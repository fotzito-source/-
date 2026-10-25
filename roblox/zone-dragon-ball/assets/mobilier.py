"""Mobilier de la zone Dragon Ball : petits objets du thème, chacun ≤ 40 pièces.

- rues du village terrestre : lampadaires ronds rétro-futuristes, bancs, parasols de terrasse,
  distributeurs automatiques, jardinières, antennes paraboliques, caisses ;
- arts martiaux : lanternes chinoises, poteaux-braseros de l'arène, bannières (武, 気, 修行…), gong,
  mannequins d'entraînement en bois, jarres d'eau, panneaux (道場, 武道…), guirlandes de fanions ;
- clôtures (blanche « tech », bois rustique, balustrade rouge de temple).

Repère : origine au centre de l'emprise au sol, avant vers -Z local. Les détails fins sont sans collision.
Propriété intellectuelle : aucune sphère orange (flammes en blocs, lanternes rouges cylindriques),
aucune étoile, aucun logo ; textes autorisés seulement (武, 道場, 修行, 武道, 気, 天).
"""

from __future__ import annotations

import math

import numpy as np

from kit import shade
from palette import c

TEXTES_AUTORISES = ("武", "道場", "修行", "武道", "気", "天")


def _texte(t: str) -> str:
    assert t in TEXTES_AUTORISES, f"texte non autorisé dans la zone : {t!r}"
    return t


def _repere(axe) -> np.ndarray:
    """Matrice de rotation dont la première colonne (axe d'un cylindre Roblox) est `axe`."""
    x = np.asarray(axe, float)
    x = x / np.linalg.norm(x)
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return np.column_stack([x, y, z])


