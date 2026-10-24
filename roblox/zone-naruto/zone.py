#!/usr/bin/env python3
"""Plan de la zone Naruto (Konoha) en style stud : assemble les assets autour du couloir de course.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course occupe x ∈ [-30, 30], bordé de trottoirs jusqu'aux façades (|x| = 40) ;
- on entre par la porte de Konoha en z = 0 et on court vers -Z : rue commerçante, puis la place
  des œufs (centre z = -262), puis le rocher des Hokage (façade en z = -304), traversé par un
  passage qui débouche sur la zone suivante en z = -364 ;
- une terrasse haute (+6) court derrière les façades, le rempart du village ferme les côtés en
  |x| = 130 et une forêt de grands arbres l'entoure.

    python zone.py                     # écrit build/parts.json (aucune dépendance à Blender)
    python zone.py --stats             # nombre de pièces par groupe
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from kit import Builder, hexrgb, shade  # noqa: E402
from palette import c  # noqa: E402
from textures import mask_rects  # noqa: E402

# ---------------------------------------------------------------------------
# Dimensions (studs)
# ---------------------------------------------------------------------------
DEMI_COULOIR = 30
X_FACADE = 40            # alignement des façades (trottoirs de 10 studs)
X_TERRASSE = 74          # bord de la terrasse haute (ruelle de service derrière les maisons)
X_TERRASSE_FOND = 108    # la terrasse recule autour de la place des œufs
H_TERRASSE = 6
X_REMPART = 130
X_FORET = 210
Z_PORTE = 0
Z_RUE = -14              # première façade
Z_FIN_RUE = -222         # dernière façade, début de la place
Z_PLACE = -262           # centre de la place des œufs
R_PLACE = 34
Z_ROCHER = -304          # façade du rocher des Hokage
PROF_ROCHER = 60         # longueur du passage dans la roche
Z_SORTIE = Z_ROCHER - PROF_ROCHER
Z_APPROCHE = 48          # sol devant la porte (côté apparition)
H_GUIRLANDE = 33         # au-dessus de ~30 studs : la caméra Roblox ne « saute » pas

VERSION = "1.0"


# ---------------------------------------------------------------------------
# Accès aux assets (avec pièce de remplacement si un module manque encore)
# ---------------------------------------------------------------------------

def _asset(module: str, fn: str):
    try:
        return getattr(importlib.import_module(f"assets.{module}"), fn)
    except (ImportError, AttributeError):
        return None


def place(b: Builder, module: str, fn: str, pos, yaw: float = 0.0, group: str | None = None, emprise=(16, 16, 16), **params) -> dict:
    """Pose un asset ; si le module n'existe pas encore, pose un bloc translucide de même emprise."""
    f = _asset(module, fn)
    with b.at(pos, yaw=yaw, group=group):
        if f is not None:
            n0 = len(b.parts)
            try:
                return f(b, **params) or {}
            except NotImplementedError:
                del b.parts[n0:]  # asset pas encore écrit : bloc d'attente ci-dessous
        w, d, h = emprise
        b.box((-w / 2, 0, -d / 2), (w / 2, h, d / 2), "#ff4fd8", transparency=0.5, name=f"ATTENTE_{module}_{fn}")
        return {"emprise": (w, d), "hauteur": h}


def face_couloir(x: float) -> float:
    """Rotation qui tourne l'avant d'un asset (-Z local) vers le couloir."""
    return -90.0 if x < 0 else 90.0


def vers_monde(x: float, z: float, yaw: float, p) -> tuple:
    """Point local d'un asset posé en (x, 0, z) avec la rotation `yaw` → coordonnées monde."""
    a = math.radians(yaw)
    return (x + p[0] * math.cos(a) + p[2] * math.sin(a), p[1], z - p[0] * math.sin(a) + p[2] * math.cos(a))


# ---------------------------------------------------------------------------
# Rangées de maisons : (fonction, largeur le long de la rue, profondeur, paramètres)
# ---------------------------------------------------------------------------

