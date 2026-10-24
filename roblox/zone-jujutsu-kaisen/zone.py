#!/usr/bin/env python3
"""Plan de la zone Jujutsu Kaisen (la ville de nuit pendant un incident surnaturel) en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course occupe x ∈ [-32, 32] (64 de large), bordé de trottoirs jusqu'aux façades (|x| = 42) ;
- on entre sous un viaduc ferroviaire (z = 0, dessous à 36 studs, train à quai) et on court vers -Z :
  rue commerçante (−12 → −150, petit carrefour en −92, passerelle piétonne en −150), quartier des tours
  et des grands écrans (−156 → −296, passerelle en −300), approche du grand carrefour (−300 → −354 :
  tour cylindrique, immeuble à écrans), grand carrefour « scramble » = place des œufs (centre −400, rayon 34),
  puis l'incident (−446 → −474 : fissures violettes, gravats, barrières 立入禁止) et la sortie sous un
  immeuble effondré en arche (−474 → −496) vers la zone suivante ;
- des tours d'arrière-plan ferment les côtés (|x| ≥ 136) ; deux dômes de barrière violet nuit
  se dressent derrière le carrefour et l'incident.

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
DEMI_COULOIR = 32        # couloir de course x ∈ [-32, 32]
X_LIBRE_HAUT = 33        # au-dessus de |x| < 33, rien sous y = 30
H_LIBRE = 34             # dessous des ouvrages qui enjambent le couloir (passerelles, immeuble effondré)
H_VIADUC = 36            # dessous des poutres du viaduc d'entrée
Y_RAIL = 42              # niveau des rails sur le viaduc
X_FACADE = 42            # alignement des façades (trottoirs de 10 studs)
X_SECOND = 84            # seconde rangée d'immeubles
X_SKYLINE = 136          # tours d'arrière-plan
X_FOND = 242             # bord du sol
Z_APPROCHE = 32          # sol devant le viaduc (côté apparition, peut être supprimé : groupe Sol/Approche)
Z_PORTE = 0              # axe du viaduc d'entrée
Z_RUE = -12              # première façade après le viaduc
Z_RUELLE = (-100, -84)   # petite rue transversale de la rue commerçante
Z_PASSERELLE_1 = -150
Z_TOURS = -156
Z_PASSERELLE_2 = -300
Z_PLACE = -400           # centre du grand carrefour = place des œufs
R_PLACE = 34
X_CARREFOUR = 46         # demi-largeur du carré peint du carrefour (passages piétons compris)
Z_CARREFOUR_N, Z_CARREFOUR_S = Z_PLACE + 46, Z_PLACE - 46      # -354, -446
Z_TRANSVERSALE = (Z_PLACE - 34, Z_PLACE + 34)                   # chaussée de la grande rue transversale
Z_EFFONDRE = -485        # immeuble effondré (repère final), emprise z ∈ [-496, -474]
Z_SORTIE = -496
DOME_G = (-168, -420, 72)    # dômes de barrière : (x, z, rayon)
DOME_D = (166, -448, 48)

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
          portique: tuple | None = None, **params) -> dict:
    """Pose un asset ; si le module n'existe pas encore, pose un bloc translucide de même emprise.
    `portique=(passage, hauteur_libre)` : l'attente laisse le couloir libre (deux piles et un tablier en hauteur)."""
    f = _asset(module, fn)
    with b.at(pos, yaw=yaw, group=group):
        if f is not None:
            n0 = len(b.parts)
            try:
                return f(b, **params) or {}
            except NotImplementedError:
                del b.parts[n0:]
        w, d, h = emprise
        att = dict(transparency=0.5, name=f"ATTENTE_{module}_{fn}")
        if portique:
            passage, hl = portique
            xa = passage / 2 + 2
            for s in (-1, 1):
                x0, x1 = sorted((s * xa, s * w / 2))
                b.box((x0, 0, -d / 2), (x1, h, d / 2), "#ff4fd8", **att)
            b.box((-xa, hl, -d / 2), (xa, h, d / 2), "#ff4fd8", **att)
        else:
            b.box((-w / 2, 0, -d / 2), (w / 2, h, d / 2), "#ff4fd8", **att)
        return {"emprise": (w, d), "hauteur": h}


def face_couloir(x: float) -> float:
    """Rotation qui tourne l'avant d'un asset (-Z local) vers le couloir."""
    return -90.0 if x < 0 else 90.0


# Occupation des trottoirs (|x| ∈ [32, 42]) : évite d'empiler escaliers, poteaux et mobilier.
OCCUPE: dict = {-1: [], 1: []}


def reserver(s: int, z0: float, z1: float, nom: str) -> None:
    za, zb = sorted((z0, z1))
    for (ya, yb, autre) in OCCUPE[s]:
        if za < yb and zb > ya:
            raise AssertionError(f"trottoir {'gauche' if s < 0 else 'droit'} : {nom} [{za}, {zb}] chevauche {autre} [{ya}, {yb}]")
    OCCUPE[s].append((za, zb, nom))


# ---------------------------------------------------------------------------
# Sol « pixel »
# ---------------------------------------------------------------------------

NEON_SOL = set()     # couleurs du sol rendues en matériau Neon (lueurs des fissures)


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
        extra = {"material": "Neon"} if col in NEON_SOL else {}
        for (i, j, w, h) in mask_rects(mask):
            b.box((x0 + i * cell, y_haut - epaisseur, z0 + j * cell),
                  (x0 + (i + w) * cell, y_haut, z0 + (j + h) * cell), col, studs=studs, name=name, **kw, **extra)
            n += 1
    return n


