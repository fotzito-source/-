#!/usr/bin/env python3
"""Plan de la zone One Piece (mer de l'Est : campagne aux moulins, bourg du port, port pirate, crique du crâne)
en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course occupe x ∈ [-45, 45] (90 studs), bordé de trottoirs ou de quais jusqu'à |x| = 55 ;
- on entre sous l'arche du port en z = 0 et on court vers -Z : campagne aux moulins (jusqu'à -112),
  bourg du port aux maisons colorées (-112 → -204), port pirate entre deux bassins turquoise avec les
  navires à quai et le phare (-204 → -292), place des œufs sur un grand ponton à rose des vents
  (centre z = -328), puis le rocher du crâne (façade en z = -366) que le couloir traverse par la bouche
  (96 de large) jusqu'à la zone suivante (z = -400) ;
- des collines vertes en gradins ferment les côtés de la campagne et du bourg (|x| ≥ 140), la pleine mer
  s'ouvre de chaque côté du port et de la place.

    python zone.py                     # écrit build/parts.json (aucune dépendance à Blender)
    python zone.py --stats             # nombre de pièces par groupe
    python zone.py --chevauchements    # assets posés qui se recoupent (boîtes orientées)
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
DEMI_COULOIR = 45        # couloir de course x ∈ [-45, 45] : rien de solide au sol
X_LIBRE_HAUT = 46        # rien du tout au-dessus de |x| < 46 sous y = 30 (caméra Roblox)
X_BORD = 55              # bord des trottoirs, des quais et alignement des façades
X_MAT = 50               # mâts des guirlandes, au milieu des trottoirs
X_TERRASSE = 92          # mur de soutènement de la terrasse haute du bourg
Y_TERRASSE = 6
X_COLLINES = 140         # début des collines latérales (campagne et bourg)
X_FOND = 220             # limite du décor (collines, mer)
X_PLACE = 72             # demi-largeur du grand ponton de la place des œufs
Z_PORTE = 0
Z_APPROCHE = 40          # sol devant l'arche (côté apparition)
Z_BOURG = -112           # fin de la campagne, début du bourg
Z_PORT = -204            # fin du bourg (quai), début des bassins
Z_PLACE = -328           # centre de la place des œufs
R_PLACE = 34
Z_PONTON = Z_PLACE + R_PLACE + 2     # bord avant du grand ponton (-292)
Z_ROCHER = -366          # façade du rocher du crâne (fond du ponton)
PROF_ROCHER = 34
Z_SORTIE = Z_ROCHER - PROF_ROCHER    # -400 : le couloir continue vers la zone suivante
PASSAGE = 96             # largeur libre de la bouche du crâne (parois à |x| ≥ 48)
H_ROCHER = 130
Z_PLAGE = -224           # plages au pied des collines (|x| ≥ 140), de Z_PORT + 8 à Z_PLAGE
Y_EAU = -1.5             # surface de l'eau (les quais et le sol sont à y = 0)
H_GUIRLANDE = 37         # corde des fanions : la pointe des fanions reste au-dessus de 31 studs
H_GUIRLANDE_HAUTE = 42   # une guirlande sur deux plus haute (les lignes de fanions ne s'empilent pas)
Z_CHEMIN_FERME = {-1: -43, 1: -98}   # chemins de ferme (côté gauche / droit) vers les granges
Z_GUIRLANDES_BOURG = (-122, -150, -178)
Z_GUIRLANDES_PORT = (-228, -262)

VERSION = "1.0"


# ---------------------------------------------------------------------------
# Accès aux assets (avec bloc d'attente si un module manque encore)
# ---------------------------------------------------------------------------

def _asset(module: str, fn: str):
    try:
        return getattr(importlib.import_module(f"assets.{module}"), fn)
    except (ImportError, AttributeError):
        return None


def place(b: Builder, module: str, fn: str, pos, yaw: float = 0.0, group: str | None = None, emprise=(16, 16, 16),
          attente: str = "centre", **params) -> dict:
    """Pose un asset ; si le module n'existe pas encore, pose un bloc translucide de même emprise.

    Chaque pose est notée dans `b.poses` (groupe, fonction, première et dernière pièce) pour le contrôle des
    chevauchements. `attente` décrit le bloc d'attente : « centre » (emprise centrée sur l'origine), « devant »
    (de z = -d à 0 : pontons, rocher), « arche » (deux piles hors de l'ouverture `params['ouverture' | 'passage']`
    et un linteau au-dessus de y = 36), « arche_devant » (arche de z = -d à 0)."""
    f = _asset(module, fn)
    n0 = len(b.parts)
    with b.at(pos, yaw=yaw, group=group):
        nom_groupe = b._groups[-1]
        info = None
        if f is not None:
            try:
                info = f(b, **params) or {}
            except NotImplementedError:
                del b.parts[n0:]
        if info is None:
            w, d, h = emprise
            z0, z1 = (-d, 0) if attente.endswith("devant") else (-d / 2, d / 2)
            nom = f"ATTENTE_{module}_{fn}"
            if attente.startswith("arche"):
                o = params.get("ouverture", params.get("passage", 64)) / 2
                for xa, xb in ((-w / 2, -o), (o, w / 2)):
                    b.box((xa, 0, z0), (xb, h, z1), "#ff4fd8", transparency=0.5, name=nom)
                b.box((-o, 36, z0), (o, h, z1), "#ff4fd8", transparency=0.5, name=nom)
            else:
                b.box((-w / 2, 0, z0), (w / 2, h, z1), "#ff4fd8", transparency=0.5, name=nom)
            info = {"emprise": (w, d), "hauteur": h}
    if not hasattr(b, "poses"):
        b.poses = []
    b.poses.append((nom_groupe, fn, n0, len(b.parts)))
    return info


def face_couloir(x: float) -> float:
    """Rotation qui tourne l'avant d'un asset (-Z local) vers le couloir."""
    return -90.0 if x < 0 else 90.0


def face_large(x: float) -> float:
    """Rotation qui tourne l'avant d'un asset (-Z local) vers le large (à l'opposé du couloir)."""
    return 90.0 if x < 0 else -90.0


# ---------------------------------------------------------------------------
# Sol « pixel »
# ---------------------------------------------------------------------------

def sol_pixel(b: Builder, x0: float, x1: float, z0: float, z1: float, cell: float, couleur, y_haut: float = 0.0,
              epaisseur: float = 1.0, studs="top", name: str = "Sol", **kw) -> int:
    """Remplit exactement [x0, x1] × [z0, z1] ; couleur(x, z) → (r, g, b) évaluée au centre de chaque case, cases
    fusionnées. La dernière case de chaque axe est raccourcie si l'étendue n'est pas un multiple de `cell`.
    Une case dont la couleur vaut None reste vide."""
    nx, nz = math.ceil((x1 - x0) / cell - 1e-6), math.ceil((z1 - z0) / cell - 1e-6)
    if nx <= 0 or nz <= 0:
        return 0
    xs = [x0 + i * cell for i in range(nx)] + [x1]
    zs = [z0 + j * cell for j in range(nz)] + [z1]
    grid = np.empty((nz, nx), dtype=object)
    for j in range(nz):
        for i in range(nx):
            v = couleur((xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2)
            grid[j, i] = tuple(v) if v is not None else None
    n = 0
    for col in set(grid.reshape(-1)):
        if col is None:
            continue
        mask = np.vectorize(lambda v, col=col: v == col)(grid)
        for (i, j, w, h) in mask_rects(mask):
            b.box((xs[i], y_haut - epaisseur, zs[j]), (xs[i + w], y_haut, zs[j + h]), col, studs=studs, name=name, **kw)
            n += 1
    return n


def damier(a, bcol, taille: float):
    a, bcol = (hexrgb(v) if isinstance(v, str) else v for v in (a, bcol))
    return lambda x, z: a if (math.floor(x / taille) + math.floor(z / taille)) % 2 == 0 else bcol


def _h(i: int, j: int, k: int = 0) -> int:
    """Petit hachage entier déterministe (motifs du sol)."""
    return (i * 73856093 ^ j * 19349663 ^ k * 83492791) & 0xFFFF


# ---------------------------------------------------------------------------
# Place des œufs : rose des vents
# ---------------------------------------------------------------------------

def rose_des_vents(x: float, z: float):
    """Mosaïque de la place : rose des vents à 8 branches sur un plancher en anneaux, bord de corde.
    Le nord (branche rouge) pointe vers -Z, la direction de la course. None hors du cercle."""
    dx, dz = x, z - Z_PLACE
    d = math.hypot(dx, dz)
    if d >= R_PLACE:
        return None
    if d >= R_PLACE - 2:
        return c("bois_fonce")
    if d >= R_PLACE - 4:
        return c("corde")
    if d < 2.4:
        return c("or")
    if d < 3.6:
        return c("bleu_marine")
    th = math.degrees(math.atan2(-dz, dx))     # 0° = +X (est), 90° = -Z (nord)
    # branches : principales (N, E, S, O) longues, secondaires plus courtes ; chaque branche en deux moitiés
    for longues in (True, False):
        for k in (range(0, 360, 90) if longues else range(45, 360, 90)):
            delta = (th - k + 180) % 360 - 180
            if abs(delta) > 60:
                continue
            le = d * math.cos(math.radians(delta))
            tr = d * math.sin(math.radians(delta))
            L, w = (26.0, 5.5) if longues else (17.0, 4.2)
            if 0 <= le <= L and abs(tr) <= w * (1 - le / L):
                if longues and k == 90:
                    return c("rouge") if tr >= 0 else c("rouge_fonce")
                if longues:
                    return c("voile") if tr >= 0 else c("bleu_marine")
                return c("jaune") if tr >= 0 else c("jaune_fonce")
    if 21 <= d < 23:
        return c("bleu_marine")                 # cercle des degrés
    return c("bois_pale") if int(d // 5) % 2 == 0 else c("bois_clair")


TONS_PLANCHES = (c("bois_quai"), c("bois_clair"), shade(c("bois_fonce"), 1.15))


def planches(x: float, z: float, rangee: float = 4.0, longueur: float = 20.0):
    """Plancher de quai : planches posées en travers (selon X), rangées de 4 studs, joints décalés, trois tons bien
    distincts ; une traverse sombre (2 studs) toutes les 5 rangées donne le rythme de la course et l'idée de ponton."""
    r = math.floor(z / rangee)
    if r % 5 == 0 and z - r * rangee < 2:
        return c("bois_fonce")
    decal = longueur / 2 if r % 2 else 0.0
    k = math.floor((x + decal) / longueur)
    return TONS_PLANCHES[_h(r, k) % 3]


# ---------------------------------------------------------------------------
# Sols : couloir, trottoirs et quais, côtés, eau
# ---------------------------------------------------------------------------

def sol_couloir(b: Builder) -> None:
    ch, chc, chf = c("chemin"), c("chemin_clair"), c("chemin_fonce")
    pave, pavef, paver, pavec = c("pave"), c("pave_fonce"), c("pave_rose"), c("pave_clair")
    sab, sabm = c("sable"), c("sable_mouille")

    def couloir(x, z):
        m = rose_des_vents(x, z)
        if m:
            return m
        ax = abs(x)
        if z > Z_BOURG:            # campagne : chemin de terre en grandes plaques, deux paires d'ornières
            if 12 <= ax < 14 or 30 <= ax < 32:
                return chf
            return ch if (math.floor(z / 12) + (ax >= 14) + (ax >= 32)) % 2 == 0 else chc
        if z > Z_PORT:             # bourg : grandes dalles 12 × 12 en deux tons proches, chemin clair dans l'axe
            if ax >= DEMI_COULOIR - 2:
                return paver if math.floor(z / 8) % 2 == 0 else pavef        # liseré rose
            if any(abs(z - zg) < 2 for zg in Z_GUIRLANDES_BOURG):
                return paver                              # bande rose sous chaque guirlande
            if ax < 10:
                return pavec                              # chemin clair dans l'axe du crâne
            return pave if (math.floor(x / 12) + math.floor(z / 12)) % 2 == 0 else pavef
        if z > Z_ROCHER:           # port et place : plancher de quai, bordé de pierre claire le long des bassins
            if Z_PONTON < z <= Z_PORT and ax >= DEMI_COULOIR - 4:
                return c("pierre_claire") if math.floor(z / 6) % 2 == 0 else c("pierre")
            return planches(x, z)
        return sab if math.floor(z / 8) % 2 else sabm   # passage du rocher : sable

    z_fin = Z_SORTIE
    zp_bas, zp_haut = Z_PLACE - R_PLACE, Z_PLACE + R_PLACE
    with b.group("Abords/Sol/Couloir"):
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, Z_PORTE, Z_APPROCHE, 2, couloir)
    with b.group("Sol/Couloir"):
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, Z_BOURG, Z_PORTE, 2, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, Z_PORT, Z_BOURG, 2, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, zp_haut, Z_PORT, 2, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, zp_bas, zp_haut, 2, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, z_fin, zp_bas, 2, couloir)


def sol_trottoirs(b: Builder) -> None:
    """Bandes 45 ≤ |x| ≤ 55 : accotement herbeux (campagne), trottoir (bourg), quai de pierre (port),
    plancher (place), sable (rocher). Le long des bassins, une margelle épaisse fait le mur du quai."""
    h, hc = c("herbe"), c("herbe_claire")
    bord, pc, p, pf = c("bordure"), c("pierre_claire"), c("pierre"), c("pierre_fonce")
    chc = c("chemin_clair")

    def trottoir(x, z):
        m = rose_des_vents(x, z)
        if m:
            return m
        ax = abs(x)
        if z > Z_BOURG:
            if ax < DEMI_COULOIR + 2:
                return chc
            s = -1 if x < 0 else 1
            if abs(z - Z_CHEMIN_FERME[s]) < 2:
                return c("chemin")
            return h if math.floor(z / 16) % 2 == 0 else hc
        if z > Z_PORT:
            if ax < DEMI_COULOIR + 1:
                return bord
            return pc if math.floor(z / 6) % 2 == 0 else p
        if z > Z_ROCHER:
            if Z_PONTON >= z:
                return planches(x, z)
            if ax < DEMI_COULOIR + 1:
                return bord
            return pc if math.floor(z / 8) % 2 == 0 else p
        return c("sable")

    z_fin = Z_SORTIE
    for s in (-1, 1):
        with b.group("Abords/Sol/Trottoirs"):
            xa, xb = sorted((s * DEMI_COULOIR, s * X_BORD))
            sol_pixel(b, xa, xb, Z_PORTE, Z_APPROCHE, 2, trottoir)
        with b.group("Sol/Trottoirs"):
            xa, xb = sorted((s * DEMI_COULOIR, s * (X_BORD - 2)))
            sol_pixel(b, xa, xb, z_fin, Z_PORTE, 2, trottoir)
            # bande extérieure : herbe/pavés normaux, margelle épaisse (mur de quai) le long des bassins
            xa, xb = sorted((s * (X_BORD - 2), s * X_BORD))
            sol_pixel(b, xa, xb, Z_PORT, Z_PORTE, 2, trottoir)
            sol_pixel(b, xa, xb, Z_PONTON, Z_PORT, 2, lambda x, z: pf if math.floor(z / 4) % 2 else shade(pf, 0.94),
                      epaisseur=5, name="Margelle")
            sol_pixel(b, xa, xb, Z_ROCHER, Z_PONTON, 2, trottoir)
            sol_pixel(b, xa, xb, z_fin, Z_ROCHER, 2, trottoir)


def sol_cotes(b: Builder) -> None:
    """Côtés : prairies et chemins de ferme (campagne), ruelles et terrasse haute (bourg), plages."""
    h, hc, hf = c("herbe"), c("herbe_claire"), c("herbe_fonce")
    ch, chc = c("chemin"), c("chemin_clair")
    pave, pavef = c("pave"), c("pave_fonce")

    def campagne(x, z):
        ax = abs(x)
        zc = Z_CHEMIN_FERME[-1 if x < 0 else 1]     # chemin de ferme vers la grange
        if zc - 2 <= z < zc + 2 and ax < (92 if x < 0 else 72):   # jusqu'à la porte de la grange
            return ch
        if Z_PORTE - 6 <= z < Z_PORTE + 6 and ax < 72:   # dallage au pied de l'arche
            return chc
        x0c, x1c, z0c, z1c = CHAMP_G
        if x0c <= x <= x1c and z0c <= z <= z1c:          # terre du champ
            return c("terre") if math.floor((x - x0c) / 2) % 2 else c("terre_fonce")
        return h if (math.floor(x / 24) + math.floor(z / 24)) % 2 == 0 else hc

    def bourg(x, z):
        ax = abs(x)
        if ax < X_BORD + 26:                          # cours des maisons (en grande partie sous les maisons)
            return pave if math.floor(z / 8) % 2 == 0 else pavef
        return chc if (math.floor(z / 8) % 3 == 0) else pave   # ruelle au pied du mur

    with b.group("Sol/Cotes"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_COLLINES))
            sol_pixel(b, xa, xb, Z_BOURG, Z_PORTE, 4, campagne)
            xa, xb = sorted((s * X_BORD, s * X_TERRASSE))
            sol_pixel(b, xa, xb, Z_PORT + 2, Z_BOURG, 2, bourg)
            # quai du bourg face au bassin (mur visible au-dessus de l'eau)
            sol_pixel(b, xa, xb, Z_PORT, Z_PORT + 2, 2, lambda x, z: c("pierre_fonce"), epaisseur=5, name="Margelle")
            # terrasse haute (jardins, pavés) et son mur de soutènement
            xa, xb = sorted((s * (X_TERRASSE + 1), s * X_COLLINES))
            sol_pixel(b, xa, xb, Z_PORT, Z_BOURG, 4,
                      lambda x, z: (hf if (math.floor(z / 24) + math.floor(abs(x) / 24)) % 2 else h)
                      if abs(x) > X_TERRASSE + 20 else (pave if math.floor(z / 8) % 2 else pavef),
                      y_haut=Y_TERRASSE, epaisseur=Y_TERRASSE + 6, name="Terrasse")
            xa, xb = sorted((s * X_TERRASSE, s * (X_TERRASSE + 1)))
            b.box((xa, -1, Z_PORT), (xb, Y_TERRASSE + 1.2, Z_BOURG), c("pierre"), studs="top", name="MurTerrasse")
    with b.group("Abords/Sol/Cotes"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_COLLINES))
            sol_pixel(b, xa, xb, Z_PORTE, Z_PORTE + 8, 4, campagne)
            sol_pixel(b, xa, xb, Z_PORTE + 8, Z_APPROCHE, 8, damier(h, hc, 24))
    with b.group("Sol/Plages"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_COLLINES, s * X_FOND))
            sol_pixel(b, xa, xb, Z_PLAGE, Z_PORT + 8, 4,
                      lambda x, z: c("sable_mouille") if z < Z_PLAGE + 4 else
                      (c("sable") if (math.floor(x / 16) + math.floor(z / 12)) % 2 else c("sable_clair")),
                      y_haut=-0.6, epaisseur=1.4, name="Plage")


