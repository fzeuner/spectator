# --- Data Display Widgets ---

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui
from typing import List, Tuple, Dict, Optional, Any

from .base_widgets import BasePlotWidget
from ..utils.constants import (
    MIN_LINE_DISTANCE, ColorSchemes, TICK_FONT
)
from ..utils.colors import getWidgetColors
from ..utils.averaging_lines import AveragingLineManager
from ..utils import (
    add_line, add_crosshair, create_histogram, 
    initialize_spectrum_plot_item, initialize_image_plot_item,
    set_plot_wavelength_range, reset_plot_wavelength_range, update_crosshair_from_mouse
)
from ..utils.plotting import SOLID_LINE
from ..models import PlotDataModel, AxisConfigs

class StokesSpatialWindow(BasePlotWidget):
    
    xChanged = QtCore.pyqtSignal(float) # Emit x value of hLine
    hLineChanged = QtCore.pyqtSignal(float) # Emit when horizontal line position changes

    def __init__(self, data: np.ndarray, stokes_index: int, name: str, config: AxisConfig = None):
        super().__init__(None)

        self.name = name + " spatial"
        
        # Use data model for axis handling
        if config is None:
            config = AxisConfigs.spatial_window()  # Default for spectator_viewer
        self.data_model = PlotDataModel(data, config)
        
        # Initialize current index
        self.current_wl_idx = self.data_model.get_dimension_size(0) // 2

        self._setup_plot_items()
        self._setup_connections()
        self._initialize_plot_state()

    def _setup_plot_items(self):
        """Initializes plot curve, movable line, and label."""
        self.plot_curve = pg.PlotDataItem() 
        self.plotItem.addItem(self.plot_curve)
        
        colors = getWidgetColors()
        self.plot_curve_avg = pg.PlotDataItem(pen=pg.mkPen(colors.get('averaging_v', 'yellow'), style=SOLID_LINE, width=2)) 
        self.plotItem.addItem(self.plot_curve_avg)

        colors = getWidgetColors()
        # Use vertical line (angle=90) since x is now on x-axis
        config = self.data_model.config
        line_angle = 90 if config.line_angle == 0 else 0  # config.line_angle=0 means vertical in our convention
        self.hLine = add_line(self.plotItem, colors.get('draggable_line', 'white'), line_angle, moveable=True)

        self.label_avg = pg.LabelItem(justify='left', size='8pt', color=colors.get('averaging_v', 'yellow'))
        self.graphics_widget.addItem(self.label_avg, row=1, col=1) 

        # Use axis labels from config
        config = self.data_model.config
        initialize_spectrum_plot_item(self.plotItem, y_label=config.y_label, y_units=config.y_units, 
                                      x_label=config.x_label, x_units=config.x_units)
        
        # Use BasePlotWidget methods for standardized axis setup
        self.setup_standard_axes(left_width=30, top_height=15)
        self.setup_custom_ticks(spectral_range=self.data_model.get_dimension_size(1))

    def _setup_connections(self):
        """Connects signals to slots."""
        self.hLine.sigPositionChanged.connect(self._on_hline_moved)
        self.hLine.sigPositionChanged.connect(self._emit_hline_changed)

    def _initialize_plot_state(self):
        """Sets initial plot data, vLine position, and updates labels."""
        # Get slice using data model
        self.plot_data = self.data_model.get_slice_at_index(0, self.current_wl_idx)
        x_coords, y_coords = self.data_model.get_plot_data(self.plot_data)
        self.plot_curve.setData(x_coords, y_coords)

        # Set initial hLine position to center
        x_indices = self.data_model.get_index_array(1)
        initial_x = (x_indices[0] + x_indices[-1]) / 2 if x_indices.size > 1 else (x_indices[0] if x_indices.size > 0 else 0)
        self.update_x_line(initial_x) 

    def _update_label(self):
        """Updates the coordinate label."""
        # Get the spatial position from the horizontal line
        spatial_pos = self.hLine.value()
        # Find the closest spatial index
        x_indices = self.data_model.get_index_array(1)
        spatial_idx = np.argmin(np.abs(x_indices - spatial_pos)) if x_indices.size > 0 else 0
        
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
        # Validate and clamp index
        wl_idx = self.data_model.validate_index(0, wl_idx)
        
        self.current_wl_idx = wl_idx
        self.plot_data = self.data_model.get_slice_at_index(0, wl_idx)
        x_coords, y_coords = self.data_model.get_plot_data(self.plot_data)
        self.plot_curve.setData(x_coords, y_coords)
        self._update_label()    

    def update_spatial_data_wl_avg(self, wl_idx_l: int, wl_idx_c: int , wl_idx_h: int):
            """Updates the plotted spectrum data based on a new spatial indices of averaging regions."""

            self.current_wl_idx_avg = wl_idx_c
            self.plot_data_avg = self.data_model.get_averaged_slice(0, wl_idx_l, wl_idx_h)
            x_coords, y_coords = self.data_model.get_plot_data(self.plot_data_avg)
            self.plot_curve_avg.setData(x_coords, y_coords)
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
                x_indices = self.data_model.get_index_array(1)
                spatial_idx = np.argmin(np.abs(x_indices - spatial_pos)) if x_indices.size > 0 else 0
                
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
    
    @QtCore.pyqtSlot(float, float, float, int)
    def handle_spectral_avg_line_movement(self, x_low: float, x_center: float, x_high: float, source_stokes_index: int):
        """Handle spectral averaging line movement from spectrum image window."""
        # Convert x positions to spectral indices
        x_idx_low = self.data_model.validate_index(0, int(np.round(x_low)))
        x_idx_center = self.data_model.validate_index(0, int(np.round(x_center)))
        x_idx_high = self.data_model.validate_index(0, int(np.round(x_high)))
        
        # Update spatial data with spectral averaging
        self.update_spatial_data_wl_avg(x_idx_low, x_idx_center, x_idx_high)

    def update_spatial_range(self, min_val, max_val):
        """Updates the spatial (x pixel) axis range of the spatial plot (x-axis)."""
        x_indices = self.data_model.get_index_array(1)
        set_plot_wavelength_range(self.plotItem, x_indices, min_val, max_val, axis='x')

    def reset_spatial_range(self):
        """Resets the spatial (x pixel) axis range to full range on the spatial plot (x-axis)."""
        x_indices = self.data_model.get_index_array(1)
        reset_plot_wavelength_range(self.plotItem, x_indices, axis='x')
    
    def set_spatial_limits(self, y_min: float, y_max: float):
        """Set Y-axis limits based on spatial range from SpectrumImageWindow zoom."""
        try:
            self.plotItem.setXRange(y_min, y_max, padding=0)
        except Exception:
            pass
    
    @QtCore.pyqtSlot(float)
    @QtCore.pyqtSlot(float, float, int)
    def update_from_spectrum_crosshair(self, xpos_wl: float, ypos_spatial_x: float, source_stokes_index: int):
        """Update spatial window based on crosshair movement in spectrum image."""
        # Update horizontal line position to match spectrum image crosshair
        self.hLine.blockSignals(True)  # Prevent feedback loop
        self.hLine.setPos(ypos_spatial_x)
        self.hLine.blockSignals(False)
        
        # Update spatial data slice based on vertical line (spectral) position
        spectral_idx = self.data_model.validate_index(0, int(np.round(xpos_wl)))
        self.update_spatial_data_spectral(spectral_idx)
    
    def update_spatial_data_spectral(self, spectral_idx: int):
        """Update spatial data based on spectral index."""
        # Validate and clamp index
        spectral_idx = self.data_model.validate_index(0, spectral_idx)
        
        self.current_spectral_idx = spectral_idx
        self.plot_data = self.data_model.get_slice_at_index(0, spectral_idx)
        x_coords, y_coords = self.data_model.get_plot_data(self.plot_data)
        self.plot_curve.setData(x_coords, y_coords)
        self._update_label()
    
    def set_spectral_limits(self, x_min: float, x_max: float):
        """Set X-axis limits based on spectral range from SpectrumImageWindow zoom."""
        try:
            self.plotItem.setXRange(x_min, x_max, padding=0)
        except Exception:
            pass

    def set_full_data(self, data: np.ndarray):
        if data.ndim != 2:
            raise ValueError(f"StokesSpatialWindow expects 2D data (spectral, x); got shape {data.shape}")

        # Update data model
        self.data_model.update_data(data)

        # Keep current indices in bounds
        self.current_wl_idx = self.data_model.validate_index(0, getattr(self, 'current_wl_idx', 0))
        self.current_spectral_idx = self.data_model.validate_index(0, getattr(self, 'current_spectral_idx', self.current_wl_idx))

        # Refresh plot using spectral index if available, otherwise current_wl_idx
        idx = self.current_spectral_idx
        self.plot_data = self.data_model.get_slice_at_index(0, idx)
        x_coords, y_coords = self.data_model.get_plot_data(self.plot_data)
        self.plot_curve.setData(x_coords, y_coords)
        self._update_label()

