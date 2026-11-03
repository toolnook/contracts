# Toolnook Contracts

The financial contracts layer for the Toolnook platform. A local-first, file-based double-entry accounting CLI for tracking income, expenses, and project-based profitability. No database required.

Part of the [Toolnook](https://github.com/toolnook) open-source developer infrastructure platform:

| Repo | Role |
|------|------|
| [toolnook/backend](https://github.com/toolnook/backend) | API gateway, reverse proxy, rate limiting, circuit breaker |
| [toolnook/frontend](https://github.com/toolnook/frontend) | Documentation-as-code generator with dependency graphs |
| **toolnook/contracts** | Double-entry accounting CLI with project profitability |

## What it does

Toolnook Contracts is a command-line bookkeeping tool that:

- **Enforces** double-entry bookkeeping — every transaction must balance
- **Stores** data in plain JSON — human-readable, git-friendly
- **Tags** transactions to projects and tracks per-project profitability
- **Generates** P&L, Balance Sheet, and Cash Flow reports
- **Imports** transactions from CSV
- **Schedules** recurring transactions (rent, subscriptions, etc.)

## Quick start

```bash
git clone https://github.com/toolnook/contracts.git
cd contracts
pip install -e .

# Initialize
ledgerlite init

# Create accounts
ledgerlite account add Cash asset
ledgerlite account add Revenue revenue

# Add a transaction
ledgerlite add --description "Client invoice" --debit Cash:1000 --credit Revenue:1000 --tag "acme"

# Check balances
ledgerlite balance

# P&L report
ledgerlite report pnl

# Project profitability
ledgerlite report by-project
```

## Commands

| Command | Description |
|---------|-------------|
| `ledgerlite init` | Initialize a new ledger |
| `ledgerlite account add <name> <type>` | Add account (asset/liability/equity/revenue/expense) |
| `ledgerlite account list` | List accounts with balances |
| `ledgerlite add` | Add a transaction |
| `ledgerlite balance` | Show account balances |
| `ledgerlite query` | Filter transactions (`from=2026-01-01 tag=acme`) |
| `ledgerlite report pnl` | Profit & Loss statement |
| `ledgerlite report balance` | Balance Sheet |
| `ledgerlite report cashflow` | Cash Flow statement |
| `ledgerlite report by-project` | Per-project profitability |
| `ledgerlite import csv <file>` | Import from CSV |
| `ledgerlite recurring add` | Register a recurring template |
| `ledgerlite recurring generate` | Generate recurring entries |

## Architecture

```
CLI (cli.py)
    ↓
Ledger (ledger.py) ← double-entry validation, balances, project profitability
    ↓
Storage (storage.py) ← JSON file I/O
    
Query (query.py) ← filtering by date/account/tag
Reports (reports.py) ← P&L, balance sheet, cash flow, by-project
CSV Import (csv_import.py) ← bulk import/export
Recurring (recurring.py) ← scheduled transaction generation
```

## Running tests

```bash
pip install -e ".[dev]"
pytest -v
```

## Roadmap

- [ ] Multi-currency support
- [ ] Budget tracking and alerts
- [ ] Web UI for browsing transactions
- [ ] Tax category mapping

## License

MIT — see [LICENSE](LICENSE).
