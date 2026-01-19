"""
Line control widgets for averaging and synchronization.

This module contains control panels for managing averaging lines and synchronization
between different plot windows.
"""

import numpy as np
from pyqtgraph.Qt import QtCore, QtWidgets
from typing import Optional


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
        self.sync_button_y_avg.clicked.connect(self._handle_avg_y_sync_toggle) # Connect to internal handler
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
        spectral_row_layout.addWidget(self.button_remove_x_avg, 1)  # Stretch factor 1 to fill width
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
        spatial_row_layout.addWidget(self.button_remove_y_avg, 1)  # Stretch factor 1 to fill width
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
    def _handle_avg_y_sync_toggle(self, checked: bool):
        """Handle the avg Y sync toggle."""
        self.toggleAvgYSync.emit(checked)
        self.sync_button_y_avg.setStyleSheet("background-color: red;" if checked else "")

    @QtCore.pyqtSlot(bool)
    def _handle_sync_zoom_toggle(self, checked: bool):
        """Handle the sync zoom toggle."""
        self.syncZoomToggled.emit(checked)
        self.sync_zoom_button.setStyleSheet("background-color: red;" if checked else "")

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
