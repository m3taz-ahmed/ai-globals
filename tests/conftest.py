import shutil
import tempfile
from pathlib import Path

import pytest

from memory.store import MemoryStore
from runtime.kernel import Kernel


@pytest.fixture
def tmp_root():
    path = Path(tempfile.mkdtemp(prefix="aios_test_"))
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def kernel(tmp_root):
    # Copy minimal structure for tests
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_root / sub).mkdir(parents=True, exist_ok=True)
    (tmp_root / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
        "  - name: deny-destructive\n    condition: \"'rm -rf' in command\"\n    action: deny\n"
    )
    (tmp_root / "workflows/test.md").write_text(
        "[WORKFLOW] test\n[OBJ] Test workflow for unit tests.\n[RULES]\n1. [REQ] Step one.\n2. [CMD] Step two.\n"
    )
    return Kernel(tmp_root)


@pytest.fixture
def store(tmp_root):
    return MemoryStore(tmp_root, db_path=tmp_root / "brain" / "memory.db", enable_vector=False)
