"""Structural diagnostics: collect classified proof issues without stopping at the first error.

This module is an UNTRUSTED analysis layer. It is intentionally separate from the trusted
kernel (stele/kernel.py). The kernel remains the sole authority for proof validity.
These diagnostics are for user feedback and failure-mode taxonomy, not for proof verification.

Entry points:
  diagnose_theorem(thm, logic_name=None) -> list[Diagnostic]
  diagnose_graph(g, label_lines=None)    -> list[Diagnostic]  (for synthetic graph tests)

Stable diagnostic codes (tests and benchmark datasets rely on these strings):
  UndefinedSymbol      — ref not defined anywhere in the proof
  MissingHypothesis    — ref exists but out of scope
  UnsupportedConclusion — conclude formula does not match referenced label
  CircularDependency   — directed cycle in proof dependency graph
  UnusedAssumption     — assumption not contributing to conclusion
  UndefinedDefinition  — definition body references an undefined name (v1: heuristic)
  InvalidTransition    — in-scope refs but rule application fails (classified from kernel)
  TypeMismatch         — sort-level mismatch (v1 machinery only; no surface trigger yet)
  KripkeCountermodelFound — additive info hint: finite Kripke countermodel found (info only,
                            additive alongside InvalidTransition; never a kernel replacement)
"""
from dataclasses import dataclass
from .ast import pretty
from .proof import Assume, Have, Suppose, Conclude


# ---------------------------------------------------------------------------
# Diagnostic data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Diagnostic:
    """An immutable classified proof issue.

    Stable code strings (relied on by tests and future benchmark datasets):
      UndefinedSymbol, MissingHypothesis, UnsupportedConclusion,
      CircularDependency, UnusedAssumption,
      UndefinedDefinition, InvalidTransition, TypeMismatch,
      KripkeCountermodelFound (info-only)
    """
    code: str          # one of the stable code strings above
    message: str       # human-readable explanation
    line: object       # int | None (best-effort; None = position unknown)
    severity: str      # "error" | "warning" | "info"


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def diagnose_theorem(thm, logic_name=None):
    """Return a list of Diagnostic for structural issues in thm.

    Does NOT stop at the first issue. Performs multiple passes:
      Pass 0: Definition analysis  → UndefinedDefinition
      Pass 1: Scope analysis       → UndefinedSymbol, MissingHypothesis, UnsupportedConclusion
      Pass 2: Graph analysis       → CircularDependency, UnusedAssumption
      Pass 3: Kernel classification → InvalidTransition (only when pass 1 is error-free)
      Pass 4: Kripke hint (info)   → KripkeCountermodelFound (intuitionistic_prop + InvalidTransition)
    """
    diags = []
    all_labels = _collect_all_labels(thm.lines)
    label_lines = _collect_label_lines(thm.lines)

    # Resolve logic for schema-aware ref checking (best-effort; not required).
    logic = None
    name = logic_name or thm.logic or "intuitionistic_prop"
    try:
        from .logic import get_logic
        logic = get_logic(name)
    except Exception:
        pass  # fall back to permissive checking

    # Pass 0: definition analysis (UndefinedDefinition)
    _check_undef_definitions(thm, diags)

    # Pass 1: scope analysis
    _diagnose_block(thm.lines, {}, all_labels, [], diags, logic)

    # Snapshot errors after scope analysis (before graph analysis adds warnings).
    scope_errors = [d for d in diags if d.severity == "error"]

    # Pass 2: graph analysis (CircularDependency, UnusedAssumption)
    from .proofgraph import build_proof_graph
    g = build_proof_graph(thm)
    diags.extend(diagnose_graph(g, label_lines))

    # Pass 3: InvalidTransition — classify kernel rule-failure errors.
    # Only run when no scope errors; kernel errors would duplicate scope errors otherwise.
    if not scope_errors and logic is not None and logic.semantics == "proof":
        _check_invalid_transitions(thm, name, diags)

    # Pass 4: Kripke countermodel hint — additive info, only safe cases.
    # Fires when (a) logic is intuitionistic_prop AND (b) no scope errors.
    # _attach_kripke_hint re-runs the kernel to confirm a rule failure (including
    # "not available" which Pass 3 does not classify as InvalidTransition).
    # This pass NEVER replaces a kernel error; it is informational only.
    if not scope_errors and name == "intuitionistic_prop":
        _attach_kripke_hint(thm, diags)

    return diags


