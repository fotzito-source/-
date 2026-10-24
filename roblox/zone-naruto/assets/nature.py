"""Végétation de Konoha en style stud : arbres du village, cerisiers, géants de la forêt, buissons,
rochers, parterres de fleurs et touffes d'herbe.

Principes :
- feuillages en blocs empilés, studs sur les dessus ; quatre tons par masse : dessous très sombre (le volume se lit
  d'en bas), corps, étage plus clair, sommet ensoleillé ; des lobes latéraux cassent les silhouettes carrées ;
- chaque variante a une silhouette franche (rond, élancé, parasol, pin en plateaux…), lisible de loin ;
- troncs, branches et racines collisionnent ; feuillages, fleurs et petits détails non (`collide=False`) ;
- cotes de conception données pour `taille = 1` sur la grille du demi-stud, puis multipliées par `taille`
  sans réarrondi : deux faces de même orientation qui se chevauchent restent toujours séparées (pas de z-fighting),
  quelle que soit la taille demandée par la mise en page.
"""

from __future__ import annotations

import math

import numpy as np

from kit import hexrgb, mix, shade
from palette import c, vary

# Couleurs locales (complètent palette.py)
OMBRE = hexrgb("#2E6B30")            # dessous des feuillages
PIN = hexrgb("#2D6A3E")              # aiguilles du pin japonais (vert bleuté sombre)
PIN_CLAIR = hexrgb("#46904A")
ECORCE_PIN = hexrgb("#7C4B36")       # écorce rousse du pin rouge
ECORCE_CERISIER = hexrgb("#83594F")  # écorce brun-violet du cerisier (reste lisible à l'ombre du houppier)
SAKURA_OMBRE = hexrgb("#C8608D")     # dessous des houppiers roses
SAKURA_VIF = hexrgb("#D96A9C")       # rose soutenu du cerisier double (yaezakura)
SAKURA_BLANC = hexrgb("#FDE3EC")     # sommet presque blanc
CREUX = hexrgb("#3A2416")            # cavité dans le tronc
CHAMPIGNON = hexrgb("#EBDDBF")       # polypores sur les géants
LIANE = hexrgb("#3D7A2E")
AZALEE = hexrgb("#E2589B")
AZALEE_CLAIR = hexrgb("#F28DBE")
HORTENSIA = hexrgb("#7A92E6")
HORTENSIA_MAUVE = hexrgb("#A88ADF")
MOUSSE = hexrgb("#6DAF3F")
VIOLET_IRIS = hexrgb("#7C5CC4")


class _K:
    """Cotes de conception (taille 1, demi-stud) multipliées par `t` : pièces de feuillage, de bois, coins."""

    def __init__(self, b, t: float = 1.0):
        self.b = b
        self.t = float(t)

    def p(self, *v):
        return tuple(x * self.t for x in v)

    def feuille(self, x0, y0, z0, x1, y1, z1, col, **kw):
        kw.setdefault("studs", "top")
        kw.setdefault("collide", False)
        kw.setdefault("name", "Feuillage")
        return self.b.box(self.p(x0, y0, z0), self.p(x1, y1, z1), col, **kw)

    def touffe(self, cx, y0, cz, sx, sy, sz, col, yaw=0.0, **kw):
        """Bloc de feuillage donné par le centre de sa base, sa taille et sa rotation (0° ou 45° le plus souvent)."""
        kw.setdefault("studs", "top")
        kw.setdefault("collide", False)
        kw.setdefault("name", "Feuillage")
        return self.b.boxc(self.p(cx, y0 + sy / 2, cz), self.p(sx, sy, sz), col, yaw=yaw, **kw)

    def bois(self, x0, y0, z0, x1, y1, z1, col, **kw):
        kw.setdefault("name", "Tronc")
        return self.b.box(self.p(x0, y0, z0), self.p(x1, y1, z1), col, **kw)

    def coin(self, x0, y0, z0, x1, y1, z1, col, down, **kw):
        kw.setdefault("name", "Racine")
        return self.b.wedge(self.p(x0, y0, z0), self.p(x1, y1, z1), col, down=down, **kw)


def _infos(b, n0: int) -> dict:
    """Emprise (x, z) et hauteur réelles des pièces ajoutées depuis `n0`, dans le repère de l'asset."""
    o = b.to_world((0, 0, 0))
    M = np.vstack([b.to_world(e) - o for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))])
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for p in b.parts[n0:]:
        R = np.asarray(p.rot, float).reshape(3, 3)
        half = np.asarray(p.size, float) / 2
        for s in ((1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1), (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1)):
            loc = M @ (np.asarray(p.pos, float) + R @ (half * s) - o)
            lo, hi = np.minimum(lo, loc), np.maximum(hi, loc)
    if not np.isfinite(lo).all():
        return {"emprise": (0, 0), "hauteur": 0}
    return {"emprise": (round(float(hi[0] - lo[0]), 1), round(float(hi[2] - lo[2]), 1)), "hauteur": round(float(hi[1]), 1)}


def _racines(k, col, specs):
    """Petites racines en coin au pied d'un tronc : (x0, z0, x1, z1, hauteur, sens de la pente)."""
    for (x0, z0, x1, z1, h, down) in specs:
        k.coin(x0, 0, z0, x1, h, z1, col, down)


# ---------------------------------------------------------------------------
# Arbres du village
# ---------------------------------------------------------------------------

