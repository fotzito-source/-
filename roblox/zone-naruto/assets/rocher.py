"""Rocher des Hokage : la grande falaise de grès au bout de la zone Naruto (style stud).

Origine = centre de l'entrée du passage, au niveau du sol.
Exception à la règle « l'avant regarde -Z » : la falaise regarde +Z (vers les joueurs qui arrivent),
sa face avant suit à peu près z = 0 et la masse s'étend vers -Z sur `profondeur`.

Composition :
- en plan, la montagne est découpée en colonnes (largeurs 12 à 26) et en gradins vers l'arrière :
  peau avant (blocs de roche), gradin 1 (fond des visages), gradins 2 et 3 (sommet), gradin arrière ;
- la peau avant est faite de « masses » rocheuses (avancées et retraits, fissures) recoupées par des
  strates horizontales continues : la falaise se lit de loin comme du grès stratifié, pas comme un mur ;
- un passage voûté en gradins traverse la roche, avec un portail de pierre claire (arc à gradins,
  clé de voûte à spirale) et deux lanternes de pierre ;
- une corniche porte les cinq visages sculptés, au-dessus du passage ;
- les dessus sont couverts d'herbe stud, de buissons et d'arbres ; escalier de bois en zigzag
  sur un côté jusqu'à un belvédère ; petites maisons blanches à toit rouge au pied.
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, rot_z, shade
from palette import c, vary
from textures import mask_rects

# ---------------------------------------------------------------------------
# Couleurs locales (dérivées de la palette)
# ---------------------------------------------------------------------------
PIERRE = mix(c("creme"), c("roche_claire"), 0.30)      # pierre taillée claire du portail
PIERRE_F = mix(c("creme"), c("roche_claire"), 0.80)
PEAU = mix(c("roche_claire"), c("creme"), 0.50)        # visages : le grès le plus clair
PEAU_C = mix(c("roche_claire"), c("creme"), 0.80)      # arcades, nez, yeux (accrochent la lumière)
CREUX = mix(c("roche_ombre"), c("roche_fonce"), 0.15)  # orbites, bouche, rainures
CHEV = mix(c("roche"), c("roche_claire"), 0.15)        # cheveux
CHEV_C = mix(c("roche"), c("roche_claire"), 0.60)
BANDEAU = c("roche_fonce")
TONS = {"F": c("roche_fonce"), "R": c("roche"), "C": c("roche_claire"), "O": c("roche_ombre")}
FONCE = {"C": "R", "R": "F", "F": "O", "O": "O"}       # la bande des visages, un ton plus sombre
FISSURE = mix(c("roche_fonce"), c("roche_ombre"), 0.5)

# clés de couleur des bas-reliefs
K_PEAU, K_PEAU_C, K_CREUX, K_CHEV, K_CHEV_C, K_BANDEAU, K_PLAQUE = range(1, 8)
COULEURS_RELIEF = {K_PEAU: PEAU, K_PEAU_C: PEAU_C, K_CREUX: CREUX, K_CHEV: CHEV, K_CHEV_C: CHEV_C,
                   K_BANDEAU: BANDEAU, K_PLAQUE: PIERRE}


# ---------------------------------------------------------------------------
# Bas-relief sur grille d'un stud (visages)
# ---------------------------------------------------------------------------
class _Relief:
    """Grille (v vers le haut, u centré) : saillie et teinte par case d'un stud."""

    def __init__(self, demi: int = 23, haut: int = 52):
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

    def emit(self, b, xc, y0, zw, plus=1.0):
        """Un bloc par rectangle de cases de même (saillie, teinte), adossé au mur (z = zw)."""
        n = 0
        for d, k in sorted({(float(d), int(k)) for d, k in zip(self.d.ravel(), self.k.ravel()) if k}):
            mask = (self.d == d) & (self.k == k)
            for x, y, w, h in mask_rects(mask):
                u0 = x - self.demi
                b.box((xc + u0, y0 + y, zw), (xc + u0 + w, y0 + y + h, zw + d + plus), COULEURS_RELIEF[k], studs="top")
                n += 1
        return n


def _visage_base(g: _Relief, st: dict):
    """Tête commune : mâchoire à gradins, oreilles, pommettes, yeux, arcades, nez, bouche, menton."""
    # silhouette en deux paliers (bord à 4, centre à 5) : le visage « tourne » sous le soleil
    g.rows([(0, 2, 5), (2, 4, 7), (4, 7, 9), (7, 10, 11), (10, 14, 12), (14, 37, 13)], 4, K_PEAU)
    g.rows([(1, 3, 3), (3, 5, 5), (5, 8, 7), (8, 11, 9), (11, 15, 10), (15, 37, 11)], 5, K_PEAU)
    if st.get("oreilles", True):
        g.sym(13, 14, 16, 25, 3.5, K_PEAU)
        g.sym(14, 16, 15, 23, 3, K_CREUX)
    # pommettes
    g.sym(6, 12, 11, 17, 5.5, K_PEAU)
    # yeux : paupière supérieure en creux (trait sombre), œil clair, pupille, coin externe
    g.sym(3, 22, 11, 25, 3.5, K_CREUX)
    g.sym(4, 19, 10, 22, 4.5, K_PEAU_C)
    g.sym(10, 20, 11, 22, 3.5, K_CREUX)
    pu = st.get("pupille", 6)
    g.sym(pu, 19, pu + 2, 22, 4, K_CREUX)
    # arcades sourcilières (séparées par la racine du nez)
    if st.get("froncé"):
        g.poly([(2, 24), (12, 26), (12, 28), (2, 26)], 7, K_PEAU_C, mirror=True)
    else:
        g.sym(2, 25, 12, 27, 7, K_PEAU_C)
    g.rect(-2, 25, 2, 27, 6, K_PEAU)
    # nez
    g.rect(-1, 16, 1, 25, 7, K_PEAU_C)
    g.rect(-2, 13, 2, 16, 8, K_PEAU_C)
    g.sym(2, 13, 3, 15, 6.5, K_PEAU)
    # bouche
    mw = st.get("bouche", 5)
    g.rect(-mw + 1, 10, mw - 1, 12, 5.5, K_PEAU)
    g.rect(-mw, 9, mw, 10, 3.5, K_CREUX)
    g.rect(-mw + 2, 7, mw - 2, 9, 5.5, K_PEAU)
    # menton
    g.rect(-4, 1, 4, 5, 6, K_PEAU)


