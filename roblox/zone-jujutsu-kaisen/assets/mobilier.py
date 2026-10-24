"""Mobilier urbain de la ville de nuit : poteaux électriques et câbles, feux tricolores japonais,
distributeurs de boissons, garde-corps, lampadaires, enseignes verticales au néon, arbres
d'alignement, poubelles de tri, vélos garés, panneaux routiers, cônes et barrières de chantier
立入禁止 (zone de l'incident), climatiseurs.

Chaque fonction respecte les conventions (origine au centre de l'emprise au sol, avant vers -Z local)
et reste sous 40 pièces. Les petits détails n'ont ni collision ni ombre. Les autres modules peuvent
importer `enseigne_verticale`, `clim`, `cable` et `_segment` pour habiller leurs bâtiments.
"""

from __future__ import annotations

import numpy as np

from kit import shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------


def _segment(b, a, bb, rayon: float, col, name: str = "Cable", collide: bool = False) -> None:
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
           collide=collide, shadow=False, name=name)


def _chainette(p0, p1, creux: float, n: int):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    pts = []
    for i in range(n + 1):
        t = i / n
        p = p0 + (p1 - p0) * t
        p[1] -= creux * 4 * t * (1 - t)
        pts.append(p)
    return pts


def cable(b, p0, p1, creux: float = 1.2, segments: int = 4, rayon: float = 0.09, col=None) -> int:
    """Câble électrique affaissé entre deux points (coordonnées du repère courant). Renvoie le nombre de pièces."""
    pts = _chainette(p0, p1, creux, segments)
    col = col or c("cable")
    for a, bb in zip(pts, pts[1:]):
        _segment(b, a, bb, rayon, col, name="Cable")
    return segments


def clim(b, x: float, y: float, z: float, sens: str = "-z") -> None:
    """Petit climatiseur extérieur posé contre une façade (3 pièces). (x, y, z) = centre du bas, contre le mur ;
    l'appareil dépasse vers `sens` (-z, +z, -x ou +x)."""
    w, h, d = 2.0, 1.6, 0.9
    dx, dz = {"-z": (0, -1), "+z": (0, 1), "-x": (-1, 0), "+x": (1, 0)}[sens]
    if dz:
        a, bb = (x - w / 2, y, z), (x + w / 2, y + h, z + dz * d)
        b.box(a, bb, c("clim"), collide=False, name="Clim")
        b.cyl((x + 0.35, y + h / 2, z + dz * (d + 0.05)), 0.55, 0.12, c("metal_fonce"), axis="z", collide=False, shadow=False, name="Grille")
        b.box((x - w / 2, y - 0.25, z), (x + w / 2, y, z + dz * (d + 0.15)), c("metal_fonce"), collide=False, shadow=False, name="Console")
    else:
        a, bb = (x, y, z - w / 2), (x + dx * d, y + h, z + w / 2)
        b.box(a, bb, c("clim"), collide=False, name="Clim")
        b.cyl((x + dx * (d + 0.05), y + h / 2, z + 0.35), 0.55, 0.12, c("metal_fonce"), axis="x", collide=False, shadow=False, name="Grille")
        b.box((x, y - 0.25, z - w / 2), (x + dx * (d + 0.15), y, z + w / 2), c("metal_fonce"), collide=False, shadow=False, name="Console")


# ---------------------------------------------------------------------------
# Réseau électrique
# ---------------------------------------------------------------------------


