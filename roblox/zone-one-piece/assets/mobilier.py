"""Mobilier de la zone One Piece (port pirate et campagne aux moulins), en style stud.

Petits objets du thème, chacun ≤ 40 pièces : guirlandes de fanions et leurs mâts, mâts de vigie, lanternes
de quai, tonneaux, caisses, bittes d'amarrage, cordages, canons, ancres, coffres au trésor, bouées, filets de
pêche, panneaux à texte, bancs, clôtures de bois, vaches, bottes de foin, crabes, mouettes, viande sur l'os
géante, barre de navire, coquillages et pavillon pirate générique.

Conventions (voir CONVENTIONS.md) : origine au centre de l'emprise, y = 0 au sol, avant vers -Z local.
Les petits détails n'ont pas de collision. Les autres modules peuvent importer ces fonctions
(`from assets.mobilier import drapeau_pirate, bouee, cordage, guirlande_fanions, ...`).
"""

from __future__ import annotations

import math

import numpy as np

from kit import rot_x, rot_y, rot_z, shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------


def _segment(b, a, bb, rayon: float, col, name: str = "Corde", collide: bool = False, shadow: bool = False) -> None:
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
           collide=collide, shadow=shadow, name=name)


def _chainette(p0, p1, creux: float, n: int) -> list:
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    pts = []
    for i in range(n + 1):
        t = i / n
        p = p0 + (p1 - p0) * t
        p[1] -= creux * 4 * t * (1 - t)
        pts.append(p)
    return pts


def _bloc_tourne(b, centre, taille, deg_z: float, col, **kw):
    """Bloc tourné autour de l'axe Z local (dans le plan x-y : rayons, bras d'ancre, os croisés)."""
    return b.part("block", taille, centre, rot_z(deg_z), col, **kw)


def cordage(b, p0, p1, creux: float = 0.8, n: int = 6, rayon: float = 0.14, variant: int = 0) -> dict:
    """Corde affaissée entre deux points (rambardes de pontons, anneau de la place)."""
    col = (c("corde"), c("corde_fonce"), c("filet"))[variant % 3]
    pts = _chainette(p0, p1, creux, n)
    with b.group("Cordage"):
        for a, bb in zip(pts, pts[1:]):
            _segment(b, a, bb, rayon, col)
    return {"segments": n}


# ---------------------------------------------------------------------------
# Fanions, mâts, pavillon
# ---------------------------------------------------------------------------

PALETTES_FANIONS = [
    ("rouge", "jaune", "bleu", "blanc", "turquoise", "orange"),
    ("rouge", "blanc"),
    ("jaune", "turquoise", "rose", "bleu", "blanc"),
]


def _fanion(b, p, u, larg: float, haut: float, col, ep: float = 0.16) -> None:
    """Fanion triangulaire pointe en bas : deux coins (triangles rectangles) dos à dos, plan vertical le long de u."""
    u = np.asarray(u, float)
    u = u / (np.linalg.norm(u) or 1)
    for s in (-1, 1):
        zl = -s * u                      # Z local : de l'extérieur vers l'axe du fanion
        yl = np.array([0.0, -1.0, 0.0])  # Y local vers le bas : le bord plein du coin est en haut
        xl = np.cross(yl, zl)
        R = np.column_stack([xl, yl, zl])
        centre = np.asarray(p, float) + s * u * larg / 4 + np.array([0.0, -haut / 2, 0.0])
        b.part("wedge", (ep, haut, larg / 2), centre, R, col, collide=False, name="Fanion")


def guirlande_fanions(b, p0, p1, n: int = 12, creux: float = 2.5, variant: int = 0, larg: float = 2.2,
                      haut: float = 2.6) -> dict:
    """Guirlande de fanions colorés entre deux points (corde affaissée, fanions dessous).

    Au-dessus du couloir, la corde doit passer à y ≥ 30 + creux + haut (H_GUIRLANDE = 37 dans zone.py)."""
    pts = _chainette(p0, p1, creux, 10)
    pal = PALETTES_FANIONS[variant % len(PALETTES_FANIONS)]
    p0a, p1a = np.asarray(p0, float), np.asarray(p1, float)
    d = p1a - p0a
    u = np.array([d[0], 0.0, d[2]])
    with b.group("Fanions"):
        for a, bb in zip(pts, pts[1:]):
            _segment(b, a, bb, 0.1, c("corde_fonce"), name="Corde")
        for i in range(n):
            t = (i + 0.5) / n
            p = p0a + d * t
            p[1] -= creux * 4 * t * (1 - t) + 0.05
            _fanion(b, p, u, larg, haut, c(pal[i % len(pal)]))
    return {"fanions": n, "point_bas": float(min(p0a[1], p1a[1]) - creux - haut)}


def drapeau_pirate(b, variant: int = 0, hauteur: float = 8.0, largeur: float = 6.0, mat: bool = True) -> dict:
    """Pavillon pirate générique (tête de mort en pixels, sans chapeau ni emblème précis) sur une hampe.

    Le drapeau est dans le plan x-y, il flotte vers +X local depuis la hampe (x = 0). variant 0 : crâne et os
    croisés ; 1 : crâne seul sur fond rouge ; 2 : crâne et sabres croisés stylisés (simples barres)."""
    fond = c("voile_rouge") if variant % 3 == 1 else c("drapeau_noir")
    blanc = c("tete_mort")
    H = hauteur
    L, Hd = largeur, largeur * 0.66
    y0 = H - Hd - 0.3
    with b.group("Pavillon"):
        if mat:
            b.cyl((0, H / 2, 0), 0.18, H, c("bois_fonce"), name="Hampe")
            b.ball((0, H + 0.2, 0), 0.3, c("or"), collide=False, name="Pomme")
        b.box((0.2, y0, -0.08), (0.2 + L, y0 + Hd, 0.08), fond, collide=False, name="Drapeau")
        cx, cy = 0.2 + L / 2, y0 + Hd * 0.56
        s = L / 6.0
        # os croisés (ou sabres) derrière le crâne : barres qui traversent le drapeau (visibles des deux côtés)
        if variant % 3 != 1:
            col_os = blanc if variant % 3 == 0 else c("metal")
            for ang in (32, -32):
                _bloc_tourne(b, (cx, cy - 0.35 * s, 0), (4.6 * s, 0.42 * s, 0.24), ang, col_os, collide=False, name="Os")
        b.box((cx - 1.0 * s, cy - 0.45 * s, -0.14), (cx + 1.0 * s, cy + 1.05 * s, 0.14), blanc, collide=False, name="Crane")
        b.box((cx - 0.6 * s, cy - 0.95 * s, -0.14), (cx + 0.6 * s, cy - 0.45 * s, 0.14), blanc, collide=False, name="Machoire")
        for dx in (-0.48, 0.48):
            b.box((cx + dx * s - 0.3 * s, cy + 0.05 * s, -0.2), (cx + dx * s + 0.3 * s, cy + 0.6 * s, 0.2), fond,
                  collide=False, name="Orbite")
        b.box((cx - 0.12 * s, cy - 0.35 * s, -0.2), (cx + 0.12 * s, cy - 0.05 * s, 0.2), fond, collide=False, name="Nez")
    return {"emprise": (L + 0.5, 0.5), "hauteur": H + 0.5}


