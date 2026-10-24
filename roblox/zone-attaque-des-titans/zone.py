#!/usr/bin/env python3
"""Plan de la zone Attaque des Titans (ville médiévale entre des murailles colossales) en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course occupe x ∈ [-32, 32], bordé de trottoirs jusqu'à |x| = 42 ;
- on arrive par +Z sur une PRAIRIE fleurie hors les murs (z 0 → -60 : chemin de terre, moulins, fermes, arbre géant),
  on passe sous la MURAILLE EXTÉRIEURE (80 studs de haut, tunnel de porte z -60 → -84), puis la ville :
  PLACE DE LA PORTE (-84 → -112), RUE DES COLOMBAGES (-112 → -214), PLACE DE L'ÉGLISE (-214 → -268),
  QUARTIER DU CANAL (-268 → -404, canal et ponts à droite, marché à gauche), GRAND-PLACE des œufs avec fontaine et
  beffroi (centre z = -446), PARVIS du dépôt (-488 → -512) et MURAILLE INTÉRIEURE dont le tunnel débouche en z = -548 ;
- deux remparts colossaux ferment les côtés (faces intérieures en |x| = 128), quatre tours d'angle ;
  au-delà (|x| > 148) s'étendent des champs.

    python zone.py                     # écrit build/parts.json (aucune dépendance à Blender)
    python zone.py --stats             # pièces par groupe, poses par asset et contrôle des budgets
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
X_BORD = 42              # bord des trottoirs = alignement des façades
Y_LIBRE = 30             # rien au-dessus du couloir (|x| < 33) sous cette hauteur
Z_APPROCHE = 8           # petit rebord de sol côté apparition (z > 0)
Z_ENTREE = 0
H_MUR = 80               # dessus du chemin de ronde des murailles
OUVERTURE = 72           # largeur des tunnels de porte (|x| < 36)
H_PASSAGE = 46           # hauteur libre sous la voûte des tunnels

Z_MUR_EXT = -72          # axe de la muraille extérieure (faces en -60 et -84)
EP_MUR_EXT = 24
Z_PRAIRIE_FIN = Z_MUR_EXT + EP_MUR_EXT / 2     # -60
Z_VILLE = Z_MUR_EXT - EP_MUR_EXT / 2           # -84
LARGEUR_MUR_EXT = 280    # la muraille extérieure s'arrête dans les tours d'angle (|x| = 140)

X_REMPART = 128          # face intérieure des remparts latéraux
EP_REMPART = 20
X_EXT = X_REMPART + EP_REMPART                 # 148 : face extérieure
X_TOUR = X_REMPART + EP_REMPART / 2            # 138 : axe des tours d'angle
COTE_TOUR = 32
X_FOND = 230             # fin du sol (champs extérieurs, prairie)

Z_MUR_INT = -530         # axe de la muraille intérieure (faces en -512 et -548)
EP_MUR_INT = 36
Z_FIN_VILLE = Z_MUR_INT + EP_MUR_INT / 2       # -512
Z_SORTIE = Z_MUR_INT - EP_MUR_INT / 2          # -548 : sortie vers la zone suivante

Z_RUE = -112             # fin de la place de la porte, début de la rue des colombages
Z_EGLISE = -214          # place de l'église (-214 → -268)
Z_CANAL = -268           # quartier du canal (-268 → -404)
Z_GRANDPLACE = -404      # grand-place (-404 → -488)
Z_PARVIS = -488          # parvis du dépôt, au pied de la muraille intérieure (-488 → -512)
Z_PLACE = -446           # centre de la place des œufs
R_PLACE = 34
X_GRANDPLACE = 86        # façades de la grand-place
X_CANAL = (44, 60)       # canal (eau entre deux quais), à droite du couloir
Z_CANAL_FIN = -404
H_FANIONS = 38           # corde des guirlandes de fanions (le bas des fanions reste au-dessus de 33)

VERSION = "0.1"

# Budgets de pièces par asset (contrôlés par --stats, voir CONCEPTION.md § 5).
BUDGETS = {
    ("remparts", "porte_colossale"): 900,          # variante 0 (entrée, largeur 280)
    ("remparts", "tour_angle"): 110, ("remparts", "canon_rail"): 26, ("remparts", "tour_guet_mur"): 40,
    ("remparts", "monte_charge"): 80, ("remparts", "escalier_mur"): 60,
    ("batiments", "maison_colombages"): 100, ("batiments", "maison_bourgeoise"): 110,
    ("batiments", "maison_arcades"): 110, ("batiments", "maison_fond"): 32, ("batiments", "ferme"): 80,
    ("monuments", "eglise"): 420, ("monuments", "clocher"): 110, ("monuments", "beffroi"): 380,
    ("monuments", "fontaine"): 70, ("monuments", "moulin"): 90, ("monuments", "depot_ravitaillement"): 160,
    ("monuments", "tour_guet"): 70, ("monuments", "mat_fete"): 45,
    ("nature", "arbre"): 32, ("nature", "arbre_geant"): 220, ("nature", "buisson"): 8,
    ("nature", "parterre_fleurs"): 18, ("nature", "meule_foin"): 10, ("nature", "champ"): 30,
    ("nature", "colline"): 40, ("nature", "canal"): 200, ("nature", "pont_arche"): 50, ("nature", "rocher"): 10,
}
BUDGET_MOBILIER = 40
_COMPTES: list = []      # (module, fn, params, pièces, groupe) de chaque pose


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
    if fn == "porte_colossale" and params.get("variant", 0) == 1:
        return 1150                                     # muraille intérieure (largeur 460), repère final
    if fn == "mur_colossal":
        return int(math.ceil(8 + 0.9 * params.get("longueur", 71) + 26 * params.get("canons", 1)
                             + 40 * bool(params.get("guet", False))))
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


def _attente_porte(largeur: float, epaisseur: float, hauteur: float):
    """Silhouette d'attente d'une muraille à tunnel : deux massifs, la voûte au-dessus de H_PASSAGE."""
    def dessin(b):
        rose = "#ff4fd8"
        for s in (-1, 1):
            xa, xb = sorted((s * OUVERTURE / 2, s * largeur / 2))
            b.box((xa, 0, -epaisseur / 2), (xb, hauteur, epaisseur / 2), rose, transparency=0.5)
        b.box((-OUVERTURE / 2, H_PASSAGE, -epaisseur / 2), (OUVERTURE / 2, hauteur, epaisseur / 2), rose, transparency=0.5)
        b.box((-14, hauteur, -8), (14, hauteur + 22, 8), rose, transparency=0.5)     # corps de garde sur la porte
    return dessin


# ---------------------------------------------------------------------------
# Sol « pixel »
# ---------------------------------------------------------------------------

def sol_pixel(b: Builder, x0: float, x1: float, z0: float, z1: float, cell: float, couleur, y_haut: float = 0.0,
              epaisseur: float = 1.0, studs="top", name: str = "Sol", **kw) -> int:
    """Remplit [x0, x1] × [z0, z1] ; couleur(x, z) → (r, g, b) ou None (trou) au centre de chaque case ; cases fusionnées."""
    nx, nz = int(round((x1 - x0) / cell)), int(round((z1 - z0) / cell))
    if nx <= 0 or nz <= 0:
        return 0
    grid = np.empty((nz, nx), dtype=object)
    for j in range(nz):
        for i in range(nx):
            v = couleur(x0 + (i + 0.5) * cell, z0 + (j + 0.5) * cell)
            grid[j, i] = None if v is None else tuple(int(t) for t in v)
    n = 0
    for col in {v for v in grid.reshape(-1) if v is not None}:
        mask = np.vectorize(lambda v, col=col: v == col)(grid)
        for (i, j, w, h) in mask_rects(mask):
            b.box((x0 + i * cell, y_haut - epaisseur, z0 + j * cell),
                  (x0 + (i + w) * cell, y_haut, z0 + (j + h) * cell), col, studs=studs, name=name, **kw)
            n += 1
    return n


def _hash(i: int, j: int, k: int = 0) -> float:
    """Bruit déterministe dans [0, 1[ pour le choix des teintes du pavage."""
    h = (i * 73856093) ^ (j * 19349663) ^ (k * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0


def _bruit(x: float, z: float, echelle: float, k: int = 0) -> float:
    """Bruit de valeur lissé (pour les taches d'herbe de la prairie)."""
    gx, gz = x / echelle, z / echelle
    i, j = math.floor(gx), math.floor(gz)
    fx, fz = gx - i, gz - j
    fx, fz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    a, b_ = _hash(i, j, k), _hash(i + 1, j, k)
    c_, d = _hash(i, j + 1, k), _hash(i + 1, j + 1, k)
    return (a + (b_ - a) * fx) * (1 - fz) + (c_ + (d - c_) * fx) * fz


def mosaique_place(x: float, z: float):
    """Place des œufs : cadran de pavés (étoile à huit branches, douze marques d'heure, anneaux). None hors du cercle."""
    dx, dz = x, z - Z_PLACE
    d = math.hypot(dx, dz)
    if d >= R_PLACE:
        return None
    th = math.atan2(dz, dx)
    if d < 3:
        return c("or")
    if d < 5:
        return c("pave_fonce")
    if d < 18:
        # étoile à huit branches (longues sur les axes, courtes en diagonale)
        k = (th / (math.pi / 4)) % 1.0
        ecart = min(k, 1 - k)                                 # 0 sur une branche
        longue = round(th / (math.pi / 4)) % 2 == 0
        portee = 17.5 if longue else 12.5
        if ecart < 0.5 * max(0.0, 1 - (d - 5) / (portee - 5)):
            return c("pave_rouge") if (ecart < 0.12 or d < 8) else c("tuile_fonce")
        return c("pave_clair")
    if d < 20:
        return c("pave_fonce")
    if d < 28:
        k = (th / (math.pi / 6)) % 1.0                       # douze marques d'heure
        if min(k, 1 - k) < 0.1 * 20 / d:
            return c("pave_rouge")
        return c("pave_clair")
    if d < 30:
        return c("pave_fonce")
    return c("pave_brun")


def dallage_grandplace(x: float, z: float):
    """Grand-place hors du cadran : anneaux carrés de pavés clairs et gris (6 studs), centrés sur la place des œufs."""
    k = math.floor(max(abs(x), abs(z - Z_PLACE)) / 6)
    return c("pave_clair") if k % 2 == 0 else c("pave")


def sol_couloir(b: Builder) -> None:
    terre, terre_c, terre_f = c("terre"), c("terre_claire"), c("terre_fonce")
    herbe_s = c("herbe_seche")
    pav = (c("pave"), c("pave_clair"), c("pave_fonce"))
    dalle_f, pave_f = c("dalle_fonce"), c("pave_fonce")
    bord = c("bordure")

    def couloir(x, z):
        m = mosaique_place(x, z)
        if m:
            return m
        ax = abs(x)
        if z > Z_PRAIRIE_FIN:                    # chemin de terre de la prairie : ornières et bas-côtés
            if ax > DEMI_COULOIR - 2 and _bruit(x, z, 6, 3) > 0.45:
                return herbe_s
            if 9 <= ax < 13:
                return terre_f
            return terre if _bruit(x, z, 10, 1) > 0.42 else terre_c
        if z > Z_VILLE or z < Z_FIN_VILLE:      # tunnels de porte : grandes dalles sombres
            return dalle_f if math.floor(z / 8) % 2 else pave_f
        if Z_GRANDPLACE >= z > Z_PARVIS:         # grand-place : anneaux de pavés autour de la place des œufs
            return dallage_grandplace(x, z)
        if ax >= DEMI_COULOIR - 2:               # caniveaux le long des trottoirs
            return bord
        # pavés en rangées décalées (blocs de 12 × 6), trois teintes
        rang = math.floor(z / 6)
        decal = 6 if rang % 2 else 0
        i = math.floor((x + decal) / 12)
        h = _hash(i, rang, 7)
        return pav[0] if h < 0.5 else (pav[1] if h < 0.78 else pav[2])

    def trottoir(x, z):
        m = mosaique_place(x, z)
        if m:
            return m
        ax = abs(x)
        if z > Z_PRAIRIE_FIN:                    # prairie : bas-côtés herbeux
            return c("herbe_fonce") if ax < DEMI_COULOIR + 2 else c("herbe")
        if Z_GRANDPLACE >= z > Z_PARVIS:
            return dallage_grandplace(x, z)
        if ax < DEMI_COULOIR + 1.01:
            return bord
        return c("dalle") if math.floor(z / 8) % 2 else c("dalle_fonce")

    z_fin = Z_SORTIE - 4
    zp_bas, zp_haut = Z_PLACE - R_PLACE, Z_PLACE + R_PLACE
    with b.group("Sol/Couloir"):
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, Z_VILLE, Z_APPROCHE, 4, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, Z_GRANDPLACE, Z_VILLE, 2, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, zp_haut, Z_GRANDPLACE, 4, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, zp_bas, zp_haut, 2, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, z_fin, zp_bas, 4, couloir)
    with b.group("Sol/Trottoirs"):
        for s in (-1, 1):
            xa, xb = sorted((s * DEMI_COULOIR, s * X_BORD))
            sol_pixel(b, xa, xb, Z_FIN_VILLE, Z_APPROCHE, 2, trottoir)


def sol_ville(b: Builder) -> None:
    """Sol de la ville entre les trottoirs et les remparts : cours pavées en bandes, jardins au pied des remparts,
    quai du canal ; grand-place en anneaux carrés. (Presque tout est couvert de maisons : motifs larges, peu de pièces.)"""
    brun, brun_f = c("pave_brun"), shade(c("pave_brun"), 0.93)
    h, hf = c("herbe"), c("herbe_fonce")
    quai = c("quai")

    def couleur(x, z):
        ax = abs(x)
        if x > 0 and X_CANAL[0] <= x < X_CANAL[1] and Z_CANAL_FIN <= z < Z_CANAL:
            return None                                       # le canal pose son propre lit
        if x > 0 and X_BORD <= x < X_CANAL[0] and Z_CANAL_FIN <= z < Z_CANAL:
            return quai
        if Z_GRANDPLACE >= z > Z_PARVIS and ax < X_GRANDPLACE:
            return dallage_grandplace(x, z)
        if ax > 92:                                           # jardins au pied des remparts
            return h if math.floor(z / 32) % 2 == 0 else hf
        return brun if math.floor(z / 24) % 2 == 0 else brun_f

    with b.group("Sol/Ville"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_REMPART))
            sol_pixel(b, xa, xb, Z_FIN_VILLE, Z_VILLE, 4, couleur)


def sol_campagne(b: Builder) -> None:
    """Prairie fleurie devant la muraille (z 8 → -56) et champs extérieurs le long des remparts (|x| > 148)."""
    h, hc, hf = c("herbe"), c("herbe_claire"), c("herbe_fonce")
    terre = c("terre")

    def prairie(x, z):
        ax = abs(x)
        # sentiers de terre vers les fermes (au pied de la muraille)
        if -50 < z < -44 and X_BORD <= ax < 58:
            return terre
        n = _bruit(x, z, 22, 5)
        return hc if n > 0.62 else (hf if n < 0.3 else h)

    def champs(x, z):
        ax = abs(x)
        if ax < 170:
            return hf if math.floor(z / 32) % 2 else h
        bande = math.floor((z + 7 * (x > 0)) / 40) % 4
        return (c("ble"), h, c("potager"), c("herbe_seche"))[bande]

    with b.group("Sol/Prairie"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_FOND))
            sol_pixel(b, xa, xb, Z_PRAIRIE_FIN + 4, Z_APPROCHE, 4, prairie)
    with b.group("Sol/Champs"):
        for s in (-1, 1):
            xa, xb = sorted((s * (X_TOUR + COTE_TOUR / 2), s * X_FOND))
            sol_pixel(b, xa, xb, Z_FIN_VILLE, Z_PRAIRIE_FIN + 4, 8, champs)