def _visage(b, kind: int, xc: float, y0: float, zw: float) -> int:
    """Cinq têtes stylisées (originales), chacune avec une silhouette de cheveux bien à elle."""
    g = _Relief()
    if kind == 1:  # cheveux lisses et longs, bandeau frontal à plaque
        g.rows([(26, 40, 17), (40, 43, 16), (43, 45, 14), (45, 47, 11), (47, 48, 6)], 4, K_CHEV)
        _visage_base(g, {"oreilles": False})
        g.sym(12, 3, 18, 31, 4.5, K_CHEV)          # mèches qui tombent sur les épaules
        g.sym(15, 5, 16, 29, 5, K_CHEV_C)
        g.sym(12, 3, 13, 26, 5, K_CHEV_C)
        g.rows([(35, 40, 14), (40, 43, 12), (43, 45, 9)], 5, K_CHEV_C)
        g.rect(-1, 36, 0, 47, 4, K_CREUX)          # raie
        g.rect(-15, 30, 15, 35, 5.5, K_BANDEAU)    # bandeau frontal
        g.rect(-7, 29, 7, 36, 6.5, K_PLAQUE)       # plaque
        for u, v in [(-3, 31), (-2, 31), (-1, 31), (0, 31), (1, 32), (1, 33), (0, 34), (-1, 34), (-2, 33)]:
            g.rect(u, v, u + 1, v + 1, 6, K_CREUX)  # petite spirale gravée
    elif kind == 2:  # cheveux courts en épis, sourcils froncés
        g.rows([(28, 40, 16), (40, 42, 14)], 4.5, K_CHEV)
        g.sym(12, 17, 16, 30, 4.5, K_CHEV)
        pics = [((-17, 36), (-10, 39), (-17, 44)), ((-12, 39), (-5, 39), (-9, 46)), ((-6, 39), (1, 39), (-3, 47)),
                ((-1, 39), (6, 39), (3, 47)), ((4, 39), (11, 39), (9, 46)), ((10, 39), (17, 36), (17, 44))]
        for i, p in enumerate(pics):
            g.poly(p, 4.5 if i % 2 else 5.5, K_CHEV if i % 2 else K_CHEV_C)
        g.poly([(-16, 26), (-16, 36), (-21, 32)], 4.5, K_CHEV, mirror=True)
        _visage_base(g, {"froncé": True, "bouche": 4})
        for p in [((-13, 37), (-6, 37), (-11, 31)), ((-7, 37), (1, 37), (-3, 30)), ((0, 37), (8, 37), (5, 31)),
                  ((6, 37), (13, 37), (11, 32))]:
            g.poly(p, 5.5, K_CHEV_C)
    elif kind == 3:  # capuche plate (sommet carré), visage âgé à barbiche
        g.rows([(0, 4, 14), (4, 10, 17), (10, 34, 19), (34, 40, 18), (40, 43, 16), (43, 45, 13)], 4, K_CHEV)
        _visage_base(g, {"bouche": 5, "oreilles": False})
        g.sym(13, 6, 15, 36, 5, K_CHEV_C)            # bord de la capuche autour du visage
        g.rows([(36, 39, 13), (39, 41, 11)], 5, K_CHEV_C)
        g.sym(16, 12, 17, 32, 4.5, K_CHEV_C)         # plis de la capuche
        g.rect(-8, 30, 8, 31, 4.5, K_CREUX)          # rides du front
        g.rect(-6, 33, 6, 34, 4.5, K_CREUX)
        g.sym(7, 8, 8, 13, 4.5, K_CREUX)             # plis du sourire
        g.rect(-3, -1, 3, 4, 6.5, K_CHEV)            # barbiche
        g.rect(-2, 0, 2, 2, 7, K_CHEV_C)
    elif kind == 4:  # grands épis balayés, longues mèches qui encadrent le visage
        g.rows([(26, 38, 17)], 4.5, K_CHEV)
        pics = [((-21, 33), (-10, 37), (-20, 46)), ((-13, 37), (-1, 37), (-6, 50)), ((-4, 37), (9, 37), (6, 52)),
                ((5, 36), (17, 36), (19, 48)), ((14, 26), (17, 37), (24, 32)), ((-16, 25), (-15, 36), (-23, 29))]
        for i, p in enumerate(pics):
            g.poly(p, 5.5 if i % 2 == 0 else 4.5, K_CHEV_C if i % 2 == 0 else K_CHEV)
        _visage_base(g, {"pupille": 5})
        g.poly([(10, 32), (15, 32), (14, 11)], 5.5, K_CHEV_C, mirror=True)
        for p in [((-13, 38), (-4, 38), (-10, 28)), ((-6, 38), (3, 38), (-1, 27)), ((1, 38), (11, 38), (8, 29))]:
            g.poly(p, 5.5, K_CHEV_C)
    else:  # cheveux longs et raides, frange droite
        g.rows([(34, 40, 19), (40, 43, 17), (43, 45, 14), (45, 46, 9)], 4.5, K_CHEV)
        g.sym(12, -1, 20, 36, 4.5, K_CHEV)
        _visage_base(g, {"bouche": 4, "oreilles": False})
        g.sym(11, -1, 13, 30, 4.5, K_CHEV)
        g.sym(16, 1, 17, 34, 5, K_CHEV_C)
        g.rect(-13, 29, 13, 37, 5.5, K_CHEV_C)      # frange
        for u in range(-12, 12, 4):
            g.rect(u, 28, u + 2, 29, 5.5, K_CHEV_C)
        g.rows([(37, 41, 13), (41, 43, 10)], 5.5, K_CHEV_C)
        g.rect(-1, 37, 1, 44, 4.5, K_CREUX)
        g.poly([(0, 26), (1, 27), (0, 28), (-1, 27)], 6, K_CREUX)  # losange au milieu du front
    return g.emit(b, xc, y0, zw)


# ---------------------------------------------------------------------------
# Outils de découpe
# ---------------------------------------------------------------------------
def _colonnes(x0: float, x1: float, rng, largeurs=(8, 10, 12, 14, 16)) -> list:
    xs = [x0]
    while xs[-1] < x1 - 1e-6:
        nx = xs[-1] + float(rng.choice(largeurs))
        if x1 - nx < min(largeurs) * 0.6:
            nx = x1
        xs.append(nx)
    return list(zip(xs[:-1], xs[1:]))


