"""Rocher des Hokage : la grande falaise de grès au bout de la zone Naruto (style stud).

Origine = centre de l'entrée du passage, au niveau du sol.
Exception à la règle « l'avant regarde -Z » : la falaise regarde +Z (vers les joueurs qui arrivent),
sa face avant suit à peu près z = 0 et la masse s'étend vers -Z sur `profondeur`.

Composition (de bas en haut, en façade) :
- falaise basse en strates horizontales (blocs de 8 à 16 studs, avancées et retraits, fissures) ;
- portail de pierre claire autour du passage (piédroits en harpe, linteau à gradins, clé de voûte) ;
- corniche continue, puis le panneau en retrait où sont sculptés cinq grands visages ;
- au-dessus, des terrasses qui montent vers un sommet central, avec arbres et buissons ;
- escalier de bois en zigzag sur un côté jusqu'à un belvédère, petites maisons blanches au pied.
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, rot_z, shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Couleurs locales (dérivées de la palette)
# ---------------------------------------------------------------------------
PIERRE = mix(c("creme"), c("roche_claire"), 0.30)      # pierre taillée claire du portail
PIERRE_F = mix(c("creme"), c("roche_claire"), 0.80)
PEAU = mix(c("roche_claire"), c("creme"), 0.35)        # visages : le grès le plus clair
PEAU_C = mix(c("roche_claire"), c("creme"), 0.60)      # arcades, nez (accrochent la lumière)
CREUX = mix(c("roche_ombre"), c("roche_fonce"), 0.20)  # orbites, bouche, rainures
CHEV = c("roche")
CHEV_C = mix(c("roche"), c("roche_claire"), 0.55)
BANDEAU = c("roche_fonce")

# clés de couleur des bas-reliefs
K_PEAU, K_PEAU_C, K_CREUX, K_CHEV, K_CHEV_C, K_BANDEAU, K_PLAQUE = range(1, 8)
COULEURS_RELIEF = {K_PEAU: PEAU, K_PEAU_C: PEAU_C, K_CREUX: CREUX, K_CHEV: CHEV, K_CHEV_C: CHEV_C,
                   K_BANDEAU: BANDEAU, K_PLAQUE: PIERRE}


# ---------------------------------------------------------------------------
# Bas-relief sur grille d'un stud (visages)
# ---------------------------------------------------------------------------
class _Relief:
    """Grille (v vers le haut, u centré) : profondeur de saillie et teinte par case d'un stud."""

    def __init__(self, demi: int = 23, haut: int = 50):
        self.demi, self.haut = demi, haut
        self.d = np.zeros((haut, 2 * demi))
        self.k = np.zeros((haut, 2 * demi), int)
        v, u = np.mgrid[0:haut, 0:2 * demi]
        self._uc = u + 0.5 - demi
        self._vc = v + 0.5

    def rect(self, u0, v0, u1, v1, d, k):
        i0, i1 = max(0, int(round(u0 + self.demi))), min(2 * self.demi, int(round(u1 + self.demi)))
        j0, j1 = max(0, int(round(v0))), min(self.haut, int(round(v1)))
        if i1 > i0 and j1 > j0:
            self.d[j0:j1, i0:i1] = d
            self.k[j0:j1, i0:i1] = k

    def sym(self, u0, v0, u1, v1, d, k):
        self.rect(u0, v0, u1, v1, d, k)
        self.rect(-u1, v0, -u0, v1, d, k)

    def rows(self, spec, d, k):
        for v0, v1, hw in spec:
            self.rect(-hw, v0, hw, v1, d, k)

    def poly(self, pts, d, k, mirror=False):
        for P in ([pts, [(-u, v) for u, v in pts]] if mirror else [pts]):
            inside = np.zeros_like(self.d, bool)
            n = len(P)
            for a in range(n):
                (u0, v0), (u1, v1) = P[a], P[(a + 1) % n]
                if v0 == v1:
                    continue
                cond = (self._vc >= min(v0, v1)) & (self._vc < max(v0, v1))
                ux = u0 + (self._vc - v0) * (u1 - u0) / (v1 - v0)
                inside ^= cond & (self._uc < ux)
            self.d[inside] = d
            self.k[inside] = k

    def emit(self, b, xc, y0, zw, studs="top"):
        """Un bloc par rectangle de cases de même (profondeur, teinte) ; chaque bloc part de zw - 1 (ancré)."""
        from textures import mask_rects

        n = 0
        for d, k in sorted({(float(d), int(k)) for d, k in zip(self.d.ravel(), self.k.ravel()) if k}):
            mask = (self.d == d) & (self.k == k)
            for x, y, w, h in mask_rects(mask):
                u0 = x - self.demi
                b.box((xc + u0, y0 + y, zw - 1), (xc + u0 + w, y0 + y + h, zw + d), COULEURS_RELIEF[k], studs=studs)
                n += 1
        return n


