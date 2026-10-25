#!/usr/bin/env python3
"""Plan de la zone 4 « arts martiaux » (campagne terrestre, terres de combat, planète extraterrestre) en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course occupe x ∈ [-45, 45] (90 studs), bordé de trottoirs jusqu'à |x| = 55 ; les premières
  façades sont à |x| = 56 ;
- on entre sous la grande porte de temple en z = 0 et on court vers -Z :
    1. campagne terrestre (0 → -146) : rue de grandes maisons-dômes blanches sur tambour, à bandes colorées, et de
       boutiques à objet géant (ligne de toits à 25-35 studs), palmiers géants, dojo, pagodes et dômes au second
       plan, falaises orange en strates couronnées d'herbe, cascades ;
    2. terres de combat (-146 → -282) : plaine verte trouée de terre ocre, seize mesas aux flancs violets (dont
       trois géantes et deux colonnes près du trottoir), cratères, et un pont de roche naturel qui enjambe le
       couloir (z = -214, appuis à |x| ≥ 54, dessous à 34,5 studs au moins) ;
    3. planète extraterrestre (-282 → -344) : herbe bleu-vert, deux pitons de sable géants en quinconce (la porte
       de la planète), canaux turquoise le long des trottoirs avec passerelles, lac et îlots, arbres « boules »,
       hameau de dômes reliés, grand vaisseau rond sur pattes, bancs de nuages dorés derrière les falaises ;
    4. place des œufs = arène d'arts martiaux en dalles (96 × 80, centre z = -389, dessus à 1,5 stud) qui couvre
       tout le couloir, marches de pierre sur les côtés, poteaux à flamme sur ses coins, temple aux toits orange à
       gauche, grandes tribunes, gong et pagode à droite, bannières, cordons de fanions au-dessus (≥ 34 studs) ;
    5. arche de roche géante (façade z = -436) : le couloir passe dessous (104 de large sous y = 22) et sort vers
       la zone suivante (z = -470) ; deux grands bancs de nuages dorés enveloppent ses pitons.
- des falaises en quatre gradins ferment les côtés (|x| ≥ 135) : orange à bandes (jusqu'à z = -178), puis lavande
  basses (les mesas se découpent sur le ciel), puis sable ocre ; arbres, palmiers et petits pitons sur les crêtes.
- tout ce qui est devant la porte (z > 0 : sol, lions, lanternes, palmiers, falaises) est rangé dans le groupe
  `Approche`, à supprimer quand la zone est raccordée à la zone précédente.

    python zone.py                     # écrit build/parts.json (aucune dépendance à Blender)
    python zone.py --stats             # nombre de pièces par groupe
    python zone.py --chevauchements    # assets posés qui se recoupent (boîtes orientées)
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

from kit import Builder, hexrgb, mix, shade  # noqa: E402
from palette import c  # noqa: E402
from textures import glyph_mask, mask_rects  # noqa: E402

# ---------------------------------------------------------------------------
# Dimensions (studs)
# ---------------------------------------------------------------------------
DEMI_COULOIR = 45        # couloir de course x ∈ [-45, 45] : rien de solide entre y = 0,05 et 12
X_LIBRE_HAUT = 46        # rien du tout au-dessus de |x| < 46 sous y = 30 (la caméra Roblox sauterait)
X_BORD = 55              # fin des trottoirs
X_MAT = 50               # lampadaires, mâts de fanions (milieu du trottoir)
X_MEUBLE = 52.5          # bancs, jardinières, distributeurs (côté façades)
X_FACADE = 56            # avant des premières maisons
X_FALAISE = 135          # début des falaises latérales
X_FOND = 216             # fin du décor (dernier gradin, bords de l'arche)
Z_APPROCHE = 48          # sol devant la porte (groupe « Approche », côté apparition)
Z_PORTE = 0
Z_FIN_VILLAGE = -146     # fin de la campagne terrestre
Z_FIN_ORANGE = -178      # les falaises orange débordent sur la friche (on les voit encore depuis le village)
Z_PONT = -214            # pont de roche au-dessus du couloir
Z_ALIEN = -282           # début de la planète extraterrestre
Z_PLACE = -389           # centre de l'arène (place des œufs)
AX_ARENE = 48            # demi-largeur de l'arène (x) : elle couvre tout le couloir, ses coins sont hors couloir
AZ_ARENE = 40            # demi-longueur de l'arène (z)
H_ARENE = 1.5            # dessus de l'arène (rampes de 5 studs devant et derrière)
L_RAMPE = 5
X_MARCHES = 53           # marches de pierre sur les côtés de l'arène : |x| de 48 à 53, en deux degrés
R_PLACE = AZ_ARENE
Z_ARCHE = -436           # façade de l'arche finale
PROF_ARCHE = 34
Z_SORTIE = Z_ARCHE - PROF_ARCHE   # -470 : le couloir continue vers la zone suivante
PASSAGE = 104            # largeur libre sous l'arche (jambes à |x| ≥ 52)
H_FANIONS = 38.5         # cordons de fanions au-dessus du couloir (creux compris ≥ 34)
Z0_SOL = Z_SORTIE        # -470 : le sol s'arrête à la sortie (la zone suivante prend le relais)

# canaux de la planète (grille de 4 du sol des côtés) : x ∈ [55, 71] le long des trottoirs ; z par côté
X_CANAL = (56, 70)                                  # centres des cases de 4 (57 à 69)
Z_CANAL = {-1: (-340, -300), 1: (-328, -288)}       # étendue de l'eau en z (gauche, droite)
LAC = (106, -314, 26, 22)   # centre x, centre z, demi-axes
# pitons de sable géants qui ouvrent la planète, en quinconce, à la tête des canaux
PITONS_PLANETE = ((-64, -290, 62, 8.0, 0), (66, -336, 68, 8.5, 1))   # x, z, hauteur, demi-côté, variante

VERSION = "0.5"


# ---------------------------------------------------------------------------
# Accès aux assets (avec bloc d'attente si un module manque encore)
# ---------------------------------------------------------------------------

def _asset(module: str, fn: str):
    try:
        return getattr(importlib.import_module(f"assets.{module}"), fn)
    except (ImportError, AttributeError):
        return None


def place(b: Builder, module: str, fn: str, pos, yaw: float = 0.0, group: str | None = None, emprise=(16, 16, 16),
          portique: float | None = None, centre_z: float = 0.0, **params) -> dict:
    """Pose un asset ; si le module n'existe pas encore, pose un bloc translucide de même emprise.

    Chaque pose est notée dans `b.poses` (groupe, fonction, première et dernière pièce) pour le contrôle des
    chevauchements. `portique` (demi-largeur du passage) : le bloc d'attente d'un monument qui enjambe le couloir
    est dessiné en portique (deux piles et un tablier au-dessus de 34 studs). `centre_z` décale le bloc d'attente."""
    f = _asset(module, fn)
    n0 = len(b.parts)
    with b.at(pos, yaw=yaw, group=group):
        nom_groupe = b._groups[-1]
        info = None
        if f is not None:
            try:
                info = f(b, **params) or {}
            except NotImplementedError:
                del b.parts[n0:]
        if info is None:
            w, d, h = emprise
            z0, z1 = centre_z - d / 2, centre_z + d / 2
            kw = dict(transparency=0.5, name=f"ATTENTE_{module}_{fn}")
            if portique:
                for s in (-1, 1):
                    b.box((s * portique, 0, z0), (s * w / 2, h, z1), "#ff4fd8", **kw)
                b.box((-portique, 34, z0), (portique, h, z1), "#ff4fd8", **kw)
            else:
                b.box((-w / 2, 0, z0), (w / 2, h, z1), "#ff4fd8", **kw)
            info = {"emprise": (w, d), "hauteur": h}
    if not hasattr(b, "poses"):
        b.poses = []
    b.poses.append((nom_groupe, fn, n0, len(b.parts)))
    return info


def face_couloir(x: float) -> float:
    """Rotation qui tourne l'avant d'un asset (-Z local) vers le couloir."""
    return -90.0 if x < 0 else 90.0


def _boite_xz(b: Builder, n0: int, n1: int):
    cache = b.__dict__.setdefault("_boites", {})
    if (n0, n1) not in cache:
        lo = np.full(3, np.inf)
        hi = np.full(3, -np.inf)
        for p in b.parts[n0:n1]:
            if p.transparency >= 1:
                continue
            l, h = _aabb(p)
            lo, hi = np.minimum(lo, l), np.maximum(hi, h)
        cache[(n0, n1)] = (lo[0], hi[0], lo[2], hi[2])
    return cache[(n0, n1)]


def libre(b: Builder, x: float, z: float, r: float, marge: float = 0.5) -> bool:
    """Vrai si le carré (x ± r, z ± r) ne touche l'emprise d'aucun asset déjà posé, ni le couloir et ses
    trottoirs (|x| < 45 + r), ni les falaises (|x| > X_FALAISE - 1), ni l'eau."""
    if abs(x) - r < DEMI_COULOIR + 1 or abs(x) + r > X_FALAISE - 1:
        return False
    if any(est_eau(x + dx, z + dz) for dx in (-r, 0, r) for dz in (-r, 0, r)):
        return False
    for (g, fn, n0, n1) in getattr(b, "poses", []):
        if n1 <= n0:
            continue
        x0, x1, z0, z1 = _boite_xz(b, n0, n1)
        if x - r - marge < x1 and x + r + marge > x0 and z - r - marge < z1 and z + r + marge > z0:
            return False
    return True


def dessus_sous(b: Builder, x0: float, x1: float, z0: float, z1: float, n0: int, n1: int,
                exclure=("Pitons", "Vegetation", "Cascade")) -> float:
    """Plus haut dessus des pièces collidables [n0, n1) qui couvrent le rectangle (pour poser un nuage)."""
    y = 0.0
    for p in b.parts[n0:n1]:
        if not p.collide or any(f"/{e}" in p.group for e in exclure):
            continue
        lo, hi = _aabb(p)
        if lo[0] < x1 and hi[0] > x0 and lo[2] < z1 and hi[2] > z0:
            y = max(y, float(hi[1]))
    return y


