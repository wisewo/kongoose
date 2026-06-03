# Sequence Diagrams

## Notes

- 이 문서는 SSD보다 한 단계 내부 설계에 가까운 Sequence Diagram이다.
- 각 Sequence Diagram은 대응되는 SSD의 시스템 오퍼레이션에서 시작한다.
- Actor에서 `Game`으로 향하는 첫 메시지는 SSD의 시스템 오퍼레이션을 그대로 사용한다.
- 이후 객체 간 메시지는 Class Diagram의 책임과 PEP 8 명명 규칙을 따른다.
- 별도 `ScreenManager`는 두지 않고, 화면별 `Scene.draw(surface)`가 사용자에게 보이는 화면을 그린다.
- 게임 진행 화면의 2.5D 표현은 `PlayingScene.draw(surface)`에서 2D row/column 좌표를 얕은 등각 투영 화면 좌표로 변환해 표시하는 렌더링 책임이다. 이 표현은 `Stage`의 이동, 충돌, 실패, 클리어 판정 흐름을 바꾸지 않는다.
- `TerrainMap`은 맵 범위와 벽 같은 정적 진입 불가 지형을 판단하며, 강 칸은 `can_enter(position)`에서 막지 않는다.
- `Stage`는 지형과 동적 객체를 조합해 이동, 실패, 경고, 자라 탑승, 클리어를 판정한다. 같은 판정 규칙은 플레이어 이동 직후와 `Stage.update(dt)` 직후에 모두 적용한다.
- `Goal` 클래스는 사용하지 않고 `TerrainType.GOAL`로 목적지를 표현한다.
- 사운드는 소리별 메서드가 아니라 `SoundManager.play(cue)`로 재생한다.
- 게임 루프의 시간 흐름은 SSD의 Actor로 두지 않고, `Game.run()` 내부에서 현재 `Scene.update(dt)`와 `Scene.draw(surface)`가 반복되는 흐름으로 표현한다.
- Use Case와의 Traceability를 위해 `SD-01`부터 `SD-07`까지 `UC-01`부터 `UC-07`에 대응시킨다.

## Traceability

| Sequence Diagram | Related Use Case | System Operation | Main Related FR |
|---|---|---|---|
| SD-01 | UC-01 메인 화면 진입 | `start_game()`, `return_to_main()` | FR-01, FR-02, FR-19, FR-20, FR-24 |
| SD-02 | UC-02 스테이지 선택 화면 진입 | `open_stage_select()` | FR-02, FR-03, FR-04, FR-13, FR-14, FR-24 |
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
    participant Progress
    participant MainScene

    alt 게임 프로그램 실행
        User->>Game: start_game()
        Game->>SaveManager: load_progress()
        SaveManager-->>Game: progress
        Game->>Game: change_scene(MainScene)
    else 다른 화면에서 메인 화면 이동 선택
        User->>Game: return_to_main()
        Game->>Game: change_scene(MainScene)
    end

    Game->>MainScene: enter(game)
    MainScene->>Progress: get_unlocked_stages()
    Progress-->>MainScene: unlocked_stages
    MainScene->>MainScene: draw(surface)
    MainScene-->>User: 메인 화면과 저장된 진행 상태 표시
```

## SD-02 / UC-02 스테이지 선택 화면 진입

```mermaid
sequenceDiagram
    actor User as Player
    participant Game
    participant Progress
    participant StageSelectScene

    User->>Game: open_stage_select()
    Game->>Game: get_stage_list()
    Game->>Progress: get_unlocked_stages()
    Progress-->>Game: unlocked_stages
    Game->>Game: change_scene(StageSelectScene)
    Game->>StageSelectScene: enter(game)
    StageSelectScene->>StageSelectScene: draw(surface)
    StageSelectScene-->>User: 스테이지 목록과 해금 상태 표시
```

## SD-03 / UC-03 게임 종료

```mermaid
sequenceDiagram
    actor User as Player
    participant Game

    User->>Game: quit_game()
    Note over Game: 실행 중 플래그를 종료 상태로 변경하고 Pygame 종료 준비
    Game-->>User: 프로그램 종료
