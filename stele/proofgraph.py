"""Proof dependency graph: structural analysis of verified proof objects.

Given a parsed Theorem, build_proof_graph() produces a ProofGraph whose
nodes are labeled proof steps and whose directed edges represent dependency
(dep → step: "dep is used by step").

This module is an analysis layer only. It does NOT perform proof checking;
call stele.kernel.check_theorem() first if you need a validated proof graph.
No imports from kernel.py (trust boundary preserved).
"""
from dataclasses import dataclass, field
from .ast import pretty
from .proof import Assume, Have, Suppose, Conclude


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ProofNode:
    """A single labeled node in the proof dependency graph."""
    label: str
    kind: str     # "assumption" | "suppose" | "have" | "conclude"
    formula: str  # pretty-printed formula string
    rule: str     # rule name for 'have' steps; None otherwise


@dataclass
class ProofGraph:
    """Directed proof dependency graph built from a parsed proof.

    Edges have direction:  dep → step  (dep is a dependency of step).
    That is, an edge (a, b) means "step b uses label a."

    The graph flows from assumptions at the source toward the conclusion.
    """
    name: str
    nodes: dict = field(default_factory=dict)    # label -> ProofNode
    edges: list = field(default_factory=list)    # list of (src_label, tgt_label)
    conclusion: str = None                       # label of the _conclude node


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_proof_graph(thm):
    """Build a ProofGraph from a parsed Theorem.

    All Assume, Suppose, Have, and Conclude nodes are included.
    Dependency edges are derived from the refs in each Have node.
    The Conclude step is represented by a synthetic '_conclude' node.
    """
    g = ProofGraph(name=thm.name)
    _visit_block(thm.lines, g)
    return g


def _visit_block(lines, g):
    for node in lines:
        if isinstance(node, Assume):
            g.nodes[node.label] = ProofNode(
                label=node.label,
                kind="assumption",
                formula=pretty(node.formula),
                rule=None,
            )
        elif isinstance(node, Suppose):
            g.nodes[node.label] = ProofNode(
                label=node.label,
                kind="suppose",
                formula=pretty(node.formula),
                rule=None,
            )
            _visit_block(node.body, g)
        elif isinstance(node, Have):
            g.nodes[node.label] = ProofNode(
                label=node.label,
                kind="have",
                formula=pretty(node.formula),
                rule=node.rule,
            )
            # Every ref (ordinary premise or discharge pair component) is a dep.
            for ref in node.refs:
                g.edges.append((ref, node.label))
        elif isinstance(node, Conclude):
            g.nodes["_conclude"] = ProofNode(
                label="_conclude",
                kind="conclude",
                formula=pretty(node.formula),
                rule=None,
            )
            g.edges.append((node.ref, "_conclude"))
            g.conclusion = "_conclude"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _adjacency(g):
    """Return dict: label -> list of labels this node points to (edges src->tgt)."""
    adj = {label: [] for label in g.nodes}
    for src, tgt in g.edges:
        if src in adj:
            adj[src].append(tgt)
    return adj


def _reverse_adjacency(g):
    """Return dict: label -> set of labels that point TO this node."""
    rev = {label: set() for label in g.nodes}
    for src, tgt in g.edges:
        if tgt in rev:
            rev[tgt].add(src)
    return rev


def _backward_reachable(g):
    """BFS from _conclude following edges backward; return reachable label set."""
    if g.conclusion not in g.nodes:
        return set()
    rev = _reverse_adjacency(g)
    reachable = {g.conclusion}
    queue = [g.conclusion]
    while queue:
        node = queue.pop()
        for pred in rev.get(node, set()):
            if pred not in reachable:
                reachable.add(pred)
                queue.append(pred)
    return reachable


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def has_cycle(g):
    """Return True if the dependency graph contains a directed cycle.

    In a successfully verified proof cycles cannot occur (proof trees are
    acyclic by construction). This check is defensive: it guards against
    graph-manipulation bugs and tests future tooling.
    """
    adj = _adjacency(g)
    # DFS coloring: 0=unvisited, 1=in stack, 2=done
    color = {label: 0 for label in g.nodes}

    def dfs(u):
        color[u] = 1
        for v in adj.get(u, []):
            if v not in color:
                continue
            if color[v] == 1:
                return True
            if color[v] == 0 and dfs(v):
                return True
        color[u] = 2
        return False

    for label in g.nodes:
        if color[label] == 0 and dfs(label):
            return True
    return False


def find_unused_assumptions(g):
    """Return labels of assumption/suppose nodes not reachable from conclusion.

    A discharged assumption that is cited in a subproof IS counted as used,
    because the discharge refs appear directly in the have-node refs and
    create edges into the graph.
    """
    reachable = _backward_reachable(g)
    return {
        label
        for label, node in g.nodes.items()
        if node.kind in ("assumption", "suppose") and label not in reachable
    }


def find_isolated_steps(g):
    """Return labels of 'have' nodes not contributing to the conclusion."""
    reachable = _backward_reachable(g)
    return {
        label
        for label, node in g.nodes.items()
        if node.kind == "have" and label not in reachable
    }


# ---------------------------------------------------------------------------
# DOT export
# ---------------------------------------------------------------------------

_KIND_COLOR = {
    "assumption": "lightblue",
    "suppose":    "lightyellow",
    "have":       "white",
    "conclude":   "lightgreen",
}


def to_dot(g):
    """Return plain DOT text for the graph. No external dependencies required.

    Render with: dot -Tpng out.dot -o out.png  (if Graphviz is installed;
    Graphviz is NOT a project dependency — DOT text is the deliverable).
    """
    lines = [f'digraph "{g.name}" {{', "  rankdir=TB;"]

    for label, node in g.nodes.items():
        color = _KIND_COLOR.get(node.kind, "white")
        parts = [label]
        if node.formula:
            parts.append(node.formula)
        if node.rule:
            parts.append(f"[{node.rule}]")
        display = "\\n".join(p.replace('"', '\\"') for p in parts)
        lines.append(
            f'  "{label}" [label="{display}", shape=box,'
            f" style=filled, fillcolor={color}];"
        )

    for src, tgt in g.edges:
        lines.append(f'  "{src}" -> "{tgt}";')

    lines.append("}")
    return "\n".join(lines)
