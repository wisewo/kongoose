import math
from pathlib import Path

from kongoose import models as M
from kongoose import scenes
from kongoose.models import SoundCue as S
from kongoose.resources import ResourceManager, SoundManager
from kongoose.stage_catalog import build_default_stages
from kongoose.storage import SaveManager
from kongoose.timing import StarRating, Timer

MAX_STAGE_COUNT = 4
BIKE_CHANNEL = 3
ACTION_CHANNEL = 4
CREW_CHANNEL = 5
TURTLE_CHANNEL = 6
SOUND_DIR = Path(__file__).resolve().parent.parent / "assets" / "sounds"
DEFAULT_SOUND_PATHS = {
    cue: SOUND_DIR / filename
    for cue, filename in (
        (S.MOVE_START, "player_jump_start.wav"),
        (S.MOVE_SUCCESS, "player_move_success.wav"),
        (S.BLOCKED, "blocked_obstacle.wav"),
        (S.TURTLE, "turtle_ride.wav"),
        (S.BIKE_AMBIENCE, "bike_appear.wav"),
        (S.RUNNING_CREW_WARNING, "running_crew_warning.wav"),
        (S.RUNNING_CREW_ACTIVE, "running_crew_active.wav"),
        (S.LAKE_SPLASH, "lake_game_over.wav"),
        (S.UI_SELECT, "ui_select.wav"),
        (S.BACKGROUND_MUSIC, "background_music.wav"),
        (S.FAILURE_SCREEN, "failure_screen.wav"),
        (S.CLEAR_SCREEN, "clear_screen.wav"),
    )
}
UPDATE_SOUNDS = {
    M.UPDATE_WARNING: (S.RUNNING_CREW_WARNING, 1.0, CREW_CHANNEL),
    M.UPDATE_RUNNING_CREW_ACTIVE: (S.RUNNING_CREW_ACTIVE, 0.0, CREW_CHANNEL),
    M.UPDATE_TURTLE_RIDE: (S.TURTLE, 0.8, TURTLE_CHANNEL),
}
MOVE_SOUNDS = {
    M.MOVE_BLOCKED: S.BLOCKED,
    M.MOVE_MOVED: S.MOVE_START,
}


