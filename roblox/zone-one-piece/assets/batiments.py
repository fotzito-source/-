"""Bâtiments du bourg du port et de la campagne (zone 2, mer de l'Est), en style « stud ».

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :
- maison_port(largeur=18, profondeur=14, etages=2) : maison colorée du bord de mer (8 variantes, `variant % 8`) ;
    0 blanc / toit rouge / volets bleus / auvent rouge et blanc ; 1 bleu / toit rouge / balcon ;
    2 jaune / toit bleu / volets verts / auvent bleu et blanc ; 3 rose / toit turquoise / balcon fleuri ;
    4 rouge à chaînages blancs / toit brun / pignon à colombage sur rue ; 5 crème à pans de bois / toit orange /
    auvent jaune et blanc ; 6 turquoise / toit rouge / tourelle d'angle ; 7 blanc / toit bleu / lucarne et cheminée.
- taverne(largeur=24, profondeur=20) : taverne de pirates à deux niveaux (rez de pierre à porche couvert,
    étage à colombage), enseigne « TAVERNE », vigie et pavillon générique sur le faîtage.
- etal(variant) : étal de marché 8 × 6 à toile rayée ; 0 « FRUITS », 1 « VIANDE », 2 « POISSONS ».
- grange(largeur=22, profondeur=16) : grange rouge ; 0 toit à la Mansart et silo, 1 toit raide, appentis et roue.

Repère (voir CONVENTIONS.md) : origine au centre de l'emprise au sol, y = 0 au sol, l'AVANT regarde -Z.
`largeur` est le long de X, `profondeur` le long de Z ; l'emprise des murs est exactement largeur × profondeur.
Les éléments de façade se dessinent dans un repère où le mur est le plan z = 0 et l'extérieur est vers -z ;
on les pose avec `b.at(...)` (avant : yaw 0 ; arrière : yaw 180 ; côté +X : yaw -90 ; côté -X : yaw 90).
Vu de la rue (depuis -z), +x est à GAUCHE.

Débords sur la rue : avant-toits, auvents, balcons, enseignes ≤ 2 studs devant le mur avant, dessous ≥ 6,5 ;
au sol (marches, pots) ≤ 1 stud. Débords latéraux ≤ 0,8 (les voisins sont à 2 studs).
Uniquement des éléments génériques de port et de campagne ; textes en français tirés de la liste autorisée.
"""

from __future__ import annotations

import math

from kit import hexrgb, rot_x, rot_y, rot_z, shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Couleurs locales et outils
# ---------------------------------------------------------------------------
INTERIEUR = "#3A2A22"        # fond sombre (porche, ouverture du fenil)
GRES = "#C9A87C"             # grès chaud du rez de la taverne
FER = "#3F444C"              # ferrures, potences, cercles de tonneaux


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


ND = dict(collide=False)                 # petits détails sans collision
NDS = dict(collide=False, shadow=False)  # détails très fins (ni collision ni ombre)


def _pan_z(b, za, ya, zb, yb, x0, x1, ep, couleur, *, ext_a=0.0, ext_b=0.0, studs="top", name="Pan", **kw):
    """Dalle inclinée dans le plan YZ : sa face supérieure passe par (za, ya) et (zb, yb), épaisseur `ep`
    sous cette ligne, étendue sur x0..x1 ; `ext_a` / `ext_b` l'allongent côté a / côté b (le long de la pente)."""
    dz, dy = zb - za, yb - ya
    L = math.hypot(dz, dy)
    uz, uy = dz / L, dy / L
    phi = math.atan2(dy, dz)
    ny, nz = math.cos(phi), -math.sin(phi)
    if ny < 0:
        ny, nz = -ny, -nz
    s = (ext_b - ext_a) / 2
    cz = (za + zb) / 2 + uz * s - nz * ep / 2
    cy = (ya + yb) / 2 + uy * s - ny * ep / 2
    return b.part("block", (x1 - x0, ep, L + ext_a + ext_b), ((x0 + x1) / 2, cy, cz), rot_x(-math.degrees(phi)),
                  col(couleur), studs=studs, name=name, **kw)


def _pan_x(b, xa, ya, xb, yb, z0, z1, ep, couleur, *, ext_a=0.0, ext_b=0.0, studs="top", name="Pan", **kw):
    """Dalle inclinée dans le plan XY (xa < xb) : face supérieure par (xa, ya) et (xb, yb), épaisseur `ep`
    sous cette ligne, étendue sur z0..z1 ; `ext_a` / `ext_b` l'allongent côté a / côté b."""
    dx, dy = xb - xa, yb - ya
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    s = (ext_b - ext_a) / 2
    cx = (xa + xb) / 2 + ux * s - nx * ep / 2
    cy = (ya + yb) / 2 + uy * s - ny * ep / 2
    return b.part("block", (L + ext_a + ext_b, ep, z1 - z0), (cx, cy, (z0 + z1) / 2), rot_z(math.degrees(math.atan2(dy, dx))),
                  col(couleur), studs=studs, name=name, **kw)


def _barre(b, p0, p1, e, z0, z1, couleur, name="Barre", **kw):
    """Poutre droite dans le plan XY, de p0 à p1 (axe), section e × (z1 - z0)."""
    (xa, ya), (xb, yb) = p0, p1
    L = math.hypot(xb - xa, yb - ya)
    return b.part("block", (L, e, z1 - z0), ((xa + xb) / 2, (ya + yb) / 2, (z0 + z1) / 2),
                  rot_z(math.degrees(math.atan2(yb - ya, xb - xa))), col(couleur), name=name, **kw)


# ---------------------------------------------------------------------------
# Éléments de façade (repère : mur = plan z = 0, extérieur vers -z)
# ---------------------------------------------------------------------------


def _fenetre(b, x, y, w, h, cadre, *, vitre="vitre", volets=None, fleurs=None, croix=True, appui=True,
             lumiere=False, linteau=None):
    """Fenêtre : cadre, vitre, croisillon, appui stud ; volets de couleur et jardinière fleurie en option.
    `fleurs` = couleur des fleurs (jardinière sous l'appui)."""
    cd = col(cadre)
    kw = {"material": "Neon"} if lumiere else {}
    b.box((x - w / 2 - 0.3, y - 0.3, -0.12), (x + w / 2 + 0.3, y + h + 0.3, 0.2), cd, name="Cadre")
    b.box((x - w / 2, y, -0.2), (x + w / 2, y + h, 0.1), col("fenetre_lumiere" if lumiere else vitre), name="Vitre", **kw)
    if croix:
        b.box((x - 0.12, y, -0.34), (x + 0.12, y + h, -0.2), cd, name="Meneau", **ND)
        if croix == 2:
            b.box((x - w / 2, y + h * 0.58 - 0.11, -0.3), (x + w / 2, y + h * 0.58 + 0.11, -0.2), cd, name="Traverse", **ND)
    if linteau:
        b.box((x - w / 2 - 0.5, y + h + 0.3, -0.4), (x + w / 2 + 0.5, y + h + 0.75, 0.2), col(linteau), name="Linteau")
    if fleurs:
        b.box((x - w / 2 - 0.35, y - 1.15, -0.95), (x + w / 2 + 0.35, y - 0.3, 0.2), col("bois"), name="Jardiniere", **ND)
        b.box((x - w / 2 - 0.2, y - 0.3, -0.85), (x + w / 2 + 0.2, y + 0.2, -0.15), col("feuillage"), name="Feuilles", **ND)
        n = 2
        for i in range(n):
            xx = x - w / 2 + 0.35 + i * (w - 0.7) / (n - 1)
            b.ball((xx, y + 0.25, -0.55), 0.38, col(fleurs), name="Fleur", **NDS)
    elif appui:
        b.box((x - w / 2 - 0.5, y - 0.6, -0.5), (x + w / 2 + 0.5, y - 0.25, 0.2), cd, studs="top", name="Appui")
    if volets:
        vc = col(volets)
        lw = w / 2 + 0.1
        for s in (-1, 1):
            xa = x + s * (w / 2 + 0.3)
            b.box((min(xa, xa + s * lw), y - 0.15, -0.26), (max(xa, xa + s * lw), y + h + 0.15, 0.2), vc, name="Volet")


def _porte(b, x, w, h, couleur, cadre, *, y0=1.0, imposte=True, marche="pierre_fonce", poignee=True):
    """Porte d'entrée sur le soubassement (seuil à y0) : chambranle, vantail à panneau, imposte vitrée, marche."""
    cd, pc = col(cadre), col(couleur)
    top = y0 + h + (0.9 if imposte else 0.0)
    b.box((x - w / 2 - 0.4, y0, -0.14), (x + w / 2 + 0.4, top + 0.4, 0.2), cd, name="Chambranle")
    b.box((x - w / 2, y0, -0.28), (x + w / 2, y0 + h, 0.1), pc, name="Porte")
    b.box((x - w / 2 + 0.4, y0 + h * 0.5, -0.38), (x + w / 2 - 0.4, y0 + h - 0.5, -0.2), shade(pc, 0.82), name="Panneau", **ND)
    if imposte:
        b.box((x - w / 2, y0 + h + 0.15, -0.24), (x + w / 2, top, 0.1), col("vitre"), name="Imposte")
    if poignee:
        b.ball((x + w / 2 - 0.45, y0 + h * 0.45, -0.35), 0.17, col("laiton"), name="Poignee", **NDS)
    if marche:
        b.box((x - w / 2 - 0.6, 0, -1.0), (x + w / 2 + 0.6, 0.5, 0.2), col(marche), studs="top", name="Marche")


def _lanterne_murale(b, x, y, cadre="fer"):
    """Lanterne de navire accrochée au mur par une potence (bas de la lanterne à y, dépasse de 1,1)."""
    cd = col(cadre)
    b.box((x - 0.12, y + 1.75, -0.9), (x + 0.12, y + 2.0, 0.1), cd, name="Potence", **ND)
    b.box((x - 0.4, y, -0.8), (x + 0.4, y + 1.1, -0.0), col("lanterne"), material="Neon", name="Lanterne", **NDS)
    b.box((x - 0.5, y + 1.1, -0.9), (x + 0.5, y + 1.45, 0.1), cd, name="Chapeau", **ND)
    b.box((x - 0.5, y - 0.2, -0.9), (x + 0.5, y, 0.1), cd, name="Fond", **ND)
    b.box((x - 0.06, y + 1.45, -0.46), (x + 0.06, y + 1.75, -0.34), cd, name="Crochet", **NDS)


def _bouee_murale(b, x, y, r=1.0):
    """Bouée rouge et blanche accrochée au mur (disque rouge, quatre bandes blanches, trou couleur du mur)."""
    b.cyl((x, y, -0.25), r, 0.4, col("rouge"), axis="z", name="Bouee", **ND)
    for a in (45, -45):
        b.part("block", (2 * r + 0.06, 0.42 * r, 0.42), (x, y, -0.26), rot_z(a), col("blanc"), name="Bande", **ND)
    b.cyl((x, y, -0.3), r * 0.48, 0.42, col("bois_fonce"), axis="z", name="Trou", **ND)


def _pot(b, x, z, fleur, r=0.45):
    """Pot de fleurs posé au sol (devant une porte) ; ne dépasse pas de z - r - 0,05."""
    b.cyl((x, 0.55, z), r, 1.1, col("terre_claire"), name="Pot", **ND)
    b.ball((x, 1.3, z), r + 0.05, col("feuillage"), name="Plante", **ND)
    b.ball((x + 0.15, 1.75, z - 0.1), 0.3, col(fleur), name="Fleur", **NDS)


