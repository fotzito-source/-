#!/usr/bin/env python3
"""Plan de la zone Dragon Ball (campagne terrestre, terres de combat, planète extraterrestre) en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course occupe x ∈ [-45, 45] (90 studs), bordé de trottoirs jusqu'à |x| = 55 ; les premières
  façades sont à |x| = 56 ;
- on entre sous la grande porte de temple en z = 0 et on court vers -Z :
    1. campagne terrestre (0 → -146) : rue de maisons-dômes blanches à bandes colorées et de boutiques à objet
       géant, palmiers, dojo et pagodes au second plan, falaises orange en strates couronnées d'herbe, cascades ;
    2. terres de combat (-146 → -282) : plaine verte trouée de terre kaki, mesas aux flancs violets, cratères,
       et un pont de roche naturel qui enjambe le couloir (z = -214, piles à |x| ≥ 50, dessous à 34 studs) ;
    3. planète extraterrestre (-282 → -344) : herbe bleu-vert, canaux turquoise le long des trottoirs, lac et
       îlots, arbres « boules », dômes blancs, vaisseau rond sur pattes, pitons de sable, nuages dorés ;
    4. place des œufs = arène d'arts martiaux en dalles (96 × 80, centre z = -389, dessus à 1 stud) qui couvre
       tout le couloir, poteaux à flamme sur ses coins, temple aux toits orange à gauche, tribunes et gong à
       droite, bannières, cordons de fanions au-dessus (≥ 34 studs) ;
    5. arche de roche géante (façade z = -436) : le couloir passe dessous (104 de large) et sort vers la zone
       suivante (z = -470).
- des falaises en quatre gradins ferment les côtés (|x| ≥ 135) : orange (jusqu'à z = -178), puis violettes, puis
  sable ocre ; arbres, palmiers et petits pitons sur leurs crêtes, nuages dorés sur les gradins du fond.

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
Z_APPROCHE = 40          # sol devant la porte (côté apparition)
Z_PORTE = 0
Z_FIN_VILLAGE = -146     # fin de la campagne terrestre
Z_FIN_ORANGE = -178      # les falaises orange débordent sur la friche (on les voit encore depuis le village)
Z_PONT = -214            # pont de roche au-dessus du couloir
Z_ALIEN = -282           # début de la planète extraterrestre
Z_PLACE = -389           # centre de l'arène (place des œufs)
AX_ARENE = 48            # demi-largeur de l'arène (x) : elle couvre tout le couloir, ses coins sont hors couloir
AZ_ARENE = 40            # demi-longueur de l'arène (z)
H_ARENE = 1.0            # dessus de l'arène (rampes de 5 studs devant et derrière)
L_RAMPE = 5
R_PLACE = AZ_ARENE
Z_ARCHE = -436           # façade de l'arche finale
PROF_ARCHE = 34
Z_SORTIE = Z_ARCHE - PROF_ARCHE   # -470 : le couloir continue vers la zone suivante
PASSAGE = 104            # largeur libre sous l'arche (jambes à |x| ≥ 52)
H_FANIONS = 38           # cordons de fanions au-dessus du couloir (creux compris ≥ 34)
Z0_SOL = Z_SORTIE - 6    # -476 : bout du sol (grille de 3 et de 2)

# canaux de la planète (grille de 4 du sol des côtés)
X_CANAL = (59, 71)
Z_CANAL = (-340, -288)
LAC = (106, -314, 26, 22)   # centre x, centre z, demi-axes

VERSION = "0.4"


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
    """Paysage au point (x, z) : « terre », « friche » ou « alien », frontières tramées sur ±6 studs."""
    zz = z + (bruit(x, z, 6, 11) - 0.5) * 12
    if zz > Z_FIN_VILLAGE:
        return "terre"
    if zz > Z_ALIEN:
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
    """Arène, ses rampes et ses marches latérales (dessinées à part, en relief ; marches de |x| = 48 à 49, le
    trottoir reprend à 49 sur sa grille de 2)."""
    return abs(x) < AX_ARENE + 1 and abs(z - Z_PLACE) < AZ_ARENE + L_RAMPE


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
    if X_CANAL[0] <= xq <= X_CANAL[1] and Z_CANAL[0] <= zq <= Z_CANAL[1]:
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
    kaki, kakif, ocre = c("kaki"), c("kaki_fonce"), c("ocre")
    sab, sabc, ha = c("sable"), c("sable_clair"), c("herbe_alien_claire")
    vio, viof, nuit = c("mesa_violet"), c("mesa_violet_fonce"), c("mesa_nuit")

    def couloir(x, z):
        if dans_arene(x, z):
            return None
        ax = abs(x)
        zz = z - Z0_SOL
        if z < Z_ARCHE + 2:                 # passage sous l'arche : grandes dalles violettes
            if ax > DEMI_COULOIR - 3:
                return vio
            return viof if math.floor(zz / 9) % 2 else nuit
        sec = section(x, z)
        if sec == "terre":                  # route du village : grandes dalles crème, frise terre cuite au bord
            if DEMI_COULOIR - 6 <= ax < DEMI_COULOIR - 3:
                return pc
            return dl if (math.floor((x + DEMI_COULOIR) / 15) + math.floor(zz / 12)) % 2 == 0 else dlf
        if sec == "friche":                 # terre battue kaki, taches ocre et sombres, bords et îlots d'herbe
            if ax > DEMI_COULOIR - 9 + 6 * bruit(x, z, 7, 13) or bruit(x, z, 14, 17) > 0.8:
                return c("herbe") if bruit(x, z, 5, 19) > 0.35 else c("herbe_claire")
            n = bruit(x, z, 18, 3)
            if n > 0.7:
                return ocre
            if n < 0.28:
                return kakif
            return kaki
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
            return c("gravats") if bruit(x, z, 12, 9) > 0.45 else kakif
        if ax < DEMI_COULOIR + 2:
            return c("sable_fonce")
        return c("sable_fonce") if math.floor(z / 8) % 3 == 0 else sab

    with b.group("Sol/Couloir"):
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, Z0_SOL, Z_APPROCHE, 3, couloir)
    with b.group("Sol/Trottoirs"):
        for s in (-1, 1):
            xa, xb = sorted((s * DEMI_COULOIR, s * X_BORD))
            sol_pixel(b, xa, xb, Z0_SOL, Z_APPROCHE, 2, trottoir)


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
            if n > 0.58:
                return kaki
            return hf if n < 0.28 else h
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
            sol_pixel(b, xa, xb, z_coupe, Z_APPROCHE + 4, 8, couleur)
            sol_pixel(b, xa, xb, Z_ARCHE, z_coupe, 4, couleur)
    with b.group("Sol/Eau"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_FALAISE))
            sol_pixel(b, xa, xb, Z_ARCHE, z_coupe, 2, eau, y_haut=-0.4, epaisseur=1.6, studs="none",
                      transparency=0.12, name="Eau")
        # fond sombre sous l'eau (profondeur turquoise foncé), 0,2 sous la dalle d'eau : une dalle par canal, une pour le lac
        for s in (-1, 1):
            xa, xb = sorted((s * X_CANAL[0], s * X_CANAL[1]))
            b.box((xa, -2.8, Z_CANAL[0]), (xb, -2.2, Z_CANAL[1]), c("eau_fonce"), name="FondEau")
        cx, cz, rx, rz = LAC
        b.box((X_CANAL[1], -2.8, cz - rz), (cx + rx, -2.2, cz + rz), c("eau_fonce"), name="FondEau")


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


def impact_sol(b: Builder, x: float, z: float, r: float, graine: int = 0) -> None:
    """Trace d'impact peinte sur le couloir (sans collision, 0,12 au-dessus du sol) : disques brûlés et fissures."""
    rng = np.random.default_rng(900 + graine)
    with b.group(f"Details/Impact{graine}"):
        b.cyl((x, 0.06, z), r, 0.12, c("kaki_fonce"), collide=False, shadow=False, name="Impact")
        b.cyl((x, 0.1, z), r * 0.62, 0.12, c("fissure"), collide=False, shadow=False, name="Impact")
        b.cyl((x, 0.14, z), r * 0.3, 0.12, c("brule"), collide=False, shadow=False, name="Impact")
        for k in range(6):
            a = k * 60 + float(rng.uniform(-18, 18))
            L = r * float(rng.uniform(0.7, 1.15))
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            cx, cz = x + ca * (r * 0.55 + L / 2), z + sa * (r * 0.55 + L / 2)
            b.boxc((cx, 0.07, cz), (L, 0.14, 0.7), c("fissure"), yaw=-a, collide=False, shadow=False, name="Fissure")


