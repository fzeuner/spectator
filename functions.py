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

def create_spectral_limit_controls(name: str, layout: QtWidgets.QVBoxLayout):
    """Label for spectral limits"""
    spectral_label = QtWidgets.QLabel(name)
    spectral_edit = QtWidgets.QLineEdit()
    spectral_edit.setPlaceholderText("Optional")
    
    layout.addWidget(spectral_label)
    layout.addWidget(spectral_edit)
    return(spectral_label, spectral_edit, layout)
    
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
    
def CreateYLimitLabel(name:str):
    """Label for spectrum y limits"""
    limit_label = QtWidgets.QLabel(name)
    limit_edit = QtWidgets.QLineEdit()
    limit_edit.setEnabled(False)

    layout = QtWidgets.QHBoxLayout()
    layout.addWidget(limit_label)
    layout.addWidget(limit_edit)
    return(limit_label, limit_edit, layout)


def SetPlotXlamRange(plot_widget: pg.PlotWidget, 
                     spectral: np.ndarray, 
                     xmin: Optional[float], 
                     xmax: Optional[float], 
                     axis: str = 'x'):
    """Sets the spectral range of a pyqtgraph PlotWidget."""
    xmin = None
    xmax = None
    
    if axis == 'x':
        x = 0
    elif axis == 'y':
        x = 1
    else:
        print(f"Error: Invalid axis '{axis}'. Must be 'x' or 'y'.")
        return

    if xmin is not None and xmax is not None:
        if xmin < xmax:
            plot_xmin, plot_xmax = xmin, xmax
        elif xmin == xmax:
            plot_xmin, plot_xmax = xmin - 0.5, xmax + 0.5 # Small range for single value
            print("Warning: spectral min is equal to spectral max.")
        else:
            plot_xmin, plot_xmax = xmax, xmin
            print("Warning: spectral min is greater than spectral max.")
            return
    elif xmin is not None:
        xmax = plot_widget.getViewBox().viewRange()[x][1]
        plot_xmin = xmin
    elif xmax is not None:
        xmin = plot_widget.getViewBox().viewRange()[x][0]
        plot_xmax = xmax
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

def ResetPlotXlamRange(plot_widget: pg.PlotWidget, spectral: np.ndarray, axis: str = 'x'):
    """Resets the x-axis range of a pyqtgraph PlotWidget to the full spectral range."""
    if len(spectral) > 0:
        if axis == 'x':
            plot_widget.setXRange(spectral.min(), spectral.max(), padding=0)
        elif axis == 'y':
            plot_widget.setYRange(spectral.min(), spectral.max(), padding=0)
        else:
            print(f"Error: Invalid axis '{axis}'. Must be 'x' or 'y'.")
            return
    else:
        print("Warning: Cannot reset spectral range, no spectral data available.")
        
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

     