def damier(a, bcol, taille: float):
    a, bcol = (hexrgb(v) if isinstance(v, str) else v for v in (a, bcol))
    return lambda x, z: a if (math.floor(x / taille) + math.floor(z / taille)) % 2 == 0 else bcol


# --- fissures de l'incident --------------------------------------------------
FISSURES = [
    [(-30, -447), (-18, -457), (-22, -469), (-8, -481), (-12, -496)],
    [(6, -446), (12, -455), (4, -466), (16, -477), (10, -491)],
    [(41, -449), (28, -461), (34, -473), (22, -487), (26, -496)],
    [(-42, -461), (-34, -466), (-39, -480), (-30, -490)],
    [(-18, -457), (-5, -462), (4, -466)],
    [(16, -477), (27, -474)],
    [(-60, -447), (-50, -455), (-56, -470)],
    [(58, -474), (48, -480), (54, -494)],
]


def _dist_seg(px, pz, a, bb):
    ax, az = a
    bx, bz = bb
    vx, vz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((px - ax) * vx + (pz - az) * vz) / (vx * vx + vz * vz)))
    return math.hypot(px - ax - t * vx, pz - az - t * vz)


def fissure(x: float, z: float) -> int:
    """0 : rien ; 1 : fissure sombre ; 2 : fissure avec lueur violette."""
    if z > Z_CARREFOUR_S:
        return 0
    d = min(_dist_seg(x, z, p, q) for f in FISSURES for p, q in zip(f, f[1:]))
    if d < 1.3:
        return 2 if (int(math.floor(x / 2)) * 7 + int(math.floor(z / 2)) * 3) % 5 == 0 else 1
    return 0


# --- grand carrefour (place des œufs) ------------------------------------------

def motif_carrefour(x: float, z: float):
    """Carrefour « scramble » : quatre passages piétons autour du carré, deux passages en diagonale (X).
    Renvoie None hors du carré |x| ≤ 46, z ∈ [-446, -354]."""
    dz = z - Z_PLACE
    ax, adz = abs(x), abs(dz)
    if ax > X_CARREFOUR or adz > X_CARREFOUR:
        return None
    blanc, asph = c("marquage"), c("asphalte_place")
    if ax > DEMI_COULOIR and adz > 34:                       # coins de trottoir
        if ax < DEMI_COULOIR + 2 or adz < 36:
            return c("bordure")
        return c("guidage") if (ax < 40 and adz < 40) else c("trottoir_clair")
    if adz > 34:                                             # passages nord et sud (bandes selon z)
        if adz < 36 or adz > 44:
            return asph
        return blanc if ax < 30 and math.floor((x + 32) / 2) % 2 == 0 else asph
    if ax > DEMI_COULOIR:                                    # passages est et ouest (bandes selon x)
        if ax < 34 or ax > 44:
            return asph
        return blanc if adz < 32 and math.floor((z - Z_PLACE + 34) / 2) % 2 == 0 else asph
    # diagonales (X) : bandes de 12 studs, rayures verticales
    k = 34.0 / 32.0
    for sgn in (1, -1):
        d = abs(dz - sgn * k * x) / math.hypot(1, k)
        if d < 6 and adz < 32 and ax < 30:
            return blanc if math.floor((x + 32) / 2) % 2 == 0 else asph
    # ligne d'arrêt devant chaque passage (côté d'arrivée des voitures, circulation à gauche)
    return asph


def marquages_couloir(x: float, z: float):
    """Chaussée de la grande rue : ligne médiane jaune double, pointillés blancs, lignes de rive."""
    ax = abs(x)
    if 2 <= ax < 4:
        return c("marquage_jaune")
    if 28 <= ax < 30:
        return c("marquage")
    if 16 <= ax < 18 and math.floor(z / 12) % 2 == 0:
        return c("marquage")
    return c("asphalte")


def couleur_couloir(x: float, z: float):
    m = motif_carrefour(x, z)
    if m:
        return m
    ax = abs(x)
    f = fissure(x, z)
    if f:
        return c("lueur_violette") if f == 2 else c("fissure")
    zr0, zr1 = Z_RUELLE
    if zr0 <= z < zr1:                                    # petit carrefour : chaussée nue
        return c("asphalte_place")
    if zr1 + 2 <= z < zr1 + 12 or zr0 - 12 <= z < zr0 - 2:   # passages piétons du petit carrefour
        return c("marquage") if ax < 30 and math.floor((x + 32) / 2) % 2 == 0 else c("asphalte")
    if (zr1 + 14 <= z < zr1 + 16 and x < 0) or (zr0 - 16 <= z < zr0 - 14 and x > 0):   # lignes d'arrêt
        return c("marquage")
    if (Z_CARREFOUR_N + 2 <= z < Z_CARREFOUR_N + 4 and x < 0) or (Z_CARREFOUR_S - 4 <= z < Z_CARREFOUR_S - 2 and x > 0):
        return c("marquage")
    if z < Z_CARREFOUR_S and abs(abs(x) - 3) < 1.01:      # incident : ligne médiane effacée par endroits
        return c("marquage_jaune") if math.floor(z / 10) % 2 else c("asphalte")
    return marquages_couloir(x, z)


def couleur_trottoir(x: float, z: float):
    m = motif_carrefour(x, z)
    if m:
        return m
    ax = abs(x)
    zr0, zr1 = Z_RUELLE
    if zr0 <= z < zr1:                                    # traversée de la petite rue (bandes selon x)
        return c("marquage") if 2 <= z - zr0 < 14 and math.floor(z / 2) % 2 == 0 else c("asphalte_place")
    f = fissure(x, z)
    if f:
        return c("lueur_violette") if f == 2 else c("fissure")
    if ax < DEMI_COULOIR + 2:
        return c("bordure")
    if ax < 36:
        return c("trottoir_fonce")
    if ax < 38:
        return c("guidage")
    if z < Z_CARREFOUR_S:                                  # incident : dalles salies
        return c("trottoir_fonce")
    return c("trottoir") if math.floor(z / 8) % 2 else c("trottoir_clair")


