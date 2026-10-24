"""Enceintes et portes de la cité blanche (zone 6), style « stud ».

Fortifications blanches d'un château japonais générique : enduit blanc (shikkui) en panneaux de blancs
voisins, base de pierre talutée (ishigaki) en gradins, chaperons de tuiles ocre-orangé à deux pentes (murs
dobei), meurtrières carrées (sama), tours de guet (yagura) à étage en encorbellement, tours-portes (yagura-mon)
à corps de garde, balcons laqués rouges, plaques (gaku) bleu profond cadrées d'or.

Fonctions publiques (chacune `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :

    grande_porte       porte colossale d'entrée (mur de 64, bastions, corps de garde, vantaux ouverts)  ≤ 850
    porte_interieure   tour-porte entre le faubourg et la cité (passage de 72 × 36, mur de 24)        ≤ 420
    passerelle_rouge   passerelle couverte laquée rouge à 38 studs au-dessus du couloir               ≤ 330
    mur_blanc          mur blanc droit à chaperon ocre (allées, enclos, remparts)    ≤ ceil(6 + longueur / 5)
    tour_blanche       tour de guet blanche carrée (remparts et cours)                                ≤ 65
    portail_cour       portail d'enclos posé dans un mur d'allée                                     ≤ 60

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
PIERRES = ("pierre", "pierre_claire", "pierre", "pierre_fonce")
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
            b.box((x0 + retrait_faite, y1 - 0.15, za_), (x1 - retrait_faite, y1 + 0.32, zb_), col(rive), collide=False,
                  name=f"{name}_rive")
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


def _lampion(b, x, y_haut, z, corps="lampion_papier", *, r=0.8, h=1.7, cordon=0.5):
    """Lanterne de papier suspendue (chōchin) : cordon, capuchon, corps lumineux, culot. Renvoie le bas."""
    b.box((x - 0.07, y_haut - cordon, z - 0.07), (x + 0.07, y_haut + 0.05, z + 0.07), col("noir"), collide=False,
          shadow=False, name="Cordon")
    yt = y_haut - cordon
    b.cyl((x, yt - 0.15, z), r * 0.62, 0.3, col("noir"), collide=False, name="Capuchon")
    b.cyl((x, yt - 0.3 - h / 2, z), r, h, col(corps), material="Neon", collide=False, shadow=False, name="Lampion")
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
            xa_, xb_ = sorted((xe, xe + s * 1.3))
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
    hc = (e + deb) * (0.6 if meurtrieres else 0.55)
    with b.group("MurBlanc"):
        n0 = len(b.parts)
        # base de pierre
        if meurtrieres:
            hp = 3.2
            b.box((x0, 0, -e - 0.6), (x1, 1.6, e + 0.6), vr("pierre_fonce", rng, 0.03), studs="top", name="Plinthe")
            b.box((x0, 1.6, -e - 0.3), (x1, hp, e + 0.3), vr("pierre", rng, 0.03), studs="top", name="Plinthe")
        else:
            hp = 1.5 if H <= 10 else 1.8
            b.box((x0, 0, -e - 0.3), (x1, hp, e + 0.3), vr("pierre", rng, 0.03), studs="top", name="Plinthe")
        # bandeau et chaperon
        bande = c("bois_fonce") if v == 1 else c("blanc_ombre")
        b.box((x0, H - 0.5, -e - 0.1), (x1, H, e + 0.1), bande, name="Bandeau")
        _chaperon(b, x0, x1, 0.0, e, H, deb, hc, rng, ep_sous=0.3, fw=0.55 if meurtrieres else 0.45)
        reste = budget - (len(b.parts) - n0)
        # répartition du reste : panneaux d'abord (≤ ~16 de large), puis détails de la variante
        n_pan = max(2, int(math.ceil(L / (14.0 if meurtrieres else 11.0))))
        n_koshi = (2 if reste - n_pan >= 2 + (2 if meurtrieres else 0) else 1) if v == 1 else 0
        n_meur = 0
        if meurtrieres:
            n_meur = max(0, min(int(L // 8), reste - n_pan - n_koshi))
        libre = reste - n_pan - n_koshi - n_meur
        second = meurtrieres and libre >= 1
        if second:
            libre -= 1
        if v != 2:
            n_pan += max(0, min(libre, int(round(L / 8)) - n_pan))
        n_pil = 0
        if v == 2:
            # pilastres aux joints des panneaux (≈ tous les 9), et aux bouts s'il reste de quoi
            while n_pan + 1 < L / 9.5 and libre >= 2:
                n_pan += 1
                libre -= 1
            n_pil = min(libre, n_pan + 1)
        _enduit(b, x0, x1, hp, H - 0.5, -e, e, rng, n_pan)
        w = L / n_pan
        if n_koshi:
            hk = hp + (H - hp) / 3
            b.box((x0 + 0.1, hp, -e - 0.15), (x1 - 0.1, hk, e + 0.15), vr("bois_fonce", rng, 0.03), name="Koshi_ita")
            if n_koshi > 1:
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
        b.box((-hf - 0.2, ym - 0.3, -hf - 0.2), (hf + 0.2, ym + 0.3, hf + 0.2), c("blanc_ombre"), name="Bandeau")
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
                     ornement="ocre_brun", h_orn=1.2, gegyo="or")
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
                     ornement="ocre_brun", h_orn=1.0, gegyo=None)
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

def portail_cour(b, variant=0, largeur=10, hauteur=12, texte=None):
    """Portail d'enclos (yakuimon) posé dans un mur d'allée : la façade regarde -Z (l'allée), le mur passe en
    z = 0 (épaisseur 2,4, sommet 10, chaperon ≈ 11,7) et s'arrête en x = ±7. Emprise |x| ≤ 7, z ∈ [-4, 3,5].
    Ouverture libre `largeur` × 8,5 ; vantaux entrouverts vers l'intérieur (+Z) ; petit toit ocre à deux pentes
    (faîtage le long de X) qui domine le chaperon ; plaque `texte` en façade (aucune si None) ; deux lanternes.
    variant 0 : bois sombre ; 1 : poteaux et linteau laqués rouges ; 2 : piles d'enduit blanc ; 3 : bois sombre
    et noren bleu dans l'ouverture. Budget 60."""
    rng = b.rng
    v = variant % 4
    W = largeur / 2                       # demi-ouverture
    X = 7.0
    Y_l = 9.0                             # dessous du linteau
    Y_t = hauteur - 0.6                   # dessus de la sous-face du toit
    Y_s = Y_t - 0.35                      # dessous de la sous-face
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
                xi, xe = sorted((s * (W - 0.05), s * (X - 0.1)))
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
        ht = hauteur + 1.5 - 0.5 - Y_t
        b.wedge((-X, Y_t, zt0), (X, Y_t + ht, zm), vr("ocre", rng, 0.02), down="-z", studs="top", name="Toit")
        b.wedge((-X, Y_t, zm), (X, Y_t + ht, zt1), vr("ocre", rng, 0.02), down="+z", studs="top", name="Toit")
        pente = ht / (zm - zt0)
        b.box((-X + 0.1, Y_t + ht - 0.5 * pente - 0.25, zm - 0.5), (X - 0.1, hauteur + 1.5, zm + 0.5), c("ocre_fonce"),
              studs="top", name="Toit_faite")
        for zr, s in ((zt0, -1), (zt1, 1)):
            za, zb = sorted((zr + s * 0.1, zr - s * 0.5))
            b.box((-X + 0.1, Y_t - 0.15, za), (X - 0.1, Y_t + 0.3, zb), c("ocre_clair"), collide=False, name="Toit_rive")
        for s in (-1, 1):
            xa, xb = sorted((s * (X - 0.1), s * (X - 1.0)))
            b.box((xa, hauteur + 0.6, zm - 0.7), (xb, hauteur + 2.0, zm + 0.7), c("ocre_brun"), collide=False,
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
        # noren bleu (variante 3) : au-dessus de 7 studs
        if v == 3:
            lw = (2 * W - 0.3) / 3
            for i in range(3):
                xa = -W + 0.15 + i * lw
                b.box((xa + 0.06, 7.0, -0.95), (xa + lw - 0.06, Y_l, -0.85), c("noren_bleu"), collide=False, name="Noren")
        if texte:
            _plaque(b, 0.0, Y_l - 0.1, 1.8, 1.8, z_pl, -1, texte, ep=0.2)
        lc = "orange_lampion" if v == 1 else "lampion_papier"
        for s in (-1, 1):
            _lampion(b, s * (W - 0.6), Y_s, -3.0, lc, r=0.55, h=1.2, cordon=0.6)
        n = len(b.parts) - n0
        assert n <= 60, n
    return {"emprise": (2 * X, 7.5), "hauteur": hauteur + 2.0}


# ---------------------------------------------------------------------------
# 1) Grande porte
# ---------------------------------------------------------------------------

def _vantail(b, charniere, ouv, s, L, H, ep, rng, *, y0=0.3, bandes=(0.04, 0.25, 0.48, 0.71, 0.93),
             clous=(0, 1, 2, 3, 4), n_clous=8, guichet=True, name="Vantail"):
    """Vantail géant ouvert de `ouv` degrés vers +Z, côté s (charnière en x = s·|x|, z) : planches verticales
    de bois sombres, bandes de fer et rangées de clous dorés traversantes (visibles sur les deux faces),
    montants de fer aux deux bords, guichet (kuguri-do) à hauteur de joueur."""
    th = math.radians(ouv)
    d = np.array([-s * math.cos(th), 0.0, math.sin(th)])          # de la charnière vers le bord libre
    a = math.degrees(math.atan2(-d[2], d[0]))
    R = rot_y(a)
    O = np.array([charniere[0], 0.0, charniere[1]])

    def bloc(u0, u1, v0, v1, w, couleur, nom, **kw):
        ctr = O + R @ np.array([(u0 + u1) / 2, 0.0, 0.0])
        ctr[1] = (v0 + v1) / 2
        return b.part("block", (u1 - u0, v1 - v0, w), ctr, R, col(couleur), name=nom, **kw)

    n_pl = 4
    for i in range(n_pl):
        bloc(L * i / n_pl, L * (i + 1) / n_pl, y0, y0 + H, ep, vr(BOIS_PORTE[i], rng, 0.03), f"{name}_planche")
    for k, f in enumerate(bandes):
        vb = y0 + H * f
        bloc(0.3, L - 0.3, vb - 0.7, vb + 0.7, ep + 0.3, "fer", f"{name}_bande", collide=False)
        if k in clous:
            for i in range(n_clous):
                u = L * (i + 0.5) / n_clous
                if guichet and k == 0 and abs(u - L * 0.62) < 2.8:
                    continue
                bloc(u - 0.5, u + 0.5, vb - 0.5, vb + 0.5, ep + 0.8, OR_VIEUX if i % 2 else "or",
                     f"{name}_clou", collide=False)
    for u0, u1 in ((0.15, 0.95), (L - 0.95, L - 0.15)):
        bloc(u0, u1, y0 + 0.2, y0 + H - 0.2, ep + 0.2, "laque_noire", f"{name}_montant", collide=False)
    if guichet:
        ug = L * 0.62
        vg0 = y0 + H * bandes[0] + 0.9
        bloc(ug - 2.3, ug + 2.3, vg0, vg0 + 7.0, ep + 0.36, "fer", f"{name}_guichet_cadre", collide=False)
        bloc(ug - 1.8, ug + 1.8, vg0 + 0.4, vg0 + 6.6, ep + 0.46, "laque_noire", f"{name}_guichet", collide=False)
        bloc(ug + 1.0, ug + 1.5, vg0 + 3.0, vg0 + 3.6, ep + 0.7, "or", f"{name}_guichet_poignee", collide=False)
    return O + d * L


def _tour_angle(b, xc, rng, *, toit="ocre", y_corps=69.0):
    """Tour d'angle (sumi-yagura) de la grande porte, centrée en (xc, 0) : base talutée, corps 16 × 17 qui
    monte au-dessus du chaperon du grand mur (y_corps), auvent à quatre pans, salle haute à fenêtres, toit
    irimoya ocre (ou croupe bleue). Renvoie le haut."""
    with b.group("TourAngle"):
        for k, (y0, y1, dx, dz) in enumerate(((0, 3.5, 9.6, 10.2), (3.5, 7, 9.0, 9.6), (7, 10, 8.4, 9.0))):
            cols = _pierres(rng, 2)
            b.box((xc - dx, y0, -dz), (xc, y1, dz), cols[0], studs="top", name="Base")
            b.box((xc, y0, -dz), (xc + dx, y1, dz), cols[1], studs="top", name="Base")
        hx, hz = 8.0, 8.5
        ym = 40.0
        cb = _blancs(rng, 4)
        b.box((xc - hx, 10, -hz), (xc, ym, hz), cb[0], name="Corps")
        b.box((xc, 10, -hz), (xc + hx, ym, hz), cb[1], name="Corps")
        b.box((xc - hx, ym, -hz), (xc, y_corps, hz), cb[2], name="Corps")
        b.box((xc, ym, -hz), (xc + hx, y_corps, hz), cb[3], name="Corps")
        b.box((xc - hx - 0.25, ym - 0.4, -hz - 0.25), (xc + hx + 0.25, ym + 0.4, hz + 0.25), c("blanc_ombre"), name="Bandeau")
        b.box((xc - hx - 0.15, y_corps - 1.2, -hz - 0.15), (xc + hx + 0.15, y_corps, hz + 0.15), c("bois_fonce"),
              name="Bandeau_haut")
        _meurtrieres_x(b, (xc - 4, xc + 4), y_corps - 11, 1.5, -hz, hz)
        _meurtrieres_x(b, (xc,), 24, 1.5, -hz, hz)
        for zc in (-4, 4):
            b.box((xc - hx - 0.1, y_corps - 11, zc - 0.75), (xc + hx + 0.1, y_corps - 9.5, zc + 0.75), c("fenetre"),
                  collide=False, name="Meurtriere")
        # auvent (hisashi), salle haute, toit
        _, _, _, _, ya = _jupe(b, xc - 10.2, xc + 10.2, -10.7, 10.7, y_corps, 1.8, (2.6, 2.6, 2.6, 2.6), toit, rng,
                               sous="ocre_fonce" if toit == "ocre" else "bleu_profond",
                               rive="ocre_clair" if toit == "ocre" else "bleu_clair")
        ys1 = ya + 4.8
        b.box((xc - 6.5, ya, -7.0), (xc + 6.5, ys1, 7.0), vr("blanc", rng, 0.02), name="Salle")
        _fenetres_x(b, (xc - 3, xc + 3), 2.6, ya + 1.0, ys1 - 1.0, -7.0, 7.0, barreaux=1)
        _fenetres_z(b, (-3, 3), 2.6, ya + 1.0, ys1 - 1.0, xc - 6.5, xc + 6.5, barreaux=1)
        b.box((xc - 6.65, ys1 - 0.9, -7.15), (xc + 6.65, ys1 - 0.45, 7.15), c("bois_fonce"), name="Sabliere")
        if toit == "ocre":
            r = _irimoya(b, xc - 8.6, xc + 8.6, -9.1, 9.1, ys1, 2.0, 4.0, (2.7, 2.7, 2.7, 2.7), "ocre", rng,
                         ornement="or", h_orn=1.6)
            return r["top"]
        return _croupe(b, xc - 8.6, xc + 8.6, -9.1, 9.1, ys1, 6.0, "bleu", rng, niveaux=3, sous="bleu_profond",
                       rive="bleu_clair", faite="bleu_profond", epi="or")


def grande_porte(b, variant=0, ouverture=76, hauteur=64, mur=150, epaisseur=16):
    """Grande porte d'entrée (posée en (0, 0, 0), yaw 0 ; face d'arrivée = +Z, esplanade) : mur d'enceinte
    blanc de `hauteur` sur base de pierre talutée, chaperon ocre, meurtrières ; ouverture |x| < 38 libre
    jusqu'à y = 50 sur toute l'épaisseur ; bastions blancs (|x| 43,5..62) en saillie ; corps de garde (yagura)
    au-dessus, à balcons laqués rouges et fenêtres sombres sur les deux faces, plaque 門 (et 静 au revers) ;
    vantaux géants ouverts à 110° vers l'extérieur ; tours d'angle en x = ±mur.
    variant 0 : toit du corps de garde à deux étages ; 1 : un seul grand toit, balcon et poteaux rouges, tours
    d'angle à toit bleu ; 2 : bastions plus lourds en gradins, toit à trois étages. Budget 850."""
    rng = b.rng
    v = variant % 3
    xo = ouverture / 2              # 38 : bord de l'ouverture
    ze = epaisseur / 2              # 8 : faces du mur
    H = float(hauteur)              # 64
    M = float(mur)                  # 150
    XB = xo + 24.0                  # 62 : flanc extérieur des bastions
    XJ = xo + 5.5                   # 43,5 : nez des bastions (logement des vantaux devant)
    ZAV, ZAR = ze + 4.0, -(ze + 1.4)   # 12 / -9,4 : faces avant / arrière des bastions
    YP = 50.0                       # dessous du linteau
    XT = M - 8.0                    # 142 : flanc des tours d'angle
    ZF, ZR = ze + 3.5, -ze          # 11,5 / -8 : faces du corps de garde
    Y1 = 72.0 if v == 1 else 70.0   # égout du premier toit
    n0 = len(b.parts)

    # --- grand mur, de part et d'autre --------------------------------------------------------------
    with b.group("Mur"):
        for s in (-1, 1):
            xa, xb = sorted((s * XB, s * XT))
            _plinthe(b, xa, xb, -ze, ze, [(0, 3, 2.0), (3, 6, 1.2), (6, 8, 0.5)], rng, nseg=3)
            ys = 36.0
            _enduit(b, xa, xb, 8, ys, -ze, ze, rng, 7)
            _enduit(b, xa, xb, ys, H - 1.2, -ze, ze, rng, 6)
            b.box((xa, ys - 0.4, -ze - 0.25), (xb, ys + 0.4, ze + 0.25), c("blanc_ombre"), name="Bandeau")
            b.box((xa, H - 1.2, -ze - 0.15), (xb, H, ze + 0.15), c("bois_fonce"), name="Bandeau_haut")
            _meurtrieres_x(b, _repartis(xa, xb, 10), H - 8.5, 1.5, -ze, ze)
            _meurtrieres_x(b, _repartis(xa, xb, 20), 21.0, 1.5, -ze, ze)
            _chaperon(b, xa, xb, 0.0, ze, H, 1.5, 3.6, rng, ep_sous=0.5, fw=0.8, rive="ocre_clair", retrait_faite=0.0)

    # --- tours d'angle ----------------------------------------------------------------------------------
    for s in (-1, 1):
        _tour_angle(b, s * M, rng, toit="bleu" if v == 1 else "ocre")

    # --- bastions, tableaux de l'ouverture, poteaux de charnière ----------------------------------------
    with b.group("Bastions"):
        if v == 2:
            marches = [(0, 5, 2.0, 0.6, 0.6), (5, 10, 1.5, 0.45, 0.45), (10, 15, 1.0, 0.3, 0.3), (15, 20, 0.5, 0.15, 0.15)]
        else:
            marches = [(0, 5, 2.0, 0.6, 0.5), (5, 10, 1.3, 0.4, 0.3), (10, 14, 0.6, 0.2, 0.1)]
        yb = marches[-1][1]
        for s in (-1, 1):
            for k, (y0, y1, dav, dar, dsi) in enumerate(marches):
                xa, xb = sorted((s * (XJ - dsi), s * XB))
                xm = s * (XJ + (XB - XJ) * (0.45 if k % 2 else 0.6))
                cols = _pierres(rng, 2)
                b.box((xa, y0, ZAR - dar), (xm, y1, ZAV + dav), cols[0], studs="top", name="Ishigaki")
                b.box((xm, y0, ZAR - dar), (xb, y1, ZAV + dav), cols[1], studs="top", name="Ishigaki")
            # corps du bastion : deux colonnes × deux assises, bandeau
            x0, x1 = sorted((s * XJ, s * XB))
            xm = (x0 + x1) / 2
            yc = (yb + YP) / 2
            cb = _blancs(rng, 4)
            for i, (xa, xb) in enumerate(((x0, xm), (xm, x1))):
                b.box((xa, yb, ZAR), (xb, yc, ZAV), cb[i], name="Bastion")
                b.box((xa, yc, ZAR), (xb, YP, ZAV), cb[2 + i], name="Bastion")
            xa, xb = sorted((s * (XJ - 0.2), s * (XB + 0.2)))
            b.box((xa, yc - 0.4, ZAR - 0.25), (xb, yc + 0.4, ZAV + 0.25), c("blanc_ombre"), name="Bandeau")
            if v == 2:
                b.box((xa, yb + 6.6, ZAR - 0.2), (xb, yb + 7.2, ZAV + 0.2), c("blanc_ombre"), name="Bandeau")
            xw = (s * (XJ + 4.6), s * (XB - 4.6))
            _fenetres_x(b, xw, 3.2, YP - 9.5, YP - 4.5, ZAR, ZAV, barreaux=2)
            _meurtrieres_x(b, xw, yc - 7.0, 1.5, ZAR, ZAV)
            # tableau (jambage) entre l'ouverture et le bastion : base de pierre, enduit
            xa, xb = sorted((s * xo, s * XJ))
            b.box((xa, 0, ZAR - 0.2), (xb, 4.0, ze + 0.2), vr("pierre_fonce", rng, 0.03), studs="top", name="Ishigaki")
            xa, xb = sorted((s * (xo + 0.5), s * XJ))
            _enduit_z(b, ZAR, ze, 4.0, 27.0, xa, xb, rng, 2, name="Tableau")
            _enduit_z(b, ZAR, ze, 27.0, YP, xa, xb, rng, 2, name="Tableau")
            # poteaux de charnière (avant laqué noir, arrière bois sombre) et ferrures
            xa, xb = sorted((s * xo, s * (xo + 2.6)))
            b.box((xa, 0, ze - 1.4), (xb, YP, ze + 1.4), c("laque_noire"), name="Poteau_porte")
            for yf in (6.0, 42.0):
                b.box((xa, yf, ze + 1.4), (xb, yf + 2.4, ze + 1.75), c("fer"), collide=False, name="Ferrure")
            xa, xb = sorted((s * xo, s * (xo + 2.4)))
            b.box((xa, 0, ZAR - 0.6), (xb, YP, ZAR + 1.2), c("bois_fonce"), name="Poteau_porte")

    # --- corps de garde ---------------------------------------------------------------------------------
    with b.group("CorpsDeGarde"):
        # poutre sombre continue (plafond du passage, y = 50) devant bastions et ouverture
        b.box((-XB - 0.2, YP, ZAR - 0.3), (XB + 0.2, YP + 1.5, ZAV + 0.3), c("laque_noire"), name="Poutre")
        y_s = YP + 1.5
        _enduit(b, -XB, XB, y_s, Y1 - 0.45, ZR, ZF, rng, 12, name="Corps_de_garde")
        b.box((-XB - 0.15, Y1 - 1.6, ZR - 0.15), (XB + 0.15, Y1 - 0.45, ZF + 0.15), c("bois_fonce"), name="Sabliere")
        xs = [s * x for s in (-1, 1) for x in (9.5, 19.5, 29.5, 39.5, 49.5)]
        _fenetres_x(b, xs, 5.0, 59.0, 65.4, ZR, ZF, barreaux=2)
        _fenetres_z(b, (1.75,), 4.0, 59.0, 65.4, -XB, XB, barreaux=2)
        if v == 1:
            # poteaux laqués rouges entre les fenêtres (traversants : deux faces)
            for x in [s * x for s in (-1, 1) for x in (4.6, 14.5, 24.5, 34.5, 44.5, 54.5)]:
                b.box((x - 0.55, y_s + 3.0, ZR - 0.3), (x + 0.55, Y1 - 1.6, ZF + 0.3), c("laque_rouge"), name="Poteau")
        # balcons laqués : avant (consoles) et arrière, coupés au milieu par la plaque
        yb_ = YP + 5.5
        rouge = "laque_rouge"
        for xa, xb in ((-XB + 2, -3.9), (3.9, XB - 2)):
            _balcon(b, xa, xb, yb_, ZF, 3.5, 1, rouge=rouge, pas=5.0 if v == 1 else 7.0,
                    plancher="laque_rouge" if v == 1 else "laque_rouge_fonce")
            _balcon(b, xa, xb, yb_, ZR, 2.0, -1, rouge=rouge, pas=7.0, consoles=False)
        _plaque(b, 0.0, YP + 2.2, 6.0, 9.0, ZF, 1, "門")
        if v != 1:
            _plaque(b, 0.0, YP + 2.2, 5.0, 7.5, ZR, -1, "静")
        # lanternes suspendues sous la poutre, devant les bastions
        for s in (-1, 1):
            for z in (ZAV + 1.6, ZAR - 1.4):
                _lampion(b, s * (XJ + (XB - XJ) / 2), YP, z, "lampion_papier", r=1.3, h=2.8, cordon=0.8)
        # toits
        if v == 0:
            x0, x1, z0, z1, ya = _jupe(b, -XB - 3.5, XB + 3.5, ZR - 2.8, ZF + 3.5, Y1, 4.2, (4.3, 5.5, 6.0, 6.0), "ocre",
                                       rng)
            y2 = ya + 9.8
            _enduit(b, -40, 40, ya, y2 - 0.45, -5.5, 8.5, rng, 7, name="Etage")
            _fenetres_x(b, (-27, -9, 9, 27), 4.6, ya + 2.4, ya + 7.0, -5.5, 8.5, barreaux=2)
            b.box((-40.15, y2 - 1.4, -5.65), (40.15, y2 - 0.45, 8.65), c("bois_fonce"), name="Sabliere")
            _irimoya(b, -44, 44, -8.6, 11.6, y2, 3.2, 6.6, (3.0, 3.0, 4.0, 4.0), "ocre", rng, ornement="or", h_orn=2.6)
            _chidori(b, 0.0, 7.5, Y1 + 0.8, 6.0, 8.5, ZF + 2.6, "ocre", rng)
            _chidori(b, 0.0, 5.5, Y1 + 0.8, 4.6, -5.5, ZR - 1.9, "ocre", rng)
        elif v == 1:
            _irimoya(b, -XB - 4.5, XB + 4.5, ZR - 3.0, ZF + 4.0, Y1, 5.4, 11.5, (5.6, 6.6, 7.5, 7.5), "ocre", rng,
                     ornement="or", h_orn=3.0, deb_g=1.0)
            _chidori(b, 0.0, 9.0, Y1 + 0.9, 7.6, 4.0, ZF + 3.0, "ocre", rng)
            _chidori(b, 0.0, 7.0, Y1 + 0.9, 6.2, -2.0, ZR - 2.4, "ocre", rng)
        else:
            x0, x1, z0, z1, ya = _jupe(b, -XB - 3.5, XB + 3.5, ZR - 2.8, ZF + 3.5, Y1, 4.2, (4.3, 5.5, 6.0, 6.0), "ocre",
                                       rng)
            y2 = ya + 7.0
            _enduit(b, -44, 44, ya, y2 - 0.45, -5.5, 8.5, rng, 7, name="Etage")
            _fenetres_x(b, (-30, -15, 15, 30), 4.0, ya + 1.6, ya + 5.4, -5.5, 8.5, barreaux=2)
            _chidori(b, 0.0, 7.0, Y1 + 0.8, 5.4, 8.5, ZF + 2.6, "ocre", rng)
            _, _, _, _, yb2 = _jupe(b, -47.5, 47.5, -8.2, 11.2, y2, 3.4, (3.4, 3.4, 4.5, 4.5), "ocre", rng)
            y3 = yb2 + 6.2
            _enduit(b, -26, 26, yb2, y3 - 0.45, -3.6, 6.6, rng, 4, name="Etage")
            _fenetres_x(b, (-14, 0, 14), 3.6, yb2 + 1.4, yb2 + 4.8, -3.6, 6.6, barreaux=2)
            _irimoya(b, -29.5, 29.5, -6.4, 9.4, y3, 2.6, 5.2, (2.6, 2.6, 3.2, 3.2), "ocre", rng, ornement="or", h_orn=2.4)

    # --- vantaux ouverts à 110° vers l'extérieur ---------------------------------------------------------
    with b.group("Vantaux"):
        for s in (-1, 1):
            _vantail(b, (s * (xo + 0.9), ze + 1.6), 110.0, s, 38.0, 49.4, 2.5, rng)
    n = len(b.parts) - n0
    assert n <= 850, n
    return {"emprise": (2 * M + 20, epaisseur + 6), "hauteur": 100.0, "pieces": n}


# ---------------------------------------------------------------------------
# 2) Porte intérieure
# ---------------------------------------------------------------------------

def porte_interieure(b, variant=0, ouverture=72, hauteur_passage=36, mur=150, hauteur_mur=24, epaisseur=10):
    """Tour-porte (yagura-mon) entre le faubourg (+Z) et la cité blanche (-Z), posée en (0, 0, -176), yaw 0 :
    passage |x| < 36 libre jusqu'à y = 36, pylônes blancs sur base de pierre (|x| 36..48, contreforts côté
    cité au-delà de |x| = 44,4), mur intérieur de `hauteur_mur` jusqu'au rempart (x = ±(mur - 1,5)) à chaperon
    ocre et meurtrières, corps de garde blanc (|x| ≤ 50) à fenêtres et balcons laqués rouges sur les deux faces,
    plaques sur les deux faces, vantaux ouverts à 90° vers la cité le long du trottoir (|x| 36..37,5).
    variant 0 : toit à deux étages, 静 ; 1 : un seul toit à faîtage et pignons bleus, 門 ;
    2 : pylônes plus lourds coiffés de tourelles à toit ocre, 静. Budget 420."""
    rng = b.rng
    v = variant % 3
    xo = ouverture / 2              # 36
    Yp = float(hauteur_passage)     # 36
    Hm = float(hauteur_mur)         # 24
    ze = epaisseur / 2              # 5
    XP = xo + (14.0 if v == 2 else 12.0)   # 48 (50) : flanc extérieur des pylônes
    XW = mur - 1.5                  # 148,5 : bout du mur contre le rempart
    n0 = len(b.parts)
    texte = "門" if v == 1 else "静"

    # --- mur intérieur ----------------------------------------------------------------------------------
    with b.group("Mur"):
        for s in (-1, 1):
            xa, xb = sorted((s * XP, s * XW))
            _plinthe(b, xa, xb, -ze, ze, [(0, 2, 0.9), (2, 4, 0.45)], rng, nseg=3)
            _enduit(b, xa, xb, 4, Hm - 1.0, -ze, ze, rng, 10)
            b.box((xa, 13.6, -ze - 0.2), (xb, 14.2, ze + 0.2), c("blanc_ombre"), name="Bandeau")
            b.box((xa, Hm - 1.0, -ze - 0.12), (xb, Hm, ze + 0.12), c("bois_fonce"), name="Bandeau_haut")
            _meurtrieres_x(b, _repartis(xa, xb, 10), Hm - 5.2, 1.3, -ze, ze)
            _chaperon(b, xa, xb, 0.0, ze, Hm, 0.9, 2.8, rng, ep_sous=0.35, fw=0.6, rive="ocre_clair",
                      retrait_faite=0.0)

    # --- pylônes, contreforts, poteaux de charnière ------------------------------------------------------
    with b.group("Pylones"):
        for s in (-1, 1):
            x0, x1 = sorted((s * (xo + 0.6), s * XP))
            for k, (y0, y1, d) in enumerate(((0, 3, 1.0), (3, 6, 0.5))):
                xa, xb = sorted((s * xo, s * XP))
                cols = _pierres(rng, 1)
                b.box((xa, y0, -ze), (xb, y1, ze + d), cols[0], studs="top", name="Ishigaki")
            xm = (x0 + x1) / 2
            cb = _blancs(rng, 4)
            for i, (xa, xb) in enumerate(((x0, xm), (xm, x1))):
                b.box((xa, 6, -ze), (xb, 21, ze), cb[i], name="Pylone")
                b.box((xa, 21, -ze), (xb, Yp, ze), cb[2 + i], name="Pylone")
            xa, xb = sorted((s * (xo + 0.4), s * (XP + 0.2)))
            b.box((xa, 20.6, -ze - 0.25), (xb, 21.4, ze + 0.25), c("blanc_ombre"), name="Bandeau")
            _fenetres_x(b, (xm,), 3.0, 26.0, 30.5, -ze, ze, barreaux=2)
            _meurtrieres_x(b, (xm,), 12.0, 1.4, -ze, ze)
            # contrefort côté cité (au-delà de la face arrière des murs d'allée, |x| > 44,4)
            xa, xb = sorted((s * 44.5, s * XP))
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
                # tourelle sur le pylône
                ya = Yp + 1.5
                b.box((x0 + 0.5, ya, -ze + 0.3), (x1 - 0.5, ya + 9.0, ze - 0.3), vr("blanc", rng, 0.02), name="Tourelle")
                _fenetres_x(b, (xm,), 3.4, ya + 3.0, ya + 7.0, -ze + 0.3, ze - 0.3, barreaux=2)
                b.box((x0 + 0.35, ya + 8.0, -ze + 0.15), (x1 - 0.35, ya + 8.6, ze - 0.15), c("bois_fonce"),
                      name="Sabliere")
                _irimoya(b, x0 - 1.0, x1 + 1.0, -ze - 1.8, ze + 1.8, ya + 9.0, 2.2, 3.8, (2.4, 2.4, 2.6, 2.6), "ocre", rng,
                         ornement="or", h_orn=1.4, gegyo=None)

    # --- corps de garde ---------------------------------------------------------------------------------
    with b.group("CorpsDeGarde"):
        XG = 36.0 if v == 2 else 50.0
        Y1 = Yp + (15.0 if v == 1 else 14.0)
        ZG = ze + 0.5
        b.box((-XG - 0.2, Yp, -ze - 0.6), (XG + 0.2, Yp + 1.5, ze + 0.6), c("laque_noire"), name="Poutre")
        _enduit(b, -XG, XG, Yp + 1.5, Y1 - 0.45, -ZG, ZG, rng, 8 if v != 2 else 6, name="Corps_de_garde")
        b.box((-XG - 0.15, Y1 - 1.5, -ZG - 0.15), (XG + 0.15, Y1 - 0.45, ZG + 0.15), c("bois_fonce"), name="Sabliere")
        xs = [s * x for s in (-1, 1) for x in ((9.0, 19.0, 29.0, 39.0) if v != 2 else (9.0, 19.0, 28.5))]
        _fenetres_x(b, xs, 4.0, Yp + 6.8, Yp + 11.4, -ZG, ZG, barreaux=2)
        yb_ = Yp + 4.8
        for xa, xb in ((-XG + 1.5, -3.3), (3.3, XG - 1.5)):
            for sens in (1, -1):
                _balcon(b, xa, xb, yb_, sens * ZG, 2.4, sens, pas=8.5, h_console=1.6, h=3.0)
        for sens in (1, -1):
            _plaque(b, 0.0, Yp + 1.9, 4.0, 6.0, sens * ZG, sens, texte)
        if v == 0:
            _, _, _, _, ya = _jupe(b, -XG - 3.0, XG + 3.0, -ZG - 3.0, ZG + 3.0, Y1, 3.2, (3.6, 3.6, 4.6, 4.6), "ocre", rng)
            y2 = ya + 6.0
            _enduit(b, -32, 32, ya, y2 - 0.45, -4.0, 4.0, rng, 5, name="Etage")
            _fenetres_x(b, (-21, -7, 7, 21), 3.6, ya + 1.5, ya + 4.8, -4.0, 4.0, barreaux=2)
            b.box((-32.15, y2 - 1.3, -4.15), (32.15, y2 - 0.45, 4.15), c("bois_fonce"), name="Sabliere")
            _irimoya(b, -35.5, 35.5, -7.0, 7.0, y2, 2.4, 4.8, (2.6, 2.6, 3.2, 3.2), "ocre", rng, ornement="or", h_orn=2.0)
        elif v == 1:
            _irimoya(b, -XG - 3.8, XG + 3.8, -ZG - 3.6, ZG + 3.6, Y1, 4.2, 7.6, (4.4, 4.4, 6.0, 6.0), "ocre", rng,
                     tri="bleu", faite="bleu_profond", gegyo="or", ornement="or", h_orn=2.2, deb_g=1.0)
        else:
            _irimoya(b, -XG - 3.0, XG + 3.0, -ZG - 3.2, ZG + 3.2, Y1, 3.6, 7.0, (3.8, 3.8, 4.6, 4.6), "ocre", rng,
                     ornement="or", h_orn=2.2)
        # lanternes suspendues sous la poutre, côté faubourg et côté cité
        for s in (-1, 1):
            for z in (ze + 1.4, -ze - 1.4):
                _lampion(b, s * 26.0, Yp, z, "lampion_papier", r=1.0, h=2.2, cordon=0.7)

    # --- vantaux ouverts à 90° vers la cité, le long du trottoir ------------------------------------------
    with b.group("Vantaux"):
        for s in (-1, 1):
            xa, xb = sorted((s * (xo + 0.05), s * (xo + 1.55)))
            za, zb = -ze - 0.6 - 18.0, -ze - 0.6
            cols = [vr(BOIS_PORTE[i % 2], rng, 0.03) for i in range(3)]
            for i in range(3):
                b.box((xa, 0.3, za + 6 * i), (xb, 34.3, za + 6 * (i + 1)), cols[i], name="Vantail_planche")
            for k, y in enumerate((2.0, 11.5, 22.5, 32.0)):
                b.box((xa - 0.15, y - 0.6, za + 0.3), (xb + 0.15, y + 0.6, zb - 0.3), c("fer"), collide=False,
                      name="Vantail_bande")
                if k in (1, 2):
                    for i in range(5):
                        z = za + 18.0 * (i + 0.5) / 5
                        b.box((xa - 0.35, y - 0.38, z - 0.38), (xb + 0.35, y + 0.38, z + 0.38), c("or"), collide=False,
                              name="Vantail_clou")
            b.box((xa - 0.1, 0.5, za + 0.15), (xb + 0.1, 34.1, za + 0.85), c("laque_noire"), collide=False,
                  name="Vantail_montant")
    n = len(b.parts) - n0
    assert n <= 420, n
    return {"emprise": (2 * mur, epaisseur + 2), "hauteur": 68.0, "pieces": n}


# ---------------------------------------------------------------------------
# 3) Passerelle rouge
# ---------------------------------------------------------------------------

def _tour_passerelle(b, xc, s, Y, rng, toit="ocre"):
    """Tour blanche d'appui de la passerelle, centrée en (xc, 0), emprise 14 × 14 ; s = côté (face intérieure
    vers -s·X, côté tablier). Base talutée, fût à deux bandeaux, porte au niveau du tablier, salle haute à
    fenêtres, balcon côté extérieur, toit irimoya. Renvoie la cote x de la face intérieure de la salle."""
    with b.group("Tour"):
        cols = _pierres(rng, 3)
        for k, (y0, y1, d) in enumerate(((0, 3, 7.0), (3, 5.5, 6.6), (5.5, 8, 6.25))):
            b.box((xc - d, y0, -d), (xc + d, y1, d), cols[k], studs="top", name="Base")
        hf = 6.0
        cb = _blancs(rng, 3)
        for i, (y0, y1) in enumerate(((8, 20), (20, 32), (32, 44))):
            b.box((xc - hf, y0, -hf), (xc + hf, y1, hf), cb[i], name="Fut")
        for yb in (20.0, 32.0):
            b.box((xc - hf - 0.25, yb - 0.35, -hf - 0.25), (xc + hf + 0.25, yb + 0.35, hf + 0.25), c("blanc_ombre"),
                  name="Bandeau")
        _fenetres_x(b, (xc,), 2.4, 24.0, 28.5, -hf, hf, barreaux=1)
        _fenetres_z(b, (0.0,), 2.4, 24.0, 28.5, xc - hf, xc + hf, barreaux=1)
        _meurtrieres_x(b, (xc - 2.5, xc + 2.5), 13.0, 1.2, -hf, hf)
        # porte vers le tablier (traversante : aussi vers le balcon extérieur)
        b.box((xc - hf - 0.1, Y, -1.6), (xc + hf + 0.1, Y + 4.6, 1.6), c("fenetre_bois"), collide=False, name="Porte")
        b.box((xc - hf - 0.25, Y + 4.6, -2.0), (xc + hf + 0.25, Y + 5.1, 2.0), c("laque_rouge"), collide=False,
              name="Linteau")
        # salle haute en léger encorbellement
        ys0, ys1 = 44.0, 51.5
        hx, hz = 6.8, 7.0
        b.box((xc - hx - 0.1, ys0 - 0.6, -hz - 0.1), (xc + hx + 0.1, ys0, hz + 0.1), c("bois_fonce"), name="Plancher")
        b.box((xc - hx, ys0, -hz), (xc + hx, ys1, hz), vr("blanc", rng, 0.02), name="Salle")
        _fenetres_x(b, (xc - 3.2, xc + 3.2), 2.8, ys0 + 1.8, ys1 - 1.6, -hz, hz, barreaux=1)
        _fenetres_z(b, (-3.2, 3.2), 2.8, ys0 + 1.8, ys1 - 1.6, xc - hx, xc + hx, barreaux=1)
        b.box((xc - hx - 0.12, ys1 - 1.0, -hz - 0.12), (xc + hx + 0.12, ys1 - 0.45, hz + 0.12), c("bois_fonce"),
              name="Sabliere")
        # balcon côté extérieur (le long de Z), laqué rouge
        with b.at((xc + s * hx, 0, 0), yaw=-90 * s):
            _balcon(b, -hz + 0.3, hz - 0.3, ys0, 0.0, 1.8, -1, pas=4.5, h=2.8, h_console=1.4)
        _irimoya(b, xc - 8.6, xc + 8.6, -8.0, 8.0, ys1, 2.4, 4.6, (2.8, 2.8, 2.8, 2.8), toit, rng,
                 ornement="or", h_orn=1.8)
    return xc - s * hx


def passerelle_rouge(b, variant=0, portee=104, hauteur=38):
    """Passerelle laquée rouge au-dessus du couloir (posée en (0, 0, -286), yaw 0), entre deux tours blanches
    centrées en x = ±portee/2 (emprise au sol 14 × 14) : tablier dont le dessous est à 36,6, poteaux et
    garde-corps laqués rouges, main courante laque noire, parapet blanc, toit ocre à deux pentes (égout 44,
    faîtage ≈ 49) qui vient buter contre les salles hautes des tours, lanternes suspendues sous le tablier
    (bas ≥ 33). Les deux faces sont identiques ; tout tient dans z ∈ [-8, 8].
    variant 0 : passerelle couverte, un long toit ocre ; 1 : passerelle ouverte et petit pavillon central à toit
    ocre ; 2 : passerelle couverte, pavillon central surélevé à toit bleu. Budget 330."""
    rng = b.rng
    v = variant % 3
    xt = portee / 2
    Y = float(hauteur)
    n0 = len(b.parts)
    xi = 0.0
    for s in (-1, 1):
        xi = abs(_tour_passerelle(b, s * xt, s, Y, rng))
    xd = xt - 6.0                      # face des fûts : bout du tablier
    with b.group("Tablier"):
        b.box((-xd, Y - 1.4, -4.8), (xd, Y - 0.3, 4.8), c("laque_rouge_fonce"), name="Poutre")
        b.box((-xd, Y - 0.3, -4.4), (xd, Y, 4.4), c("bois"), studs="top", name="Plancher")
        b.box((-xd, Y - 1.0, -4.95), (xd, Y - 0.7, 4.95), c("laque_noire"), collide=False, name="Liseré")
        xs = [-40.0 + 8.0 * i for i in range(11)]
        couvert = v != 1
        y_lin = Y + 5.6                # dessous de la sablière
        for sz in (-1, 1):
            zc = sz * 4.2
            for x in xs:
                yt = y_lin if couvert or abs(x) <= 8 else Y + 3.4
                b.box((x - 0.4, Y, zc - 0.4), (x + 0.4, yt, zc + 0.4), c("laque_rouge"), name="Poteau")
                b.box((x - 0.5, Y, zc - 0.5), (x + 0.5, Y + 0.6, zc + 0.5), c("laque_noire"), collide=False, name="Pied")
                if not couvert and abs(x) > 8:
                    b.box((x - 0.5, yt, zc - 0.5), (x + 0.5, yt + 0.4, zc + 0.5), c("laque_noire"), collide=False,
                          name="Chapeau")
            za, zb = sorted((zc - sz * 0.25, zc + sz * 0.25))
            if v != 1:
                b.box((-xd, Y, za), (xd, Y + 2.2, zb), c("blanc"), name="Parapet")
            else:
                b.box((-xd, Y + 1.0, za + 0.05), (xd, Y + 1.4, zb - 0.05), c("laque_rouge"), collide=False, name="Lisse")
                # balustres laqués entre les poteaux (garde-corps ajouré)
                for x in xs[:-1]:
                    b.box((x + 3.75, Y, zc - 0.25), (x + 4.25, Y + 2.2, zc + 0.25), c("laque_rouge"), collide=False,
                          name="Balustre")
            b.box((-xd, Y + 2.2, zc - 0.5), (xd, Y + 2.75, zc + 0.5), c("laque_rouge"), collide=False, name="Lisse")
            b.box((-xd, Y + 2.75, zc - 0.55), (xd, Y + 3.15, zc + 0.55), c("laque_noire"), collide=False,
                  name="Main_courante")
            if couvert:
                b.box((-xd, y_lin, zc - 0.6), (xd, y_lin + 0.8, zc + 0.6), c("laque_rouge"), name="Sabliere")
                # consoles sous la sablière
                for x in xs:
                    za2, zb2 = sorted((zc - sz * 0.4, zc + sz * 1.6))
                    b.wedge_under((x - 0.35, y_lin - 1.2, za2), (x + 0.35, y_lin, zb2), c("laque_rouge"),
                                  down="+z" if sz > 0 else "-z", collide=False, name="Console")
        # lanternes suspendues sous le bord du tablier (bas ≥ 33)
        for sz in (-1, 1):
            for i, x in enumerate((-36.0, -20.0, -4.0, 12.0, 28.0) if sz < 0 else (-28.0, -12.0, 4.0, 20.0, 36.0)):
                _lampion(b, x, Y - 1.4, sz * 4.4, ("lampion_papier", "orange_lampion")[i % 2], r=0.8, h=1.7, cordon=0.5)
    with b.group("Toit"):
        y_t = Y + 6.4                  # égout du toit (≥ 44)
        if v == 0:
            b.box((-xi, y_t - 0.45, -7.6), (xi, y_t, 7.6), c("ocre_fonce"), name="Toit_sous")
            b.wedge((-xi, y_t, -7.6), (xi, y_t + 4.6, 0), vr("ocre", rng, 0.02), down="-z", studs="top", name="Toit")
            b.wedge((-xi, y_t, 0), (xi, y_t + 4.6, 7.6), vr("ocre", rng, 0.02), down="+z", studs="top", name="Toit")
            b.box((-xi, y_t + 3.95, -0.8), (xi, y_t + 5.3, 0.8), c("ocre_fonce"), studs="top", name="Toit_faite")
            for sz in (-1, 1):
                za, zb = sorted((sz * 7.7, sz * 7.1))
                b.box((-xi + 0.1, y_t - 0.2, za), (xi - 0.1, y_t + 0.3, zb), c("ocre_clair"), collide=False, name="Toit_rive")
            # petit pignon central (chidori-hafu) sur chaque pente
            for sz in (-1, 1):
                za, zb = sorted((sz * 1.0, sz * 6.0))
                b.wedge((-5.0, y_t + 1.0, za), (0.0, y_t + 5.4, zb), vr("ocre", rng, 0.02), down="-x", studs="top",
                        name="Toit_pignon")
                b.wedge((0.0, y_t + 1.0, za), (5.0, y_t + 5.4, zb), vr("ocre", rng, 0.02), down="+x", studs="top",
                        name="Toit_pignon")
                za2, zb2 = sorted((sz * 6.0, sz * 6.15))
                b.wedge((-4.2, y_t + 1.6, za2), (0.0, y_t + 4.9, zb2), c("blanc"), down="-x", collide=False,
                        name="Pignon")
                b.wedge((0.0, y_t + 1.6, za2), (4.2, y_t + 4.9, zb2), c("blanc"), down="+x", collide=False,
                        name="Pignon")
                za3, zb3 = sorted((sz * 6.15, sz * 6.45))
                b.box((-0.5, y_t + 2.4, za3), (0.5, y_t + 4.0, zb3), c("or"), collide=False, name="Gegyo")
        elif v == 1:
            # pavillon central ouvert : ses poteaux sont ceux du tablier en |x| ≤ 8
            b.box((-8.6, y_lin, -4.8), (8.6, y_lin + 0.8, 4.8), c("laque_rouge"), name="Sabliere")
            _irimoya(b, -10.0, 10.0, -7.4, 7.4, y_lin + 0.8, 2.2, 4.2, (2.8, 2.8, 3.2, 3.2), "ocre", rng, ornement="or",
                     h_orn=1.6)
        else:
            b.box((-xi, y_t - 0.45, -7.6), (xi, y_t, 7.6), c("ocre_fonce"), name="Toit_sous")
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
    return {"emprise": (portee + 14, 16), "hauteur": 62.0, "pieces": n}
