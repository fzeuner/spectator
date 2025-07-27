# --- Data Display Widgets ---

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from typing import List, Tuple, Dict, Optional, Any

from .base_widgets import BasePlotWidget
from utils.constants import (
    AVG_COLORS, CROSSHAIR_COLORS, MIN_LINE_DISTANCE
)
from utils import (
    AddLine, AddCrosshair, CreateHistrogram, 
    InitializeSpectrumplotItem, InitializeImageplotItem,
    SetPlotXlamRange, ResetPlotXlamRange, update_crosshair_from_mouse
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
        
        self.plot_curve_avg = pg.PlotDataItem(pen=pg.mkPen(AVG_COLORS[1], style=QtCore.Qt.SolidLine, width=2)) 
        self.plotItem.addItem(self.plot_curve_avg)

        self.hLine = AddLine(self.plotItem, CROSSHAIR_COLORS['h_spectrum_image'], 0, moveable=True)

        self.label_avg = pg.LabelItem(justify='left', size='6pt', color=AVG_COLORS[1])
        self.graphics_widget.addItem(self.label_avg, row=1, col=1) 

        InitializeSpectrumplotItem(self.plotItem, y_label="x", x_label = "", x_units = "", y_units = "pixel")

    def _setup_connections(self):
        """Connects signals to slots."""
        self.hLine.sigPositionChanged.connect(self._on_hline_moved)
        self.hLine.sigPositionChanged.connect(self._emit_hline_changed)

    def _initialize_plot_state(self):
        """Sets initial plot data, vLine position, and updates labels."""
        self.plot_data = self.full_data[self.current_wl_idx, :]
        self.plot_curve.setData(self.plot_data, self.x)

        # Set initial hLine position
        initial_x = self.x[0] if self.x.size > 0 else 0
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
        
        self.label.setText(f"x={spatial_pos:.1f}, z={intensity_value:.5f}", size='6pt')
        
    # def _update_label_wl_avg(self):
    #         """Updates the coordinate label for avaraged region."""
    #         x_value = self.current_wl_idx_avg
    #         # Find the closest index to the current spectral value
    #         x_idx = np.argmin(np.abs(self.wavelength - x_value)) if self.wavelength.size > 0 else -1
    #         intensity_value = np.nan
    #         if isinstance(self.plot_data_avg, np.ndarray) and self.plot_data.ndim == 1 and 0 <= x_idx < self.plot_data_avg.size:
    #             intensity_value = self.plot_data_avg[x_idx]

    #         self.label_avg.setText(f"x={x_value:.1f}, z={intensity_value:.5f}", size='6pt')

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
        
        self.plot_curve_spectral_avg = pg.PlotDataItem(pen=pg.mkPen(AVG_COLORS[1], style=QtCore.Qt.SolidLine, width=2)) 
        self.plotItem.addItem(self.plot_curve_spectral_avg)

        self.vLine = AddLine(self.plotItem, CROSSHAIR_COLORS['h_spectrum_image'], 90, moveable=True)

        self.label_avg = pg.LabelItem(justify='left', size='6pt', color=AVG_COLORS[0])      
        self.graphics_widget.addItem(self.label_avg, row=1, col=1) 

        InitializeSpectrumplotItem(self.plotItem)

    def _setup_connections(self):
        """Connects signals to slots."""
        self.plotItem.getViewBox().sigYRangeChanged.connect(self._emit_y_range_changed)
        self.vLine.sigPositionChanged.connect(self._on_vline_moved)

    def _initialize_plot_state(self):
        """Sets initial plot data, vLine position, and updates labels."""
        self.plot_data = self.full_data[:, self.current_x_idx]
        self.plot_curve.setData(self.spectral, self.plot_data)
        self.plot_curve.setData(self.spectral, 0*self.plot_data)

        # Emit initial Y range and update label
        self._emit_y_range_changed(None, self.plotItem.viewRange()[1])

        # Set initial vLine position
        initial_spectral = self.spectral[0] if self.spectral.size > 0 else 0
        self.update_spectral_line(initial_spectral) 

    def _update_label(self):
        """Updates the coordinate label."""
        spectral_value = self.vLine.value()
        # Find the closest index to the current spectral value
        spectral_idx = np.argmin(np.abs(self.spectral - spectral_value)) if self.spectral.size > 0 else -1
        intensity_value = np.nan
        if isinstance(self.plot_data, np.ndarray) and self.plot_data.ndim == 1 and 0 <= spectral_idx < self.plot_data.size:
            intensity_value = self.plot_data[spectral_idx]

        self.label.setText(f"λ: {spectral_value:.1f}, z: {intensity_value:.5f}", size='6pt')
        
    def _update_label_x_avg(self):
            """Updates the coordinate label for avaraged region."""
            wl_value = self.current_x_idx_avg
            # Find the closest index to the current spectral value
            wl_idx = np.argmin(np.abs(self.spectral - wl_value)) if self.spectral.size > 0 else -1
            intensity_value = np.nan
            if isinstance(self.plot_data_avg, np.ndarray) and self.plot_data.ndim == 1 and 0 <= wl_idx < self.plot_data_avg.size:
                intensity_value = self.plot_data_avg[wl_idx]

            self.label_avg.setText(f"λ: {wl_value:.1f}, z: {intensity_value:.5f}", size='6pt')

    def _on_vline_moved(self):
        """Handles internal vLine movement and emits signal."""
        current_wl = self.vLine.value()
        self.spectralChanged.emit(current_wl)
        self._update_label()

    def update_spectral_range(self, min_val: Optional[float], max_val: Optional[float]):
        """Updates the spectral-axis range of the spectrum plot."""
        SetPlotXlamRange(self.plotItem, self.spectral, min_val, max_val, axis='x')
    
    def reset_spectral_range(self):
        """Resets the spectral-axis range to the initial maximum range."""
        ResetPlotXlamRange(self.plotItem, self.spectral, axis='x')

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
            self.plot_data_avg = (self.full_data[x_idx_l:x_idx_h,:]).mean(axis=0)
            self.plot_curve_wl_avg.setData(self.x, self.plot_data_avg)
            self._update_label_x_avg()
    
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

    def __init__(self, data: np.ndarray, stokes_index: int, name: str):
        super().__init__(None)

        self.stokes_index = stokes_index
        self.name = name
        self.data = data
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
        self.histogram = CreateHistrogram(self.image_item, self.layout)

        self.image_item.setImage(self.data.T) # <--- Transpose the data here for plotting spectral along x axis!

        x_min_spectral = self.spectral_pixels[0] if self.spectral_pixels.size > 0 else 0
        x_max_spectral = self.spectral_pixels[-1] if self.spectral_pixels.size > 0 else self.n_spectral
        y_min_x = self.spatial_pixels[0] if self.spatial_pixels.size > 0 else 0
        y_max_x = self.spatial_pixels[-1] if self.spatial_pixels.size > 0 else self.n_x_pixel

        self.image_item.setRect(x_min_spectral, y_min_x, x_max_spectral - x_min_spectral, y_max_x - y_min_x)
        
        # Lambda label removed per user request

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

        self.line1 = None
        self.line2 = None
        self.center_line = None

        self.temp_line_press = None
        self.temp_line_drag = None

    def _remove_final_lines(self):
        for line in [self.line1, self.line2, self.center_line]:
            if line:
                try:
                    line.sigPositionChanged.disconnect()
                except (TypeError, RuntimeError):
                    pass
                self.plotItem.removeItem(line)
        self.line1, self.line2, self.center_line = None, None, None

    def _remove_temp_lines(self):
        if self.temp_line_press:
            self.plotItem.removeItem(self.temp_line_press)
            self.temp_line_press = None
        if self.temp_line_drag:
            self.plotItem.removeItem(self.temp_line_drag)
            self.temp_line_drag = None

    def _handleMousePress(self, event):
        self.right_button_pressed = True
        self.is_dragging = False
        self.drag_start_pos = self.plotItem.vb.mapSceneToView(event.scenePos())

        self._remove_temp_lines()
        self.temp_line_press = AddLine(self.plotItem, AVG_COLORS[1], 90, pos=self.drag_start_pos.x(), style=QtCore.Qt.DashLine)

    def _handleMouseRelease(self, event):
        self.right_button_pressed = False

        if self.is_dragging and self.drag_start_pos:
            self._remove_final_lines()

            wl_start = self.drag_start_pos.x()
            wl_end = self.plotItem.vb.mapSceneToView(event.scenePos()).x()

            wl1_initial, wl2_initial = min(wl_start, wl_end), max(wl_start, wl_end)

            # Ensure initial distance is at least MIN_LINE_DISTANCE
            if (wl2_initial - wl1_initial) < MIN_LINE_DISTANCE:
                center_initial = (wl1_initial + wl2_initial) / 2
                wl1_initial = center_initial - MIN_LINE_DISTANCE / 2
                wl2_initial = center_initial + MIN_LINE_DISTANCE / 2

            clamped_wl1 = self._clamp_line_position(wl1_initial)
            clamped_wl2 = self._clamp_line_position(wl2_initial)

            if (clamped_wl2 - clamped_wl1) < MIN_LINE_DISTANCE:
                if clamped_wl1 == 0: 
                    clamped_wl2 = self._clamp_line_position(clamped_wl1 + MIN_LINE_DISTANCE)
                elif clamped_wl2 == self.n_spectral - 1: 
                    clamped_wl1 = self._clamp_line_position(clamped_wl2 - MIN_LINE_DISTANCE)
                else: 
                    center_temp = (clamped_wl1 + clamped_wl2) / 2
                    clamped_wl1 = self._clamp_line_position(center_temp - MIN_LINE_DISTANCE / 2)
                    clamped_wl2 = self._clamp_line_position(center_temp + MIN_LINE_DISTANCE / 2)

            center_wl = (clamped_wl1 + clamped_wl2) / 2 # Recalculate center based on final positions

            self.line1 = AddLine(self.plotItem, AVG_COLORS[1], 90, pos=clamped_wl1, moveable=True, style=QtCore.Qt.SolidLine)
            self.line2 = AddLine(self.plotItem, AVG_COLORS[1], 90, pos=clamped_wl2, moveable=True, style=QtCore.Qt.SolidLine)
            self.center_line = AddLine(self.plotItem, AVG_COLORS[1], 90, pos=center_wl, moveable=True, style=QtCore.Qt.DotLine)

            self.line1.sigPositionChanged.connect(self._update_from_line1)
            self.line2.sigPositionChanged.connect(self._update_from_line2)
            self.center_line.sigPositionChanged.connect(self._update_from_center)

            self._update_lines_and_emit(source_line=self.line1)

        self._remove_temp_lines()
        self.drag_start_pos = None
        self.is_dragging = False

    def eventFilter(self, obj, event):
        if obj == self.plotItem.vb:
            if event.type() == QtCore.QEvent.GraphicsSceneMousePress and event.button() == QtCore.Qt.RightButton:
                self._handleMousePress(event)
                return True
            elif event.type() == QtCore.QEvent.GraphicsSceneMouseMove and self.right_button_pressed:
                scene_pos = event.scenePos()
                press_pos = event.buttonDownScenePos(QtCore.Qt.RightButton)
                if (scene_pos - press_pos).manhattanLength() > 2:
                    self.is_dragging = True
                if self.is_dragging:
                    if self.temp_line_drag is None:
                        self.temp_line_drag = AddLine(self.plotItem, AVG_COLORS[1], 90, style=QtCore.Qt.DashLine) # Use AddLine here too
                    current_wl = self.plotItem.vb.mapSceneToView(scene_pos).x()
                    self.temp_line_drag.setPos(current_wl)
                self.updateCrosshairAndLabel(scene_pos)
                return True
            elif event.type() == QtCore.QEvent.GraphicsSceneMouseRelease and event.button() == QtCore.Qt.RightButton:
                self._handleMouseRelease(event)
                return True
        return super().eventFilter(obj, event)

    def _clamp_line_position(self, pos: float) -> float:
        return np.clip(pos, 0, self.n_spectral - 1)

    def _update_lines_and_emit(self, source_line=None):
        if not all([self.line1, self.line2, self.center_line]):
            return

        self.line1.blockSignals(True)
        self.line2.blockSignals(True)
        self.center_line.blockSignals(True)

        try:
            current_l1 = self.line1.value()
            current_l2 = self.line2.value()
            current_center = self.center_line.value()

            new_l1 = current_l1
            new_l2 = current_l2
            new_center = current_center

            if source_line is self.line1:
                new_l1 = self._clamp_line_position(current_l1)
                new_l2_candidate = new_l1 + (current_l2 - current_l1)
                new_l2 = self._clamp_line_position(max(new_l2_candidate, new_l1 + MIN_LINE_DISTANCE))
                new_center = (new_l1 + new_l2) / 2
            elif source_line is self.line2:
                new_l2 = self._clamp_line_position(current_l2)
                new_l1_candidate = new_l2 - (current_l2 - current_l1)
                new_l1 = self._clamp_line_position(min(new_l1_candidate, new_l2 - MIN_LINE_DISTANCE))
                new_center = (new_l1 + new_l2) / 2
            elif source_line is self.center_line:
                new_center = self._clamp_line_position(current_center)
                spacing = (current_l2 - current_l1) / 2

                if spacing < MIN_LINE_DISTANCE / 2:
                    spacing = MIN_LINE_DISTANCE / 2

                new_l1 = self._clamp_line_position(new_center - spacing)
                new_l2 = self._clamp_line_position(new_center + spacing)

                if new_l1 == 0 and (new_l2 - new_l1) < MIN_LINE_DISTANCE:
                    new_l2 = self._clamp_line_position(new_l1 + MIN_LINE_DISTANCE)
                    new_center = (new_l1 + new_l2) / 2
                elif new_l2 == self.n_spectral - 1 and (new_l2 - new_l1) < MIN_LINE_DISTANCE: 
                    new_l1 = self._clamp_line_position(new_l2 - MIN_LINE_DISTANCE)
                    new_center = (new_l1 + new_l2) / 2

            if new_l1 > new_l2:
                temp = new_l1
                new_l1 = new_l2
                new_l2 = temp
                if (new_l2 - new_l1) < MIN_LINE_DISTANCE:
                    new_l2 = new_l1 + MIN_LINE_DISTANCE
            elif (new_l2 - new_l1) < MIN_LINE_DISTANCE:
                if source_line is self.line1:
                    new_l2 = self._clamp_line_position(new_l1 + MIN_LINE_DISTANCE)
                elif source_line is self.line2:
                    new_l1 = self._clamp_line_position(new_l2 - MIN_LINE_DISTANCE)
                else:
                    center_temp = (new_l1 + new_l2) / 2
                    new_l1 = self._clamp_line_position(center_temp - MIN_LINE_DISTANCE / 2)
                    new_l2 = self._clamp_line_position(center_temp + MIN_LINE_DISTANCE / 2)

            if new_l1 > new_l2:
                 new_l1, new_l2 = new_l2, new_l1
            if (new_l2 - new_l1) < MIN_LINE_DISTANCE:
                 new_l2 = new_l1 + MIN_LINE_DISTANCE
                 if new_l2 > self.n_spectral - 1: 
                     new_l2 = self.n_spectral - 1 
                     new_l1 = max(0, new_l2 - MIN_LINE_DISTANCE)

            self.line1.setValue(new_l1)
            self.line2.setValue(new_l2)
            self.center_line.setValue((new_l1 + new_l2) / 2)
        
            # Lambda label update removed per user request

            self.avgRegionChanged.emit(new_l1, (new_l1 + new_l2) / 2, new_l2, self.stokes_index)

        finally:
            self.line1.blockSignals(False)
            self.line2.blockSignals(False)
            self.center_line.blockSignals(False)

    def _update_from_line1(self, line):
        self._update_lines_and_emit(source_line=line)

    def _update_from_line2(self, line):
        self._update_lines_and_emit(source_line=line)

    def _update_from_center(self, line):
        self._update_lines_and_emit(source_line=line)

    def _setup_axes(self):
        InitializeImageplotItem(self.plotItem, y_values=True,
                                y_label="x", y_units="pixel", 
                                x_label="λ", x_units="pixel") 

        num_wl_ticks = 8
        wl_ticks_pix = np.linspace(0, self.n_spectral - 1, num_wl_ticks)
        wl_ticks = [(tick, f'{tick:.1f}') for tick in wl_ticks_pix]
        self.plotItem.getAxis('bottom').setTicks([wl_ticks]) # Apply to bottom axis

    def _setup_crosshair(self):

        self.vLine, self.hLine = AddCrosshair(self.plotItem, CROSSHAIR_COLORS['v'], CROSSHAIR_COLORS['h_spectrum_image'])
        self.plotItem.scene().sigMouseMoved.connect(self.updateCrosshairAndLabel)
        self.plotItem.scene().sigMouseClicked.connect(self.mouseClicked)
        self.last_valid_crosshair_pos = None
        self.crosshair_locked = False
        self.updateLabelFromCrosshair(0, 0) 

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
        self.label.setText(f"λ: {xpos_wl:.1f}, x: {ypos_spatial_x:.2f}, z: {intensity:.5f}", size='6pt') 

    def update_spectral_range(self, min_val, max_val):
        SetPlotXlamRange(self.plotItem, self.spectral_pixels, min_val, max_val, axis='x') 

    def reset_spectral_range(self):
        ResetPlotXlamRange(self.plotItem, self.spectral_pixels, axis='x') 

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
        # Lambda label functionality removed per user request
        pass