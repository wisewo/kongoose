# Sequence Diagrams

## Notes

- 이 문서는 SSD보다 한 단계 내부 설계에 가까운 Sequence Diagram이다.
- 각 Sequence Diagram은 세부 설계의 주요 객체 호출 흐름을 기준으로 한다.
- 키 입력은 각 `Scene.handle_event(event)`가 받고, 필요한 경우 `Game` 공개 메서드를 호출한다.
- 별도 `ScreenManager`는 두지 않고, `Game.change_scene(scene)`가 현재 화면 객체를 교체한 뒤 `scene.enter(game)`를 호출한다.
- 게임 진행 화면의 2.5D 표현은 `StageRenderer`가 2D row/column 좌표를 얕은 등각 투영 화면 좌표로 변환해 그리는 렌더링 책임이다.
- `TerrainMap.can_enter(position)`은 맵 범위와 벽만 막으며, 강 칸은 막지 않는다.
- `Stage`는 지형과 동적 객체를 조합해 이동, 실패, 경고, 자라 탑승, 클리어를 판정한다.
- 이동 결과와 갱신 결과는 Result Object가 아니라 공통 모델의 문자열 상수이다.
- 자라 탑승과 하차 판정은 `Turtle.interaction_position()`을 사용한다. 이동 진행률이 50% 미만이면 현재 칸, 50% 이상이면 다음 칸을 기준으로 한다.
- `Goal` 클래스는 사용하지 않고 `TerrainType.GOAL`로 목적지를 표현한다.
- 사운드는 `SoundManager.play(cue, loops=0, volume=None)`와 `SoundManager.stop(cue)`로 처리한다.

## Traceability

| Sequence Diagram | Related Use Case | Main System Operation | Main Related FR |
|---|---|---|---|
| SD-01 | UC-01 메인 화면 진입 | `start_game()`, `return_to_main()` | FR-01, FR-02, FR-19, FR-20, FR-24 |
| SD-02 | UC-02 스테이지 선택 화면 진입 | `open_stage_select()` | FR-02, FR-03, FR-04, FR-13, FR-14, FR-20, FR-24 |
| SD-03 | UC-03 게임 종료 | `quit_game()` | FR-01 |
| SD-04 | UC-04 스테이지 선택 | `select_stage(stage_id)` | FR-02, FR-03, FR-04, FR-14, FR-24 |
| SD-05 | UC-05 캐릭터 이동 | `move_player(direction)` | FR-04, FR-05, FR-06, FR-07, FR-08, FR-09, FR-10, FR-11, FR-12, FR-16, FR-17, FR-18, FR-19, FR-20, FR-21, FR-22, FR-23, FR-24, FR-25 |
| SD-06 | UC-06 실패 후 행동 선택 | `restart_stage()`, `open_stage_select()`, `return_to_main()` | FR-02, FR-13, FR-15, FR-24 |
| SD-07 | UC-07 클리어 후 행동 선택 | `start_next_stage()`, `restart_stage()`, `open_stage_select()`, `return_to_main()` | FR-02, FR-03, FR-04, FR-13, FR-17, FR-18, FR-24 |

## SD-01 / UC-01 메인 화면 진입

```mermaid
sequenceDiagram
    actor User as Player
    participant Game
    participant SaveManager
    participant SoundManager
    participant MainScene
    participant Progress

    alt Game 생성 및 실행
        Game->>SaveManager: load_progress()
        SaveManager-->>Game: Progress
        User->>Game: run()
        Game->>SoundManager: load(DEFAULT_SOUND_PATHS)
        Game->>SoundManager: play(BACKGROUND_MUSIC, loops=-1)
        Game->>Game: change_scene(MainScene)
    else 다른 화면에서 메인 이동
        User->>Game: return_to_main()
        Game->>Game: _stop_stage_ambience()
        Game->>SoundManager: play(UI_SELECT)
        Game->>Game: change_scene(MainScene)
    end

    Game->>MainScene: enter(game)
    MainScene->>Progress: is_stage_unlocked(stage_id) for 1..4
    MainScene->>MainScene: draw(surface)
    MainScene-->>User: 메인 화면, 해금 수, 키 안내 표시
```

