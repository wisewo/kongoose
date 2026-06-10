# System Sequence Diagrams

## Notes

- SSD는 Actor와 `Game System` 사이의 시스템 오퍼레이션 흐름만 표현한다.
- Actor에서 `Game System`으로 향하는 메시지는 시스템 오퍼레이션 이름을 기준으로 표기한다.
- 각 화면은 키 입력을 받은 뒤 대응되는 시스템 오퍼레이션을 요청한다. SSD에서는 이 내부 라우팅을 추상화한다.
- 시스템 오퍼레이션 이름은 `STYLE-01`에 따라 PEP 8의 snake_case를 따른다.
- 시스템 내부 처리는 메서드 호출처럼 표시하지 않고 `Note over System`으로 표현한다.
- 시스템이 플레이어에게 제공하는 화면, 메시지, 사운드, 이펙트는 `System-->>Player`로 표현한다.
- 게임 루프의 시간 흐름은 외부 Actor로 두지 않고, UC-05의 내부 반복 흐름으로 다룬다.
- Use Case와 SSD는 Traceability를 위해 1:1로 대응한다.

## System Operations

| Operation | Trigger | Related Use Case |
|---|---|---|
| `start_game()` | 게임이 메인 화면으로 진입함 | UC-01 |
| `return_to_main()` | 스테이지 선택 화면의 Esc/B, 실패/결과 화면의 M/Esc 입력 | UC-01, UC-06, UC-07 |
| `open_stage_select()` | 메인 화면의 Enter/Space, 게임 진행 화면의 Esc/B, 실패/결과 화면의 S/B 입력 | UC-02, UC-06, UC-07 |
| `quit_game()` | 메인 화면의 Esc/Q 입력 | UC-03 |
| `select_stage(stage_id)` | 스테이지 선택 화면의 숫자 1~4 입력 | UC-04 |
| `move_player(direction)` | 게임 화면의 방향키 입력 | UC-05 |
| `restart_stage()` | 실패/결과 화면의 R 입력 | UC-06, UC-07 |
| `start_next_stage()` | 결과 화면의 N 입력 | UC-07 |

## SSD-01 / UC-01 메인 화면 진입

```mermaid
sequenceDiagram
    actor Player
    participant System as Game System

    alt 게임 프로그램 실행 또는 start_game 호출
        Player->>System: start_game()
        Note over System: 저장된 진행 상태는 Game 생성 시 SaveManager.load_progress()로 준비됨
    else 다른 화면에서 메인 화면 이동 키 입력
        Player->>System: return_to_main()
        Note over System: 스테이지 환경음을 정지하고 UI 선택음을 재생
    end

    System-->>Player: 메인 화면 표시
    System-->>Player: 해금된 스테이지 수와 Enter/Space, Esc/Q 안내 표시
```

## SSD-02 / UC-02 스테이지 선택 화면 진입

```mermaid
sequenceDiagram
    actor Player
    participant System as Game System

    alt 메인 화면에서 Enter/Space 입력
        Player->>System: open_stage_select()
    else 게임 진행 화면에서 Esc/B 입력
        Player->>System: open_stage_select()
    else 실패 또는 결과 화면에서 S/B 입력
        Player->>System: open_stage_select()
    end

    Note over System: 스테이지 환경음을 정지하고 UI 선택음을 재생
    Note over System: 1~4번 스테이지의 해금 상태와 최고 별점 조회
    System-->>Player: 스테이지 선택 화면 표시
    System-->>Player: 숫자키 선택과 Esc/B 메인 이동 안내 표시
```

## SSD-03 / UC-03 게임 종료

```mermaid
sequenceDiagram
    actor Player
    participant System as Game System

    Player->>System: quit_game()
    Note over System: running 플래그를 False로 변경
    System-->>Player: 게임 루프 종료 후 Pygame 종료
```

## SSD-04 / UC-04 스테이지 선택

