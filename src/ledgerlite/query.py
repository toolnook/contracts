"""
Query language for filtering transactions in LedgerLite.

Supports filtering by date range, account name, project tag, and
description text.  Filters can be combined for precise queries.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from dataclasses import dataclass

from .models import Transaction


@dataclass
class QueryFilter:
    """Filter criteria for querying transactions.

    All fields are optional; None means "no filter on this field".
    Multiple fields are AND-combined.
    """

    date_from: Optional[str] = None  # ISO date: YYYY-MM-DD
    date_to: Optional[str] = None
    account: Optional[str] = None
    tag: Optional[str] = None
    description_contains: Optional[str] = None
    payee: Optional[str] = None


class Query:
    """Execute a filter against a list of transactions."""

    def __init__(self, transactions: list[Transaction]):
        self.transactions = transactions

    def filter(self, qf: QueryFilter) -> list[Transaction]:
        """Return all transactions matching the given filter criteria."""
        results: list[Transaction] = []

        for txn in self.transactions:
            if qf.date_from and txn.date < qf.date_from:
                continue
            if qf.date_to and txn.date > qf.date_to:
                continue
            if qf.account:
                account_names = {e.account for e in txn.entries}
                if qf.account not in account_names:
                    continue
            if qf.tag and qf.tag not in txn.tags:
                continue
            if qf.description_contains:
                if qf.description_contains.lower() not in txn.description.lower():
                    continue
            if qf.payee and qf.payee.lower() not in txn.payee.lower():
                continue
            results.append(txn)

        return results

    def filter_by_date_range(self, date_from: str, date_to: str) -> list[Transaction]:
        """Convenience: filter by date range only."""
        return self.filter(QueryFilter(date_from=date_from, date_to=date_to))

    def filter_by_account(self, account: str) -> list[Transaction]:
        """Convenience: filter by account only."""
        return self.filter(QueryFilter(account=account))

    def filter_by_tag(self, tag: str) -> list[Transaction]:
        """Convenience: filter by project tag only."""
        return self.filter(QueryFilter(tag=tag))


def parse_query(args: list[str]) -> QueryFilter:
    """Parse a list of ``key=value`` strings into a QueryFilter.

    Accepted keys: ``from``, ``to``, ``account``, ``tag``,
    ``description``, ``payee``.

    Example: ``["from=2026-01-01", "to=2026-06-30", "tag=acme"]``
    """
    qf = QueryFilter()
    key_map = {
        "from": "date_from",
        "to": "date_to",
        "account": "account",
        "tag": "tag",
        "description": "description_contains",
        "payee": "payee",
    }

    for arg in args:
        if "=" not in arg:
            raise ValueError(f"Invalid query argument '{arg}'. Expected key=value format.")
        key, value = arg.split("=", 1)
        attr = key_map.get(key.strip().lower())
        if attr is None:
            raise ValueError(
                f"Unknown query field '{key}'. "
                f"Valid fields: {', '.join(key_map.keys())}"
            )
        setattr(qf, attr, value)

    return qf
