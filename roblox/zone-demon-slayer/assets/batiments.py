"""Bâtiments du village de l'ère Taishō et du sanctuaire de montagne (zone 3), style « stud ».

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :
- machiya      : maison de marchand à deux niveaux (treillis koshi, auvent, étage enduit, enseigne) ;
- auberge      : ryokan à trois niveaux (balcons, fenêtres éclairées, porche à fronton courbe, enseigne 宿) ;
- maison_the   : maison de thé ouverte (bancs à tissu rouge, grande ombrelle, menus, noren) ;
- kura         : entrepôt à murs épais d'enduit et soubassement namako ;
- sanctuaire   : pavillon de culte (socle de pierre, plancher surélevé, véranda, grand toit irimoya, cloche, shimenawa) ;
- temizuya     : pavillon des ablutions (bassin de pierre, louches, plaque 清水) ;
- yatai        : échoppe ambulante sur roues.

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

from kit import hexrgb, mix, rot_x, rot_z, shade
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
                  sori=0.5, rng=None, faitage=None, oni=True, pignons=True, blanc=True):
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
    b.box((xa - 0.15, yr - 0.6, zm - 0.95), (xb + 0.15, yr + 0.75, zm + 0.95), fa, studs="top", name="Faitage")
    if blanc:
        # liseré d'enduit blanc sous le faîtage (lits de tuiles noshi), lisible de loin
        b.box((xa, yr - 0.75, zm - 1.05), (xb, yr - 0.35, zm + 1.05), col("enduit"), name="Noshi")
    top = yr + 0.75
    if oni:
        for xe in (xa - 0.15, xb + 0.15):
            b.box((xe - 0.65, yr - 0.7, zm - 1.15), (xe + 0.65, yr + 1.55, zm + 1.15), shade(t, 0.58), name="Oni")
        top = yr + 1.55

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
    for (xa_, ya_, xb_, yb_, ea, eb) in ((x0, H + k + 0.2, xm, yr + 0.2, 0.25, 0.45), (xm, yr + 0.2, x1, H + k + 0.2, 0.45, 0.25),
                                         (x0 - deb, H - deb * pe + ke + 0.2, x0, H + ke + 0.2, 0.0, 0.2),
                                         (x1, H + ke + 0.2, x1 + deb, H - deb * pe + ke + 0.2, 0.2, 0.0)):
        _pan_x(b, xa_, ya_, xb_, yb_, z0h, z1h, ep + 0.55, hc, ext_a=ea, ext_b=eb, studs="none", name="Hafu")
    fa = col(faitage) if faitage else shade(t, 0.72)
    b.box((xm - 0.95, yr - 0.6, za - 0.5), (xm + 0.95, yr + 0.75, zb_ + 0.15), fa, studs="top", name="Faitage")
    b.box((xm - 1.15, yr - 0.7, za - 0.65), (xm + 1.15, yr + 1.5, za + 0.6), shade(t, 0.58), name="Oni")
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
    return yr + 1.5


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
         verticale=("呉服", "bois_clair", "noir"), udatsu=True, porte="droite", lampion=("lampion_papier", True)),
    # 1 : apothicaire — étage en planches sombres, baie à treillis avec sudare et garde-corps, toit ardoise
    dict(toit="tuile_ardoise", mur="enduit_creme", rdc="bois", cadre="bois_fonce", etage="sudare", fond=INTERIEUR,
         noren=("noren_violet", "blanc", "薬"), kanban_toit=None, verticale=("薬", "blanc", "noren_rouge"),
         udatsu=False, porte="gauche", lampion=("rouge", False), pied=True),
    # 2 : confiserie — boutique ouverte, étage crème à fenêtres vitrées éclairées, udatsu, lampions rouges
    dict(toit="tuile_claire", mur="enduit_creme", rdc="bois_moyen", cadre="bois_fonce", etage="vitres",
         fond="lampion_papier", noren=("noren_rouge", "blanc", "甘味"), kanban_toit=("茶", "bois_clair", "noir"),
         verticale=("甘味", "noren_rouge", "blanc"), udatsu=True, porte="gauche", lampion=("rouge", False), boutique=True),
    # 3 : soba — étage en encorbellement à balcon et shoji éclairés, toit bleu sombre, noren bleus
    dict(toit="tuile_fonce", mur="enduit", rdc="bois_fonce", cadre="bois_fonce", etage="balcon", fond=INTERIEUR,
         noren=("noren_bleu", "blanc", "蕎麦"), kanban_toit=None, verticale=("蕎麦", "noir_laque", "blanc"),
         udatsu=False, porte="droite", lampion=("orange_lampion", True)),
]


def machiya(b, variant=0, largeur=22, profondeur=18):
    """Maison de marchand de l'ère Taishō à deux niveaux : rez en bois sombre à treillis koshi (portes
    coulissantes, inuyarai, noren, lanterne), auvent stud entre les niveaux, étage d'enduit (mushiko-mado,
    sudare, fenêtres vitrées ou balcon), ailes udatsu, enseigne de toit et enseigne verticale, grand toit
    hirairi en tuiles bleu nuit ou ardoise à débord adouci."""
    rng = b.rng
    S = _style(_MACHIYA, variant, _ALT)
    v = variant % 4
    W, D = float(largeur), float(profondeur)
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    YS = 0.6                      # socle de pierre
    H1 = 9.0                      # naissance de l'auvent
    HS = H1 + 0.7                 # jonction bois / enduit (cachée sous l'auvent)
    H2 = 15.6                     # haut des murs
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
            b.box((za0, YK - 1.0, -0.75), (za1, YK - 0.1, -0.35), col(SUDARE), name="Store")
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
                _fenetre_shoji(b, 0, yw - 0.6, bw, 3.6, cadre, lumiere=True, croix=5, appui=False)
                _sudare(b, 0, yw + 3.05, bw - 0.4, 2.2, z=-0.5)
                _garde_corps(b, -bw / 2 - 0.4, bw / 2 + 0.4, yw - 0.95, -1.3, cadre, h=1.5, pas=1.6)
                b.box((-bw / 2 - 0.6, yw - 1.25, -1.6), (bw / 2 + 0.6, yw - 0.95, 0.3), cadre, studs="top", name="Plancher")
                for xx in (-W / 2 + 2.4, W / 2 - 2.4):
                    if abs(xx) > bw / 2 + 1.8:
                        _mushiko(b, xx, yw, 1.8, 2.2, "enduit_creme", n=2)
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
        with b.at((0, 0, zb), yaw=180):
            _fenetre_shoji(b, W / 5, H1 + 2.4, 4.0, 2.4, cadre, lumiere=False, croix=2)
            b.box((-W / 4 - 1.4, YS, -0.12), (-W / 4 + 1.4, 7.0, 0.3), cadre, name="Porte")
            b.box((-W / 4 - 1.9, 7.0, -0.4), (-W / 4 + 1.9, 7.5, 0.3), cadre, name="Linteau")

    # --- toit ----------------------------------------------------------------------------------------------
    with b.group("Toit"):
        top, _ = _toit_hirairi(b, x0, x1, zf, zb, H2, 0.42, S["toit"], mur, deb_av=2.4, deb_ar=1.2, deb_cote=0.6,
                               ep=0.8, sori=0.5, rng=rng)
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
         lampion=("lampion_papier", True), tour=False, verticale=True),
    # 2 : ryokan crème à tour de guet, toits de cuivre patiné, porche kara-hafu, lampions rouges
    dict(toit="cuivre_vert", mur="enduit_creme", rdc="bois", cadre="bois_fonce", garde="bois_fonce", porche="kara",
         hafu="bois_fonce", poteau="bois_fonce", noren=("noren_rouge", "blanc", "宿"), enseigne=("宿", "noir_laque", "blanc"),
         lampion=("rouge", False), tour=True),
    # 3 : quartier des fleurs : garde-corps et poteaux vermillon, toit bleu sombre, lanternes blanches
    dict(toit="tuile_fonce", mur="enduit", rdc="bois_fonce", cadre="bois_fonce", garde="vermillon", porche="kara",
         hafu="vermillon_fonce", poteau="vermillon", noren=("noren_violet", "blanc", "藤"), enseigne=("宿", "vermillon", "blanc"),
         lampion=("lampion_papier", True), tour=False),
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
            top_p, dessus = _kara_hafu(b, 0, za_p, zA + 0.3, y0, larg, hk, S["toit"], S["hafu"], ep=0.7, rng=rng)
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
            top_p = _toit_tsumairi(b, -wp / 2, wp / 2, zpo - 0.4, zA, Yb, 0.62, S["toit"], S["cadre"], deb=0.9, deb_av=0.6,
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
        with b.at((0, 0, zb), yaw=180):
            for yy in (H1 + 1.8, H2 + 1.6):
                for xc in (-W / 4, W / 4):
                    _fenetre_simple(b, xc, yy, 4.0, 2.6, cadre, lumiere=(xc < 0 and yy > H2))
            b.box((-1.6, YS, -0.12), (1.6, 7.0, 0.3), cadre, name="Porte")

    # --- toit ------------------------------------------------------------------------------------------------
    with b.group("Toit"):
        dav, dar, dco = 2.6, 1.3, 1.2
        R = _toit_irimoya(b, x0 - dco, x1 + dco, zA - dav, zb + dar, H3, S["toit"], a_z0=dav + 2.0, a_z1=dar + 2.0,
                          a_x0=dco + 3.2, a_x1=dco + 3.2, h1=2.2, h2=0.62 * ((zb - zA) / 2 - 2.0),
                          tri=mur, rng=rng, gegyo=S["cadre"])
        top = R["top"]
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
