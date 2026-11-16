"""Compare issuer liability, on-chain balance, and reserve snapshot CSVs."""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


CSV_COLUMNS = (
    "asset_code",
    "asset_issuer",
    "amount_in_issued_asset_units",
    "as_of",
    "source_ref",
)


class AssetScopeInputError(ValueError):
    """Raised when an input snapshot is malformed or inconsistent."""


@dataclass(frozen=True)
class Snapshot:
    source: str
    amount: Decimal
    as_of: date
    row_count: int
    file_name: str
    file_sha256: str


@dataclass(frozen=True)
class AssetScopeReport:
    asset_code: str
    asset_issuer: str
    tolerance: Decimal
    onchain: Snapshot
    ledger: Snapshot
    reserves: Snapshot
    status: str
    findings: tuple[str, ...]

    @property
    def onchain_ledger_difference(self) -> Decimal:
        return self.onchain.amount - self.ledger.amount

    @property
    def reserve_liability_difference(self) -> Decimal:
        return self.reserves.amount - self.ledger.amount

    def to_dict(self) -> dict[str, object]:
        return {
            "asset": {
                "code": self.asset_code,
                "issuer": self.asset_issuer,
            },
            "tolerance": str(self.tolerance),
            "sources": {
                "onchain": _snapshot_dict(self.onchain),
                "ledger": _snapshot_dict(self.ledger),
                "reserves": _snapshot_dict(self.reserves),
            },
            "comparisons": {
                "onchain_minus_ledger": str(self.onchain_ledger_difference),
                "reserves_minus_ledger": str(self.reserve_liability_difference),
            },
            "status": self.status,
            "findings": list(self.findings),
            "limitations": [
                "Amounts must already be valued in the issued asset's units.",
                "CSV contents and reserve valuations are not independently verified.",
                "This report is not an attestation of solvency or proof of reserves.",
            ],
        }


def load_snapshot(
    path: str | Path,
    *,
    source: str,
    asset_code: str,
    asset_issuer: str,
) -> Snapshot:
    """Load and sum one asset's rows from a normalized snapshot CSV."""
    csv_path = Path(path)
    try:
        content = csv_path.read_bytes()
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""))
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise AssetScopeInputError(f"{csv_path}: missing or duplicate CSV headers")
        missing = set(CSV_COLUMNS) - set(reader.fieldnames)
        if missing:
            raise AssetScopeInputError(
                f"{csv_path}: missing required columns: {', '.join(sorted(missing))}"
            )

        total = Decimal("0")
        snapshot_date: date | None = None
        seen_refs: set[str] = set()
        row_count = 0
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                raise AssetScopeInputError(
                    f"{csv_path}:{line_number}: unexpected extra CSV fields"
                )
            row_asset_code = (row.get("asset_code") or "").strip()
            row_asset_issuer = (row.get("asset_issuer") or "").strip()
            if (row_asset_code, row_asset_issuer) != (asset_code, asset_issuer):
                raise AssetScopeInputError(
                    f"{csv_path}:{line_number}: asset does not match "
                    f"{asset_code}/{asset_issuer}"
                )

            source_ref = (row.get("source_ref") or "").strip()
            if not source_ref:
                raise AssetScopeInputError(
                    f"{csv_path}:{line_number}: source_ref must not be empty"
                )
            if source_ref in seen_refs:
                raise AssetScopeInputError(
                    f"{csv_path}:{line_number}: duplicate source_ref {source_ref!r}"
                )
            seen_refs.add(source_ref)

            raw_amount = (row.get("amount_in_issued_asset_units") or "").strip()
            try:
                amount = Decimal(raw_amount)
            except InvalidOperation as error:
                raise AssetScopeInputError(
                    f"{csv_path}:{line_number}: invalid amount {raw_amount!r}"
                ) from error
            if not amount.is_finite() or amount < 0:
                raise AssetScopeInputError(
                    f"{csv_path}:{line_number}: amount must be finite and non-negative"
                )

            raw_date = (row.get("as_of") or "").strip()
            try:
                row_date = date.fromisoformat(raw_date)
            except ValueError as error:
                raise AssetScopeInputError(
                    f"{csv_path}:{line_number}: as_of must be an ISO date (YYYY-MM-DD)"
                ) from error
            if snapshot_date is not None and row_date != snapshot_date:
                raise AssetScopeInputError(
                    f"{csv_path}:{line_number}: rows in one file must share the same as_of date"
                )
            snapshot_date = row_date
            total += amount
            row_count += 1
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise AssetScopeInputError(f"cannot read {csv_path}: {error}") from error

    if row_count == 0 or snapshot_date is None:
        raise AssetScopeInputError(f"{csv_path}: snapshot has no data rows")
    return Snapshot(
        source=source,
        amount=total,
        as_of=snapshot_date,
        row_count=row_count,
        file_name=csv_path.name,
        file_sha256=hashlib.sha256(content).hexdigest(),
    )


def compare_snapshots(
    *,
    asset_code: str,
    asset_issuer: str,
    onchain: Snapshot,
    ledger: Snapshot,
    reserves: Snapshot,
    tolerance: Decimal = Decimal("0"),
) -> AssetScopeReport:
    """Compare normalized balances and report discrepancies for review."""
    if not asset_code.strip():
        raise AssetScopeInputError("asset_code must not be empty")
    if not tolerance.is_finite() or tolerance < 0:
        raise AssetScopeInputError("tolerance must be finite and non-negative")

    findings: list[str] = []
    dates = {onchain.as_of, ledger.as_of, reserves.as_of}
    if len(dates) != 1:
        findings.append("Snapshots have different as_of dates; review timing before comparing.")
    if abs(onchain.amount - ledger.amount) > tolerance:
        findings.append("On-chain balance total differs from the ledger liability total.")
    if reserves.amount + tolerance < ledger.amount:
        findings.append("Reported reserve value is below the ledger liability total.")

    status = "reconciled" if not findings else "needs_review"
    return AssetScopeReport(
        asset_code=asset_code,
        asset_issuer=asset_issuer,
        tolerance=tolerance,
        onchain=onchain,
        ledger=ledger,
        reserves=reserves,
        status=status,
        findings=tuple(findings),
    )


def _snapshot_dict(snapshot: Snapshot) -> dict[str, object]:
    return {
        "source": snapshot.source,
        "amount": str(snapshot.amount),
        "as_of": snapshot.as_of.isoformat(),
        "row_count": snapshot.row_count,
        "file_name": snapshot.file_name,
        "file_sha256": snapshot.file_sha256,
    }


def compare_csv_snapshots(
    *,
    asset_code: str,
    asset_issuer: str,
    onchain_path: str | Path,
    ledger_path: str | Path,
    reserves_path: str | Path,
    tolerance: Decimal = Decimal("0"),
) -> AssetScopeReport:
    """Load three CSV snapshots and compare their totals."""
    onchain = load_snapshot(
        onchain_path, source="onchain", asset_code=asset_code, asset_issuer=asset_issuer
    )
    ledger = load_snapshot(
        ledger_path, source="ledger", asset_code=asset_code, asset_issuer=asset_issuer
    )
    reserves = load_snapshot(
        reserves_path, source="reserves", asset_code=asset_code, asset_issuer=asset_issuer
    )
    return compare_snapshots(
        asset_code=asset_code,
        asset_issuer=asset_issuer,
        onchain=onchain,
        ledger=ledger,
        reserves=reserves,
        tolerance=tolerance,
    )