def couleur_cotes(x: float, z: float):
    """Sol au-delà des façades : rues transversales, parvis, arrière-cours."""
    m = motif_carrefour(x, z)
    if m:
        return m
    ax = abs(x)
    zt0, zt1 = Z_TRANSVERSALE
    if Z_CARREFOUR_S <= z < Z_CARREFOUR_N and ax < X_SKYLINE:
        if zt0 <= z < zt1:                               # grande rue transversale
            dz = abs(z - Z_PLACE)
            if 2 <= dz < 4:
                return c("marquage_jaune")
            if 30 <= dz < 32:
                return c("marquage")
            return c("asphalte")
        dz = abs(z - Z_PLACE)
        return c("guidage") if 38 <= dz < 40 else c("trottoir")
    zr0, zr1 = Z_RUELLE
    if zr0 <= z < zr1 and ax < X_SKYLINE:                 # petite rue
        if z < zr0 + 2 or z >= zr1 - 2:
            return c("marquage")
        return c("asphalte_place")
    if -310 <= z < Z_PASSERELLE_2 + 4 and x > 0 and ax < X_SKYLINE:   # parvis devant la tour cylindrique
        return c("trottoir_clair") if math.floor(x / 8) % 2 else c("trottoir")
    if z >= 8:                                            # parvis de la gare (côté apparition)
        return c("trottoir_clair") if (math.floor(x / 32) + math.floor(z / 16)) % 2 else c("trottoir")
    if z < Z_CARREFOUR_S and ax < 110:                    # incident : sol sale et fissuré
        f = fissure(x, z)
        if f:
            return c("lueur_violette") if f == 2 else c("fissure")
        return c("ruelle_fonce")
    return c("ruelle")


def sols(b: Builder) -> None:
    NEON_SOL.add(c("lueur_violette"))
    zf = Z_SORTIE
    with b.group("Sol/Approche"):
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, 8, Z_APPROCHE, 2, couleur_couloir)
        for s in (-1, 1):
            xa, xb = sorted((s * DEMI_COULOIR, s * X_FACADE))
            sol_pixel(b, xa, xb, 8, Z_APPROCHE, 2, couleur_trottoir)
            xa, xb = sorted((s * X_FACADE, s * X_FOND))
            sol_pixel(b, xa, xb, 8, Z_APPROCHE, 8, couleur_cotes)
    with b.group("Sol/Couloir"):
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, zf, 8, 2, couleur_couloir)
    with b.group("Sol/Trottoirs"):
        for s in (-1, 1):
            xa, xb = sorted((s * DEMI_COULOIR, s * X_FACADE))
            sol_pixel(b, xa, xb, zf, 8, 2, couleur_trottoir)
    with b.group("Sol/Cotes"):
        for s in (-1, 1):
            # bande proche (carrefour, rues, parvis) en cases de 2, le fond en cases de 8
            xa, xb = sorted((s * X_FACADE, s * X_SKYLINE))
            sol_pixel(b, xa, xb, zf, 8, 2, couleur_cotes)
            xa, xb = sorted((s * X_SKYLINE, s * X_FOND))
            sol_pixel(b, xa, xb, zf, 8, 8, couleur_cotes)


# ---------------------------------------------------------------------------
# Tours d'arrière-plan (bords de la zone)
# ---------------------------------------------------------------------------

def _dans_dome(x0, x1, z0, z1, marge=6.0) -> bool:
    for (dx, dz, r) in (DOME_G, DOME_D):
        px = min(max(dx, x0), x1)
        pz = min(max(dz, z0), z1)
        if math.hypot(px - dx, pz - dz) < r + marge:
            return True
    return False