def escaliers_terrasse(b: Builder) -> None:
    """Escaliers de pierre de la ruelle à la terrasse haute (contre le mur, perpendiculaires au couloir)."""
    for s in (-1, 1):
        for i, zc in enumerate((-146, -176)):
            with b.group(f"Bourg/Escalier{'G' if s < 0 else 'D'}{i}"):
                for k in range(Y_TERRASSE):
                    xa, xb = sorted((s * (X_TERRASSE - Y_TERRASSE + k), s * X_TERRASSE))
                    b.box((xa, 0, zc - 3), (xb, k + 1, zc + 3), c("pierre_claire") if k % 2 else c("pierre"), studs="top", name="Marche")
                for dz in (-3.5, 3.5):
                    xa, xb = sorted((s * (X_TERRASSE - Y_TERRASSE), s * X_TERRASSE))
                    b.wedge((xa, 0, zc + dz - 0.5), (xb, Y_TERRASSE + 0.8, zc + dz + 0.5), c("pierre_fonce"),
                            down="-x" if s > 0 else "+x", name="Rampe")


def eau(b: Builder) -> None:
    """Bassins du port et pleine mer : écume au pied des quais, haut-fond turquoise, eau claire, bleu profond
    au large, quelques rides claires. Surface en y = Y_EAU (lisse, sans studs)."""
    ecume, lagon, claire, moy, prof = c("ecume"), c("eau_lagon"), c("eau_claire"), c("eau"), c("eau_profonde")

    def couleur(x, z):
        ax = abs(x)
        if z > Z_PONTON:
            d = ax - X_BORD
        else:
            d = ax - X_PLACE
        d = min(d, (Z_PORT - z) if ax < X_COLLINES else (Z_PLAGE - z), z - Z_ROCHER)
        if d < 1.5:
            return ecume
        if d < 7:
            return lagon
        i, j = math.floor(x / 8), math.floor(z / 4)
        ride = _h(i, j, 5) % 19 == 0
        if d < 28:
            return lagon if ride else claire
        if ax > 160:
            return moy if ride else prof
        return claire if ride else moy

    with b.group("Eau"):
        for s in (-1, 1):
            # bassin du port
            xa, xb = sorted((s * X_BORD, s * X_COLLINES))
            sol_pixel(b, xa, xb, Z_PONTON, Z_PORT, 2, couleur, y_haut=Y_EAU, studs="none", name="Eau")
            xa, xb = sorted((s * X_COLLINES, s * X_FOND))
            sol_pixel(b, xa, xb, Z_PONTON, Z_PLAGE, 4, couleur, y_haut=Y_EAU, studs="none", name="Eau")
            # mer autour de la place, jusqu'au rocher
            xa, xb = sorted((s * X_PLACE, s * X_FOND))
            sol_pixel(b, xa, xb, Z_ROCHER, Z_PONTON, 4, couleur, y_haut=Y_EAU, studs="none", name="Eau")


