"""Ouvrages qui enjambent le couloir : viaduc ferroviaire d'entrée (gare aérienne, boutiques sous les
voies), train de banlieue à livrée inventée, passerelles piétonnes en acier (hodōkyō).

Repère Roblox (Y en haut, 1 unité = 1 stud). Couloir de course élargi : x ∈ [-45, 45] (90 de large),
trottoirs jusqu'aux façades en |x| = 55 ; au-dessus de |x| < 46, rien ne descend sous y = 30. Ces ouvrages
passent au-dessus : le dessous du viaduc est à 36, celui des passerelles à 34 (garde-corps, panneaux et
lampes compris, tous posés au-dessus du tablier). Toutes les cotes en x se déduisent des paramètres
`passage` (viaduc, 92 entre piles) et `portee` (passerelles, 110) : l'ancien couloir (66 / 84) marche aussi.

viaduc_ferroviaire (≈ 690 pièces, gare comprise)
    Posé une fois en (0, 0, 0), sans rotation : repère local = repère monde. Tablier de x = -238 à 238,
    z ∈ [-8, 8] : poutre-caisson en béton, corniche, parapets à studs, voies (ballast, traverses, rails),
    portiques de caténaire et fils. Au-dessus du couloir, un pont à poutres d'acier bleues SOUS les voies
    (le train reste visible de la rue) porte la plaque 渋谷 sur ses deux faces (seul emploi de ce nom),
    avec une clôture ajourée au-dessus. Néon le long du bas des poutres.
    Piles du couloir sur les trottoirs (x ∈ ±[47,5 ; 54,5]), à chapiteau en marteau ; autres piles tous les
    40 studs. Sous les voies, de part et d'autre, de hautes arches de brique (gādo-shita) abritent des
    boutiques traversantes : devanture, mezzanine éclairée et enseignes côté +Z (face vue en arrivant),
    devanture simple côté -Z (contre l'arrière de la rue commerçante). Gare aérienne en x ∈ [-163, -59] :
    quais latéraux couverts, panneaux 駅 ; au sol, le hall à long mur-rideau vitré éclairé (entrées 東口 et
    駅 côté +Z, 西口 côté -Z), enseigne verticale 駅 au coin côté couloir.
train_banlieue (≤ 45 pièces par voiture)
    Train inox à bandes violette et cyan (livrée inventée), origine au centre du train au niveau du dessus
    des rails, voitures alignées selon X, tête (feux blancs) vers +X, queue (feux rouges) vers -X.
passerelle_pietons (≈ 160 à 200 pièces)
    Passerelle d'acier au-dessus du couloir (dessous à 34), tours d'appui sur les trottoirs (|x| ≥ 46,5) et
    escaliers raides à palier le long des trottoirs. Variante 0 : acier bleu, garde-corps blancs, panneau de
    direction bleu 駅 / 東口. Variante 1 : acier blanc-gris, garde-corps vitrés, auvent sur poteaux.

Propriété intellectuelle : aucune livrée, aucun nom de compagnie ni de ligne réels ; seuls textes :
渋谷 (une fois), 駅, 東口, 西口, ラーメン, 寿司, 喫茶, 本, 薬, 24H.
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, rot_x, rot_z, shade
from palette import c, vary

# Faces portant un texte selon le côté : +Z → « Back », -Z → « Front » ; +X → « Right », -X → « Left ».
FACE_Z = {1: "Back", -1: "Front"}
FACE_X = {1: "Right", -1: "Left"}
BLEU_TEXTE = (34, 46, 92)        # bleu nuit des lettres sur fond blanc
BLANC_TEXTE = (250, 250, 252)

PETIT = dict(collide=False, shadow=False)   # petits détails : ni collision, ni ombre


NEON = dict(material="Neon", collide=False, shadow=False)   # néons, écrans et vitrines éclairées


# ===========================================================================
# 1. Viaduc ferroviaire, gare aérienne et boutiques sous les voies
# ===========================================================================

Z_VOIES = (-3.5, 3.5)        # axes des deux voies
ECART_RAIL = 0.85            # demi-écartement des rails (voie étroite, à l'échelle du train de 4,6)
LONG_GARE = 104.0            # longueur de la gare aérienne (quais et hall), côté gauche (x < 0)
# Côté -Z, la gare s'arrête en z = -11,8 : la rue commerçante et la seconde rangée commencent en z = -12
# (zone.py), le hall et les quais ne doivent pas les traverser. Côté +Z (parvis), elle va jusqu'à 14.
GARE_Z = (-11.8, 14.0)


def geometrie_couloir(passage: float) -> dict:
    """Cotes en x déduites de la largeur libre `passage` (= 2 × demi-couloir + 2) : tout suit le couloir.

    Couloir de 90 (|x| < 45, passage 92) : piles du couloir en |x| ∈ [47,5 ; 54,5] sur les trottoirs,
    façades en |x| = 55, premières arches à partir de |x| = 59, gare en x ∈ [-163, -59].
    (Ancien couloir de 64, passage 66 : piles en [34,5 ; 41,5], arches à partir de 46, gare en [-150, -46].)"""
    hl = passage / 2                 # au-dessus de |x| < hl, rien sous y = 30
    xi = hl + 1.5                    # face des piles du couloir côté couloir
    xo = xi + 7.0                    # face extérieure (≈ alignement des façades - 0,5)
    xa = xo + 4.5                    # début des arches (après le pilastre contre la pile)
    return {"hl": hl, "xi": xi, "xo": xo, "xa": xa, "xt": hl + 7.0, "gare": (-(xa + LONG_GARE), -xa)}

BOUTIQUES = {
    # texte, fond de l'enseigne, couleur du texte, vitrine, extra
    "ramen": ("ラーメン", "noren_rouge", BLANC_TEXTE, "fenetre_chaude", "lampions"),
    "sushi": ("寿司", "enseigne_blanc", BLEU_TEXTE, "fenetre_chaude", "noren"),
    "cafe": ("喫茶", "enseigne_noir", (255, 214, 120), "fenetre_chaude", "auvent"),
    "livres": ("本", "auvent_bleu", BLANC_TEXTE, "fenetre_froide", "livres"),
    "pharma": ("薬", "enseigne_blanc", (47, 95, 184), "fenetre_froide", "croix"),
    "ferme": (None, "rideau_fonce", None, None, "rideau"),
    "kiosque": ("24H", "auvent_rouge", BLANC_TEXTE, "fenetre_froide", "auvent"),
}
# Boutiques des faces +Z (côté parvis, très vues) et -Z (ruelles), dans l'ordre des arches.
ORDRE_PZ = ["ramen", "cafe", "livres", "ferme", "sushi", "pharma", "ramen", "ferme", "cafe", "livres", "sushi", "ramen",
            "pharma", "cafe"]
ORDRE_MZ = ["ferme", "sushi", "ramen", "cafe", "ferme", "livres", "pharma", "sushi", "ferme", "ramen", "cafe", "ferme",
            "livres", "sushi"]
HAUTS = ["affiche", "enseigne", "vide", "affiche", "grille", "enseigne", "affiche", "vide"]
AFFICHES = [("ecran_bleu", "neon_cyan"), ("ecran_rose", "neon_jaune"), ("ecran_orange", "neon_blanc"),
            ("neon_cyan", "ecran_bleu"), ("ecran_rose", "ecran_bleu")]


def _pal_viaduc(v: int) -> dict:
    """Couleurs selon la variante : 0 béton et travée d'acier bleu ; 1 poutres d'acier partout et arches
    en béton ; 2 comme 0 en brique sombre et néon blanc ; 3 comme 1 avec néon cyan."""
    acier = v % 2 == 1
    return {
        "acier": acier,
        "poutre": c("acier_bleu") if acier else c("viaduc"),
        "corniche": c("acier_bleu_fonce") if acier else c("viaduc_clair"),
        "parapet": c("metal_clair") if acier else c("viaduc_clair"),
        "pile": c("beton") if acier else c("viaduc_fonce"),
        "chapiteau": c("beton_clair") if acier else c("viaduc"),
        "travee": c("acier_bleu"),
        "travee_fonce": c("acier_bleu_fonce"),
        "mur": c("beton") if acier else (c("brique_fonce") if v == 2 else c("brique")),
        "bandeau": c("beton_clair") if not acier else c("viaduc_clair"),
        "fond": c("anthracite"),
        "neon": c("neon_cyan") if v in (0, 3) else c("neon_blanc"),
        "mat": {"material": "Metal"} if acier else {"material": "Concrete"},   # texture Roblox des poutres
    }


def _tablier_beton(b, x0, x1, pal, yd, yc, ys, yp, za=-8.0, zb=8.0, parapets=True) -> None:
    """Travée courante : poutre-caisson, corniche-dalle en saillie, parapets à studs, néon sous la poutre."""
    b.box((x0, yd, za), (x1, yc, zb), vary(pal["poutre"], b.rng, 0.02), name="Poutre", **pal["mat"])
    b.box((x0, yc, za - 0.5), (x1, ys, zb + 0.5), pal["corniche"], studs="top", name="Corniche")
    for s, zf in ((-1, za), (1, zb)):
        if parapets:
            b.box((x0, ys, zf - s * 0.6), (x1, yp, zf + s * 0.3), pal["parapet"], studs="top", name="Parapet")
        b.box((x0, yd + 0.15, zf), (x1, yd + 0.5, zf + s * 0.15), pal["neon"], name="Neon", **NEON)


def _travee_acier(b, x0, x1, pal, yd, ys, yp, texte: str | None) -> None:
    """Travée au-dessus du couloir : pont à poutres sous voies (le train reste visible de la rue). Deux poutres
    de rive à âme pleine de yd à ys + 1 (niveau des rails), semelles, raidisseurs, dalle d'acier, entretoises et rampes de
    lumière dessous ; au-dessus, une simple clôture de sécurité ajourée. Plaque de gare sur les deux faces."""
    ac, acf = pal["travee"], pal["travee_fonce"]
    yh = ys + 1.0                   # haut des poutres de rive (au niveau des rails)
    with b.group("TraveeAcier"):
        b.box((x0, ys - 1.6, -7.5), (x1, ys, 7.5), ac, studs="top", name="Platelage")
        for s in (-1, 1):
            b.box((x0, yd + 0.6, s * 7.5), (x1, yh - 0.5, s * 8.3), ac, name="Ame")
            b.box((x0, yd, s * 7.2), (x1, yd + 0.6, s * 8.8), acf, name="Semelle")
            b.box((x0, yh - 0.5, s * 7.2), (x1, yh, s * 8.8), acf, studs="top", name="Semelle")
            b.box((x0, yd + 0.12, s * 8.8), (x1, yd + 0.48, s * 8.95), pal["neon"], name="Neon", **NEON)
            # raidisseurs verticaux (sauf derrière la plaque) ; un sur deux porte un poteau de clôture
            n = int((x1 - x0) // 6)
            for k in range(n + 1):
                x = x0 + 1.5 + k * (x1 - x0 - 3.0) / n
                if not (texte and abs(x) < 13.6):
                    b.box((x - 0.25, yd + 0.6, s * 8.3), (x + 0.25, yh - 0.5, s * 8.5), acf, **PETIT, name="Raidisseur")
                if k % 2 == 0:
                    b.box((x - 0.2, yh, s * 8.0), (x + 0.2, yp - 0.4, s * 8.4), c("metal_clair"), collide=False, name="Poteau")
            # clôture ajourée : lisse basse, lisse haute (main courante), grillage translucide
            b.box((x0, yh + 0.6, s * 8.05), (x1, yh + 0.9, s * 8.35), c("metal_clair"), collide=False, name="Lisse")
            b.box((x0, yp - 0.4, s * 7.95), (x1, yp, s * 8.45), c("metal_clair"), studs="top", name="MainCourante")
            b.box((x0, yh, s * 8.15), (x1, yp - 0.4, s * 8.25), c("metal"), transparency=0.6, **PETIT, name="Grillage")
            if texte:
                b.box((-12.6, yd + 0.5, s * 8.3), (12.6, yh - 0.3, s * 8.6), c("bleu_nuit"), collide=False, name="CadrePlaque")
                p = b.box((-12.0, yd + 0.9, s * 8.6), (12.0, yh - 0.7, s * 8.85), c("enseigne_blanc"), collide=False,
                          name="PlaqueGare")
                p.label = {"face": FACE_Z[s], "text": texte, "color": BLEU_TEXTE, "bg": None, "font": "sans", "glow": 0.9}
                # filet bleu sous le nom, comme sur les plaques de gare ; deux lampes de plaque au-dessus
                b.box((-11.4, yd + 1.2, s * 8.85), (11.4, yd + 1.5, s * 8.95), c("auvent_bleu"), **PETIT, name="Filet")
                for xl in (-8.0, 8.0):
                    a_, b_ = sorted((s * 8.6, s * 9.6))
                    b.box((xl - 1.0, yh - 0.35, a_), (xl + 1.0, yh - 0.05, b_), c("metal_fonce"), **PETIT, name="Lampe")
                    b.box((xl - 0.8, yh - 0.55, a_ + 0.3), (xl + 0.8, yh - 0.35, b_ - 0.1), c("neon_blanc"), name="Lampe", **NEON)
        # entretoises sous le tablier, avec rampes de lumière au milieu
        n = int((x1 - x0) // 8)
        for k in range(n + 1):
            x = x0 + 2.0 + k * (x1 - x0 - 4.0) / n
            b.box((x - 0.4, yd + 1.3, -7.5), (x + 0.4, ys - 1.6, 7.5), acf, name="Entretoise")
        for z in (-3.5, 3.5):
            b.box((x0 + 2.4, yd + 1.0, z - 0.35), (x1 - 2.4, yd + 1.3, z + 0.35), c("neon_blanc"), name="Rampe", **NEON)


def _pile_couloir(b, s, pal, yd, txt: str | None, ecran, geo: dict) -> None:
    """Pile posée sur le trottoir (x ∈ s·[xi ; xo], z ∈ [-5, 5]) : fût, chapiteau en marteau, appareils
    d'appui, bande de protection jaune et noire, panneau ou écran sur la face qui regarde le couloir."""
    X0, X1 = geo["xi"], geo["xo"]
    xa, xb = sorted((s * X0, s * X1))
    xi = s * X0        # face côté couloir
    with b.group("Piles/Couloir"):
        b.box((xa, 0, -5.4), (xb, 1.0, 5.4), c("beton_fonce"), studs="top", name="Semelle")
        b.box((xa, 1.0, -5.0), (xb, yd - 5.0, 5.0), pal["pile"], name="Fut", material="Concrete")
        b.box((xa, yd - 5.0, -8.0), (xb, yd - 0.6, 8.0), pal["chapiteau"], name="Chapiteau")
        for sz in (-1, 1):
            b.wedge_under((xa, yd - 9.0, sz * 5.0), (xb, yd - 5.0, sz * 8.0), pal["chapiteau"],
                          down="+z" if sz > 0 else "-z", name="Console")
        # appareils d'appui : sous les poutres d'acier (côté couloir) et sous la travée de béton
        for sz in (-1, 1):
            a, bb = sorted((s * (X0 + 2.9), s * (X0 + 5.1)))
            b.box((a, yd - 0.6, sz * 7.0), (bb, yd, sz * 8.6), c("metal_fonce"), name="Appui")
        a, bb = sorted((s * (X0 + 5.7), s * (X0 + 6.9)))
        b.box((a, yd - 0.6, -7.4), (bb, yd, 7.4), c("metal_fonce"), name="Appui")
        # bande de protection (choc des véhicules)
        a, bb = sorted((s * (X0 - 0.1), s * (X1 + 0.1)))
        b.box((a, 1.0, -5.1), (bb, 3.4, 5.1), c("chantier_jaune"), collide=False, name="Protection")
        a, bb = sorted((s * (X0 - 0.2), s * (X1 + 0.2)))
        for y in (1.5, 2.5):
            b.box((a, y, -5.2), (bb, y + 0.45, 5.2), c("chantier_noir"), **PETIT, name="Rayure")
        # sur la face couloir : panneau bleu ou écran lumineux abstrait (|x| ≥ 34,2 : hors couloir)
        a, bb = sorted((xi, xi - s * 0.2))
        if txt:
            b.box((a, 8.6, -3.6), (bb, 13.4, 3.6), c("blanc"), collide=False, name="Cadre")
            a2, bb2 = sorted((xi - s * 0.2, xi - s * 0.35))
            p = b.box((a2, 8.9, -3.3), (bb2, 13.1, 3.3), c("auvent_bleu"), collide=False, name="Panneau")
            p.label = {"face": FACE_X[-s], "text": txt, "color": BLANC_TEXTE, "font": "sans"}
        if ecran:
            fond, aplat = ecran
            b.box((a, 15.0, -4.0), (bb, 27.0, 4.0), c("ecran_fond"), collide=False, name="Ecran")
            a2, bb2 = sorted((xi - s * 0.2, xi - s * 0.3))
            b.box((a2, 15.6, -3.4), (bb2, 26.4, 3.4), c(fond), name="Aplat", **NEON)
            a3, bb3 = sorted((xi - s * 0.3, xi - s * 0.4))
            b.box((a3, 18.0, -3.4), (bb3, 21.0, 3.4), c(aplat), name="Aplat", **NEON)
            b.box((a3, 22.4, -1.0), (bb3, 25.2, 1.8), c("neon_blanc"), name="Aplat", **NEON)


