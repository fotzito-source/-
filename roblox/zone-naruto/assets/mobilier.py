"""Mobilier de rue de Konoha : guirlandes de lampions, câbles et poteaux électriques, lanternes,
réverbères, bancs, caisses, tonneaux, souches d'entraînement, distributeur, clôtures, panneaux, étals.

Les petits objets sont décoratifs : pas de collision pour les détails fins.
"""

from __future__ import annotations

import math

import numpy as np

from kit import shade
from palette import c


def _segment(b, a, bb, rayon: float, col, name: str = "Cable") -> None:
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
    R = np.column_stack([x, y, z])
    b.part("cyl", (n + rayon * 0.6, 2 * rayon, 2 * rayon), (a + bb) / 2, R, col, collide=False, shadow=False, name=name)


def _chainette(p0, p1, creux: float, n: int):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    pts = []
    for i in range(n + 1):
        t = i / n
        p = p0 + (p1 - p0) * t
        p[1] -= creux * 4 * t * (1 - t)
        pts.append(p)
    return pts


def cable(b, p0, p1, creux: float = 2.0) -> dict:
    """Câble électrique noir, affaissé entre deux points."""
    pts = _chainette(p0, p1, creux, 8)
    with b.group("Cable"):
        for a, bb in zip(pts, pts[1:]):
            _segment(b, a, bb, 0.09, c("noir"))
    return {"longueur": float(np.linalg.norm(np.asarray(p1) - np.asarray(p0)))}


PALETTES_LAMPIONS = [
    [("rouge", False), ("panneau", True), ("orange_lampion", True)],
    [("panneau", True), ("panneau", True), ("rouge", False)],
    [("orange_lampion", True), ("rouge", False), ("jaune_lampion", True)],
    [("rouge", False), ("rouge", False), ("panneau", True)],
]


def _corps_lampion(b, x, y, z, col, neon: bool, r: float = 0.95, h: float = 1.7) -> None:
    """Lampion rond en papier : corps, deux capuchons sombres (y = bas du lampion)."""
    noir = c("noir")
    b.cyl((x, y + 0.15, z), r * 0.62, 0.3, noir, collide=False, name="Capuchon")
    b.cyl((x, y + 0.3 + h / 2, z), r, h, c(col), material="Neon" if neon else "SmoothPlastic",
          collide=False, shadow=False, name="Lampion")
    b.cyl((x, y + 0.45 + h, z), r * 0.62, 0.3, noir, collide=False, name="Capuchon")


def guirlande_lampions(b, p0, p1, n: int = 8, creux: float = 3.0, variant: int = 0) -> dict:
    """Guirlande de lampions ronds entre deux points (fil affaissé, lampions suspendus dessous)."""
    pts = _chainette(p0, p1, creux, 16)
    pal = PALETTES_LAMPIONS[variant % len(PALETTES_LAMPIONS)]
    with b.group("Guirlande"):
        for a, bb in zip(pts, pts[1:]):
            _segment(b, a, bb, 0.08, c("noir"), name="Fil")
        p0a, p1a = np.asarray(p0, float), np.asarray(p1, float)
        for i in range(n):
            t = (i + 1) / (n + 1)
            p = p0a + (p1a - p0a) * t
            y = p[1] - creux * 4 * t * (1 - t)
            col, neon = pal[i % len(pal)]
            b.box((p[0] - 0.06, y - 0.7, p[2] - 0.06), (p[0] + 0.06, y, p[2] + 0.06), c("noir"), collide=False, shadow=False, name="Attache")
            _corps_lampion(b, p[0], y - 0.7 - 2.3, p[2], col, neon)
    return {"lampions": n}


def poteau_electrique(b, variant: int = 0) -> dict:
    """Poteau électrique (bois ou béton), traverse perpendiculaire à la rue, isolateurs, transformateur."""
    bois = variant % 2 == 0
    col = c("bois") if bois else c("pave")
    h = 24
    with b.group("Poteau"):
        b.box((-0.9, 0, -0.9), (0.9, 1, 0.9), c("pave_fonce"), studs="top", name="Socle")
        b.cyl((0, h / 2, 0), 0.6, h, col, axis="y", name="Fut")
        b.cyl((0, h + 0.15, 0), 0.7, 0.3, shade(col, 0.8), axis="y", name="Tete")
        # traverse le long de Z local (perpendiculaire à la rue une fois posé)
        b.box((-0.3, h - 3, -3.2), (0.3, h - 2.4, 3.2), c("bois_fonce"), name="Traverse")
        attaches = []
        for z in (-2.6, 0.0, 2.6):
            b.cyl((0, h - 2.0, z), 0.22, 0.8, c("blanc"), axis="y", collide=False, name="Isolateur")
            attaches.append((0, h - 1.6, z))
        # transformateur (côté ruelle, +Z local... ici côté opposé à la rue : +Z)
        if variant % 3 != 2:
            b.box((-0.2, h - 8.4, 0.5), (0.2, h - 7.8, 1.6), c("metal_fonce"), name="Support")
            b.cyl((0, h - 7.0, 1.9), 1.0, 2.6, c("metal"), axis="y", name="Transformateur")
            b.cyl((0, h - 5.55, 1.9), 1.1, 0.3, c("metal_fonce"), axis="y", name="Couvercle")
        # échelons
        for k in range(5):
            y = 6 + k * 2.4
            b.box((-0.15, y, -1.0), (0.15, y + 0.3, 1.0), c("metal_fonce"), collide=False, name="Echelon")
    return {"emprise": (2, 7), "hauteur": h + 0.3, "attaches": attaches}


