"""Repères du grand carrefour « scramble » (place des œufs) de la ville de nuit, style « stud ».

Fonctions publiques (chacune `f(b, variant=0, ...)` → {"emprise": (largeur, profondeur), "hauteur": h}) :
- tour_cylindrique(rayon=22, hauteur=76) : tour de mode cylindrique du coin nord-est (≈ 140 pièces, budget 330) ;
    socle en gradins à vitrines éclairées et entrée vers -Z, fût argenté à bandeaux vitrés (deux éclairés), trois
    grandes affiches lumineuses verticales sur l'arc avant (-30°, 0°, +30°), quatre rubans LED (±74°, ±146°),
    couronne lumineuse à nervures, aileron au néon sans texte (tourné de 40° vers -X : le couloir une fois posée)
    et noyau d'ascenseurs à l'arrière. Tout reste dans le cercle de rayon `rayon + 2` (coin serré).
    v0 blanc argenté, affiches magenta et cyan ; v1 bleu acier, affiches orange et jaune ;
    v2 carrelage blanc, affiches rose et bleu ; v3 bleu pâle, affiches jaune et magenta.
- immeuble_ecran(largeur=42, profondeur=44, hauteur=60, angle="gauche") : immeuble d'angle couvert d'écrans
    géants (≈ 160 pièces, budget 300) ; écran géant 30 × 24 sur la face du carrefour (-X local si
    angle="gauche", +X si "droite"), écran vertical 12 × 32 sur la façade avant contre l'angle, bandeau défilant
    qui tourne l'angle (映画), panneaux de toit en équerre, café 喫茶 vitré à l'angle et hall 映画 au
    rez-de-chaussée, corps sombre à rubans de fenêtres et ailettes, enseigne verticale カラオケ.
    v0 écrans magenta / rouge / orange ; v1 écrans cyan / bleu ; v2 corps marine, magenta / jaune ;
    v3 corps anthracite, cyan / orange.
- gare_facade(largeur=62, profondeur=26, hauteur=28) : gare à longue façade vitrée éclairée (≈ 145-200 pièces,
    budget 320) ; marquise à studs, grand 駅 lumineux, sous-enseigne 西口, petit tableau lumineux, tour de
    l'horloge à deux cadrans (carrefour et couloir), écran LED sur le toit, atrium vitré ; côté -X (le couloir) :
    aile basse avec la sortie 出口 et édicule de métro 駅.
    v0 (posée) : l'incident commence (quatre vitres brisées à lueur violette et éclats, fissure en diagonale,
    néons et bureaux en partie éteints, moitié de l'écran de toit en panne, gravats) ; v1 intacte (caisson
    lumineux sur le mur plein) ; v2 et v3 : mêmes états avec une autre teinte de façade.

Repère (voir CONVENTIONS.md) : origine au centre de l'emprise au sol, y = 0 au sol, l'AVANT regarde -Z.
Règle de ce module : RIEN ne sort de l'emprise (ni du cercle de la tour). Les façades qui portent des saillies
(écrans, bandeau défilant, marquises, enseignes) sont construites en retrait dans l'emprise. Ces assets se posent
donc tels quels contre le couloir élargi (|x| < 45, façades en |x| = 55) comme contre l'ancien (|x| < 32,
façades en 42) : il suffit que zone.py place l'emprise derrière la ligne des façades. Avec le couloir élargi :
tour en (81, 0, -330), yaw ≈ 49 (bord du cercle en x = 57) ; immeuble à écrans en (-77, 0, -333), yaw -90 ;
gare en (-86, 0, -459), yaw 180.

Uniquement des éléments de ville génériques : écrans et affiches aux compositions abstraites, mots autorisés
(喫茶, 映画, カラオケ, 駅, 西口, 出口), aucune marque, aucun nom de magasin, aucun chiffre ni logo sur la tour.
"""

from __future__ import annotations

import math

import numpy as np

from assets.mobilier import enseigne_verticale
from kit import hexrgb, mix, rot_x, rot_z, shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Petits outils
# ---------------------------------------------------------------------------

PETIT = dict(collide=False, shadow=False)
NEON = dict(material="Neon", collide=False, shadow=False)
VERRE = dict(material="Glass", transparency=0.6, collide=False, shadow=False)


def col(x):
    """Nom de palette, '#hex' ou tuple → tuple RGB."""
    if isinstance(x, tuple):
        return x
    if isinstance(x, str) and x.startswith("#"):
        return hexrgb(x)
    return c(x)


def vr(x, rng, amount=0.04):
    """`vary` qui accepte aussi les tuples."""
    return vary(col(x), rng, amount)


def _d(b, a, bb, couleur, **kw):
    """Petit détail : pas de collision ni d'ombre."""
    opts = dict(PETIT)
    opts.update(kw)
    return b.box(a, bb, col(couleur), **opts)


def _n(b, a, bb, couleur, **kw):
    """Néon (matériau Neon), sans collision ni ombre."""
    opts = dict(NEON)
    opts.update(kw)
    return b.box(a, bb, col(couleur), **opts)


def _lab(p, texte, couleur, fond=None, face="Front", glow=None, vertical=False):
    """Panneau texte (SurfaceGui) sur la pièce `p`."""
    p.label = {"face": face, "text": texte, "color": tuple(col(couleur)), "bg": tuple(col(fond)) if fond else None,
               "font": "sans", "vertical": vertical}
    if glow:
        p.label["glow"] = glow
    return p


def _haut(b, n0):
    """Haut des pièces ajoutées depuis la pièce n0 (la pose ne tourne qu'autour de Y : y monde = y local)."""
    top = 0.0
    for p in b.parts[n0:]:
        R = np.asarray(p.rot).reshape(3, 3)
        top = max(top, p.pos[1] + float(np.abs(R[1]) @ (np.asarray(p.size) / 2)))
    return float(round(top, 2))


def _cyl_y(b, r, y0, y1, couleur, **kw):
    """Cylindre vertical d'axe y = 0 entre y0 et y1."""
    return b.cyl((0, (y0 + y1) / 2, 0), r, y1 - y0, col(couleur), axis="y", **kw)


def _balise(b, x, y, z, s=0.8):
    """Feu rouge d'obstacle (Neon) sur un petit pied (2 pièces)."""
    _d(b, (x - 0.15, y, z - 0.15), (x + 0.15, y + 0.8, z + 0.15), "metal_fonce")
    _n(b, (x - s / 2, y + 0.8, z - s / 2), (x + s / 2, y + 0.8 + s, z + s / 2), "rouge_balise")


def _clim_toit(b, x, y, z, rot=False):
    """Climatiseur posé sur un toit, grille vers -Z (ou -X si rot) (2 pièces)."""
    if rot:
        _d(b, (x - 0.6, y, z - 1.1), (x + 0.6, y + 1.5, z + 1.1), "clim", shadow=True)
        b.cyl((x - 0.65, y + 0.75, z), 0.5, 0.12, c("metal_fonce"), axis="x", **PETIT)
    else:
        _d(b, (x - 1.1, y, z - 0.6), (x + 1.1, y + 1.5, z + 0.6), "clim", shadow=True)
        b.cyl((x, y + 0.75, z - 0.65), 0.5, 0.12, c("metal_fonce"), axis="z", **PETIT)


def _citerne(b, x, y, z, r=1.5, h=3.0):
    """Citerne d'eau sur son socle d'acier (3 pièces)."""
    b.box((x - r, y, z - r), (x + r, y + 0.8, z + r), c("metal_fonce"), studs="top", name="SocleCiterne")
    b.cyl((x, y + 0.8 + h / 2, z), r, h, c("citerne"), name="Citerne")
    b.cyl((x, y + 0.8 + h + 0.15, z), r * 0.6, 0.3, shade(c("citerne"), 0.85), **PETIT)


# ---------------------------------------------------------------------------
# Écrans et affiches : image abstraite en blocs Neon
# ---------------------------------------------------------------------------


def _disque(b, cx, cy, r, z0, z1, couleur):
    """Disque en pixels : trois rectangles croisés (octogone presque rond) entre les plans z0 et z1."""
    for (u, v) in ((1.0, 0.42), (0.82, 0.82), (0.42, 1.0)):
        _n(b, (cx - r * u, cy - r * v, z0), (cx + r * u, cy + r * v, z1), couleur, name="Disque")


