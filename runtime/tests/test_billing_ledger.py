"""Tests for runtime/billing_ledger.py — client/invoice/payment domain model."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from runtime.billing_ledger import (
    BillingLedger,
    Client,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentStatus,
    RecurringInvoice,
)
from runtime.schemas import StorageError, ValidationError


def _client(cid: str = "c1") -> Client:
    return Client(client_id=cid, name="Acme")


def _invoice(iid: str = "i1", cid: str = "c1", amount: str = "100") -> Invoice:
    return Invoice(invoice_id=iid, client_id=cid, amount=Decimal(amount))


class TestMoney:
    def test_valid_amounts(self):
        assert Invoice(invoice_id="x", client_id="c", amount="12.50").amount == Decimal("12.50")
        assert Invoice(invoice_id="x", client_id="c", amount=7).amount == Decimal("7")

    def test_invalid_amount(self):
        with pytest.raises(ValidationError, match="not a valid amount"):
            Invoice(invoice_id="x", client_id="c", amount="abc")

    def test_negative_amount(self):
        with pytest.raises(ValidationError, match="non-negative"):
            Invoice(invoice_id="x", client_id="c", amount="-5")

    def test_payment_amount_coerced(self):
        p = Payment(payment_id="p", invoice_id="i", amount="9.99")
        assert p.amount == Decimal("9.99")


class TestInvoice:
    def test_record_payment_marks_paid(self):
        inv = _invoice()
        inv.record_payment(Payment(payment_id="p1", invoice_id="i1", amount=Decimal("100")))
        assert inv.status is InvoiceStatus.PAID
        assert inv.outstanding_balance() == Decimal("0")

    def test_partial_payment(self):
        inv = _invoice()
        inv.record_payment(Payment(payment_id="p1", invoice_id="i1", amount=Decimal("40")))
        assert inv.status is InvoiceStatus.DRAFT
        assert inv.outstanding_balance() == Decimal("60")

    def test_overpayment_zeroes_balance(self):
        inv = _invoice()
        inv.record_payment(Payment(payment_id="p1", invoice_id="i1", amount=Decimal("150")))
        assert inv.outstanding_balance() == Decimal("0")
        assert inv.status is InvoiceStatus.PAID

    def test_wrong_invoice_id(self):
        inv = _invoice()
        with pytest.raises(ValidationError, match="does not match"):
            inv.record_payment(
                Payment(payment_id="p", invoice_id="other", amount=Decimal("1")))

    def test_non_completed_payment_rejected(self):
        inv = _invoice()
        with pytest.raises(ValidationError, match="COMPLETED"):
            inv.record_payment(Payment(
                payment_id="p", invoice_id="i1", amount=Decimal("1"),
                status=PaymentStatus.PENDING))

    def test_is_overdue(self):
        inv = _invoice()
        inv.due_at = datetime.now(timezone.utc) - timedelta(days=1)
        assert inv.is_overdue() is True
        inv.due_at = datetime.now(timezone.utc) + timedelta(days=1)
        assert inv.is_overdue() is False

    def test_overdue_but_paid(self):
        inv = _invoice()
        inv.due_at = datetime.now(timezone.utc) - timedelta(days=1)
        inv.record_payment(Payment(payment_id="p", invoice_id="i1", amount=Decimal("100")))
        assert inv.is_overdue() is False

    def test_cancelled_not_overdue(self):
        inv = _invoice()
        inv.status = InvoiceStatus.CANCELLED
        inv.due_at = datetime.now(timezone.utc) - timedelta(days=1)
        assert inv.is_overdue() is False

    def test_no_due_date_not_overdue(self):
        assert _invoice().is_overdue() is False


class TestRecurringInvoice:
    def test_invalid_interval(self):
        with pytest.raises(ValidationError, match="interval_days"):
            RecurringInvoice(template_id="t", client_id="c", amount=Decimal("1"),
                             interval_days=0)

    def test_due_when_never_issued(self):
        r = RecurringInvoice(template_id="t", client_id="c", amount=Decimal("1"),
                             interval_days=30)
        assert r.is_due() is True

    def test_due_after_interval(self):
        r = RecurringInvoice(template_id="t", client_id="c", amount=Decimal("1"),
                             interval_days=30)
        r.last_issued_at = datetime.now(timezone.utc) - timedelta(days=31)
        assert r.is_due() is True
        r.last_issued_at = datetime.now(timezone.utc) - timedelta(days=10)
        assert r.is_due() is False


class TestLedger:
    def test_add_invoice_unknown_client(self):
        ledger = BillingLedger()
        with pytest.raises(ValidationError, match="unknown client"):
            ledger.add_invoice(_invoice())

    def test_outstanding_for_client(self):
        ledger = BillingLedger()
        ledger.add_client(_client())
        ledger.add_client(_client("other"))
        ledger.add_invoice(_invoice("i1", amount="100"))
        ledger.add_invoice(_invoice("i2", amount="50"))
        ledger.add_invoice(_invoice("i3", cid="other", amount="9"))
        assert ledger.outstanding_for_client("c1") == Decimal("150")

    def test_persist_called(self):
        storage = MagicMock()
        ledger = BillingLedger(storage=storage)
        ledger.add_client(_client())
        storage.put.assert_called_once()
        storage.flush.assert_called_once()

    def test_persist_failure_raises_storage_error(self):
        storage = MagicMock()
        storage.put.side_effect = RuntimeError("disk full")
        ledger = BillingLedger(storage=storage)
        with pytest.raises(StorageError, match="persist billing ledger"):
            ledger.add_client(_client())
