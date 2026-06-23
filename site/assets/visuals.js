/**
 * Stele Visual Motif Primitives
 * Vanilla JS/SVG — no dependencies, no external fetches.
 * Three exports: renderProofGraph, renderLogicSymbolField, renderKripkeMotif
 * All respect prefers-reduced-motion.
 * All are aria-hidden by default (decorative).
 *
 * Auto-init: elements with data-stele-visual="<type>" are initialised on
 * DOMContentLoaded.
 *
 * See: docs/design-system.md §6
 */
(function (global) {
  'use strict';

  /* ── Utility ────────────────────────────────────────────────────────── */

  function prefersReducedMotion() {
    return (
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  }

  /* Escape SVG text content */
  function escText(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  /* ══════════════════════════════════════════════════════════════════════ */
  /* 1. ProofGraphHero                                                       */
  /* ══════════════════════════════════════════════════════════════════════ */

  /**
   * Renders a deterministic SVG proof dependency graph into `container`.
   * Graph: h1 + h2 → mp (modus ponens) → ∴ (conclusion)
   *
   * Options:
   *   decorative {boolean} — if true, sets aria-hidden on container (default true)
   *   animated   {boolean} — if true and not reduced-motion, adds edge draw-on (default true)
   *
   * @param {Element} container
   * @param {object}  [opts]
   */
  function renderProofGraph(container, opts) {
    opts = opts || {};
    var decorative = opts.decorative !== false;
    var animated   = opts.animated   !== false && !prefersReducedMotion();

    var ariaAttr = decorative
      ? 'aria-hidden="true"'
      : 'role="img" aria-label="Proof dependency graph: hypotheses h1 (P) and h2 (P implies Q) combined by modus ponens to derive conclusion Q"';

    /* Node positions */
    var nodes = {
      h1:       { cx: 60,  cy: 80,  r: 24, label: 'h1',  sub: 'P',    stroke: 'rgba(0,232,255,.55)',  lc: '#00e8ff' },
      h2:       { cx: 60,  cy: 160, r: 24, label: 'h2',  sub: 'P→Q',  stroke: 'rgba(0,232,255,.55)',  lc: '#00e8ff' },
      mp:       { cx: 225, cy: 120, r: 24, label: 'mp',  sub: 'Q',    stroke: 'rgba(176,106,255,.55)', lc: '#b06aff' },
      conclude: { cx: 375, cy: 120, r: 27, label: '∴',   sub: 'Q',    stroke: 'rgba(0,255,159,.6)',   lc: '#00ff9f' }
    };

    /* Compute arrow start/end points (on circle circumferences) */
    function arrowEndpoints(src, dst) {
      var dx = dst.cx - src.cx, dy = dst.cy - src.cy;
      var len = Math.sqrt(dx * dx + dy * dy);
      var ux = dx / len, uy = dy / len;
      return {
        x1: Math.round(src.cx + ux * src.r),
        y1: Math.round(src.cy + uy * src.r),
        x2: Math.round(dst.cx - ux * dst.r),
        y2: Math.round(dst.cy - uy * dst.r)
      };
    }

    var edges = [
      arrowEndpoints(nodes.h1, nodes.mp),
      arrowEndpoints(nodes.h2, nodes.mp),
      arrowEndpoints(nodes.mp, nodes.conclude)
    ];

    function edgeLen(e) {
      var dx = e.x2 - e.x1, dy = e.y2 - e.y1;
      return Math.round(Math.sqrt(dx * dx + dy * dy)) + 5;
    }

    var edgeStyle = animated
      ? function (e, i) {
        var l = edgeLen(e);
        return 'class="stele-edge-draw" style="--dash-len:' + l + ';--edge-delay:' + (i * 0.25) + 's"';
      }
      : function () { return ''; };

    var nodesSvg = Object.values(nodes).map(function (n) {
      var pulseAttr = (n.label === '∴' && !prefersReducedMotion())
        ? ' class="stele-conclude-pulse"' : '';
      return [
        '<circle cx="' + n.cx + '" cy="' + n.cy + '" r="' + n.r + '"',
        '  fill="#0d1220" stroke="' + n.stroke + '" stroke-width="1.5"' + pulseAttr + '/>',
        '<text x="' + n.cx + '" y="' + (n.cy - 4) + '" text-anchor="middle"',
        '  fill="' + n.lc + '" font-family="monospace" font-size="11" font-weight="700">' + escText(n.label) + '</text>',
        '<text x="' + n.cx + '" y="' + (n.cy + 11) + '" text-anchor="middle"',
        '  fill="#b8cce0" font-family="monospace" font-size="9">' + escText(n.sub) + '</text>'
      ].join('\n');
    }).join('\n');

    var edgesSvg = edges.map(function (e, i) {
      return '<line x1="' + e.x1 + '" y1="' + e.y1 + '" x2="' + e.x2 + '" y2="' + e.y2 + '"' +
        '\n  stroke="rgba(0,232,255,.3)" stroke-width="1.5"' +
        '\n  marker-end="url(#stele-pg-arrow)" ' + edgeStyle(e, i) + '/>';
    }).join('\n');

    container.innerHTML = [
      '<svg viewBox="0 0 430 220" xmlns="http://www.w3.org/2000/svg"',
      '  ' + ariaAttr,
      '  style="width:100%;height:auto;max-height:220px;display:block;">',
      '  <defs>',
      '    <marker id="stele-pg-arrow" viewBox="0 0 10 10" refX="9" refY="5"',
      '      markerWidth="6" markerHeight="6" orient="auto">',
      '      <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(0,232,255,.5)"/>',
      '    </marker>',
      '  </defs>',
      edgesSvg,
      nodesSvg,
      '</svg>'
    ].join('\n');

    if (decorative) container.setAttribute('aria-hidden', 'true');
  }

  /* ══════════════════════════════════════════════════════════════════════ */
  /* 2. LogicSymbolField                                                     */
  /* ══════════════════════════════════════════════════════════════════════ */

  var SYMBOLS = ['⊢', '⊨', '∀', '∃', '∧', '∨', '¬', '→', '⊥', '∴', '≡', '∈'];

  /**
   * Creates a subtle decorative logic-symbol field inside `container`.
   * Renders a grid of evenly-spaced symbols at low opacity.
   *
   * Options:
   *   count {number} — number of symbols to place (default 20)
   *
   * @param {Element} container
   * @param {object}  [opts]
   */
  function renderLogicSymbolField(container, opts) {
    opts = opts || {};
    var count = opts.count || 20;

    container.setAttribute('aria-hidden', 'true');
    container.classList.add('logic-symbol-field');

    var frag = document.createDocumentFragment();
    for (var i = 0; i < count; i++) {
      var span = document.createElement('span');
      span.className = 'logic-symbol-field__symbol';
      span.textContent = SYMBOLS[i % SYMBOLS.length];
      /* Distribute evenly in a grid-ish pattern with slight jitter */
      var col = i % 5;
      var row = Math.floor(i / 5);
      span.style.cssText = [
        'left:' + (col * 20 + 5 + ((row % 2) * 8)) + '%',
        'top:' + (row * 24 + 8) + '%',
        '--sym-fs:' + (0.9 + (i % 3) * 0.15) + 'rem'
      ].join(';');
      frag.appendChild(span);
    }
    container.appendChild(frag);
  }

  /* ══════════════════════════════════════════════════════════════════════ */
  /* 3. KripkeWorldMotif                                                     */
  /* ══════════════════════════════════════════════════════════════════════ */

  /**
   * Renders a simple Kripke frame poset as SVG into `container`.
   * Graph: W0 (base world) → W1, W0 → W2 (accessibility relation)
   *
   * Options:
   *   decorative {boolean} — if true, sets aria-hidden (default false for theory page)
   *
   * @param {Element} container
   * @param {object}  [opts]
   */
  function renderKripkeMotif(container, opts) {
    opts = opts || {};
    var decorative = opts.decorative === true;

    var ariaAttr = decorative
      ? 'aria-hidden="true"'
      : 'role="img" aria-label="Kripke frame with three worlds: W0 accessible to W1 and W2"';

    container.innerHTML = [
      '<svg viewBox="0 0 240 180" xmlns="http://www.w3.org/2000/svg"',
      '  ' + ariaAttr,
      '  style="width:100%;height:auto;max-height:180px;display:block;">',
      '  <defs>',
      '    <marker id="stele-kripke-arrow" viewBox="0 0 10 10" refX="9" refY="5"',
      '      markerWidth="5" markerHeight="5" orient="auto">',
      '      <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(176,106,255,.45)"/>',
      '    </marker>',
      '  </defs>',
      /* Accessibility relation edges */
      '  <line x1="120" y1="130" x2="68" y2="68"',
      '    class="kripke-edge" marker-end="url(#stele-kripke-arrow)"/>',
      '  <line x1="120" y1="130" x2="172" y2="68"',
      '    class="kripke-edge" marker-end="url(#stele-kripke-arrow)"/>',
      /* W0 (base world) */
      '  <circle cx="120" cy="148" r="20" class="kripke-world"/>',
      '  <text x="120" y="144" text-anchor="middle" fill="#b06aff" font-family="monospace" font-size="10" font-weight="700">W0</text>',
      '  <text x="120" y="158" text-anchor="middle" fill="#7fa0be" font-family="monospace" font-size="8">base</text>',
      /* W1 */
      '  <circle cx="60" cy="50" r="20" class="kripke-world"/>',
      '  <text x="60" y="46" text-anchor="middle" fill="#b06aff" font-family="monospace" font-size="10" font-weight="700">W1</text>',
      '  <text x="60" y="60" text-anchor="middle" fill="#7fa0be" font-family="monospace" font-size="8">P true</text>',
      /* W2 */
      '  <circle cx="180" cy="50" r="20" class="kripke-world"/>',
      '  <text x="180" y="46" text-anchor="middle" fill="#b06aff" font-family="monospace" font-size="10" font-weight="700">W2</text>',
      '  <text x="180" y="60" text-anchor="middle" fill="#7fa0be" font-family="monospace" font-size="8">P false</text>',
      '</svg>'
    ].join('\n');

    if (decorative) container.setAttribute('aria-hidden', 'true');
  }

  /* ══════════════════════════════════════════════════════════════════════ */
  /* Auto-init on DOMContentLoaded                                           */
  /* ══════════════════════════════════════════════════════════════════════ */

  var RENDERERS = {
    'proof-graph':    renderProofGraph,
    'symbol-field':   renderLogicSymbolField,
    'kripke-motif':   renderKripkeMotif
  };

  function autoInit() {
    var els = document.querySelectorAll('[data-stele-visual]');
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      var type = el.getAttribute('data-stele-visual');
      var render = RENDERERS[type];
      if (render) {
        try {
          render(el, {
            decorative: el.getAttribute('data-decorative') !== 'false'
          });
        } catch (err) {
          el.textContent = '';
        }
      }
    }
  }

  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', autoInit);
    } else {
      autoInit();
    }
  }

  /* ── Exports ─────────────────────────────────────────────────────────── */
  global.SteleVisuals = {
    renderProofGraph:       renderProofGraph,
    renderLogicSymbolField: renderLogicSymbolField,
    renderKripkeMotif:      renderKripkeMotif
  };
}(typeof window !== 'undefined' ? window : {}));
