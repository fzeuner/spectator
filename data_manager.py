#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Manager for Multi-dimensional Spectral Data Visualization

This module provides a flexible interface for handling multi-dimensional data
with arbitrary axis ordering and generates appropriate viewers based on the
data structure and user specifications.

Supported dimensions:
- 1D: spatial, spectral, time
- 2D: any combination of the above
- 3D: states + any 2 of the above, or any 3 of spatial, spectral, time
- 4D: states + any 3 of the above, or spatial + spatial + spectral + time
- 5D: states + spectral + spatial + spatial + time (maximum)

Author: Data Manager System
"""

import numpy as np
from typing import List, Tuple, Dict, Optional, Union, Any
from enum import Enum
import warnings
# local imports
import sys
sys.path.append(r"/home/zeuner/CascadeProjects/windsurf-project/")

class AxisType(Enum):
    """Enumeration of supported axis types."""
    STATES = "states"
    SPECTRAL = "spectral"
    SPATIAL = "spatial"
    TIME = "time"

class DataDimensionality:
    """Class to handle data dimensionality analysis and validation."""
    
    def __init__(self):
        self.max_dimensions = 5
        self.max_states = 8
        self.max_spatial_axes = 2
    
    def validate_axis_specification(self, axes: List[str]) -> List[AxisType]:
        """
        Validate and convert axis specification to AxisType enums.
        
        Args:
            axes: List of axis type strings
            
        Returns:
            List of AxisType enums
            
        Raises:
            ValueError: If axis specification is invalid
        """
        if len(axes) > self.max_dimensions:
            raise ValueError(f"Maximum {self.max_dimensions} dimensions supported, got {len(axes)}")
        
        # Convert strings to AxisType enums
        axis_types = []
        for axis in axes:
            try:
                axis_types.append(AxisType(axis.lower()))
            except ValueError:
                raise ValueError(f"Unsupported axis type: {axis}. "
                               f"Supported types: {[e.value for e in AxisType]}")
        
        # Validate axis combinations
        self._validate_axis_combinations(axis_types)
        
        return axis_types
    
    def _validate_axis_combinations(self, axis_types: List[AxisType]):
        """Validate that axis combinations are allowed."""
        axis_counts = {axis_type: axis_types.count(axis_type) for axis_type in AxisType}
        
        # Check states constraint
        if axis_counts[AxisType.STATES] > 1:
            raise ValueError("Only one 'states' axis is allowed")
        
        # Check spatial constraint
        if axis_counts[AxisType.SPATIAL] > self.max_spatial_axes:
            raise ValueError(f"Maximum {self.max_spatial_axes} spatial axes allowed")
        
        # Check spectral and time constraints
        if axis_counts[AxisType.SPECTRAL] > 1:
            raise ValueError("Only one 'spectral' axis is allowed")
        
        if axis_counts[AxisType.TIME] > 1:
            raise ValueError("Only one 'time' axis is allowed")
        
        # Validate specific dimension requirements
        if len(axis_types) == 1:
            if axis_types[0] not in [AxisType.SPATIAL, AxisType.SPECTRAL, AxisType.TIME]:
                raise ValueError("1D data must be spatial, spectral, or time")

class DataRearranger:
    """Class to handle data rearrangement for different viewer requirements."""
    
    def __init__(self):
        self.target_order_3d = [AxisType.STATES, AxisType.SPECTRAL, AxisType.SPATIAL]
        self.target_order_4d = [AxisType.STATES, AxisType.SPECTRAL, AxisType.SPATIAL, AxisType.SPATIAL]
        self.target_order_5d = [AxisType.STATES, AxisType.SPECTRAL, AxisType.SPATIAL, AxisType.SPATIAL, AxisType.TIME]
    
    def rearrange_data(self, data: np.ndarray, 
                      input_axes: List[AxisType], 
                      target_axes: List[AxisType]) -> np.ndarray:
        """
        Rearrange data from input axis order to target axis order.
        
        Args:
            data: Input data array
            input_axes: Current axis order
            target_axes: Desired axis order
            
        Returns:
            Rearranged data array
        """
        if len(data.shape) != len(input_axes):
            raise ValueError(f"Data has {len(data.shape)} dimensions but {len(input_axes)} axes specified")
        
        # Create mapping from input to target order
        axis_mapping = []
        for target_axis in target_axes:
            try:
                input_index = input_axes.index(target_axis)
                axis_mapping.append(input_index)
            except ValueError:
                raise ValueError(f"Target axis {target_axis.value} not found in input axes")
        
        # Transpose data to target order
        rearranged_data = np.transpose(data, axis_mapping)
        
        return rearranged_data
    
    def get_target_order(self, input_axes: List[AxisType]) -> List[AxisType]:
        """
        Determine the target axis order based on input dimensionality.
        
        Args:
            input_axes: Input axis specification
            
        Returns:
            Target axis order for the viewer
        """
        ndim = len(input_axes)
        
        if ndim <= 2:
            # For 1D and 2D, preserve order but ensure spatial comes last if present
            target_order = input_axes.copy()
            if AxisType.SPATIAL in target_order:
                # Move spatial to end
                spatial_indices = [i for i, ax in enumerate(target_order) if ax == AxisType.SPATIAL]
                for i in reversed(spatial_indices):
                    target_order.append(target_order.pop(i))
            return target_order
        
        elif ndim == 3:
            # For 3D, use standard order: states, spectral, spatial (if all present)
            if set(input_axes) == set(self.target_order_3d):
                return self.target_order_3d
            else:
                # Custom 3D arrangement
                return self._arrange_custom_3d(input_axes)
        
        elif ndim == 4:
            return self._arrange_4d(input_axes)
        
        elif ndim == 5:
            return self.target_order_5d
        
        else:
            raise ValueError(f"Unsupported number of dimensions: {ndim}")
    
    def _arrange_custom_3d(self, input_axes: List[AxisType]) -> List[AxisType]:
        """Arrange 3D data that doesn't follow the standard pattern."""
        # Priority order: states, spectral, spatial, time
        priority = [AxisType.STATES, AxisType.SPECTRAL, AxisType.SPATIAL, AxisType.TIME]
        
        target_order = []
        for axis_type in priority:
            if axis_type in input_axes:
                target_order.append(axis_type)
        
        # Add any remaining spatial axes
        spatial_count = input_axes.count(AxisType.SPATIAL)
        if spatial_count > 1:
            target_order.extend([AxisType.SPATIAL] * (spatial_count - 1))
        
        return target_order
    
    def _arrange_4d(self, input_axes: List[AxisType]) -> List[AxisType]:
        """Arrange 4D data."""
        # Standard 4D: states, spectral, spatial, spatial
        if AxisType.STATES in input_axes:
            target_order = [AxisType.STATES]
            remaining_axes = input_axes.copy()
            remaining_axes.remove(AxisType.STATES)
        else:
            target_order = []
            remaining_axes = input_axes.copy()
        
        # Add in priority order
        priority = [AxisType.SPECTRAL, AxisType.SPATIAL, AxisType.TIME]
        for axis_type in priority:
            while axis_type in remaining_axes:
                target_order.append(axis_type)
                remaining_axes.remove(axis_type)
        
        return target_order

