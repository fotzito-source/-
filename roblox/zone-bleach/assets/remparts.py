"""Enceintes et portes de la cité blanche (zone 6), style « stud ».

Fortifications blanches d'un château japonais générique : enduit blanc (shikkui) en panneaux de blancs
voisins, base de pierre talutée (ishigaki) en gradins, soubassements de planches sombres (koshi-ita), auvents et
chaperons de tuiles ocre-orangé (murs dobei), meurtrières carrées (sama), bretèches (ishi-otoshi), tours de guet
(yagura) à étage en encorbellement, tours-portes (yagura-mon) à corps de garde, balcons laqués rouges, plaques
(gaku) bleu profond cadrées d'or, passerelle portée par des encorbellements de poutres (hanegi).

Fonctions publiques (chacune `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h, ...}) :

    grande_porte       porte colossale d'entrée (mur de 64, bastions, corps de garde, vantaux ouverts)  ≤ 850
    porte_interieure   tour-porte entre le faubourg et la cité (passage ouverture × 35, mur de 24)    ≤ 420
    passerelle_rouge   passerelle couverte laquée rouge à 38 studs au-dessus du couloir               ≤ 330
    mur_blanc          mur blanc droit à chaperon ocre (allées, enclos, remparts)    ≤ ceil(6 + longueur / 5)
    tour_blanche       tour de guet blanche carrée (remparts et cours)                                ≤ 65
    portail_cour       portail d'enclos posé dans un mur d'allée                                     ≤ 60

Couloir élargi (|x| < 45, trottoirs jusqu'à |x| = 55) : les trois monuments qui enjambent le couloir sont
paramétriques. Valeurs conseillées : grande_porte(ouverture=100, z_max_vantaux=60) (passage 100 × 55 sous les
solives, vantaux enduits de blanc ouverts à ≈ 102°, alignés le long de l'esplanade jusqu'à z ≈ 59 ; 92 et 96
conviennent aussi), porte_interieure(ouverture=92) (passage 92 × 35 sous les solives, vantaux de bois ouverts
côté faubourg, murs d'allée de la cité attendus en |x| = xo + 9 = 55, paramètre x_allee),
passerelle_rouge(portee=130) (tours en |x| 58..72 derrière les murs d'allée, tablier à 36,6 en dessous) ;
portail_cour(largeur=12, hauteur=18, h_mur=14) dans les murs d'allée de 14. Avec ces valeurs, rien de solide
dans |x| < 45 au sol et rien du tout dans |x| < 46 sous y = 30. Les anciennes valeurs (76, 72, 104) marchent
encore.

Repère (CONVENTIONS.md) : Y en haut, 1 unité = 1 stud, origine au centre de l'emprise au sol, avant = -Z
local. Exceptions : grande_porte, porte_interieure et passerelle_rouge sont posées sans rotation ; leur face
d'arrivée regarde +Z. Uniquement des éléments japonais génériques : aucun nom, aucun emblème, aucun chiffre.
Textes : 門 静 白 茶 宿 seulement.
"""

from __future__ import annotations

import math

import numpy as np

from kit import hexrgb, mix, rot_y, shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Couleurs
# ---------------------------------------------------------------------------
BLANCS = ("blanc", "blanc_creme", "blanc_pur", "blanc", "blanc_ombre")
PIERRES = ("pierre", "pierre_fonce", "pierre", "pierre_claire", "pierre_fonce")
BOIS_PORTE = ("bois_fonce", "bois", "#3B2A1D", "#55392A")     # planches des vantaux (alternées)
OR_VIEUX = "#C99A3A"                                     # cadres et clous un peu plus sombres que « or »


def col(x):
    """Nom de palette, '#hex' ou tuple → tuple RGB."""
    if isinstance(x, tuple):
        return x
    if isinstance(x, str) and x.startswith("#"):
        return hexrgb(x)
    return c(x)


def vr(x, rng, a=0.04):
    """`vary` qui accepte aussi '#hex' et les tuples."""
    return vary(col(x), rng, a)


def _suite(rng, n, noms, a=0.0):
    """n couleurs tirées dans `noms`, jamais deux voisines identiques."""
    out, prev = [], None
    for _ in range(n):
        k = noms[int(rng.integers(0, len(noms)))]
        while k == prev:
            k = noms[int(rng.integers(0, len(noms)))]
        prev = k
        out.append(vr(k, rng, a) if a else c(k))
    return out


def _blancs(rng, n):
    return _suite(rng, n, BLANCS)


def _pierres(rng, n):
    return _suite(rng, n, PIERRES, 0.03)


# ---------------------------------------------------------------------------
# Éléments de construction (murs le long de X)
# ---------------------------------------------------------------------------

def _enduit(b, x0, x1, y0, y1, z0, z1, rng, n, name="Enduit", couleurs=None):
    """Mur d'enduit blanc découpé en n panneaux de blancs voisins (pleine épaisseur : deux faces d'un coup)."""
    cols = couleurs or _blancs(rng, n)
    w = (x1 - x0) / n
    for i in range(n):
        b.box((x0 + i * w, y0, z0), (x0 + (i + 1) * w, y1, z1), cols[i], name=name)


def _enduit_z(b, z0, z1, y0, y1, x0, x1, rng, n, name="Enduit"):
    """Comme `_enduit`, panneaux découpés le long de Z (faces visibles en x0 et x1)."""
    cols = _blancs(rng, n)
    w = (z1 - z0) / n
    for i in range(n):
        b.box((x0, y0, z0 + i * w), (x1, y1, z0 + (i + 1) * w), cols[i], name=name)


def _plinthe(b, x0, x1, z0, z1, marches, rng, nseg=3, name="Ishigaki", x_retrait=(0.0, 0.0)):
    """Base de pierre talutée (ishigaki) le long de X : `marches` = [(y0, y1, débord)], le débord s'ajoute de
    chaque côté de [z0, z1]. Chaque gradin est coupé en `nseg` blocs de pierres voisines, joints décalés d'un
    gradin à l'autre ; studs sur les dessus. `x_retrait` = (gauche, droite) : retrait des bouts par gradin."""
    L = x1 - x0
    for k, (y0, y1, d) in enumerate(marches):
        xa, xb = x0 + x_retrait[0] * k, x1 - x_retrait[1] * k
        Lk = xb - xa
        decal = 0.5 if k % 2 else 0.0
        cuts = [xa] + [xa + Lk * (i + decal) / nseg for i in range(1, nseg + (1 if decal else 0))] + [xb]
        cuts = sorted(set(round(v, 4) for v in cuts if xa - 1e-6 <= v <= xb + 1e-6))
        cols = _pierres(rng, len(cuts) - 1)
        for (a, bb), cc in zip(zip(cuts, cuts[1:]), cols):
            if bb - a > 0.05:
                b.box((a, y0, z0 - d), (bb, y1, z1 + d), cc, studs="top", name=name)
    return L


def _chaperon(b, x0, x1, zc, demi, y, deb, h, rng, *, toit="ocre", sous="ocre_fonce", faite="ocre_fonce",
              ep_sous=0.3, fw=0.5, rive=None, retrait_faite=0.1, name="Chaperon"):
    """Chaperon de tuiles à deux pentes le long de X sur un mur de demi-épaisseur `demi` (centré en zc), posé
    à y : sous-face sombre qui déborde de `deb`, deux coins stud, faîtage stud ; `rive` = couleur de tuiles de
    rive (plus claires) le long des égouts. Le faîtage est raccourci de `retrait_faite` à chaque bout (pas de
    faces coplanaires avec les bouts des coins). Renvoie le haut du faîtage."""
    za, zb = zc - demi - deb, zc + demi + deb
    b.box((x0, y, za), (x1, y + ep_sous, zb), col(sous), name=f"{name}_sous")
    y1 = y + ep_sous
    t = col(toit)
    b.wedge((x0, y1, za), (x1, y1 + h, zc), vr(t, rng, 0.02), down="-z", studs="top", name=name)
    b.wedge((x0, y1, zc), (x1, y1 + h, zb), vr(t, rng, 0.02), down="+z", studs="top", name=name)
    pente = h / (demi + deb)
    top = y1 + h + 0.45
    b.box((x0 + retrait_faite, y1 + h - fw * pente - 0.2, zc - fw), (x1 - retrait_faite, top, zc + fw), col(faite),
          studs="top", name=f"{name}_faite")
    if rive:
        for s in (-1, 1):
            ze = zc + s * (demi + deb)
            za_, zb_ = sorted((ze + s * 0.1, ze - s * 0.55))
            rr = max(retrait_faite, 0.1)
            b.box((x0 + rr, y1 - 0.15, za_), (x1 - rr, y1 + 0.32, zb_), col(rive), collide=False, name=f"{name}_rive")
    return top


def _fenetres_x(b, xs, w, y0, y1, za, zb, *, barreaux=2, fond="fenetre", bar="bois_fonce", name="Fenetre"):
    """Fenêtres traversantes d'un mur le long de X (faces en za < zb) : bloc sombre qui dépasse de 0,1 de chaque
    côté (visible sur les deux faces), barreaux verticaux traversants qui dépassent de 0,2."""
    for xc in xs:
        b.box((xc - w / 2, y0, za - 0.1), (xc + w / 2, y1, zb + 0.1), col(fond), name=name)
        for i in range(barreaux):
            x = xc - w / 2 + w * (i + 1) / (barreaux + 1)
            b.box((x - 0.18, y0 + 0.05, za - 0.22), (x + 0.18, y1 - 0.05, zb + 0.22), col(bar), collide=False,
                  name="Barreau")


def _fenetres_z(b, zs, w, y0, y1, xa, xb, *, barreaux=2, fond="fenetre", bar="bois_fonce", name="Fenetre"):
    """Comme `_fenetres_x` pour un mur le long de Z (faces en xa < xb)."""
    for zc in zs:
        b.box((xa - 0.1, y0, zc - w / 2), (xb + 0.1, y1, zc + w / 2), col(fond), name=name)
        for i in range(barreaux):
            z = zc - w / 2 + w * (i + 1) / (barreaux + 1)
            b.box((xa - 0.22, y0 + 0.05, z - 0.18), (xb + 0.22, y1 - 0.05, z + 0.18), col(bar), collide=False,
                  name="Barreau")


def _meurtrieres_x(b, xs, y0, s, za, zb, name="Meurtriere"):
    """Petites meurtrières carrées traversantes (côté s), sombres, 0,1 en saillie sur les deux faces."""
    for x in xs:
        b.box((x - s / 2, y0, za - 0.1), (x + s / 2, y0 + s, zb + 0.1), col("fenetre"), collide=False, name=name)


def _haut(b, n0):
    """Point le plus haut (y) des pièces ajoutées depuis l'indice n0, dans le repère courant."""
    top = 0.0
    for p in b.parts[n0:]:
        R = np.asarray(p.rot).reshape(3, 3)
        top = max(top, p.pos[1] + float((np.abs(R) @ (np.asarray(p.size) / 2))[1]))
    return float(round(top - float(b.to_world((0, 0, 0))[1]), 1))


def _repartis(x0, x1, pas, marge=None):
    """Positions régulières dans [x0, x1], à peu près tous les `pas`, centrées."""
    L = x1 - x0
    n = max(1, int(round(L / pas)))
    m = L / n
    return [x0 + m * (i + 0.5) for i in range(n)]


def _balcon(b, x0, x1, y, zf, prof, sens, *, rouge="laque_rouge", plancher="laque_rouge_fonce", pas=7.0, h=3.3,
            consoles=True, lisse_haute="laque_noire", bouts="or", h_console=2.0, name="Balcon"):
    """Balcon à garde-corps le long de X devant une façade en z = zf, vers +Z (sens = 1) ou -Z (sens = -1) :
    plancher (dessus en y), poteaux laqués, lisse basse, main courante sombre, pommeaux dorés aux bouts,
    consoles sous le plancher. Renvoie le nombre de pièces."""
    n0 = len(b.parts)
    za, zb = sorted((zf, zf + sens * prof))
    b.box((x0, y - 0.7, za), (x1, y, zb), col(plancher), studs="top", name=f"{name}_plancher")
    zr = zf + sens * (prof - 0.4)
    n = max(1, int(round((x1 - x0) / pas)))
    xs = [x0 + 0.35 + (x1 - x0 - 0.7) * i / n for i in range(n + 1)]
    for i, x in enumerate(xs):
        b.box((x - 0.35, y, zr - 0.35), (x + 0.35, y + h + 0.3, zr + 0.35), col(rouge), collide=False,
              name=f"{name}_poteau")
        if consoles:
            ca, cb = sorted((zf, zf + sens * (prof - 0.6)))
            b.wedge_under((x - 0.35, y - 0.7 - h_console, ca), (x + 0.35, y - 0.7, cb), col(rouge),
                          down="+z" if sens > 0 else "-z", collide=False, name=f"{name}_console")
    b.box((x0 + 0.05, y + h - 0.55, zr - 0.45), (x1 - 0.05, y + h - 0.05, zr + 0.45), col(lisse_haute), collide=False,
          name=f"{name}_main_courante")
    b.box((x0 + 0.1, y + 1.0, zr - 0.22), (x1 - 0.1, y + 1.45, zr + 0.22), col(rouge), collide=False,
          name=f"{name}_lisse")
    if bouts:
        for x in (xs[0], xs[-1]):
            b.box((x - 0.45, y + h + 0.3, zr - 0.45), (x + 0.45, y + h + 0.9, zr + 0.45), col(bouts), collide=False,
                  name=f"{name}_pommeau")
    return len(b.parts) - n0