# ---------------------------------------------------------------------------
# Arène d'arts martiaux (place des œufs)
# ---------------------------------------------------------------------------

def arene(b: Builder) -> None:
    """Arène en dalles de pierre (96 × 80), en léger relief (dessus à 1 stud), qui couvre tout le couloir :
    rampes devant et derrière, marches sur les côtés, grand 武 rouge dans un cercle doré, bordure sombre,
    poteaux à flamme posés sur ses quatre coins (hors couloir)."""
    n_gl = 26
    glyphe = glyph_mask("武", n_gl, font="brush", bold=0.6)
    a_, af, j = c("arene"), c("arene_fonce"), c("arene_joint")
    pc, rouge, orr = c("pierre_claire"), c("laque_rouge"), c("or")

    def motif(x, z):
        dz = z - Z_PLACE
        if abs(x) > AX_ARENE - 2 or abs(dz) > AZ_ARENE - 2:
            return j
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
        # marches sur les côtés
        for s in (-1, 1):
            xa, xb = sorted((s * AX_ARENE, s * (AX_ARENE + 1)))
            b.box((xa, -1, Z_PLACE - AZ_ARENE - L_RAMPE), (xb, H_ARENE / 2, Z_PLACE + AZ_ARENE + L_RAMPE),
                  c("pierre_fonce"), studs="top", name="Marche")
    # poteaux à flamme sur les coins de l'arène (|x| ≥ 45,1 : hors couloir)
    for i, (sx, sz) in enumerate(((-1, 1), (1, 1), (-1, -1), (1, -1))):
        place(b, "mobilier", "poteau_arene", (sx * (AX_ARENE - 1.3), H_ARENE, Z_PLACE + sz * (AZ_ARENE - 1.8)),
              group=f"Place/Poteau{i}", variant=2 if i % 3 == 0 else 0, hauteur=6.6, emprise=(3, 3, 11))


