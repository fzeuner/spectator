import numpy as np
from pprint import pformat
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
import qdarkstyle
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from typing import List, Tuple, Dict, Optional, Any 
from functools import partial
from .file_controllers import FileLoadingController
from .file_controllers import FileListingController
from utils.colors import getWidgetColors
from utils.info_formatter import format_info_to_html

# local imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Note: Models import removed; unused in this controller
from views import (
    LinesControlGroup, SpectrumLimitControlGroup, PlotControlWidget
)
from views.windows import (
    StokesSpectrumWindow, StokesSpectrumImageWindow, StokesSpatialWindow
)
from controllers.app_controller import AxisType, data_manager

# --- Main Application Setup for 3D data ---

def spectator(data: np.ndarray, title: str = 'spectator', state_names: List[str] = None):
    """
    Main function to create and display the interactive data viewer.

    Args:
        data: Numpy array of shape (N_Stokes, N_wl, N_x) containing Stokes data.
        title: Window title.
        state_names: List of names for the states (e.g., ['I', 'Q', 'U', 'V'])
    """  
    app = pg.mkQApp(title)
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
    
    # Create file controllers
    file_loading_controller = FileLoadingController()
    file_widget = FileListingController()
    
    # Connect file selection to loading
    file_widget.fileSelected.connect(file_loading_controller.load_file)
    # Debug: log selected file
    try:
        file_widget.fileSelected.connect(lambda p: print(f"[DEBUG][spectator] fileSelected: {p}"))
    except Exception:
        pass
    
    # Create data update function
    def update_spectator_data(new_data: np.ndarray, new_state_names: List[str] = None):
        """Update the spectator with new data without recreating the entire interface."""
        print(f"Updating spectator with new data: {new_data.shape}")
        # Reset previous scaling and apply fresh scaling to the new data
        try:
            data_manager.reset_data_scaling()
            target_axes = [AxisType.STATES, AxisType.SPECTRAL, AxisType.SPATIAL]
            scaled_data = data_manager.scaler.scale_data(new_data, target_axes, auto_scale=True)
            scale_info = data_manager.get_current_scale_info()
            # Log scaling similar to example flow
            if scale_info.get('is_scaled'):
                if scale_info.get('has_states_axis'):
                    print("Per-state data scaling applied:")
                    for state_idx, factor in scale_info['factors'].items():
                        if factor != 1.0:
                            label = scale_info['labels'][state_idx]
                            state_name = (new_state_names[state_idx]
                                          if new_state_names is not None and state_idx < len(new_state_names)
                                          else f"State {state_idx}")
                            print(f"  {state_name}: factor {factor:.2e} ({label})")
                else:
                    factor = scale_info['factors'].get('global', 1.0)
                    label = scale_info['labels'].get('global', '')
                    print(f"Data scaled by factor {factor:.2e} ({label})")
        except Exception as e:
            print(f"Warning: scaling during update failed: {e}")
            scaled_data = new_data
        
        # Update global data reference with SCALED data
        nonlocal data, STOKES_NAMES
        data = scaled_data

        # Determine new state names and whether we need to rebuild
        incoming_state_names = None
        if new_state_names is not None:
            incoming_state_names = new_state_names
        elif len(STOKES_NAMES) != data.shape[0]:
            incoming_state_names = [str(i+1) for i in range(data.shape[0])]

        # If state count changed, teardown and rebuild viewers
        if data.shape[0] != len(spectra):
            # Set STOKES_NAMES prior to build
            STOKES_NAMES = incoming_state_names if incoming_state_names is not None else STOKES_NAMES
            _teardown_viewers()
            _build_viewers()
            return

        # No rebuild needed: just refresh existing widgets with new data
        if incoming_state_names is not None:
            STOKES_NAMES = incoming_state_names
        
        # Update existing widgets with new data
        for i, name in enumerate(STOKES_NAMES):
            if i < len(spectra) and i < data.shape[0]:
                # Update existing widgets with new full data
                stokes_data_slice = data[i, :, :]  # Shape: (spectral, spatial), already scaled
                
                # Update StokesSpectrumWindow - replace full_data and refresh current display
                if i < len(spectra):
                    spectra[i].full_data = stokes_data_slice
                    spectra[i].spectral = np.arange(stokes_data_slice.shape[0])
                    
                    # Reset vertical line (crosshair) to middle of new data
                    if hasattr(spectra[i], 'vLine') and spectra[i].vLine is not None:
                        mid_spectral = stokes_data_slice.shape[0] // 2
                        spectra[i].vLine.blockSignals(True)
                        spectra[i].vLine.setPos(mid_spectral)
                        spectra[i].vLine.blockSignals(False)
                    
                    # Clear any existing averaging regions for clean state
                    spectra[i].clear_averaging_regions()
                    
                    # Refresh current spectrum display
                    if hasattr(spectra[i], 'current_x_idx') and spectra[i].current_x_idx < stokes_data_slice.shape[1]:
                        spectra[i].update_spectrum_data(spectra[i].current_x_idx)
                    else:
                        # Default to middle spatial pixel
                        mid_x = stokes_data_slice.shape[1] // 2
                        spectra[i].update_spectrum_data(mid_x)
                
                # Update StokesSpectrumImageWindow - replace data and refresh display
                if i < len(image_spectra):
                    image_spectra[i].data = stokes_data_slice
                    image_spectra[i].n_spectral, image_spectra[i].n_x_pixel = stokes_data_slice.shape
                    image_spectra[i].spectral_pixels = np.arange(image_spectra[i].n_spectral)
                    image_spectra[i].spatial_pixels = np.arange(image_spectra[i].n_x_pixel)
                    # Update averaging line manager limits to new data ranges
                    if hasattr(image_spectra[i], 'spectral_manager'):
                        image_spectra[i].spectral_manager.set_data_range(image_spectra[i].n_spectral)
                    if hasattr(image_spectra[i], 'spatial_manager'):
                        image_spectra[i].spatial_manager.set_data_range(image_spectra[i].n_x_pixel)
                    
                    # Clear any existing averaging regions for clean state
                    image_spectra[i].clear_averaging_regions()
                    
                    # Update the image display
                    # StokesSpectrumImageWindow already transposes internally for correct spectral axis orientation
                    # Set scaled image; this will trigger histogram and scale label update via sigImageChanged
                    image_spectra[i].image_item.setImage(stokes_data_slice)
                    
                    # Update the image rectangle bounds to match new data dimensions
                    x_min_spectral = image_spectra[i].spectral_pixels[0] if image_spectra[i].spectral_pixels.size > 0 else 0
                    x_max_spectral = image_spectra[i].spectral_pixels[-1] if image_spectra[i].spectral_pixels.size > 0 else image_spectra[i].n_spectral
                    y_min_x = image_spectra[i].spatial_pixels[0] if image_spectra[i].spatial_pixels.size > 0 else 0
                    y_max_x = image_spectra[i].spatial_pixels[-1] if image_spectra[i].spatial_pixels.size > 0 else image_spectra[i].n_x_pixel
                    
                    image_spectra[i].image_item.setRect(
                        x_min_spectral, y_min_x, 
                        x_max_spectral - x_min_spectral, 
                        y_max_x - y_min_x
                    )
                    
                    # Regenerate axis ticks for the new data dimensions to remove old tick remnants
                    num_wl_ticks = 8
                    wl_ticks_pix = np.linspace(0, image_spectra[i].n_spectral - 1, num_wl_ticks)
                    wl_ticks = [(tick, f'{tick:.1f}') for tick in wl_ticks_pix]
                    image_spectra[i].plotItem.getAxis('bottom').setTicks([wl_ticks])
                    
                    # Reset crosshair to center of new data
                    if hasattr(image_spectra[i], 'vLine') and image_spectra[i].vLine is not None:
                        mid_spectral = stokes_data_slice.shape[0] // 2
                        image_spectra[i].vLine.blockSignals(True)
                        image_spectra[i].vLine.setPos(mid_spectral)
                        image_spectra[i].vLine.blockSignals(False)
                    
                    if hasattr(image_spectra[i], 'hLine') and image_spectra[i].hLine is not None:
                        mid_spatial = stokes_data_slice.shape[1] // 2
                        image_spectra[i].hLine.blockSignals(True)
                        image_spectra[i].hLine.setPos(mid_spatial)
                        image_spectra[i].hLine.blockSignals(False)
                    
                    # Reset crosshair position tracking
                    image_spectra[i].last_valid_crosshair_pos = (mid_spectral, mid_spatial)
                    image_spectra[i].updateLabelFromCrosshair(mid_spectral, mid_spatial)
                    
                    # Remove averaging lines as they're invalid for new data
                    if hasattr(image_spectra[i], '_remove_final_lines'):
                        image_spectra[i]._remove_final_lines()
                
                # Update StokesSpatialWindow - replace full_data and refresh current display
                if i < len(spatial):
                    spatial[i].full_data = stokes_data_slice
                    spatial[i].x = np.arange(stokes_data_slice.shape[1])
                    
                    # Clear any existing averaging regions for clean state
                    spatial[i].clear_averaging_regions()
                    
                    # Reset horizontal line (crosshair) to middle of new data
                    if hasattr(spatial[i], 'hLine') and spatial[i].hLine is not None:
                        mid_spatial = stokes_data_slice.shape[1] // 2
                        spatial[i].hLine.blockSignals(True)
                        spatial[i].hLine.setPos(mid_spatial)
                        spatial[i].hLine.blockSignals(False)
                    
                    # Refresh current spatial display
                    if hasattr(spatial[i], 'current_wl_idx') and spatial[i].current_wl_idx < stokes_data_slice.shape[0]:
                        spatial[i].update_spatial_data(spatial[i].current_wl_idx)
                    else:
                        # Default to middle spectral pixel
                        mid_wl = stokes_data_slice.shape[0] // 2
                        spatial[i].update_spatial_data(mid_wl)
                
                # Update dock titles if state names changed
                if new_state_names is not None:
                    dock_keys_spectrum = list(docks["spectrum"].keys())
                    dock_keys_spec_img = list(docks["spec_img"].keys())
                    dock_keys_spatial = list(docks["spatial"].keys())
                    
                    if i < len(dock_keys_spectrum):
                        docks["spectrum"][dock_keys_spectrum[i]].setTitle(f"{name} spectrum")
                    if i < len(dock_keys_spec_img):
                        docks["spec_img"][dock_keys_spec_img[i]].setTitle(f"{name} spectrum image")
                    if i < len(dock_keys_spatial):
                        docks["spatial"][dock_keys_spatial[i]].setTitle(f"{name} spatial")
        
    # Connect file loading controller to data update function
    file_loading_controller.dataLoaded.connect(update_spectator_data)
    # Also handle loading errors explicitly
    def _on_loading_error(msg: str):
        try:
            print(f"[DEBUG][spectator] Loading error: {msg}")
            QtWidgets.QMessageBox.critical(win, 'File Load Error', msg)
        except Exception:
            pass
    file_loading_controller.loadingError.connect(_on_loading_error)
    # --- Create Control and Data Docks ---
    control_dock = Dock("Control", size=(70,1000))
    files_dock = Dock("Files", size=(70,1000))
    info_win = None   # separate window for Info
    info_text = None  # text widget inside the Info window
    
    # Initial build of viewers and arrangement
    _build_viewers()

 
    area.addDock(files_dock, 'right')
    area.addDock(control_dock, 'above', files_dock)

    # Control widget
    control_dock.addWidget(control_widget)
    files_dock.addWidget(file_widget)

    # --- Independent Info window wiring ---
    def _destroy_info_window():
        nonlocal info_win, info_text
        try:
            if info_win is not None:
                try:
                    info_win.close()
                except Exception:
                    pass
                info_win = None
                info_text = None
        except Exception:
            pass

    def _show_info_window():
        nonlocal info_win, info_text
        try:
            if info_win is None:
                # Create separate plain window with empty central widget
                info_win = QtWidgets.QMainWindow()
                info_win.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
                # Title may include current filename if available
                try:
                    fname = os.path.basename(file_loading_controller.current_file_path) if file_loading_controller.current_file_path else None
                except Exception:
                    fname = None
                info_win.setWindowTitle(f"Info{(' - ' + fname) if fname else ''}")
                # Double width (360 -> 720) and increase height to 900 for tall info blocks
                info_win.resize(720, 900)

                # Create read-only text widget
                info_text = QtWidgets.QTextEdit()
                info_text.setReadOnly(True)
                # Populate with current info if available using HTML formatter
                try:
                    info_obj = file_loading_controller.get_current_info()
                    if info_obj is None:
                        info_text.setHtml('<div class="info-root">No info available. Load a file first.</div>')
                    else:
                        info_text.setHtml(format_info_to_html(info_obj))
                except Exception as e:
                    info_text.setHtml(f"<div class=\"info-root\">Could not render info: {e}</div>")

                info_win.setCentralWidget(info_text)
                info_win.show()

                # When window is destroyed, clear handle
                try:
                    info_win.destroyed.connect(lambda: _destroy_info_window())
                except Exception:
                    pass
            else:
                try:
                    # Update title and content on subsequent clicks
                    try:
                        fname = os.path.basename(file_loading_controller.current_file_path) if file_loading_controller.current_file_path else None
                    except Exception:
                        fname = None
                    info_win.setWindowTitle(f"Info{(' - ' + fname) if fname else ''}")
                    try:
                        info_obj = file_loading_controller.get_current_info()
                        if info_text is not None:
                            if info_obj is None:
                                info_text.setHtml('<div class="info-root">No info available. Load a file first.</div>')
                            else:
                                info_text.setHtml(format_info_to_html(info_obj))
                    except Exception as e:
                        if info_text is not None:
                            info_text.setHtml(f"<div class=\"info-root\">Could not render info: {e}</div>")
                    info_win.show()
                    info_win.raise_()
                    info_win.activateWindow()
                except Exception:
                    pass
        except Exception:
            pass

    file_widget.infoRequested.connect(_show_info_window)
    
    # Build wires for creating default averaging from control (these are static and will work with rebuilt viewers too)
    control_widget.lines_content_widget.createDefaultSpectralAveraging.connect(
        lambda: [w.create_default_spectral_averaging() for w in image_spectra]
    )
    control_widget.lines_content_widget.createDefaultSpatialAveraging.connect(
        lambda: [w.create_default_spatial_averaging() for w in image_spectra]
    )

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