def _plaque(b, xc, y0, w, h, z_mur, sens, texte, *, fond="bleu_profond", cadre="or", encre="or", ep=0.3):
    """Plaque (gaku) contre une façade en z = z_mur, côté sens (+1 : +Z, -1 : -Z) : cadre doré, planche bleu
    profond en saillie de 0,15, caractère doré au pinceau."""
    za, zb = sorted((z_mur, z_mur + sens * ep))
    b.box((xc - w / 2 - 0.35, y0 - 0.35, za), (xc + w / 2 + 0.35, y0 + h + 0.35, zb), col(cadre), collide=False,
          name="Plaque_cadre")
    za, zb = sorted((z_mur + sens * 0.1, z_mur + sens * (ep + 0.15)))
    p = b.box((xc - w / 2, y0, za), (xc + w / 2, y0 + h, zb), col(fond), collide=False, name="Plaque")
    p.label = {"face": "Back" if sens > 0 else "Front", "text": texte, "color": col(encre), "bg": None,
               "font": "brush", "vertical": True}
    return p


def _lampion(b, x, y_haut, z, corps="lampion_papier", *, r=0.8, h=1.7, cordon=0.5, culot=True):
    """Lanterne de papier suspendue (chōchin) : cordon, capuchon, corps lumineux, culot. Renvoie le bas."""
    b.box((x - 0.07, y_haut - cordon, z - 0.07), (x + 0.07, y_haut + 0.05, z + 0.07), col("noir"), collide=False,
          shadow=False, name="Cordon")
    yt = y_haut - cordon
    b.cyl((x, yt - 0.15, z), r * 0.62, 0.3, col("noir"), collide=False, name="Capuchon")
    b.cyl((x, yt - 0.3 - h / 2, z), r, h, col(corps), material="Neon", collide=False, shadow=False, name="Lampion")
    if culot:
        b.cyl((x, yt - 0.45 - h, z), r * 0.62, 0.3, col("noir"), collide=False, name="Culot")
    return yt - 0.6 - h


# ---------------------------------------------------------------------------
# Toits
# ---------------------------------------------------------------------------

def _jupe(b, x0, x1, z0, z1, y, h1, a, toit, rng, *, sous="ocre_fonce", rive="ocre_clair", coeur=True, name="Toit"):
    """Jupe de toit à quatre pans (avant-toit d'un étage) : sous-face sombre, quatre coins stud, cœur ;
    `a` = (profondeur côté z0, côté z1, côté x0, côté x1) ; `rive` = tuiles de rive claires (None : aucune).
    Renvoie (xi0, xi1, zi0, zi1, y + h1)."""
    t = col(toit)
    az0, az1, ax0, ax1 = a
    xi0, xi1, zi0, zi1 = x0 + ax0, x1 - ax1, z0 + az0, z1 - az1
    if sous:
        b.box((x0, y - 0.45, z0), (x1, y, z1), col(sous), name=f"{name}_sous")
    b.wedge((x0, y, z0), (x1, y + h1, zi0), vr(t, rng, 0.02), down="-z", studs="top", name=name)
    b.wedge((x0, y, zi1), (x1, y + h1, z1), vr(t, rng, 0.02), down="+z", studs="top", name=name)
    b.wedge((x0, y, zi0), (xi0, y + h1, zi1), vr(t, rng, 0.02), down="-x", studs="top", name=name)
    b.wedge((xi1, y, zi0), (x1, y + h1, zi1), vr(t, rng, 0.02), down="+x", studs="top", name=name)
    if coeur:
        b.box((xi0, y, zi0), (xi1, y + h1, zi1), shade(t, 0.8), name=f"{name}_coeur")
    if rive:
        rc = col(rive)
        b.box((x0 - 0.1, y - 0.2, z0 - 0.1), (x1 + 0.1, y + 0.3, z0 + 0.5), rc, collide=False, name=f"{name}_rive")
        b.box((x0 - 0.1, y - 0.2, z1 - 0.5), (x1 + 0.1, y + 0.3, z1 + 0.1), rc, collide=False, name=f"{name}_rive")
        b.box((x0 - 0.1, y - 0.2, z0 + 0.5), (x0 + 0.5, y + 0.3, z1 - 0.5), rc, collide=False, name=f"{name}_rive")
        b.box((x1 - 0.5, y - 0.2, z0 + 0.5), (x1 + 0.1, y + 0.3, z1 - 0.5), rc, collide=False, name=f"{name}_rive")
    return xi0, xi1, zi0, zi1, y + h1


def _irimoya(b, x0, x1, z0, z1, y, h1, h2, a, toit, rng, *, tri="blanc", deb_g=0.8, sous="ocre_fonce",
             rive="ocre_clair", faite="ocre_fonce", ornement="or", gegyo="or", h_orn=2.2, name="Toit"):
    """Toit irimoya (croupe + pignon), faîtage le long de X, posé à y sur l'emprise de l'avant-toit
    (x0..x1, z0..z1) : jupe à quatre pans (h1), puis deux pans plus raides (h2) jusqu'au faîtage, triangles de
    pignon blancs en retrait aux bouts, pendentifs dorés (gegyo), ornements de faîtage (blocs dorés, ou sombres).
    Renvoie un dict de cotes (top, yr, zm, xg0, xg1)."""
    t = col(toit)
    xi0, xi1, zi0, zi1, ya = _jupe(b, x0, x1, z0, z1, y, h1, a, toit, rng, sous=sous, rive=rive, name=name)
    zm = (zi0 + zi1) / 2
    xg0, xg1 = xi0 - deb_g, xi1 + deb_g
    b.wedge((xg0, ya, zi0), (xg1, ya + h2, zm), vr(t, rng, 0.02), down="-z", studs="top", name=name)
    b.wedge((xg0, ya, zm), (xg1, ya + h2, zi1), vr(t, rng, 0.02), down="+z", studs="top", name=name)
    run = zm - zi0
    pente = h2 / run
    bord = 0.45
    zs = zi0 + (0.35 + bord) / pente
    for xe, s in ((xg0, -1), (xg1, 1)):
        xa_, xb_ = sorted((xe, xe + 0.15 * s))
        b.wedge((xa_, ya + 0.35, zs), (xb_, ya + h2 - bord, zm), col(tri), down="-z", collide=False, name=f"{name}_pignon")
        b.wedge((xa_, ya + 0.35, zm), (xb_, ya + h2 - bord, 2 * zm - zs), col(tri), down="+z", collide=False,
                name=f"{name}_pignon")
        if gegyo:
            ga, gb = sorted((xe + 0.15 * s, xe + 0.45 * s))
            b.box((ga, ya + h2 - 2.2, zm - 0.5), (gb, ya + h2 - 0.6, zm + 0.5), col(gegyo), collide=False,
                  name=f"{name}_gegyo")
    yr = ya + h2
    b.box((xg0 - 0.3, yr - (0.9 * pente + 0.35), zm - 0.9), (xg1 + 0.3, yr + 0.8, zm + 0.9), col(faite), studs="top",
          name=f"{name}_faite")
    top = yr + 0.8
    if ornement:
        for xe, s in ((xg0 - 0.3, 1), (xg1 + 0.3, -1)):
            xa_, xb_ = sorted((xe - s * 0.15, xe + s * 1.3))
            b.box((xa_, yr - 0.4, zm - 0.65), (xb_, yr + 0.8 + h_orn, zm + 0.65), col(ornement), collide=False,
                  name=f"{name}_ornement")
        top = yr + 0.8 + h_orn
    return {"top": top, "yr": yr, "zm": zm, "xg0": xg0, "xg1": xg1, "ya": ya}


def _croupe(b, x0, x1, z0, z1, y, h, toit, rng, *, niveaux=3, sous=None, rive=None, faite=None, epi=None,
            name="Toit"):
    """Toit en croupe (yosemune) en stud : sans CornerWedge, on empile `niveaux` jupes à quatre pans de même
    pente qui rétrécissent jusqu'au sommet (silhouette de pyramide aux arêtes en gradins), faîtage court et
    épi. Renvoie le haut."""
    t = col(toit)
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    hx, hz = (x1 - x0) / 2, (z1 - z0) / 2
    hj = h / niveaux
    f_fin = 0.12
    ya = y
    for k in range(niveaux):
        f0 = 1 - (1 - f_fin) * k / niveaux
        f1 = 1 - (1 - f_fin) * (k + 1) / niveaux
        ax, az = hx * (f0 - f1), hz * (f0 - f1)
        _jupe(b, cx - hx * f0, cx + hx * f0, cz - hz * f0, cz + hz * f0, ya, hj, (az, az, ax, ax), toit, rng,
              sous=(sous or shade(t, 0.7)) if k == 0 else None, rive=rive if k == 0 else None,
              coeur=(k == niveaux - 1), name=name)
        ya += hj
    rx, rz = hx * f_fin, hz * f_fin
    fa = col(faite) if faite else shade(t, 0.72)
    b.box((cx - rx - 0.3, ya - 0.3, cz - rz - 0.3), (cx + rx + 0.3, ya + 0.5, cz + rz + 0.3), fa, studs="top",
          name=f"{name}_faite")
    top = ya + 0.5
    if epi:
        b.box((cx - 0.35, top, cz - 0.35), (cx + 0.35, top + 1.6, cz + 0.35), col(epi), collide=False,
              name=f"{name}_epi")
        top += 1.6
    return top


def _chidori(b, xc, demi, y0, h, z_fond, z_face, toit, rng, *, tri="blanc", gegyo="or", name="Chidori"):
    """Pignon de lucarne (chidori-hafu) posé sur un pan de toit : faîtage le long de Z, de z_fond (contre le
    mur ou le pan supérieur) à z_face (pignon), deux coins stud, triangle blanc en retrait, pendentif doré."""
    t = col(toit)
    za, zb = sorted((z_fond, z_face))
    s = 1 if z_face > z_fond else -1
    b.wedge((xc - demi, y0, za), (xc, y0 + h, zb), vr(t, rng, 0.02), down="-x", studs="top", name=name)
    b.wedge((xc, y0, za), (xc + demi, y0 + h, zb), vr(t, rng, 0.02), down="+x", studs="top", name=name)
    fa, fb = (za, zb + 0.3) if s > 0 else (za - 0.3, zb)
    b.box((xc - 0.6, y0 + h - 0.45, fa), (xc + 0.6, y0 + h + 0.5, fb), shade(t, 0.72), studs="top", name=f"{name}_faite")
    ta, tb = sorted((z_face, z_face + 0.15 * s))
    b.wedge((xc - demi + 0.8, y0 + 0.35, ta), (xc, y0 + h - 0.55, tb), col(tri), down="-x", collide=False,
            name=f"{name}_pignon")
    b.wedge((xc, y0 + 0.35, ta), (xc + demi - 0.8, y0 + h - 0.55, tb), col(tri), down="+x", collide=False,
            name=f"{name}_pignon")
    if gegyo:
        ga, gb = sorted((z_face + 0.15 * s, z_face + 0.45 * s))
        b.box((xc - 0.55, y0 + h - 2.6, ga), (xc + 0.55, y0 + h - 0.8, gb), col(gegyo), collide=False,
              name=f"{name}_gegyo")


# ---------------------------------------------------------------------------
# 4) Mur blanc
# ---------------------------------------------------------------------------

