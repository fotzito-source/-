"""Bâtiments du village de l'ère Taishō et du sanctuaire de montagne (zone 3), style « stud ».

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :
- machiya(largeur=22, profondeur=18) : maison de marchand à deux niveaux (≈ 22 de haut) ;
    v0 étoffes 呉服 (mushiko-mado, enseigne de toit, ailes udatsu, toit à deux pans bleu nuit),
    v1 apothicaire 薬 (étage en planches, sudare, toit irimoya ardoise, enseigne sur pied),
    v2 confiserie 甘味 (boutique ouverte, fenêtres vitrées, pignon sur rue), v3 soba 蕎麦 (balcon, lanterneau) ;
- auberge(largeur=28, profondeur=24) : ryokan à trois niveaux (≈ 30 de haut, 38 avec la tour) ;
    v0 blanc, porche kara-hafu, irimoya bleu nuit ; v1 tout en bois, porche à pignon, chidori-hafu ;
    v2 crème, tour de guet, cuivre patiné ; v3 garde-corps vermillon, chidori-hafu ;
- maison_the() : maison de thé ouverte 16 × 12 (≈ 12-14) ; v0 団子 ombrelle, v1 chaume 茶 andon,
    v2 甘味 bannières nobori, v3 藤 tonnelle de glycine ;
- kura() : entrepôt 12 × 10 (≈ 15) à soubassement namako ; v0 blanc, v1 noir à pignon sur rue,
    v2 crème 茶 sur le pignon, v3 namako sur tout le rez et 薬 ;
- sanctuaire() : pavillon de culte 28 × 24 (≈ 22), pignon sur l'avant ; v0 bois naturel et ardoise (comme la
    référence), v1 vermillon, cuivre et auvent kara-hafu, v2 laque noire et or à auvent à pignon, v3 bois clair ;
- temizuya() : pavillon des ablutions 10 × 7 (≈ 11) ; v0 bois et ardoise, v1 vermillon et cuivre,
    v2 bois sombre et lanterne de pierre, v3 chaume ;
- yatai() : échoppe ambulante 8 × 5 (≈ 8,5) ; v0 蕎麦, v1 団子, v2 茶, v3 甘味.
Débords hors emprise : avant-toits (≤ 2,6), porches et marches (≤ 1,1), ombrelle / tonnelle de la maison de thé
(≤ 1,9) ; débords latéraux des toits ≤ 1,2 (auberge), ≤ 0,8 ailleurs.

Repère (voir CONVENTIONS.md) : origine au centre de l'emprise au sol, y = 0 au sol, l'AVANT regarde -Z.
`largeur` est le long de X, `profondeur` le long de Z. Les sous-ensembles « de façade » se dessinent dans un
repère où la façade est le plan z = 0 et l'extérieur est vers -z ; on les pose avec `b.at(...)`
(yaw = -90 : façade droite +X ; yaw = 90 : façade gauche -X ; yaw = 180 : arrière).
Vu de la rue (depuis -z), +x est à GAUCHE.

Chaque fonction a au moins 4 variantes nettement différentes (`variant % 4`) ; `variant // 4` décale
encore les couleurs pour les exemplaires suivants. Uniquement des éléments japonais génériques.
"""

from __future__ import annotations

import math

from kit import hexrgb, rot_x, rot_z, shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Couleurs locales (en plus de la palette)
# ---------------------------------------------------------------------------
INTERIEUR = "#2B201A"      # fond sombre d'une boutique, d'un hall
FER = "#3A3F44"            # ferrures, grilles
BAMBOU_SEC = "#4E3B2A"     # inuyarai (barrière de bambou courbe au pied des façades)
SUDARE = "#C9A56A"         # store de bambou
NAMAKO = "#4A4E5A"         # carreaux sombres du soubassement des kura
FEUTRE = "#C8332B"         # tissu rouge des bancs (hi-mōsen)
DANGO = ("#F4A7B9", "#FAF3E3", "#9CCB6B")   # rose, blanc, vert
THE_VERT = "#7B9E5A"


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
    """Variante de base `variant % len(table)` ; au-delà, on décale toit / mur / noren pour varier la rue."""
    S = dict(table[variant % len(table)])
    k = variant // len(table)
    if k and alt:
        for key, choix in alt.items():
            if key in S:
                S[key] = choix[(variant + k) % len(choix)]
    return S


_ALT = {
    "toit": ["tuile", "tuile_ardoise", "tuile_fonce", "tuile_claire"],
    "mur": ["enduit", "enduit_creme", "enduit_gris"],
}

# ---------------------------------------------------------------------------
# Dalles inclinées (toits)
# ---------------------------------------------------------------------------


def _pan_z(b, za, ya, zb, yb, x0, x1, ep, couleur, *, ext_a=0.0, ext_b=0.0, studs="top", name="Pan", **kw):
    """Dalle inclinée dans le plan YZ : sa face supérieure passe par (za, ya) et (zb, yb), épaisseur `ep`
    sous cette ligne, étendue sur x0..x1 ; `ext_a` / `ext_b` l'allongent côté a / côté b."""
    dz, dy = zb - za, yb - ya
    L = math.hypot(dz, dy)
    uz, uy = dz / L, dy / L
    phi = math.atan2(dy, dz)
    ny, nz = math.cos(phi), -math.sin(phi)          # normale locale +Y (vers le haut si za < zb)
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


def _toit_hirairi(b, x0, x1, zf, zb, H, pente, toit, mur, *, deb_av=2.2, deb_ar=1.2, deb_cote=0.7, ep=0.8,
                  sori=0.5, rng=None, faitage=None, oni=True, pignons=True, blanc=True, fait=1.0):
    """Toit à deux pans, faîtage parallèle à X (entrée sous le long pan, « hirairi ») sur des murs x0..x1 / zf..zb
    de hauteur H : triangles de pignon en enduit, dalles stud qui débordent ; le débord est moins pentu que
    le reste du pan (`sori`), ce qui donne la courbe creuse des toits japonais. Renvoie (y_faitage_haut, f)
    où f(z) donne le dessous du pan avant à la profondeur z (pour accrocher lampions et enseignes)."""
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
        m = col(mur) if rng is None else vr(mur, rng, 0.02)
        b.wedge((x0, H, zf), (x1, H + hu + 0.3, zm), m, down="-z", name="Pignon")
        b.wedge((x0, H, zm), (x1, H + hu + 0.3, zb), m, down="+z", name="Pignon")
    # pans principaux (dessous passant par l'arête haute des murs) et débords adoucis
    _pan_z(b, zf, H + k, zm, H + hu + k, xa, xb, ep, tv(), ext_a=0.25, ext_b=0.5)
    _pan_z(b, zm, H + hu + k, zb, H + k, xa, xb, ep, tv(), ext_a=0.5, ext_b=0.25)
    _pan_z(b, zf - deb_av, H - deb_av * pe + ke, zf, H + ke, xa, xb, ep, tv(), ext_b=0.15, name="Debord")
    _pan_z(b, zb, H + ke, zb + deb_ar, H - deb_ar * pe + ke, xa, xb, ep, tv(), ext_a=0.15, name="Debord")
    # tuiles de rive (nokigawara) : bandeau vertical au bout des débords, un peu plus haut que la dalle
    rc = shade(t, 0.74)
    for zt, s_ in ((zf - deb_av, -1), (zb + deb_ar, 1)):
        yt = H - abs(zt - (zf if s_ < 0 else zb)) * pe + ke
        b.box((xa, yt - 0.8, min(zt - 0.06 * s_, zt + 0.2 * s_)), (xb, yt + 0.1, max(zt - 0.06 * s_, zt + 0.2 * s_)), rc,
              name="Rive")
    yr = H + hu + k
    fa = col(faitage) if faitage else shade(t, 0.72)
    rd = 0.95 * fait                           # demi-largeur du faîtage ; `fait` règle sa taille
    yb_f = yr - rd * pente - 0.25              # bas du faîtage, toujours noyé dans les pans
    b.box((xa - 0.15, yb_f, zm - rd), (xb + 0.15, yr + 0.75 * fait, zm + rd), fa, studs="top", name="Faitage")
    if blanc:
        # liseré d'enduit blanc sous le faîtage (lits de tuiles noshi), lisible de loin
        yn = yr - (rd + 0.1) * pente - 0.12
        b.box((xa, yn, zm - rd - 0.1), (xb, yn + 0.4 * fait, zm + rd + 0.1), col("enduit"), name="Noshi")
    top = yr + 0.75 * fait
    if oni:
        # oni-gawara aux bouts du faîtage, sans dépasser du toit (les voisins sont à 2 studs)
        for xe, s_ in ((xa - 0.2, 1), (xb + 0.2, -1)):
            xo0, xo1 = sorted((xe, xe + s_ * 1.3 * fait))
            b.box((xo0, yb_f - 0.1, zm - rd - 0.2), (xo1, yr + 1.55 * fait, zm + rd + 0.2), shade(t, 0.58), name="Oni")
        top = yr + 1.55 * fait

    def dessous(z):
        if z >= zf:
            return H + (z - zf) * pente
        return H - (zf - z) * pe

    return top, dessous


def _toit_tsumairi(b, x0, x1, zf, zb, H, pente, toit, mur, *, deb=1.2, deb_av=1.6, deb_ar=0.8, ep=0.8, sori=0.5,
                   hafu=None, gegyo="or", rng=None, faitage=None, treillis=None, pignon_z=None):
    """Toit à deux pans dont le PIGNON regarde la rue (faîtage parallèle à Z) : triangle d'enduit (ou de bois),
    dalles stud qui débordent avec un débord adouci, planches de rive (hafu) en façade, faîtage, gegyo
    (pendentif sous le faîtage) ; `treillis` = couleur d'un treillis kitsune-goshi dans le triangle avant.
    `pignon_z` = (z0, z1) de la partie pleine du comble (défaut : zf..zb). Renvoie le haut du faîtage."""
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
    m = col(mur) if rng is None else vr(mur, rng, 0.02)
    b.wedge((x0, H, pz0), (xm, H + hu + 0.3, pz1), m, down="-x", name="Pignon")
    b.wedge((xm, H, pz0), (x1, H + hu + 0.3, pz1), m, down="+x", name="Pignon")
    _pan_x(b, x0, H + k, xm, H + hu + k, za, zb_, ep, tv(), ext_a=0.25, ext_b=0.5)
    _pan_x(b, xm, H + hu + k, x1, H + k, za, zb_, ep, tv(), ext_a=0.5, ext_b=0.25)
    _pan_x(b, x0 - deb, H - deb * pe + ke, x0, H + ke, za, zb_, ep, tv(), ext_b=0.15, name="Debord")
    _pan_x(b, x1, H + ke, x1 + deb, H - deb * pe + ke, za, zb_, ep, tv(), ext_a=0.15, name="Debord")
    yr = H + hu + k
    hc = col(hafu) if hafu else shade(t, 0.62)
    # planches de rive (hafu) sur le pignon avant : suivent les deux pentes, un peu plus hautes que la dalle
    z0h, z1h = za - 0.35, za + 0.3
    for i, (xa_, ya_, xb_, yb_, ea, eb) in enumerate((
            (x0, H + k + 0.15, xm, yr + 0.15, 0.25, 0.45), (xm, yr + 0.15, x1, H + k + 0.15, 0.45, 0.25),
            (x0 - deb + 0.2, H - (deb - 0.2) * pe + ke + 0.15, x0, H + ke + 0.15, 0.0, 0.2),
            (x1, H + ke + 0.15, x1 + deb - 0.2, H - (deb - 0.2) * pe + ke + 0.15, 0.2, 0.0))):
        dz = 0.05 * (i % 2)               # planches voisines décalées : pas de faces coplanaires
        _pan_x(b, xa_, ya_, xb_, yb_, z0h - dz, z1h - dz, ep + 0.3, hc, ext_a=ea, ext_b=eb, studs="none", name="Hafu")
    fa = col(faitage) if faitage else shade(t, 0.72)
    b.box((xm - 0.95, yr - 0.6, za - 0.5), (xm + 0.95, yr + 0.55, zb_ + 0.15), fa, studs="top", name="Faitage")
    b.box((xm - 1.1, yr - 0.6, za - 0.72), (xm + 1.1, yr + 0.8, za + 0.4), shade(t, 0.58), name="Oni")
    if gegyo:
        b.box((xm - 0.7, yr - 2.6, z0h - 0.25), (xm + 0.7, yr - 0.2, z0h + 0.3), hc, name="Gegyo")
        b.box((xm - 0.4, yr - 2.3, z0h - 0.4), (xm + 0.4, yr - 1.1, z0h - 0.2), col(gegyo), name="Gegyo")
    if treillis is not None:
        # treillis kitsune-goshi dans le triangle avant (barreaux verticaux et lisses, coupés par les rives)
        tc = col(treillis)
        zt0, zt1 = pz0 - 0.25, pz0 + 0.05
        for i in range(-3, 4):
            xx = xm + i * run / 4.2
            hh = hu * (1 - abs(xx - xm) / run) - 0.2
            if hh > 0.5:
                b.box((xx - 0.12, H + 0.1, zt0), (xx + 0.12, H + hh, zt1), tc, name="Treillis")
        for j in (0.3, 0.6):
            yy = H + hu * j
            half = run * (1 - j) - 0.15
            b.box((xm - half, yy - 0.12, zt0 + 0.07), (xm + half, yy + 0.12, zt1 - 0.04), tc, name="Treillis")
    return yr + 0.8


def _toit_irimoya(b, x0, x1, z0, z1, y, toit, *, a_z0, a_z1, a_x0, a_x1, h1, h2, tri="enduit", tri_x0=None, tri_x1=None,
                  deb_g=0.7, bordure=0.5, rng=None, faitage=None, gegyo=None, oni=True):
    """Toit irimoya (croupe + pignon) en coins pleins, faîtage parallèle à X. (x0..x1, z0..z1) = bord de
    l'avant-toit, posé au niveau y (dessous plat). Jupe à quatre pans (profondeurs a_z0 / a_z1 / a_x0 / a_x1,
    hauteur h1) ; au-dessus, les pans z0 et z1 continuent, plus raides (h2), jusqu'au faîtage : la pente est
    continue vue de face, avec la courbe creuse des toits japonais ; sur les bouts x0 / x1, triangles de pignon
    (`tri`, ou `tri_x0` / `tri_x1`) en retrait, bordés par le bout des pans. Renvoie un dict de cotes."""
    t = col(toit)
    tv = (lambda: vr(t, rng, 0.025)) if rng is not None else (lambda: t)
    xi0, xi1, zi0, zi1 = x0 + a_x0, x1 - a_x1, z0 + a_z0, z1 - a_z1
    zm = (zi0 + zi1) / 2
    b.box((x0, y - 0.5, z0), (x1, y, z1), shade(t, 0.72), name="Rive")
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
    for xe, s, tc in ((xg0, -1, tri_x0 or tri), (xg1, 1, tri_x1 or tri)):
        cc = col(tc) if rng is None else vr(tc, rng, 0.02)
        xa_, xb_ = sorted((xe, xe + 0.15 * s))
        b.wedge((xa_, ya + 0.35, zs), (xb_, ya + h2 - d, zm), cc, down="-z", name="Pignon")
        b.wedge((xa_, ya + 0.35, zm), (xb_, ya + h2 - d, 2 * zm - zs), cc, down="+z", name="Pignon")
        if gegyo:
            ga, gb = sorted((xe + 0.15 * s, xe + 0.45 * s))
            b.box((ga, ya + h2 - 2.4, zm - 0.55), (gb, ya + h2 - 0.6, zm + 0.55), col(gegyo), name="Gegyo")
    yr = ya + h2
    fa = col(faitage) if faitage else shade(t, 0.72)
    b.box((xg0 - 0.3, yr - (0.95 * pente + 0.35), zm - 0.95), (xg1 + 0.3, yr + 0.8, zm + 0.95), fa, studs="top",
          name="Faitage")
    top = yr + 0.8
    if oni:
        for xe in (xg0 - 0.3, xg1 + 0.3):
            b.box((xe - 0.65, yr - 0.8, zm - 1.15), (xe + 0.65, yr + 1.6, zm + 1.15), shade(t, 0.58), name="Oni")
        top = yr + 1.6
    return {"top": top, "yr": yr, "xg0": xg0, "xg1": xg1, "zi0": zi0, "zi1": zi1, "zm": zm, "ya": ya, "pente": pente}


