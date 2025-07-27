"""
Spectrum-specific data models for the spectral data viewer.

This module contains models for handling spectral image data, spatial profiles,
and related visualization state.
"""

import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class CrosshairState:
    """State information for crosshair position and visibility."""
    x_position: float = 0.0
    y_position: float = 0.0
    visible: bool = True
    locked: bool = False


@dataclass
class AveragingRegion:
    """Parameters for spectral averaging region."""
    left_limit: float
    center: float
    right_limit: float
    
    def __post_init__(self):
        """Validate averaging region parameters."""
        if self.left_limit >= self.right_limit:
            raise ValueError("Left limit must be less than right limit")
        
        expected_center = (self.left_limit + self.right_limit) / 2
        if abs(self.center - expected_center) > 1e-6:
            # Auto-correct center if it's slightly off
            self.center = expected_center
    
    @property
    def width(self) -> float:
        """Get the width of the averaging region."""
        return self.right_limit - self.left_limit
    
    def contains(self, value: float) -> bool:
        """Check if a value is within the averaging region."""
        return self.left_limit <= value <= self.right_limit


class SpectrumImageData:
    """
    Model for 2D spectral image data and associated metadata.
    
    Handles spectral-spatial data with spectral and spatial pixel arrays.
    """
    
    def __init__(self, data: np.ndarray, spectral_pixels: np.ndarray, 
                 spatial_pixels: np.ndarray, name: str = ""):
        """
        Initialize spectrum image data.
        
        Args:
            data: 2D array (spectral, spatial) 
            spectral_pixels: 1D array of spectral pixel indices
            spatial_pixels: 1D array of spatial pixel values
            name: Optional name for this data
        """
        self.data = data
        self.spectral_pixels = spectral_pixels
        self.spatial_pixels = spatial_pixels
        self.name = name
        
        self._validate_data()
        
        # State management
        self.crosshair = CrosshairState()
        self.averaging_region: Optional[AveragingRegion] = None
        
    def _validate_data(self):
        """Validate data dimensions and consistency."""
        if self.data.ndim != 2:
            raise ValueError(f"Data must be 2D, got {self.data.ndim}D")
        
        n_spectral, n_spatial = self.data.shape
        
        if len(self.spectral_pixels) != n_spectral:
            raise ValueError(f"Spectral pixel array length ({len(self.spectral_pixels)}) must match data spectral dimension ({n_spectral})")
        
        if len(self.spatial_pixels) != n_spatial:
            raise ValueError(f"Spatial pixel array length ({len(self.spatial_pixels)}) must match data spatial dimension ({n_spatial})")
    
    @property
    def shape(self) -> Tuple[int, int]:
        """Get data shape (n_spectral, n_spatial)."""
        return self.data.shape
    
    @property
    def n_spectral(self) -> int:
        """Number of spectral points."""
        return self.shape[0]
    
    @property
    def n_spatial(self) -> int:
        """Number of spatial points."""
        return self.shape[1]
    
    def get_spectrum_at_position(self, spatial_idx: int) -> np.ndarray:
        """Get spectrum at a specific spatial position."""
        if not 0 <= spatial_idx < self.n_spatial:
            raise IndexError(f"Spatial index {spatial_idx} out of range [0, {self.n_spatial-1}]")
        
        return self.data[:, spatial_idx]
    
    def get_spatial_slice_at_spectral(self, spectral_idx: int) -> np.ndarray:
        """Get spatial slice at a specific spectral position."""
        if not 0 <= spectral_idx < self.n_spectral:
            raise IndexError(f"Spectral index {spectral_idx} out of range [0, {self.n_spectral-1}]")
        
        return self.data[spectral_idx, :]
    
    def get_averaged_spectrum(self, spatial_range: Tuple[int, int]) -> np.ndarray:
        """Get spectrum averaged over a spatial range."""
        start_idx, end_idx = spatial_range
        if start_idx >= end_idx:
            raise ValueError("Start index must be less than end index")
        
        start_idx = max(0, start_idx)
        end_idx = min(self.n_spatial, end_idx)
        
        return np.mean(self.data[:, start_idx:end_idx], axis=1)
    
    def set_averaging_region(self, left: float, center: float, right: float):
        """Set the averaging region parameters."""
        self.averaging_region = AveragingRegion(left, center, right)
    
    def update_crosshair(self, x: float, y: float):
        """Update crosshair position."""
        self.crosshair.x_position = x
        self.crosshair.y_position = y


