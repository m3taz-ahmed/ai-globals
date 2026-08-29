"""Billing ledger entities: clients, invoices, payments, recurring billing.

Domain model inspired by invoiceninja's Client -> Invoice -> Payment flow
(2.7.8). Pure-Python state with optional ``StorageFactory`` persistence.

Raises ``ValidationError`` on invalid amounts and ``StorageError`` when a
configured storage backend fails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

from runtime.schemas import StorageError, ValidationError


class InvoiceStatus(str, Enum):
    """Lifecycle status of an invoice."""

    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Lifecycle status of a payment."""

    PENDING = "pending"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    FAILED = "failed"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: float | Decimal | str, field_name: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError(
            f"{field_name} is not a valid amount",
            context={"field": field_name, "value": str(value)},
        ) from exc
    if amount < 0:
        raise ValidationError(
            f"{field_name} must be non-negative",
            context={"field": field_name, "value": str(value)},
        )
    return amount


@dataclass
class Client:
    """A billing client."""

    client_id: str
    name: str
    email: str = ""
    currency: str = "USD"
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Payment:
    """A single payment applied to an invoice."""

    payment_id: str
    invoice_id: str
    amount: Decimal
    status: PaymentStatus = PaymentStatus.COMPLETED
    paid_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            self.amount = _money(self.amount, "amount")


@dataclass
class Invoice:
    """A billable invoice belonging to a client."""

    invoice_id: str
    client_id: str
    amount: Decimal
    issued_at: datetime = field(default_factory=_now)
    due_at: datetime | None = None
    status: InvoiceStatus = InvoiceStatus.DRAFT
    payments: list[Payment] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            self.amount = _money(self.amount, "amount")

    def record_payment(self, payment: Payment) -> None:
        """Apply a payment to this invoice and update status."""
        if payment.invoice_id != self.invoice_id:
            raise ValidationError(
                "payment invoice_id does not match",
                context={"expected": self.invoice_id, "got": payment.invoice_id},
            )
        if payment.status is not PaymentStatus.COMPLETED:
            raise ValidationError(
                "only COMPLETED payments can be recorded",
                context={"status": payment.status.value},
            )
        self.payments.append(payment)
        if self.outstanding_balance() <= 0:
            self.status = InvoiceStatus.PAID

    def outstanding_balance(self) -> Decimal:
        """Return remaining balance owed on this invoice."""
        paid = sum((p.amount for p in self.payments), Decimal("0"))
        return max(self.amount - paid, Decimal("0"))

    def is_overdue(self, now: datetime | None = None) -> bool:
        """Return True if past due date with a balance and not cancelled."""
        if self.status is InvoiceStatus.CANCELLED:
            return False
        if self.due_at is None:
            return False
        now = now or _now()
        return now > self.due_at and self.outstanding_balance() > 0


@dataclass
class RecurringInvoice:
    """A template that generates invoices on an interval (days)."""

    template_id: str
    client_id: str
    amount: Decimal
    interval_days: int
    currency: str = "USD"
    last_issued_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            self.amount = _money(self.amount, "amount")
        if self.interval_days <= 0:
            raise ValidationError(
                "interval_days must be positive",
                context={"interval_days": self.interval_days},
            )

    def is_due(self, now: datetime | None = None) -> bool:
        """Return True if the next issue date has passed."""
        now = now or _now()
        if self.last_issued_at is None:
            return True
        return (now - self.last_issued_at).days >= self.interval_days


class BillingLedger:
    """In-memory ledger of clients and invoices.

    Optionally persists snapshots through a ``StorageBackend`` when one is
    injected via the constructor (constructor-injection pattern).
    """

    def __init__(self, storage: Any | None = None) -> None:
        self._storage = storage
        self.clients: dict[str, Client] = {}
        self.invoices: dict[str, Invoice] = {}

    def add_client(self, client: Client) -> None:
        self.clients[client.client_id] = client
        self._persist()

    def add_invoice(self, invoice: Invoice) -> None:
        if invoice.client_id not in self.clients:
            raise ValidationError(
                "invoice references unknown client",
                context={"client_id": invoice.client_id},
            )
        self.invoices[invoice.invoice_id] = invoice
        self._persist()

    def outstanding_for_client(self, client_id: str) -> Decimal:
        total = Decimal("0")
        for inv in self.invoices.values():
            if inv.client_id == client_id:
                total += inv.outstanding_balance()
        return total

    def _persist(self) -> None:
        if self._storage is None:
            return
        try:
            self._storage.put(
                "ledger",
                {
                    "clients": {k: v.__dict__ for k, v in self.clients.items()},
                    "invoices": {k: v.__dict__ for k, v in self.invoices.items()},
                },
            )
            self._storage.flush()
        except Exception as exc:
            raise StorageError(
                "failed to persist billing ledger",
                context={"error": str(exc)},
            ) from exc
