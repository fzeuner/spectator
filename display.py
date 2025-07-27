#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 09:56:31 2024

@author: franziskaz

WARNING: if the qdarkstyle is used, there are some minor bugs in Dock and VerticalLabel:
    create the following links (look at the files in this folder):
        - mv ~/miniconda3/envs/bayes/lib/python3.12/site-packages/pyqtgraph/widgets/VerticalLabel.py ~/miniconda3/envs/bayes/lib/python3.12/site-packages/pyqtgraph/widgets/VerticalLabel.py_bk
        - ln -s ~/code/dkist/VerticalLabel.py ~/miniconda3/envs/bayes/lib/python3.12/site-packages/pyqtgraph/widgets/
        - mv ~/miniconda3/envs/bayes/lib/python3.12/site-packages/pyqtgraph/dockarea/Dock.py ~/miniconda3/envs/bayes/lib/python3.12/site-packages/pyqtgraph/dockarea/Dock.py_bk
        - ln -s ~/code/dkist/Dock.py ~/miniconda3/envs/bayes/lib/python3.12/site-packages/pyqtgraph/dockarea/

pyqtgraph = 0.13.7

INPUT:
    - numpy data cube ordered by N_STOKES, N_WL, N_X 

- TODO: 
    + handle N_STOKES=1 case
    + add spatial x and spatial y profile
    + averaging in x and/or y
    + large data - maybe using fastplotlib?
    + changing point sizes does not work: self.plot.getAxis('left').setStyle(tickFont = QFont().setPointSize(1))
    + multiple crosshairs
    + flexible data (only image spectra, non-stokes scans...)
    
