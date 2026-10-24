#!/usr/bin/env python3
"""Plan de la zone Bleach (la cité blanche aux toits ocre) en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course occupe x ∈ [-32, 32], bordé de trottoirs jusqu'à |x| = 42 ;
- on entre par la GRANDE PORTE blanche (mur d'enceinte de 64 studs, centré sur z = 0, vantaux ouverts vers
  l'extérieur) et on court vers -Z : le FAUBOURG de bois sombre et de tuiles grises sur une route de sable à
  grandes dalles (z -8 → -171), la PORTE INTÉRIEURE (tour-porte blanche en z = -176), la CITÉ BLANCHE entre
  de longs murs blancs à chaperon ocre, trois enclos par côté, tours blanches et passerelle laquée rouge au-dessus
  du couloir (z -181 → -388), la COUR DES ŒUFS pavée et fermée de murs blancs (centre z = -430), puis la
  COLLINE de la grande tour blanche et du monolithe, traversée par un tunnel (z -476 → -522) ;
- des remparts blancs ferment les côtés (|x| = 150) ; au-delà, la ville lointaine s'étend jusqu'à |x| = 210.

    python zone.py                     # écrit build/parts.json (aucune dépendance à Blender)
    python zone.py --stats             # nombre de pièces par groupe et contrôle des budgets par asset
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
DEMI_COULOIR = 32
X_BORD = 42              # bord des trottoirs = alignement des façades et des murs d'allée
EP_MUR = 2.4             # épaisseur des murs d'allée de la cité
X_MUR = X_BORD + EP_MUR / 2          # axe des murs d'allée (faces en 42 et 44,4)
X_ARRIERE_MUR = X_BORD + EP_MUR      # 44,4 : face arrière des murs d'allée
X_FRONT_CITE = 52.4      # façades des bâtiments de la cité (cour de 8 studs derrière les murs)
X_COUR = 80              # demi-largeur de la cour des œufs
X_ENCEINTE = 150         # axe des remparts latéraux
EP_REMPART = 3.0
X_FOND = 210             # fin de la ville lointaine
Z_APPROCHE = 64          # sol devant la grande porte (côté apparition)
Z_PORTE = 0              # grande porte (mur centré sur z = 0, épaisseur 16)
EP_PORTE = 16
Z_FAUBOURG = -8          # début du faubourg (revers de la grande porte)
Z_RUE = -14              # première façade
Z_FIN_FAUBOURG = -166
Z_PORTE_INT = -176       # porte intérieure (mur centré, épaisseur 10)
EP_PORTE_INT = 10
Z_CITE = -181            # début de la cité blanche
Z_PASSERELLE = -286      # passerelle laquée au-dessus du couloir
Z_FIN_CITE = -388        # mur avant de la cour des œufs
Z_PLACE = -430           # centre de la place des œufs
R_PLACE = 34
Z_COLLINE = -476         # mur de soutènement de la colline (entrée du tunnel)
PROF_COLLINE = 46
Z_SORTIE = Z_COLLINE - PROF_COLLINE   # -522 : sortie vers la zone suivante
H_GUIRLANDE = 39         # fil des guirlandes : les lampions restent au-dessus de 31 studs (caméra Roblox)
Y_LIBRE = 30             # rien au-dessus du couloir (|x| < 33) sous cette hauteur

VERSION = "0.1"

# Budgets de pièces par asset (contrôlés par --stats). mur_blanc : 6 + longueur / 5 (arrondi au-dessus).
# Somme des budgets telle que posée ≈ 12 940 pièces (sol 1 070 et mobilier 590 compris) pour un plafond de 13 500.
BUDGETS = {
    ("remparts", "grande_porte"): 850, ("remparts", "porte_interieure"): 420,
    ("remparts", "passerelle_rouge"): 330, ("remparts", "tour_blanche"): 65, ("remparts", "portail_cour"): 60,
    ("batiments", "maison_bois"): 140, ("batiments", "echoppe"): 45, ("batiments", "tour_guet_bois"): 70,
    ("batiments", "maison_blanche"): 150, ("batiments", "caserne"): 150, ("batiments", "pavillon"): 90,
    ("batiments", "quartier_lointain"): 32,
    ("vegetation", "cerisier"): 40, ("vegetation", "cerisier_geant"): 150, ("vegetation", "pin"): 40,
    ("vegetation", "massif_arbres"): 70, ("vegetation", "buisson"): 8, ("vegetation", "rocher"): 10,
    ("vegetation", "bassin_pont"): 80,
    ("colline", "colline_tour"): 1700,
}
BUDGET_SIMPLE = 70       # maison_bois / maison_blanche / caserne avec simple=True
BUDGET_MOBILIER = 40
_COMPTES: list = []      # (module, fn, params, pièces) de chaque pose


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
        if f is not None:
            try:
                info = f(b, **params) or {}
                _COMPTES.append((module, fn, params, len(b.parts) - n0, group))
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
        b.box((-80, h, -40), (-48, h + 104, -12), rose, transparency=0.5)    # grande tour blanche
        b.box((50, h, -34), (68, h + 100, -18), rose, transparency=0.5)      # monolithe
    return dessin


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
            grid[j, i] = None if v is None else tuple(v)
    n = 0
    for col in {v for v in grid.reshape(-1) if v is not None}:
        mask = np.vectorize(lambda v, col=col: v == col)(grid)
        for (i, j, w, h) in mask_rects(mask):
            b.box((x0 + i * cell, y_haut - epaisseur, z0 + j * cell),
                  (x0 + (i + w) * cell, y_haut, z0 + (j + h) * cell), col, studs=studs, name=name, **kw)
            n += 1
    return n


def damier(a, bcol, taille: float, tz: float | None = None):
    a, bcol = (hexrgb(v) if isinstance(v, str) else v for v in (a, bcol))
    tz = tz or taille
    return lambda x, z: a if (math.floor(x / taille) + math.floor(z / tz)) % 2 == 0 else bcol


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


def _sable(x: float, z: float):
    """Route de sable du faubourg : grandes plaques de teintes voisines, ornières plus foncées."""
    ax = abs(x)
    if 16 <= ax < 20:
        return c("sable_fonce")
    v = _hash(math.floor(x / 8), math.floor(z / 12))
    return c("sable_clair") if v < 0.22 else (c("sable") if v < 0.8 else shade(c("sable"), 0.96))


def _chemin_dalles(x: float, z: float):
    """Chemin central de grandes dalles posées sur le sable (|x| < 11), rangs de 6 studs séparés de 1 stud de
    sable, chaque rang coupé en une, deux ou trois dalles."""
    ax = abs(x)
    if ax >= 11:
        return _sable(x, z)
    rang = math.floor(z / 7)
    if z - rang * 7 < 1 or ax >= 10.5:
        return c("sable_fonce")
    coupe = (None, (0.0,), (-3.5, 4.0))[int(_hash(rang, 3) * 3)]
    if coupe and any(abs(x - k) < 0.5 for k in coupe):
        return c("sable_fonce")
    piece = sum(1 for k in (coupe or ()) if x > k)
    return c("dalle_chemin") if _hash(rang, piece, 7) < 0.6 else c("dalle_chemin_fonce")


def _dallage_cite(x: float, z: float):
    """Dallage de la cité : grandes dalles de 16 × 8 en appareil décalé, deux blancs chauds, liseré au bord."""
    if abs(x) >= DEMI_COULOIR - 1.5:
        return c("pierre_claire")
    rang = math.floor(z / 8)
    k = math.floor((x + (8 if rang % 2 else 0)) / 16)
    return c("dallage") if (k + rang) % 2 == 0 else c("dallage_ombre")


def sol_couloir(b: Builder) -> None:
    pc, p, pf = c("pierre_claire"), c("pierre"), c("pierre_fonce")

    def seuil(x, z):
        return pf if math.floor(z / 4) % 2 else shade(pf, 0.94)

    def approche(x, z):
        return c("dallage") if (math.floor(x / 16) + math.floor(z / 16)) % 2 == 0 else pc

    def cour(x, z):
        m = mosaique_place(x, z)
        if m:
            return m
        return c("dallage") if math.floor(z / 8) % 2 else c("dallage_ombre")

    def tunnel(x, z):
        return pf if math.floor(z / 8) % 2 else shade(pf, 0.9)

    D = DEMI_COULOIR
    with b.group("Sol/Couloir"):
        sol_pixel(b, -D, D, EP_PORTE / 2, Z_APPROCHE, 8, approche, name="Approche")
        sol_pixel(b, -D, D, Z_FAUBOURG, EP_PORTE / 2, 4, seuil, name="Seuil")
        sol_pixel(b, -12, 12, Z_FIN_FAUBOURG, Z_FAUBOURG, 1, _chemin_dalles, name="Chemin")
        for s in (-1, 1):
            xa, xb = sorted((s * 12, s * D))
            sol_pixel(b, xa, xb, Z_FIN_FAUBOURG, Z_FAUBOURG, 4, _sable, name="Sable")
        sol_pixel(b, -D, D, Z_CITE, Z_FIN_FAUBOURG, 1, seuil, name="Seuil")
        sol_pixel(b, -D, D, Z_FIN_CITE, Z_CITE, 1, _dallage_cite, name="Dallage")
        sol_pixel(b, -D, D, Z_COLLINE, Z_FIN_CITE, 2, cour, name="Cour")
        sol_pixel(b, -36, 36, Z_SORTIE - 4, Z_COLLINE, 4, tunnel, name="Tunnel")   # tout le passage du tunnel (68)


def sol_trottoirs(b: Builder) -> None:
    pf = c("pierre_fonce")

    def trottoir(x, z):
        m = mosaique_place(x, z)
        if m:
            return m
        ax = abs(x)
        if z > EP_PORTE / 2:                                    # approche
            return c("pierre") if ax < DEMI_COULOIR + 1 else c("pierre_claire")
        if z > Z_FAUBOURG:
            return pf
        if z > Z_FIN_FAUBOURG:                                  # faubourg : bordure de pierre, terre battue
            if ax < DEMI_COULOIR + 1:
                return c("pierre")
            return c("terre") if math.floor(z / 16) % 2 else shade(c("terre"), 1.06)
        if z > Z_CITE:
            return pf
        if z > Z_FIN_CITE:                                      # cité : caniveau, dalles alternées
            if ax < DEMI_COULOIR + 1:
                return pf
            return c("pierre_claire") if math.floor(z / 6) % 2 else c("dallage_ombre")
        return c("dallage") if math.floor(z / 8) % 2 else c("dallage_ombre")   # cour des œufs

    with b.group("Sol/Trottoirs"):
        for s in (-1, 1):
            xa, xb = sorted((s * DEMI_COULOIR, s * X_BORD))
            sol_pixel(b, xa, xb, Z_COLLINE, Z_APPROCHE, 2, trottoir)


def _potager(ax: float, z: float):
    """Jardins potagers derrière le faubourg : planches de terre sombre et rangs de légumes."""
    for (za, zb) in ((-28, -66), (-86, -124)):
        if 106 <= ax < 140 and zb <= z < za:
            return c("culture") if math.floor(z / 2) % 3 == 0 else c("terre_fonce")
    return None


PELOUSES = ((-118, -88, -320, -284), (84, 114, -287, -253), (-104, -84, -350, -332), (88, 112, -348, -330),
            (-118, -84, -236, -200), (88, 122, -244, -206))   # (x0, x1, z0, z1) : pelouses sous les grands arbres


def sol_cotes(b: Builder) -> None:
    """Sol entre les trottoirs et les remparts : sable et ruelle au faubourg, potagers, gravier blanc ratissé dans
    les enclos de la cité (allées de pierre vers les portails, quelques pelouses), cour pavée et jardins autour
    de la place."""
    portes = {-1: (-213, -262, -358), 1: (-222, -312, -354)}

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
            if 62 <= ax < 68:                                   # ruelle de service
                return c("terre")
            if ax >= 100:
                return c("herbe") if (math.floor(x / 24) + math.floor(z / 24)) % 2 == 0 else c("herbe_fonce")
            return c("sable_fonce") if ax < 62 else shade(c("sable_fonce"), 1.05)
        if z > Z_CITE:
            return c("pierre_fonce")
        if z > Z_FIN_CITE:                                      # enclos de la cité
            for zg in portes[s]:
                if abs(z - zg) < 2.5 and ax < X_FRONT_CITE + 1:
                    return c("pierre_claire")
            if ax < X_FRONT_CITE + 14:
                return c("gravier") if math.floor(z / 6) % 2 else c("gravier_ombre")
            for (xa, xb, za, zb) in PELOUSES:
                if xa <= x < xb and za <= z < zb:
                    return c("herbe")
            return c("gravier_ombre")
        if ax < X_COUR:                                         # cour des œufs
            return c("dallage") if math.floor(z / 8) % 2 else c("dallage_ombre")
        return c("herbe") if (math.floor(x / 24) + math.floor(z / 22)) % 2 == 0 else c("herbe_claire")

    with b.group("Sol/Cotes"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * (X_ENCEINTE + EP_REMPART / 2)))
            sol_pixel(b, xa, xb, Z_COLLINE, EP_PORTE / 2, 2, couleur)
    with b.group("Sol/Abords"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_FOND))
            sol_pixel(b, xa, xb, EP_PORTE / 2, Z_APPROCHE, 8,
                      lambda x, z: c("pierre_claire") if abs(x) < 52 else
                      (c("herbe") if (math.floor(x / 24) + math.floor(z / 24)) % 2 == 0 else c("herbe_fonce")))
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


def enceinte(b: Builder) -> None:
    """Remparts blancs latéraux (28 studs, chaperon ocre, meurtrières) et tours blanches."""
    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        x = s * X_ENCEINTE
        trous = [(zt + 7, zt - 7) for zt in TOURS_REMPART]
        for i, (za, zb) in enumerate(_troncons(-EP_PORTE / 2, Z_COLLINE, trous)):
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

FAUBOURG = {  # (largeur, profondeur, variante, ruelle après) ; les rangées commencent en z_depart
    -1: (Z_RUE, [(22, 16, 0, 9), (20, 16, 1, 8), (24, 18, 2, 9), (18, 16, 3, 8), (22, 16, 4, 0)]),
    1: (Z_RUE - 4, [(24, 18, 1, 8), (20, 16, 2, 9), (22, 16, 3, 8), (18, 16, 0, 9), (22, 16, 5, 0)]),
}


def approche(b: Builder) -> None:
    """Esplanade devant la grande porte : lanternes, cerisiers, pins et massifs."""
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        for i, z in enumerate((56, 22)):
            x = s * 37
            place(b, "mobilier", "lanterne_pierre", (x, 0, z), yaw=face_couloir(x), group=f"Abords/Lanterne{cote}{i}",
                  variant=i, emprise=(3.4, 3.4, 7))
        for i, (dx, z, v) in enumerate(((66, 24, 0), (84, 48, 1), (122, 30, 2))):
            place(b, "vegetation", "cerisier", (s * dx, 0, z), yaw=i * 50, group=f"Abords/Cerisier{cote}{i}",
                  variant=v + (s > 0), emprise=(14, 14, 16))
        place(b, "vegetation", "massif_arbres", (s * 160, 0, 40), group=f"Abords/Massif{cote}", variant=int(s > 0),
              emprise=(28, 20, 16), largeur=28, profondeur=20)
        place(b, "vegetation", "pin", (s * 196, 0, 24), group=f"Abords/Pin{cote}", variant=1 + (s > 0), emprise=(10, 10, 16))
        for i, (dx, z) in enumerate(((100, 14), (140, 54))):
            place(b, "vegetation", "rocher", (s * dx, 0, z), yaw=i * 40, group=f"Abords/Rocher{cote}{i}", variant=i + (s > 0),
                  taille=1.0 + 0.3 * i, emprise=(5, 5, 3))
        for i, z in enumerate((48, 30)):
            place(b, "vegetation", "buisson", (s * 40, 0, z), group=f"Abords/Buisson{cote}{i}", variant=i, emprise=(2.6, 2.6, 2.4))


def faubourg(b: Builder) -> dict:
    """Rangées de maisons de bois à étage le long du couloir ; ruelles avec échoppes, puits, tours de guet."""
    ruelles = {}
    for s, (z0, plan) in FAUBOURG.items():
        cote = "Gauche" if s < 0 else "Droite"
        z = z0
        ruelles[s] = []
        for i, (larg, prof, v, apres) in enumerate(plan):
            zc = z - larg / 2
            x = s * (X_BORD + prof / 2)
            place(b, "batiments", "maison_bois", (x, 0, zc), yaw=face_couloir(x), group=f"Faubourg/{cote}/{i:02d}_MaisonBois",
                  emprise=(larg, prof, 20), largeur=larg, profondeur=prof, variant=v)
            z -= larg
            if apres:
                ruelles[s].append(z - apres / 2)
            z -= apres
        assert z > Z_FIN_FAUBOURG, f"rangée du faubourg trop longue ({z})"
    # ruelles : échoppes, puits, seaux, tours de guet visibles au bout
    contenu = {-1: ("echoppe", "puits", "echoppe", "seaux"), 1: ("echoppe", "nobori", "echoppe", "puits")}
    for s, zs in ruelles.items():
        cote = "G" if s < 0 else "D"
        for i, (zr, quoi) in enumerate(zip(zs, contenu[s])):
            g = f"Faubourg/Ruelles/{cote}{i}"
            if quoi == "echoppe":
                x = s * (X_BORD + 2.6)
                place(b, "batiments", "echoppe", (x, 0, zr), yaw=face_couloir(x), group=g, emprise=(8, 5, 8), variant=i + (s > 0))
            elif quoi == "puits":
                place(b, "mobilier", "puits", (s * 47, 0, zr), yaw=face_couloir(s), group=g, variant=0, emprise=(4.8, 4.4, 8.4))
            elif quoi == "seaux":
                place(b, "mobilier", "seaux_incendie", (s * 46, 0, zr), yaw=face_couloir(s), group=g, variant=0, emprise=(6.5, 2.4, 4.5))
            else:
                for k, dz in enumerate((-2.5, 2.5)):
                    place(b, "mobilier", "nobori", (s * 44, 0, zr + dz), yaw=face_couloir(s), group=f"{g}/{k}",
                          texte=("団子", "甘味")[k], variant=k, emprise=(1.4, 2.7, 9.6))
    for i, (x, z) in enumerate(((-69, ruelles[-1][1]), (69, ruelles[1][2]), (-70, -150))):
        place(b, "batiments", "tour_guet_bois", (x, 0, z), yaw=face_couloir(x), group=f"Faubourg/TourGuet{i}",
              emprise=(7, 7, 28), hauteur=28 - 2 * (i % 2), variant=i)
    # seconde rangée (simplifiée), tournée vers le couloir
    for i, (x, z, larg, v) in enumerate(((-84, -40, 20, 2), (-84, -118, 22, 5), (84, -64, 20, 4), (84, -138, 22, 3))):
        place(b, "batiments", "maison_bois", (x, 0, z), yaw=face_couloir(x), group=f"Faubourg/Arriere/{i:02d}_MaisonBois",
              emprise=(larg, 16, 18), largeur=larg, profondeur=16, variant=v, simple=True)
    # arbres du faubourg : au bout de la rue (devant la porte intérieure) et dans les jardins
    for i, (x, z, kind, v, t) in enumerate(((-52, -162, "cerisier", 0, 0.85), (56, -164, "cerisier", 2, 0.8),
                                            (-104, -78, "cerisier", 1, 1.0), (106, -22, "cerisier", 3, 1.0),
                                            (110, -152, "cerisier", 0, 1.1), (-122, -20, "pin", 0, 1.0),
                                            (124, -78, "pin", 1, 1.0), (-128, -150, "massif_arbres", 0, 1.0))):
        kw = {"largeur": 26, "profondeur": 18} if kind == "massif_arbres" else {"taille": t}
        place(b, "vegetation", kind, (x, 0, z), yaw=(i * 37) % 360, group=f"Faubourg/Arbres/{i:02d}_{kind}",
              variant=v, emprise=(14, 14, 16), **kw)
    return ruelles


def details_faubourg(b: Builder) -> None:
    """Objets du trottoir (|x| = 37,5) et guirlandes de lampions au-dessus de la rue."""
    props = {
        -1: [(-22, "nobori", {"texte": "茶"}), (-31, "panneau", {"texte": "団子"}), (-58, "tonneaux", {}), (-84, "etal", {}),
             (-92, "sacs_riz", {}), (-112, "lanterne_poteau", {}), (-140, "nobori", {"texte": "宿"}), (-148, "caisses", {})],
        1: [(-24, "lanterne_poteau", {}), (-34, "nobori", {"texte": "米"}), (-60, "etal", {}), (-88, "caisses", {}),
            (-96, "panneau", {"texte": "蕎麦"}), (-114, "tonneaux", {}), (-128, "charrette", {"yaw": 180}), (-146, "nobori", {"texte": "薬"})],
    }
    for s, lst in props.items():
        cote = "G" if s < 0 else "D"
        for k, (z, fn, kw) in enumerate(lst):
            x = s * 37.5
            kw = dict(kw)
            yaw = kw.pop("yaw", face_couloir(x))
            place(b, "mobilier", fn, (x, 0, z), yaw=yaw, group=f"Faubourg/Details/{cote}{k:02d}_{fn}",
                  variant=k % 3, emprise=(3, 3, 4), **kw)
    _guirlandes(b, "Faubourg/Guirlandes", (-50, -122), variant_mat=0, variants=(0, 1))


def _guirlandes(b: Builder, group: str, zs, variant_mat: int, variants) -> None:
    fmat = _asset("mobilier", "mat_guirlande")
    fgui = _asset("mobilier", "guirlande_lampions")
    for i, z in enumerate(zs):
        with b.group(f"{group}/G{i}"):
            for s in (-1, 1):
                x = s * 36
                place(b, "mobilier", "mat_guirlande", (x, 0, z), yaw=face_couloir(x), group=f"Mat{'G' if s < 0 else 'D'}",
                      variant=variant_mat, hauteur=H_GUIRLANDE, emprise=(2, 2, H_GUIRLANDE + 3))
            if fmat and fgui:
                fgui(b, (-33.6, H_GUIRLANDE, z), (33.6, H_GUIRLANDE, z), n=9, creux=2.5, variant=variants[i % len(variants)])


# ---------------------------------------------------------------------------
# Cité blanche
# ---------------------------------------------------------------------------

CITE = {  # par côté : portails des trois enclos, bâtiments, arbres, tours
    -1: {"portes": (-213, -262, -358),
         "batiments": [("maison_blanche", -213, 24, 18, 0, False), ("maison_blanche", -262, 24, 18, 1, False),
                       ("caserne", -358, 36, 14, 0, False)],
         "arriere": [("caserne", 107, -213, 40, 14, 1), ("maison_blanche", 100, -358, 24, 18, 3)],
         "cerisiers": [(-53, -192, 0, 0.9), (-53, -235, 1, 0.9), (-53, -305, 2, 1.0), (-80, -340, 3, 0.9),
                       (-82, -378, 0, 0.9), (-128, -268, 1, 1.0)],
         "geant": (-112, -302),
         "tours": [(-132, -196, 42, 0), (-132, -372, 46, 2)],
         "jardin": ("bassin_pont", -78, -305)},
    1: {"portes": (-222, -312, -354),
        "batiments": [("maison_blanche", -222, 24, 18, 2, False), ("maison_blanche", -312, 24, 18, 4, False),
                      ("caserne", -354, 36, 14, 2, False)],
        "arriere": [("caserne", 107, -222, 40, 14, 3), ("maison_blanche", 100, -354, 24, 18, 1)],
        "cerisiers": [(53, -199, 2, 0.9), (80, -238, 3, 0.85), (53, -270, 0, 0.9), (80, -377, 1, 0.9),
                      (126, -300, 2, 1.0), (80, -340, 3, 0.9)],
        "geant": (98, -270),
        "tours": [(132, -200, 44, 1), (132, -372, 42, 3)],
        "jardin": None},
}
Z_MURS_TRANSVERSES = (-246, -330)
LANTERNES_CITE = (-196, -238, -272, -302, -338, -378)


def cite(b: Builder) -> None:
    """Allée entre deux longs murs blancs à chaperon ocre ; derrière, trois enclos par côté (portail, bâtiment
    blanc à toit ocre face au couloir, cour de gravier blanc, cerisiers, tours blanches), passerelle laquée."""
    for s, cfg in CITE.items():
        cote = "Gauche" if s < 0 else "Droite"
        g = f"Cite/{cote}"
        # murs d'allée, interrompus par les portails
        trous = [(zg + 7, zg - 7) for zg in cfg["portes"]]
        for i, (za, zb) in enumerate(_troncons(Z_CITE, Z_FIN_CITE, trous, long_max=32)):
            mur(b, f"{g}/MurAllee{i:02d}", s * X_MUR, za, zb, hauteur=10, epaisseur=EP_MUR, variant=i % 3)
        for i, zg in enumerate(cfg["portes"]):
            x = s * X_MUR
            place(b, "remparts", "portail_cour", (x, 0, zg), yaw=face_couloir(x), group=f"{g}/Portail{i}",
                  emprise=(14, 6, 13), largeur=10, hauteur=12, texte=("静", "茶", "白", "宿", "門", None)[(i + 3 * (s > 0)) % 6],
                  variant=i + (s > 0))
        # murs transverses entre enclos (de la face arrière des murs d'allée au rempart)
        for i, zt in enumerate(Z_MURS_TRANSVERSES):
            xa, xb = X_ARRIERE_MUR, X_ENCEINTE - EP_REMPART / 2
            place(b, "remparts", "mur_blanc", (s * (xa + xb) / 2, 0, zt), yaw=0, group=f"{g}/MurTransverse{i}",
                  emprise=(xb - xa, EP_MUR, 10), longueur=round(xb - xa, 2), hauteur=10, epaisseur=EP_MUR, variant=2)
        # bâtiments face au couloir
        for i, (fn, zc, larg, prof, v, simple) in enumerate(cfg["batiments"]):
            x = s * (X_FRONT_CITE + prof / 2)
            place(b, "batiments", fn, (x, 0, zc), yaw=face_couloir(x), group=f"{g}/{i:02d}_{fn}",
                  emprise=(larg, prof, 18), **({"largeur": larg} if fn == "maison_blanche" else {"longueur": larg}),
                  profondeur=prof, variant=v, simple=simple)
        for i, (fn, dx, zc, larg, prof, v) in enumerate(cfg["arriere"]):
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
            x = s * 39.5
            place(b, "mobilier", "lanterne_poteau", (x, 0, z), yaw=face_couloir(x), group=f"{g}/Lanterne{i}", variant=1,
                  emprise=(2.1, 2.1, 9.7))
    place(b, "remparts", "passerelle_rouge", (0, 0, Z_PASSERELLE), group="Cite/Passerelle", emprise=(118, 14, 58),
          attente=_attente_passerelle(104, 38), portee=104, hauteur=38)


# ---------------------------------------------------------------------------
# Cour des œufs
# ---------------------------------------------------------------------------

def cour_des_oeufs(b: Builder) -> None:
    """Grande cour pavée fermée de murs blancs, cerisiers, pavillons, lanternes ; mosaïque de cerisier au centre."""
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        g = f"Place/{cote}"
        xa, xb = X_ARRIERE_MUR, X_ENCEINTE - EP_REMPART / 2
        place(b, "remparts", "mur_blanc", (s * (xa + xb) / 2, 0, Z_FIN_CITE), yaw=0, group=f"{g}/MurAvant",
              emprise=(xb - xa, EP_MUR, 12), longueur=round(xb - xa, 2), hauteur=12, epaisseur=EP_MUR, variant=0)
        mur(b, f"{g}/MurCote", s * X_COUR, Z_FIN_CITE - EP_MUR / 2, Z_COLLINE, hauteur=12, epaisseur=EP_MUR, variant=1)
        place(b, "mobilier", "pilier_lanterne", (s * 37.5, 0, Z_FIN_CITE - 3), group=f"{g}/PilierEntree",
              variant=1, hauteur=18, emprise=(4, 4, 22))
        x = s * 62
        place(b, "batiments", "pavillon", (x, 0, Z_PLACE), yaw=face_couloir(x), group=f"{g}/Pavillon", variant=int(s > 0),
              emprise=(12, 12, 12))
        for i, z in enumerate((Z_PLACE + 8, Z_PLACE - 8)):
            place(b, "vegetation", "buisson", (s * 52, 0, z), group=f"{g}/Buisson{i}", variant=i + 2 * (s > 0),
                  emprise=(2.6, 2.6, 2.4))
        for i, z in enumerate((Z_PLACE + 18, Z_PLACE - 18)):
            x = s * 38
            place(b, "mobilier", "lanterne_pierre", (x, 0, z), yaw=face_couloir(x), group=f"{g}/Lanterne{i}", variant=i,
                  emprise=(3.4, 3.4, 7))
        for i, (dx, z, v) in enumerate(((50, -401, 0), (70, -410, 1), (58, -459, 2))):
            place(b, "vegetation", "cerisier", (s * dx, 0, z), yaw=i * 70, group=f"{g}/Cerisier{i}",
                  variant=v + (s > 0), taille=1.0, emprise=(13, 13, 16))
        place(b, "vegetation", "cerisier_geant", (s * 112, 0, -432), yaw=90 * (s > 0), group=f"{g}/CerisierGeant",
              variant=2 + (s > 0), emprise=(30, 30, 30))
        place(b, "vegetation", "pin", (s * 132, 0, -400), group=f"{g}/Pin", variant=int(s > 0), emprise=(10, 10, 16))
        place(b, "vegetation", "massif_arbres", (s * 128, 0, -455), group=f"{g}/Massif", variant=2 + (s > 0),
              emprise=(26, 18, 16), largeur=26, profondeur=18)


# ---------------------------------------------------------------------------
# Repères et contrôles
# ---------------------------------------------------------------------------

def reperes(b: Builder) -> None:
    """Pièces invisibles utiles au jeu : zone des œufs, entrée, sortie, couloir."""
    inv = dict(transparency=1.0, collide=False, shadow=False)
    with b.group("Reperes"):
        b.box((-R_PLACE, 0, Z_PLACE - R_PLACE), (R_PLACE, 1, Z_PLACE + R_PLACE), "#ffffff", name="ZoneOeufs", **inv)
        b.box((-DEMI_COULOIR, 0, Z_PORTE + 18), (DEMI_COULOIR, 1, Z_PORTE + 24), "#ffffff", name="Entree", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE - 4), (DEMI_COULOIR, 1, Z_SORTIE + 2), "#ffffff", name="Sortie", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE), (DEMI_COULOIR, 1, Z_PORTE), "#ffffff", name="Couloir", **inv)


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
    b = Builder(seed=seed)
    sol_couloir(b)
    sol_trottoirs(b)
    sol_cotes(b)
    place(b, "remparts", "grande_porte", (0, 0, Z_PORTE), group="Monuments/Porte", emprise=(300, EP_PORTE, 90),
          attente=_portique(76, 50, 62, EP_PORTE, 90, X_ENCEINTE, 64),
          ouverture=76, hauteur=64, mur=X_ENCEINTE, epaisseur=EP_PORTE)
    place(b, "remparts", "porte_interieure", (0, 0, Z_PORTE_INT), group="Monuments/PorteInterieure", emprise=(300, EP_PORTE_INT, 62),
          attente=_portique(72, 36, 48, EP_PORTE_INT, 62, X_ENCEINTE, 24),
          ouverture=72, hauteur_passage=36, mur=X_ENCEINTE, hauteur_mur=24)
    place(b, "colline", "colline_tour", (0, 0, Z_COLLINE), group="Monuments/Colline", emprise=(2 * X_FOND, PROF_COLLINE, 46),
          attente=_attente_colline(68, 2 * X_FOND, PROF_COLLINE, 46),
          passage=68, largeur=2 * X_FOND, profondeur=PROF_COLLINE, hauteur=46)
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
    """Toute pièce (solide ou non) au-dessus du couloir élargi |x| < 33 et sous `y_min` : la caméra Roblox
    sauterait en passant dessous, et rien ne doit traîner dans le couloir."""
    out = []
    for p in b.parts:
        if p.group.startswith(("Sol", "Reperes")):
            continue
        lo, hi = _bornes(p)
        if lo[0] < DEMI_COULOIR + 1 and hi[0] > -DEMI_COULOIR - 1 and lo[1] < y_min and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name, round(lo[1], 1)))
    return out


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


if __name__ == "__main__":
    main()
