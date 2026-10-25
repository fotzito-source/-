#!/usr/bin/env python3
"""Plan de la zone My Hero Academia (l'académie des héros et sa ville moderne) en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course occupe x ∈ [-45, 45] (90 studs : la route du milieu est beaucoup plus large que dans
  les autres zones, à la demande), bordé de trottoirs jusqu'à |x| = 55 ;
- on entre en z = 0 dans une RUE DE VILLE moderne (chaussée, trottoirs roses, boutiques vitrées, bureaux
  blancs et bleu ciel), sous un VIADUC de train à 36 studs (z = -18), carrefour et rues latérales à voitures
  garées (z = -66) ; au bout, le grand PORTAIL DE SÉCURITÉ du campus dans un long mur d'enceinte (z = -132) ;
- l'AVENUE DU CAMPUS (z -140 → -296) : dallage lavande pâle, haies taillées, conifères, bannières, dortoirs de
  brique rouge et cerisiers à gauche, bâtiments de cours vitrés, halle d'entraînement et terrain de sport à
  piste (buts, petite tribune) à droite ;
- les TERRAINS D'ENTRAÎNEMENT (z -296 → -400) : ville factice à demi détruite et robots à gauche, grand
  DÔME DE VERRE (parc d'entraînement avec montagne artificielle) à droite ;
- le STADE (z -400 → -528) : la route le traverse par deux grandes ouvertures, la place des œufs est au
  centre de l'arène (z = -464) ;
- les TOURS JUMELLES de verre bleu-violet (z -536 → -574), reliées par une passerelle au-dessus de la route :
  on sort dessous vers la fin de la carte (z = -574).
Un mur d'enceinte (|x| = 185) et une ceinture d'arbres ferment le campus ; la ville lointaine dépasse derrière.
Contrôles d'intégration : `couloir_libre`, `trop_bas_au_dessus`, budgets par asset et `chevauchements` (boîtes
englobantes des pièces de deux poses différentes qui se pénètrent).

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

from kit import Builder, shade  # noqa: E402
from palette import c  # noqa: E402
from textures import mask_rects  # noqa: E402

# ---------------------------------------------------------------------------
# Dimensions (studs)
# ---------------------------------------------------------------------------
DEMI_COULOIR = 45        # couloir de course x ∈ [-45, 45] : 90 studs
X_BORD = 55              # bord des trottoirs = alignement des façades, des haies et des piles
X_LIBRE = 46             # rien au-dessus de |x| < 46 sous Y_LIBRE (caméra Roblox)
Y_LIBRE = 30
X_ENCEINTE = 185         # axe du mur d'enceinte latéral du campus
X_FOND = 239             # fin du sol (la ville lointaine se dresse entre 205 et 231)
Z_APPROCHE = 24          # sol avant l'entrée (côté zone précédente)
Z_ENTREE = 0
Z_VIADUC = -18           # axe du viaduc ferroviaire (tablier de 12 de large, dessous à 36 studs)
Z_RUE_A = (-26, -51)     # premier îlot de boutiques (le trottoir de la rue latérale commence en -52)
Z_CARREFOUR = -66        # axe des rues latérales (20 de large)
DEMI_RUE_LAT = 10
Z_RUE_B = (-81, -122)    # second îlot de boutiques
Z_PORTAIL = -132         # axe du portail de sécurité et du mur d'enceinte avant
EP_PORTAIL = 16
Z_AVENUE = Z_PORTAIL - EP_PORTAIL / 2          # -140 : début de l'avenue du campus
Z_FIN_AVENUE = -296
Z_FIN_TERRAINS = -400
Z_PLACE = -464           # centre de l'arène du stade = place des œufs (81 % du parcours)
R_PLACE = 34
DEMI_STADE_Z = 64        # le stade occupe z ∈ [-528, -400]
X_STADE = 140            # demi-largeur hors tout du stade
ARENE = (76, 46)         # demi-axes de l'arène (sol peint par zone.py) ; tribunes au-delà
PISTE = (72, 44)         # demi-axes extérieurs de la piste d'athlétisme ovale
Z_STADE = Z_PLACE + DEMI_STADE_Z               # -400
Z_FIN_STADE = Z_PLACE - DEMI_STADE_Z           # -528
Z_TOURS = -536           # façade avant des tours jumelles
Z_SORTIE = -574          # fin de la carte : la route sort sous la passerelle
PASSAGE_TOURS = 116      # écart entre les deux tours (faces intérieures en |x| = 58)
Y_PASSERELLE = 46        # dessous de la passerelle des tours

VERSION = "0.1"

# Budgets de pièces par asset (contrôlés par --stats). Somme des budgets telle que posée ≈ 12 260 pièces
# (sol 1 340 et mobilier 930 compris, mesurés) pour un plafond de 13 500 : marge ≈ 1 240.
BUDGETS = {
    # ville.py
    ("ville", "boutique"): 100, ("ville", "immeuble_bureaux"): 90, ("ville", "viaduc_train"): 420,
    ("ville", "portail_securite"): 700, ("ville", "silhouette_lointaine"): 8,
    # campus.py
    ("campus", "dortoir"): 160, ("campus", "batiment_cours"): 170, ("campus", "halle_entrainement"): 160,
    ("campus", "tours_jumelles"): 1300,
    # entrainement.py
    ("entrainement", "stade"): 1500, ("entrainement", "dome_entrainement"): 1100,
    ("entrainement", "immeuble_factice"): 50, ("entrainement", "decombres"): 16,
    ("entrainement", "robot_entrainement"): 40, ("entrainement", "cible"): 10,
    # vegetation.py
    ("vegetation", "conifere"): 8, ("vegetation", "arbre_rond"): 20, ("vegetation", "bosquet"): 30,
    ("vegetation", "parterre"): 10, ("vegetation", "rocher"): 6,
}
BUDGET_SIMPLE = {"immeuble_bureaux": 40, "dortoir": 70}   # variante `simple=True` (arrière-plans)
BUDGET_MOBILIER = 40
_COMPTES: list = []      # (module, fn, params, pièces, groupe) de chaque pose
_POSES: list = []        # (groupe, première pièce, fin, module, fn) de chaque pose


# ---------------------------------------------------------------------------
# Accès aux assets (avec silhouette d'attente si un module manque encore)
# ---------------------------------------------------------------------------

def _asset(module: str, fn: str):
    try:
        return getattr(importlib.import_module(f"assets.{module}"), fn)
    except (ImportError, AttributeError):
        return None


def _budget(module: str, fn: str, params: dict) -> int:
    if module == "mobilier":
        return 50 if fn == "ligne_electrique" else BUDGET_MOBILIER
    if fn == "mur_campus":
        return int(math.ceil(4 + params.get("longueur", 32) / 4))
    if fn == "haie":
        return int(math.ceil(3 + params.get("longueur", 24) / 6))
    if params.get("simple") and fn in BUDGET_SIMPLE:
        return BUDGET_SIMPLE[fn]
    return BUDGETS.get((module, fn), 10 ** 6)


def place(b: Builder, module: str, fn: str, pos, yaw: float = 0.0, group: str | None = None, emprise=(16, 16, 16),
          attente=None, **params) -> dict:
    """Pose un asset ; s'il n'existe pas encore, pose un bloc translucide rose de même emprise
    (ou la silhouette `attente(b)` des monuments qui enjambent le couloir). Chaque pose est notée dans `_POSES`
    (groupe, plage de pièces) pour le contrôle des chevauchements."""
    n_debut = len(b.parts)
    try:
        return _poser(b, module, fn, pos, yaw, group, emprise, attente, **params)
    finally:
        _POSES.append((group, n_debut, len(b.parts), module, fn))


def _poser(b: Builder, module: str, fn: str, pos, yaw, group, emprise, attente, **params) -> dict:
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


ROSE = "#ff4fd8"


def _attente_viaduc(longueur: float, hauteur: float, passage: float):
    """Tablier de 12 studs (dessous à `hauteur`) le long de X, piles hors de |x| < passage / 2."""
    def dessin(b):
        b.box((-longueur / 2, hauteur, -6), (longueur / 2, hauteur + 6, 6), ROSE, transparency=0.5)
        x = passage / 2 + 4
        while x < longueur / 2:
            for s in (-1, 1):
                b.box((s * x - 3, 0, -3), (s * x + 3, hauteur, 3), ROSE, transparency=0.5)
            x += 56
    return dessin


def _attente_portail(ouverture: float, hauteur: float, mur: float, h_mur: float, prof: float):
    """Deux pylônes, un linteau au-dessus de 36 studs, le mur d'enceinte jusqu'à |x| = mur."""
    def dessin(b):
        for s in (-1, 1):
            xa, xb = sorted((s * ouverture / 2, s * (ouverture / 2 + 22)))
            b.box((xa, 0, -prof / 2), (xb, hauteur, prof / 2), ROSE, transparency=0.5)
            xa, xb = sorted((s * (ouverture / 2 + 22), s * mur))
            b.box((xa, 0, -1.5), (xb, h_mur, 1.5), ROSE, transparency=0.6)
        b.box((-ouverture / 2, 36, -prof / 2), (ouverture / 2, hauteur, prof / 2), ROSE, transparency=0.5)
    return dessin


def _attente_stade(passage: float, largeur: float, longueur: float, arene, hauteur: float, y_portique: float):
    """Tribunes latérales et d'extrémité, portiques au-dessus de la route aux deux ouvertures."""
    ax, az = arene

    def dessin(b):
        for s in (-1, 1):
            xa, xb = sorted((s * ax, s * largeur / 2))
            b.box((xa, 0, -longueur / 2), (xb, hauteur, longueur / 2), ROSE, transparency=0.5)
            for t in (-1, 1):
                xa, xb = sorted((s * passage / 2, s * ax))
                za, zb = sorted((t * az, t * longueur / 2))
                b.box((xa, 0, za), (xb, hauteur * 0.7, zb), ROSE, transparency=0.5)
        for t in (-1, 1):
            za, zb = sorted((t * (longueur / 2 - 8), t * longueur / 2))
            b.box((-passage / 2, y_portique, za), (passage / 2, y_portique + 8, zb), ROSE, transparency=0.5)
    return dessin


