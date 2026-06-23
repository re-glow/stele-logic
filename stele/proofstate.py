"""Proof-state inspection and rule-applicability hints (UNTRUSTED layer).

This module inspects proof structure and suggests candidate next steps for a
user writing a Stele-Light proof.  It does NOT verify proofs.  The trusted
kernel (stele/kernel.py) is the sole authority on proof validity.

Every RuleHint has trusted=False.  Any step derived from a hint MUST be
independently checked by the kernel before being treated as valid.

Entry points:
  proof_state(thm, logic_name, cursor_line=None)  -> ProofState
  proof_state_from_text(text, logic=None, cursor_line=None) -> ProofState
  visible_context_at(thm, line) -> list[ContextEntry]
  available_labels_at(thm, line) -> list[str]
  suggest_rule_hints(state, goal=None, max_hints=8) -> list[RuleHint]

IMPORTANT: hints are untrusted suggestions — the kernel must re-check every step.
"""
from dataclasses import dataclass, field

from .ast import Var, Op, pretty
from .proof import Assume, Have, Suppose, Conclude


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ContextEntry:
    """One labeled item visible in the proof context."""
    label: str
    formula_str: str     # pretty-printed formula
    formula_raw: object  # Var | Op
    kind: str            # "assume" | "suppose" | "have"
    line: object         # int | None
    scope_depth: int     # 0 = top level; 1 = inside first suppose; etc.
    available: bool      # True if in scope at this state


@dataclass
class RuleHint:
    """A candidate rule application (UNTRUSTED).

    trusted is always False — hints are local structural suggestions,
    not verified proof steps.
    """
    rule: str
    title: str
    why_applicable: str
    required_refs: list          # [str] labels to cite
    candidate_line_template: str # copy-pasteable template line(s)
    confidence: str              # "low" | "medium" | "high"
    trusted: bool = False        # ALWAYS False


@dataclass
class ProofState:
    """Snapshot of the proof context (UNTRUSTED).

    Fields:
      theorem            — theorem name
      logic              — resolved logic name
      target             — pretty-printed conclude formula (or None)
      target_raw         — raw formula (Var|Op) or None
      cursor_line        — cursor position if supplied (else None)
      context            — all ContextEntry objects (available + closed)
      open_assumptions   — labels of top-level assume nodes
      available_labels   — labels currently in scope (in declaration order)
      closed_labels      — labels that exist but are out of scope (discharged)
      last_step          — label of the last available step (or None)
      pending_goal       — pretty-printed goal still to be shown (or None)
      diagnostics_summary — brief string (or None)
      parse_error        — parse error message if parsing failed (or None)
    """
    theorem: str
    logic: str
    target: object            # str | None
    target_raw: object        # formula | None
    cursor_line: object       # int | None
    context: list             # list[ContextEntry]
    open_assumptions: list    # list[str]
    available_labels: list    # list[str] in declaration order
    closed_labels: list       # list[str]
    last_step: object         # str | None
    pending_goal: object      # str | None
    diagnostics_summary: object  # str | None
    parse_error: object       # str | None


# ---------------------------------------------------------------------------
# Formula pattern helpers
# ---------------------------------------------------------------------------

def _is_imp(f):
    """Return (A, B) if f = A → B, else None."""
    if isinstance(f, Op) and f.sym == "imp" and len(f.args) == 2:
        return f.args[0], f.args[1]
    return None


def _is_and(f):
    """Return (A, B) if f = A ∧ B, else None."""
    if isinstance(f, Op) and f.sym == "and" and len(f.args) == 2:
        return f.args[0], f.args[1]
    return None


def _is_or(f):
    """Return (A, B) if f = A ∨ B, else None."""
    if isinstance(f, Op) and f.sym == "or" and len(f.args) == 2:
        return f.args[0], f.args[1]
    return None


def _is_not(f):
    """Return A if f = ¬A (Op('not', (A,))), else None."""
    if isinstance(f, Op) and f.sym == "not" and len(f.args) == 1:
        return f.args[0]
    return None


def _is_bot(f):
    """True if f = ⊥ (false)."""
    return isinstance(f, Op) and f.sym == "bot"


def _is_double_neg(f):
    """Return A if f = ¬¬A, else None."""
    inner = _is_not(f)
    if inner is not None:
        return _is_not(inner)
    return None