def collines_laterales(b: Builder) -> tuple:
    """Collines vertes en trois gradins (|x| ≥ 140) : chapeau d'herbe débordant, flanc de terre à strates claires.
    Elles descendent en marches vers la mer au bout du bourg. Les 40 studs d'approche (z > 0) vont dans le dossier
    « Abords ». Renvoie les sommets (x, y, z) du gradin du milieu (moulins) et la liste de tous les gradins
    (côté, n° de gradin, |x| début, |x| fin, z bas, z haut, hauteur) pour l'habillage."""
    rng = np.random.default_rng(5)
    sommets, tous = [], []
    terre, terre_f, terre_c = c("terre"), c("terre_fonce"), c("terre_claire")
    herbes = (c("herbe"), c("herbe_claire"), c("herbe_fonce"))
    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        z, k = Z_APPROCHE, 0
        while z > Z_PORT + 8 + 0.01:
            l = min(16, z - (Z_PORT + 8)) if z <= Z_PORTE else min(16, z - Z_PORTE)
            descente = max(0.0, (z - l - (-150)) / -50.0)          # 0 → 1 sur les 50 derniers studs
            gradins = ((X_COLLINES, X_COLLINES + 20, 5 + 3 * (k % 3)),
                       (X_COLLINES + 20, X_COLLINES + 52, 14 + 5 * math.sin(k * 0.9) + rng.uniform(0, 3)),
                       (X_COLLINES + 52, X_FOND, 26 + 7 * math.sin(k * 0.55 + 1.0) + rng.uniform(0, 4)))
            h_prec = None
            with b.group(f"Abords/Collines/{cote}" if z - l >= Z_PORTE else f"Collines/{cote}"):
                for gi, (xa_, xb_, hg) in enumerate(gradins):
                    hg = max(2, round(hg * (1 - 0.75 * descente)))
                    if gi == 0 and z - l < Z_BOURG and hg == Y_TERRASSE:
                        hg += 1          # chapeau d'herbe jamais au ras de la terrasse (pas de faces coplanaires)
                    if hg == h_prec:
                        hg += 1          # le débord du chapeau ne se confond pas avec celui du gradin voisin
                    h_prec = hg
                    xa, xb = sorted((s * xa_, s * xb_))
                    b.box((xa, 0, z - l), (xb, hg - 1.5, z), terre if (k + gi) % 2 else terre_f, name="Flanc")
                    # strate claire côté vallée
                    fa = s * xa_
                    sa, sb = sorted((fa - s * 0.2, fa + s * 0.8))
                    if hg > 6:
                        b.box((sa, hg * 0.45, z - l + 0.1), (sb, hg * 0.45 + 1, z - 0.1), terre_c, collide=False,
                              name="Strate")
                    # chapeau d'herbe qui déborde un peu côté vallée
                    ca, cb = sorted((fa - s * 0.6, s * xb_))
                    b.box((ca, hg - 1.5, z - l), (cb, hg, z), herbes[(k + gi) % 3], studs="top", name="Herbe")
                    if gi == 1 and z - l >= Z_PORTE - 0.01 and z > Z_PORTE:
                        pass
                    elif gi == 1:
                        sommets.append((s * (xa_ + xb_) / 2, hg, z - l / 2))
                    tous.append((s, gi, xa_, xb_, z - l, z, hg))
            z -= l
            k += 1
    return sommets, tous


