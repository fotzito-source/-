#!/usr/bin/env python3
"""Plan de la zone Black Clover (royaume de mages aux portes d'un royaume démoniaque) en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course, très large, occupe x ∈ [-45, 45] (90 studs), bordé d'accotements jusqu'à |x| = 55 ;
- on arrive par +Z (abords z 40 → 0, groupe `Abords`, à supprimer quand les zones sont mises bout à bout) et on
  court vers -Z ; la zone descend des confins pauvres d'un royaume de mages jusqu'aux portes d'un royaume démoniaque,
  de plus en plus sombre :
  PORTE D'ENTRÉE (deux tours rondes à toits coniques en aiguille, z 0 → -32), CHAMPS (-32 → -80, côtes géantes à
  droite), VILLAGE ABANDONNÉ (-80 → -196, fenêtres noires ou condamnées, église à gauche, CRÂNE DE DÉMON cornu au
  regard cramoisi sur sa colline à droite), BOURG DE LA TOUR AUX GRIMOIRES (-196 → -300, la tour à gauche),
  CHAMP DE BATAILLE DES MAGES (-300 → -404, grands bâtons de mage le long des accotements, ruines, AQUEDUC sombre et
  brisé en travers à z = -352), PLACE RITUELLE des œufs (cercle magique de rayon 34 centré en z = -448, grands
  obélisques, arbre démoniaque à droite, îlots flottants haut dans le ciel, ancrés aux falaises) et CHÂTEAU
  DÉMONIAQUE (-498 → -548) au donjon dominant, dont la porte (100 × 40, arc brisé au-dessus) débouche en z = -548
  sur la zone suivante ;
- côtés : champs labourés et blé, puis forêt de sapins sombres et d'arbres morts, puis falaises noires à cristaux
  violets ; la montagne couronnée d'un château (capitale du royaume) se dresse au loin à gauche ; une lisière de
  sapins ferme les bords du sol (|x| ≈ 198-231) jusqu'aux falaises.
- le sol raconte la descente (toujours plat, dessus en y = 0) : vieille route pavée aux abords, dalles sous la porte,
  chemin de terre à ornières et flaques, bas-côtés d'herbe et de boue dans les champs et le village (parvis pavé
  devant l'église, allées vers les portes), vieux pavés usés du bourg avec la place dallée de la tour et du marché
  et le parvis en éventail de la tour, terre calcinée à cratères sur le champ de bataille (fissures éteintes dans le
  couloir, incandescentes sur les côtés : jamais de « lave » sous les pieds), dalles noires de la place rituelle
  d'où deux fils violets filent sous la porte du château ;
- accotements (45 ≤ |x| < 55) : clôtures qui dessinent les cours du village, lanternes, charrettes, tonneaux,
  caisses, puits, arbres morts, tombes et feux follets, étals, bâtons de mage, armes, épines ; deux cordes à
  bannières traversent la rue du bourg (pointes des bannières à 34,45 : ce qui enjambe le couloir reste ≥ 34).

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

from kit import Builder, rot_y, rot_z, shade  # noqa: E402
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
H_TOUR_PORTE = 58        # corps des tours (toit conique en aiguille au-dessus, jusqu'à ≈ 111)
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
OUVERTURE_AQUEDUC = 94   # entre les piles qui encadrent le couloir (faces en |x| = 47, socles en |x| = 46,5)
# tronçons effondrés (x local) : la grande brèche à droite (cascade), une travée tombée à gauche
RUPTURES_AQUEDUC = ((100.0, 164.0), (-158.0, -126.0))
AFFAISSEMENTS_AQUEDUC = {(180.0, 212.0): 3.0, (-212.0, -180.0): 3.5}   # travées dont le tablier s'est affaissé
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
X_TOUR, Z_TOUR, R_TOUR, H_TOUR = -94, -250, 16, 138      # tour aux grimoires (à gauche), toit en aiguille de 80 à 138
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
    ("abime", "chateau_demon"): 1150, ("abime", "arbre_demon"): 420, ("abime", "ilot_flottant"): 95,
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
            if x > X_FOND - 4 or any(lo < s * x < hi for (lo, hi) in RUPTURES_AQUEDUC):
                continue
            b.box((s * x - 5, 0, -5), (s * x + 5, H_AQUEDUC - 12, 5), ROSE, transparency=0.5)
    bornes = [-X_FOND] + [v for r in sorted(RUPTURES_AQUEDUC) for v in r] + [X_FOND]
    for (xa, xb) in zip(bornes[0::2], bornes[1::2]):
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


def _fondu(z: float, z_a: float, z_b: float) -> float:
    """0 en z_a, 1 en z_b (fondu d'une séquence à la suivante), borné à [0, 1]."""
    return min(max((z - z_a) / (z_b - z_a), 0.0), 1.0)


# Le sol raconte la descente : chemin de terre à ornières dans les champs et le village (bas-côtés d'herbe et de
# boue), vieux pavés usés autour de la tour aux grimoires, terre calcinée à fissures incandescentes sur le champ de
# bataille, dalles noires de la place rituelle et du château. Toujours plat (dessus en y = 0) et continu.
X_PARVIS_EGLISE, Z_EGLISE, R_PARVIS_EGLISE = -55, -154, 24      # parvis pavé en demi-cercle devant l'église
R_PARVIS_TOUR = 64                                              # parvis en éventail autour de la tour aux grimoires
DEMI_PLACE_BOURG = 23                                           # place dallée de la tour et du marché : |z - Z_TOUR| < 23
ORNIERES = ((6, 8), (14, 16))                                   # deux paires d'ornières (|x|), une par sens de roulage

# Cratères du champ de bataille (x, z, rayon) : fond noir et brûlis peints dans le sol ; fissures incandescentes
# posées par fissures_bataille()
CRATERES = ((-24, -318, 8.0), (21, -336, 6.5), (-6, -374, 9.0), (31, -394, 6.0), (-36, -356, 5.0), (10, -306, 4.0))
CRATERES_COTES = ((-100, -352, 12.0), (-160, -318, 8.0), (120, -356, 11.0), (104, -318, 7.0), (-150, -360, 7.0),
                  (150, -398, 8.0))


def _cratere(x: float, z: float, liste=CRATERES):
    """Distance relative au centre du cratère qui contient (x, z), ou None."""
    for (cx, cz, r) in liste:
        d = math.hypot(x - cx, z - cz)
        if d < r:
            return d / r
    return None


def _couleur_cratere(t: float):
    return c("obsidienne") if t < 0.38 else c("brulis")


def _parvis_eglise(x: float, z: float):
    """Parvis de l'église : demi-cercle de vieux pavés bruns bordé de pierres, devant le porche (x < -31)."""
    r = math.hypot(x - X_PARVIS_EGLISE, z - Z_EGLISE)
    if r >= R_PARVIS_EGLISE:
        return None
    if r >= R_PARVIS_EGLISE - 2.6:
        return c("bordure")
    if _bruit(x, z, 5, 64) > 0.78:
        return c("boue")
    return _paves(x, z, (c("pave_brun"), c("pave_brun_clair"), c("pave_fonce")), 17, L=6, H=4)


def _parvis_tour(x: float, z: float):
    """Parvis de la tour aux grimoires : anneaux de pavés concentriques (éventail), usés par endroits."""
    r = math.hypot(x - X_TOUR, z - Z_TOUR)
    if r >= R_PARVIS_TOUR or (x < X_TOUR - 6 and r > 30):
        return None
    if r < 24:
        return c("pave_fonce")                                    # sous la tour et ses contreforts
    if r >= R_PARVIS_TOUR - 3:
        return c("bordure")
    if x > -DEMI_COULOIR - 10 and _bruit(x, z, 8, 72) > 0.8:
        return c("terre_fonce")                                   # pavés arrachés (côté rue)
    k = math.floor((r - 24) / 6)
    return c("pave_clair") if k % 2 == 0 else c("pave_fonce")


def _allee_porte(x: float, z: float) -> bool:
    """Allée de pavés de la rue jusqu'à la porte de chaque maison des champs et du village."""
    s = -1 if x < 0 else 1
    for plan in ((CHAMPS_G, VILLAGE_G) if s < 0 else (CHAMPS_D, VILLAGE_D)):
        for (_kind, zc, _l, _p, _params) in plan:
            if abs(z - zc) < 2:
                return True
    return False


def _sol_abords(x: float, z: float):
    """Abords : vieille route pavée gris-violet, mousse entre les pavés, bas-côtés de prés sombres."""
    ax = abs(x)
    w = 17 + 8 * _bruit(0.0, z, 9, 40)
    if ax < w:
        if _bruit(x, z, 8, 41) > 0.8:
            return c("mousse")
        return _paves(x + DEMI_COULOIR, Z_ABORDS - z, (c("pave"), c("pave_clair"), c("pave_fonce")), 3, L=12, H=6)
    if ax < w + 3 and _bruit(x, z, 8, 42) > 0.4:
        return c("herbe_morte")
    return c("herbe_fonce") if _bruit(x, z, 14, 43) > 0.45 else c("mousse")


def _sol_seuil(x: float, z: float):
    """Seuil de la porte : grandes dalles de 10 × 7 à joints sombres entre deux bordures ; chemin central usé plus
    sombre (|x| < 13), mousse dans les joints au pied des tours."""
    u, v = x + DEMI_COULOIR, -z
    if v < 2 or v > 30:
        return c("bordure")
    ax = abs(x)
    if u % 10 < 2 or (v - 2) % 7 < 2:
        if ax > 30 and _bruit(x, z, 6, 45) > 0.5:
            return c("mousse")                                   # joints moussus au pied des tours
        return c("joint")
    h = _hash(math.floor(u / 10), math.floor((v - 2) / 7), 44)
    if ax < 13:                                                  # chemin usé par les charrois
        return c("dalle") if h < 0.45 else (c("pave_fonce") if h < 0.85 else c("boue"))
    if ax > 36 and _bruit(x, z, 5, 46) > 0.72:
        return c("mousse")
    return c("dalle_claire") if h < 0.3 else (c("dalle") if h < 0.8 else c("pave_fonce"))


def _sol_chemin(x: float, z: float, demi: float, graine: int, pavage: float = 2.0):
    """Chemin de terre à ornières (champs, village) : bande de roulement de demi-largeur `demi`, deux paires
    d'ornières à flaques, herbe sèche au milieu, restes de pavage quand le bruit dépasse `pavage`."""
    ax = abs(x)
    if ax >= demi:
        return None
    flaque = _bruit(x, z, 10, graine + 1)
    for (a, b_) in ORNIERES:
        if a <= ax < b_:
            if flaque > 0.8:
                return c("eau")                                   # flaques dans les ornières
            return c("boue") if flaque > 0.66 else c("terre_fonce")
    if ax < 2 and _bruit(x, z, 10, graine + 2) > 0.45:
        return c("herbe_fonce")                                   # touffes d'herbe entre les deux voies
    if _bruit(x, z, 18, graine + 3) > pavage:
        return _paves(x + DEMI_COULOIR, -z, (c("pave_brun"), c("pave_brun_clair"), c("pave_fonce")), graine, L=10, H=6)
    if flaque > 0.86:
        return c("boue")
    return c("terre") if _bruit(x, z, 24, graine + 4) > 0.36 else c("terre_claire")


def _bas_cote(x: float, z: float, demi: float, graine: int):
    """Bas-côté herbeux et boueux entre le chemin et les accotements."""
    ax = abs(x)
    if ax < demi + 3 and _bruit(x, z, 9, graine + 5) > 0.35:
        return c("herbe_morte")
    n = _bruit(x, z, 12, graine + 6)
    if n > 0.78:
        return c("boue")
    return c("herbe") if n > 0.42 else c("herbe_fonce")


def _sol_champs(x: float, z: float):
    demi = 19 + 6 * _bruit(0.0, z, 11, 50)
    return _sol_chemin(x, z, demi, 50) or _bas_cote(x, z, demi, 50)


def _sol_village(x: float, z: float):
    p = _parvis_eglise(x, z)
    if p is not None:
        return p
    demi = 19 + 7 * _bruit(0.0, z, 13, 60)
    return _sol_chemin(x, z, demi, 60, pavage=0.72) or _bas_cote(x, z, demi, 60)


def _sol_bourg(x: float, z: float):
    """Bourg : vieux pavés gris-violet usés, rigole centrale, caniveaux ; au milieu, la place dallée de la tour et du
    marché (cadre de pavés bruns) ; l'éventail du parvis de la tour mord sur le côté gauche de la rue."""
    ax = abs(x)
    p = _parvis_tour(x, z)
    if p is not None:
        return p
    v = Z_BOURG - z
    if v < 3:
        return c("bordure")                                       # seuil du bourg
    if abs(z - Z_TOUR) < DEMI_PLACE_BOURG:                           # place de la tour et du marché : grandes dalles
        if abs(z - Z_TOUR) >= DEMI_PLACE_BOURG - 2:
            return c("pave_brun_clair")                           # cadre de la place
        u, w = x + DEMI_COULOIR, z - (Z_TOUR - DEMI_PLACE_BOURG + 2)
        h = _hash(math.floor(u / 8), math.floor(w / 6), 73)
        return c("dalle_claire") if h < 0.45 else (c("dalle") if h < 0.9 else c("pave_fonce"))
    if ax < 1:
        return c("joint")                                         # rigole centrale
    if ax >= 41:
        return c("bordure") if ax >= 43 else c("joint")           # caniveaux le long des trottoirs
    if _bruit(x, z, 12, 70) > 0.76:
        return c("terre_fonce")                                   # pavés arrachés
    return _paves(x + DEMI_COULOIR, v, (c("pave"), c("pave_clair"), c("pave_fonce")), 11, L=10, H=6)


def _sol_place(x: float, z: float):
    """Place rituelle : anneaux carrés de dalles noires centrés sur le cercle magique."""
    k = math.floor(max(abs(x), abs(z - Z_PLACE)) / 6)
    return c("dalle_noire") if k % 2 == 0 else c("dalle_rituelle")


def _sol_bataille(x: float, z: float):
    """Champ de bataille : terre calcinée, cendre, cratères noirs ; pavés épars au sortir du bourg, dalles noires
    qui gagnent la cendre à l'approche de la place."""
    ax = abs(x)
    t = _cratere(x, z)
    if t is not None:
        return _couleur_cratere(t)
    if z > Z_BATAILLE - 18 and _bruit(x, z, 11, 81) > 0.3 + 0.72 * _fondu(z, Z_BATAILLE, Z_BATAILLE - 18):
        return _paves(x + DEMI_COULOIR, Z_BOURG - z, (c("pave_fonce"), c("pave"), c("pave_fonce")), 11, L=10, H=6)
    if z < Z_PLACE_DEBUT + 22 and _bruit(x, z, 11, 82) > 1.02 - 0.7 * _fondu(z, Z_PLACE_DEBUT + 22, Z_PLACE_DEBUT):
        return _sol_place(x, z)
    for (a, b_) in ORNIERES:
        if a <= ax < b_ and _bruit(x, z, 12, 83) > 0.4:
            return c("boue")                                      # ornières de la route militaire
    if ax > 35 + 6 * _bruit(0.0, z, 12, 84):
        return c("herbe_grise")
    n = _bruit(x, z, 15, 86)
    return c("brulis") if n > 0.58 else (c("terre_fonce") if n > 0.4 else (c("cendre_fonce") if n > 0.18 else c("cendre")))


def couleur_couloir(x: float, z: float):
    """Sol du couloir (|x| < 45), un motif par séquence."""
    if z > Z_ENTREE:
        return _sol_abords(x, z)
    if z > Z_CHAMPS:
        return _sol_seuil(x, z)
    if z > Z_VILLAGE:
        return _sol_champs(x, z)
    if z > Z_BOURG:
        return _sol_village(x, z)
    if z > Z_BATAILLE:
        return _sol_bourg(x, z)
    if z > Z_PLACE_DEBUT:
        return _sol_bataille(x, z)
    if z > Z_CHATEAU:
        return _sol_place(x, z)
    u, v = x + DEMI_COULOIR, Z_CHATEAU - z                        # porte du château : basalte en damier
    return c("basalte_clair") if (math.floor(u / 10) + math.floor(v / 10)) % 2 == 0 else c("basalte")


def neon_couloir(x: float, z: float):
    """Cases lumineuses du sol (posées en Neon dans les trous laissés par couleur_couloir_plein) : deux fils de
    lumière violette qui partent du cercle magique et passent sous la porte du château (jamais de rouge ou d'orange
    lumineux au sol du couloir : on y lirait de la lave)."""
    if z < Z_PLACE - R_PLACE + 0.5 and 6 <= abs(x) < 8:
        return c("lueur_violette")
    return None


def couleur_couloir_plein(x: float, z: float):
    if neon_couloir(x, z) is not None:
        return None
    return couleur_couloir(x, z)


def couleur_bords(x: float, z: float):
    """Accotements (45 ≤ |x| < 55) : prés aux abords, dalles sous la porte, bas-côtés d'herbe et allées de pavés
    vers les portes, trottoir de dalles du bourg, cendre, dalles noires, basalte."""
    ax = abs(x)
    if z > Z_ENTREE:
        return c("herbe_fonce") if _bruit(x, z, 6, 12) > 0.45 else c("mousse")
    if z > Z_CHAMPS:
        return _sol_seuil(x, z)
    if z > Z_BOURG:
        p = _parvis_eglise(x, z)
        if p is not None:
            return p
        if _allee_porte(x, z):
            return c("pave_brun") if ax < 51 else c("pave_brun_clair")
        if ax < 47:
            return c("herbe_seche")
        return c("herbe") if _bruit(x, z, 12, 13) > 0.45 else c("herbe_fonce")
    if z > Z_BATAILLE:
        p = _parvis_tour(x, z)
        if p is not None:
            return p
        if ax < 47:
            return c("bordure")
        return c("dalle_claire") if math.floor(z / 6) % 2 else c("dalle")
    if z > Z_PLACE_DEBUT:
        t = _cratere(x, z, CRATERES_COTES)
        if t is not None:
            return _couleur_cratere(t)
        if z < Z_PLACE_DEBUT + 22 and _bruit(x, z, 11, 82) > 1.02 - 0.7 * _fondu(z, Z_PLACE_DEBUT + 22, Z_PLACE_DEBUT):
            return _sol_place(x, z)
        return c("cendre_fonce") if _bruit(x, z, 12, 14) > 0.55 else c("herbe_grise")
    if z > Z_CHATEAU:
        return _sol_place(x, z)
    return c("basalte")


def couleur_cotes(x: float, z: float):
    """Sol au-delà des accotements (|x| ≥ 55, cases de 4) : prés, parcelles de labours et de blé, cours et jardins,
    parvis de la tour, sous-bois, prairie calcinée et cratères, roche noire, dalles de la place rituelle."""
    ax = abs(x)
    s = 1 if x > 0 else 0
    if z > Z_CHAMPS:                                              # abords et pied de l'enceinte : prés sombres
        return c("herbe") if _bruit(x, z, 26, 21) > 0.5 else c("herbe_fonce")
    if z > Z_BOURG:                                               # champs en parcelles, cours derrière les maisons
        if ax < 75:
            if z > Z_VILLAGE:
                return c("herbe_seche") if _bruit(x, z, 24, 22) > 0.45 else c("herbe")
            return c("herbe")
        if ax >= 175:                                             # lisière de la forêt
            return c("herbe_fonce") if _bruit(x, z, 24, 23) > 0.4 else c("mousse")
        du, dv = ax - 75, Z_CHAMPS - z
        if du % 36 < 4 or dv % 32 < 4:                            # chemins entre les parcelles
            return c("terre_fonce")
        kind = int(_hash(math.floor(du / 36), math.floor(dv / 32), 31 + s) * 5)
        if _hash(math.floor(du / 36), math.floor(dv / 32), 77 + s) < 0.25:     # une parcelle sur quatre brûlée
            return c("brulis") if math.floor(ax / 4) % 2 else c("cendre_fonce")
        if kind <= 1:                                             # labours : sillons parallèles au couloir
            return c("labour") if math.floor(ax / 4) % 2 else c("labour_fonce")
        if kind == 2:
            return c("ble")
        if kind == 3:
            return c("ble_fonce")
        return c("herbe_morte")
    if z > Z_BATAILLE:                                            # bourg : parvis de la tour, cours pavées, sous-bois
        p = _parvis_tour(x, z)
        if p is not None:
            return p
        if ax < 79:
            return c("pave_fonce") if _bruit(x, z, 16, 24) > 0.45 else c("terre_fonce")
        return c("herbe_fonce") if _bruit(x, z, 24, 26) > 0.45 else c("mousse")
    if z > Z_PLACE_DEBUT:                                         # prairie calcinée, cratères, roche au pied des falaises
        if ax >= 171:
            return c("roche_noire")
        t = _cratere(x, z, CRATERES_COTES)
        if t is not None:
            return _couleur_cratere(t)
        return c("cendre_fonce") if _bruit(x, z, 26, 28) > 0.55 else c("herbe_grise")
    if z > Z_CHATEAU:
        if ax < X_PLACE + 1:
            return _sol_place(x, z)
        return c("brulis") if _bruit(x, z, 28, 29) > 0.55 else c("roche_noire")
    return c("basalte")


def fissures_bataille(b: Builder) -> None:
    """Fissures du champ de bataille : depuis le bord de chaque cratère, des fissures en zigzag qui s'amincissent
    (blocs à plat, sans collision). Dans le couloir, fissures noires éteintes (aucune lueur au sol : un sol rouge
    ou orange lumineux se lit comme de la lave) ; sur les côtés (|x| ≥ 56), trois fissures incandescentes en trois
    segments (Neon orange puis cramoisi). Angles et longueurs irréguliers : ni croix, ni étoile."""
    rng = np.random.default_rng(23)
    neon = dict(material="Neon", collide=False, shadow=False, studs="none")
    eteinte = dict(collide=False, shadow=False, studs="none")
    with b.group("Sol/Fissures"):
        for i, (cx, cz, r) in enumerate(CRATERES + CRATERES_COTES):
            dans_couloir = i < len(CRATERES)
            n = int(rng.integers(2, 4)) if dans_couloir else 3
            a = float(rng.uniform(0, 2 * math.pi))
            for k in range(n):
                a += float(rng.uniform(1.3, 2.6))                  # écarts irréguliers entre les fissures
                aa = a
                x, z = cx + 0.8 * r * math.cos(aa), cz + 0.8 * r * math.sin(aa)
                L = r * float(rng.uniform(0.8, 1.7)) * (1.0 if dans_couloir else 1.3)
                ep = 0.75 if dans_couloir else 0.9
                for s_ in range(3):
                    aa += float(rng.uniform(-0.85, 0.85))
                    lg = L / 3 * float(rng.uniform(0.7, 1.3))
                    x2, z2 = x + lg * math.cos(aa), z + lg * math.sin(aa)
                    if dans_couloir and abs(x2) > DEMI_COULOIR - 1.5:
                        break
                    if not dans_couloir and abs(x2) < X_BORD + 1:
                        break
                    taille = (math.hypot(x2 - x, z2 - z) + 0.3 * ep, 0.3, ep)
                    ctr = ((x + x2) / 2, -0.05 + (0.1 if s_ == 0 else 0.0), (z + z2) / 2)
                    yaw = math.degrees(math.atan2(-(z2 - z), x2 - x))
                    if dans_couloir:
                        b.boxc(ctr, taille, c("obsidienne"), yaw=yaw, name="Fissure", **eteinte)
                    else:
                        b.boxc(ctr, taille, c("feu") if s_ == 0 else c("feu_cramoisi"), yaw=yaw, name="Fissure", **neon)
                    x, z, ep = x2, z2, ep * 0.72


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
    fissures_bataille(b)


def cercle_magique(b: Builder) -> None:
    """Cercle magique de la place des œufs (rayon 34) : estrade de disques concentriques de 0,1 de haut chacun
    (anneaux Neon violets, bande de glyphes abstraits dont huit composés, anneau fin à douze graduations, carré
    inscrit en losange avec un nœud runique à chaque sommet, cœur cramoisi).
    Géométrie générique : ni étoile (5, 6 ou 8 branches), ni trèfle, ni lettre d'un alphabet réel."""
    z = Z_PLACE
    lum = dict(material="Neon", shadow=False)
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
        # bande de glyphes : 24 marques abstraites (barre + point) entre r = 27 et r = 31 ; une sur trois est un glyphe
        # composé (barre, barre courte décalée vers le centre, petit losange au bout opposé) : ni lettre ni chiffre
        for k in range(24):
            a = 2 * math.pi * k / 24
            ca, sa = math.cos(a), math.sin(a)
            long_ = 3.0 if k % 3 == 0 else 1.8
            r = 29.2
            yaw = -math.degrees(a)                      # X local radial, Z local tangent
            with b.at((r * ca, y + 0.05, z + r * sa), yaw=yaw):
                b.boxc((0, 0, 0), (long_, 0.1, 0.6), c("lueur_violette"), name="Glyphe", **lum)
                if k % 3 == 0:
                    sens = 1 if k % 2 else -1
                    b.boxc((sens * 0.55, 0, 1.15), (1.5, 0.1, 0.5), c("lueur_violette"), name="Glyphe", **lum)
                    b.part("block", (0.6, 0.1, 0.6), (-sens * 1.75, 0, -0.75), rot_y(45), c("lueur_violette_pale"),
                           name="Glyphe", **lum)
            if k % 3:
                r2 = 30.6 if k % 2 else 27.6
                b.boxc((r2 * ca, y + 0.05, z + r2 * sa), (0.6, 0.1, 0.6), c("lueur_violette_pale"), yaw=-math.degrees(a),
                       name="Glyphe", **lum)
        disque(26.2, "lueur_violette", neon=True)
        disque(25.0, "dalle_noire")
        # sur ce même niveau (rien ne se chevauche) : carré inscrit en losange (sommets sur les axes, 4 barres Neon)
        # avec un nœud runique à chaque sommet (losange Neon de 3 à cœur sombre, sans collision) ; anneau fin de
        # r = 18,5 en 16 segments, interrompu là où passent les barres ; douze graduations radiales de r = 13 à 17,5
        # (raccourcies devant les barres)
        for (sx, sz) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            b.boxc((sx * 12.0, y + 0.05, z + sz * 12.0), (24 * math.sqrt(2) + 0.8, 0.1, 0.8), c("lueur_cramoisie"),
                   yaw=45 if sx * sz > 0 else -45, material="Neon", shadow=False, name="Losange")
        for (nx, nz) in ((24.0, 0.0), (-24.0, 0.0), (0.0, 24.0), (0.0, -24.0)):
            b.part("block", (3.0, 0.2, 3.0), (nx, y + 0.1, z + nz), rot_y(45), c("lueur_cramoisie"), name="Noeud",
                   collide=False, **lum)
            b.part("block", (1.3, 0.1, 1.3), (nx, y + 0.25, z + nz), rot_y(45), c("obsidienne"), name="Noeud",
                   studs="none", collide=False)
        corde = 2 * 18.5 * math.sin(math.radians(7.5)) + 0.1
        for k in range(24):
            if k % 3 == 1:                               # segments centrés sur 22,5° + 45°·n : croisement des barres
                continue
            a = math.radians(7.5 + 15.0 * k)
            b.boxc((18.5 * math.cos(a), y + 0.05, z + 18.5 * math.sin(a)), (0.5, 0.1, corde), c("lueur_violette"),
                   yaw=-math.degrees(a), name="Anneau", **lum)
        for k in range(12):
            a = math.radians(15.0 + 30.0 * k)
            r_barre = 24.0 / (abs(math.cos(a)) + abs(math.sin(a)))
            r1 = min(17.5, r_barre - 0.7)
            b.boxc(((13.0 + r1) / 2 * math.cos(a), y + 0.05, z + (13.0 + r1) / 2 * math.sin(a)), (r1 - 13.0, 0.1, 0.45),
                   c("lueur_violette"), yaw=-math.degrees(a), name="Graduation", **lum)
        y += 0.1
        disque(12.0, "lueur_violette", neon=True)
        disque(11.0, "dalle_rituelle")
        disque(3.0, "lueur_cramoisie", neon=True)


# ---------------------------------------------------------------------------
# Séquence 1 : abords et porte d'entrée
# ---------------------------------------------------------------------------

def mob(b: Builder, fn: str, x: float, z: float, nom: str, yaw: float = 0.0, y: float = 0.0, **params) -> dict:
    """Pose un objet de `assets/mobilier.py` en (x, y, z) (raccourci de place())."""
    return place(b, "mobilier", fn, (x, y, z), yaw=yaw, group=nom, emprise=(4, 4, 4), **params)


def abords(b: Builder) -> None:
    """Abords (z 0 → +40, groupe Abords) : vieille route entre deux murets de pierres sèches, arbres morts et sapins,
    poteau indicateur, rochers (les lucioles dorées s'accrochent aux tours de la porte)."""
    for i, (x, z, fn, v) in enumerate(((-66, 30, "arbre_mort", 0), (-92, 14, "sapin_sombre", 1), (-150, 26, "sapin_sombre", 0),
                                       (70, 24, "sapin_sombre", 2), (98, 10, "arbre_mort", 2), (168, 30, "sapin_sombre", 0))):
        place(b, "mobilier", fn, (x, 0, z), group=f"Abords/Arbre{i}", emprise=(8, 8, 14), variant=v,
              hauteur=14 + 2 * (i % 3))
    place(b, "mobilier", "poteau_indicateur", (-51, 0, 26), yaw=90, group="Abords/Indicateur", emprise=(1, 13, 8),
          textes=("VILLAGE", "CHÂTEAU"), variant=1)
    for i, (x, z, v) in enumerate(((-51.5, 9.0, 0), (51.5, 11.0, 1), (51.5, 31.0, 2))):
        mob(b, "muret", x, z, f"Abords/Muret{i}", yaw=90, longueur=10, variant=v)
    for i, (x, z, v, t) in enumerate(((-78, 20, 1, 3.0), (86, 31, 3, 3.5), (-120, 36, 0, 4.0))):
        mob(b, "rocher", x, z, f"Abords/Rocher{i}", yaw=35 * i, variant=v, taille=t)


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
    # lucioles dorées (refBC2) : elles s'accrochent aux tours, jamais au-dessus du couloir sous 30 : un rideau plaqué
    # contre la face de chaque tour côté couloir et le long des vantaux ouverts (|x| 46,5 → 47,7), une couronne autour
    # du bas de chaque toit conique
    for s in (-1, 1):
        gd = "GD"[s > 0]
        place(b, "mobilier", "lucioles", (s * 47.1, 1, Z_PORTE - 1), group=f"Porte/Lucioles{gd}", emprise=(1.2, 22, 48),
              variant=0, rayon=11, rayon_x=0.6, hauteur=48, nombre=30)
        # couronne décalée vers -Z : rien ne dépasse z = 0 (les abords se suppriment quand on enchaîne les zones)
        place(b, "mobilier", "lucioles", (s * X_TOUR_PORTE, 60, Z_PORTE - 4), group=f"Porte/LuciolesToit{gd}",
              emprise=(38, 38, 24), variant=0, rayon=19, rayon_min=15.5, hauteur=24, nombre=12)


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


# Village abandonné : deux tiers des fenêtres sont éteintes, noires ou condamnées de planches ; restent une bougie à
# l'auberge et dans deux chaumières (le bourg, lui, garde ses fenêtres chaudes)
CHAMPS_G = [
    ("batiments:grange", -50, 20, 14, {"variant": 0}),
    ("batiments:chaumiere", -70, 12, 12, {"variant": 3, "lumieres": "eteintes"}),
]
CHAMPS_D = [
    ("batiments:chaumiere", -46, 14, 12, {"variant": 1, "lumieres": "eteintes"}),
]
VILLAGE_G = [
    ("batiments:chaumiere", -88, 14, 12, {"variant": 0}),
    ("batiments:maison_pierre", -106, 16, 14, {"variant": 0, "etages": 2, "enseigne": "FORGE", "lumieres": "eteintes"}),
    ("batiments:maison_ruine", -123, 12, 12, {"variant": 0}),
    ("batiments:chaumiere", -186, 14, 12, {"variant": 2, "lumieres": "eteintes"}),
]
VILLAGE_D = [
    ("batiments:maison_pierre", -88, 16, 14, {"variant": 1, "etages": 2, "lumieres": "eteintes"}),
    ("batiments:chaumiere", -106, 14, 12, {"variant": 1}),
    ("batiments:maison_ruine", -124, 12, 12, {"variant": 1}),
    ("batiments:chaumiere", -143, 14, 12, {"variant": 4}),
    ("batiments:maison_ruine", -161, 12, 12, {"variant": 2}),
    ("batiments:maison_pierre", -182, 16, 14, {"variant": 2, "etages": 2, "enseigne": "AUBERGE", "lumieres": "faible"}),
]
# Maisons du second rang (x, z, largeur, étages), toutes tournées vers le couloir : leurs toits dépassent des
# premières rangées (ruines, chaumières) et ferment l'horizon des cours
FOND = [(-104, -92, 12, 1), (-106, -186, 12, 2), (-100, -207, 12, 2), (-104, -292, 14, 2), (98, -232, 12, 2),
        (100, -284, 12, 1), (-84, -123, 12, 1), (96, -258, 12, 2), (122, -245, 12, 1), (-84, -201, 12, 1)]


def champs(b: Builder) -> list:
    """Champs (z -32 → -80) : grange et chaumière à gauche, moulin en retrait ; à droite une chaumière, les CÔTES
    GÉANTES du démon qui sortent des labours, meules, puits, charrettes, clôtures des parcelles."""
    poses = rangee(b, -1, CHAMPS_G, "Champs/G", x_facade=57)
    poses += rangee(b, 1, CHAMPS_D, "Champs/D", x_facade=57)
    place(b, "batiments", "moulin", (-112, 0, -62), yaw=face_couloir(-1), group="Champs/Moulin", emprise=(14, 14, 40),
          variant=0)
    place(b, "monuments", "cotes_geantes", (X_COTES, 0, Z_COTES), yaw=YAW_COTES, group="Monuments/Cotes", emprise=(56, 36, 36),
          variant=0, longueur=56, hauteur=36)
    for i, (x, z, v) in enumerate(((-150, -50, 0), (-176, -66, 1), (164, -40, 2), (80, -96, 0), (-86, -46, 2),
                                   (-94, -55, 0), (176, -88, 1))):
        mob(b, "meule", x, z, f"Champs/Meule{i}", variant=v)
    mob(b, "puits", -51.2, -60, "Champs/Puits", variant=0)
    mob(b, "charrette", 52, -62, "Champs/Charrette", yaw=200, variant=2)
    mob(b, "charrette", -50.5, -48, "Champs/CharretteFoin", yaw=8, variant=2)
    mob(b, "charrette", -130, -42, "Champs/CharretteSacs", yaw=75, variant=0)
    for i, z in enumerate((-58.0, -72.0)):                  # clôtures le long des labours, à droite
        mob(b, "cloture_bois", 55.5, z, f"Champs/ClotureD{i}", yaw=90, longueur=12, variant=(i + 1) % 4)
    for i, (x, z, yaw, L, v) in enumerate(((-110, -80, 0, 24, 0), (-142, -34, 0, 24, 3), (88, -34, 0, 20, 0),
                                           (-160, -80, 0, 18, 1))):
        mob(b, "cloture_bois", x, z, f"Champs/ClotureParcelle{i}", yaw=yaw, longueur=L, variant=v)
    for i, (x, z, v) in enumerate(((-84, -36, 1), (72, -66, 3), (150, -96, 0), (-140, -72, 1), (168, -64, 0))):
        mob(b, "arbre_mort", x, z, f"Champs/ArbreMort{i}", yaw=30 * i, variant=v, hauteur=13 + i % 2)
    mob(b, "lanterne_fer", -52, -42, "Champs/Lanterne", yaw=face_couloir(-1), variant=1)
    mob(b, "tonneaux", -50.5, -77.5, "Champs/Tonneaux", variant=0)
    mob(b, "caisses", 51, -55, "Champs/Caisses", variant=1)
    return poses


def village(b: Builder) -> list:
    """Village abandonné (z -80 → -196) : chaumières, maisons de pierre et ruines ; église, parvis et cimetière à
    gauche ; à droite, derrière les maisons, la colline boisée et le CRÂNE DE DÉMON cornu (repère de la première
    moitié). Bas-côtés : lanternes, tonneaux, caisses, charrettes, puits, arbres morts, clôtures."""
    poses = rangee(b, -1, VILLAGE_G, "Village/G")
    poses += rangee(b, 1, VILLAGE_D, "Village/D")
    place(b, "batiments", "eglise", (-(X_BORD + 22), 0, Z_EGLISE), yaw=face_couloir(-1), group="Monuments/Eglise",
          emprise=(26, 44, 56), variant=0, largeur=26, profondeur=44)
    # cimetière autour de l'église (devant, de part et d'autre du parvis, et derrière), murets
    tombes = ((-61, -133), (-66, -136), (-72, -132.5), (-79, -136), (-86, -133), (-62, -171), (-69, -174),
              (-76, -171), (-84, -174), (-92, -171), (-104.5, -145), (-106, -153), (-104, -160), (-110, -164),
              (-118, -158), (-112, -170), (-120, -146))
    for i, (x, z) in enumerate(tombes):
        place(b, "mobilier", "pierre_tombale", (x, 0, z), yaw=face_couloir(-1) + (i % 3 - 1) * 8,
              group=f"Village/Cimetiere/Tombe{i}", emprise=(2, 2, 3), variant=i % 4)
    for i, (x, z) in enumerate(((-56.4, -135.0), (-56.4, -173.0), (-125.0, -150.0), (-125.0, -164.0))):
        mob(b, "muret", x, z, f"Village/Cimetiere/Muret{i}", yaw=90, longueur=10, variant=i)
    place(b, "mobilier", "lucioles", (-72, 2, -138), group="Village/Cimetiere/FeuxFollets", emprise=(14, 14, 9),
          variant=1, rayon=7, hauteur=8, nombre=16)              # feux follets violets au-dessus des tombes
    # colline du crâne, puis le crâne posé sur son sommet
    info = place(b, "monuments", "colline_crane", (X_COLLINE, 0, Z_COLLINE), yaw=face_couloir(1),
                 group="Monuments/Colline", emprise=(110, 100, H_COLLINE), variant=0, largeur=110, profondeur=100,
                 hauteur=H_COLLINE)
    place(b, "monuments", "crane_demon", (X_COLLINE, info.get("hauteur", H_COLLINE), Z_COLLINE), yaw=YAW_CRANE,
          group="Monuments/Crane", emprise=(60, 56, 64), variant=0, hauteur=64)
    # rue du village : lanternes, tonneaux, caisses, charrettes, puits, arbres morts
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
             ("caisses", 51.8, -152, 2), ("charrette", 51.5, -118, 1), ("puits", 50.6, -133, 1),
             ("tonneaux", -50, -82, 1), ("tonneaux", -50, -191, 2), ("caisses", 50.5, -110.5, 0),
             ("tonneaux", 50.5, -166, 2), ("caisses", 50.2, -170.5, 3))
    for i, (fn, x, z, v) in enumerate(props):
        place(b, "mobilier", fn, (x, 0, z), yaw=0 if fn != "charrette" else 160, group=f"Village/{fn}{i}",
              emprise=(4, 4, 3), variant=v)
    for i, (x, z, v, yaw) in enumerate(((-104, -124, 0, 0), (74, -130, 2, 0), (75, -170, 1, 0), (-114, -150, 3, 0),
                                        (-49.5, -136, 1, 180), (50.0, -157, 3, 0))):
        mob(b, "arbre_mort", x, z, f"Village/ArbreMort{i}", yaw=yaw, variant=v, hauteur=14)
    for i, (z, v) in enumerate(((-104.0, 1), (-150.0, 3), (-186.0, 0))):   # clôtures des cours, au pied de la colline
        mob(b, "cloture_bois", 75.5, z, f"Village/Cloture{i}", yaw=90, longueur=12, variant=v)
    mob(b, "rocher", 77, -118, "Village/Rocher", yaw=20, variant=2, taille=3.0)
    # racines noires du démon qui sortent du pied de la colline et crèvent les cours, vers le couloir
    for i, (x, z, yaw, v, L) in enumerate(((88, -112, 8, 0, 22), (88, -146, -12, 2, 22), (88, -178, 6, 3, 22))):
        place(b, "abime", "racine_geante", (x, 0, z), yaw=yaw, group=f"Village/RacineColline{i}", emprise=(L, 6, 9),
              variant=v, longueur=L, hauteur=9)
    clotures_rue(b)
    return poses