Look at (multiple) images in an interactive way.
"""

# import pyqtgraph.examples
# pyqtgraph.examples.run()

import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
#from PyQt5.QtGui import QFont
import qdarkstyle
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from typing import List, Tuple, Dict, Optional, Any 
from functools import partial

from getWidgetColors import getWidgetColors

CROSSHAIR_COLORS = {'v': 'white', 'h_image': 'dodgerblue', 'h_spectrum_image': 'white'}
AVG_COLORS = ['dodgerblue', 'yellow']
# Define the minimum allowed distance between line1 and line2 (the averaging lines)
MIN_LINE_DISTANCE = 2.0 # Minimum pixel distance 

# --- Helper Functions ---

def AddLine(plotItem: pg.PlotItem, 
            color: str, 
            angle: float, 
            moveable: bool = False, pos=0, style=QtCore.Qt.SolidLine ) -> pg.InfiniteLine:
    """Adds an InfiniteLine to a PlotItem."""
    line = pg.InfiniteLine(pos=pos,angle=angle, movable=moveable)
    line.setPen(color, width=1.8, style=style)
    plotItem.addItem(line, ignoreBounds=True)
    return(line)

def AddCrosshair(plotItem: pg.PlotItem, 
                 vcolor: str, 
                 hcolor: str, 
                 style=QtCore.Qt.DashLine) -> Tuple[pg.InfiniteLine, pg.InfiniteLine]:
    """Adds a crosshair (vertical and horizontal InfiniteLine) to a PlotItem."""
    vLine = AddLine(plotItem, vcolor, 90, style=style)
    hLine = AddLine(plotItem, hcolor, 0, style=style)
    return(vLine, hLine)

class BasePlotWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.graphics_widget.setBackground(getWidgetColors.BG_NORMAL)
        self.plotItem = self.graphics_widget.addPlot(row=0, col=0, colspan=2)
        self.layout.addWidget(self.graphics_widget)
        self.setLayout(self.layout)
        
        self.label = pg.LabelItem(justify='left', size='6pt')
        self.graphics_widget.addItem(self.label, row=1, col=0)
        
        self.current_wl_idx = 0
        self.current_x_idx = 0
        
        self.current_x_idx_avg = 0
        self.current_wl_idx_avg = 0
    
def CreateYLimitLabel(name:str):
    """Label for spectrum y limits"""
    limit_label = QtWidgets.QLabel(name)
    limit_edit = QtWidgets.QLineEdit()
    limit_edit.setEnabled(False)

    layout = QtWidgets.QHBoxLayout()
    layout.addWidget(limit_label)
    layout.addWidget(limit_edit)
    return(limit_label, limit_edit, layout)

class LinesControlGroup(QtWidgets.QWidget): 
    """
    A widget for the line controls.
    """
    toggleCrosshairSync = QtCore.pyqtSignal(bool)
    toggleAvgXSync = QtCore.pyqtSignal(bool)
    toggleAvgXRemove = QtCore.pyqtSignal(bool)
    toggleAvgYSync = QtCore.pyqtSignal(bool)
    toggleAvgYRemove = QtCore.pyqtSignal(bool)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        # This layout will hold your QGroupBoxes
        self.main_v_layout = QtWidgets.QVBoxLayout(self) # Set the layout directly on self

        # QGroupBox for Synchronization buttons
        self.synchronize_box = QtWidgets.QGroupBox("Synchronize")
        sync_box_layout = QtWidgets.QVBoxLayout(self.synchronize_box) # Layout for the synchronize_box

        self.sync_button = QtWidgets.QPushButton("crosshair")
        self.sync_button.setCheckable(True)
        self.sync_button.clicked.connect(self._on_toggle_crosshair_sync) # Connect to internal handler
        sync_box_layout.addWidget(self.sync_button)

        self.sync_button_y_avg = QtWidgets.QPushButton("spatial avg.")
        self.sync_button_y_avg.setCheckable(True)
        self.sync_button_y_avg.clicked.connect(self._on_toggle_avg_y_sync) # Connect to internal handler
        sync_box_layout.addWidget(self.sync_button_y_avg)

        self.sync_button_x_avg = QtWidgets.QPushButton("wavelength avg.")
        self.sync_button_x_avg.setCheckable(True)
        self.sync_button_x_avg.clicked.connect(self._on_toggle_avg_x_sync) # Connect to internal handler
        sync_box_layout.addWidget(self.sync_button_x_avg)

        self.main_v_layout.addWidget(self.synchronize_box) # Add the group box to the main layout

        # Avg lines control

        self.avg_lines_box = QtWidgets.QGroupBox("Avg. lines")
        avg_lines_box_layout = QtWidgets.QVBoxLayout(self.avg_lines_box)
        
        self.button_remove_x_avg = QtWidgets.QPushButton("remove wavelength avg.")
        self.button_remove_x_avg.setCheckable(True)
        self.button_remove_x_avg.clicked.connect(self._on_toggle_avg_x_remove) # Connect to internal handler
        
        avg_lines_box_layout.addWidget(self.button_remove_x_avg)
        
        self.button_remove_y_avg = QtWidgets.QPushButton("remove spatial avg.")
        self.button_remove_y_avg.setCheckable(True)
        self.button_remove_y_avg.clicked.connect(self._on_toggle_avg_y_remove) # Connect to internal handler
        
        avg_lines_box_layout.addWidget(self.button_remove_y_avg)
        
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
            self.toggleAvgYSync.emit(checked) # Emit the class-level signal
            self.button_remove_x_avg.setStyleSheet("background-color: red;" if checked else "")
            
    @QtCore.pyqtSlot(bool)
    def _on_toggle_avg_y_remove(self, checked: bool):
            self.toggleAvgYSync.emit(checked) # Emit the class-level signal
            self.button_remove_y_avg.setStyleSheet("background-color: red;" if checked else "")

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


class SpectrumLimitControlGroup(QtWidgets.QGroupBox):
    """
    A widget responsible for managing the Y-axis limit controls
    for a single Stokes spectrum and its corresponding image.
    """
    def __init__(self, stokes_name: str,
                 spectrum_widget: 'StokesSpectrumWindow',
                 spectrum_image_widget: 'StokesSpectrumImageWindow',
                 parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(f"{stokes_name} y-axis limits", parent)
        self.stokes_name = stokes_name
        self.spectrum_widget = spectrum_widget
        self.spectrum_image_widget = spectrum_image_widget

        self._init_ui()
        self._connect_signals()
        self._set_initial_values()

    def _init_ui(self):
        self.layout = QtWidgets.QVBoxLayout(self)

        self.fix_limits_checkbox = QtWidgets.QCheckBox("Fix y-axis limits")
        
        self.min_limit_label, self.min_limit_edit, min_layout = CreateYLimitLabel("Min:")
        self.max_limit_label, self.max_limit_edit, max_layout = CreateYLimitLabel("Max:")

        self.layout.addWidget(self.fix_limits_checkbox)
        self.layout.addLayout(min_layout)
        self.layout.addLayout(max_layout)

    def _set_initial_values(self):
        initial_min, initial_max = self.spectrum_widget.plotItem.viewRange()[1]
        self._update_limit_edits_from_plot((initial_min, initial_max))
        self.min_limit_edit.setEnabled(False) # Start with limits unfixed
        self.max_limit_edit.setEnabled(False) # Start with limits unfixed

    def _connect_signals(self):
        self.fix_limits_checkbox.stateChanged.connect(self._toggle_fix_spectrum_limits)
        self.min_limit_edit.editingFinished.connect(self._update_spectrum_limits_from_edits)
        self.max_limit_edit.editingFinished.connect(self._update_spectrum_limits_from_edits)
        self.spectrum_widget.yRangeChanged.connect(self._update_limit_edits_from_plot)

    def _toggle_fix_spectrum_limits(self, state: QtCore.Qt.CheckState):
        fixed = state == QtCore.Qt.Checked
        self.min_limit_edit.setEnabled(fixed)
        self.max_limit_edit.setEnabled(fixed)

        if fixed:
            self._update_spectrum_limits_from_edits() # Apply current values from edits
            self.spectrum_widget.plotItem.enableAutoRange(axis='y', enable=False)
            if self.spectrum_image_widget and self.spectrum_image_widget.histogram:
                self.spectrum_image_widget.histogram.sigLevelsChanged.connect(
                    partial(self._on_histogram_levels_changed)
                )
        else:
            self.spectrum_widget.plotItem.enableAutoRange(axis='y', enable=True)
            self.spectrum_widget.plotItem.autoRange(y=True)

            if self.spectrum_image_widget and self.spectrum_image_widget.histogram:
                # Disconnect the signal (assuming you stored the partial connection if needed,
                # otherwise rely on the _on_histogram_levels_changed check)
                try:
                    # Example: if you stored `self._histogram_connection_callable`
                    # self.spectrum_image_widget.histogram.sigLevelsChanged.disconnect(self._histogram_connection_callable)
                    pass # relying on check inside slot for now
                except (TypeError, RuntimeError):
                    pass # Ignore if not connected or already disconnected

                self.spectrum_image_widget.histogram.setLevels(None, None) # Resets histogram to auto-range

    def _on_histogram_levels_changed(self):
        """
        Slot to be called when the histogram levels change.
        Updates the min/max QLineEdit fields and the spectrum plot's Y-range.
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

    def _update_spectrum_limits_from_edits(self):
        """Applies manual y-axis limits to the spectrum plot and image histogram."""
        if not self.fix_limits_checkbox.isChecked():
            return
        try:
            min_val_str = self.min_limit_edit.text()
            max_val_str = self.max_limit_edit.text()

            min_val = float(min_val_str) if min_val_str else None
            max_val = float(max_val_str) if max_val_str else None

            if min_val is None or max_val is None:
                print(f"[{self.stokes_name}] Warning: Empty input for fixed Y-axis limit.")
                return

            if min_val >= max_val:
                self.min_limit_edit.setStyleSheet("background-color: red;")
                self.max_limit_edit.setStyleSheet("background-color: red;")
                return
            else:
                self.min_limit_edit.setStyleSheet("")
                self.max_limit_edit.setStyleSheet("")

            if self.spectrum_widget:
                self.spectrum_widget.plotItem.setYRange(min_val, max_val, padding=0)
                self.spectrum_widget.plotItem.enableAutoRange(axis='y', enable=False)

            if self.spectrum_image_widget and self.spectrum_image_widget.histogram:
                self.spectrum_image_widget.histogram.setLevels(min_val, max_val)

        except ValueError:

            self.min_limit_edit.setStyleSheet("background-color: red;")
            self.max_limit_edit.setStyleSheet("background-color: red;")

    def _update_limit_edits_from_plot(self, limits: Tuple[float, float]):
        """Updates min/max QLineEdit widgets from plot's actual Y-range."""

        if not self.fix_limits_checkbox.isChecked():
            min_val, max_val = limits
            self.min_limit_edit.blockSignals(True)
            self.max_limit_edit.blockSignals(True)
            self.min_limit_edit.setText(f"{min_val:.2f}")
            self.max_limit_edit.setText(f"{max_val:.2f}")
            self.min_limit_edit.blockSignals(False)
            self.max_limit_edit.blockSignals(False)