# ---------------------------------------------------------------------------
# Murailles (porte d'entrée, remparts latéraux, tours d'angle, muraille intérieure)
# ---------------------------------------------------------------------------

def murailles(b: Builder) -> None:
    # muraille extérieure : façade extérieure (-Z local) tournée vers la prairie (+Z) → yaw 180
    place(b, "remparts", "porte_colossale", (0, 0, Z_MUR_EXT), yaw=180, group="Muraille/PorteEntree",
          attente=_attente_porte(LARGEUR_MUR_EXT, EP_MUR_EXT, H_MUR),
          variant=0, largeur=LARGEUR_MUR_EXT, hauteur=H_MUR, epaisseur=EP_MUR_EXT, ouverture=OUVERTURE, h_passage=H_PASSAGE)
    # muraille intérieure (repère final) : sa face extérieure regarde la ville (+Z)
    place(b, "remparts", "porte_colossale", (0, 0, Z_MUR_INT), yaw=180, group="Muraille/PorteFinale",
          attente=_attente_porte(2 * X_FOND, EP_MUR_INT, H_MUR),
          variant=1, largeur=2 * X_FOND, hauteur=H_MUR, epaisseur=EP_MUR_INT, ouverture=OUVERTURE, h_passage=H_PASSAGE)
    # tours d'angle : deux à la jonction muraille extérieure / remparts, deux contre la muraille intérieure
    for j, z in enumerate((Z_MUR_EXT, Z_MUR_INT)):
        for s in (-1, 1):
            place(b, "remparts", "tour_angle", (s * X_TOUR, 0, z), yaw=180, group=f"Muraille/Tour{j}{'G' if s < 0 else 'D'}",
                  emprise=(COTE_TOUR, COTE_TOUR, 100), variant=2 * j + (s > 0), cote=COTE_TOUR, hauteur=100)
    # remparts latéraux : 6 segments par côté entre les tours ; l'avant (-Z local) = face intérieure, vers la ville
    z_a, z_b = Z_MUR_EXT - COTE_TOUR / 2, Z_MUR_INT + COTE_TOUR / 2     # -88 → -514
    n = 6
    L = (z_a - z_b) / n                                                  # 71
    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        for k in range(n):
            zc = z_a - L * (k + 0.5)
            x = s * X_TOUR
            place(b, "remparts", "mur_colossal", (x, 0, zc), yaw=face_couloir(x), group=f"Muraille/{cote}/Seg{k}",
                  emprise=(L, EP_REMPART, H_MUR), variant=(k + (s > 0)) % 4, longueur=L, hauteur=H_MUR,
                  epaisseur=EP_REMPART, canons=1, guet=k in (1, 4))
    # équipements contre la face intérieure des remparts (l'arrière +Z local touche le mur)
    for i, (s, z) in enumerate(((-1, -160), (1, -312), (-1, -430), (1, -398))):
        x = s * (X_REMPART - 5)
        place(b, "remparts", "monte_charge", (x, 0, z), yaw=face_couloir(x), group=f"Muraille/MonteCharge{i}",
              emprise=(12, 10, H_MUR), variant=i % 3, hauteur=H_MUR)
    for i, (s, z) in enumerate(((1, -176), (-1, -300))):
        x = s * (X_REMPART - 4)
        place(b, "remparts", "escalier_mur", (x, 0, z), yaw=face_couloir(x), group=f"Muraille/Escalier{i}",
              emprise=(40, 8, H_MUR), variant=i, hauteur=H_MUR, longueur=40)


