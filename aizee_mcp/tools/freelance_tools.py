#!/usr/bin/env python3
"""Freelance MCP tools: contracts, invoices, pricing, win/loss, Arabic platforms.

Builds on ``runtime.pricing_calculator`` (strategic rates) and
``runtime.billing_ledger`` (clients/invoices/payments). Contract and Arabic
platform tools use pure logic / JSON proxy instructions (no network calls).
Write tools (invoice_create) produce guardian-reviewable drafts.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from aizee_mcp._compat import FastMCP  # pyright: ignore
from runtime.billing_ledger import Client, Invoice, InvoiceStatus, Payment, PaymentStatus
from runtime.pricing_calculator import recommended_rate
from runtime.schemas import ValidationError

from .common import validate_query


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, default=str)


def _err(error: str, **extra: Any) -> str:
    return _json({"ok": False, "error": error, **extra})


def _ok(**data: Any) -> str:
    return _json({"ok": True, **data})


_ARABIC_PLATFORMS = {
    "mostaql": "https://mostaql.com",
    "khamsat": "https://khamsat.com",
    "bayt": "https://www.bayt.com",
    "freelancer_ar": "https://www.freelancer.com",
}


def register_freelance_tools(mcp: FastMCP) -> None:
    """Register freelance-related MCP tools."""

    @mcp.tool()
    def contract_create(
        contract_type: str,
        party_a: str,
        party_b: str,
        terms: str = "{}",
    ) -> str:
        """Generate a contract draft (NDA / SOW / IP-assignment). Pure template; requires legal review before signing."""
        if contract_type not in ("nda", "sow", "ip"):
            return _err("'contract_type' must be nda/sow/ip")
        if err := validate_query(party_a):
            return err
        if err := validate_query(party_b):
            return err
        try:
            term_map = json.loads(terms)
        except json.JSONDecodeError:
            return _err("'terms' must be valid JSON")
        clauses = {
            "nda": ["Confidentiality", "Term (2 years)", "Return of materials", "Governing law"],
            "sow": ["Scope of work", "Deliverables", "Timeline", "Payment milestones", "Acceptance criteria"],
            "ip": ["Assignment of IP", "Moral rights waiver", "Third-party material warranty", "Effective date"],
        }.get(contract_type, [])
        return _ok(
            contract_type=contract_type,
            party_a=party_a,
            party_b=party_b,
            clauses=clauses,
            custom_terms=term_map,
            note="Draft template only. Have a qualified attorney review before execution.",
        )

    @mcp.tool()
    def contract_status(
        contract_id: str,
        signed_a: bool = False,
        signed_b: bool = False,
        effective_date: str = "",
    ) -> str:
        """Compute contract status from signature state. Pure computation."""
        if err := validate_query(contract_id):
            return err
        if signed_a and signed_b:
            status = "executed"
        elif signed_a or signed_b:
            status = "partially_signed"
        else:
            status = "draft"
        return _ok(
            contract_id=contract_id,
            status=status,
            signed_a=signed_a,
            signed_b=signed_b,
            effective_date=effective_date or None,
        )

    @mcp.tool()
    def invoice_create(
        client_id: str,
        client_name: str,
        amount: float,
        currency: str = "USD",
        due_in_days: int = 14,
    ) -> str:
        """Create a draft invoice via runtime.billing_ledger. WRITE — returns validated invoice object (guardian reviewable)."""
        if err := validate_query(client_id):
            return err
        if re.search(r"[^\w.-]", client_id) or len(client_id) > 64:
            return _err("'client_id' must be [A-Za-z0-9_.-], max 64 chars")
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return _err("'amount' must be a number")
        if not math.isfinite(amount) or amount <= 0 or amount > 1e12:
            return _err("'amount' must be finite within (0, 1e12]")
        try:
            due_in_days = int(due_in_days)
        except (TypeError, ValueError):
            return _err("'due_in_days' must be an integer")
        if not 0 <= due_in_days <= 3650:
            return _err("'due_in_days' must be within [0, 3650]")
        try:
            client = Client(client_id=client_id, name=client_name, currency=currency)
            due = datetime.now(timezone.utc) + timedelta(days=due_in_days)
            stamp = int(datetime.now(timezone.utc).timestamp() * 1000)
            invoice = Invoice(
                invoice_id=f"inv_{client_id}_{stamp}",
                client_id=client_id,
                amount=Decimal(str(amount)),
                due_at=due,
                status=InvoiceStatus.DRAFT,
            )
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        except (TypeError, ValueError) as exc:
            return _err(f"Invalid invoice data: {exc}")
        return _json({
            "ok": True,
            "gated": True,
            "approval_required": True,
            "client": asdict(client),
            "invoice": asdict(invoice),
            "note": "Invoice draft created; send only after guardian approval.",
        })

    @mcp.tool()
    def invoice_track(
        invoice_json: str,
        payment_amount: float = 0.0,
    ) -> str:
        """Apply a payment to an invoice and compute outstanding balance via runtime.billing_ledger."""
        try:
            data = json.loads(invoice_json)
        except json.JSONDecodeError:
            return _err("'invoice_json' must be valid JSON")
        if not isinstance(data, dict) or "invoice_id" not in data or "amount" not in data:
            return _err("'invoice_json' must contain invoice_id and amount")
        try:
            invoice = Invoice(
                invoice_id=data["invoice_id"],
                client_id=data.get("client_id", "unknown"),
                amount=data["amount"],
                status=InvoiceStatus(data.get("status", "draft")),
            )
            if payment_amount > 0:
                invoice.record_payment(Payment(
                    payment_id=f"pay_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                    invoice_id=invoice.invoice_id,
                    amount=Decimal(str(payment_amount)),
                    status=PaymentStatus.COMPLETED,
                ))
        except (ValidationError, ValueError, TypeError) as exc:
            return _err(str(exc))
        return _ok(
            invoice_id=invoice.invoice_id,
            amount=str(invoice.amount),
            outstanding=str(invoice.outstanding_balance()),
            status=invoice.status.value,
        )

    @mcp.tool()
    def pricing_calc(
        income_goal: float,
        billable_hours_per_week: float,
        expenses_yearly: float = 0.0,
        tax_rate: float = 0.0,
        platform_fee_rate: float = 0.0,
        utilization: float = 0.7,
        weeks_per_year: int = 48,
    ) -> str:
        """Compute recommended bill rates via runtime.pricing_calculator."""
        try:
            income_goal = float(income_goal)
            billable_hours_per_week = float(billable_hours_per_week)
            expenses_yearly = float(expenses_yearly)
            tax_rate = float(tax_rate)
            platform_fee_rate = float(platform_fee_rate)
            utilization = float(utilization)
            weeks_per_year = int(weeks_per_year)
        except (TypeError, ValueError):
            return _err("pricing inputs must be numbers")
        for name, val in (
            ("income_goal", income_goal), ("billable_hours_per_week", billable_hours_per_week),
            ("expenses_yearly", expenses_yearly), ("tax_rate", tax_rate),
            ("platform_fee_rate", platform_fee_rate), ("utilization", utilization),
        ):
            if not math.isfinite(val):
                return _err(f"'{name}' must be finite")
        if income_goal <= 0:
            return _err("'income_goal' must be positive")
        try:
            rates = recommended_rate(
                income_goal=income_goal,
                weeks_per_year=weeks_per_year,
                billable_hours_per_week=billable_hours_per_week,
                expenses_yearly=expenses_yearly,
                tax_rate=tax_rate,
                platform_fee_rate=platform_fee_rate,
                utilization=utilization,
            )
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        return _ok(rates=rates, currency="USD")

    @mcp.tool()
    def winloss_report(
        deals: str,
    ) -> str:
        """Compute win/loss analytics from a deals array. Pure computation."""
        try:
            deal_list = json.loads(deals)
        except json.JSONDecodeError:
            return _err("'deals' must be valid JSON")
        if not isinstance(deal_list, list) or not deal_list:
            return _err("'deals' must be a non-empty JSON array")
        wins, losses = [], []
        values = []
        for d in deal_list:
            if not isinstance(d, dict):
                return _err("each deal must be an object")
            outcome = str(d.get("outcome", "")).lower()
            try:
                val = float(d.get("value", 0) or 0)
            except (TypeError, ValueError):
                return _err("each deal 'value' must be a number")
            if not math.isfinite(val) or abs(val) > 1e15:
                return _err("each deal 'value' must be finite within ±1e15")
            values.append(val)
            if outcome == "won":
                wins.append(val)
            elif outcome == "lost":
                losses.append(val)
        total = len(wins) + len(losses)
        win_rate = round(len(wins) / total, 4) if total else 0.0
        avg_won = round(sum(wins) / len(wins), 2) if wins else 0.0
        avg_lost = round(sum(losses) / len(losses), 2) if losses else 0.0
        return _ok(
            total_deals=len(deal_list),
            decided_deals=total,
            undecided_deals=len(deal_list) - total,
            wins=len(wins),
            losses=len(losses),
            win_rate=win_rate,
            avg_won_value=avg_won,
            avg_lost_value=avg_lost,
            pipeline_value=round(sum(values), 2),
        )

    @mcp.tool()
    def arabic_platform_fetch(
        platform: str,
        query: str = "",
    ) -> str:
        """Fetch/scan an Arabic freelance platform (Mostaql/Khamsat/Bayt). READ/EXTERNAL — proxy instruction only."""
        key = (platform or "").lower()
        if key not in _ARABIC_PLATFORMS:
            return _err(f"unknown Arabic platform '{platform}'", allowed=list(_ARABIC_PLATFORMS))
        if query and (err := validate_query(query)):
            return err
        return _json({
            "ok": True,
            "instruction": {
                "platform": key,
                "base_url": _ARABIC_PLATFORMS[key],
                "search_query": query,
                "requires_session_env": f"AIZEE_{key.upper()}_SESSION",
                "note": "Arabic platforms require authenticated sessions; scrape via approved executor with session cookie from env.",
            },
            "rtl": True,
        })
