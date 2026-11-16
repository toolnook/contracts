import tempfile
import unittest
from datetime import date
from decimal import Decimal
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from ledgerlite.asset_scope import (
    AssetScopeInputError,
    Snapshot,
    load_snapshot,
    compare_snapshots,
)
from ledgerlite.asset_scope_cli import main


def snapshot(source, amount, as_of):
    return Snapshot(
        source,
        Decimal(amount),
        date.fromisoformat(as_of),
        1,
        f"{source}.csv",
        "0" * 64,
    )


class AssetScopeTests(unittest.TestCase):
    def setUp(self):
        self.onchain = snapshot("onchain", "100", "2026-11-01")
        self.ledger = snapshot("ledger", "100", "2026-11-01")
        self.reserves = snapshot("reserves", "105", "2026-11-01")

    def test_equal_snapshots_with_adequate_reported_reserves_pass(self):
        report = compare_snapshots(
            asset_code="USD",
            asset_issuer="GISSUER",
            onchain=self.onchain,
            ledger=self.ledger,
            reserves=self.reserves,
        )
        self.assertEqual(report.status, "reconciled")
        self.assertEqual(report.onchain_ledger_difference, Decimal("0"))
        self.assertEqual(report.reserve_liability_difference, Decimal("5"))

    def test_mismatch_and_reserve_shortfall_are_both_reported(self):
        report = compare_snapshots(
            asset_code="USD",
            asset_issuer="GISSUER",
            onchain=self.onchain,
            ledger=snapshot("ledger", "101", "2026-11-01"),
            reserves=snapshot("reserves", "99", "2026-11-01"),
        )
        self.assertEqual(report.status, "needs_review")
        self.assertEqual(len(report.findings), 2)

    def test_snapshot_date_difference_requires_review(self):
        report = compare_snapshots(
            asset_code="USD",
            asset_issuer="GISSUER",
            onchain=self.onchain,
            ledger=snapshot("ledger", "100", "2026-11-02"),
            reserves=self.reserves,
        )
        self.assertEqual(report.status, "needs_review")
        self.assertIn("different as_of dates", report.findings[0])

    def test_tolerance_is_applied_to_comparisons(self):
        report = compare_snapshots(
            asset_code="USD",
            asset_issuer="GISSUER",
            onchain=self.onchain,
            ledger=snapshot("ledger", "100.01", "2026-11-01"),
            reserves=snapshot("reserves", "100", "2026-11-01"),
            tolerance=Decimal("0.01"),
        )
        self.assertEqual(report.status, "reconciled")

    def test_duplicate_source_reference_is_rejected(self):
        content = (
            "asset_code,asset_issuer,amount_in_issued_asset_units,as_of,source_ref\n"
            "USD,GISSUER,10,2026-11-01,account-1\n"
            "USD,GISSUER,10,2026-11-01,account-1\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.csv"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(AssetScopeInputError, "duplicate source_ref"):
                load_snapshot(
                    path,
                    source="onchain",
                    asset_code="USD",
                    asset_issuer="GISSUER",
                )

    def test_amount_must_be_finite_and_non_negative(self):
        for value in ("NaN", "-1"):
            content = (
                "asset_code,asset_issuer,amount_in_issued_asset_units,as_of,source_ref\n"
                f"USD,GISSUER,{value},2026-11-01,account-1\n"
            )
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "snapshot.csv"
                path.write_text(content, encoding="utf-8")
                with self.assertRaisesRegex(AssetScopeInputError, "finite and non-negative"):
                    load_snapshot(
                        path,
                        source="onchain",
                        asset_code="USD",
                        asset_issuer="GISSUER",
                    )

    def test_cli_writes_a_provenance_report(self):
        header = "asset_code,asset_issuer,amount_in_issued_asset_units,as_of,source_ref\n"
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, amount in (("onchain", "100"), ("ledger", "100"), ("reserves", "101")):
                path = Path(directory) / f"{name}.csv"
                path.write_text(
                    header + f"USD,GISSUER,{amount},2026-11-01,{name}-row-1\n",
                    encoding="utf-8",
                )
                paths.append(path)

            output = StringIO()
            with redirect_stdout(output):
                result = main([
                    "--asset-code", "USD",
                    "--asset-issuer", "GISSUER",
                    "--onchain", str(paths[0]),
                    "--ledger", str(paths[1]),
                    "--reserves", str(paths[2]),
                ])

        report = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(report["status"], "reconciled")
        self.assertEqual(len(report["sources"]["onchain"]["file_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