## SD-02 / UC-02 스테이지 선택 화면 진입

```mermaid
sequenceDiagram
    actor User as Player
    participant MainScene
    participant PlayingScene
    participant FailedScene
    participant ResultScene
    participant Game
    participant SoundManager
    participant StageSelectScene
    participant Progress

    alt 메인 화면 Enter/Space
        User->>MainScene: handle_event(KEYDOWN)
        MainScene->>Game: open_stage_select()
    else 게임 진행 화면 Esc/B
        User->>PlayingScene: handle_event(KEYDOWN)
        PlayingScene->>Game: open_stage_select()
    else 실패 화면 S/B
        User->>FailedScene: handle_event(KEYDOWN)
        FailedScene->>Game: open_stage_select()
    else 결과 화면 S/B
        User->>ResultScene: handle_event(KEYDOWN)
        ResultScene->>Game: open_stage_select()
    end

    Game->>Game: _stop_stage_ambience()
    Game->>SoundManager: play(UI_SELECT)
    Game->>Game: change_scene(StageSelectScene)
    Game->>StageSelectScene: enter(game)
    StageSelectScene->>Progress: is_stage_unlocked(stage_id) for 1..4
    StageSelectScene->>Progress: get_best_stars(stage_id) for 1..4
    StageSelectScene->>StageSelectScene: draw(surface)
    StageSelectScene-->>User: 스테이지 목록, 해금 상태, 최고 별점 표시
```

## SD-03 / UC-03 게임 종료

```mermaid
sequenceDiagram
    actor User as Player
    participant MainScene
    participant Game

    User->>MainScene: handle_event(Esc or Q)
    MainScene->>Game: quit_game()
    Game->>Game: running = False
    Game-->>User: 게임 루프 종료 후 pygame.quit()
```

## SD-04 / UC-04 스테이지 선택

```mermaid
sequenceDiagram
    actor User as Player
    participant StageSelectScene
    participant Game
    participant Progress
    participant SoundManager
    participant Stage
    participant Timer
    participant PlayingScene

    User->>StageSelectScene: handle_event(number key 1..4)
    StageSelectScene->>Game: select_stage(stage_id)
    Game->>Progress: is_stage_unlocked(stage_id)

    alt 선택한 스테이지가 해금됨
        Progress-->>Game: true
        Game->>SoundManager: play(UI_SELECT)
        Game->>Game: start_stage(stage_id)
        Game->>Stage: initialize()
        Game->>Timer: reset()
        Game->>Timer: start()
        Game->>Game: change_scene(PlayingScene)
        Game->>PlayingScene: enter(game)
        Game->>Game: _sync_stage_ambience()
        Game->>SoundManager: stop(BIKE_AMBIENCE)
        Game->>SoundManager: stop(WATER_AMBIENCE)
        opt Stage 2/3/4
            Game->>SoundManager: play(BIKE_AMBIENCE or WATER_AMBIENCE, loops=-1, volume)
        end
        PlayingScene->>PlayingScene: draw(surface)
        PlayingScene-->>User: 게임 화면 표시
    else 선택한 스테이지가 잠김
        Progress-->>Game: false
        Game->>StageSelectScene: set_message("Stage N is locked.")
        StageSelectScene->>StageSelectScene: draw(surface)
        StageSelectScene-->>User: 스테이지 선택 화면 유지
    end
```

## SD-05 / UC-05 캐릭터 이동

