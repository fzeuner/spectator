"""
Control widget classes for the viewer.

This module contains control panels and UI controls for managing plot interactions,
synchronization, and settings.
"""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from typing import List, Dict, Optional, Any, Tuple
from functools import partial
from scipy.io import readsav
import os

from .base_widgets import BaseControlWidget
from models import ViewerSettings, PlotConfiguration
from utils.plotting import create_wavelength_limit_controls

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LinesControlGroup(QtWidgets.QWidget): 
    """
    A widget for the line controls.
    """
    # Signals
    toggleCrosshairSync = QtCore.pyqtSignal(bool)
    toggleAvgXSync = QtCore.pyqtSignal(bool)
    toggleAvgYSync = QtCore.pyqtSignal(bool)
    spectralAveragingEnabled = QtCore.pyqtSignal(bool)  # New signal for spectral averaging control
    toggleAvgXRemove = QtCore.pyqtSignal(bool)
    toggleAvgYRemove = QtCore.pyqtSignal(bool)
    createDefaultSpectralAveraging = QtCore.pyqtSignal()  # Signal to create default spectral averaging
    createDefaultSpatialAveraging = QtCore.pyqtSignal()   # Signal to create default spatial averaging

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        # This layout will hold your QGroupBoxes
        self.main_v_layout = QtWidgets.QVBoxLayout(self) # Set the layout directly on self
        # Track how many regions exist across all states
        self.spectral_regions = 0
        self.spatial_regions = 0

        # QGroupBox for Synchronization buttons
        self.synchronize_box = QtWidgets.QGroupBox("Synchronize")
        sync_box_layout = QtWidgets.QVBoxLayout(self.synchronize_box) # Layout for the synchronize_box

        self.sync_button = QtWidgets.QPushButton("crosshair")
        self.sync_button.setCheckable(True)
        self.sync_button.clicked.connect(self._on_toggle_crosshair_sync) # Connect to internal handler
        sync_box_layout.addWidget(self.sync_button)

        self.sync_button_y_avg = QtWidgets.QPushButton("<spatial>")
        self.sync_button_y_avg.setCheckable(True)
        self.sync_button_y_avg.clicked.connect(self._on_toggle_avg_y_sync) # Connect to internal handler
        self.sync_button_y_avg.setEnabled(False)  # Only enabled when any spatial region exists
        sync_box_layout.addWidget(self.sync_button_y_avg)

        self.sync_button_x_avg = QtWidgets.QPushButton("<spectral>")
        self.sync_button_x_avg.setCheckable(True)
        self.sync_button_x_avg.clicked.connect(self._on_toggle_avg_x_sync) # Connect to internal handler
        self.sync_button_x_avg.setEnabled(False)  # Only enabled when any spectral region exists
        sync_box_layout.addWidget(self.sync_button_x_avg)

        self.main_v_layout.addWidget(self.synchronize_box) # Add the group box to the main layout

        # Avg lines control

        self.avg_lines_box = QtWidgets.QGroupBox("<> lines")
        avg_lines_box_layout = QtWidgets.QVBoxLayout(self.avg_lines_box)
        
        # Radio button group for spatial/spectral selection
        self.avg_type_group = QtWidgets.QButtonGroup()
        
        # Spectral row: radio button + push button
        spectral_row_layout = QtWidgets.QHBoxLayout()
        self.radio_spectral = QtWidgets.QRadioButton()
        self.avg_type_group.addButton(self.radio_spectral, 0)  # ID 0 for spectral
        
        self.button_remove_x_avg = QtWidgets.QPushButton("<spectral>")
        self.button_remove_x_avg.setCheckable(True)
        self.button_remove_x_avg.clicked.connect(self._on_toggle_avg_x_remove) # Connect to internal handler
        
        spectral_row_layout.addWidget(self.radio_spectral)
        spectral_row_layout.addWidget(self.button_remove_x_avg)
        avg_lines_box_layout.addLayout(spectral_row_layout)
        
        # Spatial row: radio button + push button
        spatial_row_layout = QtWidgets.QHBoxLayout()
        self.radio_spatial = QtWidgets.QRadioButton()
        self.radio_spatial.setChecked(True)  # Default to spatial averaging
        self.avg_type_group.addButton(self.radio_spatial, 1)  # ID 1 for spatial
        
        self.button_remove_y_avg = QtWidgets.QPushButton("<spatial>")
        self.button_remove_y_avg.setCheckable(True)
        self.button_remove_y_avg.clicked.connect(self._on_toggle_avg_y_remove) # Connect to internal handler
        
        spatial_row_layout.addWidget(self.radio_spatial)
        spatial_row_layout.addWidget(self.button_remove_y_avg)
        avg_lines_box_layout.addLayout(spatial_row_layout)
        
        # Connect radio button group signal
        self.avg_type_group.buttonClicked.connect(self._on_avg_type_changed)
        
        # Emit initial state (spatial is default)
        self.spectralAveragingEnabled.emit(False)
        
        self.main_v_layout.addWidget(self.avg_lines_box)

        

        self.main_v_layout.addStretch(1) # Push content to the top

    @QtCore.pyqtSlot(bool)
    def _on_toggle_crosshair_sync(self, checked: bool):
        self.toggleCrosshairSync.emit(checked) # Emit the class-level signal
        self.sync_button.setStyleSheet("background-color: red;" if checked else "")

    @QtCore.pyqtSlot(bool)
    def _on_toggle_avg_x_sync(self, checked: bool):
        self.toggleAvgXSync.emit(checked) # Emit the class-level signal
        self.sync_button_x_avg.setStyleSheet("background-color: red;" if checked else "")

    @QtCore.pyqtSlot(bool)
    def _on_toggle_avg_y_sync(self, checked: bool):
        self.toggleAvgYSync.emit(checked) # Emit the class-level signal
        self.sync_button_y_avg.setStyleSheet("background-color: red;" if checked else "")
        
    @QtCore.pyqtSlot(bool)
    def _on_toggle_avg_x_remove(self, checked: bool):
            if checked:
                # If manually activated, create default spectral averaging
                if not self.button_remove_x_avg.property('auto_activated'):
                    self.createDefaultSpectralAveraging.emit()
            else:
                # If deactivated, remove averaging
                self.toggleAvgXRemove.emit(checked)
            self.button_remove_x_avg.setStyleSheet("background-color: red;" if checked else "")
            # Clear the auto_activated flag
            self.button_remove_x_avg.setProperty('auto_activated', False)
            
    @QtCore.pyqtSlot(bool)
    def _on_toggle_avg_y_remove(self, checked: bool):
            if checked:
                # If manually activated, create default spatial averaging
                if not self.button_remove_y_avg.property('auto_activated'):
                    self.createDefaultSpatialAveraging.emit()
            else:
                # If deactivated, remove averaging
                self.toggleAvgYRemove.emit(checked)
            self.button_remove_y_avg.setStyleSheet("background-color: red;" if checked else "")
            # Clear the auto_activated flag
            self.button_remove_y_avg.setProperty('auto_activated', False)
    
    def activate_spectral_button(self):
        """Activate spectral averaging button when averaging is added."""
        self.button_remove_x_avg.setProperty('auto_activated', True)  # Mark as auto-activated
        self.button_remove_x_avg.setChecked(True)
        self.button_remove_x_avg.setStyleSheet("background-color: red;")
        self.button_remove_x_avg.setEnabled(True)
    
    def activate_spatial_button(self):
        """Activate spatial averaging button when averaging is added."""
        self.button_remove_y_avg.setProperty('auto_activated', True)  # Mark as auto-activated
        self.button_remove_y_avg.setChecked(True)
        self.button_remove_y_avg.setStyleSheet("background-color: red;")
        self.button_remove_y_avg.setEnabled(True)

    def deactivate_spectral_button(self):
        """Deactivate spectral averaging button when no region exists."""
        self.button_remove_x_avg.setChecked(False)
        self.button_remove_x_avg.setStyleSheet("")
        # Keep enabled so users can recreate regions

    def deactivate_spatial_button(self):
        """Deactivate spatial averaging button when no region exists."""
        self.button_remove_y_avg.setChecked(False)
        self.button_remove_y_avg.setStyleSheet("")
        # Keep enabled so users can recreate regions
    
    def _on_avg_type_changed(self, button):
        """Handle radio button selection change for averaging type."""
        button_id = self.avg_type_group.id(button)
        if button_id == 0:  # Spectral selected
            self.spectralAveragingEnabled.emit(True)  # Enable spectral averaging
        elif button_id == 1:  # Spatial selected
            self.spectralAveragingEnabled.emit(False)  # Disable spectral averaging

    # Methods to update button states externally
    def set_crosshair_sync_state(self, checked: bool):
        self.sync_button.setChecked(checked)
        self.sync_button.setStyleSheet("background-color: red;" if checked else "")

    def set_avg_x_sync_state(self, checked: bool):
        self.sync_button_x_avg.setChecked(checked)
        self.sync_button_x_avg.setStyleSheet("background-color: red;" if checked else "")

    def set_avg_y_sync_state(self, checked: bool):
        self.sync_button_y_avg.setChecked(checked)
        self.sync_button_y_avg.setStyleSheet("background-color: red;" if checked else "")

    # Notification methods from windows to control sync button availability
    def notify_spectral_region_added(self):
        # Enable spectral sync button when at least one region exists
        if self.spectral_regions == 0:
            self.sync_button_x_avg.setEnabled(True)
        self.spectral_regions += 1

    def notify_spatial_region_added(self):
        if self.spatial_regions == 0:
            self.sync_button_y_avg.setEnabled(True)
        self.spatial_regions += 1

    def notify_spectral_region_removed(self):
        if self.spectral_regions > 0:
            self.spectral_regions -= 1
            if self.spectral_regions == 0:
                # Turn off and disable spectral sync
                if self.sync_button_x_avg.isChecked():
                    # Emit off state so listeners can disable sync behavior
                    self.toggleAvgXSync.emit(False)
                self.sync_button_x_avg.setChecked(False)
                self.sync_button_x_avg.setStyleSheet("")
                self.sync_button_x_avg.setEnabled(False)

    def notify_spatial_region_removed(self):
        if self.spatial_regions > 0:
            self.spatial_regions -= 1
            if self.spatial_regions == 0:
                if self.sync_button_y_avg.isChecked():
                    self.toggleAvgYSync.emit(False)
                self.sync_button_y_avg.setChecked(False)
                self.sync_button_y_avg.setStyleSheet("")
                self.sync_button_y_avg.setEnabled(False)


