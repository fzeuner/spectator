"""
Base widget classes for the spectral data viewer.

This module contains the fundamental UI components that other widgets inherit from.
"""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from typing import Optional

# Import our models for configuration
from models import get_default_crosshair_colors, get_default_averaging_colors, get_default_min_line_distance

# Import existing functions for compatibility
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.colors import getWidgetColors


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
        self.plotItem = self.graphics_widget.addPlot(row=0, col=0, colspan=2)
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

