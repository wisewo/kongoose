from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from kongoose.models import SoundCue


class SoundManager:
    def __init__(self) -> None:
        self.sounds: dict[SoundCue, Any] = {}

    def load(self, sound_paths: Mapping[SoundCue, str | Path]) -> None:
        import pygame

        for cue, path in sound_paths.items():
            self.sounds[cue] = pygame.mixer.Sound(str(path))

    def register_sound(self, cue: SoundCue, sound: Any) -> None:
        self.sounds[cue] = sound

    def play(self, cue: SoundCue) -> bool:
        sound = self.sounds.get(cue)
        if sound is None:
            return False
        sound.play()
        return True


class ResourceManager:
    def __init__(self) -> None:
        self.images: dict[str, Any] = {}

    def load(self, image_paths: Mapping[str, str | Path]) -> None:
        import pygame

        for name, path in image_paths.items():
            self.images[name] = pygame.image.load(str(path)).convert_alpha()

    def register_image(self, name: str, image: Any) -> None:
        self.images[name] = image

    def get_image(self, name: str) -> Any | None:
        return self.images.get(name)

    def has_image(self, name: str) -> bool:
        return name in self.images
