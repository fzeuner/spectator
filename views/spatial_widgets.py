"""
Spatial-specific widget classes for the spectral data viewer.

This module contains widgets for displaying spatial profile data.
"""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from typing import Optional

from .base_widgets import BasePlotWidget
from models import SpatialData

# Import existing functions for compatibility
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SpatialPlotWidget(BasePlotWidget):
    """
    Widget for displaying 1D spatial profile plots.
    
    Shows spatial intensity profiles with interactive crosshair and wavelength tracking.
    """
    
    # Signals
    xChanged = QtCore.pyqtSignal(float)  # Emit spatial position
    hLineChanged = QtCore.pyqtSignal(float)  # Emit horizontal line position
    
    def __init__(self, spatial_data: Optional[SpatialData] = None, stokes_index: int = 0, 
                 name: str = "", parent: Optional[QtWidgets.QWidget] = None):
        """
        Initialize spatial plot widget.
        
        Args:
            spatial_data: SpatialData model instance (optional)
            stokes_index: Index for multi-state data
            name: Widget name for identification
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.spatial_data = spatial_data
        self.stokes_index = stokes_index
        self.name = name or "Spatial Profile"
        
        # Store full data reference for updates
        self.full_data = None  # Will be set by parent controller
        self.wavelength = None  # Will be set by parent controller
        
        if self.spatial_data is not None:
            self.x = spatial_data.spatial_pixels
            # Current data slice
            self.plot_data = spatial_data.data
            self.current_wl_idx = 0
        else:
            self.x = None
            self.plot_data = None
            self.current_wl_idx = 0
        
        self._setup_plot_items()
        if self.spatial_data is not None:
            self._setup_connections()
            self._initialize_plot_state()
    
    def set_data(self, spatial_data: SpatialData):
        """Set the spatial data and initialize the widget."""
        self.spatial_data = spatial_data
        self.x = spatial_data.spatial_pixels
        self.plot_data = spatial_data.data
        self.current_wl_idx = 0
        self._setup_connections()
        self._initialize_plot_state()
        self._update_plot()
    
    def _setup_plot_items(self):
        """Initialize plot curve, movable line, and label."""
        # Main spatial profile curve
        self.plot_curve = pg.PlotDataItem()
        self.plotItem.addItem(self.plot_curve)
        
        # Averaged spatial profile curve (different color/style)
        self.plot_curve_avg = pg.PlotDataItem(
            pen=pg.mkPen(self.avg_colors[1], style=QtCore.Qt.SolidLine, width=2)
        )
        self.plotItem.addItem(self.plot_curve_avg)
        
        # Horizontal crosshair line
        self.hLine = AddLine(self.plotItem, self.crosshair_colors['h_spectrum_image'], 0, moveable=True)
        
        # Average region label
        self.label_avg = pg.LabelItem(justify='left', size='6pt', color=self.avg_colors[1])
        self.graphics_widget.addItem(self.label_avg, row=1, col=1)
        
        # Initialize plot appearance
        InitializeSpectrumplotItem(self.plotItem, y_label="x", x_label="", x_units="")
    
    def _setup_connections(self):
        """Connect signals to slots."""
        # Connect line movement to handlers
        self.hLine.sigPositionChanged.connect(self._on_hline_moved)
    
    def _initialize_plot_state(self):
        """Set initial plot data, hLine position, and update labels."""
        # Set initial data
        self.update_spatial_data_from_model()
        
        # Set initial line position
        if len(self.spatial_data.spatial_pixels) > 0:
            initial_pos = self.spatial_data.spatial_pixels[len(self.spatial_data.spatial_pixels) // 2]
            self.hLine.setValue(initial_pos)
            self.spatial_data.update_crosshair(initial_pos)
        
        # Update initial label
        self._update_label()
    
    def update_spatial_data_from_model(self):
        """Update plot data from the spatial data model."""
        spatial_pixels = self.spatial_data.spatial_pixels
        intensities = self.spatial_data.data
        
        self.plot_curve.setData(spatial_pixels, intensities)
        self.plot_data = intensities
        self._update_label()
    
    def _update_label(self):
        """Update the coordinate label."""
        if len(self.spatial_data.spatial_pixels) == 0:
            return
            
        # Get current position from crosshair
        x_value = self.hLine.value()
        x_idx = self.spatial_data.find_nearest_index(x_value)
        intensity_value = self.spatial_data.get_value_at_position(x_idx)
        
        self.update_label(f"x={x_value:.1f}, z={intensity_value:.5f}")
    
    def _on_hline_moved(self):
        """Handle internal hLine movement and emit signal."""
        x_value = self.hLine.value()
        self.spatial_data.update_crosshair(x_value)
        self._update_label()
        self._emit_hline_changed()
        self.xChanged.emit(x_value)
    
    def _emit_hline_changed(self):
        """Emit signal when horizontal line position changes."""
        self.hLineChanged.emit(self.hLine.value())
    
    def update_x_line(self, y: float):
        """
        Update the hLine position from external signal.
        
        Args:
            y: New horizontal line position
        """
        self.hLine.blockSignals(True)
        self.hLine.setValue(y)
        self.hLine.blockSignals(False)
        
        self.spatial_data.update_crosshair(y)
        self._update_label()
    
    def update_spatial_data(self, wl_idx: int):
        """
        Update the plotted spatial data based on a new wavelength index.
        
        Args:
            wl_idx: New wavelength index
        """
        if self.full_data is None:
            return
            
        self.current_wl_idx = wl_idx
        
        # Extract spatial slice at this wavelength
        if 0 <= wl_idx < self.full_data.shape[0]:
            new_data = self.full_data[wl_idx, :]
            
            # Update model
            if hasattr(self.spatial_data, 'update_data'):
                wavelength_value = self.wavelength[wl_idx] if self.wavelength is not None else float(wl_idx)
                self.spatial_data.update_data(new_data, wavelength_value)
            else:
                self.spatial_data.data = new_data
                self.spatial_data.current_wavelength = float(wl_idx)
            
            # Update plot
            self.plot_curve.setData(self.x, new_data)
            self.plot_data = new_data
            
        self._update_label()
    
    def update_from_spectrum_crosshair(self, xpos_wl: float, ypos_spatial_x: float, source_stokes_index: int):
        """
        Update spatial window based on crosshair movement in spectrum image.
        
        Args:
            xpos_wl: Wavelength position from spectrum image
            ypos_spatial_x: Spatial position from spectrum image
            source_stokes_index: Source stokes index
        """
        # Update horizontal line position
        self.update_x_line(ypos_spatial_x)
        
        # Update spatial data based on wavelength
        if self.wavelength is not None:
            wl_idx = np.argmin(np.abs(self.wavelength - xpos_wl))
            self.update_spatial_data_wl(wl_idx)
    
    def set_full_data_reference(self, full_data: np.ndarray, wavelength: np.ndarray):
        """
        Set reference to full data for wavelength-based updates.
        
        Args:
            full_data: Full 2D data array (wavelength, spatial)
            wavelength: Wavelength array
        """
        self.full_data = full_data
        self.wavelength = wavelength
