"""Mobilier de la ville médiévale : réverbères et lanternes murales, enseignes de boutique, panneaux, clôtures,
caisses, tonneaux, sacs, charrettes, bancs, étals de marché, puits, abreuvoirs, piles de boulets, bottes de foin,
tas de bois, bacs à fleurs, drapeaux et guirlandes de fanions.

Chaque objet tient en 40 pièces au plus. Les petits détails sont décoratifs : pas de collision, pas d'ombre
pour les éléments fins. Origine : centre de l'emprise au sol, avant vers -Z local (sauf mention contraire).
Enseignes et lanternes murales : origine sur la face du mur, à la hauteur de la fixation ; elles dépassent vers -Z.
"""

from __future__ import annotations

import math

import numpy as np

from kit import rot_z, shade
from palette import c, vary

# Textes d'enseigne permis (mots génériques de boutiques, pas d'alcool)
TEXTES_ENSEIGNES = ("PAIN", "BOULANGERIE", "AUBERGE", "MARCHÉ", "FROMAGES", "FORGE", "TISSUS", "HORLOGER",
                    "FLEURS", "LÉGUMES", "SAVON", "BÄCKEREI", "GASTHAUS", "MARKT", "BROT", "LIBRAIRIE")


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

def _segment(b, a, bb, rayon: float, col, name: str = "Corde") -> None:
    """Cylindre fin de a à bb (l'axe d'un cylindre Roblox est son X local)."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    d = bb - a
    n = float(np.linalg.norm(d))
    if n < 1e-3:
        return
    x = d / n
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    b.part("cyl", (n + rayon * 0.6, 2 * rayon, 2 * rayon), (a + bb) / 2, np.column_stack([x, y, z]), col,
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


def _lanterne(b, x, y, z, fer, taille: float = 1.0, name: str = "Lanterne") -> None:
    """Lanterne carrée vitrée (verre Neon, montants de fer, chapeau pyramidal) posée en (x, y, z) (bas)."""
    s = taille
    b.box((x - 0.7 * s, y, z - 0.7 * s), (x + 0.7 * s, y + 0.25 * s, z + 0.7 * s), fer, collide=False, name=name)
    b.box((x - 0.55 * s, y + 0.25 * s, z - 0.55 * s), (x + 0.55 * s, y + 1.75 * s, z + 0.55 * s), c("lampe"),
          material="Neon", collide=False, shadow=False, name=name)
    for sx in (-1, 1):
        b.box((x + sx * 0.62 * s - 0.1 * s, y + 0.25 * s, z - 0.68 * s), (x + sx * 0.62 * s + 0.1 * s, y + 1.75 * s, z + 0.68 * s),
              fer, collide=False, shadow=False, name=name)
    b.wedge((x - 0.85 * s, y + 1.75 * s, z - 0.85 * s), (x + 0.85 * s, y + 2.35 * s, z), fer, down="-z", collide=False, name=name)
    b.wedge((x - 0.85 * s, y + 1.75 * s, z), (x + 0.85 * s, y + 2.35 * s, z + 0.85 * s), fer, down="+z", collide=False, name=name)
    b.box((x - 0.15 * s, y + 2.35 * s, z - 0.15 * s), (x + 0.15 * s, y + 2.75 * s, z + 0.15 * s), fer, collide=False, name=name)


def _label(part, face: str, texte: str, couleur, fond=None, font: str = "serif") -> None:
    part.label = {"face": face, "text": texte, "color": tuple(couleur), "bg": tuple(fond) if fond else None, "font": font}


# ---------------------------------------------------------------------------
# Éclairage
# ---------------------------------------------------------------------------

def reverbere(b, variant: int = 0) -> dict:
    """Réverbère de fonte : socle de pierre, fût, lanterne vitrée.
    variant 0 : lanterne au sommet ; 1 : crosse vers l'avant (-Z) et lanterne suspendue ; 2 : deux bras (±X)."""
    fer = c("fonte")
    v = variant % 3
    with b.group("Reverbere"):
        b.box((-0.9, 0, -0.9), (0.9, 0.8, 0.9), c("pave_fonce"), studs="top", name="Socle")
        b.cyl((0, 1.6, 0), 0.55, 1.6, fer, name="Pied")
        b.cyl((0, 6.2, 0), 0.25, 8.0, fer, name="Fut")
        b.box((-0.5, 2.4, -0.5), (0.5, 2.7, 0.5), fer, collide=False, name="Bague")
        if v == 0:
            b.box((-0.45, 10.2, -0.45), (0.45, 10.5, 0.45), fer, collide=False, name="Plateau")
            _lanterne(b, 0, 10.5, 0, fer, 1.0)
            h = 13.3
        elif v == 1:
            b.box((-0.15, 9.6, -2.6), (0.15, 9.9, 0.1), fer, collide=False, name="Crosse")
            b.box((-0.12, 9.9, 0.0), (0.12, 10.5, 0.25), fer, collide=False, name="Volute")
            b.box((-0.06, 8.9, -2.46), (0.06, 9.6, -2.34), fer, collide=False, name="Tige")
            _lanterne(b, 0, 6.6, -2.4, fer, 0.9)
            b.ball((0, 10.4, 0), 0.32, fer, collide=False, name="Pointe")
            h = 10.7
        else:
            b.box((-2.4, 9.6, -0.15), (2.4, 9.9, 0.15), fer, collide=False, name="Bras")
            for sx in (-2.2, 2.2):
                _lanterne(b, sx, 9.9, 0, fer, 0.8)
            b.ball((0, 10.3, 0), 0.35, fer, collide=False, name="Pointe")
            h = 12.2
    return {"emprise": (1.8 if v != 2 else 5.4, 1.8 if v != 1 else 3.6), "hauteur": h}


