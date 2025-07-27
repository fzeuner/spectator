#!/usr/bin/env python3
"""
Debug script to test AveragingRegion issue
"""

import sys
import traceback

def test_averaging_region():
    """Test AveragingRegion instantiation."""
    try:
        print("Testing AveragingRegion import and instantiation...")
        
        from models import AveragingRegion
        print("✓ AveragingRegion imported successfully")
        
        # Test with proper parameters
        region = AveragingRegion(left_limit=6200.0, center=6250.0, right_limit=6300.0)
        print(f"✓ AveragingRegion created successfully: {region}")
        
        # Test properties
        print(f"  Width: {region.width}")
        print(f"  Contains 6250: {region.contains(6250.0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ AveragingRegion test failed: {e}")
        traceback.print_exc()
        return False

def test_mvc_basic():
    """Test basic MVC functionality."""
    try:
        print("\nTesting basic MVC components...")
        
        from controllers import SpectralViewerController
        from utils import generate_example_data
        
        print("✓ MVC imports successful")
        
        # Generate test data
        data = generate_example_data(n_stokes=2, n_wl=50, n_x=25)
        print(f"✓ Test data generated: {data.shape}")
        
        # Create controller
        controller = SpectralViewerController()
        print("✓ SpectralViewerController created")
        
        return True
        
    except Exception as e:
        print(f"❌ MVC basic test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run debug tests."""
    print("=" * 50)
    print("AveragingRegion Debug Test")
    print("=" * 50)
    
    success1 = test_averaging_region()
    success2 = test_mvc_basic()
    
    if success1 and success2:
        print("\n✅ All debug tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