def _auvent(b, xa, xb, y_haut, a, bb, *, prof=1.9, chute=1.0, bande=1.4, y_bas=None):
    """Auvent rayé (bandes alternées `a` / `bb`) au-dessus d'une vitrine : pente stud, lambrequin, deux tirants.
    Le bord avant est à `prof` du mur ; le bas du lambrequin reste ≥ 6,6 au-dessus du sol."""
    y_bas = y_haut - chute if y_bas is None else y_bas
    n = max(2, int(round((xb - xa) / bande)))
    lw = (xb - xa) / n
    for i in range(n):
        cc = col(a) if i % 2 == 0 else col(bb)
        x0 = xa + i * lw
        b.wedge((x0, y_bas, -prof), (x0 + lw, y_haut, 0.1), cc, down="-z", studs="top", name="Auvent", **ND)
        b.box((x0, y_bas - 0.65, -prof - 0.12), (x0 + lw, y_bas + 0.05, -prof + 0.08), cc, name="Lambrequin", **ND)
    for x in (xa + 0.3, xb - 0.3):
        _tige_yz(b, x, (y_haut + 0.6, 0.1), (y_bas + 0.2, -prof * 0.85), 0.12, FER, name="Tirant")


def _tige_yz(b, x, p0, p1, e, couleur, name="Tige", **kw):
    """Tige fine (section e × e) dans le plan YZ, de p0 = (y, z) à p1 = (y, z), sans collision."""
    (ya, za), (yb, zb) = p0, p1
    L = math.hypot(yb - ya, zb - za)
    ang = math.degrees(math.atan2(yb - ya, zb - za))
    return b.part("block", (e, e, L), (x, (ya + yb) / 2, (za + zb) / 2), rot_x(-ang), col(couleur), name=name,
                  collide=False, shadow=False, **kw)


def _taches(b, rects, mur, rng):
    """Taches d'enduit de teintes proches (aspect « pixel »), en saillie de 0,1 ; rects = (x0, y0, x1, y1)."""
    for (xa, ya, xb, yb) in rects:
        f = 1 + float(rng.choice((-1, 1))) * float(rng.uniform(0.05, 0.09))
        b.box((xa, ya, -0.1), (xb, yb, 0.1), shade(col(mur), f), name="Enduit", **NDS)


def _pierres(b, x, y, rng, pierre="pierre_fonce"):
    """Petit coin d'enduit tombé : trois moellons apparents."""
    for (dx, dy, w, h) in ((0, 0, 1.4, 0.7), (1.5, 0.15, 1.0, 0.6), (0.5, 0.8, 1.2, 0.6)):
        b.box((x + dx, y + dy, -0.13), (x + dx + w, y + dy + h, 0.1), vr(pierre, rng, 0.06), name="Moellon", **NDS)


# ---------------------------------------------------------------------------
# Toits
# ---------------------------------------------------------------------------


def _toit_long(b, x0, x1, zf, zb, H, pente, toit, mur, rng, *, deb_av=1.0, deb_ar=0.8, deb_cote=0.7, ep=0.8,
               faitage=None):
    """Toit à deux pans, faîtage parallèle à X (égouts sur la rue) : pignons de mur sur les côtés, pans studdés
    qui débordent, faîtage. Renvoie le haut du faîtage et y(z) du dessus du pan avant."""
    zm = (zf + zb) / 2
    hu = (zm - zf) * pente
    k = ep * math.hypot(1, pente)
    h1 = math.hypot(1, pente)
    b.wedge((x0, H, zf), (x1, H + hu + 0.3, zm), vr(mur, rng, 0.03), down="-z", name="Pignon")
    b.wedge((x0, H, zm), (x1, H + hu + 0.3, zb), vr(mur, rng, 0.03), down="+z", name="Pignon")
    xa, xb = x0 - deb_cote, x1 + deb_cote
    t = col(toit)
    _pan_z(b, zf, H + k, zm, H + hu + k, xa, xb, ep, vary(t, rng, 0.03), ext_a=deb_av * h1, ext_b=0.4)
    _pan_z(b, zm, H + hu + k, zb, H + k, xa, xb, ep, vary(t, rng, 0.03), ext_a=0.4, ext_b=deb_ar * h1)
    yr = H + hu + k
    fa = col(faitage) if faitage else shade(t, 0.72)
    b.box((xa - 0.15, yr - 0.75, zm - 0.7), (xb + 0.15, yr + 0.45, zm + 0.7), fa, studs="top", name="Faitage")
    return yr + 0.45, (lambda z: H + k + (z - zf) * pente)


def _toit_pignon(b, x0, x1, zf, zb, H, pente, toit, mur, rng, *, deb_av=1.0, deb_ar=0.8, deb_cote=0.7, ep=0.8,
                 rive=None, faitage=None):
    """Toit à deux pans, pignon sur la rue (faîtage parallèle à Z) : triangle de mur, pans studdés, planches
    de rive sur le pignon avant, faîtage. Renvoie le haut du faîtage."""
    xm = (x0 + x1) / 2
    hu = (xm - x0) * pente
    k = ep * math.hypot(1, pente)
    h1 = math.hypot(1, pente)
    b.wedge((x0, H, zf), (xm, H + hu + 0.3, zb), vr(mur, rng, 0.03), down="-x", name="Pignon")
    b.wedge((xm, H, zf), (x1, H + hu + 0.3, zb), vr(mur, rng, 0.03), down="+x", name="Pignon")
    za, zz = zf - deb_av, zb + deb_ar
    t = col(toit)
    _pan_x(b, x0, H + k, xm, H + hu + k, za, zz, ep, vary(t, rng, 0.03), ext_a=deb_cote * h1, ext_b=0.4)
    _pan_x(b, xm, H + hu + k, x1, H + k, za, zz, ep, vary(t, rng, 0.03), ext_a=0.4, ext_b=deb_cote * h1)
    yr = H + hu + k
    if rive:
        rc = col(rive)
        _pan_x(b, x0, H + k + 0.15, xm, H + hu + k + 0.15, za - 0.25, za + 0.3, ep + 0.3, rc,
               ext_a=deb_cote * h1 + 0.1, ext_b=0.55, studs="none", name="Rive", **ND)
        _pan_x(b, xm, H + hu + k + 0.15, x1, H + k + 0.15, za - 0.26, za + 0.31, ep + 0.3, rc,
               ext_a=0.55, ext_b=deb_cote * h1 + 0.1, studs="none", name="Rive", **ND)
    fa = col(faitage) if faitage else shade(t, 0.72)
    b.box((xm - 0.7, yr - 0.75, za + (0.35 if rive else -0.15)), (xm + 0.7, yr + 0.45, zz + 0.15), fa, studs="top",
          name="Faitage")
    return yr + 0.45


def _cheminee(b, x, z, y0, y1, couleur, rng, *, s=1.6):
    """Souche de cheminée (du comble jusqu'à y1) : fût, couronnement, conduit sombre."""
    b.box((x - s / 2, y0, z - s / 2), (x + s / 2, y1, z + s / 2), vr(couleur, rng, 0.04), name="Cheminee")
    b.box((x - s / 2 - 0.25, y1, z - s / 2 - 0.25), (x + s / 2 + 0.25, y1 + 0.5, z + s / 2 + 0.25), shade(col(couleur), 0.85),
          studs="top", name="Couronnement")
    b.box((x - s / 4, y1 + 0.5, z - s / 4), (x + s / 4, y1 + 0.75, z + s / 4), col("noir"), name="Conduit", **ND)
    return y1 + 0.75


# ---------------------------------------------------------------------------
# MAISON DU PORT
# ---------------------------------------------------------------------------
YP = 1.0      # haut du soubassement de pierre (seuil des portes)
H1 = 8.6      # haut du rez-de-chaussée (bandeau d'étage)
HE = 6.5      # hauteur d'un étage

_MAISONS = [
    # 0 : blanc, toit rouge, volets bleus, vitrine à auvent rouge et blanc, bouée
    dict(mur="mur_blanc", toit="toit_rouge", volet="volet_bleu", cadre="blanc", chaine="pierre", socle="pierre",
         porte="volet_bleu", forme="long", rdc="boutique", auvent=("toile_rouge", "blanc"), fleurs="fleur_rouge",
         deco="bouee", porte_cote=1, cheminee="pierre_claire"),
    # 1 : bleu, toit rouge, volets blancs, balcon, lanterne
    dict(mur="mur_bleu", toit="toit_rouge", volet="blanc", cadre="blanc", chaine="blanc", socle="pierre_claire",
         porte="bois", forme="pignon", rdc="logis", balcon="simple", fleurs="fleur_jaune", deco="lanterne",
         porte_cote=-1, rive="blanc"),
    # 2 : jaune, toit bleu, volets verts, vitrine à auvent bleu et blanc
    dict(mur="mur_jaune", toit="toit_bleu", volet="volet_vert", cadre="blanc", chaine="pierre_claire", socle="pierre",
         porte="volet_vert", forme="long", rdc="boutique", auvent=("toile_bleue", "blanc"), fleurs="fleur_rouge",
         deco="lanterne", porte_cote=-1, cheminee="mur_blanc", mouette=True),
    # 3 : rose, toit turquoise, volets blancs, balcon fleuri, bouée
    dict(mur="mur_rose", toit="toit_turquoise", volet="blanc", cadre="blanc", chaine="blanc", socle="pierre_claire",
         porte="turquoise", forme="pignon", rdc="logis", balcon="fleuri", fleurs="fleur_rose", deco="bouee",
         porte_cote=1, rive="blanc"),
    # 4 : rouge à chaînages blancs, toit brun, pignon à colombage sur rue
    dict(mur="mur_rouge", toit="toit_brun", volet="volet_vert", cadre="blanc", chaine="blanc", socle="pierre",
         porte="bois_fonce", forme="pignon", rdc="logis", pignon_bois=True, fleurs="fleur_jaune", deco="lanterne",
         porte_cote=-1, rive="bois_fonce", cheminee="pierre", mouette=True),
    # 5 : crème à pans de bois, toit orange, vitrine à auvent jaune et blanc
    dict(mur="mur_creme", toit="toit_orange", volet="volet_rouge", cadre="colombage", chaine="colombage",
         socle="pierre", porte="volet_rouge", forme="long", rdc="boutique", auvent=("toile_jaune", "blanc"),
         colombage=True, fleurs="fleur_rouge", deco="bouee", porte_cote=1, cheminee="pierre"),
    # 6 : turquoise, toit rouge, tourelle d'angle
    dict(mur="mur_turquoise", toit="toit_rouge", volet="jaune", cadre="blanc", chaine="blanc", socle="pierre_claire",
         porte="volet_bleu", forme="long", rdc="logis", tourelle=True, fleurs="fleur_rouge", deco="lanterne",
         porte_cote=-1),
    # 7 : blanc, toit bleu, volets bleus, lucarne et haute cheminée
    dict(mur="mur_blanc", toit="toit_bleu", volet="volet_bleu", cadre="bleu", chaine="bleu", socle="pierre_claire",
         porte="bleu", forme="long", rdc="logis", lucarne=True, fleurs="fleur_rose", deco="bouee", porte_cote=1,
         cheminee="mur_blanc", cheminee_haute=True),
]
_TOITS_ALT = ("toit_rouge", "toit_bleu", "toit_turquoise", "toit_orange", "toit_rouge_fonce")