def mat_guirlande(b, hauteur: float = 40.0, variant: int = 0) -> dict:
    """Mât de bois planté sur un socle de caisses, qui porte les guirlandes de fanions (attache à hauteur - 1).

    Mince (0,6 de rayon) pour tenir dans un trottoir ; vergue courte selon Z (jamais vers le couloir)."""
    bois = (c("bois_fonce"), c("bois"), c("coque_rouge"))[variant % 3]
    with b.group("MatGuirlande"):
        b.box((-1.1, 0, -1.1), (1.1, 1.6, 1.1), c("bois_pale"), studs="top", name="Caisse")
        b.box((-1.18, 0.6, -1.18), (1.18, 1.0, 1.18), c("bois"), collide=False, name="Cerclage")
        b.cyl((0, 1.6 + (hauteur - 1.6) / 2, 0), 0.55, hauteur - 1.6, bois, name="Mat")
        for y in (3.2, hauteur - 4):
            b.cyl((0, y, 0), 0.68, 0.7, c("corde"), collide=False, name="Ligature")
        b.box((-0.25, hauteur - 5.2, -1.8), (0.25, hauteur - 4.7, 1.8), bois, collide=False, name="Vergue")
        b.ball((0, hauteur + 0.25, 0), 0.5, c("or"), collide=False, name="Pomme")
        # petite flamme en haut (deux fanions) qui flotte selon Z
        _fanion(b, (0, hauteur - 0.2, -1.45), (0, 0, 1), 1.8, 2.2, c(("rouge", "jaune", "turquoise")[variant % 3]))
    return {"emprise": (2.2, 2.2), "hauteur": hauteur + 0.75, "attache": hauteur - 1.0}


def mat_vigie(b, hauteur: float = 34.0, variant: int = 0) -> dict:
    """Grand mât de navire planté sur la place : vigie (nid-de-pie), vergue à voile ferlée, haubans, pavillon."""
    H = hauteur
    bois, bois_f = c("bois"), c("bois_fonce")
    with b.group("MatVigie"):
        b.box((-2.5, 0, -2.5), (2.5, 1.2, 2.5), c("pierre_fonce"), studs="top", name="Socle")
        b.cyl((0, 1.6, 0), 1.6, 0.8, c("corde"), collide=False, name="RouleauCorde")
        b.cyl((0, 1.2 + (H - 1.2) / 2, 0), 0.85, H - 1.2, bois, name="Mat")
        for y in (6.0, 14.0):
            b.cyl((0, y, 0), 0.98, 0.6, bois_f, collide=False, name="Cercle")
        # vergue et voile ferlée (selon X local : à placer avec |x| ≥ 44)
        yv = H * 0.62
        b.cyl((0, yv, 0), 0.4, 11, bois_f, axis="x", collide=False, name="Vergue")
        b.cyl((0, yv - 0.7, 0.05), 0.65, 9.6, c("voile"), axis="x", collide=False, name="VoileFerlee")
        # nid-de-pie
        yn = H * 0.8
        b.cyl((0, yn, 0), 2.3, 0.5, bois_f, name="Plancher")
        b.cyl((0, yn + 1.0, 0), 2.1, 1.5, bois, collide=False, name="Nid")
        b.cyl((0, yn + 1.85, 0), 2.25, 0.3, bois_f, collide=False, name="Bord")
        # haubans (échelles de corde) du socle au nid
        for sx in (-1, 1):
            for sz in (-0.6, 0.6):
                _segment(b, (sx * 2.3, 1.2, sz), (sx * 1.9, yn - 0.2, sz * 0.5), 0.1, c("corde_fonce"), name="Hauban")
            for k in range(3):
                y = 1.2 + (yn - 1.4) * (k + 1) / 4
                x = sx * (2.3 - 0.4 * (k + 1) / 4)
                b.box((x - 0.08, y - 0.08, -0.7), (x + 0.08, y + 0.08, 0.7), c("corde_fonce"), collide=False, shadow=False, name="Enflechure")
        # mât de hune et pavillon
        b.cyl((0, H + 2.5, 0), 0.45, 5.0, bois_f, name="Hune")
        with b.at((0, H - 1.0, 0)):
            drapeau_pirate(b, variant=variant, hauteur=6.0, largeur=5.0, mat=False)
        b.ball((0, H + 5.2, 0), 0.5, c("or"), collide=False, name="Pomme")
    return {"emprise": (11, 5), "hauteur": H + 5.7}


# ---------------------------------------------------------------------------
# Lumières
# ---------------------------------------------------------------------------


def _lanterne(b, x, y, z, cadre, taille: float = 1.0) -> None:
    """Lanterne de navire : cage carrée vitrée éclairée, chapeau pyramidal, anneau."""
    s = taille
    b.box((x - 0.75 * s, y, z - 0.75 * s), (x + 0.75 * s, y + 0.25 * s, z + 0.75 * s), cadre, collide=False, name="Fond")
    b.box((x - 0.6 * s, y + 0.25 * s, z - 0.6 * s), (x + 0.6 * s, y + 1.65 * s, z + 0.6 * s), c("lanterne"), material="Neon",
          collide=False, shadow=False, name="Verre")
    for sx in (-0.62, 0.62):
        for sz in (-0.62, 0.62):
            b.box((x + sx * s - 0.1 * s, y + 0.25 * s, z + sz * s - 0.1 * s), (x + sx * s + 0.1 * s, y + 1.65 * s, z + sz * s + 0.1 * s),
                  cadre, collide=False, name="Montant")
    b.wedge((x - 0.85 * s, y + 1.65 * s, z - 0.85 * s), (x + 0.85 * s, y + 2.25 * s, z), cadre, down="-z", collide=False, name="Chapeau")
    b.wedge((x - 0.85 * s, y + 1.65 * s, z), (x + 0.85 * s, y + 2.25 * s, z + 0.85 * s), cadre, down="+z", collide=False, name="Chapeau")
    b.cyl((x, y + 2.45 * s, z), 0.3 * s, 0.4 * s, cadre, axis="z", collide=False, name="Anneau")


