from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
