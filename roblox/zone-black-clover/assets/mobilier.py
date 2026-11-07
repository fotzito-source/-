"""Mobilier et petite nature de la zone Black Clover (royaume de mages aux portes d'un royaume démoniaque).

Lanternes de fer et lanternes murales, braseros à flammes Neon, bâtons de mage plantés à orbe lumineux, épées
plantées, boucliers, armes abandonnées, feux de camp, chaudron, caisses, tonneaux, étal, enseignes suspendues,
panneaux, poteau indicateur, clôtures, murets, bannières unies, pierres tombales, pierres runiques, grimoires
volants (seuls ou en nuée autour d'un socle), lucioles, arbres morts, épines de racines noires, puits, charrette,
sapins sombres, rochers, meules, et une chaîne entre deux points (îlots flottants, ancrages).

Chaque objet tient en 40 pièces au plus (contrôlé par `zone.py --stats`). Origine : centre de l'emprise au sol,
avant vers -Z local, sauf mention contraire (objets muraux : origine sur la face du mur ; objets flottants :
origine au centre de l'objet). Petits détails : `collide=False`, éléments fins : `shadow=False`.
Propriété intellectuelle : aucun emblème, aucun trèfle, aucune croix ni étoile ; bannières unies ou à liseré ;
textes seulement dans `TEXTES_ENSEIGNES` et `TEXTES_INDICATEURS`.
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, rot_z, shade
from palette import CUIRS, c, vary

# Textes permis (mots français génériques, rien de la licence)
TEXTES_ENSEIGNES = ("TAVERNE", "AUBERGE", "GRIMOIRES", "MARCHÉ", "FORGE", "BIBLIOTHÈQUE", "HERBORISTE", "POTIONS",
                    "BOULANGERIE", "PAIN", "ARMURERIE")
TEXTES_INDICATEURS = ("VILLAGE", "MARCHÉ", "TAVERNE", "GRIMOIRES", "CHÂTEAU", "TOUR")

DECO = dict(collide=False)
FIN = dict(collide=False, shadow=False)
NEON = dict(material="Neon", collide=False, shadow=False)

# Teintes des feux : (extérieur, cœur)
FEUX = {"orange": ("feu", "feu_coeur"), "violet": ("feu_violet", "lueur_violette_pale"),
        "cramoisi": ("feu_cramoisi", "feu"), "vert": ("lueur_verte", "feu_coeur")}


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

def _repere(d):
    """Longueur et matrice dont l'axe X suit d (Y aussi vertical que possible)."""
    d = np.asarray(d, float)
    n = float(np.linalg.norm(d))
    x = d / n
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return n, np.column_stack([x, y, z])


def _poutre(b, a, bb, ep, col, name: str = "Poutre", ep_z: float | None = None, **kw):
    """Bloc de section ep × ep_z tendu de a à bb (branches, montants inclinés, épines)."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    n, R = _repere(bb - a)
    return b.part("block", (n, ep, ep if ep_z is None else ep_z), (a + bb) / 2, R, col, name=name, **kw)


def _segment(b, a, bb, rayon: float, col, name: str = "Tige", **kw):
    """Cylindre fin de a à bb (l'axe d'un cylindre Roblox est son X local)."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    n, R = _repere(bb - a)
    return b.part("cyl", (n, 2 * rayon, 2 * rayon), (a + bb) / 2, R, col, name=name, **kw)


def _flamme(b, x: float, y: float, z: float, taille: float = 1.0, teinte: str = "orange") -> None:
    """Flamme stylisée en 4 blocs Neon (base, corps tourné de 45°, cœur, pointe) posée en (x, y, z)."""
    ext, coeur = (c(n) for n in FEUX[teinte])
    s = taille
    b.boxc((x, y + 0.45 * s, z), (1.1 * s, 0.9 * s, 1.1 * s), ext, name="Flamme", **NEON)
    b.boxc((x, y + 1.2 * s, z), (0.8 * s, 0.9 * s, 0.8 * s), ext, yaw=45, name="Flamme", **NEON)
    b.boxc((x, y + 0.95 * s, z), (0.5 * s, 1.1 * s, 0.5 * s), coeur, yaw=20, name="Coeur", **NEON)
    b.boxc((x, y + 1.95 * s, z), (0.35 * s, 0.7 * s, 0.35 * s), coeur, yaw=10, name="Pointe", **NEON)


def _lanterne(b, x: float, y: float, z: float, fer, verre: str = "lueur_lanterne", taille: float = 1.0,
              name: str = "Lanterne") -> None:
    """Lanterne carrée de fer (verre Neon, montants, chapeau en pointe) posée en (x, y, z) (bas) : 7 pièces."""
    s = taille
    b.box((x - 0.7 * s, y, z - 0.7 * s), (x + 0.7 * s, y + 0.25 * s, z + 0.7 * s), fer, name=name, **DECO)
    b.box((x - 0.5 * s, y + 0.25 * s, z - 0.5 * s), (x + 0.5 * s, y + 1.65 * s, z + 0.5 * s), c(verre), name=name, **NEON)
    for sx in (-1, 1):
        b.box((x + sx * 0.6 * s - 0.1 * s, y + 0.25 * s, z - 0.62 * s), (x + sx * 0.6 * s + 0.1 * s, y + 1.65 * s, z + 0.62 * s),
              fer, name=name, **FIN)
    b.wedge((x - 0.8 * s, y + 1.65 * s, z - 0.8 * s), (x + 0.8 * s, y + 2.35 * s, z), fer, down="-z", name=name, **DECO)
    b.wedge((x - 0.8 * s, y + 1.65 * s, z), (x + 0.8 * s, y + 2.35 * s, z + 0.8 * s), fer, down="+z", name=name, **DECO)
    b.box((x - 0.12 * s, y + 2.35 * s, z - 0.12 * s), (x + 0.12 * s, y + 2.85 * s, z + 0.12 * s), fer, name=name, **FIN)


def _label(part, face: str, texte: str, couleur, fond=None, font: str = "serif") -> None:
    part.label = {"face": face, "text": texte, "color": tuple(couleur), "bg": tuple(fond) if fond else None, "font": font}


def _rng(variant: int, sel: int = 0):
    """Aléatoire propre à l'objet : une même variante donne toujours le même objet."""
    return np.random.default_rng(1009 * (variant + 1) + sel)


def chaine(b, p0, p1, maillon: float = 1.4, epaisseur: float = 0.3, couleur=None, creux: float = 0.0) -> int:
    """Chaîne de maillons alternés (à plat / de chant) de p0 à p1, avec un léger creux facultatif.
    Sert aux îlots flottants (ancrages), aux herses, aux enseignes. Renvoie le nombre de maillons (≤ 40)."""
    col = couleur or c("chaine")
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    L = float(np.linalg.norm(p1 - p0))
    n = max(1, min(40, int(round(L / maillon))))
    pts = []
    for i in range(n + 1):
        t = i / n
        p = p0 + (p1 - p0) * t
        p[1] -= creux * 4 * t * (1 - t)
        pts.append(p)
    for i in range(n):
        a, bb = pts[i], pts[i + 1]
        lg, R = _repere(bb - a)
        if i % 2:
            R = R @ np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)     # maillon de chant
        b.part("block", (lg + epaisseur * 0.6, epaisseur, epaisseur * 2.4), (a + bb) / 2, R, col, name="Maillon", **FIN)
    return n


# ---------------------------------------------------------------------------
# Éclairage et feux
# ---------------------------------------------------------------------------

def lanterne_fer(b, variant: int = 0) -> dict:
    """Lanterne de rue en fer forgé sur socle de pierre.
    v0 : lanterne au sommet ; v1 : crosse vers l'avant (-Z), lanterne suspendue ; v2 : fût tordu, verre violet
    (lanterne de mage) ; v3 : deux bras (±X)."""
    fer = c("fer_fonce")
    v = variant % 4
    with b.group("LanterneFer"):
        b.box((-0.8, 0, -0.8), (0.8, 0.8, 0.8), c("pierre_fonce"), studs="top", name="Socle")
        b.box((-0.45, 0.8, -0.45), (0.45, 1.6, 0.45), fer, name="Pied")
        if v == 2:
            _poutre(b, (0, 1.6, 0), (0.35, 5.6, 0.1), 0.4, fer, name="Fut")
            _poutre(b, (0.35, 5.6, 0.1), (-0.1, 9.4, -0.05), 0.36, fer, name="Fut")
        else:
            b.box((-0.2, 1.6, -0.2), (0.2, 9.6, 0.2), fer, name="Fut")
        b.box((-0.4, 2.4, -0.4), (0.4, 2.7, 0.4), fer, name="Bague", **DECO)
        if v in (0, 2):
            b.box((-0.45, 9.4, -0.45), (0.45, 9.7, 0.45), fer, name="Plateau", **DECO)
            _lanterne(b, -0.05 if v == 2 else 0, 9.7, 0, fer, "lueur_violette" if v == 2 else "lueur_lanterne")
            h = 12.6
        elif v == 1:
            b.box((-0.15, 9.3, -2.6), (0.15, 9.6, 0.2), fer, name="Crosse", **DECO)
            b.box((-0.12, 9.6, 0.0), (0.12, 10.4, 0.25), fer, name="Volute", **FIN)
            b.box((-0.06, 8.6, -2.46), (0.06, 9.3, -2.34), fer, name="Tige", **FIN)
            _lanterne(b, 0, 6.2, -2.4, fer, "lueur_lanterne", 0.9)
            b.ball((0, 9.95, 0), 0.32, fer, name="Pointe", **DECO)
            h = 10.4
        else:
            b.box((-2.4, 9.3, -0.15), (2.4, 9.6, 0.15), fer, name="Bras", **DECO)
            for sx in (-2.2, 2.2):
                _lanterne(b, sx, 9.6, 0, fer, "lueur_lanterne", 0.8)
            b.box((-0.12, 9.6, -0.12), (0.12, 10.6, 0.12), fer, name="Pointe", **FIN)
            h = 11.9
    return {"emprise": (5.4 if v == 3 else 1.6, 3.6 if v == 1 else 1.6), "hauteur": h}


