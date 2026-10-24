"""Mobilier de la zone : piliers vermillon et cordes à papiers shide (place de la sélection),
guirlandes de lampions, lanternes de pierre, réverbères à gaz de l'ère Taishō, bancs à tissu rouge,
parasols rouges, tonneaux, caisses, panneaux, clôtures de bambou et de sanctuaire.

Les petits objets sont décoratifs : pas de collision pour les détails fins.
"""

from __future__ import annotations

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


def _shide(b, x, y_haut, z, longueur: float = 2.4, larg: float = 0.85) -> None:
    """Papier shide en zigzag (quatre petits blocs blancs décalés)."""
    h = longueur / 4
    for k in range(4):
        dx = 0.3 if k % 2 else -0.3
        b.box((x + dx - larg / 2, y_haut - (k + 1) * h, z - 0.05), (x + dx + larg / 2, y_haut - k * h, z + 0.05),
              c("shide"), collide=False, shadow=False, name="Shide")


def guirlande_shide(b, p0, p1, n: int = 7, creux: float = 1.2, variant: int = 0) -> dict:
    """Corde tendue entre deux points avec des papiers blancs suspendus (comme sur la place de la sélection)."""
    pts = _chainette(p0, p1, creux, 12)
    with b.group("Shide"):
        for a, bb in zip(pts, pts[1:]):
            _segment(b, a, bb, 0.14, c("corde"), name="Corde")
        p0a, p1a = np.asarray(p0, float), np.asarray(p1, float)
        d = p1a - p0a
        horiz = np.array([d[0], 0.0, d[2]])
        horiz = horiz / (np.linalg.norm(horiz) or 1)
        for i in range(n):
            t = (i + 1) / (n + 1)
            p = p0a + d * t
            y = p[1] - creux * 4 * t * (1 - t)
            if variant % 2 == 0:
                # feuille carrée (ofuda) : panneau blanc à bord gris
                yaw = float(np.degrees(np.arctan2(horiz[0], horiz[2]))) + 90
                with b.at((p[0], 0, p[2]), yaw=yaw):
                    b.box((-0.8, y - 2.4, -0.05), (0.8, y - 0.15, 0.05), c("shide"), collide=False, shadow=False, name="Papier")
                    b.box((-0.55, y - 1.9, -0.09), (0.55, y - 0.6, 0.09), c("pierre_claire"), collide=False, shadow=False, name="Inscription")
            else:
                _shide(b, p[0], y - 0.1, p[2])
    return {"papiers": n}


def pilier_rouge(b, variant: int = 0, hauteur: float = 14) -> dict:
    """Pilier vermillon (place de la sélection) : base noire, bague, chapeau, corde nouée."""
    with b.group("Pilier"):
        b.box((-1.8, 0, -1.8), (1.8, 0.8, 1.8), c("pierre_fonce"), studs="top", name="Socle")
        b.cyl((0, 0.8 + 0.8, 0), 1.45, 1.6, c("noir_laque"), name="Base")
        b.cyl((0, 0.8 + hauteur / 2, 0), 1.2, hauteur - 0.8, c("vermillon"), name="Fut")
        b.cyl((0, hauteur + 0.35, 0), 1.45, 0.7, c("noir_laque"), name="Chapeau")
        b.cyl((0, hauteur - 2.5, 0), 1.3, 0.6, c("corde"), collide=False, name="Corde")
        if variant % 2:
            _shide(b, 0, hauteur - 2.6, -1.35)
    return {"emprise": (3.6, 3.6), "hauteur": hauteur + 0.7}


PALETTES_LAMPIONS = [
    [("rouge", False), ("lampion_papier", True), ("rouge", False)],
    [("lampion_papier", True), ("orange_lampion", True), ("lampion_papier", True)],
    [("rouge", False), ("orange_lampion", True), ("lampion_papier", True)],
]


