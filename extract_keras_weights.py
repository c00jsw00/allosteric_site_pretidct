# -*- coding: utf-8 -*-
"""Map Keras HDF5 weights to PyTorch CNN and run inference"""

import os, pickle, numpy as np, torch, torch.nn as nn
import h5py

base = r"C:\Users\c00jsw00\Downloads\allo_shared"
cnn_weights = os.path.join(base, "all.h5")

# Keras layer name -> PyTorch layer mapping
# Keras conv1d: (kernel_size, in_channels, out_channels) -> weights (kernel_size, in_channels, out_channels)
# PyTorch Conv1d: (out_channels, in_channels, kernel_size)

with h5py.File(cnn_weights, 'r') as f:
    mw = f['model_weights']
    
    # Extract all weights
    weights = {}
    def extract_weights(group, prefix=''):
        for key in group.keys():
            item = group[key]
            if isinstance(item, h5py.Group):
                extract_weights(item, prefix + key + '/')
            elif isinstance(item, h5py.Dataset):
                weights[prefix + key] = np.array(item)
    
    extract_weights(mw)
    
    print("Extracted weights:")
    for k, v in weights.items():
        print(f"  {k}: {v.shape}")

# Now map to PyTorch CNN
# PyTorch CNN structure:
# conv1: Conv1d(1, 32, 3) -> weight (32, 1, 3), bias (32,)
# bn1: BatchNorm1d(32) -> weight (32,), bias (32,), running_mean (32,), running_var (32,)
# conv2: Conv1d(32, 128, 3) -> weight (128, 32, 3), bias (128,)
# bn2: BatchNorm1d(128) -> ...
# conv3: Conv1d(128, 32, 5) -> weight (32, 128, 5), bias (32,)
# bn3: BatchNorm1d(32)
# conv4: Conv1d(32, 32, 3) -> weight (32, 32, 3), bias (32,)
# bn4: BatchNorm1d(32)
# dense1: Linear(1047*32, 128) -> weight (128, 1047*32), bias (128,)
# dense2: Linear(128, 32) -> weight (32, 128), bias (32,)
# dense3: Linear(32, 1) -> weight (1, 32), bias (1,)

# Keras naming:
# conv1d -> conv1d/kernel:1, conv1d/bias:1
# batch_normalization -> gamma, beta, moving_mean, moving_variance
# dense -> kernel:1, bias:1

print("\nKey weights for mapping:")
for k in sorted(weights.keys()):
    if any(x in k for x in ['kernel', 'bias', 'gamma', 'beta', 'moving_mean', 'moving_variance']):
        print(f"  {k}: {weights[k].shape}")