def _attente_tours(passage: float, larg_tour: float, prof: float, hauteurs, y_passerelle: float):
    def dessin(b):
        for s, h in zip((-1, 1), hauteurs):
            xa, xb = sorted((s * passage / 2, s * (passage / 2 + larg_tour)))
            b.box((xa, 0, -prof), (xb, h, 0), ROSE, transparency=0.5)
        b.box((-passage / 2, y_passerelle, -prof / 2 - 8), (passage / 2, y_passerelle + 12, -prof / 2 + 8), ROSE,
              transparency=0.5)
    return dessin


def _attente_dome(rayon: float, hauteur: float):
    def dessin(b):
        b.cyl((0, hauteur * 0.3, 0), rayon, hauteur * 0.6, ROSE, transparency=0.6)
        b.ball((0, hauteur * 0.6, 0), rayon * 0.7, ROSE, transparency=0.6)
    return dessin


# ---------------------------------------------------------------------------
# Sol « pixel »
# ---------------------------------------------------------------------------

def sol_pixel(b: Builder, x0: float, x1: float, z0: float, z1: float, cell: float, couleur, y_haut: float = 0.0,
              epaisseur: float = 1.0, studs="top", name: str = "Sol", **kw) -> int:
    """Remplit [x0, x1] × [z0, z1] ; couleur(x, z) → (r, g, b), ou ((r, g, b), "Neon") pour une case lumineuse,
    ou None (case vide), évaluée au centre de chaque case ; les cases de même couleur sont fusionnées.
    La dernière rangée et la dernière colonne sont rognées sur x1 et z1 (aucun débordement sur la bande voisine)."""
    nx = int(math.ceil((x1 - x0) / cell - 1e-6))
    nz = int(math.ceil((z1 - z0) / cell - 1e-6))
    if nx <= 0 or nz <= 0:
        return 0
    xs = [min(x0 + i * cell, x1) for i in range(nx)] + [x1]
    zs = [min(z0 + j * cell, z1) for j in range(nz)] + [z1]
    grid = np.empty((nz, nx), dtype=object)
    for j in range(nz):
        for i in range(nx):
            v = couleur((xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2)
            if v is None:
                grid[j, i] = None
            elif isinstance(v[1], str):
                grid[j, i] = (tuple(v[0]), v[1])
            else:
                grid[j, i] = (tuple(v), None)
    n = 0
    for key in {v for v in grid.reshape(-1) if v is not None}:
        col, mat = key
        mask = np.vectorize(lambda v, key=key: v == key)(grid)
        extra = dict(kw)
        st = studs
        if mat:
            extra["material"] = mat
            st = "none"
        for (i, j, w, h) in mask_rects(mask):
            b.box((xs[i], y_haut - epaisseur, zs[j]), (xs[i + w], y_haut, zs[j + h]), col, studs=st, name=name, **extra)
            n += 1
    return n


def _ellipse(x: float, dz: float, a: float, bz: float) -> float:
    return math.hypot(x / a, dz / bz)


def mosaique_place(x: float, z: float):
    """Place des œufs : étincelle à huit branches concaves (quatre longues violettes dans les axes, quatre courtes
    lavande en diagonale) autour d'un cœur orangé, anneaux de dallage, anneau orangé du couchant au bord.
    Motif géométrique générique, aucun emblème. None hors de la place."""
    dx, dz = x, z - Z_PLACE
    d = math.hypot(dx, dz)
    if d >= R_PLACE:
        return None
    if d < 3.5:
        return c("orange_couchant")
    if d < 17:
        # étincelle à quatre branches longues (axes) et quatre courtes (diagonales), branches concaves
        u, v = (dx + dz) / math.sqrt(2), (dx - dz) / math.sqrt(2)
        if abs(dx) * abs(dz) < 30 and max(abs(dx), abs(dz)) < 16.5:
            return c("violet")
        if abs(u) * abs(v) < 16 and max(abs(u), abs(v)) < 13:
            return c("lavande")
        return c("blanc_casse")
    if d < 19:
        return c("violet_fonce")
    if 24 <= d < 26:
        return c("lavande")
    if d < 30:
        return c("arene_claire")
    if d < 32:
        return c("orange_couchant")
    return c("blanc")


def sol_stade(x: float, z: float):
    """Arène du stade : pelouse rayée au centre, piste d'athlétisme ovale, parvis de dalles, sous les tribunes béton."""
    dz = z - Z_PLACE
    ax = abs(x)
    if ax < ARENE[0] and abs(dz) < ARENE[1]:
        e = _ellipse(x, dz, *PISTE)
        if e < 0.84:
            return c("herbe_claire") if math.floor(dz / 8) % 2 == 0 else c("herbe")
        if e < 1.0:
            return c("piste")
        return c("arene_fonce")
    if ax < DEMI_COULOIR + 5:      # ouvertures de la route aux deux bouts du stade
        return c("dalle_fonce") if math.floor(z / 16) % 2 == 0 else c("arene_fonce")
    return c("beton_fonce")


def sol_ville(x: float, z: float):
    """Rue de la ville : chaussée bleu-gris marquée, passages piétons, trottoirs roses à bande podotactile,
    rues latérales à voitures garées, dalles des îlots et des bureaux."""
    ax = abs(x)
    lat = abs(z - Z_CARREFOUR) < DEMI_RUE_LAT
    if ax < DEMI_COULOIR:
        if -54 < z <= -46 or -86 < z <= -78:                              # passages piétons
            return c("marquage") if math.floor((x + 45) / 4) % 2 == 0 and ax < 43 else c("asphalte")
        if lat:
            return c("asphalte_fonce")
        if ax < 1:
            return c("marquage_jaune")
        if 41 <= ax < 43:
            return c("marquage")
        if (13 <= ax < 15 or 27 <= ax < 29) and math.floor(z / 8) % 2 == 0:
            return c("marquage")
        return c("asphalte")
    if ax < X_BORD:
        if lat:     # débouché de la rue latérale : passage piéton
            return c("marquage") if math.floor(z / 4) % 2 == 0 else c("asphalte_fonce")
        if ax < 46:
            return c("bordure")
        if 47 <= ax < 48:
            return c("guidage")
        return c("trottoir_rose") if math.floor(z / 4) % 2 == 0 else c("trottoir_rose_clair")
    # au-delà des façades
    if lat:
        if abs(z - Z_CARREFOUR) < 1 and math.floor(x / 8) % 2 == 0:
            return c("marquage")
        return c("asphalte_fonce")
    if DEMI_RUE_LAT <= abs(z - Z_CARREFOUR) < DEMI_RUE_LAT + 4:          # trottoirs des rues latérales
        return c("trottoir_rose")
    if -26 < z <= -10 and ax < 84:                                       # passage piéton sous le viaduc
        return c("trottoir_rose_clair")
    if ax < 80:
        return c("dalle_claire")
    return c("beton_clair")


def sol_seuil(x: float, z: float):
    """Seuil du portail : dalles bleu nuit, deux lignes lumineuses cyan en travers de la route."""
    ax = abs(x)
    if ax < 52:
        if abs(z - (Z_PORTAIL + 5)) < 1 or abs(z - (Z_PORTAIL - 5)) < 1:
            return (c("neon_cyan"), "Neon")
        return c("marine") if (math.floor(x / 8) + math.floor(z / 4)) % 2 == 0 else c("marine_clair")
    return c("beton")


def sol_avenue(x: float, z: float):
    """Avenue du campus : grandes dalles lavande pâle en quinconce, bordures, trottoirs gris clair, pelouses et
    allées vers les entrées des bâtiments, terrain de sport derrière les bâtiments de cours."""
    ax = abs(x)
    if ax < DEMI_COULOIR:
        if ax >= 41:
            return c("pave_campus_fonce")
        rang = math.floor(z / 12)
        decal = 6 if rang % 2 else 0
        return c("pave_campus") if (math.floor((x + decal) / 12) + rang) % 2 == 0 else c("pave_campus_clair")
    if ax < X_BORD:
        if ax < 47:
            return c("dalle_claire")
        return c("dalle") if math.floor(z / 8) % 2 == 0 else c("dalle_claire")
    return sol_campus(x, z)


ENTREES_CAMPUS = {-1: (-168, -216, -264), 1: (-172, -232, -278)}   # allées vers les entrées (z), par côté
TERRAIN = (134, -200)    # centre du terrain de sport (à droite, derrière les bâtiments de cours)
TERRAIN_SOL = (106, 162, -256, -144)   # rectangle peint en cases de 2 (terrain, piste et marge)


def sol_terrain_sport(x: float, z: float):
    """Terrain de football entouré d'une piste d'athlétisme à coins arrondis (x 108 → 160, z -252 → -148) :
    pelouse rayée, lignes de touche, ligne médiane, rond central, surfaces de réparation. None au-dehors."""
    dx, dz = x - TERRAIN[0], z - TERRAIN[1]
    r = math.hypot(max(0.0, abs(dx) - 10), max(0.0, abs(dz) - 36))
    if r >= 16:
        return None
    if r >= 12:
        return c("piste") if r < 14.5 else c("piste_fonce")
    ax, az = abs(dx), abs(dz)
    ligne = ax >= 20 or az >= 46 or -2 < dz < 0 or 8 <= math.hypot(dx, dz + 1) < 10
    ligne = ligne or (ax < 10 and 38 <= az < 40) or (8 <= ax < 10 and 38 <= az < 46)
    if ligne:
        return c("marquage")
    return c("herbe_claire") if math.floor(dz / 8) % 2 == 0 else c("herbe")


def sol_campus(x: float, z: float):
    """Pelouses du campus (hors couloir), allées, terrain de sport, extérieur de l'enceinte."""
    ax = abs(x)
    s = -1 if x < 0 else 1
    if ax > X_ENCEINTE + 2:
        return c("herbe_fonce")
    if ax < 76 and any(abs(z - ze) < 4 for ze in ENTREES_CAMPUS[s]):
        return c("dalle_claire")
    if 66 <= ax < 70 and Z_FIN_AVENUE < z < Z_AVENUE:
        return c("gravier")
    if s > 0:
        t = sol_terrain_sport(x, z)
        if t is not None:
            return t
    return c("herbe") if (math.floor(x / 32) + math.floor(z / 32)) % 2 == 0 else c("herbe_fonce")


def sol_terrains(x: float, z: float):
    """Terrains d'entraînement : dalles de béton, bandes de danger jaunes et noires au bord de la route,
    rues de la ville factice à gauche, pelouse et allée du dôme à droite."""
    ax = abs(x)
    if ax < DEMI_COULOIR:
        if ax >= 41:
            return c("danger_jaune") if math.floor(z / 4) % 2 == 0 else c("noir")
        return c("dalle") if (math.floor(x / 16) + math.floor(z / 16)) % 2 == 0 else c("dalle_claire")
    if ax < X_BORD:
        return c("dalle_fonce")
    if ax > X_ENCEINTE + 2:
        return sol_campus(x, z)
    if x < 0 and ax < 160:                                               # ville factice : rues tous les 32 studs
        u, v = (ax - 55) % 32, (-z - 296) % 32
        if u < 8 or v < 8:
            return c("asphalte")
        return c("beton")
    if x > 0 and abs(z - Z_DOME) < 4 and ax < 80:                        # allée vers l'entrée du dôme
        return c("dalle_claire")
    return sol_campus(x, z)


def sol_tours(x: float, z: float):
    """Parvis des tours jumelles : dalles blanches, deux filets violets le long de la route, pelouses."""
    ax = abs(x)
    if ax < DEMI_COULOIR:
        if 17 <= ax < 21:
            return c("violet")
        return c("dalle_claire") if (math.floor(x / 16) + math.floor(z / 16)) % 2 == 0 else c("blanc_casse")
    if ax < 108:
        return c("dalle_claire")
    return sol_campus(x, z)


def couleur_sol(x: float, z: float):
    m = mosaique_place(x, z)
    if m:
        return m
    if Z_FIN_STADE <= z <= Z_STADE and abs(x) < X_STADE:
        return sol_stade(x, z)
    if z > Z_PORTAIL + EP_PORTAIL / 2:
        return sol_ville(x, z)
    if z > Z_AVENUE:
        return sol_seuil(x, z)
    if z > Z_FIN_AVENUE:
        return sol_avenue(x, z)
    if z > Z_FIN_TERRAINS:
        return sol_terrains(x, z)
    if z > Z_FIN_STADE:
        return sol_campus(x, z)          # côtés du stade au-delà de |x| = 140
    return sol_tours(x, z)


def sol(b: Builder) -> None:
    """Tout le sol, en bandes de z et de x avec une taille de case adaptée (2 près du joueur, 8 au loin)."""
    z_fin = Z_SORTIE - 4
    zp_haut, zp_bas = Z_PLACE + R_PLACE + 2, Z_PLACE - R_PLACE - 2
    # (z0, z1, cellule de la route et des trottoirs, cellule des côtés)
    bandes = [
        (Z_PORTAIL + EP_PORTAIL / 2, Z_APPROCHE, 2, 4),
        (Z_AVENUE, Z_PORTAIL + EP_PORTAIL / 2, 2, 8),
        (Z_FIN_AVENUE, Z_AVENUE, 4, 8),
        (Z_FIN_TERRAINS, Z_FIN_AVENUE, 4, 8),
        (Z_FIN_STADE, Z_STADE, 4, 8),
        (z_fin, Z_FIN_STADE, 4, 8),
    ]
    with b.group("Sol/Route"):
        for z0, z1, cr, _ in bandes:
            if z0 == Z_FIN_STADE:          # stade : la place des œufs en cases de 2, le reste en cases de 4
                sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, zp_haut, z1, cr, couleur_sol)
                sol_pixel(b, -36, 36, zp_bas, zp_haut, 2, couleur_sol)
                for s in (-1, 1):
                    xa, xb = sorted((s * 36, s * DEMI_COULOIR))
                    sol_pixel(b, xa, xb, zp_bas, zp_haut, 3, couleur_sol)
                sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, z0, zp_bas, cr, couleur_sol)
            else:
                sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, z0, z1, cr, couleur_sol)
    with b.group("Sol/Trottoirs"):
        for z0, z1, cr, _ in bandes:
            for s in (-1, 1):
                xa, xb = sorted((s * DEMI_COULOIR, s * X_BORD))
                if z0 == Z_FIN_STADE:
                    sol_pixel(b, xa, xb, z0, z1, 4, couleur_sol)
                else:
                    sol_pixel(b, xa, xb, z0, z1, 1 if cr == 2 else 2, couleur_sol)
    with b.group("Sol/Cotes"):
        for z0, z1, _, cc in bandes:
            for s in (-1, 1):
                if z0 == Z_FIN_STADE:      # bord de l'arène (piste ovale) en cases de 4, dessous des tribunes en 8
                    xa, xb = sorted((s * X_BORD, s * 79))
                    sol_pixel(b, xa, xb, z0, z1, 4, couleur_sol)
                    xa, xb = sorted((s * 79, s * X_FOND))
                elif z0 == Z_FIN_AVENUE and s > 0:   # terrain de sport en cases de 2, le reste en cases de 8
                    tx0, tx1, tz0, tz1 = TERRAIN_SOL
                    sol_pixel(b, X_BORD, tx0, z0, z1, cc, couleur_sol)
                    sol_pixel(b, tx0, tx1, tz0, tz1, 2, couleur_sol)
                    sol_pixel(b, tx0, tx1, z0, tz0, cc, couleur_sol)
                    sol_pixel(b, tx0, tx1, tz1, z1, 4, couleur_sol)
                    xa, xb = tx1, X_FOND
                else:
                    xa, xb = sorted((s * X_BORD, s * X_FOND))
                sol_pixel(b, xa, xb, z0, z1, cc, couleur_sol)