def lanterne_murale(b, variant: int = 0) -> dict:
    """Lanterne murale sur potence de fer. Origine : face du mur, au niveau de la potence ; dépasse vers -Z."""
    fer = (c("fonte"), c("fer"), c("colombage"))[variant % 3]
    with b.group("LanterneMurale"):
        b.box((-0.4, -1.2, -0.2), (0.4, 0.4, 0.0), fer, collide=False, name="Platine")
        b.box((-0.12, 0.0, -1.8), (0.12, 0.25, -0.2), fer, collide=False, name="Potence")
        b.box((-0.08, -1.0, -0.6), (0.08, 0.0, -0.4), fer, collide=False, name="Jambe")
        b.box((-0.05, -0.5, -1.6), (0.05, 0.0, -1.5), fer, collide=False, name="Tige")
        _lanterne(b, 0, -2.6, -1.55, fer, 0.75)
    return {"emprise": (1.4, 2.0), "hauteur": 3.3}


# ---------------------------------------------------------------------------
# Enseignes et panneaux
# ---------------------------------------------------------------------------

FONDS_ENSEIGNE = (("toile_creme", "colombage"), ("drapeau_rouge", "toile_creme"), ("drapeau_vert", "toile_creme"),
                  ("drapeau_bleu", "or"), ("bois_clair", "colombage"))


def enseigne(b, texte: str = "PAIN", variant: int = 0) -> dict:
    """Enseigne en drapeau sur potence de fer forgé, perpendiculaire au mur : lisible par les joueurs qui courent.
    Origine : face du mur, au niveau de la potence (y = 0) ; la potence dépasse vers -Z.
    Le texte est sur les faces Left et Right (±X local, donc vers ±Z du monde une fois sur une façade)."""
    fond, encre = FONDS_ENSEIGNE[variant % len(FONDS_ENSEIGNE)]
    fer = c("fonte")
    long_ = min(max(1.2 + 0.9 * len(texte), 3.0), 7.0)   # longueur du panneau le long de -Z (mots courts conseillés)
    z0, z1 = -0.8, -0.8 - long_
    with b.group("Enseigne"):
        b.box((-0.35, -0.9, -0.2), (0.35, 0.5, 0.0), fer, collide=False, name="Platine")
        b.box((-0.12, 0.0, z1 - 0.4), (0.12, 0.3, -0.2), fer, collide=False, name="Potence")
        b.box((-0.1, 0.3, z1 - 0.3), (0.1, 0.7, z1 + 0.2), fer, collide=False, name="Volute")
        b.box((-0.08, -0.9, -0.55), (0.08, 0.0, -0.35), fer, collide=False, name="Jambe")
        for z in (z0 - 0.3, z1 + 0.3):
            b.box((-0.05, -0.4, z - 0.05), (0.05, 0.0, z + 0.05), fer, collide=False, shadow=False, name="Chaine")
        recto = b.box((0.0, -2.8, z1), (0.15, -0.4, z0), c(fond), collide=False, name="Planche")
        _label(recto, "Right", texte, c(encre))
        verso = b.box((-0.15, -2.8, z1), (0.0, -0.4, z0), c(fond), collide=False, name="Planche")
        _label(verso, "Left", texte, c(encre))
        b.box((-0.2, -3.0, z1 - 0.1), (0.2, -2.8, z0 + 0.1), shade(c(fond), 0.7), collide=False, name="Cadre")
    return {"emprise": (0.5, long_ + 1.2), "hauteur": 3.7}


def panneau_pied(b, texte: str = "MARCHÉ", variant: int = 0) -> dict:
    """Panneau sur deux poteaux avec petit toit de tuiles ; texte sur l'avant (-Z) et l'arrière."""
    fond, encre = (("toile_creme", "colombage"), ("bois_clair", "colombage"), ("drapeau_vert", "toile_creme"))[variant % 3]
    w = min(max(1.2 + 0.75 * len(texte), 4.0), 9.0)
    with b.group("Panneau"):
        for x in (-w / 2 + 0.4, w / 2 - 0.4):
            b.box((x - 0.25, 0, -0.25), (x + 0.25, 5.4, 0.25), c("colombage"), name="Poteau")
        p = b.box((-w / 2, 2.6, -0.2), (w / 2, 4.6, 0.2), c(fond), name="Planche")
        _label(p, "Front", texte, c(encre))
        p2 = b.box((-w / 2 + 0.1, 2.7, 0.2), (w / 2 - 0.1, 4.5, 0.3), c(fond), collide=False, name="Planche")
        _label(p2, "Back", texte, c(encre))
        b.box((-w / 2 - 0.1, 4.6, -0.3), (w / 2 + 0.1, 4.8, 0.3), c("colombage"), name="Corniche")
        b.wedge((-w / 2 - 0.4, 5.4, -0.9), (w / 2 + 0.4, 6.2, 0), c("tuile"), down="-z", studs="top", name="Toit")
        b.wedge((-w / 2 - 0.4, 5.4, 0), (w / 2 + 0.4, 6.2, 0.9), c("tuile"), down="+z", studs="top", name="Toit")
        b.box((-w / 2 - 0.4, 5.3, -0.9), (w / 2 + 0.4, 5.4, 0.9), c("colombage"), name="Sous-toit")
    return {"emprise": (w + 0.8, 1.8), "hauteur": 6.2}