def lanterne_murale(b, variant: int = 0) -> dict:
    """Lanterne murale sur potence. Origine : face du mur, au niveau de la potence ; dépasse vers -Z.
    v0 : verre chaud ; v1 : verre violet ; v2 : verre cramoisi (quartier démoniaque)."""
    fer = c("fer_fonce")
    verre = ("lueur_lanterne", "lueur_violette", "lueur_cramoisie")[variant % 3]
    with b.group("LanterneMurale"):
        b.box((-0.4, -1.2, -0.2), (0.4, 0.4, 0.0), fer, name="Platine", **DECO)
        b.box((-0.12, 0.0, -1.8), (0.12, 0.25, -0.2), fer, name="Potence", **DECO)
        b.box((-0.08, -1.0, -0.6), (0.08, 0.0, -0.4), fer, name="Jambe", **FIN)
        b.box((-0.05, -0.5, -1.6), (0.05, 0.0, -1.5), fer, name="Tige", **FIN)
        _lanterne(b, 0, -2.6, -1.55, fer, verre, 0.75)
    return {"emprise": (1.4, 2.0), "hauteur": 3.3}


def brasero(b, variant: int = 0) -> dict:
    """Brasero à flammes Neon. v0 : vasque de fer sur trépied, feu orange ; v1 : vasque sur piédestal de pierre,
    feu violet ; v2 : haute coupe de fer, feu cramoisi ; v3 : bac de pierre carré, feu vert maladif."""
    v = variant % 4
    fer = c("fer_fonce")
    teinte = ("orange", "violet", "cramoisi", "vert")[v]
    with b.group("Brasero"):
        if v == 0:
            for k in range(3):
                a = math.radians(90 + 120 * k)
                _poutre(b, (1.3 * math.cos(a), 0, 1.3 * math.sin(a)), (0.5 * math.cos(a), 2.6, 0.5 * math.sin(a)), 0.25,
                        fer, name="Pied")
            y = 2.6
        elif v == 1:
            b.box((-1.2, 0, -1.2), (1.2, 0.6, 1.2), c("pierre_fonce"), studs="top", name="Socle")
            b.box((-0.75, 0.6, -0.75), (0.75, 2.8, 0.75), c("pierre"), name="Pilier")
            b.box((-1.0, 2.8, -1.0), (1.0, 3.2, 1.0), c("pierre_pale"), name="Chapiteau")
            y = 3.2
        elif v == 2:
            b.box((-1.0, 0, -1.0), (1.0, 0.3, 1.0), fer, name="Platine")
            b.cyl((0, 2.2, 0), 0.22, 3.8, fer, name="Tige")
            b.box((-0.5, 1.2, -0.5), (0.5, 1.5, 0.5), fer, name="Bague", **DECO)
            y = 4.1
        else:
            for sx in (-1, 1):
                b.box((sx * 1.0 - 0.3, 0, -1.3), (sx * 1.0 + 0.3, 1.8, 1.3), c("moellon_fonce"), studs="top", name="Bac")
                b.box((-0.7, 0, sx * 1.0 - 0.3), (0.7, 1.8, sx * 1.0 + 0.3), c("moellon"), studs="top", name="Bac")
            b.box((-0.7, 0, -0.7), (0.7, 1.2, 0.7), c("bois_brule"), name="Braises")
            _flamme(b, 0, 1.2, 0, 1.1, teinte)
            return {"emprise": (2.6, 2.6), "hauteur": 3.6}
        b.cyl((0, y + 0.35, 0), 1.25, 0.7, fer, name="Vasque")
        b.cyl((0, y + 0.8, 0), 1.45, 0.2, c("fer"), name="Bord", **DECO)
        b.cyl((0, y + 0.95, 0), 1.0, 0.15, c("bois_brule"), name="Braises", **DECO)
        _flamme(b, 0, y + 0.95, 0, 1.0, teinte)
    return {"emprise": (2.9, 2.9), "hauteur": y + 3.2}


def feu_camp(b, variant: int = 0) -> dict:
    """Feu de camp : cercle de pierres, bûches croisées, flammes Neon.
    v0 : feu vif ; v1 : trépied et marmite ; v2 : braises cramoisies mourantes ; v3 : bûches-sièges autour."""
    v = variant % 4
    rng = _rng(v, 3)
    with b.group("FeuCamp"):
        for k in range(7):
            a = 2 * math.pi * k / 7
            b.boxc((1.7 * math.cos(a), 0.3, 1.7 * math.sin(a)), (0.9, 0.6, 0.7), vary("pierre_fonce", rng, 0.1),
                   yaw=-math.degrees(a) + float(rng.uniform(-15, 15)), studs="top", name="Pierre")
        for k in range(3):
            a = math.radians(30 + 60 * k)
            _poutre(b, (-1.2 * math.cos(a), 0.15, -1.2 * math.sin(a)), (1.2 * math.cos(a), 0.55, 1.2 * math.sin(a)), 0.45,
                    c("bois_fonce") if k % 2 else c("bois"), name="Buche", **DECO)
        if v == 2:
            b.box((-0.8, 0.0, -0.8), (0.8, 0.5, 0.8), c("cramoisi"), material="Neon", name="Braises", **FIN)
            b.boxc((0.2, 0.7, -0.1), (0.5, 0.5, 0.5), c("feu_cramoisi"), yaw=30, name="Braise", **NEON)
            h = 1.0
        else:
            b.box((-0.7, 0.0, -0.7), (0.7, 0.35, 0.7), c("feu"), name="Braises", **NEON)
            _flamme(b, 0, 0.3, 0, 1.0, "orange")
            h = 2.6
        if v == 1:
            for k in range(3):
                a = math.radians(90 + 120 * k)
                _poutre(b, (2.2 * math.cos(a), 0, 2.2 * math.sin(a)), (0, 4.6, 0), 0.22, c("bois_fonce"), name="Trepied", **DECO)
            b.box((-0.05, 2.9, -0.05), (0.05, 4.5, 0.05), c("chaine"), name="Chainette", **FIN)
            b.cyl((0, 2.45, 0), 0.75, 0.9, c("fer_fonce"), name="Marmite", **DECO)
            h = 4.8
        if v == 3:
            for k, a in enumerate((20, 150, 260)):
                r = math.radians(a)
                b.cyl((3.4 * math.cos(r), 0.5, 3.4 * math.sin(r)), 0.5, 2.4, vary("bois", rng),
                      axis="x" if k % 2 else "z", name="Siege")
    return {"emprise": (5.0 if v != 3 else 8.0, 5.0 if v != 3 else 8.0), "hauteur": h}


def chaudron(b, variant: int = 0) -> dict:
    """Chaudron de fer sur pierres, potion bouillonnante (v0 vert maladif, v1 violet, v2 cramoisi)."""
    teinte = ("lueur_verte", "lueur_violette", "lueur_cramoisie")[variant % 3]
    with b.group("Chaudron"):
        for k in range(3):
            a = math.radians(90 + 120 * k)
            b.boxc((1.5 * math.cos(a), 0.4, 1.5 * math.sin(a)), (1.0, 0.8, 1.0), c("pierre_fonce"), yaw=k * 25, studs="top",
                   name="Pierre")
        b.box((-0.6, 0, -0.6), (0.6, 0.4, 0.6), c("feu"), name="Braises", **NEON)
        b.cyl((0, 1.7, 0), 1.35, 1.8, c("fer_fonce"), name="Cuve")
        b.cyl((0, 0.9, 0), 1.0, 0.4, c("fer_fonce"), name="Fond")
        b.cyl((0, 2.7, 0), 1.5, 0.3, c("fer"), name="Bord")
        b.cyl((0, 2.88, 0), 1.2, 0.12, c(teinte), name="Potion", **NEON)
        for (x, y, z, r) in ((0.4, 3.1, -0.2, 0.32), (-0.5, 3.2, 0.3, 0.24), (0.1, 3.5, 0.4, 0.16)):
            b.ball((x, y, z), r, c(teinte), name="Bulle", **NEON)
    return {"emprise": (4.0, 4.0), "hauteur": 3.9}