def CreateWlLimitLabel(name: str):
    """Label for wavelength limits"""
    wavelength_label = QtWidgets.QLabel(name)
    wavelength_edit = QtWidgets.QLineEdit()
    wavelength_edit.setPlaceholderText("Optional")
    layout = QtWidgets.QHBoxLayout()
    layout.addWidget(wavelength_label)
    layout.addWidget(wavelength_edit)
    return(wavelength_label, wavelength_edit, layout)

def CreateHistrogram(image_item: pg.ImageItem, 
                     layout: QtWidgets.QLayout) -> pg.HistogramLUTWidget:
    """Creates and configures a HistogramLUTWidget."""
    histogram = pg.HistogramLUTWidget()
    histogram.setImageItem(image_item)
    histogram.setBackground(getWidgetColors.BG_NORMAL) 
    histogram.setFixedWidth(60) # Set a fixed width of 120 pixels
    layout.addWidget(histogram)
    return(histogram)

def SetPlotXlamRange(plot_widget: pg.PlotWidget, 
                     wavelength: np.ndarray, 
                     min_val: Optional[float] = None, 
                     max_val: Optional[float] = None, 
                     axis: str = 'x'):
    """Sets the wavelength range of a pyqtgraph PlotWidget."""
    xmin = None
    xmax = None
    
    if axis == 'x':
        x = 0
    elif axis == 'y':
        x = 1
    else:
        print(f"Error: Invalid axis '{axis}'. Must be 'x' or 'y'.")
        return

    if min_val is not None and max_val is not None:
        if min_val < max_val:
            xmin, xmax = min_val, max_val
        elif min_val == max_val:
            xmin, xmax = min_val - 0.5, max_val + 0.5 # Small range for single value
            print("Warning: wavelength min is equal to wavelength max.")
        else:
            print("Warning: wavelength min is greater than wavelength max.")
            return
    elif min_val is not None:
        xmax = plot_widget.getViewBox().viewRange()[x][1]
        xmin = min_val
    elif max_val is not None:
        xmin = plot_widget.getViewBox().viewRange()[x][0]
        xmax = max_val
    else:
        # Reset to full range if no valid min or max provided
        if len(wavelength) > 0:
            xmin, xmax = wavelength.min(), wavelength.max()
        else:
            print("Warning: Cannot set wavelength range, no wavelength data available.")
            return

    if xmin is not None and xmax is not None:
        if axis == 'x':
            plot_widget.setXRange(xmin, xmax, padding=0)
        elif axis == 'y':
            plot_widget.setYRange(xmin, xmax, padding=0)
        else:
            # This case should ideally be caught earlier
            print(f"Error: Invalid axis '{axis}'. Must be 'x' or 'y'.")

def ResetPlotXlamRange(plot_widget: pg.PlotWidget, wavelength: np.ndarray, axis: str = 'x'):
    """Resets the x-axis range of a pyqtgraph PlotWidget to the full wavelength range."""
    if len(wavelength) > 0:
        if axis == 'x':
            plot_widget.setXRange(wavelength.min(), wavelength.max(), padding=0)
        elif axis == 'y':
            plot_widget.setYRange(wavelength.min(), wavelength.max(), padding=0)
        else:
            print(f"Error: Invalid axis '{axis}'. Must be 'x' or 'y'.")
    else:
        print("Warning: Cannot reset wavelength range, no wavelength data available.")
        