# ---------------------------------------------------------------------------
# Bruit déterministe (taches de terre, transitions tramées)
# ---------------------------------------------------------------------------

def _hash(i: int, j: int, s: int) -> float:
    n = (i * 374761393 + j * 668265263 + s * 982451653) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def bruit(x: float, z: float, echelle: float, s: int = 0) -> float:
    """Bruit de valeur lissé dans [0, 1]."""
    u, v = x / echelle, z / echelle
    i, j = math.floor(u), math.floor(v)
    fu, fv = u - i, v - j
    fu, fv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
    a, b_ = _hash(i, j, s), _hash(i + 1, j, s)
    c_, d = _hash(i, j + 1, s), _hash(i + 1, j + 1, s)
    return (a * (1 - fu) + b_ * fu) * (1 - fv) + (c_ * (1 - fu) + d * fu) * fv


def section(x: float, z: float) -> str:
    """Paysage au point (x, z) : « terre », « friche » ou « alien », frontières tramées sur ±6 studs (trottoirs,
    côtés). Le couloir, lui, utilise `section_nette` (frontières droites soulignées d'une bande)."""
    zz = z + (bruit(x, z, 6, 11) - 0.5) * 12
    if zz > Z_FIN_VILLAGE:
        return "terre"
    if zz > Z_ALIEN:
        return "friche"
    return "alien"


def section_nette(z: float) -> str:
    if z > Z_FIN_VILLAGE:
        return "terre"
    if z > Z_ALIEN:
        return "friche"
    return "alien"


# ---------------------------------------------------------------------------
# Sol « pixel »
# ---------------------------------------------------------------------------

def sol_pixel(b: Builder, x0: float, x1: float, z0: float, z1: float, cell: float, couleur, y_haut: float = 0.0,
              epaisseur: float = 1.0, studs="top", name: str = "Sol", **kw) -> int:
    """Remplit [x0, x1] × [z0, z1] ; couleur(x, z) → (r, g, b) ou None (case vide), évaluée au centre de chaque
    case ; les cases de même couleur sont fusionnées en rectangles. Les bornes doivent tomber sur la grille."""
    nx, nz = int(round((x1 - x0) / cell)), int(round((z1 - z0) / cell))
    assert abs(nx * cell - (x1 - x0)) < 1e-6 and abs(nz * cell - (z1 - z0)) < 1e-6, (x0, x1, z0, z1, cell)
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


def dans_arene(x: float, z: float) -> bool:
    """Arène, ses rampes et ses marches latérales (dessinées à part, en relief ; marches de |x| = 48 à 53, le
    trottoir reprend à 53 sur sa grille de 2)."""
    return abs(x) < X_MARCHES and abs(z - Z_PLACE) < AZ_ARENE + L_RAMPE


def _q4(v: float, v0: float) -> float:
    """Centre de la case de 4 (grille du sol des côtés partant de v0) qui contient v."""
    return v0 + 4 * math.floor((v - v0) / 4) + 2


def est_eau(x: float, z: float) -> bool:
    """Canaux turquoise le long des trottoirs (jamais dans le couloir) et lac à droite, sur la planète.
    Le test se fait au centre de la case de 4 du sol des côtés : sol et eau tombent toujours d'accord."""
    ax = abs(x)
    if ax < X_BORD or z < Z_ARCHE or z > Z_ALIEN + 6:
        return False
    xq, zq = _q4(ax, X_BORD), _q4(z, Z_ARCHE)
    s = -1 if x < 0 else 1
    zc0, zc1 = Z_CANAL[s]
    if X_CANAL[0] <= xq <= X_CANAL[1] and zc0 < zq < zc1:
        return True
    if x > 0:
        cx, cz, rx, rz = LAC
        if ((xq - cx) / rx) ** 2 + ((zq - cz) / rz) ** 2 < 1:
            return True
        if X_CANAL[1] <= xq <= cx and -320 <= zq <= -308:      # bras entre le canal et le lac
            return True
    return False


def pres_eau(x: float, z: float, d: float = 4) -> bool:
    return any(est_eau(x + dx, z + dz) for dx in (-d, 0, d) for dz in (-d, 0, d))


def sol_couloir(b: Builder) -> None:
    dl, dlf = c("dalle"), c("dalle_fonce")
    pc = c("pave_clair")
    kaki, kakic, ocre = c("kaki"), c("kaki_clair"), c("ocre")
    h, hc = c("herbe"), c("herbe_claire")
    sab, sabc, ha = c("sable"), c("sable_clair"), c("herbe_alien_claire")
    vio, vioc = c("mesa_violet"), c("mesa_violet_clair")

    def couloir(x, z):
        if dans_arene(x, z):
            return None
        ax = abs(x)
        zz = z - Z0_SOL
        if z < Z_ARCHE + 2:                 # passage sous l'arche : grandes dalles violettes claires et moyennes
            if ax > DEMI_COULOIR - 3:
                return vio
            return vioc if math.floor(zz / 9) % 2 else shade(vioc, 0.9)
        # bandes de seuil entre les paysages (frontières nettes dans le couloir)
        if Z_FIN_VILLAGE - 3 <= z < Z_FIN_VILLAGE:
            return c("bordure")
        if Z_ALIEN - 2 <= z < Z_ALIEN + 1:
            return c("sable_fonce")
        sec = section_nette(z)
        if sec == "terre":                  # route du village : grandes dalles crème, frise terre cuite au bord
            if DEMI_COULOIR - 6 <= ax < DEMI_COULOIR - 3:
                return pc
            return dl if (math.floor((x + DEMI_COULOIR) / 15) + math.floor(zz / 12)) % 2 == 0 else dlf
        if sec == "friche":                 # plaine verte, grandes taches ocre ; piste centrale ocre-sable claire
            piste = 20 + 5 * (bruit(x, z, 9, 13) - 0.5)
            if ax < piste:
                n = bruit(x, z, 14, 3)
                return kakic if n > 0.62 else (ocre if n < 0.3 else kaki)
            n = bruit(x, z, 16, 17)
            if n > 0.7:
                return ocre
            if n > 0.6:
                return kaki
            return hc if bruit(x, z, 7, 19) > 0.55 else h
        # planète extraterrestre : allée de sable clair, bords envahis d'herbe bleu-vert
        if ax > DEMI_COULOIR - 6 and bruit(x, z, 4, 7) > 0.5:
            return ha
        return sabc if math.floor(zz / 6) % 4 == 0 else sab

    def trottoir(x, z):
        if dans_arene(x, z):
            return None
        ax = abs(x)
        if z < Z_ARCHE + 2:
            return vio if math.floor(z / 4) % 2 else shade(vio, 0.94)
        if abs(z - Z_PLACE) < AZ_ARENE + 8:     # parvis de l'arène : bandes de dalles
            return c("pierre") if math.floor(z / 4) % 2 else c("pierre_claire")
        sec = section(x, z)
        if sec == "terre":
            if ax < DEMI_COULOIR + 2:
                return c("bordure")
            return pc if math.floor(z / 6) % 3 == 0 else c("pave")
        if sec == "friche":
            return c("gravats") if bruit(x, z, 12, 9) > 0.45 else c("kaki_fonce")
        if ax < DEMI_COULOIR + 2:
            return c("sable_fonce")
        return c("sable_fonce") if math.floor(z / 8) % 3 == 0 else sab

    # zone : de la sortie (-470) à la porte (0) ; la dernière rangée du couloir (-2 → 0) en cases de 1
    with b.group("Sol/Couloir"):
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, Z0_SOL, -2, 3, couloir)
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, -2, 0, 1, couloir)
    with b.group("Sol/Trottoirs"):
        for s in (-1, 1):
            xa, xb = sorted((s * DEMI_COULOIR, s * X_BORD))
            sol_pixel(b, xa, xb, Z0_SOL, 0, 2, trottoir)
    # approche (devant la porte) : groupe à part, supprimable
    with b.group("Approche/Sol"):
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, 0, Z_APPROCHE, 3, couloir)
        for s in (-1, 1):
            xa, xb = sorted((s * DEMI_COULOIR, s * X_BORD))
            sol_pixel(b, xa, xb, 0, Z_APPROCHE, 2, trottoir)


def sol_cotes(b: Builder) -> None:
    """Sol entre les trottoirs et les falaises : herbe vive, plaine trouée de terre, herbe bleu-vert et eau."""
    h, hc, hf = c("herbe"), c("herbe_claire"), c("herbe_fonce")
    kaki, ocre = c("kaki"), c("ocre")
    ha, haf, sab, sabc = c("herbe_alien"), c("herbe_alien_fonce"), c("sable"), c("sable_clair")

    def couleur(x, z):
        ax = abs(x)
        if z < Z_ARCHE:
            return None                       # l'arche couvre tout son sol
        if est_eau(x, z):
            return None
        if ax < 71 and abs(z - Z_PLACE) < AZ_ARENE + 6:       # parvis de l'arène
            return c("pierre") if math.floor(z / 4) % 2 else c("pierre_claire")
        sec = section(x, z)
        if sec == "terre":
            n = bruit(x, z, 20, 21)
            return hc if n > 0.62 else (hf if n < 0.35 else h)
        if sec == "friche":
            n = bruit(x, z, 18, 31)
            if n > 0.72:
                return ocre
            if n > 0.6:
                return kaki
            return hc if n < 0.25 else h
        if pres_eau(x, z):                    # rives de sable clair
            return sabc if bruit(x, z, 5, 43) > 0.55 else sab
        n = bruit(x, z, 22, 41)
        if n > 0.72:
            return sab
        return haf if n < 0.3 else ha

    def eau(x, z):
        if not est_eau(x, z):
            return None
        return c("eau_claire") if (math.floor(z / 2) % 9 == 0 and bruit(x, z, 6, 5) > 0.5) else c("eau")

    z_coupe = Z_ALIEN + 6                     # -276 : cases de 8 au-dessus, de 4 sur la planète
    with b.group("Sol/Cotes"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_FALAISE))
            sol_pixel(b, xa, xb, z_coupe, -4, 8, couleur)
            sol_pixel(b, xa, xb, -4, 0, 4, couleur)
            sol_pixel(b, xa, xb, Z_ARCHE, z_coupe, 4, couleur)
    with b.group("Approche/Sol"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_FALAISE))
            sol_pixel(b, xa, xb, 0, Z_APPROCHE, 8, couleur)
    with b.group("Sol/Eau"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_FALAISE))
            sol_pixel(b, xa, xb, Z_ARCHE, z_coupe, 2, eau, y_haut=-0.4, epaisseur=1.6, studs="none",
                      transparency=0.12, name="Eau")
        # fond sombre sous l'eau (profondeur turquoise foncé), 0,2 sous la dalle d'eau : une dalle par canal, une pour le lac
        for s in (-1, 1):
            xa, xb = sorted((s * (X_CANAL[0] - 1), s * (X_CANAL[1] + 1)))
            b.box((xa, -2.8, Z_CANAL[s][0]), (xb, -2.2, Z_CANAL[s][1]), c("eau_fonce"), name="FondEau")
        cx, cz, rx, rz = LAC
        b.box((X_CANAL[1] + 1, -2.8, cz - rz), (cx + rx, -2.2, cz + rz), c("eau_fonce"), name="FondEau")
    # liseré d'écume le long de la rive côté couloir (bord du trottoir), sans collision
    with b.group("Details/Ecume"):
        for s in (-1, 1):
            xa, xb = sorted((s * (X_BORD - 0.05), s * (X_BORD + 0.6)))
            b.box((xa, -0.55, Z_CANAL[s][0]), (xb, -0.25, Z_CANAL[s][1]), c("ecume"), collide=False, shadow=False,
                  name="Ecume")


