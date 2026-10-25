#!/usr/bin/env python3
"""Plan de la zone Attaque des Titans (ville médiévale entre des murailles colossales) en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course, très large à la demande du joueur, occupe x ∈ [-45, 45] (90 studs), bordé de trottoirs
  jusqu'aux façades (|x| = 55) : la grand-rue fait 110 studs de façade à façade ;
- on arrive par +Z sur une PRAIRIE fleurie hors les murs (z 8 → -60 : chemin de terre, moulins, fermes, arbre géant),
  on passe sous la MURAILLE EXTÉRIEURE (90 studs de haut, tunnel de porte de 104 × 46, z -60 → -84), puis la ville :
  PLACE DE LA PORTE (-84 → -112), RUE DES COLOMBAGES (-112 → -214), PLACE DE L'ÉGLISE (-214 → -268),
  QUARTIER DU CANAL (-268 → -404, canal et ponts à droite, marché à gauche), GRAND-PLACE des œufs avec fontaine et
  beffroi (centre z = -446), PARVIS du dépôt (-488 → -512) et MURAILLE INTÉRIEURE dont le tunnel débouche en z = -548 ;
- deux remparts colossaux ferment les côtés (faces intérieures en |x| = 125), quatre tours d'angle ;
  au-delà (|x| > 145) s'étendent des champs.

    python zone.py                     # écrit build/parts.json (aucune dépendance à Blender)
    python zone.py --stats             # pièces par groupe, poses par asset et contrôle des budgets
    python zone.py --chevauchements    # assets posés qui se recoupent (boîtes orientées)
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
DEMI_COULOIR = 45        # couloir de course x ∈ [-45, 45] : 90 studs de large
X_BORD = 55              # bord des trottoirs = alignement des façades
Y_LIBRE = 30             # rien au-dessus du couloir (|x| < 46) sous cette hauteur
Z_APPROCHE = 8           # petit rebord de sol côté apparition (z > 0)
Z_ENTREE = 0
H_MUR = 90               # dessus du parapet du chemin de ronde des murailles
OUVERTURE = 104          # largeur des tunnels de porte (|x| < 52)
H_PASSAGE = 46           # hauteur libre sous la voûte des tunnels (bas de la herse relevée compris)

Z_MUR_EXT = -72          # axe de la muraille extérieure (faces en -60 et -84)
EP_MUR_EXT = 24
Z_PRAIRIE_FIN = Z_MUR_EXT + EP_MUR_EXT / 2     # -60
Z_VILLE = Z_MUR_EXT - EP_MUR_EXT / 2           # -84

X_REMPART = 125          # face intérieure des remparts latéraux
EP_REMPART = 20
X_EXT = X_REMPART + EP_REMPART                 # 145 : face extérieure
X_TOUR = X_REMPART + EP_REMPART / 2            # 135 : axe des tours d'angle et des remparts
COTE_TOUR = 32
H_TOUR = 112
LARGEUR_MUR_EXT = 2 * X_TOUR                   # 270 : la muraille extérieure s'arrête dans les tours d'angle
X_FOND = 235             # fin du sol (champs extérieurs, prairie)

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
X_GRANDPLACE = 90        # façades de la grand-place
X_CANAL = (55, 75)       # emprise du canal à droite : margelle 55-57, eau 57-73, margelle 73-75
X_QUAI = 79              # façades de la rive droite (quai pavé 75-79)
X_FOND_RUE = 87          # axe de la seconde rangée (maisons simples, 81-93)
H_FANIONS = 38           # corde des guirlandes de fanions (le bas des fanions reste au-dessus de 34)
X_MAT = 49               # mâts des guirlandes, sur les trottoirs

VERSION = "0.2"

# Budgets de pièces par pose (contrôlés par --stats, voir CONCEPTION.md § 5).
BUDGETS = {
    ("remparts", "porte_colossale"): 800,          # variante 0 (entrée, largeur 270)
    ("remparts", "tour_angle"): 100, ("remparts", "monte_charge"): 70, ("remparts", "escalier_mur"): 50,
    ("batiments", "maison_colombages"): 100, ("batiments", "maison_bourgeoise"): 110,
    ("batiments", "maison_arcades"): 110, ("batiments", "maison_fond"): 30, ("batiments", "ferme"): 75,
    ("monuments", "eglise"): 400, ("monuments", "clocher"): 95, ("monuments", "beffroi"): 340,
    ("monuments", "fontaine"): 70, ("monuments", "moulin"): 80, ("monuments", "depot_ravitaillement"): 150,
    ("monuments", "tour_guet"): 60, ("monuments", "mat_fete"): 40,
    ("nature", "arbre"): 26, ("nature", "arbre_geant"): 200, ("nature", "buisson"): 8,
    ("nature", "parterre_fleurs"): 16, ("nature", "meule_foin"): 10, ("nature", "champ"): 30,
    ("nature", "colline"): 40, ("nature", "canal"): 160, ("nature", "pont_arche"): 45,
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
        return 1050                                     # muraille intérieure (largeur 470), repère final
    if fn == "mur_colossal":
        return int(math.ceil(10 + 1.0 * params.get("longueur", 71) + 24 * params.get("canons", 1)
                             + 36 * bool(params.get("guet", False))))
    return BUDGETS.get((module, fn), 10 ** 6)


def place(b: Builder, module: str, fn: str, pos, yaw: float = 0.0, group: str | None = None, emprise=(16, 16, 16),
          attente=None, **params) -> dict:
    """Pose un asset ; si le module n'existe pas encore, pose un bloc translucide de même emprise
    (ou la silhouette `attente(b)` pour les monuments qui enjambent le couloir)."""
    f = _asset(module, fn)
    with b.at(pos, yaw=yaw, group=group):
        n0 = len(b.parts)
        nom_groupe = b._groups[-1]
        info = None
        if f is not None:
            try:
                info = f(b, **params) or {}
                _COMPTES.append((module, fn, params, len(b.parts) - n0, group))
            except NotImplementedError:
                del b.parts[n0:]
        if info is None:
            if attente is not None:
                attente(b)
                for p in b.parts[n0:]:
                    p.name = f"ATTENTE_{module}_{fn}"
            else:
                w, d, h = emprise
                b.box((-w / 2, 0, -d / 2), (w / 2, h, d / 2), "#ff4fd8", transparency=0.5, name=f"ATTENTE_{module}_{fn}")
            info = {"emprise": tuple(emprise[:2]), "hauteur": emprise[2]}
    if not hasattr(b, "poses"):
        b.poses = []
    b.poses.append((nom_groupe, fn, n0, len(b.parts)))      # pour le contrôle des chevauchements
    return info


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
        b.box((-16, hauteur, -8), (16, hauteur + 22, 8), rose, transparency=0.5)     # corps de garde sur la porte
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
    """Bruit de valeur lissé (taches d'herbe de la prairie)."""
    gx, gz = x / echelle, z / echelle
    i, j = math.floor(gx), math.floor(gz)
    fx, fz = gx - i, gz - j
    fx, fz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    a, b_ = _hash(i, j, k), _hash(i + 1, j, k)
    c_, d = _hash(i, j + 1, k), _hash(i + 1, j + 1, k)
    return (a + (b_ - a) * fx) * (1 - fz) + (c_ + (d - c_) * fx) * fz


FLEURS = ("fleur_blanche", "fleur_jaune", "fleur_blanche", "fleur_bleue", "fleur_jaune", "fleur_mauve", "fleur_rouge")


def _pre_fleuri(x: float, z: float, densite: float = 0.07):
    """Herbe vert-jaune en taches, semée de fleurs blanches, jaunes et bleues (cases de 2 studs)."""
    i, j = math.floor(x / 2), math.floor(z / 2)
    if _hash(i, j, 11) < densite:
        return c(FLEURS[int(_hash(i, j, 12) * len(FLEURS))])
    n = _bruit(x, z, 14, 5)
    return c("herbe_claire") if n > 0.62 else (c("herbe_fonce") if n < 0.3 else c("herbe"))


def mosaique_place(x: float, z: float):
    """Place des œufs : cadran de pavés (rose des vents à huit branches, douze marques d'heure, anneaux).
    None hors du cercle (le cercle de rayon 34 tient entièrement dans le couloir)."""
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
        # rose des vents à huit branches (longues sur les axes, courtes en diagonale)
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


def _paves(x: float, z: float, z_haut: float, tons, graine: int):
    """Pavés en rangées décalées (pierres de 12 × 6), trois teintes ; repère : bord gauche du couloir et début de section."""
    u, v = x + DEMI_COULOIR, z_haut - z
    rang = math.floor(v / 6)
    decal = 6 if rang % 2 else 0
    h = _hash(math.floor((u + decal) / 12), rang, graine)
    return tons[0] if h < 0.5 else (tons[1] if h < 0.78 else tons[2])


def sol_couloir(b: Builder) -> None:
    terre, terre_c, terre_f = c("terre"), c("terre_claire"), c("terre_fonce")
    herbe_s = c("herbe_seche")
    rue = (c("pave"), c("pave_clair"), c("pave_fonce"))
    canal = (c("pave_brun"), shade(c("pave_brun"), 1.08), c("pave"))
    dalle, dalle_f, pave_f, pave_c = c("dalle"), c("dalle_fonce"), c("pave_fonce"), c("pave_clair")
    bord = c("bordure")

    def prairie(x, z):
        ax = abs(x)
        if ax < 22:                                           # chemin de terre, ornières, bas-côtés de foin
            if ax > 18 and _bruit(x, z, 6, 3) > 0.45:
                return herbe_s
            if 8 <= ax < 11:
                return terre_f
            return terre if _bruit(x, z, 10, 1) > 0.42 else terre_c
        return _pre_fleuri(x, z, 0.06)

    def tunnel(x, z):                                          # grandes dalles sombres
        if abs(x) < 3:
            return dalle_f
        return dalle_f if math.floor(z / 8) % 2 else pave_f

    def place_porte(x, z):                                     # tapis de dalles 9 × 7 bordé de pavés sombres
        u, v = x + DEMI_COULOIR, Z_VILLE - z
        if v < 2 or v > 26 or u < 2 or u > 88:
            return pave_f
        return pave_c if (math.floor((u - 2) / 9.6) + math.floor((v - 2) / 6)) % 2 == 0 else c("pave")

    def rue_ou_canal(z_haut, tons, graine):
        def f(x, z):
            ax = abs(x)
            if ax >= DEMI_COULOIR - 2:                         # caniveaux le long des trottoirs
                return bord
            if ax < 3:                                         # bande centrale de dalles claires
                return dalle
            return _paves(x, z, z_haut, tons, graine)
        return f

    def eglise(x, z):                                          # damier de grandes dalles, bande centrale
        u, v = x + DEMI_COULOIR, Z_EGLISE - z
        if abs(x) < 3 or abs(x) >= DEMI_COULOIR - 2:
            return bord if abs(x) >= DEMI_COULOIR - 2 else c("pave_rouge")
        return dalle if (math.floor(u / 9) + math.floor(v / 9)) % 2 == 0 else pave_c

    def grandplace(x, z):
        return mosaique_place(x, z) or dallage_grandplace(x, z)

    def parvis(x, z):
        u = x + DEMI_COULOIR
        return dalle_f if (math.floor(u / 10) + math.floor(z / 8)) % 2 == 0 else pave_f

    X0, X1 = -DEMI_COULOIR, DEMI_COULOIR
    with b.group("Sol/Couloir"):
        sol_pixel(b, X0, X1, Z_PRAIRIE_FIN, Z_APPROCHE, 2, prairie)
        sol_pixel(b, X0, X1, Z_VILLE, Z_PRAIRIE_FIN, 2, tunnel)
        sol_pixel(b, X0, X1, Z_RUE, Z_VILLE, 2, place_porte)
        sol_pixel(b, X0, X1, Z_EGLISE, Z_RUE, 2, rue_ou_canal(Z_RUE, rue, 7))
        sol_pixel(b, X0, X1, Z_CANAL, Z_EGLISE, 2, eglise)
        sol_pixel(b, X0, X1, Z_GRANDPLACE, Z_CANAL, 2, rue_ou_canal(Z_CANAL, canal, 9))
        sol_pixel(b, X0, X1, Z_PARVIS, Z_GRANDPLACE, 2, grandplace)
        sol_pixel(b, X0, X1, Z_FIN_VILLE, Z_PARVIS, 2, parvis)
        sol_pixel(b, X0, X1, Z_SORTIE - 4, Z_FIN_VILLE, 2, tunnel)

    def trottoir(x, z):
        ax = abs(x)
        if z > Z_PRAIRIE_FIN:                                  # prairie : herbe et fleurs jusqu'aux clôtures
            return c("herbe_fonce") if ax < DEMI_COULOIR + 2 else _pre_fleuri(x, z, 0.05)
        if z > Z_VILLE or z <= Z_FIN_VILLE:
            return pave_f
        if Z_GRANDPLACE >= z > Z_PARVIS:
            return dallage_grandplace(x, z)
        if ax < DEMI_COULOIR + 2:                              # bordure de trottoir
            return bord
        if x > 0 and Z_CANAL >= z > Z_GRANDPLACE:              # quai du canal
            return c("quai") if math.floor(z / 6) % 2 else shade(c("quai"), 0.94)
        return dalle if math.floor(z / 8) % 2 else dalle_f

    with b.group("Sol/Trottoirs"):
        for s in (-1, 1):
            xa, xb = sorted((s * DEMI_COULOIR, s * X_BORD))
            sol_pixel(b, xa, xb, Z_SORTIE - 4, Z_APPROCHE, 2, trottoir)


def sol_ville(b: Builder) -> None:
    """Sol de la ville entre les trottoirs et les remparts : cours pavées en bandes, jardins au pied des remparts,
    quai de la rive droite ; grand-place en anneaux carrés. (Presque tout est couvert de maisons : motifs larges.)"""
    brun, brun_f = c("pave_brun"), shade(c("pave_brun"), 0.93)
    h, hf = c("herbe"), c("herbe_fonce")
    quai = c("quai")

    def couleur(x, z):
        ax = abs(x)
        if x > 0 and X_CANAL[0] <= x < X_CANAL[1] and Z_GRANDPLACE <= z < Z_CANAL:
            return None                                       # le canal pose son propre lit
        if x > 0 and X_CANAL[1] <= x < X_QUAI and Z_GRANDPLACE <= z < Z_CANAL:
            return quai
        if Z_GRANDPLACE >= z > Z_PARVIS and ax < X_GRANDPLACE:
            return dallage_grandplace(x, z)
        if ax > 113:                                          # jardins au pied des remparts
            return h if math.floor(z / 32) % 2 == 0 else hf
        if 95 < ax <= 113 and not (Z_GRANDPLACE >= z > Z_PARVIS):   # ruelle de la troisième rangée
            return c("terre_claire") if 95 < ax < 99 else (brun if math.floor(z / 24) % 2 else brun_f)
        if X_FOND_RUE - 8 > ax >= X_BORD + 18:                # ruelle derrière la première rangée
            return c("terre_claire")
        return brun if math.floor(z / 24) % 2 == 0 else brun_f

    with b.group("Sol/Ville"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_REMPART))
            sol_pixel(b, xa, xb, Z_FIN_VILLE, Z_VILLE, 2, couleur)