def poteau_indicateur(b, textes=("MARCHÉ", "AUBERGE"), variant: int = 0) -> dict:
    """Poteau indicateur de carrefour : mât de bois, deux ou trois planches en flèche orientées différemment,
    petit chapeau de tuiles. Texte des deux côtés de chaque flèche (faces Front et Back)."""
    bois, clair = c("colombage"), (c("toile_creme"), c("bois_clair"))[variant % 2]
    encre = c("colombage")
    with b.group("Indicateur"):
        b.box((-0.9, 0, -0.9), (0.9, 0.6, 0.9), c("pierre_maison"), studs="top", name="Socle")
        b.box((-0.3, 0.6, -0.3), (0.3, 7.4, 0.3), bois, name="Mat")
        b.wedge((-0.7, 7.4, -0.7), (0.7, 8.2, 0), c("tuile"), down="-z", collide=False, name="Chapeau")
        b.wedge((-0.7, 7.4, 0), (0.7, 8.2, 0.7), c("tuile"), down="+z", collide=False, name="Chapeau")
        for k, texte in enumerate(textes[:3]):
            long_ = min(max(1.0 + 0.75 * len(texte), 3.5), 7.0)
            sens = 1 if k % 2 == 0 else -1
            y = 6.2 - k * 1.5
            with b.at((0, 0, 0), yaw=(0, 25, -20)[k]):
                xa, xb = sorted((sens * 0.3, sens * (0.3 + long_)))
                p = b.box((xa, y - 0.55, -0.12), (xb, y + 0.55, 0.0), clair, collide=False, name="Fleche")
                _label(p, "Front", texte, encre)
                p2 = b.box((xa, y - 0.55, 0.0), (xb, y + 0.55, 0.12), clair, collide=False, name="Fleche")
                _label(p2, "Back", texte, encre)
                pointe = sens * (0.3 + long_)
                b.wedge((min(pointe, pointe + sens * 0.7), y, -0.12), (max(pointe, pointe + sens * 0.7), y + 0.55, 0.12),
                        clair, down="+x" if sens > 0 else "-x", collide=False, shadow=False, name="Pointe")
                b.wedge_under((min(pointe, pointe + sens * 0.7), y - 0.55, -0.12), (max(pointe, pointe + sens * 0.7), y, 0.12),
                              clair, down="+x" if sens > 0 else "-x", collide=False, shadow=False, name="Pointe")
    return {"emprise": (2 * 7.7, 1.8), "hauteur": 8.2}


# ---------------------------------------------------------------------------
# Clôtures, bancs, bacs
# ---------------------------------------------------------------------------

def borne(b, variant: int = 0) -> dict:
    """Borne de pierre (chasse-roue) au bord du trottoir ou du quai ; variante 1 : anneau d'amarrage en fer."""
    pierre = c("pierre_maison") if variant % 2 == 0 else c("quai")
    with b.group("Borne"):
        b.box((-0.6, 0, -0.6), (0.6, 1.8, 0.6), pierre, name="Borne")
        b.box((-0.45, 1.8, -0.45), (0.45, 2.2, 0.45), shade(pierre, 1.08), studs="top", name="Tete")
        if variant % 2:
            b.cyl((-0.68, 1.1, 0), 0.35, 0.12, c("fer"), axis="x", collide=False, shadow=False, name="Anneau")
    return {"emprise": (1.2, 1.2), "hauteur": 2.2}



def cloture_bois(b, longueur: float = 12, variant: int = 0, hauteur: float = 3.0) -> dict:
    """Clôture le long de X. variant 0 : poteaux et deux lisses (campagne) ; 1 : palissade blanche ;
    2 : barrière croisée (croix de Saint-André entre poteaux)."""
    v = variant % 3
    with b.group("Cloture"):
        if v == 1:
            n = max(2, min(36, int(longueur / 0.9) + 1))
            for i in range(n):
                x = -longueur / 2 + 0.25 + i * (longueur - 0.5) / (n - 1)
                b.box((x - 0.22, 0, -0.12), (x + 0.22, hauteur - (0.3 if i % 2 else 0), 0.12), c("enduit_blanc"), name="Latte")
            for y in (0.7, hauteur - 0.9):
                b.box((-longueur / 2, y, 0.12), (longueur / 2, y + 0.3, 0.32), c("enduit_gris"), collide=False, name="Lisse")
        else:
            n = max(2, min(14, int(round(longueur / 3)) + 1))
            pas = longueur / (n - 1)
            for i in range(n):
                x = -longueur / 2 + i * pas
                b.box((x - 0.3, 0, -0.3), (x + 0.3, hauteur + 0.3, 0.3), c("bois" if i % 2 else "bois_moyen"), name="Poteau")
            if v == 0:
                for y in (hauteur * 0.4, hauteur * 0.85):
                    b.box((-longueur / 2, y - 0.2, -0.45), (longueur / 2, y + 0.2, -0.3), c("bois_clair"), name="Lisse")
            else:
                b.box((-longueur / 2, hauteur - 0.3, -0.45), (longueur / 2, hauteur + 0.1, -0.3), c("bois_clair"), name="Lisse")
                ang = math.degrees(math.atan2(hauteur - 0.6, pas))
                L = math.hypot(pas, hauteur - 0.6)
                for i in range(min(n - 1, 12)):
                    xm = -longueur / 2 + (i + 0.5) * pas
                    for sgn in (-1, 1):
                        b.part("block", (L - 0.4, 0.3, 0.12), (xm, (hauteur - 0.3) / 2, -0.38 + 0.13 * (sgn > 0)),
                               rot_z(sgn * ang), c("bois_clair"), collide=False, name="Croix")
    return {"emprise": (longueur, 0.9), "hauteur": hauteur + 0.3}


