import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from kongoose.game import Game
from kongoose.models import (
    MOVE_CLEARED,
    MOVE_FAILED,
    MOVE_MOVED,
    UPDATE_SAFE,
    UPDATE_STUDENT_CROWD_ACTIVE,
    UPDATE_WARNING,
    Direction,
    FailureReason,
    Position,
    SoundCue,
    TerrainType,
)
from kongoose.rendering import (
    BIKE_COLOR,
    DEFAULT_BACKGROUND_COLOR,
    HOP_DURATION,
    PLAYING_HUD_HEIGHT,
    PLAYING_VIEW_ZOOM,
    STUDENT_CROWD_ACTIVE_FRAME_COUNT,
    STUDENT_CROWD_COLOR,
    STUDENT_CROWD_FRAME_DURATION,
    TERRAIN_STYLES,
    TURTLE_COLOR,
    StageRenderer,
)
from kongoose.scenes import (
    FailedScene,
    MainScene,
    PlayingScene,
    ResultScene,
    StageSelectScene,
)
from kongoose.stage import Bike, Player, Stage, StudentCrowd, Turtle
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
        self.terrain_map = TerrainMap(
            [
                [TerrainType.START, TerrainType.LAND],
                [TerrainType.LAND, TerrainType.GOAL],
            ]
        )
        self.player = Player(Position(0, 0))
        self.bikes = []
        self.turtles = []
        self.student_crowds = []

    def initialize(self) -> None:
        self.initialized = True

    def move_player(self, direction: str) -> str:
        self.moves.append(direction)
        return self.next_move_result

    def update(self, dt: float) -> str:
        self.update_count += 1
        return self.next_update_result


class IncompleteStageStub:
    def initialize(self) -> None:
        return None


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
        self.stopped_cues: list[str] = []

    def play(self, cue: str, loops: int = 0, volume=None) -> bool:
        self.played_cues.append((cue, loops))
        self.played_calls.append({"cue": cue, "loops": loops, "volume": volume})
        return True

    def stop(self, cue: str) -> None:
        self.stopped_cues.append(cue)


class BareScene:
    def enter(self, game: Game) -> None:
        return None


def key_event(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def set_current_stage(game: Game, stage, stage_id: int = 1) -> None:
    game.stages = {stage_id: stage}
    game.current_stage_id = stage_id


def renderer_without_assets() -> StageRenderer:
    return StageRenderer(lambda _name: None)


def renderer_for_game(game: Game) -> StageRenderer:
    return StageRenderer(game.resource_manager.get_image)


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


def has_similar_color(
    colors: set[tuple[int, int, int]], expected: tuple[int, int, int], tolerance=8
) -> bool:
    return any(
        all(
            abs(actual - target) <= tolerance for actual, target in zip(color, expected)
        )
        for color in colors
    )


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


def register_student_crowd_test_images(game: Game) -> None:
    warning_color = (199, 141, 82)
    for index in range(4):
        image = pygame.Surface((32, 12), pygame.SRCALPHA)
        image.fill((*warning_color, 255))
        game.resource_manager.register_image(
            f"student_crowd_warning_frame_{index}", image
        )

    active_colors = [
        (29, 211, 188),
        (211, 64, 92),
        (67, 107, 218),
        (224, 181, 48),
    ]
    for index in range(STUDENT_CROWD_ACTIVE_FRAME_COUNT):
        color = active_colors[index % len(active_colors)]
        image = pygame.Surface((96, 32), pygame.SRCALPHA)
        image.fill((0, 0, 0, 0))
        image.fill((*color, 255), pygame.Rect(8, 8, 80, 16))
        game.resource_manager.register_image(
            f"student_crowd_active_frame_{index}", image
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
    stage = StageStub()
    game = Game(initial_scene=PlayingScene())
    set_current_stage(game, stage)

    game.current_scene.handle_event(key_event(pygame.K_UP))
    game.current_scene.update(0.016)

    assert stage.moves == [Direction.UP]
    assert stage.update_count == 1

    game.sound_manager = SoundManagerStub()
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
                    TerrainType.LAND,
                ],
            ]
        ),
        player=Player(Position(row=0, column=1)),
        bikes=[Bike(position=Position(row=0, column=2))],
        student_crowds=[
            StudentCrowd(
                row=1,
                columns=7,
                warning_time=0.0,
                active_duration=10.0,
                elapsed_time=1.0,
            )
        ],
        turtles=[Turtle(position=Position(row=0, column=3))],
    )
    game = Game(initial_scene=PlayingScene(), stages={1: stage})
    set_current_stage(game, stage)
    register_bike_test_images(game)
    register_turtle_test_images(game)
    register_student_crowd_test_images(game)

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
        assert has_similar_color(rendered_colors, expected_color, tolerance=18)

    assert (73, 83, 90) not in rendered_colors
    assert any(
        red > 190 and 70 <= green <= 170 and blue < 80
        for red, green, blue in rendered_colors
    )


