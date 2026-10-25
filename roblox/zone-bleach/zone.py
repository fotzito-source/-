#!/usr/bin/env python3
"""Plan de la zone Bleach (la cité blanche aux toits ocre) en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course (élargi) occupe x ∈ [-45, 45], bordé de trottoirs jusqu'à |x| = 55 ;
- on entre par la GRANDE PORTE blanche (mur d'enceinte de 64 studs, centré sur z = 0, ouverture de 100, vantaux
  enduits de blanc ouverts vers l'extérieur, presque perpendiculaires au mur) et on court vers -Z : le FAUBOURG de bois sombre et de tuiles grises sur une route de
  sable à grandes dalles (z -8 → -171), la PORTE INTÉRIEURE (tour-porte blanche en z = -176, passage de 92), la
  CITÉ BLANCHE entre de longs murs blancs de 14 à chaperon ocre (faces en |x| = 55), trois enclos par côté, tours
  blanches et passerelle laquée rouge au-dessus du couloir (z -181 → -388), la COUR DES ŒUFS pavée et fermée de
  murs blancs (centre z = -430), puis la COLLINE de la grande tour blanche et du monolithe, traversée par un
  tunnel de 96 (z -476 → -522) ;
- des remparts blancs ferment les côtés (|x| = 150) ; au-delà, la ville lointaine s'étend jusqu'à |x| = 210.

    python zone.py                     # écrit build/parts.json (aucune dépendance à Blender)
    python zone.py --stats             # nombre de pièces par groupe, budgets, couloir, chevauchements
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
from collections import defaultdict
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
DEMI_COULOIR = 45        # couloir de course vide : |x| < 45 (90 de large)
X_LIBRE = 46             # rien du tout au-dessus de |x| < 46 sous Y_LIBRE
X_BORD = 55              # bord des trottoirs = alignement des façades et des murs d'allée
EP_MUR = 2.4             # épaisseur des murs d'allée de la cité
X_MUR = X_BORD + EP_MUR / 2          # axe des murs d'allée (faces en 55 et 57,4)
X_ARRIERE_MUR = X_BORD + EP_MUR      # 57,4 : face arrière des murs d'allée
X_FRONT_CITE = 65.4      # façades des bâtiments de la cité (cour de 8 studs derrière les murs)
X_COUR = 92              # demi-largeur de la cour des œufs
X_ENCEINTE = 150         # axe des remparts latéraux
EP_REMPART = 3.0
X_FOND = 210             # fin de la ville lointaine
Z_APPROCHE = 64          # sol devant la grande porte (côté apparition)
Z_VANTAUX = 60           # bout des vantaux ouverts de la grande porte (≈ 102°, avant la fin de l'esplanade)
Z_PORTE = 0              # grande porte (mur centré sur z = 0, épaisseur 16)
EP_PORTE = 16
OUVERTURE_PORTE = 100    # passage de la grande porte (|x| < 50, plafond 56)
Z_FAUBOURG = -8          # début du faubourg (revers de la grande porte)
Z_RUE = -14              # première façade
Z_FIN_FAUBOURG = -166
Z_PORTE_INT = -176       # porte intérieure (mur centré, épaisseur 10)
EP_PORTE_INT = 10
OUVERTURE_PORTE_INT = 92  # passage de la porte intérieure (|x| < 46, hauteur 36)
Z_CITE = -181            # début de la cité blanche
Z_PASSERELLE = -286      # passerelle laquée au-dessus du couloir
PORTEE_PASSERELLE = 130  # tours de la passerelle en |x| 58..72, derrière les murs d'allée
Z_FIN_CITE = -388        # mur avant de la cour des œufs
Z_PLACE = -430           # centre de la place des œufs
R_PLACE = 34
Z_COLLINE = -476         # mur de soutènement de la colline (entrée du tunnel)
PROF_COLLINE = 46
PASSAGE_TUNNEL = 96      # tunnel de sortie : |x| < 48 libre jusqu'à y = 38
SOL_TUNNEL = 49          # demi-largeur du sol du tunnel posé ici (jusqu'au pied des murs du tunnel)
Z_SORTIE = Z_COLLINE - PROF_COLLINE   # -522 : sortie vers la zone suivante
H_GUIRLANDE = 40         # fil des guirlandes : les lampions restent au-dessus de 34 studs (caméra Roblox)
Y_LIBRE = 30             # rien au-dessus du couloir (|x| < X_LIBRE) sous cette hauteur

VERSION = "0.3"
H_MUR_ALLEE = 14         # murs d'allée de la cité (le chaperon monte vers 15,7)
H_MUR_TRANSVERSE = 15    # murs entre enclos : chaperon 1 plus haut que celui des murs d'allée (pas de faces coplanaires)
H_MUR_PLACE_AVANT = 16.5
H_MUR_PLACE_COTE = 16
LARGEUR_PORTAIL = 12     # portails d'enclos (demi-emprise 8 dans le mur d'allée)
X_CHEMIN_CITE = 14       # demi-largeur du chemin central de grandes dalles chaudes de la cité

# Budgets de pièces par asset (contrôlés par --stats). mur_blanc : 6 + longueur / 5 (arrondi au-dessus).
BUDGETS = {
    ("remparts", "grande_porte"): 850, ("remparts", "porte_interieure"): 420,
    ("remparts", "passerelle_rouge"): 330, ("remparts", "tour_blanche"): 65, ("remparts", "portail_cour"): 60,
    ("batiments", "maison_bois"): 140, ("batiments", "echoppe"): 45, ("batiments", "tour_guet_bois"): 80,
    ("batiments", "maison_blanche"): 150, ("batiments", "caserne"): 150, ("batiments", "pavillon"): 90,
    ("batiments", "quartier_lointain"): 32,
    ("vegetation", "cerisier"): 40, ("vegetation", "cerisier_geant"): 150, ("vegetation", "pin"): 40,
    ("vegetation", "massif_arbres"): 70, ("vegetation", "buisson"): 8, ("vegetation", "rocher"): 10,
    ("vegetation", "bassin_pont"): 80,
    ("colline", "colline_tour"): 1700,
}
BUDGET_SIMPLE = 70       # maison_bois / maison_blanche / caserne avec simple=True
BUDGET_MOBILIER = 40
PLAFOND = 13500          # pièces pour toute la zone
_COMPTES: list = []      # (module, fn, params, pièces, groupe) de chaque pose
_POSES: list = []        # (groupe complet, n0, n1, module, fn) : pour le contrôle des chevauchements


# ---------------------------------------------------------------------------
# Accès aux assets (avec bloc d'attente si un module manque encore)
# ---------------------------------------------------------------------------

def _asset(module: str, fn: str):
    try:
        return getattr(importlib.import_module(f"assets.{module}"), fn)
    except (ImportError, AttributeError):
        return None


def _budget(module: str, fn: str, params: dict) -> int:
    if module == "mobilier":
        return BUDGET_MOBILIER
    if fn == "mur_blanc":
        return int(math.ceil(6 + params.get("longueur", 32) / 5))
    if params.get("simple"):
        return BUDGET_SIMPLE
    return BUDGETS.get((module, fn), 10 ** 6)


def place(b: Builder, module: str, fn: str, pos, yaw: float = 0.0, group: str | None = None, emprise=(16, 16, 16),
          attente=None, **params) -> dict:
    """Pose un asset ; si le module n'existe pas encore, pose un bloc translucide de même emprise
    (ou la silhouette `attente(b)` pour les monuments qui enjambent le couloir)."""
    f = _asset(module, fn)
    with b.at(pos, yaw=yaw, group=group):
        n0 = len(b.parts)
        g = b._groups[-1]
        if f is not None:
            try:
                info = f(b, **params) or {}
                _COMPTES.append((module, fn, params, len(b.parts) - n0, group))
                _POSES.append((g, n0, len(b.parts), module, fn))
                return info
            except NotImplementedError:
                del b.parts[n0:]
        if attente is not None:
            attente(b)
            for p in b.parts[n0:]:
                p.name = f"ATTENTE_{module}_{fn}"
        else:
            w, d, h = emprise
            b.box((-w / 2, 0, -d / 2), (w / 2, h, d / 2), "#ff4fd8", transparency=0.5, name=f"ATTENTE_{module}_{fn}")
        _POSES.append((g, n0, len(b.parts), module, fn))
        return {"emprise": tuple(emprise[:2]), "hauteur": emprise[2]}


def face_couloir(x: float) -> float:
    """Rotation qui tourne l'avant d'un asset (-Z local) vers le couloir."""
    return -90.0 if x < 0 else 90.0


def _portique(ouverture: float, y_libre: float, x_ext: float, prof: float, h: float, mur: float = 0.0, h_mur: float = 0.0):
    """Silhouette d'attente d'un monument qui enjambe le couloir : deux piles, un linteau au-dessus de
    `y_libre`, et éventuellement un mur jusqu'à |x| = mur."""
    def dessin(b):
        rose = "#ff4fd8"
        for s in (-1, 1):
            xa, xb = sorted((s * ouverture / 2, s * x_ext))
            b.box((xa, 0, -prof / 2), (xb, h, prof / 2), rose, transparency=0.5)
            if mur > x_ext:
                xa, xb = sorted((s * x_ext, s * mur))
                b.box((xa, 0, -prof / 4), (xb, h_mur, prof / 4), rose, transparency=0.6)
        b.box((-ouverture / 2, y_libre, -prof / 2), (ouverture / 2, h, prof / 2), rose, transparency=0.5)
    return dessin