def sol_campagne(b: Builder) -> None:
    """Prairie fleurie devant la muraille (z 8 → -56) et champs extérieurs le long des remparts (|x| > 145)."""
    h, hc, hf = c("herbe"), c("herbe_claire"), c("herbe_fonce")
    terre = c("terre")

    def prairie(x, z):
        ax = abs(x)
        if -52 < z < -46 and X_BORD <= ax < 70:               # sentiers de terre vers les fermes
            return terre
        n = _bruit(x, z, 22, 5)
        return hc if n > 0.62 else (hf if n < 0.3 else h)

    def champs(x, z):
        ax = abs(x)
        if ax < 165:
            return hf if math.floor(z / 30) % 2 else h
        bande = math.floor((z + 7 * (x > 0)) / 38) % 4
        return (c("ble"), h, c("potager"), c("herbe_seche"))[bande]

    with b.group("Sol/Prairie"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_FOND))
            sol_pixel(b, xa, xb, Z_PRAIRIE_FIN + 4, Z_APPROCHE, 4, prairie)
    with b.group("Sol/Champs"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_EXT, s * X_FOND))
            sol_pixel(b, xa, xb, Z_FIN_VILLE, Z_PRAIRIE_FIN + 4, 6, champs)


# ---------------------------------------------------------------------------
# Murailles (porte d'entrée, remparts latéraux, tours d'angle, muraille intérieure)
# ---------------------------------------------------------------------------

