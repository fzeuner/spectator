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
    - numpy data cube ordered by N_STOKES, N_Y, N_WL, N_X 
    - wavelength data numpy 1D array

- TODO: 
    + add spatial x and spatial y profile
    + flexible N_STOKES
    + adding additional dimension to look at multiple scans
    + averaging in x and/or y
    + be able to fix histograms
    + coordinates are not working yet
    + large data - maybe using fastplotlib?
    + changing point sizes does not work: self.plot.getAxis('left').setStyle(tickFont = QFont().setPointSize(1))
    + multiple crosshairs
    + flexible data (only image spectra, non-stokes scans...)
"""

# import pyqtgraph.examples
# pyqtgraph.examples.run()

import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui
#from PyQt5.QtGui import QFont
import qdarkstyle
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from typing import List, Tuple, Dict, Optional, Any 

from getWidgetColors import getWidgetColors
try:
    import datasetst as dst
except ImportError:
    # Fallback dummy implementation
    class DummyPixelDict(dict):
        def __getitem__(self, key):
            return super().get(key, 0.0)
    
    class DummyDST:
        def __init__(self):
            self.pixel = DummyPixelDict({'sr': 0.024})
            self.line = 'sr'
            self.slitwidth = 0.05

    dst = DummyDST()


STOKES_NAMES = ["I", "Q/I", "U/I", "V/I"]
CROSSHAIR_COLORS = {'v': 'deeppink', 'h_image': 'dodgerblue', 'h_spectrum_image': 'orange'}

# --- Helper Functions ---

def AddLine(plotItem: pg.PlotItem, 
            color: str, 
            angle: float, 
            moveable: bool = False) -> pg.InfiniteLine:
    """Adds an InfiniteLine to a PlotItem."""
    line = pg.InfiniteLine(angle=angle, movable=moveable)
    line.setPen(color, width=2.5)
    plotItem.addItem(line, ignoreBounds=True)
    return(line)

def AddCrosshair(plotItem: pg.PlotItem, 
                 vcolor: str, 
                 hcolor: str) -> Tuple[pg.InfiniteLine, pg.InfiniteLine]:
    """Adds a crosshair (vertical and horizontal InfiniteLine) to a PlotItem."""
    vLine = AddLine(plotItem, vcolor, 90)
    hLine = AddLine(plotItem, hcolor, 0)
    return(vLine, hLine)

class BasePlotWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.graphics_widget.setBackground(getWidgetColors.BG_NORMAL)
        self.plotItem = self.graphics_widget.addPlot()
        self.layout.addWidget(self.graphics_widget)
        self.setLayout(self.layout)
    
def CreateYLimitLabel(name:str):
    """Label for spectrum y limits"""
    limit_label = QtWidgets.QLabel(name)
    limit_edit = QtWidgets.QLineEdit()
    limit_edit.setEnabled(False)

    layout = QtWidgets.QHBoxLayout()
    layout.addWidget(limit_label)
    layout.addWidget(limit_edit)
    return(limit_label, limit_edit, layout)

def CreateWlLimitLabel(name: str):
    """Label for xlam limits"""
    xlam_label = QtWidgets.QLabel(name)
    xlam_edit = QtWidgets.QLineEdit()
    xlam_edit.setPlaceholderText("Optional")
    layout = QtWidgets.QHBoxLayout()
    layout.addWidget(xlam_label)
    layout.addWidget(xlam_edit)
    return(xlam_label, xlam_edit, layout)

def CreateHistrogram(image_item: pg.ImageItem, 
                     layout: QtWidgets.QLayout) -> pg.HistogramLUTWidget:
    """Creates and configures a HistogramLUTWidget."""
    histogram = pg.HistogramLUTWidget()
    histogram.setImageItem(image_item)
    histogram.setBackground(getWidgetColors.BG_NORMAL) 
    layout.addWidget(histogram)
    return(histogram)

def SetPlotXlamRange(plot_widget: pg.PlotWidget, 
                     xlam: np.ndarray, 
                     min_val: Optional[float] = None, 
                     max_val: Optional[float] = None, 
                     axis: str = 'x'):
    """Sets the x-axis range of a pyqtgraph PlotWidget."""
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
            print("Warning: xlam min is equal to xlam max.")
        else:
            print("Warning: xlam min is greater than xlam max.")
            return
    elif min_val is not None:
        xmax = plot_widget.getViewBox().viewRange()[x][1]
        xmin = min_val
    elif max_val is not None:
        xmin = plot_widget.getViewBox().viewRange()[x][0]
        xmax = max_val
    else:
        # Reset to full range if no valid min or max provided
        if len(xlam) > 0:
            xmin, xmax = xlam.min(), xlam.max()
        else:
            print("Warning: Cannot set xlam range, no xlam data available.")
            return

    if xmin is not None and xmax is not None:
        if axis == 'x':
            plot_widget.setXRange(xmin, xmax, padding=0)
        elif axis == 'y':
            plot_widget.setYRange(xmin, xmax, padding=0)
        else:
            # This case should ideally be caught earlier
            print(f"Error: Invalid axis '{axis}'. Must be 'x' or 'y'.")

def ResetPlotXlamRange(plot_widget: pg.PlotWidget, xlam: np.ndarray, axis: str = 'x'):
    """Resets the x-axis range of a pyqtgraph PlotWidget to the full xlam range."""
    if len(xlam) > 0:
        if axis == 'x':
            plot_widget.setXRange(xlam.min(), xlam.max(), padding=0)
        elif axis == 'y':
            plot_widget.setYRange(xlam.min(), xlam.max(), padding=0)
        else:
            print(f"Error: Invalid axis '{axis}'. Must be 'x' or 'y'.")
    else:
        print("Warning: Cannot reset xlam range, no xlam data available.")
        
def update_crosshair_from_mouse(plot_item: pg.PlotItem, v_line: pg.InfiniteLine, h_line: pg.InfiniteLine, pos: QtCore.QPointF):
    """Updates the crosshair position based on the mouse position."""
    if plot_item.sceneBoundingRect().contains(pos):
        mousePoint = plot_item.vb.mapSceneToView(pos)
        xpos, ypos = mousePoint.x(), mousePoint.y()
        v_line.setPos(xpos)
        h_line.setPos(ypos)
        return xpos, ypos
    return None, None

def ExampleData() -> Tuple[np.ndarray, np.ndarray]:
    """
    Generates example Stokes spectropolarimetric data.
    Returns:
        xlam (np.ndarray): Wavelength axis of shape (N_WL,)
        data (np.ndarray): Stokes data cube of shape (N_STOKES, N_Y, N_WL, N_X)
    """

    print("Generating random test data...")

    # Define dimensions
    N_STOKES = 4
    N_WL = 250      # Wavelength points
    N_Y = 50        # Scan steps / spatial Y
    N_X = 150       # Slit positions / spatial X

    # Data shape: (STOKES, Y, WL, X)
    data = np.random.random(size=(N_STOKES, N_Y, N_WL, N_X)) * 5

    # Add bright Gaussian spot to Stokes I
    center_wl, center_y, center_x = N_WL // 2, N_Y // 2, N_X // 2
    width_wl, width_y, width_x = N_WL // 10, N_Y // 5, N_X // 8

    # 2D spatial Gaussian (Y, X)
    yy, xx = np.mgrid[:N_Y, :N_X]
    gauss_yx = np.exp(-(((yy - center_y) / width_y) ** 2 + ((xx - center_x) / width_x) ** 2) / 2)

    # Broadcast to (N_Y, 1, N_X) and add to I (index 0)
    data[0] += 10 * gauss_yx[:, np.newaxis, :]

    # 1D spectral Gaussian (WL)
    wl_axis = np.arange(N_WL)
    gauss_wl = np.exp(-((wl_axis - center_wl) / width_wl) ** 2 / 2)

    # Reshape for broadcast: (1, N_WL, 1) and multiply into Stokes I
    gauss_wl_3d = gauss_wl[np.newaxis, :, np.newaxis]
    data[0] *= gauss_wl_3d  # (N_Y, N_WL, N_X)

    # Add small Q feature in center region
    q_slice_y = slice(center_y - 5, center_y + 5)
    q_slice_x = slice(center_x - 5, center_x + 5)
    data[1, q_slice_y, center_wl, q_slice_x] += 3

    # Add sinusoidal pattern to V (Stokes index 3) varying with Y
    sin_y = np.sin(yy / N_Y * 2 * np.pi)
    sin_y = np.sin(np.linspace(0, 2 * np.pi, N_Y))[:, np.newaxis, np.newaxis]  # shape (50, 1, 1)
    data[3] = sin_y * 0.5  # shape (50, 250, 150) via broadcasting

    # Wavelength axis
    xlam = 6300 + np.arange(N_WL) * 0.02  # in Angstroms

    return xlam, data

def InitializeImageplotItem(item: pg.PlotItem, yvalues: bool = True, x_label: str = "x", y_label: str = "y", x_units: str = "arcsec", y_units: str = "arcsec"):
    """Initializes common properties for image PlotItems."""
    item.showAxes(True, showValues=(yvalues, True, False, False), size=15)
    item.getAxis('left').setWidth(42)
    item.getAxis('bottom').setHeight(15)
    item.getAxis('top').setHeight(15)
    item.setDefaultPadding(0.0) # plot without padding data range
    item.getAxis('top').enableAutoSIPrefix(False)
    item.getAxis('bottom').enableAutoSIPrefix(False)
    item.getAxis('left').enableAutoSIPrefix(False)
    item.setLabel("bottom", text=x_label, units=x_units)
    item.setLabel("left", text=y_label, units=y_units)
    item.invertY(False)

def InitializeSpectrumplotItem(plot: pg.PlotItem, y_label: str = "", x_label: str = "Wavelength", x_units: str = "Å"):
    """Initializes common properties for spectrum PlotItems."""
    plot.invertY(False) # orient y axis to run bottom-to-top
    plot.setDefaultPadding(0.0) # plot without padding data range
    plot.showAxes(True, showValues=(True, True, False, False), size=15)
    plot.getAxis('top').enableAutoSIPrefix(False)
    plot.getAxis('bottom').enableAutoSIPrefix(False)
    plot.getAxis('left').enableAutoSIPrefix(False)
    plot.getAxis('left').setWidth(40)
    plot.getAxis('left').setStyle(autoExpandTextSpace=True, hideOverlappingLabels=True)
    plot.setLabel("bottom", text=x_label, units=x_units)
    #plot.setLabel("left", text=y_label) # Units usually not needed for intensity

def ValidateData(xlam, data):
    expected_dims = 4
    if data.ndim != expected_dims or data.shape[0] != 4 or data.shape[2] != len(xlam):
        print(f"Error: Data shape mismatch. Expected ({4},  N_y, {len(xlam)}, N_x), got {data.shape}")
        # Optionally: Create placeholder data or raise an error
        n_wl_dummy, n_y_dummy, n_x_dummy = 50, 10, 10
        data = np.random.random(size=(4, n_y_dummy, n_wl_dummy, n_x_dummy))
        xlam = np.arange(n_wl_dummy)
        print("Using dummy data instead.")
        # return # Or exit
    return(xlam, data)

# --- Control Widget ---

class PlotControlWidget(QtWidgets.QWidget):
    crosshairMoved = QtCore.pyqtSignal(float, float, int) # x, y, source_stokes_index
    xlamRangeChanged = QtCore.pyqtSignal(object, object)
    resetXlamRangeRequested = QtCore.pyqtSignal()
    
    def __init__(self):
        super().__init__(None)
        self.layout = QtWidgets.QVBoxLayout(self)
        control_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(control_layout)

        # self.image_widgets = image_widgets
        # self.spectrum_image_widgets = spectrum_image_widgets
        
        self.image_widgets: List['StokesImageWindow'] = []
        self.spectrum_image_widgets: List['StokesSpectrumImageWindow'] = []
        self.spectra_widgets: List['StokesSpectrumWindow'] = []
        self.avg_spectrum_widget: Optional['InteractiveSpectrumWidget'] = None 

        self.sync_crosshair = False

        self.sync_button = QtWidgets.QPushButton("Synchronize Crosshair")
        self.sync_button.setCheckable(True)
        self.sync_button.clicked.connect(self.toggle_crosshair_sync)
        self.layout.addWidget(self.sync_button)

        self.spectrum_limit_controls: Dict[str, Dict[str, Any]] = {} # Dictionary to store controls for each spectrum
           
        # Add xlam range control
        self.xlam_min_label, self.xlam_min_edit, xlam_min_layout = CreateWlLimitLabel('min')
        self.xlam_min_edit.editingFinished.connect(self._xlam_range_changed)
        self.xlam_max_label, self.xlam_max_edit, xlam_max_layout = CreateWlLimitLabel('max')
        self.xlam_max_edit.editingFinished.connect(self._xlam_range_changed)
        # Add reset xlam range button
        self.reset_xlam_button = QtWidgets.QPushButton("Reset Xlam Range")
        self.layout.addWidget(self.reset_xlam_button)
        self.reset_xlam_button.clicked.connect(self.resetXlamRangeRequested.emit)
        
        xlam_group_box = QtWidgets.QGroupBox("Wavelength Axis Limits")
        limits_xlam_layout = QtWidgets.QVBoxLayout()
        
        limits_xlam_layout.addLayout(xlam_min_layout)
        limits_xlam_layout.addLayout(xlam_max_layout)
        xlam_group_box.setLayout(limits_xlam_layout)
        self.layout.addWidget(xlam_group_box)
        
    def _xlam_range_changed(self):
            min_text = self.xlam_min_edit.text()
            max_text = self.xlam_max_edit.text()
            min_val = None
            max_val = None
            try:
                if min_text:
                    min_val = float(min_text)
                if max_text:
                    max_val = float(max_text)
                if min_val is not None and max_val is not None:
                  if min_val >= max_val:
                    print("Warning: xlam min should be less than xlam max.")
                    return  # Do not emit signal if invalid range
                elif min_val is not None and max_val is not None and min_val == max_val:
                  print("Warning: xlam min is equal to xlam max.")
                # Decide if you want to emit or handle this differently
                  pass # For now, let's allow it and the other widget will handle it

                self.xlamRangeChanged.emit(min_val, max_val)
                
            except ValueError:
                # Handle invalid input (non-numeric)
                print("Warning: Invalid xlam range entered.")
                # Optionally clear the input fields or provide feedback to the user
        
    def _init_spectra_limit_controls(self, spectra_widgets: List['StokesSpectrumWindow'], spectrum_image_widgets: List['StokesSpectrumImageWindow']): #image spectra just dummy, not working yet
        """Initializes UI controls for managing spectrum Y-axis limits."""

        self.spectra_widgets = spectra_widgets  # List of StokesSpectrumWindow objects
        self.spectra_image_widgets = spectrum_image_widgets  # List of StokesSpectrumImageWindow objects
        for i, spectrum_widget in enumerate(self.spectra_widgets):

            group_box = self._create_spectrum_limits_controls(spectrum_widget.name, spectrum_widget, self.spectra_image_widgets[i])
            self.layout.addWidget(group_box)

    def _create_spectrum_limits_controls(self, stokes_name: str, 
                                         spectrum_widget: 'StokesSpectrumWindow', 
                                         spectrum_image_widget: 'StokesSpectrumImageWindow') -> QtWidgets.QGroupBox:
        """Creates the QGroupBox containing limit controls for one spectrum."""
        group_box = QtWidgets.QGroupBox(f"{stokes_name} Y-Axis Limits")
        limits_layout = QtWidgets.QVBoxLayout()

        fix_limits_checkbox = QtWidgets.QCheckBox("Fix Y-Axis Limits")
         
        min_limit_label, min_limit_edit, min_layout = CreateYLimitLabel("Min:")
        max_limit_label, max_limit_edit, max_layout = CreateYLimitLabel("Max:")

        limits_layout.addWidget(fix_limits_checkbox)
        limits_layout.addLayout(min_layout)
        limits_layout.addLayout(max_layout)
        group_box.setLayout(limits_layout)

        # Store references to the controls and the spectrum widget
        self.spectrum_limit_controls[stokes_name] = {
            "fix_checkbox": fix_limits_checkbox,
            "min_edit": min_limit_edit,
            "max_edit": max_limit_edit,
            "spectrum_widget": spectrum_widget,
            "spectrum_image_widget": spectrum_image_widget
            
        }

        # Get initial y-axis limits and set edits
        
        try:
            y_range = spectrum_widget.plot.viewRange()[1]
            if isinstance(y_range, (list, tuple)) and len(y_range) == 2:
                 y_min, y_max = y_range
                 min_limit_edit.setText(f"{y_min:.2f}")
                 max_limit_edit.setText(f"{y_max:.2f}")
            else: # Handle case where initial range might not be set
                 min_limit_edit.setText("N/A")
                 max_limit_edit.setText("N/A")
        except Exception: # Catch potential errors during initial range access
            y_min, y_max = 0, 0
            min_limit_edit.setText("Err")
            max_limit_edit.setText("Err")

        controls = self.spectrum_limit_controls.get(stokes_name)
        controls["min_edit"].setText(f"{y_min:.2f}")
        controls["max_edit"].setText(f"{y_max:.2f}")

               # Connect signals
        fix_limits_checkbox.stateChanged.connect(
                   lambda state, name=stokes_name: self.toggle_fix_spectrum_limits(name, state)
               )
        min_limit_edit.textChanged.connect(
                   lambda text, name=stokes_name: self.update_spectrum_limits(name)
               )
        max_limit_edit.textChanged.connect(
                   lambda text, name=stokes_name: self.update_spectrum_limits(name)
               )
        spectrum_widget.yRangeChanged.connect(
                   lambda limits, name=stokes_name: self._update_limit_edits_from_plot(name, limits)
               )
        return(group_box)

    def toggle_fix_spectrum_limits(self, stokes_name: str, state: QtCore.Qt.CheckState):
       #"""Enable/disable limit edits based on checkbox state."""
        fixed = state == QtCore.Qt.Checked
        controls = self.spectrum_limit_controls.get(stokes_name)
        if controls:
            controls["min_edit"].setEnabled(fixed)
            controls["max_edit"].setEnabled(fixed)
            self.update_spectrum_limits(stokes_name)

    def update_spectrum_limits(self, stokes_name):
        controls = self.spectrum_limit_controls.get(stokes_name)
        if controls and controls["fix_checkbox"].isChecked():
            try:
                min_val = float(controls["min_edit"].text())
                max_val = float(controls["max_edit"].text())
                spectrum_widget = controls["spectrum_widget"]
                if spectrum_widget is not None:
                    spectrum_widget.plotItem.setYRange(min_val, max_val, padding=0)
                    controls["spectrum_image_widget"].histogram.setLevels(min_val, max_val)

            except ValueError:
                pass
        # When not fixed, the y-axis will auto-scale

    def _update_limit_edits_from_plot(self, stokes_name, limits):
        controls = self.spectrum_limit_controls.get(stokes_name)
        if controls and not controls["fix_checkbox"].isChecked():
            min_val, max_val = limits
            controls["min_edit"].setText(f"{min_val:.2f}")
            controls["max_edit"].setText(f"{max_val:.2f}")

    def set_image_windows(self, image_widgets: List['StokesImageWindow']):
       """Set references to the image windows."""
       self.image_widgets = image_widgets

    def set_spectrum_image_windows(self, spectrum_image_widgets: List['StokesSpectrumImageWindow']):
       """Set references to the spectrum image windows."""
       self.spectrum_image_widgets = spectrum_image_widgets

    def set_spectrum_windows(self, spectra_widgets: List['StokesSpectrumWindow']):
       """Set references to the spectrum windows."""
       self.spectra_widgets = spectra_widgets

    def toggle_sync(self, state):
        """Toggle vLine synchronization across plot widgets."""
        self.sync_enabled = state == QtCore.Qt.Checked

    def toggle_crosshair_sync(self, checked):
        """Toggle crosshair synchronization between image windows."""
        self.sync_crosshair = checked
        if self.sync_crosshair:
            self.sync_button.setText("Unsynchronize Crosshair")
        else:
            self.sync_button.setText("Synchronize Crosshair")

    def emit_crosshair_moved(self, xpos, ypos, stokes_index):
        if self.sync_crosshair:
            self.crosshairMoved.emit(xpos, ypos, stokes_index)
            
# --- Data Display Widgets ---

class StokesImageWindow(BasePlotWidget):

    positionChanged = QtCore.pyqtSignal(float)
    crosshairMoved = QtCore.pyqtSignal(float, float, int) # Emit x and y position of crosshair and source index

    def __init__(self, xlam: np.ndarray, data: np.ndarray, stokes_index: int,
                  win_spectrum: 'StokesSpectrumWindow', win_image_spectrum: 'StokesSpectrumImageWindow',
                  control_widget: PlotControlWidget):
        super().__init__(None)

        pg.setConfigOptions(imageAxisOrder="row-major")
        
        self.data = data # Assumes data is already indexed for this stokes parameter -> [y, wl, x] after selection

        self.n_x_pixel, self.n_y_pixel = self.data[:, 0, :].shape[1], self.data[:, 0, :].shape[0]

        self.xlam = xlam
        self.wavelength_pos = 0
              
        # References
        self.win_spectrum = win_spectrum
        self.win_image_spectrum = win_image_spectrum
        self.control_widget = control_widget  # Store the control widget
        self.stokes_index = stokes_index
       
        InitializeImageplotItem(self.plotItem)
        
        # Ticks: relies on external 'dst' module

        x_ticks = np.arange(self.n_x_pixel, step=int(self.n_x_pixel / 8))  # eigtht ticks min
        y_ticks = np.arange(self.n_y_pixel, step=int(self.n_y_pixel / 3))  # three ticks min
 
        self.plotItem.getAxis('top').setTicks([[(x_axis_tick, '{:.1f}'.format(x_axis_tick * dst.pixel[dst.line])) for x_axis_tick in x_ticks]])       
        self.plotItem.getAxis('left').setTicks([[(y_axis_tick, '{:.1f}'.format(y_axis_tick * dst.slitwidth)) for y_axis_tick in y_ticks]])
       
        self.image_item = pg.ImageItem()
        self.plotItem.addItem(self.image_item)
        
        self.image_item.setImage(self.data[:, self.wavelength_pos, :])  # initial image
        
        # Label setup
        #item.getAxis('left').enableAutoSIPrefix(False) # y-axis  disable auto scaling of unit
        self.plotItem.setLabel("left", text="y", units="arcsec")

        # Add an InfiniteLine for crosshair functionality
        self.vLine, self.hLine = AddCrosshair(self.plotItem, CROSSHAIR_COLORS['v'], CROSSHAIR_COLORS['h_image'])

        # Create a HistogramLUTWidget for intensity scaling
        self.histogram = CreateHistrogram(self.image_item, self.layout)

        self.plotItem.scene().sigMouseMoved.connect(self.imageMouseMoved)
        self.plotItem.scene().sigMouseClicked.connect(self.mouseClicked)

        # Variables to track crosshair lock state
        self.crosshair_locked = False
        self.label = pg.LabelItem(justify='left')
        self.graphics_widget.addItem(self.label, row=5, col=0, colspan=1, rowspan=1)
        self.update_label()
          
    def update_label(self):

        xpos, ypos = self.vLine.value(), self.hLine.value()
        index_x = np.clip(int(np.round(xpos)), 0, self.n_x_pixel - 1)
        index_y = np.clip(int(np.round(ypos)), 0, self.n_y_pixel - 1)

        self.label.setText(
            # Find the closest index in xpos to the mouse
            "x={:.1f}".format(xpos * dst.pixel[dst.line]) +
            " y={:.1f} ".format(ypos * dst.slitwidth) +
            "z={:.5f}".format(self.data[index_y, self.wavelength_pos, index_x]),
            size='6pt')
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)

    def imageMouseMoved(self, pos):
        """Handle the mouse moved event over the plot area."""
        if not self.crosshair_locked:
            xpos, ypos = update_crosshair_from_mouse(self.plotItem, self.vLine, self.hLine, pos)
            if xpos is not None and ypos is not None:
                index_x = np.clip(int(np.round(xpos)), 0, self.n_x_pixel - 1)
                index_y = np.clip(int(np.round(ypos)), 0, self.n_y_pixel - 1)
                if 0 <= index_x < self.n_x_pixel and 0 <= index_y < self.n_y_pixel:
                    self.update_vline(xpos)
                    self.update_hline(ypos)
                    self.win_spectrum.update_plot_data(self.data[index_y, :, index_x])
                    self.win_image_spectrum.update_plot_data(self.data[index_y, :, :])
                    current_wavelength = self.xlam[self.wavelength_pos]
                    if hasattr(self.win_spectrum, 'vLine'):
                        self.win_spectrum.vLine.setPos(current_wavelength)
                    if hasattr(self.win_image_spectrum, 'hLine'):
                        self.win_image_spectrum.hLine.setPos(current_wavelength)
                    self.crosshairMoved.emit(xpos, ypos, self.stokes_index)
                    self.update_label()

    def handle_external_crosshair_move(self, xpos, ypos, source_stokes_index):
        """Handle crosshair movement from the other Stokes window."""
        if self.control_widget.sync_crosshair and source_stokes_index != self.stokes_index: # Avoid infinite loop
            self.update_crosshair(xpos, ypos)

    def handleExternalSpectrumImageMouseMove(self, pos):
        """Handle mouse move events from the spectrum image window."""
        if not self.crosshair_locked:
            if self.plotItem.sceneBoundingRect().contains(pos):
                mousePoint = self.plotItem.vb.mapSceneToView(pos)
                xpos = mousePoint.x()
                self.update_vline(xpos)

    def update_crosshair(self, xpos, ypos):
        """Update the crosshair position from an external signal."""
        if not self.crosshair_locked:
            self.update_vline(xpos)
            self.update_hline(ypos)
            # Find indices and update linked plots
            index_x = np.clip(int(np.round(xpos)), 0, self.n_x_pixel - 1)
            index_y = np.clip(int(np.round(ypos)), 0, self.n_y_pixel - 1)
            if 0 <= index_x < self.n_x_pixel and 0 <= index_y < self.n_y_pixel:
                self.win_spectrum.update_plot_data(self.data[index_y, :, index_x])
                self.win_image_spectrum.update_plot_data(self.data[index_y, :, :])
                self.update_label()

    def mouseClicked(self, event):
        if event.double():
            # On double-click, fix crosshair at current position
            mouse_point = self.plotItem.vb.mapSceneToView(event.scenePos())
            self.update_vline(mouse_point.x())
            self.update_hline(mouse_point.y())
            self.crosshair_locked = not self.crosshair_locked  # Toggle lock state
    def update_image(self):
        self.image_item.setImage(self.data[:, self.wavelength_pos, :])  #
        self.update_label()
    def update_vline(self, xpos):
        self.vLine.setPos(xpos)
    def update_hline(self, vpos):
        self.hLine.setPos(vpos)

class StokesSpectrumWindow(BasePlotWidget):
    yRangeChanged = QtCore.pyqtSignal(tuple)  # Emit (min, max)
    wavelengthChanged = QtCore.pyqtSignal(float) # Emit wavelength value

    def __init__(self, xlam, data, stokes_index: int, initial_y_idx=0, initial_x_idx=0):
        super().__init__(None)

        # Set up the main layout for this widget
        self.name = STOKES_NAMES[stokes_index] + " spectrum"

        self.xlam = xlam

        self.full_data = data # Store the full (y, wl, x) data

        self.current_y_idx = initial_y_idx
        self.current_x_idx = initial_x_idx
        self.plot_data = None # Initialize plot_data attribute

        # Ensure initial indices are valid
        if not (0 <= self.current_y_idx < self.full_data.shape[0] and 0 <= self.current_x_idx < self.full_data.shape[2]):
             print(f"Warning: Initial indices ({self.current_y_idx}, {self.current_x_idx}) out of bounds for data shape {self.full_data.shape}. Using (0, 0).")
             self.current_y_idx = 0
             self.current_x_idx = 0
             
        # Add movable v line (wavelength selector) - CREATE vLine EARLIER
        self.vLine = AddLine(self.plotItem,
                             CROSSHAIR_COLORS['h_spectrum_image'], # Orange line
                             90, moveable=True)

        # Label setup - Create label object
        self.label = pg.LabelItem(justify='left', size='6pt')
        self.graphics_widget.addItem(self.label, row=1, col=0) # Below plot
        # --- END Create plot items and lines FIRST ---        

        initial_plot_data = self.full_data[self.current_y_idx, :, self.current_x_idx]

        # --- Create plot items and lines FIRST ---
        self.plot_curve = pg.PlotDataItem() # Use PlotDataItem for easier updates - pen='c'
        self.plotItem.addItem(self.plot_curve)
        
        InitializeSpectrumplotItem(self.plotItem)
        
        self.plotItem.getViewBox().sigYRangeChanged.connect(self._emit_y_range_changed)
        self.n_wl = self.xlam.shape[0]

        # Connect the line's movement signal
        self.vLine.sigPositionChanged.connect(self._on_vline_moved)

        # Set initial plot data *after* vLine exists but *before* setting vLine position that depends on data/xlam
        self.update_plot_data(initial_plot_data) # This will call _update_label, which now works

        # Initialize vLine position and trigger initial signals/updates
        initial_wl = self.xlam[0] if len(self.xlam) > 0 else 0
        self.update_wavelength_line(initial_wl) # Set initial position, calls _update_label again
        
    def update_plot_data(self, new_data_1d):
        """Updates the plot with new 1D spectrum data."""
        self.plot_data = new_data_1d # Keep track of current 1D data
        self.plot_curve.setData(self.xlam, self.plot_data)

        self._emit_y_range_changed(None, self.plotItem.viewRange()[1]) # Emit new Y range
        self._update_label() # Update label as data/indices changed
        
    def _update_label(self):
        """Updates the coordinate label."""
        if not hasattr(self, 'vLine') or self.plot_data is None or self.xlam is None:
            self.label.setText("Initializing...")
            return

        wl_value = self.vLine.value()
        wl_idx = np.argmin(np.abs(self.xlam - wl_value)) if len(self.xlam) > 0 else -1

        intensity_value = np.nan
        if isinstance(self.plot_data, np.ndarray) and self.plot_data.ndim == 1 and 0 <= wl_idx < len(self.plot_data):
            intensity_value = self.plot_data[wl_idx]

        self.label.setText(f"λ={wl_value:.2f} Å, z={intensity_value:.3f}", size='6pt' )
            
    def _on_vline_moved(self):
        """Handles internal vLine movement and emits signal."""
        current_wl = self.vLine.value()
        self.wavelengthChanged.emit(current_wl)
        self._update_label() # Update label on move            
            
    def update_xlam_range(self, min_val: Optional[float], max_val: Optional[float]):
         """Updates the x-axis range of the spectrum plot"""
         SetPlotXlamRange(self.plotItem, self.xlam, min_val, max_val)
         xmin, xmax = self.plotItem.getViewBox().viewRange()[0]

    def reset_xlam_range(self):
         """Resets the x-axis range to the initial maximum range"""
         ResetPlotXlamRange(self.plotItem, self.xlam)

    def _emit_y_range_changed(self, axis, limits):
        #print(f"Type of limits in _emit_y_range_changed: {type(limits)}")
        self.yRangeChanged.emit(tuple(limits))
        
    @QtCore.pyqtSlot(float)
    def update_wavelength_line(self, wavelength: float):
        """Slot to update the vLine position from external signal."""
        if hasattr(self, 'vLine'):
            # Prevent feedback loop only if necessary (separate signals should handle it)
            # Check if value is actually different
            if not np.isclose(self.vLine.value(), wavelength):
                 self.vLine.setValue(wavelength)
                 self._update_label()
        else:
             print("Warning: update_wavelength_line called before vLine was initialized.")
            

class StokesSpectrumImageWindow(BasePlotWidget):
    def __init__(self, xlam: np.ndarray, data: np.ndarray, stokes_index: int):
        super().__init__(None)

        self.image_item = pg.ImageItem()
        self.plotItem.addItem(self.image_item)      

        self.histogram = CreateHistrogram(self.image_item, self.layout)

        self.xlam = xlam
        self.data = data # Assumed shape (wavelength, spatial_x)
        self.n_wl, self.n_x_pixel = self.data.shape
        
      # Set the rectangle to map pixel coordinates to the desired ranges
       # SetWavelengthAxis(self)
        x_min = 0
        x_max = self.n_x_pixel
        y_min = self.xlam[0] if len(self.xlam) > 0 else 0
        y_max = self.xlam[-1] if len(self.xlam) > 0 else self.n_wl

        self.image_item.setImage(self.data)
        self.image_item.setRect((x_min, y_min, x_max - x_min, y_max - y_min))
        InitializeImageplotItem(self.plotItem, yvalues=False, # Show wavelength values on left
                                y_label="Wavelength", y_units="Å",
                                x_label="x", x_units="arcsec")

        # X-axis scaling and label (moved to top)
        x_pixel_scale = dst.pixel.get(dst.line, 1.0)
        num_x_ticks = 8
        x_ticks_pix = np.linspace(0, self.n_x_pixel - 1, num_x_ticks)
        x_ticks = [(tick, f'{tick * x_pixel_scale:.1f}') for tick in x_ticks_pix]

        self.plotItem.getAxis('top').setTicks([x_ticks])          

        # Label setup
        self.label = pg.LabelItem(justify='left', size='6pt')
        self.graphics_widget.addItem(self.label, row=1, col=0) # Below plot
       
        # Crosshair
        self.vLine, self.hLine = AddCrosshair(self.plotItem, CROSSHAIR_COLORS['v'], CROSSHAIR_COLORS['h_spectrum_image'])

        # Connect mouse move event to update crosshair and label
        self.plotItem.scene().sigMouseMoved.connect(self.updateCrosshairAndLabel)
        self.plotItem.scene().sigMouseClicked.connect(self.mouseClicked) # For fixing crosshair
        self.last_valid_crosshair_pos = None
        self.crosshair_locked = False
        self.updateLabelFromCrosshair(0, 0) # initialize
        
    def mouseClicked(self, event):
        """Toggles crosshair lock on double-click."""
        if event.double():
            mouse_point = self.plotItem.vb.mapSceneToView(event.scenePos())
            if not self.crosshair_locked: # Fix at current position
                self.vLine.setPos(mouse_point.x())
                self.hLine.setPos(mouse_point.y())
                self.last_valid_crosshair_pos = (mouse_point.x(), mouse_point.y())
                self.updateLabelFromCrosshair(mouse_point.x(), mouse_point.y())
            self.crosshair_locked = not self.crosshair_locked
            
    def updateCrosshairAndLabel(self, pos: QtCore.QPointF):
        """Updates crosshair and label on mouse move (if not locked)."""
        if not self.crosshair_locked:
            xpos, ypos = update_crosshair_from_mouse(self.plotItem, self.vLine, self.hLine, pos)
            if xpos is not None and ypos is not None:
                self.last_valid_crosshair_pos = (xpos, ypos)
                self.updateLabelFromCrosshair(xpos, ypos)
        # Option: Update label from last known pos if mouse leaves?
        # elif self.last_valid_crosshair_pos:
        #     self.updateLabelFromCrosshair(*self.last_valid_crosshair_pos)

    # If locked, ensure label reflects the fixed position
        elif self.last_valid_crosshair_pos:
         self.updateLabelFromCrosshair(*self.last_valid_crosshair_pos)

    def updateLabelFromCrosshair(self, xpos: float, ypos: float):
         """Updates the label text based on crosshair coordinates."""
         # Map plot coords (pixel indices) to data indices and values
         index_x = np.clip(int(np.round(xpos)), 0, self.n_x_pixel - 1)
         index_wl = np.clip(int(np.round(ypos)), 0, self.n_wl - 1) # Y axis is wavelength index

         # Get display values
         x_coord = index_x * dst.pixel.get(dst.line, 1.0) # Spatial coordinate
         
         wavelength = ypos #self.xlam[index_wl] # scaling is correct!
         intensity = self.data[index_wl, index_x]

         self.label.setText(f"x={x_coord:.1f}\", λ={wavelength:.2f} Å, z={intensity:.3f}", size='6pt')

    def update_plot_data(self, new_data: np.ndarray):
        """Updates the image data."""
        if len(new_data.shape) == 2 and new_data.shape[0] == self.n_wl and new_data.shape[1] == self.n_x_pixel:
            self.data = new_data
            self.image_item.setImage(self.data)
            # Reset label/crosshair? Optional.
            self.last_valid_crosshair_pos = None # Reset last known position
            if not self.crosshair_locked:
                 self.vLine.setPos(0) # Reset crosshair
                 self.hLine.setPos(0)
                 self.updateLabelFromCrosshair(0,0) # Update label to origin
            # else keep locked crosshair and update label based on it
            elif self.last_valid_crosshair_pos:
                self.updateLabelFromCrosshair(*self.last_valid_crosshair_pos)

        else:
             print(f"Shape mismatch: Cannot update spectrum image. Expected ({self.n_wl},{self.n_x_pixel}), got {new_data.shape}")

    def update_xlam_range(self, min_val: Optional[float], max_val: Optional[float]):
         """Updates the x-axis range of the spectrum plot"""

         SetPlotXlamRange(self.plotItem, self.xlam, min_val, max_val, axis='y')
         xmin, xmax = self.plotItem.getViewBox().viewRange()[0]

    def reset_xlam_range(self):
         """Resets the x-axis range to the initial maximum range"""
         ResetPlotXlamRange(self.plotItem, self.xlam, axis='y')    

    def updateExternalVLine(self, xpos: float):
        """Updates the vertical line from external signals (e.g., main image window)."""
        if not self.crosshair_locked:
            self.vLine.setPos(xpos)
            current_y = self.hLine.value()
            self.last_valid_crosshair_pos = (xpos, current_y)
            self.updateLabelFromCrosshair(xpos, current_y)
            
# --- Interactive Average Spectrum Widget ---

class InteractiveSpectrumWidget(QtWidgets.QWidget):
    def __init__(self, xlam: np.ndarray, data: np.ndarray,
                 image_windows: List[StokesImageWindow]):
        super().__init__(None)
        layout = QtWidgets.QVBoxLayout(self)
        self.plot_widget = pg.PlotWidget() # Use PlotWidget directly
        self.plot_widget.setBackground(getWidgetColors.BG_NORMAL)
        layout.addWidget(self.plot_widget)
        
        self.xlam = xlam
        self._initial_xlam_min = xlam.min() if len(xlam) > 0 else None
        self._initial_xlam_max = xlam.max() if len(xlam) > 0 else None
        
        # Calculate average I spectrum (average over stokes=0, y, x)
        # Original: np.mean(data, axis=(1, 3)) -> assumes (stokes, scan, wl, spatial_y)
        # Let's assume input `data` is the full 4D [stokes, y, wl, x]
        if data.ndim == 4 and data.shape[0] > 0:
             self.avg_data = np.nanmean(data[0, :, :, :], axis=(0, 2)) # nanmean of I over y and x
        elif data.ndim == 3: # If only one stokes param passed?
             self.avg_data = np.nanmean(data[:, :, :], axis=(0, 2))
        else:
             print("Warning: Cannot calculate average spectrum, unexpected data shape.")
             self.avg_data = np.zeros_like(xlam) # Placeholder
        
      #  self.data = np.nanmean(data, axis=(1, 3))  # Average over scan and spatial slit
        self.plot_item = self.plot_widget.plot(xlam, self.avg_data)
        InitializeSpectrumplotItem(self.plot_widget.getPlotItem(), 
                                   y_label="Avg Intensity", 
                                   x_label="Wavelength") # Apply styling
        self.image_windows = image_windows

        # Add movable v line
        self.vLine = AddLine(self.plot_widget.getPlotItem(), 
                             CROSSHAIR_COLORS['v'], 
                             90, moveable=True)
        self.vLine.sigPositionChanged.connect(self.vLine_moved)
        self.setLayout(layout)
        # Set initial position reasonably
        if len(xlam) > 0:
            initial_pos = xlam[0]
            self.vLine.setPos(initial_pos)
            self.vLine_moved() # Trigger initial update       

    def vLine_moved(self):
        """Updates the displayed wavelength slice in all image windows."""
        xpos = self.vLine.value()
        index = np.abs(self.xlam - xpos).argmin()
        #print(f"InteractiveSpectrum vLine moved to {xpos:.2f} Å, index {index}")
        for win in self.image_windows:
            win.wavelength_pos = index
            win.update_image()
            
    def update_xlam_range(self, min_val: Optional[float], 
                                max_val: Optional[float]):
        """Updates the x-axis range of the spectrum plot and moves vLine."""
        SetPlotXlamRange(self.plot_widget, self.xlam, min_val, max_val)
        xmin, xmax = self.plot_widget.getViewBox().viewRange()[0]
        current_vline_pos = self.vLine.value()
        if current_vline_pos < xmin:
            self.vLine.setPos(xmin)
            self.vLine_moved()
        elif current_vline_pos > xmax:
            self.vLine.setPos(xmax)
            self.vLine_moved()
        elif xmin <= current_vline_pos <= xmax:
            pass # vLine is within the new range

    def reset_xlam_range(self):
        """Resets the x-axis range to the initial maximum range and moves vLine."""
        ResetPlotXlamRange(self.plot_widget, self.xlam)
        if self._initial_xlam_min is not None:
            self.vLine.setPos(self._initial_xlam_min)
            self.vLine_moved()
        elif len(self.xlam) > 0:
            self.vLine.setPos(self.xlam.min())
            self.vLine_moved()

# --- Main Application Setup ---

def display_dkist_scan_data(data: np.ndarray, xlam: np.ndarray, title: str = 'DKIST Data Viewer'):
    """
    Main function to create and display the interactive DKIST data viewer.

    Args:
        data: Numpy array of shape (4, N_y, N_wl, N_x) containing Stokes data.
        xlam: Numpy array of shape (N_wl,) containing wavelengths.
        title: Window title.
    """  
    app = pg.mkQApp("DKIST Data")
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1600, 900)
    win.setWindowTitle(title)

    # --- Data Validation ---
    xlam, data = ValidateData(xlam, data)
    
    # --- Widget Initialization ---
    control_widget = PlotControlWidget() # Create control widget first

    images: List[StokesImageWindow] = []
    spectra: List[StokesSpectrumWindow] = []
    image_spectra: List[StokesSpectrumImageWindow] = []
    docks: Dict[str, Dict[str, Dock]] = {"scan": {}, "spectrum": {}, "spec_img": {}} # Store docks by type and name

     # --- Create Widgets and Docks in a Loop ---
    for i, name in enumerate(STOKES_NAMES):
         base_name = name.split('/')[0] # Use "I", "Q", "U", "V" for dock names
         stokes_data_y_wl_x = data[i, :, :, :] # Shape (y, wl, x)

         # Create Widgets for this Stokes parameter
         initial_spec_img_data = data[i, 0, :, :] 

         win_spectrum = StokesSpectrumWindow(xlam, stokes_data_y_wl_x, stokes_index=i)
         win_image_spectrum = StokesSpectrumImageWindow(xlam, initial_spec_img_data, stokes_index=i)
         win_scan = StokesImageWindow(xlam, stokes_data_y_wl_x, i, win_spectrum, win_image_spectrum, control_widget)

         # Append to lists
         images.append(win_scan)
         spectra.append(win_spectrum)
         image_spectra.append(win_image_spectrum)

         # Create Docks
         scan_dock = Dock(f"{base_name} scan", size=(350, 350)) # Slightly larger default
         spectrum_dock = Dock(f"{base_name} spectrum", size=(350, 150))
         spectrum_image_dock = Dock(f"{base_name} Spectrum image", size=(350, 150))

         # Add Widgets to Docks
         scan_dock.addWidget(win_scan)
         spectrum_dock.addWidget(win_spectrum)
         spectrum_image_dock.addWidget(win_image_spectrum)

         # Store Docks
         docks["scan"][base_name] = scan_dock
         docks["spectrum"][base_name] = spectrum_dock
         docks["spec_img"][base_name] = spectrum_image_dock

    # Update control widget with the created image and spectrum widgets
    control_widget.set_image_windows(images)
    control_widget.set_spectrum_windows(spectra)
    control_widget.set_spectrum_image_windows(image_spectra)
    control_widget._init_spectra_limit_controls(spectra, image_spectra) # Now initialize UI for limits # image spectra for now just dummy, no effect!
    
    # --- Create Average Spectrum Widget ---
    avg_spectrum_widget = InteractiveSpectrumWidget(xlam, data, images) # Pass full data
    avg_spectrum_dock = Dock("Average I spectrum", size=(1000, 40)) # Adjust size as needed
    avg_spectrum_dock.addWidget(avg_spectrum_widget)
    
    # --- Create Control and Data Docks ---
    control_dock = Dock("Control", size=(70,1000))
    data_dock = Dock("Data", size=(70,1000))
    
    # --- Arrange Docks in the DockArea ---
    # Left Column: Scan Images (I, Q, U, V)
    
    for i, name in enumerate(STOKES_NAMES):
        base_name = name.split('/')[0]
        if name == STOKES_NAMES[0]: # first one always on the left
            area.addDock(docks["scan"][base_name], 'left')
        else:
            area.addDock(docks["scan"][base_name], 'bottom', docks["scan"][STOKES_NAMES[i-1].split('/')[0]])
    
    # Middle Column: Spectrum Images and Spectra
 
    for i, name in enumerate(STOKES_NAMES):
         base_name = name.split('/')[0]
         # Add spectrum image relative to scan
         area.addDock(docks["spec_img"][base_name], 'right', docks["scan"][base_name])
         # Add spectrum above spectrum image
         area.addDock(docks["spectrum"][base_name], 'above', docks["spec_img"][base_name])

    # Bottom Row: Average Spectrum
    area.addDock(avg_spectrum_dock, 'bottom')
    area.addDock(data_dock, 'right')
    area.addDock(control_dock, 'above', data_dock)

    # Control widget
    control_dock.addWidget(control_widget)
    #data_dock.addWidget()
    
    # --- Connect Signals in a Loop ---
    for i in range(len(images)):        
        images[i].crosshairMoved.connect(control_widget.emit_crosshair_moved)
        control_widget.crosshairMoved.connect(images[i].handle_external_crosshair_move)
        images[i].crosshairMoved.connect(image_spectra[i].updateExternalVLine)
     
    # To synchronize-connect vLine movement from SpectrumImage back to Scan
    # image_spectra[i].plotItem.scene().sigMouseMoved.connect(lambda pos: images[i].handleExternalSpectrumImageMouseMove(pos))    
        pass
    
    # Connect the xlamRangeChanged signal to the update method in InteractiveSpectrumWidget
    control_widget.xlamRangeChanged.connect(avg_spectrum_widget.update_xlam_range)
    for spectrum_widget in spectra:
        control_widget.xlamRangeChanged.connect(spectrum_widget.update_xlam_range)
        control_widget.resetXlamRangeRequested.connect(spectrum_widget.reset_xlam_range)
    for image_spectrum_widget in image_spectra:
        control_widget.xlamRangeChanged.connect(image_spectrum_widget.update_xlam_range)
        control_widget.resetXlamRangeRequested.connect(image_spectrum_widget.reset_xlam_range)

    # Connect the resetXlamRangeRequested signal to the reset method    # image_spectra[1].plotItem.scene().sigMouseMoved.connect(lambda pos: images[1].handleExternalSpectrumImageMouseMove(pos))
    # image_spectra[2].plotItem.scene().sigMouseMoved.connect(lambda pos: images[2].handleExternalSpectrumImageMouseMove(pos))
    # image_spectra[3].plotItem.scene().sigMouseMoved.connect(lambda pos: images[3].handleExternalSpectrumImageMouseMove(pos))
    control_widget.resetXlamRangeRequested.connect(avg_spectrum_widget.reset_xlam_range)

    # -

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
    xlam, data = ExampleData()
    display_dkist_scan_data(data, xlam, title='Test data')