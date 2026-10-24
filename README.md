# LedgerLite

A local-first, file-based double-entry accounting ledger CLI for small teams and freelancers. No database required — uses a structured JSON file format that's human-readable and git-friendly. Designed for tracking income, expenses, and project-based profitability.

## What it does

LedgerLite is a command-line bookkeeping tool that:

- **Enforces double-entry bookkeeping** — every transaction must balance (debits == credits)
- **Stores data in plain JSON** — human-readable, diff-friendly, no database
- **Supports project tagging** — tag transactions to projects and track per-project profitability
- **Generates financial reports** — P&L, Balance Sheet, Cash Flow in terminal table format
- **Imports from CSV** — bulk import transactions from spreadsheet exports
- **Schedules recurring transactions** — auto-generate entries for rent, subscriptions, etc.

## Why it exists

Most accounting software is either a heavy SaaS product (QuickBooks, Xero) or a complex desktop app (GnuCash). Freelancers and small teams often just need to track income, expenses, and project profitability in a format that works with version control. LedgerLite stores everything in a single JSON file that you can commit alongside your project code.

## Quick start

```bash
# Install
pip install ledgerlite

# Initialize a new ledger
ledgerlite init

# Create accounts
ledgerlite account add Cash asset
ledgerlite account add Revenue revenue
ledgerlite account add Office Supplies expense

# Add a transaction
ledgerlite add --description "Client invoice" --debit Cash:1000 --credit Revenue:1000 --tag "acme-project"

# Check balances
ledgerlite balance

# Generate a P&L report
ledgerlite report pnl

# See project profitability
ledgerlite report by-project
```

## Commands

### `ledgerlite init`
Initialize a new ledger file. Creates an empty JSON structure at `~/.ledgerlite/ledger.json` (or a custom path with `-l`).

### `ledgerlite account add <name> <type>`
Add an account. Types: `asset`, `liability`, `equity`, `revenue`, `expense`.

### `ledgerlite account list`
List all accounts with current balances.

### `ledgerlite add`
Add a transaction. Debits and credits are specified as `account:amount` pairs.

```bash
ledgerlite add \
  --description "Office supplies purchase" \
  --date 2026-01-20 \
  --debit "Office Supplies:50.00" \
  --credit "Cash:50.00" \
  --tag "acme-project"
```

### `ledgerlite balance`
Show all account balances, or a specific account with `--account`.

### `ledgerlite query`
Filter transactions with key=value filters.

```bash
ledgerlite query from=2026-01-01 to=2026-06-30 tag=acme-project
```

Supported filters: `from`, `to`, `account`, `tag`, `description`, `payee`.

### `ledgerlite report <type>`
Generate financial reports:
- `pnl` — Profit & Loss statement
- `balance` — Balance Sheet
- `cashflow` — Cash Flow statement (requires `--from` and `--to`)
- `by-project` — Per-project profitability breakdown

### `ledgerlite import csv <file>`
Import transactions from a CSV file. Expected columns: `date,description,payee,debit_account,credit_account,amount,tag`.

### `ledgerlite recurring add`
Register a recurring transaction template for auto-generation.

### `ledgerlite recurring generate`
Generate transactions from recurring templates for a date range.

```bash
ledgerlite recurring generate --from 2026-01-01 --to 2026-12-31 --all
```

## Data format

The ledger file is a single JSON document:

```json
{
  "accounts": [
    {"name": "Cash", "type": "asset", "description": ""}
  ],
  "transactions": [
    {
      "id": "a1b2c3d4e5f6",
      "date": "2026-01-15",
      "description": "Client invoice",
      "payee": "ACME Corp",
      "tags": ["acme-project"],
      "entries": [
        {"account": "Cash", "debit": "1000.00", "credit": "0"},
        {"account": "Revenue", "debit": "0", "credit": "1000.00"}
      ]
    }
  ],
  "recurring": []
}
```

## Architecture overview

```
┌──────────────────────────────────────────────────┐
│                   CLI (cli.py)                     │
│  argparse-based command dispatcher                │
├──────────────────────────────────────────────────┤
│                  Ledger (ledger.py)                │
│  Double-entry validation, balance calculations,  │
│  project profitability                           │
├───────────────┬──────────────┬────────────────────┤
│   Storage      │   Query      │   Reports          │
│ (storage.py)  │ (query.py)   │ (reports.py)      │
│ JSON I/O      │ Filtering    │ P&L, Balance,     │
│               │              │ Cash Flow          │
├───────────────┴──────────────┴────────────────────┤
│              Models (models.py)                    │
│  Account, Entry, Transaction, RecurringTemplate  │
├──────────────────────────────────────────────────┤
│        CSV Import       │   Recurring Scheduler   │
│       (csv_import.py)   │   (recurring.py)        │
└────────────────────────┴─────────────────────────┘
```

| Module | Responsibility |
|--------|---------------|
| `models.py` | Data classes (Account, Entry, Transaction, RecurringTemplate) |
| `storage.py` | JSON file read/write |
| `ledger.py` | Double-entry validation, balance calculation, project tracking |
| `query.py` | Transaction filtering by date, account, tag, payee |
| `reports.py` | P&L, Balance Sheet, Cash Flow, by-project reports |
| `csv_import.py` | CSV import and export |
| `recurring.py` | Recurring transaction scheduling and generation |
| `cli.py` | Command-line interface (argparse) |

## Unique features

### Project tagging

Every transaction can be tagged to one or more projects. The `report by-project` command shows revenue, expenses, and net profit per project:

```
Project Profitability

Project         Revenue        Expenses       Profit
─────────────────────────────────────────────────────
acme            $1,000.00      $200.00        $800.00
beta            $2,000.00      $0.00          $2,000.00
```

### Recurring transactions

Define a template once and generate entries for a date range:

```bash
ledgerlite recurring add \
  --description "Monthly office rent" \
  --frequency monthly \
  --debit "Rent Expense:2000" \
  --credit "Cash:2000"

ledgerlite recurring generate --from 2026-01-01 --to 2026-12-31 --all
```

Supported frequencies: `daily`, `weekly`, `monthly`, `yearly`.

## Running tests

```bash
pip install -e ".[dev]"  # or: pip install pytest
pytest -v
```

## Roadmap

- [ ] Multi-currency support
- [ ] Budget tracking and alerts
- [ ] Receipt attachment support
- [ ] Web UI for browsing transactions
- [ ] Export to QIF/OFX formats
- [ ] Tax category mapping

## License

MIT — see [LICENSE](LICENSE).