def murailles(b: Builder) -> None:
    # muraille extérieure : façade extérieure (-Z local) tournée vers la prairie (+Z) → yaw 180
    place(b, "remparts", "porte_colossale", (0, 0, Z_MUR_EXT), yaw=180, group="Muraille/PorteEntree",
          attente=_attente_porte(LARGEUR_MUR_EXT, EP_MUR_EXT, H_MUR),
          variant=0, largeur=LARGEUR_MUR_EXT, hauteur=H_MUR, epaisseur=EP_MUR_EXT, ouverture=OUVERTURE, h_passage=H_PASSAGE)
    # muraille intérieure (repère final) : sa grande façade regarde la ville (+Z)
    place(b, "remparts", "porte_colossale", (0, 0, Z_MUR_INT), yaw=180, group="Muraille/PorteFinale",
          attente=_attente_porte(2 * X_FOND, EP_MUR_INT, H_MUR),
          variant=1, largeur=2 * X_FOND, hauteur=H_MUR, epaisseur=EP_MUR_INT, ouverture=OUVERTURE, h_passage=H_PASSAGE)
    # tours d'angle : deux à la jonction muraille extérieure / remparts, deux contre la muraille intérieure
    for j, z in enumerate((Z_MUR_EXT, Z_MUR_INT)):
        for s in (-1, 1):
            place(b, "remparts", "tour_angle", (s * X_TOUR, 0, z), yaw=180, group=f"Muraille/Tour{j}{'G' if s < 0 else 'D'}",
                  emprise=(COTE_TOUR, COTE_TOUR, H_TOUR), variant=2 * j + (s > 0), cote=COTE_TOUR, hauteur=H_TOUR)
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
    for i, (s, z) in enumerate(((-1, -160), (1, -330), (-1, -430))):
        x = s * (X_REMPART - 5)
        place(b, "remparts", "monte_charge", (x, 0, z), yaw=face_couloir(x), group=f"Muraille/MonteCharge{i}",
              emprise=(12, 10, H_MUR), variant=i % 3, hauteur=H_MUR)
    for i, (s, z) in enumerate(((1, -172), (-1, -300))):
        x = s * (X_REMPART - 4)
        place(b, "remparts", "escalier_mur", (x, 0, z), yaw=face_couloir(x), group=f"Muraille/Escalier{i}",
              emprise=(40, 8, H_MUR), variant=i, hauteur=H_MUR, longueur=40)