RANGEE_GAUCHE = [
    ("vide", 6, 0, {}),
    ("maisons:boutique", 24, 20, {"variant": 0}),
    ("maisons:ramen", 16, 14, {"variant": 0}),
    ("maisons:boutique", 22, 22, {"variant": 1}),
    ("maisons:maison", 20, 18, {"variant": 0}),
    ("place:entrainement", 44, 0, {}),
    ("maisons:boutique", 24, 20, {"variant": 2}),
    ("maisons:immeuble", 26, 24, {"variant": 2, "etages": 6}),
]
RANGEE_DROITE = [
    ("vide", 6, 0, {}),
    ("maisons:maison", 20, 18, {"variant": 2}),
    ("maisons:boutique", 26, 22, {"variant": 3}),
    ("maisons:immeuble", 26, 24, {"variant": 1, "etages": 5}),
    ("place:marche", 46, 0, {}),
    ("maisons:boutique", 22, 20, {"variant": 1}),
    ("maisons:ramen", 16, 14, {"variant": 1}),
    ("maisons:boutique", 26, 22, {"variant": 0}),
]


def plan_rangee(plan) -> list:
    """Calcule la position le long de la rue de chaque élément d'une rangée : (élément, z_haut, z_bas)."""
    z = Z_RUE
    out = []
    for item in plan:
        kind, larg = item[0], item[1]
        out.append((item, z, z - larg))
        z -= larg + (0 if kind == "vide" else 2)
    assert z > Z_FIN_RUE - 4, f"rangée trop longue ({z:.0f} < {Z_FIN_RUE})"
    return out


PLAN_G = plan_rangee(RANGEE_GAUCHE)
PLAN_D = plan_rangee(RANGEE_DROITE)
PLACES = {
    item[0].split(":")[1]: (-1 if plan is PLAN_G else 1, zh, zb)
    for plan in (PLAN_G, PLAN_D) for item, zh, zb in plan if item[0].startswith("place:")
}


# ---------------------------------------------------------------------------
# Sol « pixel » : une grille de couleurs fusionnée en rectangles (peu de pièces)
# ---------------------------------------------------------------------------

def sol_pixel(b: Builder, x0: float, x1: float, z0: float, z1: float, cell: float, couleur, y_haut: float = 0.0,
              epaisseur: float = 1.0, studs="top", name: str = "Sol", **kw) -> int:
    """Remplit [x0, x1] × [z0, z1] ; couleur(x, z) → (r, g, b) est évaluée au centre de chaque case."""
    nx, nz = int(round((x1 - x0) / cell)), int(round((z1 - z0) / cell))
    if nx <= 0 or nz <= 0:
        return 0
    grid = np.empty((nz, nx), dtype=object)
    for j in range(nz):
        for i in range(nx):
            grid[j, i] = tuple(couleur(x0 + (i + 0.5) * cell, z0 + (j + 0.5) * cell))
    n = 0
    for col in set(grid.reshape(-1)):
        mask = np.vectorize(lambda v, col=col: v == col)(grid)
        for (i, j, w, h) in mask_rects(mask):
            b.box((x0 + i * cell, y_haut - epaisseur, z0 + j * cell),
                  (x0 + (i + w) * cell, y_haut, z0 + (j + h) * cell), col, studs=studs, name=name, **kw)
            n += 1
    return n


def damier(a, bcol, taille: float):
    a, bcol = (hexrgb(v) if isinstance(v, str) else v for v in (a, bcol))
    return lambda x, z: a if (math.floor(x / taille) + math.floor(z / taille)) % 2 == 0 else bcol


def mosaique_place(x: float, z: float):
    """Place des œufs : rosace en spirale au centre, anneaux de dallage autour. None hors de la place."""
    dx, dz = x, z - Z_PLACE
    d = math.hypot(dx, dz)
    if d >= R_PLACE:
        return None
    if d < 15:
        if d < 2.5:
            return c("rouge")
        th = math.atan2(dz, dx) / (2 * math.pi)
        bras = (th * 6.0 + d * 0.5) % 3.0  # deux bras de spirale
        if d > 13:
            return c("rouge_fonce")
        return c("rouge") if bras < 1.05 else (c("orange_lampion") if bras < 1.5 else c("panneau"))
    if d < 17:
        return c("pave_fonce")
    return c("pave_fonce") if int((R_PLACE - d) // 5) % 2 == 0 else c("pave")


# ---------------------------------------------------------------------------
# Sol, terrasses, escaliers, rempart latéral
# ---------------------------------------------------------------------------

def sol_couloir(b: Builder) -> None:
    sable, sable2 = c("sable"), c("sable_fonce")
    pave, pave2, bord = c("pave"), c("pave_fonce"), c("bordure")

    def rue(x, z):
        return mosaique_place(x, z) or (sable if (math.floor(x / 12 + 0.5) + math.floor(z / 12)) % 2 == 0 else sable2)

    def trottoir(x, z):
        p = mosaique_place(x, z)
        if p:
            return p
        if abs(x) < DEMI_COULOIR + 1.01:
            return bord
        return pave if math.floor(z / 8) % 2 else pave2

    z_fin = Z_SORTIE - 4
    zp_bas, zp_haut = Z_PLACE - R_PLACE, Z_PLACE + R_PLACE
    with b.group("Sol/Couloir"):
        # mosaïque plus fine sur la place, cases de 4 ailleurs
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, zp_haut, Z_APPROCHE, 4, rue)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, zp_bas, zp_haut, 2, rue)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, z_fin, zp_bas, 4, rue)
    with b.group("Sol/Trottoirs"):
        for s in (-1, 1):
            xa, xb = sorted((s * DEMI_COULOIR, s * X_FACADE))
            sol_pixel(b, xa, xb, z_fin, Z_APPROCHE, 2, trottoir)


