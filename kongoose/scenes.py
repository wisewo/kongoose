from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from kongoose.models import Direction, Position, TerrainType

if TYPE_CHECKING:
    from kongoose.game import Game


MAX_STAGE_COUNT = 4
TEXT_COLOR = (35, 45, 50)
MUTED_TEXT_COLOR = (95, 106, 112)
MESSAGE_COLOR = (172, 72, 39)
GRID_LINE_COLOR = (73, 83, 90)
TERRAIN_COLORS = {
    TerrainType.START: (176, 224, 166),
    TerrainType.LAND: (231, 222, 178),
    TerrainType.SAFE: (205, 234, 198),
    TerrainType.LAKE: (80, 155, 210),
    TerrainType.WALL: (92, 96, 105),
    TerrainType.GOAL: (245, 205, 92),
}
TERRAIN_LABELS = {
    TerrainType.START: "S",
    TerrainType.LAND: "",
    TerrainType.SAFE: "",
    TerrainType.LAKE: "LAKE",
    TerrainType.WALL: "WALL",
    TerrainType.GOAL: "GOAL",
}
PLAYER_COLOR = (240, 142, 74)
BIKE_COLOR = (210, 66, 70)
RUNNING_CREW_COLOR = (146, 80, 170)
TURTLE_COLOR = (72, 170, 120)
ACTOR_TEXT_COLOR = (255, 255, 255)


class Scene(ABC):
    @abstractmethod
    def enter(self, game: Game) -> None:
        raise NotImplementedError

    @abstractmethod
    def handle_event(self, event: object) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self, dt: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def draw(self, surface: Any) -> None:
        raise NotImplementedError


class EmptyScene(Scene):
    def __init__(
        self, background_color: tuple[int, int, int] = (242, 247, 241)
    ) -> None:
        self._background_color = background_color
        self._game: Game | None = None
        self._message = ""

    def enter(self, game: Game) -> None:
        self._game = game

    def handle_event(self, event: object) -> None:
        return None

    def update(self, dt: float) -> None:
        return None

    def draw(self, surface: Any) -> None:
        surface.fill(self._background_color)

    def set_message(self, message: str) -> None:
        self._message = message

    def _require_game(self) -> Game:
        if self._game is None:
            raise RuntimeError("Scene has not entered a Game yet.")
        return self._game

    def _draw_text_screen(
        self,
        surface: Any,
        title: str,
        lines: list[str],
    ) -> None:
        import pygame

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

    def _is_stage_unlocked(self, stage_id: int) -> bool:
        return self._require_game().progress.is_stage_unlocked(stage_id)

    def _get_best_stars(self, stage_id: int) -> int:
        return self._require_game().progress.get_best_stars(stage_id)

    def _get_elapsed_time(self) -> float:
        return self._require_game().timer.get_elapsed_time()


class MainScene(EmptyScene):
    def handle_event(self, event: object) -> None:
        import pygame

        if event.type != pygame.KEYDOWN:
            return

        game = self._require_game()
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            game.open_stage_select()
        elif event.key in (pygame.K_ESCAPE, pygame.K_q):
            game.quit_game()

    def draw(self, surface: Any) -> None:
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
                "Enter / Space: Stage Select",
                "Esc / Q: Quit",
            ],
        )


class StageSelectScene(EmptyScene):
    def handle_event(self, event: object) -> None:
        import pygame

        if event.type != pygame.KEYDOWN:
            return

        game = self._require_game()
        if event.key in (pygame.K_ESCAPE, pygame.K_b):
            game.return_to_main()
            return

        key_to_stage_id = {
            pygame.K_1: 1,
            pygame.K_2: 2,
            pygame.K_3: 3,
            pygame.K_4: 4,
        }
        stage_id = key_to_stage_id.get(event.key)
        if stage_id is not None:
            game.select_stage(stage_id)

    def draw(self, surface: Any) -> None:
        lines = ["Choose a stage with number keys.", ""]
        for stage_id in range(1, MAX_STAGE_COUNT + 1):
            status = "Unlocked" if self._is_stage_unlocked(stage_id) else "Locked"
            best_stars = self._get_best_stars(stage_id)
            stars = "-" if best_stars == 0 else "*" * best_stars
            lines.append(f"{stage_id}: Stage {stage_id} [{status}] Best: {stars}")

        lines.extend(["", "1-4: Select Stage", "Esc / B: Main"])
        self._draw_text_screen(surface, "Stage Select", lines)