```mermaid
sequenceDiagram
    actor User as Player
    participant PlayingScene
    participant Game
    participant Stage
    participant TerrainMap
    participant Position
    participant Timer
    participant StarRating
    participant Progress
    participant SaveManager
    participant SoundManager
    participant FailedScene
    participant ResultScene

    User->>PlayingScene: handle_event(arrow key)
    PlayingScene->>PlayingScene: remember start_position and target_position
    PlayingScene->>Game: move_player(direction)
    Game->>Stage: move_player(direction)
    Stage->>Stage: _player_interaction_position()
    Stage->>TerrainMap: can_enter(move_origin)
    Stage->>Position: moved(direction)
    Position-->>Stage: target_position
    Stage->>TerrainMap: can_enter(target_position)

    alt target_position is blocked or out of bounds
        TerrainMap-->>Stage: false
        Stage-->>Game: MOVE_BLOCKED
        Game->>SoundManager: play(BLOCKED)
        Game-->>PlayingScene: MOVE_BLOCKED
        PlayingScene->>PlayingScene: _start_hop(start_position, target_position, false)
        PlayingScene->>PlayingScene: draw(surface)
        PlayingScene-->>User: 막힌 방향 홉과 게임 화면 표시
    else target_position can be entered
        TerrainMap-->>Stage: true
        Stage->>Stage: player.position = target_position
        Stage->>Stage: evaluate_player_state()

        alt GOAL reached
            Stage-->>Game: MOVE_CLEARED
            Game->>Game: clear_current_stage()
            Game->>Timer: stop()
            Game->>Game: _stop_stage_ambience()
            Game->>Timer: get_elapsed_time()
            Timer-->>Game: clear_time
            Game->>StarRating: calculate(clear_time, stage_id)
            StarRating-->>Game: stars
            Game->>Progress: record_stage_clear(stage_id, stars)
            Game->>SaveManager: save_progress(progress)
            Game->>Game: change_scene(ResultScene)
            Game->>ResultScene: enter(game)
            Game->>SoundManager: play(CLEAR_SCREEN)
            ResultScene->>ResultScene: draw(surface)
            ResultScene-->>User: 클리어 시간과 별점 표시
        else failure reason set
            Stage-->>Game: MOVE_FAILED
            Game->>Game: _handle_failure_from_stage()
            opt FailureReason.FELL_IN_RIVER
                Game->>SoundManager: play(LAKE_SPLASH)
            end
            opt FailureReason.HIT_BIKE
                Game->>SoundManager: play(BIKE_COLLISION)
            end
            Game->>Game: fail_current_stage(reason)
            Game->>Game: _stop_stage_ambience()
            Game->>Game: change_scene(FailedScene)
            Game->>FailedScene: enter(game)
            Game->>SoundManager: play(FAILURE_SCREEN)
            FailedScene->>FailedScene: draw(surface)
            FailedScene-->>User: 실패 원인 표시
        else moved onto river turtle
            Stage-->>Game: MOVE_MOVED
            Game->>SoundManager: play(TURTLE)
            Game-->>PlayingScene: MOVE_MOVED
            PlayingScene->>PlayingScene: _start_hop(start_position, player.position, true)
            PlayingScene-->>User: 자라 탑승 이동 표시
        else regular moved
            Stage-->>Game: MOVE_MOVED
            Game->>SoundManager: play(MOVE_START)
            Game-->>PlayingScene: MOVE_MOVED
            PlayingScene->>PlayingScene: _start_hop(start_position, player.position, true)
            PlayingScene-->>User: 일반 이동 표시
        end
    end

    loop PlayingScene.update(dt)
        PlayingScene->>PlayingScene: advance hop timer
        opt hop finished after successful move
            PlayingScene->>SoundManager: play(MOVE_SUCCESS)
        end
        PlayingScene->>Game: update_stage(dt)
        Game->>Stage: update(dt)
        Stage->>Stage: update bikes, turtles, student_crowds
        Stage->>Stage: wrap bikes, evaluate_player_state(), wrap turtles
        Stage-->>Game: UPDATE_* string

        alt UPDATE_FAILED
            Game->>Game: _handle_failure_from_stage()
            Game-->>User: 실패 화면 표시
        else UPDATE_STUDENT_CROWD_ACTIVE
            Game->>SoundManager: play(STUDENT_CROWD)
            PlayingScene->>PlayingScene: draw(surface)
            PlayingScene-->>User: 학생 무리 활성 상태 표시
        else UPDATE_WARNING
            PlayingScene->>PlayingScene: draw(surface)
            PlayingScene-->>User: 학생 무리 경고 표시
        else UPDATE_TURTLE_RIDE or UPDATE_SAFE
            PlayingScene->>PlayingScene: _update_camera_focus(dt)
            PlayingScene->>PlayingScene: draw(surface)
            PlayingScene-->>User: 갱신된 게임 화면과 HUD 표시
        end
    end
```

