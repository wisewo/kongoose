from __future__ import annotations

from typing import Any

from kongoose.models import Direction, FailureReason
from kongoose.resources import ResourceManager, SoundManager
from kongoose.scenes import (
    FailedScene,
    MainScene,
    PlayingScene,
    ResultScene,
    Scene,
    StageSelectScene,
)
from kongoose.storage import SaveManager
from kongoose.timing import StarRating, Timer

MAX_STAGE_COUNT = 4


class Game:
    def __init__(
        self,
        window_size: tuple[int, int] = (960, 720),
        title: str = "Kongoose",
        initial_scene: Scene | None = None,
    ) -> None:
        self.window_size = window_size
        self.title = title
        self.screen: Any | None = None
        self.clock: Any | None = None
        self.running = False
        self.current_scene: Scene | None = None
        self.stages: dict[int, Any] = {}
        self.current_stage: Any | None = None
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

        if initial_scene is not None:
            self.change_scene(initial_scene)

    def run(self) -> None:
        import pygame

        pygame.init()
        pygame.display.set_caption(self.title)
        self.screen = pygame.display.set_mode(self.window_size)
        self.clock = pygame.time.Clock()
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

    def get_stage_list(self) -> list[Any]:
        return list(self.stages.values())

    def open_stage_select(self) -> None:
        self.change_scene(StageSelectScene())

    def select_stage(self, stage_id: int) -> None:
        if not self.progress.is_stage_unlocked(stage_id):
            self._set_scene_message(f"Stage {stage_id} is locked.")
            return
        self.start_stage(stage_id)

    def start_stage(self, stage_id: int) -> None:
        self.current_stage_id = stage_id
        self.current_stage = self.stages.get(stage_id)
        self.last_failure_reason = None
        self.last_clear_time = None
        self.last_stars = None
        self.last_play_message = ""

        initialize = getattr(self.current_stage, "initialize", None)
        if callable(initialize):
            initialize()

        self.timer.reset()
        self.timer.start()

        if self.current_stage is None:
            self.last_play_message = "Stage data is not connected yet."

        self.change_scene(PlayingScene())

    def start_next_stage(self) -> None:
        if self.current_stage_id is None:
            self._set_scene_message("No current stage is selected.")
            return

        next_stage_id = self.current_stage_id + 1
        if next_stage_id > MAX_STAGE_COUNT:
            self._set_scene_message("There is no next stage.")
            return

        self.start_stage(next_stage_id)

    def restart_stage(self) -> None:
        if self.current_stage_id is None:
            self.open_stage_select()
            return
        self.start_stage(self.current_stage_id)

    def return_to_main(self) -> None:
        self.change_scene(MainScene())

    def move_player(self, direction: Direction) -> None:
        move_player = getattr(self.current_stage, "move_player", None)
        if not callable(move_player):
            self.last_play_message = "Stage movement is not connected yet."
            return

        result = move_player(direction)
        self._handle_move_result(result)

    def update_stage(self, dt: float) -> None:
        update_stage = getattr(self.current_stage, "update", None)
        if not callable(update_stage):
            return

        result = update_stage(dt)
        self._handle_stage_update_result(result)

    def fail_current_stage(self, reason: FailureReason) -> None:
        self.last_failure_reason = reason
        self.change_scene(FailedScene())

    def clear_current_stage(self) -> None:
        self.timer.stop()

        if self.current_stage_id is None:
            self.last_clear_time = None
            self.last_stars = None
        else:
            self.last_clear_time = self.timer.get_elapsed_time()
            self.last_stars = StarRating.calculate(
                self.last_clear_time,
                self.current_stage_id,
            )
            self.progress.record_stage_clear(self.current_stage_id, self.last_stars)
            self.save_manager.save_progress(self.progress)

        self.change_scene(ResultScene())

    def _set_scene_message(self, message: str) -> None:
        set_message = getattr(self.current_scene, "set_message", None)
        if callable(set_message):
            set_message(message)

    def _handle_move_result(self, result: Any) -> None:
        if result is None:
            return

        if result.is_failed():
            reason = result.get_failure_reason()
            if reason is not None:
                self.fail_current_stage(reason)
            return

        if result.is_cleared():
            self.clear_current_stage()
            return

        if result.is_blocked():
            self.last_play_message = "Blocked by terrain."
            return

        if result.is_moved():
            self.last_play_message = "Moved."

    def _handle_stage_update_result(self, result: Any) -> None:
        if result is None:
            return

        if result.is_failure():
            reason = result.get_failure_reason()
            if reason is not None:
                self.fail_current_stage(reason)
            return

        if result.is_warning():
            self.last_play_message = "Running crew warning."
            return

        if result.is_turtle_ride():
            self.last_play_message = "Riding a turtle."
            return

        if result.needs_bike_ambience():
            self.last_play_message = "Bike nearby."