def rosace(b: Builder, z: float, r: float = 13.0) -> None:
    """Rosace peinte au milieu de la rue du village (sans collision, < 0,5 au-dessus du sol) : anneaux aux couleurs
    des bandes des dômes et rayons blancs, comme un rond-point rétro-futuriste. Les dessus sont étagés de 0,06
    (0,10 → 0,46) et les rayons à 0,25 : jamais deux dessus visibles au même niveau."""
    anneaux = ((r, "bande_bleue"), (r - 1.5, "blanc_dome"), (r - 3.5, "bande_orange"), (r - 5.5, "dalle"),
               (r - 8, "bande_jaune"), (r - 9.5, "blanc_dome"), (r - 11, "bande_turquoise"))
    with b.group("Details/Rosace"):
        for i, (ra, col) in enumerate(anneaux):
            h = 0.1 + 0.06 * i
            b.cyl((0, h / 2, z), ra, h, c(col), collide=False, shadow=False, name="Rosace")
        for k in range(8):           # rayons blancs entre l'anneau orange et le bord
            a = k * 45 + 22.5
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            b.boxc((ca * (r - 4.5), 0.125, z + sa * (r - 4.5)), (3.0, 0.25, 1.0), c("blanc_dome"), yaw=-a,
                   collide=False, shadow=False, name="Rayon")


def chevrons(b: Builder, zs, couleurs=("bande_orange", "bande_bleue", "bande_jaune", "bande_turquoise")) -> None:
    """Incrustations colorées en chevrons dans la rue du village (pointe vers -Z, sens de la course), sans collision,
    0,2 au-dessus du sol : rappels des bandes des dômes et sensation de vitesse."""
    with b.group("Details/Chevrons"):
        for i, z in enumerate(zs):
            col = c(couleurs[i % len(couleurs)])
            for s in (-1, 1):
                ang = s * 18.0
                L = 36.0
                cx = s * L / 2 * math.cos(math.radians(ang)) * 0.98
                cz = z + L / 2 * math.sin(math.radians(abs(ang)))
                b.boxc((cx, 0.1 + 0.02 * (s > 0), cz), (L, 0.2, 1.5), col, yaw=-ang, collide=False, shadow=False,
                       name="Chevron")


def impact_sol(b: Builder, x: float, z: float, r: float, graine: int = 0) -> None:
    """Trace d'impact peinte sur le couloir (sans collision, < 0,25 au-dessus du sol) : lèvre ocre clair, disque
    de terre battue, petit cœur brûlé et trois fissures courtes et claires (≤ r / 2)."""
    rng = np.random.default_rng(900 + graine)
    with b.group(f"Details/Impact{graine}"):
        b.cyl((x, 0.05, z), r, 0.1, c("kaki_clair"), collide=False, shadow=False, name="Impact")
        b.cyl((x, 0.08, z), r * 0.8, 0.16, c("kaki_fonce"), collide=False, shadow=False, name="Impact")
        b.cyl((x, 0.11, z), r * 0.3, 0.22, mix(c("brule"), c("kaki_fonce"), 0.4), collide=False, shadow=False,
              name="Impact")
        for k in range(3):
            a = k * 120 + float(rng.uniform(-25, 25))
            L = r * float(rng.uniform(0.3, 0.5))
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            cx, cz = x + ca * (r * 0.3 + L / 2), z + sa * (r * 0.3 + L / 2)
            b.boxc((cx, 0.095, cz), (L, 0.19, 0.6), mix(c("fissure"), c("kaki_fonce"), 0.5), yaw=-a, collide=False,
                   shadow=False, name="Fissure")


# ---------------------------------------------------------------------------
# Arène d'arts martiaux (place des œufs)
# ---------------------------------------------------------------------------

def arene(b: Builder) -> None:
    """Arène en dalles de pierre (96 × 80), en relief (dessus à 1,5 stud), qui couvre tout le couloir : rampes
    devant et derrière, deux degrés de marches sur les côtés (|x| 48 → 53), grand 武 rouge dans un cercle doré,
    liseré blanc puis joint sombre sur le bord, poteaux à flamme sur piédestal à ses quatre coins (hors couloir)."""
    n_gl = 26
    glyphe = glyph_mask("武", n_gl, font="brush", bold=0.6)
    a_, af, j = c("arene"), c("arene_fonce"), c("arene_joint")
    pc, rouge, orr = c("pierre_claire"), c("laque_rouge"), c("or")

    def motif(x, z):
        dz = z - Z_PLACE
        if abs(x) > AX_ARENE - 1 or abs(dz) > AZ_ARENE - 1:
            return pc                                       # liseré blanc du bord
        if abs(x) > AX_ARENE - 2 or abs(dz) > AZ_ARENE - 2:
            return j                                        # joint sombre
        d = math.hypot(x, dz)
        if d < 17:
            gi, gj = int(math.floor(x + n_gl / 2)), int(math.floor(dz + n_gl / 2))
            if 0 <= gi < n_gl and 0 <= gj < n_gl and glyphe[gj, gi]:
                return rouge
            return pc
        if d < 19:
            return orr
        return a_ if (math.floor(x / 8) + math.floor(dz / 8)) % 2 == 0 else af

    with b.group("Sol/Arene"):
        sol_pixel(b, -AX_ARENE, AX_ARENE, Z_PLACE - AZ_ARENE, Z_PLACE + AZ_ARENE, 1, motif, y_haut=H_ARENE,
                  epaisseur=2.0, name="Arene")
        # rampes (pente douce dans le couloir) : la pente descend vers l'extérieur de l'arène
        b.wedge((-AX_ARENE, 0, Z_PLACE + AZ_ARENE), (AX_ARENE, H_ARENE, Z_PLACE + AZ_ARENE + L_RAMPE), af, down="+z",
                studs="top", name="Rampe")
        b.wedge((-AX_ARENE, 0, Z_PLACE - AZ_ARENE - L_RAMPE), (AX_ARENE, H_ARENE, Z_PLACE - AZ_ARENE), af, down="-z",
                studs="top", name="Rampe")
        # sol sous les rampes (le couloir est laissé vide à cet endroit)
        for z0, z1 in ((Z_PLACE + AZ_ARENE, Z_PLACE + AZ_ARENE + L_RAMPE),
                       (Z_PLACE - AZ_ARENE - L_RAMPE, Z_PLACE - AZ_ARENE)):
            b.box((-AX_ARENE, -1, z0), (AX_ARENE, 0, z1), c("sable"), studs="none", name="SousRampe")
        # deux degrés de marches sur les côtés (hors couloir) : 48 → 50,5 (dessus à 1) puis 50,5 → 53 (0,5)
        for s in (-1, 1):
            for (xa_, xb_, hm, col) in ((AX_ARENE, 50.5, 1.0, "pierre"), (50.5, X_MARCHES, 0.5, "pierre_fonce")):
                xa, xb = sorted((s * xa_, s * xb_))
                b.box((xa, -1, Z_PLACE - AZ_ARENE - L_RAMPE), (xb, hm, Z_PLACE + AZ_ARENE + L_RAMPE), c(col),
                      studs="top", name="Marche")
    # poteaux à flamme sur piédestal aux coins de l'arène (|x| ≥ 46,1 : hors couloir et hors du ciel du couloir)
    for i, (sx, sz) in enumerate(((-1, 1), (1, 1), (-1, -1), (1, -1))):
        place(b, "mobilier", "poteau_arene", (sx * 47.8, 0, Z_PLACE + sz * (AZ_ARENE - 1.8)),
              group=f"Place/Poteau{i}", variant=2 if i % 3 == 0 else 0, hauteur=9.0, socle=H_ARENE + 0.1,
              emprise=(3.4, 3.4, 15))


