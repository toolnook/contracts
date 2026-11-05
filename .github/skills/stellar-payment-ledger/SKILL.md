---
name: stellar-payment-ledger
description: Use when working on Toolnook Contracts' local accounting ledger, Stellar payment sync, reconciliation, or financial reports.
---

# Stellar payment ledger

Help maintain the local-first double-entry ledger and its Stellar Horizon payment import.

- Read the existing models, CLI command, storage format, and tests before changing ledger behavior.
- Preserve balanced debits and credits, use `Decimal` for monetary values, and follow existing duplicate/import handling.
- Clearly distinguish payment data fetched from Horizon from bookkeeping classifications entered by a person. Do not assume every incoming payment is revenue.
- Use public account addresses in examples, never secret keys. Make the selected network explicit and keep public network and testnet data separate.
- Explain terms such as account, debit, credit, ledger, and reconciliation in plain language in user-facing docs.
- Add focused tests for behavior changes and run the relevant pytest suite. Do not include credentials or add contributor/author entries that were not requested.