def sol_lots(b: Builder) -> None:
    """Sol entre façades et terrasse, places vertes comprises (même hauteur que le couloir)."""
    herbe, herbe2 = c("herbe"), c("herbe_fonce")
    pave, pave2 = c("pave"), c("pave_fonce")

    def couleur(x, z):
        ax = abs(x)
        p = mosaique_place(x, z)
        if p:
            return p
        for s, zh, zb in PLACES.values():
            if x * s > 0 and zb < z < zh:
                return herbe if (math.floor(ax / 8) + math.floor(z / 8)) % 2 else herbe2
        if z < Z_FIN_RUE - 6:
            return pave if (math.floor(ax / 12) + math.floor(z / 12)) % 2 else pave2
        return pave2 if ax > X_TERRASSE - 6 else pave

    with b.group("Sol/Lots"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_FACADE, s * X_TERRASSE))
            sol_pixel(b, xa, xb, Z_ROCHER + 2, Z_PORTE - 8, 2, couleur)
            xa, xb = sorted((s * X_TERRASSE, s * X_TERRASSE_FOND))
            sol_pixel(b, xa, xb, Z_ROCHER + 2, Z_FIN_RUE - 6, 4, couleur)


def mur_pierre(b: Builder, a, bb, face: str, h: float, rng, long: float = 16) -> None:
    """Mur de soutènement en blocs de pierre décalés (motif « pixel »), studs sur la face visible."""
    pierres = [c("pave"), shade(c("pave"), 0.92), c("pave_fonce"), shade(c("pave"), 1.06)]
    (x0, z0), (x1, z1) = a, bb
    le_long_x = abs(x1 - x0) > abs(z1 - z0)
    u0, u1 = sorted((x0, x1) if le_long_x else (z0, z1))
    ep = (min(z0, z1), max(z0, z1)) if le_long_x else (min(x0, x1), max(x0, x1))
    rangs = 3
    for k in range(rangs):
        y0 = -1 + k * (h + 1.6) / rangs
        y1 = y0 + (h + 1.6) / rangs
        u = u0 - (long / 2 if k % 2 else 0)
        while u < u1 - 0.01:
            ua, ub = max(u, u0), min(u + long, u1)
            if ub - ua > 0.5:
                lo = (ua, y0, ep[0]) if le_long_x else (ep[0], y0, ua)
                hi = (ub, y1, ep[1]) if le_long_x else (ep[1], y1, ub)
                b.box(lo, hi, pierres[int(rng.integers(len(pierres)))],
                      studs=(face, "Top") if k == rangs - 1 else (face,), name="MurPierre")
            u += long