def mur_blanc(b, variant=0, longueur=32, hauteur=10, epaisseur=2.4, meurtrieres=False):
    """Mur blanc droit le long de X local, centré sur l'origine, qui occupe exactement x ∈ [-L/2, L/2]
    (chaperon compris) : base de pierre, panneaux d'enduit de blancs voisins, bandeau sous le chaperon,
    chaperon de tuiles ocre à deux pentes (studs) et faîtage ocre foncé. Les deux faces sont soignées.
    variant 0 : uni ; 1 : soubassement de planches sombres (koshi-ita, tiers bas) ; 2 : pilastres blancs.
    meurtrieres=True (remparts) : plinthe en deux gradins, chaperon plus fort, rangée de meurtrières
    carrées traversantes, second bandeau si le budget le permet. Budget : ceil(6 + L / 5) pièces."""
    rng = b.rng
    v = variant % 3
    L, H, e = float(longueur), float(hauteur), float(epaisseur) / 2
    budget = int(math.ceil(6 + L / 5))
    x0, x1 = -L / 2, L / 2
    deb = 1.0 if meurtrieres else 0.7
    hc = round((e + deb) * 0.8, 2)
    # répartition du budget : l'essentiel d'abord (plinthe, bandeau, chaperon, deux panneaux), puis la variante,
    # les meurtrières, les tuiles de rive claires, et enfin les panneaux supplémentaires ou les pilastres
    reste = budget - ((2 if meurtrieres else 1) + 1 + 4 + 2)
    n_pan = 2
    n_koshi = 1 if v == 1 else 0
    reste -= n_koshi
    n_meur = min(max(2, int(round(L / 8))), reste) if meurtrieres else 0
    reste -= n_meur
    rive = reste >= 2
    reste -= 2 if rive else 0
    lisse = v == 1 and reste >= 1
    reste -= 1 if lisse else 0
    second = meurtrieres and reste >= 1
    reste -= 1 if second else 0
    n_pil = 0
    if v != 2:
        extra = max(0, min(reste, int(round(L / 9)) - n_pan))
        n_pan += extra
    else:
        while n_pan + 1 < L / 9.5 and reste >= 2:
            n_pan += 1
            reste -= 1
        n_pil = min(reste, n_pan + 1)
    with b.group("MurBlanc"):
        n0 = len(b.parts)
        # base de pierre
        if meurtrieres:
            hp = 3.2
            b.box((x0, 0, -e - 0.6), (x1, 1.6, e + 0.6), vr("pierre_fonce", rng, 0.03), studs="top", name="Plinthe")
            b.box((x0, 1.6, -e - 0.3), (x1, hp, e + 0.3), vr("pierre", rng, 0.03), studs="top", name="Plinthe")
        else:
            hp = 1.5 if H <= 10 else (1.8 if H < 15 else 2.1)   # plinthes de murs voisins à des niveaux différents
            b.box((x0, 0, -e - 0.3), (x1, hp, e + 0.3), vr("pierre", rng, 0.03), studs="top", name="Plinthe")
        # bandeau et chaperon
        bande = c("bois_fonce") if v == 1 else c("blanc_ombre")
        b.box((x0, H - 0.5, -e - 0.1), (x1, H, e + 0.1), bande, name="Bandeau")
        _chaperon(b, x0, x1, 0.0, e, H, deb, hc, rng, ep_sous=0.3, fw=0.5 if meurtrieres else 0.4,
                  rive="ocre_clair" if rive else None)
        _enduit(b, x0, x1, hp, H - 0.5, -e, e, rng, n_pan)
        w = L / n_pan
        if n_koshi:
            hk = hp + (H - hp) / 3
            b.box((x0 + 0.1, hp, -e - 0.15), (x1 - 0.1, hk, e + 0.15), vr("bois_fonce", rng, 0.03), name="Koshi_ita")
            if lisse:
                b.box((x0 + 0.1, hk, -e - 0.27), (x1 - 0.1, hk + 0.35, e + 0.27), c("bois"), collide=False,
                      name="Koshi_lisse")
        if n_pil:
            joints = [x0 + w * i for i in range(1, n_pan)]
            pos = joints + [x0 + 0.5, x1 - 0.5] if n_pil >= len(joints) + 2 else joints[:n_pil]
            for x in pos:
                xa, xb = max(x0 + 0.1, x - 0.4), min(x1 - 0.1, x + 0.4)
                b.box((xa, hp, -e - 0.2), (xb, H - 0.5, e + 0.2), c("blanc_pur"), name="Pilastre")
        if n_meur:
            _meurtrieres_x(b, _repartis(x0, x1, L / n_meur), H - 4.6, 1.3, -e, e)
        if second:
            ys = hp + (H - hp) * 0.45
            b.box((x0 + 0.1, ys, -e - 0.12), (x1 - 0.1, ys + 0.6, e + 0.12), c("blanc_ombre"), name="Bandeau")
        n = len(b.parts) - n0
        assert n <= budget, (n, budget, L, v, meurtrieres)
    return {"emprise": (L, 2 * (e + deb)), "hauteur": H + 0.3 + hc + 0.45}


# ---------------------------------------------------------------------------
# 5) Tour blanche
# ---------------------------------------------------------------------------

def tour_blanche(b, variant=0, hauteur=40, cote=12, raccords=None):
    """Tour de guet blanche carrée (yagura), avant vers -Z : base de pierre talutée (≈ H/6), fût blanc
    (cote - 2) à bandeau et meurtrières, salle haute en encorbellement (cote + 1) à fenêtres sombres sur les
    quatre faces, consoles, balcon de bois tout autour, toit (débord ≤ 2 au-delà du côté).
    variant 0 : irimoya ocre ; 1 : croupe BLEUE ; 2 : toit ocre à deux étages ; 3 : pyramide ocre en gradins,
    épi sombre et garde-corps rouge.
    `raccords` (défaut : cote ≥ 14, tours de rempart) : le rempart traverse la tour le long de X et s'arrête en
    x = ±cote/2 ; deux raccords blancs prolongent le mur jusqu'au fût (jusqu'à y = 31) pour cacher ses bouts.
    Budget 65."""
    rng = b.rng
    v = variant % 4
    C, H = float(cote), float(hauteur)
    h = C / 2
    raccords = (C >= 14) if raccords is None else raccords
    Hb = round(H / 6 * 2) / 2                   # base de pierre ≈ H/6
    Ht = H * (0.21 if v == 2 else 0.16)         # toit
    Hs = max(5.0, round(H * 0.13 * 2) / 2)      # salle haute
    Yr = H - Ht - Hs                            # plancher de la salle
    hf = h - 1                                  # demi-côté du fût
    hs = h + 0.5                                # demi-côté de la salle
    hb = h + 1.5                                # demi-côté du balcon
    with b.group("TourBlanche"):
        n0 = len(b.parts)
        # base de pierre : talus sur l'avant et l'arrière, côtés droits (le rempart s'y appuie)
        cols = _pierres(rng, 3)
        for k, (y0, y1, dz) in enumerate(((0, Hb * 0.4, h), (Hb * 0.4, Hb * 0.72, h - 0.4), (Hb * 0.72, Hb, h - 0.8))):
            b.box((-h, y0, -dz), (h, y1, dz), cols[k], studs="top", name="Base")
        # fût en deux assises d'enduit, bandeau, meurtrières
        ym = Hb + (Yr - 0.8 - Hb) * 0.5
        cb = _blancs(rng, 2)
        b.box((-hf, Hb, -hf), (hf, ym, hf), cb[0], name="Fut")
        b.box((-hf, ym, -hf), (hf, Yr - 0.8, hf), cb[1], name="Fut")
        # auvent de tuiles à mi-fût (sur les quatre faces ; avant et arrière seulement quand le rempart traverse)
        if raccords:
            _auvent(b, -hf, hf, -hf, -1, ym, 1.6, 1.1, rng, rive=None)
            _auvent(b, -hf, hf, hf, 1, ym, 1.6, 1.1, rng, rive=None)
        else:
            _jupe(b, -hf - 1.6, hf + 1.6, -hf - 1.6, hf + 1.6, ym, 1.1, (1.6, 1.6, 1.6, 1.6), "ocre", rng, rive=None,
                  coeur=False, name="Auvent")
        yf = ym + (Yr - 0.8 - ym) * 0.4
        b.box((-0.7, yf, -hf - 0.1), (0.7, yf + 2.4, hf + 0.1), c("fenetre"), collide=False, name="Meurtriere")
        b.box((-hf - 0.1, yf, -0.7), (hf + 0.1, yf + 2.4, 0.7), c("fenetre"), collide=False, name="Meurtriere")
        yl = Hb + (ym - Hb) * 0.5
        b.box((-0.6, yl, -hf - 0.1), (0.6, yl + 1.2, hf + 0.1), c("fenetre"), collide=False, name="Meurtriere")
        if raccords:
            for s in (-1, 1):
                xa, xb = sorted((s * (hf - 0.2), s * h))
                b.box((xa, Hb, -2.6), (xb, 31.0, 2.6), c("blanc"), name="Raccord")
        # encorbellement : consoles sur les quatre faces, plancher-balcon, salle
        ys = Yr - 0.8
        bf = c("bois_fonce")
        b.wedge_under((-hs, ys - 1.6, -hs), (hs, ys, -hf), bf, down="-z", name="Console")
        b.wedge_under((-hs, ys - 1.6, hf), (hs, ys, hs), bf, down="+z", name="Console")
        b.wedge_under((-hs, ys - 1.6, -hf), (-hf, ys, hf), bf, down="-x", name="Console")
        b.wedge_under((hf, ys - 1.6, -hf), (hs, ys, hf), bf, down="+x", name="Console")
        b.box((-hb, ys, -hb), (hb, Yr, hb), c("bois"), studs="top", name="Balcon_plancher")
        b.box((-hs, Yr, -hs), (hs, Yr + Hs, hs), vr("blanc", rng, 0.02), name="Salle")
        # fenêtres sur les quatre faces (blocs traversants), un meneau chacune
        yw0, yw1 = Yr + 1.2, Yr + Hs - 1.3
        for xc in (-h * 0.45, h * 0.45):
            b.box((xc - 1.3, yw0, -hs - 0.1), (xc + 1.3, yw1, hs + 0.1), c("fenetre"), collide=False, name="Fenetre")
            b.box((xc - 0.17, yw0 + 0.05, -hs - 0.25), (xc + 0.17, yw1 - 0.05, hs + 0.25), bf, collide=False,
                  name="Meneau")
        for zc in (-h * 0.45, h * 0.45):
            b.box((-hs - 0.1, yw0, zc - 1.3), (hs + 0.1, yw1, zc + 1.3), c("fenetre"), collide=False, name="Fenetre")
            b.box((-hs - 0.25, yw0 + 0.05, zc - 0.17), (hs + 0.25, yw1 - 0.05, zc + 0.17), bf, collide=False,
                  name="Meneau")
        # garde-corps du balcon (laque rouge sur la variante 3)
        gc = c("laque_rouge") if v == 3 else c("bois_fonce")
        yh = Yr + 1.7
        b.box((-hb, yh, -hb), (hb, yh + 0.4, -hb + 0.4), gc, collide=False, name="Garde_corps")
        b.box((-hb, yh, hb - 0.4), (hb, yh + 0.4, hb), gc, collide=False, name="Garde_corps")
        b.box((-hb, yh, -hb + 0.4), (-hb + 0.4, yh + 0.4, hb - 0.4), gc, collide=False, name="Garde_corps")
        b.box((hb - 0.4, yh, -hb + 0.4), (hb, yh + 0.4, hb - 0.4), gc, collide=False, name="Garde_corps")
        for sx in (-1, 1):
            for sz in (-1, 1):
                xa, xb = sorted((sx * (hb + 0.05), sx * (hb - 0.5)))
                za, zb = sorted((sz * (hb + 0.05), sz * (hb - 0.5)))
                b.box((xa, Yr, za), (xb, yh + 0.7, zb), gc, collide=False, name="Poteau")
        b.box((-hs - 0.12, Yr + Hs - 1.0, -hs - 0.12), (hs + 0.12, Yr + Hs - 0.45, hs + 0.12), bf, name="Sabliere")
        # toit
        Y = Yr + Hs
        R = h + 2.0                       # débord maximal : 2 au-delà du côté
        if v == 0:
            hh = Ht - 0.8 - 1.2
            _irimoya(b, -R, R, -R, R, Y, hh * 0.4, hh * 0.6, (2.6, 2.6, 2.6, 2.6), "ocre", rng, rive=None,
                     ornement="or", h_orn=1.0, gegyo="or")
        elif v == 1:
            _croupe(b, -R, R, -R, R, Y, Ht - 2.1, "bleu", rng, niveaux=3, sous="bleu_profond", rive=None,
                    faite="bleu_profond", epi="or")
        elif v == 2:
            _, _, _, _, ya = _jupe(b, -R, R, -R, R, Y, Ht * 0.24, (2.4, 2.4, 2.4, 2.4), "ocre", rng, rive=None)
            hu = h - 1.6
            b.box((-hu, ya, -hu), (hu, ya + 1.9, hu), vr("blanc", rng, 0.02), name="Etage")
            b.box((-1.4, ya + 0.35, -hu - 0.1), (1.4, ya + 1.55, hu + 0.1), c("fenetre"), collide=False, name="Fenetre")
            b.box((-hu - 0.1, ya + 0.35, -1.4), (hu + 0.1, ya + 1.55, 1.4), c("fenetre"), collide=False, name="Fenetre")
            R2 = hu + 1.7
            hh = H - (ya + 1.9) - 0.8 - 1.0
            _irimoya(b, -R2, R2, -R2, R2, ya + 1.9, hh * 0.38, hh * 0.62, (1.9, 1.9, 1.9, 1.9), "ocre", rng, rive=None,
                     ornement="or", h_orn=0.9, gegyo=None)
        else:
            nst = 5
            hstep = (Ht - 1.8) / nst
            for k in range(nst):
                r = R - k * (R - 1.4) / nst
                b.box((-r, Y + k * hstep, -r), (r, Y + (k + 1) * hstep, r),
                      shade(c("ocre"), 0.82) if k == 0 else vr("ocre", rng, 0.03), studs="top", name="Toit_gradin")
            b.box((-0.45, Y + nst * hstep, -0.45), (0.45, H, 0.45), c("ardoise_fleche"), collide=False, name="Epi")
            b.box((-0.8, Y + nst * hstep, -0.8), (0.8, Y + nst * hstep + 0.5, 0.8), c("laque_noire"), collide=False,
                  name="Epi_base")
        n = len(b.parts) - n0
        assert n <= 65, n
    return {"emprise": (C, C), "hauteur": H}


# ---------------------------------------------------------------------------
# 6) Portail de cour
# ---------------------------------------------------------------------------