def _visage_base(g: _Relief, st: dict):
    """Tête commune : mâchoire à gradins, oreilles, pommettes, orbites, arcade, nez, bouche, menton."""
    # silhouette en deux paliers (bord à 4, centre à 5) : le visage « tourne » sous le soleil
    g.rows([(0, 2, 5), (2, 4, 7), (4, 7, 9), (7, 10, 11), (10, 14, 12), (14, 37, 13)], 4, K_PEAU)
    g.rows([(1, 3, 3), (3, 5, 5), (5, 8, 7), (8, 11, 9), (11, 15, 10), (15, 37, 10)], 5, K_PEAU)
    # oreilles
    g.sym(13, 14, 16, 24, 3.5, K_PEAU)
    g.sym(14, 16, 15, 22, 3, K_CREUX)
    # pommettes
    g.sym(5, 12, 11, 17, 5.5, K_PEAU)
    # orbites et yeux
    ew = st.get("oeil", 0)
    g.sym(3, 18, 11 + ew, 25, 3, K_CREUX)
    g.sym(5, 19, 10 + ew, 22, 4, K_PEAU)
    # arcade sourcilière (le soleil la sculpte : ombre portée dans les orbites)
    g.rect(-12, 25, 12, 28, 7, K_PEAU_C)
    if st.get("froncé"):
        g.sym(1, 27, 6, 28, 5, K_PEAU)
        g.sym(1, 24, 6, 25, 7, K_PEAU_C)
    # nez
    g.rect(-1, 17, 1, 25, 7, K_PEAU_C)
    g.rect(-2, 13, 2, 17, 8, K_PEAU_C)
    g.sym(2, 13, 3, 15, 6.5, K_PEAU)
    # bouche
    mw = st.get("bouche", 5)
    g.rect(-mw + 1, 9, mw - 1, 11, 5.5, K_PEAU)
    g.rect(-mw, 8, mw, 9, 3.5, K_CREUX)
    g.rect(-mw + 2, 6, mw - 2, 8, 5.5, K_PEAU)
    # menton
    g.rect(-4, 1, 4, 5, 6, K_PEAU)


def _visage(b, kind: int, xc: float, y0: float, zw: float) -> int:
    """Cinq têtes stylisées, chacune avec une silhouette de cheveux bien à elle."""
    g = _Relief()
    st = {}
    if kind == 1:  # cheveux lisses + bandeau frontal à plaque
        g.rows([(29, 38, 15), (38, 41, 14), (41, 43, 12), (43, 45, 9), (45, 46, 5)], 4.5, K_CHEV)
        g.sym(13, 17, 16, 29, 4.5, K_CHEV)
        _visage_base(g, st)
        g.rows([(38, 41, 11), (41, 43, 9), (43, 45, 6)], 5.5, K_CHEV_C)
        g.rect(-5, 37, -4, 45, 4, K_CREUX)  # raie
        g.sym(13, 17, 16, 29, 4.5, K_CHEV)
        g.rect(-15, 29, 15, 34, 5.5, K_BANDEAU)
        g.rect(-7, 29, 7, 34, 6.5, K_PLAQUE)
        g.rect(-1, 30, 1, 33, 6, K_CREUX)
        g.sym(5, 31, 6, 32, 6, K_CREUX)
    elif kind == 2:  # cheveux courts en épis
        g.rows([(30, 38, 15)], 4.5, K_CHEV)
        g.sym(13, 19, 16, 30, 4.5, K_CHEV)
        pics = [((-17, 36), (-8, 36), (-16, 44)), ((-10, 36), (-1, 36), (-6, 47)), ((-4, 36), (5, 36), (1, 49)),
                ((2, 36), (11, 36), (7, 47)), ((8, 36), (17, 36), (16, 44))]
        for i, p in enumerate(pics):
            g.poly(p, 4.5 if i % 2 else 5.5, K_CHEV if i % 2 else K_CHEV_C)
        g.poly([(-15, 29), (-15, 37), (-21, 35)], 4.5, K_CHEV, mirror=True)
        st = {"froncé": True, "bouche": 4}
        _visage_base(g, st)
        for p in [((-13, 37), (-6, 37), (-11, 31)), ((-7, 37), (1, 37), (-3, 30)), ((0, 37), (8, 37), (5, 31)),
                  ((6, 37), (13, 37), (11, 32))]:
            g.poly(p, 5.5, K_CHEV_C)
    elif kind == 3:  # capuche plate (sommet carré), visage âgé à barbiche
        g.rect(-18, 6, 18, 43, 4, K_CHEV)
        g.rows([(43, 45, 16)], 4, K_CHEV)
        st = {"bouche": 5}
        _visage_base(g, st)
        g.sym(13, 7, 15, 37, 5, K_CHEV_C)
        g.rect(-15, 35, 15, 37, 5, K_CHEV_C)
        g.rect(-6, 37, 6, 43, 5.5, K_PLAQUE)
        for u, v in [(0, 42), (0, 41), (-3, 41), (2, 41), (0, 40), (-1, 39), (1, 39), (-2, 38), (2, 38)]:
            g.rect(u, v, u + 1, v + 1, 5, K_CREUX)
        g.rect(-7, 31, 7, 32, 4.5, K_CREUX)
        g.rect(-5, 33, 5, 34, 4.5, K_CREUX)
        g.sym(10, 9, 11, 14, 3.5, K_CREUX)
        g.rect(-3, 0, 3, 4, 6, K_CHEV)
    elif kind == 4:  # grands épis balayés vers la droite, longues mèches
        g.rows([(27, 38, 17)], 4.5, K_CHEV)
        pics = [((-20, 35), (-9, 37), (-18, 46)), ((-12, 37), (0, 37), (-4, 49)), ((-3, 37), (9, 37), (8, 50)),
                ((5, 36), (17, 36), (20, 46)), ((15, 27), (15, 38), (23, 31)), ((-15, 27), (-15, 37), (-22, 30))]
        for i, p in enumerate(pics):
            g.poly(p, 5.5 if i % 2 == 0 else 4.5, K_CHEV_C if i % 2 == 0 else K_CHEV)
        st = {"oeil": 1}
        _visage_base(g, st)
        g.poly([(10, 31), (15, 31), (14, 12)], 5.5, K_CHEV_C, mirror=True)
        for p in [((-13, 37), (-4, 37), (-10, 27)), ((-6, 37), (3, 37), (-1, 26)), ((1, 37), (11, 37), (8, 28))]:
            g.poly(p, 5.5, K_CHEV_C)
    else:  # cheveux longs et raides, frange droite
        g.sym(11, 0, 19, 36, 4.5, K_CHEV)
        g.sym(15, 0, 17, 35, 5.5, K_CHEV_C)
        g.rows([(34, 40, 18), (40, 42, 16), (42, 44, 13), (44, 45, 8)], 4.5, K_CHEV)
        st = {"bouche": 4}
        _visage_base(g, st)
        g.sym(11, 0, 13, 30, 4.5, K_CHEV)
        g.rect(-13, 29, 13, 36, 5.5, K_CHEV_C)
        for u in range(-12, 12, 4):
            g.rect(u, 28, u + 2, 29, 5.5, K_CHEV_C)
        g.rows([(36, 40, 12), (40, 42, 9)], 5.5, K_CHEV_C)
        g.rect(-1, 36, 1, 44, 4, K_CREUX)
    return g.emit(b, xc, y0, zw)


