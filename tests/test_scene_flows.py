import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from kongoose.game import Game
from kongoose.models import (
    MOVE_BLOCKED,
    MOVE_CLEARED,
    MOVE_FAILED,
    MOVE_MOVED,
    UPDATE_BIKE_AMBIENCE,
    UPDATE_SAFE,
    UPDATE_WARNING,
    Direction,
    FailureReason,
    Position,
    SoundCue,
    TerrainType,
)
from kongoose.scenes import (
    BIKE_COLOR,
    DEFAULT_BACKGROUND_COLOR,
    RUNNING_CREW_COLOR,
    RUNNING_CREW_TILE_DURATION,
    TERRAIN_STYLES,
    TURTLE_COLOR,
    FailedScene,
    MainScene,
    PlayingScene,
    ResultScene,
    StageSelectScene,
)
from kongoose.stage import Bike, Player, RunningCrew, Stage, Turtle
from kongoose.terrain import TerrainMap


class ProgressStub:
    def __init__(self, unlocked_stages: set[int] | None = None) -> None:
        self.unlocked_stages = unlocked_stages or {1}
        self.best_stars: dict[int, int] = {}

    def is_stage_unlocked(self, stage_id: int) -> bool:
        return stage_id in self.unlocked_stages

    def get_best_stars(self, stage_id: int) -> int:
        return self.best_stars.get(stage_id, 0)

    def record_stage_clear(self, stage_id: int, stars: int) -> None:
        self.best_stars[stage_id] = max(stars, self.get_best_stars(stage_id))
        self.unlocked_stages.add(stage_id + 1)


class SaveManagerStub:
    def __init__(self) -> None:
        self.saved_progress: ProgressStub | None = None

    def save_progress(self, progress: ProgressStub) -> None:
        self.saved_progress = progress


class StageStub:
    def __init__(self) -> None:
        self.initialized = False
        self.moves: list[Direction] = []
        self.update_count = 0
        self.failure_reason: FailureReason | None = None
        self.next_move_result = MOVE_MOVED
        self.next_update_result = UPDATE_SAFE

    def initialize(self) -> None:
        self.initialized = True

    def move_player(self, direction: str) -> str:
        self.moves.append(direction)
        return self.next_move_result

    def update(self, dt: float) -> str:
        self.update_count += 1
        return self.next_update_result

    def peek_warning_bike_rows(self) -> tuple[int, ...]:
        return ()


class StageWarningStub:
    def __init__(
        self, player_row: int = 12, warning_row: int | None = 12, rows: int = 24
    ) -> None:
        self.player = type("Player", (), {"position": Position(player_row, 0)})()
        self.terrain_map = TerrainMap([[TerrainType.LAND] for _ in range(rows)])
        self.failure_reason: FailureReason | None = None
        self.warning_rows = () if warning_row is None else (warning_row,)

    def peek_warning_bike_rows(self) -> tuple[int, ...]:
        return self.warning_rows


class BikeWarningVisibilityStub:
    def __init__(self) -> None:
        self.player = type("Player", (), {"position": Position(10, 0)})()
        self.warning_rows = (16,)
        self.terrain_map = TerrainMap(
            [[TerrainType.LAND for _ in range(10)] for _ in range(24)]
        )
        self.failure_reason = None

    def initialize(self) -> None:
        return None

    def update(self, dt: float) -> str:
        return UPDATE_SAFE

    def peek_warning_bike_rows(self) -> tuple[int, ...]:
        return self.warning_rows


class LegacyWarningRowStub:
    def __init__(self) -> None:
        self.warning_row = 12


class StageWarningStub:
    def __init__(
        self, player_row: int = 12, warning_row: int = 12, rows: int = 24
    ) -> None:
        self.player = type("Player", (), {"position": Position(player_row, 0)})()
        self.terrain_map = TerrainMap([[TerrainType.LAND] for _ in range(rows)])
        self.failure_reason: FailureReason | None = None
        self.warning_row = warning_row

    def peek_warning_bike_row(self) -> int | None:
        return self.warning_row