def skyline_lateral(b: Builder) -> None:
    """Tours simples (bleu nuit, ardoise, violet) qui ferment les côtés : deux volumes en gradins,
    rubans de fenêtres côté couloir (quelques-uns éclairés), feux rouges d'obstacle, citernes, néons."""
    rng = np.random.default_rng(23)
    tons = [c("bleu_marine"), c("bleu_ardoise"), shade(c("bleu_acier"), 0.9), c("bleu_nuit"), shade(c("violet_nuit"), 1.15),
            shade(c("bleu_ardoise"), 0.85)]
    vitres = [c("vitre_bleue"), c("vitre_claire"), c("fenetre_froide"), c("fenetre_chaude"), c("vitre_cyan")]
    neons = [c("neon_magenta"), c("neon_cyan"), c("neon_jaune"), c("neon_violet")]
    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        z = Z_APPROCHE - 8
        k = 0
        while z > Z_SORTIE + 10:
            w = float(rng.integers(9, 18) * 2)
            if z > -14 and z - w < 14:          # passage du viaduc
                z = -14
                continue
            w = min(w, z - Z_SORTIE)
            xf = X_SKYLINE + float(rng.integers(0, 3) * 4)
            d1 = float(rng.integers(8, 15) * 2)
            if _dans_dome(min(s * xf, s * (X_FOND - 2)), max(s * xf, s * (X_FOND - 2)), z - w, z):
                z -= w
                continue
            h1 = float(rng.integers(20, 46) * 2)
            h2 = h1 + float(rng.integers(8, 30) * 2)
            col = tons[k % len(tons)]
            za, zb = z - w + 1, z - 1
            with b.group(f"Fond/{cote}/T{k:02d}"):
                xa, xb = sorted((s * xf, s * (xf + d1)))
                b.box((xa, 0, za), (xb, h1, zb), col, studs="top", name="Tour")
                xa2, xb2 = sorted((s * (xf + d1), s * (X_FOND - 2)))
                b.box((xa2, 0, za + 2), (xb2, h2, zb - 2), shade(col, 0.88), studs="top", name="Tour")
                # rubans de fenêtres sur la face qui regarde le couloir (dépassent de 0,2)
                fa, fb = sorted((s * xf, s * (xf - 0.2)))
                horizontal = k % 3 != 2
                if horizontal:
                    for i, y in enumerate(np.arange(8, h1 - 6, max(10.0, (h1 - 12) / 4))[:4]):
                        vc = vitres[(k + i) % len(vitres)]
                        b.box((fa, y, za + 2), (fb, y + 3, zb - 2), vc, material="Neon" if vc in (vitres[2], vitres[3]) else "SmoothPlastic",
                              collide=False, shadow=False, name="Fenetres")
                else:
                    for i in range(3):
                        zc = za + (i + 1) * (zb - za) / 4
                        b.box((fa, 6, zc - 1.2), (fb, h1 - 4, zc + 1.2), vitres[(k + i) % 2], collide=False, shadow=False, name="Fenetres")
                # bande éclairée sur la face avant du volume haut
                ga, gb = sorted((s * (xf + d1), s * (xf + d1 - 0.2)))
                b.box((ga, h1 + 6, za + 4), (gb, h1 + 9, zb - 4), vitres[(k + 2) % len(vitres)], collide=False, shadow=False, name="Fenetres")
                # toit : feu d'obstacle ou citerne
                xm = s * (xf + d1 + (X_FOND - 2 - xf - d1) / 2)
                if k % 2 == 0:
                    b.box((xm - 0.6, h2, (za + zb) / 2 - 0.6), (xm + 0.6, h2 + 1.2, (za + zb) / 2 + 0.6), c("rouge_balise"),
                          material="Neon", collide=False, shadow=False, name="Balise")
                else:
                    b.cyl((s * (xf + d1 / 2), h1 + 2.5, (za + zb) / 2), 2.2, 5, c("citerne"), name="Citerne")
                if k % 3 == 1:
                    na, nb = sorted((s * (xf - 0.3), s * (xf + 0.5)))
                    b.box((na, h1 * 0.25, za + 0.6), (nb, h1 * 0.85, za + 1.6), neons[k % len(neons)], material="Neon",
                          collide=False, shadow=False, name="Neon")
            z -= w
            k += 1


# ---------------------------------------------------------------------------
# Entrée : viaduc ferroviaire, train, gare aérienne
# ---------------------------------------------------------------------------

def entree(b: Builder) -> None:
    place(b, "ouvrages", "viaduc_ferroviaire", (0, 0, Z_PORTE), group="Monuments/Viaduc", emprise=(2 * X_FOND - 8, 16, Y_RAIL + 3),
          portique=(2 * DEMI_COULOIR + 2, H_VIADUC), longueur=2 * X_FOND - 8, hauteur_libre=H_VIADUC, niveau_rail=Y_RAIL,
          passage=2 * DEMI_COULOIR + 2, gare=True)
    for s in (-1, 1):
        reserver(s, Z_PORTE - 8, Z_PORTE + 8, "piles du viaduc")
    # train de banlieue qui sort de la gare aérienne (quais en x ∈ [-150, -50]) et passe au-dessus du couloir,
    # sur la voie côté apparition (z = +3,5)
    place(b, "ouvrages", "train_banlieue", (-44, Y_RAIL, Z_PORTE + 3.5), group="Monuments/Train", emprise=(86, 5, 7),
          voitures=4)


def passerelles(b: Builder) -> None:
    """Deux passerelles piétonnes au-dessus du couloir (dessous à 34), escaliers le long des trottoirs."""
    for i, (z, escaliers) in enumerate(((Z_PASSERELLE_1, ("+z", "-z")), (Z_PASSERELLE_2, ("+z", "-z")))):
        place(b, "ouvrages", "passerelle_pietons", (0, 0, z), group=f"Monuments/Passerelle{i + 1}", emprise=(84, 8, H_LIBRE + 5),
              portique=(2 * DEMI_COULOIR + 2, H_LIBRE), variant=i, portee=84, hauteur_libre=H_LIBRE, escaliers=escaliers)
        for s, sens in zip((-1, 1), escaliers):
            reserver(s, z - 4, z + 4, f"passerelle {i + 1}")
            z0, z1 = (z + 4, z + 46) if sens == "+z" else (z - 46, z - 4)
            reserver(s, z0, z1, f"escalier passerelle {i + 1}")
            if _asset("ouvrages", "passerelle_pietons") is None:
                with b.group(f"Monuments/Passerelle{i + 1}"):
                    b.box((s * 33.5, 0, z0), (s * 41.5, H_LIBRE * 0.6, z1), "#ff4fd8", transparency=0.6,
                          name="ATTENTE_ouvrages_escalier")


# ---------------------------------------------------------------------------
# Rangées d'immeubles
# ---------------------------------------------------------------------------