def arbre(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Arbre feuillu du village (12 à 20 studs à taille 1), 4 silhouettes :
    0 rond à lobes, 1 élancé en colonne, 2 parasol à branches fourchues, 3 pin japonais en plateaux."""
    rng = b.rng
    k = _K(b, taille)
    v = variant % 4
    n0 = len(b.parts)

    def F(name, a=0.035):
        return vary(name, rng, a)

    def M(a, b_, t):
        return vary(mix(c(a), c(b_), t), rng, 0.03)

    tr = F("tronc", 0.03)
    rac = shade(c("tronc"), 0.86)
    with b.group("Arbre"):
        if v == 0:  # rond : boule « octogonale » (blocs droits et blocs à 45° alternés), branche basse et sa touffe
            k.bois(-1, 0, -1, 1, 10, 1, tr)
            _racines(k, rac, [(0.5, -0.5, 2.5, 0.5, 1.5, "+x"), (-0.5, -2.5, 0.5, -0.5, 1.0, "-z"),
                              (-2, 0.5, -0.5, 1.5, 1.0, "-x")])
            k.bois(-2.5, 4.5, -0.5, -1, 5.5, 0.5, tr, collide=False, name="Branche")
            k.feuille(-3.5, 4, -1, -2, 6, 1, F("feuille_claire"))
            k.touffe(0, 7.5, 0, 6, 1, 6, OMBRE)
            k.touffe(0, 8.5, 0, 8, 2, 8, F("feuille_fonce"), 45)
            k.touffe(0, 10, 0, 11, 3.5, 11, F("feuille"))
            k.touffe(0.5, 10.5, -0.5, 10, 4, 10, M("feuille", "feuille_claire", 0.35), 45)
            k.touffe(0, 13.5, 0, 7, 2.5, 7, F("feuille_claire"))
            k.touffe(0.5, 16, 0, 4, 1.5, 4, F("herbe_claire"), 45)
            k.touffe(-4.5, 9, 4.5, 3, 2.5, 3, F("feuille_fonce"), 20)
        elif v == 1:  # élancé : colonne torsadée (étages alternés droits / 45°), légère inclinaison
            k.bois(-1, 0, -1, 1, 7, 1, tr)
            _racines(k, rac, [(0.5, -0.5, 2, 0.5, 1.0, "+x"), (-0.5, 0.5, 0.5, 2, 1.0, "+z"),
                              (-2, -0.5, -0.5, 0.5, 1.0, "-x")])
            k.touffe(0, 4, 0, 4, 1, 4, OMBRE)
            k.touffe(0, 5, 0, 6.5, 4.5, 6.5, F("feuille_fonce"))
            k.touffe(0.25, 8.5, 0.25, 6.5, 4, 6.5, M("feuille_fonce", "feuille", 0.5), 45)
            k.touffe(0.5, 12, 0.25, 5, 3.5, 5, F("feuille"))
            k.touffe(0.5, 15, 0.5, 4, 3, 4, M("feuille", "feuille_claire", 0.55), 45)
            k.touffe(0.75, 17.5, 0.5, 2.5, 1.5, 2.5, F("feuille_claire"))
            k.touffe(0.75, 19, 0.75, 1.5, 1, 1.5, F("herbe_claire"), 45)
        elif v == 2:  # parasol : tronc fourchu, large plateau octogonal qui retombe sur les côtés
            k.bois(-1, 0, -1, 1, 11, 1, tr)
            _racines(k, rac, [(0.5, -0.5, 2.5, 0.5, 1.5, "+x"), (-2.5, -0.5, -0.5, 0.5, 1.5, "-x"),
                              (-0.5, 0.5, 0.5, 2, 1.0, "+z")])
            k.bois(-4, 7, -1.5, -0.5, 8.5, 0.5, tr, name="Branche")
            k.bois(-4.5, 8, -1, -3, 11, 1, tr, name="Branche")
            k.bois(0.5, 8, -0.5, 4, 9.5, 1.5, tr, name="Branche")
            k.bois(3.5, 9, -1, 5, 11, 1, tr, name="Branche")
            k.feuille(-6.5, 10.5, -5, 6.5, 11.5, 5, OMBRE)
            k.feuille(-8, 11.5, -6, 8, 14, 6, F("feuille"))
            k.touffe(0.5, 12, 0, 13, 2.5, 13, M("feuille", "feuille_claire", 0.3), 45)
            k.touffe(-0.5, 14.5, 0, 9, 1.5, 8, F("feuille_claire"))
            k.touffe(1, 16, -0.5, 4.5, 1, 4.5, F("herbe_claire"), 45)
            k.feuille(-9.5, 11, -3, -7, 13, 2, F("feuille_fonce"))
            k.feuille(7, 10.5, -1, 9.5, 13.5, 4, F("feuille_fonce"))
        else:  # pin japonais : tronc en zigzag, plateaux d'aiguilles étagés et un peu tournés au bout des branches
            e = vary(ECORCE_PIN, rng, 0.03)
            k.bois(-1, 0, -1, 1, 6, 1, e)
            k.bois(0, 5, -0.5, 2, 10, 1.5, e)
            k.bois(-0.5, 9, 0, 1.5, 16.5, 2, e)
            _racines(k, shade(ECORCE_PIN, 0.85), [(0.5, -0.5, 2.5, 0.5, 1.5, "+x"), (-0.5, -2.5, 0.5, -0.5, 1.0, "-z"),
                                                 (-2.5, -0.5, -0.5, 0.5, 1.0, "-x")])
            k.bois(-5, 6.5, -1, 0.5, 7.5, 0, e, collide=False, name="Branche")
            k.bois(1.5, 9.5, 0, 6, 10.5, 1, e, collide=False, name="Branche")
            k.bois(-4, 12.5, 0.5, 0, 13.5, 1.5, e, collide=False, name="Branche")
            k.bois(-0.5, 4, 0.5, 0.5, 5, 4.5, e, collide=False, name="Branche")
            # plateaux : (centre x, bas, centre z, largeur, profondeur, épaisseur, rotation)
            pads = [(-5.5, 7.5, -0.5, 7.5, 6.5, 1.5, 12), (5.5, 10.5, 0.5, 7, 6, 1.5, -18), (-4, 13.5, 1, 6, 5.5, 1.5, 24),
                    (0.5, 16.5, 1, 7.5, 6.5, 2, -8), (0, 5, 4.5, 4.5, 4, 1.5, -30)]
            for (cx, y0, cz, sx, sz, h, yaw) in pads:
                k.touffe(cx, y0, cz, sx, h, sz, vary(PIN, rng, 0.04), yaw)
                k.touffe(cx, y0 + h, cz, sx - 2, 1, sz - 2, vary(PIN_CLAIR, rng, 0.04), yaw)
    return _infos(b, n0)


def _petales(b, k, rng, pts, cols):
    """Pétales tombés : carreaux fins posés au sol (non mis à l'échelle en épaisseur)."""
    for i, (x, z, sx, sz) in enumerate(pts):
        x, z = k.p(x, z)
        b.boxc((x + rng.uniform(-0.3, 0.3), 0.1, z + rng.uniform(-0.3, 0.3)), (sx, 0.2, sz), cols[i % len(cols)],
               yaw=float(rng.uniform(0, 80)), collide=False, shadow=False, name="Petales")


def cerisier(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Cerisier en fleurs : tronc brun-violet tordu, houppier rose en nuage de blocs droits et à 45°, pétales au sol.
    0 large classique, 1 penché, 2 pleureur (rameaux de fleurs qui retombent), 3 compact rose soutenu (yaezakura)."""
    rng = b.rng
    k = _K(b, taille)
    v = variant % 4
    n0 = len(b.parts)

    def S(col, a=0.03):
        return vary(c(col) if isinstance(col, str) else col, rng, a)

    sf, s0, sc = c("sakura_fonce"), c("sakura"), c("sakura_clair")
    sf45 = mix(sf, s0, 0.45)
    e = vary(ECORCE_CERISIER, rng, 0.03)
    rac = shade(ECORCE_CERISIER, 0.86)
    sols = (s0, sc, sf)
    with b.group("Cerisier"):
        if v == 0:  # large : deux bras en V qui portent un nuage rose plus large que haut
            k.bois(-1, 0, -1, 1, 4.5, 1, e)
            _racines(k, rac, [(0.5, -0.5, 2.5, 0.5, 1.5, "+x"), (-2.5, -0.5, -0.5, 0.5, 1.0, "-x"),
                              (-0.5, 0.5, 0.5, 2.5, 1.0, "+z")])
            k.bois(-2.5, 4, -1.5, -0.5, 6.5, 0.5, e, name="Branche")
            k.bois(-4.5, 6, -1, -2, 8, 1, e, name="Branche")
            k.bois(0.5, 4, -0.5, 2.5, 7, 1.5, e, name="Branche")
            k.bois(2, 6.5, 0, 4.5, 8.5, 1, e, name="Branche")
            k.touffe(0, 8, 0, 10, 1, 7, SAKURA_OMBRE)
            k.touffe(0, 9, 0, 14, 3, 10, S(sf))
            k.touffe(0.5, 9.5, 0, 11, 3.5, 11, S(sf45), 45)
            k.touffe(-7.5, 8.75, 0.5, 5, 3, 5, S(s0), 30)
            k.touffe(7.5, 9.25, -1, 5, 3, 5, S(s0), -20)
            k.touffe(-0.5, 12, 0, 9, 2, 7, S(s0))
            k.touffe(0.5, 13, 0.5, 7, 2, 7, S(mix(s0, sc, 0.4)), 45)
            k.touffe(0, 15, 0, 3.5, 1, 3.5, S(sc))
            k.touffe(-3.5, 14, -1.5, 3, 1.5, 3, S(mix(s0, sc, 0.3)), 45)
            k.touffe(3.5, 14, 2, 2.5, 1.5, 2.5, S(s0), 20)
            k.touffe(3, 7, -3.5, 1.5, 1.5, 1.5, S(s0))
            k.touffe(-3.5, 7.25, 2.5, 1.5, 1.5, 1.5, S(sf))
            _petales(b, k, rng, [(4.5, -3, 1, 1), (-5.5, 2.5, 1.5, 1), (1.5, 6, 1, 1), (-3, -5.5, 1, 1.5), (7, 3.5, 1, 1)], sols)
        elif v == 1:  # penché : tronc en escalier, couronne décalée, une branche basse fleurie
            k.bois(-1, 0, -1, 1, 5, 1, e)
            k.bois(0, 4.5, -0.5, 2, 9, 1.5, e)
            k.bois(1, 8.5, -1, 3, 11, 1, e)
            _racines(k, rac, [(-2.5, -0.5, -0.5, 0.5, 1.5, "-x"), (-0.5, -2.5, 0.5, -0.5, 1.0, "-z"),
                              (0.5, -0.5, 2, 0.5, 1.0, "+x")])
            k.bois(-3, 6, 0, 0.5, 7, 1, e, collide=False, name="Branche")
            k.feuille(-5, 6.5, -1, -2.5, 8.5, 2, S(s0))
            k.touffe(2, 10.5, 0, 8, 1, 6, SAKURA_OMBRE)
            k.touffe(2, 11.5, 0, 12, 3.5, 9, S(sf))
            k.touffe(2.5, 12, -0.5, 10, 4, 10, S(sf45), 45)
            k.touffe(8.5, 11.25, 0, 4.5, 3, 4.5, S(s0), 25)
            k.touffe(-4, 12.25, 0.5, 4, 2.5, 4, S(s0), -15)
            k.touffe(2, 15, 0, 8, 2, 6.5, S(s0))
            k.touffe(2.5, 17, 0, 4, 1, 4, S(sc), 45)
            k.touffe(-1, 16.5, 1.5, 3, 1, 3, S(mix(s0, sc, 0.3)), 30)
            k.touffe(6.75, 10, -2.25, 1.5, 1.5, 1.5, S(s0))
            _petales(b, k, rng, [(5.5, -2.5, 1, 1), (-3.5, 3.5, 1.5, 1), (2.5, 5.5, 1, 1), (8, 2, 1, 1.5), (-4.5, -4, 1, 1)], sols)
        elif v == 2:  # pleureur : dôme rose d'où retombent douze rameaux fleuris de longueurs alternées
            k.bois(-1, 0, -1, 1, 9, 1, e)
            k.bois(-0.5, 8.5, -0.5, 1.5, 12.5, 1.5, e)
            _racines(k, rac, [(0.5, -0.5, 2.5, 0.5, 1.5, "+x"), (-2.5, -0.5, -0.5, 0.5, 1.0, "-x"),
                              (-0.5, -2.5, 0.5, -0.5, 1.0, "-z")])
            k.touffe(0, 11, 0, 9, 1, 9, SAKURA_OMBRE)
            k.touffe(0, 12, 0, 13, 2.5, 13, S(sf))
            k.touffe(0, 12.5, 0, 12, 3, 12, S(sf45), 45)
            k.touffe(0, 14.5, 0, 9.5, 2, 9.5, S(s0))
            k.touffe(0.5, 15, -0.5, 8, 2, 8, S(mix(s0, sc, 0.3)), 45)
            k.touffe(0, 16.5, 0, 4, 1, 4, S(sc), 45)
            # rameaux : 20 lames fines (anneau extérieur long, anneau intérieur plus court) : un rideau rose irrégulier
            for i in range(20):
                ext = i < 12
                n, j = (12, i) if ext else (8, i - 12)
                ang = j * 360 / n + (8 if ext else 30)
                a = math.radians(ang)
                ybas = ((5.0, 8.0, 6.5, 4.0, 9.0, 5.5, 7.5, 4.5, 8.5, 6.0, 3.5, 7.0)[j] if ext
                        else (8.5, 9.5, 7.5, 10.0, 8.0, 9.0, 7.0, 10.0)[j])
                ray = 6.6 if ext else 4.8
                lg = (0.5, 0.4, 0.6)[i % 3]
                col = S((sf, s0, sf45, mix(s0, sc, 0.5), s0)[i % 5])
                with b.at(k.p(math.sin(a) * ray, 0, math.cos(a) * ray), yaw=ang):
                    k.feuille(-lg, ybas, -0.4, lg, 13, 0.4, col, studs="none")
            _petales(b, k, rng, [(4.5, -4.5, 1, 1), (-5, 3, 1.5, 1), (3, 5.5, 1, 1), (8.5, 1, 1, 1)], sols)
        else:  # compact : boule rose soutenu, tronc court et coudé
            k.bois(-1, 0, -1, 1, 4, 1, e)
            k.bois(-1.5, 3.5, -0.5, 0.5, 7, 1.5, e)
            _racines(k, rac, [(0.5, -0.5, 2, 0.5, 1.0, "+x"), (-2.5, -0.5, -0.5, 0.5, 1.5, "-x"),
                              (-0.5, 0.5, 0.5, 2, 1.0, "+z")])
            k.touffe(-0.5, 6.5, 0.5, 7, 1, 7, SAKURA_OMBRE)
            k.touffe(-0.5, 7.5, 0.5, 10, 3.5, 10, S(SAKURA_VIF))
            k.touffe(0, 8, 0, 10, 3.5, 10, S(mix(SAKURA_VIF, sf, 0.5)), 45)
            k.touffe(-0.5, 11, 0.5, 7, 2, 7, S(sf))
            k.touffe(0, 12, 0, 5.5, 1.5, 5.5, S(mix(sf, s0, 0.5)), 45)
            k.touffe(-0.5, 13.5, 0.5, 3, 1, 3, S(s0))
            k.touffe(-6, 8.25, 1, 3, 2.5, 3, S(sf), 20)
            k.touffe(5, 8.75, -1.5, 3, 2.5, 3, S(SAKURA_VIF), -30)
            _petales(b, k, rng, [(4, -3.5, 1, 1), (-4.5, 3, 1, 1.5), (2, 5, 1, 1), (-3.5, -4.5, 1.5, 1), (6, 2.5, 1, 1)],
                     (sf, s0, SAKURA_VIF))
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Géants de la forêt de Konoha
# ---------------------------------------------------------------------------

def _tronc_pixel(k, cx, cz, r, y0, y1, cols, name="Tronc", pied=False):
    """Tronc rond « pixel » : trois blocs croisés (contour en escalier), trois tons d'écorce.
    Les dessus sont étagés d'un stud (et les dessous aussi si `pied`, pour un tronçon dont le dessous se voit) :
    aucune face coplanaire de couleurs différentes."""
    a, s, m = r, r - 2, r - 1
    d1, d2 = (1, 2) if pied else (0, 0)
    k.bois(cx - a, y0 + d2, cz - s, cx + a, y1, cz + s, cols[0], name=name)
    k.bois(cx - s, y0 + d1, cz - a, cx + s, y1 + 1, cz + a, cols[1], name=name)
    k.bois(cx - m, y0, cz - m, cx + m, y1 + 2, cz + m, cols[2], name=name)


def _masse(k, cx, y0, cz, w, d, h, cols, sommet=True, rot=0.0):
    """Masse de feuillage en nuage de blocs : (cx, cz) centre, y0 bas, w × d emprise du corps, h hauteur du corps.
    Dessous sombre en retrait, corps droit + corps tourné de 45° (contour octogonal), étage plus clair, sommet
    ensoleillé. Toutes les hauteurs internes sont y0 + multiples du demi-stud : deux masses dont les y0 n'ont pas la
    même partie fractionnaire (modulo 0,5) n'ont jamais de faces horizontales au même niveau. Renvoie le haut de
    l'étage."""
    ombre, fonce, moyen, clair = cols
    k.touffe(cx, y0, cz, w - 6, 1.5, d - 6, ombre, rot)
    yb = y0 + 1.5
    yt = yb + h
    k.touffe(cx, yb, cz, w, h, d, fonce, rot)
    s = round(min(w, d) * 0.84 * 2) / 2
    k.touffe(cx + 0.5, yb + 0.5, cz - 0.5, s, h + 1, s, mix(fonce, moyen, 0.45), rot + 45)
    he = max(2.5, round(h * 0.6 * 2) / 2)
    k.touffe(cx - 0.5, yt, cz + 0.5, round(w * 0.62 * 2) / 2, he, round(d * 0.62 * 2) / 2, moyen, rot)
    if sommet:
        hs = max(1.5, round(h * 0.3 * 2) / 2)
        e = round(min(w, d) * 0.36 * 2) / 2
        k.touffe(cx + 0.5, yt + he, cz, e, hs, e, clair, rot + 45)
    return yt + he


# Hauteurs : chaque masse de feuillage a sa propre « famille » de hauteurs (partie fractionnaire de y0 modulo 0,5 :
# .0, .0625, .125, .1875, .25, .3125, .375…) : jamais deux faces horizontales de masses différentes au même niveau.
#   centre   : (cx, y0, cz, w, d, h) masse posée sur le tronc (y0 = h2 - 2,5 : le haut du tronc est noyé dedans)
#   dessus   : (cx, cz, w, d, h) seconde masse posée sur l'étage du centre
#   couronne : (angle, rayon, y0, w, d, h) masses portées chacune par une branche
GEANTS = [
    # 0 : dôme — grande couronne arrondie, une masse centrale surmontée, cinq masses autour
    dict(r=5.5, h1=26, r2=4.0, h2=58, centre=(0.5, 55.5, -0.5, 30, 28, 9), dessus=(0.25, -0.25, 18, 17, 6),
         couronne=[(20, 15, 49.25, 20, 18, 7), (95, 16, 52.375, 19, 18, 6.5), (170, 15, 48.125, 20, 19, 7),
                   (250, 16, 51.1875, 18, 18, 6.5), (320, 14, 54.3125, 17, 16, 6)],
         racines=[(10, 10, 8), (70, 8, 7), (135, 11, 8.5), (200, 9, 7), (265, 10, 8), (320, 8, 6.5)],
         lianes=[(0, 0.5, 11), (2, 0.55, 9), (3, 0.45, 12)]),
    # 1 : élancé — tronc haut, couronne étroite en deux étages
    dict(r=5.0, h1=34, r2=3.5, h2=72, centre=(-0.5, 69.5, 0.5, 24, 23, 8), dessus=(0.25, 0.25, 16, 15, 6),
         couronne=[(60, 12, 62.25, 17, 16, 6), (180, 12.5, 59.375, 16, 15, 6), (300, 12, 64.125, 16, 15, 5.5),
                   (120, 11, 74.1875, 14, 13, 5)],
         racines=[(30, 9, 7), (100, 10, 8), (170, 8, 6.5), (240, 10, 8), (300, 8.5, 7)],
         lianes=[(0, 0.5, 12), (1, 0.6, 10)]),
    # 2 : large — couronne plate et vaste (parasol), cinq longues branches
    dict(r=6.0, h1=24, r2=4.5, h2=56, centre=(0, 53.5, 0, 32, 30, 8),
         couronne=[(5, 19, 47.25, 22, 20, 6.5), (80, 20, 49.375, 21, 20, 6), (150, 19, 46.125, 22, 21, 6.5),
                   (220, 20, 48.1875, 21, 20, 6), (290, 19, 50.3125, 22, 20, 6)],
         racines=[(0, 11, 9), (60, 9, 7.5), (120, 11, 8.5), (180, 9.5, 7.5), (240, 11, 9), (300, 9, 7)],
         lianes=[(0, 0.5, 10), (1, 0.45, 12), (2, 0.55, 9), (3, 0.5, 11), (4, 0.5, 10)]),
    # 3 : fourchu — un second fût part d'un coude du tronc et porte sa propre couronne
    dict(r=5.5, h1=30, r2=4.0, h2=66, centre=(-1.5, 63.5, 0.5, 26, 25, 8),
         fourche=((6.25, -0.75), (9.75, -1.25), 3.0, 52, (12.75, 50.625, -1.25, 22, 21, 7)),
         couronne=[(140, 13, 55.25, 18, 17, 6), (230, 12, 58.375, 16, 15, 5.5), (320, 12, 52.1875, 17, 16, 6)],
         racines=[(20, 10, 8), (90, 9, 7), (160, 10.5, 8), (230, 8.5, 7), (300, 10, 8)],
         lianes=[(0, 0.5, 10), (1, 0.55, 9), (2, 0.5, 11)]),
]


def arbre_geant(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Grand arbre de la forêt autour de Konoha (70 à 100 studs à taille 1) : tronc rond « pixel » de rayon 4 à 6
    en deux tronçons, racines en contreforts, branches en escalier, couronne de 4 à 7 masses (50 à 70 studs de large)
    qui dépasse du rempart et cadre le ciel, lianes."""
    rng = b.rng
    k = _K(b, taille)
    v = variant % 4
    P = GEANTS[v]
    n0 = len(b.parts)
    tr = c("tronc")
    ecorce = (vary(tr, rng, 0.03), shade(tr, 0.9), shade(tr, 1.07))
    ecorce2 = (shade(tr, 1.04), shade(tr, 0.93), shade(tr, 0.86))
    strie = shade(tr, 0.75)
    racine = shade(tr, 0.9)

    def fcols():
        return (OMBRE, vary("feuille_fonce", rng, 0.03), vary("feuille", rng, 0.03), vary("feuille_claire", rng, 0.03))

    r, h1, r2, h2 = P["r"], P["h1"], P["r2"], P["h2"]
    with b.group("ArbreGeant"):
        with b.group("Tronc"):
            _tronc_pixel(k, 0, 0, r, 0, h1, ecorce)
            _tronc_pixel(k, 0, 0, r2, h1 - 2, h2, ecorce2)
            # stries d'écorce, cavité, polypores (visibles depuis le sol de la forêt)
            k.bois(r - 0.5, 2, -1.25, r + 0.4, h1 - 4, -0.25, strie, name="Ecorce")
            k.bois(-r - 0.4, 3, 0.75, -r + 0.5, h1 - 7, 1.75, strie, name="Ecorce")
            k.bois(1.25, 5, r - 0.5, 2.25, h1 - 3, r + 0.4, strie, name="Ecorce")
            k.bois(-1.5, 5.5, -r - 0.3, 1.5, 10.5, -r + 0.5, CREUX, name="Cavite")
            k.bois(r - 0.5, 14, -3.25, r + 1.3, 14.6, -1.75, CHAMPIGNON, collide=False, name="Champignon")
            k.bois(r - 0.5, 16.5, -2.75, r + 0.9, 17.1, -1.5, CHAMPIGNON, collide=False, name="Champignon")
        with b.group("Racines"):
            for (ang, long, haut) in P["racines"]:
                with b.at((0, 0, 0), yaw=ang + float(rng.uniform(-8, 8))):
                    k.coin(-2.5, 0, r - 2.5, 2.5, haut, r + long, racine, "+z")
                    dx = 1.0 if long > 9 else -1.0
                    k.coin(-1.75 + dx, 0, r + long - 2, 1.75 + dx, 2.5, r + long + 5, shade(racine, 0.93), "+z")
        with b.group("Branches"):
            for (ang, R, y0, _w, _d, _h) in P["couronne"]:
                with b.at(k.p(0, y0 - 4, 0), yaw=ang):
                    k.bois(-1.75, 0, 0, 1.75, 3.5, R - 1.5, ecorce[0], name="Branche")
                    k.bois(-1.5, 2.5, R - 3.5, 1.5, 5, R - 0.5, ecorce[0], name="Branche")
                    k.b.wedge_under(k.p(-1.25, -3, r2 - 1), k.p(1.25, 0, r2 + 5), ecorce[1], down="+z", name="Branche")
            if "fourche" in P:  # second fût : sort du flanc du tronc puis s'écarte d'une marche
                (fx1, fz1), (fx2, fz2), fr, fh, _crown = P["fourche"]
                _tronc_pixel(k, fx1, fz1, fr, h1 - 6, h1 + 10, ecorce, pied=True)
                _tronc_pixel(k, fx2, fz2, fr, h1 + 8, fh, ecorce2, pied=True)
        with b.group("Feuillage"):
            cx, y0, cz, w, d, h = P["centre"]
            haut = _masse(k, cx, y0, cz, w, d, h, fcols(), sommet="dessus" not in P)
            if "dessus" in P:  # posée sur l'étage du centre, tournée de 12°, famille de hauteurs .0625
                ex, ez, ew, ed, eh = P["dessus"]
                _masse(k, ex, haut - 1.9375, ez, ew, ed, eh, fcols(), rot=12)
            for (ang, R, y0, w, d, h) in P["couronne"]:
                a = math.radians(ang)
                _masse(k, math.sin(a) * (R - 2), y0, math.cos(a) * (R - 2), w, d, h, fcols(),
                       rot=float(rng.uniform(-12, 12)))
            if "fourche" in P:
                cx2, cy2, cz2, cw, cd, chh = P["fourche"][4]
                _masse(k, cx2, cy2, cz2, cw, cd, chh, fcols())
        with b.group("Lianes"):
            for (ib, frac, long) in P["lianes"]:
                ang, R, y0, _w, _d, _h = P["couronne"][ib % len(P["couronne"])]
                with b.at(k.p(0, y0 - 4, 0), yaw=ang):
                    # entre le gousset et le bout de la branche : trois rameaux de longueurs différentes
                    z0, z1 = r2 + 5.5, max(r2 + 5.5, R - 2.5)
                    for j, (dxl, fl) in enumerate(((-1.1, 1.0), (1.1, 0.6), (0.0, 0.8))):
                        z = z0 + (z1 - z0) * (frac + j * (1 - frac) / 2) * 0.9
                        ll = long * fl
                        k.bois(dxl - 0.4, -ll, z - 0.4, dxl + 0.4, 0.5, z + 0.4, vary(LIANE, rng, 0.06),
                               collide=False, name="Liane")
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Petite végétation
# ---------------------------------------------------------------------------

def buisson(b, variant: int = 0) -> dict:
    """Buisson bas (≈ 3 studs) : 0 boule verte, 1 azalée en fleurs, 2 hortensia bleu, 3 haie taillée."""
    rng = b.rng
    v = variant % 4
    n0 = len(b.parts)
    k = _K(b, 1.0)

    def F(name, a=0.04):
        return vary(name, rng, a)

    with b.group("Buisson"):
        if v == 0:  # boule verte
            k.touffe(0, 0, 0, 4, 2, 3.5, F("feuille"))
            k.touffe(0.25, 0, -0.25, 3.5, 2.5, 3.5, vary(mix(c("feuille"), c("feuille_claire"), 0.3), rng, 0.04), 45)
            k.touffe(-0.25, 2, 0.25, 2.5, 1, 2, F("feuille_claire"))
            k.touffe(2.25, 0, 1, 2, 1.5, 2, F("feuille_fonce"), 30)
            k.touffe(-2.25, 0, -0.75, 1.5, 1, 1.5, F("feuille_fonce"), -20)
            k.touffe(0, 3, 0, 1, 0.5, 1, F("herbe_claire"), 45)
        elif v == 1:  # azalée (tsutsuji) : dôme taillé piqué de fleurs roses
            k.touffe(0, 0, 0, 5, 2, 3, F("feuille_fonce"))
            k.touffe(0, 0, 0, 3.5, 2.5, 3.5, vary(mix(c("feuille_fonce"), c("feuille"), 0.5), rng, 0.04), 45)
            for (x, y, z, col) in ((-1.2, 2.0, -0.3, AZALEE), (0.6, 2.25, 0.5, AZALEE_CLAIR), (1.7, 1.75, -0.6, AZALEE),
                                   (-0.2, 2.2, -0.9, AZALEE_CLAIR), (-2.3, 1.3, 0.4, AZALEE_CLAIR), (1.0, 1.0, -1.4, AZALEE)):
                b.box((x - 0.4, y - 0.4, z - 0.4), (x + 0.4, y + 0.4, z + 0.4), col, studs="top", collide=False, name="Fleur")
        elif v == 2:  # hortensia (ajisai) : feuillage sombre, grosses boules bleues et mauves
            k.touffe(0, 0, 0, 4, 2.5, 3, F("feuille_fonce"))
            k.touffe(0.5, 0, 1, 3, 2, 3, F("feuille"), 45)
            for (x, y, z, col) in ((-1.1, 2.5, -0.7, HORTENSIA), (1.1, 2.5, 0.2, HORTENSIA_MAUVE), (-0.4, 2.0, -1.5, HORTENSIA_MAUVE),
                                   (1.6, 2.0, 1.6, HORTENSIA)):
                b.box((x - 0.7, y - 0.5, z - 0.7), (x + 0.7, y + 0.6, z + 0.7), vary(col, rng, 0.05), studs="top",
                      collide=False, name="Fleur")
        else:  # haie taillée : pavé vert foncé, dessus clair, bouts arrondis
            k.feuille(-3, 0, -1, 3, 2, 1, F("feuille_fonce"))
            k.feuille(-2.5, 2, -0.5, 2.5, 2.5, 0.5, F("feuille"))
            k.touffe(-3, 0, 0, 1.5, 1.5, 1.5, F("feuille"), 45)
            k.touffe(3, 0, 0, 1.5, 1.5, 1.5, F("feuille"), 45)
    return _infos(b, n0)


def rocher_deco(b, variant: int = 0) -> dict:
    """Groupe de rochers taillés en blocs : 0 granite gris moussu, 1 grès (comme le rocher des Hokage),
    2 pierre dressée, 3 galets plats. Studs sur les dessus, mousse en plaque."""
    rng = b.rng
    v = variant % 4
    n0 = len(b.parts)
    gris = (c("pave_fonce"), shade(c("pave_fonce"), 0.9), c("bordure"), c("pave"))
    gres = (c("roche"), c("roche_claire"), c("roche_fonce"), shade(c("roche"), 1.05))

    def R(cx, cy, cz, sx, sy, sz, col, yaw, **kw):
        kw.setdefault("studs", "top")
        kw.setdefault("name", "Rocher")
        return b.boxc((cx, cy, cz), (sx, sy, sz), col, yaw=yaw, **kw)

    with b.group("Rochers"):
        if v == 0:
            R(0, 1.25, 0, 4, 2.5, 3.5, gris[0], 12)
            with b.at((0, 0, 0), yaw=12):
                b.wedge((-3, 0, -1.25), (-2, 1.75, 1.5), gris[2], down="-x", name="Rocher")
            R(-0.3, 3.0, 0.2, 3, 1.0, 2.5, gris[3], 18)
            R(-0.6, 3.65, 0.4, 1.8, 0.3, 1.5, MOUSSE, 18, collide=False, name="Mousse")
            R(2.9, 0.6, 1.4, 1.8, 1.2, 1.6, gris[1], -20)
            R(-2.6, 0.45, 1.6, 1.4, 0.9, 1.2, gris[2], 35)
            R(1.3, 0.3, -2.5, 1.0, 0.6, 0.8, gris[0], 8)
            b.box((-2.3, 0, -1.9), (-1.9, 1.2, -1.5), c("herbe_fonce"), collide=False, shadow=False, name="Brin")
            b.box((-1.8, 0, -2.2), (-1.4, 0.8, -1.8), c("herbe_claire"), collide=False, shadow=False, name="Brin")
        elif v == 1:
            R(0, 1.5, 0, 4, 3, 3, gres[0], -10)
            with b.at((0, 0, 0), yaw=-10):
                b.wedge((-1.5, 0, 1.5), (1.25, 2.25, 2.75), gres[2], down="+z", name="Rocher")
            R(0.4, 3.5, -0.2, 2.5, 1, 2, gres[1], 5)
            R(-2.4, 0.75, 1.0, 2, 1.5, 2.5, gres[2], 30)
            R(2.4, 0.5, 1.3, 1.6, 1.0, 1.4, gres[3], -35)
            R(0.8, 0.35, -2.4, 1.2, 0.7, 1.0, gres[2], 15)
        elif v == 2:
            R(0, 2.25, 0, 1.8, 4.5, 1.6, gris[0], 10)
            R(0.1, 4.75, 0.05, 1.2, 0.5, 1.1, gris[3], 25)
            R(1.6, 0.6, 0.9, 1.8, 1.2, 1.6, gris[1], -25)
            R(-1.5, 0.4, -0.8, 1.4, 0.8, 1.2, gres[2], 40)
            R(-0.1, 1.35, 1.2, 1.2, 0.3, 0.8, MOUSSE, 10, collide=False, name="Mousse")
            R(-1.2, 0.95, 0.2, 0.9, 0.3, 0.7, MOUSSE, 0, collide=False, name="Mousse")
        else:
            for i, (x, z, sx, sz, h, yaw) in enumerate(((0, 0, 2.6, 2.0, 0.8, 8), (2.3, 1.2, 1.8, 1.4, 0.6, -25),
                                                         (-2.1, 0.9, 1.6, 1.6, 0.7, 40), (0.6, -2.0, 1.4, 1.2, 0.5, 15),
                                                         (-1.2, -1.9, 1.0, 0.9, 0.4, -10))):
                R(x, h / 2, z, sx, h, sz, (gris[0], gris[3], gris[1], gres[1], gris[2])[i], yaw)
            R(-0.3, 0.95, 0.1, 1.2, 0.3, 0.9, MOUSSE, 8, collide=False, name="Mousse")
    _ = rng
    return _infos(b, n0)


FLEURS = [
    (c("rouge"), c("jaune_lampion"), c("blanc")),          # tulipes
    (AZALEE, c("sakura"), c("blanc")),                     # roses et blanches
    (HORTENSIA, VIOLET_IRIS, c("blanc")),                  # iris et campanules
    (c("toit_orange"), c("jaune_lampion"), c("rouge")),    # soucis
]


def parterre_fleurs(b, variant: int = 0, largeur: float = 6, profondeur: float = 4) -> dict:
    """Parterre en bordure de bois : terre, rangs de feuillage, fleurs en petits blocs de couleur (≤ 25 pièces)."""
    rng = b.rng
    v = variant % 4
    n0 = len(b.parts)
    w, d = largeur / 2, profondeur / 2
    cols = FLEURS[v]
    with b.group("Parterre"):
        b.box((-w, 0, -d), (w, 0.8, d), c("bois"), name="Bordure")
        b.box((-w + 0.4, 0.8, -d + 0.4), (w - 0.4, 1.0, d - 0.4), c("terre"), studs="top", name="Terre")
        inner = 2 * d - 0.8
        rangs = [(-d + 0.7, d - 0.7)] if inner < 2.8 else [(-d + 0.7, -0.35), (0.35, d - 0.7)]
        n_max = (25 - 2 - len(rangs)) // len(rangs)
        for j, (za, zb) in enumerate(rangs):
            b.box((-w + 0.6, 1.0, za), (w - 0.6, 1.6, zb), vary("feuille_fonce" if j % 2 == 0 else "feuille", rng, 0.03),
                  studs="top", collide=False, name="Feuillage")
            pas = max(1.2, (2 * w - 1.6) / n_max)
            n = min(n_max, int((2 * w - 1.6) // pas) + 1)
            x0 = -(n - 1) * pas / 2
            for i in range(n):
                x = x0 + i * pas + (0.25 if (i + j) % 2 else -0.25) * (pas > 1.5)
                z = (za + zb) / 2 + (0.3 if i % 2 else -0.3) * (zb - za > 1.6)
                haut = 2.1 if (i + j) % 3 else 2.5
                col = cols[(i + 2 * j + v) % len(cols)]
                b.box((x - 0.45, 1.6, z - 0.45), (x + 0.45, haut, z + 0.45), col, studs="top", collide=False, name="Fleur")
    return _infos(b, n0)


def touffe_herbe(b, variant: int = 0) -> dict:
    """Touffe d'herbe ou petite fleur (≤ 4 pièces) : 0 brins, 1 herbes hautes, 2 fleur jaune, 3 fleur blanche."""
    v = variant % 4
    n0 = len(b.parts)
    fonce, clair, moy = c("herbe_fonce"), c("herbe_claire"), c("feuille")
    kw = dict(collide=False, shadow=False)
    with b.group("Herbe"):
        if v == 0:
            b.box((-0.2, 0, -0.2), (0.2, 1.6, 0.2), fonce, name="Brin", **kw)
            b.box((0.4, 0, 0.15), (0.8, 1.1, 0.55), clair, name="Brin", **kw)
            b.box((-0.75, 0, 0.1), (-0.35, 1.25, 0.5), moy, name="Brin", **kw)
        elif v == 1:
            b.box((-0.2, 0, -0.2), (0.2, 2.3, 0.2), fonce, name="Brin", **kw)
            b.box((0.35, 0, -0.1), (0.75, 1.7, 0.3), moy, name="Brin", **kw)
            b.box((-0.7, 0, 0.2), (-0.3, 1.4, 0.6), clair, name="Brin", **kw)
            b.wedge((-0.2, 0, -0.95), (0.2, 1.0, -0.2), fonce, down="-z", name="Brin", **kw)
        elif v == 2:  # fleur jaune (comme les fleurettes du sol de référence)
            b.box((-0.15, 0, -0.15), (0.15, 1.3, 0.15), fonce, name="Tige", **kw)
            b.box((-0.5, 1.3, -0.5), (0.5, 1.7, 0.5), c("jaune_lampion"), studs="top", name="Fleur", **kw)
            b.box((0.15, 0.45, -0.15), (0.65, 0.65, 0.15), moy, name="Feuille", **kw)
            b.box((0.5, 0, 0.3), (0.85, 0.9, 0.65), clair, name="Brin", **kw)
        else:  # fleur blanche à cœur jaune
            b.box((-0.15, 0, -0.15), (0.15, 1.1, 0.15), fonce, name="Tige", **kw)
            b.box((-0.45, 1.1, -0.45), (0.45, 1.4, 0.45), c("blanc"), name="Fleur", **kw)
            b.box((-0.2, 1.4, -0.2), (0.2, 1.55, 0.2), c("jaune_lampion"), name="Fleur", **kw)
            b.box((-0.75, 0, 0.2), (-0.4, 0.8, 0.55), clair, name="Brin", **kw)
    return _infos(b, n0)
