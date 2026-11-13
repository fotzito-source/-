"""Ciel de la carte « île du futur » (CarteEgghead) : l'œuf-laboratoire fêlé sur son cumulus (le repère de la carte),
son câble et sa station d'ancrage, les nacelles volantes, les pièces d'or, le dirigeable-baleine et les cumulus
lointains. Fiche : SPECS.md § assets/ciel.py ; recettes : STYLE.md § 6 (C01, C02, C03, C16, C12/M18, C14, C15).

    python apercu.py assets.ciel:oeuf_labo --no-ground --res 1200x675 --samples 12
    python apercu.py assets.ciel:nacelle --variant 1 --params '{"rayon": 7}'
    python apercu.py assets.ciel:piece_or --variant 1
    python apercu.py assets.ciel:dirigeable
    python apercu.py assets.ciel:cumulus --variant 2 --no-ground
    python apercu.py assets.ciel:cable --no-ground

L'œuf (C01, réglé pour être lu d'en bas, à 1 100 studs, depuis l'apparition) : coquille violet → mauve → rose en
5 bandes (ventre large, haut arrondi), cassure basse (69 % de la hauteur) à 14 grosses dents roses en zigzag, posées
au ras de la coquille et penchées vers l'axe, devant un dôme intérieur violet sombre qui prolonge la forme de l'œuf
(la silhouette reste celle d'un œuf) et porte une grille de lumière atténuée ; anneau de données bleu à pixels autour
du ventre ; arc lâche de 18 cubes bleu clair et lavande au-dessus ; cumulus en couches (dessous bosselé, couronne
basse, couronne moyenne, coussin qui serre l'œuf, gros flocons derrière), plus bas devant pour laisser voir le ventre ;
deux bandes lumineuses interrompues qui serrent le nuage (ellipses), sans texte ni chiffres.

Conventions (CONVENTIONS.md) : origine d'un objet volant = son centre (l'œuf : le pied de sa coquille, le cumulus :
le centre de son dessous plat) ; avant = -Z local ; tout est sans collision (sauf la station d'ancrage) ; le nuage et
l'œuf ne projettent pas d'ombre (CastShadow false). Aucun texte, aucun visage, aucun personnage : la coquille est
lisse, les « données » de l'anneau sont des pixels, les nacelles sont vides (siège et console seulement).
N'importe que kit, palette, numpy et math (les cotes de pose viennent de plan.py, lues par carte.py).
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, rot_x, rot_y, rot_z, varier
from palette import c

# =====================================================================================================================
# L'œuf-laboratoire (C01) — toutes les cotes en unités k = 1 (multipliées par `echelle` à la construction)
# =====================================================================================================================

# Coquille : 5 ellipsoïdes (centre y, rayon horizontal, demi-hauteur, couleur) ; à chaque hauteur on voit celui qui
# dépasse. Trouvés par le calcul : profil à moins de 1,5 de l'œuf de la bible (ventre le plus large vers y 85, haut
# arrondi), bandes violet → mauve → rose avec deux tons de passage, angles de croisement de 10° (raccords nets).
#   violet 0 → 88 · violet-mauve 88 → 103 · mauve 103 → 118 · mauve-rose 118 → 134 · rose 134 → cassure (138)
COQUILLE = (
    (84.0, 74.71, 84.00, "violet"),
    (92.5, 74.93, 50.06, "violet_mauve"),
    (91.5, 74.05, 79.10, "mauve"),
    (101.0, 71.01, 91.22, "mauve_rose"),
    (124.0, 66.80, 75.04, "rose"),
)
# Cassure : plus basse que dans la bible (138 au lieu de 168) pour que l'intérieur sombre se lise depuis la carte
# (on regarde l'œuf d'en bas, à 20-28°). Le haut de l'œuf est un dôme sombre : la coquille rose montée de
# DOME_DELTA et resserrée pour en sortir exactement à la cassure (même forme : la silhouette reste celle d'un œuf).
CASSURE_Y = 138.0
DOME_DELTA = 6.0
# Dents du zigzag : plaques triangulaires (2 coins) roses, debout sur un polygone de 14 côtés, la face extérieure
# au ras de la coquille au pied, penchées de DENT_PENTE vers l'axe (tangentes au dôme à la cassure : le dôme reste
# derrière elles sur toute leur hauteur), pied enfoncé de DENT_ENFONCE dans la coquille.
DENTS = 14
DENT_EP = 2.6
DENT_PENTE = 7.0
DENT_SAILLIE = 0.6
DENT_ENFONCE = 5.0
# hauteurs des dents au-dessus de la cassure, la n° 0 à l'avant (-Z local), puis dans le sens trigonométrique vu du
# dessus (n° 3-4 côté -X local, n° 7 à l'arrière, n° 10-11 côté +X) : une haute, une basse, les plus hautes vers
# l'avant ; décalage du sommet le
# long de la dent (fraction de la demi-largeur) : cassure irrégulière mais nette
DENT_H = (42.0, 28.0, 38.0, 26.0, 32.0, 24.0, 29.0, 22.0, 27.0, 23.0, 31.0, 25.0, 36.0, 30.0)
DENT_SOMMET = (0.0, 0.2, -0.14, 0.22, -0.2, 0.12, -0.16, 0.2, -0.1, 0.16, -0.22, 0.12, -0.18, 0.08)
# Grille de lumière du dôme : 7 méridiens (tranches d'ellipsoïde, un dans l'axe de chaque dent) et 3 parallèles
# (disques dont seul le bord dépasse), Neon violet atténué (« faible lueur »)
GRILLE_EP = 0.8
GRILLE_SAILLIE = 0.3
GRILLE_PARALLELES = (0.36, 0.6, 0.8)    # hauteurs, en fraction de la hauteur du dôme au-dessus de la cassure
GRILLE_ATTENUATION = 0.5                # part de la couleur de l'intérieur mêlée au Neon
# Anneau de données : ruban vertical en 6 arcs de 48° (trous de 12°), incliné, + « pixels » sur son bord haut
ANNEAU_R = 112.0
ANNEAU_Y = 62.0
ANNEAU_HAUT = 7.0          # hauteur du ruban
ANNEAU_EP = 1.2            # épaisseur du ruban
ANNEAU_INCLINAISON = (4.0, 5.0)   # (autour de X, autour de Z), degrés : l'avant (côté carte) un peu plus haut
ANNEAU_PIXEL = 5.0
# angle (0 = +X, 90 = avant), nombre de pixels en escalier, rang du pixel Neon (-1 : aucun)
ANNEAU_PIXELS = ((28, 2, -1), (40, 1, -1), (86, 3, 1), (100, 1, -1), (150, 2, -1), (208, 1, 0), (222, 2, -1),
                 (268, 1, -1), (330, 2, -1), (342, 1, -1))
# Cubes de données : arc lâche au-dessus de l'œuf, dans un plan penché vers l'arrière
CUBES_CENTRE = (0.0, 150.0, 24.0)
CUBES_R = 124.0
CUBES_PENTE = 24.0          # le plan de l'arc penche vers l'arrière (+Z local) : l'arc ne cache pas la cassure
CUBES_ARC = (-10.0, 170.0)  # angles dans le plan de l'arc (0 = +X, 90 = sommet) : arc asymétrique (finition)
# position de chaque cube le long de l'arc (0 → 1) : 3 grappes séparées par 2 trous, pas un diadème régulier
CUBES_T = (0.0, 0.05, 0.09, 0.15, 0.2, 0.36, 0.4, 0.45, 0.5, 0.56, 0.6, 0.76, 0.8, 0.85, 0.89, 0.94, 0.97, 1.0)
CUBES_COULEURS = ("cube_bleu", "lavande", "cube_bleu", "blanc_labo", "cube_bleu", "cyan", "lavande", "cube_bleu",
                  "cube_bleu", "lavande", "cube_bleu", "cyan", "blanc_labo", "cube_bleu", "lavande", "cube_bleu",
                  "lavande", "cube_bleu")
# Cumulus de l'œuf : dessous presque plat (base nuage_ombre), couronne basse, couronne moyenne, couronne qui serre
# l'œuf, gros flocons derrière l'œuf, petits flocons aux deux bouts
NUAGE_BAS = -55.0
NUAGE_BASE = ((300.0, 42.0, 220.0), -30.0)       # diamètres, centre y (dessous du cœur du nuage, caché)
# Dessous : lobes très aplatis de tailles et de hauteurs inégales (vu d'en bas, un dessous bosselé de cumulus et
# non une assiette) : (x, z, dessous y, largeur, profondeur, hauteur)
NUAGE_LOBES = ((-70.0, -40.0, -55.0, 150.0, 110.0, 34.0), (60.0, -52.0, -53.0, 140.0, 100.0, 30.0),
               (-10.0, 30.0, -54.0, 160.0, 120.0, 36.0), (95.0, 40.0, -51.0, 120.0, 96.0, 28.0),
               (-110.0, 46.0, -52.0, 118.0, 90.0, 30.0), (10.0, -78.0, -50.0, 120.0, 70.0, 26.0),
               (-150.0, -10.0, -50.0, 90.0, 80.0, 26.0))
# Bandes du nuage : sous sa plus grande largeur (vers y -24), là où il rentre déjà vers son dessous : leur ombre
# tombe sur le dessous du nuage, pas en trait sur ses flancs
BANDES_NUAGE = ((-30.0, "cyan"), (-44.0, "bleu_roi"))   # hauteur, couleur ; rayon : bord du nuage + marge
BANDES_MARGE = 10.0


def _couleurs_oeuf() -> dict:
    v, m, r = c("oeuf_violet"), c("oeuf_mauve"), c("oeuf_rose")
    return {"violet": v, "violet_mauve": mix(v, m, 0.6), "mauve": mix(m, r, 0.2), "mauve_rose": mix(m, r, 0.6),
            "rose": r,
            "interieur": c("oeuf_interieur"),
            "grille": mix(c("neon_violet"), c("oeuf_interieur"), GRILLE_ATTENUATION)}


def _r_ell(y: float, cy: float, a: float, h: float) -> float:
    u = (y - cy) / h
    return a * math.sqrt(1 - u * u) if abs(u) < 1 else 0.0


def rayon_coquille(y: float) -> float:
    """Rayon extérieur de la coquille à la hauteur y (k = 1)."""
    return max(_r_ell(y, cy, a, h) for cy, a, h, _ in COQUILLE)


def dome_interieur() -> tuple:
    """(centre y, rayon, demi-hauteur) du dôme sombre (k = 1) : la coquille rose (cr, ar, hr) montée de DOME_DELTA,
    de même forme (a/h constant), resserrée pour couper la coquille rose exactement à CASSURE_Y. Sous la cassure il
    reste dans la coquille, au-dessus il la recouvre."""
    cr, ar, hr, _ = COQUILLE[-1]
    lam = ar * ar / (hr * hr)
    d = DOME_DELTA
    ad = math.sqrt(ar * ar - lam * d * (2 * (CASSURE_Y - cr) - d))
    return cr + d, ad, ad / math.sqrt(lam)


def _dent(b, phi: float, apo: float, y0: float, larg: float, decal: float, h: float, ep: float, pente: float,
          couleur, **kw) -> None:
    """Dent de la cassure : triangle de deux coins dos à dos, dont le plan médian passe par le point `apo` × rayon à
    la hauteur y0 (pied), penché de `pente` degrés vers l'axe. `phi` : angle du milieu du côté (0 = +X, 90 = -Z) ;
    `larg` : largeur du pied ; `decal` : décalage du sommet le long du côté ; `h` : longueur dans le plan."""
    ph = math.radians(phi)
    radial = np.array([math.cos(ph), 0.0, -math.sin(ph)])
    X = np.array([-math.sin(ph), 0.0, -math.cos(ph)])        # tangente (sens des phi croissants)
    lam = math.radians(pente)
    Y = math.cos(lam) * np.array([0.0, 1.0, 0.0]) - math.sin(lam) * radial
    Z = math.sin(lam) * np.array([0.0, 1.0, 0.0]) + math.cos(lam) * radial
    pied = np.array([0.0, y0, 0.0]) + apo * radial + decal * X
    wd, wg = larg / 2 - decal, larg / 2 + decal               # largeurs à droite (+X) et à gauche du sommet
    b.part("wedge", (ep, h, wd), pied + X * (wd / 2) + Y * (h / 2), np.column_stack([Z, Y, -X]), couleur,
           name="Dent", **kw)
    # la moitié gauche est un rien plus mince : ses faces ne sont jamais dans le plan de celles de la droite
    b.part("wedge", (ep * 0.99, h, wg), pied - X * (wg / 2) + Y * (h / 2), np.column_stack([-Z, Y, X]), couleur,
           name="Dent", **kw)


def geometrie_dents() -> list:
    """Dents en k = 1 : liste de dicts (phi, pied y, apothème du plan médian au pied, largeur, décalage, longueur,
    sommet y, rayon extérieur au pied et au sommet) — sert à la construction et aux contrôles."""
    r_c = rayon_coquille(CASSURE_Y)
    t = math.tan(math.radians(DENT_PENTE))
    cosl = math.cos(math.radians(DENT_PENTE))
    out = []
    for i in range(DENTS):
        phi = 90.0 + 360.0 * i / DENTS
        y0 = CASSURE_Y - DENT_ENFONCE
        # face extérieure au milieu du côté : r_c + saillie à la cassure, plus loin de l'axe en descendant (pente)
        r_ext0 = r_c + DENT_SAILLIE + DENT_ENFONCE * t
        apo = r_ext0 - DENT_EP / (2 * cosl)                 # plan médian, mesuré horizontalement à y0
        larg = 2 * r_ext0 * math.tan(math.pi / DENTS)       # les faces extérieures se rejoignent aux coins
        hy = DENT_H[i % len(DENT_H)] + DENT_ENFONCE        # hauteur verticale du pied au sommet
        out.append({"phi": phi, "y0": y0, "apo": apo, "larg": larg,
                    "decal": DENT_SOMMET[i % len(DENT_SOMMET)] * larg / 2, "h": hy / cosl,
                    "sommet": y0 + hy, "r_ext0": r_ext0, "pente": DENT_PENTE})
    return out


def flocons_oeuf() -> list:
    """Flocons du cumulus de l'œuf en k = 1 : (centre, (dx, dy, dz), yaw, ton) ; ton 0 = nuage, 1 = nuage_ombre,
    2 = nuage_ombre éclairci.
    Dessous presque plat vers y -55, dessus en dôme autour de l'œuf (plus bas devant, côté carte, pour laisser voir
    le ventre de l'œuf), plus haut derrière ; tailles irrégulières (pas de collier de perles)."""
    rng = np.random.default_rng(404)
    out = []
    (bx, by, bz), byc = NUAGE_BASE
    out.append(((0.0, byc, 0.0), (bx, by, bz), 0.0, 1))
    for j, (x, z, yb, lx, lz, ly) in enumerate(NUAGE_LOBES):
        out.append(((x, yb + ly / 2, z), (lx, ly, lz), 25.0 * j - 40.0, 1 if j % 2 else 2))
    # couronne basse : 16 grands flocons aplatis, allongés le long de la couronne, dessous vers -53
    for i in range(16):
        t = 2 * math.pi * (i + 0.5) / 16 + rng.uniform(-0.06, 0.06)
        d = 80 + 10 * math.cos(2 * t) + rng.uniform(-10, 10)
        rr = 1.0 + rng.uniform(-0.06, 0.04)
        x, z = 118 * rr * math.cos(t), 92 * rr * math.sin(t)
        ap = rng.uniform(0.56, 0.66)
        y = NUAGE_BAS + 2 + d * ap / 2 + rng.uniform(0, 9)
        out.append(((x, y, z), (d * rng.uniform(1.1, 1.25), d * ap, d * 0.96), math.degrees(-t) + 90, 0))
    # couronne moyenne : 12 flocons ; avant (z < 0) plus bas que l'arrière
    for i in range(12):
        t = 2 * math.pi * i / 12 + 0.26 + rng.uniform(-0.08, 0.08)
        d = 74 + rng.uniform(-12, 12)
        x, z = 98 * math.cos(t), 72 * math.sin(t)
        y = 4 + 7 * math.sin(t) + rng.uniform(-3, 3)
        out.append(((x, y, z), (d * 1.1, d * rng.uniform(0.76, 0.86), d), math.degrees(-t) + 90, 0))
    # couronne haute : 10 flocons de tailles inégales qui serrent l'œuf (l'œuf est « posé dedans ») ; devant
    # (côté carte) plus bas, plus plats et plus larges : un coussin, pas une boule devant le ventre de l'œuf
    tailles = (58, 44, 52, 64, 46, 56, 50, 62, 54, 48)
    for i in range(10):
        t = 2 * math.pi * i / 10 + 0.15 + rng.uniform(-0.08, 0.08)
        d = tailles[i] + rng.uniform(-3, 3)
        avant = max(0.0, -math.sin(t))            # 1 droit devant, 0 sur les côtés et derrière
        r = 70 + 0.25 * d + 6 * avant + rng.uniform(-3, 3)
        x, z = r * math.cos(t), r * math.sin(t)
        y = 17 + 6 * math.sin(t) + 0.12 * d - 7 * avant + rng.uniform(-2, 2)
        out.append(((x, y, z), (d * (1.12 + 0.3 * avant), d * (0.9 - 0.22 * avant), d), math.degrees(-t) + 90, 0))
    # gros flocons derrière l'œuf : ils dépassent de part et d'autre de la coquille vus de la carte
    for x, z, y, d in ((-66, 60, 30, 66), (60, 68, 36, 70), (-4, 90, 42, 62), (100, 26, 22, 56), (-102, 22, 20, 54)):
        out.append(((float(x), float(y), float(z)), (d * 1.05, d * 0.9, d), 0.0, 0))
    # gros flocons de flanc (finition) : le contour monte des bouts jusqu'à y ≈ +50 vers x ±120 : un cumulus bombé,
    # pas une soucoupe ; le devant (z < 0) reste bas sur le ventre de l'œuf
    for sx in (-1, 1):
        for x, y, z, d in ((125, 30, 5, 92), (95, 50, 35, 84)):
            out.append(((sx * x, float(y), float(z)), (d * 1.05, d * 0.85, d), sx * 15.0, 0))
    return out


