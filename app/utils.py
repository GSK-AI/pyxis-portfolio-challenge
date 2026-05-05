from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def inside_ci() -> bool:
    """Whether the code is running inside a CI environment."""
    return os.getenv("REPO_NAME") is not None


def use_local_storage() -> bool:
    """Whether to use local storage or blob storage."""
    return inside_ci() or bool(int(os.environ.get("LOCAL_STORAGE", "0")))
