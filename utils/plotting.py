"""
Plotting utilities for the spectral data viewer.

This module contains helper functions for creating and configuring PyQtGraph
plot items, crosshairs, histograms, and other plotting elements.
"""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from typing import Tuple, Optional

from .constants import DEFAULT_LINE_WIDTH, DEFAULT_FONT_SIZE, DEFAULT_LABEL_SIZE, ColorSchemes
from .colors import getWidgetColors


def add_line(plot_item: pg.PlotItem, 
             color: str, 
             angle: float, 
             moveable: bool = False, 
             pos: float = 0, 
             style=QtCore.Qt.SolidLine) -> pg.InfiniteLine:
    """
    Add an InfiniteLine to a PlotItem.
    
    Args:
        plot_item: PyQtGraph PlotItem to add line to
        color: Line color
        angle: Line angle (0=horizontal, 90=vertical)
        moveable: Whether line can be moved by user
        pos: Initial position
        style: Line style (Qt pen style)
        
    Returns:
        The created InfiniteLine object
    """
    line = pg.InfiniteLine(pos=pos, angle=angle, movable=moveable)
    line.setPen(color, width=DEFAULT_LINE_WIDTH, style=style)
    plot_item.addItem(line, ignoreBounds=True)
    return line


def add_crosshair(plot_item: pg.PlotItem, 
                  v_color: str, 
                  h_color: str, 
                  style=QtCore.Qt.DashLine) -> Tuple[pg.InfiniteLine, pg.InfiniteLine]:
    """
    Add a crosshair (vertical and horizontal InfiniteLine) to a PlotItem.
    
    Args:
        plot_item: PyQtGraph PlotItem to add crosshair to
        v_color: Vertical line color
        h_color: Horizontal line color
        style: Line style for both lines
        
    Returns:
        Tuple of (vertical_line, horizontal_line)
    """
    v_line = add_line(plot_item, v_color, 90, style=style)
    h_line = add_line(plot_item, h_color, 0, style=style)
    return v_line, h_line


class ScientificAxisItem(pg.AxisItem):
    """Custom axis item that uses scientific notation for very small/large values."""
    
    def tickStrings(self, values, scale, spacing):
        """Override tick string formatting to use scientific notation when appropriate."""
        strings = []
        for v in values:
            if v == 0:
                strings.append('0')
            else:
                abs_val = abs(v)
                # Use scientific notation for very small or very large values
                if abs_val < 1e-3 or abs_val >= 1e4:
                    strings.append(f'{v:.1e}')
                elif abs_val >= 1:
                    strings.append(f'{v:.3g}')
                else:
                    # Format small decimals nicely
                    formatted = f'{v:.4f}'.rstrip('0').rstrip('.')
                    strings.append(formatted)
        return strings


def create_histogram_with_scaling(image_item: pg.ImageItem, 
                                  layout: QtWidgets.QLayout,
                                  scale_info: dict = None,
                                  stokes_index: int = None) -> tuple:
    """Creates a histogram with automatic data scaling for better display of scientific values.
    
    Returns:
        tuple: (histogram_widget, scale_label) where scale_label shows the scaling factor
    """
    import numpy as np
    
    # Create a container widget for histogram + scale label
    container = QtWidgets.QWidget()
    container_layout = QtWidgets.QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.setSpacing(2)
    
    # Create the histogram
    histogram = pg.HistogramLUTWidget()
    histogram.setImageItem(image_item)
    histogram.setBackground(getWidgetColors().get('background', '#19232D'))
    histogram.setFixedWidth(60)
    
    # Create a label for the scale factor
    scale_label = QtWidgets.QLabel("1")  # Start with "1" instead of empty string
    colors = getWidgetColors()
    scale_label.setStyleSheet(f"""
        QLabel {{
            color: {colors.get('foreground', '#FFFFFF')};
            background-color: {colors.get('background', '#19232D')};
            font-size: {DEFAULT_LABEL_SIZE};
            font-weight: normal;
            padding: 2px;
            border-radius: 1px;
        }}
    """)
    scale_label.setAlignment(QtCore.Qt.AlignCenter)
    scale_label.setMaximumHeight(20)
    scale_label.setMinimumHeight(20)
    
    # Add widgets to container
    container_layout.addWidget(scale_label)
    container_layout.addWidget(histogram)
    
    # Function to update scale label based on data model scaling info
    def update_scale_label():
        try:
            # First try to use provided scale_info
            current_scale_info = scale_info
            
            # If no scale_info provided, try to get it from global data manager
            if not current_scale_info:
                try:
                    from controllers.app_controller import data_manager
                    current_scale_info = data_manager.get_current_scale_info()
                except (ImportError, AttributeError):
                    current_scale_info = None
            
            # Default to "1" - this ensures we always show something
            label_text = "1"
            
            # Use scaling info from data model if available
            if current_scale_info and isinstance(current_scale_info, dict):
                labels = current_scale_info.get('labels', {})
                factors = current_scale_info.get('factors', {})
                
                # Use state-specific scaling if stokes_index is provided
                if stokes_index is not None:
                    # Try to get the specific label for this state
                    if labels and stokes_index in labels and labels[stokes_index]:
                        # Only use the label if it's not empty
                        label_text = labels[stokes_index]
                    elif factors and stokes_index in factors:
                        # Create label from factor for this specific state
                        factor = factors[stokes_index]
                        if factor == 1.0:
                            label_text = "1"
                        else:
                            # Convert factor to scientific notation label
                            exponent = int(np.log10(abs(factor))) if factor != 0 else 0
                            if exponent != 0:
                                label_text = f"10^{exponent}"
                            else:
                                label_text = "1"
                    # If no scaling info for this state, label_text remains "1"
                else:
                    # No stokes_index provided, use first available or default behavior
                    if labels:
                        # Get the first available non-empty scale label
                        label_text = next((label for label in labels.values() if label), "1")
                    elif factors:
                        # If we have factors but no labels, create a simple label
                        first_factor = next(iter(factors.values()), 1.0)
                        if first_factor == 1.0:
                            label_text = "1"
                        else:
                            # Convert factor to scientific notation label
                            exponent = int(np.log10(abs(first_factor))) if first_factor != 0 else 0
                            if exponent != 0:
                                label_text = f"10^{exponent}"
                            else:
                                label_text = "1"
 
            scale_label.setText(label_text)
                
        except Exception as e:
            # Always default to "1" on any error
            scale_label.setText("e")
    
    # Update scale label initially
    update_scale_label()
    
    # Connect to image item signals to update scale label when data changes
    if hasattr(image_item, 'sigImageChanged'):
        image_item.sigImageChanged.connect(update_scale_label)
    
    # Store update function for later use
    container.update_scale_label = update_scale_label
    
    layout.addWidget(container)
    
    return histogram, scale_label

