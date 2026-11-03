"""Tests for the Stellar Horizon integration module."""

import pytest
from decimal import Decimal
from ledgerlite.stellar import (
    StellarPayment,
    StellarAccount,
    HorizonClient,
    stroops_to_xlm,
    xlm_to_stroops,
    format_xlm,
    is_valid_account_id,
    payment_to_description,
    reconcile_payments,
    HORIZON_URLS,
    NETWORK_PASSPHRASES,
    STROOPS_PER_XLM,
)
from ledgerlite.models import Entry, Transaction


class TestStellarConstants:
    def test_horizon_urls_exist(self):
        assert "public" in HORIZON_URLS
        assert "testnet" in HORIZON_URLS
        assert "horizon.stellar.org" in HORIZON_URLS["public"]

    def test_network_passphrases_exist(self):
        assert "public" in NETWORK_PASSPHRASES
        assert "testnet" in NETWORK_PASSPHRASES
        assert "Public Global" in NETWORK_PASSPHRASES["public"]

    def test_stroops_per_xlm(self):
        assert STROOPS_PER_XLM == Decimal("10000000")


class TestStroopConversions:
    def test_stroops_to_xlm_whole(self):
        assert stroops_to_xlm("10000000") == Decimal("1")

    def test_stroops_to_xlm_fractional(self):
        assert stroops_to_xlm("5000000") == Decimal("0.5")
        assert stroops_to_xlm("1234567") == Decimal("0.1234567")

    def test_stroops_to_xlm_zero(self):
        assert stroops_to_xlm("0") == Decimal("0")

    def test_stroops_to_xlm_integer(self):
        assert stroops_to_xlm(10000000) == Decimal("1")

    def test_xlm_to_stroops_whole(self):
        assert xlm_to_stroops(Decimal("1")) == 10000000

    def test_xlm_to_stroops_fractional(self):
        assert xlm_to_stroops(Decimal("0.5")) == 5000000

    def test_round_trip(self):
        xlm = Decimal("123.4567890")
        stroops = xlm_to_stroops(xlm)
        assert stroops_to_xlm(stroops) == xlm


class TestFormatXlm:
    def test_format_xlm_one(self):
        assert format_xlm(Decimal("1")) == "1.0000000 XLM"

    def test_format_xlm_fractional(self):
        assert format_xlm(Decimal("0.5")) == "0.5000000 XLM"

    def test_format_xlm_zero(self):
        assert format_xlm(Decimal("0")) == "0.0000000 XLM"


class TestAccountIdValidation:
    def test_valid_account_id(self):
        assert is_valid_account_id("G" + "A" * 55)

    def test_invalid_too_short(self):
        assert not is_valid_account_id("GABC")

    def test_invalid_starts_with_s(self):
        assert not is_valid_account_id("S" + "A" * 55)

    def test_invalid_empty(self):
        assert not is_valid_account_id("")


class TestStellarPayment:
    def test_is_native_xlm(self):
        payment = StellarPayment(
            id="1",
            source_account="G" + "A" * 55,
            destination="G" + "B" * 55,
            amount=Decimal("100"),
            asset_code="XLM",
            asset_issuer="",
            transaction_hash="a" * 64,
            created_at="2026-01-15T12:00:00Z",
        )
        assert payment.is_native() is True

    def test_is_not_native_asset(self):
        payment = StellarPayment(
            id="1",
            source_account="G" + "A" * 55,
            destination="G" + "B" * 55,
            amount=Decimal("100"),
            asset_code="USDC",
            asset_issuer="G" + "C" * 55,
            transaction_hash="a" * 64,
            created_at="2026-01-15T12:00:00Z",
        )
        assert payment.is_native() is False

    def test_to_entry_amount(self):
        payment = StellarPayment(
            id="1",
            source_account="",
            destination="",
            amount=Decimal("42.5"),
            asset_code="XLM",
            asset_issuer="",
            transaction_hash="",
            created_at="",
        )
        assert payment.to_entry_amount() == Decimal("42.5")


class TestStellarAccount:
    def test_valid_account(self):
        acct = StellarAccount(account_id="G" + "A" * 55)
        assert acct.is_valid() is True

    def test_invalid_account(self):
        acct = StellarAccount(account_id="invalid")
        assert acct.is_valid() is False


class TestPaymentDescription:
    def test_xlm_payment_description(self):
        payment = StellarPayment(
            id="1",
            source_account="G" + "A" * 55,
            destination="G" + "B" * 55,
            amount=Decimal("100"),
            asset_code="XLM",
            asset_issuer="",
            transaction_hash="a" * 64,
            created_at="2026-01-15T12:00:00Z",
            payment_type="payment",
        )
        desc = payment_to_description(payment)
        assert "Stellar payment" in desc
        assert "XLM" in desc

    def test_asset_payment_description(self):
        payment = StellarPayment(
            id="1",
            source_account="G" + "A" * 55,
            destination="G" + "B" * 55,
            amount=Decimal("50"),
            asset_code="USDC",
            asset_issuer="G" + "C" * 55,
            transaction_hash="a" * 64,
            created_at="2026-01-15T12:00:00Z",
            payment_type="payment",
        )
        desc = payment_to_description(payment)
        assert "Stellar payment" in desc
        assert "USDC" in desc


class TestReconcilePayments:
    def test_reconcile_creates_balanced_transactions(self):
        payments = [
            StellarPayment(
                id="1",
                source_account="G" + "A" * 55,
                destination="G" + "B" * 55,
                amount=Decimal("100"),
                asset_code="XLM",
                asset_issuer="",
                transaction_hash="a" * 64,
                created_at="2026-01-15T12:00:00Z",
                payment_type="payment",
            ),
        ]
        txns = reconcile_payments(payments, "Stellar Wallet", "Revenue")
        assert len(txns) == 1
        assert txns[0].is_balanced
        assert txns[0].entries[0].account == "Stellar Wallet"
        assert txns[0].entries[0].debit == Decimal("100")
        assert txns[0].entries[1].account == "Revenue"
        assert txns[0].entries[1].credit == Decimal("100")

    def test_reconcile_multiple_payments(self):
        payments = [
            StellarPayment(
                id=str(i),
                source_account="G" + "A" * 55,
                destination="G" + "B" * 55,
                amount=Decimal(str(i * 10)),
                asset_code="XLM",
                asset_issuer="",
                transaction_hash="a" * 64,
                created_at="2026-01-15T12:00:00Z",
                payment_type="payment",
            )
            for i in range(1, 4)
        ]
        txns = reconcile_payments(payments)
        assert len(txns) == 3
        assert all(t.is_balanced for t in txns)

    def test_reconcile_tags_include_stellar(self):
        payments = [
            StellarPayment(
                id="1",
                source_account="",
                destination="",
                amount=Decimal("1"),
                asset_code="XLM",
                asset_issuer="",
                transaction_hash="",
                created_at="2026-01-15T12:00:00Z",
                payment_type="payment",
            ),
        ]
        txns = reconcile_payments(payments)
        assert "stellar" in txns[0].tags
        assert "xlm" in txns[0].tags


class TestHorizonClient:
    def test_default_public_network(self):
        client = HorizonClient()
        assert client.network == "public"
        assert "horizon.stellar.org" in client.base_url

    def test_testnet_network(self):
        client = HorizonClient(network="testnet")
        assert client.network == "testnet"
        assert "horizon-testnet" in client.base_url

    def test_custom_base_url(self):
        client = HorizonClient(base_url="http://localhost:8000")
        assert client.base_url == "http://localhost:8000"