# ---------------------------------------------------------------------------
# 1. Rue de la ville (z 0 → -124)
# ---------------------------------------------------------------------------

BOUTIQUES = {
    # côté : [(îlot, largeur le long de la rue, profondeur, paramètres)] ; îlot A z -26 → -51, îlot B z -81 → -122
    -1: [("A", 14, 16, {"variant": 0, "etages": 3, "enseigne": "CAFÉ"}),
         ("A", 10, 14, {"variant": 1, "etages": 2, "enseigne": "FLEURS"}),
         ("B", 14, 16, {"variant": 2, "etages": 4, "enseigne": "LIVRES"}),
         ("B", 16, 18, {"variant": 3, "etages": 1, "enseigne": "MARCHÉ"}),
         ("B", 9, 14, {"variant": 1, "etages": 3, "enseigne": "RAMEN"})],
    1: [("A", 12, 16, {"variant": 2, "etages": 3, "enseigne": "BOULANGERIE"}),
        ("A", 12, 16, {"variant": 0, "etages": 2, "enseigne": "SPORT"}),
        ("B", 16, 18, {"variant": 3, "etages": 1, "enseigne": "PHARMACIE"}),
        ("B", 14, 14, {"variant": 0, "etages": 4, "enseigne": "CAFÉ"}),
        ("B", 9, 14, {"variant": 1, "etages": 2, "enseigne": None})],
}

