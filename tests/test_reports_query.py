import pytest
from fastapi import HTTPException

from app.reports.query import Where, order_by

ALLOWED = {"days_overdue": "days_overdue", "priority": "CASE priority WHEN 'P1' THEN 1 ELSE 2 END", "region": "region"}


def test_no_filters_gives_no_where_clause():
    w = Where()
    w.any_of("region", None)
    w.any_of("region", [])
    w.compare("days_open", ">=", None)
    w.flag("breached_live", None)
    w.prefix(["complaint_id"], None)
    assert w.sql == "" and w.params == {}


def test_filters_are_anded_and_values_are_bound_not_inlined():
    w = Where()
    w.any_of("region", ["Ashford", "x'; DROP TABLE complaints; --"])
    w.compare("days_open", ">=", 10)
    assert w.sql == "WHERE region = ANY(:w0) AND days_open >= :w1"
    assert w.params["w0"] == ["Ashford", "x'; DROP TABLE complaints; --"]  # a value, never part of the SQL
    assert "DROP" not in w.sql


def test_two_wheres_in_one_query_use_different_parameter_names():
    inner, outer = Where("i"), Where("o")
    inner.compare("a", "=", 1)
    outer.compare("b", "=", 2)
    assert set(inner.params) == {"i0"} and set(outer.params) == {"o0"}


def test_flags_normal_and_strict():
    w = Where()
    w.flag("breached_live", True)
    w.flag("breached_live", False)
    w.flag("resolvable_by_information_only", False, strict=True)
    w.flag("resolvable_by_information_only", True, strict=True)
    assert w.sql == (
        "WHERE breached_live IS TRUE AND breached_live IS NOT TRUE "
        "AND resolvable_by_information_only IS FALSE AND resolvable_by_information_only IS TRUE"
    )


def test_is_set_and_raw():
    w = Where()
    w.raw("status = 'Open'")
    w.is_set("classification_id", True)
    w.is_set("classification_id", False)
    assert w.sql == "WHERE status = 'Open' AND classification_id IS NOT NULL AND classification_id IS NULL"


def test_prefix_search_escapes_wildcards():
    w = Where()
    w.prefix(["complaint_id", "account_id"], "NW_10%")
    assert w.sql == "WHERE (complaint_id ILIKE :w0 OR account_id ILIKE :w0)"
    assert w.params["w0"] == "NW\\_10\\%%"  # the customer's % and _ stay literal; only the trailing % is a wildcard


def test_compare_only_accepts_known_operators():
    with pytest.raises(AssertionError):
        Where().compare("days_open", "; DROP TABLE x; --", 1)


def test_order_by_uses_whitelisted_expressions_and_a_tiebreaker():
    sql, applied = order_by("days_overdue:desc,region", ALLOWED, "region", "complaint_id")
    assert sql == "ORDER BY days_overdue DESC NULLS LAST, region ASC NULLS LAST, complaint_id"
    assert applied == ["days_overdue:desc", "region:asc"]


def test_order_by_default_direction_and_expression_sorts():
    sql, applied = order_by(None, ALLOWED, "priority,days_overdue:desc", "id")
    assert sql.startswith("ORDER BY CASE priority WHEN 'P1' THEN 1 ELSE 2 END ASC NULLS LAST, days_overdue DESC")
    assert applied == ["priority:asc", "days_overdue:desc"]


@pytest.mark.parametrize("bad", ["password", "days_overdue:sideways", "days_overdue; DROP TABLE x", "region:asc,secret", ":desc"])
def test_order_by_rejects_anything_not_whitelisted(bad):
    with pytest.raises(HTTPException) as e:
        order_by(bad, ALLOWED, "region", "id")
    assert e.value.status_code == 422
    assert "days_overdue" in e.value.detail  # tells the caller what is allowed