# ---------------------------------------------------------------------------
# Champ de bataille des mages
# ---------------------------------------------------------------------------

ORBES = ("lueur_violette", "lueur_verte", "lueur_doree", "lueur_cramoisie")


def baton_mage(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Bâton de mage planté dans le sol, légèrement penché, orbe lumineux (Neon) tenu au sommet.
    v0 : orbe violet, tête fourchue ; v1 : orbe vert, crosse recourbée ; v2 : orbe doré, anneau ; v3 : orbe
    cramoisi, couronne d'épines. Hauteur ≈ 9 × taille (taille 2,2 : grand bâton de ≈ 20 à orbe de 2,4). Reste dans
    un rayon de 1,6 × taille autour de l'origine ; il penche vers +X+Z local (v0, v2) ou -X-Z local (v1, v3)."""
    v = variant % 4
    k = float(taille)
    bois = (c("bois_noir"), c("bois_mort"), c("bois_fonce"), c("racine"))[v]
    orbe = c(ORBES[v])
    t = math.radians((7, -9, 5, -6)[v])
    d = np.array([math.sin(t) * 0.7, math.cos(t), math.sin(t) * 0.7])
    d /= np.linalg.norm(d)
    p = lambda s: d * s * k                                 # noqa: E731  point du fût à la hauteur s
    V = lambda *xyz: np.array(xyz, float) * k               # noqa: E731  décalage mis à l'échelle
    with b.group("BatonMage"):
        b.box((-0.9 * k, 0, -0.9 * k), (0.9 * k, 0.3 * k, 0.9 * k), c("terre_fonce"), studs="top", name="Butte")
        _poutre(b, p(-0.2), p(7.6), 0.32 * k, bois, name="Fut")
        for s in (2.5, 5.8):
            _poutre(b, p(s - 0.2), p(s + 0.2), 0.48 * k, c("toile_ecru") if s < 3 else c("cuir_brun"), name="Ligature",
                    **DECO)
        top = p(7.6)
        if v == 0:
            for kk in (-1, 1):
                q = top + V(0.45 * kk, 0.9, 0.0)
                _poutre(b, top, q, 0.22 * k, bois, name="Fourche", **DECO)
                _poutre(b, q, q + V(-0.15 * kk, 0.7, 0), 0.18 * k, bois, name="Fourche", **FIN)
            b.ball(top + V(0, 1.05, 0), 0.55 * k, orbe, name="Orbe", **NEON)
            h = top[1] + 1.8 * k
        elif v == 1:
            q1 = top + V(0.0, 1.0, 0.0)
            q2 = q1 + V(-0.9, 0.7, 0.0)
            q3 = q2 + V(-0.7, -0.6, 0.0)
            _poutre(b, top, q1, 0.3 * k, bois, name="Crosse", **DECO)
            _poutre(b, q1, q2, 0.28 * k, bois, name="Crosse", **DECO)
            _poutre(b, q2, q3, 0.24 * k, bois, name="Crosse", **DECO)
            b.ball(q3 + V(0.15, -0.65, 0), 0.5 * k, orbe, name="Orbe", **NEON)
            h = q2[1] + 0.3 * k
        elif v == 2:
            b.cyl(top + V(0, 1.1, 0), 0.95 * k, 0.18 * k, c("laiton"), axis="z", name="Anneau", **DECO)
            b.ball(top + V(0, 1.1, 0), 0.6 * k, orbe, name="Orbe", **NEON)
            h = top[1] + 2.1 * k
        else:
            b.ball(top + V(0, 0.85, 0), 0.6 * k, orbe, name="Orbe", **NEON)
            for kk in range(4):
                a = math.radians(45 + 90 * kk)
                base = top + V(0.4 * math.cos(a), 0.2, 0.4 * math.sin(a))
                _poutre(b, base, base + V(0.5 * math.cos(a), 1.5, 0.5 * math.sin(a)), 0.16 * k, c("epine"),
                        name="Epine", **FIN)
            h = top[1] + 1.8 * k
        b.ball(top, 0.3 * k, c("laiton") if v != 3 else c("cramoisi"), name="Bague", **DECO)
    return {"emprise": (1.8 * k, 1.8 * k), "hauteur": round(float(h), 2)}


def epee_plantee(b, variant: int = 0) -> dict:
    """Épée plantée dans le sol, penchée. v0 : épée d'acier ; v1 : lame brisée ; v2 : grande épée rouillée ;
    v3 : épée avec un lambeau de toile noué à la garde."""
    v = variant % 4
    larg = (0.6, 0.6, 1.0, 0.6)[v]
    lame = (c("acier"), c("acier"), c("rouille"), shade(c("acier"), 0.85))[v]
    long_ = (3.6, 1.6, 4.6, 3.4)[v]
    t = (10, -14, 6, -8)[v]
    with b.group("Epee"):
        b.box((-0.7, 0, -0.5), (0.7, 0.25, 0.5), c("terre_fonce"), name="Butte", **DECO)
        with b.at((0, 0, 0), yaw=(20, -35, 65, 140)[v]):
            R = rot_z(t)
            def pt(y):                                                   # point de l'axe à la hauteur y (repère penché)
                return R @ np.array([0.0, y, 0.0])
            b.part("block", (larg, long_ + 0.4, 0.16), pt((long_ - 0.4) / 2), R, lame, name="Lame", **DECO)
            if v == 1:
                b.part("wedge", (larg, 0.5, 0.16), pt(long_ - 0.1), R, lame, name="Cassure", **FIN)
            b.part("block", (larg * 3.2, 0.3, 0.4), pt(long_ + 0.1), R, c("fer_fonce"), name="Garde", **DECO)
            b.part("cyl", (1.3, 0.34, 0.34), pt(long_ + 0.9), R @ rot_z(90), c("cuir_brun"), name="Poignee", **DECO)
            b.part("ball", (0.55, 0.55, 0.55), pt(long_ + 1.7), R, c("laiton"), name="Pommeau", **DECO)
            if v == 3:
                b.part("block", (0.7, 1.6, 0.1), pt(long_ - 0.6) + np.array([0.5, 0, 0.13]), R, c("toile_cramoisie"),
                       name="Lambeau", **FIN)
    return {"emprise": (1.6, 1.4), "hauteur": long_ + 2.0}


BOUCLIERS = ("toile_cramoisie", "toile_nuit", "toile_grise", "cuir_brun")


def bouclier(b, variant: int = 0) -> dict:
    """Bouclier abandonné, uni (aucun emblème). v0 : rond, appuyé ; v1 : écu, planté ; v2 : rond, à plat ;
    v3 : écu couché sur une pierre."""
    v = variant % 4
    fond = c(BOUCLIERS[v])
    with b.group("Bouclier"):
        if v in (0, 2):
            R = rot_z(-70) if v == 0 else rot_z(-90)
            y = 0.62 if v == 0 else 0.2
            b.part("cyl", (0.2, 2.8, 2.8), (0.25 if v == 0 else 0, y, 0), R, fond, name="Disque")
            b.part("cyl", (0.12, 3.1, 3.1), (0.25 - 0.17 if v == 0 else 0, y - 0.06 if v == 0 else 0.06, 0), R, c("fer_fonce"),
                   name="Cerclage", **DECO)
            off = R @ np.array([0.18, 0, 0])
            b.ball((0.25 + off[0] if v == 0 else 0, y + off[1], 0), 0.45, c("fer"), name="Umbo", **DECO)
            h = 2.7 if v == 0 else 0.6
        else:
            with b.at((0, 0, 0), yaw=25 if v == 1 else -40):
                R = rot_z(8) if v == 1 else rot_z(-75)
                y0 = 0.9 if v == 1 else 0.9
                b.part("block", (2.0, 1.8, 0.22), (0, y0 + 0.9, 0) if v == 1 else (0.6, 0.85, 0), R, fond, name="Ecu")
                b.part("wedge", (2.0, 1.2, 0.22), (0, y0 - 0.6, 0) if v == 1 else (-0.55, 0.55, 0),
                       R @ np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], float), fond, name="Pointe")
                b.part("block", (2.2, 0.25, 0.3), (0, y0 + 1.75, 0) if v == 1 else (1.4, 1.05, 0), R, c("fer_fonce"),
                       name="Bord", **DECO)
                if v == 3:
                    b.box((-1.6, 0, -0.8), (-0.2, 0.7, 0.8), c("pierre_fonce"), studs="top", name="Pierre")
            h = 2.8 if v == 1 else 1.4
    return {"emprise": (3.2, 2.0), "hauteur": h}


