#!/usr/bin/env python3
"""
Data Viewer Example

This example demonstrates how to use the new Model-View-Controller architecture
for the spectral data viewer. 

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
    - numpy data cube: ordered arbitrarily, because the data manager handles the ordering

- TODO: 
    + add spatial x and spatial y profile
    + averaging in x and/or y
    + large data - maybe using fastplotlib?
    + changing point sizes does not work: self.plot.getAxis('left').setStyle(tickFont = QFont().setPointSize(1))
    + multiple crosshairs
    + flexible data (only image spectra, non-stokes scans...)
    
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import required modules with proper error handling
try:
    
    from controllers import Manager
    from utils.data_utils import generate_example_data
    
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure you're running in the 'dkist' conda environment:")
    print("  conda activate dkist")
    print("  python examples/spectator_example.py")
    IMPORTS_AVAILABLE = False

if __name__ == '__main__':
    
    if not IMPORTS_AVAILABLE:
        print("\nCannot run example due to import errors.")
        print("Please ensure all dependencies are installed and you're in the correct environment.")
        exit(1)
    
    # Generate example data
    print("\n1. Generating test data...")
    data_3d = generate_example_data()  
    print(f"   3D data shape: {data_3d.shape}")
    
    print("   Command: display_data(data, 'states', 'spectral', 'spatial', title='Example', state_names=['I','Q','U','V'])")
    try:
        from controllers.app_controller import display_data
        result = display_data(data_3d, 'states', 'spectral', 'spatial', 
                              title='Example', state_names=['I','Q','U','V'])
        print("   ✓ Successfully created viewer")
    except Exception as e:
        print(f"   ✗ Error: {e}")

