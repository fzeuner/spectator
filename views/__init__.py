"""
Views package for the spectral data viewer.

This package contains all UI components organized by functionality.
"""

# Base widgets
from .base_widgets import BasePlotWidget, BaseControlWidget, BaseImageWidget

# Spectrum widgets
from .spectrum_widgets import SpectrumPlotWidget, SpectrumImageWidget

# Spatial widgets
from .spatial_widgets import SpatialPlotWidget

# Control widgets
from .control_widgets import (
    LinesControlGroup, SpectrumLimitControlGroup, PlotControlWidget
)

__all__ = [
    # Base widgets
    'BasePlotWidget',
    'BaseControlWidget', 
    'BaseImageWidget',
    
    # Spectrum widgets
    'SpectrumPlotWidget',
    'SpectrumImageWidget',
    
    # Spatial widgets
    'SpatialPlotWidget',
    
    # Control widgets
    'LinesControlGroup',
    'SpectrumLimitControlGroup',
    'PlotControlWidget'
]