def lampion(b, variant: int = 0) -> dict:
    """Lampion isolé suspendu à une potence en bois."""
    col, neon = (("rouge", False), ("panneau", True), ("orange_lampion", True))[variant % 3]
    with b.group("Lampion"):
        b.box((-0.4, 0, -0.4), (0.4, 7, 0.4), c("bois_fonce"), name="Poteau")
        b.box((-0.25, 6.4, -0.25), (0.25, 6.9, -2.2), c("bois_fonce"), name="Potence")
        b.box((-0.05, 5.1, -2.05), (0.05, 6.4, -1.95), c("noir"), collide=False, name="Attache")
        _corps_lampion(b, 0, 2.6, -2.0, col, neon)
    return {"emprise": (1, 3), "hauteur": 7}


def lanterne_pierre(b, variant: int = 0) -> dict:
    """Lanterne de pierre (tōrō) : socle, fût, chambre à lumière, toit débordant, bouton."""
    p, pf = c("pave"), c("pave_fonce")
    if variant % 2:
        p, pf = shade(p, 0.92), shade(pf, 0.92)
    with b.group("LanternePierre"):
        b.box((-1.3, 0, -1.3), (1.3, 0.6, 1.3), pf, studs="top", name="Socle")
        b.box((-0.6, 0.6, -0.6), (0.6, 3.0, 0.6), p, name="Fut")
        b.box((-1.1, 3.0, -1.1), (1.1, 3.4, 1.1), pf, name="Plateau")
        b.box((-0.85, 3.4, -0.85), (0.85, 4.8, 0.85), p, name="Chambre")
        b.box((-0.55, 3.6, -0.9), (0.55, 4.6, 0.9), c("jaune_lampion"), material="Neon", collide=False, shadow=False, name="Lumiere")
        b.box((-0.9, 3.6, -0.55), (0.9, 4.6, 0.55), c("jaune_lampion"), material="Neon", collide=False, shadow=False, name="Lumiere")
        b.box((-1.6, 4.8, -1.6), (1.6, 5.3, 1.6), pf, studs="top", name="Toit")
        b.box((-1.0, 5.3, -1.0), (1.0, 5.8, 1.0), p, studs="top", name="Toit")
        b.box((-0.35, 5.8, -0.35), (0.35, 6.4, 0.35), pf, name="Bouton")
    return {"emprise": (3.2, 3.2), "hauteur": 6.4}


def reverbere(b, variant: int = 0) -> dict:
    """Réverbère : mât, bras vers l'avant (-Z), lanterne carrée lumineuse."""
    col = (c("metal_fonce"), c("bois_fonce"), c("noir"))[variant % 3]
    with b.group("Reverbere"):
        b.box((-0.7, 0, -0.7), (0.7, 0.6, 0.7), c("pave_fonce"), studs="top", name="Socle")
        b.box((-0.3, 0.6, -0.3), (0.3, 11, 0.3), col, name="Mat")
        b.box((-0.2, 10.4, -2.6), (0.2, 10.8, 0.3), col, name="Bras")
        b.box((-0.7, 8.8, -3.2), (0.7, 10.0, -1.8), c("jaune_lampion"), material="Neon", collide=False, shadow=False, name="Lanterne")
        b.box((-0.9, 10.0, -3.4), (0.9, 10.4, -1.6), col, collide=False, name="Chapeau")
    return {"emprise": (1.8, 4), "hauteur": 11}


def banc(b, variant: int = 0) -> dict:
    bois = (c("bois_clair"), c("bois"), c("toit_rouge"))[variant % 3]
    with b.group("Banc"):
        for x in (-2.4, 2.4):
            b.box((x - 0.3, 0, -0.8), (x + 0.3, 1.4, 0.8), c("bois_fonce"), name="Pied")
        b.box((-3, 1.4, -0.9), (3, 1.8, 0.9), bois, studs="top", name="Assise")
        if variant % 3 != 2:
            b.box((-3, 1.8, 0.6), (3, 3.2, 0.9), bois, name="Dossier")
    return {"emprise": (6, 2), "hauteur": 3.2}