def place_selection(b: Builder) -> None:
    """Autour de l'arène : temple d'arts martiaux à gauche, grandes tribunes, gong et pagode à droite, fanions,
    bannières."""
    place(b, "temple", "temple_tournoi", (-(X_FACADE + 17), 0, Z_PLACE), yaw=-90, group="Place/Temple",
          emprise=(60, 34, 38), largeur=60, profondeur=34)
    for i, dz in enumerate((19, -19)):
        place(b, "temple", "tribune", (X_FACADE + 10, 0, Z_PLACE + dz), yaw=90, group=f"Place/Tribune{i}",
              emprise=(28, 20, 20), variant=i, longueur=28, rangs=8)
    place(b, "mobilier", "gong", (X_FACADE + 1.8, 0, Z_PLACE), yaw=90, group="Place/Gong", emprise=(9, 3, 8))
    place(b, "temple", "pagode", (X_FACADE + 26, 0, Z_PLACE), yaw=90, group="Place/Pagode", variant=0, etages=4,
          emprise=(12, 12, 40))
    # bannières sur le bord du trottoir, entre les marches de l'arène et le temple / les tribunes
    textes = ("武", "気", "修行", "武道")
    for s in (-1, 1):
        for i, dz in enumerate((-30, -10, 10, 30)):
            if s > 0 and abs(dz) == 10:
                continue                       # le gong occupe le milieu du côté droit
            x = s * 54.2
            place(b, "mobilier", "banniere", (x, 0, Z_PLACE + dz), yaw=face_couloir(x),
                  group=f"Place/Banniere{'GD'[s > 0]}{i}", texte=textes[(i + (s > 0)) % 4], variant=(i + (s > 0)) % 4,
                  hauteur=11, emprise=(3, 2, 11))
    # cordons de fanions au-dessus de l'arène : mâts rouges au bord du trottoir, cordons à ≥ 34 studs
    fan = _asset("mobilier", "guirlande_fanions")
    for i, dz in enumerate((22, -22)):
        z = Z_PLACE + dz
        with b.group(f"Place/Fanions{i}"):
            for s in (-1, 1):
                with b.at((s * 54.0, 0, z)):
                    b.box((-0.9, 0, -0.9), (0.9, 1.2, 0.9), c("pierre_fonce"), studs="top", name="Pied")
                    b.box((-0.45, 1.2, -0.45), (0.45, H_FANIONS + 2, 0.45), c("laque_rouge"), name="Mat")
                    b.box((-0.7, H_FANIONS + 2, -0.7), (0.7, H_FANIONS + 2.6, 0.7), c("or"), name="Chapeau")
            if fan:
                fan(b, (-53.5, H_FANIONS, z), (53.5, H_FANIONS, z), n=15, creux=2.5, variant=i)


# ---------------------------------------------------------------------------
# Falaises latérales (orange à bandes, puis lavande basses, puis sable ocre)
# ---------------------------------------------------------------------------

STYLES_FALAISE = {
    # tons des gradins, strate, herbe du sommet, hauteur de base, surcroît du 2e et du 3e gradin
    "terre": (("falaise_orange", "falaise_orange_claire", "falaise_orange_fonce"), "falaise_brune", "herbe", (14, 20), (10, 16), (22, 32)),
    # terres de combat : falaises basses lavande pâle (rappel du ciel rose-lavande) : les mesas violettes se
    # découpent dessus et sur le ciel
    "friche": (("falaise_lavande", "falaise_lavande_claire", "falaise_lavande_rose"), "mesa_violet_clair", "herbe", (8, 14), (6, 10), (10, 18)),
    "alien": (("falaise_sable", "falaise_sable_claire", "falaise_sable_fonce"), "falaise_sable_fonce", "herbe_alien", (5, 9), (6, 10), (10, 16)),
}
# bandes horizontales des falaises orange (hauteurs fixes, 2 studs, en saillie de 0,3) : lisibles de loin
BANDES_ORANGE = tuple((4.5 + 7 * i, ("falaise_orange_claire", "falaise_brune")[i % 2]) for i in range(9))
# bancs de nuages dorés posés sur le 2e gradin des falaises de sable (x centre, z centre, longueur le long de z,
# profondeur le long de x, hauteur, variante) ; le 2e gradin est aplani sous chaque banc (ils ne flottent pas)
NUAGES = ((-163, -318, 56, 22, 38, 0), (163, -352, 96, 22, 42, 1), (-163, -396, 76, 22, 36, 2),
          (163, -418, 34, 22, 30, 0))
H_GRADIN_NUAGE = 14.0
GRADINS = ((X_FALAISE, X_FALAISE + 16), (X_FALAISE + 16, X_FALAISE + 40), (X_FALAISE + 40, X_FALAISE + 61),
           (X_FALAISE + 61, X_FOND))
CASCADES_Z = {(-1, -56), (-1, -136), (1, -88), (1, -120)}   # (côté, z du centre de la tranche) : cascades du village
HAUT_FALAISE: dict = {}                          # (côté, tranche) → (z centre, (h1, h2, h3, h4), style)


def _sous_nuage(s: int, zc: float) -> bool:
    """La tranche de falaise (centre zc, 16 de long) touche-t-elle un banc de nuages de ce côté ?"""
    return any((xn < 0) == (s < 0) and abs(zc - zn) < ln / 2 + 8 for (xn, zn, ln, dn, hn, vn) in NUAGES)


def bordures(b: Builder) -> None:
    """Falaises en quatre gradins (tranches de 16 studs) qui ferment la vallée ; dessus en herbe débordante.
    Falaises orange : bandes claires et brunes à hauteurs fixes (une pièce par bande et par suite de tranches) ;
    lavande et sable : une strate par gradin. Le dernier gradin (|x| ≥ 196) monte encore de 5 à 12 studs.
    Les tranches devant la porte (z > 0) vont dans le groupe `Approche`."""
    rng = np.random.default_rng(5)
    rng4 = np.random.default_rng(6)
    bornes = [Z_APPROCHE, 32.0, 16.0, 0.0]
    z = 0.0
    while z > Z_ARCHE + 0.01:
        z = max(Z_ARCHE, z - 16)
        bornes.append(z)
    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        bandes_tr = []                                   # tranches orange : (z0, z1, hauteurs des gradins)
        for k, (za, zb) in enumerate(zip(bornes[:-1], bornes[1:])):
            l = za - zb
            zc = (za + zb) / 2
            style = "terre" if zc > Z_FIN_ORANGE else ("friche" if zc > Z_ALIEN else "alien")
            tons, strate, herbe, base, plus2, plus3 = STYLES_FALAISE[style]
            h1 = rng.uniform(*base) + 3 * math.sin(k * 0.9)
            if (s, zc) in CASCADES_Z:
                h1 = 26
            if style == "friche" and k % 3 == 1:
                h1 *= 0.75                              # encoche : on voit les mesas du fond
            h2 = h1 + rng.uniform(*plus2)
            h3 = h2 + rng.uniform(*plus3)
            h4 = h3 + rng4.uniform(5, 12)
            if style == "alien" and _sous_nuage(s, zc):
                h1 = min(h1, H_GRADIN_NUAGE - 4)
                h2 = H_GRADIN_NUAGE                     # le banc de nuages repose à plat sur le 2e gradin
                h3 = max(h3, h2 + 8)
                h4 = max(h4, h3 + 5)
            gradins = tuple((xa_, xb_, float(round(hg))) for (xa_, xb_), hg in zip(GRADINS, (h1, h2, h3, h4)))
            HAUT_FALAISE[(s, k)] = (zc, tuple(g[2] for g in gradins), style)
            racine = "Approche/Bordures" if zc > 0 else "Bordures"
            with b.group(f"{racine}/{cote}"):
                h_avant = 0.0                           # dessus du gradin de devant (la strate doit le dépasser)
                for gi, (xa_, xb_, hg) in enumerate(gradins):
                    xa, xb = sorted((s * xa_, s * xb_))
                    b.box((xa, 0, zb), (xb, hg - 1.2, za), c(tons[(k + gi) % 3]), studs="top", name="Gradin")
                    # chapeau d'herbe qui déborde de 0,6 côté vallée
                    ha, hb = sorted((s * (xa_ - 0.6), s * xb_))
                    b.box((ha, hg - 1.2, zb), (hb, hg, za), c(herbe), studs="top", name="Herbe")
                    # strate claire sur la face côté vallée (les falaises orange ont leurs bandes à part)
                    if style != "terre" and hg > 8:
                        ys = round(hg * float(rng.uniform(0.35, 0.6)))
                        ys = max(ys, h_avant + 1)
                        if ys + 1.2 < hg - 2.5:
                            sa, sb = sorted((s * (xa_ - 0.3), s * xa_))
                            b.box((sa, ys, zb + 0.5), (sb, ys + 1.2, za - 0.5), c(strate), collide=False, name="Strate")
                    # coulures d'herbe sous le chapeau
                    if gi < 2 and (k + gi) % 2 == 0:
                        zq = za - l * float(rng.uniform(0.2, 0.7))
                        lg = float(rng.uniform(1.5, 3.5))
                        ca, cb = sorted((s * (xa_ - 0.6), s * (xa_ - 0.1)))
                        b.box((ca, hg - 1.2 - lg, zq - 1.2), (cb, hg - 1.2, zq + 1.2), c(herbe), collide=False, name="Coulure")
                    h_avant = hg
            if style == "terre":
                bandes_tr.append((zb, za, [g[2] for g in gradins], zc > 0))
        # bandes des falaises orange : une pièce par bande, par gradin et par suite de tranches où elle passe
        for gi, (xa_, xb_) in enumerate(GRADINS):
            for (yb, ton) in BANDES_ORANGE:
                suite = None
                for (zb, za, hs, appr) in sorted(bandes_tr, key=lambda t: t[0]):
                    h_dev = hs[gi - 1] if gi > 0 else 0.0
                    ok = hs[gi] - 1.2 - 1.0 > yb + 2.0 and yb > h_dev + 0.5
                    if ok and suite is not None and abs(suite[1] - zb) < 1e-6 and suite[2] == appr:
                        suite[1] = za
                    else:
                        if suite is not None:
                            _bande_falaise(b, s, xa_, suite, yb, ton)
                        suite = [zb, za, appr] if ok else None
                if suite is not None:
                    _bande_falaise(b, s, xa_, suite, yb, ton)


def _bande_falaise(b: Builder, s: int, xa_: float, suite, yb: float, ton: str) -> None:
    zb, za, appr = suite
    racine = "Approche/Bordures" if appr else "Bordures"
    with b.group(f"{racine}/{'Gauche' if s < 0 else 'Droite'}"):
        sa, sb = sorted((s * (xa_ - 0.3), s * (xa_ + 0.1)))
        b.box((sa, yb, zb + 0.3), (sb, yb + 2.0, za - 0.3), c(ton), collide=False, name="Bande")


