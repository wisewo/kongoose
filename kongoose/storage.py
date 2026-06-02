from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Progress:
    total_stages: int = 4
    unlocked_stages: set[int] = field(default_factory=lambda: {1})
    best_stars: dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.total_stages < 1:
            raise ValueError("total_stages must be at least 1")
        self.unlocked_stages = {
            stage_id
            for stage_id in self.unlocked_stages
            if 1 <= stage_id <= self.total_stages
        }
        self.unlocked_stages.add(1)
        self.best_stars = {
            stage_id: stars
            for stage_id, stars in self.best_stars.items()
            if 1 <= stage_id <= self.total_stages and 0 <= stars <= 3
        }

    def get_unlocked_stages(self) -> list[int]:
        return sorted(self.unlocked_stages)

    def is_stage_unlocked(self, stage_id: int) -> bool:
        return stage_id in self.unlocked_stages

    def get_best_stars(self, stage_id: int) -> int:
        return self.best_stars.get(stage_id, 0)

    def record_stage_clear(self, stage_id: int, stars: int) -> None:
        self._validate_stage_id(stage_id)
        if not 1 <= stars <= 3:
            raise ValueError("stars must be between 1 and 3")

        self.best_stars[stage_id] = max(stars, self.get_best_stars(stage_id))

        next_stage_id = stage_id + 1
        if next_stage_id <= self.total_stages:
            self.unlocked_stages.add(next_stage_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_stages": self.total_stages,
            "unlocked_stages": self.get_unlocked_stages(),
            "best_stars": {
                str(stage_id): stars
                for stage_id, stars in sorted(self.best_stars.items())
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Progress:
        return cls(
            total_stages=int(data.get("total_stages", 4)),
            unlocked_stages={
                int(stage_id) for stage_id in data.get("unlocked_stages", [1])
            },
            best_stars={
                int(stage_id): int(stars)
                for stage_id, stars in data.get("best_stars", {}).items()
            },
        )

    def _validate_stage_id(self, stage_id: int) -> None:
        if not 1 <= stage_id <= self.total_stages:
            raise ValueError("stage_id is outside the configured stage range")


class SaveManager:
    def __init__(self, save_path: str | Path = "progress.json") -> None:
        self.save_path = Path(save_path)

    def load_progress(self) -> Progress:
        if not self.save_path.exists():
            return Progress()

        try:
            data = json.loads(self.save_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return Progress()

        if not isinstance(data, dict):
            return Progress()
        return Progress.from_dict(data)

    def save_progress(self, progress: Progress) -> None:
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        self.save_path.write_text(
            json.dumps(progress.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
