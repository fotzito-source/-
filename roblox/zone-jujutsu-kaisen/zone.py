#!/usr/bin/env python3
"""Plan de la zone 5 (ville de nuit) (la ville de nuit pendant un incident surnaturel) en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course occupe x ∈ [-45, 45] (90 de large), bordé de trottoirs jusqu'aux façades (|x| = 55) ;
- on entre sous un viaduc ferroviaire (z = 0, dessous à 36 studs, train qui sort de la gare aérienne) et on
  court vers -Z : rue commerçante (−12 → −150, petit carrefour en −92, passerelle piétonne en −150), quartier
  des tours et des grands écrans (−156 → −296, passerelle en −300), approche du grand carrefour (−300 → −354 :
  tour cylindrique, immeuble à écrans), grand carrefour « scramble » = place des œufs (centre −400, rayon 34),
  puis l'incident (−446 → −474 : fissures violettes, gravats, barrières 立入禁止) et la sortie sous un
  immeuble effondré en arche (−474 → −496, 110 studs libres entre les moignons) vers la zone suivante ;
- une seconde rangée (|x| ≥ 97) et des tours d'arrière-plan (|x| ≥ 151) ferment les côtés ; deux dômes de
  barrière violet nuit se dressent au bout de la grande rue transversale.

    python zone.py                     # écrit build/parts.json (aucune dépendance à Blender)
    python zone.py --stats             # nombre de pièces par groupe et chevauchements entre assets posés
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
DEMI_COULOIR = 45        # couloir de course x ∈ [-45, 45] (90 de large)
X_LIBRE_HAUT = 46        # au-dessus de |x| < 46, rien sous y = 30
H_LIBRE = 34             # dessous des ouvrages qui enjambent le couloir (passerelles, immeuble effondré)
H_VIADUC = 36            # dessous des poutres du viaduc d'entrée
Y_RAIL = 42              # niveau des rails sur le viaduc
X_FACADE = 55            # alignement des façades (trottoirs de 10 studs)
X_SECOND = 97            # seconde rangée d'immeubles
X_SKYLINE = 151          # tours d'arrière-plan
X_FOND = 263             # bord du sol
Z_APPROCHE = 56          # sol devant le viaduc (côté apparition, peut être supprimé : groupe Sol/Approche)
Z_PORTE = 0              # axe du viaduc d'entrée
Z_RUE = -12              # première façade après le viaduc (côté droit)
Z_RUE_G = -15            # côté gauche : la marquise de la gare aérienne descend jusqu'à z = -14,3
Z_RUELLE = (-100, -84)   # petite rue transversale de la rue commerçante
Z_PASSERELLE_1 = -150
Z_TOURS = -156
Z_PASSERELLE_2 = -300
Z_PLACE = -390           # centre du grand carrefour = place des œufs
R_PLACE = 34
DEMI_TRANSVERSALE = 34   # demi-largeur de la chaussée de la grande rue transversale
X_CARREFOUR = 59         # demi-largeur du carré peint du carrefour (passages piétons compris)
Z_CARREFOUR_N, Z_CARREFOUR_S = Z_PLACE + 46, Z_PLACE - 46      # -344, -436
Z_TRANSVERSALE = (Z_PLACE - DEMI_TRANSVERSALE, Z_PLACE + DEMI_TRANSVERSALE)
Z_EFFONDRE = -485        # immeuble effondré (repère final), emprise z ∈ [-496, -474]
Z_SORTIE = -496
DOME_G = (-200, -432, 62)    # dômes de barrière : (x, z, rayon)
DOME_D = (196, -428, 64)
Y_COLONNE = 150              # sommet des colonnes de voile qui montent des dômes (visibles depuis la rue)

VERSION = "1.0"


# ---------------------------------------------------------------------------
# Accès aux assets (avec bloc d'attente si un module manque encore)
# ---------------------------------------------------------------------------

# Assets posés : (groupe complet, première pièce, fin) → contrôle des chevauchements entre assets.
POSES: list = []


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
        n0 = len(b.parts)
        g = b._groups[-1]
        try:
            if f is not None:
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
        finally:
            POSES.append((g, n0, len(b.parts)))


def face_couloir(x: float) -> float:
    """Rotation qui tourne l'avant d'un asset (-Z local) vers le couloir."""
    return -90.0 if x < 0 else 90.0


def xt(s: int, d: float) -> float:
    """Abscisse sur le trottoir du côté s, à d studs de l'alignement des façades."""
    return s * (X_FACADE - d)


