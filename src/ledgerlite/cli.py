#!/usr/bin/env python3
"""
Command-line interface for LedgerLite.

Commands:
    ledgerlite init                    Initialize a new ledger file
    ledgerlite account add             Add an account to the chart of accounts
    ledgerlite account list            List all accounts
    ledgerlite add                     Add a transaction
    ledgerlite balance                 Show account balances
    ledgerlite query                    Query transactions with filters
    ledgerlite report                   Generate financial reports
    ledgerlite import csv               Import transactions from CSV
    ledgerlite recurring add            Add a recurring transaction template
    ledgerlite recurring generate       Generate recurring transactions
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from . import __version__
from .models import Account, Entry, Transaction, RecurringTemplate
from .storage import LedgerStorage
from .ledger import Ledger
from .query import Query, QueryFilter, parse_query
from .reports import ReportGenerator
from .csv_import import import_csv
from .recurring import RecurringScheduler


def get_ledger_path(args: argparse.Namespace) -> Path:
    """Determine the ledger file path from args or default."""
    if hasattr(args, "ledger") and args.ledger:
        return Path(args.ledger)
    env = Path.home() / ".ledgerlite" / "ledger.json"
    return env


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize a new ledger file."""
    path = get_ledger_path(args)
    storage = LedgerStorage(path)
    if storage.exists() and not args.force:
        print(f"Ledger already exists at {path}. Use --force to overwrite.")
        sys.exit(1)
    storage.init()
    print(f"Initialized ledger at {path}")


def cmd_account_add(args: argparse.Namespace) -> None:
    """Add an account."""
    path = get_ledger_path(args)
    storage = LedgerStorage(path)
    ledger = Ledger(storage)
    try:
        ledger.add_account(args.name, args.type, args.description)
        print(f"Added account: {args.name} ({args.type})")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_account_list(args: argparse.Namespace) -> None:
    """List all accounts."""
    path = get_ledger_path(args)
    storage = LedgerStorage(path)
    ledger = Ledger(storage)
    accounts = ledger.list_accounts()
    if not accounts:
        print("No accounts found. Use 'ledgerlite account add' to create one.")
        return
    print(f"{'Account':<30} {'Type':<15} {'Balance':>15}")
    print("─" * 62)
    for acct in accounts:
        bal = ledger.get_account_balance(acct.name)
        print(f"{acct.name:<30} {acct.type:<15} {bal:>15,.2f}")


