"""Bâtiments de la zone Bleach (la cité blanche aux toits ocre), style « stud ».

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :
- maison_bois(largeur=20, profondeur=16, simple=False) : maison de marchand d'Edo à étage du FAUBOURG (bois
    sombre, torchis, tuiles grises), 18-24 de haut ; v0 thé 茶 (auvent profond, comptoir en retrait),
    v1 auberge 宿 (long balcon, sudare), v2 riz 米 (treillis koshi, ailes udatsu), v3 pignon sur rue et balcon
    (蕎麦), v4 confiserie 甘味 / 団子 (banc rouge), v5 bains 湯 (cheminée, toit irimoya). simple=True : seconde
    rangée (murs, toit, fenêtres, un balcon ; ni texte ni intérieur), ≤ 70 pièces ;
- echoppe() : échoppe de ruelle 8 × 5 (≤ 9 de haut) ; v0 poisson (bâche bleue), v1 légumes (ocre),
    v2 étoffes 呉服 (rouge), v3 poteries (indigo), v4 douceurs 団子 (blanche) ;
- tour_guet_bois(hauteur=28) : tour de guet à incendie (hinomi-yagura) 7 × 7 ; v0 plateforme et toit,
    v1 deux plateformes, v2 échelle haute et cloche seule ;
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
        _pan_z(b, zf - deb_av, H - deb_av * pe + ke, zf, H + ke, xa, xb, ep, tv(), ext_b=0.15, name="Debord")
    if deb_ar > 0:
        _pan_z(b, zb, H + ke, zb + deb_ar, H - deb_ar * pe + ke, xa, xb, ep, tv(), ext_a=0.15, name="Debord")
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
        _pan_x(b, x0 - deb, H - deb * pe + ke, x0, H + ke, za, zb_, ep, tv(), ext_b=0.15, name="Debord")
        _pan_x(b, x1, H + ke, x1 + deb, H - deb * pe + ke, za, zb_, ep, tv(), ext_a=0.15, name="Debord")
    yr = H + hu + k
    hc = col(hafu) if hafu else col(J["verge"])
    z0h, z1h = za - 0.35, za + 0.3
    segs = [(x0, H + k + 0.15, xm, yr + 0.15, 0.25, 0.45), (xm, yr + 0.15, x1, H + k + 0.15, 0.45, 0.25)]
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
        b.box((xm - 1.1, yr - 0.6, za - 0.72), (xm + 1.1, yr + 0.8, za + 0.4), col(J["oni"]), name="Oni")
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
                b.box((xx - 0.13, H + 0.1, zt0), (xx + 0.13, H + hh, zt1), tc, name="Treillis")
        yy = H + hu * 0.42
        half = run * 0.58 - 0.2
        b.box((xm - half, yy - 0.13, zt0 + 0.07), (xm + half, yy + 0.13, zt1 - 0.04), tc, name="Treillis")
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
        top = yr + oni_h
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
        b.box((xx - 0.16, y0 + 0.45, -0.5), (xx + 0.16, y1 - 0.45, 0.0), bois, name="Latte")


def _mushiko(b, x, y, w, h, barreaux, *, n=None, fond=INTERIEUR, appui=None):
    """Fenêtre mushiko-mado : fente sombre barrée de gros barreaux d'enduit, appui et linteau en relief."""
    m = col(barreaux)
    a = col(appui) if appui else shade(m, 0.93)
    b.box((x - w / 2, y, -0.12), (x + w / 2, y + h, 0.3), col(fond), name="Fente")
    n = n or max(3, int(round(w / 0.95)))
    for i in range(1, n):
        xx = x - w / 2 + i * w / n
        b.box((xx - 0.22, y, -0.4), (xx + 0.22, y + h, 0.0), m, name="Barreau")
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
        b.box((xx - 0.12, ya, -0.45), (xx + 0.12, yb, -0.2), cd, name="Kumiko")
    if traverse:
        ym = (ya + yb) / 2
        b.box((xa, ym - 0.11, -0.41), (xb, ym + 0.11, -0.2), cd, name="Kumiko")