# Clôtures au bord de la rue des champs et du village (|x| = 46.6) : elles dessinent les cours de devant, s'ouvrent
# devant chaque porte et laissent le parvis de l'église ouvert ; (z début, z fin, variante) ; v1 = planches cassées
CLOTURES_RUE = {
    -1: ((-38, -45, 0), (-55, -66, 0), (-74, -79, 3), (-81, -85, 0), (-91, -103, 0), (-109, -120, 1), (-179.5, -183, 1),
         (-189, -194.5, 0)),
    1: ((-38, -43, 0), (-49, -63.4, 0), (-64.6, -79, 3), (-81, -85, 0), (-91, -103, 0), (-109, -121, 0), (-127, -140, 0),
        (-146, -158, 1), (-164, -179, 0), (-185, -194.5, 3)),
}


def clotures_rue(b: Builder) -> None:
    for s, runs in CLOTURES_RUE.items():
        for i, (za, zb, v) in enumerate(runs):
            mob(b, "cloture_bois", s * 46.6, (za + zb) / 2, f"Village/ClotureRue{'GD'[s > 0]}{i}", yaw=90 if s < 0 else -90,
                longueur=abs(za - zb), variant=v)


# ---------------------------------------------------------------------------
# Séquence 4 : bourg de la tour aux grimoires
# ---------------------------------------------------------------------------

