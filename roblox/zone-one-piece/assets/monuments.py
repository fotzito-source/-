"""Monuments de la zone mer de l'Est : arche du port (entrée) et rocher du crâne (repère final).

- `porte_entree` : arche de port en mâts de navire liés de cordages, vergue à voile ferlée, panneau de jeu
  bleu marine « ZONE RARE » / « VITESSE CONSEILLÉE : 200 » lisible des deux côtés, bouées, filets, lanternes,
  tonneaux, ancre ; palissade de pieux jusqu'aux collines.
- `rocher_crane` : rocher marin ivoire en forme de tête de mort générique ; le couloir traverse la bouche ;
  falaises sur toute la largeur, épave échouée à gauche, cascade à droite, pavillon au sommet.

Conventions : voir CONVENTIONS.md. Tout ce qui enjambe le couloir (|x| < 31) reste au-dessus de y = 34.
Aucun nom ni emblème de licence : têtes de mort génériques seulement.
"""

from __future__ import annotations

import math

import numpy as np

from kit import hexrgb, mix, rot_x, rot_y, rot_z, shade
from palette import c, vary

from assets.mobilier import (ancre, barre_navire, bouee, caisses, coffre_tresor, cordage, drapeau_pirate,
                             guirlande_fanions, lanterne_quai, mouette, tonneaux)

ND = dict(collide=False)
NDS = dict(collide=False, shadow=False)


# ---------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------


def _segment(b, a, bb, rayon: float, col, name: str = "Corde", **kw) -> None:
    """Cylindre de a à bb (l'axe d'un cylindre Roblox est son X local)."""
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
    kw.setdefault("collide", False)
    b.part("cyl", (n, 2 * rayon, 2 * rayon), (a + bb) / 2, np.column_stack([x, y, z]), col, name=name, **kw)


def _poutre(b, a, bb, ep: float, col, name: str = "Poutre", **kw) -> None:
    """Bloc de section carrée `ep` tendu de a à bb (contrefiches, rames)."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    d = bb - a
    n = float(np.linalg.norm(d))
    y = d / n
    ref = np.array([0.0, 0.0, 1.0]) if abs(y[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    x = np.cross(y, ref)
    x /= np.linalg.norm(x)
    z = np.cross(x, y)
    b.part("block", (ep, n, ep), (a + bb) / 2, np.column_stack([x, y, z]), col, name=name, **kw)


def _lanterne_navire(b, x, y, z, s: float = 1.0, cadre=None) -> None:
    """Lanterne de navire suspendue (4 pièces) : anneau, chapeau, verre éclairé, fond. `y` = bas."""
    cadre = cadre or c("fer")
    b.box((x - 0.8 * s, y, z - 0.8 * s), (x + 0.8 * s, y + 0.3 * s, z + 0.8 * s), cadre, name="Fond", **ND)
    b.box((x - 0.62 * s, y + 0.3 * s, z - 0.62 * s), (x + 0.62 * s, y + 1.9 * s, z + 0.62 * s), c("lanterne"),
          material="Neon", name="Verre", **NDS)
    b.box((x - 0.9 * s, y + 1.9 * s, z - 0.9 * s), (x + 0.9 * s, y + 2.3 * s, z + 0.9 * s), cadre, name="Chapeau", **ND)
    b.box((x - 0.4 * s, y + 2.3 * s, z - 0.4 * s), (x + 0.4 * s, y + 2.8 * s, z + 0.4 * s), cadre, name="Anneau", **ND)


# ---------------------------------------------------------------------------
# 1. Arche du port (entrée de la zone)
# ---------------------------------------------------------------------------


def _pilier_mats(b, s: int, variant: int, H: float, rng) -> dict:
    """Une pile de l'arche : trois mâts liés sur un socle de pierre, contrefiches, bagues de cordage.

    Renvoie des points d'accroche utiles (sommet, côté extérieur)."""
    socle = c("rose") if variant % 2 else c("pierre_fonce")
    socle2 = c("rose_fonce") if variant % 2 else c("pierre")
    garniture = c("bleu_marine") if variant % 2 else c("corde")
    xa = s * 44.6                 # grand mât (face intérieure à |x| = 41,8)
    xb = s * 48.8                 # mâts secondaires, côté extérieur
    with b.group("Pile"):
        # socle en deux assises studdées
        x0, x1 = sorted((s * 40.6, s * 52.6))
        b.box((x0, 0, -6), (x1, 2.4, 6), socle, studs="top", name="Socle")
        x0, x1 = sorted((s * 41.4, s * 51.8))
        b.box((x0, 2.4, -5.2), (x1, 3.6, 5.2), socle2, studs="top", name="Assise")
        # bordé de planches autour du pied (caisson de bois)
        x0, x1 = sorted((s * 41.0, s * 52.2))
        b.box((x0, 3.6, -4.4), (x1, 7.4, 4.4), vary("bois_quai", rng, 0.04), studs="top", name="Caisson")
        b.box((x0 - 0.15, 5.2, -4.55), (x1 + 0.15, 5.8, 4.55), c("bois_fonce"), name="Ceinture", **ND)
        # mâts : grand mât au centre, deux plus fins derrière/devant côté extérieur
        top_a = H + 9.0
        b.cyl((xa, 3.6 + (top_a - 3.6) / 2, 0), 2.8, top_a - 3.6, vary("bois", rng, 0.04), name="GrandMat")
        for z, top in ((-2.35, H + 4.6), (2.35, H + 2.2)):
            b.cyl((xb, 3.6 + (top - 3.6) / 2, z), 2.0, top - 3.6, vary("bois_clair", rng, 0.05), name="Mat")
            b.cyl((xb, top + 0.25, z), 2.2, 0.5, c("bois_fonce"), studs="top", name="Chapeau")
        # bagues de cordage (ligatures)
        for y in (13.0, 27.0, 41.0):
            b.cyl((xa, y, 0), 3.05, 1.6, garniture, name="Ligature", **ND)
        for y, z in ((13.4, -2.35), (27.4, -2.35), (20.4, 2.35), (34.4, 2.35)):
            b.cyl((xb, y, z), 2.25, 1.2, garniture, name="Ligature", **ND)
        # hune (plateforme ronde) au sommet du grand mât
        b.cyl((xa, top_a + 0.4, 0), 3.6, 0.8, c("bois_fonce"), studs="top", name="Hune")
        b.cyl((xa, top_a + 1.25, 0), 3.3, 0.9, c("bois"), name="Garde", **ND)
        # contrefiches de pied vers l'extérieur (de part et d'autre de la palissade), jamais vers le couloir
        for sz in (-1, 1):
            _poutre(b, (s * 56.0, 0.4, sz * 3.3), (s * 50.0, 17.0, sz * 2.6), 1.4, c("bois_fonce"), name="Contrefiche")
    return {"x_mat": xa, "x_ext": s * 52.6, "sommet": top_a + 1.7}