BUREAUX = [
    # (x, z, largeur le long de z, profondeur, hauteur, variante, simple)
    (-98, -39, 24, 24, 62, 0, False), (-100, -101, 36, 26, 84, 1, False),
    (-150, -40, 24, 22, 50, 2, True), (-152, -100, 30, 24, 72, 0, True),
    (98, -39, 24, 24, 74, 1, False), (100, -101, 36, 26, 58, 2, False),
    (150, -40, 24, 22, 66, 0, True), (152, -100, 30, 24, 92, 1, True),
    # troisième rang, plus bas, devant la ville lointaine
    (-188, -38, 22, 20, 40, 1, True), (-188, -104, 26, 20, 54, 2, True),
    (188, -38.5, 22, 20, 46, 2, True), (188, -102, 26, 20, 38, 0, True),
]


def ville(b: Builder) -> None:
    place(b, "ville", "viaduc_train", (0, 0, Z_VIADUC), group="Monuments/Viaduc",
          attente=_attente_viaduc(2 * X_FOND, 36, 112), longueur=2 * X_FOND, hauteur=36, passage=112)
    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        z_ilot = {"A": Z_RUE_A[0], "B": Z_RUE_B[0]}
        for i, (ilot, larg, prof, params) in enumerate(BOUTIQUES[s]):
            z = z_ilot[ilot]
            zc = z - larg / 2
            x = s * (X_BORD + prof / 2)
            place(b, "ville", "boutique", (x, 0, zc), yaw=face_couloir(x), group=f"Ville/{cote}/Boutique{i}",
                  emprise=(larg, prof, 9 + 6.5 * (params["etages"] - 1)), largeur=larg, profondeur=prof, **params)
            z_ilot[ilot] = z - larg - 1
        assert z_ilot["A"] + 1 >= Z_RUE_A[1] and z_ilot["B"] + 1 >= Z_RUE_B[1], (s, z_ilot)
    for i, (x, z, larg, prof, h, v, simple) in enumerate(BUREAUX):
        place(b, "ville", "immeuble_bureaux", (x, 0, z), yaw=face_couloir(x), group=f"Ville/Bureaux{i}",
              emprise=(larg, prof, h), variant=v, largeur=larg, profondeur=prof, hauteur=h, simple=simple)
    # voitures garées dans les rues latérales (hors couloir)
    k = 0
    for s in (-1, 1):
        for j, xa in enumerate((66, 84, 126, 144)):
            for t, dz in ((1, 6.5), (-1, -6.5)):
                if (j + (t > 0)) % 2:
                    continue
                place(b, "mobilier", "voiture", (s * xa, 0, Z_CARREFOUR + dz), yaw=90 if t > 0 else -90,
                      group=f"Ville/Voitures/V{k:02d}", variant=k % 6 if k % 5 else 3)
                k += 1
    mobilier_ville(b)