BOURG_G = [
    ("batiments:maison_haute", -204, 14, 14, {"variant": 0, "etages": 3}),
    ("batiments:maison_haute", -220, 14, 14, {"variant": 1, "etages": 4, "enseigne": "BIBLIOTHÈQUE"}),
    # place de la tour : z -228 → -272
    ("batiments:maison_haute", -280, 14, 14, {"variant": 2, "etages": 3, "enseigne": "POTIONS"}),
    ("batiments:maison_haute", -294, 12, 14, {"variant": 3, "etages": 4, "fioles": True}),
]
BOURG_D = [
    ("batiments:taverne", -210, 24, 16, {"variant": 0}),
    ("batiments:maison_haute", -231, 14, 14, {"variant": 4, "etages": 4, "fioles": True}),
    ("batiments:halle", -254, 26, 14, {"variant": 0}),
    ("batiments:maison_haute", -277, 14, 14, {"variant": 5, "etages": 3, "enseigne": "HERBORISTE"}),
    ("batiments:maison_haute", -293, 14, 14, {"variant": 2, "etages": 4}),
]
# Cordes à bannières au-dessus de la rue : à l'entrée et à la sortie du bourg
Z_CORDES = (-195.0, -302.0)
X_MAT = 48.6             # mâts sur les accotements
H_CORDE = 44.0           # corde aux mâts ; elle fléchit à 42 au milieu ; pointe des bannières à 34,45 (≥ 34)


