"""Architecture rétro-futuriste en dômes de la zone 4 (style « stud »).

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :
- maison_dome(rayon=9) : maison-dôme blanche du village terrestre (r = 6 à 10), socle gris clouté, bandes
    de couleur franche, hublots ronds, tunnel d'entrée à porte ronde, équipement de toit ;
    v0 dôme seul, bande orange, parabole ; v1 dôme et aile cylindrique basse, bande bleue ;
    v2 deux dômes (r et 0,65 r) reliés par un tube, bande rouge ; v3 maison haute (dôme sur un étage
    cylindrique à couronne de hublots), bande jaune ; v4 dôme à terrasse de toit (garde-corps, parasol),
    bande turquoise. Emprise : X ≤ 2r + 4 (v2 : 2r + 12), Z ≤ 2r + 6.
- boutique_dome() : boutique ronde 16 × 16 au bord de la rue, vitrine, store rayé, comptoir et tabourets,
    tableau de menu en pictogrammes, et un OBJET GÉANT sur le toit (aucun texte) :
    v0 cornet de glace, v1 brioche vapeur dans son panier, v2 gobelet à paille, v3 beignet glacé debout.
- maison_alien(rayon=7) : habitation de la planète extraterrestre, dôme blanc sur tambour, hublots-bulles
    verts, socle de sable, aiguilles blanches ; v0 dôme seul, v1 grappe de deux dômes, v2 socle en gradins
    et deux aiguilles, v3 petit dôme à grande baie ronde. Emprise (2r + 4) × (2r + 4).
- voiture_volante() : voiture volante garée (9 × 5, ≤ 4 de haut), sans roues : patins sombres ;
    v0 rouge, v1 jaune, v2 bleue, v3 turquoise.

Repère (voir CONVENTIONS.md) : origine au centre de l'emprise au sol, y = 0 au sol, l'AVANT regarde -Z
(la mise en page tourne l'asset de ±90° : X local court alors le long du couloir).
Azimut des hublots : 0 = avant (-Z), +90 = côté +X. Vu de la rue (depuis -Z), +X est à GAUCHE.

Technique des dômes : une boule centrée au sol (moitié basse cachée), une bande = un cylindre vertical
de rayon (rayon de la sphère au bord bas de la bande) + 0,15 ; hublot = disque de cadre enfoncé de 0,35
dans la sphère puis disque de verre qui dépasse de 0,15 du cadre (aucune face coplanaire).

Propriété intellectuelle : dômes rétro-futuristes génériques uniquement. Aucun logo, lettre, chiffre ni
nom d'entreprise ; aucune capsule posée au sol ; aucune sphère orange ; aucune étoile ; aucun texte.
"""

from __future__ import annotations

import math

import numpy as np

from kit import hexrgb, mix, rot_x, shade
from palette import c, vary

BANDES = ("bande_orange", "bande_bleue", "bande_rouge", "bande_jaune", "bande_turquoise", "bande_violette")

# Couleurs locales (en plus de la palette)
BRIOCHE = "#FBF5E8"        # pâte de brioche vapeur
GAUFRE = "#D9A15A"         # cornet gaufré
GAUFRE_FONCE = "#B57A3A"
GLACE_ROSE = "#F59CC8"     # boule fraise
GLACE_CHOCO = "#7A4A2E"    # boule chocolat
CREME = "#FFF8EC"
PATE_BEIGNET = "#E2B072"
GLACAGE_ROSE = "#F27BB8"
TABLEAU = "#2C3440"        # fond du tableau de menu
PORTE_ALIEN = "#4FA89A"    # porte des dômes extraterrestres (sarcelle)
LIERRE_ALIEN = "#2F9C8C"


# ---------------------------------------------------------------------------
# Outils géométriques
# ---------------------------------------------------------------------------

def _col(x):
    """Nom de palette, '#hex' ou tuple → tuple RGB."""
    if isinstance(x, tuple):
        return x
    if isinstance(x, str) and x.startswith("#"):
        return hexrgb(x)
    return c(x)


def _repere(axe) -> np.ndarray:
    """Matrice de rotation dont la première colonne (axe d'un cylindre Roblox) est `axe`."""
    x = np.asarray(axe, float)
    x = x / np.linalg.norm(x)
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return np.column_stack([x, y, z])


def _dir(az: float, el: float = 0.0) -> np.ndarray:
    """Direction unitaire : azimut depuis l'avant (-Z) vers +X, élévation au-dessus de l'horizon (degrés)."""
    a, e = math.radians(az), math.radians(el)
    return np.array([math.sin(a) * math.cos(e), math.sin(e), -math.cos(a) * math.cos(e)])


def _yaw_vers(dx: float, dz: float) -> float:
    """Lacet (degrés) qui aligne l'axe X local d'un bloc sur la direction horizontale (dx, dz)."""
    return math.degrees(math.atan2(-dz, dx))


def _disque(b, centre, normale, rayon: float, ep: float, couleur, **kw):
    """Disque (cylindre court) d'axe `normale`."""
    return b.part("cyl", (ep, 2 * rayon, 2 * rayon), centre, _repere(normale), _col(couleur), **kw)


def _rayon_sphere(r: float, t0: float, t1: float) -> float:
    """Plus grand rayon horizontal d'une sphère de rayon r entre les hauteurs t0 et t1 (relatives au centre)."""
    m = 0.0 if t0 <= 0 <= t1 else min(abs(t0), abs(t1))
    return math.sqrt(max(r * r - m * m, 0.0))


def _bande(b, ctr, r: float, y: float, h: float, couleur, ep: float = 0.15, name: str = "Bande"):
    """Bande colorée autour d'une sphère (centre `ctr`, rayon r), centrée à la hauteur absolue y."""
    cx, cy, cz = ctr
    rb = _rayon_sphere(r, y - h / 2 - cy, y + h / 2 - cy) + ep
    return b.cyl((cx, y, cz), rb, h, _col(couleur), collide=False, name=name)