def _kara_hafu(b, xc, za, zb, y0, larg, h, toit, hafu, *, ep=0.7, rng=None):
    """Toit à fronton courbe (kara-hafu) : faîtage parallèle à Z, de za (avant, côté rue) à zb (arrière) ;
    profil en vague (bosse arrondie au centre, épaules raides, bords relevés) approché par quatre dalles stud
    par côté qui se chevauchent un peu aux joints ; planche de rive (`hafu`) qui dessine la courbe en façade.
    y0 = niveau des bords du toit, h = hauteur du profil. Renvoie (haut, profil) où profil(px) donne le
    dessus de la planche à l'abscisse relative px ∈ [-1, 1]."""
    t = col(toit)
    hw = larg / 2
    prof = [(-1.0, 0.0), (-0.72, 0.16), (-0.46, 0.62), (-0.2, 0.93), (0.0, 1.0),
            (0.2, 0.93), (0.46, 0.62), (0.72, 0.16), (1.0, 0.0)]
    creux = {1, 7}                   # joints creux : les dalles se prolongent l'une sous l'autre
    n = len(prof) - 1

    def profil(dy, z0_, z1_, epp, couleur, studs, name):
        P = [(xc + px * hw, y0 + py * h + dy) for (px, py) in prof]
        for i in range(n):
            (xa_, ya_), (xb_, yb_) = P[i], P[i + 1]
            ea = 0.3 if i in creux else (0.12 if i > 0 else 0.0)
            eb = 0.3 if (i + 1) in creux else (0.12 if i + 1 < n else 0.0)
            dz = 0.06 * (i % 2)          # segments voisins décalés : pas de faces coplanaires aux joints
            _pan_x(b, xa_, ya_, xb_, yb_, z0_ - dz, z1_ - dz, epp, couleur, ext_a=ea, ext_b=eb, studs=studs, name=name)

    profil(0.0, za, zb, ep, vr(t, rng, 0.02) if rng is not None else t, "top", "Kara_hafu")
    profil(0.2, za - 0.45, za + 0.05, ep + 0.35, col(hafu), "none", "Hafu")

    def dessus(px):
        px = min(1.0, abs(px))
        for (ax, ay), (bx, by) in zip(prof[4:], prof[5:]):
            if ax <= px <= bx:
                return y0 + 0.2 + h * (ay + (by - ay) * (px - ax) / (bx - ax))
        return y0 + 0.2

    return y0 + h + 0.2, dessus


# ---------------------------------------------------------------------------
# Petits éléments de façade (plan z = 0, extérieur vers -z)
# ---------------------------------------------------------------------------


def _chochin(b, x, y_haut, z, *, r=0.65, h=1.5, corps="lampion_papier", neon=True, cap="noir", corde=0.4):
    """Lanterne de papier (chōchin) suspendue : cordon, chapeau, corps cylindrique (Neon si allumée), culot.
    Renvoie le bas de la lanterne."""
    b.box((x - 0.06, y_haut - corde - 0.05, z - 0.06), (x + 0.06, y_haut + 0.1, z + 0.06), col("noir"), collide=False,
          name="Cordon")
    yt = y_haut - corde
    b.cyl((x, yt - 0.12, z), r * 0.6, 0.3, col(cap), axis="y", collide=False, name="Chapeau")
    kw = {"material": "Neon"} if neon else {}
    b.cyl((x, yt - 0.22 - h / 2, z), r, h, col(corps), axis="y", collide=False, name="Chochin", **kw)
    b.cyl((x, yt - 0.22 - h - 0.08, z), r * 0.6, 0.3, col(cap), axis="y", collide=False, name="Culot")
    return yt - 0.22 - h - 0.23


def _noren(b, xa, xb, y_haut, h, z, fond, encre, texte, n=None, font="brush", tringle="bois_fonce"):
    """Rideau noren : tringle + lés séparés, un caractère par lé (texte plus court → centré, lés unis autour).
    Vu de face (depuis -z), +x est à GAUCHE : le premier caractère va sur le lé de plus grand x."""
    n = n or max(2, len(texte))
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


def _enseigne_v(b, x, y0, h, texte, fond, encre, cadre, *, larg=2.0, sortie=0.6, chapeau=None, bras=True):
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
        b.wedge((x - 0.7, y0 + h + 0.3, z_av - 0.6), (x, y0 + h + 0.9, z_ar + 0.4), col(chapeau), down="-x",
                studs="top", collide=False, name="Chapeau")
        b.wedge((x, y0 + h + 0.3, z_av - 0.6), (x + 0.7, y0 + h + 0.9, z_ar + 0.4), col(chapeau), down="+x",
                studs="top", collide=False, name="Chapeau")


def _kanban(b, x, y, w, h, texte, fond, encre, cadre, *, z=0.0, font="brush", ep=0.35):
    """Panneau horizontal (kanban) : cadre sombre et planche à texte devant. Plan avant en z - ep - 0.2."""
    b.box((x - w / 2 - 0.3, y - 0.3, z - ep), (x + w / 2 + 0.3, y + h + 0.3, z + 0.25), col(cadre), name="Cadre")
    p = b.box((x - w / 2, y, z - ep - 0.2), (x + w / 2, y + h, z - ep + 0.05), col(fond), name="Kanban")
    p.label = {"face": "Front", "text": texte, "color": col(encre), "font": font}
    return p


def _koshi(b, xa, xb, y0, y1, bois, fond, *, pas=0.75, neon=False):
    """Treillis de bois (koshi) devant un fond (papier clair ou intérieur sombre) : lisses haute et basse,
    lattes verticales serrées."""
    bois = col(bois)
    kw = {"material": "Neon"} if neon else {}
    b.box((xa, y0 + 0.2, -0.12), (xb, y1 - 0.2, 0.3), col(fond), name="Fond", **kw)
    b.box((xa - 0.1, y0, -0.6), (xb + 0.1, y0 + 0.45, 0.3), bois, studs="top", name="Lisse")
    b.box((xa - 0.1, y1 - 0.45, -0.6), (xb + 0.1, y1, 0.3), bois, name="Lisse")
    n = max(2, int(round((xb - xa) / pas)))
    for i in range(1, n):
        xx = xa + i * (xb - xa) / n
        b.box((xx - 0.15, y0 + 0.45, -0.5), (xx + 0.15, y1 - 0.45, 0.0), bois, name="Latte")


def _mushiko(b, x, y, w, h, mur, *, n=None, fond=INTERIEUR):
    """Fenêtre mushiko-mado : fente sombre barrée de gros barreaux d'enduit, appui et linteau en relief."""
    m = col(mur)
    b.box((x - w / 2, y, -0.12), (x + w / 2, y + h, 0.3), col(fond), name="Fente")
    n = n or max(3, int(round(w / 0.95)))
    for i in range(1, n):
        xx = x - w / 2 + i * w / n
        b.box((xx - 0.22, y, -0.4), (xx + 0.22, y + h, 0.0), m, name="Barreau")
    b.box((x - w / 2 - 0.4, y - 0.45, -0.45), (x + w / 2 + 0.4, y, 0.3), shade(m, 0.93), studs="top", name="Appui")
    b.box((x - w / 2 - 0.4, y + h, -0.45), (x + w / 2 + 0.4, y + h + 0.45, 0.3), shade(m, 0.93), name="Linteau")


def _fenetre_shoji(b, x, y, w, h, cadre, *, lumiere=True, croix=2, appui=True, papier="papier"):
    """Fenêtre à shoji : cadre de bois complet, papier (Neon chaud si éclairée) pris dans le cadre,
    petits bois (kumiko) verticaux et une traverse en retrait (aucune face coplanaire)."""
    cd = col(cadre)
    kw = {"material": "Neon"} if lumiere else {}
    b.box((x - w / 2 - 0.1, y - 0.15, -0.12), (x + w / 2 + 0.1, y + h + 0.15, 0.3),
          col("fenetre_lumiere" if lumiere else papier), name="Shoji", **kw)
    b.box((x - w / 2 - 0.35, y + h, -0.4), (x + w / 2 + 0.35, y + h + 0.4, 0.3), cd, name="Linteau")
    for xx in (x - w / 2 - 0.35, x + w / 2):
        b.box((xx, y, -0.4), (xx + 0.35, y + h, 0.3), cd, name="Montant")
    if appui:
        b.box((x - w / 2 - 0.5, y - 0.4, -0.6), (x + w / 2 + 0.5, y, 0.3), cd, studs="top", name="Appui")
    else:
        b.box((x - w / 2 - 0.35, y - 0.3, -0.4), (x + w / 2 + 0.35, y, 0.3), cd, name="Traverse_basse")
    for i in range(1, croix + 1):
        xx = x - w / 2 + i * w / (croix + 1)
        b.box((xx - 0.1, y, -0.3), (xx + 0.1, y + h, 0.0), cd, name="Kumiko")
    b.box((x - w / 2, y + h * 0.5 - 0.1, -0.24), (x + w / 2, y + h * 0.5 + 0.1, 0.0), cd, name="Kumiko")


def _fenetre_simple(b, x, y, w, h, cadre, *, lumiere=False, papier="papier"):
    """Petite fenêtre de côté (4 pièces) : papier ou lumière, linteau, appui stud, meneau."""
    cd = col(cadre)
    kw = {"material": "Neon"} if lumiere else {}
    b.box((x - w / 2, y - 0.15, -0.12), (x + w / 2, y + h + 0.15, 0.3), col("fenetre_lumiere" if lumiere else papier),
          name="Shoji", **kw)
    b.box((x - w / 2 - 0.35, y + h, -0.4), (x + w / 2 + 0.35, y + h + 0.4, 0.3), cd, name="Linteau")
    b.box((x - w / 2 - 0.35, y - 0.4, -0.5), (x + w / 2 + 0.35, y, 0.3), cd, studs="top", name="Appui")
    b.box((x - 0.12, y, -0.3), (x + 0.12, y + h, 0.0), cd, name="Meneau")


def _fenetre_vitree(b, x, y, w, h, cadre, *, lumiere=False, appui=True):
    """Fenêtre vitrée de l'ère Taishō : cadre de bois, petits carreaux 2 × 3, vitre sombre ou éclairée."""
    cd = col(cadre)
    kw = {"material": "Neon"} if lumiere else {}
    b.box((x - w / 2 - 0.1, y - 0.15, -0.12), (x + w / 2 + 0.1, y + h + 0.15, 0.3),
          col("fenetre_lumiere" if lumiere else "fenetre"), name="Vitre", **kw)
    b.box((x - w / 2 - 0.35, y + h, -0.4), (x + w / 2 + 0.35, y + h + 0.45, 0.3), cd, name="Linteau")
    for xx in (x - w / 2 - 0.35, x + w / 2):
        b.box((xx, y, -0.4), (xx + 0.35, y + h, 0.3), cd, name="Montant")
    if appui:
        b.box((x - w / 2 - 0.55, y - 0.45, -0.65), (x + w / 2 + 0.55, y, 0.3), cd, studs="top", name="Appui")
    else:
        b.box((x - w / 2 - 0.35, y - 0.3, -0.4), (x + w / 2 + 0.35, y, 0.3), cd, name="Traverse_basse")
    for i in (1, 2):
        xx = x - w / 2 + i * w / 3
        b.box((xx - 0.1, y, -0.3), (xx + 0.1, y + h, 0.0), cd, name="Petit_bois")
    b.box((x - w / 2, y + h / 2 - 0.1, -0.24), (x + w / 2, y + h / 2 + 0.1, 0.0), cd, name="Petit_bois")


def _garde_corps(b, xa, xb, y, z, cadre, *, h=2.0, pas=1.6, plein=None):
    """Garde-corps de bois le long de x (plan z) : lisse haute stud, lisse basse plus mince, balustres
    (en retrait des bouts des lisses : aucune face coplanaire)."""
    cd = col(cadre)
    b.box((xa, y + h - 0.35, z - 0.2), (xb, y + h, z + 0.2), cd, studs="top", name="Lisse")
    if plein is not None:
        b.box((xa + 0.1, y, z - 0.08), (xb - 0.1, y + h - 0.35, z + 0.08), col(plein), name="Panneau")
    b.box((xa, y + 0.45, z - 0.11), (xb, y + 0.7, z + 0.11), cd, name="Lisse")
    n = max(1, int(round((xb - xa) / pas)))
    for i in range(n + 1):
        xx = xa + 0.22 + i * (xb - xa - 0.44) / n
        b.box((xx - 0.15, y, z - 0.15), (xx + 0.15, y + h - 0.35, z + 0.15), cd, name="Balustre")


def _sudare(b, x, y_haut, w, h, *, z=-0.5, couleur=SUDARE):
    """Store de bambou (sudare) suspendu devant une baie : panneau et deux liens sombres."""
    b.box((x - w / 2, y_haut - h, z - 0.1), (x + w / 2, y_haut, z + 0.1), col(couleur), collide=False, name="Sudare")
    for xx in (x - w / 3, x + w / 3):
        b.box((xx - 0.1, y_haut - h * 0.85, z - 0.2), (xx + 0.1, y_haut, z - 0.1), col("bois_fonce"), collide=False,
              name="Lien")


def _dango(b, x, y, z):
    """Brochette de dango tricolore posée debout."""
    b.box((x - 0.06, y, z - 0.06), (x + 0.06, y + 2.2, z + 0.06), col("bois_clair"), collide=False, name="Pique")
    for i, cc in enumerate(DANGO[::-1]):
        b.ball((x, y + 0.6 + i * 0.55, z), 0.3, col(cc), collide=False, name="Dango")


# ---------------------------------------------------------------------------
# MACHIYA
# ---------------------------------------------------------------------------

_MACHIYA = [
    # 0 : marchand d'étoffes — enduit blanc, mushiko-mado, enseigne de toit noire et or, ailes udatsu, toit bleu nuit
    dict(toit="tuile", mur="enduit", rdc="bois", cadre="bois_fonce", etage="mushiko", fond="lampion_papier",
         noren=("noren_bleu", "blanc", "呉服"), kanban_toit=("呉服", "noir_laque", "or"),
         verticale=("呉服", "bois_clair", "noir"), udatsu=True, porte="droite", lampion=("lampion_papier", True),
         forme="hirairi", h2=15.6),
    # 1 : apothicaire — étage en planches sombres, baie à treillis avec sudare et garde-corps, toit ardoise
    dict(toit="tuile_ardoise", mur="enduit_creme", rdc="bois", cadre="bois_fonce", etage="sudare", fond=INTERIEUR,
         noren=("noren_violet", "blanc", "薬"), kanban_toit=None, verticale=("薬", "blanc", "noren_rouge"),
         udatsu=False, porte="gauche", lampion=("rouge", False), pied=True, forme="irimoya", h2=15.6),
    # 2 : confiserie — boutique ouverte, étage crème à fenêtres vitrées éclairées, udatsu, lampions rouges
    dict(toit="tuile_claire", mur="enduit_creme", rdc="bois_moyen", cadre="bois_fonce", etage="vitres",
         fond="lampion_papier", noren=("noren_rouge", "blanc", "甘味"), kanban_toit=("茶", "bois_clair", "noir"),
         verticale=("甘味", "noren_rouge", "blanc"), udatsu=True, porte="gauche", lampion=("rouge", False), boutique=True,
         forme="tsumairi", h2=15.0),
    # 3 : soba — étage en encorbellement à balcon et shoji éclairés, toit bleu sombre, noren bleus
    dict(toit="tuile_fonce", mur="enduit", rdc="bois_fonce", cadre="bois_fonce", etage="balcon", fond=INTERIEUR,
         noren=("noren_bleu", "blanc", "蕎麦"), kanban_toit=None, verticale=("蕎麦", "noir_laque", "blanc"),
         udatsu=False, porte="droite", lampion=("orange_lampion", True), forme="kemuri", h2=16.4),
]