def portail_cour(b, variant=0, largeur=10, hauteur=12, texte=None, h_mur=10.0):
    """Portail d'enclos (yakuimon) posé dans un mur d'allée : la façade regarde -Z (l'allée), le mur passe en
    z = 0 (épaisseur 2,4, sommet `h_mur`, chaperon ≈ h_mur + 1,7) et s'arrête en x = ±(largeur/2 + 2).
    Emprise |x| ≤ largeur/2 + 2, z ∈ [-4, 3,5]. Ouverture libre `largeur` × (h_mur - 1,5) ; vantaux
    entrouverts vers l'intérieur (+Z) ; petit toit ocre à deux pentes (faîtage le long de X) qui domine le
    chaperon (`hauteur` ≥ h_mur + 3,5) ; plaque `texte` en façade (aucune si None) ; deux lanternes.
    variant 0 : bois sombre ; 1 : poteaux et linteau laqués rouges ; 2 : piles d'enduit blanc ; 3 : bois sombre
    et noren bleu dans l'ouverture. Budget 60."""
    rng = b.rng
    v = variant % 4
    W = largeur / 2                       # demi-ouverture
    X = W + 2.0                           # bout du mur d'allée (7 pour une ouverture de 10)
    hauteur = max(float(hauteur), float(h_mur) + 3.5)
    Y_l = float(h_mur) - 1.0              # dessous du linteau
    Y_t = hauteur                         # dessus de la sous-face du toit
    Y_s = Y_t - 0.4                       # dessous de la sous-face
    with b.group("PortailCour"):
        n0 = len(b.parts)
        poteau = c("laque_rouge") if v == 1 else c("bois_fonce")
        poutre = c("laque_rouge") if v == 1 else c("bois")
        noir = c("laque_noire")
        b.box((-X, 0, -1.7), (X, 0.3, 1.7), c("pierre_claire"), studs="top", name="Seuil")
        if v == 2:
            # piles d'enduit blanc sur socle de pierre
            for s in (-1, 1):
                xa, xb = sorted((s * W, s * X))
                b.box((xa, 0.3, -1.7), (xb, 1.8, 1.7), c("pierre"), studs="top", name="Socle")
                b.box((xa, 1.8, -1.45), (xb, Y_s, 1.45), vr("blanc", rng, 0.02), name="Pile")
                xi, xe = sorted((s * (W - 0.1), s * (X - 0.1)))
                b.box((xi, 4.4, -1.6), (xe, 4.9, 1.6), c("blanc_ombre"), name="Bandeau")
                b.box((xi, Y_l - 1.4, -1.6), (xe, Y_l - 0.9, 1.6), c("bois_fonce"), name="Bandeau")
            b.box((-W, Y_l, -1.2), (W, Y_l + 1.0, 1.2), c("bois"), name="Linteau")
            z_pl = -1.2
        else:
            for s in (-1, 1):
                # poteau principal (kagami-bashira) avec pied laqué noir
                xa, xb = sorted((s * W, s * (W + 1.2)))
                b.box((xa, 0.3, -0.7), (xb, Y_s, 0.7), poteau, name="Poteau")
                b.box((xa - 0.1, 0.3, -0.85), (xb + 0.1, 1.0, 0.85), noir, collide=False, name="Pied")
                # raccord au mur d'allée (même plinthe, même enduit)
                xa2, xb2 = sorted((s * (W + 1.2), s * X))
                b.box((xa2, 0.3, -1.5), (xb2, 1.5, 1.5), c("pierre"), studs="top", name="Socle")
                b.box((xa2, 1.5, -1.2), (xb2, Y_s, 1.2), vr("blanc", rng, 0.02), name="Raccord")
                # poteau arrière (hikae-bashira) et entretoise
                xa3, xb3 = sorted((s * (W + 0.1), s * (W + 0.9)))
                b.box((xa3, 0.3, 2.3), (xb3, Y_l - 0.5, 3.1), poteau, name="Poteau_arriere")
                b.box((xa3 + 0.05, 7.0, 0.7), (xb3 - 0.05, 7.6, 2.3), poutre, collide=False, name="Entretoise")
            b.box((-X + 0.3, Y_l, -0.9), (X - 0.3, Y_l + 1.0, 0.9), poutre, name="Linteau")
            b.box((-W - 0.9, Y_l - 0.5, 2.2), (W + 0.9, Y_l, 3.2), poutre, collide=False, name="Poutre_arriere")
            z_pl = -0.9
        # frise sous le toit
        b.box((-X + 0.4, Y_l + 1.0, -0.6), (X - 0.4, Y_s, 0.6), c("blanc_pur") if v == 1 else c("blanc"), name="Frise")
        # toit à deux pentes : sous-face sombre, coins stud, faîtage, tuiles de rive claires, bouts de faîtage
        zt0, zt1 = -4.0, 3.5
        b.box((-X, Y_s, zt0), (X, Y_t, zt1), c("ocre_fonce"), name="Toit_sous")
        zm = -0.25
        ht = hauteur + 2.1 - 0.5 - Y_t
        b.wedge((-X, Y_t, zt0), (X, Y_t + ht, zm), vr("ocre", rng, 0.02), down="-z", studs="top", name="Toit")
        b.wedge((-X, Y_t, zm), (X, Y_t + ht, zt1), vr("ocre", rng, 0.02), down="+z", studs="top", name="Toit")
        pente = ht / (zm - zt0)
        b.box((-X + 0.1, Y_t + ht - 0.5 * pente - 0.25, zm - 0.5), (X - 0.1, hauteur + 2.1, zm + 0.5), c("ocre_fonce"),
              studs="top", name="Toit_faite")
        for zr, s in ((zt0, -1), (zt1, 1)):
            za, zb = sorted((zr + s * 0.1, zr - s * 0.5))
            b.box((-X + 0.1, Y_t - 0.15, za), (X - 0.1, Y_t + 0.3, zb), c("ocre_clair"), collide=False, name="Toit_rive")
        for s in (-1, 1):
            xa, xb = sorted((s * (X + 0.1), s * (X - 0.9)))
            b.box((xa, hauteur + 1.4, zm - 0.7), (xb, hauteur + 2.6, zm + 0.7), c("ocre_brun"), collide=False,
                  name="Toit_oni")
        # vantaux entrouverts vers l'intérieur (+Z)
        ouv = 33.0
        for s in (-1, 1):
            R = rot_y(180 + ouv) if s > 0 else rot_y(-ouv)
            d = R @ np.array([1.0, 0, 0])
            Lv = W - 0.3
            ctr = np.array([s * (W - 0.05), 0, 0.75]) + d * Lv / 2
            ctr[1] = 0.3 + (Y_l - 0.5) / 2
            b.part("block", (Lv, Y_l - 0.5, 0.35), ctr, R, vr("bois_fonce", rng, 0.04), name="Vantail")
            for yb in (1.6, Y_l - 1.9):
                cb = ctr.copy()
                cb[1] = 0.3 + yb
                b.part("block", (Lv - 0.3, 0.45, 0.6), cb, R, c("fer"), collide=False, name="Bande_fer")
        # noren bleu (variante 3) : sous le linteau, au-dessus de 7 studs
        if v == 3:
            lw = (2 * W - 0.3) / 3
            for i in range(3):
                xa = -W + 0.15 + i * lw
                b.box((xa + 0.06, Y_l - 2.0, -0.95), (xa + lw - 0.06, Y_l, -0.85), c("noren_bleu"), collide=False,
                      name="Noren")
        if texte:
            _plaque(b, 0.0, Y_l - 0.1, 1.8, 1.8, z_pl, -1, texte, ep=0.2)
        lc = "orange_lampion" if v == 1 else "lampion_papier"
        for s in (-1, 1):
            _lampion(b, s * (W - 0.6), Y_s, -3.0, lc, r=0.55, h=1.2, cordon=0.6)
        n = len(b.parts) - n0
        assert n <= 60, n
    return {"emprise": (2 * X, 7.5), "hauteur": hauteur + 2.6, "demi_largeur": X}


# ---------------------------------------------------------------------------
# 1) Grande porte
# ---------------------------------------------------------------------------

ENDUITS_PORTE = ("blanc", "blanc_creme", "blanc_ombre", "blanc_creme", "blanc")   # vantaux enduits (kura)


def _vantail(b, charniere, ouv, s, L, H, ep, rng, *, y0=0.3, bandes=None, clous=None, n_clous=8, guichet=True,
             materiau="bois", name="Vantail"):
    """Vantail géant ouvert de `ouv` degrés vers +Z, côté s (charnière en x = s·|x|, z) : panneaux verticaux,
    traverses haute et basse laquées noir, bandes de fer et rangées de clous dorés traversantes (visibles sur
    les deux faces), montants laqués aux deux bords, ferrures d'angle dorées, guichet (kuguri-do) à hauteur de
    joueur. materiau "bois" : planches sombres, cinq bandes ; "enduit" : porte de kura enduite de blanc
    (panneaux de blancs voisins), cadre en gradin blanc pur à l'intérieur du cadre laqué, trois bandes."""
    enduit = materiau == "enduit"
    if bandes is None:
        bandes = (0.06, 0.3, 0.5, 0.7, 0.94) if enduit else (0.06, 0.27, 0.5, 0.73, 0.94)
    if clous is None:
        clous = (1, 2, 3) if enduit else (0, 1, 2, 3, 4)
    th = math.radians(ouv)
    d = np.array([-s * math.cos(th), 0.0, math.sin(th)])          # de la charnière vers le bord libre
    a = math.degrees(math.atan2(-d[2], d[0]))
    R = rot_y(a)
    O = np.array([charniere[0], 0.0, charniere[1]])

    def bloc(u0, u1, v0, v1, w, couleur, nom, **kw):
        ctr = O + R @ np.array([(u0 + u1) / 2, 0.0, 0.0])
        ctr[1] = (v0 + v1) / 2
        return b.part("block", (u1 - u0, v1 - v0, w), ctr, R, col(couleur), name=nom, **kw)

    n_pl = 5 if L > 42 else 4
    for i in range(n_pl):
        if enduit:
            bloc(L * i / n_pl, L * (i + 1) / n_pl, y0, y0 + H, ep, vr(ENDUITS_PORTE[i % 5], rng, 0.01), f"{name}_enduit")
        else:
            bloc(L * i / n_pl, L * (i + 1) / n_pl, y0, y0 + H, ep, vr(BOIS_PORTE[i % 4], rng, 0.03), f"{name}_planche")
    if enduit:
        # cadre en gradin (jabara) blanc pur, à l'intérieur des montants et des traverses laqués
        bloc(0.95, 2.05, y0 + 2.6, y0 + H - 2.2, ep + 0.5, "blanc_pur", f"{name}_gradin", collide=False)
        bloc(L - 2.05, L - 0.95, y0 + 2.6, y0 + H - 2.2, ep + 0.5, "blanc_pur", f"{name}_gradin", collide=False)
        bloc(2.05, L - 2.05, y0 + 2.6, y0 + 3.7, ep + 0.5, "blanc_pur", f"{name}_gradin", collide=False)
        bloc(2.05, L - 2.05, y0 + H - 3.3, y0 + H - 2.2, ep + 0.5, "blanc_pur", f"{name}_gradin", collide=False)
    # traverses laquées en bas et en haut (cadre), plus épaisses que les planches
    bloc(0.95, L - 0.95, y0 + 0.2, y0 + 2.6, ep + 0.25, "laque_noire", f"{name}_traverse", collide=False)
    bloc(0.95, L - 0.95, y0 + H - 2.2, y0 + H - 0.2, ep + 0.25, "laque_noire", f"{name}_traverse", collide=False)
    for k, f in enumerate(bandes):
        vb = y0 + H * f
        if enduit and k in (0, len(bandes) - 1):
            continue            # porte enduite : les traverses laquées tiennent lieu de bandes haute et basse
        bloc(0.95, L - 0.95, vb - 0.9, vb + 0.9, ep + 0.7, "fer", f"{name}_bande", collide=False)
        if k in clous:
            for i in range(n_clous):
                u = L * (i + 0.5) / n_clous
                if guichet and k == 0 and abs(u - L * 0.62) < 2.8:
                    continue
                bloc(u - 0.6, u + 0.6, vb - 0.6, vb + 0.6, ep + 1.1, OR_VIEUX if i % 2 else "or",
                     f"{name}_clou", collide=False)
    for u0, u1 in ((0.15, 0.95), (L - 0.95, L - 0.15)):
        bloc(u0, u1, y0 + 0.2, y0 + H - 0.2, ep + 0.3, "laque_noire", f"{name}_montant", collide=False)
    # ferrures d'angle dorées (côté bord libre, en haut et en bas)
    for v0, v1 in ((y0 + 0.4, y0 + 3.4), (y0 + H - 3.4, y0 + H - 0.4)):
        bloc(L - 3.2, L - 0.3, v0, v1, ep + 0.8, "or", f"{name}_ferrure", collide=False)
    if guichet:
        ug = L * 0.62
        vg0 = y0 + H * bandes[0] + 1.1
        bloc(ug - 2.3, ug + 2.3, vg0, vg0 + 7.0, ep + 0.6, "fer", f"{name}_guichet_cadre", collide=False)
        bloc(ug - 1.8, ug + 1.8, vg0 + 0.4, vg0 + 6.6, ep + 0.8, "laque_noire", f"{name}_guichet", collide=False)
        bloc(ug + 1.0, ug + 1.5, vg0 + 3.0, vg0 + 3.6, ep + 1.1, "or", f"{name}_guichet_poignee", collide=False)
    return O + d * L


def _auvent(b, x0, x1, zf, sens, y, prof, h, rng, *, toit="ocre", sous="ocre_fonce", rive="ocre_clair",
            name="Auvent"):
    """Auvent de tuiles (hisashi) le long de X contre une façade en z = zf, qui déborde de `prof` vers `sens`
    (+1 : +Z, -1 : -Z) : dalle sombre dessous, coin stud dont la pente descend vers l'extérieur, rang de tuiles
    de rive plus claires au bord de l'égout."""
    za, zb = sorted((zf, zf + sens * prof))
    b.box((x0, y - 0.4, za), (x1, y, zb), col(sous), name=f"{name}_sous")
    b.wedge((x0, y, za), (x1, y + h, zb), vr(toit, rng, 0.02), down="+z" if sens > 0 else "-z", studs="top",
            name=name)
    if rive:
        ze_ = zf + sens * prof
        ra, rb = sorted((ze_ + sens * 0.1, ze_ - sens * 0.55))
        b.box((x0 + 0.1, y - 0.25, ra), (x1 - 0.1, y + 0.22, rb), col(rive), collide=False, name=f"{name}_rive")


