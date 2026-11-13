"""Ciel de la carte « île du futur » (CarteEgghead) : l'œuf-laboratoire fêlé sur son cumulus (le repère de la carte),
son câble et sa station d'ancrage, les nacelles volantes, les pièces d'or, le dirigeable-baleine et les cumulus
lointains. Fiche : SPECS.md § assets/ciel.py ; recettes : STYLE.md § 6 (C01, C02, C03, C16, C12/M18, C14, C15).

    python apercu.py assets.ciel:oeuf_labo --no-ground --res 1200x675 --samples 12
    python apercu.py assets.ciel:nacelle --variant 1 --params '{"rayon": 7}'
    python apercu.py assets.ciel:piece_or --variant 1
    python apercu.py assets.ciel:dirigeable
    python apercu.py assets.ciel:cumulus --variant 2 --no-ground
    python apercu.py assets.ciel:cable --no-ground

Conventions (CONVENTIONS.md) : origine d'un objet volant = son centre (l'œuf : le pied de sa coquille, le cumulus :
le centre de son dessous plat) ; avant = -Z local ; tout est sans collision (sauf le socle de la station d'ancrage) ;
le nuage et l'œuf ne projettent pas d'ombre. Aucun texte, aucun visage, aucun personnage : la coquille est lisse, les
« données » de l'anneau sont des pixels, les nacelles sont vides (siège et console seulement).
"""

from __future__ import annotations

import math

import numpy as np

import plan
from kit import mix, rot_x, rot_y, rot_z, shade, varier
from palette import c

# =====================================================================================================================
# L'œuf-laboratoire (C01) — toutes les cotes en unités k = 1 (multipliées par `echelle` à la construction)
# =====================================================================================================================

# Coquille : 5 ellipsoïdes (centre y, rayon horizontal, demi-hauteur, couleur) ; à chaque hauteur on voit celui qui
# dépasse. Trouvés par le calcul (build/ciel/profil3.py) : profil à moins de 1,5 de l'œuf de la bible, bandes violet
# → mauve → rose avec deux tons de passage, angles de croisement de 10° (raccords nets, sans facette marquée).
#   violet 0 → 88 · violet-mauve 88 → 103 · mauve 103 → 118 · mauve-rose 118 → 134 · rose 134 → cassure (166)
COQUILLE = (
    (84.0, 74.71, 84.00, "violet"),
    (92.5, 74.93, 50.06, "violet_mauve"),
    (91.5, 74.05, 79.10, "mauve"),
    (101.0, 71.01, 91.22, "mauve_rose"),
    (124.0, 66.80, 75.04, "rose"),
)
CASSURE_Y = 166.0          # pied des dents (ligne de cassure)
DENTS = 14                 # dents du zigzag
DENT_EP = 2.6              # épaisseur des dents
DENT_PENTE = 15.0          # inclinaison moyenne vers l'axe (degrés)
DENT_ENFONCE = 4.0         # les dents descendent sous la cassure, dans la coquille
# hauteurs des dents, la n° 0 à l'avant (-Z local), puis dans le sens trigonométrique vu du dessus
DENT_H = (31.0, 24.0, 28.0, 19.0, 25.0, 17.0, 22.0, 18.0, 23.0, 16.0, 24.0, 20.0, 29.0, 23.0)
# décalage du sommet le long de la dent (fraction de la demi-largeur) : cassure irrégulière mais nette
DENT_SOMMET = (0.0, 0.18, -0.12, 0.22, -0.2, 0.1, -0.15, 0.2, -0.1, 0.15, -0.22, 0.12, -0.18, 0.08)
DENT_PENTES = (16.0, 13.0, 17.0, 14.0, 16.0, 13.0, 15.0, 17.0, 14.0, 16.0, 13.0, 17.0, 15.0, 14.0)
# Intérieur : dôme sombre qui monte dans la cassure, quadrillé de lumière
DOME_Y = 168.0
DOME_DEMI_H = 40.0
DOME_MARGE = 1.0           # rayon du dôme à son équateur = apothème des dents - marge (caché dans les dents)
GRILLE_EP = 1.3            # largeur des lignes lumineuses
GRILLE_SAILLIE = 0.35      # saillie des lignes au-dessus du dôme
GRILLE_PARALLELES = (0.27, 0.52, 0.76)   # hauteurs des parallèles (fraction de la demi-hauteur du dôme)
# Anneau de données (ruban vertical en 6 arcs de 50°, incliné) + pixels sur son bord haut
ANNEAU_R = 96.0
ANNEAU_Y = 112.0
ANNEAU_HAUT = 5.0          # hauteur du ruban
ANNEAU_EP = 1.3            # épaisseur du ruban
ANNEAU_INCLINAISON = (5.0, 9.0)   # (autour de X, autour de Z), degrés
# Cubes de données : arc lâche au-dessus de l'œuf
CUBES_R = 110.0
CUBES_Y = (215.0, 290.0)
CUBES_ARC = (-30.0, 230.0)      # angles de début et de fin de l'arc (0 = +X, 90 = avant -Z)
# Cumulus de l'œuf
NUAGE_BASE = ((380.0, 50.0, 300.0), -30.0)    # diamètres, centre y : dessous presque plat, nuage_ombre
BANDES_NUAGE = ((205.0, -15.0, "cyan"), (215.0, -40.0, "bleu_roi"))


