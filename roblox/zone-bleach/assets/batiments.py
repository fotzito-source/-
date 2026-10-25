"""Bâtiments de la zone 6 (la cité blanche aux toits ocre), style « stud ».

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :
- maison_bois(largeur=20, profondeur=16, simple=False) : maison de marchand d'Edo à étage du FAUBOURG (bois
    sombre, torchis, tuiles grises), 18-24 de haut ; v0 thé 茶 (auvent profond, comptoir en retrait),
    v1 auberge 宿 (long balcon, sudare), v2 riz 米 (treillis koshi, ailes udatsu), v3 pignon sur rue et balcon
    (蕎麦), v4 confiserie 甘味 / 団子 (banc rouge), v5 bains 湯 (cheminée, toit irimoya). simple=True : seconde
    rangée (murs, toit, fenêtres, un balcon ; ni texte ni intérieur), ≤ 70 pièces ;
- echoppe() : échoppe de ruelle 8 × 5 (≤ 9 de haut) ; v0 poisson (bâche bleue), v1 légumes (ocre),
    v2 étoffes 呉服 (rouge), v3 poteries (indigo), v4 douceurs 団子 (blanche) ;
- tour_guet_bois(hauteur=28) : tour de guet à incendie (hinomi-yagura) 7 × 7 ; v0 plateforme et toit,
    v1 deux plateformes, v2 échelle haute et cloche seule (croix de Saint-André sur trois baies, deux pour v1) ;
- maison_blanche(largeur=24, profondeur=18, simple=False) : bâtiment de la CITÉ BLANCHE (enduit blanc en
    panneaux, poteaux sombres, socle de pierre, toits de tuiles ocre-orangé), 14-26 de haut ; v0 hall à
    véranda et toit irimoya à fronton, v1 deux étages et deux rangs de toits ocre, v2 hall à pignon sur l'allée
    et toit bleu, v3 entrepôt blanc (kura), v4 deux étages et balcon laqué rouge ;
- caserne(longueur=40, profondeur=14, simple=False) : long bâtiment blanc (14-18 de haut) ; v0 véranda,
    v1 deux niveaux à petites fenêtres, v2 porche central à pignon, v3 toit bleu ;
- pavillon() : pavillon de la cour des œufs 12 × 12 (≤ 14) ; v0 irimoya à six piliers, v1 toit en pavillon
    (hōgyō) à épi doré, v2 deux toits superposés ;
- quartier_lointain(largeur=56, profondeur=48) : îlot de la ville lointaine (≤ 32 pièces), six plans.

Repère (voir CONVENTIONS.md) : origine au centre de l'emprise au sol, y = 0 au sol, l'AVANT regarde -Z.
`largeur` (ou `longueur`) est le long de X, `profondeur` le long de Z. Les sous-ensembles « de façade » se
dessinent dans un repère où la façade est le plan z = 0 et l'extérieur est vers -z ; on les pose avec
`b.at(...)` (yaw = -90 : façade droite +X ; yaw = 90 : façade gauche -X ; yaw = 180 : arrière).

Débords (règles de la mise en page) : maisons de bois, avant ≤ 3 au-dessus de y = 7 (auvent, balcon,
enseignes, lanternes) et ≤ 1 au sol (marche, noren, banc), arrière ≤ 1, côtés ≤ 1 (toit) ; bâtiments de la
cité, toits ≤ 2 hors emprise. Uniquement des éléments japonais génériques ; textes permis seulement
(茶 宿 米 湯 薬 団子 蕎麦 甘味 呉服 豆腐 本 花 桜 門 静 白).

Couloir élargi (|x| < 45, rien au-dessus de |x| < 46 sous y = 30) : tout est paramétrique et tient dans son
emprise ; posés avec les façades du faubourg en |x| = 55, les échoppes en 57,6 et les façades de la cité en
65,4 (mur d'allée 55-57,4 + cour de 8), aucun élément ne descend sous |x| = 52 (débord avant de 3 des maisons
de bois, au-dessus de y = 7).

Murs blancs « vivants » : façades en travées (`_travees`), revers et arrières en panneaux de blancs voisins
entre poteaux sombres (`_revers`), pignons en panneaux (`_cotes_blancs(z_mur=...)`) ; aucun aplat blanc de plus
de ~16 studs, y compris vu d'avion ou en biais depuis l'allée.
"""

from __future__ import annotations

import math

import numpy as np

from kit import hexrgb, mix, rot_x, rot_y, rot_z, shade
from palette import blanc_pixel, c, vary

# ---------------------------------------------------------------------------
# Couleurs locales (en plus de la palette)
# ---------------------------------------------------------------------------
INTERIEUR = "#2B201A"      # fond sombre d'une boutique, d'une entrée
FER = "#3A3F44"            # ferrures, barreaux
BAMBOU_SEC = "#4E3B2A"     # inuyarai (barrière de bambou courbe au pied des façades)
FEUTRE = "#C8332B"         # tissu rouge des bancs (hi-mōsen)
DANGO = ("#F4A7B9", "#FAF3E3", "#9CCB6B")   # rose, blanc, vert tendre
AUBERGINE = "#5B3A6B"
POISSON = "#AEB7C0"


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


def _style(table, variant, alt=None):
    """Variante de base `variant % len(table)` ; au-delà, on décale quelques couleurs pour varier la rue."""
    S = dict(table[variant % len(table)])
    k = variant // len(table)
    if k and alt:
        for key, choix in alt.items():
            if key in S:
                S[key] = choix[(variant + k) % len(choix)]
    return S


# ---------------------------------------------------------------------------
# Pièces orientées
# ---------------------------------------------------------------------------


