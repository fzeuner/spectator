"""
Reusable averaging line management for spectrum image windows.

This module provides a unified approach to handling both spectral (vertical) and spatial (horizontal)
averaging lines, eliminating code duplication and providing a consistent interface.
"""

import numpy as np
from PyQt5 import QtCore
import pyqtgraph as pg
from typing import Optional, Tuple, Callable
from utils.colors import getWidgetColors
from utils.plotting import add_line

MIN_LINE_DISTANCE = 3


class AveragingLineManager(QtCore.QObject):
    """
    Manages averaging lines (spectral or spatial) for a plot widget.
    
    Handles line creation, positioning, clamping, and signal emission in a unified way
    for both vertical (spectral) and horizontal (spatial) averaging lines.
    """
    
    # Signals
    regionChanged = QtCore.pyqtSignal(float, float, float, int)  # left, center, right, stokes_index
    
    def __init__(self, plot_item, orientation: str, data_range: int, stokes_index: int, 
                 color_key: str, label_widget: Optional[pg.LabelItem] = None):
        """
        Initialize the averaging line manager.
        
        Args:
            plot_item: PyQtGraph PlotItem to add lines to
            orientation: 'vertical' for spectral (90°) or 'horizontal' for spatial (0°)
            data_range: Maximum data range (n_spectral or n_x_pixel)
            stokes_index: Stokes parameter index for signal emission
            color_key: Color key for getWidgetColors() (e.g., 'averaging_v', 'averaging_h')
            label_widget: Optional label widget to update with positions
        """
        super().__init__()
        
        self.plot_item = plot_item
        self.orientation = orientation
        self.data_range = data_range
        self.stokes_index = stokes_index
        self.color_key = color_key
        self.label_widget = label_widget
        
        # Line references
        self.line1: Optional[pg.InfiniteLine] = None
        self.line2: Optional[pg.InfiniteLine] = None
        self.center_line: Optional[pg.InfiniteLine] = None
        
        # Configuration
        self.angle = 90 if orientation == 'vertical' else 0
        self.axis_name = 'λ' if orientation == 'vertical' else 'x'
        self.label_terms = ('left', 'center', 'right') if orientation == 'vertical' else ('lower', 'center', 'upper')
        
        # Optional callbacks to integrate with UI controllers
        # These can be set by the window to handle UI activation/notifications
        self.on_region_created: Optional[Callable[[], None]] = None
        self.on_region_removed: Optional[Callable[[], None]] = None

        # Preview drag state
        self._drag_start_pos: Optional[float] = None
        self._temp_line_press: Optional[pg.InfiniteLine] = None
        self._temp_line_drag: Optional[pg.InfiniteLine] = None
        
    def set_data_range(self, new_range: int) -> None:
        """Update the valid data range and clamp any existing line positions.

        Args:
            new_range: The new maximum data range (e.g., number of spectral or spatial pixels)
        """
        # Ensure a valid positive range
        self.data_range = max(1, int(new_range))

        # If lines exist, re-apply their positions to clamp within the new range
        positions = self.get_positions()
        if positions is not None:
            pos1, center, pos2 = positions
            # set_positions will clamp and update label without emitting external signals
            self.set_positions(pos1, center, pos2, block_signals=True)

    def create_default_lines(self, center_pos: Optional[float] = None, width: int = 10) -> None:
        """
        Create default averaging lines centered in the data range.
        
        Args:
            center_pos: Center position (defaults to middle of data range)
            width: Total width of averaging region in pixels
        """
        had_lines_before = self.has_lines()
        if center_pos is None:
            center_pos = self.data_range // 2
            
        half_width = width // 2
        pos1 = max(0, center_pos - half_width)
        pos2 = min(self.data_range - 1, center_pos + half_width)
        
        # Remove existing lines first
        self.remove_lines()
        
        # Create new lines
        colors = getWidgetColors()
        color = colors.get(self.color_key, 'yellow')
        
        self.line1 = add_line(self.plot_item, color, self.angle, pos=pos1, moveable=True, style=QtCore.Qt.SolidLine)
        self.line2 = add_line(self.plot_item, color, self.angle, pos=pos2, moveable=True, style=QtCore.Qt.SolidLine)
        self.center_line = add_line(self.plot_item, color, self.angle, pos=center_pos, moveable=True, style=QtCore.Qt.DotLine)
        
        # Connect signals
        self.line1.sigPositionChanged.connect(lambda line: self._update_lines_and_emit(source_line=line))
        self.line2.sigPositionChanged.connect(lambda line: self._update_lines_and_emit(source_line=line))
        self.center_line.sigPositionChanged.connect(lambda line: self._update_lines_and_emit(source_line=line))
        
        # Initial update
        self._update_lines_and_emit(source_line=self.line1)

        # Fire created callback only if region is newly created
        if not had_lines_before and self.has_lines() and self.on_region_created:
            try:
                self.on_region_created()
            except Exception:
                pass
    
    def remove_lines(self) -> None:
        """Remove all averaging lines from the plot."""
        had_lines_before = self.has_lines()
        for line in [self.line1, self.line2, self.center_line]:
            if line is not None:
                self.plot_item.removeItem(line)
        
        self.line1 = None
        self.line2 = None
        self.center_line = None
        
        # Clear label
        if self.label_widget:
            self.label_widget.setText("")

        # Fire removed callback if a region existed before
        if had_lines_before and self.on_region_removed:
            try:
                self.on_region_removed()
            except Exception:
                pass
    
    def has_lines(self) -> bool:
        """Check if averaging lines exist."""
        return all(line is not None for line in [self.line1, self.line2, self.center_line])
    
    def get_positions(self) -> Optional[Tuple[float, float, float]]:
        """Get current line positions as (pos1, center, pos2)."""
        if not self.has_lines():
            return None
        return (self.line1.value(), self.center_line.value(), self.line2.value())
    
    def set_positions(self, pos1: float, center: float, pos2: float, block_signals: bool = True) -> None:
        """
        Set line positions programmatically (e.g., for synchronization).
        
        Args:
            pos1: Position of first line
            center: Position of center line
            pos2: Position of second line
            block_signals: Whether to block signals during update
        """
        if not self.has_lines():
            return
            
        if block_signals:
            self.line1.blockSignals(True)
            self.line2.blockSignals(True)
            self.center_line.blockSignals(True)
        
        try:
            # Clamp positions to valid range
            pos1 = self._clamp_position(pos1)
            pos2 = self._clamp_position(pos2)
            center = self._clamp_position(center)
            
            # Ensure proper ordering and minimum distance
            if pos1 > pos2:
                pos1, pos2 = pos2, pos1
            
            if (pos2 - pos1) < MIN_LINE_DISTANCE:
                center_temp = (pos1 + pos2) / 2
                pos1 = self._clamp_position(center_temp - MIN_LINE_DISTANCE / 2)
                pos2 = self._clamp_position(center_temp + MIN_LINE_DISTANCE / 2)
            
            center = (pos1 + pos2) / 2
            
            # Update line positions
            self.line1.setValue(pos1)
            self.line2.setValue(pos2)
            self.center_line.setValue(center)
            
            # Update label
            self._update_label(pos1, center, pos2)
            
        finally:
            if block_signals:
                self.line1.blockSignals(False)
                self.line2.blockSignals(False)
                self.center_line.blockSignals(False)
    
    def _clamp_position(self, pos: float) -> float:
        """Clamp position to valid data range."""
        return np.clip(pos, 0, self.data_range - 1)
    
    def _update_lines_and_emit(self, source_line=None) -> None:
        """Update line positions and emit region changed signal."""
        if not self.has_lines():
            return
        
        # Block signals to prevent recursion
        self.line1.blockSignals(True)
        self.line2.blockSignals(True)
        self.center_line.blockSignals(True)
        
        try:
            current_pos1 = self.line1.value()
            current_pos2 = self.line2.value()
            current_center = self.center_line.value()
            width = max(current_pos2 - current_pos1, MIN_LINE_DISTANCE)
            half = width / 2.0

            new_pos1 = current_pos1
            new_pos2 = current_pos2
            new_center = current_center

            # Handle different source lines
            if source_line is self.line1:
                # Move left/lower edge; keep width constant, clamp so right/upper stays within bounds
                candidate_pos1 = self._clamp_position(current_pos1)
                candidate_pos2 = candidate_pos1 + width
                if candidate_pos2 > (self.data_range - 1):
                    # Clamp pos1 so pos2 stays in range and width preserved
                    candidate_pos1 = max(0, (self.data_range - 1) - width)
                    candidate_pos2 = candidate_pos1 + width
                new_pos1, new_pos2 = candidate_pos1, candidate_pos2
                new_center = (new_pos1 + new_pos2) / 2

            elif source_line is self.line2:
                # Move right/upper edge; keep width constant, clamp so left/lower stays within bounds
                candidate_pos2 = self._clamp_position(current_pos2)
                candidate_pos1 = candidate_pos2 - width
                if candidate_pos1 < 0:
                    candidate_pos1 = 0
                    candidate_pos2 = candidate_pos1 + width
                    if candidate_pos2 > (self.data_range - 1):
                        candidate_pos2 = self.data_range - 1
                        candidate_pos1 = candidate_pos2 - width
                new_pos1, new_pos2 = candidate_pos1, candidate_pos2
                new_center = (new_pos1 + new_pos2) / 2

            elif source_line == self.center_line:
                # Move center; preserve width by clamping center range so both edges stay in-bounds
                spacing = max(half, MIN_LINE_DISTANCE / 2.0)
                min_center = spacing
                max_center = (self.data_range - 1) - spacing
                new_center = float(np.clip(current_center, min_center, max_center))
                new_pos1 = new_center - spacing
                new_pos2 = new_center + spacing

            
            # Update line positions
            self.line1.setValue(new_pos1)
            self.line2.setValue(new_pos2)
            self.center_line.setValue((new_pos1 + new_pos2) / 2)
            
            # Get final positions and emit signal
            final_pos1 = self.line1.value()
            final_pos2 = self.line2.value()
            final_center = (final_pos1 + final_pos2) / 2
            
            self.regionChanged.emit(final_pos1, final_center, final_pos2, self.stokes_index)
            
            # Update label
            self._update_label(final_pos1, final_center, final_pos2)
            
            # Trigger button activation callback if provided
            if hasattr(self, '_button_activation_callback') and self._button_activation_callback:
                self._button_activation_callback()
            
        finally:
            self.line1.blockSignals(False)
            self.line2.blockSignals(False)
            self.center_line.blockSignals(False)
    
    def _update_label(self, pos1: float, center: float, pos2: float) -> None:
        """Update the label widget with current positions."""
        if self.label_widget:
            # Use compact labels without axis prefixes
            # vertical (spectral): left/center/right -> l/c/r
            # horizontal (spatial): lower/center/upper -> l/c/u
            if self.orientation == 'vertical':
                t1, t2, t3 = 'l', 'c', 'r'
            else:
                t1, t2, t3 = 'l', 'c', 'u'
            self.label_widget.setText(
                f"{t1}: {pos1:.0f}, {t2}: {center:.0f}, {t3}: {pos2:.0f}",
                size='8pt'
            )

    def create_from_span(self, start: float, end: float) -> None:
        """Convenience to create a region from two positions (mouse drag span)."""
        pos1, pos2 = (start, end) if start <= end else (end, start)
        width = max(int(round(pos2 - pos1)), MIN_LINE_DISTANCE)
        center = (pos1 + pos2) / 2
        self.create_default_lines(center_pos=center, width=width)

    # --- Preview span handling (temp dashed lines) ---
    def _remove_preview_lines(self) -> None:
        if self._temp_line_press is not None:
            try:
                self.plot_item.removeItem(self._temp_line_press)
            except Exception:
                pass
            self._temp_line_press = None
        if self._temp_line_drag is not None:
            try:
                self.plot_item.removeItem(self._temp_line_drag)
            except Exception:
                pass
            self._temp_line_drag = None

    def begin_drag_at(self, pos: float) -> None:
        """Start a preview drag at given position (axis depends on orientation)."""
        self._drag_start_pos = float(pos)
        self._remove_preview_lines()
        colors = getWidgetColors()
        color = colors.get(self.color_key, 'yellow')
        # DashLine preview at start position
        self._temp_line_press = add_line(self.plot_item, color, self.angle, pos=self._drag_start_pos, style=QtCore.Qt.DashLine)

    def update_drag_to(self, pos: float) -> None:
        """Update preview to current position by drawing/moving second dashed line."""
        current_pos = float(pos)
        colors = getWidgetColors()
        color = colors.get(self.color_key, 'yellow')
        if self._temp_line_drag is not None:
            # Remove and recreate to keep it simple and consistent with window code
            try:
                self.plot_item.removeItem(self._temp_line_drag)
            except Exception:
                pass
            self._temp_line_drag = None
        self._temp_line_drag = add_line(self.plot_item, color, self.angle, pos=current_pos, style=QtCore.Qt.DashLine)

    def end_drag_at(self, pos: float) -> None:
        """Finish the preview drag, create region from span, and clear preview."""
        if self._drag_start_pos is not None:
            self.create_from_span(self._drag_start_pos, float(pos))
        self._drag_start_pos = None
        self._remove_preview_lines()
