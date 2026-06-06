from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SOURCE_DIR = ROOT / "kongoose"


def test_runtime_source_line_count_stays_within_guardrail() -> None:
    line_count = sum(
        len(path.read_text(encoding="utf-8").splitlines())
        for path in RUNTIME_SOURCE_DIR.glob("*.py")
    )

    assert 500 <= line_count <= 1500
