# Kongoose

건국대 캠퍼스를 건구스가 건너는 Pygame 기반 격자 이동 게임 프로젝트입니다.

## 처음 받은 뒤 실행 준비

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 로컬 확인 명령

PR을 올리기 전에 아래 명령을 실행합니다.

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

`doc/` 폴더의 문서는 AI에게 프로젝트 기준을 알려주기 위한 문서입니다. 팀원이 AI에게
작업을 맡길 때는 [doc/09_ai_handoff_prompts.md](doc/09_ai_handoff_prompts.md)와 관련
작업 문서를 함께 제공합니다.