def poteau_electrique(b, variant: int = 0, hauteur: float = 24) -> dict:
    """Poteau électrique japonais en béton : deux traverses à isolateurs, transformateur cylindrique,
    échelons, manchon rayé jaune et noir. Les câbles courent le long de l'axe X local (le long de la rue) ;
    les traverses sont selon Z (±2,5). Renvoie les points d'accroche des câbles en coordonnées monde."""
    H = hauteur
    beton, metal = c("poteau_beton"), c("metal_fonce")
    with b.group("Poteau"):
        b.box((-0.9, 0, -0.9), (0.9, 0.4, 0.9), c("beton_fonce"), studs="top", name="Socle")
        b.cyl((0, H / 2, 0), 0.55, H, vary(beton, b.rng, 0.03), name="Fut")
        b.cyl((0, H + 0.15, 0), 0.62, 0.3, shade(beton, 0.85), collide=False, name="Chapeau")
        # traverses et isolateurs
        y1, y2 = H - 1.2, H - 3.6
        b.box((-0.25, y1 - 0.25, -2.6), (0.25, y1 + 0.25, 2.6), metal, collide=False, name="Traverse")
        b.box((-0.25, y2 - 0.25, -2.1), (0.25, y2 + 0.25, 2.1), metal, collide=False, name="Traverse")
        for z in (-2.2, 0.0, 2.2):
            b.cyl((0, y1 + 0.55, z), 0.22, 0.6, c("blanc"), collide=False, shadow=False, name="Isolateur")
        for z in (-1.8, 1.8):
            b.cyl((0, y2 + 0.55, z), 0.22, 0.6, c("blanc"), collide=False, shadow=False, name="Isolateur")
        # transformateur(s) côté arrière (+Z local, vers la façade)
        if variant % 3 != 1:
            b.box((-0.2, H - 7.2, 0.5), (0.2, H - 6.8, 1.4), metal, collide=False, name="Console")
            b.cyl((0, H - 8.2, 1.65), 1.0, 2.8, c("transfo"), collide=False, name="Transfo")
            b.cyl((0, H - 6.7, 1.65), 1.05, 0.2, shade(c("transfo"), 0.8), collide=False, name="Couvercle")
        if variant % 3 == 2:
            b.cyl((0, H - 12.0, 1.65), 0.9, 2.4, c("transfo"), collide=False, name="Transfo")
            b.box((-0.2, H - 10.9, 0.5), (0.2, H - 10.6, 1.4), metal, collide=False, name="Console")
        # échelons (côté rue)
        for k in range(4):
            y = 6 + k * 2.2
            b.box((-0.08, y, -0.95 if k % 2 else 0.55), (0.08, y + 0.16, -0.55 if k % 2 else 0.95), metal,
                  collide=False, shadow=False, name="Echelon")
        # manchon rayé (protection) et petite plaque bleue
        b.cyl((0, 1.6, 0), 0.6, 2.4, c("chantier_jaune"), collide=False, name="Manchon")
        for y in (0.9, 2.1):
            b.cyl((0, y, 0), 0.61, 0.4, c("chantier_noir"), collide=False, shadow=False, name="Rayure")
        b.box((-0.55, 7.0, -0.62), (0.55, 9.0, -0.56), c("auvent_bleu"), collide=False, shadow=False, name="Plaque")
    acc = [(0, y1 + 0.85, -2.2), (0, y1 + 0.85, 0.0), (0, y1 + 0.85, 2.2), (0, y2 + 0.85, -1.8), (0, y2 + 0.85, 1.8)]
    return {"emprise": (1.8, 5.2), "hauteur": H + 0.3, "accroches": [tuple(float(v) for v in b.to_world(p)) for p in acc]}


# ---------------------------------------------------------------------------
# Feux, lampadaires, panneaux
# ---------------------------------------------------------------------------


