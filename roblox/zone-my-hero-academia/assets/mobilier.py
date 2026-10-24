"""Mobilier de la zone My Hero Academia : ville moderne, campus et terrains d'entraînement.

Lampadaires (rue et campus), bancs, poubelles, distributeurs, feux tricolores, abribus, arbres de rue,
jardinières, bornes lumineuses, totems et panneaux de direction (textes génériques uniquement),
clôtures (grillage, verre, garde-corps), matériel d'entraînement (plots, pneus, haies d'athlétisme,
sac de frappe, caisses), bannières, guirlandes de fanions et terrasse de café.

Règles communes :
- l'avant de chaque objet regarde -Z local (le couloir une fois posé avec `face_couloir`) ;
- 40 pièces au plus par objet ; détails fins sans collision (`collide=False`) ;
- tout ce qui dépasse vers le couloir (crosses, bras de feux, bannières) reste à moins de 4,5 studs
  du pied : posé en |x| ≥ 38, rien ne franchit |x| = 33.
- textes : uniquement des mots génériques (CAMPUS, ACADÉMIE, ENTRAÎNEMENT, STADE, CAFÉ…), jamais de nom
  de la licence, de l'école ou des personnages (voir CONVENTIONS.md).

Aperçu de tout le module : `apercu.py assets.mobilier:planche`.
"""

from __future__ import annotations

import numpy as np

from kit import rot_y, rot_z, shade
from palette import c


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


def _label(p, texte: str, face: str = "Front", couleur=(255, 255, 255), fond=None, glow: float | None = None,
           font: str = "sans", vertical: bool = False) -> None:
    p.label = {"face": face, "text": texte, "color": couleur, "bg": fond, "font": font, "vertical": vertical}
    if glow:
        p.label["glow"] = glow


# ---------------------------------------------------------------------------
# Éclairage
# ---------------------------------------------------------------------------

def lampadaire_ville(b, variant: int = 0, hauteur: float = 13.0) -> dict:
    """Lampadaire de rue moderne : socle, mât, crosse vers l'avant (-Z local, côté couloir), tête à LED.
    La tête s'avance de 3,4 studs : posé en |x| = 38, elle s'arrête en |x| = 34,6.
    variant 0 acier, 1 blanc, 2 bleu nuit (bague violette)."""
    mat = (c("acier"), c("blanc"), c("marine"))[variant % 3]
    h = hauteur
    with b.group("Lampadaire"):
        b.box((-0.7, 0, -0.7), (0.7, 0.6, 0.7), c("beton_fonce"), studs="top", name="Socle")
        b.cyl((0, 0.6 + 0.9, 0), 0.45, 1.8, mat, name="Pied")
        b.cyl((0, 0.6 + (h - 0.6) / 2, 0), 0.3, h - 0.6, mat, name="Mat")
        b.cyl((0, 3.2, 0), 0.38, 0.3, c("violet") if variant % 3 == 2 else shade(mat, 0.85), collide=False, name="Bague")
        b.box((-0.2, h - 0.6, -2.6), (0.2, h - 0.2, 0.25), mat, collide=False, name="Crosse")
        b.box((-0.55, h - 0.9, -3.4), (0.55, h - 0.3, -1.8), mat, collide=False, name="Tete")
        b.box((-0.45, h - 1.05, -3.3), (0.45, h - 0.9, -1.9), c("led"), material="Neon", collide=False, shadow=False, name="LED")
    return {"emprise": (1.4, 4.1), "hauteur": h}


def lampadaire_campus(b, variant: int = 0, hauteur: float = 11.0) -> dict:
    """Lampadaire du campus : poteau carré blanc à bande lumineuse cyan sur l'avant, tête plate à LED.
    variant 0 tête simple vers l'avant, 1 double tête en T (le long de X), 2 colonne à lanterne lavande."""
    h = hauteur
    with b.group("LampadaireCampus"):
        b.box((-0.8, 0, -0.8), (0.8, 0.5, 0.8), c("beton"), studs="top", name="Socle")
        b.box((-0.4, 0.5, -0.4), (0.4, h, 0.4), c("blanc"), name="Poteau")
        b.box((-0.15, 1.2, -0.5), (0.15, h - 1.6, -0.4), c("neon_cyan"), material="Neon", collide=False, shadow=False, name="BandeLumineuse")
        v = variant % 3
        if v == 0:
            b.box((-0.7, h, -2.2), (0.7, h + 0.45, 0.6), c("blanc"), studs="top", collide=False, name="Tete")
            b.box((-0.5, h - 0.15, -2.0), (0.5, h, -0.6), c("led"), material="Neon", collide=False, shadow=False, name="LED")
        elif v == 1:
            b.box((-2.6, h, -0.6), (2.6, h + 0.45, 0.6), c("blanc"), studs="top", collide=False, name="Tete")
            for sx in (-1, 1):
                b.box((sx * 2.4 - 0.7 * sx, h - 0.15, -0.45), (sx * 2.4, h, 0.45), c("led"), material="Neon",
                      collide=False, shadow=False, name="LED")
        else:
            b.box((-0.75, h, -0.75), (0.75, h + 1.6, 0.75), c("lavande_pale"), material="Neon", collide=False, shadow=False, name="Lanterne")
            b.box((-0.95, h + 1.6, -0.95), (0.95, h + 1.95, 0.95), c("blanc"), studs="top", collide=False, name="Chapeau")
            b.box((-0.25, h + 1.95, -0.25), (0.25, h + 2.4, 0.25), c("violet"), collide=False, name="Pointe")
    return {"emprise": (1.6, 2.8), "hauteur": h + (2.4 if variant % 3 == 2 else 0.45)}


