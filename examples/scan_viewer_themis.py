#!/usr/bin/env python3
import numpy as np
from spectator.controllers.app_controller import display_data


def main():
    data = np.load('/home/zeuner/data/testdata.npy')

    # Launch viewer
    win = display_data(
        data,
        order=['states', 'spatial_y','spatial_x', 'spectral'],
        title='Scan Viewer Example',
        state_names=['I', 'Q', 'U', 'V'],
        rearrange=True
    )
if __name__ == '__main__':
    main()
