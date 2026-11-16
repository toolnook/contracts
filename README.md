![Toolnook](docs/assets/toolnook-logo.svg)

# Toolnook Contracts

**A small, local-first bookkeeping ledger with Stellar payment sync.** Use it to record transactions, keep debits and credits balanced, and bring payment activity from Stellar Horizon into your ledger.

[Read the beginner-friendly guide](https://toolnook.github.io/contracts/) · [Browse all Toolnook projects](https://github.com/toolnook)

## What does it do?

A ledger is an organized record of money coming in and going out. This command-line tool stores that record in a local file, rather than requiring you to run a database server. Its double-entry rules help make sure each transaction balances.

The optional Stellar sync reads an account's payment history from Horizon and imports it into the ledger. Imported entries should still be reviewed and categorized for your own bookkeeping needs.

## Try it locally

You need Python 3.9 or newer.

```bash
git clone https://github.com/toolnook/contracts.git
cd contracts
python -m pip install -e .
ledgerlite init
ledgerlite account add "Stellar Wallet" asset
ledgerlite account add "XLM Revenue" revenue
ledgerlite balance
```

By default, the ledger is stored under `~/.ledgerlite/ledger.json`. To sync a Stellar account, use its public address (not a secret key):

```bash
ledgerlite stellar sync --account YOUR_STELLAR_PUBLIC_KEY --network testnet
```

Choose `public` only when you intend to use Stellar's public network. Review imported transactions before relying on them for financial reporting.

## Concepts in plain language

| Term | Meaning |
| --- | --- |
| Account | A named category in your books, such as a wallet, income, or expense. |
| Double-entry | Each transaction records equal debits and credits, helping the ledger stay balanced. |
| Horizon | Stellar's HTTP API for looking up accounts and payment history. |
| Reconciliation | Comparing recorded transactions with payment activity to find and resolve differences. |

## AssetScope (early prototype)

`asset-scope` compares three CSV snapshots for one issued asset: on-chain balances, booked liabilities, and reported reserve value. Every amount must already be expressed in the issued asset's units. The tool uses decimal arithmetic, rejects repeated source references, and flags mismatched snapshot dates or balances.

Each CSV uses this header; `source_ref` must be unique within its file. The report includes each input filename and SHA-256 digest so the exact imported files can be identified later:

```csv
asset_code,asset_issuer,amount_in_issued_asset_units,as_of,source_ref
USD,G...,125.50,2026-11-01,statement-row-001
```

Run it after installing the package:

```bash
asset-scope \
  --asset-code USD \
  --asset-issuer YOUR_STELLAR_ISSUER \
  --onchain onchain.csv \
  --ledger liabilities.csv \
  --reserves reserves.csv \
  --output reconciliation.json
```

This first slice compares supplied snapshots; it does not fetch or independently verify them. Reserve valuations must be converted to the issued asset's units before import. A clean report is not proof of reserves, solvency, legal compliance, or an audit opinion.

## Explore and contribute

- [Project guide and examples](https://toolnook.github.io/contracts/)
- [Source code](https://github.com/toolnook/contracts)
- [Report a problem](https://github.com/toolnook/contracts/issues)
- [Contribution guide](CONTRIBUTING.md)

Run the test suite with `pytest -v`. This project is open source under the [MIT License](LICENSE).