def sommets_falaises(b: Builder) -> None:
    """Silhouettes sur le haut des falaises (vues depuis le couloir et d'en haut) : arbres ronds et palmiers
    sur les falaises orange, buissons et arbres sur la friche, arbres boules sur la planète."""
    for (s, k), (zc, (h1, h2, h3, h4), style) in sorted(HAUT_FALAISE.items()):
        if (s, zc) in CASCADES_Z or abs(zc - Z_ARCHE) < 10 or zc > 0:
            continue
        g = f"Bordures/Sommets{'GD'[s > 0]}"
        j = (k + (s > 0)) % 4
        if style == "terre":
            if j == 0:
                place(b, "nature", "arbre_rond", (s * 143, h1, zc), group=f"{g}/Arbre{k}", variant=k % 4,
                      hauteur=10 + k % 3, emprise=(10, 10, 12))
            elif j == 2:
                place(b, "nature", "palmier", (s * 163, h2, zc - 2), yaw=k * 47, group=f"{g}/Palmier{k}", variant=k % 4,
                      hauteur=14 + k % 3, emprise=(12, 12, 14))
            elif j == 3:
                place(b, "nature", "buisson", (s * 141, h1, zc + 3), group=f"{g}/Buisson{k}", variant=k % 4,
                      teinte="vert", emprise=(4, 4, 3))
        elif style == "friche":
            if j in (0, 2):
                place(b, "nature", "buisson", (s * 142, h1, zc - 3), group=f"{g}/Buisson{k}", variant=k % 4,
                      teinte="vert", emprise=(4, 4, 3))
            if j == 1:
                place(b, "nature", "arbre_rond", (s * 162, h2, zc), group=f"{g}/Arbre{k}", variant=(k + 1) % 4,
                      hauteur=9 + k % 3, emprise=(10, 10, 12))
        else:
            if _sous_nuage(s, zc):
                continue                                 # le 2e gradin porte un banc de nuages
            if j in (0, 2):
                place(b, "nature", "arbre_boule", (s * (143 if j == 0 else 163), h1 if j == 0 else h2, zc),
                      group=f"{g}/ArbreBoule{k}", variant=k % 4, hauteur=16 + 4 * (k % 3), emprise=(8, 8, 20))
            elif j == 3:
                place(b, "nature", "buisson", (s * 141, h1, zc), group=f"{g}/Buisson{k}", variant=k % 4,
                      teinte="alien", emprise=(4, 4, 3))
        # ligne de crête : un arbre ou un piton sur le haut gradin, une tranche sur trois
        if (k + (s > 0)) % 3 == 1 and abs(zc - Z_ARCHE) > 24:
            if style == "terre":
                place(b, "nature", "arbre_rond", (s * 182, h3, zc), group=f"{g}/Crete{k}", variant=(k + 2) % 4,
                      hauteur=12 + k % 3, emprise=(10, 10, 14))
            elif style == "friche":
                place(b, "nature", "arbre_rond", (s * 184, h3, zc), group=f"{g}/Crete{k}", variant=(k + 1) % 4,
                      hauteur=10 + k % 3, emprise=(10, 10, 14))
            else:
                place(b, "nature", "arbre_boule", (s * 186, h3, zc), group=f"{g}/Crete{k}", variant=(k + 1) % 4,
                      hauteur=20 + 4 * (k % 2), emprise=(8, 8, 24))


def h_falaise(s: int, z: float, x: float) -> float:
    """Hauteur du gradin de falaise sous (x, z) (0 devant les falaises)."""
    ax = abs(x)
    if ax < X_FALAISE:
        return 0.0
    for (sk, k), (zc, hk, style) in HAUT_FALAISE.items():
        if sk == s and abs(zc - z) <= 8:
            for (xa_, xb_), hg in zip(GRADINS, hk):
                if xa_ <= ax < xb_:
                    return float(hg)
    return 0.0


# ---------------------------------------------------------------------------
# Campagne terrestre : porte, village de grands dômes, dojo, pagodes, cascades
# ---------------------------------------------------------------------------

# (fonction, paramètres, largeur le long de z, profondeur le long de x, centre z)
# maison_dome : emprise (2r + 4 ; v2 : 2r + 12) × (2r + 6) ; boutique_dome : 16 × échelle
RANGEE_GAUCHE = [
    ("maison_dome", {"variant": 0, "rayon": 15, "tambour": 6}, 34, 36, -27),
    ("boutique_dome", {"variant": 0, "echelle": 1.5}, 24, 24, -58),
    ("maison_dome", {"variant": 17, "rayon": 14, "tambour": 4}, 32, 34, -89),     # deux dômes empilés (violet)
    ("maison_dome", {"variant": 3, "rayon": 15, "tambour": 6}, 34, 36, -126),     # maison haute (jaune)
]
RANGEE_DROITE = [
    ("maison_dome", {"variant": 1, "rayon": 14, "tambour": 6}, 32, 34, -24),      # aile basse (bleu)
    ("maison_dome", {"variant": 4, "rayon": 16, "tambour": 5}, 36, 38, -63),      # terrasse de toit (turquoise)
    ("boutique_dome", {"variant": 3, "echelle": 1.5}, 24, 24, -95),
    ("maison_dome", {"variant": 2, "rayon": 14, "tambour": 5}, 40, 34, -129),     # deux dômes reliés (rouge)
]


def rangee(b: Builder, s: int, plan) -> list:
    """Aligne une rangée de bâtiments du village le long du couloir (avant tourné vers le couloir)."""
    cote = "Gauche" if s < 0 else "Droite"
    poses = []
    for i, (fn, params, larg, prof, zc) in enumerate(plan):
        x = s * (X_FACADE + prof / 2)
        info = place(b, "batiments", fn, (x, 0, zc), yaw=face_couloir(x), group=f"Village/{cote}/{i:02d}_{fn}",
                     emprise=(larg, prof, 28), **params)
        poses.append((x, zc, larg, prof, info))
    return poses


def porte_et_abords(b: Builder) -> None:
    place(b, "temple", "porte_temple", (0, 0, Z_PORTE), group="Monuments/Porte", emprise=(2 * X_FALAISE, 16, 55),
          portique=46, ouverture=92, hauteur=55, mur=X_FALAISE - 0.1)
    # devant la porte (z > 0) : groupe « Approche »
    for s in (-1, 1):
        g = "GD"[s > 0]
        place(b, "temple", "statue_gardien", (s * 59, 0, Z_PORTE + 13), yaw=180, group=f"Approche/Gardien{g}",
              variant=int(s > 0), emprise=(7, 9, 12))
        place(b, "mobilier", "lanterne_chinoise", (s * 50, 0, Z_PORTE + 26), group=f"Approche/Lanterne{g}",
              variant=1, emprise=(2, 7, 9))
        for i, (dx, dz, h) in enumerate(((70, 26, 18), (94, 33, 15), (118, 18, 20), (124, 38, 14))):
            place(b, "nature", "palmier", (s * dx, 0, Z_PORTE + dz), yaw=(i * 70 + (s > 0) * 35) % 360,
                  group=f"Approche/Palmier{g}{i}", variant=(i + (s > 0)) % 4, hauteur=h, emprise=(12, 12, 16))
        for i, (dx, dz) in enumerate(((82, 40), (106, 30))):
            place(b, "nature", "arbre_rond", (s * dx, 0, Z_PORTE + dz), group=f"Approche/Arbre{g}{i}",
                  variant=(i + 2 * (s > 0)) % 4, hauteur=12 + 2 * i, emprise=(10, 10, 14))
        for i, (dx, dz) in enumerate(((62, 36), (78, 16), (100, 14), (128, 8))):
            place(b, "nature", "buisson", (s * dx, 0, Z_PORTE + dz), yaw=i * 40, group=f"Approche/Buisson{g}{i}",
                  variant=i % 4, teinte="vert", emprise=(4, 4, 3))