class SpatialData:
    """
    Model for 1D spatial profile data.
    
    Handles spatial intensity profiles and related visualization state.
    """
    
    def __init__(self, data: np.ndarray, spatial_pixels: np.ndarray, 
                 current_spectral_position: float = 0.0, name: str = ""):
        """
        Initialize spatial data.
        
        Args:
            data: 1D spatial intensity array
            spatial_pixels: 1D array of spatial pixel positions
            current_spectral_position: Current spectral position index
            name: Optional name for this data
        """
        self.data = data
        self.spatial_pixels = spatial_pixels
        self.current_spectral_position = current_spectral_position
        self.name = name
        
        self._validate_data()
        
        # State management
        self.crosshair = CrosshairState()
        
    def _validate_data(self):
        """Validate data dimensions and consistency."""
        if self.data.ndim != 1:
            raise ValueError(f"Data must be 1D, got {self.data.ndim}D")
        
        if len(self.data) != len(self.spatial_pixels):
            raise ValueError(f"Data length ({len(self.data)}) must match spatial pixels length ({len(self.spatial_pixels)})")
    
    @property
    def n_points(self) -> int:
        """Number of spatial points."""
        return len(self.data)
    
    def get_value_at_position(self, spatial_idx: int) -> float:
        """Get intensity value at a specific spatial position."""
        if not 0 <= spatial_idx < self.n_points:
            raise IndexError(f"Spatial index {spatial_idx} out of range [0, {self.n_points-1}]")
        
        return self.data[spatial_idx]
    
    def find_nearest_index(self, spatial_position: float) -> int:
        """Find the index of the nearest spatial position."""
        return np.argmin(np.abs(self.spatial_pixels - spatial_position))
    
    def update_data(self, new_data: np.ndarray, spectral_position: float):
        """Update the spatial data and spectral position."""
        if len(new_data) != self.n_points:
            raise ValueError(f"New data length ({len(new_data)}) must match existing length ({self.n_points})")
        
        self.data = new_data
        self.current_spectral_position = spectral_position
    
    def update_crosshair(self, position: float):
        """Update crosshair position."""
        self.crosshair.x_position = position


class SpectrumData:
    """
    Model for 1D spectrum data.
    
    Handles spectral intensity profiles and spectral pixel information.
    """
    
    def __init__(self, data: np.ndarray, spectral_pixels: np.ndarray, 
                 current_spatial_position: float = 0.0, name: str = ""):
        """
        Initialize spectrum data.
        
        Args:
            data: 1D spectral intensity array
            spectral_pixels: 1D array of spectral pixel indices
            current_spatial_position: Current spatial position
            name: Optional name for this data
        """
        self.data = data
        self.spectral_pixels = spectral_pixels
        self.current_spatial_position = current_spatial_position
        self.name = name
        
        self._validate_data()
        
        # State management
        self.crosshair = CrosshairState()
        self.averaging_region: Optional[AveragingRegion] = None
        
    def _validate_data(self):
        """Validate data dimensions and consistency."""
        if self.data.ndim != 1:
            raise ValueError(f"Data must be 1D, got {self.data.ndim}D")
        
        if len(self.data) != len(self.spectral_pixels):
            raise ValueError(f"Data length ({len(self.data)}) must match spectral pixels length ({len(self.spectral_pixels)})")
    
    @property
    def n_points(self) -> int:
        """Number of spectral points."""
        return len(self.data)
    
    def get_value_at_spectral(self, spectral_idx: int) -> float:
        """Get intensity value at a specific spectral index."""
        if not 0 <= spectral_idx < self.n_points:
            raise IndexError(f"Spectral index {spectral_idx} out of range [0, {self.n_points-1}]")
        
        return self.data[spectral_idx]
    
    def find_nearest_spectral_index(self, spectral_position: float) -> int:
        """Find the index of the nearest spectral position."""
        return np.argmin(np.abs(self.spectral_pixels - spectral_position))
    
    def get_averaged_value(self) -> float:
        """Get averaged value over the averaging region if set."""
        if self.averaging_region is None:
            return np.mean(self.data)
        
        # Find indices within averaging region
        mask = np.logical_and(
            self.spectral_pixels >= self.averaging_region.left_limit,
            self.spectral_pixels <= self.averaging_region.right_limit
        )
        
        if not np.any(mask):
            return np.nan
        
        return np.mean(self.data[mask])
    
    def update_data(self, new_data: np.ndarray, spatial_position: float):
        """Update the spectrum data and spatial position."""
        if len(new_data) != self.n_points:
            raise ValueError(f"New data length ({len(new_data)}) must match existing length ({self.n_points})")
        
        self.data = new_data
        self.current_spatial_position = spatial_position
    
    def set_averaging_region(self, left: float, center: float, right: float):
        """Set the averaging region parameters."""
        self.averaging_region = AveragingRegion(left, center, right)
    
    def update_crosshair(self, spectral_position: float):
        """Update crosshair position."""
        self.crosshair.x_position = spectral_position