def mobilier_ville(b: Builder) -> None:
    """Lampadaires, feux, abribus, arbres d'alignement, distributeurs, terrasse, lignes électriques."""
    for s in (-1, 1):
        c_ = "G" if s < 0 else "D"
        x = s * 50.5
        for i, z in enumerate((9, -40, -96, -118)):
            place(b, "mobilier", "lampadaire_ville", (x, 0, z), yaw=face_couloir(x), group=f"Ville/Mobilier/Lampe{c_}{i}",
                  variant=1)
        for i, z in enumerate((Z_CARREFOUR + DEMI_RUE_LAT + 2, Z_CARREFOUR - DEMI_RUE_LAT - 2)):
            place(b, "mobilier", "feu_tricolore", (s * 51, 0, z), yaw=face_couloir(x), group=f"Ville/Mobilier/Feu{c_}{i}",
                  variant=i)
        for i, z in enumerate((-24, -88, -108) if s < 0 else (-30, -88, -104)):
            place(b, "mobilier", "arbre_rue", (s * 50.3, 0, z), group=f"Ville/Mobilier/Arbre{c_}{i}", variant=(i + (s > 0)) % 2)
        place(b, "mobilier", "abribus", (s * 51.5, 0, 0), yaw=face_couloir(x), group=f"Ville/Mobilier/Abribus{c_}",
              variant=0 if s < 0 else 2)
        place(b, "mobilier", "distributeur", (s * 53.5, 0, -10.5), yaw=face_couloir(x), group=f"Ville/Mobilier/Distrib{c_}",
              variant=1 if s < 0 else 3, nombre=2)
        place(b, "mobilier", "poubelle", (s * 53, 0, -15.2), yaw=face_couloir(x), group=f"Ville/Mobilier/Poubelle{c_}",
              variant=0)
        place(b, "mobilier", "jardiniere", (s * 52, 0, 14), yaw=face_couloir(x), group=f"Ville/Mobilier/Jardiniere{c_}",
              variant=1 if s < 0 else 3)
        # lignes électriques le long des rues latérales (de |x| = 60 vers l'extérieur)
        for j, dz in enumerate((DEMI_RUE_LAT + 2.5, -DEMI_RUE_LAT - 2.5)):
            place(b, "mobilier", "ligne_electrique", (s * 60, 0, Z_CARREFOUR + dz), yaw=-90 * s,
                  group=f"Ville/Mobilier/Ligne{c_}{j}", longueur=60, portee=30, variant=j)
    place(b, "mobilier", "terrasse", (-50.2, 0, -33), group="Ville/Mobilier/TerrasseCafe", variant=1)
    place(b, "mobilier", "terrasse", (50.5, 0, -112), group="Ville/Mobilier/TerrasseCafe2", variant=0)


# ---------------------------------------------------------------------------
# 2. Portail de sécurité et mur d'enceinte (z = -132)
# ---------------------------------------------------------------------------

def portail(b: Builder) -> None:
    place(b, "ville", "portail_securite", (0, 0, Z_PORTAIL), group="Monuments/Portail",
          attente=_attente_portail(100, 48, X_ENCEINTE, 14, EP_PORTAIL),
          ouverture=100, hauteur=48, profondeur=EP_PORTAIL, mur=X_ENCEINTE, h_mur=14)


# ---------------------------------------------------------------------------
# 3. Avenue du campus (z -140 → -296)
# ---------------------------------------------------------------------------

