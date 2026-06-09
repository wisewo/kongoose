import pygame

from kongoose.models import Direction, Position, TerrainType

HOP_DURATION, HOP_SIZE_BONUS, HOP_HEIGHT = 0.18, 0.08, 0.22
PLAYER_CELL_INSET = 0.25
MIN_TILE_SIZE, PLAYING_HUD_HEIGHT = 24, 86
TEXT_COLOR = (35, 45, 50)
HUD_OVERLAY_COLOR = (246, 250, 244, 224)
HUD_BORDER_COLOR = (182, 202, 185, 230)
DEFAULT_BACKGROUND_COLOR = (242, 247, 241)
BIKE_FRAME_COUNT = STUDENT_CROWD_WARNING_FRAME_COUNT = 4
STUDENT_CROWD_ACTIVE_FRAME_COUNT = 12
STUDENT_CROWD_FRAME_DURATION = 0.12
TURTLE_IMAGE_NAMES = {Direction.LEFT: "turtle_left", Direction.RIGHT: "turtle_right"}
TERRAIN_STYLES = {
    TerrainType.START: (176, 224, 166),
    TerrainType.LAND: (231, 222, 178),
    TerrainType.SAFE: (205, 234, 198),
    TerrainType.RIVER: (80, 155, 210),
    TerrainType.WALL: (92, 96, 105),
    TerrainType.GOAL: (245, 205, 92),
}
PLAYER_COLOR = (240, 142, 74)
BIKE_COLOR = (210, 66, 70)
STUDENT_CROWD_COLOR = (146, 80, 170)
TURTLE_COLOR = (72, 170, 120)
SPRITE_PROGRESS_OFFSETS = {
    Direction.UP: (0.0, -1.0),
    Direction.DOWN: (0.0, 1.0),
    Direction.LEFT: (-1.0, 0.0),
    Direction.RIGHT: (1.0, 0.0),
}


def blit_scaled_centered(surface, image, target_rect) -> None:
    scaled_rect = image.get_rect().fit(target_rect)
    size = max(1, scaled_rect.width), max(1, scaled_rect.height)
    scaled = pygame.transform.smoothscale(image, size)
    surface.blit(scaled, scaled_rect)


def trim_transparent_margins(image):
    bounds = image.get_bounding_rect(1)
    return (
        image
        if bounds.width <= 0 or bounds.height <= 0
        else image.subsurface(bounds).copy()
    )