def test_playing_scene_projects_grid_cells_as_isometric_diamonds() -> None:
    renderer = renderer_without_assets()
    grid, cell_size = renderer.calculate_grid_layout(240, 120, rows=2, columns=2)
    origin = renderer.cell_rect(grid, cell_size, Position(row=0, column=0)).center
    right = renderer.cell_rect(grid, cell_size, Position(row=0, column=1)).center
    down = renderer.cell_rect(grid, cell_size, Position(row=1, column=0)).center

    assert right[0] > origin[0]
    assert right[1] > origin[1]
    assert down[0] < origin[0]
    assert down[1] > origin[1]


def test_playing_scene_draws_diamond_tile_corners_as_background() -> None:
    pygame.font.init()
    surface = pygame.Surface((240, 180))
    game = Game(initial_scene=PlayingScene())
    stage = Stage(
        terrain_map=TerrainMap([[TerrainType.LAND, TerrainType.START]]),
        player=Player(Position(row=0, column=1)),
    )
    set_current_stage(game, stage)

    game.current_scene.draw(surface)
    grid, cell_size = game.current_scene._renderer.calculate_grid_layout(
        surface.get_width(),
        max(1, surface.get_height() - PLAYING_HUD_HEIGHT),
        stage.terrain_map.rows,
        stage.terrain_map.columns,
        stage.player.position,
    )
    grid.move_ip(0, PLAYING_HUD_HEIGHT)
    land_sample = game.current_scene._renderer.cell_rect(
        grid,
        cell_size,
        Position(row=0, column=0),
    ).center

    assert (
        surface.get_at((surface.get_width() - 1, PLAYING_HUD_HEIGHT + 1))[:3]
        == DEFAULT_BACKGROUND_COLOR
    )
    assert surface.get_at(land_sample)[:3] == TERRAIN_STYLES[TerrainType.LAND]


def test_playing_scene_draws_stage_specific_goal_image_when_registered() -> None:
    pygame.font.init()
    surface = pygame.Surface((240, 120))
    stage = Stage(
        terrain_map=TerrainMap([[TerrainType.GOAL, TerrainType.START]]),
        player=Player(Position(row=0, column=1)),
    )
    game = Game(initial_scene=PlayingScene())
    set_current_stage(game, stage, 2)
    register_goal_test_images(game)

    game.current_scene.draw(surface)
    rendered_colors = collect_surface_colors(surface)

    assert (236, 45, 95) in rendered_colors
    assert (30, 220, 80) not in rendered_colors


def test_start_stage_plays_fixed_ambience_for_stage() -> None:
    game = Game()
    game.sound_manager = SoundManagerStub()

    game.start_stage(4)

    assert game.sound_manager.played_cues == [
        (SoundCue.BIKE_AMBIENCE, -1),
        (SoundCue.WATER_AMBIENCE, -1),
    ]
    assert [call["volume"] for call in game.sound_manager.played_calls] == [0.25, 0.45]


def test_starting_stage_without_ambience_stops_stage_ambience() -> None:
    game = Game()
    game.sound_manager = SoundManagerStub()
    game.start_stage(4)
    game.sound_manager.played_cues.clear()
    game.sound_manager.stopped_cues.clear()

    game.start_stage(1)

    assert game.sound_manager.stopped_cues == [
        SoundCue.BIKE_AMBIENCE,
        SoundCue.WATER_AMBIENCE,
    ]
    assert game.sound_manager.played_cues == []


def test_failing_stage_stops_stage_ambience() -> None:
    game = Game()
    game.sound_manager = SoundManagerStub()
    game.start_stage(4)
    game.sound_manager.stopped_cues.clear()

    game.fail_current_stage(FailureReason.FELL_IN_RIVER)

    assert game.sound_manager.stopped_cues == [
        SoundCue.BIKE_AMBIENCE,
        SoundCue.WATER_AMBIENCE,
    ]