# ---------------------------------------------------------------------------
# Petits éléments
# ---------------------------------------------------------------------------
def _colonnes(x0: float, x1: float, rng, largeurs=(8, 10, 12, 14, 16)) -> list:
    xs = [x0]
    while xs[-1] < x1 - 1e-6:
        nx = xs[-1] + float(rng.choice(largeurs))
        if x1 - nx < 6:
            nx = x1
        xs.append(nx)
    return list(zip(xs[:-1], xs[1:]))


def _lanterne_pierre(b, x, z):
    """Lanterne de pierre (tōrō) : socle, fût, foyer lumineux, toit, pointe."""
    gr, grf = c("pave"), c("pave_fonce")
    b.box((x - 2.5, 0, z - 2.5), (x + 2.5, 1.5, z + 2.5), grf, studs="top")
    b.box((x - 0.9, 1.5, z - 0.9), (x + 0.9, 6.5, z + 0.9), gr)
    b.box((x - 2, 6.5, z - 2), (x + 2, 7.5, z + 2), grf, studs="top")
    b.box((x - 1.6, 7.5, z - 1.6), (x + 1.6, 10.5, z + 1.6), gr)
    b.box((x - 1.0, 8.0, z - 1.7), (x + 1.0, 10.0, z + 1.7), c("orange_lampion"), material="Neon", collide=False)
    b.box((x - 1.7, 8.0, z - 1.0), (x + 1.7, 10.0, z + 1.0), c("orange_lampion"), material="Neon", collide=False)
    b.box((x - 3, 10.5, z - 3), (x + 3, 11.5, z + 3), grf, studs="top")
    b.box((x - 1.8, 11.5, z - 1.8), (x + 1.8, 12.5, z + 1.8), gr, studs="top")
    b.ball((x, 13.2, z), 0.8, gr)


def _buisson(b, x, y, z, rng, s=1.0):
    w, d = (3.5 + rng.uniform(0, 2)) * s, (3 + rng.uniform(0, 1.5)) * s
    h = 2.5 * s
    b.box((x - w / 2, y, z - d / 2), (x + w / 2, y + h, z + d / 2), vary("feuille_fonce", rng, 0.05), studs="top")
    b.box((x - w / 2 + 0.8, y + h, z - d / 2 + 0.6), (x + w / 2 - 0.6, y + h + 1.3 * s, z + d / 2 - 0.5),
          vary("feuille", rng, 0.05), studs="top")


def _arbre(b, x, y, z, rng, s=1.0):
    """Arbre stud : tronc carré, trois plateaux de feuillage décalés."""
    th = (5 + rng.uniform(0, 3)) * s
    b.box((x - 0.8 * s, y, z - 0.8 * s), (x + 0.8 * s, y + th, z + 0.8 * s), c("tronc"))
    w = (9 + rng.uniform(0, 2)) * s
    y1 = y + th
    b.box((x - w / 2, y1, z - w / 2), (x + w / 2, y1 + 3 * s, z + w / 2), vary("feuille_fonce", rng, 0.04), studs="top")
    dx, dz = rng.uniform(-1, 1, 2) * s
    w2 = w * 0.7
    b.box((x + dx - w2 / 2, y1 + 3 * s, z + dz - w2 / 2), (x + dx + w2 / 2, y1 + 5.5 * s, z + dz + w2 / 2),
          vary("feuille", rng, 0.04), studs="top")
    w3 = w * 0.38
    b.box((x + dx * 0.5 - w3 / 2, y1 + 5.5 * s, z + dz * 0.5 - w3 / 2),
          (x + dx * 0.5 + w3 / 2, y1 + 7 * s, z + dz * 0.5 + w3 / 2), vary("feuille_claire", rng, 0.04), studs="top")