def bourg(b: Builder) -> list:
    """Bourg (z -196 → -300) : à gauche la TOUR AUX GRIMOIRES sur son parvis (pupitre et nuée de grimoires),
    maisons hautes à colombages noirs ; à droite taverne, halle du marché, maisons hautes ; lanternes, bannières,
    cordes à bannières au-dessus de la rue."""
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
            if s > 0 and z == -272:
                z = -290.0
            x = s * 52.2
            place(b, "mobilier", "lanterne_fer", (x, 0, z), yaw=face_couloir(x), group=f"Bourg/Lanterne{'GD'[s > 0]}{i}",
                  emprise=(2, 4, 11), variant=(0, 2, 3)[i] if s < 0 else (3, 0, 2)[i])
    for i, (z, v) in enumerate(((-246.0, 0), (-260.0, 1))):  # étals devant la halle
        place(b, "mobilier", "etal", (50.8, 0, z), yaw=face_couloir(1), group=f"Bourg/Marche/Etal{i}", emprise=(7, 4, 7),
              variant=v)
    place(b, "mobilier", "panneau_pied", (52.0, 0, -238.5), yaw=face_couloir(1), group="Bourg/Marche/Panneau",
          emprise=(6, 2, 6), texte="MARCHÉ", variant=1)
    props = (("tonneaux", 51.5, -201, 0), ("caisses", 51.5, -223, 0), ("chaudron", -51.8, -286, 0),
             ("tonneaux", -51.5, -209, 2), ("caisses", -50.0, -199.5, 2), ("tonneaux", 50.0, -296.5, 3),
             ("caisses", 50.5, -265.2, 1))
    for i, (fn, x, z, v) in enumerate(props):
        place(b, "mobilier", fn, (x, 0, z), group=f"Bourg/{fn}{i}", emprise=(4, 4, 4), variant=v)
    cordes_bannieres(b)
    return poses