def _enduit_coupes(b, coupes, y0, y1, z0, z1, rng, name="Enduit"):
    """Enduit en panneaux de blancs voisins entre les abscisses `coupes` (triées), pleine épaisseur."""
    cols = _blancs(rng, len(coupes) - 1)
    for (a, bb), cc in zip(zip(coupes, coupes[1:]), cols):
        if bb - a > 0.05:
            b.box((a, y0, z0), (bb, y1, z1), cc, name=name)


def _tour_angle(b, xc, s, rng, *, toit="ocre", H=64.0, YM=36.0):
    """Tour d'angle (sumi-yagura) de la grande porte, centrée en (xc, 0), emprise 16 × 17 ; s = côté (le grand
    mur arrive par la face x = xc - s·8). Base de pierre talutée, corps blanc à auvent de tuiles au niveau de
    celui du grand mur (YM), corps haut qui dépasse du chaperon, auvent à quatre pans, salle haute à fenêtres
    sur les quatre faces, toit irimoya ocre (ou croupe bleue). Renvoie le haut."""
    hx, hz = 8.0, 8.5
    y_corps = H + 9.0
    with b.group("TourAngle"):
        for k, (y0, y1, d) in enumerate(((0, 3.5, 2.0), (3.5, 7.5, 1.4), (7.5, 12, 0.8))):
            cols = _pierres(rng, 2)
            b.box((xc - hx - d, y0, -hz - d), (xc, y1, hz + d), cols[0], studs="top", name="Base")
            b.box((xc, y0, -hz - d), (xc + hx + d, y1, hz + d), cols[1], studs="top", name="Base")
        cb = _blancs(rng, 4)
        b.box((xc - hx, 12, -hz), (xc, YM, hz), cb[0], name="Corps")
        b.box((xc, 12, -hz), (xc + hx, YM, hz), cb[1], name="Corps")
        b.box((xc - hx, YM, -hz), (xc, y_corps, hz), cb[2], name="Corps")
        b.box((xc, YM, -hz), (xc + hx, y_corps, hz), cb[3], name="Corps")
        # auvent intermédiaire : avant, arrière et face extérieure (côté mur : le hisashi du mur s'y raccorde)
        xi, xe = xc - s * hx, xc + s * (hx + 2.2)
        xa, xb = sorted((xi, xe))
        _auvent(b, xa, xb, hz, 1, YM, 2.2, 1.6, rng, rive=None)
        _auvent(b, xa, xb, -hz, -1, YM, 2.2, 1.6, rng, rive=None)
        with b.at((xc + s * hx, 0, 0), yaw=-90 * s):
            _auvent(b, -hz, hz, 0.0, -1, YM, 2.2, 1.6, rng, rive=None)
        b.box((xc - hx - 0.15, y_corps - 1.2, -hz - 0.15), (xc + hx + 0.15, y_corps, hz + 0.15), c("bois_fonce"),
              name="Bandeau_haut")
        _fenetres_x(b, (xc - 3.5, xc + 3.5), 2.4, y_corps - 7.5, y_corps - 3.5, -hz, hz, barreaux=1)
        _meurtrieres_x(b, (xc,), 24, 1.5, -hz, hz)
        _meurtrieres_x(b, (xc - 3.5, xc + 3.5), YM + 8, 1.4, -hz, hz)
        b.box((xc - hx - 0.1, y_corps - 7.5, -1.2), (xc + hx + 0.1, y_corps - 3.5, 1.2), c("fenetre"),
              collide=False, name="Fenetre")
        b.box((xc - hx - 0.1, 24, -0.75), (xc + hx + 0.1, 25.5, 0.75), c("fenetre"), collide=False, name="Meurtriere")
        # auvent (hisashi), salle haute, toit
        sous = "ocre_fonce" if toit == "ocre" else "bleu_profond"
        rive = "ocre_clair" if toit == "ocre" else "bleu_clair"
        _, _, _, _, ya = _jupe(b, xc - 10.2, xc + 10.2, -10.7, 10.7, y_corps, 1.8, (2.6, 2.6, 2.6, 2.6), toit, rng,
                               sous=sous, rive=rive)
        ys1 = ya + 6.0
        b.box((xc - 6.5, ya, -7.0), (xc + 6.5, ys1, 7.0), vr("blanc", rng, 0.02), name="Salle")
        _fenetres_x(b, (xc - 3, xc + 3), 2.6, ya + 1.1, ys1 - 1.1, -7.0, 7.0, barreaux=1)
        _fenetres_z(b, (-3, 3), 2.6, ya + 1.1, ys1 - 1.1, xc - 6.5, xc + 6.5, barreaux=1)
        b.box((xc - 6.65, ys1 - 0.9, -7.15), (xc + 6.65, ys1 - 0.45, 7.15), c("bois_fonce"), name="Sabliere")
        if toit == "ocre":
            r = _irimoya(b, xc - 8.6, xc + 8.6, -9.1, 9.1, ys1, 2.0, 4.4, (2.7, 2.7, 2.7, 2.7), "ocre", rng,
                         ornement="or", h_orn=1.6)
            return r["top"]
        return _croupe(b, xc - 8.6, xc + 8.6, -9.1, 9.1, ys1, 6.4, "bleu", rng, niveaux=3, sous="bleu_profond",
                       rive="bleu_clair", faite="bleu_profond", epi="or")


def _poches_vantail(xh, zh, phi_deg, z_nez, marge=1.8):
    """Profondeur de la poche (nez des bastions) pour qu'un vantail charnière en (xh, zh), ouvert à phi degrés
    du plan du mur, passe devant le nez du bastion (coin en z = z_nez) avec `marge` de jeu."""
    p = math.radians(phi_deg)
    return xh + (marge + (z_nez - zh) * math.cos(p)) / math.sin(p) + 0.6