```mermaid
sequenceDiagram
    actor Player
    participant System as Game System

    Player->>System: select_stage(stage_id)

    alt 선택한 스테이지가 해금됨
        Note over System: UI 선택음 재생
        Note over System: 선택한 스테이지 초기화, 타이머 재시작, 게임 화면 전환
        Note over System: Stage 2/3/4는 필요한 환경음을 반복 재생
        System-->>Player: 게임 화면 표시
        System-->>Player: 캐릭터, 지형, 장애물, 발판, HUD 표시
    else 선택한 스테이지가 잠김
        Note over System: 현재 StageSelectScene에 잠김 메시지 상태 설정
        System-->>Player: 스테이지 선택 화면 유지
    end
```

## SSD-05 / UC-05 캐릭터 이동

```mermaid
sequenceDiagram
    actor Player
    participant System as Game System

    Player->>System: move_player(direction)
    Note over System: 이동 대상 위치와 정적 진입 가능 여부 판단

    alt MOVE_BLOCKED
        Note over System: 플레이어 위치 유지, 막힌 방향 홉 애니메이션 준비
        System-->>Player: 막힘음과 현재 게임 화면 갱신
    else MOVE_MOVED
        Note over System: 플레이어를 한 칸 이동하고 자전거, 학생 무리, 강, 자라 탑승 판정
        System-->>Player: 이동 시작음 또는 자라 탑승음 재생
        System-->>Player: 홉 애니메이션 완료 후 이동 성공음 재생
        System-->>Player: 변경된 게임 화면과 HUD 표시
    else MOVE_CLEARED
        Note over System: 타이머 정지, 클리어 시간과 별점 계산
        Note over System: 최고 별점과 다음 스테이지 해금 상태 갱신 및 저장
        System-->>Player: 클리어 화면과 별점 표시
    else MOVE_FAILED
        Note over System: 실패 원인 저장, 환경음 정지, 실패 화면 전환
        System-->>Player: 원인별 효과음과 실패 화면 표시
    end

    loop 게임 진행 화면 유지 중
        Note over System: Stage.update(dt)로 자전거, 자라, 학생 무리 갱신
        alt UPDATE_FAILED
            System-->>Player: 원인별 효과음과 실패 화면 표시
        else UPDATE_WARNING
            System-->>Player: 학생 무리 시각 경고와 게임 화면 표시
        else UPDATE_STUDENT_CROWD_ACTIVE
            System-->>Player: 학생 무리 등장음과 게임 화면 표시
        else UPDATE_TURTLE_RIDE or UPDATE_SAFE
            System-->>Player: 갱신된 게임 화면과 HUD 표시
        end
    end
```

## SSD-06 / UC-06 실패 후 행동 선택

```mermaid
sequenceDiagram
    actor Player
    participant System as Game System

    System-->>Player: 실패 화면 표시

    alt R 입력
        Player->>System: restart_stage()
        Note over System: 현재 스테이지 초기화, 타이머 재시작, 게임 화면 전환
        System-->>Player: 게임 화면 표시
    else S/B 입력
        Player->>System: open_stage_select()
        System-->>Player: 스테이지 선택 화면 표시
    else M/Esc 입력
        Player->>System: return_to_main()
        System-->>Player: 메인 화면 표시
    end
```

## SSD-07 / UC-07 클리어 후 행동 선택

```mermaid
sequenceDiagram
    actor Player
    participant System as Game System

    System-->>Player: 스테이지 클리어 화면 표시
    System-->>Player: 클리어 시간, 별점, N/R/S/B/M/Esc 안내 표시

    alt N 입력
        Player->>System: start_next_stage()
        alt 다음 스테이지가 있음
            Note over System: 다음 스테이지 초기화, 타이머 재시작, 게임 화면 전환
            System-->>Player: 다음 스테이지 게임 화면 표시
        else 마지막 스테이지임
            Note over System: 다음 스테이지 없음 메시지 상태 설정
            System-->>Player: 결과 화면 유지
        end
    else R 입력
        Player->>System: restart_stage()
        Note over System: 현재 스테이지 초기화, 타이머 재시작, 게임 화면 전환
        System-->>Player: 현재 스테이지 게임 화면 표시
    else S/B 입력
        Player->>System: open_stage_select()
        System-->>Player: 스테이지 선택 화면 표시
    else M/Esc 입력
        Player->>System: return_to_main()
        System-->>Player: 메인 화면 표시
    end
```