def machiya(b, variant=0, largeur=22, profondeur=18):
    """Maison de marchand de l'ère Taishō à deux niveaux : rez en bois sombre à treillis koshi (portes
    coulissantes, inuyarai, noren, lanterne), auvent stud entre les niveaux, étage d'enduit (mushiko-mado,
    sudare, fenêtres vitrées ou balcon), ailes udatsu, enseigne de toit et enseigne verticale ; toit à deux pans
    sur rue (v0), irimoya (v1), pignon sur rue (v2) ou à lanterneau de fumée (v3), débords adoucis."""
    rng = b.rng
    S = _style(_MACHIYA, variant, _ALT)
    W, D = float(largeur), float(profondeur)
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    YS = 0.6                      # socle de pierre
    H1 = 9.0                      # naissance de l'auvent
    HS = H1 + 0.7                 # jonction bois / enduit (cachée sous l'auvent)
    H2 = S["h2"]                  # haut des murs
    PA, PROF_A, EP_A = 0.4, 2.8, 0.6
    KA = EP_A * math.hypot(1, PA)
    YA = H1 + 1.0                 # dessus de l'auvent contre la façade
    cadre = col(S["cadre"])
    mur = S["mur"]

    def sous_auvent(z):           # dessous de l'auvent à la profondeur z (repère de façade)
        return YA + z * PA - KA

    with b.group("Corps"):
        b.box((x0 - 0.2, 0, zf - 0.4), (x1 + 0.2, YS, zb + 0.2), vr("pierre_fonce", rng, 0.03), studs="top", name="Socle")
        b.box((x0, YS, zf), (x1, HS, zb), vr(S["rdc"], rng, 0.03), name="Mur_rdc")
        b.box((x0, HS, zf), (x1, H2 - 0.8, zb), vr(mur, rng, 0.02), name="Mur_etage")
        b.box((x0 - 0.15, H2 - 0.8, zf - 0.15), (x1 + 0.15, H2, zb + 0.15), cadre, name="Sabliere")
        # poteaux d'angle de l'étage (colombage) sur les côtés
        for xa in (x0 - 0.15, x1 - 0.65):
            b.box((xa, HS, zb - 0.65), (xa + 0.8, H2 - 0.8, zb + 0.15), cadre, name="Poteau")

    # --- rez-de-chaussée sur rue ------------------------------------------------------------------------
    wd = min(5.2, W * 0.26)
    if S["porte"] == "droite":
        da, db = x0 + 0.8, x0 + 0.8 + wd
        za0, za1 = db + 0.8, x1 - 0.8
    elif S["porte"] == "gauche":
        da, db = x1 - 0.8 - wd, x1 - 0.8
        za0, za1 = x0 + 0.8, da - 0.8
    with b.group("Facade"), b.at((0, 0, zf)):
        YK = 7.0                                   # dessous du linteau (kamoi)
        posts = sorted({x0 - 0.1, x1 - 0.7, (da - 0.8) if da > x0 + 1 else None, db if db < x1 - 1 else None} - {None})
        b.box((x0, YK, -0.45), (x1, YK + 0.6, 0.3), cadre, name="Kamoi")
        # porte coulissante : un vantail fermé, l'autre ouvert sur l'intérieur sombre ; noren devant
        b.box((da, YS, -0.1), (db, YK, 0.3), col(INTERIEUR), name="Entree")
        hx = (da + db) / 2
        vx0, vx1 = (hx, db - 0.1) if S["porte"] == "droite" else (da + 0.1, hx)
        b.box((vx0, YS, -0.35), (vx1, YK, -0.1), cadre, name="Vantail")
        b.box((vx0 + 0.35, YS + 2.0, -0.45), (vx1 - 0.35, YK - 0.5, -0.35), col("papier"), name="Papier")
        for i in (1, 2):
            xx = vx0 + i * (vx1 - vx0) / 3
            b.box((xx - 0.12, YS + 1.85, -0.6), (xx + 0.12, YK - 0.35, -0.4), cadre, name="Latte")
        b.box((da + 0.4, 0, -1.7), (db - 0.4, 0.4, -0.4), vr("pierre", rng, 0.03), studs="top", name="Marche")
        nf, ne, nt = S["noren"]
        _noren(b, da + 0.15, db - 0.15, YK, 2.9, -0.85, nf, ne, nt, n=len(nt) if len(nt) >= 2 else 3)
        # poteaux
        for xa in posts:
            b.box((xa, YS, -0.3), (xa + 0.8, YA - 0.1, 0.4), cadre, name="Poteau")
        # boutique ouverte ou treillis
        if S.get("boutique"):
            b.box((za0, YS, -0.1), (za1, YK, 0.3), col(INTERIEUR), name="Interieur")
            b.box((za0 + 0.3, YS, -2.0), (za1 - 0.3, 3.0, -0.1), vr("bois", rng, 0.03), name="Comptoir")
            b.box((za0 + 0.1, 3.0, -2.2), (za1 - 0.1, 3.4, -0.1), col("bois_clair"), studs="top", name="Plateau")
            n = max(2, int((za1 - za0) / 1.7))
            for i in range(n):
                xx = za0 + (i + 0.5) * (za1 - za0) / n
                if i % 3 == 0:
                    _dango(b, xx, 3.4, -1.1)
                elif i % 3 == 1:
                    b.cyl((xx, 3.4 + 0.6, -1.1), 0.55, 1.2, vr(THE_VERT, rng, 0.06), axis="y", studs="top", name="Pot_the")
                else:
                    b.box((xx - 0.6, 3.4, -1.7), (xx + 0.6, 4.1, -0.5), col("noir_laque"), studs="top", name="Boite")
            # store de bambou roulé sous le linteau
            b.box((za0, YK - 0.9, -0.75), (za1, YK + 0.05, -0.35), col(SUDARE), name="Store")
        else:
            span = za1 - za0
            cuts = [za0, za1] if span < 10 else [za0, (za0 + za1) / 2 - 0.4, (za0 + za1) / 2 + 0.4, za1]
            panels = [(cuts[i], cuts[i + 1]) for i in range(0, len(cuts), 2)]
            if len(cuts) == 4:
                b.box(((za0 + za1) / 2 - 0.4, YS, -0.3), ((za0 + za1) / 2 + 0.4, YA - 0.1, 0.4), cadre, name="Poteau")
            for (pa, pb) in panels:
                b.wedge((pa, YS, -1.2), (pb, YS + 1.6, 0.2), col(BAMBOU_SEC), down="-z", name="Inuyarai")
                _koshi(b, pa, pb, YS + 1.6, YK, cadre, S["fond"], pas=0.72)
        # auvent (hisashi) et ses consoles
        ya_av = YA - PROF_A * PA
        _pan_z(b, -PROF_A, ya_av, 0.3, YA + 0.3 * PA, x0 - 0.3, x1 + 0.3, EP_A, vr(S["toit"], rng, 0.02), name="Auvent")
        b.box((x0 - 0.3, ya_av - 0.7, -PROF_A - 0.2), (x1 + 0.3, ya_av + 0.08, -PROF_A + 0.06), shade(col(S["toit"]), 0.74),
              name="Rive")
        for xa in posts:
            xc = xa + 0.4
            _pan_z(b, -PROF_A + 0.35, sous_auvent(-PROF_A + 0.35) + 0.15, 0.2, sous_auvent(0.2) + 0.15, xc - 0.22, xc + 0.22,
                   0.55, cadre, studs="none", name="Console")
        # lanterne près de l'entrée
        lc, lneon = S["lampion"]
        xl = (db + 0.3) if S["porte"] == "droite" else (da - 0.3)
        _chochin(b, xl, sous_auvent(-1.9), -1.9, r=0.7, h=1.6, corps=lc, neon=lneon)
        # enseigne verticale
        vt, vf, ve = S["verticale"]
        if S.get("pied"):
            # grande enseigne sur pied, posée sur le trottoir à côté de l'entrée
            xs = (da - 1.6) if S["porte"] == "gauche" else (db + 1.6)
            b.box((xs - 1.1, 0, -3.3), (xs + 1.1, 0.5, -2.1), vr("pierre", rng, 0.03), studs="top", name="Pied")
            b.box((xs - 0.9, 0.5, -2.95), (xs + 0.9, 6.6, -2.45), cadre, name="Cadre")
            p = b.box((xs - 0.7, 1.0, -3.1), (xs + 0.7, 6.2, -2.9), col(vf), name="Enseigne")
            p.label = {"face": "Front", "text": vt, "color": col(ve), "font": "brush", "vertical": True}
            b.wedge((xs - 1.2, 6.6, -3.5), (xs + 1.2, 7.3, -1.95), col(S["toit"]), down="-z", studs="top", name="Chapeau")
        else:
            if S.get("udatsu"):
                # accrochée au nez de l'aile udatsu, au-dessus de l'auvent
                xs = (x1 - 0.45) if S["porte"] == "droite" else (x0 + 0.45)
                _enseigne_v(b, xs, YA + 0.6, 1.8 * len(vt) + 0.4, vt, vf, ve, cadre, larg=1.8, sortie=2.0,
                            chapeau=None, bras=False)
            else:
                # accrochée au poteau d'angle du rez, sous l'auvent
                xs = (x1 - 0.3) if S["porte"] == "droite" else (x0 + 0.3)
                _enseigne_v(b, xs, 2.4, 4.2, vt, vf, ve, cadre, larg=1.8, sortie=0.3, chapeau=None)

    # --- étage sur rue -----------------------------------------------------------------------------------
    with b.group("Etage"), b.at((0, 0, zf)):
        yw = H1 + 2.2
        et = S["etage"]
        ud = S.get("udatsu")
        mx0, mx1 = x0 + (1.0 if ud else 0.7), x1 - (1.0 if ud else 0.7)
        if not ud:
            for xa in (x0 - 0.1, x1 - 0.7):
                b.box((xa, YA - 0.1, -0.3), (xa + 0.8, H2 - 0.8, 0.3), cadre, name="Poteau")
        kt = S["kanban_toit"]
        kw_ = min(8.0, W * 0.36) if kt else 0.0
        if et == "mushiko":
            if kt:
                xs_f = [-(kw_ / 2 + 0.6 + (mx1 - kw_ / 2 - 0.6 - 0.5) / 2) * s for s in (1, -1)]
                wf = min(5.0, mx1 - kw_ / 2 - 1.6)
            else:
                n = 3 if W >= 20 else 2
                xs_f = [mx0 + (i + 0.5) * (mx1 - mx0) / n for i in range(n)]
                wf = min(4.6, (mx1 - mx0) / n - 1.6)
            for xx in xs_f:
                _mushiko(b, xx, yw, wf, 2.2, mur)
        elif et == "sudare":
            # étage habillé de planches sombres : baie à treillis, sudare et garde-corps
            b.box((x0 + 0.7, HS, -0.15), (x1 - 0.7, H2 - 0.8, 0.3), vr("bois", rng, 0.03), name="Planches")
            bw = min(12.0, W - 6.0)
            with b.at((0, 0, -0.15)):
                n3 = 3
                for i in range(n3):
                    xx = -bw / 2 + (i + 0.5) * bw / n3
                    _fenetre_shoji(b, xx, yw - 0.6, bw / n3 - 0.75, 3.6, cadre, lumiere=(i != 1), croix=2, appui=False)
                _sudare(b, 0, yw + 3.05, bw - 0.4, 2.2, z=-0.5)
                _garde_corps(b, -bw / 2 - 0.4, bw / 2 + 0.4, yw - 0.95, -1.3, cadre, h=1.5, pas=1.6)
                b.box((-bw / 2 - 0.6, yw - 1.25, -1.6), (bw / 2 + 0.6, yw - 0.95, 0.3), cadre, studs="top", name="Plancher")
                for xx in (-W / 2 + 2.3, W / 2 - 2.3):
                    if abs(xx) > bw / 2 + 2.0:
                        _fenetre_shoji(b, xx, yw + 0.2, 1.6, 2.4, cadre, lumiere=False, croix=1, appui=True)
        elif et == "vitres":
            n = 2 if kt else (3 if W >= 20 else 2)
            if kt:
                xs_f = [-(kw_ / 2 + 0.6 + (mx1 - kw_ / 2 - 0.6 - 0.5) / 2) * s for s in (1, -1)]
                wf = min(3.6, mx1 - kw_ / 2 - 2.0)
            else:
                xs_f = [mx0 + (i + 0.5) * (mx1 - mx0) / n for i in range(n)]
                wf = min(3.6, (mx1 - mx0) / n - 1.6)
            for i, xx in enumerate(xs_f):
                _fenetre_vitree(b, xx, yw, wf, 2.8, cadre, lumiere=(i % 2 == 0))
        else:  # balcon en encorbellement, shoji éclairés
            bw = W - 3.0
            b.box((-bw / 2, YA - 0.2, -1.8), (bw / 2, YA + 0.4, 0.3), cadre, studs="top", name="Plancher")
            n = max(3, int(round(bw / 4.2)))
            for i in range(n):
                xx = -bw / 2 + 0.6 + (i + 0.5) * (bw - 1.2) / n
                _fenetre_shoji(b, xx, YA + 0.45, (bw - 1.2) / n - 0.9, 3.6, cadre, lumiere=(i != 1), croix=2, appui=False)
            _garde_corps(b, -bw / 2, bw / 2, YA + 0.4, -1.6, "bois_moyen", h=1.6, pas=1.4)
            for xx in (-bw / 2 + 0.1, bw / 2 - 0.5):
                b.box((xx, YA + 0.4, -1.6), (xx + 0.4, YA + 1.5, -0.1), col("bois_moyen"), name="Retour")
        # ailes udatsu : murs d'enduit en saillie sur l'auvent, coiffés d'un petit toit
        if ud:
            for xa in (x0, x1 - 0.9):
                ytop = H2 - 2.0
                y_hi = YA + 0.3 * PA - 0.15                       # dessus de l'auvent contre le mur, moins 0,15
                y_lo = y_hi - 2.4 * PA                            # même pente, au nez de l'aile
                mu = vr(mur, rng, 0.02)
                b.wedge_under((xa, y_lo - 0.12, -2.1), (xa + 0.9, y_hi, 0.0), mu, down="+z", name="Udatsu")
                b.box((xa, y_hi, -2.1), (xa + 0.9, ytop, 0.0), mu, name="Udatsu")
                b.box((xa - 0.1, ytop - 0.6, -2.2), (xa + 1.0, ytop, 0.0), cadre, name="Udatsu")
                b.wedge((xa - 0.45, ytop, -2.5), (xa + 0.45, ytop + 0.7, 0.3), col(S["toit"]), down="-x", studs="top",
                        name="Udatsu_toit")
                b.wedge((xa + 0.45, ytop, -2.5), (xa + 1.35, ytop + 0.7, 0.3), col(S["toit"]), down="+x", studs="top",
                        name="Udatsu_toit")
        # enseigne de toit (yane-kanban), posée sur l'auvent par deux pieds
        if kt:
            t_, f_, e_ = kt
            yk = YA + 0.5
            for xx in (-kw_ / 2 + 1.0, kw_ / 2 - 1.0):
                b.box((xx - 0.25, sous_auvent(-1.45) + KA - 0.3, -1.6), (xx + 0.25, yk, -1.1), cadre, name="Pied")
            _kanban(b, 0, yk + 0.3, kw_, 2.3, t_, f_, e_, cadre, z=-1.1, ep=0.35)
            b.wedge((-kw_ / 2 - 0.7, yk + 2.85, -2.1), (kw_ / 2 + 0.7, yk + 3.5, -1.0), col(S["toit"]), down="-z",
                    studs="top", name="Kanban_toit")
            b.wedge((-kw_ / 2 - 0.7, yk + 2.85, -1.0), (kw_ / 2 + 0.7, yk + 3.5, 0.1), col(S["toit"]), down="+z",
                    studs="top", name="Kanban_toit")

    # --- côtés et arrière ----------------------------------------------------------------------------------
    with b.group("Cotes"):
        for side in (-1, 1):
            with b.at((x1 if side > 0 else x0, 0, 0), yaw=-90 * side):
                zc = (zb - 4.0) * side
                _mushiko(b, zc, H1 + 2.6, 2.4, 1.8, mur, n=3)
                b.box((-D / 2 + 0.2, HS - 0.4, -0.25), (D / 2 - 0.2, HS + 0.2, 0.3), cadre, name="Bandeau")
                # mur à colombage apparent : poteau au milieu de l'étage, couvre-joints sur les planches du rez
                b.box((-0.35, HS + 0.2, -0.22), (0.35, H2 - 0.8, 0.3), cadre, name="Poteau")
                for lx in (-D / 4, 0.0, D / 4):
                    b.box((lx - 0.14, YS + 0.2, -0.12), (lx + 0.14, HS - 0.45, 0.2), shade(col(S["rdc"]), 0.78),
                          name="Couvre_joint")
        with b.at((0, 0, zb), yaw=180):
            _fenetre_shoji(b, W / 5, H1 + 2.4, 4.0, 2.4, cadre, lumiere=False, croix=2)
            b.box((-W / 4 - 1.4, YS, -0.12), (-W / 4 + 1.4, 7.0, 0.3), cadre, name="Porte")
            b.box((-W / 4 - 1.9, 7.0, -0.4), (-W / 4 + 1.9, 7.5, 0.3), cadre, name="Linteau")

    # --- toit ----------------------------------------------------------------------------------------------
    with b.group("Toit"):
        forme = S["forme"]
        if forme == "irimoya":
            R = _toit_irimoya(b, x0 - 0.6, x1 + 0.6, zf - 2.4, zb + 1.2, H2, S["toit"], a_z0=4.4, a_z1=3.2, a_x0=3.6,
                              a_x1=3.6, h1=1.6, h2=0.55 * (D / 2 - 2.0), tri=mur, rng=rng, gegyo=S["cadre"])
            top = R["top"]
        elif forme == "tsumairi":
            top = _toit_tsumairi(b, x0, x1, zf, zb, H2, 0.5, S["toit"], mur, deb=0.7, deb_av=2.2, deb_ar=1.0, ep=0.8,
                                 sori=0.5, hafu=None, gegyo="or", rng=rng)
            # poutre de base et fenêtre du pignon
            with b.at((0, 0, zf)):
                b.box((x0 + 0.3, H2 + 0.05, -0.35), (x1 - 0.3, H2 + 0.55, 0.1), cadre, name="Tsuma_poutre")
                _mushiko(b, 0, H2 + 1.6, 3.2, 1.5, mur, n=4)
        else:
            top, _ = _toit_hirairi(b, x0, x1, zf, zb, H2, 0.42, S["toit"], mur, deb_av=2.4, deb_ar=1.2, deb_cote=0.6,
                                   ep=0.8, sori=0.5, rng=rng)
            if forme == "kemuri":
                # lanterneau de fumée (kemuri-dashi) sur le faîtage : petite cage de bois coiffée d'un toit
                zm = (zf + zb) / 2
                yr = H2 + (zm - zf) * 0.42 + 0.8 * math.hypot(1, 0.42)
                b.box((-1.7, yr - 0.4, zm - 1.3), (1.7, yr + 1.6, zm + 1.3), cadre, name="Kemuri")
                for xx in (-0.85, 0.0, 0.85):
                    b.box((xx - 0.18, yr + 0.85, zm - 1.45), (xx + 0.18, yr + 1.45, zm + 1.45), col(INTERIEUR), name="Kemuri_fente")
                b.box((-2.3, yr + 1.6, zm - 2.0), (2.3, yr + 1.9, zm + 2.0), shade(col(S["toit"]), 0.72), name="Rive")
                b.wedge((-2.3, yr + 1.9, zm - 2.0), (2.3, yr + 2.8, zm), col(S["toit"]), down="-z", studs="top", name="Kemuri_toit")
                b.wedge((-2.3, yr + 1.9, zm), (2.3, yr + 2.8, zm + 2.0), col(S["toit"]), down="+z", studs="top", name="Kemuri_toit")
                b.box((-2.5, yr + 2.6, zm - 0.5), (2.5, yr + 3.1, zm + 0.5), shade(col(S["toit"]), 0.72), studs="top",
                      name="Faitage")
                top = max(top, yr + 3.1)
    return {"emprise": (W, D), "hauteur": round(top, 2)}