def _couleurs_oeuf() -> dict:
    v, m, r = c("oeuf_violet"), c("oeuf_mauve"), c("oeuf_rose")
    return {"violet": v, "violet_mauve": mix(v, m, 0.5), "mauve": m, "mauve_rose": mix(m, r, 0.5), "rose": r,
            "interieur": c("oeuf_interieur"), "grille": c("neon_violet")}


def _r_ell(y: float, cy: float, a: float, h: float) -> float:
    u = (y - cy) / h
    return a * math.sqrt(1 - u * u) if abs(u) < 1 else 0.0


def rayon_coquille(y: float) -> float:
    """Rayon extérieur de la coquille à la hauteur y (k = 1)."""
    return max(_r_ell(y, cy, a, h) for cy, a, h, _ in COQUILLE)


def _dent(b, phi: float, apo: float, y0: float, larg: float, decal: float, h: float, ep: float, pente: float,
          couleur, **kw) -> None:
    """Dent de la cassure : triangle de deux coins dos à dos, debout sur le côté d'un polygone (apothème `apo`) à la
    hauteur y0, penché de `pente` degrés vers l'axe. `phi` : angle du milieu du côté (0 = +X, 90 = -Z) ; `larg` :
    longueur du côté ; `decal` : décalage du sommet le long du côté (cassure irrégulière)."""
    ph = math.radians(phi)
    radial = np.array([math.cos(ph), 0.0, -math.sin(ph)])
    X = np.array([-math.sin(ph), 0.0, -math.cos(ph)])        # tangente (sens des phi croissants)
    lam = math.radians(pente)
    Y = math.cos(lam) * np.array([0.0, 1.0, 0.0]) - math.sin(lam) * radial
    Z = math.sin(lam) * np.array([0.0, 1.0, 0.0]) + math.cos(lam) * radial
    pied = np.array([0.0, y0, 0.0]) + apo * radial + decal * X
    wd, wg = larg / 2 - decal, larg / 2 + decal               # largeurs à droite (+X) et à gauche du sommet
    # coin A (côté +X) : face pleine contre l'axe de la dent, pente vers le coin du polygone
    b.part("wedge", (ep, h, wd), pied + X * (wd / 2) + Y * (h / 2), np.column_stack([Z, Y, -X]), couleur,
           name="Dent", **kw)
    b.part("wedge", (ep, h, wg), pied - X * (wg / 2) + Y * (h / 2), np.column_stack([-Z, Y, X]), couleur,
           name="Dent", **kw)


def _puff(b, centre, d, couleur, aplat: float = 1.0, rot=None, **kw):
    """Boule de nuage : boule si aplat = 1, sinon ellipsoïde (d, aplat d, d)."""
    if abs(aplat - 1.0) < 1e-6 and rot is None:
        return b.ball(centre, d / 2, couleur, name="Nuage", **kw)
    return b.ellipsoid(centre, (d, d * aplat, d), couleur, rot=rot, name="Nuage", **kw)


