from pathlib import Path


class SoundManager:
    def __init__(self) -> None:
        self.sounds = {}

    def load(self, sound_paths) -> None:
        import pygame

        for cue, path in sound_paths.items():
            sound_path = Path(path)
            if sound_path.exists():
                try:
                    self.sounds[cue] = pygame.mixer.Sound(str(sound_path))
                except pygame.error:
                    continue

    def register_sound(self, cue: str, sound) -> None:
        self.sounds[cue] = sound

    def play(self, cue, loops=0, volume=None) -> bool:
        sound = self.sounds.get(cue)
        if sound is None:
            return False
        channel = sound.play(loops=loops)
        if volume is not None and channel is not None:
            channel.set_volume(volume)
        return True

    def stop(self, cue) -> None:
        sound = self.sounds.get(cue)
        if sound is not None:
            sound.stop()


class ResourceManager:
    def __init__(self) -> None:
        self.images = {}

    def register_image(self, name: str, image) -> None:
        self.images[name] = image

    def get_image(self, name: str):
        return self.images.get(name)
