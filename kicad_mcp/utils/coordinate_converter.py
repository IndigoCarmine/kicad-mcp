"""
Coordinate conversion helpers for KiCad schematic generation.

KiCad schematic files store positions in internal units of 0.1 mm.
This module provides a small converter class for translating between
internal units and millimetres, plus a standalone helper for checking
whether a millimetre position lies within an A4 schematic sheet.
"""

# A4 landscape sheet dimensions in millimetres (KiCad default schematic size).
A4_WIDTH_MM = 297.0
A4_HEIGHT_MM = 210.0

# Default margin (mm) applied on every side when validating the usable area.
DEFAULT_MARGIN_MM = 10.0

# Number of internal units per millimetre in KiCad schematics (0.1 mm units).
INTERNAL_UNITS_PER_MM = 10.0


class CoordinateConverter:
    """
    Convert between KiCad schematic internal units (0.1 mm) and millimetres.

    The converter is deliberately lightweight; it only needs to be
    instantiable and offer simple conversion helpers.
    """

    def __init__(self) -> None:
        # Conversion factor between internal units and millimetres.
        self.units_per_mm = INTERNAL_UNITS_PER_MM

    def to_mm(self, value: float) -> float:
        """Convert a value from internal units (0.1 mm) to millimetres."""
        return value / self.units_per_mm

    def from_mm(self, value: float) -> float:
        """Convert a value from millimetres to internal units (0.1 mm)."""
        return value * self.units_per_mm


def validate_position(x: float, y: float, use_margins: bool = True) -> bool:
    """
    Check whether a millimetre position lies within an A4 schematic sheet.

    Args:
        x: X coordinate in millimetres.
        y: Y coordinate in millimetres.
        use_margins: When True, shrink the valid region by ``DEFAULT_MARGIN_MM``
            on every side; when False, use the full sheet.

    Returns:
        True if (x, y) is inside the (possibly margin-adjusted) rectangle.
    """
    margin = DEFAULT_MARGIN_MM if use_margins else 0.0

    min_x = margin
    min_y = margin
    max_x = A4_WIDTH_MM - margin
    max_y = A4_HEIGHT_MM - margin

    return min_x <= x <= max_x and min_y <= y <= max_y
