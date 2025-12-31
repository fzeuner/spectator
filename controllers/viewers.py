import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
import qdarkstyle
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from utils.constants import CONTROL_PANEL_SIZE, get_initial_window_size
from utils.fixed_dock_label import FixedDockLabel
from typing import List, Dict, Any 
 

# local imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Note: Models import removed; unused in this controller
from views import (
    PlotControlWidget
)
from views.windows import (
    StokesSpectrumWindow, StokesSpectrumImageWindow, StokesSpatialWindow, StokesImageWindow
)
 
# --- Main Application Setup for 3D data ---

def spectator(data: np.ndarray, title: str = 'spectator', state_names: List[str] = None):
    """
    Main function to create and display the interactive data viewer.

    Args:
        data: Numpy array of shape (N_Stokes, N_wl, N_x) containing Stokes data.
        title: Window title.
        state_names: List of names for the states (e.g., ['I', 'Q', 'U', 'V'])
    """  
    # Use existing QApplication if present, otherwise create one
    app = QtWidgets.QApplication.instance()
    created_app = False
    if app is None:
        app = pg.mkQApp(title)
        created_app = True
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    # Centralized initial size
    w, h = get_initial_window_size(app, env_var='SPECTATOR_WINDOW')
    win.resize(w, h)
    win.setWindowTitle(title)
    
    # --- Generate state names ---
    if state_names is None:
        # Generate default numeric names
        STOKES_NAMES = [str(i+1) for i in range(data.shape[0])]
    else:
        STOKES_NAMES = state_names
    
    # --- Widget Initialization ---
    control_widget = PlotControlWidget() # Create control widget first
        
    # External callers can invoke update_spectator_data(...) programmatically
    spectra: List[Any] = []
    image_spectra: List[Any] = []
    spatial: List[Any] = []
    docks: Dict[str, Dict[str, Dock]] = {"spectrum": {}, "spec_img": {}, "spatial": {}} # Store docks by type and name

    # --- Create Widgets and Docks in a Loop ---
    for i, name in enumerate(STOKES_NAMES):
        base_name = name  # dock names
        stokes_data_wl_x = data[i, :, :]  # Per-state 2D data: shape (wl, x)

        # Create Widgets for this Stokes parameter (all consume (wl, x))
        win_spectrum = StokesSpectrumWindow(stokes_data_wl_x, stokes_index=i, name=base_name)
        win_image_spectrum = StokesSpectrumImageWindow(stokes_data_wl_x, stokes_index=i, name=base_name)
        win_spatial = StokesSpatialWindow(stokes_data_wl_x, stokes_index=i, name=base_name)

        # Append to lists
        spectra.append(win_spectrum)
        image_spectra.append(win_image_spectrum)
        spatial.append(win_spatial)
         
        # Initialize spectrum window profile from the image window's current horizontal crosshair (x position)
        try:
            if hasattr(win_image_spectrum, 'hLine'):
                x_pos = float(win_image_spectrum.hLine.value())
                n_x = win_spectrum.full_data.shape[1]
                x_idx = int(np.clip(np.round(x_pos), 0, n_x - 1))
                win_spectrum.update_spectrum_data(x_idx)
        except Exception as e:
            print(f"Warning: could not initialize spectrum window from crosshair: {e}")

        # Create Docks (spectrum clearly wider than spatial)
        spectrum_dock = Dock(
            f"{base_name} spectrum",
            size=(600, 260),
            label=FixedDockLabel(f"{base_name} spectrum"),
        )
        spectrum_image_dock = Dock(
            f"{base_name} spectrum image",
            size=(800, 540),
            label=FixedDockLabel(f"{base_name} spectrum image"),
        )
        spatial_dock = Dock(
            f"{base_name} spatial",
            size=(360, 240),
            label=FixedDockLabel(f"{base_name} spatial"),
        )

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
       
    # --- Create Control Dock ---
    control_dock = Dock(
        "Control",
        size=(int(CONTROL_PANEL_SIZE[0] * 1.5), CONTROL_PANEL_SIZE[1]),
        label=FixedDockLabel("Control"),
    )
    
    # --- Arrange Docks in the DockArea ---
    
    for i, name in enumerate(STOKES_NAMES):
        base_name = name
        if name == STOKES_NAMES[0]: # first one always on the left
            area.addDock(docks["spec_img"][base_name], 'left')
        else:
            area.addDock(docks["spec_img"][base_name], 'bottom', docks["spec_img"][STOKES_NAMES[i-1].split('/')[0]])
    
    # Middle Column: Spectrum Images and Spectra
 
    for i, name in enumerate(STOKES_NAMES):
         base_name = name
         # Add spectrum and spatial
         area.addDock(docks["spectrum"][base_name], 'right', docks["spec_img"][base_name])
         area.addDock(docks["spatial"][base_name], 'right', docks["spectrum"][base_name])

    area.addDock(control_dock, 'right')

    # Control widget
    # Ensure control panel has a reasonable minimum width (~1.5x)
    try:
        control_widget.setMinimumWidth(int(CONTROL_PANEL_SIZE[0] * 1.5))
    except Exception:
        pass
    control_dock.addWidget(control_widget)
    
    # --- Connect Signals in a Loop ---

    for i in range(len(image_spectra)):        
        image_spectra[i].crosshairMoved.connect(control_widget.handle_crosshair_movement)
        
        # Always forward avg movements so the local windows update regardless of sync state
        image_spectra[i].avgRegionChanged.connect(control_widget.handle_v_avg_line_movement)
        if i < len(spectra):
            image_spectra[i].spatialAvgRegionChanged.connect(spectra[i].handle_spatial_avg_line_movement)
        if i < len(spatial):
            image_spectra[i].avgRegionChanged.connect(spatial[i].handle_spectral_avg_line_movement)
        
        # Connect spatial averaging to control widget for synchronization
        image_spectra[i].spatialAvgRegionChanged.connect(control_widget.handle_spatial_avg_line_movement)
        
        # Connect spectral averaging control signal
        control_widget.lines_content_widget.spectralAveragingEnabled.connect(image_spectra[i].set_spectral_averaging_enabled)
        
        # Connect averaging removal signals
        control_widget.lines_content_widget.toggleAvgXRemove.connect(image_spectra[i].remove_spectral_averaging)
        control_widget.lines_content_widget.toggleAvgYRemove.connect(image_spectra[i].remove_spatial_averaging)
        
        # Connect default averaging creation signals
        control_widget.lines_content_widget.createDefaultSpectralAveraging.connect(image_spectra[i].create_default_spectral_averaging)
        control_widget.lines_content_widget.createDefaultSpatialAveraging.connect(image_spectra[i].create_default_spatial_averaging)
        
        # Set control widget reference for button activation
        image_spectra[i].control_widget = control_widget.lines_content_widget
        # Wire manager callbacks now that control_widget is available
        if hasattr(image_spectra[i], 'spectral_manager'):
            image_spectra[i].spectral_manager.on_region_created = lambda: getattr(control_widget.lines_content_widget, 'notify_spectral_region_added', lambda: None)()
            def _on_spec_removed():
                if hasattr(control_widget.lines_content_widget, 'deactivate_spectral_button'):
                    control_widget.lines_content_widget.deactivate_spectral_button()
                if hasattr(control_widget.lines_content_widget, 'notify_spectral_region_removed'):
                    control_widget.lines_content_widget.notify_spectral_region_removed()
            image_spectra[i].spectral_manager.on_region_removed = _on_spec_removed
        if hasattr(image_spectra[i], 'spatial_manager'):
            image_spectra[i].spatial_manager.on_region_created = lambda: getattr(control_widget.lines_content_widget, 'notify_spatial_region_added', lambda: None)()
            def _on_spat_removed():
                if hasattr(control_widget.lines_content_widget, 'deactivate_spatial_button'):
                    control_widget.lines_content_widget.deactivate_spatial_button()
                if hasattr(control_widget.lines_content_widget, 'notify_spatial_region_removed'):
                    control_widget.lines_content_widget.notify_spatial_region_removed()
            image_spectra[i].spatial_manager.on_region_removed = _on_spat_removed
        

        
        # Also allow clearing spatial avg from spectrum window
        if i < len(spectra):
            control_widget.lines_content_widget.toggleAvgYRemove.connect(spectra[i].clear_averaging_regions)
        
        # Enhanced crosshair synchronization: connect spectrum image to spatial window
        if i < len(spatial):
            # Connect crosshair movement to update spatial window
            image_spectra[i].crosshairMoved.connect(spatial[i].update_from_spectrum_crosshair)
            # Connect spectral averaging removal to spatial window
            control_widget.lines_content_widget.toggleAvgXRemove.connect(spatial[i].clear_averaging_regions)
            # Note: Removed feedback connection from spatial horizontal line to spectrum image crosshair
            # to prevent unwanted feedback when moving the spatial window horizontal line
            
            # Connect zoom synchronization: spectrum image view changes update spatial window limits
            image_spectra[i].viewRangeChanged.connect(
                lambda x_min, x_max, y_min, y_max, spatial_win=spatial[i]: spatial_win.set_spatial_limits(y_min, y_max)
            )
        
        # Connect zoom synchronization: spectrum image view changes update spectrum window limits
        if i < len(spectra):
            image_spectra[i].viewRangeChanged.connect(
                lambda x_min, x_max, y_min, y_max, spectrum_win=spectra[i]: spectrum_win.set_spectral_limits(x_min, x_max)
            )
    
    # Connect the xlamRangeChanged signal 

    for spectrum_widget in spectra:
        control_widget.xlamRangeChanged.connect(spectrum_widget.update_spectral_range)
        control_widget.resetXlamRangeRequested.connect(spectrum_widget.reset_spectral_range)
        
    for image_spectrum_widget in image_spectra:
        control_widget.xlamRangeChanged.connect(image_spectrum_widget.update_spectral_range)
        control_widget.resetXlamRangeRequested.connect(image_spectrum_widget.reset_spectral_range)

    # Connect the spatialRangeChanged signal for x-axis (spatial pixel) limits
    for image_spectrum_widget in image_spectra:
        control_widget.spatialRangeChanged.connect(image_spectrum_widget.update_spatial_range)
        control_widget.resetSpatialRangeRequested.connect(image_spectrum_widget.reset_spatial_range)

    for spatial_widget in spatial:
        control_widget.spatialRangeChanged.connect(spatial_widget.update_spatial_range)
        control_widget.resetSpatialRangeRequested.connect(spatial_widget.reset_spatial_range)

    # Set widget collections for synchronization
    control_widget.set_widget_collections(image_spectra, spectra, spatial)

    # --- Show Window and Run App ---
    # Ensure normal window state (avoid accidental maximize/fullscreen under Xvfb)
    try:
        win.showNormal()
    except Exception:
        pass
    win.show()
    try:
        # Use environment variable or default to dark style
        dark_stylesheet = qdarkstyle.load_stylesheet_from_environment(is_pyqtgraph=True)
        app.setStyleSheet(dark_stylesheet)
    except ImportError:
        print("qdarkstyle not found. Using default Qt style.")
    except Exception as e:
        print(f"Could not apply qdarkstyle: {e}")

    # If we created the QApplication here, start the event loop; otherwise, return window for embedding
    if created_app:
        app.exec()
        return None
    else:
        return win