def update_crosshair_from_mouse(plot_item: pg.PlotItem, v_line: pg.InfiniteLine, h_line: pg.InfiniteLine, pos: QtCore.QPointF):
    """Updates the crosshair position based on the mouse position."""
    if plot_item.sceneBoundingRect().contains(pos):
        mousePoint = plot_item.vb.mapSceneToView(pos)
        xpos, ypos = mousePoint.x(), mousePoint.y()
        v_line.setPos(xpos)
        h_line.setPos(ypos)
        return xpos, ypos
    return None, None

def ExampleData() -> np.ndarray:
    """
    Generates example Stokes spectropolarimetric data with defined structure.
    Returns:
        data (np.ndarray): Stokes data cube of shape (N_STOKES, N_WL, N_X)
    """
    print("Generating random test data...")

    # Define dimensions
    N_STOKES, N_WL, N_X = 4, 250, 150

    # Initialize data with random noise
    data = np.random.random(size=(N_STOKES, N_WL, N_X)) * 5

    # Define Gaussian parameters for Stokes I
    center_wl, center_x = N_WL // 2, N_X // 2
    width_wl, width_x = N_WL // 10, N_X // 8

    # Create 2D spatial Gaussian and add to Stokes I
    yy, xx = np.mgrid[:N_WL, :N_X]
    spatial_gaussian = np.exp(-(((xx - center_x) / width_x) ** 2) / 2)
    data[0] += 10 * spatial_gaussian

    # Create 1D spectral Gaussian and apply to Stokes I
    spectral_gaussian = np.exp(-((np.arange(N_WL) - center_wl) / width_wl) ** 2 / 2)
    data[0] *= spectral_gaussian[:, np.newaxis]
    data[1, center_wl, center_x - 5 : center_x + 5] += 3
    return data

def InitializeImageplotItem(item: pg.PlotItem, yvalues: bool = True, x_label: str = "x",
                            y_label: str = "y", x_units: str = "x", y_units: str = "pixel"):
    """Initializes common properties for image PlotItems."""
    for axis_name in ['left', 'bottom', 'top']:
        axis = item.getAxis(axis_name)
        axis.enableAutoSIPrefix(False) # Disable auto SI prefix for all relevant axes
        if axis_name == 'left':
            axis.setWidth(42)
        else: # 'bottom' and 'top'
            axis.setHeight(15)

    item.setLabel("bottom", text=x_label, units=x_units)
    item.setLabel("left", text=y_label, units=y_units)

    item.showAxes(True, showValues=(yvalues, True, False, False), size=15)
    item.setDefaultPadding(0.0)
    item.invertY(False)

def InitializeSpectrumplotItem(plot: pg.PlotItem, y_label: str = "", x_label: str = "λ", x_units: str = "pixel"):
    """Initializes common properties for spectrum PlotItems."""

    plot.invertY(False)  # Orient y axis to run bottom-to-top
    plot.setDefaultPadding(0.0) # Plot without padding data range
    plot.showAxes(True, showValues=(True, True, False, False), size=15)

    left_axis = plot.getAxis('left')
    bottom_axis = plot.getAxis('bottom')
    top_axis = plot.getAxis('top')

    for axis in [left_axis, bottom_axis, top_axis]:
        axis.enableAutoSIPrefix(False)

    left_axis.setWidth(40)
    left_axis.setStyle(autoExpandTextSpace=True, hideOverlappingLabels=True)

    plot.setLabel("bottom", text=x_label, units=x_units)
    if y_label: # Only set left label if a y_label is provided
        plot.setLabel("left", text=y_label)

def ValidateData(data):
    max_dim=10
    if data.ndim != 3 or data.shape[0] > max_dim:
        print(f"Error: Data shape mismatch. Expected (<10, N_wl, N_x), got {data.shape}")
        # Optionally: Create placeholder data or raise an error
        n_wl_dummy, n_x_dummy = 50, 10
        data = np.random.random(size=(4, n_wl_dummy, n_x_dummy))
        print("Using dummy data instead.")
        
    names = [str(i) for i in range(1, data.shape[0] + 1)]
    return(data, names)

