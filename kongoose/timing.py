import time


class Timer:
    def __init__(self, clock=None) -> None:
        self._clock = clock or time.perf_counter
        self._start_time, self._elapsed_time = None, 0.0

    def start(self) -> None:
        if self._start_time is None:
            self._start_time = self._clock()

    def stop(self) -> None:
        if self._start_time is not None:
            self._elapsed_time += self._clock() - self._start_time
            self._start_time = None

    def reset(self) -> None:
        self._start_time, self._elapsed_time = None, 0.0

    def get_elapsed_time(self) -> float:
        if self._start_time is None:
            return self._elapsed_time
        return self._elapsed_time + self._clock() - self._start_time


class StarRating:
    _THRESHOLDS = {
        1: (40.0, 60.0),
        2: (75.0, 113.0),
        3: (75.0, 113.0),
        4: (100.0, 150.0),
    }

    @classmethod
    def calculate(cls, clear_time: float, stage_id: int) -> int:
        if clear_time < 0:
            raise ValueError("clear_time must not be negative")
        if stage_id not in cls._THRESHOLDS:
            raise ValueError("unknown stage_id")
        three_star_time, two_star_time = cls._THRESHOLDS[stage_id]
        if clear_time <= three_star_time:
            return 3
        return 2 if clear_time <= two_star_time else 1
