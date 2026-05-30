# System Sequence Diagrams

## Notes

- SSD는 Actor와 `Game System` 사이의 시스템 오퍼레이션 흐름만 표현한다.
- Actor에서 `Game System`으로 향하는 메시지는 반드시 메서드 형태의 시스템 오퍼레이션으로 표기한다.
- 시스템 오퍼레이션 이름은 `STYLE-01`에 따라 PEP 8의 snake_case를 따른다.
- 시스템 내부 처리는 메서드 호출처럼 표시하지 않고 `Note over System`으로 표현한다.
- 시스템이 플레이어에게 제공하는 화면, 메시지, 사운드, 이펙트는 `System-->>Player`로 표현한다.
- 게임 루프의 시간 흐름은 외부 Actor로 두지 않고, 내부 Sequence Diagram에서 반복 흐름으로 다룬다.
- Use Case와 SSD는 Traceability를 위해 1:1로 대응한다.

## System Operations

| Operation | Trigger | Related Use Case |
|---|---|---|
| `start_game()` | 플레이어가 게임 프로그램을 실행함 | UC-01 |
| `return_to_main()` | 플레이어가 다른 화면에서 메인 화면 이동을 선택함 | UC-01, UC-06, UC-07 |
| `open_stage_select()` | 플레이어가 메인 화면의 게임 시작 버튼, 실패 화면 또는 클리어 화면의 스테이지 선택 버튼을 클릭함 | UC-02, UC-06, UC-07 |
| `quit_game()` | 플레이어가 메인 화면에서 게임 종료를 클릭함 | UC-03 |
| `select_stage(stage_id)` | 플레이어가 스테이지 선택 화면에서 특정 스테이지를 클릭함 | UC-04 |
| `move_player(direction)` | 플레이어가 게임 화면에서 방향키를 입력함 | UC-05 |
| `restart_stage()` | 플레이어가 실패 화면 또는 클리어 화면에서 재시작을 클릭함 | UC-06, UC-07 |
| `start_next_stage()` | 플레이어가 클리어 화면에서 다음 스테이지를 클릭함 | UC-07 |

## SSD-01 / UC-01 메인 화면 진입

```mermaid
sequenceDiagram
    actor Player
    participant System as Game System

    alt 게임 프로그램 실행
        Player->>System: start_game()
        Note over System: 저장된 스테이지 해금 상태와 최고 별점 불러오기
    else 다른 화면에서 메인 화면 이동 선택
        Player->>System: return_to_main()
        Note over System: 현재 진행 상태 유지
    end

    System-->>Player: 메인 화면 표시
    System-->>Player: 저장된 진행 상태와 선택 가능한 행동 표시
```

## SSD-02 / UC-02 스테이지 선택 화면 진입

```mermaid
sequenceDiagram
    actor Player
    participant System as Game System

    alt 메인 화면에서 게임 시작 버튼 클릭
        Player->>System: open_stage_select()
    else 실패 화면에서 스테이지 선택 버튼 클릭
        Player->>System: open_stage_select()
    else 스테이지 클리어 화면에서 스테이지 선택 버튼 클릭
        Player->>System: open_stage_select()
    end

    Note over System: 스테이지 목록과 해금 상태 확인
    System-->>Player: 스테이지 선택 화면 표시
    System-->>Player: 해금된 스테이지와 잠긴 스테이지 표시
```

## SSD-03 / UC-03 게임 종료

```mermaid
sequenceDiagram
    actor Player
    participant System as Game System

    Player->>System: quit_game()
    Note over System: 게임 루프 종료 준비
    System-->>Player: 프로그램 종료
```

## SSD-04 / UC-04 스테이지 선택

```mermaid
sequenceDiagram
    actor Player
    participant System as Game System

    Player->>System: select_stage(stage_id)

    alt 선택한 스테이지가 해금됨
        Note over System: 선택한 스테이지 초기화
        System-->>Player: 게임 화면 표시
        System-->>Player: 캐릭터, 지형, 장애물, 발판, 상태 정보 표시
    else 선택한 스테이지가 잠김
        Note over System: 스테이지 시작 거부
        System-->>Player: 잠긴 스테이지 안내 표시
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

    alt 이동 불가능한 위치
        Note over System: 플레이어 위치 유지
        System-->>Player: 현재 게임 화면 갱신
    else 이동 가능한 위치
        Note over System: 플레이어를 한 칸 이동
        Note over System: 같은 판정 규칙으로 장애물, 발판, 호수, 목적지 판정

        alt 목적지 도착
            Note over System: 클리어 시간과 별점 계산
            Note over System: 최고 별점과 다음 스테이지 해금 상태 갱신 및 저장
            System-->>Player: 스테이지 클리어 화면 표시
            System-->>Player: 클리어 시간과 별점 표시
        else 실패 조건 발생
            System-->>Player: 실패 원인에 맞는 이펙트 또는 사운드 제공
            Note over System: 실패 상태로 전환
            System-->>Player: 실패 화면 표시
        else 경고 또는 특수 상호작용 발생
            System-->>Player: 경고, 자라 탑승, 상태 정보, 사운드 반영
            System-->>Player: 변경된 게임 화면 표시
        else 일반 이동
            System-->>Player: 이동 사운드 재생
            System-->>Player: 변경된 게임 화면과 상태 정보 표시
        end
    end
```

## SSD-06 / UC-06 실패 후 행동 선택

```mermaid
sequenceDiagram
    actor Player
    participant System as Game System

    System-->>Player: 실패 화면 표시

    alt 재시작 버튼 클릭
        Player->>System: restart_stage()
        Note over System: 현재 스테이지 초기화
        System-->>Player: 게임 화면 표시
    else 스테이지 선택 버튼 클릭
        Player->>System: open_stage_select()
        Note over System: 스테이지 목록과 해금 상태 확인
        System-->>Player: 스테이지 선택 화면 표시
    else 메인 화면 버튼 클릭
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
    System-->>Player: 클리어 시간, 별점, 다음 행동 표시

    alt 다음 스테이지 버튼 클릭
        Player->>System: start_next_stage()
        alt 다음 스테이지가 있음
            Note over System: 다음 스테이지 초기화
            System-->>Player: 게임 화면 표시
            System-->>Player: 캐릭터, 지형, 장애물, 발판, 상태 정보 표시
        else 마지막 스테이지임
            Note over System: 추가로 시작할 스테이지 없음
            System-->>Player: 더 이상 진행할 스테이지가 없다는 안내 표시
            System-->>Player: 스테이지 클리어 화면 유지
        end
    else 재시작 버튼 클릭
        Player->>System: restart_stage()
        Note over System: 현재 스테이지 초기화
        System-->>Player: 게임 화면 표시
    else 스테이지 선택 버튼 클릭
        Player->>System: open_stage_select()
        Note over System: 스테이지 목록과 해금 상태 확인
        System-->>Player: 스테이지 선택 화면 표시
    else 메인 화면 버튼 클릭
        Player->>System: return_to_main()
        System-->>Player: 메인 화면 표시
    end
```