class SpectrumLimitControlGroup(BaseControlWidget):
    """
    Control widget for managing spectrum Y-axis limits and histogram synchronization.
    
    Provides controls for fixing axis limits and synchronizing with histogram levels.
    """
    
    def __init__(self, stokes_name: str,
                 spectrum_widget: 'StokesSpectrumWindow',
                 spectrum_image_widget: 'StokesSpectrumImageWindow',
                 spatial_widget: 'StokesSpatialWindow' = None,
                 parent: Optional[QtWidgets.QWidget] = None):
        """
        Initialize spectrum limit control group.
        
        Args:
            stokes_name: Name of the Stokes parameter
            spectrum_widget: Associated spectrum plot widget
            spectrum_image_widget: Associated spectrum image widget
            spatial_widget: Associated spatial plot widget
            parent: Parent widget
        """
        super().__init__(f"{stokes_name}", parent)
        
        self.stokes_name = stokes_name
        self.spectrum_widget = spectrum_widget
        self.spectrum_image_widget = spectrum_image_widget
        self.spatial_widget = spatial_widget
        
        self._setup_controls()
        self._connect_signals()
        self._set_initial_values()
    
    def _setup_controls(self):
        """Setup control widgets."""
        # Fix limits checkbox
        self.fix_limits_checkbox = self.add_checkbox(
            "Fix z limits",
            checked=False,
            callback=self._toggle_fix_spectrum_limits
        )
        
        # Min/Max limit controls
        self.min_limit_edit = self.add_line_edit(
            "Min:",
            initial_value="0.0",
            callback=self._on_limit_edit_changed
        )
        self.min_limit_edit.setEnabled(False)
        
        self.max_limit_edit = self.add_line_edit(
            "Max:",
            initial_value="1.0", 
            callback=self._on_limit_edit_changed
        )
        self.max_limit_edit.setEnabled(False)
    
    def _connect_signals(self):
        """Connect widget signals to handlers."""
        # Connect spectrum plot range changes
        if hasattr(self.spectrum_widget, 'yRangeChanged'):
            self.spectrum_widget.yRangeChanged.connect(self._update_limit_edits_from_plot)
    
    def _set_initial_values(self):
        """Set initial values for the controls."""
        # Get initial range from spectrum widget
        if self.spectrum_widget and hasattr(self.spectrum_widget, 'plotItem'):
            try:
                y_range = self.spectrum_widget.plotItem.getViewBox().viewRange()[1]
                self.min_limit_edit.setText(f"{y_range[0]:.2f}")
                self.max_limit_edit.setText(f"{y_range[1]:.2f}")
            except:
                pass  # Use default values if range cannot be determined
    
    def _toggle_fix_spectrum_limits(self, state: QtCore.Qt.CheckState):
        """Toggle fixed spectrum limits mode."""
        fixed = state == QtCore.Qt.Checked
        self.min_limit_edit.setEnabled(fixed)
        self.max_limit_edit.setEnabled(fixed)
        
        if fixed:
            self._update_spectrum_limits_from_edits()  # Apply current values from edits
            self.spectrum_widget.plotItem.enableAutoRange(axis='y', enable=False)
            # Also disable auto-range for spatial window x-axis
            if self.spatial_widget:
                self.spatial_widget.plotItem.enableAutoRange(axis='x', enable=False)
            
            if self.spectrum_image_widget and self.spectrum_image_widget.histogram:
                self.spectrum_image_widget.histogram.sigLevelsChanged.connect(
                    partial(self._on_histogram_levels_changed)
                )
        else:
            self.spectrum_widget.plotItem.enableAutoRange(axis='y', enable=True)
            self.spectrum_widget.plotItem.autoRange()
            # Re-enable auto-range for spatial window x-axis
            if self.spatial_widget:
                self.spatial_widget.plotItem.enableAutoRange(axis='x', enable=True)
                self.spatial_widget.plotItem.autoRange()
            
            if self.spectrum_image_widget and self.spectrum_image_widget.histogram:
                # Disconnect the signal
                try:
                    pass  # Relying on check inside slot for now
                except (TypeError, RuntimeError):
                    pass  # Ignore if not connected or already disconnected
                
                self.spectrum_image_widget.histogram.setLevels(None, None)  # Reset histogram to auto-range
    
    def _on_histogram_levels_changed(self):
        """
        Handle histogram levels changed signal.
        Updates the min/max QLineEdit fields and the spectrum plot's Y-range.
        Also updates spatial window X-range when fix limits is enabled.
        """
        if self.fix_limits_checkbox.isChecked():
            if self.spectrum_image_widget and self.spectrum_image_widget.histogram:
                min_val, max_val = self.spectrum_image_widget.histogram.getLevels()
                
                self.min_limit_edit.blockSignals(True)
                self.max_limit_edit.blockSignals(True)
                self.min_limit_edit.setText(f"{min_val:.2f}")
                self.max_limit_edit.setText(f"{max_val:.2f}")
                self.min_limit_edit.blockSignals(False)
                self.max_limit_edit.blockSignals(False)
                
                if self.spectrum_widget:
                    self.spectrum_widget.plotItem.setYRange(min_val, max_val, padding=0)
                
                # Also update spatial window x-axis range
                if self.spatial_widget:
                    self.spatial_widget.plotItem.setXRange(min_val, max_val, padding=0)
    
    def _update_spectrum_limits_from_edits(self):
        """Apply manual z value limits to the spectrum plot and image histogram."""
        try:
            min_val = float(self.min_limit_edit.text())
            max_val = float(self.max_limit_edit.text())
            
            if min_val >= max_val:
                return  # Invalid range
            
            if self.spectrum_widget:
                self.spectrum_widget.plotItem.setYRange(min_val, max_val, padding=0)
            
            # Also apply to spatial window x-axis when fix limits is enabled
            if self.spatial_widget and self.fix_limits_checkbox.isChecked():
                self.spatial_widget.plotItem.setXRange(min_val, max_val, padding=0)
            
            if self.spectrum_image_widget and self.spectrum_image_widget.histogram:
                self.spectrum_image_widget.histogram.setLevels(min_val, max_val)
                
        except ValueError:
            self.min_limit_edit.setStyleSheet("background-color: red;")
            self.max_limit_edit.setStyleSheet("background-color: red;")
    
    def _update_limit_edits_from_plot(self, limits: Tuple[float, float]):
        """Update min/max QLineEdit widgets from plot's actual Y-range."""
        if not self.fix_limits_checkbox.isChecked():
            min_val, max_val = limits
            self.min_limit_edit.blockSignals(True)
            self.max_limit_edit.blockSignals(True)
            self.min_limit_edit.setText(f"{min_val:.2f}")
            self.max_limit_edit.setText(f"{max_val:.2f}")
            self.min_limit_edit.blockSignals(False)
            self.max_limit_edit.blockSignals(False)
    
    def _on_limit_edit_changed(self):
        """Handle manual limit edit changes."""
        if self.fix_limits_checkbox.isChecked():
            self._update_spectrum_limits_from_edits()
        
        # Reset styling
        self.min_limit_edit.setStyleSheet("")
        self.max_limit_edit.setStyleSheet("")


