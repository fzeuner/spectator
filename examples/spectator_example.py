#!/usr/bin/env python3
"""
Data Viewer Example
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
    print("Please ensure you're running in the 'spectator' conda environment:")
    print("  conda activate spectator")
    print("  python examples/spectator_example.py")
    IMPORTS_AVAILABLE = False

if __name__ == '__main__':
    
    if not IMPORTS_AVAILABLE:
        print("\nCannot run example due to import errors.")
        print("Please ensure all dependencies are installed and you're in the correct environment.")
        exit(1)
    
    # Generate example data
    print("\nGenerating test data...")
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

