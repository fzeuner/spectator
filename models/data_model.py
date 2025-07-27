"""
Core data models for the spectral data viewer.

This module contains the fundamental data structures and validation logic
for handling multi-dimensional spectral data.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any, Union
from enum import Enum


class AxisType(Enum):
    """Enumeration of supported axis types."""
    STATES = "states"
    SPECTRAL = "spectral" 
    SPATIAL = "spatial"
    TIME = "time"


class SpectralData:
    """
    Core data structure for multi-dimensional spectral data.
    
    Handles data validation, axis management, and transformations.
    """
    
    def __init__(self, data: np.ndarray, axes: List[Union[str, AxisType]], 
                 state_names: Optional[List[str]] = None, 
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize spectral data.
        
        Args:
            data: Multi-dimensional numpy array
            axes: List of axis types in data order
            state_names: Optional names for states axis
            metadata: Optional metadata dictionary
        """
        self.data = data
        self.axes = self._validate_and_convert_axes(axes)
        self.state_names = state_names
        self.metadata = metadata or {}
        
        self._validate_data()
        self._generate_default_state_names()
    
    def _validate_and_convert_axes(self, axes: List[Union[str, AxisType]]) -> List[AxisType]:
        """Convert string axes to AxisType enum and validate."""
        converted_axes = []
        for axis in axes:
            if isinstance(axis, str):
                try:
                    converted_axes.append(AxisType(axis))
                except ValueError:
                    raise ValueError(f"Invalid axis type: {axis}")
            elif isinstance(axis, AxisType):
                converted_axes.append(axis)
            else:
                raise ValueError(f"Axis must be string or AxisType, got {type(axis)}")
        
        return converted_axes
    
    def _validate_data(self):
        """Validate data dimensions and axis specifications."""
        if not isinstance(self.data, np.ndarray):
            raise ValueError("Data must be a numpy array")
        
        if len(self.axes) != self.data.ndim:
            raise ValueError(f"Number of axes ({len(self.axes)}) must match data dimensions ({self.data.ndim})")
        
        if self.data.ndim < 1 or self.data.ndim > 5:
            raise ValueError(f"Data must be 1-5 dimensional, got {self.data.ndim}D")
        
        # Validate axis type constraints
        axis_counts = {axis_type: self.axes.count(axis_type) for axis_type in AxisType}
        
        if axis_counts[AxisType.STATES] > 1:
            raise ValueError("Only one states axis is allowed")
        if axis_counts[AxisType.SPECTRAL] > 1:
            raise ValueError("Only one spectral axis is allowed")
        if axis_counts[AxisType.SPATIAL] > 2:
            raise ValueError("Maximum two spatial axes are allowed")
        if axis_counts[AxisType.TIME] > 1:
            raise ValueError("Only one time axis is allowed")
    
    def _generate_default_state_names(self):
        """Generate default state names if not provided."""
        if AxisType.STATES in self.axes and self.state_names is None:
            states_axis_idx = self.axes.index(AxisType.STATES)
            n_states = self.data.shape[states_axis_idx]
            self.state_names = [str(i+1) for i in range(n_states)]
        
        # Validate state names if provided
        if self.state_names is not None:
            if AxisType.STATES not in self.axes:
                raise ValueError("state_names provided but no states axis found")
            
            states_axis_idx = self.axes.index(AxisType.STATES)
            n_states = self.data.shape[states_axis_idx]
            
            if len(self.state_names) != n_states:
                raise ValueError(f"Number of state names ({len(self.state_names)}) must match states dimension ({n_states})")
    
    def get_axis_index(self, axis_type: AxisType) -> Optional[int]:
        """Get the index of a specific axis type."""
        try:
            return self.axes.index(axis_type)
        except ValueError:
            return None
    
    def has_axis(self, axis_type: AxisType) -> bool:
        """Check if data has a specific axis type."""
        return axis_type in self.axes
    
    def get_shape_for_axis(self, axis_type: AxisType) -> Optional[int]:
        """Get the size of a specific axis."""
        idx = self.get_axis_index(axis_type)
        return self.data.shape[idx] if idx is not None else None
    
    def rearrange_for_viewer(self, target_axes: List[AxisType]) -> Tuple[np.ndarray, List[str]]:
        """
        Rearrange data to match target axis order for a specific viewer.
        
        Args:
            target_axes: Desired axis order
            
        Returns:
            Tuple of (rearranged_data, state_names)
        """
        if len(target_axes) != len(self.axes):
            raise ValueError(f"Target axes length ({len(target_axes)}) must match data dimensions ({len(self.axes)})")
        
        # Check that all required axes are present
        for axis in target_axes:
            if axis not in self.axes:
                raise ValueError(f"Required axis {axis} not found in data")
        
        # Create transpose order
        transpose_order = []
        for target_axis in target_axes:
            current_idx = self.axes.index(target_axis)
            transpose_order.append(current_idx)
        
        # Transpose data
        rearranged_data = self.data.transpose(transpose_order)
        
        return rearranged_data, self.state_names or []
    
    @property
    def shape(self) -> Tuple[int, ...]:
        """Get data shape."""
        return self.data.shape
    
    @property
    def ndim(self) -> int:
        """Get number of dimensions."""
        return self.data.ndim
    
    @property
    def n_states(self) -> int:
        """Get number of states (first axis if it's a states axis)."""
        if self.has_axis(AxisType.STATES):
            states_idx = self.get_axis_index(AxisType.STATES)
            return self.data.shape[states_idx]
        return 1  # Default to 1 if no states axis
    
    def get_state_name(self, index: int) -> str:
        """Get the name of a specific state."""
        if self.state_names and index < len(self.state_names):
            return self.state_names[index]
        return f"State {index}"
    
    def __repr__(self) -> str:
        """String representation of the data."""
        axes_str = ", ".join([axis.value for axis in self.axes])
        return f"SpectralData(shape={self.shape}, axes=[{axes_str}])"