def test_bike_collision_sound_plays_before_failure_screen() -> None:
    game = Game(initial_scene=PlayingScene())
    stage = StageStub()
    sound_manager = SoundManagerStub()
    set_current_stage(game, stage)
    game.sound_manager = sound_manager

    stage.failure_reason = FailureReason.HIT_BIKE
    stage.next_move_result = MOVE_FAILED
    game.current_scene.handle_event(key_event(pygame.K_RIGHT))

    assert isinstance(game.current_scene, FailedScene)
    assert game.last_failure_reason == FailureReason.HIT_BIKE
    assert sound_manager.played_cues == [
        (SoundCue.BIKE_COLLISION, 0),
        (SoundCue.FAILURE_SCREEN, 0),
    ]


def test_student_crowd_sound_plays_on_active_event_without_channel_state() -> None:
    game = Game(initial_scene=PlayingScene())
    stage = Stage(
        terrain_map=TerrainMap([[TerrainType.LAND for _column in range(3)]]),
        player=Player(Position(row=0, column=0)),
        student_crowds=[
            StudentCrowd(row=0, columns=3, warning_time=1.0, active_duration=4.17)
        ],
    )
    set_current_stage(game, stage)
    game.sound_manager = SoundManagerStub()

    game._handle_move_result(MOVE_MOVED)
    game._handle_stage_update_result(UPDATE_WARNING)
    game._handle_stage_update_result(UPDATE_STUDENT_CROWD_ACTIVE)

    assert game.sound_manager.played_cues == [
        (SoundCue.MOVE_START, 0),
        (SoundCue.STUDENT_CROWD, 0),
    ]


def test_student_crowd_sound_is_not_managed_as_continuous_channel() -> None:
    from kongoose.stage import StudentCrowd

    game = Game(initial_scene=PlayingScene())
    game.sound_manager = SoundManagerStub()
    stage = Stage(
        terrain_map=TerrainMap(
            [[TerrainType.LAND for _column in range(3)] for _row in range(2)]
        ),
        player=Player(Position(row=1, column=0)),
        student_crowds=[
            StudentCrowd(row=0, columns=3, warning_time=1.0, active_duration=4.17)
        ],
    )
    set_current_stage(game, stage)

    game.update_stage(0.25)
    game.update_stage(0.75)
    game.update_stage(4.68)

    assert [cue for cue, _loops in game.sound_manager.played_cues] == [
        SoundCue.STUDENT_CROWD
    ]


def test_turtle_boarding_plays_turtle_sound_once() -> None:
    game = Game(initial_scene=PlayingScene())
    game.sound_manager = SoundManagerStub()
    turtle = Turtle(position=Position(row=0, column=1))
    stage = Stage(
        terrain_map=TerrainMap([[TerrainType.START, TerrainType.RIVER]]),
        player=Player(Position(row=0, column=0)),
        turtles=[turtle],
    )
    set_current_stage(game, stage)

    game.current_scene.handle_event(key_event(pygame.K_RIGHT))
    game.current_scene.update(0.3)

    assert game.sound_manager.played_cues == [
        (SoundCue.TURTLE, 0),
        (SoundCue.MOVE_SUCCESS, 0),
    ]


def test_playing_scene_uses_player_sprite_for_facing_direction() -> None:
    pygame.font.init()
    surface = pygame.Surface((240, 240))
    player = Player(Position(row=0, column=0), facing_direction=Direction.LEFT)
    stage = Stage(
        terrain_map=TerrainMap([[TerrainType.START]]),
        player=player,
    )
    game = Game(initial_scene=PlayingScene())
    set_current_stage(game, stage)

    game.current_scene.draw(surface)

    assert game.resource_manager.get_image("player_goose_left_0") is not None
    assert game.resource_manager.get_image("player_goose_right_0") is None

    player.facing_direction = Direction.RIGHT
    game.current_scene.draw(surface)

    assert game.resource_manager.get_image("player_goose_right_0") is not None


def test_playing_scene_uses_player_hop_animation_frames_when_registered() -> None:
    game = Game(initial_scene=PlayingScene())
    renderer = renderer_for_game(game)
    frames = [object(), object(), object()]
    for frame, image in enumerate(frames):
        game.resource_manager.register_image(f"player_goose_right_{frame}", image)

    assert renderer.player_image(Direction.RIGHT) is frames[0]
    assert renderer.player_image(Direction.RIGHT, 0.09, True) is frames[1]
    assert renderer.player_image(Direction.RIGHT, 0.17, True) is frames[2]