def cordes_bannieres(b: Builder) -> None:
    """Cordes à bannières unies tendues au-dessus de la rue du bourg : deux mâts sur les accotements, corde à
    H_CORDE qui fléchit de 2 au milieu, bannières pointues cramoisies, violettes et noires à liseré doré, dont la
    pointe reste au-dessus de 34 (ce qui enjambe le couloir garde son dessous à 34 ou plus). Aucun emblème."""
    toiles = ("toile_cramoisie", "toile_violette", "toile_noire")
    pts = ((-X_MAT, H_CORDE), (-16.0, H_CORDE - 2.0), (16.0, H_CORDE - 2.0), (X_MAT, H_CORDE))

    def y_corde(x):
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            if xa <= x <= xb:
                return ya + (yb - ya) * (x - xa) / (xb - xa)
        return H_CORDE

    fin = dict(collide=False, shadow=False)
    for i, z in enumerate(Z_CORDES):
        n0 = len(b.parts)
        nom = f"Bourg/Corde{i}"
        with b.group(nom):
            for s in (-1, 1):
                x = s * X_MAT
                b.box((x - 1.1, 0, z - 1.1), (x + 1.1, 1.2, z + 1.1), c("pierre_fonce"), studs="top", name="Socle")
                b.box((x - 0.4, 1.2, z - 0.4), (x + 0.4, H_CORDE + 2.5, z + 0.4), c("bois_noir"), name="Mat")
                b.box((x - 0.65, H_CORDE + 2.5, z - 0.65), (x + 0.65, H_CORDE + 3.0, z + 0.65), c("fer_fonce"),
                      name="Chapeau", collide=False)
                b.ball((x, H_CORDE + 3.45, z), 0.5, c("or"), name="Pommeau", collide=False)
            for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
                L = math.hypot(xb - xa, yb - ya)
                b.part("block", (L + 0.2, 0.25, 0.25), ((xa + xb) / 2, (ya + yb) / 2, z),
                       rot_z(math.degrees(math.atan2(yb - ya, xb - xa))), c("chaine"), name="Corde", **fin)
            for k, xk in enumerate((-37.0, -25.0, -13.0, 0.0, 13.0, 25.0, 37.0)):
                yk = y_corde(xk) - 0.15
                col = c(toiles[(k + i) % 3])
                b.box((xk - 1.6, yk - 6.0, z - 0.1), (xk + 1.6, yk, z + 0.1), col, name="Toile", **fin)
                b.box((xk - 1.75, yk - 0.7, z - 0.22), (xk + 1.75, yk + 0.12, z + 0.22), c("toile_or"), name="Lisere", **fin)
                b.wedge_under((xk - 1.6, yk - 7.4, z - 0.1), (xk, yk - 6.0, z + 0.1), col, down="-x", name="Pointe", **fin)
                b.wedge_under((xk, yk - 7.4, z - 0.1), (xk + 1.6, yk - 6.0, z + 0.1), col, down="+x", name="Pointe", **fin)
        b.__dict__.setdefault("poses", []).append((nom, "corde_bannieres", n0, len(b.parts)))