def caisses(b, variant: int = 0) -> dict:
    """Pile de caisses en bois, planches en relief."""
    rng = b.rng
    pile = [((-1.2, 0, 0), 2.2), ((1.3, 0, 0.3), 2.0), ((-0.2, 2.2, 0.1), 1.8)][: 2 + variant % 2]
    with b.group("Caisses"):
        for (x, y, z), s in pile:
            yaw = float(rng.uniform(-12, 12))
            b.boxc((x, y + s / 2, z), (s, s, s), c("bois_clair"), yaw=yaw, studs="top", name="Caisse")
            b.boxc((x, y + s / 2, z), (s + 0.12, s * 0.22, s + 0.12), c("bois"), yaw=yaw, collide=False, name="Cerclage")
    return {"emprise": (5, 3), "hauteur": 4.0}


def tonneaux(b, variant: int = 0) -> dict:
    with b.group("Tonneaux"):
        for k, (x, z) in enumerate(((-1.1, 0), (1.1, 0.3), (0, 1.9))[: 2 + variant % 2]):
            b.cyl((x, 1.4, z), 1.0, 2.8, c("bois"), axis="y", name="Tonneau")
            for y in (0.6, 2.2):
                b.cyl((x, y, z), 1.06, 0.25, c("metal_fonce"), axis="y", collide=False, name="Cercle")
            b.cyl((x, 2.85, z), 0.85, 0.1, c("bois_fonce"), axis="y", collide=False, name="Couvercle")
    return {"emprise": (4.2, 4), "hauteur": 2.9}


def poteaux_entrainement(b, variant: int = 0) -> dict:
    """Les trois souches du terrain d'entraînement, alignées le long de X."""
    with b.group("Souches"):
        b.box((-7, 0, -1.6), (7, 0.3, 1.6), c("terre"), studs="top", name="Terre")
        for x in (-4.5, 0, 4.5):
            b.cyl((x, 2.6, 0), 0.9, 4.6, c("bois"), axis="y", name="Souche")
            b.cyl((x, 4.95, 0), 0.75, 0.1, c("bois_clair"), axis="y", collide=False, name="Coupe")
            b.box((x - 0.95, 2.6, -0.95), (x + 0.95, 2.9, 0.95), shade(c("bois"), 0.75), collide=False, name="Corde")
    return {"emprise": (14, 3.2), "hauteur": 5.0}


def distributeur(b, variant: int = 0) -> dict:
    """Distributeur de boissons : caisse colorée, vitrine éclairée, rangées de canettes."""
    col = (c("rouge"), c("toit_bleu"), c("blanc"))[variant % 3]
    canettes = [c("rouge"), c("toit_bleu_clair"), c("jaune_lampion"), c("feuille_claire"), c("blanc")]
    with b.group("Distributeur"):
        b.box((-1.6, 0, -1.1), (1.6, 6.4, 1.1), col, name="Caisse")
        b.box((-1.3, 3.0, -1.2), (1.3, 6.0, -1.1), c("blanc"), material="Neon", collide=False, shadow=False, name="Vitrine")
        for r, y in enumerate((5.2, 4.2, 3.2)):
            for k in range(4):
                x = -0.95 + k * 0.63
                b.box((x - 0.2, y, -1.35), (x + 0.2, y + 0.65, -1.2), canettes[(k + r) % len(canettes)], collide=False, name="Canette")
        b.box((-1.3, 0.6, -1.25), (1.3, 1.4, -1.1), c("noir"), collide=False, name="Trappe")
        b.box((-1.7, 6.4, -1.2), (1.7, 6.7, 1.2), shade(col, 0.8), studs="top", name="Toit")
    return {"emprise": (3.4, 2.4), "hauteur": 6.7}


def boite_lettres(b, variant: int = 0) -> dict:
    with b.group("BoiteLettres"):
        b.box((-0.25, 0, -0.25), (0.25, 3.0, 0.25), c("metal_fonce"), name="Pied")
        b.box((-0.9, 3.0, -0.7), (0.9, 4.8, 0.7), c("rouge"), name="Boite")
        b.box((-0.6, 4.2, -0.75), (0.6, 4.4, -0.7), c("noir"), collide=False, name="Fente")
        b.box((-1.0, 4.8, -0.8), (1.0, 5.1, 0.8), shade(c("rouge"), 0.8), studs="top", name="Toit")
    return {"emprise": (2, 1.6), "hauteur": 5.1}


