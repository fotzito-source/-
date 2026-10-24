#!/usr/bin/env python3
"""Plan de la zone Demon Slayer (village de l'ère Taishō et glycines) en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course occupe x ∈ [-30, 30], bordé de trottoirs jusqu'aux façades (|x| = 40) ;
- on entre sous le grand torii en z = 0 et on court vers -Z : village de l'ère Taishō (jusqu'à -150),
  allée des glycines sous des arches fleuries (-156 → -292), place des œufs entourée de piliers
  vermillon et du sanctuaire (centre z = -334), puis la montagne aux glycines (façade en z = -376),
  traversée par une gorge et un tunnel de torii jusqu'à la zone suivante (z = -444) ;
- un train à vapeur stationne derrière le village, des falaises bleu-violet couronnées de glycines
  ferment les côtés (|x| ≥ 130).

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
X_RUELLE = 70            # ruelle derrière la première rangée du village
X_FALAISE = 130          # début des falaises latérales
X_FOND = 200
Z_PORTE = 0
Z_RUE = -16              # première façade
Z_FIN_VILLAGE = -150
Z_GLYCINES = -154        # début de l'allée des glycines
Z_FIN_GLYCINES = -294
Z_PLACE = -334           # centre de la place des œufs
R_PLACE = 34
Z_MONTAGNE = -376        # façade de la montagne
PROF_MONTAGNE = 68       # longueur de la gorge (tunnel de torii)
Z_SORTIE = Z_MONTAGNE - PROF_MONTAGNE
Z_APPROCHE = 40          # sol devant le torii (côté apparition)
H_GUIRLANDE = 37         # fil des guirlandes : les lampions restent au-dessus de 30 studs (caméra Roblox)

VERSION = "1.0"


# ---------------------------------------------------------------------------
# Accès aux assets (avec bloc d'attente si un module manque encore)
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
                del b.parts[n0:]
        w, d, h = emprise
        b.box((-w / 2, 0, -d / 2), (w / 2, h, d / 2), "#ff4fd8", transparency=0.5, name=f"ATTENTE_{module}_{fn}")
        return {"emprise": (w, d), "hauteur": h}


def face_couloir(x: float) -> float:
    """Rotation qui tourne l'avant d'un asset (-Z local) vers le couloir."""
    return -90.0 if x < 0 else 90.0


# ---------------------------------------------------------------------------
# Sol « pixel »
# ---------------------------------------------------------------------------

def sol_pixel(b: Builder, x0: float, x1: float, z0: float, z1: float, cell: float, couleur, y_haut: float = 0.0,
              epaisseur: float = 1.0, studs="top", name: str = "Sol", **kw) -> int:
    """Remplit [x0, x1] × [z0, z1] ; couleur(x, z) → (r, g, b) évaluée au centre de chaque case, cases fusionnées."""
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
    """Place des œufs : fleur de glycine stylisée au centre (5 pétales), anneaux de dallage. None hors de la place."""
    dx, dz = x, z - Z_PLACE
    d = math.hypot(dx, dz)
    if d >= R_PLACE:
        return None
    if d < 3:
        return c("or")
    if d < 14:
        th = math.atan2(dz, dx)
        petale = abs(math.cos(2.5 * th)) ** 2 * 11 + 3   # rayon des 5 pétales
        if d < petale:
            return c("glycine") if d < petale - 2.5 else c("glycine_fonce")
        return c("pierre_claire")
    if d < 16:
        return c("pierre_fonce")
    return c("pierre_fonce") if int((R_PLACE - d) // 5) % 2 == 0 else c("pierre")


def sol_couloir(b: Builder) -> None:
    gr, gr2 = c("gravier"), shade(c("gravier"), 0.93)
    pc, p, pf, bord = c("pierre_claire"), c("pierre"), c("pierre_fonce"), c("bordure")
    mousse = c("mousse")

    def couloir(x, z):
        m = mosaique_place(x, z)
        if m:
            return m
        if z > Z_GLYCINES:      # village : terre battue en grand damier doux
            return gr if (math.floor(x / 12 + 0.5) + math.floor(z / 12)) % 2 == 0 else gr2
        if z > Z_MONTAGNE:      # allée et place : dalles posées en quinconce, bords moussus
            if abs(x) > DEMI_COULOIR - 2 and math.floor(z / 6) % 3 == 0:
                return mousse
            rang = math.floor(z / 6)
            decal = 6 if rang % 2 else 0
            return pc if (math.floor((x + decal) / 12) + rang) % 2 == 0 else p
        return pf if math.floor(z / 8) % 2 else shade(pf, 0.95)   # gorge : grandes dalles sombres

    def trottoir(x, z):
        m = mosaique_place(x, z)
        if m:
            return m
        ax = abs(x)
        if ax < DEMI_COULOIR + 1.01:
            return bord
        if Z_FIN_GLYCINES < z < Z_GLYCINES:   # sous les glycines : gravier et mousse
            return mousse if (math.floor(z / 10) + math.floor(ax / 4)) % 4 == 0 else gr
        return pf if math.floor(z / 8) % 2 else p

    z_fin = Z_SORTIE - 4
    zp_bas, zp_haut = Z_PLACE - R_PLACE, Z_PLACE + R_PLACE
    with b.group("Sol/Couloir"):
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, Z_GLYCINES, Z_APPROCHE, 4, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, zp_haut, Z_GLYCINES, 2, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, zp_bas, zp_haut, 2, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, z_fin, zp_bas, 4, couloir)
    with b.group("Sol/Trottoirs"):
        for s in (-1, 1):
            xa, xb = sorted((s * DEMI_COULOIR, s * X_FACADE))
            sol_pixel(b, xa, xb, z_fin, Z_APPROCHE, 2, trottoir)


def sol_cotes(b: Builder) -> None:
    """Sol entre les façades et les falaises : herbe vert-bleu, ruelle, gravier blanc du sanctuaire."""
    h, hf = c("herbe"), c("herbe_fonce")
    terre, gr = c("terre"), c("gravier")

    def couleur(x, z):
        ax = abs(x)
        m = mosaique_place(x, z)
        if m:
            return m
        if Z_MONTAGNE < z < Z_FIN_GLYCINES and ax < 112:      # cour du sanctuaire : gravier clair ratissé
            return gr if math.floor(z / 4) % 2 else shade(gr, 0.95)
        if z > Z_FIN_VILLAGE and X_RUELLE <= ax < X_RUELLE + 4:  # ruelle de service
            return terre
        return h if (math.floor(x / 16) + math.floor(z / 16)) % 2 == 0 else hf

    with b.group("Sol/Cotes"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_FACADE, s * X_FALAISE))
            sol_pixel(b, xa, xb, Z_MONTAGNE, Z_PORTE - 8, 4, couleur)
    with b.group("Sol/Abords"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_FACADE, s * X_FOND))
            sol_pixel(b, xa, xb, Z_PORTE - 8, Z_APPROCHE, 8, damier(h, hf, 16))
        for s in (-1, 1):
            xa, xb = sorted((s * X_FALAISE, s * X_FOND))
            sol_pixel(b, xa, xb, Z_MONTAGNE, Z_PORTE - 8, 16, damier(hf, shade(hf, 0.9), 32))


def falaises_laterales(b: Builder) -> None:
    """Falaises bleu-violet en gradins, couronnées de glycines, qui ferment la vallée des deux côtés."""
    rng = np.random.default_rng(5)
    tons = [c("roche"), c("roche_claire"), c("roche_fonce")]
    glyc = [c("glycine_fonce"), c("glycine"), c("glycine_claire"), c("glycine_pale")]
    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        z = Z_PORTE - 8
        k = 0
        z_fin = Z_MONTAGNE + 24   # la montagne déborde vers l'avant : les falaises s'arrêtent avant
        while z > z_fin + 0.01:
            l = min(16, z - z_fin)
            with b.group(f"Falaises/{cote}"):
                base = 8 + 6 * math.sin(k * 0.7) + rng.uniform(0, 4)
                gradins = ((X_FALAISE, X_FALAISE + 16, base),
                           (X_FALAISE + 16, X_FALAISE + 36, base + 12 + rng.uniform(0, 8)),
                           (X_FALAISE + 36, X_FOND, base + 26 + rng.uniform(0, 12)))
                for gi, (xa_, xb_, hg) in enumerate(gradins):
                    xa, xb = sorted((s * xa_, s * xb_))
                    hg = round(hg)
                    b.box((xa, 0, z - l), (xb, hg, z), tons[(k + gi) % 3], studs="top", name="Gradin")
                    # strate claire en haut du gradin, côté vallée
                    fa = s * xa_
                    sa, sb = sorted((fa, fa + s * 1.0))
                    b.box((sa - (0.2 if s > 0 else 0), hg - 2, z - l), (sb + (0.2 if s < 0 else 0), hg - 1, z), c("roche_claire"),
                          collide=False, name="Strate")
                    # glycines qui débordent du rebord : masse + cascades
                    if (k + gi) % 2 == 0 and gi < 2:
                        za = z - l * rng.uniform(0.15, 0.4)
                        wl = rng.uniform(5, 9)
                        ma, mb = sorted((fa - s * 1.5, fa + s * 5))
                        b.box((ma, hg, za - wl), (mb, hg + 2.5, za), glyc[1], studs="top", collide=False, name="Glycine")
                        for q in range(2):
                            zq = za - 1.5 - q * (wl - 3)
                            long_ = rng.uniform(3, 7)
                            ca, cb = sorted((fa - s * 1.2, fa - s * 0.2))
                            for t, col in enumerate(glyc[1:]):
                                y1 = hg + 0.5 - t * long_ / 3
                                b.box((ca, y1 - long_ / 3, zq - 0.6), (cb, y1, zq + 0.6), col, collide=False, shadow=False, name="Cascade")
            z -= l
            k += 1


# ---------------------------------------------------------------------------
# Village
# ---------------------------------------------------------------------------

RANGEE_GAUCHE = [
    ("batiments:machiya", 22, 18, {"variant": 0}),
    ("batiments:maison_the", 16, 12, {"variant": 0}),
    ("batiments:machiya", 20, 18, {"variant": 1}),
    ("batiments:kura", 12, 10, {"variant": 0}),
    ("batiments:auberge", 28, 24, {"variant": 0}),
    ("batiments:yatai", 8, 5, {"variant": 0}),
]
RANGEE_DROITE = [
    ("batiments:auberge", 28, 24, {"variant": 1}),
    ("batiments:machiya", 22, 18, {"variant": 2}),
    ("batiments:maison_the", 16, 12, {"variant": 1}),
    ("batiments:kura", 12, 10, {"variant": 1}),
    ("batiments:machiya", 24, 18, {"variant": 3}),
    ("batiments:yatai", 8, 5, {"variant": 1}),
]


def rangee(b: Builder, s: int, plan) -> list:
    """Aligne une rangée de bâtiments du village le long du couloir."""
    cote = "Gauche" if s < 0 else "Droite"
    z = Z_RUE
    poses = []
    for i, (kind, larg, prof, params) in enumerate(plan):
        zc = z - larg / 2
        mod, fn = kind.split(":")
        kw = dict(params)
        if fn in ("machiya", "auberge"):
            kw.setdefault("largeur", larg)
            kw.setdefault("profondeur", prof)
        x = s * (X_FACADE + prof / 2)
        info = place(b, mod, fn, (x, 0, zc), yaw=face_couloir(x), group=f"Village/{cote}/{i:02d}_{fn.capitalize()}",
                     emprise=(larg, prof, 16), **kw)
        poses.append((x, zc, larg, prof, info))
        z -= larg + 3
    assert z > Z_FIN_VILLAGE - 2, f"rangée trop longue ({z})"
    return poses


def arriere_village(b: Builder) -> None:
    """Deuxième plan du village : train à vapeur à gauche, maisons, kura, étang et bambous à droite."""
    place(b, "montagne", "train_vapeur", (-104, 0, -92), group="Village/Train", emprise=(10, 110, 14), voitures=3)
    for i, (x, z, kind, v) in enumerate(((-82, -30, "bambous", 0), (-84, -66, "bambous", 1), (-80, -118, "bambous", 2),
                                         (-84, -146, "pin", 0), (-128, -40, "pin", 1), (-124, -150, "bambous", 3))):
        place(b, "glycines", kind, (x, 0, z), group=f"Village/ArriereG/{i:02d}_{kind}", variant=v, emprise=(10, 10, 22))
    place(b, "mobilier", "cloture_bambou", (-76, 0, -84), yaw=90, group="Village/ArriereG/Cloture", longueur=110, emprise=(110, 1, 4))
    # côté droit : seconde rangée tournée vers le couloir, étang, pins
    for i, (z, kind, larg, prof, v) in enumerate(((-34, "machiya", 22, 18, 2), (-70, "kura", 12, 10, 2), (-138, "machiya", 20, 18, 0))):
        x = 86 + prof / 2
        kw = {"largeur": larg, "profondeur": prof} if kind == "machiya" else {}
        place(b, "batiments", kind, (x, 0, z), yaw=90, group=f"Village/ArriereD/{i:02d}_{kind}", variant=v, emprise=(larg, prof, 14), **kw)
    with b.group("Village/Etang"):
        cx, cz = 100, -104
        sol_pixel(b, cx - 14, cx + 14, cz - 12, cz + 12, 2,
                  lambda x, z: c("eau") if ((x - cx) / 13) ** 2 + ((z - cz) / 11) ** 2 < 1 else
                  (c("pierre_fonce") if ((x - cx) / 14) ** 2 + ((z - cz) / 12) ** 2 < 1 else c("herbe")),
                  y_haut=0.2, epaisseur=0.4, name="Etang")
    for i, (x, z, kind, v) in enumerate(((84, -96, "rocher_deco", 0), (116, -118, "pin", 2), (120, -60, "bambous", 1),
                                         (118, -150, "pin", 3), (112, -20, "bambous", 2))):
        place(b, "glycines", kind, (x, 0, z), group=f"Village/ArriereD/{i + 3:02d}_{kind}", variant=v, emprise=(8, 8, 18))


def lampions_village(b: Builder) -> None:
    """Guirlandes de lampions au-dessus de la rue du village (au-dessus de 30 studs)."""
    f = _asset("mobilier", "guirlande_lampions")
    for i, z in enumerate((-30, -76, -122)):
        with b.group(f"Lampions/Guirlande{i + 1}"):
            for s in (-1, 1):
                with b.at((s * 35, 0, z)):
                    b.box((-0.6, 0, -0.6), (0.6, H_GUIRLANDE + 2, 0.6), c("bois_fonce"), name="Mat")
                    b.box((-0.9, 0, -0.9), (0.9, 1.2, 0.9), c("pierre_fonce"), studs="top", name="Pied")
                    xa, xb = sorted((0.0, -s * 2.4))
                    b.box((xa, H_GUIRLANDE - 0.4, -0.4), (xb, H_GUIRLANDE + 0.4, 0.4), c("bois_fonce"), name="Potence")
                    b.box((-0.8, H_GUIRLANDE + 2, -0.8), (0.8, H_GUIRLANDE + 2.6, 0.8), c("tuile"), name="Chapeau")
            if f:
                f(b, (-32.4, H_GUIRLANDE, z), (32.4, H_GUIRLANDE, z), n=9, creux=2.5, variant=i)


def details_village(b: Builder, poses_g, poses_d) -> None:
    """Réverbères à gaz, bancs, tonneaux, panneaux sur les trottoirs (jamais dans le couloir)."""
    for s in (-1, 1):
        for i, z in enumerate((-50, -100, -146)):
            x = s * 37.5
            place(b, "mobilier", "reverbere_gaz", (x, 0, z), yaw=face_couloir(x), group=f"Details/Reverbere{'G' if s < 0 else 'D'}{i}",
                  variant=i % 3, emprise=(2, 2, 14))
    rng = np.random.default_rng(3)
    props = ["tonneaux", "caisses", "panneau_kanji", "banc_rouge", "lampion_poteau"]
    textes = ["茶", "団子", "蕎麦", "甘味", "宿", "呉服"]
    interdits = [-30, -76, -122, -50, -100, -146]
    k = 0
    for s, poses in ((-1, poses_g), (1, poses_d)):
        for (x, zc, larg, prof, info) in poses:
            if larg < 12:
                continue
            fn = props[k % len(props)]
            zp = zc + rng.uniform(-larg / 2 + 3, larg / 2 - 3)
            if min(abs(zp - zi) for zi in interdits) < 4:
                zp += 6
            xp = s * (X_FACADE - 2.5)
            kw = {"texte": textes[k % len(textes)]} if fn == "panneau_kanji" else {}
            place(b, "mobilier", fn, (xp, 0, zp), yaw=face_couloir(xp), group=f"Details/{fn}{k}", variant=k % 3, emprise=(3, 3, 4), **kw)
            k += 1


# ---------------------------------------------------------------------------
# Allée des glycines
# ---------------------------------------------------------------------------

def allee_glycines(b: Builder) -> None:
    """Arches de glycines au-dessus du couloir, glycines, treilles, lanternes de pierre, bambous."""
    zs_arches = (-170, -206, -242, -278)
    for i, z in enumerate(zs_arches):
        place(b, "glycines", "arche_glycines", (0, 0, z), group=f"Glycines/Arche{i + 1}", emprise=(76, 8, 40),
              portee=80, hauteur=34, variant=i)
    # emprise des arches : |x| <= 48 et ~±12 en z autour de chaque arche. Entre deux arches (z ≈ -188, -222,
    # -261) : treilles sur les trottoirs et lanternes ; les glycines se rangent au-delà de |x| = 50.
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        for i, z in enumerate((-188, -261)):
            place(b, "glycines", "treille", (s * 35.5, 0, z), yaw=90, group=f"Glycines/Treille{cote}{i}",
                  longueur=12, largeur=7, hauteur=9, variant=i, emprise=(12, 7, 9))
        for i, z in enumerate(range(-160, -292, -22)):
            x = s * (61 + (i % 2) * 6)
            place(b, "glycines", "glycine", (x, 0, z - (i % 2) * 4), yaw=(i * 47) % 360, group=f"Glycines/Arbre{cote}{i:02d}",
                  variant=(i + (s > 0)) % 4, taille=1.0 + (i % 3) * 0.1, emprise=(14, 14, 18))
        for i, z in enumerate((-186, -262)):
            place(b, "glycines", "glycine_geante", (s * (98 + (i % 2) * 6), 0, z), yaw=i * 70,
                  group=f"Glycines/Geante{cote}{i}", variant=(i + (s > 0)) % 4, emprise=(30, 30, 36))
        for i, z in enumerate((-160, -222, -290)):
            place(b, "glycines", "bambous", (s * 126, 0, z), group=f"Glycines/Bambous{cote}{i}",
                  variant=i % 4, emprise=(10, 10, 26))
        for i, z in enumerate((-188, -222, -261)):
            x = s * 42.5
            place(b, "mobilier", "lanterne_pierre", (x, 0, z + (6 if z == -188 else 0)), yaw=face_couloir(x),
                  group=f"Glycines/Lanterne{cote}{i}", variant=i % 3, emprise=(3, 3, 7))
        for i, (dx, z, kind) in enumerate(((76, -222, "rocher_deco"), (80, -240, "souche"), (54, -222, "herbes"), (78, -164, "rocher_deco"))):
            place(b, "glycines", kind, (s * dx, 0, z), group=f"Glycines/Deco{cote}{i}", variant=i, emprise=(6, 6, 3))


# ---------------------------------------------------------------------------
# Place des œufs (piliers vermillon, sanctuaire)
# ---------------------------------------------------------------------------

def place_selection(b: Builder) -> None:
    fpil = _asset("mobilier", "pilier_rouge")
    fshide = _asset("mobilier", "guirlande_shide")
    # anneau de piliers rouges (hors du couloir), reliés par des cordes à papiers
    piliers = {-1: [], 1: []}
    for k in range(16):
        a = math.radians(k * 22.5 + 11.25)
        x, z = (R_PLACE + 8) * math.sin(a), Z_PLACE + (R_PLACE + 8) * math.cos(a)
        if abs(x) < DEMI_COULOIR + 4:
            continue
        s = -1 if x < 0 else 1
        with b.at((x, 0, z), group=f"Place/Piliers/P{k:02d}"):
            if fpil:
                fpil(b, variant=k % 2, hauteur=14)
        piliers[s].append((x, z))
    for s, pts in piliers.items():
        pts.sort(key=lambda p: p[1])
        for i, (pa, pb) in enumerate(zip(pts, pts[1:])):
            if fshide:
                with b.group(f"Place/Shide{'G' if s < 0 else 'D'}{i}"):
                    fshide(b, (pa[0], 11, pa[1]), (pb[0], 11, pb[1]), n=5, creux=1.2, variant=i % 2)
    # grands piliers d'entrée et de sortie de place, corde haute au-dessus du couloir
    for j, z in enumerate((Z_PLACE + R_PLACE + 4,)):   # à la sortie, le grand torii de la montagne prend le relais
        for s in (-1, 1):
            with b.at((s * 34, 0, z), group=f"Place/GrandPilier{j}{'G' if s < 0 else 'D'}"):
                if fpil:
                    fpil(b, variant=1, hauteur=40)
        if fshide:
            with b.group(f"Place/ShideHaut{j}"):
                fshide(b, (-32.6, 38.5, z), (32.6, 38.5, z), n=9, creux=1.5, variant=j % 2)
    # sanctuaire à droite, pavillon d'eau à gauche
    place(b, "batiments", "sanctuaire", (80, 0, Z_PLACE), yaw=90, group="Place/Sanctuaire", emprise=(28, 24, 22))
    place(b, "batiments", "temizuya", (-56, 0, Z_PLACE + 14), yaw=-90, group="Place/Temizuya", emprise=(10, 7, 8))
    for i, (x, z) in enumerate(((60, Z_PLACE + 16), (60, Z_PLACE - 16), (-50, Z_PLACE - 14), (-46, Z_PLACE + 30))):
        place(b, "mobilier", "lanterne_pierre", (x, 0, z), yaw=face_couloir(x), group=f"Place/Lanterne{i}", variant=i % 3, emprise=(3, 3, 7))
    # glycines géantes qui encadrent la place (comme sur la référence)
    for i, (x, z) in enumerate(((-98, Z_PLACE - 12), (116, Z_PLACE + 4))):
        place(b, "glycines", "glycine_geante", (x, 0, z), yaw=i * 55, group=f"Place/Geante{i}", variant=i % 4,
              taille=0.9 + (i % 3) * 0.1, emprise=(30, 30, 36))
    for i, (x, z) in enumerate(((-68, Z_PLACE - 8), (46, Z_PLACE + 30), (-40, Z_PLACE + 38))):
        place(b, "glycines", "rocher_deco", (x, 0, z), group=f"Place/Rocher{i}", variant=i, emprise=(6, 6, 3))


def foret_abords(b: Builder) -> None:
    """Abords du torii (côté apparition) : pins et bambous."""
    for s in (-1, 1):
        for i, (dx, dz, kind) in enumerate(((66, 16, "pin"), (96, 26, "bambous"), (130, 14, "pin"), (160, 30, "bambous"))):
            place(b, "glycines", kind, (s * dx, 0, Z_PORTE + dz), group=f"Abords/{'G' if s < 0 else 'D'}{i}",
                  variant=i % 4, emprise=(10, 10, 20))


def reperes(b: Builder) -> None:
    """Pièces invisibles utiles au jeu : zone des œufs, entrée, sortie, couloir."""
    inv = dict(transparency=1.0, collide=False, shadow=False)
    with b.group("Reperes"):
        b.box((-R_PLACE, 0, Z_PLACE - R_PLACE), (R_PLACE, 1, Z_PLACE + R_PLACE), "#ffffff", name="ZoneOeufs", **inv)
        b.box((-DEMI_COULOIR, 0, Z_PORTE + 18), (DEMI_COULOIR, 1, Z_PORTE + 24), "#ffffff", name="Entree", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE - 4), (DEMI_COULOIR, 1, Z_SORTIE + 2), "#ffffff", name="Sortie", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE), (DEMI_COULOIR, 1, Z_PORTE), "#ffffff", name="Couloir", **inv)


def decouper(b: Builder, prefixes=("Sol/", "Falaises/", "Monuments/Montagne", "Monuments/Porte"), taille: float = 64) -> None:
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
    sol_cotes(b)
    falaises_laterales(b)
    place(b, "porte", "grand_torii", (0, 0, Z_PORTE), group="Monuments/Porte", emprise=(260, 16, 48),
          ouverture=74, hauteur=48, mur=X_FALAISE)
    place(b, "montagne", "montagne_glycines", (0, 0, Z_MONTAGNE), group="Monuments/Montagne", emprise=(440, 68, 120),
          passage=68, largeur=2 * X_FOND + 40, profondeur=PROF_MONTAGNE, hauteur=120)
    poses_g = rangee(b, -1, RANGEE_GAUCHE)
    poses_d = rangee(b, 1, RANGEE_DROITE)
    arriere_village(b)
    lampions_village(b)
    details_village(b, poses_g, poses_d)
    allee_glycines(b)
    place_selection(b)
    foret_abords(b)
    reperes(b)
    decouper(b)
    return b


def couloir_libre(b: Builder) -> list:
    """Liste ce qui encombre le couloir de course au sol (hors sol et repères)."""
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


def trop_bas_au_dessus(b: Builder, y_min: float = 30.0) -> list:
    """Pièces au-dessus du couloir mais sous `y_min` (la caméra Roblox sauterait en passant dessous)."""
    out = []
    for p in b.parts:
        if p.group.startswith(("Sol", "Reperes")):
            continue
        R = np.asarray(p.rot).reshape(3, 3)
        half = np.abs(R) @ (np.asarray(p.size) / 2)
        lo, hi = np.asarray(p.pos) - half, np.asarray(p.pos) + half
        if lo[0] < DEMI_COULOIR - 1 and hi[0] > -DEMI_COULOIR + 1 and lo[1] < y_min and hi[1] > 12 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name, round(lo[1], 1)))
    return out


def meta() -> dict:
    return {"nom": "ZoneDemonSlayer", "version": VERSION, "largeur_couloir": 2 * DEMI_COULOIR,
            "longueur": -Z_SORTIE, "spawn": [0, 0, Z_PORTE + 30]}


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
    bas = trop_bas_au_dessus(b)
    print(json.dumps({"pieces": len(b.parts), "fichier": str(out), "en_attente": attente,
                      "couloir_encombre": gene[:20], "nb_couloir_encombre": len(gene),
                      "trop_bas_au_dessus_du_couloir": bas[:20]}, ensure_ascii=False))
    if args.stats:
        for k, v in b.stats().items():
            print(f"{v:6d}  {k}")


if __name__ == "__main__":
    main()