def _style_maison(variant):
    S = dict(_MAISONS[variant % len(_MAISONS)])
    k = variant // len(_MAISONS)
    if k:
        S["toit"] = _TOITS_ALT[(variant + k) % len(_TOITS_ALT)]
    return S


def _fenetres_cote(b, W, n, S, H, *, arriere=False, fleurs=False):
    """Façade simple (côté ou arrière) de largeur W : côtés, une fenêtre par étage ; arrière, deux par étage."""
    cd = S["cadre"]
    for i in range(n):
        yb = YP + 1.4 if i == 0 else H1 + (i - 1) * HE + 1.6
        if not arriere:
            if i > 0:
                _fenetre(b, 0.0, yb, 2.0, 3.0, cd, croix=False)
            elif n <= 2:
                # rez des maisons de la rangée sur rue : le pignon d'about est vu par les coureurs
                _fenetre(b, -W / 4, yb, 2.0, 3.0, cd, croix=1)
            continue
        xs = [W / 4] if i == 0 else [-W / 4, W / 4]
        for j, x in enumerate(xs):
            fl = S["fleurs"] if (fleurs and i == 1 and j == len(xs) - 1) else None
            _fenetre(b, x, yb, 2.0, 3.0, cd, croix=1 if i == n - 1 else False, fleurs=fl)


def maison_port(b, variant=0, largeur=18, profondeur=14, etages=2):
    """Maison colorée du bourg du port : soubassement de pierre claire, enduit de couleur en « pixels »,
    bandeaux et chaînes d'angle, fenêtres à volets et jardinières, porte à imposte, vitrine à auvent rayé,
    balcon, tourelle ou lucarne selon la variante ; toit à deux pans studdé (égouts ou pignon sur rue)."""
    rng = b.rng
    S = _style_maison(variant)
    W, D = float(largeur), float(profondeur)
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    n = max(1, int(etages))
    H = H1 + (n - 1) * HE
    mur, ch, cd = S["mur"], S["chaine"], S["cadre"]

    # --- volumes --------------------------------------------------------------------------------
    with b.group("Volume"):
        b.box((x0 - 0.3, 0, zf - 0.3), (x1 + 0.3, YP, zb + 0.3), vr(S["socle"], rng, 0.03), name="Soubassement")
        for i in range(n):
            ya = 0.0 if i == 0 else H1 + (i - 1) * HE
            b.box((x0, ya, zf), (x1, H1 + i * HE, zb), vr(mur, rng, 0.035), name="Mur")
        for i in range(n - 1):
            y = H1 + i * HE
            b.box((x0 - 0.25, y - 0.25, zf - 0.25), (x1 + 0.25, y + 0.25, zb + 0.25), col(ch), name="Bandeau")
        b.box((x0 - 0.3, H - 0.6, zf - 0.3), (x1 + 0.3, H, zb + 0.3), col(ch), name="Corniche")
        for xa, xb_ in ((x0 - 0.35, x0 + 0.65), (x1 - 0.65, x1 + 0.35)):
            for za, zz in ((zf - 0.35, zf + 0.65), (zb - 0.65, zb + 0.35)):
                b.box((xa, YP, za), (xb_, H - 0.6, zz), col(ch), name="Chaine")

    # --- toit ---------------------------------------------------------------------------------------
    with b.group("Toit"):
        if S["forme"] == "long":
            top, y_pan = _toit_long(b, x0, x1, zf, zb, H, 0.7, S["toit"], mur, rng)
        else:
            pente = 0.75 if W <= 18 else 0.7
            top = _toit_pignon(b, x0, x1, zf, zb, H, pente, S["toit"], mur, rng, rive=S.get("rive"))
            y_pan = None
        if S.get("mouette") and n <= 2:
            from assets.mobilier import mouette
            if S["forme"] == "long":
                with b.at((x0 + W * 0.3, top, 0.0), yaw=20):
                    mouette(b, variant=0)
            else:
                with b.at((0.0, top, zf + 0.2), yaw=-15):
                    mouette(b, variant=1)
            top += 1.5
        if S["forme"] == "long" and n <= 2:
            # corbeaux sous l'avant-toit de la façade
            gap = 2.9 if W >= 17 else 1.6           # entre les fenêtres de l'étage
            for xx in (-W / 2 + 0.3, -gap, gap, W / 2 - 0.3):
                b.wedge_under((xx - 0.3, H - 1.6, zf - 0.85), (xx + 0.3, H - 0.6, zf + 0.1), col(ch), down="-z",
                              name="Corbeau")
        if S.get("cheminee"):
            xc = x1 - 2.6 if S["porte_cote"] > 0 else x0 + 2.6
            zc = zb - 3.2
            haut = top + (3.5 if S.get("cheminee_haute") else 1.2)
            top = max(top, _cheminee(b, xc, zc, H, haut, S["cheminee"], rng, s=1.8 if S.get("cheminee_haute") else 1.6))
        if S.get("lucarne") and y_pan is not None:
            _lucarne(b, 0.0 if W < 18 else -W / 4 + 0.5, zf, H, y_pan, S, rng)
        if S.get("pignon_bois"):
            with b.at((0, 0, zf)):
                _pignon_bois(b, x0, x1, H, (x1 - x0) / 2 * pente, S)
        elif S["forme"] == "pignon":
            with b.at((0, 0, zf)):
                _hublot(b, 0.0, H + (x1 - x0) / 2 * pente * 0.42, 0.75, cadre=S["cadre"], lumiere=False)
        else:
            # hublots dans les pignons latéraux (ils regardent le long de la rue, au-dessus des voisins)
            for xg, yaw in ((x1, -90), (x0, 90)):
                with b.at((xg, 0, 0), yaw=yaw):
                    _hublot(b, 0.0, H + (D / 2) * 0.7 * 0.4, 0.7, cadre=S["cadre"], lumiere=False)

    # --- façade avant -----------------------------------------------------------------------------
    with b.at((0, 0, zf), group="FacadeAvant"):
        _facade_avant(b, S, W, n, H, rng)

    # --- côtés et arrière ------------------------------------------------------------------------
    with b.at((x1, 0, 0), yaw=-90, group="CoteDroit"):
        _fenetres_cote(b, D, n, S, H)
    with b.at((x0, 0, 0), yaw=90, group="CoteGauche"):
        _fenetres_cote(b, D, n, S, H)
    with b.at((0, 0, zb), yaw=180, group="Arriere"):
        _fenetres_cote(b, W, n, S, H, arriere=True, fleurs=True)
        _porte(b, -W / 4 if W >= 15 else 0.0, 2.6, 4.8, "bois", cd, imposte=False, poignee=False)

    if S.get("tourelle"):
        with b.group("Tourelle"):
            top = max(top, _tourelle(b, x1 - 1.6, zf + 0.7, H, S, rng))
    return {"emprise": (W, D), "hauteur": round(top, 2)}


