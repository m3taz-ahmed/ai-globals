"""Isolation for tests/mcp.

Every module in this package assigns ``os.environ["AIZEE_ROOT"]`` at import
time (before the tools-under-test are imported) and several also mutate it
inside test bodies. Without restoration, that mutation leaks into the rest
of the suite and makes unrelated tests (e.g. persona detection, which calls
``config.discover_root()``) dependent on collection order.

The original value is captured at conftest import - which pytest performs
before importing any test module in this package - and restored after every
test. MCP tests that need their own root re-set it via their ``_call``
helpers or explicit assignments, so this fixture only affects what leaks
out of this package.
"""

from __future__ import annotations

import os

import pytest

_ORIGINAL_AIZEE_ROOT = os.environ.get("AIZEE_ROOT")


@pytest.fixture(autouse=True)
def _restore_aizee_root():
    """Restore the pre-collection AIZEE_ROOT after every test in this package."""
    yield
    if _ORIGINAL_AIZEE_ROOT is None:
        os.environ.pop("AIZEE_ROOT", None)
    else:
        os.environ["AIZEE_ROOT"] = _ORIGINAL_AIZEE_ROOT
