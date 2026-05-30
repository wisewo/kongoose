# GitHub 저장소 설정 체크리스트

## 목적

이 문서는 로컬 기준선 커밋 이후 GitHub에서 직접 해야 하는 일을 순서대로 적은
체크리스트다. 저장소는 `kongoose` 이름의 private repository로 만든다.

## 1. GitHub 저장소 만들기

GitHub 웹사이트에서 새 repository를 만든다.

- Repository name: `kongoose`
- Visibility: `Private`
- README, `.gitignore`, license는 만들지 않는다.

이미 로컬에 파일이 있으므로 GitHub에서 README나 `.gitignore`를 만들면 첫 push 때
충돌이 생길 수 있다.

## 2. 로컬 저장소에 remote 연결하기

GitHub가 보여주는 repository 주소를 복사한 뒤 아래 명령을 실행한다.

```powershell
git remote add origin https://github.com/<OWNER>/kongoose.git
git push -u origin main
```

`<OWNER>` 부분은 본인 GitHub 계정 또는 조직 이름으로 바꾼다.

## 3. Branch protection 설정하기

GitHub repository 화면에서 아래 순서로 이동한다.

```text
Settings -> Branches -> Add branch protection rule
```

설정값은 다음처럼 둔다.

- Branch name pattern: `main`
- Require a pull request before merging: 켜기
- Required approvals: `1`
- Dismiss stale pull request approvals when new commits are pushed: 켜기 권장
- Require status checks to pass before merging: 켜기
- Required status checks: CI가 한 번 실행된 뒤 `Test and lint` 선택
- Require conversation resolution before merging: 켜기
- Do not allow bypassing the above settings: 가능하면 켜기
- Restrict who can push to matching branches: 팀 상황에 따라 선택
- Allow force pushes: 끄기
- Allow deletions: 끄기

## 4. 팀원 초대하기

```text
Settings -> Collaborators and teams -> Add people
```

팀원은 보통 `Write` 권한이면 충분하다.

## 5. 확인하기

설정 후에는 작은 테스트 PR을 하나 만들어서 아래 흐름이 동작하는지 확인한다.

1. 새 브랜치에서 작은 문서 수정
2. PR 생성
3. CI 실행 확인
4. 팀원 1명 승인
5. merge 가능 여부 확인