```

## SD-04 / UC-04 스테이지 선택

```mermaid
sequenceDiagram
    actor User as Player
    participant Game
    participant Progress
    participant Stage
    participant Timer
    participant StageSelectScene
    participant PlayingScene

    User->>Game: select_stage(stage_id)
    Game->>Progress: is_stage_unlocked(stage_id)

    alt 선택한 스테이지가 해금됨
        Progress-->>Game: true
        Game->>Game: start_stage(stage_id)
        Game->>Stage: initialize()
        Game->>Timer: reset()
        Game->>Timer: start()
        Game->>Game: change_scene(PlayingScene)
        Game->>PlayingScene: enter(game)
        PlayingScene->>PlayingScene: draw(surface)
        PlayingScene-->>User: 게임 화면 표시
    else 선택한 스테이지가 잠김
        Progress-->>Game: false
        Note over StageSelectScene: 잠긴 스테이지 안내 상태 설정
        StageSelectScene->>StageSelectScene: draw(surface)
        StageSelectScene-->>User: 잠긴 스테이지 안내 표시
    end
```

## SD-05 / UC-05 캐릭터 이동

```mermaid
sequenceDiagram
    actor User as Player
    participant Game
    participant PlayingScene
    participant Stage
    participant Position
    participant TerrainMap
    participant PlayerObj as Player
    participant Bike
    participant RunningCrew
    participant Turtle
    participant Timer
    participant StarRating
    participant Progress
    participant SaveManager
    participant SoundManager
    participant FailedScene
    participant ResultScene

    User->>Game: move_player(direction)
    Game->>PlayingScene: handle_event(direction)
    PlayingScene->>Stage: move_player(direction)
    Stage->>Position: moved(direction)
    Position-->>Stage: target_position
    Stage->>TerrainMap: can_enter(target_position)

    alt 이동 불가능한 위치
        TerrainMap-->>Stage: false
        Stage-->>PlayingScene: MoveResult(blocked)
        PlayingScene->>PlayingScene: draw(surface)
        PlayingScene-->>User: 현재 게임 화면 갱신
    else 이동 가능한 위치
        TerrainMap-->>Stage: true
        Stage->>PlayerObj: move_to(target_position)
        Stage->>TerrainMap: get_terrain(target_position)
        TerrainMap-->>Stage: terrain_type
        Stage->>Bike: occupies(target_position)
        Stage->>RunningCrew: occupies(target_position)
        Stage->>Turtle: occupies(target_position)
        Stage->>Stage: evaluate_player_state()

        alt 목적지 도착
            Stage-->>PlayingScene: MoveResult(cleared)
            PlayingScene->>Timer: get_elapsed_time()
            Timer-->>PlayingScene: clear_time
            PlayingScene->>StarRating: calculate(clear_time, stage)
            StarRating-->>PlayingScene: stars
            PlayingScene->>Progress: record_stage_clear(stage_id, stars)
            PlayingScene->>SaveManager: save_progress(progress)
            PlayingScene->>Game: change_scene(ResultScene)
            Game->>ResultScene: enter(game)
            ResultScene->>ResultScene: draw(surface)
            ResultScene-->>User: 스테이지 클리어 화면과 별점 표시
        else 실패 조건 발생
            Stage-->>PlayingScene: MoveResult(failed, failure_reason)
            PlayingScene->>SoundManager: play(SoundCue.FAILURE)
            PlayingScene->>Game: change_scene(FailedScene)
            Game->>FailedScene: enter(game)
            FailedScene->>FailedScene: draw(surface)
            FailedScene-->>User: 실패 화면 표시
        else 자라 탑승
            Stage-->>PlayingScene: MoveResult(moved)
            PlayingScene->>SoundManager: play(SoundCue.TURTLE)
            PlayingScene->>PlayingScene: draw(surface)
            PlayingScene-->>User: 변경된 게임 화면과 상태 정보 표시
        else 일반 이동
            Stage-->>PlayingScene: MoveResult(moved)
            PlayingScene->>SoundManager: play(SoundCue.MOVE)
            Note over PlayingScene,Stage: 이동 직후 판정은 완료되며, 게임 루프 갱신에서도 같은 판정 규칙을 재사용
            PlayingScene->>PlayingScene: draw(surface)
            PlayingScene-->>User: 변경된 게임 화면과 상태 정보 표시
        end
    end

    loop Game.run() 내부 반복
        Game->>PlayingScene: update(dt)
        PlayingScene->>Stage: update(dt)
        Stage->>Bike: update(dt)
        Stage->>RunningCrew: update(dt)
        Stage->>Turtle: update(dt)
        Stage->>Stage: evaluate_player_state()
        Stage-->>PlayingScene: StageUpdateResult(result_type)

        alt 실패 조건 발생
            PlayingScene->>SoundManager: play(SoundCue.FAILURE)
            PlayingScene->>Game: change_scene(FailedScene)
            Game->>FailedScene: enter(game)
            FailedScene->>FailedScene: draw(surface)
            FailedScene-->>User: 실패 화면 표시
        else 러닝크루 경고 발생
            PlayingScene->>SoundManager: play(SoundCue.RUNNING_CREW_WARNING)
            PlayingScene->>PlayingScene: draw(surface)
            PlayingScene-->>User: 경고와 게임 화면 표시
        else 자라 탑승
            PlayingScene->>SoundManager: play(SoundCue.TURTLE)
            PlayingScene->>PlayingScene: draw(surface)
            PlayingScene-->>User: 갱신된 게임 화면과 상태 정보 표시
        else 자전거 환경음 필요
            PlayingScene->>SoundManager: play(SoundCue.BIKE_AMBIENCE)
            PlayingScene->>PlayingScene: draw(surface)
            PlayingScene-->>User: 갱신된 게임 화면과 상태 정보 표시
        else 안전 상태
            PlayingScene->>PlayingScene: draw(surface)
            PlayingScene-->>User: 갱신된 게임 화면과 상태 정보 표시
        end
    end