def feu_tricolore(b, variant: int = 0, hauteur: float = 13, bras: float = 6.5) -> dict:
    """Feu tricolore japonais : potence vers l'avant (-Z local, au-dessus du bord de chaussée), boîtier
    horizontal à trois feux (vert bleuté, jaune, rouge) visible des deux sens de circulation (faces ±X),
    feu piétons vertical sur le mât (face -Z) et boîte d'appel.
    variant 0 : vert allumé ; 1 : rouge ; 2 : jaune. Avec bras = 6,5 et le mât à |x| = 40,5,
    le boîtier s'arrête à |x| ≈ 33,6 : il reste hors du couloir."""
    H = hauteur
    boit, gris = c("feu_boitier"), c("metal")
    allume = ("feu_vert", "feu_rouge", "feu_jaune")[variant % 3]
    with b.group("Feu"):
        b.box((-0.8, 0, -0.8), (0.8, 0.4, 0.8), c("beton_fonce"), studs="top", name="Socle")
        b.cyl((0, H / 2, 0), 0.32, H, gris, name="Mat")
        b.cyl((0, H + 0.1, 0), 0.38, 0.2, shade(gris, 0.8), collide=False, name="Chapeau")
        b.box((-0.18, H - 0.6, -bras), (0.18, H - 0.25, 0.1), gris, collide=False, name="Potence")
        _segment(b, (0, H - 2.6, -0.2), (0, H - 0.45, -2.6), 0.1, gris, name="Hauban")
        # boîtier : long selon Z (le long de la potence), feux sur les faces ±X
        zc = -bras + 1.9
        b.box((-0.45, H - 1.85, zc - 2.3), (0.45, H - 0.45, zc + 2.3), boit, collide=False, name="Boitier")
        for k, nom in enumerate(("feu_vert", "feu_jaune", "feu_rouge")):
            z = zc + 1.45 - k * 1.45     # rouge du côté de la chaussée
            on = nom == allume
            col = c(nom) if on else shade(c(nom), 0.35)
            for sx in (-1, 1):
                b.cyl((sx * 0.5, H - 1.15, z), 0.5, 0.12, col, axis="x", material="Neon" if on else "SmoothPlastic",
                      collide=False, shadow=False, name="Lampe")
            b.box((-0.75, H - 0.6, z - 0.6), (0.75, H - 0.45, z + 0.6), boit, collide=False, shadow=False, name="Visiere")
        # feu piétons (vertical, face -Z) : rouge en haut, vert en bas
        pieton_vert = variant % 3 == 1
        b.box((-0.6, 6.4, -0.75), (0.6, 9.4, -0.3), boit, collide=False, name="FeuPietons")
        b.box((-0.45, 8.0, -0.85), (0.45, 9.2, -0.75), c("feu_rouge") if not pieton_vert else shade(c("feu_rouge"), 0.35),
              material="Neon" if not pieton_vert else "SmoothPlastic", collide=False, shadow=False, name="Pieton")
        b.box((-0.45, 6.6, -0.85), (0.45, 7.8, -0.75), c("feu_vert") if pieton_vert else shade(c("feu_vert"), 0.35),
              material="Neon" if pieton_vert else "SmoothPlastic", collide=False, shadow=False, name="Pieton")
        b.box((-0.35, 3.6, -0.65), (0.35, 4.6, -0.3), c("jaune"), collide=False, name="BoiteAppel")
        # plaque de rue bleue sous la potence
        b.box((-0.08, H - 3.4, -3.6), (0.08, H - 2.4, -1.0), c("auvent_bleu"), collide=False, shadow=False, name="PlaqueRue")
    return {"emprise": (1.6, bras + 0.6), "hauteur": H + 0.2}


def lampadaire(b, variant: int = 0, hauteur: float = 14) -> dict:
    """Lampadaire de rue : mât gris, crosse vers l'avant (-Z) de 2,4 studs, tête à LED (Neon).
    variant 1 : double crosse (avant et arrière) ; variant 2 : lampadaire décoratif à deux globes."""
    H = hauteur
    gris = (c("metal"), c("metal_fonce"), c("anthracite"))[variant % 3]
    with b.group("Lampadaire"):
        b.box((-0.7, 0, -0.7), (0.7, 0.4, 0.7), c("beton_fonce"), studs="top", name="Socle")
        b.cyl((0, 1.0, 0), 0.45, 1.2, gris, name="Pied")
        b.cyl((0, H / 2, 0), 0.26, H, gris, name="Mat")
        if variant % 3 == 2:
            b.box((-0.15, H - 1.2, -1.6), (0.15, H - 0.9, 1.6), gris, collide=False, name="Traverse")
            for z in (-1.4, 1.4):
                b.ball((0, H - 1.9, z), 0.75, c("fenetre_chaude"), material="Neon", collide=False, shadow=False, name="Globe")
                b.cyl((0, H - 1.05, z), 0.35, 0.3, gris, collide=False, name="Douille")
            b.ball((0, H + 0.2, 0), 0.4, gris, collide=False, name="Pointe")
        else:
            sens = (-1, 1) if variant % 3 == 1 else (-1,)
            for s in sens:
                b.box((-0.15, H - 0.3, min(0, s * 2.4)), (0.15, H, max(0, s * 2.4)), gris, collide=False, name="Crosse")
                b.box((-0.45, H - 0.55, s * 2.4 - 0.9), (0.45, H - 0.15, s * 2.4 + 0.9), gris, collide=False, name="Tete")
                b.box((-0.35, H - 0.7, s * 2.4 - 0.75), (0.35, H - 0.55, s * 2.4 + 0.75), c("neon_blanc"), material="Neon",
                      collide=False, shadow=False, name="LED")
    return {"emprise": (1.4, 5.8), "hauteur": H}


