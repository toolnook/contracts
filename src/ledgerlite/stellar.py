"""
Stellar Horizon integration for the Toolnook Contracts ledger.

Fetches XLM and asset payments from the Stellar Horizon API and
converts them into double-entry transactions that can be added to
the ledger. This bridges on-chain Stellar payments with off-chain
bookkeeping so businesses accepting XLM can reconcile their books.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


# ── Constants ──────────────────────────────────────────────

HORIZON_URLS = {
    "public": "https://horizon.stellar.org",
    "testnet": "https://horizon-testnet.stellar.org",
}

NETWORK_PASSPHRASES = {
    "public": "Public Global Stellar Network ; September 2015",
    "testnet": "Test SDF Network ; September 2015",
}

# 1 XLM = 10,000,000 stroops
STROOPS_PER_XLM = Decimal("10000000")


# ── Data classes ───────────────────────────────────────────

@dataclass
class StellarPayment:
    """A single payment operation on the Stellar network."""
    id: str
    source_account: str
    destination: str
    amount: Decimal
    asset_code: str  # "XLM" for native, or asset code like "USDC"
    asset_issuer: str  # empty for native XLM
    transaction_hash: str
    created_at: str  # ISO timestamp
    memo: str = ""
    payment_type: str = "payment"  # payment, create_account, path_payment

    def to_entry_amount(self) -> Decimal:
        """Return the amount as a Decimal in the asset's units."""
        return self.amount

    def is_native(self) -> bool:
        """Whether this payment is in native XLM."""
        return self.asset_code == "XLM" and self.asset_issuer == ""


@dataclass
class StellarAccount:
    """A Stellar account tracked in the ledger."""
    account_id: str  # G... public key
    label: str = ""
    network: str = "public"

    def is_valid(self) -> bool:
        """Check if the account ID looks like a valid Stellar public key."""
        return len(self.account_id) == 56 and self.account_id.startswith("G")


# ── Horizon client ─────────────────────────────────────────