# (fonction, largeur le long du couloir, profondeur, paramètres, écart après)
RUE_GAUCHE_A = [
    ("batiments:immeuble_boutique", 16, 20, {"variant": 0, "enseigne": "ラーメン", "etages": 4}, 2),
    ("batiments:immeuble_boutique", 20, 22, {"variant": 3, "enseigne": "カラオケ", "etages": 6, "panneau_toit": True}, 2),
    ("batiments:immeuble_boutique", 14, 18, {"variant": 2, "enseigne": "薬", "etages": 3}, 2),
    ("batiments:immeuble_boutique", 16, 20, {"variant": 1, "enseigne": "本", "etages": 4}, 0),
]
RUE_GAUCHE_B = [
    ("batiments:superette", 24, 20, {"variant": 0}, 2),
    ("batiments:immeuble_boutique", 24, 22, {"variant": 4, "enseigne": "寿司", "etages": 5}, 0),
]
RUE_DROITE_A = [
    ("batiments:superette", 24, 20, {"variant": 1}, 2),
    ("batiments:immeuble_boutique", 16, 20, {"variant": 1, "enseigne": "本", "etages": 5}, 2),
    ("batiments:immeuble_boutique", 12, 16, {"variant": 5, "enseigne": "カラオケ", "etages": 8}, 2),
    ("batiments:immeuble_boutique", 14, 18, {"variant": 0, "enseigne": "ラーメン", "etages": 3}, 0),
]
RUE_DROITE_B = [
    ("batiments:immeuble_boutique", 20, 22, {"variant": 3, "enseigne": "映画", "etages": 6}, 2),
    ("batiments:immeuble_boutique", 14, 18, {"variant": 2, "enseigne": "薬", "etages": 4}, 2),
    ("batiments:immeuble_boutique", 12, 16, {"variant": 5, "enseigne": "喫茶", "etages": 7}, 0),
]
TOURS_GAUCHE = [
    ("batiments:tour_bureaux", 30, 28, {"variant": 1, "hauteur": 96}, 4),
    ("batiments:grand_magasin", 40, 32, {"variant": 0, "hauteur": 64}, 4),
    ("batiments:tour_bureaux", 28, 28, {"variant": 0, "hauteur": 112, "panneau_toit": True}, 4),
    ("batiments:tour_bureaux", 30, 28, {"variant": 2, "hauteur": 80}, 0),
]
TOURS_DROITE = [
    ("batiments:tour_bureaux", 28, 28, {"variant": 3, "hauteur": 84}, 4),
    ("batiments:tour_bureaux", 32, 30, {"variant": 4, "hauteur": 124}, 4),
    ("batiments:grand_magasin", 40, 32, {"variant": 1, "hauteur": 56}, 4),
    ("batiments:immeuble_boutique", 28, 24, {"variant": 3, "enseigne": "カラオケ", "etages": 7, "panneau_toit": True}, 0),
]
APPROCHE_GAUCHE = [
    ("batiments:immeuble_boutique", 10, 16, {"variant": 5, "enseigne": "ラーメン", "etages": 6}, 2),
    ("carrefour:immeuble_ecran", 42, 44, {"variant": 0, "hauteur": 60, "angle": "gauche"}, 0),
]


def _hauteur_attente(params: dict) -> float:
    if "hauteur" in params:
        return params["hauteur"]
    return 9 + 8 * (params.get("etages", 2) - 1) + 1.5


def rangee(b: Builder, s: int, z_debut: float, z_fin: float, plan, nom: str) -> list:
    """Aligne une rangée d'immeubles le long du couloir (façade en |x| = 42), de z_debut vers -Z."""
    cote = "Gauche" if s < 0 else "Droite"
    z = z_debut
    poses = []
    for i, (kind, larg, prof, params, ecart) in enumerate(plan):
        zc = z - larg / 2
        mod, fn = kind.split(":")
        kw = dict(params)
        kw.setdefault("largeur", larg)
        kw.setdefault("profondeur", prof)
        x = s * (X_FACADE + prof / 2)
        info = place(b, mod, fn, (x, 0, zc), yaw=face_couloir(x), group=f"{nom}/{cote}/{i:02d}_{fn}",
                     emprise=(larg, prof, _hauteur_attente(params)), **kw)
        poses.append((x, zc, larg, prof, info))
        z -= larg + ecart
    assert z >= z_fin - 0.01, f"rangée {nom} {cote} trop longue ({z} < {z_fin})"
    return poses


SECONDE_RANGEE = {
    # (z centre, largeur, profondeur, hauteur, variante)
    -1: [(-24, 24, 28, 56, 0), (-52, 26, 26, 64, 1), (-74, 16, 24, 48, 2), (-112, 22, 30, 60, 3), (-138, 22, 28, 52, 1),
         (-180, 28, 32, 70, 2), (-240, 30, 30, 84, 0)],
    1: [(-26, 22, 26, 60, 2), (-54, 28, 30, 50, 3), (-76, 14, 22, 44, 0), (-114, 24, 26, 66, 1), (-140, 18, 24, 48, 2),
        (-200, 26, 30, 76, 3), (-262, 28, 30, 90, 1)],
}


