from __future__ import annotations

from typing import Any

from kongoose.models import Direction, FailureReason
from kongoose.scenes import MainScene, Scene


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
        self.progress: Any | None = None
        self.timer: Any | None = None
        self.save_manager: Any | None = None
        self.sound_manager: Any | None = None
        self.resource_manager: Any | None = None

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
        raise NotImplementedError

    def select_stage(self, stage_id: int) -> None:
        raise NotImplementedError

    def start_stage(self, stage_id: int) -> None:
        raise NotImplementedError

    def start_next_stage(self) -> None:
        raise NotImplementedError

    def restart_stage(self) -> None:
        raise NotImplementedError

    def return_to_main(self) -> None:
        self.change_scene(MainScene())

    def move_player(self, direction: Direction) -> None:
        raise NotImplementedError

    def update_stage(self, dt: float) -> None:
        raise NotImplementedError

    def fail_current_stage(self, reason: FailureReason) -> None:
        raise NotImplementedError

    def clear_current_stage(self) -> None:
        raise NotImplementedError