def village(b: Builder):
    poses_g = rangee(b, -1, RANGEE_GAUCHE)
    poses_d = rangee(b, 1, RANGEE_DROITE)
    # deuxième plan à gauche : dojo et terrain d'entraînement, pagode, grands dômes du fond
    place(b, "temple", "dojo", (-113, 0, -52), yaw=-90, group="Village/Dojo", emprise=(24, 18, 16), largeur=24,
          profondeur=18, variant=0)
    entr = ((-97.5, -44, "mannequin_bois", {}), (-97.5, -51, "mannequin_bois", {"variant": 1}),
            (-97.5, -59, "jarres", {"variant": 2}), (-98, -37, "banniere", {"texte": "修行", "variant": 1}),
            (-98, -66, "panneau", {"texte": "道場", "variant": 0}))
    for i, (x, z, fn, kw) in enumerate(entr):
        place(b, "mobilier", fn, (x, 0, z), yaw=-90, group=f"Village/Entrainement{i}", emprise=(3, 3, 6), **kw)
    place(b, "temple", "pagode", (-110, 0, -100), group="Village/PagodeG", variant=1, emprise=(12, 12, 36), etages=4)
    place(b, "temple", "pagode", (106, 0, -40), group="Village/PagodeD", variant=0, emprise=(12, 12, 40), etages=4)
    place(b, "temple", "pagode", (112, 0, -104), group="Village/PagodeD2", variant=2, emprise=(12, 12, 32), etages=3)
    for i, (x, z, r, t, v) in enumerate(((-110, -134, 11, 3, 9), (-114, -17, 11, 2, 6), (112, -66, 11, 3, 8),
                                         (112, -132, 10, 2, 5))):
        place(b, "batiments", "maison_dome", (x, 0, z), yaw=face_couloir(x), group=f"Village/Arriere{i}", variant=v,
              rayon=r, tambour=t, emprise=(2 * r + 4, 2 * r + 6, r + t + 6))
    for i, (x, z, h) in enumerate(((-128, -78, 34), (126, -18, 42), (-127, -114, 28))):
        place(b, "nature", "pic_rocheux", (x, 0, z), group=f"Village/Pic{i}", variant=i, hauteur=h, teinte="orange",
              emprise=(10, 10, h))
    # cascades au pied des falaises orange
    for (s, k), (zc, hs, style) in sorted(HAUT_FALAISE.items()):
        if (s, zc) in CASCADES_Z:
            x = s * X_FALAISE
            place(b, "nature", "cascade", (x, 0, zc), yaw=face_couloir(x), group=f"Village/Cascade{'GD'[s > 0]}{k}",
                  variant=k % 3, hauteur=hs[0], largeur=8, emprise=(12, 10, hs[0]))
    # grands palmiers entre les maisons de la rue (couronne ≤ 10,5 : rien au-dessus du couloir sous 30)
    palmiers_rue = ((-58.5, -45), (-58.5, -71.5), (-57.5, -107.5), (-58.5, -148), (58.5, -42.5), (57.5, -82.5),
                    (58.5, -108), (58.5, -151))
    for i, (x, z) in enumerate(palmiers_rue):
        place(b, "nature", "palmier", (x, 0, z), yaw=(i * 53) % 360, group=f"Village/Palmier{i:02d}", variant=i % 4,
              hauteur=22 + (i % 4) * 2, rayon_max=10.5, emprise=(16, 16, 28))
    # voitures volantes garées le long des trottoirs (hors couloir)
    for i, (x, z, yaw, v) in enumerate(((-51, -64, 0, 0), (51.5, -100, 180, 1), (-51.5, -117, 180, 2))):
        place(b, "batiments", "voiture_volante", (x, 0, z), yaw=yaw, group=f"Village/Voiture{i}", variant=v,
              emprise=(5, 9, 4))
    # second plan : palmiers, arbres ronds, voitures dans les jardins, posés là où il reste de la place
    rng = np.random.default_rng(31)
    cands = [(-100, -6), (-96, -24), (100, -12), (96, -98), (-98, -118), (-96, -82), (100, -24), (-124, -36),
             (124, -94), (-104, -150), (98, -146), (126, -50), (-126, -96), (-98, -140), (96, -60), (126, -122),
             (-126, -60), (100, -122)]
    k = 0
    for i, (x, z) in enumerate(cands):
        if not libre(b, x, z, 5.0, marge=0.5):
            continue
        if k % 3 == 2:
            place(b, "nature", "arbre_rond", (x, 0, z), group=f"Village/Arbre{k}", variant=k % 4,
                  hauteur=12 + (k % 3) * 2, emprise=(10, 10, 14))
        else:
            place(b, "nature", "palmier", (x, 0, z), yaw=float(rng.uniform(0, 360)), group=f"Village/PalmierFond{k}",
                  variant=k % 4, hauteur=18 + (k % 4) * 2, emprise=(12, 12, 22))
        k += 1
    for i, (x, z) in enumerate(((-96, -30), (98, -116), (-100, -146))):
        if libre(b, x, z, 4.6):
            place(b, "batiments", "voiture_volante", (x, 0, z), yaw=float(rng.uniform(0, 360)),
                  group=f"Village/VoitureJardin{i}", variant=(i + 3) % 4, emprise=(5, 9, 4))
    return poses_g, poses_d


Z_LAMPES = (-10, -40, -70, -100, -130)
Z_FANIONS_RUE = (-48, -108, -138)


def details_village(b: Builder, poses_g, poses_d) -> None:
    """Lampadaires, bancs, terrasses, distributeurs, jardinières sur les trottoirs (jamais dans le couloir).

    Lampadaires et mâts au milieu du trottoir (|x| = 50), mobilier contre les façades (|x| = 52,5) : seuls les
    parasols (8 × 8) et les voitures garées (|x| ≈ 51) ont besoin d'un écart en z avec eux."""
    mats = {s: [] for s in (-1, 1)}          # lampadaires et mâts de fanions (x = ±50)
    gros = {-1: [-64, -117], 1: [-100]}       # voitures garées le long du trottoir
    meubles = {s: [] for s in (-1, 1)}
    for s in (-1, 1):
        for i, z in enumerate(Z_LAMPES):
            zz = z - (15 if s > 0 else 0)
            x = s * X_MAT
            place(b, "mobilier", "lampadaire_rond", (x, 0, zz), yaw=face_couloir(x), group=f"Details/Lampadaire{'GD'[s > 0]}{i}",
                  variant=0 if i % 2 == 0 else 2, emprise=(2, 4, 11))
            mats[s].append(zz)
        mats[s] += list(Z_FANIONS_RUE)
    props = [("banc", {"variant": 0}), ("jardiniere", {"variant": 0}), ("distributeur", {"variant": 0}),
             ("parasol_table", {"variant": 1}), ("jardiniere", {"variant": 1}), ("banc", {"variant": 3}),
             ("caisses", {"variant": 1}), ("distributeur", {"variant": 1}), ("parasol_table", {"variant": 0}),
             ("jardiniere", {"variant": 2})]

    def ecart(s, z, fn):
        d_mat = 6.5 if fn == "parasol_table" else 2.5
        d_gros = 9.5 if fn == "parasol_table" else 7.5
        return (all(abs(z - zo) >= d_mat for zo in mats[s]) and all(abs(z - zo) >= d_gros for zo in gros[s])
                and all(abs(z - zo) >= (8.5 if fn == "parasol_table" or f2 == "parasol_table" else 5.5)
                        for zo, f2 in meubles[s]))

    k = 0
    for s, poses in ((-1, poses_g), (1, poses_d)):
        for (x, zc, larg, prof, info) in poses:
            for dz in (-larg / 2 + 3, larg / 2 - 3):
                fn, kw = props[k % len(props)]
                zp = zc + dz
                for _ in range(5):
                    if ecart(s, zp, fn):
                        break
                    zp += 2 if dz < 0 else -2
                else:
                    k += 1
                    continue
                meubles[s].append((zp, fn))
                xp = s * (X_BORD - 4.2 if fn == "parasol_table" else X_MEUBLE)
                place(b, "mobilier", fn, (xp, 0, zp), yaw=face_couloir(xp), group=f"Details/{fn}{k}", emprise=(4, 3, 5), **kw)
                k += 1
    # cordons de fanions au-dessus de la rue (≥ 34 studs), mâts blancs « tech »
    fan = _asset("mobilier", "guirlande_fanions")
    for i, z in enumerate(Z_FANIONS_RUE):
        with b.group(f"Details/Fanions{i}"):
            for s in (-1, 1):
                with b.at((s * X_MAT, 0, z)):
                    b.box((-0.9, 0, -0.9), (0.9, 1.0, 0.9), c("gris_tech"), studs="top", name="Pied")
                    b.cyl((0, 1.0 + (H_FANIONS + 1) / 2, 0), 0.4, H_FANIONS + 1, c("blanc_dome"), name="Mat")
                    b.cyl((0, H_FANIONS + 2.3, 0), 0.6, 0.6, c(("bande_orange", "bande_bleue", "bande_jaune")[i % 3]),
                          name="Chapeau")
            if fan:
                fan(b, (-X_MAT + 0.4, H_FANIONS, z), (X_MAT - 0.4, H_FANIONS, z), n=15, creux=2.5, variant=i + 1)


# ---------------------------------------------------------------------------
# Terres de combat : mesas violettes, pont de roche, cratères
# ---------------------------------------------------------------------------

# (x, z, largeur le long du couloir (z), profondeur vers l'extérieur (x), hauteur, variante)
MESAS = (
    # près du couloir (22 à 30)
    (-70, -168, 28, 24, 26, 0), (72, -172, 30, 26, 30, 1), (-74, -262, 30, 26, 28, 2), (70, -262, 28, 24, 24, 3),
    # deux buttes-colonnes fines près du trottoir, en quinconce avant et après le pont
    (-62, -190, 14, 14, 50, 0), (63, -238, 14, 14, 44, 1),
    # second plan (40 à 52)
    (-106, -180, 34, 30, 46, 1), (108, -196, 32, 28, 52, 0), (-104, -254, 30, 28, 42, 3), (104, -264, 30, 26, 40, 2),
    # géantes (60 à 72), qui se découpent sur le ciel au-dessus des falaises lavande
    (-116, -218, 40, 32, 72, 2), (120, -226, 36, 28, 64, 1), (118, -160, 30, 28, 60, 3),
    # petites, au fond et à l'entrée de la plaine
    (-92, -154, 20, 18, 28, 0), (-128, -186, 16, 12, 34, 3), (129, -196, 16, 10, 36, 0),
)


def friche(b: Builder) -> None:
    place(b, "arche", "pont_rocheux", (0, 0, Z_PONT), group="Monuments/Pont", emprise=(172, 28, 60), portique=54,
          portee=108, hauteur=36, epaisseur=17, largeur_pile=30, variant=0)
    for i, (x, z, w, d, h, v) in enumerate(MESAS):
        place(b, "nature", "mesa", (x, 0, z), yaw=face_couloir(x), group=f"Friche/Mesa{i:02d}", variant=v,
              largeur=w, profondeur=d, hauteur=h, emprise=(w, d, h))
    for i, (x, z, r) in enumerate(((-70, -238, 6), (86, -238, 5), (-84, -194, 5))):
        place(b, "nature", "cratere", (x, 0, z), group=f"Friche/Cratere{i}", variant=i, rayon=r, emprise=(2 * r + 4, 2 * r + 4, 3))
    rng = np.random.default_rng(17)
    k = 0
    for i in range(80):
        if k >= 26:
            break
        s = -1 if i % 2 else 1
        pres = i % 3 == 0
        taille = float(rng.uniform(0.9, 1.3)) if pres else float(rng.uniform(0.8, 1.8))
        # près du couloir : gros cailloux sur le bord du trottoir (|x| ≥ 45 + 2,9 × taille)
        x = s * (46 + 2.9 * taille + float(rng.uniform(0.3, 4))) if pres else s * float(rng.uniform(58, 128))
        z = float(rng.uniform(-280, -148))
        if not libre(b, x, z, 2.0 * taille, marge=1.0):
            continue
        place(b, "nature", "rocher", (x, 0, z), yaw=float(rng.uniform(0, 360)), group=f"Friche/Rocher{k:02d}",
              variant=i % 4, taille=taille, teinte="violet" if i % 3 else "gris", emprise=(4, 4, 3))
        k += 1
    k = 0
    for i in range(60):
        if k >= 18:
            break
        s = -1 if i % 2 else 1
        x, z = s * float(rng.uniform(52, 126)), float(rng.uniform(-280, -150))
        if not libre(b, x, z, 2.2):
            continue
        place(b, "nature", "buisson", (x, 0, z), yaw=float(rng.uniform(0, 360)), group=f"Friche/Buisson{k}",
              variant=i % 4, teinte="vert", emprise=(4, 4, 3))
        k += 1
    impact_sol(b, -14, -184, 8, 0)
    impact_sol(b, 16, -258, 7, 1)
    impact_sol(b, 24, -160, 5, 2)