def place_selection(b: Builder) -> None:
    """Autour de l'arène : temple d'arts martiaux à gauche, tribunes et gong à droite, fanions, bannières."""
    place(b, "temple", "temple_tournoi", (-(X_FACADE + 17), 0, Z_PLACE), yaw=-90, group="Place/Temple",
          emprise=(60, 34, 38), largeur=60, profondeur=34)
    for i, dz in enumerate((19, -19)):
        place(b, "temple", "tribune", (X_FACADE + 7, 0, Z_PLACE + dz), yaw=90, group=f"Place/Tribune{i}",
              emprise=(28, 14, 12), variant=i, longueur=28, rangs=5)
    place(b, "mobilier", "gong", (X_FACADE + 1.8, 0, Z_PLACE), yaw=90, group="Place/Gong", emprise=(9, 3, 8))
    # bannières sur le parvis, entre les marches de l'arène et le temple / les tribunes
    textes = ("武", "気", "修行", "武道")
    for s in (-1, 1):
        for i, dz in enumerate((-30, -10, 10, 30)):
            if s > 0 and abs(dz) == 10:
                continue                       # le gong occupe le milieu du côté droit
            x = s * 52.5
            place(b, "mobilier", "banniere", (x, 0, Z_PLACE + dz), yaw=face_couloir(x),
                  group=f"Place/Banniere{'GD'[s > 0]}{i}", texte=textes[(i + (s > 0)) % 4], variant=(i + (s > 0)) % 4,
                  hauteur=11, emprise=(3, 2, 11))
    # cordons de fanions au-dessus de l'arène : mâts rouges sur le parvis, cordons à ≥ 34 studs
    fan = _asset("mobilier", "guirlande_fanions")
    for i, dz in enumerate((22, -22)):
        z = Z_PLACE + dz
        with b.group(f"Place/Fanions{i}"):
            for s in (-1, 1):
                with b.at((s * 53.5, 0, z)):
                    b.box((-0.9, 0, -0.9), (0.9, 1.2, 0.9), c("pierre_fonce"), studs="top", name="Pied")
                    b.box((-0.45, 1.2, -0.45), (0.45, H_FANIONS + 2, 0.45), c("laque_rouge"), name="Mat")
                    b.box((-0.7, H_FANIONS + 2, -0.7), (0.7, H_FANIONS + 2.6, 0.7), c("or"), name="Chapeau")
            if fan:
                fan(b, (-53, H_FANIONS, z), (53, H_FANIONS, z), n=15, creux=2.5, variant=i)


# ---------------------------------------------------------------------------
# Falaises latérales (orange, puis violettes, puis sable ocre)
# ---------------------------------------------------------------------------

STYLES_FALAISE = {
    # tons des gradins, strate, herbe du sommet, hauteur de base, surcroît du 2e et du 3e gradin
    "terre": (("falaise_orange", "falaise_orange_claire", "falaise_orange_fonce"), "falaise_brune", "herbe", (14, 20), (10, 16), (22, 32)),
    "friche": (("mesa_violet", "mesa_violet_fonce", "mesa_violet_clair"), "mesa_rose", "herbe", (20, 30), (12, 20), (26, 40)),
    "alien": (("falaise_sable", "falaise_sable_claire", "falaise_sable_fonce"), "falaise_sable_fonce", "herbe_alien", (5, 9), (6, 10), (10, 16)),
}
# bancs de nuages dorés sur les gradins des falaises : (x, z, largeur le long de z, profondeur le long de x, hauteur)
NUAGES = ((-192, -316, 44, 30, 22), (194, -358, 48, 30, 26), (-192, -404, 50, 32, 30),
          (192, -408, 44, 28, 24), (-163, -270, 40, 20, 18))
GRADINS = ((X_FALAISE, X_FALAISE + 16), (X_FALAISE + 16, X_FALAISE + 40), (X_FALAISE + 40, X_FALAISE + 61),
           (X_FALAISE + 61, X_FOND))
CASCADES = {(-1, 5), (-1, 10), (1, 7), (1, 9)}   # (côté, tranche) : cascades dans la campagne terrestre
HAUT_FALAISE: dict = {}                          # (côté, tranche) → (z centre, (h1, h2, h3, h4), style)


