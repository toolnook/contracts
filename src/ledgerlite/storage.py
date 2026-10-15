"""
JSON file-based storage for LedgerLite.

The ledger file is a single JSON document containing the chart of
accounts, all transactions, and recurring templates.  This format is
human-readable and git-friendly — you can version your books alongside
your code.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from .models import Account, Transaction, RecurringTemplate


class LedgerStorage:
    """Read and write the ledger JSON file."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def init(self, accounts: list[Account] | None = None) -> None:
        """Create a new ledger file with an empty structure.

        @param accounts — Optional initial chart of accounts.
        """
        data = {
            "accounts": [a.to_dict() for a in (accounts or [])],
            "transactions": [],
            "recurring": [],
        }
        self._write(data)

    def exists(self) -> bool:
        return self.file_path.exists()

    def load(self) -> dict:
        """Load and return the full ledger data structure."""
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"Ledger file not found: {self.file_path}. "
                f"Run 'ledgerlite init' first."
            )
        with open(self.file_path, "r") as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        """Write the full data structure, creating parent dirs."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    # --- Accounts ---

    def get_accounts(self) -> list[Account]:
        data = self.load()
        return [Account.from_dict(a) for a in data.get("accounts", [])]

    def add_account(self, account: Account) -> None:
        data = self.load()
        names = {a["name"] for a in data.get("accounts", [])}
        if account.name in names:
            raise ValueError(f"Account '{account.name}' already exists")
        data.setdefault("accounts", []).append(account.to_dict())
        self._write(data)

    # --- Transactions ---

    def get_transactions(self) -> list[Transaction]:
        data = self.load()
        return [Transaction.from_dict(t) for t in data.get("transactions", [])]

    def add_transaction(self, txn: Transaction) -> None:
        data = self.load()
        data.setdefault("transactions", []).append(txn.to_dict())
        self._write(data)

    def add_transactions(self, txns: list[Transaction]) -> None:
        """Add multiple transactions in a single write."""
        data = self.load()
        for txn in txns:
            data.setdefault("transactions", []).append(txn.to_dict())
        self._write(data)

    def delete_transaction(self, txn_id: str) -> bool:
        """Remove a transaction by ID.  Returns True if found."""
        data = self.load()
        before = len(data.get("transactions", []))
        data["transactions"] = [
            t for t in data.get("transactions", [])
            if t.get("id") != txn_id
        ]
        after = len(data["transactions"])
        if before != after:
            self._write(data)
            return True
        return False

    # --- Recurring templates ---

    def get_recurring(self) -> list[RecurringTemplate]:
        data = self.load()
        return [RecurringTemplate.from_dict(r) for r in data.get("recurring", [])]

    def add_recurring(self, template: RecurringTemplate) -> None:
        data = self.load()
        data.setdefault("recurring", []).append(template.to_dict())
        self._write(data)

    # --- Summary ---

    def transaction_count(self) -> int:
        data = self.load()
        return len(data.get("transactions", []))

    def account_count(self) -> int:
        data = self.load()
        return len(data.get("accounts", []))
