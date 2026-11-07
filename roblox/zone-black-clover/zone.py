#!/usr/bin/env python3
"""Plan de la zone Black Clover (royaume de mages aux portes d'un royaume démoniaque) en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course, très large, occupe x ∈ [-45, 45] (90 studs), bordé d'accotements jusqu'à |x| = 55 ;
- on arrive par +Z (abords z 40 → 0, groupe `Abords`, à supprimer quand les zones sont mises bout à bout) et on
  court vers -Z ; la zone descend des confins pauvres d'un royaume de mages jusqu'aux portes d'un royaume démoniaque,
  de plus en plus sombre :
  PORTE D'ENTRÉE (deux tours rondes à toits coniques, z 0 → -32), CHAMPS (-32 → -80, côtes géantes à droite),
  VILLAGE ABANDONNÉ (-80 → -196, église à gauche, CRÂNE DE DÉMON cornu sur sa colline à droite),
  BOURG DE LA TOUR AUX GRIMOIRES (-196 → -300, la tour à gauche), CHAMP DE BATAILLE DES MAGES (-300 → -404, ruines,
  AQUEDUC en travers à z = -352), PLACE RITUELLE des œufs (cercle magique de rayon 34 centré en z = -448, arbre
  démoniaque à droite, îlots flottants à gauche) et CHÂTEAU DÉMONIAQUE (-498 → -548) dont la porte (100 × 40,
  arc brisé au-dessus) débouche en z = -548 sur la zone suivante ;
- côtés : champs labourés et blé, puis forêt de sapins sombres et d'arbres morts, puis falaises noires à cristaux
  violets ; la montagne couronnée d'un château (capitale du royaume) se dresse au loin à gauche.

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

from kit import Builder, mix, shade  # noqa: E402
from palette import c  # noqa: E402
from textures import mask_rects  # noqa: E402

# ---------------------------------------------------------------------------
# Dimensions (studs)
# ---------------------------------------------------------------------------
DEMI_COULOIR = 45        # couloir de course x ∈ [-45, 45] : 90 studs de large
X_BORD = 55              # bord des accotements = alignement des façades
X_LIBRE = 46             # rien au-dessus de |x| < 46 sous Y_LIBRE (caméra Roblox)
Y_LIBRE = 30
X_FOND = 239             # fin du sol (côtés en cases de 4 : 55 → 239) ; murs invisibles en |x| = 238-239
Z_ABORDS = 40            # sol d'approche (groupe Abords) de z = 0 à z = +40
Z_ENTREE = 0

Z_PORTE = -16            # axe des tours de la porte d'entrée et de l'enceinte
X_TOUR_PORTE = 63        # axe des tours rondes (faces intérieures en |x| = 50)
R_TOUR_PORTE = 13
H_TOUR_PORTE = 58        # corps des tours (toit conique au-dessus, jusqu'à ≈ 96)
OUVERTURE_PORTE = 100    # entre les faces intérieures des tours
H_ENCEINTE = 34          # enceinte qui part des tours vers les côtés
EP_ENCEINTE = 8
Z_CHAMPS = -32           # fin du seuil de la porte, début des champs
Z_VILLAGE = -80
Z_BOURG = -196
Z_BATAILLE = -300
Z_AQUEDUC = -352         # axe de l'aqueduc ruiné (tablier en travers du couloir)
H_AQUEDUC = 62           # dessus du tablier
DESSOUS_AQUEDUC = 36     # dessous de l'arche centrale (au-dessus de |x| < 47)
OUVERTURE_AQUEDUC = 94   # entre les piles qui encadrent le couloir (faces en |x| = 47)
RUPTURE_AQUEDUC = (100.0, 164.0)   # tronçon effondré (x local), à droite
Z_PLACE_DEBUT = -404
Z_PLACE = -448           # centre du cercle magique (82 % du parcours)
R_PLACE = 34
X_PLACE = 90             # la place rituelle s'élargit jusqu'à |x| = 90
Z_CHATEAU = -498         # façade du château (porte)
Z_SORTIE = -548          # sortie vers la zone suivante
PROF_CHATEAU = Z_CHATEAU - Z_SORTIE            # 50
OUVERTURE = 100          # porte du château : |x| < 50
H_PASSAGE = 40           # montants de la porte ; l'arc brisé monte au-dessus (≈ 66)

# Grands repères
X_COLLINE, Z_COLLINE, H_COLLINE = 132, -158, 28          # colline du crâne (à droite)
YAW_CRANE = 125                                          # le crâne regarde l'entrée et le couloir
X_COTES, Z_COTES, YAW_COTES = 118, -70, 110              # côtes géantes dans les labours (à droite), échine ≈ le long du couloir
X_TOUR, Z_TOUR, R_TOUR, H_TOUR = -94, -250, 16, 118      # tour aux grimoires (à gauche)
X_ARBRE, Z_ARBRE, H_ARBRE = 150, -462, 150               # arbre démoniaque (à droite)
X_MONTAGNE, Z_MONTAGNE = -200, -112                      # montagne de la capitale (lointain, à gauche)

VERSION = "0.1"

# Budgets de pièces par pose (contrôlés par --stats, voir SPECS.md et CONCEPTION.md § 7).
BUDGETS = {
    ("remparts", "porte_entree"): 620, ("remparts", "ruine_tour"): 110, ("remparts", "arche_effondree"): 90,
    ("remparts", "aqueduc"): 560,
    ("batiments", "chaumiere"): 60, ("batiments", "maison_pierre"): 90, ("batiments", "maison_ruine"): 50,
    ("batiments", "grange"): 65, ("batiments", "moulin"): 95, ("batiments", "eglise"): 300,
    ("batiments", "maison_haute"): 95, ("batiments", "taverne"): 150, ("batiments", "halle"): 110,
    ("batiments", "maison_fond"): 28,
    ("monuments", "colline_crane"): 280, ("monuments", "crane_demon"): 680, ("monuments", "cotes_geantes"): 170,
    ("monuments", "tour_grimoires"): 620, ("monuments", "montagne_capitale"): 150,
    ("abime", "chateau_demon"): 1150, ("abime", "arbre_demon"): 420, ("abime", "ilot_flottant"): 90,
    ("abime", "obelisque"): 26, ("abime", "racine_geante"): 30, ("abime", "cristaux"): 14,
}
BUDGET_MOBILIER = 40
_COMPTES: list = []      # (module, fn, params, pièces, groupe) de chaque pose livrée
_POSES_BUDGET: list = []  # (module, fn, budget) de chaque pose, livrée ou non


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
    L = params.get("longueur", 40)
    if fn == "mur_enceinte":
        return int(math.ceil(12 + 1.1 * L))
    if fn == "ruine_mur":
        return int(math.ceil(14 + 1.4 * L))
    if fn == "falaise":
        return int(math.ceil(14 + 1.0 * L))
    return BUDGETS.get((module, fn), 10 ** 6)


def place(b: Builder, module: str, fn: str, pos, yaw: float = 0.0, group: str | None = None, emprise=(16, 16, 16),
          attente=None, **params) -> dict:
    """Pose un asset ; si le module n'existe pas encore, pose un bloc translucide de même emprise
    (ou la silhouette `attente(b)` pour ce qui enjambe le couloir)."""
    f = _asset(module, fn)
    _POSES_BUDGET.append((module, fn, _budget(module, fn, params)))
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


ROSE = "#ff4fd8"


def _attente_porte_entree(b) -> None:
    """Silhouette d'attente de la porte d'entrée : deux tours rondes à toit conique, rien au-dessus du couloir."""
    for s in (-1, 1):
        b.cyl((s * X_TOUR_PORTE, H_TOUR_PORTE / 2, 0), R_TOUR_PORTE, H_TOUR_PORTE, ROSE, transparency=0.5)
        b.cyl((s * X_TOUR_PORTE, H_TOUR_PORTE + 12, 0), R_TOUR_PORTE + 1, 24, ROSE, transparency=0.5)
        b.cyl((s * X_TOUR_PORTE, H_TOUR_PORTE + 32, 0), 4, 16, ROSE, transparency=0.5)


def _attente_aqueduc(b) -> None:
    """Silhouette d'attente de l'aqueduc : piles hors du couloir, tablier au-dessus de DESSOUS_AQUEDUC."""
    xs = [OUVERTURE_AQUEDUC / 2 + 5 + 32 * k for k in range(7)]
    for s in (-1, 1):
        for x in xs:
            if x > X_FOND - 4 or (s > 0 and RUPTURE_AQUEDUC[0] < x < RUPTURE_AQUEDUC[1]):
                continue
            b.box((s * x - 5, 0, -5), (s * x + 5, H_AQUEDUC - 12, 5), ROSE, transparency=0.5)
    for (xa, xb) in ((-X_FOND, RUPTURE_AQUEDUC[0]), (RUPTURE_AQUEDUC[1], X_FOND)):
        b.box((xa, DESSOUS_AQUEDUC + 6, -6), (xb, H_AQUEDUC, 6), ROSE, transparency=0.5)


def _attente_chateau(b) -> None:
    """Silhouette d'attente du château : falaise et ailes de part et d'autre, linteau au-dessus de H_PASSAGE,
    donjon central et deux tours de porte."""
    d = PROF_CHATEAU / 2
    for s in (-1, 1):
        xa, xb = sorted((s * OUVERTURE / 2, s * X_FOND))
        b.box((xa, 0, -d), (xb, 46, d), ROSE, transparency=0.5)
        b.box((s * 59 - 9, 0, -d), (s * 59 + 9, 110, -d + 18), ROSE, transparency=0.5)
        b.box((s * 120 - 14, 46, -d + 8), (s * 120 + 14, 84, d), ROSE, transparency=0.5)
    b.box((-OUVERTURE / 2, H_PASSAGE + 26, -d), (OUVERTURE / 2, 92, d), ROSE, transparency=0.5)
    b.box((-22, 92, -d + 12), (22, 150, d), ROSE, transparency=0.5)


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
    """Bruit déterministe dans [0, 1[ pour le choix des teintes."""
    h = (i * 73856093) ^ (j * 19349663) ^ (k * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0


def _bruit(x: float, z: float, echelle: float, k: int = 0) -> float:
    """Bruit de valeur lissé (taches d'herbe, de boue, de cendre)."""
    gx, gz = x / echelle, z / echelle
    i, j = math.floor(gx), math.floor(gz)
    fx, fz = gx - i, gz - j
    fx, fz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    a, b_ = _hash(i, j, k), _hash(i + 1, j, k)
    c_, d = _hash(i, j + 1, k), _hash(i + 1, j + 1, k)
    return (a + (b_ - a) * fx) * (1 - fz) + (c_ + (d - c_) * fx) * fz


def _paves(u: float, v: float, tons, graine: int, L: float = 6, H: float = 4):
    """Pavés en rangées décalées (pierres L × H), trois teintes."""
    rang = math.floor(v / H)
    h = _hash(math.floor((u + (L / 2 if rang % 2 else 0)) / L), rang, graine)
    return tons[0] if h < 0.5 else (tons[1] if h < 0.78 else tons[2])


# Cratères du champ de bataille (x, z, rayon) : brûlis noir, bord de cendre, fissures incandescentes
CRATERES = ((-22, -322, 7), (26, -340, 6), (-6, -384, 8), (30, -396, 5), (-34, -362, 4))


def _cratere(x: float, z: float):
    """(rayon relatif, angle) dans le cratère le plus proche, ou None."""
    for (cx, cz, r) in CRATERES:
        d = math.hypot(x - cx, z - cz)
        if d < r:
            return d / r, math.atan2(z - cz, x - cx), (cx + cz) % 7
    return None


def _fissure_cratere(x: float, z: float) -> bool:
    k = _cratere(x, z)
    if k is None:
        return False
    t, a, g = k
    if t < 0.22:
        return True
    rayons = 5
    s = ((a + g) / (2 * math.pi / rayons)) % 1.0
    return 0.3 < t < 0.85 and min(s, 1 - s) < 0.07 / max(t, 0.3)


def couleur_couloir(x: float, z: float):
    """Sol du couloir (|x| < 45), un motif par séquence (motifs larges : peu de pièces)."""
    ax = abs(x)
    u = x + DEMI_COULOIR
    if z > Z_ENTREE:                                              # abords : vieille route pavée, mousse aux bords
        if ax > 40 and _bruit(x, z, 8, 2) > 0.55:
            return c("mousse")
        return _paves(u, Z_ABORDS - z, (c("pave"), c("pave_clair"), c("pave_fonce")), 3, L=10, H=6)
    if z > Z_CHAMPS:                                              # seuil de la porte : grandes dalles en damier
        v = -z
        if v < 2 or v > 30:
            return c("bordure")
        return c("dalle_claire") if (math.floor(u / 10) + math.floor((v - 2) / 7)) % 2 == 0 else c("dalle")
    if z > Z_VILLAGE:                                             # chemin de terre à ornières
        if 8 <= ax < 12 or 28 <= ax < 32:
            return c("terre_fonce")
        if ax > 40:
            return c("herbe_seche")
        return c("terre") if _bruit(x, z, 18, 1) > 0.45 else c("terre_claire")
    if z > Z_BOURG:                                               # pavés usés du village, rigole centrale
        v = Z_VILLAGE - z
        if ax < 2:
            return c("bordure")
        if v % 36 < 2 and v > 4:
            return c("pave_fonce")
        return _paves(u, v, (c("pave_brun"), c("pave_brun_clair"), c("pave_fonce")), 7, L=10, H=6)
    if z > Z_BATAILLE:                                            # dalles sombres du bourg, appareil en panneresse
        v = Z_BOURG - z
        if ax < 2:
            return c("bordure")
        rang = math.floor(v / 6)
        k = math.floor((u + (6 if rang % 2 else 0)) / 12)
        return c("dalle_claire") if (k + rang) % 3 == 0 else c("dalle")
    if z > Z_PLACE_DEBUT:                                         # prairie piétinée, cendre et cratères
        k = _cratere(x, z)
        if k is not None:
            return c("cendre_fonce") if k[0] > 0.78 else c("brulis")
        if ax < 6:
            return c("boue")
        n = _bruit(x, z, 18, 9)
        return c("cendre") if n > 0.72 else (c("herbe_fonce") if n < 0.4 else c("herbe_grise"))
    if z > Z_CHATEAU:                                             # place rituelle : anneaux carrés de dalles noires
        k = math.floor(max(ax, abs(z - Z_PLACE)) / 6)
        return c("dalle_noire") if k % 2 == 0 else c("dalle_rituelle")
    if 6 <= ax < 8:                                               # porte du château : basalte, deux fils de lumière
        return None
    v = Z_CHATEAU - z
    return c("basalte_clair") if (math.floor(u / 10) + math.floor(v / 10)) % 2 == 0 else c("basalte")


def neon_couloir(x: float, z: float):
    """Cases lumineuses du couloir (posées en Neon dans les trous laissés par couleur_couloir_plein)."""
    if Z_BATAILLE >= z > Z_PLACE_DEBUT and _cratere(x, z) is not None and _fissure_cratere(x, z):
        return c("feu_cramoisi")
    if z <= Z_CHATEAU and 6 <= abs(x) < 8:
        return c("lueur_cramoisie")
    return None


def couleur_couloir_plein(x: float, z: float):
    if neon_couloir(x, z) is not None:
        return None
    return couleur_couloir(x, z)


def couleur_bords(x: float, z: float):
    """Accotements (45 ≤ |x| < 55) : bordure de pierre puis herbe, trottoir, cendre ou dalles selon la séquence."""
    ax = abs(x)
    if z > Z_CHAMPS:
        return c("bordure") if ax < 47 else c("herbe_fonce")
    if z > Z_BOURG:
        if ax < 47:
            return c("bordure")
        return c("herbe_seche") if _bruit(x, z, 12, 13) > 0.55 else (c("terre") if z <= Z_VILLAGE else c("herbe"))
    if z > Z_BATAILLE:
        return c("bordure") if ax < 47 else (c("dalle_claire") if math.floor(z / 6) % 2 else c("dalle"))
    if z > Z_PLACE_DEBUT:
        return c("cendre_fonce") if _bruit(x, z, 12, 14) > 0.6 else c("herbe_grise")
    if z > Z_CHATEAU:
        k = math.floor(max(ax, abs(z - Z_PLACE)) / 6)
        return c("dalle_noire") if k % 2 == 0 else c("dalle_rituelle")
    return c("basalte")


def couleur_cotes(x: float, z: float):
    """Sol au-delà des accotements (|x| ≥ 55, cases de 4) : prés, parcelles de labours et de blé, cours, sous-bois,
    prairie cendrée, roche noire, dalles de la place rituelle."""
    ax = abs(x)
    s = 1 if x > 0 else 0
    if z > Z_CHAMPS:                                              # abords et pied de l'enceinte : prés sombres
        return c("herbe") if _bruit(x, z, 26, 21) > 0.45 else c("herbe_fonce")
    if z > Z_BOURG:                                               # champs en parcelles, cours devant les maisons
        if ax < 75:
            return c("terre") if z > Z_VILLAGE else c("herbe_seche")
        if ax >= 175:                                             # lisière de la forêt
            return c("herbe_fonce")
        du, dv = ax - 75, Z_CHAMPS - z
        if du % 36 < 4 or dv % 32 < 4:                            # chemins entre les parcelles
            return c("terre_fonce")
        kind = int(_hash(math.floor(du / 36), math.floor(dv / 32), 31 + s) * 5)
        if kind <= 1:                                             # labours : sillons parallèles au couloir
            return c("labour") if math.floor(ax / 4) % 2 else c("labour_fonce")
        if kind == 2:
            return c("ble")
        if kind == 3:
            return c("ble_fonce")
        return c("herbe_morte")
    if z > Z_BATAILLE:                                            # bourg puis sous-bois
        if ax < 79:
            return c("pave_fonce") if math.floor(z / 12) % 2 else c("pave")
        return c("herbe_fonce") if _bruit(x, z, 24, 26) > 0.45 else c("mousse")
    if z > Z_PLACE_DEBUT:                                         # prairie brumeuse, cendre, roche au pied des falaises
        if ax >= 171:
            return c("roche_noire")
        n = _bruit(x, z, 24, 28)
        return c("cendre") if n > 0.7 else (c("herbe_fonce") if n < 0.38 else c("herbe_grise"))
    if z > Z_CHATEAU:
        if ax < X_PLACE + 1:
            k = math.floor(max(ax, abs(z - Z_PLACE)) / 6)
            return c("dalle_noire") if k % 2 == 0 else c("dalle_rituelle")
        return c("brulis") if _bruit(x, z, 20, 29) > 0.55 else c("roche_noire")
    return c("basalte")


def sol(b: Builder) -> None:
    X0, X1 = -DEMI_COULOIR, DEMI_COULOIR
    with b.group("Abords/Sol/Couloir"):
        sol_pixel(b, X0, X1, Z_ENTREE, Z_ABORDS, 2, couleur_couloir)
    with b.group("Sol/Couloir"):
        sol_pixel(b, X0, X1, Z_SORTIE, Z_ENTREE, 2, couleur_couloir_plein)
        sol_pixel(b, X0, X1, Z_SORTIE, Z_ENTREE, 2, neon_couloir, material="Neon", studs="none")
    for s in (-1, 1):
        xa, xb = sorted((s * DEMI_COULOIR, s * X_BORD))
        with b.group("Abords/Sol/Bords"):
            sol_pixel(b, xa, xb, Z_ENTREE, Z_ABORDS, 2, couleur_bords)
        with b.group("Sol/Bords"):
            sol_pixel(b, xa, xb, Z_SORTIE, Z_ENTREE, 2, couleur_bords)
        xa, xb = sorted((s * X_BORD, s * X_FOND))
        with b.group("Abords/Sol/Cotes"):
            sol_pixel(b, xa, xb, Z_ENTREE, Z_ABORDS, 4, couleur_cotes)
        with b.group("Sol/Cotes"):
            sol_pixel(b, xa, xb, Z_SORTIE, Z_ENTREE, 4, couleur_cotes)


def cercle_magique(b: Builder) -> None:
    """Cercle magique de la place des œufs (rayon 34) : estrade de disques concentriques de 0,1 de haut chacun
    (anneaux Neon violets, bande de glyphes abstraits, carré inscrit en losange, cœur cramoisi).
    Géométrie générique : ni étoile (5, 6 ou 8 branches), ni trèfle, ni lettre d'un alphabet réel."""
    z = Z_PLACE
    with b.group("Sol/Cercle"):
        y = 0.0

        def disque(r, col, h=0.1, neon=False):
            nonlocal y
            b.cyl((0, y + h / 2, z), r, h, c(col), name="Cercle", studs="none" if neon else "top",
                  **({"material": "Neon", "shadow": False} if neon else {}))
            y += h

        disque(34.0, "obsidienne", 0.15)
        disque(33.0, "lueur_violette", neon=True)
        disque(31.8, "dalle_rituelle")
        # bande de glyphes : 24 marques abstraites (barre + point) entre r = 27 et r = 31
        for k in range(24):
            a = 2 * math.pi * k / 24
            ca, sa = math.cos(a), math.sin(a)
            long_ = 3.0 if k % 3 == 0 else 1.8
            r = 29.2
            b.boxc((r * ca, y + 0.05, z + r * sa), (long_, 0.1, 0.6), c("lueur_violette"), yaw=-math.degrees(a),
                   material="Neon", shadow=False, name="Glyphe")
            if k % 3:
                r2 = 30.6 if k % 2 else 27.6
                b.boxc((r2 * ca, y + 0.05, z + r2 * sa), (0.6, 0.1, 0.6), c("lueur_violette_pale"), yaw=-math.degrees(a),
                       material="Neon", shadow=False, name="Glyphe")
        disque(26.2, "lueur_violette", neon=True)
        disque(25.0, "dalle_noire")
        # carré inscrit en losange (sommets sur les axes) : 4 barres Neon
        for (sx, sz) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            b.boxc((sx * 12.0, y + 0.05, z + sz * 12.0), (24 * math.sqrt(2) + 0.8, 0.1, 0.8), c("lueur_cramoisie"),
                   yaw=45 if sx * sz > 0 else -45, material="Neon", shadow=False, name="Losange")
        disque(12.0, "lueur_violette", neon=True)
        disque(11.0, "dalle_rituelle")
        disque(3.0, "lueur_cramoisie", neon=True)


# ---------------------------------------------------------------------------
# Séquence 1 : abords et porte d'entrée
# ---------------------------------------------------------------------------

def abords(b: Builder) -> None:
    """Abords (z 0 → +40, groupe Abords) : arbres morts et sapins, poteau indicateur, lucioles."""
    for i, (x, z, fn, v) in enumerate(((-66, 30, "arbre_mort", 0), (-92, 14, "sapin_sombre", 1), (-150, 26, "sapin_sombre", 0),
                                       (70, 24, "sapin_sombre", 2), (98, 8, "arbre_mort", 2), (168, 30, "sapin_sombre", 0))):
        place(b, "mobilier", fn, (x, 0, z), group=f"Abords/Arbre{i}", emprise=(8, 8, 14), variant=v,
              hauteur=14 + 2 * (i % 3))
    place(b, "mobilier", "poteau_indicateur", (-51, 0, 26), yaw=90, group="Abords/Indicateur", emprise=(1, 13, 8),
          textes=("VILLAGE", "CHÂTEAU"), variant=1)
    for s in (-1, 1):                                       # nuages de lucioles devant les tours (refBC2)
        place(b, "mobilier", "lucioles", (s * 62, 3, 10), group=f"Abords/Lucioles{'GD'[s > 0]}", emprise=(16, 16, 20),
              variant=0, rayon=8, hauteur=20, nombre=24)


def porte(b: Builder) -> None:
    """Porte d'entrée (refBC2) : deux tours rondes à toit conique de part et d'autre du couloir, vantaux ouverts,
    enceinte crénelée vers les côtés, braseros et lucioles dorées."""
    place(b, "remparts", "porte_entree", (0, 0, Z_PORTE), yaw=180, group="Porte/Entree", attente=_attente_porte_entree,
          variant=0, ouverture=OUVERTURE_PORTE, rayon_tour=R_TOUR_PORTE, hauteur_tour=H_TOUR_PORTE,
          hauteur_mur=H_ENCEINTE)
    x_debut = X_TOUR_PORTE + R_TOUR_PORTE                       # 76 : l'enceinte part du flanc des tours
    L = (X_FOND - x_debut) / 4                                  # 41
    for s in (-1, 1):
        for k in range(4):
            xc = s * (x_debut + L * (k + 0.5))
            place(b, "remparts", "mur_enceinte", (xc, 0, Z_PORTE), yaw=180, group=f"Porte/Enceinte{'GD'[s > 0]}{k}",
                  emprise=(L, EP_ENCEINTE, H_ENCEINTE), variant=(k + 2 * (s > 0)) % 4, longueur=L, hauteur=H_ENCEINTE,
                  epaisseur=EP_ENCEINTE)
    for s in (-1, 1):
        for z in (-3.0, -36.0):
            place(b, "mobilier", "brasero", (s * 48.6, 0, z), group=f"Porte/Brasero{'GD'[s > 0]}{int(-z)}", emprise=(3, 3, 6),
                  variant=0)
    # lucioles dorées : un nuage haut entre les tours (au-dessus de 31) ; les nuages bas sont dans les abords
    place(b, "mobilier", "lucioles", (0, 33, Z_PORTE), group="Porte/LuciolesHaut", emprise=(44, 44, 26), variant=0,
          rayon=22, hauteur=26, nombre=36)


# ---------------------------------------------------------------------------
# Séquences 2 et 3 : champs et village abandonné, crâne de démon
# ---------------------------------------------------------------------------

def rangee(b: Builder, s: int, plan, nom: str, x_facade: float = X_BORD) -> list:
    """Pose une rangée de bâtiments le long du couloir (avant tourné vers le couloir) ; plan : (module:fn, zc,
    largeur le long du couloir, profondeur, paramètres)."""
    poses = []
    for i, (kind, zc, larg, prof, params) in enumerate(plan):
        mod, fn = kind.split(":")
        kw = dict(params)
        kw.setdefault("largeur", larg)
        kw.setdefault("profondeur", prof)
        x = s * (x_facade + prof / 2)
        info = place(b, mod, fn, (x, 0, zc), yaw=face_couloir(x), group=f"{nom}/{i:02d}_{fn}",
                     emprise=(larg, prof, 8 + 7 * kw.get("etages", 2)), **kw)
        poses.append((x, zc, larg, prof, info))
    return poses


CHAMPS_G = [
    ("batiments:grange", -50, 20, 14, {"variant": 0}),
    ("batiments:chaumiere", -70, 12, 12, {"variant": 3}),
]
CHAMPS_D = [
    ("batiments:chaumiere", -46, 14, 12, {"variant": 1}),
]
VILLAGE_G = [
    ("batiments:chaumiere", -88, 14, 12, {"variant": 0}),
    ("batiments:maison_pierre", -106, 16, 14, {"variant": 0, "etages": 2, "enseigne": "FORGE"}),
    ("batiments:maison_ruine", -123, 12, 12, {"variant": 0}),
    ("batiments:chaumiere", -186, 14, 12, {"variant": 2}),
]
VILLAGE_D = [
    ("batiments:maison_pierre", -88, 16, 14, {"variant": 1, "etages": 2}),
    ("batiments:chaumiere", -106, 14, 12, {"variant": 1}),
    ("batiments:maison_ruine", -124, 12, 12, {"variant": 1}),
    ("batiments:chaumiere", -143, 14, 12, {"variant": 4}),
    ("batiments:maison_ruine", -161, 12, 12, {"variant": 2}),
    ("batiments:maison_pierre", -182, 16, 14, {"variant": 2, "etages": 2, "enseigne": "AUBERGE"}),
]
# Maisons du second rang (x, z, largeur, étages), toutes tournées vers le couloir
FOND = [(-104, -92, 12, 1), (-106, -186, 12, 2), (-100, -207, 12, 2), (-104, -292, 14, 2), (98, -232, 12, 2),
        (100, -284, 12, 1)]


def champs(b: Builder) -> list:
    """Champs (z -32 → -80) : grange et chaumière à gauche, moulin en retrait ; à droite une chaumière, les CÔTES
    GÉANTES du démon qui sortent des labours, meules, puits, charrette, clôtures."""
    poses = rangee(b, -1, CHAMPS_G, "Champs/G", x_facade=57)
    poses += rangee(b, 1, CHAMPS_D, "Champs/D", x_facade=57)
    place(b, "batiments", "moulin", (-112, 0, -62), yaw=face_couloir(-1), group="Champs/Moulin", emprise=(14, 14, 40),
          variant=0)
    place(b, "monuments", "cotes_geantes", (X_COTES, 0, Z_COTES), yaw=YAW_COTES, group="Monuments/Cotes", emprise=(56, 36, 36),
          variant=0, longueur=56, hauteur=36)
    for i, (x, z, v) in enumerate(((-150, -50, 0), (-176, -66, 1), (164, -40, 2), (80, -96, 0))):
        place(b, "mobilier", "meule", (x, 0, z), group=f"Champs/Meule{i}", emprise=(5, 5, 5), variant=v)
    place(b, "mobilier", "puits", (-51.2, 0, -60), group="Champs/Puits", emprise=(6, 6, 9), variant=0)
    place(b, "mobilier", "charrette", (52, 0, -62), yaw=200, group="Champs/Charrette", emprise=(5, 10, 4), variant=2)
    for s in (-1, 1):                                       # clôtures le long des champs, au bord des accotements
        for i, z in enumerate((-36.5,) if s < 0 else (-58.0, -72.0)):
            place(b, "mobilier", "cloture_bois", (s * 55.5, 0, z), yaw=90, group=f"Champs/Cloture{'GD'[s > 0]}{i}",
                  emprise=(12, 1, 3), longueur=12, variant=(i + (s > 0)) % 4)
    for i, (x, z, v) in enumerate(((-84, -36, 1), (72, -66, 3), (150, -96, 0))):
        place(b, "mobilier", "arbre_mort", (x, 0, z), group=f"Champs/ArbreMort{i}", emprise=(10, 10, 13), variant=v,
              hauteur=13)
    place(b, "mobilier", "lanterne_fer", (-52, 0, -42), yaw=face_couloir(-1), group="Champs/Lanterne", emprise=(2, 4, 11),
          variant=1)
    return poses


def village(b: Builder) -> list:
    """Village abandonné (z -80 → -196) : chaumières, maisons de pierre et ruines ; église et cimetière à gauche ;
    à droite, derrière les maisons, la colline boisée et le CRÂNE DE DÉMON cornu (repère de la première moitié)."""
    poses = rangee(b, -1, VILLAGE_G, "Village/G")
    poses += rangee(b, 1, VILLAGE_D, "Village/D")
    place(b, "batiments", "eglise", (-(X_BORD + 22), 0, -154), yaw=face_couloir(-1), group="Monuments/Eglise",
          emprise=(26, 44, 56), variant=0, largeur=26, profondeur=44)
    # cimetière de part et d'autre de l'église, muret côté couloir
    tombes = ((-61, -133), (-66, -136), (-72, -132.5), (-79, -136), (-86, -133), (-62, -171), (-69, -174),
              (-76, -171), (-84, -174), (-92, -171))
    for i, (x, z) in enumerate(tombes):
        place(b, "mobilier", "pierre_tombale", (x, 0, z), yaw=face_couloir(-1) + (i % 3 - 1) * 8,
              group=f"Village/Cimetiere/Tombe{i}", emprise=(2, 2, 3), variant=i % 4)
    for i, z in enumerate((-135.0, -173.0)):
        place(b, "mobilier", "muret", (-56.4, 0, z), yaw=90, group=f"Village/Cimetiere/Muret{i}", emprise=(10, 1.4, 2.2),
              longueur=10, variant=i)
    # colline du crâne, puis le crâne posé sur son sommet
    info = place(b, "monuments", "colline_crane", (X_COLLINE, 0, Z_COLLINE), yaw=face_couloir(1),
                 group="Monuments/Colline", emprise=(110, 100, H_COLLINE), variant=0, largeur=110, profondeur=100,
                 hauteur=H_COLLINE)
    place(b, "monuments", "crane_demon", (X_COLLINE, info.get("hauteur", H_COLLINE), Z_COLLINE), yaw=YAW_CRANE,
          group="Monuments/Crane", emprise=(60, 56, 64), variant=0, hauteur=64)
    # rue du village : lanternes, tonneaux, caisses, charrette brisée, arbres morts
    for s in (-1, 1):
        for i, z in enumerate((-97, -134, -172)):
            if s < 0 and z == -134:
                z = -128.5                                   # devant la ruine, pas devant le muret du cimetière
            if s > 0 and z == -134:
                z = -141.0                                   # le puits en ruine occupe l'accotement en z = -133
            x = s * 52.2
            place(b, "mobilier", "lanterne_fer", (x, 0, z), yaw=face_couloir(x), group=f"Village/Lanterne{'GD'[s > 0]}{i}",
                  emprise=(2, 4, 11), variant=(1, 0, 1)[i])
    props = (("tonneaux", -51.5, -102, 0), ("caisses", -51.5, -114, 1), ("tonneaux", 51.5, -92, 1),
             ("caisses", 51.8, -152, 2), ("charrette", 51.5, -118, 1), ("puits", 50.6, -133, 1))
    for i, (fn, x, z, v) in enumerate(props):
        place(b, "mobilier", fn, (x, 0, z), yaw=0 if fn != "charrette" else 160, group=f"Village/{fn}{i}",
              emprise=(4, 4, 3), variant=v)
    for i, (x, z, v) in enumerate(((-96, -122, 0), (74, -130, 2), (75, -170, 1), (-114, -150, 3))):
        place(b, "mobilier", "arbre_mort", (x, 0, z), group=f"Village/ArbreMort{i}", emprise=(10, 10, 14), variant=v,
              hauteur=14)
    return poses


# ---------------------------------------------------------------------------
# Séquence 4 : bourg de la tour aux grimoires
# ---------------------------------------------------------------------------

BOURG_G = [
    ("batiments:maison_haute", -204, 14, 14, {"variant": 0, "etages": 3}),
    ("batiments:maison_haute", -220, 14, 14, {"variant": 1, "etages": 4, "enseigne": "BIBLIOTHÈQUE"}),
    # place de la tour : z -228 → -272
    ("batiments:maison_haute", -280, 14, 14, {"variant": 2, "etages": 3, "enseigne": "POTIONS"}),
    ("batiments:maison_haute", -294, 12, 14, {"variant": 3, "etages": 4}),
]
BOURG_D = [
    ("batiments:taverne", -210, 24, 16, {"variant": 0}),
    ("batiments:maison_haute", -231, 14, 14, {"variant": 4, "etages": 4}),
    ("batiments:halle", -254, 26, 14, {"variant": 0}),
    ("batiments:maison_haute", -277, 14, 14, {"variant": 5, "etages": 3, "enseigne": "HERBORISTE"}),
    ("batiments:maison_haute", -293, 14, 14, {"variant": 2, "etages": 4}),
]


def bourg(b: Builder) -> list:
    """Bourg (z -196 → -300) : à gauche la TOUR AUX GRIMOIRES sur sa placette (pupitre et nuée de grimoires),
    maisons hautes à colombages noirs ; à droite taverne, halle du marché, maisons hautes ; lanternes et bannières."""
    poses = rangee(b, -1, BOURG_G, "Bourg/G")
    poses += rangee(b, 1, BOURG_D, "Bourg/D")
    place(b, "monuments", "tour_grimoires", (X_TOUR, 0, Z_TOUR), yaw=face_couloir(-1), group="Monuments/Tour",
          emprise=(2 * R_TOUR + 16, 2 * R_TOUR + 16, H_TOUR), variant=0, rayon=R_TOUR, hauteur=H_TOUR)
    place(b, "mobilier", "nuee_grimoires", (-64, 0, -250), group="Bourg/Place/Nuee", emprise=(12, 12, 13), variant=1,
          rayon=4.5, hauteur=13, nombre=10)
    place(b, "mobilier", "lucioles", (-66, 4, -250), group="Bourg/Place/Lucioles", emprise=(16, 16, 14), variant=0,
          rayon=8, hauteur=14, nombre=16)
    for i, (z, v) in enumerate(((-233, 1), (-267, 3))):     # bannières qui encadrent la placette
        place(b, "mobilier", "banniere", (-57.5, 0, z), group=f"Bourg/Place/Banniere{i}", emprise=(4.2, 1.8, 12), variant=v,
              hauteur=12)
    place(b, "mobilier", "puits", (-65, 0, -236), group="Bourg/Place/Puits", emprise=(6, 6, 9), variant=2)
    for s in (-1, 1):
        for i, z in enumerate((-212, -241, -272)):
            if s > 0 and z == -241:
                z = -268.5                                   # devant la halle : les étals occupent l'accotement
            x = s * 52.2
            place(b, "mobilier", "lanterne_fer", (x, 0, z), yaw=face_couloir(x), group=f"Bourg/Lanterne{'GD'[s > 0]}{i}",
                  emprise=(2, 4, 11), variant=(0, 2, 3)[i] if s < 0 else (3, 0, 2)[i])
    for i, (z, v) in enumerate(((-246.0, 0), (-260.0, 1))):  # étals devant la halle
        place(b, "mobilier", "etal", (50.8, 0, z), yaw=face_couloir(1), group=f"Bourg/Marche/Etal{i}", emprise=(7, 4, 7),
              variant=v)
    place(b, "mobilier", "panneau_pied", (52.0, 0, -238.5), yaw=face_couloir(1), group="Bourg/Marche/Panneau",
          emprise=(6, 2, 6), texte="MARCHÉ", variant=1)
    props = (("tonneaux", 51.5, -201, 0), ("caisses", 51.5, -223, 0), ("chaudron", -51.8, -286, 0),
             ("tonneaux", -51.5, -209, 2))
    for i, (fn, x, z, v) in enumerate(props):
        place(b, "mobilier", fn, (x, 0, z), group=f"Bourg/{fn}{i}", emprise=(4, 4, 4), variant=v)
    return poses


# ---------------------------------------------------------------------------
# Séquence 5 : champ de bataille des mages, aqueduc
# ---------------------------------------------------------------------------

def bataille(b: Builder) -> None:
    """Champ de bataille (z -300 → -404, refBC4) : prairie brumeuse et cratères, murs et tours en ruine, arches
    effondrées, bâtons de mage plantés à orbes lumineux, armes abandonnées, feux de camp ; l'AQUEDUC ruiné
    (refBC3) passe au-dessus du couloir en z = -352, effondré à droite entre x = 100 et 164."""
    place(b, "remparts", "aqueduc", (0, 0, Z_AQUEDUC), group="Monuments/Aqueduc", attente=_attente_aqueduc, variant=0,
          largeur=2 * X_FOND, ouverture=OUVERTURE_AQUEDUC, dessous=DESSOUS_AQUEDUC, hauteur=H_AQUEDUC,
          rupture=RUPTURE_AQUEDUC)
    tours = ((-84, -318, 10, 44, 0), (-160, -388, 12, 34, 1), (92, -392, 11, 52, 2))
    for i, (x, z, r, h, v) in enumerate(tours):
        place(b, "remparts", "ruine_tour", (x, 0, z), yaw=face_couloir(x), group=f"Bataille/Tour{i}",
              emprise=(2 * r, 2 * r, h), variant=v, rayon=r, hauteur=h)
    murs = ((-66, -380, -90, 36, 18, 0), (-122, -330, 0, 40, 16, 1), (66, -318, 90, 30, 20, 2), (150, -372, 20, 34, 14, 3),
            (-112, -376, 75, 30, 12, 0))
    for i, (x, z, yaw, L, h, v) in enumerate(murs):
        place(b, "remparts", "ruine_mur", (x, 0, z), yaw=yaw, group=f"Bataille/Mur{i}", emprise=(L, 5, h), variant=v,
              longueur=L, hauteur=h, epaisseur=5)
    for i, (x, z, yaw, v) in enumerate(((-128, -392, -60, 0), (138, -324, 70, 1))):
        place(b, "remparts", "arche_effondree", (x, 0, z), yaw=yaw, group=f"Bataille/Arche{i}", emprise=(30, 6, 26),
              variant=v, largeur=30, hauteur=26)
    # bâtons de mage plantés le long du couloir et dans la prairie
    batons = ((-50, -306), (50, -314), (-50.5, -336), (50, -362), (-50, -398), (50.5, -388), (-72, -350),
              (78, -344), (-100, -366), (110, -398), (-58, -322), (60, -376))
    for i, (x, z) in enumerate(batons):
        place(b, "mobilier", "baton_mage", (x, 0, z), yaw=37 * i, group=f"Bataille/Baton{i}", emprise=(2, 2, 10), variant=i % 4)
    armes = (("epee_plantee", -52, -312, 0), ("epee_plantee", 53, -330, 1), ("epee_plantee", -51, -372, 2),
             ("epee_plantee", 52, -402, 3), ("bouclier", -54, -330, 0), ("bouclier", 52, -370, 1),
             ("armes_abandonnees", -88, -342, 0), ("armes_abandonnees", 84, -366, 1), ("armes_abandonnees", -96, -400, 2),
             ("bouclier", 70, -334, 2))
    for i, (fn, x, z, v) in enumerate(armes):
        place(b, "mobilier", fn, (x, 0, z), yaw=23 * i, group=f"Bataille/{fn}{i}", emprise=(4, 4, 5), variant=v)
    for i, (x, z, v) in enumerate(((-78, -405, 1), (76, -326, 0), (118, -382, 3), (-140, -340, 2))):
        place(b, "mobilier", "feu_camp", (x, 0, z), group=f"Bataille/Feu{i}", emprise=(6, 6, 5), variant=v)
    for i, (x, z, v) in enumerate(((-58.5, -368, 1), (64, -398, 3))):
        place(b, "mobilier", "banniere", (x, 0, z), group=f"Bataille/Banniere{i}", emprise=(4.2, 1.8, 12), variant=v,
              hauteur=11)
    place(b, "mobilier", "nuee_grimoires", (-84, 0, -372), group="Bataille/Nuee", emprise=(10, 10, 12), variant=3,
          rayon=3.8, hauteur=11, nombre=8)
    for i, (x, z, v) in enumerate(((-110, -312, 2), (124, -310, 0), (-170, -312, 1), (168, -312, 3))):
        place(b, "mobilier", "arbre_mort", (x, 0, z), group=f"Bataille/ArbreMort{i}", emprise=(10, 10, 15), variant=v,
              hauteur=15)
    for i, (x, z, v) in enumerate(((-62, -338, 0), (58, -342, 1), (-60, -402, 2))):
        place(b, "mobilier", "rocher", (x, 0, z), yaw=40 * i, group=f"Bataille/Rocher{i}", emprise=(5, 5, 4), variant=v,
              taille=3.5)


# ---------------------------------------------------------------------------
# Séquences 6 et 7 : place rituelle des œufs, arbre démoniaque, château
# ---------------------------------------------------------------------------

def place_rituelle(b: Builder) -> None:
    """Place rituelle (z -404 → -498) : cercle magique au sol (voir cercle_magique), obélisques noirs à flammes,
    racines démoniaques, épines, braseros ; l'ARBRE DÉMONIAQUE à droite, des ÎLOTS FLOTTANTS enchaînés à gauche."""
    cercle_magique(b)
    obelisques = ((-53, -418, 0), (53, -418, 1), (-58, -448, 2), (58, -448, 0), (-53, -478, 1), (53, -478, 2))
    for i, (x, z, v) in enumerate(obelisques):
        place(b, "abime", "obelisque", (x, 0, z), yaw=face_couloir(x), group=f"Place/Obelisque{i}", emprise=(5, 5, 18),
              variant=v, hauteur=16)
    racines = ((-78, -412, 30, 0), (82, -424, -20, 1), (-88, -470, 75, 2), (-70, -494, 5, 3), (96, -486, -60, 0),
               (-120, -440, 100, 1))
    for i, (x, z, yaw, v) in enumerate(racines):
        place(b, "abime", "racine_geante", (x, 0, z), yaw=yaw, group=f"Place/Racine{i}", emprise=(24, 6, 10), variant=v,
              longueur=24, hauteur=10)
    for i, (x, z, v) in enumerate(((-50, -432, 0), (50.5, -462, 1), (-50.5, -490, 3), (51, -410, 2), (66, -440, 1),
                                   (-68, -456, 0))):
        place(b, "mobilier", "epines_racines", (x, 0, z), yaw=50 * i, group=f"Place/Epines{i}", emprise=(4, 4, 5),
              variant=v)
    for i, (x, z) in enumerate(((-48.6, -406), (48.6, -406), (-48.6, -494), (48.6, -494))):
        place(b, "mobilier", "brasero", (x, 0, z), group=f"Place/Brasero{i}", emprise=(3, 3, 6), variant=(1, 2, 2, 1)[i])
    for i, (x, z, v) in enumerate(((-100, -420, 0), (-124, -488, 2), (76, -452, 1))):
        place(b, "abime", "cristaux", (x, 0, z), yaw=30 * i, group=f"Place/Cristaux{i}", emprise=(6, 6, 7), variant=v, taille=6)
    place(b, "abime", "arbre_demon", (X_ARBRE, 0, Z_ARBRE), yaw=face_couloir(1), group="Monuments/Arbre",
          emprise=(70, 70, H_ARBRE), variant=0, hauteur=H_ARBRE)
    # îlots flottants (repos sur rien : magie voulue), enchaînés à des ancrages au sol
    ilots = ((-92, 46, -428, 14, ((12, -46, -8), (-16, -46, -4))),
             (-136, 66, -466, 18, ((6, -66, -14), (-16, -66, 4))),
             (-98, 78, -490, 12, ((-6, -78, 10),)),
             (104, 60, -414, 12, ((-18, -60, 6),)))
    for i, (x, y, z, t, ancres) in enumerate(ilots):
        place(b, "abime", "ilot_flottant", (x, y, z), group=f"Place/Ilot{i}", emprise=(t, t, t * 0.8), variant=i, taille=t,
              ancres=ancres)
    place(b, "mobilier", "lucioles", (-104, 30, -456), group="Place/LuciolesIlots", emprise=(40, 40, 50), variant=1,
          rayon=20, hauteur=50, nombre=30)


def chateau(b: Builder) -> None:
    """Château démoniaque (repère final, refBC3) : forteresse gothique noire sur falaise, flèches, fenêtres violettes,
    porte en arc brisé de 100 × 40 (sommet ≈ 66) par laquelle le couloir sort en z = -548."""
    place(b, "abime", "chateau_demon", (0, 0, (Z_CHATEAU + Z_SORTIE) / 2), yaw=180, group="Monuments/Chateau",
          attente=_attente_chateau, variant=0, largeur=2 * X_FOND, profondeur=PROF_CHATEAU, ouverture=OUVERTURE,
          h_passage=H_PASSAGE)
    place(b, "mobilier", "lucioles", (0, 34, Z_CHATEAU + 6), group="Chateau/Lucioles", emprise=(36, 36, 30), variant=1,
          rayon=18, hauteur=30, nombre=30)


# ---------------------------------------------------------------------------
# Côtés : forêt, falaises, montagne de la capitale, limites
# ---------------------------------------------------------------------------

BOSQUETS = (   # (x, z, nombre, rayon) : sapins sombres et arbres morts mêlés
    (-172, -42, 3, 10), (-224, -60, 2, 8), (-214, -168, 4, 14), (-160, -222, 4, 12), (-212, -268, 4, 12),
    (-128, -296, 2, 8), (204, -44, 3, 10), (212, -150, 3, 12), (150, -238, 4, 12), (210, -266, 4, 12),
    (120, -292, 2, 8))
FALAISES = (   # (x, z, longueur, profondeur, hauteur, yaw)
    (-205, -330, 60, 50, 34, -90), (-205, -390, 60, 50, 48, -90), (-205, -455, 70, 50, 62, -90),
    (205, -330, 60, 50, 34, 90), (205, -390, 60, 50, 46, 90), (215, -458, 76, 40, 58, 90))


def cotes(b: Builder) -> None:
    rng = np.random.default_rng(17)
    for i, (x, z, n, r) in enumerate(BOSQUETS):
        for k in range(n):
            a = 2 * math.pi * k / n + float(rng.uniform(-0.4, 0.4))
            d = r * (0.3 + 0.7 * float(rng.random())) if n > 1 else 0.0
            px, pz = x + d * math.cos(a), z + d * math.sin(a)
            mort = (k + i) % 4 == 3
            fn = "arbre_mort" if mort else "sapin_sombre"
            place(b, "mobilier", fn, (px, 0, pz), yaw=float(rng.uniform(0, 90)), group=f"Cotes/Bosquet{i}/{k}",
                  emprise=(8, 8, 18), variant=(k + 2 * i) % 4, hauteur=float(rng.uniform(15, 22)) if not mort else 15)
    for i, (x, z, L, p, h, yaw) in enumerate(FALAISES):
        place(b, "abime", "falaise", (x, 0, z), yaw=yaw, group=f"Cotes/Falaise{i}", emprise=(L, p, h), variant=i % 4,
              longueur=L, profondeur=p, hauteur=h)
    place(b, "monuments", "montagne_capitale", (X_MONTAGNE, 0, Z_MONTAGNE), yaw=face_couloir(-1),
          group="Cotes/MontagneCapitale", emprise=(70, 70, 96), variant=0, largeur=70, hauteur=96)
    for i, (x, z, rs) in enumerate(((-150, -120, 5), (172, -394, 5), (-168, -420, 5), (124, -410, 6))):
        place(b, "mobilier", "rocher", (x, 0, z), yaw=25 * i, group=f"Cotes/Rocher{i}", emprise=(8, 8, 7), variant=i % 4,
              taille=rs)
    for i, (x, z, larg, etages) in enumerate(FOND):
        place(b, "batiments", "maison_fond", (x, 0, z), yaw=face_couloir(x), group=f"Cotes/MaisonFond{i}",
              emprise=(larg, 10, 7 + 6 * etages), variant=i % 4, largeur=larg, profondeur=10, etages=etages)


def limites(b: Builder) -> None:
    """Murs invisibles solides aux bords du sol (|x| = 239-240), de la sortie aux abords."""
    inv = dict(transparency=1.0, collide=True, shadow=False)
    for s in (-1, 1):
        xa, xb = sorted((s * (X_FOND - 1.0), s * X_FOND))
        with b.group("Limites"):
            b.box((xa, 0, Z_SORTIE), (xb, 40, Z_ENTREE), "#ffffff", name="MurInvisible", **inv)
        with b.group("Abords/Limites"):
            b.box((xa, 0, Z_ENTREE), (xb, 40, Z_ABORDS), "#ffffff", name="MurInvisible", **inv)


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


def decouper(b: Builder, prefixes=("Sol/", "Cotes/", "Abords/Sol/"), taille: float = 64) -> None:
    """Range les pièces des grands ensembles dans des sous-modèles de 64 × 64 studs (streaming Roblox)."""
    for p in b.parts:
        if p.group.startswith(prefixes):
            i, j = math.floor(p.pos[0] / taille), math.floor(p.pos[2] / taille)
            n = 3 if p.group.startswith("Abords/") else 2
            racine = "/".join(p.group.split("/")[:n])
            reste = p.group[len(racine):]
            p.group = f"{racine}/Bloc_{i:+d}_{j:+d}{reste}"


def build_zone(seed: int = 7) -> Builder:
    _COMPTES.clear()
    _POSES_BUDGET.clear()
    b = Builder(seed=seed)
    sol(b)
    abords(b)
    porte(b)
    poses = champs(b)
    poses += village(b)
    poses += bourg(b)
    bataille(b)
    place_rituelle(b)
    chateau(b)
    cotes(b)
    limites(b)
    reperes(b)
    decouper(b)
    for p in b.parts:                       # petites pièces décoratives : jamais collidables
        if p.collide and max(p.size) < 1.0:
            p.collide = False
    return b


def _bornes(p):
    R = np.asarray(p.rot).reshape(3, 3)
    half = np.abs(R) @ (np.asarray(p.size) / 2)
    return np.asarray(p.pos) - half, np.asarray(p.pos) + half


def _est_sol(groupe: str) -> bool:
    return groupe.startswith(("Sol", "Reperes", "Abords/Sol"))


def couloir_libre(b: Builder) -> list:
    """Liste ce qui encombre le couloir de course au sol (pièces solides, hors sol et repères)."""
    gene = []
    for p in b.parts:
        if not p.collide or _est_sol(p.group):
            continue
        lo, hi = _bornes(p)
        if lo[0] < DEMI_COULOIR - 0.05 and hi[0] > -DEMI_COULOIR + 0.05 and lo[1] < 12 and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_ABORDS:
            gene.append((p.group, p.name, [round(v, 1) for v in lo], [round(v, 1) for v in hi]))
    return gene


def trop_bas_au_dessus(b: Builder, y_min: float = Y_LIBRE) -> list:
    """Toute pièce (solide ou non) au-dessus du couloir élargi |x| < 46 et sous `y_min` : la caméra Roblox
    sauterait en passant dessous, et rien ne doit traîner dans le couloir."""
    out = []
    for p in b.parts:
        if _est_sol(p.group):
            continue
        lo, hi = _bornes(p)
        if lo[0] < X_LIBRE and hi[0] > -X_LIBRE and lo[1] < y_min and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_ABORDS:
            out.append((p.group, p.name, round(lo[1], 1)))
    return out


FEUILLAGES = ("sapin_sombre", "arbre_mort", "lucioles", "nuee_grimoires")


def _accepte(ga: str, gb: str) -> str | None:
    """Contacts voulus entre deux poses (raison), comptés à part par --chevauchements."""
    racines = {ga.split("/")[0], gb.split("/")[0]}
    paire = {"/".join(ga.split("/")[:2]), "/".join(gb.split("/")[:2])}
    if ga.split("/")[:2] == gb.split("/")[:2] and ga.startswith("Cotes/Bosquet"):
        return "bosquet serré (étages de sapins mêlés)"
    if all(g.startswith("Porte/") for g in (ga, gb)):
        return "maçonnerie de l'enceinte (segments bout à bout, tours)"
    if paire == {"Monuments/Colline", "Monuments/Crane"}:
        return "mâchoire du crâne enfoncée dans la colline"
    if "Monuments/Chateau" in paire and racines & {"Cotes", "Place"}:
        return "falaises et racines contre le socle du château"
    if "Monuments/Arbre" in paire and racines & {"Cotes", "Place"}:
        return "racines de l'arbre sur la place et contre la falaise"
    if "Monuments/Aqueduc" in paire and racines & {"Bataille", "Cotes"}:
        return "ruines et falaises sous les arches de l'aqueduc"
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


def chevauchements(b: Builder, tol: float = 0.04, cellule: float = 16.0) -> dict:
    """Assets posés qui se recoupent : pour chaque paire de poses, nombre de paires de pièces qui s'interpénètrent
    de plus de `tol` et profondeur maximale. Le sol plat et les repères sont ignorés ; les feuillages et la magie
    flottante sans collision qui débordent sur un voisin sont rangés à part (`feuillage`) ; une pièce enfoncée de
    moins de `ASSISE` dans ce qui la porte est posée, pas recoupée."""
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
            if racine in ("Reperes", "Limites"):
                continue
            lo, hi = _bornes(p)
            if _est_sol(p.group) and hi[1] <= 1.0:
                continue
            morceaux = p.group.split("/")
            etiquette[i] = "/".join(morceaux[:2])
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
    return {"nom": "ZoneBlackClover", "version": VERSION, "largeur_couloir": 2 * DEMI_COULOIR,
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
    neon = sum(1 for p in b.parts if p.material == "Neon")
    transp = sum(1 for p in b.parts if 0 < p.transparency < 1 and not p.name.startswith("ATTENTE_"))
    print(json.dumps({"pieces": len(b.parts), "neon": neon, "transparentes": transp, "fichier": str(out),
                      "en_attente": attente, "couloir_encombre": gene[:20], "nb_couloir_encombre": len(gene),
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
        par_module = defaultdict(lambda: [0, 0])
        for (module, fn, bud) in _POSES_BUDGET:
            par_module[module][0] += 1
            par_module[module][1] += bud
        print("-- budget maximal par module (somme des budgets de toutes les poses) --")
        for k, (nb, bud) in sorted(par_module.items()):
            print(f"{bud:6d}  assets/{k}.py  ({nb} poses)")
        for prefixe in ("Sol/Couloir", "Sol/Bords", "Sol/Cotes", "Sol/Cercle", "Abords/Sol"):
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