def borne_lumineuse(b, variant: int = 0) -> dict:
    """Borne basse lumineuse (bord d'allée, parvis) : fût, anneau Neon, chapeau. 4 pièces."""
    fut = (c("blanc"), c("acier"), c("marine"))[variant % 3]
    anneau = (c("neon_cyan"), c("neon_blanc"), c("neon_violet"))[variant % 3]
    with b.group("Borne"):
        b.box((-0.6, 0, -0.6), (0.6, 0.2, 0.6), c("beton_fonce"), name="Pied")
        b.cyl((0, 1.1, 0), 0.42, 1.8, fut, name="Fut")
        b.cyl((0, 1.55, 0), 0.47, 0.35, anneau, material="Neon", collide=False, shadow=False, name="Anneau")
        b.cyl((0, 2.1, 0), 0.5, 0.2, shade(fut, 0.85), collide=False, name="Chapeau")
    return {"emprise": (1.2, 1.2), "hauteur": 2.2}


# ---------------------------------------------------------------------------
# Assises, propreté, distributeurs
# ---------------------------------------------------------------------------

def banc(b, variant: int = 0, longueur: float = 6.0) -> dict:
    """Banc moderne, assise tournée vers -Z (le couloir).
    variant 0 bloc de béton blanc et lattes de bois ; 1 pieds d'acier, lattes et dossier ; 2 béton et coussin violet."""
    w = longueur / 2
    v = variant % 3
    with b.group("Banc"):
        if v == 0:
            b.box((-w, 0, -0.9), (w, 1.5, 0.9), c("beton_clair"), name="Bloc")
            for i in range(3):
                z0 = -0.85 + i * 0.6
                b.box((-w - 0.1, 1.5, z0), (w + 0.1, 1.8, z0 + 0.5), c("bois_clair") if i % 2 else c("bois"),
                      studs="top", name="Latte")
        elif v == 1:
            for x in (-w + 0.6, w - 0.6):
                b.box((x - 0.2, 0, -0.9), (x + 0.2, 1.5, 0.9), c("acier_fonce"), name="Pied")
                b.box((x - 0.2, 1.5, 0.6), (x + 0.2, 3.4, 0.9), c("acier_fonce"), name="Montant")
            b.box((-w, 1.5, -1.0), (w, 1.8, 0.6), c("bois"), studs="top", name="Assise")
            b.box((-w, 2.2, 0.9), (w, 3.2, 1.2), c("bois_clair"), name="Dossier")
        else:
            b.box((-w, 0, -1.0), (w, 1.3, 1.0), c("blanc"), name="Bloc")
            b.box((-w + 0.3, 1.3, -0.8), (w - 0.3, 1.7, 0.8), c("violet"), studs="top", name="Coussin")
            b.box((-w - 0.1, 0.3, -1.1), (w + 0.1, 0.5, 1.1), c("neon_cyan"), material="Neon", collide=False, shadow=False,
                  name="Liseré")
    return {"emprise": (longueur + 0.2, 2.4), "hauteur": 3.4 if v == 1 else 1.8}


def poubelle(b, variant: int = 0) -> dict:
    """Deux poubelles de tri jumelles, corps blanc et couvercles de couleur."""
    cols = [(c("bleu_vif"), c("jaune")), (c("violet"), c("orange")), (c("acier_fonce"), c("robot_bleu"))][variant % 3]
    with b.group("Poubelles"):
        b.box((-1.7, 0, -0.7), (1.7, 0.2, 0.7), c("beton_fonce"), name="Dalle")
        for i, x in enumerate((-0.85, 0.85)):
            b.box((x - 0.75, 0.2, -0.6), (x + 0.75, 2.6, 0.6), c("blanc_casse"), name="Corps")
            b.box((x - 0.8, 2.6, -0.65), (x + 0.8, 2.9, 0.65), cols[i], studs="top", name="Couvercle")
            b.box((x - 0.4, 2.0, -0.7), (x + 0.4, 2.3, -0.6), c("noir"), collide=False, name="Fente")
    return {"emprise": (3.4, 1.4), "hauteur": 2.9}


