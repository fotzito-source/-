#!/usr/bin/env python3
"""Plan de la zone Dragon Ball (campagne terrestre, terres de combat, planète extraterrestre) en style stud.

Repère Roblox (Y en haut, 1 unité = 1 stud) :
- le couloir de course occupe x ∈ [-32, 32], bordé de trottoirs jusqu'à |x| = 42 ;
- on entre sous la grande porte de temple en z = 0 et on court vers -Z :
    1. campagne terrestre (0 → -146) : village de maisons-dômes blanches à bandes colorées, palmiers,
       dojo et pagode, falaises orange en strates couronnées d'herbe, cascades ;
    2. terres de combat (-146 → -290) : plaine verte trouée de terre kaki, mesas aux flancs violets,
       cratères, et un pont de roche naturel qui enjambe le couloir (z = -222, dessous à 34 studs) ;
    3. planète extraterrestre (-290 → -436) : herbe bleu-vert, canaux et lac turquoise, îlots aux bords
       de sable, arbres « boules », dômes blancs, vaisseau rond sur pattes, nuages dorés à l'horizon ;
    4. place des œufs = arène d'arts martiaux carrée (68 × 68, centre z = -392), temple aux toits orange
       à gauche, tribunes à droite, fanions au-dessus (≥ 34 studs) ;
    5. arche de roche géante (façade z = -436) : le couloir passe dessous et sort vers la zone suivante (z = -470).
- des falaises ferment les côtés (|x| ≥ 124) : orange puis violettes puis sable ocre.

    python zone.py                     # écrit build/parts.json (aucune dépendance à Blender)
    python zone.py --stats             # nombre de pièces par groupe
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
from textures import glyph_mask, mask_rects  # noqa: E402

# ---------------------------------------------------------------------------
# Dimensions (studs)
# ---------------------------------------------------------------------------
DEMI_COULOIR = 32
X_BORD = 42              # fin des trottoirs
X_FACADE = 44            # avant des premières maisons
X_FALAISE = 124          # début des falaises latérales
X_FOND = 200
Z_APPROCHE = 40          # sol devant la porte (côté apparition)
Z_PORTE = 0
Z_FIN_VILLAGE = -146     # fin de la campagne terrestre
Z_PONT = -222            # pont de roche au-dessus du couloir
Z_ALIEN = -290           # début de la planète extraterrestre
Z_PLACE = -392           # centre de l'arène (place des œufs)
A_ARENE = 34             # demi-côté de l'arène carrée
R_PLACE = A_ARENE
H_ARENE = 1.0            # dessus de l'arène (rampes de 5 studs devant et derrière)
L_RAMPE = 5
Z_ARCHE = -436           # façade de l'arche finale
PROF_ARCHE = 34
Z_SORTIE = Z_ARCHE - PROF_ARCHE   # -470 : le couloir continue vers la zone suivante
H_FANIONS = 38           # cordons de fanions au-dessus du couloir (creux compris ≥ 34)

VERSION = "0.1"


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

    `portique` (demi-largeur du passage) : le bloc d'attente d'un monument qui enjambe le couloir est dessiné
    en portique (deux piles et un tablier au-dessus de 34 studs). `centre_z` décale le bloc d'attente en z local."""
    f = _asset(module, fn)
    with b.at(pos, yaw=yaw, group=group):
        if f is not None:
            n0 = len(b.parts)
            try:
                return f(b, **params) or {}
            except NotImplementedError:
                del b.parts[n0:]
        w, d, h = emprise
        z0, z1 = centre_z - d / 2, centre_z + d / 2
        kw = dict(transparency=0.5, name=f"ATTENTE_{module}_{fn}")
        if portique:
            for s in (-1, 1):
                b.box((s * portique, 0, z0), (s * w / 2, h, z1), "#ff4fd8", **kw)
            b.box((-portique, 34, z0), (portique, h, z1), "#ff4fd8", **kw)
        else:
            b.box((-w / 2, 0, z0), (w / 2, h, z1), "#ff4fd8", **kw)
        return {"emprise": (w, d), "hauteur": h}


