# Stele Whitepaper — LaTeX Source

This directory contains the LaTeX source for the Stele technical whitepaper.

**Primary readable version:** [`docs/whitepaper.md`](../docs/whitepaper.md) (Markdown)
**LaTeX source:** `paper/stele-whitepaper.tex`
**Bibliography:** `paper/references.bib`

---

## Build Instructions

### Requirements

- TeX Live, MiKTeX, or MacTeX with standard packages:
  `amsmath`, `amssymb`, `amsthm`, `microtype`, `hyperref`,
  `booktabs`, `listings`, `xcolor`, `float`, `enumitem`, `geometry`

### Build with latexmk (recommended)

```bash
cd paper/
latexmk -pdf stele-whitepaper.tex
```

### Build with pdflatex (run twice for bibliography)

```bash
cd paper/
pdflatex stele-whitepaper.tex
bibtex stele-whitepaper
pdflatex stele-whitepaper.tex
pdflatex stele-whitepaper.tex
```

### Clean up auxiliary files

```bash
cd paper/
latexmk -C
# or manually: rm *.aux *.bbl *.blg *.log *.out *.toc *.fls *.fdb_latexmk
```

---

## Notes

- The LaTeX source and the Markdown version (`docs/whitepaper.md`) should be kept in sync.
- Do not commit generated PDF files unless repo policy explicitly allows it.
- Normal `python -m pytest -q` does not require LaTeX to be installed; whitepaper tests
  perform static text checks only.
- TODO citation placeholders in `references.bib` indicate claims where exact bibliographic
  metadata is uncertain. Use conservative related-work prose until accurate metadata is
  confirmed.
