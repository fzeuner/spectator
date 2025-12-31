from enum import Enum


class AxisType(Enum):
    """Centralized enumeration of supported axis types.

    These names must stay in sync with the strings used in
    config.viewer_config.DEFAULT_AXIS_ORDERS and VIEWER_SELECTION_RULES.
    """

    STATES = "states"
    SPECTRAL = "spectral"
    SPATIAL_Y = "spatial_y"
    SPATIAL_X = "spatial_x"
    TIME = "time"
