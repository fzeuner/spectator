"""
Color utilities and theme management for the spectral data viewer.

This module provides color schemes, theme management, and color utility functions
for consistent styling across the application.
"""

from typing import Dict
from .constants import ColorSchemes


def get_widget_colors(theme: str = 'dark') -> Dict[str, str]:
    """Get widget colors for the specified theme."""
    color_schemes = {
        'dark': ColorSchemes.DARK_THEME,
        'light': ColorSchemes.LIGHT_THEME
    }
    return color_schemes.get(theme, color_schemes['dark'])

def getWidgetColors(theme: str = 'dark') -> Dict[str, str]:
    """Get widget colors for the specified theme."""
    return get_widget_colors(theme)


# Export commonly used functions
__all__ = [
    'getWidgetColors'
]
