"""Immeubles de la ville de nuit (zone 5, style « stud ») : rue commerçante, tours de bureaux, grands magasins
à écran géant et seconde rangée.

Fonctions publiques (chacune `f(b, variant=0, ...)` → {"emprise": (largeur, profondeur), "hauteur": h}) :
- immeuble_boutique(largeur=16, profondeur=20, etages=4, enseigne="ラーメン", panneau_toit=False) :
    petit immeuble de 3 à 8 étages avec une boutique au rez-de-chaussée (≤ 150 pièces jusqu'à 5 étages, ≤ 175
    au-delà) ; v0 ramen (carrelage blanc, cadre rouge, noren, lampions, menu, caisson ラーメン sur le toit),
    v1 librairie (bleu ardoise, vitrine à rayonnages, rubans à meneaux, balcon, caisson 本), v2 pharmacie
    (crème, bandeau jaune et bleu, 薬 géant, présentoirs, caisson 薬), v3 karaoké / cinéma (bleu nuit, grande
    lame au néon, lignes de néon à chaque étage, marquise, publicité lumineuse sur les murs latéraux),
    v4 boutique fermée (rideaux métalliques tagués, brique, balcons à linge, réclame délavée, caisson éteint),
    v5 immeuble « crayon » (une enseigne par étage, escalier de secours, enseigne murale verticale, cadre
    d'enseigne sur le toit) ;
- superette(largeur=24, profondeur=20, panneau_toit=False) : supérette 24 h (≤ 120), vitrine, bandeau à trois
    rayures de couleurs inventées (v0 violet / cyan / blanc, v1 magenta / jaune / blanc, v2 orange / bleu / blanc) ;
- tour_bureaux(largeur=28, profondeur=28, hauteur=96, panneau_toit=False) : tour de bureaux sur socle à enseignes
    (≤ 200) ; v0 mur-rideau bleu, v1 bleu marine à rubans blancs (l'ADN de la zone actuelle), v2 brique à colonnes
    éclairées et couronne en gradins, v3 béton à ailettes et héliport, v4 la plus haute, verre et arêtes au néon ;
    écrans géants sur les murs latéraux (v0, v1, v3), couronnes lumineuses ;
- grand_magasin(largeur=40, profondeur=32, hauteur=64, ecran=True, panneau_toit=False) : grand magasin à écran
    géant (≤ 250) ; v0 pierre crème et écran « coucher de soleil » magenta / rose / orange, v1 bleu marine et
    écran cyan / bleu, v2 blanc à trois écrans superposés ;
- immeuble_fond(largeur=24, profondeur=24, hauteur=50) : immeuble simple de la seconde rangée (≤ 50 pièces) ;
    v0 bleu ardoise, v1 béton (néon vertical), v2 bleu marine à rubans blancs, v3 brique (enseigne de toit).

Repère (voir CONVENTIONS.md) : origine au centre de l'emprise au sol, y = 0 au sol, l'AVANT regarde -Z.
`largeur` est le long de X (le long de la rue une fois posé), `profondeur` le long de Z. La façade avant est
exactement en z = -profondeur / 2 : posé en x = ±(ligne des façades + profondeur / 2), l'immeuble a sa façade sur
la ligne des façades, quelle qu'elle soit (|x| = 55 avec le couloir élargi à 90 studs, 42 avec l'ancien).
Saillies permises en avant de la façade : 0,6 stud sous y = 7, 4 studs au-dessus. Rien ne dépasse ±largeur / 2
sur les côtés : les murs latéraux sont en retrait de COTE = 0,4 pour laisser la place aux bandeaux et publicités.

Économie de pièces : une bande « traversante » (un seul bloc qui traverse tout l'immeuble et dépasse des
deux côtés) dessine un ruban de fenêtres ou une publicité murale sur deux faces opposées à la fois ; une
« ceinture » dépasse des quatre faces (toujours dans le volume, jamais au-dessus d'un toit). Les grands aplats
sont toujours un seul bloc. Uniquement des éléments de ville génériques : aucun nom de marque, de chaîne ou de
licence, des écrans aux compositions abstraites ou des mots autorisés.
"""

from __future__ import annotations

import math

import numpy as np

from assets.mobilier import clim, enseigne_verticale
from kit import hexrgb, mix, rot_x, shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Dimensions et couleurs locales
# ---------------------------------------------------------------------------
RDC = 9.0           # hauteur du rez-de-chaussée
ETAGE = 8.0         # hauteur d'un étage
ACRO = 1.5          # acrotère (garde-corps maçonné du toit)
COTE = 0.4          # retrait des murs latéraux : les détails de côté (publicités murales) restent dans ±largeur / 2
BOIS = "#8A5A3A"
BOIS_FONCE = "#5A3A28"
ACIER = "#59616E"   # acier peint (escaliers, structures)
INTERIEUR = "#2A2F45"

LIVRES = ["auvent_rouge", "auvent_bleu", "auvent_jaune", "enseigne_blanc", "boisson_4", "bordeaux", "neon_orange"]
PRODUITS = ["boisson_1", "boisson_2", "boisson_3", "boisson_4", "neon_rose", "enseigne_blanc", "auvent_rouge"]
MOTS = ["ラーメン", "カラオケ", "喫茶", "本", "薬", "寿司", "映画"]


def col(x):
    """Nom de palette, '#hex' ou tuple → tuple RGB."""
    if isinstance(x, tuple):
        return x
    if isinstance(x, str) and x.startswith("#"):
        return hexrgb(x)
    return c(x)


def vr(x, rng, amount=0.05):
    """`vary` qui accepte aussi '#hex' et les tuples."""
    return vary(col(x), rng, amount)


def _d(b, a, bb, couleur, **kw):
    """Petit détail : pas de collision ni d'ombre."""
    kw.setdefault("collide", False)
    kw.setdefault("shadow", False)
    return b.box(a, bb, col(couleur), **kw)


def _n(b, a, bb, couleur, **kw):
    """Néon (matériau Neon), sans collision ni ombre."""
    return _d(b, a, bb, couleur, material="Neon", **kw)


def _lab(p, texte, couleur=(250, 250, 250), fond=None, face="Front", glow=None, vertical=False):
    """Pose un panneau texte (SurfaceGui) sur la pièce `p`."""
    p.label = {"face": face, "text": texte, "color": tuple(col(couleur)),
               "bg": None if fond is None else tuple(col(fond)), "font": "sans"}
    if vertical:
        p.label["vertical"] = True
    if glow:
        p.label["glow"] = glow
    return p


def _vitre(b, a, bb, allume, eteinte="vitre", lumiere="fenetre_chaude", **kw):
    """Fenêtre ou ruban de fenêtres : éclairé (Neon) ou éteint."""
    if allume:
        return _n(b, a, bb, lumiere, name="FenetreAllumee", **kw)
    return _d(b, a, bb, eteinte, name="Fenetre", **kw)


def _allumage(rng, n, part=0.3, au_moins=1):
    """Liste de n booléens « fenêtre allumée » (environ une sur trois), au moins `au_moins` allumées."""
    out = [bool(rng.random() < part) for _ in range(n)]
    if n and sum(out) < au_moins:
        out[int(rng.integers(0, n))] = True
    return out


def _hauteur(b, n0):
    """Haut de ce qui a été ajouté depuis la pièce n0, mesuré depuis l'origine de l'asset."""
    y0 = float(b.to_world((0, 0, 0))[1])
    top = y0
    for p in b.parts[n0:]:
        R = np.asarray(p.rot).reshape(3, 3)
        half = np.abs(R) @ (np.asarray(p.size) / 2)
        top = max(top, p.pos[1] + half[1])
    return round(top - y0, 2)


class _G:
    """Gabarit d'un immeuble : murs latéraux en ±hw, façade en zf, arrière en zb, toit en yt."""

    def __init__(self, w, d, n, rdc=RDC):
        self.w, self.d, self.n = float(w), float(d), int(n)
        self.hw = self.w / 2 - COTE
        self.zf, self.zb = -self.d / 2, self.d / 2
        self.rdc = rdc
        self.yt = rdc + ETAGE * (self.n - 1)
        self.niveaux = [rdc + ETAGE * k for k in range(self.n - 1)]   # bas de chaque étage


# ---------------------------------------------------------------------------
# Éléments communs : bandes, toits, panneaux
# ---------------------------------------------------------------------------


def _bande_face(b, g, x0, x1, y0, y1, couleur, s=0.12, arriere=True, **kw):
    """Bande traversante avant / arrière (un bloc dessine la même bande sur les deux faces)."""
    z1 = g.zb + s if arriere else g.zf + 1.0
    kw.setdefault("name", "Ruban")
    return _d(b, (x0, y0, g.zf - s), (x1, y1, z1), couleur, **kw)


def _bande_cotes(b, g, z0, z1, y0, y1, couleur, s=0.12, **kw):
    """Bande traversante sur les deux faces latérales (z0..z1 le long de la profondeur)."""
    kw.setdefault("name", "RubanCote")
    return _d(b, (-g.hw - s, y0, z0), (g.hw + s, y1, z1), couleur, **kw)


def _ceinture(b, x0, x1, z0, z1, y0, y1, couleur, s=0.2, **kw):
    """Bande qui fait le tour d'un volume x0..x1 / z0..z1 (dépasse de s sur les quatre faces)."""
    kw.setdefault("name", "Ceinture")
    return _d(b, (x0 - s, y0, z0 - s), (x1 + s, y1, z1 + s), couleur, **kw)


def _acrotere(b, x0, x1, z0, z1, y, couleur, h=ACRO, ep=0.6, s=0.15):
    """Acrotère en 4 blocs (studs dessus) qui dépasse de s autour du volume x0..x1 / z0..z1."""
    k = dict(studs="top", name="Acrotere")
    b.box((x0 - s, y, z0 - s), (x1 + s, y + h, z0 + ep), couleur, **k)
    b.box((x0 - s, y, z1 - ep), (x1 + s, y + h, z1 + s), couleur, **k)
    b.box((x0 - s, y, z0 + ep), (x0 + ep, y + h, z1 - ep), couleur, **k)
    b.box((x1 - ep, y, z0 + ep), (x1 + s, y + h, z1 - ep), couleur, **k)


def _citerne(b, x, y, z, r=1.4, h=2.8):
    """Citerne d'eau sur son socle d'acier (3 pièces)."""
    b.box((x - r * 0.9, y, z - r * 0.9), (x + r * 0.9, y + 1.0, z + r * 0.9), c("metal_fonce"), name="Socle")
    b.cyl((x, y + 1.0 + h / 2, z), r, h, c("citerne"), name="Citerne")
    b.cyl((x, y + 1.0 + h + 0.15, z), r * 0.45, 0.3, shade(c("citerne"), 0.8), collide=False, shadow=False, name="Trappe")
    return y + 1.3 + h


def _local_tech(b, x, y, z, sx, sz, h, couleur, porte="-z"):
    """Local technique (cage d'escalier sur le toit) : volume, dalle à studs, porte (3 pièces)."""
    b.box((x - sx / 2, y, z - sz / 2), (x + sx / 2, y + h, z + sz / 2), couleur, name="LocalTech")
    b.box((x - sx / 2 - 0.2, y + h, z - sz / 2 - 0.2), (x + sx / 2 + 0.2, y + h + 0.4, z + sz / 2 + 0.2),
          shade(couleur, 0.85), studs="top", name="DalleLocal")
    if porte == "-z":
        _d(b, (x - 0.8, y, z - sz / 2 - 0.12), (x + 0.8, y + 3.2, z - sz / 2), c("metal_fonce"), name="Porte")
    else:
        _d(b, (x + sx / 2, y, z - 0.8), (x + sx / 2 + 0.12, y + 3.2, z + 0.8), c("metal_fonce"), name="Porte")
    return y + h + 0.4


def _antenne(b, x, y, z, h=6.0):
    """Mât d'antenne et deux traverses (3 pièces)."""
    b.cyl((x, y + h / 2, z), 0.12, h, c("metal"), collide=False, name="Antenne")
    _d(b, (x - 1.2, y + h * 0.7, z - 0.06), (x + 1.2, y + h * 0.7 + 0.12, z + 0.06), c("metal"), name="Traverse")
    _d(b, (x - 0.8, y + h * 0.88, z - 0.06), (x + 0.8, y + h * 0.88 + 0.12, z + 0.06), c("metal"), name="Traverse")
    return y + h


def _clim_toit(b, x, y, z, rot=False):
    """Climatiseur posé sur le toit, grille vers -Z (ou -X si rot) (2 pièces)."""
    if rot:
        b.box((x - 0.6, y, z - 1.1), (x + 0.6, y + 1.5, z + 1.1), c("clim"), collide=False, name="ClimToit")
        b.cyl((x - 0.65, y + 0.75, z), 0.5, 0.1, c("metal_fonce"), axis="x", collide=False, shadow=False, name="Grille")
    else:
        b.box((x - 1.1, y, z - 0.6), (x + 1.1, y + 1.5, z + 0.6), c("clim"), collide=False, name="ClimToit")
        b.cyl((x, y + 0.75, z - 0.65), 0.5, 0.1, c("metal_fonce"), axis="z", collide=False, shadow=False, name="Grille")


def _balise(b, x, y, z, s=0.8):
    """Feu rouge d'obstacle (Neon) sur un petit socle (2 pièces)."""
    _d(b, (x - s * 0.4, y, z - s * 0.4), (x + s * 0.4, y + 0.4, z + s * 0.4), c("metal_fonce"), name="SocleBalise")
    _n(b, (x - s / 2, y + 0.4, z - s / 2), (x + s / 2, y + 0.4 + s, z + s / 2), "rouge_balise", name="Balise")


def _toit(b, g, rng, couleur, *, x0=None, x1=None, z0=None, z1=None, y=None, items=("local", "citerne", "clims", "antenne"),
          avant_libre=False):
    """Toit standard : acrotère (studs), puis équipements sur la surface libre. avant_libre : la bande avant reste
    vide (panneau ou caisson de toit) et l'antenne monte sur le local technique. Renvoie le haut atteint."""
    x0 = -g.hw if x0 is None else x0
    x1 = g.hw if x1 is None else x1
    z0 = g.zf if z0 is None else z0
    z1 = g.zb if z1 is None else z1
    y = g.yt if y is None else y
    _acrotere(b, x0, x1, z0, z1, y, couleur)
    top = y + ACRO
    W, D = x1 - x0, z1 - z0
    loc = None
    if "local" in items and W >= 9:
        sx, sz = min(5.0, W * 0.34), min(4.5, D * 0.3)
        lx, lz = x0 + 1.2 + sx / 2, z1 - 1.2 - sz / 2
        yl = _local_tech(b, lx, y, lz, sx, sz, 4.0, shade(couleur, 0.95))
        top = max(top, yl)
        loc = (lx, yl, lz, sx)
    if "citerne" in items:
        r = 1.2 if W < 12 else 1.5
        top = max(top, _citerne(b, x1 - 1.2 - r, y, z1 - 1.4 - r, r=r, h=2.6 if W < 12 else 3.0))
    if "clims" in items:
        zc = (z0 + z1) / 2 + (0.5 if avant_libre else -1.0)
        for k in range(2 if W >= 12 else 1):
            _clim_toit(b, x1 - 2.2 - k * 2.8, y, zc)
    if "antenne" in items:
        if not avant_libre:
            top = max(top, _antenne(b, x0 + 1.4, y, z0 + 1.4, h=5.5 if W < 14 else 7.0))
        elif loc:
            lx, yl, lz, sx = loc
            top = max(top, _antenne(b, lx - sx * 0.25, yl, lz, h=5.0))
        else:
            top = max(top, _antenne(b, x0 + 1.4, y, z1 - 1.4, h=5.5))
    return top


