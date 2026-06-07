import json
from dataclasses import dataclass
from pathlib import Path

MAX_STAGE_COUNT = 4


@dataclass
class Progress:
    unlocked_stages: set[int] | None = None
    best_stars: dict[int, int] | None = None

    def __post_init__(self) -> None:
        self.unlocked_stages = (self.unlocked_stages or set()) | {1}
        self.best_stars = {} if self.best_stars is None else self.best_stars

    def get_unlocked_stages(self) -> list[int]:
        return sorted(self.unlocked_stages)

    def is_stage_unlocked(self, stage_id: int) -> bool:
        return stage_id in self.unlocked_stages

    def get_best_stars(self, stage_id: int) -> int:
        return self.best_stars.get(stage_id, 0)

    def record_stage_clear(self, stage_id: int, stars: int) -> None:
        if not (1 <= stage_id <= MAX_STAGE_COUNT and 1 <= stars <= 3):
            raise ValueError("invalid stage result")
        self.best_stars[stage_id] = max(stars, self.get_best_stars(stage_id))
        next_stage_id = stage_id + 1
        if next_stage_id <= MAX_STAGE_COUNT:
            self.unlocked_stages.add(next_stage_id)

    def to_dict(self) -> dict:
        return {
            "unlocked_stages": self.get_unlocked_stages(),
            "best_stars": {str(k): v for k, v in sorted(self.best_stars.items())},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Progress":
        return cls(
            unlocked_stages={int(k) for k in data.get("unlocked_stages", [1])},
            best_stars={int(k): int(v) for k, v in data.get("best_stars", {}).items()},
        )


class SaveManager:
    def __init__(self, save_path: str | Path = "progress.json") -> None:
        self.save_path = Path(save_path)

    def load_progress(self) -> Progress:
        if not self.save_path.exists():
            return Progress()
        try:
            data = json.loads(self.save_path.read_text(encoding="utf-8"))
            return Progress.from_dict(data) if isinstance(data, dict) else Progress()
        except (AttributeError, OSError, TypeError, ValueError, json.JSONDecodeError):
            return Progress()

    def save_progress(self, progress: Progress) -> None:
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        self.save_path.write_text(
            json.dumps(progress.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