def test_playing_scene_draws_default_stage_player_sprite_on_screen() -> None:
    pygame.font.init()
    surface = pygame.Surface((960, 720))
    game = Game(initial_scene=PlayingScene())
    game.current_stage_id = 1
    player_color = (250, 10, 200)
    player_image = pygame.Surface((16, 16), pygame.SRCALPHA)
    player_image.fill((*player_color, 255))
    game.resource_manager.register_image("player_goose_up_0", player_image)

    game.current_scene.draw(surface)
    player_pixels = sum(
        1
        for x in range(surface.get_width())
        for y in range(surface.get_height())
        if surface.get_at((x, y))[:3] == player_color
    )

    assert player_pixels >= 16


def test_playing_scene_hops_between_tiles_after_successful_move() -> None:
    game = Game(initial_scene=PlayingScene())
    stage = Stage(
        terrain_map=TerrainMap(
            [[TerrainType.START, TerrainType.LAND, TerrainType.LAND]]
        ),
        player=Player(Position(row=0, column=0)),
    )
    set_current_stage(game, stage)
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


def test_playing_scene_camera_focus_moves_smoothly_toward_player() -> None:
    class RendererSpy:
        def __init__(self) -> None:
            self.camera_focuses = []

        def draw(self, *args, **kwargs) -> None:
            self.camera_focuses.append(kwargs.get("camera_focus"))

    game = Game(initial_scene=PlayingScene())
    stage = Stage(
        terrain_map=TerrainMap(
            [[TerrainType.START, TerrainType.LAND, TerrainType.LAND]]
        ),
        player=Player(Position(row=0, column=0)),
    )
    set_current_stage(game, stage)
    scene = game.current_scene
    scene._renderer = RendererSpy()

    scene.draw(object())
    scene.handle_event(key_event(pygame.K_RIGHT))
    scene.update(0.05)
    scene.draw(object())

    assert scene._renderer.camera_focuses[0] == Position(row=0, column=0)
    camera_focus = scene._renderer.camera_focuses[-1]
    assert camera_focus.row == 0
    assert 0 < camera_focus.column < stage.player.position.column


def test_successful_hop_plays_start_then_success_sound() -> None:
    game = Game(initial_scene=PlayingScene())
    game.sound_manager = SoundManagerStub()
    stage = Stage(
        terrain_map=TerrainMap(
            [[TerrainType.START, TerrainType.LAND, TerrainType.LAND]]
        ),
        player=Player(Position(row=0, column=0)),
    )
    set_current_stage(game, stage)
    scene = game.current_scene

    scene.handle_event(key_event(pygame.K_RIGHT))

    assert game.sound_manager.played_cues == [(SoundCue.MOVE_START, 0)]

    scene.update(0.3)

    assert game.sound_manager.played_cues == [
        (SoundCue.MOVE_START, 0),
        (SoundCue.MOVE_SUCCESS, 0),
    ]


def test_blocked_move_plays_blocked_sound_with_blocked_hop() -> None:
    game = Game(initial_scene=PlayingScene())
    game.sound_manager = SoundManagerStub()
    stage = Stage(
        terrain_map=TerrainMap([[TerrainType.START, TerrainType.WALL]]),
        player=Player(Position(row=0, column=0)),
    )
    set_current_stage(game, stage)
    scene = game.current_scene

    scene.handle_event(key_event(pygame.K_RIGHT))

    assert game.sound_manager.played_cues == [(SoundCue.BLOCKED, 0)]
    assert stage.player.position == Position(row=0, column=0)
    assert scene._hop_start_position == Position(row=0, column=0)
    assert scene._hop_end_position == Position(row=0, column=1)

    scene.update(HOP_DURATION)

    assert scene._hop_start_position is None
    assert game.sound_manager.played_cues == [(SoundCue.BLOCKED, 0)]


def test_blocked_input_during_hop_waits_without_collision_sound() -> None:
    game = Game(initial_scene=PlayingScene())
    game.sound_manager = SoundManagerStub()
    stage = Stage(
        terrain_map=TerrainMap(
            [[TerrainType.START, TerrainType.LAND, TerrainType.WALL]]
        ),
        player=Player(Position(row=0, column=0)),
    )
    set_current_stage(game, stage)
    scene = game.current_scene

    scene.handle_event(key_event(pygame.K_RIGHT))
    scene.handle_event(key_event(pygame.K_RIGHT))

    assert game.current_stage.player.position == Position(row=0, column=1)
    assert scene._hop_start_position == Position(row=0, column=0)
    assert game.sound_manager.played_cues == [(SoundCue.MOVE_START, 0)]