def armes_abandonnees(b, variant: int = 0) -> dict:
    """Tas d'armes abandonnées sur le champ de bataille : épées plantées, bouclier, casque, lance couchée."""
    v = variant % 3
    with b.group("Armes"):
        with b.at((-1.2, 0, 0.4)):
            epee_plantee(b, variant=v)
        with b.at((1.4, 0, -0.6)):
            epee_plantee(b, variant=(v + 1) % 4)
        with b.at((0.4, 0, 1.6)):
            bouclier(b, variant=(v * 2 + 1) % 4)
        # casque rond à nasal
        hx, hz = (-1.6, -1.4) if v != 1 else (1.8, 1.2)
        b.ball((hx, 0.55, hz), 0.75, c("acier"), name="Casque", **DECO)
        b.cyl((hx, 0.25, hz), 0.85, 0.2, c("fer"), name="Bord", **DECO)
        # lance couchée
        _segment(b, (-3.2, 0.2, 2.2), (3.0, 0.2, -2.6 if v != 2 else 2.4), 0.12, c("bois"), name="Hampe", **DECO)
        q = np.array([3.0, 0.2, -2.6 if v != 2 else 2.4])
        b.part("wedge", (0.3, 0.2, 0.9), q + np.array([0.3, -0.1, -0.25 if v != 2 else 0.25]), None, c("acier"), name="Fer",
               **FIN)
    return {"emprise": (7.0, 6.0), "hauteur": 5.4}


# ---------------------------------------------------------------------------
# Caisses, tonneaux, étal, puits, charrette, meule
# ---------------------------------------------------------------------------

def caisses(b, variant: int = 0) -> dict:
    """Pile de caisses de bois cerclées (2 ou 3)."""
    rng = _rng(variant, 5)
    v = variant % 3
    pos = (((-0.8, 0, 0), 2.0), ((1.3, 0, 0.3), 1.6), ((-0.4, 2.0, 0.1), 1.6))[:2 + (v != 1)]
    with b.group("Caisses"):
        for (x, y, z), s in pos:
            col = vary("bois_clair" if v != 2 else "bois_gris", rng, 0.08)
            yaw = float(rng.uniform(-12, 12))
            with b.at((x, y, z), yaw=yaw):
                b.box((-s / 2, 0, -s / 2), (s / 2, s, s / 2), col, name="Caisse")
                b.box((-s / 2 - 0.1, s * 0.15, -s / 2 - 0.1), (s / 2 + 0.1, s * 0.3, s / 2 + 0.1), c("bois_fonce"),
                      name="Cerclage", **DECO)
                b.box((-s / 2 - 0.1, s * 0.7, -s / 2 - 0.1), (s / 2 + 0.1, s * 0.85, s / 2 + 0.1), c("bois_fonce"),
                      name="Cerclage", **DECO)
    return {"emprise": (4.2, 2.4), "hauteur": 3.6 if v != 1 else 2.0}


def tonneaux(b, variant: int = 0) -> dict:
    """Tonneaux debout (2 ou 3), cerclés de fer ; v2 : un tonneau couché."""
    v = variant % 3
    with b.group("Tonneaux"):
        for i, (x, z) in enumerate(((-1.0, 0.0), (1.0, 0.3), (0.0, 1.7))[:2 + (v == 0)]):
            if v == 2 and i == 1:
                b.cyl((x, 0.85, z), 0.85, 2.2, c("bois"), axis="z", name="Tonneau")
                for dz in (-0.75, 0.75):
                    b.cyl((x, 0.85, z + dz), 0.95, 0.18, c("fer_fonce"), axis="z", name="Cercle", **DECO)
                continue
            b.cyl((x, 1.1, z), 0.85, 2.2, vary("bois", np.random.default_rng(i + 7 * v), 0.08), name="Tonneau")
            for dy in (0.45, 1.75):
                b.cyl((x, dy, z), 0.95, 0.18, c("fer_fonce"), name="Cercle", **DECO)
            b.cyl((x, 2.25, z), 0.7, 0.1, c("bois_fonce"), name="Fond", **DECO)
    return {"emprise": (4.0, 3.5), "hauteur": 2.3}


def etal(b, variant: int = 0) -> dict:
    """Étal de marché sous auvent de toile sombre : potions colorées (quelques-unes lumineuses), livres, herbes.
    L'avant (-Z) est le côté du client. v0 cramoisi, v1 violet, v2 nuit, v3 brun."""
    v = variant % 4
    toile = c(("toile_cramoisie", "toile_violette", "toile_nuit", "cuir_brun")[v])
    rng = _rng(v, 9)
    with b.group("Etal"):
        b.box((-3.0, 0, -1.2), (3.0, 2.6, 1.2), c("bois_fonce"), name="Comptoir")
        b.box((-3.2, 2.6, -1.4), (3.2, 2.9, 1.4), c("bois"), studs="top", name="Plateau")
        for x in (-2.9, 2.9):
            b.box((x - 0.2, 2.9, 0.9), (x + 0.2, 6.4, 1.3), c("bois_fonce"), name="Montant")
            b.box((x - 0.2, 2.9, -2.6), (x + 0.2, 5.2, -2.2), c("bois_fonce"), name="Montant", **DECO)
        b.wedge((-3.4, 5.2, -2.8), (3.4, 6.6, 1.4), toile, down="-z", studs="top", name="Auvent", **DECO)
        b.box((-3.4, 4.7, -2.9), (3.4, 5.2, -2.7), shade(toile, 0.75), name="Lambrequin", **FIN)
        for i in range(5):                                   # fioles
            x = -2.4 + 1.1 * i
            col = c(("lueur_verte", "cuir_rouge", "lueur_violette", "cuir_bleu", "lueur_doree")[(i + v) % 5])
            neon = i % 2 == 0
            b.cyl((x, 3.3, -0.6), 0.28, 0.8, col, name="Fiole", **(NEON if neon else DECO))
            b.box((x - 0.08, 3.7, -0.68), (x + 0.08, 3.95, -0.52), c("bois_clair"), name="Bouchon", **FIN)
        for i in range(2):                                   # livres
            col = c(CUIRS[int(rng.integers(len(CUIRS)))])
            b.boxc((-1.4 + 2.6 * i, 3.1, 0.6), (1.2, 0.4, 0.9), col, yaw=float(rng.uniform(-15, 15)), name="Livre", **DECO)
        b.box((1.6, 2.9, 0.2), (2.8, 3.3, 1.1), c("herbe_seche"), name="Herbes", **DECO)
    return {"emprise": (6.8, 4.2), "hauteur": 6.6}


def puits(b, variant: int = 0) -> dict:
    """Puits de moellons. v0 : toit de chaume sur deux poteaux, treuil et seau ; v1 : puits en ruine (margelle
    brisée, sans toit) ; v2 : toit d'ardoise."""
    v = variant % 3
    rng = _rng(v, 11)
    with b.group("Puits"):
        for k in range(8):
            if v == 1 and k in (2, 3):
                continue
            a = 2 * math.pi * k / 8
            hk = (2.4 if k % 2 == 0 else 2.5) if not (v == 1 and k == 4) else 1.4
            b.boxc((2.0 * math.cos(a), hk / 2, 2.0 * math.sin(a)), (1.75, hk, 0.9), vary("moellon", rng, 0.1),
                   yaw=-math.degrees(a) + 90, studs="top", name="Margelle")
        b.cyl((0, 1.0, 0), 1.6, 0.2, c("eau"), name="Eau", **DECO)
        if v == 1:
            b.boxc((2.8, 0.4, 2.4), (1.6, 0.8, 0.9), c("moellon_fonce"), yaw=30, studs="top", name="Pierre")
            _poutre(b, (-3.0, 0.2, -1.0), (-0.2, 0.6, -3.6), 0.4, c("bois_gris"), name="PoteauTombe")
            return {"emprise": (5.0, 5.0), "hauteur": 2.4}
        for x in (-2.0, 2.0):
            b.box((x - 0.25, 2.4, -0.25), (x + 0.25, 6.4, 0.25), c("bois_fonce"), name="Poteau")
        b.cyl((0, 5.0, 0), 0.3, 4.0, c("bois"), axis="x", name="Treuil", **DECO)
        b.box((2.25, 4.9, -0.1), (2.45, 5.1, -0.9), c("fer_fonce"), name="Manivelle", **FIN)   # contre le poteau
        b.box((-0.05, 3.2, -0.05), (0.05, 4.8, 0.05), c("chaine"), name="Corde", **FIN)
        b.cyl((0, 2.9, 0), 0.4, 0.7, c("bois_clair"), name="Seau", **DECO)
        toit = c("chaume_fonce") if v == 0 else c("ardoise")
        b.wedge((-2.8, 6.4, -2.0), (2.8, 7.9, 0), toit, down="-z", studs="top", name="Toit", **DECO)
        b.wedge((-2.8, 6.4, 0), (2.8, 7.9, 2.0), toit, down="+z", studs="top", name="Toit", **DECO)
        b.box((-2.9, 7.9, -0.2), (2.9, 8.2, 0.2), c("bois_fonce"), name="Faitiere", **DECO)
    return {"emprise": (5.8, 5.0), "hauteur": 8.2}