def _ecran(b, x0, x1, y0, y1, z, style, couleurs, *, cadre=0.6, ep=0.6, relief=0.15, mot=None, mot_couleur="blanc"):
    """Écran lumineux : cadre `ecran_fond` (face avant en z, épaisseur ep vers +z) et image abstraite en blocs Neon
    qui dépassent de `relief` ; styles : bandes, cercle, diagonale, rayures, mot. Renvoie le nombre de pièces."""
    n0 = len(b.parts)
    _d(b, (x0, y0, z), (x1, y1, z + ep), "ecran_fond", name="CadreEcran", shadow=True)
    a0, a1, b0, b1 = x0 + cadre, x1 - cadre, y0 + cadre, y1 - cadre
    zi = z - relief
    W, H = a1 - a0, b1 - b0
    c1, c2, c3 = (list(couleurs) + list(couleurs))[:3]
    if style == "bandes":                     # dégradé en trois bandes horizontales
        for k, cc in enumerate((c1, c2, c3)):
            _n(b, (a0, b1 - (k + 1) * H / 3, zi), (a1, b1 - k * H / 3, z), cc, name="Image")
    elif style == "cercle":                   # fond + grand disque en pixels (trois paliers de relief)
        _n(b, (a0, b0, zi), (a1, b1, z), c1, name="Image")
        r = min(W, H) * 0.36
        cx, cy = a0 + W * 0.62, b0 + H * 0.5
        for k, (rx, ry) in enumerate(((r, r * 0.45), (r * 0.8, r * 0.8), (r * 0.45, r))):
            _n(b, (cx - rx, cy - ry, zi - 0.1 * (k + 1)), (cx + rx, cy + ry, zi), c2, name="Disque")
        _n(b, (a0 + W * 0.08, b0 + H * 0.12, zi - 0.1), (a0 + W * 0.3, b0 + H * 0.22, zi), c3, name="Trait")
    elif style == "diagonale":                # fond + marches en diagonale
        _n(b, (a0, b0, zi), (a1, b1, z), c1, name="Image")
        for k in range(3):
            _n(b, (a0 + W * (0.12 + 0.24 * k), b0 + H * (0.15 + 0.22 * k), zi - 0.1),
               (a0 + W * (0.42 + 0.24 * k), b0 + H * (0.37 + 0.22 * k), zi), c2 if k % 2 == 0 else c3, name="Marche")
    elif style == "soleil":                   # dégradé en trois bandes, grand soleil en pixels, ligne d'horizon
        for k, cc in enumerate((c1, c2, c3)):
            _n(b, (a0, b1 - (k + 1) * H / 3, zi), (a1, b1 - k * H / 3, z), cc, name="Image")
        r = min(W, H) * 0.27
        cx, cy = a0 + W * 0.5, b0 + H * 0.4
        _n(b, (cx - r, cy - r * 0.7, zi - 0.15), (cx + r, cy + r * 0.7, zi), "neon_jaune", name="Disque")
        _n(b, (cx - r * 0.7, cy - r, zi - 0.15), (cx + r * 0.7, cy + r, zi), "neon_jaune", name="Disque")
        _n(b, (a0, b0 + H * 0.17, zi - 0.3), (a1, b0 + H * 0.24, zi), "neon_blanc", name="Horizon")
    elif style == "rayures":                  # rayures verticales alternées
        n = 5
        for k in range(n):
            _n(b, (a0 + k * W / n, b0, zi), (a0 + (k + 1) * W / n, b1, z), (c1, c2)[k % 2], name="Image")
        _n(b, (a0 + W * 0.1, b0 + H * 0.4, zi - 0.1), (a1 - W * 0.1, b0 + H * 0.6, zi), c3, name="Bandeau")
    else:                                     # « mot » : fond uni et texte lumineux
        p = _n(b, (a0, b0, zi), (a1, b1, z), c1, name="Image")
        _lab(p, mot or "映画", mot_couleur, glow=1.2)
        _n(b, (a0, b0 + H * 0.06, zi - 0.1), (a1, b0 + H * 0.14, zi), c2, name="Trait")
    if mot and style != "mot":
        ht = min(H * 0.28, 3.0)
        p = _n(b, (a0 + W * 0.08, b1 - ht - H * 0.08, zi - 0.5), (a0 + W * 0.08 + ht * 1.25 * len(mot), b1 - H * 0.08, zi - 0.3),
               "ecran_fond", name="Mot")
        _lab(p, mot, mot_couleur, fond="ecran_fond", glow=1.3)
    return len(b.parts) - n0


def _panneau_toit(b, x0, x1, y, z, h, style, couleurs, *, mot=None, pied=2.0):
    """Panneau publicitaire sur le toit, face vers -Z : deux pieds, poutre, passerelle, écran (≤ 13 pièces).
    (x0, x1) = largeur, y = niveau du toit, z = plan avant de l'écran. Renvoie le haut du panneau."""
    ya = y + pied
    for x in (x0 + 1.2, x1 - 1.2):
        b.box((x - 0.35, y, z + 0.6), (x + 0.35, ya + h * 0.85, z + 1.3), col(ACIER), name="PiedPanneau")
        _d(b, (x - 0.25, y, z + 1.3), (x + 0.25, y + 0.5, z + 3.2), col(ACIER), name="Jambe")
    _d(b, (x0 + 0.6, ya - 0.5, z - 0.8), (x1 - 0.6, ya - 0.3, z + 0.6), c("metal_fonce"), name="Passerelle")
    _ecran(b, x0, x1, ya, ya + h, z, style, couleurs, cadre=0.5, mot=mot)
    _n(b, (x0 + 0.5, ya + h, z - 0.3), (x1 - 0.5, ya + h + 0.25, z + 0.3), "neon_blanc", name="Rampe")
    return ya + h + 0.25


def _lame(b, x, y0, y1, z0, z1, texte, fond, encre, neon, *, ep=1.2, glow=1.2):
    """Grande enseigne en lame perpendiculaire à la façade (deux faces texte vers ±X), cadre au néon (7 pièces).
    x = axe de la lame ; z0 = côté façade, z1 = bout (z1 < z0)."""
    e = ep / 2
    for y in (y0 + 1.0, y1 - 1.0):
        _d(b, (x - 0.2, y - 0.25, z0 + 0.4), (x + 0.2, y + 0.25, z0), c("metal_fonce"), name="Patte")
    corps = _d(b, (x - e, y0, z1), (x + e, y1, z0), fond, name="Lame", shadow=True)
    _lab(corps, texte, encre, face="Right", vertical=True, glow=glow)
    dos = _d(b, (x - e - 0.1, y0 + 0.1, z1 + 0.1), (x - e + 0.1, y1 - 0.1, z0 - 0.1), fond, name="LameDos")
    _lab(dos, texte, encre, face="Left", vertical=True, glow=glow)
    _n(b, (x - e - 0.15, y0 - 0.15, z1 - 0.25), (x + e + 0.15, y1 + 0.15, z1), neon, name="NeonLame")
    _n(b, (x - e - 0.15, y1, z1), (x + e + 0.15, y1 + 0.25, z0), neon, name="NeonLame")
    _n(b, (x - e - 0.15, y0 - 0.25, z1), (x + e + 0.15, y0, z0), neon, name="NeonLame")


def _drapeau(b, x, y, z, texte, variant, couleur=None, hauteur=None):
    """Enseigne verticale en drapeau (mobilier.enseigne_verticale) posée contre la façade en (x, y, z)."""
    with b.at((x, y, z), group="Enseigne"):
        enseigne_verticale(b, texte, variant=variant, couleur=couleur, hauteur=hauteur)


def _choix(liste, cle):
    """Choix déterministe dans une liste à partir d'une clé texte (variété entre exemplaires)."""
    return liste[sum(ord(ch) for ch in str(cle)) % len(liste)]


# store (rideau intérieur) devant une fenêtre éclairée, selon la couleur de la lumière
STORES = {"fenetre_chaude": "#E9C27E", "fenetre_froide": "bleu_pale", "fenetre_rose": "#E89CC4"}


def _fenetre(b, x0, x1, y0, y1, zf, lit, *, eteinte="vitre_bleue", lumiere="fenetre_chaude", meneau=True, store=True,
             cadre="metal_clair", h_store=0.32):
    """Fenêtre de la façade avant (plan zf, extérieur vers -Z) : vitre en saillie de 0,12 (Neon si éclairée),
    store à moitié baissé si elle est éclairée (0,22), meneau vertical au milieu (0,32). 1 à 3 pièces."""
    _vitre(b, (x0, y0, zf - 0.12), (x1, y1, zf), lit, eteinte=eteinte, lumiere=lumiere)
    if lit and store:
        _d(b, (x0 + 0.1, y1 - (y1 - y0) * h_store, zf - 0.22), (x1 - 0.1, y1 - 0.1, zf), STORES.get(lumiere, "creme"),
           name="Store")
    if meneau and x1 - x0 > 2.4:
        xm = (x0 + x1) / 2
        _d(b, (xm - 0.15, y0 - 0.1, zf - 0.32), (xm + 0.15, y1 + 0.1, zf), cadre, name="Meneau")


def _panneau_mural(b, g, y0, y1, za, zb, style, couleurs, *, mot=None, encre="blanc", fond="ecran_fond", eteint=False,
                   x_mur=None, s0=0.1):
    """Grande publicité sur les DEUX murs latéraux, au-dessus des voisins plus bas (vue en enfilade depuis la rue) :
    cadre traversant (saillie s0), image abstraite en blocs Neon traversants (s0 + 0,1) et accents (s0 + 0,2) ;
    style « mot » : deux plaques lumineuses (une par côté) portant un mot autorisé. x_mur = demi-largeur du mur
    (g.hw par défaut). Tout reste dans ±largeur / 2. 3 à 6 pièces.
    eteint : vieille réclame peinte (aucun Neon), pour la rue déserte."""
    hw = g.hw if x_mur is None else x_mur
    e1, e2, e3 = s0, s0 + 0.1, s0 + 0.2
    _d(b, (-hw - e1, y0, za), (hw + e1, y1, zb), fond, name="CadrePub", shadow=True)
    a0, a1, b0, b1 = za + 0.5, zb - 0.5, y0 + 0.5, y1 - 0.5
    W, H = a1 - a0, b1 - b0
    c1, c2, c3 = (list(couleurs) * 2)[:3]
    tr = dict(material="SmoothPlastic" if eteint else "Neon")
    if style == "mot":
        for s in (-1, 1):
            xa, xb_ = sorted((s * (hw + e1), s * (hw + e2)))
            p = _d(b, (xa, b0, a0), (xb_, b1, a1), c1, name="PubMot", **tr)
            _lab(p, mot or "カラオケ", encre, face="Right" if s > 0 else "Left", glow=None if eteint else 1.2,
                 vertical=H > W * 1.3)
        _d(b, (-hw - e2, b0 - 0.4, a0), (hw + e2, b0 - 0.1, a1), c2, name="PubTrait", **tr)
    elif style == "cercle":
        _d(b, (-hw - e2, b0, a0), (hw + e2, b1, a1), c1, name="PubFond", **tr)
        r = min(W, H) * 0.32
        zc, yc = a0 + W * 0.6, b0 + H * 0.55
        for (rz, ry) in ((r, r * 0.42), (r * 0.82, r * 0.82), (r * 0.42, r)):   # disque en pixels (trois paliers)
            _d(b, (-hw - e3, yc - ry, zc - rz), (hw + e3, yc + ry, zc + rz), c2, name="PubDisque", **tr)
        _d(b, (-hw - e3, b0 + H * 0.1, a0 + W * 0.08), (hw + e3, b0 + H * 0.2, a0 + W * 0.45), c3, name="PubTrait", **tr)
    elif style == "diagonale":              # fond et trois marches en diagonale
        _d(b, (-hw - e2, b0, a0), (hw + e2, b1, a1), c1, name="PubFond", **tr)
        for k in range(3):
            _d(b, (-hw - e3, b0 + H * (0.12 + 0.26 * k), a0 + W * (0.1 + 0.27 * k)),
               (hw + e3, b0 + H * (0.34 + 0.26 * k), a0 + W * (0.38 + 0.27 * k)), (c2, c3, c2)[k], name="PubMarche", **tr)
    elif style == "rayures":                # rayures verticales alternées et bandeau
        n = 4
        for k in range(n):
            _d(b, (-hw - e2, b0, a0 + k * W / n), (hw + e2, b1, a0 + (k + 1) * W / n), (c1, c2)[k % 2], name="PubRayure", **tr)
        _d(b, (-hw - e3, b0 + H * 0.4, a0 + W * 0.08), (hw + e3, b0 + H * 0.55, a1 - W * 0.08), c3, name="PubTrait", **tr)
    else:                                   # « bandes » : dégradé en trois bandes et un trait
        for k, cc in enumerate((c1, c2, c3)):
            _d(b, (-hw - e2, b1 - (k + 1) * H / 3, a0), (hw + e2, b1 - k * H / 3, a1), cc, name="PubBande", **tr)
        _d(b, (-hw - e3, b0 + H * 0.42, a0 + W * 0.12), (hw + e3, b0 + H * 0.52, a1 - W * 0.3),
           "neon_blanc" if not eteint else "beton_clair", name="PubTrait", **tr)


def _caisson_toit(b, x0, x1, y, z, h, texte, fond, encre, *, glow=1.1, eteint=False):
    """Petite enseigne de toit : deux pieds d'acier, caisson (lumineux ou éteint) face vers -Z et sa rampe (4 pièces).
    (x0, x1) = largeur, y = niveau du toit, z = plan avant du caisson."""
    for x in (x0 + 0.6, x1 - 0.6):
        b.box((x - 0.2, y, z + 0.5), (x + 0.2, y + h + 1.6, z + 0.9), col(ACIER), name="PiedCaisson")
    p = _d(b, (x0, y + 1.6, z), (x1, y + 1.6 + h, z + 0.5), fond, name="CaissonToit", shadow=True,
           material="SmoothPlastic" if eteint or not str(fond).startswith("neon") else "Neon")
    _lab(p, texte, encre, glow=None if eteint else glow)
    if not eteint:
        _n(b, (x0 + 0.3, y + 1.6 + h, z - 0.1), (x1 - 0.3, y + 1.85 + h, z + 0.4), "neon_blanc", name="RampeCaisson")
    return y + 1.85 + h


def _descente(b, g, y0, y1, cote=1):
    """Descente d'eau pluviale sur un mur latéral (en x = cote · hw), le long de la profondeur près de l'avant."""
    xa, xb_ = sorted((cote * g.hw, cote * (g.hw + 0.22)))
    _d(b, (xa, y0, g.zf + 0.6), (xb_, y1, g.zf + 0.95), "metal", name="DescenteCote")


def _fenetres_cotes(b, g, rng, niveaux, *, h0=2.6, h1=6.4, n=2, part=0.3, eteinte="vitre", lumiere="fenetre_chaude",
                    z0=None, z1=None, y_max=None):
    """Fenêtres des deux murs latéraux (blocs traversants : la même fenêtre sur les deux côtés), n par étage
    réparties en profondeur entre z0 et z1, environ une sur trois éclairée. Les étages qui montent au-dessus de
    y_max (une publicité murale) sont sautés. n pièces par étage."""
    z0 = g.zf + 2.0 if z0 is None else z0
    z1 = g.zb - 2.0 if z1 is None else z1
    L = (z1 - z0) / n
    for y0 in niveaux:
        if y_max is not None and y0 + h1 > y_max:
            continue
        for i in range(n):
            lit = bool(rng.random() < part)
            _bande_cotes(b, g, z0 + i * L + 0.5, z0 + (i + 1) * L - 0.5, y0 + h0, y0 + h1, lumiere if lit else eteinte,
                         material="Neon" if lit else "SmoothPlastic", name="FenetreCote")


# ---------------------------------------------------------------------------
# 1) Immeubles de la rue commerçante
# ---------------------------------------------------------------------------