def etendue_nuage(y: float) -> tuple:
    """Demi-étendues (x, z) du cumulus de l'œuf à la hauteur y (k = 1), flocons tournés compris."""
    ex = ez = 0.0
    for (x, cy, z), (dx, dy, dz), yaw, _ in flocons_oeuf():
        u = (y - cy) / (dy / 2)
        if abs(u) >= 1:
            continue
        f = math.sqrt(1 - u * u)
        a, cz = dx / 2 * f, dz / 2 * f
        w = math.radians(yaw)
        hx = math.hypot(a * math.cos(w), cz * math.sin(w))
        hz = math.hypot(a * math.sin(w), cz * math.cos(w))
        ex, ez = max(ex, abs(x) + hx), max(ez, abs(z) + hz)
    return ex, ez


def _cumulus_oeuf(b, k: float, kw: dict) -> int:
    blanc, ombre = c("nuage"), c("nuage_ombre")
    tons = (None, ombre, mix(ombre, blanc, 0.35))
    rng = np.random.default_rng(405)
    n0 = len(b.parts)
    for i, (ctr, taille, yaw, ton) in enumerate(flocons_oeuf()):
        col = tons[ton] if ton else varier(blanc, rng, 0.012)
        nom = "NuageBase" if i == 0 else "Nuage"
        b.ellipsoid(tuple(v * k for v in ctr), tuple(v * k for v in taille), col, rot=rot_y(yaw) if yaw else None,
                    name=nom, **kw)
    return len(b.parts) - n0


