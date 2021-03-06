#!/usr/bin/env python

from __future__ import print_function

import matplotlib as mpl
#mpl.use("Agg")

import numpy as np
import matplotlib.pyplot as plt

from costar_models import *
from costar_models.sampler2 import PredictionSampler2
from costar_models.datasets.npz import NpzDataset
from costar_models.datasets.npy_generator import NpzGeneratorDataset
from costar_models.datasets.h5f_generator import H5fGeneratorDataset

'''
Tool for running model training without the rest of the simulation/planning/ROS
code. This should be more or less independent and only rely on a couple
external features.
'''

def visualizeHiddenMain(args):
    ConfigureGPU(args)

    data_file_info = args['data_file'].split('.')
    data_type = data_file_info[-1]
    root = ""
    for i, tok in enumerate(data_file_info[:-1]):
        if i < len(data_file_info)-1 and i > 0:
            root += '.'
        root += tok
    if data_type == "npz":
        dataset = NpzGeneratorDataset(root)
        data = dataset.load(success_only = args['success_only'])
    elif data_type == "h5f":
        dataset = H5fGeneratorDataset(root)
        data = dataset.load(success_only = args['success_only'])
    else:
        raise NotImplementedError('data type not implemented: %s'%data_type)

    if 'model' in args and args['model'] is not None:
        model = MakeModel(taskdef=None, **args)
        model.setValidationMode()
        model.load(world=None,**data)
        train_generator = model.trainGenerator(dataset)
        test_generator = model.testGenerator(dataset)

        if not isinstance(model, PredictionSampler2):
            raise RuntimeError('Only sampler2, conditional_sampler, etc. are'
                               'supported')

        features, targets = next(test_generator)
        I0 = features[0]
        I = features[1]
        
        h = model.encode(I)
        if not h.shape[0] == I.shape[0]:
            raise RuntimeError('something went wrong with dimensions')

        print("--------------\nHidden state:\n--------------\n")
        print("shape of hidden samples =", h.shape)
        print("shape of images =", I.shape)
        for i in range(h.shape[0]):
            plt.figure(figsize=(3,3))
            plt.subplot(3,3,1)
            Show(I[i])
            for j in range(h.shape[-1]):
                plt.subplot(3,3,j+2)
                Show(np.squeeze(h[i,:,:,j]))
            plt.show()

    else:
        raise RuntimeError('Must provide a model to load')

if __name__ == '__main__':
    args = ParseModelArgs()
    if args['profile']:
        import cProfile
        cProfile.run('main(args)')
    else:
        visualizeHiddenMain(args)