# ---------------------------------------------------------------------------
# Séquence 5 : champ de bataille des mages, aqueduc
# ---------------------------------------------------------------------------

def tente(b: Builder, variant: int = 0, largeur: float = 8.0, longueur: float = 10.0, hauteur: float = 6.0) -> dict:
    """Tente de toile à deux pans du camp des mages (7 pièces) : ouverture sombre à l'avant (-Z local), mâts et faîtage."""
    w, L, h = largeur, longueur, hauteur
    toile = c(("toile_ecru", "toile_grise", "toile_cramoisie", "toile_nuit")[variant % 4])
    bois = c("bois_fonce")
    with b.group("Tente"):
        b.wedge((-w / 2, 0, -L / 2), (0, h, L / 2), shade(toile, 0.9), down="-x", studs="top", name="Pan")
        b.wedge((0, 0, -L / 2), (w / 2, h, L / 2), toile, down="+x", studs="top", name="Pan")
        b.wedge((-w / 4, 0, -L / 2 - 0.12), (0, h / 2, -L / 2 - 0.02), c("noir"), down="-x", name="Ouverture",
                collide=False)
        b.wedge((0, 0, -L / 2 - 0.12), (w / 4, h / 2, -L / 2 - 0.02), c("noir"), down="+x", name="Ouverture",
                collide=False)
        for zz in (-L / 2 - 0.45, L / 2 + 0.45):
            b.box((-0.2, 0, zz - 0.2), (0.2, h + 0.9, zz + 0.2), bois, name="Mat")
        b.box((-0.16, h - 0.05, -L / 2 - 0.65), (0.16, h + 0.27, L / 2 + 0.65), bois, name="Faitage", collide=False)
    return {"emprise": (w, L + 1.3), "hauteur": h + 0.9}


def _penche_dehors(x: float, variant: int) -> float:
    """Yaw d'un bâton de mage (mobilier.baton_mage) pour qu'il penche vers l'extérieur du couloir."""
    alpha = 45.0 if variant % 4 in (0, 2) else -135.0         # direction de la pente dans le repère du bâton
    return alpha - (180.0 if x < 0 else 0.0)


# Grands bâtons de mage plantés le long des accotements du champ de bataille (x, z, taille), un tous les 16 environ
# de chaque côté, en quinconce, à l'écart des piles de l'aqueduc ; orbes violet, vert, doré, cramoisi
GRANDS_BATONS = ((-52.5, -307, 2.2), (52.5, -312, 1.9), (-53.0, -320, 2.4), (51.5, -326, 2.1), (-51.5, -336, 1.9),
                 (53.0, -338, 2.3), (-52.5, -364, 2.1), (51.5, -366, 2.4), (-51.5, -378, 2.0), (53.0, -380, 2.2),
                 (-53.0, -396, 2.4), (51.5, -394, 2.0))
FEUX_ANNEAUX = ((76, -326), (-131, -316))      # feux de camp entourés de trois petits bâtons