# ---------------------------------------------------------------------------
# Prairie hors les murs
# ---------------------------------------------------------------------------

def prairie(b: Builder) -> None:
    place(b, "monuments", "moulin", (-80, 0, -20), yaw=face_couloir(-80), group="Prairie/Moulin0", emprise=(12, 12, 34), variant=0)
    place(b, "monuments", "moulin", (-196, 0, -6), yaw=-60, group="Prairie/Moulin1", emprise=(12, 12, 34), variant=1)
    place(b, "monuments", "moulin", (178, 0, -18), yaw=70, group="Prairie/Moulin2", emprise=(12, 12, 34), variant=2)
    place(b, "batiments", "ferme", (-66, 0, -47), yaw=180, group="Prairie/Ferme0", emprise=(24, 14, 14), variant=0)
    place(b, "batiments", "ferme", (62, 0, -48), yaw=180, group="Prairie/Ferme1", emprise=(24, 14, 14), variant=1)
    info = place(b, "nature", "colline", (98, 0, -20), group="Prairie/Colline", emprise=(48, 30, 4), variant=0,
                 largeur=48, profondeur=30, hauteur=4)
    place(b, "nature", "arbre_geant", (98, info.get("hauteur", 4), -20), yaw=25, group="Prairie/ArbreGeant",
          emprise=(40, 40, 46), variant=0)
    for i, (x, z, v) in enumerate(((-124, -24, 0), (-150, -46, 1), (144, -42, 2))):
        place(b, "nature", "champ", (x, 0, z), group=f"Prairie/Champ{i}", emprise=(36, 24, 2), variant=v, largeur=36, profondeur=24)
    for i, (x, z) in enumerate(((-104, -50), (-112, -44), (-98, -40), (130, -50))):
        place(b, "nature", "meule_foin", (x, 0, z), group=f"Prairie/Meule{i}", emprise=(5, 5, 6), variant=i)
    for i, (x, z, v) in enumerate(((-50, -2, 0), (-140, 2, 1), (-226, -40, 2), (52, 4, 3), (140, -2, 0), (214, -44, 1))):
        place(b, "nature", "arbre", (x, 0, z), group=f"Prairie/Arbre{i}", emprise=(10, 10, 14), variant=v, taille=1.0 + 0.1 * (i % 3))
    for i, (x, z) in enumerate(((-58, -12), (-100, -4), (72, -6), (124, -24), (-170, -30), (200, -6))):
        place(b, "nature", "parterre_fleurs", (x, 0, z), group=f"Prairie/Fleurs{i}", emprise=(8, 6, 1), variant=i % 4,
              largeur=8, profondeur=6)
    for i, (x, z) in enumerate(((-48, -56), (-90, -56), (84, -56), (112, -56), (-226, -10))):
        place(b, "nature", "buisson", (x, 0, z), group=f"Prairie/Buisson{i}", emprise=(4, 4, 3), variant=i % 3)
    # clôtures de bois le long du chemin (côté campagne), avec un passage vers chaque ferme
    for s in (-1, 1):
        for i, z in enumerate((-4, -18, -32)):
            place(b, "mobilier", "cloture_bois", (s * 45, 0, z - 6), yaw=90, group=f"Prairie/Cloture{'G' if s < 0 else 'D'}{i}",
                  emprise=(12, 1, 3), longueur=12, variant=0)
    place(b, "mobilier", "charrette", (-50, 0, -36), yaw=200, group="Prairie/Charrette", emprise=(5, 10, 5), variant=0)
    place(b, "mobilier", "bottes_foin", (-82, 0, -36), group="Prairie/Bottes", emprise=(5, 5, 3), variant=2)
    place(b, "mobilier", "abreuvoir", (52, 0, -36), yaw=180, group="Prairie/Abreuvoir", emprise=(6, 5, 4))
    place(b, "mobilier", "tas_bois", (76, 0, -40), yaw=180, group="Prairie/TasBois", emprise=(7, 3, 6))