def banc(b, variant: int = 0) -> dict:
    """Banc de bois à dossier (pieds de fonte en variante 1)."""
    pied = c("fonte") if variant % 2 else c("bois")
    assise = (c("bois_clair"), c("bois_moyen"), c("volet_vert"))[variant % 3]
    with b.group("Banc"):
        for x in (-2.4, 2.4):
            b.box((x - 0.25, 0, -0.9), (x + 0.25, 1.6, 0.7), pied, name="Pied")
            b.box((x - 0.25, 1.6, 0.5), (x + 0.25, 3.4, 0.8), pied, name="Montant")
        b.box((-3.0, 1.6, -1.0), (3.0, 1.95, 0.8), assise, studs="top", name="Assise")
        b.box((-3.0, 2.4, 0.8), (3.0, 3.3, 1.05), assise, name="Dossier")
    return {"emprise": (6.0, 2.1), "hauteur": 3.4}


def bac_fleurs(b, variant: int = 0) -> dict:
    """Bac de bois (ou de pierre) planté de fleurs : géraniums rouges, fleurs jaunes, lavande, buis."""
    fleurs = (("fleur_rouge", "fleur_rose"), ("fleur_jaune", "fleur_blanche"), ("fleur_mauve", "fleur_bleue"),
              ("feuille", "feuille_claire"))[variant % 4]
    bac = c("bois") if variant % 2 == 0 else c("pierre_maison")
    with b.group("BacFleurs"):
        b.box((-1.5, 0, -1.0), (1.5, 1.6, 1.0), bac, name="Bac")
        b.box((-1.65, 1.6, -1.15), (1.65, 1.85, 1.15), shade(bac, 0.85), name="Rebord")
        b.box((-1.3, 1.85, -0.8), (1.3, 2.6, 0.8), c("feuille_fonce"), collide=False, name="Feuillage")
        b.box((-1.1, 2.6, -0.6), (0.2, 3.1, 0.3), c(fleurs[0]), collide=False, name="Fleurs")
        b.box((0.0, 2.6, -0.1), (1.1, 3.0, 0.65), c(fleurs[1]), collide=False, name="Fleurs")
        b.box((-0.5, 2.6, 0.2), (0.4, 3.3, 0.7), c(fleurs[0]), collide=False, name="Fleurs")
    return {"emprise": (3.3, 2.3), "hauteur": 3.3}


# ---------------------------------------------------------------------------
# Marchandises et objets de rue
# ---------------------------------------------------------------------------

def caisses(b, variant: int = 0) -> dict:
    """Pile de caisses de bois cerclées."""
    rng = b.rng
    pile = [((-1.2, 0, 0), 2.2), ((1.3, 0, 0.3), 2.0), ((-0.2, 2.2, 0.1), 1.8), ((2.0, 0, -1.9), 1.6)][: 2 + variant % 3]
    with b.group("Caisses"):
        for (x, y, z), s in pile:
            yaw = float(rng.uniform(-10, 10))
            col = vary("bois_clair", rng, 0.08)
            b.boxc((x, y + s / 2, z), (s, s, s), col, yaw=yaw, studs="top", name="Caisse")
            b.boxc((x, y + s / 2, z), (s + 0.12, s * 0.2, s + 0.12), c("bois_moyen"), yaw=yaw, collide=False, name="Cerclage")
    return {"emprise": (5.2, 4.4), "hauteur": 4.0}


def tonneaux(b, variant: int = 0) -> dict:
    """Tonneaux de bois cerclés de fer (eau, farine, pommes)."""
    pos = ((-1.1, 0), (1.1, 0.3), (0, 1.9), (-2.2, 1.7))[: 2 + variant % 3]
    with b.group("Tonneaux"):
        for x, z in pos:
            b.cyl((x, 1.4, z), 1.0, 2.8, c("bois_moyen"), axis="y", name="Tonneau")
            for y in (0.55, 2.25):
                b.cyl((x, y, z), 1.06, 0.25, c("fer"), axis="y", collide=False, name="Cercle")
            b.cyl((x, 2.85, z), 0.85, 0.1, c("bois_clair"), axis="y", collide=False, name="Couvercle")
        if variant % 2:
            x, z = pos[0]
            b.ball((x - 0.3, 2.95, z), 0.32, c("pomme"), collide=False, name="Pomme")
            b.ball((x + 0.35, 2.95, z + 0.2), 0.32, c("pomme"), collide=False, name="Pomme")
    return {"emprise": (4.4, 4.0), "hauteur": 3.0}


