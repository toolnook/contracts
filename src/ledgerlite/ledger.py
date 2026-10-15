"""
Core ledger logic for LedgerLite.

The ``Ledger`` class wraps the storage layer and enforces double-entry
bookkeeping rules: every transaction must balance (total debits == total
credits) and every entry must reference an existing account.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from .models import Account, Transaction, Entry
from .storage import LedgerStorage


class Ledger:
    """High-level interface for working with the ledger."""

    def __init__(self, storage: LedgerStorage):
        self.storage = storage

    # --- Account management ---

    def add_account(self, name: str, account_type: str, description: str = "") -> Account:
        """Create a new account in the chart of accounts."""
        account = Account(name=name, type=account_type, description=description)
        self.storage.add_account(account)
        return account

    def get_account(self, name: str) -> Optional[Account]:
        for account in self.storage.get_accounts():
            if account.name == name:
                return account
        return None

    def list_accounts(self) -> list[Account]:
        return self.storage.get_accounts()

    # --- Transaction management ---

    def add_transaction(self, txn: Transaction) -> Transaction:
        """Add a transaction after validating it.

        @raises ValueError if the transaction is unbalanced or references
        an unknown account.
        """
        self._validate_transaction(txn)
        self.storage.add_transaction(txn)
        return txn

    def add_transactions(self, txns: list[Transaction]) -> list[Transaction]:
        """Add multiple transactions, validating each."""
        for txn in txns:
            self._validate_transaction(txn)
        self.storage.add_transactions(txns)
        return txns

    def _validate_transaction(self, txn: Transaction) -> None:
        """Validate that a transaction is balanced and accounts exist."""
        if not txn.entries:
            raise ValueError(
                f"Transaction '{txn.description}' has no entries"
            )

        if not txn.is_balanced:
            raise ValueError(
                f"Transaction '{txn.description}' is unbalanced: "
                f"debits={txn.total_debit} credits={txn.total_credit}"
            )

        # Check that all referenced accounts exist
        account_names = {a.name for a in self.storage.get_accounts()}
        for entry in txn.entries:
            if entry.account not in account_names:
                raise ValueError(
                    f"Unknown account '{entry.account}' in transaction "
                    f"'{txn.description}'"
                )

    def get_transactions(self) -> list[Transaction]:
        return self.storage.get_transactions()

    def delete_transaction(self, txn_id: str) -> bool:
        return self.storage.delete_transaction(txn_id)

    # --- Balance calculations ---

    def get_account_balance(self, account_name: str) -> Decimal:
        """Calculate the net balance for an account.

        For asset and expense accounts, debits increase the balance.
        For liability, equity, and revenue accounts, credits increase it.
        """
        account = self.get_account(account_name)
        if account is None:
            raise ValueError(f"Unknown account: {account_name}")

        balance = Decimal("0")
        for txn in self.storage.get_transactions():
            for entry in txn.entries:
                if entry.account == account_name:
                    if account.type in ("asset", "expense"):
                        balance += entry.debit - entry.credit
                    else:
                        balance += entry.credit - entry.debit
        return balance

    def get_all_balances(self) -> dict[str, Decimal]:
        """Return a mapping of account name → balance for all accounts."""
        return {
            account.name: self.get_account_balance(account.name)
            for account in self.list_accounts()
        }

    def get_balances_by_type(self) -> dict[str, Decimal]:
        """Return total balance per account type."""
        totals: dict[str, Decimal] = {}
        for account in self.list_accounts():
            bal = self.get_account_balance(account.name)
            totals[account.type] = totals.get(account.type, Decimal("0")) + bal
        return totals

    # --- Project tagging ---

    def get_transactions_by_tag(self, tag: str) -> list[Transaction]:
        """Return all transactions tagged with the given project tag."""
        return [t for t in self.storage.get_transactions() if tag in t.tags]

    def get_all_tags(self) -> list[str]:
        """Return a sorted list of all unique project tags."""
        tags: set[str] = set()
        for txn in self.storage.get_transactions():
            tags.update(txn.tags)
        return sorted(tags)

    def get_project_profitability(self, tag: str) -> dict[str, Decimal]:
        """Calculate revenue, expenses, and net profit for a project tag."""
        revenue = Decimal("0")
        expenses = Decimal("0")

        for txn in self.get_transactions_by_tag(tag):
            for entry in txn.entries:
                account = self.get_account(entry.account)
                if account is None:
                    continue
                if account.type == "revenue":
                    revenue += entry.credit - entry.debit
                elif account.type == "expense":
                    expenses += entry.debit - entry.credit

        return {
            "revenue": revenue,
            "expenses": expenses,
            "profit": revenue - expenses,
        }