class StokesSpectrumWindow(BasePlotWidget):
    yRangeChanged = QtCore.pyqtSignal(tuple)  # Emit (min, max)
    spectralChanged = QtCore.pyqtSignal(float) # Emit spectral value

    def __init__(self, data: np.ndarray, stokes_index: int, name: str):
        super().__init__(None)

        self.name = name + " spectrum"
        
        # Use data model for axis handling
        config = AxisConfigs.spectrum_window()
        self.data_model = PlotDataModel(data, config)
        
        # Initialize current index
        self.current_x_idx = self.data_model.get_dimension_size(1) // 2

        self._setup_plot_items()
        self._setup_connections()
        self._initialize_plot_state()

    def _setup_plot_items(self):
        """Initializes plot curve, movable line, and label."""
        self.plot_curve = pg.PlotDataItem() 
        self.plotItem.addItem(self.plot_curve)
        
        colors = getWidgetColors()
        self.plot_curve_spectral_avg = pg.PlotDataItem(pen=pg.mkPen(colors.get('averaging_h', 'dodgerblue'), style=SOLID_LINE, width=2)) 
        self.plotItem.addItem(self.plot_curve_spectral_avg)

        colors = getWidgetColors()
        self.vLine = add_line(self.plotItem, colors.get('draggable_line', 'white'), 90, moveable=True)

        self.label_avg = pg.LabelItem(justify='left', size='8pt', color=colors.get('averaging_h', 'dodgerblue'))      
        self.graphics_widget.addItem(self.label_avg, row=1, col=1) 

        initialize_spectrum_plot_item(self.plotItem, y_label="z")
        
        # Use BasePlotWidget methods for standardized axis setup
        self.setup_standard_axes(left_width=30, top_height=15)

    def _setup_connections(self):
        """Connects signals to slots."""
        self.plotItem.getViewBox().sigYRangeChanged.connect(self._emit_y_range_changed)
        self.vLine.sigPositionChanged.connect(self._on_vline_moved)

    def _initialize_plot_state(self):
        """Sets initial plot data, vLine position, and updates labels."""
        # Get slice using data model
        self.plot_data = self.data_model.get_slice_at_index(1, self.current_x_idx)
        x_coords, y_coords = self.data_model.get_plot_data(self.plot_data)
        self.plot_curve.setData(x_coords, y_coords)

        # Emit initial Y range and update label
        self._emit_y_range_changed(None, self.plotItem.viewRange()[1])

        # Set initial vLine position to center
        spectral_indices = self.data_model.get_index_array(0)
        initial_spectral = (spectral_indices[0] + spectral_indices[-1]) / 2 if spectral_indices.size > 1 else (spectral_indices[0] if spectral_indices.size > 0 else 0)
        self.update_spectral_line(initial_spectral) 

    def _update_label(self):
        """Updates the coordinate label."""
        spectral_value = self.vLine.value()
        # Find the closest index to the current spectral value
        spectral_indices = self.data_model.get_index_array(0)
        spectral_idx = np.argmin(np.abs(spectral_indices - spectral_value)) if spectral_indices.size > 0 else -1
        intensity_value = np.nan
        if isinstance(self.plot_data, np.ndarray) and self.plot_data.ndim == 1 and 0 <= spectral_idx < self.plot_data.size:
            intensity_value = self.plot_data[spectral_idx]

        self.label.setText(f"λ: {spectral_value:.0f}, z: {intensity_value:.5f}", size='8pt')
        
    def _update_label_x_avg(self):
        """Updates the coordinate label for averaged region."""
        # Use the white line position to pick the averaged z value, but only show z=
        wl_value = self.vLine.value() if hasattr(self, 'vLine') and self.vLine else self.current_x_idx_avg
        spectral_indices = self.data_model.get_index_array(0)
        wl_idx = np.argmin(np.abs(spectral_indices - wl_value)) if spectral_indices.size > 0 else -1
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
        spectral_indices = self.data_model.get_index_array(0)
        set_plot_wavelength_range(self.plotItem, spectral_indices, min_val, max_val, axis='x')
    
    def reset_spectral_range(self):
        """Resets the spectral-axis range to the initial maximum range."""
        spectral_indices = self.data_model.get_index_array(0)
        reset_plot_wavelength_range(self.plotItem, spectral_indices, axis='x')
    
    def set_spectral_limits(self, x_min: float, x_max: float):
        """Set X-axis limits based on spectral range from SpectrumImageWindow zoom."""
        try:
            self.plotItem.setXRange(x_min, x_max, padding=0)
        except Exception:
            pass

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
        # Validate and clamp index
        x_idx = self.data_model.validate_index(1, x_idx)

        self.current_x_idx = x_idx
        self.plot_data = self.data_model.get_slice_at_index(1, x_idx)
        x_coords, y_coords = self.data_model.get_plot_data(self.plot_data)
        self.plot_curve.setData(x_coords, y_coords)
        self._update_label()    

    def update_spectrum_data_x_avg(self, x_idx_l: int, x_idx_c: int , x_idx_h: int):
        """Updates the plotted spectrum data based on a new spatial indices of averaging regions."""
        self.current_x_idx_avg = x_idx_c
        self.plot_data_avg = self.data_model.get_averaged_slice(1, x_idx_l, x_idx_h)
        x_coords, y_coords = self.data_model.get_plot_data(self.plot_data_avg)
        self.plot_curve_spectral_avg.setData(x_coords, y_coords)
        self._update_label_x_avg()
    
    @QtCore.pyqtSlot(float, float, float, int)
    def handle_spatial_avg_line_movement(self, y_low: float, y_center: float, y_high: float, source_stokes_index: int):
        """Handle spatial averaging line movement from spectrum image window."""
        # Convert y positions to spatial indices
        y_idx_low = self.data_model.validate_index(1, int(np.round(y_low)))
        y_idx_center = self.data_model.validate_index(1, int(np.round(y_center)))
        y_idx_high = self.data_model.validate_index(1, int(np.round(y_high)))
        
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

    def set_full_data(self, data: np.ndarray):
        if data.ndim != 2:
            raise ValueError(f"StokesSpectrumWindow expects 2D data (spectral, x); got shape {data.shape}")

        # Update data model
        self.data_model.update_data(data)

        # Clamp current_x_idx
        self.current_x_idx = self.data_model.validate_index(1, getattr(self, 'current_x_idx', 0))

        # Refresh plot
        self.plot_data = self.data_model.get_slice_at_index(1, self.current_x_idx)
        x_coords, y_coords = self.data_model.get_plot_data(self.plot_data)
        self.plot_curve.setData(x_coords, y_coords)
        self._emit_y_range_changed(None, self.plotItem.viewRange()[1])
        self._update_label()


