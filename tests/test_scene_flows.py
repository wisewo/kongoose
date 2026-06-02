from __future__ import annotations

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from kongoose.game import Game
from kongoose.models import Direction, FailureReason
from kongoose.results import MoveResult, StageUpdateResult
from kongoose.scenes import (
    FailedScene,
    MainScene,
    PlayingScene,
    ResultScene,
    StageSelectScene,
)


class ProgressStub:
    def __init__(self, unlocked_stages: set[int] | None = None) -> None:
        self.unlocked_stages = unlocked_stages or {1}
        self.best_stars: dict[int, int] = {}

    def is_stage_unlocked(self, stage_id: int) -> bool:
        return stage_id in self.unlocked_stages

    def get_best_stars(self, stage_id: int) -> int:
        return self.best_stars.get(stage_id, 0)

    def record_stage_clear(self, stage_id: int, stars: int) -> None:
        self.best_stars[stage_id] = max(stars, self.get_best_stars(stage_id))
        self.unlocked_stages.add(stage_id + 1)


class SaveManagerStub:
    def __init__(self) -> None:
        self.saved_progress: ProgressStub | None = None

    def save_progress(self, progress: ProgressStub) -> None:
        self.saved_progress = progress


class StageStub:
    def __init__(self) -> None:
        self.initialized = False
        self.moves: list[Direction] = []
        self.update_count = 0
        self.next_move_result = MoveResult.moved()
        self.next_update_result = StageUpdateResult.safe()

    def initialize(self) -> None:
        self.initialized = True

    def move_player(self, direction: Direction) -> MoveResult:
        self.moves.append(direction)
        return self.next_move_result

    def update(self, dt: float) -> StageUpdateResult:
        self.update_count += 1
        return self.next_update_result


class TimerStub:
    def __init__(self) -> None:
        self.reset_count = 0
        self.start_count = 0
        self.stopped = False

    def reset(self) -> None:
        self.reset_count += 1

    def start(self) -> None:
        self.start_count += 1

    def stop(self) -> None:
        self.stopped = True

    def get_elapsed_time(self) -> float:
        return 12.5


def key_event(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_main_scene_opens_stage_select_and_quits_from_keys() -> None:
    game = Game(initial_scene=MainScene())

    game.current_scene.handle_event(key_event(pygame.K_RETURN))

    assert isinstance(game.current_scene, StageSelectScene)

    game.running = True
    game.return_to_main()
    game.current_scene.handle_event(key_event(pygame.K_q))

    assert not game.running


def test_stage_select_starts_unlocked_stage_and_rejects_locked_stage() -> None:
    game = Game(initial_scene=StageSelectScene())
    stage = StageStub()
    timer = TimerStub()
    game.progress = ProgressStub({1})
    game.stages = {1: stage}
    game.timer = timer

    game.current_scene.handle_event(key_event(pygame.K_2))

    assert isinstance(game.current_scene, StageSelectScene)
    assert game.current_scene._message == "Stage 2 is locked."

    game.current_scene.handle_event(key_event(pygame.K_1))

    assert isinstance(game.current_scene, PlayingScene)
    assert game.current_stage_id == 1
    assert stage.initialized
    assert timer.reset_count == 1
    assert timer.start_count == 1


def test_playing_scene_moves_player_updates_stage_and_returns_to_select() -> None:
    game = Game(initial_scene=PlayingScene())
    stage = StageStub()
    game.current_stage = stage

    game.current_scene.handle_event(key_event(pygame.K_UP))
    game.current_scene.update(0.016)

    assert stage.moves == [Direction.UP]
    assert game.last_play_message == "Moved."
    assert stage.update_count == 1

    game.current_scene.handle_event(key_event(pygame.K_ESCAPE))

    assert isinstance(game.current_scene, StageSelectScene)


def test_playing_scene_changes_to_failed_or_result_for_stage_outcomes() -> None:
    game = Game(initial_scene=PlayingScene())
    stage = StageStub()
    timer = TimerStub()
    save_manager = SaveManagerStub()
    game.current_stage = stage
    game.current_stage_id = 1
    game.progress = ProgressStub({1})
    game.save_manager = save_manager
    game.timer = timer

    stage.next_move_result = MoveResult.failed(FailureReason.HIT_BIKE)
    game.current_scene.handle_event(key_event(pygame.K_RIGHT))

    assert isinstance(game.current_scene, FailedScene)
    assert game.last_failure_reason is FailureReason.HIT_BIKE

    game.change_scene(PlayingScene())
    stage.next_move_result = MoveResult.cleared()
    game.current_scene.handle_event(key_event(pygame.K_RIGHT))

    assert isinstance(game.current_scene, ResultScene)
    assert timer.stopped
    assert game.last_clear_time == 12.5
    assert game.last_stars == 3
    assert save_manager.saved_progress is game.progress


def test_failed_scene_actions_restart_select_or_main() -> None:
    game = Game(initial_scene=FailedScene())
    game.current_stage_id = 1
    game.stages = {1: StageStub()}
    game.timer = TimerStub()

    game.current_scene.handle_event(key_event(pygame.K_r))
    assert isinstance(game.current_scene, PlayingScene)

    game.change_scene(FailedScene())
    game.current_scene.handle_event(key_event(pygame.K_s))
    assert isinstance(game.current_scene, StageSelectScene)

    game.change_scene(FailedScene())
    game.current_scene.handle_event(key_event(pygame.K_m))
    assert isinstance(game.current_scene, MainScene)


def test_result_scene_actions_next_restart_select_or_main() -> None:
    game = Game(initial_scene=ResultScene())
    game.current_stage_id = 1
    game.stages = {1: StageStub(), 2: StageStub()}
    game.timer = TimerStub()

    game.current_scene.handle_event(key_event(pygame.K_n))
    assert isinstance(game.current_scene, PlayingScene)
    assert game.current_stage_id == 2

    game.change_scene(ResultScene())
    game.current_scene.handle_event(key_event(pygame.K_r))
    assert isinstance(game.current_scene, PlayingScene)
    assert game.current_stage_id == 2

    game.change_scene(ResultScene())
    game.current_scene.handle_event(key_event(pygame.K_b))
    assert isinstance(game.current_scene, StageSelectScene)

    game.change_scene(ResultScene())
    game.current_scene.handle_event(key_event(pygame.K_ESCAPE))
    assert isinstance(game.current_scene, MainScene)