def create_histogram(image_item: pg.ImageItem, 
                     layout: QtWidgets.QLayout,
                     scale_info: dict = None,
                     stokes_index: int = None) -> pg.HistogramLUTWidget:
    """Creates and configures a HistogramLUTWidget with automatic scaling display."""
    histogram, scale_label = create_histogram_with_scaling(image_item, layout, scale_info, stokes_index)
    return histogram

def initialize_image_plot_item(item: pg.PlotItem, 
                               y_values: bool = True,
                               x_label: str = "x",
                               y_label: str = "y", 
                               x_units: str = "pixel",
                               y_units: str = "pixel"):
    """
    Initialize common properties for image PlotItems.
    
    Args:
        item: PlotItem to initialize
        y_values: Whether to show y-axis values
        x_label: X-axis label
        y_label: Y-axis label
        x_units: X-axis units
        y_units: Y-axis units
    """
    # Configure axis properties
    for axis_name in ['left', 'bottom', 'top']:
        axis = item.getAxis(axis_name)
        axis.enableAutoSIPrefix(False)  # Disable auto SI prefix for all relevant axes
        if axis_name == 'left':
            axis.setWidth(42)
        else:  # 'bottom' and 'top'
            axis.setHeight(15)

    item.setLabel("bottom", text=x_label, units=x_units)
    item.setLabel("left", text=y_label, units=y_units)

    # Show axes with tick values on left and top only
    item.showAxes(True, showValues=(y_values, True, False, False), size=15)
    item.setDefaultPadding(0.0)
    item.invertY(False)


def initialize_spectrum_plot_item(plot: pg.PlotItem, 
                                  y_label: str = "", 
                                  x_label: str = "λ", 
                                  x_units: str = "pixel",
                                  y_units: str = ""):
    """
    Initialize common properties for spectrum PlotItems.
    
    Args:
        plot: PlotItem to initialize
        y_label: Y-axis label
        x_label: X-axis label  
        x_units: X-axis units
        y_units: Y-axis units
    """
    # Configure axis properties
    for axis_name in ['left', 'bottom', 'top']:
        axis = plot.getAxis(axis_name)
        axis.enableAutoSIPrefix(False)  # Disable auto SI prefix for all relevant axes
        if axis_name == 'left':
            axis.setWidth(42)
        else:  # 'bottom' and 'top'
            axis.setHeight(15)

    plot.setLabel("bottom", text=x_label, units=x_units)
    plot.setLabel("left", text=y_label, units=y_units)

    # Show axes with tick values on left and top only
    plot.showAxes(True, showValues=(True, True, False, False), size=15)
    plot.setDefaultPadding(0.0)