def _is_lem_shape(f):
    """Return A if f = A ∨ ¬A, else None."""
    parts = _is_or(f)
    if parts is None:
        return None
    L, R = parts
    body = _is_not(R)
    if body is not None and L == body:
        return L
    return None


# ---------------------------------------------------------------------------
# Tree walking
# ---------------------------------------------------------------------------

def _walk(nodes, depth, entries, avail, closed, cursor_line):
    """Walk one block of proof nodes, populating entries/avail/closed.

    avail is mutated in-place to reflect labels in scope after this block.
    Labels introduced inside suppose blocks are added to closed, not avail.
    """
    for node in nodes:
        node_line = getattr(node, "line", None)
        if cursor_line is not None and node_line is not None and node_line > cursor_line:
            # Sequential structure — once we pass cursor_line stop.
            break

        if isinstance(node, Assume):
            entries.append(ContextEntry(
                label=node.label,
                formula_str=pretty(node.formula),
                formula_raw=node.formula,
                kind="assume",
                line=node.line,
                scope_depth=depth,
                available=True,
            ))
            avail[node.label] = node.formula

        elif isinstance(node, Suppose):
            # Recurse into body to collect inner labels
            inner_entries = []
            inner_avail = {}
            inner_closed = set()
            # The suppose label itself is visible inside the block
            inner_outer = {**avail, node.label: node.formula}
            _walk(node.body, depth + 1, inner_entries, inner_avail, inner_closed,
                  cursor_line)

            # The suppose entry is marked available=False (closed after block)
            sup_entry = ContextEntry(
                label=node.label,
                formula_str=pretty(node.formula),
                formula_raw=node.formula,
                kind="suppose",
                line=node.line,
                scope_depth=depth,
                available=False,
            )
            entries.append(sup_entry)
            # Mark all inner entries as unavailable
            for e in inner_entries:
                e.available = False
            entries.extend(inner_entries)
            # Register all inner labels as closed
            closed.add(node.label)
            closed.update(inner_avail.keys())
            closed.update(inner_closed)

        elif isinstance(node, Have):
            entries.append(ContextEntry(
                label=node.label,
                formula_str=pretty(node.formula),
                formula_raw=node.formula,
                kind="have",
                line=node.line,
                scope_depth=depth,
                available=True,
            ))
            avail[node.label] = node.formula

        # Conclude doesn't introduce a label — skip


def _find_conclude(nodes):
    """Return the first Conclude node's formula in the node list."""
    for node in nodes:
        if isinstance(node, Conclude):
            return node.formula
        if isinstance(node, Suppose):
            result = _find_conclude(node.body)
            if result is not None:
                return result
    return None


# ---------------------------------------------------------------------------
# Public API — proof state extraction
# ---------------------------------------------------------------------------

def proof_state(thm, logic_name=None, cursor_line=None) -> ProofState:
    """Compute a ProofState from a parsed Theorem (UNTRUSTED).

    Parameters
    ----------
    thm : Theorem
        A parsed theorem object (from stele.parser.parse_theorem).
    logic_name : str | None
        Logic override.  If None, uses thm.logic or "intuitionistic_prop".
    cursor_line : int | None
        If given, only include proof steps at or before this line.

    Returns
    -------
    ProofState  (always succeeds; never raises)
    """
    logic = logic_name or thm.logic or "intuitionistic_prop"

    entries = []
    avail = {}
    closed = set()

    _walk(thm.lines, 0, entries, avail, closed, cursor_line)

    # Conclude formula (target)
    conclude_formula = _find_conclude(thm.lines)

    # Open assumptions = top-level assume entries
    open_assumptions = [e.label for e in entries
                        if e.kind == "assume" and e.available]

    # Available labels = all available entries in declaration order
    available_labels = [e.label for e in entries if e.available]

    # Closed labels = sorted
    closed_labels = sorted(closed)

    # Last step = last available label (have or assume)
    last_step = None
    for e in reversed(entries):
        if e.available and e.kind in ("assume", "have"):
            last_step = e.label
            break

    # Target
    target_str = pretty(conclude_formula) if conclude_formula else None

    # Pending goal
    pending_goal = None
    if conclude_formula is not None:
        # If the last step holds the conclude formula, goal is about to be met
        if last_step and avail.get(last_step) == conclude_formula:
            pending_goal = None  # just need the conclude line
        else:
            pending_goal = target_str

    return ProofState(
        theorem=thm.name,
        logic=logic,
        target=target_str,
        target_raw=conclude_formula,
        cursor_line=cursor_line,
        context=entries,
        open_assumptions=open_assumptions,
        available_labels=available_labels,
        closed_labels=closed_labels,
        last_step=last_step,
        pending_goal=pending_goal,
        diagnostics_summary=None,
        parse_error=None,
    )