def bordures(b: Builder) -> None:
    """Falaises en quatre gradins (tranches de 16 studs) qui ferment la vallée ; dessus en herbe débordante, strates.
    Le dernier gradin (|x| ≥ 196) monte encore de 5 à 12 studs : vue d'en haut, les falaises font des terrasses."""
    rng = np.random.default_rng(5)
    rng4 = np.random.default_rng(6)
    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        z = Z_APPROCHE
        k = 0
        while z > Z_ARCHE + 0.01:
            l = min(16, z - Z_ARCHE)
            zc = z - l / 2
            style = "terre" if zc > Z_FIN_ORANGE else ("friche" if zc > Z_ALIEN else "alien")
            tons, strate, herbe, base, plus2, plus3 = STYLES_FALAISE[style]
            h1 = rng.uniform(*base) + 3 * math.sin(k * 0.9)
            if (s, k) in CASCADES:
                h1 = 26
            if style == "friche" and k % 3 == 1:
                h1 *= 0.6                               # encoche : on voit les mesas du fond
            h2 = h1 + rng.uniform(*plus2)
            h3 = h2 + rng.uniform(*plus3)
            h4 = h3 + rng4.uniform(5, 12)
            gradins = tuple((xa_, xb_, hg) for (xa_, xb_), hg in zip(GRADINS, (h1, h2, h3, h4)))
            HAUT_FALAISE[(s, k)] = (zc, tuple(round(v) for v in (h1, h2, h3, h4)), style)
            with b.group(f"Bordures/{cote}"):
                h_avant = 0.0                           # dessus du gradin de devant (la strate doit le dépasser)
                for gi, (xa_, xb_, hg) in enumerate(gradins):
                    hg = float(round(hg))
                    xa, xb = sorted((s * xa_, s * xb_))
                    b.box((xa, 0, z - l), (xb, hg - 1.2, z), c(tons[(k + gi) % 3]), studs="top", name="Gradin")
                    # chapeau d'herbe qui déborde de 0,6 côté vallée
                    ha, hb = sorted((s * (xa_ - 0.6), s * xb_))
                    b.box((ha, hg - 1.2, z - l), (hb, hg, z), c(herbe), studs="top", name="Herbe")
                    # strate claire sur la face côté vallée
                    if hg > 8:
                        ys = round(hg * float(rng.uniform(0.35, 0.6)))
                        ys = max(ys, h_avant + 1)
                        if ys + 1.2 < hg - 2.5:
                            sa, sb = sorted((s * (xa_ - 0.3), s * xa_))
                            b.box((sa, ys, z - l + 0.5), (sb, ys + 1.2, z - 0.5), c(strate), collide=False, name="Strate")
                    # coulures d'herbe sous le chapeau
                    if gi < 2 and (k + gi) % 2 == 0:
                        zq = z - l * float(rng.uniform(0.2, 0.7))
                        lg = float(rng.uniform(1.5, 3.5))
                        ca, cb = sorted((s * (xa_ - 0.6), s * (xa_ - 0.1)))
                        b.box((ca, hg - 1.2 - lg, zq - 1.2), (cb, hg - 1.2, zq + 1.2), c(herbe), collide=False, name="Coulure")
                    h_avant = hg
            z -= l
            k += 1