def sacs(b, variant: int = 0) -> dict:
    """Sacs de grain empilés."""
    rng = b.rng
    poses = [(-1.0, 0, 0), (1.0, 0, 0.2), (0.0, 1.3, 0.1), (0.0, 0, 1.6)][: 3 + variant % 2]
    with b.group("Sacs"):
        for (x, y, z) in poses:
            yaw = float(rng.uniform(-15, 15))
            b.boxc((x, y + 0.65, z), (1.9, 1.3, 1.3), vary("toile_creme", rng, 0.05), yaw=yaw, name="Sac")
            b.boxc((x, y + 1.45, z), (0.6, 0.3, 0.6), c("corde"), yaw=yaw, collide=False, name="Noeud")
    return {"emprise": (3.8, 3.0), "hauteur": 2.8}


def charrette(b, variant: int = 0) -> dict:
    """Charrette à deux roues (timons vers -Z). variant 0 : foin ; 1 : caisses et tonneau ; 2 : sacs ; 3 : vide."""
    bois, clair = c("bois"), c("bois_clair")
    v = variant % 4
    with b.group("Charrette"):
        for sx in (-1, 1):
            b.cyl((sx * 2.3, 1.8, 0.6), 1.8, 0.4, c("bois_moyen"), axis="x", name="Roue")
            b.cyl((sx * 2.55, 1.8, 0.6), 0.45, 0.3, c("fer"), axis="x", collide=False, name="Moyeu")
            b.cyl((sx * 2.3, 1.8, 0.6), 1.85, 0.25, c("fer"), axis="x", collide=False, name="Bandage")
        b.box((-2.05, 1.8, 0.4), (2.05, 2.1, 0.8), c("fer"), collide=False, name="Essieu")
        b.box((-2.0, 2.1, -2.6), (2.0, 2.6, 3.6), bois, studs="top", name="Plateau")
        for sx in (-1, 1):
            b.box((sx * 2.0 - 0.15, 2.6, -2.6), (sx * 2.0 + 0.15, 3.8, 3.6), clair, name="Ridelle")
            b.box((sx * 1.2 - 0.2, 2.2, -6.5), (sx * 1.2 + 0.2, 2.6, -2.6), bois, name="Timon")
        b.box((-1.85, 2.6, 3.45), (1.85, 3.8, 3.6), clair, name="Hayon")
        b.box((-1.4, 0.0, -6.3), (1.4, 2.2, -5.9), bois, collide=False, name="Bequille")
        if v == 0:
            b.box((-1.85, 2.6, -2.4), (1.85, 4.6, 3.4), c("foin"), studs="top", name="Foin")
            b.box((-1.4, 4.6, -1.8), (1.4, 5.4, 2.6), c("foin_fonce"), studs="top", collide=False, name="Foin")
        elif v == 1:
            b.box((-1.7, 2.6, -2.3), (0.1, 4.4, -0.5), c("bois_clair"), studs="top", name="Caisse")
            b.box((0.0, 2.6, 0.4), (1.7, 4.2, 2.2), shade(c("bois_clair"), 0.9), studs="top", name="Caisse")
            b.cyl((-0.95, 3.9, 2.4), 0.8, 2.6, c("bois_moyen"), axis="y", name="Tonneau")
        elif v == 2:
            for i, z in enumerate((-1.8, 0.0, 1.8)):
                b.boxc((0.4 * (-1) ** i, 3.25, z), (2.6, 1.3, 1.6), c("toile_creme"), yaw=8 * (-1) ** i, name="Sac")
    return {"emprise": (5.2, 10.2), "hauteur": 5.4}


def brouette(b, variant: int = 0) -> dict:
    """Brouette de bois à une roue (roue vers -Z, brancards vers +Z) ; chargement de foin, de pommes ou de bûches."""
    bois, clair = c("bois"), c("bois_clair")
    charge = (("foin", "foin_fonce"), ("pomme", "feuille_claire"), ("tronc_clair", "tronc"))[variant % 3]
    with b.group("Brouette"):
        b.cyl((0, 0.9, -1.9), 0.9, 0.35, c("bois_moyen"), axis="x", name="Roue")
        b.cyl((0, 0.9, -1.9), 0.25, 0.6, c("fer"), axis="x", collide=False, name="Moyeu")
        b.wedge((-1.1, 1.0, -1.6), (1.1, 2.2, -0.6), clair, down="-z", name="Caisse")
        b.box((-1.1, 1.0, -0.6), (1.1, 2.2, 1.0), clair, name="Caisse")
        b.box((-0.85, 2.2, -0.9), (0.85, 2.6, 0.8), c(charge[0]), studs="top", collide=False, name="Charge")
        b.box((-0.5, 2.6, -0.4), (0.4, 2.9, 0.4), c(charge[1]), collide=False, name="Charge")
        for sx in (-1, 1):
            b.box((sx * 0.85 - 0.12, 1.3, 1.0), (sx * 0.85 + 0.12, 1.55, 2.8), bois, collide=False, name="Brancard")
            b.box((sx * 0.75 - 0.12, 0, 0.6), (sx * 0.75 + 0.12, 1.0, 0.85), bois, name="Pied")
    return {"emprise": (2.2, 4.8), "hauteur": 2.9}