def _attente_passerelle(portee: float, hauteur: float):
    def dessin(b):
        rose = "#ff4fd8"
        for s in (-1, 1):
            b.box((s * portee / 2 - 7, 0, -7), (s * portee / 2 + 7, hauteur + 20, 7), rose, transparency=0.5)
        b.box((-portee / 2, hauteur, -3), (portee / 2, hauteur + 9, 3), rose, transparency=0.5)
    return dessin


def _attente_colline(passage: float, largeur: float, prof: float, h: float):
    def dessin(b):
        rose = "#ff4fd8"
        for s in (-1, 1):
            xa, xb = sorted((s * (passage / 2 + 2), s * largeur / 2))
            b.box((xa, 0, -prof), (xb, h, 0), rose, transparency=0.5)
        b.box((-passage / 2 - 2, 38, -prof), (passage / 2 + 2, h, 0), rose, transparency=0.5)
    return dessin


# ---------------------------------------------------------------------------
# Sol « pixel »
# ---------------------------------------------------------------------------

def _bornes_cases(a: float, bz: float, pas: float) -> list:
    """Bornes des cases de `a` à `bz` par pas de `pas` ; la dernière case est raccourcie si besoin."""
    n = max(1, int(math.ceil((bz - a) / pas - 1e-6)))
    return [a + i * pas for i in range(n)] + [bz]


