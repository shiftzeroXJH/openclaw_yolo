from __future__ import annotations

from pathlib import Path

YAML_NAMES = ("data.yaml", "dataset.yaml", "detect.yaml")


def inspect_dataset(dataset_root: str) -> list[str]:
    root = Path(dataset_root)
    if not root.exists():
        raise FileNotFoundError(f"dataset root not found: {dataset_root}")

    candidates: list[str] = []
    for yaml_name in YAML_NAMES:
        candidates.extend(str(path.resolve()) for path in root.rglob(yaml_name))
    return sorted(set(candidates))