class BikeWarningVisibilityStub:
    def __init__(self) -> None:
        self.player = type("Player", (), {"position": Position(10, 0)})()
        self.warning_row: int | None = 16
        self.terrain_map = TerrainMap(
            [[TerrainType.LAND for _ in range(10)] for _ in range(24)]
        )
        self.failure_reason = None

    def initialize(self) -> None:
        return None

    def update(self, dt: float) -> str:
        return UPDATE_SAFE


class TimerStub:
    def __init__(self) -> None:
        self.reset_count = 0
        self.start_count = 0
        self.stopped = False

    def reset(self) -> None:
        self.reset_count += 1

    def start(self) -> None:
        self.start_count += 1

    def stop(self) -> None:
        self.stopped = True

    def get_elapsed_time(self) -> float:
        return 12.5


class SoundManagerStub:
    def __init__(self) -> None:
        self.played_cues: list[tuple[str, int]] = []
        self.played_calls: list[dict] = []

    def play(self, cue: str, loops: int = 0, cooldown: float = 0.0, **_kwargs) -> bool:
        self.played_cues.append((cue, loops))
        self.played_calls.append({"cue": cue, "loops": loops, **_kwargs})
        return True

    def stop(self, _cue: str) -> None:
        return None


def key_event(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def collect_surface_colors(surface: pygame.Surface) -> set[tuple[int, int, int]]:
    pixels = pygame.PixelArray(surface)
    try:
        return {
            surface.unmap_rgb(pixels[x, y])[:3]
            for x in range(surface.get_width())
            for y in range(surface.get_height())
        }
    finally:
        del pixels


def register_star_test_images(game: Game) -> None:
    filled_image = pygame.Surface((12, 12), pygame.SRCALPHA)
    empty_image = pygame.Surface((12, 12), pygame.SRCALPHA)
    filled_image.fill((252, 188, 37, 255))
    empty_image.fill((31, 97, 180, 255))
    game.resource_manager.register_image("star_filled", filled_image)
    game.resource_manager.register_image("star_empty", empty_image)


def register_bike_test_images(game: Game) -> None:
    frame_colors = [
        (12, 40, 80),
        (80, 120, 12),
        (18, 210, 230),
        (230, 90, 18),
    ]
    for index, color in enumerate(frame_colors):
        image = pygame.Surface((16, 10), pygame.SRCALPHA)
        image.fill((*color, 255))
        game.resource_manager.register_image(f"bike_frame_{index}", image)


def register_turtle_test_images(game: Game) -> None:
    for direction in ("left", "right"):
        image = pygame.Surface((18, 10), pygame.SRCALPHA)
        image.fill((34, 220, 120, 255))
        game.resource_manager.register_image(f"turtle_{direction}", image)


def register_goal_test_images(game: Game) -> None:
    for stage_id, color in ((1, (30, 220, 80)), (2, (236, 45, 95))):
        image = pygame.Surface((16, 16), pygame.SRCALPHA)
        image.fill((*color, 255))
        game.resource_manager.register_image(f"goal_stage_{stage_id}", image)


def register_running_crew_test_images(game: Game) -> None:
    warning_color = (199, 141, 82)
    for index in range(4):
        image = pygame.Surface((32, 12), pygame.SRCALPHA)
        image.fill((*warning_color, 255))
        game.resource_manager.register_image(
            f"running_crew_warning_frame_{index}", image
        )

    runner_colors = [
        (29, 211, 188),
        (211, 64, 92),
        (67, 107, 218),
        (224, 181, 48),
        (72, 198, 208),
        (124, 82, 176),
        (68, 166, 86),
        (232, 121, 31),
    ]
    for runner_index, color in enumerate(runner_colors):
        for frame_index in range(4):
            image = pygame.Surface((24, 32), pygame.SRCALPHA)
            image.fill((*color, 255))
            game.resource_manager.register_image(
                f"running_crew_runner_{runner_index}_frame_{frame_index}",
                image,
            )


def test_main_scene_opens_stage_select_and_quits_from_keys() -> None:
    game = Game(initial_scene=MainScene())

    game.current_scene.handle_event(key_event(pygame.K_RETURN))

    assert isinstance(game.current_scene, StageSelectScene)

    game.running = True
    game.return_to_main()
    game.current_scene.handle_event(key_event(pygame.K_q))

    assert not game.running


def test_stage_select_starts_unlocked_stage_and_rejects_locked_stage() -> None:
    game = Game(initial_scene=StageSelectScene())
    stage = StageStub()
    timer = TimerStub()
    game.progress = ProgressStub({1})
    game.stages = {1: stage}
    game.timer = timer

    game.current_scene.handle_event(key_event(pygame.K_2))

    assert isinstance(game.current_scene, StageSelectScene)
    assert game.current_scene._message == "Stage 2 is locked."

    game.current_scene.handle_event(key_event(pygame.K_1))

    assert isinstance(game.current_scene, PlayingScene)
    assert game.current_stage_id == 1
    assert stage.initialized
    assert timer.reset_count == 1
    assert timer.start_count == 1


def test_stage_select_draws_best_stars_with_registered_star_images() -> None:
    pygame.font.init()
    surface = pygame.Surface((420, 320))
    game = Game(initial_scene=StageSelectScene())
    game.progress = ProgressStub({1, 2, 3, 4})
    game.progress.best_stars[1] = 2
    register_star_test_images(game)

    game.current_scene.draw(surface)
    rendered_colors = collect_surface_colors(surface)

    assert (252, 188, 37) in rendered_colors
    assert (31, 97, 180) in rendered_colors


def test_playing_scene_moves_player_updates_stage_and_returns_to_select() -> None:
    game = Game(initial_scene=PlayingScene())
    stage = StageStub()
    game.current_stage = stage

    game.current_scene.handle_event(key_event(pygame.K_UP))
    game.current_scene.update(0.016)

    assert stage.moves == [Direction.UP]
    assert stage.update_count == 1

    game.current_scene.handle_event(key_event(pygame.K_ESCAPE))

    assert isinstance(game.current_scene, StageSelectScene)


def test_playing_scene_draws_stage_grid_terrain_and_actors() -> None:
    pygame.font.init()
    surface = pygame.Surface((420, 320))
    stage = Stage(
        terrain_map=TerrainMap(
            [
                [
                    TerrainType.START,
                    TerrainType.LAND,
                    TerrainType.SAFE,
                    TerrainType.RIVER,
                    TerrainType.WALL,
                    TerrainType.GOAL,
                ],
                [
                    TerrainType.LAND,
                    TerrainType.LAND,
                    TerrainType.LAND,
                    TerrainType.LAND,
                    TerrainType.LAND,
                    TerrainType.LAND,
                ],
            ]
        ),
        player=Player(Position(row=0, column=1)),
        bikes=[Bike(position=Position(row=0, column=2))],
        running_crews=[
            RunningCrew(
                row=1,
                columns=6,
                warning_time=0.0,
                active_duration=10.0,
                elapsed_time=1.0,
            )
        ],
        turtles=[Turtle(position=Position(row=0, column=3))],
    )
    game = Game(initial_scene=PlayingScene())
    game.current_stage = stage
    game.current_stage_id = 1
    register_bike_test_images(game)
    register_turtle_test_images(game)
    register_running_crew_test_images(game)

    game.current_scene.draw(surface)
    rendered_colors = collect_surface_colors(surface)

    for expected_color in [
        (176, 224, 166),
        (231, 222, 178),
        (205, 234, 198),
        (80, 155, 210),
        (92, 96, 105),
        (245, 205, 92),
        (12, 40, 80),
        (29, 211, 188),
        (34, 220, 120),
    ]:
        assert expected_color in rendered_colors

    assert (73, 83, 90) not in rendered_colors
    assert any(
        red > 190 and 70 <= green <= 170 and blue < 80
        for red, green, blue in rendered_colors
    )


def test_playing_scene_draws_stage_specific_goal_image_when_registered() -> None:
    pygame.font.init()
    surface = pygame.Surface((240, 120))
    stage = Stage(
        terrain_map=TerrainMap([[TerrainType.GOAL, TerrainType.START]]),
        player=Player(Position(row=0, column=1)),
    )
    game = Game(initial_scene=PlayingScene())
    game.current_stage = stage
    game.current_stage_id = 2
    register_goal_test_images(game)

    game.current_scene.draw(surface)
    rendered_colors = collect_surface_colors(surface)

    assert (236, 45, 95) in rendered_colors
    assert (30, 220, 80) not in rendered_colors


def test_blocked_move_keeps_next_bike_appear_sound() -> None:
    game = Game(initial_scene=PlayingScene())
    game.current_stage = StageWarningStub(player_row=12, warning_row=12)
    game.sound_manager = SoundManagerStub()

    game._handle_move_result(MOVE_BLOCKED)
    game._handle_stage_update_result(UPDATE_BIKE_AMBIENCE)

    assert game.sound_manager.played_cues == [
        (SoundCue.BLOCKED, 0),
        (SoundCue.BIKE_AMBIENCE, 0),
    ]


def test_offscreen_bike_warning_row_does_not_play_sound() -> None:
    game = Game(initial_scene=PlayingScene())
    game.current_stage = StageWarningStub(player_row=12, warning_row=0)
    game.sound_manager = SoundManagerStub()

    game._play_bike_warning_from_stage()

    assert game.sound_manager.played_cues == []


def test_inview_bike_warning_row_plays_appearance_sound() -> None:
    game = Game(initial_scene=PlayingScene())
    game.current_stage = StageWarningStub(player_row=12, warning_row=12)
    game.sound_manager = SoundManagerStub()

    game._play_bike_warning_from_stage()

    assert game.sound_manager.played_cues == [(SoundCue.BIKE_AMBIENCE, 0)]


def test_legacy_bike_warning_row_attribute_is_ignored() -> None:
    game = Game(initial_scene=PlayingScene())
    game.current_stage = LegacyWarningRowStub()

    assert game._pending_bike_warning_rows() == ()


def test_offscreen_bike_warning_waits_until_visible_row() -> None:
    game = Game(initial_scene=PlayingScene())
    game.current_stage = BikeWarningVisibilityStub()
    game.sound_manager = SoundManagerStub()

    game.update_stage(0.016)
    assert game.sound_manager.played_cues == []

    game.current_stage.player.position = Position(20, 0)
    game.update_stage(0.016)
    game.update_stage(0.016)

    assert game.sound_manager.played_cues == [(SoundCue.BIKE_AMBIENCE, 0)]


def test_running_crew_warning_uses_channel_separate_from_player_move() -> None:
    game = Game(initial_scene=PlayingScene())
    game.current_stage = StageStub()
    game.sound_manager = SoundManagerStub()

    game._handle_move_result(MOVE_MOVED)
    game._handle_stage_update_result(UPDATE_WARNING)

    assert game.sound_manager.played_calls[0]["cue"] == SoundCue.MOVE_START
    assert game.sound_manager.played_calls[1]["cue"] == SoundCue.RUNNING_CREW_WARNING
    assert (
        game.sound_manager.played_calls[0]["channel_index"]
        != game.sound_manager.played_calls[1]["channel_index"]
    )


def test_playing_scene_uses_player_sprite_for_facing_direction() -> None:
    pygame.font.init()
    surface = pygame.Surface((240, 240))
    player = Player(Position(row=0, column=0), facing_direction=Direction.LEFT)
    stage = Stage(
        terrain_map=TerrainMap([[TerrainType.START]]),
        player=player,
    )
    game = Game(initial_scene=PlayingScene())
    game.current_stage = stage

    game.current_scene.draw(surface)

    assert game.resource_manager.has_image("player_goose_left")
    assert not game.resource_manager.has_image("player_goose_right")

    player.face(Direction.RIGHT)
    game.current_scene.draw(surface)

    assert game.resource_manager.has_image("player_goose_right")


def test_playing_scene_hops_between_tiles_after_successful_move() -> None:
    game = Game(initial_scene=PlayingScene())
    stage = Stage(
        terrain_map=TerrainMap(
            [[TerrainType.START, TerrainType.LAND, TerrainType.LAND]]
        ),
        player=Player(Position(row=0, column=0)),
    )
    game.current_stage = stage
    scene = game.current_scene

    scene.handle_event(key_event(pygame.K_RIGHT))

    assert stage.player.position == Position(row=0, column=1)
    assert scene._hop_start_position == Position(row=0, column=0)
    assert scene._hop_end_position == Position(row=0, column=1)

    scene.handle_event(key_event(pygame.K_RIGHT))

    assert stage.player.position == Position(row=0, column=1)

    scene.update(0.3)
    scene.handle_event(key_event(pygame.K_RIGHT))

    assert stage.player.position == Position(row=0, column=2)


def test_successful_hop_plays_start_then_success_sound() -> None:
    game = Game(initial_scene=PlayingScene())
    game.sound_manager = SoundManagerStub()
    game.current_stage = Stage(
        terrain_map=TerrainMap(
            [[TerrainType.START, TerrainType.LAND, TerrainType.LAND]]
        ),
        player=Player(Position(row=0, column=0)),
    )
    scene = game.current_scene

    scene.handle_event(key_event(pygame.K_RIGHT))

    assert game.sound_manager.played_cues == [(SoundCue.MOVE_START, 0)]

    scene.update(0.3)

    assert game.sound_manager.played_cues == [
        (SoundCue.MOVE_START, 0),
        (SoundCue.MOVE_SUCCESS, 0),
    ]


def test_blocked_move_plays_blocked_sound_without_starting_hop() -> None:
    game = Game(initial_scene=PlayingScene())
    game.sound_manager = SoundManagerStub()
    game.current_stage = Stage(
        terrain_map=TerrainMap([[TerrainType.START, TerrainType.WALL]]),
        player=Player(Position(row=0, column=0)),
    )
    scene = game.current_scene

    scene.handle_event(key_event(pygame.K_RIGHT))

    assert game.sound_manager.played_cues == [(SoundCue.BLOCKED, 0)]
    assert scene._hop_start_position is None


def test_blocked_input_during_hop_plays_blocked_sound_immediately() -> None:
    game = Game(initial_scene=PlayingScene())
    game.sound_manager = SoundManagerStub()
    game.current_stage = Stage(
        terrain_map=TerrainMap(
            [[TerrainType.START, TerrainType.LAND, TerrainType.WALL]]
        ),
        player=Player(Position(row=0, column=0)),
    )
    scene = game.current_scene

    scene.handle_event(key_event(pygame.K_RIGHT))
    scene.handle_event(key_event(pygame.K_RIGHT))

    assert game.current_stage.player.position == Position(row=0, column=1)
    assert scene._hop_start_position == Position(row=0, column=0)
    assert game.sound_manager.played_cues == [
        (SoundCue.MOVE_START, 0),
        (SoundCue.BLOCKED, 0),
    ]


def test_player_hop_draw_rect_uses_small_base_and_larger_jump() -> None:
    scene = PlayingScene()
    grid_rect = pygame.Rect(0, 0, 200, 100)

    base_rect = scene._get_player_draw_rect(
        grid_rect,
        100,
        Position(row=0, column=0),
    )

    scene._hop_start_position = Position(row=0, column=0)
    scene._hop_end_position = Position(row=0, column=1)
    scene._hop_elapsed = 0.09
    jump_rect = scene._get_player_draw_rect(
        grid_rect,
        100,
        Position(row=0, column=1),
    )

    assert base_rect.width == 50
    assert jump_rect.width == 95


def test_playing_scene_grid_layout_fills_screen_width() -> None:
    scene = PlayingScene()

    grid_rect, cell_size = scene._calculate_grid_layout(
        960, 720, 24, 10, Position(row=23, column=5)
    )

    assert grid_rect.left == 0
    assert grid_rect.width == 960
    assert cell_size == 96


def test_playing_scene_draws_hud_overlay_above_grid() -> None:
    pygame.font.init()
    surface = pygame.Surface((960, 720))
    stage = Stage(
        terrain_map=TerrainMap(
            [[TerrainType.LAND for _column in range(10)] for _row in range(24)]
        ),
        player=Player(Position(row=23, column=5)),
    )
    game = Game(initial_scene=PlayingScene())
    game.current_stage = stage
    game.current_stage_id = 1

    game.current_scene.draw(surface)

    terrain_color = TERRAIN_STYLES[TerrainType.LAND]
    hud_pixel = surface.get_at((20, 20))[:3]

    assert hud_pixel != terrain_color
    assert hud_pixel != DEFAULT_BACKGROUND_COLOR


def test_playing_hud_padding_contains_status_lines() -> None:
    pygame.font.init()
    surface = pygame.Surface((420, 120))
    surface.fill(DEFAULT_BACKGROUND_COLOR)
    scene = PlayingScene()
    title_font = pygame.font.Font(None, 44)
    body_font = pygame.font.Font(None, 26)

    scene._draw_playing_hud(surface, title_font, body_font, "1", "12.5s")

    assert surface.get_at((10, 60))[:3] != DEFAULT_BACKGROUND_COLOR
    assert surface.get_at((10, 100))[:3] == DEFAULT_BACKGROUND_COLOR


def test_playing_scene_camera_keeps_tall_stage_tiles_large() -> None:
    scene = PlayingScene()

    grid_rect, cell_size = scene._calculate_grid_layout(
        800, 600, 24, 10, Position(row=23, column=5)
    )
    player_rect = scene._cell_rect(
        grid_rect,
        cell_size,
        Position(row=23, column=5),
    )

    assert cell_size >= 48
    assert grid_rect.left == 0
    assert grid_rect.width == 800
    assert grid_rect.height > 600
    assert player_rect.bottom <= 600
    assert player_rect.centery > 600 // 2


def test_playing_scene_camera_centers_player_away_from_stage_edges() -> None:
    scene = PlayingScene()

    grid_rect, cell_size = scene._calculate_grid_layout(
        800, 600, 24, 10, Position(row=12, column=5)
    )
    player_rect = scene._cell_rect(
        grid_rect,
        cell_size,
        Position(row=12, column=5),
    )
    play_area_center_y = 600 // 2

    assert abs(player_rect.centery - play_area_center_y) <= cell_size // 2


def test_position_sprite_draw_rects_use_fractional_progress() -> None:
    scene = PlayingScene()
    grid_rect = pygame.Rect(0, 0, 200, 100)
    bike = Bike(
        position=Position(row=0, column=0),
        direction=Direction.RIGHT,
        distance_progress=0.5,
    )

    draw_rect = scene._get_sprite_draw_rects(bike, grid_rect, 100)[0]
    base_rect = scene._cell_rect(grid_rect, 100, Position(row=0, column=0))

    assert draw_rect.centerx == base_rect.centerx + 50


def test_position_sprites_are_clipped_to_grid_bounds() -> None:
    pygame.font.init()
    surface = pygame.Surface((400, 120))
    surface.fill((0, 0, 0))
    scene = PlayingScene()
    grid_rect = pygame.Rect(0, 0, 300, 100)
    bike = Bike(
        position=Position(row=0, column=2),
        direction=Direction.RIGHT,
        distance_progress=0.5,
    )

    scene._draw_position_sprites(
        surface,
        [bike],
        grid_rect,
        100,
        BIKE_COLOR,
    )

    assert surface.get_at((320, 50))[:3] == (0, 0, 0)


def test_position_sprites_draw_bike_animation_frame_when_registered() -> None:
    pygame.font.init()
    surface = pygame.Surface((240, 120))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    register_bike_test_images(game)
    bike = Bike(
        position=Position(row=0, column=0),
        direction=Direction.RIGHT,
        distance_progress=0.5,
    )

    game.current_scene._draw_position_sprites(
        surface,
        [bike],
        pygame.Rect(0, 0, 200, 100),
        100,
        BIKE_COLOR,
        game.current_scene._get_bike_image,
        0.4,
    )
    rendered_colors = collect_surface_colors(surface)

    assert (18, 210, 230) in rendered_colors


def test_position_sprites_draw_turtle_image_when_registered() -> None:
    pygame.font.init()
    surface = pygame.Surface((240, 120))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    register_turtle_test_images(game)
    turtle = Turtle(
        position=Position(row=0, column=0),
        direction=Direction.RIGHT,
    )

    game.current_scene._draw_position_sprites(
        surface,
        [turtle],
        pygame.Rect(0, 0, 200, 100),
        100,
        TURTLE_COLOR,
        game.current_scene._get_turtle_image,
        0.32,
    )
    rendered_colors = collect_surface_colors(surface)

    assert (34, 220, 120) in rendered_colors


def test_running_crew_warning_draws_registered_warning_frame() -> None:
    pygame.font.init()
    surface = pygame.Surface((320, 100))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    register_running_crew_test_images(game)
    crew = RunningCrew(
        row=0,
        columns=3,
        warning_time=1.0,
        active_duration=1.0,
        elapsed_time=0.5,
    )

    game.current_scene._draw_running_crews(
        surface,
        [crew],
        TerrainMap([[TerrainType.LAND for _column in range(3)]]),
        pygame.Rect(0, 0, 300, 100),
        100,
    )
    rendered_colors = collect_surface_colors(surface)

    assert (199, 141, 82) in rendered_colors
    assert RUNNING_CREW_COLOR not in rendered_colors


def test_running_crew_active_draws_registered_runner_in_each_cell() -> None:
    pygame.font.init()
    surface = pygame.Surface((820, 100))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    register_running_crew_test_images(game)
    crew = RunningCrew(
        row=0,
        columns=8,
        warning_time=0.2,
        active_duration=1.0,
        elapsed_time=0.2,
    )

    game.current_scene._draw_running_crews(
        surface,
        [crew],
        TerrainMap([[TerrainType.LAND for _column in range(8)]]),
        pygame.Rect(0, 0, 800, 100),
        100,
    )

    assert surface.get_at((50, 50))[:3] == (29, 211, 188)
    assert surface.get_at((150, 50))[:3] == (211, 64, 92)
    assert surface.get_at((250, 50))[:3] == (67, 107, 218)
    assert surface.get_at((350, 50))[:3] == (224, 181, 48)
    assert surface.get_at((450, 50))[:3] == (72, 198, 208)
    assert surface.get_at((550, 50))[:3] == (124, 82, 176)
    assert surface.get_at((650, 50))[:3] == (68, 166, 86)
    assert surface.get_at((750, 50))[:3] == (232, 121, 31)


def test_running_crew_visual_tile_duration_is_three_times_faster() -> None:
    assert RUNNING_CREW_TILE_DURATION == 0.08


def test_running_crew_active_trims_transparent_margins_per_runner_cell() -> None:
    pygame.font.init()
    active_color = (29, 211, 188)
    surface = pygame.Surface((320, 100))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    for index in range(4):
        image = pygame.Surface((96, 12), pygame.SRCALPHA)
        image.fill((0, 0, 0, 0))
        image.fill((*active_color, 255), pygame.Rect(36, 0, 24, 12))
        game.resource_manager.register_image(
            f"running_crew_runner_0_frame_{index}", image
        )
    for runner_index in range(1, 4):
        for frame_index in range(4):
            image = pygame.Surface((24, 32), pygame.SRCALPHA)
            image.fill((*active_color, 255))
            game.resource_manager.register_image(
                f"running_crew_runner_{runner_index}_frame_{frame_index}",
                image,
            )
    crew = RunningCrew(
        row=0,
        columns=3,
        warning_time=0.2,
        active_duration=1.0,
        elapsed_time=0.2,
    )

    game.current_scene._draw_running_crews(
        surface,
        [crew],
        TerrainMap([[TerrainType.LAND for _column in range(3)]]),
        pygame.Rect(0, 0, 300, 100),
        100,
    )

    assert surface.get_at((50, 50))[:3] == active_color


def test_running_crew_active_moves_runners_right_and_refills_from_left() -> None:
    pygame.font.init()
    surface = pygame.Surface((320, 100))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    register_running_crew_test_images(game)
    crew = RunningCrew(
        row=0,
        columns=3,
        warning_time=0.2,
        active_duration=1.0,
        elapsed_time=0.2 + RUNNING_CREW_TILE_DURATION / 2,
    )

    game.current_scene._draw_running_crews(
        surface,
        [crew],
        TerrainMap([[TerrainType.LAND for _column in range(3)]]),
        pygame.Rect(0, 0, 300, 100),
        100,
    )

    assert surface.get_at((15, 50))[:3] == (232, 121, 31)
    assert surface.get_at((100, 50))[:3] == (29, 211, 188)
    assert surface.get_at((200, 50))[:3] == (211, 64, 92)
    assert surface.get_at((285, 50))[:3] == (67, 107, 218)


def test_running_crew_tail_exits_without_refilling_after_active_duration() -> None:
    pygame.font.init()
    surface = pygame.Surface((320, 100))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    register_running_crew_test_images(game)
    crew = RunningCrew(
        row=0,
        columns=3,
        warning_time=0.2,
        active_duration=1.0,
        elapsed_time=0.2 + 1.0 + RUNNING_CREW_TILE_DURATION * 2.5,
    )

    game.current_scene._draw_running_crews(
        surface,
        [crew],
        TerrainMap([[TerrainType.LAND for _column in range(3)]]),
        pygame.Rect(0, 0, 300, 100),
        100,
    )

    assert surface.get_at((50, 50))[:3] == (0, 0, 0)
    assert surface.get_at((250, 50))[:3] != (0, 0, 0)


def test_playing_scene_changes_to_failed_or_result_for_stage_outcomes() -> None:
    game = Game(initial_scene=PlayingScene())
    stage = StageStub()
    timer = TimerStub()
    save_manager = SaveManagerStub()
    sound_manager = SoundManagerStub()
    game.current_stage = stage
    game.current_stage_id = 1
    game.progress = ProgressStub({1})
    game.save_manager = save_manager
    game.timer = timer
    game.sound_manager = sound_manager

    stage.failure_reason = FailureReason.FELL_IN_RIVER
    stage.next_move_result = MOVE_FAILED
    game.current_scene.handle_event(key_event(pygame.K_RIGHT))

    assert isinstance(game.current_scene, FailedScene)
    assert game.last_failure_reason == FailureReason.FELL_IN_RIVER
    assert sound_manager.played_cues == [
        (SoundCue.LAKE_SPLASH, 0),
        (SoundCue.FAILURE_SCREEN, 0),
    ]

    game.change_scene(PlayingScene())
    stage.next_move_result = MOVE_CLEARED
    game.current_scene.handle_event(key_event(pygame.K_RIGHT))

    assert isinstance(game.current_scene, ResultScene)
    assert timer.stopped
    assert game.last_clear_time == 12.5
    assert game.last_stars == 3
    assert save_manager.saved_progress is game.progress
    assert sound_manager.played_cues[-1] == (SoundCue.CLEAR_SCREEN, 0)


def test_result_scene_draws_star_rating_with_registered_star_images() -> None:
    pygame.font.init()
    surface = pygame.Surface((420, 320))
    game = Game(initial_scene=ResultScene())
    game.last_clear_time = 12.5
    game.last_stars = 2
    register_star_test_images(game)

    game.current_scene.draw(surface)
    rendered_colors = collect_surface_colors(surface)

    assert (252, 188, 37) in rendered_colors
    assert (31, 97, 180) in rendered_colors


def test_failed_scene_actions_restart_select_or_main() -> None:
    game = Game(initial_scene=FailedScene())
    game.current_stage_id = 1
    game.stages = {1: StageStub()}
    game.timer = TimerStub()

    game.current_scene.handle_event(key_event(pygame.K_r))
    assert isinstance(game.current_scene, PlayingScene)

    game.change_scene(FailedScene())
    game.current_scene.handle_event(key_event(pygame.K_s))
    assert isinstance(game.current_scene, StageSelectScene)

    game.change_scene(FailedScene())
    game.current_scene.handle_event(key_event(pygame.K_m))
    assert isinstance(game.current_scene, MainScene)


def test_result_scene_actions_next_restart_select_or_main() -> None:
    game = Game(initial_scene=ResultScene())
    game.current_stage_id = 1
    game.stages = {1: StageStub(), 2: StageStub()}
    game.timer = TimerStub()

    game.current_scene.handle_event(key_event(pygame.K_n))
    assert isinstance(game.current_scene, PlayingScene)
    assert game.current_stage_id == 2

    game.change_scene(ResultScene())
    game.current_scene.handle_event(key_event(pygame.K_r))
    assert isinstance(game.current_scene, PlayingScene)
    assert game.current_stage_id == 2

    game.change_scene(ResultScene())
    game.current_scene.handle_event(key_event(pygame.K_b))
    assert isinstance(game.current_scene, StageSelectScene)

    game.change_scene(ResultScene())
    game.current_scene.handle_event(key_event(pygame.K_ESCAPE))
    assert isinstance(game.current_scene, MainScene)
