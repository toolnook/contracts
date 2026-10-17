"""
CSV import for LedgerLite.

Reads transactions from a CSV file and adds them to the ledger.
Expected CSV format:

    date,description,payee,debit_account,credit_account,amount,tag

If a tag column is present, the transaction is tagged to that project.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from typing import Optional

from .ledger import Ledger
from .models import Entry, Transaction


def import_csv(
    file_path: str | Path,
    ledger: Ledger,
    skip_header: bool = True,
) -> list[Transaction]:
    """Import transactions from a CSV file.

    @param file_path — Path to the CSV file.
    @param ledger — The Ledger instance to add transactions to.
    @param skip_header — Whether to skip the first row (header).
    @returns List of imported transactions.
    @raises ValueError if a row is malformed or references unknown accounts.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    transactions: list[Transaction] = []

    with open(file_path, "r", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

        if skip_header and rows:
            rows = rows[1:]

        for i, row in enumerate(rows, start=1):
            if len(row) < 6:
                raise ValueError(
                    f"CSV row {i} has {len(row)} columns, expected at least 6"
                )

            txn_date = row[0].strip()
            description = row[1].strip()
            payee = row[2].strip()
            debit_account = row[3].strip()
            credit_account = row[4].strip()
            amount_str = row[5].strip()

            try:
                amount = Decimal(amount_str)
            except Exception:
                raise ValueError(
                    f"CSV row {i}: invalid amount '{amount_str}'"
                )

            tags: list[str] = []
            if len(row) >= 7 and row[6].strip():
                tags = [t.strip() for t in row[6].split(",") if t.strip()]

            txn = Transaction(
                date=txn_date,
                description=description,
                payee=payee,
                tags=tags,
                entries=[
                    Entry(account=debit_account, debit=amount),
                    Entry(account=credit_account, credit=amount),
                ],
            )
            transactions.append(txn)

    # Validate and add all transactions
    ledger.add_transactions(transactions)
    return transactions


def export_csv(file_path: str | Path, transactions: list[Transaction]) -> None:
    """Export transactions to a CSV file."""
    file_path = Path(file_path)
    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "date", "description", "payee",
            "debit_account", "credit_account", "amount", "tag",
        ])
        for txn in transactions:
            debit_entry = None
            credit_entry = None
            for entry in txn.entries:
                if entry.debit > 0:
                    debit_entry = entry
                elif entry.credit > 0:
                    credit_entry = entry
            if debit_entry and credit_entry:
                writer.writerow([
                    txn.date,
                    txn.description,
                    txn.payee,
                    debit_entry.account,
                    credit_entry.account,
                    debit_entry.debit,
                    ",".join(txn.tags),
                ])