# ---------------------------------------------------------------------------
# AUBERGE (ryokan)
# ---------------------------------------------------------------------------

_AUBERGES = [
    # 0 : grand ryokan blanc et bois sombre, irimoya bleu nuit, porche kara-hafu laqué noir, noren 藤, lampions chauds
    dict(toit="tuile", mur="enduit", rdc="bois", cadre="bois_fonce", garde="bois_fonce", porche="kara", hafu="bois_clair",
         poteau="bois_fonce", noren=("noren_violet", "blanc", "藤"), enseigne=("宿", "noir_laque", "or"),
         lampion=("orange_lampion", True), tour=False),
    # 1 : ryokan de source chaude tout en bois, irimoya ardoise, porche à pignon treillissé, enseigne verticale
    dict(toit="tuile_ardoise", mur="bois_moyen", rdc="bois", cadre="bois_fonce", garde="bois_fonce", porche="pignon",
         hafu="bois_fonce", poteau="bois_fonce", noren=("noren_bleu", "blanc", "宿"), enseigne=("宿", "bois_clair", "noir"),
         lampion=("lampion_papier", True), tour=False, verticale=True, forme="hirairi", chidori="bois_clair"),
    # 2 : ryokan crème à tour de guet, toits de cuivre patiné, porche kara-hafu, lampions rouges
    dict(toit="cuivre_vert", mur="enduit_creme", rdc="bois", cadre="bois_fonce", garde="bois_fonce", porche="kara",
         hafu="bois_fonce", poteau="bois_fonce", noren=("noren_rouge", "blanc", "宿"), enseigne=("宿", "noir_laque", "blanc"),
         lampion=("rouge", False), tour=True),
    # 3 : quartier des fleurs : garde-corps et poteaux vermillon, toit bleu sombre, lanternes blanches
    dict(toit="tuile_fonce", mur="enduit", rdc="bois_fonce", cadre="bois_fonce", garde="vermillon", porche="kara",
         hafu="vermillon_fonce", poteau="vermillon", noren=("noren_violet", "blanc", "藤"), enseigne=("宿", "vermillon", "blanc"),
         lampion=("lampion_papier", True), tour=False, chidori="or"),
]


def _fenetre_ronde(b, x, y, r, cadre, *, lumiere=False):
    """Fenêtre ronde (maru-mado) : disque de bois, papier en saillie (Neon si éclairé), croisillon."""
    b.cyl((x, y, -0.05), r + 0.35, 0.5, col(cadre), axis="z", name="Maru_mado")
    kw = {"material": "Neon"} if lumiere else {}
    b.cyl((x, y, -0.2), r, 0.5, col("fenetre_lumiere" if lumiere else "lampion_papier"), axis="z", name="Maru_mado", **kw)
    b.box((x - 0.1, y - r + 0.05, -0.62), (x + 0.1, y + r - 0.05, -0.4), col(cadre), name="Croisillon")
    b.box((x - r + 0.05, y - 0.1, -0.56), (x + r - 0.05, y + 0.1, -0.4), col(cadre), name="Croisillon")


def auberge(b, variant=0, largeur=28, profondeur=24):
    """Ryokan de l'ère Taishō à trois niveaux : rez à treillis et fenêtres rondes, grand porche central à fronton
    courbe (kara-hafu) ou à pignon, balcons de bois à garde-corps au 1er étage, shoji éclairés, auvent stud,
    galerie au 2e étage, lanternes, grande enseigne 宿, toit irimoya (tour de guet en variante 2)."""
    rng = b.rng
    S = _style(_AUBERGES, variant, _ALT)
    W, D = float(largeur), float(profondeur)
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    RET = 2.6                              # retrait de la façade : balcons et porche restent dans l'emprise
    zA = zf + RET
    YS = 0.8
    H1, H2, H3 = 8.6, 15.6, 21.4           # planchers des étages, haut des murs
    cadre = col(S["cadre"])
    mur = S["mur"]
    garde = S["garde"]
    wp = min(9.2, W * 0.34)                # largeur du porche
    q = (W / 2 - wp / 2) / 2
    posts = [x0, -wp / 2 - q, -wp / 2, wp / 2, wp / 2 + q, x1]
    baies = [(posts[i], posts[i + 1]) for i in range(5)]
    PA, EP_A = 0.42, 0.6
    KA = EP_A * math.hypot(1, PA)
    YP = H2 + 0.9                          # dessus de l'auvent contre la façade

    def sous_auvent(z):                    # dessous de l'auvent (repère de façade, z = 0 en zA)
        return YP + z * PA - KA

    with b.group("Corps"):
        b.box((x0 - 0.3, 0, zf + 0.2), (x1 + 0.3, YS, zb + 0.3), vr("pierre", rng, 0.03), studs="top", name="Socle")
        b.box((x0, YS, zA), (x1, H1, zb), vr(S["rdc"], rng, 0.03), name="Mur_rdc")
        b.box((x0, H1 + 0.6, zA), (x1, H2 - 0.3, zb), vr(mur, rng, 0.02), name="Mur_1")
        b.box((x0, H2 + 0.4, zA), (x1, H3 - 0.8, zb), vr(mur, rng, 0.02), name="Mur_2")
        for (ya, yb_) in ((H1 - 0.1, H1 + 0.6), (H2 - 0.3, H2 + 0.4), (H3 - 0.8, H3)):
            b.box((x0 - 0.2, ya, zA - 0.2), (x1 + 0.2, yb_, zb + 0.2), cadre, name="Bandeau")
        # poteaux d'angle (arrière) des étages
        for xa in (x0 - 0.15, x1 - 0.65):
            b.box((xa, H1 + 0.6, zb - 0.65), (xa + 0.8, H3 - 0.8, zb + 0.15), cadre, name="Poteau")

    # --- rez-de-chaussée ----------------------------------------------------------------------------
    with b.group("Rez"), b.at((0, 0, zA)):
        YL = H1 - 1.4
        b.box((x0 + 0.1, YL, -0.45), (x1 - 0.1, YL + 0.6, 0.3), cadre, name="Linteau")
        for i, xp in enumerate(posts):
            xa = xp - 0.1 if i == 0 else (xp - 0.7 if i == 5 else xp - 0.4)
            b.box((xa, YS, -0.35), (xa + 0.8, H1, 0.3), cadre, name="Poteau")
        for i, (a, c_) in enumerate(baies):
            xa, xb = a + (0.7 if i == 0 else 0.4), c_ - (0.7 if i == 4 else 0.4)
            if i == 2:
                # entrée : portes vitrées à petits bois sur fond de papier, noren
                b.box((xa, YS, -0.12), (xb, YL, 0.3), col("lampion_papier"), name="Portes")
                n = 4
                for k in range(n + 1):
                    xx = xa + k * (xb - xa) / n
                    b.box((xx - 0.18, YS, -0.4), (xx + 0.18, YL, 0.0), cadre, name="Montant")
                for yy in (YS + 1.6, YL - 1.8):
                    b.box((xa, yy - 0.12, -0.32), (xb, yy + 0.12, 0.0), cadre, name="Traverse")
                nf, ne, nt = S["noren"]
                _noren(b, xa + 0.5, xb - 0.5, YL, 2.6, -0.6, nf, ne, nt, n=3)
            elif i in (1, 3):
                b.wedge((xa, YS, -1.1), (xb, YS + 1.5, 0.2), col(BAMBOU_SEC), down="-z", name="Inuyarai")
                _koshi(b, xa, xb, YS + 1.5, YL, cadre, "lampion_papier", pas=0.72)
            else:
                _fenetre_ronde(b, (xa + xb) / 2, (YS + YL) / 2 + 0.3, min(1.7, (xb - xa) / 2 - 0.6), cadre,
                               lumiere=(i == 4))
        b.box((-wp / 2 + 0.6, 0, -RET + 0.2), (wp / 2 - 0.6, 0.5, -RET - 0.6), vr("pierre_claire", rng, 0.03), studs="top",
              name="Marche")
        if S.get("verticale"):
            et, ef, ee = S["enseigne"]
            _enseigne_v(b, x1 - 0.3, 2.2, 4.4, et, ef, ee, cadre, larg=2.0, sortie=0.3)

    # --- porche ----------------------------------------------------------------------------------------
    with b.group("Porche"):
        Yb = 8.0
        zpo = zf - 0.2                      # axe des poteaux avant
        poteau = col(S["poteau"])
        xpo = wp / 2 - 0.5
        for s in (-1, 1):
            b.box((s * xpo - 0.75, 0, zpo - 0.75), (s * xpo + 0.75, 0.6, zpo + 0.75), vr("pierre_claire", rng, 0.03),
                  studs="top", name="Base")
            b.box((s * xpo - 0.45, 0.6, zpo - 0.45), (s * xpo + 0.45, Yb, zpo + 0.45), poteau, name="Poteau")
            b.box((s * xpo - 0.3, Yb - 0.75, zpo - 0.3), (s * xpo + 0.3, Yb - 0.05, zA + 0.2), poteau, name="Longrine")
        za_p = zf - 1.1
        b.box((-wp / 2 - 0.3, Yb - 0.9, za_p + 0.05), (wp / 2 + 0.3, Yb, zpo + 0.35), poteau, name="Koryo")
        if S["porche"] == "kara":
            larg, hk = wp + 1.8, 3.2
            y0 = Yb + 0.15
            _, dessus = _kara_hafu(b, 0, za_p, zA + 0.3, y0, larg, hk, S["toit"], S["hafu"], ep=0.7, rng=rng)
            # tympan d'enduit sous la courbe (caché en haut par la planche), ornement doré (kaeru-mata)
            hw = larg / 2
            tm = vr(mur, rng, 0.02)
            b.box((-0.2 * hw, Yb, za_p + 0.3), (0.2 * hw, dessus(0.2) - 0.55, za_p + 0.8), tm, name="Tympan")
            for s_ in (-1, 1):
                xa_, xb_ = sorted((s_ * 0.2 * hw, s_ * 0.46 * hw))
                b.box((xa_, Yb, za_p + 0.3), (xb_, dessus(0.46) - 0.55, za_p + 0.8), tm, name="Tympan")
            b.wedge((-1.1, Yb, za_p + 0.1), (0.0, Yb + 1.3, za_p + 0.45), col("or"), down="-x", name="Kaeru_mata")
            b.wedge((0.0, Yb, za_p + 0.1), (1.1, Yb + 1.3, za_p + 0.45), col("or"), down="+x", name="Kaeru_mata")
        else:
            _toit_tsumairi(b, -wp / 2, wp / 2, zpo - 0.4, zA, Yb, 0.62, S["toit"], S["cadre"], deb=0.9, deb_av=0.6,
                           deb_ar=0.0, ep=0.7, hafu=S["hafu"], gegyo="or", rng=rng, treillis="bois_clair",
                           pignon_z=(zpo - 0.4, zpo + 0.6))
        lc, ln = S["lampion"]
        for s in (-1, 1):
            _chochin(b, s * (xpo - 1.3), Yb - 0.9, zpo, r=0.75, h=1.7, corps=lc, neon=ln)

    # --- 1er étage : balcons, shoji éclairés, enseigne ----------------------------------------------------
    with b.group("Etage1"), b.at((0, 0, zA)):
        xl = wp / 2 + 1.1                  # les balcons s'arrêtent avant le porche
        for s in (-1, 1):
            xa, xb = sorted((s * xl, s * (W / 2)))
            b.box((xa, H1, -RET + 0.25), (xb, H1 + 0.8, 0.3), vr("bois_moyen", rng, 0.03), studs="top", name="Balcon")
            _garde_corps(b, xa + 0.15, xb - 0.15, H1 + 0.8, -RET + 0.45, garde, h=1.9, pas=1.5)
            xr = xa + 0.15 if s > 0 else xb - 0.15
            b.box((xr - 0.15, H1 + 0.8, -RET + 0.6), (xr + 0.15, H1 + 2.55, 0.0), col(garde), studs="top", name="Retour")
            for xp in posts:
                if xa - 0.1 <= xp <= xb + 0.1:
                    xc = min(max(xp, xa + 0.3), xb - 0.3)
                    b.box((xc - 0.3, H1 - 0.9, -RET + 0.5), (xc + 0.3, H1, 0.2), cadre, name="Console")
        for i, xp in enumerate(posts):
            if i in (2, 3):
                continue
            xa = xp - 0.1 if i == 0 else (xp - 0.7 if i == 5 else xp - 0.4)
            b.box((xa, H1 + 0.6, -0.3), (xa + 0.8, H2 - 0.3, 0.3), cadre, name="Poteau")
        for i, (a, c_) in enumerate(baies):
            if i == 2:
                continue
            xa, xb = a + (0.7 if i == 0 else 0.4), c_ - (0.7 if i == 4 else 0.4)
            _fenetre_shoji(b, (xa + xb) / 2, H1 + 1.0, xb - xa - 0.9, 4.6, cadre, lumiere=(i in (1, 4)), croix=3, appui=False)
        et, ef, ee = S["enseigne"]
        _kanban(b, 0, H1 + 3.4, wp - 2.6, 3.0, et, ef, ee, cadre, ep=0.4)
        # lanternes sous l'auvent, devant les garde-corps
        lc, ln = S["lampion"]
        for xx in (-(wp / 2 + q), wp / 2 + q, -(W / 2 - 1.4), W / 2 - 1.4):
            _chochin(b, xx, sous_auvent(-RET + 0.15), -RET + 0.15, r=0.6, h=1.4, corps=lc, neon=ln)
        # auvent au-dessus du balcon
        ya_av = YP - (RET + 0.5) * PA
        _pan_z(b, -RET - 0.5, ya_av, 0.3, YP + 0.3 * PA, x0 - 0.3, x1 + 0.3, EP_A, vr(S["toit"], rng, 0.02), name="Auvent")
        b.box((x0 - 0.3, ya_av - 0.7, -RET - 0.7), (x1 + 0.3, ya_av + 0.08, -RET - 0.44), shade(col(S["toit"]), 0.74),
              name="Rive")

    # --- 2e étage : galerie à garde-corps, shoji ----------------------------------------------------------
    with b.group("Etage2"), b.at((0, 0, zA)):
        yg = YP + 0.15
        b.box((x0 + 0.2, yg - 0.35, -1.2), (x1 - 0.2, yg, 0.3), cadre, studs="top", name="Galerie")
        _garde_corps(b, x0 + 0.35, x1 - 0.35, yg, -1.0, garde, h=1.3, pas=2.3)
        for i, xp in enumerate(posts):
            xa = xp - 0.1 if i == 0 else (xp - 0.7 if i == 5 else xp - 0.4)
            b.box((xa, H2 + 0.4, -0.3), (xa + 0.8, H3 - 0.8, 0.3), cadre, name="Poteau")
        for i, (a, c_) in enumerate(baies):
            xa, xb = a + (0.7 if i == 0 else 0.4), c_ - (0.7 if i == 4 else 0.4)
            _fenetre_shoji(b, (xa + xb) / 2, yg + 0.5, xb - xa - 1.0, 2.9, cadre, lumiere=(i in (0, 2, 3)),
                           croix=3 if i == 2 else 2, appui=False)

    # --- côtés et arrière -------------------------------------------------------------------------------
    with b.group("Cotes"):
        for side in (-1, 1):
            with b.at((x1 if side > 0 else x0, 0, 0), yaw=-90 * side):
                for k, (yy, hh) in enumerate(((YS + 2.6, 3.0), (H1 + 1.8, 3.0), (H2 + 1.6, 2.6))):
                    for zc in ((zA + 4.5) * side, (zb - 4.5) * side):
                        _fenetre_simple(b, zc, yy, 3.0, hh, cadre, lumiere=((k + int(zc > 0) + side) % 3 == 0))
                zmid = ((zA + 4.5) + (zb - 4.5)) / 2 * side
                b.box((zmid - 0.4, YS, -0.25), (zmid + 0.4, H3 - 0.8, 0.3), cadre, name="Poteau")
        with b.at((0, 0, zb), yaw=180):
            for yy in (H1 + 1.8, H2 + 1.6):
                for xc in (-W / 4, W / 4):
                    _fenetre_simple(b, xc, yy, 4.0, 2.6, cadre, lumiere=(xc < 0 and yy > H2))
            b.box((-1.6, YS, -0.12), (1.6, 7.0, 0.3), cadre, name="Porte")

    # --- toit ------------------------------------------------------------------------------------------------
    with b.group("Toit"):
        dav, dar, dco = 2.6, 1.3, 1.2
        wc = min(10.0, wp + 1.2)                   # largeur du fronton chidori-hafu
        if S.get("forme") == "hirairi":
            pente = 0.5
            top, _ = _toit_hirairi(b, x0, x1, zA, zb, H3, pente, S["toit"], mur, deb_av=dav, deb_ar=dar, deb_cote=dco,
                                   ep=0.9, sori=0.5, rng=rng)
            zc_ = zA + 1.4
            ys = H3 + (zc_ - zA) * pente + 0.9 * math.hypot(1, pente)
        else:
            R = _toit_irimoya(b, x0 - dco, x1 + dco, zA - dav, zb + dar, H3, S["toit"], a_z0=dav + 2.0, a_z1=dar + 2.0,
                              a_x0=dco + 3.2, a_x1=dco + 3.2, h1=2.2, h2=0.62 * ((zb - zA) / 2 - 2.0),
                              tri=mur, rng=rng, gegyo=S["cadre"])
            top = R["top"]
            zc_ = R["zi0"] + 0.6
            ys = R["ya"] + 0.6 * R["pente"]
        if S.get("chidori"):
            # fronton triangulaire (chidori-hafu) posé sur le pan avant, au-dessus du porche
            t2 = _toit_tsumairi(b, -wc / 2, wc / 2, zc_, zc_ + 7.0, ys - 0.3, 0.6, S["toit"], mur, deb=0.9, deb_av=1.3,
                                deb_ar=0.0, ep=0.8, sori=0.5, hafu=S["hafu"], gegyo="or", rng=rng,
                                treillis=S["chidori"], pignon_z=(zc_, zc_ + 4.0))
            top = max(top, t2)
        if S["tour"]:
            # tour de guet (bōrō) sur le faîtage : chambre vitrée éclairée, petit toit irimoya
            tw, tdp = 7.0, 6.0
            zc = R["zm"]
            yb_ = R["yr"] - 1.6
            yt_ = R["yr"] + 4.6
            b.box((-tw / 2, yb_, zc - tdp / 2), (tw / 2, yt_, zc + tdp / 2), vr(mur, rng, 0.02), name="Tour")
            b.box((-tw / 2 - 0.2, yt_ - 0.6, zc - tdp / 2 - 0.2), (tw / 2 + 0.2, yt_, zc + tdp / 2 + 0.2), cadre, name="Sabliere")
            b.box((-tw / 2 - 0.2, R["yr"] + 0.6, zc - tdp / 2 - 0.2), (tw / 2 + 0.2, R["yr"] + 1.0, zc + tdp / 2 + 0.2), cadre,
                  studs="top", name="Bandeau")
            with b.at((0, 0, zc - tdp / 2)):
                for xx in (-1.7, 1.7):
                    _fenetre_shoji(b, xx, R["yr"] + 1.4, 2.4, 2.2, cadre, lumiere=True, croix=1, appui=False)
            for side in (-1, 1):
                with b.at((side * tw / 2, 0, zc), yaw=-90 * side):
                    _fenetre_shoji(b, 0, R["yr"] + 1.4, 2.6, 2.2, cadre, lumiere=False, croix=1, appui=False)
            R2 = _toit_irimoya(b, -tw / 2 - 1.2, tw / 2 + 1.2, zc - tdp / 2 - 1.2, zc + tdp / 2 + 1.2, yt_, S["toit"],
                               a_z0=2.2, a_z1=2.2, a_x0=2.2, a_x1=2.2, h1=1.0, h2=1.8, tri=mur, rng=rng, gegyo="or", oni=False)
            b.cyl((0, R2["yr"] + 1.0, R2["zm"]), 0.25, 0.8, col("or"), axis="y", name="Epi")
            b.ball((0, R2["yr"] + 1.6, R2["zm"]), 0.42, col("or"), name="Hoju")
            top = max(top, R2["yr"] + 2.0)
    return {"emprise": (W, D), "hauteur": round(top, 2)}


