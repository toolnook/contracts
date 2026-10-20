"""Tests for the storage module."""

import pytest
from decimal import Decimal
from ledgerlite.models import Account, Entry, Transaction, RecurringTemplate
from ledgerlite.storage import LedgerStorage


@pytest.fixture
def storage(tmp_path):
    s = LedgerStorage(tmp_path / "test.json")
    s.init()
    return s


class TestStorageInit:
    def test_init_creates_file(self, tmp_path):
        path = tmp_path / "ledger.json"
        s = LedgerStorage(path)
        assert not s.exists()
        s.init()
        assert s.exists()

    def test_init_with_accounts(self, tmp_path):
        path = tmp_path / "ledger.json"
        s = LedgerStorage(path)
        accounts = [
            Account(name="Cash", type="asset"),
            Account(name="Revenue", type="revenue"),
        ]
        s.init(accounts=accounts)
        loaded = s.get_accounts()
        assert len(loaded) == 2
        assert loaded[0].name == "Cash"

    def test_exists_returns_false_for_missing(self, tmp_path):
        s = LedgerStorage(tmp_path / "nope.json")
        assert not s.exists()

    def test_load_missing_file_raises(self, tmp_path):
        s = LedgerStorage(tmp_path / "nope.json")
        with pytest.raises(FileNotFoundError):
            s.load()


class TestStorageAccounts:
    def test_add_and_get_accounts(self, storage):
        storage.add_account(Account(name="Cash", type="asset"))
        storage.add_account(Account(name="Revenue", type="revenue"))
        accounts = storage.get_accounts()
        assert len(accounts) == 2
        assert storage.account_count() == 2

    def test_add_duplicate_account_raises(self, storage):
        storage.add_account(Account(name="Cash", type="asset"))
        with pytest.raises(ValueError, match="already exists"):
            storage.add_account(Account(name="Cash", type="asset"))


class TestStorageTransactions:
    def test_add_and_get_transactions(self, storage):
        storage.add_account(Account(name="Cash", type="asset"))
        storage.add_account(Account(name="Revenue", type="revenue"))

        txn = Transaction(
            date="2026-01-15",
            description="Sale",
            entries=[
                Entry(account="Cash", debit=Decimal("100")),
                Entry(account="Revenue", credit=Decimal("100")),
            ],
        )
        storage.add_transaction(txn)
        txns = storage.get_transactions()
        assert len(txns) == 1
        assert txns[0].description == "Sale"
        assert storage.transaction_count() == 1

    def test_add_multiple_transactions(self, storage):
        storage.add_account(Account(name="Cash", type="asset"))
        storage.add_account(Account(name="Revenue", type="revenue"))

        txns = [
            Transaction(
                date="2026-01-15",
                description=f"Sale {i}",
                entries=[
                    Entry(account="Cash", debit=Decimal("100")),
                    Entry(account="Revenue", credit=Decimal("100")),
                ],
            )
            for i in range(5)
        ]
        storage.add_transactions(txns)
        assert storage.transaction_count() == 5

    def test_delete_transaction(self, storage):
        storage.add_account(Account(name="Cash", type="asset"))
        storage.add_account(Account(name="Revenue", type="revenue"))

        txn = Transaction(
            date="2026-01-15",
            description="Sale",
            entries=[
                Entry(account="Cash", debit=Decimal("100")),
                Entry(account="Revenue", credit=Decimal("100")),
            ],
        )
        storage.add_transaction(txn)
        assert storage.delete_transaction(txn.id) is True
        assert storage.transaction_count() == 0

    def test_delete_nonexistent_returns_false(self, storage):
        assert storage.delete_transaction("nonexistent") is False


class TestStorageRecurring:
    def test_add_and_get_recurring(self, storage):
        template = RecurringTemplate(
            description="Rent",
            frequency="monthly",
            entries=[
                Entry(account="Rent Expense", debit=Decimal("2000")),
                Entry(account="Cash", credit=Decimal("2000")),
            ],
        )
        storage.add_recurring(template)
        templates = storage.get_recurring()
        assert len(templates) == 1
        assert templates[0].description == "Rent"
        assert templates[0].frequency == "monthly"