def immeubles(b: Builder) -> dict:
    poses = {}
    for s, (pa, pb, pt, pp) in ((-1, (RUE_GAUCHE_A, RUE_GAUCHE_B, TOURS_GAUCHE, APPROCHE_GAUCHE)),
                                (1, (RUE_DROITE_A, RUE_DROITE_B, TOURS_DROITE, None))):
        poses[s] = []
        poses[s] += rangee(b, s, Z_RUE, Z_RUELLE[1], pa, "Rue")
        poses[s] += rangee(b, s, Z_RUELLE[0], Z_PASSERELLE_1, pb, "Rue")
        poses[s] += rangee(b, s, Z_TOURS, Z_PASSERELLE_2 + 4, pt, "Tours")
        if pp:
            poses[s] += rangee(b, s, Z_PASSERELLE_2, Z_CARREFOUR_N, pp, "Approche")
        for i, (zc, larg, prof, h, v) in enumerate(SECONDE_RANGEE[s]):
            x = s * (X_SECOND + prof / 2)
            place(b, "batiments", "immeuble_fond", (x, 0, zc), yaw=face_couloir(x), group=f"Arriere/{'Gauche' if s < 0 else 'Droite'}/{i:02d}",
                  emprise=(larg, prof, h), variant=v, largeur=larg, profondeur=prof, hauteur=h)
    # immeubles de la rue transversale (côté nord), tournés vers le carrefour (-Z)
    for i, (x, larg, prof, h, v) in enumerate(((-111, 42, 28, 54, 1), (113, 38, 28, 62, 3))):
        place(b, "batiments", "immeuble_fond", (x, 0, Z_CARREFOUR_N + prof / 2), yaw=0, group=f"Arriere/Transversale{i}",
              emprise=(larg, prof, h), variant=v, largeur=larg, profondeur=prof, hauteur=h)
    place(b, "batiments", "immeuble_fond", (-105, 0, -311), yaw=-90, group="Arriere/Approche", emprise=(26, 30, 66),
          variant=2, largeur=26, profondeur=30, hauteur=66)
    return poses


# ---------------------------------------------------------------------------
# Grand carrefour (place des œufs)
# ---------------------------------------------------------------------------

def carrefour(b: Builder) -> None:
    # tour cylindrique au coin nord-est, tournée vers le centre du carrefour
    place(b, "carrefour", "tour_cylindrique", (68, 0, -329), yaw=44, group="Carrefour/TourCylindrique", emprise=(34, 34, 92),
          rayon=22, hauteur=76)
    # gare au coin sud-ouest, longue façade vitrée tournée vers le carrefour (+Z)
    place(b, "carrefour", "gare_facade", (-73, 0, Z_CARREFOUR_S - 13), yaw=180, group="Carrefour/Gare", emprise=(62, 26, 28),
          variant=0, largeur=62, profondeur=26, hauteur=28)
    # coin sud-est : tour de verre endommagée (début de l'incident)
    place(b, "incident", "tour_endommagee", (58, 0, Z_CARREFOUR_S - 13), yaw=90, group="Carrefour/TourEndommagee",
          emprise=(26, 32, 70), variant=0, largeur=26, profondeur=32, hauteur=70)
    place(b, "incident", "tour_endommagee", (96, 0, -460), yaw=180, group="Incident/TourEndommagee2",
          emprise=(32, 24, 58), variant=1, largeur=32, profondeur=24, hauteur=58)
    # feux aux quatre coins (face au couloir) et face à la rue transversale
    for i, (x, z, yaw, v) in enumerate(((-40, Z_CARREFOUR_N - 4, -90, 0), (40, Z_CARREFOUR_N - 4, 90, 1),
                                        (-40, Z_CARREFOUR_S + 4, -90, 1), (40, Z_CARREFOUR_S + 4, 90, 0),
                                        (-44, Z_CARREFOUR_N - 8, 0, 1), (44, Z_CARREFOUR_N - 8, 0, 0),
                                        (-44, Z_CARREFOUR_S + 8, 180, 0), (44, Z_CARREFOUR_S + 8, 180, 1))):
        if abs(x) < X_FACADE:
            reserver(-1 if x < 0 else 1, z - 1, z + 1, f"feu carrefour {z}")
        place(b, "mobilier", "feu_tricolore", (x, 0, z), yaw=yaw, group=f"Carrefour/Feu{i}", emprise=(2, 7, 14), variant=v)
    # parvis de la tour cylindrique : arbres et bancs
    for i, x in enumerate((52, 72, 92)):
        place(b, "mobilier", "arbre_rue", (x, 0, -300), group=f"Carrefour/Parvis/Arbre{i}", variant=i % 3, taille=0.9, emprise=(4, 4, 12))
    for i, x in enumerate((62, 82)):
        place(b, "mobilier", "banc", (x, 0, -300.5), yaw=180, group=f"Carrefour/Parvis/Banc{i}", emprise=(6, 2, 3))


# ---------------------------------------------------------------------------
# Incident et sortie
# ---------------------------------------------------------------------------