def charrette(b, variant: int = 0) -> dict:
    """Charrette de bois sombre, brancards vers -Z. v0 : chargée de sacs ; v1 : brisée (penchée, roue tombée) ;
    v2 : chargée de foin."""
    v = variant % 3
    with b.group("Charrette"):
        R = rot_z(-9) if v == 1 else None
        y = 1.6 if v != 1 else 1.25
        b.part("block", (3.2, 0.4, 5.0), (0, y, 0.4), R, c("bois"), studs="top", name="Plateau")
        for sx in (-1, 1):
            b.part("block", (0.25, 0.9, 5.0), (sx * 1.5, y + 0.65 - (0.24 * sx if v == 1 else 0), 0.4), R, c("bois_fonce"),
                   name="Ridelle", collide=False)
        b.cyl((0, 1.22, 0.8), 0.18, 3.6, c("fer_fonce"), axis="x", name="Essieu", **DECO)
        b.cyl((-1.9, 1.1, 0.8), 1.1, 0.3, c("bois_fonce"), axis="x", name="Roue")
        if v == 1:
            b.cyl((2.6, 0.15, -0.6), 1.1, 0.3, c("bois_fonce"), axis="y", name="RoueTombee", **DECO)
        else:
            b.cyl((1.9, 1.1, 0.8), 1.1, 0.3, c("bois_fonce"), axis="x", name="Roue")
        for sx in (-0.9, 0.9):
            _poutre(b, (sx, 1.4, -2.0), (sx * 0.8, 0.12, -4.6), 0.25, c("bois_fonce"), name="Brancard", **DECO)
        if v == 0:
            for i, (x, z) in enumerate(((-0.7, 1.6), (0.7, 1.4), (0.0, -0.4))):
                b.boxc((x, y + 0.65, z), (1.2, 0.9, 1.5), c("toile_ecru") if i != 1 else c("toile_grise"), yaw=10 * i,
                       name="Sac", **DECO)
        elif v == 2:
            b.box((-1.3, y + 0.2, -1.6), (1.3, y + 1.8, 2.6), c("foin"), studs="top", name="Foin", **DECO)
    return {"emprise": (4.4, 9.4), "hauteur": 3.6}


def meule(b, variant: int = 0) -> dict:
    """Meule de foin terni en gradins."""
    s = 1.0 + 0.15 * (variant % 3)
    with b.group("Meule"):
        b.box((-2.0 * s, 0, -2.0 * s), (2.0 * s, 2.0 * s, 2.0 * s), c("foin"), studs="top", name="Meule")
        b.box((-1.5 * s, 2.0 * s, -1.5 * s), (1.5 * s, 3.2 * s, 1.5 * s), c("ble_fonce"), studs="top", name="Meule")
        b.box((-0.8 * s, 3.2 * s, -0.8 * s), (0.8 * s, 4.0 * s, 0.8 * s), c("foin"), studs="top", name="Meule")
    return {"emprise": (4 * s, 4 * s), "hauteur": 4 * s}


# ---------------------------------------------------------------------------
# Enseignes, panneaux, clôtures, bannières
# ---------------------------------------------------------------------------

FONDS_ENSEIGNE = (("bois_fonce", "dorure"), ("toile_cramoisie", "toile_ecru"), ("toile_nuit", "dorure"),
                  ("bois_noir", "toile_ecru"))


def enseigne(b, texte: str = "TAVERNE", variant: int = 0) -> dict:
    """Enseigne suspendue sous une potence de fer, perpendiculaire au mur (lisible des deux sens de course).
    Origine : face du mur, au niveau de la potence (y = 0) ; la potence dépasse vers -Z. Deux planches dos à dos,
    texte sur les faces ±X locales (donc vers ±Z une fois l'enseigne posée sur une façade)."""
    assert texte in TEXTES_ENSEIGNES, texte
    fond, encre = (c(n) for n in FONDS_ENSEIGNE[variant % len(FONDS_ENSEIGNE)])
    fer = c("fer_fonce")
    long_ = min(max(1.0 + 0.75 * len(texte), 3.0), 8.0)
    z0, z1 = -0.9, -0.9 - long_
    with b.group("Enseigne"):
        b.box((-0.35, -0.9, -0.2), (0.35, 0.5, 0.0), fer, name="Platine", **DECO)
        b.box((-0.12, 0.0, z1 - 0.5), (0.12, 0.3, -0.2), fer, name="Potence", **DECO)
        _poutre(b, (0, -0.8, -0.2), (0, 0.0, -1.6), 0.18, fer, name="Jambe", **FIN)
        b.ball((0, 0.15, z1 - 0.5), 0.25, fer, name="Bouton", **FIN)
        for z in (z0 - 0.3, z1 + 0.3):
            b.box((-0.05, -0.5, z - 0.05), (0.05, 0.0, z + 0.05), c("chaine"), name="Anneau", **FIN)
        y0, y1 = -2.3, -0.5
        p1 = b.box((-0.2, y0, z1), (0.0, y1, z0), fond, name="Planche", **DECO)
        p2 = b.box((0.0, y0, z1), (0.2, y1, z0), fond, name="Planche", **DECO)
        _label(p1, "Left", texte, encre)
        _label(p2, "Right", texte, encre)
        b.box((-0.26, y0 - 0.15, z1 - 0.1), (0.26, y0, z0 + 0.1), shade(fond, 0.7), name="Bord", **FIN)
    return {"emprise": (0.6, long_ + 1.4), "hauteur": 3.0}


def panneau_pied(b, texte: str = "MARCHÉ", variant: int = 0) -> dict:
    """Panneau sur deux pieds (texte face et dos), petit toit d'ardoise en v1."""
    assert texte in TEXTES_ENSEIGNES + TEXTES_INDICATEURS, texte
    fond, encre = (c(n) for n in FONDS_ENSEIGNE[variant % len(FONDS_ENSEIGNE)])
    w = min(max(1.6 + 0.8 * len(texte), 4.0), 9.0) / 2
    with b.group("Panneau"):
        for x in (-w + 0.5, w - 0.5):
            b.box((x - 0.25, 0, -0.25), (x + 0.25, 4.6, 0.25), c("bois_fonce"), name="Pied")
        p1 = b.box((-w, 2.4, -0.3), (w, 4.2, -0.05), fond, name="Planche", **DECO)
        p2 = b.box((-w, 2.4, 0.05), (w, 4.2, 0.3), fond, name="Planche", **DECO)
        b.box((-w + 0.1, 2.4, -0.05), (w - 0.1, 4.2, 0.05), shade(fond, 0.7), name="Ame", **FIN)
        _label(p1, "Front", texte, encre)
        _label(p2, "Back", texte, encre)
        if variant % 2:
            b.wedge((-w - 0.4, 4.6, -0.9), (w + 0.4, 5.4, 0), c("ardoise"), down="-z", studs="top", name="Toit", **DECO)
            b.wedge((-w - 0.4, 4.6, 0), (w + 0.4, 5.4, 0.9), c("ardoise"), down="+z", studs="top", name="Toit", **DECO)
    return {"emprise": (2 * w + 0.8, 1.8), "hauteur": 5.4}


def poteau_indicateur(b, textes=("VILLAGE", "CHÂTEAU"), variant: int = 0) -> dict:
    """Poteau indicateur : deux flèches (vers -X et +X locaux), texte des deux côtés, lanterne en v1."""
    fer = c("fer_fonce")
    with b.group("Indicateur"):
        b.box((-0.3, 0, -0.3), (0.3, 7.2, 0.3), c("bois_fonce"), name="Poteau")
        b.box((-0.45, 7.2, -0.45), (0.45, 7.5, 0.45), fer, name="Chapeau", **DECO)
        for i, t in enumerate(textes[:2]):
            assert t in TEXTES_INDICATEURS + TEXTES_ENSEIGNES, t
            s = -1 if i == 0 else 1
            L = min(max(1.2 + 0.7 * len(t), 3.0), 7.0)
            y0 = 5.6 - 1.5 * i
            xa, xb = sorted((s * 0.3, s * (0.3 + L)))
            p1 = b.box((xa, y0, -0.32), (xb, y0 + 1.1, -0.06), c("bois_clair"), name="Fleche", **DECO)
            p2 = b.box((xa, y0, 0.06), (xb, y0 + 1.1, 0.32), c("bois_clair"), name="Fleche", **DECO)
            _label(p1, "Front", t, c("bois_noir"))
            _label(p2, "Back", t, c("bois_noir"))
            tip = s * (0.3 + L)
            b.wedge((min(tip, tip + s * 0.8), y0, -0.3), (max(tip, tip + s * 0.8), y0 + 0.55, 0.3), c("bois_clair"),
                    down="+x" if s > 0 else "-x", name="Pointe", **FIN)
            b.wedge_under((min(tip, tip + s * 0.8), y0 + 0.55, -0.3), (max(tip, tip + s * 0.8), y0 + 1.1, 0.3),
                          c("bois_clair"), down="+x" if s > 0 else "-x", name="Pointe", **FIN)
        if variant % 2:
            b.box((0.3, 6.6, -0.1), (1.6, 6.8, 0.1), fer, name="Potence", **DECO)
            _lanterne(b, 1.4, 4.9, 0, fer, "lueur_lanterne", 0.6)
    return {"emprise": (13.0, 1.0), "hauteur": 7.5}


