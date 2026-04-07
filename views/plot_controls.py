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
from utils.plotting import create_wavelength_limit_controls
from utils.synchronization import SynchronizationManager


class PlotControlWidget(QtWidgets.QWidget):
    crosshairMoved = QtCore.pyqtSignal(float, float, int) # x, y, source_stokes_index
    xlamRangeChanged = QtCore.pyqtSignal(float, float)  # Emit (min, max)
    resetXlamRangeRequested = QtCore.pyqtSignal()
    spatialRangeChanged = QtCore.pyqtSignal(float, float)  # Emit (min, max)
    resetSpatialRangeRequested = QtCore.pyqtSignal()
    syncZoomToggled = QtCore.pyqtSignal(bool)  # Emit sync zoom state

    def __init__(self):
        super().__init__(None)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        
        # Initialize synchronization state
        self.sync_crosshair = False
        self.sync_avg_x = False
        self.sync_avg_y = False
        self.sync_zoom = False
        
        # Widget collections (set by external controller)
        self.spectrum_image_widgets = []
        self.spectra_widgets = []
        self.spatial_widgets = []
        
        # Initialize synchronization manager
        self.sync_manager = SynchronizationManager(self)
        
        # Initialize UI
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
        
        # Add sync zoom button
        self._init_sync_zoom_button(axis_limits_layout)

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
        
        # Note: Conditional signal connection - may be unused code
    
    def set_widget_collections(self, spectrum_image_widgets: list, spectra_widgets: list, spatial_widgets: list):
        """Update widget collections for synchronization."""
        self.spectrum_image_widgets = spectrum_image_widgets
        self.spectra_widgets = spectra_widgets
        self.spatial_widgets = spatial_widgets
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
        """Handle reset button - reset both lambda and x axis limits simultaneously."""
        self.resetXlamRangeRequested.emit()
        self.resetSpatialRangeRequested.emit()

    @QtCore.pyqtSlot(bool)
    def _handle_sync_zoom_toggle(self, checked: bool):
        """Handle sync zoom toggle - synchronize view ranges across all SpectrumImageWindows."""
        self.sync_zoom = checked
        
        # Update button styling
        if hasattr(self, 'sync_zoom_button'):
            self.sync_zoom_button.setStyleSheet("background-color: red;" if checked else "")
        
        if checked:
            # Reset all windows to full zoom when sync is activated
            for window in self.spectrum_image_widgets:
                try:
                    window.plotItem.setXRange(0, window.n_spectral - 1, padding=0)
                    window.plotItem.setYRange(0, window.n_x_pixel - 1, padding=0)
                except Exception as e:
                    print(f"Error resetting zoom: {e}")
            
            # Connect viewRangeChanged signals for continuous sync
            for window in self.spectrum_image_widgets:
                try:
                    if hasattr(window, 'plotItem') and hasattr(window.plotItem, 'vb'):
                        window.plotItem.vb.sigRangeChanged.connect(self._on_zoom_sync_range_changed)
                except Exception as e:
                    print(f"Error connecting zoom sync: {e}")
            
            # Initialize limit displays with current full zoom ranges
            if self.spectrum_image_widgets:
                window = self.spectrum_image_widgets[0]
                self._update_limit_displays_for_sync_zoom(0, window.n_spectral - 1, 0, window.n_x_pixel - 1)
        else:
            # Disconnect viewRangeChanged signals when sync is disabled
            for window in self.spectrum_image_widgets:
                try:
                    if hasattr(window, 'plotItem') and hasattr(window.plotItem, 'vb'):
                        window.plotItem.vb.sigRangeChanged.disconnect(self._on_zoom_sync_range_changed)
                except Exception as e:
                    pass  # Ignore disconnect errors
            
            # Reset limit display styling to normal when sync is disabled
            self._reset_limit_display_styling()
    
    def _on_zoom_sync_range_changed(self, vb, ranges):
        """Handle zoom changes when sync zoom is active."""
        if not hasattr(self, 'sync_zoom') or not self.sync_zoom:
            return
            
        try:
            x_range, y_range = ranges
            x_min, x_max = x_range
            y_min, y_max = y_range
            
            # Apply this range to all other SpectrumImageWindows
            for window in self.spectrum_image_widgets:
                try:
                    if window.plotItem.vb != vb:  # Don't update the source window
                        window.plotItem.vb.sigRangeChanged.disconnect(self._on_zoom_sync_range_changed)
                        window.plotItem.setXRange(x_min, x_max, padding=0)
                        window.plotItem.setYRange(y_min, y_max, padding=0)
                        window.plotItem.vb.sigRangeChanged.connect(self._on_zoom_sync_range_changed)
                except Exception as e:
                    print(f"Error syncing zoom: {e}")
            
            # Update limit displays with current zoom ranges as grey text
            self._update_limit_displays_for_sync_zoom(x_min, x_max, y_min, y_max)
                    
        except Exception as e:
            print(f"Error in zoom sync: {e}")
    
    def _update_limit_displays_for_sync_zoom(self, x_min, x_max, y_min, y_max):
        """Update wavelength and x limit displays with current zoom ranges as grey text."""
        try:
            # Update wavelength (spectral) limit displays
            if hasattr(self, 'wavelength_min_edit') and hasattr(self, 'wavelength_max_edit'):
                self.wavelength_min_edit.blockSignals(True)
                self.wavelength_max_edit.blockSignals(True)
                self.wavelength_min_edit.setText(f"{x_min:.1f}")
                self.wavelength_max_edit.setText(f"{x_max:.1f}")
                self.wavelength_min_edit.setStyleSheet("color: grey;")
                self.wavelength_max_edit.setStyleSheet("color: grey;")
                # Mark as sync-updated to distinguish from manual entries
                self.wavelength_min_edit.setProperty('sync_updated', True)
                self.wavelength_max_edit.setProperty('sync_updated', True)
                self.wavelength_min_edit.blockSignals(False)
                self.wavelength_max_edit.blockSignals(False)
            
            # Update spatial (x pixel) limit displays  
            if hasattr(self, 'spatial_min_edit') and hasattr(self, 'spatial_max_edit'):
                self.spatial_min_edit.blockSignals(True)
                self.spatial_max_edit.blockSignals(True)
                self.spatial_min_edit.setText(f"{y_min:.1f}")
                self.spatial_max_edit.setText(f"{y_max:.1f}")
                self.spatial_min_edit.setStyleSheet("color: grey;")
                self.spatial_max_edit.setStyleSheet("color: grey;")
                # Mark as sync-updated to distinguish from manual entries
                self.spatial_min_edit.setProperty('sync_updated', True)
                self.spatial_max_edit.setProperty('sync_updated', True)
                self.spatial_min_edit.blockSignals(False)
                self.spatial_max_edit.blockSignals(False)
        except Exception as e:
            print(f"Error updating limit displays: {e}")
    
    def _reset_limit_display_styling(self):
        """Reset limit display styling to normal when sync zoom is disabled."""
        try:
            # Reset wavelength (spectral) limit displays
            if hasattr(self, 'wavelength_min_edit') and hasattr(self, 'wavelength_max_edit'):
                self.wavelength_min_edit.setStyleSheet("")
                self.wavelength_max_edit.setStyleSheet("")
                self.wavelength_min_edit.setProperty('sync_updated', False)
                self.wavelength_max_edit.setProperty('sync_updated', False)
            
            # Reset spatial (x pixel) limit displays  
            if hasattr(self, 'spatial_min_edit') and hasattr(self, 'spatial_max_edit'):
                self.spatial_min_edit.setStyleSheet("")
                self.spatial_max_edit.setStyleSheet("")
                self.spatial_min_edit.setProperty('sync_updated', False)
                self.spatial_max_edit.setProperty('sync_updated', False)
        except Exception as e:
            print(f"Error resetting limit display styling: {e}")

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
        if group_name == 'wavelength':
            edit.editingFinished.connect(self._wavelength_range_changed)
        elif group_name == 'spatial':
            edit.editingFinished.connect(self._spatial_range_changed)
            
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
    
    def _apply_range_to_widgets(self, min_val, max_val, range_type: str):
        """Apply range values to appropriate widgets."""
        if range_type == 'spatial':
            # Apply to spectrum image windows
            for image_widget in self.spectrum_image_widgets:
                if hasattr(image_widget, 'update_spatial_range'):
                    image_widget.update_spatial_range(min_val, max_val)
            # Apply to spatial windows  
            for spatial_widget in self.spatial_widgets:
                if hasattr(spatial_widget, 'update_spatial_range'):
                    spatial_widget.update_spatial_range(min_val, max_val)
        elif range_type == 'wavelength':
            # Apply to spectrum windows
            for spectrum_widget in self.spectra_widgets:
                if hasattr(spectrum_widget, 'update_spectral_range'):
                    spectrum_widget.update_spectral_range(min_val, max_val)
            # Apply to spectrum image windows  
            for image_widget in self.spectrum_image_widgets:
                if hasattr(image_widget, 'update_spectral_range'):
                    image_widget.update_spectral_range(min_val, max_val)
    
    def _spatial_range_changed(self):
        """Handle spatial (x pixel) range change from edits."""
        min_text = self.spatial_min_edit.text().strip()
        max_text = self.spatial_max_edit.text().strip()
        
        min_val, max_val = self._parse_range_values(min_text, max_text)
        
        if min_val is None and max_val is None:
            return

        self._apply_range_to_widgets(min_val, max_val, 'spatial')
        
        # Emit signal only if both values are valid
        if min_val is not None and max_val is not None:
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
        # Use existing set_widget_collections method to avoid duplication
        self.set_widget_collections(spectrum_image_widgets, spectra_widgets, spatial_widgets)
        
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
        
        min_val, max_val = self._parse_range_values(min_text, max_text)
        
        if min_val is None and max_val is None:
            return

        self._apply_range_to_widgets(min_val, max_val, 'wavelength')