def avenue(b: Builder) -> None:
    # dortoirs de brique à gauche (première rangée face au couloir, seconde rangée simplifiée en retrait)
    for i, (z, v) in enumerate(((-168, 0), (-216, 1), (-264, 2))):
        place(b, "campus", "dortoir", (-85, 0, z), yaw=-90, group=f"Campus/Dortoirs/D{i}", emprise=(40, 22, 30),
              variant=v, largeur=40, profondeur=22, etages=4)
    for i, (z, v) in enumerate(((-192, 1), (-240, 0))):
        place(b, "campus", "dortoir", (-128, 0, z), yaw=-90, group=f"Campus/Dortoirs/R{i}", emprise=(36, 20, 30),
              variant=v, largeur=36, profondeur=20, etages=4, simple=True)
    # bâtiments de cours vitrés et halle d'entraînement à droite
    place(b, "campus", "batiment_cours", (86, 0, -172), yaw=90, group="Campus/Cours/C0", emprise=(52, 24, 26),
          variant=0, largeur=52, profondeur=24, hauteur=26)
    place(b, "campus", "batiment_cours", (86, 0, -232), yaw=90, group="Campus/Cours/C1", emprise=(52, 24, 30),
          variant=1, largeur=52, profondeur=24, hauteur=30)
    place(b, "campus", "halle_entrainement", (92, 0, -277), yaw=90, group="Campus/Halle", emprise=(36, 36, 22),
          variant=0, largeur=36, profondeur=36, hauteur=22)
    # haies taillées (allées vers les entrées), conifères à gauche, arbres ronds à droite
    for s in (-1, 1):
        c_ = "G" if s < 0 else "D"
        zs = sorted(ENTREES_CAMPUS[s], reverse=True)
        bornes = [Z_AVENUE - 2] + [v for ze in zs for v in (ze + 4.5, ze - 4.5)] + [Z_FIN_AVENUE + 2]
        for i in range(0, len(bornes), 2):
            za, zb = bornes[i], bornes[i + 1]
            L = za - zb
            if L < 4:
                continue
            place(b, "vegetation", "haie", (s * 57, 0, (za + zb) / 2), yaw=90, group=f"Campus/Haies/H{c_}{i // 2}",
                  emprise=(L, 3, 3), longueur=L, hauteur=3.5, variant=i // 2 % 2)
        if s < 0:
            # rangée serrée de conifères en colonnes (référence 2), interrompue au droit des allées
            z = Z_AVENUE - 6
            k = 0
            while z > Z_FIN_AVENUE + 4:
                if all(abs(z - ze) > 6 for ze in zs):
                    place(b, "vegetation", "conifere", (-62.5, 0, z), group=f"Campus/Coniferes/K{k:02d}",
                          emprise=(4, 4, 14), variant=(0, 2, 1, 0, 1)[k % 5], taille=(1.0, 1.15, 1.3, 1.1, 1.2)[k % 5])
                    k += 1
                z -= 6
        else:
            # rangée d'arbres ronds (houppiers qui se touchent), interrompue au droit des allées
            z, k = Z_AVENUE - 7, 0
            while z > Z_FIN_AVENUE + 4:
                if all(abs(z - ze) > 7 for ze in zs):
                    place(b, "vegetation", "arbre_rond", (63.5, 0, z), group=f"Campus/Arbres/A{k:02d}",
                          emprise=(9, 9, 14), variant=(0, 1, 2, 1)[k % 4], taille=(0.95, 1.05, 0.9, 1.0)[k % 4])
                    k += 1
                z -= 10
        # lampadaires, bancs, poubelles
        for i, z in enumerate((-152, -184, -216, -248, -280)):
            x = s * 50
            place(b, "mobilier", "lampadaire_campus", (x, 0, z), yaw=face_couloir(x), group=f"Campus/Mobilier/Lampe{c_}{i}",
                  variant=0)
        for i, z in enumerate((-200, -232, -262)):
            x = s * 52.5
            place(b, "mobilier", "banc", (x, 0, z), yaw=face_couloir(x), group=f"Campus/Mobilier/Banc{c_}{i}",
                  variant=i % 3)
        # bannières de campus entre les lampadaires (couleurs alternées, motifs abstraits)
        for i, z in enumerate((-168, -208, -241, -272)):
            x = s * 51
            place(b, "mobilier", "banniere", (x, 0, z), yaw=face_couloir(x), group=f"Campus/Mobilier/Banniere{c_}{i}",
                  variant=(i + (s > 0)) % 4, hauteur=12)
        place(b, "mobilier", "poubelle", (s * 53, 0, -237.5), yaw=face_couloir(s), group=f"Campus/Mobilier/Poubelle{c_}",
              variant=1)
        place(b, "mobilier", "totem", (s * 51.5, 0, Z_AVENUE - 8), yaw=face_couloir(s), group=f"Campus/Mobilier/Totem{c_}",
              texte="CAMPUS", variant=0)
    place(b, "mobilier", "panneau_direction", (51.5, 0, -160), yaw=face_couloir(1), group="Campus/Mobilier/Direction",
          textes=("STADE", "CAMPUS", "DORTOIRS"))
    # parterres de fleurs devant les dortoirs, au pied des haies
    for i, z in enumerate((-190, -240)):
        place(b, "vegetation", "parterre", (-67, 0, z), yaw=-90, group=f"Campus/Parterres/P{i}", emprise=(12, 3, 1),
              longueur=12, largeur=3, variant=i)
    jardins(b)


# Arbres des pelouses du campus : (x, z, variante, taille) ; variante 3 = cerisier rose
JARDINS = [
    # entre les deux rangées de dortoirs (x -117 → -98)
    (-107.5, -150, 3, 1.0), (-107.5, -162, 0, 0.9), (-107.5, -176, 3, 1.05), (-107.5, -190, 1, 0.95),
    (-107.5, -204, 3, 0.95), (-107.5, -218, 2, 1.0), (-107.5, -232, 3, 1.05), (-107.5, -246, 0, 0.95),
    (-107.5, -260, 3, 1.0), (-107.5, -274, 1, 1.0), (-107.5, -288, 3, 0.9),
    # derrière la seconde rangée (x -159 → -140), devant et derrière elle
    (-150, -186, 0, 1.0), (-150, -214, 3, 1.05), (-150, -242, 1, 0.95),
    (-128, -153, 3, 1.1), (-142, -163, 2, 0.95), (-120, -164, 0, 0.85),
    (-126, -273, 3, 1.1), (-142, -282, 0, 1.0), (-118, -287, 2, 0.9),
    # pelouse au sud du terrain de sport, entre la halle et le dôme
    (122, -266, 3, 1.0), (138, -278, 0, 1.05), (151, -266, 1, 0.95), (118, -286, 2, 0.9),
    # bords du terrain
    (104, -150, 3, 0.9), (104, -250, 3, 0.9),
]


def but_foot(b: Builder) -> None:
    """But de football (8 × 4), ouverture vers -Z local, filet translucide derrière (+Z)."""
    with b.group("But"):
        for sx in (-1, 1):
            b.box((sx * 4 - 0.3, 0, -0.3), (sx * 4 + 0.3, 4, 0.3), c("blanc"), name="Poteau")
        b.box((-4.3, 4, -0.3), (4.3, 4.6, 0.3), c("blanc"), name="Barre")
        b.box((-3.7, 0, 0.3), (3.7, 3.7, 2.6), c("blanc_casse"), transparency=0.55, collide=False, shadow=False,
              name="Filet")


def gradins(b: Builder, longueur: float = 48.0, variant: int = 0) -> None:
    """Petite tribune de terrain (8 de profondeur, avant -Z local) : trois marches de béton à assises de couleur
    studdées, garde-corps vitré, auvent de verre sur trois poteaux blancs à liseré cyan."""
    L = longueur
    sieges = ("siege_violet", "siege_lavande", "siege_bleu")
    with b.group("Gradins"):
        bords_z = (-4.0, -1.5, 1.0, 4.0)
        for i in range(3):
            y = 1.2 * (i + 1)
            b.box((-L / 2, 0, bords_z[i]), (L / 2, y - 0.4, bords_z[i + 1]), c("beton_tribune"), name="Marche")
            b.box((-L / 2 + 0.5, y - 0.4, bords_z[i] + 0.3), (L / 2 - 0.5, y, bords_z[i + 1]),
                  c(sieges[(i + variant) % 3]), studs="top", name="Assise")
        b.box((-L / 2 + 0.5, 3.6, 3.6), (L / 2 - 0.5, 5.0, 3.9), c("vitre_claire"), material="Glass", transparency=0.4,
              collide=False, name="GardeCorps")
        for x in (-L / 2 + 1, 0.0, L / 2 - 1):
            b.box((x - 0.4, 0, 4.0), (x + 0.4, 9.6, 4.8), c("blanc"), name="Poteau")
        b.box((-L / 2, 9.6, -3.0), (L / 2, 10.0, 4.8), c("verre_canopee"), material="Glass", transparency=0.35,
              collide=False, name="Auvent")
        b.box((-L / 2, 9.4, -3.3), (L / 2, 10.2, -3.0), c("blanc"), collide=False, name="RiveAuvent")
        b.box((-L / 2, 9.2, -3.4), (L / 2, 9.4, -3.1), c("neon_cyan"), material="Neon", collide=False, shadow=False,
              name="Liseré")


def jardins(b: Builder) -> None:
    """Pelouses du campus : arbres et cerisiers entre les dortoirs, terrain de sport (buts, petite tribune)."""
    for i, (x, z, v, t) in enumerate(JARDINS):
        place(b, "vegetation", "arbre_rond", (x, 0, z), group=f"Campus/Jardins/A{i:02d}", emprise=(9, 9, 14),
              variant=v, taille=t)
    with b.at((TERRAIN[0], 0, TERRAIN[1] + 47), group="Campus/Terrain/ButN"):
        but_foot(b)
    with b.at((TERRAIN[0], 0, TERRAIN[1] - 47), yaw=180, group="Campus/Terrain/ButS"):
        but_foot(b)
    with b.at((103.5, 0, TERRAIN[1]), yaw=-90, group="Campus/Terrain/Gradins"):
        gradins(b, longueur=48, variant=0)
    for i, z in enumerate((-170, -230)):
        place(b, "mobilier", "banc", (101, 0, z), yaw=-90, group=f"Campus/Terrain/Banc{i}", variant=i)
    place(b, "entrainement", "cible", (114, 0, -262), yaw=-90, group="Campus/Terrain/Cible", emprise=(4, 1, 6), variant=1)


# ---------------------------------------------------------------------------
# 4. Terrains d'entraînement (z -296 → -400)
# ---------------------------------------------------------------------------

Z_DOME = -347.5          # le bord de la verrière (rayon 52,3) s'arrête à 0,2 du stade (z = -400)
X_DOME = 124
R_DOME = 52

FACTICES = [
    # (x, z, largeur, profondeur, hauteur, dégâts 0-2, variante)
    (-75, -316, 20, 20, 26, 0, 0), (-75, -380, 20, 18, 18, 2, 1), (-107, -316, 22, 20, 34, 1, 2),
    (-107, -348, 20, 20, 22, 0, 1), (-139, -316, 20, 18, 16, 2, 0), (-139, -380, 22, 20, 30, 0, 2),
    (-107, -380, 18, 18, 14, 1, 0),
]


def terrains(b: Builder) -> None:
    place(b, "entrainement", "dome_entrainement", (X_DOME, 0, Z_DOME), yaw=90, group="Monuments/Dome",
          attente=_attente_dome(R_DOME, 50), rayon=R_DOME, hauteur=50)
    for i, (x, z, larg, prof, h, deg, v) in enumerate(FACTICES):
        place(b, "entrainement", "immeuble_factice", (x, 0, z), yaw=face_couloir(x), group=f"Entrainement/Ville/F{i}",
              emprise=(larg, prof, h), variant=v, largeur=larg, profondeur=prof, hauteur=h, degats=deg)
    for i, (x, z, v) in enumerate(((-75, -348, 0), (-139, -348, 1), (-90, -394.5, 2), (-128, -300, 1))):
        place(b, "entrainement", "decombres", (x, 0, z), yaw=(i * 37) % 360, group=f"Entrainement/Decombres/D{i}",
              emprise=(10, 10, 3), variant=v)
    for i, (x, z, v, yaw) in enumerate(((-60, -326, 0, -90), (-91, -340, 1, -60), (-60, -372, 3, -90),
                                        (-123, -364, 2, -120), (-120, -395.5, 0, -30))):
        place(b, "entrainement", "robot_entrainement", (x, 0, z), yaw=yaw, group=f"Entrainement/Robots/R{i}",
              emprise=(6, 6, 10), variant=v)
    for i, (x, z, v) in enumerate(((-66, -302, 0), (-66, -394, 1))):
        place(b, "entrainement", "cible", (x, 0, z), yaw=face_couloir(x), group=f"Entrainement/Cibles/C{i}",
              emprise=(4, 1, 6), variant=v)
    # grillage le long de la ville factice (ouvert au droit des rues)
    for i, (za, zb) in enumerate(((-304, -328), (-336, -360), (-368, -392))):
        place(b, "mobilier", "cloture", (-56.5, 0, (za + zb) / 2), yaw=90, group=f"Entrainement/Grillage/G{i}",
              longueur=za - zb, variant=0)
    # bande de matériel entre la route et le dôme (x 57 → 70), l'allée du dôme (z -344 → -352) reste libre
    bande = [("mobilier", "plots", 60, -301, {"nombre": 4}), ("mobilier", "pneus", 61, -309, {}),
             ("mobilier", "haies_athletisme", 61, -318, {}), ("entrainement", "robot_entrainement", 62, -328, {"variant": 2}),
             ("entrainement", "cible", 62, -337, {"variant": 2}), ("mobilier", "sac_frappe", 61, -360, {}),
             ("vegetation", "rocher", 64, -370, {"variant": 0}), ("mobilier", "caisses", 61, -380, {"variant": 1}),
             ("entrainement", "cible", 62, -390, {"variant": 0}), ("mobilier", "plots", 60, -394.5, {"variant": 1})]
    for i, (mod, fn, x, z, kw) in enumerate(bande):
        place(b, mod, fn, (x, 0, z), yaw=face_couloir(x), group=f"Entrainement/Materiel/M{i:02d}", emprise=(5, 5, 6), **kw)
    for s in (-1, 1):
        c_ = "G" if s < 0 else "D"
        for i, z in enumerate((-312, -344, -376)):
            x = s * 50.5
            place(b, "mobilier", "lampadaire_ville", (x, 0, z), yaw=face_couloir(x), group=f"Entrainement/Lampe{c_}{i}",
                  variant=2)
        place(b, "mobilier", "totem", (s * 51.5, 0, Z_FIN_AVENUE - 6), yaw=face_couloir(s),
              group=f"Entrainement/Totem{c_}", texte="ENTRAÎNEMENT", variant=1)
    place(b, "vegetation", "rocher", (-150, 0, -396), group="Entrainement/Rocher", emprise=(4, 4, 3), variant=1)


# ---------------------------------------------------------------------------
# 5. Stade et place des œufs (z -400 → -528)
# ---------------------------------------------------------------------------

def stade(b: Builder) -> None:
    place(b, "entrainement", "stade", (0, 0, Z_PLACE), group="Monuments/Stade",
          attente=_attente_stade(104, 2 * X_STADE, 2 * DEMI_STADE_Z, ARENE, 36, 38),
          passage=104, largeur=2 * X_STADE, longueur=2 * DEMI_STADE_Z, arene=ARENE, hauteur=36, y_portique=38)
    # bornes lumineuses autour de la place (hors couloir), bannières devant les ouvertures
    k = 0
    for a in range(0, 360, 30):
        x = (R_PLACE + 4) * math.sin(math.radians(a + 15))
        z = Z_PLACE + (R_PLACE + 4) * math.cos(math.radians(a + 15))
        if abs(x) < 48:
            continue
        place(b, "mobilier", "borne_lumineuse", (x, 0, z), group=f"Place/Bornes/B{k:02d}", variant=k % 3)
        k += 1
    for s in (-1, 1):
        for i, z in enumerate((Z_STADE + 5, Z_FIN_STADE - 2.5)):
            x = s * 51
            place(b, "mobilier", "banniere", (x, 0, z), yaw=face_couloir(x), group=f"Place/Bannieres/B{'GD'[s > 0]}{i}",
                  variant=i * 2 + (s > 0), hauteur=13)


# ---------------------------------------------------------------------------
# 6. Tours jumelles et sortie (z -536 → -574)
# ---------------------------------------------------------------------------

def tours(b: Builder) -> None:
    place(b, "campus", "tours_jumelles", (0, 0, Z_TOURS), group="Monuments/Tours",
          attente=_attente_tours(PASSAGE_TOURS, 44, Z_TOURS - Z_SORTIE, (120, 134), Y_PASSERELLE),
          passage=PASSAGE_TOURS, largeur_tour=44, profondeur=Z_TOURS - Z_SORTIE, hauteurs=(120, 134),
          y_passerelle=Y_PASSERELLE)
    for s in (-1, 1):
        place(b, "mobilier", "totem", (s * 51.5, 0, Z_FIN_STADE - 8), yaw=face_couloir(s), group=f"Tours/Totem{'GD'[s > 0]}",
              texte="ACADÉMIE", variant=0, hauteur=9)
        for i, z in enumerate((-544, -557, -570)):
            place(b, "mobilier", "borne_lumineuse", (s * 50, 0, z), group=f"Tours/Bornes{'GD'[s > 0]}{i}", variant=1)


# ---------------------------------------------------------------------------
# Bords : mur d'enceinte, ceinture d'arbres, ville lointaine, abords
# ---------------------------------------------------------------------------

def bords(b: Builder) -> None:
    # mur d'enceinte latéral (le mur avant fait partie du portail), en tronçons de 31 studs
    for s in (-1, 1):
        c_ = "G" if s < 0 else "D"
        z, k = Z_PORTAIL - 2.0, 0          # raccord contre la pile d'angle 4 × 4 du mur avant (z -134 → -130)
        while z > Z_SORTIE + 1:
            L = min(31.0, z - Z_SORTIE)
            place(b, "ville", "mur_campus", (s * X_ENCEINTE, 0, z - L / 2), yaw=face_couloir(s * X_ENCEINTE),
                  group=f"Enceinte/{c_}/M{k:02d}", emprise=(L, 3, 12), longueur=L, hauteur=12, variant=k % 3)
            z -= L
            k += 1
    # ceinture d'arbres le long du mur, jusqu'aux angles des tours (sauf à droite derrière le dôme)
    k = 0
    for s in (-1, 1):
        z = Z_AVENUE - 22
        while z > Z_SORTIE + 16:
            libre = not (s > 0 and (Z_FIN_TERRAINS - 6 < z < Z_FIN_AVENUE + 6))
            if libre:
                place(b, "vegetation", "bosquet", (s * 168, 0, z), yaw=face_couloir(s), group=f"Enceinte/Bosquets/B{k:02d}",
                      emprise=(36, 18, 18), variant=k % 3, largeur=36, profondeur=18)
                k += 1
            z -= 44
    # derrière le dôme : rangée de conifères entre la verrière et le mur (le dôme touche presque l'enceinte)
    z, k = Z_FIN_AVENUE + 22, 0
    while z > Z_FIN_TERRAINS - 4:
        place(b, "vegetation", "conifere", (179.5, 0, z), group=f"Enceinte/Coniferes/K{k:02d}", emprise=(4, 4, 14),
              variant=(1, 0, 2)[k % 3], taille=(1.25, 1.1, 1.3)[k % 3])
        z -= 7.5
        k += 1
    # ville lointaine derrière l'enceinte et derrière les bureaux (trouée au droit des bouts du viaduc)
    rng = np.random.default_rng(21)
    k = 0
    z_viaduc = (Z_VIADUC + 8, Z_VIADUC - 8)
    for s in (-1, 1):
        z = Z_APPROCHE + 4
        while True:
            h = float(rng.choice([44, 56, 68, 82, 96, 110]))
            larg = float(rng.choice([20, 24, 28]))
            if z - larg < Z_SORTIE - 4:
                break
            if z > z_viaduc[1] and z - larg < z_viaduc[0]:
                z = z_viaduc[1]
            place(b, "ville", "silhouette_lointaine", (s * 218, 0, z - larg / 2), yaw=face_couloir(s), group=f"Lointain/S{k:02d}",
                  emprise=(larg, 18, h), variant=k % 4, largeur=larg, profondeur=18, hauteur=h)
            z -= larg + rng.uniform(6, 14)
            k += 1
    # arbres : abords de l'entrée, flancs du stade, parvis des tours
    for s in (-1, 1):
        pts = [(66, 18), (66, 2), (150, -424), (150, -464), (150, -504), (114, -546), (114, -566),
               (131, -556), (147, -543), (148, -568)]
        for i, (x, z) in enumerate(pts):
            place(b, "vegetation", "arbre_rond", (s * x, 0, z), group=f"Abords/{'GD'[s > 0]}{i}", emprise=(9, 9, 14),
                  variant=3 if i in (6, 7) else (i + (s > 0)) % 3, taille=0.9 + 0.1 * (i % 3))
        place(b, "vegetation", "bosquet", (s * 168, 0, -554), yaw=face_couloir(s), group=f"Abords/Bosquet{'GD'[s > 0]}",
              emprise=(36, 18, 18), variant=1 if s < 0 else 2, largeur=36, profondeur=18)


def reperes(b: Builder) -> None:
    """Pièces invisibles utiles au jeu : zone des œufs, entrée, sortie, couloir."""
    inv = dict(transparency=1.0, collide=False, shadow=False)
    with b.group("Reperes"):
        b.box((-R_PLACE, 0, Z_PLACE - R_PLACE), (R_PLACE, 1, Z_PLACE + R_PLACE), "#ffffff", name="ZoneOeufs", **inv)
        b.box((-DEMI_COULOIR, 0, Z_ENTREE), (DEMI_COULOIR, 1, Z_ENTREE + 6), "#ffffff", name="Entree", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE - 4), (DEMI_COULOIR, 1, Z_SORTIE + 2), "#ffffff", name="Sortie", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE), (DEMI_COULOIR, 1, Z_ENTREE), "#ffffff", name="Couloir", **inv)


