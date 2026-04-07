"""
Spectrum limit control widgets.

This module contains control panels for managing spectrum Y-axis limits and 
histogram synchronization.
"""

import numpy as np
from pyqtgraph.Qt import QtCore, QtWidgets
from typing import Optional, Tuple, Any
from functools import partial

from .base_widgets import BaseControlWidget


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
                
                # Reset histogram to auto-range by getting current data range
                try:
                    if hasattr(self.spectrum_image_widget, 'imageItem') and self.spectrum_image_widget.imageItem.image is not None:
                        image_data = self.spectrum_image_widget.imageItem.image
                        min_val = float(np.nanmin(image_data))
                        max_val = float(np.nanmax(image_data))
                        self.spectrum_image_widget.histogram.setLevels(min_val, max_val)
                    else:
                        # Fallback: use histogram's autoHistogramRange
                        self.spectrum_image_widget.histogram.autoHistogramRange()
                except Exception as e:
                    print(f"Error resetting histogram levels: {e}")
                    # Last resort: try autoHistogramRange
                    try:
                        self.spectrum_image_widget.histogram.autoHistogramRange()
                    except:
                        pass
    
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