def terrasse(b: Builder) -> None:
    """Terrasse haute derrière les façades : mur de soutènement, herbe en damier, escaliers."""
    herbe = damier(c("herbe"), c("herbe_fonce"), 16)
    rng = b.rng
    with b.group("Terrasses"):
        for s in (-1, 1):
            face = "Right" if s < 0 else "Left"
            for z_hi, z_lo, xb in ((Z_PORTE - 8, Z_FIN_RUE - 6, X_TERRASSE), (Z_FIN_RUE - 6, Z_ROCHER + 2, X_TERRASSE_FOND)):
                xa, xb2 = sorted((s * (xb + 2), s * X_REMPART))
                sol_pixel(b, xa, xb2, z_lo, z_hi, 4, herbe, y_haut=H_TERRASSE, epaisseur=H_TERRASSE + 1, name="Herbe")
                mur_pierre(b, (s * xb, z_hi), (s * (xb + 2), z_lo), face, H_TERRASSE, rng)
            # mur de retour là où la terrasse recule, face à la place des œufs
            mur_pierre(b, (s * X_TERRASSE, Z_FIN_RUE - 8), (s * (X_TERRASSE_FOND + 2), Z_FIN_RUE - 6), "Front", H_TERRASSE, rng)
            for z_e in (-52, -150, -204):
                escalier(b, s * X_TERRASSE, z_e, s)


def escalier(b: Builder, x_bord: float, z_c: float, s: int, largeur: float = 6) -> None:
    """Escalier de pierre le long du mur, de la ruelle (y = 0) à la terrasse (y = 6)."""
    marche = c("pave")
    with b.group("Escaliers"):
        xa, xb = sorted((x_bord, x_bord - s * 3))
        for k in range(H_TERRASSE):
            za = z_c - largeur / 2 - (H_TERRASSE - k) * 1.5
            b.box((xa, 0, za), (xb, k + 1, za + 1.5), shade(marche, 1.0 if k % 2 else 0.94), studs="top", name="Marche")
        b.box((xa, 0, z_c - largeur / 2), (xb, H_TERRASSE, z_c + largeur / 2), marche, studs="top", name="Palier")


def rempart_lateral(b: Builder, s: int) -> None:
    """Mur d'enceinte le long du village (prolonge celui de la porte), chaperon de tuiles et contreforts."""
    rng = b.rng
    tons = [c("rempart"), shade(c("rempart"), 0.94), c("rempart_fonce"), shade(c("rempart"), 1.05)]
    h, ep = 32, 7
    xa, xb = sorted((s * X_REMPART, s * (X_REMPART + ep)))
    face = "Right" if s < 0 else "Left"
    with b.group("Rempart/" + ("Gauche" if s < 0 else "Droite")):
        y = 0.0
        for k in range(4):
            z = Z_PORTE - 4 + (8 if k % 2 else 0)
            while z > Z_ROCHER + 0.01:
                za, zb = max(z - 16, Z_ROCHER), min(z, Z_PORTE - 4)
                if zb - za > 0.4:
                    b.box((xa, y, za), (xb, y + 8, zb), tons[int(rng.integers(len(tons)))], studs=(face,), name="Bloc")
                z -= 16
            y += 8
        tuile = c("rempart_tuile")
        b.box((xa - 1, h, Z_ROCHER), (xb + 1, h + 1.2, Z_PORTE - 4), shade(tuile, 0.9), name="Chaperon")
        b.box((xa - 1.6, h + 1.2, Z_ROCHER), (xb + 1.6, h + 2.4, Z_PORTE - 4), tuile, studs="top", name="Tuiles")
        for zc in range(-30, int(Z_ROCHER) + 10, -48):
            ca, cb = sorted((s * X_REMPART, s * (X_REMPART - 3)))
            b.box((ca, H_TERRASSE, zc - 2), (cb, 22, zc + 2), tons[2], name="Contrefort")
            b.wedge((ca, 22, zc - 2), (cb, 27, zc + 2), tons[1], down="+x" if s < 0 else "-x", name="Contrefort")


def sol_exterieur(b: Builder) -> None:
    """Herbe hors les murs (forêt) et abords de la porte."""
    with b.group("Sol/Foret"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_REMPART, s * X_FORET))
            sol_pixel(b, xa, xb, Z_SORTIE, Z_APPROCHE, 16, damier(c("herbe_fonce"), shade(c("herbe_fonce"), 0.9), 32))
    with b.group("Sol/Abords"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_FACADE, s * X_REMPART))
            sol_pixel(b, xa, xb, Z_PORTE, Z_APPROCHE, 8, damier(c("herbe"), c("herbe_fonce"), 16))
            sol_pixel(b, xa, xb, Z_PORTE - 8, Z_PORTE, 4, lambda x, z: c("pave_fonce"))


# ---------------------------------------------------------------------------
# Places et petits décors
# ---------------------------------------------------------------------------

