"""Tests for the CLI interface."""

import pytest
import sys
from decimal import Decimal
from ledgerlite.cli import build_parser
from ledgerlite.storage import LedgerStorage
from ledgerlite.ledger import Ledger
from ledgerlite.models import Account, Entry, Transaction
from ledgerlite.reports import ReportGenerator


@pytest.fixture
def setup_ledger(tmp_path, monkeypatch):
    """Set up a test ledger and return its path."""
    path = tmp_path / "test.json"
    storage = LedgerStorage(path)
    storage.init()
    led = Ledger(storage)
    led.add_account("Cash", "asset")
    led.add_account("Revenue", "revenue")
    led.add_account("Office Supplies", "expense")
    led.add_transaction(Transaction(
        date="2026-01-15", description="January sale", tags=["acme"],
        entries=[
            Entry(account="Cash", debit=Decimal("1000")),
            Entry(account="Revenue", credit=Decimal("1000")),
        ],
    ))
    return str(path)


class TestCLIParser:
    def test_parser_has_init_command(self):
        parser = build_parser()
        args = parser.parse_args(["init"])
        assert args.command == "init"

    def test_parser_has_add_command(self):
        parser = build_parser()
        args = parser.parse_args([
            "add", "--description", "Test",
            "--debit", "Cash:100",
            "--credit", "Revenue:100",
        ])
        assert args.command == "add"
        assert args.description == "Test"
        assert args.debit == ["Cash:100"]
        assert args.credit == ["Revenue:100"]

    def test_parser_has_balance_command(self):
        parser = build_parser()
        args = parser.parse_args(["balance"])
        assert args.command == "balance"

    def test_parser_has_query_command(self):
        parser = build_parser()
        args = parser.parse_args(["query", "from=2026-01-01", "tag=acme"])
        assert args.command == "query"
        assert args.filter == ["from=2026-01-01", "tag=acme"]

    def test_parser_has_report_command(self):
        parser = build_parser()
        args = parser.parse_args(["report", "pnl"])
        assert args.command == "report"
        assert args.type == "pnl"

    def test_parser_report_cashflow(self):
        parser = build_parser()
        args = parser.parse_args([
            "report", "cashflow", "--from", "2026-01-01", "--to", "2026-12-31"
        ])
        assert args.type == "cashflow"
        assert args.from_date == "2026-01-01"

    def test_parser_has_account_add(self):
        parser = build_parser()
        args = parser.parse_args(["account", "add", "Equipment", "asset"])
        assert args.command == "account"
        assert args.subcommand == "add"
        assert args.name == "Equipment"

    def test_parser_has_import_csv(self):
        parser = build_parser()
        args = parser.parse_args(["import", "csv", "data.csv"])
        assert args.command == "import"
        assert args.subcommand == "csv"
        assert args.file == "data.csv"

    def test_parser_has_recurring_add(self):
        parser = build_parser()
        args = parser.parse_args([
            "recurring", "add",
            "--description", "Rent",
            "--frequency", "monthly",
            "--debit", "Rent Expense:2000",
            "--credit", "Cash:2000",
        ])
        assert args.command == "recurring"
        assert args.frequency == "monthly"

    def test_ledger_path_from_args(self):
        parser = build_parser()
        args = parser.parse_args(["-l", "/tmp/test.json", "balance"])
        assert args.ledger == "/tmp/test.json"