```

## SD-06 / UC-06 실패 후 행동 선택

```mermaid
sequenceDiagram
    actor User as Player
    participant Game
    participant Stage
    participant Timer
    participant Progress
    participant FailedScene
    participant StageSelectScene
    participant MainScene
    participant PlayingScene

    FailedScene->>FailedScene: draw(surface)
    FailedScene-->>User: 실패 화면 표시

    alt 재시작 버튼 클릭
        User->>Game: restart_stage()
        Game->>Stage: initialize()
        Game->>Timer: reset()
        Game->>Timer: start()
        Game->>Game: change_scene(PlayingScene)
        Game->>PlayingScene: enter(game)
        PlayingScene->>PlayingScene: draw(surface)
        PlayingScene-->>User: 게임 화면 표시
    else 스테이지 선택 버튼 클릭
        User->>Game: open_stage_select()
        Game->>Progress: get_unlocked_stages()
        Progress-->>Game: unlocked_stages
        Game->>Game: change_scene(StageSelectScene)
        Game->>StageSelectScene: enter(game)
        StageSelectScene->>StageSelectScene: draw(surface)
        StageSelectScene-->>User: 스테이지 선택 화면 표시
    else 메인 화면 버튼 클릭
        User->>Game: return_to_main()
        Game->>Game: change_scene(MainScene)
        Game->>MainScene: enter(game)
        MainScene->>MainScene: draw(surface)
        MainScene-->>User: 메인 화면 표시
    end
```

## SD-07 / UC-07 클리어 후 행동 선택

```mermaid
sequenceDiagram
    actor User as Player
    participant Game
    participant Stage
    participant Timer
    participant Progress
    participant ResultScene
    participant PlayingScene
    participant StageSelectScene
    participant MainScene

    ResultScene->>ResultScene: draw(surface)
    ResultScene-->>User: 클리어 시간, 별점, 다음 행동 표시

    alt 다음 스테이지 버튼 클릭
        User->>Game: start_next_stage()
        alt 다음 스테이지가 있음
            Game->>Game: start_stage(next_stage_id)
            Game->>Stage: initialize()
            Game->>Timer: reset()
            Game->>Timer: start()
            Game->>Game: change_scene(PlayingScene)
            Game->>PlayingScene: enter(game)
            PlayingScene->>PlayingScene: draw(surface)
            PlayingScene-->>User: 다음 스테이지 게임 화면 표시
        else 마지막 스테이지임
            Note over ResultScene: 다음 스테이지 없음 안내 상태 설정
            ResultScene->>ResultScene: draw(surface)
            ResultScene-->>User: 더 이상 진행할 스테이지가 없다는 안내 표시
        end
    else 재시작 버튼 클릭
        User->>Game: restart_stage()
        Game->>Stage: initialize()
        Game->>Timer: reset()
        Game->>Timer: start()
        Game->>Game: change_scene(PlayingScene)
        Game->>PlayingScene: enter(game)
        PlayingScene->>PlayingScene: draw(surface)
        PlayingScene-->>User: 현재 스테이지 게임 화면 표시
    else 스테이지 선택 버튼 클릭
        User->>Game: open_stage_select()
        Game->>Progress: get_unlocked_stages()
        Progress-->>Game: unlocked_stages
        Game->>Game: change_scene(StageSelectScene)
        Game->>StageSelectScene: enter(game)
        StageSelectScene->>StageSelectScene: draw(surface)
        StageSelectScene-->>User: 스테이지 선택 화면 표시
    else 메인 화면 버튼 클릭
        User->>Game: return_to_main()
        Game->>Game: change_scene(MainScene)
        Game->>MainScene: enter(game)
        MainScene->>MainScene: draw(surface)
        MainScene-->>User: 메인 화면 표시
    end
```