# ---------------------------------------------------------------------------
# Prairie hors les murs
# ---------------------------------------------------------------------------

def prairie(b: Builder) -> None:
    place(b, "monuments", "moulin", (-92, 0, -22), yaw=face_couloir(-92), group="Prairie/Moulin0", emprise=(12, 12, 36), variant=0)
    place(b, "monuments", "moulin", (-196, 0, -8), yaw=-60, group="Prairie/Moulin1", emprise=(12, 12, 36), variant=1)
    place(b, "monuments", "moulin", (186, 0, -20), yaw=70, group="Prairie/Moulin2", emprise=(12, 12, 36), variant=2)
    place(b, "batiments", "ferme", (-84, 0, -47), yaw=180, group="Prairie/Ferme0", emprise=(24, 14, 14), variant=0)
    place(b, "batiments", "ferme", (80, 0, -48), yaw=180, group="Prairie/Ferme1", emprise=(24, 14, 14), variant=1)
    info = place(b, "nature", "colline", (122, 0, -20), group="Prairie/Colline", emprise=(48, 30, 4), variant=0,
                 largeur=48, profondeur=30, hauteur=4)
    place(b, "nature", "arbre_geant", (122, info.get("hauteur", 4), -20), yaw=25, group="Prairie/ArbreGeant",
          emprise=(40, 40, 46), variant=0)
    for i, (x, z, v) in enumerate(((-146, -20, 0), (-196, -42, 1), (176, -44, 2))):
        place(b, "nature", "champ", (x, 0, z), group=f"Prairie/Champ{i}", emprise=(36, 24, 2), variant=v, largeur=36, profondeur=24)
    for i, (x, z) in enumerate(((-112, -48), (-120, -42), (-106, -38), (146, -50))):
        place(b, "nature", "meule_foin", (x, 0, z), group=f"Prairie/Meule{i}", emprise=(5, 5, 6), variant=i)
    for i, (x, z, v) in enumerate(((-66, 0, 0), (-150, 4, 1), (-226, -36, 2), (68, 2, 3), (156, -4, 0), (222, -44, 1))):
        place(b, "nature", "arbre", (x, 0, z), group=f"Prairie/Arbre{i}", emprise=(10, 10, 14), variant=v, taille=1.0 + 0.1 * (i % 3))
    for i, (x, z) in enumerate(((-72, -12), (-118, -4), (86, -8), (150, -28), (-170, -30), (206, -6))):
        place(b, "nature", "parterre_fleurs", (x, 0, z), group=f"Prairie/Fleurs{i}", emprise=(8, 6, 1), variant=i % 4,
              largeur=8, profondeur=6)
    for i, (x, z) in enumerate(((-62, -54), (-104, -54), (64, -54), (100, -54), (-226, -10))):
        place(b, "nature", "buisson", (x, 0, z), group=f"Prairie/Buisson{i}", emprise=(4, 4, 3), variant=i % 3)
    # clôtures de bois le long du chemin (côté campagne), avec un passage vers chaque ferme
    for s in (-1, 1):
        for i, z in enumerate((-4, -18, -32)):
            place(b, "mobilier", "cloture_bois", (s * 57, 0, z - 6), yaw=90, group=f"Prairie/Cloture{'G' if s < 0 else 'D'}{i}",
                  emprise=(12, 1, 3), longueur=12, variant=0)
    place(b, "mobilier", "poteau_indicateur", (-60, 0, 4), yaw=-90, group="Prairie/Indicateur", emprise=(4, 1, 7),
          textes=("MARCHÉ", "AUBERGE"), variant=0)
    place(b, "mobilier", "charrette", (-66, 0, -36), yaw=200, group="Prairie/Charrette", emprise=(5, 10, 5), variant=0)
    place(b, "mobilier", "bottes_foin", (-100, 0, -34), group="Prairie/Bottes", emprise=(5, 5, 3), variant=2)
    place(b, "mobilier", "abreuvoir", (66, 0, -36), yaw=180, group="Prairie/Abreuvoir", emprise=(6, 5, 4))
    place(b, "mobilier", "tas_bois", (98, 0, -40), yaw=180, group="Prairie/TasBois", emprise=(7, 3, 6))
    place(b, "mobilier", "brouette", (62, 0, -22), yaw=150, group="Prairie/Brouette", emprise=(3, 5, 2), variant=0)


# ---------------------------------------------------------------------------
# Ville
# ---------------------------------------------------------------------------