# --- PlotControlWidget ---
class PlotControlWidget(QtWidgets.QWidget):
    crosshairMoved = QtCore.pyqtSignal(float, float, int) # x, y, source_stokes_index
    xlamRangeChanged = QtCore.pyqtSignal(object, object)
    resetXlamRangeRequested = QtCore.pyqtSignal()

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
        # Changed 'right' to 'above' as per your original code's suggestion
        self.dock_area.addDock(self.lines_dock, 'above', self.limits_dock)

        # --- Widgets for the "limits" dock ---
        limits_content_widget = QtWidgets.QWidget()
        self.limits_layout = QtWidgets.QVBoxLayout(limits_content_widget)
        self.limits_dock.addWidget(limits_content_widget)

        self._init_wavelength_range_controls(self.limits_layout)

        # --- Widgets for the "lines" dock ---
        self.lines_content_widget = LinesControlGroup(self) # Instance of LinesControlGroup
        self.lines_dock.addWidget(self.lines_content_widget)

        # Connect the signals from LinesControlGroup to PlotControlWidget's methods
        self.lines_content_widget.toggleCrosshairSync.connect(self._handle_crosshair_sync_toggle)
        self.lines_content_widget.toggleAvgXSync.connect(self._handle_avg_x_sync_toggle)
        self.lines_content_widget.toggleAvgYSync.connect(self._handle_avg_y_sync_toggle)

    def _init_wavelength_range_controls(self, parent_layout: QtWidgets.QVBoxLayout):
        """Initializes controls for wavelength (wavelength) axis limits, now taking a parent layout."""
        wavelength_group_box = QtWidgets.QGroupBox("λ axis limits")
        limits_wavelength_layout = QtWidgets.QVBoxLayout(wavelength_group_box)

        for limit_type in ['min', 'max']:
            label, edit, layout = CreateWlLimitLabel(limit_type)
            setattr(self, f'wavelength_{limit_type}_label', label)
            setattr(self, f'wavelength_{limit_type}_edit', edit)
            edit.editingFinished.connect(self._wavelength_range_changed)
            limits_wavelength_layout.addLayout(layout)

        self.reset_wavelength_button = QtWidgets.QPushButton("Reset wavelength range")
        self.reset_wavelength_button.clicked.connect(self.resetXlamRangeRequested.emit)
        limits_wavelength_layout.addWidget(self.reset_wavelength_button)

        parent_layout.addWidget(wavelength_group_box)
        parent_layout.addStretch(1)

    def init_spectrum_limit_controls(self, spectra_widgets: List['StokesSpectrumWindow'],
                                     spectrum_image_widgets: List['StokesSpectrumImageWindow'],
                                     spatial_widgets: List['StokesSpatialWindow']):
        self.spectra_widgets = spectra_widgets
        self.spectrum_image_widgets = spectrum_image_widgets
        self.spatial_widgets = spatial_widgets

        for i, spectrum_widget in enumerate(self.spectra_widgets):
            spectrum_image_widget = self.spectrum_image_widgets[i] if i < len(self.spectrum_image_widgets) else None
            if spectrum_image_widget is None:
                continue

            limit_group = SpectrumLimitControlGroup(
                stokes_name=spectrum_widget.name,
                spectrum_widget=spectrum_widget,
                spectrum_image_widget=spectrum_image_widget
            )

            self.limits_layout.addWidget(limit_group)

    def _wavelength_range_changed(self):
        parsed_values = {}
        error_flag = False

        try:
            for limit_type in ['min', 'max']:
                edit_widget = getattr(self, f'wavelength_{limit_type}_edit')
                text = edit_widget.text()
                try:
                    parsed_values[limit_type] = float(text) if text else None
                    edit_widget.setStyleSheet("")
                except ValueError:
                    edit_widget.setStyleSheet("background-color: red;")
                    error_flag = True
                    break

            if error_flag:
                print("Warning: Invalid λ range entered (non-numeric).")
                return

            min_val = parsed_values.get('min')
            max_val = parsed_values.get('max')

            if min_val is not None and max_val is not None and min_val >= max_val:
                print("Warning: λ min should be less than λ max.")
                self.wavelength_min_edit.setStyleSheet("background-color: red;")
                self.wavelength_max_edit.setStyleSheet("background-color: red;")
                return

            self.wavelength_min_edit.setStyleSheet("")
            self.wavelength_max_edit.setStyleSheet("")
            self.xlamRangeChanged.emit(min_val, max_val)

        except Exception as e:
            print(f"An unexpected error occurred in _wavelength_range_changed: {e}")

    @QtCore.pyqtSlot(bool)
    def _handle_crosshair_sync_toggle(self, checked: bool):
        """Slot to receive and handle the crosshair sync toggle state."""
        self.sync_crosshair = checked

    @QtCore.pyqtSlot(bool)
    def _handle_avg_x_sync_toggle(self, checked: bool):
        """Slot to receive and handle the wavelength average sync toggle state."""
        self.sync_avg_x = checked

    @QtCore.pyqtSlot(bool)
    def _handle_avg_y_sync_toggle(self, checked: bool):
        """Slot to receive and handle the spatial average sync toggle state."""
        self.sync_avg_y = checked

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
                    spec_widget.update_wavelength_line(xpos)
                    spec_widget.update_spectrum_data(index_x)
                elif not corresponding_img_widget.crosshair_locked:
                    spec_widget.update_wavelength_line(xpos)
                    spec_widget.update_spectrum_data(index_x)

        else:
            source_spectrum_widget.update_wavelength_line(xpos)
            source_spectrum_widget.update_spectrum_data(index_x)

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

      
# --- Data Display Widgets ---

