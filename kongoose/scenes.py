from contextlib import contextmanager
from pathlib import Path

import pygame

from kongoose.models import MOVE_BLOCKED, Direction, Position, SoundCue, TerrainType

MAX_STAGE_COUNT = 4
HOP_DURATION = 0.18
HOP_SIZE_BONUS = 0.90
PLAYER_CELL_INSET = 0.50
MIN_TILE_SIZE = 24
TEXT_COLOR = (35, 45, 50)
MESSAGE_COLOR = (172, 72, 39)
HUD_OVERLAY_COLOR = (246, 250, 244, 224)
HUD_BORDER_COLOR = (182, 202, 185, 230)
PLAYING_HUD_HEIGHT = 86
ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
DEFAULT_BACKGROUND_COLOR = (242, 247, 241)
BIKE_FRAME_COUNT = 4
RUNNING_CREW_FRAME_COUNT = 4
RUNNING_CREW_RUNNER_COUNT = 8
RUNNING_CREW_FRAME_DURATION = 0.12
RUNNING_CREW_TILE_DURATION = 0.08
TURTLE_IMAGE_NAMES = {Direction.LEFT: "turtle_left", Direction.RIGHT: "turtle_right"}
STAR_FILLED_IMAGE = "star_filled"
STAR_EMPTY_IMAGE = "star_empty"
STAR_ICON_SIZE = 30
STAR_ICON_GAP = 5
MAIN_ACTION_LINES = ("Enter / Space: Stage Select", "Esc / Q: Quit")
FAILED_ACTION_LINES = ("R: Restart Stage", "S / B: Stage Select", "M / Esc: Main")
RESULT_ACTION_LINES = ("N: Next Stage", *FAILED_ACTION_LINES)
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
RUNNING_CREW_COLOR = (146, 80, 170)
TURTLE_COLOR = (72, 170, 120)
DIRECTION_KEYS = {
    pygame.K_UP: Direction.UP,
    pygame.K_DOWN: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT,
}
BACK_KEYS = (pygame.K_ESCAPE, pygame.K_b)
SPRITE_PROGRESS_OFFSETS = {
    Direction.UP: (0.0, -1.0),
    Direction.DOWN: (0.0, 1.0),
    Direction.LEFT: (-1.0, 0.0),
    Direction.RIGHT: (1.0, 0.0),
}


def _fonts(*sizes: int):
    return tuple(pygame.font.Font(None, size) for size in sizes)


def grid_top_for_focus(rows, cell_size, surface_height, focus_row):
    grid_height = cell_size * rows
    if rows <= 0 or grid_height <= surface_height:
        return 0
    focus_center_y = focus_row * cell_size + cell_size / 2
    desired_top = surface_height / 2 - focus_center_y
    return min(max(desired_top, surface_height - grid_height), 0)


def _blit_scaled_centered(surface, image, target_rect) -> None:
    scaled_rect = image.get_rect().fit(target_rect)
    size = max(1, scaled_rect.width), max(1, scaled_rect.height)
    scaled = pygame.transform.smoothscale(image, size)
    surface.blit(scaled, scaled_rect)


@contextmanager
def _clipped(surface, rect):
    previous_clip = surface.get_clip()
    surface.set_clip(rect)
    try:
        yield
    finally:
        surface.set_clip(previous_clip)


def _trim_transparent_margins(image):
    bounds = image.get_bounding_rect(1)
    if bounds.width <= 0 or bounds.height <= 0:
        return image
    return image.subsurface(bounds).copy()


Scene = object