def _maison(b, xc, s, rng, toit_plat=False):
    """Petite maison blanche à toit rouge, posée sur un replat de roche au pied de la falaise (avant = +Z)."""
    X = lambda x: s * x  # noqa: E731
    x0, x1 = sorted((X(xc - 12.7), X(xc + 12.7)))
    # replat de roche + deux marches
    b.box((x0, 0, -1.3), (x1, 5, 15.7), vary("roche", rng, 0.04), studs="top")
    b.box((x0 + 0.4, 5, -1.3), (x1 - 0.4, 5.6, 15.3), vary("roche_claire", rng, 0.03), studs="top")
    b.box((X(xc) - 3.2, 0, 15.7), (X(xc) + 3.2, 2, 18.7), c("pave"), studs="top")
    b.box((X(xc) - 3.2, 2, 15.7), (X(xc) + 3.2, 3.8, 17.2), c("pave"), studs="top")
    y0 = 5.6
    hx0, hx1 = X(xc) - 8, X(xc) + 8
    z0, z1 = 0.7, 10.7
    b.box((hx0, y0, z0), (hx1, y0 + 0.8, z1), c("bois_fonce"))
    b.box((hx0 + 0.2, y0 + 0.8, z0 + 0.2), (hx1 - 0.2, y0 + 8.5, z1 - 0.2), vary("enduit", rng, 0.02))
    yb = y0 + 8.5
    b.box((hx0 - 0.2, yb, z0 - 0.2), (hx1 + 0.2, yb + 1, z1 + 0.2), c("poutre"))
    # façade : porte, fenêtres, poteaux d'angle
    b.box((X(xc) - 1.6, y0 + 0.8, z1 - 0.2), (X(xc) + 1.6, y0 + 6, z1 + 0.15), c("bois"))
    b.box((X(xc) - 2.4, y0 + 4.6, z1 + 0.15), (X(xc) + 2.4, y0 + 7.4, z1 + 0.6), c("noren_bleu"), collide=False)
    for dx in (-5.5, 5.5):
        b.box((X(xc) + dx - 2, y0 + 3.2, z1 - 0.2), (X(xc) + dx + 2, y0 + 6.4, z1 + 0.1), c("fenetre"))
        b.box((X(xc) + dx - 2.3, y0 + 2.8, z1 - 0.2), (X(xc) + dx + 2.3, y0 + 3.2, z1 + 0.5), c("bois_clair"))
    for x in (hx0, hx1 - 0.8):
        b.box((x - 0.1, y0 + 0.8, z1 - 0.7), (x + 0.9, yb, z1 + 0.1), c("poutre"))
    yt = yb + 1
    if not toit_plat:
        zm = (z0 + z1) / 2
        b.wedge((hx0 - 1.6, yt, zm), (hx1 + 1.6, yt + 4.5, z1 + 1.8), c("toit_rouge"), down="+z", studs="top")
        b.wedge((hx0 - 1.6, yt, z0 - 1.6), (hx1 + 1.6, yt + 4.5, zm), shade(c("toit_rouge"), 0.9), down="-z", studs="top")
        b.box((hx0 - 1.8, yt + 4.5, zm - 0.6), (hx1 + 1.8, yt + 5.1, zm + 0.6), c("rouge_fonce"), studs="top")
        for x in (hx0 + 0.2, hx1 - 0.2):
            b.wedge((x - 0.1 if x < X(xc) else x - 0.1, yt, zm), (x + 0.1, yt + 4.2, z1 - 0.2), vary("enduit", rng, 0.02), down="+z")
            b.wedge((x - 0.1, yt, z0 + 0.2), (x + 0.1, yt + 4.2, zm), vary("enduit", rng, 0.02), down="-z")
    else:
        # toit-terrasse : acrotère, citerne sur pieds, petit auvent rouge au-dessus de la porte
        b.box((hx0 - 0.6, yt, z0 - 0.6), (hx1 + 0.6, yt + 0.8, z1 + 0.6), c("toit_rouge"), studs="top")
        b.box((hx0 - 0.6, yt + 0.8, z1 - 0.2), (hx1 + 0.6, yt + 1.8, z1 + 0.6), c("rouge_fonce"))
        cx = X(xc) + s * 3.5
        for dx in (-1.6, 1.6):
            for dz in (-1.6, 1.6):
                b.box((cx + dx - 0.25, yt + 0.8, 5.7 + dz - 0.25), (cx + dx + 0.25, yt + 2.8, 5.7 + dz + 0.25), c("metal_fonce"))
        b.cyl((cx, yt + 5.3, 5.7), 2.6, 5, c("citerne"), axis="y")
        b.cyl((cx, yt + 8.0, 5.7), 1.6, 0.6, c("metal"), axis="y")
        b.wedge((X(xc) - 3.4, y0 + 7.4, z1 + 0.6), (X(xc) + 3.4, y0 + 8.4, z1 + 3.0), c("toit_rouge"), down="+z", studs="top")