def face_couloir(x: float) -> float:
    """Rotation qui tourne l'avant d'un asset (-Z local) vers le couloir."""
    return -90.0 if x < 0 else 90.0


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
    case ; les cases de même couleur sont fusionnées en rectangles."""
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


def damier(a, bcol, taille: float):
    a, bcol = (hexrgb(v) if isinstance(v, str) else v for v in (a, bcol))
    return lambda x, z: a if (math.floor(x / taille) + math.floor(z / taille)) % 2 == 0 else bcol


def dans_arene(x: float, z: float) -> bool:
    """Arène carrée, ses rampes et ses marches latérales (dessinées à part, en relief)."""
    return abs(x) < A_ARENE + 2 and abs(z - Z_PLACE) < A_ARENE + L_RAMPE


def est_eau(x: float, z: float) -> bool:
    """Canaux turquoise le long du couloir (jamais dedans) et lac à droite, sur la planète extraterrestre."""
    ax = abs(x)
    if 46 <= ax <= 60 and -352 <= z <= -298:
        return True
    if x > 0:
        if ((x - 92) / 26) ** 2 + ((z + 322) / 25) ** 2 < 1:
            return True
        if 58 <= x <= 70 and -316 <= z <= -306:
            return True
    return False


def sol_couloir(b: Builder) -> None:
    dl, dlf = c("dalle"), c("dalle_fonce")
    pc = c("pave_clair")
    kaki, kakic, kakif, ocre = c("kaki"), c("kaki_clair"), c("kaki_fonce"), c("ocre")
    sab, sabc, ha = c("sable"), c("sable_clair"), c("herbe_alien_claire")
    vio, viof, nuit = c("mesa_violet"), c("mesa_violet_fonce"), c("mesa_nuit")

    def couloir(x, z):
        if dans_arene(x, z):
            return None
        ax = abs(x)
        if z < Z_ARCHE + 2:                 # passage sous l'arche : grandes dalles violettes
            if ax > DEMI_COULOIR - 2:
                return vio
            return viof if math.floor(z / 8) % 2 else nuit
        sec = section(x, z)
        if sec == "terre":                  # route du village : dalles crème, frise terre cuite au bord
            if DEMI_COULOIR - 4 <= ax < DEMI_COULOIR - 2:
                return pc
            return dl if (math.floor(x / 16) + math.floor(z / 12)) % 2 == 0 else dlf
        if sec == "friche":                 # terre battue kaki, taches ocre et sombres
            n = bruit(x, z, 18, 3)
            if n > 0.7:
                return ocre
            if n < 0.28:
                return kakif
            return kaki
        # planète extraterrestre : allée de sable clair, bords envahis d'herbe bleu-vert
        if ax > DEMI_COULOIR - 3 and bruit(x, z, 4, 7) > 0.5:
            return ha
        return sabc if math.floor(z / 6) % 4 == 0 else sab

    def trottoir(x, z):
        if dans_arene(x, z):
            return None
        ax = abs(x)
        if z < Z_ARCHE + 2:
            return vio if math.floor(z / 4) % 2 else shade(vio, 0.94)
        if abs(z - Z_PLACE) < A_ARENE + 8:      # parvis de l'arène : bandes de dalles
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

    z_fin = Z_SORTIE - 4
    with b.group("Sol/Couloir"):
        sol_pixel(b, -DEMI_COULOIR, DEMI_COULOIR, z_fin, Z_APPROCHE, 4, couloir)
    with b.group("Sol/Trottoirs"):
        for s in (-1, 1):
            xa, xb = sorted((s * DEMI_COULOIR, s * X_BORD))
            sol_pixel(b, xa, xb, z_fin, Z_APPROCHE, 2, trottoir)


def sol_cotes(b: Builder) -> None:
    """Sol entre les trottoirs et les falaises : herbe vive, plaine trouée de terre, herbe bleu-vert et eau."""
    h, hc, hf = c("herbe"), c("herbe_claire"), c("herbe_fonce")
    kaki, ocre = c("kaki"), c("ocre")
    ha, hac, haf, sab = c("herbe_alien"), c("herbe_alien_claire"), c("herbe_alien_fonce"), c("sable")

    def couleur(x, z):
        ax = abs(x)
        if z < Z_ARCHE + 2:
            return None                       # l'arche couvre tout son sol
        if est_eau(x, z):
            return None
        if ax < 50 and abs(z - Z_PLACE) < A_ARENE + 8:
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
        n = bruit(x, z, 22, 41)
        if n > 0.7:
            return sab
        return haf if n < 0.3 else ha

    def eau(x, z):
        if z < Z_ARCHE + 2 or not est_eau(x, z):
            return None
        return c("eau_claire") if (math.floor(z / 2) % 9 == 0 and bruit(x, z, 6, 5) > 0.5) else c("eau")

    with b.group("Sol/Cotes"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_FALAISE))
            # grandes cases (8) dans la campagne et la friche, cases de 4 sur la planète (rives des canaux)
            sol_pixel(b, xa, xb, Z_ALIEN + 6, Z_APPROCHE + 2, 8, couleur)
            sol_pixel(b, xa, xb, Z_ARCHE, Z_ALIEN + 6, 4, couleur)
    with b.group("Sol/Eau"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_BORD, s * X_FALAISE))
            sol_pixel(b, xa, xb, Z_ARCHE, Z_APPROCHE, 2, eau, y_haut=-0.4, epaisseur=1.6, studs="none",
                      transparency=0.12, name="Eau")


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
    """Arène carrée en dalles de pierre, en léger relief (dessus à 1 stud) : rampes dans le couloir,
    marches sur les côtés, grand 武 rouge au centre, bordure sombre, poteaux d'angle à flamme."""
    glyphe = glyph_mask("武", 22, font="brush", bold=0.6)
    a_, af, j = c("arene"), c("arene_fonce"), c("arene_joint")
    pc, rouge, orr = c("pierre_claire"), c("laque_rouge"), c("or")

    def motif(x, z):
        dz = z - Z_PLACE
        if abs(x) > A_ARENE - 2 or abs(dz) > A_ARENE - 2:
            return j
        d = math.hypot(x, dz)
        if d < 14:
            gi, gj = int(math.floor(x + 11)), int(math.floor(dz + 11))
            if 0 <= gi < 22 and 0 <= gj < 22 and glyphe[gj, gi]:
                return rouge
            return pc
        if d < 15.5:
            return orr
        return a_ if (math.floor(x / 8) + math.floor(dz / 8)) % 2 == 0 else af

    with b.group("Sol/Arene"):
        sol_pixel(b, -A_ARENE, A_ARENE, Z_PLACE - A_ARENE, Z_PLACE + A_ARENE, 1, motif, y_haut=H_ARENE, epaisseur=2.0,
                  name="Arene")
        # rampes (pente douce dans le couloir) : la pente descend vers l'extérieur de l'arène
        b.wedge((-A_ARENE, 0, Z_PLACE + A_ARENE), (A_ARENE, H_ARENE, Z_PLACE + A_ARENE + L_RAMPE), af, down="+z",
                studs="top", name="Rampe")
        b.wedge((-A_ARENE, 0, Z_PLACE - A_ARENE - L_RAMPE), (A_ARENE, H_ARENE, Z_PLACE - A_ARENE), af, down="-z",
                studs="top", name="Rampe")
        # sol sous les rampes (le couloir est laissé vide à cet endroit)
        for z0, z1 in ((Z_PLACE + A_ARENE, Z_PLACE + A_ARENE + L_RAMPE), (Z_PLACE - A_ARENE - L_RAMPE, Z_PLACE - A_ARENE)):
            b.box((-A_ARENE, -1, z0), (A_ARENE, 0, z1), c("sable"), studs="none", name="SousRampe")
        # marches sur les côtés (hors couloir)
        for s in (-1, 1):
            xa, xb = sorted((s * A_ARENE, s * (A_ARENE + 2)))
            b.box((xa, -1, Z_PLACE - A_ARENE - L_RAMPE), (xb, H_ARENE / 2, Z_PLACE + A_ARENE + L_RAMPE), c("pierre_fonce"),
                  studs="top", name="Marche")
    for i, (sx, sz) in enumerate(((-1, 1), (1, 1), (-1, -1), (1, -1))):
        place(b, "mobilier", "poteau_arene", (sx * (A_ARENE + 4), 0, Z_PLACE + sz * (A_ARENE + 4)),
              group=f"Place/Poteau{i}", variant=0, hauteur=7, emprise=(3, 3, 11))


