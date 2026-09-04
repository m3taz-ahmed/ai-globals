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
import re
from enum import Enum
from typing import Any

from aizee_mcp._compat import FastMCP  # pyright: ignore
from runtime import crm_manager, drip_engine
from runtime.schemas import ValidationError

from .common import validate_query

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_MAX_EMAIL_BODY = 200_000  # 200KB cap on inline bodies


def _clean_header(value: Any, name: str, limit: int = 998) -> str:
    """Validate an email header field: str, no CR/LF (header injection), bounded.

    Raises ValidationError on violation.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"'{name}' is required")
    if "\n" in value or "\r" in value:
        raise ValidationError(f"'{name}' must not contain line breaks (header injection)")
    if len(value) > limit:
        raise ValidationError(f"'{name}' exceeds {limit} chars")
    return value.strip()


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
    #: Provider events endpoint (never derived from the send endpoint).
    EVENTS_ENDPOINT: str = ""

    @abc.abstractmethod
    def build_send_instruction(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a JSON instruction object for the external ESP."""


class BrevoBackend(EmailBackend):
    provider = EmailProvider.BREVO
    EVENTS_ENDPOINT = "https://api.brevo.com/v3/smtp/statistics/events"

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
    EVENTS_ENDPOINT = "/api/subscribers/events"

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
    EVENTS_ENDPOINT = "/3.0/reports"

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
        try:
            to = _clean_header(to, "to", 254)
            subject = _clean_header(subject, "subject")
            sender = _clean_header(sender, "sender", 254) if sender else ""
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        if not _EMAIL_RE.match(to):
            return _err("'to' must be a valid email address")
        if sender and not _EMAIL_RE.match(sender):
            return _err("'sender' must be a valid email address")
        if not isinstance(html, str) or not isinstance(text, str):
            return _err("Provide 'html' or 'text' body as strings")
        if not html and not text:
            return _err("Provide 'html' or 'text' body")
        if len(html) + len(text) > _MAX_EMAIL_BODY:
            return _err(f"Email body exceeds {_MAX_EMAIL_BODY} chars")
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
        try:
            since_days = max(1, min(int(since_days), 90))
        except (TypeError, ValueError):
            since_days = 7
        return _json({
            "ok": True,
            "provider": backend.provider.value,
            "since_days": since_days,
            "instruction": {
                "endpoint": backend.EVENTS_ENDPOINT,
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
        try:
            subject = _clean_header(subject, "subject")
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
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
        try:
            email = _clean_header(email, "email", 254)
            list_id = _clean_header(list_id, "list_id", 128)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        if not _EMAIL_RE.match(email):
            return _err("'email' must be valid")
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
        try:
            email = _clean_header(email, "email", 254)
            list_id = _clean_header(list_id, "list_id", 128)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        if not _EMAIL_RE.match(email):
            return _err("'email' must be valid")
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
        steps: str = "[]",
    ) -> str:
        """List ready-to-fire steps in a drip sequence via runtime.drip_engine. Pure computation.

        Args:
            sequence_name: Name of the sequence to check.
            context: JSON object with runtime context for condition evaluation.
            steps: JSON array of {trigger, action, delay_hours,
                entered_hours_ago, fired} defining the sequence inline
                (the tool is stateless — sequences do not persist across calls).
        """
        if err := validate_query(sequence_name):
            return err
        try:
            ctx = json.loads(context)
        except json.JSONDecodeError:
            return _err("'context' must be valid JSON")
        if not isinstance(ctx, dict):
            return _err("'context' must be a JSON object")
        try:
            steps_list = json.loads(steps)
        except json.JSONDecodeError:
            return _err("'steps' must be valid JSON")
        if not isinstance(steps_list, list):
            return _err("'steps' must be a JSON array")
        try:
            from datetime import datetime, timedelta, timezone
            engine = drip_engine.DripEngine()
            seq = engine.add_sequence(sequence_name)
            for i, s in enumerate(steps_list):
                if not isinstance(s, dict):
                    return _err(f"step {i} must be an object")
                try:
                    trigger = drip_engine.Trigger(str(s.get("trigger", "on_enter")))
                except ValueError:
                    return _err(f"step {i}: invalid trigger {[t.value for t in drip_engine.Trigger]}")
                try:
                    delay = float(s.get("delay_hours", 0.0))
                    entered_ago = float(s.get("entered_hours_ago", 0.0))
                except (TypeError, ValueError):
                    return _err(f"step {i}: delay_hours/entered_hours_ago must be numbers")
                if delay < 0 or entered_ago < 0:
                    return _err(f"step {i}: delays must be non-negative")
                step = engine.add_step(seq, trigger, None, str(s.get("action", "")), delay_hours=delay)
                if bool(s.get("entered", True)):
                    engine.enter(step, datetime.now(timezone.utc) - timedelta(hours=entered_ago))
                if s.get("fired"):
                    engine.mark_fired(step)
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
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return _err("'amount' must be a number")
        import math
        if not math.isfinite(amount) or amount < 0 or amount > 1e15:
            return _err("'amount' must be finite within [0, 1e15]")
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