def sol_pixel(b: Builder, x0: float, x1: float, z0: float, z1: float, cell, couleur, y_haut: float = 0.0,
              epaisseur: float = 1.0, studs="top", name: str = "Sol", **kw) -> int:
    """Remplit [x0, x1] × [z0, z1] ; couleur(x, z) → (r, g, b) évaluée au centre de chaque case, cases fusionnées.
    `cell` = pas commun ou (pas x, pas z) ; la dernière case de chaque rangée est raccourcie si l'étendue n'est
    pas un multiple du pas. Une case dont la couleur vaut None reste vide."""
    if x1 - x0 <= 0 or z1 - z0 <= 0:
        return 0
    cx, cz = cell if isinstance(cell, tuple) else (cell, cell)
    xs, zs = _bornes_cases(x0, x1, cx), _bornes_cases(z0, z1, cz)
    nx, nz = len(xs) - 1, len(zs) - 1
    grid = np.empty((nz, nx), dtype=object)
    for j in range(nz):
        for i in range(nx):
            v = couleur((xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2)
            grid[j, i] = None if v is None else tuple(v)
    n = 0
    for col in {v for v in grid.reshape(-1) if v is not None}:
        mask = np.vectorize(lambda v, col=col: v == col)(grid)
        for (i, j, w, h) in mask_rects(mask):
            b.box((xs[i], y_haut - epaisseur, zs[j]), (xs[i + w], y_haut, zs[j + h]), col, studs=studs, name=name, **kw)
            n += 1
    return n


def _hash(*k) -> float:
    """Bruit déterministe dans [0, 1) à partir d'entiers."""
    h = 2166136261
    for v in k:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return (h % 10007) / 10007


def mosaique_place(x: float, z: float):
    """Place des œufs : fleur de cerisier stylisée à cinq pétales échancrés (un pétale pointe vers -Z, « vers le
    haut » pour le joueur qui arrive), anneaux de dallage, bordure sombre. None hors de la place."""
    dx, dz = x, z - Z_PLACE
    d = math.hypot(dx, dz)
    if d >= R_PLACE:
        return None
    if d >= R_PLACE - 2:
        return c("bordure")
    if d >= R_PLACE - 4:
        return c("pierre_claire")
    if d < 2.5:
        return c("or")
    if d < 5:
        return c("sakura_fonce")
    th = math.degrees(math.atan2(dz, dx))
    phi = ((th + 90 + 36) % 72) - 36              # 0 sur l'axe d'un pétale
    rp = 5 + 14.5 * max(0.0, 1 - (abs(phi) / 33) ** 1.8)
    encoche = abs(phi) < 7 and d > rp - 4.5 + abs(phi) * 0.45
    if d < rp and not encoche:
        return c("sakura_vif") if d > rp - 2.5 else c("sakura")
    if 21.5 <= d < 23.5:
        return c("ocre")
    return c("dallage")


X_CHEMIN = 15            # demi-largeur du chemin de grandes dalles du faubourg


def _sable(x: float, z: float):
    """Route de sable du faubourg : grandes plaques de teintes voisines, deux paires d'ornières plus foncées."""
    ax = abs(x)
    if 22 <= ax < 24 or 30 <= ax < 32:
        return c("sable_fonce")
    v = _hash(math.floor(x / 8), math.floor(z / 12))
    return c("sable_clair") if v < 0.22 else (c("sable") if v < 0.8 else shade(c("sable"), 0.96))


def _chemin_dalles(x: float, z: float):
    """Chemin central de grandes dalles posées sur le sable (|x| < X_CHEMIN), rangs de 6 studs séparés de 1 stud
    de sable, chaque rang coupé en deux, trois ou quatre dalles."""
    ax = abs(x)
    if ax >= X_CHEMIN:
        return _sable(x, z)
    rang = math.floor(z / 7)
    if z - rang * 7 < 1 or ax >= X_CHEMIN - 0.5:
        return c("sable_fonce")
    coupe = ((0.5,), (-5.5, 4.5), (-7.5, -0.5, 6.5), (-3.5, 5.5))[int(_hash(rang, 3) * 4)]
    if any(abs(x - k) < 0.5 for k in coupe):
        return c("sable_fonce")
    piece = sum(1 for k in coupe if x > k)
    return c("dalle_chemin") if _hash(rang, piece, 7) < 0.6 else c("dalle_chemin_fonce")


def _dallage_cite(x: float, z: float):
    """Dallage de la cité : chemin central de grandes dalles chaudes (|x| < 14, rangs de 8 coupés en deux,
    écho clair du chemin du faubourg) bordé d'un liseré ocre ; de part et d'autre, grandes dalles de
    18 × 8 en appareil décalé, deux blancs chauds bien distincts ; un joint sombre traverse toute l'allée tous
    les 24 studs (repère de vitesse) ; caniveau de pierre foncée de 2 studs au bord du couloir."""
    ax = abs(x)
    if ax >= DEMI_COULOIR - 2:
        return c("pierre_fonce")
    if (z - Z_CITE) % 24 >= 23:
        return c("bordure")
    rang = math.floor(z / 8)
    if ax < X_CHEMIN_CITE:
        coupe = 3.5 if rang % 2 else -3.5
        piece = int(x > coupe)
        return c("dalle_cite") if _hash(rang, piece, 11) < 0.55 else c("dalle_cite_fonce")
    if ax < X_CHEMIN_CITE + 1:
        return c("ocre_fonce")
    k = math.floor((x + 9 + (9 if rang % 2 else 0)) / 18)
    return c("dallage") if (k + rang) % 2 == 0 else c("dallage_ombre")


def _dallage_cour(x: float, z: float):
    """Cour des œufs autour de la mosaïque : bandes de dalles alternées, cadre carré de pierre sombre autour de
    la place (côté 80) et croix de dalles claires dans les axes de la place, jusqu'aux murs."""
    dz = z - Z_PLACE
    if (abs(x) < 1 or abs(dz) < 1) and math.hypot(x, dz) >= R_PLACE:
        return c("pierre_claire")
    if 38 <= max(abs(x), abs(dz)) < 40:
        return c("bordure")
    return c("dallage") if math.floor(z / 8) % 2 else c("dallage_ombre")


def sol_couloir(b: Builder) -> None:
    pc, pf = c("pierre_claire"), c("pierre_fonce")

    def seuil(x, z):
        return pf if math.floor(z / 4) % 2 else shade(pf, 0.94)

    def approche(x, z):
        return c("dallage") if (math.floor((x + 9) / 18) + math.floor((z - 8) / 14)) % 2 == 0 else pc

    def cour(x, z):
        m = mosaique_place(x, z)
        if m:
            return m
        return _dallage_cour(x, z)

    def tunnel(x, z):
        return pf if math.floor(z / 8) % 2 else shade(pf, 0.9)

    D = DEMI_COULOIR
    with b.group("Sol/Couloir"):
        sol_pixel(b, -D, D, EP_PORTE / 2, Z_APPROCHE, (9, 7), approche, name="Approche")
        sol_pixel(b, -D, D, Z_FAUBOURG, EP_PORTE / 2, (D, 4), seuil, name="Seuil")
        sol_pixel(b, -X_CHEMIN, X_CHEMIN, Z_FIN_FAUBOURG, Z_FAUBOURG, 1, _chemin_dalles, name="Chemin")
        for s in (-1, 1):
            xa, xb = sorted((s * X_CHEMIN, s * D))
            sol_pixel(b, xa, xb, Z_FIN_FAUBOURG, Z_FAUBOURG, (2, 4), _sable, name="Sable")
        sol_pixel(b, -D, D, Z_CITE, Z_FIN_FAUBOURG, (D, 1), seuil, name="Seuil")
        sol_pixel(b, -D, D, Z_FIN_CITE, Z_CITE, 1, _dallage_cite, name="Dallage")
        sol_pixel(b, -D, D, Z_COLLINE, Z_FIN_CITE, 2, cour, name="Cour")
        # tout le passage du tunnel, jusqu'au pied de ses murs ; s'arrête net sur la sortie (z = -522)
        sol_pixel(b, -SOL_TUNNEL, SOL_TUNNEL, Z_SORTIE, Z_COLLINE, (SOL_TUNNEL, 4), tunnel, name="Tunnel")


def sol_trottoirs(b: Builder) -> None:
    pf = c("pierre_fonce")

    def trottoir(x, z):
        m = mosaique_place(x, z)
        if m:
            return m
        ax = abs(x)
        bord = ax < DEMI_COULOIR + 1
        if z > EP_PORTE / 2:                                    # approche
            return c("pierre") if bord else c("pierre_claire")
        if z > Z_FAUBOURG:
            return pf
        if z > Z_FIN_FAUBOURG:                                  # faubourg : bordure de pierre, terre battue
            if bord:
                return c("pierre")
            return c("terre") if math.floor(z / 16) % 2 else shade(c("terre"), 1.06)
        if z > Z_CITE:
            return pf
        if z > Z_FIN_CITE:                                      # cité : caniveau, dalles alternées
            if bord:
                return pf
            return c("pierre_claire") if math.floor(z / 6) % 2 else c("dallage_ombre")
        return _dallage_cour(x, z)                              # cour des œufs

    with b.group("Sol/Trottoirs"):
        for s in (-1, 1):
            xa, xb = sorted((s * DEMI_COULOIR, s * X_BORD))
            sol_pixel(b, xa, xb, Z_COLLINE, Z_APPROCHE, 2, trottoir)


# --- faubourg : rangées, ruelle de service, seconde rangée, jardins -----------------------------------------
X_SERVICE = (74, 82)     # ruelle de service derrière la première rangée
X_ARRIERE_F = 90         # axe de la seconde rangée du faubourg (maisons de 16 de profondeur : 82..98)
POTAGERS = ((-28, -66), (-86, -124))
X_POTAGER = (108, 142)


def _potager(ax: float, z: float):
    """Jardins potagers derrière le faubourg : planches de terre sombre et rangs de légumes."""
    for (za, zb) in POTAGERS:
        if X_POTAGER[0] <= ax < X_POTAGER[1] and zb <= z < za:
            return c("culture") if math.floor(z / 2) % 3 == 0 else c("terre_fonce")
    return None


# (x0, x1, z0, z1) : pelouses sous les grands arbres des enclos de la cité
PELOUSES = ((-134, -96, -318, -278), (94, 128, -290, -250), (-122, -98, -347, -333), (114, 136, -328, -304),
            (86, 104, -245, -229), (-138, -118, -280, -260))


def sol_cotes(b: Builder) -> None:
    """Sol entre les trottoirs et les remparts : sable et ruelle au faubourg, potagers, gravier blanc ratissé dans
    les enclos de la cité (allées de pierre vers les portails, quelques pelouses), cour pavée et jardins autour
    de la place."""
    portes = {-1: CITE[-1]["portes"], 1: CITE[1]["portes"]}

    def couleur(x, z):
        ax, s = abs(x), (-1 if x < 0 else 1)
        m = mosaique_place(x, z)
        if m:
            return m
        if z > Z_FAUBOURG:                                     # revers de la grande porte
            return c("pierre_fonce")
        if z > Z_PORTE_INT + EP_PORTE_INT / 2:                  # faubourg
            pot = _potager(ax, z)
            if pot:
                return pot
            if X_SERVICE[0] <= ax < X_SERVICE[1]:               # ruelle de service
                return c("terre")
            if ax >= 104:
                return c("herbe") if (math.floor(x / 24) + math.floor(z / 24)) % 2 == 0 else c("herbe_fonce")
            return c("sable_fonce") if ax < X_SERVICE[0] else shade(c("sable_fonce"), 1.05)
        if z > Z_CITE:
            return c("pierre_fonce")
        if z > Z_FIN_CITE:                                      # enclos de la cité
            for zg in portes[s]:
                if abs(z - zg) < 2.5 and ax < X_FRONT_CITE + 1:
                    return c("pierre_claire")
            if ax < X_FRONT_CITE + 20:
                return c("gravier") if math.floor(z / 6) % 2 else c("gravier_ombre")
            for (xa, xb, za, zb) in PELOUSES:
                if xa <= x < xb and za <= z < zb:
                    return c("herbe")
            return c("gravier_ombre")
        if ax < X_COUR:                                         # cour des œufs
            return _dallage_cour(x, z)
        return c("herbe") if (math.floor(x / 24) + math.floor(z / 22)) % 2 == 0 else c("herbe_claire")

    with b.group("Sol/Cotes"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * (X_ENCEINTE + EP_REMPART / 2)))
            sol_pixel(b, xa, xb, Z_COLLINE, EP_PORTE / 2, 2, couleur)

    def abords(x, z):
        ax = abs(x)
        if ax < 95:                                             # parvis dallé devant la porte
            return c("pierre_claire") if (math.floor(ax / 8) + math.floor(z / 8)) % 2 == 0 else c("dallage")
        return c("herbe") if (math.floor(x / 24) + math.floor(z / 24)) % 2 == 0 else c("herbe_fonce")

    with b.group("Sol/Abords"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_FOND))
            sol_pixel(b, xa, xb, EP_PORTE / 2, Z_APPROCHE, 8, abords)
    with b.group("Sol/Lointain"):
        for s in (-1, 1):
            xa, xb = sorted((s * (X_ENCEINTE + EP_REMPART / 2), s * X_FOND))
            sol_pixel(b, xa, xb, Z_COLLINE, EP_PORTE / 2, 4,
                      lambda x, z: c("gravier_ombre") if math.floor(z / 40) % 2 else c("pierre_claire"))