def diagnose_graph(g, label_lines=None):
    """Run graph-level diagnostics on a ProofGraph.

    Accepts synthetic ProofGraph objects so that CircularDependency can be
    tested without constructing a proof that the parser/kernel would reject.
    """
    if label_lines is None:
        label_lines = {}
    diags = []
    from .proofgraph import has_cycle, find_unused_assumptions
    if has_cycle(g):
        diags.append(Diagnostic(
            "CircularDependency",
            "dependency graph contains a directed cycle",
            None,
            "error",
        ))
    for label in sorted(find_unused_assumptions(g)):
        diags.append(Diagnostic(
            "UnusedAssumption",
            f"assumption '{label}' does not contribute to the conclusion",
            label_lines.get(label),
            "warning",
        ))
    return diags


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _collect_all_labels(lines):
    """Return the set of every label defined anywhere in the proof tree."""
    labels = set()
    for node in lines:
        if isinstance(node, (Assume, Suppose, Have)):
            labels.add(node.label)
        if isinstance(node, Suppose):
            labels |= _collect_all_labels(node.body)
    return labels


def _collect_label_lines(lines):
    """Return dict: label -> source line number (first occurrence wins)."""
    result = {}
    for node in lines:
        if isinstance(node, (Assume, Suppose, Have)) and node.label not in result:
            result[node.label] = node.line
        if isinstance(node, Suppose):
            for k, v in _collect_label_lines(node.body).items():
                if k not in result:
                    result[k] = v
    return result


def _accessible(ref, env, subproofs):
    """Return True if ref is reachable from the current position.

    'Accessible' means: in env (ordinary scope) OR is a subproof assume-label
    OR is in a closed sibling subproof's local dict (discharge refs live there).
    This is permissive — used only when no schema is available.
    """
    if ref in env:
        return True
    for (sp_assume, _, sp_locals) in subproofs:
        if ref == sp_assume or ref in sp_locals:
            return True
    return False


def _diagnose_block(lines, env, all_labels, subproofs, diags, logic):
    """Walk one proof block, collecting diagnostics without stopping.

    Mirrors the structure of kernel._check_block but does not raise on errors;
    instead appends Diagnostic objects and continues for multi-error collection.
    env and subproofs are mutated in place (same pattern as kernel).
    """
    for node in lines:
        if isinstance(node, Assume):
            env[node.label] = node.formula

        elif isinstance(node, Suppose):
            inner = dict(env)
            inner[node.label] = node.formula
            _diagnose_block(node.body, inner, all_labels, [], diags, logic)
            local = {k: v for k, v in inner.items() if k not in env}
            subproofs.append((node.label, node.formula, local))

        elif isinstance(node, Have):
            _check_have_refs(node, env, all_labels, subproofs, diags, logic)
            env[node.label] = node.formula

        elif isinstance(node, Conclude):
            _check_conclude(node, env, all_labels, diags)


def _check_have_refs(node, env, all_labels, subproofs, diags, logic):
    """Classify refs in a Have step as UndefinedSymbol or MissingHypothesis.

    When the logic is known, refs are classified schema-accurately:
    - ordinary premises must be in env (same as kernel)
    - discharge pairs (a, b) must match a closed sibling subproof (same as kernel)

    When the logic is unknown (no schema), a permissive _accessible check is used
    to avoid false positives on unfamiliar rules.
    """
    schema = logic.rules.get(node.rule) if (logic and logic.semantics == "proof") else None

    if schema is None:
        # Permissive fallback: accept anything in env OR any sibling subproof
        for ref in node.refs:
            if ref not in all_labels:
                diags.append(Diagnostic(
                    "UndefinedSymbol",
                    f"cited label '{ref}' does not exist in this proof",
                    node.line,
                    "error",
                ))
            elif not _accessible(ref, env, subproofs):
                diags.append(Diagnostic(
                    "MissingHypothesis",
                    f"label '{ref}' exists but is not available at this point",
                    node.line,
                    "error",
                ))
        return

    n_ord = len(schema.premises)
    n_hyp = len(schema.hyp_premises)

    # Ordinary premises: must be in env (same check as kernel._apply_rule).
    for ref in node.refs[:n_ord]:
        if ref not in all_labels:
            diags.append(Diagnostic(
                "UndefinedSymbol",
                f"cited label '{ref}' does not exist in this proof",
                node.line,
                "error",
            ))
        elif ref not in env:
            diags.append(Diagnostic(
                "MissingHypothesis",
                f"label '{ref}' exists but is not in scope "
                f"(used as ordinary premise for rule '{node.rule}')",
                node.line,
                "error",
            ))

    # Discharge pairs: (a, b) must appear in a closed sibling subproof.
    hyp_refs = node.refs[n_ord:]
    for j in range(n_hyp):
        idx = 2 * j
        if idx + 1 >= len(hyp_refs):
            break  # wrong ref count — kernel will report the arity mismatch
        a, b = hyp_refs[idx], hyp_refs[idx + 1]
        for ref in (a, b):
            if ref not in all_labels:
                diags.append(Diagnostic(
                    "UndefinedSymbol",
                    f"cited label '{ref}' does not exist in this proof",
                    node.line,
                    "error",
                ))
        if a in all_labels and b in all_labels:
            found = any(sp[0] == a and b in sp[2] for sp in subproofs)
            if not found:
                diags.append(Diagnostic(
                    "MissingHypothesis",
                    f"no closed subproof found assuming '{a}' with '{b}' derived inside",
                    node.line,
                    "error",
                ))