def _facade_avant(b, S, W, n, H, rng):
    """Façade sur rue d'une maison (repère de façade : mur en z = 0, rue vers -z)."""
    cd, mur = S["cadre"], S["mur"]
    s = S["porte_cote"]
    xd = s * (W / 2 - 3.0)                    # porte près d'un angle
    dw, dh = 3.0, 4.9
    # rez-de-chaussée
    _porte(b, xd, dw, dh, S["porte"], cd)
    autre = -s * (W / 2 - 1.0)                # bord opposé utile
    lim = xd - s * (dw / 2 + 1.2)
    if S["rdc"] == "boutique":
        xa, xb = sorted((autre, lim))
        xc, ww = (xa + xb) / 2, xb - xa - 0.6
        _vitrine(b, xc, ww, cd)
        a, bb = S["auvent"]
        _auvent(b, xc - ww / 2 - 0.5, xc + ww / 2 + 0.5, H1 - 0.35, a, bb, prof=1.8, y_bas=7.25)
    else:
        xa, xb = sorted((autre, lim))
        span = xb - xa
        if span >= 10.4:
            for x in (xa + span * 0.25, xa + span * 0.75):
                _fenetre(b, x, YP + 1.6, 2.2, 3.4, cd, volets=S["volet"], croix=2, appui=True)
        else:
            # rez étroit : une fenêtre à volets et une petite fenêtre à jardinière
            xg, xp = (xa + 2.7, xb - 1.6) if s < 0 else (xb - 2.7, xa + 1.6)
            _fenetre(b, xg, YP + 1.6, 2.2, 3.4, cd, volets=S["volet"], croix=2, appui=True)
            _fenetre(b, xp, YP + 2.4, 1.6, 2.6, cd, croix=1, fleurs=S["fleurs"])
    # décor près de la porte
    xdeco = xd - s * (dw / 2 + 1.0)
    if S["deco"] == "bouee" and S["rdc"] != "boutique":
        _bouee_murale(b, xdeco, 4.6, 0.9)
    elif S["deco"] == "bouee":
        _bouee_murale(b, xd + s * (dw / 2 + 1.25), 4.8, 0.8)
    else:
        _lanterne_murale(b, xd + s * (dw / 2 + 1.0), 4.4)
    if n <= 2:
        _pot(b, xd + s * (dw / 2 + 0.9), -0.5, S["fleurs"])
    # enduit « pixel » et moellons apparents
    xt = s * (W / 2 - 1.6)
    _taches(b, [(xt - 0.9, 6.4, xt + 0.9, 7.6), (-W / 2 + 1.0, H1 + 0.6, -W / 2 + 2.6, H1 + 1.3)], mur, rng)
    if n <= 2 and S["rdc"] != "boutique":
        _pierres(b, -W / 2 + 1.0 if s > 0 else W / 2 - 3.5, 6.55, rng)
    elif n <= 2:
        _taches(b, [(xd - s * 0.5 - 0.8, H1 + 0.7, xd - s * 0.5 + 0.8, H1 + 1.25)], mur, rng)
    # étages
    for i in range(1, n):
        y = H1 + (i - 1) * HE + 1.6
        if i == 1 and S.get("balcon"):
            _balcon(b, 0.0, H1, 6.4 if W >= 17 else 5.6, S, rng)
            xs = [-(W / 2 - 2.6), W / 2 - 2.6]
            for x in xs:
                _fenetre(b, x, y, 2.0, 3.4, cd, volets=S["volet"], croix=2)
            continue
        if S.get("colombage") and i == 1:
            _colombage(b, W, H1 + 0.25, H1 + HE - 0.25 if n > 2 else H - 0.6, S)
        if S.get("tourelle"):
            xs = [-(W / 2 - 3.2), 0.6 if W >= 17 else -0.4]     # l'angle +x est pris par la tourelle
        elif W >= 17:
            xs = [-(W / 2 - 3.2), 0.0, W / 2 - 3.2]
        else:
            xs = [-(W / 2 - 3.0), W / 2 - 3.0]
        for j, x in enumerate(xs):
            fl = S["fleurs"] if i == 1 and (j == len(xs) // 2 or (len(xs) == 2 and j == 1)) else None
            _fenetre(b, x, y, 2.2, 3.4, cd, volets=S["volet"], croix=2, fleurs=fl)


def _vitrine(b, x, w, cadre):
    """Vitrine de boutique : cadre, grande vitre, deux meneaux, tablette stud."""
    cd = col(cadre)
    y0, y1 = YP + 1.0, 6.6
    b.box((x - w / 2 - 0.4, y0 - 0.3, -0.14), (x + w / 2 + 0.4, y1 + 0.4, 0.2), cd, name="Cadre")
    b.box((x - w / 2, y0, -0.22), (x + w / 2, y1, 0.1), col("vitre"), name="Vitrine")
    for k in (1, 2):
        xx = x - w / 2 + k * w / 3
        b.box((xx - 0.14, y0, -0.36), (xx + 0.14, y1, -0.22), cd, name="Meneau", **ND)
    b.box((x - w / 2 - 0.6, y0 - 0.7, -0.75), (x + w / 2 + 0.6, y0 - 0.2, 0.2), cd, studs="top", name="Tablette")


def _balcon(b, x, y, w, S, rng):
    """Balcon de l'étage (dalle stud à 1,8 du mur, consoles, garde-corps) devant une porte-fenêtre."""
    cd = col(S["cadre"])
    prof = 1.8 if S.get("balcon") != "fleuri" else 1.35
    yb = y - 0.1                            # dessous de la dalle (≠ bandeau)
    yt = y + 0.6
    b.box((x - w / 2, yb, -prof), (x + w / 2, yt, 0.2), vr("bois_pale" if S["mur"] != "mur_rose" else "pierre_claire", rng, 0.03),
          studs="top", name="Balcon")
    for xx in (x - w / 2 + 0.6, x + w / 2 - 0.6):
        b.wedge_under((xx - 0.3, yb - 1.2, -prof + 0.4), (xx + 0.3, yb, 0.1), cd, down="-z", name="Console")
    # porte-fenêtre
    pw, ph = 2.6, 4.4
    b.box((x - pw / 2 - 0.3, yt, -0.12), (x + pw / 2 + 0.3, yt + ph + 0.3, 0.2), cd, name="Cadre")
    b.box((x - pw / 2, yt, -0.2), (x + pw / 2, yt + ph, 0.1), col("vitre"), name="PorteFenetre")
    b.box((x - 0.12, yt, -0.34), (x + 0.12, yt + ph, -0.2), cd, name="Meneau", **ND)
    b.box((x - pw / 2, yt + ph * 0.62 - 0.1, -0.3), (x + pw / 2, yt + ph * 0.62 + 0.1, -0.2), cd, name="Traverse", **ND)
    # garde-corps
    rh = 2.2
    rc = col(S["volet"]) if S["volet"] != "blanc" else col("blanc")
    b.box((x - w / 2, yt + rh - 0.3, -prof), (x + w / 2, yt + rh, -prof + 0.35), rc, studs="top", name="Lisse")
    for sx in (-1, 1):
        xe = x + sx * (w / 2 - 0.175)
        b.box((xe - 0.175, yt + rh - 0.3, -prof + 0.35), (xe + 0.175, yt + rh, 0.0), rc, studs="top", name="Lisse")
    nb = int(round(w / 1.1))
    for i in range(nb + 1):
        xx = x - w / 2 + 0.2 + i * (w - 0.4) / nb
        b.box((xx - 0.1, yt, -prof + 0.07), (xx + 0.1, yt + rh - 0.3, -prof + 0.27), rc, name="Balustre", **ND)
    if S.get("balcon") == "fleuri":
        for sx in (-1, 1):
            xx = x + sx * (w / 4 + 0.2)
            b.box((xx - 1.0, yt + rh - 1.0, -prof - 0.55), (xx + 1.0, yt + rh - 0.2, -prof + 0.02), col("bois"), name="Jardiniere", **ND)
            b.box((xx - 0.9, yt + rh - 0.2, -prof - 0.5), (xx + 0.9, yt + rh + 0.3, -prof - 0.03), col("feuillage"), name="Feuilles", **ND)
            for dx in (-0.5, 0.5):
                b.ball((xx + dx, yt + rh + 0.35, -prof - 0.25), 0.36, col(S["fleurs"] if dx < 0 else "fleur_blanche"), name="Fleur", **NDS)
        b.cyl((x + w / 2 - 0.9, yt + 0.6, -0.9), 0.5, 1.2, col("terre_claire"), name="Pot", **ND)
        b.ball((x + w / 2 - 0.9, yt + 1.5, -0.9), 0.75, col("feuillage"), name="Plante", **ND)


def _colombage(b, W, ya, yb, S):
    """Pans de bois de l'étage (poteaux, sablières, écharpes), en saillie de 0,15."""
    cb = col("colombage")
    e = 0.45
    b.box((-W / 2 + 0.65, ya, -0.18), (W / 2 - 0.65, ya + e, 0.1), cb, name="Sabliere", **ND)
    b.box((-W / 2 + 0.65, yb - e, -0.18), (W / 2 - 0.65, yb, 0.1), cb, name="Sabliere", **ND)
    xs = [-(W / 2 - 1.2), -1.6, 1.6, W / 2 - 1.2]
    for x in xs:
        b.box((x - e / 2, ya + e, -0.16), (x + e / 2, yb - e, 0.1), cb, name="Poteau", **ND)
    # écharpes en croix de Saint-André entre les deux poteaux du milieu
    for (pa, pb) in (((-1.6, ya + e), (1.6, yb - e)), ((1.6, ya + e), (-1.6, yb - e))):
        _barre(b, pa, pb, e, -0.15, 0.1, cb, name="Echarpe", **ND)


def _pignon_bois(b, x0, x1, H, hu, S):
    """Pignon sur rue à colombage (repère de façade) : entrait, poinçon, arbalétriers, deux jours."""
    cb = col("colombage")
    xm = (x0 + x1) / 2
    e = 0.5
    b.box((x0 + 0.4, H, -0.2), (x1 - 0.4, H + e, 0.1), cb, name="Entrait", **ND)
    b.box((xm - 0.3, H + e, -0.2), (xm + 0.3, H + hu - 0.4, 0.1), cb, name="Poincon", **ND)
    for sx in (-1, 1):
        _barre(b, (xm + sx * 0.3, H + e + 0.4), (xm + sx * (x1 - x0) * 0.3, H + e), e, -0.18, 0.1, cb, name="Contrefiche", **ND)
    for sx in (-1, 1):
        xx = xm + sx * (x1 - x0) * 0.17
        b.box((xx - 0.7, H + 1.6, -0.14), (xx + 0.7, H + 2.9, 0.1), col("vitre"), name="Jour")


def _lucarne(b, x, zf, H, y_pan, S, rng):
    """Lucarne à deux pans sur le pan avant (toit à égouts sur rue)."""
    w = 3.4
    zl = zf + 1.6
    ybas = y_pan(zl) - 0.8
    yh = ybas + 3.4
    z_fond = zf + 5.0
    b.box((x - w / 2, ybas, zl), (x + w / 2, yh, z_fond), vr(S["mur"], rng, 0.03), name="Lucarne")
    t = col(S["toit"])
    b.wedge((x - w / 2 - 0.5, yh, zl - 0.5), (x, yh + 1.6, z_fond), t, down="-x", studs="top", name="ToitLucarne")
    b.wedge((x, yh, zl - 0.5), (x + w / 2 + 0.5, yh + 1.6, z_fond), t, down="+x", studs="top", name="ToitLucarne")
    with b.at((0, 0, zl)):
        _fenetre(b, x, ybas + 1.0, 1.6, 1.9, S["cadre"], croix=1, appui=False)


def _tourelle(b, x, z, H, S, rng):
    """Tourelle d'angle en encorbellement (cylindre sur culots, toit conique en gradins studdés)."""
    r = 2.2
    y0 = H1 - 1.0
    b.cyl((x, y0 - 0.25, z), r - 0.9, 0.5, col(S["chaine"]), name="Culot")
    b.cyl((x, y0 + 0.35, z), r - 0.4, 0.7, col(S["chaine"]), name="Culot")
    ytop = H + 2.2
    b.cyl((x, (y0 + 0.7 + ytop) / 2, z), r, ytop - y0 - 0.7, vr(S["mur"], rng, 0.03), name="Tourelle")
    b.cyl((x, ytop - 0.3, z), r + 0.25, 0.6, col(S["chaine"]), name="Corniche")
    # fenêtres de la tourelle (vers la rue et vers le côté)
    for (dx, dz, yaw) in ((0, -1, 0), (-0.7071, -0.7071, 45)):
        cx, cz = x + dx * (r - 0.25), z + dz * (r - 0.25)
        for yy in (H1 + 1.6, H1 + 1.6 + HE) if H > H1 + HE else (H1 + 1.6,):
            b.boxc((cx, yy + 1.5, cz), (1.3, 3.0, 0.7), col("vitre"), yaw=yaw, name="Vitre")
            b.boxc((cx, yy - 0.2, cz), (1.9, 0.4, 0.8), col(S["cadre"]), yaw=yaw, studs="top", name="Appui")
    # toit conique en gradins
    t = col(S["toit"])
    y = ytop
    for k, (rr, hh) in enumerate(((r + 0.3, 1.0), (r - 0.2, 1.0), (r - 0.8, 1.0), (r - 1.4, 1.0), (0.5, 1.2))):
        b.cyl((x, y + hh / 2, z), rr, hh, vary(t, rng, 0.04) if k % 2 else t, studs="top", name="Toit")
        y += hh
    b.ball((x, y + 0.3, z), 0.45, col("or"), name="Epi", **ND)
    return y + 0.75


# ---------------------------------------------------------------------------
# TAVERNE
# ---------------------------------------------------------------------------


def _mur_colombage(b, W, ya, yb, xs, *, croix=(), e=0.45, couleur="colombage"):
    """Pans de bois sur un mur (repère de façade) : sablières haute et basse, poteaux en xs, écharpes
    en croix entre les paires (xa, xb) de `croix`."""
    cb = col(couleur)
    b.box((-W / 2 + 0.7, ya, -0.18), (W / 2 - 0.7, ya + e, 0.1), cb, name="Sabliere", **ND)
    for x in xs:
        b.box((x - e / 2, ya + e, -0.16), (x + e / 2, yb, 0.1), cb, name="Poteau", **ND)
    for (xa, xb) in croix:
        _barre(b, (xa, ya + e), (xb, yb), e * 0.9, -0.14, 0.1, cb, name="Echarpe", **ND)
        _barre(b, (xb, ya + e), (xa, yb), e * 0.9, -0.13, 0.1, cb, name="Echarpe", **ND)


def _hublot(b, x, y, r, cadre="laiton", lumiere=True):
    """Hublot rond (cerclage de laiton, verre éclairé) sur un mur (repère de façade)."""
    b.cyl((x, y, -0.15), r + 0.3, 0.5, col(cadre), axis="z", name="Hublot")
    b.cyl((x, y, -0.25), r, 0.5, col("fenetre_lumiere" if lumiere else "vitre"), axis="z",
          material="Neon" if lumiere else "SmoothPlastic", name="Verre", **ND)


def _table_tonneau(b, x, y, z, rng):
    """Tonneau debout servant de table (plateau rond stud, cercle de fer, chope)."""
    b.cyl((x, y + 1.1, z), 0.8, 2.2, vr("bois", rng, 0.06), name="Tonneau")
    b.cyl((x, y + 1.1, z), 0.88, 0.25, col(FER), name="Cercle", **ND)
    b.cyl((x, y + 2.32, z), 1.15, 0.25, col("bois_pale"), studs="top", name="Plateau")
    b.cyl((x + 0.35, y + 2.75, z - 0.2), 0.25, 0.6, col("laiton"), name="Chope", **NDS)


def taverne(b, variant=0, largeur=24, profondeur=20):
    """Taverne de pirates, repère du bourg : rez de pierre à porche couvert (mur en retrait de 4 sous l'étage,
    poteaux et liens), étage crème à pans de bois avec grande enseigne « TAVERNE » et hublot, enseigne
    suspendue perpendiculaire lisible des deux côtés, porte double entre deux lanternes, fenêtres éclairées,
    fond de tonneau géant, bancs et tables-tonneaux ; toit de tuiles rouge sombre studdé, cheminée,
    vigie et pavillon pirate générique sur le faîtage."""
    from assets.mobilier import banc, drapeau_pirate
    rng = b.rng
    W, D = float(largeur), float(profondeur)
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    PR = 4.0                     # profondeur du porche
    zr = zf + PR                 # mur du rez, en retrait
    Y1 = 10.0                    # dessous de l'étage (plafond du porche)
    H = Y1 + 7.0                 # haut des murs
    bf, bp = col("colombage"), col("bois_fonce")
    v = variant % 2

    # --- volumes ------------------------------------------------------------------------------------
    with b.group("Volume"):
        b.box((x0, 0, zr), (x1, Y1, zb), vr(GRES, rng, 0.03), name="Rez")
        b.box((x0 - 0.3, 0, zr - 0.3), (x1 + 0.3, 1.2, zb + 0.3), vr("pierre_fonce", rng, 0.03), name="Soubassement")
        b.box((x0, 0, zf), (x1, 0.6, zr - 0.3), vr("bois_quai", rng, 0.03), studs="top", name="Plancher")
        b.box((-3.2, 0, zf - 0.9), (3.2, 0.3, zf + 0.1), col("pierre_fonce"), studs="top", name="Marche")
        for xa, xb in ((x0, x0 + 0.8), (x1 - 0.8, x1)):
            b.box((xa, 0.6, zf + 1.0), (xb, 2.8, zr - 0.3), vr(GRES, rng, 0.04), studs="top", name="Muret")
        b.box((x0, Y1, zf), (x1, H, zb), vr("mur_creme", rng, 0.025), name="Etage")
        # sablière basse (ceinture de l'étage), poutre de rive sur le porche, solives sous le plafond
        b.box((x0 - 0.3, Y1 - 0.2, zf - 0.3), (x1 + 0.3, Y1 + 0.6, zb + 0.3), bf, name="Sabliere")
        b.box((x0, Y1 - 1.0, zf), (x1, Y1 - 0.2, zf + 0.9), bp, name="Poutre")
        for x in (-7.8, 0.0, 7.8):
            b.box((x - 0.35, Y1 - 0.6, zf + 0.9), (x + 0.35, Y1, zr), bp, name="Solive")
        b.box((x0 - 0.3, H - 0.6, zf - 0.3), (x1 + 0.3, H, zb + 0.3), bf, name="Corniche")
        for xa, xb_ in ((x0 - 0.38, x0 + 0.62), (x1 - 0.62, x1 + 0.38)):
            for za, zz in ((zf - 0.38, zf + 0.62), (zb - 0.62, zb + 0.38)):
                b.box((xa, Y1 + 0.6, za), (xb_, H - 0.6, zz), bf, name="Cornier")
        # chaînes d'angle de pierre au rez (arrière)
        for xa, xb_ in ((x0 - 0.35, x0 + 0.65), (x1 - 0.65, x1 + 0.35)):
            b.box((xa, 1.2, zb - 0.65), (xb_, Y1 - 0.2, zb + 0.35), col("pierre_claire"), name="Chaine")
            b.box((xa, 1.2, zr - 0.35), (xb_, Y1 - 0.2, zr + 0.65), col("pierre_claire"), name="Chaine")

    # --- porche : poteaux et liens -----------------------------------------------------------------
    with b.group("Porche"):
        xp = (x0 + 0.5, -6.6, 6.6, x1 - 0.5)
        for i, x in enumerate(xp):
            b.box((x - 0.4, 0.6, zf + 0.1), (x + 0.4, Y1 - 1.0, zf + 0.9), bp, name="Poteau")
            b.box((x - 0.55, 0.6, zf - 0.05), (x + 0.55, 1.3, zf + 1.05), col("pierre_fonce"), name="Base")
            for s in (-1, 1):
                if (i == 0 and s < 0) or (i == 3 and s > 0):
                    continue
                xa, xb = sorted((x + s * 0.4, x + s * 1.8))
                b.wedge_under((xa, Y1 - 2.4, zf + 0.25), (xb, Y1 - 1.0, zf + 0.75), bp, down="+x" if s > 0 else "-x",
                              name="Lien")

    # --- façade du rez (en retrait) -----------------------------------------------------------------
    with b.at((0, 0, zr), group="Rez"):
        # porte double à imposte éclairée
        b.box((-2.7, 0.6, -0.16), (2.7, 7.6, 0.2), bp, name="Chambranle")
        for sx in (-1, 1):
            xa, xb = sorted((sx * 0.06, sx * 2.25))
            b.box((xa, 0.6, -0.32), (xb, 6.5, 0.1), vr("bois", rng, 0.04), name="Vantail")
            b.ball((sx * 0.45, 3.6, -0.42), 0.2, col("laiton"), name="Anneau", **NDS)
        for y in (1.6, 5.3):
            b.box((-2.25, y, -0.42), (2.25, y + 0.3, -0.3), col(FER), name="Penture", **ND)
        b.box((-2.25, 6.7, -0.28), (2.25, 7.4, 0.1), col("fenetre_lumiere"), material="Neon", name="Imposte")
        for sx in (-1, 1):
            _lanterne_murale(b, sx * 3.7, 4.6)
        # fenêtre éclairée et banc (côté -x), fond de tonneau géant (côté +x)
        xw = -8.4 if v == 0 else 8.4
        xt = -xw
        _fenetre(b, xw, 3.3, 3.4, 3.0, "colombage", croix=2, lumiere=True, appui=False, volets="volet_rouge")
        with b.at((xw, 0.6, -1.15)):
            banc(b, variant=2)
        yc, R = 3.5, 2.85
        b.cyl((xt, yc, -0.6), R, 1.3, vr("bois", rng, 0.05), axis="z", name="TonneauGeant")
        b.cyl((xt, yc, -1.35), R + 0.12, 0.35, col(FER), axis="z", name="Cercle")
        b.cyl((xt, yc, -1.45), R - 0.45, 0.35, vr("bois_clair", rng, 0.03), axis="z", name="Fond")
        for dx in (-0.9, 0.9):
            b.box((xt + dx - 0.07, yc - 2.0, -1.68), (xt + dx + 0.07, yc + 2.0, -1.55), col("bois_fonce"), name="Douelle", **NDS)
        b.cyl((xt, yc - 1.3, -1.9), 0.25, 0.8, col("laiton"), axis="z", name="Robinet", **ND)
        b.box((xt - 0.12, yc - 1.3, -2.25), (xt + 0.12, yc - 0.85, -2.05), col("laiton"), name="Clef", **NDS)
        # moellons de teintes proches
        for (x, y, w, h) in ((-11.0, 7.4, 1.6, 0.8), (-9.6, 8.25, 1.2, 0.7), (-5.4, 8.2, 1.4, 0.7), (4.4, 7.9, 1.4, 0.8),
                             (9.6, 8.3, 1.6, 0.7), (-11.2, 1.5, 1.3, 0.8), (5.0, 1.4, 1.2, 0.7)):
            b.box((x, y, -0.12), (x + w, y + h, 0.1), vr("pierre_claire" if (x * 7 + y) % 2 < 1 else "pierre_fonce", rng, 0.04),
                  name="Moellon", **NDS)
    # tables-tonneaux sur le porche
    with b.group("Porche"):
        _table_tonneau(b, xw, 0.6, zf + 1.35, rng)
        _table_tonneau(b, xt + (1.6 if xt > 0 else -1.6), 0.6, zf + 1.35, rng)

    # --- façade de l'étage --------------------------------------------------------------------------
    with b.at((0, 0, zf), group="Etage"):
        _mur_colombage(b, W, Y1 + 0.6, H - 0.6, (-5.6, 5.6), croix=())
        for sx in (-1, 1):
            _fenetre(b, sx * 8.6, Y1 + 1.6, 2.6, 3.4, "colombage", croix=2, lumiere=True, volets="volet_rouge",
                     fleurs="fleur_rouge" if sx < 0 else "fleur_jaune")
        # grande enseigne « TAVERNE »
        b.box((-5.0, Y1 + 0.9, -0.35), (5.0, Y1 + 3.9, 0.1), bp, name="Cadre")
        pan = b.box((-4.6, Y1 + 1.2, -0.5), (4.6, Y1 + 3.6, -0.2), col("bois_pale"), name="Enseigne")
        pan.label = {"face": "Front", "text": "TAVERNE", "color": hexrgb("#7A2A1C"), "font": "sans"}
        _hublot(b, 0.0, Y1 + 5.2, 0.85)
        for sx in (-1, 1):
            b.box((sx * 2.2 - 0.22, Y1 + 3.9, -0.16), (sx * 2.2 + 0.22, H - 0.6, 0.1), bf, name="Poteau", **ND)

    # --- enseigne suspendue perpendiculaire (lisible à l'aller et au retour) -------------------------
    with b.group("Enseigne"):
        xs = -4.7 if v == 0 else 4.7
        b.box((xs - 0.13, Y1 - 1.0 - 0.3, zf - 1.7), (xs + 0.13, Y1 - 1.0, zf + 2.6), col(FER), name="Potence", **ND)
        b.box((xs - 0.1, Y1 - 1.0, zf + 2.35), (xs + 0.1, Y1, zf + 2.55), col(FER), name="Suspente", **ND)
        b.ball((xs, Y1 - 1.15, zf - 1.72), 0.22, col(FER), name="Bouton", **NDS)
        for z in (zf - 1.3, zf + 1.9):
            b.box((xs - 0.06, 8.55, z - 0.06), (xs + 0.06, Y1 - 1.3, z + 0.06), col(FER), name="Chainette", **NDS)
        for k, face in enumerate(("Front", "Back")):
            p = b.part("block", (4.2, 1.85, 0.16), (xs + (-0.08 if k == 0 else 0.08), 7.62, zf + 0.3), rot_y(90),
                       col("bois_pale"), name="Panneau", **ND)
            p.label = {"face": face, "text": "TAVERNE", "color": hexrgb("#7A2A1C"), "font": "sans"}
        b.part("block", (4.5, 2.15, 0.2), (xs, 7.62, zf + 0.3), rot_y(90), bp, name="Bordure", **ND)

    # --- côtés et arrière ---------------------------------------------------------------------------
    for (pos, yaw, nom, larg) in (((x1, 0, 0), -90, "CoteDroit", D), ((x0, 0, 0), 90, "CoteGauche", D),
                                  ((0, 0, zb), 180, "Arriere", W)):
        with b.at(pos, yaw=yaw, group=nom):
            if nom == "Arriere":
                _mur_colombage(b, larg, Y1 + 0.6, H - 0.6, (-4.0, 4.0))
                for x in (-8.0, 0.0, 8.0):
                    _fenetre(b, x, Y1 + 1.8, 2.2, 3.0, "colombage", croix=1, lumiere=(x == 0.0))
                _porte(b, 6.0, 3.0, 5.6, "bois", "colombage", y0=1.2, imposte=False, poignee=False)
                _fenetre(b, -6.0, 3.6, 2.2, 2.6, "colombage", croix=1, lumiere=True)
            else:
                _mur_colombage(b, larg, Y1 + 0.6, H - 0.6, (0.0,), croix=((-6.6, -2.2),) if nom == "CoteDroit" else ((2.2, 6.6),))
                xw_ = 4.4 if nom == "CoteDroit" else -4.4
                _fenetre(b, xw_, Y1 + 1.8, 2.2, 3.0, "colombage", croix=1, lumiere=True)
                _fenetre(b, (2.0 if nom == "CoteDroit" else -2.0) + 0.0, 3.6, 2.0, 2.6, "colombage", croix=1, lumiere=True)

    # --- toit ---------------------------------------------------------------------------------------
    with b.group("Toit"):
        top, y_pan = _toit_long(b, x0, x1, zf, zb, H, 0.62, "toit_rouge_fonce", "mur_creme", rng, deb_av=1.3,
                                deb_ar=1.0, deb_cote=0.8)
        hu = (D / 2) * 0.62
        for xg, yaw in ((x1, -90), (x0, 90)):
            with b.at((xg, 0, 0), yaw=yaw):
                b.box((-D / 2 + 0.6, H, -0.2), (D / 2 - 0.6, H + 0.5, 0.1), bf, name="Entrait", **ND)
                b.box((-0.3, H + 0.5, -0.2), (0.3, H + hu - 0.3, 0.1), bf, name="Poincon", **ND)
                for sx in (-1, 1):
                    _barre(b, (sx * 0.3, H + 2.6), (sx * 4.6, H + 0.5), 0.45, -0.18, 0.1, bf, name="Contrefiche", **ND)
        top = max(top, _cheminee(b, x1 - 3.4, zb - 4.0, H, top + 2.4, "pierre", rng, s=2.0))
        # lucarne éclairée sur le pan avant
        xl = 5.0 if v == 0 else -5.0
        zl = zf + 2.0
        ybas = y_pan(zl) - 0.9
        b.box((xl - 1.9, ybas, zl), (xl + 1.9, ybas + 3.4, zf + 6.5), vr("mur_creme", rng, 0.03), name="Lucarne")
        tt = col("toit_rouge_fonce")
        b.wedge((xl - 2.4, ybas + 3.4, zl - 0.5), (xl, ybas + 5.0, zf + 6.5), tt, down="-x", studs="top", name="ToitLucarne")
        b.wedge((xl, ybas + 3.4, zl - 0.5), (xl + 2.4, ybas + 5.0, zf + 6.5), tt, down="+x", studs="top", name="ToitLucarne")
        with b.at((0, 0, zl)):
            _fenetre(b, xl, ybas + 1.1, 1.8, 1.9, "colombage", croix=1, appui=False, lumiere=True)
        # vigie et pavillon sur le faîtage
        xm = -6.0 if v == 0 else 6.0
        yr = H + hu + 0.8 * math.hypot(1, 0.62)          # dessus du faîtage
        ym = yr + 9.5
        b.cyl((xm, (yr - 1.0 + ym) / 2, 0), 0.32, ym - yr + 1.0, col("bois_fonce"), name="Mat")
        b.cyl((xm, yr + 5.2, 0), 1.5, 0.35, col("bois"), studs="top", name="Plancher")
        b.cyl((xm, yr + 5.95, 0), 1.35, 1.15, vr("bois", rng, 0.05), name="Nid")
        b.cyl((xm, yr + 6.6, 0), 1.5, 0.25, col("bois_fonce"), name="Bord", **ND)
        for sx in (-1, 1):
            p0 = (xm + sx * 3.2, yr - 0.3)
            p1 = (xm + sx * 1.2, yr + 5.0)
            _barre(b, p0, p1, 0.1, -0.05, 0.05, col("corde_fonce"), name="Hauban", **NDS)
        with b.at((xm, ym - 4.8, 0)):
            drapeau_pirate(b, variant=0, hauteur=4.8, largeur=4.2, mat=False)
        b.ball((xm, ym + 0.25, 0), 0.4, col("or"), name="Pomme", **ND)
        top = max(top, ym + 0.65)
    return {"emprise": (W, D), "hauteur": round(top, 2)}


# ---------------------------------------------------------------------------
# ÉTAL DE MARCHÉ
# ---------------------------------------------------------------------------
_ETALS = [
    dict(toile="toile_rouge", texte="FRUITS", encre="#8E2A1E"),
    dict(toile="toile_jaune", texte="VIANDE", encre="#7A3B1E"),
    dict(toile="toile_bleue", texte="POISSONS", encre="#1F4C8A"),
]


def _poisson(b, x, y, z, L, couleur, yaw=0.0, debout=False):
    """Petit poisson : corps et queue (couché à plat, ou suspendu tête en bas si `debout`)."""
    if debout:
        b.box((x - 0.5, y - 0.35, z - 0.1), (x + 0.5, y, z + 0.1), shade(col(couleur), 0.8), name="Queue", **ND)
        b.box((x - 0.3, y - L * 0.8, z - 0.18), (x + 0.3, y - 0.35, z + 0.18), col(couleur), name="Poisson", **ND)
        b.box((x - 0.2, y - L, z - 0.14), (x + 0.2, y - L * 0.8, z + 0.14), shade(col(couleur), 0.85), name="Tete", **ND)
        return
    b.boxc((x, y + 0.2, z), (L * 0.75, 0.4, 0.5), col(couleur), yaw=yaw, name="Poisson", **ND)
    a = math.radians(yaw)
    tx, tz = x + math.cos(a) * L * 0.47, z - math.sin(a) * L * 0.47
    b.boxc((tx, y + 0.2, tz), (L * 0.22, 0.25, 0.75), shade(col(couleur), 0.85), yaw=yaw, name="Queue", **ND)


def _viande_os(b, x, y_haut, z, s=1.0):
    """Morceau de viande sur l'os suspendu à un crochet (os vertical)."""
    b.cyl((x, y_haut - 1.3 * s, z), 0.15 * s, 2.6 * s, col("os_viande"), name="Os", **ND)
    b.ball((x, y_haut - 1.15 * s, z), 0.66 * s, col("viande"), name="Viande", **ND)
    b.ball((x, y_haut - 1.7 * s, z), 0.56 * s, col("viande_fonce"), name="Viande", **ND)
    for dx in (-0.18, 0.18):
        b.ball((x + dx * s, y_haut - 2.6 * s, z), 0.21 * s, col("os_viande"), name="Bout", **NDS)


def etal(b, variant=0):
    """Étal de marché 8 × 6 ouvert vers l'avant (-Z) : quatre poteaux, comptoir à tablette stud, étagère en
    gradins au fond, toile rayée en pente (bandes couleur / blanc, lambrequin), enseigne sur la toile lisible
    des deux côtés. 0 : fruits (cageots de mandarines, pommes, bananes, pastèques, raisin) ; 1 : viande sur
    l'os (morceaux aux crochets, grosse viande en enseigne sur le toit) ; 2 : poissons sur glace."""
    rng = b.rng
    v = variant % 3
    S = _ETALS[v]
    W, D = 8.0, 6.0
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    bois, bp = vr("bois", rng, 0.04), col("bois_fonce")
    yt_av, yt_ar = 7.7, 8.9                 # dessus de la toile au droit de l'avant / de l'arrière
    pente = (yt_ar - yt_av) / D
    ep = 0.3

    def y_toile(z):                          # dessus de la toile
        return yt_av + (z - zf) * pente

    # poteaux (ceux de devant montent jusqu'à l'enseigne)
    for x in (x0 + 0.3, x1 - 0.3):
        b.box((x - 0.3, 0, zf + 0.1), (x + 0.3, 10.0, zf + 0.7), bois, name="Poteau")
        b.box((x - 0.3, 0, zb - 0.7), (x + 0.3, y_toile(zb - 0.4) - 0.1, zb - 0.1), bois, name="Poteau")
        if v != 1:
            b.ball((x, 10.25, zf + 0.4), 0.38, col("or"), name="Pomme", **ND)
    # comptoir et tablette
    b.box((x0 + 0.6, 0, zf + 0.2), (x1 - 0.6, 2.9, zf + 1.6), vr("bois_clair", rng, 0.04), name="Comptoir")
    b.box((x0 + 1.0, 0.4, zf + 0.06), (x1 - 1.0, 2.5, zf + 0.2), col(S["toile"]), name="Bandeau", **ND)
    b.box((x0 + 0.3, 2.9, zf - 0.1), (x1 - 0.3, 3.25, zf + 1.85), col("bois_pale"), studs="top", name="Tablette")
    # fond et étagère en gradins
    b.box((x0 + 0.6, 0, zb - 0.75), (x1 - 0.6, 6.4, zb - 0.45), bp, name="Fond")
    b.box((x0 + 0.6, 0, zb - 2.2), (x1 - 0.6, 2.0, zb - 0.75), vr("bois_clair", rng, 0.04), studs="top", name="Etagere")
    b.box((x0 + 0.6, 2.0, zb - 1.45), (x1 - 0.6, 3.8, zb - 0.75), vr("bois_clair", rng, 0.04), studs="top", name="Etagere")
    # toile rayée (bandes le long de X) et lambrequin
    nb = 4
    lw = (W + 0.6) / nb
    for i in range(nb):
        cc = col(S["toile"]) if i % 2 == 0 else col("blanc")
        xa = x0 - 0.3 + i * lw
        _pan_z(b, zf, yt_av, zb, yt_ar, xa, xa + lw, ep, cc, ext_a=1.0, ext_b=0.3, studs="top", name="Toile", **ND)
        yb = yt_av - 1.0 * pente - ep - 0.02
        b.box((xa, yb - 0.6, zf - 1.12), (xa + lw, yb + 0.05, zf - 0.92), cc, name="Lambrequin", **ND)
    # enseigne (deux planches dos à dos entre les poteaux)
    for k, face in enumerate(("Front", "Back")):
        z0 = zf + 0.2 + 0.2 * k
        p = b.box((x0 + 0.6, 8.35, z0), (x1 - 0.6, 9.85, z0 + 0.2), col("bois_pale"), name="Enseigne", **ND)
        p.label = {"face": face, "text": S["texte"], "color": hexrgb(S["encre"]), "font": "sans"}
    b.box((x0 + 0.6, 9.85, zf + 0.15), (x1 - 0.6, 10.1, zf + 0.65), bp, name="Chapeau", **ND)

    # marchandises
    yt = 3.25
    if v == 0:
        for i, f in enumerate(("agrume", "pomme", "banane")):
            xc = -2.4 + i * 2.4
            b.box((xc - 1.0, yt, zf + 0.1), (xc + 1.0, yt + 0.8, zf + 1.5), vr("bois_pale", rng, 0.05), name="Cageot", **ND)
            if f == "banane":
                for dz in (0.35, 0.95):
                    b.box((xc - 0.85, yt + 0.8, zf + dz - 0.25), (xc + 0.85, yt + 1.2, zf + dz + 0.25), col("banane"),
                          name="Bananes", **ND)
            else:
                b.box((xc - 0.85, yt + 0.8, zf + 0.25), (xc + 0.85, yt + 1.1, zf + 1.35), shade(col(f), 0.9), name="Fruits", **ND)
                for dx in (-0.45, 0.45):
                    b.ball((xc + dx, yt + 1.25, zf + 0.8), 0.42, col(f), name="Fruit", **ND)
        # pastèques sur l'étagère basse, l'une coupée
        for dx in (-2.2, 0.0):
            b.ball((dx, 2.0 + 0.85, zb - 1.5), 0.85, col("pasteque"), name="Pasteque", **ND)
        b.cyl((2.2, 2.0 + 0.75, zb - 1.5), 0.75, 0.3, col("pasteque_chair"), axis="z", name="Tranche", **ND)
        b.cyl((2.2, 2.0 + 0.75, zb - 1.32), 0.85, 0.3, col("pasteque"), axis="z", name="Ecorce", **ND)
        # raisin et mandarines sur l'étagère haute
        for dx in (-2.1, -1.5):
            b.ball((dx, 3.8 + 0.4, zb - 1.1), 0.42, col("raisin"), name="Raisin", **ND)
        b.box((0.6, 3.8, zb - 1.4), (2.8, 4.4, zb - 0.8), col("agrume"), studs="top", name="Mandarines", **ND)
        # régime de bananes suspendu sous la toile
        b.box((-0.07, 6.1, zf + 0.85), (0.07, y_toile(zf + 0.9) - 0.2, zf + 0.99), col("bois_fonce"), name="Tige", **NDS)
        for a in (-28, 0, 28):
            r = math.radians(a)
            b.part("block", (0.42, 1.7, 0.42), (0.75 * math.sin(r), 6.15 - 0.75 * math.cos(r), zf + 0.92), rot_z(a),
                   col("banane"), name="Banane", **ND)
    elif v == 1:
        b.box((x0 + 0.6, 6.9, zf + 0.85), (x1 - 0.6, 7.15, zf + 1.05), col(FER), name="Tringle", **ND)
        for k, x in enumerate((-2.4, 0.0, 2.4)):
            _viande_os(b, x, 6.9, zf + 0.95, s=0.9 if k != 1 else 1.05)
        b.box((-3.0, yt, zf + 0.3), (-0.6, yt + 0.25, zf + 1.6), col("bois_pale"), name="Planche", **ND)
        b.ball((-1.8, yt + 0.75, zf + 0.95), 0.65, col("viande_claire"), name="Jambon", **ND)
        for dx in (-1.8, -0.4):
            b.cyl((dx, 3.8 + 0.3, zb - 1.1), 0.3, 1.2, col("viande_fonce"), axis="x", name="Saucisse", **ND)
        # plateforme et grosse viande d'enseigne sur la toile
        b.box((-1.8, y_toile(zb - 3.2) - 0.3, zb - 3.2), (1.8, 9.6, zb - 0.3), bp, studs="top", name="Plateforme")
        from assets.mobilier import viande_geante
        with b.at((0, 9.6, zb - 1.75)):
            viande_geante(b, variant=0, taille=0.8)
    else:
        b.box((x0 + 0.5, yt, zf + 0.05), (x1 - 0.5, yt + 0.4, zf + 1.75), col("glace"), studs="top", name="Glace")
        for (x, z, yaw, cc) in ((-2.5, zf + 0.5, 15, "orange"), (-0.8, zf + 1.2, -10, "poisson"),
                                (0.9, zf + 0.55, 5, "rouge"), (2.5, zf + 1.2, -20, "poisson_fonce")):
            _poisson(b, x, yt + 0.4, z, 1.9, cc, yaw=yaw)
        b.box((x0 + 0.6, 7.0, zf + 0.85), (x1 - 0.6, 7.2, zf + 1.0), bp, name="Tringle", **ND)
        for x, cc in ((-1.6, "poisson"), (1.6, "orange")):
            b.box((x - 0.05, 6.3, zf + 0.88), (x + 0.05, 7.0, zf + 0.98), col("corde"), name="Lien", **NDS)
            _poisson(b, x, 6.3, zf + 0.93, 2.2, cc, debout=True)
        b.cyl((2.0, 2.0 + 0.55, zb - 1.5), 0.7, 1.1, col("bois"), name="Seau", **ND)
        b.cyl((2.0, 2.0 + 1.15, zb - 1.5), 0.6, 0.15, col("glace"), name="Glace", **ND)
        for dx, cc in ((-0.25, "poisson_fonce"), (0.25, "orange")):
            b.wedge((2.0 + dx - 0.15, 3.2, zb - 1.8), (2.0 + dx + 0.15, 3.9, zb - 1.2), col(cc), down="-z", name="Queue", **ND)
    return {"emprise": (W, D), "hauteur": 13.0 if v == 1 else 10.6}


# ---------------------------------------------------------------------------
# GRANGE
# ---------------------------------------------------------------------------


def _vantail_x(b, xa, xb, y0, y1, rouge, blanc):
    """Vantail de grange à cadre blanc et croix de Saint-André (repère de façade)."""
    b.box((xa, y0, -0.22), (xb, y1, 0.1), blanc, name="Cadre")
    b.box((xa + 0.35, y0 + 0.35, -0.32), (xb - 0.35, y1 - 0.35, 0.0), rouge, name="Vantail")
    _barre(b, (xa + 0.45, y0 + 0.45), (xb - 0.45, y1 - 0.45), 0.4, -0.42, -0.25, blanc, name="Croix", **ND)
    _barre(b, (xb - 0.45, y0 + 0.45), (xa + 0.45, y1 - 0.45), 0.4, -0.41, -0.25, blanc, name="Croix", **ND)


def _girouette(b, x, y, z):
    """Girouette au coq (profil dans le plan x-y) sur une tige, avec flèche."""
    m = col("laiton")
    b.cyl((x, y + 1.3, z), 0.1, 2.6, col(FER), name="Tige", **ND)
    b.box((x - 1.2, y + 1.7, z - 0.06), (x + 1.2, y + 1.85, z + 0.06), col(FER), name="Fleche", **ND)
    b.wedge((x + 1.0, y + 1.5, z - 0.07), (x + 1.5, y + 2.05, z + 0.07), col(FER), down="+x", name="Pointe", **NDS)
    yb = y + 2.6
    b.box((x - 0.6, yb, z - 0.1), (x + 0.5, yb + 0.7, z + 0.1), m, name="Coq", **ND)
    b.box((x - 1.05, yb + 0.35, z - 0.08), (x - 0.55, yb + 1.4, z + 0.08), m, name="Queue", **ND)
    b.box((x + 0.3, yb + 0.6, z - 0.09), (x + 0.75, yb + 1.15, z + 0.09), m, name="Tete", **ND)
    b.box((x + 0.35, yb + 1.15, z - 0.05), (x + 0.65, yb + 1.4, z + 0.05), col("rouge"), name="Crete", **NDS)
    return yb + 1.4


def grange(b, variant=0, largeur=22, profondeur=16):
    """Grange rouge de la campagne aux moulins : murs de planches rouges (couvre-joints), chaînes d'angle et
    encadrements blancs, grandes portes à croix de Saint-André vers -Z, porte de fenil garnie de foin et
    potence de levage, girouette au coq. 0 : toit à la Mansart (brisé) et silo rond à dôme sur le côté ;
    1 : plus petite, toit raide à deux pans, appentis à bûches et roue de charrette."""
    rng = b.rng
    v = variant % 2
    W, D = float(largeur), float(profondeur)
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    rouge, blanc = col("mur_rouge"), col("blanc")
    toit = col("toit_brun") if v == 0 else col("toit_rouge_fonce")
    # corps (v1 : appentis de 4,5 inclus dans l'emprise côté +x)
    xb_ = x1 if v == 0 else x1 - 4.5
    Hw = 9.0 if v == 0 else 8.0
    with b.group("Volume"):
        xc0 = (x0 + xb_) / 2
        dw0 = 8.0 if v == 0 else 6.4
        b.box((x0 - 0.2, 0, zf + 0.3), (xb_ + 0.2, 0.8, zb + 0.2), vr("pierre_fonce", rng, 0.03), name="Soubassement")
        for xa, xz in ((x0 - 0.2, xc0 - dw0 / 2 - 0.5), (xc0 + dw0 / 2 + 0.5, xb_ + 0.2)):
            b.box((xa, 0, zf - 0.2), (xz, 0.8, zf + 0.3), vr("pierre_fonce", rng, 0.03), name="Soubassement")
        b.box((x0, 0.8, zf), (xb_, Hw, zb), vr(rouge, rng, 0.03), name="Mur")
        for xa, xz in ((x0 - 0.35, x0 + 0.65), (xb_ - 0.65, xb_ + 0.35)):
            for za, zz in ((zf - 0.35, zf + 0.65), (zb - 0.65, zb + 0.35)):
                b.box((xa, 0.8, za), (xz, Hw, zz), blanc, name="Chaine")
        b.box((x0 - 0.25, Hw - 0.5, zf - 0.25), (xb_ + 0.25, Hw, zb + 0.25), blanc, name="Bandeau")
    # couvre-joints (planches verticales) sur l'avant et les côtés
    with b.group("Planches"):
        sombre = shade(rouge, 0.82)
        xm = (x0 + xb_) / 2
        for x in [x0 + 2.0 + 2.0 * i for i in range(int((xb_ - x0 - 2.5) // 2.0))]:
            if abs(x - xm) < 4.6:
                continue
            b.box((x - 0.15, 0.8, zf - 0.12), (x + 0.15, Hw - 0.5, zf + 0.1), sombre, name="CouvreJoint", **NDS)
        for xs in (x0, xb_):
            s = -1 if xs == x0 else 1
            if v == 1 and s > 0:
                continue
            for z in [zf + 2.0 + 2.0 * i for i in range(int((D - 2.5) // 2.0))]:
                b.box((xs + (-0.12 if s < 0 else -0.1), 0.8, z - 0.15), (xs + (0.1 if s < 0 else 0.12), Hw - 0.5, z + 0.15),
                      sombre, name="CouvreJoint", **NDS)

    # --- toit ---------------------------------------------------------------------------------------
    with b.group("Toit"):
        k = 0.8
        if v == 0:
            xa_ = x0 + (W / 2) * 0.48           # brisis : 48 % de la demi-largeur
            hb, hh = 5.4, 2.6
            yb, yh = Hw + hb, Hw + hb + hh
            for (a0, a1, down) in ((x0, xa_, "-x"), (-xa_, x1, "+x")):
                b.wedge((a0, Hw, zf), (a1, yb, zb), vr(rouge, rng, 0.03), down=down, name="Pignon")
            b.box((xa_, Hw, zf), (-xa_, yb, zb), vr(rouge, rng, 0.03), name="Pignon")
            b.wedge((xa_, yb, zf), (0, yh + 0.2, zb), vr(rouge, rng, 0.03), down="-x", name="Pignon")
            b.wedge((0, yb, zf), (-xa_, yh + 0.2, zb), vr(rouge, rng, 0.03), down="+x", name="Pignon")
            za, zz = zf - 1.0, zb + 1.0
            pb = hb / (xa_ - x0)
            ph = hh / (0 - xa_)
            kb, kh = k * math.hypot(1, pb), k * math.hypot(1, ph)
            _pan_x(b, x0, Hw + kb, xa_, yb + kb, za, zz, k, vary(toit, rng, 0.03), ext_a=0.9 * math.hypot(1, pb), ext_b=0.35)
            _pan_x(b, -xa_, yb + kb, x1, Hw + kb, za, zz, k, vary(toit, rng, 0.03), ext_a=0.35, ext_b=0.9 * math.hypot(1, pb))
            _pan_x(b, xa_, yb + kh, 0, yh + kh, za, zz, k, vary(toit, rng, 0.03), ext_a=0.2, ext_b=0.45)
            _pan_x(b, 0, yh + kh, -xa_, yb + kh, za, zz, k, vary(toit, rng, 0.03), ext_a=0.45, ext_b=0.2)
            yr = yh + kh
            b.box((-0.7, yr - 0.7, za - 0.15), (0.7, yr + 0.45, zz + 0.15), shade(toit, 0.75), studs="top", name="Faitage")
            # planches de rive blanches sur le pignon avant
            for i, (pa, pb_, ea, eb) in enumerate((((x0, Hw), (xa_, yb), 0.9 * math.hypot(1, pb) + 0.1, 0.6),
                                                    ((xa_, yb), (0, yh), 0.3, 0.6), ((0, yh), (-xa_, yb), 0.6, 0.3),
                                                    ((-xa_, yb), (x1, Hw), 0.6, 0.9 * math.hypot(1, pb) + 0.1))):
                kk = kb if pa[1] == Hw or pb_[1] == Hw else kh
                dz = 0.01 * i
                _pan_x(b, pa[0], pa[1] + kk + 0.15, pb_[0], pb_[1] + kk + 0.15, za - 0.25 - dz, za + 0.3 + dz, k + 0.3, blanc,
                       ext_a=ea, ext_b=eb, studs="none", name="Rive", **ND)
            top = yr + 0.45
            xg, y_fenil = 0.0, Hw + 1.0
        else:
            xm = (x0 + xb_) / 2
            hu = (xb_ - x0) / 2 * 1.05
            b.wedge((x0, Hw, zf), (xm, Hw + hu + 0.3, zb), vr(rouge, rng, 0.03), down="-x", name="Pignon")
            b.wedge((xm, Hw, zf), (xb_, Hw + hu + 0.3, zb), vr(rouge, rng, 0.03), down="+x", name="Pignon")
            p = 1.05
            kk = k * math.hypot(1, p)
            za, zz = zf - 1.0, zb + 0.8
            _pan_x(b, x0, Hw + kk, xm, Hw + hu + kk, za, zz, k, vary(toit, rng, 0.03), ext_a=0.8 * math.hypot(1, p), ext_b=0.4)
            _pan_x(b, xm, Hw + hu + kk, xb_, Hw + kk, za, zz, k, vary(toit, rng, 0.03), ext_a=0.4, ext_b=0.5 * math.hypot(1, p))
            for i, (pa, pb_, ea, eb) in enumerate((((x0, Hw), (xm, Hw + hu), 0.8 * math.hypot(1, p) + 0.1, 0.6),
                                                    ((xm, Hw + hu), (xb_, Hw), 0.6, 0.5 * math.hypot(1, p) + 0.1))):
                dz = 0.01 * i
                _pan_x(b, pa[0], pa[1] + kk + 0.15, pb_[0], pb_[1] + kk + 0.15, za - 0.25 - dz, za + 0.3 + dz, k + 0.3, blanc,
                       ext_a=ea, ext_b=eb, studs="none", name="Rive", **ND)
            yr = Hw + hu + kk
            b.box((xm - 0.7, yr - 0.7, za - 0.15), (xm + 0.7, yr + 0.45, zz + 0.15), shade(toit, 0.75), studs="top", name="Faitage")
            top = yr + 0.45
            xg, y_fenil = xm, Hw + 0.6
        top = max(top, _girouette(b, xg, top - 0.2, za + 1.2))

    # --- façade avant : grandes portes, fenil ------------------------------------------------------
    with b.at((0, 0, zf), group="FacadeAvant"):
        xc = (x0 + xb_) / 2
        dw = 8.0 if v == 0 else 6.4
        dh = 7.2 if v == 0 else 6.4
        sombre = shade(rouge, 0.86)
        b.box((xc - dw / 2 - 0.5, 0, -0.18), (xc + dw / 2 + 0.5, dh + 0.6, 0.1), blanc, name="Encadrement")
        b.box((xc - dw / 2, 0, -0.2), (xc + dw / 2, dh, 0.08), col(INTERIEUR), name="Fond")
        _vantail_x(b, xc - dw / 2, xc - 0.05, 0.0, dh, sombre, blanc)
        _vantail_x(b, xc + 0.05, xc + dw / 2, 0.0, dh, sombre, blanc)
        b.box((xc - dw / 2 - 0.8, dh + 0.6, -0.45), (xc + dw / 2 + 0.8, dh + 1.1, 0.1), blanc, studs="top", name="Larmier")
        # fenil : ouverture, foin, vantail ouvert, potence et poulie
        fw, fh = 3.6, 3.6
        yf = y_fenil + 1.0
        b.box((xc - fw / 2 - 0.4, yf - 0.4, -0.16), (xc + fw / 2 + 0.4, yf + fh + 0.4, 0.1), blanc, name="Encadrement")
        b.box((xc - fw / 2, yf, -0.24), (xc + fw / 2, yf + fh, 0.08), col(INTERIEUR), name="Fenil")
        b.box((xc - fw / 2 + 0.1, yf + 0.05, -0.7), (xc + fw / 2 - 0.1, yf + 1.5, 0.0), col("foin"), studs="top", name="Foin")
        b.box((xc - fw / 2 + 0.4, yf + 1.5, -0.5), (xc + 0.4, yf + 2.3, 0.0), col("foin_fonce"), studs="top", name="Foin")
        xo0, xo1 = xc + fw / 2 + 0.5, xc + fw / 2 + 0.5 + fw / 2
        b.box((xo0, yf, -0.24), (xo1, yf + fh, 0.1), blanc, name="VantailOuvert")
        b.box((xo0 + 0.3, yf + 0.3, -0.32), (xo1 - 0.3, yf + fh - 0.3, 0.0), sombre, name="VantailOuvert", **ND)
        _barre(b, (xo0 + 0.4, yf + 0.4), (xo1 - 0.4, yf + fh - 0.4), 0.32, -0.4, -0.28, blanc, name="Croix", **ND)
        yp = yf + fh + 0.6
        b.box((xc - 0.3, yp, -1.8), (xc + 0.3, yp + 0.6, 0.4), col("bois_fonce"), name="Potence")
        b.cyl((xc, yp - 0.3, -1.45), 0.35, 0.3, col(FER), axis="x", name="Poulie", **ND)
        b.box((xc - 0.05, yf + 1.6, -1.5), (xc + 0.05, yp - 0.6, -1.4), col("corde"), name="Corde", **NDS)
        # fenêtres de part et d'autre des portes
        for sx in (-1, 1):
            xw = xc + sx * (dw / 2 + (2.6 if v == 0 else 1.8))
            if v == 1 and sx > 0:
                continue
            b.box((xw - 1.2, 4.0, -0.16), (xw + 1.2, 6.4, 0.1), blanc, name="Cadre")
            b.box((xw - 0.85, 4.35, -0.24), (xw + 0.85, 6.05, 0.08), col("fenetre"), name="Vitre")
            b.box((xw - 0.12, 4.35, -0.34), (xw + 0.12, 6.05, -0.24), blanc, name="Meneau", **ND)

    # --- côtés et arrière ---------------------------------------------------------------------------
    for (pos, yaw, nom) in (((x0, 0, 0), 90, "CoteGauche"), ((xb_, 0, 0), -90, "CoteDroit"), ((0, 0, zb), 180, "Arriere")):
        with b.at(pos, yaw=yaw, group=nom):
            if nom == "Arriere":
                xc_ = -(x0 + xb_) / 2
                b.box((xc_ - 1.9, 0, -0.16), (xc_ + 1.9, 5.6, 0.1), blanc, name="Encadrement")
                b.box((xc_ - 1.5, 0, -0.3), (xc_ + 1.5, 5.2, 0.0), shade(rouge, 0.86), name="Porte")
                continue
            if nom == "CoteDroit" and v == 1:
                continue
            for x in (-D / 4, D / 4):
                b.box((x - 1.0, 4.4, -0.16), (x + 1.0, 6.4, 0.1), blanc, name="Cadre")
                b.box((x - 0.7, 4.7, -0.24), (x + 0.7, 6.1, 0.08), col("fenetre"), name="Vitre")

    # --- silo (v0) ou appentis et roue (v1) ---------------------------------------------------------
    if v == 0:
        with b.group("Silo"):
            r, xs, zs = 2.5, x1 + 0.2, zb - 4.2
            hs = Hw + 10.0
            b.cyl((xs, 0.4, zs), r + 0.3, 0.8, vr("pierre_fonce", rng, 0.03), name="Socle")
            b.cyl((xs, hs / 2, zs), r, hs, vr("pierre_claire", rng, 0.02), name="Silo")
            for y in (Hw - 0.25, hs - 2.0):
                b.cyl((xs, y, zs), r + 0.12, 0.7, rouge, name="Cercle", **ND)
            b.ball((xs, hs, zs), r + 0.15, col("toit_rouge"), name="Dome")
            b.cyl((xs, hs + 0.2, zs), r + 0.3, 0.4, rouge, name="Rebord", **ND)
            b.ball((xs, hs + r + 0.35, zs), 0.45, col("laiton"), name="Epi", **ND)
            top = max(top, hs + r + 0.8)
    else:
        with b.group("Appentis"):
            xa, xz = xb_, x1
            ya, yz = Hw - 0.6, Hw - 2.8
            for z in (zf + 0.4, 0.0, zb - 0.4):
                b.box((xz - 0.7, 0, z - 0.3), (xz - 0.1, yz - 0.1, z + 0.3), col("bois_fonce"), name="Poteau")
            pa = (ya - yz) / (xz - xa)
            _pan_x(b, xa, ya + 0.7, xz, yz + 0.7, zf - 0.6, zb + 0.6, 0.6, vary(toit, rng, 0.03), ext_a=0.0, ext_b=0.45,
                   name="Appentis")
            b.box((xa - 0.2, ya + 0.2, zf - 0.6), (xa + 0.45, ya + 1.0, zb + 0.6), col("bois_fonce"), name="Lambourde")
            # bûches empilées et tonneau
            for i, (y, n) in enumerate(((0, 4), (1.0, 3), (2.0, 2))):
                b.box((xa + 0.3, y, zb - 0.6 - n * 1.4), (xz - 1.0, y + 1.0, zb - 0.6), vr("tronc", rng, 0.08), studs="top",
                      name="Buches")
                b.box((xz - 1.0 + 0.0, y + 0.15, zb - 0.6 - n * 1.4 + 0.15), (xz - 0.85, y + 0.85, zb - 0.75),
                      col("tronc_clair"), name="Coupe", **NDS)
            b.cyl((xa + 2.0, 1.3, zf + 2.0), 1.0, 2.6, col("bois"), name="Tonneau", **ND)
            b.cyl((xa + 2.0, 1.3, zf + 2.0), 1.08, 0.25, col(FER), name="Cercle", **ND)
        with b.at((x0 + 2.4, 0, zf), group="Roue"):
            R = 1.8
            yc = R + 0.05
            b.cyl((0, yc, -0.35), R, 0.35, col("bois_fonce"), axis="z", name="Jante", **ND)
            b.cyl((0, yc, -0.37), R - 0.35, 0.37, shade(rouge, 0.95), axis="z", name="Jour", **ND)
            for a in (0, 60, 120):
                b.part("block", (2 * R - 0.4, 0.22, 0.22), (0, yc, -0.45), rot_z(a), col("bois_fonce"), name="Rayon", **NDS)
            b.cyl((0, yc, -0.5), 0.4, 0.4, col(FER), axis="z", name="Moyeu", **ND)
    return {"emprise": (W, D), "hauteur": round(top, 2)}