def _cumulus_oeuf(b, k: float, kw: dict) -> int:
    """Le gros cumulus sous l'œuf : dessous plat nuage_ombre, trois étages de boules (grandes en couronne basse,
    moyennes, petites contre la coquille), quelques boules basses aux deux bouts. ≈ 36 pièces."""
    rng = b.rng
    blanc, ombre = c("nuage"), c("nuage_ombre")
    demi_ombre = mix(blanc, ombre, 0.4)
    n0 = len(b.parts)
    (dx, dy, dz), yb = NUAGE_BASE
    b.ellipsoid((0, yb * k, 0), (dx * k, dy * k, dz * k), ombre, name="NuageBase", **kw)
    # étage A : couronne basse de 12 grandes boules aplaties (dessous au-dessus du dessous de la base)
    for i in range(12):
        t = 2 * math.pi * (i + 0.5) / 12
        d = (98 + 14 * math.cos(2 * t) + rng.uniform(-6, 6))
        x, z = 150 * math.cos(t), 112 * math.sin(t)
        y = -6 + rng.uniform(-3, 3)
        col = varier(blanc if math.sin(t) < 0.35 else demi_ombre, rng, 0.03)
        _puff(b, (x * k, y * k, z * k), d * k, col, aplat=0.78, rot=rot_y(math.degrees(-t)), **kw)
    # étage B : 10 boules moyennes
    for i in range(10):
        t = 2 * math.pi * i / 10 + 0.31
        d = 78 + rng.uniform(-8, 8)
        x, z = 100 * math.cos(t), 78 * math.sin(t)
        y = 14 + rng.uniform(-3, 3)
        _puff(b, (x * k, y * k, z * k), d * k, varier(blanc, rng, 0.03), aplat=0.86, **kw)
    # étage C : 8 boules contre la coquille (l'œuf est « posé dedans »)
    for i in range(8):
        t = 2 * math.pi * i / 8 + 0.2
        d = 52 + rng.uniform(-5, 5)
        x, z = 74 * math.cos(t), 72 * math.sin(t)
        y = 30 + rng.uniform(-2, 3)
        _puff(b, (x * k, y * k, z * k), d * k, varier(blanc, rng, 0.03), **kw)
    # bouts : boules basses qui affinent la silhouette
    for sx in (-1, 1):
        for j, (x, z, y, d) in enumerate(((205, 20, -18, 64), (182, -60, -22, 56))):
            _puff(b, (sx * x * k, y * k, (z if sx > 0 else -z) * k), d * k, varier(blanc, rng, 0.03), aplat=0.8,
                  **kw)
    return len(b.parts) - n0


