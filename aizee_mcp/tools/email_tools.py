#!/usr/bin/env python3
"""Email MCP tools: send, sequences, segments, events, templates, campaigns, subscribe/unsubscribe.

Implements a pluggable ``EmailBackend`` concept (Brevo / listmonk / Mailchimp)
without importing network libraries. Write tools are gated: they return a
structured instruction object documenting that they require human approval
(and are intercepted by the guardian) before any external ESP call is made.
External sends are represented as JSON instruction objects (proxies), never
executed inline.
"""

from __future__ import annotations

import abc
import json
from enum import Enum
from typing import Any

from aizee_mcp._compat import FastMCP  # pyright: ignore
from runtime import crm_manager, drip_engine
from runtime.schemas import ValidationError

from .common import validate_query


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, default=str)


def _err(error: str, **extra: Any) -> str:
    return _json({"ok": False, "error": error, **extra})


def _ok(**data: Any) -> str:
    return _json({"ok": True, **data})


# --- Pluggable EmailBackend ------------------------------------------------


class EmailProvider(str, Enum):
    BREVO = "brevo"
    LISTMONK = "listmonk"
    MAILCHIMP = "mailchimp"


class EmailBackend(abc.ABC):
    """Pluggable email service provider backend (concept).

    Subclasses implement ``build_send_instruction`` to produce a JSON
    instruction object describing the external call. Actual transport is
    delegated to the guardian-approved executor.
    """

    provider: EmailProvider

    @abc.abstractmethod
    def build_send_instruction(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a JSON instruction object for the external ESP."""


class BrevoBackend(EmailBackend):
    provider = EmailProvider.BREVO

    def build_send_instruction(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "provider": "brevo",
            "endpoint": "https://api.brevo.com/v3/smtp/email",
            "method": "POST",
            "requires_api_key_env": "AIZEE_BREVO_API_KEY",
            "body": {
                "sender": payload.get("sender"),
                "to": payload.get("to"),
                "subject": payload.get("subject"),
                "htmlContent": payload.get("html"),
            },
        }


class ListmonkBackend(EmailBackend):
    provider = EmailProvider.LISTMONK

    def build_send_instruction(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "provider": "listmonk",
            "endpoint": "/api/campaigns",
            "method": "POST",
            "requires_api_key_env": "AIZEE_LISTMONK_API_KEY",
            "body": {
                "name": payload.get("subject"),
                "subject": payload.get("subject"),
                "lists": payload.get("lists", []),
                "type": "regular",
            },
        }


class MailchimpBackend(EmailBackend):
    provider = EmailProvider.MAILCHIMP

    def build_send_instruction(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "provider": "mailchimp",
            "endpoint": "/3.0/campaigns",
            "method": "POST",
            "requires_api_key_env": "AIZEE_MAILCHIMP_API_KEY",
            "body": {
                "type": "regular",
                "recipients": {"list_id": payload.get("list_id")},
                "settings": {"subject_line": payload.get("subject")},
            },
        }


_BACKENDS: dict[str, type[EmailBackend]] = {
    EmailProvider.BREVO.value: BrevoBackend,
    EmailProvider.LISTMONK.value: ListmonkBackend,
    EmailProvider.MAILCHIMP.value: MailchimpBackend,
}


def _resolve_backend(provider: str) -> EmailBackend:
    key = (provider or "brevo").lower()
    if key not in _BACKENDS:
        raise ValidationError(
            f"Unknown email provider '{provider}'",
            context={"allowed": list(_BACKENDS)},
        )
    return _BACKENDS[key]()


# --- Tool registration -----------------------------------------------------


def register_email_tools(mcp: FastMCP) -> None:
    """Register email-related MCP tools."""

    @mcp.tool()
    def email_send(
        to: str,
        subject: str,
        html: str = "",
        text: str = "",
        sender: str = "",
        provider: str = "brevo",
    ) -> str:
        """Send a transactional email. WRITE/EXTERNAL — gated by guardian; requires human approval before the ESP call executes. Returns a JSON instruction object (proxy) describing the send."""
        if not to or "@" not in to:
            return _err("'to' must be a valid email address")
        if not subject:
            return _err("'subject' is required")
        if not html and not text:
            return _err("Provide 'html' or 'text' body")
        try:
            backend = _resolve_backend(provider)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        payload = {
            "to": [{"email": to}],
            "subject": subject,
            "html": html,
            "text": text,
            "sender": sender or None,
        }
        instruction = backend.build_send_instruction(payload)
        return _json({
            "ok": True,
            "gated": True,
            "approval_required": True,
            "note": "This send is a proxy instruction. The guardian must approve before any external API call.",
            "instruction": instruction,
        })

    @mcp.tool()
    def email_sequence(
        name: str,
        steps: str = "[]",
        provider: str = "brevo",
    ) -> str:
        """Define a drip/email sequence (list of timed steps). Returns the structured sequence plan. WRITE/EXTERNAL — gated."""
        if err := validate_query(name):
            return err
        try:
            parsed = json.loads(steps)
        except json.JSONDecodeError:
            return _err("'steps' must be valid JSON")
        if not isinstance(parsed, list):
            return _err("'steps' must be a JSON array")
        try:
            backend = _resolve_backend(provider)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        plan = []
        for i, step in enumerate(parsed):
            if not isinstance(step, dict):
                return _err(f"step {i} must be an object")
            plan.append({
                "step": i + 1,
                "delay_hours": step.get("delay_hours", 0),
                "subject": step.get("subject", ""),
                "provider": backend.provider.value,
            })
        return _json({
            "ok": True,
            "gated": True,
            "approval_required": True,
            "sequence": name,
            "steps": plan,
            "note": "Sequence execution requires guardian approval per step.",
        })

    @mcp.tool()
    def email_segment(
        name: str,
        criteria: str = "{}",
    ) -> str:
        """Compute an audience segment from JSON criteria (e.g. {"country":"EG","opened":true}). Pure computation; returns matched-rule summary."""
        if err := validate_query(name):
            return err
        try:
            crit = json.loads(criteria)
        except json.JSONDecodeError:
            return _err("'criteria' must be valid JSON")
        if not isinstance(crit, dict):
            return _err("'criteria' must be a JSON object")
        rules = [{"field": k, "op": "equals", "value": v} for k, v in crit.items()]
        return _ok(
            segment=name,
            rule_count=len(rules),
            rules=rules,
            note="Apply this segment against your ESP contact list via email_subscribe/export.",
        )

    @mcp.tool()
    def email_events(
        provider: str = "brevo",
        since_days: int = 7,
    ) -> str:
        """Fetch engagement events (opens/clicks/bounces) from an ESP. READ/EXTERNAL — proxy instruction only, no inline network call."""
        try:
            backend = _resolve_backend(provider)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        since_days = max(1, min(since_days, 90))
        return _json({
            "ok": True,
            "provider": backend.provider.value,
            "since_days": since_days,
            "instruction": {
                "endpoint": f"{backend.build_send_instruction({}).get('endpoint', '')}/events",
                "method": "GET",
                "requires_api_key_env": "AIZEE_" + backend.provider.value.upper() + "_API_KEY",
                "query": {"since": f"{since_days}d"},
            },
            "note": "Proxy instruction. Fetch via approved executor with API key from env.",
        })

    @mcp.tool()
    def email_template(
        name: str,
        body: str = "",
        variables: str = "[]",
    ) -> str:
        """Create/validate an email template with merge variables. Pure computation; returns variable list + render placeholder."""
        if err := validate_query(name):
            return err
        try:
            vars_list = json.loads(variables)
        except json.JSONDecodeError:
            return _err("'variables' must be valid JSON")
        if not isinstance(vars_list, list):
            return _err("'variables' must be a JSON array")
        rendered = body
        for v in vars_list:
            rendered = rendered.replace("{{" + str(v) + "}}", f"[{v}]")
        return _ok(
            template=name,
            variable_count=len(vars_list),
            variables=vars_list,
            preview=rendered[:500],
        )

    @mcp.tool()
    def email_campaign(
        name: str,
        list_id: str = "",
        subject: str = "",
        template: str = "",
        provider: str = "brevo",
    ) -> str:
        """Assemble a campaign from a template + list. WRITE/EXTERNAL — gated; returns proxy instruction."""
        if err := validate_query(name):
            return err
        if not subject:
            return _err("'subject' is required")
        try:
            backend = _resolve_backend(provider)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        instruction = backend.build_send_instruction({
            "subject": subject,
            "list_id": list_id,
            "template": template,
        })
        return _json({
            "ok": True,
            "gated": True,
            "approval_required": True,
            "campaign": name,
            "instruction": instruction,
            "note": "Campaign send requires guardian approval.",
        })

    @mcp.tool()
    def email_subscribe(
        list_id: str,
        email: str,
        double_opt_in: bool = True,
        provider: str = "brevo",
    ) -> str:
        """Subscribe an email to a list (GDPR/CAN-SPAM aware). WRITE/EXTERNAL — gated; returns proxy instruction. double_opt_in enforces consent."""
        if not email or "@" not in email:
            return _err("'email' must be valid")
        if not list_id:
            return _err("'list_id' is required")
        try:
            backend = _resolve_backend(provider)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        return _json({
            "ok": True,
            "gated": True,
            "approval_required": True,
            "email": email,
            "list_id": list_id,
            "double_opt_in": double_opt_in,
            "instruction": {
                "provider": backend.provider.value,
                "action": "subscribe",
                "requires_api_key_env": "AIZEE_" + backend.provider.value.upper() + "_API_KEY",
                "consent_required": double_opt_in,
            },
        })

    @mcp.tool()
    def email_unsubscribe(
        list_id: str,
        email: str,
        provider: str = "brevo",
    ) -> str:
        """Unsubscribe an email from a list (honors unsubscribe requests). WRITE/EXTERNAL — gated; returns proxy instruction."""
        if not email or "@" not in email:
            return _err("'email' must be valid")
        if not list_id:
            return _err("'list_id' is required")
        try:
            backend = _resolve_backend(provider)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        return _json({
            "ok": True,
            "gated": True,
            "approval_required": True,
            "email": email,
            "list_id": list_id,
            "instruction": {
                "provider": backend.provider.value,
                "action": "unsubscribe",
                "requires_api_key_env": "AIZEE_" + backend.provider.value.upper() + "_API_KEY",
            },
        })

    @mcp.tool()
    def drip_create_sequence(
        name: str,
    ) -> str:
        """Create a drip sequence via runtime.drip_engine. WRITE — returns sequence metadata."""
        if err := validate_query(name):
            return err
        try:
            engine = drip_engine.DripEngine()
            seq = engine.add_sequence(name)
        except (ValidationError, TypeError, ValueError, AttributeError) as exc:
            return _err(exc.message if hasattr(exc, "message") else str(exc))
        return _ok(
            sequence=seq.name,
            step_count=len(seq.steps),
            note="Sequence created via runtime.drip_engine. Use drip_ready_steps to check ready steps.",
        )

    @mcp.tool()
    def drip_ready_steps(
        sequence_name: str,
        context: str = "{}",
    ) -> str:
        """List ready-to-fire steps in a drip sequence via runtime.drip_engine. Pure computation.

        Args:
            sequence_name: Name of the sequence to check.
            context: JSON object with runtime context for condition evaluation.
        """
        if err := validate_query(sequence_name):
            return err
        try:
            ctx = json.loads(context)
        except json.JSONDecodeError:
            return _err("'context' must be valid JSON")
        try:
            engine = drip_engine.DripEngine()
            try:
                engine.add_sequence(sequence_name)
            except ValidationError:
                engine.sequence(sequence_name)
            ready = engine.ready_steps(context=ctx)
        except (ValidationError, TypeError, ValueError) as exc:
            return _err(exc.message if hasattr(exc, "message") else str(exc))
        return _ok(
            sequence=sequence_name,
            ready_count=len(ready),
            ready_steps=[
                {
                    "step_id": s.step_id,
                    "action": s.action,
                    "trigger": s.trigger.value,
                    "delay_hours": s.delay_hours,
                    "fired": s.fired,
                }
                for s in ready
            ],
            note="Computed via runtime.drip_engine.",
        )

    @mcp.tool()
    def crm_opportunity_transition(
        opportunity_id: str,
        company_id: str,
        from_stage: str,
        to_stage: str,
        amount: float = 0.0,
    ) -> str:
        """Validate and perform a CRM opportunity stage transition via runtime.crm_manager. Pure computation.

        Args:
            opportunity_id: Unique opportunity ID.
            company_id: Associated company ID.
            from_stage: Current stage (new/qualified/proposal/won/lost).
            to_stage: Target stage.
            amount: Opportunity amount.
        """
        if err := validate_query(opportunity_id):
            return err
        try:
            current = crm_manager.OpportunityStage(from_stage)
            target = crm_manager.OpportunityStage(to_stage)
        except ValueError:
            return _err(f"invalid stage; valid: {[s.value for s in crm_manager.OpportunityStage]}")
        opp = crm_manager.Opportunity(
            opportunity_id=opportunity_id,
            company_id=company_id,
            stage=current,
            amount=amount,
        )
        try:
            opp.validate_transition(target)
            opp.transition(target)
        except (ValidationError, TypeError, ValueError) as exc:
            return _err(exc.message if hasattr(exc, "message") else str(exc))
        return _ok(
            opportunity_id=opportunity_id,
            company_id=company_id,
            from_stage=current.value,
            to_stage=opp.stage.value,
            amount=amount,
            note="Transition validated via runtime.crm_manager.",
        )
