"""aiZee memory service."""

from __future__ import annotations

import config

__version__ = config.VERSION

# Re-export new memory modules for convenient access.
from memory.checkpoint import Checkpoint as Checkpoint
from memory.checkpoint import SqliteCheckpointSaver as SqliteCheckpointSaver
from memory.schema_contract import SchemaContract as SchemaContract

__all__ = [
    "Checkpoint",
    "SchemaContract",
    "SqliteCheckpointSaver",
]