def habiller_collines(b: Builder, gradins: list) -> None:
    """Habille les gradins des collines (références 1 et 3) : petite ferme à toit rouge, clôture et vaches, palmiers sur
    le gradin bas, bosquets de mandariniers, buissons et rochers. Chaque objet reste sur un seul gradin (les gradins
    voisins n'ont pas la même hauteur). Les moulins des collines occupent déjà certains gradins du milieu."""
    cases = {}
    for (s, gi, xa_, xb_, z0, z1, hg) in gradins:
        if z1 <= Z_PORTE + 0.01 and z1 - z0 > 15.9:
            cases[(s, gi, round((Z_PORTE - z1) / 16))] = ((xa_ + xb_) / 2, (z0 + z1) / 2, hg)

    def poser(s, gi, idx, module, fn, dx=0.0, dz=0.0, yaw=0.0, nom="", **kw):
        if (s, gi, idx) not in cases:
            return
        xc, zc, hg = cases[(s, gi, idx)]
        place(b, module, fn, (s * (xc + dx), hg, zc + dz), yaw=yaw, group=f"Campagne/Collines{'G' if s < 0 else 'D'}/{nom}",
              emprise=(6, 6, 6), **kw)

    plan = {
        -1: dict(ferme=3, enclos=4, palmiers=(0, 7), bosquets=[
            ("oranger", 1, 0, -7, 2), ("buisson", 1, 0, 6, -3), ("buisson", 0, 2, 2, 0), ("rocher", 2, 2, -4, 0),
            ("oranger", 1, 2, 5, -2), ("buisson", 2, 5, 0, 2), ("oranger", 1, 7, 4, 0)]),
        1: dict(ferme=5, enclos=6, palmiers=(1, 4), bosquets=[
            ("oranger", 1, 0, -6, 0), ("buisson", 0, 0, 3, 3), ("rocher", 2, 1, 3, 0), ("oranger", 1, 2, 5, 2),
            ("buisson", 1, 2, -7, -3), ("buisson", 2, 4, 0, 0), ("oranger", 1, 7, -4, 0)]),
    }
    for s, pl in plan.items():
        poser(s, 1, pl["ferme"], "batiments", "grange", dz=0.3, yaw=face_couloir(s), nom="Ferme", variant=1, largeur=13,
              profondeur=10.5)
        # clôture le long du gradin et deux vaches devant
        poser(s, 1, pl["enclos"], "mobilier", "cloture_bois", dz=5.0, nom="Cloture", longueur=24, variant=2)
        for i, (dx, dz, yaw, v) in enumerate(((-7.0, -1.5, 80, 0), (6.0, 0.5, 250, 2))):
            poser(s, 1, pl["enclos"], "mobilier", "vache", dx=dx, dz=dz, yaw=yaw, nom=f"Vache{i}", variant=v)
        for i, idx in enumerate(pl["palmiers"]):
            poser(s, 0, idx, "nature", "palmier", dx=(-3, 2)[i], yaw=i * 75 + (s > 0) * 30, nom=f"Palmier{i}",
                  variant=i % 3, hauteur=13 + 2 * (i % 2))
        for i, (fn, gi, idx, dx, dz) in enumerate(pl["bosquets"]):
            kw = {"taille": 1.2} if fn == "rocher" else {}
            poser(s, gi, idx, "nature", fn, dx=dx, dz=dz, yaw=i * 47, nom=f"Bosquet{i}", variant=i % 3, **kw)


# ---------------------------------------------------------------------------
# Campagne aux moulins (z 0 → -112)
# ---------------------------------------------------------------------------

def enclos(b: Builder, x0: float, x1: float, z0: float, z1: float, variant: int, group: str, ouverture: str = "") -> None:
    """Enclos rectangulaire en clôture de ranch ; `ouverture` = côté laissé ouvert au milieu ('x0', 'x1', 'z0', 'z1')."""
    xa, xb = sorted((x0, x1))
    za, zb = sorted((z0, z1))
    cotes = {"z0": ((xa + xb) / 2, za, 0.0, xb - xa), "z1": ((xa + xb) / 2, zb, 180.0, xb - xa),
             "x0": (xa, (za + zb) / 2, -90.0, zb - za), "x1": (xb, (za + zb) / 2, 90.0, zb - za)}
    for nom, (x, z, yaw, L) in cotes.items():
        if nom == ouverture:
            for sgn in (-1, 1):   # deux demi-clôtures et un passage de 6 studs
                off = sgn * (L / 4 + 1.5)
                dx, dz = (off, 0) if nom in ("z0", "z1") else (0, off)
                place(b, "mobilier", "cloture_bois", (x + dx, 0, z + dz), yaw=yaw, group=f"{group}/{nom}{sgn}",
                      longueur=L / 2 - 3, variant=variant, emprise=(L / 2 - 3, 1, 4))
        else:
            place(b, "mobilier", "cloture_bois", (x, 0, z), yaw=yaw, group=f"{group}/{nom}", longueur=L, variant=variant,
                  emprise=(L, 1, 4))


CHAMP_G = (-136, -94, -30, -2)          # champ de blé et de légumes à gauche (x0, x1, z0, z1), près du moulin de pierre


