from enum import Enum

from src.game import Game
from src.models import FailureReason
from src.scenes import FailedScene


class FailedSceneProbe(FailedScene):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.lines: list[str] = []

    def _draw_text_screen(self, surface, title: str, lines: list[str]) -> None:
        self.title = title
        self.lines = lines


def test_failure_reason_is_enum_member() -> None:
    assert isinstance(FailureReason.HIT_BIKE, FailureReason)
    assert isinstance(FailureReason.HIT_BIKE, Enum)
    assert FailureReason.HIT_BIKE.name == "HIT_BIKE"
    assert FailureReason.HIT_BIKE.value == "hit_bike"


def test_failed_scene_draws_failure_reason_enum_name() -> None:
    scene = FailedSceneProbe()
    game = Game(initial_scene=scene)
    game.last_failure_reason = FailureReason.HIT_BIKE

    scene.draw(None)

    assert scene.title == "Stage Failed"
    assert scene.lines[0] == "Reason: HIT_BIKE"
