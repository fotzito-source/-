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
                             filet_peche, guirlande_fanions, lanterne_quai, mouette, tonneaux)

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
    """Lanterne de navire suspendue (5 pièces) : anneau, chapeau, verre éclairé, montants, fond. `y` = bas."""
    cadre = cadre or c("fer")
    b.box((x - 0.8 * s, y, z - 0.8 * s), (x + 0.8 * s, y + 0.3 * s, z + 0.8 * s), cadre, name="Fond", **ND)
    b.box((x - 0.62 * s, y + 0.3 * s, z - 0.62 * s), (x + 0.62 * s, y + 1.9 * s, z + 0.62 * s), c("lanterne"),
          material="Neon", name="Verre", **NDS)
    b.box((x - 0.72 * s, y + 0.3 * s, z - 0.2 * s), (x + 0.72 * s, y + 1.9 * s, z + 0.2 * s), cadre, name="Montants", **ND)
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
            for z in (-2.35, 2.35):
                b.cyl((xb, y + 0.4, z), 2.25, 1.2, garniture, name="Ligature", **ND)
        # hune (plateforme ronde) au sommet du grand mât
        b.cyl((xa, top_a + 0.4, 0), 3.6, 0.8, c("bois_fonce"), studs="top", name="Hune")
        b.cyl((xa, top_a + 1.25, 0), 3.3, 0.9, c("bois"), name="Garde", **ND)
        # contrefiches de pied (dans le plan y-z), jamais vers le couloir
        for sz in (-1, 1):
            _poutre(b, (xa, 3.4, sz * 5.6), (xa, 16.0, sz * 2.2), 1.3, c("bois_fonce"), name="Contrefiche")
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
            larg = 2.3
            xc = x + larg / 2
            if not any(abs(xc - f) < 2.2 for f in forts):
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
            if i % 2 == 0:
                # potence courte et lanterne côté couloir (-Z)
                b.box((xf - 0.25, 10.0, -2.9), (xf + 0.25, 10.5, -1.0), c("bois_fonce"), name="Potence", **ND)
                _lanterne_navire(b, xf, 7.3, -2.4, 0.8)
            else:
                with b.at((xf, 3.0, -1.35)):
                    bouee(b, variant=1, rayon=1.1)
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
            _lanterne_navire(b, xv, 10.4, -2.4, 0.7)


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
            for xx in (36.0, 48.0):
                b.box((s * xx - 0.4, yp0 - 0.12, -2.55), (s * xx + 0.4, yp1 + 0.12, 2.55), c("fer"), name="Ferrure", **ND)
        # voile ferlée sur la vergue (en deux moitiés, la barre au milieu), rabans de cordage
        for s in (-1, 1):
            xa, xb = sorted((s * 5.0, s * 39.0))
            b.cyl(((xa + xb) / 2, yp1 + 1.2, 0), 1.35, xb - xa, c("voile"), axis="x", name="VoileFerlee", **ND)
            b.cyl(((xa + xb) / 2, yp1 + 1.25, -0.25), 1.2, xb - xa - 3, c("voile_ombre"), axis="x", name="Pli", **NDS)
            for k in range(4):
                xx = s * (9.0 + k * 9.0)
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
                for (dx, dz) in ((5.5, -7.5), (-2.0, 7.6)):
                    x = s * (46.6 + dx)
                    b.cyl((x, 0.35, dz), 1.5, 0.7, c("corde"), studs="top", name="Rouleau", **ND)
                    b.cyl((x, 0.85, dz), 1.0, 0.3, c("corde_fonce"), name="Rouleau", **ND)

    # accessoires au pied (tous à |x| ≥ 40)
    with b.group("Abords"):
        with b.at((-57.5, 0, -7.0), yaw=-20):
            tonneaux(b, variant=1)
        with b.at((44.5, 0, -8.6), yaw=10):
            tonneaux(b, variant=0)
        with b.at((-50.5, 0, 9.4), yaw=170):
            caisses(b, variant=0)
        with b.at((58.0, 0, 7.6), yaw=195):
            caisses(b, variant=2)
        with b.at((56.5, 0, -6.5), yaw=0):
            ancre(b, variant=2, taille=0.9)
        with b.at((-62.0, 0, 6.0), yaw=180):
            filet_peche(b, variant=0, largeur=6.0)
        # guirlandes de fanions du haut des piles vers les poteaux de la palissade
        for s in (-1, 1):
            guirlande_fanions(b, (s * 47.0, 34.0, -1.6), (s * 79.1, 10.6, -1.3), n=8, creux=1.8, variant=0 if s < 0 else 2)

    with b.group("Palissades"):
        for s in (-1, 1):
            _palissade(b, s, 52.6, mur, variant, rng)

    return {"emprise": (2 * mur, 12), "hauteur": round(H + 9 + 1.7 + 10.5, 1)}


# ---------------------------------------------------------------------------
# 2. Rocher du crâne (repère final, le couloir passe par la bouche)
# ---------------------------------------------------------------------------


def rocher_crane(b, variant: int = 0, passage: float = 64, largeur: float = 440, profondeur: float = 34,
                 hauteur: float = 100) -> dict:
    raise NotImplementedError
