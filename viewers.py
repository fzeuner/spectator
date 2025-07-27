import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
import qdarkstyle
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from typing import List, Tuple, Dict, Optional, Any 
from functools import partial

from getWidgetColors import getWidgetColors

# local imports
import sys
sys.path.append(r"/home/zeuner/CascadeProjects/windsurf-project/")
from functions import *
from widgets import *

# --- Main Application Setup for 3D data ---

def spectator(data: np.ndarray, title: str = 'Data Viewer', state_names: List[str] = None):
    """
    Main function to create and display the interactive data viewer.

    Args:
        data: Numpy array of shape (N_Stokes, N_wl, N_x) containing Stokes data.
        title: Window title.
        state_names: List of names for the states (e.g., ['I', 'Q', 'U', 'V'])
    """  
    app = pg.mkQApp("Data viewer")
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1700, 800)
    win.setWindowTitle(title)
    
    # --- Generate state names ---
    if state_names is None:
        # Generate default numeric names
        STOKES_NAMES = [str(i+1) for i in range(data.shape[0])]
    else:
        STOKES_NAMES = state_names
    
    # --- Widget Initialization ---
    control_widget = PlotControlWidget() # Create control widget first

    spectra: List[StokesSpectrumWindow] = []
    image_spectra: List[StokesSpectrumImageWindow] = []
    spatial: List[StokesSpatialWindow] = []
    docks: Dict[str, Dict[str, Dock]] = {"spectrum": {}, "spec_img": {}, "spatial": {}} # Store docks by type and name

     # --- Create Widgets and Docks in a Loop ---
    for i, name in enumerate(STOKES_NAMES):
         base_name = name # dock names
         stokes_data_y_wl_x = data[i, :, :] # Shape ( wl, x)

         # Create Widgets for this Stokes parameter
         initial_spec_img_data = data[i, :, :] 

         win_spectrum = StokesSpectrumWindow(stokes_data_y_wl_x, stokes_index=i, name=base_name)
         win_image_spectrum = StokesSpectrumImageWindow(initial_spec_img_data, stokes_index=i, name=base_name)
         win_spatial = StokesSpatialWindow(initial_spec_img_data, stokes_index=i, name=base_name)

         # Append to lists
         spectra.append(win_spectrum)
         image_spectra.append(win_image_spectrum)
         spatial.append(win_spatial)
         
         # Create Docks
         spectrum_dock = Dock(f"{base_name} spectrum", size=(350, 150))
         spectrum_image_dock = Dock(f"{base_name} spectrum image", size=(350, 150))
         spatial_dock = Dock(f"{base_name} spatial", size=(250, 150))

         # Add Widgets to Docks
         spectrum_dock.addWidget(win_spectrum)
         spectrum_image_dock.addWidget(win_image_spectrum)
         spatial_dock.addWidget(win_spatial)

         # Store Docks
         docks["spectrum"][base_name] = spectrum_dock
         docks["spec_img"][base_name] = spectrum_image_dock
         docks["spatial"][base_name] = spatial_dock

    # Update control widget with the created image and spectrum widgets
    control_widget.init_spectrum_limit_controls(spectra, image_spectra, spatial) # Now initialize UI for limits
       
    # --- Create Control and Data Docks ---
    control_dock = Dock("Control", size=(70,1000))
    data_dock = Dock("Data", size=(70,1000))
    
    # --- Arrange Docks in the DockArea ---
    
    for i, name in enumerate(STOKES_NAMES):
        base_name = name.split('/')[0]
        if name == STOKES_NAMES[0]: # first one always on the left
            area.addDock(docks["spec_img"][base_name], 'left')
        else:
            area.addDock(docks["spec_img"][base_name], 'bottom', docks["spec_img"][STOKES_NAMES[i-1].split('/')[0]])
    
    # Middle Column: Spectrum Images and Spectra
 
    for i, name in enumerate(STOKES_NAMES):
         base_name = name.split('/')[0]
         # Add spectrum and spatial
         area.addDock(docks["spectrum"][base_name], 'right', docks["spec_img"][base_name])
         area.addDock(docks["spatial"][base_name], 'right', docks["spectrum"][base_name])

    # Bottom Row: Average Spectrum
    area.addDock(data_dock, 'right')
    area.addDock(control_dock, 'above', data_dock)

    # Control widget
    control_dock.addWidget(control_widget)
    #data_dock.addWidget()
    
    # --- Connect Signals in a Loop ---

    for i in range(len(image_spectra)):        
        image_spectra[i].crosshairMoved.connect(control_widget.handle_crosshair_movement)
        image_spectra[i].avgRegionChanged.connect(control_widget.handle_v_avg_line_movement)
        
        # Enhanced crosshair synchronization: connect spectrum image to spatial window
        if i < len(spatial):
            # Connect crosshair movement to update spatial window
            image_spectra[i].crosshairMoved.connect(spatial[i].update_from_spectrum_crosshair)
            # Connect spatial horizontal line movement back to spectrum image
            spatial[i].hLineChanged.connect(image_spectra[i].update_horizontal_crosshair)
    
    # Connect the xlamRangeChanged signal 

    for spectrum_widget in spectra:
        control_widget.xlamRangeChanged.connect(spectrum_widget.update_spectral_range)
        control_widget.resetXlamRangeRequested.connect(spectrum_widget.reset_spectral_range)
        
    for image_spectrum_widget in image_spectra:
        control_widget.xlamRangeChanged.connect(image_spectrum_widget.update_spectral_range)
        control_widget.resetXlamRangeRequested.connect(image_spectrum_widget.reset_spectral_range)

    # --- Show Window and Run App ---
    win.show()
    try:
        # Use environment variable or default to dark style
        dark_stylesheet = qdarkstyle.load_stylesheet_from_environment(is_pyqtgraph=True)
        app.setStyleSheet(dark_stylesheet)
    except ImportError:
        print("qdarkstyle not found. Using default Qt style.")
    except Exception as e:
        print(f"Could not apply qdarkstyle: {e}")

    sys.exit(app.exec_()) # Use sys.exit for proper exit codes