# ---------------------------------------------------------------------------
# Planète extraterrestre : pitons, eau, passerelles, îlots, arbres boules, dômes, vaisseau
# ---------------------------------------------------------------------------

def passerelle(b: Builder, s: int, z: float, larg: float = 4.0) -> None:
    """Petite passerelle de pierre blanche en dos d'âne au-dessus d'un canal : du bord du trottoir (|x| = 52,5) à la
    rive extérieure (|x| = 73,5), rampes en coin, tablier plat à 1,6, garde-corps bas, culées sur les rives."""
    x0, x1 = X_BORD - 2.5, X_CANAL[1] + 3.5
    xm = (x0 + x1) / 2
    hz = larg / 2
    blanc, ombre = c("pierre_claire"), c("pierre")
    with b.group(f"Alien/Passerelle{'GD'[s > 0]}{int(-z)}"):
        def X(v):
            return s * v
        # culées sur les rives
        for (a, bb) in ((x0, X_BORD + 0.6), (X_CANAL[1] + 1.4, x1)):
            xa, xb = sorted((X(a), X(bb)))
            b.box((xa, -1.0, z - hz - 0.3), (xb, 0.6, z + hz + 0.3), ombre, studs="top", name="Culee")
        # rampes et tablier
        ra, rb = x0 + 0.5, xm - 4.0
        rc, rd = xm + 4.0, x1 - 0.5
        xa, xb = sorted((X(ra), X(rb)))
        b.wedge((xa, 0.6, z - hz), (xb, 1.6, z + hz), blanc, down="-x" if s > 0 else "+x", studs="top", name="Rampe")
        xa, xb = sorted((X(rc), X(rd)))
        b.wedge((xa, 0.6, z - hz), (xb, 1.6, z + hz), blanc, down="+x" if s > 0 else "-x", studs="top", name="Rampe")
        xa, xb = sorted((X(rb), X(rc)))
        b.box((xa, 0.6, z - hz), (xb, 1.6, z + hz), blanc, studs="top", name="Tablier")
        # arc dessous (pierre plus sombre) et garde-corps bas sur le tablier
        xa, xb = sorted((X(rb - 1.0), X(rc + 1.0)))
        b.box((xa, -0.2, z - hz + 0.4), (xb, 0.6, z + hz - 0.4), ombre, name="Arc")
        for sz in (-1, 1):
            xa, xb = sorted((X(rb), X(rc)))
            za, zb2 = sorted((z + sz * (hz - 0.4), z + sz * hz))
            b.box((xa, 1.6, za), (xb, 2.5, zb2), blanc, collide=False, name="Garde-corps")
            for xx in (rb, rc):
                b.box((X(xx) - 0.3, 1.6, za - 0.05), (X(xx) + 0.3, 2.9, zb2 + 0.05), c("coque_lavande"), collide=False,
                      name="Borne")


def planete(b: Builder) -> None:
    # pitons de sable géants à la tête des canaux (la porte de la planète)
    for i, (x, z, h, d, v) in enumerate(PITONS_PLANETE):
        place(b, "arche", "piton_geant", (x, 0, z), group=f"Alien/PitonGeant{i}", variant=v, hauteur=h, demi=d,
              demi_haut=round(d * 0.7 * 2) / 2, emprise=(2 * d + 3, 2 * d + 3, h))
    # grand vaisseau rond sur pattes, avant tourné vers le couloir
    place(b, "arche", "vaisseau_rond", (-96, 0, -318), yaw=-90, group="Alien/Vaisseau", emprise=(44, 44, 32), rayon=18,
          variant=0)
    cx, cz, rx, rz = LAC
    for i, (x, z, w, d, h, v) in enumerate(((cx - 5.75, cz + 8.25, 20, 14, 3, 0), (cx + 12.25, cz - 9.75, 14, 10, 4, 1))):
        place(b, "nature", "ile_herbeuse", (x, 0, z), yaw=0, group=f"Alien/Ile{i}", variant=v, largeur=w, profondeur=d,
              hauteur=h, emprise=(w, d, h))
    # passerelles au-dessus des canaux
    for s, zs in ((-1, (-314, -332)), (1, (-298, -322))):
        for z in zs:
            passerelle(b, s, z)
    # dômes extraterrestres (rayon 9 à 12) et hameau de dômes reliés
    place(b, "batiments", "maison_alien", (-122, 0, -289), yaw=face_couloir(-1), group="Alien/Dome0", variant=0, rayon=9,
          emprise=(22, 22, 14))
    place(b, "batiments", "hameau_alien", (-117, 0, -372), yaw=face_couloir(-1), group="Alien/Hameau0", variant=0,
          rayon=10, emprise=(49, 28, 16))
    place(b, "batiments", "maison_alien", (100, 0, -357), yaw=face_couloir(1), group="Alien/Dome1", variant=1, rayon=11,
          emprise=(26, 26, 16))
    arbres = ((-84, -284, 0, 30), (-104, -290, 0, 26), (-128, -318, 0, 34), (-80, -346, 0, 24), (-126, -340, 0, 30),
              (82, -282, 0, 32), (130, -300, 0, 38), (86, -344, 0, 24), (cx - 5.75, cz + 8.25, 3.15, 18),
              (cx + 12.25, cz - 9.75, 4.15, 14))
    for i, (x, z, y, h) in enumerate(arbres):
        place(b, "nature", "arbre_boule", (x, y, z), group=f"Alien/Arbre{i:02d}", variant=i % 4, hauteur=h, emprise=(8, 8, h))
    rng = np.random.default_rng(23)
    k = 0
    for i in range(50):
        if k >= 14:
            break
        s = -1 if i % 2 else 1
        x, z = s * float(rng.uniform(58, 130)), float(rng.uniform(-346, -284))
        if not libre(b, x, z, 2.2):
            continue
        place(b, "nature", "buisson", (x, 0, z), group=f"Alien/Buisson{k}", variant=i % 4, teinte="alien",
              emprise=(4, 4, 3))
        k += 1


def abords_place(b: Builder) -> None:
    """Derrière le temple et les tribunes : arbres boules, dômes, pitons de sable, nuages dorés sur les falaises."""
    arbres = ((-98, -348, 0, 30), (-100, -420, 0, 38), (-128, -420, 0, 32),
              (92, -428, 0, 34), (126, -372, 0, 42), (124, -428, 0, 30), (100, -380, 0, 24))
    for i, (x, z, y, h) in enumerate(arbres):
        if libre(b, x, z, 3.0, marge=0.0):
            place(b, "nature", "arbre_boule", (x, y, z), group=f"Abords/ArbrePlace{i}", variant=(i + 1) % 4, hauteur=h,
                  emprise=(8, 8, h))
    place(b, "batiments", "maison_alien", (106, 0, -408), yaw=face_couloir(1), group="Abords/DomePlace0", variant=3,
          rayon=10, emprise=(24, 24, 14))
    for i, (x, z, h) in enumerate(((-118, -406, 58), (126, -394, 50))):
        place(b, "nature", "pic_rocheux", (x, 0, z), group=f"Abords/PicPlace{i}", variant=(i + 1) % 4, hauteur=h,
              teinte="sable", emprise=(12, 12, h))
    # bancs de nuages dorés posés à plat sur le 2e gradin des falaises de sable (visibles au-dessus des falaises)
    for i, (x, z, ln, dn, hn, vn) in enumerate(NUAGES):
        s = -1 if x < 0 else 1
        place(b, "arche", "nuages_dores", (x, H_GRADIN_NUAGE, z), yaw=face_couloir(x), group=f"Abords/Nuages{i}",
              variant=vn, largeur=ln, profondeur=dn, hauteur=hn, emprise=(ln, dn, hn))


def arche_finale(b: Builder) -> None:
    n0 = len(b.parts)
    place(b, "arche", "arche_finale", (0, 0, Z_ARCHE), group="Monuments/Arche", emprise=(2 * X_FOND, PROF_ARCHE, 96),
          portique=PASSAGE / 2, centre_z=-PROF_ARCHE / 2, passage=PASSAGE, largeur=2 * X_FOND, profondeur=PROF_ARCHE,
          hauteur=96, variant=0)
    n1 = len(b.parts)
    # deux grands bancs de nuages dorés posés sur les épaules de l'arche, autour des pitons géants
    for i, s in enumerate((-1, 1)):
        xc, zc, L, P, H = s * 100, Z_ARCHE - 17, 76, 30, 40
        y = dessus_sous(b, abs(xc) - L / 2 if s > 0 else -abs(xc) - L / 2, abs(xc) + L / 2 if s > 0 else -abs(xc) + L / 2,
                        zc - P / 2, zc + P / 2, n0, n1)
        place(b, "arche", "nuages_dores", (xc, y, zc), yaw=180, group=f"Monuments/NuagesArche{i}", variant=(1, 2)[i],
              largeur=L, profondeur=P, hauteur=H, emprise=(L, P, H))


# ---------------------------------------------------------------------------
# Repères, découpage, réglages, contrôles
# ---------------------------------------------------------------------------

