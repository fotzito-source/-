"""Végétation en style stud : arbres feuillus, cerisiers, grands arbres de la forêt, buissons, rochers, fleurs.

Feuillages en cubes empilés (studs sur le dessus), troncs en blocs bruns. Les feuillages et petits
détails ne collisionnent pas ; les troncs, si.
"""

from __future__ import annotations

from kit import shade
from palette import c, vary


def _r(v: float) -> float:
    """Arrondi au demi-stud (studs alignés, pièces propres)."""
    return round(v * 2) / 2


def _feuilles(b, cx, y0, cz, sx, sy, sz, col, **kw):
    sx, sy, sz = _r(sx), _r(sy), _r(sz)
    return b.box((cx - sx / 2, y0, cz - sz / 2), (cx + sx / 2, y0 + sy, cz + sz / 2), col, studs="top",
                 collide=False, name="Feuillage", **kw)


def _tronc(b, x, z, w, y0, y1, col=None):
    w = _r(w)
    return b.box((x - w / 2, y0, z - w / 2), (x + w / 2, y1, z + w / 2), col or c("tronc"), name="Tronc")


def arbre(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Arbre feuillu, 4 silhouettes : rond, élancé, parasol, étagé."""
    rng = b.rng
    t = taille
    f, fc, ff = c("feuille"), c("feuille_claire"), c("feuille_fonce")
    v = variant % 4
    with b.group("Arbre"):
        b.box((-1.5 * t, 0, -1.5 * t), (1.5 * t, 0.6, 1.5 * t), shade(c("tronc"), 0.85), name="Racines")
        if v == 0:  # rond
            h = _r(7 * t)
            _tronc(b, 0, 0, 2 * t, 0, h + 1)
            _feuilles(b, 0, h - 1, 0, 11 * t, 6 * t, 11 * t, f)
            _feuilles(b, 0.5, h + 5 * t - 1, -0.5, 7 * t, 4 * t, 7 * t, fc)
            for dx, dz in ((-5.5, 1), (5.5, -1.5), (1, 5.5), (-1.5, -5.5)):
                _feuilles(b, dx * t, h, dz * t, 4 * t, 4 * t, 4 * t, ff)
            hmax = h + 9 * t
        elif v == 1:  # élancé
            h = _r(6 * t)
            _tronc(b, 0, 0, 1.8 * t, 0, h + 8 * t)
            for k, (w, hh, col) in enumerate(((9, 5, ff), (7, 5, f), (5, 4, fc), (3, 2, fc))):
                _feuilles(b, (k % 2 - 0.5) * 0.5, h + sum((5, 5, 4, 2)[:k]) * t - k * 0.5, 0, w * t, hh * t, w * t, col)
            hmax = h + 16 * t
        elif v == 2:  # parasol
            h = _r(10 * t)
            _tronc(b, 0, 0, 2 * t, 0, h + 1)
            b.box((-4 * t, h - 2.5, -0.5), (0, h - 1.5, 0.5), c("tronc"), name="Branche")
            b.box((0, h - 3.5, -0.5), (3.5 * t, h - 2.5, 0.5), c("tronc"), name="Branche")
            _feuilles(b, 0, h, 0, 15 * t, 3.5 * t, 13 * t, f)
            _feuilles(b, -0.5, h + 3.5 * t, 0.5, 9 * t, 2.5 * t, 8 * t, fc)
            _feuilles(b, -6 * t, h - 2, 0, 4 * t, 2.5 * t, 4 * t, ff)
            hmax = h + 6 * t
        else:  # étagé, asymétrique
            h = _r(6 * t)
            _tronc(b, 0, 0, 2 * t, 0, h + 7 * t)
            b.box((0, h + 2, -0.6), (4 * t, h + 3, 0.6), c("tronc"), name="Branche")
            _feuilles(b, 4 * t, h + 3, 0, 7 * t, 4 * t, 7 * t, ff)
            _feuilles(b, -1 * t, h + 5 * t, 0.5, 9 * t, 4 * t, 9 * t, f)
            _feuilles(b, 0, h + 9 * t, 0, 6 * t, 3 * t, 6 * t, fc)
            hmax = h + 12 * t
    return {"emprise": (11 * t, 11 * t), "hauteur": hmax}


def cerisier(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Cerisier en fleurs : tronc sombre tordu, houppier rose en nuages, pétales au sol."""
    rng = b.rng
    t = taille
    s, sc, sf = c("sakura"), c("sakura_clair"), c("sakura_fonce")
    bois = shade(c("tronc"), 0.8)
    v = variant % 3
    with b.group("Cerisier"):
        b.box((-1.5 * t, 0, -1.5 * t), (1.5 * t, 0.6, 1.5 * t), shade(bois, 0.9), name="Racines")
        # tronc en deux segments décalés (silhouette tordue)
        d = (1, -1, 1)[v]
        b.box((-1 * t, 0, -1 * t), (1 * t, 5 * t, 1 * t), bois, name="Tronc")
        b.box((-1 * t + d * 0.8 * t, 5 * t, -0.9 * t), (0.9 * t + d * 0.8 * t, 9 * t, 0.9 * t), bois, name="Tronc")
        b.box((d * 0.8 * t, 7 * t, -0.5), (d * 4.5 * t, 8 * t, 0.5), bois, name="Branche")
        b.box((-d * 3.5 * t, 6 * t, -0.5), (d * 0.5 * t, 7 * t, 0.5), bois, name="Branche")
        y = 8 * t
        nuages = [
            (d * 0.8, y, 0, 12, 5, 11, s),
            (d * 4.5, y - 1.5, 1, 6, 4, 6, sf),
            (-d * 4, y - 2, -1, 6, 4, 6, sf),
            (d * 0.5, y + 5, -0.5, 8, 3.5, 7, sc),
            (-d * 1.5, y + 2, 4, 5, 4, 4, s),
            (d * 2.5, y + 1.5, -4.5, 5, 3.5, 4, sc),
        ]
        for (x, yy, z, w, h, dd, col) in nuages:
            _feuilles(b, x * t, yy, z * t, w * t, h * t, dd * t, col)
        # pétales tombés (fins carreaux roses posés sur le sol)
        for k in range(5):
            px, pz = rng.uniform(-6, 6) * t, rng.uniform(-6, 6) * t
            b.box((px - 0.6, 0, pz - 0.6), (px + 0.6, 0.15, pz + 0.6), (s, sc, sf)[k % 3], collide=False, shadow=False, name="Petales")
    return {"emprise": (13 * t, 12 * t), "hauteur": y + 8.5 * t}


def arbre_geant(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Grand arbre de la forêt de Konoha : tronc énorme à racines, couronne en grandes masses étagées."""
    rng = b.rng
    t = taille
    v = variant % 4
    r = (5, 4.5, 5.5, 4)[v] * t
    h = (62, 70, 56, 66)[v] * t
    tronc, tronc2 = c("tronc"), shade(c("tronc"), 0.82)
    f, fc, ff = c("feuille"), c("feuille_claire"), c("feuille_fonce")
    with b.group("ArbreGeant"):
        b.cyl((0, h / 2, 0), r, h, tronc, axis="y", name="Tronc")
        # écorce : bandes verticales plus sombres
        for k in range(4):
            yaw = 45 + k * 90 + rng.uniform(-10, 10)
            with b.at((0, 0, 0), yaw=yaw):
                b.box((-0.8, 0, r - 0.6), (0.8, h * rng.uniform(0.5, 0.8), r + 0.4), tronc2, name="Ecorce")
        # racines rayonnantes (coins posés au sol)
        for k in range(5):
            yaw = k * 72 + rng.uniform(-12, 12)
            with b.at((0, 0, 0), yaw=yaw):
                b.wedge((-1.5 * t, 0, r - 1), (1.5 * t, 6 * t, r + 6 * t), tronc2, down="+z", name="Racine")
        # branches maîtresses
        for k, (yy, yaw, long) in enumerate(((0.62, 30, 14), (0.74, 160, 12), (0.82, 260, 11))):
            with b.at((0, h * yy, 0), yaw=yaw + v * 25):
                b.box((r - 1, 0, -1.2 * t), (r + long * t, 2.2 * t, 1.2 * t), tronc, name="Branche")
                _feuilles(b, r + long * t, 1.5 * t, 0, 14 * t, 7 * t, 13 * t, ff)
                _feuilles(b, r + long * t - 1, 8.5 * t, 0.5, 9 * t, 4 * t, 8 * t, f)
        # couronne : masses étagées de plus en plus claires
        for (yy, w, hh, col, dx, dz) in ((h * 0.88, 30, 10, ff, 0, 0), (h * 0.88 + 9 * t, 24, 8, f, 1.5, -1),
                                        (h * 0.88 + 16 * t, 16, 6, fc, -1, 1), (h * 0.88 + 21 * t, 8, 4, fc, 0.5, 0)):
            _feuilles(b, dx * t, yy, dz * t, w * t, hh * t, w * t * rng.uniform(0.85, 1.0), col)
        for k in range(4):
            yaw = k * 90 + 45 + rng.uniform(-15, 15)
            with b.at((0, h * 0.88 + 3 * t, 0), yaw=yaw):
                _feuilles(b, 0, 0, 15 * t, 10 * t, 7 * t, 8 * t, (f, ff)[k % 2])
    return {"emprise": (44 * t, 44 * t), "hauteur": h * 0.88 + 25 * t}


def buisson(b, variant: int = 0) -> dict:
    v = variant % 3
    cols = (c("feuille"), c("feuille_fonce"), c("feuille_claire"))
    with b.group("Buisson"):
        _feuilles(b, 0, 0, 0, 4, 2.5, 3.5, cols[v])
        _feuilles(b, 1.5, 0, 1, 3, 3.5, 3, cols[(v + 1) % 3])
        _feuilles(b, -1.5, 0, -0.5, 2.5, 2, 2.5, cols[(v + 2) % 3])
        if v == 1:
            for x, z, col in ((0.5, -1.9, c("rouge")), (-1, 1.3, c("blanc"))):
                b.box((x - 0.3, 1.6, z - 0.3), (x + 0.3, 2.2, z + 0.3), col, collide=False, name="Fleur")
    return {"emprise": (6, 5), "hauteur": 3.5}


def rocher_deco(b, variant: int = 0) -> dict:
    rng = b.rng
    tons = [c("pave_fonce"), shade(c("pave_fonce"), 0.9), c("roche"), c("bordure")]
    with b.group("Rochers"):
        for k, (x, z, s) in enumerate(((0, 0, 3.5), (2.6, 1.2, 2.2), (-2.2, 1.5, 1.6), (0.8, -2.4, 1.4))):
            if k == 3 and variant % 2:
                continue
            b.boxc((x, s * 0.4, z), (s, s * 0.8, s * 0.9), tons[(k + variant) % len(tons)], yaw=float(rng.uniform(-30, 30)),
                   studs="top", name="Rocher")
    return {"emprise": (7, 6), "hauteur": 2.8}


def parterre_fleurs(b, variant: int = 0, largeur: float = 6, profondeur: float = 4) -> dict:
    """Parterre bordé de bois, terre, fleurs en petits cubes de couleur."""
    rng = b.rng
    w, d = largeur / 2, profondeur / 2
    fleurs = [c("rouge"), c("jaune_lampion"), c("blanc"), c("sakura"), c("toit_bleu_clair")]
    with b.group("Parterre"):
        b.box((-w, 0, -d), (w, 0.8, d), c("bois"), name="Bordure")
        b.box((-w + 0.4, 0.8, -d + 0.4), (w - 0.4, 0.9, d - 0.4), c("terre"), name="Terre")
        n = 0
        x = -w + 1.1
        while x < w - 0.9 and n < 22:
            for z in (-d / 2 + 0.2, d / 2 - 0.2):
                if n >= 22:
                    break
                hh = 1.3 + rng.uniform(0, 0.5)
                b.box((x - 0.15, 0.9, z - 0.15), (x + 0.15, hh, z + 0.15), c("feuille_fonce"), collide=False, name="Tige")
                b.box((x - 0.4, hh, z - 0.4), (x + 0.4, hh + 0.5, z + 0.4), fleurs[(n + variant) % len(fleurs)],
                      collide=False, name="Fleur")
                n += 2
            x += 1.6
    return {"emprise": (largeur, profondeur), "hauteur": 2.2}


def touffe_herbe(b, variant: int = 0) -> dict:
    col = (c("herbe_fonce"), c("feuille"), c("herbe_claire"))[variant % 3]
    with b.group("Herbe"):
        for x, z, h in ((0, 0, 1.6), (0.6, 0.4, 1.1), (-0.5, 0.3, 1.2)):
            b.box((x - 0.2, 0, z - 0.2), (x + 0.2, h, z + 0.2), col, collide=False, shadow=False, name="Brin")
    return {"emprise": (1.5, 1.5), "hauteur": 1.6}