def _fenetre_simple(b, x, y, w, h, cadre, *, lumiere=False, papier="papier"):
    """Petite fenêtre (4 pièces) : papier ou lumière, linteau, appui stud, meneau."""
    cd = col(cadre)
    kw = {"material": "Neon"} if lumiere else {}
    b.box((x - w / 2, y - 0.15, -0.12), (x + w / 2, y + h + 0.15, 0.3), col("fenetre_lumiere" if lumiere else papier),
          name="Shoji", **kw)
    b.box((x - w / 2 - 0.35, y + h, -0.4), (x + w / 2 + 0.35, y + h + 0.4, 0.3), cd, name="Linteau")
    b.box((x - w / 2 - 0.35, y - 0.4, -0.5), (x + w / 2 + 0.35, y, 0.3), cd, studs="top", name="Appui")
    b.box((x - 0.12, y, -0.3), (x + 0.12, y + h, 0.0), cd, name="Meneau")


def _fenetre_cite(b, x, y, w, h, cadre="bois_fonce", *, n=3, encadrement="blanc_pur", fond="fenetre"):
    """Fenêtre de la cité blanche (2 + n - 1 pièces) : encadrement d'enduit en relief, ouverture sombre en
    avant, barreaux de bois sombre (treillis vertical)."""
    b.box((x - w / 2 - 0.35, y - 0.4, -0.22), (x + w / 2 + 0.35, y + h + 0.35, 0.05), col(encadrement), name="Encadrement")
    b.box((x - w / 2, y, -0.34), (x + w / 2, y + h, 0.05), col(fond), name="Fenetre")
    for i in range(1, n):
        xx = x - w / 2 + i * w / n
        b.box((xx - 0.13, y, -0.5), (xx + 0.13, y + h, -0.2), col(cadre), name="Barreau")


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
        b.box((xx - 0.15, y, z - 0.15), (xx + 0.15, y + h - 0.35, z + 0.15), cd, name="Balustre")


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
            b.box((xa, ya, z0), (xb, yb, z1), blanc_pixel(rng), name=name)


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
        b.box((x0 - 0.05, HS - 0.4, zf + 0.1), (x1 + 0.05, HS + 0.25, zb + 0.05), cadre, name="Bandeau")
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
        _noren(b, da + 0.2, db - 0.2, YK, 2.9, zr - 0.8, nf, ne, nt, n=3 if len(nt) == 1 else 4)
        for xp in poteaux:
            b.box((xp - 0.4, YS, -0.3), (xp + 0.4, YA - 0.1, 0.4), cadre, name="Poteau")
        for (sa, sb) in boutiques:
            if S["rez"] == "comptoir":
                b.box((sa, YS, zr - 0.1), (sb, YK, zr + 0.3), col(INTERIEUR), name="Interieur")
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
                    b.wedge((pa, YS, -0.95), (pb, YS + 1.5, 0.2), col(BAMBOU_SEC), down="-z", name="Inuyarai")
                    _koshi(b, pa, pb, YS + 1.5, YK, cadre, "lampion_papier" if S["porte"] == "centre" else INTERIEUR,
                           pas=1.05)
        if S.get("banc"):
            sa, sb = boutiques[0]
            _banc_rouge(b, (sa + sb) / 2, -0.2, min(6.0, sb - sa - 1.0), d=1.2, rng=rng)
        if S["noren"][2] == "米":
            # ballots de riz (tawara) empilés contre le treillis, à côté de l'entrée
            xb_ = da - 1.6
            for i, (dx, yy) in enumerate(((-0.9, 0.75), (0.9, 0.75), (0.0, 2.1))):
                b.cyl((xb_ + dx, yy, -0.55), 0.7, 1.9, vr("chaume", rng, 0.05), axis="z", name="Ballot")
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
        elif et == "sudare":
            # grande baie de shoji éclairés derrière un store de bambou à demi baissé, petit garde-corps
            bw = W - 4.0
            _shoji(b, -bw / 2, bw / 2, YA + 0.9, H2 - 1.6, cadre, n=5, lumiere=True)
            b.box((-bw / 2 - 0.2, H2 - 3.4, -0.8), (bw / 2 + 0.2, H2 - 1.1, -0.6), col("sudare"), collide=False,
                  name="Sudare")
            for xx in (-bw / 4, bw / 4):
                b.box((xx - 0.1, H2 - 3.0, -0.95), (xx + 0.1, H2 - 1.1, -0.8), cadre, collide=False, name="Lien")
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
            _fenetre_simple(b, W / 5, HS + 1.6, 3.4, 2.2, cadre, lumiere=(variant % 3 == 1))
            b.box((-W / 4 - 1.4, YS, -0.12), (-W / 4 + 1.4, YK, 0.3), cadre, name="Porte")

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
        b.box((x0 - 0.05, HS - 0.4, zf - 0.05), (x1 + 0.05, HS + 0.25, zb + 0.05), cadre, name="Bandeau")
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
