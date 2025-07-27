#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 09:56:31 2024

@author: franziskaz

WARNING: if the qdarkstyle is used, there are some minor bugs in Dock and VerticalLabel:
    create the following links (look at the files in this folder):
        - mv ~/miniconda3/envs/bayes/lib/python3.12/site-packages/pyqtgraph/widgets/VerticalLabel.py ~/miniconda3/envs/bayes/lib/python3.12/site-packages/pyqtgraph/widgets/VerticalLabel.py_bk
        - ln -s ~/code/dkist/VerticalLabel.py ~/miniconda3/envs/bayes/lib/python3.12/site-packages/pyqtgraph/widgets/
        - mv ~/miniconda3/envs/bayes/lib/python3.12/site-packages/pyqtgraph/dockarea/Dock.py ~/miniconda3/envs/bayes/lib/python3.12/site-packages/pyqtgraph/dockarea/Dock.py_bk
        - ln -s ~/code/dkist/Dock.py ~/miniconda3/envs/bayes/lib/python3.12/site-packages/pyqtgraph/dockarea/

pyqtgraph = 0.13.7

INPUT:
    - numpy data cube ordered by N_STOKES, N_WL, N_X 

- TODO: 
    + handle N_STOKES=1 case
    + add spatial x and spatial y profile
    + averaging in x and/or y
    + large data - maybe using fastplotlib?
    + changing point sizes does not work: self.plot.getAxis('left').setStyle(tickFont = QFont().setPointSize(1))
    + multiple crosshairs
    + flexible data (only image spectra, non-stokes scans...)
    
Look at (multiple) images in an interactive way.
"""
import numpy as np
from data_manager import display_data
from functions import ExampleData

if __name__ == '__main__':
    
       # Generate example data
    print("\n1. Generating test data...")
    data_3d = ExampleData()  # Shape: (N_STOKES, N_WL, N_X)
    print(f"   3D data shape: {data_3d.shape}")
    
    print("   Command: display_data(data, 'spectral', 'spatial', title='Current Format', states=['I','Q','U','V'])")
    try:
        result = display_data(data_3d, 'states', 'spectral', 'spatial', 
                              title='Current Format', state_names=['I','Q','U','V'])
        print("   ✓ Successfully created viewer")
    except Exception as e:
        print(f"   ✗ Error: {e}")