def _belvedere_et_escalier(b, s, xa, xb, y_bas, y_corniche, y_haut, z_bas, z_haut, rng):
    """Escalier de bois en zigzag (volées de 6 marches) collé à la falaise, puis belvédère au sommet.

    xa..xb : emprise en x (côté droit, recopiée en miroir si s = -1). Paliers de 6 studs aux deux bouts.
    z_bas / z_haut : front de la falaise sous et au-dessus de la corniche. Volées de 5 studs de large.
    """
    X = lambda x: s * x  # noqa: E731
    bois, bois_f, bois_c = c("bois"), c("bois_fonce"), c("bois_clair")
    L0, L1 = xa, xa + 6           # palier gauche
    R0, R1 = xb - 6, xb           # palier droit
    run = R0 - L1                 # 18 studs = 6 marches de 3
    n = 6
    ang = math.degrees(math.atan2(12, run))
    longueur = math.hypot(run, 12)

    def bx(xx0, y0, zz0, xx1, y1, zz1, col, **kw):
        a, bb = sorted((X(xx0), X(xx1)))
        return b.box((a, y0, zz0), (bb, y1, zz1), col, **kw)

    def poutre_pente(xm, ym, zm, ep, larg, col, sens):
        # bloc incliné (rotation autour de Z) centré en (xm, ym, zm)
        a = ang if (sens * s) > 0 else -ang
        return b.part("block", (longueur + 0.6, ep, larg), (X(xm), ym, zm), rot_z(a), col)

    def volee(y0, sens, zf):
        z0, z1 = zf, zf + 5
        for i in range(n):
            xi0 = L1 + 3 * i if sens > 0 else R0 - 3 * (i + 1)
            yt = y0 + 2 * (i + 1)
            bx(xi0, yt - 2, z0, xi0 + 3, yt, z1, vary("bois_clair", rng, 0.05), studs="top")
        xm = (L1 + R0) / 2
        poutre_pente(xm, y0 + 6 - 1.6, z1 + 0.3, 1.4, 0.6, bois_f, sens)        # limon
        poutre_pente(xm, y0 + 6 + 3.6, z1 + 0.3, 0.6, 0.6, bois, sens)          # main courante
        bx(xm - 0.3, y0 + 6 - 0.8, z1, xm + 0.3, y0 + 6 + 3.4, z1 + 0.6, bois)   # poteau milieu

    def palier(xx0, xx1, yt, zf, mur=True, cote_ext=None):
        z0, z1 = zf, zf + 5.6
        bx(xx0, yt - 1, z0, xx1, yt, z1, vary("bois", rng, 0.04), studs="top")
        if mur:
            a, bb = sorted((X(xx0 + 0.5), X(xx1 - 0.5)))
            b.wedge_under((a, yt - 4, z0), (bb, yt - 1, z1 - 0.6), bois_f, down="+z")
        for xp in (xx0, xx1 - 0.6):
            bx(xp, yt, z1 - 0.6, xp + 0.6, yt + 4.2, z1, bois_f)
        bx(xx0, yt + 3.6, z1 - 0.6, xx1, yt + 4.2, z1, bois)
        if cote_ext is not None:
            xe = xx1 - 0.6 if cote_ext > 0 else xx0
            bx(xe, yt, z0, xe + 0.6, yt + 4.2, z0 + 0.6, bois_f)
            bx(xe, yt + 3.6, z0, xe + 0.6, yt + 4.2, z1 - 0.6, bois)

    # dalle de départ en pierre
    bx(L0 - 1, 0, z_bas - 0.0, L1, y_bas, z_bas + 6, c("pave"), studs="top")
    y = y_bas
    k = 0
    n_bas = int(round((y_corniche - y_bas) / 12))
    for k in range(n_bas):
        sens = 1 if k % 2 == 0 else -1
        volee(y, sens, z_bas)
        y += 12
        if y < y_corniche - 0.1:
            if sens > 0:
                palier(R0, R1, y, z_bas, cote_ext=1)
            else:
                palier(L0, L1, y, z_bas, cote_ext=-1)
    # palier de la corniche (devant la roche, la corniche elle-même sert de sol derrière)
    last_right = (n_bas - 1) % 2 == 0
    if last_right:
        palier(R0, R1, y, z_bas, cote_ext=1)
    else:
        palier(L0, L1, y, z_bas, cote_ext=-1)
    # volées hautes, contre le panneau en retrait
    n_haut = int(round((y_haut - y_corniche) / 12))
    sens = -1 if last_right else 1
    for k in range(n_haut):
        volee(y, sens, z_haut)
        y += 12
        if k < n_haut - 1:
            if sens > 0:
                palier(R0, R1, y, z_haut, cote_ext=1)
            else:
                palier(L0, L1, y, z_haut, cote_ext=-1)
        sens = -sens
    # arrivée : palier en porte-à-faux au-dessus de la dernière volée, côté où elle aboutit
    arrivee_droite = sens < 0  # la dernière volée montait vers +x si sens est maintenant -1
    return arrivee_droite