def test_player_hop_draw_rect_arcs_up_without_large_scaling() -> None:
    renderer = renderer_without_assets()
    grid_rect = pygame.Rect(0, 0, 200, 100)
    start = Position(row=0, column=0)
    end = Position(row=0, column=1)

    base_rect = renderer.player_draw_rect(
        grid_rect,
        100,
        start,
    )

    jump_rect = renderer.player_draw_rect(
        grid_rect,
        100,
        end,
        hop_state=(start, end, HOP_DURATION * 0.5),
    )
    start_rect = renderer.cell_rect(grid_rect, 100, start)
    end_rect = renderer.cell_rect(grid_rect, 100, end)
    linear_mid_y = round((start_rect.centery + end_rect.centery) / 2)

    assert base_rect.width == 75
    assert jump_rect.width <= round(base_rect.width * 1.12)
    assert jump_rect.centery < linear_mid_y


def test_player_hop_draw_rect_uses_hop_before_turtle_carry_offset() -> None:
    renderer = renderer_without_assets()
    grid_rect = pygame.Rect(0, 0, 200, 100)
    start = Position(row=0, column=0)
    end = Position(row=0, column=1)
    hop_state = (start, end, HOP_DURATION * 0.5)
    carried_turtle = Turtle(
        position=end,
        direction=Direction.RIGHT,
        distance_progress=0.75,
    )

    carried_rect = renderer.player_draw_rect(
        grid_rect,
        100,
        end,
        carried=carried_turtle,
    )
    hop_rect = renderer.player_draw_rect(
        grid_rect,
        100,
        end,
        carried=carried_turtle,
        hop_state=hop_state,
    )
    expected_hop_rect = renderer.player_draw_rect(
        grid_rect,
        100,
        end,
        hop_state=hop_state,
    )

    assert hop_rect == expected_hop_rect
    assert hop_rect != carried_rect


def test_blocked_hop_draw_rect_returns_toward_start() -> None:
    renderer = renderer_without_assets()
    grid_rect = pygame.Rect(0, 0, 200, 100)
    start = Position(row=0, column=0)
    target = Position(row=0, column=1)

    base_rect = renderer.player_draw_rect(grid_rect, 100, start)
    target_rect = renderer.cell_rect(grid_rect, 100, target)
    late_rect = renderer.player_draw_rect(
        grid_rect,
        100,
        start,
        hop_state=(start, target, HOP_DURATION * 0.95),
    )

    assert late_rect.centerx < (base_rect.centerx + target_rect.centerx) // 2


def test_playing_scene_grid_layout_applies_playing_view_zoom() -> None:
    renderer = renderer_without_assets()

    grid_rect, cell_size = renderer.calculate_grid_layout(
        960, 720, 24, 10, Position(row=23, column=5)
    )

    assert cell_size == pytest.approx(96 * PLAYING_VIEW_ZOOM)
    assert grid_rect.width > 960
    assert grid_rect.height > 720


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
    set_current_stage(game, stage)

    game.current_scene.draw(surface)

    terrain_color = TERRAIN_STYLES[TerrainType.LAND]
    hud_pixel = surface.get_at((20, 20))[:3]

    assert hud_pixel != terrain_color
    assert hud_pixel != DEFAULT_BACKGROUND_COLOR


def test_playing_hud_padding_contains_status_lines() -> None:
    pygame.font.init()
    surface = pygame.Surface((420, 120))
    surface.fill(DEFAULT_BACKGROUND_COLOR)
    renderer = renderer_without_assets()
    title_font = pygame.font.Font(None, 44)
    body_font = pygame.font.Font(None, 26)

    renderer.draw_playing_hud(surface, title_font, body_font, "1", "12.5s")

    assert surface.get_at((10, 60))[:3] != DEFAULT_BACKGROUND_COLOR
    assert surface.get_at((10, 100))[:3] == DEFAULT_BACKGROUND_COLOR


def test_playing_scene_isometric_layout_keeps_player_in_play_area() -> None:
    renderer = renderer_without_assets()

    grid_rect, cell_size = renderer.calculate_grid_layout(
        800, 600, 24, 10, Position(row=23, column=5)
    )
    player_rect = renderer.cell_rect(
        grid_rect,
        cell_size,
        Position(row=23, column=5),
    )

    assert cell_size == pytest.approx(80 * PLAYING_VIEW_ZOOM)
    assert grid_rect.width > 800
    assert grid_rect.height > 600
    assert 0 <= player_rect.centerx <= 800
    assert player_rect.bottom <= 600
    assert player_rect.centery > 600 // 2