# ---------------------------------------------------------------------------
# Enceinte : remparts latéraux, tours, ville lointaine
# ---------------------------------------------------------------------------

TOURS_REMPART = (-90, -230, -370)


def _troncons(z_haut: float, z_bas: float, trous, long_max: float = 48):
    """Découpe [z_bas, z_haut] en tronçons de mur ≤ long_max en sautant les intervalles `trous` [(za, zb)]."""
    bornes = [(z_haut, z_bas)]
    for (ta, tb) in sorted(trous, key=lambda t: -max(t)):
        hi, lo = max(ta, tb), min(ta, tb)
        nouv = []
        for (a, bz) in bornes:
            if lo >= a or hi <= bz:
                nouv.append((a, bz))
                continue
            if a > hi:
                nouv.append((a, hi))
            if lo > bz:
                nouv.append((lo, bz))
        bornes = nouv
    out = []
    for (a, bz) in bornes:
        L = a - bz
        n = max(1, math.ceil(L / long_max - 1e-6))
        for k in range(n):
            out.append((a - k * L / n, a - (k + 1) * L / n))
    return out


def mur(b: Builder, group: str, x: float, za: float, zb: float, **params) -> None:
    """Mur blanc le long de Z (de za à zb) en x, avant tourné vers le couloir."""
    L = abs(za - zb)
    place(b, "remparts", "mur_blanc", (x, 0, (za + zb) / 2), yaw=face_couloir(x), group=group,
          emprise=(L, params.get("epaisseur", EP_MUR), params.get("hauteur", 10)), longueur=round(L, 2), **params)


Z_DEBUT_REMPART = -10.8  # dos des tours d'angle de la grande porte


def enceinte(b: Builder) -> None:
    """Remparts blancs latéraux (28 studs, chaperon ocre, meurtrières) et tours blanches."""
    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        x = s * X_ENCEINTE
        trous = [(zt + 7, zt - 7) for zt in TOURS_REMPART]
        # le dernier tronçon s'arrête sur la face avant de l'appui de la colline (z = Z_COLLINE + 0,2)
        for i, (za, zb) in enumerate(_troncons(Z_DEBUT_REMPART, Z_COLLINE + 0.2, trous)):
            mur(b, f"Enceinte/{cote}/Mur{i:02d}", x, za, zb, hauteur=28, epaisseur=EP_REMPART, meurtrieres=True, variant=1)
        for i, zt in enumerate(TOURS_REMPART):
            place(b, "remparts", "tour_blanche", (x, 0, zt), yaw=face_couloir(x), group=f"Enceinte/{cote}/Tour{i}",
                  emprise=(14, 14, 46), hauteur=46, cote=14, variant=(i + (s > 0)) % 4)


def ville_lointaine(b: Builder) -> None:
    """Enclos blancs à toits ocre derrière les remparts (vus d'avion et de côté) : la ville paraît immense."""
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        for i, z in enumerate((-60, -150, -240, -330, -420)):
            place(b, "batiments", "quartier_lointain", (s * 182, 0, z), yaw=face_couloir(s), group=f"Lointain/{cote}{i}",
                  emprise=(56, 48, 14), largeur=56, profondeur=48, variant=i + (s > 0))


# ---------------------------------------------------------------------------
# Approche et faubourg
# ---------------------------------------------------------------------------

# (largeur, profondeur, variante, ruelle après, contenu de la ruelle) ; les rangées commencent en z_depart.
# Contenu : échoppe sur le trottoir, puits, seaux d'incendie, bannières ; « +tour » ajoute une tour de guet
# au fond de la ruelle (ruelles de 11).
# Les rangées s'arrêtent vers z = -129 : devant la porte intérieure s'ouvre une petite place plantée de cerisiers,
# visibles depuis la rue (les vantaux de la porte intérieure, ouverts côté faubourg, cacheraient des arbres plus
# proches de la porte).
FAUBOURG = {
    -1: (Z_RUE, [(22, 16, 0, 10, "echoppe"), (20, 16, 1, 8, "puits"), (24, 18, 2, 11, "echoppe+tour"),
                 (18, 16, 3, 0, "seaux")]),
    1: (Z_RUE - 2, [(24, 18, 1, 10, "echoppe"), (20, 16, 2, 11, "nobori+tour"), (20, 16, 3, 10, "echoppe"),
                    (18, 16, 0, 0, "puits")]),
}
# seconde rangée (simplifiée), tournée vers le couloir : (côté, z, largeur, variante)
FAUBOURG_ARRIERE = ((-1, -36, 20, 2), (-1, -92, 20, 0), (-1, -124, 22, 5), (-1, -152, 18, 3),
                    (1, -32, 20, 1), (1, -64, 20, 4), (1, -104, 22, 3), (1, -140, 22, 2))


def approche(b: Builder) -> None:
    """Esplanade devant la grande porte : lanternes, cerisiers, pins et massifs. Les vantaux blancs ouverts à
    ≈ 102° bordent l'esplanade (|x| ≈ 50 à 63, z ≈ 9 à 59) : lanternes et buissons entre le couloir et les
    vantaux, cerisiers au-delà."""
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        for i, z in enumerate((56, 24)):
            x = s * 50
            place(b, "mobilier", "lanterne_pierre", (x, 0, z), yaw=face_couloir(x), group=f"Abords/Lanterne{cote}{i}",
                  variant=i, emprise=(3.4, 3.4, 7))
        for i, (dx, z, v, t) in enumerate(((78, 48, 0, 1.1), (100, 56, 1, 1.1), (112, 24, 2, 1.0), (134, 46, 3, 0.9))):
            place(b, "vegetation", "cerisier", (s * dx, 0, z), yaw=i * 50, group=f"Abords/Cerisier{cote}{i}",
                  variant=v + (s > 0), taille=t, emprise=(14, 14, 16))
        place(b, "vegetation", "massif_arbres", (s * 168, 0, 40), group=f"Abords/Massif{cote}", variant=int(s > 0),
              emprise=(28, 20, 16), largeur=28, profondeur=20)
        place(b, "vegetation", "pin", (s * 198, 0, 22), group=f"Abords/Pin{cote}", variant=1 + (s > 0), emprise=(10, 10, 16))
        for i, (dx, z) in enumerate(((122, 12), (150, 58))):
            place(b, "vegetation", "rocher", (s * dx, 0, z), yaw=i * 40, group=f"Abords/Rocher{cote}{i}", variant=i + (s > 0),
                  taille=1.0 + 0.3 * i, emprise=(5, 5, 3))
        for i, z in enumerate((48, 32)):
            place(b, "vegetation", "buisson", (s * 52, 0, z), group=f"Abords/Buisson{cote}{i}", variant=i, emprise=(2.6, 2.6, 2.4))


