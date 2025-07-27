"""
Data utilities for the spectral data viewer.

This module contains helper functions for data generation, validation,
and transformation operations.
"""

import numpy as np
from typing import Tuple, Optional, List, Union
from .constants import DEFAULT_N_STOKES, DEFAULT_N_WL, DEFAULT_N_X


def generate_example_data(n_stokes: int = DEFAULT_N_STOKES,
                         n_wl: int = DEFAULT_N_WL, 
                         n_x: int = DEFAULT_N_X,
                         add_noise: bool = True,
                         noise_level: float = 0.1) -> np.ndarray:
    """
    Generate example Stokes spectropolarimetric data with defined structure.
    
    Args:
        n_stokes: Number of Stokes parameters
        n_wl: Number of spectral points
        n_x: Number of spatial points
        add_noise: Whether to add random noise
        noise_level: Relative noise level (0.0 to 1.0)
        
    Returns:
        Stokes data cube of shape (n_stokes, n_wl, n_x)
    """
    # Initialize data with random noise using actual parameters
    data = np.random.random(size=(n_stokes, n_wl, n_x)) * 5

    # Define Gaussian parameters for Stokes I
    center_wl, center_x = n_wl // 2, n_x // 2
    width_wl, width_x = n_wl // 10, n_x // 8

    # Create 2D spatial Gaussian and add to Stokes I
    yy, xx = np.mgrid[:n_wl, :n_x]
    spatial_gaussian = np.exp(-(((xx - center_x) / width_x) ** 2) / 2)
    data[0] += 100000 * spatial_gaussian

    # Create 1D spectral Gaussian and apply to Stokes I
    spectral_gaussian = np.exp(-((np.arange(n_wl) - center_wl) / width_wl) ** 2 / 2)
    data[0] *= spectral_gaussian[:, np.newaxis]
    # Only add to second Stokes parameter if it exists
    if n_stokes > 1:
        data[1, center_wl, center_x - 5 : center_x + 5] += 3
        data[1] *= 0.0000001
    # Add noise if requested
        if add_noise and noise_level > 0:
            noise = np.random.normal(0, noise_level * np.mean(data[1]), data.shape)
            data += noise
    
    return data


def validate_data_array(data: np.ndarray, 
                       min_dim: int = 1, 
                       max_dim: int = 5) -> tuple:
    """
    Validate that a data array meets basic requirements.
    
    Args:
        data: Data array to validate
        min_dim: Minimum allowed dimensions
        max_dim: Maximum allowed dimensions
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(data, np.ndarray):
        return False, "Data must be a numpy array"
    
    if data.ndim < min_dim or data.ndim > max_dim:
        return False, f"Data must have between {min_dim} and {max_dim} dimensions, got {data.ndim}"
    
    if data.size == 0:
        return False, "Data array is empty"
    
    if not np.isfinite(data).all():
        return False, "Data contains non-finite values (NaN or Inf)"
    
    return True, "Data is valid"

