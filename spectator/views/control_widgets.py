"""
Control widget classes for the viewer.

This module contains control panels and UI controls for managing plot interactions,
synchronization, and settings.

This file now imports the split components from separate modules for better organization.
"""

# Import the split components
from .line_controls import LinesControlGroup
from .spectrum_limits import SpectrumLimitControlGroup
from .plot_controls import PlotControlWidget
from .file_controls import FilesControlWidget

__all__ = ['LinesControlGroup', 'SpectrumLimitControlGroup', 'PlotControlWidget', 'FilesControlWidget']
