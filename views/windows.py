# --- Data Display Widgets ---

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from typing import List, Tuple, Dict, Optional, Any

from .base_widgets import BasePlotWidget
from utils.constants import (
    MIN_LINE_DISTANCE, ColorSchemes
)
from utils.colors import getWidgetColors
from utils.averaging_lines import AveragingLineManager
from utils import (
    add_line, add_crosshair, create_histogram, 
    initialize_spectrum_plot_item, initialize_image_plot_item,
    set_plot_wavelength_range, reset_plot_wavelength_range, update_crosshair_from_mouse
)

class StokesSpatialWindow(BasePlotWidget):
    
    xChanged = QtCore.pyqtSignal(float) # Emit x value of hLine
    hLineChanged = QtCore.pyqtSignal(float) # Emit when horizontal line position changes

    def __init__(self, data: np.ndarray, stokes_index: int, name: str):
        super().__init__(None)

        self.name = name + " spatial"
        self.full_data = data  # Store the full (spectral, x) data
        self.spectral = np.arange(self.full_data.shape[0])
        self.x = np.arange(self.full_data.shape[1])

        self._setup_plot_items()
        self._setup_connections()
        self._initialize_plot_state()

    def _setup_plot_items(self):
        """Initializes plot curve, movable line, and label."""
        self.plot_curve = pg.PlotDataItem() 
        self.plotItem.addItem(self.plot_curve)
        
        colors = getWidgetColors()
        self.plot_curve_avg = pg.PlotDataItem(pen=pg.mkPen(colors.get('averaging_v', 'yellow'), style=QtCore.Qt.SolidLine, width=2)) 
        self.plotItem.addItem(self.plot_curve_avg)

        colors = getWidgetColors()
        self.hLine = add_line(self.plotItem, colors.get('crosshair_h_spectrum_image', 'white'), 0, moveable=True)

        self.label_avg = pg.LabelItem(justify='left', size='8pt', color=colors.get('averaging_v', 'yellow'))
        self.graphics_widget.addItem(self.label_avg, row=1, col=1) 

        initialize_spectrum_plot_item(self.plotItem, y_label="x", x_label = "", x_units = "", y_units = "pixel")

    def _setup_connections(self):
        """Connects signals to slots."""
        self.hLine.sigPositionChanged.connect(self._on_hline_moved)
        self.hLine.sigPositionChanged.connect(self._emit_hline_changed)

    def _initialize_plot_state(self):
        """Sets initial plot data, vLine position, and updates labels."""
        self.plot_data = self.full_data[self.current_wl_idx, :]
        self.plot_curve.setData(self.plot_data, self.x)

        # Set initial hLine position to center
        initial_x = (self.x[0] + self.x[-1]) / 2 if self.x.size > 1 else (self.x[0] if self.x.size > 0 else 0)
        self.update_x_line(initial_x) 

    def _update_label(self):
        """Updates the coordinate label."""
        # Get the spatial position from the horizontal line
        spatial_pos = self.hLine.value()
        # Find the closest spatial index
        spatial_idx = np.argmin(np.abs(self.x - spatial_pos)) if self.x.size > 0 else 0
        
        # Get the z value (intensity) at the current position
        intensity_value = np.nan
        if hasattr(self, 'plot_data') and isinstance(self.plot_data, np.ndarray) and spatial_idx < len(self.plot_data):
            intensity_value = self.plot_data[spatial_idx]
        
        self.label.setText(f"x={spatial_pos:.0f}, z={intensity_value:.5f}", size='8pt')
        
    def _on_hline_moved(self):
        """Handles internal hLine movement and emits signal."""
        current_y = self.hLine.value()
        self.xChanged.emit(current_y)
        self._update_label()  # Update regular label
        self._update_label_wl_avg()  # Update averaged label

    @QtCore.pyqtSlot(float)
    def update_x_line(self, y: float):
        """Slot to update the hLine position from external signal."""
        if hasattr(self, 'hLine'):
            # Only update if the value is significantly different to avoid unnecessary updates
            if not np.isclose(self.hLine.value(), y):
                # Temporarily disconnect signal to avoid double emission
                self.hLine.sigPositionChanged.disconnect(self._on_hline_moved)
                self.hLine.setValue(y)
                # Reconnect signal
                self.hLine.sigPositionChanged.connect(self._on_hline_moved)
                # Manually call the update since setValue might not emit signal
                self._on_hline_moved()
        else:
            print("Warning: update_x_line called before vLine was initialized.")

    def update_spatial_data(self, wl_idx: int):
        """Updates the plotted spectrum data based on a new spatial index."""
        if not (0 <= wl_idx < self.full_data.shape[0]):
            print(f"Error: Provided wl_idx {wl_idx} is out of bounds for data with {self.full_data.shape[0]} spectral pixels.")
            return

        self.current_wl_idx = wl_idx
        self.plot_data = self.full_data[self.current_wl_idx, :]
        self.plot_curve.setData(self.x, self.plot_data)
        self._update_label() # Update label after data change    

    def update_spatial_data_wl_avg(self, wl_idx_l: int, wl_idx_c: int , wl_idx_h: int):
            """Updates the plotted spectrum data based on a new spatial indices of averaging regions."""

            self.current_wl_idx_avg = wl_idx_c
            self.plot_data_avg = (self.full_data[wl_idx_l:wl_idx_h,:]).mean(axis=0)
            self.plot_curve_avg.setData(self.plot_data_avg, self.x)
            self._update_label_wl_avg()     
            
    def clear_averaging_regions(self):
        """Clear all spatial averaging regions and reset to clean state."""
        # Remove averaged data
        if hasattr(self, 'plot_data_avg'):
            delattr(self, 'plot_data_avg')
        if hasattr(self, 'current_wl_idx_avg'):
            delattr(self, 'current_wl_idx_avg')
            
        # Clear the averaged plot curve
        self.plot_curve_avg.setData([], [])
        
        # Clear the label
        self.label_avg.setText("")
    
    def _update_label_wl_avg(self):
                """Updates the coordinate label for averaged region."""
                # Get the spatial position from the horizontal line
                spatial_pos = self.hLine.value()
                # Find the closest spatial index
                spatial_idx = np.argmin(np.abs(self.x - spatial_pos)) if self.x.size > 0 else 0
                
                # Get the z value (intensity) at the intersection of yellow line and white horizontal line
                has_avg_data = hasattr(self, 'plot_data_avg') and isinstance(self.plot_data_avg, np.ndarray)
                if has_avg_data and spatial_idx < len(self.plot_data_avg):
                    z_value = self.plot_data_avg[spatial_idx]
                    self.label_avg.setText(f"z= {z_value:.3f}")
                else:
                    # Hide the label when no averaging region is defined
                    self.label_avg.setText("")
    
    def _emit_hline_changed(self):
        """Emit signal when horizontal line position changes."""
        self.hLineChanged.emit(self.hLine.value())

    def update_spatial_range(self, min_val, max_val):
        """Updates the spatial (x pixel) axis range of the spatial plot (y-axis)."""
        set_plot_wavelength_range(self.plotItem, self.x, min_val, max_val, axis='y')

    def reset_spatial_range(self):
        """Resets the spatial (x pixel) axis range to full range on the spatial plot (y-axis)."""
        reset_plot_wavelength_range(self.plotItem, self.x, axis='y')
    
    @QtCore.pyqtSlot(float)
    @QtCore.pyqtSlot(float, float, int)
    def update_from_spectrum_crosshair(self, xpos_wl: float, ypos_spatial_x: float, source_stokes_index: int):
        """Update spatial window based on crosshair movement in spectrum image."""
        # Update horizontal line position to match spectrum image crosshair
        self.hLine.blockSignals(True)  # Prevent feedback loop
        self.hLine.setPos(ypos_spatial_x)
        self.hLine.blockSignals(False)
        
        # Update spatial data slice based on vertical line (spectral) position
        spectral_idx = np.clip(int(np.round(xpos_wl)), 0, self.full_data.shape[0] - 1)
        self.update_spatial_data_spectral(spectral_idx)
    
    def update_spatial_data_spectral(self, spectral_idx: int):
        """Update spatial data based on spectral index."""
        if not (0 <= spectral_idx < self.full_data.shape[0]):
            print(f"Error: Provided spectral_idx {spectral_idx} is out of bounds for data with {self.full_data.shape[0]} spectral pixels.")
            return
        
        self.current_spectral_idx = spectral_idx
        self.plot_data = self.full_data[spectral_idx, :]
        self.plot_curve.setData(self.plot_data, self.x)
        self._update_label()  # Use consistent label format without λ

