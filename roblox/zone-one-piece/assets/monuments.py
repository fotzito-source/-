"""Monuments de la zone mer de l'Est : arche du port (entrée) et rocher du crâne (repère final).

- `porte_entree` : arche de port en mâts de navire liés de cordages, nids-de-pie, vergue à voile ferlée, panneau de
  jeu bleu marine « ZONE RARE » / « VITESSE CONSEILLÉE : 200 » lisible des deux côtés, bouées, filet, lanternes,
  tonneaux, ancre ; palissade de pieux jusqu'aux collines.
- `rocher_crane` : rocher marin ivoire en forme de tête de mort générique ; le couloir traverse la bouche ;
  falaises sur toute la largeur, épave échouée à gauche, cascade en gradins à droite, pavillon au sommet.

Couloir élargi : x ∈ [-45, 45] (90 studs), trottoirs jusqu'à |x| = 55. Les deux monuments sont paramétrés par
la largeur libre (`ouverture` = 110 pour l'arche : piles à |x| ≥ 55 ; `passage` = 96 pour la bouche : parois à
|x| ≥ 48). Tout ce qui enjambe le couloir reste au-dessus de y = 35 (panneau) ou y = 36 (dents du crâne).
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


def _pilier_mats(b, s: int, xi: float, variant: int, top_a: float, yp1: float, rng) -> dict:
    """Une pile de l'arche : trois mâts liés sur un socle de pierre, contrefiches, bagues de cordage.

    `xi` = |x| de la face intérieure du socle (bord de l'ouverture). Renvoie des points d'accroche utiles."""
    socle = c("rose") if variant % 2 else c("pierre_fonce")
    socle2 = c("rose_fonce") if variant % 2 else c("pierre")
    garniture = c("bleu_marine") if variant % 2 else c("corde")
    xa = s * (xi + 4.6)           # grand mât (face intérieure à |x| = xi + 1,8)
    xb = s * (xi + 8.8)           # mâts secondaires, côté extérieur
    X = lambda d: s * (xi + d)    # |x| = xi + d, du bon côté
    with b.group("Pile"):
        # socle en deux assises studdées
        x0, x1 = sorted((X(0.6), X(12.6)))
        b.box((x0, 0, -6), (x1, 2.4, 6), socle, studs="top", name="Socle")
        x0, x1 = sorted((X(1.4), X(11.8)))
        b.box((x0, 2.4, -5.2), (x1, 3.6, 5.2), socle2, studs="top", name="Assise")
        # bordé de planches autour du pied (caisson de bois)
        x0, x1 = sorted((X(1.0), X(12.2)))
        b.box((x0, 3.6, -4.4), (x1, 7.4, 4.4), vary("bois_quai", rng, 0.04), studs="top", name="Caisson")
        b.box((x0 - 0.15, 5.2, -4.55), (x1 + 0.15, 5.8, 4.55), c("bois_fonce"), name="Ceinture", **ND)
        # mâts : grand mât au centre, deux plus fins côté extérieur (ils traversent la vergue)
        b.cyl((xa, 3.6 + (top_a - 3.6) / 2, 0), 2.8, top_a - 3.6, vary("bois", rng, 0.04), name="GrandMat")
        for z, top in ((-2.35, yp1 - 2.0), (2.35, yp1 - 4.4)):
            b.cyl((xb, 3.6 + (top - 3.6) / 2, z), 2.0, top - 3.6, vary("bois_clair", rng, 0.05), name="Mat")
        # bagues de cordage (ligatures)
        for y in (13.0, 27.0, 41.0):
            b.cyl((xa, y, 0), 3.05, 1.6, garniture, name="Ligature", **ND)
        b.cyl((xa, yp1 + 2.2, 0), 3.05, 1.2, garniture, name="Ligature", **ND)
        for y, z in ((13.4, -2.35), (27.4, -2.35), (20.4, 2.35), (34.4, 2.35)):
            b.cyl((xb, y, z), 2.25, 1.2, garniture, name="Ligature", **ND)
        # nid-de-pie (tonneau de vigie cerclé) au sommet du grand mât
        b.cyl((xa, top_a + 0.4, 0), 3.7, 0.8, c("bois_fonce"), studs="top", name="Hune")
        b.cyl((xa, top_a + 2.0, 0), 3.3, 2.4, vary("bois_clair", rng, 0.04), name="NidDePie", **ND)
        b.cyl((xa, top_a + 3.35, 0), 3.45, 0.5, garniture, name="Cercle", **ND)
        # contrefiches de pied vers l'extérieur, en V de part et d'autre du caisson (jamais vers le couloir) :
        # courtes (sommet à 12) et posées sur un sabot de pierre
        for sz in (-1, 1):
            x0, x1 = sorted((X(15.0), X(18.0)))
            b.box((x0, 0, sz * 3.3 - 1.1), (x1, 1.3, sz * 3.3 + 1.1), vary("pierre_fonce", rng, 0.04), studs="top",
                  name="Sabot")
            _poutre(b, (X(16.2), 1.0, sz * 3.3), (X(11.0), 12.0, sz * 2.4), 1.3, c("bois_fonce"), name="Contrefiche")
    return {"x_mat": xa, "x_sec": xb, "x_ext": X(12.6), "sommet": top_a + 3.6}


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
    # cordage le long du bas du cadre (des deux côtés) et clous dorés aux coins
    for z in (-0.82, 0.82):
        b.box((x0 - 0.3, y0 - 0.55, z - 0.12), (x1 + 0.3, y0 - 0.25, z + 0.12), c("corde"), name="Corde", **NDS)
        for xx in (x0 - 0.375, x1 + 0.375):
            b.box((xx - 0.3, y1 + 0.1, z - 0.1), (xx + 0.3, y1 + 0.65, z + 0.1), c("laiton"), name="Clou", **NDS)


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


def _filet_drape(b, s: int, xi: float) -> None:
    """Filet de pêche drapé du grand mât (à 14 de haut) vers une perche courte, côté apparition (+Z) : une vraie maille
    de cordelettes (fils horizontaux qui suivent la ralingue, fils verticaux tous les 1,2 stud), flotteurs."""
    xm, xp = s * (xi + 7.0), s * (xi + 20.0)
    with b.group("Filet"):
        b.cyl((xp, 3.5, 6.5), 0.3, 7.0, c("bois_flotte"), name="Perche")
        b.box((xp - 0.6, 0, 5.9), (xp + 0.6, 0.5, 7.1), c("pierre_fonce"), name="Pierre", **ND)
        # ralingue (bord haut) en deux pans : du mât au creux, du creux à la perche
        haut = [np.array(v, float) for v in ((xm, 14.0, 4.6), (s * (xi + 13.5), 9.0, 5.6), (xp, 6.8, 6.5))]
        longueurs = [float(np.linalg.norm(haut[i + 1] - haut[i])) for i in range(2)]
        L = sum(longueurs)

        def point(u: float) -> np.ndarray:
            """Point de la ralingue à l'abscisse curviligne u (0 : mât, L : perche)."""
            if u <= longueurs[0]:
                return haut[0] + (haut[1] - haut[0]) * (u / longueurs[0])
            return haut[1] + (haut[2] - haut[1]) * ((u - longueurs[0]) / longueurs[1])

        def chute(u: float) -> float:
            """Hauteur de la nappe sous la ralingue : 6 au milieu, moins près du mât et de la perche."""
            t = u / L
            return 1.2 + 4.8 * math.sin(math.pi * min(1.0, max(0.0, t)) ) ** 0.6

        maille = c("corde_fonce")
        # fils verticaux tous les 1,2 stud
        nu = int(L // 1.2)
        for k in range(1, nu + 1):
            u = k * L / (nu + 1)
            p = point(u)
            _segment(b, p, p - np.array([0.0, chute(u), 0.0]), 0.06, maille, name="Maille", shadow=False)
        # fils horizontaux (parallèles à la ralingue), un tous les 1,2 stud de chute
        for j in range(1, 5):
            dy = 1.2 * j
            us = [u for u in np.linspace(0.0, L, 6) if chute(u) >= dy - 0.05]
            if len(us) < 2:
                continue
            pts = [point(u) - np.array([0.0, dy, 0.0]) for u in us]
            for a, bb in zip(pts, pts[1:]):
                _segment(b, a, bb, 0.06, maille, name="Maille", shadow=False)
        _segment(b, (xm, 14.2, 4.6), haut[1] + np.array([0, 0.2, 0]), 0.1, c("corde_fonce"), name="Ralingue")
        _segment(b, haut[1] + np.array([0, 0.2, 0]), (xp, 7.0, 6.5), 0.1, c("corde_fonce"), name="Ralingue")
        for k, t in enumerate((0.3, 0.55, 0.8)):
            p = point(t * L) + np.array([0.0, 0.2, 0.0])
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


def _plan_palissade(x_debut: float, x_fin: float) -> tuple:
    """Positions (|x|) des poteaux forts et de la tour de guet d'une palissade."""
    vigie = x_debut + (x_fin - x_debut) * 0.55
    forts = [x_debut + 7 + k * 19.5 for k in range(8) if x_debut + 7 + k * 19.5 < x_fin - 3]
    forts = [f for f in forts if abs(f - vigie) > 7.5]
    return forts, vigie


def _palissade(b, s: int, x_debut: float, x_fin: float, variant: int, rng) -> None:
    """Palissade de pieux pointus le long de z ≈ 0, de |x| = x_debut à x_fin, poteaux forts tous les ~19 studs."""
    garniture = c("bleu_marine") if variant % 2 else c("corde")
    cols = ("bois", "bois_clair", "bois_flotte", "bois_quai")
    forts, vigie = _plan_palissade(x_debut, x_fin)
    with b.group("Palissade"):
        # pieux
        x = x_debut + 0.2
        k = 0
        larg = max(3.0, (x_fin - x_debut) / 21.0)      # nombre de pieux à peu près constant (budget)
        while x < x_fin - 1.0:
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
            fz = -1 if i % 2 == 0 else 1
            if i % 3 == 2:
                # bouée accrochée au poteau
                with b.at((xf, 3.2, fz * 1.3), yaw=0 if fz < 0 else 180):
                    bouee(b, variant=1, rayon=1.2)
            else:
                # potence courte et lanterne, alternée côté zone (-Z) et côté apparition (+Z)
                b.box((xf - 0.25, 10.0, fz * 1.0), (xf + 0.25, 10.5, fz * 2.9), c("bois_fonce"), name="Potence", **ND)
                _lanterne_navire(b, xf, 10.0 - 2.8 * 0.8, fz * 2.4, 0.8)
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


def porte_entree(b, variant: int = 0, ouverture: float = 110, hauteur: float = 50, mur: float = 130) -> dict:
    """Arche du port : deux piles en mâts liés, vergue à voile ferlée, panneau de jeu suspendu, palissades.

    Origine au centre de l'ouverture au sol, arche dans le plan z = 0 (profondeur z ∈ [-6, 6] hors accessoires).
    `ouverture` = écart entre les faces intérieures des piles (couloir + trottoirs : 110 pour |x| ≤ 55).
    Les joueurs arrivent par +Z ; le panneau se lit des deux côtés. Tout ce qui enjambe l'ouverture reste à y ≥ 35."""
    rng = b.rng
    xi = ouverture / 2                   # face intérieure des socles
    cadre = c("rose") if variant % 2 else c("bois_fonce")
    # Étagement du panneau (de bas en haut) : bas du cadre à 35 au-dessus du couloir.
    yv0 = 35.75
    yv1 = yv0 + 7.5                      # « VITESSE CONSEILLÉE : 200 »
    yz0 = yv1 + 2.35
    yz1 = yz0 + 9.0                      # « ZONE RARE »
    yp0 = yz1 + 0.75                     # dessous de la vergue
    yp1 = yp0 + 3.2                      # dessus de la vergue
    top_a = max(hauteur + 9.0, yp1 + 5.5)    # sommet des grands mâts
    wz = min(64.0, 0.58 * ouverture)     # largeur de « ZONE RARE »
    wv = max(56.0, min(96.0, ouverture - 14.0))   # largeur de « VITESSE CONSEILLÉE : 200 »
    xe = xi + 17.5                       # bout de la vergue
    with b.group("Arche"):
        piles = [_pilier_mats(b, s, xi, variant, top_a, yp1, rng) for s in (-1, 1)]
        # vergue maîtresse (poutre carrée) traversant les mâts
        b.box((-xe, yp0, -2.4), (xe, yp1, 2.4), c("bois_fonce"), studs="top", name="Poutre")
        for s in (-1, 1):
            xa, xb = sorted((s * xe, s * (xe + 1.5)))
            b.box((xa, yp0 + 0.4, -2.0), (xb, yp1 - 0.4, 2.0), c("bois"), studs="top", name="Embout")
            # aisseliers sous la poutre (au-dessus de y = 44, hors couloir)
            _poutre(b, (s * (xi + 2.0), yp0 - 11.0, 0), (s * (xi - 6.0), yp0 + 0.3, 0), 1.4, c("bois"), name="Aisselier")
            # bandes de fer décoratives
            b.box((s * (xi - 4.0) - 0.4, yp0 - 0.12, -2.55), (s * (xi - 4.0) + 0.4, yp1 + 0.12, 2.55), c("fer"),
                  name="Ferrure", **ND)
        # voile ferlée sur la vergue (en deux moitiés, la barre au milieu), rabans de cordage
        for s in (-1, 1):
            xa, xb = sorted((s * 5.0, s * (xi - 1.0)))
            b.cyl(((xa + xb) / 2, yp1 + 1.6, 0), 1.75, xb - xa, c("voile"), axis="x", name="VoileFerlee", **ND)
            b.cyl(((xa + xb) / 2, yp1 + 1.7, -0.35), 1.55, xb - xa - 3, c("voile_ombre"), axis="x", name="Pli", **NDS)
            nr = max(2, int((xi - 8.0) // 11.0))
            for k in range(nr):
                xx = s * (11.0 + k * (xi - 14.0) / max(nr - 1, 1))
                b.cyl((xx, yp1 + 1.6, 0), 1.9, 0.6, c("corde"), axis="x", name="Raban", **ND)
        # barre de navire au centre de la poutre
        with b.at((0, yp1, 0)):
            barre_navire(b, variant=2 if variant % 2 == 0 else 1, taille=2.2)

        # panneau de jeu
        with b.group("Panneau"):
            _planche_texte(b, -wz / 2, wz / 2, yz0, yz1, "ZONE RARE", (0xB4, 0x8C, 0xFF), cadre, rng, "ZoneRare")
            _planche_texte(b, -wv / 2, wv / 2, yv0, yv1, "VITESSE CONSEILLÉE : 200", (0xFF, 0xE3, 0x7A), cadre, rng,
                           "Vitesse")
            # ferrures d'accroche sous la poutre (ZONE RARE) et chaînes entre les deux planches
            for xx in (-(wz / 2 - 7.0), wz / 2 - 7.0):
                for z in (-0.95, 0.95):
                    b.box((xx - 0.7, yz1 - 1.6, z - 0.12), (xx + 0.7, yp0 + 0.5, z + 0.12), c("fer"), name="Ferrure", **ND)
            for xx in (-(wz / 2 - 4.0), wz / 2 - 4.0):
                _chaine(b, xx, yz0 - 0.75, yv1 + 0.75)
            # lanternes suspendues sous la poutre, entre le panneau et les piles
            for s in (-1, 1):
                xl = s * (wz / 2 + xi) / 2
                _chaine(b, xl, yp0, yp0 - 1.6)
                _lanterne_navire(b, xl, yp0 - 4.4, 0, 1.0)

        # étais : du haut des grands mâts au bout de la vergue et au premier poteau fort de la palissade
        forts0, _ = _plan_palissade(xi + 12.6, mur)
        for s, p in zip((-1, 1), piles):
            _segment(b, (p["x_mat"], top_a - 1.0, 0), (s * (xe + 1.2), yp1 - 0.2, 0), 0.16, c("corde_fonce"), name="Etai")
            if forts0:
                _segment(b, (p["x_mat"], top_a - 2.0, 0), (s * forts0[0], 11.0, 0), 0.16, c("corde_fonce"), name="Etai")

        # pavillons génériques au sommet des grands mâts (ils flottent vers l'extérieur)
        for s, p in zip((-1, 1), piles):
            with b.at((p["x_mat"], p["sommet"], 0), yaw=0 if s > 0 else 180):
                drapeau_pirate(b, variant=0, hauteur=10, largeur=7, mat=True)

        # habillage des piles : bouées, rames croisées, lanternes, cordages enroulés
        with b.group("Habillage"):
            for s, p in zip((-1, 1), piles):
                xm = p["x_mat"]
                for face in (-1, 1):
                    with b.at((xm, 17.0, face * 2.95), yaw=0 if face < 0 else 180):
                        bouee(b, variant=1, rayon=1.5)
                    # lanterne de pile sur console
                    b.box((xm - 0.3, 25.4, face * 2.6), (xm + 0.3, 25.9, face * 4.6), c("fer"), name="Console", **ND)
                    _lanterne_navire(b, xm, 25.4 - 2.8 * 0.9, face * 4.3, 0.9)
                # rames croisées sur la face des mâts secondaires (avant à gauche, arrière à droite)
                fz = -4.55 if s < 0 else 4.55
                xb = p["x_sec"]
                for ang in (25, -25):
                    R = rot_z(ang)
                    b.part("block", (0.5, 11.0, 0.3), (xb, 22.0, fz), R, c("bois_clair"), name="Rame", **ND)
                    pale = R @ np.array([0, -5.2, 0]) + np.array([xb, 22.0, fz])
                    b.part("block", (1.3, 3.0, 0.32), tuple(pale), R, c("rouge") if ang > 0 else c("blanc"), name="Pale", **ND)
                # rouleau de cordage au pied
                x = s * (xi + 12.1)
                b.cyl((x, 0.35, -7.5), 1.5, 0.7, c("corde"), studs="top", name="Rouleau", **ND)
                b.cyl((x, 0.85, -7.5), 1.0, 0.3, c("corde_fonce"), name="Rouleau", **ND)

    # accessoires au pied (tous à |x| ≥ xi)
    x_pal = xi + 12.6
    forts, _ = _plan_palissade(x_pal, mur)
    with b.group("Abords"):
        with b.at((-(xi + 17.5), 0, -7.0), yaw=-20):
            tonneaux(b, variant=1)
        with b.at((xi + 4.5, 0, -8.8), yaw=80):
            tonneaux(b, variant=2)
        with b.at((-(xi + 10.5), 0, 9.4), yaw=170):
            caisses(b, variant=0)
        with b.at((xi + 18.0, 0, 7.6), yaw=195):
            caisses(b, variant=1)
        with b.at((xi + 21.5, 0, -6.8), yaw=0):
            ancre(b, variant=2, taille=0.9)
        _filet_drape(b, -1, xi)
        # guirlandes de fanions du haut des piles vers un poteau fort de la palissade
        if forts:
            xg = forts[min(1, len(forts) - 1)]
            for s in (-1, 1):
                guirlande_fanions(b, (s * (xi + 7.0), 34.0, -1.6), (s * xg, 10.6, -1.3), n=5, creux=1.8,
                                  variant=0 if s < 0 else 2)

    with b.group("Palissades"):
        for s in (-1, 1):
            _palissade(b, s, x_pal, mur, variant, rng)

    return {"emprise": (2 * mur, 12), "hauteur": round(top_a + 3.6 + 10.5, 1)}


# ---------------------------------------------------------------------------
# 2. Rocher du crâne (repère final, le couloir passe par la bouche)
# ---------------------------------------------------------------------------


def _palmier(b, x, y, z, h: float, cap: float, rng) -> None:
    """Palmier courbé (9 pièces) : tronc en deux tronçons, couronne, cinq palmes, une noix. La couronne grandit avec
    le tronc au-delà de 14 studs (palmiers du sommet du crâne, visibles de loin)."""
    e = max(1.0, h / 14.0)
    a = math.radians(cap)
    d = np.array([math.sin(a), 0.0, -math.cos(a)])         # direction de l'inclinaison
    base = np.array([x, y, z], float)
    pts = [base]
    for k in range(1, 3):
        t = k / 2
        pts.append(base + np.array([0, h * t, 0]) + d * (h * 0.3 * t * t))
    for k in range(2):
        _segment(b, pts[k] - np.array([0, 0.3, 0]), pts[k + 1], (0.6 - 0.15 * k) * e, vary("tronc", rng, 0.06),
                 name="Tronc", collide=(k == 0), shadow=True)
    top = pts[-1]
    b.ball(tuple(top), 1.0 * e, c("palme_fonce"), name="Couronne", **ND)
    for k in range(5):
        ang = cap + k * 72 + float(rng.uniform(-12, 12))
        R = rot_y(-ang) @ rot_x(-22 if k % 2 else -30)
        centre = top + R @ np.array([0, 0, -3.0 * e]) + np.array([0, -0.4 * e, 0])
        b.part("block", (1.6 * e, 0.3 * e, 6.2 * e), tuple(centre), R, c("palme") if k % 2 else c("palme_claire"),
               name="Palme", **ND)
    b.ball((top[0] + 0.5 * e, top[1] - 0.9 * e, top[2] + 0.4 * e), 0.5 * e, c("coco"), name="Coco", **NDS)


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
                bx((xr - 0.4, 4.6, sz * 3.6 - 0.4), (xr + 0.4, 9.8 - abs(xr + 2.0) * 0.4, sz * 3.6 + 0.4), fonce,
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
            b.box((x + dx - w / 2, -2.7, z + dz - w / 2), (x + dx + w / 2, h - 1, z + dz + w / 2), vary("roche", rng, 0.06),
                  studs="top", name="Rocher")
        with b.at((x + 28, -0.6, z + 6), yaw=30):
            tonneaux(b, variant=2)
        with b.at((x - 22, -0.6, z + 7.5), yaw=-15):
            coffre_tresor(b, variant=2)


def _decor_variant(nom: str, variant: int):
    """Couleur du rocher selon la variante (0 : ivoire ; 1 : pierre grise chaude)."""
    nom = {"os_ombre_orbite": "os_ombre"}.get(nom, nom)
    if variant % 2 == 0:
        return c(nom)
    table = {"os": "roche_claire", "os_clair": "pierre_claire", "os_fonce": "roche", "os_ombre": "roche_fonce"}
    return c(table.get(nom, nom))


def rocher_crane(b, variant: int = 0, passage: float = 96, largeur: float = 440, profondeur: float = 34,
                 hauteur: float = 130, x_ecume: float = 0.0) -> dict:
    """Rocher marin en tête de mort générique : le couloir passe par la bouche (plafond ≥ 36).

    Origine : centre de l'entrée du passage, au sol, sur la façade. Exception à la règle -Z : le rocher regarde +Z
    (vers les joueurs qui arrivent) et s'étend jusqu'à z = -profondeur. Façade en « pixels » de 2 studs (blocs
    fusionnés), reliefs en gradins studdés ; bouche, dents, couloir intérieur, falaises, épave, cascade.
    `passage` = largeur libre de la bouche (|x| < passage / 2 libre du sol à y ≥ 36) ; le crâne s'élargit avec lui
    tant que `hauteur` le permet (largeur du crâne ≤ 1,6 × hauteur : 130 de haut pour un passage de 96).
    `x_ecume` : |x| où commence l'écume au pied de la façade (bord du ponton de la place, pour ne pas passer dessous).
    Le rocher ne dépasse pas z = -profondeur (le cadre de sortie est posé dans l'épaisseur) : la zone suivante commence
    exactement là."""
    rng = b.rng
    D = float(profondeur)
    L2 = largeur / 2
    P2 = passage / 2                      # demi-largeur du passage libre
    k = hauteur / 100.0
    kf = math.sqrt(k)                     # échelle des falaises
    CELL = 2.0
    nx = int(round(largeur / CELL))
    col_f = lambda n: _decor_variant(n, variant)

    X_DEV = max(60.0, P2 + 28.0)          # |x| ≤ X_DEV : rien devant z = 0 sous y = 45 (ponton et mâts de la place)
    XM = CELL * math.ceil((P2 + 12.0) / CELL)    # bord extérieur des parois de la bouche (sur la grille)
    wm = XM - P2                          # épaisseur des parois de la bouche (≥ 12)
    XJ = P2 + 28.0                        # demi-largeur de la mâchoire au sol
    YJ = 48.0 if P2 >= 40 else 44.0       # dessous de la mâchoire supérieure (dents de 8 à 12, pointes à y ≥ 36)
    A_CR = min(78.0 * max(1.0, (P2 + 16.0) / 48.0), 0.8 * hauteur)    # demi-largeur du crâne
    sx = A_CR / 78.0                      # échelle horizontale du visage (1 pour un passage de 64 et 100 de haut)
    span = hauteur - YJ                   # hauteur du visage au-dessus de la bouche

    def Y(t: float) -> float:
        """Hauteur à la fraction t du visage (0 : dessous de la mâchoire, 1 : sommet du crâne)."""
        return YJ + t * span

    EX, EY, EA, EB = 29.0 * sx, Y(0.40), 14.0 * sx, 0.19 * span    # orbites
    YC = EY - 0.5 * EB                    # le crâne est le plus large un peu sous le milieu des orbites
    B_CR = hauteur - YC
    YN0, YN1 = YJ + 2.0, Y(0.20)          # nez (cœur renversé), au-dessus d'une rangée d'os
    YP0, YP1 = Y(0.15), Y(0.24)           # pommettes
    # rangées de la grille : 2 studs jusqu'au-dessus des arcades, puis 4 studs pour la calotte (moins de pièces)
    y_fin = 2.0 * math.ceil((EY + EB + 6.0) / 2.0)
    ys = [-3.0] + [float(v) for v in np.arange(0.0, y_fin + 0.1, 2.0)]
    while ys[-1] < hauteur + 2:
        ys.append(ys[-1] + 4.0)
    ny = len(ys) - 1

    # profil des falaises : basses et en retrait près du crâne (sa silhouette se détache sur le ciel),
    # crête vers le premier tiers, puis gradins qui descendent vers le bord de la zone
    paliers = [(0.10, 34), (0.18, 44), (0.28, 54), (0.39, 60), (0.51, 52), (0.63, 44), (0.76, 38), (0.89, 32), (9.0, 26)]
    paliers = [(A_CR + u * (L2 - A_CR), h) for u, h in paliers]
    jit = {}

    def h_falaise(ax: float, s: int) -> float:
        key = (s, int(ax // 16))
        if key not in jit:
            jit[key] = float(rng.choice([0, 0, 2, -2, 4, -4]))
        for lim, h in paliers:
            if ax < lim:
                return (h + jit[key]) * kf
        return 26 * kf

    def z_falaise(ax, y, hc, s) -> float:
        t = y / max(hc, 1)
        j = -2.0 * (int(ax // 16 + (s > 0)) % 3)
        recul = -10.0 if ax < A_CR + 22 else -4.0 if ax < A_CR + 34 else 0.0
        if y < 0 or t < 0.18:
            return 2.0 if ax > X_DEV else 0.0
        if t < 0.5:
            return min(0.0 + j, 0.0) + recul * 0.5
        if t < 0.8:
            return -4.0 + j + recul
        return -8.0 + j + recul

    fissures = [((-12, 98), (-6, 90)), ((-6, 90), (-10, 82)), ((46, 94), (52, 86)), ((52, 86), (48, 80)),
                ((-60, 88), (-68, 80)), ((-68, 80), (-64, 74)), ((64, 56), (68, 50))]
    fissures = [((xa * sx, Y((ya - 42) / 58)), (xb * sx, Y((yb - 42) / 58))) for (xa, ya), (xb, yb) in fissures]

    def dist_seg(px, py, a, bb) -> float:
        ax_, ay_ = a
        bx_, by_ = bb
        vx, vy = bx_ - ax_, by_ - ay_
        t = max(0.0, min(1.0, ((px - ax_) * vx + (py - ay_) * vy) / (vx * vx + vy * vy)))
        return math.hypot(px - ax_ - t * vx, py - ay_ - t * vy)

    def demi_largeur(y) -> float:
        """Silhouette du crâne : calotte pleine (super-ellipse), tempes, pommettes, mâchoire plus étroite."""
        if y >= YC:
            v = 1.0 - ((y - YC) / B_CR) ** 2.2
            return A_CR * v ** (1 / 2.2) if v > 0 else -1.0
        if y >= YP1:
            return A_CR - (YC - y) * 0.25
        w1 = A_CR - (YC - YP1) * 0.25                 # largeur aux pommettes
        y_bas = YJ - 20.0                             # coin de la mâchoire
        if y >= y_bas:                                # joue arrondie (quart d'ellipse) jusqu'à la mâchoire
            t = (YP1 - y) / (YP1 - y_bas)
            return XJ + (w1 - XJ) * math.sqrt(max(0.0, 1.0 - t * t))
        return XJ - max(0.0, 8.0 - y) * 0.6

    def cellule(x, y):
        ax = abs(x)
        s = 1 if x > 0 else -1
        if ax < XM and y < YJ:
            return None                                   # bouche et parois : posées à la main
        en_faille = s > 0 and abs(ax - X_CASC) <= 6
        hc = HC_CASC if en_faille else h_falaise(ax, s)
        if ax > demi_largeur(y):
            if ax >= P2 + 20 and y < hc:
                # falaise : herbe au sommet, roches claires en haut, foncées en bas ; faille de la cascade à droite
                zf = z_falaise(ax, y, hc, s)
                if en_faille:
                    return ("gres_fonce", z_falaise(X_CASC, y, hc, 1) - 4.0)
                if y + 4 >= hc:
                    return ("herbe", zf)
                if y + 6 >= hc:
                    return ("terre", zf)
                if y < 3:
                    return ("gres_mouille", zf)             # roche mouillée à la ligne d'eau
                t = y / hc
                return ("gres_clair" if t > 0.62 else "gres" if t > 0.22 else "gres_fonce", zf)
            return None
        nom, zf = crane(x, y, ax)
        if ax <= X_DEV and y < 45:
            zf = min(zf, 0.0)
        return (nom, zf)

    def crane(x, y, ax):
        # calotte : gradins qui reculent vers les bords (arrondi), teinte plus sombre en retrait
        r2 = (x / A_CR) ** 2 + (max(y - YC, 0.0) / B_CR) ** 2
        zd = -5.0 * round(20.0 * r2 ** 1.7 / 5.0)
        base = ("os_clair" if zd >= -5 and y >= Y(0.62) else "os" if zd >= -10 else "os_fonce" if zd >= -15 else "os_ombre")
        # orbites
        e = ((ax - EX) / EA) ** 2 + ((y - EY) / EB) ** 2
        if e <= 1.0:
            return ("grotte", -9.0)
        if e <= 1.45:
            return ("os_ombre_orbite", min(zd, 0.0) - 3.0)
        # arcades sourcilières en surplomb (au-dessus de y = 45 : avancée permise)
        if EY + EB + 1 <= y < EY + EB + 5 and abs(ax - EX) <= 16 * sx:
            return ("os_clair", 3.0)
        # fissures
        for a, bb in fissures:
            if dist_seg(x, y, a, bb) < 1.1:
                return ("os_fissure", zd - 1.0)
        # nez (cœur renversé : pointe en haut, cloison au milieu en bas)
        if YN0 <= y < YN1:
            hw = 7.5 * sx * (YN1 - y) / (YN1 - YN0)
            if ax < hw and not (y < YN0 + 3 and ax < 1.6):
                return ("grotte", -7.0)
            if ax < hw + 2.2:
                return ("os_fonce", -2.0)
        if YJ <= y < YJ + 5 and ax < 44 * sx:
            return ("os", -1.0)                           # maxillaire au-dessus des dents
        if YJ <= y < YP1 and 46 * sx <= ax:               # pommettes saillantes (en relief sur les gradins)
            zc = min(3.0, zd + 5.0) if 62 * sx <= ax else min(0.0, zd + 2.0)
            return ("os_clair" if y >= YP0 and zd >= -10 else "os" if zd >= -10 else "os_fonce", zc)
        if YJ <= y < YP1 and 42 * sx <= ax < 46 * sx:
            return ("os_fonce", min(-3.0, zd - 1.0))      # creux sous la pommette
        if y < YJ:                                        # mâchoire, de part et d'autre de la bouche
            if y >= 36:
                return ("os" if zd >= -5 else "os_fonce", min(-1.0, zd))
            if y < 6:
                return ("os_ombre", min(-3.0, zd))
            return ("os_fonce" if zd >= -10 else "os_ombre", min(-2.0, zd))
        return (base, zd)

    X_CASC = max(156.0, A_CR + 52.0)      # faille de la cascade (flanc droit)
    HC_CASC = h_falaise(X_CASC, 1)        # hauteur de la falaise à la cascade

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
            # les creux sombres (orbites, nez) s'arrêtent avant le dos : le dos du rocher reste couleur d'os
            z_dos = -D + 2.0 if nom in ("grotte", "os_ombre_orbite") else -D
            for (i, j, w, h) in mask_rects(m):
                x0, x1 = -L2 + i * CELL, -L2 + (i + w) * CELL
                y0, y1 = ys[j], ys[j + h]
                col = vary(col_f(nom), rng, 0.035) if nom not in ("grotte",) else col_f(nom)
                mat = "Grass" if nom == "herbe" else "SmoothPlastic"
                b.box((x0, y0, z_dos), (x1, y1, zf), col, studs="top", material=mat,
                      name="Orbite" if nom == "grotte" else "Rocher")
        # dos des orbites et du nez : une plaque d'os par creux, en léger retrait au dos (pas de faces confondues,
        # rien au-delà de z = -D)
        ea, eb = 1.21 * EA + 1.0, 1.21 * EB + 1.0
        for x0_, x1_, y0_, y1_ in ((-EX - ea, -EX + ea, EY - eb, EY + eb), (EX - ea, EX + ea, EY - eb, EY + eb),
                                   (-7.5 * sx - 1, 7.5 * sx + 1, YN0 - 1.0, YN1 + 1)):
            b.box((x0_, y0_, -D + 0.1), (x1_, y1_, -D + 2.0), vary(col_f("os"), rng, 0.03), name="DosCreux")

    # --- bouche : dents, gencives, parois en gradins, niche au trésor, cadre de sortie -----------------
    os_, osc, osf, oso = col_f("os"), col_f("os_clair"), col_f("os_fonce"), col_f("os_ombre")
    ZT = -4.5                                       # profondeur des dents
    with b.group("Bouche"):
        # fond sombre derrière les dents : la mâchoire se lit comme une bouche ouverte
        b.box((-P2, 36.0, ZT - 0.8), (P2, YJ, ZT - 0.2), c("grotte"), name="FondBouche", **NDS)
        # dents du haut : longues dents pointues au-dessus du couloir (pointes à y ≥ 36), canines aux deux bouts,
        # dents centrales plus longues, écarts sombres bien lisibles
        g = 2.0
        n = max(6, 2 * int(round((passage - 3.0) / 17.0)))
        w = (passage - 3.0 - (n - 1) * g) / n
        x0 = -(n * w + (n - 1) * g) / 2
        hp = min(3.4, 0.45 * w)                     # hauteur de la pointe (deux coins en V)
        for t in range(n):
            xa = x0 + t * (w + g)
            xb, xm_ = xa + w, xa + w / 2
            m = min(t, n - 1 - t)                   # 0 aux bouts (canines), n/2 - 1 au centre
            if m == 0:
                pointe = 36.3
            elif m == n // 2 - 1:
                pointe = 36.8
            else:
                pointe = 39.0 + 0.6 * ((3 * t) % 4)
            col_d = vary(c("dent"), rng, 0.015)
            b.box((xa, pointe + hp, ZT), (xb, YJ, 0.0), col_d, name="Dent")
            b.wedge_under((xa, pointe, ZT), (xm_, pointe + hp, 0.0), col_d, down="-x", name="Pointe")
            b.wedge_under((xm_, pointe, ZT), (xb, pointe + hp, 0.0), shade(col_d, 0.95), down="+x", name="Pointe")
        for sgn in (-1, 1):
            X = lambda d: sgn * (P2 + d)
            xa, xb = sorted((X(0.2), X(5.4)))
            b.box((xa, 33.0, ZT), (xb, YJ, 0.0), vary(c("dent"), rng, 0.015), name="Dent")
            # crocs du bas, plantés au sol à côté du couloir (corps et pointe en V), couleur d'os foncé
            lt = (wm - 0.6 - 2 * 0.6) / 3
            for kk, hd in enumerate((9.5, 8.0, 6.8)):
                d0 = 0.4 + kk * (lt + 0.6)
                xa, xb = sorted((X(d0), X(d0 + lt)))
                xm_ = (xa + xb) / 2
                col_d = vary(osf, rng, 0.03)
                hpt = min(2.6, 0.8 * lt)
                b.box((xa, 0, ZT), (xb, hd - hpt, 0.0), col_d, name="Croc")
                b.wedge((xa, hd - hpt, ZT), (xm_, hd, 0.0), col_d, down="-x", name="Croc")
                b.wedge((xm_, hd - hpt, ZT), (xb, hd, 0.0), shade(col_d, 0.94), down="+x", name="Croc")
            # gencive (front de mâchoire) au-dessus des dents du bas
            xa, xb = sorted((X(5.6), X(wm)))
            b.box((xa, 10.0, ZT), (xb, 33.0, -0.5), osf, name="Machoire")
            b.box((xa, 10.0, -0.5), (xb, 10.8, 0.0), osc, studs="top", name="Gencive")
            xa, xb = sorted((X(5.4), X(wm)))
            b.box((xa, 33.0, ZT), (xb, YJ, -0.5), os_, name="Machoire")
            # parois intérieures en gradins (côté couloir), niche du trésor à droite
            niche = sgn > 0
            zs = [(-D + 1.5, -22.0), (-14.0, ZT)] if niche else [(-D + 1.5, ZT)]
            for za, zb in zs:
                xa, xb = sorted((X(8.0), X(wm)))
                b.box((xa, -3.0, za), (xb, YJ, zb), oso, name="Paroi")
                xa, xb = sorted((X(5.0), X(8.0)))
                b.box((xa, 2.5, za), (xb, YJ, zb), osf, studs="top", name="Paroi")
                xa, xb = sorted((X(1.0), X(8.0)))
                b.box((xa, 0.0, za), (xb, 2.5, zb), vary(oso, rng, 0.04), studs="top", name="Banquette")
            if niche:
                b.box((P2 + 8.0, 11.0, -22.0), (XM, YJ, -14.0), oso, name="Paroi")
                b.box((P2 + 5.0, 11.0, -22.0), (P2 + 8.0, YJ, -14.0), osf, name="Paroi")
                b.box((P2 + 8.0, -3.0, -22.0), (XM, 0.2, -14.0), c("sable"), studs="top", name="SolNiche")
                with b.at((P2 + 9.6, 0.2, -18.0), yaw=90):
                    coffre_tresor(b, variant=0)
                b.box((XM - 0.4, 6.0, -18.6), (XM, 7.0, -17.4), c("fer"), name="Support", **ND)
                b.box((XM - 1.0, 7.0, -18.4), (XM - 0.2, 8.2, -17.6), c("flamme"), material="Neon", name="Flamme", **NDS)
            # consoles (coins arrondis du plafond)
            xa, xb = sorted((X(0.2), X(5.0)))
            b.wedge_under((xa, 36.0, -D + 1.5), (xb, YJ, ZT), osf, down="-x" if sgn > 0 else "+x", name="Console")
            # lanternes de paroi (potence fixée au gradin, verre à |x| ≥ P2 + 1)
            for zl in (-9.0, -27.0) if niche else (-9.0, -18.0, -27.0):
                xa, xb = sorted((X(5.0), X(2.4)))
                b.box((xa, 14.0, zl - 0.25), (xb, 14.5, zl + 0.25), c("fer"), name="Potence", **ND)
                _lanterne_navire(b, X(2.9), 14.0 - 2.8 * 0.95, zl, 0.95)
        # cadre de sortie (côté zone suivante), posé dans l'épaisseur du rocher : rien ne dépasse z = -D
        for sgn in (-1, 1):
            xa, xb = sorted((sgn * (P2 + 0.4), sgn * XM))
            b.box((xa, 0, -D), (xb, YJ - 3.0, -D + 1.5), osf, name="CadreSortie")
        b.box((-XM, YJ - 3.0, -D), (XM, YJ, -D + 1.5), osf, name="CadreSortie")
        # stalactites au plafond du passage (pointes à y ≥ 37, sans collision)
        for (xs, zs_, r) in ((-0.6, -12.0, 2.4), (-0.15, -24.0, 2.0), (0.3, -15.0, 2.6), (0.7, -26.0, 2.0)):
            xs *= P2
            yb = YJ
            kh = min(1.0, (YJ - 37.0) / 6.4)          # pointe toujours à y ≥ 37
            for kk, (rr, hh) in enumerate(((r, 2.4 * kh), (r * 0.62, 2.2 * kh), (r * 0.32, 1.8 * kh))):
                b.box((xs - rr, yb - hh, zs_ - rr), (xs + rr, yb + (0.3 if kk == 0 else 0.0), zs_ + rr),
                      vary(osf if kk == 0 else oso, rng, 0.04), name="Stalactite", **ND)
                yb -= hh

    # --- ornements du crâne : lierre, lianes, mousse, herbe, palmiers, mouettes, pavillon ----------------
    with b.group("Ornements"):
        # lierre qui pend du bout extérieur des arcades sourcilières, sur les tempes (accroché au surplomb)
        yv = min(ys[j] for j in range(ny) if (ys[j] + ys[j + 1]) / 2 >= EY + EB + 1)    # dessous des arcades
        for sgn in (-1, 1):
            for (dx, L) in ((0.78, 11.0), (1.06, 5.0)):
                xv = sgn * (EX + dx * EA)
                b.box((xv - 1.0, yv - L, 1.4), (xv + 1.0, yv + 0.4, 2.2), c("herbe_fonce"), name="Lierre", **NDS)
                b.box((xv - 0.7, yv - L * 0.55, 2.2), (xv + 0.7, yv + 0.4, 2.6), c("roche_mousse"), name="Lierre", **NDS)
        # lianes qui pendent du chapeau d'herbe des falaises, plaquées contre la paroi (même aplomb que l'herbe)
        for sgn in (-1, 1):
            for ax_ in np.arange(A_CR + 14.0, L2 - 8.0, 17.0):
                i = int((sgn * ax_ + L2) // CELL)
                rangs_herbe = [j for j in range(ny) if grille[j, i] is not None and grille[j, i][0] == "herbe"]
                if not rangs_herbe:
                    continue
                j_h = min(rangs_herbe)
                zf = grille[j_h, i][1]
                j = j_h - 1
                while j >= 0 and grille[j, i] is not None and grille[j, i][1] == zf:
                    j -= 1
                y_haut, y_min = ys[j_h], ys[j + 1]
                L = min(float(rng.uniform(6.0, 12.0)), y_haut - y_min - 0.5)
                if L < 3.0:
                    continue
                xc = -L2 + (i + 0.5) * CELL
                b.box((xc - 0.8, y_haut - L, zf), (xc + 0.8, y_haut + 0.6, zf + 0.4), c("herbe_fonce"), name="Liane", **NDS)
                b.box((xc - 0.5, y_haut - 0.6 * L, zf + 0.4), (xc + 0.5, y_haut + 0.6, zf + 0.7), c("herbe"), name="Liane",
                      **NDS)
        # touffes d'herbe et de mousse sur les gradins du crâne
        touffes = [(-60, -20), (-44, -24), (-22, -28), (-6, -30), (14, -29), (34, -26), (52, -22), (66, -18),
                   (-70, -12), (72, -10), (-36, -12), (40, -14)]
        # mousse sur les arcades sourcilières et les pommettes (en relief, z ≥ 2)
        for (tx, tz) in ((-36, 1.4), (-22, 1.4), (24, 1.4), (35, 1.4), (-68, 1.0), (67, 1.0)):
            tx = tx * sx + 0.13
            y = dessus(tx, tz)
            if y is None:
                continue
            w_ = float(rng.uniform(3.0, 5.5))
            # (dépasse de 0,1 devant la corniche : pas de face confondue avec le rocher)
            b.box((tx - w_ / 2, y - 0.2, tz - 1.6), (tx + w_ / 2, y + 0.6, tz + 1.7), c("roche_mousse"), studs="top",
                  name="Mousse", **ND)
        for (tx, tz) in touffes:
            tx = tx * sx + 0.13
            y = dessus(tx, tz)
            if y is None:
                continue
            w_ = float(rng.uniform(2.5, 5.0))
            col = c("herbe") if rng.uniform() < 0.6 else c("roche_mousse")
            b.box((tx - w_ / 2, y - 0.2, tz - 1.8), (tx + w_ / 2, y + 0.7, tz + 1.8), col, studs="top", name="Herbe", **ND)
        for (px, pz, h, cap) in ((-48, -16, 17, -150), (-30, -18, 15, 170), (44, -16, 18, 150), (60, -14, 14, 120)):
            px *= sx
            y = dessus(px, pz)
            if y is not None:
                _palmier(b, px, y, pz, h * k, cap, rng)
        # pavillon au sommet
        xm, zm = 8.0 * sx, -22.0
        ym = dessus(xm, zm) or hauteur
        b.box((xm - 2.0, ym, zm - 2.0), (xm + 2.0, ym + 1.4, zm + 2.0), c("roche"), studs="top", name="Cairn")
        b.cyl((xm, ym + 1.4 + 8.0, zm), 0.6, 16.0, c("bois_fonce"), name="Mat")
        b.cyl((xm, ym + 6.0, zm), 0.75, 0.8, c("corde"), name="Ligature", **ND)
        with b.at((xm, ym + 1.4 + 16.0 - 9.6, zm)):
            drapeau_pirate(b, variant=0, hauteur=9.6, largeur=11.0, mat=False)
        b.ball((xm, ym + 17.8, zm), 0.6, c("or"), name="Pomme", **ND)
        # mouettes sur les corniches
        for (gx, yaw, v) in ((-30, 20, 0), (26, -30, 1), (70, 160, 0), (-66, 200, 1)):
            gx *= sx
            y = dessus(gx, 1.5 if abs(gx) < 40 * sx else 1.0)
            if y is not None:
                with b.at((gx, y, 1.0), yaw=yaw):
                    mouette(b, variant=v)

    # --- mer : écume au pied, pitons rocheux, épave (gauche), cascade (droite) ---------------------------
    with b.group("Mer"):
        for sgn in (-1, 1):
            segs = [(max(P2 + 9.0, x_ecume), X_DEV, 0.0), (X_DEV, A_CR + 22, 2.0), (A_CR + 26, X_CASC - 6, 2.0),
                    (X_CASC + 6, L2 - 1, 2.0)]
            for xa_, xb_, zf in segs:
                if xb_ - xa_ < 2:
                    continue
                xa, xb = sorted((sgn * xa_, sgn * xb_))
                b.box((xa, -1.75, zf), (xb, -1.2, zf + float(rng.uniform(1.0, 2.2))), c("ecume"), name="Ecume", **NDS)
        pitons = [(-1, 84, 14, 7, 16), (-1, 202, 16, 9, 24), (1, 88, 12, 6, 13), (1, 128, 16, 9, 22), (1, 198, 12, 10, 30)]
        for (sgn, ax_, pz, r, h) in pitons:
            px = sgn * max(ax_, X_DEV + 3 + r)
            with b.group("Piton"):
                b.box((px - r, -3, pz - r * 0.8), (px + r, h * 0.45, pz + r * 0.8), vary("gres_fonce", rng, 0.05),
                      studs="top", name="Piton")
                b.box((px - r * 0.75, h * 0.45, pz - r * 0.6), (px + r * 0.7, h * 0.8, pz + r * 0.55), vary("gres", rng, 0.05),
                      studs="top", name="Piton")
                b.box((px - r * 0.5, h * 0.8, pz - r * 0.4), (px + r * 0.45, h, pz + r * 0.35), vary("gres_clair", rng, 0.05),
                      studs="top", name="Piton")
                b.box((px - r * 0.45, h, pz - r * 0.35), (px + r * 0.4, h + 0.6, pz + r * 0.3), c("herbe"), studs="top",
                      material="Grass", name="Herbe", **ND)
                b.box((px - r - 0.8, -1.75, pz - r * 0.8 - 0.8), (px + r + 0.8, -1.2, pz + r * 0.8 + 0.8), c("ecume"),
                      name="Ecume", **NDS)
        # plage et épave à gauche
        b.box((-180, -2.9, -1.0), (-120, -0.6, 16.0), c("sable"), studs="top", material="Sand", name="Plage")
        b.box((-176, -2.9, 16.0), (-124, -1.2, 19.0), c("sable_mouille"), studs="top", material="Sand", name="Plage")
        b.box((-177, -1.75, 19.0), (-123, -1.25, 20.2), c("ecume"), name="Ecume", **NDS)
        _epave(b, -150.0, 7.0, rng)
        # cascade à droite (tombe de la faille de la falaise)
        # cascade en gradins : une nappe d'eau par gradin de la faille, écume à chaque ressaut, bassin au pied
        hc = HC_CASC
        xa, xb = X_CASC - 5.4, X_CASC + 5.4
        bornes = [-1.6, 0.18 * hc, 0.5 * hc, 0.8 * hc, hc]
        z_haut = z_falaise(X_CASC, 0.9 * hc, hc, 1) - 4.0
        b.box((xa, hc - 0.2, -D + 4.0), (xb, hc + 0.5, z_haut + 1.4), c("cascade"), name="Ruisseau", **ND)
        zcs = [z_falaise(X_CASC, max((bornes[i] + bornes[i + 1]) / 2, 0.5), hc, 1) - 4.0 for i in range(4)]
        for i in range(4):
            y0, y1 = bornes[i], bornes[i + 1]
            zc = zcs[i]
            b.box((xa, y0, zc + 0.2), (xb, y1 + 0.4, zc + 1.4), c("cascade"), transparency=0.1, name="Cascade", **ND)
            b.box((xa + 2.2, y0, zc + 1.4), (xb - 2.2, y0 + (y1 - y0) * 0.6, zc + 1.9), c("ecume"), transparency=0.15,
                  name="Cascade", **NDS)
            if i < 3:   # écume sur le ressaut : l'eau du gradin supérieur se brise sur le dessus du gradin inférieur
                b.box((xa - 0.3, y1 - 0.1, zcs[i + 1] + 1.4), (xb + 0.3, y1 + 0.6, zc + 1.6), c("ecume"), name="Ecume", **NDS)
        z0 = z_falaise(X_CASC, 0.5, hc, 1) - 4.0
        b.box((xa - 4.0, -1.75, z0 + 1.4), (xb + 4.0, -1.0, z0 + 10.0), c("ecume"), name="Bassin", **NDS)
        for (dx, dz, r) in ((-3.0, 4.0, 1.6), (2.5, 5.0, 1.3), (0.0, 7.5, 1.0)):
            b.ball((X_CASC + dx, -0.6, z0 + dz), r, c("ecume"), transparency=0.25, name="Embruns", **NDS)
        for (px, pz, h, cap) in ((X_CASC - 12, -12.0, 12, 70), (X_CASC + 12, -16.0, 14, 120), (X_CASC + 24, -10.0, 11, 40)):
            y = dessus(px, pz)
            if y is not None:
                _palmier(b, px, y, pz, h, cap, rng)
        for (px, pz, h, cap) in ((-(A_CR + 8), -16.0, 12, -60), (-196.0, -14.0, 13, -120)):
            y = dessus(px, pz)
            if y is not None:
                _palmier(b, px, y, pz, h, cap, rng)

    return {"emprise": (largeur, profondeur), "hauteur": hauteur}
