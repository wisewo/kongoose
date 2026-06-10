from pathlib import Path

from src import models, scenes
from src.models import SoundCue
from src.resources import ResourceManager, SoundManager
from src.stage_catalog import build_default_stages
from src.storage import SaveManager
from src.timing import StarRating, Timer

MAX_STAGE_COUNT = 4
SOUND_DIR = Path(__file__).resolve().parent.parent / "assets" / "sounds"
DEFAULT_SOUND_PATHS = {
    cue: SOUND_DIR / filename
    for cue, filename in (
        (SoundCue.MOVE_START, "player_jump_start.wav"),
        (SoundCue.MOVE_SUCCESS, "player_move_success.wav"),
        (SoundCue.BLOCKED, "blocked_obstacle.wav"),
        (SoundCue.TURTLE, "turtle_ride.wav"),
        (SoundCue.BIKE_AMBIENCE, "bike_ambience_loop.wav"),
        (SoundCue.BIKE_COLLISION, "bike_collision.wav"),
        (SoundCue.STUDENT_CROWD, "student_crowd.wav"),
        (SoundCue.WATER_AMBIENCE, "running_water.mp3"),
        (SoundCue.LAKE_SPLASH, "lake_game_over.wav"),
        (SoundCue.UI_SELECT, "ui_select.wav"),
        (SoundCue.BACKGROUND_MUSIC, "background_music.wav"),
        (SoundCue.FAILURE_SCREEN, "failure_screen.wav"),
        (SoundCue.CLEAR_SCREEN, "clear_screen.wav"),
    )
}
STAGE_AMBIENCE = {
    2: ((SoundCue.BIKE_AMBIENCE, 0.25),),
    3: ((SoundCue.WATER_AMBIENCE, 0.45),),
    4: ((SoundCue.BIKE_AMBIENCE, 0.25), (SoundCue.WATER_AMBIENCE, 0.45)),
}
AMBIENCE_CUES = (SoundCue.BIKE_AMBIENCE, SoundCue.WATER_AMBIENCE)
MOVE_SOUNDS = {
    models.MOVE_BLOCKED: SoundCue.BLOCKED,
    models.MOVE_MOVED: SoundCue.MOVE_START,
}


class Game:
    def __init__(
        self,
        window_size=(960, 720),
        title="길Kon너 Goose들",
        initial_scene=None,
        stages=None,
    ):
        self.window_size, self.title = window_size, title
        self.screen = self.clock = None
        self.running = False
        self.current_scene = None
        self.stages = dict(stages) if stages is not None else build_default_stages()
        self.save_manager, self.timer = SaveManager(), Timer()
        self.sound_manager, self.resource_manager = SoundManager(), ResourceManager()
        self.progress = self.save_manager.load_progress()
        self.current_stage_id = None
        self.last_failure_reason = self.last_clear_time = self.last_stars = None
        if initial_scene is not None:
            self.change_scene(initial_scene)

    @property
    def current_stage(self):
        return self.stages[self.current_stage_id]

    def run(self) -> None:
        import pygame

        pygame.init()
        pygame.display.set_caption(self.title)
        self.screen = pygame.display.set_mode(self.window_size)
        self.clock = pygame.time.Clock()
        self.sound_manager.load(DEFAULT_SOUND_PATHS)
        self.sound_manager.play(SoundCue.BACKGROUND_MUSIC, loops=-1)
        self.running = True
        if self.current_scene is None:
            self.change_scene(scenes.MainScene())
        while self.running:
            dt = self.clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                else:
                    self.current_scene.handle_event(event)
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
        self._stop_stage_ambience()
        self.sound_manager.play(SoundCue.UI_SELECT)
        self.change_scene(scenes.StageSelectScene())

    def select_stage(self, stage_id: int) -> None:
        if not self.progress.is_stage_unlocked(stage_id):
            self.current_scene.set_message(f"Stage {stage_id} is locked.")
            return
        self.sound_manager.play(SoundCue.UI_SELECT)
        self.start_stage(stage_id)

    def start_stage(self, stage_id: int) -> None:
        self.current_stage_id = stage_id
        self.last_failure_reason = self.last_clear_time = self.last_stars = None
        self.current_stage.initialize()
        self.timer.reset()
        self.timer.start()
        self.change_scene(scenes.PlayingScene())
        self._sync_stage_ambience()

    def start_next_stage(self) -> None:
        next_stage_id = self.current_stage_id + 1
        if next_stage_id > MAX_STAGE_COUNT:
            self.current_scene.set_message("There is no next stage.")
            return
        self.sound_manager.play(SoundCue.UI_SELECT)
        self.start_stage(next_stage_id)

    def restart_stage(self) -> None:
        self.sound_manager.play(SoundCue.UI_SELECT)
        self.start_stage(self.current_stage_id)

    def return_to_main(self) -> None:
        self._stop_stage_ambience()
        self.sound_manager.play(SoundCue.UI_SELECT)
        self.change_scene(scenes.MainScene())

    def move_player(self, direction: str) -> str | None:
        result = self.current_stage.move_player(direction)
        self._handle_move_result(result)
        return result

    def update_stage(self, dt: float) -> None:
        result = self.current_stage.update(dt)
        self._handle_stage_update_result(result)

    def fail_current_stage(self, reason) -> None:
        self.last_failure_reason = reason
        self._stop_stage_ambience()
        self.change_scene(scenes.FailedScene())
        self.sound_manager.play(SoundCue.FAILURE_SCREEN)

    def clear_current_stage(self) -> None:
        self.timer.stop()
        self._stop_stage_ambience()
        self.last_clear_time = self.timer.get_elapsed_time()
        stage_id = self.current_stage_id
        self.last_stars = StarRating.calculate(self.last_clear_time, stage_id)
        self.progress.record_stage_clear(stage_id, self.last_stars)
        self.save_manager.save_progress(self.progress)
        self.change_scene(scenes.ResultScene())
        self.sound_manager.play(SoundCue.CLEAR_SCREEN)

    def _handle_failure_from_stage(self) -> None:
        reason = self.current_stage.failure_reason
        if reason == models.FailureReason.FELL_IN_RIVER:
            self.sound_manager.play(SoundCue.LAKE_SPLASH)
        if reason == models.FailureReason.HIT_BIKE:
            self.sound_manager.play(SoundCue.BIKE_COLLISION)
        self.fail_current_stage(reason)

    def _handle_move_result(self, result: str | None) -> None:
        if result == models.MOVE_FAILED:
            self._handle_failure_from_stage()
            return
        if result == models.MOVE_CLEARED:
            self.clear_current_stage()
            return
        if cue := MOVE_SOUNDS.get(result):
            if (
                result == models.MOVE_MOVED
                and self.current_stage.player.mounted_turtle is not None
            ):
                cue = SoundCue.TURTLE
            self.sound_manager.play(cue)

    def _handle_stage_update_result(self, result: str | None) -> None:
        if result == models.UPDATE_FAILED:
            self._handle_failure_from_stage()
            return
        if result == models.UPDATE_STUDENT_CROWD_ACTIVE:
            self.sound_manager.play(SoundCue.STUDENT_CROWD)
            return

    def _sync_stage_ambience(self) -> None:
        self._stop_stage_ambience()
        for cue, volume in STAGE_AMBIENCE.get(self.current_stage_id, ()):
            self.sound_manager.play(cue, loops=-1, volume=volume)

    def _stop_stage_ambience(self) -> None:
        for cue in AMBIENCE_CUES:
            self.sound_manager.stop(cue)