def bataille(b: Builder) -> None:
    """Champ de bataille (z -300 → -404, refBC4) : terre calcinée et cendre, cratères (fissures éteintes dans le
    couloir, incandescentes sur les côtés), grands bâtons de mage plantés le long des deux accotements (≈ 20 de haut,
    orbes de 2,4), murs et tours en ruine rapprochés du couloir, arcade effondrée sous l'aqueduc, armes abandonnées,
    feux de camp entourés de petits bâtons, camp de tentes, menhirs gravés ; l'AQUEDUC ruiné et sombre (refBC3) passe
    au-dessus du couloir en z = -352 : grande brèche à droite (x 100 → 164, cascade), travée tombée à gauche
    (x -158 → -126), parapets édentés, deux travées affaissées."""
    place(b, "remparts", "aqueduc", (0, 0, Z_AQUEDUC), group="Monuments/Aqueduc", attente=_attente_aqueduc, variant=3,
          largeur=2 * X_FOND, ouverture=OUVERTURE_AQUEDUC, dessous=DESSOUS_AQUEDUC, hauteur=H_AQUEDUC,
          rupture=RUPTURES_AQUEDUC, affaisse=AFFAISSEMENTS_AQUEDUC)
    tours = ((-72, -322, 10, 44, 0), (-160, -388, 12, 34, 1), (74, -394, 11, 52, 2))
    for i, (x, z, r, h, v) in enumerate(tours):
        place(b, "remparts", "ruine_tour", (x, 0, z), yaw=face_couloir(x), group=f"Bataille/Tour{i}",
              emprise=(2 * r, 2 * r, h), variant=v, rayon=r, hauteur=h)
    murs = ((-66, -380, -90, 36, 18, 0), (-122, -330, 0, 40, 16, 1), (70, -312, 90, 24, 20, 2), (150, -372, 20, 34, 14, 3),
            (-112, -376, 75, 30, 12, 0), (-62, -342, -90, 18, 12, 3), (60, -380, 90, 20, 13, 0))
    for i, (x, z, yaw, L, h, v) in enumerate(murs):
        place(b, "remparts", "ruine_mur", (x, 0, z), yaw=yaw, group=f"Bataille/Mur{i}", emprise=(L, 5, h), variant=v,
              longueur=L, hauteur=h, epaisseur=5)
    for i, (x, z, yaw, v) in enumerate(((-128, -392, -60, 0), (138, -324, 70, 1), (64, -340, 90, 3))):
        place(b, "remparts", "arche_effondree", (x, 0, z), yaw=yaw, group=f"Bataille/Arche{i}", emprise=(30, 6, 26),
              variant=v, largeur=30, hauteur=26)
    # grands bâtons de mage le long des accotements, penchés vers l'extérieur
    for i, (x, z, t) in enumerate(GRANDS_BATONS):
        v = i % 4
        place(b, "mobilier", "baton_mage", (x, 0, z), yaw=_penche_dehors(x, v), group=f"Bataille/GrandBaton{i}",
              emprise=(4, 4, 21), variant=v, taille=t)
    # petits bâtons plantés en cercle autour de deux feux de camp
    for j, (fx, fz) in enumerate(FEUX_ANNEAUX):
        for k in range(3):
            a = math.radians(90 + 120 * k)
            x, z = fx + 4.5 * math.cos(a), fz + 4.5 * math.sin(a)
            place(b, "mobilier", "baton_mage", (x, 0, z), yaw=37 * (3 * j + k), group=f"Bataille/Baton{3 * j + k}",
                  emprise=(2, 2, 10), variant=(j + k) % 4)
    armes = (("epee_plantee", -52, -312, 0), ("epee_plantee", 53, -330, 1), ("epee_plantee", -51, -372, 2),
             ("epee_plantee", 52, -402, 3), ("bouclier", -54, -330, 0), ("bouclier", 52, -370, 1),
             ("armes_abandonnees", -88, -342, 0), ("armes_abandonnees", 84, -366, 1), ("armes_abandonnees", -96, -400, 2),
             ("bouclier", 70, -334, 2), ("armes_abandonnees", 50.5, -319, 3), ("epee_plantee", -49.5, -390, 1),
             ("epee_plantee", 49.5, -399, 0), ("bouclier", -49.5, -383, 3))
    for i, (fn, x, z, v) in enumerate(armes):
        place(b, "mobilier", fn, (x, 0, z), yaw=23 * i, group=f"Bataille/{fn}{i}", emprise=(4, 4, 5), variant=v)
    for i, (x, z, v) in enumerate(((-78, -405, 1), (76, -326, 0), (118, -382, 3), (-140, -340, 2), (-131, -316, 3))):
        place(b, "mobilier", "feu_camp", (x, 0, z), group=f"Bataille/Feu{i}", emprise=(6, 6, 5), variant=v)
    # camp des mages (à gauche, au sortir du bourg) : tentes autour d'un feu
    for i, (x, z, yaw, v) in enumerate(((-122, -303, 20, 0), (-142, -307, -15, 1), (-112, -318, 80, 2))):
        n0 = len(b.parts)
        with b.at((x, 0, z), yaw=yaw, group=f"Bataille/Tente{i}"):
            tente(b, variant=v)
        b.__dict__.setdefault("poses", []).append((f"Bataille/Tente{i}", "tente", n0, len(b.parts)))
    for i, (x, z, v) in enumerate(((-58.5, -368, 1), (57, -403, 3), (-150, -298, 1))):
        place(b, "mobilier", "banniere", (x, 0, z), group=f"Bataille/Banniere{i}", emprise=(4.2, 1.8, 12), variant=v,
              hauteur=11)
    place(b, "mobilier", "nuee_grimoires", (-84, 0, -372), group="Bataille/Nuee", emprise=(10, 10, 12), variant=3,
          rayon=3.8, hauteur=11, nombre=8)
    for i, (x, z, v) in enumerate(((75, -370, 1), (-80, -338, 0))):
        mob(b, "pierre_runique", x, z, f"Bataille/Menhir{i}", yaw=face_couloir(x), variant=v)
    for i, (x, z, v) in enumerate(((-152, -331, 2), (124, -310, 0), (-170, -312, 1), (168, -312, 3))):
        place(b, "mobilier", "arbre_mort", (x, 0, z), group=f"Bataille/ArbreMort{i}", emprise=(10, 10, 15), variant=v,
              hauteur=15)
    for i, (x, z, v) in enumerate(((-100, -308, 0), (58, -342, 1), (-60, -402, 2))):
        place(b, "mobilier", "rocher", (x, 0, z), yaw=40 * i, group=f"Bataille/Rocher{i}", emprise=(5, 5, 4), variant=v,
              taille=3.5)


# ---------------------------------------------------------------------------
# Séquences 6 et 7 : place rituelle des œufs, arbre démoniaque, château
# ---------------------------------------------------------------------------

def place_rituelle(b: Builder) -> None:
    """Place rituelle (z -404 → -498) : cercle magique au sol (voir cercle_magique), six grands obélisques noirs à
    flammes (28), grandes racines démoniaques qui encadrent le cercle, épines, braseros, cristaux ; l'ARBRE
    DÉMONIAQUE à droite (les ÎLOTS FLOTTANTS sont posés par ilots(), après les falaises qui les ancrent) ; deux fils
    de lumière violette relient le cercle à la porte du château (dans le sol)."""
    cercle_magique(b)
    obelisques = ((-53, -418, 0), (53, -418, 1), (-58, -448, 2), (58, -448, 0), (-53, -478, 1), (53, -478, 2))
    for i, (x, z, v) in enumerate(obelisques):
        place(b, "abime", "obelisque", (x, 0, z), yaw=face_couloir(x), group=f"Place/Obelisque{i}", emprise=(7, 7, 35),
              variant=v, hauteur=28)
    # racines démoniaques : trois grandes au bord de la place, le long du couloir (cadre du cercle), trois plus loin
    racines = ((-67, -430, -90, 0, 30, 14), (67, -462, 90, 1, 30, 14), (-67, -476, -90, 2, 30, 14), (82, -424, -20, 1, 24, 10),
               (96, -486, -60, 0, 24, 10), (-120, -440, 100, 1, 24, 10))
    for i, (x, z, yaw, v, L, h) in enumerate(racines):
        place(b, "abime", "racine_geante", (x, 0, z), yaw=yaw, group=f"Place/Racine{i}", emprise=(L, 6, h), variant=v,
              longueur=L, hauteur=h)
    for i, (x, z, v) in enumerate(((-50, -432, 0), (50.5, -462, 1), (-50.5, -490, 3), (51, -410, 2), (66, -440, 1),
                                   (-68, -456, 0), (49.5, -440, 3), (-49.5, -459, 3))):
        place(b, "mobilier", "epines_racines", (x, 0, z), yaw=50 * i, group=f"Place/Epines{i}", emprise=(4, 4, 5),
              variant=v)
    for i, (x, z) in enumerate(((-48.6, -406), (48.6, -406), (-48.6, -494), (48.6, -494))):
        place(b, "mobilier", "brasero", (x, 0, z), group=f"Place/Brasero{i}", emprise=(3, 3, 6), variant=(1, 2, 2, 1)[i])
    for i, (x, z, v, t) in enumerate(((-100, -420, 0, 6), (-124, -488, 2, 6), (76, -452, 1, 6), (-172, -436, 0, 7),
                                      (174, -404, 1, 6), (-170, -478, 2, 6))):
        place(b, "abime", "cristaux", (x, 0, z), yaw=30 * i, group=f"Place/Cristaux{i}", emprise=(6, 6, 7), variant=v, taille=t)
    place(b, "abime", "arbre_demon", (X_ARBRE, 0, Z_ARBRE), yaw=face_couloir(1), group="Monuments/Arbre",
          emprise=(136, 136, H_ARBRE), variant=0, hauteur=H_ARBRE)


def chateau(b: Builder) -> None:
    """Château démoniaque (repère final, refBC3) : forteresse gothique noire sur falaise, flèches, fenêtres violettes,
    porte en arc brisé de 100 × 40 (sommet ≈ 66) par laquelle le couloir sort en z = -548."""
    place(b, "abime", "chateau_demon", (0, 0, (Z_CHATEAU + Z_SORTIE) / 2), yaw=180, group="Monuments/Chateau",
          attente=_attente_chateau, variant=0, largeur=2 * X_FOND, profondeur=PROF_CHATEAU, ouverture=OUVERTURE,
          h_passage=H_PASSAGE)


# Îlots flottants (x, y, z, taille, variante) haut dans le ciel au-dessus de la place, et le point visé pour leur
# ancrage sur le dessus de la falaise la plus proche (une chaîne en biais par îlot)
ILOTS = ((-100, 104, -470, 30, 0, (-200, -464)), (-162, 124, -490, 26, 1, (-210, -486)),
         (-150, 90, -420, 22, 2, (-200, -414)), (98, 112, -384, 24, 3, (198, -380)))