## SD-06 / UC-06 실패 후 행동 선택

```mermaid
sequenceDiagram
    actor User as Player
    participant FailedScene
    participant Game
    participant SoundManager
    participant Stage
    participant Timer
    participant PlayingScene
    participant StageSelectScene
    participant MainScene

    FailedScene->>FailedScene: draw(surface)
    FailedScene-->>User: 실패 화면 표시

    alt R 입력
        User->>FailedScene: handle_event(KEYDOWN)
        FailedScene->>Game: restart_stage()
        Game->>SoundManager: play(UI_SELECT)
        Game->>Game: start_stage(current_stage_id)
        Game->>Stage: initialize()
        Game->>Timer: reset()
        Game->>Timer: start()
        Game->>Game: change_scene(PlayingScene)
        Game->>PlayingScene: enter(game)
        PlayingScene-->>User: 게임 화면 표시
    else S/B 입력
        User->>FailedScene: handle_event(KEYDOWN)
        FailedScene->>Game: open_stage_select()
        Game->>Game: change_scene(StageSelectScene)
        Game->>StageSelectScene: enter(game)
        StageSelectScene-->>User: 스테이지 선택 화면 표시
    else M/Esc 입력
        User->>FailedScene: handle_event(KEYDOWN)
        FailedScene->>Game: return_to_main()
        Game->>Game: change_scene(MainScene)
        Game->>MainScene: enter(game)
        MainScene-->>User: 메인 화면 표시
    end
```

## SD-07 / UC-07 클리어 후 행동 선택

```mermaid
sequenceDiagram
    actor User as Player
    participant ResultScene
    participant Game
    participant SoundManager
    participant Stage
    participant Timer
    participant PlayingScene
    participant StageSelectScene
    participant MainScene

    ResultScene->>ResultScene: draw(surface)
    ResultScene-->>User: 클리어 시간, 별점, 행동 키 표시

    alt N 입력
        User->>ResultScene: handle_event(KEYDOWN)
        ResultScene->>Game: start_next_stage()
        alt next_stage_id <= 4
            Game->>SoundManager: play(UI_SELECT)
            Game->>Game: start_stage(next_stage_id)
            Game->>Stage: initialize()
            Game->>Timer: reset()
            Game->>Timer: start()
            Game->>Game: change_scene(PlayingScene)
            Game->>PlayingScene: enter(game)
            PlayingScene-->>User: 다음 스테이지 게임 화면 표시
        else next_stage_id > 4
            Game->>ResultScene: set_message("There is no next stage.")
            ResultScene-->>User: 결과 화면 유지
        end
    else R 입력
        User->>ResultScene: handle_event(KEYDOWN)
        ResultScene->>Game: restart_stage()
        Game->>SoundManager: play(UI_SELECT)
        Game->>Game: start_stage(current_stage_id)
        Game->>Stage: initialize()
        Game->>Timer: reset()
        Game->>Timer: start()
        Game->>Game: change_scene(PlayingScene)
        Game->>PlayingScene: enter(game)
        PlayingScene-->>User: 현재 스테이지 게임 화면 표시
    else S/B 입력
        User->>ResultScene: handle_event(KEYDOWN)
        ResultScene->>Game: open_stage_select()
        Game->>Game: change_scene(StageSelectScene)
        Game->>StageSelectScene: enter(game)
        StageSelectScene-->>User: 스테이지 선택 화면 표시
    else M/Esc 입력
        User->>ResultScene: handle_event(KEYDOWN)
        ResultScene->>Game: return_to_main()
        Game->>Game: change_scene(MainScene)
        Game->>MainScene: enter(game)
        MainScene-->>User: 메인 화면 표시
    end
```
