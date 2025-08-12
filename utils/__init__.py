"""
Utilities package for the spectral data viewer.

This package contains utility functions, constants, and helper classes
organized by functionality.
"""

# Constants and configuration
from .constants import (
    MIN_LINE_DISTANCE,
    DEFAULT_N_STOKES, DEFAULT_N_WL, DEFAULT_N_X, 
    DEFAULT_LINE_WIDTH, ColorSchemes, GrayPalette, BluePalette,
    SUPPORTED_VIEWER_TYPES, MAX_STATES, MAX_SPATIAL_AXES
)

# Plotting utilities
from .plotting import (
    add_line, add_crosshair, create_histogram,
    initialize_image_plot_item, initialize_spectrum_plot_item,
    set_plot_wavelength_range, reset_plot_wavelength_range,
    update_crosshair_from_mouse, create_wavelength_limit_controls,
    create_y_limit_controls, apply_dark_theme, apply_light_theme
)

# Data utilities
from .data_utils import (
    generate_example_data, validate_data_array
)

# Color utilities
from .colors import getWidgetColors
# Legacy crosshair colors function removed - use getWidgetColors() instead

# Legacy compatibility aliases
AddLine = add_line
AddCrosshair = add_crosshair
CreateHistrogram = create_histogram
CreateWlLimitLabel = create_wavelength_limit_controls
CreateYLimitLabel = create_y_limit_controls
SetPlotXlamRange = set_plot_wavelength_range
ResetPlotXlamRange = reset_plot_wavelength_range
update_crosshair_from_mouse = update_crosshair_from_mouse
ExampleData = generate_example_data
InitializeImageplotItem = initialize_image_plot_item
InitializeSpectrumplotItem = initialize_spectrum_plot_item

__all__ = [
    # Constants
    'MIN_LINE_DISTANCE',
    'DEFAULT_N_STOKES', 'DEFAULT_N_WL', 'DEFAULT_N_X', 'DEFAULT_WAVELENGTH_RANGE',
    'DEFAULT_LINE_WIDTH', 'ColorSchemes', 'GrayPalette', 'BluePalette',
    'SUPPORTED_VIEWER_TYPES', 'MAX_STATES', 'MAX_SPATIAL_AXES',
    
    # Plotting utilities
    'add_line', 'add_crosshair', 'create_histogram',
    'initialize_image_plot_item', 'initialize_spectrum_plot_item',
    'set_plot_wavelength_range', 'reset_plot_wavelength_range',
    'update_crosshair_from_mouse', 'create_wavelength_limit_controls',
    'create_y_limit_controls', 'apply_dark_theme', 'apply_light_theme',
    
    # Data utilities
    'generate_example_data', 'validate_data_array', 'validate_data', 'normalize_data',
    'calculate_statistics', 'resample_data', 'extract_spectral_line',
    'apply_spectral_smoothing', 'detect_spectral_lines',
    
    # Color utilities
    'getWidgetColors', 'get_crosshair_colors',
    
    # Legacy compatibility
    'AddLine', 'AddCrosshair', 'CreateHistrogram', 'CreateWlLimitLabel',
    'CreateYLimitLabel', 'SetPlotXlamRange', 'ResetPlotXlamRange',
    'ExampleData', 'InitializeImageplotItem', 'InitializeSpectrumplotItem'
]
