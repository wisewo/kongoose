# Kongoose

건국대 캠퍼스를 건구스가 건너는 Pygame 기반 격자 이동 게임 프로젝트입니다.

## 처음 받은 뒤 실행 준비

처음 GitHub 에서 코드를 다운 받으면 아래 명령어를 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 로컬 확인 명령

PR을 올리기 전에 프로젝트 폴더에서 아래 명령을 실행합니다.

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

게임 실행 명령은 구현 골격이 만들어진 뒤 아래 명령을 기준으로 맞춥니다.

```powershell
python -m kongoose
```

## 작업 방식

사람이 읽는 쉬운 작업 안내서는 Notion에 정리합니다.

`doc/` 폴더의 문서는 AI에게 프로젝트 기준을 알려주기 위한 문서입니다. 팀원이 직접 읽는
작업 안내, AI에게 붙여넣을 프롬프트, GitHub 설정 따라하기 문서는 Notion에 정리합니다.