def cloture_bois(b, longueur: float = 12.0, variant: int = 0) -> dict:
    """Clôture de bois patiné le long de X local (centrée). v0 : deux lisses ; v1 : planches cassées ou tombées ;
    v2 : piquets serrés ; v3 : lisses en zigzag. ≤ 40 pièces : longueur ≤ 36 (v2 : ≤ 18)."""
    v = variant % 4
    rng = _rng(v, 13)
    n = max(1, int(round(longueur / 3.0)))
    pas = longueur / n
    x0 = -longueur / 2
    with b.group("Cloture"):
        if v == 2:
            k = int(longueur / 0.9)
            for i in range(min(k, 38)):
                x = x0 + 0.45 + i * 0.9 * longueur / (min(k, 38) * 0.9)
                hh = 2.6 + 0.4 * float(rng.uniform(-1, 1))
                b.box((x - 0.3, 0, -0.15), (x + 0.3, hh, 0.15), vary("bois_gris", rng, 0.1), name="Piquet")
            b.box((x0, 1.8, 0.15), (x0 + longueur, 2.1, 0.35), c("bois_fonce"), name="Lisse", **DECO)
            return {"emprise": (longueur, 0.7), "hauteur": 3.0}
        for i in range(n + 1):
            x = x0 + i * pas
            hh = 3.0 if v != 1 or i % 3 else 2.2
            b.box((x - 0.3, 0, -0.3), (x + 0.3, hh, 0.3), vary("bois_gris", rng, 0.08), name="Poteau")
        for y in (1.0, 2.2):
            if v == 3:
                for i in range(n):
                    xa = x0 + i * pas
                    _poutre(b, (xa, y - 0.3 + 0.6 * (i % 2), -0.42), (xa + pas, y + 0.3 - 0.6 * (i % 2), -0.42), 0.22,
                            c("bois_gris"), name="Lisse", **DECO)
                continue
            if v == 1:
                for i in range(n):
                    if (i + int(y)) % 3 == 1:
                        continue
                    xa = x0 + i * pas
                    b.box((xa, y - 0.2, -0.45), (xa + pas, y + 0.2, -0.3), c("bois_gris"), name="Lisse", **DECO)
                continue
            b.box((x0, y - 0.2, -0.45), (x0 + longueur, y + 0.2, -0.3), c("bois_gris"), name="Lisse", **DECO)
        if v == 1:
            _poutre(b, (x0 + pas * 1.2, 0.15, -1.0), (x0 + pas * 2.0, 0.15, -1.6), 0.3, c("bois_gris"), name="PlancheTombee",
                    **DECO)
    return {"emprise": (longueur, 1.0), "hauteur": 3.0}


def muret(b, longueur: float = 12.0, variant: int = 0) -> dict:
    """Muret de pierres sèches le long de X local (centré), deux assises décalées, quelques pierres manquantes."""
    rng = _rng(variant, 17)
    x0 = -longueur / 2
    with b.group("Muret"):
        for assise, (y0, y1, dec) in enumerate(((0, 1.2, 0.0), (1.2, 2.2, 1.0))):
            x = x0 + dec * (assise > 0)
            while x < x0 + longueur - 0.5:
                L = min(float(rng.uniform(1.8, 3.4)), x0 + longueur - x)
                if not (assise == 1 and rng.random() < 0.18):
                    b.box((x + 0.05, y0, -0.7 + 0.1 * assise), (x + L - 0.05, y1, 0.7 - 0.1 * assise),
                          vary("moellon", rng, 0.12), studs="top", name="Pierre")
                x += L
    return {"emprise": (longueur, 1.4), "hauteur": 2.2}


BANNIERES = ("toile_cramoisie", "toile_violette", "toile_noire", "toile_nuit")


def banniere(b, variant: int = 0, hauteur: float = 10.0) -> dict:
    """Bannière unie sur mât à traverse, liseré doré en haut. La toile pend dans le plan X-Y local (elle se voit
    de face depuis ±Z : poser avec yaw = 0 pour qu'elle regarde les coureurs). v1 et v3 : bas déchiré."""
    v = variant % 4
    toile = c(BANNIERES[v])
    h = hauteur
    L = 0.55 * h
    with b.group("Banniere"):
        b.box((-0.9, 0, -0.9), (0.9, 0.6, 0.9), c("pierre_fonce"), studs="top", name="Socle")
        b.box((-0.22, 0.6, -0.22), (0.22, h + 0.4, 0.22), c("bois_noir"), name="Mat")
        b.box((-2.1, h - 0.3, -0.12), (2.1, h, 0.12), c("fer_fonce"), name="Traverse", **DECO)
        b.box((-1.8, h - 0.3 - L, 0.24), (1.8, h - 0.3, 0.4), toile, name="Toile", **FIN)
        b.box((-1.8, h - 0.9, 0.4), (1.8, h - 0.5, 0.52), c("toile_or"), name="Lisere", **FIN)
        if v in (1, 3):
            for i, (xa, xb, d) in enumerate(((-1.8, -0.6, 1.2), (-0.6, 0.6, 0.4), (0.6, 1.8, 0.9))):
                b.box((xa + 0.05, h - 0.3 - L - d, 0.24), (xb - 0.05, h - 0.3 - L, 0.4), toile, name="Lambeau", **FIN)
        else:
            b.wedge((-1.8, h - 0.3 - L - 0.8, 0.24), (0, h - 0.3 - L, 0.4), toile, down="-x", name="Pointe", **FIN)
            b.wedge((0, h - 0.3 - L - 0.8, 0.24), (1.8, h - 0.3 - L, 0.4), toile, down="+x", name="Pointe", **FIN)
        b.ball((0, h + 0.7, 0), 0.4, c("or"), name="Pommeau", **DECO)
    return {"emprise": (4.2, 1.8), "hauteur": h + 1.1}


def banniere_murale(b, variant: int = 0, hauteur: float = 8.0) -> dict:
    """Bannière unie pendue à une tringle contre un mur. Origine : face du mur, en haut de la bannière ;
    la toile pend vers le bas, décollée de 0,4 du mur (-Z). Largeur 3,6."""
    v = variant % 4
    toile = c(BANNIERES[v])
    with b.group("BanniereMurale"):
        for x in (-1.6, 1.6):
            b.box((x - 0.12, -0.3, -0.6), (x + 0.12, 0.1, 0.0), c("fer_fonce"), name="Patte", **FIN)
        b.cyl((0, 0, -0.5), 0.14, 4.4, c("fer_fonce"), axis="x", name="Tringle", **FIN)
        b.box((-1.8, -hauteur, -0.42), (1.8, -0.15, -0.3), toile, name="Toile", **FIN)
        b.box((-1.8, -0.75, -0.54), (1.8, -0.4, -0.42), c("toile_or"), name="Lisere", **FIN)
        if v in (1, 3):
            for (xa, xb, d) in ((-1.8, -0.6, 1.0), (-0.6, 0.6, 0.3), (0.6, 1.8, 0.7)):
                b.box((xa + 0.05, -hauteur - d, -0.42), (xb - 0.05, -hauteur, -0.3), toile, name="Lambeau", **FIN)
        else:
            b.wedge((-1.8, -hauteur - 0.8, -0.42), (0, -hauteur, -0.3), toile, down="-x", name="Pointe", **FIN)
            b.wedge((0, -hauteur - 0.8, -0.42), (1.8, -hauteur, -0.3), toile, down="+x", name="Pointe", **FIN)
    return {"emprise": (4.4, 0.6), "hauteur": hauteur + 1.0}


# ---------------------------------------------------------------------------
# Pierres tombales et pierres runiques
# ---------------------------------------------------------------------------

def pierre_tombale(b, variant: int = 0) -> dict:
    """Pierre tombale sans symbole (aucune croix). v0 : dessus arrondi ; v1 : dessus en pointe ; v2 : penchée et
    fendue ; v3 : dalle couchée sur un tertre."""
    v = variant % 4
    pierre = (c("pierre_fonce"), c("pierre"), c("pierre_noire"), c("moellon_fonce"))[v]
    with b.group("Tombe"):
        b.box((-1.0, 0, -0.7), (1.0, 0.3, 0.7), c("terre_fonce"), name="Tertre", **DECO)
        if v == 0:
            b.box((-0.8, 0.3, -0.2), (0.8, 2.2, 0.2), pierre, name="Stele")
            b.cyl((0, 2.2, 0), 0.8, 0.4, pierre, axis="z", name="Arrondi")
            b.box((-0.5, 0.9, -0.3), (0.5, 1.1, -0.2), c("mousse"), name="Mousse", **FIN)
        elif v == 1:
            b.box((-0.75, 0.3, -0.2), (0.75, 2.0, 0.2), pierre, name="Stele")
            b.wedge((-0.75, 2.0, -0.2), (0, 2.8, 0.2), pierre, down="-x", name="Pointe")
            b.wedge((0, 2.0, -0.2), (0.75, 2.8, 0.2), pierre, down="+x", name="Pointe")
        elif v == 2:
            b.part("block", (1.5, 2.1, 0.4), (0.2, 1.2, 0), rot_z(-14), pierre, name="Stele")
            b.part("block", (0.12, 1.0, 0.62), (0.35, 1.7, 0), rot_z(-14) @ rot_z(25), c("fissure"), name="Fissure", **FIN)
        else:
            b.box((-0.9, 0.3, -1.2), (0.9, 0.7, 1.2), pierre, studs="top", name="Dalle")
            b.box((-0.6, 0.3, 1.2), (0.6, 1.5, 1.5), pierre, name="Chevet")
    return {"emprise": (2.0, 2.4 if v == 3 else 1.4), "hauteur": 2.8}