def terrain_entrainement(b: Builder, x: float, z: float) -> None:
    """Le terrain d'entraînement : trois souches, la stèle et un cerisier."""
    with b.at((x, 0, z), yaw=face_couloir(x), group="Places/Entrainement"):
        place(b, "mobilier", "poteaux_entrainement", (0, 0, 2), group="Souches", emprise=(14, 4, 5))
        with b.group("Stele"):
            b.box((9, 0, 4), (15, 1, 8), c("pave_fonce"), studs="top", name="Socle")
            b.box((11, 1, 5.4), (13, 7, 6.6), c("metal"), name="Lame")
            b.wedge((11, 7, 5.4), (12, 9, 6.6), c("metal"), down="-x", name="Pointe")
            b.wedge((12, 7, 5.4), (13, 9, 6.6), c("metal"), down="+x", name="Pointe")
        place(b, "nature", "cerisier", (-12, 0, 8), group="Cerisier", variant=1, taille=1.3, emprise=(10, 10, 16))
        place(b, "nature", "buisson", (16, 0, -4), group="Buisson")
        place(b, "nature", "arbre", (6, 0, 14), group="Arbre", variant=3, taille=1.1, emprise=(10, 10, 16))
        place(b, "mobilier", "cloture", (-8, 0, 16), group="Cloture", longueur=24, emprise=(24, 1, 3))


def place_marche(b: Builder, x: float, z: float) -> None:
    """Jardin du marché : étals, cerisiers, lanternes de pierre, banc."""
    with b.at((x, 0, z), yaw=face_couloir(x), group="Places/Marche"):
        # repère local : avant = -Z (vers le couloir), X le long de la rue
        for i, dx in enumerate((-13, 0, 13)):
            place(b, "mobilier", "etal_marche", (dx, 0, 0), variant=i, group=f"Etal{i + 1}", emprise=(10, 8, 9))
        place(b, "nature", "cerisier", (-14, 0, 14), variant=0, taille=1.4, group="Cerisier1", emprise=(12, 12, 18))
        place(b, "nature", "cerisier", (13, 0, 15), variant=2, taille=1.2, group="Cerisier2", emprise=(12, 12, 18))
        place(b, "mobilier", "lanterne_pierre", (-4, 0, 11), variant=0, group="Lanterne1", emprise=(3, 3, 6))
        place(b, "mobilier", "lanterne_pierre", (4, 0, 11), variant=1, group="Lanterne2", emprise=(3, 3, 6))
        place(b, "mobilier", "banc", (0, 0, 17), yaw=180, group="Banc", emprise=(6, 2, 2))
        place(b, "nature", "parterre_fleurs", (0, 0, 6), group="Fleurs", largeur=10, profondeur=3, emprise=(10, 3, 1))
        place(b, "mobilier", "distributeur", (21, 0, 8), yaw=-90, group="Distributeur", emprise=(3, 3, 7))


def balancoire(b: Builder, x: float, z: float, yaw: float) -> None:
    """L'arbre à la balançoire (clin d'œil à l'Académie)."""
    with b.at((x, 0, z), yaw=yaw, group="Places/Balancoire"):
        place(b, "nature", "arbre", (0, 0, 0), variant=0, taille=1.4, group="Arbre", emprise=(10, 10, 18))
        corde = c("bois_fonce")
        with b.group("Balancoire"):
            b.box((1.4, 9.2, -0.5), (7.0, 10.0, 0.5), c("tronc"), name="Branche")
            for dx in (-1.6, 1.6):
                b.box((4.6 + dx - 0.1, 3, -0.1), (4.6 + dx + 0.1, 9.2, 0.1), corde, collide=False, name="Corde")
            b.box((2.7, 2.6, -0.7), (6.5, 3.0, 0.7), c("bois_clair"), name="Planche")


def rangee(b: Builder, s: int, plan) -> list:
    """Pose une rangée de bâtiments le long du couloir (s = -1 gauche, +1 droite)."""
    poses = []
    cote = "Gauche" if s < 0 else "Droite"
    for i, ((kind, larg, prof, params), zh, zb) in enumerate(plan):
        zc = (zh + zb) / 2
        if kind == "vide":
            continue
        if kind == "place:entrainement":
            terrain_entrainement(b, s * (X_FACADE + 12), zc)
            continue
        if kind == "place:marche":
            place_marche(b, s * (X_FACADE + 6), zc)
            continue
        mod, fn = kind.split(":")
        x = s * (X_FACADE + prof / 2)
        kw = dict(params)
        if fn in ("boutique", "maison", "immeuble"):
            kw.setdefault("largeur", larg)
            kw.setdefault("profondeur", prof)
        info = place(b, mod, fn, (x, 0, zc), yaw=face_couloir(x), group=f"Rue/{cote}/{i:02d}_{fn.capitalize()}",
                     emprise=(larg, prof, 18), **kw)
        poses.append((x, zc, larg, prof, info))
    return poses


