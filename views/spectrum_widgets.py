"""
Spectrum-specific widget classes for the spectral data viewer.

This module contains widgets for displaying spectral data, including spectrum plots
and spectrum image displays.
"""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from typing import Optional, Tuple

from .base_widgets import BasePlotWidget, BaseImageWidget
from models import SpectrumImageData, SpectrumData, CrosshairState, AveragingRegion

# Import existing functions for compatibility
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from functions import *  # Commented out - functions module was removed


class SpectrumPlotWidget(BasePlotWidget):
    """
    Widget for displaying 1D spectrum plots.
    
    Shows spectral intensity vs wavelength with interactive crosshair and averaging capabilities.
    """
    
    # Signals
    yRangeChanged = QtCore.pyqtSignal(tuple)  # Emit (min, max)
    spectralChanged = QtCore.pyqtSignal(float)  # Emit spectral position
    
    def __init__(self, spectrum_data: Optional[SpectrumData] = None, name: str = "", parent: Optional[QtWidgets.QWidget] = None):
        """
        Initialize spectrum plot widget.
        
        Args:
            spectrum_data: SpectrumData model instance (optional)
            name: Widget name for identification
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.spectrum_data = spectrum_data
        self.name = name or "Spectrum"
        
        self._setup_plot_items()
        if self.spectrum_data is not None:
            self._setup_connections()
            self._initialize_plot_state()
    
    def set_data(self, spectrum_data: SpectrumData):
        """Set the spectrum data and initialize the widget."""
        self.spectrum_data = spectrum_data
        self._setup_connections()
        self._initialize_plot_state()
        self._update_plot()
    
    def _setup_plot_items(self):
        """Initialize plot curve, movable line, and label."""
        # Main spectrum curve
        self.plot_curve = pg.PlotDataItem()
        self.plotItem.addItem(self.plot_curve)
        
        # Averaged spectrum curve (different color/style)
        self.plot_curve_wl_avg = pg.PlotDataItem(
            pen=pg.mkPen(self.avg_colors[1], style=QtCore.Qt.SolidLine, width=2)
        )
        self.plotItem.addItem(self.plot_curve_wl_avg)
        
        # Vertical crosshair line
        self.vLine = AddLine(self.plotItem, self.crosshair_colors['h_spectrum_image'], 90, moveable=True)
        
        # Average region label
        self.label_avg = pg.LabelItem(justify='left', size='6pt', color=self.avg_colors[0])
        self.graphics_widget.addItem(self.label_avg, row=1, col=1)
        
        # Initialize plot appearance
        InitializeSpectrumplotItem(self.plotItem)
    
    def _setup_connections(self):
        """Connect signals to slots."""
        # Connect line movement to handlers
        self.vLine.sigPositionChanged.connect(self._on_vline_moved)
        
        # Connect plot range changes
        self.plotItem.sigRangeChanged.connect(self._emit_y_range_changed)
    
    def _initialize_plot_state(self):
        """Set initial plot data, vLine position, and update labels."""
        # Set initial data
        self.update_spectrum_data_from_model()
        
        # Set initial line position
        if len(self.spectrum_data.wavelengths) > 0:
            initial_wl = self.spectrum_data.wavelengths[len(self.spectrum_data.wavelengths) // 2]
            self.vLine.setValue(initial_wl)
        
        # Update initial label
        self._update_label()
    
    def update_spectrum_data_from_model(self):
        """Update plot data from the spectrum data model."""
        wavelengths = self.spectrum_data.wavelengths
        intensities = self.spectrum_data.data
        
        self.plot_curve.setData(wavelengths, intensities)
        self._update_label()
    
    def _update_label(self):
        """Update the coordinate label."""
        if len(self.spectrum_data.wavelengths) == 0:
            return
            
        # Get current wavelength from crosshair
        wl_value = self.vLine.value()
        wl_idx = self.spectrum_data.find_nearest_wavelength_index(wl_value)
        intensity_value = self.spectrum_data.get_value_at_wavelength(wl_idx)
        
        self.update_label(f"λ={wl_value:.1f}, z={intensity_value:.5f}")
    
    def _update_label_x_avg(self):
        """Update the coordinate label for averaged region."""
        if self.spectrum_data.averaging_region is None:
            return
            
        avg_value = self.spectrum_data.get_averaged_value()
        region = self.spectrum_data.averaging_region
        
        self.label_avg.setText(
            f"x avg: {region.left_limit:.1f}-{region.right_limit:.1f}, z={avg_value:.5f}",
            size='6pt'
        )
    
    def _on_vline_moved(self):
        """Handle internal vLine movement and emit signal."""
        wl_value = self.vLine.value()
        self.spectrum_data.update_crosshair(wl_value)
        self._update_label()
        self.spectralChanged.emit(wl_value)
    
    def update_wavelength_range(self, min_val: Optional[float], max_val: Optional[float]):
        """Update the λ-axis range of the spectrum plot."""
        if min_val is not None and max_val is not None:
            self.plotItem.setXRange(min_val, max_val, padding=0)
            self.plotItem.enableAutoRange(axis='x', enable=False)
        else:
            self.plotItem.enableAutoRange(axis='x', enable=True)
    
    def reset_wavelength_range(self):
        """Reset the λ-axis range to the initial maximum range."""
        self.plotItem.enableAutoRange(axis='x', enable=True)
        self.plotItem.autoRange()
    
    def _emit_y_range_changed(self, axis, limits):
        """Emit the current Y-axis range."""
        if axis is self.plotItem.getViewBox():
            y_range = self.plotItem.getViewBox().viewRange()[1]  # [1] for y-axis
            self.yRangeChanged.emit(y_range)
    
    def update_wavelength_line(self, wavelength: float):
        """
        Update the vLine position from external signal.
        
        Args:
            wavelength: New wavelength position
        """
        self.vLine.blockSignals(True)
        self.vLine.setValue(wavelength)
        self.vLine.blockSignals(False)
        
        self.spectrum_data.update_crosshair(wavelength)
        self._update_label()
    
    def update_spectrum_data(self, x_idx: int):
        """
        Update the plotted spectrum data based on a new spatial index.
        
        Args:
            x_idx: New spatial index
        """
        # This would typically update from a parent data source
        # For now, we'll update the model's spatial position
        if hasattr(self.spectrum_data, 'current_spatial_position'):
            self.spectrum_data.current_spatial_position = float(x_idx)
        
        self._update_label()
    
    def update_spectrum_data_x_avg(self, x_idx_l: int, x_idx_c: int, x_idx_h: int):
        """
        Update the plotted spectrum data based on spatial averaging indices.
        
        Args:
            x_idx_l: Left spatial index
            x_idx_c: Center spatial index  
            x_idx_h: Right spatial index
        """
        # Update averaging region in model
        if hasattr(self.spectrum_data, 'set_averaging_region'):
            self.spectrum_data.set_averaging_region(float(x_idx_l), float(x_idx_c), float(x_idx_h))
        
        self._update_label_x_avg()


class SpectrumImageWidget(BaseImageWidget):
    """
    Widget for displaying 2D spectrum images.
    
    Shows spectral-spatial data as an image with interactive crosshair and averaging lines.
    """
    
    # Signals
    crosshairMoved = QtCore.pyqtSignal(float, float, int)  # wavelength, spatial, stokes_index
    avgRegionChanged = QtCore.pyqtSignal(float, float, float, int)  # left, center, right, stokes_index
    
    def __init__(self, spectrum_image_data: Optional[SpectrumImageData] = None, stokes_index: int = 0, 
                 name: str = "", parent: Optional[QtWidgets.QWidget] = None):
        """
        Initialize spectrum image widget.
        
        Args:
            spectrum_image_data: SpectrumImageData model instance (optional)
            stokes_index: Index for multi-state data
            name: Widget name for identification
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.spectrum_image_data = spectrum_image_data
        self.stokes_index = stokes_index
        self.name = name or "Spectrum Image"
        
        # State tracking
        self.crosshair_locked = False
        self.last_valid_crosshair_pos = None
        
        # Averaging lines
        self.line1 = None  # Left averaging line
        self.line2 = None  # Right averaging line  
        self.center_line = None  # Center averaging line
        
        self._setup_image_plot()
        if self.spectrum_image_data is not None:
            self._setup_axes()
            self._setup_crosshair()
            self._setup_averaging_lines()
    
    def set_data(self, spectrum_image_data: SpectrumImageData):
        """Set the spectrum image data and initialize the widget."""
        self.spectrum_image_data = spectrum_image_data
        self._setup_axes()
        self._setup_crosshair()
        self._setup_averaging_lines()
        self._update_image_display()
    
    def _setup_image_plot(self):
        """Setup the image display and histogram."""
        # Initialize empty image display
        if self.spectrum_image_data is not None:
            # Setup image display with actual data
            self.setup_image_display(self.spectrum_image_data.data.T)  # Transpose for wavelength on x-axis
            
            # Set coordinate mapping
            x_min_wl = self.spectrum_image_data.wavelengths[0] if len(self.spectrum_image_data.wavelengths) > 0 else 0
            x_max_wl = self.spectrum_image_data.wavelengths[-1] if len(self.spectrum_image_data.wavelengths) > 0 else self.spectrum_image_data.n_wavelengths
            y_min_x = self.spectrum_image_data.spatial_pixels[0] if len(self.spectrum_image_data.spatial_pixels) > 0 else 0
            y_max_x = self.spectrum_image_data.spatial_pixels[-1] if len(self.spectrum_image_data.spatial_pixels) > 0 else self.spectrum_image_data.n_spatial
            
            self.set_image_rect(x_min_wl, y_min_x, x_max_wl - x_min_wl, y_max_x - y_min_x)
        else:
            # Setup empty image display
            import numpy as np
            empty_data = np.zeros((10, 10))
            self.setup_image_display(empty_data)
            self.set_image_rect(0, 0, 10, 10)
        
        # Lambda label removed per user request
        
        # Configure plot interaction
        self.plotItem.setMenuEnabled(False)
        self.plotItem.vb.mouseButtons = {
            QtCore.Qt.LeftButton: pg.ViewBox.PanMode,
            QtCore.Qt.MiddleButton: pg.ViewBox.RectMode,
            QtCore.Qt.RightButton: None
        }
        self.plotItem.vb.installEventFilter(self)
    
    def _update_image_display(self):
        """Update the image display with current data."""
        if self.spectrum_image_data is not None:
            self.setup_image_display(self.spectrum_image_data.data.T)
            
            # Update coordinate mapping
            x_min_wl = self.spectrum_image_data.wavelengths[0] if len(self.spectrum_image_data.wavelengths) > 0 else 0
            x_max_wl = self.spectrum_image_data.wavelengths[-1] if len(self.spectrum_image_data.wavelengths) > 0 else self.spectrum_image_data.n_wavelengths
            y_min_x = self.spectrum_image_data.spatial_pixels[0] if len(self.spectrum_image_data.spatial_pixels) > 0 else 0
            y_max_x = self.spectrum_image_data.spatial_pixels[-1] if len(self.spectrum_image_data.spatial_pixels) > 0 else self.spectrum_image_data.n_spatial
            
            self.set_image_rect(x_min_wl, y_min_x, x_max_wl - x_min_wl, y_max_x - y_min_x)
    
    def _setup_averaging_lines(self):
        """Setup vertical averaging lines."""
        if self.spectrum_image_data is None:
            return
            
        # Get initial positions (center region of wavelength range)
        n_wl = self.spectrum_image_data.n_wavelengths
        center_idx = n_wl // 2
        width = max(self.min_line_distance, n_wl // 10)  # 10% of range or minimum distance
        
        left_idx = max(0, center_idx - width // 2)
        right_idx = min(n_wl - 1, center_idx + width // 2)
        center_idx = (left_idx + right_idx) // 2
        
        # Create averaging lines
        self.line1 = AddLine(self.plotItem, self.avg_colors[1], left_idx, moveable=True, orientation='vertical')
        self.line2 = AddLine(self.plotItem, self.avg_colors[1], right_idx, moveable=True, orientation='vertical')
        self.center_line = AddLine(self.plotItem, self.avg_colors[1], center_idx, moveable=True, orientation='vertical')
        
        # Set line styles
        self.center_line.setPen(pg.mkPen(self.avg_colors[1], style=QtCore.Qt.DashLine, width=2))
        
        # Connect line movement signals
        self.line1.sigPositionChanged.connect(lambda: self._update_lines_and_emit(self.line1))
        self.line2.sigPositionChanged.connect(lambda: self._update_lines_and_emit(self.line2))
        self.center_line.sigPositionChanged.connect(lambda: self._update_lines_and_emit(self.center_line))
        
        # Initialize averaging region in model
        self.spectrum_image_data.set_averaging_region(float(left_idx), float(center_idx), float(right_idx))
        # Lambda label update removed per user request
    
    def _setup_axes(self):
        """Setup axis labels and ranges."""
        self.set_axis_labels("Wavelength", "Spatial Position", "Å", "pixels")
    
    def _setup_crosshair(self):
        """Setup interactive crosshair."""
        if self.spectrum_image_data is None:
            return
            
        # Create crosshair lines
        self.h_line = AddLine(self.plotItem, self.crosshair_colors['h_image'], 
                             self.spectrum_image_data.n_spatial // 2, moveable=True, orientation='horizontal')
        self.v_line = AddLine(self.plotItem, self.crosshair_colors['v'], 
                             self.spectrum_image_data.n_wavelengths // 2, moveable=True, orientation='vertical')
        
        # Connect crosshair movement
        self.h_line.sigPositionChanged.connect(self._on_crosshair_moved)
        self.v_line.sigPositionChanged.connect(self._on_crosshair_moved)
    
    def _on_crosshair_moved(self):
        """Handle crosshair movement and emit signal."""
        if self.crosshair_locked:
            return
            
        wl_pos = self.v_line.value()
        spatial_pos = self.h_line.value()
        
        # Update model
        self.spectrum_image_data.update_crosshair(wl_pos, spatial_pos)
        
        # Update label
        self.updateLabelFromCrosshair(wl_pos, spatial_pos)
        
        # Emit signal
        self.crosshairMoved.emit(wl_pos, spatial_pos, self.stokes_index)
    
    def _clamp_line_position(self, pos: float) -> float:
        """Clamp line position to valid range."""
        return max(0, min(self.spectrum_image_data.n_wavelengths - 1, pos))
    
    def _update_lines_and_emit(self, source_line=None):
        """Update averaging lines and emit averaging region change signal."""
        if not all([self.line1, self.line2, self.center_line]):
            return
        
        # Block signals to prevent feedback loops
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
            
            # Update positions based on which line moved
            if source_line is self.line1:
                new_l1 = self._clamp_line_position(current_l1)
                new_l2_candidate = new_l1 + (current_l2 - current_l1)
                new_l2 = self._clamp_line_position(max(new_l2_candidate, new_l1 + self.min_line_distance))
                new_center = (new_l1 + new_l2) / 2
            elif source_line is self.line2:
                new_l2 = self._clamp_line_position(current_l2)
                new_l1_candidate = new_l2 - (current_l2 - current_l1)
                new_l1 = self._clamp_line_position(min(new_l1_candidate, new_l2 - self.min_line_distance))
                new_center = (new_l1 + new_l2) / 2
            elif source_line is self.center_line:
                new_center = self._clamp_line_position(current_center)
                spacing = (current_l2 - current_l1) / 2
                
                if spacing < self.min_line_distance / 2:
                    spacing = self.min_line_distance / 2
                
                new_l1 = self._clamp_line_position(new_center - spacing)
                new_l2 = self._clamp_line_position(new_center + spacing)
            
            # Ensure minimum distance
            if (new_l2 - new_l1) < self.min_line_distance:
                if source_line is self.line1:
                    new_l2 = self._clamp_line_position(new_l1 + self.min_line_distance)
                elif source_line is self.line2:
                    new_l1 = self._clamp_line_position(new_l2 - self.min_line_distance)
                else:
                    center_temp = (new_l1 + new_l2) / 2
                    new_l1 = self._clamp_line_position(center_temp - self.min_line_distance / 2)
                    new_l2 = self._clamp_line_position(center_temp + self.min_line_distance / 2)
            
            # Update line positions
            self.line1.setValue(new_l1)
            self.line2.setValue(new_l2)
            self.center_line.setValue((new_l1 + new_l2) / 2)
            
            # Lambda label update removed per user request
            
            # Update model
            self.spectrum_image_data.set_averaging_region(new_l1, (new_l1 + new_l2) / 2, new_l2)
            
            # Emit signal
            self.avgRegionChanged.emit(new_l1, (new_l1 + new_l2) / 2, new_l2, self.stokes_index)
            
        finally:
            # Restore signals
            self.line1.blockSignals(False)
            self.line2.blockSignals(False)
            self.center_line.blockSignals(False)
    
    # Lambda label method removed per user request
    
    def updateLabelFromCrosshair(self, xpos_wl: float, ypos_spatial_x: float):
        """Update label from crosshair position."""
        # Find nearest indices
        wl_idx = np.argmin(np.abs(self.spectrum_image_data.wavelengths - xpos_wl))
        spatial_idx = np.argmin(np.abs(self.spectrum_image_data.spatial_pixels - ypos_spatial_x))
        
        # Get intensity value
        if 0 <= wl_idx < self.spectrum_image_data.n_wavelengths and 0 <= spatial_idx < self.spectrum_image_data.n_spatial:
            intensity = self.spectrum_image_data.data[wl_idx, spatial_idx]
        else:
            intensity = np.nan
        
        self.update_label(f"λ={xpos_wl:.1f}, x={ypos_spatial_x:.2f}, z={intensity:.5f}")
    
    def set_crosshair_position(self, xpos_wl: float, ypos_spatial_x: float):
        """Set crosshair position programmatically."""
        self.crosshair_locked = True
        
        self.v_line.blockSignals(True)
        self.h_line.blockSignals(True)
        
        self.v_line.setValue(xpos_wl)
        self.h_line.setValue(ypos_spatial_x)
        
        self.v_line.blockSignals(False)
        self.h_line.blockSignals(False)
        
        self.crosshair_locked = False
        
        # Update model and label
        self.spectrum_image_data.update_crosshair(xpos_wl, ypos_spatial_x)
        self.updateLabelFromCrosshair(xpos_wl, ypos_spatial_x)
    
    def update_horizontal_crosshair(self, ypos_spatial_x: float):
        """Update only the horizontal crosshair line from spatial window."""
        self.h_line.blockSignals(True)
        self.h_line.setValue(ypos_spatial_x)
        self.h_line.blockSignals(False)
        
        # Update label with current crosshair position
        if self.last_valid_crosshair_pos:
            self.updateLabelFromCrosshair(self.last_valid_crosshair_pos[0], ypos_spatial_x)
            self.last_valid_crosshair_pos = (self.last_valid_crosshair_pos[0], ypos_spatial_x)
