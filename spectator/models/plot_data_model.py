"""
Data model for plot windows.

This module provides a unified interface for managing plot data, handling
slicing operations, and coordinate transformations across different window types.
"""

import numpy as np
from typing import Tuple, Optional
from .axis_config import AxisConfig


class PlotDataModel:
    """Encapsulates data and axis configuration for plot windows.
    
    This class provides a consistent interface for:
    - Storing multi-dimensional data
    - Slicing data along specific dimensions
    - Computing averaged slices
    - Converting data slices to plot coordinates
    - Validating indices
    
    Attributes:
        data: The underlying numpy array
        config: AxisConfig defining how to plot the data
        shape: Shape of the data array
        ndim: Number of dimensions in the data
    """
    
    def __init__(self, data: np.ndarray, config: AxisConfig):
        """Initialize the data model.
        
        Args:
            data: Numpy array of any dimensionality
            config: AxisConfig specifying how to plot this data
        """
        self.data = data
        self.config = config
        self.shape = data.shape
        self.ndim = data.ndim
        
        # Create index arrays for each dimension
        self._index_arrays = tuple(np.arange(s) for s in self.shape)
    
    def get_slice_at_index(self, dim: int, index: int) -> np.ndarray:
        """Get a slice along specified dimension at given index.
        
        Args:
            dim: Dimension to slice along (0-indexed)
            index: Index along that dimension
            
        Returns:
            Sliced data array (reduced by one dimension)
            
        Example:
            For 2D data (spectral, x), get_slice_at_index(0, 10) returns
            data[10, :] - the spatial profile at spectral index 10
        """
        if dim < 0 or dim >= self.ndim:
            raise ValueError(f"Dimension {dim} out of range for {self.ndim}D data")
        
        index = self.validate_index(dim, index)
        
        # Build slice tuple
        slices = [slice(None)] * self.ndim
        slices[dim] = index
        return self.data[tuple(slices)]
    
    def get_averaged_slice(self, dim: int, start: int, end: int) -> np.ndarray:
        """Get averaged slice along dimension between start and end indices.
        
        Args:
            dim: Dimension to slice and average along
            start: Starting index (inclusive)
            end: Ending index (inclusive)
            
        Returns:
            Averaged data array (reduced by one dimension)
            
        Example:
            For 2D data (spectral, x), get_averaged_slice(0, 10, 20) returns
            data[10:21, :].mean(axis=0) - spatial profile averaged over spectral range
        """
        if dim < 0 or dim >= self.ndim:
            raise ValueError(f"Dimension {dim} out of range for {self.ndim}D data")
        
        start = self.validate_index(dim, start)
        end = self.validate_index(dim, end)
        
        # Ensure start <= end
        if start > end:
            start, end = end, start
        
        # Build slice tuple
        slices = [slice(None)] * self.ndim
        slices[dim] = slice(start, end + 1)
        
        # Get slice and average along the specified dimension
        data_slice = self.data[tuple(slices)]
        return data_slice.mean(axis=dim)
    
    def get_plot_data(self, data_slice: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Convert data slice to (x, y) coordinates for setData().
        
        Args:
            data_slice: 1D array from get_slice_at_index or get_averaged_slice
            
        Returns:
            Tuple of (x_coords, y_coords) ready for PlotDataItem.setData()
        """
        return self.config.get_plot_coordinates(data_slice, self._index_arrays)
    
    def validate_index(self, dim: int, index: int) -> int:
        """Clamp index to valid range for given dimension.
        
        Args:
            dim: Dimension to validate against
            index: Index to validate
            
        Returns:
            Clamped index within [0, shape[dim]-1]
        """
        if dim < 0 or dim >= self.ndim:
            raise ValueError(f"Dimension {dim} out of range for {self.ndim}D data")
        
        return int(np.clip(index, 0, self.shape[dim] - 1))
    
    def update_data(self, new_data: np.ndarray):
        """Update the underlying data array.
        
        Args:
            new_data: New data array (must have same number of dimensions)
            
        Raises:
            ValueError: If new data has different dimensionality
        """
        if new_data.ndim != self.ndim:
            raise ValueError(
                f"New data has {new_data.ndim} dimensions, "
                f"expected {self.ndim} dimensions"
            )
        
        self.data = new_data
        self.shape = new_data.shape
        self._index_arrays = tuple(np.arange(s) for s in self.shape)
    
    def get_dimension_size(self, dim: int) -> int:
        """Get the size of a specific dimension.
        
        Args:
            dim: Dimension index
            
        Returns:
            Size of that dimension
        """
        if dim < 0 or dim >= self.ndim:
            raise ValueError(f"Dimension {dim} out of range for {self.ndim}D data")
        return self.shape[dim]
    
    def get_index_array(self, dim: int) -> np.ndarray:
        """Get the index array for a specific dimension.
        
        Args:
            dim: Dimension index
            
        Returns:
            Array of indices [0, 1, 2, ..., size-1]
        """
        if dim < 0 or dim >= self.ndim:
            raise ValueError(f"Dimension {dim} out of range for {self.ndim}D data")
        return self._index_arrays[dim]