class ViewerSelector:
    """Class to select appropriate viewer based on data characteristics."""
    
    def __init__(self):
        self.viewer_types = {
            1: "plot_1d",
            2: "plot_2d", 
            3: "spectator",
            4: "plot_4d",
            5: "plot_5d"
        }
    
    def select_viewer(self, data_shape: Tuple[int, ...], 
                     axes: List[AxisType]) -> str:
        """
        Select appropriate viewer type based on data characteristics.
        
        Args:
            data_shape: Shape of the data array
            axes: Axis types in target order
            
        Returns:
            Viewer type identifier
        """
        ndim = len(data_shape)
        
        if ndim in self.viewer_types:
            return self.viewer_types[ndim]
        else:
            raise ValueError(f"No viewer available for {ndim}D data")

class DataManager:
    """
    Main data manager class that handles input parsing, data rearrangement,
    and viewer generation.
    """
    
    def __init__(self):
        self.dimensionality = DataDimensionality()
        self.rearranger = DataRearranger()
        self.viewer_selector = ViewerSelector()
    
    def display_data(self, data: np.ndarray, 
                    *axes: str,
                    title: str = 'Data Viewer',
                    state_names: Optional[List[str]] = None,
                    **kwargs) -> Any:
        """
        Main entry point for displaying multi-dimensional data.
        
        Args:
            data: Input data array
            *axes: Axis type specifications in data order ('states', 'spectral', 'spatial', 'time')
            title: Window title for the viewer
            state_names: Optional list of names for states axis (e.g., ['I', 'Q', 'U', 'V'])
                        If None and 'states' axis is present, will use numbers ['1', '2', '3', ...]
            **kwargs: Additional parameters for specific viewers
            
        Returns:
            Viewer instance
            
        Examples:
            # 3D data: states, spectral, spatial
            display_data(data, 'states', 'spectral', 'spatial', title='Test', state_names=['I','Q'])
            
            # 3D data: states, spatial, spectral (will be rearranged)
            display_data(data, 'states', 'spatial', 'spectral', title='Test', state_names=['I','Q'])
            
            # 3D data with default state names (numbers)
            display_data(data, 'states', 'spectral', 'spatial', title='Test')
            
            # 2D data: spectral, spatial
            display_data(data, 'spectral', 'spatial', title='Test')
            
            # 4D data: states, spectral, spatial, spatial
            display_data(data, 'states', 'spectral', 'spatial', 'spatial', title='Test', state_names=['I','Q'])
        """
        # Parse input arguments
        input_axes, states_info = self._parse_input_args(data, state_names, axes)
        
        # Validate axis specification
        validated_axes = self.dimensionality.validate_axis_specification(input_axes)
        
        # Determine target axis order
        target_axes = self.rearranger.get_target_order(validated_axes)
        
        # Rearrange data if necessary
        if validated_axes != target_axes:
            print(f"Rearranging data from {[ax.value for ax in validated_axes]} "
                  f"to {[ax.value for ax in target_axes]}")
            rearranged_data = self.rearranger.rearrange_data(data, validated_axes, target_axes)
        else:
            rearranged_data = data
        
        # Select and create appropriate viewer
        viewer_type = self.viewer_selector.select_viewer(rearranged_data.shape, target_axes)
        
        # Generate viewer-specific metadata
        viewer_metadata = self._generate_viewer_metadata(rearranged_data, target_axes, states_info, title)
        
        # Create and return viewer
        return self._create_viewer(viewer_type, rearranged_data, viewer_metadata, **kwargs)
    
    def _parse_input_args(self, data: np.ndarray, 
                         state_names: Optional[List[str]], 
                         axes: Tuple[str, ...]) -> Tuple[List[str], Dict[str, Any]]:
        """Parse and validate input arguments."""
        input_axes = list(axes)
        states_info = {}
        
        # Validate that we have the right number of axes
        if len(input_axes) != len(data.shape):
            raise ValueError(f"Number of axes ({len(input_axes)}) must match data dimensions ({len(data.shape)}). "
                           f"Provided axes: {input_axes}, Data shape: {data.shape}")
        
        # Handle states axis and naming
        if 'states' in input_axes:
            states_axis_index = input_axes.index('states')
            n_states = data.shape[states_axis_index]
            
            # Validate state_names if provided
            if state_names is not None:
                if len(state_names) > self.dimensionality.max_states:
                    raise ValueError(f"Maximum {self.dimensionality.max_states} states allowed")
                if len(state_names) != n_states:
                    raise ValueError(f"Number of state names ({len(state_names)}) must match states dimension ({n_states})")
                names = state_names
            else:
                # Generate default numeric names
                names = [str(i+1) for i in range(n_states)]
            
            states_info = {
                'names': names,
                'count': n_states,
                'axis_index': states_axis_index
            }
        
        return input_axes, states_info
    
    def _generate_viewer_metadata(self, data: np.ndarray, 
                                 axes: List[AxisType], 
                                 states_info: Dict[str, Any], 
                                 title: str) -> Dict[str, Any]:
        """Generate metadata for the viewer."""
        metadata = {
            'title': title,
            'data_shape': data.shape,
            'axes': [ax.value for ax in axes],
            'states_info': states_info
        }
        
        # Add axis-specific information
        for i, axis_type in enumerate(axes):
            if axis_type == AxisType.STATES:
                metadata['states_axis'] = i
                metadata['n_states'] = data.shape[i]
            elif axis_type == AxisType.SPECTRAL:
                metadata['spectral_axis'] = i
                metadata['n_spectral'] = data.shape[i]
            elif axis_type == AxisType.SPATIAL:
                if 'spatial_axes' not in metadata:
                    metadata['spatial_axes'] = []
                metadata['spatial_axes'].append(i)
            elif axis_type == AxisType.TIME:
                metadata['time_axis'] = i
                metadata['n_time'] = data.shape[i]
        
        return metadata
    
    def _create_viewer(self, viewer_type: str, 
                      data: np.ndarray, 
                      metadata: Dict[str, Any], 
                      **kwargs) -> Any:
        """Create the appropriate viewer instance."""
        if viewer_type == "spectator":
            # Use existing 3D spectral viewer
            from viewers import spectator
            
            # Validate that this is the expected format for the current viewer
            if (len(data.shape) == 3 and 
                metadata.get('states_axis') == 0 and 
                metadata.get('spectral_axis') == 1 and 
                2 in metadata.get('spatial_axes', [])):
                
                # Get state names from metadata
                state_names = metadata.get('states_info', {}).get('names', None)
                return spectator(data, title=metadata['title'], state_names=state_names)
            else:
                raise NotImplementedError(f"3D viewer for axis configuration {metadata['axes']} not yet implemented")
        
        else:
            # Placeholder for other viewer types
            print(f"Viewer type '{viewer_type}' not yet implemented.")
            print(f"Data shape: {data.shape}")
            print(f"Axes: {metadata['axes']}")
            print(f"Metadata: {metadata}")
            
            # For now, return a simple representation
            return {
                'viewer_type': viewer_type,
                'data': data,
                'metadata': metadata,
                'message': f"Viewer for {len(data.shape)}D data with axes {metadata['axes']} is ready for implementation"
            }