def cloture(b, longueur: float = 12, variant: int = 0) -> dict:
    """Clôture de bois le long de X local : poteaux tous les 3 studs, deux lisses."""
    bois = (c("bois"), c("bois_clair"))[variant % 2]
    with b.group("Cloture"):
        n = max(2, int(longueur // 3) + 1)
        for i in range(n):
            x = -longueur / 2 + i * longueur / (n - 1)
            b.box((x - 0.3, 0, -0.3), (x + 0.3, 3.4, 0.3), c("bois_fonce"), name="Poteau")
        for y in (1.2, 2.6):
            b.box((-longueur / 2, y, -0.15), (longueur / 2, y + 0.4, 0.15), bois, name="Lisse")
    return {"emprise": (longueur, 0.6), "hauteur": 3.4}


def panneau_kanji(b, texte: str = "茶", variant: int = 0) -> dict:
    """Panneau sur pied : planche crème, texte vertical rouge (SurfaceGui dans Roblox)."""
    fond = (c("panneau"), c("blanc"), c("bois_clair"))[variant % 3]
    with b.group("Panneau"):
        for x in (-0.9, 0.9):
            b.box((x - 0.15, 0, -0.15), (x + 0.15, 1.2, 0.15), c("bois_fonce"), name="Pied")
        b.box((-1.2, 0, -0.4), (1.2, 0.3, 0.4), c("bois_fonce"), name="Patin")
        h = 1.6 + 1.5 * len(texte)
        board = b.box((-1.1, 1.2, -0.2), (1.1, 1.2 + h, 0.2), fond, name="Planche")
        board.label = {"face": "Front", "text": texte, "color": (200, 50, 43), "font": "brush", "vertical": True}
        b.box((-1.3, 1.2 + h, -0.3), (1.3, 1.6 + h, 0.3), c("bois_fonce"), studs="top", name="Chapeau")
    return {"emprise": (2.6, 0.8), "hauteur": 1.6 + h}


def etal_marche(b, variant: int = 0) -> dict:
    """Étal de marché : comptoir, quatre poteaux, auvent rayé, marchandises (fruits, poissons, caisses)."""
    rng = b.rng
    rayures = [(c("rouge"), c("blanc")), (c("toit_vert"), c("panneau")), (c("toit_bleu"), c("blanc"))][variant % 3]
    with b.group("Etal"):
        b.box((-4.5, 0, -3), (4.5, 0.4, 3), c("bois_fonce"), studs="top", name="Plancher")
        b.box((-4, 0.4, -3), (4, 3.0, -1.2), c("bois"), name="Comptoir")
        b.box((-4.2, 3.0, -3.2), (4.2, 3.4, -1.0), c("bois_clair"), studs="top", name="Plateau")
        for x in (-4, 4):
            for z in (-2.8, 2.6):
                b.box((x - 0.3, 0.4, z - 0.3), (x + 0.3, 7.5, z + 0.3), c("poutre"), name="Poteau")
        # auvent rayé (coins, pente vers l'avant)
        for k in range(6):
            x0 = -5 + k * 10 / 6
            b.wedge((x0, 7.5, -4.4), (x0 + 10 / 6, 9.2, 3.2), rayures[k % 2], down="-z", studs="top", name="Auvent")
        b.box((-5, 7.1, -4.4), (5, 7.5, -4.0), rayures[0], collide=False, name="Lambrequin")
        # marchandises
        if variant % 3 == 0:  # fruits
            for k in range(8):
                x = -3.4 + k * 0.95
                col = (c("rouge"), c("orange_lampion"), c("jaune_lampion"), c("feuille_claire"))[k % 4]
                b.ball((x, 3.85, -2.1 + (k % 2) * 0.6), 0.45, col, collide=False, name="Fruit")
        elif variant % 3 == 1:  # poissons sur glace
            b.box((-3.6, 3.4, -2.9), (3.6, 3.6, -1.3), c("fenetre_claire"), collide=False, name="Glace")
            for k in range(5):
                x = -2.8 + k * 1.4
                b.box((x - 0.5, 3.6, -2.5), (x + 0.5, 3.95, -1.6), c("metal"), collide=False, name="Poisson")
        else:  # pots et bocaux
            for k in range(6):
                x = -3.2 + k * 1.3
                b.cyl((x, 3.95, -2.1), 0.45, 1.1, (c("bois_clair"), c("toit_bleu_clair"), c("blanc"))[k % 3], axis="y",
                      collide=False, name="Pot")
        # caisses à l'arrière + lampion
        b.box((-3.5, 0.4, 0.8), (-1.5, 2.4, 2.6), c("bois_clair"), studs="top", name="Caisse")
        b.box((1.0, 0.4, 1.0), (3.0, 1.8, 2.6), c("bois_clair"), studs="top", name="Caisse")
        _corps_lampion(b, 4.5, 4.6, -3.0, "rouge", False, r=0.6, h=1.2)
        b.box((4.45, 6.1, -3.05), (4.55, 7.5, -2.95), c("noir"), collide=False, name="Attache")
    return {"emprise": (10, 8), "hauteur": 9.2}
