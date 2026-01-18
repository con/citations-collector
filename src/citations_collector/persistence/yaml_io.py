"""Load and save YAML collection files."""

from __future__ import annotations

from pathlib import Path

import yaml

from citations_collector.models import Collection


def load_collection(path: Path) -> Collection:
    """
    Load collection from YAML file.

    Args:
        path: Path to YAML file

    Returns:
        Collection object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValidationError: If YAML doesn't match schema
    """
    with open(path) as f:
        data = yaml.safe_load(f)

    return Collection(**data)


def save_collection(collection: Collection, path: Path) -> None:
    """
    Save collection to YAML file.

    Args:
        collection: Collection object to save
        path: Path to output YAML file
    """
    # Convert to dict, excluding None values for cleaner output
    data = collection.model_dump(exclude_none=True, mode="python")

    with open(path, "w") as f:
        yaml.safe_dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
