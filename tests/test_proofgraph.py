"""Tests for stele/proofgraph.py: dependency graph, diagnostics, DOT export."""
import pytest
from stele.parser import parse_theorem
from stele.proofgraph import (
    ProofGraph, ProofNode,
    build_proof_graph, to_dot,
    has_cycle, find_unused_assumptions, find_isolated_steps,
)

# ---------------------------------------------------------------------------
# Simple proof fixture
# ---------------------------------------------------------------------------

_SIMPLE = """
theorem simple:
  assume h1: P -> Q
  assume h2: P
  have h3: Q by mp h1 h2
  conclude Q by h3
"""

_IMP_INTRO = """
theorem imp_i:
  suppose h1: P
    have h2: P by copy h1
  have h3: P -> P by imp_intro h1 h2
  conclude P -> P by h3
"""

_PEIRCE = open("examples/peirce.stele", encoding="utf-8").read()


def _build(src):
    return build_proof_graph(parse_theorem(src))


# ---------------------------------------------------------------------------
# 1. Build graph from simple valid proof
# ---------------------------------------------------------------------------

def test_build_simple_nodes():
    g = _build(_SIMPLE)
    assert "h1" in g.nodes
    assert "h2" in g.nodes
    assert "h3" in g.nodes
    assert "_conclude" in g.nodes


def test_build_node_kinds():
    g = _build(_SIMPLE)
    assert g.nodes["h1"].kind == "assumption"
    assert g.nodes["h2"].kind == "assumption"
    assert g.nodes["h3"].kind == "have"
    assert g.nodes["_conclude"].kind == "conclude"


def test_build_node_rule():
    g = _build(_SIMPLE)
    assert g.nodes["h3"].rule == "mp"
    assert g.nodes["h1"].rule is None
    assert g.nodes["_conclude"].rule is None


def test_build_node_formula():
    g = _build(_SIMPLE)
    assert "P" in g.nodes["h1"].formula
    assert "Q" in g.nodes["h3"].formula


def test_build_conclude_label():
    g = _build(_SIMPLE)
    assert g.conclusion == "_conclude"


def test_build_suppose_node_kind():
    g = _build(_IMP_INTRO)
    assert g.nodes["h1"].kind == "suppose"


# ---------------------------------------------------------------------------
# 2. Dependency edges from rule references
# ---------------------------------------------------------------------------

def test_edges_mp():
    """mp h1 h2 → edges h1→h3, h2→h3."""
    g = _build(_SIMPLE)
    assert ("h1", "h3") in g.edges
    assert ("h2", "h3") in g.edges


def test_edges_conclude():
    """conclude step references h3 → edge h3→_conclude."""
    g = _build(_SIMPLE)
    assert ("h3", "_conclude") in g.edges


def test_edges_imp_intro_discharge():
    """imp_intro h1 h2 cites both the suppose label and the conclusion label."""
    g = _build(_IMP_INTRO)
    assert ("h1", "h3") in g.edges
    assert ("h2", "h3") in g.edges


def test_peirce_all_edges():
    """Peirce's law graph has 14 edges (verified by smoke test)."""
    g = _build(_PEIRCE)
    assert len(g.edges) == 14


def test_peirce_edge_neg_elim():
    """neg_elim hp hnp → edges hp→hbot, hnp→hbot."""
    g = _build(_PEIRCE)
    assert ("hp", "hbot") in g.edges
    assert ("hnp", "hbot") in g.edges


def test_peirce_edge_pbc():
    """pbc hnp hbot2 → edges hnp→hp3, hbot2→hp3."""
    g = _build(_PEIRCE)
    assert ("hnp", "hp3") in g.edges
    assert ("hbot2", "hp3") in g.edges


# ---------------------------------------------------------------------------
# 3. DOT output
# ---------------------------------------------------------------------------

def test_dot_contains_digraph():
    g = _build(_SIMPLE)
    dot = to_dot(g)
    assert "digraph" in dot


def test_dot_contains_node_labels():
    g = _build(_SIMPLE)
    dot = to_dot(g)
    assert '"h1"' in dot
    assert '"h3"' in dot
    assert '"_conclude"' in dot


def test_dot_contains_edges():
    g = _build(_SIMPLE)
    dot = to_dot(g)
    assert "->" in dot
    assert '"h1" -> "h3"' in dot


def test_dot_contains_rule():
    g = _build(_SIMPLE)
    dot = to_dot(g)
    # h3 has rule mp; it should appear in the label
    assert "mp" in dot


def test_dot_name_in_header():
    g = _build(_SIMPLE)
    dot = to_dot(g)
    assert "simple" in dot


def test_dot_peirce():
    g = _build(_PEIRCE)
    dot = to_dot(g)
    assert "peirce" in dot
    assert '"h" ->' in dot


# ---------------------------------------------------------------------------
# 4. Cycle detection
# ---------------------------------------------------------------------------

def test_no_cycle_valid_proof():
    """A successfully verified proof has no cycle."""
    g = _build(_SIMPLE)
    assert not has_cycle(g)


def test_no_cycle_peirce():
    g = _build(_PEIRCE)
    assert not has_cycle(g)


def test_synthetic_cycle_two_nodes():
    """Two nodes pointing at each other form a cycle."""
    g = ProofGraph(name="synthetic")
    g.nodes["a"] = ProofNode("a", "have", "P", "copy")
    g.nodes["b"] = ProofNode("b", "have", "Q", "copy")
    g.edges.append(("a", "b"))
    g.edges.append(("b", "a"))
    assert has_cycle(g)