def _vitrine(b, g, R, ys, mur_rdc, pilier, interieur, *, ep_pilier=1.0, saillie_pilier=0.25, socle="beton_fonce",
             verre=True, transparence=0.5, x_porte=None, porte_larg=3.2):
    """Rez-de-chaussée vitré en retrait de R : volume intérieur, piliers, fond éclairé, socle, vitrage, porte.
    `ys` = haut de la vitrine ; renvoie (xa, xb) l'intervalle vitré entre les piliers."""
    hw, zf, zb = g.hw, g.zf, g.zb
    b.box((-hw, 0, zf + R), (hw, ys, zb), mur_rdc, name="Rdc")
    xa, xb = -hw + ep_pilier, hw - ep_pilier
    for s in (-1, 1):
        x0, x1 = sorted((s * hw, s * (hw - ep_pilier)))
        b.box((x0, 0, zf - saillie_pilier), (x1, ys, zf + R), pilier, name="Pilier")
    _n(b, (xa, 0.4, zf + R - 0.1), (xb, ys, zf + R), interieur, name="Interieur")
    b.box((xa, 0, zf - 0.2), (xb, 0.4, zf + R - 0.1), c(socle), studs="top", name="Seuil")
    if verre:
        _d(b, (xa, 0.4, zf + 0.15), (xb, ys, zf + 0.25), "vitre_claire", transparency=transparence, name="Vitrine")
    if x_porte is not None:
        pa, pb = x_porte - porte_larg / 2, x_porte + porte_larg / 2
        for x in (pa, pb):
            _d(b, (x - 0.15, 0.4, zf + 0.05), (x + 0.15, ys, zf + 0.35), "metal_fonce", name="Montant")
        _d(b, (pa - 0.15, ys - 1.0, zf + 0.05), (pb + 0.15, ys - 0.7, zf + 0.35), "metal_fonce", name="Imposte")
    return xa, xb


def _ramen(b, g, enseigne, rng, panneau=False):
    """v0 ramen : étages en carrelage blanc à chaînes d'angle, rez à cadre rouge, noren, deux lampions, auvent,
    intérieur chaud, menu lumineux ; fenêtres à meneau et store ; caisson ラーメン sur le toit."""
    hw, zf, zb, yt = g.hw, g.zf, g.zb, g.yt
    mur = vr("carrelage", rng, 0.025)
    rouge = vr("noren_rouge", rng, 0.03)
    R, ys = 1.0, 7.5
    b.box((-hw, ys, zf), (hw, yt, zb), mur, studs="top", name="Corps")
    _vitrine(b, g, R, ys, shade(mur, 0.8), rouge, "fenetre_chaude", ep_pilier=1.2, saillie_pilier=0.3, verre=False)
    xa, xb = -hw + 1.2, hw - 1.2
    # devanture en bois : soubassements, vitres, porte coulissante au centre
    for s in (-1, 1):
        x0, x1 = sorted((s * 1.8, s * (hw - 1.2)))
        _d(b, (x0, 0.4, zf + 0.0), (x1, 2.6, zf + 0.4), BOIS_FONCE, name="Soubassement")
        _d(b, (x0, 2.6, zf + 0.15), (x1, ys, zf + 0.25), "vitre_claire", transparency=0.55, name="Vitre")
    _d(b, (-1.8, 0.4, zf + 0.15), (1.8, 6.6, zf + 0.25), "fenetre_chaude", transparency=0.35, name="Porte")
    _d(b, (-1.8, 6.6, zf + 0.0), (1.8, ys, zf + 0.4), BOIS_FONCE, name="Imposte")
    _d(b, (-0.12, 0.4, zf + 0.05), (0.12, 6.6, zf + 0.3), BOIS_FONCE, name="Montant")
    # menu lumineux plaqué devant la vitre de gauche (≤ 0,6)
    _d(b, (xa + 0.5, 2.9, zf - 0.3), (xa + 2.7, 5.9, zf + 0.15), BOIS_FONCE, name="CadreMenu")
    _n(b, (xa + 0.7, 3.1, zf - 0.42), (xa + 2.5, 5.7, zf - 0.3), "fenetre_chaude", name="Menu")
    # linteau rouge, tringle et noren en trois lés (texte sur celui du milieu)
    b.box((-hw, ys, zf - 0.3), (hw, 8.6, zf), rouge, name="Linteau")
    _d(b, (-2.6, 7.2, zf - 0.55), (2.6, ys, zf), BOIS_FONCE, name="Tringle")
    for k in range(3):
        x0 = -2.4 + k * 1.6
        p = _d(b, (x0 + 0.05, 4.4, zf - 0.5), (x0 + 1.55, 7.2, zf - 0.4), "noren_rouge" if k != 1 else shade(c("noren_rouge"), 0.9),
               name="Noren")
        if k == 1:
            _lab(p, enseigne, (250, 246, 236), vertical=True)
        else:
            _d(b, (x0 + 0.45, 6.0, zf - 0.6), (x0 + 1.15, 6.7, zf - 0.5), "enseigne_blanc", name="Motif")
    # auvent sombre à studs et lampions accrochés dessous
    b.wedge((-hw, 8.6, zf - 1.8), (hw, 9.7, zf), shade(c("anthracite"), 1.05), down="-z", studs="top", name="Auvent")
    _d(b, (-hw, 8.3, zf - 1.8), (hw, 8.6, zf - 1.55), "anthracite", name="Rive")
    for s in (-1, 1):
        x = s * (hw - 1.0)
        b.cyl((x, 7.75, zf - 1.1), 0.62, 1.1, c("lampion"), material="Neon", collide=False, shadow=False, name="Lampion")
        b.cyl((x, 8.45, zf - 1.1), 0.42, 0.3, c("noir"), collide=False, shadow=False, name="Coiffe")
        b.cyl((x, 7.1, zf - 1.1), 0.42, 0.2, c("noir"), collide=False, shadow=False, name="Coiffe")
    # enseigne horizontale lumineuse au-dessus de l'auvent
    p = _d(b, (xa + 0.4, 9.9, zf - 0.6), (xb - 0.4, 11.9, zf), "enseigne_noir", name="Enseigne", shadow=True)
    _lab(p, enseigne, "neon_jaune", glow=1.2)
    _n(b, (xa + 0.2, 9.75, zf - 0.7), (xb - 0.2, 9.9, zf), "neon_rouge", name="NeonEnseigne")
    # chaînes d'angle en carrelage plus sombre, qui retournent sur les côtés
    for s in (-1, 1):
        x0, x1 = sorted((s * (hw + 0.1), s * (hw - 0.7)))
        _d(b, (x0, 12.0, zf - 0.16), (x1, yt - 0.7, zf + 0.6), shade(mur, 0.9), name="Chaine")
    # étages : deux fenêtres à meneau par étage, appui et linteau filants, stores, climatiseurs
    allume = _allumage(rng, 2 * len(g.niveaux), 0.34)
    for k, y0 in enumerate(g.niveaux):
        wy0, wy1 = y0 + 3.2, y0 + 6.8
        _d(b, (xa + 0.1, wy0 - 0.4, zf - 0.45), (xb - 0.6, wy0, zf), "beton", name="Appui")
        _fenetre(b, xa + 0.4, -0.7, wy0, wy1, zf, allume[2 * k], eteinte="vitre_bleue")
        _fenetre(b, 0.7, xb - 0.9, wy0, wy1, zf, allume[2 * k + 1], eteinte="vitre_bleue",
                 lumiere=("fenetre_chaude", "fenetre_froide")[k % 2])
        _d(b, (xa + 0.1, wy1 + 0.1, zf - 0.25), (xb - 0.6, wy1 + 0.45, zf), shade(mur, 0.86), name="Linteau")
        if k in (1, 2):
            clim(b, (xa + 1.8) if k == 1 else (xb - 3.0), y0 + 0.7, zf, "-z")
    _fenetres_cotes(b, g, rng, g.niveaux, h0=3.2, h1=6.8, n=2, eteinte="vitre_bleue")
    _descente(b, g, 1.0, yt - 0.7, cote=-1)
    _drapeau(b, xb - 0.3, 12.4, zf, enseigne, variant=0, couleur="neon_rouge")
    _ceinture(b, -hw, hw, zf, zb, yt - 0.7, yt - 0.1, shade(mur, 0.9), s=0.2)
    top = _toit(b, g, rng, shade(mur, 0.93), avant_libre=True)
    if not panneau:
        cw = min(4.2, hw - 2.4)
        top = max(top, _caisson_toit(b, -cw, cw, yt, zf + 1.2, 2.4, enseigne, "auvent_rouge", "blanc"))
    return top


def _librairie(b, g, enseigne, rng, panneau=False):
    """v1 librairie : façade bleu ardoise, grande vitrine montrant les rayonnages, 本, rubans continus à meneaux
    filants et stores, un balcon ; publicité murale sur les côtés au-delà de 4 étages ; caisson 本 sur le toit."""
    hw, zf, zb, yt = g.hw, g.zf, g.zb, g.yt
    mur = vr("bleu_ardoise", rng, 0.04)
    cadre = vr("bleu_nuit", rng, 0.03)
    R, ys = 1.8, 7.4
    b.box((-hw, ys, zf), (hw, yt, zb), mur, studs="top", name="Corps")
    xa, xb = _vitrine(b, g, R, ys, shade(mur, 0.7), cadre, "fenetre_chaude", ep_pilier=0.8, transparence=0.6, x_porte=-1.2)
    # rayonnages : trois rangées de livres de couleurs, de part et d'autre de l'allée
    zl0, zl1 = zf + R - 0.7, zf + R - 0.1
    for r, y in enumerate((1.0, 3.0, 5.0)):
        for s, (x0, x1) in enumerate(((xa + 0.3, -3.2), (0.8, xb - 0.3))):
            _d(b, (x0, y, zl0), (x1, y + 1.3, zl1), LIVRES[(r * 2 + s + int(rng.integers(0, 3))) % len(LIVRES)], name="Livres")
    _d(b, (-2.6, 0.4, zf + 0.6), (0.2, 1.6, zf + 1.3), BOIS, name="Table")
    _d(b, (-2.4, 1.6, zf + 0.7), (0.0, 1.9, zf + 1.2), "auvent_jaune", name="Nouveautes")
    # présentoir à magazines devant la vitrine (≤ 0,6)
    _d(b, (xb - 4.2, 0, zf - 0.45), (xb - 0.6, 3.0, zf), "metal_clair", name="Presentoir", collide=True)
    for k, y in enumerate((0.8, 1.9)):
        _d(b, (xb - 4.0, y, zf - 0.6), (xb - 0.8, y + 0.8, zf - 0.45), ("auvent_rouge", "boisson_2")[k], name="Magazines")
    # bandeau blanc à liserés bleus, 本 en grand
    p = _d(b, (-hw, ys, zf - 0.7), (hw, 10.2, zf), "enseigne_blanc", name="Enseigne", shadow=True)
    _lab(p, enseigne, "auvent_bleu")
    _d(b, (-hw, 10.2, zf - 0.8), (hw, 10.5, zf), "auvent_bleu", name="Lisere")
    _n(b, (-hw + 0.8, ys - 0.2, zf - 0.8), (hw - 0.8, ys, zf - 0.25), "neon_cyan", name="NeonEnseigne")
    # publicité murale sur les deux côtés (au-dessus de la supérette voisine) si l'immeuble est haut
    pub = g.n >= 5
    ypub0, ypub1 = max(yt - 15.0, 26.0), yt - 2.0
    zpa, zpb = zf + 1.5, min(zb - 1.5, zf + 13.5)
    if pub:
        _panneau_mural(b, g, ypub0, ypub1, zpa, zpb, "bandes", ("ecran_bleu", "neon_cyan", "neon_jaune"))
    # étages : rubans continus, stores, bandeaux de plancher clairs, meneaux filants
    allume = _allumage(rng, len(g.niveaux), 0.35)
    for k, y0 in enumerate(g.niveaux):
        wy0, wy1 = y0 + 2.4, y0 + 6.4
        _vitre(b, (xa, wy0, zf - 0.12), (xb, wy1, zf), allume[k], eteinte="vitre_claire", lumiere="fenetre_chaude")
        if allume[k]:
            _d(b, (xa + 0.1, wy1 - 1.4, zf - 0.22), (xb - 0.1, wy1 - 0.1, zf), STORES["fenetre_chaude"], name="Store")
        if k > 0 and pub and ypub0 - 0.6 < y0 < ypub1 + 0.6:
            # bandeau avant seulement (retour de 1,2 sur l'angle) : il ne traverse pas la publicité murale
            _d(b, (-hw - 0.2, y0 - 0.4, zf - 0.2), (hw + 0.2, y0 + 0.4, zf + 1.2), "beton_clair", name="Bandeau")
        elif k > 0:
            _ceinture(b, -hw, hw, zf, zb, y0 - 0.4, y0 + 0.4, "beton_clair", s=0.2)
    _fenetres_cotes(b, g, rng, g.niveaux, h0=2.4, h1=6.4, n=2, eteinte="vitre_bleue", part=0.35,
                    y_max=ypub0 if pub else None)
    nm = 3 if xb - xa >= 12.0 else 2
    pas_m = (xb - xa) / (nm + 1)
    for x in np.linspace(xa, xb, nm + 2)[1:-1]:
        _bande_face(b, g, x - 0.2, x + 0.2, 10.5, yt - 0.1, cadre, s=0.3, name="Meneau")
    # balcon au dernier étage : dalle à studs, garde-corps vitré, main courante
    y0 = g.niveaux[-1]
    b.box((xa, y0, zf - 1.8), (xb, y0 + 0.5, zf), shade(c("beton_clair"), 0.95), studs="top", name="Balcon")
    _d(b, (xa, y0 + 0.5, zf - 1.8), (xb, y0 + 2.6, zf - 1.6), "vitre_claire", transparency=0.45, name="GardeCorps")
    _d(b, (xa, y0 + 2.6, zf - 1.85), (xb, y0 + 2.85, zf - 1.55), "metal_clair", name="MainCourante")
    for x in (xa + 0.1, xb - 0.3):
        _d(b, (x, y0 + 0.5, zf - 1.6), (x + 0.2, y0 + 2.6, zf - 0.3), "metal_clair", name="GardeCorpsCote")
    clim(b, xa + 0.5 * pas_m, y0 + 0.75, zf, "-z")
    if g.n >= 4:
        clim(b, xb - 0.5 * pas_m, g.niveaux[1] + 0.5, zf, "-z")
    _descente(b, g, 1.0, yt - 0.7, cote=1)
    _drapeau(b, xa + 0.2, 11.2, zf, enseigne, variant=1, couleur="neon_bleu", hauteur=6.0)
    _ceinture(b, -hw, hw, zf, zb, yt - 0.7, yt - 0.1, cadre, s=0.2)
    top = _toit(b, g, rng, shade(mur, 0.9), avant_libre=True)
    if not panneau:
        cw = min(3.6, hw - 2.4)
        top = max(top, _caisson_toit(b, -cw, cw, yt, zf + 1.2, 2.6, enseigne, "enseigne_blanc", "auvent_bleu"))
    return top


