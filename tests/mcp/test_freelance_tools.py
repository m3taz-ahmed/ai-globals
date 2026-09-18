"""Tests for aizee_mcp/tools/freelance_tools.py MCP tools."""

from __future__ import annotations

import json
from typing import Any

import pytest

from aizee_mcp.tools.freelance_tools import (  # pyright: ignore[reportMissingImports]
    register_freelance_tools,
)

pytestmark = pytest.mark.mcp


class _FakeTool:
    def __call__(self, fn: Any | None = None) -> Any:
        if fn is not None:
            _captured_tools[fn.__name__] = fn
            return fn

        def decorator(inner_fn: Any) -> Any:
            _captured_tools[inner_fn.__name__] = inner_fn
            return inner_fn

        return decorator


class _FakeMCP:
    def __init__(self) -> None:
        self.tool = _FakeTool()


_captured_tools: dict[str, Any] = {}


def _get_tool(name: str) -> Any:
    _captured_tools.clear()
    register_freelance_tools(_FakeMCP())
    return _captured_tools[name]


def _parse(result: str) -> dict[str, Any]:
    return json.loads(result)


class TestContractCreate:
    @pytest.mark.parametrize("ctype", ["nda", "sow", "ip"])
    def test_all_types(self, ctype: str):
        out = _parse(_get_tool("contract_create")(contract_type=ctype,
                                                    party_a="Me", party_b="Client"))
        assert out["ok"] is True
        assert out["contract_type"] == ctype
        assert len(out["clauses"]) >= 3

    def test_bad_type(self):
        out = _parse(_get_tool("contract_create")(contract_type="lease",
                                                    party_a="a", party_b="b"))
        assert out["ok"] is False
        assert "nda/sow/ip" in out["error"]

    def test_empty_party(self):
        out = _parse(_get_tool("contract_create")(contract_type="nda",
                                                    party_a="", party_b="b"))
        assert out["ok"] is False

    def test_bad_terms_json(self):
        out = _parse(_get_tool("contract_create")(contract_type="nda",
                                                    party_a="a", party_b="b", terms="nope"))
        assert out["ok"] is False


class TestContractStatus:
    def test_draft(self):
        out = _parse(_get_tool("contract_status")(contract_id="c1"))
        assert out["status"] == "draft"
        assert out["effective_date"] is None

    def test_partial(self):
        out = _parse(_get_tool("contract_status")(contract_id="c1", signed_a=True))
        assert out["status"] == "partially_signed"

    def test_executed(self):
        out = _parse(_get_tool("contract_status")(contract_id="c1", signed_a=True,
                                                    signed_b=True,
                                                    effective_date="2026-01-01"))
        assert out["status"] == "executed"
        assert out["effective_date"] == "2026-01-01"

    def test_empty_id(self):
        out = _parse(_get_tool("contract_status")(contract_id=""))
        assert out["ok"] is False


class TestInvoiceCreate:
    def test_happy(self):
        out = _parse(_get_tool("invoice_create")(client_id="acme", client_name="Acme",
                                                 amount=500.0, due_in_days=30))
        assert out["ok"] is True
        assert out["gated"] is True
        assert out["invoice"]["status"] == "draft"
        assert out["invoice"]["invoice_id"].startswith("inv_acme_")

    def test_empty_client_id(self):
        out = _parse(_get_tool("invoice_create")(client_id="", client_name="x",
                                                 amount=1))
        assert out["ok"] is False

    def test_bad_client_id_chars(self):
        out = _parse(_get_tool("invoice_create")(client_id="bad id!", client_name="x",
                                                 amount=1))
        assert out["ok"] is False

    def test_non_number_amount(self):
        out = _parse(_get_tool("invoice_create")(client_id="a", client_name="x",
                                                 amount="lots"))
        assert out["ok"] is False
        assert "number" in out["error"]

    def test_negative_amount(self):
        out = _parse(_get_tool("invoice_create")(client_id="a", client_name="x",
                                                 amount=-5))
        assert out["ok"] is False
        assert "finite" in out["error"]

    def test_non_int_due_days(self):
        out = _parse(_get_tool("invoice_create")(client_id="a", client_name="x",
                                                 amount=1, due_in_days="soon"))
        assert out["ok"] is False
        assert "integer" in out["error"]

    def test_due_days_out_of_range(self):
        out = _parse(_get_tool("invoice_create")(client_id="a", client_name="x",
                                                 amount=1, due_in_days=99999))
        assert out["ok"] is False