def ellipse_nuage(y: float, marge: float = 0.0) -> tuple:
    """Demi-axes (RX, RZ) de la plus petite ellipse (de mêmes proportions que l'étendue du nuage) qui entoure la
    coupe du cumulus de l'œuf à la hauteur y (k = 1), plus `marge` : la bande lumineuse la serre sans le toucher."""
    ex, ez = etendue_nuage(y)
    m = 1.0
    for (x, cy, z), (dx, dy, dz), yaw, _ in flocons_oeuf():
        u = (y - cy) / (dy / 2)
        if abs(u) >= 1:
            continue
        f = math.sqrt(1 - u * u)
        w = math.radians(yaw)
        for j in range(24):
            t = 2 * math.pi * j / 24
            lx, lz = dx / 2 * f * math.cos(t), dz / 2 * f * math.sin(t)
            px = x + lx * math.cos(w) + lz * math.sin(w)
            pz = z - lx * math.sin(w) + lz * math.cos(w)
            m = max(m, math.hypot(px / ex, pz / ez))
    return m * ex + marge, m * ez + marge


def _bande_ellipse(b, rx: float, rz: float, ep: float, larg: float, couleur, n: int = 40, *, runs: int = 8,
                   decale: float = 0.0, pixel=None, **kw) -> int:
    """Bande plate horizontale sur une ellipse (demi-axes rx, rz, dans le plan y = 0 du repère courant), en `runs`
    arcs interrompus : n segments, 1 sur 5 retiré. Segments tangents (cordes), allongés pour fermer les joints
    extérieurs ; épaisseurs alternées (+0,04) pour qu'aucun dessus ne se confonde avec celui du voisin.
    `pixel` : (couleur, matériau) d'un pixel posé sur le milieu de chaque arc. Renvoie le nombre de pièces."""
    n0 = len(b.parts)
    pas = 2 * math.pi / n
    par_run = n // runs

    def pt(t):
        return np.array([rx * math.cos(t), 0.0, -rz * math.sin(t)])

    def direction(t0, t1):
        d = pt(t1) - pt(t0)
        return d / np.linalg.norm(d)

    for r in range(runs):
        for j in range(par_run - 1):            # le dernier segment de chaque groupe est le trou
            i = r * par_run + j
            t0, t1 = decale + i * pas, decale + (i + 1) * pas
            p0, p1 = pt(t0), pt(t1)
            X = direction(t0, t1)
            # allongement à chaque bout : demi-largeur × tan(demi-angle de virage avec le segment voisin)
            def virage(ta, tb, tc):
                u, v = direction(ta, tb), direction(tb, tc)
                return math.acos(max(-1.0, min(1.0, float(u @ v))))
            e0 = larg / 2 * math.tan(virage(t0 - pas, t0, t1) / 2)
            e1 = larg / 2 * math.tan(virage(t0, t1, t1 + pas) / 2)
            L = float(np.linalg.norm(p1 - p0)) + e0 + e1
            ctr = (p0 + p1) / 2 + X * (e1 - e0) / 2
            Y = np.array([0.0, 1.0, 0.0])
            Z = np.cross(X, Y)
            b.part("block", (L, ep + 0.04 * (j % 2), larg), ctr, np.column_stack([X, Y, Z]), couleur, name="Bande",
                   **kw)
        if pixel is not None:
            tm = decale + (r * par_run + (par_run - 1) / 2) * pas
            X = direction(tm - 0.01, tm + 0.01)
            Y = np.array([0.0, 1.0, 0.0])
            pc, pm = pixel
            kwp = {cle: v for cle, v in kw.items() if cle != "material"}
            b.part("block", (6.0 * larg / 2.5, ep, larg + 0.6), pt(tm) * 0.995 + Y * (ep * 0.9),
                   np.column_stack([X, Y, np.cross(X, Y)]), pc, material=pm, name="Pixel", **kwp)
    return len(b.parts) - n0