def _check_conclude(node, env, all_labels, diags):
    """Check the conclude step for scope and formula-match errors."""
    ref = node.ref
    if ref not in all_labels:
        diags.append(Diagnostic(
            "UndefinedSymbol",
            f"conclude references nonexistent label '{ref}'",
            node.line,
            "error",
        ))
    elif ref not in env:
        diags.append(Diagnostic(
            "MissingHypothesis",
            f"conclude references out-of-scope label '{ref}'",
            node.line,
            "error",
        ))
    elif env[ref] != node.formula:
        diags.append(Diagnostic(
            "UnsupportedConclusion",
            f"conclusion {pretty(node.formula)!r} does not match "
            f"'{ref}' = {pretty(env[ref])!r}",
            node.line,
            "error",
        ))


# ---------------------------------------------------------------------------
# New diagnostic passes (v1 extension)
# ---------------------------------------------------------------------------

def _is_def_like_name(name):
    """Heuristic: does this identifier look like a definition name rather than a prop variable?

    Prop variables in Stele examples are typically single uppercase letters (P, Q, R, ...).
    Definition names are multi-character identifiers, often containing underscores.

    Rule: multi-char, all-uppercase (including underscores) and not a keyword.

    v1 LIMITATION: multi-character prop variables such as 'PHI' or 'PP' will be treated
    as potential definition names by this heuristic. Document this and only test clear cases.
    """
    if len(name) <= 1:
        return False
    # All chars uppercase or underscore, at least one letter
    return name.upper() == name and any(c.isalpha() for c in name)


def _scan_def_body_for_undef(formula, defs_dict, line, diags):
    """Recursively scan a definition formula for undefined definition references."""
    from .ast import Var, Op
    if isinstance(formula, Var):
        if _is_def_like_name(formula.name) and formula.name not in defs_dict:
            diags.append(Diagnostic(
                "UndefinedDefinition",
                f"definition body references '{formula.name}' "
                f"which is not a defined name in this file",
                line,
                "warning",
            ))
    elif isinstance(formula, Op):
        for arg in formula.args:
            _scan_def_body_for_undef(arg, defs_dict, line, diags)


def _check_undef_definitions(thm, diags):
    """Pass 0: scan definition bodies for references to missing definitions."""
    if not thm.definitions:
        return
    defs_dict = {d.name: d for d in thm.definitions}
    for defn in thm.definitions:
        _scan_def_body_for_undef(defn.formula, defs_dict, defn.line, diags)


def _check_invalid_transitions(thm, logic_name, diags):
    """Pass 3: try the trusted kernel; classify rule-application failures as InvalidTransition.

    Called only when scope analysis found no errors, so the kernel's exception is
    not a scope issue (those are already covered by UndefinedSymbol/MissingHypothesis).

    The kernel remains the sole authority — diagnostics only classify its output.
    """
    from .kernel import check_theorem
    from .errors import ProofError
    try:
        check_theorem(thm, logic_name)
    except ProofError as e:
        msg = str(e)
        line = getattr(e, "line", None)
        # Classify as InvalidTransition: rule applied to valid refs but application failed.
        # Kernel messages for rule failures contain "rule '" but NOT "is not available"
        # (which indicates an unknown rule, a different category).
        if "rule '" in msg and "is not available" not in msg:
            diags.append(Diagnostic("InvalidTransition", msg, line, "error"))
        # Other ProofError types (no conclude, duplicate label) are structural issues
        # not covered by this pass.


