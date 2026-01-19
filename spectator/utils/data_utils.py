"""
Data utilities for the spectral data viewer.

This module contains helper functions for data generation, validation,
and transformation operations.
"""

import numpy as np
from typing import Tuple, Optional, List, Union
from .constants import DEFAULT_N_STOKES, DEFAULT_N_WL, DEFAULT_N_X


def generate_example_data_3d(n_stokes: int = DEFAULT_N_STOKES,
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

def generate_example_data_4d():
    S, L, Y, X = 2, 100, 40, 80
    rng = np.random.default_rng(0)
    data = rng.normal(scale=0.05, size=(S, L, Y, X)).astype(float)
    # Axes
    x = np.linspace(-1, 1, X)        # spatial_x
    y = np.linspace(-1, 1, Y)        # spatial_y
    lam = np.linspace(400, 800, L)   # spectral (wavelength)
    # Spatial 2D Gaussian bump in (y, x)
    Xg, Yg = np.meshgrid(x, y, indexing="xy")      # shapes (Y, X)
    spatial_bump = np.exp(-(Xg**2 + Yg**2) / (2 * 0.3**2))  # (Y, X)
    # Spectral Gaussian line profile in λ
    line_profile = np.exp(-((lam - 600.0) ** 2) / (2 * 30.0**2))  # (L,)
    # Outer product to get (L, Y, X)
    feature = line_profile[:, None, None] * spatial_bump[None, :, :]  # (L, Y, X)
    # Add feature to each state with different scaling
    for s in range(S):
        data[s] += (1.0 + 0.5 * s) * feature

    return data