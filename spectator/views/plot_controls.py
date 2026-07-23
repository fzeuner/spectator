"""
Plot control widgets for main viewer functionality.

This module contains the main PlotControlWidget class that coordinates
all plot interactions, synchronization, and axis controls.
"""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from pyqtgraph.dockarea import Dock, DockArea
from typing import List, Dict, Optional, Any, Tuple
from functools import partial

from .line_controls import LinesControlGroup
from .spectrum_limits import SpectrumLimitControlGroup
from ..utils.plotting import create_wavelength_limit_controls
from ..utils.synchronization import SynchronizationManager
from ..utils.fixed_dock_label import FixedDockLabel


class PlotControlWidget(QtWidgets.QWidget):
    crosshairMoved = QtCore.pyqtSignal(float, float, int) # x, y, source_stokes_index
    xlamRangeChanged = QtCore.pyqtSignal(float, float)  # Emit (min, max)
    resetXlamRangeRequested = QtCore.pyqtSignal()
    spatialRangeChanged = QtCore.pyqtSignal(float, float)  # Emit (min, max)
    resetSpatialRangeRequested = QtCore.pyqtSignal()
    spatialYRangeChanged = QtCore.pyqtSignal(float, float)  # Emit (min, max) for y axis
    resetSpatialYRangeRequested = QtCore.pyqtSignal()
    syncZoomToggled = QtCore.pyqtSignal(bool)  # Emit sync zoom state

    def __init__(self, spatial_label: str = "x", has_spatial_y: bool = False):
        super().__init__(None)

        self.spatial_label = spatial_label
        self.has_spatial_y = has_spatial_y
        self.main_layout = QtWidgets.QVBoxLayout(self)
        
        # Initialize synchronization state
        self.sync_crosshair = False
        self.sync_avg_x = False
        self.sync_avg_y = False
        self.sync_spatial_y = False
        self.sync_zoom = False
        
        # Widget collections (set by external controller)
        self.spectrum_image_widgets = []
        self.spectra_widgets = []
        self.spatial_widgets = []
        self.spectrum_image_y_widgets = []
        self.scan_image_widgets = []
        
        # Initialize synchronization manager
        self.sync_manager = SynchronizationManager(self)
        
        # Initialize UI
        self._init_dock_layout()
    
    def _init_dock_layout(self):
        """Initializes the DockArea and places controls into specific docks."""
        self.dock_area = DockArea()
        self.main_layout.addWidget(self.dock_area)

        self.limits_dock = Dock(
            "Limits",
            closable=False,
            size=(1, 1),
            label=FixedDockLabel("Limits"),
        )
        self.dock_area.addDock(self.limits_dock)

        self.lines_dock = Dock(
            "Lines",
            closable=False,
            size=(1, 1),
            label=FixedDockLabel("Lines"),
        )
        self.dock_area.addDock(self.lines_dock, 'above', self.limits_dock)

        # --- Widgets for the "limits" dock ---
        limits_content_widget = QtWidgets.QWidget()
        self.limits_layout = QtWidgets.QVBoxLayout(limits_content_widget)
        self.limits_dock.addWidget(limits_content_widget)
        # Parent group for axis limits
        axis_limits_group = QtWidgets.QGroupBox("Axis limits")
        axis_limits_layout = QtWidgets.QVBoxLayout(axis_limits_group)

        # Add lambda and x sub-groups into the parent
        self._init_wavelength_range_controls(axis_limits_layout)
        self._init_spatial_range_controls(axis_limits_layout)
        if self.has_spatial_y:
            self._init_spatial_y_range_controls(axis_limits_layout)
        
        # Add sync zoom button
        self._init_sync_zoom_button(axis_limits_layout)

        # Add the parent group to the dock layout
        self.limits_layout.addWidget(axis_limits_group)

        # Parent group for z-axis (intensity) limits per state
        self.z_limits_group = QtWidgets.QGroupBox("z axis limits")
        self.z_limits_layout = QtWidgets.QVBoxLayout(self.z_limits_group)
        self.limits_layout.addWidget(self.z_limits_group)

        # --- Widgets for the "lines" dock ---
        self.lines_content_widget = LinesControlGroup(self, spatial_label=self.spatial_label, has_spatial_y=self.has_spatial_y) # Instance of LinesControlGroup
        self.lines_dock.addWidget(self.lines_content_widget)

        # Connect the signals from LinesControlGroup to PlotControlWidget's methods
        self.lines_content_widget.toggleCrosshairSync.connect(self._handle_crosshair_sync_toggle)
        self.lines_content_widget.toggleAvgXSync.connect(self._handle_avg_x_sync_toggle)
        self.lines_content_widget.toggleAvgYSync.connect(self._handle_avg_y_sync_toggle)
        self.lines_content_widget.toggleSpatialYSync.connect(self._handle_spatial_y_sync_toggle)
        
        # Note: Conditional signal connection - may be unused code
    
    def set_widget_collections(self, spectrum_image_widgets: list, spectra_widgets: list, spatial_widgets: list,
                              spectrum_image_y_widgets: Optional[list] = None, scan_image_widgets: Optional[list] = None):
        """Update widget collections for synchronization."""
        self.spectrum_image_widgets = spectrum_image_widgets
        self.spectra_widgets = spectra_widgets
        self.spatial_widgets = spatial_widgets
        self.spectrum_image_y_widgets = spectrum_image_y_widgets or []
        self.scan_image_widgets = scan_image_widgets or []
        self.sync_manager.set_widget_collections(spectrum_image_widgets, spectra_widgets, spatial_widgets)
    
    def _handle_sync_toggle(self, sync_type: str, checked: bool):
        """Generic handler for synchronization toggle changes."""
        if sync_type == 'crosshair':
            self.sync_crosshair = checked
            if checked:
                self.sync_manager.broadcast_crosshair_positions()
        elif sync_type == 'avg_x':
            self.sync_avg_x = checked
            if checked:
                self.sync_manager._broadcast_spectral_positions()
        elif sync_type == 'avg_y':
            self.sync_avg_y = checked
            if checked:
                self.sync_manager._broadcast_spatial_positions()
    
    @QtCore.pyqtSlot(bool)
    def _handle_crosshair_sync_toggle(self, checked: bool):
        """Slot to receive and handle the crosshair sync toggle state."""
        self._handle_sync_toggle('crosshair', checked)

    @QtCore.pyqtSlot(bool)
    def _handle_avg_x_sync_toggle(self, checked: bool):
        """Slot to receive and handle the wavelength average sync toggle state."""
        self._handle_sync_toggle('avg_x', checked)

    @QtCore.pyqtSlot(bool)
    def _handle_avg_y_sync_toggle(self, checked: bool):
        """Slot to receive and handle the spatial average sync toggle state."""
        self._handle_sync_toggle('avg_y', checked)

    @QtCore.pyqtSlot(bool)
    def _handle_spatial_y_sync_toggle(self, checked: bool):
        """Slot to receive and handle the spatial_y average sync toggle state."""
        self.sync_spatial_y = checked
    
    @QtCore.pyqtSlot(float, float, float, int)
    def handle_spectral_avg_line_movement(self, left_pos: float, center_pos: float, right_pos: float, source_stokes_index: int):
        """Handle spectral averaging line movement and synchronize across windows."""
        self.sync_manager.sync_spectral_averaging(left_pos, center_pos, right_pos, source_stokes_index, self.sync_avg_x)
    
    @QtCore.pyqtSlot(float, float, float, int)
    def handle_spatial_avg_line_movement(self, lower_pos: float, center_pos: float, upper_pos: float, source_stokes_index: int):
        """Handle spatial averaging line movement and synchronize across windows."""
        self.sync_manager.sync_spatial_averaging(lower_pos, center_pos, upper_pos, source_stokes_index, self.sync_avg_y)
    
    @QtCore.pyqtSlot(float, float, int)
    def handle_crosshair_movement(self, xpos: float, ypos: float, source_stokes_index: int):
        """Handle crosshair movement and synchronize across windows."""
        self.sync_manager.sync_crosshair_movement(xpos, ypos, source_stokes_index, self.sync_crosshair)
    
    @QtCore.pyqtSlot()
    def _handle_reset_button(self):
        """Handle reset button - reset all axis limits simultaneously."""
        self.resetXlamRangeRequested.emit()
        self.resetSpatialRangeRequested.emit()
        if self.has_spatial_y:
            self.resetSpatialYRangeRequested.emit()

    # Zoom sync groups: (widgets_attr, x_dim_attr, y_dim_attr)
    _ZOOM_GROUPS = [
        ('spectrum_image_widgets', 'n_spectral', 'n_x_pixel'),
        ('spectrum_image_y_widgets', 'n_spectral', 'n_y_pixel'),
        ('scan_image_widgets', 'n_x', 'n_y'),
    ]

    def _all_zoom_windows(self):
        return self.spectrum_image_widgets + self.spectrum_image_y_widgets + self.scan_image_widgets

    @QtCore.pyqtSlot(bool)
    def _handle_sync_zoom_toggle(self, checked: bool):
        """Handle sync zoom toggle - synchronize view ranges across all image windows."""
        self.sync_zoom = checked

        if hasattr(self, 'sync_zoom_button'):
            self.sync_zoom_button.setStyleSheet("background-color: red;" if checked else "")

        if checked:
            for widgets_attr, x_dim, y_dim in self._ZOOM_GROUPS:
                for window in getattr(self, widgets_attr):
                    try:
                        window.plotItem.setRange(
                            xRange=(0, getattr(window, x_dim) - 1),
                            yRange=(0, getattr(window, y_dim) - 1),
                            padding=0)
                    except Exception as e:
                        print(f"Error resetting zoom: {e}")

            for window in self._all_zoom_windows():
                try:
                    window.plotItem.vb.sigRangeChanged.connect(self._on_zoom_sync_range_changed)
                except Exception as e:
                    print(f"Error connecting zoom sync: {e}")

            if self.spectrum_image_widgets:
                w = self.spectrum_image_widgets[0]
                self._update_limit_displays_for_sync_zoom(0, w.n_spectral - 1, 0, w.n_x_pixel - 1)
        else:
            for window in self._all_zoom_windows():
                try:
                    window.plotItem.vb.sigRangeChanged.disconnect(self._on_zoom_sync_range_changed)
                except Exception:
                    pass
            self._reset_limit_display_styling()
    
    def _sync_group_zoom(self, group, vb, x_min, x_max, y_min, y_max, x_only=False):
        """Sync zoom to all windows in group except the source, blocking signals."""
        for window in group:
            try:
                if window.plotItem.vb != vb:
                    window.plotItem.vb.sigRangeChanged.disconnect(self._on_zoom_sync_range_changed)
                    if x_only:
                        window.plotItem.setXRange(x_min, x_max, padding=0)
                    else:
                        window.plotItem.setRange(xRange=(x_min, x_max), yRange=(y_min, y_max), padding=0)
                    window.plotItem.vb.sigRangeChanged.connect(self._on_zoom_sync_range_changed)
            except Exception as e:
                print(f"Error syncing zoom: {e}")

    def _on_zoom_sync_range_changed(self, vb, ranges):
        """Handle zoom changes when sync zoom is active."""
        if not getattr(self, 'sync_zoom', False):
            return

        try:
            x_min, x_max = ranges[0]
            y_min, y_max = ranges[1]

            # Determine source group
            for widgets_attr, _, _ in self._ZOOM_GROUPS:
                group = getattr(self, widgets_attr)
                if any(w.plotItem.vb == vb for w in group):
                    src_group = group
                    src_is_scan = widgets_attr == 'scan_image_widgets'
                    src_is_y = widgets_attr == 'spectrum_image_y_widgets'
                    break
            else:
                return

            # Sync within same group (full x+y)
            self._sync_group_zoom(src_group, vb, x_min, x_max, y_min, y_max)

            # Cross-group: sync spectral axis (x) between x and y image windows
            if not src_is_scan:
                cross = self.spectrum_image_y_widgets if not src_is_y else self.spectrum_image_widgets
                self._sync_group_zoom(cross, vb, x_min, x_max, y_min, y_max, x_only=True)

            self._update_limit_displays_for_sync_zoom(x_min, x_max, y_min, y_max)
        except Exception as e:
            print(f"Error in zoom sync: {e}")
    
    def _update_limit_displays_for_sync_zoom(self, x_min, x_max, y_min, y_max):
        """Update limit displays with current zoom ranges as grey text."""
        for prefix, val_min, val_max in [('wavelength', x_min, x_max), ('spatial', y_min, y_max)]:
            min_edit = getattr(self, f'{prefix}_min_edit', None)
            max_edit = getattr(self, f'{prefix}_max_edit', None)
            if min_edit and max_edit:
                for edit, val in [(min_edit, val_min), (max_edit, val_max)]:
                    edit.blockSignals(True)
                    edit.setText(f"{val:.1f}")
                    edit.setStyleSheet("color: grey;")
                    edit.setProperty('sync_updated', True)
                    edit.blockSignals(False)
    
    def _reset_limit_display_styling(self):
        """Reset limit display styling to normal when sync zoom is disabled."""
        for prefix in ['wavelength', 'spatial']:
            for suffix in ['min_edit', 'max_edit']:
                edit = getattr(self, f'{prefix}_{suffix}', None)
                if edit:
                    edit.setStyleSheet("")
                    edit.setProperty('sync_updated', False)

    # Removed handle_crosshair_movement_continued - unused method
    
    @QtCore.pyqtSlot(float, float, float, int)
    def handle_v_avg_line_movement(self, xl: float, xpos: float, xh: float, source_stokes_index: int):
        """Handle spectral averaging line movement - this is the same as handle_spectral_avg_line_movement."""
        # Delegate to the existing spectral averaging handler
        self.handle_spectral_avg_line_movement(xl, xpos, xh, source_stokes_index)
    
    def _create_limit_controls(self, limit_type: str, group_name: str):
        """Create label and edit controls for axis limits."""
        label = QtWidgets.QLabel(f"{limit_type}:")
        edit = QtWidgets.QLineEdit()
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(edit)
        
        # Store references and connect signals
        setattr(self, f'{group_name}_{limit_type}_label', label)
        setattr(self, f'{group_name}_{limit_type}_edit', edit)
        
        # Connect appropriate range change handler
        handler_map = {
            'wavelength': lambda: self._axis_range_changed('wavelength', 'xlamRangeChanged', 'wavelength'),
            'spatial': lambda: self._axis_range_changed('spatial', 'spatialRangeChanged', 'spatial'),
            'spatial_y': lambda: self._axis_range_changed('spatial_y', 'spatialYRangeChanged', 'spatial_y'),
        }
        if group_name in handler_map:
            edit.editingFinished.connect(handler_map[group_name])
            
        # Add text changed handler to reset styling on manual input
        edit.textChanged.connect(lambda text, e=edit: self._on_manual_limit_input(e))
        
        return label, edit, layout
    
    def _init_wavelength_range_controls(self, parent_layout: QtWidgets.QVBoxLayout):
        """Initializes controls for wavelength (wavelength) axis limits."""
        wavelength_group_box = QtWidgets.QGroupBox("λ")
        limits_wavelength_layout = QtWidgets.QVBoxLayout(wavelength_group_box)

        for limit_type in ['min', 'max']:
            label, edit, layout = self._create_limit_controls(limit_type, 'wavelength')
            limits_wavelength_layout.addLayout(layout)

        self.reset_wavelength_button = QtWidgets.QPushButton("Reset λ range")
        self.reset_wavelength_button.clicked.connect(self.resetXlamRangeRequested.emit)
        limits_wavelength_layout.addWidget(self.reset_wavelength_button)

        parent_layout.addWidget(wavelength_group_box)

    def _init_spatial_range_controls(self, parent_layout: QtWidgets.QVBoxLayout):
        """Initializes controls for spatial (x pixel) axis limits."""
        spatial_group_box = QtWidgets.QGroupBox("x")
        limits_spatial_layout = QtWidgets.QVBoxLayout(spatial_group_box)

        for limit_type in ['min', 'max']:
            label, edit, layout = self._create_limit_controls(limit_type, 'spatial')
            limits_spatial_layout.addLayout(layout)

        self.reset_spatial_button = QtWidgets.QPushButton("Reset x range")
        self.reset_spatial_button.clicked.connect(self.resetSpatialRangeRequested.emit)
        limits_spatial_layout.addWidget(self.reset_spatial_button)

        parent_layout.addWidget(spatial_group_box)
    
    def _init_sync_zoom_button(self, parent_layout):
        """Initializes sync zoom and reset buttons in axis limits group."""
        sync_zoom_layout = QtWidgets.QHBoxLayout()
        
        self.sync_zoom_button = QtWidgets.QPushButton("sync zoom")
        self.sync_zoom_button.setCheckable(True)
        self.sync_zoom_button.clicked.connect(self._handle_sync_zoom_toggle)
        
        self.reset_button = QtWidgets.QPushButton("reset")
        self.reset_button.clicked.connect(self._handle_reset_button)
        
        sync_zoom_layout.addWidget(self.sync_zoom_button)
        sync_zoom_layout.addWidget(self.reset_button)
        
        parent_layout.addLayout(sync_zoom_layout)
    
    def _on_manual_limit_input(self, edit_widget):
        """Handle manual input in limit boxes - make text white and deactivate sync zoom."""
        # Only reset styling if this was a sync-updated field
        if edit_widget.property('sync_updated'):
            edit_widget.setStyleSheet("color: white;")
            edit_widget.setProperty('sync_updated', False)
            
            # Deactivate sync zoom when user manually enters values
            if hasattr(self, 'sync_zoom_button') and self.sync_zoom_button.isChecked():
                self.sync_zoom_button.setChecked(False)
                self._handle_sync_zoom_toggle(False)
    
    def _parse_range_values(self, min_text: str, max_text: str) -> tuple:
        """Parse and validate range values from text inputs."""
        min_val = None
        max_val = None
        
        if min_text:
            try:
                min_val = float(min_text)
            except ValueError:
                min_val = None
        if max_text:
            try:
                max_val = float(max_text)
            except ValueError:
                max_val = None

        # Validate range order if both values present
        if (min_val is not None) and (max_val is not None):
            if min_val >= max_val:
                return None, None
                
        return min_val, max_val
    
    # Mapping: range_type -> list of (widgets_attr, method_name)
    _RANGE_WIDGET_MAP = {
        'wavelength': [
            ('spectra_widgets', 'update_spectral_range'),
            ('spectrum_image_widgets', 'update_spectral_range'),
        ],
        'spatial': [
            ('spectrum_image_widgets', 'update_spatial_range'),
            ('spatial_widgets', 'update_spatial_range'),
            ('scan_image_widgets', 'update_spatial_x_range'),
        ],
        'spatial_y': [
            ('spectrum_image_y_widgets', 'update_spatial_y_range'),
            ('scan_image_widgets', 'update_spatial_y_range'),
            ('spatial_widgets', 'update_spatial_y_range'),
        ],
    }

    def _apply_range_to_widgets(self, min_val, max_val, range_type: str):
        """Apply range values to appropriate widgets."""
        for widgets_attr, method_name in self._RANGE_WIDGET_MAP.get(range_type, []):
            for widget in getattr(self, widgets_attr):
                method = getattr(widget, method_name, None)
                if method:
                    method(min_val, max_val)
    
    def _axis_range_changed(self, range_type: str, signal_attr: str, edit_prefix: str):
        """Unified handler for axis range changes from edit fields."""
        min_text = getattr(self, f'{edit_prefix}_min_edit').text().strip()
        max_text = getattr(self, f'{edit_prefix}_max_edit').text().strip()

        min_val, max_val = self._parse_range_values(min_text, max_text)

        if min_val is None and max_val is None:
            return

        self._apply_range_to_widgets(min_val, max_val, range_type)

        if min_val is not None and max_val is not None:
            getattr(self, signal_attr).emit(min_val, max_val)

    def _init_spatial_y_range_controls(self, parent_layout: QtWidgets.QVBoxLayout):
        """Initializes controls for spatial y axis limits (scan viewer only)."""
        spatial_y_group_box = QtWidgets.QGroupBox("y")
        limits_spatial_y_layout = QtWidgets.QVBoxLayout(spatial_y_group_box)

        for limit_type in ['min', 'max']:
            label, edit, layout = self._create_limit_controls(limit_type, 'spatial_y')
            limits_spatial_y_layout.addLayout(layout)

        self.reset_spatial_y_button = QtWidgets.QPushButton("Reset y range")
        self.reset_spatial_y_button.clicked.connect(self.resetSpatialYRangeRequested.emit)
        limits_spatial_y_layout.addWidget(self.reset_spatial_y_button)

        parent_layout.addWidget(spatial_y_group_box)

    
    def init_spectrum_limit_controls(self, spectra_widgets: List,
                                   spectrum_image_widgets: List,
                                   spatial_widgets: List,
                                   spectrum_image_y_widgets: Optional[List] = None):
        """
        Initialize spectrum limit controls for all Stokes parameters.
        
        Args:
            spectra_widgets: List of spectrum plot widgets
            spectrum_image_widgets: List of spectrum image widgets
            spatial_widgets: List of spatial plot widgets
            spectrum_image_y_widgets: Optional list of Y-direction spectrum image widgets
        """
        # Use existing set_widget_collections method to avoid duplication
        self.set_widget_collections(spectrum_image_widgets, spectra_widgets, spatial_widgets)
        
        for i, spectrum_widget in enumerate(self.spectra_widgets):
            spectrum_image_widget = self.spectrum_image_widgets[i] if i < len(self.spectrum_image_widgets) else None
            spatial_widget = self.spatial_widgets[i] if i < len(self.spatial_widgets) else None
            spectrum_image_y_widget = spectrum_image_y_widgets[i] if spectrum_image_y_widgets and i < len(spectrum_image_y_widgets) else None
            if spectrum_image_widget is None:
                continue
            
            limit_group = SpectrumLimitControlGroup(
                stokes_name=spectrum_widget.name,
                spectrum_widget=spectrum_widget,
                spectrum_image_widget=spectrum_image_widget,
                spatial_widget=spatial_widget,
                spectrum_image_y_widget=spectrum_image_y_widget
            )
            
            if hasattr(self, 'z_limits_layout'):
                self.z_limits_layout.addWidget(limit_group)
            else:
                # Fallback: in case init order changes
                self.limits_layout.addWidget(limit_group)
    