def _corps_lampion(b, x, y, z, col, neon: bool, r: float = 0.95, h: float = 1.8) -> None:
    noir = c("noir")
    b.cyl((x, y + 0.15, z), r * 0.62, 0.3, noir, collide=False, name="Capuchon")
    b.cyl((x, y + 0.3 + h / 2, z), r, h, c(col), material="Neon" if neon else "SmoothPlastic",
          collide=False, shadow=False, name="Lampion")
    b.cyl((x, y + 0.3 + h * 0.5, z), r + 0.05, 0.18, noir, collide=False, shadow=False, name="Cerclage")
    b.cyl((x, y + 0.45 + h, z), r * 0.62, 0.3, noir, collide=False, name="Capuchon")


def guirlande_lampions(b, p0, p1, n: int = 8, creux: float = 3.0, variant: int = 0) -> dict:
    """Guirlande de lampions de papier entre deux points (fil affaissé, lampions dessous)."""
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
            b.box((p[0] - 0.06, y - 0.6, p[2] - 0.06), (p[0] + 0.06, y, p[2] + 0.06), c("noir"), collide=False, shadow=False, name="Attache")
            _corps_lampion(b, p[0], y - 0.6 - 2.4, p[2], col, neon)
    return {"lampions": n}


def lanterne_pierre(b, variant: int = 0) -> dict:
    """Lanterne de pierre (tōrō) : socle, fût, chambre éclairée, toit débordant, bouton."""
    p, pf = c("pierre"), c("pierre_fonce")
    if variant % 2:
        p, pf = shade(p, 0.93), shade(pf, 0.93)
    with b.group("LanternePierre"):
        b.box((-1.4, 0, -1.4), (1.4, 0.7, 1.4), pf, studs="top", name="Socle")
        b.box((-0.6, 0.7, -0.6), (0.6, 3.4, 0.6), p, name="Fut")
        b.box((-1.15, 3.4, -1.15), (1.15, 3.85, 1.15), pf, name="Plateau")
        b.box((-0.9, 3.85, -0.9), (0.9, 5.4, 0.9), p, name="Chambre")
        b.box((-0.55, 4.1, -0.95), (0.55, 5.15, 0.95), c("jaune_lampion"), material="Neon", collide=False, shadow=False, name="Lumiere")
        b.box((-0.95, 4.1, -0.55), (0.95, 5.15, 0.55), c("jaune_lampion"), material="Neon", collide=False, shadow=False, name="Lumiere")
        b.box((-1.7, 5.4, -1.7), (1.7, 5.9, 1.7), pf, studs="top", name="Toit")
        b.box((-1.05, 5.9, -1.05), (1.05, 6.4, 1.05), p, studs="top", name="Toit")
        b.box((-0.4, 6.4, -0.4), (0.4, 7.0, 0.4), pf, name="Bouton")
        if variant % 3 == 2:  # mousse
            b.box((-1.2, 0.7, -1.2), (1.2, 0.9, 0.2), c("mousse"), collide=False, name="Mousse")
    return {"emprise": (3.4, 3.4), "hauteur": 7.0}


def reverbere_gaz(b, variant: int = 0) -> dict:
    """Réverbère à gaz de l'ère Taishō : fût de fonte noir, crosse, lanterne vitrée hexagonale (carrée en stud)."""
    fonte = (c("noir"), c("metal_fonce"), c("bois_fonce"))[variant % 3]
    with b.group("Reverbere"):
        b.box((-0.8, 0, -0.8), (0.8, 0.8, 0.8), c("pierre_fonce"), studs="top", name="Socle")
        b.cyl((0, 0.8 + 0.9, 0), 0.6, 1.8, fonte, name="Pied")
        b.cyl((0, 6.4, 0), 0.3, 9.4, fonte, name="Fut")
        b.box((-0.7, 9.6, -0.7), (0.7, 9.9, 0.7), fonte, name="Bague")
        b.box((-0.18, 10.6, -0.18), (0.18, 11.0, 2.0), fonte, collide=False, name="Bras")   # bras vers l'arrière
        b.box((-0.9, 11.1, -0.9), (0.9, 13.0, 0.9), c("fenetre_lumiere"), material="Neon", collide=False, shadow=False, name="Verre")
        for sx in (-0.95, 0.95):
            for sz in (-0.95, 0.95):
                b.box((sx - 0.12, 11.1, sz - 0.12), (sx + 0.12, 13.0, sz + 0.12), fonte, collide=False, name="Montant")
        b.wedge((-1.2, 13.0, -1.2), (1.2, 13.9, 0), fonte, down="-z", collide=False, name="Chapeau")
        b.wedge((-1.2, 13.0, 0), (1.2, 13.9, 1.2), fonte, down="+z", collide=False, name="Chapeau")
        b.ball((0, 14.2, 0), 0.35, fonte, collide=False, name="Pointe")
        b.box((-0.25, 9.9, -0.25), (0.25, 11.1, 0.25), fonte, collide=False, name="Col")
    return {"emprise": (1.8, 1.8), "hauteur": 14.5}


