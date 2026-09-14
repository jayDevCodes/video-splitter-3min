from pathlib import Path

READY_FILE = "READY"


def mark_ready(output_dir: Path) -> None:
    (output_dir / READY_FILE).touch()


def is_ready(output_dir: Path) -> bool:
    return (output_dir / READY_FILE).exists()