def place_selection(b: Builder) -> None:
    """Autour de l'arène : temple d'arts martiaux à gauche, tribunes et gong à droite, fanions, bannières."""
    place(b, "temple", "temple_tournoi", (-(X_FACADE + 2 + 17), 0, Z_PLACE), yaw=-90, group="Place/Temple",
          emprise=(60, 34, 38), largeur=60, profondeur=34)
    for i, dz in enumerate((18, -18)):
        place(b, "temple", "tribune", (X_FACADE + 2 + 7, 0, Z_PLACE + dz), yaw=90, group=f"Place/Tribune{i}",
              emprise=(28, 14, 12), variant=i, longueur=28, rangs=5)
    place(b, "mobilier", "gong", (X_FACADE + 0.5, 0, Z_PLACE), yaw=90, group="Place/Gong", emprise=(9, 3, 8))
    # bannières le long des côtés de l'arène (hors couloir, sur le parvis)
    textes = ("武", "気", "修行", "武道")
    for s in (-1, 1):
        for i, dz in enumerate((-26, -9, 9, 26)):
            x = s * 39.5
            place(b, "mobilier", "banniere", (x, 0, Z_PLACE + dz), yaw=face_couloir(x), group=f"Place/Banniere{'GD'[s > 0]}{i}",
                  texte=textes[(i + (s > 0)) % 4], variant=(i + (s > 0)) % 4, hauteur=10, emprise=(3, 2, 11))
    # cordons de fanions au-dessus de l'arène : mâts rouges sur les trottoirs, cordons à ≥ 34 studs
    fan = _asset("mobilier", "guirlande_fanions")
    for i, dz in enumerate((22, -22)):
        z = Z_PLACE + dz
        with b.group(f"Place/Fanions{i}"):
            for s in (-1, 1):
                with b.at((s * 41, 0, z)):
                    b.box((-0.9, 0, -0.9), (0.9, 1.2, 0.9), c("pierre_fonce"), studs="top", name="Pied")
                    b.box((-0.45, 1.2, -0.45), (0.45, H_FANIONS + 2, 0.45), c("laque_rouge"), name="Mat")
                    b.box((-0.7, H_FANIONS + 2, -0.7), (0.7, H_FANIONS + 2.6, 0.7), c("or"), name="Chapeau")
            if fan:
                fan(b, (-40.5, H_FANIONS, z), (40.5, H_FANIONS, z), n=11, creux=2.5, variant=i)