def sommets_falaises(b: Builder) -> None:
    """Silhouettes sur le haut des falaises (vues depuis le couloir et d'en haut) : arbres ronds et palmiers
    sur les falaises orange, buissons et rochers violets sur la friche, arbres boules sur la planète."""
    for (s, k), (zc, (h1, h2, h3, h4), style) in sorted(HAUT_FALAISE.items()):
        if (s, k) in CASCADES or abs(zc - Z_ARCHE) < 10 or zc > Z_APPROCHE - 8:
            continue
        g = f"Bordures/Sommets{'GD'[s > 0]}"
        j = (k + (s > 0)) % 4
        if style == "terre":
            if j == 0:
                place(b, "nature", "arbre_rond", (s * 143, h1, zc), group=f"{g}/Arbre{k}", variant=k % 4,
                      hauteur=10 + k % 3, emprise=(10, 10, 12))
            elif j == 2:
                place(b, "nature", "palmier", (s * 163, h2, zc - 2), yaw=k * 47, group=f"{g}/Palmier{k}", variant=k % 4,
                      hauteur=12 + k % 3, emprise=(12, 12, 14))
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
            if j in (0, 2):
                place(b, "nature", "arbre_boule", (s * (143 if j == 0 else 163), h1 if j == 0 else h2, zc),
                      group=f"{g}/ArbreBoule{k}", variant=k % 4, hauteur=16 + 4 * (k % 3), emprise=(8, 8, 20))
            elif j == 3:
                place(b, "nature", "buisson", (s * 141, h1, zc), group=f"{g}/Buisson{k}", variant=k % 4,
                      teinte="alien", emprise=(4, 4, 3))
        # ligne de crête : un arbre ou un piton sur le haut gradin, une tranche sur trois
        sous_nuage = any((x_n < 0) == (s < 0) and abs(zc - z_n) < w_n / 2 + 8 and abs(abs(x_n) - 182) < d_n / 2 + 6
                         for (x_n, z_n, w_n, d_n, h_n) in NUAGES)
        if (k + (s > 0)) % 3 == 1 and abs(zc - Z_ARCHE) > 24 and not sous_nuage:
            if style == "terre":
                place(b, "nature", "arbre_rond", (s * 182, h3, zc), group=f"{g}/Crete{k}", variant=(k + 2) % 4,
                      hauteur=12 + k % 3, emprise=(10, 10, 14))
            elif style == "friche":
                place(b, "nature", "pic_rocheux", (s * 184, h3, zc), group=f"{g}/Crete{k}", variant=k % 4,
                      hauteur=14 + 2 * (k % 3), teinte="violet", emprise=(10, 10, 18))
            else:
                place(b, "nature", "arbre_boule", (s * 182, h3, zc), group=f"{g}/Crete{k}", variant=(k + 1) % 4,
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
# Campagne terrestre : porte, village de dômes, dojo, pagodes, cascades
# ---------------------------------------------------------------------------

# (fonction, rayon ou None, largeur le long de z, profondeur le long de x, centre z, paramètres)
RANGEE_GAUCHE = [
    ("maison_dome", 10, 24, 26, -25, {"variant": 0}),
    ("boutique_dome", None, 16, 16, -51, {"variant": 0}),
    ("maison_dome", 9, 30, 24, -80, {"variant": 2}),
    ("maison_dome", 11, 26, 28, -114, {"variant": 3}),
    ("boutique_dome", None, 16, 16, -141, {"variant": 2}),
]
RANGEE_DROITE = [
    ("maison_dome", 9, 22, 24, -24, {"variant": 1}),
    ("maison_dome", 11, 26, 28, -54, {"variant": 4}),
    ("boutique_dome", None, 16, 16, -81, {"variant": 3}),
    ("maison_dome", 10, 24, 26, -107, {"variant": 5}),
    ("maison_dome", 8, 28, 22, -139, {"variant": 2}),
]


def rangee(b: Builder, s: int, plan) -> list:
    """Aligne une rangée de bâtiments du village le long du couloir (avant tourné vers le couloir)."""
    cote = "Gauche" if s < 0 else "Droite"
    poses = []
    for i, (fn, r, larg, prof, zc, params) in enumerate(plan):
        kw = dict(params)
        if r is not None:
            kw["rayon"] = r
        x = s * (X_FACADE + prof / 2)
        info = place(b, "batiments", fn, (x, 0, zc), yaw=face_couloir(x), group=f"Village/{cote}/{i:02d}_{fn}",
                     emprise=(larg, prof, (r or 6) + 6), **kw)
        poses.append((x, zc, larg, prof, info))
    return poses


def porte_et_abords(b: Builder) -> None:
    place(b, "temple", "porte_temple", (0, 0, Z_PORTE), group="Monuments/Porte", emprise=(2 * X_FALAISE, 16, 55),
          portique=46, ouverture=92, hauteur=55, mur=X_FALAISE - 0.1)
    for s in (-1, 1):
        g = "GD"[s > 0]
        place(b, "temple", "statue_gardien", (s * 59, 0, Z_PORTE + 13), yaw=180, group=f"Monuments/Gardien{g}",
              variant=int(s > 0), emprise=(7, 9, 12))
        place(b, "mobilier", "lanterne_chinoise", (s * 50, 0, Z_PORTE + 26), group=f"Abords/Lanterne{g}",
              variant=1, emprise=(2, 7, 9))
        for i, (dx, dz, h) in enumerate(((70, 26, 15), (94, 33, 13), (118, 18, 16), (124, 36, 12))):
            place(b, "nature", "palmier", (s * dx, 0, Z_PORTE + dz), yaw=(i * 70 + (s > 0) * 35) % 360,
                  group=f"Abords/Palmier{g}{i}", variant=(i + (s > 0)) % 4, hauteur=h, emprise=(12, 12, 16))
        for i, (dx, dz) in enumerate(((82, 37), (106, 30))):
            place(b, "nature", "arbre_rond", (s * dx, 0, Z_PORTE + dz), group=f"Abords/Arbre{g}{i}",
                  variant=(i + 2 * (s > 0)) % 4, hauteur=12 + 2 * i, emprise=(10, 10, 14))
        for i, (dx, dz) in enumerate(((62, 34), (78, 16), (100, 14), (128, 8))):
            place(b, "nature", "buisson", (s * dx, 0, Z_PORTE + dz), yaw=i * 40, group=f"Abords/Buisson{g}{i}",
                  variant=i % 4, teinte="vert", emprise=(4, 4, 3))


def village(b: Builder):
    poses_g = rangee(b, -1, RANGEE_GAUCHE)
    poses_d = rangee(b, 1, RANGEE_DROITE)
    # deuxième plan à gauche : dojo et terrain d'entraînement, pagode verte, dôme du fond
    place(b, "temple", "dojo", (-106, 0, -46), yaw=-90, group="Village/Dojo", emprise=(24, 18, 16), largeur=24,
          profondeur=18, variant=0)
    entr = ((-89, -38, "mannequin_bois", {}), (-89, -45, "mannequin_bois", {"variant": 1}),
            (-89, -55, "jarres", {"variant": 2}), (-90, -29, "banniere", {"texte": "修行", "variant": 1}),
            (-90, -63, "panneau", {"texte": "道場", "variant": 0}))
    for i, (x, z, fn, kw) in enumerate(entr):
        place(b, "mobilier", fn, (x, 0, z), yaw=-90, group=f"Village/Entrainement{i}", emprise=(3, 3, 6), **kw)
    place(b, "temple", "pagode", (-104, 0, -112), group="Village/PagodeG", variant=1, emprise=(12, 12, 22), etages=2)
    place(b, "temple", "pagode", (100, 0, -38), group="Village/PagodeD", variant=0, emprise=(12, 12, 30), etages=3)
    place(b, "temple", "pagode", (104, 0, -122), group="Village/PagodeD2", variant=2, emprise=(12, 12, 22), etages=2)
    for i, (x, z, r, v) in enumerate(((-100, -84, 7, 4), (-100, -17, 6, 1), (96, -84, 8, 3), (98, -12, 6, 0),
                                       (-112, -132, 7, 2))):
        place(b, "batiments", "maison_dome", (x, 0, z), yaw=face_couloir(x), group=f"Village/Arriere{i}", variant=v,
              rayon=r, emprise=(2 * r + 4, 2 * r + 6, r + 6))
    # voitures volantes garées le long des trottoirs (hors couloir) et dans les jardins
    for i, (x, z, yaw, v) in enumerate(((-51, -63, 0, 0), (51.5, -100, 180, 1), (-51.5, -119, 180, 2),
                                         (90, -66, -60, 3), (-90, -126, 30, 1))):
        place(b, "batiments", "voiture_volante", (x, 0, z), yaw=yaw, group=f"Village/Voiture{i}", variant=v,
              emprise=(5, 9, 4))
    # palmiers entre les maisons de la rue et au second plan ; arbres ronds
    palmiers = ((-58.5, -40), (-58.5, -63.5), (-58.5, -98), (-58.5, -130), (-58.5, -152), (58.5, -38),
                (58.5, -70), (58.5, -92), (58.5, -122), (-84, -6), (84, -26), (-122, -58),
                (120, -98), (-86, -100), (86, -144), (118, -62), (-80, -150))
    for i, (x, z) in enumerate(palmiers):
        place(b, "nature", "palmier", (x, 0, z), yaw=(i * 53) % 360, group=f"Village/Palmier{i:02d}", variant=i % 4,
              hauteur=13 + (i % 3) * 2, emprise=(12, 12, 16))
    for i, (x, z) in enumerate(((-122, -30), (-92, -136), (116, -136), (120, -12), (84, -106), (-124, -92),
                                 (86, -40), (-86, -20))):
        place(b, "nature", "arbre_rond", (x, 0, z), group=f"Village/Arbre{i}", variant=i % 4, hauteur=11 + (i % 3) * 2,
              emprise=(10, 10, 14))
    for i, (x, z, h) in enumerate(((-124, -76, 34), (122, -26, 42), (124, -138, 30), (-126, -12, 26))):
        place(b, "nature", "pic_rocheux", (x, 0, z), group=f"Village/Pic{i}", variant=i, hauteur=h, teinte="orange",
              emprise=(10, 10, h))
    # cascades au pied des falaises orange
    for (s, k), (zc, hs, style) in sorted(HAUT_FALAISE.items()):
        if (s, k) in CASCADES:
            x = s * X_FALAISE
            place(b, "nature", "cascade", (x, 0, zc), yaw=face_couloir(x), group=f"Village/Cascade{'GD'[s > 0]}{k}",
                  variant=k % 3, hauteur=hs[0], largeur=8, emprise=(12, 10, hs[0]))
    return poses_g, poses_d


Z_LAMPES = (-10, -40, -70, -100, -130)
Z_FANIONS_RUE = (-48, -108, -138)


def details_village(b: Builder, poses_g, poses_d) -> None:
    """Lampadaires, bancs, terrasses, distributeurs, jardinières sur les trottoirs (jamais dans le couloir).

    Lampadaires et mâts au milieu du trottoir (|x| = 50), mobilier contre les façades (|x| = 52,5) : seuls les
    parasols (8 × 8) et les voitures garées (|x| ≈ 51) ont besoin d'un écart en z avec eux."""
    mats = {s: [] for s in (-1, 1)}          # lampadaires et mâts de fanions (x = ±50)
    gros = {-1: [-63, -119], 1: [-100]}       # voitures garées le long du trottoir
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

def friche(b: Builder) -> None:
    place(b, "arche", "pont_rocheux", (0, 0, Z_PONT), group="Monuments/Pont", emprise=(162, 28, 54), portique=50,
          portee=100, hauteur=36, epaisseur=12, largeur_pile=30, variant=0)
    mesas = (  # (x, z, largeur le long du couloir (z), profondeur vers l'extérieur (x), hauteur, variante)
        (-66, -170, 30, 26, 22, 0), (68, -170, 30, 26, 26, 1), (-72, -262, 34, 28, 30, 2), (66, -260, 30, 24, 20, 3),
        (-112, -192, 36, 30, 46, 1), (114, -206, 34, 32, 54, 0), (-110, -244, 30, 28, 40, 3), (112, -258, 30, 28, 42, 2),
        (-104, -158, 24, 20, 30, 2), (106, -160, 22, 20, 28, 3),
    )
    for i, (x, z, w, d, h, v) in enumerate(mesas):
        place(b, "nature", "mesa", (x, 0, z), yaw=face_couloir(x), group=f"Friche/Mesa{i:02d}", variant=v,
              largeur=w, profondeur=d, hauteur=h, emprise=(w, d, h))
    for i, (x, z, r) in enumerate(((-62, -236, 7), (86, -237, 6), (-98, -278, 7), (104, -232, 5))):
        place(b, "nature", "cratere", (x, 0, z), group=f"Friche/Cratere{i}", variant=i, rayon=r, emprise=(2 * r + 4, 2 * r + 4, 3))
    for i, (x, z, h) in enumerate(((88, -186, 34), (-90, -214, 46), (90, -278, 30))):
        place(b, "nature", "pic_rocheux", (x, 0, z), group=f"Friche/Pic{i}", variant=(i + 1) % 4, hauteur=h,
              teinte="violet", emprise=(10, 10, h))
    rng = np.random.default_rng(17)
    k = 0
    for i in range(60):
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
    for i in range(40):
        if k >= 16:
            break
        s = -1 if i % 2 else 1
        x, z = s * float(rng.uniform(52, 126)), float(rng.uniform(-280, -150))
        if not libre(b, x, z, 2.2):
            continue
        place(b, "nature", "buisson", (x, 0, z), yaw=float(rng.uniform(0, 360)), group=f"Friche/Buisson{k}",
              variant=i % 4, teinte="vert", emprise=(4, 4, 3))
        k += 1
    impact_sol(b, -14, -184, 9, 0)
    impact_sol(b, 18, -256, 7, 1)
    impact_sol(b, 26, -160, 5, 2)


# ---------------------------------------------------------------------------
# Planète extraterrestre : eau, îlots, arbres boules, dômes, vaisseau, nuages dorés
# ---------------------------------------------------------------------------

def planete(b: Builder) -> None:
    place(b, "arche", "vaisseau_rond", (-94, 0, -306), yaw=-115, group="Alien/Vaisseau", emprise=(30, 30, 24), rayon=13,
          variant=0)
    cx, cz, rx, rz = LAC
    for i, (x, z, w, d, h, v) in enumerate(((cx - 5.75, cz + 8.25, 20, 14, 3, 0), (cx + 12.25, cz - 9.75, 14, 10, 4, 1))):
        place(b, "nature", "ile_herbeuse", (x, 0, z), yaw=0, group=f"Alien/Ile{i}", variant=v, largeur=w, profondeur=d,
              hauteur=h, emprise=(w, d, h))
    domes = ((-124, -292, 8, 1), (-120, -344, 7, 2), (-84, -340, 6, 3), (92, -352, 7, 1),
             (124, -350, 6, 2))
    for i, (x, z, r, v) in enumerate(domes):
        place(b, "batiments", "maison_alien", (x, 0, z), yaw=face_couloir(x), group=f"Alien/Dome{i}", variant=v, rayon=r,
              emprise=(2 * r + 4, 2 * r + 4, r + 4))
    arbres = ((-80, -284, 0, 26), (-104, -288, 0, 30), (-78, -326, 0, 22), (-128, -316, 0, 34), (-66, -344, 0, 28),
              (78, -290, 0, 30), (126, -296, 0, 36), (78, -338, 0, 24), (104, -344, 0, 26), (cx - 5.75, cz + 8.25, 3.15, 18),
              (cx + 12.25, cz - 9.75, 4.15, 14))
    for i, (x, z, y, h) in enumerate(arbres):
        place(b, "nature", "arbre_boule", (x, y, z), group=f"Alien/Arbre{i:02d}", variant=i % 4, hauteur=h, emprise=(8, 8, h))
    for i, (x, z, h) in enumerate(((-122, -330, 44), (126, -330, 40))):
        place(b, "nature", "pic_rocheux", (x, 0, z), group=f"Alien/Pic{i}", variant=i + 2, hauteur=h, teinte="sable",
              emprise=(12, 12, h))
    rng = np.random.default_rng(23)
    k = 0
    for i in range(40):
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
    """Derrière le temple et les tribunes : arbres boules, dômes, pitons de sable, nuages dorés sur les gradins."""
    arbres = ((-98, -356, 0, 30), (-100, -414, 0, 38), (-126, -386, 0, 32),
              (80, -360, 0, 26), (88, -414, 0, 34), (124, -384, 0, 42), (122, -428, 0, 30), (100, -394, 0, 22))
    for i, (x, z, y, h) in enumerate(arbres):
        place(b, "nature", "arbre_boule", (x, y, z), group=f"Abords/ArbrePlace{i}", variant=(i + 1) % 4, hauteur=h,
              emprise=(8, 8, h))
    for i, (x, z, r, v) in enumerate(((96, -374, 7, 3), (100.25, -410, 8, 0), (-118, -404, 6, 1))):
        place(b, "batiments", "maison_alien", (x, 0, z), yaw=face_couloir(x), group=f"Abords/DomePlace{i}", variant=v,
              rayon=r, emprise=(2 * r + 4, 2 * r + 4, r + 4))
    for i, (x, z, h) in enumerate(((-112, -374, 60), (112, -394, 52))):
        place(b, "nature", "pic_rocheux", (x, 0, z), group=f"Abords/PicPlace{i}", variant=(i + 1) % 4, hauteur=h,
              teinte="sable", emprise=(12, 12, h))
    # nuages dorés posés sur les gradins extérieurs des falaises et au pied de l'arche (cadrent l'horizon)
    for i, (x, z, w, d, h) in enumerate(NUAGES):
        s = -1 if x < 0 else 1
        # posé sur le plus haut des gradins couverts : il repose dessus et déborde au-dessus des plus bas
        hs = [h_falaise(s, zz, xx) for zz in (z - w / 2 + 1, z - w / 4, z, z + w / 4, z + w / 2 - 1)
              for xx in (abs(x) - d / 2 + 1, abs(x), abs(x) + d / 2 - 1)]
        y = max(hs)
        place(b, "arche", "nuages_dores", (x, y, z), yaw=face_couloir(x), group=f"Abords/Nuages{i}", variant=i % 3,
              largeur=w, profondeur=d, hauteur=h, emprise=(w, d, h))
    for i, (x, z, w, d, h) in enumerate(((-84, -429, 36, 12, 16), (86, -429.5, 32, 12, 18))):
        place(b, "arche", "nuages_dores", (x, 0, z), yaw=180, group=f"Abords/NuagesArche{i}", variant=(i + 1) % 3,
              largeur=w, profondeur=d, hauteur=h, emprise=(w, d, h))


def arche_finale(b: Builder) -> None:
    place(b, "arche", "arche_finale", (0, 0, Z_ARCHE), group="Monuments/Arche", emprise=(2 * X_FOND, PROF_ARCHE, 96),
          portique=PASSAGE / 2, centre_z=-PROF_ARCHE / 2, passage=PASSAGE, largeur=2 * X_FOND, profondeur=PROF_ARCHE,
          hauteur=96, variant=0)


# ---------------------------------------------------------------------------
# Repères, découpage, contrôles
# ---------------------------------------------------------------------------

def reperes(b: Builder) -> None:
    """Pièces invisibles utiles au jeu : zone des œufs (sur l'arène), entrée, sortie, couloir."""
    inv = dict(transparency=1.0, collide=False, shadow=False)
    with b.group("Reperes"):
        b.box((-AX_ARENE, H_ARENE, Z_PLACE - AZ_ARENE), (AX_ARENE, H_ARENE + 1, Z_PLACE + AZ_ARENE), "#ffffff",
              name="ZoneOeufs", **inv)
        b.box((-DEMI_COULOIR, 0, Z_PORTE + 18), (DEMI_COULOIR, 1, Z_PORTE + 24), "#ffffff", name="Entree", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE - 4), (DEMI_COULOIR, 1, Z_SORTIE + 2), "#ffffff", name="Sortie", **inv)
        b.box((-DEMI_COULOIR, 0, Z_SORTIE), (DEMI_COULOIR, 1, Z_PORTE), "#ffffff", name="Couloir", **inv)