def _pharmacie(b, g, enseigne, rng, panneau=False):
    """v2 pharmacie : corps crème, grand bandeau jaune et bleu au 薬 géant, présentoirs colorés, très éclairée ;
    rubans à meneaux et stores, caisson 薬 jaune sur le toit."""
    hw, zf, zb, yt = g.hw, g.zf, g.zb, g.yt
    mur = vr("creme", rng, 0.025)
    R, ys = 1.4, 7.0
    b.box((-hw, ys, zf), (hw, yt, zb), mur, studs="top", name="Corps")
    xa, xb = _vitrine(b, g, R, ys, shade(mur, 0.8), c("blanc"), "fenetre_froide", ep_pilier=0.8, transparence=0.55,
                      x_porte=0.0, porte_larg=3.6)
    # rayons de produits derrière la vitrine
    for r, y in enumerate((1.2, 3.4)):
        for s, (x0, x1) in enumerate(((xa + 0.3, -2.2), (2.2, xb - 0.3))):
            _d(b, (x0, y, zf + R - 0.7), (x1, y + 1.6, zf + R - 0.1), PRODUITS[(2 * r + s + 1) % len(PRODUITS)], name="Produits")
    # présentoirs dehors, plaqués contre la vitrine (≤ 0,6)
    for s in (-1, 1):
        x0, x1 = sorted((s * 2.2, s * (hw - 0.9)))
        _d(b, (x0, 0, zf - 0.45), (x1, 3.8, zf), "blanc", name="Presentoir", collide=True)
        for k, y in enumerate((0.5, 1.6, 2.7)):
            _d(b, (x0 + 0.2, y, zf - 0.6), (x1 - 0.2, y + 0.8, zf - 0.45), PRODUITS[(k * 2 + (s > 0)) % len(PRODUITS)],
               name="Produits")
        _d(b, (x0 + 0.4, 3.8, zf - 0.5), (x0 + 1.6, 4.9, zf - 0.4), "auvent_jaune", name="Affichette")
    # grand bandeau : bleu (lumineux) puis jaune avec 薬 géant
    _d(b, (-hw, 7.0, zf - 0.9), (hw, 7.8, zf), "auvent_bleu", name="BandeauBleu", shadow=True)
    _n(b, (-hw + 0.2, 7.25, zf - 1.0), (hw - 0.2, 7.55, zf - 0.9), "neon_blanc", name="NeonBandeau")
    p = _d(b, (-hw, 7.8, zf - 0.8), (hw, 12.2, zf), "auvent_jaune", name="Enseigne", shadow=True)
    _lab(p, enseigne, "auvent_bleu")
    _d(b, (-hw, 12.2, zf - 0.9), (hw, 12.5, zf), "auvent_bleu", name="Lisere")
    # étages : rubans clairs (beaucoup d'allumés) à stores, appuis blancs, meneaux filants
    allume = _allumage(rng, len(g.niveaux), 0.45)
    for k, y0 in enumerate(g.niveaux):
        wy0, wy1 = (max(y0 + 2.6, 13.4), y0 + 6.6)
        if wy1 - wy0 < 1.5:
            continue
        _d(b, (xa + 0.3, wy0 - 0.35, zf - 0.4), (xb - 0.3, wy0, zf), "blanc", name="Appui")
        _vitre(b, (xa + 0.6, wy0, zf - 0.12), (xb - 0.6, wy1, zf), allume[k], eteinte="vitre_bleue", lumiere="fenetre_froide")
        if allume[k]:
            _d(b, (xa + 0.7, wy1 - 1.2, zf - 0.22), (xb - 0.7, wy1 - 0.1, zf), STORES["fenetre_froide"], name="Store")
    _fenetres_cotes(b, g, rng, g.niveaux[1:], h0=2.6, h1=6.6, n=2, eteinte="vitre_bleue", lumiere="fenetre_froide", part=0.4)
    for x in (-hw / 3, hw / 3):
        _bande_face(b, g, x - 0.2, x + 0.2, 12.5, yt - 0.1, "blanc", s=0.3, name="Meneau")
    if g.n >= 4:
        clim(b, xa + 1.6, g.niveaux[2] + 0.7, zf, "-z")
    clim(b, xb - 3.2, g.niveaux[-1] + 0.7, zf, "-z")
    _descente(b, g, 1.0, yt - 0.7, cote=-1)
    _drapeau(b, xb - 0.1, 13.0, zf, enseigne, variant=1, couleur="neon_bleu", hauteur=5.5)
    _ceinture(b, -hw, hw, zf, zb, yt - 0.7, yt - 0.1, c("blanc"), s=0.2)
    top = _toit(b, g, rng, shade(mur, 0.92), avant_libre=True)
    if not panneau:
        cw = min(3.4, hw - 2.4)
        top = max(top, _caisson_toit(b, -cw, cw, yt, zf + 1.2, 3.0, enseigne, "auvent_jaune", "auvent_bleu"))
    return top


