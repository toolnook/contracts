"""Tests for the models module."""

import pytest
from decimal import Decimal
from ledgerlite.models import Account, Entry, Transaction, RecurringTemplate


class TestAccount:
    def test_create_valid_account(self):
        acct = Account(name="Cash", type="asset")
        assert acct.name == "Cash"
        assert acct.type == "asset"
        assert acct.description == ""

    def test_create_account_with_description(self):
        acct = Account(name="Bank", type="asset", description="Main checking")
        assert acct.description == "Main checking"

    def test_invalid_account_type_raises(self):
        with pytest.raises(ValueError, match="Invalid account type"):
            Account(name="Foo", type="invalid")

    def test_account_round_trip(self):
        acct = Account(name="Supplies", type="expense", description="Office supplies")
        d = acct.to_dict()
        assert Account.from_dict(d) == acct


class TestEntry:
    def test_debit_entry(self):
        entry = Entry(account="Cash", debit=Decimal("100.00"))
        assert entry.debit == Decimal("100.00")
        assert entry.credit == Decimal("0")
        assert entry.amount == Decimal("100.00")
        assert entry.side == "dr"

    def test_credit_entry(self):
        entry = Entry(account="Revenue", credit=Decimal("50.00"))
        assert entry.debit == Decimal("0")
        assert entry.credit == Decimal("50.00")
        assert entry.side == "cr"

    def test_both_debit_and_credit_raises(self):
        with pytest.raises(ValueError, match="both debit and credit"):
            Entry(account="Cash", debit=Decimal("10"), credit=Decimal("10"))

    def test_negative_amount_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            Entry(account="Cash", debit=Decimal("-5"))

    def test_entry_round_trip(self):
        entry = Entry(account="Cash", debit=Decimal("42.50"))
        d = entry.to_dict()
        restored = Entry.from_dict(d)
        assert restored.account == "Cash"
        assert restored.debit == Decimal("42.50")


class TestTransaction:
    def test_balanced_transaction(self):
        txn = Transaction(
            date="2026-01-15",
            description="Sale",
            entries=[
                Entry(account="Cash", debit=Decimal("100")),
                Entry(account="Revenue", credit=Decimal("100")),
            ],
        )
        assert txn.is_balanced
        assert txn.total_debit == Decimal("100")
        assert txn.total_credit == Decimal("100")

    def test_unbalanced_transaction(self):
        txn = Transaction(
            date="2026-01-15",
            description="Bad",
            entries=[
                Entry(account="Cash", debit=Decimal("100")),
                Entry(account="Revenue", credit=Decimal("90")),
            ],
        )
        assert not txn.is_balanced

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError):
            Transaction(date="01/15/2026", description="X", entries=[])

    def test_auto_generates_id(self):
        txn = Transaction(date="2026-01-01", description="Test", entries=[])
        assert len(txn.id) == 12

    def test_transaction_round_trip(self):
        txn = Transaction(
            date="2026-03-01",
            description="Payment",
            payee="ACME Corp",
            tags=["acme"],
            entries=[
                Entry(account="Cash", debit=Decimal("50")),
                Entry(account="Revenue", credit=Decimal("50")),
            ],
        )
        d = txn.to_dict()
        restored = Transaction.from_dict(d)
        assert restored.date == txn.date
        assert restored.description == txn.description
        assert restored.tags == txn.tags
        assert restored.entries[0].account == "Cash"


class TestRecurringTemplate:
    def test_create_monthly_template(self):
        template = RecurringTemplate(
            description="Rent",
            frequency="monthly",
            entries=[
                Entry(account="Rent Expense", debit=Decimal("2000")),
                Entry(account="Cash", credit=Decimal("2000")),
            ],
        )
        assert template.frequency == "monthly"
        assert len(template.id) == 12

    def test_invalid_frequency_raises(self):
        with pytest.raises(ValueError, match="Invalid frequency"):
            RecurringTemplate(
                description="X",
                frequency="hourly",
                entries=[],
            )