def _hublot(b, ctr, r: float, az: float, el: float, rw: float, cadre, verre="vitre", neon=False):
    """Hublot rond sur une sphère : cadre enfoncé (dépasse de 0,15) puis verre (dépasse encore de 0,15)."""
    n = _dir(az, el)
    C = np.asarray(ctr, float)
    _disque(b, C + n * (r - 0.1), n, rw + 0.3, 0.5, cadre, collide=False, shadow=False, name="Cadre")
    _disque(b, C + n * (r + 0.15), n, rw, 0.3, "vitre_lumiere" if neon else verre,
            material="Neon" if neon else "Glass", collide=False, shadow=False, name="Hublot")


def _hublot_cyl(b, cx: float, cz: float, R: float, az: float, y: float, rw: float, cadre, verre="vitre", neon=False):
    """Hublot rond sur un mur cylindrique vertical (centre cx, cz ; rayon R)."""
    n = _dir(az, 0.0)
    C = np.array([cx, y, cz])
    _disque(b, C + n * (R - 0.1), n, rw + 0.3, 0.5, cadre, collide=False, shadow=False, name="Cadre")
    _disque(b, C + n * (R + 0.15), n, rw, 0.3, "vitre_lumiere" if neon else verre,
            material="Neon" if neon else "Glass", collide=False, shadow=False, name="Hublot")


def _bulle(b, ctr, r: float, az: float, el: float, rw: float, couleur="vitre_verte"):
    """Hublot-bulle : petite boule de verre à moitié enfoncée dans la sphère."""
    p = np.asarray(ctr, float) + _dir(az, el) * (r - 0.1 * rw)
    b.ball(tuple(p), rw, _col(couleur), material="Glass", reflectance=0.1, collide=False, shadow=False, name="Bulle")


def _anneau_poly(b, cx: float, cz: float, R: float, y: float, n: int, couleur, *, h=0.25, ep=0.25, a0=0.0,
                 poteaux=None, h_pot=1.2, name="Garde-corps"):
    """Garde-corps polygonal (n lisses) de rayon R, lisse en haut à la hauteur y (+ poteaux éventuels)."""
    for i in range(n):
        a1 = math.radians(a0 + 360 * i / n)
        a2 = math.radians(a0 + 360 * (i + 1) / n)
        p1 = np.array([cx + R * math.sin(a1), cz - R * math.cos(a1)])
        p2 = np.array([cx + R * math.sin(a2), cz - R * math.cos(a2)])
        m, d = (p1 + p2) / 2, p2 - p1
        b.boxc((m[0], y, m[1]), (float(np.linalg.norm(d)) + ep, h, ep), _col(couleur), yaw=_yaw_vers(d[0], d[1]),
               collide=False, name=name)
        if poteaux is not None:
            b.cyl((p1[0], y - h_pot / 2, p1[1]), 0.12, h_pot, _col(poteaux), collide=False, shadow=False, name="Poteau")


# ---------------------------------------------------------------------------
# Sous-ensembles communs des maisons-dômes
# ---------------------------------------------------------------------------

def _porche(b, x: float, z_masse: float, z_av: float, rt: float, yc: float, S: dict, *, lampes=True):
    """Tunnel d'entrée horizontal (axe z) à moitié enterré, de l'intérieur de la masse (z_masse) jusqu'à
    l'avant (z_av < z_masse) : encadrement coloré, porte ronde à judas, marche cloutée, deux bornes lumineuses."""
    blanc = S["blanc"]
    z0 = z_av + 0.3
    rp = rt - 0.55
    with b.group("Entree"):
        b.cyl((x, yc, (z0 + z_masse) / 2), rt, z_masse - z0, blanc, axis="z", name="Tunnel")
        b.cyl((x, yc, z_av + 0.35), rt + 0.3, 0.7, c(S["bande"]), axis="z", name="Encadrement")
        b.cyl((x, yc, z_av), rp, 0.3, c(S["porte"]), axis="z", name="Porte")
        b.cyl((x, yc + rp * 0.55, z_av - 0.15), min(0.65, rp * 0.24), 0.2, c("vitre"), axis="z", material="Glass",
              collide=False, shadow=False, name="Judas")
        b.box((x + rp * 0.5 - 0.15, 1.3, z_av - 0.35), (x + rp * 0.5 + 0.15, 2.1, z_av - 0.1), c("gris_tech_fonce"),
              collide=False, shadow=False, name="Poignee")
        b.box((x - rt + 0.4, 0, z_av - 1.0), (x + rt - 0.4, 0.3, z_av + 0.6), c("gris_tech"), studs="top", name="Marche")
        if lampes:
            for s in (-1, 1):
                lx = x + s * (rt + 1.0)
                b.cyl((lx, 0.8, z_av - 0.3), 0.3, 1.6, blanc, collide=False, name="Borne")
                b.cyl((lx, 1.75, z_av - 0.3), 0.36, 0.3, c("neon_cyan"), material="Neon", collide=False, shadow=False,
                      name="Lumiere")