def rangee_terrasse(b: Builder, s: int) -> None:
    """Deuxième rang sur la terrasse : immeubles plus hauts qui dépassent des toits, arbres entre eux."""
    cote = "Gauche" if s < 0 else "Droite"
    plan = [
        (-30, "maisons:immeuble", 26, 24, {"variant": 1 if s < 0 else 2, "etages": 6}),
        (-66, "nature:arbre", 0, 0, {"variant": 1, "taille": 1.4}),
        (-96, "maisons:maison", 22, 20, {"variant": 3 if s < 0 else 0}),
        (-130, "maisons:immeuble", 24, 24, {"variant": 3 if s < 0 else 0, "etages": 5}),
        (-166, "nature:arbre", 0, 0, {"variant": 2, "taille": 1.6}),
        (-198, "maisons:boutique", 24, 22, {"variant": 2 if s < 0 else 1}),
    ]
    for i, (z, kind, larg, prof, params) in enumerate(plan):
        mod, fn = kind.split(":")
        if mod == "nature":
            for k, dx in enumerate((0, 20, 38)):
                place(b, mod, fn, (s * (X_TERRASSE + 10 + dx), H_TERRASSE, z + (k % 2) * 8), group=f"Terrasse/{cote}/{i:02d}_Arbres",
                      emprise=(10, 10, 18), **{**params, "variant": (params["variant"] + k) % 4})
            continue
        x = s * (X_TERRASSE + 4 + prof / 2)
        kw = dict(params)
        kw.setdefault("largeur", larg)
        kw.setdefault("profondeur", prof)
        place(b, mod, fn, (x, H_TERRASSE, z), yaw=face_couloir(x), group=f"Terrasse/{cote}/{i:02d}_{fn.capitalize()}",
              emprise=(larg, prof, 24), **kw)
        place(b, "nature", "arbre", (s * (X_REMPART - 10), H_TERRASSE, z - 4), group=f"Terrasse/{cote}/{i:02d}_Jardin",
              variant=(i + 1) % 4, taille=1.2, emprise=(10, 10, 16))


def lampions_couloir(b: Builder) -> None:
    """Guirlandes de lampions au-dessus du couloir (au-dessus de 30 studs), sur des mâts de trottoir."""
    f = _asset("mobilier", "guirlande_lampions")
    zs = (-36, -86, -186, -212)
    for i, z in enumerate(zs):
        with b.group(f"Lampions/Guirlande{i + 1}"):
            for s in (-1, 1):
                with b.at((s * 35, 0, z)):
                    b.box((-0.6, 0, -0.6), (0.6, H_GUIRLANDE + 2, 0.6), c("bois_fonce"), name="Mat")
                    b.box((-0.9, 0, -0.9), (0.9, 1.2, 0.9), c("pave_fonce"), studs="top", name="Pied")
                    xa, xb = sorted((0.0, -s * 2.4))
                    b.box((xa, H_GUIRLANDE - 0.4, -0.4), (xb, H_GUIRLANDE + 0.4, 0.4), c("bois_fonce"), name="Potence")
                    b.box((-0.8, H_GUIRLANDE + 2, -0.8), (0.8, H_GUIRLANDE + 2.6, 0.8), c("toit_rouge"), name="Chapeau")
            if f:
                f(b, (-32.4, H_GUIRLANDE, z), (32.4, H_GUIRLANDE, z), n=9, creux=3.0, variant=i)
            else:
                b.box((-32, H_GUIRLANDE - 1, z - 0.2), (32, H_GUIRLANDE - 0.6, z + 0.2), "#ff4fd8", transparency=0.5, name="ATTENTE_guirlande")