def incident(b: Builder) -> None:
    place(b, "incident", "immeuble_effondre", (0, 0, Z_EFFONDRE), group="Monuments/Effondre", emprise=(200, 22, 100),
          portique=(2 * DEMI_COULOIR, H_LIBRE), passage=2 * DEMI_COULOIR, hauteur_libre=H_LIBRE)
    for i, (x, z, r) in enumerate((DOME_G, DOME_D)):
        place(b, "incident", "voile_dome", (x, 0, z), group=f"Monuments/Voile{i + 1}", emprise=(2 * r, 2 * r, r),
              variant=i, rayon=r)
    # trottoirs du couloir (|x| 33-42) : barrières 立入禁止, voitures abandonnées, gravats — réservés pour ne rien empiler
    trottoirs = [
        # (fonction, x, z, yaw, longueur occupée le long du trottoir, paramètres)
        ("barriere_chantier", -35, -450.5, 90, 8, {"longueur": 8, "variant": 0}),
        ("voiture_abandonnee", -37.5, -460, 0, 9, {"variant": 1}),
        ("gravats", -38, -470, 40, 6, {"variant": 0, "taille": 0.9}),
        ("gravats", 38, -450, 110, 5, {"variant": 1, "taille": 0.8}),
        ("barriere_chantier", 35, -458, 90, 8, {"longueur": 8, "variant": 1}),
        ("voiture_abandonnee", 37.5, -468.5, 180, 9, {"variant": 2}),
    ]
    for i, (fn, x, z, yaw, L, kw) in enumerate(trottoirs):
        reserver(-1 if x < 0 else 1, z - L / 2, z + L / 2, f"{fn} {z}")
        mod = "mobilier" if fn == "barriere_chantier" else "incident"
        place(b, mod, fn, (x, 0, z), yaw=yaw, group=f"Incident/Trottoir{i:02d}_{fn}", emprise=(4.6, L, 4), **kw)
    # rue transversale et abords : gravats, voitures, barrières qui coupent la rue devant les dômes
    for i, (x, z, v, t) in enumerate(((-58, -438, 2, 1.0), (54, -436, 0, 1.1), (-80, -380, 1, 1.0), (84, -414, 2, 0.9),
                                      (120, -360, 1, 1.0), (-100, -360, 0, 0.8), (-70, -430, 1, 0.7))):
        place(b, "incident", "gravats", (x, 0, z), yaw=(i * 67) % 360, group=f"Incident/Gravats{i}", emprise=(6, 6, 3), variant=v, taille=t)
    for i, (x, z, yaw, v) in enumerate(((-64, -404, 30, 0), (70, -420, -20, 3), (104, -392, 75, 1))):
        place(b, "incident", "voiture_abandonnee", (x, 0, z), yaw=yaw, group=f"Incident/Voiture{i}", emprise=(4.6, 9, 4), variant=v)
    for i, (x, z, yaw, L, v) in enumerate(((-64, -444, 0, 12, 2), (66, -444, 0, 12, 1), (-92, -400, 90, 24, 0), (112, -400, 90, 24, 2))):
        place(b, "mobilier", "barriere_chantier", (x, 0, z), yaw=yaw, group=f"Incident/Barriere{i}", emprise=(L, 2, 5),
              longueur=L, variant=v)
    for i, (x, z) in enumerate(((-76, -444), (78, -440))):
        place(b, "mobilier", "cones", (x, 0, z), group=f"Incident/Cones{i}", emprise=(9, 2, 3), variant=1)


# ---------------------------------------------------------------------------
# Mobilier de rue
# ---------------------------------------------------------------------------

def mobilier_rue(b: Builder) -> None:
    """Poteaux électriques et câbles (rue commerçante), feux, distributeurs, vélos, lampadaires, arbres, garde-corps."""
    # --- poteaux et câbles (le long des trottoirs, jamais en travers du couloir) ---
    poteaux = {-1: (-18, -42, -66), 1: (-18, -42, -66, -108, -132)}
    for s, zs in poteaux.items():
        cote = "G" if s < 0 else "D"
        accs = []
        for i, z in enumerate(zs):
            x = s * 38
            reserver(s, z - 1, z + 1, f"poteau {z}")
            info = place(b, "mobilier", "poteau_electrique", (x, 0, z), yaw=face_couloir(x), group=f"Rue/Poteaux/{cote}{i}",
                         emprise=(2, 5, 24), variant=i % 3, hauteur=24)
            accs.append(info.get("accroches"))
        f = _asset("mobilier", "cable")
        if f:
            with b.group(f"Rue/Cables/{cote}"):
                for a0, a1 in zip(accs, accs[1:]):
                    if a0 and a1:
                        for k in (0, 1, 2, 4):
                            f(b, a0[k], a1[k], creux=1.4, segments=4)
                for a in accs:          # branchements vers les façades
                    if a:
                        p0 = a[2]           # +Z local = côté façade
                        f(b, p0, (s * (X_FACADE - 0.1), p0[1] - 7, p0[2] + 3), creux=0.8, segments=2)
    # --- feux du petit carrefour ---
    zr0, zr1 = Z_RUELLE
    for i, (s, z, v) in enumerate(((-1, zr1 + 4, 0), (1, zr1 + 4, 0), (-1, zr0 - 3, 1), (1, zr0 - 3, 1))):
        x = s * 40.5
        reserver(s, z - 1, z + 1, f"feu {z}")
        place(b, "mobilier", "feu_tricolore", (x, 0, z), yaw=face_couloir(x), group=f"Rue/Feux/F{i}", emprise=(2, 7, 14), variant=v)
    # --- distributeurs, vélos, poubelles, panneaux ---
    objets = [
        # (fonction, x, z, longueur occupée le long du trottoir, paramètres)
        ("distributeurs", -40.7, -50, 7, {"nombre": 2, "variant": 0}),
        ("distributeurs", 40.7, -48, 7, {"nombre": 2, "variant": 1}),
        ("distributeurs", 40.7, -122, 10, {"nombre": 3, "variant": 2}),
        ("distributeurs", -40.7, -232, 7, {"nombre": 2, "variant": 1}),
        ("distributeurs", 40.7, -266, 10, {"nombre": 3, "variant": 0}),
        ("distributeurs", 40.7, 20, 10, {"nombre": 3, "variant": 2}),
        ("velos", 38.5, -27, 8, {"nombre": 4, "variant": 0}),
        ("velos", -38.5, 22, 8, {"nombre": 4, "variant": 1}),
        ("poubelles_tri", -40.6, -74, 7, {"variant": 0}),
        ("poubelles_tri", 40.6, -60, 7, {"variant": 1}),
        ("panneau_route", 40.5, -114, 2, {"variant": 0}),
        ("panneau_route", -40.5, 14, 2, {"variant": 2}),
        ("panneau_route", -40.5, -30, 2, {"variant": 1}),
    ]
    for i, (fn, x, z, L, kw) in enumerate(objets):
        s = -1 if x < 0 else 1
        reserver(s, z - L / 2, z + L / 2, f"{fn} {z}")
        place(b, "mobilier", fn, (x, 0, z), yaw=face_couloir(x), group=f"Rue/Objets/{i:02d}_{fn}", emprise=(L, 3, 6), **kw)
    # --- quartier des tours : lampadaires, arbres, garde-corps ---
    tours = {
        -1: [("lampadaire", -170), ("arbre_rue", -186), ("lampadaire", -202), ("arbre_rue", -218), ("lampadaire", -244)],
        1: [("lampadaire", -206), ("arbre_rue", -222), ("lampadaire", -238), ("arbre_rue", -254), ("lampadaire", -282)],
    }
    for s, items in tours.items():
        cote = "G" if s < 0 else "D"
        for i, (fn, z) in enumerate(items):
            x = s * (37 if fn == "lampadaire" else 38)
            reserver(s, z - 2, z + 2, f"{fn} {z}")
            kw = {"variant": i % 2} if fn == "lampadaire" else {"variant": i % 3, "taille": 0.8}
            place(b, "mobilier", fn, (x, 0, z), yaw=face_couloir(x), group=f"Tours/Rue/{cote}{i}_{fn}", emprise=(4, 4, 14), **kw)
    for i, (x, z) in enumerate(((-33.8, -194), (-33.8, -226), (33.8, -214), (33.8, -246), (33.8, -270))):
        place(b, "mobilier", "glissiere", (x, 0, z), yaw=90, group=f"Tours/Rue/Glissiere{i}", emprise=(12, 0.4, 3), longueur=12)