def lanterne_quai(b, variant: int = 0) -> dict:
    """Lanterne de quai. 0 : poteau à lanterne ; 1 : potence (lanterne suspendue vers l'avant) ; 2 : basse sur bitte."""
    cadre = c("fer")
    with b.group("LanterneQuai"):
        if variant % 3 == 2:
            b.cyl((0, 0.9, 0), 0.75, 1.8, c("bois_fonce"), name="Pieu")
            b.cyl((0, 1.0, 0), 0.82, 0.4, c("corde"), collide=False, name="Corde")
            _lanterne(b, 0, 1.8, 0, cadre, 0.9)
            return {"emprise": (1.6, 1.6), "hauteur": 4.1}
        b.box((-0.9, 0, -0.9), (0.9, 0.8, 0.9), c("pierre_fonce"), studs="top", name="Socle")
        if variant % 3 == 0:
            b.box((-0.35, 0.8, -0.35), (0.35, 8.6, 0.35), c("bois_fonce"), name="Poteau")
            b.box((-0.55, 8.6, -0.55), (0.55, 8.9, 0.55), cadre, name="Plateau")
            _lanterne(b, 0, 8.9, 0, cadre)
            return {"emprise": (1.8, 1.8), "hauteur": 11.5}
        b.box((-0.35, 0.8, -0.35), (0.35, 10.4, 0.35), c("bois_fonce"), name="Poteau")
        b.box((-0.22, 9.6, -2.7), (0.22, 10.1, 0.35), c("bois_fonce"), collide=False, name="Potence")
        _segment(b, (0, 8.2, -0.3), (0, 9.7, -1.8), 0.1, c("bois_fonce"), name="Jambe")
        b.box((-0.05, 8.9, -2.25), (0.05, 9.6, -2.15), cadre, collide=False, name="Chainette")
        _lanterne(b, 0, 6.6, -2.2, cadre)
    return {"emprise": (1.8, 3.6), "hauteur": 10.4}


# ---------------------------------------------------------------------------
# Tonneaux, caisses, amarrage
# ---------------------------------------------------------------------------


def _tonneau_debout(b, x, y, z, r: float = 1.05, h: float = 2.8, col=None) -> None:
    col = col or c("bois")
    b.cyl((x, y + h / 2, z), r, h, col, name="Tonneau")
    b.cyl((x, y + h / 2, z), r + 0.08, h * 0.45, shade(col, 1.12), collide=False, name="Ventre")
    for yy in (0.35, h - 0.35):
        b.cyl((x, y + yy, z), r + 0.06, 0.22, c("fer"), collide=False, name="Cercle")
    b.cyl((x, y + h + 0.03, z), r * 0.85, 0.08, c("bois_pale"), collide=False, name="Couvercle")


def _tonneau_couche(b, x, y, z, r: float = 1.05, h: float = 2.8, col=None) -> None:
    """Tonneau couché selon X, posé à la hauteur y."""
    col = col or c("bois")
    b.cyl((x, y + r, z), r, h, col, axis="x", name="Tonneau")
    b.cyl((x, y + r, z), r + 0.08, h * 0.45, shade(col, 1.12), axis="x", collide=False, name="Ventre")
    for dx in (-h / 2 + 0.35, h / 2 - 0.35):
        b.cyl((x + dx, y + r, z), r + 0.06, 0.22, c("fer"), axis="x", collide=False, name="Cercle")


def tonneaux(b, variant: int = 0) -> dict:
    """Groupe de tonneaux. 0 : trois debout ; 1 : deux debout et un couché dessus ; 2 : pyramide couchée."""
    rng = b.rng
    with b.group("Tonneaux"):
        v = variant % 3
        if v == 0:
            for (x, z) in ((-1.15, 0.2), (1.15, 0.4), (0.0, -1.5)):
                _tonneau_debout(b, x, 0, z, col=vary("bois", rng, 0.08))
            return {"emprise": (4.4, 4.2), "hauteur": 2.9}
        if v == 1:
            for x in (-1.15, 1.15):
                _tonneau_debout(b, x, 0, 0, col=vary("bois_clair", rng, 0.06))
            _tonneau_couche(b, 0, 2.86, 0, col=c("bois"))
            return {"emprise": (4.4, 2.4), "hauteur": 5.0}
        for x in (-1.1, 1.1):
            _tonneau_couche(b, 0, 0, x, r=1.05, h=2.8, col=vary("bois", rng, 0.08))
        _tonneau_couche(b, 0, 1.75, 0, r=1.05, h=2.8, col=c("bois_clair"))
        b.box((-1.2, 0, -2.3), (1.2, 0.4, -1.9), c("bois_fonce"), collide=False, name="Cale")
    return {"emprise": (3.0, 4.4), "hauteur": 3.9}


def caisses(b, variant: int = 0) -> dict:
    """Pile de caisses à claire-voie. 0 : trois caisses ; 1 : deux caisses et un sac ; 2 : caisses de mandarines."""
    rng = b.rng
    pile = [((-1.25, 0, 0.1), 2.3), ((1.25, 0, 0.3), 2.1), ((-0.3, 2.3, 0.2), 1.9)]
    with b.group("Caisses"):
        v = variant % 3
        for k, ((x, y, z), s) in enumerate(pile[: 3 if v == 0 else 2]):
            yaw = float(rng.uniform(-10, 10))
            col = vary("bois_pale", rng, 0.05)
            b.boxc((x, y + s / 2, z), (s, s, s), col, yaw=yaw, studs="top", name="Caisse")
            b.boxc((x, y + s / 2, z), (s + 0.14, s * 0.24, s + 0.14), c("bois"), yaw=yaw, collide=False, name="Cerclage")
            b.boxc((x, y + s / 2, z), (s * 0.24, s + 0.14, s + 0.14), c("bois"), yaw=yaw, collide=False, name="Montant")
            if v == 2:
                for i in range(3):
                    for j in range(2):
                        b.ball((x - s * 0.28 + i * s * 0.28, y + s + 0.25, z - s * 0.2 + j * s * 0.4), 0.42, c("agrume"),
                               collide=False, name="Mandarine")
        if v == 1:
            b.box((-0.9, 2.3, -0.5), (0.5, 3.3, 0.7), c("voile_ombre"), collide=False, name="Sac")
            b.box((-0.6, 3.3, -0.25), (0.2, 3.7, 0.45), c("voile_ombre"), collide=False, name="Sac")
            b.box((-0.65, 3.2, -0.3), (0.25, 3.35, 0.5), c("corde"), collide=False, name="Lien")
    return {"emprise": (5.0, 3.0), "hauteur": 4.3}


