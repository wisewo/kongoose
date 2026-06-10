from argparse import ArgumentParser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "src"


def iter_source_files(source_dir: Path):
    return sorted(source_dir.glob("*.py"))


def count_source_lines(source_dir: Path = DEFAULT_SOURCE_DIR) -> int:
    return sum(
        len(path.read_text(encoding="utf-8").splitlines())
        for path in iter_source_files(source_dir)
    )


def main() -> None:
    parser = ArgumentParser(description="Count runtime source lines in src/*.py.")
    parser.add_argument(
        "source_dir",
        nargs="?",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Directory containing Python source files to count.",
    )
    args = parser.parse_args()
    print(count_source_lines(args.source_dir))


if __name__ == "__main__":
    main()
