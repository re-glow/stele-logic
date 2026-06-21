import re
from .ast import Var, Op
from .proof import Assume, Have, Suppose, Conclude, Theorem, MatrixDirective
from .errors import ParseError

_TOKEN = re.compile(r"\s*(->|\(|\)|[A-Za-z_][A-Za-z0-9_]*)")
_OPS = {"->", "(", ")", "and", "or", "not"}


def tokenize(s):
    toks = []
    i = 0
    while i < len(s):
        m = _TOKEN.match(s, i)
        if not m:
            if s[i:].strip() == "":
                break
            raise ParseError(f"unexpected character {s[i]!r}")
        i = m.end()
        toks.append(m.group(1))
    return toks


class _Pratt:
    def __init__(self, toks):
        self.toks = toks
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def adv(self):
        t = self.peek()
        self.i += 1
        return t

    def expect(self, t):
        if self.peek() != t:
            raise ParseError(f"expected {t!r}, got {self.peek()!r}")
        self.adv()

    def parse(self):
        f = self.imp()
        if self.peek() is not None:
            raise ParseError(f"unexpected token {self.peek()!r}")
        return f

    def imp(self):
        left = self.disj()
        if self.peek() == "->":
            self.adv()
            return Op("imp", (left, self.imp()))
        return left

    def disj(self):
        left = self.conj()
        while self.peek() == "or":
            self.adv()
            left = Op("or", (left, self.conj()))
        return left

    def conj(self):
        left = self.neg()
        while self.peek() == "and":
            self.adv()
            left = Op("and", (left, self.neg()))
        return left

    def neg(self):
        if self.peek() == "not":
            self.adv()
            return Op("not", (self.neg(),))
        return self.atom()

    def atom(self):
        t = self.peek()
        if t == "(":
            self.adv()
            f = self.imp()
            self.expect(")")
            return f
        if t is None or t in _OPS:
            raise ParseError(f"expected a formula, got {t!r}")
        self.adv()
        if t == "false":
            return Op("bot", ())
        return Var(t)


def parse_formula(s):
    return _Pratt(tokenize(s)).parse()


_HEADER = re.compile(
    r"theorem\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:using\s+([A-Za-z_][A-Za-z0-9_]*)\s*)?:$")
_ASSUME = re.compile(r"(assume|suppose)\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$")
_HAVE = re.compile(r"have\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+?)\s+by\s+(.+)$")
_CONCLUDE = re.compile(r"conclude\s+(.+?)\s+by\s+([A-Za-z_][A-Za-z0-9_]*)$")


def parse_theorem(text):
    items = []
    for n, raw in enumerate(text.splitlines(), start=1):
        code = raw.split("#", 1)[0].rstrip()
        if code.strip() == "":
            continue
        indent = len(code) - len(code.lstrip(" "))
        items.append((n, indent, code.strip()))
    if not items:
        raise ParseError("empty proof file")
    n0, _, head = items[0]
    m = _HEADER.match(head)
    if not m:
        raise ParseError("expected 'theorem NAME [using LOGIC]:'", line=n0)
    name, logic = m.group(1), m.group(2)
    body = items[1:]
    if not body:
        raise ParseError("theorem has no body", line=n0)
    lines, idx = _parse_block(body, 0, body[0][1])
    if idx != len(body):
        raise ParseError("unexpected indentation", line=body[idx][0])
    return Theorem(name=name, logic=logic, lines=tuple(lines))


def _parse_block(items, idx, base):
    out = []
    while idx < len(items) and items[idx][1] >= base:
        n, indent, text = items[idx]
        if indent != base:
            raise ParseError("unexpected indentation", line=n)
        if text.startswith("suppose"):
            label, formula = _parse_assume(text, n)
            j = idx + 1
            if j < len(items) and items[j][1] > base:
                body, idx = _parse_block(items, j, items[j][1])
            else:
                raise ParseError("suppose requires an indented subproof", line=n)
            out.append(Suppose(label=label, formula=formula, body=tuple(body), line=n))
        elif text.startswith("assume"):
            label, formula = _parse_assume(text, n)
            out.append(Assume(label=label, formula=formula, line=n))
            idx += 1
        elif text.startswith("have"):
            out.append(_parse_have(text, n))
            idx += 1
        elif text.startswith("conclude"):
            out.append(_parse_conclude(text, n))
            idx += 1
        else:
            raise ParseError(f"unknown statement: {text!r}", line=n)
    return out, idx


def _parse_assume(text, n):
    m = _ASSUME.match(text)
    if not m:
        raise ParseError("malformed assume/suppose", line=n)
    return m.group(2), parse_formula(m.group(3))


def _parse_have(text, n):
    m = _HAVE.match(text)
    if not m:
        raise ParseError("malformed have (expected 'have L: F by RULE ARGS')", line=n)
    parts = m.group(3).split()
    return Have(label=m.group(1), formula=parse_formula(m.group(2)),
                rule=parts[0], refs=tuple(parts[1:]), line=n)


def _parse_conclude(text, n):
    m = _CONCLUDE.match(text)
    if not m:
        raise ParseError("malformed conclude (expected 'conclude F by REF')", line=n)
    return Conclude(formula=parse_formula(m.group(1)), ref=m.group(2), line=n)


def parse_matrix_file(text):
    """Parse a matrix-mode .stele file into a list of MatrixDirective objects.

    Supported directives (one per non-blank, non-comment line):
      evaluate <formula>
      tautology? <formula>
      entails <premise>, ... |- <conclusion>
    """
    directives = []
    for n, raw in enumerate(text.splitlines(), start=1):
        code = raw.split("#", 1)[0].strip()
        if not code:
            continue
        if code.startswith("evaluate "):
            f = parse_formula(code[9:].strip())
            directives.append(MatrixDirective("evaluate", (), f, n))
        elif code.startswith("tautology? "):
            f = parse_formula(code[11:].strip())
            directives.append(MatrixDirective("tautology", (), f, n))
        elif code.startswith("entails "):
            rest = code[8:].strip()
            if "|-" not in rest:
                raise ParseError("entails directive requires '|-'", line=n)
            prem_part, concl_part = rest.split("|-", 1)
            prems = tuple(
                parse_formula(p.strip())
                for p in prem_part.split(",")
                if p.strip()
            )
            conc = parse_formula(concl_part.strip())
            directives.append(MatrixDirective("entails", prems, conc, n))
        else:
            raise ParseError(f"unknown matrix directive: {code!r}", line=n)
    if not directives:
        raise ParseError("empty matrix file")
    return directives