def champ(b: Builder, x0: float, x1: float, z0: float, z1: float) -> None:
    """Champ en sillons parallèles au chemin : rangs de blé (foin) puis de légumes (vert), terre entre les rangs,
    épouvantail de piquets au milieu. Le sol du champ est en terre (voir `sol_cotes`)."""
    with b.group("Campagne/Champ"):
        xs = np.arange(x0 + 2, x1 - 1, 4.0)
        zm = (z0 + z1) / 2
        for i, x in enumerate(xs):
            ble = i < len(xs) * 0.6
            col = c("foin") if ble else c("herbe_fonce")
            h = 1.6 if ble else 1.0
            # rangs coupés au milieu par un sentier de 2 studs
            for za, zb in ((z0 + 2, zm - 1), (zm + 1, z1 - 2)):
                b.box((x - 1, 0, za), (x + 1, h, zb), shade(col, 0.94 + 0.06 * (i % 2)), studs="top", collide=False,
                      name="Rang")
            if not ble and i % 2 == 0:       # choux ronds sur les rangs de légumes
                for zz in (z0 + 5, zm - 4, zm + 4, z1 - 5):
                    b.ball((x, 1.0, zz), 0.9, c("feuillage"), collide=False, shadow=False, name="Chou")
        # épouvantail : croix de piquets, blouse bleue, tête de paille, petit chapeau brun
        xe = xs[len(xs) // 3] + 2
        b.box((xe - 0.2, 0, zm - 0.2), (xe + 0.2, 6.2, zm + 0.2), c("bois_fonce"), name="Piquet")
        b.box((xe - 2.2, 4.4, zm - 0.15), (xe + 2.2, 4.8, zm + 0.15), c("bois_fonce"), collide=False, name="Bras")
        b.box((xe - 1.0, 3.0, zm - 0.45), (xe + 1.0, 4.9, zm + 0.45), c("toile_bleue"), collide=False, name="Blouse")
        b.box((xe - 0.6, 4.9, zm - 0.6), (xe + 0.6, 6.0, zm + 0.6), c("foin"), collide=False, name="Tete")
        b.box((xe - 0.75, 6.0, zm - 0.75), (xe + 0.75, 6.6, zm + 0.75), c("bois_fonce"), collide=False, name="Chapeau")


def campagne(b: Builder, sommets: list) -> None:
    """Prairies, clôtures le long du chemin, moulins (bois à ailes jaunes, tour rose, tours de pierre à dôme),
    granges rouges, vaches, foin, verger de mandarines, champ et palmiers en bord de route.

    Plans : buissons sur les accotements (|x| 51), clôtures (|x| 54), palmiers juste derrière (|x| 60) ; moulins,
    verger, granges, enclos et champ en |x| 60-136 ; moulins sur les collines (|x| ≈ 176) au fond."""
    # clôtures le long du chemin (bord extérieur de l'accotement), interrompues au chemin de ferme
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        zc = Z_CHEMIN_FERME[s]
        for i, (za, zb) in enumerate(((-8, zc + 4), (zc - 4, -110))):
            place(b, "mobilier", "cloture_bois", (s * 54, 0, (za + zb) / 2), yaw=face_couloir(s), group=f"Campagne/Cloture{cote}{i}",
                  longueur=abs(zb - za), variant=2, emprise=(abs(zb - za), 1, 4))
    # moulins près du chemin, ailes face aux joueurs qui arrivent (avant vers +Z, un peu tourné vers le couloir)
    moulins = [(-72, 0, -46, 0, 44, 200), (-126, 0, -42, 2, 26, 195), (74, 0, -64, 1, 40, 160)]
    for i, (x, y, z, v, h, yaw) in enumerate(moulins):
        place(b, "nature", "moulin", (x, y, z), yaw=yaw, group=f"Campagne/Moulin{i}", variant=v, hauteur=h, emprise=(12, 12, h))
    # butte et moulin à calotte bleue sur la droite
    place(b, "nature", "colline", (116, 0, -26), yaw=90, group="Campagne/Butte", variant=0, largeur=40, profondeur=36, hauteur=8,
          emprise=(40, 36, 8))
    place(b, "nature", "moulin", (118, 8, -26), yaw=160, group="Campagne/MoulinButte", variant=3, hauteur=24, emprise=(12, 12, 24))
    # moulins sur les collines latérales (gradin du milieu)
    for i in range(2):
        for s in (-1, 1):
            cand = [p for p in sommets if (p[0] < 0) == (s < 0)]
            k = ((1, 6) if s < 0 else (3, 8))[i]
            if k < len(cand):
                x, y, z = cand[k]
                place(b, "nature", "moulin", (x, y, z), yaw=180 + s * 20, group=f"Campagne/MoulinColline{'G' if s < 0 else 'D'}{i}",
                      variant=(i + (s > 0) + 1) % 4, hauteur=22, emprise=(10, 10, 22))
    # champ à gauche, entre le moulin de bois et le moulin de pierre
    champ(b, *CHAMP_G)
    # granges, porte tournée vers le chemin de ferme
    place(b, "batiments", "grange", (-100, 0, Z_CHEMIN_FERME[-1]), yaw=-90, group="Campagne/GrangeG", variant=0, largeur=22,
          profondeur=16, emprise=(22, 16, 18))
    place(b, "batiments", "grange", (79, 0, Z_CHEMIN_FERME[1]), yaw=90, group="Campagne/GrangeD", variant=1, largeur=18,
          profondeur=14, emprise=(18, 14, 16))
    # enclos à vaches (celui de gauche s'ouvre sur le chemin, à deux pas de la route)
    enclos(b, -64, -116, -58, -106, 0, "Campagne/EnclosG", ouverture="x1")
    enclos(b, 96, 134, -50, -108, 0, "Campagne/EnclosD", ouverture="x0")
    for i, (x, z, yaw, v) in enumerate(((-78, -68, 30, 0), (-98, -76, 200, 1), (-84, -92, 120, 2), (-106, -98, 300, 0),
                                        (-72, -100, 250, 1), (108, -64, 250, 1), (124, -80, 20, 0), (110, -96, 150, 2),
                                        (104, -84, 300, 0))):
        place(b, "mobilier", "vache", (x, 0, z), yaw=yaw, group=f"Campagne/Vache{i}", variant=v, emprise=(3, 8, 6))
    for i, (x, z, v) in enumerate(((-110, -64, 0), (-82, -30, 1), (-88, -36, 2), (128, -100, 0), (90, -106, 1),
                                   (-122, -56, 2), (-136, -48, 0))):
        place(b, "mobilier", "botte_foin", (x, 0, z), yaw=i * 37, group=f"Campagne/Foin{i}", variant=v, emprise=(5, 5, 4))
    # verger de mandarines (entre le chemin et la butte)
    for i, (x, z) in enumerate(((64, -12), (74, -24), (64, -36), (82, -10), (88, -30), (78, -44))):
        place(b, "nature", "oranger", (x, 0, z), yaw=i * 60, group=f"Campagne/Verger{i}", variant=i % 3, emprise=(6, 6, 8))
    # palmiers juste derrière les clôtures : rythme le long du chemin, en quinconce
    for i, (x, z, h) in enumerate(((-60, -34, 16), (-59, -98, 15), (60, -50, 17), (60, -82, 15), (60, -104, 16))):
        place(b, "nature", "palmier", (x, 0, z), yaw=i * 70, group=f"Campagne/Palmier{i}", variant=(0, 1, 1, 0, 2)[i], hauteur=h,
              emprise=(8, 8, 16))
    # buissons fleuris sur les accotements et au pied des clôtures
    for i, (x, z, v) in enumerate(((-51, -12, 0), (-51, -52, 1), (-51, -80, 3), (-51, -104, 2), (51, -18, 2), (51, -40, 0),
                                   (51, -70, 1), (51, -106, 3), (-90, -50, 3), (-62, -16, 2), (90, -50, 0))):
        place(b, "nature", "buisson", (x, 0, z), group=f"Campagne/Buisson{i}", variant=v, emprise=(4, 4, 3))
    for i, (x, z) in enumerate(((-51, -28), (51, -92))):
        place(b, "mobilier", "panneau", (x, 0, z), yaw=face_couloir(x), group=f"Campagne/Panneau{i}",
              texte=("MOULIN", "FERME")[i], variant=i % 2, emprise=(6, 1, 6))


# ---------------------------------------------------------------------------
# Bourg du port (z -112 → -204)
# ---------------------------------------------------------------------------

RANGEE_GAUCHE = [
    ("batiments:maison_port", 18, 14, {"variant": 0, "etages": 4}),
    ("batiments:etal", 8, 6, {"variant": 0}),           # fruits
    ("batiments:maison_port", 16, 14, {"variant": 1}),
    ("batiments:taverne", 24, 20, {"variant": 0}),
    ("batiments:maison_port", 16, 14, {"variant": 2, "etages": 4}),
]
RANGEE_DROITE = [
    ("batiments:maison_port", 16, 14, {"variant": 3, "etages": 4}),
    ("batiments:maison_port", 20, 16, {"variant": 4}),
    ("batiments:etal", 8, 6, {"variant": 1}),           # viande sur l'os
    ("batiments:maison_port", 18, 14, {"variant": 5, "etages": 4}),
    ("batiments:maison_port", 18, 14, {"variant": 7, "etages": 3}),
]
ECART = 2.0


def rangee(b: Builder, s: int, plan) -> list:
    """Aligne une rangée du bourg le long du couloir (façades en |x| = 55, avant tourné vers le couloir)."""
    cote = "Gauche" if s < 0 else "Droite"
    z = Z_BOURG - ECART
    poses = []
    for i, (kind, larg, prof, params) in enumerate(plan):
        zc = z - larg / 2
        mod, fn = kind.split(":")
        kw = dict(params)
        if fn in ("maison_port", "taverne"):
            kw.setdefault("largeur", larg)
            kw.setdefault("profondeur", prof)
        x = s * (X_BORD + prof / 2)
        info = place(b, mod, fn, (x, 0, zc), yaw=face_couloir(x), group=f"Bourg/{cote}/{i:02d}_{fn.capitalize()}",
                     emprise=(larg, prof, 18), **kw)
        poses.append((x, zc, larg, prof, fn))
        z -= larg + ECART
    assert z + ECART >= Z_PORT - 0.01, f"rangée trop longue ({z + ECART})"
    return poses


def bourg(b: Builder) -> tuple:
    poses_g = rangee(b, -1, RANGEE_GAUCHE)
    poses_d = rangee(b, 1, RANGEE_DROITE)
    # seconde rangée sur la terrasse haute
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        for i, (zc, larg, prof, v) in enumerate(((-128, 18, 14, 6 if s < 0 else 7), (-161, 16, 14, 3 if s < 0 else 1),
                                                   (-191, 18, 14, 5 if s < 0 else 2))):
            x = s * (X_TERRASSE + 4 + prof / 2)
            place(b, "batiments", "maison_port", (x, Y_TERRASSE, zc), yaw=face_couloir(x), group=f"Bourg/Terrasse{cote}{i}",
                  variant=v, largeur=larg, profondeur=prof, etages=3, emprise=(larg, prof, 22))
        # palmiers : deux entre les maisons (dans l'axe des escaliers), quatre derrière les toits
        for i, (dx, zc, h) in enumerate(((11, -145, 13), (11, -175.5, 15), (30, -118, 17), (34, -150, 19), (28, -186, 18),
                                         (38, -200, 16))):
            place(b, "nature", "palmier", (s * (X_TERRASSE + dx), Y_TERRASSE, zc), yaw=i * 80 + (s > 0) * 40,
                  group=f"Bourg/Palmier{cote}{i}", variant=1 if i < 2 else (i + (s > 0)) % 3, hauteur=h, emprise=(8, 8, 16))
    escaliers_terrasse(b)
    return poses_g, poses_d


def guirlandes(b: Builder, zs, prefixe: str, hauteurs=None) -> None:
    """Guirlandes de fanions au-dessus du couloir, tendues entre deux mâts plantés sur les trottoirs (|x| = 50).
    `hauteurs` : hauteur de la corde de chaque guirlande (alternées pour que les lignes ne s'empilent pas)."""
    f = _asset("mobilier", "guirlande_fanions")
    for i, z in enumerate(zs):
        h = hauteurs[i] if hauteurs else H_GUIRLANDE
        with b.group(f"{prefixe}/Guirlande{i + 1}"):
            for s in (-1, 1):
                place(b, "mobilier", "mat_guirlande", (s * X_MAT, 0, z), group=f"Mat{'G' if s < 0 else 'D'}", hauteur=h + 1,
                      variant=i % 3, emprise=(2, 2, h + 1))
            if f:
                f(b, (-X_MAT + 0.6, h, z), (X_MAT - 0.6, h, z), n=20, creux=3.0, variant=i % 3)


def details_bourg(b: Builder, poses_g, poses_d) -> None:
    """Lanternes, tonneaux, caisses, panneaux, bancs, viande à la broche devant les façades (|x| ≈ 52)."""
    for s in (-1, 1):
        for i, z in enumerate((-136, -166, -196)):
            x = s * 52.5
            place(b, "mobilier", "lanterne_quai", (x, 0, z), yaw=face_couloir(x), group=f"Bourg/Details/Lanterne{'G' if s < 0 else 'D'}{i}",
                  variant=1, emprise=(2, 4, 10))
    props = ["tonneaux", "caisses", "panneau", "banc", "bouee"]
    # enseignes par côté : celle de gauche est devant la taverne
    textes = {-1: ["AUBERGE", "MARCHÉ"], 1: ["ÉPICES", "POISSONS", "PORT"]}
    occupes = {-1: [-122, -150, -178, -136, -166, -196], 1: [-122, -150, -178, -136, -166, -196, -160]}
    hauts = {s: list(v) for s, v in occupes.items()}       # mâts, lanternes, broche, enseignes : sous la toile
    bas = {-1: [], 1: []}                                   # tonneaux, caisses, bancs, bouées : à côté de la table
    k = 0
    for s, poses in ((-1, poses_g), (1, poses_d)):
        for (x, zc, larg, prof, fn_pose) in poses:
            if larg < 12:
                continue
            fn = props[k % len(props)]
            # position le long de la façade la plus éloignée des mâts, lanternes et de la broche
            cands = [zc + t for t in np.linspace(-larg / 2 + 3.5, larg / 2 - 3.5, 9)]
            zp = max(cands, key=lambda z: (min(abs(z - zi) for zi in occupes[s]), -abs(z - zc)))
            occupes[s].append(zp)
            (hauts if fn == "panneau" else bas)[s].append(zp)
            xp = s * (X_BORD - 3.6)
            kw = {}
            if fn == "panneau":
                kw["texte"] = "TAVERNE" if fn_pose == "taverne" else textes[s].pop(0)
            place(b, "mobilier", fn, (xp, 0, zp), yaw=face_couloir(xp), group=f"Bourg/Details/{fn}{k}", variant=k % 3,
                  emprise=(3, 3, 4), **kw)
            k += 1
    place(b, "mobilier", "viande_geante", (50.5, 0, -160), yaw=90, group="Bourg/Details/Broche", variant=2, taille=0.8,
          emprise=(5, 3, 4))
    # parasols de marché et jardinières : un premier plan de mi-hauteur entre les accessoires (toile à |x| ≥ 47,5)
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        libres = []
        for _ in range(3):
            cands = [float(z) for z in np.arange(Z_BOURG - 5.0, Z_PORT + 5.0, -0.5)
                     if min(abs(z - zi) for zi in hauts[s]) >= 5.0 and min([abs(z - zi) for zi in bas[s]] + [99]) >= 4.0
                     and min([abs(z - zi) for zi in libres] + [99]) >= 12.0]
            if not cands:
                break
            libres.append(max(cands, key=lambda z: min(abs(z - zi) for zi in hauts[s] + bas[s] + libres)))
        for i, z in enumerate(sorted(libres, reverse=True)):
            place(b, "mobilier", "parasol", (s * 50.3, 0, z), group=f"Bourg/Details/Parasol{cote}{i}", variant=i + (s > 0),
                  demi=2.6, emprise=(6, 6, 9))
            place(b, "mobilier", "jardiniere", (s * 46.9, 0, z), yaw=face_couloir(s), group=f"Bourg/Details/Jardiniere{cote}{i}",
                  variant=i + (s > 0), emprise=(3, 1, 2))


# ---------------------------------------------------------------------------
# Port (z -204 → -292)
# ---------------------------------------------------------------------------

def port(b: Builder) -> None:
    """Quais, pontons, navires à quai, phare sur sa jetée, barques, îlots, plages au pied des collines."""
    # côté gauche : ponton long, grand galion à quai, navire au mouillage au large
    place(b, "port", "ponton", (-X_BORD, 0, -212), yaw=90, group="Port/PontonG", variant=0, longueur=64, largeur=8,
          emprise=(8, 64, 4), attente="devant")
    # passerelle = x local du bout de la passerelle : elle mord de 1,5 sur la margelle du quai (|x| = 53,5)
    xg = -82
    place(b, "port", "galion", (xg, Y_EAU, -256), yaw=0, group="Port/Galion", variant=0, longueur=72, passerelle=-xg - X_BORD + 1.5,
          emprise=(22, 72, 70))
    place(b, "port", "galion", (-182, Y_EAU, -294), yaw=200, group="Port/GalionLarge", variant=2, longueur=60,
          emprise=(20, 60, 60))
    # caravelle turquoise au mouillage à droite de la place (répond au galion aux voiles rouges)
    place(b, "port", "caravelle", (156, Y_EAU, -314), yaw=160, group="Port/CaravelleLarge", variant=1, longueur=48,
          emprise=(18, 48, 46))
    # côté droit : jetée de pierre et phare, caravelle, ponton des pêcheurs
    x_phare, z_phare = 124, -216
    place(b, "port", "ponton", (X_BORD, 0, z_phare), yaw=-90, group="Port/Jetee", variant=2, longueur=x_phare - 10 - X_BORD,
          largeur=8, emprise=(8, 59, 4), attente="devant")
    place(b, "port", "phare", (x_phare, 0, z_phare), group="Port/Phare", variant=0, hauteur=64, emprise=(22, 22, 64))
    xc = 78
    place(b, "port", "caravelle", (xc, Y_EAU, -252), yaw=180, group="Port/Caravelle", variant=0, longueur=52,
          passerelle=xc - X_BORD + 1.5, emprise=(18, 52, 50))
    place(b, "port", "ponton", (X_BORD, 0, -286), yaw=-90, group="Port/PontonD", variant=1, longueur=48, largeur=6,
          emprise=(6, 48, 4), attente="devant")
    for i, (x, z, yaw, v) in enumerate(((-108, -226, 80, 0), (-130, -228, 100, 1), (100, -278, 260, 2), (116, -292, 280, 0),
                                        (156, -240, 30, 1))):
        place(b, "port", "barque", (x, Y_EAU, z), yaw=yaw, group=f"Port/Barque{i}", variant=v, emprise=(4, 9, 2))
    # îlots rocheux à palmiers au large
    for i, (x, z, r, v) in enumerate(((-190, -252, 16, 0), (194, -262, 13, 1), (-104, -330, 10, 2), (108, -332, 9, 3))):
        place(b, "nature", "ilot", (x, Y_EAU, z), group=f"Port/Ilot{i}", variant=v, rayon=r, emprise=(2 * r, 2 * r, 14))
    # plages au pied des collines : palmiers, rochers, crabes, coquillages
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        for i, (dx, z) in enumerate(((152, -206), (172, -214), (196, -208), (212, -219))):
            place(b, "nature", "palmier", (s * dx, -0.6, z), yaw=i * 70 + (s > 0) * 30, group=f"Port/Plage{cote}/Palmier{i}",
                  variant=(i + (s > 0)) % 3, hauteur=13 + 3 * (i % 2), emprise=(8, 8, 16))
        for i, (dx, z) in enumerate(((144, -219), (186, -221))):
            place(b, "nature", "rocher", (s * dx, -0.6, z), yaw=i * 50, group=f"Port/Plage{cote}/Rocher{i}", variant=i, taille=1.0,
                  emprise=(6, 6, 4))
        place(b, "mobilier", "crabe", (s * 162, -0.6, -218), yaw=s * 40, group=f"Port/Plage{cote}/Crabe", emprise=(2, 2, 1))
        place(b, "mobilier", "coquillages", (s * 182, -0.6, -212), group=f"Port/Plage{cote}/Coquillages", variant=(s > 0),
              emprise=(3, 3, 1))
    # quais : bittes, lanternes, canons pointés vers le large, filets
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        for i, z in enumerate(range(-218, -280, -14)):
            place(b, "mobilier", "bitte", (s * 53.8, 0, z), group=f"Port/Quai{cote}/Bitte{i}", variant=0, emprise=(2, 2, 2))
        for i, z in enumerate((-224, -250, -276)):
            place(b, "mobilier", "lanterne_quai", (s * 51.5, 0, z), yaw=face_couloir(s), group=f"Port/Quai{cote}/Lanterne{i}",
                  variant=0, emprise=(2, 2, 11))
        for i, z in enumerate((-238, -268)):
            place(b, "mobilier", "canon", (s * 50.6, 0, z), yaw=face_large(s), group=f"Port/Quai{cote}/Canon{i}", variant=i,
                  emprise=(3, 5, 3))
        place(b, "mobilier", "tonneaux", (s * 50.5, 0, -244), yaw=s * 20, group=f"Port/Quai{cote}/Tonneaux", variant=1 + (s > 0),
              emprise=(4, 4, 4))
        place(b, "mobilier", "caisses", (s * 50.5, 0, -258), yaw=face_couloir(s), group=f"Port/Quai{cote}/Caisses",
              variant=(s > 0) * 2, emprise=(5, 3, 4))
    place(b, "mobilier", "filet_peche", (-88, 0, -209.6), yaw=180, group="Port/PontonG/Filet", variant=0, emprise=(7, 1, 7))
    place(b, "batiments", "etal", (51, 0, -284), yaw=90, group="Port/EtalPoissons", variant=2, emprise=(8, 6, 11))
    place(b, "mobilier", "panneau", (-51, 0, -208), yaw=-90, group="Port/PanneauPort", texte="PORT", variant=2, emprise=(6, 1, 6))
    place(b, "mobilier", "panneau", (51, 0, -208), yaw=90, group="Port/PanneauPhare", texte="PHARE", variant=2, emprise=(6, 1, 6))


# ---------------------------------------------------------------------------
# Place des œufs (grand ponton, z -292 → -366)
# ---------------------------------------------------------------------------

def place_oeufs(b: Builder) -> None:
    """Grand ponton à rose des vents : bordure de poutres, pieux et cordages, mâts de vigie, canons, trésors."""
    with b.group("Place/Ponton"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_PLACE))
            sol_pixel(b, xa, xb, Z_ROCHER, Z_PONTON, 2, planches, name="Plancher")
            # poutre de rive (bord épais au-dessus de l'eau)
            # (dépasse de 0,1 du plancher pour éviter les faces coplanaires)
            xa, xb = sorted((s * (X_PLACE - 1), s * (X_PLACE + 0.1)))
            b.box((xa, -2.6, Z_ROCHER), (xb, 0.4, Z_PONTON + 0.1), c("bois_fonce"), studs="top", name="PoutreRive")
            xa, xb = sorted((s * X_BORD, s * (X_PLACE - 1)))
            b.box((xa, -2.6, Z_PONTON - 1), (xb, 0.4, Z_PONTON + 0.1), c("bois_fonce"), studs="top", name="PoutreRive")
    fcord = _asset("mobilier", "cordage")
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        # pieux et cordage le long de la rive extérieure
        zs = list(range(Z_PONTON - 4, Z_ROCHER + 3, -8))
        for i, z in enumerate(zs):
            place(b, "mobilier", "bitte", (s * (X_PLACE - 1.8), 0, z), group=f"Place/Rive{cote}/Pieu{i:02d}", variant=1, emprise=(2, 2, 4))
        if fcord:
            with b.group(f"Place/Rive{cote}/Cordage"):
                for za, zb in zip(zs, zs[1:]):
                    fcord(b, (s * (X_PLACE - 1.8), 3.0, za), (s * (X_PLACE - 1.8), 3.0, zb), creux=0.7)
        # mâts de vigie aux quatre coins, guirlande haute entre les mâts
        for i, z in enumerate((Z_PLACE + 28, Z_PLACE - 28)):
            place(b, "mobilier", "mat_vigie", (s * 62, 0, z), yaw=0, group=f"Place/Mat{cote}{i}", hauteur=36, variant=i,
                  emprise=(11, 5, 40))
        # trésors, canons vers le large, ancre et barre
        place(b, "mobilier", "coffre_tresor", (s * 56, 0, Z_PLACE + 10), yaw=face_couloir(s), group=f"Place/Coffre{cote}",
              variant=0 if s < 0 else 2, emprise=(4, 3, 3))
        for i, z in enumerate((Z_PLACE + 16, Z_PLACE - 16)):
            place(b, "mobilier", "canon", (s * 66, 0, z), yaw=face_large(s), group=f"Place/Canon{cote}{i}", variant=1 if i else 2,
                  emprise=(7, 5, 3))
        place(b, "mobilier", "tonneaux", (s * 64, 0, Z_PLACE), yaw=s * 15, group=f"Place/Tonneaux{cote}", variant=0, emprise=(4, 4, 3))
        place(b, "mobilier", "caisses", (s * 57, 0, Z_PLACE - 22), yaw=face_couloir(s), group=f"Place/Caisses{cote}", variant=2,
              emprise=(5, 3, 4))
    place(b, "mobilier", "ancre", (-57, 0, Z_PLACE - 8), yaw=face_couloir(-1), group="Place/Ancre", variant=1, emprise=(7, 3, 11))
    place(b, "mobilier", "barre_navire", (57, 0, Z_PLACE - 8), yaw=face_couloir(1), group="Place/Barre", taille=1.4, variant=1,
          emprise=(7, 3, 9))
    place(b, "mobilier", "panneau", (52, 0, Z_PONTON - 4), yaw=90, group="Place/PanneauTresor", texte="TRÉSOR", variant=1,
          emprise=(8, 1, 6))
    f = _asset("mobilier", "guirlande_fanions")
    if f:
        # une seule guirlande haute, côté port : celle du fond passerait devant la mâchoire du crâne
        with b.group("Place/GuirlandeHaute0"):
            f(b, (-61.2, 38.0, Z_PLACE + 28), (61.2, 38.0, Z_PLACE + 28), n=24, creux=3.0, variant=1)
        for s in (-1, 1):
            with b.group(f"Place/GuirlandeCote{'G' if s < 0 else 'D'}"):
                f(b, (s * 62, 32.0, Z_PLACE + 27), (s * 62, 32.0, Z_PLACE - 27), n=12, creux=2.5, variant=2)


