# AI용 팀 작업 규칙

## 문서 목적

이 문서는 AI 도구가 Kongoose 프로젝트 작업을 도울 때 지켜야 할 팀 운영 규칙이다.
사람이 처음 읽는 쉬운 안내서는 Notion에 따로 둔다. `doc/` 폴더의 문서는 기본적으로
AI가 프로젝트 맥락을 읽고 일관된 작업을 하기 위한 기준 문서로 사용한다.

AI는 이 문서를 읽고 팀원에게 답할 때, 규칙을 그대로 나열하기보다 팀원이 지금 해야 할
다음 행동을 쉽게 설명해야 한다.

## 팀원 전제

- 팀은 5인 팀이다.
- 팀원 대부분은 컴퓨터공학 전공자가 아닌 2학년 공대생이다.
- 팀원은 AI를 사용하지만, AI Agent나 자동화 도구를 쓴다는 보장은 없다.
- Git, Pull Request, CI, pytest, ruff를 처음 볼 수 있다.

따라서 AI는 답변할 때 다음 원칙을 따른다.

1. 어려운 용어는 짧게 풀어서 설명한다.
2. 명령어는 복사해서 실행할 수 있게 코드 블록으로 준다.
3. 한 번에 너무 많은 선택지를 주지 않는다.
4. 위험한 Git 명령은 실행 전에 경고한다.
5. 팀원이 직접 확인해야 하는 부분을 체크리스트로 남긴다.

## 저장소 운영 규칙

`main` 브랜치는 항상 실행 가능한 기준선으로 유지한다.

모든 구현 작업은 별도 브랜치에서 진행하고 Pull Request(PR)로 `main`에 합친다. `main`에
직접 push하지 않는다.

PR 병합 조건은 다음과 같다.

- GitHub Actions CI 통과
- 팀원 1명 이상 승인
- 작성자가 자기 PR을 승인하지 않음
- 리뷰 대화가 남아 있으면 해결 후 병합

GitHub branch protection도 위 조건에 맞춰 설정한다. 필수 승인 수는 1명으로 통일한다.

## AI가 작업할 때 지킬 범위

AI는 사용자가 맡긴 작업 패키지의 범위를 넘지 않는다.

예를 들어 `B: 지형과 플레이어 이동` 작업을 맡았다면 Scene UI, 사운드, 저장 기능까지
임의로 구현하지 않는다. 필요한 인터페이스가 있다면 "가정"으로 적고, 실제 구현은 담당
범위에 남긴다.

작업 전에 우선순위로 읽어야 하는 문서는 다음과 같다.

1. `doc/02_requirements.md`
2. `doc/06_class_diagram.md`
3. `doc/05_sequence_diagrams.md`
4. `doc/07_stage_balance.md`
5. `doc/08_implementation_dashboard.md`
6. `doc/09_team_workflow.md`

GitHub 저장소 연결이나 PR 설정을 돕는 경우에는 `doc/10_github_setup_checklist.md`도 읽는다.

## 테스트와 검증 규칙

화면 없이 결과를 확인할 수 있는 로직은 단위 테스트를 작성한다.

테스트를 작성해야 하는 대표 대상은 다음과 같다.

- `Position`, `Direction`의 이동 계산
- `TerrainMap.can_enter()`와 지형 조회
- `Stage.move_player()`의 벽, 범위, 목적지, 실패 결과
- `Stage.evaluate_player_state()`의 충돌, 강 추락, 자라 탑승 판정
- `Progress`의 스테이지 해금과 최고 별점 갱신
- `SaveManager`의 저장과 불러오기
- `StarRating`의 시간별 별점 계산

Pygame 창, 화면 전환, 키보드 조작감, 사운드, 난이도 체감은 수동 검증으로 대체할 수 있다.
수동 검증으로 대체했다면 무엇을 직접 확인했는지 PR 설명에 적게 한다.

## 로컬 검증 명령

AI가 코드 변경을 도왔고 프로젝트 구조상 실행 가능하다면 아래 명령을 안내한다.

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

가상환경을 쓰는 경우에는 Windows 기준으로 아래 명령을 안내할 수 있다.

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
```

검증 명령이 실패하면 실패 로그를 숨기지 말고, 원인을 짧게 설명한 뒤 다음 확인 단계를
제시한다.

## PR 설명 형식

AI는 팀원이 PR을 만들 때 아래 형식을 채우도록 도와야 한다.

```text
## 작업 내용
-

## 읽은 문서
- [ ] doc/02_requirements.md
- [ ] doc/06_class_diagram.md
- [ ] doc/05_sequence_diagrams.md
- [ ] doc/07_stage_balance.md
- [ ] doc/09_team_workflow.md

## 테스트
- [ ] python -m pytest
- [ ] python -m ruff check .
- [ ] python -m ruff format --check .

## 수동 확인
-

## 남은 문제
-
```

팀원이 테스트를 실행하지 못했거나 이해하지 못한 부분이 있다면 빈칸으로 두지 말고
"아직 못 함", "이유를 모르겠음", "팀장에게 확인 필요"처럼 현재 상태를 적게 한다.

## 팀원에게 설명할 때의 말투

AI는 팀원에게 아래처럼 설명한다.

- "이 명령은 새 작업 공간을 만드는 명령이에요."
- "이 파일은 PR을 올릴 때 자동으로 보이는 양식이에요."
- "테스트가 실패했으니 바로 고치기보다 에러 메시지의 첫 줄을 먼저 봐야 해요."

AI는 아래처럼 말하지 않는다.

- "그냥 CI 깨진 거 고치면 됩니다."
- "브랜치 보호 설정에서 required status check를 enable 하세요."
- "pytest fixture를 mock으로 구성하면 됩니다."

전문 용어가 필요하면 쉬운 뜻을 바로 붙인다.

## 사람용 문서의 위치

팀원이 직접 읽는 안내서는 Notion에 둔다. 여기에는 다음 내용을 포함한다.

- 처음 작업을 시작하는 방법
- AI에게 붙여넣을 작업 프롬프트
- PR 작성 방법
- GitHub 저장소 설정 따라하기
- 자주 막히는 상황별 질문 예시

AI는 `doc/` 폴더 문서를 사람에게 그대로 읽으라고 하지 않는다. 대신 `doc/`의 기준을
바탕으로 필요한 부분을 쉬운 말로 요약하거나, 사람이 읽어야 하는 내용은 Notion 문서를
보라고 안내한다.
