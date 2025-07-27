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

class DataScaler:
    """
    Class to handle automatic data scaling for better visualization.
    
    Detects when data values are very small or very large and applies
    appropriate scaling factors to improve histogram and display readability.
    """
    
    def __init__(self):
        self.current_scale_factors = {}  # Per-state scaling factors
        self.current_scale_exponents = {}  # Per-state scaling exponents
        self.current_scale_labels = {}  # Per-state scaling labels
        self.has_states_axis = False
        self.states_axis_index = None
        # Target: keep final data values under 10 for better histogram display
        self.target_max_value = 10.0
        self.scale_thresholds = {
            'large': {
                1e12: (1e-12, -12, "×10⁻¹²"),
                1e9: (1e-9, -9, "×10⁻⁹"),
                1e6: (1e-6, -6, "×10⁻⁶"),
                1e3: (1e-3, -3, "×10⁻³"),
                100: (1e-2, -2, "×10⁻²"),
                10: (1e-1, -1, "×10⁻¹"),
            },
            'small': {
                1e-12: (1e12, 12, "×10¹²"),
                1e-9: (1e9, 9, "×10⁹"),
                1e-6: (1e6, 6, "×10⁶"),
                1e-3: (1e3, 3, "×10³"),
                1e-2: (1e2, 2, "×10²"),
                1e-1: (1e1, 1, "×10¹"),
            }
        }
    
    def analyze_data_range(self, data: np.ndarray) -> Tuple[float, int, str]:
        """
        Analyze data range and determine appropriate scaling factor to keep max values under 10.
        
        Args:
            data: Input data array
            
        Returns:
            Tuple of (scale_factor, exponent, label)
        """
        if data is None or data.size == 0:
            return 1.0, 0, ""
        
        # Get data range, ignoring NaN and infinite values
        valid_data = data[np.isfinite(data)]
        if len(valid_data) == 0:
            return 1.0, 0, ""
        
        # Calculate the maximum absolute value to determine scale
        data_max = np.max(np.abs(valid_data))
        
        if data_max == 0:
            return 1.0, 0, ""
        
        # If data is already in a good range (0.1 to 10), no scaling needed
        if 0.1 <= data_max <= self.target_max_value:
            return 1.0, 0, ""
        
        # Calculate the required scaling to bring max value to around 1-10 range
        # We want: data_max * scale_factor ≈ target (let's target 5 for good margin)
        target_value = 5.0
        required_scale = target_value / data_max
        
        # Round to nearest power of 10 for clean scaling
        exponent = round(np.log10(required_scale))
        scale_factor = 10 ** exponent
        
        # Generate appropriate label
        if exponent > 0:
            label = f"×10{self._format_exponent(exponent)}"
        elif exponent < 0:
            label = f"×10{self._format_exponent(exponent)}"
        else:
            label = ""
        
        return scale_factor, exponent, label
    
    def _format_exponent(self, exp: int) -> str:
        """Format exponent with superscript characters."""
        if exp == 0:
            return ""
        
        # Superscript digits mapping
        superscript = {
            '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
            '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
            '-': '⁻'
        }
        
        exp_str = str(exp)
        return ''.join(superscript.get(c, c) for c in exp_str)
    
    def scale_data(self, data: np.ndarray, target_axes: list, auto_scale: bool = True) -> np.ndarray:
        """
        Apply per-state scaling to data if needed.
        
        Args:
            data: Input data array
            target_axes: List of axis types in data order
            auto_scale: Whether to automatically determine scaling
            
        Returns:
            Scaled data array
        """
        if not auto_scale:
            return data
        
        # Check if data has a states axis
        self.has_states_axis = any(ax == AxisType.STATES for ax in target_axes)
        
        if not self.has_states_axis:
            # No states axis - apply global scaling as before
            scale_factor, exponent, label = self.analyze_data_range(data)
            self.current_scale_factors = {'global': scale_factor}
            self.current_scale_exponents = {'global': exponent}
            self.current_scale_labels = {'global': label}
            
            if scale_factor != 1.0:
                return data * scale_factor
            else:
                return data
        
        # Has states axis - apply per-state scaling
        self.states_axis_index = target_axes.index(AxisType.STATES)
        n_states = data.shape[self.states_axis_index]
        
        # Create a copy of the data for scaling
        scaled_data = data.copy()
        
        # Scale each state independently
        for state_idx in range(n_states):
            # Extract data for this state
            state_slice = tuple(slice(None) if i != self.states_axis_index else state_idx 
                              for i in range(data.ndim))
            state_data = data[state_slice]
            
            # Analyze and determine scaling for this state
            scale_factor, exponent, label = self.analyze_data_range(state_data)
            
            # Store scaling information for this state
            self.current_scale_factors[state_idx] = scale_factor
            self.current_scale_exponents[state_idx] = exponent
            self.current_scale_labels[state_idx] = label
            
            # Apply scaling to this state if needed
            if scale_factor != 1.0:
                scaled_data[state_slice] = state_data * scale_factor
        
        return scaled_data
    
    def get_scale_info(self) -> Dict[str, Any]:
        """
        Get current scaling information.
        
        Returns:
            Dictionary with per-state scale factors, exponents, and labels
        """
        # Check if any scaling was applied
        is_scaled = any(factor != 1.0 for factor in self.current_scale_factors.values())
        
        return {
            'factors': self.current_scale_factors.copy(),
            'exponents': self.current_scale_exponents.copy(),
            'labels': self.current_scale_labels.copy(),
            'is_scaled': is_scaled,
            'has_states_axis': self.has_states_axis,
            'states_axis_index': self.states_axis_index
        }
    
    def reset_scaling(self):
        """Reset scaling to default values."""
        self.current_scale_factors = {}
        self.current_scale_exponents = {}
        self.current_scale_labels = {}
        self.has_states_axis = False
        self.states_axis_index = None