def cmd_add(args: argparse.Namespace) -> None:
    """Add a transaction."""
    path = get_ledger_path(args)
    storage = LedgerStorage(path)
    ledger = Ledger(storage)

    entries: list[Entry] = []

    # Parse debit entries: "Account:amount"
    for d in args.debit:
        if ":" not in d:
            print(f"Error: invalid debit '{d}'. Expected account:amount")
            sys.exit(1)
        acct, amt = d.rsplit(":", 1)
        entries.append(Entry(account=acct.strip(), debit=Decimal(amt.strip())))

    for c in args.credit:
        if ":" not in c:
            print(f"Error: invalid credit '{c}'. Expected account:amount")
            sys.exit(1)
        acct, amt = c.rsplit(":", 1)
        entries.append(Entry(account=acct.strip(), credit=Decimal(amt.strip())))

    tags = [t.strip() for t in args.tag.split(",")] if args.tag else []

    txn = Transaction(
        date=args.date or datetime.now().strftime("%Y-%m-%d"),
        description=args.description,
        payee=args.payee or "",
        tags=tags,
        entries=entries,
    )

    try:
        ledger.add_transaction(txn)
        print(f"Added transaction: {txn.id} — {txn.description}")
        print(f"  Debits:  {txn.total_debit}")
        print(f"  Credits: {txn.total_credit}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_balance(args: argparse.Namespace) -> None:
    """Show account balances."""
    path = get_ledger_path(args)
    storage = LedgerStorage(path)
    ledger = Ledger(storage)
    report = ReportGenerator(ledger)

    if args.account:
        bal = ledger.get_account_balance(args.account)
        print(f"{args.account}: {bal:,.2f}")
    else:
        print(report.account_balances())


def cmd_query(args: argparse.Namespace) -> None:
    """Query transactions."""
    path = get_ledger_path(args)
    storage = LedgerStorage(path)
    ledger = Ledger(storage)
    transactions = ledger.get_transactions()

    try:
        qf = parse_query(args.filter)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    results = Query(transactions).filter(qf)
    if not results:
        print("No transactions found matching the query.")
        return

    print(f"Found {len(results)} transaction(s):\n")
    print(f"{'ID':<14} {'Date':<12} {'Description':<35} {'Debit':>10} {'Credit':>10} {'Tags'}")
    print("─" * 95)
    for txn in results:
        tag_str = ",".join(txn.tags) if txn.tags else ""
        print(
            f"{txn.id:<14} {txn.date:<12} {txn.description:<35} "
            f"{str(txn.total_debit):>10} {str(txn.total_credit):>10} {tag_str}"
        )


def cmd_report(args: argparse.Namespace) -> None:
    """Generate financial reports."""
    path = get_ledger_path(args)
    storage = LedgerStorage(path)
    ledger = Ledger(storage)
    report = ReportGenerator(ledger)

    if args.type == "pnl":
        print(report.profit_and_loss(args.from_date, args.to_date))
    elif args.type == "balance":
        print(report.balance_sheet(args.to_date))
    elif args.type == "cashflow":
        if not args.from_date or not args.to_date:
            print("Error: cashflow report requires --from and --to dates")
            sys.exit(1)
        print(report.cash_flow(args.from_date, args.to_date))
    elif args.type == "by-project":
        print(report.by_project(args.from_date, args.to_date))
    else:
        print(f"Unknown report type: {args.type}")
        print("Available: pnl, balance, cashflow, by-project")
        sys.exit(1)


def cmd_import_csv(args: argparse.Namespace) -> None:
    """Import transactions from CSV."""
    path = get_ledger_path(args)
    storage = LedgerStorage(path)
    ledger = Ledger(storage)

    try:
        txns = import_csv(args.file, ledger, skip_header=not args.no_header)
        print(f"Imported {len(txns)} transaction(s) from {args.file}")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_recurring_add(args: argparse.Namespace) -> None:
    """Add a recurring transaction template."""
    path = get_ledger_path(args)
    storage = LedgerStorage(path)
    ledger = Ledger(storage)
    scheduler = RecurringScheduler(ledger)

    entries: list[Entry] = []
    for d in args.debit:
        acct, amt = d.rsplit(":", 1)
        entries.append(Entry(account=acct.strip(), debit=Decimal(amt.strip())))
    for c in args.credit:
        acct, amt = c.rsplit(":", 1)
        entries.append(Entry(account=acct.strip(), credit=Decimal(amt.strip())))

    tags = [t.strip() for t in args.tag.split(",")] if args.tag else []

    template = RecurringTemplate(
        description=args.description,
        frequency=args.frequency,
        entries=entries,
        tags=tags,
        payee=args.payee or "",
    )

    try:
        scheduler.add_template(template)
        print(f"Added recurring template: {template.id} — {template.description} ({template.frequency})")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_recurring_generate(args: argparse.Namespace) -> None:
    """Generate recurring transactions for a date range."""
    path = get_ledger_path(args)
    storage = LedgerStorage(path)
    ledger = Ledger(storage)
    scheduler = RecurringScheduler(ledger)

    try:
        if args.all:
            txns = scheduler.generate_all(args.from_date, args.to_date)
        else:
            templates = scheduler.get_templates()
            if not templates:
                print("No recurring templates found.")
                return
            txns = []
            for template in templates:
                txns.extend(scheduler.generate(template, args.from_date, args.to_date))
            if txns:
                ledger.add_transactions(txns)

        print(f"Generated {len(txns)} transaction(s) from {args.from_date} to {args.to_date}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_stellar_sync(args: argparse.Namespace) -> None:
    """Sync XLM and asset payments from Stellar Horizon API."""
    path = get_ledger_path(args)
    storage = LedgerStorage(path)
    ledger = Ledger(storage)

    from .stellar import HorizonClient, reconcile_payments, is_valid_account_id

    if not is_valid_account_id(args.account):
        print(f"Error: invalid Stellar account ID: {args.account}")
        print("Account IDs start with 'G' and are 56 characters long.")
        sys.exit(1)

    client = HorizonClient(network=args.network)
    print(f"Fetching payments for {args.account} from Horizon ({args.network})...")

    try:
        payments = client.get_all_payments(args.account, max_records=args.limit)
        if not payments:
            print(f"No payments found for {args.account}")
            return

        txns = reconcile_payments(payments)
        ledger.add_transactions(txns)
        total_xlm = sum(
            p.amount for p in payments if p.is_native()
        )
        print(f"Synced {len(txns)} payment(s) from Horizon")
        if total_xlm:
            print(f"  Total XLM: {total_xlm}")
        print(f"  Network: {args.network}")
    except Exception as e:
        print(f"Error syncing from Horizon: {e}")
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="ledgerlite",
        description="A local-first, file-based double-entry accounting ledger CLI.",
    )
    parser.add_argument("--version", action="version", version=f"ledgerlite {__version__}")
    parser.add_argument("-l", "--ledger", help="Path to the ledger JSON file")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    init_parser = subparsers.add_parser("init", help="Initialize a new ledger")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing ledger")
    init_parser.set_defaults(func=cmd_init)

    # account
    acct_parser = subparsers.add_parser("account", help="Manage accounts")
    acct_sub = acct_parser.add_subparsers(dest="subcommand", required=True)

    acct_add = acct_sub.add_parser("add", help="Add an account")
    acct_add.add_argument("name", help="Account name")
    acct_add.add_argument("type", choices=["asset", "liability", "equity", "revenue", "expense"])
    acct_add.add_argument("--description", default="", help="Account description")
    acct_add.set_defaults(func=cmd_account_add)

    acct_list = acct_sub.add_parser("list", help="List all accounts")
    acct_list.set_defaults(func=cmd_account_list)

    # add transaction
    add_parser = subparsers.add_parser("add", help="Add a transaction")
    add_parser.add_argument("--date", help="Transaction date (YYYY-MM-DD, default: today)")
    add_parser.add_argument("--description", required=True, help="Transaction description")
    add_parser.add_argument("--payee", help="Payee name")
    add_parser.add_argument("--debit", nargs="+", required=True, help="Debit entries as account:amount")
    add_parser.add_argument("--credit", nargs="+", required=True, help="Credit entries as account:amount")
    add_parser.add_argument("--tag", help="Project tags (comma-separated)")
    add_parser.set_defaults(func=cmd_add)

    # balance
    bal_parser = subparsers.add_parser("balance", help="Show account balances")
    bal_parser.add_argument("--account", help="Show balance for a specific account")
    bal_parser.set_defaults(func=cmd_balance)

    # query
    query_parser = subparsers.add_parser("query", help="Query transactions")
    query_parser.add_argument("filter", nargs="*", help="Filters as key=value (from, to, account, tag, description, payee)")
    query_parser.set_defaults(func=cmd_query)

    # report
    report_parser = subparsers.add_parser("report", help="Generate reports")
    report_parser.add_argument("type", choices=["pnl", "balance", "cashflow", "by-project"], help="Report type")
    report_parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    report_parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    report_parser.set_defaults(func=cmd_report)

    # import
    import_parser = subparsers.add_parser("import", help="Import data")
    import_sub = import_parser.add_subparsers(dest="subcommand", required=True)
    csv_parser = import_sub.add_parser("csv", help="Import transactions from CSV")
    csv_parser.add_argument("file", help="Path to the CSV file")
    csv_parser.add_argument("--no-header", action="store_true", help="CSV has no header row")
    csv_parser.set_defaults(func=cmd_import_csv)

    # recurring
    recurring_parser = subparsers.add_parser("recurring", help="Manage recurring transactions")
    recurring_sub = recurring_parser.add_subparsers(dest="subcommand", required=True)

    rec_add = recurring_sub.add_parser("add", help="Add a recurring template")
    rec_add.add_argument("--description", required=True, help="Transaction description")
    rec_add.add_argument("--frequency", required=True, choices=["daily", "weekly", "monthly", "yearly"])
    rec_add.add_argument("--debit", nargs="+", required=True, help="Debit entries as account:amount")
    rec_add.add_argument("--credit", nargs="+", required=True, help="Credit entries as account:amount")
    rec_add.add_argument("--payee", help="Payee name")
    rec_add.add_argument("--tag", help="Project tags (comma-separated)")
    rec_add.set_defaults(func=cmd_recurring_add)

    rec_gen = recurring_sub.add_parser("generate", help="Generate recurring transactions")
    rec_gen.add_argument("--from", dest="from_date", required=True, help="Start date")
    rec_gen.add_argument("--to", dest="to_date", required=True, help="End date")
    rec_gen.add_argument("--all", action="store_true", help="Generate for all templates")
    rec_gen.set_defaults(func=cmd_recurring_generate)

    # stellar
    stellar_parser = subparsers.add_parser("stellar", help="Sync Stellar payments from Horizon")
    stellar_sub = stellar_parser.add_subparsers(dest="subcommand", required=True)

    stellar_sync = stellar_sub.add_parser("sync", help="Sync XLM payments from Horizon API")
    stellar_sync.add_argument("--account", required=True, help="Stellar account ID (G...)")
    stellar_sync.add_argument("--network", default="public", choices=["public", "testnet"], help="Stellar network")
    stellar_sync.add_argument("--limit", type=int, default=1000, help="Max records to fetch")
    stellar_sync.set_defaults(func=cmd_stellar_sync)

    return parser


def main() -> None:
    """Entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