def _ancrage_falaise(b: Builder, x: float, z: float, rayon: float = 14.0, d: float = 1.3, depart=None):
    """Point (x, y, z) d'un ancrage de 2,6 × 2,6 posé à plat sur une colonne de falaise (`Cotes/Falaise*`, blocs
    `Roche`) près de (x, z), le plus haut possible ; aucune autre pièce de la falaise ne le recouvre ni ne coupe la
    chaîne tendue depuis `depart` (point d'accroche sous l'îlot). None sinon."""
    boites = [(_bornes(p), p) for p in b.parts if p.group.startswith("Cotes/Falaise")]
    roches = [(lo, hi) for (lo, hi), p in boites if p.name == "Roche" and p.shape == "block"]

    def coupe_chaine(a_, b_):
        a_, b_ = np.asarray(a_, float), np.asarray(b_, float)
        L = float(np.linalg.norm(b_ - a_))
        for t in np.arange(0.0, max(0.0, L - 2.5), 0.8) / max(L, 1e-6):
            q = a_ + (b_ - a_) * t
            for (lo, hi), _p in boites:
                if lo[0] - 0.4 < q[0] < hi[0] + 0.4 and lo[1] - 0.4 < q[1] < hi[1] + 0.4 and lo[2] - 0.4 < q[2] < hi[2] + 0.4:
                    return True
        return False

    best = None
    for dx in np.arange(-rayon, rayon + 0.1, 2.0):
        for dz in np.arange(-rayon, rayon + 0.1, 2.0):
            xx, zz = x + float(dx), z + float(dz)
            tops = [hi[1] for (lo, hi) in roches
                    if lo[0] <= xx - d and hi[0] >= xx + d and lo[2] <= zz - d and hi[2] >= zz + d]
            if not tops:
                continue
            y = max(tops)
            if any(lo[0] < xx + d + 0.3 and hi[0] > xx - d - 0.3 and lo[2] < zz + d + 0.3 and hi[2] > zz - d - 0.3
                   and hi[1] > y + 0.05 for (lo, hi), _p in boites):
                continue
            score = y - 0.3 * math.hypot(float(dx), float(dz))
            if best is not None and score <= best[0]:
                continue
            if depart is not None and coupe_chaine(depart, (xx, y + 2.7, zz)):
                continue
            best = (score, (xx, float(y), zz))
    return None if best is None else best[1]


def ilots(b: Builder) -> None:
    """Îlots de roche noire qui flottent par magie haut au-dessus de la place (85-120, contre le ciel), chacun tenu
    par une chaîne en biais vers un ancrage sur le dessus de la falaise la plus proche ; lucioles violettes autour."""
    for i, (x, y, z, t, v, (ax, az)) in enumerate(ILOTS):
        u = np.array([ax - x, 0.0, az - z])
        u /= np.linalg.norm(u)
        pt = _ancrage_falaise(b, ax, az, depart=(x + u[0] * t * 0.39, y - 3.4, z + u[2] * t * 0.32))
        if pt is None:
            pt = (ax, 0.0, az)
        ancre = (pt[0] - x, pt[1] - y, pt[2] - z)
        place(b, "abime", "ilot_flottant", (x, y, z), group=f"Place/Ilot{i}", emprise=(t, t, t * 0.8), variant=v,
              taille=t, ancres=(ancre,))
    for i, (x, y, z, r, h, n) in enumerate(((-100, 80, -470, 16, 30, 10), (-162, 102, -490, 13, 26, 8))):
        place(b, "mobilier", "lucioles", (x, y, z), group=f"Place/LuciolesIlots{i}", emprise=(2 * r, 2 * r, h), variant=1,
              rayon=r, hauteur=h, nombre=n)


# ---------------------------------------------------------------------------
# Côtés : forêt, falaises, montagne de la capitale, limites
# ---------------------------------------------------------------------------

BOSQUETS = (   # (x, z, nombre, rayon) : sapins sombres et arbres morts mêlés (à l'intérieur des terres) ; derrière
    # le bourg, un sous-bois de part et d'autre
    (-172, -42, 3, 10), (-160, -222, 4, 12), (150, -238, 4, 12), (120, -292, 2, 8), (-150, -262, 3, 10),
    (168, -268, 4, 11), (140, -297, 2, 6), (-128, -206, 3, 8), (-182, -288, 3, 9))
FALAISES = (   # (x, z, longueur, profondeur, hauteur, yaw) ; la dernière à gauche rejoint la falaise du château
    (-205, -330, 60, 50, 34, -90), (-205, -390, 60, 50, 48, -90), (-205, -458, 76, 50, 62, -90),
    (205, -330, 60, 50, 34, 90), (205, -390, 60, 50, 46, 90), (215, -458, 76, 40, 58, 90))


def lisiere(b: Builder) -> None:
    """Lisière de sapins sombres et d'arbres morts le long des bords du sol (|x| 198-232), des abords jusqu'aux
    falaises : la limite latérale de la zone. Elle s'interrompt devant l'enceinte et la montagne de la capitale."""
    rng = np.random.default_rng(29)
    for s in (-1, 1):
        z, k = 36.0, 0
        while z > Z_BATAILLE + 4:
            x = s * float(rng.uniform(198, 231))
            libre = not (-27 < z < 5)                               # enceinte (et rien à cheval sur z = 0)
            if s < 0 and -152 < z < -72:                            # montagne de la capitale
                libre = False
            if libre:
                mort = float(rng.random()) < 0.2
                fn = "arbre_mort" if mort else "sapin_sombre"
                grp = f"Abords/Lisiere{'GD'[s > 0]}{k:02d}" if z > Z_ENTREE else f"Cotes/Lisiere{'GD'[s > 0]}{k:02d}"
                place(b, "mobilier", fn, (x, 0, z), yaw=float(rng.uniform(0, 90)), group=grp, emprise=(10, 10, 24),
                      variant=int(rng.integers(0, 4)), hauteur=15.0 if mort else float(rng.uniform(19, 27)))
                k += 1
            z -= float(rng.uniform(10, 15))


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
    lisiere(b)
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
    ilots(b)
    limites(b)
    reperes(b)
    decouper(b)
    for p in b.parts:                       # petites pièces décoratives (ou petites et hors de portée) : sans collision
        if not p.collide:
            continue
        if max(p.size) < 1.0 or (max(p.size) < 3.0 and _bornes(p)[0][1] > 12.0):
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


def sous_34_au_dessus(b: Builder, y_max: float = 34.0) -> list:
    """Ce qui passe au-dessus du couloir (|x| < 46) avec son dessous entre 30 et 34 (hors lucioles) : ce qui
    enjambe le couloir doit garder son dessous à 34 ou plus."""
    out = []
    for p in b.parts:
        if _est_sol(p.group) or p.name == "Luciole":
            continue
        lo, hi = _bornes(p)
        if lo[0] < X_LIBRE and hi[0] > -X_LIBRE and lo[1] < y_max and hi[1] > Y_LIBRE \
                and hi[2] > Z_SORTIE and lo[2] < Z_ABORDS:
            out.append((p.group, p.name, round(lo[1], 2)))
    return out


FEUILLAGES = ("sapin_sombre", "arbre_mort", "lucioles", "nuee_grimoires")


def _accepte(ga: str, gb: str) -> str | None:
    """Contacts voulus entre deux poses (raison), comptés à part par --chevauchements."""
    racines = {ga.split("/")[0], gb.split("/")[0]}
    paire = {"/".join(ga.split("/")[:2]), "/".join(gb.split("/")[:2])}
    if ga.split("/")[:2] == gb.split("/")[:2] and ga.startswith("Cotes/Bosquet"):
        return "bosquet serré (étages de sapins mêlés)"
    if all("/Lisiere" in g for g in (ga, gb)):
        return "lisière serrée (étages de sapins mêlés)"
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
    if "Monuments/Colline" in paire and any("/RacineColline" in g for g in (ga, gb)):
        return "racines qui sortent du pied de la colline"
    if racines == {"Place", "Cotes"} and any("/Ilot" in g for g in (ga, gb)):
        return "ancrage d'îlot posé sur la falaise"
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
    sous34 = sous_34_au_dessus(b)
    neon = sum(1 for p in b.parts if p.material == "Neon")
    transp = sum(1 for p in b.parts if 0 < p.transparency < 1 and not p.name.startswith("ATTENTE_"))
    print(json.dumps({"pieces": len(b.parts), "neon": neon, "transparentes": transp, "fichier": str(out),
                      "en_attente": attente, "couloir_encombre": gene[:20], "nb_couloir_encombre": len(gene),
                      "trop_bas_au_dessus_du_couloir": bas[:20], "nb_trop_bas": len(bas),
                      "enjambe_sous_34": sous34[:20],
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
