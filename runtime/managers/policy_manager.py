#!/usr/bin/env python3
"""Policy, guardian, and approval management for the kernel."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, ClassVar

from runtime.approval_cache import ApprovalCache
from runtime.approval_service import ApprovalService
from runtime.audit import AuditLogger
from runtime.budget import BudgetManager
from runtime.enums import ActionResultStatus, Decision
from runtime.guardian import ActionRequest, DecisionStatus, GuardConfig, Guardian
from runtime.metrics import Counter
from runtime.policy import READ_ACTIONS, PolicyEngine
from runtime.preloop import FeedbackLoop, Outcome
from runtime.probity import Guardrails

_logger = logging.getLogger(__name__)


class PolicyManager:
    """Encapsulates policy evaluation, guardian checks, approval caching, and probity."""

    def __init__(
        self,
        root: Path,
        project_root: Path,
        audit: AuditLogger,
        budget: BudgetManager,
        approval_cache: ApprovalCache,
        preloop: FeedbackLoop,
        actions_total: Counter,
        guardian_denials_total: Counter,
        probity_violations_total: Counter,
        approval_service: ApprovalService | None = None,
    ) -> None:
        self.root = root
        self.project_root = project_root
        self.audit = audit
        self.budget = budget
        self.approval_cache = approval_cache
        self.approval_service = approval_service
        self.preloop = preloop
        self._actions_total = actions_total
        self._guardian_denials_total = guardian_denials_total
        self._probity_violations_total = probity_violations_total
        self.policy = PolicyEngine(root, project_root)
        self.guardian = self._build_guardian()
        self.probity = self._build_probity()

    def _build_guardian(self) -> Guardian:
        import yaml

        rules: list[dict[str, Any]] = []
        roots = [self.root]
        if self.project_root and self.project_root != self.root:
            roots.append(self.project_root)
        for root in roots:
            path = root / "runtime" / "policies" / "guardian.yaml"
            if path.exists():
                try:
                    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                    loaded = data.get("rules", [])
                    if isinstance(loaded, list):
                        rules.extend(loaded)
                    else:
                        _logger.error("Guardian config %s: 'rules' is not a list — ignored", path)
                except Exception as exc:
                    # Fail closed: a corrupted guardian config must never
                    # silently allow actions. Deny everything until fixed.
                    _logger.error("Guardian config %s unreadable (fail-closed deny-all): %s", path, exc)
                    return Guardian([], config=GuardConfig(default_decision=DecisionStatus.DENY))
        return Guardian(rules)

    def _build_probity(self) -> Guardrails:
        # Load OS-level probity first, then project-level (B2 fix): previously
        # only project_root was read, so in multi-project setups the rich OS
        # probity rules were silently dropped, leaving a gap behind Guardian.
        # Collect rules from ALL roots (OS + project) before constructing one
        # Guardrails — a premature ``return`` inside the loop dropped project
        # rules whenever an OS-level probity.yaml existed first.
        import yaml

        rules: list[dict[str, Any]] = []
        roots = [self.root]
        if self.project_root and self.project_root != self.root:
            roots.append(self.project_root)
        for root in roots:
            path = root / "runtime" / "policies" / "probity.yaml"
            if path.exists():
                try:
                    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                    loaded = data.get("rules", [])
                    if isinstance(loaded, list):
                        rules.extend(loaded)
                    else:
                        _logger.error("Probity config %s: 'rules' is not a list — ignored", path)
                except Exception as exc:
                    _logger.error("Probity config %s unreadable — those rules skipped: %s", path, exc)
        return Guardrails({"rules": rules}) if rules else Guardrails()

    # Read-only actions skip the guardian gate. Derived from the canonical
    # READ_ACTIONS set in runtime/policy.py (single source of truth) plus
    # ChatMessage, which is user-initiated and carries no side effects.
    _READ_ONLY_ACTIONS: ClassVar[frozenset[str]] = frozenset(READ_ACTIONS | {"ChatMessage"})

    def check_guardian(
        self, action_type: str, action_data: dict[str, Any], guardian: Guardian | None = None
    ) -> dict[str, Any] | None:
        """Run guardian-angel policy and return an error response if denied.

        Read-only actions (Read, query, ChatMessage, etc.) skip the guardian
        gate entirely. Write/exec/bash actions are always evaluated.
        """
        # Skip guardian for inherently safe read-only actions
        if action_type in self._READ_ONLY_ACTIONS:
            return None
        g = guardian if guardian is not None else self.guardian
        try:
            decision = g.authorize(
                ActionRequest(tool=action_type, attributes={"action": action_data, "args": action_data})
            )
        except Exception as exc:
            # Fail closed: a broken guardian must never silently allow actions.
            self._guardian_denials_total.labels(rule="guardian_error").inc()
            self.audit.log("guardian.error", {"action": action_type, "error": str(exc)})
            return {
                "ok": False,
                "error": f"Guardian evaluation failed: {exc}",
                "decision": {"rule": "guardian_error", "reason": f"fail-closed: {exc}"},
            }
        if decision.status == DecisionStatus.DENY:
            self._guardian_denials_total.labels(rule=decision.rule_name).inc()
            self.audit.log("guardian.deny", {"action": action_type, "rule": decision.rule_name, "reason": decision.reason})
            return {
                "ok": False,
                "error": f"Guardian denied by {decision.rule_name}",
                "decision": {"rule": decision.rule_name, "reason": decision.reason},
            }
        if decision.status == DecisionStatus.REQUIRE_APPROVAL:
            return {
                "ok": False,
                "error": f"Guardian requires approval for {decision.rule_name}",
                "requires_approval": True,
                "decision": {"rule": decision.rule_name, "reason": decision.reason},
            }
        return None

    def check_probity(
        self, action_type: str, action_data: dict[str, Any], probity: Guardrails | None = None
    ) -> None:
        """Run probity guardrails for write and command actions.

        Action types are normalized so that aliases like "Bash", "Shell",
        "Apply", "Patch" are mapped to canonical types ("exec", "write")
        before rule evaluation. This ensures probity cannot be bypassed by
        using a different action label (GATE-02).
        """
        from runtime.probity import normalize_action_type

        normalized = normalize_action_type(action_type)
        # M2: wire real action history so RequireCommand/EnforceTdd guardrails
        # can actually verify prerequisites. Previously ``history`` was always
        # empty, making those guardrails fire false-positive violations.
        history = action_data.get("history")
        if not isinstance(history, list):
            history = []
        event: dict[str, Any] = {
            "type": normalized,
            "raw_type": action_type,
            "history": history,
        }
        if normalized == "write":
            event["path"] = str(action_data.get("path", ""))
            event["content"] = str(action_data.get("content", ""))
        elif normalized == "exec":
            event["command"] = str(action_data.get("command", ""))
        try:
            p = probity if probity is not None else self.probity
            p.check(event)
        except Exception as exc:
            _logger.debug("probity check failed: %s", exc, exc_info=True)
            rule = getattr(exc, "rule_name", "unknown")
            self._probity_violations_total.labels(rule=rule).inc()
            raise

    def resolve_approval(self, action_data: dict[str, Any], dry_run: bool) -> bool:
        # NOTE (B7 / GATE-02): a caller-supplied `approved=True` is still
        # honored here. The residual risk (an agent self-approving a non-read
        # action to skip the Policy ASK gate) is mitigated because the
        # Guardian and Probity gates run *before* this point and will deny
        # destructive/forbidden commands regardless of `approved` (see the B1
        # alias-aware Guardian fix). A stricter option — rejecting caller
        # claims and trusting only `approval_cache` — is intentionally NOT
        # applied because it would break the ChatMessage read-only path and
        # existing approval flows; revisit if Guardian/Probity coverage gaps
        # are found.
        if action_data.get("approved"):
            self._cache_approval(action_data, dry_run)
            return True
        if self.approval_cache.is_approved(action_data):
            action_data["approved"] = True
            return True
        # F1/I3: When an ApprovalService is wired, create a persistent
        # request so the approval lifecycle (notify → poll → resolve) can
        # proceed asynchronously. This is an enhancement layered on top of
        # the cache — the cache still handles replay suppression.
        if self.approval_service is not None:
            action_type = str(action_data.get("type", "unknown"))
            req = self.approval_service.create_request(
                action=action_type,
                args=action_data,
                reason=f"Policy ASK gate for {action_type}",
            )
            _logger.debug(
                "Created approval request %s for action %s",
                req.id, action_type,
            )
        return False

    def _cache_approval(self, action_data: dict[str, Any], dry_run: bool) -> None:
        if not dry_run:
            self.approval_cache.approve(action_data)

    def handle_policy_denied(
        self,
        action_data: dict[str, Any],
        kwargs: dict[str, Any],
        decision: dict[str, Any],
        dry_run: bool,
        telemetry: Any,
    ) -> dict[str, Any]:
        if not dry_run:
            self.audit.log("policy.denied", {"action": action_data.get("type", "unknown"), "args": kwargs, "decision": decision})
        telemetry.record(
            event_type="action",
            action=action_data.get("type", "unknown"),
            status="policy_denied",
            tokens=action_data.get("tokens", 0),
            cost=action_data.get("cost", 0.0),
            metadata={"decision": decision, "dry_run": dry_run, "args": kwargs},
        )
        return {"ok": False, "error": f"Policy denied by {decision.get('rule', 'unknown')}", "decision": decision}

    def handle_policy_ask(
        self,
        action_data: dict[str, Any],
        kwargs: dict[str, Any],
        decision: dict[str, Any],
        dry_run: bool,
        telemetry: Any,
    ) -> dict[str, Any]:
        if not dry_run:
            self.audit.log("policy.asked", {"action": action_data.get("type", "unknown"), "args": kwargs, "decision": decision})
        telemetry.record(
            event_type="action",
            action=action_data.get("type", "unknown"),
            status=Decision.ASK.value,
            tokens=action_data.get("tokens", 0),
            cost=action_data.get("cost", 0.0),
            metadata={"decision": decision, "dry_run": dry_run, "args": kwargs},
        )
        return {
            "ok": False,
            "error": "Action requires explicit approval (approved=True)",
            "requires_approval": True,
            "decision": decision,
        }

    def build_budget_kwargs(
        self, action_data: dict[str, Any], session_id: str | None = None
    ) -> dict[str, Any]:
        budget_kwargs: dict[str, Any] = {}
        if "rollout_id" in action_data:
            budget_kwargs["rollout_id"] = action_data["rollout_id"]
        if "token_weight" in action_data:
            budget_kwargs["token_weight"] = action_data["token_weight"]
        if "input_tokens" in action_data and "output_tokens" in action_data:
            budget_kwargs["input_tokens"] = action_data["input_tokens"]
            budget_kwargs["output_tokens"] = action_data["output_tokens"]
        if session_id is not None:
            budget_kwargs["session_id"] = session_id
        return budget_kwargs

    def audit_budget(
        self,
        action_data: dict[str, Any],
        kwargs: dict[str, Any],
        decision: dict[str, Any],
        budget_result: dict[str, Any],
        dry_run: bool,
    ) -> None:
        if dry_run:
            return
        self.budget.save()
        action_type = action_data.get("type", "unknown")
        if not budget_result.get("ok", False):
            self.audit.log("budget.blocked", {"action": action_type, "args": kwargs, "budget": budget_result})
        else:
            self.audit.log(
                "action.allowed",
                {"action": action_type, "args": kwargs, "decision": decision, "budget": budget_result},
            )

    def finalize_action(
        self,
        action_data: dict[str, Any],
        kwargs: dict[str, Any],
        decision: dict[str, Any],
        budget_result: dict[str, Any],
        dry_run: bool,
        telemetry: Any,
    ) -> dict[str, Any]:
        self.audit_budget(action_data, kwargs, decision, budget_result, dry_run)
        ok = budget_result.get("ok", False)
        telemetry.record(
            event_type="action",
            action=action_data.get("type", "unknown"),
            status=ActionResultStatus.ALLOWED.value if ok else ActionResultStatus.BUDGET_BLOCKED.value,
            tokens=action_data.get("tokens", 0),
            cost=action_data.get("cost", 0.0),
            metadata={"decision": decision, "dry_run": dry_run, "args": kwargs},
        )
        if not ok:
            return {"ok": False, "error": budget_result.get("reason", "budget blocked"), "budget": budget_result}
        return {
            "ok": True,
            "decision": decision,
            "budget": budget_result,
            "action": action_data.get("type", "unknown"),
            "args": kwargs,
        }

    def record_preloop(self, action_type: str, result: dict[str, Any], decision: dict[str, Any]) -> None:
        tag = decision.get("decision", "unknown")
        if not isinstance(tag, str):
            tag = "unknown"
        self.preloop.record(
            Outcome(
                action=action_type,
                ok=result.get("ok", False),
                reward=1.0 if result.get("ok") else 0.0,
                tags=[tag],
            )
        )
