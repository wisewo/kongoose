from src.models import Position
from src.models import TerrainType as T


class TerrainMap:
    def __init__(self, terrain_rows) -> None:
        if not terrain_rows:
            raise ValueError("terrain map must have at least one row")
        column_count = len(terrain_rows[0])
        if column_count == 0:
            raise ValueError("terrain map must have at least one column")
        if any(len(row) != column_count for row in terrain_rows):
            raise ValueError("all terrain rows must have the same number of columns")
        self._map = [list(row) for row in terrain_rows]
        self.rows, self.columns = len(self._map), column_count

    def get_terrain(self, position: Position) -> str:
        if not self._is_in_bounds(position):
            raise IndexError("position is outside the terrain map")
        return self._map[position.row][position.column]

    def can_enter(self, position: Position) -> bool:
        return self._is_in_bounds(position) and self.get_terrain(position) != T.WALL

    def _is_in_bounds(self, position: Position) -> bool:
        return 0 <= position.row < self.rows and 0 <= position.column < self.columns