class StageRenderer:
    def __init__(self, get_asset_image) -> None:
        self._get_asset_image = get_asset_image

    def draw(
        self,
        surface,
        stage,
        stage_id,
        elapsed_text,
        background_color=DEFAULT_BACKGROUND_COLOR,
        hop_state=None,
        camera_focus=None,
    ) -> None:
        terrain_map, player = stage.terrain_map, stage.player
        surface.fill(background_color)
        width, height = surface.get_size()
        title_font = pygame.font.Font(None, 44)
        body_font = pygame.font.Font(None, 26)
        grid, cell_size = self.calculate_grid_layout(
            width,
            max(1, height - PLAYING_HUD_HEIGHT),
            terrain_map.rows,
            terrain_map.columns,
            camera_focus if camera_focus is not None else player.position,
        )
        grid.move_ip(0, PLAYING_HUD_HEIGHT)
        self.draw_terrain_grid(surface, terrain_map, grid, cell_size, stage_id)
        self.draw_student_crowds(
            surface, stage.student_crowds, terrain_map, grid, cell_size
        )
        for sprites, style in (
            (stage.turtles, (TURTLE_COLOR, self.turtle_image, 0.32)),
            (stage.bikes, (BIKE_COLOR, self.bike_image, 0.4)),
        ):
            self.draw_position_sprites(
                surface, sprites, grid, cell_size, style, terrain_map.columns
            )
        hop_start, _hop_end, hop_elapsed = hop_state or (None, None, 0.0)
        player_rect = self.player_draw_rect(
            grid,
            cell_size,
            player.position,
            player.mounted_turtle,
            hop_state,
            terrain_map.get_terrain(player.position),
        )
        image = self.player_image(
            player.facing_direction, hop_elapsed, hop_start is not None
        )
        if image:
            blit_scaled_centered(surface, trim_transparent_margins(image), player_rect)
        else:
            pygame.draw.rect(surface, PLAYER_COLOR, player_rect, border_radius=8)
        self.draw_playing_hud(
            surface, title_font, body_font, str(stage_id), elapsed_text
        )

    def draw_playing_hud(
        self, surface, title_font, body_font, stage_text, elapsed_text
    ):
        hud_rect = pygame.Rect(0, 0, surface.get_width(), PLAYING_HUD_HEIGHT)
        pygame.draw.rect(surface, HUD_OVERLAY_COLOR, hud_rect)
        pygame.draw.line(
            surface, HUD_BORDER_COLOR, hud_rect.bottomleft, hud_rect.bottomright
        )
        title_image = title_font.render(f"Stage {stage_text}", True, TEXT_COLOR)
        surface.blit(title_image, (18, 12))
        for text, position in (
            (f"Elapsed: {elapsed_text}", (20, 54)),
            ("Arrows: Move   Esc / B: Stage Select", (220, 54)),
        ):
            surface.blit(body_font.render(text, True, TEXT_COLOR), position)

    def calculate_grid_layout(self, width, height, rows, columns, focus=None):
        columns = max(1, columns)
        cell_size = max(MIN_TILE_SIZE, width / columns)
        grid_width = round((rows + columns) * cell_size / 2)
        grid_height = round((rows + columns) * cell_size / 4)
        origin_x = round((width - grid_width) / 2 + rows * cell_size / 2)
        top = min(0, round((height - grid_height) / 2))
        if focus is not None:
            origin_x = round(width / 2 - (focus.column - focus.row) * cell_size / 2)
            top = round(height / 2 - (focus.column + focus.row + 1) * cell_size / 4)
        if grid_width > width:
            min_origin = width - columns * cell_size / 2
            origin_x = round(min(max(origin_x, min_origin), rows * cell_size / 2))
        if grid_height > height:
            top = round(min(max(top, height - grid_height), 0))
        return pygame.Rect(origin_x, top, grid_width, grid_height), cell_size

    def draw_terrain_grid(self, surface, terrain_map, grid, cell_size, stage_id=None):
        for row in range(terrain_map.rows):
            for column in range(terrain_map.columns):
                position = Position(row=row, column=column)
                terrain = terrain_map.get_terrain(position)
                rect = self.cell_rect(grid, cell_size, position)
                pygame.draw.polygon(
                    surface,
                    TERRAIN_STYLES[terrain],
                    self.tile_points(grid, cell_size, position),
                )
                if terrain == TerrainType.GOAL and (
                    goal_image := self.goal_image(stage_id)
                ):
                    blit_scaled_centered(surface, goal_image, rect)

    def draw_student_crowds(self, surface, crowds, terrain, grid, cell_size):
        for crowd in crowds:
            if not 0 <= crowd.row < terrain.rows:
                continue
            if crowd.is_active() and self._draw_student_crowd_active(
                surface, crowd, terrain, grid, cell_size
            ):
                continue
            if crowd.should_warn() and self._draw_student_crowd_warning(
                surface, crowd, terrain, grid, cell_size
            ):
                continue
            self._draw_student_crowd_blocks(surface, crowd, terrain, grid, cell_size)

    def _draw_student_crowd_blocks(self, surface, crowd, terrain, grid, cell_size):
        for column in range(terrain.columns):
            position = Position(row=crowd.row, column=column)
            rect = self.cell_rect(grid, cell_size, position).inflate(
                -cell_size * 0.22, -cell_size * 0.34
            )
            if crowd.occupies(position):
                pygame.draw.rect(surface, STUDENT_CROWD_COLOR, rect, border_radius=4)
            elif crowd.should_warn():
                pygame.draw.rect(surface, STUDENT_CROWD_COLOR, rect, 2, 4)

    def _draw_student_crowd_warning(self, surface, crowd, terrain, grid, cell_size):
        if (crowd_image := self.student_crowd_warning_image(crowd)) is None:
            return False
        first = self.cell_rect(grid, cell_size, Position(crowd.row, 0))
        last = self.cell_rect(grid, cell_size, Position(crowd.row, terrain.columns - 1))
        target = first.union(last).inflate(0, round(cell_size * 0.2))
        blit_scaled_centered(surface, crowd_image, target)
        return True

    def _draw_student_crowd_active(self, surface, crowd, terrain, grid, cell_size):
        if (crowd_image := self.student_crowd_active_image(crowd)) is None:
            return False
        first = self.cell_rect(grid, cell_size, Position(crowd.row, 0))
        last = self.cell_rect(grid, cell_size, Position(crowd.row, terrain.columns - 1))
        blit_scaled_centered(surface, crowd_image, first.union(last))
        return True

    def draw_position_sprites(self, surface, sprites, grid, cell_size, style, columns):
        color, get_image, width_bonus = style
        for sprite in sprites:
            for rect in self.sprite_draw_rects(sprite, grid, cell_size, columns):
                if get_image is not None and (image := get_image(sprite)) is not None:
                    blit_scaled_centered(
                        surface, image, rect.inflate(round(cell_size * width_bonus), 0)
                    )
                    continue
                pygame.draw.ellipse(
                    surface,
                    color,
                    rect.inflate(-cell_size * 0.24, -cell_size * 0.24),
                )

    def player_draw_rect(
        self,
        grid,
        cell_size,
        position,
        carried=None,
        hop_state=None,
        terrain_type=None,
    ):
        hop_start, hop_end, hop_elapsed = hop_state or (None, None, 0.0)
        cell_rect = self.cell_rect(grid, cell_size, position)
        base_rect = cell_rect.inflate(
            -round(cell_rect.width * PLAYER_CELL_INSET),
            -round(cell_rect.height * PLAYER_CELL_INSET),
        )
        if hop_start is None or hop_end is None:
            if carried is not None:
                return self.move_rect_by_sprite_progress(base_rect, carried, cell_size)
            return base_rect
        progress = min(1.0, hop_elapsed / HOP_DURATION)
        arc = 4.0 * progress * (1.0 - progress)
        move_progress = progress * progress * (3.0 - 2.0 * progress)
        if position == hop_start and position != hop_end:
            move_progress = 0.35 * arc
        start_rect = self.cell_rect(grid, cell_size, hop_start)
        end_rect = self.cell_rect(grid, cell_size, hop_end)
        center = (
            start_rect.centerx
            + (end_rect.centerx - start_rect.centerx) * move_progress,
            start_rect.centery
            + (end_rect.centery - start_rect.centery) * move_progress
            - arc * cell_size * HOP_HEIGHT,
        )
        jump_scale = 1.0 + HOP_SIZE_BONUS * arc
        draw_rect = base_rect.inflate(
            *(round(size * (jump_scale - 1.0)) for size in base_rect.size)
        )
        draw_rect.center = (round(center[0]), round(center[1]))
        return draw_rect

    def sprite_draw_rects(self, sprite, grid, cell_size: int, columns=None):
        if self.is_crossing_map_edge(sprite, columns):
            return []
        return [
            self.move_rect_by_sprite_progress(
                self.cell_rect(grid, cell_size, sprite.position),
                sprite,
                cell_size,
                columns,
            )
        ]

    def is_crossing_map_edge(self, sprite, columns) -> bool:
        direction = getattr(sprite, "direction", "")
        progress = getattr(sprite, "distance_progress", 0.0)
        return (
            columns is not None
            and progress >= 0.5
            and direction in SPRITE_PROGRESS_OFFSETS
            and not 0 <= sprite.position.moved(direction).column < columns
        )

    def move_rect_by_sprite_progress(self, rect, sprite, cell_size: int, columns=None):
        direction = getattr(sprite, "direction", "")
        progress = getattr(sprite, "distance_progress", 0.0)
        return self.move_rect_by_grid_progress(rect, direction, progress, cell_size)

    def move_rect_by_grid_progress(self, rect, direction, progress, cell_size):
        column_offset, row_offset = SPRITE_PROGRESS_OFFSETS.get(direction, (0.0, 0.0))
        return rect.move(
            round((column_offset - row_offset) * progress * cell_size / 2),
            round((column_offset + row_offset) * progress * cell_size / 4),
        )

    def player_image(self, direction: str, hop_elapsed=0.0, is_hopping=False):
        if direction not in (
            Direction.UP,
            Direction.DOWN,
            Direction.LEFT,
            Direction.RIGHT,
        ):
            direction = Direction.DOWN
        progress = hop_elapsed / HOP_DURATION if is_hopping else 0
        frame = min(2, max(0, int(progress * 3)))
        image = self._get_asset_image(f"player_goose_{direction}_{frame}")
        return image or self._get_asset_image(f"player_goose_{direction}")

    def bike_image(self, bike):
        frame = int(getattr(bike, "distance_progress", 0.0) * BIKE_FRAME_COUNT)
        image = self._get_asset_image(f"bike_frame_{frame % BIKE_FRAME_COUNT}")
        direction = getattr(bike, "direction", Direction.RIGHT)
        if image is not None and direction == Direction.LEFT:
            return pygame.transform.flip(image, True, False)
        return image

    def turtle_image(self, turtle):
        direction = getattr(turtle, "direction", Direction.RIGHT)
        return self._get_asset_image(TURTLE_IMAGE_NAMES.get(direction, "turtle_right"))

    def goal_image(self, stage_id):
        return self._get_asset_image(f"goal_stage_{stage_id}")

    def student_crowd_warning_image(self, crowd):
        frame = (
            int(max(0.0, crowd.elapsed_time) / STUDENT_CROWD_FRAME_DURATION)
            % STUDENT_CROWD_WARNING_FRAME_COUNT
        )
        return self._get_asset_image(f"student_crowd_warning_frame_{frame}")

    def student_crowd_active_image(self, crowd):
        elapsed = max(0.0, crowd.elapsed_time - crowd.warning_time)
        frame = (
            int(elapsed / STUDENT_CROWD_FRAME_DURATION)
            % STUDENT_CROWD_ACTIVE_FRAME_COUNT
        )
        return self._get_asset_image(f"student_crowd_active_frame_{frame}")

    def cell_rect(self, grid, cell_size: int, position: Position):
        rect = pygame.Rect(0, 0, round(cell_size), round(cell_size / 2))
        rect.center = (
            grid.left + round((position.column - position.row) * cell_size / 2),
            grid.top + round((position.column + position.row + 1) * cell_size / 4),
        )
        return rect

    def tile_points(self, grid, cell_size, position):
        rect = self.cell_rect(grid, cell_size, position)
        return rect.midtop, rect.midright, rect.midbottom, rect.midleft