class Manager:
    """
    Main data manager class that handles input parsing, data rearrangement,
    viewer generation, and data scaling.
    """
    
    def __init__(self):
        self.dimensionality = DataDimensionality()
        self.rearranger = DataRearranger()
        self.viewer_selector = ViewerSelector()
        self.scaler = DataScaler()
    
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
            rearranged_data = self.rearranger.rearrange_data(data, validated_axes, target_axes)
        else:
            rearranged_data = data
        
        # Apply data scaling for better visualization
        auto_scale = kwargs.get('auto_scale', True)  # Allow disabling auto-scaling
        scaled_data = self.scaler.scale_data(rearranged_data, target_axes, auto_scale=auto_scale)
        
        # Log scaling information if scaling was applied
        scale_info = self.scaler.get_scale_info()
        if scale_info['is_scaled']:
            if scale_info['has_states_axis']:
                print("Per-state data scaling applied:")
                for state_idx, factor in scale_info['factors'].items():
                    if factor != 1.0:
                        label = scale_info['labels'][state_idx]
                        state_name = states_info.get(state_idx, f"State {state_idx}") if states_info else f"State {state_idx}"
                        print(f"  {state_name}: factor {factor:.2e} ({label})")
            else:
                # Global scaling (no states axis)
                factor = scale_info['factors']['global']
                label = scale_info['labels']['global']
                print(f"Data scaled by factor {factor:.2e} ({label})")
        
        # Select and create appropriate viewer
        viewer_type = self.viewer_selector.select_viewer(scaled_data.shape, target_axes)
        
        # Generate viewer-specific metadata
        viewer_metadata = self._generate_viewer_metadata(scaled_data, target_axes, states_info, title)
        
        # Add scaling information to metadata for potential display
        viewer_metadata['scale_info'] = scale_info
        
        # Create and return viewer
        return self._create_viewer(viewer_type, scaled_data, viewer_metadata, **kwargs)
    
    def get_current_scale_info(self) -> Dict[str, Any]:
        """
        Get the current data scaling information.
        
        Returns:
            Dictionary containing scale factor, exponent, label, and scaling status
        """
        return self.scaler.get_scale_info()
    
    def reset_data_scaling(self):
        """
        Reset data scaling to default values.
        """
        self.scaler.reset_scaling()
    
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
            from controllers.viewers import spectator
            
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
data_manager = Manager()

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
    from utils.data_utils import generate_example_data
    
    print("Testing Data Manager...")
    
    # Generate test data
    test_data = generate_example_data()  # Shape: (N_STOKES, N_SPECTRAL, N_X)
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
