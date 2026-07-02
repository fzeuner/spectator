"""
Spectrum limit control widgets.

This module contains control panels for managing spectrum Y-axis limits and 
histogram synchronization.
"""

import numpy as np
from pyqtgraph.Qt import QtCore, QtWidgets
from typing import Optional, Tuple, Any

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
                 spatial_y_widget: 'StokesSpatialYWindow' = None,
                 average_spectrum_widget: 'AverageSpectrumWindow' = None,
                 spectrum_image_y_widget: 'StokesSpectrumYImageWindow' = None,
                 parent: Optional[QtWidgets.QWidget] = None):
        """
        Initialize spectrum limit control group.
        
        Args:
            stokes_name: Name of the Stokes parameter
            spectrum_widget: Associated spectrum plot widget
            spectrum_image_widget: Associated spectrum image widget
            spatial_widget: Associated spatial plot widget (z on x-axis)
            spatial_y_widget: Associated spatial Y plot widget (z on x-axis)
            average_spectrum_widget: Associated average spectrum widget (z on y-axis)
            parent: Parent widget
        """
        super().__init__(f"{stokes_name}", parent)
        
        self.stokes_name = stokes_name
        self.spectrum_widget = spectrum_widget
        self.spectrum_image_widget = spectrum_image_widget
        self.spatial_widget = spatial_widget
        self.spatial_y_widget = spatial_y_widget
        self.average_spectrum_widget = average_spectrum_widget
        self.spectrum_image_y_widget = spectrum_image_y_widget
        
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
        
        # Min/Max limit controls - start as read-only but editable when checked
        self.min_limit_edit = self.add_line_edit(
            "Min:",
            initial_value="0.0",
            callback=self._on_limit_edit_changed
        )
        self.min_limit_edit.setReadOnly(True)
        
        self.max_limit_edit = self.add_line_edit(
            "Max:",
            initial_value="1.0", 
            callback=self._on_limit_edit_changed
        )
        self.max_limit_edit.setReadOnly(True)
    
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
    
    def _z_axis_targets(self):
        """Return (widget, axis) pairs for all plots whose z maps to a view axis."""
        return (
            (self.spectrum_widget, 'y'),
            (self.spatial_widget, 'x'),
            (self.spatial_y_widget, 'x'),
            (self.average_spectrum_widget, 'y'),
        )

    def _set_edit_values(self, min_val: float, max_val: float, fmt: str = "{:.2f}"):
        """Set both min/max edit boxes without triggering their change callbacks."""
        for edit, val in ((self.min_limit_edit, min_val), (self.max_limit_edit, max_val)):
            edit.blockSignals(True)
            edit.setText(fmt.format(val))
            edit.blockSignals(False)

    def _current_histogram_range(self):
        """Return (min, max) from the histogram levels, falling back to image data."""
        widget = self.spectrum_image_widget
        if not widget:
            return None, None
        try:
            levels = widget.histogram.getLevels()
            h_min, h_max = float(levels[0]), float(levels[1])
            if h_min < h_max:
                return h_min, h_max
        except Exception:
            pass
        try:
            img = widget.image_item.image
            if img is not None and img.size > 0:
                return float(np.nanmin(img)), float(np.nanmax(img))
        except Exception:
            pass
        return None, None

    def _set_autorange(self, enable: bool):
        """Enable or disable auto-range on the z-axis of all plots."""
        for widget, axis in self._z_axis_targets():
            if not widget:
                continue
            widget.plotItem.enableAutoRange(axis=axis, enable=enable)
            if enable:
                widget.plotItem.autoRange()

    def _apply_fixed_limits(self, min_val: float, max_val: float):
        """Set the view range on every z-axis plot and persist the fixed values."""
        for widget, axis in self._z_axis_targets():
            if not widget:
                continue
            if axis == 'y':
                widget.plotItem.setYRange(min_val, max_val, padding=0)
            else:
                widget.plotItem.setXRange(min_val, max_val, padding=0)
        for widget, method in (
            (self.spectrum_image_widget, 'set_fixed_levels'),
            (self.spectrum_image_y_widget, 'set_fixed_levels'),
            (self.spectrum_widget, 'set_fixed_y_range'),
            (self.spatial_widget, 'set_fixed_x_range'),
        ):
            if widget and hasattr(widget, method):
                getattr(widget, method)(min_val, max_val)

    def _clear_fixed_limits(self):
        """Clear the stored fixed values so data updates no longer enforce them."""
        for widget, method in (
            (self.spectrum_image_widget, 'clear_fixed_levels'),
            (self.spectrum_image_y_widget, 'clear_fixed_levels'),
            (self.spectrum_widget, 'clear_fixed_y_range'),
            (self.spatial_widget, 'clear_fixed_x_range'),
        ):
            if widget and hasattr(widget, method):
                getattr(widget, method)()

    def _toggle_fix_spectrum_limits(self, state: QtCore.Qt.CheckState):
        """Toggle fixed spectrum limits mode."""
        fixed = state == QtCore.Qt.CheckState.Checked
        self.min_limit_edit.setReadOnly(not fixed)
        self.max_limit_edit.setReadOnly(not fixed)
        hist = getattr(self.spectrum_image_widget, 'histogram', None)

        if fixed:
            # Seed the edit boxes from the current image range, then apply
            min_val, max_val = self._current_histogram_range()
            if min_val is not None:
                self._set_edit_values(min_val, max_val, "{:.4f}")
            self._update_spectrum_limits_from_edits()
            self._set_autorange(False)
            if hist:
                hist.sigLevelsChanged.connect(self._on_histogram_levels_changed)
        else:
            self._clear_fixed_limits()
            self._set_autorange(True)
            if hist:
                try:
                    hist.sigLevelsChanged.disconnect(self._on_histogram_levels_changed)
                except (TypeError, RuntimeError):
                    pass
                # Reset histogram levels to the current data range
                min_val, max_val = self._current_histogram_range()
                if min_val is not None:
                    hist.setLevels(min_val, max_val)

    def _on_histogram_levels_changed(self):
        """Sync edit boxes and all z-axis plots from the histogram levels."""
        if not self.fix_limits_checkbox.isChecked():
            return
        if not (self.spectrum_image_widget and self.spectrum_image_widget.histogram):
            return
        min_val, max_val = self.spectrum_image_widget.histogram.getLevels()
        self._set_edit_values(min_val, max_val)
        self._apply_fixed_limits(min_val, max_val)

    def _update_spectrum_limits_from_edits(self):
        """Apply manual z value limits to the spectrum plot and image histogram."""
        try:
            min_val = float(self.min_limit_edit.text())
            max_val = float(self.max_limit_edit.text())
        except ValueError:
            self.min_limit_edit.setStyleSheet("background-color: red;")
            self.max_limit_edit.setStyleSheet("background-color: red;")
            return

        if min_val >= max_val:
            return  # Invalid range

        if self.fix_limits_checkbox.isChecked():
            self._apply_fixed_limits(min_val, max_val)

        if self.spectrum_image_widget and self.spectrum_image_widget.histogram:
            self.spectrum_image_widget.histogram.setLevels(min_val, max_val)
    
    def _update_limit_edits_from_plot(self, limits: Tuple[float, float]):
        """Update min/max QLineEdit widgets from plot's actual Y-range."""
        if not self.fix_limits_checkbox.isChecked():
            self._set_edit_values(limits[0], limits[1])
    
    def _on_limit_edit_changed(self):
        """Handle manual limit edit changes."""
        if self.fix_limits_checkbox.isChecked():
            self._update_spectrum_limits_from_edits()
        
        # Reset styling
        self.min_limit_edit.setStyleSheet("")
        self.max_limit_edit.setStyleSheet("")