def canon_affut(b, variant: int = 0) -> dict:
    """Canon de campagne sur affût de bois à deux roues (bouche vers -Z) ; variante 1 : bâche sur le tube.
    Artillerie générique, sans insigne."""
    fonte, bois = c("fonte"), c("bois_moyen")
    with b.group("Canon"):
        for sx in (-1, 1):
            b.cyl((sx * 1.6, 1.5, -0.6), 1.5, 0.35, bois, axis="x", name="Roue")
            b.cyl((sx * 1.6, 1.5, -0.6), 1.55, 0.2, c("fer"), axis="x", collide=False, name="Bandage")
            b.cyl((sx * 1.85, 1.5, -0.6), 0.35, 0.3, c("fer"), collide=False, axis="x", name="Moyeu")
            b.box((sx * 0.9 - 0.25, 0.9, -1.4), (sx * 0.9 + 0.25, 2.0, 2.4), c("bois"), name="Flasque")
        b.box((-1.45, 1.35, -0.75), (1.45, 1.65, -0.45), c("fer"), collide=False, name="Essieu")
        b.box((-0.4, 0, 2.4), (0.4, 1.1, 4.4), c("bois"), name="Crosse")
        b.cyl((0, 2.4, -0.6), 0.75, 3.6, fonte, axis="z", name="Tube")
        b.cyl((0, 2.4, -2.6), 0.88, 0.5, fonte, axis="z", collide=False, name="Bouche")
        b.cyl((0, 2.4, 1.3), 0.95, 0.6, fonte, axis="z", collide=False, name="Culasse")
        if variant % 2:
            b.box((-0.85, 2.3, -1.4), (0.85, 3.35, 1.4), c("toile_creme"), collide=False, name="Bache")
        else:
            b.ball((0, 2.4, 1.9), 0.5, fonte, collide=False, name="Bouton")
    return {"emprise": (3.8, 7.0), "hauteur": 3.4}


ETALS = (
    ("toile_rouge", "toile_creme", ("pomme", "feuille_claire", "fleur_jaune")),     # fruits et légumes
    ("toile_verte", "toile_creme", ("bois_clair", "enduit_ocre", "terre")),          # pains
    ("toile_bleue", "toile_creme", ("fleur_rouge", "fleur_mauve", "fleur_jaune")),   # fleurs
    ("toile_jaune", "toile_rouge", ("enduit_jaune", "ble", "enduit_blanc")),         # fromages
)


def etal(b, variant: int = 0) -> dict:
    """Étal de marché : table, quatre poteaux, auvent rayé incliné vers l'avant (-Z), cagettes de marchandises."""
    col_a, col_b, marchandises = ETALS[variant % len(ETALS)]
    bois = c("bois")
    w, d = 4.0, 2.4
    with b.group("Etal"):
        for x in (-w + 0.3, w - 0.3):
            b.box((x - 0.25, 0, -d + 0.1), (x + 0.25, 6.0, -d + 0.6), bois, name="Poteau")
            b.box((x - 0.25, 0, d - 0.6), (x + 0.25, 7.2, d - 0.1), bois, name="Poteau")
        b.box((-w, 2.6, -d), (w, 3.0, d - 0.6), c("bois_clair"), studs="top", name="Table")
        b.box((-w + 0.4, 0, -d + 0.2), (w - 0.4, 2.6, -d + 0.5), c("bois_moyen"), name="Facade")
        # auvent rayé en 6 lés alternés, incliné vers l'avant
        n = 6
        for i in range(n):
            x0 = -w - 0.4 + i * (2 * w + 0.8) / n
            x1 = x0 + (2 * w + 0.8) / n
            b.wedge((x0, 6.0, -d - 1.2), (x1, 7.4, d), c(col_a if i % 2 == 0 else col_b), down="-z", collide=False, name="Auvent")
        for i in range(n):
            x0 = -w - 0.4 + i * (2 * w + 0.8) / n
            x1 = x0 + (2 * w + 0.8) / n
            b.box((x0, 5.4, -d - 1.35), (x1, 6.0, -d - 1.2), c(col_b if i % 2 == 0 else col_a), collide=False, name="Lambrequin")
        # cagettes et marchandises
        for i, x in enumerate((-2.6, 0.0, 2.6)):
            b.box((x - 1.1, 3.0, -1.9), (x + 1.1, 3.6, -0.1), c("bois_clair"), collide=False, name="Cagette")
            b.box((x - 0.9, 3.6, -1.7), (x + 0.9, 4.2, -0.3), c(marchandises[i]), studs="top", collide=False, name="Marchandise")
        b.box((-w + 0.6, 3.0, 0.4), (w - 0.6, 3.9, 1.2), c("toile_creme"), collide=False, name="Sacs")
    return {"emprise": (2 * w + 0.8, 2 * d + 1.4), "hauteur": 7.4}


