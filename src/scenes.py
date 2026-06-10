from pathlib import Path

import pygame

from src.models import MOVE_BLOCKED, Direction, Position, SoundCue
from src.rendering import (
    DEFAULT_BACKGROUND_COLOR,
    HOP_DURATION,
    TEXT_COLOR,
    StageRenderer,
    blit_scaled_centered,
    get_ui_font,
    render_ui_text,
)

MAX_STAGE_COUNT = 4
MESSAGE_COLOR = (172, 72, 39)
ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
STAR_FILLED_IMAGE = "star_filled"
STAR_EMPTY_IMAGE = "star_empty"
STAR_ICON_SIZE, STAR_ICON_GAP = 30, 5
MAIN_ACTION_LINES = ("Enter / Space: Stage Select", "Esc / Q: Quit")
FAILED_ACTION_LINES = ("R: Restart Stage", "S / B: Stage Select", "M / Esc: Main")
RESULT_ACTION_LINES = ("N: Next Stage", *FAILED_ACTION_LINES)
DIRECTION_KEYS = {
    pygame.K_UP: Direction.UP,
    pygame.K_DOWN: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT,
}
BACK_KEYS = (pygame.K_ESCAPE, pygame.K_b)
CAMERA_FOLLOW_SPEED = 8.0


def _fonts(*sizes: int):
    return tuple(get_ui_font(size) for size in sizes)


class EmptyScene:
    def __init__(self, background_color=DEFAULT_BACKGROUND_COLOR) -> None:
        self._background_color = background_color
        self._game = None
        self._message = ""

    def enter(self, game) -> None:
        self._game = game

    def update(self, dt: float) -> None:
        return None

    def set_message(self, message: str) -> None:
        self._message = message

    def _require_game(self):
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
        image = render_ui_text(font, text, color)
        surface.blit(image, image.get_rect(center=(surface.get_width() // 2, y)))

    def _draw_centered_lines(self, surface, lines, y, font, color=TEXT_COLOR):
        for line in lines:
            self._draw_centered_text(surface, line, y, font, color)
            y += 58
        return y

    def _draw_message(self, surface, y: int, font) -> None:
        if self._message:
            self._draw_centered_text(surface, self._message, y, font, MESSAGE_COLOR)

    def _get_asset_image(self, image_name: str):
        game = self._require_game()
        if cached_image := game.resource_manager.get_image(image_name):
            return cached_image
        image_path = ASSET_DIR / f"{image_name}.png"
        if not image_path.exists():
            return None
        image = pygame.image.load(str(image_path))
        game.resource_manager.register_image(image_name, image)
        return image

    def _draw_star_line(self, surface, label, stars, y, font, icon_size=STAR_ICON_SIZE):
        stars = max(0, min(3, stars))
        label_image = render_ui_text(font, label)
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
            icon_size * 3 + STAR_ICON_GAP * 2
            if has_icons
            else render_ui_text(font, stars_text).get_width()
        )
        left = (surface.get_width() - label_image.get_width() - gap - rating_width) // 2
        label_rect = label_image.get_rect(midleft=(left, y))
        surface.blit(label_image, label_rect)
        rating_left = min(
            label_rect.right + gap, surface.get_width() - rating_width - gap
        )
        if has_icons:
            for index, image in enumerate(images):
                target = pygame.Rect(
                    rating_left + index * (icon_size + STAR_ICON_GAP),
                    y - icon_size // 2,
                    icon_size,
                    icon_size,
                )
                blit_scaled_centered(surface, image, target)
            return
        rating_image = render_ui_text(font, stars_text)
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
            "길Kon너 Goose들",
            [
                "Campus crossing with kongoose(건구스)",
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
        y += 100
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
            y += 58
        y += 58
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
        self._hop_plays_success = False
        self._camera_focus: Position | None = None
        self._renderer = StageRenderer(self._get_asset_image)

    def handle_event(self, event: object) -> None:
        if event.type != pygame.KEYDOWN:
            return
        game = self._require_game()
        if event.key in BACK_KEYS:
            game.open_stage_select()
            return
        direction = DIRECTION_KEYS.get(event.key)
        if direction is not None:
            stage = game.current_stage
            player = stage.player
            if self._hop_start_position is not None:
                return
            start_position = player.position
            target_position = player.position.moved(direction)
            result = game.move_player(direction)
            if game.current_scene is self and start_position != player.position:
                self._start_hop(start_position, player.position, True)
            elif game.current_scene is self and result == MOVE_BLOCKED:
                self._start_hop(start_position, target_position, False)

    def update(self, dt: float) -> None:
        if self._hop_start_position is not None:
            self._hop_elapsed += dt
            if self._hop_elapsed >= HOP_DURATION:
                self._hop_start_position = None
                self._hop_end_position = None
                self._hop_elapsed = 0.0
                if self._hop_plays_success:
                    self._require_game().sound_manager.play(SoundCue.MOVE_SUCCESS)
                self._hop_plays_success = False
        game = self._require_game()
        game.update_stage(dt)
        if game.current_scene is self:
            self._update_camera_focus(dt)

    def _start_hop(self, start: Position, end: Position, plays_success: bool) -> None:
        self._hop_start_position = start
        self._hop_end_position = end
        self._hop_elapsed = 0.0
        self._hop_plays_success = plays_success

    def _ensure_camera_focus(self) -> Position:
        if self._camera_focus is None:
            position = self._require_game().current_stage.player.position
            self._camera_focus = Position(position.row, position.column)
        return self._camera_focus

    def _update_camera_focus(self, dt: float) -> None:
        focus = self._ensure_camera_focus()
        target = self._require_game().current_stage.player.position
        amount = 1.0 - pow(2.0, -CAMERA_FOLLOW_SPEED * max(0.0, dt))
        self._camera_focus = Position(
            focus.row + (target.row - focus.row) * amount,
            focus.column + (target.column - focus.column) * amount,
        )

    def draw(self, surface) -> None:
        game = self._require_game()
        hop = self._hop_start_position, self._hop_end_position, self._hop_elapsed
        self._renderer.draw(
            surface,
            game.current_stage,
            game.current_stage_id,
            f"{game.timer.get_elapsed_time():.1f}s",
            self._background_color,
            hop,
            camera_focus=self._ensure_camera_focus(),
        )


class FailedScene(EmptyScene):
    def handle_event(self, event: object) -> None:
        self._dispatch_end_scene_keys(event)

    def draw(self, surface) -> None:
        reason_text = self._require_game().last_failure_reason.name
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
        clear_time_text = f"{game.last_clear_time:.1f}s"
        body_font, y = self._begin_text_screen(surface, "Stage Cleared")
        self._draw_centered_text(
            surface, f"Clear time: {clear_time_text}", y, body_font, TEXT_COLOR
        )
        y += 38
        self._draw_star_line(surface, "Stars:", game.last_stars, y, body_font)
        y += 76
        self._draw_centered_lines(surface, RESULT_ACTION_LINES, y, body_font)