def _attach_kripke_hint(thm, diags):
    """Pass 4: optionally attach a KripkeCountermodelFound info diagnostic.

    Safe cases ONLY:
      - Logic is intuitionistic_prop (caller checks this)
      - No scope errors (caller checks)
      - Kernel rejects with "rule X is not available" (classical-only rule)
      - A Kripke countermodel exists within 3 worlds

    Deliberately excludes wrong-premises errors and structural issues.
    Never replaces a kernel error — adds an info note alongside.
    """
    # Only fire for "rule X is not available" (classical-only rule used under
    # intuitionistic logic). Ignore wrong-premise errors and structural issues.
    from .kernel import check_theorem
    from .errors import ProofError
    try:
        check_theorem(thm, "intuitionistic_prop")
        return  # proof passed; nothing to annotate
    except ProofError as e:
        if "is not available" not in str(e):
            return  # not a classical-only rule; no semantic interpretation
    except Exception:
        return

    # Extract the theorem's conclude formula (the first Conclude node).
    conclude_formula = None
    for node in thm.lines:
        if isinstance(node, Conclude):
            conclude_formula = node.formula
            break
    if conclude_formula is None:
        return

    try:
        from .kripke import kripke_explain
        from .ast import pretty as pretty_formula
    except Exception:
        return

    try:
        ex = kripke_explain(conclude_formula, max_worlds=3,
                            formula_str=pretty_formula(conclude_formula))
    except Exception:
        return

    if ex.status != "countermodel_found":
        return

    diags.append(Diagnostic(
        "KripkeCountermodelFound",
        (
            f"Kripke countermodel (≤3 worlds): '{ex.formula}' fails at world "
            f"{ex.failing_world}. "
            f"worlds={ex.worlds}, "
            f"order={ex.order_pairs}, "
            f"valuation={ex.valuation}. "
            f"Note: proof-check failure ≠ semantic non-derivability; "
            f"this is an independent semantic witness."
        ),
        None,
        "info",
    ))


# ---------------------------------------------------------------------------
# Diagnostic explanations (static catalog)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DiagnosticExplanation:
    """Human-readable explanation of a diagnostic code.

    Fields:
      code          — stable diagnostic code string
      short         — one-line summary
      likely_cause  — common root cause
      how_to_fix    — actionable suggestion
      example       — illustrative snippet (may be empty string)
      related       — guide section or rule reference
    """
    code: str
    short: str
    likely_cause: str
    how_to_fix: str
    example: str
    related: str