# ---------------------------------------------------------------------------
# SANCTUAIRE (haiden)
# ---------------------------------------------------------------------------

_SANCTUAIRES = [
    # 0 : pavillon de bois naturel sous un grand toit d'ardoise à pignon sur l'avant (comme la référence)
    dict(toit="tuile_ardoise", poteau="bois_moyen", poutre="bois_fonce", garde="vermillon_fonce", mur="enduit",
         fronton="noir_laque", treillis="bois_moyen", hafu="tuile_fonce", sol="bois_moyen", kohai=None, lanterne="pierre"),
    # 1 : sanctuaire vermillon, toit de cuivre patiné, auvent kara-hafu au-dessus de l'escalier
    dict(toit="cuivre_vert", poteau="vermillon", poutre="vermillon", garde="vermillon", mur="enduit",
         fronton="vermillon_fonce", treillis="or", hafu="vermillon_fonce", sol="bois_moyen", kohai="kara",
         lanterne="pierre_claire"),
    # 2 : laque noire et or, toit bleu nuit, auvent à pignon treillissé
    dict(toit="tuile", poteau="noir_laque", poutre="noir_laque", garde="noir_laque", mur="enduit", fronton="noir_laque",
         treillis="or", hafu="noir_laque", sol="bois", kohai="pignon", lanterne="pierre"),
    # 3 : sanctuaire de montagne en bois clair, toit bleu sombre, grosse corde shimenawa
    dict(toit="tuile_fonce", poteau="bois_clair", poutre="bois_moyen", garde="bois_moyen", mur="enduit_creme",
         fronton="bois_moyen", treillis="bois_clair", hafu="bois_fonce", sol="bois_clair", kohai=None,
         lanterne="pierre_fonce", grosse_corde=True),
]


def _shide(b, x, y_haut, z, n=4, w=0.5, hh=0.48):
    """Papier shide en zigzag : n petits rectangles blancs décalés à gauche et à droite (épaisseurs alternées :
    pas de faces coplanaires)."""
    for i in range(n):
        dx = 0.17 if i % 2 else -0.17
        e = 0.05 if i % 2 else 0.07
        b.box((x + dx - w / 2, y_haut - (i + 1) * hh, z - e), (x + dx + w / 2, y_haut - i * hh + 0.03, z + e), col("shide"),
              collide=False, name="Shide")


def _corde(b, xa, ya, xb, yb, z, r, couleur, name="Shimenawa"):
    """Segment de corde (cylindre incliné dans le plan XY) entre (xa, ya) et (xb, yb)."""
    L = math.hypot(xb - xa, yb - ya)
    ang = math.degrees(math.atan2(yb - ya, xb - xa))
    return b.part("cyl", (L, 2 * r, 2 * r), ((xa + xb) / 2, (ya + yb) / 2, z), rot_z(ang), col(couleur), collide=False,
                  name=name)


def _toro(b, x, z, pierre="pierre", *, lumiere=True, h=1.0):
    """Lanterne de pierre (tōrō) : socle, fût, plateau, foyer éclairé, toit à deux gradins, joyau."""
    p = col(pierre)
    b.box((x - 0.9 * h, 0, z - 0.9 * h), (x + 0.9 * h, 0.5 * h, z + 0.9 * h), shade(p, 0.95), studs="top", name="Toro_socle")
    b.cyl((x, 0.45 * h + 1.15 * h, z), 0.4 * h, 2.3 * h, p, axis="y", name="Toro_fut")
    y = 2.7 * h
    b.box((x - 0.8 * h, y, z - 0.8 * h), (x + 0.8 * h, y + 0.45 * h, z + 0.8 * h), p, studs="top", name="Toro_plateau")
    y += 0.45 * h
    b.box((x - 0.55 * h, y, z - 0.55 * h), (x + 0.55 * h, y + 1.1 * h, z + 0.55 * h), shade(p, 1.04), name="Toro_foyer")
    kw = {"material": "Neon"} if lumiere else {}
    b.box((x - 0.3 * h, y + 0.25 * h, z - 0.65 * h), (x + 0.3 * h, y + 0.85 * h, z + 0.65 * h),
          col("orange_lampion" if lumiere else "noir"), name="Toro_feu", **kw)
    y += 1.1 * h
    b.box((x - 1.0 * h, y, z - 1.0 * h), (x + 1.0 * h, y + 0.35 * h, z + 1.0 * h), shade(p, 0.92), studs="top", name="Toro_toit")
    b.box((x - 0.6 * h, y + 0.35 * h, z - 0.6 * h), (x + 0.6 * h, y + 0.7 * h, z + 0.6 * h), shade(p, 0.92), studs="top",
          name="Toro_toit")
    b.ball((x, y + 0.95 * h, z), 0.32 * h, shade(p, 0.92), name="Toro_joyau")
    return y + 1.3 * h


