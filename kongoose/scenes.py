from pathlib import Path

from kongoose.models import MOVE_BLOCKED, Direction, Position, SoundCue, TerrainType

MAX_STAGE_COUNT = 4
HOP_DURATION = 0.18
HOP_SIZE_BONUS = 0.90
PLAYER_CELL_INSET = 0.50
CAMERA_TILE_SIZE = 56
MIN_TILE_SIZE = 24
TEXT_COLOR = (35, 45, 50)
MUTED_TEXT_COLOR = (95, 106, 112)
MESSAGE_COLOR = (172, 72, 39)
HUD_OVERLAY_COLOR = (246, 250, 244, 224)
HUD_BORDER_COLOR = (182, 202, 185, 230)
HUD_BOX_PADDING = 8
ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
DEFAULT_BACKGROUND_COLOR = (242, 247, 241)
PLAYER_IMAGE_DIRECTIONS = {
    Direction.UP,
    Direction.DOWN,
    Direction.LEFT,
    Direction.RIGHT,
}
BIKE_FRAME_NAMES = tuple(f"bike_frame_{index}" for index in range(4))
RUNNING_CREW_WARNING_FRAME_NAMES = tuple(
    f"running_crew_warning_frame_{index}" for index in range(4)
)
RUNNING_CREW_RUNNER_FRAME_NAMES = tuple(
    tuple(
        f"running_crew_runner_{runner_index}_frame_{frame_index}"
        for frame_index in range(4)
    )
    for runner_index in range(8)
)
RUNNING_CREW_FRAME_DURATION = 0.12
RUNNING_CREW_TILE_DURATION = 0.24
TURTLE_IMAGE_NAMES = {
    Direction.LEFT: "turtle_left",
    Direction.RIGHT: "turtle_right",
}
STAR_FILLED_IMAGE = "star_filled"
STAR_EMPTY_IMAGE = "star_empty"
STAR_ICON_SIZE = 30
STAR_ICON_GAP = 5
MAIN_ACTION_LINES = ("Enter / Space: Stage Select", "Esc / Q: Quit")
FAILED_ACTION_LINES = ("R: Restart Stage", "S / B: Stage Select", "M / Esc: Main")
RESULT_ACTION_LINES = ("N: Next Stage", *FAILED_ACTION_LINES)
TERRAIN_STYLES = {
    TerrainType.START: ((176, 224, 166), "S"),
    TerrainType.LAND: ((231, 222, 178), ""),
    TerrainType.SAFE: ((205, 234, 198), ""),
    TerrainType.RIVER: ((80, 155, 210), "RIVER"),
    TerrainType.WALL: ((92, 96, 105), "WALL"),
    TerrainType.GOAL: ((245, 205, 92), "GOAL"),
}

PLAYER_COLOR = (240, 142, 74)
BIKE_COLOR = (210, 66, 70)
RUNNING_CREW_COLOR = (146, 80, 170)
TURTLE_COLOR = (72, 170, 120)
ACTOR_TEXT_COLOR = (255, 255, 255)


def _pygame():
    import pygame

    return pygame


class Scene:
    def enter(self, game) -> None:
        return None

    def handle_event(self, event: object) -> None:
        return None

    def update(self, dt: float) -> None:
        return None

    def draw(self, surface) -> None:
        return None


