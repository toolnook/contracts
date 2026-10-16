"""
Financial report generation for LedgerLite.

Generates Profit & Loss, Balance Sheet, Cash Flow, and
per-project profitability reports formatted as terminal tables.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from .ledger import Ledger
from .models import Account
from .query import Query, QueryFilter


def format_amount(amount: Decimal) -> str:
    """Format a Decimal as a currency string."""
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a simple monospaced table for terminal output."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    def fmt_row(cells: list[str]) -> str:
        return "  ".join(
            str(cell).ljust(col_widths[i]) for i, cell in enumerate(cells)
        )

    separator = "─" * (sum(col_widths) + 2 * (len(headers) - 1))
    lines = [fmt_row(headers), separator]
    for row in rows:
        lines.append(fmt_row(row))
    return "\n".join(lines)


class ReportGenerator:
    """Generate financial reports from the ledger."""

    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def profit_and_loss(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> str:
        """Generate a Profit & Loss statement."""
        transactions = self.ledger.get_transactions()
        query = Query(transactions)
        qf = QueryFilter(date_from=date_from, date_to=date_to)
        txns = query.filter(qf)

        revenue_accounts = [
            a for a in self.ledger.list_accounts() if a.type == "revenue"
        ]
        expense_accounts = [
            a for a in self.ledger.list_accounts() if a.type == "expense"
        ]

        def calc(account_name: str) -> Decimal:
            total = Decimal("0")
            for txn in txns:
                for entry in txn.entries:
                    if entry.account == account_name:
                        # Revenue: credit increases; Expense: debit increases
                        account = self.ledger.get_account(account_name)
                        if account and account.type == "revenue":
                            total += entry.credit - entry.debit
                        elif account and account.type == "expense":
                            total += entry.debit - entry.credit
            return total

        rows: list[list[str]] = []
        total_revenue = Decimal("0")
        for acct in revenue_accounts:
            bal = calc(acct.name)
            if bal != 0:
                rows.append([acct.name, format_amount(bal)])
                total_revenue += bal

        rows.append(["", ""])
        rows.append(["Total Revenue", format_amount(total_revenue)])

        total_expenses = Decimal("0")
        for acct in expense_accounts:
            bal = calc(acct.name)
            if bal != 0:
                rows.append([acct.name, format_amount(bal)])
                total_expenses += bal

        rows.append(["", ""])
        rows.append(["Total Expenses", format_amount(total_expenses)])
        rows.append(["", ""])
        net = total_revenue - total_expenses
        rows.append(["Net Income", format_amount(net)])

        header_line = "Profit & Loss"
        if date_from or date_to:
            header_line += f" ({date_from or '...'} to {date_to or '...'})"
        return f"{header_line}\n\n{format_table(['Account', 'Amount'], rows)}"

    def balance_sheet(self, date_as_of: Optional[str] = None) -> str:
        """Generate a Balance Sheet."""
        transactions = self.ledger.get_transactions()
        query = Query(transactions)
        qf = QueryFilter(date_to=date_as_of)
        txns = query.filter(qf)

        asset_accounts = [
            a for a in self.ledger.list_accounts() if a.type == "asset"
        ]
        liability_accounts = [
            a for a in self.ledger.list_accounts() if a.type == "liability"
        ]
        equity_accounts = [
            a for a in self.ledger.list_accounts() if a.type == "equity"
        ]

        def calc(account_name: str, account_type: str) -> Decimal:
            total = Decimal("0")
            for txn in txns:
                for entry in txn.entries:
                    if entry.account == account_name:
                        if account_type in ("asset", "expense"):
                            total += entry.debit - entry.credit
                        else:
                            total += entry.credit - entry.debit
            return total

        rows: list[list[str]] = []
        total_assets = Decimal("0")
        for acct in asset_accounts:
            bal = calc(acct.name, "asset")
            rows.append([acct.name, format_amount(bal)])
            total_assets += bal
        rows.append(["Total Assets", format_amount(total_assets)])
        rows.append(["", ""])

        total_liabilities = Decimal("0")
        for acct in liability_accounts:
            bal = calc(acct.name, "liability")
            rows.append([acct.name, format_amount(bal)])
            total_liabilities += bal
        rows.append(["Total Liabilities", format_amount(total_liabilities)])
        rows.append(["", ""])

        total_equity = Decimal("0")
        for acct in equity_accounts:
            bal = calc(acct.name, "equity")
            rows.append([acct.name, format_amount(bal)])
            total_equity += bal

        # Calculate retained earnings (revenue - expenses up to date_as_of)
        revenue = Decimal("0")
        expenses = Decimal("0")
        for txn in txns:
            for entry in txn.entries:
                account = self.ledger.get_account(entry.account)
                if account and account.type == "revenue":
                    revenue += entry.credit - entry.debit
                elif account and account.type == "expense":
                    expenses += entry.debit - entry.credit
        retained = revenue - expenses
        rows.append(["Retained Earnings", format_amount(retained)])
        total_equity += retained
        rows.append(["Total Equity", format_amount(total_equity)])

        header = "Balance Sheet"
        if date_as_of:
            header += f" as of {date_as_of}"
        return f"{header}\n\n{format_table(['Account', 'Amount'], rows)}"

    def cash_flow(self, date_from: str, date_to: str) -> str:
        """Generate a simplified Cash Flow statement (indirect method)."""
        transactions = self.ledger.get_transactions()
        query = Query(transactions)
        qf = QueryFilter(date_from=date_from, date_to=date_to)
        txns = query.filter(qf)

        # Operating: revenue - expenses
        operating = Decimal("0")
        for txn in txns:
            for entry in txn.entries:
                account = self.ledger.get_account(entry.account)
                if account and account.type == "revenue":
                    operating += entry.credit - entry.debit
                elif account and account.type == "expense":
                    operating -= entry.debit - entry.credit

        # Investing: changes in non-cash assets
        investing = Decimal("0")
        asset_accounts = [
            a for a in self.ledger.list_accounts()
            if a.type == "asset" and a.name != "Cash"
        ]
        for acct in asset_accounts:
            for txn in txns:
                for entry in txn.entries:
                    if entry.account == acct.name:
                        investing -= entry.debit - entry.credit

        # Financing: changes in liabilities and equity
        financing = Decimal("0")
        for txn in txns:
            for entry in txn.entries:
                account = self.ledger.get_account(entry.account)
                if account and account.type == "liability":
                    financing += entry.credit - entry.debit
                elif account and account.type == "equity":
                    financing += entry.credit - entry.debit

        net = operating + investing + financing
        rows = [
            ["Operating Activities", format_amount(operating)],
            ["Investing Activities", format_amount(investing)],
            ["Financing Activities", format_amount(financing)],
            ["", ""],
            ["Net Cash Flow", format_amount(net)],
        ]
        header = f"Cash Flow ({date_from} to {date_to})"
        return f"{header}\n\n{format_table(['Category', 'Amount'], rows)}"

    def by_project(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> str:
        """Generate a per-project profitability report."""
        tags = self.ledger.get_all_tags()
        if not tags:
            return "No tagged transactions found."

        rows: list[list[str]] = []
        for tag in tags:
            profit = self.ledger.get_project_profitability(tag)
            rows.append([
                tag,
                format_amount(profit["revenue"]),
                format_amount(profit["expenses"]),
                format_amount(profit["profit"]),
            ])

        header = "Project Profitability"
        if date_from or date_to:
            header += f" ({date_from or '...'} to {date_to or '...'})"
        return (
            f"{header}\n\n"
            f"{format_table(['Project', 'Revenue', 'Expenses', 'Profit'], rows)}"
        )

    def account_balances(self) -> str:
        """List all account balances."""
        rows: list[list[str]] = []
        for account in self.ledger.list_accounts():
            bal = self.ledger.get_account_balance(account.name)
            rows.append([
                account.name,
                account.type,
                format_amount(bal),
            ])
        return f"Account Balances\n\n{format_table(['Account', 'Type', 'Balance'], rows)}"