def _segment(b, a, bb, rayon: float, col, name: str = "Cable") -> None:
    """Cylindre fin de a à bb (câble, cordon)."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    n = float(np.linalg.norm(bb - a))
    if n < 1e-3:
        return
    b.part("cyl", (n + rayon * 0.6, 2 * rayon, 2 * rayon), (a + bb) / 2, _repere(bb - a), col,
           collide=False, shadow=False, name=name)


def _chainette(p0, p1, creux: float, n: int):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    pts = []
    for i in range(n + 1):
        t = i / n
        p = p0 + (p1 - p0) * t
        p[1] -= creux * 4 * t * (1 - t)
        pts.append(p)
    return pts


# ---------------------------------------------------------------------------
# Rues du village terrestre
# ---------------------------------------------------------------------------

BANDES = ("bande_orange", "bande_bleue", "bande_rouge", "bande_jaune", "bande_turquoise", "bande_violette")


def lampadaire_rond(b, variant: int = 0) -> dict:
    """Lampadaire rétro-futuriste : mât blanc à bague colorée, tête en disque lumineux (blanc-cyan).

    variant 0 : une tête en potence vers l'avant ; 1 : deux têtes de part et d'autre ; 2 : anneau lumineux debout.
    Hauteur ≈ 11. Sur un trottoir à |x| ≥ 36, la potence (2,4 studs) reste hors du couloir."""
    bande = c(BANDES[variant % len(BANDES)])
    blanc, gris = c("blanc_dome"), c("gris_tech")
    with b.group("Lampadaire"):
        b.box((-0.9, 0, -0.9), (0.9, 0.6, 0.9), gris, studs="top", name="Socle")
        b.cyl((0, 0.6 + 0.5, 0), 0.6, 1.0, blanc, name="Pied")
        b.cyl((0, 1.6 + 4.4, 0), 0.28, 8.8, blanc, name="Mat")
        b.cyl((0, 5.2, 0), 0.36, 0.8, bande, collide=False, name="Bague")
        if variant % 3 == 2:
            b.cyl((0, 10.4 + 0.5, 0), 0.5, 1.0, blanc, collide=False, name="Col")
            b.part("cyl", (0.5, 3.0, 3.0), (0, 12.6, 0), _repere((0, 0, 1)), blanc, collide=False, name="Anneau")
            b.part("cyl", (0.62, 2.1, 2.1), (0, 12.6, 0), _repere((0, 0, 1)), c("neon_cyan"), material="Neon",
                   collide=False, shadow=False, name="Lumiere")
            b.cyl((0, 14.25, 0), 0.3, 0.5, bande, collide=False, name="Pointe")
            return {"emprise": (3, 1.8), "hauteur": 14.6}
        bras = [(0, -1)] if variant % 3 == 0 else [(-1, 0), (1, 0)]
        b.cyl((0, 10.6, 0), 0.4, 0.4, bande, collide=False, name="Chapeau")
        for dx, dz in bras:
            x1, z1 = dx * 2.4, dz * 2.4
            b.box((min(0, x1) - 0.18, 10.2, min(0, z1) - 0.18), (max(0, x1) + 0.18, 10.5, max(0, z1) + 0.18), blanc,
                  collide=False, name="Potence")
            b.cyl((x1, 9.95, z1), 1.25, 0.5, blanc, collide=False, name="Tete")
            b.cyl((x1, 9.6, z1), 1.0, 0.2, c("neon_blanc"), material="Neon", collide=False, shadow=False, name="Lumiere")
            b.cyl((x1, 10.3, z1), 0.6, 0.2, bande, collide=False, name="Capot")
    return {"emprise": (5.4 if variant % 3 == 1 else 2.5, 3.7 if variant % 3 == 0 else 2.5), "hauteur": 10.6}


def banc(b, variant: int = 0) -> dict:
    """Banc : 0 banc blanc arrondi (village), 1 banc de bois sur pieds de pierre, 2 banc de pierre (temple)."""
    v = variant % 3
    with b.group("Banc"):
        if v == 0:
            bande = c(BANDES[(variant // 3) % len(BANDES)])
            for x in (-2.4, 2.4):
                b.box((x - 0.4, 0, -0.7), (x + 0.4, 1.4, 0.7), c("gris_tech"), name="Pied")
            b.box((-3.0, 1.4, -1.0), (3.0, 1.9, 1.0), c("blanc_dome"), studs="top", name="Assise")
            b.cyl((-3.0, 1.63, 0), 1.0, 0.46, c("blanc_dome"), axis="y", collide=False, name="Bout")
            b.cyl((3.0, 1.63, 0), 1.0, 0.46, c("blanc_dome"), axis="y", collide=False, name="Bout")
            b.box((-3.0, 1.9, 0.6), (3.0, 3.6, 1.0), c("blanc_dome"), name="Dossier")
            b.box((-3.0, 2.6, 0.5), (3.0, 3.0, 0.6), bande, collide=False, name="Bande")
            return {"emprise": (8, 2), "hauteur": 3.6}
        if v == 1:
            for x in (-2.4, 2.4):
                b.box((x - 0.5, 0, -0.6), (x + 0.5, 1.3, 0.6), c("pierre_fonce"), name="Pied")
            b.box((-3.2, 1.3, -0.9), (3.2, 1.7, 0.9), c("bois"), studs="top", name="Assise")
            b.box((-3.2, 1.25, -0.95), (3.2, 1.35, -0.85), c("bois_fonce"), collide=False, name="Liseré")
            return {"emprise": (6.4, 1.8), "hauteur": 1.7}
        b.box((-3.0, 0, -0.7), (-1.8, 1.4, 0.7), c("pierre_fonce"), name="Pied")
        b.box((1.8, 0, -0.7), (3.0, 1.4, 0.7), c("pierre_fonce"), name="Pied")
        b.box((-3.4, 1.4, -1.0), (3.4, 2.0, 1.0), c("pierre"), studs="top", name="Assise")
    return {"emprise": (6.8, 2), "hauteur": 2.0}


def parasol_table(b, variant: int = 0) -> dict:
    """Table ronde de terrasse, deux tabourets et un parasol rayé (disques de couleurs alternées)."""
    a = c(BANDES[variant % len(BANDES)])
    bl = c("blanc_dome")
    with b.group("Terrasse"):
        b.cyl((0, 0.15, 0), 1.0, 0.3, c("gris_tech"), name="Pied")
        b.cyl((0, 1.4, 0), 0.25, 2.2, c("gris_tech"), name="Fut")
        b.cyl((0, 2.65, 0), 1.6, 0.3, bl, studs="top", name="Plateau")
        for x in (-2.6, 2.6):
            b.cyl((x, 0.75, 0), 0.7, 1.5, a, studs="top", name="Tabouret")
        b.cyl((0, 5.0, 0), 0.14, 4.4, c("metal"), collide=False, name="Manche")
        b.cyl((0, 7.1, 0), 4.0, 0.3, a, collide=False, name="Toile")
        b.cyl((0, 7.4, 0), 3.0, 0.3, bl, collide=False, name="Toile")
        b.cyl((0, 7.7, 0), 1.9, 0.3, a, collide=False, name="Toile")
        b.cyl((0, 8.0, 0), 0.8, 0.3, bl, collide=False, name="Toile")
        b.cyl((0, 8.3, 0), 0.25, 0.4, a, collide=False, name="Pointe")
    return {"emprise": (8, 8), "hauteur": 8.5}


def distributeur(b, variant: int = 0) -> dict:
    """Distributeur automatique de boissons : caisse colorée, vitrine éclairée, rangées de bouteilles."""
    corps = c(("bande_rouge", "bande_bleue", "blanc_dome")[variant % 3])
    with b.group("Distributeur"):
        b.box((-1.6, 0, -1.0), (1.6, 0.4, 1.0), c("gris_tech_fonce"), name="Socle")
        b.box((-1.5, 0.4, -0.9), (1.5, 6.2, 1.0), corps, name="Caisse")
        b.box((-1.6, 6.2, -1.05), (1.6, 6.6, 1.05), shade(corps, 0.85), studs="top", name="Chapeau")
        b.box((-1.2, 3.0, -1.0), (0.6, 5.8, -0.9), c("vitre_lumiere"), material="Neon", collide=False, shadow=False, name="Vitrine")
        for i, col in enumerate(("bande_jaune", "bande_turquoise", "bande_orange")):
            y = 3.3 + i * 0.85
            b.box((-1.05, y, -1.12), (0.45, y + 0.5, -0.98), c(col), collide=False, shadow=False, name="Bouteilles")
        b.box((0.8, 4.2, -1.05), (1.25, 5.6, -0.9), c("noir"), collide=False, name="Monnayeur")
        b.box((-1.0, 0.9, -1.05), (1.0, 1.8, -0.9), c("noir"), collide=False, name="Trappe")
    return {"emprise": (3.2, 2.1), "hauteur": 6.6}


def jardiniere(b, variant: int = 0) -> dict:
    """Jardinière ronde blanche à bague colorée, buisson arrondi semé de petites fleurs (roses, jaunes ou blanches)."""
    bande = c(BANDES[(variant + 2) % len(BANDES)])
    fleur = c(("fleur_rose", "fleur_jaune", "blanc")[variant % 3])
    rng = np.random.default_rng(300 + variant)
    with b.group("Jardiniere"):
        b.cyl((0, 0.9, 0), 2.0, 1.8, c("blanc_dome"), name="Bac")
        b.cyl((0, 1.5, 0), 2.08, 0.4, bande, collide=False, name="Bague")
        b.cyl((0, 1.85, 0), 1.8, 0.1, c("terre_fonce"), collide=False, name="Terre")
        b.cyl((0, 2.5, 0), 1.65, 1.3, c("buisson"), collide=False, name="Buisson")
        b.ball((0.2, 3.1, -0.1), 1.35, c("feuillage"), collide=False, name="Buisson")
        for k in range(7):
            a = k * 51.4 + float(rng.uniform(-12, 12))
            r = 1.45 if k % 2 else 1.0
            y = 2.7 + (k % 3) * 0.45 if k % 2 else 3.95
            x, z = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
            b.box((x - 0.22, y, z - 0.22), (x + 0.22, y + 0.44, z + 0.22), fleur, collide=False, shadow=False, name="Fleur")
    return {"emprise": (4, 4), "hauteur": 4.4}


def antenne_parabole(b, variant: int = 0) -> dict:
    """Antenne parabolique sur un petit mât (toits et jardins du village)."""
    incl = (40, 55, 30)[variant % 3]
    a = math.radians(incl)
    axe = np.array([0.0, math.sin(a), -math.cos(a)])     # la parabole regarde l'avant et le ciel
    with b.group("Antenne"):
        b.box((-1.0, 0, -1.0), (1.0, 0.5, 1.0), c("gris_tech"), studs="top", name="Socle")
        b.cyl((0, 0.5 + 1.6, 0), 0.25, 3.2, c("gris_tech_fonce"), name="Mat")
        centre = np.array([0, 4.0, 0]) + axe * 0.4
        b.part("cyl", (0.35, 4.4, 4.4), centre, _repere(axe), c("blanc_dome"), collide=False, name="Parabole")
        b.part("cyl", (0.4, 1.6, 1.6), centre + axe * 0.05, _repere(axe), c("blanc_ombre"), collide=False, name="Creux")
        _segment(b, centre, centre + axe * 2.0, 0.1, c("gris_tech_fonce"), name="Bras")
        b.box(tuple(centre + axe * 2.0 - 0.25), tuple(centre + axe * 2.0 + 0.25), c(BANDES[variant % len(BANDES)]),
              collide=False, name="Tete")
        b.box((-0.4, 3.5, -0.4), (0.4, 3.9, 0.4), c("gris_tech_fonce"), collide=False, name="Rotule")
    return {"emprise": (4.4, 4.4), "hauteur": 6.0}


def caisses(b, variant: int = 0) -> dict:
    """0 caisses de bois, 1 caisses blanches « tech » à bandes, 2 tonneaux."""
    rng = b.rng
    v = variant % 3
    with b.group("Caisses"):
        if v == 2:
            for x, z in ((-1.1, 0), (1.1, 0.3), (0, 1.9)):
                b.cyl((x, 1.4, z), 1.0, 2.8, c("bois"), name="Tonneau")
                for y in (0.6, 2.2):
                    b.cyl((x, y, z), 1.06, 0.25, c("bois_fonce"), collide=False, name="Cercle")
                b.cyl((x, 2.85, z), 0.85, 0.1, c("bois_clair"), collide=False, name="Couvercle")
            return {"emprise": (4.2, 4), "hauteur": 2.9}
        pile = [((-1.2, 0, 0), 2.2), ((1.3, 0, 0.3), 2.0), ((-0.2, 2.2, 0.1), 1.8)]
        for (x, y, z), s in pile:
            yaw = float(rng.uniform(-10, 10))
            if v == 0:
                b.boxc((x, y + s / 2, z), (s, s, s), c("bois_clair"), yaw=yaw, studs="top", name="Caisse")
                b.boxc((x, y + s / 2, z), (s + 0.12, s * 0.22, s + 0.12), c("bois"), yaw=yaw, collide=False, name="Cerclage")
            else:
                b.boxc((x, y + s / 2, z), (s, s, s), c("blanc_dome"), yaw=yaw, studs="top", name="Caisse")
                b.boxc((x, y + s * 0.62, z), (s + 0.12, s * 0.18, s + 0.12), c(BANDES[int(rng.integers(len(BANDES)))]),
                       yaw=yaw, collide=False, name="Bande")
    return {"emprise": (5, 3), "hauteur": 4.0}


# ---------------------------------------------------------------------------
# Arts martiaux
# ---------------------------------------------------------------------------

def lanterne_chinoise(b, variant: int = 0) -> dict:
    """Lanterne rouge (cylindre ventru à chapeaux dorés et gland) pendue à une potence de bois laqué.

    variant 0 : une lanterne rouge ; 1 : deux lanternes (potence en T) ; 2 : lanterne jaune."""
    corps = c("banniere_jaune" if variant % 3 == 2 else "laque_rouge")
    bois = c("laque_rouge_fonce") if variant % 3 != 1 else c("bois_fonce")
    with b.group("Lanterne"):
        b.box((-0.9, 0, -0.9), (0.9, 0.7, 0.9), c("pierre_fonce"), studs="top", name="Socle")
        b.box((-0.35, 0.7, -0.35), (0.35, 8.0, 0.35), bois, name="Poteau")
        b.box((-0.45, 8.0, -0.45), (0.45, 8.4, 0.45), c("or"), collide=False, name="Chapeau")
        bras = [-1] if variant % 3 != 1 else [-1, 1]
        for s in bras:
            z1 = s * 2.2
            b.box((-0.2, 7.3, min(0, z1) - 0.2), (0.2, 7.7, max(0, z1) + 0.2), bois, collide=False, name="Potence")
            b.box((-0.05, 6.5, z1 - 0.05), (0.05, 7.3, z1 + 0.05), c("noir"), collide=False, name="Attache")
            b.cyl((0, 6.35, z1), 0.55, 0.3, c("or"), collide=False, name="Chapeau")
            b.cyl((0, 5.3, z1), 0.85, 1.8, corps, collide=False, shadow=False, name="Lanterne")
            b.cyl((0, 5.3, z1), 1.0, 1.0, corps, collide=False, shadow=False, name="Ventre")
            b.cyl((0, 4.25, z1), 0.55, 0.3, c("or"), collide=False, name="Chapeau")
            b.box((-0.12, 3.2, z1 - 0.12), (0.12, 4.1, z1 + 0.12), c("or_fonce"), collide=False, shadow=False, name="Gland")
    return {"emprise": (2, 2.6 if variant % 3 != 1 else 5.2), "hauteur": 8.4}


def poteau_arene(b, variant: int = 0, hauteur: float = 6.0, socle: float = 0.0) -> dict:
    """Poteau d'angle de l'arène : pilier de pierre carré (fût de 2,8), bagues rouges, chapiteau, bassin de
    bronze et flamme en blocs (Neon). `socle` : piédestal de pierre sous le poteau (le poteau commence à y = socle).

    variant 0 : flamme ; 1 : lanterne carrée blanche ; 2 : flamme et écharpe rouge."""
    h = hauteur + socle
    p, pf, pc = c("pierre"), c("pierre_fonce"), c("pierre_claire")
    with b.group("PoteauArene"):
        if socle > 0:
            b.box((-1.7, 0, -1.7), (1.7, socle, 1.7), pf, studs="top", name="Piedestal")
        b.box((-1.6, socle, -1.6), (1.6, socle + 0.8, 1.6), pf, studs="top", name="Socle")
        b.box((-1.4, socle + 0.8, -1.4), (1.4, h - 0.6, 1.4), p, name="Fut")
        b.box((-1.5, h - 2.0, -1.5), (1.5, h - 1.6, 1.5), c("laque_rouge"), collide=False, name="Bague")
        b.box((-1.5, socle + 2.0, -1.5), (1.5, socle + 2.4, 1.5), c("laque_rouge"), collide=False, name="Bague")
        b.box((-1.65, h - 0.6, -1.65), (1.65, h, 1.65), pc, studs="top", name="Chapiteau")
        if variant % 3 == 1:
            b.box((-0.9, h, -0.9), (0.9, h + 1.8, 0.9), c("neon_blanc"), material="Neon", collide=False, shadow=False, name="Lumiere")
            for sx in (-0.95, 0.95):
                for sz in (-0.95, 0.95):
                    b.box((sx - 0.12, h, sz - 0.12), (sx + 0.12, h + 1.8, sz + 0.12), c("laque_rouge_fonce"), collide=False, name="Montant")
            b.box((-1.3, h + 1.8, -1.3), (1.3, h + 2.3, 1.3), c("tuile_orange"), studs="top", collide=False, name="Toit")
            b.box((-0.4, h + 2.3, -0.4), (0.4, h + 2.8, 0.4), c("or"), collide=False, name="Bouton")
            return {"emprise": (3.2, 3.2), "hauteur": h + 2.8}
        b.cyl((0, h + 0.5, 0), 1.35, 1.0, c("bronze"), name="Bassin")
        b.cyl((0, h + 1.05, 0), 1.45, 0.2, shade(c("bronze"), 0.8), collide=False, name="Rebord")
        fl, fc = c("flamme"), c("flamme_coeur")
        b.boxc((0, h + 1.8, 0), (1.9, 1.4, 1.9), fl, yaw=0, material="Neon", collide=False, shadow=False, name="Flamme")
        b.boxc((0.15, h + 2.8, -0.1), (1.2, 1.2, 1.2), fl, yaw=20, material="Neon", collide=False, shadow=False, name="Flamme")
        b.boxc((-0.1, h + 3.6, 0.1), (0.6, 0.9, 0.6), fl, yaw=40, material="Neon", collide=False, shadow=False, name="Flamme")
        b.boxc((0, h + 2.0, 0), (1.0, 1.5, 2.0), fc, yaw=45, material="Neon", collide=False, shadow=False, name="Coeur")
        if variant % 3 == 2:
            b.box((-1.5, h - 3.2, -1.5), (1.5, h - 2.6, 1.5), c("banniere_rouge"), collide=False, name="Echarpe")
            b.box((-0.5, h - 4.6, -1.6), (0.3, h - 2.6, -1.5), c("banniere_rouge"), collide=False, shadow=False, name="Pan")
    return {"emprise": (3.2, 3.2), "hauteur": h + 4.0}


COULEURS_BANNIERE = [("banniere_rouge", "or"), ("banniere_jaune", "laque_rouge"),
                     ("banniere_blanche", "laque_rouge"), ("banniere_bleue", "blanc")]


def banniere(b, texte: str = "武", variant: int = 0, hauteur: float = 10.0) -> dict:
    """Bannière verticale sur mât (texte lisible des deux côtés), pointe de lance dorée en coins."""
    fond, encre = (c(n) for n in COULEURS_BANNIERE[variant % len(COULEURS_BANNIERE)])
    h = hauteur
    n = len(_texte(texte))
    haut_tissu = min(h - 2.5, 2.0 + 2.2 * n)
    with b.group("Banniere"):
        b.box((-0.8, 0, -0.8), (0.8, 0.8, 0.8), c("pierre_fonce"), studs="top", name="Socle")
        b.cyl((0, 0.8 + (h - 0.8) / 2, 0), 0.2, h - 0.8, c("laque_rouge_fonce"), name="Mat")
        b.box((-1.5, h - 0.7, -0.45), (1.5, h - 0.4, 0.45), c("laque_rouge_fonce"), collide=False, name="Traverse")
        b.wedge((-0.25, h, -0.12), (0.25, h + 1.2, 0), c("or"), down="-z", collide=False, name="Pointe")
        b.wedge((-0.25, h, 0), (0.25, h + 1.2, 0.12), c("or"), down="+z", collide=False, name="Pointe")
        y1 = h - 0.7
        y0 = y1 - haut_tissu
        for z0, z1, face in ((-0.42, -0.22, "Front"), (0.22, 0.42, "Back")):
            t = b.box((-1.3, y0, z0), (1.3, y1, z1), fond, collide=False, shadow=False, name="Tissu")
            t.label = {"face": face, "text": texte, "color": encre, "font": "brush", "vertical": True}
        b.box((-1.3, y0 - 0.5, -0.42), (1.3, y0, 0.42), encre, collide=False, shadow=False, name="Frange")
    return {"emprise": (3, 1.6), "hauteur": h + 1.2}


def panneau(b, texte: str = "道場", variant: int = 0) -> dict:
    """Panneau : 0 planche de bois à petit toit de tuiles, 1 panneau blanc « tech » arrondi, 2 stèle de pierre."""
    v = variant % 3
    n = len(_texte(texte))
    w = 1.6 + 2.0 * n
    with b.group("Panneau"):
        if v == 0:
            for x in (-w / 2 + 0.3, w / 2 - 0.3):
                b.box((x - 0.25, 0, -0.25), (x + 0.25, 5.3, 0.25), c("bois_fonce"), name="Pied")
            p = b.box((-w / 2, 2.6, -0.2), (w / 2, 4.8, 0.2), c("bois_clair"), name="Planche")
            p.label = {"face": "Front", "text": texte, "color": c("encre"), "font": "brush"}
            b.wedge((-w / 2 - 0.6, 5.4, -0.9), (w / 2 + 0.6, 6.4, 0), c("tuile_orange"), down="-z", studs="top", collide=False, name="Toit")
            b.wedge((-w / 2 - 0.6, 5.4, 0), (w / 2 + 0.6, 6.4, 0.9), c("tuile_orange"), down="+z", studs="top", collide=False, name="Toit")
            b.box((-w / 2 - 0.3, 5.0, -0.35), (w / 2 + 0.3, 5.4, 0.35), c("laque_rouge"), collide=False, name="Linteau")
            return {"emprise": (w + 1.2, 1.8), "hauteur": 6.4}
        if v == 1:
            bande = c(BANDES[n % len(BANDES)])
            b.box((-0.7, 0, -0.7), (0.7, 0.5, 0.7), c("gris_tech"), studs="top", name="Socle")
            b.cyl((0, 0.5 + 1.6, 0), 0.25, 3.2, c("blanc_dome"), name="Mat")
            p = b.box((-w / 2, 3.7, -0.3), (w / 2, 6.1, 0.3), c("blanc_dome"), name="Panneau")
            p.label = {"face": "Front", "text": texte, "color": bande, "font": "sans"}
            for x in (-w / 2, w / 2):
                b.cyl((x, 4.9, 0), 1.2, 0.56, c("blanc_dome"), axis="z", collide=False, name="Bout")
            b.box((-w / 2, 3.5, -0.32), (w / 2, 3.7, 0.32), bande, collide=False, name="Liseré")
            return {"emprise": (w + 2.4, 1.4), "hauteur": 6.1}
        b.box((-w / 2 - 0.6, 0, -1.0), (w / 2 + 0.6, 0.8, 1.0), c("pierre_fonce"), studs="top", name="Socle")
        p = b.box((-w / 2, 0.8, -0.5), (w / 2, 4.2 + 0.6 * n, 0.5), c("pierre"), name="Stele")
        p.label = {"face": "Front", "text": texte, "color": c("laque_rouge_fonce"), "font": "brush"}
        b.box((-w / 2 - 0.2, 4.2 + 0.6 * n, -0.6), (w / 2 + 0.2, 4.7 + 0.6 * n, 0.6), c("pierre_claire"), studs="top", name="Chapeau")
    return {"emprise": (w + 1.2, 2), "hauteur": 4.7 + 0.6 * n}


def gong(b, variant: int = 0) -> dict:
    """Gong de bronze suspendu à un portique de bois laqué aux extrémités relevées."""
    bois = c("laque_rouge") if variant % 2 == 0 else c("bois_fonce")
    with b.group("Gong"):
        b.box((-3.4, 0, -1.2), (3.4, 0.6, 1.2), c("pierre_fonce"), studs="top", name="Socle")
        for x in (-2.8, 2.8):
            b.box((x - 0.35, 0.6, -0.35), (x + 0.35, 7.0, 0.35), bois, name="Montant")
            b.box((x - 0.5, 0.6, -0.9), (x + 0.5, 1.2, 0.9), bois, name="Pied")
        b.box((-3.4, 7.0, -0.4), (3.4, 7.6, 0.4), bois, name="Traverse")
        b.wedge((-4.3, 7.0, -0.4), (-3.4, 8.0, 0.4), bois, down="+x", collide=False, name="Corne")
        b.wedge((3.4, 7.0, -0.4), (4.3, 8.0, 0.4), bois, down="-x", collide=False, name="Corne")
        for x in (-0.9, 0.9):
            b.box((x - 0.06, 6.1, -0.06), (x + 0.06, 7.0, 0.06), c("noir"), collide=False, name="Cordon")
        b.cyl((0, 3.9, 0), 2.3, 0.3, c("bronze"), axis="z", collide=False, name="Disque")
        b.cyl((0, 3.9, -0.15), 1.4, 0.2, shade(c("bronze"), 1.15), axis="z", collide=False, name="Anneau")
        b.cyl((0, 3.9, -0.25), 0.6, 0.2, c("or"), axis="z", collide=False, name="Bosse")
        b.cyl((2.4, 1.6, -0.8), 0.12, 2.0, c("bois_clair"), axis="y", collide=False, name="Manche")
        b.box((2.1, 2.6, -1.1), (2.7, 3.2, -0.5), c("banniere_blanche"), collide=False, name="Maillet")
    return {"emprise": (8.6, 2.4), "hauteur": 8.0}


def mannequin_bois(b, variant: int = 0) -> dict:
    """Mannequin d'entraînement en bois : fût sur socle, trois bras et une jambe coudée (vers l'avant -Z)."""
    with b.group("Mannequin"):
        b.box((-1.2, 0, -1.2), (1.2, 0.5, 1.2), c("bois_fonce"), studs="top", name="Socle")
        b.cyl((0, 0.5 + 2.9, 0), 0.6, 5.8, c("bois" if variant % 2 == 0 else "bois_clair"), name="Fut")
        b.cyl((0, 6.45, 0), 0.62, 0.3, c("bois_fonce"), collide=False, name="Chapeau")
        for y, dx in ((5.0, -0.45), (5.0, 0.45), (4.0, 0.0)):
            b.box((dx - 0.14, y - 0.14, -2.0), (dx + 0.14, y + 0.14, -0.5), c("bois_clair"), collide=False, name="Bras")
        b.box((-0.18, 2.0, -1.6), (0.18, 2.4, -0.5), c("bois_clair"), collide=False, name="Jambe")
        b.box((-0.18, 0.9, -1.6), (0.18, 2.0, -1.25), c("bois_clair"), collide=False, name="Jambe")
    return {"emprise": (2.4, 2.4), "hauteur": 6.6}


def jarres(b, variant: int = 0) -> dict:
    """Jarres de terre cuite (eau d'entraînement) : deux à quatre jarres ventrues, certaines pleines d'eau."""
    pos = [(-1.4, 0.0, 1.0), (1.3, 0.3, 1.1), (0.0, 1.9, 0.85), (2.6, 2.2, 0.75)][: 2 + variant % 3]
    with b.group("Jarres"):
        for i, (x, z, s) in enumerate(pos):
            h = 2.6 * s
            b.cyl((x, h * 0.25, z), 0.9 * s, h * 0.5, c("pave_fonce"), name="Pied")
            b.cyl((x, h * 0.55, z), 1.25 * s, h * 0.5, c("pave"), name="Ventre")
            b.cyl((x, h * 0.9, z), 0.8 * s, h * 0.2, c("pave_fonce"), collide=False, name="Col")
            b.cyl((x, h + 0.05, z), 0.95 * s, 0.1 * s + 0.1, c("pave_clair"), collide=False, name="Levre")
            if i % 2 == 0:
                b.cyl((x, h + 0.08, z), 0.7 * s, 0.1 * s + 0.1, c("eau"), collide=False, shadow=False, name="Eau")
    return {"emprise": (5.5, 4.5), "hauteur": 2.8}


COULEURS_FANIONS = ("banniere_rouge", "banniere_jaune", "banniere_bleue", "banniere_blanche", "rose_ciel")


def guirlande_fanions(b, p0, p1, n: int = 10, creux: float = 1.5, variant: int = 0) -> dict:
    """Cordon tendu entre deux points avec des fanions triangulaires de couleurs (deux coins par fanion).

    p0, p1 en coordonnées du repère courant. Au-dessus du couloir, les deux points doivent être à y ≥ 33 + creux."""
    pts = _chainette(p0, p1, creux, 6)
    p0a, p1a = np.asarray(p0, float), np.asarray(p1, float)
    d = p1a - p0a
    yaw = math.degrees(math.atan2(-d[2], d[0]))
    cols = COULEURS_FANIONS[variant % 2:] + COULEURS_FANIONS[: variant % 2]
    with b.group("Fanions"):
        for a, bb in zip(pts, pts[1:]):
            _segment(b, a, bb, 0.08, c("blanc"), name="Cordon")
        for i in range(n):
            t = (i + 0.5) / n
            p = p0a + d * t
            y = p[1] - creux * 4 * t * (1 - t) - 0.05
            col = c(cols[i % len(cols)])
            with b.at((p[0], 0, p[2]), yaw=yaw):
                b.wedge_under((-0.7, y - 1.6, -0.05), (0, y, 0.05), col, down="-x", collide=False, shadow=False, name="Fanion")
                b.wedge_under((0, y - 1.6, -0.05), (0.7, y, 0.05), col, down="+x", collide=False, shadow=False, name="Fanion")
    return {"fanions": n}


# ---------------------------------------------------------------------------
# Clôtures
# ---------------------------------------------------------------------------

def cloture(b, longueur: float = 12, variant: int = 0) -> dict:
    """Clôture le long de X : 0 barrière blanche « tech » à capuchons colorés, 1 bois rustique,
    2 balustrade rouge de temple sur muret de pierre."""
    v = variant % 3
    n = max(2, int(longueur // 3) + 1)
    L = longueur
    with b.group("Cloture"):
        if v == 0:
            cap = c(BANDES[(variant // 3) % len(BANDES)])
            for i in range(n):
                x = -L / 2 + i * L / (n - 1)
                b.box((x - 0.3, 0, -0.3), (x + 0.3, 3.0, 0.3), c("blanc_dome"), name="Poteau")
                b.cyl((x, 3.15, 0), 0.38, 0.3, cap, collide=False, name="Capuchon")
            for y in (1.0, 2.3):
                b.box((-L / 2, y, -0.15), (L / 2, y + 0.4, 0.15), c("blanc_ombre"), name="Lisse")
            return {"emprise": (L, 0.8), "hauteur": 3.3}
        if v == 1:
            for i in range(n):
                x = -L / 2 + i * L / (n - 1)
                b.box((x - 0.3, 0, -0.3), (x + 0.3, 3.2, 0.3), c("bois_fonce"), name="Poteau")
            for y in (1.0, 2.2):
                b.box((-L / 2, y, -0.4), (L / 2, y + 0.5, -0.3), c("bois"), name="Planche")
            return {"emprise": (L, 0.8), "hauteur": 3.2}
        b.box((-L / 2, 0, -0.6), (L / 2, 1.0, 0.6), c("pierre_fonce"), studs="top", name="Muret")
        for i in range(n):
            x = -L / 2 + i * L / (n - 1)
            b.box((x - 0.3, 1.0, -0.3), (x + 0.3, 3.4, 0.3), c("laque_rouge"), name="Poteau")
            b.box((x - 0.4, 3.4, -0.4), (x + 0.4, 3.8, 0.4), c("or"), collide=False, name="Pommeau")
        b.box((-L / 2, 2.6, -0.2), (L / 2, 3.0, 0.2), c("laque_rouge"), name="Lisse")
        b.box((-L / 2, 1.6, -0.15), (L / 2, 1.9, 0.15), c("laque_rouge_fonce"), collide=False, name="Lisse")
    return {"emprise": (L, 1.2), "hauteur": 3.8}
