"""Architecture d'arts martiaux de la zone (style temple chinois, tuiles vernissées orange), en style stud.

- `porte_temple`   : grande porte d'entrée (paifang) qui enjambe le couloir en z = 0, ailes et murs blancs
                     à chaperon de tuiles jusqu'aux falaises ;
- `statue_gardien` : lion gardien de pierre assis sur un haut socle ;
- `temple_tournoi` : temple d'arts martiaux à côté de l'arène des œufs (colonnade rouge, double toit) ;
- `tribune`        : gradins de spectateurs à auvent rayé ;
- `dojo`           : petite salle d'entraînement sur plancher surélevé ;
- `pagode`         : pagode à étages qui rétrécissent, flèche dorée en disques.

Repère : origine au centre de l'emprise au sol (y = 0), avant vers -Z local.
Toits chinois : avant-toit sombre, jupe peu pentue puis pignon plus raide (courbe creuse), coins relevés
faits de petits coins (wedges) montants, faîtage doré et ornements d'extrémité génériques (crosses).
Propriété intellectuelle : textes autorisés seulement (武, 道場, 修行, 武道, 気, 天), aucune sphère orange,
aucun dragon, aucun personnage (les statues sont des lions), aucun logo.
"""

from __future__ import annotations

import math

import numpy as np

from kit import hexrgb, mix, rot_y as _rot_y, shade
from palette import c, vary

TEXTES_AUTORISES = ("武", "道場", "修行", "武道", "気", "天")

# couleurs locales (peintures des charpentes chinoises, creux des fenêtres)
VERT_PEINT = hexrgb("#2FA593")      # vert-bleu des consoles (accent, jamais dominant)
BLEU_PEINT = hexrgb("#2F6FC8")
CREUX = c("hublot")                  # fond sombre des fenêtres « lune »


def _col(x):
    if x is None:
        return None
    return c(x) if isinstance(x, str) else tuple(int(v) for v in x)


def _texte(t: str) -> str:
    assert t in TEXTES_AUTORISES, f"texte non autorisé dans la zone : {t!r}"
    return t


def _repere(axe) -> np.ndarray:
    """Matrice de rotation dont la première colonne (axe X local) est `axe`, Y local au plus près du haut."""
    x = np.asarray(axe, float)
    x = x / np.linalg.norm(x)
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return np.column_stack([x, y, z])