# Global instance for easy access
data_manager = DataManager()

# Convenience function that matches the requested interface
def display_data(data: np.ndarray, 
                *axes: str,
                title: str = 'Data Viewer',
                state_names: Optional[List[str]] = None,
                **kwargs) -> Any:
    """
    Display multi-dimensional data with flexible axis specification.
    
    This function provides a flexible interface for visualizing multi-dimensional
    spectral data. It automatically handles data rearrangement and selects the
    appropriate viewer based on the data structure.
    
    Args:
        data: Input data array (1-5 dimensions)
        *axes: Axis type specifications in data order ('states', 'spectral', 'spatial', 'time')
        title: Window title for the viewer
        state_names: Optional list of names for states axis (e.g., ['I', 'Q', 'U', 'V'])
                    If None and 'states' axis is present, will use numbers ['1', '2', '3', ...]
        **kwargs: Additional parameters for specific viewers
        
    Returns:
        Viewer instance or viewer information
        
    Examples:
        # 3D data: states, spectral, spatial
        display_data(data, 'states', 'spectral', 'spatial', title='Test data', state_names=['I','Q'])
        
        # Same data but with different input order (will be rearranged)
        display_data(data, 'states', 'spatial', 'spectral', title='Test data', state_names=['I','Q'])
        
        # 3D data with default state names (numbers)
        display_data(data, 'states', 'spectral', 'spatial', title='Test data')
        
        # 2D spectral-spatial data
        display_data(data, 'spectral', 'spatial', title='2D data')
        
        # 1D spectral data
        display_data(data, 'spectral', title='Spectrum')
        
        # 4D data with two spatial dimensions
        display_data(data, 'states', 'spectral', 'spatial', 'spatial', title='4D data', state_names=['I','Q'])
        
        # 5D data (maximum)
        display_data(data, 'states', 'spectral', 'spatial', 'spatial', 'time', title='5D data', state_names=['I','Q','U','V'])
    """
    return data_manager.display_data(data, *axes, title=title, state_names=state_names, **kwargs)