def test_synthetic_cycle_three_nodes():
    """Three-node cycle: a→b→c→a."""
    g = ProofGraph(name="tri")
    for lbl in ("a", "b", "c"):
        g.nodes[lbl] = ProofNode(lbl, "have", lbl, None)
    g.edges += [("a", "b"), ("b", "c"), ("c", "a")]
    assert has_cycle(g)


def test_synthetic_no_cycle_chain():
    """Linear chain a→b→c has no cycle."""
    g = ProofGraph(name="chain")
    for lbl in ("a", "b", "c"):
        g.nodes[lbl] = ProofNode(lbl, "have", lbl, None)
    g.edges += [("a", "b"), ("b", "c")]
    assert not has_cycle(g)


# ---------------------------------------------------------------------------
# 5. Unused assumptions and isolated steps
# ---------------------------------------------------------------------------

def test_no_unused_in_simple_proof():
    g = _build(_SIMPLE)
    assert find_unused_assumptions(g) == set()


def test_no_isolated_steps_in_simple_proof():
    g = _build(_SIMPLE)
    assert find_isolated_steps(g) == set()


def test_synthetic_unused_assumption():
    """An assumption with no outgoing edges toward conclusion is unused."""
    g = ProofGraph(name="test", conclusion="_conclude")
    g.nodes["h1"] = ProofNode("h1", "assumption", "P -> Q", None)
    g.nodes["h2"] = ProofNode("h2", "assumption", "P", None)      # will be unused
    g.nodes["h3"] = ProofNode("h3", "have", "P -> Q", "copy")
    g.nodes["_conclude"] = ProofNode("_conclude", "conclude", "P -> Q", None)
    g.edges += [("h1", "h3"), ("h3", "_conclude")]
    unused = find_unused_assumptions(g)
    assert "h2" in unused
    assert "h1" not in unused


def test_synthetic_used_suppose_not_flagged():
    """A suppose label cited in imp_intro is reachable and must NOT be flagged."""
    g = ProofGraph(name="test", conclusion="_conclude")
    g.nodes["h1"] = ProofNode("h1", "suppose", "P", None)
    g.nodes["h2"] = ProofNode("h2", "have", "P", "copy")
    g.nodes["h3"] = ProofNode("h3", "have", "P -> P", "imp_intro")
    g.nodes["_conclude"] = ProofNode("_conclude", "conclude", "P -> P", None)
    # imp_intro h1 h2 → edges h1→h3, h2→h3
    g.edges += [("h1", "h3"), ("h2", "h3"), ("h3", "_conclude")]
    unused = find_unused_assumptions(g)
    assert "h1" not in unused


def test_synthetic_isolated_have_step():
    """A have step with no path to conclusion is isolated."""
    g = ProofGraph(name="test", conclusion="_conclude")
    g.nodes["h1"] = ProofNode("h1", "assumption", "P", None)
    g.nodes["h2"] = ProofNode("h2", "have", "P", "copy")           # isolated
    g.nodes["h3"] = ProofNode("h3", "have", "P", "copy")
    g.nodes["_conclude"] = ProofNode("_conclude", "conclude", "P", None)
    g.edges += [("h1", "h3"), ("h3", "_conclude")]   # h2 is never used
    iso = find_isolated_steps(g)
    assert "h2" in iso
    assert "h3" not in iso


def test_no_unused_in_peirce():
    """In Peirce's law, every suppose/assume contributes to the conclusion."""
    g = _build(_PEIRCE)
    assert find_unused_assumptions(g) == set()


def test_no_isolated_in_peirce():
    g = _build(_PEIRCE)
    assert find_isolated_steps(g) == set()


# ---------------------------------------------------------------------------
# 6. CLI graph command
# ---------------------------------------------------------------------------

def test_cli_graph_summary(tmp_path, capsys):
    p = tmp_path / "t.stele"
    p.write_text(_SIMPLE)
    from stele.cli import cmd_graph
    rc = cmd_graph(str(p), "intuitionistic_prop", dot_mode=False)
    assert rc == 0
    out = capsys.readouterr().out
    assert "graph" in out
    assert "h1" in out
    assert "h3" in out
    assert "mp" in out
    assert "edges" in out


def test_cli_graph_dot(tmp_path, capsys):
    p = tmp_path / "t.stele"
    p.write_text(_SIMPLE)
    from stele.cli import cmd_graph
    rc = cmd_graph(str(p), "intuitionistic_prop", dot_mode=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "digraph" in out
    assert "h1" in out


def test_cli_graph_invalid_proof_returns_1(tmp_path, capsys):
    """Verification failure prevents graph generation."""
    bad = """
theorem bad:
  assume h1: P
  have h2: Q by copy h1
  conclude Q by h2
"""
    p = tmp_path / "bad.stele"
    p.write_text(bad)
    from stele.cli import cmd_graph
    rc = cmd_graph(str(p), "intuitionistic_prop", dot_mode=False)
    assert rc == 1
    out = capsys.readouterr().out
    assert "must pass verification" in out


def test_cli_graph_peirce(capsys):
    from stele.cli import cmd_graph
    rc = cmd_graph("examples/peirce.stele", "classical_prop", dot_mode=False)
    assert rc == 0
    out = capsys.readouterr().out
    assert "peirce" in out
    assert "diagnostics: OK" in out


def test_cli_graph_peirce_dot(capsys):
    from stele.cli import cmd_graph
    rc = cmd_graph("examples/peirce.stele", "classical_prop", dot_mode=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "digraph" in out
    assert "pbc" in out