class StokesSpatialYWindow(BasePlotWidget):
    yChanged = QtCore.pyqtSignal(float)

    def __init__(self, data_cube: np.ndarray, stokes_index: int, name: str):
        super().__init__(None)

        self.name = name + " spatial y"
        self.stokes_index = stokes_index
        self.full_cube = data_cube
        if self.full_cube.ndim != 3:
            raise ValueError(f"StokesSpatialYWindow expects 3D data (y, spectral, x); got shape {self.full_cube.shape}")

        self.n_y, self.n_spectral, self.n_x = self.full_cube.shape
        self.y_pixels = np.arange(self.n_y)

        self.current_y_idx = int(self.n_y // 2) if self.n_y > 0 else 0
        self.current_spectral_idx = int(self.n_spectral // 2) if self.n_spectral > 0 else 0
        self.current_x_idx = int(self.n_x // 2) if self.n_x > 0 else 0

        self.plot_curve = pg.PlotDataItem()
        self.plotItem.addItem(self.plot_curve)

        colors = getWidgetColors()
        self.hLine = add_line(self.plotItem, colors.get('draggable_line', 'white'), 0, moveable=True)
        self.hLine.sigPositionChanged.connect(self._on_hline_moved)

        self.label = pg.LabelItem(justify='left', size='8pt')
        self.graphics_widget.addItem(self.label, row=1, col=1)

        # x-axis: intensity z, y-axis: spatial_y
        initialize_spectrum_plot_item(self.plotItem, y_label="y", y_units="pixel", x_label="z", x_units="")
        self.setup_standard_axes(left_width=30, top_height=15)
        self.setup_custom_ticks(spatial_range=len(self.y_pixels))
        self.configure_axis_styling(hide_left_label=True, right_label="y", right_units="pixel")

        self._refresh_profile()
        self.hLine.setPos(float(self.current_y_idx))

    def _profile_data(self) -> np.ndarray:
        if self.n_y == 0:
            return np.array([])
        return self.full_cube[:, self.current_spectral_idx, self.current_x_idx]

    def _refresh_profile(self):
        prof = self._profile_data()
        # Plot z horizontally, y vertically
        self.plot_curve.setData(prof, self.y_pixels)
        self._update_label()

    def _update_label(self):
        y_pos = float(self.hLine.value()) if hasattr(self, 'hLine') else float(self.current_y_idx)
        y_idx = int(np.clip(np.round(y_pos), 0, self.n_y - 1)) if self.n_y > 0 else 0

        z = np.nan
        if self.n_y > 0:
            z = float(self.full_cube[y_idx, self.current_spectral_idx, self.current_x_idx])
        self.label.setText(f"y={y_pos:.0f}, z={z:.5f}", size='8pt')

    def _on_hline_moved(self):
        y_pos = float(self.hLine.value())
        self.current_y_idx = int(np.clip(np.round(y_pos), 0, self.n_y - 1)) if self.n_y > 0 else 0
        self.yChanged.emit(y_pos)
        self._update_label()

    def set_full_cube(self, data_cube: np.ndarray):
        if data_cube.ndim != 3:
            raise ValueError(f"StokesSpatialYWindow expects 3D data (y, spectral, x); got shape {data_cube.shape}")
        self.full_cube = data_cube
        self.n_y, self.n_spectral, self.n_x = self.full_cube.shape
        self.y_pixels = np.arange(self.n_y)

        self.current_y_idx = int(np.clip(self.current_y_idx, 0, max(self.n_y - 1, 0)))
        self.current_spectral_idx = int(np.clip(self.current_spectral_idx, 0, max(self.n_spectral - 1, 0)))
        self.current_x_idx = int(np.clip(self.current_x_idx, 0, max(self.n_x - 1, 0)))
        self._refresh_profile()

    # Keep naming consistent with other windows
    def set_full_data(self, data: np.ndarray):
        self.set_full_cube(data)

    def update_profile(self, spectral_idx: int, x_idx: int):
        if self.n_spectral == 0 or self.n_x == 0:
            return
        self.current_spectral_idx = int(np.clip(spectral_idx, 0, self.n_spectral - 1))
        self.current_x_idx = int(np.clip(x_idx, 0, self.n_x - 1))
        self._refresh_profile()

    def update_spatial_data_spectral(self, spectral_idx: int):
        """Alias to mirror StokesSpatialWindow.update_spatial_data_spectral."""
        self.update_spectral_index(int(spectral_idx))

    @QtCore.pyqtSlot(float)
    def update_y_line(self, y_pos: float):
        if not hasattr(self, 'hLine'):
            return
        if np.isclose(self.hLine.value(), y_pos):
            return
        self.hLine.blockSignals(True)
        try:
            self.hLine.setPos(float(y_pos))
            self.current_y_idx = int(np.clip(np.round(y_pos), 0, self.n_y - 1)) if self.n_y > 0 else 0
            self._update_label()
        finally:
            self.hLine.blockSignals(False)

    @QtCore.pyqtSlot(float, float, int)
    def update_from_spectrum_image_crosshair(self, xpos_wl: float, ypos_spatial_x: float, source_stokes_index: int):
        spectral_idx = int(np.clip(np.round(xpos_wl), 0, self.n_spectral - 1)) if self.n_spectral > 0 else 0
        x_idx = int(np.clip(np.round(ypos_spatial_x), 0, self.n_x - 1)) if self.n_x > 0 else 0
        self.update_profile(spectral_idx, x_idx)

    @QtCore.pyqtSlot(float, float, int)
    def update_from_scan_crosshair(self, xpos_spatial_x: float, ypos_spatial_y: float, source_stokes_index: int):
        """Update y profile from scan-image crosshair (x=spatial_x, y=spatial_y)."""
        x_idx = int(np.clip(np.round(xpos_spatial_x), 0, self.n_x - 1)) if self.n_x > 0 else 0
        self.update_profile(self.current_spectral_idx, x_idx)
        self.update_y_line(float(ypos_spatial_y))

    @QtCore.pyqtSlot(int)
    def update_spectral_index(self, spectral_idx: int):
        self.update_profile(int(spectral_idx), self.current_x_idx)

class StokesSpectrumImageWindow(BasePlotWidget):
    crosshairMoved = QtCore.pyqtSignal(float, float, int)
    avgRegionChanged = QtCore.pyqtSignal(float, float, float, int)
    spatialAvgRegionChanged = QtCore.pyqtSignal(float, float, float, int)
    viewRangeChanged = QtCore.pyqtSignal(float, float, float, float) # Emit (x_min, x_max, y_min, y_max) when zoom changes

    def __init__(self, data: np.ndarray, stokes_index: int, name: str, scale_info: dict = None, config: AxisConfig = None):
        super().__init__(None)

        self.stokes_index = stokes_index
        self.name = name
        self.scale_info = scale_info
        
        # Use data model with axis configuration
        if config is None:
            config = AxisConfigs.spectrum_image_window_default()
        self.data_model = PlotDataModel(data, config)
        
        # Store original data for image display
        self.data = data
        self.n_spectral = self.data_model.get_dimension_size(0)
        self.n_x_pixel = self.data_model.get_dimension_size(1) 

        self._setup_image_plot()
        self._setup_axes()
        self._setup_crosshair()
        self._setup_v_avg() 

    def _setup_image_plot(self):
        self.image_item = pg.ImageItem()
        self.plotItem.addItem(self.image_item)
        self.histogram = create_histogram(self.image_item, self.layout, self.scale_info, self.stokes_index)

        # Respect pyqtgraph's imageAxisOrder to avoid unintended transposes across versions
        axis_order = pg.getConfigOption('imageAxisOrder')
        
        # Transpose data based on axis configuration
        config = self.data_model.config
        if config.x_data_dim == 0 and config.y_data_dim == 1:
            # Default: spectral on x, spatial on y
            img = self.data.T if axis_order == 'row-major' else self.data
        else:
            # Swapped: spatial on x, spectral on y
            img = self.data if axis_order == 'row-major' else self.data.T
        
        self.image_item.setImage(img)

        # Set image rectangle based on which dimension is on which axis
        if config.x_data_dim == 0:
            # Spectral on x-axis, spatial on y-axis (default)
            x_min, x_max = 0, self.n_spectral - 1
            y_min, y_max = 0, self.n_x_pixel - 1
        else:
            # Spatial on x-axis, spectral on y-axis (swapped)
            x_min, x_max = 0, self.n_x_pixel - 1
            y_min, y_max = 0, self.n_spectral - 1

        width = x_max - x_min
        height = y_max - y_min
        self.image_item.setRect(x_min, y_min, width, height)

        self.plotItem.setMenuEnabled(False)
        self.plotItem.vb.mouseButtons = {
            QtCore.Qt.MouseButton.LeftButton: pg.ViewBox.PanMode,
            QtCore.Qt.MouseButton.MiddleButton: pg.ViewBox.RectMode,
            QtCore.Qt.MouseButton.RightButton: None
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
            if event.type() == QtCore.QEvent.Type.GraphicsSceneMousePress and event.button() == QtCore.Qt.MouseButton.RightButton:
                if self.spectral_averaging_enabled or self.spatial_averaging_enabled:
                    self._handleMousePress(event)
                    return True
                else:
                    # Block right-click completely when no averaging is enabled
                    return True
            # Block panning: consume middle-button drags entirely
            elif event.type() == QtCore.QEvent.Type.GraphicsSceneMousePress and event.button() == QtCore.Qt.MouseButton.MiddleButton:
                return True
            elif event.type() == QtCore.QEvent.Type.GraphicsSceneMouseMove and getattr(event, 'buttons', lambda: 0)() & QtCore.Qt.MouseButton.MiddleButton:
                return True
            elif event.type() == QtCore.QEvent.Type.GraphicsSceneMouseRelease and event.button() == QtCore.Qt.MouseButton.MiddleButton:
                return True
            elif event.type() == QtCore.QEvent.Type.GraphicsSceneMouseMove and self.right_button_pressed:
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
            elif event.type() == QtCore.QEvent.Type.GraphicsSceneMouseRelease and event.button() == QtCore.Qt.MouseButton.RightButton:
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
        config = self.data_model.config
        
        # Get axis labels from config
        initialize_image_plot_item(self.plotItem, y_values=True,
                                y_label=config.y_label, y_units=config.y_units, 
                                x_label=config.x_label, x_units=config.x_units)
        
        self.setup_standard_axes(left_width=30, top_height=15)
        
        # Set ticks based on which dimension is on which axis
        # config.x_data_dim: 0=spectral, 1=spatial
        if config.x_data_dim == 0:
            # Spectral on x-axis, spatial on y-axis (default)
            x_range = self.n_spectral
            y_range = self.n_x_pixel
        else:
            # Spatial on x-axis, spectral on y-axis (swapped)
            x_range = self.n_x_pixel
            y_range = self.n_spectral
        
        # Top axis shows x-axis dimension
        x_ticks_pix = np.linspace(0, x_range - 1, 8)
        x_ticks = [(tick, f'{tick:.0f}') for tick in x_ticks_pix]
        self.plotItem.getAxis('top').setTicks([x_ticks])
        
        # Also set bottom axis to same ticks (even though it's hidden) to prevent auto-ticks
        self.plotItem.getAxis('bottom').setTicks([x_ticks])
        
        # Right axis shows y-axis dimension
        y_ticks_pix = np.linspace(0, y_range - 1, 6)
        y_ticks = [(tick, f'{tick:.0f}') for tick in y_ticks_pix]
        self.plotItem.getAxis('right').setTicks([y_ticks])
        
        # Left axis should also show y-axis dimension ticks
        self.plotItem.getAxis('left').setTicks([y_ticks])
        
        # Configure axis styling
        self.plotItem.getAxis('left').showLabel(False)
        self.plotItem.getAxis('left').setStyle(showValues=True)
        self.plotItem.getAxis('left').enableAutoSIPrefix(False)
        self.plotItem.getAxis('right').setLabel(text=config.y_label, units=config.y_units)
        self.plotItem.getAxis('bottom').setStyle(showValues=False)
        self.plotItem.getAxis('top').setStyle(showValues=True, tickFont=TICK_FONT)
        
        # Set viewbox limits
        x_max = x_range - 1
        y_max = y_range - 1
        self.setup_viewbox_limits(x_max=x_max, y_max=y_max, min_range=1.0, enable_rect_zoom=True)
        
        try:
            self.plotItem.setXRange(0, x_max, padding=0)
            self.plotItem.setYRange(0, y_max, padding=0)
        except Exception:
            pass

        # Connect view range change signal to emit limits for synchronization
        try:
            vb.sigRangeChanged.connect(self._on_view_range_changed)
        except Exception:
            pass

    def _setup_crosshair(self):

        colors = getWidgetColors()
        self.vLine, self.hLine = add_crosshair(self.plotItem, colors.get('crosshair', 'white'), colors.get('crosshair', 'white'))
        self.plotItem.scene().sigMouseMoved.connect(self.updateCrosshairAndLabel)
        self.plotItem.scene().sigMouseClicked.connect(self.mouseClicked)
        self.last_valid_crosshair_pos = None
        self.crosshair_locked = False
        # Initialize crosshair at image center using data model
        config = self.data_model.config
        mid_x = (self.data_model.get_dimension_size(config.x_data_dim) - 1) / 2
        mid_y = (self.data_model.get_dimension_size(config.y_data_dim) - 1) / 2
        
        self.vLine.setPos(mid_x)
        self.hLine.setPos(mid_y)
        self.last_valid_crosshair_pos = (mid_x, mid_y)
        self.updateLabelFromCrosshair(mid_x, mid_y)
        
        # Add yellow spectral averaging label using same positioning as spectrum windows
        colors = getWidgetColors()
        self.label_avg_spectral = pg.LabelItem(justify='left', size='8pt', color=colors.get('averaging_v', 'yellow'))
        self.graphics_widget.addItem(self.label_avg_spectral, row=1, col=1)
        
        # Add blue spatial averaging label using same positioning as spectrum windows  
        self.label_avg_spatial = pg.LabelItem(justify='left', size='8pt', color=colors.get('averaging_h', 'dodgerblue'))
        self.graphics_widget.addItem(self.label_avg_spatial, row=1, col=2)
        
        # Initialize averaging line managers based on axis configuration
        config = self.data_model.config
        # Spectral averaging: along spectral dimension (dim 0)
        # Spatial averaging: along spatial dimension (dim 1)
        spectral_orientation = 'horizontal' if config.x_data_dim == 1 else 'vertical'
        spatial_orientation = 'vertical' if config.x_data_dim == 1 else 'horizontal'
        
        self.spectral_manager = AveragingLineManager(
            self.plotItem, spectral_orientation, self.n_spectral, self.stokes_index, 
            'averaging_v', self.label_avg_spectral
        )
        self.spatial_manager = AveragingLineManager(
            self.plotItem, spatial_orientation, self.n_x_pixel, self.stokes_index,
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

    def _on_view_range_changed(self, vb, ranges):
        """Emit view range changes to synchronize spectrum and spatial window limits."""
        try:
            x_range, y_range = ranges
            x_min, x_max = x_range
            y_min, y_max = y_range
            self.viewRangeChanged.emit(float(x_min), float(x_max), float(y_min), float(y_max))
        except Exception:
            pass

    def mouseClicked(self, event):
        if event.double():
            mouse_point = self.plotItem.vb.mapSceneToView(event.scenePos())
            if not self.crosshair_locked:
                xpos, ypos = mouse_point.x(), mouse_point.y()
                self.vLine.setPos(xpos)
                self.hLine.setPos(ypos)
                self.last_valid_crosshair_pos = (xpos, ypos)
                self.updateLabelFromCrosshair(xpos, ypos)
            self.crosshair_locked = not self.crosshair_locked

    def updateCrosshairAndLabel(self, pos: QtCore.QPointF):
        if not self.crosshair_locked:
            crosshair_pos = update_crosshair_from_mouse(self.plotItem, self.vLine, self.hLine, pos)
            if crosshair_pos is not None:
                xpos, ypos = crosshair_pos
                self.last_valid_crosshair_pos = (xpos, ypos)
                self.updateLabelFromCrosshair(xpos, ypos)
                
                # Emit spectral and spatial values in consistent order (spectral, spatial)
                config = self.data_model.config
                if config.x_data_dim == 0:  # spectral on x-axis
                    spectral_pos, spatial_pos = xpos, ypos
                else:  # spatial on x-axis
                    spectral_pos, spatial_pos = ypos, xpos
                
                self.crosshairMoved.emit(spectral_pos, spatial_pos, self.stokes_index)
        elif self.last_valid_crosshair_pos:
            self.updateLabelFromCrosshair(*self.last_valid_crosshair_pos)

    def updateLabelFromCrosshair(self, xpos: float, ypos: float):
        config = self.data_model.config
        
        # xpos and ypos are plot coordinates
        # Data is always stored as (spectral, spatial_x)
        # Need to map plot coordinates to data indices
        if config.x_data_dim == 0:  # spectral on x-axis, spatial on y-axis
            spectral_idx = int(np.clip(np.round(xpos), 0, self.n_spectral - 1))
            spatial_idx = int(np.clip(np.round(ypos), 0, self.n_x_pixel - 1))
        else:  # spatial on x-axis, spectral on y-axis
            spatial_idx = int(np.clip(np.round(xpos), 0, self.n_x_pixel - 1))
            spectral_idx = int(np.clip(np.round(ypos), 0, self.n_spectral - 1))
        
        # Access data in original (spectral, spatial_x) order
        intensity = self.data[spectral_idx, spatial_idx]
        
        self.label.setText(f"{config.x_label}: {xpos:.0f}, {config.y_label}: {ypos:.0f}, z: {intensity:.5f}", size='8pt') 

    def update_spectral_range(self, min_val, max_val):
        config = self.data_model.config
        axis = 'x' if config.x_data_dim == 0 else 'y'
        spectral_indices = self.data_model.get_index_array(0)
        set_plot_wavelength_range(self.plotItem, spectral_indices, min_val, max_val, axis=axis) 

    def reset_spectral_range(self):
        config = self.data_model.config
        axis = 'x' if config.x_data_dim == 0 else 'y'
        spectral_indices = self.data_model.get_index_array(0)
        reset_plot_wavelength_range(self.plotItem, spectral_indices, axis=axis) 

    def update_spatial_range(self, min_val, max_val):
        """Updates the spatial (x pixel) axis range of the image plot."""
        config = self.data_model.config
        axis = 'x' if config.x_data_dim == 1 else 'y'
        spatial_indices = self.data_model.get_index_array(1)
        set_plot_wavelength_range(self.plotItem, spatial_indices, min_val, max_val, axis=axis)

    def reset_spatial_range(self):
        """Resets the spatial (x pixel) axis range to the initial maximum range."""
        config = self.data_model.config
        axis = 'x' if config.x_data_dim == 1 else 'y'
        spatial_indices = self.data_model.get_index_array(1)
        reset_plot_wavelength_range(self.plotItem, spatial_indices, axis=axis)

    def updateExternalVLine(self, spectral_pos: float): 
        if not self.crosshair_locked:
            config = self.data_model.config
            if config.x_data_dim == 0:  # spectral on x-axis
                self.vLine.setPos(spectral_pos)
                current_y = self.hLine.value()
                self.last_valid_crosshair_pos = (spectral_pos, current_y)
                self.updateLabelFromCrosshair(spectral_pos, current_y)
            else:  # spectral on y-axis
                self.hLine.setPos(spectral_pos)
                current_x = self.vLine.value()
                self.last_valid_crosshair_pos = (current_x, spectral_pos)
                self.updateLabelFromCrosshair(current_x, spectral_pos)

    @QtCore.pyqtSlot(float, float)
    def set_crosshair_position(self, spectral_pos: float, spatial_pos: float): 
        if not self.crosshair_locked:
            # Convert spectral/spatial to plot x/y based on axis configuration
            config = self.data_model.config
            if config.x_data_dim == 0:  # spectral on x-axis
                xpos, ypos = spectral_pos, spatial_pos
            else:  # spatial on x-axis
                xpos, ypos = spatial_pos, spectral_pos
            
            self.vLine.setPos(xpos)
            self.hLine.setPos(ypos)
            self.updateLabelFromCrosshair(xpos, ypos)
            self.last_valid_crosshair_pos = (xpos, ypos)
    
    @QtCore.pyqtSlot(float)
    def update_horizontal_crosshair(self, spatial_pos: float):
        """Update only the horizontal crosshair line from spatial window."""
        if not self.crosshair_locked:
            config = self.data_model.config
            if config.x_data_dim == 0:  # spectral on x-axis, spatial on y-axis
                self.hLine.setPos(spatial_pos)
                current_x = self.vLine.value()
                self.last_valid_crosshair_pos = (current_x, spatial_pos)
                self.updateLabelFromCrosshair(current_x, spatial_pos)
            else:  # spatial on x-axis, spectral on y-axis
                self.vLine.setPos(spatial_pos)
                current_y = self.hLine.value()
                self.last_valid_crosshair_pos = (spatial_pos, current_y)
                self.updateLabelFromCrosshair(spatial_pos, current_y)
            # Update label with current crosshair position
            if self.last_valid_crosshair_pos:
                self.updateLabelFromCrosshair(self.last_valid_crosshair_pos[0], self.last_valid_crosshair_pos[1])
    
    @QtCore.pyqtSlot(float, float, int)
    def update_crosshair_from_sync(self, spectral_pos: float, spatial_pos: float, source_stokes_index: int):
        """Update crosshair position from synchronization with other states."""
        if not self.crosshair_locked and source_stokes_index != self.stokes_index:
            # Convert spectral/spatial to plot x/y based on axis configuration
            config = self.data_model.config
            if config.x_data_dim == 0:  # spectral on x-axis
                xpos, ypos = spectral_pos, spatial_pos
            else:  # spatial on x-axis
                xpos, ypos = spatial_pos, spectral_pos
            
            # Block signals to prevent feedback loops
            self.vLine.blockSignals(True)
            self.hLine.blockSignals(True)
            
            # Update crosshair positions
            self.vLine.setPos(xpos)
            self.hLine.setPos(ypos)
            
            # Update label and store position
            self.last_valid_crosshair_pos = (xpos, ypos)
            self.updateLabelFromCrosshair(xpos, ypos)
            
            # Re-enable signals
            self.vLine.blockSignals(False)
            self.hLine.blockSignals(False)

    def set_data(self, data: np.ndarray):
        if data.ndim != 2:
            raise ValueError(f"StokesSpectrumImageWindow expects 2D data (spectral, x); got shape {data.shape}")

        self.data = data
        self.n_spectral, self.n_x_pixel = self.data.shape
        self.spectral_pixels = np.arange(self.n_spectral)
        self.spatial_pixels = np.arange(self.n_x_pixel)

        # Update histogram/image - handle axis configuration
        config = self.data_model.config
        axis_order = pg.getConfigOption('imageAxisOrder')
        
        if config.x_data_dim == 0 and config.y_data_dim == 1:
            # Default: spectral on x, spatial on y
            img = self.data.T if axis_order == 'row-major' else self.data
        else:
            # Swapped: spatial on x, spectral on y
            img = self.data if axis_order == 'row-major' else self.data.T
        
        self.image_item.setImage(img)

        # Set image rectangle based on which dimension is on which axis
        if config.x_data_dim == 0:
            # Spectral on x-axis, spatial on y-axis (default)
            x_min, x_max = 0, self.n_spectral - 1
            y_min, y_max = 0, self.n_x_pixel - 1
        else:
            # Spatial on x-axis, spectral on y-axis (swapped)
            x_min, x_max = 0, self.n_x_pixel - 1
            y_min, y_max = 0, self.n_spectral - 1

        width = x_max - x_min
        height = y_max - y_min
        self.image_item.setRect(x_min, y_min, width, height)

        # Update managers/clamps
        if hasattr(self, 'spectral_manager'):
            self.spectral_manager.set_data_range(self.n_spectral)
        if hasattr(self, 'spatial_manager'):
            self.spatial_manager.set_data_range(self.n_x_pixel)

        # Clamp view and crosshair to new bounds - respect axis configuration
        config = self.data_model.config
        if config.x_data_dim == 0:
            # Spectral on x-axis, spatial on y-axis (default)
            x_max = self.n_spectral - 1
            y_max = self.n_x_pixel - 1
        else:
            # Spatial on x-axis, spectral on y-axis (swapped)
            x_max = self.n_x_pixel - 1
            y_max = self.n_spectral - 1
        
        try:
            self.plotItem.setXRange(0, x_max, padding=0)
            self.plotItem.setYRange(0, y_max, padding=0)
        except Exception:
            pass

        if hasattr(self, 'vLine') and hasattr(self, 'hLine'):
            x = float(np.clip(self.vLine.value(), 0, self.n_spectral - 1))
            y = float(np.clip(self.hLine.value(), 0, self.n_x_pixel - 1))
            self.vLine.setPos(x)
            self.hLine.setPos(y)
            self.last_valid_crosshair_pos = (x, y)
            self.updateLabelFromCrosshair(x, y)
    
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
        self.spectral_manager.create_default_lines()
        self.control_widget.activate_spectral_button()
        self.control_widget.notify_spectral_region_added()
    
    def create_default_spatial_averaging(self):
        """Create default spatial averaging lines using the manager."""
        self.spatial_manager.create_default_lines()
        self.control_widget.activate_spatial_button()
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
        if source_stokes_index != self.stokes_index and self.spectral_manager.has_lines():
            self.spectral_manager.set_positions(left_pos, center_pos, right_pos, block_signals=True)
    
    def sync_spatial_averaging_lines(self, lower_pos: float, center_pos: float, upper_pos: float, source_stokes_index: int):
        """Synchronize spatial averaging lines from another window."""
        if source_stokes_index != self.stokes_index and self.spatial_manager.has_lines():
            self.spatial_manager.set_positions(lower_pos, center_pos, upper_pos, block_signals=True)
    
    def _activate_spectral_button(self):
        """Helper method to activate spectral averaging button."""
        if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'activate_spectral_button'):
            self.control_widget.activate_spectral_button()
    
    def _activate_spatial_button(self):
        """Helper method to activate spatial averaging button."""
        if hasattr(self, 'control_widget') and hasattr(self.control_widget, 'activate_spatial_button'):
            self.control_widget.activate_spatial_button()


class StokesSpectrumYImageWindow(BasePlotWidget):
    """Spectrum image with axes (spectral vs spatial_y).

    Input data shape: (spectral, y).
    """

    crosshairMoved = QtCore.pyqtSignal(float, float, int)  # spectral_idx, y_idx, stokes_index

    def __init__(self, data: np.ndarray, stokes_index: int, name: str, scale_info: dict = None):
        super().__init__(None)

        self.stokes_index = stokes_index
        self.name = name
        self.data = data
        self.scale_info = scale_info
        if self.data.ndim != 2:
            raise ValueError(f"StokesSpectrumYImageWindow expects 2D data (spectral, y); got shape {self.data.shape}")

        self.n_spectral, self.n_y_pixel = self.data.shape
        self.spectral_pixels = np.arange(self.n_spectral)
        self.y_pixels = np.arange(self.n_y_pixel)

        self._setup_image_plot()
        self._setup_axes()
        self._setup_crosshair()

    def _setup_image_plot(self):
        self.image_item = pg.ImageItem()
        self.plotItem.addItem(self.image_item)
        self.histogram = create_histogram(self.image_item, self.layout, self.scale_info, self.stokes_index)

        axis_order = pg.getConfigOption('imageAxisOrder')
        img = self.data.T if axis_order == 'row-major' else self.data
        self.image_item.setImage(img)

        x_min_spectral = self.spectral_pixels[0] if self.spectral_pixels.size > 0 else 0
        x_max_spectral = self.spectral_pixels[-1] if self.spectral_pixels.size > 0 else self.n_spectral
        y_min = self.y_pixels[0] if self.y_pixels.size > 0 else 0
        y_max = self.y_pixels[-1] if self.y_pixels.size > 0 else self.n_y_pixel
        self.image_item.setRect(x_min_spectral, y_min, x_max_spectral - x_min_spectral, y_max - y_min)

        self.plotItem.setMenuEnabled(False)
        self.plotItem.vb.mouseButtons = {
            QtCore.Qt.MouseButton.LeftButton: pg.ViewBox.PanMode,
            QtCore.Qt.MouseButton.MiddleButton: pg.ViewBox.RectMode,
            QtCore.Qt.MouseButton.RightButton: None
        }
        self.plotItem.vb.installEventFilter(self)

    def _setup_axes(self):
        initialize_image_plot_item(
            self.plotItem,
            y_values=True,
            y_label="y",
            y_units="pixel",
            x_label="λ",
            x_units="pixel",
        )
        self.setup_standard_axes(left_width=30, top_height=15)
        self.setup_custom_ticks(spectral_range=self.n_spectral, spatial_range=self.n_y_pixel)
        self.configure_axis_styling(hide_left_label=True, right_label="y", right_units="pixel")
        self.plotItem.getAxis('bottom').setStyle(showValues=False)
        self.plotItem.getAxis('top').setStyle(showValues=True, tickFont=TICK_FONT)
        spectral_ticks_pix = np.linspace(0, self.n_spectral - 1, 8)
        spectral_ticks = [(tick, f'{tick:.0f}') for tick in spectral_ticks_pix]
        self.plotItem.getAxis('top').setTicks([spectral_ticks])
        self.setup_viewbox_limits(x_max=self.n_spectral - 1, y_max=self.n_y_pixel - 1, min_range=1.0, enable_rect_zoom=True)
        try:
            self.plotItem.setXRange(0, self.n_spectral - 1, padding=0)
            self.plotItem.setYRange(0, self.n_y_pixel - 1, padding=0)
        except Exception:
            pass

    def _setup_crosshair(self):
        colors = getWidgetColors()
        self.vLine, self.hLine = add_crosshair(self.plotItem, colors.get('crosshair', 'white'), colors.get('crosshair', 'white'))
        self.plotItem.scene().sigMouseMoved.connect(self._on_mouse_moved)
        self.plotItem.scene().sigMouseClicked.connect(self._on_mouse_clicked)
        self.crosshair_locked = False
        
        # Throttle crosshair updates for better performance
        self._crosshair_update_timer = QtCore.QTimer()
        self._crosshair_update_timer.setSingleShot(True)
        self._crosshair_update_timer.timeout.connect(self._emit_crosshair_position)
        self._pending_crosshair_pos = None

        mid_spectral = (self.n_spectral - 1) / 2
        mid_y = (self.n_y_pixel - 1) / 2
        self.vLine.setPos(mid_spectral)
        self.hLine.setPos(mid_y)

        self.label = pg.LabelItem(justify='left', size='8pt')
        self.graphics_widget.addItem(self.label, row=1, col=1)
        self._update_label(mid_spectral, mid_y)

    def _update_label(self, xpos_wl: float, ypos_y: float):
        index_spectral = np.clip(int(np.round(xpos_wl)), 0, self.n_spectral - 1)
        index_y = np.clip(int(np.round(ypos_y)), 0, self.n_y_pixel - 1)
        intensity = self.data[index_spectral, index_y]
        self.label.setText(f"l: {xpos_wl:.0f}, y: {ypos_y:.0f}, z: {intensity:.5f}", size='8pt')

    def _on_mouse_clicked(self, event):
        if event.double():
            p = self.plotItem.vb.mapSceneToView(event.scenePos())
            if not self.crosshair_locked:
                self.vLine.setPos(p.x())
                self.hLine.setPos(p.y())
                self._update_label(p.x(), p.y())
            self.crosshair_locked = not self.crosshair_locked

    def _on_mouse_moved(self, pos: QtCore.QPointF):
        if self.crosshair_locked:
            return
        cross = update_crosshair_from_mouse(self.plotItem, self.vLine, self.hLine, pos)
        if cross is None:
            return
        x, y = cross
        self._update_label(x, y)
        
        # Throttle signal emission - store position and emit after delay
        self._pending_crosshair_pos = (x, y)
        if not self._crosshair_update_timer.isActive():
            self._crosshair_update_timer.start(16)  # ~60 FPS max update rate
    
    def _emit_crosshair_position(self):
        """Emit the pending crosshair position after throttle delay."""
        if self._pending_crosshair_pos is not None:
            x, y = self._pending_crosshair_pos
            self.crosshairMoved.emit(x, y, self.stokes_index)
            self._pending_crosshair_pos = None

    @QtCore.pyqtSlot(float, float)
    def set_crosshair_position(self, xpos_wl: float, ypos_y: float):
        if self.crosshair_locked:
            return
        self.vLine.blockSignals(True)
        self.hLine.blockSignals(True)
        try:
            self.vLine.setPos(xpos_wl)
            self.hLine.setPos(ypos_y)
            self._update_label(xpos_wl, ypos_y)
        finally:
            self.vLine.blockSignals(False)
            self.hLine.blockSignals(False)

    def set_data(self, data: np.ndarray):
        if data.ndim != 2:
            raise ValueError(f"StokesSpectrumYImageWindow expects 2D data (spectral, y); got shape {data.shape}")
        self.data = data
        self.n_spectral, self.n_y_pixel = self.data.shape
        self.spectral_pixels = np.arange(self.n_spectral)
        self.y_pixels = np.arange(self.n_y_pixel)

        axis_order = pg.getConfigOption('imageAxisOrder')
        img = self.data.T if axis_order == 'row-major' else self.data
        self.image_item.setImage(img)

        x_min_spectral = self.spectral_pixels[0] if self.spectral_pixels.size > 0 else 0
        x_max_spectral = self.spectral_pixels[-1] if self.spectral_pixels.size > 0 else self.n_spectral
        y_min = self.y_pixels[0] if self.y_pixels.size > 0 else 0
        y_max = self.y_pixels[-1] if self.y_pixels.size > 0 else self.n_y_pixel
        self.image_item.setRect(x_min_spectral, y_min, x_max_spectral - x_min_spectral, y_max - y_min)

        try:
            self.plotItem.setXRange(0, self.n_spectral - 1, padding=0)
            self.plotItem.setYRange(0, self.n_y_pixel - 1, padding=0)
        except Exception:
            pass

        if hasattr(self, 'vLine') and hasattr(self, 'hLine'):
            x = float(np.clip(self.vLine.value(), 0, self.n_spectral - 1))
            y = float(np.clip(self.hLine.value(), 0, self.n_y_pixel - 1))
            self.vLine.setPos(x)
            self.hLine.setPos(y)
            self._update_label(x, y)

    def update_spectral_range(self, min_val: Optional[float], max_val: Optional[float]):
        set_plot_wavelength_range(self.plotItem, self.spectral_pixels, min_val, max_val, axis='x')

    def reset_spectral_range(self):
        reset_plot_wavelength_range(self.plotItem, self.spectral_pixels, axis='x')


class AverageSpectrumWindow(BasePlotWidget):
    spectralIndexChanged = QtCore.pyqtSignal(int)

    def __init__(self, data: np.ndarray, name: str = "Average spectrum", scale_info: dict = None):
        super().__init__(None)
        self.name = name
        self.scale_info = scale_info

        if data.ndim != 3:
            raise ValueError(f"AverageSpectrumWindow expects 3D data (y, spectral, x); got shape {data.shape}")

        self.full_data = data
        self.n_y, self.n_spectral, self.n_x = self.full_data.shape
        self.spectral = np.arange(self.n_spectral)

        self.plot_curve = pg.PlotDataItem()
        self.plotItem.addItem(self.plot_curve)

        colors = getWidgetColors()
        self.vLine = add_line(self.plotItem, colors.get('draggable_line', 'white'), 90, moveable=True)
        self.vLine.sigPositionChanged.connect(self._on_vline_moved)

        initialize_spectrum_plot_item(self.plotItem, y_label="z", x_label="λ", x_units="pixel")
        self.setup_standard_axes(left_width=30, top_height=15)

        self._recompute_and_plot()

        initial_idx = self.n_spectral // 2 if self.n_spectral > 0 else 0
        self.vLine.setPos(float(initial_idx))
        self._emit_index(initial_idx)

    def _recompute_and_plot(self):
        avg = np.nanmean(self.full_data, axis=(0, 2))
        self.plot_curve.setData(self.spectral, avg)

    def _emit_index(self, idx: int):
        self.spectralIndexChanged.emit(int(idx))

    def _on_vline_moved(self):
        idx = int(np.clip(np.round(self.vLine.value()), 0, self.n_spectral - 1))
        self._emit_index(idx)

    def update_spectral_range(self, min_val: Optional[float], max_val: Optional[float]):
        set_plot_wavelength_range(self.plotItem, self.spectral, min_val, max_val, axis='x')

    def reset_spectral_range(self):
        reset_plot_wavelength_range(self.plotItem, self.spectral, axis='x')

class StokesImageWindow(BasePlotWidget):
    """Displays a scan image (spatial_y vs spatial_x) for a selected wavelength.

    Input data shape: (y, λ, x). This widget does not directly reference other windows.
    It exposes a method to set the wavelength index and emits crosshair movement signals.
    """

    crosshairMoved = QtCore.pyqtSignal(float, float, int)  # x, y, stokes_index

    def __init__(self, data: np.ndarray, stokes_index: int, name: str, scale_info: dict = None):
        super().__init__(None)

        self.name = name + " scan"
        self.stokes_index = stokes_index
        self.full_data = data  # (y, λ, x)
        if self.full_data.ndim != 3:
            raise ValueError(f"StokesImageWindow expects 3D data (y, λ, x); got shape {self.full_data.shape}")

        self.n_y, self.n_wl, self.n_x = self.full_data.shape
        self.y_pixels = np.arange(self.n_y)
        self.x_pixels = np.arange(self.n_x)
        self.current_wl_idx = self.n_wl // 2 if self.n_wl > 0 else 0  # dummy selector default
        self.scale_info = scale_info

        self._setup_image_plot()
        self._setup_axes()
        self._setup_crosshair()

    def _slice_image(self) -> np.ndarray:
        """Return image slice for current wavelength as (y, x)."""
        # Respect pyqtgraph imageAxisOrder like other windows
        img = self.full_data[:, self.current_wl_idx, :]
        axis_order = pg.getConfigOption('imageAxisOrder')
        if axis_order == 'row-major':
            # ImageItem expects (rows=y, cols=x); data already (y,x)
            return img
        else:
            # col-major expects (x,y)
            return img.T

    def _setup_image_plot(self):
        self.image_item = pg.ImageItem()
        self.plotItem.addItem(self.image_item)
        self.histogram = create_histogram(self.image_item, self.layout, self.scale_info, self.stokes_index)
        self.image_item.setImage(self._slice_image())

        # Set image rect to exact pixel extents
        x_min, x_max = 0, self.n_x - 1 if self.n_x > 0 else 0
        y_min, y_max = 0, self.n_y - 1 if self.n_y > 0 else 0
        self.image_item.setRect(x_min, y_min, (x_max - x_min), (y_max - y_min))

        self.plotItem.setMenuEnabled(False)
        self.plotItem.vb.mouseButtons = {
            QtCore.Qt.MouseButton.LeftButton: pg.ViewBox.PanMode,
            QtCore.Qt.MouseButton.MiddleButton: pg.ViewBox.RectMode,
            QtCore.Qt.MouseButton.RightButton: None
        }
        self.plotItem.vb.installEventFilter(self)

    def _setup_axes(self):
        # x axis is spatial_x, y axis is spatial_y
        initialize_image_plot_item(self.plotItem, y_values=True, y_label="y", y_units="pixel", x_label="x", x_units="pixel")
        self.setup_standard_axes(left_width=30, top_height=15)
        self.setup_custom_ticks(spatial_range=self.n_x)  # reuse for x ticks
        # Configure left as y, but we hide left label using right label pattern for consistency
        self.configure_axis_styling(hide_left_label=True, right_label="y", right_units="pixel")
        self.setup_viewbox_limits(x_max=self.n_x - 1, y_max=self.n_y - 1, min_range=1.0, enable_rect_zoom=True)
        try:
            self.plotItem.setXRange(0, self.n_x - 1, padding=0)
            self.plotItem.setYRange(0, self.n_y - 1, padding=0)
        except Exception:
            pass

    def _setup_crosshair(self):
        colors = getWidgetColors()
        self.vLine, self.hLine = add_crosshair(self.plotItem, colors.get('crosshair', 'white'), colors.get('crosshair', 'white'))
        self.plotItem.scene().sigMouseMoved.connect(self._on_mouse_moved)
        self.plotItem.scene().sigMouseClicked.connect(self._on_mouse_clicked)
        self.crosshair_locked = False
        
        # Throttle crosshair updates for better performance
        self._crosshair_update_timer = QtCore.QTimer()
        self._crosshair_update_timer.setSingleShot(True)
        self._crosshair_update_timer.timeout.connect(self._emit_crosshair_position)
        self._pending_crosshair_pos = None

        # Initialize crosshair at image center
        mid_x = (self.n_x - 1) / 2
        mid_y = (self.n_y - 1) / 2
        self.vLine.setPos(mid_x)
        self.hLine.setPos(mid_y)

        # Label
        self.label = pg.LabelItem(justify='left', size='8pt')
        self.graphics_widget.addItem(self.label, row=1, col=1)
        self._update_label(mid_x, mid_y)

    def _update_label(self, xpos: float, ypos: float):
        xi = int(np.clip(np.round(xpos), 0, self.n_x - 1))
        yi = int(np.clip(np.round(ypos), 0, self.n_y - 1))
        z = float(self.full_data[yi, self.current_wl_idx, xi]) if self.n_y and self.n_x else np.nan
        self.label.setText(f"x: {xpos:.0f}, y: {ypos:.0f}, z: {z:.5f}")

    def _on_mouse_clicked(self, event):
        if event.double():
            p = self.plotItem.vb.mapSceneToView(event.scenePos())
            if not self.crosshair_locked:
                self.vLine.setPos(p.x())
                self.hLine.setPos(p.y())
                self._update_label(p.x(), p.y())
            self.crosshair_locked = not self.crosshair_locked

    def _on_mouse_moved(self, pos: QtCore.QPointF):
        if not self.crosshair_locked:
            cross = update_crosshair_from_mouse(self.plotItem, self.vLine, self.hLine, pos)
            if cross is not None:
                x, y = cross
                self._update_label(x, y)
                
                # Throttle signal emission - store position and emit after delay
                self._pending_crosshair_pos = (x, y)
                if not self._crosshair_update_timer.isActive():
                    self._crosshair_update_timer.start(16)  # ~60 FPS max update rate
    
    def _emit_crosshair_position(self):
        """Emit the pending crosshair position after throttle delay."""
        if self._pending_crosshair_pos is not None:
            x, y = self._pending_crosshair_pos
            self.crosshairMoved.emit(x, y, self.stokes_index)
            self._pending_crosshair_pos = None

    # Public API
    @QtCore.pyqtSlot(int)
    def update_wavelength_index(self, wl_idx: int):
        """Update the displayed image to the given wavelength index."""
        if not (0 <= wl_idx < self.n_wl):
            print(f"Error: wl_idx {wl_idx} out of bounds for data with {self.n_wl} spectral pixels.")
            return
        self.current_wl_idx = wl_idx
        self.image_item.setImage(self._slice_image())
        # Refresh label at current crosshair
        self._update_label(self.vLine.value(), self.hLine.value())

    @QtCore.pyqtSlot(float, float)
    def set_crosshair_position(self, xpos: float, ypos: float):
        if self.crosshair_locked:
            return
        self.vLine.blockSignals(True)
        self.hLine.blockSignals(True)
        try:
            self.vLine.setPos(xpos)
            self.hLine.setPos(ypos)
            self._update_label(xpos, ypos)
        finally:
            self.vLine.blockSignals(False)
            self.hLine.blockSignals(False)

    def update_spatial_x_range(self, min_val: float, max_val: float):
        set_plot_wavelength_range(self.plotItem, self.x_pixels, min_val, max_val, axis='x')

    def reset_spatial_x_range(self):
        reset_plot_wavelength_range(self.plotItem, self.x_pixels, axis='x')

    def update_spatial_y_range(self, min_val: float, max_val: float):
        set_plot_wavelength_range(self.plotItem, self.y_pixels, min_val, max_val, axis='y')

    def reset_spatial_y_range(self):
        reset_plot_wavelength_range(self.plotItem, self.y_pixels, axis='y')