def sanctuaire(b, variant=0):
    """Pavillon de culte (haiden) d'environ 28 × 24 × 22 : socle de pierre, plancher surélevé et véranda à
    garde-corps, large escalier central, piliers ronds et consoles, portes à treillis, rideau violet, grand toit
    irimoya à pignon sur l'avant (fronton à treillis, planches de rive, gegyo doré), cloche et sa corde,
    tronc à offrandes, shimenawa avec papiers shide, deux lanternes de pierre ; auvent kara-hafu ou à pignon
    au-dessus de l'escalier selon la variante."""
    rng = b.rng
    S = _style(_SANCTUAIRES, variant, {"toit": ["tuile_ardoise", "cuivre_vert", "tuile", "tuile_fonce"]})
    poteau, poutre, garde = col(S["poteau"]), col(S["poutre"]), col(S["garde"])
    mur = S["mur"]
    PX, PZ0, PZ1 = 13.0, -7.4, 11.6        # socle de pierre (kidan)
    YS, YF = 1.6, 4.0                      # dessus du socle, dessus du plancher
    DX, DZ0, DZ1 = 11.2, -6.4, 10.4        # plancher et véranda
    HX, HZ0, HZ1 = 7.6, -2.6, 8.4          # axes des piliers du hall
    YW, YB = 11.6, 12.8                    # haut des murs (poutre de tête), haut des consoles (sous-face du toit)
    ZE0, ZE1, XE = -7.6, 11.6, 12.0        # bord de l'avant-toit
    NM = 6                                 # marches
    Z_ESC = -12.0                          # pied de l'escalier
    tread = (DZ0 - Z_ESC) / NM
    rise = YF / NM

    with b.group("Socle"):
        b.box((-PX, 0, PZ0), (PX, YS - 0.4, PZ1), vr("pierre", rng, 0.03), name="Kidan")
        b.box((-PX - 0.2, YS - 0.4, PZ0 - 0.2), (PX + 0.2, YS, PZ1 + 0.2), vr("pierre_claire", rng, 0.02), studs="top",
              name="Kidan")
        b.box((-DX + 0.6, YS, DZ0 + 0.6), (DX - 0.6, YF - 0.6, DZ1 - 0.6), col("bois_fonce"), name="Soubassement")
        b.box((-DX, YF - 0.6, DZ0), (DX, YF, DZ1), vr(S["sol"], rng, 0.03), studs="top", name="Plancher")
        for xx in (-DX + 1.0, -4.8, 4.8, DX - 1.0):
            b.box((xx - 0.35, YS, DZ0 + 0.3), (xx + 0.35, YF - 0.6, DZ0 + 1.0), poutre, name="Tsuka")

    with b.group("Escalier"):
        for i in range(NM):
            za = Z_ESC + i * tread
            b.box((-4.0, 0, za), (4.0, (i + 1) * rise, za + tread), vr(S["sol"], rng, 0.03), studs="top", name="Marche")
        sl = (YF + 0.9 - 1.3) / (DZ0 - Z_ESC + 0.2)
        for s in (-1, 1):
            xa, xb = sorted((s * 3.8, s * 4.45))
            _pan_z(b, Z_ESC - 0.2, 1.3, DZ0, YF + 0.9, xa, xb, 0.9, poutre, studs="none", name="Limon")
            # main courante inclinée sur deux poteaux, giboshi doré en bas
            xm = s * 4.12
            for zz in (Z_ESC + 0.15, (Z_ESC + DZ0) / 2):
                yl = 1.3 + (zz - Z_ESC + 0.2) * sl
                b.box((xm - 0.22, yl - 0.3, zz - 0.22), (xm + 0.22, yl + 1.9, zz + 0.22), garde, name="Poteau_rampe")
            b.ball((xm, 1.3 + 0.35 * sl + 2.05, Z_ESC + 0.15), 0.33, col("or"), name="Giboshi")
            _pan_z(b, Z_ESC, 1.3 + 0.2 * sl + 1.9, DZ0 + 0.3, YF + 0.9 + 0.3 * sl + 1.9, xm - 0.2, xm + 0.2, 0.35, garde,
                   studs="top", name="Rampe")

    with b.group("Veranda"):
        # garde-corps : côtés sur toute la profondeur, avant (de part et d'autre de l'escalier) et arrière entre eux
        for s in (-1, 1):
            with b.at((s * (DX - 0.3), YF, 0), yaw=-90 * s):
                za_, zb_ = (DZ0 + 0.1, DZ1 - 0.1) if s > 0 else (-(DZ1 - 0.1), -(DZ0 + 0.1))
                _garde_corps(b, za_, zb_, 0, 0, garde, h=1.9, pas=2.3)
            xa, xb = sorted((s * 4.5, s * (DX - 0.5)))
            _garde_corps(b, xa, xb, YF, DZ0 + 0.3, garde, h=1.9, pas=2.2)
            # poteaux d'about à l'escalier, coiffés d'un giboshi
            b.box((s * 4.5 - 0.3, YF, DZ0 + 0.05), (s * 4.5 + 0.3, YF + 2.2, DZ0 + 0.6), garde, name="Oyabashira")
            b.ball((s * 4.5, YF + 2.45, DZ0 + 0.32), 0.35, col("or"), name="Giboshi")
        _garde_corps(b, -(DX - 0.5), DX - 0.5, YF, DZ1 - 0.3, garde, h=1.9, pas=2.3)

    with b.group("Hall"):
        m = vr(mur, rng, 0.02)
        b.box((-HX + 0.15, YF, HZ0 + 0.15), (HX - 0.15, YW, HZ1 - 0.15), m, name="Murs")
        b.box((-HX + 0.05, YF, HZ0 + 0.05), (HX - 0.05, YF + 1.2, HZ1 - 0.05), poutre, name="Lambris")
        b.box((-HX - 0.05, 10.0, HZ0 - 0.05), (HX + 0.05, 10.5, HZ1 + 0.05), poutre, name="Nageshi")
        b.box((-HX - 0.65, YW - 0.9, HZ0 - 0.65), (HX + 0.65, YW, HZ1 + 0.65), poutre, name="Poutre_tete")
        b.box((-HX + 0.25, YW, HZ0 + 0.25), (HX - 0.25, YB, HZ1 - 0.25), m, name="Frise")
        piliers = [(sx * HX, z) for sx in (-1, 1) for z in (HZ0, (HZ0 + HZ1) / 2, HZ1)] + \
                  [(sx * 2.6, z) for sx in (-1, 1) for z in (HZ0, HZ1)]
        for (px, pz) in piliers:
            b.cyl((px, (YF + YW) / 2, pz), 0.55, YW - YF, poteau, axis="y", name="Pilier")
            # consoles (tokyō) : bloc, bras le long du mur, deux petits blocs
            along_x = abs(abs(pz) - abs(HZ0)) < 0.01 or abs(pz - HZ1) < 0.01
            b.box((px - 0.5, YW, pz - 0.5), (px + 0.5, YW + 0.5, pz + 0.5), poutre, name="Masu")
            if along_x:
                b.box((px - 1.35, YW + 0.5, pz - 0.32), (px + 1.35, YW + 0.85, pz + 0.32), poutre, name="Hijiki")
                for dx in (-1.0, 1.0):
                    b.box((px + dx - 0.32, YW + 0.85, pz - 0.38), (px + dx + 0.32, YB, pz + 0.38), poutre, name="Masu")
            else:
                b.box((px - 0.32, YW + 0.5, pz - 1.35), (px + 0.32, YW + 0.85, pz + 1.35), poutre, name="Hijiki")
                for dz in (-1.0, 1.0):
                    b.box((px - 0.38, YW + 0.85, pz + dz - 0.32), (px + 0.38, YB, pz + dz + 0.32), poutre, name="Masu")
        # façade : baie centrale ouverte (intérieur sombre, rideau violet), baies latérales à treillis
        with b.at((0, 0, HZ0 + 0.15)):
            b.box((-2.05, YF, -0.25), (2.05, 10.0, 0.3), col(INTERIEUR), name="Interieur")
            b.box((-2.05, 8.6, -0.5), (2.05, 10.0, -0.3), col("noren_violet"), material="Fabric", name="Rideau")
            for xx in (-1.2, 1.2):
                b.box((xx - 0.14, 7.9, -0.62), (xx + 0.14, 9.95, -0.45), col("blanc"), name="Noeud")
            for s in (-1, 1):
                xa, xb = sorted((s * 3.15, s * (HX - 0.55)))
                b.box((xa, YF + 1.2, -0.25), (xb, 10.0, 0.3), col(S["fronton"]), name="Treillis_fond")
                for k in range(1, 5):
                    xx = xa + k * (xb - xa) / 5
                    b.box((xx - 0.12, YF + 1.25, -0.45), (xx + 0.12, 9.95, -0.1), col(S["treillis"]), name="Treillis")
                for yy in (6.4, 8.2):
                    b.box((xa, yy - 0.12, -0.39), (xb, yy + 0.12, -0.1), col(S["treillis"]), name="Treillis")
        # côtés et arrière : fenêtres à barreaux de bois
        for s in (-1, 1):
            with b.at((s * (HX - 0.15), 0, 0), yaw=-90 * s):
                for zc in ((HZ0 + (HZ0 + HZ1) / 2) / 2, ((HZ0 + HZ1) / 2 + HZ1) / 2):
                    _mushiko(b, zc * s, 7.0, 2.8, 2.2, S["poutre"], n=4)
        with b.at((0, 0, HZ1 - 0.15), yaw=180):
            for xx in (-5.1, 5.1):
                _mushiko(b, xx, 7.0, 2.8, 2.2, S["poutre"], n=4)

    # --- toit irimoya à pignon sur l'avant (repère tourné : x local = -z monde) ---------------------------------
    with b.group("Toit"):
        with b.at((0, 0, 0), yaw=90):
            R = _toit_irimoya(b, -ZE1, -ZE0, -XE, XE, YB + 0.5, S["toit"], a_z0=4.4, a_z1=4.4, a_x0=3.0, a_x1=3.6, h1=2.4,
                              h2=0.66 * (XE - 4.4), tri=mur, tri_x1=S["fronton"], deb_g=0.8, rng=rng, gegyo="or")
        ya, yr = R["ya"], R["yr"]
        zg = -R["xg1"]                     # face avant du triangle des pans hauts (monde)
        run = XE - 4.4
        pente = R["pente"]
        hc = col(S["hafu"])
        # planches de rive (hafu) sur le pignon avant, bouts relevés
        for s in (-1, 1):
            # du faîtage au pied du pignon (même pente que le toit, 0,3 au-dessus), puis bout relevé
            pts = [(s * (run + 0.75), ya + 0.5), (s * run, ya + 0.3), (0.0, yr + 0.3)]
            dz = 0.05 if s > 0 else 0.0
            for (pa, pb, ea, eb) in ((pts[0], pts[1], 0.0, 0.25), (pts[1], pts[2], 0.25, 0.5)):
                (xa_, ya_), (xb_, yb_) = sorted((pa, pb))
                e1, e2 = (ea, eb) if pa[0] <= pb[0] else (eb, ea)
                _pan_x(b, xa_, ya_, xb_, yb_, zg - 0.55 + dz, zg + 0.1 - dz, 1.0, hc, ext_a=e1, ext_b=e2,
                       studs="none", name="Hafu")
                dz = 0.05 - dz
        # poutre de base et treillis kitsune-goshi dans le fronton
        b.box((-run + 0.4, ya + 0.02, zg - 0.45), (run - 0.4, ya + 0.42, zg + 0.05), poutre, name="Tsuma_poutre")
        tc = col(S["treillis"])
        for k in range(-3, 4):
            xx = k * run / 4.0
            ytop = ya + (run - abs(xx)) * pente - 0.7
            if ytop - (ya + 0.42) > 0.6:
                b.box((xx - 0.13, ya + 0.42, zg - 0.4), (xx + 0.13, ytop, zg + 0.05), tc, name="Kitsune_goshi")
        for yy in (ya + 1.6, ya + 3.0):
            half = run - (yy - ya + 0.7) / pente - 0.2
            if half > 0.8:
                b.box((-half, yy - 0.12, zg - 0.34), (half, yy + 0.12, zg + 0.0), tc, name="Kitsune_goshi")
        # plaque (hengaku) laquée noir et or au milieu du fronton
        b.box((-0.95, ya + 0.75, zg - 0.7), (0.95, ya + 3.35, zg - 0.3), col("or"), name="Hengaku_cadre")
        p = b.box((-0.75, ya + 0.95, zg - 0.86), (0.75, ya + 3.15, zg - 0.66), col("noir_laque"), name="Hengaku")
        p.label = {"face": "Front", "text": "藤", "color": col("or"), "font": "brush"}
        # coins de la jupe relevés : petits coins dont le haut est à l'angle (pointe de l'avant-toit)
        tc_ = shade(col(S["toit"]), 0.8)
        for sx in (-1, 1):
            for zz, sz in ((ZE0, 1), (ZE1, -1)):
                xa_, xb_ = sorted((sx * (XE + 0.12), sx * (XE - 2.1)))
                za_, zb_ = sorted((zz - sz * 0.12, zz + sz * 1.1))
                b.wedge((xa_, YB + 0.45, za_), (xb_, YB + 1.05, zb_), tc_, down="+x" if sx < 0 else "-x", studs="top",
                        name="Sumi")
        top = R["top"]

    # --- cloche, corde, tronc à offrandes, shimenawa -------------------------------------------------------------
    with b.group("Culte"):
        y_sous = YB                         # dessous de l'avant-toit
        if S["kohai"]:
            y_sous = 12.0
        zc_ = -4.4
        b.box((-0.07, 11.0, zc_ - 0.07), (0.07, y_sous + 0.1, zc_ + 0.07), col("noir"), collide=False, name="Cordon")
        b.ball((0, 10.55, zc_), 0.62, col("or"), material="Metal", name="Suzu")
        cols_ = ("vermillon", "blanc", "noren_violet", "blanc")
        for i in range(4):
            yt = 9.95 - i * 1.15
            b.cyl((0, yt - 0.575, zc_), 0.26 + 0.02 * (i % 2), 1.15, col(cols_[i]), axis="y", collide=False, name="Suzu_no_o")
        b.cyl((0, 9.95 - 4 * 1.15 - 0.35, zc_), 0.34, 0.7, col("vermillon"), axis="y", collide=False, name="Gland")
        # tronc à offrandes (saisen-bako) en haut de l'escalier
        b.box((-1.8, YF, -6.1), (1.8, YF + 1.5, -5.0), vr("bois_moyen", rng, 0.03), name="Saisen")
        for k in range(3):
            xx = -1.2 + k * 1.2
            b.box((xx - 0.42, YF + 1.5, -6.0), (xx + 0.42, YF + 1.75, -5.1), col("bois_fonce"), studs="top", name="Grille")
        # shimenawa entre les piliers de la baie centrale, papiers shide
        r0 = 0.62 if S.get("grosse_corde") else 0.45
        zs = HZ0 - 0.75
        ys0, ys1 = 9.6, 8.9
        _corde(b, -2.6, ys0, -0.9, ys1 + 0.05, zs, r0 * 0.8, "corde")
        _corde(b, -0.95, ys1, 0.95, ys1, zs, r0, "corde")
        _corde(b, 0.9, ys1 + 0.05, 2.6, ys0, zs, r0 * 0.8, "corde")
        for xx in (-1.8, 0.0, 1.8):
            _shide(b, xx, ys1 - r0 + 0.25 + (0.25 if abs(xx) > 1 else 0.0), zs, n=4)
        for xx in (-0.9, 0.9):
            b.box((xx - 0.12, ys1 - r0 - 0.8, zs - 0.12), (xx + 0.12, ys1 - r0 * 0.5, zs + 0.12), col("corde"), collide=False,
                  name="Fusa")

    # --- auvent au-dessus de l'escalier (kōhai) ------------------------------------------------------------------
    if S["kohai"]:
        with b.group("Kohai"):
            Yk = 9.6
            zk = Z_ESC + 1.0
            xk = 4.6
            for s in (-1, 1):
                b.box((s * xk - 0.75, 0, zk - 0.75), (s * xk + 0.75, 0.6, zk + 0.75), col(S["lanterne"]), studs="top",
                      name="Base")
                b.cyl((s * xk, (0.6 + Yk) / 2, zk), 0.5, Yk - 0.6, poteau, axis="y", name="Pilier")
                b.box((s * xk - 0.3, Yk - 0.75, zk - 0.3), (s * xk + 0.3, Yk - 0.05, HZ0 - 0.6), poutre, name="Longrine")
            za_k = zk - 1.0
            b.box((-xk - 0.4, Yk - 0.9, za_k + 0.05), (xk + 0.4, Yk, zk + 0.35), poutre, name="Koryo")
            if S["kohai"] == "kara":
                larg, hk = 2 * xk + 1.8, 2.8
                y0 = Yk + 0.15
                _, dessus = _kara_hafu(b, 0, za_k, -4.6, y0, larg, hk, S["toit"], S["hafu"], ep=0.7, rng=rng)
                hw = larg / 2
                tm = vr(mur, rng, 0.02)
                b.box((-0.2 * hw, Yk, za_k + 0.3), (0.2 * hw, dessus(0.2) - 0.55, za_k + 0.8), tm, name="Tympan")
                for s_ in (-1, 1):
                    xa_, xb_ = sorted((s_ * 0.2 * hw, s_ * 0.46 * hw))
                    b.box((xa_, Yk, za_k + 0.3), (xb_, dessus(0.46) - 0.55, za_k + 0.8), tm, name="Tympan")
                b.wedge((-1.1, Yk, za_k + 0.1), (0.0, Yk + 1.2, za_k + 0.45), col("or"), down="-x", name="Kaeru_mata")
                b.wedge((0.0, Yk, za_k + 0.1), (1.1, Yk + 1.2, za_k + 0.45), col("or"), down="+x", name="Kaeru_mata")
            else:
                _toit_tsumairi(b, -xk, xk, za_k + 0.6, -4.6, Yk, 0.6, S["toit"], S["poutre"], deb=0.9, deb_av=0.6,
                               deb_ar=0.0, ep=0.7, hafu=S["hafu"], gegyo="or", rng=rng, treillis=S["treillis"],
                               pignon_z=(za_k + 0.6, za_k + 1.6))

    # --- lanternes de pierre --------------------------------------------------------------------------------------
    with b.group("Lanternes"):
        for s in (-1, 1):
            _toro(b, s * 7.6, -10.2, S["lanterne"], lumiere=True, h=1.0)
    return {"emprise": (28.0, 24.0), "hauteur": round(top, 2)}


# ---------------------------------------------------------------------------
# MAISON DE THÉ (chaya)
# ---------------------------------------------------------------------------
CHAUME = "#B39463"          # toit de chaume
CHAUME_FONCE = "#7E6440"

_MAISONS_THE = [
    # 0 : dango — toit bleu nuit, noren rouges 団子, ombrelle vermillon, lampions rouges
    dict(toit="tuile", mur="enduit", cadre="bois_fonce", noren=("noren_rouge", "blanc", "団子"), ombrelle="vermillon",
         lampion=("rouge", False), chaume=False, menus=("団子", "茶", "甘味"), andon=False),
    # 1 : salon de thé du col de montagne, toit de chaume à faîtage croisé, noren violets 茶, lanterne andon
    dict(toit=CHAUME, mur="enduit_creme", cadre="bois", noren=("noren_violet", "blanc", "茶"), ombrelle="rouge",
         lampion=("lampion_papier", True), chaume=True, menus=("茶", "団子"), andon=True),
    # 2 : douceurs — toit ardoise, noren bleus 甘味, lanternes de papier éclairées
    dict(toit="tuile_ardoise", mur="enduit", cadre="bois_fonce", noren=("noren_bleu", "blanc", "甘味"), ombrelle="vermillon",
         lampion=("lampion_papier", True), chaume=False, menus=("甘味", "団子", "茶"), andon=False, nobori=True),
    # 3 : maison de thé aux glycines : tonnelle fleurie devant, toit bleu clair, noren violets 藤
    dict(toit="tuile_claire", mur="enduit", cadre="bois_fonce", noren=("noren_violet", "blanc", "藤"), ombrelle="rouge",
         lampion=("orange_lampion", True), chaume=False, menus=("茶", "甘味"), andon=False, tonnelle=True),
]


def _banc_rouge(b, x, z, w, *, d=1.6, h=1.6, rng=None):
    """Banc bas (endai) couvert de feutre rouge (hi-mōsen)."""
    for xx in (x - w / 2 + 0.45, x + w / 2 - 0.45):
        b.box((xx - 0.22, 0, z - d / 2 + 0.2), (xx + 0.22, h - 0.3, z + d / 2 - 0.2), col("bois_fonce"), name="Pied")
    b.box((x - w / 2, h - 0.3, z - d / 2), (x + w / 2, h, z + d / 2), col("bois_moyen"), name="Banc")
    b.box((x - w / 2 + 0.25, h, z - d / 2 - 0.12), (x + w / 2 - 0.25, h + 0.15, z + d / 2 + 0.12),
          vr(FEUTRE, rng, 0.03) if rng is not None else col(FEUTRE), material="Fabric", studs="top", name="Feutre")
    return h + 0.15


def _ombrelle(b, x, z, couleur, *, r=3.0, y=6.4):
    """Grande ombrelle de cérémonie (nodate-gasa) : pied lesté, mât, toile en trois disques stud, nervures claires."""
    b.box((x - 0.5, 0, z - 0.5), (x + 0.5, 0.45, z + 0.5), col("pierre_fonce"), studs="top", name="Lest")
    b.cyl((x, (0.45 + y + 0.9) / 2, z), 0.14, y + 0.9 - 0.45, col("bois_fonce"), axis="y", name="Mat")
    cc = col(couleur)
    b.cyl((x, y - 0.06, z), r * 0.86, 0.12, col("blanc"), axis="y", collide=False, name="Nervures")
    b.cyl((x, y + 0.14, z), r, 0.28, cc, axis="y", studs="top", collide=False, name="Toile")
    b.cyl((x, y + 0.45, z), r * 0.7, 0.34, shade(cc, 0.96), axis="y", studs="top", collide=False, name="Toile")
    b.cyl((x, y + 0.79, z), r * 0.38, 0.34, shade(cc, 0.92), axis="y", studs="top", collide=False, name="Toile")
    b.ball((x, y + 1.05, z), 0.3, col("noir"), collide=False, name="Pommeau")


