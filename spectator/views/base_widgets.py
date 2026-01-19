"""
Base widget classes for the spectral data viewer.

This module contains the fundamental UI components that other widgets inherit from.
"""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui
from pyqtgraph.widgets.VerticalLabel import VerticalLabel as PgVerticalLabel
from typing import Optional
import warnings

# Import our models for configuration
from ..models import get_default_crosshair_colors, get_default_averaging_colors, get_default_min_line_distance
from ..utils.colors import getWidgetColors


class CustomVerticalLabel(PgVerticalLabel):
    """
    Custom VerticalLabel that extends pyqtgraph's VerticalLabel with minimum size constraints.
    
    This addresses the issue where vertical labels can become too small to be visible.
    Sets minimum width/height to 25 pixels instead of 0.
    """
    
    def __init__(self, text, orientation='vertical', forceWidth=True):
        """
        Initialize the custom vertical label.
        
        Args:
            text: Label text
            orientation: 'vertical' or 'horizontal'
            forceWidth: Whether to force minimum width based on text
        """
        super().__init__(text, orientation, forceWidth)
    
    def paintEvent(self, ev):
        """Override paintEvent to apply custom minimum size constraints."""
        p = QtGui.QPainter(self)
        
        if self.orientation == 'vertical':
            p.rotate(-90)
            rgn = QtCore.QRect(-self.height(), 0, self.height(), self.width())
        else:
            rgn = self.contentsRect()
        align = self.alignment()
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.hint = p.drawText(rgn, align, self.text())
        p.end()
        
        # Apply custom minimum size constraints (Franzi's modifications)
        if self.orientation == 'vertical':
            self.setMaximumWidth(self.hint.height())
            self.setMinimumWidth(25)  # Changed from 0 to 25
            self.setMaximumHeight(16777215)
            if self.forceWidth:
                self.setMinimumHeight(self.hint.width())
            else:
                self.setMinimumHeight(25)  # Changed from 0 to 25
        else:
            self.setMaximumHeight(self.hint.height())
            self.setMinimumHeight(25)  # Changed from 0 to 25
            self.setMaximumWidth(16777215)
            if self.forceWidth:
                self.setMinimumWidth(self.hint.width())
            else:
                self.setMinimumWidth(25)  # Changed from 0 to 25


