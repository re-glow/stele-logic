from dataclasses import dataclass


@dataclass(frozen=True)
class Definition:
    """A top-level formula abbreviation: definition NAME := FORMULA.

    formula stores the original (unexpanded) formula body.
    The parser expands definition references in the theorem body so the
    trusted kernel always receives fully-expanded formulas.
    """
    name: str
    formula: object  # original formula (Var | Op)
    line: int


@dataclass(frozen=True)
class Assume:
    label: str
    formula: object
    line: int


@dataclass(frozen=True)
class Have:
    label: str
    formula: object
    rule: str
    refs: tuple
    line: int


@dataclass(frozen=True)
class Suppose:
    label: str
    formula: object
    body: tuple
    line: int


@dataclass(frozen=True)
class Conclude:
    formula: object
    ref: str
    line: int


@dataclass(frozen=True)
class Theorem:
    name: str
    logic: object
    lines: tuple        # expanded proof lines (Var nodes for definition names are replaced)
    definitions: tuple = ()  # tuple of Definition objects, in declaration order


@dataclass(frozen=True)
class MatrixDirective:
    kind: str      # "evaluate" | "tautology" | "entails"
    premises: tuple  # formula tuple for entails; empty for evaluate/tautology
    formula: object  # main formula (evaluate/tautology) or conclusion (entails)
    line: int