def faubourg(b: Builder) -> dict:
    """Rangées de maisons de bois à étage le long du couloir ; ruelles avec échoppes, puits, tours de guet."""
    ruelles = {}
    for s, (z0, plan) in FAUBOURG.items():
        cote = "Gauche" if s < 0 else "Droite"
        z = z0
        ruelles[s] = []
        for i, (larg, prof, v, apres, quoi) in enumerate(plan):
            zc = z - larg / 2
            x = s * (X_BORD + prof / 2)
            place(b, "batiments", "maison_bois", (x, 0, zc), yaw=face_couloir(x), group=f"Faubourg/{cote}/{i:02d}_MaisonBois",
                  emprise=(larg, prof, 20), largeur=larg, profondeur=prof, variant=v)
            z -= larg
            if quoi:
                ruelles[s].append((z - (apres or 9) / 2, quoi))
            z -= apres
        assert z > Z_FIN_FAUBOURG, f"rangée du faubourg trop longue ({z})"
    # ruelles : échoppes, puits, seaux, bannières ; tours de guet au fond de certaines ruelles
    nt = 0
    for s, lst in ruelles.items():
        cote = "G" if s < 0 else "D"
        for i, (zr, quoi) in enumerate(lst):
            g = f"Faubourg/Ruelles/{cote}{i}"
            kind = quoi.split("+")[0]
            if kind == "echoppe":
                x = s * (X_BORD + 2.6)
                place(b, "batiments", "echoppe", (x, 0, zr), yaw=face_couloir(x), group=g, emprise=(8, 5, 8), variant=i + (s > 0))
            elif kind == "puits":
                place(b, "mobilier", "puits", (s * 60, 0, zr), yaw=face_couloir(s), group=g, variant=0, emprise=(4.8, 4.4, 8.4))
            elif kind == "seaux":
                place(b, "mobilier", "seaux_incendie", (s * 58.5, 0, zr), yaw=face_couloir(s), group=g, variant=0, emprise=(6.5, 2.4, 4.5))
            elif kind == "nobori":
                for k, dz in enumerate((-2.5, 2.5)):
                    place(b, "mobilier", "nobori", (s * 57, 0, zr + dz), yaw=face_couloir(s), group=f"{g}/{k}",
                          texte=("団子", "甘味")[k], variant=k, emprise=(1.4, 2.7, 9.6))
            if quoi.endswith("+tour"):
                x = s * 66
                place(b, "batiments", "tour_guet_bois", (x, 0, zr), yaw=face_couloir(x), group=f"Faubourg/TourGuet{nt}",
                      emprise=(7, 7, 30), hauteur=30 + 2 * nt, variant=nt)
                nt += 1
    # troisième tour de guet : dans la ruelle de service, dans l'axe d'une ruelle à puits (vue depuis la rue)
    zr = ruelles[-1][1][0]
    x = -sum(X_SERVICE) / 2
    place(b, "batiments", "tour_guet_bois", (x, 0, zr), yaw=face_couloir(x), group=f"Faubourg/TourGuet{nt}",
          emprise=(7, 7, 34), hauteur=34, variant=2)
    # seconde rangée (simplifiée), tournée vers le couloir
    for i, (s, z, larg, v) in enumerate(FAUBOURG_ARRIERE):
        x = s * X_ARRIERE_F
        place(b, "batiments", "maison_bois", (x, 0, z), yaw=face_couloir(x), group=f"Faubourg/Arriere/{i:02d}_MaisonBois",
              emprise=(larg, 16, 18), largeur=larg, profondeur=16, variant=v, simple=True)
    # arbres du faubourg : sur la petite place devant la porte intérieure, deux cerisiers géants qui encadrent la
    # porte et dépassent des toits (vus de toute la rue, et dès l'entrée par l'ouverture de la grande porte) ;
    # deux autres cerisiers géants entre les potagers, et des cerisiers plus grands dans les jardins
    for i, (x, z, kind, v, t) in enumerate(((-65, -154, "cerisier_geant", 0, 0.95), (65, -153, "cerisier_geant", 3, 0.95),
                                            (-120, -76, "cerisier_geant", 0, 1.25), (114, -18, "cerisier", 3, 1.3),
                                            (116, -152, "cerisier", 0, 1.35), (-130, -16, "pin", 0, 1.0),
                                            (120, -76, "cerisier_geant", 1, 1.25), (-128, -150, "massif_arbres", 0, 1.0),
                                            (-114, -136, "cerisier", 4, 1.3), (112, -128, "cerisier", 1, 1.3))):
        kw = {"largeur": 26, "profondeur": 18} if kind == "massif_arbres" else {"taille": t}
        place(b, "vegetation", kind, (x, 0, z), yaw=(i * 37) % 360, group=f"Faubourg/Arbres/{i:02d}_{kind}",
              variant=v, emprise=(14, 14, 16), **kw)
    return ruelles


X_PROPS = 51             # objets du trottoir du faubourg


def details_faubourg(b: Builder) -> None:
    """Objets du trottoir et guirlandes de lampions au-dessus de la rue."""
    props = {
        -1: [(-22, "nobori", {"texte": "茶"}), (-31, "panneau", {"texte": "団子"}), (-58, "tonneaux", {}), (-80, "etal", {}),
             (-88, "sacs_riz", {}), (-112, "lanterne_poteau", {}), (-130, "nobori", {"texte": "宿"}), (-140, "caisses", {})],
        1: [(-24, "lanterne_poteau", {}), (-34, "nobori", {"texte": "米"}), (-60, "etal", {}), (-84, "caisses", {}),
            (-92, "panneau", {"texte": "蕎麦"}), (-114, "tonneaux", {}), (-128, "charrette", {"yaw": 180}), (-142, "nobori", {"texte": "薬"})],
    }
    for s, lst in props.items():
        cote = "G" if s < 0 else "D"
        for k, (z, fn, kw) in enumerate(lst):
            x = s * X_PROPS
            kw = dict(kw)
            yaw = kw.pop("yaw", face_couloir(x))
            place(b, "mobilier", fn, (x, 0, z), yaw=yaw, group=f"Faubourg/Details/{cote}{k:02d}_{fn}",
                  variant=k % 3, emprise=(3, 3, 4), **kw)
    # la dernière guirlande reste devant les vantaux de la porte intérieure (ouverts côté faubourg jusqu'à -146,65)
    _guirlandes(b, "Faubourg/Guirlandes", (-46, -96, -144), variant_mat=0, variants=(0, 1))


X_MAT = 49.5             # mâts des guirlandes (sur le trottoir) ; potence vers le couloir


def _guirlandes(b: Builder, group: str, zs, variant_mat: int, variants, n: int = 13) -> None:
    fmat = _asset("mobilier", "mat_guirlande")
    fgui = _asset("mobilier", "guirlande_lampions")
    bras = 2.4
    for i, z in enumerate(zs):
        with b.group(f"{group}/G{i}"):
            for s in (-1, 1):
                x = s * X_MAT
                place(b, "mobilier", "mat_guirlande", (x, 0, z), yaw=face_couloir(x), group=f"Mat{'G' if s < 0 else 'D'}",
                      variant=variant_mat, hauteur=H_GUIRLANDE, bras=bras, emprise=(2, 2, H_GUIRLANDE + 3))
            if fmat and fgui:
                xa = X_MAT - bras
                fgui(b, (-xa, H_GUIRLANDE, z), (xa, H_GUIRLANDE, z), n=n, creux=3.0, variant=variants[i % len(variants)])


