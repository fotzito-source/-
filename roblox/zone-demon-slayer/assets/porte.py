"""Entrée de la zone : grand torii vermillon (style myōjin), corde shimenawa et papiers shide,
plaque 藤 (glycine), chiens-lions gardiens, lanternes de pierre et clôture de sanctuaire.

Origine : centre de l'ouverture au sol ; le torii est centré sur z = 0. L'extérieur (d'où arrivent les
joueurs) est +Z, le village est vers -Z. Tout ce qui enjambe le couloir (|x| < 31) est au-dessus de y = 33.
"""

from __future__ import annotations

import math

import numpy as np

from kit import shade
from palette import c, vary


def _shide(b, x, y_haut, z, longueur: float = 4.0) -> None:
    """Papier shide en zigzag : quatre petits blocs blancs décalés, suspendus à une corde."""
    w, h = 1.4, longueur / 4
    for k in range(4):
        dx = (0.35 if k % 2 else -0.35)
        b.box((x + dx - w / 2, y_haut - (k + 1) * h, z - 0.06), (x + dx + w / 2, y_haut - k * h, z + 0.06),
              c("shide"), collide=False, shadow=False, name="Shide")


def _shimenawa(b, xa: float, xb: float, y: float, z: float, creux: float = 0.8, r: float = 0.75) -> None:
    """Corde de paille tressée (segments de cylindre) avec papiers shide et pompons."""
    n = 10
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append((xa + (xb - xa) * t, y - creux * 4 * t * (1 - t), z))
    for (x0, y0, _), (x1, y1, _) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        a = math.radians(ang)
        R = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
        b.part("cyl", (L + 0.3, 2 * r, 2 * r), ((x0 + x1) / 2, (y0 + y1) / 2, z), R, c("corde"), collide=False, name="Shimenawa")
    for i in (2, 4, 6, 8):
        x, yy, _ = pts[i]
        _shide(b, x, yy - r * 0.6, z)
    for i in (3, 5, 7):
        x, yy, _ = pts[i]
        b.box((x - 0.35, yy - r - 1.6, z - 0.35), (x + 0.35, yy - r, z + 0.35), c("corde"), collide=False, name="Pompon")


def _koma_inu(b, x: float, z: float, sens: int, rng) -> None:
    """Chien-lion gardien stylisé (pierre grise) sur un socle, assis, tourné vers l'allée."""
    p, pf, pc = c("pierre"), c("pierre_fonce"), c("pierre_claire")
    with b.at((x, 0, z), yaw=90 * sens, group="KomaInu"):
        b.box((-3, 0, -3), (3, 3.5, 3), pf, studs="top", name="Socle")
        b.box((-3.4, 3.5, -3.4), (3.4, 4.2, 3.4), p, studs="top", name="Corniche")
        y = 4.2
        b.box((-1.8, y, -1.2), (1.8, y + 2.6, 2.4), p, name="Corps")           # arrière-train assis
        b.box((-1.5, y, -2.2), (-0.5, y + 2.0, -1.2), pc, name="Patte")
        b.box((0.5, y, -2.2), (1.5, y + 2.0, -1.2), pc, name="Patte")
        b.box((-1.6, y + 2.0, -2.0), (1.6, y + 4.6, 0.6), p, name="Poitrail")
        b.box((-1.9, y + 4.2, -2.6), (1.9, y + 7.0, 0.4), pc, name="Tete")
        b.box((-2.2, y + 4.6, -1.0), (2.2, y + 7.4, 1.0), pf, name="Criniere")
        b.box((-1.2, y + 4.4, -3.1), (1.2, y + 5.4, -2.6), pf, name="Museau")
        for dx in (-0.9, 0.9):
            b.box((dx - 0.35, y + 6.0, -2.75), (dx + 0.35, y + 6.5, -2.6), c("noir"), collide=False, name="Oeil")
        b.box((-0.6, y + 2.6, 1.6), (0.6, y + 5.6, 2.6), pf, name="Queue")
        # bavoir rouge (offrande)
        b.box((-1.7, y + 3.4, -2.15), (1.7, y + 4.4, -1.95), c("vermillon"), collide=False, name="Bavoir")