def test_playing_scene_isometric_layout_stacks_rows_diagonally() -> None:
    renderer = renderer_without_assets()

    grid_rect, cell_size = renderer.calculate_grid_layout(
        800, 600, 24, 10, Position(row=12, column=5)
    )
    player_rect = renderer.cell_rect(
        grid_rect,
        cell_size,
        Position(row=12, column=5),
    )
    top_rect = renderer.cell_rect(grid_rect, cell_size, Position(row=0, column=5))

    assert player_rect.center == (400, 300)
    assert player_rect.centerx < top_rect.centerx
    assert player_rect.centery > top_rect.centery


def test_position_sprite_draw_rects_use_fractional_progress() -> None:
    renderer = renderer_without_assets()
    grid_rect = pygame.Rect(0, 0, 200, 100)
    bike = Bike(
        position=Position(row=0, column=0),
        direction=Direction.RIGHT,
        distance_progress=0.5,
    )

    draw_rect = renderer.sprite_draw_rects(bike, grid_rect, 100)[0]
    base_rect = renderer.cell_rect(grid_rect, 100, Position(row=0, column=0))

    assert draw_rect.centerx == base_rect.centerx + 25
    assert draw_rect.centery == base_rect.centery + 12


def test_position_sprite_progress_follows_isometric_left_direction() -> None:
    renderer = renderer_without_assets()
    grid_rect = pygame.Rect(0, 0, 200, 100)
    bike = Bike(
        position=Position(row=0, column=0),
        direction=Direction.LEFT,
        distance_progress=0.5,
    )

    draw_rect = renderer.sprite_draw_rects(bike, grid_rect, 100)[0]
    base_rect = renderer.cell_rect(grid_rect, 100, Position(row=0, column=0))

    assert draw_rect.centerx == base_rect.centerx - 25
    assert draw_rect.centery == base_rect.centery - 12


def test_position_sprite_disappears_after_crossing_map_edge() -> None:
    renderer = renderer_without_assets()
    grid_rect = pygame.Rect(0, 0, 300, 150)
    cases = (
        (
            Bike(Position(row=0, column=2), Direction.RIGHT, distance_progress=0.75),
            Bike(Position(row=0, column=2), Direction.RIGHT, distance_progress=0.49),
        ),
        (
            Turtle(Position(row=0, column=0), Direction.LEFT, distance_progress=0.75),
            Turtle(Position(row=0, column=0), Direction.LEFT, distance_progress=0.49),
        ),
    )

    for hidden_sprite, visible_sprite in cases:
        assert (
            renderer.sprite_draw_rects(hidden_sprite, grid_rect, 100, columns=3) == []
        )

        draw_rects = renderer.sprite_draw_rects(
            visible_sprite,
            grid_rect,
            100,
            columns=3,
        )
        assert len(draw_rects) == 1


def test_position_sprites_draw_bike_animation_frame_when_registered() -> None:
    pygame.font.init()
    surface = pygame.Surface((240, 120))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    register_bike_test_images(game)
    renderer = renderer_for_game(game)
    bike = Bike(
        position=Position(row=0, column=0),
        direction=Direction.RIGHT,
        distance_progress=0.5,
    )

    renderer.draw_position_sprites(
        surface,
        [bike],
        pygame.Rect(0, 0, 200, 100),
        100,
        (BIKE_COLOR, renderer.bike_image, 0.4),
        None,
    )
    rendered_colors = collect_surface_colors(surface)

    assert (18, 210, 230) in rendered_colors


def test_position_sprites_draw_turtle_image_when_registered() -> None:
    pygame.font.init()
    surface = pygame.Surface((240, 120))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    register_turtle_test_images(game)
    renderer = renderer_for_game(game)
    turtle = Turtle(
        position=Position(row=0, column=0),
        direction=Direction.RIGHT,
    )

    renderer.draw_position_sprites(
        surface,
        [turtle],
        pygame.Rect(0, 0, 200, 100),
        100,
        (TURTLE_COLOR, renderer.turtle_image, 0.32),
        None,
    )
    rendered_colors = collect_surface_colors(surface)

    assert (34, 220, 120) in rendered_colors


def test_bike_assets_keep_four_padded_animation_frames() -> None:
    paths = sorted(Path("assets").glob("bike_frame_*.png"))

    assert [path.stem for path in paths] == [
        "bike_frame_0",
        "bike_frame_1",
        "bike_frame_2",
        "bike_frame_3",
    ]
    for path in paths:
        image = pygame.image.load(str(path))
        visible = image.get_bounding_rect(1)

        assert visible.width / image.get_width() <= 0.93, path.name
        assert visible.height / image.get_height() <= 0.93, path.name