# ---------------------------------------------------------------------------
# Cité blanche
# ---------------------------------------------------------------------------

# Bâtiments face au couloir : seulement des maisons blanches à étage (v1, v4 : un étage entier et le toit ocre
# dépassent des murs d'allée de 14) et un hall à toit bleu (v2) par côté. Tours d'allée en |x| = 64, juste
# derrière les murs, pour rythmer les deux longues lignes de murs.
CITE = {  # par côté : portails des trois enclos, bâtiments, arbres, tours
    -1: {"portes": (-213, -262, -358),
         "batiments": [("maison_blanche", -213, 24, 18, 4), ("maison_blanche", -262, 24, 18, 2),
                       ("maison_blanche", -358, 30, 18, 1)],
         "arriere": [("caserne", 116, -214, 40, 14, 1), ("maison_blanche", 110, -360, 24, 18, 3)],
         "cerisiers": [(-69, -192, 0, 1.45), (-69, -235.5, 1, 1.3), (-128, -270, 2, 1.2), (-86, -381, 3, 0.85),
                       (-110, -340, 0, 1.1), (-72, -319, 4, 1.35)],
         "geant": (-115, -298),
         "tours": [(-134, -196, 44, 0), (-130, -372, 46, 2), (-96, -236, 40, 1), (-64, -302, 36, 3)],
         "ajouts": [("maison_blanche", -110, -262, 24, 18, 4)],
         "jardin": ("bassin_pont", -84, -314)},
    1: {"portes": (-222, -312, -354),
        "batiments": [("maison_blanche", -222, 24, 18, 1), ("maison_blanche", -312, 24, 18, 2),
                      ("maison_blanche", -354, 30, 18, 4)],
        "arriere": [("caserne", 116, -222, 40, 14, 0), ("maison_blanche", 110, -354, 24, 18, 1)],
        "cerisiers": [(69, -197, 2, 1.45), (86, -265, 1, 1.3), (90, -236, 0, 1.0), (86, -381, 1, 0.85),
                      (124, -316, 2, 1.2), (66, -381, 3, 0.85)],
        "geant": (110, -268),
        "tours": [(134, -196, 46, 3), (130, -372, 44, 0), (94, -194, 40, 2), (64, -258, 36, 0)],
        "ajouts": [("maison_blanche", 100, -312, 24, 18, 0)],
        "jardin": None},
}
Z_MURS_TRANSVERSES = (-246, -330)
LANTERNES_CITE = (-198, -240, -272, -300, -338, -378)
X_LANTERNE_CITE = 52.5


def cite(b: Builder) -> None:
    """Allée entre deux longs murs blancs à chaperon ocre ; derrière, trois enclos par côté (portail, bâtiment
    blanc à toit ocre face au couloir, cour de gravier blanc, cerisiers, tours blanches), passerelle laquée."""
    for s, cfg in CITE.items():
        cote = "Gauche" if s < 0 else "Droite"
        g = f"Cite/{cote}"
        # murs d'allée, interrompus par les portails
        dp = LARGEUR_PORTAIL / 2 + 2            # demi-emprise des portails dans le mur d'allée
        trous = [(zg + dp, zg - dp) for zg in cfg["portes"]]
        for i, (za, zb) in enumerate(_troncons(Z_CITE, Z_FIN_CITE, trous, long_max=32)):
            mur(b, f"{g}/MurAllee{i:02d}", s * X_MUR, za, zb, hauteur=H_MUR_ALLEE, epaisseur=EP_MUR, variant=i % 3)
        for i, zg in enumerate(cfg["portes"]):
            x = s * X_MUR
            place(b, "remparts", "portail_cour", (x, 0, zg), yaw=face_couloir(x), group=f"{g}/Portail{i}",
                  emprise=(2 * dp, 6, 21), largeur=LARGEUR_PORTAIL, hauteur=H_MUR_ALLEE + 4, h_mur=H_MUR_ALLEE,
                  texte=("静", "茶", "白", "宿", "門", None)[(i + 3 * (s > 0)) % 6], variant=i + (s > 0))
        # murs transverses entre enclos (de la face arrière des murs d'allée au rempart), 1 plus hauts que les
        # murs d'allée : plinthe et chaperon à d'autres niveaux (pas de scintillement)
        for i, zt in enumerate(Z_MURS_TRANSVERSES):
            xa, xb = X_ARRIERE_MUR, X_ENCEINTE - EP_REMPART / 2
            place(b, "remparts", "mur_blanc", (s * (xa + xb) / 2, 0, zt), yaw=0, group=f"{g}/MurTransverse{i}",
                  emprise=(xb - xa, EP_MUR, H_MUR_TRANSVERSE), longueur=round(xb - xa, 2), hauteur=H_MUR_TRANSVERSE,
                  epaisseur=EP_MUR, variant=2)
        # bâtiments face au couloir
        for i, (fn, zc, larg, prof, v) in enumerate(cfg["batiments"]):
            x = s * (X_FRONT_CITE + prof / 2)
            place(b, "batiments", fn, (x, 0, zc), yaw=face_couloir(x), group=f"{g}/{i:02d}_{fn}",
                  emprise=(larg, prof, 18), **({"largeur": larg} if fn == "maison_blanche" else {"longueur": larg}),
                  profondeur=prof, variant=v)
        for i, (fn, dx, zc, larg, prof, v) in enumerate(cfg["arriere"] + [(f, abs(x), z, l, pr, v)
                                                                        for (f, x, z, l, pr, v) in cfg["ajouts"]]):
            x = s * dx
            place(b, "batiments", fn, (x, 0, zc), yaw=face_couloir(x), group=f"{g}/Arriere{i}_{fn}",
                  emprise=(larg, prof, 16), **({"largeur": larg} if fn == "maison_blanche" else {"longueur": larg}),
                  profondeur=prof, variant=v, simple=True)
        for i, (x, z, h, v) in enumerate(cfg["tours"]):
            place(b, "remparts", "tour_blanche", (x, 0, z), yaw=face_couloir(x), group=f"{g}/Tour{i}",
                  emprise=(12, 12, h), hauteur=h, cote=12, variant=v)
        for i, (x, z, v, t) in enumerate(cfg["cerisiers"]):
            place(b, "vegetation", "cerisier", (x, 0, z), yaw=(i * 61) % 360, group=f"{g}/Cerisier{i}",
                  variant=v, taille=t, emprise=(13, 13, 16))
        gx, gz = cfg["geant"]
        place(b, "vegetation", "cerisier_geant", (gx, 0, gz), yaw=40 * (s > 0), group=f"{g}/CerisierGeant",
              variant=int(s > 0), emprise=(30, 30, 30))
        if cfg["jardin"]:
            kind, x, z = cfg["jardin"]
            place(b, "vegetation", kind, (x, 0, z), yaw=face_couloir(x), group=f"{g}/Jardin", emprise=(28, 18, 6),
                  largeur=28, profondeur=18, variant=0)
        for i, z in enumerate(LANTERNES_CITE):
            x = s * X_LANTERNE_CITE
            place(b, "mobilier", "lanterne_poteau", (x, 0, z), yaw=face_couloir(x), group=f"{g}/Lanterne{i}", variant=1,
                  hauteur=7.5, emprise=(2.1, 2.1, 11))
    # guirlandes blanches et rouges à l'entrée de la cité et devant la cour (mâts laqués), loin de la passerelle :
    # les deux ouvrages au-dessus de la rue ne se superposent jamais dans les vues d'aller et de retour
    _guirlandes(b, "Cite/Guirlandes", (-204, -372), variant_mat=1, variants=(2,))
    place(b, "remparts", "passerelle_rouge", (0, 0, Z_PASSERELLE), group="Cite/Passerelle", emprise=(148, 16, 63),
          attente=_attente_passerelle(PORTEE_PASSERELLE, 38), portee=PORTEE_PASSERELLE, hauteur=38)


