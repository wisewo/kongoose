import json
import wave
from inspect import signature
from pathlib import Path

from kongoose.game import DEFAULT_SOUND_PATHS
from kongoose.models import SoundCue
from kongoose.resources import ResourceManager, SoundManager
from kongoose.storage import Progress, SaveManager
from kongoose.timing import StarRating, Timer


def test_progress_unlocks_next_stage_and_keeps_best_star_score() -> None:
    progress = Progress()

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
    progress = Progress()
    progress.record_stage_clear(stage_id=1, stars=3)
    progress.record_stage_clear(stage_id=2, stars=1)

    SaveManager(save_path).save_progress(progress)
    loaded = SaveManager(save_path).load_progress()

    assert loaded.get_unlocked_stages() == [1, 2, 3]
    assert loaded.get_best_stars(1) == 3
    assert loaded.get_best_stars(2) == 1
    assert json.loads(save_path.read_text(encoding="utf-8")) == {
        "unlocked_stages": [1, 2, 3],
        "best_stars": {"1": 3, "2": 1},
    }


def test_save_manager_returns_default_progress_when_file_is_missing(tmp_path) -> None:
    progress = SaveManager(tmp_path / "missing.json").load_progress()

    assert progress.get_unlocked_stages() == [1]
    assert progress.get_best_stars(1) == 0


def test_star_rating_uses_stage_balance_thresholds() -> None:
    assert StarRating.calculate(clear_time=15, stage_id=1) == 3
    assert StarRating.calculate(clear_time=30, stage_id=1) == 2
    assert StarRating.calculate(clear_time=30.1, stage_id=1) == 1
    assert StarRating.calculate(clear_time=20, stage_id=2) == 3
    assert StarRating.calculate(clear_time=40, stage_id=2) == 2
    assert StarRating.calculate(clear_time=40.1, stage_id=2) == 1
    assert StarRating.calculate(clear_time=60, stage_id=3) == 3
    assert StarRating.calculate(clear_time=85, stage_id=3) == 2
    assert StarRating.calculate(clear_time=85.1, stage_id=3) == 1
    assert StarRating.calculate(clear_time=100, stage_id=4) == 3
    assert StarRating.calculate(clear_time=120, stage_id=4) == 2
    assert StarRating.calculate(clear_time=120.1, stage_id=4) == 1


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

    assert resource_manager.get_image("player") is image
    assert resource_manager.get_image("missing") is None


def test_sound_manager_ignores_missing_cues_and_plays_registered_sound() -> None:
    sound_manager = SoundManager()
    sound = FakeSound()

    sound_manager.register_sound(SoundCue.MOVE_START, sound)

    assert sound_manager.play("missing") is False
    assert sound_manager.play(SoundCue.MOVE_START) is True
    assert sound.play_count == 1
    assert sound.played_loops == [0]


def test_sound_cues_match_runtime_actions() -> None:
    assert not hasattr(SoundCue, "MOVE")
    assert SoundCue.BIKE_COLLISION == "bike_collision"


def test_default_sound_paths_include_bike_collision_sound() -> None:
    assert DEFAULT_SOUND_PATHS[SoundCue.BIKE_COLLISION].name == "bike_collision.wav"


def test_bike_collision_sound_volume_is_not_full_scale() -> None:
    sound_path = DEFAULT_SOUND_PATHS[SoundCue.BIKE_COLLISION]

    assert _sound_peak_ratio(sound_path) <= 0.5


def test_sound_manager_keeps_playback_policy_simple() -> None:
    play_parameters = signature(SoundManager.play).parameters

    assert set(play_parameters) == {"self", "cue", "loops", "volume"}
    assert set(signature(SoundManager.stop).parameters) == {"self", "cue"}


def test_sound_manager_passes_loop_count_and_optional_volume() -> None:
    sound_manager = SoundManager()
    sound = FakeSound()
    sound_manager.register_sound(SoundCue.BACKGROUND_MUSIC, sound)

    assert sound_manager.play(SoundCue.BACKGROUND_MUSIC, loops=-1, volume=0.75) is True
    assert sound.played_loops == [-1]
    assert sound.channels[0].volumes == [0.75]


def test_sound_manager_stops_the_last_channel_for_a_cue() -> None:
    sound_manager = SoundManager()
    sound = FakeSound()
    sound_manager.register_sound(SoundCue.BACKGROUND_MUSIC, sound)

    sound_manager.play(SoundCue.BACKGROUND_MUSIC, loops=-1)
    sound_manager.stop(SoundCue.BACKGROUND_MUSIC)
    sound_manager.stop("missing")

    assert sound.channels[0].stopped


class FakeSound:
    def __init__(self) -> None:
        self.play_count = 0
        self.played_loops: list[int] = []
        self.channels: list[FakeChannel] = []

    def play(self, loops: int = 0):
        self.play_count += 1
        self.played_loops.append(loops)
        channel = FakeChannel()
        self.channels.append(channel)
        return channel

    def stop(self) -> None:
        for channel in self.channels:
            channel.stop()


class FakeChannel:
    def __init__(self) -> None:
        self.volumes: list[float] = []
        self.stopped = False

    def set_volume(self, volume: float) -> None:
        self.volumes.append(volume)

    def stop(self) -> None:
        self.stopped = True


def _sound_peak_ratio(sound_path: Path) -> float:
    with wave.open(str(sound_path), "rb") as sound_file:
        sample_width = sound_file.getsampwidth()
        frames = sound_file.readframes(sound_file.getnframes())
    peak = max(abs(sample) for sample in _samples(frames, sample_width))
    max_possible = 2 ** (8 * sample_width - 1)
    return peak / max_possible


def _samples(frames: bytes, sample_width: int) -> list[int]:
    if sample_width != 2:
        raise ValueError("only 16-bit wav files are supported")
    return [
        int.from_bytes(frames[index : index + 2], "little", signed=True)
        for index in range(0, len(frames), 2)
    ]
