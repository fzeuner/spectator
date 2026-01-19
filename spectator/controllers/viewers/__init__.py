"""
Viewers package for the spectral data viewer.

This package contains viewer functions for different data dimensionalities.
"""

from .spectator_viewer import spectator
from .scan_viewer import scan_viewer

__all__ = ['spectator', 'scan_viewer']
