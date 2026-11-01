/* Spot Nuraq — animation entièrement pilotée par le temps.
 *
 * window.seek(t) dessine l'image à l'instant t (en secondes). Aucune animation CSS :
 * chaque image se calcule seule, ce qui permet un rendu image par image, dans n'importe
 * quel ordre. ?format=16x9 donne la version YouTube, sinon la version 9:16.
 *
 * Grille rythmique : 100 BPM (1 temps = 0,6 s). Les changements de scène tombent sur les temps.
 */
(() => {
  "use strict";

  const Q = new URLSearchParams(location.search);
  const LAND = Q.get("format") === "16x9";
  const W = LAND ? 1920 : 1080;
  const H = LAND ? 1080 : 1920;
  const DURATION = 26.4;

  // ------------------------------------------------------------------ outils
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, k) => a + (b - a) * k;
  const ramp = (t, a, b) => (b <= a ? (t >= a ? 1 : 0) : clamp((t - a) / (b - a)));
  const E = {
    outCubic: (x) => 1 - Math.pow(1 - x, 3),
    inCubic: (x) => x * x * x,
    inOutCubic: (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
    outQuint: (x) => 1 - Math.pow(1 - x, 5),
    inOutQuint: (x) => (x < 0.5 ? 16 * x ** 5 : 1 - Math.pow(-2 * x + 2, 5) / 2),
    outExpo: (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x)),
    inExpo: (x) => (x <= 0 ? 0 : Math.pow(2, 10 * x - 10)),
    outBack: (x) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2),
  };
  /** Ressort amorti : 0 → 1 avec un léger dépassement, x en secondes depuis le départ. */
  const spring = (x, freq = 1.9, damp = 7.5) => (x <= 0 ? 0 : 1 - Math.exp(-damp * x) * Math.cos(2 * Math.PI * freq * x));
  /** Enveloppe d'apparition / disparition. */
  const env = (t, a, b, fin = 0.35, fout = 0.3) =>
    Math.min(E.outCubic(ramp(t, a, a + fin)), 1 - E.inCubic(ramp(t, b - fout, b)));

  let seed = 11;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;

  const stage = document.getElementById("stage");
  stage.style.width = `${W}px`;
  stage.style.height = `${H}px`;

  function h(tag, cls, parent, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    (parent || stage).appendChild(e);
    return e;
  }
  const NS = "http://www.w3.org/2000/svg";
  function sv(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  const css = (e, o) => Object.assign(e.style, o);
  const icon = (name, size, color, sw = 2) =>
    `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="${color}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round">${window.FEATHER[name]}</svg>`;
  const vis = (e, on) => (e.style.display = on ? "" : "none");

  let uid = 0;
  /** Icônes de ressources de l'app (app/components/ResourceIcon.tsx). */
  function streakIcon(size, active) {
    const id = `st${uid++}`;
    const o = active ? "#F7F5FA" : "#9F99AA";
    const g = (k) => (active ? `url(#${id}${k})` : k.startsWith("i") ? "#686370" : "#9F99AA");
    return `<svg viewBox="0 0 255 255" width="${size}" height="${size}">
<path d="M53.8935 180.293C24.1289 140.484 32.3126 84.1396 72.1721 54.4434L137.23 5.97431C141.658 2.67473 147.93 3.58559 151.237 8.00876L201.107 74.7069C230.871 114.515 222.235 171.197 182.376 200.893C142.516 230.589 85.6224 222.729 55.8579 182.92L53.8935 180.293Z" fill="${o}"/>
<path d="M96.3935 214.353C49.5507 198.557 24.4234 147.793 40.27 100.967L64.0237 30.7765C65.7941 25.5451 71.4717 22.7348 76.705 24.4995L154.608 50.7689C200.035 66.0875 224.404 115.319 209.036 160.73C193.668 206.141 144.383 230.536 98.9555 215.217L96.3935 214.353Z" fill="${o}"/>
<path d="M101.836 206.964C63.8727 194.164 43.459 153.006 56.3012 115.056L76.2824 56.0107C78.0527 50.7793 83.7303 47.9689 88.9637 49.7335L148.324 69.7495C186.234 82.5323 206.569 123.615 193.745 161.51C180.922 199.406 139.745 219.747 101.836 206.964Z" fill="${o}"/>
<path d="M69.7631 180.567C46.3071 149.196 52.7563 104.793 84.1676 81.3912L133.082 44.9493C137.51 41.6497 143.782 42.5606 147.089 46.9837L183.55 95.7484C207.018 127.135 200.551 171.571 169.123 194.985C137.712 218.387 93.219 211.938 69.7631 180.567Z" fill="${o}"/>
<path d="M61.8503 176.232C35.4233 140.824 42.7039 90.6963 78.112 64.2693L136.111 20.9814C140.537 17.678 146.803 18.5881 150.106 23.0141L194.599 82.6268C221.026 118.035 213.745 168.162 178.337 194.589L176.436 196.008C141.028 222.435 90.9005 215.154 64.4735 179.746L61.8503 176.232Z" fill="${g("oa")}"/>
<path d="M101.06 208.193C59.2009 194.053 36.7307 148.656 50.8711 106.797L71.9247 44.4741C73.6922 39.2417 79.3668 36.433 84.5991 38.2005L153.301 61.4087C194.056 75.1764 215.934 119.376 202.167 160.132C188.399 200.888 144.199 222.766 103.443 208.998L101.06 208.193Z" fill="${g("ob")}"/>
<path d="M106.085 201.63C72.0742 190.141 53.8166 153.257 65.3053 119.246L82.907 67.1388C84.6745 61.9064 90.349 59.0976 95.5814 60.8651L147.689 78.4668C181.699 89.9554 199.957 126.84 188.468 160.85C176.98 194.861 140.095 213.118 106.085 201.63Z" fill="${g("ia")}"/>
<path d="M77.3951 177.953C56.3814 149.798 62.1707 109.939 90.3257 88.925L133.291 56.8578C137.717 53.5544 143.983 54.4645 147.286 58.8905L179.353 101.856C200.367 130.011 194.578 169.87 166.423 190.883C138.268 211.897 98.4088 206.108 77.3951 177.953Z" fill="${g("ib")}"/>
<path d="M111.287 162.886C103.606 153.056 105.348 138.861 115.178 131.181L129.063 120.331C131.247 118.624 134.402 119.011 136.109 121.196L146.909 135.017C154.599 144.858 152.844 159.078 143.003 166.768C133.173 174.449 118.968 172.715 111.287 162.886Z" fill="${active ? "#FFE1BF" : "#D9D4E2"}"/>
<defs>
<linearGradient id="${id}oa" x1="143.33" x2="114.374" y1="20.724" y2="211.799" gradientUnits="userSpaceOnUse"><stop stop-color="#FFE358"/><stop offset="1" stop-color="#FFDD00"/></linearGradient>
<linearGradient id="${id}ob" x1="77.679" x2="158.156" y1="39.9754" y2="208.725" gradientUnits="userSpaceOnUse"><stop stop-color="#FFE358"/><stop offset="1" stop-color="#FFDD00"/></linearGradient>
<linearGradient id="${id}ia" x1="88.1472" x2="156.368" y1="61.7857" y2="199.607" gradientUnits="userSpaceOnUse"><stop stop-color="#AC26FF"/><stop offset="1" stop-color="#FF2197"/></linearGradient>
<linearGradient id="${id}ib" x1="140.658" x2="119.026" y1="55.3297" y2="204.267" gradientUnits="userSpaceOnUse"><stop stop-color="#AC26FF"/><stop offset="1" stop-color="#FF2197"/></linearGradient>
</defs></svg>`;
  }
  function gemIcon(size) {
    const id = `gm${uid++}`;
    return `<svg viewBox="0 0 174 174" width="${size}" height="${size}">
<path d="M79 4.6188C83.9504 1.76068 90.0496 1.76068 95 4.6188L154.344 38.8812C159.295 41.7393 162.344 47.0214 162.344 52.7376V121.262C162.344 126.979 159.295 132.261 154.344 135.119L95 169.381C90.0496 172.239 83.9504 172.239 79 169.381L19.6558 135.119C14.7054 132.261 11.6558 126.979 11.6558 121.262V52.7376C11.6558 47.0214 14.7054 41.7393 19.6558 38.8812L79 4.6188Z" fill="#F7F5FA"/>
<path d="M78.805 13.887C83.8536 10.8763 90.1464 10.8763 95.1949 13.887L145.013 43.5955C149.853 46.482 152.818 51.702 152.818 57.3375V117.662C152.818 123.298 149.853 128.518 145.013 131.404L95.195 161.113C90.1464 164.124 83.8536 164.124 78.8051 161.113L28.9871 131.404C24.1469 128.518 21.1821 123.298 21.1821 117.662V57.3375C21.1821 51.702 24.1469 46.482 28.9871 43.5955L78.805 13.887Z" fill="url(#${id})"/>
<path d="M81.0723 27.2602L35.4482 52.3535C32.3276 54.0698 32.8372 58.7017 36.2563 59.6985L63.237 67.5642C64.1985 67.8445 65.2302 67.7539 66.1281 67.3103L84.7716 58.1008C86.1362 57.4267 87 56.0365 87 54.5145V30.7651C87 27.7227 83.7381 25.794 81.0723 27.2602Z" fill="#F7F5FA"/>
<defs><linearGradient id="${id}" x1="87" x2="87" y1="9" y2="166" gradientUnits="userSpaceOnUse"><stop stop-color="#CA8AFF"/><stop offset="1" stop-color="#8624AD"/></linearGradient></defs></svg>`;
  }
  function energyIcon(size) {
    const id = `en${uid++}`;
    return `<svg viewBox="0 0 117 227" width="${(size * 117) / 227}" height="${size}">
<path d="M3.09325 116.325L71.6231 4.42981C73.8542 0.786805 79.4763 2.70879 79.0103 6.95524L70.3516 85.8592C70.1431 87.76 71.309 89.5426 73.1341 90.1132L111.035 101.964C113.727 102.806 114.726 106.095 112.956 108.292L72.8463 158.059L22.6166 222.715C19.9785 226.111 14.5727 223.521 15.566 219.337L35.8853 133.751C36.3939 131.609 35.0758 129.459 32.9361 128.94L5.56172 122.302C2.92492 121.662 1.6762 118.639 3.09325 116.325Z" fill="url(#${id})" stroke="#F7F5FA" stroke-width="5"/>
<defs><linearGradient id="${id}" x1="59.4323" x2="53.1283" y1="3.07833" y2="229.377" gradientUnits="userSpaceOnUse"><stop stop-color="#FFF126"/><stop offset="1" stop-color="#FFA200"/></linearGradient></defs></svg>`;
  }

  // ------------------------------------------------------------------ mise en page
  const LAY = LAND
    ? {
        cap: { x: 170, y: 540, w: 700, main: 84, sub: 34, align: "left" },
        phone: { cx: 1350, cy: 548, zoom: 1.02 },
        vis: { cx: 1350, cy: 540 },
        card: { zoom: 1.55 },
        rail: { zoom: 1.12 },
        logo: { markH: 420, markCy: 360, wordW: 560, wordY: 668, tagW: 420, tagY: 772, fineY: 1000, fine: 20 },
        line: 1,
      }
    : {
        cap: { x: 60, y: 200, w: 960, main: 80, sub: 38, align: "center" },
        phone: { cx: 540, cy: 1222, zoom: 1.55 },
        vis: { cx: 540, cy: 1150 },
        card: { zoom: 2.15 },
        rail: { zoom: 1.6 },
        logo: { markH: 560, markCy: 730, wordW: 660, wordY: 1135, tagW: 490, tagY: 1252, fineY: 1440, fine: 24 },
        line: 1.25,
      };

  // ------------------------------------------------------------------ fond
  const bg = h("div", "layer", stage);
  bg.id = "bg";
  const blobA = h("div", "glow-blob", bg);
  const blobB = h("div", "glow-blob", bg);
  const particles = [];
  for (let i = 0; i < (LAND ? 46 : 40); i++) {
    const p = h("div", "particle", bg);
    const size = 1.5 + rnd() * 2.6;
    particles.push({ e: p, x: rnd() * W, y: rnd() * H, size, speed: 8 + rnd() * 22, phase: rnd() * 6.28, base: 0.12 + rnd() * 0.3 });
    css(p, { width: `${size}px`, height: `${size}px` });
  }
  function updateBackground(t) {
    const sA = LAND ? 1300 : 1500;
    const ax = lerp(W * 0.32, W * 0.7, 0.5 + 0.5 * Math.sin(t * 0.21));
    const ay = lerp(H * 0.3, H * 0.62, 0.5 + 0.5 * Math.sin(t * 0.17 + 1.3));
    css(blobA, { width: `${sA}px`, height: `${sA}px`, left: `${ax - sA / 2}px`, top: `${ay - sA / 2}px`, opacity: 0.2 });
    const sB = LAND ? 900 : 1000;
    const bx = lerp(W * 0.75, W * 0.25, 0.5 + 0.5 * Math.sin(t * 0.13 + 2.0));
    const by = lerp(H * 0.75, H * 0.4, 0.5 + 0.5 * Math.sin(t * 0.19 + 0.4));
    css(blobB, { width: `${sB}px`, height: `${sB}px`, left: `${bx - sB / 2}px`, top: `${by - sB / 2}px`, opacity: 0.12 });
    for (const p of particles) {
      const y = (((p.y - p.speed * t) % H) + H) % H;
      const a = p.base * (0.6 + 0.4 * Math.sin(t * 1.3 + p.phase));
      css(p.e, { transform: `translate(${p.x}px, ${y}px)`, opacity: a });
    }
  }

  // Calque du fil lumineux (coordonnées de la scène)
  const lineSvg = sv("svg", { width: W, height: H, class: "layer" }, null);
  stage.appendChild(lineSvg);
  const defs = sv("defs", {}, lineSvg);
  function addDefs(target) {
    target.innerHTML = `
      <filter id="blur10" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="10"/></filter>
      <filter id="blur5" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5"/></filter>
      <radialGradient id="headGrad"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0.95"/><stop offset="0.25" stop-color="#DDD9FF" stop-opacity="0.75"/><stop offset="0.6" stop-color="#8179FB" stop-opacity="0.25"/><stop offset="1" stop-color="#6157F8" stop-opacity="0"/></radialGradient>`;
  }
  addDefs(defs);

  /** Fil lumineux : un tracé révélé entre deux fractions, avec une tête brillante. */
  class Light {
    constructor(parent, scale = LAY.line) {
      this.g = sv("g", {}, parent);
      this.pg = sv("path", { fill: "none", stroke: "#8179FB", "stroke-width": 13 * scale, "stroke-linecap": "round", filter: "url(#blur10)", opacity: 0.85 }, this.g);
      this.pc = sv("path", { fill: "none", stroke: "#EFECFD", "stroke-width": 3.2 * scale, "stroke-linecap": "round" }, this.g);
      this.halo = sv("circle", { r: 30 * scale, fill: "url(#headGrad)" }, this.g);
      this.dot = sv("circle", { r: 4.6 * scale, fill: "#FFFFFF" }, this.g);
      this.d = null;
    }
    path(d) {
      if (d !== this.d) {
        this.d = d;
        this.pg.setAttribute("d", d);
        this.pc.setAttribute("d", d);
        this.len = this.pc.getTotalLength();
      }
      return this;
    }
    point(f) {
      return this.pc.getPointAtLength(clamp(f) * this.len);
    }
    draw(a, b, opacity = 1, head = 1) {
      if (opacity <= 0.001 || b - a <= 0.0005) {
        this.g.style.display = "none";
        return;
      }
      this.g.style.display = "";
      const L = this.len;
      for (const p of [this.pg, this.pc]) {
        p.style.strokeDasharray = `${Math.max(0.01, (b - a) * L)} ${L * 2 + 10}`;
        p.style.strokeDashoffset = `${-a * L}`;
      }
      const pt = this.point(b);
      for (const c of [this.halo, this.dot]) {
        c.setAttribute("cx", pt.x);
        c.setAttribute("cy", pt.y);
        c.style.opacity = head;
      }
      this.g.style.opacity = opacity;
    }
  }

  // ------------------------------------------------------------------ légendes
  const CAPTIONS = [
    { a: 2.7, b: 4.62, main: "Apprends l’islam", sub: "de façon claire et progressive" },
    { a: 5.05, b: 9.4, main: "Des exercices courts", sub: "et une explication à chaque réponse", subAt: 7.15 },
    { a: 9.75, b: 12.4, main: "Le Coran", sub: "lis et reprends ta lecture" },
    { a: 12.85, b: 14.8, main: "Garde le rythme", sub: "un jour après l’autre" },
    { a: 15.2, b: 17.2, main: "Une progression claire", sub: "chaque niveau débloque le suivant" },
    { a: 17.45, b: 19.6, main: "12 parcours", sub: "des Piliers au Ramadan" },
  ];
  const capLayer = h("div", "layer", stage);
  for (const c of CAPTIONS) {
    const box = h("div", "caption", capLayer);
    css(box, { left: `${LAY.cap.x}px`, width: `${LAY.cap.w}px`, textAlign: LAY.cap.align });
    if (LAND) css(box, { top: `${LAY.cap.y}px` });
    else css(box, { top: `${LAY.cap.y}px` });
    c.mainEl = h("div", "main", box, c.main);
    c.subEl = h("div", "sub", box, c.sub);
    css(c.mainEl, { fontSize: `${LAY.cap.main}px`, whiteSpace: "normal", textWrap: "balance" });
    css(c.subEl, { fontSize: `${LAY.cap.sub}px` });
    c.box = box;
  }
  function updateCaptions(t) {
    for (const c of CAPTIONS) {
      const on = t > c.a - 0.05 && t < c.b + 0.05;
      vis(c.box, on);
      if (!on) continue;
      if (LAND) c.box.style.transform = `translateY(-50%)`;
      const out = E.inCubic(ramp(t, c.b - 0.3, c.b));
      const kin = E.outQuint(ramp(t, c.a, c.a + 0.55));
      css(c.mainEl, { opacity: kin * (1 - out), transform: `translateY(${(1 - kin) * 34 - out * 18}px)` });
      const sa = c.subAt ?? c.a + 0.14;
      const ks = E.outQuint(ramp(t, sa, sa + 0.55));
      css(c.subEl, { opacity: ks * (1 - out), transform: `translateY(${(1 - ks) * 26 - out * 18}px)` });
    }
  }

  // ------------------------------------------------------------------ logo (scènes 1 et 9)
  const LOGO = window.NURAQ_LOGO;
  const vb = (s) => s.split(" ").map(Number);
  function buildLogo() {
    const root = h("div", "scene", stage);
    const L = LAY.logo;
    const [, , mw, mh] = vb(LOGO.mark.viewBox);
    const markW = (L.markH * mw) / mh;
    const glow = h("div", "glow-blob", root);
    const gs = L.markH * 1.9;
    css(glow, { width: `${gs}px`, height: `${gs}px`, left: `${W / 2 - gs / 2}px`, top: `${L.markCy - gs / 2}px` });
    const svg = sv("svg", { viewBox: LOGO.mark.viewBox, width: markW, height: L.markH, class: "abs" }, root);
    css(svg, { left: `${W / 2 - markW / 2}px`, top: `${L.markCy - L.markH / 2}px` });
    const ldefs = sv("defs", {}, svg);
    ldefs.innerHTML = `<filter id="lgBlur${uid}" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="22"/></filter>`;
    const blurId = `lgBlur${uid++}`;
    const fill = sv("path", { d: LOGO.mark.d, fill: "#F7F5FA", "fill-rule": "evenodd" }, svg);
    const subs = LOGO.mark.d.split(/(?=M)/).map((s) => s.trim()).filter(Boolean);
    const outlines = [];
    const sw = (mw / markW) * 2.6 * LAY.line;
    for (const d of subs) {
      const gl = sv("path", { d, fill: "none", stroke: "#8179FB", "stroke-width": sw * 5, filter: `url(#${blurId})`, pathLength: 1, "stroke-linecap": "round" }, svg);
      const co = sv("path", { d, fill: "none", stroke: "#EFECFD", "stroke-width": sw, pathLength: 1, "stroke-linecap": "round" }, svg);
      outlines.push(gl, co);
    }
    // tête lumineuse sur le contour extérieur (premier sous-tracé)
    const probe = sv("path", { d: subs[0], fill: "none", stroke: "none" }, svg);
    const probeLen = probe.getTotalLength();
    const headHalo = sv("circle", { r: (mw / markW) * 34 * LAY.line, fill: "url(#headGrad)" }, svg);
    const headDot = sv("circle", { r: (mw / markW) * 5 * LAY.line, fill: "#FFFFFF" }, svg);
    // headGrad doit exister dans ce SVG aussi
    const hdefs = sv("defs", {}, svg);
    addDefs(hdefs);

    const [, , ww, wh] = vb(LOGO.wordmark.viewBox);
    const wordH = (L.wordW * wh) / ww;
    const word = sv("svg", { viewBox: LOGO.wordmark.viewBox, width: L.wordW, height: wordH, class: "abs" }, root);
    css(word, { left: `${W / 2 - L.wordW / 2}px`, top: `${L.wordY - wordH / 2}px` });
    const wmaskId = `wmask${uid++}`;
    const wdefs = sv("defs", {}, word);
    const wgrad = sv("linearGradient", { id: `${wmaskId}g`, gradientUnits: "userSpaceOnUse", x1: 0, x2: ww * 0.18, y1: 0, y2: 0 }, wdefs);
    sv("stop", { offset: 0, "stop-color": "#fff" }, wgrad);
    sv("stop", { offset: 1, "stop-color": "#000" }, wgrad);
    const wmask = sv("mask", { id: wmaskId, maskUnits: "userSpaceOnUse", x: -ww, y: -100, width: ww * 3, height: wh + 200 }, wdefs);
    const wrect = sv("rect", { x: -ww * 1.2, y: -100, width: ww * 1.2, height: wh + 200, fill: "#fff" }, wmask);
    const wedge = sv("rect", { x: 0, y: -100, width: ww * 0.18, height: wh + 200, fill: `url(#${wmaskId}g)` }, wmask);
    sv("path", { d: LOGO.wordmark.d, fill: "#F7F5FA", mask: `url(#${wmaskId})` }, word);
    const [, , tw, th] = vb(LOGO.tagline.viewBox);
    const tagH = (L.tagW * th) / tw;
    const tag = sv("svg", { viewBox: LOGO.tagline.viewBox, width: L.tagW, height: tagH, class: "abs" }, root);
    css(tag, { left: `${W / 2 - L.tagW / 2}px`, top: `${L.tagY - tagH / 2}px` });
    sv("path", { d: LOGO.tagline.d, fill: "#BBB7FD" }, tag);
    // balayage lumineux sous le nom
    const sweep = new Light(lineSvg);
    const sweepY = L.wordY + wordH / 2 + (LAND ? 26 : 32);
    sweep.path(`M ${W / 2 - L.wordW / 2 - 20} ${sweepY} L ${W / 2 + L.wordW / 2 + 20} ${sweepY}`);

    return {
      root,
      /** Révèle le logo : dessin du contour (d0→d1), remplissage, nom, slogan. */
      update(t, k) {
        const on = k.show;
        vis(root, on);
        if (!on) {
          sweep.draw(0, 0, 0);
          return;
        }
        const draw = E.inOutCubic(ramp(t, k.d0, k.d1));
        const fillK = E.outCubic(ramp(t, k.f0, k.f0 + 0.45));
        const outK = 1 - ramp(t, k.f0 + 0.15, k.f0 + 0.6);
        outlines.forEach((p) => {
          p.style.strokeDasharray = "1 1";
          p.style.strokeDashoffset = `${1 - draw}`;
          p.style.opacity = draw > 0 ? outK : 0;
        });
        fill.style.opacity = fillK;
        const pt = probe.getPointAtLength(draw * probeLen);
        const ho = draw > 0 && draw < 1 ? 1 : draw >= 1 ? outK : 0;
        for (const c of [headHalo, headDot]) {
          c.setAttribute("cx", pt.x);
          c.setAttribute("cy", pt.y);
          c.style.opacity = ho;
        }
        glow.style.opacity = 0.22 * ramp(t, k.d0, k.f0 + 0.4) + 0.06 * Math.sin(t * 2.2) * ramp(t, k.f0, k.f0 + 1);
        const wk = E.inOutCubic(ramp(t, k.w0, k.w0 + 0.5));
        const edgeX = lerp(-ww * 0.2, ww * 1.05, wk);
        wrect.setAttribute("x", edgeX - ww * 1.2);
        wedge.setAttribute("transform", `translate(${edgeX} 0)`);
        word.style.opacity = wk > 0 ? 1 : 0;
        sweep.draw(Math.max(0, wk - 0.35), wk, (wk > 0 ? 1 : 0) * (1 - ramp(t, k.w0 + 0.45, k.w0 + 0.75)));
        const tk = E.outCubic(ramp(t, k.t0, k.t0 + 0.5));
        css(tag, { opacity: tk, transform: `translateY(${(1 - tk) * 14}px)` });
        const sc = k.scale ?? 1;
        css(root, { opacity: k.alpha ?? 1, transform: `translateY(${k.dy ?? 0}px) scale(${sc})`, transformOrigin: `${W / 2}px ${L.markCy}px` });
      },
    };
  }

  // ------------------------------------------------------------------ scène 2 : le monde des parcours
  const S2 = (() => {
    const root = h("div", "scene", stage);
    const world = h("div", "abs", root);
    css(world, { left: 0, top: 0, width: `${W}px`, height: `${H}px` });
    const isl = LAND
      ? [
          { key: "quran", name: "Découvrir le Coran", ico: "book-open", x: 1580, y: 290, w: 300, depth: 0.75 },
          { key: "sunnah", name: "Apprendre la prière", ico: "clock", x: 1130, y: 560, w: 340, depth: 1.0 },
          { key: "pillars", name: "Les Piliers", ico: "compass", x: 1590, y: 800, w: 400, depth: 1.25 },
        ]
      : [
          { key: "quran", name: "Découvrir le Coran", ico: "book-open", x: 770, y: 760, w: 330, depth: 0.75 },
          { key: "sunnah", name: "Apprendre la prière", ico: "clock", x: 300, y: 1160, w: 390, depth: 1.0 },
          { key: "pillars", name: "Les Piliers", ico: "compass", x: 640, y: 1620, w: 520, depth: 1.25 },
        ];
    const svg = sv("svg", { width: W, height: H, class: "layer" }, null);
    world.appendChild(svg);
    addDefs(sv("defs", {}, svg));
    for (const i of isl) {
      i.wrap = h("div", "isle", world);
      i.img = h("img", "", i.wrap);
      i.img.src = `assets/img/island-${i.key}.webp`;
      css(i.wrap, { width: `${i.w}px`, left: `${i.x - i.w / 2}px`, top: `${i.y - i.w / 2}px` });
      i.chip = h("div", "chip", world, `<div class="ci">${icon(i.ico, 22, "#BBB7FD")}</div><div class="ct">${i.name}</div>`);
      const cs = LAND ? 1 : 1.25;
      css(i.chip, { left: `${i.x}px`, top: `${i.y + i.w * 0.42}px`, transformOrigin: "0 0" });
      i.cs = cs;
    }
    // chemin pointillé (comme la carte de l'app) + fil lumineux
    const pts = isl.map((i) => ({ x: i.x, y: i.y + i.w * 0.42 + 26 }));
    const start = LAND ? { x: 1360, y: -260 } : { x: 1010, y: -240 };
    const d = `M ${start.x} ${start.y}
      C ${start.x} ${start.y + (LAND ? 260 : 640)}, ${pts[0].x + (LAND ? 120 : 250)} ${pts[0].y - (LAND ? 420 : 300)}, ${pts[0].x - 40} ${pts[0].y - 30}
      C ${pts[0].x - 160} ${pts[0].y + 120}, ${pts[1].x + 220} ${pts[1].y - 330}, ${pts[1].x + 10} ${pts[1].y - 20}
      C ${pts[1].x - 120} ${pts[1].y + 140}, ${pts[2].x - 300} ${pts[2].y - 300}, ${pts[2].x - 20} ${pts[2].y}`;
    const dots = sv("path", { d, fill: "none", stroke: "#BBB7FD", "stroke-width": 6 * LAY.line, "stroke-linecap": "round", "stroke-dasharray": `0 ${22 * LAY.line}`, opacity: 0.35 }, svg);
    const light = new Light(svg).path(d);
    const fracs = [0.36, 0.68, 0.995];
    return {
      update(t) {
        const on = t > 2.2 && t < 4.95;
        vis(root, on);
        if (!on) return;
        const head = E.inOutCubic(ramp(t, 2.38, 4.35));
        const cam = E.inOutCubic(ramp(t, 2.3, 4.5));
        const zoom = E.inExpo(ramp(t, 4.45, 4.85));
        const fadeIn = E.outCubic(ramp(t, 2.25, 2.7));
        const camY = lerp(LAND ? 90 : 260, LAND ? -70 : -170, cam);
        for (const [n, i] of isl.entries()) {
          const pop = spring(t - (2.35 + n * 0.16));
          const bob = Math.sin(t * 1.6 + n * 1.7) * 7;
          const py = camY * (i.depth - 1) * 0.6;
          css(i.wrap, { opacity: clamp(pop * 1.4), transform: `translateY(${py + bob}px) scale(${0.82 + 0.18 * pop})` });
          const lit = ramp(head, fracs[n] - 0.04, fracs[n]);
          const pulse = lit * (1 - ramp(t, 2.38 + 1.97 * fracs[n] + 0.25, 2.38 + 1.97 * fracs[n] + 0.9));
          css(i.chip, {
            opacity: clamp(pop * 1.4),
            transform: `translateY(${py}px) scale(${i.cs * (1 + 0.04 * pulse)}) translateX(-50%)`,
            borderColor: lit > 0 ? `rgba(129, 121, 251, ${0.35 + 0.4 * pulse})` : "rgba(247, 245, 250, 0.18)",
          });
        }
        css(world, { transform: `translateY(${camY}px)` });
        dots.style.opacity = 0.35 * fadeIn;
        light.draw(0, head, 1 - ramp(t, 4.4, 4.75));
        const pil = isl[2];
        css(root, {
          opacity: fadeIn * (1 - ramp(t, 4.55, 4.85)),
          transform: `scale(${1 + 0.7 * zoom})`,
          transformOrigin: `${pil.x}px ${pil.y + camY}px`,
          filter: zoom > 0.02 ? `blur(${zoom * 14}px)` : "none",
        });
      },
    };
  })();

  // ------------------------------------------------------------------ téléphone (scènes 3 et 4)
  const PH = (() => {
    const z = LAY.phone.zoom;
    const holder = h("div", "holder", stage);
    css(holder, { width: `${410 * z}px`, height: `${864 * z}px`, left: `${LAY.phone.cx - 205 * z}px`, top: `${LAY.phone.cy - 432 * z}px` });
    const phone = h("div", "phone", holder);
    phone.style.zoom = z;
    const screen = h("div", "screen", phone);
    h("div", "dyn-island", screen);
    h("div", "statusbar", screen, `<span>09:41</span><span class="icons">
      <svg width="18" height="12" viewBox="0 0 18 12"><rect x="0" y="8" width="3" height="4" rx="1" fill="#F7F5FA"/><rect x="5" y="5.5" width="3" height="6.5" rx="1" fill="#F7F5FA"/><rect x="10" y="3" width="3" height="9" rx="1" fill="#F7F5FA"/><rect x="15" y="0" width="3" height="12" rx="1" fill="#F7F5FA"/></svg>
      <svg width="27" height="13" viewBox="0 0 27 13"><rect x="0.5" y="0.5" width="22" height="12" rx="3.5" stroke="#F7F5FA" stroke-opacity="0.5" fill="none"/><rect x="2.5" y="2.5" width="18" height="8" rx="2" fill="#F7F5FA"/><rect x="24" y="4" width="2" height="5" rx="1" fill="#F7F5FA" fill-opacity="0.5"/></svg></span>`);

    // --- page exercice (contenu réel : app/data/pillarsCourse.ts, exercice « shahada-count »)
    const ex = h("div", "page", screen);
    h("div", "ex-head", ex, `<div class="icon-btn">${icon("x", 22, "#D9D4E2")}</div>
      <div class="track"><div class="fill"></div></div>
      <div class="res">${gemIcon(20)}<span>56</span></div><div class="res">${energyIcon(21)}<span>15</span></div>`);
    const exFill = ex.querySelector(".fill");
    h("div", "ex-title", ex, "Combien de piliers l’Islam compte-t-il ?");
    const choicesBox = h("div", "choices", ex);
    const choices = ["3", "4", "5", "6"].map((v) => {
      const c = h("div", "choice", choicesBox, `<div class="mark"></div><span>${v}</span><div class="end"></div>`);
      return c;
    });
    const correct = choices[2];
    correct.querySelector(".end").innerHTML = icon("check", 22, "#55C98A", 2.6);
    const correctEnd = correct.querySelector(".end");
    const correctMark = correct.querySelector(".mark");
    const exBottom = h("div", "ex-bottom", ex);
    const tray = h("div", "tray", exBottom, `<div class="row">${icon("check-circle", 26, "#55C98A")}<div class="title">Bien joué !</div></div>
      <div class="text">Les cinq piliers sont la Shahada, la Salat, la Zakat, le Sawm et le Hajj.</div>`);
    const action = h("div", "action", exBottom, "Valider");

    // --- page bibliothèque du Coran
    const lib = h("div", "page", screen);
    h("div", "lib-kicker", lib, "BIBLIOTHÈQUE");
    h("div", "lib-title", lib, "Le Coran");
    h("div", "lib-sub", lib, "Lis, mémorise et reprends facilement tes sourates.");
    h("div", "lib-bookmark", lib, icon("bookmark", 20, "#BBB7FD"));
    h("div", "search", lib, `${icon("search", 20, "#9F99AA")}<span>Rechercher une sourate…</span>`);
    const resume = h("div", "resume", lib, `<div class="k">Reprendre la lecture</div><div class="t">Al-Fatihah</div>
      <div class="m">Verset 1 • 7 versets</div><div class="m">Sourate mecquoise • 7 versets</div><div class="btn">Continuer</div>`);
    h("div", "lib-count", lib, "114 sourates");
    const s1 = h("div", "surah", lib, `<div class="num">1</div><div><div class="ar">الفاتحة</div><div class="nm">Al-Fatihah</div><div class="mt">7 versets • Mecquoise</div></div>`);
    css(s1, { top: "604px" });
    const s2 = h("div", "surah", lib, `<div class="num">2</div><div><div class="ar">البقرة</div><div class="nm">Al-Baqarah</div><div class="mt">286 versets • Médinoise</div></div>`);
    css(s2, { top: "726px" });
    h("div", "tabbar", lib, [["home", "Home"], ["map", "Parcours"], ["book-open", "Coran"], ["user", "Profil"]]
      .map(([i, l]) => `<div class="tab${l === "Coran" ? " on" : ""}">${icon(i, 22, l === "Coran" ? "#BBB7FD" : "#9F99AA")}<span>${l}</span></div>`).join(""));
    const resumeSvg = sv("svg", { width: 350, height: 260, class: "abs" }, null);
    lib.appendChild(resumeSvg);
    css(resumeSvg, { left: "20px", top: "300px" });
    addDefs(sv("defs", {}, resumeSvg));

    // --- page lecteur (texte arabe Tanzil, traduction Rachid Maach, tels que fournis par l'app)
    const rd = h("div", "page", screen);
    h("div", "reader-back", rd, icon("chevron-left", 24, "#F7F5FA"));
    const scroller = h("div", "abs", rd);
    css(scroller, { left: 0, top: 0, width: "390px", height: "1200px" });
    h("div", "hero", scroller, `<div class="ar">الفاتحة</div><div class="t">Al-Fatihah</div><div class="f">L’ouverture</div>
      <div class="m">7 versets • Mecquoise</div>
      <div class="c">Traduction française : Rachid Maach · QuranEnc 1.0.3</div>
      <div class="c2">Texte arabe : Tanzil Project via Quran JSON ${icon("external-link", 12, "#8179FB")}</div>`);
    const v1 = h("div", "verse", scroller, `<div class="badge">1</div>
      <div class="ar">بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ</div>
      <div class="tr">Au nom d’Allah, le Tout Miséricordieux, le Très Miséricordieux.</div>`);
    css(v1, { top: "438px" });
    const v2 = h("div", "verse", scroller, `<div class="badge" style="background:rgba(97,87,248,0.2)">2</div>
      <div class="ar">ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ</div>
      <div class="tr">Louange à Allah, Seigneur de la Création,</div>`);
    css(v2, { top: "650px" });

    // contour lumineux du téléphone (dans le repère du téléphone, donc fidèle à la perspective)
    const rimSvg = sv("svg", { width: 410, height: 864, class: "rim" }, null);
    phone.appendChild(rimSvg);
    addDefs(sv("defs", {}, rimSvg));
    const rimD = `M 205 1.5 L 344 1.5 A 64.5 64.5 0 0 1 408.5 66 L 408.5 798 A 64.5 64.5 0 0 1 344 862.5 L 66 862.5 A 64.5 64.5 0 0 1 1.5 798 L 1.5 66 A 64.5 64.5 0 0 1 66 1.5 Z`;
    const rim = new Light(rimSvg, 1 / z).path(rimD);
    const rimStatic = sv("path", { d: rimD, fill: "none", stroke: "#8179FB", "stroke-width": 1.6, opacity: 0 }, rimSvg);
    const resumeLight = new Light(resumeSvg, 1 / z).path(
      `M 175 0.5 L 326 0.5 A 23.5 23.5 0 0 1 349.5 24 L 349.5 216 A 23.5 23.5 0 0 1 326 239.5 L 24 239.5 A 23.5 23.5 0 0 1 0.5 216 L 0.5 24 A 23.5 23.5 0 0 1 24 0.5 Z`,
    );

    const touch = h("div", "touch", screen);

    function tapAt(t, t0, x, y) {
      const k = ramp(t, t0 - 0.12, t0 + 0.35);
      if (k <= 0 || k >= 1) return 0;
      css(touch, { left: `${x}px`, top: `${y}px`, opacity: Math.sin(Math.PI * k) * 0.9, transform: `scale(${0.55 + 0.6 * k})` });
      return 1;
    }

    return {
      holder,
      update(t) {
        const on = t > 4.55 && t < 12.7;
        vis(holder, on);
        if (!on) return;
        // entrée / sortie du téléphone
        const enter = E.outQuint(ramp(t, 4.62, 5.4));
        const exit = E.inCubic(ramp(t, 12.22, 12.62));
        const drift = Math.sin(t * 0.5) * 1.5;
        let rx, ry, tx, ty;
        if (LAND) {
          rx = lerp(26, 5, enter) + drift * 0.4;
          ry = lerp(-30, -11, enter) + lerp(0, 4, ramp(t, 5.4, 12.2)) + exit * 28;
          tx = lerp(220, 0, enter) - exit * 1500;
          ty = lerp(260, 0, enter);
        } else {
          rx = lerp(34, 6, enter) + drift * 0.4;
          ry = lerp(-8, -3, enter) + drift + exit * 22;
          tx = -exit * 1200;
          ty = lerp(520, 0, enter) + exit * 60;
        }
        const sc = lerp(0.86, 1, enter);
        css(holder, {
          opacity: enter,
          transform: `perspective(2400px) translate(${tx}px, ${ty}px) rotateX(${rx}deg) rotateY(${ry}deg) scale(${sc})`,
          filter: exit > 0.03 ? `blur(${exit * 18}px)` : "none",
        });
        // contour lumineux
        const rk = E.inOutCubic(ramp(t, 4.95, 5.85));
        rim.draw(0, rk, 1 - ramp(t, 5.85, 6.5));
        rimStatic.style.opacity = 0.32 * ramp(t, 5.7, 6.3) * (1 - exit);

        // pages : exercice → bibliothèque → lecteur
        const p1 = E.inOutQuint(ramp(t, 9.22, 9.62));
        const p2 = E.inOutQuint(ramp(t, 10.78, 11.18));
        css(ex, { transform: `translateX(${-390 * p1}px)`, opacity: 1 - 0.5 * p1 });
        css(lib, { transform: `translateX(${390 * (1 - p1) - 390 * p2}px)` });
        css(rd, { transform: `translateX(${390 * (1 - p2)}px)` });
        vis(ex, p1 < 1);
        vis(lib, p1 > 0 && p2 < 1);
        vis(rd, p2 > 0);

        // exercice
        const selT = 6.2;
        const valT = 6.95;
        const sel = t >= selT;
        const ok = t >= valT + 0.1;
        choices.forEach((c) => css(c, { background: "rgba(31, 31, 35, 0.72)", borderColor: "rgba(247, 245, 250, 0.1)", transform: "none" }));
        if (sel) {
          const pop = spring(t - selT, 2.4, 9);
          css(correct, {
            background: "rgba(48, 44, 57, 0.72)",
            borderColor: ok ? "#55C98A" : "#6157F8",
            transform: `scale(${1 + 0.035 * (1 - pop) * (t - selT < 0.4 ? 1 : 0)})`,
          });
          correctMark.style.borderColor = ok ? "rgba(85, 201, 138, 0.6)" : "#6157F8";
          correctMark.style.background = ok ? "rgba(85, 201, 138, 0.2)" : "rgba(97, 87, 248, 0.35)";
        } else {
          correctMark.style.borderColor = "rgba(247, 245, 250, 0.18)";
          correctMark.style.background = "transparent";
        }
        const okPop = spring(t - (valT + 0.1), 2.2, 8);
        css(correctEnd, { opacity: ok ? 1 : 0, transform: `scale(${ok ? okPop : 0})` });
        const trayK = E.outCubic(ramp(t, valT + 0.1, valT + 0.38));
        css(tray, { opacity: trayK, transform: `translateY(${(1 - trayK) * 24}px)`, display: trayK > 0 ? "block" : "none" });
        if (ok) {
          action.textContent = "Continuer";
          css(action, { background: "#55C98A", color: "#1D1D1D" });
        } else if (sel) {
          action.textContent = "Valider";
          css(action, { background: "#6157F8", color: "#F7F5FA" });
        } else {
          action.textContent = "Valider";
          css(action, { background: "rgba(104, 99, 112, 0.35)", color: "#9F99AA" });
        }
        const pr = lerp(1 / 9, 2 / 9, E.outCubic(ramp(t, valT + 0.15, valT + 0.51)));
        exFill.style.width = `${pr * 100}%`;

        // bibliothèque : le fil lumineux entoure la carte « Reprendre la lecture »
        const rl = E.inOutCubic(ramp(t, 9.75, 10.5));
        resumeLight.draw(0, rl, (p1 > 0.5 ? 1 : 0) * (1 - ramp(t, 10.5, 10.85)));
        // lecteur : verset 1 mis en avant, défilement doux
        const scrollK = E.inOutCubic(ramp(t, 11.25, 12.3));
        css(scroller, { transform: `translateY(${-70 * scrollK}px)` });
        v1.classList.toggle("on", t > 11.5);

        // toucher
        let touched = 0;
        touched |= tapAt(t, selT, 205, 436);
        touched |= tapAt(t, valT, 195, 780);
        touched |= tapAt(t, 8.95, 195, 780);
        touched |= tapAt(t, 10.55, 92, 488);
        if (!touched) touch.style.opacity = 0;
      },
    };
  })();

  // ------------------------------------------------------------------ scène 5 : la série
  const S5 = (() => {
    const z = LAY.card.zoom;
    const holder = h("div", "holder", stage);
    const cw = 360;
    const card = h("div", "card", holder);
    card.style.width = `${cw}px`;
    card.style.zoom = z;
    const top = h("div", "streak-top", card);
    const flame = h("div", "", top);
    css(flame, { position: "relative", width: "104px", height: "104px", flex: "none" });
    const flameOff = h("div", "abs", flame, streakIcon(104, false));
    const flameOn = h("div", "abs", flame, streakIcon(104, true));
    const numBox = h("div", "", top);
    const num = h("div", "streak-num", numBox, "0");
    h("div", "streak-lbl", numBox, "jours de série");
    h("div", "sep", card);
    h("div", "days-title", card, "Tes 7 derniers jours");
    const days = h("div", "days", card);
    const L = ["S", "D", "L", "M", "M", "J", "V"];
    const cells = L.map((l) => {
      const d = h("div", "day", days, `<div class="l">${l}</div><div class="c"><div class="dot"></div></div>`);
      const c = d.querySelector(".c");
      const chk = h("div", "abs", c, icon("check", 22, "#F7F5FA", 2.8));
      c.style.position = "relative";
      css(chk, { left: "10px", top: "10px" });
      return { c, chk, dot: d.querySelector(".dot") };
    });
    // fil lumineux sous la rangée de jours
    days.style.position = "relative";
    const rowW = cw - 52;
    const lsvg = sv("svg", { width: rowW, height: 40, class: "abs" }, null);
    days.appendChild(lsvg);
    css(lsvg, { left: "0px", top: "calc(100% - 6px)" });
    addDefs(sv("defs", {}, lsvg));
    const light = new Light(lsvg, 1 / z).path(`M 20 20 L ${rowW - 20} 20`);
    const ch = 380; // hauteur approximative de la carte (px logiques)
    css(holder, { width: `${cw * z}px`, height: `${ch * z}px`, left: `${LAY.vis.cx - (cw * z) / 2}px`, top: `${LAY.vis.cy - (ch * z) / 2}px` });
    const t0 = 13.05;
    const step = 0.2;
    return {
      update(t) {
        const on = t > 12.4 && t < 15.05;
        vis(holder, on);
        if (!on) return;
        const enter = E.outQuint(ramp(t, 12.45, 13.15));
        const exit = E.inCubic(ramp(t, 14.62, 15.0));
        const bob = Math.sin(t * 1.4) * 5;
        const rx = LAND ? lerp(12, 4, enter) - exit * 30 : lerp(16, 4, enter) - exit * 34;
        const ry = LAND ? lerp(32, -6, enter) : lerp(18, -2, enter);
        const tx = LAND ? lerp(900, 0, enter) : lerp(700, 0, enter);
        const ty = -exit * (LAND ? 600 : 900) + bob;
        css(holder, {
          opacity: Math.min(1, enter * 1.4) * (1 - exit),
          transform: `perspective(2200px) translate(${tx}px, ${ty}px) rotateX(${rx}deg) rotateY(${ry}deg)`,
          filter: (1 - enter) > 0.04 || exit > 0.03 ? `blur(${(1 - enter) * 16 + exit * 16}px)` : "none",
        });
        let n = 0;
        cells.forEach((cell, i) => {
          const ti = t0 + i * step;
          const k = spring(t - ti, 2.2, 8);
          const done = t >= ti;
          if (done) n = i + 1;
          css(cell.c, { background: done ? "#6157F8" : "rgba(247, 245, 250, 0.07)", transform: `scale(${done ? 0.7 + 0.3 * k : 1})` });
          css(cell.chk, { opacity: done ? 1 : 0, transform: `scale(${done ? k : 0})` });
          cell.dot.style.opacity = done ? 0 : 1;
        });
        num.textContent = String(n);
        const fk = ramp(t, t0, t0 + 0.25);
        flameOn.style.opacity = fk;
        flameOff.style.opacity = 1 - fk;
        const pulse = spring(t - t0, 1.8, 6);
        flame.style.transform = `scale(${t >= t0 ? 0.85 + 0.15 * pulse : 1})`;
        const lk = E.inOutCubic(ramp(t, t0 - 0.1, t0 + 6 * step + 0.25));
        light.draw(Math.max(0, lk - 0.45), lk, 1 - ramp(t, 14.3, 14.7));
      },
    };
  })();

  // ------------------------------------------------------------------ scène 6 : le parcours des Piliers
  const S6 = (() => {
    const z = LAY.rail.zoom;
    const holder = h("div", "holder", stage);
    const rw = 430;
    const box = h("div", "", holder);
    css(box, { width: `${rw}px`, zoom: z });
    h("div", "rail-head", box, `<div class="rail-ico">${icon("compass", 26, "#BBB7FD")}</div><div class="rail-title">Les Piliers</div>`);
    h("div", "rail-desc", box, "Le parcours d’introduction aux cinq piliers de l’Islam.");
    const prog = h("div", "rail-prog", box, `<span>Avancement du parcours</span><b>0/5 · 0 %</b>`);
    const progB = prog.querySelector("b");
    const track = h("div", "rail-track", box, `<div class="fill"></div>`);
    const fill = track.querySelector(".fill");
    const rows = h("div", "rail-rows", box);
    // titres et descriptions réels : app/data/pillarsCourse.ts
    const levels = [
      ["La Shahada", "Comprendre le témoignage de foi et sa place parmi les cinq piliers."],
      ["La Salat", "Comprendre la place des cinq prières quotidiennes."],
      ["La Zakat", "Comprendre une obligation liée aux biens et à la solidarité."],
      ["Le Sawm", "Comprendre le jeûne du mois de Ramadan."],
      ["Le Hajj", "Comprendre le pèlerinage et les conditions générales de son obligation."],
    ];
    const rowH = 112;
    const conns = [];
    for (let i = 0; i < 4; i++) {
      const c = h("div", "connector", rows);
      css(c, { top: `${i * rowH + 64}px`, height: `${rowH - 64}px`, background: "rgba(247, 245, 250, 0.12)" });
      const f = h("div", "connector", rows);
      css(f, { top: `${i * rowH + 64}px`, height: `${rowH - 64}px`, background: "#4F45D8", transformOrigin: "50% 0" });
      conns.push(f);
    }
    const nodes = levels.map(([title, desc], i) => {
      const r = h("div", "node-row", rows, `<div class="nt">${title}</div><div class="nd">${desc}</div>`);
      const n = h("div", "node", r);
      const lockI = h("div", "abs", n, icon("lock", 22, "#9F99AA"));
      css(lockI, { left: "21px", top: "21px" });
      const chk = h("div", "abs", n, icon("check", 28, "#F7F5FA", 2.8));
      css(chk, { left: "18px", top: "18px" });
      return { r, n, lockI, chk };
    });
    const lsvg = sv("svg", { width: 70, height: rowH * 5, class: "abs" }, null);
    rows.appendChild(lsvg);
    css(lsvg, { left: "0px", top: "0px" });
    addDefs(sv("defs", {}, lsvg));
    const light = new Light(lsvg, 1 / z).path(`M 32 32 L 32 ${4 * rowH + 32}`);
    const bh = 760;
    css(holder, { width: `${rw * z}px`, height: `${bh * z}px`, left: `${LAY.vis.cx - (rw * z) / 2}px`, top: `${LAY.vis.cy - (bh * z) / 2 + (LAND ? 10 : 30)}px` });
    const T0 = 15.55;
    const STEP = 0.3;
    return {
      update(t) {
        const on = t > 14.85 && t < 17.55;
        vis(holder, on);
        if (!on) return;
        const enter = E.outQuint(ramp(t, 14.88, 15.5));
        const exit = E.inCubic(ramp(t, 17.1, 17.5));
        css(holder, {
          opacity: Math.min(1, enter * 1.3) * (1 - exit),
          transform: `perspective(2400px) translateY(${lerp(LAND ? 500 : 700, 0, enter)}px) rotateX(${lerp(28, 3, enter)}deg) rotateY(${LAND ? -8 : 0}deg) scale(${1 - 0.18 * exit})`,
          filter: (1 - enter) > 0.04 || exit > 0.04 ? `blur(${(1 - enter) * 14 + exit * 10}px)` : "none",
        });
        let done = 0;
        nodes.forEach((nd, i) => {
          const ti = T0 + i * STEP;
          const k = spring(t - ti, 2.1, 8);
          const isDone = t >= ti;
          if (isDone) done = i + 1;
          css(nd.n, {
            background: isDone ? "#6157F8" : "rgba(104, 99, 112, 0.28)",
            boxShadow: isDone ? "0 0 0 6px rgba(97, 87, 248, 0.16)" : "none",
            transform: `scale(${isDone ? 0.82 + 0.18 * k : 1})`,
          });
          nd.lockI.style.opacity = isDone ? 0 : 1;
          css(nd.chk, { opacity: isDone ? 1 : 0, transform: `scale(${isDone ? k : 0})` });
          nd.r.style.opacity = isDone ? 1 : 0.55;
          if (i < 4) conns[i].style.transform = `scaleY(${E.inOutCubic(ramp(t, ti, ti + STEP))})`;
        });
        const pct = Math.round((done / 5) * 100);
        progB.textContent = `${done}/5 · ${pct} %`;
        const fk = lerp(0, 1, E.outCubic(ramp(t, T0 - 0.05, T0 + 4 * STEP + 0.3)));
        fill.style.width = `${fk * 100}%`;
        const lk = E.inOutCubic(ramp(t, T0 - 0.1, T0 + 4 * STEP));
        light.draw(0, lk, 1 - ramp(t, 17.0, 17.35));
      },
    };
  })();

  // ------------------------------------------------------------------ scène 7 : les parcours en branches
  const S7 = (() => {
    const root = h("div", "scene", stage);
    const svg = sv("svg", { width: W, height: H, class: "layer" }, null);
    root.appendChild(svg);
    addDefs(sv("defs", {}, svg));
    const rootPt = LAND ? { x: 1400, y: 1090 } : { x: 540, y: 1960 };
    const ell = LAND ? { rx: 400, ry: 600 } : { rx: 380, ry: 880 };
    const base = LAND ? { x: 1400, y: 1050 } : { x: 540, y: 1790 };
    const angles = [162, 126, 90, 54, 18];
    const items = [
      ["sunnah", "Prière"],
      ["quran", "Coran"],
      ["prophets", "Prophètes"],
      ["ramadan", "Ramadan"],
      ["hajj-umrah", "Hajj & Umrah"],
    ].map(([key, name], i) => {
      const a = (angles[i] * Math.PI) / 180;
      const x = base.x + ell.rx * Math.cos(a);
      const y = base.y - ell.ry * Math.sin(a);
      const w = LAND ? 235 : 260;
      const wrap = h("div", "isle", root);
      css(wrap, { width: `${w}px`, left: `${x - w / 2}px`, top: `${y - w / 2}px` });
      const img = h("img", "", wrap);
      img.src = `assets/img/island-${key}.webp`;
      const nm = h("div", "name", wrap, name);
      css(nm, { top: `${w * 0.98}px`, fontSize: `${LAND ? 26 : 32}px` });
      const tgt = { x, y: y + w * 0.38 };
      const d = `M ${rootPt.x} ${rootPt.y} C ${rootPt.x} ${rootPt.y - (LAND ? 260 : 420)}, ${tgt.x} ${tgt.y + (LAND ? 260 : 380)}, ${tgt.x} ${tgt.y}`;
      const light = new Light(svg).path(d);
      return { wrap, nm, light, i };
    });
    return {
      update(t) {
        const on = t > 17.3 && t < 19.9;
        vis(root, on);
        if (!on) return;
        const exit = E.inCubic(ramp(t, 19.4, 19.8));
        items.forEach((it) => {
          const t0 = 17.3 + it.i * 0.17;
          const k = E.inOutCubic(ramp(t, t0, t0 + 0.45));
          const arrive = t0 + 0.42;
          const pop = spring(t - arrive, 1.9, 7.5);
          const bob = Math.sin(t * 1.5 + it.i) * 6;
          it.light.draw(Math.max(0, exit * 1.0), Math.max(k, exit), 1 - ramp(t, 19.35, 19.75), 1);
          css(it.wrap, {
            opacity: clamp(pop * 1.5) * (1 - exit),
            transform: `translateY(${bob - exit * 40}px) scale(${(t >= arrive ? 0.6 + 0.4 * pop : 0) * (1 - 0.2 * exit)})`,
          });
          css(it.nm, { opacity: E.outCubic(ramp(t, arrive + 0.1, arrive + 0.45)) });
        });
      },
    };
  })();

  // ------------------------------------------------------------------ scène 8 : signature + mascotte
  const S8 = (() => {
    const root = h("div", "scene", stage);
    const mascot = h("img", "abs", root);
    mascot.src = "assets/img/coach.webp";
    const mh = LAND ? 640 : 620;
    const mw = (mh * 900) / 975;
    const mpos = LAND ? { x: 620, y: 560 } : { x: 540, y: 800 };
    css(mascot, { width: `${mw}px`, height: `${mh}px`, left: `${mpos.x - mw / 2}px`, top: `${mpos.y - mh / 2}px` });
    const words = ["Comprendre.", "Pratiquer.", "Progresser."];
    const fs = LAND ? 104 : 96;
    const gap = LAND ? 142 : 132;
    const blockW = LAND ? 760 : 700;
    const bx = LAND ? 1060 : (W - blockW) / 2 + 30;
    const by = LAND ? 540 - gap : 1290;
    const svg = sv("svg", { width: W, height: H, class: "layer" }, null);
    root.appendChild(svg);
    addDefs(sv("defs", {}, svg));
    const nodeX = bx + 18;
    const conn = sv("path", { d: `M ${nodeX} ${by} L ${nodeX} ${by + 2 * gap}`, stroke: "rgba(247,245,250,0.14)", "stroke-width": 4, fill: "none" }, svg);
    const light = new Light(svg).path(`M ${nodeX} ${by - gap * 0.9} L ${nodeX} ${by + 2 * gap}`);
    const els = words.map((w, i) => {
      const y = by + i * gap;
      const node = sv("circle", { cx: nodeX, cy: y, r: LAND ? 17 : 16, fill: "rgba(104,99,112,0.4)" }, svg);
      const e = h("div", "tagword", root, w);
      css(e, { left: `${nodeX + 56}px`, top: `${y - fs * 0.66}px`, fontSize: `${fs}px` });
      return { e, node, i };
    });
    return {
      update(t) {
        const on = t > 19.6 && t < 22.95;
        vis(root, on);
        if (!on) return;
        const exit = E.inCubic(ramp(t, 22.4, 22.8));
        const pop = spring(t - 19.85, 1.6, 6.5);
        const bob = Math.sin(t * 1.7) * 10;
        css(mascot, {
          opacity: clamp(pop * 1.6) * (1 - exit),
          transform: `translateY(${bob}px) rotate(${Math.sin(t * 1.2) * 2}deg) scale(${(0.5 + 0.5 * pop) * (1 - 0.15 * exit)})`,
        });
        const lk = E.inOutCubic(ramp(t, 19.85, 21.25));
        light.draw(Math.max(0, lk - 0.5), lk, 1 - ramp(t, 22.3, 22.7));
        conn.style.opacity = ramp(t, 19.85, 20.3) * (1 - exit);
        els.forEach(({ e, node, i }) => {
          const ti = 20.05 + i * 0.6;
          const k = E.outQuint(ramp(t, ti, ti + 0.5));
          const lit = t >= ti;
          node.setAttribute("fill", lit ? "#6157F8" : "rgba(104,99,112,0.4)");
          node.style.opacity = ramp(t, 19.85, 20.2) * (1 - exit);
          const r = lit ? (LAND ? 17 : 16) * (0.8 + 0.2 * spring(t - ti, 2, 8)) : LAND ? 17 : 16;
          node.setAttribute("r", r);
          css(e, { opacity: k * (1 - exit), transform: `translateX(${(1 - k) * -26}px)`, color: i === 2 ? "#BBB7FD" : "#F7F5FA" });
        });
      },
    };
  })();

  // ------------------------------------------------------------------ logos
  const LOGO1 = buildLogo();
  const LOGO9 = buildLogo();
  const fine = h("div", "fine", stage, "Texte arabe : Tanzil Project · Traduction française : Rachid Maach (QuranEnc)");
  css(fine, { top: `${LAY.logo.fineY}px`, fontSize: `${LAY.logo.fine}px` });

  const grain = h("div", "layer", stage);
  grain.id = "grain";
  const vig = h("div", "layer", stage);
  vig.id = "vignette";
  const fade = h("div", "layer", stage);
  fade.style.background = "#1D1D1D";

  // ------------------------------------------------------------------ boucle de rendu
  window.seek = (t) => {
    updateBackground(t);
    // Scène 1 : logo d'ouverture
    const s1exit = E.inCubic(ramp(t, 1.95, 2.4));
    LOGO1.update(t, { show: t < 2.45, d0: 0.12, d1: 1.15, f0: 1.0, w0: 1.3, t0: 1.62, alpha: 1 - s1exit, dy: -s1exit * (LAND ? 160 : 260), scale: 1 - 0.06 * s1exit });
    S2.update(t);
    PH.update(t);
    S5.update(t);
    S6.update(t);
    S7.update(t);
    S8.update(t);
    // Scène 9 : logo final
    LOGO9.update(t, { show: t > 22.6, d0: 22.72, d1: 23.45, f0: 23.3, w0: 23.55, t0: 23.85, alpha: E.outCubic(ramp(t, 22.6, 22.8)) });
    css(fine, { opacity: E.outCubic(ramp(t, 24.0, 24.5)) * 0.9 });
    updateCaptions(t);
    css(grain, { backgroundPosition: `${Math.floor(t * 30 * 37) % 256}px ${Math.floor(t * 30 * 59) % 256}px` });
    fade.style.opacity = Math.max(1 - ramp(t, 0, 0.18), ramp(t, 26.0, 26.4));
  };
  window.DURATION = DURATION;
  window.READY = Promise.all([
    document.fonts.ready,
    ...[...document.images].map((im) => (im.complete ? Promise.resolve() : new Promise((r) => (im.onload = im.onerror = r)))),
  ]).then(() => {
    window.seek(0);
    return true;
  });
})();