def panneau_route(b, variant: int = 0) -> dict:
    """Panneau routier japonais : 0 = triangle rouge inversé 止まれ ; 1 = disque bleu (sens obligatoire) ;
    2 = panneau bleu de direction (駅 / 東口)."""
    gris = c("metal")
    with b.group("Panneau"):
        b.box((-0.5, 0, -0.5), (0.5, 0.3, 0.5), c("beton_fonce"), name="Socle")
        b.cyl((0, 3.6, 0), 0.14, 7.2, gris, name="Mat")
        if variant % 3 == 0:
            # triangle inversé en trois marches de pixels, bord blanc
            rouge, blanc = c("feu_rouge"), c("blanc")
            b.box((-1.6, 6.7, -0.32), (1.6, 7.5, -0.14), blanc, collide=False, name="Bord")
            b.box((-1.4, 6.8, -0.36), (1.4, 7.4, -0.3), rouge, collide=False, name="Triangle")
            p = b.box((-1.0, 5.9, -0.36), (1.0, 6.8, -0.3), rouge, collide=False, name="Triangle")
            p.label = {"face": "Front", "text": "止まれ", "color": (250, 250, 250), "font": "sans"}
            b.box((-1.2, 5.8, -0.32), (1.2, 6.7, -0.14), blanc, collide=False, name="Bord")
            b.box((-0.5, 5.2, -0.36), (0.5, 5.9, -0.3), rouge, collide=False, name="Triangle")
            b.box((-0.7, 5.0, -0.32), (0.7, 5.8, -0.14), blanc, collide=False, name="Bord")
        elif variant % 3 == 1:
            b.cyl((0, 6.4, -0.25), 1.2, 0.16, c("blanc"), axis="z", collide=False, name="Bord")
            b.cyl((0, 6.4, -0.36), 1.05, 0.08, c("auvent_bleu"), axis="z", collide=False, name="Disque")
            b.box((-0.15, 5.7, -0.44), (0.15, 6.9, -0.38), c("blanc"), collide=False, shadow=False, name="Fleche")
            b.box((-0.45, 6.6, -0.44), (0.45, 6.9, -0.38), c("blanc"), collide=False, shadow=False, name="Fleche")
        else:
            p = b.box((-2.2, 5.4, -0.3), (2.2, 7.4, -0.14), c("auvent_bleu"), collide=False, name="Direction")
            p.label = {"face": "Front", "text": "駅 ←  → 東口", "color": (250, 250, 250), "font": "sans"}
            b.box((-2.3, 5.3, -0.26), (2.3, 7.5, -0.15), c("blanc"), collide=False, shadow=False, name="Cadre")
    return {"emprise": (1, 1), "hauteur": 7.5}


# ---------------------------------------------------------------------------
# Commerces de trottoir
# ---------------------------------------------------------------------------


def distributeurs(b, variant: int = 0, nombre: int = 2) -> dict:
    """Rangée de distributeurs de boissons éclairés (avant vers -Z), dos contre une façade.
    Chaque machine : 3,2 × 2,2 × 6,2 studs, vitrine éclairée avec deux rangées de boissons."""
    corps = ["distrib_rouge", "distrib_blanc", "distrib_bleu"]
    boissons = [c("boisson_1"), c("boisson_2"), c("boisson_3"), c("boisson_4")]
    W, D, H = 3.2, 2.2, 6.2
    x0 = -nombre * W / 2
    with b.group("Distributeurs"):
        b.box((x0 - 0.2, 0, -D / 2 - 0.2), (-x0 + 0.2, 0.3, D / 2), c("beton_fonce"), studs="top", name="Socle")
        for i in range(nombre):
            xa = x0 + i * W
            col = c(corps[(i + variant) % 3])
            b.box((xa + 0.05, 0.3, -D / 2), (xa + W - 0.05, H, D / 2), col, studs="top", name="Machine")
            b.box((xa + 0.3, 3.0, -D / 2 - 0.12), (xa + W - 0.3, 5.6, -D / 2), c("fenetre_froide"), material="Neon",
                  collide=False, shadow=False, name="Vitrine")
            for r, y in enumerate((3.35, 4.55)):
                b.box((xa + 0.5, y, -D / 2 - 0.22), (xa + W - 0.5, y + 0.75, -D / 2 - 0.12),
                      boissons[(i + r + variant) % 4], collide=False, shadow=False, name="Boissons")
            b.box((xa + 0.4, 1.0, -D / 2 - 0.15), (xa + W - 0.4, 1.7, -D / 2), c("noir"), collide=False, shadow=False, name="Trappe")
            b.box((xa + W - 1.0, 2.0, -D / 2 - 0.15), (xa + W - 0.45, 2.8, -D / 2), c("metal"), collide=False, shadow=False, name="Monnayeur")
            b.box((xa + 0.3, 5.75, -D / 2 - 0.1), (xa + W - 0.3, 6.05, -D / 2), shade(col, 0.8), collide=False, shadow=False, name="Bandeau")
    return {"emprise": (nombre * W + 0.4, D + 0.2), "hauteur": H}