# ---------------------------------------------------------------------------
# Repères, découpage, vérifications
# ---------------------------------------------------------------------------

def reperes(b: Builder) -> None:
    """Pièces invisibles utiles au jeu : zone des œufs, entrée, sortie, couloir."""
    inv = dict(transparency=1.0, collide=False, shadow=False)
    with b.group("Reperes"):
        b.box((-R_PLACE, 0, Z_PLACE - R_PLACE), (R_PLACE, 1, Z_PLACE + R_PLACE), "#ffffff", name="ZoneOeufs", **inv)
        b.box((-DEMI_COULOIR, 0, Z_PORTE + 18), (DEMI_COULOIR, 1, Z_PORTE + 24), "#ffffff", name="Entree", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE), (DEMI_COULOIR, 1, Z_SORTIE + 6), "#ffffff", name="Sortie", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE), (DEMI_COULOIR, 1, Z_PORTE), "#ffffff", name="Couloir", **inv)


def decouper(b: Builder, prefixes=("Sol/", "Fond/", "Monuments/Viaduc", "Monuments/Effondre", "Monuments/Voile"), taille: float = 64) -> None:
    """Range les pièces des grands ensembles dans des sous-modèles de 64 × 64 studs (streaming Roblox)."""
    for p in b.parts:
        if p.group.startswith(prefixes):
            i, j = math.floor(p.pos[0] / taille), math.floor(p.pos[2] / taille)
            racine = "/".join(p.group.split("/")[:2])
            reste = p.group[len(racine):]
            p.group = f"{racine}/Bloc_{i:+d}_{j:+d}{reste}"


def build_zone(seed: int = 7) -> Builder:
    OCCUPE[-1].clear()
    OCCUPE[1].clear()
    b = Builder(seed=seed)
    sols(b)
    skyline_lateral(b)
    entree(b)
    passerelles(b)
    immeubles(b)
    carrefour(b)
    incident(b)
    mobilier_rue(b)
    reperes(b)
    decouper(b)
    return b


def _boite(p):
    R = np.asarray(p.rot).reshape(3, 3)
    half = np.abs(R) @ (np.asarray(p.size) / 2)
    return np.asarray(p.pos) - half, np.asarray(p.pos) + half


def couloir_libre(b: Builder) -> list:
    """Liste ce qui encombre le couloir de course au sol (pièces solides dans |x| < 32, 0,05 < y < 12)."""
    gene = []
    for p in b.parts:
        if not p.collide or p.group.startswith(("Sol", "Reperes")):
            continue
        lo, hi = _boite(p)
        if lo[0] < DEMI_COULOIR - 0.05 and hi[0] > -DEMI_COULOIR + 0.05 and lo[1] < 12 and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            gene.append((p.group, p.name, [round(v, 1) for v in lo], [round(v, 1) for v in hi]))
    return gene


def trop_bas_au_dessus(b: Builder, y_min: float = 30.0) -> list:
    """Toute pièce (solide ou non) au-dessus de |x| < 33 et sous `y_min` : la caméra Roblox sauterait."""
    out = []
    for p in b.parts:
        if p.group.startswith(("Sol", "Reperes")):
            continue
        lo, hi = _boite(p)
        if lo[0] < X_LIBRE_HAUT - 0.01 and hi[0] > -X_LIBRE_HAUT + 0.01 and lo[1] < y_min and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name, round(lo[1], 1)))
    return out


def meta() -> dict:
    return {"nom": "ZoneJujutsuKaisen", "version": VERSION, "largeur_couloir": 2 * DEMI_COULOIR,
            "longueur": -Z_SORTIE, "spawn": [0, 0, Z_PORTE + 24]}


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
                      "trop_bas_au_dessus_du_couloir": bas[:20], "nb_trop_bas": len(bas)}, ensure_ascii=False))
    if args.stats:
        for k, v in b.stats().items():
            print(f"{v:6d}  {k}")
        sous = {}
        for p in b.parts:
            if p.group.startswith("Sol"):
                k = "/".join(p.group.split("/")[:2])
                sous[k] = sous.get(k, 0) + 1
        for k, v in sorted(sous.items()):
            print(f"        {v:6d}  {k}")


if __name__ == "__main__":
    main()