def _barre(b, a, bb, ep_y, ep_z, col, name="Barre", **kw):
    """Bloc allongé de a à bb (arêtier, rampe), section ep_y × ep_z."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    n = float(np.linalg.norm(bb - a))
    return b.part("block", (n, ep_y, ep_z), (a + bb) / 2, _repere(bb - a), col, name=name, **kw)


# ---------------------------------------------------------------------------
# Toit chinois
# ---------------------------------------------------------------------------

def _toit(b, x0, x1, z0, z1, y, *, a=3.0, ax=None, h1=1.0, h2=2.0, ep=0.7, tuile="tuile_orange", fonce=None,
          claire=None, dessous="laque_rouge_fonce", faitage="or", ornement=None, pignon="laque_rouge",
          hanches=(True, True), releve=1.8, l_releve=4.5, cornes=(True, True), deb_g=0.6,
          ornements=(True, True), epi=False, aretiers=True, rng=None, medaillon="or", rive=True,
          h_orn=1.5, rd=0.7) -> dict:
    """Toit chinois sur l'avant-toit (x0..x1, z0..z1) dont le dessous est à y.

    - plaque d'avant-toit sombre (épaisseur `ep`) et sous-face peinte (`dessous`) ;
    - jupe à quatre pans peu pentue (profondeur `a` devant/derrière, `ax` aux bouts, hauteur `h1`) ;
      `hanches` = (bout x0, bout x1) : False → le bout est coupé net (il bute contre un pilier ou un mur) ;
    - si h2 > 0 : pignon central plus raide (courbe creuse), triangles de pignon (`pignon`), faîtage
      (`faitage`) et crosses d'extrémité (`ornements`) ; sinon le cœur plat reçoit des studs ;
    - coins relevés : deux petits coins montants qui se croisent à chaque angle (`cornes` par bout).
    Renvoie les cotes utiles (haut de jupe, faîtage, sommet)."""
    T, F = _col(tuile), _col(fonce) or shade(_col(tuile), 0.78)
    Cl = _col(claire) or shade(T, 1.22)
    Rf = _col(faitage) or F
    Orn = _col(ornement) or Rf
    ax = a if ax is None else ax
    tv = (lambda: vary(T, rng, 0.03)) if rng is not None else (lambda: T)
    hx0, hx1 = hanches
    if ep > 0:
        b.box((x0, y, z0), (x1, y + ep, z1), F, name="Avant_toit")
        if dessous is not None:
            b.box((x0 + 0.4, y - 0.25, z0 + 0.4), (x1 - 0.4, y, z1 - 0.4), _col(dessous), name="Sous_face")
    ys = y + ep
    xi0 = x0 + ax if hx0 else x0
    xi1 = x1 - ax if hx1 else x1
    zi0, zi1 = z0 + a, z1 - a
    zm = (z0 + z1) / 2
    b.wedge((x0, ys, z0), (x1, ys + h1, zi0), tv(), down="-z", studs="top", name="Jupe")
    b.wedge((x0, ys, zi1), (x1, ys + h1, z1), tv(), down="+z", studs="top", name="Jupe")
    if hx0:
        b.wedge((x0, ys, zi0), (xi0, ys + h1, zi1), tv(), down="-x", studs="top", name="Jupe")
    if hx1:
        b.wedge((xi1, ys, zi0), (x1, ys + h1, zi1), tv(), down="+x", studs="top", name="Jupe")
    ya = ys + h1
    b.box((xi0, ys, zi0), (xi1, ya, zi1), shade(T, 0.92), studs="top" if h2 <= 0 else "none", name="Coeur")
    if rive and ep > 0:
        # rang de tuiles de rive : liseré clair au bord de l'avant-toit, qui dessine l'égout vu d'en bas
        for zc, sz in ((z0, -1), (z1, 1)):
            za_, zb_ = sorted((zc + sz * 0.15, zc - sz * 0.6))
            b.box((x0, ys - 0.35, za_), (x1, ys + 0.2, zb_), Cl, collide=False, name="Rive")
        for xc, sx, hip in ((x0, -1, hx0), (x1, 1, hx1)):
            if hip:
                xa_, xb_ = sorted((xc + sx * 0.15, xc - sx * 0.6))
                b.box((xa_, ys - 0.35, z0 + 0.6), (xb_, ys + 0.2, z1 - 0.6), Cl, collide=False, name="Rive")
    # arêtiers : lignes claires qui soulignent les angles de la jupe
    if aretiers:
        for (xc, xi, hip_x), (zc, zi) in ((p, q) for p in ((x0, xi0, hx0), (x1, xi1, hx1)) for q in ((z0, zi0), (z1, zi1))):
            if not hip_x:
                continue
            sx = 1 if xi > xc else -1
            sz = 1 if zi > zc else -1
            _barre(b, (xc + sx * 0.5, ys + 0.25, zc + sz * 0.5), (xi, ya + 0.25, zi), 0.5, 0.6, Cl,
                   collide=False, name="Aretier")
    top = ya
    yr = ya
    xg0, xg1 = xi0, xi1
    if h2 > 0:
        xg0 = xi0 - deb_g if hx0 else x0
        xg1 = xi1 + deb_g if hx1 else x1
        b.wedge((xg0, ya, zi0), (xg1, ya + h2, zm), tv(), down="-z", studs="top", name="Pan")
        b.wedge((xg0, ya, zm), (xg1, ya + h2, zi1), tv(), down="+z", studs="top", name="Pan")
        yr = ya + h2
        run = zm - zi0
        pente = h2 / run
        if pignon is not None:
            d = min(0.8, run * 0.3)
            hr = h2 * (run - d) / run
            P = _col(pignon)
            for xe, s, hip in ((xg0, -1, hx0), (xg1, 1, hx1)):
                if not hip:
                    continue
                xa_, xb_ = sorted((xe + s * 0.15, xe - s * 0.3))
                b.wedge((xa_, ya, zi0 + d), (xb_, ya + hr, zm), P, down="-z", name="Pignon")
                b.wedge((xa_, ya, zm), (xb_, ya + hr, zi1 - d), P, down="+z", name="Pignon")
                if medaillon and hr > 1.4:
                    r_ = min(0.75, hr * 0.28)
                    xm_a, xm_b = sorted((xe + s * 0.15, xe + s * 0.35))
                    b.cyl(((xm_a + xm_b) / 2, ya + hr * 0.38, zm), r_, xm_b - xm_a, _col(medaillon), axis="x",
                          collide=False, shadow=False, name="Medaillon")
        yb_f = yr - rd * pente - 0.2
        hf = 0.5
        b.box((xg0 - 0.3, yb_f, zm - rd), (xg1 + 0.3, yr + hf, zm + rd), Rf, studs="top", name="Faitage")
        top = yr + hf
        for xe, s, on in ((xg0 - 0.3, -1, ornements[0]), (xg1 + 0.3, 1, ornements[1])):
            if not on or h_orn <= 0:
                continue
            # crosse d'extrémité générique (queue de poisson stylisée) : socle, corne relevée vers l'extérieur,
            # petite volute tournée vers le faîtage
            hb = h_orn * 0.45
            xa_, xb_ = sorted((xe + s * 0.2, xe - s * 1.5))
            b.box((xa_, yr + hf - 0.2, zm - rd + 0.05), (xb_, yr + hf + hb, zm + rd - 0.05), Orn, name="Crosse")
            b.wedge((xa_, yr + hf + hb, zm - rd + 0.05), (xb_, yr + h_orn + hf, zm + rd - 0.05), Orn,
                    down="+x" if s < 0 else "-x", name="Crosse")
            xv_a, xv_b = sorted((xe - s * 1.5, xe - s * 2.3))
            b.box((xv_a, yr + hf - 0.2, zm - 0.4), (xv_b, yr + hf + hb * 0.7, zm + 0.4), Orn, collide=False,
                  name="Volute")
            top = max(top, yr + hf + h_orn)
        if epi:
            xm = (xg0 + xg1) / 2
            top = max(top, _epi(b, xm, yr + hf, zm, Orn))
    # coins relevés
    r, L = releve, l_releve
    for (xc, sx, on, hip) in ((x0, -1, cornes[0], hx0), (x1, 1, cornes[1], hx1)):
        if not on:
            continue
        for zc, sz in ((z0, -1), (z1, 1)):
            xa_, xb_ = sorted((xc + sx * 0.5, xc - sx * L))
            za_, zb_ = sorted((zc + sz * 0.3, zc - sz * 1.0))
            b.wedge((xa_, ys - 0.15, za_), (xb_, ys + r, zb_), Cl, down="+x" if sx < 0 else "-x", studs="top",
                    collide=False, name="Coin_releve")
            if hip:
                xa_, xb_ = sorted((xc + sx * 0.3, xc - sx * 1.0))
                za_, zb_ = sorted((zc + sz * 0.5, zc - sz * min(L, (z1 - z0) / 2 - 0.5)))
                b.wedge((xa_, ys - 0.15, za_), (xb_, ys + r, zb_), Cl, down="+z" if sz < 0 else "-z", studs="top",
                        collide=False, name="Coin_releve")
            # pointe au bout de l'angle (petit coin qui file en diagonale vers le haut)
            yaw = math.degrees(math.atan2(sx, sz))
            b.part("wedge", (0.8, r * 0.7, 1.3), (xc + sx * 0.45, ys + r - 0.1 + r * 0.35, zc + sz * 0.45),
                   _rot_y(yaw), Orn, collide=False, shadow=False, name="Pointe")
    return {"ys": ys, "ya": ya, "yr": yr, "top": top, "xg0": xg0, "xg1": xg1, "zm": zm, "zi0": zi0, "zi1": zi1}


def _epi(b, x, y, z, col) -> float:
    """Épi de faîtage doré : disques empilés qui rétrécissent (jamais une boule). Renvoie le sommet."""
    for r, h in ((0.95, 0.45), (0.7, 0.5), (0.45, 0.9), (0.25, 0.8)):
        b.cyl((x, y + h / 2, z), r, h, col, collide=False, name="Epi")
        y += h
    return y


# ---------------------------------------------------------------------------
# Petits éléments
# ---------------------------------------------------------------------------

def _dougong(b, x, y, zf, s, *, h=1.8, larg=1.0, saillie=2.0):
    """Console dougong sur la face z = zf, saillie vers s (±1) : petit bloc vert, bras rouge, chapeau or,
    chaque étage débordant un peu plus (encorbellement)."""
    e = h / 3
    for k, (col, w, d) in enumerate(((VERT_PEINT, larg * 0.6, saillie * 0.45), (c("laque_rouge"), larg * 1.35, saillie * 0.72),
                                      (c("or"), larg * 0.8, saillie))):
        za, zb = sorted((zf - s * 0.2, zf + s * d))
        b.box((x - w, y + k * e, za), (x + w, y + (k + 1) * e, zb), col, collide=False, name="Dougong")


def _lanterne(b, x, y_haut, z, *, r=1.0, h=2.0, corps="laque_rouge"):
    """Lanterne rouge cylindrique suspendue (chapeaux dorés, gland) : le haut du cordon est à y_haut."""
    corps = _col(corps)
    b.box((x - 0.06, y_haut - 0.8, z - 0.06), (x + 0.06, y_haut, z + 0.06), c("encre"), collide=False, shadow=False,
          name="Cordon")
    yc = y_haut - 0.8 - 0.25 - h / 2
    b.cyl((x, y_haut - 0.8 - 0.12, z), r * 0.55, 0.25, c("or"), collide=False, name="Chapeau")
    b.cyl((x, yc, z), r * 0.85, h, corps, collide=False, shadow=False, name="Lanterne")
    b.cyl((x, yc, z), r, h * 0.55, corps, collide=False, shadow=False, name="Ventre")
    b.cyl((x, yc - h / 2 - 0.12, z), r * 0.55, 0.25, c("or"), collide=False, name="Chapeau")
    b.box((x - 0.14, yc - h / 2 - 1.2, z - 0.14), (x + 0.14, yc - h / 2 - 0.24, z + 0.14), c("or_fonce"),
          collide=False, shadow=False, name="Gland")


def _fenetre_lune(b, x, y, r, ez, *, cadre="pierre_claire", barreaux="laque_rouge", axe="z"):
    """Fenêtre « lune » qui traverse un mur d'épaisseur 2·ez : anneau clair, disque sombre en retrait des
    deux faces (dépasse de 0,1), treillis en # rouge. axe = normale du mur (z ou x)."""
    cad = _col(cadre)
    if axe == "z":
        b.cyl((x, y, 0), r + 0.55, 2 * ez + 0.2, cad, axis="z", collide=False, name="Cadre_lune")
        b.cyl((x, y, 0), r, 2 * ez + 0.4, CREUX, axis="z", collide=False, shadow=False, name="Lune")
        for d in (-r * 0.36, r * 0.36):
            hh = math.sqrt(max(r * r - d * d, 0.0)) * 0.98
            b.box((x + d - 0.18, y - hh, -ez - 0.35), (x + d + 0.18, y + hh, ez + 0.35), _col(barreaux),
                  collide=False, shadow=False, name="Treillis")
            b.box((x - hh, y + d - 0.18, -ez - 0.3), (x + hh, y + d + 0.18, ez + 0.3), _col(barreaux),
                  collide=False, shadow=False, name="Treillis")
    else:
        b.cyl((0, y, x), r + 0.55, 2 * ez + 0.2, cad, axis="x", collide=False, name="Cadre_lune")
        b.cyl((0, y, x), r, 2 * ez + 0.4, CREUX, axis="x", collide=False, shadow=False, name="Lune")
        for d in (-r * 0.36, r * 0.36):
            hh = math.sqrt(max(r * r - d * d, 0.0)) * 0.98
            b.box((-ez - 0.35, y - hh, x + d - 0.18), (ez + 0.35, y + hh, x + d + 0.18), _col(barreaux),
                  collide=False, shadow=False, name="Treillis")
            b.box((-ez - 0.3, y + d - 0.18, x - hh), (ez + 0.3, y + d + 0.18, x + hh), _col(barreaux),
                  collide=False, shadow=False, name="Treillis")