def reperes(b: Builder) -> None:
    """Pièces invisibles utiles au jeu : zone des œufs (sur l'arène), entrée, sortie, couloir."""
    inv = dict(transparency=1.0, collide=False, shadow=False)
    with b.group("Reperes"):
        b.box((-AX_ARENE, H_ARENE, Z_PLACE - AZ_ARENE), (AX_ARENE, H_ARENE + 1, Z_PLACE + AZ_ARENE), "#ffffff",
              name="ZoneOeufs", **inv)
        b.box((-DEMI_COULOIR, 0, Z_PORTE - 6), (DEMI_COULOIR, 1, Z_PORTE), "#ffffff", name="Entree", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE), (DEMI_COULOIR, 1, Z_SORTIE + 6), "#ffffff", name="Sortie", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE), (DEMI_COULOIR, 1, Z_PORTE), "#ffffff", name="Couloir", **inv)


def decouper(b: Builder, prefixes=("Sol/", "Bordures/", "Monuments/Arche", "Monuments/Porte", "Approche/Sol",
                                   "Approche/Bordures"), taille: float = 64) -> None:
    """Range les pièces des grands ensembles dans des sous-modèles de 64 × 64 studs (streaming Roblox)."""
    for p in b.parts:
        if p.group.startswith(prefixes):
            i, j = math.floor(p.pos[0] / taille), math.floor(p.pos[2] / taille)
            racine = "/".join(p.group.split("/")[:2])
            reste = p.group[len(racine):]
            p.group = f"{racine}/Bloc_{i:+d}_{j:+d}{reste}"


def reglages(b: Builder) -> dict:
    """Allège la physique et les ombres : petites pièces collidables (< 0,5 × < 2) et pièces hors d'atteinte
    (bas au-dessus de 40) sans collision ; petits détails (< 1 stud) sans ombre. Les repères et le sol ne
    changent pas."""
    n_col = n_haut = n_omb = 0
    for p in b.parts:
        if p.group.startswith(("Reperes", "Sol", "Approche/Sol")):
            continue
        lo, hi = _aabb(p)
        if p.collide and min(p.size) < 0.5 and max(p.size) < 2.0:
            p.collide = False
            n_col += 1
        elif p.collide and lo[1] > 40.0:
            p.collide = False
            n_haut += 1
        if p.shadow and max(p.size) <= 1.0:
            p.shadow = False
            n_omb += 1
    return {"petites_sans_collision": n_col, "hautes_sans_collision": n_haut, "details_sans_ombre": n_omb}


def build_zone(seed: int = 7) -> Builder:
    b = Builder(seed=seed)
    b.poses = []
    HAUT_FALAISE.clear()
    sol_couloir(b)
    sol_cotes(b)
    arene(b)
    bordures(b)
    sommets_falaises(b)
    porte_et_abords(b)
    poses_g, poses_d = village(b)
    details_village(b, poses_g, poses_d)
    rosace(b, -78)
    chevrons(b, (-22, -50, -106, -132))
    friche(b)
    planete(b)
    place_selection(b)
    abords_place(b)
    arche_finale(b)
    reperes(b)
    b.reglages = reglages(b)
    decouper(b)
    return b


def _aabb(p):
    R = np.asarray(p.rot).reshape(3, 3)
    half = np.abs(R) @ (np.asarray(p.size) / 2)
    return np.asarray(p.pos) - half, np.asarray(p.pos) + half


_bornes = _aabb
SOL_RELIEF = ("Arene", "Rampe", "SousRampe", "Marche")


def couloir_libre(b: Builder) -> list:
    """Liste ce qui encombre le couloir de course au sol (|x| < 45) : toute pièce collidable entre y = 0,05 et 12,
    sauf les repères et, dans le groupe Sol, les dalles plates (dessus ≤ 0,05) et le relief voulu de l'arène."""
    gene = []
    for p in b.parts:
        if not p.collide or p.group.startswith("Reperes"):
            continue
        lo, hi = _aabb(p)
        if p.group.startswith(("Sol", "Approche/Sol")) and (hi[1] <= 0.05 + 1e-6 or p.name in SOL_RELIEF):
            continue
        if lo[0] < DEMI_COULOIR - 0.05 and hi[0] > -DEMI_COULOIR + 0.05 and lo[1] < 12 and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            gene.append((p.group, p.name, [round(v, 1) for v in lo], [round(v, 1) for v in hi]))
    return gene


def trop_bas_au_dessus(b: Builder, y_min: float = 30.0) -> list:
    """Pièces au-dessus du couloir (|x| < 46) mais sous `y_min` (la caméra Roblox sauterait en passant dessous)."""
    out = []
    for p in b.parts:
        if p.group.startswith(("Sol", "Approche/Sol", "Reperes")):
            continue
        lo, hi = _aabb(p)
        if lo[0] < X_LIBRE_HAUT - 0.05 and hi[0] > -X_LIBRE_HAUT + 0.05 and lo[1] < y_min and hi[1] > 12 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name, round(lo[1], 1)))
    return out


def decor_dans_couloir(b: Builder) -> list:
    """Détails sans collision posés dans le couloir au-dessus du sol (hors marquages peints)."""
    out = []
    for p in b.parts:
        if p.collide or p.group.startswith(("Sol", "Approche/Sol", "Reperes", "Details/Impact", "Details/Rosace",
                                            "Details/Chevrons")) or p.transparency >= 1:
            continue
        lo, hi = _aabb(p)
        if lo[0] < DEMI_COULOIR - 0.05 and hi[0] > -DEMI_COULOIR + 0.05 and lo[1] < 12 and hi[1] > 0.3 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name))
    return out


def trous_sol(b: Builder, pas: float = 0.5) -> int:
    """Nombre de points (grille de 0,5) du couloir et des trottoirs (|x| < 55, z de -470 à 48) qui ne sont couverts
    par aucune dalle de sol (dessus entre -0,05 et le dessus de l'arène)."""
    nx, nz = int(2 * X_BORD / pas), int((Z_APPROCHE - Z_SORTIE) / pas)
    couvert = np.zeros((nz, nx), bool)
    for p in b.parts:
        if not p.group.startswith(("Sol", "Approche/Sol")) or p.transparency >= 1:
            continue
        lo, hi = _aabb(p)
        if not (-0.05 <= hi[1] <= H_ARENE + 0.05):
            continue
        i0 = max(0, int(math.ceil((lo[0] + X_BORD) / pas - 0.5 - 1e-6)))
        i1 = min(nx, int(math.floor((hi[0] + X_BORD) / pas - 0.5 + 1e-6)) + 1)
        j0 = max(0, int(math.ceil((lo[2] - Z_SORTIE) / pas - 0.5 - 1e-6)))
        j1 = min(nz, int(math.floor((hi[2] - Z_SORTIE) / pas - 0.5 + 1e-6)) + 1)
        if i1 > i0 and j1 > j0:
            couvert[j0:j1, i0:i1] = True
    return int((~couvert).sum())


FEUILLAGES = ("palmier", "buisson", "arbre_rond", "arbre_boule", "nuages_dores")
ASSISE = 0.8     # un pied, un tronc ou une semelle enfoncés de moins de 0,8 dans ce qui les porte : posé, pas un recoupement


def _obb(p):
    return np.asarray(p.pos, float), np.asarray(p.rot, float).reshape(3, 3), np.asarray(p.size, float) / 2


def _penetration(a, bb) -> float:
    """Profondeur d'interpénétration de deux boîtes orientées (axes séparateurs) ; 0 si elles ne se touchent pas.
    Coins, cylindres et boules sont traités comme leur boîte englobante (contrôle prudent)."""
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
    de plus de `tol` et profondeur maximale. Le sol plat et l'eau sont ignorés (tout y est posé) ; l'arène, ses
    marches, les falaises (par côté) et les mâts de fanions comptent comme des poses. Les feuillages (palmiers,
    arbres, buissons) et les boules sans collision des nuages qui débordent sur un voisin sont rangés à part
    (`feuillage`) ; une pièce enfoncée de moins de `ASSISE` dans ce qui la porte (tronc dans l'herbe d'une
    falaise, pied d'arbre sur un îlot) est posée, pas recoupée."""
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
            if racine in ("Reperes",) or p.name in ("Eau", "FondEau") or p.group.startswith((
                    "Details/Impact", "Details/Rosace", "Details/Chevrons", "Details/Ecume")):
                continue
            lo, hi = _aabb(p)
            if (racine == "Sol" or p.group.startswith("Approche/Sol")) and hi[1] <= 0.6:
                continue
            parts = p.group.split("/")
            etiquette[i] = "/".join(parts[:2]) if racine != "Sol" else f"Sol/{p.name}"
        actifs.append(i)
    boites = {i: _aabb(b.parts[i]) for i in actifs}
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
                    continue                   # assise : l'un est posé sur l'autre (plus haut en bas comme en haut)
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


def meta() -> dict:
    return {"nom": "ZoneDragonBall", "version": VERSION, "largeur_couloir": 2 * DEMI_COULOIR,
            "longueur": -Z_SORTIE, "spawn": [0, 0, Z_PORTE + 30]}


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
    deco = decor_dans_couloir(b)
    print(json.dumps({"pieces": len(b.parts), "fichier": str(out), "en_attente": attente,
                      "couloir_encombre": gene[:20], "nb_couloir_encombre": len(gene),
                      "trop_bas_au_dessus_du_couloir": bas[:20], "decor_dans_couloir": deco[:20],
                      "trous_sol": trous_sol(b), "reglages": getattr(b, "reglages", {}),
                      "approche": sum(p.group.startswith("Approche") for p in b.parts)}, ensure_ascii=False))
    if args.stats:
        for k, v in b.stats().items():
            print(f"{v:6d}  {k}")
    if args.chevauchements:
        res = chevauchements(b)
        durs = {k: v for k, v in res.items() if not v["feuillage"]}
        print(f"chevauchements : {len(durs)} paires de poses (+ {len(res) - len(durs)} de feuillage)")
        for (ga, gb), v in sorted(res.items(), key=lambda kv: -kv[1]["profondeur"]):
            tag = "feuillage " if v["feuillage"] else ""
            print(f"  {tag}{v['profondeur']:6.2f}  {v['paires']:4d}  {ga}  <->  {gb}   {v['exemple']}")


if __name__ == "__main__":
    main()