def distributeur(b, variant: int = 0, nombre: int = 2) -> dict:
    """Rangée de distributeurs de boissons éclairés (avant vers -Z), dos contre une façade. 6 pièces chacun."""
    corps = [c("blanc"), c("bleu_vif"), c("rouge"), c("violet")]
    w = 2.6
    x0 = -nombre * w / 2
    with b.group("Distributeurs"):
        for i in range(nombre):
            x = x0 + i * w + w / 2
            col = corps[(i + variant) % len(corps)]
            b.box((x - 1.25, 0, -1.0), (x + 1.25, 6.0, 1.0), col, name="Corps")
            b.box((x - 1.0, 3.0, -1.1), (x + 1.0, 5.6, -1.0), c("vitre_claire"), material="Neon", collide=False, shadow=False,
                  name="Vitrine")
            for k in range(2):
                b.box((x - 0.9, 3.4 + k * 1.1, -1.2), (x + 0.9, 3.9 + k * 1.1, -1.1), corps[(i + k + 2) % 4],
                      collide=False, shadow=False, name="Canettes")
            b.box((x - 0.8, 0.6, -1.15), (x + 0.8, 1.4, -1.0), c("noir"), collide=False, name="Trappe")
            b.box((x - 1.35, 6.0, -1.1), (x + 1.35, 6.3, 1.1), shade(col, 0.85), studs="top", name="Chapeau")
    return {"emprise": (nombre * w, 2.2), "hauteur": 6.3}


# ---------------------------------------------------------------------------
# Rue : feux, abribus, arbres, jardinières
# ---------------------------------------------------------------------------

def feu_tricolore(b, variant: int = 0, hauteur: float = 12.0, bras: float = 4.5) -> dict:
    """Feu tricolore : mât, potence vers l'avant (-Z local, côté couloir) de `bras` studs, boîtier horizontal
    à trois feux sur ses deux faces (le long de la rue), feu piéton sur le mât.
    Posé en |x| = 38,5 avec bras = 4,5 : le boîtier s'arrête en |x| = 33,5."""
    mat = (c("acier"), c("blanc"))[variant % 2]
    h = hauteur
    allume = (0, 2)[variant % 2]          # 0 vert-bleu, 2 rouge
    lampes = (c("neon_cyan"), c("jaune"), c("rouge"))
    with b.group("Feu"):
        b.box((-0.7, 0, -0.7), (0.7, 0.4, 0.7), c("beton_fonce"), name="Socle")
        b.cyl((0, 0.4 + (h - 0.4) / 2, 0), 0.3, h - 0.4, mat, name="Mat")
        b.box((-0.2, h - 1.4, -bras + 0.6), (0.2, h - 1.0, 0.2), mat, collide=False, name="Potence")
        # boîtier : long selon Z (en travers de la rue), feux sur les faces ±X (vers la circulation)
        zb0, zb1 = -bras - 0.1, -bras + 3.5
        b.box((-0.45, h - 2.0, zb0), (0.45, h - 0.6, zb1), c("noir"), collide=False, name="Boitier")
        for sx in (-1, 1):
            for k in range(3):
                zc = zb0 + 0.65 + k * 1.1
                col = lampes[k]
                lit = k == allume
                b.box((sx * 0.45, h - 1.7, zc - 0.4), (sx * 0.55, h - 0.9, zc + 0.4), col if lit else shade(col, 0.45),
                      material="Neon" if lit else "SmoothPlastic", collide=False, shadow=False, name="Lampe")
        # feu piéton
        b.box((-0.5, 6.0, -0.75), (0.5, 8.0, -0.3), c("noir"), collide=False, name="FeuPieton")
        b.box((-0.35, 7.1, -0.85), (0.35, 7.8, -0.75), c("rouge"), material="Neon", collide=False, shadow=False, name="Pieton")
        b.box((-0.35, 6.2, -0.85), (0.35, 6.9, -0.75), shade(c("neon_cyan"), 0.45), collide=False, shadow=False, name="Pieton")
    return {"emprise": (1.4, bras + 1), "hauteur": h}


def abribus(b, variant: int = 0, longueur: float = 10.0) -> dict:
    """Abribus vitré ouvert vers -Z : dalle, trois poteaux, paroi de verre, toit blanc à liseré lumineux,
    banc, plan du quartier (aplats colorés, sans texte) et poteau d'arrêt à disque bleu."""
    w = longueur / 2
    toit = (c("blanc"), c("facade_ciel"), c("lavande_pale"))[variant % 3]
    with b.group("Abribus"):
        b.box((-w, 0, -1.8), (w, 0.3, 1.8), c("dalle_claire"), studs="top", name="Dalle")
        for x in (-w + 0.3, 0, w - 0.3):
            b.box((x - 0.2, 0.3, 1.1), (x + 0.2, 6.6, 1.5), c("acier"), name="Poteau")
        b.box((-w + 0.5, 0.9, 1.15), (w - 0.5, 6.0, 1.35), c("vitre_claire"), material="Glass", transparency=0.45,
              collide=False, name="Paroi")
        b.box((-w - 0.3, 6.6, -2.2), (w + 0.3, 7.1, 1.8), toit, studs="top", name="Toit")
        b.box((-w - 0.3, 6.45, -2.3), (w + 0.3, 6.6, -2.0), c("neon_cyan"), material="Neon", collide=False, shadow=False,
              name="Liseré")
        b.box((-w + 1.2, 0.3, 0.3), (-0.4, 1.6, 1.0), c("acier_fonce"), name="Banc")
        b.box((-w + 1.2, 1.6, 0.2), (-0.4, 1.8, 1.05), c("bois"), studs="top", name="Assise")
        # plan du quartier sur la paroi de droite
        b.box((1.0, 1.4, 1.0), (w - 1.0, 5.0, 1.1), c("blanc"), collide=False, name="Plan")
        b.box((1.4, 2.0, 0.95), (2.8, 3.4, 1.0), c("herbe_claire"), collide=False, shadow=False, name="PlanParc")
        b.box((2.9, 3.0, 0.95), (w - 1.4, 4.4, 1.0), c("facade_ciel_fonce"), collide=False, shadow=False, name="PlanQuartier")
        b.box((1.4, 3.6, 0.95), (2.8, 4.4, 1.0), c("violet"), collide=False, shadow=False, name="PlanCampus")
        # poteau d'arrêt
        xp = w + 1.0
        b.box((xp - 0.5, 0, -1.2), (xp + 0.5, 0.3, -0.2), c("beton_fonce"), name="PiedArret")
        b.cyl((xp, 4.0, -0.7), 0.15, 7.4, c("acier"), name="PoteauArret")
        b.cyl((xp, 7.3, -0.7), 1.0, 0.2, c("bleu_vif"), axis="z", collide=False, name="Disque")
        b.cyl((xp, 7.3, -0.7), 0.6, 0.3, c("blanc"), axis="z", collide=False, name="DisqueCentre")
    return {"emprise": (longueur + 3, 4.1), "hauteur": 8.3}