def test_turtle_assets_keep_visible_body_inside_canvas_padding() -> None:
    for path in sorted(Path("assets").glob("turtle_*.png")):
        image = pygame.image.load(str(path))
        visible = image.get_bounding_rect(1)

        assert visible.width / image.get_width() <= 0.8, path.name
        assert visible.height / image.get_height() <= 0.8, path.name


def test_student_crowd_warning_assets_allow_isometric_row_angle() -> None:
    for path in sorted(Path("assets").glob("student_crowd_warning_frame_*.png")):
        image = pygame.image.load(str(path))
        visible = image.get_bounding_rect(1)

        assert image.get_width() / image.get_height() <= 2.5, path.name
        assert visible.height / visible.width >= 0.25, path.name


def test_student_crowd_warning_draws_registered_warning_frame() -> None:
    pygame.font.init()
    surface = pygame.Surface((320, 100))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    register_student_crowd_test_images(game)
    renderer = renderer_for_game(game)
    crowd = StudentCrowd(
        row=0,
        columns=3,
        warning_time=1.0,
        active_duration=1.0,
        elapsed_time=0.5,
    )

    renderer.draw_student_crowds(
        surface,
        [crowd],
        TerrainMap([[TerrainType.LAND for _column in range(3)]]),
        pygame.Rect(0, 0, 300, 100),
        100,
    )
    rendered_colors = collect_surface_colors(surface)

    assert (199, 141, 82) in rendered_colors
    assert STUDENT_CROWD_COLOR not in rendered_colors


def test_student_crowd_active_draws_registered_active_frame() -> None:
    pygame.font.init()
    active_color = (16, 188, 204)
    surface = pygame.Surface((320, 100))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    renderer = renderer_for_game(game)
    for index in range(4):
        image = pygame.Surface((96, 32), pygame.SRCALPHA)
        image.fill((*active_color, 255))
        game.resource_manager.register_image(
            f"student_crowd_active_frame_{index}", image
        )
    crowd = StudentCrowd(
        row=0,
        columns=3,
        warning_time=0.2,
        active_duration=1.0,
        elapsed_time=0.2,
    )

    grid, cell_size = renderer.calculate_grid_layout(300, 100, 1, 3)
    renderer.draw_student_crowds(
        surface,
        [crowd],
        TerrainMap([[TerrainType.LAND for _column in range(3)]]),
        grid,
        cell_size,
    )
    rendered_colors = collect_surface_colors(surface)

    assert active_color in rendered_colors
    assert STUDENT_CROWD_COLOR not in rendered_colors


def test_student_crowd_active_uses_first_animation_frame_at_start() -> None:
    pygame.font.init()
    surface = pygame.Surface((820, 260))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    register_student_crowd_test_images(game)
    renderer = renderer_for_game(game)
    crowd = StudentCrowd(
        row=0,
        columns=8,
        warning_time=0.2,
        active_duration=1.0,
        elapsed_time=0.2,
    )

    grid, cell_size = renderer.calculate_grid_layout(800, 260, 1, 8)
    renderer.draw_student_crowds(
        surface,
        [crowd],
        TerrainMap([[TerrainType.LAND for _column in range(8)]]),
        grid,
        cell_size,
    )
    rendered_colors = collect_surface_colors(surface)

    assert (29, 211, 188) in rendered_colors
    assert (211, 64, 92) not in rendered_colors


def test_student_crowd_active_frame_duration_is_simple_loop() -> None:
    assert STUDENT_CROWD_FRAME_DURATION == 0.12


def test_student_crowd_active_draws_padded_frame_art() -> None:
    pygame.font.init()
    active_color = (29, 211, 188)
    surface = pygame.Surface((320, 100))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    renderer = renderer_for_game(game)
    for index in range(4):
        image = pygame.Surface((96, 32), pygame.SRCALPHA)
        image.fill((0, 0, 0, 0))
        image.fill((*active_color, 255), pygame.Rect(8, 8, 80, 16))
        game.resource_manager.register_image(
            f"student_crowd_active_frame_{index}", image
        )
    crowd = StudentCrowd(
        row=0,
        columns=3,
        warning_time=0.2,
        active_duration=1.0,
        elapsed_time=0.2,
    )

    grid, cell_size = renderer.calculate_grid_layout(300, 100, 1, 3)
    renderer.draw_student_crowds(
        surface,
        [crowd],
        TerrainMap([[TerrainType.LAND for _column in range(3)]]),
        grid,
        cell_size,
    )
    rendered_colors = collect_surface_colors(surface)

    assert active_color in rendered_colors
    assert (0, 0, 0) in rendered_colors