def decouper(b: Builder, prefixes=("Sol/", "Bordures/", "Monuments/Arche", "Monuments/Porte"), taille: float = 64) -> None:
    """Range les pièces des grands ensembles dans des sous-modèles de 64 × 64 studs (streaming Roblox)."""
    for p in b.parts:
        if p.group.startswith(prefixes):
            i, j = math.floor(p.pos[0] / taille), math.floor(p.pos[2] / taille)
            racine = "/".join(p.group.split("/")[:2])
            reste = p.group[len(racine):]
            p.group = f"{racine}/Bloc_{i:+d}_{j:+d}{reste}"


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
    friche(b)
    planete(b)
    place_selection(b)
    abords_place(b)
    arche_finale(b)
    reperes(b)
    decouper(b)
    return b


def _aabb(p):
    R = np.asarray(p.rot).reshape(3, 3)
    half = np.abs(R) @ (np.asarray(p.size) / 2)
    return np.asarray(p.pos) - half, np.asarray(p.pos) + half


_bornes = _aabb


def couloir_libre(b: Builder) -> list:
    """Liste ce qui encombre le couloir de course au sol (|x| < 45, hors sol et repères)."""
    gene = []
    for p in b.parts:
        if not p.collide or p.group.startswith(("Sol", "Reperes")):
            continue
        lo, hi = _aabb(p)
        if lo[0] < DEMI_COULOIR - 0.05 and hi[0] > -DEMI_COULOIR + 0.05 and lo[1] < 12 and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            gene.append((p.group, p.name, [round(v, 1) for v in lo], [round(v, 1) for v in hi]))
    return gene