def oeuf_labo(b, variant: int = 0, echelle: float = 1.6, **params) -> dict:
    """Le repère du ciel (C01) : œuf rose-lavande à fond violet, cassé en zigzag sur un intérieur sombre quadrillé
    de lumière, anneau de données, arc de cubes, posé dans un gros cumulus ceinturé de deux bandes lumineuses.

    Origine : pied de la coquille (y = 0, enfoncé dans le nuage) ; avant (-Z local) : la face tournée vers la carte
    (dents les plus hautes, sommet de l'arc de cubes). Tout sans collision ; nuage et œuf sans ombre.
    Pièces ≈ 230 (≤ 320), Neon ≈ 60 (≤ 90), transparentes 0."""
    k = float(echelle)
    col = _couleurs_oeuf()
    kw = {"collide": False, "shadow": False}

    # --- coquille --------------------------------------------------------------------------------------------
    with b.group("Coquille"):
        for cy, a, h, nom in COQUILLE:
            b.ellipsoid((0, cy * k, 0), (2 * a * k, 2 * h * k, 2 * a * k), col[nom], name="Coquille", **kw)

    # --- cassure : 14 dents en zigzag sur un polygone posé sur la coquille ---------------------------------------
    r_cass = rayon_coquille(CASSURE_Y)
    apo = r_cass - DENT_EP / 2                       # face extérieure au ras de la coquille au pied
    larg = 2 * apo * math.tan(math.pi / DENTS)
    with b.group("Cassure"):
        for i in range(DENTS):
            phi = 90.0 + 360.0 * i / DENTS
            h = DENT_H[i % len(DENT_H)] + DENT_ENFONCE
            _dent(b, phi, apo * k, (CASSURE_Y - DENT_ENFONCE) * k, larg * k,
                  DENT_SOMMET[i % len(DENT_SOMMET)] * larg / 2 * k, h * k, DENT_EP * k,
                  DENT_PENTES[i % len(DENT_PENTES)], col["rose"], **kw)

    # --- intérieur : dôme sombre et grille lumineuse ------------------------------------------------------------
    a_d = apo - DENT_EP / 2 - DOME_MARGE + DENT_EP / 2   # équateur dans l'épaisseur des dents
    with b.group("Interieur"):
        b.ellipsoid((0, DOME_Y * k, 0), (2 * a_d * k, 2 * DOME_DEMI_H * k, 2 * a_d * k), col["interieur"],
                    name="Interieur", **kw)
        s = GRILLE_SAILLIE
        for ang in (0.0, 45.0, 90.0, 135.0):
            b.ellipsoid((0, DOME_Y * k, 0), (GRILLE_EP * k, 2 * (DOME_DEMI_H + s) * k, 2 * (a_d + s) * k),
                        col["grille"], rot=rot_y(ang), material="Neon", name="Meridien", **kw)
        for f in GRILLE_PARALLELES:
            y = DOME_DEMI_H * f
            r = _r_ell(DOME_Y + y, DOME_Y, a_d, DOME_DEMI_H) + s
            b.cyl((0, (DOME_Y + y) * k, 0), r * k, GRILLE_EP * k, col["grille"], material="Neon", name="Parallele",
                  **kw)

    # --- anneau de données : 6 arcs de 50° (trous de 10°), ruban bleu, pixels sur le bord haut -------------------
    ix, iz = ANNEAU_INCLINAISON
    R_an = rot_z(iz) @ rot_x(ix)
    with b.group("Anneau"):
        with b.at((0, ANNEAU_Y * k, 0), rot=R_an):
            for j in range(6):
                b.anneau((0, 0, 0), ANNEAU_R * k, ANNEAU_HAUT * k, [c("bleu_roi"), c("bleu_nuit")], 36,
                         arc=50, depart=60 * j + 15, section="plat", largeur=ANNEAU_EP * k, name="Donnees", **kw)
            # pixels : petits blocs en escalier posés sur le bord haut du ruban (« barres de données »)
            pix = ((32, 1), (36, 2), (40, 1), (95, 1), (99, 2), (103, 3), (158, 1), (162, 2), (215, 1), (279, 2))
            for th, n in pix:
                t = math.radians(th)
                rad = np.array([math.cos(t), 0.0, -math.sin(t)])
                tang = math.degrees(math.atan2(-rad[0], -rad[2]))
                taille = 3.0 * k
                for e in range(n):
                    y = (ANNEAU_HAUT / 2) * k + taille * (e + 0.5) - 0.05 * k
                    neon = (th, e) in ((99, 1), (215, 0))
                    b.boxc(tuple(rad * ANNEAU_R * k + np.array([0, y, 0])), (taille, taille * 0.9, ANNEAU_EP * k),
                           c("cyan") if neon else c("cube_bleu"), yaw=tang + 90, name="Pixel",
                           material="Neon" if neon else "SmoothPlastic", **kw)

    # --- cubes de données : arc lâche au-dessus de l'œuf ----------------------------------------------------------
    cols = (["cube_bleu"] * 8 + ["lavande"] * 5 + ["blanc_labo"] * 3)
    ordre = (0, 8, 13, 1, 9, 2, 14, 3, 10, 4, 11, 15, 5, 12, 6, 7)          # mélange fixe des couleurs
    neons = (4, 11)
    rng = np.random.default_rng(404)
    with b.group("Cubes"):
        a0, a1 = CUBES_ARC
        for i in range(16):
            t = i / 15
            th = math.radians(a0 + (a1 - a0) * t)
            y = CUBES_Y[0] + (CUBES_Y[1] - CUBES_Y[0]) * (0.5 - 0.5 * math.cos(math.pi * t))
            r = CUBES_R + rng.uniform(-8, 8)
            p = np.array([r * math.cos(th), y + rng.uniform(-6, 6), -r * math.sin(th)])
            cote = (6 + 8 * rng.uniform(0, 1)) if i not in neons else 7.0
            nom = cols[ordre[i]]
            R = rot_y(rng.uniform(0, 90)) @ rot_x(rng.uniform(10, 35)) @ rot_z(rng.uniform(10, 35))
            b.part("block", (cote * k,) * 3, p * k, R, c("cyan") if i in neons else c(nom),
                   material="Neon" if i in neons else "SmoothPlastic", name="Cube", **kw)

    # --- cumulus ---------------------------------------------------------------------------------------------
    with b.group("Nuage"):
        _cumulus_oeuf(b, k, kw)

    # --- bandes lumineuses autour du nuage : arcs interrompus (1 segment sur 5 retiré) ---------------------------
    with b.group("Bandes"):
        for j, (R, y, nom) in enumerate(BANDES_NUAGE):
            incl = rot_x(2.0 if j == 0 else -1.5) @ rot_z(-1.5 if j == 0 else 2.0)
            with b.at((0, y * k, 0), rot=incl):
                neon = nom == "cyan"
                for run in range(8):
                    b.anneau((0, 0, 0), R * k, 1.2 * k, c(nom), 40, arc=36, depart=45 * run + 4.5 * j,
                             section="plat", largeur=2.5 * k, material="Neon" if neon else "SmoothPlastic",
                             name="Bande", **kw)
                    if not neon:     # un pixel Neon cyan par arc, posé sur la bande
                        t = math.radians(45 * run + 4.5 * j + 18)
                        rad = np.array([math.cos(t), 0.0, -math.sin(t)])
                        b.boxc(tuple(rad * R * k + np.array([0, 0.6 * k + 0.5 * k, 0])), (6 * k, 1.0 * k, 3.2 * k),
                               c("cyan"), yaw=math.degrees(math.atan2(-rad[0], -rad[2])) + 90, material="Neon",
                               name="Pixel", **kw)

    lo_nuage = (NUAGE_BASE[1] - NUAGE_BASE[0][1] / 2) * k
    return {"emprise": (round(NUAGE_BASE[0][0] * k, 1), round(NUAGE_BASE[0][2] * k, 1)),
            "hauteur": round((DOME_Y + DOME_DEMI_H) * k, 1),
            "nuage_bas": round(lo_nuage, 1), "nuage_haut": round(40 * k, 1),
            "oeuf_haut": round((DOME_Y + DOME_DEMI_H) * k, 1),
            "cubes_haut": round((CUBES_Y[1] + 12) * k, 1)}