if __name__ == "__main__":
    # Test the data manager with example data
    from functions import ExampleData
    
    print("Testing Data Manager...")
    
    # Generate test data
    test_data = ExampleData()  # Shape: (N_STOKES, N_WL, N_X)
    print(f"Test data shape: {test_data.shape}")
    
    # Test 1: Current format (should work with existing viewer)
    print("\n1. Testing current format (states, spectral, spatial):")
    try:
        result1 = display_data(test_data, 'states', 'spectral', 'spatial', 
                              title='Current Format', state_names=['I', 'Q', 'U', 'V'])
        print("✓ Current format test passed")
    except Exception as e:
        print(f"✗ Current format test failed: {e}")
    
    # Test 2: Rearranged format
    print("\n2. Testing rearranged format (states, spatial, spectral):")
    try:
        result2 = display_data(test_data, 'states', 'spatial', 'spectral',
                              title='Rearranged Format', state_names=['I', 'Q', 'U', 'V'])
        print("✓ Rearranged format test passed")
    except Exception as e:
        print(f"✗ Rearranged format test failed: {e}")
    
    # Test 3: Default state names
    print("\n3. Testing default state names (states, spectral, spatial):")
    try:
        result3 = display_data(test_data, 'states', 'spectral', 'spatial', title='Default Names')
        print("✓ Default state names test passed")
    except Exception as e:
        print(f"✗ Default state names test failed: {e}")
    
    # Test 4: 2D data
    print("\n4. Testing 2D data (spectral, spatial):")
    try:
        data_2d = test_data[0, :, :]  # Take first Stokes parameter
        result4 = display_data(data_2d, 'spectral', 'spatial', title='2D Data')
        print("✓ 2D data test passed")
    except Exception as e:
        print(f"✗ 2D data test failed: {e}")
    
    print("\nData Manager testing complete!")
