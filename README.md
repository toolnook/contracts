# Toolnook Contracts — Stellar Payment Ledger

A double-entry accounting CLI that reconciles on-chain XLM and asset payments from the Stellar Horizon API with off-chain bookkeeping. Designed for businesses and freelancers who accept Stellar payments and need to track income, expenses, and project profitability.

Part of the [Toolnook](https://github.com/toolnook) Stellar developer tooling platform:

| Repo | Role |
|------|------|
| [toolnook/backend](https://github.com/toolnook/backend) | Horizon gateway with caching, rate limiting, circuit breaker |
| [toolnook/frontend](https://github.com/toolnook/frontend) | Soroban contract documentation generator |
| **toolnook/contracts** | XLM payment reconciliation and double-entry ledger |

## Why this helps Stellar

Businesses accepting XLM and Stellar assets need a way to track payments, reconcile them with invoices, and report on project profitability — all without a database. Toolnook Contracts:

- **Fetches** payment history from Horizon (XLM native payments, create_account, path_payments)
- **Reconciles** on-chain Stellar payments into double-entry transactions automatically
- **Tracks** XLM and issued assets (USDC, EURT, etc.) alongside each other
- **Tags** payments to projects and reports per-project profitability
- **Generates** P&L, Balance Sheet, and Cash Flow reports
- **Imports** from CSV for off-chain transactions
- **Schedules** recurring entries (monthly subscriptions, rent, etc.)

## Quick start

```bash
git clone https://github.com/toolnook/contracts.git
cd contracts
pip install -e .

# Initialize
ledgerlite init
ledgerlite account add "Stellar Wallet" asset
ledgerlite account add "XLM Revenue" revenue
ledgerlite account add "Operating Expenses" expense

# Sync on-chain XLM payments from Horizon
ledgerlite stellar sync --account GABC...1234 --network public

# Check balances
ledgerlite balance

# P&L report
ledgerlite report pnl

# Project profitability (by Stellar payment tags)
ledgerlite report by-project
```

## Commands

| Command | Description |
|---------|-------------|
| `ledgerlite init` | Initialize a new ledger |
| `ledgerlite account add <name> <type>` | Add account |
| `ledgerlite add` | Add an off-chain transaction |
| `ledgerlite balance` | Show balances |
| `ledgerlite query` | Filter transactions |
| `ledgerlite report pnl` | P&L statement |
| `ledgerlite report balance` | Balance sheet |
| `ledgerlite report cashflow` | Cash flow |
| `ledgerlite report by-project` | Per-project profitability |
| `ledgerlite import csv <file>` | Import from CSV |
| `ledgerlite stellar sync` | Sync XLM payments from Horizon |
| `ledgerlite recurring generate` | Generate recurring entries |

## Stellar sync

```bash
# Sync all payments for a Stellar account from Horizon
ledgerlite stellar sync --account GABC...1234 --network public

# Sync from testnet
ledgerlite stellar sync --account GABC...1234 --network testnet
```

This fetches payment operations from Horizon, converts them to balanced double-entry transactions (debit Stellar Wallet, credit XLM Revenue), and saves them to the ledger file with `stellar` and `xlm` tags.

## Architecture

```
Horizon API → stellar.py → StellarPayment objects → reconcile_payments() → double-entry transactions → ledger
```

| Module | File | What it does |
|--------|------|-------------|
| Stellar sync | `src/ledgerlite/stellar.py` | Fetch XLM/asset payments from Horizon, reconcile to transactions |
| Models | `src/ledgerlite/models.py` | Account, Entry, Transaction with Decimal amounts |
| Ledger | `src/ledgerlite/ledger.py` | Double-entry validation, balance calculation |
| Reports | `src/ledgerlite/reports.py` | P&L, balance sheet, cash flow, by-project |
| CSV import | `src/ledgerlite/csv_import.py` | Import off-chain transactions |
| Recurring | `src/ledgerlite/recurring.py` | Schedule recurring entries |

## Running tests

```bash
pip install -e ".[dev]"
pytest -v
```

## License

MIT — see [LICENSE](LICENSE).