def bitte(b, variant: int = 0) -> dict:
    """Bitte d'amarrage. 0 : fonte noire avec corde ; 1 : pieu de bois et rouleau de corde ; 2 : bittes doubles."""
    with b.group("Bitte"):
        v = variant % 3
        if v == 0:
            b.cyl((0, 0.25, 0), 0.95, 0.5, c("fer"), name="Base")
            b.cyl((0, 1.25, 0), 0.62, 1.6, c("metal_fonce"), name="Fut")
            b.cyl((0, 2.2, 0), 0.88, 0.35, c("metal_fonce"), studs="top", name="Tete")
            b.cyl((0, 1.0, 0), 0.72, 0.35, c("corde"), collide=False, name="Corde")
            return {"emprise": (1.9, 1.9), "hauteur": 2.4}
        if v == 1:
            b.cyl((0, 1.8, 0), 0.7, 3.6, c("bois_fonce"), name="Pieu")
            b.cyl((0, 3.65, 0), 0.6, 0.15, c("bois_flotte"), collide=False, name="Tete")
            b.cyl((0, 0.25, -1.3), 0.9, 0.5, c("corde"), collide=False, name="Rouleau")
            b.cyl((0, 0.55, -1.3), 0.6, 0.2, c("corde_fonce"), collide=False, name="Rouleau")
            b.cyl((0, 2.6, 0), 0.78, 0.3, c("corde"), collide=False, name="Corde")
            return {"emprise": (1.8, 3.2), "hauteur": 3.7}
        b.box((-1.6, 0, -0.6), (1.6, 0.4, 0.6), c("fer"), name="Semelle")
        for x in (-1.0, 1.0):
            b.cyl((x, 1.2, 0), 0.5, 1.6, c("metal_fonce"), name="Bitte")
            b.cyl((x, 2.05, 0), 0.62, 0.25, c("metal_fonce"), collide=False, name="Tete")
        b.box((-1.0, 1.3, -0.2), (1.0, 1.6, 0.2), c("corde"), collide=False, name="Tour")
    return {"emprise": (3.2, 1.2), "hauteur": 2.2}


# ---------------------------------------------------------------------------
# Armes et trésors (génériques)
# ---------------------------------------------------------------------------


def canon(b, variant: int = 0) -> dict:
    """Canon sur affût de bois à quatre roues, bouche vers -Z ; variante 1 : avec pyramide de boulets ;
    variante 2 : affût rouge."""
    affut = c("coque_rouge") if variant % 3 == 2 else c("bois")
    fer = c("metal_fonce")
    with b.group("Canon"):
        for x in (-0.75, 0.75):
            b.box((x - 0.2, 0.55, -1.4), (x + 0.2, 1.75, 1.5), affut, name="Flasque")
        b.box((-0.75, 0.55, -1.0), (0.75, 0.95, 1.4), shade(affut, 0.85), name="Semelle")
        for z, r in ((-0.95, 0.62), (1.05, 0.55)):
            for x in (-1.1, 1.1):
                b.cyl((x, r, z), r, 0.3, c("bois_fonce"), axis="x", name="Roue")
            b.cyl((0, r, z), 0.14, 2.6, c("fer"), axis="x", collide=False, name="Essieu")
        R = rot_x(7) @ rot_y(90)
        b.part("cyl", (4.6, 1.15, 1.15), (0, 2.0, -0.5), R, fer, name="Fut")
        b.part("cyl", (0.35, 1.45, 1.45), (0, 2.27, -2.6), R, fer, collide=False, name="Bouche")
        b.part("cyl", (0.3, 1.4, 1.4), (0, 1.88, 0.4), R, fer, collide=False, name="Renfort")
        b.ball((0, 1.75, 1.95), 0.38, fer, collide=False, name="Bouton")
        if variant % 3 == 1:
            for (x, y, z) in ((2.3, 0.4, -0.5), (3.1, 0.4, -0.5), (2.7, 0.4, 0.2), (2.7, 1.05, -0.25)):
                b.ball((x, y, z), 0.4, c("noir"), collide=False, name="Boulet")
    return {"emprise": (3.0 if variant % 3 != 1 else 7.0, 5.2), "hauteur": 2.9}


def _emettre(b, pieces, M, t) -> None:
    """Pose une liste (forme, taille, centre, rotation, couleur, kw) après rotation M et translation t."""
    for forme, taille, centre, R, col, kw in pieces:
        b.part(forme, taille, M @ np.asarray(centre, float) + np.asarray(t, float), M @ R, col, **kw)