class Game:
    def __init__(
        self, window_size=(960, 720), title="Kongoose", initial_scene=None, stages=None
    ):
        self.window_size, self.title = window_size, title
        self.screen = self.clock = None
        self.running = False
        self.current_scene = None
        self.stages = dict(stages) if stages is not None else build_default_stages()
        self.current_stage = None
        self.save_manager, self.timer = SaveManager(), Timer()
        self.sound_manager, self.resource_manager = SoundManager(), ResourceManager()
        self.progress = self.save_manager.load_progress()
        self.current_stage_id = None
        self.last_failure_reason = self.last_clear_time = self.last_stars = None
        self._last_bike_warning_rows = ()
        if initial_scene is not None:
            self.change_scene(initial_scene)

    def run(self) -> None:
        import pygame

        pygame.init()
        pygame.display.set_caption(self.title)
        self.screen = pygame.display.set_mode(self.window_size)
        self.clock = pygame.time.Clock()
        self.sound_manager.load(DEFAULT_SOUND_PATHS)
        self.sound_manager.play(S.BACKGROUND_MUSIC, loops=-1)
        self.running = True
        if self.current_scene is None:
            self.change_scene(scenes.MainScene())
        while self.running:
            dt = self.clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                elif self.current_scene is not None:
                    self.current_scene.handle_event(event)
            if self.current_scene is not None:
                self.current_scene.update(dt)
                self.current_scene.draw(self.screen)
            pygame.display.flip()
        pygame.quit()

    def start_game(self) -> None:
        self.change_scene(scenes.MainScene())

    def change_scene(self, scene: scenes.Scene) -> None:
        self.current_scene = scene
        scene.enter(self)

    def quit_game(self) -> None:
        self.running = False

    def open_stage_select(self) -> None:
        self.sound_manager.play(S.UI_SELECT)
        self.change_scene(scenes.StageSelectScene())

    def select_stage(self, stage_id: int) -> None:
        if not self.progress.is_stage_unlocked(stage_id):
            self._set_scene_message(f"Stage {stage_id} is locked.")
            return
        self.sound_manager.play(S.UI_SELECT)
        self.start_stage(stage_id)

    def start_stage(self, stage_id: int) -> None:
        self.current_stage_id, self.current_stage = stage_id, self.stages[stage_id]
        self.last_failure_reason = self.last_clear_time = self.last_stars = None
        self._last_bike_warning_rows = ()
        self.current_stage.initialize()
        self.timer.reset()
        self.timer.start()
        self.change_scene(scenes.PlayingScene())

    def start_next_stage(self) -> None:
        if self.current_stage_id is None:
            self._set_scene_message("No current stage is selected.")
            return
        next_stage_id = self.current_stage_id + 1
        if next_stage_id > MAX_STAGE_COUNT:
            self._set_scene_message("There is no next stage.")
            return
        self.sound_manager.play(S.UI_SELECT)
        self.start_stage(next_stage_id)

    def restart_stage(self) -> None:
        if self.current_stage_id is None:
            self.open_stage_select()
            return
        self.sound_manager.play(S.UI_SELECT)
        self.start_stage(self.current_stage_id)

    def return_to_main(self) -> None:
        self.sound_manager.play(S.UI_SELECT)
        self.change_scene(scenes.MainScene())

    def move_player(self, direction: str) -> None:
        self._handle_move_result(self.current_stage.move_player(direction))

    def update_stage(self, dt: float) -> None:
        self._handle_stage_update_result(self.current_stage.update(dt))

    def fail_current_stage(self, reason) -> None:
        self.last_failure_reason = reason
        self.change_scene(scenes.FailedScene())
        self.sound_manager.play(S.FAILURE_SCREEN)

    def clear_current_stage(self) -> None:
        self.timer.stop()
        self.last_clear_time = self.timer.get_elapsed_time()
        self.last_stars = StarRating.calculate(
            self.last_clear_time, self.current_stage_id
        )
        self.progress.record_stage_clear(self.current_stage_id, self.last_stars)
        self.save_manager.save_progress(self.progress)
        self.change_scene(scenes.ResultScene())
        self.sound_manager.play(S.CLEAR_SCREEN)

    def _set_scene_message(self, message: str) -> None:
        set_message = getattr(self.current_scene, "set_message", None)
        if callable(set_message):
            set_message(message)

    def _handle_failure_from_stage(self) -> None:
        reason = getattr(self.current_stage, "failure_reason", None)
        if reason == M.FailureReason.FELL_IN_RIVER:
            self.sound_manager.play(S.LAKE_SPLASH)
        if reason is not None:
            self.fail_current_stage(reason)

    def _handle_move_result(self, result: str | None) -> None:
        if result == M.MOVE_FAILED:
            self._handle_failure_from_stage()
            return
        if result == M.MOVE_CLEARED:
            self.clear_current_stage()
            return
        if cue := MOVE_SOUNDS.get(result):
            self.sound_manager.play(cue, channel_index=ACTION_CHANNEL)

    def _handle_stage_update_result(self, result: str | None) -> None:
        self._maybe_play_pending_bike_warning()
        if result == M.UPDATE_FAILED:
            self._handle_failure_from_stage()
            return
        if result in (None, M.UPDATE_BIKE_AMBIENCE):
            return
        if update_sound := UPDATE_SOUNDS.get(result):
            cue, cooldown, channel = update_sound
            self.sound_manager.play(cue, cooldown=cooldown, channel_index=channel)

    def _play_bike_warning_from_stage(self) -> bool:
        if not any(
            self._is_row_in_view(row) for row in self._pending_bike_warning_rows()
        ):
            return False
        self.sound_manager.play(S.BIKE_AMBIENCE, channel_index=BIKE_CHANNEL)
        return True

    def _maybe_play_pending_bike_warning(self) -> bool:
        if not (warning_rows := self._pending_bike_warning_rows()):
            self._last_bike_warning_rows = ()
            return False
        if warning_rows == self._last_bike_warning_rows:
            return False
        if self._play_bike_warning_from_stage():
            self._last_bike_warning_rows = warning_rows
            return True
        return False

    def _pending_bike_warning_rows(self) -> tuple[int, ...]:
        if self.current_stage is None:
            return ()
        peek_warning_rows = getattr(self.current_stage, "peek_warning_bike_rows", None)
        return tuple(peek_warning_rows()) if callable(peek_warning_rows) else ()

    def _is_row_in_view(self, row: int) -> bool:
        if self.current_stage is None:
            return False
        terrain_map = self.current_stage.terrain_map
        rows, columns = terrain_map.rows, terrain_map.columns
        if rows <= 0 or columns <= 0:
            return False
        available_width, available_height = self.window_size
        if available_width <= 0 or available_height <= 0:
            return False
        cell_size = max(scenes.MIN_TILE_SIZE, available_width / columns)
        grid_height = cell_size * rows
        if grid_height <= available_height:
            return 0 <= row < rows
        player_row = self.current_stage.player.position.row
        top = scenes.grid_top_for_focus(rows, cell_size, available_height, player_row)
        start = max(0, math.floor(-top / cell_size))
        end = min(rows - 1, math.ceil((available_height - top) / cell_size) - 1)
        return start <= row <= end
