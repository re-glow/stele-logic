"""Surface syntax parser for proof terms.

Grammar summary
---------------
  term    ::= fun_term | case_term | app_term

  fun_term ::= ('fun' | 'λ') IDENT ':' formula '=>' term

  case_term ::= 'case' app_term 'of' 'inl' IDENT '=>' term '|' 'inr' IDENT '=>' term

  app_term  ::= primary ('(' term ')')*       (left-associative application)

  primary ::= IDENT                            variable
            | '(' term ')'                     grouping
            | 'pair' '(' term ',' term ')'
            | 'fst'  '(' term ')'
            | 'snd'  '(' term ')'
            | 'inl'  '(' term ',' formula ')'  right_type annotation required
            | 'inr'  '(' term ',' formula ')'  left_type annotation required
            | 'abort' '(' term ',' formula ')'  target_type annotation required

Formulas inside terms (after ':' in fun, or as second arg in inl/inr/abort) use the
same formula grammar as the rest of Stele (->  and  or  not  false  parens).

Keywords (not valid as variable names):
  fun  λ  case  of  inl  inr  pair  fst  snd  abort
  and  or  not  false  (formula-level keywords)

Punctuation tokens: ( ) | , : => ->

Examples
--------
  fun x: A => x
  fun f: A -> B => fun a: A => f(a)
  pair(x, y)
  fst(pair(x, y))
  inl(x, B)
  inr(y, A)
  case e of inl x => x | inr y => y
  abort(bot, C)
"""
import re
from stele.ast import Var as FVar, Op
from stele.core.terms import TVar, Lam, App, Pair, Fst, Snd, Inl, Inr, Case, Abort

# ── Tokenizer ────────────────────────────────────────────────────────────────

_TOK = re.compile(r"\s*(=>|->|\(|\)|\||,|:|λ|[A-Za-z_][A-Za-z0-9_]*)")

_TERM_KWS = frozenset({
    "fun", "case", "of", "inl", "inr", "pair", "fst", "snd", "abort",
    "and", "or", "not", "false",
})
_PUNCT = frozenset({"(", ")", "|", ",", ":", "=>", "->", "λ"})


class TermParseError(Exception):
    """Raised when a term surface string cannot be parsed."""


def _tokenize(s):
    toks = []
    i = 0
    while i < len(s):
        m = _TOK.match(s, i)
        if not m:
            rest = s[i:].lstrip()
            if not rest:
                break
            raise TermParseError(f"unexpected character {s[i]!r}")
        i = m.end()
        toks.append(m.group(1))
    return toks


# ── Parser ───────────────────────────────────────────────────────────────────

class _Parser:
    def __init__(self, toks):
        self.toks = toks
        self.i = 0

    # -- helpers --

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def adv(self):
        t = self.peek()
        self.i += 1
        return t

    def expect(self, *choices):
        t = self.peek()
        if t not in choices:
            opts = " or ".join(repr(c) for c in choices)
            raise TermParseError(f"expected {opts}, got {t!r}")
        return self.adv()

    def ident(self):
        t = self.peek()
        if t is None or t in _TERM_KWS or t in _PUNCT:
            raise TermParseError(f"expected an identifier, got {t!r}")
        return self.adv()

    # -- term grammar --

    def term(self):
        t = self.peek()
        if t in ("fun", "λ"):
            return self.fun_term()
        if t == "case":
            return self.case_term()
        return self.app_term()

    def fun_term(self):
        self.adv()                      # consume 'fun' or 'λ'
        var = self.ident()
        self.expect(":")
        ty = self.formula_until({"=>"})
        self.expect("=>")
        body = self.term()
        return Lam(var, ty, body)

    def case_term(self):
        self.adv()                      # consume 'case'
        scrutinee = self.app_term()
        self.expect("of")
        self.expect("inl")
        lvar = self.ident()
        self.expect("=>")
        lbody = self.term()
        self.expect("|")
        self.expect("inr")
        rvar = self.ident()
        self.expect("=>")
        rbody = self.term()
        return Case(scrutinee, lvar, lbody, rvar, rbody)

    def app_term(self):
        t = self.primary()
        while self.peek() == "(":
            self.adv()
            arg = self.term()
            self.expect(")")
            t = App(t, arg)
        return t

    def primary(self):
        t = self.peek()

        if t == "(":
            self.adv()
            e = self.term()
            self.expect(")")
            return e

        if t == "pair":
            self.adv()
            self.expect("(")
            left = self.term()
            self.expect(",")
            right = self.term()
            self.expect(")")
            return Pair(left, right)

        if t == "fst":
            self.adv()
            self.expect("(")
            inner = self.term()
            self.expect(")")
            return Fst(inner)

        if t == "snd":
            self.adv()
            self.expect("(")
            inner = self.term()
            self.expect(")")
            return Snd(inner)

        if t == "inl":
            self.adv()
            self.expect("(")
            value = self.term()
            self.expect(",")
            rtype = self.formula_until({")"})
            self.expect(")")
            return Inl(value, rtype)

        if t == "inr":
            self.adv()
            self.expect("(")
            value = self.term()
            self.expect(",")
            ltype = self.formula_until({")"})
            self.expect(")")
            return Inr(value, ltype)

        if t == "abort":
            self.adv()
            self.expect("(")
            ft = self.term()
            self.expect(",")
            target = self.formula_until({")"})
            self.expect(")")
            return Abort(ft, target)

        # Variable — must be a non-keyword, non-punctuation identifier
        if t is None:
            raise TermParseError("unexpected end of input in term position")
        if t in _TERM_KWS or t in _PUNCT:
            raise TermParseError(f"unexpected token {t!r} in term position")
        self.adv()
        return TVar(t)

    # -- formula sub-parser --

    def formula_until(self, terminators):
        """Collect tokens (respecting paren depth) up to a terminator, then
        parse them as a Stele formula.  The terminator is NOT consumed.
        """
        depth = 0
        start = self.i
        while self.i < len(self.toks):
            tok = self.toks[self.i]
            if tok == "(":
                depth += 1
                self.i += 1
            elif tok == ")":
                if depth == 0:
                    break
                depth -= 1
                self.i += 1
            elif tok in terminators and depth == 0:
                break
            else:
                self.i += 1
        formula_toks = self.toks[start:self.i]
        if not formula_toks:
            raise TermParseError("expected a formula, found nothing")
        return _parse_formula_from_toks(formula_toks)

    def parse(self):
        t = self.term()
        if self.peek() is not None:
            raise TermParseError(
                f"unexpected token {self.peek()!r} after term"
            )
        return t


def _parse_formula_from_toks(toks):
    from stele.parser import parse_formula
    from stele.errors import ParseError
    try:
        return parse_formula(" ".join(toks))
    except ParseError as e:
        raise TermParseError(f"bad formula in term: {e}") from e


# ── Public API ───────────────────────────────────────────────────────────────

def parse_term(s):
    """Parse a proof term from a surface syntax string.

    Returns: a Term (TVar | Lam | App | Pair | Fst | Snd | Inl | Inr | Case | Abort)
    Raises:  TermParseError on syntax errors
    """
    toks = _tokenize(s)
    if not toks:
        raise TermParseError("empty term string")
    return _Parser(toks).parse()