def _nobori(b, x, z, texte, fond, encre, *, h=6.8, larg=1.3):
    """Bannière nobori : mât lesté, bras en haut, toile verticale dans le plan YZ (texte lisible des deux sens
    de la rue)."""
    b.box((x - 0.45, 0, z - 0.45), (x + 0.45, 0.4, z + 0.45), col("pierre_fonce"), studs="top", name="Lest")
    b.cyl((x, (0.4 + h) / 2, z), 0.12, h - 0.4, col("bois_fonce"), axis="y", name="Mat")
    b.box((x - 0.07, h - 0.45, z - larg - 0.15), (x + 0.07, h - 0.3, z + 0.1), col("bois_fonce"), collide=False, name="Bras")
    for sx, face in ((-1, "Left"), (1, "Right")):
        xa, xb = sorted((x + sx * 0.0, x + sx * 0.09))
        p = b.box((xa, 1.4, z - larg - 0.1), (xb, h - 0.45, z - 0.15), col(fond), collide=False, material="Fabric",
                  name="Nobori")
        p.label = {"face": face, "text": texte, "color": col(encre), "font": "brush", "vertical": True}


def _croix_faitage(b, x0, x1, z, y, n=3, couleur="bois_fonce", long=2.0):
    """Bois croisés posés sur le faîtage d'un toit de chaume (umanori)."""
    for i in range(n):
        x = x0 + (i + 0.5) * (x1 - x0) / n
        for k, a in enumerate((32, -32)):
            b.part("block", (0.28, long, 0.28), (x, y + 0.55 * long / 2.0, z + (0.16 if k else -0.16)), rot_x(a),
                   col(couleur), collide=False, name="Umanori")


def maison_the(b, variant=0):
    """Maison de thé (chaya) d'environ 16 × 12 : salle ouverte sur la rue (comptoir, bouilloire, menus), bancs
    couverts de feutre rouge sous l'avant-toit, grande ombrelle rouge, noren 団子 / 茶 / 甘味 / 藤, lanternes ;
    toit de tuiles ou de chaume ; tonnelle de glycine en variante 3."""
    rng = b.rng
    S = _style(_MAISONS_THE, variant, {"toit": ["tuile", CHAUME, "tuile_ardoise", "tuile_claire"]})
    W, D = 16.0, 12.0
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    zh = -0.6                              # ligne des poteaux avant (la salle est derrière)
    H = 7.4
    cadre = col(S["cadre"])
    mur = S["mur"]
    with b.group("Salle"):
        b.box((x0 - 0.2, 0, zf + 0.5), (x1 + 0.2, 0.3, zb + 0.2), vr("pierre", rng, 0.03), studs="top", name="Dallage")
        b.box((x0 + 0.7, 0.3, zh + 0.75), (x1 - 0.7, 0.6, zb - 0.8), vr("terre", rng, 0.03), studs="top", name="Doma")
        m = vr(mur, rng, 0.02)
        b.box((x0, 0.3, zb - 0.8), (x1, H, zb), m, name="Mur_fond")
        for xa in (x0, x1 - 0.7):
            b.box((xa, 0.3, zh + 0.6), (xa + 0.7, H, zb - 0.8), m, name="Mur")
            b.box((xa - 0.1, 0.3, zh + 0.5), (xa + 0.8, 1.6, zb - 0.7), cadre, name="Plinthe")
        xs_po = [x0 + 0.35, x0 + W / 3, x1 - W / 3, x1 - 0.35]
        for xx in xs_po:
            b.box((xx - 0.35, 0.3, zh - 0.35), (xx + 0.35, H - 0.6, zh + 0.35), cadre, name="Poteau")
        b.box((x0 - 0.1, H - 1.2, zh - 0.4), (x1 + 0.1, H, zh + 0.4), cadre, name="Kamoi")
        # comptoir, bouilloire, étagère à jarres, menus
        b.box((x0 + 2.0, 0.6, zb - 3.0), (x1 - 2.0, 3.0, zb - 1.8), vr("bois", rng, 0.03), name="Comptoir")
        b.box((x0 + 1.8, 3.0, zb - 3.2), (x1 - 1.8, 3.35, zb - 1.7), col("bois_clair"), studs="top", name="Plateau")
        b.cyl((x0 + 4.0, 3.95, zb - 2.45), 0.6, 1.2, col("noir"), axis="y", name="Bouilloire")
        b.cyl((x0 + 4.0, 4.65, zb - 2.45), 0.25, 0.3, col("noir"), axis="y", name="Couvercle")
        for i in range(3):
            b.cyl((x1 - 3.2 - i * 1.4, 3.35 + 0.5, zb - 2.45), 0.45, 1.0, vr(THE_VERT if i != 1 else "bois_clair", rng, 0.05),
                  axis="y", studs="top", name="Jarre")
        b.box((x0 + 1.2, 4.6, zb - 1.4), (x1 - 1.2, 4.9, zb - 0.8), col("bois_clair"), studs="top", name="Etagere")
        for i, t in enumerate(S["menus"]):
            xx = -2.4 + i * 2.4
            p = b.box((xx - 0.8, 5.2, zb - 0.95), (xx + 0.8, 7.0 - 0.3, zb - 0.8), col("papier"), name="Menu")
            p.label = {"face": "Front", "text": t, "color": col("noir"), "font": "brush", "vertical": len(t) > 1}
        nf, ne, nt = S["noren"]
        _noren(b, xs_po[1] + 0.45, xs_po[2] - 0.45, H - 1.2, 2.4, zh - 0.55, nf, ne, nt, n=len(nt) if len(nt) > 1 else 3)

    with b.group("Toit"):
        if S["chaume"]:
            top, dessous = _toit_hirairi(b, x0, x1, zh, zb, H, 0.85, S["toit"], mur, deb_av=2.4, deb_ar=1.4, deb_cote=0.9,
                                         ep=1.3, sori=0.7, rng=rng, faitage=CHAUME_FONCE, oni=False, blanc=False)
            zm = (zh + zb) / 2
            yr = H + (zm - zh) * 0.85 + 1.3 * math.hypot(1, 0.85)
            _croix_faitage(b, x0 + 1.0, x1 - 1.0, zm, yr + 0.5, n=4)
            top = max(top, yr + 2.0)
        else:
            top, dessous = _toit_hirairi(b, x0, x1, zh, zb, H, 0.5, S["toit"], mur, deb_av=2.8, deb_ar=1.2, deb_cote=0.7,
                                         ep=0.8, sori=0.45, rng=rng, fait=0.8)

    with b.group("Terrasse"):
        lc, ln = S["lampion"]
        for xx in (x0 + 0.6, x1 - 0.6):
            zl = zh - 1.6
            _chochin(b, xx, dessous(zl), zl, r=0.62, h=1.4, corps=lc, neon=ln)
        yb_ = _banc_rouge(b, -4.0, -2.5, 4.4, rng=rng)
        b.cyl((-5.0, yb_ + 0.25, -2.5), 0.28, 0.5, col("blanc"), axis="y", collide=False, name="Tasse")
        b.box((-4.2, yb_, -2.8), (-3.2, yb_ + 0.15, -2.2), col("bois_clair"), collide=False, name="Plateau")
        _dango(b, -3.7, yb_ + 0.15, -2.5)
        if S.get("tonnelle"):
            # tonnelle de glycine devant la terrasse droite : poteaux, pannes, grappes mauves
            _banc_rouge(b, 4.6, -5.6, 4.4, rng=rng)
            pts = [(1.6, -7.4), (7.6, -7.4), (1.6, -4.2), (7.6, -4.2)]
            for (px, pz) in pts:
                b.box((px - 0.22, 0, pz - 0.22), (px + 0.22, 6.0, pz + 0.22), col("bois"), name="Poteau_tonnelle")
            for pz in (-7.4, -4.2):
                b.box((1.2, 6.0, pz - 0.25), (8.0, 6.45, pz + 0.25), col("bois"), name="Panne")
            for i in range(4):
                px = 2.0 + i * 1.8
                b.box((px - 0.15, 6.45, -7.9), (px + 0.15, 6.75, -3.75), col("bois_clair"), studs="top", name="Latte")
            gl = (("glycine_fonce", "glycine"), ("glycine", "glycine_claire"), ("glycine", "glycine_pale"))
            for i in range(7):
                px = 2.0 + (i % 4) * 1.8 + (0.0 if i < 4 else 0.9)
                pz = -6.6 if i < 4 else -5.0
                hh = 1.2 + 0.45 * ((i * 7) % 3)
                c1, c2 = gl[i % 3]
                # grappe en cascade : haut large et foncé, pointe plus fine et plus claire
                b.box((px - 0.5, 6.45 - hh, pz - 0.5), (px + 0.5, 6.5, pz + 0.5), col(c1), collide=False, name="Grappe")
                b.box((px - 0.3, 6.45 - hh - 1.0, pz - 0.3), (px + 0.3, 6.45 - hh + 0.1, pz + 0.3), col(c2), collide=False,
                      name="Grappe")
        else:
            _banc_rouge(b, 4.4, -4.3, 3.6, rng=rng)
            _ombrelle(b, 6.2, -5.3, S["ombrelle"], r=2.2, y=5.5)
        if S.get("nobori"):
            for xx in (x0 + 0.9, x1 - 0.9):
                _nobori(b, xx, -4.3, S["noren"][2], "noren_rouge" if xx > 0 else "noren_bleu", "blanc")
        if S.get("andon"):
            # lanterne-enseigne andon posée près de l'entrée
            b.box((-7.4, 0.3, -6.6), (-6.0, 0.8, -5.2), col("bois_fonce"), studs="top", name="Andon_pied")
            b.box((-7.2, 0.8, -6.4), (-6.2, 3.6, -5.4), col("lampion_papier"), material="Neon", name="Andon")
            p = b.box((-7.3, 1.1, -6.55), (-6.1, 3.3, -6.42), col("papier"), name="Andon_face")
            p.label = {"face": "Front", "text": S["noren"][2], "color": col("noir"), "font": "brush", "vertical": True}
            b.box((-7.35, 3.6, -6.55), (-6.05, 3.9, -5.25), col("bois_fonce"), studs="top", name="Andon_toit")
    return {"emprise": (W, D), "hauteur": round(top, 2)}


# ---------------------------------------------------------------------------
# KURA (entrepôt)
# ---------------------------------------------------------------------------

_KURAS = [
    # 0 : kura blanc, soubassement namako, toit bleu nuit à deux pans, porte sous un petit auvent
    dict(mur="enduit", toit="tuile", forme="hirairi", hachimaki=False, signe=None, haut=False),
    # 1 : kura noir de marchand, pignon sur rue, bandeau épais sous l'avant-toit
    dict(mur="#2E2D33", toit="tuile_ardoise", forme="tsumairi", hachimaki=True, signe=None, haut=False),
    # 2 : kura crème à bandeau épais, pignon sur rue marqué 茶
    dict(mur="enduit_creme", toit="tuile_fonce", forme="tsumairi", hachimaki=True, signe="茶", haut=False),
    # 3 : kura blanc, namako sur tout le rez, toit bleu clair, grand 薬 peint sur la façade
    dict(mur="enduit", toit="tuile_claire", forme="hirairi", hachimaki=False, signe="薬", haut=True),
]


def _namako(b, xa, xb, ya, yb, joint, *, pas=1.6, w=0.24):
    """Treillis diagonal du soubassement namako (repère de façade, plan z = 0) : joints blancs à ±45°
    (profondeurs différentes : pas de faces coplanaires), coupés au bord du panneau ; les bouts se cachent
    sous le cadre (rebord, socle, pilastres), qui dépasse davantage."""
    jc = col(joint)
    W_, H_ = xb - xa, yb - ya
    for sgn, (z0_, z1_) in ((1, (-0.12, 0.02)), (-1, (-0.16, 0.0))):
        t = (W_ / 2 % pas) - pas * math.ceil((H_ + W_) / pas) if sgn > 0 else (W_ / 2 % pas)
        while t <= W_ + H_ + pas:
            if sgn > 0:
                u1, u2 = max(0.0, t), min(W_, t + H_)
                p1, p2 = (u1, u1 - t), (u2, u2 - t)
            else:
                u1, u2 = max(0.0, t - H_), min(W_, t)
                p1, p2 = (u1, t - u1), (u2, t - u2)
            L = (u2 - u1) * math.sqrt(2)
            if L > 0.9:
                cx = xa + (p1[0] + p2[0]) / 2
                cy = ya + (p1[1] + p2[1]) / 2
                b.part("block", (L, w, z1_ - z0_), (cx, cy, (z0_ + z1_) / 2), rot_z(45 * sgn), jc, name="Namako")
            t += pas


def _fenetre_kura(b, x, y, s, mur, *, volets=True):
    """Petite fenêtre lourde de kura : encadrement épais d'enduit, ouverture sombre, barreaux de fer,
    volets d'enduit ouverts de part et d'autre."""
    m = col(mur)
    b.box((x - s / 2 - 0.45, y - 0.45, -0.45), (x + s / 2 + 0.45, y + s + 0.45, 0.2), shade(m, 0.95), name="Encadrement")
    b.box((x - s / 2, y, -0.55), (x + s / 2, y + s, -0.3), col(INTERIEUR), name="Ouverture")
    for xx in (x - s / 6, x + s / 6):
        b.box((xx - 0.09, y - 0.1, -0.68), (xx + 0.09, y + s + 0.1, -0.5), col(FER), name="Barreau")
    if volets:
        for sx in (-1, 1):
            xa, xb = sorted((x + sx * (s / 2 + 0.5), x + sx * (s / 2 + 0.5 + s * 0.55)))
            b.box((xa, y - 0.05, -0.75), (xb, y + s + 0.05, -0.2), shade(m, 1.02), name="Volet")


