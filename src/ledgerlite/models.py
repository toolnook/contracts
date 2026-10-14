"""
Data models for LedgerLite.

Defines the core domain objects: accounts, entries, transactions,
and recurring transaction templates.  All amounts are stored as
``Decimal`` to avoid floating-point rounding errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import json
import uuid


# Account types following standard accounting conventions
ACCOUNT_TYPES = frozenset({"asset", "liability", "equity", "revenue", "expense"})


@dataclass
class Account:
    """A single account in the chart of accounts."""

    name: str
    type: str  # asset, liability, equity, revenue, expense
    description: str = ""

    def __post_init__(self) -> None:
        if self.type not in ACCOUNT_TYPES:
            raise ValueError(
                f"Invalid account type '{self.type}'. "
                f"Must be one of: {', '.join(sorted(ACCOUNT_TYPES))}"
            )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Account:
        return cls(
            name=data["name"],
            type=data["type"],
            description=data.get("description", ""),
        )


@dataclass
class Entry:
    """A single debit or credit posting within a transaction.

    Exactly one of ``debit`` or ``credit`` should be non-zero.
    Both use positive values; the side (debit/credit) determines
    the accounting effect.
    """

    account: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        # Ensure we're working with Decimal
        self.debit = Decimal(str(self.debit))
        self.credit = Decimal(str(self.credit))
        if self.debit < 0 or self.credit < 0:
            raise ValueError("Debit and credit must be non-negative")
        if self.debit > 0 and self.credit > 0:
            raise ValueError(
                f"Entry for account '{self.account}' has both debit and credit "
                f"amounts — use separate entries for each side"
            )

    @property
    def amount(self) -> Decimal:
        """The absolute amount of this entry (debit or credit)."""
        return self.debit if self.debit > 0 else self.credit

    @property
    def side(self) -> str:
        """Whether this entry is a debit ('dr') or credit ('cr')."""
        if self.debit > 0:
            return "dr"
        return "cr"

    def to_dict(self) -> dict:
        return {
            "account": self.account,
            "debit": str(self.debit),
            "credit": str(self.credit),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Entry:
        return cls(
            account=data["account"],
            debit=Decimal(data.get("debit", "0")),
            credit=Decimal(data.get("credit", "0")),
        )


@dataclass
class Transaction:
    """A double-entry transaction with one or more debit/credit entries.

    Every transaction must balance: total debits == total credits.
    Transactions can be tagged to projects for profitability tracking.
    """

    date: str  # ISO format: YYYY-MM-DD
    description: str
    entries: list[Entry] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    id: str = ""
    payee: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = uuid.uuid4().hex[:12]
        # Validate date format
        datetime.strptime(self.date, "%Y-%m-%d")

    @property
    def total_debit(self) -> Decimal:
        return sum((e.debit for e in self.entries), Decimal("0"))

    @property
    def total_credit(self) -> Decimal:
        return sum((e.credit for e in self.entries), Decimal("0"))

    @property
    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date,
            "description": self.description,
            "payee": self.payee,
            "tags": self.tags,
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Transaction:
        return cls(
            id=data.get("id", ""),
            date=data["date"],
            description=data["description"],
            payee=data.get("payee", ""),
            tags=data.get("tags", []),
            entries=[Entry.from_dict(e) for e in data["entries"]],
        )


@dataclass
class RecurringTemplate:
    """A template for generating recurring transactions on a schedule.

    The ``frequency`` field accepts: ``daily``, ``weekly``, ``monthly``,
    or ``yearly``.  The ``entries`` define the template that will be
    cloned for each occurrence, with the date set automatically.
    """

    description: str
    frequency: str  # daily, weekly, monthly, yearly
    entries: list[Entry]
    tags: list[str] = field(default_factory=list)
    payee: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = uuid.uuid4().hex[:12]
        valid = {"daily", "weekly", "monthly", "yearly"}
        if self.frequency not in valid:
            raise ValueError(
                f"Invalid frequency '{self.frequency}'. "
                f"Must be one of: {', '.join(sorted(valid))}"
            )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "frequency": self.frequency,
            "payee": self.payee,
            "tags": self.tags,
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> RecurringTemplate:
        return cls(
            id=data.get("id", ""),
            description=data["description"],
            frequency=data["frequency"],
            payee=data.get("payee", ""),
            tags=data.get("tags", []),
            entries=[Entry.from_dict(e) for e in data["entries"]],
        )
