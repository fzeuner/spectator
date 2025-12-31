#!/usr/bin/env python3
import os, sys
# Ensure project root is on sys.path when running this script directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from controllers.app_controller import display_data


def main():
# Synthetic 4D data: (states, spectral, spatial_y, spatial_x)
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

    # Launch viewer
    win = display_data(
        data,
        order=['states', 'spectral', 'spatial', 'spatial'],
        title='Scan Viewer Example',
        state_names=['I', 'Q'],
        rearrange=True
    )
if __name__ == '__main__':
    main()