class AxisConfiguration:
    """
    Configuration for axis types and their properties.
    """
    
    # Standard axis orders for different viewer types
    VIEWER_AXIS_ORDERS = {
        1: {
            "plot_1d": [AxisType.SPECTRAL],  # or SPATIAL or TIME
        },
        2: {
            "plot_2d": [AxisType.SPECTRAL, AxisType.SPATIAL],
        },
        3: {
            "spectator": [AxisType.STATES, AxisType.SPECTRAL, AxisType.SPATIAL],
        },
        4: {
            "plot_4d": [AxisType.STATES, AxisType.SPECTRAL, AxisType.SPATIAL, AxisType.TIME],
        },
        5: {
            "plot_5d": [AxisType.STATES, AxisType.SPECTRAL, AxisType.SPATIAL, AxisType.SPATIAL, AxisType.TIME],
        }
    }
    
    @classmethod
    def get_viewer_axes(cls, viewer_type: str, ndim: int) -> List[AxisType]:
        """Get the expected axis order for a specific viewer type."""
        if ndim not in cls.VIEWER_AXIS_ORDERS:
            raise ValueError(f"No axis configuration for {ndim}D data")
        
        if viewer_type not in cls.VIEWER_AXIS_ORDERS[ndim]:
            raise ValueError(f"No axis configuration for viewer type '{viewer_type}' with {ndim}D data")
        
        return cls.VIEWER_AXIS_ORDERS[ndim][viewer_type]
    
    @classmethod
    def validate_axes_for_viewer(cls, axes: List[AxisType], viewer_type: str) -> bool:
        """Validate that axes are compatible with a viewer type."""
        try:
            expected_axes = cls.get_viewer_axes(viewer_type, len(axes))
            return set(axes) == set(expected_axes)
        except ValueError:
            return False
    
    def parse_axis_types(self, axis_types: List[str]) -> List[AxisType]:
        """Parse string axis types to AxisType enum."""
        parsed_axes = []
        for axis_str in axis_types:
            try:
                axis_type = AxisType(axis_str.lower())
                parsed_axes.append(axis_type)
            except ValueError:
                raise ValueError(f"Invalid axis type: {axis_str}")
        return parsed_axes
    
    def validate_data_shape(self, data_shape: tuple, axes: List[AxisType]) -> bool:
        """Validate that data shape is compatible with axis specification."""
        if len(data_shape) != len(axes):
            return False
        
        # Check for valid axis combinations
        axis_counts = {}
        for axis in axes:
            axis_counts[axis] = axis_counts.get(axis, 0) + 1
        
        # Validation rules
        if axis_counts.get(AxisType.STATES, 0) > 1:
            return False  # Only one states axis allowed
        if axis_counts.get(AxisType.SPECTRAL, 0) > 1:
            return False  # Only one spectral axis allowed
        if axis_counts.get(AxisType.SPATIAL, 0) > 2:
            return False  # Maximum two spatial axes
        if axis_counts.get(AxisType.TIME, 0) > 1:
            return False  # Only one time axis allowed
        
        return True
    
    def rearrange_data_for_viewer(self, data: np.ndarray, axes: List[AxisType], 
                                viewer_type) -> Tuple[np.ndarray, List[AxisType]]:
        """Rearrange data to match viewer requirements."""
        from .viewer_config import ViewerType  # Import here to avoid circular imports
        
        # Get expected axis order for viewer
        if viewer_type == ViewerType.SPECTATOR:
            expected_axes = [AxisType.STATES, AxisType.SPECTRAL, AxisType.SPATIAL]
        else:
            # For other viewers, return data as-is for now
            return data, axes
        
        # Check if rearrangement is needed
        if axes == expected_axes:
            return data, axes
        
        # Create mapping from current to expected order
        transpose_order = []
        final_axes = []
        
        for expected_axis in expected_axes:
            if expected_axis in axes:
                current_index = axes.index(expected_axis)
                transpose_order.append(current_index)
                final_axes.append(expected_axis)
        
        # Transpose data if needed
        if transpose_order != list(range(len(transpose_order))):
            rearranged_data = np.transpose(data, transpose_order)
        else:
            rearranged_data = data
        
        return rearranged_data, final_axes