# Rangées (module:fonction, largeur le long du couloir, profondeur, paramètres). Façades en |x| = 55 (x = 79 au canal).
RUE_G = [
    ("batiments:maison_colombages", 18, 18, {"variant": 0, "etages": 3, "enseigne": "PAIN"}),
    ("batiments:maison_colombages", 16, 18, {"variant": 1, "etages": 4}),
    ("batiments:maison_colombages", 22, 18, {"variant": 2, "etages": 4, "enseigne": "AUBERGE"}),
    ("batiments:maison_colombages", 16, 18, {"variant": 3, "etages": 2}),
    ("batiments:maison_colombages", 20, 18, {"variant": 4, "etages": 3, "enseigne": "FLEURS"}),
]
RUE_D = [
    ("batiments:maison_colombages", 16, 18, {"variant": 2, "etages": 3}),
    ("batiments:maison_colombages", 22, 18, {"variant": 0, "etages": 4, "enseigne": "BÄCKEREI"}),
    ("batiments:maison_colombages", 18, 18, {"variant": 3, "etages": 3}),
    ("batiments:maison_colombages", 16, 18, {"variant": 1, "etages": 2, "enseigne": "TISSUS"}),
    ("batiments:maison_colombages", 20, 18, {"variant": 4, "etages": 4}),
]
CANAL_G = [
    ("batiments:maison_bourgeoise", 20, 18, {"variant": 0, "etages": 4}),
    ("batiments:maison_colombages", 16, 18, {"variant": 1, "etages": 3, "enseigne": "FROMAGES"}),
    ("batiments:maison_bourgeoise", 22, 18, {"variant": 1, "etages": 3}),
    ("batiments:maison_colombages", 16, 18, {"variant": 2, "etages": 4}),
    ("batiments:maison_bourgeoise", 20, 18, {"variant": 2, "etages": 4, "enseigne": "LIBRAIRIE"}),
    ("batiments:maison_colombages", 18, 18, {"variant": 3, "etages": 3, "enseigne": "HORLOGER"}),
]
CANAL_D = [   # rive droite du canal (façades en x = 79), un pont devant les maisons 0, 2 et 4
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
                     emprise=(larg, prof, 8 + 7 * kw.get("etages", 3)), **kw)
        poses.append((x, zc, larg, prof, info))
        z -= larg + ecart
    assert z > z_fin - ecart - 0.01, f"rangée {nom} trop longue ({z} < {z_fin})"
    return poses


def place_porte(b: Builder) -> None:
    """Place de la porte (-84 → -112) : puits, étals, charrettes et boulets au pied de la muraille."""
    place(b, "mobilier", "puits", (-72, 0, -98), group="Ville/PlacePorte/Puits", emprise=(6, 6, 10), variant=0)
    place(b, "mobilier", "charrette", (-60, 0, -92), yaw=10, group="Ville/PlacePorte/Charrette", emprise=(5, 10, 5), variant=1)
    place(b, "mobilier", "pile_boulets", (-84, 0, -90), group="Ville/PlacePorte/Boulets0", emprise=(4, 4, 3), variant=0)
    place(b, "mobilier", "pile_boulets", (-90, 0, -92), group="Ville/PlacePorte/Boulets1", emprise=(3, 3, 2), variant=1)
    place(b, "mobilier", "canon_affut", (-100, 0, -94), yaw=150, group="Ville/PlacePorte/Canon", emprise=(4, 8, 4), variant=0)
    for i, z in enumerate((-94, -104)):
        place(b, "mobilier", "etal", (50, 0, z), yaw=90, group=f"Ville/PlacePorte/Etal{i}", emprise=(9, 6, 7), variant=i)
    place(b, "mobilier", "caisses", (62, 0, -90), group="Ville/PlacePorte/Caisses", emprise=(5, 4, 4), variant=2)
    place(b, "mobilier", "tonneaux", (68, 0, -95), group="Ville/PlacePorte/Tonneaux", emprise=(4, 4, 3), variant=2)
    place(b, "mobilier", "poteau_indicateur", (-50, 0, -103), yaw=-90, group="Ville/PlacePorte/Indicateur", emprise=(4, 1, 7),
          textes=("MARCHÉ", "FONTAINE"), variant=1)
    for i, (x, z) in enumerate(((-112, -100), (86, -100), (-96, -106), (106, -101))):
        place(b, "nature", "arbre", (x, 0, z), group=f"Ville/PlacePorte/Arbre{i}", emprise=(10, 10, 14), variant=i % 4)


def place_eglise(b: Builder) -> None:
    """Place de l'église (-214 → -268) : église à gauche, placette au mât de fête et clocher à droite."""
    place(b, "monuments", "eglise", (-(X_BORD + 6 + 15), 0, -241), yaw=face_couloir(-1), group="Monuments/Eglise",
          emprise=(52, 30, 76), variant=0, largeur=52, profondeur=30)
    place(b, "monuments", "clocher", (106, 0, -246), yaw=face_couloir(1), group="Monuments/ClocherA",
          emprise=(12, 12, 66), variant=0, hauteur=66)
    place(b, "monuments", "mat_fete", (74, 0, -238), group="Ville/PlaceEglise/MatFete", emprise=(4, 4, 40), variant=0, hauteur=40)
    for i, (x, z) in enumerate(((64, -222), (90, -222), (90, -262), (64, -262))):
        place(b, "nature", "arbre", (x, 0, z), group=f"Ville/PlaceEglise/Arbre{i}", emprise=(10, 10, 14), variant=(i + 1) % 4)
    place(b, "mobilier", "puits", (82, 0, -252), group="Ville/PlaceEglise/Puits", emprise=(6, 6, 10), variant=1)
    for i, z in enumerate((-232, -246)):
        place(b, "mobilier", "banc", (53, 0, z), yaw=90, group=f"Ville/PlaceEglise/Banc{i}", emprise=(6, 2, 3), variant=i)
    for i, z in enumerate((-218, -264)):
        place(b, "mobilier", "bac_fleurs", (-58, 0, z), group=f"Ville/PlaceEglise/Bac{i}", emprise=(3, 2, 3), variant=i)