class EmptyScene(Scene):
    def __init__(self, background_color=DEFAULT_BACKGROUND_COLOR) -> None:
        self._background_color = background_color
        self._game = None
        self._message = ""

    def enter(self, game) -> None:
        self._game = game

    def draw(self, surface) -> None:
        surface.fill(self._background_color)

    def update(self, dt: float) -> None:
        return None

    def set_message(self, message: str) -> None:
        self._message = message

    def _require_game(self):
        if self._game is None:
            raise RuntimeError("Scene has not entered a Game yet.")
        return self._game

    def _dispatch_key(self, event: object, *bindings) -> bool:
        if event.type != pygame.KEYDOWN:
            return False
        for keys, action in bindings:
            if event.key in keys:
                action()
                return True
        return False

    def _draw_text_screen(self, surface, title: str, lines: list[str]) -> None:
        body_font, y = self._begin_text_screen(surface, title)
        y = self._draw_centered_lines(surface, lines, y, body_font)
        self._draw_message(surface, y + 20, body_font)

    def _begin_text_screen(self, surface, title: str):
        surface.fill(self._background_color)
        title_font, body_font = _fonts(58, 32)
        self._draw_centered_text(surface, title, 96, title_font, TEXT_COLOR)
        return body_font, 170

    def _dispatch_end_scene_keys(self, event, include_next=False) -> None:
        game = self._require_game()
        bindings = [
            ((pygame.K_r,), game.restart_stage),
            ((pygame.K_s, pygame.K_b), game.open_stage_select),
            ((pygame.K_m, pygame.K_ESCAPE), game.return_to_main),
        ]
        if include_next:
            bindings.insert(0, ((pygame.K_n,), game.start_next_stage))
        self._dispatch_key(event, *bindings)

    def _draw_centered_text(self, surface, text: str, y: int, font, color) -> None:
        width, _height = surface.get_size()
        image = font.render(text, True, color)
        rect = image.get_rect(center=(width // 2, y))
        surface.blit(image, rect)

    def _draw_centered_lines(self, surface, lines, y, font, color=TEXT_COLOR):
        for line in lines:
            self._draw_centered_text(surface, line, y, font, color)
            y += 38
        return y

    def _draw_message(self, surface, y: int, font) -> None:
        if self._message:
            self._draw_centered_text(surface, self._message, y, font, MESSAGE_COLOR)

    def _get_asset_image(self, image_name: str):
        game = self._game
        if game is None:
            return None
        cached_image = game.resource_manager.get_image(image_name)
        if cached_image is not None:
            return cached_image
        image_path = ASSET_DIR / f"{image_name}.png"
        if not image_path.exists():
            return None
        image = pygame.image.load(str(image_path))
        game.resource_manager.register_image(image_name, image)
        return image

    def _draw_star_line(self, surface, label, stars, y, font, icon_size=STAR_ICON_SIZE):
        stars = max(0, min(3, stars))
        label_image = font.render(label, True, TEXT_COLOR)
        images = [
            self._get_asset_image(
                STAR_FILLED_IMAGE if index < stars else STAR_EMPTY_IMAGE
            )
            for index in range(3)
        ]
        gap = 10
        has_icons = all(images)
        stars_text = "*" * stars or "-"
        rating_width = (
            icon_size * 3 + STAR_ICON_GAP * 2 if has_icons else font.size(stars_text)[0]
        )
        left = (surface.get_width() - label_image.get_width() - gap - rating_width) // 2
        label_rect = label_image.get_rect(midleft=(left, y))
        surface.blit(label_image, label_rect)
        rating_left = label_rect.right + gap
        if has_icons:
            for index, image in enumerate(images):
                target = pygame.Rect(
                    rating_left + index * (icon_size + STAR_ICON_GAP),
                    y - icon_size // 2,
                    icon_size,
                    icon_size,
                )
                _blit_scaled_centered(surface, image, target)
            return
        rating_image = font.render(stars_text, True, TEXT_COLOR)
        surface.blit(rating_image, rating_image.get_rect(midleft=(rating_left, y)))


class MainScene(EmptyScene):
    def handle_event(self, event: object) -> None:
        game = self._require_game()
        self._dispatch_key(
            event,
            ((pygame.K_RETURN, pygame.K_SPACE), game.open_stage_select),
            ((pygame.K_ESCAPE, pygame.K_q), game.quit_game),
        )

    def draw(self, surface) -> None:
        progress = self._require_game().progress
        unlocked_count = sum(
            progress.is_stage_unlocked(stage_id)
            for stage_id in range(1, MAX_STAGE_COUNT + 1)
        )
        self._draw_text_screen(
            surface,
            "Kongoose",
            [
                "Campus crossing with Geon-goose",
                f"Unlocked stages: {unlocked_count}/{MAX_STAGE_COUNT}",
                "",
                *MAIN_ACTION_LINES,
            ],
        )


class StageSelectScene(EmptyScene):
    def handle_event(self, event: object) -> None:
        game = self._require_game()
        if self._dispatch_key(event, (BACK_KEYS, game.return_to_main)):
            return
        if event.type != pygame.KEYDOWN:
            return
        stage_id = event.key - pygame.K_0
        if 1 <= stage_id <= MAX_STAGE_COUNT:
            game.select_stage(stage_id)

    def draw(self, surface) -> None:
        progress = self._require_game().progress
        body_font, y = self._begin_text_screen(surface, "Stage Select")
        self._draw_centered_text(
            surface, "Choose a stage with number keys.", y, body_font, TEXT_COLOR
        )
        y += 76
        for stage_id in range(1, MAX_STAGE_COUNT + 1):
            status = "Unlocked" if progress.is_stage_unlocked(stage_id) else "Locked"
            self._draw_star_line(
                surface,
                f"{stage_id}: Stage {stage_id} [{status}] Best:",
                progress.get_best_stars(stage_id),
                y,
                body_font,
                24,
            )
            y += 38
        y += 38
        y = self._draw_centered_lines(
            surface, ("1-4: Select Stage", "Esc / B: Main"), y, body_font
        )
        self._draw_message(surface, y + 20, body_font)


class PlayingScene(EmptyScene):
    def __init__(self, background_color=DEFAULT_BACKGROUND_COLOR) -> None:
        super().__init__(background_color)
        self._hop_start_position: Position | None = None
        self._hop_end_position: Position | None = None
        self._hop_elapsed = 0.0

    def handle_event(self, event: object) -> None:
        if event.type != pygame.KEYDOWN:
            return
        game = self._require_game()
        if event.key in BACK_KEYS:
            game.open_stage_select()
            return
        direction = DIRECTION_KEYS.get(event.key)
        if direction is not None:
            stage = getattr(game, "current_stage", None)
            player = getattr(stage, "player", None)
            if self._hop_start_position is not None:
                terrain_map = getattr(stage, "terrain_map", None)
                if player is not None and terrain_map is not None:
                    target_position = player.position.moved(direction)
                    if not terrain_map.can_enter(target_position):
                        game._handle_move_result(MOVE_BLOCKED)
                return
            start_position = None if player is None else player.position
            game.move_player(direction)
            if (
                game.current_scene is self
                and player is not None
                and start_position != player.position
            ):
                self._hop_start_position = start_position
                self._hop_end_position = player.position
                self._hop_elapsed = 0.0

            if (
                game.current_scene is self
                and player is not None
                and start_position != player.position
            ):
                self._hop_start_position = start_position
                self._hop_end_position = player.position
                self._hop_elapsed = 0.0

    def update(self, dt: float) -> None:
        if self._hop_start_position is not None:
            self._hop_elapsed += dt
            if self._hop_elapsed >= HOP_DURATION:
                self._hop_start_position = None
                self._hop_end_position = None
                self._hop_elapsed = 0.0
                self._require_game().sound_manager.play(SoundCue.MOVE_SUCCESS)
        self._require_game().update_stage(dt)

    def draw(self, surface) -> None:
        game = self._require_game()
        stage_id = getattr(game, "current_stage_id", None)
        stage_text = "-" if stage_id is None else str(stage_id)
        elapsed_text = f"{game.timer.get_elapsed_time():.1f}s"
        stage = game.current_stage
        terrain_map = stage.terrain_map
        player = stage.player
        surface.fill(self._background_color)
        width, height = surface.get_size()
        title_font, body_font = _fonts(44, 26)
        grid_rect, cell_size = self._calculate_grid_layout(
            width, max(1, height - PLAYING_HUD_HEIGHT), terrain_map.rows,
            terrain_map.columns, player.position
        )
        grid_rect.move_ip(0, PLAYING_HUD_HEIGHT)
        self._draw_terrain_grid(surface, terrain_map, grid_rect, cell_size, stage_id)
        crews = getattr(stage, "running_crews", [])
        self._draw_running_crews(surface, crews, terrain_map, grid_rect, cell_size)
        for sprites, color, get_image, width_bonus in (
            (getattr(stage, "turtles", []), TURTLE_COLOR, self._get_turtle_image, 0.32),
            (getattr(stage, "bikes", []), BIKE_COLOR, self._get_bike_image, 0.4),
        ):
            self._draw_position_sprites(
                surface, sprites, grid_rect, cell_size, color, get_image, width_bonus
            )
        self._draw_player(surface, player, grid_rect, cell_size)
        self._draw_playing_hud(surface, title_font, body_font, stage_text, elapsed_text)

    def _draw_playing_hud(
        self, surface, title_font, body_font, stage_text, elapsed_text
    ) -> None:
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

    def _calculate_grid_layout(self, width, height, rows, columns, focus=None):
        cell_size = max(MIN_TILE_SIZE, width / columns)
        grid_width = max(width, round(cell_size * columns))
        grid_height = round(cell_size * rows)
        top = (
            0
            if focus is None
            else round(grid_top_for_focus(rows, cell_size, height, focus.row))
        )
        return pygame.Rect(0, top, grid_width, grid_height), cell_size

    def _draw_terrain_grid(
        self, surface, terrain_map, grid_rect, cell_size, stage_id=None
    ):
        for row in range(terrain_map.rows):
            for column in range(terrain_map.columns):
                position = Position(row=row, column=column)
                terrain = terrain_map.get_terrain(position)
                color = TERRAIN_STYLES[terrain]
                rect = self._cell_rect(grid_rect, cell_size, position)
                pygame.draw.rect(surface, color, rect)
                if terrain == TerrainType.GOAL and (
                    goal_image := self._get_goal_image(stage_id)
                ):
                    _blit_scaled_centered(surface, goal_image, rect)

    def _draw_running_crews(self, surface, crews, terrain, grid, cell_size):
        for crew in crews:
            if not 0 <= crew.row < terrain.rows:
                continue
            if self._draw_running_crew_runners(surface, crew, terrain, grid, cell_size):
                continue
            if crew.should_warn() and self._draw_running_crew_warning(
                surface, crew, terrain, grid, cell_size
            ):
                continue
            for column in range(terrain.columns):
                position = Position(row=crew.row, column=column)
                rect = self._cell_rect(grid, cell_size, position).inflate(
                    -cell_size * 0.22, -cell_size * 0.34
                )
                if crew.occupies(position):
                    pygame.draw.rect(surface, RUNNING_CREW_COLOR, rect, border_radius=4)
                elif crew.should_warn():
                    pygame.draw.rect(surface, RUNNING_CREW_COLOR, rect, 2, 4)

    def _draw_running_crew_warning(self, surface, crew, terrain, grid, cell_size):
        if (crew_image := self._get_running_crew_warning_image(crew)) is None:
            return False
        first = self._cell_rect(grid, cell_size, Position(crew.row, 0))
        last = self._cell_rect(grid, cell_size, Position(crew.row, terrain.columns - 1))
        target_rect = first.union(last).inflate(0, round(cell_size * 0.2))
        with _clipped(surface, grid):
            _blit_scaled_centered(surface, crew_image, target_rect)
        return True

    def _draw_running_crew_runners(self, surface, crew, terrain, grid, cell_size):
        runner_images = []
        columns = min(max(1, crew.columns), terrain.columns)
        elapsed_time = crew.elapsed_time - crew.warning_time
        if elapsed_time < 0.0:
            return False
        motion = elapsed_time / RUNNING_CREW_TILE_DURATION
        whole_tiles, progress = int(motion), motion % 1
        base_frame = int(elapsed_time / RUNNING_CREW_FRAME_DURATION)
        cutoff_motion = crew.active_duration / RUNNING_CREW_TILE_DURATION
        cutoff_tiles, cutoff_progress = int(cutoff_motion), cutoff_motion % 1
        min_tail_stream = (-1 if cutoff_progress > 0.0 else 0) - cutoff_tiles
        first_column = -1 if progress > 0.0 else 0
        for column in range(first_column, columns):
            stream_index = column - whole_tiles
            if elapsed_time >= crew.active_duration and stream_index < min_tail_stream:
                continue
            runner_image = self._get_running_crew_runner_image(stream_index, base_frame)
            if runner_image is None:
                return False
            runner_images.append((column, _trim_transparent_margins(runner_image)))
        if not runner_images:
            return False
        with _clipped(surface, grid):
            for column, runner_image in runner_images:
                cell = self._cell_rect(grid, cell_size, Position(crew.row, column))
                rect = cell.move(round(progress * cell_size), 0)
                target_rect = rect.inflate(
                    -round(cell_size * 0.08), -round(cell_size * 0.04)
                )
                _blit_scaled_centered(surface, runner_image, target_rect)
        return True

    def _draw_position_sprites(
        self, surface, sprites, grid, cell_size, color, get_image=None, width_bonus=0
    ):
        with _clipped(surface, grid):
            for sprite in sprites:
                for rect in self._get_sprite_draw_rects(sprite, grid, cell_size):
                    if (
                        get_image is not None
                        and (image := get_image(sprite)) is not None
                    ):
                        asset_rect = rect.inflate(round(cell_size * width_bonus), 0)
                        _blit_scaled_centered(surface, image, asset_rect)
                        continue
                    rect = rect.inflate(-cell_size * 0.24, -cell_size * 0.24)
                    pygame.draw.ellipse(surface, color, rect)

    def _draw_player(self, surface, player, grid_rect, cell_size: int) -> None:
        rect = self._get_player_draw_rect(
            grid_rect, cell_size, player.position, player.mounted_turtle
        )
        if image := self._get_player_image(player.facing_direction):
            _blit_scaled_centered(surface, image, rect)
            return
        pygame.draw.rect(surface, PLAYER_COLOR, rect, border_radius=8)

    def _get_player_draw_rect(self, grid, cell_size, position, carried=None):
        base_rect = self._cell_rect(grid, cell_size, position).inflate(
            -cell_size * PLAYER_CELL_INSET,
            -cell_size * PLAYER_CELL_INSET,
        )
        if carried is not None:
            return self._move_rect_by_sprite_progress(base_rect, carried, cell_size)
        if self._hop_start_position is None or self._hop_end_position is None:
            return base_rect
        progress = min(1.0, self._hop_elapsed / HOP_DURATION)
        start_rect = self._cell_rect(grid, cell_size, self._hop_start_position)
        end_rect = self._cell_rect(grid, cell_size, self._hop_end_position)
        center = (
            start_rect.centerx + (end_rect.centerx - start_rect.centerx) * progress,
            start_rect.centery + (end_rect.centery - start_rect.centery) * progress,
        )
        jump_scale = 1.0 + HOP_SIZE_BONUS * (1.0 - abs(progress * 2.0 - 1.0))
        draw_rect = base_rect.inflate(
            *(round(size * (jump_scale - 1.0)) for size in base_rect.size)
        )
        draw_rect.center = (round(center[0]), round(center[1]))
        return draw_rect

    def _get_sprite_draw_rects(self, sprite, grid_rect, cell_size: int):
        return [
            self._move_rect_by_sprite_progress(
                self._cell_rect(grid_rect, cell_size, position), sprite, cell_size
            )
            for position in sprite.get_positions()
        ]

    def _move_rect_by_sprite_progress(self, rect, sprite, cell_size: int):
        progress = getattr(sprite, "distance_progress", 0.0)
        x_offset, y_offset = SPRITE_PROGRESS_OFFSETS.get(
            getattr(sprite, "direction", ""), (0.0, 0.0)
        )
        return rect.move(
            round(x_offset * progress * cell_size),
            round(y_offset * progress * cell_size),
        )

    def _get_player_image(self, direction: str):
        if direction not in DIRECTION_KEYS.values():
            direction = Direction.DOWN
        return self._get_asset_image(f"player_goose_{direction}")

    def _get_bike_image(self, bike):
        frame = int(getattr(bike, "distance_progress", 0.0) * BIKE_FRAME_COUNT)
        image = self._get_asset_image(f"bike_frame_{frame % BIKE_FRAME_COUNT}")
        if (
            image is not None
            and getattr(bike, "direction", Direction.RIGHT) == Direction.LEFT
        ):
            return pygame.transform.flip(image, True, False)
        return image

    def _get_turtle_image(self, turtle):
        direction = getattr(turtle, "direction", Direction.RIGHT)
        return self._get_asset_image(TURTLE_IMAGE_NAMES.get(direction, "turtle_right"))

    def _get_goal_image(self, stage_id):
        if stage_id is not None:
            return self._get_asset_image(f"goal_stage_{stage_id}")

    def _get_running_crew_warning_image(self, crew):
        frame = (
            int(max(0.0, crew.elapsed_time) / RUNNING_CREW_FRAME_DURATION)
            % RUNNING_CREW_FRAME_COUNT
        )
        return self._get_asset_image(f"running_crew_warning_frame_{frame}")

    def _get_running_crew_runner_image(self, stream_index, base_frame):
        runner = stream_index % RUNNING_CREW_RUNNER_COUNT
        frame = (base_frame + stream_index) % RUNNING_CREW_FRAME_COUNT
        return self._get_asset_image(f"running_crew_runner_{runner}_frame_{frame}")

    def _cell_rect(self, grid_rect, cell_size: int, position: Position):
        left = grid_rect.left + round(position.column * cell_size)
        top = grid_rect.top + round(position.row * cell_size)
        right = grid_rect.left + round((position.column + 1) * cell_size)
        bottom = grid_rect.top + round((position.row + 1) * cell_size)
        return pygame.Rect(left, top, max(1, right - left), max(1, bottom - top))


class FailedScene(EmptyScene):
    def handle_event(self, event: object) -> None:
        self._dispatch_end_scene_keys(event)

    def draw(self, surface) -> None:
        reason = getattr(self._require_game(), "last_failure_reason", None)
        reason_text = "-" if reason is None else reason.name
        self._draw_text_screen(
            surface,
            "Stage Failed",
            [f"Reason: {reason_text}", "", *FAILED_ACTION_LINES],
        )


class ResultScene(EmptyScene):
    def handle_event(self, event: object) -> None:
        self._dispatch_end_scene_keys(event, include_next=True)

    def draw(self, surface) -> None:
        game = self._require_game()
        clear_time = getattr(game, "last_clear_time", None)
        stars = getattr(game, "last_stars", None)
        clear_time_text = "-" if clear_time is None else f"{clear_time:.1f}s"
        body_font, y = self._begin_text_screen(surface, "Stage Cleared")
        self._draw_centered_text(
            surface, f"Clear time: {clear_time_text}", y, body_font, TEXT_COLOR
        )
        y += 38
        if stars is None:
            self._draw_centered_text(surface, "Stars: -", y, body_font, TEXT_COLOR)
        else:
            self._draw_star_line(surface, "Stars:", stars, y, body_font)
        y += 76
        self._draw_centered_lines(surface, RESULT_ACTION_LINES, y, body_font)
