#!/usr/bin/env python3
"""Plan de la zone One Piece (mer de l'Est : campagne aux moulins, bourg du port, port pirate, crique du crâne)
en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course occupe x ∈ [-30, 30], bordé de trottoirs ou de quais jusqu'à |x| = 40 ;
- on entre sous l'arche du port en z = 0 et on court vers -Z : campagne aux moulins (jusqu'à -112),
  bourg du port aux maisons colorées (-112 → -204), port pirate entre deux bassins turquoise avec les
  navires à quai et le phare (-204 → -294), place des œufs sur un grand ponton à rose des vents
  (centre z = -328), puis le rocher du crâne (façade en z = -366) que le couloir traverse par la bouche
  jusqu'à la zone suivante (z = -400) ;
- des collines vertes en gradins ferment les côtés de la campagne et du bourg (|x| ≥ 130), la pleine mer
  s'ouvre de chaque côté du port et de la place.

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
X_BORD = 40              # bord des trottoirs, des quais et alignement des façades
X_TERRASSE = 76          # mur de soutènement de la terrasse haute du bourg
Y_TERRASSE = 6
X_COLLINES = 130         # début des collines latérales (campagne et bourg)
X_FOND = 220             # limite du décor (collines, mer)
X_PLACE = 56             # demi-largeur du grand ponton de la place des œufs
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
Z_PLAGE = -224           # plages au pied des collines (|x| ≥ 130), de Z_PORT + 4 à Z_PLAGE
Y_EAU = -1.5             # surface de l'eau (les quais et le sol sont à y = 0)
H_GUIRLANDE = 37         # corde des fanions : la pointe des fanions reste au-dessus de 31 studs

VERSION = "0.1"


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

    `attente` décrit le bloc d'attente : « centre » (emprise centrée sur l'origine), « devant » (de z = -d à 0 :
    pontons, rocher), « arche » (deux piles hors de l'ouverture `params['ouverture' | 'passage']` et un linteau
    au-dessus de y = 36), « arche_devant » (arche de z = -d à 0)."""
    f = _asset(module, fn)
    with b.at(pos, yaw=yaw, group=group):
        if f is not None:
            n0 = len(b.parts)
            try:
                return f(b, **params) or {}
            except NotImplementedError:
                del b.parts[n0:]
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
        return {"emprise": (w, d), "hauteur": h}


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
    """Remplit [x0, x1] × [z0, z1] ; couleur(x, z) → (r, g, b) évaluée au centre de chaque case, cases fusionnées.
    Une case dont la couleur vaut None reste vide."""
    nx, nz = int(round((x1 - x0) / cell)), int(round((z1 - z0) / cell))
    if nx <= 0 or nz <= 0:
        return 0
    grid = np.empty((nz, nx), dtype=object)
    for j in range(nz):
        for i in range(nx):
            v = couleur(x0 + (i + 0.5) * cell, z0 + (j + 0.5) * cell)
            grid[j, i] = tuple(v) if v is not None else None
    n = 0
    for col in set(grid.reshape(-1)):
        if col is None:
            continue
        mask = np.vectorize(lambda v, col=col: v == col)(grid)
        for (i, j, w, h) in mask_rects(mask):
            b.box((x0 + i * cell, y_haut - epaisseur, z0 + j * cell),
                  (x0 + (i + w) * cell, y_haut, z0 + (j + h) * cell), col, studs=studs, name=name, **kw)
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
            L, w = (26.0, 4.6) if longues else (17.0, 3.4)
            if 0 <= le <= L and abs(tr) <= w * (1 - le / L):
                if longues and k == 90:
                    return c("rouge") if tr >= 0 else c("rouge_fonce")
                if longues:
                    return c("voile") if tr >= 0 else c("bleu_marine")
                return c("jaune") if tr >= 0 else c("jaune_fonce")
    if 21 <= d < 22.5:
        return c("bleu_marine")                 # cercle des degrés
    if 22.5 <= d < 25 and int((th + 360) % 360 // 11.25) % 2 == 0:
        return c("bois_fonce")                  # graduations
    return c("bois_pale") if int(d // 5) % 2 == 0 else c("bois_clair")


def planches(x: float, z: float, rangee: float = 4.0, longueur: float = 20.0):
    """Plancher de quai : planches posées en travers (selon X), rangées de 4 studs, joints décalés."""
    r = math.floor(z / rangee)
    decal = longueur / 2 if r % 2 else 0.0
    k = math.floor((x + decal) / longueur)
    tons = (c("bois_quai"), c("bois_clair"), shade(c("bois_quai"), 0.92))
    return tons[_h(r, k) % 3]


# ---------------------------------------------------------------------------
# Sols : couloir, trottoirs et quais, côtés, eau
# ---------------------------------------------------------------------------

def sol_couloir(b: Builder) -> None:
    ch, chc, chf = c("chemin"), c("chemin_clair"), c("chemin_fonce")
    pave, pavef, paver = c("pave"), c("pave_fonce"), c("pave_rose")
    sab, sabm = c("sable"), c("sable_mouille")

    def couloir(x, z):
        m = rose_des_vents(x, z)
        if m:
            return m
        if z > Z_BOURG:            # campagne : chemin de terre en grandes plaques, deux ornières continues
            if 8 <= abs(x) < 10:
                return chf
            return ch if (math.floor(z / 12) + (abs(x) >= 10)) % 2 == 0 else chc
        if z > Z_PORT:             # bourg : grandes dalles ocre en quinconce, médaillons roses
            r = math.floor(z / 8)
            k = math.floor((x + (5 if r % 2 else 0)) / 10)
            if abs(x) < 5 and r % 4 == 0:
                return paver
            return pave if (k + r) % 2 == 0 else pavef
        if z > Z_ROCHER:           # port et place : plancher de quai
            return planches(x, z)
        return sab if math.floor(z / 8) % 2 else sabm   # passage du rocher : sable

    z_fin = Z_SORTIE - 4
    zp_bas, zp_haut = Z_PLACE - R_PLACE, Z_PLACE + R_PLACE
    with b.group("Sol/Couloir"):
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, Z_PORT, Z_APPROCHE, 2, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, zp_haut, Z_PORT, 2, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, zp_bas, zp_haut, 2, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, z_fin, zp_bas, 2, couloir)


def sol_trottoirs(b: Builder) -> None:
    """Bandes 30 ≤ |x| ≤ 40 : accotement herbeux (campagne), trottoir (bourg), quai de pierre (port),
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
            if ax < 32:
                return chc
            return h if math.floor(z / 16) % 2 == 0 else hc
        if z > Z_PORT:
            if ax < 31:
                return bord
            return pc if math.floor(z / 6) % 2 == 0 else p
        if z > Z_ROCHER:
            if Z_PONTON >= z:
                return planches(x, z)
            if ax < 31:
                return bord
            return pc if math.floor(z / 8) % 2 == 0 else p
        return c("sable")

    z_fin = Z_SORTIE - 4
    with b.group("Sol/Trottoirs"):
        for s in (-1, 1):
            xa, xb = sorted((s * DEMI_COULOIR, s * (X_BORD - 2)))
            sol_pixel(b, xa, xb, z_fin, Z_APPROCHE, 2, trottoir)
            # bande extérieure : herbe/pavés normaux, margelle épaisse (mur de quai) le long des bassins
            xa, xb = sorted((s * (X_BORD - 2), s * X_BORD))
            sol_pixel(b, xa, xb, Z_PORT, Z_APPROCHE, 2, trottoir)
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
        for zc in (-42, -92):                       # chemins de ferme vers les granges
            if zc - 2 <= z < zc + 2:
                return ch
        if Z_PORTE - 6 <= z < Z_PORTE + 6 and ax < 52:   # dallage au pied de l'arche
            return chc
        return h if (math.floor(x / 24) + math.floor(z / 24)) % 2 == 0 else hc

    def bourg(x, z):
        ax = abs(x)
        if ax < 66:                                  # cours des maisons (en grande partie sous les maisons)
            return pave if math.floor(z / 8) % 2 == 0 else pavef
        return chc if (math.floor(z / 8) % 3 == 0) else pave   # ruelle au pied du mur

    with b.group("Sol/Cotes"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_COLLINES))
            sol_pixel(b, xa, xb, Z_BOURG, Z_PORTE + 8, 4, campagne)
            xa, xb = sorted((s * X_BORD, s * X_TERRASSE))
            sol_pixel(b, xa, xb, Z_PORT + 2, Z_BOURG, 2, bourg)
            # quai du bourg face au bassin (mur visible au-dessus de l'eau)
            sol_pixel(b, xa, xb, Z_PORT, Z_PORT + 2, 2, lambda x, z: c("pierre_fonce"), epaisseur=5, name="Margelle")
            # terrasse haute (jardins, pavés) et son mur de soutènement
            xa, xb = sorted((s * (X_TERRASSE + 1), s * X_COLLINES))
            sol_pixel(b, xa, xb, Z_PORT, Z_BOURG, 4,
                      lambda x, z: (hf if (math.floor(z / 24) + math.floor(abs(x) / 24)) % 2 else h)
                      if abs(x) > 85 else (pave if math.floor(z / 8) % 2 else pavef),
                      y_haut=Y_TERRASSE, epaisseur=Y_TERRASSE + 6, name="Terrasse")
            xa, xb = sorted((s * X_TERRASSE, s * (X_TERRASSE + 1)))
            b.box((xa, -1, Z_PORT), (xb, Y_TERRASSE + 1.2, Z_BOURG), c("pierre"), studs="top", name="MurTerrasse")
    with b.group("Sol/Abords"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_COLLINES))
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


def collines_laterales(b: Builder) -> list:
    """Collines vertes en trois gradins (|x| ≥ 130) : chapeau d'herbe débordant, flanc de terre à strates claires.
    Elles descendent en marches vers la mer au bout du bourg. Renvoie les sommets (x, y, z) pour les moulins."""
    rng = np.random.default_rng(5)
    sommets = []
    terre, terre_f, terre_c = c("terre"), c("terre_fonce"), c("terre_claire")
    herbes = (c("herbe"), c("herbe_claire"), c("herbe_fonce"))
    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        z, k = Z_APPROCHE, 0
        while z > Z_PORT + 8 + 0.01:
            l = min(16, z - (Z_PORT + 8))
            descente = max(0.0, (z - l - (-150)) / -50.0)          # 0 → 1 sur les 50 derniers studs
            gradins = ((X_COLLINES, X_COLLINES + 20, 5 + 3 * (k % 3)),
                       (X_COLLINES + 20, X_COLLINES + 52, 14 + 5 * math.sin(k * 0.9) + rng.uniform(0, 3)),
                       (X_COLLINES + 52, X_FOND, 26 + 7 * math.sin(k * 0.55 + 1.0) + rng.uniform(0, 4)))
            with b.group(f"Collines/{cote}"):
                for gi, (xa_, xb_, hg) in enumerate(gradins):
                    hg = max(2, round(hg * (1 - 0.75 * descente)))
                    xa, xb = sorted((s * xa_, s * xb_))
                    b.box((xa, 0, z - l), (xb, hg - 1.5, z), terre if (k + gi) % 2 else terre_f, name="Flanc")
                    # strate claire côté vallée
                    fa = s * xa_
                    sa, sb = sorted((fa - s * 0.2, fa + s * 0.8))
                    if hg > 6:
                        b.box((sa, hg * 0.45, z - l), (sb, hg * 0.45 + 1, z), terre_c, collide=False, name="Strate")
                    # chapeau d'herbe qui déborde un peu côté vallée
                    ca, cb = sorted((fa - s * 0.6, s * xb_))
                    b.box((ca, hg - 1.5, z - l), (cb, hg, z), herbes[(k + gi) % 3], studs="top", name="Herbe")
                    if gi == 1:
                        sommets.append((s * (xa_ + xb_) / 2, hg, z - l / 2))
            z -= l
            k += 1
    return sommets


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


def campagne(b: Builder, sommets: list) -> None:
    """Prairies, clôtures le long du chemin, moulins (bois à ailes jaunes, tour rose, tours de pierre à dôme),
    granges rouges, vaches, foin, verger de mandarines."""
    # clôtures le long du chemin (bord extérieur de l'accotement), interrompues aux chemins de ferme
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        for i, (za, zb) in enumerate(((-6, -38), (-46, -88), (-96, -110))):
            place(b, "mobilier", "cloture_bois", (s * 39, 0, (za + zb) / 2), yaw=face_couloir(s), group=f"Campagne/Cloture{cote}{i}",
                  longueur=abs(zb - za), variant=2, emprise=(abs(zb - za), 1, 4))
    # moulins près du chemin (ailes face aux joueurs qui arrivent : yaw 180 → avant vers +Z)
    moulins = [(-60, 0, -24, 0, 30, 180), (64, 0, -64, 1, 28, 200), (-98, 0, -100, 2, 26, 160)]
    for i, (x, y, z, v, h, yaw) in enumerate(moulins):
        place(b, "nature", "moulin", (x, y, z), yaw=yaw, group=f"Campagne/Moulin{i}", variant=v, hauteur=h, emprise=(12, 12, h))
    # butte et moulin de pierre sur la droite
    place(b, "nature", "colline", (102, 0, -24), yaw=90, group="Campagne/Butte", variant=0, largeur=40, profondeur=36, hauteur=8,
          emprise=(40, 36, 8))
    place(b, "nature", "moulin", (102, 8, -24), yaw=150, group="Campagne/MoulinButte", variant=2, hauteur=24, emprise=(12, 12, 24))
    # moulins sur les collines latérales (gradin du milieu)
    for i in range(2):
        for s in (-1, 1):
            cand = [p for p in sommets if (p[0] < 0) == (s < 0)]
            k = ((3, 9) if s < 0 else (5, 11))[i]
            if k < len(cand):
                x, y, z = cand[k]
                place(b, "nature", "moulin", (x, y, z), yaw=180 + s * 20, group=f"Campagne/MoulinColline{'G' if s < 0 else 'D'}{i}",
                      variant=(i + (s > 0) + 1) % 4, hauteur=22, emprise=(10, 10, 22))
    # granges
    place(b, "batiments", "grange", (-104, 0, -62), yaw=-90, group="Campagne/GrangeG", variant=0, largeur=22, profondeur=16,
          emprise=(22, 16, 18))
    place(b, "batiments", "grange", (64, 0, -100), yaw=90, group="Campagne/GrangeD", variant=1, largeur=18, profondeur=14,
          emprise=(18, 14, 16))
    # enclos à vaches
    enclos(b, -122, -74, -10, -40, 0, "Campagne/EnclosG", ouverture="x1")
    enclos(b, 80, 124, -60, -106, 0, "Campagne/EnclosD", ouverture="x0")
    for i, (x, z, yaw, v) in enumerate(((-90, -20, 30, 0), (-108, -30, 200, 1), (-84, -34, 120, 2),
                                        (96, -74, 250, 1), (112, -90, 20, 0), (100, -98, 150, 2), (90, -88, 300, 0))):
        place(b, "mobilier", "vache", (x, 0, z), yaw=yaw, group=f"Campagne/Vache{i}", variant=v, emprise=(3, 8, 6))
    for i, (x, z, v) in enumerate(((-116, -16, 0), (-78, -54, 1), (-86, -106, 2), (118, -66, 0), (74, -84, 1), (46, -104, 2))):
        place(b, "mobilier", "botte_foin", (x, 0, z), yaw=i * 37, group=f"Campagne/Foin{i}", variant=v, emprise=(5, 5, 4))
    # verger de mandarines
    for i, (x, z) in enumerate(((50, -16), (58, -26), (50, -36), (66, -14), (74, -30), (62, -40))):
        place(b, "nature", "oranger", (x, 0, z), yaw=i * 60, group=f"Campagne/Verger{i}", variant=i % 3, emprise=(6, 6, 8))
    for i, (x, z, v) in enumerate(((-52, -60, 0), (-56, -76, 1), (-48, -104, 2), (54, -50, 0), (76, -48, 1), (-66, -10, 2))):
        place(b, "nature", "buisson", (x, 0, z), group=f"Campagne/Buisson{i}", variant=v, emprise=(4, 4, 3))
    for i, (x, z) in enumerate(((-36, -70), (36, -30))):
        place(b, "mobilier", "panneau", (x, 0, z), yaw=face_couloir(x), group=f"Campagne/Panneau{i}",
              texte=("MOULIN", "FERME")[i], variant=i % 2, emprise=(6, 1, 6))


# ---------------------------------------------------------------------------
# Bourg du port (z -112 → -204)
# ---------------------------------------------------------------------------

RANGEE_GAUCHE = [
    ("batiments:maison_port", 18, 14, {"variant": 0}),
    ("batiments:etal", 8, 6, {"variant": 0}),           # fruits
    ("batiments:maison_port", 16, 14, {"variant": 1}),
    ("batiments:taverne", 24, 20, {"variant": 0}),
    ("batiments:maison_port", 16, 14, {"variant": 2}),
]
RANGEE_DROITE = [
    ("batiments:maison_port", 16, 14, {"variant": 3}),
    ("batiments:maison_port", 20, 16, {"variant": 4}),
    ("batiments:etal", 8, 6, {"variant": 1}),           # viande sur l'os
    ("batiments:maison_port", 18, 14, {"variant": 5}),
    ("batiments:maison_port", 18, 14, {"variant": 0}),
]
ECART = 2.0


def rangee(b: Builder, s: int, plan) -> list:
    """Aligne une rangée du bourg le long du couloir (façades en |x| = 40, avant tourné vers le couloir)."""
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
        poses.append((x, zc, larg, prof, info))
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
        for i, zc in enumerate((-115, -144, -177, -203)):
            place(b, "nature", "palmier", (s * (X_TERRASSE + 6), Y_TERRASSE, zc), yaw=i * 80, group=f"Bourg/Palmier{cote}{i}",
                  variant=i % 3, hauteur=14 + 2 * (i % 2), emprise=(8, 8, 16))
    escaliers_terrasse(b)
    return poses_g, poses_d


def guirlandes(b: Builder, zs, prefixe: str) -> None:
    """Guirlandes de fanions au-dessus du couloir, tendues entre deux mâts plantés sur les trottoirs (|x| = 35)."""
    f = _asset("mobilier", "guirlande_fanions")
    for i, z in enumerate(zs):
        with b.group(f"{prefixe}/Guirlande{i + 1}"):
            for s in (-1, 1):
                place(b, "mobilier", "mat_guirlande", (s * 35, 0, z), group=f"Mat{'G' if s < 0 else 'D'}", hauteur=H_GUIRLANDE + 1,
                      variant=i % 3, emprise=(2, 2, H_GUIRLANDE + 1))
            if f:
                f(b, (-34.4, H_GUIRLANDE, z), (34.4, H_GUIRLANDE, z), n=14, creux=2.5, variant=i % 3)


def details_bourg(b: Builder, poses_g, poses_d) -> None:
    """Lanternes, tonneaux, caisses, panneaux, bancs, viande à la broche devant les façades (|x| ≈ 37)."""
    for s in (-1, 1):
        for i, z in enumerate((-136, -166, -196)):
            x = s * 37.5
            place(b, "mobilier", "lanterne_quai", (x, 0, z), yaw=face_couloir(x), group=f"Bourg/Details/Lanterne{'G' if s < 0 else 'D'}{i}",
                  variant=1, emprise=(2, 4, 10))
    rng = np.random.default_rng(3)
    props = ["tonneaux", "caisses", "panneau", "banc", "bouee"]
    textes = ["MARCHÉ", "TAVERNE", "AUBERGE", "ÉPICES", "POISSONS", "PORT"]
    interdits = [-122, -150, -178, -136, -166, -196]
    k = 0
    for s, poses in ((-1, poses_g), (1, poses_d)):
        for (x, zc, larg, prof, info) in poses:
            if larg < 12:
                continue
            fn = props[k % len(props)]
            zp = zc + rng.uniform(-larg / 2 + 3, larg / 2 - 3)
            if min(abs(zp - zi) for zi in interdits) < 4:
                zp += 6 if zp + 6 < zc + larg / 2 else -6
            xp = s * (X_BORD - 2.6)
            kw = {"texte": textes[k % len(textes)]} if fn == "panneau" else {}
            place(b, "mobilier", fn, (xp, 0, zp), yaw=face_couloir(xp), group=f"Bourg/Details/{fn}{k}", variant=k % 3,
                  emprise=(3, 3, 4), **kw)
            k += 1
    place(b, "mobilier", "viande_geante", (34.5, 0, -160), yaw=90, group="Bourg/Details/Broche", variant=2, taille=0.8,
          emprise=(5, 3, 4))


# ---------------------------------------------------------------------------
# Port (z -204 → -292)
# ---------------------------------------------------------------------------

def port(b: Builder) -> None:
    """Quais, pontons, navires à quai, phare sur sa jetée, barques, îlots, plages au pied des collines."""
    # côté gauche : ponton long, grand galion à quai, navire au mouillage au large
    place(b, "port", "ponton", (-X_BORD, 0, -210), yaw=90, group="Port/PontonG", variant=0, longueur=64, largeur=8,
          emprise=(8, 64, 4), attente="devant")
    # passerelle = x local du bout de la passerelle (posée sur la margelle du quai, |x| = 39 dans la zone)
    place(b, "port", "galion", (-66, Y_EAU, -252), yaw=0, group="Port/Galion", variant=0, longueur=72, passerelle=66 - 39,
          emprise=(22, 72, 70))
    place(b, "port", "galion", (-158, Y_EAU, -318), yaw=200, group="Port/GalionLarge", variant=2, longueur=60,
          emprise=(20, 60, 60))
    # côté droit : jetée de pierre et phare, caravelle, ponton des pêcheurs
    place(b, "port", "ponton", (X_BORD, 0, -210), yaw=-90, group="Port/Jetee", variant=2, longueur=74, largeur=8,
          emprise=(8, 74, 4), attente="devant")
    place(b, "port", "phare", (X_BORD + 74 + 10, 0, -210), group="Port/Phare", variant=0, hauteur=64, emprise=(22, 22, 64))
    place(b, "port", "caravelle", (62, Y_EAU, -248), yaw=180, group="Port/Caravelle", variant=0, longueur=52, passerelle=62 - 39,
          emprise=(18, 52, 50))
    place(b, "port", "ponton", (X_BORD, 0, -284), yaw=-90, group="Port/PontonD", variant=1, longueur=48, largeur=6,
          emprise=(6, 48, 4), attente="devant")
    for i, (x, z, yaw, v) in enumerate(((-96, -218, 80, 0), (-118, -202 - 4, 100, 1), (70, -278, 260, 2), (94, -290, 280, 0),
                                        (150, -232, 30, 1))):
        place(b, "port", "barque", (x, Y_EAU, z), yaw=yaw, group=f"Port/Barque{i}", variant=v, emprise=(4, 9, 2))
    # îlots rocheux à palmiers au large
    for i, (x, z, r, v) in enumerate(((-186, -246, 16, 0), (176, -312, 14, 1), (-110, -350, 10, 2), (196, -228 - 40, 9, 0))):
        place(b, "nature", "ilot", (x, Y_EAU, z), group=f"Port/Ilot{i}", variant=v, rayon=r, emprise=(2 * r, 2 * r, 14))
    # plages au pied des collines : palmiers, rochers, crabes, coquillages
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        for i, (dx, z) in enumerate(((146, -206), (170, -214), (196, -208), (210, -220))):
            place(b, "nature", "palmier", (s * dx, -0.6, z), yaw=i * 70 + (s > 0) * 30, group=f"Port/Plage{cote}/Palmier{i}",
                  variant=(i + (s > 0)) % 3, hauteur=13 + 3 * (i % 2), emprise=(8, 8, 16))
        for i, (dx, z) in enumerate(((136, -220), (184, -222))):
            place(b, "nature", "rocher", (s * dx, -0.6, z), yaw=i * 50, group=f"Port/Plage{cote}/Rocher{i}", variant=i, taille=1.0,
                  emprise=(6, 6, 4))
        place(b, "mobilier", "crabe", (s * 160, -0.6, -218), yaw=s * 40, group=f"Port/Plage{cote}/Crabe", emprise=(2, 2, 1))
        place(b, "mobilier", "coquillages", (s * 176, -0.6, -212), group=f"Port/Plage{cote}/Coquillages", variant=(s > 0),
              emprise=(3, 3, 1))
    # quais : bittes, lanternes, canons pointés vers le large, filets
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        for i, z in enumerate(range(-216, -292, -14)):
            place(b, "mobilier", "bitte", (s * 38.6, 0, z), group=f"Port/Quai{cote}/Bitte{i}", variant=0, emprise=(2, 2, 2))
        for i, z in enumerate((-222, -250, -276)):
            place(b, "mobilier", "lanterne_quai", (s * 36.5, 0, z), yaw=face_couloir(s), group=f"Port/Quai{cote}/Lanterne{i}",
                  variant=0, emprise=(2, 2, 11))
        for i, z in enumerate((-236, -266)):
            place(b, "mobilier", "canon", (s * 35.6, 0, z), yaw=face_large(s), group=f"Port/Quai{cote}/Canon{i}", variant=i,
                  emprise=(3, 5, 3))
        place(b, "mobilier", "tonneaux", (s * 35.5, 0, -243), yaw=s * 20, group=f"Port/Quai{cote}/Tonneaux", variant=1 + (s > 0),
              emprise=(4, 4, 4))
        place(b, "mobilier", "caisses", (s * 35.5, 0, -258), yaw=face_couloir(s), group=f"Port/Quai{cote}/Caisses",
              variant=(s > 0) * 2, emprise=(5, 3, 4))
    place(b, "mobilier", "filet_peche", (-70, 0, -213), yaw=180, group="Port/PontonG/Filet", variant=0, emprise=(7, 1, 7))
    place(b, "mobilier", "filet_peche", (64, 0, -287), yaw=0, group="Port/PontonD/Filet", variant=2, emprise=(6, 3, 2))
    place(b, "mobilier", "panneau", (-37, 0, -208), yaw=-90, group="Port/PanneauPort", texte="PORT", variant=2, emprise=(6, 1, 6))
    place(b, "mobilier", "panneau", (37, 0, -208), yaw=90, group="Port/PanneauPhare", texte="PHARE", variant=2, emprise=(6, 1, 6))


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
            place(b, "mobilier", "mat_vigie", (s * 48, 0, z), yaw=0, group=f"Place/Mat{cote}{i}", hauteur=34, variant=i,
                  emprise=(11, 5, 40))
        # trésors, canons vers le large, ancre et barre
        place(b, "mobilier", "coffre_tresor", (s * 43, 0, Z_PLACE + 12), yaw=face_couloir(s), group=f"Place/Coffre{cote}",
              variant=0 if s < 0 else 2, emprise=(4, 3, 3))
        for i, z in enumerate((Z_PLACE + 18, Z_PLACE - 16)):
            place(b, "mobilier", "canon", (s * 51, 0, z), yaw=face_large(s), group=f"Place/Canon{cote}{i}", variant=1 if i else 2,
                  emprise=(7, 5, 3))
        place(b, "mobilier", "tonneaux", (s * 50, 0, Z_PLACE), yaw=s * 15, group=f"Place/Tonneaux{cote}", variant=0, emprise=(4, 4, 3))
        place(b, "mobilier", "caisses", (s * 44, 0, Z_PLACE - 26), yaw=face_couloir(s), group=f"Place/Caisses{cote}", variant=2,
              emprise=(5, 3, 4))
    place(b, "mobilier", "ancre", (-44, 0, Z_PLACE - 10), yaw=face_couloir(-1), group="Place/Ancre", variant=1, emprise=(7, 3, 11))
    place(b, "mobilier", "barre_navire", (44, 0, Z_PLACE - 10), yaw=face_couloir(1), group="Place/Barre", taille=1.4, variant=1,
          emprise=(7, 3, 9))
    f = _asset("mobilier", "guirlande_fanions")
    if f:
        for i, z in enumerate((Z_PLACE + 28, Z_PLACE - 28)):
            with b.group(f"Place/GuirlandeHaute{i}"):
                f(b, (-47.2, 36.0, z), (47.2, 36.0, z), n=18, creux=2.2, variant=(i + 1) % 3)
        for s in (-1, 1):
            with b.group(f"Place/GuirlandeCote{'G' if s < 0 else 'D'}"):
                f(b, (s * 48, 30.0, Z_PLACE + 27), (s * 48, 30.0, Z_PLACE - 27), n=12, creux=2.5, variant=2)


def abords(b: Builder) -> None:
    """Abords de l'arche (côté apparition) : palmiers, rochers, panneau."""
    for s in (-1, 1):
        for i, (dx, dz, kind) in enumerate(((54, 14, "palmier"), (68, 30, "palmier"), (84, 18, "rocher"), (100, 33, "palmier"),
                                            (112, 14, "buisson"), (122, 26, "palmier"))):
            kw = {"hauteur": 14 + 2 * (i % 2)} if kind == "palmier" else {}
            place(b, "nature", kind, (s * dx, 0, Z_PORTE + dz), yaw=i * 50, group=f"Abords/{'G' if s < 0 else 'D'}{i}",
                  variant=(i + (s > 0)) % 3, emprise=(8, 8, 14), **kw)


def reperes(b: Builder) -> None:
    """Pièces invisibles utiles au jeu : zone des œufs, entrée, sortie, couloir."""
    inv = dict(transparency=1.0, collide=False, shadow=False)
    with b.group("Reperes"):
        b.box((-R_PLACE, 0, Z_PLACE - R_PLACE), (R_PLACE, 1, Z_PLACE + R_PLACE), "#ffffff", name="ZoneOeufs", **inv)
        b.box((-DEMI_COULOIR, 0, Z_PORTE + 18), (DEMI_COULOIR, 1, Z_PORTE + 24), "#ffffff", name="Entree", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE - 4), (DEMI_COULOIR, 1, Z_SORTIE + 2), "#ffffff", name="Sortie", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE), (DEMI_COULOIR, 1, Z_PORTE), "#ffffff", name="Couloir", **inv)