class BasePlotWidget(QtWidgets.QWidget):
    """
    Base class for all plot widgets in the spectral data viewer.
    
    Provides common functionality for plot setup, labeling, and basic state management.
    """
    
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        """
        Initialize the base plot widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Setup layout
        self.layout = QtWidgets.QHBoxLayout(self)
        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.graphics_widget.setBackground(getWidgetColors().get('background', '#19232D'))
        self.plotItem = self.graphics_widget.addPlot(row=0, col=0, colspan=3)
        self.layout.addWidget(self.graphics_widget)
        self.setLayout(self.layout)
        
        # Setup label
        self.label = pg.LabelItem(justify='left', size='6pt')
        self.graphics_widget.addItem(self.label, row=1, col=0)
        
        # State tracking
        self.current_wl_idx = 0
        self.current_x_idx = 0
        self.current_x_idx_avg = 0
        self.current_wl_idx_avg = 0
        
        # Configuration
        self._setup_default_colors()
    
    def _setup_default_colors(self):
        """Setup default color schemes from models."""
        self.crosshair_colors = get_default_crosshair_colors()
        self.avg_colors = get_default_averaging_colors()
        self.min_line_distance = get_default_min_line_distance()
    
    def update_label(self, text: str):
        """
        Update the widget label text.
        
        Args:
            text: New label text
        """
        self.label.setText(text, size='6pt')
    
    def set_plot_title(self, title: str):
        """
        Set the plot title.
        
        Args:
            title: Plot title
        """
        self.plotItem.setTitle(title)
    
    def set_axis_labels(self, x_label: str = "", y_label: str = "", 
                       x_units: str = "", y_units: str = ""):
        """
        Set axis labels and units.
        
        Args:
            x_label: X-axis label
            y_label: Y-axis label  
            x_units: X-axis units
            y_units: Y-axis units
        """
        x_text = f"{x_label} ({x_units})" if x_units else x_label
        y_text = f"{y_label} ({y_units})" if y_units else y_label
        
        self.plotItem.setLabel('bottom', x_text)
        self.plotItem.setLabel('left', y_text)
    
    def enable_auto_range(self, x: bool = True, y: bool = True):
        """
        Enable or disable auto-ranging for axes.
        
        Args:
            x: Enable x-axis auto-range
            y: Enable y-axis auto-range
        """
        if x:
            self.plotItem.enableAutoRange(axis='x', enable=True)
        if y:
            self.plotItem.enableAutoRange(axis='y', enable=True)
    
    def set_range(self, x_range: Optional[tuple] = None, y_range: Optional[tuple] = None, padding: float = 0.0):
        """
        Set axis ranges.
        
        Args:
            x_range: (min, max) for x-axis
            y_range: (min, max) for y-axis
            padding: Padding around the range
        """
        if x_range:
            self.plotItem.setXRange(x_range[0], x_range[1], padding=padding)
        if y_range:
            self.plotItem.setYRange(y_range[0], y_range[1], padding=padding)
    
    def setup_standard_axes(self, left_width: int = 30, top_height: int = 15):
        """
        Setup standard axis dimensions and visibility.
        
        Args:
            left_width: Width of left axis in pixels
            top_height: Height of top axis in pixels
        """
        # Configure axis visibility
        self.plotItem.showAxes(True, showValues=(True, True, False, False))
        
        # Set individual axis dimensions for precise control
        self.plotItem.getAxis('top').setHeight(top_height)
        self.plotItem.getAxis('left').setWidth(left_width)
    
    def setup_custom_ticks(self, spectral_range: Optional[int] = None, spatial_range: Optional[int] = None,
                          num_spectral_ticks: int = 8, num_spatial_ticks: int = 6):
        """
        Setup custom tick marks for spectral and spatial axes.
        
        Args:
            spectral_range: Maximum spectral index (for bottom axis)
            spatial_range: Maximum spatial index (for left axis)
            num_spectral_ticks: Number of spectral tick marks
            num_spatial_ticks: Number of spatial tick marks
        """
        if spectral_range is not None:
            spectral_ticks_pix = np.linspace(0, spectral_range - 1, num_spectral_ticks)
            spectral_ticks = [(tick, f'{tick:.0f}') for tick in spectral_ticks_pix]
            self.plotItem.getAxis('bottom').setTicks([spectral_ticks])
        
        if spatial_range is not None:
            spatial_ticks_pix = np.linspace(0, spatial_range - 1, num_spatial_ticks)
            spatial_ticks = [(tick, f'{tick:.0f}') for tick in spatial_ticks_pix]
            self.plotItem.getAxis('left').setTicks([spatial_ticks])
    
    def configure_axis_styling(self, hide_left_label: bool = True, right_label: str = "x", 
                              right_units: str = "pixel"):
        """
        Configure standard axis styling patterns.
        
        Args:
            hide_left_label: Whether to hide the left axis label
            right_label: Label text for right axis
            right_units: Units for right axis
        """
        # Configure left axis styling
        left_axis = self.plotItem.getAxis('left')
        if hide_left_label:
            left_axis.showLabel(False)
        left_axis.setStyle(showValues=True)
        left_axis.enableAutoSIPrefix(False)
        
        # Configure right axis label
        right_axis = self.plotItem.getAxis('right')
        right_axis.setLabel(text=right_label, units=right_units)
    
    def setup_viewbox_limits(self, x_max: float, y_max: float, 
                           min_range: float = 1.0, enable_rect_zoom: bool = False):
        """
        Setup standard viewbox limits and interaction modes.
        
        Args:
            x_max: Maximum x value for limits
            y_max: Maximum y value for limits  
            min_range: Minimum zoom range
            enable_rect_zoom: Whether to enable rectangle zoom mode
        """
        vb = self.plotItem.vb
        
        if enable_rect_zoom:
            try:
                # Enable rectangle-zoom mode for left-drag
                vb.setMouseMode(pg.ViewBox.RectMode)
            except Exception:
                pass
        
        # Set viewbox limits to constrain zoom and pan
        try:
            vb.setLimits(
                xMin=0, xMax=float(x_max),
                yMin=0, yMax=float(y_max),
                minXRange=min_range, minYRange=min_range,
                maxXRange=float(x_max + 1),
                maxYRange=float(y_max + 1)
            )
        except Exception:
            pass


class BaseControlWidget(QtWidgets.QGroupBox):
    """
    Base class for control widgets (panels with controls and settings).
    
    Provides common functionality for grouped controls with consistent styling.
    """
    
    def __init__(self, title: str, parent: Optional[QtWidgets.QWidget] = None):
        """
        Initialize the base control widget.
        
        Args:
            title: Group box title
            parent: Parent widget
        """
        super().__init__(title, parent)
        
        # Setup main layout
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.main_layout)
        
        # Configuration
        self._setup_default_styling()
    
    def _setup_default_styling(self):
        """Setup default styling for the control widget."""
        # Add any default styling here
        pass
    
    def add_control_row(self, label: str, widget: QtWidgets.QWidget) -> QtWidgets.QHBoxLayout:
        """
        Add a labeled control row.
        
        Args:
            label: Label text
            widget: Control widget
            
        Returns:
            The layout containing the label and widget
        """
        row_layout = QtWidgets.QHBoxLayout()
        label_widget = QtWidgets.QLabel(label)
        row_layout.addWidget(label_widget)
        row_layout.addWidget(widget)
        
        self.main_layout.addLayout(row_layout)
        return row_layout
    
    def add_checkbox(self, label: str, checked: bool = False, 
                    callback: Optional[callable] = None) -> QtWidgets.QCheckBox:
        """
        Add a checkbox control.
        
        Args:
            label: Checkbox label
            checked: Initial checked state
            callback: Callback function for state changes
            
        Returns:
            The checkbox widget
        """
        checkbox = QtWidgets.QCheckBox(label)
        checkbox.setChecked(checked)
        
        if callback:
            checkbox.stateChanged.connect(callback)
        
        self.main_layout.addWidget(checkbox)
        return checkbox
    
    def add_button(self, label: str, callback: Optional[callable] = None) -> QtWidgets.QPushButton:
        """
        Add a button control.
        
        Args:
            label: Button label
            callback: Callback function for clicks
            
        Returns:
            The button widget
        """
        button = QtWidgets.QPushButton(label)
        
        if callback:
            button.clicked.connect(callback)
        
        self.main_layout.addWidget(button)
        return button
    
    def add_line_edit(self, label: str, initial_value: str = "", 
                     callback: Optional[callable] = None) -> QtWidgets.QLineEdit:
        """
        Add a line edit control with label.
        
        Args:
            label: Label text
            initial_value: Initial text value
            callback: Callback function for text changes
            
        Returns:
            The line edit widget
        """
        line_edit = QtWidgets.QLineEdit(initial_value)
        
        if callback:
            line_edit.textChanged.connect(callback)
        
        self.add_control_row(label, line_edit)
        return line_edit
    
    def add_separator(self):
        """Add a horizontal separator line."""
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.main_layout.addWidget(line)


class BaseImageWidget(BasePlotWidget):
    """
    Base class for image display widgets.
    
    Extends BasePlotWidget with image-specific functionality.
    """
    
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        """
        Initialize the base image widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Image-specific setup
        self.image_item = None
        self.histogram = None
        
    def setup_image_display(self, data: np.ndarray):
        """
        Setup image display with data.
        
        Args:
            data: 2D image data array
        """
        if self.image_item is None:
            self.image_item = pg.ImageItem()
            self.plotItem.addItem(self.image_item)
        
        self.image_item.setImage(data)
        
        # Note: Histogram functionality removed for simplicity and compatibility
    
    def update_image_data(self, data: np.ndarray):
        """
        Update the displayed image data.
        
        Args:
            data: New 2D image data array
        """
        if self.image_item is not None:
            self.image_item.setImage(data)
    
    def set_image_rect(self, x_min: float, y_min: float, width: float, height: float):
        """
        Set the image rectangle (coordinate mapping).
        
        Args:
            x_min: Minimum x coordinate
            y_min: Minimum y coordinate
            width: Image width in coordinate units
            height: Image height in coordinate units
        """
        if self.image_item is not None:
            self.image_item.setRect(x_min, y_min, width, height)