# ---------------------------------------------------------------------------
# Ville
# ---------------------------------------------------------------------------

# Rangées (module:fonction, largeur le long du couloir, profondeur, paramètres). Façades en |x| = 42 (ou x = 62 au canal).
RUE_G = [
    ("batiments:maison_colombages", 16, 16, {"variant": 0, "etages": 3, "enseigne": "PAIN"}),
    ("batiments:maison_colombages", 14, 16, {"variant": 1, "etages": 3}),
    ("batiments:maison_colombages", 18, 16, {"variant": 2, "etages": 4, "enseigne": "AUBERGE"}),
    ("batiments:maison_colombages", 14, 16, {"variant": 3, "etages": 2}),
    ("batiments:maison_colombages", 16, 16, {"variant": 4, "etages": 3, "enseigne": "FLEURS"}),
]
RUE_D = [
    ("batiments:maison_colombages", 14, 16, {"variant": 2, "etages": 3}),
    ("batiments:maison_colombages", 18, 16, {"variant": 0, "etages": 4, "enseigne": "BÄCKEREI"}),
    ("batiments:maison_colombages", 16, 16, {"variant": 3, "etages": 3}),
    ("batiments:maison_colombages", 14, 16, {"variant": 1, "etages": 2, "enseigne": "TISSUS"}),
    ("batiments:maison_colombages", 16, 16, {"variant": 4, "etages": 3}),
]
CANAL_G = [
    ("batiments:maison_bourgeoise", 20, 18, {"variant": 0, "etages": 4}),
    ("batiments:maison_colombages", 16, 16, {"variant": 1, "etages": 3, "enseigne": "FROMAGES"}),
    ("batiments:maison_bourgeoise", 22, 18, {"variant": 1, "etages": 3}),
    ("batiments:maison_colombages", 16, 16, {"variant": 2, "etages": 4}),
    ("batiments:maison_bourgeoise", 20, 18, {"variant": 2, "etages": 4, "enseigne": "LIBRAIRIE"}),
    ("batiments:maison_colombages", 18, 16, {"variant": 3, "etages": 3, "enseigne": "HORLOGER"}),
]
CANAL_D = [   # rive droite du canal (façades en x = 62), un pont devant les maisons 0, 2 et 4
    ("batiments:maison_bourgeoise", 24, 18, {"variant": 3, "etages": 4}),
    ("batiments:maison_bourgeoise", 24, 18, {"variant": 0, "etages": 3}),
    ("batiments:maison_bourgeoise", 24, 18, {"variant": 1, "etages": 4, "enseigne": "SAVON"}),
    ("batiments:maison_bourgeoise", 24, 18, {"variant": 2, "etages": 3}),
    ("batiments:maison_bourgeoise", 24, 18, {"variant": 3, "etages": 4}),
]