def lignes_electriques(b: Builder) -> None:
    """Poteaux électriques sur les trottoirs, reliés par des câbles affaissés."""
    fpole = _asset("mobilier", "poteau_electrique")
    fcable = _asset("mobilier", "cable")
    zs = [-60, -110, -160, -204]
    for s in (-1, 1):
        prec = None
        for i, z in enumerate(zs):
            x = s * 37.5
            yaw = face_couloir(x)
            with b.at((x, 0, z), yaw=yaw, group=f"Electricite/{'G' if s < 0 else 'D'}{i + 1}"):
                info = fpole(b, variant=i % 3) if fpole else {}
                if not fpole:
                    b.box((-0.6, 0, -0.6), (0.6, 24, 0.6), "#ff4fd8", transparency=0.5, name="ATTENTE_poteau")
            att = [vers_monde(x, z, yaw, p) for p in (info.get("attaches") or [(0, 22, 0)])][:3]
            if prec and fcable:
                with b.group(f"Electricite/Cables{'G' if s < 0 else 'D'}{i}"):
                    for a, bb in zip(prec, att):
                        fcable(b, a, bb, creux=2.0)
            prec = att


def details_rue(b: Builder, poses_g, poses_d) -> None:
    """Petits objets devant les façades (jamais dans le couloir)."""
    rng = np.random.default_rng(7)
    props = ["caisses", "tonneaux", "boite_lettres", "panneau_kanji", "reverbere", "caisses", "tonneaux"]
    textes = ["茶", "団子", "薬", "本", "宿", "花", "忍具"]
    interdits = [-36, -86, -186, -212, -60, -110, -160, -204]  # mâts et poteaux
    k = 0
    for s, poses in ((-1, poses_g), (1, poses_d)):
        for (x, zc, larg, prof, info) in poses:
            if rng.random() < 0.25:
                continue
            fn = props[k % len(props)]
            zp = zc + rng.uniform(-larg / 2 + 3, larg / 2 - 3)
            if min(abs(zp - zi) for zi in interdits) < 4:
                zp += 6
            xp = s * (X_FACADE - 2.5)
            kw = {"texte": textes[k % len(textes)]} if fn == "panneau_kanji" else {}
            place(b, "mobilier", fn, (xp, 0, zp), yaw=face_couloir(xp), group=f"Details/{fn}{k}", variant=k % 3, emprise=(3, 3, 4), **kw)
            k += 1


def fond_place(b: Builder) -> None:
    """Place des œufs : résidence du Hokage à droite, tour bleue et balançoire à gauche, lanternes."""
    place(b, "residence", "residence_hokage", (76, 0, -262), yaw=118, group="Monuments/ResidenceHokage", emprise=(60, 60, 30))
    place(b, "residence", "tour_bleue", (-60, 0, -270), yaw=-112, group="Monuments/TourBleue", emprise=(20, 20, 60))
    balancoire(b, -86, -238, yaw=-120)
    i = 0
    for s in (-1, 1):
        for dz in (26, 10, -10, -24):
            z = Z_PLACE + dz
            x = s * max(math.sqrt(max(R_PLACE ** 2 - dz ** 2, 0)) + 3, DEMI_COULOIR + 6)
            place(b, "mobilier", "lanterne_pierre", (x, 0, z), yaw=face_couloir(x), group=f"Place/Lanterne{i}", variant=i % 2, emprise=(3, 3, 6))
            i += 1
    for x, z, v in ((-44, -294, 0), (48, -232, 1), (-96, -292, 2)):
        place(b, "nature", "arbre", (x, 0, z), variant=v, taille=1.3, group=f"Place/Arbre{v}", emprise=(10, 10, 16))


def foret(b: Builder) -> None:
    """Grands arbres hors les murs : ils dépassent du rempart et cadrent le ciel."""
    rng = np.random.default_rng(42)
    k = 0
    for s in (-1, 1):
        z = Z_PORTE - 8
        while z > Z_ROCHER + 20:
            x = s * (X_REMPART + 30 + rng.uniform(-6, 16))
            place(b, "nature", "arbre_geant", (x, 0, z), yaw=float(rng.uniform(0, 360)),
                  group=f"Foret/{'Gauche' if s < 0 else 'Droite'}/Arbre{k:02d}", variant=k % 4,
                  taille=float(rng.uniform(0.85, 1.15)), emprise=(30, 30, 80))
            z -= rng.uniform(52, 66)
            k += 1
        for dz, dx in ((18, 60), (34, 96)):
            place(b, "nature", "arbre", (s * dx, 0, Z_PORTE + dz), group=f"Abords/{'Gauche' if s < 0 else 'Droite'}{dx}",
                  variant=(dx // 32) % 4, taille=1.5, emprise=(10, 10, 18))


def reperes(b: Builder) -> None:
    """Pièces invisibles utiles au jeu : zone des œufs, entrée, sortie, couloir."""
    inv = dict(transparency=1.0, collide=False, shadow=False)
    with b.group("Reperes"):
        b.box((-R_PLACE, 0, Z_PLACE - R_PLACE), (R_PLACE, 1, Z_PLACE + R_PLACE), "#ffffff", name="ZoneOeufs", **inv)
        b.box((-DEMI_COULOIR, 0, Z_PORTE + 18), (DEMI_COULOIR, 1, Z_PORTE + 24), "#ffffff", name="Entree", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE - 4), (DEMI_COULOIR, 1, Z_SORTIE + 2), "#ffffff", name="Sortie", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE), (DEMI_COULOIR, 1, Z_PORTE), "#ffffff", name="Couloir", **inv)