def proof_state_from_text(text, logic=None, cursor_line=None) -> ProofState:
    """Compute a ProofState from a proof text string (UNTRUSTED).

    Gracefully handles parse errors by returning a ProofState with
    parse_error set rather than raising an exception.
    """
    try:
        from .parser import parse_theorem
        thm = parse_theorem(text)
    except Exception as e:
        return ProofState(
            theorem="(unknown)",
            logic=logic or "intuitionistic_prop",
            target=None,
            target_raw=None,
            cursor_line=cursor_line,
            context=[],
            open_assumptions=[],
            available_labels=[],
            closed_labels=[],
            last_step=None,
            pending_goal=None,
            diagnostics_summary=None,
            parse_error=str(e),
        )
    return proof_state(thm, logic, cursor_line)


def visible_context_at(thm, line) -> list:
    """Return ContextEntry list visible up to (and including) the given line.

    Convenience wrapper around proof_state with cursor_line.
    """
    state = proof_state(thm, cursor_line=line)
    return [e for e in state.context if e.available]


def available_labels_at(thm, line) -> list:
    """Return list of label strings available up to the given line."""
    state = proof_state(thm, cursor_line=line)
    return state.available_labels


# ---------------------------------------------------------------------------
# Rule-applicability hints
# ---------------------------------------------------------------------------

def suggest_rule_hints(state, goal=None, max_hints=8) -> list:
    """Suggest local structural rule applications (UNTRUSTED).

    Hints are local pattern matches on available context formulas and the goal.
    No proof search is performed.  No guarantee of completeness or correctness.
    All returned RuleHint objects have trusted=False.

    Parameters
    ----------
    state : ProofState
    goal : formula (Var | Op) | None
        Override goal formula.  Defaults to state.target_raw.
    max_hints : int
        Maximum number of hints to return.

    Returns
    -------
    list[RuleHint]  (may be empty)
    """
    hints = []

    goal_f = goal if goal is not None else state.target_raw
    avail = {e.label: e.formula_raw
             for e in state.context if e.available}
    is_classical = "classical" in state.logic

    # ── Hints from context formulas ──────────────────────────────────────────

    # mp: context has A → B and A
    _hint_mp(avail, hints)

    # and_elim_left / and_elim_right: context has A ∧ B
    _hint_and_elim(avail, hints)

    # neg_elim: context has A and ¬A
    _hint_neg_elim(avail, hints)

    # ex_falso: context has false/⊥
    if goal_f is not None:
        _hint_ex_falso(avail, goal_f, hints)

    if is_classical:
        # dne: context has ¬¬A
        _hint_dne(avail, hints)

    # ── Hints from goal shape ────────────────────────────────────────────────

    if goal_f is not None:
        # imp_intro: goal is A → B
        _hint_imp_intro(goal_f, hints)

        # and_intro: goal is A ∧ B
        _hint_and_intro(goal_f, hints)

        # or_intro: goal is A ∨ B
        _hint_or_intro(goal_f, avail, hints)

        # neg_intro: goal is ¬A
        _hint_neg_intro(goal_f, hints)

        if is_classical:
            # lem: goal is A ∨ ¬A
            _hint_lem(goal_f, hints)
            # pbc: general low-confidence classical fallback
            _hint_pbc(goal_f, hints)

    # Deduplicate by rule (keep first occurrence)
    seen_rules = set()
    deduped = []
    for h in hints:
        if h.rule not in seen_rules:
            deduped.append(h)
            seen_rules.add(h.rule)

    return deduped[:max_hints]


# ---------------------------------------------------------------------------
# Individual hint generators (private)
# ---------------------------------------------------------------------------