def _planche_texte(b, x0, x1, y0, y1, texte, couleur, cadre, rng, name) -> None:
    """Panneau bleu marine lisible des deux côtés (deux pièces dos à dos) dans un cadre de bois."""
    marine = c("bleu_marine")
    avant = b.box((x0, y0, -0.45), (x1, y1, 0.0), marine, name=name)
    avant.label = {"face": "Front", "text": texte, "color": couleur, "bg": None, "font": "sans"}
    arriere = b.box((x0, y0, 0.0), (x1, y1, 0.45), marine, name=name)
    arriere.label = {"face": "Back", "text": texte, "color": couleur, "bg": None, "font": "sans"}
    e = 0.75
    b.box((x0 - e, y1, -0.7), (x1 + e, y1 + e, 0.7), cadre, studs="top", name="Cadre")
    b.box((x0 - e, y0 - e, -0.7), (x1 + e, y0, 0.7), cadre, name="Cadre")
    for xa, xb in ((x0 - e, x0), (x1, x1 + e)):
        b.box((xa, y0, -0.7), (xb, y1, 0.7), cadre, name="Cadre")
    # cordage clouté le long du bas du cadre (des deux côtés)
    for z in (-0.82, 0.82):
        b.box((x0 - 0.3, y0 - 0.55, z - 0.12), (x1 + 0.3, y0 - 0.25, z + 0.12), c("corde"), name="Corde", **NDS)


def _chaine(b, x, y_haut, y_bas, z: float = 0.0) -> None:
    """Chaînette verticale (maillons alternés) de y_haut à y_bas."""
    n = max(1, int(round((y_haut - y_bas) / 0.5)))
    h = (y_haut - y_bas) / n
    for k in range(n):
        ya = y_haut - (k + 1) * h
        if k % 2 == 0:
            b.box((x - 0.3, ya, z - 0.1), (x + 0.3, ya + h, z + 0.1), c("fer"), name="Maillon", **NDS)
        else:
            b.box((x - 0.1, ya, z - 0.3), (x + 0.1, ya + h, z + 0.3), c("fer"), name="Maillon", **NDS)


def _filet_drape(b, s: int) -> None:
    """Filet de pêche drapé du grand mât (à 14 de haut) vers une perche courte, côté apparition (+Z)."""
    xm, xp = s * 47.0, s * 60.0
    with b.group("Filet"):
        b.cyl((xp, 3.5, 6.5), 0.3, 7.0, c("bois_flotte"), name="Perche")
        b.box((xp - 0.6, 0, 5.9), (xp + 0.6, 0.5, 7.1), c("pierre_fonce"), name="Pierre", **ND)
        # nappe de filet (deux pans inclinés, mailles translucides) et ralingue
        for (xa, ya, za), (xb, yb, zb) in (((xm, 14.0, 4.6), (s * 53.5, 9.0, 5.6)), ((s * 53.5, 9.0, 5.6), (xp, 6.8, 6.5))):
            _poutre_plate(b, (xa, ya, za), (xb, yb, zb), 6.0, 0.12, c("filet"), transparency=0.35, name="Filet", **NDS)
        _segment(b, (xm, 14.2, 4.6), (xp, 7.0, 6.5), 0.1, c("corde_fonce"), name="Ralingue")
        for k, t in enumerate((0.3, 0.55, 0.8)):
            p = np.array((xm, 14.2, 4.6)) * (1 - t) + np.array((xp, 7.0, 6.5)) * t
            p[1] -= 0.7 * math.sin(math.pi * t)
            b.ball(tuple(p), 0.45, c("orange") if k % 2 else c("blanc"), name="Flotteur", **ND)