class PlotControlWidget(QtWidgets.QWidget):
    crosshairMoved = QtCore.pyqtSignal(float, float, int) # x, y, source_stokes_index
    xlamRangeChanged = QtCore.pyqtSignal(object, object)
    resetXlamRangeRequested = QtCore.pyqtSignal()
    # Spatial axis (x pixel) range controls
    spatialRangeChanged = QtCore.pyqtSignal(object, object)
    resetSpatialRangeRequested = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__(None)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.spectrum_image_widgets: List['StokesSpectrumImageWindow'] = []
        self.spectra_widgets: List['StokesSpectrumWindow'] = []
        self.spatial_widgets: List['StokesSpatialWindow'] = []
        self.spectrum_limit_controls: Dict[str, Dict[str, Any]] = {}

        # These synchronization states should live in the PlotControlWidget
        self.sync_crosshair = False
        self.sync_avg_y = False
        self.sync_avg_x = False
        self._histogram_connections = {}

        self._init_dock_layout()
    
    def _init_dock_layout(self):
        """Initializes the DockArea and places controls into specific docks."""
        self.dock_area = DockArea()
        self.main_layout.addWidget(self.dock_area)

        self.limits_dock = Dock("Limits", closable=False, size=(1,1))
        self.dock_area.addDock(self.limits_dock)

        self.lines_dock = Dock("Lines", closable=False, size=(1,1))
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

        # Add the parent group to the dock layout
        self.limits_layout.addWidget(axis_limits_group)

        # Parent group for z-axis (intensity) limits per state
        self.z_limits_group = QtWidgets.QGroupBox("z axis limits")
        self.z_limits_layout = QtWidgets.QVBoxLayout(self.z_limits_group)
        self.limits_layout.addWidget(self.z_limits_group)

        # --- Widgets for the "lines" dock ---
        self.lines_content_widget = LinesControlGroup(self) # Instance of LinesControlGroup
        self.lines_dock.addWidget(self.lines_content_widget)

        # Connect the signals from LinesControlGroup to PlotControlWidget's methods
        self.lines_content_widget.toggleCrosshairSync.connect(self._handle_crosshair_sync_toggle)
        self.lines_content_widget.toggleAvgXSync.connect(self._handle_avg_x_sync_toggle)
        self.lines_content_widget.toggleAvgYSync.connect(self._handle_avg_y_sync_toggle)
    
    def _init_line_controls(self):
        """Initialize line control widgets."""
        self.lines_control = LinesControlGroup()
        
        # Connect signals
        self.lines_control.toggleCrosshairSync.connect(self._handle_crosshair_sync_toggle)
        self.lines_control.toggleAvgXSync.connect(self._handle_avg_x_sync_toggle)
        self.lines_control.toggleAvgYSync.connect(self._handle_avg_y_sync_toggle)
        
        self.lines_dock.addWidget(self.lines_control)
    
    def _init_wavelength_range_controls(self, parent_layout: QtWidgets.QVBoxLayout):
        """Initializes controls for wavelength (wavelength) axis limits, now taking a parent layout."""
        wavelength_group_box = QtWidgets.QGroupBox("λ")
        limits_wavelength_layout = QtWidgets.QVBoxLayout(wavelength_group_box)

        for limit_type in ['min', 'max']:
            label, edit, layout = create_wavelength_limit_controls(limit_type)
            setattr(self, f'wavelength_{limit_type}_label', label)
            setattr(self, f'wavelength_{limit_type}_edit', edit)
            edit.editingFinished.connect(self._wavelength_range_changed)
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
            label, edit, layout = create_wavelength_limit_controls(limit_type)
            setattr(self, f'spatial_{limit_type}_label', label)
            setattr(self, f'spatial_{limit_type}_edit', edit)
            edit.editingFinished.connect(self._spatial_range_changed)
            limits_spatial_layout.addLayout(layout)

        self.reset_spatial_button = QtWidgets.QPushButton("Reset x range")
        self.reset_spatial_button.clicked.connect(self.resetSpatialRangeRequested.emit)
        limits_spatial_layout.addWidget(self.reset_spatial_button)

        parent_layout.addWidget(spatial_group_box)
    
    def _spatial_range_changed(self):
        """Handle spatial (x pixel) range change from edits."""
        min_text = self.spatial_min_edit.text().strip()
        max_text = self.spatial_max_edit.text().strip()

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

        if min_val is None and max_val is None:
            return

        if (min_val is not None) and (max_val is not None):
            if min_val >= max_val:
                return

        self.spatialRangeChanged.emit(min_val, max_val)
    
    def init_spectrum_limit_controls(self, spectra_widgets: List,
                                   spectrum_image_widgets: List,
                                   spatial_widgets: List):
        """
        Initialize spectrum limit controls for all Stokes parameters.
        
        Args:
            spectra_widgets: List of spectrum plot widgets
            spectrum_image_widgets: List of spectrum image widgets
            spatial_widgets: List of spatial plot widgets
        """
        self.spectra_widgets = spectra_widgets
        self.spectrum_image_widgets = spectrum_image_widgets
        self.spatial_widgets = spatial_widgets
        
        for i, spectrum_widget in enumerate(self.spectra_widgets):
            spectrum_image_widget = self.spectrum_image_widgets[i] if i < len(self.spectrum_image_widgets) else None
            spatial_widget = self.spatial_widgets[i] if i < len(self.spatial_widgets) else None
            if spectrum_image_widget is None:
                continue
            
            limit_group = SpectrumLimitControlGroup(
                stokes_name=spectrum_widget.name,
                spectrum_widget=spectrum_widget,
                spectrum_image_widget=spectrum_image_widget,
                spatial_widget=spatial_widget
            )
            
            if hasattr(self, 'z_limits_layout'):
                self.z_limits_layout.addWidget(limit_group)
            else:
                # Fallback: in case init order changes
                self.limits_layout.addWidget(limit_group)
    
    def _wavelength_range_changed(self):
        """Handle wavelength range change."""
        min_text = self.wavelength_min_edit.text().strip()
        max_text = self.wavelength_max_edit.text().strip()

        # Parse values if present; empty -> None
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

        # If both absent or both invalid, do nothing
        if min_val is None and max_val is None:
            return

        # If both provided, validate order
        if (min_val is not None) and (max_val is not None):
            if min_val >= max_val:
                # Invalid range -> ignore change
                return

        # Emit with None for the unspecified side; plotting util will expand to data bounds
        self.xlamRangeChanged.emit(min_val, max_val)
    
    @QtCore.pyqtSlot(bool)
    def _handle_crosshair_sync_toggle(self, checked: bool):
        """Slot to receive and handle the crosshair sync toggle state."""
        self.sync_crosshair = checked

    @QtCore.pyqtSlot(bool)
    def _handle_avg_x_sync_toggle(self, checked: bool):
        """Slot to receive and handle the wavelength average sync toggle state."""
        self.sync_avg_x = checked
        # When enabling sync, immediately broadcast current spectral avg positions from any window
        if checked and hasattr(self, 'spectrum_image_widgets'):
            # Find a source image widget that currently has spectral averaging lines
            for src_idx, img_widget in enumerate(self.spectrum_image_widgets):
                if hasattr(img_widget, 'spectral_manager') and img_widget.spectral_manager and img_widget.spectral_manager.has_lines():
                    left_pos = img_widget.spectral_manager.line1.value()
                    center_pos = img_widget.spectral_manager.center_line.value()
                    right_pos = img_widget.spectral_manager.line2.value()
                    # Push positions to all windows
                    for dst_idx, dst_img in enumerate(self.spectrum_image_widgets):
                        if dst_idx != src_idx:
                            dst_img.sync_spectral_averaging_lines(left_pos, center_pos, right_pos, src_idx)
                    break

    @QtCore.pyqtSlot(bool)
    def _handle_avg_y_sync_toggle(self, checked: bool):
        """Slot to receive and handle the spatial average sync toggle state."""
        self.sync_avg_y = checked
        # When enabling sync, immediately broadcast current spatial avg positions from any window
        if checked and hasattr(self, 'spectrum_image_widgets'):
            for src_idx, img_widget in enumerate(self.spectrum_image_widgets):
                if hasattr(img_widget, 'spatial_manager') and img_widget.spatial_manager and img_widget.spatial_manager.has_lines():
                    lower_pos = img_widget.spatial_manager.line1.value()
                    center_pos = img_widget.spatial_manager.center_line.value()
                    upper_pos = img_widget.spatial_manager.line2.value()
                    # Push positions to all image windows
                    for dst_idx, dst_img in enumerate(self.spectrum_image_widgets):
                        if dst_idx != src_idx:
                            dst_img.sync_spatial_averaging_lines(lower_pos, center_pos, upper_pos, src_idx)
                    break
    
    @QtCore.pyqtSlot(float, float, float, int)
    def handle_spectral_avg_line_movement(self, left_pos: float, center_pos: float, right_pos: float, source_stokes_index: int):
        """Handle spectral averaging line movement and synchronize across windows."""
        if self.sync_avg_x:
            for img_idx, img_widget in enumerate(self.spectrum_image_widgets):
                if img_idx != source_stokes_index:
                    img_widget.sync_spectral_averaging_lines(left_pos, center_pos, right_pos, source_stokes_index)
            # Update spatial widgets for all states that currently have spectral regions
            if hasattr(self, 'spatial_widgets'):
                # Convert positions to wavelength indices based on each spatial widget's data
                for sp_idx, sp_widget in enumerate(self.spatial_widgets):
                    if sp_idx < len(self.spectrum_image_widgets):
                        img_widget = self.spectrum_image_widgets[sp_idx]
                        has_spectral = hasattr(img_widget, 'spectral_manager') and img_widget.spectral_manager and img_widget.spectral_manager.has_lines()
                        if has_spectral:
                            n_wl_pixel = sp_widget.full_data.shape[0]
                            index_wl_l = np.clip(int(np.round(left_pos)), 0, n_wl_pixel - 1)
                            index_wl_c = np.clip(int(np.round(center_pos)), 0, n_wl_pixel - 1)
                            index_wl_h = np.clip(int(np.round(right_pos)), 0, n_wl_pixel - 1)
                            sp_widget.update_spatial_data_wl_avg(index_wl_l, index_wl_c, index_wl_h)
    
    @QtCore.pyqtSlot(float, float, float, int)
    def handle_spatial_avg_line_movement(self, lower_pos: float, center_pos: float, upper_pos: float, source_stokes_index: int):
        """Handle spatial averaging line movement and synchronize across windows."""
        if self.sync_avg_y:
            for img_idx, img_widget in enumerate(self.spectrum_image_widgets):
                if img_idx != source_stokes_index:
                    img_widget.sync_spatial_averaging_lines(lower_pos, center_pos, upper_pos, source_stokes_index)
            # Update spectra for all states that currently have spatial regions
            if hasattr(self, 'spectra_widgets'):
                for spec_idx, spec_widget in enumerate(self.spectra_widgets):
                    # Only update spectra for states that have spatial averaging lines displayed
                    if spec_idx < len(self.spectrum_image_widgets):
                        img_widget = self.spectrum_image_widgets[spec_idx]
                        has_spatial = hasattr(img_widget, 'spatial_manager') and img_widget.spatial_manager and img_widget.spatial_manager.has_lines()
                        if has_spatial and spec_idx != source_stokes_index and hasattr(spec_widget, 'handle_spatial_avg_line_movement'):
                            spec_widget.handle_spatial_avg_line_movement(lower_pos, center_pos, upper_pos, source_stokes_index)
    
    @QtCore.pyqtSlot(float, float, int)
    def handle_crosshair_movement(self, xpos: float, ypos: float, source_stokes_index: int):
        if not self.spectra_widgets or source_stokes_index >= len(self.spectra_widgets):
            print(f"Error: Invalid source_stokes_index {source_stokes_index} or spectra_widgets not initialized.")
            return

        source_spectrum_widget = self.spectra_widgets[source_stokes_index]
        n_x_pixel = source_spectrum_widget.full_data.shape[1]
        index_x = np.clip(int(np.round(ypos)), 0, n_x_pixel - 1)

        if self.sync_crosshair:
            for img_idx, img_widget in enumerate(self.spectrum_image_widgets):
                if img_idx == source_stokes_index:
                    if img_widget.crosshair_locked:
                        continue
                    else:
                        img_widget.set_crosshair_position(xpos, ypos)
                elif not img_widget.crosshair_locked:
                    img_widget.set_crosshair_position(xpos, ypos)

            for spec_idx, spec_widget in enumerate(self.spectra_widgets):
                corresponding_img_widget = self.spectrum_image_widgets[spec_idx]

                if spec_idx == source_stokes_index:
                    spec_widget.update_spectral_line(xpos)
                    spec_widget.update_spectrum_data(index_x)
                elif not corresponding_img_widget.crosshair_locked:
                    spec_widget.update_spectral_line(xpos)
                    spec_widget.update_spectrum_data(index_x)
            
            # Also synchronize spatial widgets
            for spatial_idx, spatial_widget in enumerate(self.spatial_widgets):
                corresponding_img_widget = self.spectrum_image_widgets[spatial_idx] if spatial_idx < len(self.spectrum_image_widgets) else None
                
                if spatial_idx == source_stokes_index:
                    # Update the source spatial widget's crosshair and data
                    spatial_widget.update_x_line(ypos)
                    spectral_idx = np.clip(int(np.round(xpos)), 0, spatial_widget.full_data.shape[0] - 1)
                    spatial_widget.update_spatial_data_spectral(spectral_idx)
                elif corresponding_img_widget and not corresponding_img_widget.crosshair_locked:
                    # Update other spatial widgets' crosshairs and data
                    spatial_widget.update_x_line(ypos)
                    spectral_idx = np.clip(int(np.round(xpos)), 0, spatial_widget.full_data.shape[0] - 1)
                    spatial_widget.update_spatial_data_spectral(spectral_idx)

        else:
            source_spectrum_widget.update_spectral_line(xpos)
            source_spectrum_widget.update_spectrum_data(index_x)
            
        # Always update the source spatial widget regardless of sync_crosshair setting
        # so that the z= label updates when crosshair moves within the same state
        if self.spatial_widgets and source_stokes_index < len(self.spatial_widgets):
            source_spatial_widget = self.spatial_widgets[source_stokes_index]
            source_spatial_widget.update_x_line(ypos)
            spectral_idx = np.clip(int(np.round(xpos)), 0, source_spatial_widget.full_data.shape[0] - 1)
            source_spatial_widget.update_spatial_data_spectral(spectral_idx)
    
    @QtCore.pyqtSlot(float, float, float, int)
    def handle_v_avg_line_movement(self, xl: float, xpos: float, xh: float, source_stokes_index: int):
        if not self.spatial_widgets or source_stokes_index >= len(self.spatial_widgets):
            print(f"Error: Invalid source_stokes_index {source_stokes_index} or spectra_widgets not initialized.")
            return

        source_spatial_widget = self.spatial_widgets[source_stokes_index]
        n_wl_pixel = source_spatial_widget.full_data.shape[0]
        index_wl_c = np.clip(int(np.round(xpos)), 0, n_wl_pixel - 1)
        index_wl_l = np.clip(int(np.round(xl)), 0, n_wl_pixel - 1)
        index_wl_h = np.clip(int(np.round(xh)), 0, n_wl_pixel - 1)

        # Assuming this functionality also depends on self.sync_avg_x or self.sync_avg_y if implemented
        # For now, it directly updates the source spectrum data, which is fine if sync logic is external.
        # If the sync affects this behavior, you'd add an 'if self.sync_avg_x:' condition here.
        source_spatial_widget.update_spatial_data_wl_avg(index_wl_l, index_wl_c , index_wl_h)


