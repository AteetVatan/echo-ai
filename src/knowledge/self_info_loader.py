"""
Loader for self_info.json.

Reads a JSON array, validates each element against SelfInfoItem,
and returns a strongly-typed list.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from src.knowledge.self_info_schema import SelfInfoItem
from src.utils import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


def load_self_info_items(path: Path | str) -> list[SelfInfoItem]:
    """Load and validate all self-info records from *path*.

    Parameters
    ----------
    path:
        Filesystem path to ``self_info.json``.

    Returns
    -------
    list[SelfInfoItem]
        Validated items.  Items that fail validation are logged and skipped.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If *path* does not contain a JSON array or if zero valid items remain.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"self_info.json not found at {path}")

    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {path}, got {type(data).__name__}")

    items: list[SelfInfoItem] = []
    skipped = 0
    for idx, entry in enumerate(data):
        try:
            items.append(SelfInfoItem.model_validate(entry))
        except (ValidationError, Exception) as exc:  # noqa: BLE001
            logger.warning("Skipping item %d in %s: %s", idx, path.name, exc)
            skipped += 1

    if not items:
        raise ValueError(f"No valid items found in {path} ({skipped} skipped)")

    logger.info(
        "Loaded %d self-info items from %s (%d skipped)", len(items), path.name, skipped
    )
    return items