def _equipement_toit(b, x: float, y: float, z: float, S: dict, style: int):
    """Équipement au sommet d'un dôme (y = sommet) : trappe ronde puis parabole (0), anneau-balise (1)
    ou lanterneau en bulle (2)."""
    blanc = S["blanc"]
    with b.group("Toit"):
        b.cyl((x, y - 0.1, z), 1.5, 0.8, c("gris_tech"), name="Trappe")
        b.cyl((x, y + 0.42, z), 1.1, 0.25, c(S["bande"]), collide=False, name="Couvercle")
        if style == 0:
            b.cyl((x, y + 0.55 + 1.3, z), 0.18, 2.6, c("gris_tech_fonce"), collide=False, name="Mat")
            a = math.radians(38)
            axe = np.array([0.0, math.sin(a), -math.cos(a)])
            ctr = np.array([x, y + 3.25, z]) + axe * 0.15
            _disque(b, ctr, axe, 1.7, 0.3, blanc, collide=False, name="Parabole")
            _disque(b, ctr + axe * 0.1, axe, 0.75, 0.3, c(S["bande"]), collide=False, shadow=False, name="Creux")
            p = ctr + axe * 1.3
            b.part("cyl", (1.2, 0.16, 0.16), tuple(ctr + axe * 0.75), _repere(axe), c("gris_tech_fonce"),
                   collide=False, shadow=False, name="Bras")
            b.box(tuple(p - 0.22), tuple(p + 0.22), c("neon_blanc"), material="Neon", collide=False, shadow=False,
                  name="Tete")
        elif style == 1:
            b.cyl((x, y + 0.55 + 1.6, z), 0.18, 3.2, c("gris_tech_fonce"), collide=False, name="Mat")
            b.cyl((x, y + 3.2, z), 1.2, 0.3, blanc, axis="z", collide=False, name="Anneau")
            b.cyl((x, y + 3.2, z), 0.8, 0.42, c("neon_cyan"), axis="z", material="Neon", collide=False, shadow=False,
                  name="Lumiere")
            b.cyl((x, y + 4.0, z), 0.3, 0.4, c(S["bande"]), collide=False, name="Pointe")
            b.box((x - 0.15, y + 4.2, z - 0.15), (x + 0.15, y + 4.6, z + 0.15), c("rouge"), material="Neon",
                  collide=False, shadow=False, name="Balise")
        else:
            b.ball((x, y + 0.5, z), 1.0, c("vitre"), material="Glass", reflectance=0.1, collide=False, name="Lanterneau")


def _jardiniere(b, x: float, z: float, S: dict, r: float = 0.9):
    """Pot rond blanc à bague colorée et buisson arrondi."""
    b.cyl((x, 0.6, z), r, 1.2, S["blanc"], name="Bac")
    b.cyl((x, 0.95, z), r + 0.08, 0.3, c(S["bande2"]), collide=False, name="Bague")
    b.ball((x, 1.2 + r * 0.55, z), r * 0.95, c("feuillage"), collide=False, name="Buisson")


def _boite_lettres(b, x: float, z: float, S: dict):
    """Boîte aux lettres arrondie sur pied."""
    b.cyl((x, 0.7, z), 0.15, 1.4, c("gris_tech_fonce"), collide=False, name="Pied")
    b.box((x - 0.4, 1.4, z - 0.55), (x + 0.4, 2.0, z + 0.55), c(S["bande"]), collide=False, name="Boite")
    b.cyl((x, 2.0, z), 0.4, 1.1, c(S["bande"]), axis="z", collide=False, name="Toit")


def _clim(b, x: float, z: float, yaw: float):
    """Bloc technique (climatiseur) posé au sol contre l'arrière."""
    with b.at((x, 0, z), yaw=yaw):
        b.box((-1.0, 0, -0.7), (1.0, 1.4, 0.7), c("gris_tech"), studs="top", name="Clim")
        b.cyl((0, 0.7, -0.75), 0.5, 0.12, c("gris_tech_fonce"), axis="z", collide=False, shadow=False, name="Grille")


STYLES_MAISON = (
    {"bande": "bande_orange", "bande2": "bande_turquoise", "porte": "porte", "cadre": "gris_tech"},
    {"bande": "bande_bleue", "bande2": "bande_jaune", "porte": "bande_jaune", "cadre": "bande_bleue"},
    {"bande": "bande_rouge", "bande2": "bande_jaune", "porte": "bande_bleue", "cadre": "gris_tech"},
    {"bande": "bande_jaune", "bande2": "bande_violette", "porte": "bande_violette", "cadre": "gris_tech"},
    {"bande": "bande_turquoise", "bande2": "bande_orange", "porte": "bande_orange", "cadre": "bande_turquoise"},
)


def _style_maison(variant: int, rng) -> dict:
    """Style de base (`variant % 5`) ; au-delà, on décale les couleurs pour varier la rue."""
    S = dict(STYLES_MAISON[variant % 5])
    k = variant // 5
    if k:
        for key in ("bande", "bande2", "porte"):
            if S[key] in BANDES:
                S[key] = BANDES[(BANDES.index(S[key]) + k) % len(BANDES)]
    S["blanc"] = vary("blanc_dome", rng, 0.015)
    return S


# ---------------------------------------------------------------------------
# 1) Maison-dôme du village terrestre
# ---------------------------------------------------------------------------

