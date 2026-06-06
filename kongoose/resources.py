from pathlib import Path
from time import monotonic


class SoundManager:
    def __init__(self, clock=None) -> None:
        self.sounds = {}
        self._clock = monotonic if clock is None else clock
        self._last_played_at = {}

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

    def play(self, cue, loops=0, cooldown=0.0, channel_index=None) -> bool:
        sound = self.sounds.get(cue)
        if sound is None:
            return False
        now = self._clock()
        if cooldown > 0 and now - self._last_played_at.get(cue, -cooldown) < cooldown:
            return False
        if channel_index is None:
            sound.play(loops=loops)
        else:
            import pygame

            current_channels = pygame.mixer.get_num_channels()
            if current_channels <= channel_index:
                pygame.mixer.set_num_channels(channel_index + 1)
            play_channel = pygame.mixer.Channel(channel_index)
            play_channel.stop()
            play_channel.play(sound, loops=loops)
        self._last_played_at[cue] = now
        return True


class ResourceManager:
    def __init__(self) -> None:
        self.images = {}

    def register_image(self, name: str, image) -> None:
        self.images[name] = image

    def get_image(self, name: str):
        return self.images.get(name)

    def has_image(self, name: str) -> bool:
        return name in self.images
