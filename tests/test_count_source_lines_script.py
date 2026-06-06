from pathlib import Path

from scripts.count_source_lines import count_source_lines

ROOT = Path(__file__).resolve().parents[1]


def test_count_source_lines_matches_runtime_source_guardrail_scope() -> None:
    expected = sum(
        len(path.read_text(encoding="utf-8").splitlines())
        for path in (ROOT / "kongoose").glob("*.py")
    )

    assert count_source_lines(ROOT / "kongoose") == expected