# Occupation des trottoirs (|x| ∈ [45, 55]) : évite d'empiler escaliers, poteaux et mobilier.
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
    assert abs(nx * cell - (x1 - x0)) < 1e-6 and abs(nz * cell - (z1 - z0)) < 1e-6, (x0, x1, z0, z1, cell)
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
    [(-40, -447), (-24, -457), (-30, -469), (-11, -481), (-16, -496)],
    [(8, -446), (16, -455), (5, -466), (22, -477), (13, -491)],
    [(54, -449), (38, -461), (46, -473), (30, -487), (35, -496)],
    [(-54, -458), (-45, -466), (-51, -480), (-40, -490)],
    [(-24, -457), (-7, -462), (5, -466)],
    [(22, -477), (36, -474)],
    [(-30, -469), (-42, -476), (-50, -486)],
    [(46, -473), (53, -482), (50, -494)],
    [(-20, -437), (-12, -444), (-24, -447)],
    [(28, -437), (20, -443), (8, -446)],
    [(-44, -440), (-36, -452), (-54, -458)],
    [(2, -470), (-9, -476), (-11, -481)],
    [(30, -455), (16, -455)],
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
    Renvoie None hors du carré |x| ≤ 59, z ∈ [-446, -354]."""
    W, T, Q = DEMI_COULOIR, DEMI_TRANSVERSALE, X_CARREFOUR
    QZ = Z_CARREFOUR_N - Z_PLACE                              # 46
    dz = z - Z_PLACE
    ax, adz = abs(x), abs(dz)
    if ax > Q or adz > QZ:
        return None
    blanc, asph = c("marquage"), c("asphalte_place")
    if ax > W and adz > T:                                   # coins de trottoir
        if ax < W + 2 or adz < T + 2:
            return c("bordure")
        return c("guidage") if (ax < W + 8 and adz < T + 6) else c("trottoir_clair")
    if adz > T:                                              # passages nord et sud (bandes selon z)
        if adz < T + 2 or adz > QZ - 2:
            return asph
        return blanc if ax < W - 2 and math.floor((x + W) / 2) % 2 == 0 else asph
    if ax > W:                                               # passages est et ouest (bandes selon x)
        if ax < W + 2 or ax > Q - 2:
            return asph
        return blanc if adz < T - 2 and math.floor((dz + T) / 2) % 2 == 0 else asph
    # diagonales (X) : bandes de 12 studs, rayures parallèles au couloir
    k = T / W
    for sgn in (1, -1):
        d = abs(dz - sgn * k * x) / math.hypot(1, k)
        if d < 6 and adz < T - 2 and ax < W - 2:
            return blanc if math.floor((x + W) / 2) % 2 == 0 else asph
    return asph


def marquages_couloir(x: float, z: float):
    """Chaussée de la grande rue (3 voies par sens) : ligne médiane jaune double, pointillés blancs, lignes de rive."""
    ax = abs(x)
    if 1 <= ax < 3:
        return c("marquage_jaune")
    if DEMI_COULOIR - 4 <= ax < DEMI_COULOIR - 2:
        return c("marquage")
    if (15 <= ax < 17 or 29 <= ax < 31) and math.floor(z / 12) % 2 == 0:
        return c("marquage")
    return c("asphalte")


def couleur_couloir(x: float, z: float):
    m = motif_carrefour(x, z)
    if m:
        return m
    ax = abs(x)
    W = DEMI_COULOIR
    f = fissure(x, z)
    if f:
        return c("lueur_violette") if f == 2 else c("fissure")
    zr0, zr1 = Z_RUELLE
    if zr0 <= z < zr1:                                    # petit carrefour : chaussée nue
        return c("asphalte_place")
    if zr1 + 2 <= z < zr1 + 12 or zr0 - 12 <= z < zr0 - 2:   # passages piétons du petit carrefour
        return c("marquage") if ax < W - 2 and math.floor((x + W) / 2) % 2 == 0 else c("asphalte")
    if (zr1 + 14 <= z < zr1 + 16 and x < 0) or (zr0 - 16 <= z < zr0 - 14 and x > 0):   # lignes d'arrêt
        return c("marquage")
    if (Z_CARREFOUR_N + 2 <= z < Z_CARREFOUR_N + 4 and x < 0) or (Z_CARREFOUR_S - 4 <= z < Z_CARREFOUR_S - 2 and x > 0):
        return c("marquage")
    for zp in (-232, -176, -276):                          # passages piétons du quartier des tours (rythme au sol)
        if zp <= z < zp + 10:
            return c("marquage") if ax < W - 2 and math.floor((x + W) / 2) % 2 == 0 else c("asphalte")
        if (zp + 12 <= z < zp + 14 and x < 0) or (zp - 4 <= z < zp - 2 and x > 0):
            return c("marquage")
    if z < Z_CARREFOUR_S and 1 <= ax < 3:                 # incident : ligne médiane effacée par endroits
        return c("marquage_jaune") if math.floor(z / 10) % 2 else c("asphalte")
    return marquages_couloir(x, z)


def couleur_trottoir(x: float, z: float):
    m = motif_carrefour(x, z)
    if m:
        return m
    ax = abs(x)
    W = DEMI_COULOIR
    zr0, zr1 = Z_RUELLE
    if zr0 <= z < zr1:                                    # traversée de la petite rue (bandes selon x)
        return c("marquage") if 2 <= z - zr0 < 14 and math.floor(z / 2) % 2 == 0 else c("asphalte_place")
    f = fissure(x, z)
    if f:
        return c("lueur_violette") if f == 2 else c("fissure")
    if ax < W + 2:
        return c("bordure")
    if ax < W + 4:
        return c("trottoir_fonce")
    if ax < W + 6:
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
    if Z_CARREFOUR_S <= z < Z_CARREFOUR_N and ax < X_SKYLINE + 40:
        dz = abs(z - Z_PLACE)
        if zt0 <= z < zt1:                               # grande rue transversale
            if 1 <= dz < 3:
                return c("marquage_jaune")
            if DEMI_TRANSVERSALE - 4 <= dz < DEMI_TRANSVERSALE - 2:
                return c("marquage")
            if 15 <= dz < 17 and math.floor(x / 12) % 2 == 0:
                return c("marquage")
            return c("asphalte")
        if dz < DEMI_TRANSVERSALE + 2:
            return c("bordure")
        return c("guidage") if DEMI_TRANSVERSALE + 4 <= dz < DEMI_TRANSVERSALE + 6 else c("trottoir")
    zr0, zr1 = Z_RUELLE
    if zr0 <= z < zr1 and ax < X_SKYLINE:                 # petite rue
        if z < zr0 + 2 or z >= zr1 - 2:
            return c("marquage")
        return c("asphalte_place")
    if ax < X_FACADE + RECUL_ESCALIER + 0.5 and Z_CARREFOUR_N <= z < Z_RUE:   # dalles devant les façades en retrait
        return c("trottoir") if math.floor(z / 8) % 2 else c("trottoir_clair")
    if -310 <= z < Z_PASSERELLE_2 + 4 and x > 0 and ax < X_SKYLINE:   # parvis devant la tour cylindrique
        return c("trottoir_clair") if math.floor(x / 8) % 2 else c("trottoir")
    if z >= 8:                                            # parvis de la gare (côté apparition)
        return c("trottoir_clair") if (math.floor(x / 32) + math.floor(z / 16)) % 2 else c("trottoir")
    if z < Z_CARREFOUR_S and ax < 125:                    # incident : sol sale et fissuré
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
            xa, xb = sorted((s * X_FACADE, s * X_SKYLINE))
            sol_pixel(b, xa, xb, 8, Z_APPROCHE, 8, couleur_cotes)
            xa, xb = sorted((s * X_SKYLINE, s * X_FOND))
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
    """Tours d'arrière-plan qui ferment les côtés (|x| ≥ 151) : devant, un immeuble simple (`immeuble_fond` :
    rubans de fenêtres, meneaux, retrait, toit équipé) tourné vers le couloir ; derrière, un volume plus haut
    (bleu nuit, ardoise, violet) puis un volume plus bas jusqu'au bord du sol. Les deux volumes ont des rubans
    de fenêtres en ceinture (un sur quatre ou cinq éclairé) et une corniche claire ; le volume haut porte une
    couronne de néon, un néon vertical ou un panneau lumineux tourné vers le couloir, un local et un feu
    d'obstacle ou une citerne ; le volume bas, une cage d'escalier et une citerne ou des climatiseurs."""
    from assets.batiments import _citerne, _clim_toit, _local_tech   # équipements de toit des immeubles

    rng = np.random.default_rng(23)
    tons = [c("bleu_marine"), c("bleu_ardoise"), shade(c("bleu_acier"), 0.9), c("bleu_nuit"), shade(c("violet_nuit"), 1.15),
            shade(c("bleu_ardoise"), 0.85)]
    neons = [c("neon_magenta"), c("neon_cyan"), c("neon_jaune"), c("neon_orange")]
    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        z = Z_APPROCHE - 8
        k = 0
        while z > Z_SORTIE + 10:
            w = float(rng.integers(9, 18) * 2)
            if z > -16 and z - w < 19:          # viaduc et gare aérienne (z ∈ [-14,3 ; 17,5])
                z = -16
                continue
            w = min(w, z - Z_SORTIE)
            xf = X_SKYLINE + float(rng.integers(0, 3) * 4)
            d1 = float(rng.integers(10, 16) * 2)
            if _dans_dome(min(s * xf, s * (X_FOND - 2)), max(s * xf, s * (X_FOND - 2)), z - w, z):
                z -= w
                continue
            h1 = float(rng.integers(22, 44) * 2)
            h2 = h1 + float(rng.integers(5, 18) * 2)
            h3 = max(h1 - 10.0, 36.0) + float(rng.integers(0, 8) * 2)
            col = tons[k % len(tons)]
            za, zb = z - w + 1, z - 1
            n0 = len(b.parts)
            g = f"Fond/{cote}/T{k:02d}"
            # devant : immeuble simple tourné vers le couloir
            place(b, "batiments", "immeuble_fond", (s * (xf + d1 / 2), 0, (za + zb) / 2), yaw=face_couloir(s), group=f"{g}/Avant",
                  emprise=(zb - za, d1, h1), variant=(k + (s > 0)) % 4, largeur=zb - za, profondeur=d1, hauteur=h1)
            POSES.pop()                          # le volume arrière s'appuie dessus : une seule pose pour les deux
            with b.group(g):
                # derrière : volume plus haut (sa face avant entre de 1 stud dans l'immeuble de devant), puis un
                # volume plus bas jusqu'au bord du sol (silhouette en gradins vue d'avion)
                xmid = xf + d1 + float(rng.integers(14, 24) * 2)
                xa2, xb2 = sorted((s * (xf + d1 - 1), s * xmid))
                b.box((xa2, 0, za + 2), (xb2, h2, zb - 2), shade(col, 0.95), studs="top", name="Tour")
                xa3, xb3 = sorted((s * (xmid - 1), s * (X_FOND - 2)))
                b.box((xa3, 0, za + 1), (xb3, h3, zb - 1), shade(col, 0.82), studs="top", name="Tour")
                # toit du volume haut : local technique à studs
                xl = s * (xf + d1 + (xmid - xf - d1) * 0.35)
                b.box((xl - 3, h2, (za + zb) / 2 - 3), (xl + 3, h2 + 4, (za + zb) / 2 + 3), shade(col, 1.25), studs="top",
                      name="Local")
                # rubans de fenêtres en « ceinture » (un bloc qui dépasse de 0,15 des quatre faces) : les étages du
                # volume haut au-dessus des voisins, ceux du volume bas (vus d'avion et depuis le côté) ; environ un
                # sur quatre est éclairé (Neon). Aléa à part : la mise en page (rng) ne change pas.
                r2 = np.random.default_rng(500 + 37 * k + (s > 0))
                style = (k + 2 * (s > 0)) % 4
                eteint = (c("vitre"), c("vitre_bleue"), c("carrelage"), c("vitre_claire"))[style]
                e = 0.15

                def ceinture(x0, x1, z0, z1, y0, y1, lit, couleur=None, nom="Ruban", neon=None, d=e):
                    cc = couleur or ((c("fenetre_froide"), c("fenetre_chaude"))[int(r2.integers(0, 2))] if lit else eteint)
                    neon = (couleur is not None) if neon is None else neon     # fenêtres lointaines : pas de Neon
                    b.box((x0 - d, y0, z0 - d), (x1 + d, y1, z1 + d), cc, material="Neon" if neon else "SmoothPlastic",
                          collide=False, shadow=False, name=nom)

                for y in np.arange(max(12.0, min(h1, h3) - 12.0), h2 - 6.0, 8.0):
                    ceinture(xa2, xb2, za + 2, zb - 2, float(y), float(y) + 3.0, r2.random() < 0.25)
                for y in np.arange(8.0, h3 - 5.0, 8.0):
                    ceinture(xa3, xb3, za + 1, zb - 1, float(y), float(y) + 3.0, r2.random() < 0.2)
                # corniches claires en haut des deux volumes : les toits se détachent mieux vus d'avion
                ceinture(xa2, xb2, za + 2, zb - 2, h2 - 1.0, h2 - 0.1, False, shade(col, 1.4), "Corniche", neon=False, d=0.25)
                ceinture(xa3, xb3, za + 1, zb - 1, h3 - 1.0, h3 - 0.1, False, shade(col, 1.3), "Corniche", neon=False, d=0.25)
                # toit du volume bas : cage d'escalier, citerne ou climatiseurs
                zc = (za + zb) / 2
                if X_FOND - 2 - xmid >= 24:
                    _local_tech(b, s * (xmid + 6.5), h3, zc + (zb - za) / 2 - 6.0, 5.0, 6.0, 4.0, shade(col, 1.3))
                    if k % 2:
                        _citerne(b, s * (X_FOND - 9.0), h3, zc - (zb - za) / 2 + 5.0, r=2.0, h=3.2)
                    else:
                        _clim_toit(b, s * (X_FOND - 10.0), h3, zc - 2.0)
                        _clim_toit(b, s * (X_FOND - 14.0), h3, zc - 2.0)
                if k % 3 == 0:                   # couronne lumineuse, sous la corniche
                    ceinture(xa2, xb2, za + 2, zb - 2, h2 - 2.6, h2 - 1.4, True, neons[(k // 3) % len(neons)], "Couronne")
                elif k % 3 == 2 and zb - za >= 18:
                    # panneau lumineux de toit tourné vers le couloir (vu de la rue au-dessus des premières rangées)
                    xp = s * (xf + d1 + 1.5)
                    zp0, zp1 = za + 4, zb - 4
                    for zz in (zp0 + 1.5, zp1 - 1.5):
                        b.box((xp - 0.4, h2, zz - 0.4), (xp + 0.4, h2 + 2.5, zz + 0.4), c("metal_fonce"), name="Montant")
                    ya, yb = h2 + 2.5, h2 + 2.5 + min(11.0, 0.6 * (zp1 - zp0))
                    b.box((xp - 0.35, ya, zp0), (xp + 0.35, yb, zp1), c("ecran_fond"), name="Panneau")
                    fa, fb = sorted((s * (xf + d1 + 1.5 - 0.5), s * (xf + d1 + 1.5 - 0.35)))
                    pal = ((c("ecran_rose"), c("neon_jaune")), (c("ecran_bleu"), c("neon_cyan")), (c("ecran_orange"), c("neon_rose")))
                    p1, p2 = pal[(k // 3 + (s > 0)) % 3]
                    zm = zp0 + 0.6 + (zp1 - zp0 - 1.2) * 0.62
                    b.box((fa, ya + 0.6, zp0 + 0.6), (fb, yb - 0.6, zm), p1, material="Neon", collide=False, shadow=False, name="Ecran")
                    b.box((fa, ya + 0.6, zm), (fb, yb - 0.6, zp1 - 0.6), p2, material="Neon", collide=False, shadow=False, name="Ecran")
                xm = s * (xf + d1 + (xmid - xf - d1) * 0.75)
                if k % 2 == 0:
                    b.box((xm - 0.6, h2, (za + zb) / 2 - 0.6), (xm + 0.6, h2 + 1.2, (za + zb) / 2 + 0.6), c("rouge_balise"),
                          material="Neon", collide=False, shadow=False, name="Balise")
                else:
                    b.cyl((xm, h2 + 2.5, (za + zb) / 2), 2.2, 5, c("citerne"), name="Citerne")
                if k % 3 == 1:
                    na, nb = sorted((s * (xf + d1 - 1.3), s * (xf + d1 - 0.5)))
                    b.box((na, h1 + 2, za + 2.6), (nb, h2 - 4, za + 3.6), neons[k % len(neons)], material="Neon",
                          collide=False, shadow=False, name="Neon")
            POSES.append((g, n0, len(b.parts)))
            z -= w
            k += 1


# ---------------------------------------------------------------------------
# Entrée : viaduc ferroviaire, train, gare aérienne
# ---------------------------------------------------------------------------

def entree(b: Builder) -> None:
    passage = 2 * DEMI_COULOIR + 2                 # 92 studs libres entre les piles du couloir
    place(b, "ouvrages", "viaduc_ferroviaire", (0, 0, Z_PORTE), group="Monuments/Viaduc", emprise=(2 * X_FOND - 8, 16, Y_RAIL + 3),
          portique=(passage, H_VIADUC), longueur=2 * X_FOND - 8, hauteur_libre=H_VIADUC, niveau_rail=Y_RAIL,
          passage=passage, gare=True)
    for s in (-1, 1):
        reserver(s, Z_PORTE - 8, Z_PORTE + 8, "piles du viaduc")
    # train de banlieue qui sort de la gare aérienne (quais en x ∈ [-163, -59]) : la tête passe au-dessus du
    # couloir, sur la voie côté apparition (z = +3,5)
    place(b, "ouvrages", "train_banlieue", (-38, Y_RAIL, Z_PORTE + 3.5), group="Monuments/Train", emprise=(86, 5, 7),
          voitures=4)


def passerelles(b: Builder) -> None:
    """Deux passerelles piétonnes au-dessus du couloir (dessous à 34, 108 studs entre les tours d'appui),
    escaliers le long des trottoirs (|x| ∈ [46,5 ; 54,5])."""
    portee = 2 * X_FACADE                            # 110 : tours d'appui en |x| ∈ [46,5 ; 54,5]
    for i, (z, escaliers) in enumerate(((Z_PASSERELLE_1, ("+z", "-z")), (Z_PASSERELLE_2, ("+z", "+z")))):
        place(b, "ouvrages", "passerelle_pietons", (0, 0, z), group=f"Monuments/Passerelle{i + 1}", emprise=(portee, 8, H_LIBRE + 5),
              portique=(2 * DEMI_COULOIR + 2, H_LIBRE), variant=i, portee=portee, hauteur_libre=H_LIBRE, escaliers=escaliers)
        for s, sens in zip((-1, 1), escaliers):
            reserver(s, z - 4, z + 4, f"passerelle {i + 1}")
            z0, z1 = (z + 4, z + 46) if sens == "+z" else (z - 46, z - 4)
            reserver(s, z0, z1, f"escalier passerelle {i + 1}")
            if _asset("ouvrages", "passerelle_pietons") is None:
                with b.group(f"Monuments/Passerelle{i + 1}"):
                    b.box((xt(s, 8.5), 0, z0), (xt(s, 0.5), H_LIBRE * 0.6, z1), "#ff4fd8", transparency=0.6,
                          name="ATTENTE_ouvrages_escalier")


def parvis_approche(b: Builder) -> None:
    """Parvis devant le viaduc, côté apparition (z de 20 à 52, |x| ≥ 60) : arbres, bancs, lampadaires et vélos.
    Groupe `Parvis` : à supprimer avec `Sol/Approche` si la zone précédente touche directement le viaduc."""
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        for i, (x, z, v) in enumerate(((64, 34, 0), (84, 44, 2), (104, 34, 1), (124, 44, 0), (142, 32, 2))):
            place(b, "mobilier", "arbre_rue", (s * x, 0, z), group=f"Parvis/{cote}/Arbre{i}", variant=(v + (s > 0)) % 3,
                  taille=0.9, emprise=(4, 4, 12))
        for i, (x, z) in enumerate(((74, 39), (114, 39))):
            place(b, "mobilier", "lampadaire", (s * x, 0, z), group=f"Parvis/{cote}/Lampadaire{i}", variant=2, emprise=(4, 4, 14))
        for i, (x, z) in enumerate(((94, 30), (134, 50))):
            place(b, "mobilier", "banc", (s * x, 0, z), yaw=180, group=f"Parvis/{cote}/Banc{i}", emprise=(6, 2, 3))
        place(b, "mobilier", "velos", (s * 96, 0, 50), group=f"Parvis/{cote}/Velos", variant=1 + (s > 0), nombre=5, emprise=(10, 3, 3))


# ---------------------------------------------------------------------------
# Rangées d'immeubles
# ---------------------------------------------------------------------------

# (fonction, largeur le long du couloir, profondeur, paramètres, écart après)
# Avec une rue de 110 studs entre façades, les petits immeubles ont 4 à 8 étages.
RUE_GAUCHE_A = [
    ("batiments:immeuble_boutique", 14, 26, {"variant": 0, "enseigne": "ラーメン", "etages": 5}, 2),
    ("batiments:immeuble_boutique", 20, 28, {"variant": 3, "enseigne": "カラオケ", "etages": 8, "panneau_toit": True}, 2),
    ("batiments:immeuble_boutique", 14, 24, {"variant": 2, "enseigne": "薬", "etages": 4}, 2),
    ("batiments:immeuble_boutique", 15, 26, {"variant": 1, "enseigne": "本", "etages": 6}, 0),
]
RUE_GAUCHE_B = [
    ("batiments:superette", 24, 26, {"variant": 0}, 2),
    ("batiments:immeuble_boutique", 24, 28, {"variant": 4, "enseigne": "寿司", "etages": 6}, 0),
]
RUE_DROITE_A = [
    ("batiments:superette", 24, 26, {"variant": 1}, 2),
    ("batiments:immeuble_boutique", 16, 26, {"variant": 1, "enseigne": "本", "etages": 6}, 2),
    ("batiments:immeuble_boutique", 12, 24, {"variant": 5, "enseigne": "カラオケ", "etages": 8}, 2),
    ("batiments:immeuble_boutique", 14, 24, {"variant": 0, "enseigne": "ラーメン", "etages": 5}, 0),
]
RUE_DROITE_B = [
    ("batiments:immeuble_boutique", 20, 28, {"variant": 3, "enseigne": "映画", "etages": 7}, 2),
    ("batiments:immeuble_boutique", 14, 24, {"variant": 2, "enseigne": "薬", "etages": 5}, 2),
    ("batiments:immeuble_boutique", 12, 24, {"variant": 5, "enseigne": "喫茶", "etages": 8}, 0),
]
TOURS_GAUCHE = [
    ("batiments:tour_bureaux", 30, 34, {"variant": 1, "hauteur": 112}, 4),
    ("batiments:grand_magasin", 40, 36, {"variant": 0, "hauteur": 72}, 4),
    ("batiments:tour_bureaux", 28, 34, {"variant": 0, "hauteur": 132, "panneau_toit": True}, 4),
    ("batiments:tour_bureaux", 30, 32, {"variant": 2, "hauteur": 96}, 0),
]
TOURS_DROITE = [
    ("batiments:tour_bureaux", 28, 34, {"variant": 3, "hauteur": 100}, 4),
    ("batiments:tour_bureaux", 32, 34, {"variant": 4, "hauteur": 146}, 4),
    ("batiments:grand_magasin", 40, 36, {"variant": 1, "hauteur": 64}, 4),
    ("batiments:immeuble_boutique", 28, 30, {"variant": 3, "enseigne": "カラオケ", "etages": 8, "panneau_toit": True}, 0),
]
APPROCHE_GAUCHE = [
    ("batiments:immeuble_boutique", 10, 22, {"variant": 5, "enseigne": "ラーメン", "etages": 8}, 2),
    ("carrefour:immeuble_ecran", 32, 44, {"variant": 0, "hauteur": 72, "angle": "gauche"}, 0),
]


def _hauteur_attente(params: dict) -> float:
    if "hauteur" in params:
        return params["hauteur"]
    return 9 + 8 * (params.get("etages", 2) - 1) + 1.5


RECUL_ESCALIER = 4.5      # recul des façades derrière un escalier de passerelle (balcons et enseignes : 4 studs)


def _devant_escalier(s: int, z0: float, z1: float) -> bool:
    return any(z0 < zb and z1 > za for (za, zb, nom) in OCCUPE[s] if nom.startswith(("escalier", "passerelle")))


def rangee(b: Builder, s: int, z_debut: float, z_fin: float, plan, nom: str) -> list:
    """Aligne une rangée d'immeubles le long du couloir (façade en |x| = 55, en retrait de 4,5 derrière les
    escaliers des passerelles), de z_debut vers -Z."""
    cote = "Gauche" if s < 0 else "Droite"
    z = z_debut
    poses = []
    for i, (kind, larg, prof, params, ecart) in enumerate(plan):
        zc = z - larg / 2
        mod, fn = kind.split(":")
        kw = dict(params)
        kw.setdefault("largeur", larg)
        kw.setdefault("profondeur", prof)
        recul = RECUL_ESCALIER if _devant_escalier(s, z - larg, z) else 0.0
        x = s * (X_FACADE + recul + prof / 2)
        info = place(b, mod, fn, (x, 0, zc), yaw=face_couloir(x), group=f"{nom}/{cote}/{i:02d}_{fn}",
                     emprise=(larg, prof, _hauteur_attente(params)), **kw)
        poses.append((x, zc, larg, prof, info))
        z -= larg + ecart
    assert z >= z_fin - 0.01, f"rangée {nom} {cote} trop longue ({z} < {z_fin})"
    return poses


SECONDE_RANGEE = {
    # (z centre, largeur, profondeur, hauteur, variante) ; façade en |x| = 97
    -1: [(-27, 24, 32, 64, 0), (-53, 26, 32, 74, 1), (-75, 16, 30, 56, 2), (-112, 22, 34, 70, 3), (-138, 22, 32, 60, 1),
         (-180, 28, 34, 84, 2), (-210, 24, 32, 66, 3), (-240, 30, 34, 96, 0), (-276, 26, 32, 78, 1)],
    1: [(-26, 22, 32, 70, 2), (-54, 28, 34, 60, 3), (-76, 14, 30, 52, 0), (-114, 24, 32, 76, 1), (-140, 18, 30, 56, 2),
        (-168, 24, 32, 70, 0), (-200, 26, 34, 88, 3), (-232, 26, 32, 64, 2), (-262, 28, 34, 100, 1)],
}


def immeubles(b: Builder) -> dict:
    poses = {}
    for s, (pa, pb, pt, pp) in ((-1, (RUE_GAUCHE_A, RUE_GAUCHE_B, TOURS_GAUCHE, APPROCHE_GAUCHE)),
                                (1, (RUE_DROITE_A, RUE_DROITE_B, TOURS_DROITE, None))):
        poses[s] = []
        poses[s] += rangee(b, s, Z_RUE_G if s < 0 else Z_RUE, Z_RUELLE[1], pa, "Rue")
        poses[s] += rangee(b, s, Z_RUELLE[0], Z_PASSERELLE_1, pb, "Rue")
        poses[s] += rangee(b, s, Z_TOURS, Z_PASSERELLE_2 + 4, pt, "Tours")
        if pp:
            poses[s] += rangee(b, s, Z_PASSERELLE_2, Z_CARREFOUR_N, pp, "Approche")
        for i, (zc, larg, prof, h, v) in enumerate(SECONDE_RANGEE[s]):
            x = s * (X_SECOND + prof / 2)
            place(b, "batiments", "immeuble_fond", (x, 0, zc), yaw=face_couloir(x), group=f"Arriere/{'Gauche' if s < 0 else 'Droite'}/{i:02d}",
                  emprise=(larg, prof, h), variant=v, largeur=larg, profondeur=prof, hauteur=h)
    # immeubles de la grande rue transversale (côté nord), tournés vers le carrefour (-Z)
    for i, (x, larg, prof, h, v) in enumerate(((-125, 40, 18, 62, 1), (129, 38, 18, 70, 3))):
        place(b, "batiments", "immeuble_fond", (x, 0, Z_CARREFOUR_N + prof / 2), yaw=0, group=f"Arriere/Transversale{i}",
              emprise=(larg, prof, h), variant=v, largeur=larg, profondeur=prof, hauteur=h)
    # derrière l'immeuble à écrans (gauche) et derrière la tour cylindrique (droite)
    place(b, "batiments", "immeuble_fond", (-118, 0, -311), yaw=-90, group="Arriere/Approche0", emprise=(26, 30, 76),
          variant=2, largeur=26, profondeur=30, hauteur=76)
    place(b, "batiments", "immeuble_fond", (128, 0, -310), yaw=90, group="Arriere/Approche1", emprise=(24, 30, 82),
          variant=0, largeur=24, profondeur=30, hauteur=82)
    return poses


# ---------------------------------------------------------------------------
# Grand carrefour (place des œufs)
# ---------------------------------------------------------------------------

def carrefour(b: Builder) -> None:
    # tour cylindrique au coin nord-est, tournée vers le centre du carrefour
    place(b, "carrefour", "tour_cylindrique", (81, 0, -330), yaw=49.2, group="Carrefour/TourCylindrique", emprise=(48, 48, 100),
          rayon=22, hauteur=84)
    # gare au coin sud-ouest, longue façade vitrée tournée vers le carrefour (+Z), sortie 出口 vers le couloir
    place(b, "carrefour", "gare_facade", (-86, 0, Z_CARREFOUR_S - 13), yaw=180, group="Carrefour/Gare", emprise=(62, 26, 28),
          variant=0, largeur=62, profondeur=26, hauteur=28)
    # coin sud-est : tour de verre endommagée (début de l'incident), et sa voisine derrière
    place(b, "incident", "tour_endommagee", (X_FACADE + 16, 0, Z_CARREFOUR_S - 13), yaw=90, group="Carrefour/TourEndommagee",
          emprise=(26, 32, 70), variant=0, largeur=26, profondeur=32, hauteur=74)
    place(b, "incident", "tour_endommagee", (110, 0, -460), yaw=180, group="Incident/TourEndommagee2",
          emprise=(32, 24, 58), variant=1, largeur=32, profondeur=24, hauteur=62)
    # feux aux quatre coins (face au couloir) et face à la rue transversale
    W = DEMI_COULOIR
    for i, (x, z, yaw, v) in enumerate(((-(W + 8), Z_CARREFOUR_N - 4, -90, 0), (W + 8, Z_CARREFOUR_N - 4, 90, 1),
                                        (-(W + 8), Z_CARREFOUR_S + 4, -90, 1), (W + 8, Z_CARREFOUR_S + 4, 90, 0),
                                        (-(W + 12), Z_CARREFOUR_N - 8, 0, 1), (W + 12, Z_CARREFOUR_N - 8, 0, 0),
                                        (-(W + 12), Z_CARREFOUR_S + 8, 180, 0), (W + 12, Z_CARREFOUR_S + 8, 180, 1))):
        if abs(x) < X_FACADE:
            reserver(-1 if x < 0 else 1, z - 1, z + 1, f"feu carrefour {z}")
        place(b, "mobilier", "feu_tricolore", (x, 0, z), yaw=yaw, group=f"Carrefour/Feu{i}", emprise=(2, 7, 14), variant=v,
              bras=6.5)
    # bout de la rue transversale côté -X : immeuble couvert d'écrans géants tourné vers le carrefour (+X)
    place(b, "carrefour", "immeuble_ecran", (-112, 0, Z_PLACE), yaw=0, group="Carrefour/EcransOuest", emprise=(42, 44, 66),
          variant=3, largeur=42, profondeur=44, hauteur=66, angle="droite")
    # parvis de la tour cylindrique : arbres et bancs
    for i, x in enumerate((63, 105)):
        place(b, "mobilier", "arbre_rue", (x, 0, -301.5), group=f"Carrefour/Parvis/Arbre{i}", variant=(0, 2)[i], taille=0.9,
              emprise=(4, 4, 12))
    for i, x in enumerate((74, 94)):
        place(b, "mobilier", "banc", (x, 0, -300.5), yaw=180, group=f"Carrefour/Parvis/Banc{i}", emprise=(6, 2, 3))


# ---------------------------------------------------------------------------
# Incident et sortie
# ---------------------------------------------------------------------------

def colonne_voile(b: Builder, x: float, z: float, r: float, groupe: str) -> None:
    """Colonne de voile violette qui monte du sommet d'un dôme jusqu'à Y_COLONNE : dalles translucides
    empilées, arêtes au néon, anneaux lumineux. Elle dépasse des toits et se voit depuis la rue."""
    with b.group(groupe):
        y = r - 2.0
        k = 0
        while y < Y_COLONNE - 0.5:
            h = min(14.0, Y_COLONNE - y)
            w = 12.0 - 3.0 * (k % 2) * 0.5
            b.boxc((x, y + h / 2, z), (w, h, w), c("voile_moyen") if k % 2 else c("voile_clair"), yaw=(k * 17) % 90,
                   transparency=0.35, collide=False, name="Colonne")
            y += h
            k += 1
        for dx, dz in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            b.boxc((x + dx * 6.3, (r + Y_COLONNE) / 2, z + dz * 6.3), (0.6, Y_COLONNE - r, 0.6), c("voile_bord"),
                   material="Neon", collide=False, name="Arete")
        for yy in (r + 18, r + 46, Y_COLONNE - 4):
            b.boxc((x, yy, z), (15.0, 1.0, 15.0), c("lueur_violette"), material="Neon", transparency=0.2, collide=False,
                   name="Anneau")


def incident(b: Builder) -> None:
    place(b, "incident", "immeuble_effondre", (0, 0, Z_EFFONDRE), group="Monuments/Effondre", emprise=(220, 22, 100),
          portique=(2 * DEMI_COULOIR, H_LIBRE), passage=2 * DEMI_COULOIR, hauteur_libre=H_LIBRE)
    for i, (x, z, r) in enumerate((DOME_G, DOME_D)):
        place(b, "incident", "voile_dome", (x, 0, z), group=f"Monuments/Voile{i + 1}", emprise=(2 * r, 2 * r, r),
              variant=i, rayon=r)
    for i, (x, z, r) in enumerate((DOME_G, DOME_D)):
        colonne_voile(b, x, z, r, f"Monuments/Voile{i + 1}/Colonne")
    # trottoirs du couloir (|x| 45-55) : barrières 立入禁止, voitures abandonnées, gravats — réservés pour ne rien empiler
    trottoirs = [
        ("gravats", -1, 4, -440, 15, 6, {"variant": 2, "taille": 0.9}),
        ("barriere_chantier", 1, 7, -441, 90, 8, {"longueur": 8, "variant": 2}),
        # (fonction, côté, distance à la façade, z, yaw, longueur occupée le long du trottoir, paramètres)
        ("barriere_chantier", -1, 7, -450.5, 90, 8, {"longueur": 8, "variant": 0}),
        ("voiture_abandonnee", -1, 4.5, -460, 0, 9, {"variant": 1}),
        ("gravats", -1, 4, -470, 40, 6, {"variant": 0, "taille": 0.9}),
        ("gravats", 1, 4, -450, 110, 5, {"variant": 1, "taille": 0.8}),
        ("barriere_chantier", 1, 7, -458, 90, 8, {"longueur": 8, "variant": 1}),
        ("voiture_abandonnee", 1, 4.5, -468.5, 180, 9, {"variant": 2}),
    ]
    for i, (fn, s, d, z, yaw, L, kw) in enumerate(trottoirs):
        reserver(s, z - L / 2, z + L / 2, f"{fn} {z}")
        mod = "mobilier" if fn == "barriere_chantier" else "incident"
        place(b, mod, fn, (xt(s, d), 0, z), yaw=yaw, group=f"Incident/Trottoir{i:02d}_{fn}", emprise=(4.6, L, 4), **kw)
    # rue transversale et abords : gravats, voitures, barrières qui coupent la rue devant les dômes
    dz = Z_PLACE + 400                     # positions écrites pour le carrefour en z = -400
    for i, (x, z, v, t) in enumerate(((-72, -438, 2, 1.0), (68, -438, 0, 1.1), (-75, -372, 1, 1.0), (98, -414, 2, 0.9),
                                      (124, -362, 1, 1.0), (-104, -362, 0, 0.8), (-84, -430, 1, 0.7), (112, -432, 3, 1.0))):
        z += dz
        place(b, "incident", "gravats", (x, 0, z), yaw=(i * 67) % 360, group=f"Incident/Gravats{i}", emprise=(6, 6, 3), variant=v, taille=t)
    for i, (x, z, yaw, v) in enumerate(((-80, -404, 30, 0), (84, -420, -20, 3), (118, -392, 75, 1))):
        z += dz
        place(b, "incident", "voiture_abandonnee", (x, 0, z), yaw=yaw, group=f"Incident/Voiture{i}", emprise=(4.6, 9, 4), variant=v)
    for i, (x, z, yaw, L, v) in enumerate(((-78, -443, 0, 12, 2), (80, -443, 0, 12, 1), (-84, -422, 0, 10, 0), (127, -400, 90, 24, 2))):
        z += dz
        place(b, "mobilier", "barriere_chantier", (x, 0, z), yaw=yaw, group=f"Incident/Barriere{i}", emprise=(L, 2, 5),
              longueur=L, variant=v)
    for i, (x, z) in enumerate(((-92, -443), (94, -442))):
        z += dz
        place(b, "mobilier", "cones", (x, 0, z), group=f"Incident/Cones{i}", emprise=(9, 2, 3), variant=1)


# ---------------------------------------------------------------------------
# Mobilier de rue
# ---------------------------------------------------------------------------

def mobilier_rue(b: Builder) -> None:
    """Poteaux électriques et câbles (rue commerçante), feux, distributeurs, vélos, lampadaires, arbres, garde-corps."""
    # --- poteaux et câbles (le long des trottoirs, jamais en travers du couloir) ---
    poteaux = {-1: (-22, -44, -66), 1: (-18, -42, -66, -108, -132)}
    for s, zs in poteaux.items():
        cote = "G" if s < 0 else "D"
        accs = []
        for i, z in enumerate(zs):
            x = xt(s, 4.6)
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
    for i, (s, z, v) in enumerate(((-1, zr1 - 1.5, 0), (1, zr1 - 1.5, 0), (-1, zr0 + 1.5, 1), (1, zr0 + 1.5, 1))):
        x = xt(s, 1.5)
        reserver(s, z - 1, z + 1, f"feu {z}")
        place(b, "mobilier", "feu_tricolore", (x, 0, z), yaw=face_couloir(x), group=f"Rue/Feux/F{i}", emprise=(2, 7, 14), variant=v,
              bras=7.0)
    # --- distributeurs, vélos, poubelles, panneaux (dos aux façades) ---
    objets = [
        # (fonction, côté, distance à la façade, z, longueur occupée le long du trottoir, paramètres)
        ("distributeurs", -1, 1.75, -50, 7, {"nombre": 2, "variant": 0}),
        ("distributeurs", 1, 1.75, -48, 7, {"nombre": 2, "variant": 1}),
        ("distributeurs", 1, 1.75, -122, 10, {"nombre": 3, "variant": 2}),
        ("distributeurs", -1, 1.75, -232, 7, {"nombre": 2, "variant": 1}),
        ("distributeurs", 1, 1.75, -244, 10, {"nombre": 3, "variant": 0}),
        ("distributeurs", 1, 1.75, 20, 10, {"nombre": 3, "variant": 2}),
        ("velos", 1, 3.5, -27, 8, {"nombre": 4, "variant": 0}),
        ("velos", -1, 3.5, 22, 8, {"nombre": 4, "variant": 1}),
        ("velos", -1, 3.5, -30, 8, {"nombre": 3, "variant": 2}),
        ("poubelles_tri", -1, 1.7, -74, 7, {"variant": 0}),
        ("poubelles_tri", 1, 1.7, -60, 7, {"variant": 1}),
        ("panneau_route", 1, 1.5, -114, 2, {"variant": 0}),
        ("panneau_route", -1, 1.5, 14, 2, {"variant": 2}),
        ("panneau_route", -1, 1.5, -36, 2, {"variant": 1}),
        # quartier des tours : plus de mobilier à hauteur de piéton
        ("velos", -1, 3.5, -190, 6, {"nombre": 3, "variant": 0}),
        ("poubelles_tri", 1, 1.7, -223.5, 7, {"variant": 0}),
        ("poubelles_tri", -1, 1.7, -210, 7, {"variant": 1}),
    ]
    for i, (fn, s, d, z, L, kw) in enumerate(objets):
        reserver(s, z - L / 2, z + L / 2, f"{fn} {z}")
        x = xt(s, d)
        place(b, "mobilier", fn, (x, 0, z), yaw=face_couloir(x), group=f"Rue/Objets/{i:02d}_{fn}", emprise=(L, 3, 6), **kw)
    # --- quartier des tours : lampadaires, arbres, garde-corps ---
    tours = {
        -1: [("arbre_rue", -160.5), ("lampadaire", -172), ("arbre_rue", -181), ("lampadaire", -200), ("lampadaire", -220),
             ("arbre_rue", -239), ("lampadaire", -248)],
        1: [("arbre_rue", -200), ("lampadaire", -208), ("arbre_rue", -215), ("lampadaire", -232), ("lampadaire", -252)],
    }
    for s, items in tours.items():
        cote = "G" if s < 0 else "D"
        for i, (fn, z) in enumerate(items):
            x = xt(s, 5 if fn == "lampadaire" else 4.0)
            reserver(s, z - 2, z + 2, f"{fn} {z}")
            kw = {"variant": i % 2} if fn == "lampadaire" else {"variant": (i + 2 * (s > 0)) % 3, "taille": 0.75}
            place(b, "mobilier", fn, (x, 0, z), yaw=face_couloir(x), group=f"Tours/Rue/{cote}{i}_{fn}", emprise=(4, 4, 14), **kw)
    # approche du carrefour : lampadaires devant l'immeuble à écrans et la tour cylindrique
    for i, (s, z) in enumerate(((-1, -318), (-1, -340), (1, -316), (1, -340))):
        x = xt(s, 5)
        reserver(s, z - 2, z + 2, f"lampadaire {z}")
        place(b, "mobilier", "lampadaire", (x, 0, z), yaw=face_couloir(x), group=f"Approche/Rue/{'G' if s < 0 else 'D'}{i}_lampadaire",
              emprise=(4, 4, 14), variant=2 if i % 2 else 0)
    for i, (s, z) in enumerate(((-1, -192), (-1, -230), (1, -224), (1, -244))):
        place(b, "mobilier", "glissiere", (s * (DEMI_COULOIR + 1.8), 0, z), yaw=90, group=f"Tours/Rue/Glissiere{i}",
              emprise=(12, 0.4, 3), longueur=12)


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
    POSES.clear()
    b = Builder(seed=seed)
    sols(b)
    skyline_lateral(b)
    entree(b)
    parvis_approche(b)
    passerelles(b)
    immeubles(b)
    carrefour(b)
    incident(b)
    mobilier_rue(b)
    reperes(b)
    decouper(b)
    return b


def _boite(p):
    """Boîte englobante (alignée sur les axes) d'une pièce ; exacte pour les cylindres et les boules."""
    R = np.asarray(p.rot).reshape(3, 3)
    size = np.asarray(p.size, float)
    if p.shape == "cyl":                     # axe = X local, Size = (longueur, diamètre, diamètre)
        a = R[:, 0]
        r = size[1] / 2
        half = np.abs(a) * size[0] / 2 + r * np.sqrt(np.clip(1.0 - a * a, 0.0, 1.0))
    elif p.shape == "ball":
        half = np.full(3, size[0] / 2)
    else:
        half = np.abs(R) @ (size / 2)
    return np.asarray(p.pos) - half, np.asarray(p.pos) + half