class FilesControlWidget(QtWidgets.QWidget):
    # Signal emitted when a file is selected for loading
    fileSelected = QtCore.pyqtSignal(str)  # file_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize instance variables
        self.directory = ['']
        self.selected_directories = ['']
        self.must_be_in_directory = "reduced"
        self.excluded_file_types = ["cal", "dark", "ff"]
        self.file_paths = []  # Store full file paths
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Create widgets
        self.button = QtWidgets.QPushButton('Choose Directory')
        self.listWidget = QtWidgets.QListWidget()
        self.directorylabel = QtWidgets.QLabel()
        self.fileinfolabel1 = QtWidgets.QLabel()
        self.fileinfolabel2 = QtWidgets.QLabel()
        
        # Set initial text
        self.directorylabel.setText('Current directory: ' + self.directory[0])
        self.directorylabel.setWordWrap(True)
        self.fileinfolabel1.setText('Files sub-directory: ' + self.must_be_in_directory)
        
        file_type_string = " ".join(self.excluded_file_types)
        self.fileinfolabel2.setText('Excluded files: ' + file_type_string)
        
        # Add widgets to layout
        self.main_layout.addWidget(self.listWidget)
        self.main_layout.addWidget(self.button)
        self.main_layout.addWidget(self.directorylabel)
        self.main_layout.addWidget(self.fileinfolabel1)
        self.main_layout.addWidget(self.fileinfolabel2)
    
    def _connect_signals(self):
        """Connect widget signals to handlers."""
        self.button.clicked.connect(self.handleChooseDirectories)
        self.listWidget.itemClicked.connect(self.on_file_clicked)

    def handleChooseDirectories(self):
        """Handle directory selection and populate file list."""
        dialog = QtWidgets.QFileDialog(self)
        dialog.setWindowTitle('Choose a directory')
        dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        
        for view in dialog.findChildren((QtWidgets.QListView, QtWidgets.QTreeView)):
            if isinstance(view.model(), QtWidgets.QFileSystemModel):
                view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.listWidget.clear()
            self.file_paths.clear()
            
            list_files, list_dirs = self.all_sav_files(
                dialog.selectedFiles(),
                excludes=self.excluded_file_types,
                in_dir=self.must_be_in_directory
            )
            
            # Store full file paths for later use
            for i, (file, directory) in enumerate(zip(list_files, list_dirs)):
                full_path = os.path.join(directory, file)
                self.file_paths.append(full_path)
                
                # Create display name with number
                display_name = f"{i+1}. {file}"
                self.listWidget.addItem(display_name)
            
            self.directory = dialog.selectedFiles()
            self.directorylabel.setText('Current directory: ' + self.directory[0])
            self.selected_directories = list_dirs
        
        dialog.deleteLater()

        
    def all_sav_files(self, directories, excludes=None, in_dir=None):
        """Find all .sav files in the specified directories."""
        if excludes is None:
            excludes = []
        if in_dir is None:
            in_dir = self.must_be_in_directory
            
        list_of_files = []
        list_of_directories = []
        
        for root, dirs, files in os.walk(directories[0]):       
            for file in files:
                if in_dir in root and file.endswith('.sav'):
                    use = True
                    for exclude in excludes:
                        if exclude in file:
                            use = False
                            break
                    if use:
                        list_of_files.append(file)
                        list_of_directories.append(root)
                 
        return list_of_files, list_of_directories
    
    def on_file_clicked(self, item):
        """Handle file selection from the list."""
        try:
            # Extract the item number from the display text (e.g., "1. filename.sav")
            item_text = item.text()
            item_number = int(item_text.split('.')[0]) - 1
            
            if 0 <= item_number < len(self.file_paths):
                file_path = self.file_paths[item_number]
                print(f"Selected file: {file_path}")
                # Emit signal with the selected file path
                self.fileSelected.emit(file_path)
            else:
                print(f"Invalid file selection: index {item_number} out of range")
                
        except (ValueError, IndexError) as e:
            print(f"Error processing file selection: {e}")    