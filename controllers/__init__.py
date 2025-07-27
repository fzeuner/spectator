"""
Controllers package for the data viewer.

This package contains all business logic controllers that coordinate
between models and views in the MVC architecture.
"""

# Main application controller
from .app_controller import Manager

# Sub-controllers
from .viewers import spectator
from .file_controllers import FileLoadingController, FileListingController

__all__ = [
    'Manager',
    'spectator',
    'FileLoadingController',
    'FileListingController'
]
