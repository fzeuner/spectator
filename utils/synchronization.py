"""
Synchronization utilities for coordinating plot interactions across multiple widgets.

This module provides classes to handle synchronization of averaging lines, crosshairs,
and other plot interactions without code duplication.
"""

import numpy as np
from typing import List, Optional, Callable, Any
from pyqtgraph.Qt import QtCore


class SynchronizationManager(QtCore.QObject):
    """
    Manages synchronization of plot interactions across multiple widget collections.
    
    Handles common patterns like widget iteration, position broadcasting, and
    index conversion to reduce code duplication in plot controllers.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.spectrum_image_widgets: List[Any] = []
        self.spectra_widgets: List[Any] = []
        self.spatial_widgets: List[Any] = []
    
    def set_widget_collections(self, spectrum_image_widgets: List[Any], 
                              spectra_widgets: List[Any], 
                              spatial_widgets: List[Any]):
        """Set the widget collections to synchronize."""
        self.spectrum_image_widgets = spectrum_image_widgets
        self.spectra_widgets = spectra_widgets
        self.spatial_widgets = spatial_widgets
    
    def sync_spectral_averaging(self, left_pos: float, center_pos: float, right_pos: float, 
                               source_index: int, sync_enabled: bool):
        """Synchronize spectral averaging lines across all widgets."""
        if not sync_enabled:
            return
            
        self._sync_averaging_lines('spectral', (left_pos, center_pos, right_pos), source_index)
        
        # Update spatial widgets
        self._update_spatial_widgets_from_spectral(left_pos, center_pos, right_pos)
    
    def sync_spatial_averaging(self, lower_pos: float, center_pos: float, upper_pos: float,
                              source_index: int, sync_enabled: bool):
        """Synchronize spatial averaging lines across all widgets."""
        if not sync_enabled:
            return
            
        self._sync_averaging_lines('spatial', (lower_pos, center_pos, upper_pos), source_index)
        
        # Update spectrum widgets
        self._update_spectrum_widgets_from_spatial(lower_pos, center_pos, upper_pos, source_index)
    
    def sync_crosshair_movement(self, xpos: float, ypos: float, source_index: int, sync_enabled: bool):
        """
        Synchronize crosshair movement across all widgets.
        
        Args:
            xpos: X position (spectral)
            ypos: Y position (spatial)
            source_index: Index of the source widget
            sync_enabled: Whether synchronization is enabled
        """
        if not self._validate_source_index(source_index):
            return
            
        source_spectrum_widget = self.spectra_widgets[source_index]
        n_x_pixel = source_spectrum_widget.full_data.shape[1]
        index_x = self._convert_to_index(ypos, n_x_pixel)
        
        if sync_enabled:
            self._sync_image_widgets_crosshair(xpos, ypos, source_index)
            self._sync_spectrum_widgets_crosshair(xpos, index_x, source_index)
            self._sync_spatial_widgets_crosshair(xpos, ypos, source_index)
        else:
            # Update only source widget when sync is off
            source_spectrum_widget.update_spectral_line(xpos)
            source_spectrum_widget.update_spectrum_data(index_x)
        
        # Always update source spatial widget
        self._update_source_spatial_widget(xpos, ypos, source_index)
    
    def broadcast_averaging_positions_on_sync_enable(self, sync_type: str):
        """
        Broadcast current averaging positions when sync is enabled.
        
        Args:
            sync_type: 'spectral' or 'spatial'
        """
        if not self.spectrum_image_widgets:
            return
            
        if sync_type == 'spectral':
            self._broadcast_spectral_positions()
        elif sync_type == 'spatial':
            self._broadcast_spatial_positions()
    
    def broadcast_crosshair_positions(self):
        """Broadcast current crosshair positions when sync is enabled."""
        if not self.spectrum_image_widgets:
            return
            
        # Find the first image widget with a crosshair position to broadcast
        for src_idx, img_widget in enumerate(self.spectrum_image_widgets):
            if hasattr(img_widget, 'hLine') and hasattr(img_widget, 'vLine'):
                if img_widget.hLine and img_widget.vLine:
                    xpos = img_widget.vLine.value()
                    ypos = img_widget.hLine.value()
                    # Sync to all other widgets
                    self._sync_image_widgets_crosshair(xpos, ypos, src_idx)
                    if self.spectra_widgets and src_idx < len(self.spectra_widgets):
                        source_spectrum_widget = self.spectra_widgets[src_idx]
                        n_x_pixel = source_spectrum_widget.full_data.shape[1]
                        index_x = self._convert_to_index(ypos, n_x_pixel)
                        self._sync_spectrum_widgets_crosshair(xpos, index_x, src_idx)
                    self._sync_spatial_widgets_crosshair(xpos, ypos, src_idx)
                    break
    
    def _update_spatial_widgets_from_spectral(self, left_pos: float, center_pos: float, right_pos: float):
        """Update spatial widgets based on spectral averaging positions."""
        if not self.spatial_widgets:
            return
            
        for sp_idx, sp_widget in enumerate(self.spatial_widgets):
            if sp_idx < len(self.spectrum_image_widgets):
                img_widget = self.spectrum_image_widgets[sp_idx]
                if self._has_spectral_lines(img_widget):
                    n_wl_pixel = sp_widget.full_data.shape[0]
                    index_wl_l = self._convert_to_index(left_pos, n_wl_pixel)
                    index_wl_c = self._convert_to_index(center_pos, n_wl_pixel)
                    index_wl_h = self._convert_to_index(right_pos, n_wl_pixel)
                    sp_widget.update_spatial_data_wl_avg(index_wl_l, index_wl_c, index_wl_h)
    
    def _update_spectrum_widgets_from_spatial(self, lower_pos: float, center_pos: float, upper_pos: float, source_index: int):
        """Update spectrum widgets based on spatial averaging positions."""
        if not self.spectra_widgets:
            return
            
        for spec_idx, spec_widget in enumerate(self.spectra_widgets):
            if spec_idx < len(self.spectrum_image_widgets):
                img_widget = self.spectrum_image_widgets[spec_idx]
                if (self._has_spatial_lines(img_widget) and 
                    spec_idx != source_index and 
                    hasattr(spec_widget, 'handle_spatial_avg_line_movement')):
                    spec_widget.handle_spatial_avg_line_movement(lower_pos, center_pos, upper_pos, source_index)
    
    def _sync_image_widgets_crosshair(self, xpos: float, ypos: float, source_index: int):
        """Sync crosshair across image widgets."""
        for img_idx, img_widget in enumerate(self.spectrum_image_widgets):
            if img_idx == source_index:
                if not img_widget.crosshair_locked:
                    img_widget.set_crosshair_position(xpos, ypos)
            elif not img_widget.crosshair_locked:
                img_widget.set_crosshair_position(xpos, ypos)
    
    def _sync_spectrum_widgets_crosshair(self, xpos: float, index_x: int, source_index: int):
        """Sync crosshair across spectrum widgets."""
        for spec_idx, spec_widget in enumerate(self.spectra_widgets):
            corresponding_img_widget = self.spectrum_image_widgets[spec_idx]
            
            if spec_idx == source_index:
                spec_widget.update_spectral_line(xpos)
                spec_widget.update_spectrum_data(index_x)
            elif not corresponding_img_widget.crosshair_locked:
                spec_widget.update_spectral_line(xpos)
                spec_widget.update_spectrum_data(index_x)
    
    def _sync_spatial_widgets_crosshair(self, xpos: float, ypos: float, source_index: int):
        """Sync crosshair across spatial widgets."""
        for spatial_idx, spatial_widget in enumerate(self.spatial_widgets):
            corresponding_img_widget = (self.spectrum_image_widgets[spatial_idx] 
                                      if spatial_idx < len(self.spectrum_image_widgets) else None)
            
            if spatial_idx == source_index:
                self._update_spatial_widget_crosshair(spatial_widget, xpos, ypos)
            elif corresponding_img_widget and not corresponding_img_widget.crosshair_locked:
                self._update_spatial_widget_crosshair(spatial_widget, xpos, ypos)
    
    def _update_source_spatial_widget(self, xpos: float, ypos: float, source_index: int):
        """Always update source spatial widget regardless of sync state."""
        if self.spatial_widgets and source_index < len(self.spatial_widgets):
            source_spatial_widget = self.spatial_widgets[source_index]
            self._update_spatial_widget_crosshair(source_spatial_widget, xpos, ypos)
    
    def _update_spatial_widget_crosshair(self, spatial_widget: Any, xpos: float, ypos: float):
        """Update a single spatial widget's crosshair and data."""
        spatial_widget.update_x_line(ypos)
        spectral_idx = self._convert_to_index(xpos, spatial_widget.full_data.shape[0])
        spatial_widget.update_spatial_data_spectral(spectral_idx)
    
    def _broadcast_spectral_positions(self):
        """Broadcast current spectral averaging positions when sync is enabled."""
        self._broadcast_averaging_positions('spectral')
    
    def _broadcast_spatial_positions(self):
        """Broadcast current spatial averaging positions when sync is enabled."""
        self._broadcast_averaging_positions('spatial')
    
    def _sync_averaging_lines(self, avg_type: str, positions: tuple, source_index: int):
        """Unified method to sync averaging lines across widgets."""
        for dst_idx, dst_img in enumerate(self.spectrum_image_widgets):
            if dst_idx != source_index:
                if avg_type == 'spectral':
                    dst_img.sync_spectral_averaging_lines(*positions, source_index)
                else:  # spatial
                    dst_img.sync_spatial_averaging_lines(*positions, source_index)
    
    def _broadcast_averaging_positions(self, avg_type: str):
        """Unified method to broadcast averaging positions when sync is enabled."""
        has_lines_func = self._has_spectral_lines if avg_type == 'spectral' else self._has_spatial_lines
        manager_attr = 'spectral_manager' if avg_type == 'spectral' else 'spatial_manager'
        sync_method = 'sync_spectral_averaging_lines' if avg_type == 'spectral' else 'sync_spatial_averaging_lines'
        
        # Find all widgets with lines
        widgets_with_lines = []
        for src_idx, img_widget in enumerate(self.spectrum_image_widgets):
            if has_lines_func(img_widget):
                widgets_with_lines.append((src_idx, img_widget))
        
        if not widgets_with_lines:
            return
            
        # Use the first widget with lines as the source
        src_idx, src_widget = widgets_with_lines[0]
        manager = getattr(src_widget, manager_attr)
        pos1 = manager.line1.value()
        center_pos = manager.center_line.value()
        pos2 = manager.line2.value()
        
        # Only sync to widgets that already have lines
        for dst_idx, dst_img in enumerate(self.spectrum_image_widgets):
            if dst_idx != src_idx and has_lines_func(dst_img):
                getattr(dst_img, sync_method)(pos1, center_pos, pos2, src_idx)
    
    def _has_spectral_lines(self, img_widget: Any) -> bool:
        """Check if image widget has spectral averaging lines."""
        return self._has_averaging_lines(img_widget, 'spectral_manager')
    
    def _has_spatial_lines(self, img_widget: Any) -> bool:
        """Check if image widget has spatial averaging lines."""
        return self._has_averaging_lines(img_widget, 'spatial_manager')
    
    def _has_averaging_lines(self, img_widget: Any, manager_attr: str) -> bool:
        """Unified method to check if widget has averaging lines."""
        manager = getattr(img_widget, manager_attr)
        return manager and manager.has_lines()
    
    def _convert_to_index(self, pos: float, max_val: int) -> int:
        """Convert position to array index with bounds checking."""
        return np.clip(int(np.round(pos)), 0, max_val - 1)
    
    def _validate_source_index(self, source_index: int) -> bool:
        """Validate that source index is within bounds."""
        return (self.spectra_widgets and 
                0 <= source_index < len(self.spectra_widgets))