def _image(b, x0, x1, y0, y1, z, style, couleurs, relief=0.25):
    """Image abstraite lumineuse dans le rectangle [x0, x1] × [y0, y1], posée devant le plan z (vers -z).
    Le fond dépasse de `relief`, les formes de `relief` encore. Styles : bandes, soleil, disque, barres,
    diagonale, vague, rayures, ville. Renvoie le nombre de pièces."""
    n0 = len(b.parts)
    W, H = x1 - x0, y1 - y0
    c1, c2, c3 = (list(couleurs) * 2)[:3]
    za, zb = z + 0.05, z - relief            # fond (ancré de 0,05 dans le support)
    zc = zb - relief                          # formes en relief
    e = 0.12                                  # les formes restent en retrait des bords du fond (pas de faces confondues)
    if style == "bandes":                     # dégradé en trois bandes horizontales et trait blanc
        for k, cc in enumerate((c1, c2, c3)):
            _n(b, (x0, y1 - (k + 1) * H / 3, zb), (x1, y1 - k * H / 3, za), cc, name="Image")
        _n(b, (x0 + W * 0.12, y0 + H * 0.3, zc), (x1 - W * 0.12, y0 + H * 0.34, zb + 0.05), "neon_blanc", name="Trait")
    elif style == "soleil":                   # ciel en deux bandes, grand soleil en pixels, horizon, silhouette de ville
        _n(b, (x0, y0 + H * 0.45, zb), (x1, y1, za), c1, name="Image")
        _n(b, (x0, y0, zb), (x1, y0 + H * 0.45, za), c2, name="Image")
        r = min(W, H) * 0.27
        cx, cy = x0 + W * 0.6, y0 + H * 0.5
        _disque(b, cx, cy, r, zc, zb + 0.05, "neon_jaune")
        _n(b, (x0 + e, y0 + H * 0.24, zc - 0.1), (x1 - e, y0 + H * 0.28, zb + 0.05), "neon_blanc", name="Horizon")
        for k, (u, w, h) in enumerate(((0.04, 0.16, 0.36), (0.22, 0.1, 0.22), (0.7, 0.13, 0.3), (0.86, 0.1, 0.18))):
            _n(b, (x0 + W * u, y0 + e, zc - 0.15), (x0 + W * (u + w), y0 + H * h, zb + 0.05), c3, name="Silhouette")
    elif style == "disque":                   # fond uni, grand disque en pixels, bande basse
        _n(b, (x0, y0, zb), (x1, y1, za), c1, name="Image")
        cx, cy = x0 + W * 0.5, y0 + H * 0.6
        r = min(W * 0.4, y1 - cy - e, cy - y0 - H * 0.24)
        _disque(b, cx, cy, r, zc, zb + 0.05, c2)
        _n(b, (x0 + e, y0 + H * 0.08, zc), (x1 - e, y0 + H * 0.2, zb + 0.05), c3, name="Bande")
    elif style == "barres":                   # fond, grande barre verticale, carré et trait
        _n(b, (x0, y0, zb), (x1, y1, za), c1, name="Image")
        _n(b, (x0 + W * 0.12, y0 + H * 0.1, zc), (x0 + W * 0.42, y1 - H * 0.08, zb + 0.05), c2, name="Barre")
        _n(b, (x0 + W * 0.55, y1 - H * 0.36, zc), (x1 - W * 0.1, y1 - H * 0.12, zb + 0.05), c3, name="Carre")
        _n(b, (x0 + W * 0.55, y0 + H * 0.12, zc), (x1 - W * 0.1, y0 + H * 0.16, zb + 0.05), "neon_blanc", name="Trait")
    elif style == "diagonale":                # fond et marches en diagonale
        _n(b, (x0, y0, zb), (x1, y1, za), c1, name="Image")
        for k in range(3):
            _n(b, (x0 + W * (0.08 + 0.26 * k), y0 + H * (0.1 + 0.27 * k), zc),
               (x0 + W * (0.4 + 0.26 * k), y0 + H * (0.34 + 0.27 * k), zb + 0.05), (c2, c3)[k % 2], name="Marche")
    elif style == "vague":                    # fond en deux tons, grand chevron en escalier (zigzag)
        _n(b, (x0, y0 + H * 0.5, zb), (x1, y1, za), c1, name="Image")
        _n(b, (x0, y0, zb), (x1, y0 + H * 0.5, za), c2, name="Image")
        for k in range(5):
            u = (0.08, 0.32, 0.56, 0.32, 0.08)[k]
            _n(b, (x0 + W * u, y0 + H * (0.1 + 0.16 * k), zc), (x0 + W * (u + 0.36), y0 + H * (0.24 + 0.16 * k), zb + 0.05),
               c3 if k % 2 == 0 else "neon_blanc", name="Chevron")
    elif style == "rayures":                  # rayures verticales alternées et bandeau
        nb = 5
        for k in range(nb):
            _n(b, (x0 + k * W / nb, y0, zb), (x0 + (k + 1) * W / nb, y1, za), (c1, c2)[k % 2], name="Image")
        _n(b, (x0 + W * 0.08, y0 + H * 0.4, zc), (x1 - W * 0.08, y0 + H * 0.6, zb + 0.05), c3, name="Bandeau")
    elif style == "affiche":                  # dégradé en trois bandes, grand disque clair, trait sombre
        for k, (a_, b_) in enumerate(((0.62, 1.0), (0.34, 0.62), (0.0, 0.34))):
            _n(b, (x0, y0 + H * a_, zb), (x1, y0 + H * b_, za), (c1, c2, c3)[k], name="Image")
        r = min(W * 0.36, H * 0.2)
        _disque(b, x0 + W * 0.5, y0 + H * 0.66, r, zc, zb + 0.05, "neon_blanc")
        _n(b, (x0 + W * 0.15, y0 + H * 0.2, zc), (x1 - W * 0.15, y0 + H * 0.24, zb + 0.05), "ecran_fond", name="Trait")
        _n(b, (x0 + W * 0.3, y0 + H * 0.1, zc), (x1 - W * 0.3, y0 + H * 0.13, zb + 0.05), "neon_blanc", name="Trait")
    else:                                     # « ville » : ciel en dégradé et tours en silhouette
        _n(b, (x0, y0 + H * 0.5, zb), (x1, y1, za), c1, name="Image")
        _n(b, (x0, y0, zb), (x1, y0 + H * 0.5, za), c2, name="Image")
        for k, (u, w, h) in enumerate(((0.05, 0.14, 0.62), (0.22, 0.2, 0.42), (0.47, 0.12, 0.78), (0.64, 0.18, 0.5),
                                       (0.85, 0.11, 0.34))):
            _n(b, (x0 + W * u, y0 + e, zc), (x0 + W * (u + w), y0 + H * h, zb + 0.05), c3, name="Tour")
    return len(b.parts) - n0


def _ecran(b, x0, x1, y0, y1, z, style, couleurs, cadre=0.8, ep=0.8):
    """Écran géant : cadre `ecran_fond` (face arrière sur le plan z, épaisseur ep vers -z) et image abstraite.
    Renvoie le plan avant du cadre."""
    _d(b, (x0, y0, z - ep), (x1, y1, z), "ecran_fond", shadow=True, name="CadreEcran")
    _image(b, x0 + cadre, x1 - cadre, y0 + cadre, y1 - cadre, z - ep, style, couleurs, relief=0.2)
    return z - ep


# ---------------------------------------------------------------------------
# 1) Tour de mode cylindrique
# ---------------------------------------------------------------------------

TOURS = [
    # v0 : blanc argenté, affiches magenta et cyan (variante posée)
    dict(corps="beton_clair", socle="metal_clair", corniche="metal_clair", bandes=("vitre_bleue", "vitre"),
         neon_socle="neon_magenta", couronne=mix(c("neon_blanc"), c("neon_cyan"), 0.18), liseré="neon_cyan",
         nervure="metal_clair", annexe="beton_fonce",
         affiches=(("bandes", ("neon_magenta", "neon_rose", "neon_orange")),
                   ("diagonale", ("neon_cyan", "neon_blanc", "ecran_bleu")),
                   ("barres", ("neon_magenta", "neon_cyan", "neon_jaune"))),
         rubans=("neon_cyan", "neon_bleu", "neon_magenta", "neon_rose"), aileron=("neon_magenta", "neon_blanc")),
    # v1 : bleu acier, affiches orange et jaune
    dict(corps="bleu_acier", socle="bleu_pale", corniche="beton_clair", bandes=("vitre_claire", "vitre"),
         neon_socle="neon_orange", couronne=mix(c("neon_blanc"), c("neon_jaune"), 0.2), liseré="neon_orange",
         nervure="bleu_pale", annexe="bleu_marine",
         affiches=(("diagonale", ("neon_orange", "neon_jaune", "neon_blanc")),
                   ("disque", ("neon_jaune", "neon_orange", "ecran_bleu")),
                   ("vague", ("neon_orange", "neon_rouge", "neon_jaune"))),
         rubans=("neon_jaune", "neon_orange", "neon_rouge", "neon_rose"), aileron=("neon_orange", "neon_jaune")),
    # v2 : carrelage blanc, affiches rose et bleu
    dict(corps="carrelage", socle="beton", corniche="metal_clair", bandes=("vitre", "vitre_bleue"),
         neon_socle="neon_rose", couronne=mix(c("neon_blanc"), c("neon_rose"), 0.15), liseré="neon_bleu",
         nervure="beton", annexe="anthracite",
         affiches=(("rayures", ("neon_rose", "ecran_bleu", "neon_blanc")),
                   ("bandes", ("neon_bleu", "neon_cyan", "neon_rose")),
                   ("diagonale", ("neon_rose", "neon_blanc", "neon_bleu"))),
         rubans=("neon_rose", "neon_magenta", "neon_bleu", "neon_cyan"), aileron=("neon_bleu", "neon_rose")),
    # v3 : bleu pâle, affiches jaune et magenta
    dict(corps="bleu_pale", socle="beton_clair", corniche="beton_clair", bandes=("vitre_bleue", "vitre"),
         neon_socle="neon_jaune", couronne=mix(c("neon_blanc"), c("neon_cyan"), 0.1), liseré="neon_magenta",
         nervure="beton_clair", annexe="bleu_ardoise",
         affiches=(("barres", ("neon_jaune", "neon_magenta", "neon_blanc")),
                   ("bandes", ("neon_magenta", "neon_orange", "neon_jaune")),
                   ("disque", ("neon_magenta", "neon_jaune", "neon_cyan"))),
         rubans=("neon_jaune", "neon_magenta", "neon_cyan", "neon_bleu"), aileron=("neon_jaune", "neon_magenta")),
]