def _fenetre_treillis(b, x, y0, w, h, zf, s, *, cadre="laque_rouge", fond=None, barreaux="or", n=3, traverse=True):
    """Fenêtre à treillis plaquée sur la face z = zf (saillie vers s) : cadre, fond sombre, barreaux."""
    fond = _col(fond) or CREUX
    za, zb = sorted((zf - s * 0.1, zf + s * 0.25))
    b.box((x - w / 2 - 0.35, y0 - 0.35, za), (x + w / 2 + 0.35, y0 + h + 0.35, zb), _col(cadre), collide=False,
          name="Cadre")
    za2, zb2 = sorted((zf - s * 0.1, zf + s * 0.35))
    b.box((x - w / 2, y0, za2), (x + w / 2, y0 + h, zb2), fond, collide=False, shadow=False, name="Vitre")
    za3, zb3 = sorted((zf - s * 0.1, zf + s * 0.45))
    for i in range(n):
        xx = x - w / 2 + (i + 1) * w / (n + 1)
        b.box((xx - 0.12, y0, za3), (xx + 0.12, y0 + h, zb3), _col(barreaux), collide=False, shadow=False, name="Barreau")
    if traverse:
        b.box((x - w / 2, y0 + h / 2 - 0.12, za3), (x + w / 2, y0 + h / 2 + 0.12, zb3), _col(barreaux), collide=False,
              shadow=False, name="Barreau")