def _hint_mp(avail, hints):
    """mp: context has A → B and A."""
    for label1, f1 in avail.items():
        imp = _is_imp(f1)
        if imp is None:
            continue
        A, B = imp
        for label2, f2 in avail.items():
            if label1 != label2 and f2 == A:
                hints.append(RuleHint(
                    rule="mp",
                    title="Modus Ponens",
                    why_applicable=(
                        f"Context has {pretty(f1)} ({label1}) and"
                        f" {pretty(A)} ({label2})"
                    ),
                    required_refs=[label1, label2],
                    candidate_line_template=(
                        f"have hN: {pretty(B)} by mp {label1} {label2}"
                    ),
                    confidence="high",
                ))
                return  # one mp hint is enough


def _hint_and_elim(avail, hints):
    """and_elim_left/right: context has A ∧ B."""
    for label, f in avail.items():
        parts = _is_and(f)
        if parts is None:
            continue
        A, B = parts
        hints.append(RuleHint(
            rule="and_elim_left",
            title="Conjunction Elimination (left)",
            why_applicable=f"Context has {pretty(f)} ({label})",
            required_refs=[label],
            candidate_line_template=(
                f"have hN: {pretty(A)} by and_elim_left {label}"
            ),
            confidence="medium",
        ))
        hints.append(RuleHint(
            rule="and_elim_right",
            title="Conjunction Elimination (right)",
            why_applicable=f"Context has {pretty(f)} ({label})",
            required_refs=[label],
            candidate_line_template=(
                f"have hN: {pretty(B)} by and_elim_right {label}"
            ),
            confidence="medium",
        ))
        return  # one conjunction is enough


def _hint_neg_elim(avail, hints):
    """neg_elim: context has A and ¬A."""
    for label1, f1 in avail.items():
        body = _is_not(f1)
        if body is None:
            continue
        for label2, f2 in avail.items():
            if label2 != label1 and f2 == body:
                hints.append(RuleHint(
                    rule="neg_elim",
                    title="Negation Elimination",
                    why_applicable=(
                        f"Context has {pretty(f2)} ({label2}) and"
                        f" {pretty(f1)} ({label1})"
                    ),
                    required_refs=[label2, label1],
                    candidate_line_template=(
                        f"have hN: false by neg_elim {label2} {label1}"
                    ),
                    confidence="high",
                ))
                return


def _hint_ex_falso(avail, goal_f, hints):
    """ex_falso: context has ⊥."""
    for label, f in avail.items():
        if _is_bot(f):
            hints.append(RuleHint(
                rule="ex_falso",
                title="Ex Falso (from contradiction)",
                why_applicable=f"Context has ⊥/false ({label})",
                required_refs=[label],
                candidate_line_template=(
                    f"have hN: {pretty(goal_f)} by ex_falso {label}"
                ),
                confidence="high",
            ))
            return


def _hint_dne(avail, hints):
    """dne (classical): context has ¬¬A."""
    for label, f in avail.items():
        inner = _is_double_neg(f)
        if inner is not None:
            hints.append(RuleHint(
                rule="dne",
                title="Double Negation Elimination (classical only)",
                why_applicable=(
                    f"Context has ¬¬{pretty(inner)} ({label})"
                ),
                required_refs=[label],
                candidate_line_template=(
                    f"have hN: {pretty(inner)} by dne {label}"
                ),
                confidence="high",
            ))
            return


def _hint_imp_intro(goal_f, hints):
    """imp_intro: goal is A → B."""
    imp = _is_imp(goal_f)
    if imp is None:
        return
    A, B = imp
    hints.append(RuleHint(
        rule="imp_intro",
        title="Implication Introduction",
        why_applicable=(
            f"Goal has shape {pretty(A)} → {pretty(B)}"
        ),
        required_refs=[],
        candidate_line_template=(
            f"suppose hA: {pretty(A)}\n"
            f"    have hB: {pretty(B)} by ...  "
            f"# derive {pretty(B)} from hA\n"
            f"  have hN: {pretty(goal_f)} by imp_intro hA hB"
        ),
        confidence="high",
    ))


def _hint_and_intro(goal_f, hints):
    """and_intro: goal is A ∧ B."""
    parts = _is_and(goal_f)
    if parts is None:
        return
    A, B = parts
    hints.append(RuleHint(
        rule="and_intro",
        title="Conjunction Introduction",
        why_applicable=(
            f"Goal has shape {pretty(A)} ∧ {pretty(B)}"
        ),
        required_refs=[],
        candidate_line_template=(
            f"# Prove {pretty(A)} as hA, prove {pretty(B)} as hB, then:\n"
            f"  have hN: {pretty(goal_f)} by and_intro hA hB"
        ),
        confidence="medium",
    ))