_EXPLANATION_CATALOG = {
    "UndefinedSymbol": DiagnosticExplanation(
        code="UndefinedSymbol",
        short="A cited label does not exist anywhere in this proof.",
        likely_cause=(
            "Typo in the label name, or referencing a label before it is introduced."
        ),
        how_to_fix=(
            "Check the spelling of the label. Ensure it is introduced "
            "(via assume, suppose, or have) before it is cited."
        ),
        example=(
            "assume h1: P -> Q\n"
            "assume h2: P\n"
            "have h3: Q by mp h1 missing  # 'missing' was never introduced"
        ),
        related="GUIDE.md §4",
    ),
    "MissingHypothesis": DiagnosticExplanation(
        code="MissingHypothesis",
        short="A cited label exists but is not in scope at this point.",
        likely_cause=(
            "Referencing a label introduced inside a suppose block "
            "after that block has closed (scope leak)."
        ),
        how_to_fix=(
            "Move the reference inside the suppose block, or restructure "
            "the proof so discharged labels are not reused."
        ),
        example=(
            "suppose h1: P\n"
            "    have h2: P by copy h1\n"
            "  have h3: P by copy h2  # h2 is out of scope here"
        ),
        related="GUIDE.md §6 (discharge rules)",
    ),
    "UnsupportedConclusion": DiagnosticExplanation(
        code="UnsupportedConclusion",
        short="The conclude formula does not match the referenced label.",
        likely_cause=(
            "The conclude formula was edited without updating the cited "
            "label, or the wrong label was cited."
        ),
        how_to_fix=(
            "Ensure the formula after 'conclude' exactly matches the formula "
            "held by the cited label."
        ),
        example=(
            "assume h1: P\n"
            "conclude Q by h1  # h1 holds P, not Q"
        ),
        related="GUIDE.md §5",
    ),
    "CircularDependency": DiagnosticExplanation(
        code="CircularDependency",
        short="The proof dependency graph contains a directed cycle.",
        likely_cause=(
            "Two or more steps mutually depend on each other."
        ),
        how_to_fix=(
            "Review the refs of each step. Ensure no step (directly or "
            "indirectly) depends on itself."
        ),
        example="",
        related="GUIDE.md §10",
    ),
    "UnusedAssumption": DiagnosticExplanation(
        code="UnusedAssumption",
        short="An assumption is declared but never contributes to the conclusion.",
        likely_cause=(
            "An extra assume was added and forgotten, or the proof was "
            "restructured leaving an assumption behind."
        ),
        how_to_fix=(
            "Remove the unused assume line, or use the assumption "
            "in the proof chain leading to the conclusion."
        ),
        example=(
            "assume h1: P\n"
            "assume h2: Q  # never used\n"
            "conclude P by h1"
        ),
        related="GUIDE.md §4",
    ),
    "UndefinedDefinition": DiagnosticExplanation(
        code="UndefinedDefinition",
        short="A definition body references a name not defined in this file.",
        likely_cause=(
            "The definition refers to another definition that is missing "
            "or misspelled."
        ),
        how_to_fix=(
            "Add the missing definition above this one, or correct the spelling."
        ),
        example="",
        related="GUIDE.md §9",
    ),
    "InvalidTransition": DiagnosticExplanation(
        code="InvalidTransition",
        short="A proof step applies a rule to valid refs but the application fails.",
        likely_cause=(
            "The cited premises do not have the formula shapes required "
            "by the rule, or the claimed conclusion does not match what "
            "the rule produces."
        ),
        how_to_fix=(
            "Check the rule's premise requirements in GUIDE.md §7. "
            "Ensure cited labels hold the correct formula shapes."
        ),
        example=(
            "assume h1: P -> Q\n"
            "assume h2: R\n"
            "have h3: Q by mp h1 h2  # mp needs A -> B and A; h2 is R, not P"
        ),
        related="GUIDE.md §7 (inference rules)",
    ),
    "TypeMismatch": DiagnosticExplanation(
        code="TypeMismatch",
        short="A sort-level or type mismatch was detected.",
        likely_cause=(
            "A term or type in the proof-term layer does not satisfy "
            "the typing judgment."
        ),
        how_to_fix=(
            "Review the proof-term structure. This error is uncommon in "
            "surface Stele-Light proofs."
        ),
        example="",
        related="docs/semantics.md",
    ),
    "KripkeCountermodelFound": DiagnosticExplanation(
        code="KripkeCountermodelFound",
        short=(
            "A finite Kripke countermodel was found for the conclusion "
            "under intuitionistic logic."
        ),
        likely_cause=(
            "The formula is classically valid but not intuitionistically "
            "valid. The proof uses a classical-only rule (e.g. dne, lem, pbc)."
        ),
        how_to_fix=(
            "Switch to classical_prop if the classical rule is intentional. "
            "Or restructure the proof using only intuitionistic rules."
        ),
        example="",
        related="GUIDE.md §24 (Kripke semantics)",
    ),
}

_FALLBACK_EXPLANATION = DiagnosticExplanation(
    code="(unknown)",
    short="No explanation available for this diagnostic code.",
    likely_cause="The diagnostic code is not in the static catalog.",
    how_to_fix="Check the proof structure for the location flagged by this diagnostic.",
    example="",
    related="GUIDE.md",
)


def explain_diagnostic(diag) -> DiagnosticExplanation:
    """Return a static DiagnosticExplanation for the given Diagnostic.

    Never raises.  Falls back to a generic explanation for unknown codes.
    """
    return _EXPLANATION_CATALOG.get(diag.code, _FALLBACK_EXPLANATION)


def explain_diagnostic_code(code: str) -> DiagnosticExplanation:
    """Return a static DiagnosticExplanation for the given code string.

    Never raises.  Falls back to a generic explanation for unknown codes.
    """
    return _EXPLANATION_CATALOG.get(code, _FALLBACK_EXPLANATION)
