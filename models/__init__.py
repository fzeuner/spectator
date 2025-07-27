"""
Models package for the spectral data viewer.

This package contains all data models and configuration classes.
"""

from .data_model import SpectralData, AxisType, AxisConfiguration
from .spectrum_model import (
    SpectrumImageData, SpatialData, SpectrumData,
    CrosshairState, AveragingRegion
)
from .viewer_config import (
    ViewerSettings, ViewerType, ColorScheme, PlotConfiguration,
    PlotLimits, SynchronizationSettings,
    get_default_crosshair_colors, get_default_averaging_colors,
    get_default_min_line_distance
)

__all__ = [
    # Core data models
    'SpectralData',
    'AxisType', 
    'AxisConfiguration',
    
    # Spectrum-specific models
    'SpectrumImageData',
    'SpatialData',
    'SpectrumData',
    'CrosshairState',
    'AveragingRegion',
    
    # Configuration models
    'ViewerSettings',
    'ViewerType',
    'ColorScheme',
    'PlotConfiguration',
    'PlotLimits',
    'SynchronizationSettings',
    
    # Convenience functions
    'get_default_crosshair_colors',
    'get_default_averaging_colors',
    'get_default_min_line_distance'
]