def quartier_canal(b: Builder) -> list:
    """Quartier du canal (-268 → -404) : canal et ponts à droite, marché à gauche."""
    zc = (Z_CANAL + Z_GRANDPLACE) / 2
    place(b, "nature", "canal", ((X_CANAL[0] + X_CANAL[1]) / 2, 0, zc), group="Canal/Canal",
          emprise=(X_CANAL[1] - X_CANAL[0], Z_CANAL - Z_GRANDPLACE, 1), variant=0,
          longueur=Z_CANAL - Z_GRANDPLACE, largeur=X_CANAL[1] - X_CANAL[0])
    poses_d = rangee(b, 1, CANAL_D, Z_CANAL - 2, Z_GRANDPLACE, "CanalD", x_facade=X_QUAI, ecart=3)
    for i, k in enumerate((0, 2, 4)):
        z = poses_d[k][1]
        place(b, "nature", "pont_arche", ((X_BORD + X_QUAI) / 2, 0, z), group=f"Canal/Pont{i}", emprise=(24, 7, 5),
              variant=i, portee=X_QUAI - X_BORD, largeur=7)
    poses_g = rangee(b, -1, CANAL_G, Z_CANAL - 2, Z_GRANDPLACE, "CanalG")
    # marché sur le trottoir de gauche
    place(b, "mobilier", "panneau_pied", (-50.5, 0, -273), yaw=-90, group="Ville/Marche/Panneau", emprise=(6, 2, 6), texte="MARCHÉ")
    for i, z in enumerate((-284, -294, -306, -318)):
        place(b, "mobilier", "etal", (-50, 0, z), yaw=-90, group=f"Ville/Marche/Etal{i}", emprise=(9, 6, 7), variant=i)
    place(b, "monuments", "clocher", (-106, 0, -372), yaw=face_couloir(-1), group="Monuments/ClocherB",
          emprise=(12, 12, 60), variant=1, hauteur=60)
    return poses_g + poses_d


X_RANG3 = 106            # axe de la troisième rangée (maisons simples, |x| 100-112), entre la seconde et le jardin du rempart

# Maisons du fond : (x, z, largeur le long du couloir, étages). Toutes regardent le couloir ; profondeur 12.
FOND_G = [
    # seconde rangée (|x| 81-93)
    (-X_FOND_RUE, -122, 14, 2), (-X_FOND_RUE, -146, 14, 3), (-X_FOND_RUE, -170, 14, 2), (-X_FOND_RUE, -194, 14, 3),
    (-X_FOND_RUE, -282, 14, 2), (-X_FOND_RUE, -302, 12, 3), (-X_FOND_RUE, -322, 14, 2), (-X_FOND_RUE, -344, 14, 3),
    (-X_FOND_RUE, -366, 12, 2),
    # troisième rangée (|x| 100-112), coupée de jardins et d'arbres
    (-X_RANG3, -121, 16, 3), (-X_RANG3, -139, 12, 2), (-X_RANG3, -168, 14, 3), (-X_RANG3, -186, 16, 2),
    (-X_RANG3, -222, 14, 2), (-X_RANG3, -240, 12, 3),
    (-X_RANG3, -282, 14, 3), (-X_RANG3, -300, 12, 2), (-X_RANG3, -318, 14, 3), (-X_RANG3, -356, 12, 2),
    (-X_RANG3, -392, 12, 3),
]
FOND_D = [
    (X_FOND_RUE, -122, 14, 3), (X_FOND_RUE, -146, 14, 2), (X_FOND_RUE, -170, 14, 3), (X_FOND_RUE, -194, 14, 2),
    (X_RANG3, -120, 14, 2), (X_RANG3, -138, 12, 3), (X_RANG3, -170, 16, 2), (X_RANG3, -188, 12, 3),
    (X_RANG3 + 1, -224, 14, 3), (X_RANG3 + 1, -264, 12, 2),
    # derrière la rive droite du canal (|x| 100-112)
    (X_RANG3, -284, 14, 2), (X_RANG3, -320, 14, 3), (X_RANG3, -338, 12, 2), (X_RANG3, -356, 14, 2),
    (X_RANG3, -374, 12, 3), (X_RANG3, -392, 14, 2),
]


def arriere_ville(b: Builder) -> None:
    """Seconde et troisième rangées (maisons simples), jardins et arbres entre les rangées et les remparts :
    vue des remparts ou d'avion, la ville est une mer de toits serrés ; de la rue, les faîtes de la seconde
    rangée dépassent entre les pignons de la première."""
    for nom, plan in (("FondG", FOND_G), ("FondD", FOND_D)):
        for i, (x, z, larg, etages) in enumerate(plan):
            place(b, "batiments", "maison_fond", (x, 0, z), yaw=face_couloir(x), group=f"Ville/{nom}/{i:02d}",
                  emprise=(larg, 12, 7 + 6 * etages), variant=(i * 3 + (x > 0) + (abs(x) > 95)) % 4, largeur=larg,
                  profondeur=12, etages=etages)
    # arbres des jardins : dans les trouées des rangées et sur les placettes
    arbres = ((-106, -153), (-106, -204), (-104, -340), (-112, -262), (-84, -398),
              (106, -154), (108, -205), (106, -302))
    for i, (x, z) in enumerate(arbres):
        place(b, "nature", "arbre", (x, 0, z), group=f"Ville/Jardins/Arbre{i}", emprise=(10, 10, 14), variant=i % 4,
              taille=1.0 + 0.15 * (i % 3))
    for i, (x, z) in enumerate(((-116, -150), (117, -128), (-117, -352), (116, -250), (-117, -232), (117, -300))):
        place(b, "nature", "buisson", (x, 0, z), group=f"Ville/Jardins/Buisson{i}", emprise=(4, 4, 3), variant=i % 4)