def kura(b, variant=0):
    """Entrepôt (kura) d'environ 12 × 10 × 14 : murs épais d'enduit (blanc, crème ou noir), soubassement sombre
    à treillis diagonal namako, rebord, pilastres d'angle, porte lourde à encadrement à gradins sous un petit
    auvent, petites fenêtres à barreaux et volets, lourd toit de tuiles à deux pans (faîtage sur rue ou pignon
    sur rue), bandeau épais (hachimaki) en variante, grand caractère peint en variante."""
    rng = b.rng
    S = _style(_KURAS, variant, {"toit": ["tuile", "tuile_ardoise", "tuile_fonce", "tuile_claire"]})
    W, D = 12.0, 10.0
    x0, x1, z0, z1 = -W / 2, W / 2, -D / 2, D / 2
    YN = 6.6 if S["haut"] else 4.0            # haut du soubassement namako
    H = 9.6                                   # haut des murs
    mur = S["mur"]
    noir = mur.startswith("#")
    joint = "enduit"
    with b.group("Corps"):
        b.box((x0 - 0.3, 0, z0 - 0.3), (x1 + 0.3, 0.8, z1 + 0.3), vr("pierre_fonce", rng, 0.03), studs="top", name="Socle")
        b.box((x0, 0.8, z0), (x1, YN, z1), col(NAMAKO), name="Namako_mur")
        b.box((x0 - 0.3, YN - 0.1, z0 - 0.3), (x1 + 0.3, YN + 0.35, z1 + 0.3), shade(col("enduit"), 0.96), studs="top",
              name="Rebord")
        b.box((x0 + 0.15, YN + 0.35, z0 + 0.15), (x1 - 0.15, H - (0.8 if S["hachimaki"] else 0.0), z1 - 0.15),
              vr(mur, rng, 0.02), name="Murs")
        for sx in (-1, 1):
            for sz in (-1, 1):
                xa, xb = sorted((sx * (W / 2 + 0.26), sx * (W / 2 - 0.45)))
                za, zb_ = sorted((sz * (D / 2 + 0.26), sz * (D / 2 - 0.45)))
                b.box((xa, 0.8, za), (xb, YN - 0.1, zb_), col(joint), name="Pilastre")
        if S["hachimaki"]:
            b.box((x0 - 0.15, H - 1.6, z0 - 0.15), (x1 + 0.15, H - 0.8, z1 + 0.15),
                  col("enduit_gris") if noir else shade(col(mur), 0.97), name="Hachimaki")
            b.box((x0 - 0.4, H - 0.8, z0 - 0.4), (x1 + 0.4, H, z1 + 0.4),
                  shade(col("enduit_gris"), 0.92) if noir else shade(col(mur), 0.95), name="Hachimaki")
    # treillis namako : façade (de part et d'autre de la porte), côtés et arrière
    with b.group("Namako"):
        wp = 4.6                                   # largeur de l'encadrement de porte
        with b.at((0, 0, z0)):
            _namako(b, x0 + 0.45, -wp / 2 - 0.05, 0.8, YN - 0.1, joint, pas=1.6)
            _namako(b, wp / 2 + 0.05, x1 - 0.45, 0.8, YN - 0.1, joint, pas=1.6)
        for side in (-1, 1):
            with b.at((x1 if side > 0 else x0, 0, 0), yaw=-90 * side):
                _namako(b, -D / 2 + 0.45, D / 2 - 0.45, 0.8, YN - 0.1, joint, pas=1.8 if S["haut"] else 1.6)
        if not S["haut"]:
            with b.at((0, 0, z1), yaw=180):
                _namako(b, x0 + 0.45, x1 - 0.45, 0.8, YN - 0.1, joint, pas=2.0)
    with b.group("Porte"), b.at((0, 0, z0)):
        yp = 6.2 if S["haut"] else 7.4
        b.box((-wp / 2, 0.8, -0.5), (wp / 2, yp, 0.1), shade(col("enduit"), 0.94), name="Encadrement")
        b.box((-wp / 2 + 0.5, 0.8, -0.75), (wp / 2 - 0.5, yp - 0.5, -0.5), col("enduit"), name="Gradin")
        b.box((-1.5, 0.8, -0.95), (1.5, yp - 1.1, -0.75), col("bois_fonce"), name="Porte")
        for xx in (-0.5, 0.5):
            b.box((xx - 0.08, 0.9, -1.05), (xx + 0.08, yp - 1.2, -0.9), col("bois"), name="Planche")
        for yy in (2.2, 4.6):
            b.box((-1.4, yy, -1.12), (1.4, yy + 0.3, -0.9), col(FER), name="Penture")
        b.box((-0.25, 3.3, -1.25), (0.25, 3.9, -1.0), col("or"), name="Serrure")
        b.box((-2.0, 0, -2.0), (2.0, 0.55, -0.3), vr("pierre", rng, 0.03), studs="top", name="Marche")
        # petit auvent de porte (kiriyoke)
        b.box((-wp / 2 - 0.6, yp + 0.05, -2.0), (wp / 2 + 0.6, yp + 0.35, 0.2), shade(col(S["toit"]), 0.72), name="Rive")
        b.wedge((-wp / 2 - 0.6, yp + 0.35, -2.0), (wp / 2 + 0.6, yp + 1.2, 0.2), col(S["toit"]), down="-z", studs="top",
                name="Auvent")
    with b.group("Fenetres"):
        with b.at((0, 0, z0 + 0.15)):
            if S["forme"] == "hirairi":
                for xx in (-4.0, 4.0):
                    _fenetre_kura(b, xx, 7.6 if S["haut"] else 7.2, 1.5, mur, volets=False)
        for side in (-1, 1):
            with b.at(((x1 - 0.15) if side > 0 else (x0 + 0.15), 0, 0), yaw=-90 * side):
                _fenetre_kura(b, 0, 6.6 if not S["haut"] else 7.5, 1.6, mur)
        if S["signe"] and S["forme"] == "hirairi":
            with b.at((0, 0, z0 + 0.15)):
                p = b.box((-1.0, 7.5, -0.25), (1.0, 9.1, 0.1), vr(mur, rng, 0.02), name="Signe")
                p.label = {"face": "Front", "text": S["signe"], "color": col("noir"), "font": "brush"}
    with b.group("Toit"):
        if S["forme"] == "hirairi":
            top, _ = _toit_hirairi(b, x0 + 0.15, x1 - 0.15, z0 + 0.15, z1 - 0.15, H, 0.52, S["toit"], mur, deb_av=1.3,
                                   deb_ar=1.3, deb_cote=1.0, ep=1.0, sori=0.55, rng=rng)
        else:
            top = _toit_tsumairi(b, x0 + 0.15, x1 - 0.15, z0 + 0.15, z1 - 0.15, H, 0.55, S["toit"], mur, deb=1.1,
                                 deb_av=1.2, deb_ar=1.0, ep=1.0, sori=0.55, hafu=None, gegyo=None, rng=rng)
            # fenêtre du pignon, et caractère peint
            with b.at((0, 0, z0 + 0.15)):
                if S["signe"]:
                    p = b.box((-1.0, H + 0.3, -0.25), (1.0, H + 2.15, 0.1), vr(mur, rng, 0.02), name="Signe")
                    p.label = {"face": "Front", "text": S["signe"], "color": col("noir" if not noir else "blanc"),
                               "font": "brush"}
                else:
                    _fenetre_kura(b, 0, H + 0.75, 1.2, mur, volets=False)
    return {"emprise": (W, D), "hauteur": round(top, 2)}


# ---------------------------------------------------------------------------
# TEMIZUYA (pavillon des ablutions)
# ---------------------------------------------------------------------------

_TEMIZUYAS = [
    # 0 : bois naturel et tuiles d'ardoise (comme la référence), plaque de bois clair
    dict(toit="tuile_ardoise", poteau="bois_moyen", poutre="bois_fonce", bassin="pierre_fonce",
         plaque=("清水", "bois_clair", "noir"), chaume=False, lanterne=False),
    # 1 : poteaux vermillon, toit de cuivre patiné, plaque laquée noir et or
    dict(toit="cuivre_vert", poteau="vermillon", poutre="vermillon", bassin="pierre",
         plaque=("清水", "noir_laque", "or"), chaume=False, lanterne=False),
    # 2 : bois sombre, toit bleu nuit, plaque blanche, lanterne de pierre à côté
    dict(toit="tuile", poteau="bois_fonce", poutre="bois_fonce", bassin="pierre_claire",
         plaque=("清水", "blanc", "noir"), chaume=False, lanterne=True),
    # 3 : rustique : toit de chaume, bassin de pierre sombre
    dict(toit=CHAUME, poteau="bois", poutre="bois_fonce", bassin="pierre_fonce",
         plaque=("清水", "bois_clair", "noir"), chaume=True, lanterne=False),
]


def temizuya(b, variant=0):
    """Pavillon des ablutions (temizuya) d'environ 10 × 7 : dallage, quatre poteaux sur socles, poutres, toit à
    deux pans (tuiles, cuivre ou chaume), grand bassin de pierre plein d'eau, bec de bambou et filet d'eau,
    louches posées sur le bord, plaque 清水 suspendue à la poutre avant."""
    rng = b.rng
    S = _style(_TEMIZUYAS, variant, {"toit": ["tuile_ardoise", "cuivre_vert", "tuile", CHAUME]})
    poteau, poutre = col(S["poteau"]), col(S["poutre"])
    PX, PZ = 3.9, 2.4
    H = 6.6
    with b.group("Pavillon"):
        b.box((-5.0, 0, -3.5), (5.0, 0.3, 3.5), vr("pierre_claire", rng, 0.03), studs="top", name="Dallage")
        for sx in (-1, 1):
            for sz in (-1, 1):
                b.box((sx * PX - 0.5, 0.3, sz * PZ - 0.5), (sx * PX + 0.5, 0.8, sz * PZ + 0.5), col("pierre"), studs="top",
                      name="Socle")
                b.cyl((sx * PX, (0.8 + H) / 2, sz * PZ), 0.32, H - 0.8, poteau, axis="y", name="Poteau")
        for sz in (-1, 1):
            b.box((-PX - 0.7, H - 0.6, sz * PZ - 0.3), (PX + 0.7, H, sz * PZ + 0.3), poutre, name="Poutre")
        for sx in (-1, 1):
            b.box((sx * PX - 0.25, H - 0.55, -PZ - 0.35), (sx * PX + 0.25, H - 0.05, PZ + 0.35), poutre, name="Poutre")
        # plaque 清水 suspendue sous la poutre avant
        t, f, e = S["plaque"]
        for xx in (-1.0, 1.0):
            b.box((xx - 0.06, 5.75, -PZ - 0.06), (xx + 0.06, H - 0.5, -PZ + 0.06), col("noir"), collide=False, name="Cordon")
        b.box((-1.7, 4.45, -PZ - 0.3), (1.7, 5.85, -PZ + 0.0), poutre, collide=False, name="Cadre")
        p = b.box((-1.5, 4.6, -PZ - 0.45), (1.5, 5.7, -PZ - 0.25), col(f), collide=False, name="Plaque")
        p.label = {"face": "Front", "text": t, "color": col(e), "font": "brush"}
    with b.group("Bassin"):
        st = col(S["bassin"])
        b.box((-2.6, 0.3, -1.2), (2.6, 1.8, 1.2), vr(st, rng, 0.03), name="Bassin")
        b.box((-2.6, 1.8, -1.2), (2.6, 2.6, -0.8), st, studs="top", name="Rebord")
        b.box((-2.6, 1.8, 0.8), (2.6, 2.6, 1.2), st, studs="top", name="Rebord")
        for xa in (-2.6, 2.2):
            b.box((xa, 1.8, -0.8), (xa + 0.4, 2.6, 0.8), shade(st, 0.97), studs="top", name="Rebord")
        b.box((-2.2, 1.8, -0.8), (2.2, 2.38, 0.8), col("eau"), material="Glass", reflectance=0.15, name="Eau")
        # bec de bambou (kakei) et filet d'eau
        b.cyl((1.4, 1.95, 1.9), 0.2, 3.3, col("bambou_fonce"), axis="y", name="Support")
        b.cyl((1.4, 3.45, 0.85), 0.17, 2.3, col("bambou"), axis="z", name="Kakei")
        b.box((1.32, 2.35, -0.38), (1.48, 3.3, -0.22), col("eau_fonce"), transparency=0.35, collide=False, name="Filet")
        # louches (hishaku) posées en travers du bassin
        for xx in (-1.6, -0.5, 0.6):
            b.box((xx - 0.06, 2.62, -1.05), (xx + 0.06, 2.72, 1.05), col("bois_clair"), collide=False, name="Manche")
            b.cyl((xx, 2.82, -1.0), 0.28, 0.4, col("bois_clair"), axis="y", collide=False, name="Godet")
    with b.group("Toit"):
        if S["chaume"]:
            top, _ = _toit_hirairi(b, -PX - 0.3, PX + 0.3, -PZ - 0.3, PZ + 0.3, H, 0.85, S["toit"], S["poutre"], deb_av=1.5,
                                   deb_ar=1.5, deb_cote=1.1, ep=1.2, sori=0.7, rng=rng, faitage=CHAUME_FONCE, oni=False,
                                   blanc=False, fait=0.8)
            _croix_faitage(b, -PX, PX, 0.0, H + 2.7 * 0.85 + 1.2 * math.hypot(1, 0.85) + 0.35, n=3, long=1.3)
            top += 0.9
        else:
            top, _ = _toit_hirairi(b, -PX - 0.3, PX + 0.3, -PZ - 0.3, PZ + 0.3, H, 0.6, S["toit"], S["poutre"], deb_av=1.4,
                                   deb_ar=1.4, deb_cote=1.2, ep=0.7, sori=0.5, rng=rng, fait=0.6)
    if S["lanterne"]:
        with b.group("Lanterne"):
            _toro(b, -4.4, -2.9, "pierre", lumiere=True, h=0.75)
    return {"emprise": (10.0, 7.0), "hauteur": round(top, 2)}


# ---------------------------------------------------------------------------
# YATAI (échoppe ambulante)
# ---------------------------------------------------------------------------

_YATAIS = [
    # 0 : soba — noren bleus 蕎麦, lampion rouge, toit de tuiles bleu nuit, bols
    dict(noren=("noren_bleu", "blanc", "蕎麦"), toit="tuile", bois="bois", lampion=("rouge", False), plat="bols"),
    # 1 : dango — noren rouges 団子, lanterne de papier, toit de bardeaux, brochettes
    dict(noren=("noren_rouge", "blanc", "団子"), toit="bois_moyen", bois="bois_clair", lampion=("lampion_papier", True),
         plat="dango"),
    # 2 : thé — noren violets 茶, lanterne orange, toit d'ardoise, bouilloire
    dict(noren=("noren_violet", "blanc", "茶"), toit="tuile_ardoise", bois="bois_moyen", lampion=("orange_lampion", True),
         plat="the"),
    # 3 : douceurs — noren noirs 甘味, toit vermillon, lanterne de papier
    dict(noren=("noir", "blanc", "甘味"), toit="vermillon", bois="bois", lampion=("lampion_papier", True), plat="dango"),
]


def yatai(b, variant=0):
    """Échoppe ambulante (yatai) d'environ 8 × 5 : caisse sur deux grandes roues et deux pieds, brancards,
    comptoir stud, quatre montants, petit toit à deux pans, noren 蕎麦 / 団子 / 茶 / 甘味, lanterne, marchandises."""
    rng = b.rng
    S = _style(_YATAIS, variant, {"toit": ["tuile", "bois_moyen", "tuile_ardoise", "vermillon"]})
    bois = col(S["bois"])
    bf = col("bois_fonce")
    with b.group("Chariot"):
        for sx in (-1, 1):
            b.cyl((sx * 3.55, 1.25, 0.8), 1.25, 0.35, bf, axis="x", name="Roue")
            b.cyl((sx * 3.55, 1.25, 0.8), 0.95, 0.42, col("bois_moyen"), axis="x", name="Jante")
            b.cyl((sx * 3.62, 1.25, 0.8), 0.32, 0.6, col(FER), axis="x", name="Moyeu")
            b.box((sx * 2.7 - 0.18, 0, -1.15), (sx * 2.7 + 0.18, 1.45, -0.8), bf, name="Pied")
            b.box((sx * 2.4 - 0.15, 1.5, 1.9), (sx * 2.4 + 0.15, 1.8, 3.1), bf, name="Brancard")
        b.cyl((0, 1.25, 0.8), 0.14, 7.0, col(FER), axis="x", name="Essieu")
        b.box((-3.1, 1.45, -1.2), (3.1, 3.6, 2.0), vr(bois, rng, 0.03), name="Caisse")
        for xx in (-1.55, 1.55):
            b.box((xx - 1.3, 1.85, -1.32), (xx + 1.3, 3.2, -1.15), shade(bois, 0.85), name="Panneau")
        b.box((-3.4, 3.6, -2.0), (3.4, 3.95, 2.2), col("bois_clair"), studs="top", name="Comptoir")
        for sx in (-1, 1):
            for zz in (-1.05, 1.8):
                b.box((sx * 3.0 - 0.15, 3.95, zz - 0.15), (sx * 3.0 + 0.15, 6.1, zz + 0.15), bf, name="Montant")
        for zz in (-1.05, 1.8):
            b.box((-3.25, 6.1, zz - 0.2), (3.25, 6.5, zz + 0.2), bf, name="Traverse")
    with b.group("Etal"):
        if S["plat"] == "bols":
            for i, xx in enumerate((-2.2, -1.1, 0.0, 1.1)):
                b.cyl((xx, 4.2, -0.9), 0.42, 0.5, col(("noir", "rouge", "noir", "rouge")[i]), axis="y", studs="top",
                      collide=False, name="Bol")
            b.cyl((2.3, 4.55, 0.9), 0.7, 1.2, col("metal"), axis="y", name="Marmite")
        elif S["plat"] == "dango":
            b.box((-2.6, 3.95, -1.0), (1.0, 4.3, -0.2), col("bois_moyen"), studs="top", name="Plateau")
            for xx in (-2.2, -1.4, -0.6, 0.2):
                _dango(b, xx, 4.3, -0.6)
            b.cyl((2.2, 4.25, 0.8), 0.65, 0.6, col("noir"), axis="y", name="Brasero")
        else:
            b.cyl((-1.8, 4.55, 0.6), 0.65, 1.2, col("noir"), axis="y", name="Bouilloire")
            for xx in (-0.2, 0.6, 1.4):
                b.cyl((xx, 4.17, -0.9), 0.25, 0.45, col("blanc"), axis="y", collide=False, name="Tasse")
    with b.group("Toit"):
        top, dessous = _toit_hirairi(b, -3.25, 3.25, -1.25, 2.0, 6.5, 0.45, S["toit"], S["bois"], deb_av=0.9, deb_ar=0.6,
                                     deb_cote=0.55, ep=0.5, sori=0.55, rng=rng, oni=False, blanc=False, fait=0.5)
        nf, ne, nt = S["noren"]
        _noren(b, -2.8, 2.8, 6.1, 1.15, -1.35, nf, ne, nt, n=len(nt) if len(nt) > 1 else 3)
        lc, ln = S["lampion"]
        _chochin(b, 3.35, dessous(-1.8), -1.8, r=0.55, h=1.2, corps=lc, neon=ln)
    return {"emprise": (8.0, 5.0), "hauteur": round(top, 2)}