class StokesSpatialWindow(BasePlotWidget):
    
    xChanged = QtCore.pyqtSignal(float) # Emit x value of hLine

    def __init__(self, data: np.ndarray, stokes_index: int, name: str):
        super().__init__(None)

        self.name = name + " spatial"
        self.full_data = data  # Store the full (wl, x) data
        self.wavelength = np.arange(self.full_data.shape[0])
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

        InitializeSpectrumplotItem(self.plotItem, y_label="x", x_label = "", x_units = "")

    def _setup_connections(self):
        """Connects signals to slots."""
        self.hLine.sigPositionChanged.connect(self._on_hline_moved)

    def _initialize_plot_state(self):
        """Sets initial plot data, vLine position, and updates labels."""
        self.plot_data = self.full_data[self.current_wl_idx, :]
        self.plot_curve.setData(self.x, self.plot_data)
        self.plot_curve.setData(self.x, 0*self.plot_data)

        # Set initial hLine position
        initial_x = self.x[0] if self.x.size > 0 else 0
        self.update_x_line(initial_x) 

    def _update_label(self):
        """Updates the coordinate label."""
        y_value = self.hLine.value()
        # Find the closest index to the current wavelength value
        y_idx = np.argmin(np.abs(self.x - y_value)) if self.x.size > 0 else -1
        intensity_value = np.nan
        if isinstance(self.plot_data, np.ndarray) and self.plot_data.ndim == 1 and 0 <= y_idx < self.plot_data.size:
            intensity_value = self.plot_data[y_idx]

        self.label.setText(f"x={y_value:.1f}, z={intensity_value:.5f}", size='6pt')
        
    # def _update_label_wl_avg(self):
    #         """Updates the coordinate label for avaraged region."""
    #         x_value = self.current_wl_idx_avg
    #         # Find the closest index to the current wavelength value
    #         x_idx = np.argmin(np.abs(self.wavelength - x_value)) if self.wavelength.size > 0 else -1
    #         intensity_value = np.nan
    #         if isinstance(self.plot_data_avg, np.ndarray) and self.plot_data.ndim == 1 and 0 <= x_idx < self.plot_data_avg.size:
    #             intensity_value = self.plot_data_avg[x_idx]

    #         self.label_avg.setText(f"x={x_value:.1f}, z={intensity_value:.5f}", size='6pt')

    def _on_hline_moved(self):
        """Handles internal hLine movement and emits signal."""
        current_y = self.hLine.value()
        self.xChanged.emit(current_y)
        self._update_label()

    @QtCore.pyqtSlot(float)
    def update_x_line(self, y: float):
        """Slot to update the hLine position from external signal."""
        if hasattr(self, 'hLine'):
            # Only update if the value is significantly different to avoid unnecessary updates
            if not np.isclose(self.hLine.value(), y):
                self.hLine.setValue(y)
                self._update_label()
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
            
    def _update_label_wl_avg(self):
                """Updates the coordinate label for avaraged region."""
                wl_value = self.current_wl_idx_avg
                # Find the closest index to the current wavelength value
                x_idx = np.argmin(np.abs(self.x - wl_value)) if self.wavelength.size > 0 else -1
                intensity_value = np.nan
                if isinstance(self.plot_data_avg, np.ndarray) and self.plot_data.ndim == 1 and 0 <= wl_idx < self.plot_data_avg.size:
                    intensity_value = self.plot_data_avg[wl_idx]

                self.label_avg.setText(f"λ={wl_value:.1f}, z={intensity_value:.5f}", size='6pt')

class StokesSpectrumWindow(BasePlotWidget):
    yRangeChanged = QtCore.pyqtSignal(tuple)  # Emit (min, max)
    wavelengthChanged = QtCore.pyqtSignal(float) # Emit wavelength value

    def __init__(self, data: np.ndarray, stokes_index: int, name: str):
        super().__init__(None)

        self.name = name + " spectrum"
        self.full_data = data  # Store the full (wl, x) data
        self.wavelength = np.arange(self.full_data.shape[0])

        self._setup_plot_items()
        self._setup_connections()
        self._initialize_plot_state()

    def _setup_plot_items(self):
        """Initializes plot curve, movable line, and label."""
        self.plot_curve = pg.PlotDataItem() 
        self.plotItem.addItem(self.plot_curve)
        
        self.plot_curve_wl_avg = pg.PlotDataItem(pen=pg.mkPen(AVG_COLORS[1], style=QtCore.Qt.SolidLine, width=2)) 
        self.plotItem.addItem(self.plot_curve_wl_avg)

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
        self.plot_curve.setData(self.wavelength, self.plot_data)
        self.plot_curve.setData(self.wavelength, 0*self.plot_data)

        # Emit initial Y range and update label
        self._emit_y_range_changed(None, self.plotItem.viewRange()[1])

        # Set initial vLine position
        initial_wl = self.wavelength[0] if self.wavelength.size > 0 else 0
        self.update_wavelength_line(initial_wl) 

    def _update_label(self):
        """Updates the coordinate label."""
        wl_value = self.vLine.value()
        # Find the closest index to the current wavelength value
        wl_idx = np.argmin(np.abs(self.wavelength - wl_value)) if self.wavelength.size > 0 else -1
        intensity_value = np.nan
        if isinstance(self.plot_data, np.ndarray) and self.plot_data.ndim == 1 and 0 <= wl_idx < self.plot_data.size:
            intensity_value = self.plot_data[wl_idx]

        self.label.setText(f"λ={wl_value:.1f}, z={intensity_value:.5f}", size='6pt')
        
    def _update_label_x_avg(self):
            """Updates the coordinate label for avaraged region."""
            wl_value = self.current_x_idx_avg
            # Find the closest index to the current wavelength value
            wl_idx = np.argmin(np.abs(self.wavelength - wl_value)) if self.wavelength.size > 0 else -1
            intensity_value = np.nan
            if isinstance(self.plot_data_avg, np.ndarray) and self.plot_data.ndim == 1 and 0 <= wl_idx < self.plot_data_avg.size:
                intensity_value = self.plot_data_avg[wl_idx]

            self.label_avg.setText(f"λ={wl_value:.1f}, z={intensity_value:.5f}", size='6pt')

    def _on_vline_moved(self):
        """Handles internal vLine movement and emits signal."""
        current_wl = self.vLine.value()
        self.wavelengthChanged.emit(current_wl)
        self._update_label()

    def update_wavelength_range(self, min_val: Optional[float], max_val: Optional[float]):
        """Updates the λ-axis range of the spectrum plot."""
        SetPlotXlamRange(self.plotItem, self.wavelength, min_val, max_val, axis='x')

    def reset_wavelength_range(self):
        """Resets the λ-axis range to the initial maximum range."""
        ResetPlotXlamRange(self.plotItem, self.wavelength, axis='x')

    def _emit_y_range_changed(self, axis, limits):
        """Emits the current Y-axis range."""
        self.yRangeChanged.emit(tuple(limits))

    @QtCore.pyqtSlot(float)
    def update_wavelength_line(self, wavelength: float):
        """Slot to update the vLine position from external signal."""
        if hasattr(self, 'vLine'):
            # Only update if the value is significantly different to avoid unnecessary updates
            if not np.isclose(self.vLine.value(), wavelength):
                self.vLine.setValue(wavelength)
                self._update_label()
        else:
            print("Warning: update_wavelength_line called before vLine was initialized.")

    def update_spectrum_data(self, x_idx: int):
        """Updates the plotted spectrum data based on a new spatial index."""
        if not (0 <= x_idx < self.full_data.shape[1]):
            print(f"Error: Provided x_idx {x_idx} is out of bounds for data with {self.full_data.shape[1]} spatial pixels.")
            return

        self.current_x_idx = x_idx
        self.plot_data = self.full_data[:, self.current_x_idx]
        self.plot_curve.setData(self.wavelength, self.plot_data)
        self._update_label() # Update label after data change    

    def update_spectrum_data_x_avg(self, x_idx_l: int, x_idx_c: int , x_idx_h: int):
            """Updates the plotted spectrum data based on a new spatial indices of averaging regions."""

            self.current_x_idx_avg = x_idx_c
            self.plot_data_avg = (self.full_data[x_idx_l:x_idx_h,:]).mean(axis=0)
            self.plot_curve_wl_avg.setData(self.x, self.plot_data_avg)
            self._update_label_x_avg()         

