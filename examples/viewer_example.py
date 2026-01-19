#!/usr/bin/env python3
"""
Data Viewer Example
"""

from spectator.utils.data_utils import generate_example_data_3d
from spectator.controllers.app_controller import display_data

if __name__ == '__main__':
    
    # Generate example data
    print("\nGenerating test data...")
    data_3d = generate_example_data_3d()  
    print(f"   3D data shape: {data_3d.shape}")
    
    print("   Command: display_data(data, order=['states', 'spectral', 'spatial_x'], title='Example', state_names=['I','Q','U','V'])")
    result = display_data(
        data_3d,
        order=['states', 'spectral', 'spatial_x'],
        title='Example',
        state_names=['I','Q','U','V'],
    )
    print("   Successfully created viewer")
