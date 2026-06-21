"""stele_ml — isolated ML baseline for Stele proof-verification tasks.

This package is intentionally isolated from the trusted stele/ core.
The symbolic checker (stele/kernel.py) remains the authoritative validator;
this package only provides a statistical approximation baseline.

Architecture constraints:
  - stele/ must NOT import stele_ml
  - ML dependencies (scikit-learn etc.) are optional and listed in requirements-ml.txt
  - The baseline works without any external dependencies (stdlib-only NB)
"""
__version__ = "0.1.0"
