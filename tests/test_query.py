"""Tests for the query module."""

import pytest
from decimal import Decimal
from ledgerlite.models import Entry, Transaction
from ledgerlite.query import Query, QueryFilter, parse_query


@pytest.fixture
def transactions():
    return [
        Transaction(
            date="2026-01-15", description="January sale", payee="ACME",
            tags=["acme"],
            entries=[
                Entry(account="Cash", debit=Decimal("500")),
                Entry(account="Revenue", credit=Decimal("500")),
            ],
        ),
        Transaction(
            date="2026-02-20", description="February expense", payee="OfficeMax",
            tags=["office"],
            entries=[
                Entry(account="Office Supplies", debit=Decimal("100")),
                Entry(account="Cash", credit=Decimal("100")),
            ],
        ),
        Transaction(
            date="2026-03-10", description="March sale", payee="ACME",
            tags=["acme"],
            entries=[
                Entry(account="Cash", debit=Decimal("800")),
                Entry(account="Revenue", credit=Decimal("800")),
            ],
        ),
    ]


class TestQueryFilter:
    def test_filter_by_date_range(self, transactions):
        results = Query(transactions).filter(QueryFilter(date_from="2026-02-01", date_to="2026-02-28"))
        assert len(results) == 1
        assert results[0].description == "February expense"

    def test_filter_by_date_from_only(self, transactions):
        results = Query(transactions).filter(QueryFilter(date_from="2026-02-01"))
        assert len(results) == 2

    def test_filter_by_date_to_only(self, transactions):
        results = Query(transactions).filter(QueryFilter(date_to="2026-01-31"))
        assert len(results) == 1
        assert results[0].description == "January sale"

    def test_filter_by_account(self, transactions):
        results = Query(transactions).filter(QueryFilter(account="Revenue"))
        assert len(results) == 2
        assert all(any(e.account == "Revenue" for e in t.entries) for t in results)

    def test_filter_by_tag(self, transactions):
        results = Query(transactions).filter(QueryFilter(tag="acme"))
        assert len(results) == 2
        assert all("acme" in t.tags for t in results)

    def test_filter_by_description(self, transactions):
        results = Query(transactions).filter(QueryFilter(description_contains="sale"))
        assert len(results) == 2

    def test_filter_by_payee(self, transactions):
        results = Query(transactions).filter(QueryFilter(payee="ACME"))
        assert len(results) == 2

    def test_combined_filter(self, transactions):
        results = Query(transactions).filter(
            QueryFilter(date_from="2026-03-01", tag="acme")
        )
        assert len(results) == 1
        assert results[0].description == "March sale"

    def test_no_matches_returns_empty(self, transactions):
        results = Query(transactions).filter(QueryFilter(tag="nonexistent"))
        assert results == []

    def test_filter_by_date_range_helper(self, transactions):
        results = Query(transactions).filter_by_date_range("2026-01-01", "2026-01-31")
        assert len(results) == 1

    def test_filter_by_account_helper(self, transactions):
        results = Query(transactions).filter_by_account("Cash")
        assert len(results) == 3

    def test_filter_by_tag_helper(self, transactions):
        results = Query(transactions).filter_by_tag("office")
        assert len(results) == 1


class TestParseQuery:
    def test_parse_date_from(self):
        qf = parse_query(["from=2026-01-01"])
        assert qf.date_from == "2026-01-01"

    def test_parse_multiple(self):
        qf = parse_query(["from=2026-01-01", "to=2026-06-30", "tag=acme"])
        assert qf.date_from == "2026-01-01"
        assert qf.date_to == "2026-06-30"
        assert qf.tag == "acme"

    def test_parse_invalid_key_raises(self):
        with pytest.raises(ValueError, match="Unknown query field"):
            parse_query(["invalid=x"])

    def test_parse_no_equals_raises(self):
        with pytest.raises(ValueError, match="key=value"):
            parse_query(["noequals"])