class EmptyScene(Scene):
    def __init__(self, background_color=DEFAULT_BACKGROUND_COLOR) -> None:
        self._background_color = background_color
        self._game = None
        self._message = ""

    def enter(self, game) -> None:
        self._game = game

    def draw(self, surface) -> None:
        surface.fill(self._background_color)

    def set_message(self, message: str) -> None:
        self._message = message

    def _require_game(self):
        if self._game is None:
            raise RuntimeError("Scene has not entered a Game yet.")
        return self._game

    def _dispatch_key(self, event: object, actions: dict[int, object]) -> bool:
        pygame = _pygame()
        if event.type != pygame.KEYDOWN:
            return False
        action = actions.get(event.key)
        if action is None:
            return False
        action()
        return True

    def _draw_text_screen(self, surface, title: str, lines: list[str]) -> None:
        pygame = _pygame()
        surface.fill(self._background_color)
        width, _height = surface.get_size()
        title_font = pygame.font.Font(None, 58)
        body_font = pygame.font.Font(None, 32)
        message_font = pygame.font.Font(None, 26)

        y = 96
        title_image = title_font.render(title, True, TEXT_COLOR)
        title_rect = title_image.get_rect(center=(width // 2, y))
        surface.blit(title_image, title_rect)

        y += 74
        for line in lines:
            color = MUTED_TEXT_COLOR if line.startswith("  ") else TEXT_COLOR
            image = body_font.render(line, True, color)
            rect = image.get_rect(center=(width // 2, y))
            surface.blit(image, rect)
            y += 38

        if self._message:
            message_image = message_font.render(self._message, True, MESSAGE_COLOR)
            message_rect = message_image.get_rect(center=(width // 2, y + 20))
            surface.blit(message_image, message_rect)

    def _draw_centered_text(self, surface, text: str, y: int, font, color) -> None:
        width, _height = surface.get_size()
        image = font.render(text, True, color)
        rect = image.get_rect(center=(width // 2, y))
        surface.blit(image, rect)

    def _get_asset_image(self, image_name: str):
        pygame = _pygame()
        game = self._require_game()
        cached_image = game.resource_manager.get_image(image_name)
        if cached_image is not None:
            return cached_image

        image_path = ASSET_DIR / f"{image_name}.png"
        if not image_path.exists():
            return None

        image = pygame.image.load(str(image_path))
        game.resource_manager.register_image(image_name, image)
        return image

    def _draw_star_rating(
        self, surface, stars: int, center: tuple[int, int], icon_size: int
    ) -> bool:
        pygame = _pygame()
        images = []
        for index in range(3):
            image_name = STAR_FILLED_IMAGE if index < stars else STAR_EMPTY_IMAGE
            image = self._get_asset_image(image_name)
            if image is None:
                return False
            images.append(image)

        total_width = icon_size * 3 + STAR_ICON_GAP * 2
        left = center[0] - total_width // 2
        for index, image in enumerate(images):
            scaled = pygame.transform.smoothscale(image, (icon_size, icon_size))
            x = left + index * (icon_size + STAR_ICON_GAP)
            rect = scaled.get_rect(midleft=(x, center[1]))
            surface.blit(scaled, rect)
        return True

    def _draw_star_line(
        self,
        surface,
        label: str,
        stars: int,
        y: int,
        font,
        icon_size: int = STAR_ICON_SIZE,
    ) -> None:
        label_image = font.render(label, True, TEXT_COLOR)
        gap = 10
        rating_width = icon_size * 3 + STAR_ICON_GAP * 2
        left = (surface.get_width() - label_image.get_width() - gap - rating_width) // 2
        rating_center = (left + label_image.get_width() + gap + rating_width // 2, y)
        if self._draw_star_rating(
            surface, max(0, min(3, stars)), rating_center, icon_size
        ):
            surface.blit(label_image, label_image.get_rect(midleft=(left, y)))
            return

        stars_text = "-" if stars == 0 else "*" * stars
        rating_image = font.render(stars_text, True, TEXT_COLOR)
        width, _height = surface.get_size()
        left = (width - label_image.get_width() - gap - rating_image.get_width()) // 2
        label_rect = label_image.get_rect(midleft=(left, y))
        rating_rect = rating_image.get_rect(midleft=(label_rect.right + gap, y))
        surface.blit(label_image, label_rect)
        surface.blit(rating_image, rating_rect)

    def _is_stage_unlocked(self, stage_id: int) -> bool:
        return self._require_game().progress.is_stage_unlocked(stage_id)

    def _get_best_stars(self, stage_id: int) -> int:
        return self._require_game().progress.get_best_stars(stage_id)

    def _get_elapsed_time(self) -> float:
        return self._require_game().timer.get_elapsed_time()


class MainScene(EmptyScene):
    def handle_event(self, event: object) -> None:
        pygame = _pygame()
        game = self._require_game()
        actions = dict.fromkeys(
            (pygame.K_RETURN, pygame.K_SPACE), game.open_stage_select
        )
        actions.update(dict.fromkeys((pygame.K_ESCAPE, pygame.K_q), game.quit_game))
        self._dispatch_key(event, actions)

    def draw(self, surface) -> None:
        unlocked_count = sum(
            1
            for stage_id in range(1, MAX_STAGE_COUNT + 1)
            if self._is_stage_unlocked(stage_id)
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
        pygame = _pygame()
        game = self._require_game()
        actions = dict.fromkeys((pygame.K_ESCAPE, pygame.K_b), game.return_to_main)
        if self._dispatch_key(event, actions):
            return

        if event.type != pygame.KEYDOWN:
            return

        stage_id = event.key - pygame.K_0
        if 1 <= stage_id <= MAX_STAGE_COUNT:
            game.select_stage(stage_id)

    def draw(self, surface) -> None:
        pygame = _pygame()
        surface.fill(self._background_color)
        title_font = pygame.font.Font(None, 58)
        body_font = pygame.font.Font(None, 32)
        message_font = pygame.font.Font(None, 26)

        y = 96
        self._draw_centered_text(surface, "Stage Select", y, title_font, TEXT_COLOR)
        y += 74
        self._draw_centered_text(
            surface, "Choose a stage with number keys.", y, body_font, TEXT_COLOR
        )
        y += 76

        for stage_id in range(1, MAX_STAGE_COUNT + 1):
            status = "Unlocked" if self._is_stage_unlocked(stage_id) else "Locked"
            best_stars = self._get_best_stars(stage_id)
            self._draw_star_line(
                surface,
                f"{stage_id}: Stage {stage_id} [{status}] Best:",
                best_stars,
                y,
                body_font,
                24,
            )
            y += 38

        y += 38
        for line in ("1-4: Select Stage", "Esc / B: Main"):
            self._draw_centered_text(surface, line, y, body_font, TEXT_COLOR)
            y += 38

        if self._message:
            self._draw_centered_text(
                surface, self._message, y + 20, message_font, MESSAGE_COLOR
            )


class PlayingScene(EmptyScene):
    def __init__(self, background_color=DEFAULT_BACKGROUND_COLOR) -> None:
        super().__init__(background_color)
        self._hop_start_position: Position | None = None
        self._hop_end_position: Position | None = None
        self._hop_elapsed = 0.0

    def handle_event(self, event: object) -> None:
        pygame = _pygame()
        if event.type != pygame.KEYDOWN:
            return

        game = self._require_game()
        if event.key in (pygame.K_ESCAPE, pygame.K_b):
            game.open_stage_select()
            return

        direction = {
            pygame.K_UP: Direction.UP,
            pygame.K_DOWN: Direction.DOWN,
            pygame.K_LEFT: Direction.LEFT,
            pygame.K_RIGHT: Direction.RIGHT,
        }.get(event.key)
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
        pygame = _pygame()
        game = self._require_game()
        stage_id = getattr(game, "current_stage_id", None)
        stage_text = "-" if stage_id is None else str(stage_id)
        elapsed_text = f"{self._get_elapsed_time():.1f}s"
        play_message = getattr(game, "last_play_message", "")

        if play_message:
            self.set_message(play_message)

        stage = game.current_stage
        terrain_map = stage.terrain_map
        player = stage.player

        surface.fill(self._background_color)
        width, height = surface.get_size()
        title_font = pygame.font.Font(None, 44)
        body_font = pygame.font.Font(None, 26)
        small_font = pygame.font.Font(None, 20)

        grid_rect, cell_size = self._calculate_grid_layout(
            width, height, terrain_map.rows, terrain_map.columns, player.position
        )
        self._draw_terrain_grid(surface, terrain_map, grid_rect, cell_size, small_font)
        crews = getattr(stage, "running_crews", [])
        self._draw_running_crews(
            surface, crews, terrain_map, grid_rect, cell_size, small_font
        )
        for sprites, color, label in (
            (getattr(stage, "turtles", []), TURTLE_COLOR, "T"),
            (getattr(stage, "bikes", []), BIKE_COLOR, "B"),
        ):
            self._draw_position_sprites(
                surface, sprites, grid_rect, cell_size, color, label, small_font
            )
        self._draw_player(surface, player, grid_rect, cell_size, small_font)
        self._draw_playing_hud(
            surface, title_font, body_font, stage_text, elapsed_text, play_message
        )

    def _draw_playing_hud(
        self, surface, title_font, body_font, stage_text, elapsed_text, play_message
    ) -> None:
        width = surface.get_width()

        title_image = title_font.render(f"Stage {stage_text}", True, TEXT_COLOR)
        elapsed_image = body_font.render(f"Elapsed: {elapsed_text}", True, TEXT_COLOR)
        status_text = "Arrows: Move   Esc / B: Stage Select"
        status_image = body_font.render(status_text, True, TEXT_COLOR)

        images = [
            (title_image, title_image.get_rect(topleft=(18, 12))),
            (
                elapsed_image,
                elapsed_image.get_rect(topright=(max(18, width - 18), 22)),
            ),
            (status_image, status_image.get_rect(topleft=(20, 58))),
        ]

        if play_message:
            message_image = body_font.render(play_message, True, MESSAGE_COLOR)
            images.append((message_image, message_image.get_rect(topleft=(20, 84))))

        for _image, rect in images:
            self._draw_hud_box(surface, rect.inflate(HUD_BOX_PADDING * 2, 6))
        for image, rect in images:
            surface.blit(image, rect)

    def _draw_hud_box(self, surface, rect) -> None:
        pygame = _pygame()
        box = pygame.Surface(rect.size, pygame.SRCALPHA)
        box_rect = box.get_rect()
        pygame.draw.rect(box, HUD_OVERLAY_COLOR, box_rect, border_radius=6)
        pygame.draw.rect(box, HUD_BORDER_COLOR, box_rect, 1, border_radius=6)
        surface.blit(box, rect)

    def _calculate_grid_layout(
        self, surface_width, surface_height, rows, columns, focus_position=None
    ):
        pygame = _pygame()
        top_margin = 0
        bottom_margin = 0
        available_height = surface_height - top_margin - bottom_margin
        cell_size = max(MIN_TILE_SIZE, surface_width / columns)
        grid_width = max(surface_width, round(cell_size * columns))
        grid_height = round(cell_size * rows)
        left = 0
        if grid_height <= available_height or focus_position is None:
            top = top_margin
        else:
            viewport_bottom = surface_height - bottom_margin
            focus_center_y = focus_position.row * cell_size + cell_size / 2
            desired_top = top_margin + available_height / 2 - focus_center_y
            top = round(
                min(max(desired_top, viewport_bottom - grid_height), top_margin)
            )
        return pygame.Rect(left, top, grid_width, grid_height), cell_size

    def _draw_terrain_grid(
        self, surface, terrain_map, grid_rect, cell_size: int, font
    ) -> None:
        pygame = _pygame()
        for row in range(terrain_map.rows):
            for column in range(terrain_map.columns):
                position = Position(row=row, column=column)
                terrain = terrain_map.get_terrain(position)
                color, label = TERRAIN_STYLES[terrain]
                rect = self._cell_rect(grid_rect, cell_size, position)
                pygame.draw.rect(surface, color, rect)
                self._draw_centered_label(surface, rect, label, font, TEXT_COLOR)

    def _draw_running_crews(
        self, surface, running_crews: list, terrain_map, grid_rect, cell_size: int, font
    ) -> None:
        pygame = _pygame()
        for crew in running_crews:
            if not 0 <= crew.row < terrain_map.rows:
                continue
            if self._draw_running_crew_sprite(
                surface, crew, terrain_map, grid_rect, cell_size
            ):
                continue
            for column in range(terrain_map.columns):
                position = Position(row=crew.row, column=column)
                rect = self._cell_rect(grid_rect, cell_size, position).inflate(
                    -cell_size * 0.22, -cell_size * 0.34
                )
                if crew.occupies(position):
                    pygame.draw.rect(surface, RUNNING_CREW_COLOR, rect, border_radius=4)
                    self._draw_centered_label(
                        surface, rect, "R", font, ACTOR_TEXT_COLOR
                    )
                elif crew.should_warn():
                    pygame.draw.rect(surface, RUNNING_CREW_COLOR, rect, 2, 4)

    def _draw_running_crew_sprite(
        self, surface, crew, terrain_map, grid_rect, cell_size: int
    ) -> bool:
        if crew.is_active():
            return self._draw_running_crew_runners(
                surface, crew, terrain_map, grid_rect, cell_size
            )
        if crew.should_warn():
            return self._draw_running_crew_warning(
                surface, crew, terrain_map, grid_rect, cell_size
            )
        return False

    def _draw_running_crew_warning(
        self, surface, crew, terrain_map, grid_rect, cell_size: int
    ) -> bool:
        pygame = _pygame()
        crew_image = self._get_running_crew_warning_image(crew)
        if crew_image is None:
            return False

        columns = terrain_map.columns
        start_rect = self._cell_rect(grid_rect, cell_size, Position(crew.row, 0))
        end_rect = self._cell_rect(
            grid_rect, cell_size, Position(crew.row, columns - 1)
        )
        row_rect = start_rect.union(end_rect)
        target_rect = row_rect.inflate(0, round(cell_size * 0.2))
        scale = min(
            target_rect.width / crew_image.get_width(),
            target_rect.height / crew_image.get_height(),
        )
        sprite_size = (
            max(1, int(crew_image.get_width() * scale)),
            max(1, int(crew_image.get_height() * scale)),
        )
        sprite_image = pygame.transform.smoothscale(crew_image, sprite_size)
        sprite_rect = sprite_image.get_rect(center=row_rect.center)

        previous_clip = surface.get_clip()
        surface.set_clip(grid_rect)
        try:
            surface.blit(sprite_image, sprite_rect)
        finally:
            surface.set_clip(previous_clip)
        return True

    def _draw_running_crew_runners(
        self, surface, crew, terrain_map, grid_rect, cell_size: int
    ) -> bool:
        runner_images = []
        columns = min(max(1, crew.columns), terrain_map.columns)
        whole_tiles, progress = self._get_running_crew_motion(crew)
        first_column = -1 if progress > 0.0 else 0
        for column in range(first_column, columns):
            runner_image = self._get_running_crew_runner_image(
                crew, column, whole_tiles
            )
            if runner_image is None:
                return False
            runner_images.append((column, self._trim_transparent_margins(runner_image)))

        previous_clip = surface.get_clip()
        surface.set_clip(grid_rect)
        try:
            for column, runner_image in runner_images:
                rect = self._cell_rect(
                    grid_rect, cell_size, Position(crew.row, column)
                ).move(round(progress * cell_size), 0)
                self._draw_runner_cell(surface, runner_image, rect, cell_size)
        finally:
            surface.set_clip(previous_clip)
        return True

    def _draw_runner_cell(self, surface, runner_image, rect, cell_size: int) -> None:
        pygame = _pygame()
        target_rect = rect.inflate(-round(cell_size * 0.08), -round(cell_size * 0.04))
        scale = min(
            target_rect.width / runner_image.get_width(),
            target_rect.height / runner_image.get_height(),
        )
        sprite_size = (
            max(1, int(runner_image.get_width() * scale)),
            max(1, int(runner_image.get_height() * scale)),
        )
        sprite_image = pygame.transform.smoothscale(runner_image, sprite_size)
        sprite_rect = sprite_image.get_rect(center=rect.center)
        surface.blit(sprite_image, sprite_rect)

    def _trim_transparent_margins(self, image):
        bounds = image.get_bounding_rect(1)
        if bounds.width <= 0 or bounds.height <= 0:
            return image
        return image.subsurface(bounds).copy()

    def _draw_position_sprites(
        self, surface, sprites, grid_rect, cell_size, color, label, font
    ) -> None:
        pygame = _pygame()
        previous_clip = surface.get_clip()
        surface.set_clip(grid_rect)
        try:
            for sprite in sprites:
                for rect in self._get_sprite_draw_rects(sprite, grid_rect, cell_size):
                    if label == "B" and self._draw_bike_sprite(
                        surface, sprite, rect, cell_size
                    ):
                        continue
                    if label == "T" and self._draw_turtle_sprite(
                        surface, sprite, rect, cell_size
                    ):
                        continue
                    rect = rect.inflate(-cell_size * 0.24, -cell_size * 0.24)
                    pygame.draw.ellipse(surface, color, rect)
                    self._draw_centered_label(
                        surface, rect, label, font, ACTOR_TEXT_COLOR
                    )
        finally:
            surface.set_clip(previous_clip)

    def _draw_bike_sprite(self, surface, bike, rect, cell_size: int) -> bool:
        pygame = _pygame()
        bike_image = self._get_bike_image(bike)
        if bike_image is None:
            return False

        target_rect = rect.inflate(round(cell_size * 0.4), 0)
        scale = min(
            target_rect.width / bike_image.get_width(),
            target_rect.height / bike_image.get_height(),
        )
        sprite_size = (
            max(1, int(bike_image.get_width() * scale)),
            max(1, int(bike_image.get_height() * scale)),
        )
        sprite_image = pygame.transform.smoothscale(bike_image, sprite_size)
        sprite_rect = sprite_image.get_rect(center=rect.center)
        surface.blit(sprite_image, sprite_rect)
        return True

    def _draw_turtle_sprite(self, surface, turtle, rect, cell_size: int) -> bool:
        pygame = _pygame()
        turtle_image = self._get_turtle_image(turtle)
        if turtle_image is None:
            return False

        target_rect = rect.inflate(round(cell_size * 0.32), 0)
        scale = min(
            target_rect.width / turtle_image.get_width(),
            target_rect.height / turtle_image.get_height(),
        )
        sprite_size = (
            max(1, int(turtle_image.get_width() * scale)),
            max(1, int(turtle_image.get_height() * scale)),
        )
        sprite_image = pygame.transform.smoothscale(turtle_image, sprite_size)
        sprite_rect = sprite_image.get_rect(center=rect.center)
        surface.blit(sprite_image, sprite_rect)
        return True

    def _draw_player(self, surface, player, grid_rect, cell_size: int, font) -> None:
        pygame = _pygame()
        rect = self._get_player_draw_rect(
            grid_rect, cell_size, player.position, player.mounted_turtle
        )
        player_image = self._get_player_image(player.facing_direction)
        if player_image is None:
            pygame.draw.rect(surface, PLAYER_COLOR, rect, border_radius=8)
            self._draw_centered_label(surface, rect, "P", font, ACTOR_TEXT_COLOR)
            return

        scale = min(
            rect.width / player_image.get_width(),
            rect.height / player_image.get_height(),
        )
        sprite_size = (
            max(1, int(player_image.get_width() * scale)),
            max(1, int(player_image.get_height() * scale)),
        )
        sprite_image = pygame.transform.smoothscale(player_image, sprite_size)
        sprite_rect = sprite_image.get_rect(center=rect.center)
        surface.blit(sprite_image, sprite_rect)

    def _get_player_draw_rect(
        self, grid_rect, cell_size, position, carried_sprite=None
    ):
        base_rect = self._cell_rect(grid_rect, cell_size, position).inflate(
            -cell_size * PLAYER_CELL_INSET,
            -cell_size * PLAYER_CELL_INSET,
        )
        if carried_sprite is not None:
            return self._move_rect_by_sprite_progress(
                base_rect, carried_sprite, cell_size
            )

        if self._hop_start_position is None or self._hop_end_position is None:
            return base_rect

        progress = min(1.0, self._hop_elapsed / HOP_DURATION)
        start_rect = self._cell_rect(grid_rect, cell_size, self._hop_start_position)
        end_rect = self._cell_rect(grid_rect, cell_size, self._hop_end_position)
        center_x = (
            start_rect.centerx + (end_rect.centerx - start_rect.centerx) * progress
        )
        center_y = (
            start_rect.centery + (end_rect.centery - start_rect.centery) * progress
        )

        jump_scale = 1.0 + HOP_SIZE_BONUS * (1.0 - abs(progress * 2.0 - 1.0))
        width_bonus = round(base_rect.width * (jump_scale - 1.0))
        height_bonus = round(base_rect.height * (jump_scale - 1.0))
        draw_rect = base_rect.inflate(width_bonus, height_bonus)
        draw_rect.center = (round(center_x), round(center_y))
        return draw_rect

    def _get_sprite_draw_rects(self, sprite, grid_rect, cell_size: int):
        return [
            self._move_rect_by_sprite_progress(
                self._cell_rect(grid_rect, cell_size, position), sprite, cell_size
            )
            for position in sprite.get_positions()
        ]

    def _move_rect_by_sprite_progress(self, rect, sprite, cell_size: int):
        x_offset, y_offset = self._sprite_progress_offset(sprite)
        return rect.move(round(x_offset * cell_size), round(y_offset * cell_size))

    def _sprite_progress_offset(self, sprite) -> tuple[float, float]:
        progress = getattr(sprite, "distance_progress", 0.0)
        direction = getattr(sprite, "direction", "")
        offsets = {
            Direction.UP: (0.0, -progress),
            Direction.DOWN: (0.0, progress),
            Direction.LEFT: (-progress, 0.0),
            Direction.RIGHT: (progress, 0.0),
        }
        return offsets.get(direction, (0.0, 0.0))

    def _get_player_image(self, direction: str):
        if direction not in PLAYER_IMAGE_DIRECTIONS:
            direction = Direction.DOWN
        image_name = f"player_goose_{direction}"
        return self._get_asset_image(image_name)

    def _get_bike_image(self, bike):
        pygame = _pygame()
        frame_index = int(
            getattr(bike, "distance_progress", 0.0) * len(BIKE_FRAME_NAMES)
        )
        try:
            image = self._get_asset_image(
                BIKE_FRAME_NAMES[frame_index % len(BIKE_FRAME_NAMES)]
            )
        except RuntimeError:
            return None
        if image is None:
            return None
        if getattr(bike, "direction", Direction.RIGHT) == Direction.LEFT:
            return pygame.transform.flip(image, True, False)
        return image

    def _get_turtle_image(self, turtle):
        direction = getattr(turtle, "direction", Direction.RIGHT)
        image_name = TURTLE_IMAGE_NAMES.get(direction, "turtle_right")
        try:
            return self._get_asset_image(image_name)
        except RuntimeError:
            return None

    def _get_running_crew_warning_image(self, crew):
        elapsed_time = crew.elapsed_time
        frame_index = int(max(0.0, elapsed_time) / RUNNING_CREW_FRAME_DURATION) % len(
            RUNNING_CREW_WARNING_FRAME_NAMES
        )
        try:
            return self._get_asset_image(RUNNING_CREW_WARNING_FRAME_NAMES[frame_index])
        except RuntimeError:
            return None

    def _get_running_crew_motion(self, crew) -> tuple[int, float]:
        elapsed_time = crew.elapsed_time - crew.warning_time
        distance_progress = max(0.0, elapsed_time) / RUNNING_CREW_TILE_DURATION
        whole_tiles = int(distance_progress)
        return whole_tiles, distance_progress - whole_tiles

    def _get_running_crew_runner_image(self, crew, column: int, whole_tiles: int):
        stream_index = column - whole_tiles
        elapsed_time = crew.elapsed_time - crew.warning_time
        runner_frames = RUNNING_CREW_RUNNER_FRAME_NAMES[
            stream_index % len(RUNNING_CREW_RUNNER_FRAME_NAMES)
        ]
        base_frame = int(max(0.0, elapsed_time) / RUNNING_CREW_FRAME_DURATION)
        frame_index = (base_frame + stream_index) % len(runner_frames)
        try:
            return self._get_asset_image(runner_frames[frame_index])
        except RuntimeError:
            return None

    def _cell_rect(self, grid_rect, cell_size: int, position: Position):
        pygame = _pygame()
        left = grid_rect.left + round(position.column * cell_size)
        top = grid_rect.top + round(position.row * cell_size)
        right = grid_rect.left + round((position.column + 1) * cell_size)
        bottom = grid_rect.top + round((position.row + 1) * cell_size)
        return pygame.Rect(
            left,
            top,
            max(1, right - left),
            max(1, bottom - top),
        )

    def _draw_centered_label(self, surface, rect, text: str, font, color) -> None:
        if not text:
            return
        label_image = font.render(text, True, color)
        label_rect = label_image.get_rect(center=rect.center)
        surface.blit(label_image, label_rect)


class FailedScene(EmptyScene):
    def handle_event(self, event: object) -> None:
        pygame = _pygame()
        game = self._require_game()
        actions = {pygame.K_r: game.restart_stage}
        actions.update(dict.fromkeys((pygame.K_s, pygame.K_b), game.open_stage_select))
        actions.update(
            dict.fromkeys((pygame.K_m, pygame.K_ESCAPE), game.return_to_main)
        )
        self._dispatch_key(event, actions)

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
        pygame = _pygame()
        game = self._require_game()
        actions = {pygame.K_n: game.start_next_stage, pygame.K_r: game.restart_stage}
        actions.update(dict.fromkeys((pygame.K_s, pygame.K_b), game.open_stage_select))
        actions.update(
            dict.fromkeys((pygame.K_m, pygame.K_ESCAPE), game.return_to_main)
        )
        self._dispatch_key(event, actions)

    def draw(self, surface) -> None:
        pygame = _pygame()
        game = self._require_game()
        clear_time = getattr(game, "last_clear_time", None)
        stars = getattr(game, "last_stars", None)
        clear_time_text = "-" if clear_time is None else f"{clear_time:.1f}s"

        surface.fill(self._background_color)
        title_font = pygame.font.Font(None, 58)
        body_font = pygame.font.Font(None, 32)

        y = 96
        self._draw_centered_text(surface, "Stage Cleared", y, title_font, TEXT_COLOR)
        y += 74
        self._draw_centered_text(
            surface, f"Clear time: {clear_time_text}", y, body_font, TEXT_COLOR
        )
        y += 38
        if stars is None:
            self._draw_centered_text(surface, "Stars: -", y, body_font, TEXT_COLOR)
        else:
            self._draw_star_line(surface, "Stars:", stars, y, body_font)

        y += 76
        for line in RESULT_ACTION_LINES:
            self._draw_centered_text(surface, line, y, body_font, TEXT_COLOR)
            y += 38
