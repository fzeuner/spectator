"""
Configuration models for the spectral data viewer.

This module contains configuration classes for viewer settings, plot parameters,
and UI preferences.
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ViewerType(Enum):
    """Enumeration of available viewer types."""
    PLOT_1D = "plot_1d"
    PLOT_2D = "plot_2d" 
    SPECTATOR = "spectator"
    PLOT_4D = "plot_4d"
    PLOT_5D = "plot_5d"


@dataclass
class ColorScheme:
    """Color scheme configuration for the viewer."""
    crosshair_vertical: str = 'white'
    crosshair_horizontal_image: str = 'dodgerblue'
    crosshair_horizontal_spectrum: str = 'white'
    averaging_primary: str = 'dodgerblue'
    averaging_secondary: str = 'yellow'
    background_normal: str = '#2b2b2b'
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format."""
        return {
            'v': self.crosshair_vertical,
            'h_image': self.crosshair_horizontal_image,
            'h_spectrum_image': self.crosshair_horizontal_spectrum
        }


@dataclass
class PlotLimits:
    """Plot axis limits configuration."""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    auto_range: bool = True
    padding: float = 0.0
    
    def is_valid(self) -> bool:
        """Check if limits are valid."""
        if self.min_value is not None and self.max_value is not None:
            return self.min_value < self.max_value
        return True
    
    def get_range(self) -> Optional[Tuple[float, float]]:
        """Get the range as a tuple if both limits are set."""
        if self.min_value is not None and self.max_value is not None:
            return (self.min_value, self.max_value)
        return None


@dataclass
class SynchronizationSettings:
    """Settings for plot synchronization."""
    crosshair_sync: bool = False
    averaging_y_sync: bool = False
    averaging_x_sync: bool = False
    axis_limits_sync: bool = False


@dataclass
class PlotConfiguration:
    """Configuration for individual plot settings."""
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    x_units: str = ""
    y_units: str = ""
    x_limits: PlotLimits = field(default_factory=PlotLimits)
    y_limits: PlotLimits = field(default_factory=PlotLimits)
    show_grid: bool = True
    show_crosshair: bool = True
    show_averaging_lines: bool = True
    
    def update_limits(self, axis: str, min_val: float, max_val: float, auto_range: bool = False):
        """Update axis limits."""
        limits = PlotLimits(min_val, max_val, auto_range)
        if axis.lower() == 'x':
            self.x_limits = limits
        elif axis.lower() == 'y':
            self.y_limits = limits
        else:
            raise ValueError(f"Invalid axis: {axis}. Must be 'x' or 'y'")