def tour_cylindrique(b, variant=0, rayon=22, hauteur=76):
    """Tour de mode cylindrique (générique : ni nom, ni chiffre, ni logo). L'avant (-Z) regarde le centre du
    carrefour. Tout tient dans le cercle de rayon `rayon + 2`."""
    rng = b.rng
    n0 = len(b.parts)
    st = TOURS[variant % len(TOURS)]
    R, H = float(rayon), float(hauteur)
    RM = R + 2.0                 # limite absolue du coin
    y_soc = 10.2                 # haut de la corniche du socle
    y_cou = H - 10.0             # bas de la couronne lumineuse

    # --- socle en gradins : emmarchement, vitrines éclairées, corniche ---
    with b.group("Socle"):
        _cyl_y(b, RM - 0.2, 0.0, 0.6, "beton_fonce", studs="top", name="Emmarchement")
        _cyl_y(b, R + 0.8, 0.5, 9.1, vr(st["socle"], rng), name="Socle")
        _cyl_y(b, R + 1.0, 1.0, 8.0, "fenetre_chaude", material="Neon", name="Vitrines")
        _cyl_y(b, R + 1.25, 8.3, 8.85, st["neon_socle"], material="Neon", name="Liseré")
        _cyl_y(b, RM - 0.1, 9.0, y_soc, st["corniche"], studs="top", name="Corniche")
        # meneaux des vitrines sur l'arc avant (l'entrée est en 0°)
        for th in range(-120, 121, 12):
            if abs(th) < 10:
                continue
            with b.at((0, 0, 0), yaw=th):
                _d(b, (-0.25, 1.0, -(R + 1.4)), (0.25, 8.0, -(R + 0.85)), "metal_fonce", name="Meneau")
        # entrée principale (vers le carrefour) : portes sombres, piédroits, linteau, bandeau lumineux
        _d(b, (-3.0, 0.6, -(R + 1.4)), (3.0, 7.2, -(R + 0.9)), "vitre", shadow=True, name="Portes")
        _d(b, (-0.15, 0.7, -(R + 1.5)), (0.15, 7.1, -(R + 1.35)), "metal_clair", name="Battant")
        for s in (-1, 1):
            _d(b, (s * 3.0, 0.6, -(R + 1.6)), (s * 3.7, 8.2, -(R + 0.85)), st["corniche"], shadow=True, name="Piedroit")
        _d(b, (-3.7, 7.2, -(R + 1.6)), (3.7, 8.2, -(R + 0.85)), st["corniche"], shadow=True, name="Linteau")
        _n(b, (-2.8, 7.4, -(R + 1.75)), (2.8, 8.0, -(R + 1.55)), "neon_blanc", name="BandeauEntree")

    # --- fût argenté et bandeaux vitrés ---
    with b.group("Fut"):
        _cyl_y(b, R, y_soc - 0.2, y_cou + 0.2, vr(st["corps"], rng, 0.02), name="Fut")
        k = 0
        y = 14.0
        while y + 1.2 < y_cou - 1.0:
            neon = k in (1, 4)
            couleur = "fenetre_froide" if neon else st["bandes"][k % 2]
            _cyl_y(b, R + 0.2, y - 1.2, y + 1.2, couleur, material="Neon" if neon else "SmoothPlastic", name="Bandeau")
            y += 8.0
            k += 1

    # --- trois grandes affiches verticales sur l'arc avant ---
    with b.group("Affiches"):
        y0, y1 = 15.0, min(52.0, y_cou - 4.0)
        for th, (style, couleurs) in zip((-30, 0, 30), st["affiches"]):
            with b.at((0, 0, 0), yaw=th):
                zi, zo = -(R - 0.7), -(R + 0.8)          # face intérieure ancrée dans le fût, face avant
                _d(b, (-5.2, y0, zo), (5.2, y1, zi), "ecran_fond", shadow=True, name="Caisson")
                _image(b, -4.6, 4.6, y0 + 0.6, y1 - 0.6, zo, style, couleurs, relief=0.22)
                for yy in (y1, y0 - 0.35):              # rampes lumineuses haut et bas
                    _n(b, (-5.0, yy, zo - 0.1), (5.0, yy + 0.35, zi - 1.0), "neon_blanc", name="Rampe")
        # rubans LED étroits de part et d'autre (visibles depuis la rue et depuis la rue transversale)
        for th in (-74, 74, -146, 146):
            with b.at((0, 0, 0), yaw=th):
                zi, zo = -(R - 0.4), -(R + 0.6)
                _d(b, (-2.6, 13.0, zo), (2.6, y_cou - 2.0, zi), "ecran_fond", shadow=True, name="CaissonRuban")
                hh = (y_cou - 2.0 - 13.6 - 0.6) / 4
                for i, cc in enumerate(st["rubans"]):
                    ya = 13.6 + i * hh
                    _n(b, (-2.0, ya, zo - 0.25), (2.0, ya + hh - 0.3, zo + 0.05), cc, name="Ruban")

    # --- couronne lumineuse à nervures, toit ---
    with b.group("Couronne"):
        _cyl_y(b, R + 1.0, y_cou - 0.6, y_cou + 0.4, st["corniche"], studs="top", name="CorniCouronne")
        _cyl_y(b, R + 0.5, y_cou + 0.3, H - 0.7, st["couronne"], material="Neon", name="Couronne")
        for yy in (y_cou + 1.2, H - 2.0):
            _cyl_y(b, R + 0.75, yy, yy + 0.45, st["liseré"], material="Neon", name="Liseré")
        for th in range(0, 360, 20):
            with b.at((0, 0, 0), yaw=th):
                _d(b, (-0.4, y_cou + 0.4, -(R + 1.1)), (0.4, H - 0.8, -(R + 0.3)), st["nervure"], shadow=True, name="Nervure")
        _cyl_y(b, R + 0.9, H - 0.8, H, st["corniche"], studs="top", name="Toit")

    # --- aileron au néon (sans texte), tourné vers le couloir et le carrefour ---
    with b.group("Aileron"):
        with b.at((0, 0, 0), yaw=40):
            zf = -(R - 6.4)                                   # face avant de l'aileron
            hf, lf = 22.0, 3.8                                # hauteur, demi-largeur
            b.box((-lf, H, zf), (lf, H + hf, zf + 1.2), col(st["nervure"]), name="Aileron")
            ca, cb = st["aileron"]
            for zz, nom in ((zf - 0.2, "Image"), (zf + 1.15, "ImageDos")):
                z0, z1 = (zz, zf + 0.05) if nom == "Image" else (zf + 1.15, zf + 1.4)
                _n(b, (-lf + 0.6, H + 1.0, z0), (lf - 0.6, H + hf * 0.42, z1), ca, name=nom)
                _n(b, (-lf + 0.6, H + hf * 0.42, z0), (lf - 0.6, H + hf * 0.62, z1), "neon_blanc", name=nom)
                _n(b, (-lf + 0.6, H + hf * 0.62, z0), (lf - 0.6, H + hf - 1.0, z1), cb, name=nom)
            for s in (-1, 1):
                _n(b, (s * lf, H, zf - 0.1), (s * (lf + 0.3), H + hf, zf + 1.3), st["liseré"], name="Arete")
            b.box((-lf - 0.5, H + hf, zf - 0.3), (lf + 0.5, H + hf + 0.6, zf + 1.5), col(st["corniche"]), studs="top",
                  name="Chapeau")
            b.box((-0.6, H, zf + 1.2), (0.6, H + hf * 0.7, zf + 2.4), c("metal_fonce"), name="Raidisseur")
            for s in (-1, 1):
                b.wedge((s * 2.6 - 0.3, H, zf + 1.2), (s * 2.6 + 0.3, H + 8.0, zf + 6.0), c("metal_fonce"), down="+z",
                        name="Jambe")
            _balise(b, 0.0, H + hf + 0.6, zf + 0.6, s=0.7)

    # --- toit : local technique, climatiseurs, citerne, feux d'obstacle ---
    with b.group("Toit"):
        b.box((-4.0, H, R - 14.0), (4.0, H + 3.5, R - 9.0), col(st["annexe"]), studs="top", name="LocalTech")
        _clim_toit(b, 9.0, H, 9.0)
        _clim_toit(b, 11.5, H, 5.0, rot=True)
        _clim_toit(b, -9.5, H, 10.5)
        _citerne(b, 8.0, H, -2.0)
        for th in (125, -125):
            with b.at((0, 0, 0), yaw=th):
                _balise(b, 0.0, H, -(R - 0.6))

    # --- noyau d'ascenseurs à l'arrière (+Z), dans le cercle ---
    with b.group("Noyau"):
        za, zb = R - 7.5, R + 1.2
        b.box((-5.5, 0, za), (5.5, H + 4.0, zb), vr(st["annexe"], rng), studs="top", name="Noyau")
        _n(b, (-1.2, 12.0, zb), (1.2, H - 2.0, zb + 0.15), "fenetre_froide", name="FenteLumineuse")
        _d(b, (-1.0, H, za - 0.15), (1.0, H + 2.6, za), "vitre", name="PorteToit")
        _balise(b, 3.5, H + 4.0, zb - 1.5)
    return {"emprise": (2 * RM, 2 * RM), "hauteur": _haut(b, n0)}


