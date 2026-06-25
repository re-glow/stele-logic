# Security Policy

## Scope

Stele is a local proof checker and browser-local web application. It has
no backend server, no authentication, no user accounts, and no persistent
data storage. All proof checking runs client-side via Pyodide/WASM or
locally via Python.

**The trusted kernel (`stele/kernel.py`) is purely computational** — it
performs syntactic rule matching and produces a verdict. It does not execute
user-supplied code, make network requests, or access the filesystem beyond
reading the proof file passed to it.

## What is and is not in scope

**In scope:**
- Logic errors in `stele/kernel.py` that cause the kernel to accept an
  invalid proof as valid (false positive)
- Logic errors that cause the kernel to reject a valid proof as invalid
  when the proof correctly applies the declared rule (false negative in
  the correctness direction)
- Security issues in `stele/web.py` (local HTTP server) that could allow
  privilege escalation or code execution on the local machine

**Out of scope:**
- The browser Studio running malicious JavaScript (it's a static site with
  no user-supplied script execution)
- Pyodide/WASM runtime vulnerabilities (report to the Pyodide project)
- Proof scripts that cause Python to raise exceptions (these are handled
  as errors, not security issues)
- Performance issues or denial-of-service on local inputs

## Reporting a vulnerability

If you believe you have found a security issue in scope, please report it
via a **private GitHub Security Advisory**:

1. Go to https://github.com/re-glow/stele-logic/security/advisories
2. Click "Report a vulnerability"
3. Describe the issue, steps to reproduce, and the expected vs actual behavior

Please do not open a public issue for security vulnerabilities until a fix
is available.

## Response timeline

This is an independent research project maintained by a single person.
I will acknowledge receipt within 7 days and aim to provide a fix or
assessment within 30 days for valid in-scope issues.

## Kernel correctness claims

Stele's correctness guarantee is structural, not formally verified:
- The kernel is small (≈160 lines) and readable in one sitting.
- Import isolation between kernel and semantics modules is enforced by tests.
- Metatheory claims (subject reduction, soundness) are supported by regression
  tests and proof sketches — not machine-checked proofs.

If you find a proof that the kernel incorrectly accepts, that is the most
important class of bug this project can have. Please report it.
