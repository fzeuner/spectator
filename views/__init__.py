"""
Views package for the spectral data viewer.

This package contains all UI components organized by functionality.
"""

# Base widgets
from .base_widgets import BasePlotWidget, BaseControlWidget, BaseImageWidget, CustomVerticalLabel

# Spectrum/Spatial widgets removed (legacy modules)

# Control widgets
from .control_widgets import (
    LinesControlGroup, SpectrumLimitControlGroup, PlotControlWidget
)

__all__ = [
    # Base widgets
    'BasePlotWidget',
    'BaseControlWidget', 
    'BaseImageWidget',
    'CustomVerticalLabel',
    
    # (legacy Spectrum/Spatial widgets removed)
    
    # Control widgets
    'LinesControlGroup',
    'SpectrumLimitControlGroup',
    'PlotControlWidget'
]