def banc_rouge(b, variant: int = 0) -> dict:
    """Banc de salon de thé couvert d'un tissu rouge (hi-mōsen)."""
    with b.group("Banc"):
        for x in (-2.6, 2.6):
            for z in (-0.8, 0.8):
                b.box((x - 0.25, 0, z - 0.25), (x + 0.25, 1.5, z + 0.25), c("bois_fonce"), name="Pied")
        b.box((-3.2, 1.5, -1.2), (3.2, 1.8, 1.2), c("bois"), name="Plateau")
        b.box((-3.3, 1.8, -1.3), (3.3, 2.0, 1.3), c("rouge"), studs="top", name="Tissu")
        b.box((-3.3, 1.2, -1.32), (3.3, 2.0, -1.3), c("rouge"), collide=False, name="Rabat")
    return {"emprise": (6.6, 2.6), "hauteur": 2.0}


def parasol_rouge(b, variant: int = 0) -> dict:
    """Grand parasol rouge (nodate-gasa) planté au sol."""
    with b.group("Parasol"):
        b.box((-0.8, 0, -0.8), (0.8, 0.6, 0.8), c("pierre_fonce"), name="Socle")
        b.cyl((0, 5.3, 0), 0.22, 9.4, c("bois_clair"), collide=False, name="Manche")
        b.cyl((0, 9.6, 0), 4.6, 0.4, c("rouge"), collide=False, name="Toile")
        b.cyl((0, 10.0, 0), 3.4, 0.4, c("rouge"), collide=False, name="Toile")
        b.cyl((0, 10.4, 0), 2.0, 0.4, shade(c("rouge"), 0.9), collide=False, name="Toile")
        b.cyl((0, 10.75, 0), 0.6, 0.3, c("noir"), collide=False, name="Pointe")
        b.cyl((0, 9.35, 0), 4.65, 0.12, c("blanc"), collide=False, shadow=False, name="Bordure")
    return {"emprise": (9.2, 9.2), "hauteur": 10.9}


def tonneaux(b, variant: int = 0) -> dict:
    with b.group("Tonneaux"):
        for x, z in ((-1.1, 0), (1.1, 0.3), (0, 1.9))[: 2 + variant % 2]:
            b.cyl((x, 1.4, z), 1.0, 2.8, c("bois_moyen"), axis="y", name="Tonneau")
            for y in (0.6, 2.2):
                b.cyl((x, y, z), 1.06, 0.25, c("bois_fonce"), axis="y", collide=False, name="Cercle")
            b.cyl((x, 2.85, z), 0.85, 0.1, c("bois_clair"), axis="y", collide=False, name="Couvercle")
    return {"emprise": (4.2, 4), "hauteur": 2.9}


def caisses(b, variant: int = 0) -> dict:
    rng = b.rng
    pile = [((-1.2, 0, 0), 2.2), ((1.3, 0, 0.3), 2.0), ((-0.2, 2.2, 0.1), 1.8)][: 2 + variant % 2]
    with b.group("Caisses"):
        for (x, y, z), s in pile:
            yaw = float(rng.uniform(-12, 12))
            b.boxc((x, y + s / 2, z), (s, s, s), c("bois_clair"), yaw=yaw, studs="top", name="Caisse")
            b.boxc((x, y + s / 2, z), (s + 0.12, s * 0.22, s + 0.12), c("bois_moyen"), yaw=yaw, collide=False, name="Cerclage")
    return {"emprise": (5, 3), "hauteur": 4.0}