def _pile(b, x, pal, yd, w=5.0) -> None:
    """Pile courante, prise dans les arches : pilastre de béton plus saillant que le remplissage."""
    with b.group("Piles"):
        b.box((x - w / 2, 0, -7.6), (x + w / 2, yd - 3.0, 7.6), pal["pile"], name="Pile", material="Concrete")
        b.box((x - w / 2 - 0.3, yd - 3.0, -7.9), (x + w / 2 + 0.3, yd, 7.9), pal["chapiteau"], name="Chapiteau")


def _devanture(b, xa, xb, s, kind, pal) -> None:
    """Devanture d'une boutique sous les voies, sur la face s (z = s·6 est le fond de l'arche)."""
    rng = b.rng
    texte, fond, tcol, vitrine, extra = BOUTIQUES[kind]
    face = FACE_Z[s]
    xm = (xa + xb) / 2
    z0 = s * 6.0
    if extra == "rideau":
        b.box((xa + 0.8, 0, z0), (xb - 0.8, 8.4, s * 6.2), vary("rideau_metal", rng, 0.04), name="Rideau")
        b.box((xa + 0.6, 8.4, z0), (xb - 0.6, 9.2, s * 6.6), c("rideau_fonce"), name="Coffre")
        for y in (2.6, 5.4):
            b.box((xa + 0.8, y, s * 6.2), (xb - 0.8, y + 0.25, s * 6.3), c("rideau_fonce"), **PETIT, name="Lame")
        # tags abstraits (taches de couleur, aucun texte)
        g = ("graffiti_1", "graffiti_2", "graffiti_3")
        k = int(rng.integers(0, 3))
        w = xb - xa
        x1 = xa + 1.6 + float(rng.uniform(0, w * 0.3))
        b.box((x1, 1.0, s * 6.2), (x1 + w * 0.32, 3.6, s * 6.32), c(g[k]), **PETIT, name="Tag")
        x2 = xb - 1.6 - w * 0.28
        b.box((x2, 3.2, s * 6.2), (x2 + w * 0.22, 5.0, s * 6.34), c(g[(k + 1) % 3]), **PETIT, name="Tag")
        b.box((xa + 2.6, 9.6, z0), (xb - 2.6, 11.2, s * 6.4), c("enseigne_noir"), collide=False, name="Enseigne")
        return
    b.box((xa + 0.8, 0.6, z0), (xb - 0.8, 8.2, s * 6.12), c(vitrine), name="Vitrine", **NEON)
    dx = (xb - xa) * 0.2 * (1 if (int(xa) // 7) % 2 else -1)
    b.box((xm + dx - 1.3, 0, s * 6.12), (xm + dx + 1.3, 7.0, s * 6.24), c("vitre"), collide=False, name="Porte")
    b.box((xa + 0.8, 7.0, s * 6.12), (xb - 0.8, 7.4, s * 6.24), c("metal_fonce"), **PETIT, name="Imposte")
    p = b.box((xa + 2.6, 8.8, z0), (xb - 2.6, 11.0, s * 6.45), c(fond), collide=False, name="Enseigne")
    p.label = {"face": face, "text": texte, "color": tcol, "font": "sans", "glow": 1.2}
    if extra == "lampions":
        for x in (xa + 1.7, xb - 1.7):
            b.cyl((x, 6.2, s * 6.7), 0.62, 1.5, c("lampion"), axis="y", name="Lampion", **NEON)
        b.box((xm + dx - 2.2, 5.0, s * 6.24), (xm + dx + 2.2, 7.0, s * 6.36), c("noren_rouge"), **PETIT, name="Noren")
    elif extra == "noren":
        p = b.box((xm + dx - 2.0, 5.0, s * 6.24), (xm + dx + 2.0, 7.0, s * 6.36), c("noren_bleu"), **PETIT, name="Noren")
        b.cyl((xb - 1.7, 6.2, s * 6.7), 0.62, 1.5, c("fenetre_chaude"), axis="y", name="Lanterne", **NEON)
    elif extra == "auvent":
        col = "auvent_rouge" if kind == "cafe" else "auvent_bleu"
        b.wedge((xa + 0.6, 7.5, s * 6.24), (xb - 0.6, 8.6, s * 8.4), c(col), down="+z" if s > 0 else "-z",
                studs="top", collide=False, name="Auvent")
    elif extra == "livres":
        cols = ("boisson_1", "boisson_2", "boisson_3", "boisson_4")
        for i, y in enumerate((1.4, 3.6)):
            b.box((xa + 1.4, y, s * 6.12), (xb - 1.4, y + 1.1, s * 6.22), c(cols[(i + int(xa)) % 4]), **PETIT, name="Livres")
    elif extra == "croix":
        b.box((xb - 2.0, 4.0, s * 6.12), (xb - 1.2, 6.4, s * 6.3), c("neon_vert"), name="Croix", **NEON)
        b.box((xb - 2.6, 4.8, s * 6.12), (xb - 0.6, 5.6, s * 6.3), c("neon_vert"), name="Croix", **NEON)


def _devanture_arriere(b, xa, xb, kind) -> None:
    """Devanture simplifiée de la face -Z (côté ruelle, presque cachée par la rue commerçante) :
    vitrine éclairée et petite enseigne, ou rideau baissé."""
    texte, fond, tcol, vitrine, extra = BOUTIQUES[kind]
    if extra == "rideau":
        b.box((xa + 0.8, 0, -6.2), (xb - 0.8, 8.4, -6.0), vary("rideau_metal", b.rng, 0.04), collide=False, name="Rideau")
        return
    b.box((xa + 0.8, 0.6, -6.12), (xb - 0.8, 8.2, -6.0), c(vitrine), name="Vitrine", **NEON)
    p = b.box((xa + 2.6, 8.8, -6.45), (xb - 2.6, 11.0, -6.0), c(fond), collide=False, name="Enseigne")
    p.label = {"face": "Front", "text": texte, "color": tcol, "font": "sans", "glow": 1.2}


def _etage(b, xa, xb, k: int) -> None:
    """Mezzanine dans le haut de l'arche (face +Z) : appui, bandeau vitré, vitres éclairées (Neon)."""
    b.box((xa + 1.0, 12.0, 6.0), (xb - 1.0, 12.4, 6.6), c("metal_fonce"), **PETIT, name="Appui")
    b.box((xa + 1.6, 12.4, 6.0), (xb - 1.6, 16.6, 6.12), c("vitre"), collide=False, name="Etage")
    xm = (xa + xb) / 2
    col = ("fenetre_chaude", "fenetre_rose", "fenetre_froide")[k % 3]
    if k % 4 == 3:
        return                                   # étage éteint
    if k % 2:
        b.box((xa + 2.0, 12.8, 6.12), (xm - 0.4, 16.2, 6.22), c(col), name="Fenetre", **NEON)
    else:
        b.box((xa + 2.0, 12.8, 6.12), (xb - 2.0, 16.2, 6.22), c(col), name="Fenetre", **NEON)
        for x in (xm - (xb - xa) / 6, xm + (xb - xa) / 6):
            b.box((x - 0.2, 12.4, 6.22), (x + 0.2, 16.6, 6.32), c("metal_fonce"), **PETIT, name="Meneau")


def _haut_de_baie(b, xa, xb, kind, k, y0: float, y1: float) -> None:
    """Habillage du mur de brique au-dessus de l'arche (face +Z, mur en z = 6,5), entre y0 et y1 : affiche
    lumineuse abstraite, enseigne horizontale (カラオケ, 映画) ou grille de ventilation."""
    zw = 6.5
    xm = (xa + xb) / 2
    if kind == "affiche":
        fond, aplat = AFFICHES[k % len(AFFICHES)]
        b.box((xa + 2.0, y0, zw), (xb - 2.0, y1, 6.75), c("ecran_fond"), collide=False, name="Affiche")
        b.box((xa + 2.6, y0 + 0.6, 6.75), (xb - 2.6, y1 - 0.6, 6.85), c(fond), name="Aplat", **NEON)
        h = (y1 - y0) * (0.25 + 0.08 * (k % 3))
        b.box((xa + 2.6, y0 + 2.0, 6.85), (xm + 1.0, y0 + 2.0 + h, 6.95), c(aplat), name="Aplat", **NEON)
        b.box((xb - 6.6, y1 - 4.6, 6.85), (xb - 3.4, y1 - 1.4, 7.05), c("neon_blanc"), name="Aplat", **NEON)
    elif kind == "enseigne":
        texte, col = (("カラオケ", "neon_magenta"), ("映画", "neon_jaune"), ("喫茶", "neon_orange"))[k % 3]
        L = min(xb - xa - 4.0, 4.2 * len(texte) + 2.0)
        ym = (y0 + y1) / 2
        b.box((xm - L / 2 - 0.3, ym - 2.5, zw), (xm + L / 2 + 0.3, ym + 2.5, 6.9), c(col), name="Cadre", **NEON)
        p = b.box((xm - L / 2, ym - 2.2, 6.9), (xm + L / 2, ym + 2.2, 7.05), c("enseigne_noir"), collide=False, name="Enseigne")
        p.label = {"face": "Back", "text": texte, "color": c(col), "font": "sans", "glow": 1.3}
    elif kind == "grille":
        for y in (y0 + 3.0, y0 + 4.6, y0 + 6.2):
            b.box((xa + 4.0, y, zw), (xb - 4.0, y + 0.8, 6.75), c("metal_fonce"), **PETIT, name="Grille")


def _arches(b, x0, x1, pal, k0: int, yd) -> int:
    """Remplissage d'une travée entre deux piles : mur de brique jusqu'à la poutre, bandeau d'imposte,
    une ou deux hautes arches à boutiques traversantes (devanture et mezzanine éclairée côté +Z,
    devanture simple côté -Z). Renvoie le nombre d'arches posées."""
    W = x1 - x0
    yh = 20.0      # sommet des arches
    mat = {"material": "Brick"} if pal["mur"] in (c("brique"), c("brique_fonce")) else {"material": "Concrete"}
    with b.group("GadoShita"):
        b.box((x0, yh + 0.5, -6.5), (x1, yd, 6.5), vary(pal["mur"], b.rng, 0.03), name="Mur", **mat)
        b.box((x0, yh, -6.7), (x1, yh + 1.0, 6.7), pal["bandeau"], name="Bandeau")
        b.box((x0, yd - 2.4, -6.8), (x1, yd - 1.6, 6.8), pal["bandeau"], collide=False, name="Bandeau")
        if W < 12:
            # étroit : sortie secondaire éclairée côté +Z, porte de service côté -Z
            b.box((x0, 0, -6.5), (x1, yh, 6.5), pal["mur"], name="Mur", **mat)
            b.box((x0 + 0.8, 0, 6.5), (x1 - 0.8, 7.4, 6.62), c("fenetre_froide"), name="Vitrine", **NEON)
            p = b.box((x0 + 1.0, 8.2, 6.5), (x1 - 1.0, 10.4, 6.9), c("auvent_bleu"), collide=False, name="Enseigne")
            p.label = {"face": "Back", "text": "出口", "color": BLANC_TEXTE, "font": "sans", "glow": 1.2}
            return 0
        n = 2 if W >= 24 else 1
        bornes = [x0] + [x0 + W * i / n for i in range(1, n)] + [x1]
        for i in range(n):
            xa, xb = bornes[i], bornes[i + 1]
            if i > 0:
                b.box((xa - 0.8, 0, -7.0), (xa + 0.8, yh, 7.0), pal["mur"], name="Pilastre", **mat)
                xa += 0.8
            if i < n - 1:
                xb -= 0.8
            k = k0 + i
            b.box((xa, 0, -6.0), (xb, yh, 6.0), pal["fond"], name="Boutique")
            b.wedge_under((xa, yh - 4.5, -6.5), (xa + 3.2, yh, 6.5), pal["mur"], down="+x", name="Ecoincon", **mat)
            b.wedge_under((xb - 3.2, yh - 4.5, -6.5), (xb, yh, 6.5), pal["mur"], down="-x", name="Ecoincon", **mat)
            _devanture(b, xa, xb, 1, ORDRE_PZ[k % len(ORDRE_PZ)], pal)
            _etage(b, xa, xb, k)
            _devanture_arriere(b, xa, xb, ORDRE_MZ[k % len(ORDRE_MZ)])
            _haut_de_baie(b, xa, xb, HAUTS[k % len(HAUTS)], k, yh + 2.2, yd - 3.4)
        return n


def _hall_gare(b, x0, x1, za, zb, yd) -> None:
    """Hall de la gare sous les voies : façades vitrées éclairées sur les deux faces, entrées à auvent
    (駅 et 東口 côté +Z, 西口 côté -Z), étage de la salle des billets, écrans et grand panneau 駅."""
    def zz(d0, d1):
        return sorted((zf + s * d0, zf + s * d1))

    with b.group("Gare/Hall"):
        b.box((x0, 0, za), (x1, yd, zb), c("beton_clair"), name="Hall")
        b.box((x0 - 0.2, 0, za - 0.2), (x1 + 0.2, 0.6, zb + 0.2), c("beton_fonce"), studs="top", name="Socle")
        xm = (x0 + x1) / 2
        for s, zf in ((1, zb), (-1, za)):
            face = FACE_Z[s]
            principale = s > 0          # la face +Z (parvis, vue en arrivant) ; -Z est contre la rue commerçante
            # --- rez-de-chaussée : vitrine sombre continue, piliers, panneaux éclairés, entrées ---------
            a, bb = zz(0, 0.12)
            b.box((x0 + 1.0, 0.6, a), (x1 - 1.0, 9.0, bb), c("vitre"), collide=False, name="Vitrine")
            n = 12 if principale else 4
            larg = (x1 - x0 - 2.0) / n
            entrees = [(x1 - 26.0, "東口"), (x0 + 22.0, "駅")] if principale else [(x1 - 27.0, "西口")]
            for i in range(n + 1):
                xp = x0 + 1.0 + i * larg
                a, bb = zz(0, 0.5)
                b.box((xp - 0.6, 0.6, a), (xp + 0.6, 9.0, bb), c("beton_clair"), name="Pilier")
                if i == n:
                    break
                xa, xb = xp + 0.6, xp + larg - 0.6
                xc = (xa + xb) / 2
                if any(abs(xc - xe) < larg / 2 for xe, _ in entrees):
                    a, bb = zz(0.12, 0.22)
                    b.box((xa + 0.6, 0.6, a), (xb - 0.6, 7.2, bb), c("enseigne_noir"), **PETIT, name="Entree")
                    b.box((xa + 0.6, 7.2, a), (xb - 0.6, 7.6, bb), c("neon_blanc"), name="Imposte", **NEON)
                elif i % 4 != 2:
                    a, bb = zz(0.12, 0.22)
                    col = "fenetre_chaude" if i % 3 == 0 else "fenetre_froide"
                    b.box((xa + 0.3, 1.2, a), (xb - 0.3, 8.4, bb), c(col), name="Vitrage", **NEON)
            # --- marquise continue sur le rez-de-chaussée, rampe lumineuse dessous, enseignes d'entrée --
            prof = 3.6 if principale else 2.4
            a, bb = zz(0, prof)
            b.box((x0 + 1.0, 9.0, a), (x1 - 1.0, 9.8, bb), c("metal_clair"), studs="top", name="Marquise")
            a, bb = zz(prof, prof + 0.3)
            b.box((x0 + 1.0, 8.8, a), (x1 - 1.0, 10.4, bb), c("bleu_marine"), collide=False, name="Rive")
            a, bb = zz(prof - 0.6, prof - 0.2)
            b.box((x0 + 1.4, 8.6, a), (x1 - 1.4, 9.0, bb), c("neon_blanc"), name="Rampe", **NEON)
            for xe, txt in entrees:
                a, bb = zz(prof + 0.3, prof + 0.5)
                p = b.box((xe - 4.6, 9.0, a), (xe + 4.6, 11.8, bb), c("enseigne_blanc"), collide=False, name="Panneau")
                p.label = {"face": face, "text": txt, "color": BLEU_TEXTE, "font": "sans", "glow": 1.0}
            # --- étages : mur-rideau vitré (meneaux, traverses), baies éclairées, enseigne 駅, écrans ----
            yb, yh = 11.0, 33.0
            a, bb = zz(0, 0.12)
            b.box((x0 + 1.0, yb, a), (x1 - 1.0, yh, bb), c("vitre_bleue"), collide=False, name="MurRideau")
            # réservations (enseigne et écrans) : ni meneaux ni baies derrière
            resa = [(xm - 8.2, xm + 8.2, 14.0)] if principale else []
            if principale:
                resa += [(x0 + 11.0, x0 + 29.0, 18.4), (x1 - 29.0, x1 - 11.0, 18.4)]
            niveaux = [(yb, 18.5), (18.5, 26.0), (26.0, yh)]
            nm = 16 if principale else 4
            pas = (x1 - x0 - 2.0) / nm
            for i in range(nm + 1):
                x = x0 + 1.0 + i * pas
                y_haut = yh
                for r0, r1, yr in resa:
                    if r0 - 0.3 < x < r1 + 0.3:
                        y_haut = yr
                a, bb = zz(0.12, 0.45)
                b.box((x - 0.25, yb, a), (x + 0.25, y_haut, bb), c("metal_clair"), **PETIT, name="Meneau")
                if i == nm:
                    break
                # baies éclairées (Neon) : une sur trois environ, motif irrégulier mais reproductible
                for j, (y0_, y1_) in enumerate(niveaux):
                    xc = x + pas / 2
                    if any(r0 - 0.5 < xc < r1 + 0.5 and y1_ > yr for r0, r1, yr in resa):
                        continue
                    if (i * 5 + j * 3 + (0 if principale else 2)) % 7 in (0, 3):
                        a, bb = zz(0.12, 0.22)
                        col = "fenetre_froide" if (i + j) % 2 else "fenetre_chaude"
                        b.box((x + 0.25, y0_ + 0.3, a), (x + pas - 0.25, y1_ - 0.3, bb), c(col), name="Baie", **NEON)
            for y in (yb, 18.5, 26.0):
                a, bb = zz(0.12, 0.5)
                segs = [(x0 + 1.0, x1 - 1.0)]
                for r0, r1, yr in resa:
                    if y >= yr - 0.3:
                        segs = [(u, w) for (p0, p1) in segs for (u, w) in ((p0, min(p1, r0)), (max(p0, r1), p1)) if w - u > 0.5]
                for u, w in segs:
                    b.box((u, y - 0.3, a), (w, y + 0.3, bb), c("metal_clair"), **PETIT, name="Traverse")
            a, bb = zz(0, 0.35)
            b.box((x0 + 1.0, yh, a), (x1 - 1.0, yd - 0.4, bb), c("bleu_marine"), collide=False, name="Bandeau")
            a, bb = zz(0.35, 0.5)
            b.box((x0 + 1.0, yh + 0.3, a), (x1 - 1.0, yh + 0.7, bb), c("neon_cyan"), name="Neon", **NEON)
            if principale:
                # grand panneau 駅 au centre, deux écrans abstraits de part et d'autre
                a, bb = zz(0.12, 0.6)
                b.box((xm - 8.0, 14.0, a), (xm + 8.0, yh, bb), c("bleu_nuit"), collide=False, name="CadreEnseigne")
                a, bb = zz(0.6, 0.8)
                p = b.box((xm - 6.8, 16.2, a), (xm + 6.8, 31.0, bb), c("enseigne_blanc"), collide=False, name="Enseigne")
                p.label = {"face": face, "text": "駅", "color": BLEU_TEXTE, "font": "sans", "glow": 1.0}
                for (r0, r1, yr), (fond, aplat) in zip(resa[1:], (AFFICHES[0], AFFICHES[1])):
                    a, bb = zz(0.12, 0.6)
                    b.box((r0, yr, a), (r1, yh, bb), c("ecran_fond"), collide=False, name="Ecran")
                    a, bb = zz(0.6, 0.7)
                    b.box((r0 + 0.6, yr + 0.6, a), (r1 - 0.6, yh - 0.6, bb), c(fond), name="Aplat", **NEON)
                    a, bb = zz(0.7, 0.8)
                    b.box((r0 + 0.6, yr + 3.6, a), ((r0 + r1) / 2 + 2.0, yr + 9.0, bb), c(aplat), name="Aplat", **NEON)
        # enseigne verticale 駅 en drapeau au coin côté couloir (lisible depuis le parvis et depuis la rue)
        xe = x1
        with b.group("Enseigne"):
            for y in (15.0, 27.0):
                b.box((xe, y - 0.2, zb - 3.15), (xe + 0.6, y + 0.2, zb - 2.85), c("metal_fonce"), **PETIT, name="Patte")
            b.box((xe + 0.6, 13.8, zb - 3.6), (xe + 3.4, 28.2, zb - 2.4), c("neon_cyan"), name="Neon", **NEON)
            for sz in (-1, 1):
                a, bb = sorted((zb - 3.0 + sz * 0.6, zb - 3.0 + sz * 0.75))
                p = b.box((xe + 0.8, 14.2, a), (xe + 3.2, 27.8, bb), c("enseigne_blanc"), **PETIT, name="Enseigne")
                p.label = {"face": FACE_Z[sz], "text": "駅", "color": BLEU_TEXTE, "font": "sans", "vertical": True,
                           "glow": 1.0}


def _quais(b, x0, x1, pal, ys, yd, yc, za, zb) -> None:
    """Tablier élargi de la gare, quais latéraux à bande podotactile, abris de quai sur poteaux avec
    rampes lumineuses, panneaux 駅 suspendus, cages d'escalier, bancs et clôtures extérieures."""
    yq = ys + 2.2          # dessus des quais (= plancher du train)
    with b.group("Gare/Quais"):
        b.box((x0, yd, za + 0.5), (x1, yc, zb - 0.5), pal["poutre"], name="Poutre", **pal["mat"])
        b.box((x0, yc, za), (x1, ys, zb), pal["corniche"], studs="top", name="Corniche")
        for s, zf in ((-1, za + 0.5), (1, zb - 0.5)):
            b.box((x0, yd + 0.15, zf), (x1, yd + 0.5, zf + s * 0.15), pal["neon"], name="Neon", **NEON)
        quais = ((1, 6.2, zb - 0.5), (-1, -6.2, za + 0.5))
        for s, zi, ze in quais:
            a, bb = sorted((zi, ze))
            b.box((x0, ys, a), (x1, yq, bb), c("beton_clair"), studs="top", name="Quai")
            a2, bb2 = sorted((s * 6.7, s * 7.5))
            b.box((x0 + 1.0, yq, a2), (x1 - 1.0, yq + 0.1, bb2), c("guidage"), **PETIT, name="Podotactile")
            b.box((x0, yq - 0.5, zi), (x1, yq, zi - s * 0.1), c("marquage"), **PETIT, name="Bordure")
            # clôture extérieure : muret et vitrage
            a3, bb3 = sorted((ze, ze - s * 0.5))
            b.box((x0, yq, a3), (x1, yq + 1.2, bb3), c("beton"), studs="top", name="Muret")
            a4, bb4 = sorted((ze - s * 0.15, ze - s * 0.35))
            b.box((x0, yq + 1.2, a4), (x1, yq + 3.0, bb4), c("vitre_claire"), transparency=0.45, collide=False, name="Vitrage")
            # abri : poteaux sur l'axe du quai, toit à studs, bandeau côté voie, rampes de lumière
            zc = (zi + ze) / 2
            za_t, zb_t = sorted((zi + s * 0.2, ze + s * 0.2))
            yt = yq + 8.2
            for x in np.linspace(x0 + 8, x1 - 8, 6):
                b.box((x - 0.4, yq, zc - 0.4), (x + 0.4, yt, zc + 0.4), c("metal_clair"), name="Poteau")
            b.box((x0 + 4, yt, za_t), (x1 - 4, yt + 0.6, zb_t), c("metal_clair"), studs="top", name="Abri")
            a5, bb5 = sorted((zi + s * 0.2, zi + s * 0.5))
            b.box((x0 + 4, yt - 0.8, a5), (x1 - 4, yt, bb5), c("bleu_marine"), collide=False, name="Bandeau")
            for dz in (-1.9, 1.9):
                b.box((x0 + 6, yt - 0.3, zc + dz - 0.25), (x1 - 6, yt, zc + dz + 0.25), c("neon_blanc"), name="Rampe", **NEON)
            # panneau 駅 suspendu (deux faces) au milieu du quai
            xm = (x0 + x1) / 2 + s * 14
            b.box((xm - 0.15, yt - 1.8, zc - 0.15), (xm + 0.15, yt, zc + 0.15), c("metal_fonce"), **PETIT, name="Suspente")
            for sz in (-1, 1):
                a6, bb6 = sorted((zc, zc + sz * 0.15))
                p = b.box((xm - 3.6, yt - 3.6, a6), (xm + 3.6, yt - 1.8, bb6), c("enseigne_blanc"), **PETIT, name="PanneauQuai")
                p.label = {"face": FACE_Z[sz], "text": "駅", "color": BLEU_TEXTE, "font": "sans", "glow": 1.0}
            # cage d'escalier vers le hall, bancs, distributeur
            xs = (x0 + x1) / 2 - s * 12
            a7, bb7 = sorted((zc - 1.6, zc + 1.6))
            b.box((xs - 6, yq, a7), (xs + 6, yq + 1.2, bb7), c("metal_clair"), name="Escalier")
            b.box((xs - 5.6, yq + 1.2, a7 + 0.3), (xs + 5.6, yq + 1.3, bb7 - 0.3), c("vitre"), **PETIT, name="Tremie")
            poteaux = np.linspace(x0 + 8, x1 - 8, 6)
            for xb_ in ((poteaux[0] + poteaux[1]) / 2, (poteaux[-2] + poteaux[-1]) / 2):
                b.box((xb_ - 2, yq, zc - 0.6), (xb_ + 2, yq + 1.0, zc + 0.6), c("bleu_ardoise"), studs="top", name="Banc")
            xv = xs + 22 * s
            b.box((xv - 1.4, yq, ze - s * 1.7), (xv + 1.4, yq + 3.6, ze - s * 0.5), c("distrib_bleu"), name="Distributeur")
            a8, bb8 = sorted((ze - s * 1.7, ze - s * 1.8))
            b.box((xv - 1.1, yq + 1.6, a8), (xv + 1.1, yq + 3.2, bb8), c("fenetre_froide"), name="Vitrine", **NEON)


def _voies(b, x0, x1, ys, yr) -> None:
    """Deux voies : lit de ballast, traverses en longues bandes, deux rails par voie."""
    with b.group("Voies"):
        bornes = [x0] + [x for x in (-120.0, 0.0, 120.0) if x0 < x < x1] + [x1]
        for xa, xb in zip(bornes, bornes[1:]):
            for z in Z_VOIES:
                b.box((xa, ys, z - 1.9), (xb, ys + 0.45, z + 1.9), c("ballast"), studs="top", name="Ballast")
                b.box((xa, ys + 0.45, z - 1.35), (xb, yr - 0.3, z + 1.35), c("beton_fonce"), name="Traverses")
                for dz in (-ECART_RAIL, ECART_RAIL):
                    b.box((xa, yr - 0.3, z + dz - 0.14), (xb, yr, z + dz + 0.14), c("rail"), material="Metal", name="Rail")


def _catenaire(b, xs, x0, x1, yp, yf) -> None:
    """Portiques de caténaire (deux poteaux sur les parapets, traverse) et un fil par voie, accroché sous
    les traverses (fil de rayon 0,08 : le dessus du fil touche le dessous de la traverse)."""
    acier = c("metal_fonce")
    with b.group("Catenaire"):
        for x in xs:
            for s in (-1, 1):
                b.box((x - 0.35, yp, s * 7.5), (x + 0.35, yf + 1.6, s * 8.2), acier, name="Poteau")
            b.box((x - 0.3, yf + 0.08, -8.4), (x + 0.3, yf + 0.68, 8.4), acier, name="Traverse")
            b.box((x - 0.2, yf + 1.1, -8.4), (x + 0.2, yf + 1.4, 8.4), acier, collide=False, name="Traverse")
        bornes = [x0, -120.0, 0.0, 120.0, x1]
        for xa, xb in zip(bornes, bornes[1:]):
            for z in Z_VOIES:
                b.cyl(((xa + xb) / 2, yf, z), 0.08, xb - xa, c("cable"), axis="x", **PETIT, name="Fil")


def _consoles_gare(b, xs, yf, yq) -> None:
    """Dans la gare, les fils sont tenus par des consoles fixées aux poteaux des abris de quai."""
    with b.group("Catenaire"):
        for x in xs:
            for s, z in ((1, 3.5), (-1, -3.5)):
                a, bb = sorted((z - s * 0.2, s * 6.4))
                b.box((x - 0.15, yf + 0.08, a), (x + 0.15, yf + 0.38, bb), c("metal_fonce"), **PETIT, name="Console")


def viaduc_ferroviaire(b, variant: int = 0, longueur: float = 476, hauteur_libre: float = 36, niveau_rail: float = 42,
                       passage: float = 92, gare: bool = True) -> dict:
    """Viaduc d'entrée sur toute la largeur de la zone (voir l'en-tête du module).

    `passage` : largeur libre entre les piles du couloir (92 pour le couloir de 90 ; toutes les cotes en x
    en découlent, voir `geometrie_couloir`).
    variant : 0 béton clair et travée d'acier bleu, arches de brique, néon cyan ; 1 poutres d'acier partout,
    arches de béton, néon blanc ; 2 et 3 : mélanges (brique sombre, néons inversés)."""
    v = variant % 4
    pal = _pal_viaduc(v)
    geo = geometrie_couloir(passage)
    X = longueur / 2
    yd = float(hauteur_libre)        # dessous des poutres
    yr = float(niveau_rail)          # dessus des rails
    ys = yr - 1.0                    # dessus de la dalle
    yc = ys - 1.4                    # bas de la corniche
    yp = yr + 3.0                    # haut des parapets
    yf = yr + 8.65                   # fil de contact
    xt = geo["xt"]                   # extrémité de la travée d'acier (sur les piles du couloir)
    gx0, gx1 = geo["gare"]
    gare = bool(gare) and X > abs(gx0) + 12
    n0 = len(b.parts)

    # --- piles ------------------------------------------------------------------------------
    piles = [p for p in (80.0, 120.0, 160.0, 200.0) if geo["xa"] + 14 < p < X - 12] + [X - 2.5]
    for s in (-1, 1):
        _pile_couloir(b, s, pal, yd, "東口" if s < 0 else None, AFFICHES[3] if s > 0 else AFFICHES[1], geo)
        for p in piles:
            x = s * p
            if gare and gx0 - 2.5 < x < gx1 + 2.5:
                continue        # sous la gare, le hall porte le tablier
            _pile(b, x, pal, yd, w=5.0)

    # --- tablier -----------------------------------------------------------------------------
    bornes = sorted({-X, X, -xt, xt, *(s * p for s in (-1, 1) for p in piles[:-1])}
                    | ({gx0, gx1} if gare else set()))
    with b.group("Tablier"):
        for xa, xb in zip(bornes, bornes[1:]):
            if xb <= -xt + 1e-6 or xa >= xt - 1e-6:
                if gare and xa >= gx0 - 1e-6 and xb <= gx1 + 1e-6:
                    continue
                _tablier_beton(b, xa, xb, pal, yd, yc, ys, yp)
        _travee_acier(b, -xt, xt, pal, yd, ys, yp, "渋谷")
    _voies(b, -X, X, ys, yr)

    # --- gare ----------------------------------------------------------------------------------
    if gare:
        za, zb = GARE_Z
        _quais(b, gx0, gx1, pal, ys, yd, yc, za, zb)
        _hall_gare(b, gx0, gx1, za + 0.4, zb - 0.6, yd)
        _consoles_gare(b, np.linspace(gx0 + 8, gx1 - 8, 6)[1:5], yf, ys + 2.2)

    # --- caténaire -----------------------------------------------------------------------------
    mats = [xt + 1.0] + [p for p in piles[:-1]] + [X - 3.0]
    xs = sorted({s * m for s in (-1, 1) for m in mats if not (gare and gx0 - 2 < s * m < gx1 + 2)})
    _catenaire(b, xs, -X, X, yp, yf)

    # --- boutiques sous les voies --------------------------------------------------------------
    k = 0
    for s in (1, -1):
        # pilastre de 5 contre la pile du couloir (x ∈ s·[xo - 0,5 ; xa]), puis arches entre les piles
        if not (gare and s < 0):
            _pile(b, s * (geo["xa"] - 2.5), pal, yd, w=5.0)
        faces = [geo["xa"]] + [q for p in piles for q in (p - 2.5, p + 2.5)]
        travees = [(faces[i], faces[i + 1]) for i in range(0, len(faces) - 1, 2)]
        for a, bb in travees:
            xa, xb = sorted((s * a, s * bb))
            morceaux = [(xa, xb)]
            if gare:
                morceaux = [(u, w) for (u, w) in ((xa, min(xb, gx0)), (max(xa, gx1), xb)) if w - u > 1.0]
            for u, w in morceaux:
                k += _arches(b, u, w, pal, k, yd)
    # emprise en z : de -11,8 (arrière du hall) à 17,5 (bord de la marquise du hall, côté parvis) avec la gare
    return {"emprise": (longueur, round(GARE_Z[1] + 3.5 - GARE_Z[0], 1) if gare else 17.0), "hauteur": round(yf + 1.6, 1),
            "niveau_rail": yr, "pieces": len(b.parts) - n0}


# ===========================================================================
# 2. Train de banlieue
# ===========================================================================

LIVREES = [("train_bande", "train_bande_2"), ("train_bande_2", "train_bande"), ("neon_rose", "bleu_marine"),
           ("neon_jaune", "train_bande")]


def _pantographe(b, x: float, y0: float) -> None:
    """Pantographe en losange (quatre bras fins), socle isolant et archet."""
    with b.group("Pantographe"):
        b.box((x - 1.2, y0, -0.9), (x + 1.2, y0 + 0.25, 0.9), c("metal_fonce"), **PETIT, name="Socle")
        yb, yh = y0 + 0.25, y0 + 1.15
        ym = (yb + yh) / 2
        dx, dy = 1.0, (yh - yb) / 2
        L = math.hypot(dx, dy) + 0.1
        ang = math.degrees(math.atan2(dy, dx))
        for sx in (-1, 1):
            for sy in (-1, 1):
                cx, cy = x + sx * dx / 2, ym + sy * dy / 2
                b.part("block", (L, 0.12, 0.12), (cx, cy, 0.0), rot_z(sx * sy * -ang), c("metal"), **PETIT, name="Bras")
        b.box((x - 0.25, yh, -1.6), (x + 0.25, yh + 0.12, 1.6), c("metal"), **PETIT, name="Archet")


def _cabine(b, xe: float, sg: int, liv, tete: bool) -> None:
    """Face de cabine (en x = xe, tournée vers sg·X) : masque sombre, pare-brise, girouette, phares et feux."""
    def bx(d0, d1):
        return sorted((xe + sg * d0, xe + sg * d1))
    face = FACE_X[sg]
    with b.group("Cabine"):
        a, bb = bx(0, 0.2)
        b.box((a, 2.55, -2.65), (bb, 3.15, 2.65), c(liv[0]), **PETIT, name="Bande")
        a, bb = bx(0, 0.1)
        b.box((a, 3.3, -2.15), (bb, 6.5, 2.15), c("train_vitre"), **PETIT, name="Masque")
        a, bb = bx(0.1, 0.2)
        b.box((a, 3.55, -1.85), (bb, 5.55, 1.85), mix(c("train_vitre"), c("vitre_claire"), 0.35), **PETIT, name="PareBrise")
        p = b.box((a, 5.75, -1.1), (bb, 6.35, 1.1), c("enseigne_noir"), **PETIT, name="Girouette")
        p.label = {"face": face, "text": "駅", "color": (255, 154, 46), "font": "sans", "glow": 1.4}
        a, bb = bx(0, 0.25)
        for s in (-1, 1):
            za, zb = sorted((s * 1.25, s * 2.0))
            b.box((a, 1.6, za), (bb, 2.1, zb), c("neon_blanc") if tete else shade(c("neon_blanc"), 0.55),
                  name="Phare", **(NEON if tete else PETIT))
            za, zb = sorted((s * 0.45, s * 1.05))
            b.box((a, 1.6, za), (bb, 2.1, zb), c("neon_rouge") if not tete else shade(c("neon_rouge"), 0.45),
                  name="Feu", **(NEON if not tete else PETIT))
        a, bb = bx(-0.6, 0.5)
        b.box((a, 0.35, -1.9), (bb, 1.2, 1.9), c("metal_fonce"), **PETIT, name="Chasse")


def _voiture(b, x0: float, x1: float, liv, avant: bool, arriere: bool, panto: bool) -> None:
    """Une voiture de 20 studs : caisse inox, toit à bords en biseau, climatiseurs, bogies, bandeau de
    fenêtres et rampe lumineuse, quatre portes par face, bandes de livrée."""
    xc = (x0 + x1) / 2
    inox = c("train_inox")
    b.box((x0, 1.2, -2.3), (x1, 6.8, 2.3), inox, name="Caisse")
    b.box((x0 + 0.3, 6.8, -1.95), (x1 - 0.3, 7.3, 1.95), c("train_toit"), studs="top", name="Toit")
    for s in (-1, 1):
        b.wedge((x0 + 0.3, 6.8, s * 1.95), (x1 - 0.3, 7.15, s * 2.3), c("train_toit"), down="+z" if s > 0 else "-z",
                collide=False, name="Toit")
    for dx in (-5.5, 5.5):
        if panto and dx > 0:
            continue
        b.box((xc + dx - 1.6, 7.3, -1.2), (xc + dx + 1.6, 7.9, 1.2), c("clim"), studs="top", **PETIT, name="Clim")
    if panto:
        _pantographe(b, xc + 4.5, 7.3)
    # dessous : bogies, roues, coffres
    for dx in (-6.8, 6.8):
        b.box((xc + dx - 2.2, 0.45, -1.5), (xc + dx + 2.2, 1.2, 1.5), c("metal_fonce"), name="Bogie")
        for dw in (-1.2, 1.2):
            b.cyl((xc + dx + dw, 0.55, 0.0), 0.55, 3.2, c("pneu"), axis="z", **PETIT, name="Roue")
    b.box((xc - 4.0, 0.6, -1.9), (xc + 4.0, 1.2, 1.9), c("anthracite"), **PETIT, name="Coffres")
    # flancs
    ea = 1.4 if arriere else 0.8
    eb = 1.4 if avant else 0.8
    for s in (-1, 1):
        def zz(d0, d1):
            return sorted((s * (2.3 + d0), s * (2.3 + d1)))
        # profondeurs : vitres 0,1 < éclairage 0,2 < portes 0,25 < bandes de livrée 0,35 (continues sur les portes)
        a, bb = zz(0, 0.1)
        b.box((x0 + ea, 3.3, a), (x1 - eb, 5.6, bb), c("train_vitre"), **PETIT, name="Fenetres")
        a, bb = zz(0.1, 0.2)
        b.box((x0 + ea + 0.2, 5.05, a), (x1 - eb - 0.2, 5.45, bb), c("fenetre_froide"), name="Eclairage", **NEON)
        a, bb = zz(0, 0.25)
        for dx in (-7.5, -2.5, 2.5, 7.5):
            b.box((xc + dx - 0.9, 1.3, a), (xc + dx + 0.9, 6.3, bb), c("train_inox_fonce"), **PETIT, name="Porte")
        a, bb = zz(0, 0.35)
        b.box((x0, 2.55, a), (x1, 3.15, bb), c(liv[0]), **PETIT, name="Bande")
        b.box((x0, 2.15, a), (x1, 2.4, bb), c(liv[1]), **PETIT, name="Filet")
        b.box((x0 + ea, 5.75, a), (x1 - eb, 6.25, bb), c(liv[0]), **PETIT, name="Bandeau")


def train_banlieue(b, variant: int = 0, voitures: int = 4) -> dict:
    """Train de banlieue inox à livrée inventée, à l'arrêt en sortie de gare (voir l'en-tête du module).

    variant : 0 bande violette et filet cyan ; 1 bande cyan et filet violet ; 2 rose et bleu ; 3 jaune et violet."""
    n = max(1, int(voitures))
    liv = LIVREES[variant % len(LIVREES)]
    Lv, G = 20.0, 1.0
    total = n * Lv + (n - 1) * G
    x = -total / 2
    for i in range(n):
        x0, x1 = x, x + Lv
        with b.group(f"Voiture{i + 1}"):
            panto = (0 < i < n - 1) if n > 2 else (i == 0)
            _voiture(b, x0, x1, liv, avant=(i == n - 1), arriere=(i == 0), panto=panto)
            if i == n - 1:
                _cabine(b, x1, 1, liv, tete=True)
            if i == 0:
                _cabine(b, x0, -1, liv, tete=False)
            if i < n - 1:
                b.box((x1, 1.6, -1.4), (x1 + G, 6.2, 1.4), c("enseigne_noir"), collide=False, name="Soufflet")
        x += Lv + G
    return {"emprise": (round(total, 2), 4.6), "hauteur": 7.5}


# ===========================================================================
# 3. Passerelles piétonnes (hodōkyō)
# ===========================================================================

def _barre(b, z0, y0, z1, y1, xa, xb, ep_bas, ep_haut, col, name="Barre", **kw):
    """Bloc incliné dans le plan Y-Z, de x = xa à xb, le long de la droite (z0, y0) → (z1, y1) ;
    il s'étend de `ep_bas` sous la droite à `ep_haut` au-dessus (mesurés verticalement)."""
    dz, dy = z1 - z0, y1 - y0
    L = math.hypot(dz, dy)
    ang = math.degrees(math.atan2(dy, dz))         # pente (y monte quand z augmente si ang > 0)
    cosa = abs(dz) / L
    ep = (ep_bas + ep_haut) * cosa                  # épaisseur perpendiculaire à la pente
    off = (ep_haut - ep_bas) / 2                    # décalage vertical du centre
    cz, cy = (z0 + z1) / 2, (y0 + y1) / 2 + off
    # rot_x(-ang) envoie l'axe Z local sur (0, sin ang, cos ang) : le long de la pente
    return b.part("block", (xb - xa, ep, L), ((xa + xb) / 2, cy, cz), rot_x(-ang), col, name=name, **kw)


def _pal_passerelle(v: int) -> dict:
    if v % 2 == 0:
        return {"acier": c("acier_bleu"), "acier_fonce": c("acier_bleu_fonce"), "garde": c("rambarde"),
                "sol": c("trottoir_fonce"), "neon": c("neon_cyan") if v == 0 else c("neon_blanc"), "vitre": False}
    return {"acier": c("metal_clair"), "acier_fonce": c("metal"), "garde": c("metal_clair"),
            "sol": c("bleu_gris"), "neon": c("neon_blanc") if v == 1 else c("neon_cyan"), "vitre": True}


def _bande(b, xa, xb, d: int, p: float, q: float, yp: float, yq: float, h: float, col, name: str, **kw) -> None:
    """Bande inclinée à bouts verticaux dans le plan Y-Z (x de xa à xb), entre |z| = p (bout bas) et |z| = q
    (bout haut) : bord inférieur de yp à yq, hauteur verticale h. Chaque tronçon = coin + bloc + coin ; on
    coupe en tronçons qui montent de moins que h (sens d : +1 si |z| = z, -1 si |z| = -z)."""
    delta = yq - yp
    n = max(1, math.ceil(delta / (h * 0.95)))
    vers_q = "-z" if d > 0 else "+z"          # sens où |z| diminue (vers le haut de la volée)
    vers_p = "+z" if d > 0 else "-z"
    for i in range(n):
        pi = p - (p - q) * i / n
        qi = p - (p - q) * (i + 1) / n
        A, B = yp + delta * i / n, yp + delta * (i + 1) / n
        b.wedge_under((xa, A, d * pi), (xb, B, d * qi), col, down=vers_q, name=name, **kw)
        if A + h > B + 0.05:
            b.box((xa, B, d * pi), (xb, A + h, d * qi), col, name=name, **kw)
        b.wedge((xa, A + h, d * pi), (xb, B + h, d * qi), col, down=vers_p, name=name, **kw)


def _plein(b, xa, xb, d: int, p: float, q: float, yp: float, yq: float, col, name: str, **kw) -> None:
    """Flanc plein, du sol jusqu'à la droite (|z| = p, yp) → (|z| = q, yq) : bloc + coin."""
    b.box((xa, 0, d * p), (xb, yp, d * q), col, name=name, **kw)
    b.wedge((xa, yp, d * p), (xb, yq, d * q), col, down="+z" if d > 0 else "-z", name=name, **kw)


def _escalier(b, s: int, sens: str, pal, y1: float, XI: float, XE: float, D: float = 4.0, L: float = 46.0) -> None:
    """Escalier droit à palier le long du trottoir : x ∈ s·[XI ; XE], du tablier (|z| = D) au sol (|z| = L).
    20 contremarches de y1/20 et girons de 2 : volée basse pleine jusqu'au sol (9 marches), palier, volée
    haute (9 marches) portée par ses flancs. Flancs à bouts verticaux, mains courantes blanches."""
    d = 1 if sens == "+z" else -1
    xa, xb = sorted((s * XI, s * XE))
    xi0, xi1 = sorted((s * (XI + 0.6), s * (XE - 0.6)))
    n, g = 20, 2.0
    r = y1 / n
    pente = r / g
    zp0 = D + 9 * g              # début du palier (côté tablier)
    zp1 = L - 9 * g              # fin du palier (côté sol)
    yl = 10 * r                  # dessus du palier

    def nez_bas(za):             # ligne des nez de marche, volée basse
        return r + (L - za) * pente

    def nez_haut(za):            # ligne des nez de marche, volée haute
        return yl + r + (zp0 - za) * pente

    with b.group("Escaliers"):
        for k in range(1, 10):
            za, zb = sorted((d * (L - k * g), d * (L - (k - 1) * g)))
            b.box((xi0, 0, za), (xi1, k * r, zb), vary(pal["sol"], b.rng, 0.03), studs="top", name="Marche")
        for k in range(11, 20):
            za, zb = sorted((d * (zp0 - (k - 10) * g), d * (zp0 - (k - 11) * g)))
            b.box((xi0, (k - 1) * r - 0.4, za), (xi1, k * r, zb), vary(pal["sol"], b.rng, 0.03), studs="top", name="Marche")
        za, zb = sorted((d * zp0, d * zp1))
        b.box((xi0, yl - 1.2, za), (xi1, yl, zb), pal["sol"], studs="top", name="Palier")
        for x0, x1 in ((xa, xa + 0.6), (xb - 0.6, xb)):
            if pal["vitre"]:
                _plein(b, x0, x1, d, L, zp1, nez_bas(L) + 0.4, yl + 0.4, pal["acier"], "Limon")
                b.box((x0, yl - 1.6, za), (x1, yl + 0.4, zb), pal["acier"], name="Limon")
                _bande(b, x0, x1, d, zp0, D, nez_haut(zp0) - 4.0, y1 - 4.0, 4.4, pal["acier"], "Limon")
                vit = dict(transparency=0.4, collide=False)
                _barre(b, d * (L - 1.0), nez_bas(L - 1.0), d * (zp1 + 0.8), nez_bas(zp1 + 0.8), x0 + 0.2, x1 - 0.2,
                       -0.4, 3.1, c("vitre_claire"), name="Vitrage", **vit)
                b.box((x0 + 0.2, yl + 0.4, za), (x1 - 0.2, yl + 3.1, zb), c("vitre_claire"), name="Vitrage", **vit)
                _barre(b, d * (zp0 - 0.8), nez_haut(zp0 - 0.8), d * (D + 0.8), nez_haut(D + 0.8), x0 + 0.2, x1 - 0.2,
                       -0.4, 3.1, c("vitre_claire"), name="Vitrage", **vit)
            else:
                _plein(b, x0, x1, d, L, zp1, nez_bas(L) + 2.9, yl + 2.9, pal["acier"], "Flanc")
                b.box((x0, yl - 1.6, za), (x1, yl + 2.9, zb), pal["acier"], name="Flanc")
                _bande(b, x0, x1, d, zp0, D, nez_haut(zp0) - 4.0, y1 - 4.0, 6.9, pal["acier"], "Flanc")
            # mains courantes : volée basse, palier, volée haute
            mc = dict(collide=False, shadow=False)
            _barre(b, d * (L - 0.3), nez_bas(L - 0.3), d * zp1, yl, x0, x1, -2.9, 3.3, pal["garde"], name="MainCourante", **mc)
            b.box((x0, yl + 2.9, za), (x1, yl + 3.3, zb), pal["garde"], name="MainCourante", **mc)
            _barre(b, d * zp0, nez_haut(zp0), d * (D + 0.3), nez_haut(D + 0.3), x0, x1, -2.9, 3.3, pal["garde"],
                   name="MainCourante", **mc)
        # poteaux sous le palier
        zc = d * (zp0 + zp1) / 2
        for xx in (s * (XI + 0.6), s * (XE - 0.6)):
            b.box((xx - 0.5, 0, zc - 0.5), (xx + 0.5, yl - 1.2, zc + 0.5), pal["acier_fonce"], name="Poteau")


def passerelle_pietons(b, variant: int = 0, portee: float = 110, hauteur_libre: float = 34,
                       escaliers=("+z", "-z")) -> dict:
    """Passerelle piétonne au-dessus du couloir (voir l'en-tête du module).

    Tablier x ∈ [-X, X] avec X = portee/2 - 0,5, z ∈ [-4, 4], dessous à `hauteur_libre` ; tours d'appui et
    escaliers sur les trottoirs en x ∈ ±[X - 8 ; X] (couloir de 90 : portee 110 → ±[46,5 ; 54,5] ;
    ancien couloir : portee 84 → ±[33,5 ; 41,5]).
    Escalier gauche selon escaliers[0], droit selon escaliers[1] ('+z' : z ∈ [4, 46], '-z' : z ∈ [-46, -4]).
    variant : 0 acier bleu et panneau de direction ; 1 acier blanc, garde-corps vitrés et auvent."""
    v = variant % 4
    pal = _pal_passerelle(v)
    X = portee / 2 - 0.5
    XI = X - 8.0
    y0 = float(hauteur_libre)
    y1 = y0 + 1.6             # dessus du platelage
    D = 4.0
    # côtés ouverts (là où arrive un escalier)
    ouverts = {(s, 1 if sens == "+z" else -1) for s, sens in zip((-1, 1), escaliers)}
    top = y1 + 3.6
    with b.group("Tablier"):
        b.box((-X, y0, -D), (X, y1 - 0.4, D), pal["acier"], name="Poutre")
        b.box((-X, y1 - 0.4, -D + 0.3), (X, y1, D - 0.3), pal["sol"], studs="top", name="Platelage")
        for sz in (-1, 1):
            # étendue du côté fermé
            xa = -XI if (-1, sz) in ouverts else -X
            xb = XI if (1, sz) in ouverts else X
            ep = 0.5 if pal["vitre"] else 0.3
            za, zb = sorted((sz * D, sz * (D + ep)))
            if pal["vitre"]:
                b.box((-X, y0, za), (X, y1 + 0.3, zb), pal["acier"], name="Rive")
                b.box((xa, y1 + 0.3, sz * (D + 0.1)), (xb, y1 + 3.3, sz * (D + 0.3)), c("vitre_claire"), transparency=0.4,
                      collide=False, name="Vitrage")
                b.box((xa, y1 + 3.3, sz * (D - 0.05)), (xb, y1 + 3.6, sz * (D + 0.55)), pal["garde"], name="MainCourante")
            else:
                b.box((-X, y0, za), (X, y1 - 0.4, zb), pal["acier"], name="Rive")
                b.box((xa, y1 - 0.4, za), (xb, y1 + 2.0, zb), pal["acier"], name="Panneau")
                # raidisseurs verticaux (rythme de pont d'acier), pas derrière le panneau de direction
                a_, b_ = sorted((sz * (D + ep), sz * (D + ep + 0.15)))
                for x in np.arange(xa + 4.5, xb - 3.0, 9.0):
                    if abs(x) > 12.8:
                        b.box((x - 0.25, y0 + 0.6, a_), (x + 0.25, y1 + 2.0, b_), pal["acier_fonce"], **PETIT,
                              name="Raidisseur")
                b.box((xa, y1 + 2.0, sz * (D - 0.1)), (xb, y1 + 2.3, sz * (D + 0.4)), pal["garde"], studs="top", name="Lisse")
                for x in np.arange(xa + 3.0, xb - 2.0, 6.0):
                    b.box((x - 0.15, y1 + 2.3, sz * (D + 0.0)), (x + 0.15, y1 + 3.3, sz * (D + 0.3)), pal["garde"],
                          collide=False, name="Barreau")
                b.box((xa, y1 + 3.3, sz * (D - 0.05)), (xb, y1 + 3.6, sz * (D + 0.35)), pal["garde"], collide=False,
                      name="MainCourante")
            # néon le long de la rive
            za, zb = sorted((sz * (D + ep), sz * (D + ep + 0.15)))
            b.box((-X, y0 + 0.2, za), (X, y0 + 0.6, zb), pal["neon"], name="Neon", **NEON)
        # garde-corps des extrémités (au-dessus des tours)
        for s in (-1, 1):
            a, bb = sorted((s * X, s * (X - 0.4)))
            if pal["vitre"]:
                b.box((a, y1, -D), (bb, y1 + 3.3, D), c("vitre_claire"), transparency=0.4, collide=False, name="Vitrage")
            else:
                b.box((a, y1, -D), (bb, y1 + 2.0, D), pal["acier"], name="Panneau")
            b.box((a, y1 + 3.3, -D), (bb, y1 + 3.6, D), pal["garde"], collide=False, name="MainCourante")
        # panneaux de direction (variante acier bleu) sur les deux faces
        if not pal["vitre"]:
            for sz, txt in ((1, "駅 ←  → 東口"), (-1, "東口 ←  → 駅")):
                za, zb = sorted((sz * (D + 0.45), sz * (D + 0.55)))
                b.box((-12.4, y0 + 0.7, za), (12.4, y1 + 3.5, zb), c("blanc"), collide=False, name="Cadre")
                za, zb = sorted((sz * (D + 0.55), sz * (D + 0.7)))
                p = b.box((-12.0, y0 + 0.9, za), (12.0, y1 + 3.3, zb), c("auvent_bleu"), collide=False, name="Direction")
                p.label = {"face": FACE_Z[sz], "text": txt, "color": BLANC_TEXTE, "font": "sans"}
            # deux lampadaires sur le garde-corps
            for x, sz in ((-18.0, -1), (18.0, 1), (-(X - 14.0), 1), (X - 14.0, -1)):
                za, zb = sorted((sz * (D - 0.5), sz * (D - 0.1)))
                b.box((x - 0.2, y1, za), (x + 0.2, y1 + 6.0, zb), c("metal_fonce"), collide=False, name="Lampadaire")
                b.box((x - 0.8, y1 + 6.0, za - 0.4), (x + 0.8, y1 + 6.5, zb + 0.4), c("neon_blanc"), name="Lampe",
                      **NEON)
            top = y1 + 6.5
        else:
            # auvent léger sur poteaux
            yt = 44.0
            for sz in (-1, 1):
                za, zb = sorted((sz * D, sz * (D + 0.5)))
                for x in np.linspace(-X + 1.0, X - 1.0, 8):
                    b.box((x - 0.25, y1 + 0.3, za), (x + 0.25, yt, zb), pal["acier"], collide=False, name="Poteau")
                za, zb = sorted((sz * (D + 0.6), sz * (D + 0.9)))
                b.box((-X, yt - 0.3, za), (X, yt, zb), pal["neon"], name="Neon", **NEON)
            b.box((-X, yt, -D - 1.2), (X, yt + 0.6, D + 1.2), c("metal_clair"), studs="top", name="Auvent")
            b.box((-X, yt + 0.6, -0.8), (X, yt + 1.0, 0.8), c("metal"), studs="top", name="Faitage")
            top = yt + 1.0
    # piles d'appui aux extrémités (|x| ≥ 33,5) : portique de deux poteaux, chevêtre sous le tablier
    with b.group("Piles"):
        for s in (-1, 1):
            xm = s * (X - 4.0)
            for zz in (-2.6, 2.6):
                b.box((xm - 1.4, 0, zz - 1.3), (xm + 1.4, 0.5, zz + 1.3), c("beton_fonce"), studs="top", name="Socle")
                b.box((xm - 0.8, 0.5, zz - 0.8), (xm + 0.8, y0 - 1.6, zz + 0.8), pal["acier_fonce"], name="Poteau")
            b.box((xm - 0.5, 17.0, -1.8), (xm + 0.5, 18.2, 1.8), pal["acier"], name="Entretoise")
            xa, xb = sorted((s * XI, s * X))
            b.box((xa, y0 - 1.6, -D), (xb, y0, D), pal["acier"], name="Chevetre")
    for s, sens in zip((-1, 1), escaliers):
        _escalier(b, s, sens, pal, y1, XI, X, D=D)
    return {"emprise": (portee, 92), "hauteur": round(top, 1)}