class PlayingScene(EmptyScene):
    def handle_event(self, event: object) -> None:
        import pygame

        if event.type != pygame.KEYDOWN:
            return

        game = self._require_game()
        if event.key in (pygame.K_ESCAPE, pygame.K_b):
            game.open_stage_select()
            return

        key_to_direction = {
            pygame.K_UP: Direction.UP,
            pygame.K_DOWN: Direction.DOWN,
            pygame.K_LEFT: Direction.LEFT,
            pygame.K_RIGHT: Direction.RIGHT,
        }
        direction = key_to_direction.get(event.key)
        if direction is not None:
            game.move_player(direction)

    def update(self, dt: float) -> None:
        self._require_game().update_stage(dt)

    def draw(self, surface: Any) -> None:
        import pygame

        game = self._require_game()
        stage_id = getattr(game, "current_stage_id", None)
        stage_text = "-" if stage_id is None else str(stage_id)
        elapsed_text = f"{self._get_elapsed_time():.1f}s"
        play_message = getattr(game, "last_play_message", "")

        if play_message:
            self.set_message(play_message)

        stage = getattr(game, "current_stage", None)
        terrain_map = getattr(stage, "terrain_map", None)
        player = getattr(stage, "player", None)
        if terrain_map is None or player is None:
            self._draw_text_screen(
                surface,
                "Playing",
                [
                    f"Current stage: {stage_text}",
                    f"Elapsed time: {elapsed_text}",
                    "",
                    "Arrow keys: Move one tile",
                    "Esc / B: Stage Select",
                ],
            )
            return

        surface.fill(self._background_color)
        width, height = surface.get_size()
        title_font = pygame.font.Font(None, 44)
        body_font = pygame.font.Font(None, 26)
        small_font = pygame.font.Font(None, 20)

        self._draw_playing_hud(
            surface,
            title_font,
            body_font,
            stage_text,
            elapsed_text,
            play_message,
        )

        grid_rect, cell_size = self._calculate_grid_layout(
            width,
            height,
            terrain_map.rows,
            terrain_map.columns,
        )
        self._draw_terrain_grid(surface, terrain_map, grid_rect, cell_size, small_font)
        self._draw_running_crews(
            surface,
            getattr(stage, "running_crews", []),
            terrain_map,
            grid_rect,
            cell_size,
            small_font,
        )
        self._draw_position_sprites(
            surface,
            getattr(stage, "turtles", []),
            grid_rect,
            cell_size,
            TURTLE_COLOR,
            "T",
            small_font,
        )
        self._draw_position_sprites(
            surface,
            getattr(stage, "bikes", []),
            grid_rect,
            cell_size,
            BIKE_COLOR,
            "B",
            small_font,
        )
        self._draw_player(surface, player, grid_rect, cell_size, small_font)

    def _draw_playing_hud(
        self,
        surface: Any,
        title_font: Any,
        body_font: Any,
        stage_text: str,
        elapsed_text: str,
        play_message: str,
    ) -> None:
        title_image = title_font.render("Playing", True, TEXT_COLOR)
        surface.blit(title_image, (36, 24))

        status_text = (
            f"Current stage: {stage_text}   Elapsed time: {elapsed_text}   "
            "Arrow keys: Move one tile   Esc / B: Stage Select"
        )
        status_image = body_font.render(status_text, True, TEXT_COLOR)
        surface.blit(status_image, (38, 72))

        if play_message:
            message_image = body_font.render(play_message, True, MESSAGE_COLOR)
            surface.blit(message_image, (38, 102))

    def _calculate_grid_layout(
        self,
        surface_width: int,
        surface_height: int,
        rows: int,
        columns: int,
    ) -> tuple[Any, int]:
        import pygame

        top_margin = 140
        side_margin = 40
        bottom_margin = 32
        available_width = surface_width - side_margin * 2
        available_height = surface_height - top_margin - bottom_margin
        cell_size = max(16, min(available_width // columns, available_height // rows))
        grid_width = cell_size * columns
        grid_height = cell_size * rows
        left = (surface_width - grid_width) // 2
        top = top_margin + max(0, (available_height - grid_height) // 2)
        return pygame.Rect(left, top, grid_width, grid_height), cell_size

    def _draw_terrain_grid(
        self,
        surface: Any,
        terrain_map: Any,
        grid_rect: Any,
        cell_size: int,
        font: Any,
    ) -> None:
        import pygame

        for row in range(terrain_map.rows):
            for column in range(terrain_map.columns):
                position = Position(row=row, column=column)
                terrain = terrain_map.get_terrain(position)
                rect = self._cell_rect(grid_rect, cell_size, position)
                pygame.draw.rect(surface, TERRAIN_COLORS[terrain], rect)
                pygame.draw.rect(surface, GRID_LINE_COLOR, rect, 1)
                self._draw_centered_label(
                    surface,
                    rect,
                    TERRAIN_LABELS[terrain],
                    font,
                    TEXT_COLOR,
                )

    def _draw_running_crews(
        self,
        surface: Any,
        running_crews: list[Any],
        terrain_map: Any,
        grid_rect: Any,
        cell_size: int,
        font: Any,
    ) -> None:
        import pygame

        for crew in running_crews:
            for column in range(terrain_map.columns):
                position = Position(row=crew.row, column=column)
                if not self._is_in_terrain(position, terrain_map):
                    continue
                rect = self._cell_rect(grid_rect, cell_size, position).inflate(
                    -cell_size * 0.22,
                    -cell_size * 0.34,
                )
                if crew.occupies(position):
                    pygame.draw.rect(surface, RUNNING_CREW_COLOR, rect, border_radius=4)
                    self._draw_centered_label(
                        surface,
                        rect,
                        "R",
                        font,
                        ACTOR_TEXT_COLOR,
                    )
                elif crew.should_warn():
                    pygame.draw.rect(surface, RUNNING_CREW_COLOR, rect, 2, 4)

    def _draw_position_sprites(
        self,
        surface: Any,
        sprites: list[Any],
        grid_rect: Any,
        cell_size: int,
        color: tuple[int, int, int],
        label: str,
        font: Any,
    ) -> None:
        import pygame

        for sprite in sprites:
            for position in getattr(sprite, "positions", ()):
                rect = self._cell_rect(grid_rect, cell_size, position).inflate(
                    -cell_size * 0.24,
                    -cell_size * 0.24,
                )
                pygame.draw.ellipse(surface, color, rect)
                self._draw_centered_label(surface, rect, label, font, ACTOR_TEXT_COLOR)

    def _draw_player(
        self,
        surface: Any,
        player: Any,
        grid_rect: Any,
        cell_size: int,
        font: Any,
    ) -> None:
        import pygame

        rect = self._cell_rect(grid_rect, cell_size, player.position).inflate(
            -cell_size * 0.18,
            -cell_size * 0.18,
        )
        pygame.draw.rect(surface, PLAYER_COLOR, rect, border_radius=8)
        self._draw_centered_label(surface, rect, "P", font, ACTOR_TEXT_COLOR)

    def _cell_rect(self, grid_rect: Any, cell_size: int, position: Position) -> Any:
        import pygame

        return pygame.Rect(
            grid_rect.left + position.column * cell_size,
            grid_rect.top + position.row * cell_size,
            cell_size,
            cell_size,
        )

    def _draw_centered_label(
        self,
        surface: Any,
        rect: Any,
        text: str,
        font: Any,
        color: tuple[int, int, int],
    ) -> None:
        if not text:
            return
        label_image = font.render(text, True, color)
        label_rect = label_image.get_rect(center=rect.center)
        surface.blit(label_image, label_rect)

    def _is_in_terrain(self, position: Position, terrain_map: Any) -> bool:
        return (
            0 <= position.row < terrain_map.rows
            and 0 <= position.column < terrain_map.columns
        )


class FailedScene(EmptyScene):
    def handle_event(self, event: object) -> None:
        import pygame

        if event.type != pygame.KEYDOWN:
            return

        game = self._require_game()
        if event.key == pygame.K_r:
            game.restart_stage()
        elif event.key in (pygame.K_s, pygame.K_b):
            game.open_stage_select()
        elif event.key in (pygame.K_m, pygame.K_ESCAPE):
            game.return_to_main()

    def draw(self, surface: Any) -> None:
        reason = getattr(self._require_game(), "last_failure_reason", None)
        reason_text = "-" if reason is None else reason.name
        self._draw_text_screen(
            surface,
            "Stage Failed",
            [
                f"Reason: {reason_text}",
                "",
                "R: Restart Stage",
                "S / B: Stage Select",
                "M / Esc: Main",
            ],
        )


class ResultScene(EmptyScene):
    def handle_event(self, event: object) -> None:
        import pygame

        if event.type != pygame.KEYDOWN:
            return

        game = self._require_game()
        if event.key == pygame.K_n:
            game.start_next_stage()
        elif event.key == pygame.K_r:
            game.restart_stage()
        elif event.key in (pygame.K_s, pygame.K_b):
            game.open_stage_select()
        elif event.key in (pygame.K_m, pygame.K_ESCAPE):
            game.return_to_main()

    def draw(self, surface: Any) -> None:
        game = self._require_game()
        clear_time = getattr(game, "last_clear_time", None)
        stars = getattr(game, "last_stars", None)
        clear_time_text = "-" if clear_time is None else f"{clear_time:.1f}s"
        stars_text = "-" if stars is None else "*" * stars

        self._draw_text_screen(
            surface,
            "Stage Cleared",
            [
                f"Clear time: {clear_time_text}",
                f"Stars: {stars_text}",
                "",
                "N: Next Stage",
                "R: Restart Stage",
                "S / B: Stage Select",
                "M / Esc: Main",
            ],
        )