# =====================================================================================================================
# Câble et station d'ancrage
# =====================================================================================================================

def cable(b, variant: int = 0, depart=(-80, 216, -760), arrivee=(-80, 0, -560), **params) -> dict:
    """Câble de l'œuf (coordonnées de la carte : carte.py appelle avec b.at((0, 0, 0))) : `cyl_entre` R 1
    blanc_labo du dessous du nuage (`depart`, caché dans le nuage) au tambour d'une station d'ancrage posée sur
    son propre socle (`arrivee` = point au sol). 7 perles Neon (neon_blanc, rouge) tous les 40.
    Pièces ≈ 18 (≤ 22), Neon 8."""
    p0 = np.asarray(depart, float)
    a = np.asarray(arrivee, float)
    blanc = c("blanc_labo")
    with b.group("Station"):
        b.box((a[0] - 12, a[1] - 2, a[2] - 12), (a[0] + 12, a[1] + 0.4, a[2] + 12), c("sol_vert_clair"),
              studs="top", name="Socle")
        b.cyl((a[0], a[1] + 0.7, a[2]), 6.5, 0.6, c("dalle_labo"), studs="top", name="Plateau")
        b.cyl((a[0], a[1] + 4.0, a[2]), 3.0, 6.0, blanc, name="Tambour")
        b.cyl((a[0], a[1] + 6.2, a[2]), 3.4, 0.8, c("bleu_roi"), studs="top", name="Bague")
        b.cyl((a[0], a[1] + 2.0, a[2]), 3.25, 0.6, c("rouge"), name="Liseré", collide=False)
        for sx, sz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            b.wedge((a[0] + sx * 3 - 1.5 * abs(sz) - (0.5 if sx else 0), a[1] + 1.0, a[2] + sz * 3 - 1.5 * abs(sx)),
                    (a[0] + sx * 6 + 1.5 * abs(sz), a[1] + 3.0, a[2] + sz * 6 + 1.5 * abs(sx)), blanc,
                    down={(1, 0): "+x", (-1, 0): "-x", (0, 1): "+z", (0, -1): "-z"}[(sx, sz)], name="Contrefort")
        b.ball((a[0], a[1] + 7.3, a[2]), 0.9, c("cyan"), material="Neon", collide=False, shadow=False,
               name="Balise")
    top = a + np.array([0, 6.6, 0])
    with b.group("Cable"):
        b.cyl_entre(p0, top, 1.0, blanc, collide=False, name="Cable")
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
        L = 0.62 * r
        for i in range(5):
            a = math.radians(90 + 72 * i)
            ctr = (math.cos(a) * L / 2, math.sin(a) * L / 2, 0)
            b.part("block", (L, 0.16 * r, 2.0), ctr, rot_z(math.degrees(a)), c("or"), name="Etoile", **kw)
        b.cyl((0, 0, 0), 0.16 * r, 2.1, c("or"), axis="z", name="Etoile", **kw)
    return {"emprise": (round(2 * r, 1), 2.1 if variant % 2 else 1.8), "hauteur": round(2 * r, 1)}


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
                z = (-22.0 + 8.5 * i) * k
                dirn = np.array([sx * 1.0, 0.18, (z - corps_c[2]) / (corps_d[2] * 1.6)])
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
            for ang in (20.0, 110.0):
                b.part("block", (6.6 * k, 0.9 * k, 0.4 * k), (hx, yg, 0.4 * k), rot_z(ang + sx * 15), orange,
                       name="Pale", **kw)
    with b.group("Feux"):
        for sx in (-1, 1):
            b.ball((sx * 17.0 * k, 1.2 * k, 50.5 * k), 0.9 * k, c("cyan"), material="Neon", shadow=False,
                   name="Feu", **kw)
            b.ball((sx * 19.2 * k, -9.6 * k, -11.5 * k), 0.8 * k, c("cyan"), material="Neon", shadow=False,
                   name="Feu", **kw)
    return {"emprise": (round(40 * k, 1), round(longueur, 1)), "hauteur": round(48 * k, 1)}