# ---------------------------------------------------------------------------

def decouper(b: Builder, prefixes=("Sol/", "Terrasses", "Rempart/", "Monuments/RocherHokage", "Monuments/Porte"),
             taille: float = 64) -> None:
    """Range les pièces des grands ensembles dans des sous-modèles de 64 × 64 studs (streaming Roblox)."""
    for p in b.parts:
        if p.group.startswith(prefixes):
            i, j = math.floor(p.pos[0] / taille), math.floor(p.pos[2] / taille)
            racine = "/".join(p.group.split("/")[:2])
            reste = p.group[len(racine):]
            p.group = f"{racine}/Bloc_{i:+d}_{j:+d}{reste}"


def build_zone(seed: int = 7) -> Builder:
    b = Builder(seed=seed)
    sol_couloir(b)
    sol_lots(b)
    sol_exterieur(b)
    terrasse(b)
    for s in (-1, 1):
        rempart_lateral(b, s)
    place(b, "porte", "porte_konoha", (0, 0, Z_PORTE), group="Monuments/Porte", emprise=(260, 12, 46),
          ouverture=72, hauteur=46, mur=X_REMPART)
    place(b, "rocher", "rocher_hokage", (0, 0, Z_ROCHER), group="Monuments/RocherHokage", emprise=(420, 60, 150),
          passage=68, hauteur_passage=48, largeur=2 * X_FORET, profondeur=PROF_ROCHER, hauteur=150)
    poses_g = rangee(b, -1, PLAN_G)
    poses_d = rangee(b, 1, PLAN_D)
    for s in (-1, 1):
        rangee_terrasse(b, s)
    fond_place(b)
    lampions_couloir(b)
    lignes_electriques(b)
    details_rue(b, poses_g, poses_d)
    foret(b)
    reperes(b)
    decouper(b)
    return b


def couloir_libre(b: Builder) -> list:
    """Liste ce qui encombre le couloir de course au sol (hors sol, porte et repères)."""
    gene = []
    for p in b.parts:
        if not p.collide or p.group.startswith(("Sol", "Reperes")):
            continue
        R = np.asarray(p.rot).reshape(3, 3)
        half = np.abs(R) @ (np.asarray(p.size) / 2)
        lo, hi = np.asarray(p.pos) - half, np.asarray(p.pos) + half
        if lo[0] < DEMI_COULOIR - 0.05 and hi[0] > -DEMI_COULOIR + 0.05 and lo[1] < 12 and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            gene.append((p.group, p.name, [round(v, 1) for v in lo], [round(v, 1) for v in hi]))
    return gene


def meta() -> dict:
    return {"nom": "ZoneNaruto", "version": VERSION, "largeur_couloir": 2 * DEMI_COULOIR,
            "longueur": -Z_SORTIE, "spawn": [0, 0, Z_PORTE + 32]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / "build" / "parts.json"))
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    b = build_zone()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    b.save_json(out, meta=meta())
    attente = sorted({p.name for p in b.parts if p.name.startswith("ATTENTE_")})
    gene = couloir_libre(b)
    print(json.dumps({"pieces": len(b.parts), "fichier": str(out), "en_attente": attente,
                      "couloir_encombre": gene[:20], "nb_couloir_encombre": len(gene)}, ensure_ascii=False))
    if args.stats:
        for k, v in b.stats().items():
            print(f"{v:6d}  {k}")


if __name__ == "__main__":
    main()
