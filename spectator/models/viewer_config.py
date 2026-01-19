"""
Configuration defaults for the spectral data viewer.
"""

from typing import Dict


# Default color settings
_DEFAULT_CROSSHAIR_COLORS = {
    'v': 'white',
    'h_image': 'dodgerblue',
    'h_spectrum_image': 'white'
}

_DEFAULT_AVERAGING_COLORS = ['dodgerblue', 'yellow']

_DEFAULT_MIN_LINE_DISTANCE = 2.0


def get_default_crosshair_colors() -> Dict[str, str]:
    """Get default crosshair colors."""
    return _DEFAULT_CROSSHAIR_COLORS.copy()


def get_default_averaging_colors() -> list:
    """Get default averaging colors."""
    return _DEFAULT_AVERAGING_COLORS.copy()


def get_default_min_line_distance() -> float:
    """Get default minimum line distance."""
    return _DEFAULT_MIN_LINE_DISTANCE