class StokesSpectrumWindow(BasePlotWidget):
    yRangeChanged = QtCore.pyqtSignal(tuple)  # Emit (min, max)
    spectralChanged = QtCore.pyqtSignal(float) # Emit spectral value

    def __init__(self, data: np.ndarray, stokes_index: int, name: str):
        super().__init__(None)

        self.name = name + " spectrum"
        self.full_data = data  # Store the full (spectral, x) data
        self.spectral = np.arange(self.full_data.shape[0])

        self._setup_plot_items()
        self._setup_connections()
        self._initialize_plot_state()

    def _setup_plot_items(self):
        """Initializes plot curve, movable line, and label."""
        self.plot_curve = pg.PlotDataItem() 
        self.plotItem.addItem(self.plot_curve)
        
        colors = getWidgetColors()
        self.plot_curve_spectral_avg = pg.PlotDataItem(pen=pg.mkPen(colors.get('averaging_h', 'dodgerblue'), style=QtCore.Qt.SolidLine, width=2)) 
        self.plotItem.addItem(self.plot_curve_spectral_avg)

        colors = getWidgetColors()
        self.vLine = add_line(self.plotItem, colors.get('crosshair_h_spectrum_image', 'white'), 90, moveable=True)

        self.label_avg = pg.LabelItem(justify='left', size='8pt', color=colors.get('averaging_h', 'dodgerblue'))      
        self.graphics_widget.addItem(self.label_avg, row=1, col=1) 

        initialize_spectrum_plot_item(self.plotItem)

    def _setup_connections(self):
        """Connects signals to slots."""
        self.plotItem.getViewBox().sigYRangeChanged.connect(self._emit_y_range_changed)
        self.vLine.sigPositionChanged.connect(self._on_vline_moved)

    def _initialize_plot_state(self):
        """Sets initial plot data, vLine position, and updates labels."""
        # Initialize current_x_idx to center if not set
        if not hasattr(self, 'current_x_idx'):
            n_x = self.full_data.shape[1]
            self.current_x_idx = n_x // 2 if n_x > 0 else 0
        # Set initial plot data based on current_x_idx
        self.plot_data = self.full_data[:, self.current_x_idx]
        self.plot_curve.setData(self.spectral, self.plot_data)

        # Emit initial Y range and update label
        self._emit_y_range_changed(None, self.plotItem.viewRange()[1])

        # Set initial vLine position to center
        initial_spectral = (self.spectral[0] + self.spectral[-1]) / 2 if self.spectral.size > 1 else (self.spectral[0] if self.spectral.size > 0 else 0)
        self.update_spectral_line(initial_spectral) 

    def _update_label(self):
        """Updates the coordinate label."""
        spectral_value = self.vLine.value()
        # Find the closest index to the current spectral value
        spectral_idx = np.argmin(np.abs(self.spectral - spectral_value)) if self.spectral.size > 0 else -1
        intensity_value = np.nan
        if isinstance(self.plot_data, np.ndarray) and self.plot_data.ndim == 1 and 0 <= spectral_idx < self.plot_data.size:
            intensity_value = self.plot_data[spectral_idx]

        self.label.setText(f"λ: {spectral_value:.0f}, z: {intensity_value:.5f}", size='8pt')
        
    def _update_label_x_avg(self):
        """Updates the coordinate label for averaged region."""
        # Use the white line position to pick the averaged z value, but only show z=
        wl_value = self.vLine.value() if hasattr(self, 'vLine') and self.vLine else self.current_x_idx_avg
        wl_idx = np.argmin(np.abs(self.spectral - wl_value)) if self.spectral.size > 0 else -1
        intensity_value = np.nan
        if isinstance(self.plot_data_avg, np.ndarray) and self.plot_data_avg.ndim == 1 and 0 <= wl_idx < self.plot_data_avg.size:
            intensity_value = self.plot_data_avg[wl_idx]

        # Match spatial window convention: only show z=
        self.label_avg.setText(f"z= {intensity_value:.3f}")

    def _on_vline_moved(self):
        """Handles internal vLine movement and emits signal."""
        current_wl = self.vLine.value()
        self.spectralChanged.emit(current_wl)
        self._update_label()
        # Also update spatial averaging label if it exists
        if hasattr(self, 'plot_data_avg') and hasattr(self, 'current_x_idx_avg'):
            self._update_label_x_avg()

    def update_spectral_range(self, min_val: Optional[float], max_val: Optional[float]):
        """Updates the spectral-axis range of the spectrum plot."""
        set_plot_wavelength_range(self.plotItem, self.spectral, min_val, max_val, axis='x')
    
    def reset_spectral_range(self):
        """Resets the spectral-axis range to the initial maximum range."""
        reset_plot_wavelength_range(self.plotItem, self.spectral, axis='x')

    def _emit_y_range_changed(self, axis, limits):
        """Emits the current Y-axis range."""
        self.yRangeChanged.emit(tuple(limits))

    @QtCore.pyqtSlot(float)
    def update_spectral_line(self, spectral_position: float):
        """Updates the vertical line position to the given spectral position."""
        try:
            # Update the vertical line position if it exists
            if not np.isclose(self.vLine.value(), spectral_position):
                self.vLine.setValue(spectral_position)
                self._update_label()
        except AttributeError:
            print("Warning: update_spectral_line called before vLine was initialized.")

    def update_spectrum_data(self, x_idx: int):
        """Updates the plotted spectrum data based on a new spatial index."""
        if not (0 <= x_idx < self.full_data.shape[1]):
            print(f"Error: Provided x_idx {x_idx} is out of bounds for data with {self.full_data.shape[1]} spatial pixels.")
            return

        self.current_x_idx = x_idx
        self.plot_data = self.full_data[:, self.current_x_idx]
        self.plot_curve.setData(self.spectral, self.plot_data)
        self._update_label() # Update label after data change    

    def update_spectrum_data_x_avg(self, x_idx_l: int, x_idx_c: int , x_idx_h: int):
        """Updates the plotted spectrum data based on a new spatial indices of averaging regions."""
        self.current_x_idx_avg = x_idx_c
        self.plot_data_avg = (self.full_data[:, x_idx_l:x_idx_h+1]).mean(axis=1)
        self.plot_curve_spectral_avg.setData(self.spectral, self.plot_data_avg)
        self._update_label_x_avg()
    
    @QtCore.pyqtSlot(float, float, float, int)
    def handle_spatial_avg_line_movement(self, y_low: float, y_center: float, y_high: float, source_stokes_index: int):
        """Handle spatial averaging line movement from spectrum image window."""
        # Convert y positions to spatial indices
        y_idx_low = int(np.clip(np.round(y_low), 0, self.full_data.shape[1] - 1))
        y_idx_center = int(np.clip(np.round(y_center), 0, self.full_data.shape[1] - 1))
        y_idx_high = int(np.clip(np.round(y_high), 0, self.full_data.shape[1] - 1))
        
        # Update spectrum data with spatial averaging
        self.update_spectrum_data_x_avg(y_idx_low, y_idx_center, y_idx_high)
    
    def clear_averaging_regions(self):
        """Clear all spectrum averaging regions and reset to clean state."""
        # Remove averaged data
        if hasattr(self, 'plot_data_avg'):
            delattr(self, 'plot_data_avg')
        if hasattr(self, 'current_x_idx_avg'):
            delattr(self, 'current_x_idx_avg')
            
        # Clear the averaged plot curve
        self.plot_curve_spectral_avg.setData([], [])
        
        # Clear the label
        self.label_avg.setText("")         