# =====================================================================================================================
# Cumulus lointains (C15)
# =====================================================================================================================

def cumulus(b, variant: int = 0, largeur: float = 220, **params) -> dict:
    """Cumulus « cartoon » lointain, origine au centre de son dessous plat. 24 boules et ellipsoïdes : couronne basse
    nuage_ombre (dessous presque plat), dôme de boules nuage, une tête plus haute décalée selon la variante.
    Emprise ≈ largeur × 0,6 largeur, hauteur ≈ 0,35 largeur. ≤ 30 pièces."""
    L = float(largeur)
    rng = np.random.default_rng(1000 + variant)
    kw = {"collide": False, "shadow": False}
    blanc, ombre = c("nuage"), c("nuage_ombre")
    dec = (-0.12, 0.1, 0.0)[variant % 3]          # tête décalée à gauche, à droite ou au centre
    D = 0.6 * L
    with b.group("Nuage"):
        # dessous : ellipsoïde plat nuage_ombre
        b.ellipsoid((0, 0.05 * L, 0), (0.92 * L, 0.1 * L, 0.5 * L), ombre, name="NuageBase", **kw)
        # couronne basse : 9 boules aplaties
        for i in range(9):
            t = 2 * math.pi * (i + 0.5) / 9
            d = (0.3 + 0.05 * math.cos(2 * t)) * L
            _puff(b, (0.36 * L * math.cos(t), 0.12 * L, 0.2 * L * math.sin(t)), d,
                  varier(mix(blanc, ombre, 0.25), rng, 0.03), aplat=0.75, **kw)
        # étage moyen : 8 boules
        for i in range(8):
            t = 2 * math.pi * i / 8 + 0.3
            d = (0.26 + rng.uniform(-0.02, 0.02)) * L
            _puff(b, ((0.22 * math.cos(t) + dec * 0.5) * L, 0.2 * L, 0.13 * L * math.sin(t)), d,
                  varier(blanc, rng, 0.03), **kw)
        # dôme : 5 boules hautes et la tête
        for i in range(5):
            t = 2 * math.pi * i / 5 + 0.6
            _puff(b, ((0.1 * math.cos(t) + dec) * L, 0.27 * L, 0.07 * L * math.sin(t)), 0.2 * L,
                  varier(blanc, rng, 0.03), **kw)
        _puff(b, (dec * L, 0.3 * L, 0), 0.24 * L, varier(blanc, rng, 0.02), **kw)
    return {"emprise": (round(L, 1), round(D, 1)), "hauteur": round(0.42 * L, 1)}