# ---------------------------------------------------------------------------
# 2) Immeuble d'angle à écrans géants
# ---------------------------------------------------------------------------

ECRANS = [
    # v0 : écrans magenta / orange (variante posée)
    dict(corps="bleu_nuit", ailette="bleu_ardoise", vitre="vitre_bleue", acrotere="bleu_marine", auvent="bordeaux",
         cafe="enseigne_noir", liseré="neon_cyan",
         geant=("soleil", ("neon_magenta", "neon_rouge", "ecran_fond")),
         vertical=("diagonale", ("neon_magenta", "neon_orange", "neon_jaune")),
         toit_a=("bandes", ("neon_orange", "neon_rose", "neon_magenta")),
         toit_b=("barres", ("ecran_bleu", "neon_magenta", "neon_jaune")),
         defilant=("neon_magenta", "neon_jaune", "neon_cyan", "neon_orange")),
    # v1 : écrans cyan / bleu
    dict(corps="anthracite", ailette="bleu_marine", vitre="vitre_bleue", acrotere="bleu_nuit", auvent="noren_bleu",
         cafe="enseigne_noir", liseré="neon_magenta",
         geant=("soleil", ("ecran_bleu", "neon_cyan", "ecran_fond")),
         vertical=("rayures", ("neon_bleu", "neon_cyan", "neon_blanc")),
         toit_a=("bandes", ("neon_cyan", "neon_bleu", "neon_blanc")),
         toit_b=("disque", ("ecran_bleu", "neon_cyan", "neon_blanc")),
         defilant=("neon_cyan", "neon_blanc", "neon_bleu", "neon_jaune")),
    # v2 : corps marine, écrans magenta / jaune
    dict(corps="bleu_marine", ailette="bleu_acier", vitre="vitre", acrotere="bleu_nuit", auvent="auvent_rouge",
         cafe="enseigne_noir", liseré="neon_jaune",
         geant=("ville", ("neon_magenta", "neon_rose", "ecran_fond")),
         vertical=("diagonale", ("ecran_bleu", "neon_jaune", "neon_magenta")),
         toit_a=("rayures", ("neon_jaune", "neon_magenta", "neon_blanc")),
         toit_b=("bandes", ("neon_rose", "neon_orange", "neon_jaune")),
         defilant=("neon_jaune", "neon_magenta", "neon_blanc", "neon_rose")),
    # v3 : corps anthracite, écrans cyan / orange
    dict(corps="anthracite", ailette="bleu_ardoise", vitre="vitre_bleue", acrotere="bleu_marine", auvent="auvent_bleu",
         cafe="enseigne_noir", liseré="neon_orange",
         geant=("ville", ("ecran_bleu", "neon_cyan", "ecran_fond")),
         vertical=("barres", ("neon_cyan", "neon_orange", "neon_blanc")),
         toit_a=("disque", ("neon_orange", "neon_jaune", "neon_cyan")),
         toit_b=("vague", ("neon_cyan", "neon_bleu", "neon_orange")),
         defilant=("neon_orange", "neon_cyan", "neon_blanc", "neon_jaune")),
]