def velos(b, variant: int = 0, nombre: int = 3) -> dict:
    """Vélos de ville garés le long d'une barre (alignés selon X, roues selon Z)."""
    cols = [c("velo_1"), c("velo_2"), c("velo_3"), c("metal_fonce")]
    with b.group("Velos"):
        L = nombre * 1.6 + 1
        b.box((-L / 2, 0, 1.3), (L / 2, 0.2, 1.7), c("metal_fonce"), name="Rail")
        for i in range(nombre):
            x = -L / 2 + 1.1 + i * 1.6
            col = cols[(i + variant) % 4]
            for z in (-1.3, 1.3):
                b.cyl((x, 1.1, z), 1.05, 0.2, c("pneu"), axis="x", collide=False, name="Roue")
            b.box((x - 0.1, 1.0, -1.3), (x + 0.1, 1.3, 1.3), col, collide=False, shadow=False, name="Cadre")
            b.box((x - 0.1, 1.2, 0.4), (x + 0.1, 2.5, 0.65), col, collide=False, shadow=False, name="TubeSelle")
            b.box((x - 0.25, 2.5, 0.2), (x + 0.25, 2.7, 0.9), c("noir"), collide=False, shadow=False, name="Selle")
            b.box((x - 0.55, 2.7, -1.2), (x + 0.55, 2.85, -1.0), c("metal"), collide=False, shadow=False, name="Guidon")
            b.box((x - 0.4, 1.9, -1.8), (x + 0.4, 2.5, -1.2), c("metal_clair"), collide=False, shadow=False, name="Panier")
    return {"emprise": (nombre * 1.6 + 1, 3.6), "hauteur": 2.9}


def poubelles_tri(b, variant: int = 0) -> dict:
    """Trois poubelles de tri (bleu, jaune, gris) avec couvercles et fentes."""
    cols = [c("auvent_bleu"), c("jaune"), c("metal")]
    with b.group("Poubelles"):
        for i in range(3):
            x = -2.2 + i * 2.2
            col = cols[(i + variant) % 3]
            b.box((x - 0.95, 0, -0.9), (x + 0.95, 3.0, 0.9), col, name="Poubelle")
            b.box((x - 1.05, 3.0, -1.0), (x + 1.05, 3.4, 1.0), shade(col, 0.8), studs="top", name="Couvercle")
            b.box((x - 0.5, 2.3, -0.98), (x + 0.5, 2.7, -0.9), c("noir"), collide=False, shadow=False, name="Fente")
    return {"emprise": (6.6, 2.0), "hauteur": 3.4}


def banc(b, variant: int = 0) -> dict:
    """Banc public en métal et lattes."""
    with b.group("Banc"):
        for x in (-2.4, 2.4):
            b.box((x - 0.2, 0, -0.9), (x + 0.2, 1.6, 0.9), c("metal_fonce"), name="Pied")
        b.box((-3, 1.6, -0.9), (3, 1.9, 0.9), shade(c("gris_chaud"), 0.85), studs="top", name="Assise")
        b.box((-3, 1.9, 0.6), (3, 3.4, 0.9), shade(c("gris_chaud"), 0.85), name="Dossier")
    return {"emprise": (6, 1.8), "hauteur": 3.4}


