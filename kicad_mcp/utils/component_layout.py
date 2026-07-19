"""
Component layout management for KiCad schematic generation.

Provides an A4 sheet-bounds description and a layout manager that finds
valid, non-overlapping positions for components on a fixed grid while
keeping every returned position inside the usable (margin-adjusted) area.
"""

from dataclasses import dataclass, field

from kicad_mcp.config import CIRCUIT_DEFAULTS
from kicad_mcp.utils.coordinate_converter import (
    A4_HEIGHT_MM,
    A4_WIDTH_MM,
    DEFAULT_MARGIN_MM,
    validate_position,
)

# Grid spacing (mm) used when searching for a free cell. Falls back to a
# sensible constant if the config value is unavailable.
COMPONENT_SPACING = float(CIRCUIT_DEFAULTS.get("component_spacing", 10.16))


@dataclass
class SchematicBounds:
    """
    Describes the drawable bounds of a schematic sheet.

    Defaults to an A4 landscape sheet with a uniform margin on every side.
    """

    width: float = A4_WIDTH_MM
    height: float = A4_HEIGHT_MM
    margin: float = DEFAULT_MARGIN_MM

    @property
    def usable_width(self) -> float:
        """Width of the drawable area after subtracting both side margins."""
        return self.width - 2 * self.margin

    @property
    def usable_height(self) -> float:
        """Height of the drawable area after subtracting both margins."""
        return self.height - 2 * self.margin

    @property
    def min_x(self) -> float:
        """Left edge of the usable area."""
        return self.margin

    @property
    def min_y(self) -> float:
        """Top edge of the usable area."""
        return self.margin

    @property
    def max_x(self) -> float:
        """Right edge of the usable area."""
        return self.width - self.margin

    @property
    def max_y(self) -> float:
        """Bottom edge of the usable area."""
        return self.height - self.margin


class ComponentLayoutManager:
    """
    Places components on a fixed grid inside the usable schematic area.

    Positions are clamped into the usable rectangle and snapped to a grid so
    that components never overlap. Every position returned by
    :meth:`find_valid_position` is guaranteed to satisfy
    ``validate_position(x, y, use_margins=True)``.
    """

    def __init__(self, bounds: SchematicBounds | None = None) -> None:
        self.bounds = bounds or SchematicBounds()
        self.spacing = COMPONENT_SPACING
        # Set of occupied grid cells, stored as (col, row) integer tuples.
        self._occupied: set[tuple[int, int]] = set()

    def clear_layout(self) -> None:
        """Reset all recorded occupied positions."""
        self._occupied.clear()

    def _clamp(self, value: float, low: float, high: float) -> float:
        """Clamp ``value`` into the inclusive range [low, high]."""
        if value < low:
            return low
        if value > high:
            return high
        return value

    def _to_cell(self, x: float, y: float) -> tuple[int, int]:
        """Snap a millimetre position to the nearest grid cell indices."""
        col = round((x - self.bounds.min_x) / self.spacing)
        row = round((y - self.bounds.min_y) / self.spacing)
        return col, row

    def _to_position(self, col: int, row: int) -> tuple[float, float]:
        """Convert grid cell indices back to a millimetre position."""
        x = self.bounds.min_x + col * self.spacing
        y = self.bounds.min_y + row * self.spacing
        return x, y

    def _cell_in_bounds(self, col: int, row: int) -> bool:
        """Return True if a grid cell maps to a position inside the usable area."""
        x, y = self._to_position(col, row)
        return (
            self.bounds.min_x <= x <= self.bounds.max_x
            and self.bounds.min_y <= y <= self.bounds.max_y
        )

    def find_valid_position(
        self,
        component_ref: str,
        component_type: str,
        preferred_x: float,
        preferred_y: float,
    ) -> tuple[float, float]:
        """
        Find a free, in-bounds grid position near the preferred point.

        The preferred point is clamped into the usable rectangle and snapped
        to the grid. If that cell is already occupied, the search spirals
        outward ring by ring until a free in-bounds cell is found.

        Args:
            component_ref: Component reference (e.g. "R1"); used for context.
            component_type: Component type; used for context.
            preferred_x: Desired X coordinate in millimetres.
            preferred_y: Desired Y coordinate in millimetres.

        Returns:
            A ``(x, y)`` tuple of floats guaranteed to be inside the usable
            area and not previously recorded as occupied.
        """
        # Clamp the preferred point into the usable rectangle before snapping.
        clamped_x = self._clamp(preferred_x, self.bounds.min_x, self.bounds.max_x)
        clamped_y = self._clamp(preferred_y, self.bounds.min_y, self.bounds.max_y)
        start_col, start_row = self._to_cell(clamped_x, clamped_y)

        # Determine how far outward we might need to search (grid dimensions).
        max_cols = max(1, int(self.bounds.usable_width / self.spacing))
        max_rows = max(1, int(self.bounds.usable_height / self.spacing))
        max_radius = max_cols + max_rows

        # Spiral outward ring by ring looking for a free, in-bounds cell.
        for radius in range(0, max_radius + 1):
            for col, row in self._cells_at_radius(start_col, start_row, radius):
                if not self._cell_in_bounds(col, row):
                    continue
                if (col, row) in self._occupied:
                    continue
                self._occupied.add((col, row))
                x, y = self._to_position(col, row)
                return float(x), float(y)

        # Fallback: grid is fully occupied. Return the clamped centre-ish point,
        # still guaranteed to be inside the usable area.
        fallback_x, fallback_y = self._to_position(start_col, start_row)
        fallback_x = self._clamp(fallback_x, self.bounds.min_x, self.bounds.max_x)
        fallback_y = self._clamp(fallback_y, self.bounds.min_y, self.bounds.max_y)
        # Guard the guarantee even in the degenerate fallback case.
        if not validate_position(fallback_x, fallback_y, use_margins=True):
            fallback_x, fallback_y = self.bounds.min_x, self.bounds.min_y
        return float(fallback_x), float(fallback_y)

    def _cells_at_radius(self, center_col: int, center_row: int, radius: int):
        """
        Yield grid cells lying on the square ring at ``radius`` from the centre.

        Radius 0 yields only the centre cell.
        """
        if radius == 0:
            yield center_col, center_row
            return

        for d_col in range(-radius, radius + 1):
            for d_row in range(-radius, radius + 1):
                # Only cells on the ring perimeter (max distance == radius).
                if max(abs(d_col), abs(d_row)) != radius:
                    continue
                yield center_col + d_col, center_row + d_row