class ViewerSettings:
    """
    Main configuration class for viewer settings and preferences.
    """
    
    # Default configurations for different viewer types
    DEFAULT_CONFIGS = {
        ViewerType.SPECTATOR: {
            'spectrum_image': PlotConfiguration(
                title="Spectrum Image",
                x_label="Wavelength",
                y_label="Spatial Position",
                x_units="Å",
                y_units="pixels"
            ),
            'spectrum': PlotConfiguration(
                title="Spectrum",
                x_label="Wavelength", 
                y_label="Intensity",
                x_units="Å",
                y_units="counts"
            ),
            'spatial': PlotConfiguration(
                title="Spatial Profile",
                x_label="Spatial Position",
                y_label="Intensity", 
                x_units="pixels",
                y_units="counts"
            )
        }
    }
    
    def __init__(self, viewer_type: ViewerType = ViewerType.SPECTATOR):
        """
        Initialize viewer settings.
        
        Args:
            viewer_type: Type of viewer to configure
        """
        self.viewer_type = viewer_type
        self.color_scheme = ColorScheme()
        self.synchronization = SynchronizationSettings()
        
        # Load default plot configurations
        self.plot_configs: Dict[str, PlotConfiguration] = {}
        if viewer_type in self.DEFAULT_CONFIGS:
            self.plot_configs = self.DEFAULT_CONFIGS[viewer_type].copy()
        
        # General settings
        self.window_title = "Spectral Data Viewer"
        self.use_dark_theme = True
        self.min_line_distance = 2.0  # Minimum distance between averaging lines
        self.default_font_size = '6pt'
        
        # Viewer-specific settings
        self.dock_area_settings = {
            'spectrum_image_size': (400, 300),
            'spectrum_size': (400, 200),
            'spatial_size': (400, 200),
            'controls_size': (200, 400)
        }
    
    def get_plot_config(self, plot_name: str) -> PlotConfiguration:
        """Get configuration for a specific plot."""
        if plot_name not in self.plot_configs:
            # Return default configuration
            return PlotConfiguration(title=plot_name.replace('_', ' ').title())
        return self.plot_configs[plot_name]
    
    def set_plot_config(self, plot_name: str, config: PlotConfiguration):
        """Set configuration for a specific plot."""
        self.plot_configs[plot_name] = config
    
    def update_color_scheme(self, **colors):
        """Update color scheme with new colors."""
        for key, value in colors.items():
            if hasattr(self.color_scheme, key):
                setattr(self.color_scheme, key, value)
    
    def enable_synchronization(self, sync_type: str, enabled: bool = True):
        """Enable or disable a specific type of synchronization."""
        if hasattr(self.synchronization, sync_type):
            setattr(self.synchronization, sync_type, enabled)
        else:
            raise ValueError(f"Unknown synchronization type: {sync_type}")
    
    def get_crosshair_colors(self) -> Dict[str, str]:
        """Get crosshair colors in the format expected by widgets."""
        return {
            'v': self.color_scheme.crosshair_vertical,
            'h_image': self.color_scheme.crosshair_horizontal_image,
            'h_spectrum_image': self.color_scheme.crosshair_horizontal_spectrum
        }
    
    def get_averaging_colors(self) -> list:
        """Get averaging colors in the format expected by widgets."""
        return [
            self.color_scheme.averaging_primary,
            self.color_scheme.averaging_secondary
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for serialization."""
        return {
            'viewer_type': self.viewer_type.value,
            'color_scheme': {
                'crosshair_vertical': self.color_scheme.crosshair_vertical,
                'crosshair_horizontal_image': self.color_scheme.crosshair_horizontal_image,
                'crosshair_horizontal_spectrum': self.color_scheme.crosshair_horizontal_spectrum,
                'averaging_primary': self.color_scheme.averaging_primary,
                'averaging_secondary': self.color_scheme.averaging_secondary,
                'background_normal': self.color_scheme.background_normal
            },
            'synchronization': {
                'crosshair_sync': self.synchronization.crosshair_sync,
                'averaging_y_sync': self.synchronization.averaging_y_sync,
                'averaging_x_sync': self.synchronization.averaging_x_sync,
                'axis_limits_sync': self.synchronization.axis_limits_sync
            },
            'window_title': self.window_title,
            'use_dark_theme': self.use_dark_theme,
            'min_line_distance': self.min_line_distance,
            'default_font_size': self.default_font_size,
            'dock_area_settings': self.dock_area_settings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ViewerSettings':
        """Create settings from dictionary."""
        viewer_type = ViewerType(data.get('viewer_type', ViewerType.SPECTATOR.value))
        settings = cls(viewer_type)
        
        # Update color scheme
        if 'color_scheme' in data:
            for key, value in data['color_scheme'].items():
                if hasattr(settings.color_scheme, key):
                    setattr(settings.color_scheme, key, value)
        
        # Update synchronization settings
        if 'synchronization' in data:
            for key, value in data['synchronization'].items():
                if hasattr(settings.synchronization, key):
                    setattr(settings.synchronization, key, value)
        
        # Update other settings
        settings.window_title = data.get('window_title', settings.window_title)
        settings.use_dark_theme = data.get('use_dark_theme', settings.use_dark_theme)
        settings.min_line_distance = data.get('min_line_distance', settings.min_line_distance)
        settings.default_font_size = data.get('default_font_size', settings.default_font_size)
        settings.dock_area_settings = data.get('dock_area_settings', settings.dock_area_settings)
        
        return settings


# Convenience functions for backward compatibility
def get_default_crosshair_colors() -> Dict[str, str]:
    """Get default crosshair colors."""
    return ViewerSettings().get_crosshair_colors()


def get_default_averaging_colors() -> list:
    """Get default averaging colors."""
    return ViewerSettings().get_averaging_colors()


def get_default_min_line_distance() -> float:
    """Get default minimum line distance."""
    return ViewerSettings().min_line_distance