def pierre_runique(b, variant: int = 0) -> dict:
    """Menhir dressé, gravé de marques abstraites lumineuses (pas de lettres d'un alphabet réel).
    v0 : violet ; v1 : vert maladif ; v2 : violet, menhir double ; v3 : cramoisi."""
    v = variant % 4
    lueur = c(("lueur_violette", "lueur_verte", "lueur_violette", "lueur_cramoisie")[v])
    rng = _rng(v, 19)
    with b.group("PierreRunique"):
        for k in range(3):
            a = math.radians(40 + 120 * k)
            b.boxc((1.6 * math.cos(a), 0.3, 1.6 * math.sin(a)), (1.2, 0.6, 0.9), vary("roche_noire", rng, 0.1),
                   yaw=float(rng.uniform(0, 90)), studs="top", name="Pierre")
        hh = 6.0 + v * 0.5
        b.box((-1.1, 0, -0.6), (1.1, hh * 0.6, 0.6), c("pierre_fonce"), name="Menhir")
        b.boxc((0.1, hh * 0.6 + hh * 0.2, 0), (1.7, hh * 0.4, 1.0), c("pierre_fonce"), yaw=6, name="Menhir")
        b.wedge((-0.85, hh, -0.5), (0.95, hh + 0.9, 0.5), c("pierre_fonce"), down="-x", name="Sommet")
        b.box((-0.9, hh - 0.2, -0.45), (0.2, hh + 0.05, 0.45), c("mousse"), studs="top", name="Mousse", **DECO)
        # marques abstraites : losanges, points et traits obliques (±25°), à 0,3 au moins l'une de l'autre (aucune
        # lettre : ni L, ni T, ni Y, ni +), en saillie de 0,12 sur la face avant (bloc du haut : tourné de 6°)
        marques = ((-0.45, 1.3, "losange"), (0.35, 1.1, 25.0), (0.4, 2.2, "point"), (-0.35, 2.6, -25.0),
                   (0.1, 3.0, "losange"), (-0.4, 4.3, "point"), (0.35, 4.75, 25.0))
        for (x, y, kind) in marques:
            haut = y >= hh * 0.6
            with b.at((0.1, 0, 0) if haut else (0, 0, 0), yaw=6 if haut else 0):
                ctr = (x - 0.1 if haut else x, y, (-0.5 if haut else -0.6) - 0.05)
                if kind == "losange":
                    b.part("block", (0.4, 0.4, 0.14), ctr, rot_z(45), lueur, name="Marque", **NEON)
                elif kind == "point":
                    b.part("block", (0.3, 0.3, 0.14), ctr, None, lueur, name="Marque", **NEON)
                else:
                    b.part("block", (0.2, 0.8, 0.14), ctr, rot_z(kind), lueur, name="Marque", **NEON)
        if v == 2:
            b.box((1.8, 0, -0.5), (3.2, 3.4, 0.5), c("pierre_noire"), name="Menhir2")
            b.box((2.3, 1.4, -0.6), (2.7, 2.6, -0.5), lueur, name="Marque", **NEON)
    return {"emprise": (5.0 if v == 2 else 4.0, 4.0), "hauteur": hh + 0.9}


# ---------------------------------------------------------------------------
# Magie flottante : grimoires, nuée de grimoires, lucioles
# ---------------------------------------------------------------------------

def _livre(b, x, y, z, yaw: float, couv, page, ouvert: float = 22.0, s: float = 1.0, lumineux: bool = False) -> None:
    """Livre ouvert en V (2 couvertures + bloc de pages), dos le long de Z local : 3 pièces."""
    with b.at((x, y, z), yaw=yaw):
        for k in (-1, 1):
            R = rot_z(k * ouvert)
            off = R @ np.array([k * 0.68 * s, 0.0, 0.0])
            b.part("block", (1.4 * s, 0.12 * s, 1.9 * s), off, R, couv, name="Couverture", **DECO)
        b.box((-1.15 * s, 0.06 * s, -0.82 * s), (1.15 * s, 0.34 * s, 0.82 * s), page, name="Pages",
              **(NEON if lumineux else FIN))


def grimoire_volant(b, variant: int = 0) -> dict:
    """Grimoire ouvert qui flotte (magie voulue) : couvertures unies de cuir, pages crème, page lumineuse en v1 et v3.
    Origine : centre du livre (zone.py le pose à la hauteur voulue, près d'une source : tour, socle, cercle)."""
    v = variant % 6
    couv = c(CUIRS[v % len(CUIRS)])
    with b.group("Grimoire"):
        _livre(b, 0, 0, 0, 0, couv, c("page") if v not in (1, 3) else c("lueur_doree"), 18 + 4 * (v % 3),
               1.0, lumineux=v in (1, 3))
        b.box((-0.2, -0.05, -1.0), (0.2, 0.2, 1.0), shade(couv, 0.7), name="Dos", **FIN)
    return {"emprise": (2.8, 2.0), "hauteur": 1.0}


def nuee_grimoires(b, variant: int = 0, rayon: float = 5.0, hauteur: float = 10.0, nombre: int = 9) -> dict:
    """Nuée de grimoires en spirale autour d'un axe vertical (magie voulue, alignée sur sa source).
    v0 et v2 : sans socle (à poser contre une tour, au-dessus d'un cercle) ; v1 et v3 : sur un pupitre de pierre
    gravé, source visible de la nuée. Origine : centre de la base. ≤ 12 livres (3 pièces chacun)."""
    v = variant % 4
    nombre = max(3, min(int(nombre), 11 if v in (1, 3) else 12))
    rng = _rng(v, 23)
    with b.group("NueeGrimoires"):
        y0 = 1.5
        if v in (1, 3):
            b.box((-1.4, 0, -1.4), (1.4, 0.6, 1.4), c("pierre_fonce"), studs="top", name="Socle")
            b.box((-0.7, 0.6, -0.7), (0.7, 3.0, 0.7), c("pierre"), name="Pupitre")
            b.wedge((-1.1, 3.0, -1.0), (1.1, 3.6, 1.0), c("pierre_pale"), down="-z", name="Lutrin")
            b.box((-0.75, 1.4, -0.8), (0.75, 1.6, -0.7), c("lueur_violette"), name="Marque", **NEON)
            y0 = 4.6
        tours = 1.25
        for i in range(nombre):
            t = i / max(1, nombre - 1)
            a = 2 * math.pi * tours * t + (0.6 if v % 2 else 0.0)
            r = rayon * (0.55 + 0.45 * t) if v in (1, 3) else rayon
            y = y0 + (hauteur - y0) * t
            couv = c(CUIRS[int(rng.integers(len(CUIRS)))])
            lum = (i % 4) == 1
            _livre(b, r * math.cos(a), y, r * math.sin(a), -math.degrees(a) + float(rng.uniform(-20, 20)), couv,
                   c("lueur_doree") if lum else c("page"), float(rng.uniform(14, 34)), 0.85, lumineux=lum)
    return {"emprise": (2 * rayon + 3, 2 * rayon + 3), "hauteur": hauteur + 1}


LUCIOLES = ("lueur_doree", "lueur_violette", "lueur_verte", "lueur_cramoisie")


