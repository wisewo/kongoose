from collections.abc import Sequence

from kongoose.models import Position, TerrainType


class TerrainMap:
    def __init__(self, terrain_rows: Sequence[Sequence[str]]) -> None:
        if not terrain_rows:
            raise ValueError("terrain map must have at least one row")

        column_count = len(terrain_rows[0])
        if column_count == 0:
            raise ValueError("terrain map must have at least one column")

        if any(len(row) != column_count for row in terrain_rows):
            raise ValueError("all terrain rows must have the same number of columns")

        self._map = [list(row) for row in terrain_rows]
        self.rows = len(self._map)
        self.columns = column_count

    def get_terrain(self, position: Position) -> str:
        if not self._is_in_bounds(position):
            raise IndexError("position is outside the terrain map")
        return self._map[position.row][position.column]

    def can_enter(self, position: Position) -> bool:
        if not self._is_in_bounds(position):
            return False
        return self.get_terrain(position) != TerrainType.WALL

    def _is_in_bounds(self, position: Position) -> bool:
        return 0 <= position.row < self.rows and 0 <= position.column < self.columns