def rangee(b: Builder, s: int, plan, z_debut: float, z_fin: float, nom: str, x_facade: float = X_BORD, ecart: float = 2) -> list:
    """Aligne une rangée de bâtiments le long du couloir (avant tourné vers le couloir)."""
    z = z_debut
    poses = []
    for i, (kind, larg, prof, params) in enumerate(plan):
        zc = z - larg / 2
        mod, fn = kind.split(":")
        kw = dict(params)
        kw.setdefault("largeur", larg)
        kw.setdefault("profondeur", prof)
        x = s * (x_facade + prof / 2)
        info = place(b, mod, fn, (x, 0, zc), yaw=face_couloir(x), group=f"Ville/{nom}/{i:02d}_{fn}",
                     emprise=(larg, prof, 6 + 6 * kw.get("etages", 3)), **kw)
        poses.append((x, zc, larg, prof, info))
        z -= larg + ecart
    assert z > z_fin - ecart - 0.01, f"rangée {nom} trop longue ({z} < {z_fin})"
    return poses


def place_porte(b: Builder) -> None:
    """Place de la porte (-84 → -112) : puits, étals, charrettes et boulets au pied de la muraille."""
    place(b, "mobilier", "puits", (-54, 0, -98), group="Ville/PlacePorte/Puits", emprise=(6, 6, 10), variant=0)
    place(b, "mobilier", "charrette", (-38, 0, -92), yaw=10, group="Ville/PlacePorte/Charrette", emprise=(5, 10, 5), variant=1)
    place(b, "mobilier", "pile_boulets", (-66, 0, -90), group="Ville/PlacePorte/Boulets0", emprise=(4, 4, 3), variant=0)
    place(b, "mobilier", "pile_boulets", (-72, 0, -92), group="Ville/PlacePorte/Boulets1", emprise=(3, 3, 2), variant=1)
    for i, z in enumerate((-94, -104)):
        place(b, "mobilier", "etal", (37, 0, z), yaw=90, group=f"Ville/PlacePorte/Etal{i}", emprise=(9, 6, 7), variant=i)
    place(b, "mobilier", "caisses", (50, 0, -90), group="Ville/PlacePorte/Caisses", emprise=(5, 4, 4), variant=2)
    place(b, "mobilier", "tonneaux", (56, 0, -94), group="Ville/PlacePorte/Tonneaux", emprise=(4, 4, 3), variant=2)
    for i, (x, z) in enumerate(((-80, -100), (74, -100), (-104, -96), (100, -96))):
        place(b, "nature", "arbre", (x, 0, z), group=f"Ville/PlacePorte/Arbre{i}", emprise=(10, 10, 14), variant=i % 4)