def abords(b: Builder) -> None:
    """Abords de l'arche (côté apparition) : palmiers, rochers, buissons, panneau de bienvenue."""
    for s in (-1, 1):
        for i, (dx, dz, kind) in enumerate(((64, 16, "palmier"), (80, 32, "palmier"), (96, 20, "rocher"), (110, 34, "palmier"),
                                            (122, 14, "buisson"), (132, 28, "palmier"))):
            kw = {"hauteur": 14 + 2 * (i % 2)} if kind == "palmier" else {}
            place(b, "nature", kind, (s * dx, 0, Z_PORTE + dz), yaw=i * 50, group=f"Abords/{'G' if s < 0 else 'D'}{i}",
                  variant=(i + (s > 0)) % 3, emprise=(8, 8, 14), **kw)
    place(b, "mobilier", "panneau", (52.5, 0, Z_PORTE + 22), yaw=180, group="Abords/Bienvenue", texte="BIENVENUE", variant=1,
          emprise=(12, 1, 6))


def reperes(b: Builder) -> None:
    """Pièces invisibles utiles au jeu : zone des œufs, entrée, sortie, couloir."""
    inv = dict(transparency=1.0, collide=False, shadow=False)
    with b.group("Reperes"):
        b.box((-R_PLACE, 0, Z_PLACE - R_PLACE), (R_PLACE, 1, Z_PLACE + R_PLACE), "#ffffff", name="ZoneOeufs", **inv)
        b.box((-DEMI_COULOIR, 0, Z_PORTE + 18), (DEMI_COULOIR, 1, Z_PORTE + 24), "#ffffff", name="Entree", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE), (DEMI_COULOIR, 1, Z_SORTIE + 6), "#ffffff", name="Sortie", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE), (DEMI_COULOIR, 1, Z_PORTE), "#ffffff", name="Couloir", **inv)