def grand_place(b: Builder) -> None:
    """Grand-place des œufs (-404 → -488) : maisons à arcades, beffroi, fontaine, arbres, réverbères."""
    for i, (zc, v) in enumerate(((-417, 0), (-446, 1), (-475, 2))):
        x = -(X_GRANDPLACE + 9)
        place(b, "batiments", "maison_arcades", (x, 0, zc), yaw=face_couloir(x), group=f"GrandPlace/ArcadesG{i}",
              emprise=(26, 18, 30), variant=v, largeur=26, profondeur=18, etages=3)
    for i, (zc, v) in enumerate(((-413, 3), (-479, 1))):
        x = X_GRANDPLACE + 9
        place(b, "batiments", "maison_arcades", (x, 0, zc), yaw=face_couloir(x), group=f"GrandPlace/ArcadesD{i}",
              emprise=(18, 18, 30), variant=v, largeur=18, profondeur=18, etages=3)
    place(b, "monuments", "beffroi", (X_GRANDPLACE + 13.5, 0, Z_PLACE), yaw=face_couloir(1), group="Monuments/Beffroi",
          emprise=(44, 30, 84), variant=0, largeur=44, profondeur=30)
    place(b, "monuments", "fontaine", (-72, 0, Z_PLACE), yaw=face_couloir(-1), group="GrandPlace/Fontaine",
          emprise=(16, 16, 12), variant=0)
    for i, (x, z) in enumerate(((-82, -410), (-82, -482), (78, -410), (78, -482))):
        place(b, "nature", "arbre", (x, 0, z), group=f"GrandPlace/Arbre{i}", emprise=(10, 10, 14), variant=(i + 2) % 4)
    for i, (x, z) in enumerate(((-72, -426), (-72, -466), (72, -430), (72, -462))):
        place(b, "nature", "parterre_fleurs", (x, 0, z), yaw=90, group=f"GrandPlace/Parterre{i}", emprise=(8, 6, 1),
              variant=i % 4, largeur=8, profondeur=6)
    for i, (x, z) in enumerate(((-58, -420), (-58, -472), (58, -420), (58, -472))):
        place(b, "mobilier", "reverbere", (x, 0, z), group=f"GrandPlace/Reverbere{i}", emprise=(5, 2, 12), variant=2)
    for i, (x, z, yaw) in enumerate(((-58, -440, 90), (-58, -452, 90), (62, -446, -90))):
        place(b, "mobilier", "banc", (x, 0, z), yaw=yaw, group=f"GrandPlace/Banc{i}", emprise=(6, 2, 3), variant=i)
    for i, (x, z) in enumerate(((-88, -405), (86, -405))):
        place(b, "mobilier", "drapeau", (x, 0, z), group=f"GrandPlace/Drapeau{i}", emprise=(6, 1, 14), variant=i, hauteur=14)
    for i, (x, z) in enumerate(((-66, -486), (66, -486))):
        place(b, "mobilier", "etal", (x, 0, z), yaw=180, group=f"GrandPlace/Etal{i}", emprise=(9, 6, 7), variant=i + 2)


def parvis(b: Builder) -> None:
    """Parvis de la muraille intérieure (-488 → -512) : dépôt de ravitaillement à gauche, tour de guet à droite."""
    # dépôt entre la tour gauche de la porte (|x| ≤ 73 jusqu'à z = -504) et le rempart, devant le talus (z ≥ -509)
    place(b, "monuments", "depot_ravitaillement", (-94.5, 0, -498.8), yaw=180, group="Parvis/Depot", emprise=(36, 20, 16),
          variant=0, largeur=36, profondeur=20)
    place(b, "monuments", "tour_guet", (86, 0, -500), yaw=face_couloir(1), group="Parvis/TourGuet", emprise=(10, 10, 40),
          variant=0, hauteur=40)
    # tout reste devant les tours de la porte (z > -504) ou entre elles et les remparts
    props = (("charrette", (-64, -494), 160, 2), ("pile_boulets", (-54, -500), 0, 0), ("caisses", (-69, -501), 0, 1),
             ("tonneaux", (64, -500), 0, 0), ("sacs", (58, -500), 0, 1), ("pile_boulets", (70, -494), 0, 1),
             ("charrette", (104, -497), 200, 3), ("canon_affut", (97, -500), 200, 1))
    for i, (fn, (x, z), yaw, v) in enumerate(props):
        place(b, "mobilier", fn, (x, 0, z), yaw=yaw, group=f"Parvis/{fn}{i}", emprise=(5, 5, 4), variant=v)


def exterieur(b: Builder) -> None:
    """Bosquets hors des remparts (vues aérienne et de côté seulement ; les champs sont peints au sol)."""
    for s in (-1, 1):
        cote = "G" if s < 0 else "D"
        for i, z in enumerate((-100, -236, -384)):
            place(b, "nature", "arbre", (s * (158 + 8 * (i % 2)), 0, z), group=f"Exterieur/Arbre{cote}{i}",
                  emprise=(10, 10, 14), variant=i % 4, taille=1.2)


def mats_fanions(b: Builder) -> None:
    """Guirlandes de fanions au-dessus de la grand-rue (corde à 38 studs) entre deux mâts sur les trottoirs."""
    f = _asset("mobilier", "guirlande_fanions")
    for i, z in enumerate((-134, -180, -300, -352, -412, -480)):
        n_g = len(b.parts)
        with b.group(f"Fanions/Guirlande{i + 1}"):
            for s in (-1, 1):
                with b.at((s * X_MAT, 0, z)):
                    b.box((-0.6, 0, -0.6), (0.6, H_FANIONS + 2, 0.6), c("bois"), name="Mat")
                    b.box((-1.0, 0, -1.0), (1.0, 1.2, 1.0), c("pave_fonce"), studs="top", name="Pied")
                    b.box((-0.9, H_FANIONS + 2, -0.9), (0.9, H_FANIONS + 2.4, 0.9), c("bois_moyen"), name="Chapeau")
                    b.ball((0, H_FANIONS + 2.9, 0), 0.5, c("or"), collide=False, name="Pommeau")
            if f:
                n0 = len(b.parts)
                f(b, (-(X_MAT - 0.6), H_FANIONS, z), (X_MAT - 0.6, H_FANIONS, z), n=14, creux=2.0, variant=i)
                _COMPTES.append(("mobilier", "guirlande_fanions", {}, len(b.parts) - n0, f"Fanions/Guirlande{i + 1}"))
        b.__dict__.setdefault("poses", []).append((f"Fanions/Guirlande{i + 1}", "guirlande_fanions", n_g, len(b.parts)))