def _plaque(b, x, y0, w, h, zf, s, texte, *, fond="encre", encre="or", cadre="or", vertical=False):
    """Plaque à texte (SurfaceGui) sur la face z = zf, lisible depuis le côté s (-1 : face Front, +1 : Back),
    avec un cadre doré qui déborde tout autour."""
    za, zb = sorted((zf - s * 0.1, zf + s * 0.5))
    b.box((x - w / 2 - 0.5, y0 - 0.5, za), (x + w / 2 + 0.5, y0 + h + 0.5, zb), _col(cadre), collide=False,
          name="Cadre_plaque")
    za2, zb2 = sorted((zf - s * 0.1, zf + s * 0.7))
    p = b.box((x - w / 2, y0, za2), (x + w / 2, y0 + h, zb2), _col(fond), collide=False, name="Plaque")
    p.label = {"face": "Front" if s < 0 else "Back", "text": _texte(texte), "color": _col(encre), "font": "brush",
               "vertical": vertical}
    return p


# ---------------------------------------------------------------------------
# 1) Grande porte de temple (paifang) et murs d'enceinte
# ---------------------------------------------------------------------------

STYLES_PORTE = [
    # tuiles, faîtage/ornements, piliers, bagues des piliers
    dict(tuile="tuile_orange", faitage="or", pilier="laque_rouge", bague="or", extra=False),
    dict(tuile="tuile_verte", faitage="tuile_orange", pilier="laque_rouge", bague="or", extra=False),
    dict(tuile="tuile_orange", faitage="or", pilier="laque_rouge_fonce", bague="or", extra=True),
    dict(tuile="tuile_orange_fonce", faitage="or", pilier="laque_rouge", bague="noir", extra=True),
]


