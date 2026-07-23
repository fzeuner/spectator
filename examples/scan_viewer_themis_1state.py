#!/usr/bin/env python3
import numpy as np
from spectator.controllers.app_controller import display_data


def main():
    data = np.load('/home/franziskaz/data/testdata.npy')
    data=data[0,:]
    # Launch viewer
    win = display_data(
        data,
        order=['spatial_y',  'spatial_x', 'spectral',],
        title='Scan Viewer Example 1 state',
        rearrange=True
    )
if __name__ == '__main__':
    main()
