import math
from pathlib import Path

from kongoose.models import (
    MOVE_BLOCKED,
    MOVE_CLEARED,
    MOVE_FAILED,
    MOVE_MOVED,
    UPDATE_BIKE_AMBIENCE,
    UPDATE_FAILED,
    UPDATE_RUNNING_CREW_ACTIVE,
    UPDATE_TURTLE_RIDE,
    UPDATE_WARNING,
    FailureReason,
    SoundCue,
)
from kongoose.resources import ResourceManager, SoundManager
from kongoose.scenes import (
    MIN_TILE_SIZE,
    FailedScene,
    MainScene,
    PlayingScene,
    ResultScene,
    Scene,
    StageSelectScene,
)
from kongoose.stage import Stage
from kongoose.stage_catalog import build_default_stages
from kongoose.storage import SaveManager
from kongoose.timing import StarRating, Timer

MAX_STAGE_COUNT = 4
BIKE_WARNING_CHANNEL = 3
ACTION_SOUND_CHANNEL = 4
RUNNING_CREW_SOUND_CHANNEL = 5
TURTLE_SOUND_CHANNEL = 6
_SCENE_SIDE_MARGIN = 0
_SCENE_TOP_MARGIN = 0
_SCENE_BOTTOM_MARGIN = 0
SOUND_DIR = Path(__file__).resolve().parent.parent / "assets" / "sounds"
DEFAULT_SOUND_PATHS = {
    SoundCue.MOVE_START: SOUND_DIR / "player_jump_start.wav",
    SoundCue.MOVE_SUCCESS: SOUND_DIR / "player_move_success.wav",
    SoundCue.BLOCKED: SOUND_DIR / "blocked_obstacle.wav",
    SoundCue.TURTLE: SOUND_DIR / "turtle_ride.wav",
    SoundCue.BIKE_AMBIENCE: SOUND_DIR / "bike_appear.wav",
    SoundCue.RUNNING_CREW_WARNING: SOUND_DIR / "running_crew_warning.wav",
    SoundCue.RUNNING_CREW_ACTIVE: SOUND_DIR / "running_crew_active.wav",
    SoundCue.LAKE_SPLASH: SOUND_DIR / "lake_game_over.wav",
    SoundCue.UI_SELECT: SOUND_DIR / "ui_select.wav",
    SoundCue.BACKGROUND_MUSIC: SOUND_DIR / "background_music.wav",
    SoundCue.FAILURE_SCREEN: SOUND_DIR / "failure_screen.wav",
    SoundCue.CLEAR_SCREEN: SOUND_DIR / "clear_screen.wav",
}
MOVE_MESSAGES = {
    MOVE_BLOCKED: "Blocked by terrain.",
    MOVE_MOVED: "Moved.",
}
UPDATE_CUES = {
    UPDATE_WARNING: SoundCue.RUNNING_CREW_WARNING,
    UPDATE_RUNNING_CREW_ACTIVE: SoundCue.RUNNING_CREW_ACTIVE,
    UPDATE_TURTLE_RIDE: SoundCue.TURTLE,
    UPDATE_BIKE_AMBIENCE: SoundCue.BIKE_AMBIENCE,
}
UPDATE_MESSAGES = {
    UPDATE_WARNING: "Running crew warning.",
    UPDATE_RUNNING_CREW_ACTIVE: "Running crew active.",
    UPDATE_TURTLE_RIDE: "Riding a turtle.",
    UPDATE_BIKE_AMBIENCE: "Bike appeared.",
}
UPDATE_CUE_COOLDOWNS = {
    SoundCue.RUNNING_CREW_WARNING: 1.0,
    SoundCue.TURTLE: 0.8,
    SoundCue.BIKE_AMBIENCE: 0.0,
}
UPDATE_CUE_CHANNELS = {
    SoundCue.RUNNING_CREW_WARNING: RUNNING_CREW_SOUND_CHANNEL,
    SoundCue.RUNNING_CREW_ACTIVE: RUNNING_CREW_SOUND_CHANNEL,
    SoundCue.TURTLE: TURTLE_SOUND_CHANNEL,
}


