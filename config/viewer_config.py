"""Viewer configuration: default axis orders and viewer selection rules.

This module centralizes how N-D data (shape + axis semantics) maps to
viewer types. It is intentionally declarative so the Manager and
selector logic can stay simple.
"""

from __future__ import annotations

from typing import Dict, Tuple, Sequence

# Default axis ordering for display_data by data dimensionality.
# Keys are data.ndim, values are tuples of axis labels in data order.
DEFAULT_AXIS_ORDERS: Dict[int, Tuple[str, ...]] = {
    1: ("spectral",),
    2: ("spectral", "spatial_x"),
    3: ("states", "spectral", "spatial_x"),
    # 4D default chosen for scan-style data: 
    4: ("states", "spectral", "spatial_y", "spatial_x"),
}

# Declarative mapping from canonical axis order -> viewer type.
# The Manager's viewer selector can consult this mapping instead of
# hard-coding logic. Shapes are validated separately; here we only
# encode semantic axis order.
VIEWER_SELECTION_RULES: Dict[Tuple[str, ...], str] = {
    # 3D canonical viewer: states, spectral, spatial_x
    ("states", "spectral", "spatial_x"): "spectator",
    # 4D scan viewer: states, spectral, spatial_y, spatial_x
    ("states", "spatial_y", "spectral", "spatial_x"): "scan_viewer",
}

__all__ = [
    "DEFAULT_AXIS_ORDERS",
    "VIEWER_SELECTION_RULES",
]
