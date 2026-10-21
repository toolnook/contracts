"""Tests for CSV import and export."""

import pytest
from decimal import Decimal
from ledgerlite.models import Account, Entry, Transaction
from ledgerlite.storage import LedgerStorage
from ledgerlite.ledger import Ledger
from ledgerlite.csv_import import import_csv, export_csv


@pytest.fixture
def ledger(tmp_path):
    storage = LedgerStorage(tmp_path / "test.json")
    storage.init()
    led = Ledger(storage)
    led.add_account("Cash", "asset")
    led.add_account("Revenue", "revenue")
    led.add_account("Office Supplies", "expense")
    return led


class TestImportCSV:
    def test_import_simple_csv(self, ledger, tmp_path):
        csv_path = tmp_path / "import.csv"
        csv_path.write_text(
            "date,description,payee,debit_account,credit_account,amount,tag\n"
            "2026-01-15,Sale,ACME,Cash,Revenue,500.00,acme\n"
            "2026-02-01,Supplies,OfficeMax,Office Supplies,Cash,50.00,office\n"
        )
        txns = import_csv(str(csv_path), ledger)
        assert len(txns) == 2
        assert ledger.storage.transaction_count() == 2
        assert txns[0].description == "Sale"
        assert txns[0].entries[0].account == "Cash"
        assert txns[0].entries[0].debit == Decimal("500.00")
        assert "acme" in txns[0].tags

    def test_import_no_header(self, ledger, tmp_path):
        csv_path = tmp_path / "import.csv"
        csv_path.write_text(
            "2026-01-15,Sale,ACME,Cash,Revenue,500.00,acme\n"
        )
        txns = import_csv(str(csv_path), ledger, skip_header=False)
        assert len(txns) == 1

    def test_import_missing_file_raises(self, ledger, tmp_path):
        with pytest.raises(FileNotFoundError):
            import_csv(str(tmp_path / "nope.csv"), ledger)

    def test_import_malformed_row_raises(self, ledger, tmp_path):
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text(
            "date,description,payee,debit_account,credit_account,amount,tag\n"
            "2026-01-15,Short,ACME,Cash\n"
        )
        with pytest.raises(ValueError, match="columns"):
            import_csv(str(csv_path), ledger)

    def test_import_invalid_amount_raises(self, ledger, tmp_path):
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text(
            "date,description,payee,debit_account,credit_account,amount,tag\n"
            "2026-01-15,Bad,ACME,Cash,Revenue,notanumber,acme\n"
        )
        with pytest.raises(ValueError, match="invalid amount"):
            import_csv(str(csv_path), ledger)


class TestExportCSV:
    def test_export_and_reimport(self, ledger, tmp_path):
        ledger.add_transaction(Transaction(
            date="2026-01-15", description="Sale", payee="ACME", tags=["acme"],
            entries=[
                Entry(account="Cash", debit=Decimal("500")),
                Entry(account="Revenue", credit=Decimal("500")),
            ],
        ))
        export_path = tmp_path / "export.csv"
        txns = ledger.get_transactions()
        export_csv(str(export_path), txns)

        # Reimport into a fresh ledger
        storage2 = LedgerStorage(tmp_path / "test2.json")
        storage2.init()
        led2 = Ledger(storage2)
        led2.add_account("Cash", "asset")
        led2.add_account("Revenue", "revenue")
        imported = import_csv(str(export_path), led2, skip_header=True)
        assert len(imported) == 1
        assert imported[0].description == "Sale"
        assert imported[0].payee == "ACME"
        assert "acme" in imported[0].tags