def _decoupe(x0, x1, rng, largeurs, forces=()):
    pts = sorted({x0, x1, *[f for f in forces if x0 + 1e-6 < f < x1 - 1e-6]})
    out = []
    for a, bb in zip(pts[:-1], pts[1:]):
        out += _colonnes(a, bb, rng, largeurs)
    return out


def _strates(yr: float, top: float) -> list:
    """Strates horizontales communes à toute la falaise : (y0, y1, ton)."""
    bas = [(5, "O"), (9, "R"), (7, "C"), (2, "F"), (9, "C"), (8, "R"), (2, "O"), (10, "C"), (8, "R")]  # 60 studs
    f = yr / 60.0
    out, y = [], 0.0
    for e, t in bas:
        out.append((round(y, 1), round(y + e * f, 1), t))
        y += e * f
    out[-1] = (out[-1][0], yr, out[-1][2])
    haut = [(4, "C"), (8, "R"), (2, "O"), (10, "C"), (8, "R"), (2, "F"), (10, "C"), (6, "R"), (2, "O"), (12, "C"),
            (8, "R"), (2, "F")]
    y, i = yr, 0
    while y < top:
        e, t = haut[i % len(haut)]
        out.append((y, y + e, t))
        y, i = y + e, i + 1
    return out


def _paroi(b, x0, x1, y0, y1, zr, strates, rng, *, saillies=(1.5, 2.5, 3.5, 4.5, 5.5, 6.5), larg=(10, 14, 18, 22, 26),
           fissures=0.22, plat=None, sombre=1.0, sens=1, touffes=0.0):
    """Peau rocheuse entre x0 et x1, de y0 à y1, adossée au plan z = zr (vers +Z si sens = 1, sinon vers -Z).

    Masses de roche (une saillie chacune) recoupées par les strates : les couleurs restent continues
    d'une masse à l'autre, les décrochements dessinent des fissures verticales et de petites corniches.
    """
    n = 0
    coupes = [s[0] for s in strates if y0 + 6 < s[0] < y1 - 6]
    for c0, c1 in _colonnes(x0, x1, rng, larg):
        cols = [(c0, c1, False)]
        if plat is None and c1 - c0 >= 12 and rng.random() < fissures:
            xf = c0 + float(rng.integers(3, int(c1 - c0) - 5))
            cols = [(c0, xf, False), (xf, xf + 3, True), (xf + 3, c1, False)]
        # 1 à 3 masses par colonne, coupées sur des limites de strates
        k = int(rng.integers(0, 3)) if coupes else 0
        ys = [y0, y1]
        if k:
            ys = sorted({y0, y1, *[float(v) for v in rng.choice(coupes, size=min(k, len(coupes)), replace=False)]})
        for a, bb, fiss in cols:
            prev = None
            for m0, m1 in zip(ys[:-1], ys[1:]):
                if plat is not None:
                    sa = plat
                elif fiss:
                    sa = max(0.5, min(saillies) - 0.25)
                else:
                    sa = float(rng.choice(saillies))
                    if prev is not None and rng.random() < 0.3:
                        sa = min(max(saillies), prev + 1)  # léger surplomb
                # touffe d'herbe sur la petite corniche laissée par la masse du dessous
                if prev is not None and sens > 0 and touffes and prev - sa >= 2 and bb - a >= 6 and rng.random() < touffes:
                    lw = float(rng.choice([3, 4, 5]))
                    ux = a + 0.25 + float(rng.uniform(0, bb - a - lw - 0.5))
                    b.box((ux, m0, zr + sa), (ux + lw, m0 + 0.6, zr + prev - 0.25), vary("herbe", rng, 0.05),
                          studs="top", collide=False)
                    if rng.random() < 0.5:
                        b.box((ux + 0.5, m0 + 0.6, zr + sa + 0.2), (ux + lw - 1, m0 + 1.4, zr + prev - 0.6),
                              vary("feuille", rng, 0.05), studs="top", collide=False)
                prev = sa
                for s0, s1, t in strates:
                    lo, hi = max(s0, m0), min(s1, m1)
                    if hi - lo < 0.05:
                        continue
                    col = shade(vary(FISSURE if fiss else TONS[t], rng, 0.025), sombre)
                    if sens > 0:
                        b.box((a, lo, zr), (bb, hi, zr + sa), col, studs="top")
                    else:
                        b.box((a, lo, zr - sa), (bb, hi, zr), col, studs="top")
                    n += 1
    return n


# ---------------------------------------------------------------------------
# Petits éléments
# ---------------------------------------------------------------------------
def _lanterne_pierre(b, x, z, s=1.0):
    """Lanterne de pierre (tōrō) : socle, fût, foyer lumineux, toit, pointe."""
    gr, grf = c("pave"), c("pave_fonce")
    S = lambda v: v * s  # noqa: E731
    b.box((x - S(2.5), 0, z - S(2.5)), (x + S(2.5), S(1.5), z + S(2.5)), grf, studs="top")
    b.box((x - S(0.9), S(1.5), z - S(0.9)), (x + S(0.9), S(6.5), z + S(0.9)), gr)
    b.box((x - S(2), S(6.5), z - S(2)), (x + S(2), S(7.5), z + S(2)), grf, studs="top")
    b.box((x - S(1.6), S(7.5), z - S(1.6)), (x + S(1.6), S(10.5), z + S(1.6)), gr)
    b.box((x - S(1.0), S(8.0), z - S(1.7)), (x + S(1.0), S(10.0), z + S(1.7)), c("orange_lampion"), material="Neon", collide=False)
    b.box((x - S(1.7), S(8.0), z - S(1.0)), (x + S(1.7), S(10.0), z + S(1.0)), c("orange_lampion"), material="Neon", collide=False)
    b.box((x - S(3), S(10.5), z - S(3)), (x + S(3), S(11.5), z + S(3)), grf, studs="top")
    b.box((x - S(1.8), S(11.5), z - S(1.8)), (x + S(1.8), S(12.5), z + S(1.8)), gr, studs="top")
    b.ball((x, S(13.2), z), S(0.8), gr)