def ancre(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Grande ancre marine. 0 : debout sur un socle de pierre ; 1 : avec chaîne enroulée ; 2 : penchée contre
    un rocher (inclinaison vers +Z)."""
    s = taille
    col = c("metal_fonce") if variant % 3 != 1 else c("fer")
    I = np.eye(3)
    nd = dict(collide=False)
    P = []
    P.append(("block", (0.9 * s, 8.4 * s, 0.9 * s), (0, 5.2 * s, 0), I, col, {"name": "Verge"}))
    P.append(("block", (5.4 * s, 0.7 * s, 0.7 * s), (0, 8.0 * s, 0), I, c("bois_fonce"), {"name": "Jas"}))
    for (dx, dy, w, h) in ((0, 10.6, 1.9, 0.4), (0, 9.2, 1.9, 0.4), (-0.75, 9.9, 0.4, 1.8), (0.75, 9.9, 0.4, 1.8)):
        P.append(("block", (w * s, h * s, 0.4 * s), (dx * s, dy * s, 0), I, col, {"name": "Organeau", **nd}))
    P.append(("block", (2.2 * s, 1.0 * s, 1.0 * s), (0, 1.3 * s, 0), I, col, {"name": "Diamant"}))
    for sx in (-1, 1):
        ang = 32 if sx > 0 else -32
        P.append(("block", (3.6 * s, 0.8 * s, 0.8 * s), (sx * 1.9 * s, 2.15 * s, 0), rot_z(ang), col, {"name": "Bras"}))
        P.append(("block", (1.5 * s, 1.5 * s, 0.5 * s), (sx * 3.35 * s, 3.25 * s, 0), rot_z(45), col, {"name": "Patte"}))
    v = variant % 3
    with b.group("Ancre"):
        if v == 2:
            M = rot_x(16)
            _emettre(b, P, M, (0, -0.75 * s, -0.4 * s))
            b.box((-2.2 * s, 0, 1.2 * s), (2.2 * s, 3.0 * s, 3.6 * s), c("roche"), studs="top", name="Rocher")
            b.box((-1.4 * s, 3.0 * s, 1.8 * s), (1.6 * s, 4.2 * s, 3.4 * s), c("roche_claire"), studs="top", name="Rocher")
            return {"emprise": (7.4 * s, 4.8 * s), "hauteur": 11.0 * s}
        _emettre(b, P, I, (0, -0.2 * s, 0))
        b.box((-3.0 * s, 0, -1.6 * s), (3.0 * s, 0.6 * s, 1.6 * s), c("pierre_fonce"), studs="top", name="Socle")
        if v == 1:
            for k in range(5):
                a = k * 72
                x, z = 2.4 * s + 1.0 * s * math.cos(math.radians(a)), 0.6 * s + 0.6 * s * math.sin(math.radians(a))
                b.boxc((x, 0.85 * s, z), (0.8 * s, 0.5 * s, 0.35 * s), c("fer"), yaw=a, collide=False, name="Maillon")
            for k in range(3):
                b.boxc((0.5 * s, (1.4 + k * 0.7) * s, 0.55 * s), (0.35 * s, 0.6 * s, 0.6 * s), c("fer"), collide=False, name="Maillon")
    return {"emprise": (7.4 * s, 3.2 * s), "hauteur": 11.2 * s}


def coffre_tresor(b, variant: int = 0) -> dict:
    """Coffre au trésor. 0 : ouvert et débordant d'or et de gemmes ; 1 : fermé, serrure dorée ; 2 : ouvert, pièces
    renversées devant."""
    bois = c("coque_rouge") if variant % 3 == 1 else c("bois")
    laiton = c("laiton")
    gold = dict(reflectance=0.2, collide=False)
    with b.group("Coffre"):
        b.box((-1.7, 0, -1.1), (1.7, 1.7, 1.1), bois, name="Caisse")
        for x in (-1.15, 1.15):
            b.box((x - 0.18, -0.0, -1.18), (x + 0.18, 1.78, 1.18), laiton, collide=False, name="Ferrure")
        b.box((-1.78, 0.0, -1.18), (1.78, 0.25, 1.18), laiton, collide=False, name="Pied")
        if variant % 3 == 1:
            b.cyl((0, 1.7, 0), 1.1, 3.4, bois, axis="x", name="Couvercle")
            for x in (-1.15, 1.15):
                b.cyl((x, 1.7, 0), 1.17, 0.36, laiton, axis="x", collide=False, name="Ferrure")
            b.box((-0.35, 1.0, -1.25), (0.35, 1.9, -1.1), c("or"), collide=False, name="Serrure")
            return {"emprise": (3.6, 2.4), "hauteur": 2.8}
        # couvercle ouvert, rabattu vers l'arrière
        b.part("block", (3.4, 0.5, 2.2), (0, 2.75, 1.45), rot_x(-72), bois, collide=False, name="Couvercle")
        b.part("block", (3.5, 0.3, 0.36), (0, 2.75, 1.6), rot_x(-72), laiton, collide=False, name="Ferrure")
        b.box((-1.5, 1.7, -0.9), (1.5, 2.1, 0.9), c("or"), name="Or", **{k: v for k, v in gold.items() if k != "collide"})
        for (x, z, r) in ((-0.7, -0.2, 0.55), (0.5, 0.1, 0.6), (0.0, -0.5, 0.45), (1.0, -0.4, 0.4)):
            b.ball((x, 2.15, z), r, c("or_clair") if r < 0.5 else c("or"), name="Pieces", **gold)
        for (x, z, col) in ((-0.2, 0.3, "rubis"), (0.9, 0.4, "saphir"), (-1.0, 0.3, "emeraude_gemme")):
            b.ball((x, 2.55, z), 0.3, c(col), material="Glass", collide=False, name="Gemme")
        if variant % 3 == 2:
            for (x, z) in ((-1.2, -1.7), (-0.3, -2.1), (0.6, -1.6), (1.4, -2.3), (0.1, -2.9)):
                b.cyl((x, 0.06, z), 0.38, 0.12, c("or"), axis="y", name="Piece", **gold)
            b.box((-1.9, 0, -2.0), (-1.3, 1.2, -1.4), c("or"), name="Lingot", **gold)
    return {"emprise": (3.8, 3.4), "hauteur": 3.6}


def barre_navire(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Barre à roue de navire sur un piédestal (roue dans le plan x-y, face vers -Z)."""
    s = taille
    bois = (c("bois"), c("coque_rouge"), c("bois_fonce"))[variant % 3]
    yc = 3.6 * s
    R = 1.8 * s
    with b.group("Barre"):
        b.box((-1.0 * s, 0, -1.0 * s), (1.0 * s, 0.6 * s, 1.0 * s), c("pierre_fonce"), studs="top", name="Socle")
        b.box((-0.45 * s, 0.6 * s, 0.1 * s), (0.45 * s, yc - 0.2 * s, 1.0 * s), bois, name="Pied")
        b.cyl((0, yc, -0.1 * s), 0.5 * s, 0.7 * s, c("laiton"), axis="z", name="Moyeu")
        L = 2 * R * math.tan(math.radians(22.5)) + 0.25 * s
        for k in range(8):
            a = math.radians(k * 45 + 22.5)
            _bloc_tourne(b, (R * math.cos(a), yc + R * math.sin(a), -0.1 * s), (L, 0.32 * s, 0.32 * s),
                         k * 45 + 22.5 + 90, bois, collide=False, name="Jante")
        for k in range(4):
            _bloc_tourne(b, (0, yc, -0.1 * s), (2 * R + 1.6 * s, 0.22 * s, 0.22 * s), k * 45 + 22.5, c("bois_pale"),
                         collide=False, name="Rayon")
    return {"emprise": (2 * R + 1.6 * s, 2.0 * s), "hauteur": yc + R + 0.8 * s}


def bouee(b, variant: int = 0, rayon: float = 1.2) -> dict:
    """Bouée de sauvetage rouge et blanche (anneau octogonal dans le plan x-y, face -Z).
    0 : sur un poteau ; 1 : seule, centre à y = rayon + 0,3 (à accrocher à un mur ou un pilier) ; 2 : couchée au sol."""
    R, t = rayon, rayon * 0.42
    L = 2 * R * math.tan(math.radians(22.5)) + t * 0.42
    v = variant % 3
    with b.group("Bouee"):
        if v == 0:
            b.box((-0.25, 0, 0.15), (0.25, 4.6, 0.65), c("bois_fonce"), name="Poteau")
            yc = 3.2
        else:
            yc = R + 0.3
        for k in range(8):
            a = math.radians(k * 45 + 22.5)
            col = c("rouge") if k % 2 == 0 else c("blanc")
            if v == 2:
                b.boxc((R * math.cos(a), t * 0.4, R * math.sin(a)), (L, t * 0.8, t), col, yaw=-(k * 45 + 22.5 + 90),
                       collide=False, name="Bouee")
            else:
                _bloc_tourne(b, (R * math.cos(a), yc + R * math.sin(a), -0.1), (L, t, t * 0.8), k * 45 + 22.5 + 90, col,
                             collide=False, name="Bouee")
        if v != 2:
            _segment(b, (-R * 0.7, yc + R * 0.7, -0.25), (R * 0.7, yc + R * 0.7, -0.25), 0.07, c("corde"), name="Filin")
    return {"emprise": (2 * R + t, 1.0), "hauteur": (4.6 if v == 0 else yc + R + t / 2)}


# ---------------------------------------------------------------------------
# Pêche, panneaux, bancs, clôtures
# ---------------------------------------------------------------------------


def filet_peche(b, variant: int = 0, largeur: float = 6.0) -> dict:
    """Filet de pêche qui sèche entre deux perches (maille de cordelettes, flotteurs orange et blancs).
    variante 2 : filet en tas avec flotteurs et une nasse."""
    col = c("filet")
    with b.group("Filet"):
        if variant % 3 == 2:
            b.box((-2.0, 0, -1.4), (2.0, 0.7, 1.4), col, collide=False, name="Tas")
            b.box((-1.3, 0.7, -0.9), (1.5, 1.3, 1.0), shade(col, 1.1), collide=False, name="Tas")
            for (x, z, k) in ((-1.6, -1.2, 0), (0.3, -1.3, 1), (1.7, -0.5, 0), (-0.4, 0.8, 1)):
                b.ball((x, 0.75 if k else 0.5, z), 0.4, c("orange") if k else c("blanc"), collide=False, name="Flotteur")
            b.cyl((2.9, 0.9, 0.6), 0.9, 1.8, c("bois_pale"), axis="z", collide=False, name="Nasse")
            b.cyl((2.9, 0.9, 0.6), 0.96, 0.25, c("bois"), axis="z", collide=False, name="Cercle")
            return {"emprise": (6.0, 3.0), "hauteur": 1.8}
        W = largeur
        h0, h1 = 1.2, 5.6
        for x in (-W / 2, W / 2):
            b.cyl((x, 3.3, 0), 0.22, 6.6, c("bois_flotte"), name="Perche")
            b.box((x - 0.5, 0, -0.5), (x + 0.5, 0.4, 0.5), c("pierre_fonce"), collide=False, name="Pierre")
        _segment(b, (-W / 2, h1 + 0.2, 0), (W / 2, h1 + 0.2, 0), 0.08, c("corde_fonce"), name="Filin")
        n_v = int(W // 1.0) + 1
        for i in range(1, n_v - 1):
            x = -W / 2 + i * W / (n_v - 1)
            creux = 0.6 * math.sin(math.pi * i / (n_v - 1))
            b.box((x - 0.05, h0 + creux, -0.05), (x + 0.05, h1, 0.05), col, collide=False, shadow=False, name="Maille")
        for k in range(5):
            y = h0 + 0.4 + k * (h1 - h0 - 0.6) / 4
            b.box((-W / 2 + 0.2, y - 0.05, -0.06), (W / 2 - 0.2, y + 0.05, 0.06), col, collide=False, shadow=False, name="Maille")
        for i in range(4):
            x = -W / 2 + 0.9 + i * (W - 1.8) / 3
            b.ball((x, h1 + 0.15, -0.1), 0.32, c("orange") if i % 2 else c("blanc"), collide=False, name="Flotteur")
    return {"emprise": (W + 1, 1.0), "hauteur": 6.6}


TEXTES_PANNEAUX = ("PORT", "TAVERNE", "MARCHÉ", "POISSONS", "FRUITS", "VIANDE", "MOULIN", "PHARE", "AUBERGE",
                   "CHANTIER", "ÉPICES", "PLAGE", "FERME", "TRÉSOR")


def panneau(b, texte: str = "PORT", variant: int = 0) -> dict:
    """Panneau de bois à texte (SurfaceGui). 0 : planche sur poteau ; 1 : sur deux pieds ; 2 : flèche directionnelle.
    Textes : mots français génériques (voir TEXTES_PANNEAUX), jamais de nom de la licence."""
    larg = max(4.0, 0.95 * len(texte) + 1.6)
    fond = (c("bois_pale"), c("bois_flotte"), c("bois_pale"))[variant % 3]
    with b.group("Panneau"):
        v = variant % 3
        y0 = 3.4 if v != 1 else 1.4
        if v == 1:
            for x in (-larg / 2 + 0.5, larg / 2 - 0.5):
                b.box((x - 0.2, 0, -0.2), (x + 0.2, y0 + 1.9, 0.2), c("bois_fonce"), name="Pied")
        else:
            b.box((-larg / 2 - 0.6, 0, -0.3), (-larg / 2, y0 + 2.6, 0.3), c("bois_fonce"), name="Poteau")
            b.box((-larg / 2 - 0.9, 0, -0.6), (-larg / 2 + 0.3, 0.4, 0.6), c("pierre_fonce"), collide=False, name="Pierre")
        board = b.box((-larg / 2, y0, -0.25), (larg / 2, y0 + 1.9, 0.0), fond, name="Planche")
        board.label = {"face": "Front", "text": texte, "color": (60, 34, 18), "font": "sans"}
        dos = b.box((-larg / 2, y0, 0.0), (larg / 2, y0 + 1.9, 0.25), fond, collide=False, name="Planche")
        dos.label = {"face": "Back", "text": texte, "color": (60, 34, 18), "font": "sans"}
        if v == 2:
            b.wedge((larg / 2, y0, -0.25), (larg / 2 + 1.0, y0 + 0.95, 0.25), fond, down="+x", collide=False, name="Pointe")
            b.wedge_under((larg / 2, y0 + 0.95, -0.25), (larg / 2 + 1.0, y0 + 1.9, 0.25), fond, down="+x", collide=False, name="Pointe")
        else:
            b.box((-larg / 2 - 0.15 - (0.6 if v == 0 else 0), y0 + 1.9, -0.35), (larg / 2 + 0.15, y0 + 2.2, 0.35), c("bois_fonce"),
                  studs="top", collide=False, name="Chapeau")
    return {"emprise": (larg + 1, 0.8), "hauteur": y0 + 2.6}


def banc(b, variant: int = 0) -> dict:
    """Banc de bois (0), banc rondin (1), banc-caisse avec coussin rouge (2)."""
    with b.group("Banc"):
        v = variant % 3
        if v == 1:
            b.cyl((0, 1.0, 0), 1.0, 5.6, c("tronc"), axis="x", name="Rondin")
            b.box((-2.8, 1.85, -0.6), (2.8, 2.0, 0.6), c("tronc_clair"), collide=False, name="Assise")
            for x in (-2.0, 2.0):
                b.box((x - 0.4, 0, -0.9), (x + 0.4, 0.4, 0.9), c("tronc_fonce"), collide=False, name="Cale")
            return {"emprise": (5.6, 2.0), "hauteur": 2.0}
        if v == 2:
            b.box((-2.6, 0, -1.0), (2.6, 1.6, 1.0), c("bois_pale"), name="Caisse")
            b.box((-2.7, 0.6, -1.08), (2.7, 1.0, 1.08), c("bois"), collide=False, name="Cerclage")
            b.box((-2.4, 1.6, -0.85), (2.4, 2.0, 0.85), c("rouge"), studs="top", name="Coussin")
            return {"emprise": (5.4, 2.2), "hauteur": 2.0}
        for x in (-2.3, 2.3):
            b.box((x - 0.3, 0, -0.8), (x + 0.3, 1.6, 0.8), c("bois_fonce"), name="Pied")
        b.box((-3.0, 1.6, -0.9), (3.0, 1.95, 0.9), c("bois"), studs="top", name="Assise")
        b.box((-3.0, 2.1, 0.75), (3.0, 3.4, 1.05), c("bois"), name="Dossier")
        for x in (-2.3, 2.3):
            b.box((x - 0.25, 1.95, 0.8), (x + 0.25, 3.4, 1.0), c("bois_fonce"), collide=False, name="Montant")
    return {"emprise": (6.0, 2.1), "hauteur": 3.4}


def cloture_bois(b, longueur: float = 12, variant: int = 0, hauteur: float = 3.6) -> dict:
    """Clôture de ranch le long de X (centrée), poteaux tous les 4 studs environ.
    0 : bois brun, deux lisses continues ; 1 : bois délavé, trois lisses ; 2 : rustique, lisses par travée
    légèrement de travers (comme les clôtures des moulins des références)."""
    v = variant % 3
    bois = c("bois_flotte") if v == 1 else c("bois")
    poteau = c("bois_fonce") if v != 1 else shade(c("bois_flotte"), 0.85)
    n = max(2, int(round(longueur / 4)) + 1)
    xs = [-longueur / 2 + i * longueur / (n - 1) for i in range(n)]
    rng = b.rng
    with b.group("Cloture"):
        for i, x in enumerate(xs):
            h = hauteur + (0.4 if (v == 2 and i % 2) else 0.0)
            b.box((x - 0.32, 0, -0.32), (x + 0.32, h, 0.32), poteau, studs="top", name="Poteau")
        ys = (0.42, 0.82) if v != 1 else (0.3, 0.58, 0.86)
        if v == 2:
            for x0, x1 in zip(xs, xs[1:]):
                for yy in ys:
                    dy = float(rng.uniform(-0.25, 0.25))
                    xm, L = (x0 + x1) / 2, (x1 - x0) + 0.3
                    ang = math.degrees(math.atan2(dy * 2, L))
                    b.part("block", (L, 0.4, 0.3), (xm, hauteur * yy + dy * 0.2, -0.45), rot_z(ang), bois, name="Lisse")
        else:
            for yy in ys:
                b.box((-longueur / 2 - 0.2, hauteur * yy - 0.2, -0.62), (longueur / 2 + 0.2, hauteur * yy + 0.2, -0.32), bois,
                      name="Lisse")
    return {"emprise": (longueur + 0.6, 1.0), "hauteur": hauteur + 0.4}


# ---------------------------------------------------------------------------
# Campagne : vaches, foin
# ---------------------------------------------------------------------------


def vache(b, variant: int = 0) -> dict:
    """Vache en blocs (tête vers -Z) : blanche à taches noires (0, 1) ou brune à tête blanche (2)."""
    v = variant % 3
    corps = c("vache_blanc") if v != 2 else c("terre_claire")
    tache = c("vache_noir") if v != 2 else c("vache_blanc")
    rose = c("vache_rose")
    with b.group("Vache"):
        for x in (-0.95, 0.95):
            for z in (-1.9, 1.9):
                b.box((x - 0.4, 0, z - 0.4), (x + 0.4, 2.0, z + 0.4), corps, name="Patte")
                b.box((x - 0.42, 0, z - 0.42), (x + 0.42, 0.35, z + 0.42), c("vache_noir"), collide=False, name="Sabot")
        b.box((-1.5, 2.0, -2.6), (1.5, 4.5, 2.6), corps, name="Corps")
        # taches (dépassent de 0,1)
        spots = [((1.5, 2.6, -1.6), (1.6, 3.9, 0.2)), ((-1.6, 2.4, 0.4), (-1.5, 4.1, 2.0)), ((-0.6, 4.5, -0.8), (0.9, 4.6, 0.9))]
        if v == 1:
            spots = [((1.5, 3.0, 0.5), (1.6, 4.3, 2.2)), ((-1.6, 2.4, -2.0), (-1.5, 3.8, -0.4)), ((-1.0, 4.5, 1.0), (0.4, 4.6, 2.4))]
        for a, bb in spots:
            b.box(a, bb, tache, collide=False, name="Tache")
        b.box((-0.45, 1.55, -0.3), (0.45, 2.0, 0.9), rose, collide=False, name="Pis")
        # tête
        b.box((-1.05, 3.2, -4.4), (1.05, 5.3, -2.5), corps if v != 2 else c("vache_blanc"), name="Tete")
        b.box((-0.95, 3.1, -4.75), (0.95, 4.2, -4.3), rose, collide=False, name="Museau")
        for x in (-0.45, 0.45):
            b.box((x - 0.15, 3.65, -4.8), (x + 0.15, 3.9, -4.7), c("vache_noir"), collide=False, name="Narine")
            b.box((x * 1.6 - 0.2, 4.55, -4.5), (x * 1.6 + 0.2, 4.95, -4.38), c("vache_noir"), collide=False, name="Oeil")
        for sx in (-1, 1):
            b.box((sx * 1.05, 4.5, -3.4), (sx * 1.6, 4.9, -3.0), corps, collide=False, name="Oreille")
            b.box((sx * 0.6 - 0.18, 5.3, -3.5), (sx * 0.6 + 0.18, 5.9, -3.15), c("corne"), collide=False, name="Corne")
        b.box((-0.12, 2.4, 2.6), (0.12, 4.3, 2.8), corps, collide=False, name="Queue")
        b.box((-0.2, 2.1, 2.62), (0.2, 2.6, 2.9), tache, collide=False, name="Toupet")
    return {"emprise": (3.2, 7.6), "hauteur": 5.9}


def botte_foin(b, variant: int = 0) -> dict:
    """Foin : 0 balle ronde ; 1 trois bottes carrées empilées ; 2 meule en gradins."""
    foin, foin_f = c("foin"), c("foin_fonce")
    with b.group("Foin"):
        v = variant % 3
        if v == 0:
            b.cyl((0, 1.6, 0), 1.6, 2.4, foin, axis="x", name="Balle")
            for x in (-0.6, 0.6):
                b.cyl((x, 1.6, 0), 1.65, 0.2, foin_f, axis="x", collide=False, name="Lien")
            return {"emprise": (2.4, 3.2), "hauteur": 3.2}
        if v == 1:
            for (x, y, z) in ((-1.3, 0, 0), (1.3, 0, 0), (0, 1.4, 0)):
                b.box((x - 1.25, y, z - 0.8), (x + 1.25, y + 1.4, z + 0.8), foin, studs="top", name="Botte")
                b.box((x - 0.6, y - 0.0, z - 0.85), (x - 0.4, y + 1.45, z + 0.85), foin_f, collide=False, name="Lien")
            return {"emprise": (5.0, 1.6), "hauteur": 2.8}
        for k, (r, h) in enumerate(((2.6, 1.6), (2.1, 1.4), (1.5, 1.2), (0.8, 0.8))):
            y0 = sum(hh for _, hh in ((2.6, 1.6), (2.1, 1.4), (1.5, 1.2), (0.8, 0.8))[:k])
            b.box((-r, y0, -r), (r, y0 + h, r), foin if k % 2 == 0 else foin_f, studs="top", name="Meule")
    return {"emprise": (5.2, 5.2), "hauteur": 5.0}


# ---------------------------------------------------------------------------
# Bord de mer : crabes, mouettes, coquillages
# ---------------------------------------------------------------------------


def crabe(b, variant: int = 0) -> dict:
    """Crabe rouge en blocs (pinces vers -Z)."""
    col = c("crabe") if variant % 2 == 0 else c("orange")
    nd = dict(collide=False)
    with b.group("Crabe"):
        b.box((-0.8, 0.3, -0.55), (0.8, 0.85, 0.55), col, name="Carapace", **nd)
        for sx in (-1, 1):
            b.box((sx * 0.55 - 0.18, 0.45, -1.15), (sx * 0.55 + 0.18, 0.7, -0.5), col, name="Bras", **nd)
            b.box((sx * 0.6 - 0.32, 0.4, -1.65), (sx * 0.6 + 0.32, 0.9, -1.1), shade(col, 1.08), name="Pince", **nd)
            b.box((sx * 0.25 - 0.08, 0.85, -0.5), (sx * 0.25 + 0.08, 1.15, -0.38), c("blanc"), name="Oeil", **nd)
            for z in (-0.2, 0.25):
                b.box((sx * 0.8, 0.0, z - 0.08), (sx * 1.25, 0.45, z + 0.08), col, name="Patte", **nd)
    return {"emprise": (2.5, 1.8), "hauteur": 1.15}


def mouette(b, variant: int = 0) -> dict:
    """Mouette posée (tête vers -Z). variante 1 : ailes à demi ouvertes."""
    nd = dict(collide=False)
    with b.group("Mouette"):
        for x in (-0.18, 0.18):
            b.box((x - 0.05, 0, -0.05), (x + 0.05, 0.4, 0.05), c("bec"), name="Patte", **nd)
        b.box((-0.4, 0.4, -0.6), (0.4, 1.05, 0.6), c("mouette"), name="Corps", **nd)
        b.box((-0.3, 1.0, -0.95), (0.3, 1.5, -0.4), c("mouette"), name="Tete", **nd)
        b.box((-0.08, 1.12, -1.3), (0.08, 1.24, -0.95), c("bec"), name="Bec", **nd)
        b.box((-0.25, 0.55, 0.6), (0.25, 0.85, 1.05), c("mouette_gris"), name="Queue", **nd)
        if variant % 2:
            for sx in (-1, 1):
                _bloc_tourne(b, (sx * 0.8, 1.15, 0.0), (1.2, 0.12, 0.9), sx * 25, c("mouette_gris"), name="Aile", **nd)
        else:
            for sx in (-1, 1):
                b.box((sx * 0.4, 0.55, -0.35), (sx * 0.5, 0.95, 0.7), c("mouette_gris"), name="Aile", **nd)
    return {"emprise": (1.0 if variant % 2 == 0 else 2.6, 2.4), "hauteur": 1.5}


def coquillages(b, variant: int = 0) -> dict:
    """Coquillages et étoile de mer posés sur le sable (plats, sans collision)."""
    rng = b.rng
    nd = dict(collide=False, shadow=False)
    with b.group("Coquillages"):
        for k in range(3):
            x, z = float(rng.uniform(-1.6, 1.6)), float(rng.uniform(-1.2, 1.2))
            col = (c("fleur_rose"), c("blanc"), c("sable_clair"))[(k + variant) % 3]
            b.wedge((x - 0.35, 0, z - 0.3), (x + 0.35, 0.3, z + 0.3), col, down="-z", name="Coquillage", **nd)
        cx, cz = (0.4, 0.2) if variant % 2 else (-0.5, -0.3)
        for k in range(5):
            a = math.radians(k * 72)
            b.boxc((cx + 0.38 * math.cos(a), 0.07, cz - 0.38 * math.sin(a)), (0.8, 0.14, 0.3), c("orange"), yaw=k * 72,
                   name="Etoile", **nd)
    return {"emprise": (3.6, 2.8), "hauteur": 0.3}


def viande_geante(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Grosse viande sur l'os, façon dessin animé (motif générique de manga). Os selon X.
    0 : posée sur un piédestal (enseigne d'étal) ; 1 : seule, posée au sol ; 2 : à la broche sur un feu."""
    s = taille
    v = variant % 3
    yc = {0: 3.4 * s, 1: 1.5 * s, 2: 3.0 * s}[v]
    with b.group("Viande"):
        if v == 0:
            b.box((-1.6 * s, 0, -1.6 * s), (1.6 * s, 0.5 * s, 1.6 * s), c("bois_fonce"), studs="top", name="Socle")
            b.cyl((0, 1.1 * s, 0), 0.5 * s, 1.2 * s, c("bois"), name="Pied")
            b.cyl((0, 1.8 * s, 0), 1.6 * s, 0.25 * s, c("blanc"), name="Assiette")
        if v == 2:
            for x in (-3.2 * s, 3.2 * s):
                b.box((x - 0.25 * s, 0, -0.25 * s), (x + 0.25 * s, yc + 0.6 * s, 0.25 * s), c("bois_fonce"), name="Fourche")
            b.box((-1.4 * s, 0, -1.4 * s), (1.4 * s, 0.5 * s, 1.4 * s), c("roche_fonce"), name="Foyer")
            b.box((-0.8 * s, 0.5 * s, -0.8 * s), (0.8 * s, 1.4 * s, 0.8 * s), c("flamme"), material="Neon", collide=False,
                  shadow=False, name="Feu")
            b.box((-0.4 * s, 1.4 * s, -0.4 * s), (0.4 * s, 1.9 * s, 0.4 * s), c("jaune"), material="Neon", collide=False,
                  shadow=False, name="Feu")
        b.cyl((0, yc, 0), 0.35 * s, 6.4 * s if v == 2 else 4.8 * s, c("os_viande"), axis="x", collide=False, name="Os")
        for sx in (-1, 1):
            for dz in (-0.3, 0.3):
                b.ball((sx * 2.45 * s, yc, dz * s), 0.45 * s, c("os_viande"), collide=False, name="Bout")
        b.ball((0, yc + 0.05 * s, 0), 1.5 * s, c("viande"), collide=False, name="Viande")
        b.cyl((0, yc, 0), 1.3 * s, 2.4 * s, c("viande"), axis="x", collide=False, name="Viande")
        for sx in (-1, 1):
            b.ball((sx * 1.05 * s, yc, 0), 1.2 * s, c("viande_fonce"), collide=False, name="Viande")
        b.box((-0.9 * s, yc + 0.9 * s, -0.95 * s), (0.5 * s, yc + 1.35 * s, -0.35 * s), c("viande_claire"), collide=False,
              name="Reflet")
    return {"emprise": (5.8 * s, 3.2 * s), "hauteur": yc + 1.3 * s}


__all__ = [
    "cordage", "guirlande_fanions", "drapeau_pirate", "mat_guirlande", "mat_vigie", "lanterne_quai", "tonneaux", "caisses",
    "bitte", "canon", "ancre", "coffre_tresor", "barre_navire", "bouee", "filet_peche", "panneau", "TEXTES_PANNEAUX", "banc",
    "cloture_bois", "vache", "botte_foin", "crabe", "mouette", "coquillages", "viande_geante",
]