def decouper(b: Builder, prefixes=("Sol/", "Eau", "Collines/", "Monuments/Rocher", "Monuments/Porte"), taille: float = 64) -> None:
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
    sol_trottoirs(b)
    sol_cotes(b)
    eau(b)
    sommets = collines_laterales(b)
    place(b, "monuments", "porte_entree", (0, 0, Z_PORTE), group="Monuments/Porte", emprise=(260, 12, 50), attente="arche",
          ouverture=2 * X_BORD, hauteur=50, mur=X_COLLINES)
    place(b, "monuments", "rocher_crane", (0, 0, Z_ROCHER), group="Monuments/Rocher", emprise=(440, 34, 100), attente="arche_devant",
          passage=64, largeur=2 * X_FOND, profondeur=PROF_ROCHER, hauteur=100)
    campagne(b, sommets)
    poses_g, poses_d = bourg(b)
    guirlandes(b, (-122, -150, -178), "Bourg")
    details_bourg(b, poses_g, poses_d)
    port(b)
    guirlandes(b, (-228, -262), "Port")
    place_oeufs(b)
    abords(b)
    reperes(b)
    decouper(b)
    return b


def _aabb(p):
    R = np.asarray(p.rot).reshape(3, 3)
    half = np.abs(R) @ (np.asarray(p.size) / 2)
    return np.asarray(p.pos) - half, np.asarray(p.pos) + half


def couloir_libre(b: Builder) -> list:
    """Liste ce qui encombre le couloir de course au sol (hors sol et repères)."""
    gene = []
    for p in b.parts:
        if not p.collide or p.group.startswith(("Sol", "Reperes")):
            continue
        lo, hi = _aabb(p)
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
        lo, hi = _aabb(p)
        if lo[0] < DEMI_COULOIR - 1 and hi[0] > -DEMI_COULOIR + 1 and lo[1] < y_min and hi[1] > 12 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name, round(lo[1], 1)))
    return out


def meta() -> dict:
    return {"nom": "ZoneOnePiece", "version": VERSION, "largeur_couloir": 2 * DEMI_COULOIR,
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