def trop_bas_au_dessus(b: Builder, y_min: float = 30.0) -> list:
    """Pièces au-dessus du couloir (|x| < 46) mais sous `y_min` (la caméra Roblox sauterait en passant dessous)."""
    out = []
    for p in b.parts:
        if p.group.startswith(("Sol", "Reperes")):
            continue
        lo, hi = _aabb(p)
        if lo[0] < X_LIBRE_HAUT - 0.05 and hi[0] > -X_LIBRE_HAUT + 0.05 and lo[1] < y_min and hi[1] > 12 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name, round(lo[1], 1)))
    return out


def decor_dans_couloir(b: Builder) -> list:
    """Détails sans collision posés dans le couloir au-dessus du sol (hors traces d'impact peintes)."""
    out = []
    for p in b.parts:
        if p.collide or p.group.startswith(("Sol", "Reperes", "Details/Impact", "Details/Rosace")) or p.transparency >= 1:
            continue
        lo, hi = _aabb(p)
        if lo[0] < DEMI_COULOIR - 0.05 and hi[0] > -DEMI_COULOIR + 0.05 and lo[1] < 12 and hi[1] > 0.3 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name))
    return out


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
            if racine in ("Reperes",) or p.name in ("Eau", "FondEau") or p.group.startswith(("Details/Impact",
                                                                                                  "Details/Rosace")):
                continue
            lo, hi = _aabb(p)
            if racine == "Sol" and hi[1] <= 0.6:
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
                      "trop_bas_au_dessus_du_couloir": bas[:20], "decor_dans_couloir": deco[:20]}, ensure_ascii=False))
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