def _poutre_plate(b, a, bb, larg: float, ep: float, col, name: str = "Pan", **kw) -> None:
    """Plaque de largeur `larg` (pendant vers le bas, -Y) dont le bord haut va de a à bb."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    d = bb - a
    n = float(np.linalg.norm(d))
    x = d / n
    zz = np.cross(x, np.array([0.0, 1.0, 0.0]))
    zz /= np.linalg.norm(zz)
    y = np.cross(zz, x)
    centre = (a + bb) / 2 - y * larg / 2
    b.part("block", (n, larg, ep), centre, np.column_stack([x, y, zz]), col, name=name, **kw)


def _pieu(b, x, y_haut, z, larg, ep, col) -> None:
    """Pieu de palissade : planche épaisse et pointe en losange."""
    b.box((x - larg / 2, 0, z - ep / 2), (x + larg / 2, y_haut, z + ep / 2), col, name="Pieu")
    d = larg / math.sqrt(2)
    b.part("block", (d, d, ep * 0.9), (x, y_haut, z), rot_z(45), shade(col, 0.92), name="Pointe")


def _palissade(b, s: int, x_debut: float, x_fin: float, variant: int, rng) -> None:
    """Palissade de pieux pointus le long de z ≈ 0, de |x| = x_debut à x_fin, poteaux forts tous les ~19 studs."""
    garniture = c("bleu_marine") if variant % 2 else c("corde")
    cols = ("bois", "bois_clair", "bois_flotte", "bois_quai")
    forts = [x_debut + 7 + k * 19.5 for k in range(5) if x_debut + 7 + k * 19.5 < x_fin - 3]
    vigie = x_debut + (x_fin - x_debut) * 0.55
    forts = [f for f in forts if abs(f - vigie) > 7]
    with b.group("Palissade"):
        # pieux
        x = x_debut + 0.2
        k = 0
        while x < x_fin - 1.0:
            larg = 3.0
            xc = x + larg / 2
            if not any(abs(xc - f) < 2.6 for f in forts) and abs(xc - vigie) > 0.8:
                h = 6.4 + float(rng.uniform(0, 1.6)) + (0.6 if k % 3 == 0 else 0.0)
                _pieu(b, s * xc, h, float(rng.uniform(-0.15, 0.15)), larg - 0.15, 1.6,
                      vary(cols[int(rng.integers(len(cols)))], rng, 0.06))
            x += larg
            k += 1
        # lisses (côté couloir en bas, côté apparition en haut)
        xa, xb = sorted((s * x_debut, s * x_fin))
        b.box((xa, 1.8, -1.25), (xb, 2.6, -0.8), c("bois_fonce"), name="Lisse")
        b.box((xa, 4.4, 0.8), (xb, 5.2, 1.25), c("bois_fonce"), name="Lisse")
        # poteaux forts : rondins, ligature, lanterne ou bouée
        for i, f in enumerate(forts):
            xf = s * f
            b.cyl((xf, 5.5, 0), 1.25, 11.0, vary("bois", rng, 0.05), studs="top", name="Poteau")
            b.cyl((xf, 7.5, 0), 1.42, 0.9, garniture, name="Ligature", **ND)
            # potence courte et lanterne côté couloir (-Z), alternée côté apparition (+Z)
            fz = -1 if i % 2 == 0 else 1
            b.box((xf - 0.25, 10.0, fz * 1.0), (xf + 0.25, 10.5, fz * 2.9), c("bois_fonce"), name="Potence", **ND)
            _lanterne_navire(b, xf, 7.3, fz * 2.4, 0.8)
        # tour de guet basse sur la palissade
        xv = s * vigie
        with b.group("Guet"):
            for dx in (-2.6, 2.6):
                for dz in (-2.6, 2.6):
                    b.cyl((xv + dx, 6.5, dz), 0.6, 13.0, c("bois_fonce"), name="Pied")
            b.box((xv - 3.6, 9.6, -3.6), (xv + 3.6, 10.4, 3.6), c("bois_quai"), studs="top", name="Plancher")
            for dz in (-3.4, 3.4):
                b.box((xv - 3.4, 10.4, dz - 0.2), (xv + 3.4, 12.2, dz + 0.2), c("bois_clair"), name="Garde", **ND)
            b.box((xv - 3.6, 13.0, -3.6), (xv + 3.6, 13.5, 3.6), c("bois_fonce"), name="Toit")
            b.wedge((xv - 4.2, 13.5, -4.2), (xv + 4.2, 15.2, 0), c("toit_rouge"), down="-z", studs="top", name="Toit")
            b.wedge((xv - 4.2, 13.5, 0), (xv + 4.2, 15.2, 4.2), c("toit_rouge_fonce"), down="+z", studs="top", name="Toit")


def porte_entree(b, variant: int = 0, ouverture: float = 80, hauteur: float = 50, mur: float = 130) -> dict:
    """Arche du port : deux piles en mâts liés, vergue à voile ferlée, panneau de jeu suspendu, palissades.

    Origine au centre de l'ouverture au sol, arche dans le plan z = 0. Les joueurs arrivent par +Z ; le panneau
    se lit des deux côtés. Le dessous de tout ce qui enjambe le couloir est à y ≥ 35."""
    rng = b.rng
    H = hauteur
    cadre = c("rose") if variant % 2 else c("bois_fonce")
    # Étagement du panneau (de bas en haut) : bas à 35 au-dessus du couloir.
    yv0, yv1 = 35.75, 42.25          # « VITESSE CONSEILLÉE : 200 »
    yz0, yz1 = 44.6, 52.6            # « ZONE RARE »
    yp0 = yz1 + 0.75                 # dessous de la poutre
    yp1 = yp0 + 3.2                  # dessus de la poutre (≈ hauteur + 6)
    with b.group("Arche"):
        piles = [_pilier_mats(b, s, variant, H, rng) for s in (-1, 1)]
        # poutre maîtresse (vergue carrée) traversant les mâts
        b.box((-57.5, yp0, -2.4), (57.5, yp1, 2.4), c("bois_fonce"), studs="top", name="Poutre")
        for s in (-1, 1):
            xa, xb = sorted((s * 57.5, s * 59.0))
            b.box((xa, yp0 + 0.4, -2.0), (xb, yp1 - 0.4, 2.0), c("bois"), studs="top", name="Embout")
            # aisseliers sous la poutre (au-dessus de y = 44, hors couloir)
            _poutre(b, (s * 42.0, 44.0, 0), (s * 34.0, yp0 + 0.3, 0), 1.4, c("bois"), name="Aisselier")
            # bandes de fer décoratives
            for xx in (36.0,):
                b.box((s * xx - 0.4, yp0 - 0.12, -2.55), (s * xx + 0.4, yp1 + 0.12, 2.55), c("fer"), name="Ferrure", **ND)
        # voile ferlée sur la vergue (en deux moitiés, la barre au milieu), rabans de cordage
        for s in (-1, 1):
            xa, xb = sorted((s * 5.0, s * 39.0))
            b.cyl(((xa + xb) / 2, yp1 + 1.2, 0), 1.35, xb - xa, c("voile"), axis="x", name="VoileFerlee", **ND)
            b.cyl(((xa + xb) / 2, yp1 + 1.25, -0.25), 1.2, xb - xa - 3, c("voile_ombre"), axis="x", name="Pli", **NDS)
            for k in range(3):
                xx = s * (11.0 + k * 11.0)
                b.cyl((xx, yp1 + 1.2, 0), 1.5, 0.6, c("corde"), axis="x", name="Raban", **ND)
        # barre de navire au centre de la poutre
        with b.at((0, yp1, 0)):
            barre_navire(b, variant=2 if variant % 2 == 0 else 1, taille=1.6)

        # panneau de jeu
        with b.group("Panneau"):
            _planche_texte(b, -25.0, 25.0, yz0, yz1, "ZONE RARE", (0xB4, 0x8C, 0xFF), cadre, rng, "ZoneRare")
            _planche_texte(b, -38.0, 38.0, yv0, yv1, "VITESSE CONSEILLÉE : 200", (0xFF, 0xE3, 0x7A), cadre, rng,
                           "Vitesse")
            # ferrures d'accroche sous la poutre (ZONE RARE) et chaînes entre les deux planches
            for xx in (-18.0, 18.0):
                for z in (-0.95, 0.95):
                    b.box((xx - 0.7, yz1 - 1.6, z - 0.12), (xx + 0.7, yp0 + 0.5, z + 0.12), c("fer"), name="Ferrure", **ND)
            for xx in (-21.0, 21.0):
                _chaine(b, xx, yz0 - 0.75, yv1 + 0.75)
            # lanternes suspendues sous la poutre, de part et d'autre du panneau
            for s in (-1, 1):
                _chaine(b, s * 31.5, yp0, yp0 - 1.6)
                _lanterne_navire(b, s * 31.5, yp0 - 4.4, 0, 1.0)

        # pavillons génériques au sommet des grands mâts (ils flottent vers l'extérieur)
        for s, p in zip((-1, 1), piles):
            with b.at((p["x_mat"], p["sommet"], 0), yaw=0 if s > 0 else 180):
                drapeau_pirate(b, variant=0, hauteur=10, largeur=7, mat=True)

        # habillage des piles : bouées, rames croisées, lanternes, filet, cordages enroulés
        with b.group("Habillage"):
            for s, p in zip((-1, 1), piles):
                xm = p["x_mat"]
                for face in (-1, 1):
                    with b.at((xm, 17.0, face * 3.05), yaw=0 if face < 0 else 180):
                        bouee(b, variant=1, rayon=1.5)
                    # lanterne de pile sur console (à |x| ≥ 40)
                    b.box((xm - 0.3, 25.4, face * 2.6), (xm + 0.3, 25.9, face * 4.6), c("fer"), name="Console", **ND)
                    _lanterne_navire(b, xm, 22.2, face * 4.3, 0.9)
                # rames croisées sur la face des mâts secondaires (avant à gauche, arrière à droite)
                fz = -4.55 if s < 0 else 4.55
                xb = s * 48.8
                for ang in (25, -25):
                    R = rot_z(ang)
                    b.part("block", (0.5, 11.0, 0.3), (xb, 22.0, fz), R, c("bois_clair"), name="Rame", **ND)
                    pale = R @ np.array([0, -5.2, 0]) + np.array([xb, 22.0, fz])
                    b.part("block", (1.3, 3.0, 0.32), tuple(pale), R, c("rouge") if ang > 0 else c("blanc"), name="Pale", **ND)
                # rouleaux de cordage au pied
                for (dx, dz) in ((5.5, -7.5),):
                    x = s * (46.6 + dx)
                    b.cyl((x, 0.35, dz), 1.5, 0.7, c("corde"), studs="top", name="Rouleau", **ND)
                    b.cyl((x, 0.85, dz), 1.0, 0.3, c("corde_fonce"), name="Rouleau", **ND)

    # accessoires au pied (tous à |x| ≥ 40)
    with b.group("Abords"):
        with b.at((-57.5, 0, -7.0), yaw=-20):
            tonneaux(b, variant=1)
        with b.at((44.5, 0, -8.8), yaw=80):
            tonneaux(b, variant=2)
        with b.at((-50.5, 0, 9.4), yaw=170):
            caisses(b, variant=0)
        with b.at((58.0, 0, 7.6), yaw=195):
            caisses(b, variant=1)
        with b.at((61.5, 0, -6.8), yaw=0):
            ancre(b, variant=2, taille=0.9)
        _filet_drape(b, -1)
        # guirlandes de fanions du haut des piles vers les poteaux de la palissade
        for s in (-1, 1):
            guirlande_fanions(b, (s * 47.0, 34.0, -1.6), (s * 79.1, 10.6, -1.3), n=5, creux=1.8, variant=0 if s < 0 else 2)

    with b.group("Palissades"):
        for s in (-1, 1):
            _palissade(b, s, 52.6, mur, variant, rng)

    return {"emprise": (2 * mur, 12), "hauteur": round(H + 9 + 1.7 + 10.5, 1)}


# ---------------------------------------------------------------------------
# 2. Rocher du crâne (repère final, le couloir passe par la bouche)
# ---------------------------------------------------------------------------


def _palmier(b, x, y, z, h: float, cap: float, rng) -> None:
    """Petit palmier courbé (9 pièces) : tronc en deux tronçons, couronne, cinq palmes, une noix."""
    a = math.radians(cap)
    d = np.array([math.sin(a), 0.0, -math.cos(a)])         # direction de l'inclinaison
    base = np.array([x, y, z], float)
    pts = [base]
    for k in range(1, 3):
        t = k / 2
        pts.append(base + np.array([0, h * t, 0]) + d * (h * 0.3 * t * t))
    for k in range(2):
        _segment(b, pts[k] - np.array([0, 0.3, 0]), pts[k + 1], 0.6 - 0.15 * k, vary("tronc", rng, 0.06),
                 name="Tronc", collide=(k == 0), shadow=True)
    top = pts[-1]
    b.ball(tuple(top), 1.0, c("palme_fonce"), name="Couronne", **ND)
    for k in range(5):
        ang = cap + k * 72 + float(rng.uniform(-12, 12))
        R = rot_y(-ang) @ rot_x(-22 if k % 2 else -30)
        centre = top + R @ np.array([0, 0, -3.0]) + np.array([0, -0.4, 0])
        b.part("block", (1.6, 0.3, 6.2), tuple(centre), R, c("palme") if k % 2 else c("palme_claire"), name="Palme", **ND)
    b.ball((top[0] + 0.5, top[1] - 0.9, top[2] + 0.4), 0.5, c("coco"), name="Coco", **NDS)


def _emettre(b, M, t, shape, size, centre, R, col, **kw) -> None:
    """Pose une pièce exprimée dans un repère local tourné (M) et translaté (t) : épave inclinée."""
    b.part(shape, size, tuple(M @ np.asarray(centre, float) + np.asarray(t, float)), M @ R, col, **kw)


def _epave(b, x, z, rng) -> None:
    """Épave générique échouée et couchée sur le flanc (coque cassée, membrures, mât brisé, voile déchirée)."""
    M = rot_y(-14) @ rot_z(5) @ rot_x(20)
    t = np.array([x, -1.4, z])
    I = np.eye(3)
    rouge, fonce, clair = c("coque_rouge"), c("bois_fonce"), c("bois_clair")

    def bx(a, bb, col, **kw):
        a, bb = np.asarray(a, float), np.asarray(bb, float)
        _emettre(b, M, t, "block", tuple(bb - a), (a + bb) / 2, I, col, **kw)

    def diamant(xc, y0, y1, demi, col):
        d = demi * math.sqrt(2)
        _emettre(b, M, t, "block", (d, y1 - y0, d), (xc, (y0 + y1) / 2, 0), rot_y(45), col)

    with b.group("Epave"):
        bx((-19, 0, -1.4), (19, 1.6, 1.4), fonce, name="Quille")
        bx((-17, 1.6, -4.0), (15, 4.6, 4.0), vary("coque_rouge", rng, 0.04), name="Coque")
        diamant(15, 1.6, 4.6, 4.0, rouge)
        # bordé supérieur cassé au milieu (trou béant : membrures visibles)
        for xa, xb in ((-18, -7), (3, 17)):
            bx((xa, 4.6, -5.6), (xb, 8.0, 5.6), vary("coque_rouge", rng, 0.05), studs="top", name="Coque")
            bx((xa, 8.0, -5.0), (xb, 8.5, 5.0), vary("bois_clair", rng, 0.05), studs="top", name="Pont")
            bx((xa, 5.6, 5.6), (xb, 6.3, 5.8), fonce, name="Preceinte", **ND)
            bx((xa, 8.0, 5.0), (xb, 9.6, 5.6), fonce, name="Lisse", **ND)
        diamant(17, 4.6, 8.0, 5.6, rouge)
        bx((20.0, 6.5, -0.4), (27.0, 7.3, 0.4), fonce, name="Beaupre", **ND)
        for xr in (-5.0, -2.0, 1.0):
            for sz in (-1, 1):
                bx((xr - 0.4, 4.6, sz * 5.4 - 0.4), (xr + 0.4, 9.8 - abs(xr + 2.0) * 0.4, sz * 5.4 + 0.4), fonce,
                   name="Membrure")
        bx((-7, 4.6, -4.6), (3, 5.0, 4.6), c("grotte"), name="Cale")
        for xg in (6.0, 10.5, -12.5):
            bx((xg - 0.8, 5.4, 5.6), (xg + 0.8, 7.2, 5.75), c("noir"), name="Sabord", **ND)
        # château arrière (fenêtres de poupe)
        bx((-18, 8.5, -5.0), (-11, 12.5, 5.0), vary("coque_rouge", rng, 0.05), studs="top", name="Chateau")
        bx((-18.15, 9.6, -3.6), (-17.9, 11.4, 3.6), c("fenetre"), name="Fenetres", **ND)
        bx((-18.4, 12.5, -5.2), (-10.8, 13.4, 5.2), fonce, name="Garde", **ND)
        # mât de misaine brisé et mât d'artimon avec vergue et voile déchirée
        _emettre(b, M, t, "cyl", (10.0, 1.3, 1.3), (9.0, 13.3, 0), rot_z(90), c("bois"), name="MatBrise")
        _emettre(b, M, t, "wedge", (1.3, 1.6, 1.3), (9.0, 19.1, 0), I, c("bois_pale"), name="Cassure", **ND)
        _emettre(b, M, t, "cyl", (14.0, 1.0, 1.0), (-14.5, 19.5, 0), rot_z(90), c("bois"), name="Artimon")
        _emettre(b, M, t, "cyl", (12.0, 0.6, 0.6), (-14.5, 24.0, 0), rot_y(90), fonce, name="Vergue", **ND)
        for zc, h, col in ((-3.6, 7.5, "voile"), (-0.4, 4.5, "voile_ombre"), (3.0, 6.0, "voile")):
            _emettre(b, M, t, "block", (0.2, h, 3.0), (-14.2, 24.0 - h / 2, zc), rot_x(float(rng.uniform(-8, 8))), c(col),
                     name="VoileDechiree", **ND)
        _emettre(b, M, t, "block", (0.18, 3.6, 4.6), (-14.5, 28.2, -2.3), I, c("drapeau_noir"), name="Pavillon", **ND)
        _emettre(b, M, t, "block", (0.24, 1.5, 1.5), (-14.5, 28.4, -2.3), I, c("tete_mort"), name="Crane", **ND)
    # mât tombé sur la plage, rochers de calage, tonneaux renversés et coffre
    with b.group("EpaveAbords"):
        _segment(b, (x + 24, -0.2, z + 9), (x + 6, 1.4, z + 13), 0.65, c("bois"), name="MatTombe", collide=True, shadow=True)
        _segment(b, (x + 20, -0.3, z + 6.5), (x + 21, 0.8, z + 14), 0.35, c("bois_fonce"), name="Vergue")
        b.box((x + 19.5, -0.62, z + 9), (x + 26, -0.4, z + 15), c("voile_ombre"), name="Voile", **NDS)
        for (dx, dz, w, h) in ((-12, 2, 8, 5), (12, -1, 7, 4), (-1, 9, 5, 2.5)):
            b.box((x + dx - w / 2, -3, z + dz - w / 2), (x + dx + w / 2, h - 1, z + dz + w / 2), vary("roche", rng, 0.06),
                  studs="top", name="Rocher")
        with b.at((x + 6, -0.6, z + 15), yaw=30):
            tonneaux(b, variant=2)
        with b.at((x - 6, -0.6, z + 15), yaw=-15):
            coffre_tresor(b, variant=2)


def _decor_variant(nom: str, variant: int):
    """Couleur du rocher selon la variante (0 : ivoire ; 1 : pierre grise chaude)."""
    if variant % 2 == 0:
        return c(nom)
    table = {"os": "roche_claire", "os_clair": "pierre_claire", "os_fonce": "roche", "os_ombre": "roche_fonce"}
    return c(table.get(nom, nom))


def rocher_crane(b, variant: int = 0, passage: float = 64, largeur: float = 440, profondeur: float = 34,
                 hauteur: float = 100) -> dict:
    """Rocher marin en tête de mort générique : le couloir passe par la bouche (plafond ≥ 36).

    Origine : centre de l'entrée du passage, au sol, sur la façade. Exception à la règle -Z : le rocher regarde +Z
    (vers les joueurs qui arrivent) et s'étend jusqu'à z = -profondeur. Façade en « pixels » de 2 studs (blocs
    fusionnés), reliefs en gradins studdés ; bouche, dents, couloir intérieur, falaises, épave, cascade."""
    rng = b.rng
    D = float(profondeur)
    L2 = largeur / 2
    P2 = passage / 2                      # 32 : demi-largeur du passage libre
    k = hauteur / 100.0
    CELL = 2.0
    nx = int(round(largeur / CELL))
    ys = [-3.0] + [float(v) for v in range(0, int(hauteur) + 4, 2)]
    ny = len(ys) - 1
    col_f = lambda n: _decor_variant(n, variant)

    # profil des falaises : basses et en retrait près du crâne (sa silhouette se détache sur le ciel),
    # crête vers |x| = 120-140, puis gradins qui descendent vers le bord de la zone
    paliers = [(92, 34), (104, 44), (118, 54), (134, 60), (150, 52), (168, 44), (186, 38), (204, 32), (999, 26)]
    jit = {}

    def h_falaise(ax: float, s: int) -> float:
        key = (s, int(ax // 12))
        if key not in jit:
            jit[key] = float(rng.choice([0, 0, 2, -2, 4, -4]))
        for lim, h in paliers:
            if ax < lim:
                return (h + jit[key]) * k
        return 26 * k

    def z_falaise(ax, y, hc, s) -> float:
        t = y / max(hc, 1)
        j = -2.0 * (int(ax // 12 + (s > 0)) % 3)
        recul = -10.0 if ax < 100 else -4.0 if ax < 112 else 0.0
        if y < 0 or t < 0.18:
            return 2.0 if ax >= 62 else 0.0
        if t < 0.5:
            return min(0.0 + j, 0.0) + recul * 0.5
        if t < 0.8:
            return -4.0 + j + recul
        return -8.0 + j + recul

    fissures = [((-12, 98), (-6, 90)), ((-6, 90), (-10, 82)), ((46, 94), (52, 86)), ((52, 86), (48, 80)),
                ((-60, 88), (-68, 80)), ((-68, 80), (-64, 74)), ((64, 56), (68, 50))]

    def dist_seg(px, py, a, bb) -> float:
        ax_, ay_ = a
        bx_, by_ = bb
        vx, vy = bx_ - ax_, by_ - ay_
        t = max(0.0, min(1.0, ((px - ax_) * vx + (py - ay_) * vy) / (vx * vx + vy * vy)))
        return math.hypot(px - ax_ - t * vx, py - ay_ - t * vy)

    A_CR, YC, B_CR = 78.0, 64.0 * k, 36.0 * k      # ellipse du crâne (le plus large à hauteur des yeux)
    EX, EY, EA, EB = 29.0, 64.0 * k, 14.0, 11.0     # orbites

    def demi_largeur(y) -> float:
        """Silhouette du crâne : calotte ronde, tempes, pommettes, mâchoire plus étroite."""
        if y >= YC:
            v = 1.0 - ((y - YC) / B_CR) ** 2
            return A_CR * math.sqrt(v) if v > 0 else -1.0
        if y >= 52 * k:
            return A_CR - (YC - y) * 0.5
        if y >= 42 * k:
            return A_CR - (YC - 52 * k) * 0.5 - (52 * k - y) * 1.3
        return 56.0 - max(0.0, 8.0 - y) * 0.6

    def cellule(x, y):
        ax = abs(x)
        s = 1 if x > 0 else -1
        if ax < 44 and y < 42 * k:
            return None                                   # bouche et parois : posées à la main
        hc = h_falaise(ax, s)
        if ax > demi_largeur(y):
            if ax >= 52 and y < hc:
                # falaise : herbe au sommet, roches claires en haut, foncées en bas ; cascade à droite
                zf = z_falaise(ax, y, hc, s)
                if s > 0 and 150 <= ax <= 162 and y >= 8:
                    return ("roche_fonce", zf - 6)
                if y + 2 >= hc:
                    return ("herbe", zf)
                if y + 4 >= hc:
                    return ("terre", zf)
                t = y / hc
                return ("roche_claire" if t > 0.62 else "roche" if t > 0.22 else "roche_fonce", zf)
            return None
        # calotte : gradins qui reculent vers les bords (arrondi), teinte plus sombre en retrait
        r2 = (x / A_CR) ** 2 + (max(y - YC, 0.0) / B_CR) ** 2
        zd = -4.0 * round(20.0 * r2 ** 1.7 / 4.0)
        base = ("os_clair" if zd >= -4 and y >= 78 * k else "os" if zd >= -8 else "os_fonce" if zd >= -16 else "os_ombre")
        # orbites
        e = ((ax - EX) / EA) ** 2 + ((y - EY) / EB) ** 2
        if e <= 1.0:
            return ("grotte", -9.0)
        if e <= 1.5:
            return ("os_ombre", min(zd, 0.0) - 3.0)
        # arcades sourcilières en surplomb (au-dessus de y = 45 : avancée permise)
        if EY + EB + 1 <= y < EY + EB + 5 and abs(ax - EX) <= 16:
            return ("os_clair", 3.0)
        # fissures
        for a, bb in fissures:
            if dist_seg(x, y, a, bb) < 1.1:
                return ("os_ombre", zd - 1.0)
        # nez (cœur renversé)
        if 42 * k <= y < 53 * k:
            hw = 7.5 * (53 * k - y) / (11 * k)
            if ax < hw and not (y < 45 * k and ax < 1.6):
                return ("grotte", -7.0)
            if ax < hw + 2.2:
                return ("os_fonce", -2.0)
        if 42 * k <= y < 47 * k and ax < 44:
            return ("os", -1.0)                           # maxillaire au-dessus des dents
        if 42 * k <= y < 56 * k and 46 <= ax:             # pommettes saillantes
            zc = 3.0 if 62 <= ax else 0.0
            return ("os_clair" if y >= 52 * k else "os", zc)
        if 42 * k <= y < 56 * k and 42 <= ax < 46:
            return ("os_fonce", -3.0)                     # creux sous la pommette
        if y < 42 * k:                                    # mâchoire, de part et d'autre de la bouche
            if y >= 36 * k:
                return ("os", -1.0)
            return ("os_ombre" if y < 6 else "os_fonce", -3.0 if ax > 52 else -2.0)
        return (base, zd)

    # grille de façade
    grille = np.empty((ny, nx), dtype=object)
    for j in range(ny):
        yc = (ys[j] + ys[j + 1]) / 2
        for i in range(nx):
            grille[j, i] = cellule(-L2 + (i + 0.5) * CELL, yc)

    def dessus(x, z):
        """Hauteur du dessus du rocher en (x, z) (pour poser herbe, palmiers, mouettes)."""
        i = int((x + L2) // CELL)
        for j in range(ny - 1, -1, -1):
            v = grille[j, i]
            if v is not None and v[1] >= z:
                return ys[j + 1]
        return None

    from textures import mask_rects
    with b.group("Facade"):
        cles = {v for v in grille.reshape(-1) if v is not None}
        for cle in sorted(cles, key=str):
            nom, zf = cle
            m = np.zeros((ny, nx), bool)
            for j in range(ny):
                for i in range(nx):
                    m[j, i] = grille[j, i] == cle
            for (i, j, w, h) in mask_rects(m):
                x0, x1 = -L2 + i * CELL, -L2 + (i + w) * CELL
                y0, y1 = ys[j], ys[j + h]
                col = vary(col_f(nom), rng, 0.035) if nom not in ("grotte",) else col_f(nom)
                mat = "Grass" if nom == "herbe" else "SmoothPlastic"
                b.box((x0, y0, -D), (x1, y1, zf), col, studs="top", material=mat,
                      name="Orbite" if nom == "grotte" else "Rocher")

    # --- bouche : dents, gencives, parois en gradins, niche au trésor, cadre de sortie -----------------
    os_, osc, osf, oso = col_f("os"), col_f("os_clair"), col_f("os_fonce"), col_f("os_ombre")
    YJ = 42.0 * k                                   # dessous de la mâchoire supérieure (plafond du passage)
    ZT = -4.5                                       # profondeur des dents
    with b.group("Bouche"):
        # dents du haut : 8 grosses dents carrées au-dessus du couloir (bas ≥ 36), une de plus de chaque côté
        n, w, g = 8, 6.6, 1.2
        x0 = -(n * w + (n - 1) * g) / 2
        for t in range(n):
            xa = x0 + t * (w + g)
            yb = 36.4 + float(rng.uniform(0, 1.2)) + (0.6 if t in (0, n - 1) else 0.0)
            b.box((xa, yb, ZT), (xa + w, YJ, 0.0), vary(osc, rng, 0.03), studs="top", name="Dent")
        for sgn in (-1, 1):
            xa, xb = sorted((sgn * (P2 + 0.2), sgn * 37.4))
            b.box((xa, 33.0, ZT), (xb, YJ, 0.0), vary(osc, rng, 0.03), name="Dent")
            # dents du bas, posées au sol à côté du couloir
            xa, xb = sorted((sgn * (P2 + 0.4), sgn * 37.6))
            b.box((xa, 0, ZT), (xb, 9.5, 0.0), vary(osc, rng, 0.03), studs="top", name="DentBas")
            xa, xb = sorted((sgn * 38.2, sgn * 43.8))
            b.box((xa, 0, ZT), (xb, 8.0, 0.0), vary(osc, rng, 0.03), studs="top", name="DentBas")
            # gencive (front de mâchoire) au-dessus des dents du bas
            xa, xb = sorted((sgn * 37.6, sgn * 44.0))
            b.box((xa, 8.0, ZT), (xb, 33.0, -0.5), osf, name="Machoire")
            xa, xb = sorted((sgn * 37.4, sgn * 44.0))
            b.box((xa, 33.0, ZT), (xb, YJ, -0.5), os_, name="Machoire")
            b.box((xa, 8.0, -0.5), (xb, 9.0, 0.0), osc, studs="top", name="Gencive")
            # parois intérieures en gradins (côté couloir), niche du trésor à droite
            niche = sgn > 0
            zs = [(-D, -22.0), (-14.0, ZT)] if niche else [(-D, ZT)]
            for za, zb in zs:
                xa, xb = sorted((sgn * 40.0, sgn * 44.0))
                b.box((xa, -3.0, za), (xb, YJ, zb), oso, name="Paroi")
                xa, xb = sorted((sgn * 37.0, sgn * 40.0))
                b.box((xa, 2.5, za), (xb, YJ, zb), osf, studs="top", name="Paroi")
                xa, xb = sorted((sgn * 33.0, sgn * 40.0))
                b.box((xa, 0.0, za), (xb, 2.5, zb), vary(oso, rng, 0.04), studs="top", name="Banquette")
            if niche:
                b.box((40.0, 11.0, -22.0), (44.0, YJ, -14.0), oso, name="Paroi")
                b.box((37.0, 11.0, -22.0), (40.0, YJ, -14.0), osf, name="Paroi")
                b.box((40.0, -3.0, -22.0), (44.0, 0.2, -14.0), c("sable"), studs="top", name="SolNiche")
                with b.at((41.6, 0.2, -18.0), yaw=90):
                    coffre_tresor(b, variant=0)
                b.box((43.6, 6.0, -18.6), (44.0, 7.0, -17.4), c("fer"), name="Support", **ND)
                b.box((43.0, 7.0, -18.4), (43.8, 8.2, -17.6), c("flamme"), material="Neon", name="Flamme", **NDS)
            # consoles (coins arrondis du plafond)
            xa, xb = sorted((sgn * P2 + sgn * 0.2, sgn * 37.0))
            b.wedge_under((xa, 36.0, -D), (xb, YJ, ZT), osf, down="-x" if sgn > 0 else "+x", name="Console")
            # lanternes de paroi (potence fixée au gradin, verre à |x| ≥ 33)
            for zl in (-9.0, -27.0) if niche else (-9.0, -18.0, -27.0):
                xm = sgn * 37.0
                xa, xb = sorted((xm, sgn * 34.4))
                b.box((xa, 14.0, zl - 0.25), (xb, 14.5, zl + 0.25), c("fer"), name="Potence", **ND)
                _lanterne_navire(b, sgn * 34.9, 10.6, zl, 0.95)
        # cadre de sortie (côté zone suivante)
        for sgn in (-1, 1):
            xa, xb = sorted((sgn * (P2 + 0.4), sgn * 40.0))
            b.box((xa, 0, -D - 1.5), (xb, YJ, -D), osf, studs="top", name="CadreSortie")
        b.box((-40.0, YJ - 3.0, -D - 1.5), (40.0, YJ + 4.0, -D), osf, studs="top", name="CadreSortie")

    # --- ornements du crâne : lueurs dans les orbites, herbe, palmiers, mouettes, pavillon ---------------
    with b.group("Ornements"):
        for sgn in (-1, 1):
            b.box((sgn * EX - 3.0 + sgn * 3.0, EY + 2.0, -9.0), (sgn * EX + 0.0 + sgn * 3.0, EY + 4.0, -8.7),
                  mix(c("grotte"), c("lanterne"), 0.55), material="Neon", name="Lueur", **NDS)
        # touffes d'herbe et de mousse sur les gradins du crâne
        touffes = [(-60, -20), (-44, -24), (-22, -28), (-6, -30), (14, -29), (34, -26), (52, -22), (66, -18),
                   (-70, -12), (72, -10), (-36, -12), (40, -14)]
        for (tx, tz) in touffes:
            y = dessus(tx, tz)
            if y is None:
                continue
            w = float(rng.uniform(2.5, 5.0))
            col = c("herbe") if rng.uniform() < 0.6 else c("roche_mousse")
            b.box((tx - w / 2, y - 0.2, tz - 1.8), (tx + w / 2, y + 0.7, tz + 1.8), col, studs="top", name="Herbe", **ND)
        for (px, pz, h, cap) in ((-48, -26, 13, -40), (-30, -30, 11, 10), (44, -26, 14, 50), (60, -22, 10, 120)):
            y = dessus(px, pz)
            if y is not None:
                _palmier(b, px, y, pz, h * k, cap, rng)
        # pavillon au sommet
        xm, zm = 8.0, -24.0
        ym = dessus(xm, zm) or hauteur
        b.box((xm - 2.0, ym, zm - 2.0), (xm + 2.0, ym + 1.4, zm + 2.0), c("roche"), studs="top", name="Cairn")
        b.cyl((xm, ym + 1.4 + 8.0, zm), 0.6, 16.0, c("bois_fonce"), name="Mat")
        b.cyl((xm, ym + 6.0, zm), 0.75, 0.8, c("corde"), name="Ligature", **ND)
        with b.at((xm, ym + 1.4 + 16.0 - 9.6, zm)):
            drapeau_pirate(b, variant=0, hauteur=9.6, largeur=11.0, mat=False)
        b.ball((xm, ym + 17.8, zm), 0.6, c("or"), name="Pomme", **ND)
        # mouettes sur les corniches
        for (gx, gz, yaw, v) in ((-30, EY + EB + 5, 20, 0), (26, EY + EB + 5, -30, 1), (70, YC, 160, 0), (-66, YC, 200, 1)):
            y = dessus(gx, 1.5 if abs(gx) < 40 else 1.0)
            if y is not None:
                with b.at((gx, y, 1.0), yaw=yaw):
                    mouette(b, variant=v)

    # --- mer : écume au pied, pitons rocheux, épave (gauche), cascade (droite) ---------------------------
    with b.group("Mer"):
        for sgn in (-1, 1):
            segs = [(57.0, 62.0, 0.0), (62.0, 100.0, 2.0), (104.0, 150.0, 2.0), (154.0, 219.0, 2.0)]
            for xa_, xb_, zf in segs:
                xa, xb = sorted((sgn * xa_, sgn * xb_))
                b.box((xa, -1.75, zf), (xb, -1.2, zf + float(rng.uniform(1.0, 2.2))), c("ecume"), name="Ecume", **NDS)
        pitons = [(-84, 14, 7, 16), (-202, 18, 9, 24), (88, 12, 6, 13), (128, 20, 9, 22), (198, 12, 10, 30)]
        for (px, pz, r, h) in pitons:
            with b.group("Piton"):
                b.box((px - r, -3, pz - r * 0.8), (px + r, h * 0.45, pz + r * 0.8), vary("roche_fonce", rng, 0.05),
                      studs="top", name="Piton")
                b.box((px - r * 0.75, h * 0.45, pz - r * 0.6), (px + r * 0.7, h * 0.8, pz + r * 0.55), vary("roche", rng, 0.05),
                      studs="top", name="Piton")
                b.box((px - r * 0.5, h * 0.8, pz - r * 0.4), (px + r * 0.45, h, pz + r * 0.35), vary("roche_claire", rng, 0.05),
                      studs="top", name="Piton")
                b.box((px - r * 0.45, h, pz - r * 0.35), (px + r * 0.4, h + 0.6, pz + r * 0.3), c("herbe"), studs="top",
                      material="Grass", name="Herbe", **ND)
                b.box((px - r - 0.8, -1.75, pz - r * 0.8 - 0.8), (px + r + 0.8, -1.2, pz + r * 0.8 + 0.8), c("ecume"),
                      name="Ecume", **NDS)
        # plage et épave à gauche
        b.box((-180, -3.0, -1.0), (-120, -0.6, 16.0), c("sable"), studs="top", material="Sand", name="Plage")
        b.box((-176, -3.0, 16.0), (-124, -1.2, 19.0), c("sable_mouille"), studs="top", material="Sand", name="Plage")
        b.box((-177, -1.75, 19.0), (-123, -1.25, 20.2), c("ecume"), name="Ecume", **NDS)
        _epave(b, -150.0, 7.0, rng)
        # cascade à droite (tombe de la faille de la falaise)
        hc = h_falaise(156.0, 1)
        zc = z_falaise(156.0, hc * 0.9, hc, 1) - 6
        b.box((151.0, hc - 0.2, -14.0), (161.0, hc + 0.5, zc + 1.6), c("cascade"), name="Ruisseau", **ND)
        b.box((151.4, -1.6, zc + 0.2), (160.6, hc + 0.3, zc + 1.6), c("cascade"), transparency=0.1, name="Cascade", **ND)
        b.box((153.0, -1.6, zc + 1.6), (158.6, hc * 0.7, zc + 2.4), c("ecume"), transparency=0.15, name="Cascade", **NDS)
        b.box((155.0, -1.6, zc + 2.4), (157.0, hc * 0.45, zc + 2.8), c("blanc"), transparency=0.2, name="Cascade", **NDS)
        b.box((146.0, -1.75, zc), (166.0, -1.0, zc + 8.0), c("ecume"), name="Bassin", **NDS)
        for (dx, dz, r) in ((-3.0, 4.0, 1.6), (2.5, 5.0, 1.3), (0.0, 7.0, 1.0)):
            b.ball((156.0 + dx, -0.6, zc + dz), r, c("ecume"), transparency=0.25, name="Embruns", **NDS)
        for (px, pz, h, cap) in ((144.0, -12.0, 12, 70), (168.0, -16.0, 14, 120), (180.0, -10.0, 11, 40)):
            y = dessus(px, pz)
            if y is not None:
                _palmier(b, px, y, pz, h, cap, rng)
        for (px, pz, h, cap) in ((-108.0, -16.0, 12, -60), (-196.0, -14.0, 13, -120)):
            y = dessus(px, pz)
            if y is not None:
                _palmier(b, px, y, pz, h, cap, rng)

    return {"emprise": (largeur, profondeur), "hauteur": hauteur}
