import random
from pathlib import Path

from kongoose import models as M
from kongoose import scenes
from kongoose.models import SoundCue as S
from kongoose.resources import ResourceManager, SoundManager
from kongoose.stage_catalog import build_default_stages
from kongoose.storage import SaveManager
from kongoose.timing import StarRating, Timer

MAX_STAGE_COUNT = 4
BIKE_AMBIENCE_INTERVAL_RANGE = (2.0, 5.0)
BIKE_AMBIENCE_BELL_COUNT_RANGE = (1, 3)
BIKE_AMBIENCE_VOLUME_RANGE = (0.2, 1.0)
SOUND_DIR = Path(__file__).resolve().parent.parent / "assets" / "sounds"
DEFAULT_SOUND_PATHS = {
    cue: SOUND_DIR / filename
    for cue, filename in (
        (S.MOVE_START, "player_jump_start.wav"),
        (S.MOVE_SUCCESS, "player_move_success.wav"),
        (S.BLOCKED, "blocked_obstacle.wav"),
        (S.TURTLE, "turtle_ride.wav"),
        (S.BIKE_AMBIENCE, "bike_appear.wav"),
        (S.STUDENT_CROWD, "student_crowd.wav"),
        (S.WATER_AMBIENCE, "running_water.mp3"),
        (S.LAKE_SPLASH, "lake_game_over.wav"),
        (S.UI_SELECT, "ui_select.wav"),
        (S.BACKGROUND_MUSIC, "background_music.wav"),
        (S.FAILURE_SCREEN, "failure_screen.wav"),
        (S.CLEAR_SCREEN, "clear_screen.wav"),
    )
}
MOVE_SOUNDS = {
    M.MOVE_BLOCKED: S.BLOCKED,
    M.MOVE_MOVED: S.MOVE_START,
}


class Game:
    def __init__(
        self,
        window_size=(960, 720),
        title="Kongoose",
        initial_scene=None,
        stages=None,
        rng=None,
    ):
        self.window_size, self.title = window_size, title
        self._rng = rng or random.Random()
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
        self._bike_ambience_elapsed = 0.0
        self._next_bike_ambience_delay = self._random_bike_ambience_delay()
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

    def change_scene(self, scene) -> None:
        self.current_scene = scene
        scene.enter(self)

    def quit_game(self) -> None:
        self.running = False

    def open_stage_select(self) -> None:
        self._stop_water_ambience()
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
        self._reset_bike_ambience_timer()
        self.current_stage.initialize()
        self.timer.reset()
        self.timer.start()
        self.change_scene(scenes.PlayingScene())
        self._sync_water_ambience()

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
        self._stop_water_ambience()
        self.sound_manager.play(S.UI_SELECT)
        self.change_scene(scenes.MainScene())

    def move_player(self, direction: str) -> None:
        self._handle_move_result(self.current_stage.move_player(direction))

    def update_stage(self, dt: float) -> None:
        result = self.current_stage.update(dt)
        self._handle_stage_update_result(result)
        if result != M.UPDATE_FAILED:
            self._update_bike_ambience(dt)

    def fail_current_stage(self, reason) -> None:
        self.last_failure_reason = reason
        self._stop_water_ambience()
        self.change_scene(scenes.FailedScene())
        self.sound_manager.play(S.FAILURE_SCREEN)

    def clear_current_stage(self) -> None:
        self.timer.stop()
        self._stop_water_ambience()
        self.last_clear_time = self.timer.get_elapsed_time()
        stage_id = self.current_stage_id
        self.last_stars = StarRating.calculate(self.last_clear_time, stage_id)
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
            player = getattr(self.current_stage, "player", None)
            mounted_turtle = getattr(player, "mounted_turtle", None)
            if result == M.MOVE_MOVED and mounted_turtle is not None:
                cue = S.TURTLE
            self.sound_manager.play(cue)

    def _handle_stage_update_result(self, result: str | None) -> None:
        if result == M.UPDATE_FAILED:
            self._handle_failure_from_stage()
            return
        if result == M.UPDATE_STUDENT_CROWD_ACTIVE:
            self.sound_manager.play(S.STUDENT_CROWD)
            return
        if result in (None, M.UPDATE_TURTLE_RIDE):
            return

    def _update_bike_ambience(self, dt: float) -> None:
        if not getattr(self.current_stage, "bikes", ()):
            return
        self._bike_ambience_elapsed += dt
        if self._bike_ambience_elapsed < self._next_bike_ambience_delay:
            return
        self._bike_ambience_elapsed = 0.0
        self._play_bike_ambience_burst()
        self._next_bike_ambience_delay = self._random_bike_ambience_delay()

    def _play_bike_ambience_burst(self) -> None:
        minimum, maximum = BIKE_AMBIENCE_BELL_COUNT_RANGE
        for _count in range(self._rng.randint(minimum, maximum)):
            volume = self._random_bike_ambience_volume()
            self.sound_manager.play(S.BIKE_AMBIENCE, volume=volume)

    def _random_bike_ambience_delay(self) -> float:
        return self._rng.uniform(*BIKE_AMBIENCE_INTERVAL_RANGE)

    def _random_bike_ambience_volume(self) -> float:
        return self._rng.uniform(*BIKE_AMBIENCE_VOLUME_RANGE)

    def _reset_bike_ambience_timer(self) -> None:
        self._bike_ambience_elapsed = 0.0
        self._next_bike_ambience_delay = self._random_bike_ambience_delay()

    def _sync_water_ambience(self) -> None:
        self._stop_water_ambience()
        terrain = getattr(self.current_stage, "terrain_map", None)
        if terrain is not None and terrain.has_terrain(M.TerrainType.RIVER):
            self.sound_manager.play(S.WATER_AMBIENCE, loops=-1, volume=0.45)

    def _stop_water_ambience(self) -> None:
        self.sound_manager.stop(S.WATER_AMBIENCE)
