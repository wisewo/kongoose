from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from kongoose.models import Direction

if TYPE_CHECKING:
    from kongoose.game import Game


MAX_STAGE_COUNT = 4
TEXT_COLOR = (35, 45, 50)
MUTED_TEXT_COLOR = (95, 106, 112)
MESSAGE_COLOR = (172, 72, 39)


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
        game = self._require_game()
        stage_id = getattr(game, "current_stage_id", None)
        stage_text = "-" if stage_id is None else str(stage_id)
        elapsed_text = f"{self._get_elapsed_time():.1f}s"
        play_message = getattr(game, "last_play_message", "")

        if play_message:
            self.set_message(play_message)

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