def grand_torii(b, variant: int = 0, ouverture: float = 74, hauteur: float = 44, mur: float = 130) -> dict:
    """Grand torii d'entrée (myōjin) + clôture de sanctuaire jusqu'à |x| = mur."""
    rng = b.rng
    verm, verm_f, noir = c("vermillon"), c("vermillon_fonce"), c("noir_laque")
    xp = ouverture / 2 + 2.6          # axe des piliers : bien hors du couloir
    rp = 3.0
    H = hauteur
    with b.group("Torii"):
        for s in (-1, 1):
            x = s * xp
            b.box((x - 4.5, 0, -4.5), (x + 4.5, 1.2, 4.5), c("pierre_fonce"), studs="top", name="Fondation")
            b.cyl((x, 1.2 + 1.6, 0), rp + 0.7, 3.2, noir, name="Kamaki")
            b.cyl((x, 1.2 + H / 2, 0), rp, H - 1.2, verm, name="Pilier")
            b.cyl((x, H - 7.2, 0), rp + 0.25, 0.8, noir, name="Bague")
        # nuki (traverse basse, traverse les piliers et dépasse)
        y_nuki = H - 9
        b.box((-xp - 6, y_nuki, -1.6), (xp + 6, y_nuki + 3.4, 1.6), verm, name="Nuki")
        # gakuzuka + plaque (gaku) avec 藤
        b.box((-1.3, y_nuki + 3.4, -1.0), (1.3, H, 1.0), verm_f, name="Gakuzuka")
        plaque = b.box((-4.2, y_nuki + 2.0, -1.6), (4.2, H + 0.6, -1.15), noir, name="Gaku")
        plaque.label = {"face": "Front", "text": "藤", "color": c("or"), "bg": None, "font": "brush"}
        plaque2 = b.box((-4.2, y_nuki + 2.0, 1.15), (4.2, H + 0.6, 1.6), noir, name="Gaku")
        plaque2.label = {"face": "Back", "text": "藤", "color": c("or"), "bg": None, "font": "brush"}
        b.box((-4.6, H + 0.6, -1.8), (4.6, H + 1.0, 1.8), c("or"), collide=False, name="Cadre")
        # shimaki (poutre sous le kasagi) + kasagi laqué noir aux extrémités relevées
        L = xp + 9
        b.box((-L, H, -2.0), (L, H + 3.0, 2.0), verm, name="Shimaki")
        b.box((-L - 1, H + 3.0, -2.6), (L + 1, H + 5.0, 2.6), noir, studs="top", name="Kasagi")
        for s in (-1, 1):
            xa, xb = sorted((s * (L + 1), s * (L + 6)))
            b.wedge((xa, H + 3.0, -2.6), (xb, H + 7.0, 2.6), noir, down="+x" if s < 0 else "-x", name="Kasagi_bout")
            xa, xb = sorted((s * (L - 8), s * (L + 1)))
            b.box((xa, H + 5.0, -2.6), (xb, H + 5.9, 2.6), noir, name="Kasagi_releve")
        # corde sacrée sous le nuki (au-dessus de 33 studs au-dessus du couloir)
        _shimenawa(b, -xp + rp, xp - rp, y_nuki - 1.2, 0, creux=1.8, r=1.3)

    with b.group("Gardiens"):
        for s in (-1, 1):
            _koma_inu(b, s * (xp + 10), 7, s, rng)

    with b.group("Lanternes"):
        for s in (-1, 1):
            for dz in (6, -8):
                x = s * (xp + 20)
                with b.at((x, 0, dz)):
                    p, pf = c("pierre"), c("pierre_fonce")
                    b.box((-1.6, 0, -1.6), (1.6, 0.8, 1.6), pf, studs="top", name="Socle")
                    b.box((-0.7, 0.8, -0.7), (0.7, 4.0, 0.7), p, name="Fut")
                    b.box((-1.3, 4.0, -1.3), (1.3, 4.5, 1.3), pf, name="Plateau")
                    b.box((-1.0, 4.5, -1.0), (1.0, 6.2, 1.0), p, name="Chambre")
                    b.box((-0.65, 4.8, -1.05), (0.65, 5.9, 1.05), c("jaune_lampion"), material="Neon", collide=False, shadow=False, name="Lumiere")
                    b.box((-1.9, 6.2, -1.9), (1.9, 6.8, 1.9), pf, studs="top", name="Toit")
                    b.box((-1.1, 6.8, -1.1), (1.1, 7.4, 1.1), p, studs="top", name="Toit")
                    b.box((-0.4, 7.4, -0.4), (0.4, 8.1, 0.4), pf, name="Bouton")

    # clôture de sanctuaire (tamagaki) : muret de pierre + barrière vermillon, de part et d'autre
    with b.group("Cloture"):
        for s in (-1, 1):
            x0, x1 = sorted((s * (xp + 30), s * mur))
            # muret en blocs de pierre décalés
            x = x0
            k = 0
            while x < x1 - 0.01:
                xa, xb = x, min(x + 8, x1)
                b.box((xa, 0, -2), (xb, 3, 2), vary("pierre_fonce", rng, 0.05), studs="top", name="Muret")
                x = xb
                k += 1
            # barrière : poteaux tous les 4 studs, deux lisses, chapeau noir
            x = x0 + 1
            while x < x1 - 0.5:
                b.box((x - 0.4, 3, -0.4), (x + 0.4, 9, 0.4), verm, name="Poteau")
                b.box((x - 0.6, 9, -0.6), (x + 0.6, 9.5, 0.6), noir, name="Chapeau")
                x += 4
            b.box((x0, 7.2, -0.3), (x1, 8.0, 0.3), verm, name="Lisse")
            b.box((x0, 4.6, -0.3), (x1, 5.2, 0.3), verm, name="Lisse")
        # raccord entre torii et clôture : lanternes déjà posées ; petits buissons
    # bannières verticales (nobori) de part et d'autre de l'allée, côté extérieur
    with b.group("Nobori"):
        couleurs = [c("vermillon"), c("glycine_fonce"), c("blanc"), c("noren_bleu")]
        textes = ["藤", "奉納", "藤", "祭"]
        for s in (-1, 1):
            for k in range(4):
                x = s * (xp + 27 + k * 4.5)
                z = 4 + k * 1.5
                b.box((x - 0.4, 0, z - 0.4), (x + 0.4, 0.6, z + 0.4), c("pierre_fonce"), name="Socle")
                b.cyl((x, 7.5, z), 0.18, 15, c("bois_fonce"), collide=False, name="Hampe")
                b.box((x - 0.18, 14.4, z - 0.18), (x - s * 2.6, 14.8, z + 0.18), c("bois_fonce"), collide=False, name="Traverse")
                xa, xb = sorted((x - s * 0.2, x - s * 2.6))
                ban = b.box((xa, 5.0, z - 0.08), (xb, 14.4, z + 0.08), couleurs[(k + (s > 0)) % 4], collide=False, name="Banniere")
                fg = (40, 30, 30) if couleurs[(k + (s > 0)) % 4] == c("blanc") else (250, 246, 236)
                ban.label = {"face": "Back", "text": textes[k], "color": fg, "bg": None, "font": "brush", "vertical": True}
    return {"emprise": (2 * mur, 16), "hauteur": H + 7.0, "ouverture": ouverture}
