"""Structural diagnostics: collect classified proof issues without stopping at the first error.

This module is an UNTRUSTED analysis layer. It is intentionally separate from the trusted
kernel (stele/kernel.py). The kernel remains the sole authority for proof validity.
These diagnostics are for user feedback and failure-mode taxonomy, not for proof verification.

Entry points:
  diagnose_theorem(thm, logic_name=None) -> list[Diagnostic]
  diagnose_graph(g, label_lines=None)    -> list[Diagnostic]  (for synthetic graph tests)
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
      CircularDependency, UnusedAssumption
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

    Does NOT call the trusted kernel. Does NOT stop at the first issue.
    Performs two passes:
      1. Scope analysis   → UndefinedSymbol, MissingHypothesis, UnsupportedConclusion
      2. Graph analysis   → CircularDependency, UnusedAssumption
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

    # Pass 1: scope analysis
    _diagnose_block(thm.lines, {}, all_labels, [], diags, logic)

    # Pass 2: graph analysis
    from .proofgraph import build_proof_graph
    g = build_proof_graph(thm)
    diags.extend(diagnose_graph(g, label_lines))

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
