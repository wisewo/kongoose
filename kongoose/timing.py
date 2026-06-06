import time
from collections.abc import Callable


class Timer:
    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.perf_counter
        self._start_time: float | None = None
        self._elapsed_time = 0.0

    def start(self) -> None:
        if self._start_time is None:
            self._start_time = self._clock()

    def stop(self) -> None:
        if self._start_time is not None:
            self._elapsed_time += self._clock() - self._start_time
            self._start_time = None

    def reset(self) -> None:
        self._start_time = None
        self._elapsed_time = 0.0

    def get_elapsed_time(self) -> float:
        if self._start_time is None:
            return self._elapsed_time
        return self._elapsed_time + self._clock() - self._start_time


class StarRating:
    _THRESHOLDS = {
        1: (45.0, 68.0, 100.0),
        2: (55.0, 83.0, 120.0),
        3: (65.0, 98.0, 145.0),
        4: (80.0, 120.0, 175.0),
    }

    @classmethod
    def calculate(cls, clear_time: float, stage_id: int) -> int:
        if clear_time < 0:
            raise ValueError("clear_time must not be negative")
        if stage_id not in cls._THRESHOLDS:
            raise ValueError("unknown stage_id")

        three_star_time, two_star_time, _one_star_time = cls._THRESHOLDS[stage_id]
        if clear_time <= three_star_time:
            return 3
        if clear_time <= two_star_time:
            return 2
        return 1
