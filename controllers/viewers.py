import numpy as np
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

# local imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import (
    CrosshairState, AveragingRegion, ViewerSettings,
    SpectrumImageData, SpatialData, SpectrumData
)
from views import (
    SpectrumPlotWidget, SpectrumImageWidget, SpatialPlotWidget,
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
        
        # Update state names if provided
        if new_state_names is not None:
            STOKES_NAMES = new_state_names
        else:
            # Generate default names if we have different number of states
            if len(STOKES_NAMES) != data.shape[0]:
                STOKES_NAMES = [str(i+1) for i in range(data.shape[0])]
        
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
        
        print("Spectator data update completed")
    
    # Connect file loading controller to data update function
    file_loading_controller.dataLoaded.connect(update_spectator_data)
    spectra: List[SpectrumPlotWidget] = []
    image_spectra: List[SpectrumImageWidget] = []
    spatial: List[SpatialPlotWidget] = []
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
    files_dock = Dock("Files", size=(70,1000))
    
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

 
    area.addDock(files_dock, 'right')
    area.addDock(control_dock, 'above', files_dock)

    # Control widget
    control_dock.addWidget(control_widget)
    files_dock.addWidget(file_widget)
    
    # --- Connect Signals in a Loop ---

    for i in range(len(image_spectra)):        
        image_spectra[i].crosshairMoved.connect(control_widget.handle_crosshair_movement)
        
        # Always forward avg movements so the local windows update regardless of sync state
        image_spectra[i].avgRegionChanged.connect(control_widget.handle_v_avg_line_movement)
        if i < len(spectra):
            image_spectra[i].spatialAvgRegionChanged.connect(spectra[i].handle_spatial_avg_line_movement)
        
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
        
        # Connect averaging line synchronization signals (propagate to other windows when sync is enabled)
        if hasattr(image_spectra[i], 'spectral_manager'):
            image_spectra[i].spectral_manager.regionChanged.connect(control_widget.handle_spectral_avg_line_movement)
        if hasattr(image_spectra[i], 'spatial_manager'):
            image_spectra[i].spatial_manager.regionChanged.connect(control_widget.handle_spatial_avg_line_movement)
        
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