def lucioles(b, variant: int = 0, rayon: float = 10.0, hauteur: float = 12.0, nombre: int = 24,
             rayon_x: float | None = None, rayon_min: float = 0.0) -> dict:
    """Nuage de lucioles (petits cubes Neon) dans un cylindre de rayon `rayon`, de y = 0 à y = hauteur
    (refBC2). v0 doré, v1 violet, v2 vert, v3 cramoisi. Origine : centre du bas du nuage. ≤ 40 lucioles.
    `rayon_x` : demi-largeur en X (nuage aplati le long d'une façade) ; `rayon_min` : couronne (autour d'un toit).
    Au-dessus du couloir, poser le nuage à y ≥ 31 (rien sous 30 au-dessus de |x| < 46)."""
    v = variant % 4
    nombre = max(1, min(int(nombre), 40))
    rng = _rng(v, 29 + nombre)
    col = c(LUCIOLES[v])
    pale = mix(col, (255, 255, 255), 0.45)
    with b.group("Lucioles"):
        for i in range(nombre):
            r = math.sqrt(rayon_min ** 2 + (rayon ** 2 - rayon_min ** 2) * float(rng.random()))
            a = float(rng.uniform(0, 2 * math.pi))
            s = float(rng.choice((0.35, 0.45, 0.6)))
            fx = 1.0 if rayon_x is None else rayon_x / rayon
            b.boxc((r * math.cos(a) * fx, float(rng.uniform(0, hauteur)), r * math.sin(a)), (s, s, s),
                   pale if i % 5 == 0 else col, yaw=float(rng.uniform(0, 90)), name="Luciole", **NEON)
    return {"emprise": (2 * (rayon if rayon_x is None else rayon_x), 2 * rayon), "hauteur": hauteur}


# ---------------------------------------------------------------------------
# Petite nature : arbres morts, sapins sombres, rochers, épines de racines
# ---------------------------------------------------------------------------

def arbre_mort(b, variant: int = 0, hauteur: float = 12.0) -> dict:
    """Arbre mort tordu, branches nues en blocs inclinés. v0 : étalé ; v1 : penché ; v2 : haut et maigre à crochets ;
    v3 : tronc brisé à deux moignons. ≤ 24 pièces."""
    v = variant % 4
    rng = _rng(v, 31)
    h = hauteur
    tronc = c("bois_mort") if v != 2 else c("bois_noir")
    clair = c("bois_mort_clair")
    with b.group("ArbreMort"):
        for k in range(3):                                   # racines
            a = math.radians(30 + 120 * k + float(rng.uniform(-20, 20)))
            _poutre(b, (0, 0.8, 0), (2.2 * math.cos(a), 0.0, 2.2 * math.sin(a)), 0.6, tronc, name="Racine", **DECO)
        lean = (0.12, 0.3, 0.05, 0.08)[v]
        p0 = np.array([0.0, -0.2, 0.0])
        p1 = np.array([lean * h * 0.4, h * (0.45 if v != 3 else 0.55), 0.1])
        p2 = np.array([lean * h * 0.9, h * (0.85 if v != 3 else 0.62), -0.2])
        _poutre(b, p0, p1, (1.3 if v != 2 else 0.9) * h / 12, tronc, name="Tronc")
        _poutre(b, p1, p2, (1.0 if v != 2 else 0.7) * h / 12, tronc, name="Tronc")
        if v == 3:
            b.boxc(p2 + np.array([0, 0.4, 0]), (0.9, 0.8, 0.9), c("bois_brule"), yaw=20, name="Cassure")
        n_br = (5, 4, 6, 2)[v]
        for i in range(n_br):
            t = 0.45 + 0.5 * i / max(1, n_br - 1)
            base = p0 + (p2 - p0) * t if v != 3 else p0 + (p1 - p0) * (0.6 + 0.3 * i)
            a = math.radians(i * 137 + float(rng.uniform(-25, 25)))
            L = h * float(rng.uniform(0.25, 0.4))
            q = base + np.array([L * math.cos(a), L * float(rng.uniform(0.35, 0.8)), L * math.sin(a)])
            _poutre(b, base, q, 0.45 * h / 12, tronc if i % 2 else clair, name="Branche", **DECO)
            if v != 3:
                a2 = a + float(rng.uniform(-1.0, 1.0))
                q2 = q + np.array([0.4 * L * math.cos(a2), 0.35 * L, 0.4 * L * math.sin(a2)])
                _poutre(b, q, q2, 0.28 * h / 12, clair, name="Rameau", **FIN)
                if v == 2:
                    _poutre(b, q2, q2 + np.array([0.25 * math.cos(a2), -0.6, 0.25 * math.sin(a2)]), 0.2, clair,
                            name="Crochet", **FIN)
    return {"emprise": (0.8 * h, 0.8 * h), "hauteur": h * 1.05}


def sapin_sombre(b, variant: int = 0, hauteur: float = 16.0) -> dict:
    """Sapin sombre en étages de blocs carrés (tournés de 45° un étage sur deux), studs sur les étages.
    v0 : sapin gris-vert ; v1 : plus clair ; v2 : élancé ; v3 : à moitié mort (étages clairsemés, tronc visible)."""
    v = variant % 4
    h = hauteur
    col = (c("sapin"), c("sapin_clair"), c("sapin_fonce"), c("sapin_fonce"))[v]
    larg = (0.42, 0.42, 0.3, 0.36)[v] * h
    with b.group("Sapin"):
        b.box((-0.06 * h, 0, -0.06 * h), (0.06 * h, 0.35 * h if v != 3 else 0.8 * h, 0.06 * h), c("bois_fonce"), name="Tronc")
        n = 4 if v != 2 else 5
        for i in range(n):
            if v == 3 and i == 1:
                continue
            t = i / n
            w = larg * (1 - 0.72 * t)
            y0 = 0.2 * h + 0.68 * h * t
            b.boxc((0, y0 + 0.11 * h, 0), (w, 0.22 * h, w), shade(col, 1 + 0.05 * (i % 2)), yaw=45 * (i % 2),
                   studs="top", name="Etage", collide=i == 0)
        b.boxc((0, 0.93 * h, 0), (0.08 * h, 0.16 * h, 0.08 * h), col, name="Cime", **DECO)
        if v == 3:
            for k in (-1, 1):
                _poutre(b, (0, 0.38 * h, 0), (k * 0.2 * h, 0.5 * h, 0.05 * h), 0.05 * h, c("bois_mort"), name="Branche", **DECO)
    return {"emprise": (larg, larg), "hauteur": h}


def rocher(b, variant: int = 0, taille: float = 4.0) -> dict:
    """Rocher sombre de 2 à 4 blocs inclinés, mousse en v0 et v2. ≤ 6 pièces."""
    v = variant % 4
    rng = _rng(v, 37)
    s = taille
    with b.group("Rocher"):
        b.boxc((0, 0.35 * s, 0), (1.0 * s, 0.7 * s, 0.8 * s), vary("roche_noire", rng, 0.1), yaw=float(rng.uniform(0, 90)),
               studs="top", name="Bloc")
        b.part("block", (0.7 * s, 0.6 * s, 0.6 * s), (0.25 * s, 0.75 * s, 0.1 * s), rot_z(float(rng.uniform(-20, 20))),
               vary("basalte_clair", rng, 0.1), studs="top", name="Bloc")
        if v in (1, 3):
            b.boxc((-0.55 * s, 0.25 * s, 0.3 * s), (0.5 * s, 0.5 * s, 0.5 * s), vary("basalte", rng, 0.1),
                   yaw=float(rng.uniform(0, 90)), studs="top", name="Bloc")
        if v in (0, 2):
            b.boxc((0.15 * s, 1.07 * s, 0.1 * s), (0.5 * s, 0.1 * s, 0.4 * s), c("mousse"), yaw=10, name="Mousse", **FIN)
    return {"emprise": (1.4 * s, 1.2 * s), "hauteur": 1.1 * s}


def epines_racines(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Épines de racines noires qui percent le sol (approche du royaume démoniaque), fente violette à leur pied.
    v0 : trois épines ; v1 : cinq épines en couronne ; v2 : une grande épine courbe ; v3 : fente cramoisie."""
    v = variant % 4
    s = taille
    rng = _rng(v, 41)
    lueur = c("lueur_cramoisie") if v == 3 else c("lueur_violette")
    with b.group("Epines"):
        b.boxc((0, 0.3 * s, 0), (3.2 * s, 0.6 * s, 2.6 * s), c("racine"), yaw=15, studs="top", name="Butte")
        b.boxc((0.2 * s, 0.65 * s, -0.1 * s), (2.2 * s, 0.1 * s, 0.3 * s), lueur, yaw=-20, name="Fente", **NEON)
        n = (3, 5, 1, 4)[v]
        for i in range(n):
            a = 2 * math.pi * i / n + float(rng.uniform(-0.3, 0.3))
            r = 0.0 if n == 1 else 0.9 * s
            base = np.array([r * math.cos(a), 0.3 * s, r * math.sin(a)])
            hh = s * (5.5 if n == 1 else float(rng.uniform(2.6, 4.2)))
            mid = base + np.array([0.35 * hh * math.cos(a) * 0.5, hh * 0.55, 0.35 * hh * math.sin(a) * 0.5])
            tip = mid + np.array([0.3 * hh * math.cos(a) * (1.4 if n == 1 else 0.6), hh * 0.45, 0.3 * hh * math.sin(a)])
            _poutre(b, base, mid, 0.75 * s * (1.3 if n == 1 else 1.0), c("racine"), name="Epine")
            _poutre(b, mid, tip, 0.4 * s * (1.3 if n == 1 else 1.0), c("epine"), name="Pointe", **DECO)
    return {"emprise": (3.4 * s, 3.0 * s), "hauteur": (5.8 if v == 2 else 4.4) * s}

