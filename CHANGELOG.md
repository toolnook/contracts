# Changelog

All notable changes to LedgerLite are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-11-03

### Added
- Double-entry transaction model with automatic balance validation
- JSON file-based storage (human-readable, git-friendly)
- Account management with five standard types (asset, liability, equity, revenue, expense)
- CLI with subcommands: `init`, `add`, `balance`, `query`, `report`, `import`, `recurring`
- Transaction filtering by date range, account, tag, description, and payee
- Financial reports: Profit & Loss, Balance Sheet, Cash Flow
- Project tagging system with per-project profitability report (`report by-project`)
- Recurring transaction scheduler (daily, weekly, monthly, yearly)
- CSV import and export
- Terminal table formatting for reports
- Full test suite (unit + integration)
- CI workflow for GitHub Actions
- Issue templates and PR template

[0.1.0]: https://github.com/toolnook/ledgerlite/releases/tag/v0.1.0