def _hint_or_intro(goal_f, avail, hints):
    """or_intro_left/right: goal is A ∨ B and context has A or B."""
    parts = _is_or(goal_f)
    if parts is None:
        return
    A, B = parts
    # Check context for left disjunct
    for label, f in avail.items():
        if f == A:
            hints.append(RuleHint(
                rule="or_intro_left",
                title="Disjunction Introduction (left)",
                why_applicable=(
                    f"Goal is {pretty(goal_f)} and context has"
                    f" left disjunct {pretty(A)} ({label})"
                ),
                required_refs=[label],
                candidate_line_template=(
                    f"have hN: {pretty(goal_f)} by or_intro_left {label}"
                ),
                confidence="high",
            ))
    # Check context for right disjunct
    for label, f in avail.items():
        if f == B:
            hints.append(RuleHint(
                rule="or_intro_right",
                title="Disjunction Introduction (right)",
                why_applicable=(
                    f"Goal is {pretty(goal_f)} and context has"
                    f" right disjunct {pretty(B)} ({label})"
                ),
                required_refs=[label],
                candidate_line_template=(
                    f"have hN: {pretty(goal_f)} by or_intro_right {label}"
                ),
                confidence="high",
            ))


def _hint_neg_intro(goal_f, hints):
    """neg_intro: goal is ¬A."""
    body = _is_not(goal_f)
    if body is None:
        return
    hints.append(RuleHint(
        rule="neg_intro",
        title="Negation Introduction",
        why_applicable=(
            f"Goal has shape ¬{pretty(body)}"
        ),
        required_refs=[],
        candidate_line_template=(
            f"suppose hA: {pretty(body)}\n"
            f"    have hBot: false by ...  # derive contradiction\n"
            f"  have hN: {pretty(goal_f)} by neg_intro hA hBot"
        ),
        confidence="high",
    ))


def _hint_lem(goal_f, hints):
    """lem (classical): goal is A ∨ ¬A."""
    a = _is_lem_shape(goal_f)
    if a is None:
        return
    hints.append(RuleHint(
        rule="lem",
        title="Law of Excluded Middle (classical only)",
        why_applicable=(
            f"Goal has shape {pretty(a)} ∨ ¬{pretty(a)}"
        ),
        required_refs=[],
        candidate_line_template=(
            f"have hN: {pretty(goal_f)} by lem"
        ),
        confidence="high",
    ))


def _hint_pbc(goal_f, hints):
    """pbc (classical): general low-confidence fallback."""
    hints.append(RuleHint(
        rule="pbc",
        title="Proof by Contradiction (classical only)",
        why_applicable="Classical logic is available; pbc assumes ¬goal and derives ⊥",
        required_refs=[],
        candidate_line_template=(
            f"suppose hNot: not ({pretty(goal_f)})\n"
            f"    have hBot: false by ...  # derive contradiction\n"
            f"  have hN: {pretty(goal_f)} by pbc hNot hBot"
        ),
        confidence="low",
    ))


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def proof_state_to_dict(state) -> dict:
    """Serialize a ProofState to a JSON-compatible dict."""
    return {
        "theorem": state.theorem,
        "logic": state.logic,
        "target": state.target,
        "cursor_line": state.cursor_line,
        "context": [
            {
                "label": e.label,
                "formula": e.formula_str,
                "kind": e.kind,
                "line": e.line,
                "scope_depth": e.scope_depth,
                "available": e.available,
            }
            for e in state.context
        ],
        "open_assumptions": state.open_assumptions,
        "available_labels": state.available_labels,
        "closed_labels": state.closed_labels,
        "last_step": state.last_step,
        "pending_goal": state.pending_goal,
        "diagnostics_summary": state.diagnostics_summary,
        "parse_error": state.parse_error,
    }


def rule_hints_to_list(hints) -> list:
    """Serialize a list of RuleHint to JSON-compatible list."""
    return [
        {
            "rule": h.rule,
            "title": h.title,
            "why_applicable": h.why_applicable,
            "required_refs": h.required_refs,
            "candidate_line_template": h.candidate_line_template,
            "confidence": h.confidence,
            "trusted": False,
        }
        for h in hints
    ]