def grande_porte(b, variant=0, ouverture=100, hauteur=64, mur=150, epaisseur=16, angle_vantaux=None,
                 z_max_vantaux=60.0, vantaux="enduit"):
    """Grande porte d'entrée (posée en (0, 0, 0), yaw 0 ; face d'arrivée = +Z, esplanade) : mur d'enceinte
    blanc de `hauteur` sur base de pierre talutée, auvent de tuiles à mi-hauteur, fenêtres et meurtrières,
    chaperon ocre ; ouverture |x| < ouverture/2 libre sur toute l'épaisseur jusqu'au plafond du passage
    (YP ≥ 50, plus haut pour une ouverture large : 56 pour 100) ; bastions sur base de pierre en gradins, à
    bretèche (ishi-otoshi) ; corps de garde (yagura) au-dessus, à fenêtres sombres et balcons laqués rouges sur
    les deux faces, plaque 門 (et 静 au revers) ; vantaux géants ouverts vers l'extérieur (angle calculé pour
    que leur bout reste en z ≤ z_max_vantaux, au moins 95° : avec 60, ≈ 102°, presque perpendiculaires au mur,
    alignés le long de l'esplanade, ils se présentent par la tranche et laissent voir la façade) ; vantaux
    `vantaux` = "enduit" (portes de kura blanches, défaut) ou "bois" (planches sombres) ; tours d'angle en
    x = ±mur.
    variant 0 : toit du corps de garde à deux étages ; 1 : un seul grand toit, balcon et poteaux rouges, tours
    d'angle à toit bleu ; 2 : bastions plus lourds en gradins, toit à trois étages. Budget 850."""
    rng = b.rng
    v = variant % 3
    xo = ouverture / 2              # bord de l'ouverture (38 ; 50 pour le couloir élargi)
    ze = epaisseur / 2              # 8 : faces du mur
    H = float(hauteur)              # 64
    M = float(mur)                  # 150
    YP = float(max(51, min(H - 8, round(ouverture * 0.56))))     # plafond du passage : 51 (76) … 56 (100)
    YM = float(round(H * 0.56))     # 36 : auvent intermédiaire du grand mur
    ZAV, ZAR = ze + 5.0, -(ze + 1.4)   # 13 / -9,4 : faces avant / arrière des bastions
    XT = M - 8.0                    # flanc des tours d'angle
    zh = ze + 1.6                   # charnières des vantaux
    Lv = xo                         # largeur d'un vantail
    if angle_vantaux is None:
        angle_vantaux = max(95.0, 180.0 - math.degrees(math.asin(min(1.0, (z_max_vantaux - zh - 1.5) / Lv))))
    phi = 180.0 - angle_vantaux
    # charnière assez loin du bord pour que le vantail ouvert (montants et clous compris) reste en |x| ≥ xo + 0,2
    xh = xo + max(0.9, 1.55 * math.sin(math.radians(phi)) + 0.1)
    dav0 = 2.4 if v == 2 else 2.0
    XJ = math.ceil(max(xo + 5.5, _poches_vantail(xh, zh, phi, ZAV + dav0)) * 2) / 2   # nez des bastions
    XB = max(xo + 24.0, XJ + 15.0)  # flanc extérieur des bastions
    ZF, ZR = ZAV + 0.5, -ze         # faces du corps de garde
    Y1 = YP + (22.0 if v == 1 else 20.0)   # égout du premier toit
    n0 = len(b.parts)

    # --- grand mur, de part et d'autre --------------------------------------------------------------
    with b.group("Mur"):
        for s in (-1, 1):
            xa, xb = sorted((s * XB, s * XT))
            L = xb - xa
            _plinthe(b, xa, xb, -ze, ze, [(0, 4, 2.0), (4, 8, 1.2), (8, 11, 0.5)], rng, nseg=3)
            _enduit(b, xa, xb, 11, YM, -ze, ze, rng, max(2, math.ceil(L / 12)))
            _enduit(b, xa, xb, YM, H - 1.2, -ze, ze, rng, max(2, math.ceil(L / 15)))
            # soubassement de planches sombres (koshi-ita) et sa lisse laquée, sur les deux faces
            b.box((xa, 11, -ze - 0.15), (xb, 16.5, ze + 0.15), vr("bois_fonce", rng, 0.03), name="Koshi_ita")
            b.box((xa, 16.5, -ze - 0.3), (xb, 17.1, ze + 0.3), c("laque_noire"), collide=False, name="Koshi_lisse")
            b.box((xa, H - 1.2, -ze - 0.15), (xb, H, ze + 0.15), c("bois_fonce"), name="Bandeau_haut")
            _auvent(b, xa, xb, ze, 1, YM, 2.6, 1.8, rng)
            _auvent(b, xa, xb, -ze, -1, YM, 1.8, 1.3, rng, rive=None)
            xw = _repartis(xa, xb, 11)
            _fenetres_x(b, xw, 3.2, YM + 8.0, YM + 13.0, -ze, ze, barreaux=2)
            _meurtrieres_x(b, [(p + q) / 2 for p, q in zip(xw, xw[1:])], H - 7.5, 1.4, -ze, ze)
            _meurtrieres_x(b, _repartis(xa, xb, 9), 21.0, 1.5, -ze, ze)
            _chaperon(b, xa, xb, 0.0, ze, H, 1.5, 3.6, rng, ep_sous=0.5, fw=0.8, rive="ocre_clair", retrait_faite=0.0)

    # --- tours d'angle ----------------------------------------------------------------------------------
    for s in (-1, 1):
        _tour_angle(b, s * M, s, rng, toit="bleu" if v == 1 else "ocre", H=H, YM=YM)

    # --- bastions, tableaux de l'ouverture, poteaux de charnière ----------------------------------------
    with b.group("Bastions"):
        if v == 2:
            marches = [(0, 5, 2.4, 0.6, 0.6), (5, 10, 1.8, 0.45, 0.45), (10, 15, 1.2, 0.3, 0.3), (15, 20, 0.6, 0.15, 0.15)]
        else:
            marches = [(0, 5, 2.0, 0.6, 0.5), (5, 10, 1.3, 0.4, 0.3), (10, 15, 0.6, 0.2, 0.1)]
        yb = marches[-1][1]
        yc = YM - 3.0                # bandeau des bastions, sous l'auvent du grand mur
        for s in (-1, 1):
            for k, (y0, y1, dav, dar, dsi) in enumerate(marches):
                xa, xb = sorted((s * (XJ - dsi), s * XB))
                xm = s * (XJ + (XB - XJ) * (0.45 if k % 2 else 0.6))
                cols = _pierres(rng, 2)
                b.box((min(xa, xm), y0, ZAR - dar), (max(xa, xm), y1, ZAV + dav), cols[0], studs="top", name="Ishigaki")
                b.box((min(xm, xb), y0, ZAR - dar), (max(xm, xb), y1, ZAV + dav), cols[1], studs="top", name="Ishigaki")
            # corps du bastion : deux colonnes × deux assises, bandeau
            x0, x1 = sorted((s * XJ, s * XB))
            xm = (x0 + x1) / 2
            cb = _blancs(rng, 4)
            for i, (xa, xb) in enumerate(((x0, xm), (xm, x1))):
                b.box((xa, yb, ZAR), (xb, yc, ZAV), cb[i], name="Bastion")
                b.box((xa, yc, ZAR), (xb, YP, ZAV), cb[2 + i], name="Bastion")
            b.box((x0 - 0.2, yc - 0.4, ZAR - 0.25), (x1 + 0.2, yc + 0.4, ZAV + 0.25), c("blanc_ombre"), name="Bandeau")
            if v == 2:
                b.box((x0 - 0.2, yb + 6.6, ZAR - 0.2), (x1 + 0.2, yb + 7.2, ZAV + 0.2), c("blanc_ombre"), name="Bandeau")
            # bretèche (ishi-otoshi) en saillie sur la face avant : consoles, corps, fenêtre, auvent
            yo0, yo1 = yc + 3.0, min(yc + 11.0, YP - 3.5)
            hw = min(4.5, (x1 - x0) / 2 - 2.0)
            b.wedge_under((xm - hw, yo0 - 1.6, ZAV), (xm + hw, yo0, ZAV + 1.5), c("blanc_ombre"), down="+z",
                          name="Breteche_console")
            b.box((xm - hw, yo0, ZAV), (xm + hw, yo1, ZAV + 1.5), vr("blanc_pur", rng, 0.01), name="Breteche")
            b.box((xm - hw + 1.4, yo0 + 2.0, ZAV + 1.5), (xm + hw - 1.4, yo1 - 1.6, ZAV + 1.62), c("fenetre"),
                  collide=False, name="Breteche_fenetre")
            for xq in (xm - hw / 3, xm + hw / 3):
                b.box((xq - 0.18, yo0 + 2.05, ZAV + 1.5), (xq + 0.18, yo1 - 1.65, ZAV + 1.78), c("bois_fonce"),
                      collide=False, name="Barreau")
            _auvent(b, xm - hw - 0.7, xm + hw + 0.7, ZAV, 1, yo1, 2.4, 1.4, rng, rive=None)
            # fenêtres hautes et meurtrières traversantes (deux faces)
            xw = (xm - (x1 - x0) * 0.27, xm + (x1 - x0) * 0.27)
            _fenetres_x(b, xw, 3.0, YP - 9.0, YP - 4.5, ZAR, ZAV, barreaux=2)
            _meurtrieres_x(b, xw, yb + 5.0, 1.5, ZAR, ZAV)
            # tableau (jambage) entre l'ouverture et le bastion : base de pierre, enduit
            xa, xb = sorted((s * (xo + 0.1), s * XJ))
            b.box((xa, 0, ZAR - 0.2), (xb, 4.0, ze + 0.2), vr("pierre_fonce", rng, 0.03), studs="top", name="Ishigaki")
            xa, xb = sorted((s * (xo + 0.5), s * XJ))
            _enduit_z(b, ZAR, ze, 4.0, round(YP * 0.55), xa, xb, rng, 2, name="Tableau")
            _enduit_z(b, ZAR, ze, round(YP * 0.55), YP, xa, xb, rng, 2, name="Tableau")
            # poteaux de charnière (avant laqué noir, arrière bois sombre) et ferrures
            xa, xb = sorted((s * xo, s * (xo + 2.6)))
            b.box((xa, 0, ze - 1.4), (xb, YP, ze + 1.4), c("laque_noire"), name="Poteau_porte")
            for yf in (6.0, YP - 8.0):
                b.box((xa, yf, ze + 1.4), (xb, yf + 2.4, ze + 1.75), c("fer"), collide=False, name="Ferrure")
            xa, xb = sorted((s * xo, s * (xo + 2.4)))
            b.box((xa, 0, ZAR - 0.6), (xb, YP, ZAR + 1.2), c("bois_fonce"), name="Poteau_porte")

    # --- corps de garde ---------------------------------------------------------------------------------
    with b.group("CorpsDeGarde"):
        # poutre sombre continue (plafond du passage) et solives apparentes sous le plafond
        b.box((-XB - 0.2, YP, ZAR - 0.3), (XB + 0.2, YP + 1.5, ZF + 0.3), c("laque_noire"), name="Poutre")
        for z in _repartis(ZAR + 1.0, ze - 0.5, 4.5):
            b.box((-xo - 0.4, YP - 1.0, z - 0.5), (xo + 0.4, YP, z + 0.5), c("bois_fonce"), name="Solive")
        y_s = YP + 1.5
        nfen = int((XB - 19.5) // 10) + 1
        xf = [9.5 + 10.0 * k for k in range(nfen)]
        coupes = sorted({-XB, XB} | {s * (x - 5.0) for s in (-1, 1) for x in xf})
        _enduit_coupes(b, coupes, y_s, Y1 - 0.45, ZR, ZF, rng, name="Corps_de_garde")
        b.box((-XB - 0.15, Y1 - 1.6, ZR - 0.15), (XB + 0.15, Y1 - 0.45, ZF + 0.15), c("bois_fonce"), name="Sabliere")
        xs = [s * x for s in (-1, 1) for x in xf]
        yw0, yw1 = YP + 9.0, min(YP + 15.4, Y1 - 2.4)
        _fenetres_x(b, xs, 5.0, yw0, yw1, ZR, ZF, barreaux=2)
        _fenetres_z(b, ((ZR + ZF) / 2,), 4.0, yw0, yw1, -XB, XB, barreaux=2)
        if v == 1:
            # poteaux laqués rouges entre les fenêtres (traversants : deux faces)
            for x in [s * (x - 5.0) for s in (-1, 1) for x in xf] + [s * (xf[-1] + 5.0) for s in (-1, 1)]:
                if abs(x) < XB - 0.6:
                    b.box((x - 0.55, y_s + 3.0, ZR - 0.3), (x + 0.55, Y1 - 1.6, ZF + 0.3), c("laque_rouge"),
                          name="Poteau")
        # balcons laqués : avant (consoles) et arrière, coupés au milieu par la plaque
        yb_ = YP + 5.5
        for xa, xb in ((-XB + 2, -3.9), (3.9, XB - 2)):
            _balcon(b, xa, xb, yb_, ZF, 3.5, 1, pas=5.0 if v == 1 else 7.0,
                    plancher="laque_rouge" if v == 1 else "laque_rouge_fonce")
            _balcon(b, xa, xb, yb_, ZR, 2.0, -1, pas=7.0, consoles=False)
        _plaque(b, 0.0, YP + 2.2, 6.0, 9.0, ZF, 1, "門")
        if v != 1:
            _plaque(b, 0.0, YP + 2.2, 5.0, 7.5, ZR, -1, "静")
        # lanternes : côté esplanade, à des consoles laquées qui sortent de la poutre devant les bastions ; côté
        # faubourg, sous le plancher du balcon arrière (rien au-delà de z = -10)
        for s in (-1, 1):
            xc = s * (XJ + XB) / 2
            b.box((xc - 0.4, YP + 0.3, ZF + 0.3), (xc + 0.4, YP + 1.1, ZAV + 2.7), c("laque_noire"), collide=False,
                  name="Console_lanterne")
            _lampion(b, xc, YP + 0.3, ZAV + 1.9, "lampion_papier", r=1.3, h=2.8, cordon=0.8)
            _lampion(b, xc, YP + 4.8, ZR - 1.0, "lampion_papier", r=0.8, h=1.7, cordon=0.5)
        # toits
        XU = xo + 2.0                 # demi-largeur de l'étage
        zu0, zu1 = ZR + 2.5, ZF - 3.0
        xu = [x for x in (9.0, 27.0, 45.0, 63.0) if x <= XU - 5.0]
        if v == 0:
            _, _, _, _, ya = _jupe(b, -XB - 4.0, XB + 4.0, ZR - 3.0, ZF + 4.0, Y1, 5.0, (4.5, 6.0, 6.5, 6.5), "ocre", rng)
            y2 = ya + 9.8
            _enduit(b, -XU, XU, ya, y2 - 0.45, zu0, zu1, rng, 7, name="Etage")
            _fenetres_x(b, [s * x for s in (-1, 1) for x in xu], 4.6, ya + 2.4, ya + 7.0, zu0, zu1, barreaux=2)
            b.box((-XU - 0.15, y2 - 1.4, zu0 - 0.15), (XU + 0.15, y2 - 0.45, zu1 + 0.15), c("bois_fonce"), name="Sabliere")
            r = _irimoya(b, -XU - 4, XU + 4, zu0 - 3.1, zu1 + 3.1, y2, 3.2, 6.6, (3.0, 3.0, 4.0, 4.0), "ocre", rng,
                         ornement="or", h_orn=2.6)
            _chidori(b, 0.0, 9.0, Y1 + 1.0, 7.0, zu1, ZF + 2.6, "ocre", rng)
            _chidori(b, 0.0, 5.5, Y1 + 0.8, 4.6, zu0, ZR - 1.9, "ocre", rng)
        elif v == 1:
            r = _irimoya(b, -XB - 4.5, XB + 4.5, ZR - 3.0, ZF + 4.0, Y1, 5.4, 11.5, (5.6, 6.6, 7.5, 7.5), "ocre", rng,
                         ornement="or", h_orn=3.0, deb_g=1.0)
            _chidori(b, 0.0, 9.0, Y1 + 0.9, 7.6, zu1 - 2.0, ZF + 3.0, "ocre", rng)
            _chidori(b, 0.0, 7.0, Y1 + 0.9, 6.2, zu0 + 3.5, ZR - 2.4, "ocre", rng)
        else:
            _, _, _, _, ya = _jupe(b, -XB - 4.0, XB + 4.0, ZR - 3.0, ZF + 4.0, Y1, 5.0, (4.5, 6.0, 6.5, 6.5), "ocre", rng)
            y2 = ya + 7.0
            XU2 = xo + 6.0
            _enduit(b, -XU2, XU2, ya, y2 - 0.45, zu0, zu1, rng, 7, name="Etage")
            _fenetres_x(b, [s * x for s in (-1, 1) for x in (15.0, 30.0, 45.0) if x <= XU2 - 5], 4.0, ya + 1.6, ya + 5.4,
                        zu0, zu1, barreaux=2)
            _chidori(b, 0.0, 7.0, Y1 + 0.8, 5.4, zu1, ZF + 2.6, "ocre", rng)
            _, _, _, _, yb2 = _jupe(b, -XU2 - 3.5, XU2 + 3.5, zu0 - 2.7, zu1 + 2.7, y2, 3.4, (3.4, 3.4, 4.5, 4.5), "ocre", rng)
            y3 = yb2 + 6.2
            XU3 = xo - 12.0
            _enduit(b, -XU3, XU3, yb2, y3 - 0.45, zu0 + 1.9, zu1 - 1.9, rng, 4, name="Etage")
            _fenetres_x(b, [s * x for s in (-1, 1) for x in (7.0, 21.0, 35.0) if x <= XU3 - 4] + [0.0], 3.6,
                        yb2 + 1.4, yb2 + 4.8, zu0 + 1.9, zu1 - 1.9, barreaux=2)
            r = _irimoya(b, -XU3 - 3.5, XU3 + 3.5, zu0 - 0.9, zu1 + 0.9, y3, 2.6, 5.2, (2.6, 2.6, 3.2, 3.2), "ocre", rng,
                         ornement="or", h_orn=2.4)

    # --- vantaux ouverts vers l'extérieur ---------------------------------------------------------------
    with b.group("Vantaux"):
        for s in (-1, 1):
            _vantail(b, (s * xh, zh), angle_vantaux, s, Lv, YP - 0.6, 2.5, rng,
                     n_clous=max(6, int(round(Lv / 5))), materiau=vantaux)
    n = len(b.parts) - n0
    assert n <= 850, n
    return {"emprise": (2 * M + 20, epaisseur + 6), "hauteur": _haut(b, n0), "pieces": n,
            "ouverture_libre": (2 * xo, YP - 1.0), "angle_vantaux": round(angle_vantaux, 1),
            "nez_bastions": round(XJ, 2), "flanc_bastions": round(XB, 2)}


# ---------------------------------------------------------------------------
# 2) Porte intérieure
# ---------------------------------------------------------------------------

def porte_interieure(b, variant=0, ouverture=92, hauteur_passage=36, mur=150, hauteur_mur=24, epaisseur=10,
                     x_allee=None):
    """Tour-porte (yagura-mon) entre le faubourg (+Z) et la cité blanche (-Z), posée en (0, 0, -176), yaw 0.
    xo = ouverture / 2 : passage |x| < xo libre jusqu'à y = hauteur_passage ; pylônes blancs sur base de pierre
    talutée (|x| xo..xo+12, xo+14 en variante 2) ; mur intérieur de `hauteur_mur` jusqu'au rempart
    (x = ±(mur - 1,5)) à soubassement de planches, meurtrières et chaperon ocre ; contreforts côté cité derrière
    les murs d'allée (face en |x| = x_allee, défaut xo + 9) ; corps de garde blanc à fenêtres et balcons laqués
    rouges sur les deux faces, plaques sur les deux faces ; vantaux de bois sombre ouverts à 90° vers le faubourg
    (+Z), couchés le long du trottoir (|x| ≥ xo + 0,1, clous compris, de z = ze + 1,35 à ze + 1,35 + xo/2).
    variant 0 : toit à deux étages, 静 ; 1 : un seul toit, pignons et faîtage bleus, 門 ;
    2 : pylônes plus lourds coiffés de tourelles à toit ocre, 静. Budget 420."""
    rng = b.rng
    v = variant % 3
    xo = ouverture / 2              # 46 pour le couloir élargi (36 dans le plan d'origine)
    Yp = float(hauteur_passage)     # 36
    Hm = float(hauteur_mur)         # 24
    ze = epaisseur / 2              # 5
    XA = xo + 9.0 if x_allee is None else float(x_allee)   # face des murs d'allée de la cité
    XP = xo + (14.0 if v == 2 else 12.0)   # flanc extérieur des pylônes
    XW = mur - 1.5                  # bout du mur contre le rempart
    XG = XP + (0.0 if v == 2 else 2.0)     # demi-largeur du corps de garde
    n0 = len(b.parts)
    texte = "門" if v == 1 else "静"

    # --- mur intérieur ----------------------------------------------------------------------------------
    with b.group("Mur"):
        for s in (-1, 1):
            xa, xb = sorted((s * XP, s * XW))
            L = xb - xa
            _plinthe(b, xa, xb, -ze, ze, [(0, 2, 0.9), (2, 4, 0.45)], rng, nseg=3)
            _enduit(b, xa, xb, 4, Hm - 1.0, -ze, ze, rng, max(2, math.ceil(L / 10)))
            b.box((xa, 4, -ze - 0.15), (xb, 8.5, ze + 0.15), vr("bois_fonce", rng, 0.03), name="Koshi_ita")
            b.box((xa, 8.5, -ze - 0.3), (xb, 9.0, ze + 0.3), c("laque_noire"), collide=False, name="Koshi_lisse")
            b.box((xa, Hm - 1.0, -ze - 0.12), (xb, Hm, ze + 0.12), c("bois_fonce"), name="Bandeau_haut")
            _meurtrieres_x(b, _repartis(xa, xb, 10), Hm - 5.4, 1.3, -ze, ze)
            _chaperon(b, xa, xb, 0.0, ze, Hm, 0.9, 2.8, rng, ep_sous=0.35, fw=0.6, rive="ocre_clair",
                      retrait_faite=0.0)

    # --- pylônes, contreforts, poteaux de charnière ------------------------------------------------------
    with b.group("Pylones"):
        yh = round(Yp * 0.58)       # 21 : bandeau des pylônes
        for s in (-1, 1):
            x0, x1 = sorted((s * (xo + 0.6), s * XP))
            for k, (y0, y1, d) in enumerate(((0, 3, 1.2), (3, 6, 0.7), (6, 8, 0.3))):
                xa, xb = sorted((s * (xo + 0.1), s * (XP + d)))
                cols = _pierres(rng, 1)
                b.box((xa, y0, -ze - (0.3 if k < 2 else 0.0)), (xb, y1, ze + d), cols[0], studs="top", name="Ishigaki")
            xm = (x0 + x1) / 2
            cb = _blancs(rng, 4)
            for i, (xa, xb) in enumerate(((x0, xm), (xm, x1))):
                b.box((xa, 8, -ze), (xb, yh, ze), cb[i], name="Pylone")
                b.box((xa, yh, -ze), (xb, Yp, ze), cb[2 + i], name="Pylone")
            xa, xb = sorted((s * (xo + 0.4), s * (XP + 0.2)))
            b.box((xa, yh - 0.4, -ze - 0.25), (xb, yh + 0.4, ze + 0.25), c("blanc_ombre"), name="Bandeau")
            _fenetres_x(b, (xm,), 3.0, yh + 5.0, yh + 9.5, -ze, ze, barreaux=2)
            _meurtrieres_x(b, (xm,), 12.5, 1.4, -ze, ze)
            # auvent de tuiles sur la face faubourg, au-dessus de la base de pierre (ombre forte)
            _auvent(b, x0 + 0.3, x1 - 0.3, ze, 1, yh + 0.4, 1.0, 0.9, rng, rive=None)
            # contrefort côté cité, derrière les murs d'allée (|x| > XA + 2,4)
            xa, xb = sorted((s * (XA + 2.5), s * (XP + 4.0)))
            b.box((xa, 0, -ze - 3.0), (xb, 5.0, -ze), vr("pierre_fonce", rng, 0.03), studs="top", name="Contrefort")
            b.box((xa + 0.3 * (s < 0), 5.0, -ze - 2.6), (xb - 0.3 * (s > 0), 27.0, -ze), vr("blanc_creme", rng, 0.02),
                  name="Contrefort")
            b.wedge((xa + 0.3 * (s < 0), 27.0, -ze - 2.6), (xb - 0.3 * (s > 0), 29.2, -ze), vr("ocre", rng, 0.02),
                    down="-z", studs="top", name="Contrefort_toit")
            # poteaux de charnière (deux faces)
            xa, xb = sorted((s * xo, s * (xo + 1.4)))
            b.box((xa, 0, ze - 1.7), (xb, Yp, ze + 0.6), c("bois_fonce"), name="Poteau_porte")
            b.box((xa, 0, -ze - 0.6), (xb, Yp, -ze + 1.7), c("laque_noire"), name="Poteau_porte")
            if v == 2:
                # tourelle sur le pylône, au-dessus du corps de garde
                ya = Yp + 16.0
                b.box((x0 + 0.5, ya, -ze + 0.3), (x1 - 0.5, ya + 8.0, ze - 0.3), vr("blanc", rng, 0.02), name="Tourelle")
                _fenetres_x(b, (xm,), 3.4, ya + 2.4, ya + 6.0, -ze + 0.3, ze - 0.3, barreaux=2)
                b.box((x0 + 0.35, ya + 7.0, -ze + 0.15), (x1 - 0.35, ya + 7.6, ze - 0.15), c("bois_fonce"),
                      name="Sabliere")
                _irimoya(b, x0 - 1.0, x1 + 1.0, -ze - 1.8, ze + 1.8, ya + 8.0, 2.2, 3.8, (2.4, 2.4, 2.6, 2.6), "ocre", rng,
                         ornement="or", h_orn=1.4, gegyo=None)

    # --- corps de garde ---------------------------------------------------------------------------------
    with b.group("CorpsDeGarde"):
        Y1 = Yp + (15.0 if v == 1 else 14.0)
        ZG = ze + 0.5
        XC = xo if v == 2 else XG          # en variante 2 : corps de garde entre les tourelles
        b.box((-XG - 0.2, Yp, -ze - 0.6), (XG + 0.2, Yp + 1.5, ze + 0.6), c("laque_noire"), name="Poutre")
        for z in (-ze + 1.5, 0.0, ze - 1.5):
            b.box((-xo - 0.4, Yp - 0.9, z - 0.45), (xo + 0.4, Yp, z + 0.45), c("bois_fonce"), name="Solive")
        nfen = int((XC - 15.0) // 10) + 1
        xf = [9.0 + 10.0 * k for k in range(nfen)]
        coupes = sorted({-XC, XC} | {s * (x - 5.0) for s in (-1, 1) for x in xf})
        _enduit_coupes(b, coupes, Yp + 1.5, Y1 - 0.45, -ZG, ZG, rng, name="Corps_de_garde")
        if v == 2:
            for s in (-1, 1):            # le corps de garde passe aussi sur les pylônes, sous les tourelles
                xa, xb = sorted((s * xo, s * XP))
                b.box((xa + 0.3 * (s < 0), Yp + 1.5, -ZG), (xb - 0.3 * (s > 0), Yp + 16.0, ZG), vr("blanc_creme", rng, 0.02),
                      name="Corps_de_garde")
        b.box((-XC - 0.15, Y1 - 1.5, -ZG - 0.15), (XC + 0.15, Y1 - 0.45, ZG + 0.15), c("bois_fonce"), name="Sabliere")
        xs = [s * x for s in (-1, 1) for x in xf]
        _fenetres_x(b, xs, 4.0, Yp + 6.8, Yp + 11.4, -ZG, ZG, barreaux=2)
        yb_ = Yp + 4.8
        for xa, xb in ((-XC + 1.5, -3.3), (3.3, XC - 1.5)):
            for sens in (1, -1):
                _balcon(b, xa, xb, yb_, sens * ZG, 2.4, sens, pas=8.5, h_console=1.6, h=3.0)
        for sens in (1, -1):
            _plaque(b, 0.0, Yp + 1.9, 4.0, 6.0, sens * ZG, sens, texte)
        XU = xo - 4.0
        xu = [x for x in (7.0, 21.0, 35.0, 49.0) if x <= XU - 4.0]
        if v == 0:
            _, _, _, _, ya = _jupe(b, -XC - 3.0, XC + 3.0, -ZG - 3.0, ZG + 3.0, Y1, 3.4, (3.6, 3.6, 4.6, 4.6), "ocre", rng)
            y2 = ya + 6.0
            _enduit(b, -XU, XU, ya, y2 - 0.45, -4.0, 4.0, rng, 5, name="Etage")
            _fenetres_x(b, [s * x for s in (-1, 1) for x in xu], 3.6, ya + 1.5, ya + 4.8, -4.0, 4.0, barreaux=2)
            b.box((-XU - 0.15, y2 - 1.3, -4.15), (XU + 0.15, y2 - 0.45, 4.15), c("bois_fonce"), name="Sabliere")
            r = _irimoya(b, -XU - 3.5, XU + 3.5, -7.0, 7.0, y2, 2.4, 4.8, (2.6, 2.6, 3.2, 3.2), "ocre", rng,
                         ornement="or", h_orn=2.0)
            _chidori(b, 0.0, 6.0, Y1 + 0.7, 4.4, 4.0, ZG + 2.2, "ocre", rng)
            _chidori(b, 0.0, 6.0, Y1 + 0.7, 4.4, -4.0, -ZG - 2.2, "ocre", rng)
        elif v == 1:
            r = _irimoya(b, -XC - 3.8, XC + 3.8, -ZG - 3.6, ZG + 3.6, Y1, 4.2, 7.6, (4.4, 4.4, 6.0, 6.0), "ocre", rng,
                         tri="bleu", faite="bleu_profond", gegyo="or", ornement="or", h_orn=2.2, deb_g=1.0)
            for sens in (1, -1):
                _chidori(b, 0.0, 6.5, Y1 + 0.7, 5.0, 0.0, sens * (ZG + 2.8), "ocre", rng, tri="bleu")
        else:
            r = _irimoya(b, -XC - 3.0, XC + 3.0, -ZG - 3.2, ZG + 3.2, Y1, 3.6, 7.0, (3.8, 3.8, 4.6, 4.6), "ocre", rng,
                         ornement="or", h_orn=2.2)
        # lanternes devant les pylônes, côté faubourg et côté cité, à des consoles laquées sorties de la poutre
        # (rien au-dessus du passage)
        for s in (-1, 1):
            xc = s * (xo + XP) / 2
            for sens in (1, -1):
                za, zb = sorted((sens * (ze + 0.6), sens * (ze + 2.3)))
                b.box((xc - 0.35, Yp + 0.2, za), (xc + 0.35, Yp + 0.8, zb), c("laque_noire"), collide=False,
                      name="Console_lanterne")
                _lampion(b, xc, Yp + 0.2, sens * (ze + 1.6), "lampion_papier", r=1.0, h=2.2, cordon=0.7)

    # --- vantaux ouverts à 90° vers le faubourg, couchés le long du trottoir : le bois sombre reste du côté
    # des maisons de bois, la cité ne voit que du blanc -------------------------------------------------------
    with b.group("Vantaux"):
        Lv = min(24.0, round(xo / 2))
        Hv = Yp - 1.7
        zc = ze + 1.35                  # charnière : devant la base de pierre (ze + 1,2) et l'auvent (ze + 1)
        for s in (-1, 1):
            xa, xb = sorted((s * (xo + 0.45), s * (xo + 1.95)))
            za, zb = zc, zc + Lv
            npl = 4 if Lv > 20 else 3
            cols = [vr(BOIS_PORTE[i % 2], rng, 0.03) for i in range(npl)]
            for i in range(npl):
                b.box((xa, 0.3, za + Lv * i / npl), (xb, Hv + 0.3, za + Lv * (i + 1) / npl), cols[i], name="Vantail_planche")
            for k, y in enumerate((2.0, Hv * 0.34, Hv * 0.66, Hv - 1.5)):
                b.box((xa - 0.15, y - 0.6, za + 0.3), (xb + 0.15, y + 0.6, zb - 0.3), c("fer"), collide=False,
                      name="Vantail_bande")
                if k in (1, 2):
                    nc = int(round(Lv / 3.6))
                    for i in range(nc):
                        z = za + Lv * (i + 0.5) / nc
                        b.box((xa - 0.33, y - 0.38, z - 0.38), (xb + 0.33, y + 0.38, z + 0.38), c("or"), collide=False,
                              name="Vantail_clou")
            b.box((xa - 0.25, 0.5, zb - 0.85), (xb + 0.25, Hv + 0.1, zb - 0.15), c("laque_noire"), collide=False,
                  name="Vantail_montant")
            # gonds de fer entre le poteau de charnière et le vantail
            xg0, xg1 = sorted((s * (xo + 0.3), s * (xo + 2.1)))
            for y in (4.0, Hv * 0.5, Hv - 3.5):
                b.box((xg0, y - 0.45, ze + 0.5), (xg1, y + 0.45, za + 1.6), c("fer"), collide=False, name="Gond")
    n = len(b.parts) - n0
    assert n <= 420, n
    return {"emprise": (2 * mur, epaisseur + 2), "hauteur": _haut(b, n0), "pieces": n,
            "passage_libre": (2 * xo, Yp - 0.9)}


# ---------------------------------------------------------------------------
# 3) Passerelle rouge
# ---------------------------------------------------------------------------

def _tour_passerelle(b, xc, s, Y, rng, toit="ocre", y_auvent=29.0):
    """Tour blanche d'appui de la passerelle, centrée en (xc, 0), emprise 14 × 14 ; s = côté (face intérieure
    vers -s·X, côté tablier). Base de pierre talutée, fût à bandeaux et auvent de tuiles, porte au niveau du
    tablier, salle haute en encorbellement à fenêtres sur les quatre faces, balcon laqué côté extérieur, toit
    irimoya. Renvoie la cote x de la face intérieure de la salle."""
    with b.group("Tour"):
        cols = _pierres(rng, 3)
        for k, (y0, y1, d) in enumerate(((0, 3, 7.0), (3, 5.5, 6.6), (5.5, 8, 6.25))):
            b.box((xc - d, y0, -d), (xc + d, y1, d), cols[k], studs="top", name="Base")
        hf = 6.0
        cb = _blancs(rng, 3)
        for i, (y0, y1) in enumerate(((8, 18), (18, y_auvent), (y_auvent, 44))):
            b.box((xc - hf, y0, -hf), (xc + hf, y1, hf), cb[i], name="Fut")
        b.box((xc - hf - 0.25, 17.65, -hf - 0.25), (xc + hf + 0.25, 18.35, hf + 0.25), c("blanc_ombre"), name="Bandeau")
        # auvent de tuiles sur les quatre faces (jupe sans cœur autour du fût)
        _jupe(b, xc - hf - 1.8, xc + hf + 1.8, -hf - 1.8, hf + 1.8, y_auvent, 1.3, (1.8, 1.8, 1.8, 1.8), "ocre", rng,
              rive=None, coeur=False, name="Auvent")
        _fenetres_x(b, (xc,), 2.4, 21.5, 26.0, -hf, hf, barreaux=1)
        _fenetres_z(b, (0.0,), 2.4, 21.5, 26.0, xc - hf, xc + hf, barreaux=1)
        _meurtrieres_x(b, (xc - 2.5, xc + 2.5), 12.5, 1.2, -hf, hf)
        # porte vers le tablier (traversante : aussi vers le balcon extérieur)
        b.box((xc - hf - 0.1, Y, -1.6), (xc + hf + 0.1, Y + 4.6, 1.6), c("fenetre_bois"), collide=False, name="Porte")
        b.box((xc - hf - 0.25, Y + 4.6, -2.0), (xc + hf + 0.25, Y + 5.1, 2.0), c("laque_rouge"), collide=False,
              name="Linteau")
        # salle haute en léger encorbellement
        ys0, ys1 = 44.0, 53.0
        hx, hz = 7.0, 7.2
        b.wedge_under((xc - hx, ys0 - 1.4, -hz), (xc + hx, ys0 - 0.6, -hf), c("bois_fonce"), down="-z", name="Console")
        b.wedge_under((xc - hx, ys0 - 1.4, hf), (xc + hx, ys0 - 0.6, hz), c("bois_fonce"), down="+z", name="Console")
        b.box((xc - hx, ys0 - 0.6, -hz - 0.1), (xc + hx, ys0, hz + 0.1), c("bois_fonce"), name="Plancher")
        b.box((xc - hx, ys0, -hz), (xc + hx, ys1, hz), vr("blanc", rng, 0.02), name="Salle")
        _fenetres_x(b, (xc - 3.3, xc + 3.3), 3.0, ys0 + 2.0, ys1 - 1.8, -hz, hz, barreaux=1)
        _fenetres_z(b, (-3.3, 3.3), 3.0, ys0 + 2.0, ys1 - 1.8, xc - hx, xc + hx, barreaux=1)
        b.box((xc - hx - 0.12, ys1 - 1.0, -hz - 0.12), (xc + hx + 0.12, ys1 - 0.45, hz + 0.12), c("bois_fonce"),
              name="Sabliere")
        # balcon côté extérieur (le long de Z), laqué rouge
        with b.at((xc + s * hx, 0, 0), yaw=-90 * s):
            _balcon(b, -hz + 0.3, hz - 0.3, ys0, 0.0, 1.8, -1, pas=4.5, h=2.8, h_console=1.4)
        _irimoya(b, xc - 8.8, xc + 8.8, -8.0, 8.0, ys1, 2.2, 4.8, (2.6, 2.6, 2.8, 2.8), toit, rng,
                 ornement="or", h_orn=1.8)
    return xc - s * hx


def passerelle_rouge(b, variant=0, portee=130, hauteur=38, x_libre=46.0):
    """Passerelle laquée rouge au-dessus du couloir (posée en (0, 0, -286), yaw 0), entre deux tours blanches
    centrées en x = ±portee/2 (emprise au sol 14 × 14 ; portee = 130 pour le couloir élargi : tours derrière les
    murs d'allée en |x| 58..72). Tablier dont le dessous est à hauteur - 1,4 ; il est porté aux deux bouts par
    des encorbellements de poutres laquées en gradins (hanegi) qui sortent des tours (|x| ≥ portee/2 - 16, y ≥ 32).
    Poteaux et garde-corps laqués rouges, main courante laque noire, parapet blanc, toit ocre à deux pentes
    (égout hauteur + 6,4, faîtage ≈ hauteur + 11,7) qui bute contre les salles hautes des tours, lanternes
    suspendues sous le tablier (bas ≥ 34). Les deux faces sont identiques ; tout tient dans z ∈ [-8, 8].
    variant 0 : passerelle couverte, un long toit ocre à pignons ; 1 : passerelle ouverte et petit pavillon
    central à toit ocre ; 2 : passerelle couverte, pavillon central surélevé à toit bleu. Budget 330."""
    rng = b.rng
    v = variant % 3
    xt = portee / 2
    Y = float(hauteur)
    n0 = len(b.parts)
    xi = 0.0
    for s in (-1, 1):
        xi = abs(_tour_passerelle(b, s * xt, s, Y, rng))
    xd = xt - 6.0                      # face des fûts : bout du tablier
    with b.group("Hanegi"):
        # encorbellements en gradins : trois rangs de poutres de plus en plus longues sous le tablier
        ext_max = max(3.0, xd - x_libre)
        for s in (-1, 1):
            for k in range(4):
                y0 = Y - 1.4 - 1.5 * (4 - k)
                ext = ext_max * (k + 1) / 4
                xa, xb = sorted((s * xd, s * (xd - ext)))
                for sz in (-1, 1):
                    b.box((xa, y0, sz * 3.4 - 0.9), (xb, y0 + 1.5, sz * 3.4 + 0.9),
                          c("laque_rouge") if k % 2 else c("laque_rouge_fonce"), name="Hanegi")
                xa2, xb2 = sorted((s * (xd - ext - 0.1), s * (xd - ext + 0.6)))
                b.box((xa2, y0 + 0.15, -4.5), (xb2, y0 + 1.35, 4.5), c("laque_noire"), collide=False, name="Hanegi_bout")
    with b.group("Tablier"):
        b.box((-xd, Y - 1.4, -4.8), (xd, Y - 0.3, 4.8), c("laque_rouge_fonce"), name="Poutre")
        b.box((-xd, Y - 0.3, -4.8), (xd, Y, 4.8), c("bois"), studs="top", name="Plancher")
        b.box((-xd, Y - 1.0, -4.95), (xd, Y - 0.7, 4.95), c("laque_noire"), collide=False, name="Liseré")
        n_tr = max(4, int(round(2 * xd / 8.0)))
        pas = 2 * xd / n_tr
        xs = [-xd + pas * k for k in range(1, n_tr)]
        couvert = v != 1
        x_pav = 8.0                    # demi-largeur du pavillon central (variante 1)
        y_lin = Y + 5.6                # dessous de la sablière
        for sz in (-1, 1):
            zc = sz * 4.2
            for x in xs:
                yt = y_lin if couvert or abs(x) <= x_pav + 0.5 else Y + 3.4
                b.box((x - 0.4, Y, zc - 0.4), (x + 0.4, yt, zc + 0.4), c("laque_rouge"), name="Poteau")
                if not couvert and abs(x) > x_pav + 0.5:
                    b.box((x - 0.5, yt, zc - 0.5), (x + 0.5, yt + 0.4, zc + 0.5), c("laque_noire"), collide=False,
                          name="Chapeau")
            za, zb = sorted((zc - sz * 0.25, zc + sz * 0.25))
            if v != 1:
                b.box((-xd, Y, za), (xd, Y + 2.2, zb), c("blanc"), name="Parapet")
            else:
                b.box((-xd, Y + 1.0, za + 0.05), (xd, Y + 1.4, zb - 0.05), c("laque_rouge"), collide=False, name="Lisse")
                # balustres laqués à mi-travée (garde-corps ajouré)
                for x in xs[:-1]:
                    b.box((x + pas / 2 - 0.25, Y, zc - 0.25), (x + pas / 2 + 0.25, Y + 2.2, zc + 0.25), c("laque_rouge"),
                          collide=False, name="Balustre")
            b.box((-xd, Y + 2.2, zc - 0.5), (xd, Y + 2.75, zc + 0.5), c("laque_rouge"), collide=False, name="Lisse")
            b.box((-xd, Y + 2.75, zc - 0.55), (xd, Y + 3.15, zc + 0.55), c("laque_noire"), collide=False,
                  name="Main_courante")
            if couvert:
                b.box((-xd, y_lin, zc - 0.6), (xd, y_lin + 0.8, zc + 0.6), c("laque_rouge"), name="Sabliere")
                # consoles sous la sablière, un poteau sur deux
                for x in xs[::2]:
                    za2, zb2 = sorted((zc - sz * 0.4, zc + sz * 1.6))
                    b.wedge_under((x - 0.35, y_lin - 1.2, za2), (x + 0.35, y_lin, zb2), c("laque_rouge"),
                                  down="+z" if sz > 0 else "-z", collide=False, name="Console")
        # lanternes suspendues sous le bord du tablier, en quinconce (bas ≥ 34)
        lx = [x for x in [x + pas / 2 for x in [-xd] + xs][1:-1:2] if abs(x) < xd - ext_max - 1.0]
        for sz in (-1, 1):
            for i, x in enumerate(lx if sz < 0 else [-x for x in lx]):
                _lampion(b, x, Y - 1.4, sz * 4.4, ("lampion_papier", "orange_lampion")[i % 2], r=0.8, h=1.7, cordon=0.5,
                         culot=False)
    with b.group("Toit"):
        y_t = Y + 6.4                  # égout du toit (≥ 44)
        if v in (0, 2):
            b.box((-xi, y_t - 0.45, -7.6), (xi, y_t, 7.6), c("ocre_fonce"), name="Toit_sous")
            for sz in (-1, 1):
                za, zb = sorted((sz * 7.7, sz * 7.1))
                b.box((-xi + 0.1, y_t - 0.2, za), (xi - 0.1, y_t + 0.3, zb), c("ocre_clair"), collide=False, name="Toit_rive")
        if v == 0:
            b.wedge((-xi, y_t, -7.6), (xi, y_t + 5.0, 0), vr("ocre", rng, 0.02), down="-z", studs="top", name="Toit")
            b.wedge((-xi, y_t, 0), (xi, y_t + 5.0, 7.6), vr("ocre", rng, 0.02), down="+z", studs="top", name="Toit")
            b.box((-xi, y_t + 4.3, -0.8), (xi, y_t + 5.7, 0.8), c("ocre_fonce"), studs="top", name="Toit_faite")
            # pignons de lucarne (chidori-hafu) : un au centre, deux aux quarts, sur chaque pente
            for xc_ in ([0.0] + ([-xd / 2, xd / 2] if xd > 40 else [])):
                for sz in (-1, 1):
                    za, zb = sorted((sz * 1.0, sz * 6.0))
                    hw = 5.0 if xc_ == 0 else 3.6
                    hh = 4.4 if xc_ == 0 else 3.3
                    b.wedge((xc_ - hw, y_t + 1.0, za), (xc_, y_t + 1.0 + hh, zb), vr("ocre", rng, 0.02), down="-x",
                            studs="top", name="Toit_pignon")
                    b.wedge((xc_, y_t + 1.0, za), (xc_ + hw, y_t + 1.0 + hh, zb), vr("ocre", rng, 0.02), down="+x",
                            studs="top", name="Toit_pignon")
                    za2, zb2 = sorted((sz * 6.0, sz * 6.15))
                    b.wedge((xc_ - hw + 0.8, y_t + 1.6, za2), (xc_, y_t + 0.5 + hh, zb2), c("blanc"), down="-x",
                            collide=False, name="Pignon")
                    b.wedge((xc_, y_t + 1.6, za2), (xc_ + hw - 0.8, y_t + 0.5 + hh, zb2), c("blanc"), down="+x",
                            collide=False, name="Pignon")
                    if xc_ == 0:
                        za3, zb3 = sorted((sz * 6.15, sz * 6.45))
                        b.box((-0.5, y_t + 2.4, za3), (0.5, y_t + 4.0, zb3), c("or"), collide=False, name="Gegyo")
        elif v == 1:
            # pavillon central ouvert : ses poteaux sont ceux du tablier en |x| ≤ x_pav
            b.box((-x_pav - 0.6, y_lin, -4.8), (x_pav + 0.6, y_lin + 0.8, 4.8), c("laque_rouge"), name="Sabliere")
            _irimoya(b, -x_pav - 2.0, x_pav + 2.0, -7.4, 7.4, y_lin + 0.8, 2.2, 4.2, (2.8, 2.8, 3.2, 3.2), "ocre", rng,
                     ornement="or", h_orn=1.6)
        else:
            for xa, xb in ((-xi, -9.0), (9.0, xi)):
                b.wedge((xa, y_t, -7.6), (xb, y_t + 4.6, 0), vr("ocre", rng, 0.02), down="-z", studs="top", name="Toit")
                b.wedge((xa, y_t, 0), (xb, y_t + 4.6, 7.6), vr("ocre", rng, 0.02), down="+z", studs="top", name="Toit")
                b.box((xa, y_t + 3.95, -0.8), (xb, y_t + 5.3, 0.8), c("ocre_fonce"), studs="top", name="Toit_faite")
            b.box((-8.8, y_t, -5.2), (8.8, y_t + 3.2, 5.2), vr("blanc", rng, 0.02), name="Pavillon")
            _fenetres_x(b, (-4.4, 0.0, 4.4), 2.6, y_t + 0.8, y_t + 2.6, -5.2, 5.2, barreaux=1)
            _irimoya(b, -11.5, 11.5, -8.0, 8.0, y_t + 3.2, 2.2, 4.4, (2.8, 2.8, 3.2, 3.2), "bleu", rng, sous="bleu_profond",
                     rive="bleu_clair", faite="bleu_profond", ornement="or", h_orn=1.8)
    n = len(b.parts) - n0
    assert n <= 330, n
    return {"emprise": (portee + 14, 16), "hauteur": _haut(b, n0), "pieces": n, "dessous_tablier": Y - 1.4}