class StokesSpectrumImageWindow(BasePlotWidget):
    crosshairMoved = QtCore.pyqtSignal(float, float, int)
    avgRegionChanged = QtCore.pyqtSignal(float, float, float, int)
    spatialAvgRegionChanged = QtCore.pyqtSignal(float, float, float, int)

    def __init__(self, data: np.ndarray, stokes_index: int, name: str, scale_info: dict = None):
        super().__init__(None)

        self.stokes_index = stokes_index
        self.name = name
        self.data = data
        self.scale_info = scale_info
        self.n_spectral, self.n_x_pixel = self.data.shape 
        self.spectral_pixels = np.arange(self.n_spectral) 
        self.spatial_pixels = np.arange(self.n_x_pixel) 

        self._setup_image_plot()
        self._setup_axes()
        self._setup_crosshair()
        self._setup_v_avg() 

    def _setup_image_plot(self):
        self.image_item = pg.ImageItem()
        self.plotItem.addItem(self.image_item)
        self.histogram = create_histogram(self.image_item, self.layout, self.scale_info, self.stokes_index)

        # Respect pyqtgraph's imageAxisOrder to avoid unintended transposes across versions
        # - 'row-major': array is (rows=y, cols=x) -> need transpose because data is (spectral=x, spatial=y)
        # - 'col-major': array is (x, y) -> no transpose needed
        axis_order = pg.getConfigOption('imageAxisOrder')
        if axis_order == 'row-major':
            img = self.data.T
        else:
            img = self.data
        self.image_item.setImage(img)

        x_min_spectral = self.spectral_pixels[0] if self.spectral_pixels.size > 0 else 0
        x_max_spectral = self.spectral_pixels[-1] if self.spectral_pixels.size > 0 else self.n_spectral
        y_min_x = self.spatial_pixels[0] if self.spatial_pixels.size > 0 else 0
        y_max_x = self.spatial_pixels[-1] if self.spatial_pixels.size > 0 else self.n_x_pixel

        self.image_item.setRect(x_min_spectral, y_min_x, x_max_spectral - x_min_spectral, y_max_x - y_min_x)

        self.plotItem.setMenuEnabled(False)
        self.plotItem.vb.mouseButtons = {
            QtCore.Qt.LeftButton: pg.ViewBox.PanMode,
            QtCore.Qt.MiddleButton: pg.ViewBox.RectMode,
            QtCore.Qt.RightButton: None
        }
        self.plotItem.vb.installEventFilter(self)

    def _setup_v_avg(self):
        self.right_button_pressed = False
        self.drag_start_pos = None
        self.is_dragging = False
        self.spectral_averaging_enabled = False  # Default to disabled
        self.spatial_averaging_enabled = True  # Default to enabled

        # Averaging line managers will be initialized after labels are created


    def _remove_final_lines(self):
        # Remove both spectral and spatial averaging lines
        self._remove_spectral_lines()
        self._remove_spatial_lines()
    
    def _remove_spectral_lines(self):
        # Remove spectral averaging lines using manager
        if hasattr(self, 'spectral_manager'):
            had_lines_before = self.spectral_manager.has_lines()
            self.spectral_manager.remove_lines()
        # Clear legacy references
        self.line1, self.line2, self.center_line = None, None, None
        # Deactivate spectral button in control widget
        if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'deactivate_spectral_button'):
            self.control_widget.deactivate_spectral_button()
        # Notify region removed only if it existed before
        if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'notify_spectral_region_removed'):
            if had_lines_before:
                self.control_widget.notify_spectral_region_removed()
    
    def _remove_spatial_lines(self):
        # Remove spatial averaging lines using manager
        if hasattr(self, 'spatial_manager'):
            had_lines_before = self.spatial_manager.has_lines()
            self.spatial_manager.remove_lines()
        # Clear legacy references
        self.h_line1, self.h_line2, self.h_center_line = None, None, None
        # Deactivate spatial button in control widget
        if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'deactivate_spatial_button'):
            self.control_widget.deactivate_spatial_button()
        # Notify region removed only if it existed before
        if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'notify_spatial_region_removed'):
            if had_lines_before:
                self.control_widget.notify_spatial_region_removed()

    def _remove_temp_lines(self):
        """Deprecated: preview lines now managed by AveragingLineManager."""
        if hasattr(self, 'spectral_manager'):
            self.spectral_manager._remove_preview_lines()
        if hasattr(self, 'spatial_manager'):
            self.spatial_manager._remove_preview_lines()

    def _handleMousePress(self, event):
        self.right_button_pressed = True
        self.is_dragging = False
        self.drag_start_pos = self.plotItem.vb.mapSceneToView(event.scenePos())
        self._remove_temp_lines()
        if self.spectral_averaging_enabled and hasattr(self, 'spectral_manager'):
            self.spectral_manager.begin_drag_at(self.drag_start_pos.x())
        elif self.spatial_averaging_enabled and hasattr(self, 'spatial_manager'):
            self.spatial_manager.begin_drag_at(self.drag_start_pos.y())

    def _handleMouseRelease(self, event):
        self.right_button_pressed = False

        if self.is_dragging and self.drag_start_pos:
            if self.spectral_averaging_enabled:
                self._handle_spectral_averaging_release(event)
            else:
                self._handle_spatial_averaging_release(event)

        self._remove_temp_lines()
        self.drag_start_pos = None
        self.is_dragging = False
    
    def _handle_spectral_averaging_release(self, event):
        """Handle mouse release for spectral averaging (vertical lines)."""
        wl_end = self.plotItem.vb.mapSceneToView(event.scenePos()).x()
        if hasattr(self, 'spectral_manager'):
            self.spectral_manager.end_drag_at(wl_end)
    
    def _handle_spatial_averaging_release(self, event):
        """Handle mouse release for spatial averaging (horizontal lines)."""
        y_end = self.plotItem.vb.mapSceneToView(event.scenePos()).y()
        if hasattr(self, 'spatial_manager'):
            self.spatial_manager.end_drag_at(y_end)

    def eventFilter(self, obj, event):
        if obj == self.plotItem.vb:
            # Handle right-click events based on averaging state
            if event.type() == QtCore.QEvent.GraphicsSceneMousePress and event.button() == QtCore.Qt.RightButton:
                if self.spectral_averaging_enabled or self.spatial_averaging_enabled:
                    self._handleMousePress(event)
                    return True
                else:
                    # Block right-click completely when no averaging is enabled
                    return True
            elif event.type() == QtCore.QEvent.GraphicsSceneMouseMove and self.right_button_pressed:
                if self.spectral_averaging_enabled or self.spatial_averaging_enabled:
                    current_pos = self.plotItem.vb.mapSceneToView(event.scenePos())
                    if self.spectral_averaging_enabled and hasattr(self, 'spectral_manager'):
                        self.spectral_manager.update_drag_to(current_pos.x())
                    elif self.spatial_averaging_enabled and hasattr(self, 'spatial_manager'):
                        self.spatial_manager.update_drag_to(current_pos.y())
                    self.is_dragging = True
                    return True
                else:
                    # Block right-click drag when no averaging is enabled
                    return True
            elif event.type() == QtCore.QEvent.GraphicsSceneMouseRelease and event.button() == QtCore.Qt.RightButton:
                if self.spectral_averaging_enabled or self.spatial_averaging_enabled:
                    self._handleMouseRelease(event)
                    return True
                else:
                    # Block right-click release when no averaging is enabled
                    return True
        return super().eventFilter(obj, event)

    def _clamp_spectral_position(self, pos: float) -> float:
        return np.clip(pos, 0, self.n_spectral - 1)
    
    def _clamp_spatial_position(self, pos: float) -> float:
        return np.clip(pos, 0, self.n_x_pixel - 1)

    def _setup_axes(self):
        initialize_image_plot_item(self.plotItem, y_values=True,
                                y_label="x", y_units="pixel", 
                                x_label="λ", x_units="pixel") 

        num_wl_ticks = 8
        wl_ticks_pix = np.linspace(0, self.n_spectral - 1, num_wl_ticks)
        wl_ticks = [(tick, f'{tick:.0f}') for tick in wl_ticks_pix]
        self.plotItem.getAxis('bottom').setTicks([wl_ticks]) # Apply to bottom axis

    def _setup_crosshair(self):

        colors = getWidgetColors()
        self.vLine, self.hLine = add_crosshair(self.plotItem, colors.get('crosshair_v', 'white'), colors.get('crosshair_h_spectrum_image', 'white'))
        self.plotItem.scene().sigMouseMoved.connect(self.updateCrosshairAndLabel)
        self.plotItem.scene().sigMouseClicked.connect(self.mouseClicked)
        self.last_valid_crosshair_pos = None
        self.crosshair_locked = False
        # Initialize crosshair at image center
        mid_spectral = (self.n_spectral - 1) / 2
        mid_spatial = (self.n_x_pixel - 1) / 2
        self.vLine.setPos(mid_spectral)
        self.hLine.setPos(mid_spatial)
        self.last_valid_crosshair_pos = (mid_spectral, mid_spatial)
        self.updateLabelFromCrosshair(mid_spectral, mid_spatial)
        
        # Add yellow spectral averaging label using same positioning as spectrum windows
        colors = getWidgetColors()
        self.label_avg_spectral = pg.LabelItem(justify='left', size='8pt', color=colors.get('averaging_v', 'yellow'))
        self.graphics_widget.addItem(self.label_avg_spectral, row=1, col=1)
        
        # Add blue spatial averaging label using same positioning as spectrum windows  
        self.label_avg_spatial = pg.LabelItem(justify='left', size='8pt', color=colors.get('averaging_h', 'dodgerblue'))
        self.graphics_widget.addItem(self.label_avg_spatial, row=1, col=2)
        
        # Initialize averaging line managers now that labels exist
        self.spectral_manager = AveragingLineManager(
            self.plotItem, 'vertical', self.n_spectral, self.stokes_index, 
            'averaging_v', self.label_avg_spectral
        )
        self.spatial_manager = AveragingLineManager(
            self.plotItem, 'horizontal', self.n_x_pixel, self.stokes_index,
            'averaging_h', self.label_avg_spatial
        )
        
        # Connect signals
        self.spectral_manager.regionChanged.connect(self.avgRegionChanged)
        self.spatial_manager.regionChanged.connect(self.spatialAvgRegionChanged)
        
        # Set up button activation callbacks
        self.spectral_manager._button_activation_callback = self._activate_spectral_button
        self.spatial_manager._button_activation_callback = self._activate_spatial_button

        # Notify control widget when a new region is created (manager handles de-dup logic)
        if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'notify_spectral_region_added'):
            self.spectral_manager.on_region_created = lambda: getattr(self.control_widget, 'notify_spectral_region_added', lambda: None)()
        if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'notify_spatial_region_added'):
            self.spatial_manager.on_region_created = lambda: getattr(self.control_widget, 'notify_spatial_region_added', lambda: None)()

        # Notify and deactivate when a region is removed
        def _on_spectral_removed():
            if hasattr(self, 'control_widget'):
                if hasattr(self.control_widget, 'deactivate_spectral_button'):
                    self.control_widget.deactivate_spectral_button()
                if hasattr(self.control_widget, 'notify_spectral_region_removed'):
                    self.control_widget.notify_spectral_region_removed()
        def _on_spatial_removed():
            if hasattr(self, 'control_widget'):
                if hasattr(self.control_widget, 'deactivate_spatial_button'):
                    self.control_widget.deactivate_spatial_button()
                if hasattr(self.control_widget, 'notify_spatial_region_removed'):
                    self.control_widget.notify_spatial_region_removed()

        self.spectral_manager.on_region_removed = _on_spectral_removed
        self.spatial_manager.on_region_removed = _on_spatial_removed

    def mouseClicked(self, event):
        if event.double():
            mouse_point = self.plotItem.vb.mapSceneToView(event.scenePos())
            if not self.crosshair_locked:
                self.vLine.setPos(mouse_point.x())
                self.hLine.setPos(mouse_point.y())
                self.last_valid_crosshair_pos = (mouse_point.x(), mouse_point.y())
                self.updateLabelFromCrosshair(mouse_point.x(), mouse_point.y())
            self.crosshair_locked = not self.crosshair_locked

    def updateCrosshairAndLabel(self, pos: QtCore.QPointF):
        if not self.crosshair_locked:
            crosshair_pos = update_crosshair_from_mouse(self.plotItem, self.vLine, self.hLine, pos)
            if crosshair_pos is not None:
                xpos_wl, ypos_spatial_x = crosshair_pos
                self.last_valid_crosshair_pos = (xpos_wl, ypos_spatial_x)
                self.updateLabelFromCrosshair(xpos_wl, ypos_spatial_x)
                self.crosshairMoved.emit(xpos_wl, ypos_spatial_x, self.stokes_index)
        elif self.last_valid_crosshair_pos:
            self.updateLabelFromCrosshair(*self.last_valid_crosshair_pos)

    def updateLabelFromCrosshair(self, xpos_wl: float, ypos_spatial_x: float):
        index_spectral = np.clip(int(np.round(xpos_wl)), 0, self.n_spectral - 1)
        index_x = np.clip(int(np.round(ypos_spatial_x)), 0, self.n_x_pixel - 1)

        intensity = self.data[index_spectral, index_x] 
        # Compact label: use 'l' for spectral and omit the 'x' prefix while keeping the spatial value
        self.label.setText(f"l: {xpos_wl:.0f}, {ypos_spatial_x:.0f}, z: {intensity:.5f}", size='8pt') 

    def update_spectral_range(self, min_val, max_val):
        set_plot_wavelength_range(self.plotItem, self.spectral_pixels, min_val, max_val, axis='x') 

    def reset_spectral_range(self):
        reset_plot_wavelength_range(self.plotItem, self.spectral_pixels, axis='x') 

    def update_spatial_range(self, min_val, max_val):
        """Updates the spatial (x pixel) axis range of the image plot (y-axis)."""
        set_plot_wavelength_range(self.plotItem, self.spatial_pixels, min_val, max_val, axis='y')

    def reset_spatial_range(self):
        """Resets the spatial (x pixel) axis range of the image plot (y-axis) to full range."""
        reset_plot_wavelength_range(self.plotItem, self.spatial_pixels, axis='y')

    def updateExternalVLine(self, xpos_wl: float): 
        if not self.crosshair_locked:
            self.vLine.setPos(xpos_wl)
            current_y_spatial = self.hLine.value() 
            self.last_valid_crosshair_pos = (xpos_wl, current_y_spatial)
            self.updateLabelFromCrosshair(xpos_wl, current_y_spatial)

    @QtCore.pyqtSlot(float, float)
    def set_crosshair_position(self, xpos_wl: float, ypos_spatial_x: float): 
        if not self.crosshair_locked:
            self.vLine.setPos(xpos_wl)
            self.hLine.setPos(ypos_spatial_x)
            self.updateLabelFromCrosshair(xpos_wl, ypos_spatial_x)
            self.last_valid_crosshair_pos = (xpos_wl, ypos_spatial_x)
    
    @QtCore.pyqtSlot(float)
    def update_horizontal_crosshair(self, ypos_spatial_x: float):
        """Update only the horizontal crosshair line from spatial window."""
        if not self.crosshair_locked:
            self.hLine.blockSignals(True)  # Prevent feedback loop
            self.hLine.setPos(ypos_spatial_x)
            self.hLine.blockSignals(False)
            # Update label with current crosshair position
            if self.last_valid_crosshair_pos:
                self.updateLabelFromCrosshair(self.last_valid_crosshair_pos[0], ypos_spatial_x)
                self.last_valid_crosshair_pos = (self.last_valid_crosshair_pos[0], ypos_spatial_x)
    
    @QtCore.pyqtSlot(float, float, int)
    def update_crosshair_from_sync(self, xpos_wl: float, ypos_spatial_x: float, source_stokes_index: int):
        """Update crosshair position from synchronization with other states."""
        if not self.crosshair_locked and source_stokes_index != self.stokes_index:
            # Block signals to prevent feedback loops
            self.vLine.blockSignals(True)
            self.hLine.blockSignals(True)
            
            # Update crosshair positions
            self.vLine.setPos(xpos_wl)
            self.hLine.setPos(ypos_spatial_x)
            
            # Update label and store position
            self.last_valid_crosshair_pos = (xpos_wl, ypos_spatial_x)
            self.updateLabelFromCrosshair(xpos_wl, ypos_spatial_x)
            
            # Re-enable signals
            self.vLine.blockSignals(False)
            self.hLine.blockSignals(False)
    
    def clear_averaging_regions(self):
        """Clear all averaging regions and reset to clean state."""
        self._remove_final_lines()
    
    def remove_spectral_averaging(self):
        """Remove all spectral averaging lines and clear labels."""
        self._remove_spectral_lines()
        if hasattr(self, 'label_avg_spectral'):
            self.label_avg_spectral.setText("")
    
    def remove_spatial_averaging(self):
        """Remove all spatial averaging lines and clear labels."""
        self._remove_spatial_lines()
        if hasattr(self, 'label_avg_spatial'):
            self.label_avg_spatial.setText("")
    
    def create_default_spectral_averaging(self):
        """Create default spectral averaging lines using the manager."""
        if hasattr(self, 'spectral_manager'):
            had_lines_before = self.spectral_manager.has_lines()
            self.spectral_manager.create_default_lines()
            # Update legacy references for backward compatibility
            if self.spectral_manager.has_lines():
                self.line1 = self.spectral_manager.line1
                self.line2 = self.spectral_manager.line2
                self.center_line = self.spectral_manager.center_line
                
            # Activate spectral button when averaging is created
            if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'activate_spectral_button'):
                self.control_widget.activate_spectral_button()
            # Notify control widget only if newly created
            if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'notify_spectral_region_added'):
                if not had_lines_before and self.spectral_manager.has_lines():
                    self.control_widget.notify_spectral_region_added()
    
    def create_default_spatial_averaging(self):
        """Create default spatial averaging lines using the manager."""
        if hasattr(self, 'spatial_manager'):
            had_lines_before = self.spatial_manager.has_lines()
            self.spatial_manager.create_default_lines()
            # Update legacy references for backward compatibility
            if self.spatial_manager.has_lines():
                self.h_line1 = self.spatial_manager.line1
                self.h_line2 = self.spatial_manager.line2
                self.h_center_line = self.spatial_manager.center_line
                
            # Activate spatial button when averaging is created
            if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'activate_spatial_button'):
                self.control_widget.activate_spatial_button()
            # Notify control widget only if newly created
            if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'notify_spatial_region_added'):
                if not had_lines_before and self.spatial_manager.has_lines():
                    self.control_widget.notify_spatial_region_added()
    
    @QtCore.pyqtSlot(bool)
    def set_spectral_averaging_enabled(self, enabled: bool):
        """Enable or disable spectral averaging functionality."""
        self.spectral_averaging_enabled = enabled
        self.spatial_averaging_enabled = not enabled  # Toggle between the two
        # Note: Don't clear existing averaging regions when disabled
        # The lines should remain visible, only creation of new ones is disabled
    
    def sync_spectral_averaging_lines(self, left_pos: float, center_pos: float, right_pos: float, source_stokes_index: int):
        """Synchronize spectral averaging lines from another window."""
        if source_stokes_index != self.stokes_index and hasattr(self, 'spectral_manager') and self.spectral_manager.has_lines():
            # Use the manager's set_positions method which handles clamping internally
            self.spectral_manager.set_positions(left_pos, center_pos, right_pos, block_signals=True)
    
    def sync_spatial_averaging_lines(self, lower_pos: float, center_pos: float, upper_pos: float, source_stokes_index: int):
        """Synchronize spatial averaging lines from another window."""
        if source_stokes_index != self.stokes_index and hasattr(self, 'spatial_manager') and self.spatial_manager.has_lines():
            # Use the manager's set_positions method which handles clamping internally
            self.spatial_manager.set_positions(lower_pos, center_pos, upper_pos, block_signals=True)
    
    def _activate_spectral_button(self):
        """Helper method to activate spectral averaging button."""
        if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'activate_spectral_button'):
            self.control_widget.activate_spectral_button()
    
    def _activate_spatial_button(self):
        """Helper method to activate spatial averaging button."""
        if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'activate_spatial_button'):
            self.control_widget.activate_spatial_button()