def couloir_libre(b: Builder) -> list:
    """Liste ce qui encombre le couloir de course au sol (pièces solides dans |x| < 45, 0,05 < y < 12)."""
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
    """Toute pièce (solide ou non) au-dessus de |x| < 46 et sous `y_min` : la caméra Roblox sauterait."""
    out = []
    for p in b.parts:
        if p.group.startswith(("Sol", "Reperes")):
            continue
        lo, hi = _boite(p)
        if lo[0] < X_LIBRE_HAUT - 0.01 and hi[0] > -X_LIBRE_HAUT + 0.01 and lo[1] < y_min and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name, round(lo[1], 1)))
    return out


# Contacts voulus entre assets posés (préfixes de groupes) : le train roule sur le viaduc.
CONTACTS_VOULUS = (("Monuments/Train", "Monuments/Viaduc"),)


def chevauchements(b: Builder, tol: float = 0.05) -> list:
    """Assets posés qui se traversent : pour chaque paire de poses dont les boîtes se recouvrent, compte les
    paires de pièces qui s'interpénètrent de plus de `tol` sur les trois axes (câbles et repères ignorés)."""
    boites = []
    for (g, n0, n1) in POSES:
        ps = [p for p in b.parts[n0:n1] if p.name != "Cable" and p.transparency < 0.99]
        if not ps:
            continue
        bx = [_boite(p) for p in ps]
        lo = np.array([v[0] for v in bx])
        hi = np.array([v[1] for v in bx])
        boites.append((g, ps, lo, hi, lo.min(0), hi.max(0)))
    out = []
    for i in range(len(boites)):
        gi, pi, loi, hii, Li, Hi = boites[i]
        for j in range(i + 1, len(boites)):
            gj, pj, loj, hij, Lj, Hj = boites[j]
            if np.any(np.minimum(Hi, Hj) - np.maximum(Li, Lj) <= tol):
                continue
            if any((gi.startswith(a) and gj.startswith(bb)) or (gi.startswith(bb) and gj.startswith(a))
                   for a, bb in CONTACTS_VOULUS):
                continue
            ov = np.minimum(hii[:, None, :], hij[None, :, :]) - np.maximum(loi[:, None, :], loj[None, :, :])
            m = np.all(ov > tol, axis=2)
            for a, bb in np.argwhere(m):          # cylindre vertical : distance réelle à l'axe (pas la boîte)
                for cy, (lo_o, hi_o) in ((pi[a], (loj[bb], hij[bb])), (pj[bb], (loi[a], hii[a]))):
                    if cy.shape == "cyl" and abs(np.asarray(cy.rot).reshape(3, 3)[1, 0]) > 0.999:
                        cx, cz = cy.pos[0], cy.pos[2]
                        dx = max(lo_o[0] - cx, 0.0, cx - hi_o[0])
                        dz = max(lo_o[2] - cz, 0.0, cz - hi_o[2])
                        if math.hypot(dx, dz) >= cy.size[1] / 2 - tol:
                            m[a, bb] = False
            if m.any():
                vol = np.where(m, np.prod(np.clip(ov, 0, None), axis=2), 0)
                a, bb = np.unravel_index(int(np.argmax(vol)), vol.shape)
                out.append((gi, gj, int(m.sum()), pi[a].name, pj[bb].name, round(float(vol[a, bb]), 2),
                            [round(float(v), 1) for v in np.maximum(loi[a], loj[bb])]))
    return out


def meta() -> dict:
    return {"nom": "ZoneVilleNuit", "version": VERSION, "largeur_couloir": 2 * DEMI_COULOIR,
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
        ch = chevauchements(b)
        print(f"chevauchements entre assets posés : {len(ch)}")
        for row in ch:
            print("   ", row)


if __name__ == "__main__":
    main()