def immeuble_ecran(b, variant=0, largeur=42, profondeur=44, hauteur=60, angle="gauche"):
    """Immeuble d'angle du carrefour couvert d'écrans géants. L'avant (-Z) longe le couloir ; la face des écrans
    (-X si angle="gauche", +X si "droite") regarde le carrefour. Les deux façades sur rue sont en retrait de
    2,5 dans l'emprise : écrans, bandeau défilant, marquise et enseignes restent dans l'emprise."""
    rng = b.rng
    n0 = len(b.parts)
    st = ECRANS[variant % len(ECRANS)]
    m = 1.0 if angle == "gauche" else -1.0
    hw, hd, H = largeur / 2, profondeur / 2, float(hauteur)
    RET = 2.5
    xg, xd = -hw + RET, hw - 0.3            # face du carrefour (en retrait), face opposée
    zf, zb = -hd + RET, hd - 0.3            # façade sur le couloir (en retrait), arrière
    yT = H - 1.5                             # dessus du toit (acrotère jusqu'à H)

    def X(x):
        return m * x

    def F(face):
        return {"Left": "Right", "Right": "Left"}.get(face, face) if m < 0 else face

    def box(a, bb, couleur, **kw):
        return b.box((X(a[0]), a[1], a[2]), (X(bb[0]), bb[1], bb[2]), col(couleur), **kw)

    def dbox(a, bb, couleur, **kw):
        opts = dict(PETIT)
        opts.update(kw)
        return box(a, bb, couleur, **opts)

    def nbox(a, bb, couleur, **kw):
        opts = dict(NEON)
        opts.update(kw)
        return box(a, bb, couleur, **opts)

    yaw_cote = 90.0 * m                       # repère d'un écran posé sur la face du carrefour
    LX, LZ = xd - xg, zb - zf                 # longueurs utiles des deux façades sur rue
    xcafe = min(2.0, xg + 0.52 * LX)          # fin du café vers +X (le hall prend la suite)
    zcafe = zf + min(22.0, 0.55 * LZ)         # fin du café sur la face du carrefour

    # --- volume principal ---
    with b.group("Corps"):
        box((xg, 0, zf), (xd, yT, zb), vr(st["corps"], rng, 0.03), studs="top", name="Corps")
        # acrotère (studs) et liseré lumineux sous l'acrotère
        a = st["acrotere"]
        box((xg - 0.15, yT, zf - 0.15), (xd + 0.1, H, zf + 0.6), a, studs="top", name="Acrotere")
        box((xg - 0.15, yT, zb - 0.6), (xd + 0.1, H, zb + 0.1), a, studs="top", name="Acrotere")
        box((xg - 0.15, yT, zf + 0.6), (xg + 0.6, H, zb - 0.6), a, studs="top", name="Acrotere")
        box((xd - 0.6, yT, zf + 0.6), (xd + 0.1, H, zb - 0.6), a, studs="top", name="Acrotere")
        nbox((xg - 0.2, yT - 1.3, zf - 0.2), (xd + 0.12, yT - 0.9, zb + 0.12), st["liseré"], name="Liseré")
        # arête lumineuse verticale à l'angle des deux façades sur rue
        nbox((xg - 0.35, 12.4, zf - 0.35), (xg + 0.35, yT - 1.6, zf + 0.35), st["liseré"], name="Arete")

    # --- rubans de fenêtres (bandes traversantes) et fenêtres éclairées ---
    with b.group("Fenetres"):
        k = 0
        y0 = 12.8
        while y0 + 4.0 < yT - 1.5:
            y1 = y0 + 4.0
            box((xg - 0.12, y0, zf + 0.6), (xd + 0.12, y1, zb - 0.6), vr(st["vitre"], rng, 0.03), name="Ruban")
            box((xg + 0.6, y0, zf - 0.12), (xd - 0.6, y1, zb + 0.12), vr(st["vitre"], rng, 0.03), name="Ruban")
            # quelques bureaux éclairés : façade avant (hors écran), face opposée, face du carrefour au-dessus de l'écran
            lum = "fenetre_froide" if k % 3 else "fenetre_chaude"
            xa = float(rng.uniform(-3.0, 8.0))
            nbox((xa, y0 + 0.4, zf - 0.27), (xa + float(rng.uniform(4, 9)), y1 - 0.4, zf - 0.1), lum, name="Lumiere")
            za = float(rng.uniform(zf + 2, zb - 12))
            nbox((xd + 0.1, y0 + 0.4, za), (xd + 0.25, y1 - 0.4, za + float(rng.uniform(4, 10))), lum, name="Lumiere")
            if y0 > 43:
                za = float(rng.uniform(zf + 4, zf + 18))
                nbox((xg - 0.27, y0 + 0.4, za), (xg - 0.1, y1 - 0.4, za + 6), lum, name="Lumiere")
            y0 += 8.0
            k += 1
        # ailettes verticales (façade avant hors écran, face opposée, fin de la face du carrefour)
        ailettes = list(np.arange(xg + 14.9, xd - 1.0, 4.4))
        for x in ailettes:
            box((x - 0.3, 12.4, zf - 0.45), (x + 0.3, yT - 1.6, zf), st["ailette"], name="Ailette")
        for z in np.arange(zf + 2.0, zb - 1.0, 4.6):
            box((xd, 9.0, z - 0.3), (xd + 0.3, yT - 1.6, z + 0.3), st["ailette"], name="Ailette")
        for z in (zf + 33.0, zf + 37.5):
            if z < zb - 1.0:
                box((xg - 0.45, 9.0, z - 0.3), (xg, yT - 1.6, z + 0.3), st["ailette"], name="Ailette")

    # --- écrans géants ---
    with b.group("Ecrans"):
        # écran géant sur la face du carrefour (~30 × 24, y 18-42)
        sw = min(30.0, (zb - zf) - 6.0)
        style, couleurs = st["geant"]
        with b.at((X(xg), 0, zf + 1.0 + sw / 2), yaw=yaw_cote):
            _ecran(b, -sw / 2, sw / 2, 18.0, 42.0, 0.0, style, couleurs, cadre=0.9, ep=0.8)
            _n(b, (-sw / 2, 17.6, -1.0), (sw / 2, 17.9, 0.05), "neon_blanc", name="RampeEcran")
        # écran vertical sur la façade avant, contre l'angle (12 × 32, y 14-46)
        style, couleurs = st["vertical"]
        with b.at((X(xg + 7.0), 0, zf), yaw=0.0):
            _ecran(b, -6.0, 6.0, 14.0, 46.0, 0.0, style, couleurs, cadre=0.8, ep=0.8)
            _n(b, (-6.0, 46.0, -1.0), (6.0, 46.3, 0.05), "neon_blanc", name="RampeEcran")
        # bandeau défilant qui tourne l'angle (y 9,4-11,4)
        ya, yb = 10.4, 12.4
        lf_, ls_ = min(22.0, 0.56 * LX), min(24.0, 0.58 * LZ)
        dbox((xg - 0.6, ya, zf - 0.6), (xg + lf_, yb, zf), "ecran_fond", shadow=True, name="Defilant")
        dbox((xg - 0.6, ya, zf), (xg, yb, zf + ls_), "ecran_fond", shadow=True, name="Defilant")
        cs = st["defilant"]
        for i in range(int((lf_ - 1.0) // 4.2)):
            x = xg + 1.0 + i * 4.2
            nbox((x, ya + 0.35, zf - 0.78), (x + 3.0, yb - 0.35, zf - 0.55), cs[i % len(cs)], name="Defile")
        p = dbox((xg - 0.78, ya + 0.25, zf + 1.5), (xg - 0.55, yb - 0.25, zf + 9.5), "ecran_fond", name="DefileMot")
        _lab(p, "映画", cs[1], face=F("Left"), glow=1.4)
        for i in range(int((ls_ - 11.0) // 4.2)):
            z = zf + 11.0 + i * 4.2
            nbox((xg - 0.78, ya + 0.35, z), (xg - 0.55, yb - 0.35, z + 3.0), cs[(i + 2) % len(cs)], name="Defile")

    # --- rez-de-chaussée : café vitré à l'angle, hall, marquises ---
    with b.group("RezDeChaussee"):
        # soubassement, vitrines éclairées (saillie 0,3) et meneaux
        box((xg + 0.4, 0, zf - 0.55), (xd - 0.8, 0.4, zf), "anthracite", studs="top", name="Soubassement")
        box((xg - 0.55, 0, zf), (xg, 0.4, zcafe), "anthracite", studs="top", name="Soubassement")
        nbox((xg + 0.4, 0.4, zf - 0.3), (xcafe, 6.0, zf + 0.05), "fenetre_chaude", collide=True, name="VitrineCafe")
        nbox((xg - 0.3, 0.4, zf + 0.4), (xg + 0.05, 6.0, zcafe - 0.2), "fenetre_chaude", collide=True, name="VitrineCafe")
        nbox((xcafe + 0.6, 0.4, zf - 0.3), (xd - 0.8, 6.0, zf + 0.05), "fenetre_froide", collide=True, name="VitrineHall")
        for x in list(np.arange(xg + 3.0, xcafe - 0.6, 3.4)) + list(np.arange(xcafe + 3.6, xd - 1.0, 3.6)):
            dbox((x - 0.2, 0.4, zf - 0.5), (x + 0.2, 6.0, zf), "metal_fonce", name="Meneau")
        for z in np.arange(zf + 3.0, zcafe, 3.4):
            dbox((xg - 0.5, 0.4, z - 0.2), (xg, 6.0, z + 0.2), "metal_fonce", name="Meneau")
        dbox((xg + 8.5, 0.4, zf - 0.45), (xg + 12.1, 5.8, zf - 0.28), "vitre", name="PorteCafe")
        dbox((xcafe + 6.4, 0.4, zf - 0.45), (xcafe + 10.6, 5.8, zf - 0.28), "vitre", name="PorteHall")
        box((xg - 0.5, 0, zf - 0.5), (xg + 0.4, 7.6, zf + 0.4), "anthracite", name="PilierAngle")
        box((xcafe, 0, zf - 0.5), (xcafe + 0.6, 7.6, zf + 0.05), "anthracite", name="Pilier")
        # bandeaux d'enseigne sous la marquise (saillie 0,5 sous y = 7)
        p = dbox((xg + 0.4, 6.0, zf - 0.5), (xcafe, 7.4, zf + 0.05), st["cafe"], shadow=True, name="EnseigneCafe")
        _lab(p, "喫茶", (255, 214, 140), face="Front", glow=1.2)
        p = dbox((xg - 0.5, 6.0, zf + 0.4), (xg + 0.05, 7.4, zcafe), st["cafe"], shadow=True, name="EnseigneCafe")
        _lab(p, "喫茶", (255, 214, 140), face=F("Left"), glow=1.2)
        p = dbox((xcafe + 0.6, 6.0, zf - 0.5), (xd - 0.8, 7.4, zf + 0.05), "bleu_marine", shadow=True, name="EnseigneHall")
        _lab(p, "映画", (220, 235, 255), face="Front", glow=1.2)
        # caissons 喫茶 debout sur le bord des marquises (devant et côté carrefour)
        p = dbox((xg + 2.0, 8.2, -hd + 0.1), (xg + 9.0, 10.0, -hd + 0.5), st["cafe"], shadow=True, name="CaissonCafe")
        _lab(p, "喫茶", (255, 214, 140), face="Front", glow=1.3)
        p = dbox((xg - RET + 0.1, 8.2, zf + 3.0), (xg - RET + 0.5, 10.0, zf + 10.0), st["cafe"], shadow=True,
                 name="CaissonCafe")
        _lab(p, "喫茶", (255, 214, 140), face=F("Left"), glow=1.3)
        # marquises (studs) qui tournent l'angle, néon chaud sous le bord
        box((xg - RET, 7.6, zf - RET), (xcafe + 1.0, 8.2, zf), st["auvent"], studs="top", name="Marquise")
        box((xg - RET, 7.6, zf), (xg, 8.2, zcafe + 0.5), st["auvent"], studs="top", name="Marquise")
        box((xcafe + 1.0, 7.6, zf - 1.6), (xd - 0.6, 8.0, zf), "metal_fonce", studs="top", name="MarquiseHall")
        nbox((xg - RET, 7.3, zf - RET), (xcafe + 1.0, 7.6, zf - RET + 0.3), "fenetre_chaude", name="NeonMarquise")
        nbox((xg - RET, 7.3, zf - RET + 0.3), (xg - RET + 0.3, 7.6, zcafe + 0.5), "fenetre_chaude", name="NeonMarquise")

    # --- enseigne verticale (drapeau) sur la façade avant, lisible depuis la rue ---
    xe = (ailettes[-2] + ailettes[-1]) / 2 if len(ailettes) > 1 else xd - 4.9
    with b.at((X(xe), 13.0, zf), group="Enseigne"):
        enseigne_verticale(b, "カラオケ", variant=2, couleur="neon_cyan", hauteur=17.0, profondeur=2.0)

    # --- toit : panneaux en équerre au-dessus de l'angle, équipements, feux d'obstacle ---
    with b.group("Toit"):
        hp, yp = 10.0, yT + 2.5
        lp = min(16.0, 0.42 * min(LX, LZ))
        # panneau A : face au carrefour
        style, couleurs = st["toit_a"]
        with b.at((X(xg + 1.6), 0, zf + 1.6 + lp / 2), yaw=yaw_cote):
            _ecran(b, -lp / 2, lp / 2, yp, yp + hp, 0.0, style, couleurs, cadre=0.6, ep=0.8)
            _n(b, (-lp / 2, yp + hp, -1.0), (lp / 2, yp + hp + 0.3, 0.05), "neon_blanc", name="Rampe")
            _d(b, (-lp / 2, yp - 0.4, -1.6), (lp / 2, yp - 0.2, 0.0), "metal_fonce", name="Passerelle")
            for u in (-lp / 2 + 1.5, lp / 2 - 1.5):
                b.box((u - 0.35, yT, 0.0), (u + 0.35, yp + hp * 0.85, 0.7), c("metal_fonce"), name="PiedPanneau")
                b.wedge((u - 0.25, yT, 0.7), (u + 0.25, yT + 5.0, 4.0), c("metal_fonce"), down="+z", name="Jambe")
        # panneau B : face au couloir
        style, couleurs = st["toit_b"]
        with b.at((X(xg + 1.6 + lp / 2 + 0.2), 0, zf + 1.6), yaw=0.0):
            _ecran(b, -lp / 2, lp / 2, yp, yp + hp, 0.0, style, couleurs, cadre=0.6, ep=0.8)
            _n(b, (-lp / 2, yp + hp, -1.0), (lp / 2, yp + hp + 0.3, 0.05), "neon_blanc", name="Rampe")
            _d(b, (-lp / 2, yp - 0.4, -1.6), (lp / 2, yp - 0.2, 0.0), "metal_fonce", name="Passerelle")
            for u in (-lp / 2 + 1.5, lp / 2 - 1.5):
                b.box((u - 0.35, yT, 0.0), (u + 0.35, yp + hp * 0.85, 0.7), c("metal_fonce"), name="PiedPanneau")
                b.wedge((u - 0.25, yT, 0.7), (u + 0.25, yT + 5.0, 4.0), c("metal_fonce"), down="+z", name="Jambe")
        # équipements
        def rx(f):
            return xg + f * LX

        def rz(f):
            return zf + f * LZ

        box((rx(0.62), yT, rz(0.67)), (rx(0.82), yT + 4.0, rz(0.84)), "beton_fonce", studs="top", name="LocalTech")
        with b.at((X(rx(0.72)), 0, rz(0.4))):
            _citerne(b, 0.0, yT, 0.0)
        for (x, z) in ((rx(0.32), rz(0.76)), (rx(0.42), rz(0.76)), (rx(0.52), rz(0.87))):
            with b.at((X(x), 0, z)):
                _clim_toit(b, 0.0, yT, 0.0)
        for (x, z) in ((xd - 1.2, zb - 1.2), (xg + 1.2, zb - 1.2)):
            with b.at((X(x), 0, z)):
                _balise(b, 0.0, H, 0.0)
        with b.at((X(xg + 1.1), 0, zf + 2.4)):             # sur la rampe du panneau A
            _balise(b, 0.0, yp + hp + 0.3, 0.0, s=0.7)
    return {"emprise": (largeur, profondeur), "hauteur": _haut(b, n0)}


# ---------------------------------------------------------------------------
# 3) Gare à longue façade vitrée
# ---------------------------------------------------------------------------

GARES = [
    dict(mur="beton_clair", pilier="metal_clair", meneau="bleu_nuit", bandeau="bleu_marine", pylone="bleu_nuit",
         aile="beton", kiosque="bleu_marine", marquise="metal_clair", lumiere=("fenetre_chaude", "fenetre_froide")),
    dict(mur="beton_clair", pilier="metal_clair", meneau="bleu_nuit", bandeau="bleu_marine", pylone="bleu_nuit",
         aile="beton", kiosque="bleu_marine", marquise="metal_clair", lumiere=("fenetre_chaude", "fenetre_froide")),
    dict(mur="bleu_pale", pilier="metal_clair", meneau="anthracite", bandeau="bleu_nuit", pylone="bleu_marine",
         aile="beton_clair", kiosque="bleu_nuit", marquise="beton_clair", lumiere=("fenetre_froide", "fenetre_chaude")),
    dict(mur="beton", pilier="metal_clair", meneau="bleu_marine", bandeau="anthracite", pylone="bleu_ardoise",
         aile="beton_clair", kiosque="anthracite", marquise="metal_clair", lumiere=("fenetre_chaude", "fenetre_chaude")),
]


def _horloge(b, cx, cy, cz, axe, sens, r=2.3, h1=40.0, h2=150.0):
    """Horloge de gare : boîtier, cadran blanc, deux aiguilles et axe (5 pièces). Le cadran regarde `sens` (-1 ou +1)
    le long de l'axe `axe` (x ou z) ; (cx, cy, cz) = centre du dos du boîtier, contre le mur."""
    ep = 0.6
    if axe == "z":
        b.cyl((cx, cy, cz + sens * ep / 2), r, ep, c("metal_clair"), axis="z", name="Horloge")
        b.cyl((cx, cy, cz + sens * (ep + 0.05)), r - 0.35, 0.2, c("blanc"), axis="z", **PETIT, name="Cadran")
        zf = cz + sens * (ep + 0.15)
        for ang, L, w in ((h1, 1.3, 0.3), (h2, 1.75, 0.2)):
            a = math.radians(ang)
            ctr = (cx + math.sin(a) * L / 2, cy + math.cos(a) * L / 2, zf + sens * 0.06)
            b.part("block", (w, L, 0.1), ctr, rot_z(-ang), c("enseigne_noir"), **PETIT, name="Aiguille")
        b.cyl((cx, cy, zf + sens * 0.15), 0.25, 0.12, c("neon_rouge"), axis="z", **PETIT, name="Axe")
    else:
        b.cyl((cx + sens * ep / 2, cy, cz), r, ep, c("metal_clair"), axis="x", name="Horloge")
        b.cyl((cx + sens * (ep + 0.05), cy, cz), r - 0.35, 0.2, c("blanc"), axis="x", **PETIT, name="Cadran")
        xf = cx + sens * (ep + 0.15)
        for ang, L, w in ((h1, 1.3, 0.3), (h2, 1.75, 0.2)):
            a = math.radians(ang)
            ctr = (xf + sens * 0.06, cy + math.cos(a) * L / 2, cz - sens * math.sin(a) * L / 2)
            b.part("block", (0.1, L, w), ctr, rot_x(-sens * ang), c("enseigne_noir"), **PETIT, name="Aiguille")
        b.cyl((xf + sens * 0.15, cy, cz), 0.25, 0.12, c("neon_rouge"), axis="x", **PETIT, name="Axe")


def gare_facade(b, variant=0, largeur=62, profondeur=26, hauteur=28):
    """Gare du coin sud-ouest : longue façade vitrée éclairée vers -Z (le carrefour), côté -X vers le couloir
    (sortie 出口, édicule de métro). v0 / v2 : l'incident commence (vitres brisées, lueur violette, fissure)."""
    rng = b.rng
    n0 = len(b.parts)
    st = GARES[variant % len(GARES)]
    abime = variant % 2 == 0
    hw, hd = largeur / 2, profondeur / 2
    yR = hauteur - 3.0                       # toit de la halle
    yP = yR + 7.0                            # haut de la tour de l'horloge
    zf = -hd + 3.5                           # plan de la façade vitrée (marquise et horloge dans l'emprise)
    xr = hw - 0.3                            # pignon +X (les détails du pignon restent dans l'emprise)
    zr = hd - 0.3                            # arrière
    xp0, xp1 = -hw + 9.0, -hw + 15.0         # tour de l'horloge
    xa0 = -hw + 1.5                          # pignon de l'aile (côté couloir)
    xg0, xg1 = xp1 + 0.6, hw - 7.0           # bande vitrée (le reste à droite est un mur plein)

    # --- grande halle ---
    with b.group("Halle"):
        b.box((xp0, 0, zf), (xr, yR, zr), vr(st["mur"], rng, 0.02), studs="top", name="Halle")
        a = c("beton_fonce")
        b.box((xp1, yR, zf - 0.15), (xr + 0.1, yR + 1.5, zf + 0.5), a, studs="top", name="Acrotere")
        b.box((xp0 + 0.4, yR, zr - 0.5), (xr + 0.1, yR + 1.5, zr + 0.1), a, studs="top", name="Acrotere")
        b.box((xr - 0.5, yR, zf + 0.5), (xr + 0.1, yR + 1.5, zr - 0.5), a, studs="top", name="Acrotere")
        b.box((xp0 - 0.1, yR, zf + 6.3), (xp0 + 0.5, yR + 1.5, zr - 0.5), a, studs="top", name="Acrotere")

    # --- rez-de-chaussée : hall d'entrée éclairé, portes, piliers ---
    with b.group("Entree"):
        b.box((xp1, 0, zf - 0.6), (xr - 0.6, 0.4, zf), c("beton_fonce"), studs="top", name="Soubassement")
        _n(b, (xp1, 0.4, zf - 0.3), (xr - 0.6, 9.2, zf + 0.05), "fenetre_chaude", collide=True, name="Hall")
        for x0 in (-6.0, -1.9, 2.2):
            _d(b, (x0, 0.4, zf - 0.5), (x0 + 3.7, 7.4, zf - 0.28), "vitre", shadow=True, name="Portes")
            _d(b, (x0 + 1.75, 0.5, zf - 0.6), (x0 + 1.95, 7.3, zf - 0.45), "metal_clair", name="Battant")
        for x in (xp1 + 0.4, -9.0, 9.0, 20.0, xr - 0.6):
            b.box((x - 0.4, 0, zf - 0.7), (x + 0.4, 9.8, zf), c(st["pilier"]), name="Pilier")
        b.box((xp1, 9.2, zf - 0.5), (xr, 9.8, zf), c(st["pilier"]), name="Linteau")
        # marquise (studs) et néon sous le bord ; tirants vers la façade
        b.box((xp1, 9.8, -hd), (xr - 0.4, 10.6, zf), c(st["marquise"]), studs="top", name="Marquise")
        if abime:
            _n(b, (xp1 + 0.3, 9.5, -hd + 0.15), (6.0, 9.8, -hd + 0.55), "neon_blanc", name="NeonMarquise")
            _d(b, (6.0, 9.5, -hd + 0.15), (xr - 0.7, 9.8, -hd + 0.55), "metal_fonce", name="NeonEteint")
        else:
            _n(b, (xp1 + 0.3, 9.5, -hd + 0.15), (xr - 0.7, 9.8, -hd + 0.55), "neon_blanc", name="NeonMarquise")
        for x in (-12.0, 9.0, 26.0):
            b.box((x - 0.3, 0, -hd + 0.4), (x + 0.3, 9.8, -hd + 1.0), c(st["pilier"]), name="Poteau")

    # --- longue bande vitrée éclairée (2 rangs de cellules) ---
    with b.group("Vitrage"):
        n = max(4, int(round((xg1 - xg0) / 3.6)))
        p = (xg1 - xg0) / n
        rangs = ((11.0, 16.0), (16.4, yR - 3.6))
        etat = [["L"] * n for _ in rangs]
        for r in range(2):
            for i in range(n):
                if rng.random() < (0.3 if abime else 0.1):
                    etat[r][i] = "O"
        if abime:
            for (r, i) in ((1, 2), (0, 3), (1, 7), (0, 9)):
                if i < n:
                    etat[r][i] = "B"
        for r, (ya, yb) in enumerate(rangs):
            i = 0
            while i < n:
                j = i
                while j + 1 < n and etat[r][j + 1] == etat[r][i]:
                    j += 1
                x0, x1 = xg0 + i * p, xg0 + (j + 1) * p
                e = etat[r][i]
                if e == "L":
                    _n(b, (x0, ya, zf - 0.25), (x1, yb, zf + 0.05), st["lumiere"][r], collide=True, name="Lumiere")
                else:
                    b.box((x0, ya, zf - 0.25), (x1, yb, zf + 0.05), c("vitre") if e == "O" else c("fissure"),
                          name="Eteint" if e == "O" else "Trou")
                if e != "B":
                    b.box((x0, ya, zf - 0.55), (x1, yb, zf - 0.35), c("vitre_claire"), **VERRE, name="Vitre")
                else:
                    for k in range(j - i + 1):
                        cx = xg0 + (i + k + 0.5) * p
                        cy = (ya + yb) / 2
                        for (u0, v0, u1, v1) in ((-1.3, -1.0, 0.5, 0.2), (-0.6, -0.2, 1.1, 1.3), (-0.2, -1.8, 0.6, -0.6)):
                            _n(b, (cx + u0, cy + v0, zf - 0.38), (cx + u1, cy + v1, zf - 0.2), "lueur_violette", name="Lueur")
                        xa, xb = xg0 + (i + k) * p + 0.2, xg0 + (i + k + 1) * p - 0.2
                        b.wedge((xa, ya, zf - 0.55), (xa + 1.4, ya + 1.9, zf - 0.35), c("verre_brise"), down="+x",
                                transparency=0.4, material="Glass", **PETIT, name="Eclat")
                        b.wedge_under((xb - 1.1, yb - 1.6, zf - 0.55), (xb, yb, zf - 0.35), c("verre_brise"), down="-x",
                                      transparency=0.4, material="Glass", **PETIT, name="Eclat")
                        # éclats tombés sur la marquise
                        for dx, dz, ang in ((-0.8, -hd + 1.4, 9), (0.9, -hd + 0.8, -7)):
                            b.part("block", (1.1, 0.14, 0.7), (cx + dx, 10.68, dz), rot_z(ang), c("verre_brise"),
                                   transparency=0.4, material="Glass", **PETIT, name="EclatTombe")
                i = j + 1
        # meneaux, traverse, appuis
        for i in range(n + 1):
            x = xg0 + i * p
            b.box((x - 0.2, 10.6, zf - 0.8), (x + 0.2, yR - 3.2, zf), c(st["meneau"]), name="Meneau")
        b.box((xg0, 16.0, zf - 0.75), (xg1, 16.4, zf), c(st["meneau"]), name="Traverse")
        b.box((xg0 - 0.5, 10.6, zf - 0.9), (xg1 + 0.5, 11.0, zf), c(st["pilier"]), studs="top", name="Appui")
        b.box((xg0 - 0.5, yR - 3.6, zf - 0.9), (xg1 + 0.5, yR - 3.2, zf), c(st["pilier"]), name="Appui")

    # --- bandeau d'enseigne, grand 駅, 西口 ---
    with b.group("Enseignes"):
        yb0, yb1 = yR - 3.2, yR - 0.6             # bandeau d'enseigne (21,8-24,4 pour une gare de 28)
        b.box((xp1, yb0, zf - 0.7), (xr, yb1, zf), c(st["bandeau"]), name="Bandeau")
        _n(b, (xp1 + 0.1, yb0, zf - 0.85), (xr - 0.1, yb0 + 0.3, zf - 0.65), "neon_cyan", name="NeonBandeau")
        _n(b, (-4.6, yb0 - 0.3, zf - 1.5), (4.6, yR + 5.4, zf - 0.65), "neon_bleu", name="Halo")
        p = _d(b, (-4.2, yb0 + 0.1, zf - 1.9), (4.2, yR + 5.0, zf - 0.6), "enseigne_blanc", shadow=True, name="EnseigneGare")
        _lab(p, "駅", (28, 48, 108), fond=(246, 249, 255), glow=1.1)
        for s in (-1, 1):
            _d(b, (s * 3.0 - 0.3, yR + 1.5, zf - 0.7), (s * 3.0 + 0.3, yR + 4.0, zf + 1.5), "metal_fonce", name="Console")
        p = _d(b, (8.0, yb0 + 0.5, zf - 1.0), (17.0, yb1 - 0.4, zf - 0.68), (46, 92, 196), shadow=True, name="SousEnseigne")
        _lab(p, "西口", (255, 255, 255), fond=(46, 92, 196), glow=1.1)
        # petit tableau lumineux à gauche du 駅 (images abstraites)
        _d(b, (-14.6, yb0 + 0.4, zf - 1.0), (-6.2, yb1 - 0.2, zf - 0.68), "ecran_fond", shadow=True, name="Tableau")
        for i, cc in enumerate(("neon_cyan", "neon_jaune", "neon_magenta", "neon_blanc")):
            x = -14.2 + i * 2.0
            _n(b, (x, yb0 + 0.75, zf - 1.2), (x + 1.6, yb1 - 0.55, zf - 0.95), cc, name="TableauImage")

    # --- tour de l'horloge (deux cadrans : vers le carrefour et vers le couloir) ---
    with b.group("TourHorloge"):
        b.box((xp0 - 0.3, 0, zf - 0.7), (xp1, yP, zf + 6.0), vr(st["pylone"], rng, 0.03), name="Tour")
        b.box((xp0 - 0.6, yP, zf - 1.0), (xp1 + 0.3, yP + 0.8, zf + 6.3), c("metal_clair"), studs="top", name="Chapeau")
        _n(b, (xp0 + 2.4, 11.0, zf - 0.85), (xp1 - 2.4, yP - 7.5, zf - 0.65), "neon_cyan", name="Lame")
        _n(b, (xp0 - 0.45, yP - 1.4, zf - 0.85), (xp1 + 0.15, yP - 1.0, zf + 6.15), "neon_blanc", name="Liseré")
        _horloge(b, (xp0 + xp1) / 2, yP - 4.2, zf - 0.7, "z", -1)
        _horloge(b, xp0 - 0.3, yP - 4.2, zf + 2.65, "x", -1)

    # --- aile basse côté couloir : sortie 出口 ---
    with b.group("Aile"):
        zw = -hd + 9.0                            # façade avant de l'aile (derrière l'édicule)
        b.box((xa0, 0, zw), (xp0, 16.0, zr), vr(st["aile"], rng, 0.03), studs="top", name="Aile")
        b.box((xa0 - 0.15, 16.0, zw - 0.15), (xp0, 17.2, zw + 0.4), c("beton_fonce"), studs="top", name="Acrotere")
        b.box((xa0 - 0.15, 16.0, zw + 0.4), (xa0 + 0.45, 17.2, zr), c("beton_fonce"), studs="top", name="Acrotere")
        _d(b, (xa0 - 0.4, 0.3, 1.0), (xa0, 7.6, 8.0), "vitre", shadow=True, name="PortesSortie")
        _d(b, (xa0 - 0.5, 0.4, 4.4), (xa0 - 0.35, 7.5, 4.6), "metal_clair", name="Battant")
        _n(b, (xa0 - 0.3, 0.3, 0.4), (xa0 + 0.05, 7.6, 1.0), "fenetre_chaude", name="Jour")
        _n(b, (xa0 - 0.3, 0.3, 8.0), (xa0 + 0.05, 7.6, 8.6), "fenetre_chaude", name="Jour")
        b.box((-hw, 8.4, -0.4), (xa0, 9.0, 9.4), c(st["marquise"]), studs="top", name="MarquiseSortie")
        _n(b, (-hw, 8.1, -0.4), (-hw + 0.3, 8.4, 9.4), "neon_blanc", name="NeonSortie")
        p = _d(b, (xa0 - 0.5, 9.6, 1.2), (xa0, 12.4, 7.8), (255, 214, 60), shadow=True, name="EnseigneSortie")
        _lab(p, "出口", (30, 30, 36), fond=(255, 214, 60), face="Left", glow=1.0)
        b.box((xa0 - 0.2, 13.0, zw + 0.8), (xa0, 15.0, zr - 0.8), c("vitre_bleue"), name="Ruban")
        _n(b, (xa0 - 0.32, 13.3, 2.0), (xa0 - 0.1, 14.7, 9.0), "fenetre_froide", name="Lumiere")
        b.box((xa0 + 0.6, 2.0, zw - 0.2), (xp0 - 0.6, 14.0, zw), c("vitre_bleue"), name="VitreAile")
        _n(b, (xa0 + 1.2, 2.6, zw - 0.32), (xp0 - 1.2, 7.5, zw - 0.1), "fenetre_chaude", name="Lumiere")
        # pignon de la halle au-dessus de l'aile
        b.box((xp0 - 0.2, 17.8, zw + 1.0), (xp0, yR - 2.4, zr - 0.6), c("vitre_bleue"), name="Ruban")
        _n(b, (xp0 - 0.35, 18.2, zw + 5.0), (xp0 - 0.1, yR - 2.8, zw + 11.0), "fenetre_froide", name="Lumiere")

    # --- édicule du métro (dans l'emprise, ouvert vers le couloir) ---
    with b.group("Edicule"):
        k0, k1 = -hw + 0.6, -hw + 7.6
        z0, z1 = -hd + 0.6, -hd + 7.6
        b.box((k0, 0, z0), (k1, 0.3, z1), c("beton_fonce"), studs="top", name="Dalle")
        b.box((k0 + 0.8, 0.3, z0 + 1.0), (k1 - 1.2, 0.4, z1 - 1.0), c("noir"), name="Tremie")
        b.box((k1 - 0.5, 0.3, z0), (k1, 4.4, z1), c(st["kiosque"]), name="Fond")
        _n(b, (k1 - 0.65, 0.8, z0 + 0.8), (k1 - 0.45, 4.0, z1 - 0.8), "fenetre_froide", name="Lumiere")
        for za, zb_ in ((z0, z0 + 0.3), (z1 - 0.3, z1)):
            b.box((k0 + 0.4, 0.3, za), (k1 - 0.5, 4.2, zb_), c("vitre_claire"), **VERRE, name="Paroi")
            b.box((k0, 0.3, za), (k0 + 0.4, 4.4, zb_), c("metal_clair"), name="Montant")
            zz0, zz1 = (za + 0.6, za + 0.75) if za == z0 else (za - 0.75, za - 0.6)
            _d(b, (k0 + 0.55, 1.5, zz0), (k1 - 0.5, 1.7, zz1), "metal_clair", name="MainCourante")
            _d(b, (k0 + 0.55, 0.3, zz0), (k0 + 0.75, 1.5, zz1), "metal_clair", name="Potelet")
        b.box((k0 - 0.6, 4.4, z0 - 0.6), (k1 + 0.2, 5.0, z1 + 0.4), c(st["kiosque"]), studs="top", name="Toit")
        p = _d(b, (k0 - 0.2, 5.0, z0 - 0.2), (k0 + 2.6, 7.8, z0 + 2.6), (40, 92, 200), shadow=True, name="EnseigneMetro")
        _lab(p, "駅", (255, 255, 255), fond=(40, 92, 200), face="Left", glow=1.1)
        p = _d(b, (k0 + 0.1, 5.3, z0 - 0.35), (k0 + 2.3, 7.5, z0 - 0.2), (40, 92, 200), name="EnseigneMetro")
        _lab(p, "駅", (255, 255, 255), fond=(40, 92, 200), face="Front", glow=1.1)

    # --- mur plein à droite de la bande vitrée, pignon +X, arrière ---
    with b.group("Murs"):
        _n(b, (xg1 + 1.0, 12.0, zf - 0.15), (xr - 1.0, 13.0, zf + 0.05), "neon_cyan" if not abime else "lueur_violette",
           name="Filet")
        b.box((xr, 11.0, zf + 1.0), (xr + 0.2, 20.0, zr - 1.0), c("vitre_bleue"), name="Ruban")
        _n(b, (xr + 0.1, 11.6, 4.0), (xr + 0.25, 19.4, 11.0), "fenetre_froide", name="Lumiere")
        b.box((xp0 + 1.0, 12.0, zr), (xr - 1.0, 20.0, zr + 0.2), c("vitre_bleue"), name="Ruban")
        if not abime:
            # caisson lumineux (affiche abstraite) sur le mur plein, quand la gare est intacte
            yc1 = min(20.6, yR - 4.4)
            _d(b, (xg1 + 1.2, 13.6, zf - 0.6), (xr - 1.2, yc1, zf + 0.05), "ecran_fond", shadow=True, name="Caisson")
            _image(b, xg1 + 1.7, xr - 1.7, 14.1, yc1 - 0.5, zf - 0.6, "disque", ("neon_bleu", "neon_blanc", "neon_cyan"),
                   relief=0.2)
        if abime:
            # fissure en diagonale (escalier de petits blocs sombres) sur le mur plein et le bandeau
            pts = [(xr - 0.8, yR - 3.4), (xr - 2.4, yR - 6.0), (xr - 2.0, 16.6), (xr - 4.2, 14.2), (xr - 4.0, 12.0),
                   (xg1 + 0.8, 11.2)]
            for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
                L = math.hypot(xb - xa, yb - ya)
                ang = math.degrees(math.atan2(yb - ya, xb - xa))
                b.part("block", (L + 0.3, 0.35, 0.2), ((xa + xb) / 2, (ya + yb) / 2, zf - 0.1), rot_z(ang),
                       c("fissure"), **PETIT, name="Fissure")
            for (x, y) in ((xr - 2.3, yR - 6.6), (xr - 4.1, 13.4)):
                _n(b, (x - 0.35, y - 0.35, zf - 0.32), (x + 0.35, y + 0.35, zf - 0.08), "lueur_violette", name="Lueur")
            b.part("block", (3.2, 0.35, 0.2), (xr - 2.0, yR - 1.8, zf - 0.8), rot_z(-55), c("fissure"), **PETIT, name="Fissure")
            # gravats au pied du mur, sous la marquise
            for (x, z, s) in ((xr - 3.0, -hd + 1.6, 1.2), (xr - 1.6, -hd + 2.6, 0.8), (xr - 4.4, -hd + 2.8, 0.7)):
                b.box((x - s, 0, z - s * 0.8), (x + s, s * 0.9, z + s * 0.8), vr("gravats", rng, 0.08), name="Gravats")

    # --- grand écran LED sur le toit, derrière l'acrotère (en panne en partie quand l'incident commence) ---
    with b.group("EcranToit"):
        ex0, ex1 = 8.5, xr - 2.5
        ey0, ey1 = yR + 1.8, yR + 7.8
        ez = zf + 1.6                               # dos de l'écran
        _d(b, (ex0, ey0, ez - 0.8), (ex1, ey1, ez), "ecran_fond", shadow=True, name="CadreEcran")
        _n(b, (ex0, ey1, ez - 1.0), (ex1, ey1 + 0.3, ez + 0.05), "neon_blanc", name="Rampe")
        for x in (ex0 + 1.5, ex1 - 1.5, (ex0 + ex1) / 2):
            b.box((x - 0.35, yR, ez), (x + 0.35, ey1 - 0.6, ez + 0.7), c("metal_fonce"), name="PiedEcran")
            b.wedge((x - 0.25, yR, ez + 0.7), (x + 0.25, yR + 3.5, ez + 3.2), c("metal_fonce"), down="+z", name="Jambe")
        if abime:
            xm = ex0 + (ex1 - ex0) * 0.58
            _image(b, ex0 + 0.6, xm, ey0 + 0.6, ey1 - 0.6, ez - 0.8, "bandes", ("neon_cyan", "ecran_bleu", "neon_blanc"),
                   relief=0.2)
            b.box((xm, ey0 + 0.6, ez - 0.95), (ex1 - 0.6, ey1 - 0.6, ez - 0.75), c("vitre"), name="EcranEteint")
            for (u, v, w, h) in ((0.15, 0.55, 0.3, 0.12), (0.45, 0.25, 0.22, 0.1), (0.62, 0.7, 0.2, 0.09)):
                xa = xm + (ex1 - 0.6 - xm) * u
                ya = ey0 + 0.6 + (ey1 - ey0 - 1.2) * v
                _n(b, (xa, ya, ez - 1.1), (xa + (ex1 - xm) * w, ya + (ey1 - ey0) * h, ez - 0.9), "lueur_violette",
                   name="Parasite")
        else:
            _image(b, ex0 + 0.6, ex1 - 0.6, ey0 + 0.6, ey1 - 0.6, ez - 0.8, "vague", ("neon_cyan", "ecran_bleu", "neon_jaune"),
                   relief=0.2)

    # --- toit : atrium vitré, local technique, climatiseurs, antenne ---
    with b.group("Toit"):
        ax0, ax1, az0, az1 = 4.0, 18.0, zf + 9.0, zf + 18.0
        for x in (ax0, ax1 - 0.6):
            for z in (az0, az1 - 0.6):
                b.box((x, yR, z), (x + 0.6, yR + 4.0, z + 0.6), c(st["pilier"]), name="Poteau")
        b.box((ax0 + 0.6, yR, az0 + 0.1), (ax1 - 0.6, yR + 4.0, az1 - 0.1), c("vitre_claire"), **VERRE, name="Atrium")
        _n(b, (ax0 + 1.6, yR, az0 + 1.2), (ax1 - 1.6, yR + 3.0, az1 - 1.2), "fenetre_froide", name="Lumiere")
        b.box((ax0 - 0.4, yR + 4.0, az0 - 0.4), (ax1 + 0.4, yR + 4.6, az1 + 0.4), c(st["marquise"]), studs="top", name="ToitAtrium")
        b.box((-12.0, yR, zf + 10.0), (-4.0, yR + 3.5, zf + 16.0), c("beton_fonce"), studs="top", name="LocalTech")
        _d(b, (-9.0, yR, zf + 9.85), (-7.0, yR + 2.6, zf + 10.0), "vitre", name="Porte")
        _clim_toit(b, xr - 7.7, yR, zf + 12.0)
        _clim_toit(b, xr - 4.2, yR, zf + 12.0)
        _clim_toit(b, xr - 7.7, yR, zf + 16.0)
        b.cyl((-14.0, yR + 3.0, zr - 2.0), 0.15, 6.0, c("metal"), **PETIT, name="Antenne")
    return {"emprise": (largeur, profondeur), "hauteur": _haut(b, n0)}
