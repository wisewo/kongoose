# AI용 GitHub 설정 지원 지침

## 문서 목적

이 문서는 팀원의 AI가 Kongoose GitHub 저장소 설정을 도울 때 읽는 지침이다.
사람이 직접 읽는 쉬운 안내서는 Notion에 둔다. AI는 이 문서를 바탕으로 팀원에게
짧고 쉬운 단계별 안내를 제공한다.

## 중요한 전제

- 저장소 이름은 `kongoose`이다.
- GitHub 저장소는 `Private`으로 만든다.
- 로컬 저장소에는 이미 기준선 커밋이 있다.
- GitHub에서 README, `.gitignore`, license를 새로 만들지 않는다.
- `main` 브랜치는 PR로만 변경되도록 보호한다.
- PR 승인 필수 인원은 1명이다.

AI는 팀원이 Git이나 GitHub에 익숙하지 않을 수 있음을 전제로 설명한다.
전문 용어를 쓰면 바로 쉬운 뜻을 붙인다.

## AI가 팀원에게 먼저 확인할 것

작업을 시작하기 전에 아래를 확인한다.

1. GitHub 계정에 로그인되어 있는가
2. private repository를 만들 권한이 있는가
3. 로컬 프로젝트 위치가 `kongoose` 폴더인가
4. 이미 GitHub에 같은 이름의 repository가 있는가
5. repository owner가 개인 계정인지 조직인지 알고 있는가

팀원이 잘 모르면 다음처럼 안내한다.

```text
GitHub에서 새 저장소를 만들 때 주소가 `https://github.com/OWNER/kongoose`처럼 보여요.
여기서 OWNER는 본인 계정 이름이나 팀 조직 이름이에요.
```

## 1단계: GitHub private repository 만들기

AI는 팀원에게 GitHub 웹사이트에서 다음 설정으로 저장소를 만들게 안내한다.

```text
Repository name: kongoose
Visibility: Private
README: 만들지 않음
.gitignore: 만들지 않음
License: 만들지 않음
```

설명할 때는 이렇게 말한다.

```text
이미 우리 컴퓨터에 README와 .gitignore가 있어서 GitHub에서 또 만들면 처음 올릴 때
충돌이 날 수 있어요. 그래서 GitHub에서는 빈 저장소로 만드는 게 좋아요.
```

## 2단계: 로컬 저장소에 remote 연결하기

저장소를 만든 뒤 GitHub가 보여주는 HTTPS 주소를 사용한다.

AI는 팀원에게 `<OWNER>`를 실제 계정 또는 조직 이름으로 바꾸라고 설명한다.

```powershell
git remote add origin https://github.com/<OWNER>/kongoose.git
git push -u origin main
```

이미 remote가 등록되어 있다는 에러가 나오면, 바로 삭제하거나 덮어쓰라고 하지 않는다.
먼저 아래 명령으로 현재 상태를 확인하게 한다.

```powershell
git remote -v
```

그 다음 팀원에게 현재 remote 주소를 보여달라고 요청한다.

## 3단계: 첫 push 확인하기

push가 끝나면 GitHub repository 페이지에서 파일이 올라갔는지 확인하게 한다.

AI는 팀원에게 아래 파일들이 보이면 정상이라고 알려준다.

- `README.md`
- `.github/workflows/ci.yml`
- `.github/pull_request_template.md`
- `doc/`
- `tests/`
- `requirements.txt`
- `pyproject.toml`

GitHub Actions 탭에서 CI가 실행되는지 확인한다. 첫 push에서는 `main`에 대한 CI가 한 번
실행될 수 있다.

## 4단계: Branch protection 설정하기

AI는 팀원에게 GitHub 웹 화면에서 아래 순서로 이동하게 안내한다.

```text
Settings -> Branches -> Add branch protection rule
```

설정값은 다음과 같다.

```text
Branch name pattern: main
Require a pull request before merging: 켜기
Required approvals: 1
Dismiss stale pull request approvals when new commits are pushed: 켜기 권장
Require status checks to pass before merging: 켜기
Require conversation resolution before merging: 켜기
Allow force pushes: 끄기
Allow deletions: 끄기
```

`Required status checks`는 CI가 한 번 실행된 뒤에 목록에 나타난다.
목록에 보이면 `Test and lint`를 선택한다.

목록에 안 보이면 이렇게 안내한다.

```text
아직 CI가 한 번도 실행되지 않아서 목록에 안 보일 수 있어요.
먼저 main push가 끝났는지 확인하고, Actions 탭에서 CI 이름이 보이는지 확인해요.
```

## 5단계: 팀원 초대하기

AI는 팀원에게 아래 메뉴로 이동하게 안내한다.

```text
Settings -> Collaborators and teams -> Add people
```

팀원 권한은 보통 `Write`면 충분하다.

권한을 쉽게 설명할 때는 이렇게 말한다.

```text
Write 권한은 코드를 올리고 PR을 만들 수 있는 권한이에요.
관리자 설정까지 바꿀 필요가 없다면 Admin 권한은 주지 않아도 돼요.
```

## 6단계: 작은 테스트 PR 만들기

설정이 잘 되었는지 확인하려면 작은 문서 수정 PR을 하나 만든다.

AI는 팀원에게 다음 흐름을 안내한다.

```powershell
git checkout -b docs/check-pr-flow
```

작은 문서 수정 후:

```powershell
git add .
git commit -m "Check PR workflow"
git push -u origin docs/check-pr-flow
```

그 다음 GitHub에서 PR을 만든다.

확인할 것은 다음과 같다.

- PR 템플릿이 자동으로 보이는가
- CI가 실행되는가
- 팀원 1명 승인이 없으면 merge가 막히는가
- 승인 후 merge가 가능한가

## 에러가 났을 때 AI가 지킬 원칙

에러가 나면 바로 위험한 명령을 제안하지 않는다.

먼저 아래 정보를 확인한다.

```powershell
git status
git branch --show-current
git remote -v
git log --oneline -3
```

AI는 `git reset --hard`, `git push --force`, remote 삭제 같은 명령을 쉽게 제안하지 않는다.
필요하다면 왜 위험한지 먼저 설명하고 팀장에게 확인하도록 한다.

## 팀원에게 줄 수 있는 짧은 안내 문장

AI는 상황에 따라 아래 문장을 그대로 사용해도 된다.

```text
지금 하는 일은 GitHub에 우리 프로젝트 공간을 만들고, main 브랜치를 안전하게 보호하는
작업이에요. 처음 한 번만 해두면 이후에는 팀원들이 PR로 작업을 올리면 됩니다.
```

```text
PR 승인을 1명으로 둔 이유는 속도를 너무 늦추지 않으면서도, AI가 만든 코드를 아무 확인
없이 합치는 일을 막기 위해서예요.
```

```text
CI는 GitHub가 자동으로 테스트와 코드 검사를 돌리는 장치예요. 초록불이면 기본 검사를
통과했다는 뜻이고, 빨간불이면 로그를 보고 고치면 됩니다.
```

## 완료 기준

AI는 GitHub 설정 지원이 끝나면 팀원에게 아래 결과를 확인하게 한다.

1. private `kongoose` repository가 만들어졌다.
2. 로컬 `main` 브랜치가 GitHub에 push되었다.
3. GitHub Actions CI가 보인다.
4. `main` branch protection이 설정되었다.
5. PR에는 팀원 1명 승인이 필요하다.
6. force push와 branch deletion이 꺼져 있다.
