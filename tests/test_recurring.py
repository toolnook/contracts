"""Tests for the recurring transaction scheduler."""

import pytest
from decimal import Decimal
from ledgerlite.models import Account, Entry, RecurringTemplate, Transaction
from ledgerlite.storage import LedgerStorage
from ledgerlite.ledger import Ledger
from ledgerlite.recurring import RecurringScheduler


@pytest.fixture
def ledger(tmp_path):
    storage = LedgerStorage(tmp_path / "test.json")
    storage.init()
    led = Ledger(storage)
    led.add_account("Cash", "asset")
    led.add_account("Rent Expense", "expense")
    led.add_account("Revenue", "revenue")
    return led


class TestRecurringScheduler:
    def test_add_and_get_template(self, ledger):
        scheduler = RecurringScheduler(ledger)
        template = RecurringTemplate(
            description="Monthly rent",
            frequency="monthly",
            entries=[
                Entry(account="Rent Expense", debit=Decimal("2000")),
                Entry(account="Cash", credit=Decimal("2000")),
            ],
        )
        scheduler.add_template(template)
        templates = scheduler.get_templates()
        assert len(templates) == 1
        assert templates[0].description == "Monthly rent"

    def test_generate_monthly(self, ledger):
        scheduler = RecurringScheduler(ledger)
        template = RecurringTemplate(
            description="Monthly rent",
            frequency="monthly",
            entries=[
                Entry(account="Rent Expense", debit=Decimal("2000")),
                Entry(account="Cash", credit=Decimal("2000")),
            ],
        )
        txns = scheduler.generate(template, "2026-01-01", "2026-03-31")
        assert len(txns) == 3
        assert txns[0].date == "2026-01-01"
        assert txns[1].date == "2026-02-01"
        assert txns[2].date == "2026-03-01"
        assert all(t.description == "Monthly rent" for t in txns)

    def test_generate_weekly(self, ledger):
        scheduler = RecurringScheduler(ledger)
        template = RecurringTemplate(
            description="Weekly payroll",
            frequency="weekly",
            entries=[
                Entry(account="Rent Expense", debit=Decimal("500")),
                Entry(account="Cash", credit=Decimal("500")),
            ],
        )
        txns = scheduler.generate(template, "2026-01-01", "2026-01-22")
        assert len(txns) == 4
        assert txns[0].date == "2026-01-01"
        assert txns[3].date == "2026-01-22"

    def test_generate_daily(self, ledger):
        scheduler = RecurringScheduler(ledger)
        template = RecurringTemplate(
            description="Daily coffee",
            frequency="daily",
            entries=[
                Entry(account="Rent Expense", debit=Decimal("5")),
                Entry(account="Cash", credit=Decimal("5")),
            ],
        )
        txns = scheduler.generate(template, "2026-01-01", "2026-01-05")
        assert len(txns) == 5

    def test_generate_yearly(self, ledger):
        scheduler = RecurringScheduler(ledger)
        template = RecurringTemplate(
            description="Annual insurance",
            frequency="yearly",
            entries=[
                Entry(account="Rent Expense", debit=Decimal("12000")),
                Entry(account="Cash", credit=Decimal("12000")),
            ],
        )
        txns = scheduler.generate(template, "2026-01-01", "2028-12-31")
        assert len(txns) == 3
        assert txns[0].date == "2026-01-01"
        assert txns[1].date == "2027-01-01"
        assert txns[2].date == "2028-01-01"

    def test_generate_and_save(self, ledger):
        scheduler = RecurringScheduler(ledger)
        template = RecurringTemplate(
            description="Monthly rent",
            frequency="monthly",
            entries=[
                Entry(account="Rent Expense", debit=Decimal("2000")),
                Entry(account="Cash", credit=Decimal("2000")),
            ],
        )
        txns = scheduler.generate_and_save(template, "2026-01-01", "2026-03-31")
        assert len(txns) == 3
        assert ledger.storage.transaction_count() == 3
        # Verify the transactions are balanced
        assert all(t.is_balanced for t in txns)

    def test_generate_all_templates(self, ledger):
        scheduler = RecurringScheduler(ledger)
        template1 = RecurringTemplate(
            description="Monthly rent",
            frequency="monthly",
            entries=[
                Entry(account="Rent Expense", debit=Decimal("2000")),
                Entry(account="Cash", credit=Decimal("2000")),
            ],
        )
        template2 = RecurringTemplate(
            description="Monthly revenue",
            frequency="monthly",
            entries=[
                Entry(account="Cash", debit=Decimal("5000")),
                Entry(account="Revenue", credit=Decimal("5000")),
            ],
        )
        scheduler.add_template(template1)
        scheduler.add_template(template2)
        txns = scheduler.generate_all("2026-01-01", "2026-02-28")
        assert len(txns) == 4  # 2 templates × 2 months

    def test_invalid_date_range_raises(self, ledger):
        scheduler = RecurringScheduler(ledger)
        template = RecurringTemplate(
            description="Monthly rent",
            frequency="monthly",
            entries=[
                Entry(account="Rent Expense", debit=Decimal("2000")),
                Entry(account="Cash", credit=Decimal("2000")),
            ],
        )
        with pytest.raises(ValueError, match="end_date must be"):
            scheduler.generate(template, "2026-03-01", "2026-01-01")

    def test_get_next_occurrence(self, ledger):
        scheduler = RecurringScheduler(ledger)
        template = RecurringTemplate(
            description="Monthly rent",
            frequency="monthly",
            entries=[
                Entry(account="Rent Expense", debit=Decimal("2000")),
                Entry(account="Cash", credit=Decimal("2000")),
            ],
        )
        next_date = scheduler.get_next_occurrence(template, "2026-01-15")
        assert next_date == "2026-02-15"