class StokesSpectrumImageWindow(BasePlotWidget):
    crosshairMoved = QtCore.pyqtSignal(float, float, int)
    avgRegionChanged = QtCore.pyqtSignal(float, float, float, int)

    def __init__(self, data: np.ndarray, stokes_index: int, name: str):
        super().__init__(None)

        self.stokes_index = stokes_index
        self.name = name
        self.data = data
        self.n_wl, self.n_x_pixel = self.data.shape 
        self.wavelengths = np.arange(self.n_wl) 
        self.spatial_pixels = np.arange(self.n_x_pixel) 

        self._setup_image_plot()
        self._setup_axes()
        self._setup_crosshair()
        self._setup_v_avg() 

    def _setup_image_plot(self):
        self.image_item = pg.ImageItem()
        self.plotItem.addItem(self.image_item)
        self.histogram = CreateHistrogram(self.image_item, self.layout)

        self.image_item.setImage(self.data.T) # <--- Transpose the data here for plotting wavelength along x axis!

        x_min_wl = self.wavelengths[0] if self.wavelengths.size > 0 else 0
        x_max_wl = self.wavelengths[-1] if self.wavelengths.size > 0 else self.n_wl
        y_min_x = self.spatial_pixels[0] if self.spatial_pixels.size > 0 else 0
        y_max_x = self.spatial_pixels[-1] if self.spatial_pixels.size > 0 else self.n_x_pixel

        self.image_item.setRect(x_min_wl, y_min_x, x_max_wl - x_min_wl, y_max_x - y_min_x)

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
                elif clamped_wl2 == self.n_wl - 1: 
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
        return np.clip(pos, 0, self.n_wl - 1)

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
                elif new_l2 == self.n_wl - 1 and (new_l2 - new_l1) < MIN_LINE_DISTANCE: 
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
                 if new_l2 > self.n_wl - 1: 
                     new_l2 = self.n_wl - 1 
                     new_l1 = max(0, new_l2 - MIN_LINE_DISTANCE)

            self.line1.setValue(new_l1)
            self.line2.setValue(new_l2)
            self.center_line.setValue((new_l1 + new_l2) / 2)

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
        InitializeImageplotItem(self.plotItem, yvalues=True,
                                y_label="x", y_units="pixel", 
                                x_label="λ", x_units="pixel") 

        num_wl_ticks = 8
        wl_ticks_pix = np.linspace(0, self.n_wl - 1, num_wl_ticks)
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
            xpos_wl, ypos_spatial_x = update_crosshair_from_mouse(self.plotItem, self.vLine, self.hLine, pos)
            if xpos_wl is not None and ypos_spatial_x is not None:
                self.last_valid_crosshair_pos = (xpos_wl, ypos_spatial_x)
                self.updateLabelFromCrosshair(xpos_wl, ypos_spatial_x)
                self.crosshairMoved.emit(xpos_wl, ypos_spatial_x, self.stokes_index)
        elif self.last_valid_crosshair_pos:
            self.updateLabelFromCrosshair(*self.last_valid_crosshair_pos)

    def updateLabelFromCrosshair(self, xpos_wl: float, ypos_spatial_x: float):
        index_wl = np.clip(int(np.round(xpos_wl)), 0, self.n_wl - 1)
        index_x = np.clip(int(np.round(ypos_spatial_x)), 0, self.n_x_pixel - 1)

        intensity = self.data[index_wl, index_x] 
        self.label.setText(f"λ={xpos_wl:.1f}, x={ypos_spatial_x:.2f}, z={intensity:.5f}", size='6pt') 

    def update_wavelength_range(self, min_val, max_val):
        SetPlotXlamRange(self.plotItem, self.wavelengths, min_val, max_val, axis='x') 

    def reset_wavelength_range(self):
        ResetPlotXlamRange(self.plotItem, self.wavelengths, axis='x') 

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
       
