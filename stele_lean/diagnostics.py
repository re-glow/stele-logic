"""Lean 4 diagnostic types and stderr/stdout parser.

LeanDiagnostic is a separate type from stele.diagnostics.Diagnostic to
keep the Lean bridge fully isolated from the trusted core.  stele/ must
NOT import this module.

Lean 4 error format (line-level pattern):
  {file}:{line}:{col}: {severity}: {message}

Example:
  /tmp/t.lean:7:8: error: type mismatch
  /tmp/t.lean:3:12: warning: declaration uses 'sorry'
  /tmp/t.lean:2:0: info: ...
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Diagnostic data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LeanDiagnostic:
    """A single diagnostic produced by Lean 4 elaboration.

    Stable codes:
        LeanTypeError   — Lean reported an elaboration/type error
        LeanWarning     — Lean reported a warning (e.g. 'sorry' usage)
        LeanInfo        — Lean reported an informational message
    """
    code: str        # "LeanTypeError" | "LeanWarning" | "LeanInfo"
    message: str     # first-line message text from Lean
    file: str        # source file path as reported by Lean
    line: int        # 1-indexed line number
    col: int         # 0-indexed column number
    severity: str    # "error" | "warning" | "info"
    raw: str         # original diagnostic line from Lean output


@dataclass
class LeanCheckResult:
    """Result of running Lean on a file."""
    available: bool                        # False if lean not found on PATH
    returncode: int | None                 # process return code (None if not run)
    stdout: str                            # captured stdout
    stderr: str                            # captured stderr
    diagnostics: list[LeanDiagnostic] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(d.severity == "error" for d in self.diagnostics)

    @property
    def lean_type_errors(self) -> list[LeanDiagnostic]:
        return [d for d in self.diagnostics if d.code == "LeanTypeError"]

    @property
    def has_sorry_warning(self) -> bool:
        """True if the only diagnostics are 'sorry' warnings (expected for skeletons)."""
        return (
            not self.has_errors
            and any("sorry" in d.message for d in self.diagnostics)
        )

    def summary(self) -> str:
        if not self.available:
            return "Lean not available (not found on PATH)"
        if not self.diagnostics:
            return f"OK (returncode={self.returncode})"
        parts = []
        n_errors = sum(1 for d in self.diagnostics if d.severity == "error")
        n_warns = sum(1 for d in self.diagnostics if d.severity == "warning")
        if n_errors:
            parts.append(f"{n_errors} error(s)")
        if n_warns:
            parts.append(f"{n_warns} warning(s)")
        return ", ".join(parts)


# ---------------------------------------------------------------------------
# Lean output parser
# ---------------------------------------------------------------------------

# Matches: /path/to/file.lean:LINE:COL: SEVERITY: MESSAGE
_LEAN_LINE_RE = re.compile(
    r"^(.*?):(\d+):(\d+):\s*(error|warning|info):\s*(.+)$",
    re.MULTILINE,
)

_SEVERITY_TO_CODE = {
    "error": "LeanTypeError",
    "warning": "LeanWarning",
    "info": "LeanInfo",
}


def parse_lean_output(text: str) -> list[LeanDiagnostic]:
    """Parse Lean 4 stderr/stdout into a list of LeanDiagnostic objects.

    Only the first line of each diagnostic is captured as the message;
    multi-line context (the "term has type" lines) is not currently parsed.

    Args:
        text: raw output string from the Lean process (stderr or combined)

    Returns:
        List of LeanDiagnostic (may be empty if no diagnostics found).
    """
    diags: list[LeanDiagnostic] = []
    for m in _LEAN_LINE_RE.finditer(text):
        file_, line_str, col_str, severity, message = m.groups()
        code = _SEVERITY_TO_CODE.get(severity, "LeanInfo")
        diags.append(LeanDiagnostic(
            code=code,
            message=message.strip(),
            file=file_,
            line=int(line_str),
            col=int(col_str),
            severity=severity,
            raw=m.group(0),
        ))
    return diags