def _poutre(b, p0, p1, larg, ep, couleur, normale=(0.0, 0.0, -1.0), name="Poutre", **kw):
    """Bloc tendu de p0 à p1 (son Y local suit le segment) ; `normale` fixe l'orientation de sa face
    (épaisseur `ep` le long de la normale, `larg` dans le plan)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = float(np.linalg.norm(d))
    y = d / L
    n = np.asarray(normale, float)
    z = n - y * float(n @ y)
    z /= np.linalg.norm(z)
    x = np.cross(y, z)
    return b.part("block", (larg, L, ep), (p0 + p1) / 2, np.column_stack([x, y, z]), col(couleur), name=name, **kw)


def _pan_z(b, za, ya, zb, yb, x0, x1, ep, couleur, *, ext_a=0.0, ext_b=0.0, studs="top", name="Pan", **kw):
    """Dalle inclinée dans le plan YZ : sa face supérieure passe par (za, ya) et (zb, yb), épaisseur `ep`
    sous cette ligne, étendue sur x0..x1 ; `ext_a` / `ext_b` l'allongent côté a / côté b."""
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
    sous cette ligne, étendue sur z0..z1."""
    dx, dy = xb - xa, yb - ya
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    s = (ext_b - ext_a) / 2
    cx = (xa + xb) / 2 + ux * s - nx * ep / 2
    cy = (ya + yb) / 2 + uy * s - ny * ep / 2
    return b.part("block", (L + ext_a + ext_b, ep, z1 - z0), (cx, cy, (z0 + z1) / 2), rot_z(math.degrees(math.atan2(dy, dx))),
                  col(couleur), studs=studs, name=name, **kw)


# ---------------------------------------------------------------------------
# Toits
# ---------------------------------------------------------------------------

TUILES_GRISES = dict(rive="tuile_grise_fonce", faitage="tuile_grise_fonce", oni="tuile_grise_fonce",
                     verge="tuile_grise_claire")
TUILES_OCRE = dict(rive="ocre_fonce", faitage="ocre_fonce", oni="ocre_brun", verge="ocre_clair")
TUILES_BLEUES = dict(rive="bleu_profond", faitage="bleu_profond", oni="bleu_profond", verge="bleu_clair")


def _jeu(toit):
    """Couleurs d'accompagnement (rive, faîtage, oni, rives de pignon) d'une couleur de tuiles."""
    if isinstance(toit, str) and toit.startswith("tuile"):
        return TUILES_GRISES
    if isinstance(toit, str) and toit.startswith("bleu"):
        return TUILES_BLEUES
    return TUILES_OCRE


def _toit_hirairi(b, x0, x1, zf, zb, H, pente, toit, pignon, *, deb_av=2.2, deb_ar=0.8, deb_cote=0.6, ep=0.8,
                  sori=0.5, rng=None, oni=True, oni_h=1.55, noshi="blanc", verge=True, pignons=True, fait=1.0,
                  jeu=None):
    """Toit à deux pans, faîtage parallèle à X, sur des murs x0..x1 / zf..zb de hauteur H : triangles de
    pignon (`pignon`), dalles stud qui débordent ; le débord est moins pentu que le pan (`sori`) : courbe creuse
    des toits japonais. Rives (bandeau au bout des débords), faîtage, lit blanc (noshi), oni, planches de rive
    claires sur les pignons (`verge`). Renvoie (haut, f) où f(z) donne le dessous du pan avant en z."""
    J = jeu or _jeu(toit)
    t = col(toit)
    zm = (zf + zb) / 2
    run = zm - zf
    hu = run * pente
    pe = pente * sori
    k = ep * math.hypot(1, pente)
    ke = ep * math.hypot(1, pe)
    xa, xb = x0 - deb_cote, x1 + deb_cote
    tv = (lambda: vr(t, rng, 0.025)) if rng is not None else (lambda: t)
    if pignons:
        m = col(pignon) if rng is None else vr(pignon, rng, 0.02)
        b.wedge((x0, H, zf), (x1, H + hu + 0.3, zm), m, down="-z", name="Pignon")
        b.wedge((x0, H, zm), (x1, H + hu + 0.3, zb), m, down="+z", name="Pignon")
    _pan_z(b, zf, H + k, zm, H + hu + k, xa, xb, ep, tv(), ext_a=0.25, ext_b=0.5)
    _pan_z(b, zm, H + hu + k, zb, H + k, xa, xb, ep, tv(), ext_a=0.5, ext_b=0.25)
    if deb_av > 0:
        _pan_z(b, zf - deb_av, H - deb_av * pe + ke, zf, H + ke, xa - 0.1, xb + 0.1, ep, tv(), ext_b=0.15, name="Debord")
    if deb_ar > 0:
        _pan_z(b, zb, H + ke, zb + deb_ar, H - deb_ar * pe + ke, xa - 0.1, xb + 0.1, ep, tv(), ext_a=0.15, name="Debord")
    rc = col(J["rive"])
    for zt, s_, d_ in ((zf - deb_av, -1, deb_av), (zb + deb_ar, 1, deb_ar)):
        if d_ <= 0:
            continue
        yt = H - d_ * pe + ke
        b.box((xa, yt - 0.8, min(zt - 0.06 * s_, zt + 0.2 * s_)), (xb, yt + 0.1, max(zt - 0.06 * s_, zt + 0.2 * s_)), rc,
              name="Rive")
    yr = H + hu + k
    if verge:
        vc = col(J["verge"])
        for xe in (xa, xb):
            xv0, xv1 = (xe - 0.12, xe + 0.4) if xe == xa else (xe - 0.4, xe + 0.12)
            _pan_z(b, zf, H + k + 0.15, zm, yr + 0.15, xv0, xv1, ep + 0.3, vc, ext_a=0.1, ext_b=0.4, studs="none",
                   name="Verge", collide=False)
            _pan_z(b, zm, yr + 0.15, zb, H + k + 0.15, xv0 + 0.03, xv1 - 0.03, ep + 0.3, vc, ext_a=0.4, ext_b=0.1,
                   studs="none", name="Verge", collide=False)
    rd = 0.95 * fait
    yb_f = yr - rd * pente - 0.25
    b.box((xa - 0.15, yb_f, zm - rd), (xb + 0.15, yr + 0.75 * fait, zm + rd), col(J["faitage"]), studs="top",
          name="Faitage")
    if noshi:
        yn = yr - (rd + 0.1) * pente - 0.12
        b.box((xa, yn, zm - rd - 0.1), (xb, yn + 0.4 * fait, zm + rd + 0.1), col(noshi), name="Noshi")
    top = yr + 0.75 * fait
    if oni:
        for xe, s_ in ((xa - 0.2, 1), (xb + 0.2, -1)):
            xo0, xo1 = sorted((xe, xe + s_ * 1.3 * fait))
            b.box((xo0, yb_f - 0.1, zm - rd - 0.2), (xo1, yr + oni_h * fait, zm + rd + 0.2), col(J["oni"]), name="Oni")
        top = yr + oni_h * fait

    def dessous(z):
        if z >= zf:
            return H + (z - zf) * pente
        return H - (zf - z) * pe

    return top, dessous


def _toit_tsumairi(b, x0, x1, zf, zb, H, pente, toit, pignon, *, deb=0.8, deb_av=1.6, deb_ar=0.6, ep=0.8, sori=0.5,
                   hafu=None, gegyo="or", rng=None, treillis=None, pignon_z=None, oni=True, jeu=None):
    """Toit à deux pans dont le PIGNON regarde l'avant (faîtage parallèle à Z) : triangle (`pignon`), dalles
    stud avec débord adouci, planches de rive (hafu) en façade, faîtage, oni, gegyo ; `treillis` = couleur
    d'un treillis kitsune-goshi dans le triangle avant. `pignon_z` = (z0, z1) de la partie pleine du comble.
    Renvoie le haut du faîtage."""
    J = jeu or _jeu(toit)
    t = col(toit)
    xm = (x0 + x1) / 2
    run = xm - x0
    hu = run * pente
    pe = pente * sori
    k = ep * math.hypot(1, pente)
    ke = ep * math.hypot(1, pe)
    za, zb_ = zf - deb_av, zb + deb_ar
    tv = (lambda: vr(t, rng, 0.025)) if rng is not None else (lambda: t)
    pz0, pz1 = pignon_z or (zf, zb)
    m = col(pignon) if rng is None else vr(pignon, rng, 0.02)
    b.wedge((x0, H, pz0), (xm, H + hu + 0.3, pz1), m, down="-x", name="Pignon")
    b.wedge((xm, H, pz0), (x1, H + hu + 0.3, pz1), m, down="+x", name="Pignon")
    _pan_x(b, x0, H + k, xm, H + hu + k, za, zb_, ep, tv(), ext_a=0.25, ext_b=0.5)
    _pan_x(b, xm, H + hu + k, x1, H + k, za, zb_, ep, tv(), ext_a=0.5, ext_b=0.25)
    if deb > 0:
        _pan_x(b, x0 - deb, H - deb * pe + ke, x0, H + ke, za - 0.1, zb_ + 0.1, ep, tv(), ext_b=0.15, name="Debord")
        _pan_x(b, x1, H + ke, x1 + deb, H - deb * pe + ke, za - 0.1, zb_ + 0.1, ep, tv(), ext_a=0.15, name="Debord")
    yr = H + hu + k
    hc = col(hafu) if hafu else col(J["verge"])
    z0h, z1h = za - 0.35, za + 0.3
    # les deux planches se rejoignent au faîte sans se croiser (pas de « cornes » au-dessus du pignon)
    segs = [(x0, H + k + 0.15, xm, yr + 0.15, 0.25, 0.05), (xm, yr + 0.15, x1, H + k + 0.15, 0.05, 0.25)]
    if deb > 0.3:
        segs += [(x0 - deb + 0.2, H - (deb - 0.2) * pe + ke + 0.15, x0, H + ke + 0.15, 0.0, 0.2),
                 (x1, H + ke + 0.15, x1 + deb - 0.2, H - (deb - 0.2) * pe + ke + 0.15, 0.2, 0.0)]
    for i, (xa_, ya_, xb_, yb_, ea, eb) in enumerate(segs):
        dz = 0.05 * (i % 2)
        _pan_x(b, xa_, ya_, xb_, yb_, z0h - dz, z1h - dz, ep + 0.3, hc, ext_a=ea, ext_b=eb, studs="none", name="Hafu")
    b.box((xm - 0.95, yr - 0.6, za - 0.5), (xm + 0.95, yr + 0.55, zb_ + 0.15), col(J["faitage"]), studs="top",
          name="Faitage")
    top = yr + 0.55
    if oni:
        b.box((xm - 1.1, yr - 0.7, za - 0.72), (xm + 1.1, yr + 0.8, za + 0.4), col(J["oni"]), name="Oni")
        top = yr + 0.8
    if gegyo:
        b.box((xm - 0.7, yr - 2.4, z0h - 0.25), (xm + 0.7, yr - 0.2, z0h + 0.3), hc, name="Gegyo")
        b.box((xm - 0.4, yr - 2.1, z0h - 0.4), (xm + 0.4, yr - 1.0, z0h - 0.2), col(gegyo), name="Gegyo")
    if treillis is not None:
        tc = col(treillis)
        zt0, zt1 = pz0 - 0.25, pz0 + 0.05
        for i in range(-2, 3):
            xx = xm + i * run / 3.2
            hh = hu * (1 - abs(xx - xm) / run) - 0.25
            if hh > 0.6:
                b.box((xx - 0.13, H + 0.1, zt0), (xx + 0.13, H + hh, zt1), tc, collide=False, name="Treillis")
        yy = H + hu * 0.42
        half = run * 0.58 - 0.2
        b.box((xm - half, yy - 0.13, zt0 + 0.07), (xm + half, yy + 0.13, zt1 - 0.04), tc, collide=False, name="Treillis")
    return top


def _toit_irimoya(b, x0, x1, z0, z1, y, toit, *, a_z0, a_z1, a_x0, a_x1, h1, h2, tri="blanc", deb_g=0.7,
                  bordure=0.5, rng=None, gegyo=None, oni=True, oni_h=1.6, verge=True, jeu=None, faitage_l=0.95):
    """Toit irimoya (croupe + pignon) en coins pleins, faîtage parallèle à X. (x0..x1, z0..z1) = bord de
    l'avant-toit, posé au niveau y (dessous plat). Jupe à quatre pans (profondeurs a_*, hauteur h1) ; au-dessus,
    les pans z0 / z1 continuent plus raides (h2) jusqu'au faîtage ; sur les bouts x0 / x1, triangles de pignon
    (`tri`) en retrait, bordés de planches de rive claires (`verge`). Renvoie un dict de cotes."""
    J = jeu or _jeu(toit)
    t = col(toit)
    tv = (lambda: vr(t, rng, 0.025)) if rng is not None else (lambda: t)
    xi0, xi1, zi0, zi1 = x0 + a_x0, x1 - a_x1, z0 + a_z0, z1 - a_z1
    zm = (zi0 + zi1) / 2
    b.box((x0, y - 0.5, z0), (x1, y, z1), col(J["rive"]), name="Rive")
    b.wedge((x0, y, z0), (x1, y + h1, zi0), tv(), down="-z", studs="top", name="Jupe")
    b.wedge((x0, y, zi1), (x1, y + h1, z1), tv(), down="+z", studs="top", name="Jupe")
    b.wedge((x0, y, zi0), (xi0, y + h1, zi1), tv(), down="-x", studs="top", name="Jupe")
    b.wedge((xi1, y, zi0), (x1, y + h1, zi1), tv(), down="+x", studs="top", name="Jupe")
    b.box((xi0, y, zi0), (xi1, y + h1, zi1), shade(t, 0.8), name="Coeur")
    ya = y + h1
    xg0, xg1 = xi0 - deb_g, xi1 + deb_g
    b.wedge((xg0, ya, zi0), (xg1, ya + h2, zm), tv(), down="-z", studs="top", name="Pan")
    b.wedge((xg0, ya, zm), (xg1, ya + h2, zi1), tv(), down="+z", studs="top", name="Pan")
    run = zm - zi0
    pente = h2 / run
    d = bordure
    zs = zi0 + (0.35 + d) / pente
    for xe, s in ((xg0, -1), (xg1, 1)):
        cc = col(tri) if rng is None else vr(tri, rng, 0.02)
        xa_, xb_ = sorted((xe, xe + 0.15 * s))
        b.wedge((xa_, ya + 0.35, zs), (xb_, ya + h2 - d, zm), cc, down="-z", name="Pignon")
        b.wedge((xa_, ya + 0.35, zm), (xb_, ya + h2 - d, 2 * zm - zs), cc, down="+z", name="Pignon")
        if verge:
            vc = col(J["verge"])
            xv0, xv1 = sorted((xe + 0.3 * s, xe - 0.2 * s))
            _pan_z(b, zi0, ya + 0.12, zm, ya + h2 + 0.12, xv0, xv1, 0.75, vc, ext_a=0.0, ext_b=0.35, studs="none",
                   name="Verge", collide=False)
            _pan_z(b, zm, ya + h2 + 0.12, zi1, ya + 0.12, xv0 + 0.03, xv1 - 0.03, 0.75, vc, ext_a=0.35, ext_b=0.0,
                   studs="none", name="Verge", collide=False)
        if gegyo:
            ga, gb = sorted((xe + 0.15 * s, xe + 0.45 * s))
            b.box((ga, ya + h2 - 2.2, zm - 0.5), (gb, ya + h2 - 0.6, zm + 0.5), col(gegyo), name="Gegyo")
    yr = ya + h2
    fl = faitage_l
    b.box((xg0 - 0.3, yr - (fl * pente + 0.35), zm - fl), (xg1 + 0.3, yr + 0.8, zm + fl), col(J["faitage"]),
          studs="top", name="Faitage")
    top = yr + 0.8
    if oni:
        for xe in (xg0 - 0.3, xg1 + 0.3):
            b.box((xe - 0.6, yr - 0.8, zm - fl - 0.2), (xe + 0.6, yr + oni_h, zm + fl + 0.2), col(J["oni"]), name="Oni")
        top = max(top, yr + oni_h)
    return {"top": top, "yr": yr, "xg0": xg0, "xg1": xg1, "zi0": zi0, "zi1": zi1, "zm": zm, "ya": ya, "pente": pente,
            "xi0": xi0, "xi1": xi1}


def _jupe(b, x0, x1, z0, z1, y, h, toit, *, a=2.0, rng=None, jeu=None, studs="top"):
    """Toit-jupe à quatre pans (rang inférieur d'un toit à deux niveaux, mokoshi) : bord de l'avant-toit
    x0..x1 / z0..z1 au niveau y, profondeur `a`, hauteur h ; rive sombre dessous. Le cœur est caché par l'étage."""
    J = jeu or _jeu(toit)
    t = col(toit)
    tv = (lambda: vr(t, rng, 0.025)) if rng is not None else (lambda: t)
    b.box((x0, y - 0.45, z0), (x1, y, z1), col(J["rive"]), name="Rive")
    b.wedge((x0, y, z0), (x1, y + h, z0 + a), tv(), down="-z", studs=studs, name="Jupe")
    b.wedge((x0, y, z1 - a), (x1, y + h, z1), tv(), down="+z", studs=studs, name="Jupe")
    b.wedge((x0, y, z0 + a), (x0 + a, y + h, z1 - a), tv(), down="-x", studs=studs, name="Jupe")
    b.wedge((x1 - a, y, z0 + a), (x1, y + h, z1 - a), tv(), down="+x", studs=studs, name="Jupe")


# ---------------------------------------------------------------------------
# Petits éléments de façade (plan z = 0, extérieur vers -z)
# ---------------------------------------------------------------------------


def _chochin(b, x, y_haut, z, *, r=0.6, h=1.3, corps="lampion_papier", neon=True, cap="noir", corde=0.1):
    """Lanterne de papier (chōchin) suspendue : cordon, chapeau, corps (Neon si allumée), culot.
    Renvoie le bas de la lanterne (y_haut - corde - h - 0,45)."""
    b.box((x - 0.06, y_haut - corde - 0.05, z - 0.06), (x + 0.06, y_haut + 0.1, z + 0.06), col("noir"), collide=False,
          name="Cordon")
    yt = y_haut - corde
    b.cyl((x, yt - 0.12, z), r * 0.6, 0.3, col(cap), axis="y", collide=False, name="Chapeau")
    kw = {"material": "Neon"} if neon else {}
    b.cyl((x, yt - 0.22 - h / 2, z), r, h, col(corps), axis="y", collide=False, shadow=False, name="Chochin", **kw)
    b.cyl((x, yt - 0.22 - h - 0.08, z), r * 0.6, 0.3, col(cap), axis="y", collide=False, name="Culot")
    return yt - 0.22 - h - 0.23


def _noren(b, xa, xb, y_haut, h, z, fond, encre, texte, n=None, font="brush", tringle="bois_fonce"):
    """Rideau noren : tringle + lés séparés, un caractère par lé (texte plus court → centré, lés unis autour).
    Vu de face (depuis -z), +x est à GAUCHE : le premier caractère va sur le lé de plus grand x."""
    n = n or max(3, len(texte))
    chars = list(texte)[:n]
    pad = n - len(chars)
    chars = [""] * (pad // 2) + chars + [""] * (pad - pad // 2)
    gap = 0.16
    lw = (xb - xa - gap * (n - 1)) / n
    b.box((xa - 0.25, y_haut - 0.3, z - 0.2), (xb + 0.25, y_haut, z + 0.2), col(tringle), collide=False, name="Tringle")
    fond = col(fond)
    for i in range(n):
        x = xa + i * (lw + gap)
        p = b.box((x, y_haut - 0.3 - h, z - 0.1), (x + lw, y_haut - 0.3, z + 0.1), fond, collide=False,
                  material="Fabric", name="Noren")
        ch = chars[n - 1 - i]
        if ch.strip():
            p.label = {"face": "Front", "text": ch, "color": col(encre), "font": font}


def _enseigne_v(b, x, y0, h, texte, fond, encre, cadre, *, larg=1.6, sortie=0.4, bras=True, chapeau=None):
    """Enseigne verticale perpendiculaire à la façade (lisible des deux sens de la rue), accrochée par deux
    bras ; `chapeau` = couleur d'un petit toit stud au-dessus."""
    zc = -(sortie + larg / 2)
    z_av, z_ar = zc - larg / 2, zc + larg / 2
    b.box((x - 0.2, y0 - 0.3, z_av - 0.3), (x + 0.2, y0 + h + 0.3, z_ar + 0.3), col(cadre), collide=False, name="Cadre")
    for s, face in ((-1, "Left"), (1, "Right")):
        xa, xb = sorted((x + s * 0.2, x + s * 0.34))
        p = b.box((xa, y0, z_av), (xb, y0 + h, z_ar), col(fond), collide=False, name="Enseigne")
        p.label = {"face": face, "text": texte, "color": col(encre), "font": "brush", "vertical": True}
    if bras:
        for yb in (y0 + 0.3, y0 + h - 0.7):
            b.box((x - 0.12, yb, z_ar + 0.3), (x + 0.12, yb + 0.35, 0.3), col(FER), collide=False, name="Bras")
    if chapeau is not None:
        b.wedge((x - 0.7, y0 + h + 0.3, z_av - 0.5), (x, y0 + h + 0.9, z_ar + 0.4), col(chapeau), down="-x",
                studs="top", collide=False, name="Chapeau")
        b.wedge((x, y0 + h + 0.3, z_av - 0.5), (x + 0.7, y0 + h + 0.9, z_ar + 0.4), col(chapeau), down="+x",
                studs="top", collide=False, name="Chapeau")


def _kanban(b, x, y, w, h, texte, fond, encre, cadre, *, z=0.0, font="brush", ep=0.35):
    """Panneau horizontal (kanban) : cadre sombre et planche à texte devant. Plan avant en z - ep - 0.2."""
    b.box((x - w / 2 - 0.3, y - 0.3, z - ep), (x + w / 2 + 0.3, y + h + 0.3, z + 0.25), col(cadre), name="Cadre")
    p = b.box((x - w / 2, y, z - ep - 0.2), (x + w / 2, y + h, z - ep + 0.05), col(fond), name="Kanban")
    p.label = {"face": "Front", "text": texte, "color": col(encre), "font": font}
    return p


def _koshi(b, xa, xb, y0, y1, bois, fond, *, pas=1.0, neon=False):
    """Treillis de bois (koshi) devant un fond (papier clair ou intérieur sombre) : lisses haute et basse,
    lattes verticales."""
    bois = col(bois)
    kw = {"material": "Neon"} if neon else {}
    b.box((xa, y0 + 0.2, -0.12), (xb, y1 - 0.2, 0.3), col(fond), name="Fond", **kw)
    b.box((xa - 0.1, y0, -0.6), (xb + 0.1, y0 + 0.45, 0.3), bois, studs="top", name="Lisse")
    b.box((xa - 0.1, y1 - 0.45, -0.6), (xb + 0.1, y1, 0.3), bois, name="Lisse")
    n = max(2, int(round((xb - xa) / pas)))
    for i in range(1, n):
        xx = xa + i * (xb - xa) / n
        b.box((xx - 0.16, y0 + 0.45, -0.5), (xx + 0.16, y1 - 0.45, 0.0), bois, collide=False, name="Latte")


def _mushiko(b, x, y, w, h, barreaux, *, n=None, fond=INTERIEUR, appui=None):
    """Fenêtre mushiko-mado : fente sombre barrée de gros barreaux d'enduit, appui et linteau en relief."""
    m = col(barreaux)
    a = col(appui) if appui else shade(m, 0.93)
    b.box((x - w / 2, y, -0.12), (x + w / 2, y + h, 0.3), col(fond), name="Fente")
    n = n or max(3, int(round(w / 0.95)))
    for i in range(1, n):
        xx = x - w / 2 + i * w / n
        b.box((xx - 0.22, y + 0.05, -0.4), (xx + 0.22, y + h - 0.05, 0.0), m, collide=False, name="Barreau")
    b.box((x - w / 2 - 0.4, y - 0.45, -0.45), (x + w / 2 + 0.4, y, 0.3), a, studs="top", name="Appui")
    b.box((x - w / 2 - 0.4, y + h, -0.45), (x + w / 2 + 0.4, y + h + 0.45, 0.3), a, name="Linteau")


def _shoji(b, xa, xb, ya, yb, cadre, *, n=3, lumiere=True, traverse=True, papier="papier"):
    """Baie de shoji : cadre sombre en saillie, papier (Neon chaud si éclairé) un peu en avant du cadre,
    n-1 montants et une traverse (2 + n pièces)."""
    cd = col(cadre)
    kw = {"material": "Neon"} if lumiere else {}
    b.box((xa - 0.35, ya - 0.35, -0.2), (xb + 0.35, yb + 0.35, 0.3), cd, name="Cadre")
    b.box((xa, ya, -0.32), (xb, yb, 0.0), col("fenetre_lumiere" if lumiere else papier), name="Shoji", **kw)
    for i in range(1, n):
        xx = xa + i * (xb - xa) / n
        b.box((xx - 0.12, ya, -0.45), (xx + 0.12, yb, -0.2), cd, collide=False, name="Kumiko")
    if traverse:
        ym = (ya + yb) / 2
        b.box((xa, ym - 0.11, -0.41), (xb, ym + 0.11, -0.2), cd, collide=False, name="Kumiko")


def _fenetre_simple(b, x, y, w, h, cadre, *, lumiere=False, papier="papier"):
    """Petite fenêtre (4 pièces) : papier ou lumière, linteau, appui stud, meneau."""
    cd = col(cadre)
    kw = {"material": "Neon"} if lumiere else {}
    b.box((x - w / 2, y - 0.15, -0.12), (x + w / 2, y + h + 0.15, 0.3), col("fenetre_lumiere" if lumiere else papier),
          name="Shoji", **kw)
    b.box((x - w / 2 - 0.35, y + h, -0.4), (x + w / 2 + 0.35, y + h + 0.4, 0.3), cd, name="Linteau")
    b.box((x - w / 2 - 0.35, y - 0.4, -0.5), (x + w / 2 + 0.35, y, 0.3), cd, studs="top", name="Appui")
    b.box((x - 0.12, y, -0.3), (x + 0.12, y + h, 0.0), cd, collide=False, name="Meneau")


def _fenetre_cite(b, x, y, w, h, cadre="bois_fonce", *, n=3, encadrement="blanc_pur", fond="fenetre"):
    """Fenêtre de la cité blanche (2 + n - 1 pièces) : encadrement d'enduit en relief, ouverture sombre en
    avant, barreaux de bois sombre (treillis vertical)."""
    b.box((x - w / 2 - 0.35, y - 0.4, -0.22), (x + w / 2 + 0.35, y + h + 0.35, 0.05), col(encadrement), collide=False,
          name="Encadrement")
    b.box((x - w / 2, y, -0.34), (x + w / 2, y + h, 0.05), col(fond), name="Fenetre")
    for i in range(1, n):
        xx = x - w / 2 + i * w / n
        b.box((xx - 0.13, y + 0.05, -0.5), (xx + 0.13, y + h - 0.05, -0.2), col(cadre), collide=False, name="Barreau")


def _garde_corps(b, xa, xb, y, z, cadre, *, h=1.8, pas=1.8, plein=None):
    """Garde-corps le long de x (plan z) : lisse haute stud, lisse basse, balustres (ou panneau plein)."""
    cd = col(cadre)
    b.box((xa, y + h - 0.35, z - 0.2), (xb, y + h, z + 0.2), cd, studs="top", name="Lisse")
    if plein is not None:
        b.box((xa + 0.1, y, z - 0.08), (xb - 0.1, y + h - 0.35, z + 0.08), col(plein), name="Panneau")
    else:
        b.box((xa, y + 0.45, z - 0.11), (xb, y + 0.7, z + 0.11), cd, name="Lisse")
    n = max(1, int(round((xb - xa) / pas)))
    for i in range(n + 1):
        xx = xa + 0.22 + i * (xb - xa - 0.44) / n
        b.box((xx - 0.15, y, z - 0.15), (xx + 0.15, y + h - 0.35, z + 0.15), cd, collide=False, name="Balustre")


def _banc_rouge(b, x, z, w, *, d=1.2, h=1.6, rng=None):
    """Banc bas (endai) couvert de feutre rouge (hi-mōsen) ; 4 pièces."""
    for xx in (x - w / 2 + 0.45, x + w / 2 - 0.45):
        b.box((xx - 0.22, 0, z - d / 2 + 0.15), (xx + 0.22, h - 0.3, z + d / 2 - 0.15), col("bois_fonce"), name="Pied")
    b.box((x - w / 2, h - 0.3, z - d / 2), (x + w / 2, h, z + d / 2), col("bois_moyen"), name="Banc")
    b.box((x - w / 2 + 0.2, h, z - d / 2 - 0.1), (x + w / 2 - 0.2, h + 0.15, z + d / 2 + 0.1),
          vr(FEUTRE, rng, 0.03) if rng is not None else col(FEUTRE), material="Fabric", studs="top", name="Feutre")
    return h + 0.15


def _dango(b, x, y, z):
    """Brochette de dango tricolore posée debout (4 pièces)."""
    b.box((x - 0.06, y, z - 0.06), (x + 0.06, y + 2.0, z + 0.06), col("bois_clair"), collide=False, name="Pique")
    for i, cc in enumerate(DANGO[::-1]):
        b.ball((x, y + 0.55 + i * 0.5, z), 0.28, col(cc), collide=False, name="Dango")


def _panneaux(b, xs, ya, yb, rng, *, z0=-0.1, z1=0.05, name="Panneau"):
    """Panneaux d'enduit blanc (`blanc_pixel`) un peu en saillie entre les abscisses `xs` (bornes des baies) :
    le grand mur blanc se lit en « pixels » de blancs voisins."""
    for xa, xb in zip(xs, xs[1:]):
        if xb - xa > 0.4:
            b.box((xa, ya, z0), (xb, yb, z1), blanc_pixel(rng), collide=False, name=name)


# ---------------------------------------------------------------------------
# MAISON DE BOIS DU FAUBOURG
# ---------------------------------------------------------------------------

_MAISONS_BOIS = [
    # 0 : maison de thé 茶 — auvent profond, comptoir ouvert en retrait (jarres, tasses), étage de torchis à mushiko
    dict(toit="tuile_grise", mur="torchis", rdc="bois", cadre="bois_fonce", rez="comptoir", etage="mushiko",
         noren=("noren_indigo", "blanc", "茶"), kanban=("茶", "bois_clair", "bois_fonce"), auvent=2.8, lampions=2,
         porte="droite", forme="hirairi", etal="the", h2=16.0),
    # 1 : auberge 宿 — long balcon à garde-corps, sudare, shoji éclairés ; rez à treillis, entrée centrale
    dict(toit="tuile_grise_fonce", mur="bois", rdc="bois", cadre="bois_fonce", rez="koshi", etage="balcon",
         noren=("noren_bleu", "blanc", "宿"), kanban=None, verticale=("宿", "laque_noire", "blanc"), auvent=2.6,
         lampions=2, porte="centre", forme="hirairi", h2=16.6, sudare=True, garde="bois_moyen"),
    # 2 : marchand de riz 米 — treillis koshi, ailes udatsu, mushiko, ballots de riz à l'entrée
    dict(toit="tuile_grise", mur="torchis", rdc="bois_fonce", cadre="bois_fonce", rez="koshi", etage="mushiko",
         noren=("noren_blanc", "noren_indigo", "米"), kanban=("米", "laque_noire", "blanc"), auvent=2.6, lampions=1,
         porte="gauche", forme="hirairi", udatsu=True, h2=16.0),
    # 3 : maison à pignon sur rue, balcon, planches grises patinées ; soba 蕎麦
    dict(toit="tuile_grise", mur="bois_gris", rdc="bois", cadre="bois_fonce", rez="koshi", etage="balcon",
         noren=("noren_ocre", "bois_fonce", "蕎麦"), kanban=None, verticale=("蕎麦", "bois_clair", "bois_fonce"),
         auvent=2.4, lampions=1, porte="droite", forme="tsumairi", h2=15.6, garde="bois_fonce"),
    # 4 : confiserie 甘味 / 団子 — comptoir de dango en retrait, banc rouge, étage à sudare
    dict(toit="tuile_grise_fonce", mur="torchis", rdc="bois", cadre="bois_fonce", rez="comptoir", etage="sudare",
         noren=("noren_rouge", "blanc", "甘味"), kanban=("団子", "blanc", "laque_rouge"), auvent=2.8, lampions=2,
         porte="gauche", forme="hirairi", etal="dango", banc=True, h2=16.0),
    # 5 : bains 湯 — entrée centrale, treillis, étage à shoji, cheminée, toit irimoya
    dict(toit="tuile_grise", mur="bois", rdc="bois_fonce", cadre="bois_fonce", rez="koshi", etage="shoji",
         noren=("noren_bleu", "blanc", "湯"), kanban=("湯", "bois_clair", "bois_fonce"), auvent=2.6, lampions=2,
         porte="centre", forme="irimoya", cheminee=True, h2=16.0),
]
_ALT_BOIS = {"toit": ["tuile_grise", "tuile_grise_fonce"], "mur": ["torchis", "bois", "bois_gris", "torchis"]}


def maison_bois(b, variant=0, largeur=20, profondeur=16, simple=False):
    """Maison de marchand d'Edo à étage, en bois sombre : socle de pierre, rez ouvert sur la rue (treillis koshi
    ou comptoir en retrait), noren à un seul texte, enseigne kanban au-dessus de l'entrée, auvent stud (hisashi)
    sur consoles, lanternes de papier allumées ; étage à mushiko-mado, balcon à garde-corps et sudare, ou shoji ;
    toit de tuiles grises à deux pans (sur rue ou pignon sur rue) ou irimoya ; ailes udatsu, cheminée.
    `simple=True` : version de seconde rangée (≤ 70 pièces)."""
    if simple:
        return _maison_bois_simple(b, variant, largeur, profondeur)
    rng = b.rng
    S = _style(_MAISONS_BOIS, variant, _ALT_BOIS)
    W, D = float(largeur), float(profondeur)
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    YS, YK, YA, HS = 0.6, 7.2, 10.2, 10.0        # socle, linteau du rez, auvent contre le mur, jonction des niveaux
    H2 = S["h2"]
    PA, EP_A = 0.4, 0.6
    KA = EP_A * math.hypot(1, PA)
    PROF_A = S["auvent"]
    cadre = col(S["cadre"])
    mur, toit = S["mur"], S["toit"]
    J = _jeu(toit)
    RET = 2.0 if S["rez"] == "comptoir" else 0.0   # rez en retrait sous l'étage (porche ombragé)

    def sous_auvent(z):                             # dessous de l'auvent à la profondeur z (repère de façade)
        return YA + z * PA - KA

    # --- baies du rez : porte et boutiques -------------------------------------------------------------
    wd = 5.0 if W >= 20 else 4.4
    if S["porte"] == "droite":
        da, db = x0 + 0.7, x0 + 0.7 + wd
        poteaux = [db + 0.4]
        boutiques = [(db + 0.8, x1 - 0.7)]
    elif S["porte"] == "gauche":
        da, db = x1 - 0.7 - wd, x1 - 0.7
        poteaux = [da - 0.4]
        boutiques = [(x0 + 0.7, da - 0.8)]
    else:
        da, db = -wd / 2, wd / 2
        poteaux = [da - 0.4, db + 0.4]
        boutiques = [(x0 + 0.7, da - 0.8), (db + 0.8, x1 - 0.7)]

    with b.group("Corps"):
        b.box((x0, 0, zf - 0.4), (x1, YS, zb), vr("pierre_fonce", rng, 0.03), studs="top", name="Socle")
        b.box((x0, YS, zf + RET), (x1, HS, zb), vr(S["rdc"], rng, 0.03), name="Mur_rdc")
        b.box((x0, HS, zf), (x1, H2 - 0.8, zb), vr(mur, rng, 0.02), name="Mur_etage")
        if RET:
            b.box((x0 + 0.7, YK + 0.6, zf), (x1 - 0.7, HS, zf + RET), shade(col(S["rdc"]), 0.85), name="Ranma")
        b.box((x0 - 0.15, H2 - 0.8, zf - 0.15), (x1 + 0.15, H2, zb + 0.15), cadre, name="Sabliere")
        b.box((x0 - 0.1, HS - 0.4, zf + 0.1), (x1 + 0.1, HS + 0.25, zb + 0.1), cadre, name="Bandeau")
        for xa in (x0 - 0.1, x1 - 0.7):
            b.box((xa, YS, zf - 0.3), (xa + 0.8, H2 - 0.8, zf + 0.7), cadre, name="Poteau_angle")
            b.box((xa, YS, zb - 0.7), (xa + 0.8, H2 - 0.8, zb + 0.1), cadre, name="Poteau_angle")

    # --- rez-de-chaussée sur rue ------------------------------------------------------------------------
    with b.group("Rez"), b.at((0, 0, zf)):
        zr = RET
        b.box((x0 + 0.7, YK, -0.45), (x1 - 0.7, YK + 0.6, 0.3), cadre, name="Kamoi")
        b.box((da, YS, zr - 0.1), (db, YK, zr + 0.3), col(INTERIEUR), name="Entree")
        b.box((da + 0.4, 0, -1.0), (db - 0.4, 0.4, -0.4), vr("pierre", rng, 0.03), studs="top", name="Marche")
        nf, ne, nt = S["noren"]
        _noren(b, da + 0.2, db - 0.2, YK, 2.9, -0.55, nf, ne, nt, n=3 if len(nt) == 1 else 4)
        for xp in poteaux:
            b.box((xp - 0.4, YS, -0.3), (xp + 0.4, YA - 0.1, 0.4), cadre, name="Poteau")
        for (sa, sb) in boutiques:
            if S["rez"] == "comptoir":
                # fond de boutique : shoji éclairés derrière le comptoir (la boutique luit sous l'auvent)
                b.box((sa, YS, zr - 0.1), (sb, YK, zr + 0.3), col("fenetre_lumiere"), material="Neon", name="Interieur")
                for k in (1, 2):
                    xx = sa + k * (sb - sa) / 3
                    b.box((xx - 0.15, 3.3, zr - 0.25), (xx + 0.15, YK, zr - 0.1), cadre, name="Kumiko")
                b.box((sa + 0.2, YS, zr - 1.1), (sb - 0.2, 3.0, zr - 0.1), vr("bois", rng, 0.03), name="Comptoir")
                b.box((sa, 3.0, zr - 1.3), (sb, 3.4, zr - 0.1), col("bois_clair"), studs="top", name="Plateau")
                b.box((sa, YK - 0.5, zr - 0.6), (sb, YK + 0.6, zr - 0.2), col("sudare"), name="Store")
                _etal_comptoir(b, S.get("etal"), sa, sb, 3.4, zr - 0.7, rng)
            else:
                cuts = [(sa, sb)]
                if sb - sa > 9.5:
                    xm = (sa + sb) / 2
                    b.box((xm - 0.4, YS, -0.3), (xm + 0.4, YK, 0.4), cadre, name="Poteau")
                    cuts = [(sa, xm - 0.4), (xm + 0.4, sb)]
                for (pa, pb) in cuts:
                    if not (S["noren"][2] == "米" and pb > da - 4.5):
                        b.wedge((pa, YS, -0.95), (pb, YS + 1.5, 0.2), col(BAMBOU_SEC), down="-z", name="Inuyarai")
                    _koshi(b, pa, pb, YS + 1.5, YK, cadre, "lampion_papier" if S["porte"] == "centre" else INTERIEUR,
                           pas=1.05)
        if S.get("banc"):
            sa, sb = boutiques[0]
            _banc_rouge(b, (sa + sb) / 2, -0.2, min(6.0, sb - sa - 1.0), d=1.2, rng=rng)
        if S["noren"][2] == "米":
            # ballots de riz (tawara) couchés contre le treillis, à côté de l'entrée (≤ 1 devant la façade)
            xb_ = da - 2.6
            for i, (dx, yy) in enumerate(((-0.8, 1.1), (0.8, 1.1), (0.0, 2.05))):
                b.cyl((xb_ + dx, yy, -0.5), 0.5, 1.5, vr("chaume", rng, 0.05), axis="x", name="Ballot")
        # auvent (hisashi) stud et ses consoles
        ya_av = YA - PROF_A * PA
        _pan_z(b, -PROF_A, ya_av, 0.3, YA + 0.3 * PA, x0 - 0.3, x1 + 0.3, EP_A, vr(toit, rng, 0.02), name="Auvent")
        b.box((x0 - 0.3, ya_av - 0.7, -PROF_A - 0.2), (x1 + 0.3, ya_av + 0.08, -PROF_A + 0.06), col(J["rive"]),
              name="Rive")
        for xc in [x0 + 0.3, x1 - 0.3] + poteaux:
            _pan_z(b, -PROF_A + 0.4, sous_auvent(-PROF_A + 0.4) + 0.15, 0.2, sous_auvent(0.2) + 0.15, xc - 0.22,
                   xc + 0.22, 0.55, cadre, studs="none", name="Console")
        # lanternes de papier allumées de part et d'autre de l'entrée (bas ≥ 7)
        xs_l = [da - 0.2, db + 0.2] if S["lampions"] == 2 else [db + 0.2 if S["porte"] == "droite" else da - 0.2]
        for xl in xs_l:
            _chochin(b, xl, sous_auvent(-1.55), -1.55, r=0.6, h=1.3, corps="lampion_papier", neon=True)

    # --- étage sur rue -----------------------------------------------------------------------------------
    with b.group("Etage"), b.at((0, 0, zf)):
        yw = YA + 1.3
        et = S["etage"]
        kt = S.get("kanban")
        libres = [(x0 + 1.2, x1 - 1.2)]
        if kt:
            # enseigne de toit (yane-kanban) posée sur l'auvent, au-dessus de l'entrée
            t_, f_, e_ = kt
            kw_ = min(wd + 1.6, 7.0)
            xc = min(max((da + db) / 2, x0 + kw_ / 2 + 1.0), x1 - kw_ / 2 - 1.0)
            yk = YA + 0.45
            for xx in (xc - kw_ / 2 + 0.9, xc + kw_ / 2 - 0.9):
                b.box((xx - 0.2, sous_auvent(-1.35) + KA - 0.3, -1.55), (xx + 0.2, yk + 0.3, -1.15), cadre, name="Pied")
            _kanban(b, xc, yk + 0.3, kw_, 2.1, t_, f_, e_, cadre, z=-1.15, ep=0.35)
            b.wedge((xc - kw_ / 2 - 0.6, yk + 2.7, -2.2), (xc + kw_ / 2 + 0.6, yk + 3.4, 0.1), col(toit), down="-z",
                    studs="top", name="Chapeau")
            libres = [(x0 + 1.2, xc - kw_ / 2 - 0.9), (xc + kw_ / 2 + 0.9, x1 - 1.2)]
        if et == "mushiko":
            for (la, lb) in libres:
                if lb - la < 3.2:
                    continue
                n = 2 if lb - la > 11 else 1
                for i in range(n):
                    xx = la + (i + 0.5) * (lb - la) / n
                    wf = min(4.6, (lb - la) / n - 1.4)
                    _mushiko(b, xx, yw, wf, 2.3, "torchis" if mur != "torchis" else "blanc_creme", n=4,
                             appui=S["cadre"] if mur == "torchis" else None)
        elif et == "balcon":
            PB = 2.0
            bw = W - 2.6
            b.box((-bw / 2, YA - 0.05, -PB), (bw / 2, YA + 0.5, 0.3), vr("bois_moyen", rng, 0.03), studs="top",
                  name="Plancher")
            for xx in (-bw / 2 + 1.0, 0.0, bw / 2 - 1.0):
                b.box((xx - 0.25, YA - 0.9, -PB + 0.3), (xx + 0.25, YA - 0.05, 0.2), cadre, name="Console")
            _shoji(b, -bw / 2 + 0.9, bw / 2 - 0.9, YA + 0.85, H2 - 1.5, cadre, n=max(4, int(bw / 3.2)), lumiere=True)
            g = S.get("garde", "bois_moyen")
            _garde_corps(b, -bw / 2, bw / 2, YA + 0.5, -PB + 0.25, g, h=1.7, pas=2.1 if S.get("sudare") else 3.0,
                         plein=None if S.get("sudare") else "bois_gris_clair")
            if S.get("sudare"):
                for xx in (-bw / 3, 0.0, bw / 3):
                    b.box((xx - bw / 7, H2 - 3.1, -PB + 0.45), (xx + bw / 7, H2 - 0.85, -PB + 0.65), col("sudare"),
                          collide=False, name="Sudare")
                    for xc_ in (xx - bw / 7 + 0.4, xx + bw / 7 - 0.4):      # cordons pendus au débord du toit
                        b.box((xc_ - 0.05, H2 - 0.95, -PB + 0.5), (xc_ + 0.05, H2 - 0.15, -PB + 0.6), cadre,
                              collide=False, name="Cordon")
        elif et == "sudare":
            # grande baie de shoji éclairés derrière un store de bambou à demi baissé, petit garde-corps
            bw = W - 4.0
            _shoji(b, -bw / 2, bw / 2, YA + 0.9, H2 - 1.6, cadre, n=5, lumiere=True)
            b.box((-bw / 2 - 0.2, H2 - 1.1, -1.0), (bw / 2 + 0.2, H2 - 0.8, -0.25), cadre, collide=False,
                  name="Latte")
            for k, (xa_, xb_, yb_) in enumerate(((-bw / 2 - 0.2, -0.1, H2 - 3.6), (0.1, bw / 2 + 0.2, H2 - 2.5))):
                b.box((xa_, yb_, -0.8 - 0.1 * k), (xb_, H2 - 1.1, -0.6 - 0.1 * k), col("sudare"), collide=False,
                      name="Sudare")
                b.box(((xa_ + xb_) / 2 - 0.1, yb_ + 0.3, -0.95 - 0.1 * k), ((xa_ + xb_) / 2 + 0.1, H2 - 1.1,
                      -0.78 - 0.1 * k), cadre, collide=False, name="Lien")
            _garde_corps(b, -bw / 2 - 0.3, bw / 2 + 0.3, YA + 0.5, -0.75, cadre, h=1.2, pas=3.2, plein=S["cadre"])
        else:  # shoji : trois fenêtres éclairées
            n = 3
            for i in range(n):
                xx = x0 + 1.2 + (i + 0.5) * (W - 2.4) / n
                ww = (W - 2.4) / n - 2.0
                _shoji(b, xx - ww / 2, xx + ww / 2, yw - 0.2, yw + 2.6, cadre, n=3, lumiere=(i != 1))
            for xx in (x0 + 1.2 + (W - 2.4) / 3, x0 + 1.2 + 2 * (W - 2.4) / 3):
                b.box((xx - 0.35, HS + 0.25, -0.25), (xx + 0.35, H2 - 0.8, 0.2), cadre, name="Poteau")
        if S.get("verticale"):
            vt, vf, ve = S["verticale"]
            xs = x1 - 0.3 if S["porte"] != "gauche" else x0 + 0.3
            _enseigne_v(b, xs, YA + 1.0, 1.7 * len(vt) + 0.5, vt, vf, ve, cadre, larg=1.6, sortie=0.35)
        if S.get("udatsu"):
            # ailes udatsu : murs coupe-feu enduits en saillie sur l'auvent, coiffés d'un petit toit
            for xa in (x0, x1 - 0.9):
                ytop = H2 - 2.0
                y_hi = YA + 0.3 * PA - 0.15
                y_lo = y_hi - 2.2 * PA
                mu = vr("torchis", rng, 0.02)
                b.wedge_under((xa, y_lo - 0.12, -1.9), (xa + 0.9, y_hi, 0.0), mu, down="+z", name="Udatsu")
                b.box((xa, y_hi, -1.9), (xa + 0.9, ytop, 0.0), mu, name="Udatsu")
                b.box((xa - 0.1, ytop - 0.6, -2.0), (xa + 1.0, ytop, 0.0), cadre, name="Udatsu")
                b.wedge((xa - 0.35, ytop, -2.3), (xa + 0.45, ytop + 0.7, 0.3), col(toit), down="-x", studs="top",
                        name="Udatsu_toit")
                b.wedge((xa + 0.45, ytop, -2.3), (xa + 1.25, ytop + 0.7, 0.3), col(toit), down="+x", studs="top",
                        name="Udatsu_toit")

    # --- côtés et arrière ----------------------------------------------------------------------------------
    with b.group("Cotes"):
        for side in (-1, 1):
            with b.at((x1 if side > 0 else x0, 0, 0), yaw=-90 * side):
                zc = (zb - 4.0) * side
                _fenetre_simple(b, zc, HS + 1.6, 2.6, 2.0, cadre, lumiere=(side > 0 and variant % 2 == 0))
                b.box((-0.35, HS + 0.25, -0.22), (0.35, H2 - 0.8, 0.3), cadre, name="Poteau")
                b.box((-0.3, YS, -0.18), (0.3, HS - 0.4, 0.3), cadre, name="Poteau")
        with b.at((0, 0, zb), yaw=180):
            for k, xx in enumerate((W / 5 + 0.6, -W / 5 - 0.6)):
                _fenetre_simple(b, xx, HS + 1.6, 3.2, 2.2, cadre, lumiere=((variant + k) % 3 == 1))
            b.box((-W / 4 - 1.4, YS, -0.12), (-W / 4 + 1.4, YK, 0.3), cadre, name="Porte")
            # petit auvent arrière (hisashi) sur toute la largeur : dos de machiya, lu d'avion et des ruelles
            _pan_z(b, -0.9, YA - 1.0, 0.3, YA - 0.52, x0 + 0.3, x1 - 0.3, 0.5, vr(toit, rng, 0.02), name="Auvent")
            b.box((x0 + 0.3, YA - 1.55, -1.0), (x1 - 0.3, YA - 0.95, -0.75), col(J["rive"]), name="Rive")

    # --- toit ----------------------------------------------------------------------------------------------
    with b.group("Toit"):
        forme = S["forme"]
        pign = "torchis" if mur == "torchis" else mur
        if forme == "irimoya":
            R = _toit_irimoya(b, x0 - 0.6, x1 + 0.6, zf - 2.4, zb + 0.7, H2, toit, a_z0=4.4, a_z1=2.7, a_x0=3.4,
                              a_x1=3.4, h1=1.6, h2=0.55 * (D / 2 - 1.6), tri="torchis", rng=rng, gegyo=S["cadre"],
                              oni_h=1.3)
            top = R["top"]
        elif forme == "tsumairi":
            top = _toit_tsumairi(b, x0, x1, zf, zb, H2, 0.46 if W > 20 else 0.5, toit, pign, deb=0.75, deb_av=2.2,
                                 deb_ar=0.6, ep=0.8, rng=rng, treillis=S["cadre"], gegyo="bronze")
            with b.at((0, 0, zf)):
                b.box((x0 + 0.3, H2 + 0.05, -0.35), (x1 - 0.3, H2 + 0.5, 0.1), cadre, name="Tsuma_poutre")
        else:
            top, _ = _toit_hirairi(b, x0, x1, zf, zb, H2, 0.45, toit, pign, deb_av=2.4, deb_ar=0.6, deb_cote=0.6,
                                   ep=0.8, sori=0.5, rng=rng)
        if S.get("cheminee"):
            # cheminée de briques des bains (dépasse du toit à l'arrière)
            xc, zc = x1 - 3.0, zb - 2.4
            b.box((xc - 0.9, H2 - 1.0, zc - 0.9), (xc + 0.9, 22.9, zc + 0.9), vr("terre_cuite", rng, 0.03), name="Cheminee")
            b.box((xc - 1.05, 21.6, zc - 1.05), (xc + 1.05, 22.2, zc + 1.05), col("fer"), name="Cheminee_bague")
            b.box((xc - 1.15, 22.9, zc - 1.15), (xc + 1.15, 23.4, zc + 1.15), col("fer"), studs="top", name="Cheminee_cap")
            top = max(top, 23.4)
    return {"emprise": (W, D), "hauteur": round(top, 2)}


def _etal_comptoir(b, etal, sa, sb, y, z, rng):
    """Marchandises sur le comptoir d'une boutique ouverte (z = milieu du plateau, repère de façade)."""
    if etal == "the":
        # jarres à thé, bouilloire, rangée de tasses
        b.cyl((sa + 1.2, y + 0.9, z), 0.75, 1.8, vr("bleu_profond", rng, 0.05), axis="y", name="Jarre")
        b.cyl((sa + 1.2, y + 1.95, z), 0.45, 0.3, col("bois_fonce"), axis="y", studs="top", collide=False, name="Couvercle")
        b.cyl((sa + 2.9, y + 0.7, z), 0.65, 1.4, vr("ocre_fonce", rng, 0.05), axis="y", studs="top", name="Jarre")
        b.cyl((sb - 1.4, y + 0.45, z), 0.6, 0.9, col("noir"), axis="y", name="Bouilloire")
        for i in range(3):
            b.cyl((sa + 4.4 + i * 0.9, y + 0.22, z - 0.1), 0.28, 0.44, col("blanc_creme"), axis="y", collide=False,
                  name="Tasse")
    elif etal == "dango":
        b.box((sa + 0.6, y, z - 0.45), (sa + 3.6, y + 0.3, z + 0.45), col("laque_noire"), studs="top", name="Plateau")
        for xx in (sa + 1.4, sa + 2.8):
            _dango(b, xx, y + 0.3, z)
        b.box((sb - 3.2, y, z - 0.5), (sb - 2.0, y + 0.8, z + 0.5), col("sakura_clair"), studs="top", name="Boite")
        b.box((sb - 1.8, y, z - 0.5), (sb - 0.6, y + 0.6, z + 0.5), col("blanc_creme"), studs="top", name="Boite")


def _maison_bois_simple(b, variant, largeur, profondeur):
    """Maison de bois de la seconde rangée (≤ 70 pièces) : murs, poteaux d'angle, auvent, deux fenêtres au rez,
    balcon à shoji éclairés à l'étage, fenêtres de côté, toit à deux pans de tuiles grises."""
    rng = b.rng
    S = _style(_MAISONS_BOIS, variant, _ALT_BOIS)
    W, D = float(largeur), float(profondeur)
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    YS, YK, YA, HS = 0.6, 7.2, 10.2, 10.0
    H2 = min(S["h2"], 15.6)
    PA = 0.4
    cadre = col(S["cadre"])
    mur, toit = S["mur"], S["toit"]
    J = _jeu(toit)
    with b.group("Corps"):
        b.box((x0, 0, zf - 0.3), (x1, YS, zb), vr("pierre_fonce", rng, 0.03), studs="top", name="Socle")
        b.box((x0, YS, zf), (x1, HS, zb), vr(S["rdc"], rng, 0.03), name="Mur_rdc")
        b.box((x0, HS, zf), (x1, H2 - 0.8, zb), vr(mur, rng, 0.02), name="Mur_etage")
        b.box((x0 - 0.15, H2 - 0.8, zf - 0.15), (x1 + 0.15, H2, zb + 0.15), cadre, name="Sabliere")
        b.box((x0 - 0.1, HS - 0.4, zf - 0.1), (x1 + 0.1, HS + 0.25, zb + 0.1), cadre, name="Bandeau")
        for xa in (x0 - 0.1, x1 - 0.7):
            for za in (zf - 0.1, zb - 0.7):
                b.box((xa, YS, za), (xa + 0.8, H2 - 0.8, za + 0.8), cadre, name="Poteau_angle")
    with b.group("Facade"), b.at((0, 0, zf)):
        b.box((-2.2, YS, -0.1), (2.2, YK, 0.3), col(INTERIEUR), name="Entree")
        b.box((-2.7, YK, -0.4), (2.7, YK + 0.5, 0.3), cadre, name="Linteau")
        for xx in (x0 + W / 4 - 0.6, x1 - W / 4 + 0.6):
            _fenetre_simple(b, xx, 2.6, 3.4, 2.6, cadre, lumiere=False)
        _pan_z(b, -2.0, YA - 0.8, 0.3, YA + 0.12, x0 - 0.3, x1 + 0.3, 0.6, vr(toit, rng, 0.02), name="Auvent")
        b.box((x0 - 0.3, YA - 1.5, -2.2), (x1 + 0.3, YA - 0.72, -1.94), col(J["rive"]), name="Rive")
        bw = W - 4.0
        b.box((-bw / 2, YA + 0.15, -1.6), (bw / 2, YA + 0.6, 0.3), vr("bois_moyen", rng, 0.03), studs="top",
              name="Plancher")
        _shoji(b, -bw / 2 + 0.8, bw / 2 - 0.8, YA + 0.95, H2 - 1.6, cadre, n=4, lumiere=(variant % 2 == 0),
               traverse=False)
        _garde_corps(b, -bw / 2, bw / 2, YA + 0.6, -1.35, "bois_moyen", h=1.4, pas=bw / 2, plein="bois_gris_clair")
    with b.group("Cotes"):
        for side in (-1, 1):
            with b.at((x1 if side > 0 else x0, 0, 0), yaw=-90 * side):
                _fenetre_simple(b, 0.0, HS + 1.5, 2.6, 2.0, cadre, lumiere=(side > 0))
        with b.at((0, 0, zb), yaw=180):
            _fenetre_simple(b, 0.0, HS + 1.5, 3.4, 2.0, cadre, lumiere=False)
    with b.group("Toit"):
        top, _ = _toit_hirairi(b, x0, x1, zf, zb, H2, 0.45, toit, "torchis" if mur == "torchis" else mur, deb_av=1.8,
                               deb_ar=0.6, deb_cote=0.6, ep=0.8, rng=rng, oni=(variant % 2 == 1), verge=False,
                               noshi=None)
    return {"emprise": (W, D), "hauteur": round(top, 2)}


# ---------------------------------------------------------------------------
# ÉCHOPPE DE RUELLE
# ---------------------------------------------------------------------------

_ECHOPPES = [
    # 0 : poissonnier — bâche bleue, plateaux de glace, poissons argentés et un rouge, seaux
    dict(bache="noren_bleu", bord="noren_indigo", rayure="blanc_pur", marchandise="poisson",
         lampion=("lampion_papier", True), texte=None),
    # 1 : légumes — bâche ocre, paniers de légumes colorés, daikon, potiron
    dict(bache="noren_ocre", bord="ocre_brun", rayure="toile_ecrue", marchandise="legumes",
         lampion=("rouge", False), texte=None),
    # 2 : étoffes 呉服 — bâche rouge, rouleaux de tissu, pièces pliées
    dict(bache="noren_rouge", bord="laque_rouge_fonce", rayure="blanc", marchandise="etoffes",
         lampion=("lampion_papier", True), texte="呉服"),
    # 3 : poteries — bâche indigo, jarres, vases et bols empilés
    dict(bache="noren_indigo", bord="noren_bleu", rayure="toile_ecrue", marchandise="poteries",
         lampion=("orange_lampion", True), texte=None),
    # 4 : douceurs 団子 — bâche blanche à bord rose, brochettes de dango, boîtes de couleur
    dict(bache="noren_blanc", bord="sakura_vif", rayure="sakura", marchandise="douceurs",
         lampion=("rouge", False), texte="団子"),
]


def echoppe(b, variant=0):
    """Échoppe de ruelle 8 × 5 (≤ 9 de haut) : bâti de bois clair à quatre montants, bâche de toile inclinée vers
    la rue (rayures et lambrequin), comptoir stud, gradins de présentation, marchandises colorées, lanterne ;
    enseigne de toile pour 呉服 et 団子. L'avant (-Z) regarde le couloir ; la bâche déborde de 0,8 au-dessus de 6."""
    rng = b.rng
    S = _style(_ECHOPPES, variant)
    bois, bm = col("bois_clair"), col("bois_moyen")
    za, ya, zb_, yb_ = -3.3, 7.05, 2.3, 8.7            # dessus de la bâche : bord avant / bord arrière
    pente = (yb_ - ya) / (zb_ - za)

    def bache(z):
        return ya + (z - za) * pente

    with b.group("Bati"):
        b.box((-3.9, 0, -2.4), (3.9, 0.3, 2.4), col("bois_fonce"), studs="top", name="Plancher")
        for sx in (-1, 1):
            for zp in (-2.0, 2.0):
                yt = bache(zp) - 0.25
                b.box((sx * 3.7 - 0.2, 0.3, zp - 0.2), (sx * 3.7 + 0.2, yt, zp + 0.2), bois, name="Montant")
        for zp in (-2.0, 2.0):
            yt = bache(zp) - 0.25
            b.box((-3.95, yt - 0.45, zp - 0.3), (3.95, yt, zp + 0.3), bm, name="Traverse")
        b.box((-3.5, 0.3, -2.3), (3.5, 2.4, -1.0), vr(bm, rng, 0.03), name="Comptoir")
        b.box((-3.8, 2.4, -2.5), (3.8, 2.8, -0.8), bois, studs="top", name="Plateau")
        b.box((-3.5, 0.3, 0.5), (3.5, 3.2, 1.9), vr(bm, rng, 0.03), studs="top", name="Gradin")
        b.box((-3.5, 3.2, 1.2), (3.5, 4.4, 1.9), vr(bm, rng, 0.03), studs="top", name="Gradin")
    with b.group("Bache"):
        _pan_z(b, za, ya, zb_, yb_, -4.0, 4.0, 0.3, vr(S["bache"], rng, 0.02), name="Bache", material="Fabric")
        for xx in (-1.6, 1.6):
            _pan_z(b, za, ya + 0.15, zb_, yb_ + 0.15, xx - 0.6, xx + 0.6, 0.3, col(S["rayure"]), studs="top",
                   name="Rayure", material="Fabric", collide=False)
        p = b.box((-4.0, 6.0, za - 0.12), (4.0, ya - 0.2, za + 0.12), col(S["bord"]), material="Fabric",
                  collide=False, name="Lambrequin")
        if S["texte"]:
            p.label = {"face": "Front", "text": S["texte"], "color": col("blanc_pur"), "font": "brush"}
    with b.group("Marchandises"):
        _marchandises(b, S["marchandise"], rng)
    lc, ln = S["lampion"]
    _chochin(b, 2.9, bache(-2.0) - 0.7, -2.0, r=0.5, h=1.0, corps=lc, neon=ln)
    return {"emprise": (8.0, 5.0), "hauteur": round(yb_ + 0.1, 2)}


def _marchandises(b, quoi, rng):
    """Marchandises d'une échoppe : plateau (y = 2,8, z ≈ -1,65) et gradins (y = 3,2 et 4,4)."""
    yP, zP = 2.8, -1.65
    if quoi == "poisson":
        for xc in (-2.0, 1.6):
            b.box((xc - 1.5, yP, zP - 0.6), (xc + 1.5, yP + 0.35, zP + 0.6), col("bois_clair"), name="Plateau")
            b.box((xc - 1.3, yP + 0.35, zP - 0.45), (xc + 1.3, yP + 0.5, zP + 0.45), col("blanc_pur"), name="Glace")
        for i, (xc, yaw, cc) in enumerate(((-2.6, 8, POISSON), (-1.4, -6, POISSON), (1.0, 4, "#D8665A"),
                                          (2.2, -10, POISSON))):
            b.boxc((xc, yP + 0.72, zP), (0.7, 0.45, 1.6), col(cc), yaw=yaw, collide=False, name="Poisson")
        for xc in (-2.2, 0.0, 2.2):
            b.cyl((xc, 3.2 + 0.55, 1.5), 0.6, 1.1, col("bois_moyen"), axis="y", studs="top", name="Seau")
        b.cyl((0.0, 4.4 + 0.15, 1.55), 0.75, 0.3, col("bleu"), axis="y", studs="top", name="Panier")
    elif quoi == "legumes":
        tas = (("feuille_claire", -2.5), ("orange_lampion", -0.85), (AUBERGINE, 0.85), ("rouge", 2.5))
        for cc, xc in tas:
            b.cyl((xc, yP + 0.3, zP), 0.72, 0.6, col("sudare"), axis="y", name="Panier")
            b.box((xc - 0.5, yP + 0.6, zP - 0.5), (xc + 0.5, yP + 1.05 + 0.15 * float(rng.integers(0, 3)), zP + 0.5),
                  col(cc), studs="top", collide=False, name="Legumes")
        for xc in (-2.0, -0.8):
            b.cyl((xc, 3.2 + 0.32, 1.0), 0.3, 2.2, col("blanc_creme"), axis="z", collide=False, name="Daikon")
            b.box((xc - 0.25, 3.3, 2.1), (xc + 0.25, 3.9, 2.45), col("feuille"), collide=False, name="Fanes")
        b.ball((1.6, 3.2 + 0.75, 1.1), 0.75, col("ocre"), name="Potiron")
        b.box((-2.8, 4.4, 1.25), (2.8, 5.0, 1.85), col("feuille"), studs="top", collide=False, name="Bottes")
    elif quoi == "etoffes":
        couleurs = ("noren_bleu", "sakura", "ocre_clair", "blanc", "noren_indigo", "laque_rouge")
        for i, cc in enumerate(couleurs):
            xc = -2.9 + i * 1.16
            b.cyl((xc, 3.2 + 0.42, 0.95), 0.42, 0.9, col(cc), axis="z", name="Rouleau")
            if i % 2 == 0:
                b.cyl((xc + 0.58, 4.4 + 0.42, 1.55), 0.42, 0.6, col(couleurs[(i + 3) % 6]), axis="z",
                      collide=False, name="Rouleau")
        for xc, cc in ((-2.0, "noren_bleu"), (0.0, "sakura_clair"), (2.0, "ocre_clair")):
            b.box((xc - 0.8, yP, zP - 0.55), (xc + 0.8, yP + 0.45, zP + 0.55), col(cc), studs="top", name="Pli")
    elif quoi == "poteries":
        for i, (xc, r, h, cc) in enumerate(((-2.7, 0.55, 1.4, "bleu"), (-1.4, 0.45, 0.9, "blanc_creme"),
                                            (0.0, 0.6, 1.6, "terre_cuite"), (1.4, 0.45, 1.0, "bleu_profond"),
                                            (2.7, 0.55, 1.2, "blanc_creme"))):
            b.cyl((xc, yP + h / 2, zP), r, h, col(cc), axis="y", studs="top", name="Vase")
        for xc in (-2.4, -0.8, 0.8, 2.4):
            b.cyl((xc, 3.2 + 0.2, 1.0), 0.55, 0.4, col("blanc_creme" if xc < 0 else "ocre_clair"), axis="y",
                  studs="top", name="Bols")
        b.cyl((-1.5, 4.4 + 0.7, 1.55), 0.5, 1.4, col("terre_cuite"), axis="y", studs="top", name="Jarre")
        b.cyl((1.5, 4.4 + 0.55, 1.55), 0.45, 1.1, col("bleu"), axis="y", studs="top", name="Jarre")
    else:  # douceurs
        b.box((-3.3, yP, zP - 0.55), (-0.3, yP + 0.25, zP + 0.55), col("laque_rouge"), studs="top", name="Plateau")
        for xc in (-2.6, -1.6, -0.8):
            _dango(b, xc, yP + 0.25, zP)
        for xc, cc in ((0.9, "sakura_clair"), (2.4, "jaune_lampion")):
            b.box((xc - 0.6, yP, zP - 0.5), (xc + 0.6, yP + 0.7, zP + 0.5), col(cc), studs="top", name="Boite")
        for xc, cc in ((-2.2, "blanc_creme"), (0.0, "sakura"), (2.2, DANGO[2])):
            b.box((xc - 0.8, 3.2, 0.7), (xc + 0.8, 3.75, 1.7), col(cc), studs="top", collide=False, name="Gateaux")


# ---------------------------------------------------------------------------
# TOUR DE GUET À INCENDIE (hinomi-yagura)
# ---------------------------------------------------------------------------


def tour_guet_bois(b, variant=0, hauteur=28):
    """Tour de guet à incendie d'Edo (hinomi-yagura), emprise 7 × 7 : quatre poteaux de bois patiné inclinés
    vers l'intérieur, liernes et croix de Saint-André sur trois faces, échelle sur la face avant (-Z),
    plateforme à garde-corps, petit toit de tuiles grises, cloche d'alarme de bronze (hanshō).
    v0 plateforme et toit ; v1 deux plateformes ; v2 tour-échelle élancée, cloche seule sous un petit toit."""
    rng = b.rng
    v = variant % 3
    H = float(hauteur)
    bg = vr("bois_gris", rng, 0.03)
    bgc, bf = col("bois_gris_clair"), col("bois_fonce")
    if v == 2:
        r0, yp = 2.6, H - 4.4           # demi-écart des poteaux au pied, niveau du palier haut
        rp = 1.15
        yr = yp + 2.2                   # pied du petit toit
        niveaux = [5.0, 10.5, 16.0, yp - 3.5]
    else:
        r0, yp = 3.0, H - 6.2
        rp = 2.1
        yr = yp + 3.4
        niveaux = [5.5, 11.0, 16.5] if v == 0 else [5.5, yp / 2 + 0.3, 16.5]

    def r(y):
        return r0 + (rp - r0) * (y - 0.4) / (yp - 0.4)

    with b.group("Bati"):
        b.box((-3.5, 0, -3.5), (3.5, 0.4, 3.5), vr("pierre_fonce", rng, 0.03), studs="top", name="Socle")
        for sx in (-1, 1):
            for sz in (-1, 1):
                _poutre(b, (sx * r0, 0.4, sz * r0), (sx * r(yr), yr, sz * r(yr)), 0.6, 0.6, bg, name="Poteau")
        # liernes horizontales (nuki) sur les quatre faces
        for yl in niveaux:
            rl = r(yl)
            for s in (-1, 1):
                b.box((-rl - 0.5, yl - 0.25, s * rl - 0.2), (rl + 0.5, yl + 0.25, s * rl + 0.2 + 0.15 * s), bf,
                      collide=False, name="Nuki")
                xa, xb = sorted((s * rl - 0.2, s * rl + 0.2 + 0.15 * s))
                b.box((xa - 0.02 * s, yl - 0.2, -rl - 0.45), (xb, yl + 0.2, rl + 0.45), bf, collide=False, name="Nuki")
        # croix de Saint-André sur trois faces (la face avant porte l'échelle)
        baies = list(zip([0.4] + niveaux, niveaux))[: (2 if v == 1 else 3)]
        for (ya_, yb_) in baies:
            ra, rb = r(ya_ + 0.3), r(yb_ - 0.3)
            rm = (ra + rb) / 2
            for k, (n, off) in enumerate((((0, 0, 1), (0, 0, rm + 0.05)), ((1, 0, 0), (rm + 0.05, 0, 0)),
                                         ((-1, 0, 0), (-rm - 0.05, 0, 0)))):
                for d_, sgn in ((0.0, 1), (0.06, -1)):
                    if n[2]:
                        p0 = (-sgn * ra, ya_ + 0.3, off[2] + d_)
                        p1 = (sgn * rb, yb_ - 0.3, off[2] + d_)
                    else:
                        p0 = (off[0] + d_ * n[0], ya_ + 0.3, -sgn * ra)
                        p1 = (off[0] + d_ * n[0], yb_ - 0.3, sgn * rb)
                    _poutre(b, p0, p1, 0.32, 0.22, bgc, normale=n, collide=False, name="Croix")
        # échelle sur la face avant, du sol au palier
        n_bar = int((yp - 1.0) / 2.0)
        for sx in (-0.75, 0.75):
            _poutre(b, (sx, 0.4, -r0 + 0.2), (sx, yp + 0.6, -r(yp + 0.6) + 0.2), 0.26, 0.3, bgc, name="Montant")
        for i in range(n_bar):
            y = 1.6 + i * (yp - 1.6) / n_bar
            zc = -r(y) + 0.2
            b.box((-0.75, y - 0.1, zc - 0.11), (0.75, y + 0.1, zc + 0.11), bgc, collide=False, name="Barreau")

    with b.group("Plateforme"):
        paliers = [yp] + ([yp / 2 + 0.3 + 0.5] if v == 1 else [])
        for k, yq in enumerate(paliers):
            rq = min(3.35, (rp if k == 0 else r(yq)) + (0.85 if v != 2 else 0.6))
            b.box((-rq, yq - 0.5, -rq), (rq, yq, rq), vr("bois_gris", rng, 0.04), studs="top", name="Plancher")
            if v != 2:
                hg = 1.5 if k == 0 else 1.2
                for s in (-1, 1):
                    b.box((-rq, yq + hg - 0.3, s * rq - 0.15), (rq, yq + hg, s * rq + 0.15), bf, studs="top", name="Lisse")
                    b.box((s * rq - 0.15, yq + hg - 0.3, -rq + 0.15), (s * rq + 0.15, yq + hg, rq - 0.15), bf,
                          studs="top", name="Lisse")
                    if k == 0:
                        b.box((-rq + 0.1, yq, s * rq - 0.1), (rq - 0.1, yq + 0.7, s * rq + 0.1), bgc, name="Plinthe")
                        b.box((s * rq - 0.1, yq, -rq + 0.3), (s * rq + 0.1, yq + 0.7, rq - 0.3), bgc, name="Plinthe")
                # balustres d'angle : du plancher au dessous des lisses, en retrait (aucune face coplanaire)
                for sx in (-1, 1):
                    for sz in (-1, 1):
                        xa_, xb_ = sorted((sx * (rq - 0.3), sx * (rq - 0.02)))
                        za_, zb_ = sorted((sz * (rq - 0.3), sz * (rq - 0.02)))
                        b.box((xa_, yq, za_), (xb_, yq + hg - 0.3, zb_), bf, collide=False, name="Balustre")

    with b.group("Toit"):
        rt = r(yr)
        dt = rt + (1.2 if v != 2 else 0.9)
        for s in (-1, 1):
            b.box((-rt - 0.3, yr - 0.45, s * rt - 0.25), (rt + 0.3, yr, s * rt + 0.25), bf, name="Entrait")
        ht = 1.7 if v != 2 else 1.3
        tg = vr("tuile_grise", rng, 0.02)
        b.box((-dt, yr, -dt), (dt, yr + 0.3, dt), col("tuile_grise_fonce"), collide=False, name="Rive")
        b.wedge((-dt, yr + 0.3, -dt), (dt, yr + 0.3 + ht, 0), tg, down="-z", studs="top", name="Toit")
        b.wedge((-dt, yr + 0.3, 0), (dt, yr + 0.3 + ht, dt), tg, down="+z", studs="top", name="Toit")
        b.box((-dt - 0.2, yr + ht - 0.1, -0.45), (dt + 0.2, yr + ht + 0.6, 0.45), col("tuile_grise_fonce"), studs="top",
              name="Faitage")
        top = yr + ht + 0.6
        # cloche d'alarme suspendue à l'entrait central
        b.box((-rt - 0.2, yr - 0.4, -0.2), (rt + 0.2, yr - 0.05, 0.2), bf, name="Entrait")
        b.box((-0.06, yr - 0.95, -0.06), (0.06, yr - 0.4, 0.06), col("noir"), collide=False, name="Corde")
        b.cyl((0, yr - 1.05, 0), 0.3, 0.25, col("bronze"), axis="y", collide=False, name="Anse")
        b.cyl((0, yr - 1.65, 0), 0.5, 1.0, col("bronze"), axis="y", collide=False, name="Cloche")
        b.cyl((0, yr - 2.2, 0), 0.62, 0.2, shade(col("bronze"), 0.8), axis="y", collide=False, name="Levre")
    return {"emprise": (7.0, 7.0), "hauteur": round(top, 2)}


# ---------------------------------------------------------------------------
# Outils de la cité blanche
# ---------------------------------------------------------------------------


def _socle(b, x0, x1, z0, z1, h, rng, *, retrait=0.35):
    """Socle de pierre à deux assises (la seconde en retrait, dessus stud) : 2 pièces."""
    b.box((x0, 0, z0), (x1, h * 0.55, z1), vr("pierre_fonce", rng, 0.03), name="Socle")
    b.box((x0 + retrait, h * 0.55, z0 + retrait), (x1 - retrait, h, z1 - retrait), vr("pierre", rng, 0.03), studs="top",
          name="Socle")


def _travees(b, xs, ya, yb, rng, cadre, *, poteaux=True, panneaux=True, saillie=0.3):
    """Mur d'enduit en travées (repère de façade, mur en z = 0) : panneaux de `blanc_pixel` (0,1 en saillie)
    entre des poteaux de bois sombre (0,6 de large, `saillie` en avant) posés aux abscisses `xs`."""
    if panneaux:
        for xa, xb in zip(xs, xs[1:]):
            if xb - xa > 1.0:
                b.box((xa + 0.3, ya, -0.1), (xb - 0.3, yb, 0.05), blanc_pixel(rng), collide=False, name="Panneau")
    if poteaux:
        for xx in xs:
            b.box((xx - 0.3, ya, -saillie), (xx + 0.3, yb, 0.0), col(cadre), name="Poteau")


def _poutre_h(b, xa, xb, ya, yb, cadre, *, saillie=0.42, name="Nageshi"):
    """Poutre horizontale apparente (nageshi, sablière) en avant des poteaux (repère de façade)."""
    b.box((xa, ya, -saillie), (xb, yb, 0.05), col(cadre), name=name)


def _porte_cite(b, x, w, y0, h, cadre, *, battants="bois_fonce"):
    """Porte de la cité : encadrement sombre, deux battants de bois, ferrures dorées (4 pièces)."""
    b.box((x - w / 2 - 0.45, y0, -0.3), (x + w / 2 + 0.45, y0 + h + 0.5, 0.05), col(cadre), name="Encadrement")
    b.box((x - w / 2, y0, -0.45), (x + w / 2, y0 + h, -0.25), col(battants), name="Battants")
    b.box((x - 0.06, y0, -0.55), (x + 0.06, y0 + h, -0.4), shade(col(battants), 0.7), name="Joint")
    b.box((x - w / 2 + 0.2, y0 + h * 0.45, -0.6), (x + w / 2 - 0.2, y0 + h * 0.45 + 0.3, -0.4), col("or"), name="Ferrure")


def _cotes_blancs(b, W, D, ya, yb, rng, cadre, *, fenetres=((0.0, 9.0, 3.0, 2.2),), poteau=True, z_mur=None,
                  poutre=None):
    """Pignons latéraux d'un bâtiment blanc (murs x = ±W/2, repère du bâtiment) : poteau central sombre et
    fenêtres (z_rel, y, w, h) à barreaux ; z_rel est mesuré vers l'arrière. `z_mur` = (z0, z1) du mur : deux
    panneaux de blancs voisins de part et d'autre du poteau (le côté se lit en « pixels », vu en biais depuis
    l'allée dans les deux sens) ; `poutre` = hauteur d'une poutre horizontale sombre."""
    for side in (-1, 1):
        with b.at((side * W / 2, 0, 0), yaw=-90 * side):
            if poteau:
                b.box((-0.3, ya, -0.3), (0.3, yb, 0.05), col(cadre), name="Poteau")
            if z_mur is not None:
                la, lb = sorted((z_mur[0] * side, z_mur[1] * side))
                _panneaux(b, [la + 0.05, -0.3, 0.3, lb - 0.05] if poteau else [la + 0.05, lb - 0.05], ya, yb, rng)
                if poutre is not None:
                    b.box((la + 0.05, poutre, -0.4), (lb - 0.05, poutre + 0.5, 0.05), col(cadre), name="Nageshi")
            for (zr, y, w, h) in fenetres:
                _fenetre_cite(b, zr * side, y, w, h, cadre, n=3)


def _revers(b, xa, xb, ya, yb, rng, cadre, *, n=3, ym=None, plinthe=None, h_plinthe=2.4):
    """Mur secondaire (arrière, retour) en repère de façade (mur en z = 0, extérieur vers -z) : n panneaux de
    blancs voisins (0,1 en saillie) entre n + 1 poteaux sombres (0,3 en saillie, les poteaux d'extrémité restent
    dans la longueur du mur), poutre horizontale à `ym`, soubassement de planches `plinthe` (2n + 2 à 2n + 4
    pièces). Aucun grand aplat blanc."""
    xs = [xa + 0.3 + i * (xb - xa - 0.6) / n for i in range(n + 1)]
    for x_a, x_b in zip(xs, xs[1:]):
        b.box((x_a + 0.3, ya, -0.1), (x_b - 0.3, yb, 0.05), blanc_pixel(rng), collide=False, name="Panneau")
    for xx in xs:
        b.box((xx - 0.3, ya, -0.3), (xx + 0.3, yb, 0.0), col(cadre), name="Poteau")
    if ym is not None:
        b.box((xa + 0.6, ym, -0.4), (xb - 0.6, ym + 0.5, 0.05), col(cadre), name="Nageshi")
    if plinthe is not None:
        b.box((xa + 0.6, ya, -0.2), (xb - 0.6, ya + h_plinthe, 0.05), col(plinthe), name="Koshi_ita")
    return xs


# ---------------------------------------------------------------------------
# MAISON BLANCHE DE LA CITÉ
# ---------------------------------------------------------------------------


def maison_blanche(b, variant=0, largeur=24, profondeur=18, simple=False):
    """Bâtiment de la cité blanche : socle de pierre, enduit blanc en panneaux de blancs voisins entre des
    poteaux de bois sombre, fenêtres à barreaux, portes, toits de tuiles ocre-orangé à grand débord (pentes stud,
    rives claires, sous-faces foncées, oni brun). Le bas (≤ 10-12) est caché par le mur d'allée : ce qui dépasse
    est riche (étage, frontons, toits). v0 hall à véranda et irimoya à fronton chidori ; v1 deux étages et deux
    rangs de toits ; v2 hall à pignon sur l'allée, toit bleu ; v3 entrepôt blanc (kura) ; v4 deux étages à balcon
    laqué rouge. `simple=True` : version d'arrière-plan (≤ 70 pièces)."""
    if simple:
        return _maison_blanche_simple(b, variant, largeur, profondeur)
    rng = b.rng
    v = variant % 5
    W, D = float(largeur), float(profondeur)
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    cadre = "bois_fonce"
    ocre = "ocre"
    top = 0.0
    if v == 0:
        # --- hall de plain-pied, véranda (engawa), irimoya à fronton chidori-hafu ---------------------
        YS, HM = 1.6, 13.0
        zw = zf + 3.6                                    # façade du hall (derrière la véranda)
        with b.group("Socle"):
            _socle(b, x0 + 0.4, x1 - 0.4, zf + 1.4, zb - 0.4, YS, rng)
            b.box((-3.0, 0, zf + 0.2), (3.0, 0.55, zf + 1.4), vr("pierre_claire", rng, 0.03), studs="top", name="Marche")
            b.box((-3.0, 0.55, zf + 0.8), (3.0, 1.1, zf + 1.4), vr("pierre_claire", rng, 0.03), studs="top", name="Marche")
        with b.group("Hall"):
            b.box((x0 + 1.2, YS, zw), (x1 - 1.2, HM, zb - 1.2), c("blanc"), name="Murs")
            b.box((x0 + 0.9, YS, zf + 1.6), (x1 - 0.9, YS + 0.5, zw + 0.2), vr("bois_clair", rng, 0.03), studs="top",
                  name="Engawa")
            xs = [x0 + 1.5 + i * (W - 3.0) / 4 for i in range(5)]
            for xx in xs:
                b.box((xx - 0.35, YS + 0.5, zf + 1.65), (xx + 0.35, HM, zf + 2.35), col(cadre), name="Pilier")
            b.box((x0 + 1.0, HM - 0.8, zf + 1.5), (x1 - 1.0, HM, zf + 2.5), col(cadre), name="Sabliere")
            with b.at((0, 0, zw)):
                _travees(b, xs, YS + 0.5, HM - 0.6, rng, cadre, panneaux=False)
                for i, (xa, xb) in enumerate(zip(xs, xs[1:])):
                    if i in (1, 2):
                        _shoji(b, xa + 0.6, xb - 0.6, YS + 0.6, 8.2, cadre, n=3, lumiere=True, traverse=False)
                    else:
                        _panneaux(b, [xa + 0.3, xb - 0.3], YS + 0.5, 8.6, rng)
                        _fenetre_cite(b, (xa + xb) / 2, 4.6, 2.6, 2.4, cadre, n=3)
                _poutre_h(b, x0 + 1.2, x1 - 1.2, 8.6, 9.2, cadre)
                for xa, xb in zip(xs, xs[1:]):
                    _panneaux(b, [xa + 0.3, xb - 0.3], 9.2, HM - 0.6, rng)
                for xa, xb in list(zip(xs, xs[1:]))[1:3]:
                    _fenetre_cite(b, (xa + xb) / 2, 10.0, xb - xa - 2.2, 1.6, cadre, n=5, encadrement="blanc_creme")
                _poutre_h(b, x0 + 1.2, x1 - 1.2, HM - 0.6, HM, cadre, name="Sabliere")
            _cotes_blancs(b, W - 2.4, D, YS, HM, rng, cadre, fenetres=(((zb - 1.2) / 2 + 0.15, 9.6, 3.0, 2.0),),
                          z_mur=(zw, zb - 1.2), poutre=8.6)
            with b.at((0, 0, zb - 1.2), yaw=180):
                xs_r = _revers(b, -(W / 2 - 1.2), W / 2 - 1.2, YS, HM, rng, cadre, n=4, ym=8.6)
                for xa, xb in (xs_r[:2], xs_r[-2:]):
                    _fenetre_cite(b, (xa + xb) / 2, 9.4, 3.0, 2.0, cadre, n=4)
        with b.group("Toit"):
            R = _toit_irimoya(b, x0 - 1.4, x1 + 1.4, zf - 0.8, zb + 1.6, HM, ocre, a_z0=4.6, a_z1=4.2, a_x0=4.4,
                              a_x1=4.4, h1=2.4, h2=5.0, tri="blanc", rng=rng, gegyo="or", deb_g=0.8)
            top = R["top"]
            # fronton triangulaire (chidori-hafu) sur le pan avant, face à l'allée
            wc = 9.0
            zc_ = R["zi0"] + 0.5
            ys = R["ya"] + 0.5 * R["pente"] - 0.2
            t2 = _toit_tsumairi(b, -wc / 2, wc / 2, zc_, zc_ + 6.0, ys, 0.62, ocre, "blanc", deb=0.9, deb_av=1.2,
                                deb_ar=0.0, ep=0.8, gegyo="or", rng=rng, treillis=cadre, pignon_z=(zc_, zc_ + 3.5))
            top = max(top, t2)
            # lanternes de bronze suspendues aux angles de la véranda
            for xx in (x0 + 2.6, x1 - 2.6):
                _chochin(b, xx, HM - 0.8, zf + 2.0, r=0.55, h=1.2, corps="lampion_papier", neon=True)
    elif v in (1, 4):
        # --- deux étages : rez sous un toit-jupe (v1) ou sous un balcon laqué (v4), étage, irimoya ------------
        YS = 1.4
        H1 = 10.8 if v == 1 else 11.4
        H2 = 18.0 if v == 1 else 18.4
        with b.group("Socle"):
            _socle(b, x0 + 0.3, x1 - 0.3, zf + 0.3, zb - 0.3, YS, rng)
        with b.group("Rez"):
            zr0 = zf + 1.0 if v == 1 else zf + 2.2
            b.box((x0 + 1.0, YS, zr0), (x1 - 1.0, H1, zb - 1.0), c("blanc"), name="Murs")
            xs = [x0 + 1.3 + i * (W - 2.6) / 4 for i in range(5)]
            with b.at((0, 0, zr0)):
                _travees(b, xs, YS, H1 - 0.6, rng, cadre)
                _porte_cite(b, 0.0, 3.4, YS, 5.2, cadre)
                for xx in ((xs[0] + xs[1]) / 2, (xs[3] + xs[4]) / 2):
                    _fenetre_cite(b, xx, 4.4, 2.8, 2.2, cadre, n=3)
                _poutre_h(b, x0 + 1.0, x1 - 1.0, H1 - 0.6, H1, cadre, name="Sabliere")
            _cotes_blancs(b, W - 2.0, D, YS, H1 - 0.6, rng, cadre, fenetres=((-3.2, 4.6, 2.8, 2.0),))
            with b.at((0, 0, zb - 1.0), yaw=180):
                _revers(b, x0 + 1.0, x1 - 1.0, YS, H1 - 0.6, rng, cadre, n=4)
        if v == 1:
            with b.group("Jupe"):
                _jupe(b, x0 - 0.6, x1 + 0.6, zf - 0.6, zb + 0.6, H1, 1.7, ocre, a=3.6, rng=rng)
            ux0, ux1, uz0, uz1 = x0 + 3.0, x1 - 3.0, zf + 3.0, zb - 3.0
        else:
            ux0, ux1, uz0, uz1 = x0 + 1.6, x1 - 1.6, zf + 3.2, zb - 1.6
            with b.group("Balcon"):
                yb_ = H1 + 0.6
                b.box((x0 + 0.5, H1, zf + 0.4), (x1 - 0.5, yb_, uz0 + 0.2), vr("bois_moyen", rng, 0.03), studs="top",
                      name="Plancher")
                b.box((x0 + 0.4, H1 - 0.35, zf + 0.3), (x1 - 0.4, H1 + 0.25, zf + 0.75), col("laque_rouge_fonce"),
                      name="Bandeau")
                for xx in (xs[0], xs[2], xs[4]):
                    _pan_z(b, zf + 0.6, H1 + 0.1, zr0 + 0.1, H1 - 2.2, xx - 0.3, xx + 0.3, 0.6, "laque_rouge",
                           studs="none", name="Console")
                _garde_corps(b, x0 + 0.6, x1 - 0.6, yb_, zf + 0.7, "laque_rouge", h=1.9, pas=2.3)
                for s in (-1, 1):
                    xa, xb = sorted((s * (W / 2 - 0.75), s * (W / 2 - 0.45)))
                    b.box((xa, yb_, zf + 0.9), (xb, yb_ + 1.55, uz0), col("laque_rouge"), name="Retour")
                    b.box((xa - 0.05, yb_ + 1.55, zf + 0.5), (xb + 0.05, yb_ + 1.9, uz0), col("laque_rouge"), studs="top",
                          name="Lisse")
        with b.group("Etage"):
            y0 = H1 + (0.0 if v == 1 else 0.6)
            b.box((ux0, y0, uz0), (ux1, H2, uz1), c("blanc"), name="Murs")
            wu = ux1 - ux0
            nb = 3 if v == 1 else 4
            xs2 = [ux0 + 0.3 + i * (wu - 0.6) / nb for i in range(nb + 1)]
            ya = H1 + 1.6 if v == 1 else y0
            with b.at((0, 0, uz0)):
                _travees(b, xs2, ya, H2 - 0.6, rng, cadre)
                for i, (xa, xb) in enumerate(zip(xs2, xs2[1:])):
                    if v == 4 and i in (1, 2):
                        _shoji(b, xa + 0.6, xb - 0.6, y0 + 0.3, H2 - 1.4, cadre, n=3, lumiere=True)
                    else:
                        _fenetre_cite(b, (xa + xb) / 2, ya + 1.4, min(3.4, xb - xa - 1.6), 2.4, cadre, n=4)
                _poutre_h(b, ux0 - 0.2, ux1 + 0.2, H2 - 0.6, H2, cadre, name="Sabliere")
                if v == 1:
                    _poutre_h(b, ux0 - 0.2, ux1 + 0.2, ya - 0.5, ya, cadre)
            for side in (-1, 1):
                with b.at((ux1 if side > 0 else ux0, 0, 0), yaw=-90 * side):
                    _fenetre_cite(b, ((uz0 + uz1) / 2) * side, ya + 1.4, 3.0, 2.2, cadre, n=3)
            with b.at((0, 0, uz1), yaw=180):
                _revers(b, -wu / 2, wu / 2, ya, H2 - 0.6, rng, cadre, n=2)
                for xx in (-wu / 4, wu / 4):
                    _fenetre_cite(b, xx, ya + 1.4, 3.0, 2.2, cadre, n=3)
            if v == 4:
                # lanternes rouges sous l'avant-toit, au-dessus du balcon (vues par-dessus le mur d'allée)
                for xx in (-wu / 4 - 1.2, wu / 4 + 1.2):
                    _chochin(b, xx, H2 - 0.6, zf + 1.6, r=0.6, h=1.3, corps="laque_rouge", neon=False)
        with b.group("Toit"):
            if v == 1:
                R = _toit_irimoya(b, ux0 - 2.0, ux1 + 2.0, uz0 - 2.0, uz1 + 2.0, H2, ocre, a_z0=3.4, a_z1=3.4,
                                  a_x0=3.4, a_x1=3.4, h1=1.8, h2=3.4, tri="blanc", rng=rng, gegyo="or", oni_h=1.3)
            else:
                R = _toit_irimoya(b, x0 - 0.4, x1 + 0.4, zf - 0.4, zb + 0.4, H2, ocre, a_z0=4.4, a_z1=4.0,
                                  a_x0=4.2, a_x1=4.2, h1=1.8, h2=3.6, tri="blanc", rng=rng, gegyo="or", oni_h=1.2)
            top = R["top"]
    elif v == 2:
        # --- hall à pignon sur l'allée, toit bleu (accent), fronton blanc à colombage --------------------------
        YS, HM = 1.4, 12.6
        wx0, wx1, wz0, wz1 = x0 + 1.4, x1 - 1.4, zf + 1.4, zb - 1.4
        with b.group("Socle"):
            _socle(b, x0 + 0.6, x1 - 0.6, zf + 0.6, zb - 0.6, YS, rng)
        with b.group("Hall"):
            b.box((wx0, YS, wz0), (wx1, HM, wz1), c("blanc"), name="Murs")
            xs = [wx0 + 0.3 + i * (wx1 - wx0 - 0.6) / 5 for i in range(6)]
            with b.at((0, 0, wz0)):
                _travees(b, xs, YS, HM - 0.6, rng, cadre)
                _porte_cite(b, 0.0, 3.0, YS, 5.6, cadre, battants="bois")
                _poutre_h(b, wx0, wx1, 8.4, 9.0, cadre)
                for i, (xa, xb) in enumerate(zip(xs, xs[1:])):
                    if i in (0, 4):
                        _fenetre_cite(b, (xa + xb) / 2, 4.4, xb - xa - 1.6, 2.4, cadre, n=3)
                    if i in (1, 3):
                        _fenetre_cite(b, (xa + xb) / 2, 9.6, xb - xa - 1.4, 1.8, cadre, n=4)
                _poutre_h(b, wx0 - 0.1, wx1 + 0.1, HM - 0.6, HM, cadre, name="Sabliere")
                # auvent bleu au-dessus de l'entrée (lu d'en haut)
                _pan_z(b, -1.8, 7.2, 0.3, 8.0, -3.0, 3.0, 0.5, "bleu", name="Auvent")
            _cotes_blancs(b, wx1 - wx0, D, YS, HM - 0.6, rng, cadre,
                          fenetres=((-4.0, 9.4, 2.8, 2.0), (4.0, 9.4, 2.8, 2.0)), z_mur=(wz0, wz1), poutre=8.4)
            with b.at((0, 0, wz1), yaw=180):
                xs_r = _revers(b, wx0, wx1, YS, HM - 0.6, rng, cadre, n=4, ym=8.4)
                for xa, xb in (xs_r[:2], xs_r[-2:]):
                    _fenetre_cite(b, (xa + xb) / 2, 9.4, 3.0, 2.0, cadre, n=4)
        with b.group("Toit"):
            top = _toit_tsumairi(b, wx0, wx1, wz0, wz1, HM, 0.56, "bleu", "blanc", deb=1.7, deb_av=1.8, deb_ar=1.6,
                                 ep=0.9, hafu="blanc_pur", gegyo="or", rng=rng)
            for zz, yaw in ((wz0, 0), (wz1, 180)):
                with b.at((0, 0, zz), yaw=yaw):
                    # fronton blanc (devant et derrière) : poutre de base, poteaux et lisse sombres, fenêtre
                    # d'aération à barreaux
                    run = (wx1 - wx0) / 2
                    _poutre_h(b, wx0 + 0.2, wx1 - 0.2, HM + 0.05, HM + 0.6, cadre, saillie=0.35, name="Tsuma_poutre")
                    for xx in (-run * 0.45, run * 0.45):
                        hh = run * 0.55 * 0.56 * 1.0
                        b.box((xx - 0.25, HM + 0.6, -0.25), (xx + 0.25, HM + 0.6 + hh, 0.05), col(cadre), name="Tsuka")
                    b.box((-run * 0.62, HM + 2.6, -0.28), (run * 0.62, HM + 3.05, 0.05), col(cadre), name="Nuki")
                    _fenetre_cite(b, 0.0, HM + 3.6, 2.6, 1.5, cadre, n=4)
    else:
        # --- entrepôt blanc (kura) : soubassement de planches sombres, petites fenêtres hautes, toit lourd ---
        YS, HM = 1.4, 15.0
        wx0, wx1, wz0, wz1 = x0 + 1.2, x1 - 1.2, zf + 1.2, zb - 1.2
        with b.group("Socle"):
            _socle(b, x0 + 0.5, x1 - 0.5, zf + 0.5, zb - 0.5, YS, rng)
        with b.group("Kura"):
            b.box((wx0, YS, wz0), (wx1, HM, wz1), vr("blanc", rng, 0.01), name="Murs")
            b.box((wx0 - 0.2, YS, wz0 - 0.2), (wx1 + 0.2, 5.6, wz1 + 0.2), col("bois_fonce"), name="Koshi_ita")
            b.box((wx0 - 0.3, 5.6, wz0 - 0.3), (wx1 + 0.3, 6.1, wz1 + 0.3), c("blanc_pur"), studs="top", name="Bandeau")
            b.box((wx0 - 0.25, HM - 1.2, wz0 - 0.25), (wx1 + 0.25, HM, wz1 + 0.25), c("blanc_creme"), name="Corniche")
            with b.at((0, 0, wz0 - 0.2)):
                for k in range(7):
                    xx = wx0 + 0.8 + k * (wx1 - wx0 - 1.6) / 6
                    if abs(xx) > 2.6:
                        b.box((xx - 0.15, YS + 0.2, -0.2), (xx + 0.15, 5.4, 0.05), col("bois"), name="Couvre_joint")
            # enduit en « pixels » au-dessus du bandeau : trois panneaux devant et derrière, deux par pignon
            yp0, yp1 = 6.1, HM - 1.2
            for zz, yaw in ((wz0, 0), (wz1, 180)):
                with b.at((0, 0, zz), yaw=yaw):
                    _panneaux(b, [wx0 + 0.05, -3.4, 3.4, wx1 - 0.05], yp0, yp1, rng)
            for side in (-1, 1):
                with b.at((side * (wx1 - wx0) / 2, 0, 0), yaw=-90 * side):
                    _panneaux(b, [wz0 + 0.05, 0.0, wz1 - 0.05], yp0, yp1, rng)
            with b.at((0, 0, wz1), yaw=180):
                for xx in (-W / 4 - 0.6, W / 4 + 0.6):
                    _fenetre_kura(b, xx, 10.4, 1.8, "blanc", volets=False)
            with b.at((0, 0, wz0)):
                b.box((-2.6, YS, -0.5), (2.6, 7.6, 0.05), c("blanc_pur"), name="Encadrement")
                b.box((-1.8, YS + 0.05, -0.7), (1.8, 6.6, -0.45), col("bois_fonce"), name="Porte")
                b.box((-1.8, 4.0, -0.85), (1.8, 4.3, -0.65), col("fer"), name="Ferrure")
                _pan_z(b, -2.0, 7.8, 0.3, 8.7, -3.4, 3.4, 0.6, ocre, name="Auvent")
                for xx in (-W / 4 - 0.6, W / 4 + 0.6):
                    _fenetre_kura(b, xx, 10.4, 2.0, "blanc")
            for side in (-1, 1):
                with b.at((side * (wx1 - wx0) / 2, 0, 0), yaw=-90 * side):
                    _fenetre_kura(b, 0.0, 10.4, 1.8, "blanc", volets=False)
        with b.group("Toit"):
            top, _ = _toit_hirairi(b, wx0, wx1, wz0, wz1, HM, 0.52, ocre, "blanc", deb_av=1.9, deb_ar=1.9,
                                   deb_cote=1.4, ep=1.1, sori=0.55, rng=rng, fait=1.25, oni_h=1.5)
    return {"emprise": (W, D), "hauteur": round(top, 2)}


def _fenetre_kura(b, x, y, s, mur, *, volets=True):
    """Petite fenêtre lourde d'entrepôt : encadrement épais d'enduit, ouverture sombre, deux barreaux de fer,
    volets d'enduit ouverts (6 pièces, 4 sans volets)."""
    m = col(mur)
    b.box((x - s / 2 - 0.45, y - 0.45, -0.45), (x + s / 2 + 0.45, y + s + 0.45, 0.2), shade(m, 0.97), name="Encadrement")
    b.box((x - s / 2, y, -0.55), (x + s / 2, y + s, -0.3), col(INTERIEUR), name="Ouverture")
    for xx in (x - s / 6, x + s / 6):
        b.box((xx - 0.09, y - 0.1, -0.68), (xx + 0.09, y + s + 0.1, -0.5), col(FER), name="Barreau")
    if volets:
        for sx in (-1, 1):
            xa, xb = sorted((x + sx * (s / 2 + 0.5), x + sx * (s / 2 + 0.5 + s * 0.55)))
            b.box((xa, y - 0.05, -0.75), (xb, y + s + 0.05, -0.2), c("blanc_pur"), name="Volet")


def _maison_blanche_simple(b, variant, largeur, profondeur):
    """Version d'arrière-plan (≤ 70 pièces) : v1 (et v0, v4) deux étages à toit-jupe, v3 (et v2) entrepôt."""
    rng = b.rng
    v = variant % 5
    W, D = float(largeur), float(profondeur)
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    cadre = "bois_fonce"
    if v in (2, 3):
        HM = 14.0
        wx0, wx1, wz0, wz1 = x0 + 1.2, x1 - 1.2, zf + 1.2, zb - 1.2
        _socle(b, x0 + 0.5, x1 - 0.5, zf + 0.5, zb - 0.5, 1.4, rng)
        b.box((wx0, 1.4, wz0), (wx1, HM, wz1), c("blanc"), name="Murs")
        b.box((wx0 - 0.2, 1.4, wz0 - 0.2), (wx1 + 0.2, 5.4, wz1 + 0.2), col("bois_fonce"), name="Koshi_ita")
        b.box((wx0 - 0.3, 5.4, wz0 - 0.3), (wx1 + 0.3, 5.9, wz1 + 0.3), c("blanc_pur"), studs="top", name="Bandeau")
        with b.at((0, 0, wz0)):
            b.box((-2.4, 1.4, -0.45), (2.4, 7.2, 0.05), c("blanc_pur"), name="Encadrement")
            b.box((-1.7, 1.45, -0.65), (1.7, 6.4, -0.4), col("bois_fonce"), name="Porte")
            for xx in (-W / 4 - 0.6, W / 4 + 0.6):
                _fenetre_kura(b, xx, 9.6, 1.9, "blanc", volets=False)
        with b.at((0, 0, wz1), yaw=180):
            _fenetre_kura(b, 0.0, 9.6, 1.9, "blanc", volets=False)
        for zz, yaw in ((wz0, 0), (wz1, 180)):
            with b.at((0, 0, zz), yaw=yaw):
                _panneaux(b, [wx0 + 0.05, -3.2, 3.2, wx1 - 0.05], 5.9, HM - 0.3, rng)
        for side in (-1, 1):
            with b.at((side * (wx1 - wx0) / 2, 0, 0), yaw=-90 * side):
                _panneaux(b, [wz0 + 0.05, 0.0, wz1 - 0.05], 5.9, HM - 0.3, rng)
        top, _ = _toit_hirairi(b, wx0, wx1, wz0, wz1, HM, 0.52, "ocre", "blanc", deb_av=1.8, deb_ar=1.8, deb_cote=1.4,
                               ep=1.0, rng=rng, fait=1.2, verge=False)
        return {"emprise": (W, D), "hauteur": round(top, 2)}
    H1, H2 = 10.2, 17.0
    _socle(b, x0 + 0.3, x1 - 0.3, zf + 0.3, zb - 0.3, 1.4, rng)
    b.box((x0 + 1.0, 1.4, zf + 1.0), (x1 - 1.0, H1, zb - 1.0), c("blanc"), name="Murs")
    xs = [x0 + 1.3 + i * (W - 2.6) / 4 for i in range(5)]
    with b.at((0, 0, zf + 1.0)):
        _travees(b, xs, 1.4, H1, rng, cadre, panneaux=False)
        _porte_cite(b, 0.0, 3.0, 1.4, 5.0, cadre)
    with b.at((0, 0, zb - 1.0), yaw=180):
        _revers(b, x0 + 1.0, x1 - 1.0, 1.4, H1, rng, cadre, n=3)
    _jupe(b, x0 - 0.5, x1 + 0.5, zf - 0.5, zb + 0.5, H1, 1.6, "ocre", a=3.4, rng=rng)
    ux0, ux1, uz0, uz1 = x0 + 3.0, x1 - 3.0, zf + 3.0, zb - 3.0
    b.box((ux0, H1, uz0), (ux1, H2, uz1), c("blanc"), name="Murs")
    xs2 = [ux0 + 0.3 + i * (ux1 - ux0 - 0.6) / 3 for i in range(4)]
    with b.at((0, 0, uz0)):
        _travees(b, xs2, H1 + 1.6, H2 - 0.5, rng, cadre)
        for xa, xb in zip(xs2, xs2[1:]):
            _fenetre_cite(b, (xa + xb) / 2, H1 + 2.6, 2.6, 2.0, cadre, n=3)
        _poutre_h(b, ux0 - 0.2, ux1 + 0.2, H2 - 0.6, H2, cadre, name="Sabliere")
    with b.at((0, 0, uz1), yaw=180):
        _fenetre_cite(b, 0.0, H1 + 2.6, 3.0, 2.0, cadre, n=3)
    R = _toit_irimoya(b, ux0 - 2.0, ux1 + 2.0, uz0 - 2.0, uz1 + 2.0, H2, "ocre", a_z0=3.4, a_z1=3.4, a_x0=3.4, a_x1=3.4,
                      h1=1.8, h2=3.2, tri="blanc", rng=rng, verge=False, oni_h=1.2)
    return {"emprise": (W, D), "hauteur": round(R["top"], 2)}


# ---------------------------------------------------------------------------
# CASERNE (long bâtiment blanc)
# ---------------------------------------------------------------------------


def caserne(b, variant=0, longueur=40, profondeur=14, simple=False):
    """Long bâtiment blanc (14-18 de haut), longueur le long de X : socle, travées de ~4,5 studs à poteaux sombres
    et fenêtres hautes à barreaux (au-dessus du mur d'allée), long toit ocre à faîtage. v0 véranda couverte à
    poteaux ; v1 deux niveaux à petites fenêtres et toit-jupe ; v2 véranda et porche central à pignon ;
    v3 toit bleu, façade pleine à fenêtres jumelées. `simple=True` : version d'arrière-plan (≤ 70 pièces)."""
    rng = b.rng
    v = variant % 4
    L, D = float(longueur), float(profondeur)
    x0, x1, zf, zb = -L / 2, L / 2, -D / 2, D / 2
    cadre = "bois_fonce"
    toit = "bleu" if v == 3 else "ocre"
    nb = max(4, int(round((L - 2.0) / 4.5)))
    if simple:
        return _caserne_simple(b, v, L, D, nb, toit)
    YS = 1.2
    if v == 1:
        H1, HM = 8.4, 13.6
        with b.group("Socle"):
            _socle(b, x0 + 0.3, x1 - 0.3, zf + 0.3, zb - 0.3, YS, rng)
        with b.group("Murs"):
            b.box((x0 + 0.8, YS, zf + 0.8), (x1 - 0.8, H1, zb - 0.8), c("blanc"), name="Murs")
            b.box((x0 + 1.4, H1, zf + 1.6), (x1 - 1.4, HM, zb - 1.6), c("blanc"), name="Murs")
            xs = [x0 + 1.1 + i * (L - 2.2) / nb for i in range(nb + 1)]
            with b.at((0, 0, zf + 0.8)):
                _travees(b, xs, YS, H1 - 0.5, rng, cadre, panneaux=False)
                for i, (xa, xb) in enumerate(zip(xs, xs[1:])):
                    if i == nb // 2:
                        _porte_cite(b, (xa + xb) / 2, 2.6, YS, 4.8, cadre)
                    else:
                        _fenetre_cite(b, (xa + xb) / 2, 4.4, 1.8, 1.8, cadre, n=2)
            _jupe(b, x0, x1, zf, zb, H1, 1.3, toit, a=2.6, rng=rng)
            xs2 = [x0 + 1.7 + i * (L - 3.4) / nb for i in range(nb + 1)]
            with b.at((0, 0, zf + 1.6)):
                _travees(b, xs2, H1 + 1.2, HM - 0.5, rng, cadre)
                for xa, xb in zip(xs2, xs2[1:]):
                    _fenetre_cite(b, (xa + xb) / 2, H1 + 2.0, 1.6, 1.7, cadre, n=2)
                _poutre_h(b, x0 + 1.2, x1 - 1.2, HM - 0.6, HM, cadre, name="Sabliere")
            _cotes_blancs(b, L - 2.8, D, H1, HM, rng, cadre, fenetres=((0.0, H1 + 2.0, 2.2, 1.7),), poteau=False)
            with b.at((0, 0, zb - 0.8), yaw=180):
                _revers(b, x0 + 0.8, x1 - 0.8, YS, H1, rng, cadre, n=4)
            with b.at((0, 0, zb - 1.6), yaw=180):
                _revers(b, x0 + 1.4, x1 - 1.4, H1 + 1.2, HM - 0.5, rng, cadre, n=3)
                for k in range(3):
                    _fenetre_cite(b, -L / 3 + k * L / 3, H1 + 2.0, 1.8, 1.7, cadre, n=2)
        with b.group("Toit"):
            R = _toit_irimoya(b, x0 - 0.6, x1 + 0.6, zf - 0.2, zb + 0.2, HM, toit, a_z0=3.4, a_z1=3.4, a_x0=3.4,
                              a_x1=3.4, h1=1.2, h2=2.2, tri="blanc", rng=rng, oni_h=0.6, faitage_l=0.8)
        return {"emprise": (L, D), "hauteur": round(R["top"], 2)}

    HM = 12.0
    ver = v in (0, 2)
    zw = zf + 2.6 if ver else zf + 1.0
    with b.group("Socle"):
        _socle(b, x0 + 0.2, x1 - 0.2, zf + 0.3, zb - 0.3, YS, rng)
    with b.group("Murs"):
        b.box((x0 + 0.8, YS, zw), (x1 - 0.8, HM, zb - 0.8), c("blanc"), name="Murs")
        xs = [x0 + 1.1 + i * (L - 2.2) / nb for i in range(nb + 1)]
        if ver:
            b.box((x0 + 0.6, YS, zf + 0.5), (x1 - 0.6, YS + 0.45, zw + 0.2), vr("bois_clair", rng, 0.03), studs="top",
                  name="Engawa")
            for xx in xs:
                b.box((xx - 0.3, YS + 0.45, zf + 0.75), (xx + 0.3, HM, zf + 1.35), col(cadre), name="Pilier")
            b.box((x0 + 0.7, HM - 0.7, zf + 0.6), (x1 - 0.7, HM, zf + 1.5), col(cadre), name="Sabliere")
        with b.at((0, 0, zw)):
            _travees(b, xs, YS, HM - 0.5, rng, cadre, panneaux=False)
            b.box((x0 + 0.9, YS, -0.18), (x1 - 0.9, 3.0, 0.05), col("bois"), name="Lambris")
            _poutre_h(b, x0 + 0.8, x1 - 0.8, 8.0, 8.5, cadre)
            _panneaux(b, [xx + 0.3 * (1 if k else 1) for k, xx in enumerate(xs)][:-1] + [xs[-1] - 0.3], 8.5, HM - 0.5,
                      rng)
            for i, (xa, xb) in enumerate(zip(xs, xs[1:])):
                xc = (xa + xb) / 2
                if v == 3:
                    for dx in (-0.85, 0.85):
                        _fenetre_cite(b, xc + dx, 9.1, 1.2, 1.9, cadre, n=2)
                else:
                    _fenetre_cite(b, xc, 9.1, xb - xa - 1.8, 1.9, cadre, n=3)
                if i in (1, nb - 2) and not (v == 2 and abs(xc) < 4):
                    b.box((xc - 1.4, YS, -0.3), (xc + 1.4, 6.6, 0.05), col("bois_fonce"), name="Porte")
            _poutre_h(b, x0 + 0.8, x1 - 0.8, HM - 0.6, HM, cadre, name="Sabliere")
        _cotes_blancs(b, L - 1.6, D, YS, HM, rng, cadre, fenetres=((0.0, 8.8, 2.4, 2.0),), poteau=False)
        with b.at((0, 0, zb - 0.8), yaw=180):
            _revers(b, x0 + 0.8, x1 - 0.8, YS, HM - 0.5, rng, cadre, n=4, ym=8.0)
            for k in range(4):
                _fenetre_cite(b, -L * 0.375 + k * L / 4, 9.1, 2.2, 1.8, cadre, n=2)
    with b.group("Toit"):
        R = _toit_irimoya(b, x0 - 0.8, x1 + 0.8, zf - 0.6, zb + 0.8, HM, toit, a_z0=3.6, a_z1=3.6, a_x0=3.6, a_x1=3.6,
                          h1=1.8, h2=2.9, tri="blanc", rng=rng, gegyo="or" if v != 3 else None, oni_h=0.5,
                          faitage_l=0.85)
        top = R["top"]
        if v == 2:
            # porche central à pignon (karahafu simplifié) : deux poteaux, fronton blanc treillissé, rives claires
            wp = 8.0
            for s in (-1, 1):
                b.box((s * (wp / 2 - 0.4) - 0.4, YS + 0.45, zf + 0.2), (s * (wp / 2 - 0.4) + 0.4, 10.3, zf + 1.0),
                      col("laque_rouge"), name="Pilier")
            b.box((-wp / 2 + 0.1, 9.8, zf + 0.1), (wp / 2 - 0.1, 10.4, zw), col(cadre), name="Linteau")
            t2 = _toit_tsumairi(b, -wp / 2, wp / 2, zf + 0.6, zw + 2.0, 10.4, 0.62, toit, "blanc", deb=0.8, deb_av=0.9,
                                deb_ar=0.0, ep=0.8, gegyo="or", rng=rng, treillis=cadre, pignon_z=(zf + 0.6, zf + 2.0))
            top = max(top, t2)
        if ver:
            for xx in (xs[1], xs[-2]):
                _chochin(b, xx, HM - 0.7, zf + 1.05 - 0.7, r=0.55, h=1.2, corps="lampion_papier", neon=True)
    return {"emprise": (L, D), "hauteur": round(top, 2)}


def _caserne_simple(b, v, L, D, nb, toit):
    """Caserne d'arrière-plan (≤ 70 pièces) : socle, murs, poteaux, fenêtres hautes, toit irimoya sans
    ornements ; v1 à deux niveaux et toit-jupe."""
    rng = b.rng
    x0, x1, zf, zb = -L / 2, L / 2, -D / 2, D / 2
    cadre = "bois_fonce"
    _socle(b, x0 + 0.3, x1 - 0.3, zf + 0.3, zb - 0.3, 1.2, rng)
    nb = max(4, nb // 2 + 1)
    xs = [x0 + 1.1 + i * (L - 2.2) / nb for i in range(nb + 1)]
    if v == 1:
        H1, HM = 8.2, 13.4
        b.box((x0 + 0.8, 1.2, zf + 0.8), (x1 - 0.8, H1, zb - 0.8), c("blanc"), name="Murs")
        b.box((x0 + 1.4, H1, zf + 1.6), (x1 - 1.4, HM, zb - 1.6), c("blanc"), name="Murs")
        with b.at((0, 0, zf + 0.8)):
            _travees(b, xs, 1.2, H1, rng, cadre, panneaux=False)
            for xa, xb in zip(xs, xs[1:]):
                _fenetre_cite(b, (xa + xb) / 2, 4.2, 2.0, 1.8, cadre, n=2)
        _jupe(b, x0, x1, zf, zb, H1, 1.3, toit, a=2.6, rng=rng)
        with b.at((0, 0, zf + 1.6)):
            for xa, xb in zip(xs, xs[1:]):
                _fenetre_cite(b, (xa + xb) / 2, H1 + 2.0, 2.0, 1.7, cadre, n=2)
        y_t, zt0, zt1 = HM, zf - 0.2, zb + 0.2
    else:
        HM = 12.0
        b.box((x0 + 0.8, 1.2, zf + 2.4), (x1 - 0.8, HM, zb - 0.8), c("blanc"), name="Murs")
        b.box((x0 + 0.6, 1.2, zf + 0.5), (x1 - 0.6, 1.65, zf + 2.6), vr("bois_clair", rng, 0.03), studs="top",
              name="Engawa")
        for xx in xs:
            b.box((xx - 0.3, 1.65, zf + 0.75), (xx + 0.3, HM, zf + 1.35), col(cadre), name="Pilier")
        with b.at((0, 0, zf + 2.4)):
            _poutre_h(b, x0 + 0.8, x1 - 0.8, 8.0, 8.5, cadre)
            for xa, xb in zip(xs, xs[1:]):
                _fenetre_cite(b, (xa + xb) / 2, 9.0, xb - xa - 2.4, 1.9, cadre, n=3)
        y_t, zt0, zt1 = HM, zf - 0.6, zb + 0.8
    with b.at((0, 0, zb - (1.6 if v == 1 else 0.8)), yaw=180):
        if v != 1:
            _revers(b, x0 + 0.8, x1 - 0.8, 1.2, HM, rng, cadre, n=3)
        for k in range(3):
            _fenetre_cite(b, -L / 3 + k * L / 3, y_t - 3.2, 2.2, 1.8, cadre, n=2)
    R = _toit_irimoya(b, x0 - 0.8, x1 + 0.8, zt0, zt1, y_t, toit, a_z0=3.4, a_z1=3.4, a_x0=3.4, a_x1=3.4,
                      h1=1.4 if v == 1 else 1.8, h2=2.4 if v == 1 else 2.9, tri="blanc", rng=rng, verge=False,
                      oni_h=0.5, faitage_l=0.8)
    return {"emprise": (L, D), "hauteur": round(R["top"], 2)}


# ---------------------------------------------------------------------------
# PAVILLON DE LA COUR DES ŒUFS
# ---------------------------------------------------------------------------


def _coins_releves(b, x0, x1, z0, z1, y, couleur, *, long=2.2, larg=1.1, h=0.9):
    """Coins relevés d'un avant-toit : un coin (wedge) par angle, posé en diagonale, la pente montant vers
    l'extérieur (4 pièces)."""
    for (cx, cz, yaw) in ((x1, z1, 45), (x0, z1, -45), (x1, z0, 135), (x0, z0, -135)):
        ux, uz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
        d = (long + larg) / 2                       # la pointe s'arrête à l'angle (emprise respectée)
        cc = (cx - ux * d, y + h / 2 - 0.15, cz - uz * d)
        b.part("wedge", (larg, h, long), cc, rot_y(yaw), col(couleur), studs="top", collide=False, name="Coin_releve")


def pavillon(b, variant=0):
    """Pavillon ouvert de la cour des œufs (12 × 12, ≤ 14 de haut) : socle de pierre à deux assises et marches,
    colonnes laquées rouge sur bases de bronze, poutres rouges, garde-corps bas sur les côtés et l'arrière, banc
    central, lanternes allumées, toit de tuiles ocre à coins relevés. v0 irimoya sur six colonnes ; v1 toit en
    pavillon (hōgyō) à gradins et joyau doré, quatre colonnes et frises ajourées ; v2 deux toits superposés."""
    rng = b.rng
    v = variant % 3
    rouge, rf = col("laque_rouge"), col("laque_rouge_fonce")
    YS = 1.2
    YC = 8.6 if v != 2 else 7.4
    R_ = 3.9 if v != 1 else 3.7
    with b.group("Socle"):
        b.box((-5.6, 0, -5.6), (5.6, 0.6, 5.6), vr("pierre_fonce", rng, 0.03), studs="top", name="Socle")
        b.box((-4.9, 0.6, -4.9), (4.9, YS, 4.9), vr("pierre", rng, 0.03), studs="top", name="Socle")
        b.box((-2.2, 0, -6.0), (2.2, 0.3, -5.6), vr("pierre_claire", rng, 0.03), studs="top", name="Marche")
        b.box((-2.2, 0.6, -5.3), (2.2, 0.9, -4.9), vr("pierre_claire", rng, 0.03), studs="top", name="Marche")
    if v == 0:
        cols = [(sx * R_, sz * R_) for sx in (-1, 1) for sz in (-1, 1)] + [(-R_, 0.0), (R_, 0.0)]
    elif v == 1:
        cols = [(sx * R_, sz * R_) for sx in (-1, 1) for sz in (-1, 1)]
    else:
        cols = [(sx * R_, sz * R_) for sx in (-1, 1) for sz in (-1, 1)] + [(-R_, 0.0), (R_, 0.0)]
    with b.group("Colonnes"):
        for (cx, cz) in cols:
            b.cyl((cx, YS + 0.15, cz), 0.6, 0.3, col("bronze"), axis="y", name="Base")
            b.cyl((cx, (YS + YC) / 2 + 0.15, cz), 0.42, YC - YS - 0.3, rouge, axis="y", name="Colonne")
        for s in (-1, 1):
            b.box((-R_ - 0.5, YC - 0.7, s * R_ - 0.3), (R_ + 0.5, YC, s * R_ + 0.3), rouge, name="Poutre")
            b.box((s * R_ - 0.3, YC - 0.7, -R_ + 0.3), (s * R_ + 0.3, YC, R_ - 0.3), rf, name="Poutre")
        # tirant bas (nuki) sur les côtés et l'arrière, consoles dorées aux angles
        b.box((-R_ - 0.3, YC - 2.3, R_ - 0.2), (R_ + 0.3, YC - 1.9, R_ + 0.2), rouge, name="Nuki")
        for s in (-1, 1):
            b.box((s * R_ - 0.2, YC - 2.3, -R_ - 0.3), (s * R_ + 0.2, YC - 1.9, R_ + 0.3), rouge, name="Nuki")
        for (cx, cz) in cols[:4]:
            b.box((cx - 0.55, YC - 0.1, cz - 0.55), (cx + 0.55, YC + 0.4, cz + 0.55), col("or"), name="Masu")
        if v == 1:
            # frises ajourées (ranma) sous les poutres des côtés et de l'arrière
            for s in (-1, 1):
                b.box((s * R_ - 0.12, YC - 1.9, -R_ + 0.45), (s * R_ + 0.12, YC - 0.7, R_ - 0.45), col("or"), name="Ranma")
            b.box((-R_ + 0.45, YC - 1.9, R_ - 0.12), (R_ - 0.45, YC - 0.7, R_ + 0.12), col("or"), name="Ranma")
    with b.group("Garde_corps"):
        yg = YS
        for s in (-1, 1):
            with b.at((s * R_, 0, 0), yaw=-90 * s):
                _garde_corps(b, -R_ + 0.45, R_ - 0.45, yg, 0.0, "laque_rouge", h=1.4, pas=R_ * 2)
        _garde_corps(b, -R_ + 0.45, R_ - 0.45, yg, R_, "laque_rouge", h=1.4, pas=R_ * 2)
    with b.group("Banc"):
        for xx in (-1.8, 1.8):
            b.box((xx - 0.3, YS, 0.4), (xx + 0.3, YS + 1.1, 1.6), vr("pierre_fonce", rng, 0.03), name="Pied")
        b.box((-2.4, YS + 1.1, 0.2), (2.4, YS + 1.5, 1.8), vr("pierre_claire", rng, 0.03), studs="top", name="Banc")
    with b.group("Lanternes"):
        for xx in (-2.2, 2.2):
            _chochin(b, xx, YC - 0.7, -R_, r=0.55, h=1.2, corps="lampion_papier", neon=True)
    with b.group("Toit"):
        if v == 0:
            R = _toit_irimoya(b, -6.0, 6.0, -6.0, 6.0, YC + 0.45, "ocre", a_z0=2.8, a_z1=2.8, a_x0=2.8, a_x1=2.8,
                              h1=1.4, h2=2.2, tri="blanc", rng=rng, gegyo="or", oni_h=0.9, faitage_l=0.8, deb_g=0.6)
            _coins_releves(b, -6.0, 6.0, -6.0, 6.0, YC + 0.45, "ocre_clair")
            top = R["top"]
        elif v == 1:
            y0 = YC + 0.45
            _jupe(b, -6.0, 6.0, -6.0, 6.0, y0, 1.4, "ocre", a=2.4, rng=rng)
            b.box((-3.6, y0, -3.6), (3.6, y0 + 1.4, 3.6), shade(col("ocre"), 0.8), name="Coeur")
            _jupe(b, -3.6, 3.6, -3.6, 3.6, y0 + 1.4, 1.2, "ocre", a=1.8, rng=rng)
            b.box((-1.8, y0 + 1.4, -1.8), (1.8, y0 + 2.6, 1.8), shade(col("ocre"), 0.8), name="Coeur")
            b.box((-1.9, y0 + 2.6, -1.9), (1.9, y0 + 3.1, 1.9), col("ocre_fonce"), studs="top", name="Chapeau")
            b.cyl((0, y0 + 3.5, 0), 0.35, 0.8, col("bronze"), axis="y", name="Epi")
            b.ball((0, y0 + 4.25, 0), 0.6, col("or"), name="Hoju")
            _coins_releves(b, -6.0, 6.0, -6.0, 6.0, y0, "ocre_clair")
            top = y0 + 4.85
        else:
            y0 = YC + 0.45
            _jupe(b, -6.0, 6.0, -6.0, 6.0, y0, 1.1, "ocre", a=2.2, rng=rng)
            _coins_releves(b, -6.0, 6.0, -6.0, 6.0, y0, "ocre_clair", long=1.9, h=0.8)
            b.box((-3.8, y0, -3.8), (3.8, y0 + 2.8, 3.8), c("blanc"), name="Etage")
            for s in (-1, 1):
                b.box((s * 3.8 - 0.3 * (s > 0) - 0.05, y0 + 1.1, -3.95), (s * 3.8 + 0.3 * (s < 0) + 0.05, y0 + 2.8, 3.95),
                      rouge, name="Poteau")
            b.box((-3.95, y0 + 2.3, -3.95), (3.95, y0 + 2.8, 3.95), rouge, name="Sabliere")
            with b.at((0, 0, -3.8)):
                _fenetre_cite(b, 0.0, y0 + 1.2, 3.6, 0.9, "laque_rouge", n=4)
            R = _toit_irimoya(b, -5.0, 5.0, -5.0, 5.0, y0 + 2.8, "ocre", a_z0=2.4, a_z1=2.4, a_x0=2.4, a_x1=2.4,
                              h1=1.0, h2=1.5, tri="blanc", rng=rng, gegyo=None, oni_h=0.7, faitage_l=0.7, deb_g=0.5,
                              verge=False)
            _coins_releves(b, -5.0, 5.0, -5.0, 5.0, y0 + 2.8, "ocre_clair", long=1.7, h=0.7, larg=0.9)
            top = R["top"]
    return {"emprise": (12.0, 12.0), "hauteur": round(top, 2)}


# ---------------------------------------------------------------------------
# QUARTIER LOINTAIN (ville vue d'avion et de côté)
# ---------------------------------------------------------------------------

# bâtiments (cx, cz, w, d, h, faîtage) dans un îlot de 56 × 48 ; « x » = faîtage le long de X
_QUARTIERS = [
    # 0 : cour en U (grand hall au fond, deux ailes, corps d'entrée) + annexes et deux maisons de façade
    [(0, 12, 30, 12, 10, "x"), (-19, -4, 10, 18, 8, "z"), (19, -4, 10, 18, 8, "z"), (0, -15, 14, 7, 7, "x"),
     (-6, -3, 6, 6, 6, "x"), (7, 1, 8, 6, 6, "z"), (-17, -18, 12, 6, 6, "x"), (17, -18, 12, 6, 6, "x")],
    # 1 : quatre bâtiments en damier, une longue maison entre eux, tour blanche dans la cour libre
    [(-13, 9, 20, 12, 9, "x"), (13, -9, 20, 12, 9, "x"), (-13, -11, 16, 10, 7, "x"), (12, 11, 14, 10, 8, "z"),
     (-13, -1.5, 16, 5, 6, "x")],
    # 2 : trois longues halles parallèles et trois pavillons
    [(0, 13, 44, 8, 8, "x"), (-1, 0, 30, 8, 9, "x"), (4, -13, 36, 8, 7, "x"), (20, 0, 6, 6, 6, "z"),
     (-21, -13, 6, 6, 6, "z"), (-21, 0, 6, 8, 6, "z")],
    # 3 : deux rangées décalées, deux maisons basses de part et d'autre de la tour centrale
    [(-14, 12, 18, 10, 8, "x"), (12, 12, 20, 10, 9, "x"), (-12, -12, 22, 10, 9, "x"), (15, -12, 14, 10, 7, "x"),
     (-15, 0, 14, 6, 6, "x"), (15, 0, 14, 6, 6, "x")],
    # 4 : grand hall de temple au centre, deux ailes en équerre, porche, longue maison au fond
    [(0, 4, 26, 18, 12, "x"), (-21, 2, 8, 30, 8, "z"), (21, 2, 8, 30, 8, "z"), (0, -16, 10, 6, 7, "x"),
     (-12, -16, 8, 6, 6, "x"), (12, -16, 8, 6, 6, "x"), (0, 18, 26, 6, 7, "x")],
    # 5 : îlot dense en escalier, tour en avant
    [(-12, 13, 24, 10, 10, "x"), (14, 10, 16, 14, 8, "z"), (-16, -6, 14, 12, 8, "z"), (4, -4, 14, 10, 9, "x"),
     (-12, -18, 18, 6, 6, "x")],
]
_TOURS = {1: (18, 1.5, 44, "bleu"), 3: (0, 0, 38, "ocre"), 5: (17, -14, 32, "bleu")}


def quartier_lointain(b, variant=0, largeur=56, profondeur=48):
    """Îlot de la ville lointaine (≤ 32 pièces), au-delà des remparts : mur d'enceinte bas blanc à chaperon ocre,
    trois à six bâtiments blancs à toits ocre (deux coins stud chacun), et sur v1 / v3 / v5 une tour blanche de
    34-46 à toit bleu ou ocre. Grandes formes simples, lisibles d'avion : une mer de murs blancs et de toits
    orangés. Les plans sont donnés pour 56 × 48 et mis à l'échelle de l'emprise."""
    rng = b.rng
    v = variant % 6
    W, D = float(largeur), float(profondeur)
    sx, sz = W / 56.0, D / 48.0
    x0, x1, z0, z1 = -W / 2 + 0.5, W / 2 - 0.5, -D / 2 + 0.5, D / 2 - 0.5
    toits = ("ocre", "ocre", "ocre_clair", "ocre_fonce", "terre_cuite", "ocre")
    top = 0.0
    with b.group("Enceinte"):
        hm, ep = 5.0, 1.2
        for zz in (z0, z1 - ep):
            b.box((x0, 0, zz), (x1, hm, zz + ep), blanc_pixel(rng), name="Mur")
        for xx in (x0, x1 - ep):
            b.box((xx, 0, z0 + ep), (xx + ep, hm, z1 - ep), blanc_pixel(rng), name="Mur")
        ch = vr("ocre", rng, 0.03)
        for zz in (z0, z1 - ep):
            b.box((x0 - 0.3, hm, zz - 0.3), (x1 + 0.3, hm + 0.7, zz + ep + 0.3), ch, studs="top", name="Chaperon")
        for xx in (x0, x1 - ep):
            b.box((xx - 0.3, hm, z0 + ep + 0.3), (xx + ep + 0.3, hm + 0.6, z1 - ep - 0.3), ch, studs="top",
                  name="Chaperon")
    with b.group("Batiments"):
        for i, (cx, cz, w, d, h, fa) in enumerate(_QUARTIERS[v]):
            cx, cz, w, d = cx * sx, cz * sz, w * sx, d * sz
            h = h + float(rng.integers(0, 2))
            b.box((cx - w / 2, 0, cz - d / 2), (cx + w / 2, h, cz + d / 2), blanc_pixel(rng), name="Corps")
            t = vr(toits[(i + v) % len(toits)], rng, 0.03)
            o = 1.0
            if fa == "x":
                rh = (d / 2 + o) * 0.55
                b.wedge((cx - w / 2 - o, h, cz - d / 2 - o), (cx + w / 2 + o, h + rh, cz), t, down="-z", studs="top",
                        name="Toit")
                b.wedge((cx - w / 2 - o, h, cz), (cx + w / 2 + o, h + rh, cz + d / 2 + o), t, down="+z", studs="top",
                        name="Toit")
            else:
                rh = (w / 2 + o) * 0.55
                b.wedge((cx - w / 2 - o, h, cz - d / 2 - o), (cx, h + rh, cz + d / 2 + o), t, down="-x", studs="top",
                        name="Toit")
                b.wedge((cx, h, cz - d / 2 - o), (cx + w / 2 + o, h + rh, cz + d / 2 + o), t, down="+x", studs="top",
                        name="Toit")
            top = max(top, h + rh)
    if v in _TOURS:
        tx, tz, th, tc = _TOURS[v]
        tx, tz = tx * sx, tz * sz
        with b.group("Tour"):
            b.box((tx - 3.2, 0, tz - 3.2), (tx + 3.2, th, tz + 3.2), c("blanc"), name="Tour")
            b.box((tx - 4.2, th * 0.6, tz - 4.2), (tx + 4.2, th * 0.6 + 0.8, tz + 4.2), vr("ocre", rng, 0.03), studs="top",
                  name="Jupe")
            b.wedge((tx - 4.6, th, tz - 4.6), (tx + 4.6, th + 3.4, tz), col(tc), down="-z", studs="top", name="Toit")
            b.wedge((tx - 4.6, th, tz), (tx + 4.6, th + 3.4, tz + 4.6), col(tc), down="+z", studs="top", name="Toit")
            b.box((tx - 3.3, th - 4.0, tz - 3.3), (tx + 3.3, th - 2.6, tz + 3.3), col("fenetre"), name="Fenetres")
        top = max(top, th + 3.4)
    return {"emprise": (W, D), "hauteur": round(top, 2)}