def puits(b, variant: int = 0) -> dict:
    """Puits de pierre : margelle (ronde ou carrée), deux montants, treuil, seau, petit toit de tuiles ou d'ardoise."""
    toit = (c("tuile"), c("ardoise"), c("tuile_brune"))[variant % 3]
    pierre = c("pierre_maison")
    with b.group("Puits"):
        if variant % 2 == 0:
            b.cyl((0, 1.6, 0), 2.6, 3.2, pierre, axis="y", name="Margelle")
            b.cyl((0, 3.3, 0), 2.75, 0.25, c("pierre_maison_claire"), axis="y", studs="top", name="Couronne")
            b.cyl((0, 3.45, 0), 1.9, 0.12, c("eau_fonce"), axis="y", collide=False, name="Eau")
        else:
            b.box((-2.6, 0, -2.6), (2.6, 3.2, 2.6), pierre, name="Margelle")
            b.box((-2.75, 3.2, -2.75), (2.75, 3.5, 2.75), c("pierre_maison_claire"), studs="top", name="Couronne")
            b.box((-1.9, 3.5, -1.9), (1.9, 3.62, 1.9), c("eau_fonce"), collide=False, name="Eau")
        for x in (-2.2, 2.2):
            b.box((x - 0.3, 3.2, -0.3), (x + 0.3, 8.2, 0.3), c("bois"), name="Montant")
        b.cyl((0, 6.6, 0), 0.35, 4.1, c("bois_clair"), axis="x", collide=False, name="Treuil")
        b.box((2.5, 6.4, -0.1), (2.7, 6.8, 1.2), c("fer"), collide=False, name="Manivelle")
        b.box((-0.05, 4.9, -0.05), (0.05, 6.3, 0.05), c("corde"), collide=False, shadow=False, name="Corde")
        b.cyl((0, 4.5, 0), 0.5, 0.8, c("bois_moyen"), axis="y", collide=False, name="Seau")
        b.box((-3.3, 9.8, -0.35), (3.3, 10.3, 0.35), c("bois"), name="Faitiere")
        b.wedge((-3.2, 8.2, -2.4), (3.2, 10.0, 0), toit, down="-z", studs="top", name="Toit")
        b.wedge((-3.2, 8.2, 0), (3.2, 10.0, 2.4), toit, down="+z", studs="top", name="Toit")
    return {"emprise": (6.4, 5.5), "hauteur": 10.0}


def abreuvoir(b, variant: int = 0) -> dict:
    """Abreuvoir de pierre (ou de bois) avec pompe à bras."""
    pierre = c("pierre_maison") if variant % 2 == 0 else c("bois_moyen")
    with b.group("Abreuvoir"):
        b.box((-3.0, 0, -1.2), (3.0, 1.8, 1.2), pierre, name="Bac")
        b.box((-2.6, 1.8, -0.8), (2.6, 1.9, 0.8), c("eau"), collide=False, name="Eau")
        for x in (-3.0, 3.0):
            b.box((x - 0.15, 1.8, -1.2), (x + 0.15, 2.05, 1.2), shade(pierre, 0.85), collide=False, name="Rebord")
        b.box((2.0, 0, 1.2), (2.8, 4.2, 2.0), c("fer"), name="Pompe")
        b.box((2.2, 3.4, -0.2), (2.6, 3.7, 1.2), c("fer"), collide=False, name="Bec")
        b.box((2.25, 4.2, 1.45), (2.55, 4.5, 3.4), c("fonte"), collide=False, name="Bras")
    return {"emprise": (6.0, 4.6), "hauteur": 4.5}


def pile_boulets(b, variant: int = 0) -> dict:
    """Pyramide de boulets de canon sur une palette de bois (3 étages, ou 2 en variante 1)."""
    r = 0.6
    etages = 3 if variant % 2 == 0 else 2
    with b.group("Boulets"):
        n0 = etages
        demi = n0 * r + 0.3
        b.box((-demi, 0, -demi), (demi, 0.4, demi), c("bois"), studs="top", name="Palette")
        for k in range(etages):
            n = etages - k
            y = 0.4 + r + k * r * 1.42
            for i in range(n):
                for j in range(n):
                    b.ball(((i - (n - 1) / 2) * 2 * r, y, (j - (n - 1) / 2) * 2 * r), r, c("fonte"), collide=False, name="Boulet")
    return {"emprise": (2 * demi, 2 * demi), "hauteur": 0.4 + 2 * r + (etages - 1) * r * 1.42}


def bottes_foin(b, variant: int = 0) -> dict:
    """Bottes de foin rectangulaires empilées."""
    rng = b.rng
    poses = [(-1.3, 0, 0), (1.3, 0, 0.2), (0.0, 1.6, 0.1), (0.2, 0, 2.4), (-0.3, 1.6, 2.3)][: 3 + variant % 3]
    with b.group("BottesFoin"):
        for (x, y, z) in poses:
            yaw = float(rng.uniform(-8, 8))
            b.boxc((x, y + 0.8, z), (2.5, 1.6, 1.8), vary("foin", rng, 0.05), yaw=yaw, studs="top", name="Botte")
            b.boxc((x, y + 0.8, z), (0.25, 1.65, 1.85), c("foin_fonce"), yaw=yaw, collide=False, name="Lien")
    return {"emprise": (5.2, 4.6), "hauteur": 3.2}