def oeuf_labo(b, variant: int = 0, echelle: float = 1.6, **params) -> dict:
    """Le repère du ciel (C01) : œuf violet → mauve → rose, haut cassé en zigzag (14 dents roses) sur un dôme
    intérieur violet sombre quadrillé d'une faible lumière, anneau de données à pixels, arc de cubes, posé dans un
    gros cumulus ceinturé de deux bandes lumineuses interrompues.

    Origine : pied de la coquille (y = 0, enfoncé dans le nuage) ; avant (-Z local) : la face tournée vers la carte
    (plus grande dent, nuage plus bas). Tout sans collision ; nuage et œuf sans ombre.
    Pièces 237 (≤ 320), Neon 54 (≤ 90), transparentes 0. À k = 1,6 : œuf 240 × 327 (cassure à 221), nuage de -88 à
    112 (58 devant), bandes comprises 689 × 475, cubes jusqu'à 443."""
    k = float(echelle)
    col = _couleurs_oeuf()
    kw = {"collide": False, "shadow": False}

    # --- coquille --------------------------------------------------------------------------------------------
    with b.group("Coquille"):
        for cy, a, h, nom in COQUILLE:
            b.ellipsoid((0, cy * k, 0), (2 * a * k, 2 * h * k, 2 * a * k), col[nom], name="Coquille", **kw)

    # --- intérieur : dôme sombre et grille de lumière ------------------------------------------------------------
    cd, ad, hd = dome_interieur()
    s = GRILLE_SAILLIE
    with b.group("Interieur"):
        b.ellipsoid((0, cd * k, 0), (2 * ad * k, 2 * hd * k, 2 * ad * k), col["interieur"], name="Interieur", **kw)
        for i in range(DENTS // 2):          # un méridien dans l'axe de chaque dent (caché sous la dent à son pied)
            phi = 90.0 + 360.0 * i / DENTS
            b.ellipsoid((0, cd * k, 0), (GRILLE_EP * k, 2 * (hd + s) * k, 2 * (ad + s) * k), col["grille"],
                        rot=rot_y(90.0 + phi), material="Neon", name="Meridien", **kw)
        haut = cd + hd
        for f in GRILLE_PARALLELES:
            y = CASSURE_Y + (haut - CASSURE_Y) * f
            r = _r_ell(y, cd, ad, hd) + s
            b.cyl((0, y * k, 0), r * k, GRILLE_EP * k, col["grille"], material="Neon", name="Parallele", **kw)

    # --- cassure : 14 dents en zigzag ---------------------------------------------------------------------------
    with b.group("Cassure"):
        for d in geometrie_dents():
            _dent(b, d["phi"], d["apo"] * k, d["y0"] * k, d["larg"] * k, d["decal"] * k, d["h"] * k, DENT_EP * k,
                  d["pente"], col["rose"], **kw)

    # --- anneau de données : 6 arcs de 48° (trous de 12°), ruban bleu, pixels sur le bord haut -------------------
    ix, iz = ANNEAU_INCLINAISON
    with b.group("Anneau"):
        with b.at((0, ANNEAU_Y * k, 0), rot=rot_z(iz) @ rot_x(ix)):
            for j in range(6):
                b.anneau((0, 0, 0), ANNEAU_R * k, ANNEAU_HAUT * k, [c("bleu_roi"), c("bleu_nuit")], 36,
                         arc=48, depart=60 * j + 6, section="plat", largeur=ANNEAU_EP * k, name="Donnees", **kw)
            t = ANNEAU_PIXEL * k
            for th, n, neon_i in ANNEAU_PIXELS:
                for e in range(n):
                    a = math.radians(th + e * math.degrees(t / (ANNEAU_R * k)))
                    rad = np.array([math.cos(a), 0.0, -math.sin(a)])
                    yaw = math.degrees(a) + 90          # X local le long de l'anneau, Z local vers l'extérieur
                    y = (ANNEAU_HAUT / 2) * k + t * (e + 0.5) - 0.05 * k
                    neon = e == neon_i
                    b.boxc(tuple(rad * ANNEAU_R * k + np.array([0, y, 0])), (t, t, (ANNEAU_EP + 0.3) * k),
                           c("cyan") if neon else c("cube_bleu"), yaw=yaw, name="Pixel",
                           material="Neon" if neon else "SmoothPlastic", **kw)

    # --- cubes de données : arc lâche au-dessus de l'œuf ----------------------------------------------------------
    rng = np.random.default_rng(406)
    pente = math.radians(CUBES_PENTE)
    ex = np.array([1.0, 0.0, 0.0])
    ey = np.array([0.0, math.cos(pente), math.sin(pente)])
    ez = np.cross(ex, ey)
    ctr = np.array(CUBES_CENTRE)
    n = len(CUBES_COULEURS)
    with b.group("Cubes"):
        a0, a1 = CUBES_ARC
        for i, nom in enumerate(CUBES_COULEURS):
            t = CUBES_T[i] if i < len(CUBES_T) else i / (n - 1)
            th = math.radians(a0 + (a1 - a0) * t)
            r = CUBES_R + rng.uniform(-15, 15)
            p = ctr + r * (math.cos(th) * ex + math.sin(th) * ey) + rng.uniform(-8, 8) * ez
            cote = (5.0, 9.0, 16.0, 6.5, 12.0, 7.0, 14.0, 5.5, 10.0)[i % 9] + rng.uniform(-0.8, 0.8)
            R = rot_y(rng.uniform(0, 90)) @ rot_x(rng.uniform(10, 35)) @ rot_z(rng.uniform(10, 35))
            neon = nom == "cyan"
            b.part("block", (cote * k,) * 3, p * k, R, c(nom), material="Neon" if neon else "SmoothPlastic",
                   name="Cube", **kw)

    # --- cumulus ---------------------------------------------------------------------------------------------
    with b.group("Nuage"):
        _cumulus_oeuf(b, k, kw)

    # --- bandes lumineuses autour du nuage : ellipses qui le serrent, arcs interrompus (1 segment sur 5 retiré) --
    with b.group("Bandes"):
        for j, (y, nom) in enumerate(BANDES_NUAGE):
            rx, rz = ellipse_nuage(y, BANDES_MARGE)
            # inclinées de 8 à 10° en sens contraires (finition) : deux orbites qui croisent les flancs du cumulus,
            # à demi cachées dans les flocons, et non deux anneaux plats de soucoupe
            incl = rot_x(9 if j == 0 else -7) @ rot_z(-6 if j == 0 else 8)
            with b.at((0, y * k, 0), rot=incl):
                neon = nom == "cyan"
                _bande_ellipse(b, rx * k, rz * k, 1.2 * k, 2.5 * k, c(nom), 40, decale=math.radians(4.5 + 22.5 * j),
                               pixel=None if neon else (c("cyan"), "Neon"),
                               material="Neon" if neon else "SmoothPlastic", **kw)

    haut = max(cd + hd, max(d["sommet"] for d in geometrie_dents()))
    nuage_haut = max(ctr[1] + taille[1] / 2 for ctr, taille, _, _ in flocons_oeuf())
    rx, rz = ellipse_nuage(BANDES_NUAGE[1][0], BANDES_MARGE)
    return {"emprise": (round(2 * (rx + 2) * k, 1), round(2 * (rz + 2) * k, 1)),
            "hauteur": round(haut * k, 1),
            "nuage_bas": round(NUAGE_BAS * k, 1), "nuage_haut": round(nuage_haut * k, 1),
            "nuage_haut_devant": round(max(ctr[1] + taille[1] / 2 for ctr, taille, _, _ in flocons_oeuf()
                                          if ctr[2] < -40 and abs(ctr[0]) < 90) * k, 1),
            "oeuf_haut": round(haut * k, 1), "cassure": round(CASSURE_Y * k, 1),
            "cubes_haut": round((CUBES_CENTRE[1] + CUBES_R * math.cos(math.radians(CUBES_PENTE)) + 14) * k, 1)}


# =====================================================================================================================
# Câble et station d'ancrage
# =====================================================================================================================

def cable(b, variant: int = 0, depart=(-80, 216, -760), arrivee=(-80, 0, -560), **params) -> dict:
    """Câble de l'œuf (coordonnées de la carte : carte.py appelle avec b.at((0, 0, 0))) : `cyl_entre` R 1
    blanc_labo du dessous du nuage (`depart`, caché dans le nuage) au tambour d'une station d'ancrage posée sur
    son propre socle (`arrivee` = point au sol). Le câble part 24 au-delà de `depart` (bout bien dans le nuage).
    Perles Neon (neon_blanc, rouge) tous les 40, 7 au plus. Pièces 17-18 (≤ 22), Neon 7-8."""
    p0 = np.asarray(depart, float)
    a = np.asarray(arrivee, float)
    blanc = c("blanc_labo")
    with b.group("Station"):
        b.box((a[0] - 12, a[1] - 2, a[2] - 12), (a[0] + 12, a[1] + 0.4, a[2] + 12), c("sol_vert_clair"),
              studs="top", name="Socle")
        b.cyl((a[0], a[1] + 0.7, a[2]), 6.5, 0.6, c("dalle_labo"), studs="top", name="Plateau")
        b.cyl((a[0], a[1] + 3.95, a[2]), 3.0, 6.1, blanc, name="Tambour")
        b.cyl((a[0], a[1] + 6.2, a[2]), 3.4, 0.8, c("bleu_roi"), studs="top", name="Bague")
        b.cyl((a[0], a[1] + 2.0, a[2]), 3.25, 0.6, c("rouge"), name="Liseré", collide=False)
        for sx, sz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            b.wedge((a[0] + sx * 3 - 1.5 * abs(sz) - (0.5 if sx else 0), a[1] + 1.0, a[2] + sz * 3 - 1.5 * abs(sx)),
                    (a[0] + sx * 6 + 1.5 * abs(sz), a[1] + 3.0, a[2] + sz * 6 + 1.5 * abs(sx)), blanc,
                    down={(1, 0): "+x", (-1, 0): "-x", (0, 1): "+z", (0, -1): "-z"}[(sx, sz)], name="Contrefort")
        b.ball((a[0], a[1] + 7.3, a[2]), 0.9, c("cyan"), material="Neon", collide=False, shadow=False,
               name="Balise")
    top = a + np.array([0, 6.6, 0])
    u0 = (p0 - top) / float(np.linalg.norm(p0 - top))
    haut_cable = p0 + u0 * 24.0          # le bout du câble entre bien dans le nuage
    with b.group("Cable"):
        b.cyl_entre(haut_cable, top, 1.0, blanc, collide=False, name="Cable")
        L = float(np.linalg.norm(top - p0))
        u = (top - p0) / L
        n = min(7, int((L - 30) // 40) + 1)
        s0 = (L - 40 * (n - 1)) / 2
        for i in range(n):
            q = p0 + u * (s0 + 40 * i)
            b.ball(tuple(q), 1.5, c("neon_blanc") if i % 2 == 0 else c("rouge"), material="Neon", collide=False,
                   shadow=False, name="Perle")
    return {"emprise": (24, 24), "hauteur": round(float(p0[1] - a[1]), 1), "longueur": round(L, 1)}


# =====================================================================================================================
# Nacelles volantes (C02 bol bleu à bulle, C03 toupie, C16 blanche et orange)
# =====================================================================================================================

def nacelle(b, variant: int = 0, rayon: float = 7, inclinaison: float = 6, couleur=None, **params) -> dict:
    """Nacelle volante, origine en son centre, avant (-Z local) = sens de la marche, penchée de `inclinaison` vers
    l'avant. Variante 0 : bol bleu à bulle (C02) ; 1 : toupie (C03) ; 2 : blanche et orange à coupole (C16).
    Échelle rayon / 7 ; `couleur` (nom de palette) remplace la couleur de coque. Bulle de verre vide (siège et
    console), halo Neon cyan sous le plot. ≤ 12 pièces, 1 Neon, 1 verre."""
    s = float(rayon) / 7.0
    v = variant % 3
    kw = {"collide": False}
    verre = {"material": "Glass", "transparency": 0.5}
    with b.at((0, 0, 0), rot=rot_x(-float(inclinaison))):
        if v == 0:   # C02 bol bleu à bulle
            coque = c(couleur) if couleur else c("bleu_roi")
            b.ellipsoid((0, -2 * s, 0), (14 * s, 9 * s, 14 * s), coque, name="Coque", **kw)
            b.cyl((0, -1.6 * s, 0), 7.3 * s, 0.8 * s, c("jaune_citron"), name="Ceinture", **kw)
            b.cyl((0, -1.0 * s, 0), 7.2 * s, 0.6 * s, c("turquoise"), name="Ceinture", **kw)
            b.cyl((0, -0.4 * s, 0), 7.1 * s, 0.6 * s, c("orange"), name="Ceinture", **kw)
            b.cyl((0, 0.3 * s, 0), 6.5 * s, 0.6 * s, c("blanc_labo"), studs="top", name="Pont", **kw)
            b.ellipsoid((0, 0.6 * s, 0), (11 * s, 10 * s, 11 * s), c("verre"), name="Bulle", **verre, **kw)
            b.boxc((0, 1.6 * s, 1.2 * s), (2.4 * s, 2.0 * s, 2.0 * s), c("blanc_labo"), name="Siege", **kw)
            b.boxc((0, 1.4 * s, -2.6 * s), (3.2 * s, 1.6 * s, 1.0 * s), c("bleu_nuit"), name="Console", **kw)
            b.cyl((0, -7.0 * s, 0), 1.5 * s, 2.0 * s, c("bleu_nuit"), name="Plot", **kw)
            b.cyl((0, -8.15 * s, 0), 3.0 * s, 0.25 * s, c("cyan"), material="Neon", shadow=False, name="Halo", **kw)
            haut, bas = 5.6 * s, -8.3 * s
        elif v == 1:   # C03 toupie
            coque = c(couleur) if couleur else c("jaune_citron")
            b.ellipsoid((0, 1.5 * s, 0), (12 * s, 8 * s, 12 * s), coque, name="Coque", **kw)
            b.cyl((0, 5.9 * s, 0), 1.0 * s, 1.5 * s, c("rouge"), name="Pointe", **kw)
            b.ball((0, 7.0 * s, 0), 0.6 * s, c("rouge"), name="Pointe", **kw)
            b.cyl((0, 8.4 * s, 0), 0.15 * s, 2.0 * s, c("blanc_labo"), name="Antenne", shadow=False, **kw)
            b.ellipsoid((0, 0, 0), (13 * s, 5 * s, 13 * s), c("blanc_labo"), name="Ceinture", **kw)
            b.cyl((0, -0.4 * s, 0), 6.7 * s, 0.8 * s, c("bleu_roi"), name="Filet", **kw)
            b.cyl((0, 1.2 * s, 0), 6.3 * s, 0.5 * s, c("turquoise"), name="Filet", **kw)
            b.ellipsoid((0, -3.0 * s, 0), (8 * s, 6 * s, 8 * s), c("verre"), name="Bulbe", **verre, **kw)
            b.ball((0, -3.0 * s, 0), 1.5 * s, c("bleu_nuit"), name="Noyau", **kw)
            b.cyl((0, -6.4 * s, 0), 2.4 * s, 0.25 * s, c("cyan"), material="Neon", shadow=False, name="Halo", **kw)
            haut, bas = 9.4 * s, -6.5 * s
        else:   # C16 blanche et orange à coupole
            coque = c(couleur) if couleur else c("blanc_labo")
            b.ellipsoid((0, -1.5 * s, 0), (14 * s, 8 * s, 14 * s), coque, name="Coque", **kw)
            b.cyl((0, -1.2 * s, 0), 7.25 * s, 1.2 * s, c("orange"), name="Ceinture", **kw)
            b.cyl((0, -0.35 * s, 0), 6.9 * s, 0.5 * s, c("bleu_roi"), name="Filet", **kw)
            b.cyl((0, 0.3 * s, 0), 6.2 * s, 0.6 * s, c("blanc_labo"), studs="top", name="Pont", **kw)
            b.ellipsoid((0, 0.6 * s, 0), (10 * s, 9 * s, 10 * s), c("verre"), name="Coupole", **verre, **kw)
            b.boxc((0, 1.6 * s, 1.0 * s), (2.4 * s, 2.0 * s, 2.0 * s), c("orange"), name="Siege", **kw)
            b.boxc((0, 1.4 * s, -2.4 * s), (3.0 * s, 1.6 * s, 1.0 * s), c("bleu_nuit"), name="Console", **kw)
            b.cyl((0, -6.0 * s, 0), 1.6 * s, 1.6 * s, c("orange"), name="Plot", **kw)
            b.cyl((0, -6.95 * s, 0), 2.8 * s, 0.25 * s, c("cyan"), material="Neon", shadow=False, name="Halo", **kw)
            haut, bas = 5.1 * s, -7.1 * s
    return {"emprise": (round(14.6 * s, 1), round(14.6 * s, 1)), "hauteur": round(haut - bas, 1)}


# =====================================================================================================================
# Pièces d'or (M18 / C12)
# =====================================================================================================================

def piece_or(b, variant: int = 0, rayon: float = 6, **params) -> dict:
    """Pièce d'or géante, origine en son centre, faces normales à Z local (la ligne de pièces suit X local).
    Disque `or` R rayon ép 1,6 + face centrale `or_fonce` R 0,75 rayon ép 1,8 ; variante 1 : étoile en relief
    (5 rayons et un bouton, visibles des deux côtés). 2 pièces (8 en variante 1)."""
    r = float(rayon)
    kw = {"collide": False}
    b.cyl((0, 0, 0), r, 1.6, c("or"), axis="z", name="Piece", **kw)
    b.cyl((0, 0, 0), 0.75 * r, 1.8, c("or_fonce"), axis="z", name="Face", **kw)
    if variant % 2 == 1:
        L = 0.6 * r
        for i in range(5):
            a = math.radians(90 + 72 * i)
            ctr = (math.cos(a) * L / 2, math.sin(a) * L / 2, 0)
            b.part("block", (L, 0.2 * r, 2.0 + 0.03 * i), ctr, rot_z(math.degrees(a)), c("or"), name="Etoile", **kw)
        b.cyl((0, 0, 0), 0.22 * r, 2.3, c("or"), axis="z", name="Etoile", **kw)
    return {"emprise": (round(2 * r, 1), 2.3 if variant % 2 else 1.8), "hauteur": round(2 * r, 1)}


# =====================================================================================================================
# Dirigeable-baleine (générique)
# =====================================================================================================================

def _sur_ellipsoide(centre, demi, direction):
    """Point de la surface d'un ellipsoïde (centre, demi-axes) dans une direction, et normale extérieure."""
    d = np.asarray(direction, float)
    d = d / np.linalg.norm(d)
    a = np.asarray(demi, float)
    t = 1.0 / math.sqrt(float(np.sum((d / a) ** 2)))
    p = np.asarray(centre, float) + d * t
    n = (p - np.asarray(centre, float)) / a ** 2
    return p, n / np.linalg.norm(n)


def dirigeable(b, variant: int = 0, longueur: float = 90, **params) -> dict:
    """Dirigeable en forme de baleine générique, opaque, origine au centre, avant (-Z local) = la tête. Corps
    bleu_roi dessus / blanc_labo ventre (deux ellipsoïdes décalés), pédoncule, caudale à deux lobes (horizontale),
    deux pectorales, rangée de hublots sur chaque flanc, nacelle en gélule sous le ventre, deux hélices orange,
    feux Neon cyan. Ni œil, ni bouche, ni cicatrice. ≤ 60 pièces, ≤ 6 Neon."""
    k = float(longueur) / 90.0
    kw = {"collide": False}
    bleu, blanc, orange = c("bleu_roi"), c("blanc_labo"), c("orange")
    corps_c, corps_d = np.array([0, 0, -6.0]) * k, np.array([14.0, 13.0, 36.0]) * k
    with b.group("Corps"):
        b.ellipsoid(tuple(corps_c), tuple(2 * corps_d), bleu, name="Corps", **kw)
        b.ellipsoid((0, -4.6 * k, -6.5 * k), (26.4 * k, 19.0 * k, 68.0 * k), blanc, name="Ventre", **kw)
        b.ellipsoid((0, 0.8 * k, 30.0 * k), (12.0 * k, 11.0 * k, 34.0 * k), bleu, name="Pedoncule", **kw)
        for sx in (-1, 1):
            b.ellipsoid((sx * 8.5 * k, 1.2 * k, 46.5 * k), (20.0 * k, 2.2 * k, 9.5 * k), bleu,
                        rot=rot_y(sx * 28.0), name="Caudale", **kw)
            b.ellipsoid((sx * 13.5 * k, -6.0 * k, -14.0 * k), (15.0 * k, 1.8 * k, 6.5 * k), blanc,
                        rot=rot_y(sx * 32.0) @ rot_z(-sx * 24.0), name="Pectorale", **kw)
        # petite dorsale arrondie
        b.ellipsoid((0, 12.2 * k, 6.0 * k), (1.8 * k, 6.0 * k, 10.0 * k), bleu, rot=rot_x(-25), name="Dorsale",
                    **kw)
    with b.group("Hublots"):
        for sx in (-1, 1):
            for i in range(5):
                z = (-26.0 + 9.0 * i) * k                     # le long du corps, de la tête vers le pédoncule
                dz, dy = (z - corps_c[2]) / corps_d[2], 1.2 * k / corps_d[1]
                x = corps_d[0] * math.sqrt(max(0.05, 1 - dz * dz - dy * dy))
                dirn = np.array([sx * x, 1.2 * k, z - corps_c[2]]) - np.array([0, corps_c[1], 0])
                p, n = _sur_ellipsoide(corps_c, corps_d, dirn)
                R = np.column_stack([n, np.array([0, 1.0, 0]) - n * n[1], np.cross(n, np.array([0, 1.0, 0]) - n * n[1])])
                R[:, 1] /= np.linalg.norm(R[:, 1])
                R[:, 2] = np.cross(R[:, 0], R[:, 1])
                b.part("cyl", (1.2 * k, 3.6 * k, 3.6 * k), tuple(p + n * 0.2 * k), R, orange, name="Cadre", **kw)
                b.part("cyl", (1.2 * k, 2.4 * k, 2.4 * k), tuple(p + n * 0.35 * k), R, c("hublot"), name="Hublot",
                       **kw)
    with b.group("Nacelle"):
        yg = -16.6 * k
        b.cyl((0, yg, -8 * k), 3.4 * k, 14.0 * k, c("jaune_or"), axis="z", name="Gelule", **kw)
        for sz in (-1, 1):
            b.ball((0, yg, -8 * k + sz * 7.0 * k), 3.4 * k, c("jaune_or"), name="Gelule", **kw)
        for sx in (-1, 1):
            b.boxc((sx * 3.1 * k, yg + 0.6 * k, -8 * k), (0.6 * k, 1.6 * k, 11.0 * k), c("hublot"), name="Vitres",
                   **kw)
        for sz in (-1, 1):
            b.cyl_entre((0, yg + 2.0 * k, -8 * k + sz * 4 * k), (0, -10.0 * k, -8 * k + sz * 5 * k), 0.6 * k,
                        blanc, name="Suspente", **kw)
        b.ball((0, yg - 3.5 * k, -8 * k), 0.8 * k, c("cyan"), material="Neon", shadow=False, name="Feu", **kw)
        for sx in (-1, 1):       # hélices orange de part et d'autre de la gélule
            hx = sx * 6.2 * k
            b.cyl((hx, yg, -1.2 * k), 1.0 * k, 3.0 * k, blanc, axis="z", name="Moyeu", **kw)
            b.cyl_entre((sx * 3.0 * k, yg, -2.2 * k), (hx, yg, -2.2 * k), 0.5 * k, blanc, name="Bras", **kw)
            for j, ang in enumerate((20.0, 110.0)):
                b.part("block", (6.6 * k, 0.9 * k, (0.4 + 0.06 * j) * k), (hx, yg, 0.4 * k), rot_z(ang + sx * 15),
                       orange, name="Pale", **kw)
    with b.group("Feux"):
        for sx in (-1, 1):
            b.ball((sx * 17.0 * k, 1.2 * k, 50.5 * k), 0.9 * k, c("cyan"), material="Neon", shadow=False,
                   name="Feu", **kw)
            b.ball((sx * 19.2 * k, -9.6 * k, -11.5 * k), 0.8 * k, c("cyan"), material="Neon", shadow=False,
                   name="Feu", **kw)
    # boîte mesurée (k = 1) : x ±21,3 (pectorales, feux), z -42 → 55,4 (caudale), y -20,9 → 17 (gélule → dorsale)
    return {"emprise": (round(42.6 * k, 1), round(97.4 * k, 1)), "hauteur": round(37.9 * k, 1)}


# =====================================================================================================================
# Cumulus lointains (C15)
# =====================================================================================================================

def flocons_cumulus(largeur: float = 220, variant: int = 0) -> list:
    """Flocons d'un cumulus lointain (origine au centre de son dessous plat) : (centre, (dx, dy, dz), yaw, ton) ;
    ton 0 = nuage, 1 = nuage_ombre, 2 = entre les deux. Même facture que le nuage de l'œuf : dessous plat, couronne
    basse de flocons aplatis allongés, étage moyen, tête en chou-fleur décalée selon la variante."""
    L = float(largeur)
    v = variant % 3
    rng = np.random.default_rng(1000 + v)
    dec = (-0.13, 0.12, 0.0)[v]                    # tête décalée à gauche, à droite ou au centre
    out = [((0.0, 0.045 * L, 0.0), (0.74 * L, 0.09 * L, 0.42 * L), 0.0, 1)]
    for i in range(9):                             # couronne basse
        t = 2 * math.pi * (i + 0.5) / 9 + rng.uniform(-0.08, 0.08)
        d = (0.27 + 0.04 * math.cos(2 * t) + rng.uniform(-0.03, 0.03)) * L
        ap = rng.uniform(0.58, 0.68)
        out.append(((0.35 * L * math.cos(t), d * ap / 2 + rng.uniform(0, 0.012) * L, 0.18 * L * math.sin(t)),
                    (d * 1.22, d * ap, d * 0.95), math.degrees(-t) + 90, 2 if math.sin(t) > 0.3 else 0))
    for i in range(7):                             # étage moyen
        t = 2 * math.pi * i / 7 + 0.35 + rng.uniform(-0.1, 0.1)
        d = (0.25 + rng.uniform(-0.03, 0.03)) * L
        out.append((((0.21 * math.cos(t) + 0.4 * dec) * L, (0.15 + rng.uniform(-0.015, 0.015)) * L,
                     0.1 * L * math.sin(t)), (d * 1.08, d * 0.86, d), math.degrees(-t) + 90, 0))
    for i in range(5):                             # chou-fleur de la tête
        t = 2 * math.pi * i / 5 + 0.6 + 0.4 * v
        d = (0.19 + rng.uniform(-0.02, 0.02)) * L
        out.append((((0.1 * math.cos(t) + dec) * L, (0.25 + rng.uniform(-0.01, 0.02)) * L, 0.06 * L * math.sin(t)),
                    (d, d * 0.94, d), 0.0, 0))
    out.append(((dec * L, 0.3 * L, 0.0), (0.23 * L, 0.21 * L, 0.21 * L), 0.0, 0))
    if v == 2:                                     # variante 2 : une seconde tête plus basse
        out.append(((0.2 * L, 0.21 * L, 0.02 * L), (0.18 * L, 0.16 * L, 0.17 * L), 0.0, 0))
    return out


def cumulus(b, variant: int = 0, largeur: float = 220, **params) -> dict:
    """Cumulus « cartoon » lointain (C15), origine au centre de son dessous plat : 23 ou 24 ellipsoïdes, dessous plat
    nuage_ombre, couronne basse de flocons aplatis, étage moyen, tête en chou-fleur décalée selon la variante.
    Emprise ≈ largeur × 0,5 largeur, hauteur ≈ 0,4 largeur. ≤ 30 pièces, sans collision ni ombre."""
    L = float(largeur)
    rng = np.random.default_rng(2000 + variant)
    kw = {"collide": False, "shadow": False}
    blanc, ombre = c("nuage"), c("nuage_ombre")
    tons = (blanc, ombre, mix(ombre, blanc, 0.45))
    lo = np.array([1e9, 1e9, 1e9])
    hi = -lo
    with b.group("Nuage"):
        for i, (ctr, taille, yaw, ton) in enumerate(flocons_cumulus(L, variant)):
            col = varier(tons[ton], rng, 0.012) if ton != 1 else ombre
            b.ellipsoid(ctr, taille, col, rot=rot_y(yaw) if yaw else None, name="NuageBase" if i == 0 else "Nuage",
                        **kw)
            demi = np.array(taille) / 2
            lo = np.minimum(lo, np.array(ctr) - demi.max())
            hi = np.maximum(hi, np.array(ctr) + demi.max())
    return {"emprise": (round(float(hi[0] - lo[0]), 1), round(float(hi[2] - lo[2]), 1)),
            "hauteur": round(float(hi[1]), 1)}


# =====================================================================================================================
# Skyline lointaine (C07, finition)
# =====================================================================================================================

SKYLINE_TEINTES = ("skyline", ("skyline", "bleu_roi", 0.25), ("skyline", "turquoise", 0.35), ("skyline", "blanc_labo", 0.5))


def _teinte_skyline(i: int):
    t = SKYLINE_TEINTES[i % 4]
    return c(t) if isinstance(t, str) else mix(c(t[0]), c(t[1]), t[2])


def skyline_lointaine(b, variant: int = 0, tours=(), **params) -> dict:
    """Skyline pâle au-delà du mur de fond (bible § 6.7) : tours simplifiées de 3 à 5 pièces (fût, dôme, 1 ou 2
    disques ou galettes), en `skyline` et ses trois variantes, sans détail. `tours` : liste de dicts (x, z, h, d,
    teinte, forme) en coordonnées de la carte (pose à l'origine). Sans collision ni ombre. ≈ 4,5 pièces par tour."""
    kw = {"collide": False, "shadow": False}
    n0 = len(b.parts)
    for i, t in enumerate(tours):
        x, z, H, D = float(t["x"]), float(t["z"]), float(t["h"]), float(t["d"])
        col = _teinte_skyline(int(t.get("teinte", 0)))
        clair = mix(col, c("blanc_labo"), 0.35)
        sombre = mix(col, c("bleu_roi"), 0.18)
        r = D / 2
        forme = int(t.get("forme", 0)) % 4
        with b.group(f"Tour_{i + 1:02d}"):
            y0 = -4.0                                    # pied caché sous le niveau du sol de la carte
            if forme == 2:                               # galettes : fût fin et 3 lentilles
                b.cyl((x, (y0 + H) / 2, z), 0.42 * r, H - y0, col, name="Fut", **kw)
                for j in range(3):
                    yj = H * (0.45 + 0.22 * j)
                    b.ellipsoid((x, yj, z), (D * (1.1 - 0.15 * j), 0.18 * D, D * (1.1 - 0.15 * j)),
                                clair if j % 2 == 0 else sombre, name="Galette", **kw)
                b.ellipsoid((x, H, z), (0.6 * D, 0.35 * D, 0.6 * D), clair, name="Dome", **kw)
            else:
                b.cyl((x, (y0 + H) / 2, z), r, H - y0, col, name="Fut", **kw)
                b.ellipsoid((x, H, z), (D - 0.6, 0.55 * D, D - 0.6), clair, name="Dome", **kw)
                if forme in (1, 3):                      # disque débordant (chapeau, plateau)
                    b.cyl((x, H * 0.72, z), r * 1.45, max(1.2, 0.06 * D), sombre, name="Disque", **kw)
                if forme == 3:
                    b.cyl((x, H * 0.5, z), r * 1.25, max(1.0, 0.05 * D), clair, name="Disque", **kw)
    return {"tours": len(tours), "pieces": len(b.parts) - n0}