def maison_dome(b, variant: int = 0, rayon: float = 9) -> dict:
    """Maison-dôme blanche (voir l'en-tête du module). Le centre du dôme est à z = +1,5 pour que le
    tunnel d'entrée atteigne l'avant de l'emprise (z ≈ -(r + 3))."""
    rng = b.rng
    v = variant % 5
    r = float(rayon)
    S = _style_maison(variant, rng)
    blanc = S["blanc"]
    gris = c("gris_tech")
    cz = 1.5
    rt = round(0.42 * r, 2)                   # rayon du tunnel d'entrée
    yc = round(0.25 * rt, 2)
    z_av = -(r + 2.6)
    lum = rng.random(8) < 0.35                # hublots éclairés au hasard
    rw = max(0.8, round(0.12 * r, 2))
    larg = 2 * r + (12 if v == 2 else 4)
    hauteur = r + 4.6

    with b.group("MaisonDome"):
        if v == 3:
            # ---- maison haute : étage cylindrique (rayon r) puis dôme
            he = 4.4
            ctr = (0.0, he, cz)
            b.cyl((0, 0.4, cz), r + 0.6, 0.8, gris, studs="top", name="Socle")
            b.cyl((0, he / 2, cz), r, he, blanc, name="Etage")
            b.ball(ctr, r, blanc, name="Dome")
            b.cyl((0, he + 0.1, cz), r + 0.25, 1.0, c(S["bande"]), collide=False, name="Bande")
            _bande(b, ctr, r, he + 0.62 * r, 0.5, S["bande2"])
            for i, az in enumerate((-52, -88, -124, -160, 160, 124, 88, 52)):
                _hublot_cyl(b, 0, cz, r, az, 2.5, 0.75, S["cadre"], neon=bool(lum[i % 8]))
            for i, az in enumerate((-40, 40, -110, 110)):
                _hublot(b, ctr, r, az, 34, rw, S["cadre"], neon=bool(lum[(i + 3) % 8]))
            rt3 = round(0.3 * r, 2)
            _porche(b, 0, cz - math.sqrt(r * r - rt3 * rt3) + 0.6, z_av, rt3, 0.9, S)
            _equipement_toit(b, 0, he + r, cz, S, 1)
            hauteur = he + r + 4.6
            _jardiniere(b, -(r - 0.5), -(r + 1.2), S)
            _jardiniere(b, r - 0.5, -(r + 1.2), S, r=0.8)
        else:
            cx = {0: 0.0, 1: -1.4, 2: -5.2, 4: 0.0}[v]
            ctr = (cx, 0.0, cz)
            b.cyl((cx, 0.5, cz), r + 0.6, 1.0, gris, studs="top", name="Socle")
            b.ball(ctr, r, blanc, name="Dome")
            _bande(b, ctr, r, 0.4 * r, 1.2, S["bande"])
            if v != 4:
                _bande(b, ctr, r, 0.84 * r, 0.45, S["bande2"])
            hublots = {
                0: [(-52, 42), (52, 42), (-108, 30), (108, 30), (180, 36)],
                1: [(-52, 42), (-108, 30), (36, 46), (160, 36)],
                2: [(-52, 42), (-108, 30), (34, 46), (-160, 36)],
                4: [(-50, 38), (50, 38), (-110, 30), (110, 30), (180, 34)],
            }[v]
            for i, (az, el) in enumerate(hublots):
                _hublot(b, ctr, r, az, el, rw, S["cadre"], neon=bool(lum[i]))
            _porche(b, cx, cz - math.sqrt(max(r * r - (yc + rt) ** 2, 1.0)) + 0.4, z_av, rt, yc, S)

            if v == 0:
                _equipement_toit(b, cx, r, cz, S, 0)
                _jardiniere(b, -(r - 0.6), -(r + 0.8), S)
                _boite_lettres(b, r - 0.4, -(r + 1.6), S)
                _clim(b, r * 0.55, r * 0.75 + cz, 215)
            elif v == 1:
                # aile cylindrique basse côté +X, toit-terrasse clouté, lanterneau et panneaux solaires
                ra = round(0.45 * r + 0.5, 2)
                ha = round(0.42 * r + 1.2, 2)
                ax = (r + 2) - ra - 0.45
                azc = cz + 0.8
                with b.group("Aile"):
                    b.cyl((ax, 0.4, azc), ra + 0.4, 0.8, gris, studs="top", name="Socle")
                    b.cyl((ax, ha / 2, azc), ra, ha, blanc, name="Aile")
                    b.cyl((ax, ha + 0.25, azc), ra + 0.35, 0.5, c(S["bande"]), studs="top", name="Toiture")
                    b.ball((ax + 0.3 * ra, ha + 0.5, azc - 0.3 * ra), 1.1, c("vitre"), material="Glass",
                           reflectance=0.1, collide=False, name="Lanterneau")
                    for k, dz in enumerate((0.4, 1.9)):
                        b.part("block", (2.6, 0.2, 1.3), (ax - 0.2 * ra, ha + 1.0, azc + dz - 0.6 * ra + 0.6), rot_x(-25),
                               c("vitre_fonce"), collide=False, name="Solaire")
                    for i, az in enumerate((-20, 40, 100)):
                        _hublot_cyl(b, ax, azc, ra, az, ha * 0.5, 0.7, S["cadre"], neon=bool(lum[5 + i % 3]))
                _equipement_toit(b, cx, r, cz, S, 1)
                _jardiniere(b, cx - (r - 0.4), -(r + 0.9), S, r=0.8)
            elif v == 2:
                # second dôme (0,65 r) relié par un tube court à collier coloré
                rs = round(0.65 * r, 2)
                sx = (r + 6) - rs - 0.75
                sz = cz + 2.5
                sctr = (sx, 0.0, sz)
                with b.group("Dome2"):
                    b.cyl((sx, 0.4, sz), rs + 0.6, 0.8, gris, studs="top", name="Socle")
                    b.ball(sctr, rs, blanc, name="Dome")
                    _bande(b, sctr, rs, 0.42 * rs, 0.9, S["bande"])
                    for i, (az, el) in enumerate(((-15, 40), (70, 34), (150, 34))):
                        _hublot(b, sctr, rs, az, el, max(0.7, rw * 0.8), S["cadre"], neon=bool(lum[5 + i]))
                    b.ball((sx, rs - 0.2, sz), 0.9, c("vitre"), material="Glass", reflectance=0.1, collide=False,
                           name="Lanterneau")
                    d = np.array([sx - cx, 0.0, sz - cz])
                    dist = float(np.linalg.norm(d))
                    d /= dist
                    a = np.array(ctr) + d * (r - 2.5) + np.array([0, 2.4, 0])
                    e = np.array(sctr) + d * (dist - rs + 2.0) - d * dist + np.array([0, 2.4, 0])
                    mid = (a + e) / 2
                    b.part("cyl", (float(np.linalg.norm(e - a)), 3.4, 3.4), tuple(mid), _repere(d), blanc, name="Tube")
                    g = np.array(ctr) + d * (dist - rs + r) / 2 + np.array([0, 2.4, 0])
                    _disque(b, g, d, 2.0, 0.7, S["bande"], collide=False, name="Collier")
                _equipement_toit(b, cx, r, cz, S, 0)
                _jardiniere(b, cx - (r - 0.6), -(r + 0.8), S)
                _boite_lettres(b, sx + 0.5, -(r + 1.6), S)
            else:
                # v4 : terrasse de toit sur un tambour, garde-corps, parasol et plante en pot
                yd0, rd = 0.75 * r, round(0.5 * r, 2)
                yt = r + 0.5
                rt_ = round(0.66 * r, 2)
                with b.group("Terrasse"):
                    b.cyl((cx, (yd0 + yt) / 2, cz), rd, yt - yd0, blanc, name="Tambour")
                    b.cyl((cx, yt - 0.35, cz), rd + 0.15, 0.4, c(S["bande2"]), collide=False, name="Liseré")
                    for i, az in enumerate((-30, 30, 150, -150)):
                        _hublot_cyl(b, cx, cz, rd, az, yd0 + 0.62 * (yt - yd0) - 0.5, 0.45, S["cadre"],
                                    neon=bool(lum[i + 3]))
                    b.cyl((cx, yt + 0.25, cz), rt_, 0.5, c(S["bande"]), studs="top", name="Terrasse")
                    _anneau_poly(b, cx, cz, rt_ - 0.3, yt + 1.75, 10, blanc, poteaux=c("gris_tech"), h_pot=1.25, a0=18)
                    # parasol rayé
                    px, pz = cx + 0.25 * rt_, cz + 0.15 * rt_
                    b.cyl((px, yt + 0.5 + 1.6, pz), 0.12, 3.2, c("metal"), collide=False, name="Manche")
                    for k, (rr, col) in enumerate(((2.6, S["bande2"]), (1.9, "blanc"), (1.2, S["bande2"]), (0.5, "blanc"))):
                        b.cyl((px, yt + 3.5 + 0.25 * k, pz), rr, 0.26, c(col), collide=False, name="Toile")
                    b.cyl((px, yt + 1.4, pz), 1.0, 0.2, blanc, studs="top", collide=False, name="Table")
                    b.cyl((cx - 0.4 * rt_, yt + 1.0, cz - 0.2 * rt_), 0.7, 1.0, c("pave"), name="Pot")
                    b.ball((cx - 0.4 * rt_, yt + 2.1, cz - 0.2 * rt_), 0.95, c("feuillage"), collide=False,
                           name="Plante")
                hauteur = yt + 4.5
                _jardiniere(b, -(r - 0.6), -(r + 0.8), S)
                _jardiniere(b, r - 0.6, -(r + 0.8), S, r=0.8)
    return {"emprise": (larg, 2 * r + 6), "hauteur": round(hauteur, 2)}