# ---------------------------------------------------------------------------
# Falaises latérales (orange, puis violettes, puis sable ocre)
# ---------------------------------------------------------------------------

STYLES_FALAISE = {
    # tons des gradins, strate, herbe du sommet, hauteur de base, surcroît du 2e et du 3e gradin
    "terre": (("falaise_orange", "falaise_orange_claire", "falaise_orange_fonce"), "falaise_brune", "herbe", (14, 20), (10, 16), (22, 32)),
    "friche": (("mesa_violet", "mesa_violet_fonce", "mesa_violet_clair"), "mesa_rose", "herbe", (20, 30), (12, 20), (26, 40)),
    "alien": (("falaise_sable", "falaise_sable_claire", "falaise_sable_fonce"), "falaise_sable_fonce", "herbe_alien", (5, 9), (6, 10), (10, 16)),
}
CASCADES = {(-1, 5), (-1, 10), (1, 7), (1, 9)}   # (côté, tranche) : cascades dans la campagne terrestre
HAUT_FALAISE: dict = {}                          # (côté, tranche) → (z centre, (h1, h2, h3), style)


def bordures(b: Builder) -> None:
    """Falaises en gradins (tranches de 16 studs) qui ferment la vallée ; dessus en herbe débordante, strates."""
    rng = np.random.default_rng(5)
    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        z = Z_APPROCHE
        k = 0
        while z > Z_ARCHE + 0.01:
            l = min(16, z - Z_ARCHE)
            zc = z - l / 2
            style = "terre" if zc > Z_FIN_VILLAGE else ("friche" if zc > Z_ALIEN else "alien")
            tons, strate, herbe, base, plus2, plus3 = STYLES_FALAISE[style]
            h1 = rng.uniform(*base) + 3 * math.sin(k * 0.9)
            if (s, k) in CASCADES:
                h1 = 26
            if style == "friche" and k % 3 == 1:
                h1 *= 0.6                               # encoche : on voit les mesas du fond
            h2 = h1 + rng.uniform(*plus2)
            h3 = h2 + rng.uniform(*plus3)
            gradins = ((X_FALAISE, X_FALAISE + 16, h1), (X_FALAISE + 16, X_FALAISE + 40, h2), (X_FALAISE + 40, X_FOND, h3))
            HAUT_FALAISE[(s, k)] = (zc, (round(h1), round(h2), round(h3)), style)
            with b.group(f"Bordures/{cote}"):
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
                        sa, sb = sorted((s * (xa_ - 0.3), s * xa_))
                        b.box((sa, ys, z - l + 0.5), (sb, ys + 1.2, z - 0.5), c(strate), collide=False, name="Strate")
                    # coulures d'herbe sous le chapeau
                    if gi < 2 and (k + gi) % 2 == 0:
                        zq = z - l * float(rng.uniform(0.2, 0.7))
                        lg = float(rng.uniform(1.5, 3.5))
                        ca, cb = sorted((s * (xa_ - 0.6), s * (xa_ - 0.1)))
                        b.box((ca, hg - 1.2 - lg, zq - 1.2), (cb, hg - 1.2, zq + 1.2), c(herbe), collide=False, name="Coulure")
            z -= l
            k += 1


# ---------------------------------------------------------------------------
# Campagne terrestre : porte, village de dômes, dojo, pagodes, cascades
# ---------------------------------------------------------------------------

