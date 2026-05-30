from __future__ import annotations

from dataclasses import dataclass

from kongoose.models import FailureReason, MoveResultType, StageUpdateResultType


@dataclass(frozen=True, slots=True)
class MoveResult:
    result_type: MoveResultType
    failure_reason: FailureReason | None = None

    @classmethod
    def blocked(cls) -> MoveResult:
        return cls(MoveResultType.BLOCKED)

    @classmethod
    def moved(cls) -> MoveResult:
        return cls(MoveResultType.MOVED)

    @classmethod
    def cleared(cls) -> MoveResult:
        return cls(MoveResultType.CLEARED)

    @classmethod
    def failed(cls, failure_reason: FailureReason) -> MoveResult:
        return cls(MoveResultType.FAILED, failure_reason)

    def is_moved(self) -> bool:
        return self.result_type is MoveResultType.MOVED

    def is_blocked(self) -> bool:
        return self.result_type is MoveResultType.BLOCKED

    def is_cleared(self) -> bool:
        return self.result_type is MoveResultType.CLEARED

    def is_failed(self) -> bool:
        return self.result_type is MoveResultType.FAILED

    def get_failure_reason(self) -> FailureReason | None:
        return self.failure_reason


@dataclass(frozen=True, slots=True)
class StageUpdateResult:
    result_type: StageUpdateResultType
    failure_reason: FailureReason | None = None

    @classmethod
    def safe(cls) -> StageUpdateResult:
        return cls(StageUpdateResultType.SAFE)

    @classmethod
    def warning(cls) -> StageUpdateResult:
        return cls(StageUpdateResultType.WARNING)

    @classmethod
    def turtle_ride(cls) -> StageUpdateResult:
        return cls(StageUpdateResultType.TURTLE_RIDE)

    @classmethod
    def bike_ambience(cls) -> StageUpdateResult:
        return cls(StageUpdateResultType.BIKE_AMBIENCE)

    @classmethod
    def failure(cls, failure_reason: FailureReason) -> StageUpdateResult:
        return cls(StageUpdateResultType.FAILURE, failure_reason)

    def is_safe(self) -> bool:
        return self.result_type is StageUpdateResultType.SAFE

    def is_warning(self) -> bool:
        return self.result_type is StageUpdateResultType.WARNING

    def is_turtle_ride(self) -> bool:
        return self.result_type is StageUpdateResultType.TURTLE_RIDE

    def needs_bike_ambience(self) -> bool:
        return self.result_type is StageUpdateResultType.BIKE_AMBIENCE

    def is_failure(self) -> bool:
        return self.result_type is StageUpdateResultType.FAILURE

    def get_failure_reason(self) -> FailureReason | None:
        return self.failure_reason