def _lampion(b, x, y_haut, z, r=1.3, h=2.6):
    """Lampion rond suspendu : cordon, chapeau sombre, corps lumineux."""
    b.box((x - 0.15, y_haut - 1.2, z - 0.15), (x + 0.15, y_haut, z + 0.15), c("noir"), collide=False, shadow=False)
    b.cyl((x, y_haut - 1.2 - 0.25, z), r * 0.6, 0.5, c("noir"), axis="y", collide=False)
    b.cyl((x, y_haut - 1.5 - h / 2, z), r, h, c("orange_lampion"), axis="y", material="Neon", collide=False)
    b.cyl((x, y_haut - 1.5 - h - 0.2, z), r * 0.6, 0.4, c("noir"), axis="y", collide=False)


def _buisson(b, x, y, z, rng, s=1.0):
    w, d = round((3.5 + rng.uniform(0, 2)) * s * 4) / 4 + 0.05, round((3 + rng.uniform(0, 1.5)) * s * 4) / 4 + 0.05
    h = 2.5 * s + 0.05
    b.box((x - w / 2, y, z - d / 2), (x + w / 2, y + h, z + d / 2), vary("feuille_fonce", rng, 0.05), studs="top", collide=False)
    b.box((x - w / 2 + 0.8, y + h, z - d / 2 + 0.6), (x + w / 2 - 0.6, y + h + 1.3 * s, z + d / 2 - 0.5),
          vary("feuille", rng, 0.05), studs="top", collide=False)


def _arbre(b, x, y, z, rng, s=1.0):
    """Arbre stud : tronc carré, trois plateaux de feuillage décalés."""
    th = round((5 + rng.uniform(0, 3)) * s * 4) / 4 + 0.05
    b.box((x - 0.8 * s, y, z - 0.8 * s), (x + 0.8 * s, y + th, z + 0.8 * s), c("tronc"))
    w = round((9 + rng.uniform(0, 2)) * s * 4) / 4 + 0.05
    y1 = y + th
    b.box((x - w / 2, y1, z - w / 2), (x + w / 2, y1 + 3 * s, z + w / 2), vary("feuille_fonce", rng, 0.04), studs="top")
    dx, dz = rng.uniform(-1, 1, 2) * s
    w2 = w * 0.7
    b.box((x + dx - w2 / 2, y1 + 3 * s, z + dz - w2 / 2), (x + dx + w2 / 2, y1 + 5.5 * s, z + dz + w2 / 2),
          vary("feuille", rng, 0.04), studs="top", collide=False)
    w3 = w * 0.38
    b.box((x + dx * 0.5 - w3 / 2, y1 + 5.5 * s, z + dz * 0.5 - w3 / 2),
          (x + dx * 0.5 + w3 / 2, y1 + 7 * s, z + dz * 0.5 + w3 / 2), vary("feuille_claire", rng, 0.04), studs="top",
          collide=False)


def _maison(b, xc, rng, toit_plat=False):
    """Petite maison blanche à toit rouge sur un replat de roche, adossée à la falaise (avant = +Z)."""
    x0, x1 = xc - 12, xc + 12
    # replat de roche + marches
    b.box((x0, 0, -1), (x1, 4, 16), vary("roche", rng, 0.04), studs="top")
    b.box((x0 + 0.75, 4, -1), (x1 - 0.75, 4.6, 15.5), vary("roche_claire", rng, 0.03), studs="top")
    b.box((xc - 3.2, 0, 16), (xc + 3.2, 1.4, 19), c("pave"), studs="top")
    b.box((xc - 3.2, 1.4, 16), (xc + 3.2, 2.8, 17.6), c("pave"), studs="top")
    y0 = 4.6
    hx0, hx1 = xc - 8, xc + 8
    z0, z1 = 2.5, 12.5
    b.box((hx0, y0, z0), (hx1, y0 + 0.8, z1), c("bois_fonce"))
    b.box((hx0 + 0.2, y0 + 0.8, z0 + 0.2), (hx1 - 0.2, y0 + 8.5, z1 - 0.2), vary("enduit", rng, 0.02))
    yb = y0 + 8.5
    b.box((hx0 - 0.2, yb, z0 - 0.2), (hx1 + 0.2, yb + 1, z1 + 0.2), c("poutre"))
    # façade : porte, noren, fenêtres, poteaux d'angle
    b.box((xc - 1.6, y0 + 0.8, z1 - 0.2), (xc + 1.6, y0 + 6, z1 + 0.15), c("bois"))
    b.box((xc - 2.4, y0 + 4.6, z1 + 0.15), (xc + 2.4, y0 + 7.4, z1 + 0.6), c("noren_bleu"), collide=False)
    for dx in (-5.5, 5.5):
        b.box((xc + dx - 2, y0 + 3.2, z1 - 0.2), (xc + dx + 2, y0 + 6.4, z1 + 0.1), c("fenetre"))
        b.box((xc + dx - 2.3, y0 + 2.8, z1 - 0.2), (xc + dx + 2.3, y0 + 3.2, z1 + 0.5), c("bois_clair"))
    for x in (hx0, hx1 - 0.8):
        b.box((x - 0.1, y0 + 0.8, z1 - 0.7), (x + 0.9, yb, z1 + 0.25), c("poutre"))
    yt = yb + 1
    if not toit_plat:
        zm = (z0 + z1) / 2
        b.wedge((hx0 - 1.6, yt, zm), (hx1 + 1.6, yt + 4.5, z1 + 1.8), c("toit_rouge"), down="+z", studs="top")
        b.wedge((hx0 - 1.6, yt, z0 - 1.6), (hx1 + 1.6, yt + 4.5, zm), shade(c("toit_rouge"), 0.9), down="-z", studs="top")
        b.box((hx0 - 1.8, yt + 4.5, zm - 0.6), (hx1 + 1.8, yt + 5.1, zm + 0.6), c("rouge_fonce"), studs="top")
        for x in (hx0 + 0.2, hx1 - 0.4):
            b.wedge((x, yt, zm), (x + 0.2, yt + 4.2, z1 - 0.2), vary("enduit", rng, 0.02), down="+z")
            b.wedge((x, yt, z0 + 0.2), (x + 0.2, yt + 4.2, zm), vary("enduit", rng, 0.02), down="-z")
    else:
        # toit-terrasse : acrotère, citerne sur pieds, petit auvent rouge au-dessus de la porte
        b.box((hx0 - 0.6, yt, z0 - 0.6), (hx1 + 0.6, yt + 0.8, z1 + 0.6), c("toit_rouge"), studs="top")
        b.box((hx0 - 0.6, yt + 0.8, z1 - 0.2), (hx1 + 0.6, yt + 1.8, z1 + 0.6), c("rouge_fonce"))
        cx, cz = xc + 3.5, (z0 + z1) / 2
        for dx in (-1.6, 1.6):
            for dz in (-1.6, 1.6):
                b.box((cx + dx - 0.25, yt + 0.8, cz + dz - 0.25), (cx + dx + 0.25, yt + 2.8, cz + dz + 0.25), c("metal_fonce"))
        b.cyl((cx, yt + 5.3, cz), 2.6, 5, c("citerne"), axis="y")
        b.cyl((cx, yt + 8.0, cz), 1.6, 0.6, c("metal"), axis="y")
        b.wedge((xc - 3.4, y0 + 7.4, z1 + 0.6), (xc + 3.4, y0 + 8.4, z1 + 3.0), c("toit_rouge"), down="+z", studs="top")


