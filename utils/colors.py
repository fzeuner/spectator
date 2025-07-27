"""
Color utilities and theme management for the spectral data viewer.

This module provides color schemes, theme management, and color utility functions
for consistent styling across the application.
"""

from typing import Dict
from .constants import ColorSchemes


# Legacy compatibility function (replaces getWidgetColors functionality)
def getWidgetColors(theme: str = 'dark') -> Dict[str, str]:
    """
    Get widget colors for backward compatibility.
    
    Args:
        theme: Theme name
        
    Returns:
        Dictionary of color mappings
    """
    color_schemes = {
        'dark': ColorSchemes.DARK_THEME,
        'light': ColorSchemes.LIGHT_THEME
    }
    return color_schemes.get(theme, color_schemes['dark'])


# Export commonly used functions
__all__ = [
    'getWidgetColors'
]
