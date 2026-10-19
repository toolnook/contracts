"""Tests for the ledger module (core accounting logic)."""

import pytest
from decimal import Decimal
from ledgerlite.models import Account, Entry, Transaction
from ledgerlite.storage import LedgerStorage
from ledgerlite.ledger import Ledger


@pytest.fixture
def ledger(tmp_path):
    """Create a ledger with standard accounts."""
    storage = LedgerStorage(tmp_path / "test.json")
    storage.init()
    led = Ledger(storage)
    # Standard chart of accounts
    led.add_account("Cash", "asset")
    led.add_account("Accounts Receivable", "asset")
    led.add_account("Revenue", "revenue")
    led.add_account("Office Supplies", "expense")
    led.add_account("Rent Expense", "expense")
    led.add_account("Accounts Payable", "liability")
    led.add_account("Owner Equity", "equity")
    return led


class TestLedgerAccounts:
    def test_add_and_list_accounts(self, ledger):
        accounts = ledger.list_accounts()
        assert len(accounts) == 7
        assert any(a.name == "Cash" for a in accounts)

    def test_add_duplicate_account_raises(self, ledger):
        with pytest.raises(ValueError, match="already exists"):
            ledger.add_account("Cash", "asset")

    def test_get_account(self, ledger):
        acct = ledger.get_account("Cash")
        assert acct is not None
        assert acct.type == "asset"

    def test_get_unknown_account_returns_none(self, ledger):
        assert ledger.get_account("Nonexistent") is None


class TestLedgerTransactions:
    def test_add_balanced_transaction(self, ledger):
        txn = Transaction(
            date="2026-01-15",
            description="Cash sale",
            entries=[
                Entry(account="Cash", debit=Decimal("500")),
                Entry(account="Revenue", credit=Decimal("500")),
            ],
        )
        result = ledger.add_transaction(txn)
        assert result.id == txn.id
        assert ledger.storage.transaction_count() == 1

    def test_add_unbalanced_transaction_raises(self, ledger):
        txn = Transaction(
            date="2026-01-15",
            description="Bad",
            entries=[
                Entry(account="Cash", debit=Decimal("100")),
                Entry(account="Revenue", credit=Decimal("90")),
            ],
        )
        with pytest.raises(ValueError, match="unbalanced"):
            ledger.add_transaction(txn)

    def test_add_transaction_unknown_account_raises(self, ledger):
        txn = Transaction(
            date="2026-01-15",
            description="Unknown",
            entries=[
                Entry(account="Nonexistent", debit=Decimal("100")),
                Entry(account="Revenue", credit=Decimal("100")),
            ],
        )
        with pytest.raises(ValueError, match="Unknown account"):
            ledger.add_transaction(txn)

    def test_add_empty_transaction_raises(self, ledger):
        txn = Transaction(date="2026-01-15", description="Empty", entries=[])
        with pytest.raises(ValueError, match="no entries"):
            ledger.add_transaction(txn)

    def test_delete_transaction(self, ledger):
        txn = Transaction(
            date="2026-01-15",
            description="Sale",
            entries=[
                Entry(account="Cash", debit=Decimal("100")),
                Entry(account="Revenue", credit=Decimal("100")),
            ],
        )
        ledger.add_transaction(txn)
        assert ledger.delete_transaction(txn.id) is True
        assert ledger.storage.transaction_count() == 0

    def test_delete_nonexistent_returns_false(self, ledger):
        assert ledger.delete_transaction("nonexistent") is False


class TestLedgerBalances:
    def test_asset_balance_increases_with_debit(self, ledger):
        txn = Transaction(
            date="2026-01-15",
            description="Sale",
            entries=[
                Entry(account="Cash", debit=Decimal("500")),
                Entry(account="Revenue", credit=Decimal("500")),
            ],
        )
        ledger.add_transaction(txn)
        assert ledger.get_account_balance("Cash") == Decimal("500")

    def test_revenue_balance_increases_with_credit(self, ledger):
        txn = Transaction(
            date="2026-01-15",
            description="Sale",
            entries=[
                Entry(account="Cash", debit=Decimal("500")),
                Entry(account="Revenue", credit=Decimal("500")),
            ],
        )
        ledger.add_transaction(txn)
        assert ledger.get_account_balance("Revenue") == Decimal("500")

    def test_expense_balance_increases_with_debit(self, ledger):
        txn = Transaction(
            date="2026-01-15",
            description="Buy supplies",
            entries=[
                Entry(account="Office Supplies", debit=Decimal("50")),
                Entry(account="Cash", credit=Decimal("50")),
            ],
        )
        ledger.add_transaction(txn)
        assert ledger.get_account_balance("Office Supplies") == Decimal("50")
        assert ledger.get_account_balance("Cash") == Decimal("-50")

    def test_get_all_balances(self, ledger):
        txn = Transaction(
            date="2026-01-15",
            description="Sale",
            entries=[
                Entry(account="Cash", debit=Decimal("1000")),
                Entry(account="Revenue", credit=Decimal("1000")),
            ],
        )
        ledger.add_transaction(txn)
        balances = ledger.get_all_balances()
        assert balances["Cash"] == Decimal("1000")
        assert balances["Revenue"] == Decimal("1000")

    def test_get_balances_by_type(self, ledger):
        txn = Transaction(
            date="2026-01-15",
            description="Sale",
            entries=[
                Entry(account="Cash", debit=Decimal("1000")),
                Entry(account="Revenue", credit=Decimal("1000")),
            ],
        )
        ledger.add_transaction(txn)
        by_type = ledger.get_balances_by_type()
        assert by_type["asset"] == Decimal("1000")
        assert by_type["revenue"] == Decimal("1000")


class TestProjectTagging:
    def test_get_transactions_by_tag(self, ledger):
        txn = Transaction(
            date="2026-01-15",
            description="Project sale",
            tags=["acme"],
            entries=[
                Entry(account="Cash", debit=Decimal("500")),
                Entry(account="Revenue", credit=Decimal("500")),
            ],
        )
        ledger.add_transaction(txn)
        tagged = ledger.get_transactions_by_tag("acme")
        assert len(tagged) == 1
        assert tagged[0].description == "Project sale"

    def test_get_all_tags(self, ledger):
        for desc, tag in [("Sale", "acme"), ("Cost", "acme"), ("Sale2", "beta")]:
            ledger.add_transaction(Transaction(
                date="2026-01-15",
                description=desc,
                tags=[tag],
                entries=[
                    Entry(account="Cash", debit=Decimal("100")),
                    Entry(account="Revenue", credit=Decimal("100")),
                ],
            ))
        assert ledger.get_all_tags() == ["acme", "beta"]

    def test_project_profitability(self, ledger):
        # Revenue for "acme" project
        ledger.add_transaction(Transaction(
            date="2026-01-15",
            description="Acme sale",
            tags=["acme"],
            entries=[
                Entry(account="Cash", debit=Decimal("1000")),
                Entry(account="Revenue", credit=Decimal("1000")),
            ],
        ))
        # Expense for "acme" project
        ledger.add_transaction(Transaction(
            date="2026-01-20",
            description="Acme supplies",
            tags=["acme"],
            entries=[
                Entry(account="Office Supplies", debit=Decimal("300")),
                Entry(account="Cash", credit=Decimal("300")),
            ],
        ))
        profit = ledger.get_project_profitability("acme")
        assert profit["revenue"] == Decimal("1000")
        assert profit["expenses"] == Decimal("300")
        assert profit["profit"] == Decimal("700")