class Game:
    def __init__(
        self,
        window_size: tuple[int, int] = (960, 720),
        title: str = "Kongoose",
        initial_scene: Scene | None = None,
        stages: dict[int, Stage] | None = None,
    ) -> None:
        self.window_size = window_size
        self.title = title
        self.screen = None
        self.clock = None
        self.running = False
        self.current_scene: Scene | None = None
        self.stages = dict(stages) if stages is not None else build_default_stages()
        self.current_stage: Stage | None = None
        self.save_manager = SaveManager()
        self.progress = self.save_manager.load_progress()
        self.timer = Timer()
        self.sound_manager = SoundManager()
        self.resource_manager = ResourceManager()
        self.current_stage_id: int | None = None
        self.last_failure_reason: FailureReason | None = None
        self.last_clear_time: float | None = None
        self.last_stars: int | None = None
        self.last_play_message = ""
        self._last_bike_warning_rows: tuple[int, ...] = ()

        if initial_scene is not None:
            self.change_scene(initial_scene)

    def run(self) -> None:
        import pygame

        pygame.init()
        pygame.display.set_caption(self.title)
        self.screen = pygame.display.set_mode(self.window_size)
        self.clock = pygame.time.Clock()
        self._load_default_sounds()
        self.sound_manager.play(SoundCue.BACKGROUND_MUSIC, loops=-1)
        self.running = True

        if self.current_scene is None:
            self.change_scene(MainScene())

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
        self.change_scene(MainScene())

    def change_scene(self, scene: Scene) -> None:
        self.current_scene = scene
        scene.enter(self)

    def quit_game(self) -> None:
        self.running = False

    def open_stage_select(self) -> None:
        self._play_ui_select()
        self.change_scene(StageSelectScene())

    def select_stage(self, stage_id: int) -> None:
        if not self.progress.is_stage_unlocked(stage_id):
            self._set_scene_message(f"Stage {stage_id} is locked.")
            return
        self._play_ui_select()
        self.start_stage(stage_id)

    def start_stage(self, stage_id: int) -> None:
        self.current_stage_id = stage_id
        self.current_stage = self.stages[stage_id]
        self.last_failure_reason = self.last_clear_time = self.last_stars = None
        self.last_play_message = ""
        self._last_bike_warning_rows = ()

        self.current_stage.initialize()

        self.timer.reset()
        self.timer.start()

        self.change_scene(PlayingScene())

    def start_next_stage(self) -> None:
        if self.current_stage_id is None:
            self._set_scene_message("No current stage is selected.")
            return

        next_stage_id = self.current_stage_id + 1
        if next_stage_id > MAX_STAGE_COUNT:
            self._set_scene_message("There is no next stage.")
            return

        self._play_ui_select()
        self.start_stage(next_stage_id)

    def restart_stage(self) -> None:
        if self.current_stage_id is None:
            self.open_stage_select()
            return
        self._play_ui_select()
        self.start_stage(self.current_stage_id)

    def return_to_main(self) -> None:
        self._play_ui_select()
        self.change_scene(MainScene())

    def move_player(self, direction: str) -> None:
        self._handle_move_result(self.current_stage.move_player(direction))

    def update_stage(self, dt: float) -> None:
        self._handle_stage_update_result(self.current_stage.update(dt))

    def fail_current_stage(self, reason: FailureReason) -> None:
        self.last_failure_reason = reason
        self.change_scene(FailedScene())
        self.sound_manager.play(SoundCue.FAILURE_SCREEN)

    def clear_current_stage(self) -> None:
        self.timer.stop()
        self.last_clear_time = self.timer.get_elapsed_time()
        self.last_stars = StarRating.calculate(
            self.last_clear_time, self.current_stage_id
        )
        self.progress.record_stage_clear(self.current_stage_id, self.last_stars)
        self.save_manager.save_progress(self.progress)

        self.change_scene(ResultScene())
        self.sound_manager.play(SoundCue.CLEAR_SCREEN)

    def _load_default_sounds(self) -> None:
        self.sound_manager.load(DEFAULT_SOUND_PATHS)

    def _play_ui_select(self) -> None:
        self.sound_manager.play(SoundCue.UI_SELECT)

    def _set_scene_message(self, message: str) -> None:
        set_message = getattr(self.current_scene, "set_message", None)
        if callable(set_message):
            set_message(message)

    def _fail_from_current_stage(self) -> None:
        if self.current_stage.failure_reason is not None:
            self.fail_current_stage(self.current_stage.failure_reason)

    def _play_failure_reason_sound(self) -> None:
        reason = getattr(self.current_stage, "failure_reason", None)
        if reason == FailureReason.FELL_IN_RIVER:
            self.sound_manager.play(SoundCue.LAKE_SPLASH)

    def _handle_move_result(self, result: str | None) -> None:
        if result == MOVE_FAILED:
            self._play_failure_reason_sound()
            self._fail_from_current_stage()
        elif result == MOVE_CLEARED:
            self.clear_current_stage()
        elif result in MOVE_MESSAGES:
            if result == MOVE_BLOCKED:
                self.sound_manager.play(
                    SoundCue.BLOCKED, channel_index=ACTION_SOUND_CHANNEL
                )
            if result == MOVE_MOVED:
                self.sound_manager.play(
                    SoundCue.MOVE_START, channel_index=ACTION_SOUND_CHANNEL
                )
            self.last_play_message = MOVE_MESSAGES[result]

    def _handle_stage_update_result(self, result: str | None) -> None:
        played_bike_warning = self._maybe_play_pending_bike_warning()

        if result == UPDATE_FAILED:
            self._play_failure_reason_sound()
            self._fail_from_current_stage()
        elif result == UPDATE_BIKE_AMBIENCE:
            if played_bike_warning:
                self.last_play_message = UPDATE_MESSAGES[result]
        elif result in UPDATE_MESSAGES:
            cue = UPDATE_CUES[result]
            self.sound_manager.play(
                cue,
                cooldown=UPDATE_CUE_COOLDOWNS.get(cue, 0.0),
                channel_index=UPDATE_CUE_CHANNELS.get(cue, ACTION_SOUND_CHANNEL),
            )
            self.last_play_message = UPDATE_MESSAGES[result]

    def _play_bike_warning_from_stage(self) -> bool:
        if self.current_stage is None:
            return False

        warning_rows = self._pending_bike_warning_rows()
        if not warning_rows:
            return False

        if not any(self._is_row_in_view(row) for row in warning_rows):
            return False

        self.sound_manager.play(
            SoundCue.BIKE_AMBIENCE,
            channel_index=BIKE_WARNING_CHANNEL,
        )
        return True

    def _maybe_play_pending_bike_warning(self) -> bool:
        if self.current_stage is None:
            self._last_bike_warning_rows = ()
            return False

        warning_rows = self._pending_bike_warning_rows()
        if not warning_rows:
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
        if callable(peek_warning_rows):
            return tuple(peek_warning_rows())
        peek_warning_row = getattr(self.current_stage, "peek_warning_bike_row", None)
        if callable(peek_warning_row):
            warning_row = peek_warning_row()
        else:
            warning_row = getattr(self.current_stage, "warning_row", None)
        return () if warning_row is None else (warning_row,)

    def _visible_row_window(self) -> tuple[int, int]:
        if self.current_stage is None:
            return (0, -1)

        rows = self.current_stage.terrain_map.rows
        columns = self.current_stage.terrain_map.columns
        if rows <= 0 or columns <= 0:
            return (0, -1)

        available_width = self.window_size[0] - _SCENE_SIDE_MARGIN * 2
        available_height = (
            self.window_size[1] - _SCENE_TOP_MARGIN - _SCENE_BOTTOM_MARGIN
        )
        if available_width <= 0 or available_height <= 0:
            return (0, -1)

        cell_size = max(MIN_TILE_SIZE, available_width / columns)
        grid_height = cell_size * rows
        if grid_height <= available_height:
            return (0, rows - 1)

        player_row = self.current_stage.player.position.row
        focus_center_y = player_row * cell_size + cell_size / 2
        desired_top = available_height / 2 - focus_center_y
        top = min(max(desired_top, available_height - grid_height), 0)
        first_row = max(0, math.floor(-top / cell_size))
        last_row = min(rows - 1, math.ceil((available_height - top) / cell_size) - 1)
        return (first_row, last_row)

    def _is_row_in_view(self, row: int) -> bool:
        start_row, end_row = self._visible_row_window()
        return start_row <= row <= end_row