# --- 4D Scan Viewer: states, spatial, spectral, spatial ---

def scan_viewer(data: np.ndarray, title: str = 'scan viewer', state_names: List[str] = None):
    """
    Expected overall data shape: (states, spatial_y, spectral, spatial_x)
    """
    # Use existing QApplication if present, otherwise create one
    app = QtWidgets.QApplication.instance()
    created_app = False
    if app is None:
        app = pg.mkQApp(title)
        created_app = True
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    # Centralized window size (uses same policy as spectator) with env override
    w, h = get_initial_window_size(app, env_var='SPECTATOR_WINDOW')
    win.resize(w, h)
    win.setWindowTitle(title)

    # --- State names ---
    if state_names is None:
        STOKES_NAMES = [str(i+1) for i in range(data.shape[0])]
    else:
        STOKES_NAMES = state_names

    # --- Widgets ---
    control_widget = PlotControlWidget()

    scan_images: List[Any] = []
    spectra: List[Any] = []
    image_spectra: List[Any] = []
    spatial: List[Any] = []
    docks: Dict[str, Dict[str, Dock]] = {"scan": {}, "spectrum": {}, "spec_img": {}, "spatial": {}}

    # Data is expected as (states, spatial_y, spectral, spatial_x)
    n_states = data.shape[0]
    for i in range(n_states):
        base_name = STOKES_NAMES[i]
        # For each state, we will display a spectrum image (spectral vs spatial_x) at a given spatial_y index.
        state_data = data[i]
        # Shapes: spatial_y, spectral, spatial_x
        if state_data.ndim != 3:
            raise ValueError(f"scan_viewer expects per-state 3D data (y, spectral, x); got shape {state_data.shape}")

        stokes_data_wl_x = state_data[0, :, :]  # (spectral, x)
        

        # Windows
        win_image_spectrum = StokesSpectrumImageWindow(stokes_data_wl_x, stokes_index=i, name=base_name)
        win_spectrum = StokesSpectrumWindow(stokes_data_wl_x, stokes_index=i, name=base_name)
        win_spatial = StokesSpatialWindow(stokes_data_wl_x, stokes_index=i, name=base_name)
        win_scan = StokesImageWindow(state_data, stokes_index=i, name=base_name)

        image_spectra.append(win_image_spectrum)
        spectra.append(win_spectrum)
        spatial.append(win_spatial)
        scan_images.append(win_scan)

        # Initialize spectrum from image_spectrum hLine (spatial x)
        try:
            if hasattr(win_image_spectrum, 'hLine'):
                x_pos = float(win_image_spectrum.hLine.value())
                n_x = stokes_data_wl_x.shape[1]
                x_idx = int(np.clip(np.round(x_pos), 0, n_x - 1))
                win_spectrum.update_spectrum_data(x_idx)
        except Exception:
            pass

        # Docks (use FixedDockLabel workaround for consistent labels)
        spectrum_image_dock = Dock(
            f"{base_name} spectrum image",
            size=(800, 540),
            label=FixedDockLabel(f"{base_name} spectrum image"),
        )
        spatial_dock = Dock(
            f"{base_name} scan",
            size=(360, 240),
            label=FixedDockLabel(f"{base_name} scan"),
        )
        spectrum_dock = Dock(
            f"{base_name} spectrum",
            size=(800, 240),
            label=FixedDockLabel(f"{base_name} spectrum"),
        )
        scan_dock = Dock(
            f"{base_name} scan",
            size=(800, 540),
            label=FixedDockLabel(f"{base_name} scan"),
        )

        spectrum_image_dock.addWidget(win_image_spectrum)
        spatial_dock.addWidget(win_spatial)
        spectrum_dock.addWidget(win_spectrum)
        scan_dock.addWidget(win_scan)

        docks["spec_img"][base_name] = spectrum_image_dock
        docks["spatial"][base_name] = spatial_dock
        docks["spectrum"][base_name] = spectrum_dock
        docks["scan"][base_name] = scan_dock

    # Arrange docks
    for i, name in enumerate(STOKES_NAMES):
        base_name = name.split('/')[0]
        if i == 0:
            area.addDock(docks["scan"][base_name], 'left')
        else:
            area.addDock(docks["scan"][base_name], 'bottom', docks["scan"][STOKES_NAMES[i-1].split('/')[0]])
      
    # Middle Column: Spectrum Images
 
    for i, name in enumerate(STOKES_NAMES):
         base_name = name
         # Add spectrum and spatial
         area.addDock(docks["spec_img"][base_name], 'right', docks["scan"][base_name])
         area.addDock(docks["spectrum"][base_name], 'right', docks["spec_img"][base_name])
         area.addDock(docks["spatial"][base_name], 'bottom', docks["spectrum"][base_name])

      # Show and style
    try:
        win.showNormal()
    except Exception:
        pass
    win.show()
    try:
        dark_stylesheet = qdarkstyle.load_stylesheet_from_environment(is_pyqtgraph=True)
        app.setStyleSheet(dark_stylesheet)
    except Exception:
        pass

    if created_app:
        app.exec_()
        return None
    else:
        return win