def place_eglise(b: Builder) -> None:
    """Place de l'église (-214 → -268) : église à gauche, placette au mât de fête et clocher à droite."""
    place(b, "monuments", "eglise", (-(X_BORD + 6 + 15), 0, -241), yaw=face_couloir(-1), group="Monuments/Eglise",
          emprise=(56, 30, 72), variant=0)
    place(b, "monuments", "clocher", (100, 0, -246), yaw=face_couloir(1), group="Monuments/ClocherA",
          emprise=(12, 12, 64), variant=0, hauteur=64)
    place(b, "monuments", "mat_fete", (60, 0, -238), group="Ville/PlaceEglise/MatFete", emprise=(4, 4, 40), variant=0, hauteur=40)
    for i, (x, z) in enumerate(((50, -222), (82, -222), (78, -262), (50, -262))):
        place(b, "nature", "arbre", (x, 0, z), group=f"Ville/PlaceEglise/Arbre{i}", emprise=(10, 10, 14), variant=(i + 1) % 4)
    place(b, "mobilier", "puits", (68, 0, -250), group="Ville/PlaceEglise/Puits", emprise=(6, 6, 10), variant=1)
    for i, (x, z) in enumerate(((44.5, -232), (44.5, -246))):
        place(b, "mobilier", "banc", (x, 0, z), yaw=90, group=f"Ville/PlaceEglise/Banc{i}", emprise=(6, 2, 3), variant=i)
    for i, z in enumerate((-218, -264)):
        place(b, "mobilier", "bac_fleurs", (-45, 0, z), group=f"Ville/PlaceEglise/Bac{i}", emprise=(3, 2, 3), variant=i)


def quartier_canal(b: Builder) -> list:
    """Quartier du canal (-268 → -404) : canal et ponts à droite, marché à gauche."""
    zc = (Z_CANAL + Z_CANAL_FIN) / 2
    place(b, "nature", "canal", ((X_CANAL[0] + X_CANAL[1]) / 2, 0, zc), group="Canal/Canal",
          emprise=(X_CANAL[1] - X_CANAL[0], Z_CANAL - Z_CANAL_FIN, 1), variant=0,
          longueur=Z_CANAL - Z_CANAL_FIN, largeur=X_CANAL[1] - X_CANAL[0])
    poses_d = rangee(b, 1, CANAL_D, Z_CANAL - 2, Z_CANAL_FIN, "CanalD", x_facade=62, ecart=3)
    for i, k in enumerate((0, 2, 4)):
        z = poses_d[k][1]
        place(b, "nature", "pont_arche", ((X_BORD + 62) / 2, 0, z), group=f"Canal/Pont{i}", emprise=(20, 7, 5),
              variant=i, portee=62 - X_BORD, largeur=7)
    poses_g = rangee(b, -1, CANAL_G, Z_CANAL - 2, Z_CANAL_FIN, "CanalG")
    # marché sur le trottoir de gauche
    place(b, "mobilier", "panneau_pied", (-38.5, 0, -273), yaw=-90, group="Ville/Marche/Panneau", emprise=(6, 2, 6), texte="MARCHÉ")
    for i, z in enumerate((-284, -296, -308, -320)):
        place(b, "mobilier", "etal", (-37, 0, z), yaw=-90, group=f"Ville/Marche/Etal{i}", emprise=(9, 6, 7), variant=i)
    place(b, "monuments", "clocher", (-100, 0, -372), yaw=face_couloir(-1), group="Monuments/ClocherB",
          emprise=(12, 12, 60), variant=1, hauteur=60)
    return poses_g + poses_d


def arriere_ville(b: Builder) -> None:
    """Seconde rangée (maisons simples), jardins et arbres entre les rangées et les remparts."""
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        zs = [-120, -144, -168, -192, -282, -320] if s < 0 else [-122, -146, -170, -194]
        for i, z in enumerate(zs):
            x0 = 66 if z > Z_EGLISE else 68
            x = s * (x0 + 6)
            place(b, "batiments", "maison_fond", (x, 0, z), yaw=face_couloir(x), group=f"Ville/Fond{cote}/{i:02d}",
                  emprise=(14, 12, 14), variant=(i + (s > 0)) % 4, largeur=14, profondeur=12, etages=2 + (i % 2))
    for i, z in enumerate((-284, -320, -356, -392)):
        place(b, "batiments", "maison_fond", (94, 0, z), yaw=90, group=f"Ville/FondCanal/{i:02d}",
              emprise=(14, 12, 14), variant=i % 4, largeur=14, profondeur=12, etages=2)
    arbres = ((-100, -130), (-108, -200), (-96, -320), (-112, -250), (104, -130), (112, -206), (110, -282),
              (114, -360), (-74, -398))
    for i, (x, z) in enumerate(arbres):
        place(b, "nature", "arbre", (x, 0, z), group=f"Ville/Jardins/Arbre{i}", emprise=(10, 10, 14), variant=i % 4,
              taille=1.0 + 0.15 * (i % 3))
    for i, (x, z) in enumerate(((-90, -150), (92, -160), (-118, -350), (118, -250))):
        place(b, "nature", "buisson", (x, 0, z), group=f"Ville/Jardins/Buisson{i}", emprise=(4, 4, 3), variant=i % 3)