class HorizonClient:
    """Minimal HTTP client for Stellar Horizon REST API.

    Only uses the standard library (urllib) — no external dependencies.
    Handles pagination via the Horizon cursor mechanism.
    """

    def __init__(self, network: str = "public", base_url: str = ""):
        self.network = network
        self.base_url = base_url or HORIZON_URLS.get(network, HORIZON_URLS["public"])

    def _get(self, path: str) -> dict:
        """Make a GET request to Horizon and return parsed JSON."""
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, headers={"Accept": "application/hal+json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}
            raise

    def get_account(self, account_id: str) -> dict:
        """Fetch account details from Horizon."""
        return self._get(f"/accounts/{account_id}")

    def get_payments(
        self,
        account_id: str,
        cursor: str = "",
        limit: int = 100,
    ) -> tuple[list[StellarPayment], Optional[str]]:
        """Fetch payment operations for an account.

        Returns a list of StellarPayment objects and the next pagination
        cursor (or None if there are no more results).
        """
        path = f"/accounts/{account_id}/payments?limit={limit}&order=asc"
        if cursor:
            path += f"&cursor={cursor}"

        data = self._get(path)
        records = data.get("_embedded", {}).get("records", [])

        payments: list[StellarPayment] = []
        for record in records:
            payment = self._parse_payment(record)
            if payment:
                payments.append(payment)

        # Get next cursor
        next_link = data.get("_links", {}).get("next", {}).get("href", "")
        next_cursor = None
        if next_link:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(next_link)
            params = parse_qs(parsed.query)
            next_cursor = params.get("cursor", [None])[0]

        return payments, next_cursor

    def get_all_payments(
        self,
        account_id: str,
        max_records: int = 1000,
    ) -> list[StellarPayment]:
        """Fetch all payments for an account, handling pagination."""
        all_payments: list[StellarPayment] = []
        cursor: Optional[str] = ""

        while cursor is not None and len(all_payments) < max_records:
            payments, next_cursor = self.get_payments(account_id, cursor or "")
            all_payments.extend(payments)
            cursor = next_cursor
            if not payments:
                break

        return all_payments[:max_records]

    def _parse_payment(self, record: dict) -> Optional[StellarPayment]:
        """Parse a Horizon payment operation record into a StellarPayment."""
        ptype = record.get("type", "payment")

        if ptype == "payment":
            return StellarPayment(
                id=record.get("id", ""),
                source_account=record.get("source_account", ""),
                destination=record.get("to", ""),
                amount=Decimal(record.get("amount", "0")),
                asset_code=record.get("asset_code", "XLM"),
                asset_issuer=record.get("asset_issuer", ""),
                transaction_hash=record.get("transaction_hash", ""),
                created_at=record.get("created_at", ""),
                memo=record.get("transaction", {}).get("memo", ""),
                payment_type="payment",
            )
        elif ptype == "create_account":
            return StellarPayment(
                id=record.get("id", ""),
                source_account=record.get("funder", ""),
                destination=record.get("account", ""),
                amount=Decimal(record.get("starting_balance", "0")),
                asset_code="XLM",
                asset_issuer="",
                transaction_hash=record.get("transaction_hash", ""),
                created_at=record.get("created_at", ""),
                payment_type="create_account",
            )
        elif ptype == "path_payment":
            return StellarPayment(
                id=record.get("id", ""),
                source_account=record.get("source_account", ""),
                destination=record.get("to", ""),
                amount=Decimal(record.get("amount", "0")),
                asset_code=record.get("asset_code", "XLM"),
                asset_issuer=record.get("asset_issuer", ""),
                transaction_hash=record.get("transaction_hash", ""),
                created_at=record.get("created_at", ""),
                payment_type="path_payment",
            )

        return None

    def get_latest_ledger(self) -> dict:
        """Fetch the latest ledger from Horizon."""
        data = self._get("/ledgers?limit=1&order=desc")
        records = data.get("_embedded", {}).get("records", [])
        return records[0] if records else {}


# ── Helpers ────────────────────────────────────────────────

def stroops_to_xlm(stroops: int | str) -> Decimal:
    """Convert stroops to XLM (1 XLM = 10,000,000 stroops)."""
    value = Decimal(str(stroops))
    return value / STROOPS_PER_XLM


def xlm_to_stroops(xlm: Decimal) -> int:
    """Convert XLM to stroops."""
    return int(xlm * STROOPS_PER_XLM)


def format_xlm(amount: Decimal) -> str:
    """Format an XLM amount for display."""
    return f"{amount:.7f} XLM"


def is_valid_account_id(account_id: str) -> bool:
    """Check if a string looks like a valid Stellar account ID (G..., 56 chars)."""
    return len(account_id) == 56 and account_id.startswith("G")


def payment_to_description(payment: StellarPayment) -> str:
    """Generate a human-readable description for a Stellar payment."""
    asset = payment.asset_code if payment.is_native() else f"{payment.asset_code}:{payment.asset_issuer[:8]}"
    direction = "from" if payment.source_account else ""
    source = payment.source_account[:12] + "..." if payment.source_account else "network"
    return f"Stellar {payment.payment_type}: {format_xlm(payment.amount) if payment.is_native() else payment.amount} {asset} {direction} {source}"


def reconcile_payments(
    payments: list[StellarPayment],
    ledger_account: str = "Stellar Wallet",
    revenue_account: str = "Revenue",
) -> list:
    """Convert Stellar payments into double-entry transaction dicts.

    Each payment becomes a balanced transaction: debit the wallet
    (asset increase), credit revenue.
    """
    from .models import Entry, Transaction

    transactions: list[Transaction] = []
    for payment in payments:
        amount = payment.amount
        txn = Transaction(
            date=payment.created_at[:10] if payment.created_at else "",
            description=payment_to_description(payment),
            payee=payment.source_account[:16] if payment.source_account else "",
            tags=["stellar", payment.asset_code.lower()],
            entries=[
                Entry(account=ledger_account, debit=amount),
                Entry(account=revenue_account, credit=amount),
            ],
        )
        transactions.append(txn)

    return transactions