def limites(b: Builder) -> None:
    """Murs invisibles au bord de la carte (|x| = 220) : on ne sort pas de la zone en marchant sur la mer."""
    with b.group("Limites"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_FOND, s * (X_FOND + 1)))
            b.box((xa, -3, Z_SORTIE), (xb, 80, Z_APPROCHE), "#ffffff", transparency=1.0, shadow=False, name="MurInvisible")


# petits détails de façade et de clôture : sans collision (ils ne servent à rien en jeu et chargent la physique)
DETAILS_SANS_COLLISION = {"Cadre", "Vitre", "Appui", "Volet", "Chambranle", "Tablette", "Lisse", "Croisillon", "Corbeau",
                          "Bandeau", "Chaine", "Poignee", "Imposte", "Pot", "Fleur"}
RACINES_SOL = ("Sol", "Eau", "Collines", "Reperes", "Limites", "Abords/Sol", "Abords/Collines")


def est_sol(groupe: str) -> bool:
    return groupe.startswith(("Sol", "Reperes", "Abords/Sol"))


def alleger(b: Builder) -> dict:
    """Allège la physique et les ombres dans Roblox : pas de collision sur les petits détails (volume < 1 ou noms
    de `DETAILS_SANS_COLLISION`), pas d'ombre portée pour les petits détails sans collision (volume < 2)."""
    n_col = n_omb = 0
    for p in b.parts:
        if p.group.startswith(RACINES_SOL) or p.transparency >= 1:
            continue
        vol = p.size[0] * p.size[1] * p.size[2]
        if p.collide and (vol < 1.0 or (p.name in DETAILS_SANS_COLLISION and vol < 8.0)):
            p.collide = False
            n_col += 1
        if not p.collide and p.shadow and vol < 2.0:
            p.shadow = False
            n_omb += 1
    return {"sans_collision": n_col, "sans_ombre": n_omb}


def decouper(b: Builder, prefixes=("Sol/", "Eau", "Collines/", "Monuments/Rocher", "Monuments/Porte", "Abords/Sol/",
                                   "Abords/Collines/"), taille: float = 64) -> None:
    """Range les pièces des grands ensembles dans des sous-modèles de 64 × 64 studs (streaming Roblox)."""
    for p in b.parts:
        if p.group.startswith(prefixes):
            i, j = math.floor(p.pos[0] / taille), math.floor(p.pos[2] / taille)
            racine = "/".join(p.group.split("/")[:3 if p.group.startswith("Abords/") else 2])
            reste = p.group[len(racine):]
            p.group = f"{racine}/Bloc_{i:+d}_{j:+d}{reste}"