# ---------------------------------------------------------------------------
# Cour des œufs
# ---------------------------------------------------------------------------

def cour_des_oeufs(b: Builder) -> None:
    """Grande cour pavée fermée de murs blancs, cerisiers, pavillons, lanternes ; mosaïque de cerisier au centre."""
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        g = f"Place/{cote}"
        xa, xb = X_ARRIERE_MUR, X_ENCEINTE - EP_REMPART / 2
        # mur avant (16,5) et murs de côté (16) : chaperons à des hauteurs différentes ; le mur de côté part du bord
        # de la plinthe du mur avant et s'arrête sur l'appui de la colline (aucune face coplanaire)
        place(b, "remparts", "mur_blanc", (s * (xa + xb) / 2, 0, Z_FIN_CITE), yaw=0, group=f"{g}/MurAvant",
              emprise=(xb - xa, EP_MUR, H_MUR_PLACE_AVANT), longueur=round(xb - xa, 2), hauteur=H_MUR_PLACE_AVANT,
              epaisseur=EP_MUR, variant=0)
        mur(b, f"{g}/MurCote", s * X_COUR, Z_FIN_CITE - EP_MUR / 2 - 0.3, Z_COLLINE + 0.2, hauteur=H_MUR_PLACE_COTE,
            epaisseur=EP_MUR, variant=1)
        # deux tours blanches encadrent l'entrée de la cour (une seule à toit bleu)
        x = s * 64
        place(b, "remparts", "tour_blanche", (x, 0, -401), yaw=face_couloir(x), group=f"{g}/TourEntree",
              emprise=(12, 12, 38), hauteur=38, cote=12, variant=2 if s < 0 else 1)
        place(b, "mobilier", "pilier_lanterne", (s * 50, 0, Z_FIN_CITE - 3.5), group=f"{g}/PilierEntree",
              variant=1, hauteur=18, emprise=(4, 4, 22))
        x = s * 69
        place(b, "batiments", "pavillon", (x, 0, Z_PLACE), yaw=face_couloir(x), group=f"{g}/Pavillon", variant=int(s > 0),
              emprise=(12, 12, 12))
        for i, z in enumerate((Z_PLACE + 10, Z_PLACE - 10)):
            place(b, "vegetation", "buisson", (s * 63, 0, z), group=f"{g}/Buisson{i}", variant=i + 2 * (s > 0),
                  emprise=(2.6, 2.6, 2.4))
        for i, z in enumerate((Z_PLACE + 18, Z_PLACE - 18)):
            x = s * 51
            place(b, "mobilier", "lanterne_pierre", (x, 0, z), yaw=face_couloir(x), group=f"{g}/Lanterne{i}", variant=i,
                  emprise=(3.4, 3.4, 7))
        variantes = (1, 4, 2, 0) if s < 0 else (4, 2, 0, 1)      # pas de cerisier pleureur devant la colline
        for i, (dx, z, t) in enumerate(((82, -404, 1.1), (84, -430, 0.95), (64, -459, 1.0), (82, -456, 1.1))):
            place(b, "vegetation", "cerisier", (s * dx, 0, z), yaw=i * 70, group=f"{g}/Cerisier{i}",
                  variant=variantes[i], taille=t, emprise=(13, 13, 16))
        place(b, "vegetation", "cerisier_geant", (s * 118, 0, -428), yaw=90 * (s > 0), group=f"{g}/CerisierGeant",
              variant=2 + (s > 0), emprise=(30, 30, 30))
        place(b, "vegetation", "pin", (s * 138, 0, -398), group=f"{g}/Pin", variant=int(s > 0), emprise=(10, 10, 16))
        place(b, "vegetation", "massif_arbres", (s * 128, 0, -458), group=f"{g}/Massif", variant=2 + (s > 0),
              emprise=(26, 18, 16), largeur=26, profondeur=18)


# ---------------------------------------------------------------------------
# Repères et contrôles
# ---------------------------------------------------------------------------

def reperes(b: Builder) -> None:
    """Pièces invisibles utiles au jeu : zone des œufs, entrée, sortie, couloir."""
    inv = dict(transparency=1.0, collide=False, shadow=False)
    D = DEMI_COULOIR
    with b.group("Reperes"):
        b.box((-R_PLACE, 0, Z_PLACE - R_PLACE), (R_PLACE, 1, Z_PLACE + R_PLACE), "#ffffff", name="ZoneOeufs", **inv)
        b.box((-D, 0, Z_PORTE + 18), (D, 1, Z_PORTE + 24), "#ffffff", name="Entree", **inv)
        b.box((-D, 0, Z_SORTIE - 4), (D, 1, Z_SORTIE + 2), "#ffffff", name="Sortie", **inv)
        b.box((-D, 0, Z_SORTIE), (D, 1, Z_PORTE), "#ffffff", name="Couloir", **inv)


def decouper(b: Builder, prefixes=("Sol/", "Enceinte/", "Lointain/", "Monuments/Colline", "Monuments/Porte"),
             taille: float = 64) -> None:
    """Range les pièces des grands ensembles dans des sous-modèles de 64 × 64 studs (streaming Roblox)."""
    for p in b.parts:
        if p.group.startswith(prefixes):
            i, j = math.floor(p.pos[0] / taille), math.floor(p.pos[2] / taille)
            racine = "/".join(p.group.split("/")[:2])
            reste = p.group[len(racine):]
            p.group = f"{racine}/Bloc_{i:+d}_{j:+d}{reste}"


def build_zone(seed: int = 7) -> Builder:
    _COMPTES.clear()
    _POSES.clear()
    b = Builder(seed=seed)
    sol_couloir(b)
    sol_trottoirs(b)
    sol_cotes(b)
    place(b, "remparts", "grande_porte", (0, 0, Z_PORTE), group="Monuments/Porte", emprise=(320, EP_PORTE, 100),
          attente=_portique(OUVERTURE_PORTE, 56, 76, EP_PORTE, 100, X_ENCEINTE, 64),
          ouverture=OUVERTURE_PORTE, hauteur=64, mur=X_ENCEINTE, epaisseur=EP_PORTE, variant=0,
          z_max_vantaux=Z_VANTAUX, vantaux="enduit")
    place(b, "remparts", "porte_interieure", (0, 0, Z_PORTE_INT), group="Monuments/PorteInterieure",
          emprise=(300, EP_PORTE_INT, 70), attente=_portique(OUVERTURE_PORTE_INT, 36, 62, EP_PORTE_INT, 70, X_ENCEINTE, 24),
          ouverture=OUVERTURE_PORTE_INT, hauteur_passage=36, mur=X_ENCEINTE, hauteur_mur=24, x_allee=X_BORD, variant=0)
    place(b, "colline", "colline_tour", (0, 0, Z_COLLINE), group="Monuments/Colline", emprise=(2 * X_FOND, PROF_COLLINE, 46),
          attente=_attente_colline(PASSAGE_TUNNEL, 2 * X_FOND, PROF_COLLINE, 46),
          passage=PASSAGE_TUNNEL, largeur=2 * X_FOND, profondeur=PROF_COLLINE, hauteur=46, sol_tunnel=SOL_TUNNEL,
          appuis=(X_COUR, X_ENCEINTE))
    enceinte(b)
    ville_lointaine(b)
    approche(b)
    faubourg(b)
    details_faubourg(b)
    cite(b)
    cour_des_oeufs(b)
    reperes(b)
    decouper(b)
    return b


def _bornes(p):
    R = np.asarray(p.rot).reshape(3, 3)
    half = np.abs(R) @ (np.asarray(p.size) / 2)
    return np.asarray(p.pos) - half, np.asarray(p.pos) + half