def panneau_kanji(b, texte: str = "茶", variant: int = 0) -> dict:
    """Panneau sur pied : planche claire, texte vertical (SurfaceGui dans Roblox)."""
    fond = (c("papier"), c("bois_clair"), c("blanc"))[variant % 3]
    with b.group("Panneau"):
        for x in (-0.9, 0.9):
            b.box((x - 0.15, 0, -0.15), (x + 0.15, 1.2, 0.15), c("bois_fonce"), name="Pied")
        b.box((-1.2, 0, -0.4), (1.2, 0.3, 0.4), c("bois_fonce"), name="Patin")
        h = 1.6 + 1.5 * len(texte)
        board = b.box((-1.1, 1.2, -0.2), (1.1, 1.2 + h, 0.2), fond, name="Planche")
        board.label = {"face": "Front", "text": texte, "color": (40, 30, 30), "font": "brush", "vertical": True}
        b.box((-1.3, 1.2 + h, -0.3), (1.3, 1.6 + h, 0.3), c("tuile"), studs="top", name="Chapeau")
    return {"emprise": (2.6, 0.8), "hauteur": 1.6 + h}


def cloture_bambou(b, longueur: float = 12, variant: int = 0, hauteur: float = 4.0) -> dict:
    """Clôture de bambou (yotsume-gaki) le long de X : poteaux, traverses, liens noirs."""
    with b.group("ClotureBambou"):
        n = max(2, int(longueur // 2.5) + 1)
        for i in range(n):
            x = -longueur / 2 + i * longueur / (n - 1)
            b.cyl((x, hauteur / 2, 0), 0.28, hauteur, c("bambou" if i % 2 else "bambou_fonce"), axis="y", name="Poteau")
        for y in (hauteur * 0.35, hauteur * 0.75):
            b.cyl((0, y, 0.35), 0.2, longueur, c("bambou"), axis="x", collide=False, name="Traverse")
    return {"emprise": (longueur, 0.8), "hauteur": hauteur}


def cloture_rouge(b, longueur: float = 12, variant: int = 0) -> dict:
    """Barrière vermillon de sanctuaire (tamagaki) le long de X."""
    with b.group("ClotureRouge"):
        n = max(2, int(longueur // 3) + 1)
        for i in range(n):
            x = -longueur / 2 + i * longueur / (n - 1)
            b.box((x - 0.35, 0, -0.35), (x + 0.35, 4.6, 0.35), c("vermillon"), name="Poteau")
            b.box((x - 0.5, 4.6, -0.5), (x + 0.5, 5.0, 0.5), c("noir_laque"), name="Chapeau")
        for y in (1.6, 3.6):
            b.box((-longueur / 2, y, -0.2), (longueur / 2, y + 0.45, 0.2), c("vermillon"), name="Lisse")
    return {"emprise": (longueur, 1.0), "hauteur": 5.0}


def lampion_poteau(b, variant: int = 0) -> dict:
    """Lampion de papier suspendu à une potence de bois."""
    col, neon = (("rouge", False), ("lampion_papier", True), ("orange_lampion", True))[variant % 3]
    with b.group("Lampion"):
        b.box((-0.4, 0, -0.4), (0.4, 7, 0.4), c("bois_fonce"), name="Poteau")
        b.box((-0.25, 6.4, -2.2), (0.25, 6.9, 0.25), c("bois_fonce"), name="Potence")
        b.box((-0.05, 5.1, -2.05), (0.05, 6.4, -1.95), c("noir"), collide=False, name="Attache")
        _corps_lampion(b, 0, 2.6, -2.0, col, neon)
    return {"emprise": (1, 3), "hauteur": 7}