def test_student_crowd_active_advances_animation_frame() -> None:
    pygame.font.init()
    surface = pygame.Surface((320, 100))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    register_student_crowd_test_images(game)
    renderer = renderer_for_game(game)
    crowd = StudentCrowd(
        row=0,
        columns=3,
        warning_time=0.2,
        active_duration=1.0,
        elapsed_time=0.2 + STUDENT_CROWD_FRAME_DURATION * 1.5,
    )

    grid, cell_size = renderer.calculate_grid_layout(300, 100, 1, 3)
    renderer.draw_student_crowds(
        surface,
        [crowd],
        TerrainMap([[TerrainType.LAND for _column in range(3)]]),
        grid,
        cell_size,
    )
    rendered_colors = collect_surface_colors(surface)

    assert (211, 64, 92) in rendered_colors
    assert (29, 211, 188) not in rendered_colors


def test_student_crowd_active_stops_after_active_duration() -> None:
    pygame.font.init()
    surface = pygame.Surface((320, 100))
    surface.fill((0, 0, 0))
    game = Game(initial_scene=PlayingScene())
    register_student_crowd_test_images(game)
    renderer = renderer_for_game(game)
    crowd = StudentCrowd(
        row=0,
        columns=3,
        warning_time=0.2,
        active_duration=1.0,
        elapsed_time=0.2 + 1.0,
    )

    grid, cell_size = renderer.calculate_grid_layout(300, 100, 1, 3)
    renderer.draw_student_crowds(
        surface,
        [crowd],
        TerrainMap([[TerrainType.LAND for _column in range(3)]]),
        grid,
        cell_size,
    )
    rendered_colors = collect_surface_colors(surface)

    assert (29, 211, 188) not in rendered_colors
    assert rendered_colors == {(0, 0, 0)}


def test_playing_scene_changes_to_failed_or_result_for_stage_outcomes() -> None:
    game = Game(initial_scene=PlayingScene())
    stage = StageStub()
    timer = TimerStub()
    save_manager = SaveManagerStub()
    sound_manager = SoundManagerStub()
    set_current_stage(game, stage)
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


def test_result_next_requires_current_stage_context() -> None:
    game = Game(initial_scene=ResultScene())

    with pytest.raises(TypeError):
        game.current_scene.handle_event(key_event(pygame.K_n))


def test_failed_restart_requires_current_stage_context() -> None:
    game = Game(initial_scene=FailedScene())

    with pytest.raises(KeyError):
        game.current_scene.handle_event(key_event(pygame.K_r))


def test_locked_stage_message_requires_scene_contract() -> None:
    game = Game(initial_scene=BareScene())
    game.progress = ProgressStub({2})

    with pytest.raises(AttributeError):
        game.select_stage(1)


def test_start_stage_uses_stage_id_for_ambience() -> None:
    game = Game(stages={4: IncompleteStageStub()})
    game.timer = TimerStub()
    game.sound_manager = SoundManagerStub()

    game.start_stage(4)

    assert game.sound_manager.played_cues == [
        (SoundCue.BIKE_AMBIENCE, -1),
        (SoundCue.WATER_AMBIENCE, -1),
    ]


def test_move_sound_requires_stage_player_contract() -> None:
    game = Game(stages={1: object()})
    game.current_stage_id = 1

    with pytest.raises(AttributeError):
        game._handle_move_result(MOVE_MOVED)


def test_playing_scene_hop_input_requires_stage_context() -> None:
    game = Game(initial_scene=PlayingScene(), stages={1: object()})
    game.current_stage_id = 1
    game.current_scene._hop_start_position = Position(0, 0)

    with pytest.raises(AttributeError):
        game.current_scene.handle_event(key_event(pygame.K_RIGHT))


def test_failed_scene_draw_requires_failure_reason_context() -> None:
    game = Game(initial_scene=FailedScene())
    pygame.font.init()
    surface = pygame.Surface((640, 480))

    with pytest.raises(AttributeError):
        game.current_scene.draw(surface)


def test_result_scene_draw_requires_clear_context() -> None:
    game = Game(initial_scene=ResultScene())
    pygame.font.init()
    surface = pygame.Surface((640, 480))

    with pytest.raises(TypeError):
        game.current_scene.draw(surface)
