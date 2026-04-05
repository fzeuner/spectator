"""
Axis configuration for plot windows.

This module defines how data dimensions map to plot axes, providing a clear
abstraction for different window types with varying axis orientations.
"""

from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass
class AxisConfig:
    """Configuration for how data dimensions map to plot axes.
    
    This class encapsulates all the information needed to correctly orient
    and label plot axes for different window types.
    
    Attributes:
        x_axis_source: Which data to use for plot x-axis ('data' or 'index')
        y_axis_source: Which data to use for plot y-axis ('data' or 'index')
        x_data_dim: Which data dimension provides x values (if x_axis_source='data')
        y_data_dim: Which data dimension provides y values (if y_axis_source='data')
        x_label: Label for x-axis
        y_label: Label for y-axis
        x_units: Units for x-axis
        y_units: Units for y-axis
        line_angle: Angle for draggable line (0=vertical, 90=horizontal)
        swap_plot_coords: If True, swap x and y when calling setData()
    """
    x_axis_source: str  # 'data' or 'index'
    y_axis_source: str  # 'data' or 'index'
    x_data_dim: int = 0
    y_data_dim: int = 1
    x_label: str = ""
    y_label: str = ""
    x_units: str = ""
    y_units: str = ""
    line_angle: float = 90
    swap_plot_coords: bool = False
    
    def get_plot_coordinates(self, 
                            data_slice: np.ndarray,
                            index_arrays: Tuple[np.ndarray, ...] = None) -> Tuple[np.ndarray, np.ndarray]:
        """Convert data slice to (x_coords, y_coords) for plotting.
        
        Args:
            data_slice: 1D array of data values
            index_arrays: Tuple of index arrays corresponding to data dimensions
            
        Returns:
            Tuple of (x_coords, y_coords) ready for setData()
        """
        if data_slice.ndim != 1:
            raise ValueError(f"Expected 1D data slice, got shape {data_slice.shape}")
        
        # Determine x coordinates
        if self.x_axis_source == 'data':
            x_coords = data_slice
        elif self.x_axis_source == 'index':
            if index_arrays is None or len(index_arrays) <= self.x_data_dim:
                x_coords = np.arange(len(data_slice))
            else:
                x_coords = index_arrays[self.x_data_dim]
        else:
            raise ValueError(f"Invalid x_axis_source: {self.x_axis_source}")
        
        # Determine y coordinates
        if self.y_axis_source == 'data':
            y_coords = data_slice
        elif self.y_axis_source == 'index':
            if index_arrays is None or len(index_arrays) <= self.y_data_dim:
                y_coords = np.arange(len(data_slice))
            else:
                y_coords = index_arrays[self.y_data_dim]
        else:
            raise ValueError(f"Invalid y_axis_source: {self.y_axis_source}")
        
        # Swap if needed
        if self.swap_plot_coords:
            return y_coords, x_coords
        else:
            return x_coords, y_coords
    
    def __post_init__(self):
        """Validate configuration."""
        valid_sources = {'data', 'index'}
        if self.x_axis_source not in valid_sources:
            raise ValueError(f"x_axis_source must be one of {valid_sources}")
        if self.y_axis_source not in valid_sources:
            raise ValueError(f"y_axis_source must be one of {valid_sources}")


class AxisConfigs:
    """Factory methods for common window type configurations."""
    
    @staticmethod
    def spatial_window() -> AxisConfig:
        """Config for StokesSpatialWindow (x vs z).
        
        Data shape: (spectral, x)
        Plot: x-axis shows spatial position (x), y-axis shows intensity (z)
        Draggable line: vertical (tracks x position)
        
        Note: We slice along spectral dimension to get 1D spatial profile.
        The spatial indices go on x-axis, profile data values go on y-axis.
        """
        return AxisConfig(
            x_axis_source='index',  # spatial indices on x-axis
            y_axis_source='data',  # intensity values on y-axis
            x_data_dim=1,  # spatial dimension for indices
            y_data_dim=0,  # not used since y comes from data
            x_label="x",
            y_label="z",
            x_units="pixel",
            y_units="",
            line_angle=0,  # vertical line
            swap_plot_coords=False  # setData(indices, data) - normal orientation
        )
    
    @staticmethod
    def spectrum_window() -> AxisConfig:
        """Config for StokesSpectrumWindow (z vs λ).
        
        Data shape: (spectral, x)
        Plot: x-axis shows spectral position (λ), y-axis shows intensity (z)
        Draggable line: vertical (tracks spectral position)
        """
        return AxisConfig(
            x_axis_source='index',  # spectral indices on x-axis
            y_axis_source='data',  # intensity values on y-axis
            x_data_dim=0,  # spectral dimension
            y_data_dim=1,  # not used since y comes from data
            x_label="λ",
            y_label="z",
            x_units="pixel",
            y_units="",
            line_angle=90,  # horizontal line
            swap_plot_coords=False  # setData(indices, data)
        )
    
    @staticmethod
    def spatial_y_window() -> AxisConfig:
        """Config for StokesSpatialYWindow (z vs y).
        
        Data: 3D cube sliced to 1D profile
        Plot: x-axis shows intensity (z), y-axis shows spatial_y position
        Draggable line: horizontal (tracks y position)
        """
        return AxisConfig(
            x_axis_source='data',  # intensity values on x-axis
            y_axis_source='index',  # spatial_y indices on y-axis
            x_data_dim=0,  # not used
            y_data_dim=0,  # y dimension
            x_label="z",
            y_label="y",
            x_units="",
            y_units="pixel",
            line_angle=0,  # horizontal line (in z-y space)
            swap_plot_coords=True  # setData(data, y_indices)
        )
    
    @staticmethod
    def spectrum_image_window_default() -> AxisConfig:
        """Config for StokesSpectrumImageWindow - default orientation (spectator_viewer).
        
        Data: 2D image (spectral, x)
        Plot: x-axis shows spectral, y-axis shows spatial_x
        For spectator_viewer compatibility
        """
        return AxisConfig(
            x_axis_source='index',
            y_axis_source='index',
            x_data_dim=0,  # spectral dimension
            y_data_dim=1,  # spatial_x dimension
            x_label="λ",
            y_label="x",
            x_units="pixel",
            y_units="pixel",
            line_angle=None,  # image window, no draggable line
            swap_plot_coords=False
        )
    
    @staticmethod
    def spectrum_image_window_swapped() -> AxisConfig:
        """Config for StokesSpectrumImageWindow - swapped orientation (scan_viewer).
        
        Data: 2D image (spectral, x)
        Plot: x-axis shows spatial_x, y-axis shows spectral
        For scan_viewer to match scan window orientation
        """
        return AxisConfig(
            x_axis_source='index',
            y_axis_source='index',
            x_data_dim=1,  # spatial_x dimension on x-axis
            y_data_dim=0,  # spectral dimension on y-axis
            x_label="x",
            y_label="λ",
            x_units="pixel",
            y_units="pixel",
            line_angle=None,  # image window, no draggable line
            swap_plot_coords=False
        )