# --- Main Application Setup ---

def display_data(data: np.ndarray, title: str = 'Data Viewer'):
    """
    Main function to create and display the interactive data viewer.

    Args:
        data: Numpy array of shape (N_Stokes, N_wl, N_x) containing Stokes data.
        title: Window title.
    """  
    app = pg.mkQApp("Data viewer")
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1700, 800)
    win.setWindowTitle(title)

    # --- Data Validation ---
    data, STOKES_NAMES = ValidateData(data)
    
    # --- Widget Initialization ---
    control_widget = PlotControlWidget() # Create control widget first

    spectra: List[StokesSpectrumWindow] = []
    image_spectra: List[StokesSpectrumImageWindow] = []
    spatial: List[StokesSpatialWindow] = []
    docks: Dict[str, Dict[str, Dock]] = {"spectrum": {}, "spec_img": {}, "spatial": {}} # Store docks by type and name

     # --- Create Widgets and Docks in a Loop ---
    for i, name in enumerate(STOKES_NAMES):
         base_name = name # dock names
         stokes_data_y_wl_x = data[i, :, :] # Shape ( wl, x)

         # Create Widgets for this Stokes parameter
         initial_spec_img_data = data[i, :, :] 

         win_spectrum = StokesSpectrumWindow(stokes_data_y_wl_x, stokes_index=i, name=base_name)
         win_image_spectrum = StokesSpectrumImageWindow(initial_spec_img_data, stokes_index=i, name=base_name)
         win_spatial = StokesSpatialWindow(initial_spec_img_data, stokes_index=i, name=base_name)

         # Append to lists
         spectra.append(win_spectrum)
         image_spectra.append(win_image_spectrum)
         spatial.append(win_spatial)
         
         # Create Docks
         spectrum_dock = Dock(f"{base_name} spectrum", size=(350, 150))
         spectrum_image_dock = Dock(f"{base_name} spectrum image", size=(350, 150))
         spatial_dock = Dock(f"{base_name} spatial", size=(250, 150))

         # Add Widgets to Docks
         spectrum_dock.addWidget(win_spectrum)
         spectrum_image_dock.addWidget(win_image_spectrum)
         spatial_dock.addWidget(win_spatial)

         # Store Docks
         docks["spectrum"][base_name] = spectrum_dock
         docks["spec_img"][base_name] = spectrum_image_dock
         docks["spatial"][base_name] = spatial_dock

    # Update control widget with the created image and spectrum widgets
    control_widget.init_spectrum_limit_controls(spectra, image_spectra, spatial) # Now initialize UI for limits
       
    # --- Create Control and Data Docks ---
    control_dock = Dock("Control", size=(70,1000))
    data_dock = Dock("Data", size=(70,1000))
    
    # --- Arrange Docks in the DockArea ---
    
    for i, name in enumerate(STOKES_NAMES):
        base_name = name.split('/')[0]
        if name == STOKES_NAMES[0]: # first one always on the left
            area.addDock(docks["spec_img"][base_name], 'left')
        else:
            area.addDock(docks["spec_img"][base_name], 'bottom', docks["spec_img"][STOKES_NAMES[i-1].split('/')[0]])
    
    # Middle Column: Spectrum Images and Spectra
 
    for i, name in enumerate(STOKES_NAMES):
         base_name = name.split('/')[0]
         # Add spectrum and spatial
         area.addDock(docks["spectrum"][base_name], 'right', docks["spec_img"][base_name])
         area.addDock(docks["spatial"][base_name], 'right', docks["spectrum"][base_name])

    # Bottom Row: Average Spectrum
    area.addDock(data_dock, 'right')
    area.addDock(control_dock, 'above', data_dock)

    # Control widget
    control_dock.addWidget(control_widget)
    #data_dock.addWidget()
    
    # --- Connect Signals in a Loop ---

    for i in range(len(image_spectra)):        
        image_spectra[i].crosshairMoved.connect(control_widget.handle_crosshair_movement)
        image_spectra[i].avgRegionChanged.connect(control_widget.handle_v_avg_line_movement)
    pass
    
    # Connect the xlamRangeChanged signal 

    for spectrum_widget in spectra:
        control_widget.xlamRangeChanged.connect(spectrum_widget.update_wavelength_range)
        control_widget.resetXlamRangeRequested.connect(spectrum_widget.reset_wavelength_range)
    for image_spectrum_widget in image_spectra:
        control_widget.xlamRangeChanged.connect(image_spectrum_widget.update_wavelength_range)
        control_widget.resetXlamRangeRequested.connect(image_spectrum_widget.reset_wavelength_range)

    # --- Show Window and Run App ---
    win.show()
    try:
        # Use environment variable or default to dark style
        dark_stylesheet = qdarkstyle.load_stylesheet_from_environment(is_pyqtgraph=True)
        app.setStyleSheet(dark_stylesheet)
    except ImportError:
        print("qdarkstyle not found. Using default Qt style.")
    except Exception as e:
        print(f"Could not apply qdarkstyle: {e}")

    sys.exit(app.exec_()) # Use sys.exit for proper exit codes

if __name__ == '__main__':
    
    # Example data for display
    data = ExampleData() #N_Stokes, N_wl, N_x
    display_data(data, title='Test data')