"""Architecture rétro-futuriste en dômes de la zone 4 (style « stud »).

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :
- maison_dome(rayon=9) : maison-dôme blanche du village terrestre (r = 6 à 10), socle clair clouté à liseré
    coloré, bande de couleur franche et filet d'une seconde couleur, hublots ronds à reflet, tunnel d'entrée
    à porte ronde, équipement de toit, jardinet (massif fleuri, lampadaire, pot, boîte aux lettres) ;
    v0 dôme seul, bande orange, parabole ; v1 dôme et aile cylindrique basse, bande bleue ;
    v2 deux dômes (r et 0,65 r) reliés par un tube, bande rouge ; v3 maison haute (dôme sur un étage
    cylindrique à couronne de hublots), bande jaune ; v4 dôme à terrasse de toit (garde-corps, parasol),
    bande turquoise. Au-delà de 4, mêmes formes, couleurs décalées. Emprise : X ≤ 2r + 4 (v2 : 2r + 12), Z ≤ 2r + 6.
- boutique_dome() : boutique ronde 16 × 16 au bord de la rue, vitrine, store rayé, comptoir et tabourets,
    tableau de menu en pictogrammes, et un OBJET GÉANT sur le toit (aucun texte) :
    v0 cornet de glace, v1 brioche vapeur dans son panier de bambou, v2 gobelet à paille, v3 beignet glacé debout.
- maison_alien(rayon=7) : habitation de la planète extraterrestre, dôme blanc sur tambour, hublots-bulles
    verts, socle de sable, cheminées courtes, lampe et arbuste boule ; v0 dôme seul, v1 grappe de deux dômes,
    v2 socle en gradins et deux aiguilles, v3 petit dôme à grande baie ronde. Emprise (2r + 4) × (2r + 4).
- voiture_volante() : voiture volante garée (9 × 5, ≤ 4 de haut), sans roues : quatre patins ronds à halo ;
    v0 rouge, v1 jaune, v2 bleue, v3 turquoise.

Repère (voir CONVENTIONS.md) : origine au centre de l'emprise au sol, y = 0 au sol, l'AVANT regarde -Z
(la mise en page tourne l'asset de ±90° : X local court alors le long du couloir).
Azimut des hublots : 0 = avant (-Z), +90 = côté +X. Vu de la rue (depuis -Z), +X est à GAUCHE.
Les emprises sont celles de la spécification : elles ne dépendent pas de la largeur du couloir (c'est
`zone.py` qui recule les façades quand le couloir s'élargit).

Technique des dômes : une boule centrée au sol (moitié basse cachée), une bande = un cylindre vertical
de rayon (rayon de la sphère au bord bas de la bande) + 0,15 ; hublot = disque de cadre enfoncé de 0,35
dans la sphère, disque de verre qui dépasse de 0,15 du cadre, puis petit reflet blanc qui dépasse encore
de 0,15 (aucune face coplanaire).

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
SOCLE = mix(c("gris_tech"), c("blanc_dome"), 0.4)   # socle clair des maisons (gris « tech » éclairci)
BRIOCHE = "#FAE8CA"        # pâte de brioche vapeur (crème chaud, se détache des dômes blancs)
BRIOCHE_PLI = "#E0C496"
GAUFRE = "#E0A85C"         # cornet gaufré
GAUFRE_FONCE = "#B9803E"
GLACE_ROSE = "#F59CC8"     # boule fraise
GLACE_CHOCO = "#7A4A2E"    # boule chocolat
CREME = "#FFF8EC"
PATE_BEIGNET = "#E2B072"
GLACAGE_ROSE = "#F27BB8"
TABLEAU = "#2C3440"        # fond du tableau de menu
PORTE_ALIEN = "#4FA89A"    # porte des dômes extraterrestres (sarcelle)
LUMIERE = "#FFE08A"        # hublots et vitrines éclairés (jaune chaud, Neon)


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
    """Matrice de rotation dont la première colonne (axe d'un cylindre Roblox) est `axe`.
    La deuxième colonne est la tangente « montante », la troisième la tangente horizontale."""
    x = np.asarray(axe, float)
    x = x / np.linalg.norm(x)
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return np.column_stack([x, y, z])


def _repere_bloc(axe_x, axe_y) -> np.ndarray:
    """Matrice de rotation d'un bloc : X local le long de `axe_x`, Y local au plus près de `axe_y`."""
    x = np.asarray(axe_x, float)
    x = x / np.linalg.norm(x)
    z = np.cross(x, np.asarray(axe_y, float))
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
    return b.part("cyl", (ep, 2 * rayon, 2 * rayon), tuple(np.asarray(centre, float)), _repere(normale),
                  _col(couleur), **kw)


def _rayon_sphere(r: float, t0: float, t1: float) -> float:
    """Plus grand rayon horizontal d'une sphère de rayon r entre les hauteurs t0 et t1 (relatives au centre)."""
    m = 0.0 if t0 <= 0 <= t1 else min(abs(t0), abs(t1))
    return math.sqrt(max(r * r - m * m, 0.0))


def _bande(b, ctr, r: float, y: float, h: float, couleur, ep: float = 0.15, prise: float = 0.0, name: str = "Bande"):
    """Bande colorée autour d'une sphère (centre `ctr`, rayon r), centrée à la hauteur absolue y.

    `prise` = 0 : rayon de la sphère au bord bas de la bande (anneau net, léger débord en haut) ;
    `prise` = 0,5 : rayon pris à mi-hauteur (le bas s'enfonce dans la sphère, débord plus discret)."""
    cx, cy, cz = ctr
    t0 = y - h / 2 - cy
    rb = _rayon_sphere(r, t0 + prise * h, y + h / 2 - cy) + ep
    return b.cyl((cx, y, cz), rb, h, _col(couleur), collide=False, name=name)


def _verre(b, C, n, R: float, rw: float, cadre, verre, neon: bool, reflet: bool):
    """Cadre, verre et reflet d'un hublot rond posé sur une surface de rayon R (centre C, normale n)."""
    _disque(b, C + n * (R - 0.1), n, rw + 0.3, 0.5, cadre, collide=False, shadow=False, name="Cadre")
    _disque(b, C + n * (R + 0.15), n, rw, 0.3, LUMIERE if neon else verre,
            material="Neon" if neon else "Glass", collide=False, shadow=False, name="Hublot")
    if reflet and not neon:
        M = _repere(n)
        p = C + n * (R + 0.35) + M[:, 1] * (0.42 * rw) + M[:, 2] * (0.3 * rw)
        _disque(b, p, n, max(0.12, 0.2 * rw), 0.2, "blanc", collide=False, shadow=False, name="Reflet")


def _hublot(b, ctr, r: float, az: float, el: float, rw: float, cadre, verre="vitre", neon=False, reflet=True):
    """Hublot rond sur une sphère (centre ctr, rayon r) : cadre enfoncé, verre, petit reflet."""
    _verre(b, np.asarray(ctr, float), _dir(az, el), r, rw, cadre, verre, neon, reflet)


def _hublot_cyl(b, cx: float, cz: float, R: float, az: float, y: float, rw: float, cadre, verre="vitre", neon=False,
                reflet=False):
    """Hublot rond sur un mur cylindrique vertical (centre cx, cz ; rayon R)."""
    _verre(b, np.array([cx, y, cz]), _dir(az, 0.0), R, rw, cadre, verre, neon, reflet)


def _bulle(b, ctr, r: float, az: float, el: float, rw: float, couleur="vitre_verte"):
    """Hublot-bulle : petite boule de verre à moitié enfoncée dans la sphère."""
    p = np.asarray(ctr, float) + _dir(az, el) * (r - 0.1 * rw)
    b.ball(tuple(p), rw, _col(couleur), material="Glass", reflectance=0.1, collide=False, shadow=False, name="Bulle")


def _rivets_bande(b, ctr, r: float, y: float, h: float, n: int, couleur, *, ep: float = 0.15,
                  az_libre: float = 34.0, a0: float = 0.0):
    """Rangée de petits rivets carrés sur la bande posée par `_bande(b, ctr, r, y, h, ..., ep)` (coordonnées
    locales), sauf devant le porche (|azimut| < az_libre) : rythme « technique » lisible de loin."""
    cx, cy, cz = ctr
    rb = _rayon_sphere(r, y - h / 2 - cy, y + h / 2 - cy) + ep
    for i in range(n):
        az = a0 + 360 * (i + 0.5) / n
        az = (az + 180) % 360 - 180
        if abs(az) < az_libre:
            continue
        with b.at((cx, 0, cz), yaw=-az):
            b.box((-0.28, y - 0.22, -(rb + 0.2)), (0.28, y + 0.22, -(rb - 0.1)), _col(couleur), collide=False,
                  shadow=False, name="Rivet")


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


def _hauteur(b, i0: int) -> float:
    """Hauteur réelle (au-dessus de l'origine de l'asset) des pièces émises depuis l'indice i0.
    Les repères de `Builder.at` ne tournent qu'autour de Y : la hauteur ne dépend pas du placement."""
    y0 = float(b.to_world((0, 0, 0))[1])
    h = 0.0
    for p in b.parts[i0:]:
        R = np.asarray(p.rot).reshape(3, 3)
        h = max(h, p.pos[1] + float((np.abs(R) @ (np.asarray(p.size) / 2))[1]) - y0)
    return round(float(h), 2)


# ---------------------------------------------------------------------------
# Sous-ensembles communs des maisons-dômes
# ---------------------------------------------------------------------------

def _socle(b, cx: float, cz: float, rr: float, h: float, S: dict, name: str = "Socle"):
    """Socle rond clair clouté, ceinturé d'un liseré de la couleur de la bande (décollé du sol)."""
    b.cyl((cx, h / 2, cz), rr, h, SOCLE, studs="top", name=name)
    b.cyl((cx, 0.25, cz), rr + 0.15, 0.3, c(S["bande"]), collide=False, name="Liseré")


def _porche(b, x: float, z_masse: float, z_av: float, rt: float, yc: float, S: dict, *, lampes=True):
    """Tunnel d'entrée horizontal (axe z) à moitié enterré, de l'intérieur de la masse (z_masse) jusqu'à
    l'avant (z_av < z_masse) : encadrement coloré, bague, porte ronde à judas, marche cloutée, deux bornes."""
    blanc = S["blanc"]
    z0 = z_av + 0.3
    rp = rt - 0.55
    with b.group("Entree"):
        b.cyl((x, yc, (z0 + z_masse) / 2), rt, z_masse - z0, blanc, axis="z", name="Tunnel")
        b.cyl((x, yc, z_av + 0.35), rt + 0.3, 0.7, c(S["bande"]), axis="z", name="Encadrement")
        b.cyl((x, yc, z_av + 2.65), rt + 0.15, 0.5, c(S["bande2"]), axis="z", collide=False, name="Bague")
        b.cyl((x, yc, z_av), rp, 0.3, c(S["porte"]), axis="z", name="Porte")
        b.cyl((x, yc + rp * 0.55, z_av - 0.15), min(0.65, rp * 0.24), 0.2, c("vitre"), axis="z", material="Glass",
              collide=False, shadow=False, name="Judas")
        b.box((x + rp * 0.5 - 0.15, 1.3, z_av - 0.35), (x + rp * 0.5 + 0.15, 2.1, z_av - 0.1), c("gris_tech_fonce"),
              collide=False, shadow=False, name="Poignee")
        b.box((x - rt + 0.4, 0, z_av - 0.55), (x + rt - 0.4, 0.3, z_av + 0.6), c("gris_tech"), studs="top", name="Marche")
        if lampes:
            for s in (-1, 1):
                lx = x + s * (rt + 1.0)
                b.cyl((lx, 0.8, z_av + 0.1), 0.3, 1.6, blanc, collide=False, name="Borne")
                b.cyl((lx, 1.75, z_av + 0.1), 0.36, 0.3, c("neon_cyan"), material="Neon", collide=False, shadow=False,
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
            _disque(b, ctr, axe, 1.8, 0.3, blanc, collide=False, name="Parabole")
            _disque(b, ctr + axe * 0.1, axe, 0.8, 0.3, c(S["bande"]), collide=False, shadow=False, name="Creux")
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
            b.cyl((x, y + 4.55, z), 0.3, 0.4, c(S["bande"]), collide=False, name="Pointe")
            b.box((x - 0.15, y + 4.75, z - 0.15), (x + 0.15, y + 5.1, z + 0.15), c("rouge"), material="Neon",
                  collide=False, shadow=False, name="Balise")
        else:
            b.ball((x, y + 0.5, z), 1.0, c("vitre"), material="Glass", reflectance=0.1, collide=False, name="Lanterneau")


def _jardiniere(b, x: float, z: float, S: dict, r: float = 0.9):
    """Pot rond blanc à bague colorée et buisson arrondi."""
    b.cyl((x, 0.6, z), r, 1.2, S["blanc"], name="Bac")
    b.cyl((x, 0.95, z), r + 0.08, 0.3, c(S["bande2"]), collide=False, name="Bague")
    b.ball((x, 1.2 + r * 0.55, z), r * 0.95, c("feuillage"), collide=False, name="Buisson")


def _massif(b, x: float, z: float, S: dict, l: float = 2.6, yaw: float = 0.0, k: int = 0):
    """Massif fleuri : bac blanc à rebord coloré, terre, deux touffes vertes et trois fleurs carrées."""
    fleurs = (("fleur_rose", "fleur_jaune", "blanc"), ("fleur_jaune", "fleur_rose", "fleur_rose"))[k % 2]
    with b.at((x, 0, z), yaw=yaw, group="Massif"):
        b.box((-l / 2, 0, -0.6), (l / 2, 0.7, 0.6), S["blanc"], name="Bac")
        b.box((-l / 2 - 0.1, 0.45, -0.7), (l / 2 + 0.1, 0.8, 0.7), c(S["bande2"]), collide=False, name="Rebord")
        b.box((-l / 2 + 0.15, 0.6, -0.45), (l / 2 - 0.15, 0.95, 0.45), c("terre"), studs="top", collide=False,
              name="Terre")
        for s in (-1, 1):
            b.ball((s * l * 0.22, 1.05, 0.05), 0.5, c("feuillage_clair" if s < 0 else "feuillage"), collide=False,
                   shadow=False, name="Touffe")
        for j, fx in enumerate((-0.36, 0.0, 0.36)):
            y = 1.5 if j != 1 else 1.3
            b.boxc((fx * l, y, -0.05 + 0.1 * j), (0.5, 0.5, 0.5), c(fleurs[j]), collide=False, shadow=False,
                   name="Fleur")


def _lampe_jardin(b, x: float, z: float, S: dict, h: float = 4.6):
    """Lampadaire de jardin : mât blanc, tête ronde à disque lumineux (blanc, jamais orange)."""
    b.cyl((x, 0.2, z), 0.45, 0.4, c("gris_tech"), name="Socle")
    b.cyl((x, 0.4 + (h - 0.4) / 2, z), 0.16, h - 0.4, S["blanc"], collide=False, name="Mat")
    b.cyl((x, h + 0.2, z), 0.8, 0.4, S["blanc"], collide=False, name="Tete")
    b.cyl((x, h - 0.05, z), 0.6, 0.12, c("neon_blanc"), material="Neon", collide=False, shadow=False, name="Lumiere")
    b.cyl((x, h + 0.5, z), 0.35, 0.2, c(S["bande"]), collide=False, name="Capot")


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
    {"bande": "bande_orange", "bande2": "bande_turquoise", "porte": "porte"},
    {"bande": "bande_bleue", "bande2": "bande_jaune", "porte": "bande_jaune"},
    {"bande": "bande_rouge", "bande2": "bande_jaune", "porte": "bande_bleue"},
    {"bande": "bande_jaune", "bande2": "bande_violette", "porte": "bande_violette"},
    {"bande": "bande_turquoise", "bande2": "bande_orange", "porte": "bande_orange"},
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
    S["cadre"] = S["bande"]
    return S


def _elevation_hublots(r: float, rw: float, y_min: float) -> float:
    """Plus petite élévation (34 à 52°) qui met le bas du cadre d'un hublot au-dessus de y_min."""
    for el in range(34, 53):
        e = math.radians(el)
        if r * math.sin(e) - (rw + 0.3) * math.cos(e) >= y_min:
            return float(el)
    return 52.0


# ---------------------------------------------------------------------------
# 1) Maison-dôme du village terrestre
# ---------------------------------------------------------------------------

def maison_dome(b, variant: int = 0, rayon: float = 9) -> dict:
    """Maison-dôme blanche (voir l'en-tête du module).

    Étagement d'un dôme : socle clair clouté (0 → 1) à liseré, bande principale à 0,3 r, filet d'une seconde
    couleur juste au-dessus, couronne de hublots au-dessus du filet, anneau de faîte à 0,88 r, trappe et
    équipement au sommet. Le centre du dôme est à z = +1,5 pour que le tunnel d'entrée atteigne l'avant de
    l'emprise (z = -(r + 3)). Jardinet devant : massifs fleuris, lampadaire, pot, boîte aux lettres."""
    rng = b.rng
    i0 = len(b.parts)
    v = variant % 5
    r = float(rayon)
    S = _style_maison(variant, rng)
    blanc = S["blanc"]
    cz = 1.5
    rt = round(0.42 * r, 2)                   # rayon du tunnel d'entrée
    yc = round(0.25 * rt, 2)
    z_av = -(r + 2.4)
    zg = -(r + 1.5)                           # ligne du jardinet
    xm = rt + 3.1                             # centre des massifs fleuris
    lum = rng.random(10) < 0.3                # hublots éclairés au hasard
    rw = max(0.85, round(0.13 * r, 2))
    hb = round(min(1.4, max(1.2, 0.14 * r)), 2)   # hauteur de la bande principale
    larg = 2 * r + (12 if v == 2 else 4)

    with b.group("MaisonDome"):
        if v == 3:
            # ---- maison haute : étage cylindrique (rayon r), balcon annulaire, puis dôme
            he = 4.4
            ctr = (0.0, he, cz)
            _socle(b, 0, cz, r + 0.6, 0.8, S)
            b.cyl((0, he / 2, cz), r, he, blanc, name="Etage")
            b.ball(ctr, r, blanc, name="Dome")
            for i, az in enumerate((-52, -88, -124, -160, 160, 124, 88, 52)):
                _hublot_cyl(b, 0, cz, r, az, 2.4, 0.75, S["cadre"], neon=bool(lum[i]))
            with b.group("Balcon"):
                rbal = r + 1.3
                b.cyl((0, he + 0.1, cz), rbal, 0.6, c(S["bande"]), studs="top", name="Balcon")
                b.cyl((0, he - 0.35, cz), rbal - 0.4, 0.3, c("gris_tech"), collide=False, name="Sous-face")
                _anneau_poly(b, 0, cz, rbal - 0.25, he + 1.6, 12, blanc, poteaux=c("gris_tech"), h_pot=1.2, a0=15)
            el = 22
            for i, az in enumerate((-36, 36, -96, 96, 150, -150)):
                _hublot(b, ctr, r, az, el, rw, S["cadre"], neon=bool(lum[(i + 3) % 10]))
            _bande(b, ctr, r, he + 0.6 * r, 0.6, S["bande2"], ep=0.12)
            _bande(b, ctr, r, he + 0.88 * r, 0.45, S["bande"], ep=0.1, name="Faite")
            rt3 = round(0.3 * r, 2)
            _porche(b, 0, cz - math.sqrt(r * r - rt3 * rt3) + 0.6, z_av, rt3, 0.8, S)
            _equipement_toit(b, 0, he + r, cz, S, 1)
            _lampe_jardin(b, -(r + 1.2), -(r + 0.4), S)
            _massif(b, xm - (rt - rt3), zg, S, k=1)
            _jardiniere(b, -(rt3 + 2.6), zg, S, r=0.8)
        else:
            cx = {0: 0.0, 1: -1.25, 2: -5.2, 4: 0.0}[v]
            ctr = (cx, 0.0, cz)
            _socle(b, cx, cz, r + 0.6, 1.0, S)
            b.ball(ctr, r, blanc, name="Dome")
            yb = 0.3 * r
            _bande(b, ctr, r, yb, hb, S["bande"])
            _rivets_bande(b, ctr, r, yb, hb, 12 if r >= 8 else 10, S["blanc"])
            _bande(b, ctr, r, yb + hb / 2 + 0.6, 0.35, S["bande2"], ep=0.12, name="Filet")
            el = _elevation_hublots(r, rw, yb + hb / 2 + 0.6 + 0.175 + 0.35)
            if v != 4:
                _bande(b, ctr, r, 0.88 * r, 0.45, S["bande"], ep=0.1, prise=0.5, name="Faite")
            hublots = {
                0: [-52, 52, -110, 110, 180],
                1: [-52, -110, 160, 30],
                2: [-52, -110, 40, -165],
                4: [-50, 50, -112, 112, 180],
            }[v]
            for i, az in enumerate(hublots):
                _hublot(b, ctr, r, az, el, rw, S["cadre"], neon=bool(lum[i]))
            _porche(b, cx, cz - math.sqrt(max(r * r - (yc + rt) ** 2, 1.0)) + 0.4, z_av, rt, yc, S)

            if v == 0:
                _equipement_toit(b, cx, r, cz, S, 0)
                _massif(b, xm, zg, S, k=0)
                _massif(b, -xm, zg, S, k=1)
                _lampe_jardin(b, r + 1.2, -(r + 0.4), S)
                _boite_lettres(b, -(r + 1.2), -(r - 1.0), S)
                _clim(b, 0.707 * (r + 1.7), cz + 0.707 * (r + 1.7), 225)
            elif v == 1:
                # aile cylindrique basse à l'avant côté +X : toit-terrasse clouté, lanterneau, panneaux solaires
                ra = round(0.5 * r + 0.5, 2)
                ha = round(0.45 * r + 1.0, 2)
                ax = (r + 2) - ra - 0.45
                azc = cz - 0.5 * r
                with b.group("Aile"):
                    b.cyl((ax, 0.4, azc), ra + 0.4, 0.8, SOCLE, studs="top", name="Socle")
                    b.cyl((ax, ha / 2, azc), ra, ha, blanc, name="Aile")
                    b.cyl((ax, 1.6, azc), ra + 0.15, 0.6, c(S["bande"]), collide=False, name="Bande")
                    b.cyl((ax, 2.2, azc), ra + 0.12, 0.2, c(S["bande2"]), collide=False, name="Filet")
                    b.cyl((ax, ha + 0.25, azc), ra + 0.35, 0.5, c(S["bande"]), studs="top", name="Toiture")
                    b.ball((ax + 0.35 * ra, ha + 0.5, azc - 0.2 * ra), 1.1, c("vitre"), material="Glass",
                           reflectance=0.1, collide=False, name="Lanterneau")
                    for k, dz in enumerate((-0.2, 1.3)):
                        b.part("block", (2.6, 0.2, 1.3), (ax - 0.15 * ra, ha + 1.0, azc + dz), rot_x(-25),
                               c("vitre_fonce"), collide=False, name="Solaire")
                        b.box((ax - 0.15 * ra - 0.15, ha + 0.5, azc + dz - 0.15),
                              (ax - 0.15 * ra + 0.15, ha + 0.9, azc + dz + 0.15), c("gris_tech_fonce"),
                              collide=False, shadow=False, name="Pied")
                    for i, az in enumerate((-35, 25, 85, 145)):
                        _hublot_cyl(b, ax, azc, ra, az, 0.55 * ha + 0.9, 0.65, S["cadre"], neon=bool(lum[5 + i]),
                                    reflet=(i < 2))
                _equipement_toit(b, cx, r, cz, S, 1)
                _massif(b, max(cx - xm, -(r + 2) + 1.45), zg, S, k=1)
                _lampe_jardin(b, -(r + 1.2), -(r - 3.0), S, h=4.2)
            elif v == 2:
                # second dôme (0,65 r) relié par un tube court à collier coloré
                rs = round(0.65 * r, 2)
                sx = (r + 6) - rs - 0.75
                sz = cz + 2.5
                sctr = (sx, 0.0, sz)
                with b.group("Dome2"):
                    b.cyl((sx, 0.4, sz), rs + 0.6, 0.8, SOCLE, studs="top", name="Socle")
                    b.ball(sctr, rs, blanc, name="Dome")
                    _bande(b, sctr, rs, 0.32 * rs, 0.9, S["bande"])
                    _bande(b, sctr, rs, 0.32 * rs + 0.95, 0.3, S["bande2"], ep=0.12, name="Filet")
                    for i, (az, ee) in enumerate(((-15, 46), (70, 44), (150, 44))):
                        _hublot(b, sctr, rs, az, ee, max(0.7, rw * 0.75), S["cadre"], neon=bool(lum[5 + i]))
                    b.cyl((sx, rs - 0.1, sz), 1.1, 0.6, c("gris_tech"), name="Trappe")
                    b.ball((sx, rs + 0.2, sz), 0.8, c("vitre"), material="Glass", reflectance=0.1, collide=False,
                           name="Lanterneau")
                    d = np.array([sx - cx, 0.0, sz - cz])
                    dist = float(np.linalg.norm(d))
                    d /= dist
                    h_tube = 2.6
                    a = np.array(ctr) + d * (r - 2.5) + np.array([0, h_tube, 0])
                    e = np.array(sctr) - d * (rs - 2.0) + np.array([0, h_tube, 0])
                    b.part("cyl", (float(np.linalg.norm(e - a)), 3.6, 3.6), tuple((a + e) / 2), _repere(d), blanc,
                           name="Tube")
                    g = np.array(ctr) + d * (dist - rs + r) / 2 + np.array([0, h_tube, 0])
                    _disque(b, g, d, 2.1, 0.8, S["bande"], collide=False, name="Collier")
                _equipement_toit(b, cx, r, cz, S, 0)
                _massif(b, max(cx - xm, -(larg / 2) + 1.45), zg, S, k=0)
                _lampe_jardin(b, sx + 0.3, -(r + 1.6), S, h=4.2)
                _boite_lettres(b, sx - 2.6, -(r + 1.9), S)
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
                    px, pz = cx + 0.25 * rt_, cz + 0.15 * rt_
                    b.cyl((px, yt + 0.5 + 1.6, pz), 0.12, 3.2, c("metal"), collide=False, name="Manche")
                    for k, (rr, col) in enumerate(((2.6, S["bande2"]), (1.9, "blanc"), (1.2, S["bande2"]), (0.5, "blanc"))):
                        b.cyl((px, yt + 3.5 + 0.25 * k, pz), rr, 0.26, c(col), collide=False, name="Toile")
                    b.cyl((px, yt + 1.4, pz), 1.0, 0.2, blanc, studs="top", collide=False, name="Table")
                    b.cyl((px, yt + 0.95, pz), 0.15, 0.9, c("metal"), collide=False, name="Pied")
                    for k, (dx, dz) in enumerate(((-1.7, 0.4), (1.2, 1.4))):
                        b.cyl((px + dx, yt + 0.85, pz + dz), 0.5, 0.7, c(S["bande2"]), studs="top", collide=False,
                              name="Tabouret")
                    b.cyl((cx - 0.4 * rt_, yt + 1.0, cz - 0.2 * rt_), 0.7, 1.0, c("pave"), name="Pot")
                    b.ball((cx - 0.4 * rt_, yt + 2.1, cz - 0.2 * rt_), 0.95, c("feuillage"), collide=False,
                           name="Plante")
                _massif(b, xm, zg, S, k=0)
                _massif(b, -xm, zg, S, k=1)
                _lampe_jardin(b, r + 1.2, -(r + 0.4), S)
    return {"emprise": (larg, 2 * r + 6), "hauteur": _hauteur(b, i0)}


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
    """Objet géant posé sur le toit (base vers y0). Renvoie la hauteur de son sommet (≤ 16)."""
    with b.group("ObjetGeant"):
        if v == 0:
            # cornet de glace : cornet gaufré en gradins, bord, boule fraise (bas) qui coule sur le bord, boule
            # vanille (haut) semée de vermicelles colorés. Boules empilées : silhouette sans ambiguïté.
            hk = 0.6
            for k, rr in enumerate((0.45, 0.8, 1.15, 1.5, 1.85)):
                b.cyl((0, y0 + hk * k + hk / 2, 0), rr, hk, _col(GAUFRE if k % 2 == 0 else GAUFRE_FONCE), name="Cornet")
            yb = y0 + 5 * hk
            b.cyl((0, yb + 0.2, 0), 2.05, 0.4, _col(GAUFRE_FONCE), name="Bord")
            yb += 0.4
            yf, rf = yb + 0.95, 1.75
            b.ball((0, yf, 0), rf, _col(GLACE_ROSE), name="Boule")
            yv, rv = yf + 1.75, 1.35
            b.ball((0, yv, 0), rv, _col(CREME), name="Boule")
            # coulures roses : petits blocs accrochés au bord, qui pendent sur le cornet
            for az, L in ((-70, 0.6), (-30, 1.1), (10, 0.7), (45, 1.0), (85, 0.55), (150, 0.8), (-140, 0.9)):
                with b.at((0, 0, 0), yaw=-az):
                    b.box((-0.22, yb - 0.45 - L, -2.15), (0.22, yb - 0.05, -1.75), _col(GLACE_ROSE),
                          collide=False, shadow=False, name="Coulure")
            # vermicelles sur la boule vanille
            cols = ("bande_jaune", "bande_turquoise", "bande_rouge", "bande_violette", "bande_bleue", "fleur_rose")
            for k, (az, el) in enumerate(((-40, 35), (20, 55), (75, 30), (140, 45), (-110, 50), (-170, 30))):
                q = np.array([0, yv, 0]) + _dir(az, el) * (rv - 0.02)
                b.boxc(tuple(q), (0.45, 0.16, 0.16), c(cols[k]), yaw=az * 1.7 + 30, collide=False, shadow=False,
                       name="Vermicelle")
            return yv + rv
        if v == 1:
            # brioche vapeur : base cylindrique et calotte aplatie (largeur 9, hauteur 3,1), dans un grand panier
            # de bambou à cerclages sombres ; huit plis qui convergent vers un nœud, point rouge au sommet
            b.cyl((0, y0 + 0.2, 0), 5.4, 0.4, c("blanc_dome"), studs="top", name="Toit")
            yp = y0 + 0.4
            hp = 1.6
            b.cyl((0, yp + hp / 2, 0), 4.8, hp, c("bois_clair"), name="Panier")
            for yy in (0.35, 1.25):
                b.cyl((0, yp + yy, 0), 4.92, 0.3, c("bois_fonce"), collide=False, name="Cerclage")
            yp += hp
            hbase, hcap, rb = 0.7, 2.4, 4.6
            b.cyl((0, yp + hbase / 2, 0), 4.5, hbase, _col(BRIOCHE), name="Brioche")
            ys = yp + hbase + hcap              # sommet de la calotte
            ycb = ys - rb                       # centre de la boule (cachée dans le panier et la boutique)
            b.ball((0, ycb, 0), rb, _col(BRIOCHE), name="Brioche")
            el = 64.0
            for k in range(8):
                n = _dir(k * 45 + 22.5, el)
                t = np.array([n[0], 0.0, n[2]])
                t /= np.linalg.norm(t)
                # tangente le long du méridien, vers le bas
                desc = t * math.sin(math.radians(el)) - np.array([0, 1, 0]) * math.cos(math.radians(el))
                p = np.array([0, ycb, 0]) + n * (rb + 0.03)
                b.part("block", (2.2, 0.36, 0.5), tuple(p), _repere_bloc(desc, n), _col(BRIOCHE_PLI),
                       collide=False, shadow=False, name="Pli")
            b.cyl((0, ys + 0.15, 0), 1.0, 0.5, _col(BRIOCHE_PLI), name="Noeud")
            b.cyl((0, ys + 0.55, 0), 0.55, 0.4, _col(BRIOCHE), collide=False, name="Noeud")
            b.cyl((0, ys + 0.8, 0), 0.45, 0.12, c("bande_rouge"), collide=False, shadow=False, name="Point")
            return ys + 0.86
        if v == 2:
            # gobelet à paille : gobelet évasé à manchon coloré et pictogramme de fruit (aucun texte),
            # couvercle bombé, longue paille rayée inclinée
            ys = y0
            for k, (rr, hh, col) in enumerate(((1.9, 1.2, "blanc"), (2.2, 1.3, "bande_turquoise"), (2.5, 1.2, "blanc"))):
                b.cyl((0, ys + hh / 2, 0), rr, hh, c(col), name="Gobelet")
                ys += hh
            yp = y0 + 1.2 + 0.65
            b.cyl((0, yp, -2.25), 0.55, 0.3, c("blanc"), axis="z", collide=False, shadow=False, name="Picto")
            b.cyl((0, yp - 0.05, -2.45), 0.36, 0.2, _col("#F27BC0"), axis="z", collide=False, shadow=False, name="Picto")
            b.box((0.0, yp + 0.25, -2.6), (0.3, yp + 0.45, -2.4), c("feuillage"), collide=False, shadow=False,
                  name="Picto")
            b.cyl((0, ys + 0.2, 0), 2.7, 0.4, _col("#F27BC0"), name="Couvercle")
            b.ball((0, ys - 0.6, 0), 2.1, _col("#F7A9D6"), name="Dome")
            axe = np.array([0.35, 1.0, 0.15])
            axe /= np.linalg.norm(axe)
            base = np.array([0.0, ys + 0.9, 0.0])
            ls, rp = 0.95, 0.38
            for k, col in enumerate(("blanc", "bande_rouge", "blanc")):
                b.part("cyl", (ls, 2 * rp, 2 * rp), tuple(base + axe * (ls / 2 + ls * k)), _repere(axe), c(col),
                       collide=False, name="Paille")
            return float(base[1] + axe[1] * 3 * ls + rp * math.sqrt(1 - axe[1] ** 2))
        # v3 : beignet géant debout, glaçage rose et vermicelles
        b.box((-1.6, y0, -1.0), (1.6, y0 + 0.8, 1.0), c("gris_tech"), studs="top", name="Socle")
        R, rb = 2.1, 1.1
        yc = y0 + 0.8 + R + rb - 0.4
        cols = ("bande_jaune", "bande_turquoise", "blanc", "bande_violette")
        for k in range(10):
            a = 2 * math.pi * k / 10
            px, py = R * math.cos(a), yc + R * math.sin(a)
            b.ball((px, py, 0.15), rb, _col(PATE_BEIGNET), name="Pate")
            b.ball((px, py, -0.2), rb * 0.86, _col(GLACAGE_ROSE), name="Glacage")
            if k % 2 == 0:
                b.box((px - 0.18, py - 0.06, -1.27), (px + 0.18, py + 0.06, -1.05), c(cols[k // 2 % 4]),
                      collide=False, shadow=False, name="Vermicelle")
        return yc + R + rb


def boutique_dome(b, variant: int = 0) -> dict:
    """Boutique ronde (rayon 6,4) : vitrine, store rayé, toit plat bordé (coupole basse sauf pour la brioche),
    comptoir avant, tabourets, tableau de menu en pictogrammes, objet géant sur le toit.
    Emprise 16 × 16, hauteur ≤ 16."""
    rng = b.rng
    i0 = len(b.parts)
    v = variant % 4
    S = dict(STYLES_BOUTIQUE[v])
    blanc = vary("blanc_dome", rng, 0.015)
    gris = c("gris_tech")
    R = 6.4
    H = 6.8                      # haut du mur
    with b.group("Boutique"):
        b.cyl((0, 0.3, 0), 7.2, 0.6, SOCLE, studs="top", name="Socle")
        b.cyl((0, 0.6 + (H - 0.6) / 2, 0), R, H - 0.6, blanc, name="Mur")
        b.cyl((0, 1.45, 0), R + 0.12, 0.3, c(S["bord"]), collide=False, name="Plinthe")
        b.cyl((0, 5.55, 0), R + 0.2, 0.3, c(S["bord"]), collide=False, name="Bandeau")
        # vitrine : panneaux tangents entre montants, quelques-uns éclairés ; une porte vitrée
        n = 16
        pas = 360 / n
        for i in range(-4, 5):
            az = i * pas
            with b.at((0, 0, 0), yaw=-az):
                if i == -3:
                    b.box((-1.05, 0.6, -(R + 0.2)), (1.05, 5.2, -(R - 0.1)), c(S["porte"]), name="Porte")
                    b.box((-0.7, 2.4, -(R + 0.3)), (0.7, 4.7, -(R + 0.1)), c("vitre"), material="Glass",
                          collide=False, shadow=False, name="Vitre")
                    b.box((0.55, 2.0, -(R + 0.4)), (0.75, 2.6, -(R + 0.15)), c("gris_tech_fonce"), collide=False,
                          shadow=False, name="Poignee")
                else:
                    neon = i in (-1, 2)
                    b.box((-1.05, 1.8, -(R + 0.2)), (1.05, 5.2, -(R - 0.1)),
                          _col(LUMIERE) if neon else c("vitre"), material="Neon" if neon else "Glass",
                          collide=False, shadow=False, name="Vitrine")
            with b.at((0, 0, 0), yaw=-(az + pas / 2)):
                b.box((-0.2, 1.6, -(R + 0.35)), (0.2, 5.4, -(R - 0.1)), blanc, collide=False, name="Montant")
        with b.at((0, 0, 0), yaw=-(-4.5 * pas)):
            b.box((-0.2, 1.6, -(R + 0.35)), (0.2, 5.4, -(R - 0.1)), blanc, collide=False, name="Montant")
        # store rayé en couronne (coins tournés) : les pans colorés sont relevés de 0,06 pour couvrir
        # les recouvrements (rayures nettes), lambrequin et rampe lumineuse
        a1, a2 = S["store"]
        ro = 7.8
        w = 2 * ro * math.tan(math.radians(pas / 2)) + 0.05
        for i in range(n):
            az = (i + 0.5) * pas
            col = c(a1) if i % 2 == 0 else c(a2)
            dy = 0.06 if i % 2 == 0 else 0.0
            with b.at((0, 0, 0), yaw=-az):
                b.wedge((-w / 2, H - 0.9 + dy, -ro), (w / 2, H + dy, -(R - 0.2)), col, down="-z", collide=False,
                        name="Store")
                b.box((-w / 2 + 0.02, H - 1.5 + dy, -ro), (w / 2 - 0.02, H - 0.9 + dy, -(ro - 0.15)), col,
                      collide=False, shadow=False, name="Lambrequin")
        b.cyl((0, H - 1.15, 0), R + 0.12, 0.15, c("neon_blanc"), material="Neon", collide=False, shadow=False,
              name="Rampe")
        # toit plat bordé (clouté) puis coupole basse (sauf v1 : panier de la brioche posé à plat)
        b.cyl((0, H + 0.2, 0), R + 0.3, 0.4, c(S["bord"]), studs="top", name="Rebord")
        if v == 1:
            _objet_geant(b, v, H + 0.4)
        else:
            rcap = 6.3
            ycap = H + 0.4 - math.sqrt(rcap ** 2 - 4.0 ** 2)
            b.ball((0, ycap, 0), rcap, blanc, name="Coupole")
            _objet_geant(b, v, ycap + rcap - 0.3)
        # comptoir avant et tabourets
        with b.group("Comptoir"):
            b.box((-2.8, 0.6, -6.7), (2.8, 3.0, -5.5), blanc, name="Comptoir")
            b.box((-2.9, 1.4, -6.8), (2.9, 1.8, -6.6), c(S["bord"]), collide=False, name="Bande")
            b.box((-3.1, 3.0, -7.1), (3.1, 3.4, -5.4), c(S["bord"]), studs="top", name="Plateau")
            for x in (-2.0, 0.0, 2.0):
                b.cyl((x, 0.95, -7.35), 0.15, 1.9, c("gris_tech_fonce"), collide=False, name="Pied")
                b.cyl((x, 2.05, -7.35), 0.55, 0.3, c(S["store"][0]), studs="top", name="Assise")
        # tableau de menu sur pieds, en pictogrammes (carrés de couleur, aucun texte)
        with b.at((4.9, 0, -6.6), yaw=-30, group="Menu"):
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
    return {"emprise": (16, 16), "hauteur": _hauteur(b, i0)}


# ---------------------------------------------------------------------------
# 3) Habitation de la planète extraterrestre
# ---------------------------------------------------------------------------

def _dome_alien(b, x: float, z: float, r: float, hb: float, blanc, rng, *, hublots, porche=True, aiguilles=0,
                pile=True, cheminees=(), y_sol=0.5):
    """Dôme blanc sur tambour (hauteur hb), liseré lavande, hublots-bulles verts, porche rond, cheminées
    courtes, sommet (pile d'anneaux et feu) ou aiguilles. Renvoie la hauteur du sommet du dôme."""
    ctr = (x, hb, z)
    b.cyl((x, hb / 2, z), r, hb, blanc, name="Tambour")
    b.ball(ctr, r, blanc, name="Dome")
    b.cyl((x, hb + 0.2, z), r + 0.12, 0.4, c("coque_lavande"), collide=False, name="Liseré")
    for az, el, rw in hublots:
        _bulle(b, ctr, r, az, el, rw)
    if porche:
        rt = round(max(1.6, 0.36 * r), 2)
        yc = 0.9
        z_av = z - r - 1.3
        z_in = z - math.sqrt(max(r * r - rt * rt, 1.0)) + 0.5
        b.cyl((x, yc, (z_av + 0.3 + z_in) / 2), rt, z_in - z_av - 0.3, blanc, axis="z", name="Porche")
        b.cyl((x, yc, z_av + 0.35), rt + 0.25, 0.7, c("coque_lavande"), axis="z", name="Encadrement")
        b.cyl((x, yc, z_av), rt - 0.45, 0.3, _col(PORTE_ALIEN), axis="z", name="Porte")
        b.cyl((x, yc + 0.5 * (rt - 0.45), z_av - 0.15), 0.4, 0.2, c("vitre_verte"), axis="z", material="Glass",
              collide=False, shadow=False, name="Judas")
        b.box((x - rt + 0.3, y_sol - 0.3, z_av - 0.6), (x + rt - 0.3, y_sol + 0.1, z_av + 0.4), c("sable_clair"),
              studs="top", name="Marche")
    for az, el in cheminees:
        # cheminée courte : pied enfoncé dans le dôme, chapeau lavande
        p = np.array(ctr) + _dir(az, el) * r
        h = 1.6
        b.cyl((p[0], p[1] - 0.6 + h / 2, p[2]), 0.42, h, blanc, collide=False, name="Cheminee")
        b.cyl((p[0], p[1] + 1.0 + 0.12, p[2]), 0.55, 0.25, c("coque_lavande"), collide=False, shadow=False,
              name="Chapeau")
    top = hb + r
    if pile:
        # pile d'anneaux blancs, mât et feu vert d'eau
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


def _lampe_alien(b, x: float, z: float, h: float = 3.0):
    """Lampe de jardin extraterrestre : tige blanche, globe vert d'eau lumineux, chapeau lavande."""
    b.cyl((x, 0.15, z), 0.4, 0.3, c("sable_fonce"), name="Socle")
    b.cyl((x, 0.3 + (h - 0.3) / 2, z), 0.13, h - 0.3, c("blanc_dome"), collide=False, name="Tige")
    b.ball((x, h + 0.25, z), 0.45, c("neon_cyan"), material="Neon", collide=False, shadow=False, name="Globe")
    b.cyl((x, h + 0.72, z), 0.5, 0.18, c("coque_lavande"), collide=False, shadow=False, name="Chapeau")


def _arbuste_boule(b, x: float, z: float, rng, h: float = 3.2):
    """Arbuste à tronc fin et couronne ronde bleu-vert (rappel des arbres boules)."""
    b.cyl((x, h / 2, z), 0.18, h, c("tronc_alien"), collide=False, name="Tronc")
    b.ball((x, h + 0.6, z), 1.15, vary("boule_alien", rng, 0.05), collide=False, name="Couronne")
    b.ball((x + 0.55, h - 0.1, z - 0.3), 0.7, vary("boule_alien_claire", rng, 0.04), collide=False, shadow=False,
           name="Couronne")


def maison_alien(b, variant: int = 0, rayon: float = 7) -> dict:
    """Habitation extraterrestre (voir l'en-tête du module). Emprise (2r + 4) × (2r + 4), centrée."""
    rng = b.rng
    i0 = len(b.parts)
    v = variant % 4
    r = float(rayon)
    blanc = vary("blanc_dome", rng, 0.015)
    sable, sable_c, sable_f = c("sable"), c("sable_clair"), c("sable_fonce")
    hb = 1.2
    e = r + 2                                  # demi-emprise
    with b.group("DomeAlien"):
        if v == 1:
            # grappe : dôme principal (0,82 r) et petit dôme satellite (0,48 r)
            rm, rs = round(0.82 * r, 2), round(0.48 * r, 2)
            xm = -e + rm + 0.9
            xs = e - rs - 0.9
            b.cyl((xm, 0.25, 0), rm + 0.8, 0.5, sable, studs="top", name="Socle")
            b.cyl((xs, 0.2, 1.5), rs + 0.8, 0.4, sable_c, studs="top", name="Socle")
            _dome_alien(b, xm, 0, rm, hb, blanc, rng,
                        hublots=[(-50, 30, 1.1), (-110, 26, 0.9), (40, 34, 1.0), (170, 30, 1.0),
                                 (-20, 12, 0.8), (75, 14, 0.8)],
                        cheminees=[(-140, 52)])
            _dome_alien(b, xs, 1.5, rs, 0.9, blanc, rng, hublots=[(-20, 32, 0.8), (80, 30, 0.8)], porche=False,
                        pile=False, aiguilles=0)
            b.ball((xs, 0.9 + rs + 0.1, 1.5), 0.7, c("vitre_verte"), material="Glass", collide=False, name="Bulle")
            _lampe_alien(b, xs + 0.4, -(e - 1.2))
            _arbuste_boule(b, xm - 0.2, e - 1.4, rng, h=2.8)
        elif v == 2:
            # socle en gradins et deux aiguilles
            b.cyl((0, 0.25, 0), r + 1.8, 0.5, sable_f, studs="top", name="Gradin")
            b.cyl((0, 0.75, 0), r + 1.0, 0.5, sable, studs="top", name="Gradin")
            with b.at((0, 1.0, 0)):
                _dome_alien(b, 0, 0, r, hb, blanc, rng,
                            hublots=[(-45, 30, 1.2), (45, 30, 1.2), (-105, 26, 1.0), (105, 26, 1.0),
                                     (180, 30, 1.0), (-75, 12, 0.8), (75, 12, 0.8)],
                            aiguilles=2, pile=False, cheminees=[(160, 50)], y_sol=0.0)
            _lampe_alien(b, -(e - 0.7), -(e - 0.7), h=2.6)
            _arbuste_boule(b, e - 1.4, e - 1.4, rng)
        elif v == 3:
            # petit dôme à grande baie ronde
            b.cyl((0, 0.25, 0), r + 0.9, 0.5, sable, studs="top", name="Socle")
            _dome_alien(b, 0, 0, r, hb, blanc, rng, hublots=[(70, 28, 0.8), (140, 30, 0.8), (-120, 26, 0.8)],
                        cheminees=[(120, 50)])
            ctr = (0.0, hb, 0.0)
            rg = round(0.36 * r, 2)
            n = _dir(-42, 30)
            C = np.array(ctr)
            _disque(b, C + n * (r - 0.15), n, rg + 0.35, 0.6, c("coque_lavande"), collide=False, name="Cadre")
            _disque(b, C + n * (r + 0.2), n, rg, 0.3, c("vitre_verte"), material="Glass", reflectance=0.1,
                    collide=False, shadow=False, name="Baie")
            M = _repere(n)
            # meneaux en croix : la baie se lit comme une fenêtre
            for taille in ((0.2, 2 * rg, 0.2), (0.2, 0.2, 2 * rg)):
                b.part("block", taille, tuple(C + n * (r + 0.4)), M, c("coque_lavande"), collide=False, shadow=False,
                       name="Meneau")
            _disque(b, C + n * (r + 0.4) + M[:, 1] * (0.45 * rg) + M[:, 2] * (0.3 * rg), n, 0.2 * rg, 0.2, "blanc",
                    collide=False, shadow=False, name="Reflet")
            _lampe_alien(b, e - 1.0, -(e - 1.0), h=2.6)
            _arbuste_boule(b, -(e - 1.4), e - 1.4, rng, h=2.8)
        else:
            b.cyl((0, 0.25, 0), r + 0.9, 0.5, sable, studs="top", name="Socle")
            _dome_alien(b, 0, 0, r, hb, blanc, rng,
                        hublots=[(-48, 30, 1.1), (48, 30, 1.1), (-112, 26, 0.9), (112, 26, 0.9), (180, 32, 1.0),
                                 (-80, 11, 0.8), (80, 11, 0.8), (140, 12, 0.8)],
                        cheminees=[(-130, 50), (150, 54)])
            _lampe_alien(b, e - 1.0, -(e - 1.0))
            _arbuste_boule(b, -(e - 1.4), e - 1.4, rng)
        # buissons bleu-verts au pied
        for k, (x, z, rr) in enumerate(((-(r + 0.6), -(r * 0.55), 0.9), (r + 0.4, -(r * 0.35), 0.75))):
            if v == 1 and k == 1:
                continue
            b.ball((x, 0.4 + rr * 0.45, z), rr, vary("buisson_alien", rng, 0.05), collide=False, name="Buisson")
    return {"emprise": (2 * r + 4, 2 * r + 4), "hauteur": _hauteur(b, i0)}


# ---------------------------------------------------------------------------
# 4) Voiture volante garée
# ---------------------------------------------------------------------------

def voiture_volante(b, variant: int = 0) -> dict:
    """Voiture volante rétro-futuriste (longueur 9 le long de Z, avant vers -Z, largeur 5, hauteur ≤ 4) :
    caisse basse arrondie (bloc + demi-cylindres avant et arrière), capot et poupe en pente, liseré blanc,
    bulle de verre cerclée, ailerons et becquet, deux tuyères, quatre patins ronds posés au sol avec un halo
    lumineux (aucune roue), phares blancs et feux arrière."""
    i0 = len(b.parts)
    v = variant % 4
    corps = c(("bande_rouge", "bande_jaune", "bande_bleue", "bande_turquoise")[v])
    clair = shade(corps, 1.25)
    fonce = c("gris_tech_fonce")
    blanc = c("blanc_dome")
    with b.group("VoitureVolante"):
        # patins ronds et halos
        for x in (-1.45, 1.45):
            for z in (-2.3, 2.3):
                b.cyl((x, 0.25, z), 0.6, 0.5, fonce, name="Patin")
                b.cyl((x, 0.22, z), 0.7, 0.14, c("neon_cyan"), material="Neon", collide=False, shadow=False,
                      name="Halo")
        b.box((-1.9, 0.5, -2.6), (1.9, 0.85, 2.6), c("noir"), name="Dessous")
        # caisse : bloc + deux demi-cylindres verticaux (nez et poupe arrondis vus de dessus)
        b.box((-2.2, 0.85, -2.2), (2.2, 1.85, 2.2), corps, name="Caisse")
        for z in (-2.2, 2.2):
            b.cyl((0, 1.35, z), 2.2, 1.0, corps, name="Caisse")
        # liseré blanc tout autour
        b.box((-2.3, 1.2, -2.15), (2.3, 1.45, 2.15), blanc, collide=False, name="Liseré")
        for z in (-2.2, 2.2):
            b.cyl((0, 1.325, z), 2.3, 0.25, blanc, collide=False, name="Liseré")
        # capot et poupe en pente
        b.wedge((-1.8, 1.85, -3.4), (1.8, 2.2, -1.2), clair, down="-z", name="Capot")
        b.wedge((-1.8, 1.85, 1.3), (1.8, 2.45, 3.5), corps, down="+z", name="Poupe")
        # bulle de verre cerclée et siège
        b.box((-0.9, 1.85, -0.2), (0.9, 2.9, 0.9), shade(corps, 0.55), collide=False, name="Siege")
        b.cyl((0, 1.95, 0.1), 1.75, 0.25, blanc, collide=False, name="Cerclage")
        b.ball((0, 1.95, 0.1), 1.55, c("vitre"), material="Glass", transparency=0.3, collide=False, shadow=False,
               name="Bulle")
        # ailerons et becquet blanc
        for x in (-1.6, 1.6):
            b.wedge((x - 0.15, 2.0, 2.4), (x + 0.15, 3.5, 4.0), corps, down="-z", collide=False, name="Aileron")
        b.box((-1.85, 3.2, 3.4), (1.85, 3.45, 3.9), blanc, collide=False, name="Becquet")
        # tuyères arrière
        for x in (-0.9, 0.9):
            b.cyl((x, 1.3, 4.1), 0.42, 0.6, c("gris_tech"), axis="z", collide=False, name="Tuyere")
        # phares avant et feux arrière
        for s in (-1, 1):
            n = _dir(s * 28, 0)
            p = np.array([0, 1.62, -2.2]) + n * 2.2
            _disque(b, p, n, 0.24, 0.3, c("neon_blanc"), material="Neon", collide=False, shadow=False, name="Phare")
            n2 = _dir(180 + s * 50, 0)
            p2 = np.array([0, 1.62, 2.2]) + n2 * 2.2
            _disque(b, p2, n2, 0.24, 0.3, c("rouge"), material="Neon", collide=False, shadow=False, name="Feu")
    return {"emprise": (5, 9), "hauteur": _hauteur(b, i0)}