def grand_place(b: Builder) -> None:
    """Grand-place des œufs (-404 → -488) : maisons à arcades, beffroi, fontaine, arbres, réverbères."""
    for i, (zc, v) in enumerate(((-417, 0), (-446, 1), (-475, 2))):
        x = -(X_GRANDPLACE + 9)
        place(b, "batiments", "maison_arcades", (x, 0, zc), yaw=face_couloir(x), group=f"GrandPlace/ArcadesG{i}",
              emprise=(26, 18, 26), variant=v, largeur=26, profondeur=18, etages=3)
    for i, (zc, v) in enumerate(((-413, 3), (-479, 1))):
        x = X_GRANDPLACE + 9
        place(b, "batiments", "maison_arcades", (x, 0, zc), yaw=face_couloir(x), group=f"GrandPlace/ArcadesD{i}",
              emprise=(18, 18, 26), variant=v, largeur=18, profondeur=18, etages=3)
    place(b, "monuments", "beffroi", (X_GRANDPLACE + 16, 0, Z_PLACE), yaw=face_couloir(1), group="Monuments/Beffroi",
          emprise=(44, 32, 80), variant=0, largeur=44, profondeur=32)
    place(b, "monuments", "fontaine", (-58, 0, Z_PLACE), yaw=face_couloir(-1), group="GrandPlace/Fontaine",
          emprise=(16, 16, 12), variant=0)
    for i, (x, z) in enumerate(((-72, -410), (-72, -482), (62, -410), (62, -482))):
        place(b, "nature", "arbre", (x, 0, z), group=f"GrandPlace/Arbre{i}", emprise=(10, 10, 14), variant=(i + 2) % 4)
    for i, (x, z) in enumerate(((-62, -426), (-62, -466), (60, -432), (60, -460))):
        place(b, "nature", "parterre_fleurs", (x, 0, z), yaw=90, group=f"GrandPlace/Parterre{i}", emprise=(8, 6, 1),
              variant=i % 4, largeur=8, profondeur=6)
    for i, (x, z) in enumerate(((-44, -420), (-44, -472), (44, -420), (44, -472))):
        place(b, "mobilier", "reverbere", (x, 0, z), group=f"GrandPlace/Reverbere{i}", emprise=(5, 2, 12), variant=2)
    for i, (x, z, yaw) in enumerate(((-46, -440, 90), (-46, -452, 90), (70, -446, -90))):
        place(b, "mobilier", "banc", (x, 0, z), yaw=yaw, group=f"GrandPlace/Banc{i}", emprise=(6, 2, 3), variant=i)
    for i, (x, z) in enumerate(((-80, -404), (80, -404))):
        place(b, "mobilier", "drapeau", (x, 0, z), group=f"GrandPlace/Drapeau{i}", emprise=(6, 1, 14), variant=i, hauteur=14)


def parvis(b: Builder) -> None:
    """Parvis de la muraille intérieure (-488 → -512) : dépôt de ravitaillement à gauche, tour de guet à droite."""
    place(b, "monuments", "depot_ravitaillement", (-80, 0, -500), yaw=180, group="Parvis/Depot", emprise=(36, 20, 16),
          variant=0, largeur=36, profondeur=20)
    place(b, "monuments", "tour_guet", (72, 0, -500), yaw=face_couloir(1), group="Parvis/TourGuet", emprise=(10, 10, 36),
          variant=0, hauteur=36)
    props = (("charrette", (-50, -494), 160, 2), ("pile_boulets", (-56, -506), 0, 0), ("caisses", (-46, -506), 0, 1),
             ("tonneaux", (52, -506), 0, 0), ("sacs", (46, -500), 0, 1), ("pile_boulets", (58, -494), 0, 1),
             ("charrette", (100, -494), 200, 3))
    for i, (fn, (x, z), yaw, v) in enumerate(props):
        place(b, "mobilier", fn, (x, 0, z), yaw=yaw, group=f"Parvis/{fn}{i}", emprise=(5, 5, 4), variant=v)


def exterieur(b: Builder) -> None:
    """Champs et bosquets hors des remparts (vues aérienne et de côté seulement)."""
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        for i, z in enumerate((-150, -300, -440)):
            place(b, "nature", "champ", (s * 196, 0, z), group=f"Exterieur/Champ{cote}{i}", emprise=(60, 80, 2),
                  variant=(i + (s > 0)) % 3, largeur=60, profondeur=80)
        for i, z in enumerate((-100, -230, -370, -490)):
            place(b, "nature", "arbre", (s * (164 + 8 * (i % 2)), 0, z), group=f"Exterieur/Arbre{cote}{i}",
                  emprise=(10, 10, 14), variant=i % 4, taille=1.2)