def decouper(b: Builder, prefixes=("Sol/", "Enceinte/", "Lointain/", "Monuments/Stade", "Monuments/Viaduc",
                                    "Monuments/Portail"), taille: float = 64) -> None:
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
    sol(b)
    ville(b)
    portail(b)
    avenue(b)
    terrains(b)
    stade(b)
    tours(b)
    bords(b)
    reperes(b)
    decouper(b)
    return b


# ---------------------------------------------------------------------------
# Contrôles
# ---------------------------------------------------------------------------

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
    """Toute pièce (solide ou non) au-dessus de |x| < 46 et sous `y_min` : la caméra Roblox sauterait en
    passant dessous, et rien ne doit traîner dans le couloir."""
    out = []
    for p in b.parts:
        if p.group.startswith(("Sol", "Reperes")):
            continue
        lo, hi = _bornes(p)
        if lo[0] < X_LIBRE - 0.01 and hi[0] > -X_LIBRE + 0.01 and lo[1] < y_min and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name, round(lo[1], 1)))
    return out


def chevauchements(b: Builder, tol: float = 0.05) -> list:
    """Paires de poses dont des pièces se pénètrent de plus de `tol` sur les trois axes (boîtes englobantes
    monde, grille de hachage en XZ). Les pièces posées directement par zone.py comptent par groupe ; le sol et
    les repères sont ignorés. Renvoie [(groupe A, groupe B, nb de paires de pièces, pénétration max, végétation
    des deux côtés ?)], du plus profond au moins profond."""
    n = len(b.parts)
    owner = np.full(n, -1)
    poses = list(_POSES)
    for k, (g, n0, n1, m, f) in enumerate(poses):
        owner[n0:n1] = k
    pseudo = {}
    for i, p in enumerate(b.parts):
        if owner[i] < 0 and not p.group.startswith(("Sol", "Reperes")):
            if p.group not in pseudo:
                pseudo[p.group] = len(poses)
                poses.append((p.group, i, i, "zone", "direct"))
            owner[i] = pseudo[p.group]
    lo = np.zeros((n, 3))
    hi = np.zeros((n, 3))
    for i, p in enumerate(b.parts):
        lo[i], hi[i] = _bornes(p)
    cell = 12.0
    grid = defaultdict(list)
    for i in np.where(owner >= 0)[0]:
        for gx in range(math.floor(lo[i, 0] / cell), math.floor(hi[i, 0] / cell) + 1):
            for gz in range(math.floor(lo[i, 2] / cell), math.floor(hi[i, 2] / cell) + 1):
                grid[(gx, gz)].append(i)
    paires: dict = {}
    vus = set()
    for idx in grid.values():
        if len(idx) < 2:
            continue
        arr = np.array(idx)
        for u, i in enumerate(arr):
            m = owner[arr] != owner[i]
            if not m.any():
                continue
            pen = np.minimum(hi[arr[m]], hi[i]) - np.maximum(lo[arr[m]], lo[i])
            for j, pn in zip(arr[m][(pen > tol).all(1)], pen[(pen > tol).all(1)]):
                pk = (min(i, j), max(i, j))
                if pk in vus:
                    continue
                vus.add(pk)
                key = (min(owner[i], owner[j]), max(owner[i], owner[j]))
                e = paires.setdefault(key, [0, 0.0])
                e[0] += 1
                e[1] = max(e[1], float(pn.min()))
    out = []
    for (k1, k2), (nb, pmax) in paires.items():
        veg = poses[k1][3] == "vegetation" and poses[k2][3] == "vegetation"
        out.append((poses[k1][0], poses[k2][0], nb, round(pmax, 2), veg))
    return sorted(out, key=lambda t: -t[3])


def hors_budget() -> list:
    out = []
    for (module, fn, params, n, group) in _COMPTES:
        bud = _budget(module, fn, params)
        if n > bud:
            out.append((group, f"{module}.{fn}", n, bud))
    return out


def meta() -> dict:
    return {"nom": "ZoneMyHeroAcademia", "version": VERSION, "largeur_couloir": 2 * DEMI_COULOIR,
            "longueur": -Z_SORTIE, "spawn": [0, 0, Z_ENTREE + 16]}


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
    chev = chevauchements(b)
    print(json.dumps({"pieces": len(b.parts), "fichier": str(out), "en_attente": attente,
                      "couloir_encombre": gene[:20], "nb_couloir_encombre": len(gene),
                      "trop_bas_au_dessus_du_couloir": bas[:20], "nb_trop_bas": len(bas),
                      "hors_budget": hors_budget()[:20], "chevauchements": chev[:20],
                      "nb_chevauchements": len(chev)}, ensure_ascii=False))
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
        sol_n = sum(1 for p in b.parts if p.group.startswith("Sol"))
        print(f"-- sol : {sol_n} pièces")


if __name__ == "__main__":
    main()
