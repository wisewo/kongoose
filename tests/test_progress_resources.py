from __future__ import annotations

import json

from kongoose.models import SoundCue
from kongoose.resources import ResourceManager, SoundManager
from kongoose.storage import Progress, SaveManager
from kongoose.timing import StarRating, Timer


def test_progress_unlocks_next_stage_and_keeps_best_star_score() -> None:
    progress = Progress(total_stages=4)

    assert progress.get_unlocked_stages() == [1]
    assert progress.is_stage_unlocked(1)
    assert not progress.is_stage_unlocked(2)

    progress.record_stage_clear(stage_id=1, stars=2)

    assert progress.get_unlocked_stages() == [1, 2]
    assert progress.is_stage_unlocked(2)
    assert progress.get_best_stars(1) == 2

    progress.record_stage_clear(stage_id=1, stars=1)

    assert progress.get_best_stars(1) == 2


def test_save_manager_round_trips_progress_as_json(tmp_path) -> None:
    save_path = tmp_path / "progress.json"
    progress = Progress(total_stages=4)
    progress.record_stage_clear(stage_id=1, stars=3)
    progress.record_stage_clear(stage_id=2, stars=1)

    SaveManager(save_path).save_progress(progress)
    loaded = SaveManager(save_path).load_progress()

    assert loaded.get_unlocked_stages() == [1, 2, 3]
    assert loaded.get_best_stars(1) == 3
    assert loaded.get_best_stars(2) == 1
    assert json.loads(save_path.read_text(encoding="utf-8")) == {
        "total_stages": 4,
        "unlocked_stages": [1, 2, 3],
        "best_stars": {"1": 3, "2": 1},
    }


def test_save_manager_returns_default_progress_when_file_is_missing(tmp_path) -> None:
    progress = SaveManager(tmp_path / "missing.json").load_progress()

    assert progress.get_unlocked_stages() == [1]
    assert progress.get_best_stars(1) == 0


def test_star_rating_uses_stage_balance_thresholds() -> None:
    assert StarRating.calculate(clear_time=20, stage_id=1) == 3
    assert StarRating.calculate(clear_time=30, stage_id=1) == 2
    assert StarRating.calculate(clear_time=45, stage_id=1) == 1
    assert StarRating.calculate(clear_time=46, stage_id=1) == 1
    assert StarRating.calculate(clear_time=35, stage_id=4) == 3
    assert StarRating.calculate(clear_time=52, stage_id=4) == 2
    assert StarRating.calculate(clear_time=75, stage_id=4) == 1


def test_timer_tracks_elapsed_time_with_injected_clock() -> None:
    current_time = 10.0

    def now() -> float:
        return current_time

    timer = Timer(clock=now)
    timer.start()
    current_time = 12.5

    assert timer.get_elapsed_time() == 2.5

    timer.stop()
    current_time = 20.0

    assert timer.get_elapsed_time() == 2.5

    timer.reset()

    assert timer.get_elapsed_time() == 0.0


def test_resource_manager_registers_and_retrieves_images() -> None:
    resource_manager = ResourceManager()
    image = object()

    resource_manager.register_image("player", image)

    assert resource_manager.has_image("player")
    assert resource_manager.get_image("player") is image
    assert not resource_manager.has_image("missing")
    assert resource_manager.get_image("missing") is None


def test_sound_manager_ignores_missing_cues_and_plays_registered_sound() -> None:
    sound_manager = SoundManager()
    sound = FakeSound()

    sound_manager.register_sound(SoundCue.MOVE, sound)

    assert sound_manager.play(SoundCue.FAILURE) is False
    assert sound_manager.play(SoundCue.MOVE) is True
    assert sound.play_count == 1


class FakeSound:
    def __init__(self) -> None:
        self.play_count = 0

    def play(self) -> None:
        self.play_count += 1