class TestInvoiceTrack:
    def test_no_payment(self):
        inv = json.dumps({"invoice_id": "i1", "amount": 100.0, "status": "sent"})
        out = _parse(_get_tool("invoice_track")(invoice_json=inv))
        assert out["ok"] is True
        assert out["outstanding"] == "100.0"
        assert out["status"] == "sent"

    def test_partial_payment(self):
        inv = json.dumps({"invoice_id": "i1", "amount": 100})
        out = _parse(_get_tool("invoice_track")(invoice_json=inv, payment_amount=40))
        assert out["ok"] is True
        assert out["outstanding"] == "60"

    def test_full_payment_marks_paid(self):
        inv = json.dumps({"invoice_id": "i1", "amount": 100})
        out = _parse(_get_tool("invoice_track")(invoice_json=inv, payment_amount=100))
        assert out["status"] == "paid"

    def test_bad_json(self):
        out = _parse(_get_tool("invoice_track")(invoice_json="nope"))
        assert out["ok"] is False

    def test_missing_fields(self):
        out = _parse(_get_tool("invoice_track")(invoice_json='{"x":1}'))
        assert out["ok"] is False
        assert "invoice_id" in out["error"]

    def test_bad_status(self):
        inv = json.dumps({"invoice_id": "i1", "amount": 5, "status": "bogus"})
        out = _parse(_get_tool("invoice_track")(invoice_json=inv))
        assert out["ok"] is False


class TestPricingCalc:
    def test_happy(self):
        out = _parse(_get_tool("pricing_calc")(income_goal=100000,
                                               billable_hours_per_week=30))
        assert out["ok"] is True
        assert "rates" in out
        assert out["currency"] == "USD"

    def test_non_number(self):
        out = _parse(_get_tool("pricing_calc")(income_goal="rich",
                                               billable_hours_per_week=30))
        assert out["ok"] is False
        assert "numbers" in out["error"]

    def test_nan_input(self):
        out = _parse(_get_tool("pricing_calc")(income_goal=float("nan"),
                                               billable_hours_per_week=30))
        assert out["ok"] is False
        assert "finite" in out["error"]

    def test_zero_income(self):
        out = _parse(_get_tool("pricing_calc")(income_goal=0,
                                               billable_hours_per_week=30))
        assert out["ok"] is False
        assert "positive" in out["error"]


class TestWinlossReport:
    def test_happy_mixed(self):
        deals = json.dumps([
            {"outcome": "won", "value": 1000},
            {"outcome": "lost", "value": 500},
            {"outcome": "pending", "value": 300},
        ])
        out = _parse(_get_tool("winloss_report")(deals=deals))
        assert out["ok"] is True
        assert out["win_rate"] == 0.5
        assert out["avg_won_value"] == 1000.0
        assert out["undecided_deals"] == 1
        assert out["pipeline_value"] == 1800.0

    def test_bad_json(self):
        out = _parse(_get_tool("winloss_report")(deals="nope"))
        assert out["ok"] is False

    def test_empty_list(self):
        out = _parse(_get_tool("winloss_report")(deals="[]"))
        assert out["ok"] is False

    def test_non_dict_deal(self):
        out = _parse(_get_tool("winloss_report")(deals="[1]"))
        assert out["ok"] is False
        assert "object" in out["error"]

    def test_bad_value(self):
        out = _parse(_get_tool("winloss_report")(deals='[{"outcome":"won","value":"x"}]'))
        assert out["ok"] is False
        assert "number" in out["error"]

    def test_nan_value(self):
        out = _parse(_get_tool("winloss_report")(deals='[{"outcome":"won","value":1e999}]'))
        # 1e999 parses to inf in Python
        assert out["ok"] is False


class TestArabicPlatformFetch:
    def test_happy_mostaql(self):
        out = _parse(_get_tool("arabic_platform_fetch")(platform="mostaql",
                                                        query="python dev"))
        assert out["ok"] is True
        assert out["rtl"] is True
        assert "mostaql.com" in out["instruction"]["base_url"]

    def test_unknown_platform(self):
        out = _parse(_get_tool("arabic_platform_fetch")(platform="fiverr"))
        assert out["ok"] is False
        assert "unknown Arabic platform" in out["error"]

    def test_empty_query_ok(self):
        out = _parse(_get_tool("arabic_platform_fetch")(platform="khamsat"))
        assert out["ok"] is True