def details_rue(b: Builder, poses) -> None:
    """Réverbères, bancs, tonneaux, caisses, bacs à fleurs au pied des façades (jamais dans le couloir)."""
    zs_reverberes = (-124, -160, -200, -286, -330, -376)
    for s in (-1, 1):
        for i, z in enumerate(zs_reverberes):
            x = s * 53
            place(b, "mobilier", "reverbere", (x, 0, z), yaw=face_couloir(x), group=f"Details/Reverbere{'G' if s < 0 else 'D'}{i}",
                  emprise=(2, 4, 11), variant=1)
    rng = np.random.default_rng(3)
    props = ["tonneaux", "bac_fleurs", "caisses", "banc", "sacs", "bac_fleurs"]
    interdits = list(zs_reverberes) + [-134, -180, -300, -352]
    k = 0
    for (x, zc, larg, prof, info) in poses:
        s = -1 if x < 0 else 1
        if abs(x) > X_BORD + prof / 2 + 1 or (s < 0 and -326 < zc < -276):     # rive droite du canal et marché : pas de props
            continue
        fn = props[k % len(props)]
        zp = zc + rng.uniform(-larg / 2 + 3, larg / 2 - 3)
        if min(abs(zp - zi) for zi in interdits) < 4:
            zp += 6 if zp + 6 < zc + larg / 2 else -6
        xp = s * (X_BORD - 3.6)
        yaw = face_couloir(xp) if fn == "banc" else 0
        place(b, "mobilier", fn, (xp, 0, zp), yaw=yaw, group=f"Details/{fn}{k}", emprise=(3, 3, 3), variant=k % 3)
        k += 1
    # bornes de pierre le long du quai (rive gauche du canal = trottoir droit)
    for i, z in enumerate(range(-276, -400, -16)):
        place(b, "mobilier", "borne", (54, 0, z), group=f"Details/BorneQuai{i}", emprise=(1, 1, 2), variant=1)


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
    """Toute pièce (solide ou non) au-dessus du couloir élargi |x| < 46 et sous `y_min` : la caméra Roblox
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


FEUILLAGES = ("arbre", "arbre_geant", "buisson", "parterre_fleurs")


def _accepte(ga: str, gb: str) -> str | None:
    """Contacts voulus entre deux poses (raison), comptés à part par --chevauchements."""
    if ga.startswith("Muraille/") and gb.startswith("Muraille/"):
        return "maçonnerie"            # tours d'angle noyées dans les murailles, segments bout à bout, équipements sur le talus
    paire = {ga.split("/")[0] + "/" + ga.split("/")[1][:4], gb.split("/")[0] + "/" + gb.split("/")[1][:4]}
    if paire == {"Canal/Cana", "Canal/Pont"}:
        return "bornes des ponts plantées dans la margelle"
    if paire == {"Canal/Pont", "Ville/Cana"}:
        return "rampes des ponts posées sur les seuils"
    return None
ASSISE = 0.8     # pied, tronc ou semelle enfoncés de moins de 0,8 dans ce qui les porte : posé, pas un recoupement


def _obb(p):
    return np.asarray(p.pos, float), np.asarray(p.rot, float).reshape(3, 3), np.asarray(p.size, float) / 2


def _penetration(a, bb) -> float:
    """Profondeur d'interpénétration de deux boîtes orientées (axes séparateurs) ; 0 si elles ne se touchent pas.
    Coins, cylindres et boules sont traités comme leur boîte (contrôle prudent)."""
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
    de plus de `tol` et profondeur maximale. Le sol plat et les repères sont ignorés (tout y est posé). Les
    feuillages (arbres, buissons, parterres) sans collision qui débordent sur un voisin sont rangés à part
    (`feuillage`) ; une pièce enfoncée de moins de `ASSISE` dans ce qui la porte est posée, pas recoupée."""
    n = len(b.parts)
    etiquette = [None] * n
    fonction = [""] * n
    for (g, fn, n0, n1) in getattr(b, "poses", []):
        for i in range(n0, n1):
            if etiquette[i] is None:
                etiquette[i], fonction[i] = g, fn
    actifs = []
    for i, p in enumerate(b.parts):
        if p.transparency >= 1:
            continue
        if etiquette[i] is None:
            racine = p.group.split("/")[0]
            if racine == "Reperes":
                continue
            lo, hi = _bornes(p)
            if racine == "Sol" and hi[1] <= 0.6:
                continue
            morceaux = p.group.split("/")
            etiquette[i] = "/".join(morceaux[:2]) if racine != "Sol" else f"Sol/{p.name}"
        actifs.append(i)
    boites = {i: _bornes(b.parts[i]) for i in actifs}
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
                inter = np.minimum(hi_i, hi_j) - np.maximum(lo_i, lo_j)
                if np.any(inter <= tol):
                    continue
                if inter[1] <= ASSISE and (hi_i[1] - hi_j[1]) * (lo_i[1] - lo_j[1]) > 0:
                    continue                   # assise : l'un est posé sur l'autre
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
    ap.add_argument("--chevauchements", action="store_true", help="liste les assets posés qui se recoupent")
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
    if args.chevauchements:
        res = chevauchements(b)
        durs = {k: v for k, v in res.items() if not v["feuillage"] and not _accepte(*k)}
        voulus = {k: _accepte(*k) for k in res if _accepte(*k)}
        print(f"chevauchements : {len(durs)} paires de poses (+ {len(res) - len(durs) - len(voulus)} de feuillage, "
              f"{len(voulus)} contacts voulus)")
        for (ga, gb), v in sorted(res.items(), key=lambda kv: -kv[1]["profondeur"]):
            tag = f"[{voulus[(ga, gb)]}] " if (ga, gb) in voulus else ("feuillage " if v["feuillage"] else "")
            print(f"  {tag}{v['profondeur']:6.2f}  {v['paires']:4d}  {ga}  <->  {gb}   {v['exemple']}")


if __name__ == "__main__":
    main()
