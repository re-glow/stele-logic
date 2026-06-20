from stele.parser import parse_formula
from stele.ast import Var, Op


def test_imp_right_assoc():
    assert parse_formula("P -> Q -> R") == Op(
        "imp", (Var("P"), Op("imp", (Var("Q"), Var("R")))))


def test_not_binds_tightest():
    assert parse_formula("not P and Q") == Op(
        "and", (Op("not", (Var("P"),)), Var("Q")))


def test_double_negation():
    assert parse_formula("not not P") == Op("not", (Op("not", (Var("P"),)),))


def test_parens_override():
    assert parse_formula("(P -> Q) -> R") == Op(
        "imp", (Op("imp", (Var("P"), Var("Q"))), Var("R")))


def test_and_or_precedence():
    assert parse_formula("P and Q or R") == Op(
        "or", (Op("and", (Var("P"), Var("Q"))), Var("R")))
