"""P1.1: APL verdicts - modify (payload rewrite) + observe (log-only)."""
from __future__ import annotations

from pathlib import Path

from runtime.kernel import Kernel

_POLICY = """\
default_action: allow
rules:
  - name: modify-model
    condition: "type == 'chat' and model == 'expensive'"
    action: modify
    set: {model: "cheap"}
  - name: observe-prod
    condition: "type == 'deploy' and env == 'prod'"
    action: observe
"""


def _kernel(tmp_path: Path) -> Kernel:
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(_POLICY)
    return Kernel(tmp_path)


def test_modify_verdict_rewrites_payload(tmp_path):
    k = _kernel(tmp_path)
    r = k.act("chat", model="expensive")
    assert r["ok"]
    # Decision carries the rewrite; audit trail got policy.modify.
    log = (tmp_path / "state" / "audit.log").read_text(encoding="utf-8")
    assert "policy.modify" in log and "modify-model" in log


def test_observe_verdict_allows_and_audits(tmp_path):
    k = _kernel(tmp_path)
    r = k.act("deploy", env="prod", approved=True)
    assert r["ok"]
    log = (tmp_path / "state" / "audit.log").read_text(encoding="utf-8")
    assert "policy.observe" in log and "observe-prod" in log


def test_modify_rule_exposes_modifications(tmp_path):
    k = _kernel(tmp_path)
    d = k.policy.can("chat", model="expensive")
    assert d["decision"] == "modify"
    assert d["modifications"] == {"model": "cheap"}


def test_observe_rule_decision(tmp_path):
    k = _kernel(tmp_path)
    d = k.policy.can("deploy", env="prod")
    assert d["decision"] == "observe"
    assert d["requires_approval"] is False