# ---------------------------------------------------------------------------
# Asset principal
# ---------------------------------------------------------------------------
def rocher_hokage(b, variant: int = 0, passage: float = 68, hauteur_passage: float = 48, largeur: float = 480,
                  profondeur: float = 110, hauteur: float = 150) -> dict:
    """Rocher des Hokage : falaise stud, cinq visages, passage du couloir, escalier, belvédère, maisons.

    variant : 0/2 escalier à droite, 1/3 à gauche ; 2 et 3 changent le tirage des strates et de la végétation.
    """
    rng = np.random.default_rng(1871 + 31 * variant)
    s_esc = -1 if variant % 2 else 1
    P = passage / 2
    HP = hauteur_passage
    W = largeur / 2
    D = profondeur
    H = hauteur

    xj = P + 10                    # bord extérieur des murs du tunnel / début de la falaise (44)
    yc = HP + 2                    # sous-face du plafond du tunnel (50)
    yl0, yl1 = HP + 10, HP + 14    # corniche sous les visages (58 → 62)
    yp = min(HP + 66, H - 30)      # haut du panneau des visages (114)
    zr0 = -22                      # arrière de la « peau » avant
    zb0 = -D + 18                  # avant de la « peau » arrière
    z_pan = -6                     # front du panneau en retrait
    s1, s2, s3 = round(W * 0.625), round(W * 0.7333), round(W * 0.875)
    y_esc = yl1 + 36 - 1           # haut de roche sous le belvédère (97)

    fx = yl0 / 58.0
    bandes_bas = [(0, 7, "roche_fonce", 0), (7, 15, "roche", 0), (15, 24, "roche_claire", -0.5), (24, 31, "roche", 0),
                  (31, 40, "roche_fonce", 1.5), (40, 48, "roche", 0), (48, 58, "roche_claire", 0.5)]
    bandes_bas = [(round(a * fx, 1), round(bb * fx, 1), t, o) for a, bb, t, o in bandes_bas]
    tons_haut = ["roche_fonce", "roche", "roche_fonce", "roche", "roche_claire", "roche", "roche_fonce"]
    ep_haut = [10, 12, 10, 10, 10, 12, 10]

    def bandes_haut(top):
        out, y, i = [], yl1, 0
        while y < top - 0.1:
            y1 = min(top, y + ep_haut[i % len(ep_haut)])
            if top - y1 < 4:
                y1 = top
            out.append((y, y1, tons_haut[i % len(tons_haut)]))
            y, i = y1, i + 1
        return out

    xs_vis = [-2 * 62, -62, 0, 62, 2 * 62]
    pas = min(62.0, (s1 - 26) / 2)
    xs_vis = [k * pas for k in (-2, -1, 0, 1, 2)]

    def zone_visage(x0, x1):
        return any(x1 > xv - 24 and x0 < xv + 24 for xv in xs_vis)

    tops_r0 = []  # (x0, x1, top) pour placer la végétation et les rangs arrière

    # ------------------------------------------------------------------ peau avant
    with b.group("Falaise"):
        for side in (1, -1):
            sections = [("centre", xj, s1), ("contrefort", s1, s2), ("cote", s2, s3), ("bout", s3, W)]
            for kind, a0, a1 in sections:
                escalier_ici = kind == "cote" and side == s_esc
                cols = _colonnes(a0, a1, rng)
                # fissures : colonnes étroites en retrait (hors visages et escalier)
                if kind in ("centre", "bout", "contrefort") and not escalier_ici:
                    nc = []
                    for col in cols:
                        nc.append((col, False))
                        if rng.random() < 0.3 and col[1] < a1 - 4 and col[1] - col[0] > 9:
                            m = col[1] - 2
                            nc[-1] = ((col[0], m), False)
                            nc.append(((m, col[1]), True))
                    cols_f = nc
                else:
                    cols_f = [(cc, False) for cc in cols]
                for (c0, c1), fissure in cols_f:
                    x0, x1 = sorted((side * c0, side * c1))
                    if kind == "centre":
                        top = yp + float(rng.choice([0, 0, 2, 4]))
                        zf_haut = z_pan
                    elif kind == "contrefort":
                        top = yp + 8 + float(rng.choice([0, 2, 4, 6]))
                        zf_haut = 0
                    elif kind == "cote":
                        top = y_esc if escalier_ici else yp - 18 + float(rng.choice([-2, 0, 2, 4]))
                        zf_haut = z_pan
                    else:
                        top = HP + 24 + float(rng.choice([-4, 0, 2, 4, 6]))
                        zf_haut = -4
                    tops_r0.append((x0, x1, top, kind))
                    # fissure : plage de strates en creux
                    fk0 = int(rng.integers(1, 4))
                    fk1 = fk0 + int(rng.integers(2, 5))
                    for k, (y0, y1, ton, off) in enumerate(bandes_bas):
                        if escalier_ici:
                            zf = 0.0
                        else:
                            zf = off + float(rng.choice([-1, -0.5, 0, 0, 0.5, 1]))
                        col = vary(ton, rng, 0.035)
                        if fissure and fk0 <= k <= fk1:
                            zf, col = zf - 3, vary("roche_ombre", rng, 0.03)
                        b.box((x0, y0, zr0), (x1, y1, zf), col, studs="top")
                    # corniche
                    zc = 0.0 if escalier_ici else 2.0 + float(rng.choice([0, 0, 0.5]))
                    b.box((x0, yl0, zr0), (x1, yl1, zc), vary("roche_claire", rng, 0.03), studs="top")
                    # partie haute
                    vis = kind == "centre" and zone_visage(x0, x1)
                    for k, (y0, y1, ton) in enumerate(bandes_haut(top)):
                        if vis or escalier_ici:
                            zf = zf_haut
                        else:
                            zf = zf_haut + float(rng.choice([-1, -0.5, 0, 0.5, 1]))
                        col = vary(ton, rng, 0.035)
                        if fissure and not vis and k in (1, 2) and kind != "contrefort":
                            zf, col = zf - 3, vary("roche_ombre", rng, 0.03)
                        b.box((x0, y0, zr0), (x1, y1, zf), col, studs="top")

        # au-dessus du passage : corniche + panneau, posés sur la dalle du plafond
        for c0, c1 in _colonnes(-xj, xj, rng, (10, 12, 14, 16)):
            top = yp + float(rng.choice([0, 2, 4]))
            tops_r0.append((c0, c1, top, "centre"))
            b.box((c0, yl0, zr0), (c1, yl1, 2.0), vary("roche_claire", rng, 0.03), studs="top")
            for y0, y1, ton in bandes_haut(top):
                b.box((c0, y0, zr0), (c1, y1, z_pan), vary(ton, rng, 0.035), studs="top")

        # ------------------------------------------------------------------ rangs arrière (masse et sommet)
        def m_profil(x):
            return H - 70 * (abs(x) / W) ** 2

        def top_r0_max(x0, x1):
            return max(t for a, bb, t, _ in tops_r0 if bb > x0 and a < x1)

        core_cols = []
        for side in (1, -1):
            for c0, c1 in _colonnes(xj, W, rng, (16, 20, 24)):
                core_cols.append(tuple(sorted((side * c0, side * c1))))
        core_cols += [(-xj, -xj / 3), (-xj / 3, xj / 3), (xj / 3, xj)]
        core_cols.sort()
        tops_core = []
        for x0, x1 in core_cols:
            xm = (x0 + x1) / 2
            base = yl0 if abs(xm) < xj else 0
            t0 = top_r0_max(x0, x1)
            j = float(rng.choice([-2, 0, 2, 4]))
            r1 = max(m_profil(xm) - 14 + j, t0 + 6)
            r2 = min(H, max(m_profil(xm) + float(rng.choice([-4, -2, 0])), r1 + 6))
            if abs(xm) < xj:
                r2 = H
            r3 = max(r2 - 8 + float(rng.choice([-2, 0, 2])), r1 - 6)
            r4 = max(r3 - 10 + float(rng.choice([-2, 0, 2])), HP + 22)
            rows = [(-44, zr0, r1), (-70, -44, r2), (zb0, -70, r3)]
            for (za, zz, top), ton in zip(rows, ("roche", "roche_claire", "roche")):
                b.box((x0, base, za), (x1, top, zz), vary(ton, rng, 0.04), studs="top")
            tops_core.append((x0, x1, r1, r2, r3, r4))
            # peau arrière en strates (face -Z, vue depuis la zone suivante)
            yb = [0, 12, 26, 40, 52, 66, 80, 94, 108, 122, 136, 150]
            ys = [y for y in yb if y < r4 - 5] + [r4]
            for k in range(len(ys) - 1):
                y0, y1 = ys[k], ys[k + 1]
                if abs(xm) < xj and y1 <= yl0:
                    continue
                y0 = max(y0, base)
                if y1 - y0 < 1:
                    continue
                zf = -D - float(rng.choice([-1, -0.5, 0, 0.5, 1]))
                ton = ("roche_fonce", "roche", "roche_claire", "roche")[k % 4]
                b.box((x0, y0, zf), (x1, y1, zb0), vary(ton, rng, 0.035), studs="top")

    # ------------------------------------------------------------------ tunnel
    with b.group("Passage"):
        for side in (1, -1):
            x0, x1 = sorted((side * (P + 2), side * xj))
            b.box((x0, 0, -D), (x1, 6, 0), c("pave_fonce"))
            b.box((x0, 6, -D), (x1, yc, 0), c("pave"))
        b.box((-xj, yc, -D), (xj, yl0, 0), c("roche_fonce"))
        # arcs intérieurs (piédroits hors du gabarit 68 x 48) et lanternes murales
        for zr in np.linspace(-D, 0, 6)[1:-1]:
            for side in (1, -1):
                x0, x1 = sorted((side * P, side * (P + 2)))
                b.box((x0, 0, zr - 1.5), (x1, HP, zr + 1.5), PIERRE_F)
            b.box((-P - 2, HP, zr - 1.5), (P + 2, yc, zr + 1.5), PIERRE_F)
        for zl in (np.linspace(-D, 0, 6)[:-1] + D / 10):
            for side in (1, -1):
                x0, x1 = sorted((side * (P + 1.2), side * (P + 2)))
                b.box((x0, 26, zl - 1.2), (x1, 29.5, zl + 1.2), c("orange_lampion"), material="Neon", collide=False)
                b.box((x0, 29.5, zl - 1.5), (x1, 30.3, zl + 1.5), c("bois_fonce"), collide=False)

    # ------------------------------------------------------------------ portail avant
    with b.group("Portail"):
        for side in (1, -1):
            X = lambda x: side * x  # noqa: E731
            a, bb = sorted((X(P), X(P + 15)))
            b.box((a, 0, -2), (bb, 3, 5), c("pave_fonce"), studs="top")
            hc = (HP - 3) / 6
            for i in range(6):
                w = 13 if i % 2 == 0 else 10.5
                a, bb = sorted((X(P), X(P + w)))
                b.box((a, 3 + i * hc, -2), (bb, 3 + (i + 1) * hc, 3.5 if i % 2 == 0 else 3),
                      PIERRE if i % 2 == 0 else PIERRE_F)
            # linteau à gradins, en voussoirs
            for (xa, xb, y0, y1, z1, ton) in [(6, 17, HP, HP + 5, 4.5, PIERRE_F), (17, 28, HP, HP + 5, 4.5, PIERRE),
                                               (28, 39, HP, HP + 5, 4.5, PIERRE_F), (39, P + 16, HP, HP + 5, 4.5, PIERRE),
                                               (6, 20, HP + 5, yl0, 4.0, PIERRE), (20, 32, HP + 5, yl0, 4.0, PIERRE_F),
                                               (32, P + 7, HP + 5, yl0, 4.0, PIERRE)]:
                a, bb = sorted((X(xa), X(xb)))
                b.box((a, y0, -2), (bb, y1, z1), ton, studs="top")
            a, bb = sorted((X(P + 7), X(P + 16)))
            b.box((a, HP + 5, -2), (bb, HP + 6.5, 4.2), PIERRE_F, studs="top")
        # clé de voûte avec la spirale de la feuille de Konoha
        b.box((-6, HP - 1.5, -2), (6, yl0, 5.5), PIERRE, studs="top")
        spirale = ["..####..",
                   ".#....#.",
                   "#..##..#",
                   "#.#..#.#",
                   "#.#.#..#",
                   "#..#...#",
                   ".#....#.",
                   "..####.."]
        for j, row in enumerate(spirale):
            for i, ch in enumerate(row):
                if ch == "#":
                    b.box((-4 + i, yl0 - 1.5 - j - 1, 5.5), (-3 + i, yl0 - 1.5 - j, 5.9), c("roche_ombre"), collide=False)
        for side in (1, -1):
            _lanterne_pierre(b, side * (P + 21), 9)

        # portail arrière, plus simple
        for side in (1, -1):
            a, bb = sorted((side * P, side * (P + 12)))
            b.box((a, 0, -D - 2.5), (bb, HP, -D + 2), PIERRE_F)
        b.box((-P - 14, HP, -D - 3), (P + 14, HP + 6, -D + 2), PIERRE, studs="top")
        b.box((-5, HP - 1.5, -D - 3.5), (5, HP + 7, -D + 2), PIERRE_F, studs="top")

    # ------------------------------------------------------------------ visages
    with b.group("Visages"):
        for i, xv in enumerate(xs_vis):
            with b.group(f"Visage{i + 1}"):
                _visage(b, i + 1, xv, yl1, z_pan)

    # ------------------------------------------------------------------ escalier et belvédère
    with b.group("Escalier"):
        xa, xb = s2 + 2, s3 - 2
        _belvedere_et_escalier(b, s_esc, xa, xb, 2, yl1, y_esc + 1, 0.0, z_pan, rng)
        X = lambda x: s_esc * x  # noqa: E731
        bois, bois_f = c("bois"), c("bois_fonce")
        yd = y_esc + 1

        def bx(xx0, y0, zz0, xx1, y1, zz1, col, **kw):
            a, bb = sorted((X(xx0), X(xx1)))
            return b.box((a, y0, zz0), (bb, y1, zz1), col, **kw)

        # plancher du belvédère sur la roche + porte-à-faux au-dessus de l'arrivée
        bx(xa, y_esc, zr0 + 1, xb, yd, z_pan, vary("bois", rng, 0.04), studs="top")
        bx(xa, y_esc, z_pan, xa + 6, yd, z_pan + 5.6, vary("bois", rng, 0.04), studs="top")
        # garde-corps
        for (p0, p1) in [((xa + 6, z_pan), (xb, z_pan)), ((xa, z_pan + 5), (xa + 6, z_pan + 5))]:
            bx(p0[0], yd + 3.6, p0[1], p1[0], yd + 4.2, p0[1] + 0.6, bois)
            for xp in np.arange(p0[0], p1[0] + 0.01, 6):
                xp = min(xp, p1[0] - 0.6)
                bx(xp, yd, p0[1], xp + 0.6, yd + 4.2, p0[1] + 0.6, bois_f)
        bx(xb - 0.6, yd, zr0 + 1, xb, yd + 4.2, z_pan, bois_f)
        bx(xb - 0.6, yd + 3.6, zr0 + 1, xb, yd + 4.2, z_pan, bois)
        # pavillon à toit rouge
        px0, px1, pz0, pz1 = xa + 9, xb - 4, zr0 + 3, z_pan - 3
        for xp in (px0, px1 - 1):
            for zp in (pz0, pz1 - 1):
                bx(xp, yd, zp, xp + 1, yd + 7, zp + 1, c("rouge_fonce"))
        bx(px0 - 1, yd + 7, pz0 - 1, px1 + 1, yd + 8, pz1 + 1, c("poutre"))
        zm = (pz0 + pz1) / 2
        a, bb = sorted((X(px0 - 2.5), X(px1 + 2.5)))
        b.wedge((a, yd + 8, zm), (bb, yd + 11.5, pz1 + 2.5), c("toit_rouge"), down="+z", studs="top")
        b.wedge((a, yd + 8, pz0 - 2.5), (bb, yd + 11.5, zm), shade(c("toit_rouge"), 0.9), down="-z", studs="top")
        a, bb = sorted((X(px0 - 2.7), X(px1 + 2.7)))
        b.box((a, yd + 11.5, zm - 0.6), (bb, yd + 12.1, zm + 0.6), c("rouge_fonce"))

    # ------------------------------------------------------------------ maisons au pied
    with b.group("Maisons"):
        _maison(b, 94, 1, rng)
        _maison(b, 94, -1, rng, toit_plat=True)
        xm3 = (s2 + s3) / 2
        _maison(b, xm3, -s_esc, rng)

    # ------------------------------------------------------------------ végétation
    with b.group("Vegetation"):
        # arbres sur la terrasse au-dessus des visages (entre les têtes et derrière)
        for x0, x1, top, kind in tops_r0:
            if x1 - x0 < 8:
                continue
            xm = (x0 + x1) / 2
            if kind == "cote" and np.sign(xm) == s_esc:
                continue
            r = rng.random()
            if r < 0.35:
                _arbre(b, xm + rng.uniform(-1, 1), top, rng.uniform(-17, -12), rng, s=0.9)
            elif r < 0.75:
                _buisson(b, xm, top, rng.uniform(-18, -9), rng)
        for x0, x1, r1, r2, r3, r4 in tops_core:
            xm = (x0 + x1) / 2
            if rng.random() < 0.55:
                _arbre(b, xm + rng.uniform(-3, 3), r2, rng.uniform(-64, -50), rng, s=1.1)
            if rng.random() < 0.5:
                _buisson(b, xm + rng.uniform(-3, 3), r1, rng.uniform(-38, -28), rng, s=1.2)
            if rng.random() < 0.4:
                _arbre(b, xm + rng.uniform(-3, 3), r3, rng.uniform(-86, -76), rng)
        # touffes au pied de la falaise
        for side in (1, -1):
            for xb in np.linspace(xj + 12, W - 8, 7):
                if abs(xb - 94) < 16 or abs(xb - (s2 + s3) / 2) < 22:
                    continue
                _buisson(b, side * (xb + rng.uniform(-3, 3)), 0, rng.uniform(3.5, 5.5), rng, s=0.9)

    return {"emprise": (largeur, profondeur), "hauteur": hauteur, "passage": passage}