def arbre_rue(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Arbre d'alignement dans sa fosse carrée à grille ; houppier arrondi en trois blocs étagés.
    variant 0 vert, 1 vert clair, 2 cerisier rose (accent, avec parcimonie)."""
    t = taille
    v = variant % 3
    tons = [(c("feuille"), c("feuille_claire"), c("feuille_fonce")),
            (c("feuille_claire"), c("feuille_pale"), c("feuille")),
            (c("fleur_rose"), shade(c("fleur_rose"), 1.25), shade(c("fleur_rose"), 0.85))][v]
    with b.group("ArbreRue"):
        b.box((-1.5, 0, -1.5), (1.5, 0.2, 1.5), c("acier_fonce"), studs="top", name="Grille")
        b.box((-1.0, 0.2, -1.0), (1.0, 0.3, 1.0), c("terre_fonce"), name="Terre")
        tr = 0.45 * t
        b.box((-tr, 0.2, -tr), (tr, 6.0 * t, tr), c("tronc"), name="Tronc")
        y = 4.5 * t
        b.box((-2.6 * t, y, -2.6 * t), (2.6 * t, y + 2.6 * t, 2.6 * t), tons[2], studs="top", collide=False, name="Feuillage")
        b.box((-3.2 * t, y + 1.2 * t, -2.0 * t), (3.2 * t, y + 3.6 * t, 2.0 * t), tons[0], studs="top", collide=False, name="Feuillage")
        b.box((-2.0 * t, y + 1.2 * t, -3.2 * t), (2.0 * t, y + 3.6 * t, 3.2 * t), tons[0], studs="top", collide=False, name="Feuillage")
        b.box((-1.8 * t, y + 3.6 * t, -1.8 * t), (1.8 * t, y + 4.8 * t, 1.8 * t), tons[1], studs="top", collide=False, name="Feuillage")
    return {"emprise": (6.4 * t, 6.4 * t), "hauteur": y + 4.8 * t}


def jardiniere(b, variant: int = 0, longueur: float = 6.0) -> dict:
    """Jardinière de béton blanc garnie d'arbustes taillés et de fleurs (rose, blanc, jaune ou violet)."""
    w = longueur / 2
    fleurs = [c("fleur_rose"), c("fleur_blanche"), c("fleur_jaune"), c("fleur_violette")]
    with b.group("Jardiniere"):
        b.box((-w, 0, -1.0), (w, 1.6, 1.0), c("blanc_casse"), name="Bac")
        b.box((-w - 0.1, 1.4, -1.1), (w + 0.1, 1.7, 1.1), c("beton"), studs="top", name="Margelle")
        b.box((-w + 0.4, 1.7, -0.7), (w - 0.4, 2.9, 0.7), c("haie"), studs="top", collide=False, name="Arbuste")
        n = max(2, int(longueur // 2))
        for i in range(n):
            x = -w + 0.9 + i * (longueur - 1.8) / max(1, n - 1)
            col = fleurs[(i + variant) % len(fleurs)]
            b.box((x - 0.45, 2.9, -0.45), (x + 0.45, 3.4, 0.45), col, collide=False, shadow=False, name="Fleurs")
    return {"emprise": (longueur + 0.2, 2.2), "hauteur": 3.4}


def terrasse(b, variant: int = 0) -> dict:
    """Terrasse de café : deux tables rondes, quatre chaises, un parasol (devant une façade, vers -Z)."""
    toile = (c("store_rouge"), c("violet"), c("store_bleu"))[variant % 3]
    with b.group("Terrasse"):
        for i, x in enumerate((-2.6, 2.6)):
            b.cyl((x, 0.1, 0), 0.8, 0.2, c("acier_fonce"), name="PiedTable")
            b.cyl((x, 1.4, 0), 0.18, 2.4, c("acier_fonce"), name="Fut")
            b.cyl((x, 2.7, 0), 1.2, 0.2, c("blanc"), studs="top", name="Plateau")
            for sz in (-1, 1):
                b.box((x - 0.6, 0, sz * 1.9 - 0.6), (x + 0.6, 1.4, sz * 1.9 + 0.6), c("bois"), name="Chaise")
                b.box((x - 0.6, 1.4, sz * 2.4 - 0.1), (x + 0.6, 2.8, sz * 2.4 + 0.1), c("bois_fonce"), collide=False, name="Dossier")
        b.cyl((0, 3.5, 0), 0.15, 7.0, c("blanc"), collide=False, name="Manche")
        b.box((-3.6, 6.4, -3.6), (3.6, 6.8, 3.6), toile, collide=False, name="Toile")
        b.box((-2.4, 6.8, -2.4), (2.4, 7.3, 2.4), toile, collide=False, name="Toile")
        b.box((-3.7, 6.2, -3.7), (3.7, 6.4, 3.7), c("blanc"), collide=False, shadow=False, name="Frange")
        b.box((-0.3, 7.3, -0.3), (0.3, 7.7, 0.3), c("blanc"), collide=False, name="Pointe")
    return {"emprise": (7.4, 7.4), "hauteur": 7.7}


# ---------------------------------------------------------------------------
# Signalétique (textes génériques seulement)
# ---------------------------------------------------------------------------

def totem(b, texte: str = "CAMPUS", variant: int = 0, hauteur: float = 8.0) -> dict:
    """Totem de signalétique : stèle blanche, bandeau de couleur avec le texte sur les deux faces (lumineux),
    bande Neon cyan sur la tranche. Textes autorisés : CAMPUS, ACADÉMIE, ENTRAÎNEMENT, STADE, CAFÉ…"""
    w = float(max(3, round(0.62 * len(texte) + 1.4)))
    h = hauteur
    bande = (c("violet"), c("marine"), c("orange"))[variant % 3]
    with b.group("Totem"):
        b.box((-w / 2 - 0.4, 0, -1.0), (w / 2 + 0.4, 0.6, 1.0), c("beton_fonce"), studs="top", name="Socle")
        b.box((-w / 2, 0.6, -0.5), (w / 2, h, 0.5), c("blanc"), studs="top", name="Stele")
        b.box((-w / 2 - 0.1, h - 3.4, -0.6), (w / 2 + 0.1, h - 0.8, 0.6), bande, name="Bandeau")
        for face, z0, z1 in (("Front", -0.7, -0.6), ("Back", 0.6, 0.7)):
            p = b.box((-w / 2 + 0.2, h - 3.2, z0), (w / 2 - 0.2, h - 1.0, z1), bande, collide=False, shadow=False, name="Texte")
            _label(p, texte, face=face, couleur=(255, 255, 255), glow=1.0)
        for sx in (-1, 1):
            b.box((sx * (w / 2) - 0.15, 1.0, -0.2), (sx * (w / 2) + 0.15, h - 3.6, 0.2), c("neon_cyan"), material="Neon",
                  collide=False, shadow=False, name="Bande")
        b.box((-w / 2 + 0.6, 1.4, -0.6), (w / 2 - 0.6, 1.8, -0.5), bande, collide=False, name="Filet")
    return {"emprise": (w + 0.8, 2.0), "hauteur": h}


def panneau_direction(b, variant: int = 0, textes=("STADE", "CAMPUS")) -> dict:
    """Poteau de direction à lames pointues (alternativement vers +X et -X), texte sur les deux faces."""
    mat = (c("blanc"), c("acier"))[variant % 2]
    lame = (c("marine"), c("violet"))[variant % 2]
    n = len(textes)
    h = 4.6 + 1.5 * n
    with b.group("Direction"):
        b.box((-0.7, 0, -0.7), (0.7, 0.4, 0.7), c("beton_fonce"), name="Socle")
        b.box((-0.25, 0.4, -0.25), (0.25, h, 0.25), mat, name="Poteau")
        b.box((-0.4, h, -0.4), (0.4, h + 0.3, 0.4), c("violet"), collide=False, name="Chapeau")
        for i, texte in enumerate(textes):
            s = 1 if i % 2 == 0 else -1
            L = 0.55 * len(texte) + 1.6
            y0 = h - 1.6 - i * 1.5
            xa, xb = sorted((s * 0.3, s * (0.3 + L)))
            for face, z0, z1 in (("Front", -0.35, -0.25), ("Back", 0.25, 0.35)):
                p = b.box((xa, y0, z0), (xb, y0 + 1.1, z1), lame, collide=False, shadow=False, name="Lame")
                _label(p, texte, face=face, couleur=(255, 255, 255))
            b.box((xa, y0, -0.25), (xb, y0 + 1.1, 0.25), lame, collide=False, name="LameCoeur")
            # pointe (coin) au bout de la lame
            xt = s * (0.3 + L)
            ta, tb = sorted((xt, xt + s * 0.8))
            b.wedge((ta, y0, -0.35), (tb, y0 + 0.55, 0.35), lame, down="+x" if s > 0 else "-x", collide=False, name="Pointe")
            b.wedge_under((ta, y0 + 0.55, -0.35), (tb, y0 + 1.1, 0.35), lame, down="+x" if s > 0 else "-x", collide=False, name="Pointe")
    return {"emprise": (2 * (0.55 * max(len(t) for t in textes) + 2.7), 1.4), "hauteur": h + 0.3}


# ---------------------------------------------------------------------------
# Clôtures
# ---------------------------------------------------------------------------

def cloture(b, longueur: float = 12.0, variant: int = 0, hauteur: float | None = None) -> dict:
    """Clôture le long de X local (centrée sur l'origine).
    variant 0 grillage des terrains d'entraînement (poteaux gris, panneau grillagé translucide, lisse haute
    jaune) ; 1 garde-corps de verre à main courante blanche ; 2 barrière basse blanche à deux lisses."""
    v = variant % 3
    h = hauteur or (6.0, 3.2, 2.6)[v]
    L = longueur
    n = max(2, int(round(L / 4)) + 1)
    with b.group("Cloture"):
        for i in range(n):
            x = -L / 2 + i * L / (n - 1)
            x = min(max(x, -L / 2 + 0.2), L / 2 - 0.2)
            col = (c("acier_fonce"), c("acier"), c("blanc"))[v]
            b.box((x - 0.2, 0, -0.2), (x + 0.2, h, 0.2), col, name="Poteau")
        if v == 0:
            b.box((-L / 2, 0.3, -0.05), (L / 2, h - 0.4, 0.05), c("acier"), transparency=0.55, collide=True, name="Grillage")
            b.box((-L / 2, h - 0.4, -0.15), (L / 2, h - 0.1, 0.15), c("danger_jaune"), collide=False, name="Lisse")
            b.box((-L / 2, 0.0, -0.12), (L / 2, 0.3, 0.12), c("acier_fonce"), name="Lisse")
        elif v == 1:
            b.box((-L / 2 + 0.2, 0.3, -0.06), (L / 2 - 0.2, h - 0.4, 0.06), c("vitre_claire"), material="Glass", transparency=0.5,
                  name="Verre")
            b.box((-L / 2, h - 0.1, -0.3), (L / 2, h + 0.2, 0.3), c("blanc"), studs="top", name="MainCourante")
            b.box((-L / 2, 0.0, -0.15), (L / 2, 0.3, 0.15), c("acier"), name="Lisse")
        else:
            for y in (h * 0.45, h - 0.3):
                b.box((-L / 2, y - 0.15, -0.15), (L / 2, y + 0.15, 0.15), c("blanc"), name="Lisse")
    return {"emprise": (L, 0.6), "hauteur": h}


# ---------------------------------------------------------------------------
# Matériel d'entraînement
# ---------------------------------------------------------------------------

def plots(b, variant: int = 0, nombre: int = 4) -> dict:
    """Plots d'entraînement orange à bande blanche, alignés selon X (3 pièces chacun)."""
    col = (c("orange"), c("danger_jaune"), c("rouge"))[variant % 3]
    with b.group("Plots"):
        for i in range(nombre):
            x = (i - (nombre - 1) / 2) * 2.2
            b.box((x - 0.6, 0, -0.6), (x + 0.6, 0.2, 0.6), col, name="Base")
            b.cyl((x, 0.95, 0), 0.4, 1.5, col, collide=False, name="Cone")
            b.cyl((x, 1.1, 0), 0.45, 0.35, c("blanc"), collide=False, shadow=False, name="Bande")
    return {"emprise": (nombre * 2.2, 1.2), "hauteur": 1.7}


def pneus(b, variant: int = 0) -> dict:
    """Pneus d'entraînement : deux posés à plat et un empilé (ou une ligne de trois en variante 1)."""
    pos = [((-1.2, 0, 0), (1.2, 0, 0), (0, 0.8, 0)), ((-2.5, 0, 0), (0, 0, 0), (2.5, 0, 0)), ((0, 0, 0), (0, 0.8, 0), (0, 1.6, 0))][variant % 3]
    with b.group("Pneus"):
        for (x, y, z) in pos:
            b.cyl((x, y + 0.4, z), 1.15, 0.8, c("pneu"), name="Pneu")
            b.cyl((x, y + 0.4, z), 0.55, 1.0, c("gris_acier"), collide=False, name="Jante")
    return {"emprise": (5.0, 2.4), "hauteur": 2.4}


def haies_athletisme(b, variant: int = 0, nombre: int = 3) -> dict:
    """Haies d'athlétisme alignées selon Z (barre selon X), barres blanches à bandes noires. 6 pièces chacune."""
    with b.group("Haies"):
        for i in range(nombre):
            z = (i - (nombre - 1) / 2) * 3.0
            for x in (-1.6, 1.6):
                b.box((x - 0.15, 0, z - 0.6), (x + 0.15, 0.2, z + 0.6), c("acier_fonce"), name="Pied")
                b.box((x - 0.12, 0.2, z - 0.12), (x + 0.12, 2.6, z + 0.12), c("acier"), name="Montant")
            b.box((-1.75, 2.0, z - 0.1), (1.75, 2.7, z + 0.1), c("blanc"), collide=False, name="Barre")
            b.box((-0.4, 1.95, z - 0.15), (0.4, 2.75, z + 0.15), c("noir") if variant % 2 == 0 else c("violet"),
                  collide=False, shadow=False, name="Bande")
    return {"emprise": (3.5, nombre * 3.0), "hauteur": 2.75}


def sac_frappe(b, variant: int = 0) -> dict:
    """Sac de frappe suspendu à un portique d'acier (portique le long de X)."""
    portique = (c("acier_fonce"), c("robot_orange"), c("marine"))[variant % 3]
    sac = (c("rouge"), c("bleu_vif"), c("noir"))[variant % 3]
    with b.group("SacFrappe"):
        for x in (-2.2, 2.2):
            b.box((x - 0.8, 0, -0.8), (x + 0.8, 0.3, 0.8), c("beton_fonce"), name="Platine")
            b.box((x - 0.2, 0.3, -0.2), (x + 0.2, 7.2, 0.2), portique, name="Montant")
        b.box((-2.4, 7.2, -0.25), (2.4, 7.7, 0.25), portique, studs="top", name="Traverse")
        b.box((-0.06, 5.4, -0.06), (0.06, 7.2, 0.06), c("gris_acier"), collide=False, shadow=False, name="Chaine")
        b.cyl((0, 3.8, 0), 0.75, 3.2, sac, name="Sac")
        b.cyl((0, 3.0, 0), 0.8, 0.3, c("blanc"), collide=False, shadow=False, name="Bande")
        b.cyl((0, 5.45, 0), 0.5, 0.1, shade(sac, 0.7), collide=False, name="Haut")
    return {"emprise": (6.0, 1.6), "hauteur": 7.7}


def caisses(b, variant: int = 0) -> dict:
    """Caisses de matériel bleues ou grises cerclées d'une bande jaune (studs sur le dessus)."""
    rng = b.rng
    pile = [((-1.3, 0, 0), 2.4), ((1.3, 0, 0.2), 2.2), ((-0.4, 2.4, 0.1), 2.0)][: 2 + variant % 2]
    corps = (c("robot_bleu"), c("robot_gris"), c("marine_clair"))[variant % 3]
    with b.group("Caisses"):
        for (x, y, z), s in pile:
            yaw = float(rng.uniform(-10, 10))
            b.boxc((x, y + s / 2, z), (s, s, s), corps, yaw=yaw, studs="top", name="Caisse")
            b.boxc((x, y + s * 0.62, z), (s + 0.2, s * 0.18, s + 0.2), c("danger_jaune"), yaw=yaw, collide=False, name="Bande")
    return {"emprise": (5.2, 3.0), "hauteur": 4.4 if variant % 2 else 2.4}


# ---------------------------------------------------------------------------
# Fête du stade : bannières et fanions
# ---------------------------------------------------------------------------

BANNIERES = [("violet", "blanc"), ("lavande", "violet"), ("orange_couchant", "blanc"), ("bleu_vif", "blanc")]


def banniere(b, variant: int = 0, hauteur: float = 11.0) -> dict:
    """Mât à bannière verticale : le tissu part du mât vers l'avant (-Z local, côté couloir) sur 2,6 studs.
    Motifs abstraits (bandes, chevron), jamais d'emblème."""
    fond, bande = (c(n) for n in BANNIERES[variant % len(BANNIERES)])
    h = hauteur
    with b.group("Banniere"):
        b.box((-0.7, 0, -0.7), (0.7, 0.4, 0.7), c("beton_fonce"), name="Socle")
        b.cyl((0, 0.4 + (h - 0.4) / 2, 0), 0.22, h - 0.4, c("acier"), name="Mat")
        b.ball((0, h + 0.25, 0), 0.4, c("blanc"), collide=False, name="Boule")
        for y in (h - 0.6, h - 6.2):
            b.box((-0.1, y - 0.15, -2.9), (0.1, y + 0.15, 0.0), c("acier"), collide=False, name="Bras")
        b.box((-0.08, h - 6.4, -2.8), (0.08, h - 0.6, -0.3), fond, collide=False, shadow=False, name="Tissu")
        b.box((-0.18, h - 3.8, -2.8), (0.18, h - 3.0, -0.3), bande, collide=False, shadow=False, name="Bande")
        b.box((-0.18, h - 2.2, -2.8), (0.18, h - 1.9, -0.3), bande, collide=False, shadow=False, name="Filet")
        b.box((-0.18, h - 6.4, -2.8), (0.18, h - 6.0, -0.3), c("orange") if variant % 2 else c("lavande"),
              collide=False, shadow=False, name="Ourlet")
    return {"emprise": (1.4, 3.2), "hauteur": h + 0.65}


def guirlande_fanions(b, p0, p1, n: int = 10, creux: float = 1.5, variant: int = 0) -> dict:
    """Guirlande de fanions triangulaires entre deux points (coordonnées du repère courant).
    Chaque fanion = deux coins dos à dos (triangle pointe en bas). Au-dessus du couloir : fil et fanions
    entièrement au-dessus de 30 studs."""
    palettes = [("violet", "blanc", "orange_couchant", "lavande"), ("bleu_vif", "jaune", "blanc", "rouge"),
                ("lavande", "violet", "blanc", "neon_cyan")]
    cols = [c(k) for k in palettes[variant % len(palettes)]]
    pts = _chainette(p0, p1, creux, 10)
    p0a, p1a = np.asarray(p0, float), np.asarray(p1, float)
    d = p1a - p0a
    dh = np.array([d[0], 0.0, d[2]])
    dh = dh / (np.linalg.norm(dh) or 1)
    up = np.array([0.0, 1.0, 0.0])
    nx = np.cross(up, dh)
    F = np.column_stack([nx, up, dh])          # X local = normale, Y = haut, Z = le long du fil
    w, hf = 1.4, 1.8
    with b.group("Fanions"):
        for a, bb in zip(pts, pts[1:]):
            _segment(b, a, bb, 0.07, c("blanc"), name="Fil")
        for i in range(n):
            t = (i + 0.5) / n
            p = p0a + d * t
            y = p[1] - creux * 4 * t * (1 - t) - 0.1
            col = cols[i % len(cols)]
            # moitié gauche (angle droit en haut, côté centre) et moitié droite
            for sgn, Rl in ((-1, rot_z(180)), (1, rot_y(180) @ rot_z(180))):
                ctr = p + dh * (sgn * w / 4)
                ctr = np.array([ctr[0], y - hf / 2, ctr[2]])
                b.part("wedge", (0.1, hf, w / 2), ctr, F @ Rl, col, collide=False, shadow=False, name="Fanion")
    return {"fanions": n}


# ---------------------------------------------------------------------------
# Planche de contrôle
# ---------------------------------------------------------------------------

def planche(b, variant: int = 0, partie: int | None = None) -> dict:
    """Tous les objets du module alignés, pour un seul rendu de contrôle (apercu.py assets.mobilier:planche).
    `partie` 0 ou 1 : seulement la première ou la seconde moitié (images plus lisibles)."""
    items = [
        (lampadaire_ville, {"variant": variant}, 4),
        (lampadaire_campus, {"variant": variant}, 5),
        (lampadaire_campus, {"variant": variant + 1}, 5),
        (lampadaire_campus, {"variant": variant + 2}, 5),
        (borne_lumineuse, {"variant": variant}, 2),
        (banc, {"variant": variant}, 7),
        (banc, {"variant": variant + 1}, 7),
        (banc, {"variant": variant + 2}, 7),
        (poubelle, {"variant": variant}, 4),
        (distributeur, {"variant": variant, "nombre": 2}, 6),
        (feu_tricolore, {"variant": variant}, 5),
        (abribus, {"variant": variant}, 13),
        (arbre_rue, {"variant": variant}, 7),
        (arbre_rue, {"variant": 2}, 7),
        (jardiniere, {"variant": variant}, 7),
        (terrasse, {"variant": variant}, 8),
        (totem, {"variant": variant, "texte": "CAMPUS"}, 7),
        (totem, {"variant": variant + 1, "texte": "ENTRAÎNEMENT"}, 10),
        (panneau_direction, {"variant": variant, "textes": ("STADE", "CAMPUS", "CAFÉ")}, 10),
        (cloture, {"variant": 0, "longueur": 12}, 12),
        (cloture, {"variant": 1, "longueur": 8}, 8),
        (cloture, {"variant": 2, "longueur": 8}, 8),
        (plots, {"variant": variant}, 9),
        (pneus, {"variant": variant}, 5),
        (haies_athletisme, {"variant": variant}, 4),
        (sac_frappe, {"variant": variant}, 6),
        (caisses, {"variant": variant + 1}, 6),
        (banniere, {"variant": variant}, 3),
        (banniere, {"variant": variant + 1}, 3),
    ]
    if partie is not None:
        items = items[:15] if partie == 0 else items[15:]
    x = 0.0
    n = {}
    for fn, kw, w in items:
        n0 = len(b.parts)
        with b.at((x + w / 2, 0, 0)):
            fn(b, **kw)
        n[f"{fn.__name__}{kw.get('variant', '')}"] = len(b.parts) - n0
        x += w + 2
    # deux mâts et une guirlande de fanions au bout de la planche
    for xm in ((x + 1, x + 21) if partie != 0 else ()):
        b.box((xm - 0.3, 0, -0.3), (xm + 0.3, 9, 0.3), c("acier"), name="MatFanions")
    if partie != 0:
        n0 = len(b.parts)
        guirlande_fanions(b, (x + 1, 8.6, 0), (x + 21, 8.6, 0), n=9, creux=1.2, variant=variant)
        n["guirlande_fanions"] = len(b.parts) - n0
    trop = {k: v for k, v in n.items() if v > 40}
    assert not trop, f"objets au-delà de 40 pièces : {trop}"
    return {"pieces_par_objet": n}