def build_zone(seed: int = 7) -> Builder:
    b = Builder(seed=seed)
    b.poses = []
    sol_couloir(b)
    sol_trottoirs(b)
    sol_cotes(b)
    eau(b)
    sommets, gradins = collines_laterales(b)
    place(b, "monuments", "porte_entree", (0, 0, Z_PORTE), group="Monuments/Porte", emprise=(2 * X_COLLINES, 12, 50),
          attente="arche", ouverture=2 * X_BORD, hauteur=50, mur=X_COLLINES)
    place(b, "monuments", "rocher_crane", (0, 0, Z_ROCHER), group="Monuments/Rocher", emprise=(2 * X_FOND, PROF_ROCHER, H_ROCHER),
          attente="arche_devant", passage=PASSAGE, largeur=2 * X_FOND, profondeur=PROF_ROCHER, hauteur=H_ROCHER,
          x_ecume=X_PLACE + 0.2)
    campagne(b, sommets)
    habiller_collines(b, gradins)
    poses_g, poses_d = bourg(b)
    guirlandes(b, Z_GUIRLANDES_BOURG, "Bourg", (H_GUIRLANDE, H_GUIRLANDE_HAUTE, H_GUIRLANDE))
    details_bourg(b, poses_g, poses_d)
    port(b)
    guirlandes(b, Z_GUIRLANDES_PORT, "Port", (H_GUIRLANDE_HAUTE, H_GUIRLANDE))
    place_oeufs(b)
    abords(b)
    reperes(b)
    limites(b)
    b.allegement = alleger(b)
    decouper(b)
    return b


# ---------------------------------------------------------------------------
# Contrôles
# ---------------------------------------------------------------------------

def _aabb(p):
    R = np.asarray(p.rot).reshape(3, 3)
    half = np.abs(R) @ (np.asarray(p.size) / 2)
    return np.asarray(p.pos) - half, np.asarray(p.pos) + half


def couloir_libre(b: Builder) -> list:
    """Liste ce qui encombre le couloir de course au sol (hors sol et repères)."""
    gene = []
    for p in b.parts:
        if not p.collide or est_sol(p.group):
            continue
        lo, hi = _aabb(p)
        if lo[0] < DEMI_COULOIR - 0.05 and hi[0] > -DEMI_COULOIR + 0.05 and lo[1] < 12 and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            gene.append((p.group, p.name, [round(v, 1) for v in lo], [round(v, 1) for v in hi]))
    return gene


def trop_bas_au_dessus(b: Builder, y_min: float = 30.0) -> list:
    """Pièces au-dessus du couloir (|x| < 46) mais sous `y_min` (la caméra Roblox sauterait en passant dessous)."""
    out = []
    for p in b.parts:
        if est_sol(p.group):
            continue
        lo, hi = _aabb(p)
        if lo[0] < X_LIBRE_HAUT and hi[0] > -X_LIBRE_HAUT and lo[1] < y_min and hi[1] > 12 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name, round(lo[1], 1)))
    return out


def decor_dans_couloir(b: Builder) -> list:
    """Petits détails sans collision posés dans le couloir au sol (fleurs, cordages…) : à éviter aussi."""
    out = []
    for p in b.parts:
        if p.collide or est_sol(p.group) or p.transparency >= 1:
            continue
        lo, hi = _aabb(p)
        if lo[0] < DEMI_COULOIR - 0.05 and hi[0] > -DEMI_COULOIR + 0.05 and lo[1] < 12 and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name))
    return out


FEUILLAGES = ("palmier", "buisson", "oranger")


def _obb(p):
    return np.asarray(p.pos, float), np.asarray(p.rot, float).reshape(3, 3), np.asarray(p.size, float) / 2


def _penetration(a, bb) -> float:
    """Profondeur d'interpénétration de deux boîtes orientées (axes séparateurs) ; 0 si elles ne se touchent pas.
    Coins, cylindres et boules sont traités comme leur boîte englobante (contrôle prudent)."""
    ca, Ra, ha = a
    cb, Rb, hb = bb
    T = cb - ca
    axes = [Ra[:, i] for i in range(3)] + [Rb[:, j] for j in range(3)]
    for i in range(3):
        for j in range(3):
            v = np.cross(Ra[:, i], Rb[:, j])
            n = np.linalg.norm(v)
            if n > 1e-6:
                axes.append(v / n)
    best = math.inf
    for L in axes:
        ra = float(np.abs(Ra.T @ L) @ ha)
        rb = float(np.abs(Rb.T @ L) @ hb)
        d = ra + rb - abs(float(T @ L))
        if d <= 0:
            return 0.0
        best = min(best, d)
    return best


def chevauchements(b: Builder, tol: float = 0.25, cellule: float = 16.0) -> dict:
    """Assets posés qui se recoupent : pour chaque paire de poses, nombre de paires de pièces qui s'interpénètrent
    de plus de `tol` et profondeur maximale. Le sol plat et l'eau sont ignorés (tout y est posé) ; la terrasse, son
    mur, les collines, les escaliers et le ponton de la place comptent comme des poses. Les feuillages (palmiers,
    buissons, mandariniers) qui débordent sur un voisin sont rangés à part (`feuillage`)."""
    n = len(b.parts)
    etiquette = [None] * n
    fonction = [""] * n
    for (g, fn, n0, n1) in getattr(b, "poses", []):
        for i in range(n0, n1):
            etiquette[i], fonction[i] = g, fn
    actifs = []
    for i, p in enumerate(b.parts):
        if p.transparency >= 1:
            continue
        if etiquette[i] is None:
            racine = p.group.split("/")[0]
            if racine in ("Eau", "Reperes", "Limites"):
                continue
            lo, hi = _aabb(p)
            sol = est_sol(p.group)
            if sol and hi[1] <= 0.6:
                continue
            parts = p.group.split("/")
            etiquette[i] = "/".join(parts[:2]) if not sol else f"Sol/{p.name}"
        actifs.append(i)
    boites = {i: _aabb(b.parts[i]) for i in actifs}
    grille: dict = {}
    for i in actifs:
        lo, hi = boites[i]
        for gx in range(math.floor(lo[0] / cellule), math.floor(hi[0] / cellule) + 1):
            for gz in range(math.floor(lo[2] / cellule), math.floor(hi[2] / cellule) + 1):
                grille.setdefault((gx, gz), []).append(i)
    vus = set()
    res: dict = {}
    for liste in grille.values():
        for a_i, i in enumerate(liste):
            lo_i, hi_i = boites[i]
            for j in liste[a_i + 1:]:
                if etiquette[i] == etiquette[j]:
                    continue
                key = (i, j) if i < j else (j, i)
                if key in vus:
                    continue
                vus.add(key)
                lo_j, hi_j = boites[j]
                if np.any(np.minimum(hi_i, hi_j) - np.maximum(lo_i, lo_j) <= tol):
                    continue
                d = _penetration(_obb(b.parts[i]), _obb(b.parts[j]))
                if d <= tol:
                    continue
                ga, gb = sorted((etiquette[i], etiquette[j]))
                feuille = any(fonction[k] in FEUILLAGES and not b.parts[k].collide for k in (i, j))
                r = res.setdefault((ga, gb), {"paires": 0, "profondeur": 0.0, "feuillage": True, "exemple": None})
                r["paires"] += 1
                r["feuillage"] = r["feuillage"] and feuille
                if d > r["profondeur"]:
                    r["profondeur"] = round(d, 2)
                    r["exemple"] = (b.parts[i].name, b.parts[j].name)
    return res


def meta() -> dict:
    return {"nom": "ZoneOnePiece", "version": VERSION, "largeur_couloir": 2 * DEMI_COULOIR,
            "longueur": -Z_SORTIE, "spawn": [0, 0, Z_PORTE + 30]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / "build" / "parts.json"))
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--chevauchements", action="store_true", help="liste les assets posés qui se recoupent")
    args = ap.parse_args()
    b = build_zone()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    b.save_json(out, meta=meta())
    attente = sorted({p.name for p in b.parts if p.name.startswith("ATTENTE_")})
    gene = couloir_libre(b)
    bas = trop_bas_au_dessus(b)
    deco = decor_dans_couloir(b)
    print(json.dumps({"pieces": len(b.parts), "fichier": str(out), "en_attente": attente,
                      "allegement": getattr(b, "allegement", {}),
                      "couloir_encombre": gene[:20], "nb_couloir_encombre": len(gene),
                      "trop_bas_au_dessus_du_couloir": bas[:20], "decor_dans_couloir": deco[:20]}, ensure_ascii=False))
    if args.stats:
        for k, v in b.stats().items():
            print(f"{v:6d}  {k}")
    if args.chevauchements:
        res = chevauchements(b)
        durs = {k: v for k, v in res.items() if not v["feuillage"]}
        print(f"chevauchements : {len(durs)} paires de poses (+ {len(res) - len(durs)} de feuillage)")
        for (ga, gb), v in sorted(res.items(), key=lambda kv: -kv[1]["profondeur"]):
            tag = "feuillage " if v["feuillage"] else ""
            print(f"  {tag}{v['profondeur']:6.2f}  {v['paires']:4d}  {ga}  <->  {gb}   {v['exemple']}")


if __name__ == "__main__":
    main()