# ---------------------------------------------------------------------------
# 2) Boutique ronde à objet géant
# ---------------------------------------------------------------------------

STYLES_BOUTIQUE = (
    {"store": ("bande_rouge", "blanc"), "bord": "bande_rouge", "porte": "porte", "menu": (GLACE_ROSE, CREME, GLACE_CHOCO)},
    {"store": ("bande_bleue", "blanc"), "bord": "bande_bleue", "porte": "bande_rouge",
     "menu": (BRIOCHE, "#E0453A", "#B98552")},
    {"store": ("bande_turquoise", "blanc"), "bord": "bande_turquoise", "porte": "bande_violette",
     "menu": ("#F6C83C", "#2DBFC2", "#F27BC0")},
    {"store": ("bande_violette", "blanc"), "bord": "bande_violette", "porte": "bande_jaune",
     "menu": (GLACAGE_ROSE, PATE_BEIGNET, "#8E6BE8")},
)


def _objet_geant(b, v: int, y0: float) -> float:
    """Objet géant posé au sommet du toit (base vers y0). Renvoie la hauteur du sommet."""
    with b.group("ObjetGeant"):
        if v == 0:
            # cornet de glace : socle, cornet gaufré en gradins, deux boules (fraise, chocolat), crème, gaufrette
            b.cyl((0, y0 + 0.3, 0), 1.2, 0.8, c("gris_tech"), name="Socle")
            for k, rr in enumerate((0.55, 0.95, 1.35, 1.75)):
                b.cyl((0, y0 + 0.7 + 0.75 * k + 0.375, 0), rr, 0.75, _col(GAUFRE if k % 2 == 0 else GAUFRE_FONCE),
                      name="Cornet")
            yb = y0 + 0.7 + 3.0
            b.cyl((0, yb + 0.2, 0), 2.05, 0.4, _col(GAUFRE_FONCE), name="Bord")
            b.ball((-0.75, yb + 1.5, -0.1), 1.75, _col(GLACE_ROSE), name="Boule")
            b.ball((0.85, yb + 1.65, 0.25), 1.6, _col(GLACE_CHOCO), name="Boule")
            b.ball((0.0, yb + 3.0, 0.0), 0.95, _col(CREME), name="Creme")
            b.part("block", (0.5, 2.6, 0.5), (1.3, yb + 3.0, -0.4), rot_x(15) @ np.array(
                [[math.cos(0.4), -math.sin(0.4), 0], [math.sin(0.4), math.cos(0.4), 0], [0, 0, 1]]),
                _col(GAUFRE), collide=False, name="Gaufrette")
            return yb + 3.95
        if v == 1:
            # brioche vapeur blanche (gradins aplatis) dans son panier de bambou, point rouge au sommet
            b.cyl((0, y0 + 0.6, 0), 3.6, 1.2, c("bois_clair"), name="Panier")
            b.cyl((0, y0 + 1.0, 0), 3.72, 0.3, c("bois"), collide=False, name="Cerclage")
            b.cyl((0, y0 + 0.35, 0), 3.72, 0.3, c("bois"), collide=False, name="Cerclage")
            ys = y0 + 1.2
            for k, (rr, hh) in enumerate(((3.3, 1.0), (2.9, 0.9), (2.25, 0.8), (1.4, 0.6))):
                b.cyl((0, ys + hh / 2, 0), rr, hh, _col(BRIOCHE), name="Brioche")
                ys += hh
            b.cyl((0, ys + 0.2, 0), 0.6, 0.4, _col(shade(hexrgb(BRIOCHE), 0.94)), name="Noeud")
            b.cyl((0, ys + 0.45, 0), 0.42, 0.1, c("bande_rouge"), collide=False, name="Point")
            return ys + 0.5
        if v == 2:
            # gobelet à paille : gobelet évasé à bandes, couvercle bombé, paille rayée inclinée
            ys = y0
            b.cyl((0, ys + 0.3, 0), 1.3, 0.6, c("gris_tech"), name="Socle")
            ys += 0.6
            for k, (rr, hh, col) in enumerate(((1.6, 1.2, "blanc"), (1.9, 1.4, "bande_turquoise"), (2.2, 1.4, "blanc"))):
                b.cyl((0, ys + hh / 2, 0), rr, hh, c(col), name="Gobelet")
                ys += hh
            b.cyl((0, ys + 0.2, 0), 2.4, 0.4, c("bande_rose") if False else _col("#F27BC0"), name="Couvercle")
            b.ball((0, ys - 0.6, 0), 1.75, _col("#F7A9D6"), name="Dome")
            axe = np.array([0.35, 1.0, 0.15])
            axe /= np.linalg.norm(axe)
            base = np.array([0.0, ys + 0.6, 0.0])
            for k, col in enumerate(("blanc", "bande_rouge", "blanc")):
                b.part("cyl", (1.3, 0.6, 0.6), tuple(base + axe * (0.65 + 1.3 * k)), _repere(axe), c(col),
                       collide=False, name="Paille")
            return float(base[1] + axe[1] * 3.9)
        # v3 : beignet géant debout, glaçage rose et vermicelles
        b.box((-1.6, y0, -1.0), (1.6, y0 + 1.0, 1.0), c("gris_tech"), studs="top", name="Socle")
        R, rb = 2.4, 1.25
        yc = y0 + 1.0 + R + rb - 0.4
        cols = ("bande_jaune", "bande_turquoise", "blanc", "bande_violette")
        for k in range(10):
            a = 2 * math.pi * k / 10
            px, py = R * math.cos(a), yc + R * math.sin(a)
            b.ball((px, py, 0.15), rb, _col(PATE_BEIGNET), name="Pate")
            b.ball((px, py, -0.25), rb * 0.86, _col(GLACAGE_ROSE), name="Glacage")
            if k % 2 == 0:
                b.box((px - 0.18, py - 0.06, -1.42), (px + 0.18, py + 0.06, -1.2), c(cols[k // 2 % 4]),
                      collide=False, shadow=False, name="Vermicelle")
        return yc + R + rb


def boutique_dome(b, variant: int = 0) -> dict:
    """Boutique ronde (rayon 6,4) : vitrine, store rayé, toit plat bordé et coupole basse, comptoir avant,
    tabourets, tableau de menu en pictogrammes, objet géant sur le toit. Emprise 16 × 16, hauteur ≤ 16."""
    rng = b.rng
    v = variant % 4
    S = dict(STYLES_BOUTIQUE[v])
    blanc = vary("blanc_dome", rng, 0.015)
    gris = c("gris_tech")
    R = 6.4
    with b.group("Boutique"):
        b.cyl((0, 0.3, 0), 7.2, 0.6, gris, studs="top", name="Socle")
        b.cyl((0, 3.3, 0), R, 5.4, blanc, name="Mur")
        # vitrine : panneaux tangents entre montants, quelques-uns éclairés
        n = 16
        pas = 360 / n
        lum = rng.random(n) < 0.4
        for i in range(-4, 5):
            az = i * pas
            with b.at((0, 0, 0), yaw=-az):
                if i == -3:
                    # porte vitrée
                    b.box((-1.05, 0.6, -(R + 0.2)), (1.05, 4.6, -(R - 0.1)), c(S["porte"]), name="Porte")
                    b.box((-0.7, 2.2, -(R + 0.3)), (0.7, 4.2, -(R + 0.1)), c("vitre"), material="Glass",
                          collide=False, shadow=False, name="Vitre")
                    b.box((0.55, 1.9, -(R + 0.4)), (0.75, 2.4, -(R + 0.15)), c("gris_tech_fonce"), collide=False,
                          shadow=False, name="Poignee")
                else:
                    neon = bool(lum[i + 4]) and i != 0
                    b.box((-1.05, 1.8, -(R + 0.2)), (1.05, 4.6, -(R - 0.1)),
                          c("vitre_lumiere") if neon else c("vitre"), material="Neon" if neon else "Glass",
                          collide=False, shadow=False, name="Vitrine")
            with b.at((0, 0, 0), yaw=-(az + pas / 2)):
                b.box((-0.2, 1.6, -(R + 0.35)), (0.2, 4.8, -(R - 0.1)), blanc, collide=False, name="Montant")
        with b.at((0, 0, 0), yaw=-(-4.5 * pas)):
            b.box((-0.2, 1.6, -(R + 0.35)), (0.2, 4.8, -(R - 0.1)), blanc, collide=False, name="Montant")
        b.cyl((0, 1.65, 0), R + 0.2, 0.3, c(S["bord"]), collide=False, name="Plinthe")
        # store rayé en couronne (coins tournés) et lambrequin
        a1, a2 = S["store"]
        for i in range(n):
            az = (i + 0.5) * pas
            col = c(a1) if i % 2 == 0 else c(a2)
            w = 2 * 7.9 * math.tan(math.radians(pas / 2)) + 0.05
            with b.at((0, 0, 0), yaw=-az):
                b.wedge((-w / 2, 5.0, -7.9), (w / 2, 6.2, -(R - 0.2)), col, down="-z", collide=False, name="Store")
                b.box((-w / 2 + 0.02, 4.4, -7.9), (w / 2 - 0.02, 5.0, -7.75), col, collide=False, shadow=False,
                      name="Lambrequin")
        # toit plat bordé (clouté) et coupole basse
        b.cyl((0, 6.3, 0), R + 0.3, 0.6, c(S["bord"]), studs="top", name="Rebord")
        rcap = R - 0.2
        ycap = 6.6 - math.sqrt(rcap ** 2 - 5.0 ** 2)
        b.ball((0, ycap, 0), rcap, blanc, name="Coupole")
        haut = _objet_geant(b, v, ycap + rcap - 0.35)
        # comptoir avant et tabourets
        with b.group("Comptoir"):
            b.box((-2.8, 0.6, -6.7), (2.8, 3.0, -5.5), blanc, name="Comptoir")
            b.box((-2.8, 1.4, -6.8), (2.8, 1.8, -6.7 + 0.05), c(S["bord"]), collide=False, name="Bande")
            b.box((-3.1, 3.0, -7.1), (3.1, 3.4, -5.4), c(S["bord"]), studs="top", name="Plateau")
            for x in (-2.0, 0.0, 2.0):
                b.cyl((x, 0.95, -7.35), 0.15, 1.9, c("gris_tech_fonce"), collide=False, name="Pied")
                b.cyl((x, 2.05, -7.35), 0.55, 0.3, c(S["store"][0]), studs="top", name="Assise")
        # tableau de menu sur pieds, en pictogrammes (carrés de couleur, aucun texte)
        with b.at((5.0, 0, -6.2), yaw=-25, group="Menu"):
            for x in (-0.9, 0.9):
                b.box((x - 0.12, 0, -0.12), (x + 0.12, 3.4, 0.12), c("gris_tech_fonce"), name="Pied")
            b.box((-1.3, 1.4, -0.2), (1.3, 3.6, 0.0), _col(TABLEAU), name="Tableau")
            b.box((-1.3, 3.6, -0.25), (1.3, 3.9, 0.05), c(S["bord"]), collide=False, name="Fronton")
            cols = S["menu"]
            for k in range(6):
                x = -0.75 + (k % 3) * 0.75
                y = 2.9 - (k // 3) * 0.9
                b.box((x - 0.25, y - 0.25, -0.32), (x + 0.25, y + 0.25, -0.2), _col(cols[k % 3]), collide=False,
                      shadow=False, name="Picto")
    return {"emprise": (16, 16), "hauteur": round(haut, 2)}


# ---------------------------------------------------------------------------
# 3) Habitation de la planète extraterrestre
# ---------------------------------------------------------------------------

def _dome_alien(b, x: float, z: float, r: float, hb: float, blanc, rng, *, hublots, porche=True, aiguilles=0,
                pile=True, y_sol=0.5):
    """Dôme blanc sur tambour (hauteur hb), liseré lavande, hublots-bulles verts, porche rond, sommet."""
    ctr = (x, hb, z)
    b.cyl((x, hb / 2, z), r, hb, blanc, name="Tambour")
    b.ball(ctr, r, blanc, name="Dome")
    b.cyl((x, hb + 0.2, z), r + 0.12, 0.4, c("coque_lavande"), collide=False, name="Liseré")
    for az, el, rw in hublots:
        _bulle(b, ctr, r, az, el, rw)
    if porche:
        rt = round(max(1.6, 0.36 * r), 2)
        yc = 0.9
        z_av = z - r - 1.6
        z_in = z - math.sqrt(max(r * r - rt * rt, 1.0)) + 0.5
        b.cyl((x, yc, (z_av + 0.3 + z_in) / 2), rt, z_in - z_av - 0.3, blanc, axis="z", name="Porche")
        b.cyl((x, yc, z_av + 0.35), rt + 0.25, 0.7, c("coque_lavande"), axis="z", name="Encadrement")
        b.cyl((x, yc, z_av), rt - 0.45, 0.3, _col(PORTE_ALIEN), axis="z", name="Porte")
        b.cyl((x, yc + 0.5 * (rt - 0.45), z_av - 0.15), 0.4, 0.2, c("vitre_verte"), axis="z", material="Glass",
              collide=False, shadow=False, name="Judas")
        b.box((x - rt + 0.3, y_sol - 0.3, z_av - 0.9), (x + rt - 0.3, y_sol, z_av + 0.4), c("sable_clair"),
              studs="top", name="Marche")
    top = hb + r
    if pile:
        # pile d'anneaux blancs, mât et feu vert
        b.cyl((x, top + 0.0, z), 1.3, 0.6, blanc, name="Pile")
        b.cyl((x, top + 0.55, z), 0.9, 0.5, c("coque_lavande"), collide=False, name="Pile")
        b.cyl((x, top + 1.0, z), 0.55, 0.4, blanc, collide=False, name="Pile")
        b.cyl((x, top + 2.2, z), 0.12, 2.0, c("blanc_ombre"), collide=False, shadow=False, name="Mat")
        b.box((x - 0.2, top + 3.2, z - 0.2), (x + 0.2, top + 3.6, z + 0.2), c("neon_cyan"), material="Neon",
              collide=False, shadow=False, name="Feu")
    for k in range(aiguilles):
        az = (k * 360 / aiguilles) + 90
        el = 58
        base = np.array(ctr) + _dir(az, el) * (r - 0.2)
        axe = np.array([0, 1, 0]) * 0.85 + _dir(az, 0) * 0.35
        axe /= np.linalg.norm(axe)
        for j, (rr, ll) in enumerate(((0.5, 1.0), (0.32, 1.0), (0.16, 1.0))):
            b.part("cyl", (ll, 2 * rr, 2 * rr), tuple(base + axe * (0.5 + j * 0.95)), _repere(axe), blanc,
                   collide=False, name="Aiguille")
    return top


def maison_alien(b, variant: int = 0, rayon: float = 7) -> dict:
    """Habitation extraterrestre (voir l'en-tête du module). Emprise (2r + 4) × (2r + 4), centrée."""
    rng = b.rng
    v = variant % 4
    r = float(rayon)
    blanc = vary("blanc_dome", rng, 0.015)
    sable, sable_c, sable_f = c("sable"), c("sable_clair"), c("sable_fonce")
    hb = 1.2
    with b.group("DomeAlien"):
        if v == 1:
            # grappe : dôme principal (0,82 r) et petit dôme satellite (0,48 r)
            rm, rs = round(0.82 * r, 2), round(0.48 * r, 2)
            xm = -(r + 2) + rm + 0.9
            xs = (r + 2) - rs - 0.9
            b.cyl((xm, 0.25, 0), rm + 0.8, 0.5, sable, studs="top", name="Socle")
            b.cyl((xs, 0.2, 1.5), rs + 0.8, 0.4, sable_c, studs="top", name="Socle")
            top = _dome_alien(b, xm, 0, rm, hb, blanc, rng, hublots=[(-50, 30, 1.1), (-110, 26, 0.9), (40, 34, 1.0),
                                                                     (170, 30, 1.0)])
            _dome_alien(b, xs, 1.5, rs, 0.8, blanc, rng, hublots=[(-20, 32, 0.8), (80, 30, 0.7)], porche=False,
                        pile=False, aiguilles=0)
            b.ball((xs, 0.8 + rs + 0.1, 1.5), 0.7, c("vitre_verte"), material="Glass", collide=False, name="Bulle")
            hauteur = top + 3.6
        elif v == 2:
            # socle en gradins et deux aiguilles
            b.cyl((0, 0.25, 0), r + 1.8, 0.5, sable_f, studs="top", name="Gradin")
            b.cyl((0, 0.75, 0), r + 1.0, 0.5, sable, studs="top", name="Gradin")
            with b.at((0, 1.0, 0)):
                top = _dome_alien(b, 0, 0, r, hb, blanc, rng,
                                  hublots=[(-45, 30, 1.2), (45, 30, 1.2), (-105, 26, 1.0), (105, 26, 1.0), (180, 30, 1.0)],
                                  aiguilles=2, pile=False, y_sol=0.0)
            hauteur = top + 1.0 + 2.9
        elif v == 3:
            # petit dôme à grande baie ronde
            b.cyl((0, 0.25, 0), r + 0.9, 0.5, sable, studs="top", name="Socle")
            top = _dome_alien(b, 0, 0, r, hb, blanc, rng, hublots=[(70, 28, 0.8), (140, 30, 0.8)])
            ctr = (0.0, hb, 0.0)
            rg = round(0.42 * r, 2)
            n = _dir(-42, 30)
            C = np.array(ctr)
            _disque(b, C + n * (r - 0.15), n, rg + 0.35, 0.6, c("coque_lavande"), collide=False, name="Cadre")
            _disque(b, C + n * (r + 0.2), n, rg, 0.3, c("vitre_verte"), material="Glass", reflectance=0.1,
                    collide=False, shadow=False, name="Baie")
            hauteur = top + 3.6
        else:
            b.cyl((0, 0.25, 0), r + 0.9, 0.5, sable, studs="top", name="Socle")
            top = _dome_alien(b, 0, 0, r, hb, blanc, rng,
                              hublots=[(-48, 30, 1.1), (48, 30, 1.1), (-112, 26, 0.9), (112, 26, 0.9), (180, 32, 1.0)],
                              aiguilles=0)
            hauteur = top + 3.6
        # buissons bleu-verts au pied
        for k, (x, z, rr) in enumerate(((-(r + 0.6), -(r * 0.55), 0.9), (r + 0.4, -(r * 0.35), 0.75))):
            if v == 1 and k == 1:
                continue
            b.ball((x, 0.5 + rr * 0.45, z), rr, vary("buisson_alien", rng, 0.05), collide=False, name="Buisson")
    return {"emprise": (2 * r + 4, 2 * r + 4), "hauteur": round(hauteur, 2)}


# ---------------------------------------------------------------------------
# 4) Voiture volante garée
# ---------------------------------------------------------------------------

def voiture_volante(b, variant: int = 0) -> dict:
    """Voiture volante rétro-futuriste (longueur 9 le long de Z, largeur 5, hauteur ≤ 4) : caisse arrondie
    (bloc + demi-cylindres avant et arrière), liseré blanc, bulle de verre, ailerons, patins sombres au sol."""
    v = variant % 4
    corps = c(("bande_rouge", "bande_jaune", "bande_bleue", "bande_turquoise")[v])
    fonce = c("gris_tech_fonce")
    blanc = c("blanc_dome")
    with b.group("VoitureVolante"):
        for x in (-1.5, 1.5):
            for z in (-2.6, 2.6):
                b.cyl((x, 0.25, z), 0.75, 0.5, fonce, name="Patin")
        b.box((-1.9, 0.5, -2.6), (1.9, 0.8, 2.6), c("noir"), name="Dessous")
        b.box((-2.3, 0.8, -2.2), (2.3, 2.1, 2.2), corps, name="Caisse")
        for z in (-2.2, 2.2):
            b.cyl((0, 1.45, z), 2.3, 1.3, corps, name="Caisse")
        b.box((-2.4, 1.3, -2.2), (2.4, 1.6, 2.2), blanc, collide=False, name="Liseré")
        for z in (-2.2, 2.2):
            b.cyl((0, 1.45, z), 2.4, 0.3, blanc, collide=False, name="Liseré")
        b.box((-1.0, 2.1, 0.3), (1.0, 2.9, 1.1), shade(corps, 0.6), collide=False, name="Siege")
        b.ball((0, 2.0, -0.1), 1.9, c("vitre"), material="Glass", transparency=0.3, collide=False, name="Bulle")
        for x in (-1.5, 1.5):
            b.wedge((x - 0.15, 2.1, 2.4), (x + 0.15, 3.3, 4.1), corps, down="-z", collide=False, name="Aileron")
        b.box((-1.65, 3.0, 3.5), (1.65, 3.3, 4.1), blanc, collide=False, name="Becquet")
        for s in (-1, 1):
            n = _dir(s * 28, 0)
            p = np.array([0, 1.75, -2.2]) + n * 2.32
            _disque(b, p, n, 0.42, 0.3, c("neon_blanc"), material="Neon", collide=False, shadow=False, name="Phare")
            n2 = _dir(180 + s * 30, 0)
            p2 = np.array([0, 1.75, 2.2]) + n2 * 2.32
            _disque(b, p2, n2, 0.32, 0.3, c("rouge"), material="Neon", collide=False, shadow=False, name="Feu")
        b.cyl((0, 1.1, 4.45), 0.45, 0.4, fonce, axis="z", collide=False, name="Tuyere")
    return {"emprise": (5, 9), "hauteur": 3.9}