def porte_temple(b, variant=0, ouverture=76, hauteur=50, mur=124) -> dict:
    """Grande porte de temple (paifang à trois travées) qui enjambe le couloir en z = 0.

    Deux énormes piliers ronds rouges (faces intérieures à |x| = ouverture/2) sur socles de pierre et tambours,
    linteaux rouges et dorés, consoles dougong, plaque 武道 sur les deux faces, toit central surélevé et deux
    toits latéraux à coins relevés ; travées latérales murées à toit plus bas (|x| 44..56), puis murs blancs à
    chaperon de tuiles orange jusqu'à |x| = mur. Au-dessus du couloir, tout est à y ≥ 34."""
    rng = b.rng
    st = STYLES_PORTE[variant % len(STYLES_PORTE)]
    H = float(hauteur)
    tuile = st["tuile"]
    T = c(tuile)
    Rf = c(st["faitage"])
    pil = c(st["pilier"])
    rouge, rouge_f, orr = c("laque_rouge"), c("laque_rouge_fonce"), c("or")
    xo = ouverture / 2                 # 38 : faces intérieures des piliers
    rp = 3.0
    xp = xo + rp                       # 41 : axe des piliers
    xe = xp + rp                       # 44 : faces extérieures
    toit_kw = dict(tuile=tuile, faitage=st["faitage"], ornement=st["faitage"], rng=rng)

    # cotes verticales (au-dessus du couloir : tout au-dessus de 34)
    y_l1 = 34.2                        # linteau bas
    y_fr = y_l1 + 1.8                  # frise
    y_l2 = y_fr + 1.2                  # linteau haut
    y_pl = y_l2 + 1.8                  # plate-bande dorée
    y_dg = y_pl + 0.5                  # consoles
    y_tl = y_dg + 1.5                  # avant-toit des toits latéraux (≈ 41)
    y_tc = H - 4.8                     # avant-toit du toit central (≈ 45.2), au-dessus des faîtages latéraux

    with b.group("Piliers"):
        for s in (-1, 1):
            x = s * xp
            b.box((x - 4, 0, -4), (x + 4, 2.0, 4), c("pierre_fonce"), studs="top", name="Socle")
            b.cyl((x, 2.5, 0), rp + 0.7, 1.0, c("pierre_claire"), name="Tambour")
            b.cyl((x, 3.0 + (y_tl - 3.0) / 2, 0), rp, y_tl - 3.0, pil, name="Pilier")
            b.cyl((x, 3.6, 0), rp + 0.2, 1.0, c(st["bague"]), collide=False, name="Bague")
            for yb, col in ((28.6, st["bague"]), (29.5, "encre"), (30.1, st["bague"])):
                b.cyl((x, yb + 0.3, 0), rp + 0.2, 0.6, c(col), collide=False, name="Bague")
            # tambours de pierre (baogu shi) qui épaulent le pied du pilier, devant et derrière
            for sz in (-1, 1):
                za, zb = sorted((sz * 4.0, sz * 7.6))
                b.box((x - 1.2, 0, za), (x + 1.2, 2.6, zb), c("pierre"), studs="top", name="Baogu")
                b.cyl((x, 4.5, sz * 5.4), 1.9, 1.8, c("pierre_claire"), axis="x", name="Baogu_tambour")
                b.cyl((x, 4.5, sz * 5.4), 0.8, 2.0, c("pierre_fonce"), axis="x", collide=False, name="Baogu_rosace")
                # plaques verticales (couplets) sur la face du pilier
                txt = "修行" if s < 0 else "道場"
                zf = sz * 2.35
                za, zb = sorted((zf, zf + sz * 0.9))
                b.box((x - 2.0, 8.6, za), (x + 2.0, 21.4, zb), orr, collide=False, name="Cadre_couplet")
                za, zb = sorted((zf, zf + sz * 1.1))
                p = b.box((x - 1.6, 9.0, za), (x + 1.6, 21.0, zb), c("encre"), collide=False, name="Couplet")
                p.label = {"face": "Back" if sz > 0 else "Front", "text": txt, "color": orr, "font": "brush",
                           "vertical": True}
                # lanterne rouge suspendue à une console dorée
                za, zb = sorted((sz * 2.6, sz * 5.6))
                b.box((x - 0.35, 26.0, za), (x + 0.35, 26.6, zb), orr, collide=False, name="Console")
                _lanterne(b, x, 26.0, sz * 5.2, r=1.1, h=2.2)

    with b.group("Linteaux"):
        L = xe + 2.0
        b.box((-L, y_l1, -2.2), (L, y_fr, 2.2), rouge, name="Linteau")
        b.box((-L - 0.1, y_l1 + 0.75, -2.3), (L + 0.1, y_l1 + 1.25, 2.3), orr, collide=False, name="Filet")
        b.box((-L + 0.3, y_fr, -1.7), (L - 0.3, y_l2, 1.7), rouge_f, name="Frise")
        n = int((2 * L - 4) // 4)
        for i in range(n + 1):
            xx = -L + 2 + i * (2 * L - 4) / n
            if abs(xx) < 9.5:
                continue
            b.cyl((xx, (y_fr + y_l2) / 2, 0), 0.5, 3.8, orr, axis="z", collide=False, shadow=False, name="Rosace")
        b.box((-L, y_l2, -2.4), (L, y_pl, 2.4), rouge, name="Linteau")
        b.box((-L - 0.1, y_l2 + 0.75, -2.5), (L + 0.1, y_l2 + 1.25, 2.5), VERT_PEINT, collide=False, name="Filet")
        b.box((-L - 0.3, y_pl, -2.8), (L + 0.3, y_dg, 2.8), orr, name="Plate_bande")
        for s in (-1, 1):
            for y0_, y1_ in ((y_l1, y_fr), (y_l2, y_pl)):
                xa_, xb_ = sorted((s * L, s * (L + 0.25)))
                b.box((xa_, y0_ + 0.2, -2.0), (xb_, y1_ - 0.2, 2.0), orr, collide=False, name="Bout")
        # panneau de fond des consoles (on ne voit pas le ciel entre elles)
        b.box((-xe - 2, y_dg, -1.2), (xe + 2, y_tl, 1.2), rouge_f, name="Fond_consoles")
        for s in (-1, 1):
            for k in range(6):
                x = s * (22.8 + k * 4.3)
                for sz in (-1, 1):
                    _dougong(b, x, y_dg, sz * 2.6, sz, h=y_tl - y_dg, larg=0.9, saillie=2.6)

    with b.group("Plaque"):
        xc = 20.5
        b.box((-xc, y_l2, -1.8), (xc, y_tc, 1.8), rouge, name="Panneau_central")
        b.box((-xc - 0.2, y_tc - 1.9, -2.0), (xc + 0.2, y_tc - 1.5, 2.0), orr, collide=False, name="Filet")
        for sz in (-1, 1):
            _plaque(b, 0, y_l1 + 1.0, 15.0, 6.6, sz * 2.2, sz, "武道", fond="encre", encre="or", cadre="or")
            for x in (-18.0, -13.5, 13.5, 18.0):
                _dougong(b, x, y_tc - 1.6, sz * 1.8, sz, h=1.6, larg=0.85, saillie=2.4)

    with b.group("Toits"):
        # toit central surélevé (son sommet atteint H) : plus profond que les toits latéraux
        ep_c, h1_c, orn_c = 1.0, 0.8, 1.4
        _toit(b, -24.5, 24.5, -7.0, 7.0, y_tc, a=2.9, ax=3.2, h1=h1_c, h2=H - y_tc - ep_c - h1_c - 0.5 - orn_c,
              ep=ep_c, releve=2.1, l_releve=5.2, h_orn=orn_c, **toit_kw)
        # toits latéraux : le bout intérieur glisse sous l'avant-toit central (faîtage plus bas que lui)
        for s in (-1, 1):
            xa_, xb_ = sorted((s * 20.0, s * 52))
            _toit(b, xa_, xb_, -6.6, 6.6, y_tl, a=2.9, ax=3.2, h1=0.9, h2=H - 4.8 - y_tl - 1.0 - 0.9 - 0.75,
                  ep=1.0, releve=2.1, l_releve=5.2, rd=0.6, h_orn=1.8,
                  hanches=(s < 0, s > 0), cornes=(s < 0, s > 0), ornements=(s < 0, s > 0), **toit_kw)

    # travées latérales murées sous un toit plus bas
    xs = 55.0                          # axe des piliers secondaires
    y_ls = 19.0
    with b.group("Travees"):
        for s in (-1, 1):
            x = s * xs
            b.box((x - 2.4, 0, -2.4), (x + 2.4, 1.6, 2.4), c("pierre_fonce"), studs="top", name="Socle")
            b.box((x - 1.6, 1.6, -1.6), (x + 1.6, y_ls, 1.6), pil, name="Pilier")
            b.box((x - 1.75, 3.0, -1.75), (x + 1.75, 3.8, 1.75), c(st["bague"]), collide=False, name="Bague")
            xa_, xb_ = sorted((s * (xe - 1.0), s * (xs - 1.6)))
            b.box((xa_, 0, -2.0), (xb_, 1.6, 2.0), c("pierre"), studs="top", name="Soubassement")
            b.box((xa_, 1.6, -1.3), (xb_, y_ls, 1.3), vary("enduit", rng, 0.02), name="Mur")
            _fenetre_lune(b, s * (xe + xs - 1.6) / 2, 10.0, 3.0, 1.3)
            xa_, xb_ = sorted((s * (xe - 1.0), s * (xs + 1.8)))
            b.box((xa_, y_ls, -1.8), (xb_, y_ls + 2.2, 1.8), rouge, name="Linteau")
            b.box((xa_, y_ls + 0.8, -1.9), (xb_, y_ls + 1.3, 1.9), orr, collide=False, name="Filet")
            b.box((xa_, y_ls + 2.2, -2.1), (xb_, y_ls + 2.6, 2.1), orr, name="Plate_bande")
            for xx in (s * 47.5, s * 51.5):
                for sz in (-1, 1):
                    _dougong(b, xx, y_ls + 2.6, sz * 2.1, sz, h=1.5, larg=0.8, saillie=2.2)
            b.box((xa_, y_ls + 2.6, -1.0), (xb_, y_ls + 4.1, 1.0), rouge_f, name="Fond_consoles")
            xa_, xb_ = sorted((s * (xe - 1.5), s * (xs + 4.5)))
            r = _toit(b, xa_, xb_, -6.2, 6.2, y_ls + 4.1, a=3.0, ax=3.0, h1=0.9, h2=1.9, ep=0.6, releve=1.2,
                      l_releve=3.4, hanches=(s < 0, s > 0), cornes=(True, True), ornements=(s < 0, s > 0), **toit_kw)
            if st["extra"]:
                # étage de toit supplémentaire : tambour rouge et second toit plus petit
                xa2, xb2 = sorted((s * (xe + 2.0), s * (xs + 0.5)))
                b.box((xa2, r["ya"], -2.2), (xb2, r["ya"] + 3.2, 2.2), rouge, name="Tambour")
                b.box((xa2 - 0.1, r["ya"] + 2.0, -2.3), (xb2 + 0.1, r["ya"] + 2.5, 2.3), orr, collide=False, name="Filet")
                xa3, xb3 = sorted((s * (xe + 0.5), s * (xs + 2.5)))
                _toit(b, xa3, xb3, -4.4, 4.4, r["ya"] + 3.2, a=2.2, ax=2.2, h1=0.7, h2=1.6, ep=0.5, releve=1.0,
                      l_releve=2.6, **toit_kw)

    # murs d'enceinte blancs à chaperon de tuiles, fenêtres lune / treillis, contreforts
    with b.group("Murs"):
        x_debut = xs + 1.0
        n_seg = max(1, round((mur - x_debut) / 17))
        pas = (mur - x_debut) / n_seg
        hm = 9.4
        for s in (-1, 1):
            for k in range(n_seg):
                xa_, xb_ = sorted((s * (x_debut + k * pas), s * (x_debut + (k + 1) * pas)))
                b.box((xa_, 0, -2.0), (xb_, 1.0, 2.0), vary("pierre_fonce", rng, 0.04), studs="top", name="Soubassement")
                b.box((xa_, 1.0, -1.5), (xb_, hm, 1.5), vary("enduit", rng, 0.02), name="Mur")
                b.box((xa_, hm - 1.0, -1.6), (xb_, hm - 0.4, 1.6), rouge, collide=False, name="Bandeau")
                b.box((xa_ - 0.05, hm, -2.6), (xb_ + 0.05, hm + 0.6, 2.6), shade(T, 0.78), name="Chaperon")
                b.wedge((xa_, hm + 0.6, -2.6), (xb_, hm + 1.9, 0), vary(T, rng, 0.03), down="-z", studs="top",
                        name="Chaperon")
                b.wedge((xa_, hm + 0.6, 0), (xb_, hm + 1.9, 2.6), vary(T, rng, 0.03), down="+z", studs="top",
                        name="Chaperon")
                b.box((xa_ - 0.1, hm + 1.4, -0.55), (xb_ + 0.1, hm + 2.3, 0.55), Rf, studs="top", name="Faitage")
                xm = (xa_ + xb_) / 2
                if k % 2 == 0:
                    _fenetre_lune(b, xm, 5.4, 2.4, 1.5)
                else:
                    for sz in (-1, 1):
                        _fenetre_treillis(b, xm, 3.4, 4.4, 4.0, sz * 1.5, sz, cadre="pierre_claire", barreaux="laque_rouge")
            # contreforts entre les segments et au bout (contre la falaise)
            for k in range(1, n_seg + 1):
                x = s * (x_debut + k * pas)
                if k == n_seg:
                    x -= s * 1.0
                b.box((x - 0.9, 0, -3.0), (x + 0.9, 4.6, 3.0), vary("pierre", rng, 0.04), name="Contrefort")
                for sz in (-1, 1):
                    za, zb = sorted((sz * 1.5, sz * 3.0))
                    b.wedge((x - 0.9, 4.6, za), (x + 0.9, 6.4, zb), c("pierre_claire"), down="+z" if sz > 0 else "-z",
                            studs="top", name="Contrefort")
                b.box((x - 0.6, 4.6, -1.65), (x + 0.6, hm, 1.65), rouge, name="Pilastre")
    return {"emprise": (2 * mur, 16), "hauteur": H, "ouverture": ouverture}


# ---------------------------------------------------------------------------
# Fonctions encore à écrire
# ---------------------------------------------------------------------------

def statue_gardien(b, variant=0) -> dict:
    raise NotImplementedError


def temple_tournoi(b, variant=0, largeur=60, profondeur=34) -> dict:
    raise NotImplementedError


def tribune(b, variant=0, longueur=28, rangs=5) -> dict:
    raise NotImplementedError


def dojo(b, variant=0, largeur=24, profondeur=18) -> dict:
    raise NotImplementedError


def pagode(b, variant=0, etages=3) -> dict:
    raise NotImplementedError
