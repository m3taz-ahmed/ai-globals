import json
import os
import tempfile
from pathlib import Path

os.environ["AGENT_OS_ROOT"] = tempfile.mkdtemp(prefix="aios_mcp_test_")
ROOT = Path(os.environ["AGENT_OS_ROOT"])
for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)
(ROOT / "runtime/policies/default.yaml").write_text(
    "default_action: ask\nrules:\n"
    "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
)
(ROOT / "workflows/test.md").write_text(
    "[WORKFLOW] test\n[RULES]\n1. [REQ] Step one.\n"
)

from aios_mcp.aios_server import mcp  # noqa: E402


def _call(name, arguments):
    return mcp._tool_manager.get_tool(name).fn(**arguments)


def test_tools_list():
    tools = mcp._tool_manager._tools.values()
    names = {t.name for t in tools}
    assert "check_policy" in names
    assert "search_memory" in names
    assert "search_memory_vector" in names


def test_check_policy():
    result = _call("check_policy", {"action": "Read"})
    data = json.loads(result)
    assert data["ok"]


def test_get_tech_stack_missing():
    result = _call("get_tech_stack", {"pkg": "foo", "ver": "1.0"})
    data = json.loads(result)
    assert data["exists"] is False