# (fonction, rayon ou None, largeur le long de z, profondeur le long de x, centre z, paramètres)
RANGEE_GAUCHE = [
    ("maison_dome", 9, 22, 24, -26, {"variant": 0}),
    ("boutique_dome", None, 16, 16, -54, {"variant": 0}),
    ("maison_dome", 8, 28, 22, -82, {"variant": 2}),
    ("maison_dome", 10, 24, 26, -113, {"variant": 3}),
    ("maison_dome", 7, 18, 20, -138, {"variant": 1}),
]
RANGEE_DROITE = [
    ("maison_dome", 8, 20, 22, -24, {"variant": 1}),
    ("maison_dome", 10, 24, 26, -54, {"variant": 4}),
    ("boutique_dome", None, 16, 16, -84, {"variant": 1}),
    ("maison_dome", 9, 22, 24, -110, {"variant": 0}),
    ("maison_dome", 7, 26, 20, -137, {"variant": 2}),
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
    place(b, "temple", "porte_temple", (0, 0, Z_PORTE), group="Monuments/Porte", emprise=(2 * X_FALAISE, 16, 50),
          portique=38, ouverture=76, hauteur=50, mur=X_FALAISE)
    for s in (-1, 1):
        place(b, "temple", "statue_gardien", (s * 50, 0, Z_PORTE + 10), yaw=180, group=f"Monuments/Gardien{'GD'[s > 0]}",
              variant=int(s > 0), emprise=(7, 9, 12))
        for i, (dx, dz) in enumerate(((62, 14), (84, 28), (106, 12))):
            place(b, "nature", "palmier", (s * dx, 0, Z_PORTE + dz), yaw=(i * 70 + (s > 0) * 35) % 360,
                  group=f"Abords/Palmier{'GD'[s > 0]}{i}", variant=i % 4, hauteur=13 + 3 * (i % 2), emprise=(12, 12, 16))
        for i, (dx, dz) in enumerate(((72, 32), (96, 34))):
            place(b, "nature", "arbre_rond", (s * dx, 0, Z_PORTE + dz), group=f"Abords/Arbre{'GD'[s > 0]}{i}",
                  variant=i, hauteur=12, emprise=(10, 10, 14))
        place(b, "mobilier", "lanterne_chinoise", (s * 41, 0, Z_PORTE + 14), yaw=face_couloir(s), group=f"Abords/Lanterne{'GD'[s > 0]}",
              variant=1, emprise=(2, 5, 9))


def village(b: Builder):
    poses_g = rangee(b, -1, RANGEE_GAUCHE)
    poses_d = rangee(b, 1, RANGEE_DROITE)
    # deuxième plan : dojo et terrain d'entraînement à gauche, pagode et dômes à droite
    place(b, "temple", "dojo", (-96, 0, -50), yaw=-90, group="Village/Dojo", emprise=(24, 18, 16), largeur=24, profondeur=18)
    for i, (x, z, fn, kw) in enumerate(((-78, -36, "mannequin_bois", {}), (-78, -44, "mannequin_bois", {"variant": 1}),
                                        (-78, -62, "jarres", {"variant": 2}), (-80, -70, "panneau", {"texte": "道場", "variant": 0}),
                                        (-80, -28, "banniere", {"texte": "修行", "variant": 1}))):
        place(b, "mobilier", fn, (x, 0, z), yaw=-90, group=f"Village/Entrainement{i}", emprise=(3, 3, 6), **kw)
    place(b, "temple", "pagode", (100, 0, -40), group="Village/Pagode", emprise=(12, 12, 30), etages=3)
    place(b, "temple", "pagode", (-104, 0, -118), group="Village/Pagode2", variant=1, emprise=(12, 12, 26), etages=2)
    for i, (x, z, r, v) in enumerate(((84, -84, 7, 1), (92, -126, 8, 3), (-84, -96, 6, 0))):
        place(b, "batiments", "maison_dome", (x, 0, z), yaw=face_couloir(x), group=f"Village/Arriere{i}", variant=v, rayon=r,
              emprise=(2 * r + 4, 2 * r + 6, r + 6))
    for i, (x, z, yaw, v) in enumerate(((-62, -41.5, 90, 0), (60, -71, -90, 1), (76, -100, 200, 2))):
        place(b, "batiments", "voiture_volante", (x, 0, z), yaw=yaw, group=f"Village/Voiture{i}", variant=v,
              emprise=(5, 9, 4))
    # palmiers et arbres ronds entre les maisons et au second plan
    palmiers = ((-48, -41.5), (-48, -65), (-48, -98.5), (-48, -127), (48, -38), (48, -71), (48, -95.5), (48, -122.5),
                (-70, -14), (74, -18), (-118, -60), (114, -96), (-74, -140), (78, -142))
    for i, (x, z) in enumerate(palmiers):
        place(b, "nature", "palmier", (x, 0, z), yaw=(i * 53) % 360, group=f"Village/Palmier{i:02d}", variant=i % 4,
              hauteur=12 + (i % 3) * 2, emprise=(12, 12, 16))
    for i, (x, z) in enumerate(((-112, -20), (-92, -82), (110, -60), (104, -14), (86, -110), (-116, -140))):
        place(b, "nature", "arbre_rond", (x, 0, z), group=f"Village/Arbre{i}", variant=i % 3, hauteur=11 + (i % 3) * 2,
              emprise=(10, 10, 14))
    for i, (x, z, h) in enumerate(((-108, -88, 34), (112, -24, 42), (110, -130, 30))):
        place(b, "nature", "pic_rocheux", (x, 0, z), group=f"Village/Pic{i}", variant=i, hauteur=h, teinte="orange",
              emprise=(10, 10, h))
    # cascades au pied des falaises orange
    for (s, k), (zc, hs, style) in sorted(HAUT_FALAISE.items()):
        h1 = hs[0]
        if (s, k) in CASCADES:
            x = s * X_FALAISE
            place(b, "nature", "cascade", (x, 0, zc), yaw=face_couloir(x), group=f"Village/Cascade{'GD'[s > 0]}{k}",
                  variant=k % 3, hauteur=h1, largeur=8, emprise=(12, 10, h1))
    return poses_g, poses_d


def details_village(b: Builder, poses_g, poses_d) -> None:
    """Lampadaires, bancs, terrasses, distributeurs, jardinières sur les trottoirs (jamais dans le couloir)."""
    for s in (-1, 1):
        for i, z in enumerate((-12, -44, -76, -108, -140)):
            zz = z - (16 if s > 0 else 0) * (i % 2)
            x = s * 39.5
            place(b, "mobilier", "lampadaire_rond", (x, 0, zz), yaw=face_couloir(x), group=f"Details/Lampadaire{'GD'[s > 0]}{i}",
                  variant=0 if i % 2 == 0 else 2, emprise=(2, 4, 11))
    props = [("banc", {"variant": 0}), ("jardiniere", {"variant": 0}), ("distributeur", {"variant": 0}),
             ("parasol_table", {"variant": 1}), ("jardiniere", {"variant": 1}), ("banc", {"variant": 3}),
             ("caisses", {"variant": 1}), ("distributeur", {"variant": 1}), ("caisses", {"variant": 0})]
    occupe = {s: [z - (16 if s > 0 else 0) * (i % 2) for i, z in enumerate((-12, -44, -76, -108, -140))] + [-60, -122]
              for s in (-1, 1)}   # lampadaires et mâts de fanions
    k = 0
    for s, poses in ((-1, poses_g), (1, poses_d)):
        for (x, zc, larg, prof, info) in poses:
            fn, kw = props[k % len(props)]
            xp = s * (38.5 if fn == "parasol_table" else 39.5)
            zp = zc - 6
            for _ in range(3):
                if min(abs(zp - zo) for zo in occupe[s]) >= 6:
                    break
                zp += 7
            occupe[s].append(zp)
            place(b, "mobilier", fn, (xp, 0, zp), yaw=face_couloir(xp), group=f"Details/{fn}{k}", emprise=(4, 3, 5), **kw)
            k += 1
    # cordons de fanions au-dessus de la rue (≥ 34 studs), mâts blancs « tech »
    fan = _asset("mobilier", "guirlande_fanions")
    for i, z in enumerate((-60, -122)):
        with b.group(f"Details/Fanions{i}"):
            for s in (-1, 1):
                with b.at((s * 41, 0, z)):
                    b.box((-0.9, 0, -0.9), (0.9, 1.0, 0.9), c("gris_tech"), studs="top", name="Pied")
                    b.cyl((0, 1.0 + (H_FANIONS + 1) / 2, 0), 0.4, H_FANIONS + 1, c("blanc_dome"), name="Mat")
                    b.cyl((0, H_FANIONS + 2.3, 0), 0.6, 0.6, c("bande_orange" if i == 0 else "bande_bleue"), name="Chapeau")
            if fan:
                fan(b, (-40.6, H_FANIONS, z), (40.6, H_FANIONS, z), n=11, creux=2.5, variant=i + 1)


# ---------------------------------------------------------------------------
# Terres de combat : mesas violettes, pont de roche, cratères
# ---------------------------------------------------------------------------

def friche(b: Builder) -> None:
    place(b, "arche", "pont_rocheux", (0, 0, Z_PONT), group="Monuments/Pont", emprise=(140, 20, 48), portique=40,
          portee=80, hauteur=36, epaisseur=12, largeur_pile=30)
    mesas = (  # (x, z, largeur le long du couloir (z), profondeur vers l'extérieur (x), hauteur, variante)
        (-64, -168, 30, 26, 22, 0), (66, -176, 34, 28, 26, 1), (-70, -268, 36, 30, 30, 2), (70, -278, 30, 26, 20, 3),
        (-102, -196, 34, 30, 44, 1), (104, -204, 36, 34, 52, 0), (-98, -246, 30, 28, 38, 3), (100, -252, 30, 26, 40, 2),
        (-104, -160, 24, 20, 30, 2),
    )
    for i, (x, z, w, d, h, v) in enumerate(mesas):
        place(b, "nature", "mesa", (x, 0, z), yaw=face_couloir(x), group=f"Friche/Mesa{i:02d}", variant=v,
              largeur=w, profondeur=d, hauteur=h, emprise=(w, d, h))
    for i, (x, z, r) in enumerate(((-56, -200, 9), (60, -250, 12), (-52, -241, 7), (82, -236, 8))):
        place(b, "nature", "cratere", (x, 0, z), group=f"Friche/Cratere{i}", variant=i, rayon=r, emprise=(2 * r + 4, 2 * r + 4, 3))
    for i, (x, z, h) in enumerate(((88, -158, 34), (-86, -222, 46), (92, -290, 30))):
        place(b, "nature", "pic_rocheux", (x, 0, z), group=f"Friche/Pic{i}", variant=i + 1, hauteur=h, teinte="violet",
              emprise=(10, 10, h))
    rng = np.random.default_rng(17)
    for i in range(18):
        s = -1 if i % 2 else 1
        near = i % 3 == 0
        x = s * (float(rng.uniform(37, 40.5)) if near else float(rng.uniform(46, 116)))
        z = float(rng.uniform(-288, -150))
        if abs(z - Z_PONT) < 16 and abs(x) < 76:
            z -= 22
        place(b, "nature", "rocher", (x, 0, z), yaw=float(rng.uniform(0, 360)), group=f"Friche/Rocher{i:02d}", variant=i % 4,
              taille=0.5 if near else float(rng.uniform(0.8, 1.6)), teinte="violet" if i % 3 else "gris", emprise=(4, 4, 3))
    for i in range(10):
        s = -1 if i % 2 else 1
        x, z = s * float(rng.uniform(46, 112)), float(rng.uniform(-286, -152))
        place(b, "nature", "buisson", (x, 0, z), group=f"Friche/Buisson{i}", variant=i % 3, teinte="vert", emprise=(4, 4, 3))
    impact_sol(b, -8, -186, 9, 0)
    impact_sol(b, 12, -262, 7, 1)


# ---------------------------------------------------------------------------
# Planète extraterrestre : eau, îlots, arbres boules, dômes, vaisseau, nuages dorés
# ---------------------------------------------------------------------------

def planete(b: Builder) -> None:
    place(b, "arche", "vaisseau_rond", (-90, 0, -324), yaw=-120, group="Alien/Vaisseau", emprise=(30, 30, 24), rayon=13)
    for i, (x, z, w, d, h, v) in enumerate(((90, -314, 20, 16, 3, 0), (102, -336, 14, 12, 5, 1), (-53, -326, 8, 12, 2, 2))):
        place(b, "nature", "ile_herbeuse", (x, 0, z), yaw=0, group=f"Alien/Ile{i}", variant=v, largeur=w, profondeur=d,
              hauteur=h, emprise=(w, d, h))
    domes = ((-72, -296, 5, 0), (-114, -296, 8, 1), (-112, -356, 7, 2), (86, -372, 7, 1), (102, -398, 8, 0), (-66, -354, 5, 3))
    for i, (x, z, r, v) in enumerate(domes):
        place(b, "batiments", "maison_alien", (x, 0, z), yaw=face_couloir(x), group=f"Alien/Dome{i}", variant=v, rayon=r,
              emprise=(2 * r + 4, 2 * r + 4, r + 4))
    arbres = ((-66, -284, 0, 26), (-100, -282, 0, 30), (-80, -346, 0, 22), (-104, -380, 0, 38), (-112, -414, 0, 30),
              (82, -292, 0, 30), (90, -316, 3, 24), (104, -334, 5, 20), (114, -300, 0, 36), (76, -352, 0, 22),
              (74, -392, 0, 26), (78, -424, 0, 34), (112, -380, 0, 42), (116, -424, 0, 30), (-53, -326, 2, 14),
              (-120, -432, 0, 36))
    for i, (x, z, y, h) in enumerate(arbres):
        place(b, "nature", "arbre_boule", (x, y, z), group=f"Alien/Arbre{i:02d}", variant=i % 4, hauteur=h, emprise=(8, 8, h))
    for i, (x, z, h) in enumerate(((-96, -398, 64), (110, -352, 50), (-120, -320, 44))):
        place(b, "nature", "pic_rocheux", (x, 0, z), group=f"Alien/Pic{i}", variant=i + 2, hauteur=h, teinte="sable",
              emprise=(12, 12, h))
    rng = np.random.default_rng(23)
    for i in range(10):
        s = -1 if i % 2 else 1
        x, z = s * float(rng.uniform(64, 118)), float(rng.uniform(-430, -292))
        if est_eau(x, z) or (s < 0 and -428 < z < -356 and abs(x) < 82):
            continue
        place(b, "nature", "buisson", (x, 0, z), group=f"Alien/Buisson{i}", variant=i % 3, teinte="alien", emprise=(4, 4, 3))
    # nuages dorés posés sur les gradins extérieurs et au pied de l'arche (cadrent l'horizon)
    for i, (x, z, w, d, h) in enumerate(((-150, -330, 50, 30, 22), (156, -372, 56, 30, 26), (-160, -410, 60, 34, 30),
                                         (150, -424, 50, 26, 24), (-96, -432, 36, 14, 18), (100, -432, 40, 14, 20))):
        # posé sur les gradins : base au plus bas des gradins couverts (le nuage s'enfonce dans les plus hauts)
        y = 0.0
        if abs(x) + d / 2 > X_FALAISE:
            s = -1 if x < 0 else 1
            hs = []
            for (sk, k), (zc, hk, style) in HAUT_FALAISE.items():
                if sk == s and abs(zc - z) < w / 2 + 8:
                    for (xa_, xb_), hg in zip(((X_FALAISE, X_FALAISE + 16), (X_FALAISE + 16, X_FALAISE + 40), (X_FALAISE + 40, X_FOND)), hk):
                        if xa_ < abs(x) + d / 2 and xb_ > abs(x) - d / 2:
                            hs.append(hg)
            y = float(min(hs)) if hs else 0.0
        place(b, "arche", "nuages_dores", (x, y, z), yaw=face_couloir(x), group=f"Alien/Nuages{i}", variant=i % 3,
              largeur=w, profondeur=d, hauteur=h, emprise=(w, d, h))


def arche_finale(b: Builder) -> None:
    place(b, "arche", "arche_finale", (0, 0, Z_ARCHE), group="Monuments/Arche", emprise=(2 * X_FOND, PROF_ARCHE, 96),
          portique=40, centre_z=-PROF_ARCHE / 2, passage=80, largeur=2 * X_FOND, profondeur=PROF_ARCHE, hauteur=96)


# ---------------------------------------------------------------------------
# Repères, découpage, contrôles
# ---------------------------------------------------------------------------

def reperes(b: Builder) -> None:
    """Pièces invisibles utiles au jeu : zone des œufs (sur l'arène), entrée, sortie, couloir."""
    inv = dict(transparency=1.0, collide=False, shadow=False)
    with b.group("Reperes"):
        b.box((-A_ARENE, H_ARENE, Z_PLACE - A_ARENE), (A_ARENE, H_ARENE + 1, Z_PLACE + A_ARENE), "#ffffff", name="ZoneOeufs", **inv)
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
    HAUT_FALAISE.clear()
    sol_couloir(b)
    sol_cotes(b)
    arene(b)
    bordures(b)
    porte_et_abords(b)
    poses_g, poses_d = village(b)
    details_village(b, poses_g, poses_d)
    friche(b)
    planete(b)
    place_selection(b)
    arche_finale(b)
    reperes(b)
    decouper(b)
    return b


def _bornes(p):
    R = np.asarray(p.rot).reshape(3, 3)
    half = np.abs(R) @ (np.asarray(p.size) / 2)
    return np.asarray(p.pos) - half, np.asarray(p.pos) + half


def couloir_libre(b: Builder) -> list:
    """Liste ce qui encombre le couloir de course au sol (hors sol et repères)."""
    gene = []
    for p in b.parts:
        if not p.collide or p.group.startswith(("Sol", "Reperes")):
            continue
        lo, hi = _bornes(p)
        if lo[0] < DEMI_COULOIR - 0.05 and hi[0] > -DEMI_COULOIR + 0.05 and lo[1] < 12 and hi[1] > 0.05 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            gene.append((p.group, p.name, [round(v, 1) for v in lo], [round(v, 1) for v in hi]))
    return gene


def trop_bas_au_dessus(b: Builder, y_min: float = 30.0) -> list:
    """Pièces au-dessus du couloir (|x| < 33) mais sous `y_min` (la caméra Roblox sauterait en passant dessous)."""
    out = []
    for p in b.parts:
        if p.group.startswith(("Sol", "Reperes")):
            continue
        lo, hi = _bornes(p)
        if lo[0] < DEMI_COULOIR + 1 and hi[0] > -DEMI_COULOIR - 1 and lo[1] < y_min and hi[1] > 12 \
                and hi[2] > Z_SORTIE and lo[2] < Z_APPROCHE:
            out.append((p.group, p.name, round(lo[1], 1)))
    return out


def meta() -> dict:
    return {"nom": "ZoneDragonBall", "version": VERSION, "largeur_couloir": 2 * DEMI_COULOIR,
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
                      "trop_bas_au_dessus_du_couloir": bas[:20]}, ensure_ascii=False))
    if args.stats:
        for k, v in b.stats().items():
            print(f"{v:6d}  {k}")


if __name__ == "__main__":
    main()
