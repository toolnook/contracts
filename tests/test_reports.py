"""Tests for the reports module."""

import pytest
from decimal import Decimal
from ledgerlite.models import Account, Entry, Transaction
from ledgerlite.storage import LedgerStorage
from ledgerlite.ledger import Ledger
from ledgerlite.reports import ReportGenerator, format_table, format_amount


@pytest.fixture
def ledger(tmp_path):
    storage = LedgerStorage(tmp_path / "test.json")
    storage.init()
    led = Ledger(storage)
    led.add_account("Cash", "asset")
    led.add_account("Revenue", "revenue")
    led.add_account("Office Supplies", "expense")
    led.add_account("Rent Expense", "expense")
    led.add_account("Accounts Payable", "liability")
    led.add_account("Owner Equity", "equity")

    # Revenue transactions
    led.add_transaction(Transaction(
        date="2026-01-15", description="January sale", tags=["acme"],
        entries=[
            Entry(account="Cash", debit=Decimal("1000")),
            Entry(account="Revenue", credit=Decimal("1000")),
        ],
    ))
    led.add_transaction(Transaction(
        date="2026-03-20", description="March sale", tags=["beta"],
        entries=[
            Entry(account="Cash", debit=Decimal("2000")),
            Entry(account="Revenue", credit=Decimal("2000")),
        ],
    ))

    # Expense transactions
    led.add_transaction(Transaction(
        date="2026-02-10", description="Office supplies", tags=["acme"],
        entries=[
            Entry(account="Office Supplies", debit=Decimal("200")),
            Entry(account="Cash", credit=Decimal("200")),
        ],
    ))
    led.add_transaction(Transaction(
        date="2026-02-28", description="Rent", tags=[],
        entries=[
            Entry(account="Rent Expense", debit=Decimal("800")),
            Entry(account="Cash", credit=Decimal("800")),
        ],
    ))
    return led


class TestFormatHelpers:
    def test_format_amount_positive(self):
        assert format_amount(Decimal("1000")) == "$1,000.00"

    def test_format_amount_negative(self):
        assert format_amount(Decimal("-500")) == "-$500.00"

    def test_format_amount_zero(self):
        assert format_amount(Decimal("0")) == "$0.00"

    def test_format_table(self):
        result = format_table(["A", "B"], [["1", "2"], ["3", "4"]])
        assert "A" in result
        assert "B" in result
        assert "1" in result
        assert "4" in result


class TestProfitLoss:
    def test_pnl_contains_revenue(self, ledger):
        report = ReportGenerator(ledger)
        output = report.profit_and_loss()
        assert "Revenue" in output
        assert "Net Income" in output
        assert "$1,000.00" in output  # Jan revenue
        assert "$2,000.00" in output  # Mar revenue

    def test_pnl_contains_expenses(self, ledger):
        report = ReportGenerator(ledger)
        output = report.profit_and_loss()
        assert "Office Supplies" in output
        assert "Rent Expense" in output

    def test_pnl_calculates_net_income(self, ledger):
        report = ReportGenerator(ledger)
        output = report.profit_and_loss()
        # Revenue: 1000 + 2000 = 3000
        # Expenses: 200 + 800 = 1000
        # Net: 2000
        assert "$2,000.00" in output

    def test_pnl_with_date_filter(self, ledger):
        report = ReportGenerator(ledger)
        output = report.profit_and_loss("2026-01-01", "2026-01-31")
        assert "January sale" not in output  # description not shown
        # Only Jan revenue (1000), no expenses
        assert "Total Revenue" in output


class TestBalanceSheet:
    def test_balance_sheet_contains_assets(self, ledger):
        report = ReportGenerator(ledger)
        output = report.balance_sheet()
        assert "Cash" in output
        assert "Total Assets" in output

    def test_balance_sheet_contains_liabilities(self, ledger):
        report = ReportGenerator(ledger)
        output = report.balance_sheet()
        assert "Accounts Payable" in output
        assert "Total Liabilities" in output

    def test_balance_sheet_contains_equity(self, ledger):
        report = ReportGenerator(ledger)
        output = report.balance_sheet()
        assert "Owner Equity" in output
        assert "Total Equity" in output


class TestCashFlow:
    def test_cash_flow_generates(self, ledger):
        report = ReportGenerator(ledger)
        output = report.cash_flow("2026-01-01", "2026-12-31")
        assert "Operating Activities" in output
        assert "Investing Activities" in output
        assert "Financing Activities" in output
        assert "Net Cash Flow" in output


class TestByProject:
    def test_by_project_lists_projects(self, ledger):
        report = ReportGenerator(ledger)
        output = report.by_project()
        assert "acme" in output
        assert "beta" in output

    def test_by_project_shows_profit(self, ledger):
        report = ReportGenerator(ledger)
        output = report.by_project()
        # acme: revenue 1000, expenses 200, profit 800
        assert "$800.00" in output

    def test_by_project_no_tags(self, tmp_path):
        storage = LedgerStorage(tmp_path / "empty.json")
        storage.init()
        led = Ledger(storage)
        led.add_account("Cash", "asset")
        led.add_account("Revenue", "revenue")
        led.add_transaction(Transaction(
            date="2026-01-15", description="Sale",
            entries=[
                Entry(account="Cash", debit=Decimal("100")),
                Entry(account="Revenue", credit=Decimal("100")),
            ],
        ))
        report = ReportGenerator(led)
        output = report.by_project()
        assert "No tagged transactions" in output


class TestAccountBalances:
    def test_account_balances_lists_all(self, ledger):
        report = ReportGenerator(ledger)
        output = report.account_balances()
        assert "Cash" in output
        assert "Revenue" in output
        assert "Office Supplies" in output
