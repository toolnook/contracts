"""Command-line entry point for AssetScope."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence

from .asset_scope import AssetScopeInputError, compare_csv_snapshots


def _decimal_argument(value: str) -> Decimal:
    try:
        amount = Decimal(value)
    except InvalidOperation as error:
        raise argparse.ArgumentTypeError("must be a decimal number") from error
    if not amount.is_finite() or amount < 0:
        raise argparse.ArgumentTypeError("must be finite and non-negative")
    return amount


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="asset-scope",
        description="Compare normalized on-chain, ledger, and reserve CSV snapshots.",
    )
    parser.add_argument("--asset-code", required=True, help="Issued asset code")
    parser.add_argument(
        "--asset-issuer",
        default="",
        help="Issued asset issuer public key (empty for native XLM)",
    )
    parser.add_argument("--onchain", required=True, help="On-chain balance snapshot CSV")
    parser.add_argument("--ledger", required=True, help="Ledger liability snapshot CSV")
    parser.add_argument("--reserves", required=True, help="Reserve valuation snapshot CSV")
    parser.add_argument(
        "--tolerance",
        type=_decimal_argument,
        default=Decimal("0"),
        help="Allowed amount difference, in issued-asset units (default: 0)",
    )
    parser.add_argument("--output", type=Path, help="Write JSON report to this path instead of stdout")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = compare_csv_snapshots(
            asset_code=args.asset_code,
            asset_issuer=args.asset_issuer,
            onchain_path=args.onchain,
            ledger_path=args.ledger,
            reserves_path=args.reserves,
            tolerance=args.tolerance,
        )
        rendered = json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0 if report.status == "reconciled" else 1
    except (OSError, ReconciliationInputError) as error:
        print(f"asset-scope: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
