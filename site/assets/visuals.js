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
      h1:       { cx: 60,  cy: 80,  r: 24, label: 'h1',  sub: 'P',    stroke: 'rgba(124,92,255,.55)',  lc: '#9D7BFF' },
      h2:       { cx: 60,  cy: 160, r: 24, label: 'h2',  sub: 'P→Q',  stroke: 'rgba(124,92,255,.55)',  lc: '#9D7BFF' },
      mp:       { cx: 225, cy: 120, r: 24, label: 'mp',  sub: 'Q',    stroke: 'rgba(157,123,255,.55)', lc: '#9D7BFF' },
      conclude: { cx: 375, cy: 120, r: 27, label: '∴',   sub: 'Q',    stroke: 'rgba(62,156,143,.6)',   lc: '#3E9C8F' }
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
  /* 4. ProofConstellation (Canvas)                                          */
  /* ══════════════════════════════════════════════════════════════════════ */

  /**
   * Renders an animated proof-space constellation on a Canvas element.
   * Nodes: Γ (context), h1 (P→Q), h2 (P), mp (Q), ⊢ (kernel), cert (proof)
   * Deterministic layout; respects prefers-reduced-motion (static when set).
   * Pointer parallax: gentle depth shift on mousemove, disabled when reduced.
   *
   * @param {HTMLCanvasElement} canvas
   * @param {object} [opts]
   */
  function renderProofConstellation(canvas, opts) {
    opts = opts || {};
    var reduced = prefersReducedMotion();

    var W = 460, H = 340;
    var dpr = (typeof window !== 'undefined' && window.devicePixelRatio) || 1;
    canvas.width  = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    canvas.style.width  = W + 'px';
    canvas.style.height = H + 'px';
    canvas.setAttribute('aria-hidden', 'true');

    var ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    /* Nodes: id, x, y, r, label, sub, rgb, depth, phase */
    var nodes = [
      { id:'gamma',  x: 78,  y:170, r:30, label:'Γ',    sub:'ctx',    rgb:[176,106,255], depth:0.32, phase:0.0 },
      { id:'h1',     x:168,  y: 80, r:22, label:'h1',   sub:'P→Q',    rgb:[155,195,230], depth:0.62, phase:1.3 },
      { id:'h2',     x:168,  y:260, r:22, label:'h2',   sub:'P',      rgb:[155,195,230], depth:0.62, phase:2.1 },
      { id:'mp',     x:278,  y:170, r:26, label:'mp',   sub:'Q',      rgb:[176,106,255], depth:0.90, phase:0.7 },
      { id:'kernel', x:380,  y:105, r:20, label:'⊢',    sub:'kernel', rgb:[200,220,245], depth:0.52, phase:1.8 },
      { id:'cert',   x:380,  y:235, r:20, label:'cert', sub:'proof',  rgb:[210,170, 85], depth:0.44, phase:2.6 }
    ];

    /* Edges: [srcId, dstId, dashed] */
    var edgeDefs = [
      ['gamma', 'h1',     false],
      ['gamma', 'h2',     false],
      ['h1',    'mp',     false],
      ['h2',    'mp',     false],
      ['mp',    'kernel', false],
      ['mp',    'cert',   true ]
    ];

    var nodeMap = {};
    nodes.forEach(function(n) { nodeMap[n.id] = n; });
    var edges = edgeDefs.map(function(d) {
      return { src: nodeMap[d[0]], dst: nodeMap[d[1]], dashed: d[2] };
    });

    /* Pointer parallax state */
    var mouseOffX = 0, mouseOffY = 0;
    if (!reduced) {
      var wrap = canvas.parentElement || canvas;
      wrap.addEventListener('mousemove', function(e) {
        var rect = canvas.getBoundingClientRect();
        mouseOffX = (e.clientX - rect.left  - W / 2) / W;
        mouseOffY = (e.clientY - rect.top   - H / 2) / H;
      });
      wrap.addEventListener('mouseleave', function() {
        mouseOffX = 0; mouseOffY = 0;
      });
    }

    var t = 0, rafId;

    function nodePos(n) {
      var floatY = reduced ? 0 : Math.sin(t * 0.55 + n.phase) * 3;
      var px = reduced ? 0 : mouseOffX * n.depth * 18;
      var py = reduced ? 0 : mouseOffY * n.depth * 14;
      return { x: n.x + px, y: n.y + floatY + py };
    }

    function drawFrame() {
      ctx.clearRect(0, 0, W, H);

      /* Edges */
      edges.forEach(function(e) {
        var sp = nodePos(e.src), dp = nodePos(e.dst);
        var vx = dp.x - sp.x, vy = dp.y - sp.y;
        var len = Math.sqrt(vx * vx + vy * vy);
        if (len < 1) return;
        var ux = vx / len, uy = vy / len;
        var x1 = sp.x + ux * e.src.r;
        var y1 = sp.y + uy * e.src.r;
        var x2 = dp.x - ux * (e.dst.r + 5);
        var y2 = dp.y - uy * (e.dst.r + 5);

        var alpha = Math.min(e.src.depth, e.dst.depth) * 0.38;
        var er = e.dashed ? [210,170,85] : [176,106,255];
        var ec = 'rgba(' + er[0] + ',' + er[1] + ',' + er[2] + ',' + alpha + ')';

        ctx.save();
        ctx.beginPath();
        if (e.dashed) ctx.setLineDash([4, 7]);
        ctx.strokeStyle = ec;
        ctx.lineWidth = 1.2;
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();

        /* Arrowhead */
        ctx.setLineDash([]);
        var ang = Math.atan2(uy, ux), as = 6;
        ctx.beginPath();
        ctx.moveTo(x2, y2);
        ctx.lineTo(x2 - as * Math.cos(ang - 0.42), y2 - as * Math.sin(ang - 0.42));
        ctx.lineTo(x2 - as * Math.cos(ang + 0.42), y2 - as * Math.sin(ang + 0.42));
        ctx.closePath();
        ctx.fillStyle = ec;
        ctx.fill();
        ctx.restore();
      });

      /* Nodes */
      nodes.forEach(function(n) {
        var p = nodePos(n);
        var r = n.rgb, a = n.depth;
        var col = 'rgba(' + r[0] + ',' + r[1] + ',' + r[2] + ',';

        /* Outer glow (animated) */
        if (!reduced) {
          var gs = n.r + 10 + Math.sin(t * 0.7 + n.phase) * 4;
          var grd = ctx.createRadialGradient(p.x, p.y, n.r * 0.5, p.x, p.y, gs);
          grd.addColorStop(0, col + (a * 0.14) + ')');
          grd.addColorStop(1, 'rgba(11,10,16,0)');
          ctx.beginPath();
          ctx.arc(p.x, p.y, gs, 0, Math.PI * 2);
          ctx.fillStyle = grd;
          ctx.fill();
        }

        /* Node fill */
        var fill = ctx.createRadialGradient(
          p.x - n.r * 0.22, p.y - n.r * 0.22, 0, p.x, p.y, n.r
        );
        fill.addColorStop(0, col + (a * 0.13) + ')');
        fill.addColorStop(1, 'rgba(11,10,16,' + (a * 0.35) + ')');
        ctx.beginPath();
        ctx.arc(p.x, p.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = fill;
        ctx.fill();

        /* Node stroke */
        ctx.beginPath();
        ctx.arc(p.x, p.y, n.r, 0, Math.PI * 2);
        ctx.strokeStyle = col + (a * 0.72) + ')';
        ctx.lineWidth = 1.3;
        ctx.stroke();

        /* Label */
        ctx.fillStyle = col + (a * 0.95) + ')';
        ctx.font = 'bold 11px ui-monospace,monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(n.label, p.x, p.y - 3);

        /* Sublabel */
        ctx.fillStyle = 'rgba(184,204,224,' + (a * 0.52) + ')';
        ctx.font = '8px ui-monospace,monospace';
        ctx.fillText(n.sub, p.x, p.y + 9);
      });

      if (!reduced) {
        t += 0.016;
        rafId = requestAnimationFrame(drawFrame);
      }
    }

    drawFrame();
    canvas._steleStop = function() { if (rafId) cancelAnimationFrame(rafId); };
  }

  /* ══════════════════════════════════════════════════════════════════════ */
  /* 5. ProofOrb — semantic galaxy / proof-space nebula (Canvas)            */
  /* ══════════════════════════════════════════════════════════════════════ */

  /**
   * Renders a dimensional galaxy/nebula visual for the landing hero.
   * 520 depth-sorted particles in a flattened spherical distribution form
   * a rotating "proof-space" cosmos. Logic symbols float as dim star-labels.
   * This is intentionally NOT a proof DAG — it is a semantic space visual.
   *
   * Palette: violet / deep plum / ice-blue; no neon.
   * Motion: very slow rotation (~80 s/rev). prefers-reduced-motion → static.
   * No external dependencies; fully deterministic seeded layout.
   *
   * @param {HTMLCanvasElement} canvas
   * @param {object} [opts]
   */
  function renderProofOrb(canvas, opts) {
    opts = opts || {};
    var reduced = prefersReducedMotion();

    var W = 680, H = 620;
    var cx = W / 2, cy = H / 2;
    var R = 252; /* galaxy cloud radius */

    var dpr = (typeof window !== 'undefined' && window.devicePixelRatio) || 1;
    canvas.width  = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    canvas.style.width  = '100%';
    canvas.style.maxWidth = W + 'px';
    canvas.style.height = 'auto';
    canvas.setAttribute('aria-hidden', 'true');

    var ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    /* Seeded deterministic pseudo-random (no Math.random) */
    function rand(seed) {
      var x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
      return x - Math.floor(x);
    }

    /* Orthographic projection with x-axis tilt */
    var tilt = 0.30;
    function project(phi, lam, r) {
      var x3 = r * Math.cos(phi) * Math.cos(lam);
      var y3 = r * Math.sin(phi);
      var z3 = r * Math.cos(phi) * Math.sin(lam);
      var y2 = y3 * Math.cos(tilt) - z3 * Math.sin(tilt);
      var z2 = y3 * Math.sin(tilt) + z3 * Math.cos(tilt);
      return { x: cx + x3, y: cy - y2, z: z2 };
    }

    /* Particle palette: amethyst / deep violet / light amethyst */
    var PAL = [
      [124,  92, 255], /* amethyst     — 58% */
      [ 59,  42, 107], /* deep violet  — 27% */
      [157, 123, 255]  /* light ameth. — 15% */
    ];

    /* 520 particles: galaxy-disc distribution (flattened sphere) */
    var particles = [];
    for (var i = 0; i < 520; i++) {
      /* Latitude biased toward equator (disc shape) */
      var flatness = 0.48 + rand(i * 5 + 1) * 0.52;
      var phi  = (rand(i * 5) * 2 - 1) * Math.PI * 0.5 * flatness;
      var lam  = rand(i * 5 + 2) * Math.PI * 2;
      /* Power-law radial distribution: dense core, sparse edges */
      var rr   = Math.pow(rand(i * 5 + 3), 0.62) * R;
      var sz   = 0.45 + rand(i + 1000) * 1.85;
      var ci   = rand(i + 2000) < 0.58 ? 0 : (rand(i + 2001) < 0.68 ? 1 : 2);
      var ph   = rand(i + 3000) * Math.PI * 2;
      var da   = rand(i + 4000) * 0.016;
      particles.push({ phi: phi, lam0: lam, r: rr, sz: sz, ci: ci, ph: ph, da: da });
    }

    /* 14 floating logic/proof symbol labels — no edges, no circles */
    var SYM = ['∀', '⊢', '∃', '¬', '→', '⊨', 'Γ', '⊥', '∴', '≡', '⊃', '∈', 'cert', 'kernel'];
    var symPts = [];
    for (var j = 0; j < 14; j++) {
      symPts.push({
        sym:  SYM[j],
        phi:  (rand(j + 600) * 2 - 1) * Math.PI * 0.44,
        lam0: rand(j + 700) * Math.PI * 2,
        r:    R * (0.35 + rand(j + 800) * 0.55),
        fs:   rand(j + 900) < 0.25 ? 10 : 8
      });
    }

    /* 3 very-low-opacity equatorial rings for structural depth */
    var RING_PHIS = [0, 0.30, -0.30];

    var theta = 0, t = 0, rafId;

    function drawFrame() {
      ctx.clearRect(0, 0, W, H);

      /* Core glow — the heart of the orb */
      var core = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 0.62);
      core.addColorStop(0,    'rgba(124,92,255,.12)');
      core.addColorStop(0.40, 'rgba(157,123,255,.05)');
      core.addColorStop(1,    'rgba(11,10,16,0)');
      ctx.fillStyle = core;
      ctx.fillRect(0, 0, W, H);

      /* Outer nebula haze */
      var haze = ctx.createRadialGradient(cx, cy, R * 0.52, cx, cy, R * 1.18);
      haze.addColorStop(0, 'rgba(59,42,107,.04)');
      haze.addColorStop(1, 'rgba(11,10,16,0)');
      ctx.fillStyle = haze;
      ctx.fillRect(0, 0, W, H);

      /* Equatorial rings: structural skeleton, very dim */
      RING_PHIS.forEach(function(phi) {
        var ringR = R * (1 - Math.abs(phi) * 0.28);
        ctx.beginPath();
        var moved = false;
        for (var k = 0; k <= 80; k++) {
          var p = project(phi, (k / 80) * Math.PI * 2 - Math.PI + theta, ringR);
          if (p.z > -0.04 * R) {
            if (!moved) { ctx.moveTo(p.x, p.y); moved = true; }
            else ctx.lineTo(p.x, p.y);
          } else { moved = false; }
        }
        ctx.strokeStyle = phi === 0 ? 'rgba(176,106,255,.10)' : 'rgba(176,106,255,.06)';
        ctx.lineWidth = phi === 0 ? 0.8 : 0.55;
        ctx.stroke();
      });

      /* Depth-sort and draw particles */
      var sorted = particles.map(function(p) {
        var dx = reduced ? 0 : Math.sin(t * 0.38 + p.ph) * p.da * R;
        var dy = reduced ? 0 : Math.cos(t * 0.31 + p.ph * 1.25) * p.da * R * 0.7;
        var pr = project(p.phi, p.lam0 + theta, p.r);
        return { x: pr.x + dx, y: pr.y + dy, z: pr.z, p: p };
      });
      sorted.sort(function(a, b) { return a.z - b.z; });

      sorted.forEach(function(item) {
        var p   = item.p;
        var d01 = (item.z + R) / (2 * R);
        var rF  = p.r / R;
        var alpha = Math.min(0.80, d01 * 0.58 * (1 - rF * 0.45) + 0.03);
        var sz    = p.sz * (0.5 + d01 * 0.7);
        if (sz < 0.18 || alpha < 0.025) return;
        var rgb = PAL[p.ci];
        ctx.beginPath();
        ctx.arc(item.x, item.y, sz, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ',' + alpha.toFixed(3) + ')';
        ctx.fill();
      });

      /* Floating logic symbol stars — dim, atmospheric, not structural */
      symPts.forEach(function(sp) {
        var pr = project(sp.phi, sp.lam0 + theta * 0.75, sp.r);
        if (pr.z < -0.28 * R) return;
        var d01 = (pr.z + R) / (2 * R);
        var a = d01 * 0.20 + 0.035;
        ctx.fillStyle = 'rgba(205,178,255,' + a.toFixed(3) + ')';
        ctx.font = sp.fs + 'px ui-monospace,monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(sp.sym, pr.x, pr.y);
      });

      if (!reduced) {
        theta += 0.0015; /* ~80 s per full revolution */
        t += 0.016;
        rafId = requestAnimationFrame(drawFrame);
      }
    }

    drawFrame();
    canvas._steleStop = function() { if (rafId) cancelAnimationFrame(rafId); };
  }

  /* ══════════════════════════════════════════════════════════════════════ */
  /* Auto-init on DOMContentLoaded                                           */
  /* ══════════════════════════════════════════════════════════════════════ */

  var RENDERERS = {
    'proof-graph':         renderProofGraph,
    'symbol-field':        renderLogicSymbolField,
    'kripke-motif':        renderKripkeMotif,
    'proof-constellation': renderProofConstellation,
    'proof-orb':           renderProofOrb
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
    renderProofGraph:          renderProofGraph,
    renderLogicSymbolField:    renderLogicSymbolField,
    renderKripkeMotif:         renderKripkeMotif,
    renderProofConstellation:  renderProofConstellation,
    renderProofOrb:            renderProofOrb
  };
}(typeof window !== 'undefined' ? window : {}));
