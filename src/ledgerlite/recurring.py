"""
Recurring transaction scheduler for LedgerLite.

Generates transaction entries for a date range based on recurring
templates.  Supports daily, weekly, monthly, and yearly frequencies.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from .ledger import Ledger
from .models import Entry, RecurringTemplate, Transaction


class RecurringScheduler:
    """Schedule and generate recurring transactions."""

    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def add_template(self, template: RecurringTemplate) -> RecurringTemplate:
        """Register a new recurring template in the ledger."""
        self.ledger.storage.add_recurring(template)
        return template

    def get_templates(self) -> list[RecurringTemplate]:
        """Return all registered recurring templates."""
        return self.ledger.storage.get_recurring()

    def generate(
        self,
        template: RecurringTemplate,
        start_date: str,
        end_date: str,
    ) -> list[Transaction]:
        """Generate transactions for the given template and date range.

        @param template — The recurring template to expand.
        @param start_date — ISO date string (inclusive).
        @param end_date — ISO date string (inclusive).
        @returns List of generated transactions (not yet saved to storage).
        """
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if end < start:
            raise ValueError("end_date must be >= start_date")

        dates = self._generate_dates(template.frequency, start, end)
        transactions: list[Transaction] = []

        for d in dates:
            txn = Transaction(
                date=d.isoformat(),
                description=template.description,
                payee=template.payee,
                tags=list(template.tags),
                entries=[
                    Entry(
                        account=e.account,
                        debit=Decimal(str(e.debit)),
                        credit=Decimal(str(e.credit)),
                    )
                    for e in template.entries
                ],
            )
            transactions.append(txn)

        return transactions

    def generate_and_save(
        self,
        template: RecurringTemplate,
        start_date: str,
        end_date: str,
    ) -> list[Transaction]:
        """Generate and save recurring transactions to the ledger."""
        transactions = self.generate(template, start_date, end_date)
        self.ledger.add_transactions(transactions)
        return transactions

    def generate_all(
        self, start_date: str, end_date: str
    ) -> list[Transaction]:
        """Generate transactions for ALL registered templates."""
        all_txns: list[Transaction] = []
        for template in self.get_templates():
            txns = self.generate(template, start_date, end_date)
            all_txns.extend(txns)
        if all_txns:
            self.ledger.add_transactions(all_txns)
        return all_txns

    def _generate_dates(
        self, frequency: str, start: date, end: date
    ) -> list[date]:
        """Generate the list of occurrence dates between start and end."""
        dates: list[date] = []
        current = start

        if frequency == "daily":
            while current <= end:
                dates.append(current)
                current += timedelta(days=1)

        elif frequency == "weekly":
            while current <= end:
                dates.append(current)
                current += timedelta(weeks=1)

        elif frequency == "monthly":
            while current <= end:
                dates.append(current)
                # Move to same day next month
                year = current.year + (current.month // 12)
                month = (current.month % 12) + 1
                day = min(current.day, 28)  # Safe day for all months
                current = date(year, month, day)

        elif frequency == "yearly":
            while current <= end:
                dates.append(current)
                try:
                    current = date(current.year + 1, current.month, current.day)
                except ValueError:
                    # Handle Feb 29 → Feb 28 on non-leap years
                    current = date(current.year + 1, current.month, 28)

        return dates

    def get_next_occurrence(
        self, template: RecurringTemplate, after_date: str
    ) -> Optional[str]:
        """Return the next occurrence date after the given date, or None."""
        after = datetime.strptime(after_date, "%Y-%m-%d").date()

        if template.frequency == "daily":
            return (after + timedelta(days=1)).isoformat()
        elif template.frequency == "weekly":
            return (after + timedelta(weeks=1)).isoformat()
        elif template.frequency == "monthly":
            year = after.year + (after.month // 12)
            month = (after.month % 12) + 1
            day = min(after.day, 28)
            return date(year, month, day).isoformat()
        elif template.frequency == "yearly":
            try:
                return date(after.year + 1, after.month, after.day).isoformat()
            except ValueError:
                return date(after.year + 1, after.month, 28).isoformat()
        return None