def _escalier(b, s, xa, xb, y_haut, rng):
    """Escalier de bois en zigzag contre la falaise (front z = 0), de x = xa à xb (miroir si s = -1).

    Volées de 6 marches (12 studs de montée sur 18), en deux couloirs : les volées paires contre la roche
    (z 0 → 5), les impaires devant (z 5.6 → 10.6), ce qui garde la hauteur libre. Paliers aux deux bouts.
    """
    X = lambda x: s * x  # noqa: E731
    bois, bois_f = c("bois_clair"), c("bois")
    L0, L1, R0, R1 = xa, xa + 6, xb - 6, xb
    run = R0 - L1
    nm = 6
    rise = 12
    ang = math.degrees(math.atan2(rise, run))
    longueur = math.hypot(run, rise)
    ZE = 11.2  # bord extérieur

    def bx(xx0, y0, zz0, xx1, y1, zz1, col, **kw):
        a, bb = sorted((X(xx0), X(xx1)))
        return b.box((a, y0, zz0), (bb, y1, zz1), col, **kw)

    def pente(xm, ym, zm, ep, larg, col, monte_vers_x):
        a = ang if (monte_vers_x * s) > 0 else -ang
        return b.part("block", (longueur + 0.4, ep, larg), (X(xm), ym, zm), rot_z(a), col)

    nf = int(round(y_haut / rise))
    for k in range(nf):
        y0 = rise * k
        vers_r = k % 2 == 0
        za, zb = (0.0, 5.0) if vers_r else (5.6, 10.6)
        for i in range(nm):
            xi0 = L1 + 3 * i if vers_r else R0 - 3 * (i + 1)
            bx(xi0, y0 + 2 * i, za, xi0 + 3, y0 + 2 * (i + 1), zb, vary("bois_clair", rng, 0.06), studs="top")
        xm = (L1 + R0) / 2
        zr = zb + 0.3
        pente(xm, y0 + rise / 2 - 0.9, zr, 1.2, 0.6, bois_f, 1 if vers_r else -1)    # limon
        pente(xm, y0 + rise / 2 + 3.6, zr, 0.5, 0.5, bois, 1 if vers_r else -1)      # main courante
        bx(xm - 0.3, y0 + rise / 2 - 0.3, zb, xm + 0.3, y0 + rise / 2 + 3.6, zb + 0.6, bois_f)  # poteau
    # paliers (un à chaque virage, plus le départ)
    for k in range(nf + 1):
        y = rise * k
        droite = k % 2 == 1
        p0, p1 = (R0, R1) if droite else (L0, L1)
        if k == 0:
            bx(L0 - 2, 0, 0, L1, 1, ZE, c("pave"), studs="top")
            continue
        bx(p0, y - 1, 0, p1, y, ZE, vary("bois", rng, 0.04), studs="top")
        # console sous le palier
        a, bb = sorted((X(p0 + 0.5), X(p1 - 0.5)))
        b.wedge_under((a, y - 4, 0), (bb, y - 1, ZE - 1), bois_f, down="+z")
        # garde-corps côté vide : lisse en bout de palier et en façade, poteau intermédiaire
        xe = p1 - 0.6 if droite else p0
        bx(xe, y + 3.6, 0, xe + 0.6, y + 4.2, ZE - 0.6, bois)
        bx(xe, y, 0, xe + 0.6, y + 3.6, 0.6, bois_f)
        bx(p0, y + 3.6, ZE - 0.6, p1, y + 4.2, ZE, bois)
    return nf % 2 == 1  # True : l'escalier arrive côté extérieur (R)


