# Changelog

All notable changes to LedgerLite are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-11-03

### Added
- Stellar Horizon payment sync — fetch XLM and asset payments from Horizon API
- Payment reconciliation — converts on-chain payments to balanced double-entry transactions
- Stellar account ID validation and network passphrase support
- Stroop-to-XLM conversion with Decimal precision
- Multi-asset support (XLM native, USDC, EURT, custom assets)
- Double-entry transaction model with automatic balance validation
- JSON file-based storage (human-readable, git-friendly)
- Account management with five standard types
- CLI with subcommands: init, account, add, balance, query, report, import, recurring, stellar sync
- Transaction filtering by date range, account, tag, description, and payee
- Financial reports: P&L, Balance Sheet, Cash Flow, by-project
- Project tagging system with per-project profitability report
- Recurring transaction scheduler (daily, weekly, monthly, yearly)
- CSV import and export
- Terminal table formatting for reports
- Full test suite including Stellar module tests
- CI workflow for GitHub Actions
- Issue templates and PR template

[0.1.0]: https://github.com/toolnook/contracts/releases/tag/v0.1.0