def mats_fanions(b: Builder) -> None:
    """Guirlandes de fanions au-dessus de la rue (corde à 38 studs) entre deux mâts sur les trottoirs."""
    f = _asset("mobilier", "guirlande_fanions")
    for i, z in enumerate((-134, -180, -300, -352)):
        with b.group(f"Fanions/Guirlande{i + 1}"):
            for s in (-1, 1):
                with b.at((s * 36.5, 0, z)):
                    b.box((-0.6, 0, -0.6), (0.6, H_FANIONS + 2, 0.6), c("bois"), name="Mat")
                    b.box((-1.0, 0, -1.0), (1.0, 1.2, 1.0), c("pave_fonce"), studs="top", name="Pied")
                    b.box((-0.9, H_FANIONS + 2, -0.9), (0.9, H_FANIONS + 2.4, 0.9), c("bois_moyen"), name="Chapeau")
                    b.ball((0, H_FANIONS + 2.9, 0), 0.5, c("or"), collide=False, name="Pommeau")
            if f:
                n0 = len(b.parts)
                f(b, (-35.9, H_FANIONS, z), (35.9, H_FANIONS, z), n=14, creux=2.0, variant=i)
                _COMPTES.append(("mobilier", "guirlande_fanions", {}, len(b.parts) - n0, f"Fanions/Guirlande{i + 1}"))


def details_rue(b: Builder, poses) -> None:
    """Réverbères, bancs, tonneaux, caisses, bacs à fleurs au pied des façades (jamais dans le couloir)."""
    for s in (-1, 1):
        for i, z in enumerate((-124, -160, -200, -286, -330, -376)):
            if s > 0 and z < Z_CANAL:
                x = s * 41.5           # quai du canal : réverbère au bord du trottoir
            else:
                x = s * 40.5
            place(b, "mobilier", "reverbere", (x, 0, z), yaw=face_couloir(x), group=f"Details/Reverbere{'G' if s < 0 else 'D'}{i}",
                  emprise=(2, 4, 11), variant=1)
    rng = np.random.default_rng(3)
    props = ["tonneaux", "bac_fleurs", "caisses", "banc", "sacs", "bac_fleurs"]
    interdits = [-124, -160, -200, -286, -330, -376, -134, -180, -300, -352]
    k = 0
    for (x, zc, larg, prof, info) in poses:
        s = -1 if x < 0 else 1
        if abs(x) > 60 or (s < 0 and -326 < zc < -276):     # rive droite du canal et marché : pas de props
            continue
        fn = props[k % len(props)]
        zp = zc + rng.uniform(-larg / 2 + 3, larg / 2 - 3)
        if min(abs(zp - zi) for zi in interdits) < 4:
            zp += 6 if zp + 6 < zc + larg / 2 else -6
        xp = s * (X_BORD - 2.2)
        yaw = face_couloir(xp) if fn == "banc" else 0
        place(b, "mobilier", fn, (xp, 0, zp), yaw=yaw, group=f"Details/{fn}{k}", emprise=(3, 3, 3), variant=k % 3)
        k += 1


# ---------------------------------------------------------------------------
# Repères, découpage, contrôles
# ---------------------------------------------------------------------------

def reperes(b: Builder) -> None:
    """Pièces invisibles utiles au jeu : zone des œufs, entrée, sortie, couloir."""
    inv = dict(transparency=1.0, collide=False, shadow=False)
    with b.group("Reperes"):
        b.box((-R_PLACE, 0, Z_PLACE - R_PLACE), (R_PLACE, 1, Z_PLACE + R_PLACE), "#ffffff", name="ZoneOeufs", **inv)
        b.box((-DEMI_COULOIR, 0, Z_ENTREE - 2), (DEMI_COULOIR, 1, Z_ENTREE + 4), "#ffffff", name="Entree", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE - 4), (DEMI_COULOIR, 1, Z_SORTIE + 2), "#ffffff", name="Sortie", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE), (DEMI_COULOIR, 1, Z_ENTREE), "#ffffff", name="Couloir", **inv)


def decouper(b: Builder, prefixes=("Sol/", "Muraille/"), taille: float = 64) -> None:
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
    sol_ville(b)
    sol_campagne(b)
    murailles(b)
    prairie(b)
    place_porte(b)
    poses = rangee(b, -1, RUE_G, Z_RUE, Z_EGLISE, "RueG")
    poses += rangee(b, 1, RUE_D, Z_RUE, Z_EGLISE, "RueD")
    place_eglise(b)
    poses += quartier_canal(b)
    arriere_ville(b)
    grand_place(b)
    parvis(b)
    exterieur(b)
    mats_fanions(b)
    details_rue(b, poses)
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
    return {"nom": "ZoneAttaqueDesTitans", "version": VERSION, "largeur_couloir": 2 * DEMI_COULOIR,
            "longueur": -Z_SORTIE, "spawn": [0, 0, Z_ENTREE + 4]}


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
            print("-- assets livrés (pièces, poses) --")
            for k, (nb, n) in sorted(par_asset.items(), key=lambda kv: -kv[1][1]):
                print(f"{n:6d}  {k} ×{nb}")
        for prefixe in ("Sol/Couloir", "Sol/Trottoirs", "Sol/Ville", "Sol/Prairie", "Sol/Champs"):
            n = sum(1 for p in b.parts if p.group.startswith(prefixe))
            print(f"-- {prefixe} : {n} pièces")
        attente_n = sum(1 for p in b.parts if p.name.startswith("ATTENTE_"))
        print(f"-- blocs d'attente : {attente_n} pièces ; poses d'attente à remplacer par les assets")


if __name__ == "__main__":
    main()