def couloir_libre(b: Builder) -> list:
    """Liste ce qui encombre le couloir de course au sol (pièces solides, hors sol et repères)."""
    gene = []
    for p in b.parts:
        if not p.collide or p.group.startswith(("Sol", "Reperes")):
            continue
        lo, hi = _bornes(p)
        if lo[0] < DEMI_COULOIR - 0.05 and hi[0] > -DEMI_COULOIR + 0.05 and lo[1] < 12 and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            gene.append((p.group, p.name, [round(v, 1) for v in lo], [round(v, 1) for v in hi]))
    return gene


def trop_bas_au_dessus(b: Builder, y_min: float = Y_LIBRE) -> list:
    """Toute pièce (solide ou non) au-dessus du couloir élargi |x| < X_LIBRE et sous `y_min` : la caméra Roblox
    sauterait en passant dessous, et rien ne doit traîner dans le couloir."""
    out = []
    for p in b.parts:
        if p.group.startswith(("Sol", "Reperes")):
            continue
        lo, hi = _bornes(p)
        if lo[0] < X_LIBRE and hi[0] > -X_LIBRE and lo[1] < y_min and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name, round(lo[1], 1)))
    return out


# Contacts voulus entre poses (préfixes de groupes) : un mur qui bute contre une tour ou un portail, etc.
CONTACTS_VOULUS = (
    ("Enceinte/", "Monuments/Porte"),            # remparts contre les tours d'angle de la grande porte
    ("Enceinte/", "Monuments/PorteInterieure"),  # mur intérieur jusqu'au rempart
    ("Enceinte/", "Monuments/Colline"),          # remparts contre les appuis de la colline
    ("Place/G/MurCote", "Monuments/Colline"), ("Place/D/MurCote", "Monuments/Colline"),
    ("Cite/Gauche/MurAllee", "Monuments/PorteInterieure"), ("Cite/Droite/MurAllee", "Monuments/PorteInterieure"),
    ("Cite/Gauche/MurTransverse", "Enceinte/"), ("Cite/Droite/MurTransverse", "Enceinte/"),
    ("Place/G/MurAvant", "Enceinte/"), ("Place/D/MurAvant", "Enceinte/"),
)


def _voulu(ga: str, gb: str) -> bool:
    for (a, bb) in CONTACTS_VOULUS:
        if (ga.startswith(a) and gb.startswith(bb)) or (gb.startswith(a) and ga.startswith(bb)):
            return True
    return False


def chevauchements(b: Builder, marge: float = 0.1, tout: bool = False) -> list:
    """Paires de poses dont des pièces s'interpénètrent de plus de `marge` sur les trois axes (boîtes englobantes
    des pièces). Les feuillages qui se mêlent (végétation contre végétation) et les contacts voulus
    (CONTACTS_VOULUS) sont ignorés sauf si `tout`. → [(groupe A, groupe B, nb de paires, recouvrement max)]."""
    boites = []
    for (g, n0, n1, module, fn) in _POSES:
        if n1 <= n0:
            continue
        bs = [_bornes(p) for p in b.parts[n0:n1]]
        lo = np.array([x[0] for x in bs])
        hi = np.array([x[1] for x in bs])
        boites.append((g, module, fn, lo, hi, lo.min(0), hi.max(0), n0))
    out = []
    for i in range(len(boites)):
        ga, ma, fa, loa, hia, la, ha, na = boites[i]
        for j in range(i + 1, len(boites)):
            gb, mb, fb, lob, hib, lb, hb, nb = boites[j]
            if np.any(la >= hb - marge) or np.any(lb >= ha - marge):
                continue
            if not tout and ((ma == "vegetation" and mb == "vegetation") or _voulu(ga, gb)):
                continue
            ov = np.minimum(hia[:, None, :], hib[None, :, :]) - np.maximum(loa[:, None, :], lob[None, :, :])
            m = np.all(ov > marge, axis=2)
            n, prof = 0, 0.0
            for (ia, ib) in zip(*np.nonzero(m)):
                pa, pb = b.parts[na + ia], b.parts[nb + ib]
                d = _penetration(pa, pb)
                if d > marge:
                    n += 1
                    prof = max(prof, d)
            # jointure voulue : un mur blanc qui bute contre un autre ouvrage maçonné (≤ 1 stud)
            mur_contre = "mur_blanc" in (fa, fb) and {ma, mb} <= {"remparts", "colline"} and prof <= 1.0
            if n and (tout or not mur_contre):
                out.append((ga, gb, n, round(prof, 2)))
    return out


def _penetration(pa, pb) -> float:
    """Pénétration de deux pièces vues comme des boîtes orientées (axes séparateurs) ; ≤ 0 si disjointes."""
    Ra, Rb = np.asarray(pa.rot).reshape(3, 3), np.asarray(pb.rot).reshape(3, 3)
    ha, hb = np.asarray(pa.size) / 2, np.asarray(pb.size) / 2
    T = np.asarray(pb.pos) - np.asarray(pa.pos)
    axes = [Ra[:, i] for i in range(3)] + [Rb[:, i] for i in range(3)]
    for i in range(3):
        for j in range(3):
            v = np.cross(Ra[:, i], Rb[:, j])
            nv = np.linalg.norm(v)
            if nv > 1e-6:
                axes.append(v / nv)
    best = math.inf
    for L in axes:
        d = np.sum(ha * np.abs(Ra.T @ L)) + np.sum(hb * np.abs(Rb.T @ L)) - abs(T @ L)
        best = min(best, d)
        if best <= 0:
            return best
    return float(best)


def hors_budget() -> list:
    out = []
    for (module, fn, params, n, group) in _COMPTES:
        bud = _budget(module, fn, params)
        if n > bud:
            out.append((group, f"{module}.{fn}", n, bud))
    return out


def meta() -> dict:
    return {"nom": "ZoneBleach", "version": VERSION, "largeur_couloir": 2 * DEMI_COULOIR,
            "longueur": -Z_SORTIE, "spawn": [0, 0, Z_PORTE + 30]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / "build" / "parts.json"))
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--chevauchements", action="store_true", help="liste les poses qui s'interpénètrent")
    args = ap.parse_args()
    b = build_zone()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    b.save_json(out, meta=meta())
    attente = sorted({p.name for p in b.parts if p.name.startswith("ATTENTE_")})
    gene = couloir_libre(b)
    bas = trop_bas_au_dessus(b)
    print(json.dumps({"pieces": len(b.parts), "plafond": PLAFOND, "fichier": str(out), "en_attente": attente,
                      "couloir_encombre": gene[:20], "nb_couloir_encombre": len(gene),
                      "trop_bas_au_dessus_du_couloir": bas[:20], "nb_trop_bas": len(bas),
                      "hors_budget": hors_budget()[:20]}, ensure_ascii=False))
    if args.stats:
        for k, v in b.stats().items():
            print(f"{v:6d}  {k}")
        par_asset = defaultdict(lambda: [0, 0])
        for (module, fn, params, n, group) in _COMPTES:
            par_asset[f"{module}.{fn}"][0] += 1
            par_asset[f"{module}.{fn}"][1] += n
        if par_asset:
            print("-- assets livrés (poses, pièces) --")
            for k, (nb, n) in sorted(par_asset.items(), key=lambda kv: -kv[1][1]):
                print(f"{n:6d}  {k} ×{nb}")
        sol = sum(1 for p in b.parts if p.group.startswith("Sol"))
        print(f"-- sol : {sol} pièces")
    if args.stats or args.chevauchements:
        ch = chevauchements(b)
        print(f"-- chevauchements entre poses : {len(ch)}")
        for (ga, gb, n, prof) in ch:
            print(f"   {ga}  ×  {gb}  ({n} paires, jusqu'à {prof})")


if __name__ == "__main__":
    main()
