#!/usr/bin/env python3
import os, sys
# Ensure project root is on sys.path when running this script directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from controllers.app_controller import display_data
from PyQt5 import QtWidgets


def main():
    # Synthetic 4D data: (states, spatial_y, spectral, spatial_x)
    S, Y, L, X = 2, 40, 100, 80
    rng = np.random.default_rng(0)
    data = rng.normal(scale=0.1, size=(S, Y, L, X)).astype(float)

    # Add smooth spectral feature that varies with x and y
    x = np.linspace(0, 2*np.pi, X)        # (X,)
    y = np.linspace(-1, 1, Y)            # (Y,)
    lam = np.linspace(400, 800, L)       # (L,)

    sinx = np.sin(x)                     # (X,)
    gauss = np.exp(-((lam-600.0)**2)/(2*40.0**2))  # (L,)
    yscale = 1 + 0.3*y                   # (Y,)

    # Proper outer-broadcast to (Y, L, X)
    feature = yscale[:, None, None] * gauss[None, :, None] * sinx[None, None, :]

    for s in range(S):
        data[s] += (1 + 0.5*s) * feature

    # Launch viewer
    win = display_data(
        data,
        'states', 'spatial', 'spectral', 'spatial',
        title='Scan Viewer Example',
        state_names=['I', 'Q']
    )
    # If a QApplication exists and we received a window (meaning the viewer didn't start its own loop), enter the event loop
    app = QtWidgets.QApplication.instance()
    if app is not None and win is not None:
        app.exec_()


if __name__ == '__main__':
    main()