def tas_bois(b, variant: int = 0) -> dict:
    """Bûches empilées contre un mur, sous un petit appentis (l'arrière +Z se pose contre un mur)."""
    with b.group("TasBois"):
        b.box((-3.0, 0, -0.9), (3.0, 0.3, 0.9), c("bois"), name="Lambourde")
        for k in range(3):
            n = 4 - k % 2
            for i in range(n):
                x = -2.25 + (k % 2) * 0.75 + i * 1.5
                b.cyl((x, 0.3 + 0.7 + k * 1.3, 0), 0.68, 1.8, vary("tronc_clair", b.rng, 0.1), axis="z", collide=False, name="Buche")
        b.box((-3.0, 0.3, -0.9), (-2.8, 4.6, 0.9), c("bois"), name="Montant")
        b.box((2.8, 0.3, -0.9), (3.0, 4.6, 0.9), c("bois"), name="Montant")
        b.wedge((-3.4, 4.6, -1.6), (3.4, 5.6, 1.1), c("tuile_brune") if variant % 2 else c("bois_gris"), down="-z", studs="top", name="Appentis")
    return {"emprise": (6.8, 2.7), "hauteur": 5.6}


# ---------------------------------------------------------------------------
# Drapeaux et fanions
# ---------------------------------------------------------------------------

def _tissu_drapeau(b, x0, y0, z, long_, haut, variant: int) -> None:
    """Drapeau rectangulaire générique (aucun emblème) le long de +X depuis la hampe, en 3 lés « flottants »."""
    v = variant % 4
    cols = {0: ("drapeau_rouge", "drapeau_blanc", "drapeau_rouge"),     # rouge à bande blanche
            1: ("drapeau_vert", "drapeau_blanc", "drapeau_vert"),       # vert à bande blanche
            2: ("drapeau_rouge", "drapeau_rouge", "drapeau_rouge"),     # rouge uni, bordure blanche
            3: ("drapeau_bleu", "drapeau_blanc", "drapeau_bleu")}[v]
    n = 3
    for i in range(n):
        xa = x0 + i * long_ / n
        xb = xa + long_ / n
        dz = (0.0, 0.25, -0.05)[i]
        dy = (0.0, -0.15, -0.35)[i]
        for k, col in enumerate(cols):
            ya = y0 + dy + haut * (1 - (k + 1) / 3)
            b.box((xa, ya, z - 0.08 + dz), (xb, ya + haut / 3, z + 0.08 + dz), c(col), collide=False, shadow=False, name="Drapeau")
    if v == 2:
        b.box((x0 + long_, y0 - 0.35, z - 0.1 + 0.0), (x0 + long_ + 0.3, y0 + haut - 0.35, z + 0.1), c("drapeau_blanc"),
              collide=False, shadow=False, name="Bordure")


def drapeau(b, hauteur: float = 12, variant: int = 0, longueur: float = 5.0) -> dict:
    """Mât à drapeau (hampe de bois, pommeau doré) ; drapeau générique rouge, vert ou bleu à bande blanche."""
    with b.group("Drapeau"):
        b.box((-0.7, 0, -0.7), (0.7, 0.6, 0.7), c("fonte"), name="Pied")
        b.cyl((0, hauteur / 2, 0), 0.22, hauteur, c("bois"), axis="y", name="Hampe")
        b.ball((0, hauteur + 0.25, 0), 0.4, c("or"), collide=False, name="Pommeau")
        haut = longueur * 0.6
        _tissu_drapeau(b, 0.22, hauteur - 0.4 - haut, 0, longueur, haut, variant)
    return {"emprise": (longueur + 1, 1.4), "hauteur": hauteur + 0.65}


def guirlande_fanions(b, p0, p1, n: int = 10, creux: float = 2.0, variant: int = 0) -> dict:
    """Guirlande de fanions triangulaires entre deux points (coordonnées du repère courant, comme DS).
    À poser au-dessus de 30 studs quand elle traverse le couloir (le bas des fanions compris)."""
    p0a, p1a = np.asarray(p0, float), np.asarray(p1, float)
    d = p1a - p0a
    yaw = -math.degrees(math.atan2(d[2], d[0]))
    pal = (("drapeau_rouge", "drapeau_blanc", "toile_jaune", "drapeau_vert"),
           ("drapeau_rouge", "toile_jaune"),
           ("drapeau_bleu", "drapeau_blanc", "drapeau_rouge"))[variant % 3]
    pts = _chainette(p0, p1, creux, 8)
    with b.group("Fanions"):
        for a, bb in zip(pts, pts[1:]):
            _segment(b, a, bb, 0.07, c("corde"), name="Corde")
        for i in range(n):
            t = (i + 1) / (n + 1)
            p = p0a + d * t
            y = p[1] - creux * 4 * t * (1 - t)
            col = c(pal[i % len(pal)])
            with b.at((p[0], 0, p[2]), yaw=yaw):
                b.wedge_under((-0.7, y - 1.8, -0.05), (0.0, y - 0.05, 0.05), col, down="-x", collide=False, shadow=False, name="Fanion")
                b.wedge_under((0.0, y - 1.8, -0.05), (0.7, y - 0.05, 0.05), col, down="+x", collide=False, shadow=False, name="Fanion")
    return {"fanions": n}