def set_plot_wavelength_range(plot_widget: pg.PlotWidget, 
                             wavelength: np.ndarray, 
                             min_val: Optional[float] = None, 
                             max_val: Optional[float] = None, 
                             axis: str = 'x'):
    """
    Set the wavelength range of a PyQtGraph PlotWidget.
    
    Args:
        plot_widget: PlotWidget to modify
        wavelength: Wavelength array
        min_val: Minimum wavelength value (None for auto)
        max_val: Maximum wavelength value (None for auto)
        axis: Axis to modify ('x' or 'y')
    """
    if min_val is None:
        min_val = wavelength.min()
    if max_val is None:
        max_val = wavelength.max()
    
    # Ensure valid range
    if min_val >= max_val:
        min_val = wavelength.min()
        max_val = wavelength.max()
    
    # Apply range based on axis
    if axis.lower() == 'x':
        plot_widget.setXRange(min_val, max_val, padding=0.02)
    elif axis.lower() == 'y':
        plot_widget.setYRange(min_val, max_val, padding=0.02)


def reset_plot_wavelength_range(plot_widget: pg.PlotWidget, 
                               wavelength: np.ndarray, 
                               axis: str = 'x'):
    """
    Reset the wavelength range of a PyQtGraph PlotWidget to full range.
    
    Args:
        plot_widget: PlotWidget to reset
        wavelength: Wavelength array
        axis: Axis to reset ('x' or 'y')
    """
    min_val = wavelength.min()
    max_val = wavelength.max()
    
    if axis.lower() == 'x':
        plot_widget.setXRange(min_val, max_val, padding=0.02)
    elif axis.lower() == 'y':
        plot_widget.setYRange(min_val, max_val, padding=0.02)


def update_crosshair_from_mouse(plot_item: pg.PlotItem, 
                                v_line: pg.InfiniteLine, 
                                h_line: pg.InfiniteLine, 
                                pos: QtCore.QPointF):
    """
    Update crosshair position based on mouse position.
    
    Args:
        plot_item: PlotItem containing the crosshair
        v_line: Vertical crosshair line
        h_line: Horizontal crosshair line
        pos: Mouse position in plot coordinates
        
    Returns:
        Tuple of (x_pos, y_pos) if valid, None otherwise
    """
    if plot_item.sceneBoundingRect().contains(pos):
        mouse_point = plot_item.vb.mapSceneToView(pos)
        v_line.setPos(mouse_point.x())
        h_line.setPos(mouse_point.y())
        return mouse_point.x(), mouse_point.y()
    return None


def create_wavelength_limit_controls(name: str) -> Tuple[QtWidgets.QLabel, QtWidgets.QLineEdit, QtWidgets.QHBoxLayout]:
    """
    Create wavelength limit control widgets.
    
    Args:
        name: Label text for the control
        
    Returns:
        Tuple of (label, line_edit, layout)
    """
    label = QtWidgets.QLabel(name)
    line_edit = QtWidgets.QLineEdit()
    line_edit.setPlaceholderText("Optional")
    
    layout = QtWidgets.QHBoxLayout()
    layout.addWidget(label)
    layout.addWidget(line_edit)
    
    return label, line_edit, layout

def CreateWlLimitLabel(name: str):
    """Label for wavelength limits"""
    wavelength_label = QtWidgets.QLabel(name)
    wavelength_edit = QtWidgets.QLineEdit()
    wavelength_edit.setPlaceholderText("Optional")
    layout = QtWidgets.QHBoxLayout()
    layout.addWidget(wavelength_label)
    layout.addWidget(wavelength_edit)
    return(wavelength_label, wavelength_edit, layout)

def create_y_limit_controls(name: str) -> Tuple[QtWidgets.QLabel, QtWidgets.QLineEdit, QtWidgets.QHBoxLayout]:
    """
    Create Y-axis limit control widgets.
    
    Args:
        name: Label text for the control
        
    Returns:
        Tuple of (label, line_edit, layout)
    """
    label = QtWidgets.QLabel(name)
    line_edit = QtWidgets.QLineEdit()
    line_edit.setPlaceholderText("Auto")
    
    layout = QtWidgets.QHBoxLayout()
    layout.addWidget(label)
    layout.addWidget(line_edit)
    
    return label, line_edit, layout

def apply_dark_theme(plot_widget: pg.PlotWidget):
    """
    Apply dark theme styling to a plot widget.
    
    Args:
        plot_widget: PlotWidget to style
    """
    plot_widget.setBackground('k')  # Black background
    
    # Style axes
    for axis in ['left', 'bottom', 'right', 'top']:
        ax = plot_widget.getAxis(axis)
        ax.setPen('w')  # White axis lines
        ax.setTextPen('w')  # White text


def apply_light_theme(plot_widget: pg.PlotWidget):
    """
    Apply light theme styling to a plot widget.
    
    Args:
        plot_widget: PlotWidget to style
    """
    plot_widget.setBackground('w')  # White background
    
    # Style axes
    for axis in ['left', 'bottom', 'right', 'top']:
        ax = plot_widget.getAxis(axis)
        ax.setPen('k')  # Black axis lines
        ax.setTextPen('k')  # Black text