def _divertissement(b, g, enseigne, rng, panneau=False):
    """v3 karaoké / cinéma : façade bleu nuit, grande lame au néon sur plusieurs étages, une ligne de néon par étage
    (qui tourne sur l'angle), fenêtres colorées éclairées, marquise lumineuse, grande publicité lumineuse sur les
    deux murs latéraux au-dessus des voisins."""
    hw, zf, zb, yt = g.hw, g.zf, g.zb, g.yt
    mur = vr("bleu_nuit", rng, 0.04)
    cinema = "映画" in enseigne
    neon = "neon_cyan" if cinema else "neon_magenta"
    neon2 = "neon_jaune" if cinema else "neon_cyan"
    R, ys = 1.6, 7.2
    b.box((-hw, ys, zf), (hw, yt, zb), mur, studs="top", name="Corps")
    xa, xb = _vitrine(b, g, R, ys, shade(mur, 0.8), shade(mur, 0.8), "fenetre_rose" if not cinema else "fenetre_chaude",
                      ep_pilier=1.2, transparence=0.5, x_porte=0.0, porte_larg=5.0)
    # affiches (cinéma) ou vitrines lumineuses (karaoké) sur les côtés de l'entrée
    for s in (-1, 1):
        x0, x1 = sorted((s * 3.4, s * (3.4 + min(3.2, hw - 5.2))))
        _d(b, (x0 - 0.2, 1.0, zf - 0.3), (x1 + 0.2, 6.2, zf + 0.15), "metal_fonce", name="CadreAffiche")
        cc = ("ecran_rose", "ecran_orange") if s < 0 else ("ecran_bleu", "neon_jaune")
        _n(b, (x0, 1.2, zf - 0.45), (x1, 6.0, zf - 0.3), cc[0], name="Affiche")
        _n(b, (x0 + 0.5, 2.0, zf - 0.55), (x1 - 0.5, 3.6, zf - 0.45), cc[1], name="AfficheMotif")
    # marquise : dalle à studs, bandeau lumineux, ampoules, dessous éclairé
    ma, mb = -min(hw - 3.0, 7.0), min(hw - 3.0, 7.0)
    b.box((ma, 8.2, zf - 3.2), (mb, 9.2, zf), shade(c("anthracite"), 1.1), studs="top", name="Marquise")
    p = _n(b, (ma, 8.2, zf - 3.4), (mb, 9.2, zf - 3.2), "fenetre_chaude", name="BandeauMarquise")
    _lab(p, enseigne, "bordeaux")
    _n(b, (ma + 0.4, 8.0, zf - 3.0), (mb - 0.4, 8.2, zf - 0.4), "neon_blanc", name="DessousMarquise")
    nb = int((mb - ma) // 1.6)
    for k in range(nb):
        x = ma + (k + 0.5) * (mb - ma) / nb
        _n(b, (x - 0.2, 7.45, zf - 3.55), (x + 0.2, 7.85, zf - 3.15), neon2, name="Ampoule")
    _d(b, (ma, 7.85, zf - 3.4), (mb, 8.2, zf - 3.1), "metal_fonce", name="Rail")
    # publicité lumineuse sur les deux murs latéraux, en haut
    ypub0, ypub1 = max(yt - 19.0, 27.0), yt - 1.6
    zpa, zpb = zf + 1.6, min(zb - 1.5, zf + 1.6 + 14.0)
    _panneau_mural(b, g, ypub0, ypub1, zpa, zpb, "cercle" if cinema else "bandes",
                   ("ecran_bleu", "neon_jaune", "neon_cyan") if cinema else ("ecran_rose", "neon_magenta", "ecran_orange"))
    # étages : ligne de néon à chaque étage (avant + retour sur l'angle), fenêtres colorées, meneaux
    couleurs = ["fenetre_rose", "vitre_cyan", "vitre", "fenetre_rose", "vitre_cyan", "vitre"]
    dec = int(rng.integers(0, 3))
    xw0 = -hw + 3.0
    for k, y0 in enumerate(g.niveaux):
        _n(b, (-hw - 0.18, y0 + 0.05, zf - 0.18), (hw + 0.18, y0 + 0.35, zf + 1.2), neon if k % 2 == 0 else neon2,
           name="LigneNeon")
        cc = couleurs[(k + dec) % len(couleurs)]
        lit = cc != "vitre"
        wy0, wy1 = y0 + 2.0, y0 + 6.2
        if k == 0:
            wy0 = 10.4
        _d(b, (xw0, wy0, zf - 0.12), (xb, wy1, zf), cc, material="Neon" if lit else "SmoothPlastic", name="Fenetre")
        cs = couleurs[(k + dec + 1) % len(couleurs)]
        mat = "Neon" if cs != "vitre" else "SmoothPlastic"
        if y0 + 5.8 <= ypub0:
            _bande_cotes(b, g, zf + 2.0, zb - 2.0, y0 + 2.4, y0 + 5.8, cs, material=mat, name="FenetreCote")
        elif zb - 2.0 - zpb > 3.0:
            _bande_cotes(b, g, zpb + 0.8, zb - 2.0, y0 + 2.4, y0 + 5.8, cs, material=mat, name="FenetreCote")
    for x in np.linspace(xw0, xb, 5)[1:-1]:
        _bande_face(b, g, x - 0.2, x + 0.2, 9.4, yt - 0.6, shade(mur, 0.75), s=0.26, name="Meneau", arriere=False)
    # grande lame au néon (plusieurs étages) côté gauche, enseigne en drapeau côté droit
    hl = min(yt - 13.0, max(14.0, 4.6 * len(enseigne) + 3.5))
    _lame(b, -hw + 1.4, 11.0, 11.0 + hl, zf - 0.4, zf - 3.75, enseigne, shade(c(neon), 0.55), "blanc", neon)
    _drapeau(b, xb - 0.4, 11.0, zf, enseigne, variant=2, couleur=neon2)
    clim(b, 2.0, g.niveaux[1] + 0.6, zf, "-z")
    clim(b, xb - 3.6, g.niveaux[-1] + 0.6, zf, "-z")
    _ceinture(b, -hw, hw, zf, zb, yt - 0.8, yt - 0.1, shade(mur, 1.25), s=0.24)
    top = _toit(b, g, rng, shade(mur, 1.2), avant_libre=True)
    if not panneau:
        cw = min(5.0, hw - 2.4)
        top = max(top, _caisson_toit(b, -cw, cw, yt, zf + 1.2, 3.0, enseigne, shade(c(neon), 0.6), "blanc", glow=1.3))
    return top


def _graffiti(b, x0, x1, y0, y1, z, rng):
    """Taches de tags abstraites (aucune lettre) : aplats, contour et zigzag en blocs inclinés."""
    W, H = x1 - x0, y1 - y0
    cols = ["graffiti_1", "graffiti_2", "graffiti_3"]
    k0 = int(rng.integers(0, 3))
    # grande tache : contour (moins saillant) + aplat
    cx, cy = x0 + W * float(rng.uniform(0.3, 0.45)), y0 + H * 0.45
    _d(b, (cx - W * 0.22, cy - H * 0.28, z - 0.12), (cx + W * 0.22, cy + H * 0.26, z), cols[(k0 + 1) % 3], name="Tag")
    _d(b, (cx - W * 0.18, cy - H * 0.2, z - 0.24), (cx + W * 0.18, cy + H * 0.18, z - 0.12), cols[k0], name="Tag")
    _d(b, (cx - W * 0.1, cy + H * 0.18, z - 0.24), (cx + W * 0.06, cy + H * 0.34, z - 0.12), cols[k0], name="Tag")
    # zigzag : quatre traits inclinés
    zx, zy = x0 + W * 0.62, y0 + H * 0.3
    for k in range(4):
        ang = 40 if k % 2 == 0 else -40
        b.part("block", (W * 0.11, 0.35, 0.1), (zx + k * W * 0.075, zy + H * 0.12, z - 0.16),
               np.array([[math.cos(math.radians(ang)), -math.sin(math.radians(ang)), 0],
                         [math.sin(math.radians(ang)), math.cos(math.radians(ang)), 0], [0, 0, 1]]),
               col(cols[(k0 + 2) % 3]), collide=False, shadow=False, name="Zigzag")
    # petites taches
    for k in range(2):
        px = x0 + W * float(rng.uniform(0.05, 0.9))
        py = y0 + H * float(rng.uniform(0.65, 0.85))
        _d(b, (px - 0.5, py - 0.35, z - 0.16 - 0.1 * k), (px + 0.5, py + 0.35, z), cols[(k0 + k) % 3], name="Tag")


def _boutique_fermee(b, g, enseigne, rng, panneau=False):
    """v4 boutique fermée : rideaux métalliques baissés et tagués, petite enseigne, étages en brique avec balcons
    et perches à linge (la rue déserte) ; vieille réclame peinte délavée sur les côtés, caisson de toit éteint."""
    hw, zf, zb, yt = g.hw, g.zf, g.zb, g.yt
    mur = vr("brique", rng, 0.04)
    gris = vr("beton_fonce", rng, 0.03)
    ys = 7.4
    b.box((-hw, ys, zf), (hw, yt, zb), mur, studs="top", name="Corps")
    b.box((-hw, 0, zf + 0.4), (hw, ys, zb), shade(gris, 0.85), name="Rdc")
    # trois piliers et deux rideaux (grand à gauche, petit à droite)
    xm = hw - 7.0
    for x0, x1 in ((-hw, -hw + 1.0), (xm - 0.5, xm + 0.5), (hw - 1.0, hw)):
        b.box((x0, 0, zf - 0.25), (x1, ys, zf + 0.4), gris, name="Pilier")
    for x0, x1 in ((-hw + 1.0, xm - 0.5), (xm + 0.5, hw - 1.0)):
        b.box((x0, 0, zf - 0.1), (x1, 6.6, zf + 0.4), c("rideau_metal"), name="Rideau")
        _d(b, (x0, 6.6, zf - 0.5), (x1, ys, zf + 0.4), "rideau_fonce", name="Coffre", shadow=True)
        _d(b, (x0 + 0.3, 0, zf - 0.22), (x1 - 0.3, 0.3, zf - 0.1), "metal_fonce", name="Lame")
    for y in (1.6, 3.0, 4.4, 5.8):
        _d(b, (-hw + 1.0, y, zf - 0.2), (hw - 1.0, y + 0.15, zf - 0.1), "rideau_fonce", name="Nervure")
    _graffiti(b, -hw + 1.4, xm - 1.0, 0.4, 6.2, zf - 0.1, rng)
    _d(b, (xm + 1.4, 1.0, zf - 0.22), (xm + 3.4, 2.4, zf - 0.1), "graffiti_2", name="Tag")
    _d(b, (xm + 2.8, 2.0, zf - 0.28), (xm + 5.2, 2.8, zf - 0.1), "graffiti_1", name="Tag")
    # petite enseigne en bois et bandeau
    p = _d(b, (-hw + 1.6, 7.8, zf - 0.4), (-hw + 6.4, 9.6, zf), BOIS_FONCE, name="Enseigne", shadow=True)
    _lab(p, enseigne, (240, 232, 214))
    _d(b, (-hw + 1.6, ys, zf - 0.3), (hw - 1.6, 7.75, zf), "metal_fonce", name="Bandeau")
    # vieille réclame peinte, délavée, sur les deux murs latéraux (immeuble plus haut que ses voisins)
    pub = g.n >= 5
    ypub0, ypub1 = max(yt - 14.0, 33.0), yt - 2.0
    zpa, zpb = zf + 1.4, min(zb - 1.5, zf + 12.4)
    if pub:
        fade = lambda n: mix(c(n), c("beton_clair"), 0.45)  # noqa: E731
        _panneau_mural(b, g, ypub0, ypub1, zpa, zpb, "bandes", (fade("auvent_bleu"), fade("auvent_jaune"), fade("auvent_rouge")),
                       fond=shade(c("beton"), 0.9), eteint=True)
    # étages : balcons à gauche (perche à linge), fenêtres et climatiseurs à droite
    xbal = 1.0
    linge = ["blanc", "boisson_2", "auvent_rouge", "neon_rose", "auvent_jaune"]
    for k, y0 in enumerate(g.niveaux):
        wy0 = y0 + 1.0 if k > 0 else 10.0
        allumee = bool(rng.random() < 0.3)
        _vitre(b, (-hw + 1.4, wy0, zf - 0.12), (xbal - 0.6, y0 + 6.6, zf), allumee, eteinte="vitre", lumiere="fenetre_chaude")
        b.box((-hw + 0.8, y0, zf - 1.8), (xbal, y0 + 0.5, zf), shade(c("beton_clair"), 0.95), studs="top", name="Balcon")
        _d(b, (-hw + 0.8, y0 + 0.5, zf - 1.8), (xbal, y0 + 2.8, zf - 1.5), "beton_clair", name="Allege", shadow=True,
           studs="top")
        # perche à linge et linge
        _d(b, (-hw + 1.2, y0 + 5.2, zf - 1.3), (-hw + 1.4, y0 + 5.6, zf), "metal", name="Bras")
        _d(b, (xbal - 0.6, y0 + 5.2, zf - 1.3), (xbal - 0.4, y0 + 5.6, zf), "metal", name="Bras")
        b.cyl(((-hw + 1.2 + xbal - 0.4) / 2, y0 + 5.5, zf - 1.2), 0.08, xbal + hw - 1.6, c("metal_clair"), axis="x",
              collide=False, shadow=False, name="Perche")
        xc = -hw + 2.0
        for j in range(2):
            ll = float(rng.uniform(1.0, 1.8))
            lx = xc + float(rng.uniform(0.0, 0.8))
            xc = lx + ll + 0.3
            if lx + ll > xbal - 0.6:
                break
            _d(b, (lx, y0 + 5.4 - ll * 1.1, zf - 1.26), (lx + ll, y0 + 5.42, zf - 1.14), linge[(k + j) % len(linge)], name="Linge")
        # fenêtres côté droit (meneau, store si éclairée)
        _d(b, (xbal + 1.0, y0 + 2.4, zf - 0.4), (hw - 1.5, y0 + 2.75, zf), "beton_clair", name="Appui")
        _fenetre(b, xbal + 1.3, hw - 1.8, y0 + 2.75, y0 + 6.4, zf, bool(rng.random() < 0.3), eteinte="vitre_bleue",
                 cadre="beton_clair")
        if k % 2 == 1:
            clim(b, min(xbal + 3.0 + (k % 3) * 2.0, hw - 2.8), y0 + 0.4, zf, "-z")
    _fenetres_cotes(b, g, rng, g.niveaux, h0=2.75, h1=6.4, n=2, eteinte="vitre", part=0.15,
                    y_max=ypub0 if pub else None)
    # chaînages en béton aux angles de la façade
    for s in (-1, 1):
        x0, x1 = sorted((s * hw, s * (hw - 0.8)))
        _d(b, (x0, ys, zf - 0.35), (x1, yt, zf), shade(mur, 0.8), name="Chainage")
    _descente(b, g, 1.0, yt - 0.7, cote=1)
    _drapeau(b, hw - 0.7, 10.5, zf, enseigne, variant=0, couleur="neon_orange")
    _ceinture(b, -hw, hw, zf, zb, yt - 0.8, yt - 0.1, "beton_clair", s=0.2)
    top = _toit(b, g, rng, shade(c("beton"), 0.95), avant_libre=not panneau)
    if not panneau:
        # vieux caisson de toit éteint (le restaurant est fermé)
        cw = min(4.0, hw - 2.4)
        top = max(top, _caisson_toit(b, -cw, cw, yt, zf + 1.2, 2.4, enseigne, mix(c("enseigne_blanc"), c("beton"), 0.5),
                                     mix(c("bordeaux"), c("beton"), 0.3), eteint=True))
    return top


def _crayon(b, g, enseigne, rng, panneau=False):
    """v5 immeuble « crayon » : étroit et haut, une enseigne horizontale de couleur par étage, enseigne en drapeau,
    escalier de secours extérieur sur un côté (dans la largeur), cadre d'enseigne sur le toit (ou écran si
    panneau), grande enseigne murale verticale sur les deux côtés."""
    hw, zf, zb, yt = g.hw, g.zf, g.zb, g.yt
    mur = vr(_choix(["beton_clair", "bleu_acier", "gris_chaud", "bleu_pale"], enseigne), rng, 0.03)
    xe = hw - 3.0          # l'escalier occupe x ∈ [xe, hw], z ∈ [zf, zf + pe]
    pe = 5.0
    ys = 7.4
    # volumes : corps avant (hors escalier) et arrière (pleine largeur)
    b.box((-hw, ys, zf), (xe, yt, zf + pe), mur, studs="top", name="Corps")
    b.box((-hw, 0, zf + pe), (hw, yt, zb), mur, studs="top", name="Corps")
    b.box((-hw, 0, zf + 1.0), (xe, ys, zf + pe), shade(mur, 0.75), name="Rdc")
    # rez : petite vitrine éclairée, piliers, enseigne
    for x0, x1 in ((-hw, -hw + 0.7), (xe - 0.7, xe)):
        b.box((x0, 0, zf - 0.2), (x1, ys, zf + 1.0), shade(mur, 0.85), name="Pilier")
    _n(b, (-hw + 0.7, 0.4, zf + 0.9), (xe - 0.7, ys, zf + 1.0), "fenetre_chaude", name="Interieur")
    _d(b, (-hw + 0.7, 0.4, zf + 0.15), (xe - 0.7, ys, zf + 0.25), "vitre_claire", transparency=0.5, name="Vitrine")
    _d(b, (-hw + 0.7, 0, zf - 0.1), (xe - 0.7, 0.4, zf + 0.9), "beton_fonce", name="Seuil")
    p = _d(b, (-hw, ys, zf - 0.8), (xe, 9.4, zf), "enseigne_noir", name="Enseigne", shadow=True)
    _lab(p, enseigne, "neon_jaune", glow=1.2)
    # enseignes d'étage : chacune une couleur, un mot autorisé
    dec = sum(ord(ch) for ch in enseigne)
    reste = [m for m in MOTS if m != enseigne]
    reste = reste[dec % len(reste):] + reste[:dec % len(reste)]
    mots = [enseigne] + reste
    fonds = [("auvent_rouge", "blanc"), ("enseigne_blanc", "auvent_bleu"), ("auvent_jaune", "noir"), ("auvent_bleu", "blanc"),
             ("neon_rose", "noir"), ("enseigne_noir", "neon_cyan"), ("neon_orange", "noir"), ("enseigne_blanc", "auvent_rouge")]
    fdec = dec % len(fonds)
    # grande enseigne murale verticale sur les deux côtés (en arrière de l'escalier)
    ypub0, ypub1 = max(yt - 24.0, 30.0), yt - 1.6
    zpa, zpb = zf + pe + 0.8, zb - 1.2
    pub = ypub1 - ypub0 >= 8.0
    if pub:
        _panneau_mural(b, g, ypub0, ypub1, zpa, zpb, "mot",
                       (_choix(["ecran_rose", "ecran_bleu", "ecran_orange"], enseigne + "m"), "neon_blanc"),
                       mot=[m for m in mots[1:] if len(m) >= 2][1])
    allume = _allumage(rng, len(g.niveaux), 0.35)
    for k, y0 in enumerate(g.niveaux):
        _vitre(b, (-hw + 0.8, y0 + 0.9, zf - 0.12), (xe - 0.8, y0 + 4.4, zf), allume[k], eteinte="vitre_bleue")
        fond, encre = fonds[(k + fdec) % len(fonds)]
        _d(b, (-hw + 1.6, y0 + 4.7, zf - 0.7), (xe - 0.3, y0 + 7.5, zf), "metal_fonce", name="CadreEnseigne")
        p = _d(b, (-hw + 1.8, y0 + 4.85, zf - 0.95), (xe - 0.5, y0 + 7.35, zf - 0.7), fond,
               material="Neon" if fond.startswith("neon") else "SmoothPlastic", name="EnseigneEtage")
        _lab(p, mots[(k + 1) % len(mots)], encre, glow=1.1)
        cs = "fenetre_chaude" if allume[-1 - k] else "vitre"
        mat = "Neon" if allume[-1 - k] else "SmoothPlastic"
        if not pub or y0 + 5.4 <= ypub0:
            _bande_cotes(b, g, zf + pe + 1.0, zb - 1.0, y0 + 1.6, y0 + 5.4, cs, material=mat, name="FenetreCote")
    # escalier de secours : paliers, garde-corps pleins, volées alternées, poteau d'angle
    acier = col(ACIER)
    for k, y0 in enumerate(g.niveaux):
        b.box((xe, y0 - 0.35, zf), (hw, y0, zf + pe), shade(acier, 1.1), studs="top", name="Palier")
        _d(b, (xe, y0, zf), (hw - 0.35, y0 + 2.4, zf + 0.15), acier, name="GardeCorps", shadow=True)
        _d(b, (hw - 0.15, y0, zf + 0.35), (hw, y0 + 2.4, zf + pe), acier, name="GardeCorps", shadow=True)
    for k in range(len(g.niveaux)):
        ya = 0.4 if k == 0 else g.niveaux[k - 1]
        yb = g.niveaux[k]
        za, zb_ = (zf + pe - 0.3, zf + 0.4) if k % 2 == 0 else (zf + 0.4, zf + pe - 0.3)
        L = math.hypot(yb - ya, zb_ - za)
        ang = math.degrees(math.atan2(-(yb - ya), zb_ - za))
        b.part("block", (1.2, 0.3, L), ((xe + hw) / 2 - 0.4, (ya + yb) / 2, (za + zb_) / 2), rot_x(ang), shade(acier, 0.9),
               collide=False, name="Volee")
    _d(b, (hw - 0.4, 0, zf - 0.15), (hw + 0.1, yt + 1.0, zf + 0.35), acier, name="Poteau", shadow=True)
    _d(b, (xe + 0.4, 0, zf + pe - 0.12), (hw - 0.6, 6.4, zf + pe), "metal_fonce", name="PorteSecours")
    _drapeau(b, -hw + 0.75, 10.0, zf, enseigne, variant=int(dec) % 3, couleur=_choix(["neon_magenta", "neon_cyan", "neon_jaune"], enseigne),
             hauteur=min(yt - 12.0, 3.0 + 2.6 * len(enseigne)))
    for k in (1, len(g.niveaux) - 1):
        clim(b, (xe + hw) / 2, g.niveaux[k] + 0.25, zf + pe, "-z")
    _ceinture(b, -hw, hw, zf + pe, zb, yt - 0.7, yt - 0.1, shade(mur, 0.85), s=0.2)
    _d(b, (-hw - 0.2, yt - 0.7, zf - 0.2), (xe + 0.2, yt - 0.1, zf + pe), shade(mur, 0.85), name="Corniche")
    # toit : acrotère, cadre d'enseigne en acier (ou écran), citerne, antenne
    _acrotere(b, -hw, hw, zf + pe, zb, yt, shade(mur, 0.9))
    top = yt + ACRO
    fa, fb = -hw + 0.6, xe - 0.4
    if panneau:
        top = max(top, _panneau_toit(b, fa, fb, yt, zf + 0.6, min(6.0, (fb - fa) * 0.7), "cercle",
                                     ("ecran_bleu", "neon_jaune", "neon_cyan"), pied=1.2))
    else:
        for x in (fa + 0.3, fb - 0.3):
            b.box((x - 0.2, yt, zf + 0.6), (x + 0.2, yt + 6.2, zf + 1.0), acier, name="MontantCadre")
        fond, encre = _choix([("auvent_rouge", "blanc"), ("auvent_bleu", "neon_jaune"), ("enseigne_blanc", "auvent_rouge")], enseigne + "toit")
        p = _d(b, (fa, yt + 2.4, zf + 0.2), (fb, yt + 5.8, zf + 0.6), fond, name="EnseigneToit", shadow=True)
        _lab(p, enseigne, encre, glow=1.1)
        _n(b, (fa, yt + 5.8, zf + 0.2), (fb, yt + 6.1, zf + 0.6), "neon_blanc", name="RampeCadre")
        top = max(top, yt + 6.2)
    top = max(top, _citerne(b, hw - 2.0, yt, zb - 2.6, r=1.3, h=2.6))
    _clim_toit(b, -hw + 2.0, yt, zb - 2.0)
    top = max(top, _antenne(b, -hw + 1.6, yt, zf + pe + 1.6, h=6.0))
    b.box((-hw, yt, zf), (xe, yt + 0.6, zf + pe), shade(mur, 0.9), studs="top", name="DalleAvant")
    return top


def immeuble_boutique(b, variant=0, largeur=16, profondeur=20, etages=4, enseigne="ラーメン", panneau_toit=False):
    """Petit immeuble de la rue commerçante : boutique au rez-de-chaussée (9 de haut), étages de 8, acrotère de 1,5.
    variant % 6 : 0 ramen, 1 librairie, 2 pharmacie, 3 karaoké / cinéma, 4 boutique fermée, 5 immeuble « crayon ».
    panneau_toit : panneau publicitaire sur le toit (écran abstrait ou mot autorisé, ≤ 15 pièces) ; sinon un
    petit caisson d'enseigne (ou le cadre d'enseigne du « crayon »)."""
    n0 = len(b.parts)
    v = variant % 6
    g = _G(largeur, profondeur, max(2, int(etages)))
    rng = b.rng
    {0: _ramen, 1: _librairie, 2: _pharmacie, 3: _divertissement, 4: _boutique_fermee, 5: _crayon}[v](
        b, g, enseigne, rng, panneau=bool(panneau_toit))
    if panneau_toit and v != 5:
        pw = min(g.w - 3.0, 18.0)
        style = ("bandes", "cercle", "mot", "diagonale")[(v + len(enseigne)) % 4]
        cols = (("ecran_rose", "neon_jaune", "ecran_orange"), ("ecran_bleu", "neon_cyan", "neon_blanc"))[(len(enseigne) + v) % 2]
        _panneau_toit(b, -pw / 2, pw / 2, g.yt, g.zf + 1.4, min(7.0, pw * 0.42), style, cols, mot=enseigne if style == "mot" else None)
    return {"emprise": (float(largeur), float(profondeur)), "hauteur": _hauteur(b, n0)}


# ---------------------------------------------------------------------------
# 2) Supérette 24 h
# ---------------------------------------------------------------------------

RAYURES = {
    # combinaisons inventées (jamais celles des vraies chaînes)
    0: ("neon_violet", "neon_cyan", "blanc"),
    1: ("neon_magenta", "neon_jaune", "blanc"),
    2: ("neon_orange", "neon_bleu", "blanc"),
}


def superette(b, variant=0, largeur=24, profondeur=20, panneau_toit=False):
    """Supérette ouverte 24 h sur 24 : rez de 10 entièrement vitré (fond éclairé froid, rayons colorés, porte
    automatique au centre, affichettes abstraites sur le verre), bandeau à trois rayures de couleurs inventées qui
    tourne sur les côtés, caissons lumineux コンビニ et 24H, puis un (v1) ou deux (v0, v2) étages d'habitation à
    fenêtres à meneaux, stores et balcons ; toit à climatiseurs.
    variant % 3 : rayures v0 violet / cyan / blanc, v1 magenta / jaune / blanc, v2 orange / bleu / blanc."""
    n0 = len(b.parts)
    rng = b.rng
    v = variant % 3
    n_hab = 1 if v == 1 else 2
    g = _G(largeur, profondeur, n_hab + 1, rdc=10.0)
    hw, zf, zb, yt = g.hw, g.zf, g.zb, g.yt
    r1, r2, r3 = RAYURES[v]
    mur = vr(("beton_clair", "bleu_pale", "beton_clair")[v], rng, 0.03)
    R, ys = 1.6, 8.0
    # volumes
    b.box((-hw, ys, zf), (hw, yt, zb), mur, studs="top", name="Corps")
    xa, xb = _vitrine(b, g, R, ys, shade(mur, 0.8), c("metal_clair"), "fenetre_froide", ep_pilier=0.6, saillie_pilier=0.2,
                      transparence=0.6)
    # rayons : trois rangées de produits colorés de part et d'autre de l'allée centrale
    zr0, zr1 = zf + R - 0.7, zf + R - 0.1
    for r, y in enumerate((0.9, 2.5, 4.1)):
        for s, (x0, x1) in enumerate(((xa + 0.4, -3.6), (3.6, xb - 0.4))):
            k = (r * 2 + s + v) % len(PRODUITS)
            _d(b, (x0, y, zr0), ((x0 + x1) / 2, y + 1.1, zr1), PRODUITS[k], name="Rayon")
            _d(b, ((x0 + x1) / 2, y, zr0), (x1, y + 1.1, zr1), PRODUITS[(k + 3) % len(PRODUITS)], name="Rayon")
    # coin magazines le long de la vitrine et caisse
    _d(b, (xa + 0.6, 0.4, zf + 0.35), (-3.4, 2.0, zf + 0.75), "metal_clair", name="Magazines")
    _d(b, (xa + 0.8, 2.0, zf + 0.4), (-3.6, 2.3, zf + 0.7), "neon_rose", name="Couvertures")
    _d(b, (4.0, 0.4, zf + 0.7), (8.0, 2.6, zf + 1.2), "enseigne_blanc", name="Caisse")
    # meneaux, porte automatique et affichettes abstraites collées sur le verre
    for x in (xa + (xb - xa) * 0.25, xb - (xb - xa) * 0.25):
        _d(b, (x - 0.15, 0.4, zf + 0.05), (x + 0.15, ys, zf + 0.35), "metal_clair", name="Meneau")
    _d(b, (-2.6, 0.4, zf - 0.05), (2.6, 6.9, zf + 0.12), "vitre_claire", transparency=0.45, name="PorteAuto")
    _d(b, (-0.1, 0.4, zf - 0.15), (0.1, 6.9, zf + 0.08), "metal_clair", name="Joint")
    _d(b, (-2.9, 6.9, zf - 0.3), (2.9, ys, zf + 0.35), "metal_clair", name="Linteau")
    _n(b, (-0.5, 7.2, zf - 0.4), (0.5, 7.6, zf - 0.3), "feu_vert", name="Capteur")
    for k, (x0, cc) in enumerate(((xb - 4.6, r1 if r1 != "blanc" else r2), (xb - 2.4, "auvent_jaune"))):
        _d(b, (x0, 4.6 - k * 0.8, zf + 0.0), (x0 + 1.8, 6.8 - k * 0.8, zf + 0.15), cc, name="Affichette")
    # bandeau à trois rayures, qui tourne sur l'avant et les deux côtés
    for k, (cc, y0) in enumerate(((r1, ys + 0.1), (r2, ys + 1.1), (r3, ys + 2.1))):
        _d(b, (-hw - 0.2, y0, zf - 0.5), (hw + 0.2, y0 + 1.0, zf + 5.0), cc, material="Neon" if cc != "blanc" else "SmoothPlastic",
           name="Rayure", shadow=k == 0)
    # caissons lumineux コンビニ et 24H
    p = _d(b, (-hw + 1.0, ys + 3.4, zf - 0.7), (3.0, ys + 5.8, zf), "enseigne_blanc", name="Caisson", shadow=True)
    _lab(p, "コンビニ", r1 if r1 != "blanc" else r2, glow=1.2)
    p = _n(b, (4.0, ys + 3.4, zf - 0.7), (hw - 1.0, ys + 5.8, zf), r2, name="Caisson24")
    _lab(p, "24H", "blanc", glow=1.4)
    _d(b, (-hw + 1.0, ys + 3.2, zf - 0.8), (hw - 1.0, ys + 3.4, zf), "metal_fonce", name="Support")
    # étages d'habitation : portes-fenêtres en ruban, stores, meneaux filants, balcons, climatiseurs
    allume = _allumage(rng, n_hab + 2, 0.34)
    for k, y0 in enumerate(g.niveaux):
        wy0, wy1 = y0 + (5.4 if k == 0 else 1.0), y0 + 6.8
        _vitre(b, (-hw + 1.2, wy0, zf - 0.12), (hw - 1.2, wy1, zf), allume[k], eteinte="vitre_bleue")
        if allume[k]:
            _d(b, (-hw + 1.3, wy1 - 1.3, zf - 0.22), (hw - 1.3, wy1 - 0.1, zf), STORES["fenetre_chaude"], name="Store")
        if k > 0:
            b.box((-hw + 0.6, y0, zf - 1.6), (hw - 0.6, y0 + 0.5, zf), shade(mur, 0.95), studs="top", name="Balcon")
            _d(b, (-hw + 0.6, y0 + 0.5, zf - 1.6), (hw - 0.6, y0 + 2.7, zf - 1.4), "vitre_claire", transparency=0.5, name="GardeCorps")
            _d(b, (-hw + 0.6, y0 + 2.7, zf - 1.65), (hw - 0.6, y0 + 2.95, zf - 1.35), "metal_clair", name="MainCourante")
            for x in np.linspace(-hw + 0.8, hw - 0.8, 4):
                _d(b, (x - 0.15, y0 + 0.5, zf - 1.7), (x + 0.15, y0 + 2.7, zf - 1.3), "metal_clair", name="Poteau")
            clim(b, -hw + 3.0, y0 + 0.75, zf, "-z")
            clim(b, hw - 3.0, y0 + 0.75, zf, "-z")
        if y0 + 8.0 < yt - 0.8:
            _ceinture(b, -hw, hw, zf, zb, y0 + 7.6, y0 + 8.0, shade(mur, 0.88), s=0.15)
    for x in np.linspace(-hw + 1.2, hw - 1.2, 5)[1:-1]:
        _bande_face(b, g, x - 0.18, x + 0.18, g.niveaux[0] + 5.3, yt - 0.7, "metal_clair", s=0.3, name="MeneauEtage",
                    arriere=False)
    _fenetres_cotes(b, g, rng, g.niveaux, h0=2.4, h1=6.4, n=2, z0=zf + 6.0, eteinte="vitre", part=0.34)
    _descente(b, g, 10.6, yt - 0.7, cote=1)
    _ceinture(b, -hw, hw, zf, zb, yt - 0.7, yt - 0.1, shade(mur, 0.85), s=0.2)
    if panneau_toit:
        _toit(b, g, rng, shade(mur, 0.92), items=("citerne", "clims"), avant_libre=True)
        _panneau_toit(b, -8.0, 8.0, yt, zf + 1.4, 6.0, "rayures", (r1, r2, "blanc"))
    else:
        _toit(b, g, rng, shade(mur, 0.92), items=("local", "citerne", "clims", "antenne"))
    return {"emprise": (float(largeur), float(profondeur)), "hauteur": _hauteur(b, n0)}


# ---------------------------------------------------------------------------
# 3) Tours de bureaux
# ---------------------------------------------------------------------------


def _bandes_tour(b, x0, x1, z0, z1, y0, y1, pas, couleur, *, h=1.2, s=0.15, decal=0.0, allume=None, lumiere="fenetre_froide",
                 h_lum=3.2, s_lum=0.08, mode="ceinture", marge=0.0):
    """Bandes horizontales régulières sur un fût x0..x1 / z0..z1 entre y0 et y1 (pas = hauteur d'étage).
    mode « ceinture » : une pièce fait le tour ; « faces » : une pièce avant/arrière + une pièce côtés (marge aux angles).
    allume : fonction k → bool ; une bande éclairée (Neon) est posée entre deux bandes. Renvoie le nombre de pièces."""
    n0 = len(b.parts)
    k = 0
    y = y0 + decal
    while y + h <= y1 + 1e-6:
        if mode == "ceinture":
            _ceinture(b, x0, x1, z0, z1, y, y + h, couleur, s=s, name="Bande")
        else:
            _d(b, (x0 + marge, y, z0 - s), (x1 - marge, y + h, z1 + s), couleur, name="Bande")
            _d(b, (x0 - s, y, z0 + marge), (x1 + s, y + h, z1 - marge), couleur, name="BandeCote")
        if allume is not None and allume(k) and y + h + 0.3 + h_lum <= y1:
            ya = y + h + (pas - h - h_lum) / 2
            if mode == "ceinture":
                _ceinture(b, x0, x1, z0, z1, ya, ya + h_lum, lumiere, s=s_lum, material="Neon", name="EtageAllume")
            else:
                _n(b, (x0 + marge, ya, z0 - s_lum), (x1 - marge, ya + h_lum, z1 + s_lum), lumiere, name="EtageAllume")
                _n(b, (x0 - s_lum, ya, z0 + marge), (x1 + s_lum, ya + h_lum, z1 - marge), lumiere, name="EtageAllume")
        y += pas
        k += 1
    return len(b.parts) - n0


def _meneaux(b, x0, x1, z0, z1, y0, y1, n_x, n_z, couleur, *, w=0.35, s=0.22, bords=False):
    """Meneaux verticaux traversants : n_x sur l'avant / l'arrière, n_z sur les côtés."""
    for x in np.linspace(x0, x1, n_x + 2)[(0 if bords else 1):(None if bords else -1)]:
        _d(b, (x - w / 2, y0, z0 - s), (x + w / 2, y1, z1 + s), couleur, name="Meneau")
    for z in np.linspace(z0, z1, n_z + 2)[(0 if bords else 1):(None if bords else -1)]:
        _d(b, (x0 - s, y0, z - w / 2), (x1 + s, y1, z + w / 2), couleur, name="Meneau")


def _aretes(b, x0, x1, z0, z1, y0, y1, couleur, *, e=0.9, s=0.25, coins=(0, 1, 2, 3)):
    """Bandes de néon verticales aux angles d'un volume (0 avant-gauche, 1 avant-droit, 2 arrière-droit, 3 arrière-gauche)."""
    pos = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    for i in coins:
        x, z = pos[i]
        sx = -1 if x == x0 else 1
        sz = -1 if z == z0 else 1
        xa, xb = sorted((x + sx * s, x - sx * (e - s)))
        za, zb_ = sorted((z + sz * s, z - sz * (e - s)))
        _n(b, (xa, y0, za), (xb, y1, zb_), couleur, name="AreteNeon")


def _socle_tour(b, g, rng, couleur, lobby="fenetre_chaude", variant=0):
    """Socle de deux niveaux (0 → 17) : hall vitré éclairé en retrait, colonnes, auvent d'entrée, ruban vitré à
    l'étage avec deux enseignes de commerces (un mot autorisé lumineux, un caisson abstrait), corniche."""
    hw, zf, zb = g.hw, g.zf, g.zb
    R = 2.4
    b.box((-hw, 0, zf + R), (hw, 9.0, zb), shade(couleur, 0.8), name="SocleRdc")
    b.box((-hw, 9.0, zf), (hw, 17.0, zb), couleur, studs="top", name="Socle")
    _n(b, (-hw + 1.0, 0.4, zf + R - 0.12), (hw - 1.0, 9.0, zf + R), lobby, name="Hall")
    b.box((-hw + 1.0, 0, zf - 0.2), (hw - 1.0, 0.4, zf + R - 0.12), c("beton_clair"), studs="top", name="Parvis")
    xs = np.linspace(-hw, hw, 6)
    for i, x in enumerate(xs):
        x0, x1 = (x, x + 1.4) if i == 0 else ((x - 1.4, x) if i == len(xs) - 1 else (x - 0.7, x + 0.7))
        b.box((x0, 0, zf - 0.25 if i in (0, len(xs) - 1) else zf + 0.3), (x1, 9.0, zf + R), shade(couleur, 0.9), name="Colonne")
    for x in np.linspace(-hw + 1.0, hw - 1.0, 9)[1:-1]:
        _d(b, (x - 0.12, 0.4, zf + R - 0.32), (x + 0.12, 9.0, zf + R - 0.12), "metal_fonce", name="MeneauHall")
    # auvent d'entrée en porte-à-faux (studs) avec rive lumineuse
    b.box((-6.5, 8.2, zf - 3.6), (6.5, 9.0, zf + 0.6), shade(c("metal_clair"), 0.95), studs="top", name="AuventEntree")
    _n(b, (-6.5, 8.0, zf - 3.8), (6.5, 8.4, zf - 3.6), "neon_blanc", name="RiveAuvent")
    _n(b, (-5.5, 7.95, zf - 3.0), (5.5, 8.2, zf - 0.4), "fenetre_froide", name="DessousAuvent")
    # premier étage du socle : ruban vitré continu, corniche
    _bande_face(b, g, -hw + 1.0, hw - 1.0, 11.0, 15.4, "vitre_bleue", s=0.12)
    _bande_cotes(b, g, zf + 1.0, zb - 1.0, 11.0, 15.4, "vitre_bleue", s=0.12)
    _ceinture(b, -hw, hw, zf, zb, 16.2, 16.9, shade(couleur, 1.15), s=0.22)
    # enseignes des commerces du socle : un mot lumineux à gauche, un caisson abstrait à droite
    mot = ("喫茶", "カラオケ", "本", "映画", "喫茶")[variant % 5]
    fond, encre = (("bordeaux", "fenetre_chaude"), ("enseigne_noir", "neon_magenta"), ("auvent_bleu", "blanc"),
                   ("enseigne_noir", "neon_cyan"), ("bordeaux", "neon_jaune"))[variant % 5]
    wl = min(10.0, hw * 0.62)
    xa, xb = -hw + 1.8, hw - 1.8
    _d(b, (xa - 0.25, 10.0, zf - 0.45), (xa + wl + 0.25, 16.0, zf), "metal_fonce", name="CadreEnseigne")
    p = _d(b, (xa, 10.35, zf - 0.6), (xa + wl, 15.65, zf - 0.45), fond, name="EnseigneSocle", shadow=True)
    _lab(p, mot, encre, glow=1.2)
    c1, c2 = (("ecran_rose", "neon_jaune"), ("ecran_bleu", "neon_cyan"), ("ecran_orange", "neon_blanc"),
              ("neon_cyan", "ecran_bleu"), ("ecran_rose", "neon_cyan"))[variant % 5]
    _d(b, (xb - wl - 0.25, 10.0, zf - 0.45), (xb + 0.25, 16.0, zf), "ecran_fond", name="CadreCaisson")
    _n(b, (xb - wl, 10.35, zf - 0.6), (xb, 15.65, zf - 0.45), c1, name="Caisson")
    _n(b, (xb - wl * 0.75, 11.4, zf - 0.75), (xb - wl * 0.15, 13.2, zf - 0.6), c2, name="CaissonMotif")


def tour_bureaux(b, variant=0, largeur=28, profondeur=28, hauteur=96, panneau_toit=False):
    """Tour de bureaux sur toute l'emprise : socle de deux niveaux (hall éclairé, auvent, enseignes de commerces),
    fût à bandes tous les 6 à 8 studs, retrait éventuel du dernier tiers, écrans géants sur les murs latéraux,
    toit à feux d'obstacle, local technique, mât, citerne ou héliport.
    variant % 5 : 0 mur-rideau bleu (allèges marine, néon cyan à un angle, écran latéral, couronne cyan),
    1 bleu marine à rubans blancs coupés par des ailettes (un sur trois éclairé, néon jaune vertical, écran latéral),
    2 brique à colonnes de fenêtres éclairées, néon orange d'angle et couronne en gradins,
    3 béton à ailettes verticales, verre cyan, écran latéral et héliport,
    4 la plus haute : verre, arêtes au néon, couronne lumineuse et flèche."""
    n0 = len(b.parts)
    rng = b.rng
    v = variant % 5
    W, D, H = float(largeur), float(profondeur), float(hauteur)
    g = _G(W, D, 2)
    g.hw = W / 2 - 0.3
    hw, zf, zb = g.hw, g.zf, g.zb
    corps = vr(("vitre_bleue", "bleu_marine", "brique", "beton", "vitre_cyan")[v], rng, 0.03)
    socle = vr(("bleu_marine", "bleu_nuit", "brique_fonce", "beton_fonce", "bleu_ardoise")[v], rng, 0.03)
    _socle_tour(b, g, rng, socle, lobby="fenetre_chaude" if v != 4 else "fenetre_froide", variant=v)
    # fût : léger retrait de 1 sur le socle, puis retrait du dernier tiers
    i1 = 1.0
    x0, x1, z0, z1 = -hw + i1, hw - i1, zf + i1, zb - i1
    retrait = v in (0, 4)
    ys = 17.0
    yr = round(ys + (H - ys) * (0.68 if v == 0 else 0.6)) if retrait else H
    b.box((x0, ys, z0), (x1, yr, z1), corps, studs="top", name="Fut")
    i2 = 3.5
    rx0, rx1, rz0, rz1 = x0 + i2, x1 - i2, z0 + i2, z1 - i2
    if retrait:
        b.box((rx0, yr, rz0), (rx1, H, rz1), shade(corps, 1.04), studs="top", name="FutHaut")
    pas = (7.0, 6.0, 8.0, 6.0, 6.0)[v]
    allume = _allumage(rng, 40, 0.3)
    al = (lambda k: allume[k % 40])
    couronne = None
    if v == 0:
        marine = vr("bleu_marine", rng, 0.03)
        _bandes_tour(b, x0, x1, z0, z1, ys, yr - 0.5, pas, marine, h=1.4, decal=pas - 1.4, allume=al)
        _meneaux(b, x0, x1, z0, z1, ys, yr - 0.6, 5, 5, c("bleu_pale"), w=0.35, s=0.22)
        _aretes(b, x0, x1, z0, z1, ys + 1.0, yr - 0.6, "neon_cyan", coins=(0,))
        _bandes_tour(b, rx0, rx1, rz0, rz1, yr, H - 2.0, pas, marine, h=1.4, decal=pas - 1.4, allume=lambda k: allume[(k + 7) % 40])
        _meneaux(b, rx0, rx1, rz0, rz1, yr, H - 1.6, 3, 3, c("bleu_pale"), w=0.35, s=0.22)
        _aretes(b, rx0, rx1, rz0, rz1, yr + 0.6, H - 1.6, "neon_cyan", coins=(0,))
        # écran géant sur les deux murs latéraux, sous le retrait
        _panneau_mural(b, g, yr - 25.0, yr - 4.0, z0 + 3.0, z1 - 3.0, "bandes", ("ecran_bleu", "neon_cyan", "ecran_rose"),
                       x_mur=x1, s0=0.4)
        couronne = "neon_cyan"
    elif v == 1:
        # ADN de la zone actuelle : bleu marine, épais rubans blancs (un sur trois éclairé), néon jaune vertical
        y = ys + 1.6
        k = 0
        while y + 2.6 <= H - 2.0:
            lit = k % 3 == int(rng.integers(0, 3)) if k == 0 else (k % 3 == 1)
            cc, mat = ("fenetre_froide", "Neon") if lit else (vr("carrelage", rng, 0.02), "SmoothPlastic")
            _d(b, (x0 + 1.6, y, z0 - 0.15), (x1 - 1.6, y + 2.6, z1 + 0.15), cc, material=mat, name="RubanBlanc")
            _d(b, (x0 - 0.15, y, z0 + 1.6), (x1 + 0.15, y + 2.6, z1 - 1.6), cc, material=mat, name="RubanBlancCote")
            y += pas
            k += 1
        # ailettes verticales qui coupent les rubans en fenêtres (comme la tour de la zone actuelle)
        _meneaux(b, x0 + 1.6, x1 - 1.6, z0 + 1.6, z1 - 1.6, ys + 0.6, H - 1.4, 3, 3, shade(corps, 0.9), w=0.7, s=0.32)
        _n(b, (x0 + 0.5, ys + 4.0, z0 - 0.35), (x0 + 1.3, H - 6.0, z0 + 0.0), "neon_jaune", name="NeonVertical")
        _n(b, (x1 + 0.0, ys + 10.0, z1 - 1.3), (x1 + 0.35, H - 12.0, z1 - 0.5), "neon_magenta", name="NeonVertical")
        _ceinture(b, x0, x1, z0, z1, H - 1.2, H - 0.2, "neon_jaune", s=0.2, material="Neon", name="Couronne")
        _panneau_mural(b, g, H - 36.0, H - 13.0, z0 + 3.0, z1 - 3.4, "diagonale", ("ecran_orange", "neon_jaune", "neon_blanc"),
                       x_mur=x1, s0=0.45)
    elif v == 2:
        # brique : colonnes de fenêtres (certaines éclairées), allèges sombres, couronne en gradins
        nc = 5
        larg = (x1 - x0 - 2.0) / nc
        ycour = H - 10.0
        for i in range(nc):
            xc = x0 + 1.0 + (i + 0.5) * larg
            lit = i in (1, 3) if (i + int(rng.integers(0, 2))) % 2 == 0 else i == 2
            _vitre(b, (xc - larg * 0.3, ys + 1.0, z0 - 0.12), (xc + larg * 0.3, ycour - 1.0, z1 + 0.12), lit, eteinte="vitre",
                   lumiere="fenetre_chaude")
        nz = 4
        lz = (z1 - z0 - 2.0) / nz
        for i in range(nz):
            zc = z0 + 1.0 + (i + 0.5) * lz
            _vitre(b, (x0 - 0.12, ys + 1.0, zc - lz * 0.3), (x1 + 0.12, ycour - 1.0, zc + lz * 0.3), i == 1, eteinte="vitre",
                   lumiere="fenetre_chaude")
        _bandes_tour(b, x0, x1, z0, z1, ys + 1.0, ycour - 1.0, pas, vr("brique_fonce", rng, 0.03), h=1.0, s=0.2,
                     decal=pas - 1.0)
        _aretes(b, x0, x1, z0, z1, ys + 1.5, ycour - 1.5, "neon_orange", coins=(0, 1), e=0.8, s=0.3)
        # couronne : trois gradins et bandeau éclairé
        _ceinture(b, x0, x1, z0, z1, ycour, ycour + 1.2, c("beton_clair"), s=0.3)
        for k, ins in enumerate((1.6, 3.4, 5.4)):
            ya = ycour + 1.2 + k * 3.0
            b.box((x0 + ins, ya, z0 + ins), (x1 - ins, ya + 3.0, z1 - ins), shade(corps, 0.92 + 0.05 * k), studs="top", name="Gradin")
            if k == 0:
                _ceinture(b, x0 + ins, x1 - ins, z0 + ins, z1 - ins, ya + 1.0, ya + 2.0, "fenetre_chaude", s=0.1,
                          material="Neon", name="CouronneLumineuse")
        H = ycour + 1.2 + 9.0
    elif v == 3:
        # béton : rubans de verre cyan, ailettes verticales profondes
        _bandes_tour(b, x0, x1, z0, z1, ys, H - 1.0, pas, c("vitre_cyan"), h=3.4, s=0.1, decal=1.2,
                     allume=None)
        for k, y in enumerate(np.arange(ys + 1.2, H - 4.4, pas)):
            if al(k + 3):
                _ceinture(b, x0, x1, z0, z1, y + 0.4, y + 3.0, "fenetre_froide", s=0.14, material="Neon", name="EtageAllume")
        _meneaux(b, x0, x1, z0, z1, ys, H - 0.2, 6, 6, shade(corps, 1.08), w=0.6, s=0.9)
        _ceinture(b, x0, x1, z0, z1, H - 1.0, H - 0.2, shade(corps, 0.9), s=1.0)
        _panneau_mural(b, g, H - 30.0, H - 8.0, z0 + 2.5, z1 - 2.5, "rayures", ("ecran_rose", "neon_magenta", "neon_cyan"),
                       x_mur=x1, s0=1.0)
    else:
        # la plus haute : verre cyan à allèges claires, arêtes au néon, deux retraits, couronne lumineuse et flèche
        _bandes_tour(b, x0, x1, z0, z1, ys, yr - 0.4, pas, c("vitre_claire"), h=1.0, s=0.12, decal=pas - 1.0,
                     allume=lambda k: allume[k % 40] and k % 2 == 0)
        _aretes(b, x0, x1, z0, z1, ys + 0.6, yr - 0.4, "neon_magenta")
        _bandes_tour(b, rx0, rx1, rz0, rz1, yr, H - 0.4, pas, c("vitre_claire"), h=1.0, s=0.12, decal=pas - 1.0,
                     allume=lambda k: k % 3 == 1)
        _aretes(b, rx0, rx1, rz0, rz1, yr + 0.4, H - 0.4, "neon_cyan")
        _meneaux(b, x0, x1, z0, z1, ys, yr - 0.4, 3, 3, c("vitre_claire"), w=0.4, s=0.18)
        # couronne : lanterne vitrée éclairée, flèche et feu
        c0, c1 = 3.0, 3.0
        b.box((rx0 + c0, H, rz0 + c1), (rx1 - c0, H + 6.0, rz1 - c1), c("fenetre_froide"), material="Neon", name="Couronne")
        b.box((rx0 + c0 - 0.4, H + 6.0, rz0 + c1 - 0.4), (rx1 - c0 + 0.4, H + 6.8, rz1 - c1 + 0.4), shade(corps, 0.85),
              studs="top", name="ChapeauCouronne")
        ym = H + 6.8
        b.cyl((0, ym + 7.0, (rz0 + rz1) / 2), 0.35, 14.0, c("metal_clair"), name="Fleche")
        _n(b, (-0.5, ym + 14.0, (rz0 + rz1) / 2 - 0.5), (0.5, ym + 15.0, (rz0 + rz1) / 2 + 0.5), "rouge_balise", name="Balise")
    # grande lame lumineuse fixée au fût, à l'angle avant droit (le commerce du socle : même mot que son enseigne)
    if v in (0, 1, 3):
        mot = ("喫茶", "カラオケ", "本", "映画", "喫茶")[v]
        neon = ("neon_orange", "neon_magenta", "", "neon_cyan")[v]
        _lame(b, x1 - 1.1, 19.0, 19.0 + 4.6 * len(mot) + 4.0, z0, z0 - 3.35, mot, shade(c(neon), 0.55), "blanc", neon,
              ep=1.4)
    # toit : acrotère, feux d'obstacle aux angles, local technique, mât, citerne ou héliport
    if v in (0, 4):
        tx0, tx1, tz0, tz1 = rx0, rx1, rz0, rz1
    elif v == 2:
        tx0, tx1, tz0, tz1 = x0 + 5.4, x1 - 5.4, z0 + 5.4, z1 - 5.4
    else:
        tx0, tx1, tz0, tz1 = x0, x1, z0, z1
    ytoit = H
    if v != 4:
        _acrotere(b, tx0, tx1, tz0, tz1, ytoit, shade(corps if v != 0 else socle, 0.95), h=1.2, ep=0.6, s=0.15)
    if couronne:
        # bandeau lumineux juste sous l'acrotère (dans le volume du fût : rien ne dépasse au-dessus du toit)
        _ceinture(b, tx0, tx1, tz0, tz1, ytoit - 1.4, ytoit - 0.5, couronne, s=0.2, material="Neon", name="Couronne")
    for (x, z) in ((tx0 + 0.3, tz0 + 0.3), (tx1 - 0.3, tz0 + 0.3), (tx1 - 0.3, tz1 - 0.3), (tx0 + 0.3, tz1 - 0.3)):
        _n(b, (x - 0.4, ytoit + (1.2 if v != 4 else 0.0), z - 0.4), (x + 0.4, ytoit + (2.0 if v != 4 else 0.8), z + 0.4),
           "rouge_balise", name="Balise")
    if v == 3:
        # héliport : plateau à studs sur pieds, H blanc en trois blocs, feux de bord
        hp = min(tx1 - tx0, tz1 - tz0) - 3.0
        yh = ytoit + 2.4
        b.box((-hp / 2 + 3, ytoit, -hp / 2 + 3), (hp / 2 - 3, yh - 0.6, hp / 2 - 3), c("beton_fonce"), name="PiedHeliport")
        b.box((-hp / 2, yh - 0.6, -hp / 2), (hp / 2, yh, hp / 2), c("anthracite"), studs="top", name="Heliport")
        for xa_, xb_ in ((-2.6, -1.6), (1.6, 2.6)):
            _d(b, (xa_, yh, -3.0), (xb_, yh + 0.1, 3.0), "blanc", name="H")
        _d(b, (-1.6, yh, -0.5), (1.6, yh + 0.1, 0.5), "blanc", name="H")
        _d(b, (-hp / 2 + 0.6, yh, -hp / 2 + 0.6), (hp / 2 - 0.6, yh + 0.1, -hp / 2 + 1.0), "jaune", name="Bord")
        _d(b, (-hp / 2 + 0.6, yh, hp / 2 - 1.0), (hp / 2 - 0.6, yh + 0.1, hp / 2 - 0.6), "jaune", name="Bord")
        for x in (-hp / 2 + 0.6, hp / 2 - 0.6):
            _n(b, (x - 0.3, yh, -0.3), (x + 0.3, yh + 0.5, 0.3), "neon_jaune", name="FeuBord")
        _antenne(b, tx1 - 1.5, ytoit, tz1 - 1.5, h=6.0)
    elif v != 4:
        _local_tech(b, tx0 + 4.0, ytoit, tz1 - 3.5, 6.0, 5.0, 4.5, shade(corps, 0.9))
        _antenne(b, tx0 + 2.0, ytoit + 4.9, tz1 - 2.0, h=9.0)
        if not panneau_toit:
            _citerne(b, tx1 - 3.0, ytoit, tz1 - 3.0, r=1.8, h=3.2)
            zc = tz0 + 3.0 if v != 1 else (tz0 + tz1) / 2 + 1.0
            _clim_toit(b, tx1 - 3.0, ytoit, zc)
            _clim_toit(b, tx1 - 6.0, ytoit, zc)
            if v == 1:
                # enseigne lumineuse abstraite sur le toit, à l'avant (silhouette de la ligne des toits)
                _panneau_toit(b, -8.0, 8.0, ytoit, tz0 + 1.0, 5.5, "rayures", ("neon_jaune", "ecran_orange", "neon_blanc"),
                              pied=1.6)
    if panneau_toit:
        pw = min(tx1 - tx0 - 1.0, 20.0)
        _panneau_toit(b, -pw / 2, pw / 2, ytoit, tz0 + 1.0, 8.5, ("cercle", "bandes", "diagonale")[v % 3],
                      (("ecran_bleu", "neon_jaune", "neon_cyan"), ("ecran_rose", "ecran_orange", "neon_jaune"))[v % 2], pied=2.5)
    return {"emprise": (W, D), "hauteur": _hauteur(b, n0)}


# ---------------------------------------------------------------------------
# 4) Grands magasins à écran géant
# ---------------------------------------------------------------------------

ECRANS = {
    # (style, couleurs, mot du bandeau défilant)
    0: ("soleil", ("ecran_rose", "neon_magenta", "ecran_orange"), "百貨店"),
    1: ("diagonale", ("ecran_bleu", "neon_cyan", "neon_blanc"), "映画"),
    2: ("cercle", ("ecran_orange", "neon_jaune", "neon_rose"), "カラオケ"),
}


def grand_magasin(b, variant=0, largeur=40, profondeur=32, hauteur=64, ecran=True, panneau_toit=False):
    """Grand magasin : rez à vitrines éclairées et auvent, écran vidéo géant sur la façade (≈ 60 % de la largeur,
    40 % de la hauteur, centré vers 0,6 H), lame lumineuse 百貨店 à un angle, rubans de fenêtres sur les côtés,
    dernier niveau en retrait, toit à acrotère, cadre d'enseigne et feux d'obstacle.
    variant % 3 : 0 pierre crème, écran magenta / rose / orange ; 1 bleu marine, écran cyan / bleu, rubans de LED
    sur les côtés ; 2 blanc, trois écrans superposés."""
    n0 = len(b.parts)
    rng = b.rng
    v = variant % 3
    W, D, H = float(largeur), float(profondeur), float(hauteur)
    g = _G(W, D, 2)
    g.hw = W / 2 - 0.3
    hw, zf, zb = g.hw, g.zf, g.zb
    corps = vr(("creme", "bleu_marine", "carrelage")[v], rng, 0.025)
    accent = vr(("gris_chaud", "bleu_nuit", "beton")[v], rng, 0.03)
    hr = H - 7.0                      # haut du volume principal ; dernier niveau en retrait au-dessus
    R, ys = 2.0, 9.0
    b.box((-hw, ys, zf), (hw, hr, zb), corps, studs="top", name="Corps")
    b.box((-hw, 0, zf + R), (hw, ys, zb), shade(corps, 0.78), name="Rdc")
    # rez : piliers, vitrines éclairées garnies, entrée centrale vitrée
    xs = np.linspace(-hw, hw, 6)
    for i, x in enumerate(xs):
        x0, x1 = (x, x + 1.4) if i == 0 else ((x - 1.4, x) if i == len(xs) - 1 else (x - 0.7, x + 0.7))
        b.box((x0, 0, zf - 0.25), (x1, ys, zf + R), accent, name="Pilier")
    for i in range(5):
        xa_, xb_ = xs[i] + (1.4 if i == 0 else 0.7), xs[i + 1] - (1.4 if i == 4 else 0.7)
        entree = i == 2
        _n(b, (xa_, 0.5, zf + R - 0.1), (xb_, ys - 0.6, zf + R), "fenetre_chaude" if not entree else "fenetre_froide", name="Vitrine")
        _d(b, (xa_, ys - 0.6, zf + 0.1), (xb_, ys, zf + R), shade(accent, 0.8), name="Linteau")
        if not entree:
            _d(b, (xa_, 0, zf + 0.2), (xb_, 1.2, zf + R - 0.1), accent, name="Socle")
            _d(b, (xa_ + 0.6, 1.2, zf + R - 0.9), (xa_ + (xb_ - xa_) * 0.45, 4.6, zf + R - 0.1),
               PRODUITS[(i + v) % len(PRODUITS)], name="Etalage")
            _d(b, (xa_ + (xb_ - xa_) * 0.55, 1.2, zf + R - 0.9), (xb_ - 0.6, 3.4, zf + R - 0.1),
               PRODUITS[(i + v + 3) % len(PRODUITS)], name="Etalage")
            _d(b, (xa_, 1.2, zf + 0.25), (xb_, ys - 0.6, zf + 0.35), "vitre_claire", transparency=0.6, name="Verre")
        else:
            for x in np.linspace(xa_, xb_, 4)[1:-1]:
                _d(b, (x - 0.12, 0.5, zf + 0.15), (x + 0.12, ys - 0.6, zf + 0.4), "metal_fonce", name="MeneauEntree")
    # auvent d'entrée
    b.box((-9.0, 9.0, zf - 3.6), (9.0, 9.9, zf), shade(accent, 0.9), studs="top", name="Auvent")
    _n(b, (-9.0, 8.8, zf - 3.8), (9.0, 9.2, zf - 3.6), "neon_blanc", name="RiveAuvent")
    _n(b, (-8.0, 8.75, zf - 3.2), (8.0, 9.0, zf - 0.4), "fenetre_chaude", name="DessousAuvent")
    # façade : bandeaux horizontaux et pilastres (derrière l'écran), rubans de fenêtres sur les côtés
    for y in np.arange(ys + 8.0, hr - 2.0, 8.0):
        _ceinture(b, -hw, hw, zf, zb, y, y + 0.8, accent, s=0.2, name="Bandeau")
    for x in (-hw + 3.0, -hw + 6.0, hw - 6.0, hw - 3.0):
        _bande_face(b, g, x - 0.5, x + 0.5, ys, hr - 0.1, shade(corps, 1.08) if v != 1 else shade(corps, 1.25), s=0.32,
                    name="Pilastre")
    allume = _allumage(rng, 12, 0.3, au_moins=2)
    for k, y in enumerate(np.arange(ys + 2.0, hr - 4.0, 8.0)):
        lit = allume[k]
        _bande_cotes(b, g, zf + 3.0, zb - 3.0, y + 0.6, y + 5.0, "fenetre_chaude" if lit else ("vitre_bleue" if v != 1 else "vitre_cyan"),
                     s=0.12, material="Neon" if lit else "SmoothPlastic")
        if v == 1 and y + 6.0 < hr - 0.6:
            _bande_cotes(b, g, zf + 1.0, zb - 1.0, y + 5.6, y + 6.0, ("neon_cyan", "neon_bleu")[k % 2], s=0.25, material="Neon",
                         name="RubanLED")
    # écran géant (ou trois écrans superposés pour la variante 2)
    if ecran:
        ew = W * 0.6
        if v == 2:
            eh = H * 0.15
            for k in range(3):
                yc = H * 0.3 + k * (eh + 1.6)
                st, cc = (("bandes", ("ecran_bleu", "neon_cyan", "neon_blanc")), ("cercle", ("ecran_rose", "neon_jaune", "neon_blanc")),
                          ("rayures", ("ecran_orange", "neon_jaune", "ecran_rose")))[k]
                xo = (-1, 1, -1)[k] * W * 0.06
                _ecran(b, xo - ew * 0.42, xo + ew * 0.42, yc, yc + eh, zf - 0.8, st, cc, cadre=0.6, ep=0.8)
        else:
            style, cc, mot = ECRANS[v]
            eh = H * 0.42
            y0 = H * 0.6 - eh / 2
            _ecran(b, -ew / 2, ew / 2, y0, y0 + eh, zf - 0.9, style, cc, cadre=0.9, ep=0.9)
            # bandeau défilant sous l'écran (mot autorisé)
            p = _n(b, (-ew / 2 + 1.0, y0 - 3.0, zf - 0.7), (ew / 2 - 1.0, y0 - 0.6, zf), "ecran_fond", name="Bandeau")
            _lab(p, mot, "neon_jaune" if v == 0 else "neon_cyan", fond="ecran_fond", glow=1.3)
            _n(b, (-ew / 2 - 0.3, y0 + eh, zf - 1.1), (ew / 2 + 0.3, y0 + eh + 0.3, zf), "neon_blanc", name="RampeEcran")
            # projecteurs sur consoles au-dessus de l'écran
            for x in (-ew / 3, 0.0, ew / 3):
                _d(b, (x - 0.15, y0 + eh + 0.3, zf - 1.8), (x + 0.15, y0 + eh + 0.6, zf), "metal_fonce", name="Console")
                _n(b, (x - 0.5, y0 + eh + 0.0, zf - 2.0), (x + 0.5, y0 + eh + 0.3, zf - 1.5), "neon_blanc", name="Projecteur")
    # lame lumineuse 百貨店 à l'angle avant gauche (côté +X vu de la rue)
    hl = 3 * 5.2 + 3.0
    _lame(b, hw - 1.6, 12.0, 12.0 + hl, zf - 0.4, zf - 3.75, "百貨店", shade(c("neon_rouge") if v != 1 else c("neon_bleu"), 0.6),
          "blanc", "neon_rouge" if v != 1 else "neon_cyan", ep=1.6)
    # néon vertical à l'autre angle avant (retour sur le côté)
    _n(b, (-hw - 0.25, ys + 2.0, zf - 0.25), (-hw + 0.6, hr - 2.0, zf + 0.6), ("neon_magenta", "neon_cyan", "neon_jaune")[v],
       name="NeonAngle")
    # dernier niveau en retrait, acrotère, cadre d'enseigne, feux d'obstacle
    ins = 4.0
    _acrotere(b, -hw, hw, zf, zb, hr, shade(corps, 0.92), h=1.2)
    b.box((-hw + ins, hr, zf + ins), (hw - ins, H, zb - ins), shade(corps, 0.95), studs="top", name="Attique")
    _d(b, (-hw + ins + 1.5, hr + 1.8, zf + ins - 0.12), (hw - ins - 1.5, H - 1.6, zf + ins + 1.0),
       "vitre_bleue" if v != 1 else "fenetre_froide", material="SmoothPlastic" if v != 1 else "Neon", name="Ruban")
    _ceinture(b, -hw + ins, hw - ins, zf + ins, zb - ins, H - 0.9, H - 0.1, accent, s=0.2)
    _ceinture(b, -hw + ins, hw - ins, zf + ins, zb - ins, hr + 0.6, hr + 1.1, ("neon_rose", "neon_cyan", "fenetre_froide")[v],
              s=0.12, material="Neon", name="LiseréAttique")
    for (x, z) in ((-hw + 0.6, zf + 0.6), (hw - 0.6, zf + 0.6), (hw - 0.6, zb - 0.6), (-hw + 0.6, zb - 0.6)):
        _balise(b, x, hr + 1.2, z)
    if panneau_toit:
        _panneau_toit(b, -11.0, 11.0, H, zf + ins + 1.0, 7.0, "mot", ("ecran_rose", "neon_jaune", "neon_cyan"), mot="百貨店")
    else:
        # cadre d'enseigne : poutres d'acier et caisson lumineux abstrait
        fx0, fx1 = -hw + ins + 2.0, -hw + ins + 14.0
        for x in (fx0 + 0.4, fx1 - 0.4):
            b.box((x - 0.25, H, zf + ins + 1.4), (x + 0.25, H + 7.0, zf + ins + 1.9), col(ACIER), name="MontantCadre")
        _n(b, (fx0, H + 2.4, zf + ins + 1.0), (fx1, H + 6.6, zf + ins + 1.4), ("ecran_rose", "neon_cyan", "neon_jaune")[v], name="Caisson")
        _d(b, (fx0 + 1.0, H + 3.2, zf + ins + 0.85), (fx1 - 5.0, H + 5.8, zf + ins + 1.0), "ecran_fond", name="Motif")
        _citerne(b, hw - ins - 3.0, H, zb - ins - 3.0, r=1.8, h=3.0)
        _local_tech(b, hw - ins - 4.0, H, zf + ins + 4.0, 5.0, 4.0, 3.5, shade(corps, 0.9))
    for (x, z) in ((-hw + ins + 0.6, zb - ins - 0.6), (hw - ins - 0.6, zb - ins - 0.6)):
        _balise(b, x, H, z)
    return {"emprise": (W, D), "hauteur": _hauteur(b, n0)}


# ---------------------------------------------------------------------------
# 5) Immeubles de la seconde rangée
# ---------------------------------------------------------------------------


def immeuble_fond(b, variant=0, largeur=24, profondeur=24, hauteur=50):
    """Immeuble simple de la seconde rangée, vu par-dessus la première (≤ 50 pièces) : un ou deux volumes
    (retrait en haut), rubans de fenêtres sur la façade (quelques-uns éclairés) coupés par des meneaux filants,
    bandes sur les côtés, écran latéral sur les plus hauts, toit à citerne, climatiseur, antenne et feu d'obstacle
    au-delà de 60.
    variant % 4 : 0 bleu ardoise ; 1 béton clair avec néon vertical ; 2 bleu marine à rubans blancs ;
    3 brique et bordeaux avec petite enseigne abstraite sur le toit."""
    n0 = len(b.parts)
    rng = b.rng
    v = variant % 4
    W, D, H = float(largeur), float(profondeur), float(hauteur)
    hw, zf, zb = W / 2 - 0.5, -D / 2, D / 2
    corps = vr(("bleu_ardoise", "beton", "bleu_marine", "brique")[v], rng, 0.05)
    second = vr(("bleu_acier", "beton_clair", "bleu_ardoise", "bordeaux")[v], rng, 0.05)
    retrait = H >= 50
    hb = round(H * 0.78) if retrait else H
    b.box((-hw, 0, zf), (hw, hb, zb), corps, studs="top", name="Corps")
    ins = 3.0 if W >= 20 else 2.0
    if retrait:
        b.box((-hw + ins, hb, zf + ins), (hw - ins, H, zb - ins), second, studs="top", name="Retrait")
    # socle sombre (rez) et rubans de façade
    _ceinture(b, -hw, hw, zf, zb, 0, 6.0, shade(corps, 0.7), s=0.15, name="Socle")
    n = int(max(3, min(6, (hb - 10) // 8)))
    pas = (hb - 10.0) / n
    allume = _allumage(rng, n + 2, 0.3)
    ruban = ("vitre_bleue", "vitre_claire", "carrelage", "vitre")[v]
    for k in range(n):
        y = 8.0 + k * pas
        h = pas * (0.45 if v != 2 else 0.4)
        lit = allume[k]
        cc = ("fenetre_chaude" if v in (0, 3) else "fenetre_froide") if lit else ruban
        if v in (0, 2):
            _ceinture(b, -hw + 0.0, hw, zf, zb, y, y + h, cc, s=0.12, material="Neon" if lit else "SmoothPlastic", name="Ruban")
        else:
            _d(b, (-hw + 1.5, y, zf - 0.12), (hw - 1.5, y + h, zb + 0.12), cc, material="Neon" if lit else "SmoothPlastic", name="Ruban")
    # meneaux filants : ils découpent les rubans en fenêtres (avant et arrière)
    nm = 2 if W < 22 else 3
    for x in np.linspace(-hw, hw, nm + 2)[1:-1]:
        _d(b, (x - 0.3, 7.0, zf - 0.25), (x + 0.3, hb - 1.4, zb + 0.25), shade(corps, 0.85), name="Meneau")
    if v in (1, 3):
        # côtés : deux colonnes de fenêtres
        for z0 in (zf + 2.0, zb - 2.0 - min(5.0, D * 0.2)):
            _d(b, (-hw - 0.12, 8.0, z0), (hw + 0.12, hb - 3.0, z0 + min(5.0, D * 0.2)), "vitre" if v == 3 else "vitre_bleue", name="ColonneCote")
    if retrait:
        _d(b, (-hw + ins + 1.0, hb + 2.0, zf + ins - 0.12), (hw - ins - 1.0, hb + 2.0 + min(4.0, (H - hb) * 0.45), zb - ins + 0.12),
           "fenetre_froide" if allume[n] else "vitre_bleue", material="Neon" if allume[n] else "SmoothPlastic", name="RubanHaut")
    _ceinture(b, -hw, hw, zf, zb, hb - 1.0, hb - 0.1, shade(corps, 1.15), s=0.2, name="Corniche")
    # écran latéral (les deux côtés) sur les plus hauts des variantes 0 et 2
    if v in (0, 2) and H >= 60:
        g = _G(W, D, 2)
        g.hw = hw
        za, zb_ = zf + 2.0, min(zb - 2.0, zf + 16.0)
        _panneau_mural(b, g, max(hb - 22.0, 24.0), hb - 3.0, za, zb_, _choix(["bandes", "rayures", "diagonale"], f"{H}{W}"),
                       _choix([("ecran_bleu", "neon_cyan", "neon_blanc"), ("ecran_rose", "neon_jaune", "ecran_orange"),
                               ("ecran_orange", "neon_jaune", "neon_rose")], f"{W}{H}"), s0=0.2)
    # néon vertical (v1) ou enseigne abstraite de toit (v3)
    if v == 1:
        cc = _choix(["neon_magenta", "neon_cyan", "neon_jaune"], f"{W}{H}")
        _n(b, (hw - 2.4, 10.0, zf - 0.35), (hw - 1.4, hb - 4.0, zf), cc, name="NeonVertical")
    elif v == 3:
        xa, xb = -hw + 1.0, -hw + 1.0 + min(10.0, W * 0.45)
        for x in (xa + 0.4, xb - 0.4):
            b.box((x - 0.25, hb, zf + 1.4), (x + 0.25, hb + 6.0, zf + 1.9), col(ACIER), name="MontantCadre")
        _n(b, (xa, hb + 2.0, zf + 1.0), (xb, hb + 5.6, zf + 1.4), _choix(["ecran_rose", "neon_cyan", "ecran_orange"], f"{W}{H}"),
           name="Caisson")
        _d(b, (xa + 1.0, hb + 2.6, zf + 0.85), ((xa + xb) / 2, hb + 5.0, zf + 1.0), "ecran_fond", name="Motif")
    # toit
    ty = H
    tx0, tx1, tz0, tz1 = (-hw + ins, hw - ins, zf + ins, zb - ins) if retrait else (-hw, hw, zf, zb)
    _citerne(b, tx1 - 2.4, ty, tz1 - 2.4, r=1.5, h=2.8)
    _clim_toit(b, tx0 + 2.4, ty, tz1 - 2.0)
    _antenne(b, tx0 + 1.5, ty, tz1 - 4.0, h=5.0 if H < 60 else 7.0)
    if H >= 60:
        _balise(b, (tx0 + tx1) / 2, ty, (tz0 + tz1) / 2)
    return {"emprise": (W, D), "hauteur": _hauteur(b, n0)}