# ---------------------------------------------------------------------------
# Asset principal
# ---------------------------------------------------------------------------
def rocher_hokage(b, variant: int = 0, passage: float = 68, hauteur_passage: float = 48, largeur: float = 480,
                  profondeur: float = 110, hauteur: float = 150) -> dict:
    """Rocher des Hokage : falaise stud, cinq visages, passage du couloir, escalier, belvédère, maisons.

    variant : 0/2 escalier à droite (+x), 1/3 à gauche ; 2 et 3 changent le tirage des roches et de la végétation.
    """
    rng = np.random.default_rng(1871 + 31 * variant)
    s_esc = -1 if variant % 2 else 1
    P = passage / 2
    HP = hauteur_passage
    W = largeur / 2
    D = profondeur
    H = hauteur

    # -- repères ---------------------------------------------------------------
    XT = P + 10                     # bord extérieur des murs du passage
    XP = P + 16                     # bord extérieur du portail
    YR = HP + 14                    # dessus de la voûte = dessous de la corniche (62)
    YL = HP + 18                    # dessus de la corniche = bas des visages (66)
    YT1 = min(YL + 56, H - 16)      # haut du gradin des visages (122)
    # voûte en gradins (demi-largeur extérieure, dessous) : l'arc monte de HP à HP + 11
    VOUTE = [(P, P - 8, HP + 3), (P - 8, P - 18, HP + 6), (P - 18, P - 28, HP + 9), (P - 28, 0, HP + 11)]
    pas = 62.0                      # écart entre visages
    xs_vis = [k * pas for k in (-2, -1, 0, 1, 2)]
    XV = 2 * pas + 26               # fin de la bande des visages (150)
    ZF = -3.0                       # front du gradin 1 (fond des visages)
    Z1 = -min(14.0, 0.25 * D)
    Z2 = -min(28.0, 0.5 * D)
    ZB = -D + min(14.0, 0.25 * D)
    xs0 = XV + 4                    # escalier : x de xs0 à xs1
    xs1 = min(xs0 + 30, W - 6)
    y_esc = 12 * int(round(min(YL + 44, YT1 - 8) / 12))
    strates = _strates(YR, H + 20)

    # -- colonnes --------------------------------------------------------------
    cols = [(a, bb, "tunnel") for a, bb in _colonnes(-XT, XT, rng, (14, 16, 20))]
    for side in (1, -1):
        forces = [XP, XV] + ([xs0, xs1] if side == s_esc else [])
        for a, bb in _decoupe(XT, W, rng, (14, 18, 22, 26), forces):
            if bb <= XP + 1e-6:
                kind = "portail"
            elif bb <= XV + 1e-6:
                kind = "visages"
            elif side == s_esc and a >= xs0 - 1e-6 and bb <= xs1 + 1e-6:
                kind = "escalier"
            else:
                kind = "cote"
            x0, x1 = sorted((side * a, side * bb))
            cols.append((x0, x1, kind))
    cols.sort()

    tops = []
    for x0, x1, kind in cols:
        xm = abs((x0 + x1) / 2)
        f = (xm / W) ** 2
        if kind in ("tunnel", "portail", "visages"):
            t1 = YT1 + float(rng.choice([0, 2, 4, 6]))
        elif kind == "escalier":
            t1 = float(y_esc - 1)
        else:
            u = (xm - XV) / max(1.0, W - XV)
            t1 = YT1 - 10 - u * (YT1 - 10 - (YR + 18)) + float(rng.choice([-4, -2, 0, 2]))
            t1 = 2 * round(t1 / 2)
        t2 = YT1 + 16 - 54 * f + float(rng.choice([-2, 0, 2]))
        t2 = 2 * round(t2 / 2) if t2 >= t1 + 5 else t1
        t3 = H - 72 * f + float(rng.choice([-4, -2, 0]))
        t3 = 2 * round(t3 / 2) if t3 >= t2 + 5 else t2
        if kind == "escalier":
            t2 = t3 = t1
        tb = max(YR + 22, min(t3 - 30, YT1 - 10))
        tb = 2 * round(tb / 2) if tb < t3 - 4 else t3
        tops.append((t1, t2, t3, tb))

    herbe = []  # (x0, x1, y, z0, z1, gradin) : dessus herbeux, pour la végétation
    x3 = -s_esc * (min(XV + 24, W - 14) + 0.5)  # troisième maison, du côté sans escalier

    def bandes(x0, x1, ya, yb, za, zb, carte=None, sombre=1.0):
        for s0, s1, t in strates:
            lo, hi = max(s0, ya), min(s1, yb)
            if hi - lo > 0.05:
                col = TONS[carte[t] if carte else t]
                b.box((x0, lo, za), (x1, hi, zb), shade(vary(col, rng, 0.025), sombre), studs="top")

    with b.group("Falaise"):
        for (x0, x1, kind), (t1, t2, t3, tb) in zip(cols, tops):
            base = YR if kind == "tunnel" else 0.0
            # gradin 1 : noyau + bandes visibles au-dessus de la corniche (bande des visages)
            if kind in ("tunnel", "portail", "visages"):
                b.box((x0, base, Z1), (x1, YL, ZF), c("roche_fonce"))
                bandes(x0, x1, YL, t1 - 3, Z1, ZF, FONCE, 0.95)
                # rebord supérieur en léger surplomb
                b.box((x0, t1 - 3, Z1), (x1, t1, ZF + 1.5 + float(rng.choice([0, 0.5]))),
                      vary("roche_claire", rng, 0.03), studs="top")
                herbe.append((x0, x1, t1, Z1, ZF + 1.5, 1))
            else:
                b.box((x0, 0, Z1), (x1, t1, ZF), vary("roche", rng, 0.03), studs="top")
                herbe.append((x0, x1, t1, Z1, ZF, 1))
            # gradins 2 et 3 (strates sur la partie visible), gradin arrière
            for (ta, tz, za, zb, g) in ((t1, t2, Z2, Z1, 2), (t2, t3, ZB, Z2, 3)):
                if tz > ta:
                    b.box((x0, base, za), (x1, ta, zb), vary("roche", rng, 0.04))
                    bandes(x0, x1, ta, tz, za, zb)
                else:
                    b.box((x0, base, za), (x1, tz, zb), vary("roche", rng, 0.04), studs="top")
                herbe.append((x0, x1, tz, za, zb, g))
            b.box((x0, base, -D + 4), (x1, tb, ZB), vary("roche", rng, 0.04), studs="top")
            herbe.append((x0, x1, tb, -D + 4, ZB, 4))

            # peau avant
            if kind == "visages":
                _paroi(b, x0, x1, 0, YR, ZF, strates, rng, touffes=0.6)
            elif kind == "portail":
                _paroi(b, x0, x1, 0, YR, ZF, strates, rng, plat=-ZF)
            elif kind == "escalier":
                _paroi(b, x0, x1, 0, t1, ZF, strates, rng, plat=-ZF)
            elif kind == "cote":
                _paroi(b, x0, x1, 0, t1, ZF, strates, rng, touffes=0.6)
            # peau arrière (vue depuis la zone suivante)
            y_dos = YR if kind == "tunnel" else 0.0
            _paroi(b, x0, x1, y_dos, tb, -D + 4, strates, rng, saillies=(2, 2.5, 3, 3.5), larg=(16, 22, 28),
                   fissures=0.12, sens=-1)

        # nervures de roche entre les têtes : elles cadrent les visages et dentellent la crête
        def t1_en(x):
            for (a, bb, _), tt in zip(cols, tops):
                if a <= x <= bb:
                    return tt[0]
            return YT1

        for xr in [k * pas / 2 for k in (-3, -1, 1, 3)] + [-(2 * pas + 23), 2 * pas + 23]:
            w = float(rng.choice([5.5, 6.5, 7.5])) if abs(xr) < 2 * pas else 3.5
            pr = float(rng.choice([2.75, 3.25, 3.75]))
            tt = t1_en(xr)
            extra = float(rng.choice([0, 3.5, 5.5, 7.5]))
            r0, r1 = xr - w / 2, xr + w / 2
            bandes(r0, r1, YL, tt - 3, ZF, ZF + pr, FONCE, 0.97)
            b.box((r0, tt - 3, ZF - (6 if extra else 0)), (r1, tt + extra, ZF + pr), vary("roche_claire", rng, 0.03),
                  studs="top")
            if extra >= 5:
                herbe.append((r0, r1, tt + extra, ZF - 6, ZF + pr, 5))

        # corniche sous les visages
        for a, bb in _colonnes(-XV, XV, rng, (16, 20, 24, 28)):
            b.box((a, YR, ZF), (bb, YL, 2.5 + float(rng.choice([0, 0, 0.5]))), vary("roche_claire", rng, 0.03),
                  studs="top")

        # herbe stud sur tous les dessus
        for x0, x1, y, za, zb, g in herbe:
            if g in (1, 2) and xs0 - 1e-6 < abs((x0 + x1) / 2) < xs1 and np.sign((x0 + x1) / 2) == s_esc:
                continue  # le belvédère a son plancher
            if g == 5:
                continue  # sommet des nervures : un buisson suffit
            b.box((x0, y, za), (x1, y + 1, zb), vary("herbe", rng, 0.04), studs="top")

        # éboulis au pied de la falaise (socle en gradins), touffes posées dessus ou devant
        pieds = []
        evite = [(XP + 32.5, 13), (-(XP + 32.5), 13), (x3, 13), (s_esc * (xs0 + xs1) / 2, (xs1 - xs0) / 2 + 3)]
        for side in (1, -1):
            u = XP + 3.25
            while u < W - 6:
                w = min(float(rng.choice([6, 8, 10, 12])), W - 0.5 - u)
                xc = side * (u + w / 2)
                if not any(abs(xc - xe) < r + w / 2 for xe, r in evite):
                    h = float(rng.choice([2, 3, 4]))
                    d = float(rng.choice([4, 5, 6]))
                    a, bb = sorted((side * u, side * (u + w)))
                    b.box((a, 0, ZF + 0.5), (bb, h, 0.5 + d), vary("roche", rng, 0.04), studs="top")
                    r = rng.random()
                    if r < 0.35:
                        b.box((a + 1, h, ZF + 0.5), (bb - 1, h + 2, d - 1.25), vary("roche_fonce", rng, 0.04), studs="top")
                    elif r < 0.75:
                        pieds.append((xc, h, d - 1.5))
                    if w >= 8 and rng.random() < 0.5:
                        pieds.append((xc + side * (w / 2 + 2.5), 0, d + 2.5))
                u += w + float(rng.choice([0, 0, 2, 4]))

    # ------------------------------------------------------------------ passage
    with b.group("Passage"):
        z_dos = -D + 4
        for side in (1, -1):
            X = lambda x: side * x  # noqa: E731
            a, bb = sorted((X(P), X(XT)))
            b.box((a, 0, z_dos), (bb, 3, 0), c("pave_fonce"))
            # panneaux de pierre en alternance le long du mur
            zz = z_dos
            i = 0
            while zz < -0.01:
                zn = min(0.0, zz + float(rng.choice([12, 14, 16])))
                if -zn < 6:
                    zn = 0.0
                b.box((a, 3, zz), (bb, HP + 3, zn), PIERRE_F if i % 2 else vary("pave", rng, 0.02))
                zz, i = zn, i + 1
            b.box((a, HP + 3, z_dos), (bb, YR, 0), PIERRE)
        # voûte en gradins (toute la longueur)
        for i, (u1, u0, yb) in enumerate(VOUTE):
            for side in ((1, -1) if u0 > 0 else (1,)):
                a, bb = sorted((side * u0, side * u1)) if u0 > 0 else (-u1, u1)
                b.box((a, yb, z_dos), (bb, YR, 0), PIERRE if i % 2 == 0 else PIERRE_F)
        # lampions ronds suspendus à la voûte
        nl = max(2, int(round((D - 4) / 22)))
        for zl in np.linspace(z_dos + (D - 4) / (2 * nl), -(D - 4) / (2 * nl), nl):
            for side in (1, -1):
                _lampion(b, side * (P - 13), HP + 6, float(zl))

    # ------------------------------------------------------------------ portail avant
    with b.group("Portail"):
        for side in (1, -1):
            X = lambda x: side * x  # noqa: E731

            def bx(u0, y0, z0, u1, y1, z1, col, **kw):
                a, bb = sorted((X(u0), X(u1)))
                return b.box((a, y0, z0), (bb, y1, z1), col, **kw)

            bx(P, 0, 0, XP + 1.5, 4, 6.5, c("pave_fonce"), studs="top")                # socle
            hc = (HP + 3 - 4) / 4
            for i in range(4):                                                      # piédroit en harpe
                w = XP - P if i % 2 == 0 else XP - P - 3
                bx(P, 4 + i * hc, 0, P + w, 4 + (i + 1) * hc, 5 if i % 2 == 0 else 4.5,
                   PIERRE if i % 2 == 0 else PIERRE_F, studs="top")
            # chapiteau sur le piédroit
            bx(P - 1.5, HP + 3, 0, XP + 2, HP + 5, 6, PIERRE_F, studs="top")
            # arc à gradins : voussoirs qui suivent la voûte, de plus en plus saillants vers la clé
            bx(P - 8, HP + 5, 0, XP + 1.5, HP + 9, 5, PIERRE, studs="top")
            bx(P - 8, HP + 3, 0, P - 1.5, HP + 5, 5, PIERRE, studs="top")
            bx(P - 18, HP + 6, 0, P - 8, HP + 10.5, 5.5, PIERRE_F, studs="top")
            bx(P - 28, HP + 9, 0, P - 18, YR, 6, PIERRE, studs="top")
            # remplissage au-dessus des voussoirs (en retrait)
            bx(P - 8, HP + 9, 0, XP + 1.5, YR, 3.75, PIERRE_F, studs="top")
            bx(P - 18, HP + 10.5, 0, P - 8, YR, 3.75, PIERRE_F, studs="top")
        # clé de voûte avec la spirale de la feuille de Konoha
        b.box((-(P - 27), HP + 10, 0), (P - 27, YL + 0.5, 7), PIERRE, studs="top")
        spirale = ["..####..",
                   ".#....#.",
                   "#..##..#",
                   "#.#..#.#",
                   "#.#.##.#",
                   "#.#....#",
                   "##.####.",
                   "#......."]
        m = np.array([[ch == "#" for ch in row] for row in spirale])
        for i, j, w, h in mask_rects(m):
            yt = YL - 1.5 - j
            b.box((-4 + i, yt - h, 7), (-4 + i + w, yt, 7.4), c("roche_ombre"), collide=False)
        for side in (1, -1):
            _lanterne_pierre(b, side * (XP + 8), 9, s=1.25)
        # lampions ronds sous l'arc
        for side in (1, -1):
            _lampion(b, side * (P - 13), HP + 6, 2.5)

        # portail arrière, plus simple
        for side in (1, -1):
            X = lambda x: side * x  # noqa: E731

            def bx(u0, y0, z0, u1, y1, z1, col, **kw):
                a, bb = sorted((X(u0), X(u1)))
                return b.box((a, y0, z0), (bb, y1, z1), col, **kw)

            bx(P, 0, -D, XP, HP + 3, -D + 4, PIERRE_F)
            bx(P - 8, HP + 3, -D, XP, HP + 11, -D + 4, PIERRE, studs="top")
            bx(P - 18, HP + 6, -D + 0.25, P - 8, HP + 11, -D + 4, PIERRE_F)
            bx(P - 28, HP + 9, -D + 0.25, P - 18, HP + 11, -D + 4, PIERRE)
        b.box((-XP, HP + 11, -D + 0.25), (XP, YR, -D + 4), PIERRE, studs="top")
        b.box((-5, HP + 10, -D), (5, YR + 2, -D + 4), PIERRE_F, studs="top")

    # ------------------------------------------------------------------ visages
    with b.group("Visages"):
        for i, xv in enumerate(xs_vis):
            with b.group(f"Visage{i + 1}"):
                _visage(b, i + 1, xv, YL, ZF)

    # ------------------------------------------------------------------ escalier et belvédère
    with b.group("Escalier"):
        cote_r = _escalier(b, s_esc, xs0, xs1, y_esc, rng)
        X = lambda x: s_esc * x  # noqa: E731
        bois, bois_f = c("bois"), c("bois_fonce")
        yd = y_esc

        def bx(u0, y0, z0, u1, y1, z1, col, **kw):
            a, bb = sorted((X(u0), X(u1)))
            return b.box((a, y0, z0), (bb, y1, z1), col, **kw)

        # plancher du belvédère sur le sommet de la colonne
        bx(xs0, yd - 1, Z2, xs1, yd, 0, vary("bois", rng, 0.04), studs="top")
        # garde-corps : avant (sauf l'arrivée), côtés
        ya = yd
        arr0, arr1 = (xs1 - 6, xs1) if cote_r else (xs0, xs0 + 6)
        for u0, u1 in ((xs0, arr0), (arr1, xs1)):
            if u1 - u0 > 1:
                bx(u0, ya + 3.4, -0.6, u1, ya + 4, 0, bois)
                for up in np.arange(u0, u1 - 0.5, 5):
                    bx(up, ya, -0.6, up + 0.6, ya + 3.4, 0, bois_f)
        for up in (xs0, xs1 - 0.6):
            bx(up, ya + 3.4, Z2, up + 0.6, ya + 4, -0.6, bois)
            bx(up, ya, Z2, up + 0.6, ya + 3.4, Z2 + 0.6, bois_f)
        # pavillon à toit rouge
        px0, px1, pz0, pz1 = xs0 + 7, xs1 - 7, Z2 + 5, -5
        for xp in (px0, px1 - 1):
            for zp in (pz0, pz1 - 1):
                bx(xp, ya, zp, xp + 1, ya + 7, zp + 1, c("rouge_fonce"))
        bx(px0 - 1, ya + 7, pz0 - 1, px1 + 1, ya + 8, pz1 + 1, c("poutre"))
        zm = (pz0 + pz1) / 2
        a, bb = sorted((X(px0 - 2.5), X(px1 + 2.5)))
        b.wedge((a, ya + 8, zm), (bb, ya + 11.5, pz1 + 2.5), c("toit_rouge"), down="+z", studs="top")
        b.wedge((a, ya + 8, pz0 - 2.5), (bb, ya + 11.5, zm), shade(c("toit_rouge"), 0.9), down="-z", studs="top")
        a, bb = sorted((X(px0 - 2.7), X(px1 + 2.7)))
        b.box((a, ya + 11.5, zm - 0.6), (bb, ya + 12.1, zm + 0.6), c("rouge_fonce"))
        _lampion(b, X((px0 + px1) / 2), ya + 7, pz1 - 0.5)

    # ------------------------------------------------------------------ maisons au pied
    with b.group("Maisons"):
        xm = XP + 32.5
        _maison(b, xm, rng)
        _maison(b, -xm, rng, toit_plat=True)
        _maison(b, x3, rng)

    # ------------------------------------------------------------------ végétation
    with b.group("Vegetation"):
        for x0, x1, y, za, zb, g in herbe:
            xm = (x0 + x1) / 2
            if np.sign(xm) == s_esc and xs0 - 2 < abs(xm) < xs1 + 2:
                continue
            w = x1 - x0
            if g == 1:
                if rng.random() < 0.7:
                    _buisson(b, xm + rng.uniform(-w / 4, w / 4), y + 1, (za + zb) / 2 + rng.uniform(-1, 1), rng, s=1.1)
            elif g == 5:
                _buisson(b, xm, y, (za + zb) / 2, rng, s=0.8)
            elif g in (2, 3):
                if rng.random() < 0.6:
                    _arbre(b, xm + rng.uniform(-w / 5, w / 5), y + 1, (za + zb) / 2, rng, s=1.0 + 0.15 * (g == 3))
                elif rng.random() < 0.6:
                    _buisson(b, xm, y + 1, (za + zb) / 2, rng, s=1.3)
            else:
                if rng.random() < 0.4:
                    _buisson(b, xm, y + 1, (za + zb) / 2, rng, s=1.2)
        # touffes au pied de la falaise
        for x, y, z in pieds:
            if abs(x) < W - 4 and not any(abs(x - xe) < r + 3 for xe, r in evite):
                _buisson(b, x, y, z, rng, s=0.9)

    return {"emprise": (largeur, profondeur), "hauteur": hauteur, "passage": passage, "debord_avant": 19}
