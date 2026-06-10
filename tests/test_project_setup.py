from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_source_folder_is_named_src() -> None:
    assert (ROOT / "src").is_dir()
    assert not (ROOT / "kongoose").exists()


def test_game_and_player_names_use_canonical_terms() -> None:
    runtime_text = (ROOT / "src" / "game.py").read_text(encoding="utf-8")
    scene_text = (ROOT / "src" / "scenes.py").read_text(encoding="utf-8")
    project_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "README.md",
            ROOT / "AGENTS.md",
            ROOT / "doc" / "01_use_cases.md",
            ROOT / "doc" / "02_requirements.md",
            ROOT / "doc" / "03_domain_model.md",
        )
    )

    assert 'title="길Kon너 Goose들"' in runtime_text
    assert '"길Kon너 Goose들"' in scene_text
    assert "kongoose(건구스)" in project_text
    assert "Geon-goose" not in project_text
    assert "geon goose" not in project_text.lower()


def test_required_team_documents_exist() -> None:
    required_paths = [
        ROOT / "doc" / "02_requirements.md",
        ROOT / "doc" / "06_class_diagram.md",
        ROOT / "doc" / "05_sequence_diagrams.md",
        ROOT / "doc" / "07_stage_balance.md",
        ROOT / "doc" / "09_team_workflow.md",
        ROOT / "doc" / "10_github_setup_checklist.md",
    ]

    missing_paths = [path for path in required_paths if not path.exists()]

    assert missing_paths == []
