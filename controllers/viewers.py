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
    StokesSpectrumWindow, StokesSpectrumImageWindow, StokesSpatialWindow, StokesImageWindow,
    AverageSpectrumWindow, StokesSpatialYWindow, StokesSpectrumYImageWindow
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
    image_spectra_x: List[Any] = []
    image_spectra_y: List[Any] = []
    spatial_x: List[Any] = []
    spatial_y: List[Any] = []
    docks: Dict[str, Dict[str, Dock]] = {
        "scan": {},
        "spectrum": {},
        "spec_img_x": {},
        "spec_img_y": {},
        "spatial_x": {},
        "spatial_y": {},
    }

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
        initial_spec_y = state_data[:, :, 0].T if state_data.shape[2] > 0 else np.zeros((stokes_data_wl_x.shape[0], state_data.shape[0]))

        # Windows
        win_image_spectrum_x = StokesSpectrumImageWindow(stokes_data_wl_x, stokes_index=i, name=base_name)
        
        win_image_spectrum_y = StokesSpectrumYImageWindow(initial_spec_y, stokes_index=i, name=base_name)
        win_spectrum = StokesSpectrumWindow(stokes_data_wl_x, stokes_index=i, name=base_name)
        win_spatial_x = StokesSpatialWindow(stokes_data_wl_x, stokes_index=i, name=base_name)
        win_spatial_y = StokesSpatialYWindow(state_data, stokes_index=i, name=base_name)
        win_scan = StokesImageWindow(state_data, stokes_index=i, name=base_name)

        image_spectra_x.append(win_image_spectrum_x)
        image_spectra_y.append(win_image_spectrum_y)
        spectra.append(win_spectrum)
        spatial_x.append(win_spatial_x)
        spatial_y.append(win_spatial_y)
        scan_images.append(win_scan)

        # Initialize spectrum from x-spectrum-image crosshair (spatial x)
        try:
            if hasattr(win_image_spectrum_x, 'hLine'):
                x_pos = float(win_image_spectrum_x.hLine.value())
                n_x = stokes_data_wl_x.shape[1]
                x_idx = int(np.clip(np.round(x_pos), 0, n_x - 1))
                win_spectrum.update_spectrum_data(x_idx)
        except Exception:
            pass

        # Docks (use FixedDockLabel workaround for consistent labels)
        spectrum_image_dock_x = Dock(
            f"{base_name} spectrum image x",
            size=(800, 540),
            label=FixedDockLabel(f"{base_name} spectrum image x"),
        )
        spectrum_image_dock_y = Dock(
            f"{base_name} spectrum image y",
            size=(800, 540),
            label=FixedDockLabel(f"{base_name} spectrum image y"),
        )
        spatial_x_dock = Dock(
            f"{base_name} spatial x",
            size=(360, 240),
            label=FixedDockLabel(f"{base_name} spatial x"),
        )
        spatial_y_dock = Dock(
            f"{base_name} spatial y",
            size=(360, 240),
            label=FixedDockLabel(f"{base_name} spatial y"),
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

        spectrum_image_dock_x.addWidget(win_image_spectrum_x)
        spectrum_image_dock_y.addWidget(win_image_spectrum_y)
        spatial_x_dock.addWidget(win_spatial_x)
        spatial_y_dock.addWidget(win_spatial_y)
        spectrum_dock.addWidget(win_spectrum)
        scan_dock.addWidget(win_scan)

        docks["spec_img_x"][base_name] = spectrum_image_dock_x
        docks["spec_img_y"][base_name] = spectrum_image_dock_y
        docks["spatial_x"][base_name] = spatial_x_dock
        docks["spatial_y"][base_name] = spatial_y_dock
        docks["spectrum"][base_name] = spectrum_dock
        docks["scan"][base_name] = scan_dock

    # Control dock
    control_dock = Dock(
        "Control",
        size=(int(CONTROL_PANEL_SIZE[0] * 1.5), CONTROL_PANEL_SIZE[1]),
        label=FixedDockLabel("Control"),
    )

    # Average spectrum dock (use state 0, full scan cube: (y, spectral, x))
    avg_spectrum_widget = None
    avg_spectrum_dock = None
    try:
        avg_spectrum_widget = AverageSpectrumWindow(data[0], name=f"{STOKES_NAMES[0]} average spectrum")
        avg_spectrum_dock = Dock(
            "Average spectrum",
            size=(1000, 180),
            label=FixedDockLabel("Average spectrum"),
        )
        avg_spectrum_dock.addWidget(avg_spectrum_widget)
    except Exception as e:
        print(f"Warning: could not create average spectrum widget: {e}")

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
        # Middle/right column: spectrum image with spectrum above; spatial slices below
        area.addDock(docks["spec_img_x"][base_name], 'right', docks["scan"][base_name])
        area.addDock(docks["spec_img_y"][base_name], 'below', docks["spec_img_x"][base_name])
        area.addDock(docks["spatial_x"][base_name], 'right', docks["spec_img_x"][base_name])
        area.addDock(docks["spectrum"][base_name], 'above', docks["spatial_x"][base_name])
        area.addDock(docks["spatial_y"][base_name], 'below', docks["spatial_x"][base_name])

    # Add average spectrum at bottom and control at right
    if avg_spectrum_dock is not None:
        area.addDock(avg_spectrum_dock, 'bottom')
    area.addDock(control_dock, 'right')
    try:
        control_widget.setMinimumWidth(int(CONTROL_PANEL_SIZE[0] * 1.5))
    except Exception:
        pass
    control_dock.addWidget(control_widget)

    # Setup z-limit controls (use x-spectrum-image + x-spatial slice for existing controls)
    try:
        control_widget.init_spectrum_limit_controls(spectra, image_spectra_x, spatial_x)
    except Exception as e:
        print(f"Warning: could not initialize limit controls: {e}")

    # Set widget collections for synchronization
    try:
        control_widget.set_widget_collections(image_spectra_x, spectra, spatial_x)
    except Exception:
        pass

    # --- Crosshair/data wiring ---

    _scan_crosshair_sync_guard = {"active": False}

    def _apply_state_slice_from_scan_crosshair(xpos: float, ypos: float, stokes_index: int):
        """Apply per-state (spectral, x) views from scan image crosshair (x=spatial_x, y=spatial_y)."""
        y_idx = int(np.clip(np.round(ypos), 0, data[stokes_index].shape[0] - 1))
        x_idx = int(np.clip(np.round(xpos), 0, data[stokes_index].shape[2] - 1))

        slice_wl_x = data[stokes_index][y_idx, :, :]  # (spectral, x)
        slice_wl_y = data[stokes_index][:, :, x_idx].T  # (spectral, y)

        # Update dependent windows
        image_spectra_x[stokes_index].set_data(slice_wl_x)
        image_spectra_y[stokes_index].set_data(slice_wl_y)
        spectra[stokes_index].set_full_data(slice_wl_x)
        spatial_x[stokes_index].set_full_data(slice_wl_x)

        # Use current spectral index from avg spectrum if available, otherwise spectrum vLine
        if avg_spectrum_widget is not None:
            spectral_idx = int(np.clip(np.round(avg_spectrum_widget.vLine.value()), 0, slice_wl_x.shape[0] - 1))
        else:
            spectral_idx = int(np.clip(np.round(spectra[stokes_index].vLine.value()), 0, slice_wl_x.shape[0] - 1))

        # Align crosshairs / selectors
        spectra[stokes_index].update_spectral_line(float(spectral_idx))
        spectra[stokes_index].update_spectrum_data(x_idx)

        image_spectra_x[stokes_index].set_crosshair_position(float(spectral_idx), float(x_idx))
        image_spectra_y[stokes_index].set_crosshair_position(float(spectral_idx), float(y_idx))
        spatial_x[stokes_index].update_x_line(float(x_idx))
        spatial_x[stokes_index].update_spatial_data_spectral(int(spectral_idx))

        # Update y-profile (z as function of y) at current (spectral_idx, x_idx) and show current y
        if stokes_index < len(spatial_y):
            spatial_y[stokes_index].update_profile(int(spectral_idx), int(x_idx))
            spatial_y[stokes_index].update_y_line(float(y_idx))

    def _update_state_slice_from_scan_crosshair(xpos: float, ypos: float, stokes_index: int):
        """Update per-state (spectral, x) views from scan image crosshair (x=spatial_x, y=spatial_y)."""
        if _scan_crosshair_sync_guard["active"]:
            return

        try:
            _scan_crosshair_sync_guard["active"] = True

            # Always update the source state
            _apply_state_slice_from_scan_crosshair(xpos, ypos, stokes_index)

            # If crosshair sync is enabled, update other states too.
            # NOTE: programmatic crosshair movement does not emit crosshairMoved,
            # so we must explicitly apply the slice update for those states.
            if getattr(control_widget, 'sync_crosshair', False):
                for j, scan in enumerate(scan_images):
                    if j == stokes_index:
                        continue
                    try:
                        scan.set_crosshair_position(xpos, ypos)
                    except Exception:
                        pass
                    _apply_state_slice_from_scan_crosshair(xpos, ypos, j)
        except Exception as e:
            print(f"Warning: could not update scan slice from crosshair: {e}")
        finally:
            _scan_crosshair_sync_guard["active"] = False

    # Connect scan crosshair to slice updates
    for i in range(len(scan_images)):
        scan_images[i].crosshairMoved.connect(_update_state_slice_from_scan_crosshair)

    # Connect spectrum-image crosshair/averaging to existing control sync logic
    for i in range(len(image_spectra_x)):
        image_spectra_x[i].crosshairMoved.connect(control_widget.handle_crosshair_movement)
        image_spectra_x[i].avgRegionChanged.connect(control_widget.handle_v_avg_line_movement)
        if i < len(spectra):
            image_spectra_x[i].spatialAvgRegionChanged.connect(spectra[i].handle_spatial_avg_line_movement)
        if i < len(spatial_x):
            image_spectra_x[i].avgRegionChanged.connect(spatial_x[i].handle_spectral_avg_line_movement)
        image_spectra_x[i].spatialAvgRegionChanged.connect(control_widget.handle_spatial_avg_line_movement)

        control_widget.lines_content_widget.spectralAveragingEnabled.connect(image_spectra_x[i].set_spectral_averaging_enabled)
        control_widget.lines_content_widget.toggleAvgXRemove.connect(image_spectra_x[i].remove_spectral_averaging)
        control_widget.lines_content_widget.toggleAvgYRemove.connect(image_spectra_x[i].remove_spatial_averaging)
        control_widget.lines_content_widget.createDefaultSpectralAveraging.connect(image_spectra_x[i].create_default_spectral_averaging)
        control_widget.lines_content_widget.createDefaultSpatialAveraging.connect(image_spectra_x[i].create_default_spatial_averaging)

        image_spectra_x[i].control_widget = control_widget.lines_content_widget

        if hasattr(image_spectra_x[i], 'spectral_manager'):
            image_spectra_x[i].spectral_manager.on_region_created = lambda: getattr(control_widget.lines_content_widget, 'notify_spectral_region_added', lambda: None)()
            def _on_spec_removed():
                if hasattr(control_widget.lines_content_widget, 'deactivate_spectral_button'):
                    control_widget.lines_content_widget.deactivate_spectral_button()
                if hasattr(control_widget.lines_content_widget, 'notify_spectral_region_removed'):
                    control_widget.lines_content_widget.notify_spectral_region_removed()
            image_spectra_x[i].spectral_manager.on_region_removed = _on_spec_removed
        if hasattr(image_spectra_x[i], 'spatial_manager'):
            image_spectra_x[i].spatial_manager.on_region_created = lambda: getattr(control_widget.lines_content_widget, 'notify_spatial_region_added', lambda: None)()
            def _on_spat_removed():
                if hasattr(control_widget.lines_content_widget, 'deactivate_spatial_button'):
                    control_widget.lines_content_widget.deactivate_spatial_button()
                if hasattr(control_widget.lines_content_widget, 'notify_spatial_region_removed'):
                    control_widget.lines_content_widget.notify_spatial_region_removed()
            image_spectra_x[i].spatial_manager.on_region_removed = _on_spat_removed

        if i < len(spectra):
            control_widget.lines_content_widget.toggleAvgYRemove.connect(spectra[i].clear_averaging_regions)

        if i < len(spatial_x):
            image_spectra_x[i].crosshairMoved.connect(spatial_x[i].update_from_spectrum_crosshair)
            control_widget.lines_content_widget.toggleAvgXRemove.connect(spatial_x[i].clear_averaging_regions)
            image_spectra_x[i].viewRangeChanged.connect(
                lambda x_min, x_max, y_min, y_max, spatial_win=spatial_x[i]: spatial_win.set_spatial_limits(y_min, y_max)
            )

        if i < len(spatial_y):
            image_spectra_x[i].crosshairMoved.connect(spatial_y[i].update_from_spectrum_image_crosshair)

        if i < len(spectra):
            image_spectra_x[i].viewRangeChanged.connect(
                lambda x_min, x_max, y_min, y_max, spectrum_win=spectra[i]: spectrum_win.set_spectral_limits(x_min, x_max)
            )

    # Connect axis limit controls
    for spectrum_widget in spectra:
        control_widget.xlamRangeChanged.connect(spectrum_widget.update_spectral_range)
        control_widget.resetXlamRangeRequested.connect(spectrum_widget.reset_spectral_range)
    for image_spectrum_widget in image_spectra_x:
        control_widget.xlamRangeChanged.connect(image_spectrum_widget.update_spectral_range)
        control_widget.resetXlamRangeRequested.connect(image_spectrum_widget.reset_spectral_range)
    for image_spectrum_widget in image_spectra_y:
        control_widget.xlamRangeChanged.connect(image_spectrum_widget.update_spectral_range)
        control_widget.resetXlamRangeRequested.connect(image_spectrum_widget.reset_spectral_range)
    for spatial_widget in spatial_x:
        control_widget.spatialRangeChanged.connect(spatial_widget.update_spatial_range)
        control_widget.resetSpatialRangeRequested.connect(spatial_widget.reset_spatial_range)
    for image_spectrum_widget in image_spectra_x:
        control_widget.spatialRangeChanged.connect(image_spectrum_widget.update_spatial_range)
        control_widget.resetSpatialRangeRequested.connect(image_spectrum_widget.reset_spatial_range)

    if avg_spectrum_widget is not None:
        control_widget.xlamRangeChanged.connect(avg_spectrum_widget.update_spectral_range)
        control_widget.resetXlamRangeRequested.connect(avg_spectrum_widget.reset_spectral_range)
        # Avg spectrum drives scan image wavelength index + spectral selectors
        for i in range(len(scan_images)):
            avg_spectrum_widget.spectralIndexChanged.connect(scan_images[i].update_wavelength_index)
            avg_spectrum_widget.spectralIndexChanged.connect(lambda idx, w=spectra[i]: w.update_spectral_line(float(idx)))
            avg_spectrum_widget.spectralIndexChanged.connect(spatial_x[i].update_spatial_data_spectral)
            if i < len(spatial_y):
                avg_spectrum_widget.spectralIndexChanged.connect(spatial_y[i].update_spectral_index)

    # Initialize per-state slices based on initial scan crosshair
    for i in range(len(scan_images)):
        try:
            _update_state_slice_from_scan_crosshair(scan_images[i].vLine.value(), scan_images[i].hLine.value(), i)
        except Exception:
            pass

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
