# -*- coding: utf-8 -*-

import logging
import yaml
import re
import numpy as np

from dan.common.config import ConfigBunch

def prune_tool():
    raise Exception("Unimplemented")

class PruneTool(object):
    required_conf = ['input_proto', 'input_caffemodel', 'output_caffemodel', 'conditions']

    def __init__(self, config, hide_file_path=False):
        self.prune_cond = config.conditions
        self.input_proto = str(config.input_proto)
        self.input_caffemodel = str(config.input_caffemodel)
        self.output_caffemodel = str(config.output_caffemodel)

    @classmethod
    def load_from_config_file(cls, conf_file):
        logger = logging.getLogger('dan.prunetool') # could move to global variable
        try:
            conf_dict = yaml.load(open(conf_file, 'r'))
        #except yaml.error.YAMLError as e:
        except Exception: # 还有文件不存在
            logger.error("Configuration file is corrupted! Aborting!")
            return None

        hide_file_path = conf_dict.get('hide_file_path', False)
        return cls.load_from_config(conf_dict, hide_file_path=hide_file_path)
        
    @classmethod
    def load_from_config(cls, conf_dict, **kwargs):
        """
        Construct PruneTool instance from config"""
        logger = logging.getLogger('dan.prunetool')
        for conf_name in cls.required_conf:
            if not conf_name in conf_dict:
                logger.error("Configuration do not have '%s' which is required,"
                             " please check your configuration file.", conf_name)
                return None

        new_ins = cls(ConfigBunch(conf_dict), **kwargs)
        return new_ins

    def run(self):
        logger = logging.getLogger('dan.prunetool')
        import caffe

        net = caffe.Net(self.input_proto, self.input_caffemodel, caffe.TEST)
        layers = net.params.keys()
        done_layers = []

        for (regex, pattern, sparsity) in self.prune_cond:
            if regex:
                p = re.compile(pattern)
                def match(string):
                    res = p.match(string)
                    if res is None:
                        return False
                    span = res.span()
                    return (span[1] - span[0]) == len(string)
                
                layers_to_prune = filter(match, layers)
            else:
                layers_to_prune = filter(lambda x:pattern in x, layers)

            layers_to_prune = filter(lambda x:x not in done_layers, layers_to_prune)
            done_layers.extend(layers_to_prune)

            for layer in layers_to_prune:
                weights = net.params[layer][0].data

                flatten_data= weights.flatten()
                rank = np.argsort(abs(flatten_data))
                flatten_data[rank[:int(rank.size * sparsity)]] = 0

                flatten_data = flatten_data.reshape(weights.shape)
                np.copyto(weights, flatten_data)
                logger.info('Finish pruning of layer %s!\n', layer)

        net.save(self.output_caffemodel)
        logger.info('Finish pruning of all layers! Caffemodel in file "%s".\n', self.output_caffemodel)
                
        return True