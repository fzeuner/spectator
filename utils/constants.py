"""
Constants and configuration values for the spectral data viewer.

This module contains all the constant values, color schemes, and configuration
parameters used throughout the application.
"""

from typing import Dict, List

# Color definitions for crosshairs and UI elements (moved to color schemes)

# Colors for averaging lines and regions (moved to color schemes)

# UI configuration constants
MIN_LINE_DISTANCE = 2.0  # Minimum pixel distance between averaging lines

# Default data generation parameters
DEFAULT_N_STOKES = 4
DEFAULT_N_WL = 250
DEFAULT_N_X = 150


# Plot styling constants
DEFAULT_LINE_WIDTH = 1.8
DEFAULT_CROSSHAIR_STYLE = 'DashLine'

# Font and sizing constants
DEFAULT_FONT_SIZE = '6pt'
DEFAULT_LABEL_SIZE = '8pt'

# Viewer configuration
SUPPORTED_VIEWER_TYPES = ['spectator', 'plot_1d', 'plot_2d', 'plot_4d', 'plot_5d']
MAX_STATES = 8
MAX_SPATIAL_AXES = 2

# Data validation constants
MIN_DATA_DIMENSION = 1
MAX_DATA_DIMENSION = 5
DEFAULT_DATA_TYPE = 'float64'

# UI layout constants
DEFAULT_DOCK_SIZE = (400, 300)
DEFAULT_WINDOW_SIZE = (1200, 800)
CONTROL_PANEL_SIZE = (130, 200)

# Color scheme definitions
class ColorSchemes:
    """Predefined color schemes for the application."""
    
    DARK_THEME = {
        'background': '#19232D',
        'foreground': '#FFFFFF',
        'accent': '#375A7F',
        'crosshair_v': 'white',
        'crosshair_h_image': 'dodgerblue',
        'crosshair_h_spectrum_image': 'white',
        'averaging_h': 'dodgerblue',
        'averaging_v': 'yellow'
    }
    
    LIGHT_THEME = {
        'background': '#FFFFFF',
        'foreground': '#000000',
        'accent': '#0078D4',
        'crosshair_v': 'black',
        'crosshair_h_image': 'blue',
        'crosshair_h_spectrum_image': 'black',
        'averaging_h': 'blue',
        'averaging_v': 'orange'
    }

# Gray color palette (from existing getWidgetColors.py)
class GrayPalette:
    """Gray color palette for UI theming."""
    B0 = '#000000'    # black
    B10 = '#19232D'   # dark-gray-blue
    B20 = '#293544'
    B30 = '#37414F'
    B40 = '#455364'
    B50 = '#54687A'
    B60 = '#60798B'
    B70 = '#788D9C'
    B80 = '#9DA9B5'
    B90 = '#ACB1B6'
    B100 = '#B9BDC1'
    B110 = '#C9CDD0'
    B120 = '#CED1D4'
    B130 = '#E0E1E3'
    B140 = '#FAFAFA'
    B150 = '#FFFFFF'

# Blue color palette (from existing getWidgetColors.py)
class BluePalette:
    """Blue color palette for UI theming."""
    B0 = '#000000'
    B10 = '#062647'
    B20 = '#26486B'
    B30 = '#375A7F'
    B40 = '#346792'
    B50 = '#1A72BB'
    B60 = '#057DCE'
    B70 = '#259AE9'
    B80 = '#37AEFE'
    B90 = '#73C7FF'
    B100 = '#9FCBFF'
    B110 = '#C2DFFA'
    B120 = '#CEE8FF'
    B130 = '#DAEDFF'
    B140 = '#F5FAFF'
    B150 = '#FFFFFF'

# Export commonly used constants
__all__ = [
    'MIN_LINE_DISTANCE',
    'DEFAULT_N_STOKES',
    'DEFAULT_N_WL', 
    'DEFAULT_N_X',
    'DEFAULT_LINE_WIDTH',
    'DEFAULT_CROSSHAIR_STYLE',
    'DEFAULT_FONT_SIZE',
    'DEFAULT_LABEL_SIZE',
    'SUPPORTED_VIEWER_TYPES',
    'MAX_STATES',
    'MAX_SPATIAL_AXES',
    'ColorSchemes',
    'GrayPalette',
    'BluePalette'
]