def arbre_rue(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Arbre d'alignement dans sa fosse carrée (grille), houppier en blocs étagés.
    variant 0 : zelkova vert ; 1 : zelkova haut ; 2 : ginkgo jaune."""
    rng = b.rng
    t = taille * (1.15 if variant % 3 == 1 else 1.0)
    vert = variant % 3 != 2
    tons = ([c("feuille_fonce"), c("feuille"), c("feuille_claire")] if vert else [c("ginkgo"), c("ginkgo_clair"), shade(c("ginkgo"), 0.9)])
    with b.group("Arbre"):
        b.box((-2, 0, -2), (2, 0.5, 2), c("beton"), studs="top", name="Fosse")
        b.box((-1.6, 0.5, -1.6), (1.6, 0.6, 1.6), c("metal_fonce"), collide=False, name="Grille")
        h = 7 * t
        b.box((-0.5, 0.6, -0.5), (0.5, h, 0.5), c("tronc"), name="Tronc")
        b.box((-0.3, h - 2.5, -0.3), (1.8, h - 1.9, 0.3), c("tronc"), collide=False, name="Branche")
        b.box((-1.8, h - 1.6, -0.3), (0.3, h - 1.0, 0.3), c("tronc"), collide=False, name="Branche")
        etages = [(4.2, 3.0), (5.0, 3.0), (3.8, 2.6), (2.2, 1.8)] if vert else [(3.4, 2.6), (3.0, 2.6), (2.2, 2.4), (1.2, 1.6)]
        y = h - 1.4
        for k, (r, hh) in enumerate(etages):
            r *= t
            dx, dz = float(rng.uniform(-0.4, 0.4)), float(rng.uniform(-0.4, 0.4))
            b.box((dx - r, y, dz - r), (dx + r, y + hh, dz + r), tons[(k + variant) % 3], studs="top", collide=False, name="Feuillage")
            y += hh
        # deux touffes latérales pour casser le cube
        for s in (-1, 1):
            r = 1.6 * t
            b.box((s * 3.6 * t - r, h + 0.6, -r), (s * 3.6 * t + r, h + 2.6, r), tons[1], studs="top", collide=False, name="Feuillage")
    return {"emprise": (4, 4), "hauteur": y}


def glissiere(b, longueur: float = 16, variant: int = 0) -> dict:
    """Garde-corps piéton blanc le long de X (poteaux tous les 4 studs, deux lisses tubulaires).
    variant 1 : lisses jaunes et poteaux gris (zone de travaux)."""
    n = max(2, int(round(longueur / 4)) + 1)
    blanc = c("rambarde") if variant % 2 == 0 else c("metal")
    lisse = c("rambarde") if variant % 2 == 0 else c("chantier_jaune")
    with b.group("Glissiere"):
        for i in range(n):
            x = -longueur / 2 + i * longueur / (n - 1)
            b.box((x - 0.18, 0, -0.18), (x + 0.18, 3.0, 0.18), blanc, name="Poteau")
        for y in (1.4, 2.8):
            b.cyl((0, y, 0), 0.16, longueur, lisse, axis="x", name="Lisse")
    return {"emprise": (longueur, 0.4), "hauteur": 3.0}


# ---------------------------------------------------------------------------
# Enseignes
# ---------------------------------------------------------------------------


def enseigne_verticale(b, texte: str = "カラオケ", variant: int = 0, couleur: str | None = None, hauteur: float | None = None,
                       profondeur: float = 2.6, epaisseur: float = 1.0) -> dict:
    """Enseigne verticale « en drapeau » fixée à une façade, lisible des deux sens de la rue.
    Origine : point de la façade au bas de l'enseigne ; l'enseigne dépasse vers -Z (de 0,3 à 0,3 + profondeur).
    Les deux grandes faces regardent ±X (le long de la rue) et portent le texte vertical.
    variant : 0 fond blanc et cadre néon ; 1 fond de couleur et texte blanc ; 2 fond sombre et texte néon."""
    n = max(1, len(texte))
    H = hauteur or (1.6 + 1.9 * n)
    neon = c(couleur) if couleur else c(("neon_magenta", "neon_cyan", "neon_jaune", "neon_orange", "neon_vert")[variant % 5])
    v = variant % 3
    fond = (c("enseigne_blanc"), shade(neon, 0.75), c("enseigne_noir"))[v]
    texte_col = ((40, 30, 40), (250, 250, 250), tuple(int(x) for x in neon))[v]
    z0, z1 = -0.3, -0.3 - profondeur
    e = epaisseur / 2
    with b.group("EnseigneVerticale"):
        for y in (0.6, H - 0.6):
            b.box((-0.15, y - 0.2, 0), (0.15, y + 0.2, z0), c("metal_fonce"), collide=False, shadow=False, name="Patte")
        corps = b.box((-e, 0, z1), (e, H, z0), fond, collide=False, name="Enseigne")
        corps.label = {"face": "Right", "text": texte, "color": texte_col, "font": "sans", "vertical": True,
                       **({"glow": 1.2} if v == 2 else {})}
        dos = b.box((-e - 0.1, 0.1, z1 + 0.1), (-e + 0.1, H - 0.1, z0 - 0.1), fond, collide=False, shadow=False, name="Dos")
        dos.label = {"face": "Left", "text": texte, "color": texte_col, "font": "sans", "vertical": True,
                     **({"glow": 1.2} if v == 2 else {})}
        # cadre néon (avant, haut, bas)
        b.box((-e - 0.1, -0.1, z1 - 0.2), (e + 0.1, H + 0.1, z1), neon, material="Neon", collide=False, shadow=False, name="Neon")
        b.box((-e - 0.1, H, z1), (e + 0.1, H + 0.2, z0), neon, material="Neon", collide=False, shadow=False, name="Neon")
        b.box((-e - 0.1, -0.2, z1), (e + 0.1, 0, z0), neon, material="Neon", collide=False, shadow=False, name="Neon")
    return {"emprise": (epaisseur, profondeur + 0.3), "hauteur": H}


# ---------------------------------------------------------------------------
# Zone de l'incident
# ---------------------------------------------------------------------------


def cones(b, variant: int = 0, nombre: int = 3) -> dict:
    """Cônes de signalisation rouge et blanc, alignés selon X ; variant 1 : reliés par une barre jaune et noire."""
    with b.group("Cones"):
        for i in range(nombre):
            x = (i - (nombre - 1) / 2) * 3.0
            b.box((x - 0.8, 0, -0.8), (x + 0.8, 0.25, 0.8), c("noir"), name="Base")
            b.cyl((x, 0.95, 0), 0.6, 1.4, c("feu_rouge"), name="Cone")
            b.cyl((x, 1.9, 0), 0.42, 0.5, c("blanc"), collide=False, name="Bande")
            b.cyl((x, 2.5, 0), 0.3, 0.7, c("feu_rouge"), collide=False, name="Pointe")
        if variant % 2 and nombre > 1:
            L = (nombre - 1) * 3.0
            for k in range(nombre - 1):
                for j in range(3):
                    xa = -L / 2 + k * 3.0 + j * 1.0
                    b.box((xa, 2.2, -0.12), (xa + 1.0, 2.5, 0.12), c("chantier_jaune" if j % 2 == 0 else "chantier_noir"),
                          collide=False, shadow=False, name="Barre")
    return {"emprise": (nombre * 3.0, 1.6), "hauteur": 2.9}


def barriere_chantier(b, longueur: float = 8, variant: int = 0, texte: str = "立入禁止") -> dict:
    """Barrière d'interdiction (le long de X) avec panneau 立入禁止.
    variant 0 : barrière à pieds en A, lisses rayées rouge et blanc, feu clignotant jaune ;
    variant 1 : poteaux et ruban jaune et noir tendu ; variant 2 : panneaux de clôture grillagés provisoires."""
    L = longueur
    v = variant % 3
    with b.group("Barriere"):
        if v == 0:
            for x in (-L / 2 + 0.4, L / 2 - 0.4):
                b.wedge((x - 0.2, 0, -1.0), (x + 0.2, 3.4, 0), c("metal"), down="-z", name="Pied")
                b.wedge((x - 0.2, 0, 0), (x + 0.2, 3.4, 1.0), c("metal"), down="+z", name="Pied")
            n = max(3, int(L // 1.6))
            for y in (2.0, 3.0):
                for k in range(n):
                    xa = -L / 2 + k * L / n
                    b.box((xa, y, -0.12), (xa + L / n, y + 0.6, 0.12), c("barriere_rouge" if (k + (y > 2.5)) % 2 == 0 else "barriere_blanc"),
                          name="Lisse")
            b.box((L / 2 - 0.9, 3.6, -0.3), (L / 2 - 0.3, 4.2, 0.3), c("feu_jaune"), material="Neon", collide=False, shadow=False, name="Clignotant")
            yp = 0.6
        elif v == 1:
            for x in (-L / 2 + 0.3, L / 2 - 0.3):
                b.box((x - 0.6, 0, -0.6), (x + 0.6, 0.5, 0.6), c("chantier_noir"), name="Lest")
                b.cyl((x, 2.0, 0), 0.22, 3.6, c("barriere_blanc"), name="Poteau")
                b.cyl((x, 3.2, 0), 0.24, 0.5, c("barriere_rouge"), collide=False, name="Bague")
            n = max(4, int(L // 1.2))
            for k in range(n):
                xa = -L / 2 + 0.3 + k * (L - 0.6) / n
                b.box((xa, 2.9, -0.04), (xa + (L - 0.6) / n, 3.4, 0.04), c("chantier_jaune" if k % 2 == 0 else "chantier_noir"),
                      collide=False, shadow=False, name="Ruban")
            yp = 1.0
        else:
            n = max(1, int(round(L / 4)))
            w = L / n
            for k in range(n):
                xa = -L / 2 + k * w
                b.box((xa, 0, -0.5), (xa + 0.5, 0.4, 0.5), c("chantier_noir"), name="Plot")
                b.box((xa + 0.1, 0.4, -0.1), (xa + 0.3, 5.0, 0.1), c("metal_clair"), name="Montant")
                b.box((xa + 0.3, 4.8, -0.1), (xa + w - 0.1, 5.0, 0.1), c("metal_clair"), name="Traverse")
                b.box((xa + 0.3, 0.8, -0.05), (xa + w - 0.1, 4.8, 0.05), c("metal"), transparency=0.55, name="Grillage")
            b.box((L / 2 - 0.2, 0, -0.5), (L / 2 + 0.3, 0.4, 0.5), c("chantier_noir"), name="Plot")
            b.box((L / 2 - 0.1, 0.4, -0.1), (L / 2 + 0.1, 5.0, 0.1), c("metal_clair"), name="Montant")
            yp = 1.8
        # panneau 立入禁止 (blanc, texte rouge), sur la face avant
        pw = min(3.2, L - 1.0)
        p = b.box((-pw / 2, yp, -0.32), (pw / 2, yp + 1.4, -0.14), c("barriere_blanc"), collide=False, shadow=False, name="Panneau")
        p.label = {"face": "Front", "text": texte, "color": (210, 40, 40), "font": "sans"}
    return {"emprise": (L, 2.0), "hauteur": 5.0 if v == 2 else 4.2}


# ---------------------------------------------------------------------------
# Planche d'aperçu
# ---------------------------------------------------------------------------


def planche(b, variant: int = 0) -> dict:
    """Tous les objets du module alignés, pour un seul rendu de contrôle (apercu.py assets.mobilier:planche)."""
    items = [
        (poteau_electrique, {"variant": variant}, 5),
        (feu_tricolore, {"variant": variant}, 7),
        (lampadaire, {"variant": variant}, 5),
        (panneau_route, {"variant": variant}, 5),
        (distributeurs, {"variant": variant, "nombre": 3}, 11),
        (velos, {"variant": variant}, 7),
        (poubelles_tri, {"variant": variant}, 8),
        (banc, {"variant": variant}, 7),
        (arbre_rue, {"variant": variant}, 11),
        (glissiere, {"variant": variant, "longueur": 12}, 13),
        (cones, {"variant": 1}, 10),
        (barriere_chantier, {"variant": variant}, 10),
        (barriere_chantier, {"variant": variant + 1}, 10),
        (barriere_chantier, {"variant": variant + 2}, 10),
    ]
    x = 0.0
    n = {}
    for fn, kw, w in items:
        n0 = len(b.parts)
        with b.at((x + w / 2, 0, 0)):
            fn(b, **kw)
        n[fn.__name__ + str(kw.get("variant", ""))] = len(b.parts) - n0
        x += w + 2
    with b.at((x + 2, 0, 0)):
        b.box((-3, 0, 0), (3, 14, 1), c("carrelage"), name="Mur")
        with b.at((-1, 2.5, 0)):
            n0 = len(b.parts)
            enseigne_verticale(b, "ラーメン", variant=variant)
            n["enseigne_verticale"] = len(b.parts) - n0
        clim(b, 1.6, 1.0, 0, sens="-z")
    return {"pieces_par_objet": n}
