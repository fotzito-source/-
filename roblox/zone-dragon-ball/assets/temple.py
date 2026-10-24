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
          h_orn=1.5, rd=0.7, pignon_bouts=False, pointes=True) -> dict:
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
                if not hip and not pignon_bouts:
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
            if not pointes:
                continue
            # pointe au bout de l'angle (petit coin qui file en diagonale vers le haut)
            yaw = math.degrees(math.atan2(sx, sz))
            b.part("wedge", (0.8, r * 0.7, 1.3), (xc + sx * 0.45, ys + r - 0.1 + r * 0.35, zc + sz * 0.45),
                   _rot_y(yaw), Orn, collide=False, shadow=False, name="Pointe")
    return {"ys": ys, "ya": ya, "yr": yr, "top": top, "xg0": xg0, "xg1": xg1, "zm": zm, "zi0": zi0, "zi1": zi1}


EPI = ((0.95, 0.45), (0.7, 0.5), (0.45, 0.9), (0.25, 0.8))
EPI_H = sum(h for _, h in EPI)


def _epi(b, x, y, z, col) -> float:
    """Épi de faîtage doré : disques empilés qui rétrécissent (jamais une boule). Renvoie le sommet."""
    for r, h in EPI:
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


def _plaque(b, x, y0, w, h, zf, s, texte, *, fond="encre", encre="or", cadre="or", vertical=False, marge=0.5):
    """Plaque à texte (SurfaceGui) sur la face z = zf, lisible depuis le côté s (-1 : face Front, +1 : Back),
    avec un cadre doré qui déborde tout autour."""
    za, zb = sorted((zf - s * 0.1, zf + s * 0.5))
    b.box((x - w / 2 - marge, y0 - marge, za), (x + w / 2 + marge, y0 + h + marge, zb), _col(cadre), collide=False,
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
        _toit(b, -24.5, 24.5, -6.8, 6.8, y_tc, a=2.8, ax=3.2, h1=h1_c, h2=H - y_tc - ep_c - h1_c - 0.5 - orn_c,
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
                ea = 0.05 if (k > 0 or s > 0) and not (k == n_seg - 1 and s < 0) else 0.0
                eb = 0.05 if (k > 0 or s < 0) and not (k == n_seg - 1 and s > 0) else 0.0
                b.box((xa_ - ea, hm, -2.6), (xb_ + eb, hm + 0.6, 2.6), shade(T, 0.78), name="Chaperon")
                b.wedge((xa_, hm + 0.6, -2.6), (xb_, hm + 1.9, 0), vary(T, rng, 0.03), down="-z", studs="top",
                        name="Chaperon")
                b.wedge((xa_, hm + 0.6, 0), (xb_, hm + 1.9, 2.6), vary(T, rng, 0.03), down="+z", studs="top",
                        name="Chaperon")
                b.box((xa_ - 2 * ea, hm + 1.4, -0.55), (xb_ + 2 * eb, hm + 2.3, 0.55), Rf, studs="top", name="Faitage")
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



def _fenetre_ronde(b, x, y, r, zf, s, *, cadre="laque_rouge", fond=None, barreaux="or"):
    """Fenêtre ronde plaquée sur la face z = zf (saillie vers s) : anneau, disque sombre, croisillon."""
    fond = _col(fond) or CREUX
    za, zb = sorted((zf - s * 0.1, zf + s * 0.3))
    b.cyl((x, y, (za + zb) / 2), r + 0.45, zb - za, _col(cadre), axis="z", collide=False, name="Cadre_rond")
    za, zb = sorted((zf - s * 0.1, zf + s * 0.4))
    b.cyl((x, y, (za + zb) / 2), r, zb - za, fond, axis="z", collide=False, shadow=False, name="Vitre")
    za, zb = sorted((zf - s * 0.1, zf + s * 0.5))
    b.box((x - 0.13, y - r * 0.96, za), (x + 0.13, y + r * 0.96, zb), _col(barreaux), collide=False, shadow=False,
          name="Barreau")
    b.box((x - r * 0.96, y - 0.13, za), (x + r * 0.96, y + 0.13, zb), _col(barreaux), collide=False, shadow=False,
          name="Barreau")


def _brasero(b, x, z, *, h=2.2):
    """Brasero de pierre et de bronze, flamme en blocs lumineux (jamais une boule)."""
    b.box((x - 1.2, 0, z - 1.2), (x + 1.2, 0.6, z + 1.2), c("pierre_fonce"), studs="top", name="Socle")
    b.box((x - 0.6, 0.6, z - 0.6), (x + 0.6, h, z + 0.6), c("pierre"), name="Fut")
    b.cyl((x, h + 0.5, z), 1.3, 1.0, c("bronze"), name="Bassin")
    b.cyl((x, h + 1.05, z), 1.42, 0.2, shade(c("bronze"), 0.8), collide=False, name="Rebord")
    b.boxc((x, h + 1.7, z), (1.6, 1.2, 1.6), c("flamme"), yaw=10, material="Neon", collide=False, shadow=False,
           name="Flamme")
    b.boxc((x + 0.1, h + 2.6, z - 0.1), (0.9, 1.1, 0.9), c("flamme"), yaw=35, material="Neon", collide=False,
           shadow=False, name="Flamme")
    b.boxc((x, h + 1.9, z), (0.9, 1.3, 1.8), c("flamme_coeur"), yaw=55, material="Neon", collide=False, shadow=False,
           name="Coeur")


def _balustrade(b, a, bb, y, *, pas=3.4, h=1.6, poteau="pierre_claire", lisse="pierre_claire", ep=0.5):
    """Balustrade de marbre blanc du point a au point bb (même z ou même x), posée au niveau y."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    n = max(1, int(round(np.linalg.norm(bb - a) / pas)))
    for i in range(n + 1):
        p_ = a + (bb - a) * i / n
        b.box((p_[0] - 0.4, y, p_[2] - 0.4), (p_[0] + 0.4, y + h + 0.4, p_[2] + 0.4), _col(poteau), name="Balustre")
    lo, hi = np.minimum(a, bb), np.maximum(a, bb)
    b.box((lo[0] - ep / 2, y + h - 0.45, lo[2] - ep / 2), (hi[0] + ep / 2, y + h, hi[2] + ep / 2), _col(lisse),
          name="Main_courante")
    b.box((lo[0] - ep / 2 + 0.05, y + 0.25, lo[2] - ep / 2 + 0.05), (hi[0] + ep / 2 - 0.05, y + 0.55, hi[2] + ep / 2 - 0.05),
          _col(lisse), collide=False, name="Lisse")


# ---------------------------------------------------------------------------
# 2) Lion gardien de pierre
# ---------------------------------------------------------------------------

def statue_gardien(b, variant=0) -> dict:
    """Lion gardien chinois de pierre (shishi), assis sur un haut socle, tourné vers -Z.

    variant 0 : patte avant posée sur une boule de pierre ; 1 : patte sur un lionceau ;
    2 : gueule ouverte et crinière plus grosse ; 3 : boule de pierre et gueule ouverte."""
    v = variant % 4
    p, pc, pf = c("pierre"), c("pierre_claire"), c("pierre_fonce")
    lion = mix(pc, c("sable"), 0.35)                  # pierre chaude, lisible sur le socle gris
    lion_f = shade(lion, 0.86)
    crin = mix(pf, c("ocre_fonce"), 0.25)             # crinière plus sombre : elle encadre la face
    boucle = shade(crin, 1.12)
    with b.group("Socle"):
        b.box((-3.4, 0, -4.4), (3.4, 0.8, 4.4), pf, studs="top", name="Base")
        b.box((-3.0, 0.8, -4.0), (3.0, 3.6, 4.0), p, name="De")
        b.box((-2.3, 1.4, -4.15), (2.3, 3.0, 3.6), pf, collide=False, name="Panneau")
        b.box((-3.3, 3.6, -4.3), (3.3, 4.2, 4.3), pc, studs="top", name="Corniche")
        b.box((-2.7, 4.2, -3.7), (2.7, 4.6, 3.5), c("laque_rouge"), studs="top", name="Coussin")
        b.box((-2.8, 4.25, -3.8), (2.8, 4.45, 3.6), c("or"), collide=False, name="Galon")
    y0 = 4.6
    big = v in (2, 3)
    with b.group("Lion"):
        b.box((-2.2, y0, 0.0), (2.2, y0 + 2.6, 3.3), lion, name="Arriere_train")
        for sx in (-1, 1):
            xa_, xb_ = sorted((sx * 1.2, sx * 2.45))
            b.box((xa_, y0, -1.1), (xb_, y0 + 1.0, 0.6), lion_f, name="Patte_arriere")
        b.box((-1.8, y0 + 1.8, -2.2), (1.8, y0 + 4.6, 1.6), lion, name="Poitrail")
        # pattes avant ; la patte +x (v 0, 3) se pose sur une boule, la patte -x (v 1) sur un lionceau
        for sx in (-1, 1):
            xa_, xb_ = sorted((sx * 0.45, sx * 1.85))
            leve = (sx > 0 and v in (0, 3)) or (sx < 0 and v == 1)
            yb = y0 + (2.1 if leve else 0.0)
            b.box((xa_, yb + 0.6, -2.7), (xb_, y0 + 3.6, -1.3), lion, name="Patte_avant")
            pa, pb = sorted((sx * 0.35, sx * 2.0))
            b.box((pa, yb, -3.7), (pb, yb + 0.8, -2.2), lion_f, name="Patte")
        if v in (0, 3):
            b.ball((1.2, y0 + 1.05, -3.0), 1.1, c("rocher_clair"), name="Boule_pierre")
        if v == 1:
            b.box((-2.5, y0, -4.1), (-0.3, y0 + 1.1, -2.3), lion, name="Lionceau")
            b.box((-2.2, y0 + 0.5, -4.35), (-0.9, y0 + 1.8, -3.3), lion_f, name="Lionceau_tete")
            b.box((-2.35, y0 + 1.1, -3.6), (-0.75, y0 + 2.05, -3.1), crin, collide=False, name="Lionceau_criniere")
        # crinière qui encadre la face, tête, boucles
        mx = 2.95 if big else 2.7
        mt = y0 + (7.9 if big else 7.6)
        b.box((-mx, y0 + 3.4, -2.5), (mx, mt, 1.2), crin, name="Criniere")
        b.box((-2.2, y0 + 2.6, 1.2), (2.2, y0 + 6.4, 2.1), crin, name="Criniere_dos")
        b.box((-1.9, y0 + 4.3, -3.5), (1.9, y0 + 7.2, -2.3), lion, name="Tete")
        for x in (-1.15, 0.0, 1.15):
            b.box((x - 0.48, y0 + 7.15, -3.3), (x + 0.48, y0 + 7.85, -2.3), boucle, collide=False, name="Boucle")
        for sx in (-1, 1):
            for yy in (y0 + 4.0, y0 + 5.5):
                xa_, xb_ = sorted((sx * 2.0, sx * (mx - 0.1)))
                b.box((xa_, yy, -2.8), (xb_, yy + 0.95, -2.45), boucle, collide=False, name="Boucle")
        b.box((-1.3, y0 + 4.3, -4.1), (1.3, y0 + 5.6, -3.4), lion, name="Museau")
        b.box((-0.85, y0 + 5.2, -4.25), (0.85, y0 + 5.85, -3.9), crin, collide=False, name="Nez")
        if big:
            b.box((-1.05, y0 + 4.25, -4.15), (1.05, y0 + 5.05, -3.6), c("laque_rouge_fonce"), collide=False, name="Gueule")
            for sx in (-1, 1):
                xa_, xb_ = sorted((sx * 0.45, sx * 0.85))
                b.box((xa_, y0 + 4.7, -4.25), (xb_, y0 + 5.05, -3.95), c("blanc"), collide=False, shadow=False, name="Croc")
        else:
            b.box((-0.95, y0 + 4.5, -4.15), (0.95, y0 + 4.8, -3.95), c("laque_rouge_fonce"), collide=False, name="Bouche")
        for sx in (-1, 1):
            xa_, xb_ = sorted((sx * 0.4, sx * 1.4))
            b.box((xa_, y0 + 5.9, -3.65), (xb_, y0 + 6.6, -3.4), c("or"), collide=False, shadow=False, name="Oeil")
            xa_, xb_ = sorted((sx * 0.65, sx * 1.05))
            b.box((xa_, y0 + 6.0, -3.72), (xb_, y0 + 6.45, -3.55), c("encre"), collide=False, shadow=False, name="Pupille")
        b.box((-1.85, y0 + 6.6, -3.75), (1.85, y0 + 7.15, -3.3), crin, collide=False, name="Sourcils")
        # collier rouge et grelot doré
        b.box((-1.95, y0 + 3.75, -2.35), (1.95, y0 + 4.25, 1.4), c("laque_rouge"), collide=False, name="Collier")
        b.cyl((0, y0 + 3.45, -2.5), 0.5, 0.6, c("or"), axis="z", collide=False, shadow=False, name="Grelot")
        # queue en panache
        b.box((-0.6, y0 + 1.8, 3.2), (0.6, y0 + 5.0, 4.0), crin, name="Queue")
        b.box((-0.95, y0 + 4.6, 2.5), (0.95, y0 + 5.9, 4.15), boucle, collide=False, name="Panache")
    return {"emprise": (6.8, 8.8), "hauteur": round(mt - 0.0, 2) if mt > y0 + 7.85 else round(y0 + 7.85, 2)}


# ---------------------------------------------------------------------------
# 3) Temple d'arts martiaux de la place des œufs
# ---------------------------------------------------------------------------

STYLES_TEMPLE = [
    dict(tuile="tuile_orange", faitage="or", ornement="or"),
    dict(tuile="tuile_verte", faitage="tuile_orange", ornement="tuile_orange"),
    dict(tuile="tuile_orange", faitage="or", ornement="or"),
    dict(tuile="tuile_orange_fonce", faitage="or", ornement="or"),
]


def _tour(b, x, z, w, d, y0, h, toit_kw, *, rng=None, fenetres_x=0):
    """Tour d'angle (pavillon) : murs blancs à poteaux rouges, fenêtres rondes, toit en pavillon à deux jupes
    et épi doré. fenetres_x = côté (±1) qui reçoit aussi des fenêtres sur la face x (0 : aucune)."""
    rouge = c("laque_rouge")
    x0, x1, z0, z1 = x - w / 2, x + w / 2, z - d / 2, z + d / 2
    b.box((x0, y0, z0), (x1, y0 + h, z1), vary("enduit", rng, 0.02) if rng is not None else c("enduit"), name="Mur")
    b.box((x0 - 0.1, y0, z0 - 0.1), (x1 + 0.1, y0 + 1.2, z1 + 0.1), c("laque_rouge_fonce"), name="Plinthe")
    for xx in (x0, x1):
        for zz in (z0, z1):
            b.box((xx - 0.45, y0, zz - 0.45), (xx + 0.45, y0 + h, zz + 0.45), rouge, name="Poteau")
    b.box((x0 - 0.25, y0 + h - 1.4, z0 - 0.25), (x1 + 0.25, y0 + h, z1 + 0.25), rouge, name="Bandeau")
    b.box((x0 - 0.35, y0 + h - 0.9, z0 - 0.35), (x1 + 0.35, y0 + h - 0.6, z1 + 0.35), c("or"), collide=False,
          name="Filet")
    # porte et fenêtres rondes sur la face avant (z0)
    b.box((x - 1.3, y0, z0 - 0.3), (x + 1.3, y0 + 4.2, z0 + 0.1), c("laque_rouge_fonce"), collide=False, name="Porte")
    b.box((x - 1.6, y0 + 4.2, z0 - 0.35), (x + 1.6, y0 + 4.6, z0 + 0.1), c("or"), collide=False, name="Linteau")
    for yy in (y0 + h * 0.45, y0 + h * 0.72):
        _fenetre_ronde(b, x, yy, 1.1, z0, -1, cadre="laque_rouge", barreaux="or")
    if fenetres_x:
        xf = x1 if fenetres_x > 0 else x0
        with b.at((xf, 0, z), yaw=-90 * fenetres_x):
            for yy in (y0 + h * 0.45, y0 + h * 0.72):
                _fenetre_ronde(b, 0, yy, 1.1, 0.0, -1, cadre="laque_rouge", barreaux="or")
    r = _toit(b, x0 - 1.1, x1 + 1.1, z0 - 1.6, z1 + 1.6, y0 + h, a=2.0, ax=1.6, h1=1.3, h2=0, ep=0.7, releve=1.6,
              l_releve=2.8, aretiers=True, pointes=False, **toit_kw)
    r2 = _toit(b, x0 + 0.5, x1 - 0.5, z0 + 0.3, z1 - 0.3, r["ya"], a=1.5, ax=1.3, h1=1.3, h2=0, ep=0, cornes=(False, False),
               aretiers=False, rive=False, **toit_kw)
    return _epi(b, x, r2["ya"], z, _col(toit_kw.get("ornement") or "or"))


def temple_tournoi(b, variant=0, largeur=60, profondeur=34) -> dict:
    """Temple d'arts martiaux à côté de l'arène : podium de pierre à grand escalier et balustrade de marbre,
    colonnade rouge, murs blancs, grande porte rouge cloutée d'or, consoles dougong, double toit à coins relevés
    (jupe basse puis toit à croupe et pignon), plaque 武 sous l'avant-toit haut, deux tours d'angle à toit en
    pavillon, braseros au pied de l'escalier. L'avant (z = -profondeur/2) regarde l'arène.

    variant 0 : tuiles orange ; 1 : tuiles vertes à faîtages orange ; 2 : pavillon central plus haut ;
    3 : tuiles orange foncé."""
    rng = b.rng
    v = variant % 4
    st = STYLES_TEMPLE[v]
    W, D = largeur / 2, profondeur / 2
    zf = -D                                    # avant (pied de l'escalier)
    rouge, rouge_f, orr = c("laque_rouge"), c("laque_rouge_fonce"), c("or")
    toit_kw = dict(tuile=st["tuile"], faitage=st["faitage"], ornement=st["ornement"], rng=rng)
    yp = 3.0                                   # dessus du podium
    zp0, zp1 = zf + 5.4, D - 1.4               # podium (l'escalier occupe zf..zp0)
    xpod = W - 0.4

    with b.group("Podium"):
        b.box((-xpod - 0.4, 0, zp0 - 0.4), (xpod + 0.4, 1.0, zp1 + 0.4), c("pierre_fonce"), studs="top", name="Assise")
        b.box((-xpod, 1.0, zp0), (xpod, yp, zp1), vary("pierre", rng, 0.02), studs="top", name="Podium")
        b.box((-xpod - 0.1, 1.9, zp0 - 0.1), (xpod + 0.1, 2.3, zp1 + 0.1), c("pierre_claire"), collide=False, name="Corniche")
        # escalier frontal (5 marches) et limons
        n = 5
        for j in range(n):
            za_ = zf + 0.4 + j * (zp0 - zf - 0.4) / n
            b.box((-11, 0, za_), (11, yp * (j + 1) / n, za_ + (zp0 - zf - 0.4) / n), c("pierre_claire"), studs="top",
                  name="Marche")
        for sx in (-1, 1):
            xa_, xb_ = sorted((sx * 11, sx * 12.4))
            b.box((xa_, 0, zf + 0.2), (xb_, 1.4, zp0), c("pierre"), studs="top", name="Limon")
            b.wedge((xa_, 1.4, zf + 0.2), (xb_, yp + 1.2, zp0), c("pierre"), down="-z", name="Limon")
            b.box((xa_ - 0.1, 0, zf), (xb_ + 0.1, 2.0, zf + 1.4), c("pierre_claire"), studs="top", name="Borne")
        # balustrade de marbre blanc sur le bord du podium
        for sx in (-1, 1):
            _balustrade(b, (sx * 12.6, 0, zp0 + 0.5), (sx * (xpod - 0.5), 0, zp0 + 0.5), yp)
            _balustrade(b, (sx * (xpod - 0.5), 0, zp0 + 4.5), (sx * (xpod - 0.5), 0, zp1 - 0.5), yp, pas=4.2)

    # salle principale
    xh, zh0, zh1 = 17.0, zf + 13.0, D - 4.6    # murs de la salle (avant à zh0)
    zc = zh0 - 5.0                             # colonnade
    y_col = 15.0
    with b.group("Salle"):
        b.box((-xh, yp, zh0), (xh, y_col, zh1), vary("enduit", rng, 0.015), name="Murs")
        b.box((-xh - 0.1, yp, zh0 - 0.1), (xh + 0.1, yp + 1.5, zh1 + 0.1), rouge_f, name="Plinthe")
        # grande porte rouge cloutée d'or
        b.box((-4.0, yp, zh0 - 0.35), (4.0, yp + 9.2, zh0 + 0.1), rouge_f, collide=False, name="Encadrement")
        b.box((-4.2, yp + 9.2, zh0 - 0.45), (4.2, yp + 9.8, zh0 + 0.1), orr, collide=False, name="Linteau_porte")
        for sx in (-1, 1):
            xa_, xb_ = sorted((sx * 0.06, sx * 3.5))
            b.box((xa_, yp, zh0 - 0.6), (xb_, yp + 8.8, zh0 - 0.2), rouge, collide=False, name="Vantail")
            for i in range(3):
                for j in range(3):
                    xx = sx * (0.9 + i * 1.05)
                    yy = yp + 2.6 + j * 1.9
                    b.box((xx - 0.22, yy - 0.22, zh0 - 0.78), (xx + 0.22, yy + 0.22, zh0 - 0.5), orr, collide=False,
                          shadow=False, name="Clou")
            b.cyl((sx * 0.75, yp + 4.4, zh0 - 0.75), 0.45, 0.3, orr, axis="z", collide=False, shadow=False, name="Heurtoir")
        for sx in (-1, 1):
            _fenetre_treillis(b, sx * 8.2, yp + 3.6, 4.6, 5.2, zh0, -1, cadre="laque_rouge", barreaux="or", n=4)
            _fenetre_ronde(b, sx * 14.4, yp + 6.4, 1.8, zh0, -1, cadre="laque_rouge", barreaux="or")
            with b.at((sx * xh, 0, (zh0 + zh1) / 2), yaw=-90 * sx):
                _fenetre_treillis(b, 0, yp + 3.6, 5.0, 5.2, 0.0, -1, cadre="laque_rouge", barreaux="or", n=4)
        # colonnade rouge (6 colonnes rondes) et poutres
        for x in (-18, -10.8, -3.6, 3.6, 10.8, 18):
            b.cyl((x, yp + 0.35, zc), 1.45, 0.7, c("pierre_claire"), name="Base")
            b.cyl((x, (yp + 0.7 + y_col) / 2, zc), 1.0, y_col - yp - 0.7, rouge, name="Colonne")
            b.cyl((x, y_col - 1.2, zc), 1.1, 0.5, orr, collide=False, name="Bague")
        b.box((-19.5, y_col, zc - 1.0), (19.5, y_col + 1.6, zc + 1.0), rouge, name="Linteau")
        b.box((-19.6, y_col + 0.5, zc - 1.1), (19.6, y_col + 1.0, zc + 1.1), VERT_PEINT, collide=False, name="Frise")
        for x in (-16.2, -12.6, -9.0, -5.4, 5.4, 9.0, 12.6, 16.2):
            b.cyl((x, y_col + 0.75, zc - 1.05), 0.42, 0.3, orr, axis="z", collide=False, shadow=False, name="Rosace")
        for sx in (-1, 1):
            xa_, xb_ = sorted((sx * 17.4, sx * 18.6))
            b.box((xa_, y_col, zc), (xb_, y_col + 1.4, zh0 + 0.2), rouge, name="Poutre")
        b.box((-19.8, y_col + 1.6, zc - 1.2), (19.8, y_col + 2.1, zc + 1.2), orr, name="Plate_bande")
        y_dg = y_col + 2.1
        b.box((-19.5, y_dg, zc - 0.6), (19.5, y_dg + 1.5, zc + 0.6), rouge_f, name="Fond_consoles")
        for k in range(14):
            _dougong(b, -19.5 + k * 3.0, y_dg, zc - 0.6, -1, h=1.5, larg=0.75, saillie=2.0)
        # lanternes rouges sous l'avant-toit, entre les colonnes
        for x in (-14.4, -7.2, 7.2, 14.4):
            _lanterne(b, x, y_col, zc - 0.2, r=0.9, h=1.8)

    y_t1 = y_col + 3.6 if v != 2 else y_col + 3.0           # avant-toit bas
    with b.group("Toit_bas"):
        r1 = _toit(b, -21.5, 21.5, zc - 3.4, zh1 + 2.4, y_t1, a=5.0, ax=4.4, h1=2.4 if v != 2 else 2.0, h2=0, ep=0.9,
                   releve=2.0, l_releve=4.6, **toit_kw)
    # étage : tambour blanc à poteaux rouges, consoles, plaque 武
    if v == 2:
        xu, zu0, zu1, hu = 11.0, zh0 - 1.5, zh1 - 3.0, 8.6
    else:
        xu, zu0, zu1, hu = 13.5, zh0 - 2.0, zh1 - 2.6, 6.0
    yu = r1["ya"]
    with b.group("Etage"):
        b.box((-xu, yu, zu0), (xu, yu + hu, zu1), vary("enduit", rng, 0.015), name="Tambour")
        for x in (-xu, xu):
            for z in (zu0, zu1):
                b.box((x - 0.5, yu, z - 0.5), (x + 0.5, yu + hu, z + 0.5), rouge, name="Poteau")
        b.box((-xu - 0.3, yu + hu - 1.6, zu0 - 0.3), (xu + 0.3, yu + hu, zu1 + 0.3), rouge, name="Bandeau")
        b.box((-xu - 0.4, yu + hu - 1.05, zu0 - 0.4), (xu + 0.4, yu + hu - 0.7, zu1 + 0.4), orr, collide=False, name="Filet")
        for sx in (-1, 1):
            _fenetre_treillis(b, sx * (xu * 0.55 + 2.0), yu + 0.9, 3.4, hu - 3.2, zu0, -1, cadre="laque_rouge",
                              barreaux="or", n=3)
        nd = int((2 * xu - 2) // 3.2)
        for k in range(nd + 1):
            x = -xu + 1 + k * (2 * xu - 2) / nd
            if abs(x) < 3.6:
                continue
            _dougong(b, x, yu + hu - 1.6, zu0 - 0.3, -1, h=1.6, larg=0.7, saillie=1.8)
        hp = min(5.6, hu - 1.1)
        _plaque(b, 0, yu + hu - 0.4 - hp, 4.6, hp, zu0 - 0.3, -1, "武", fond="encre", encre="or", cadre="or",
                vertical=True, marge=0.4)
    with b.group("Toit_haut"):
        H_MAX = 38.0
        y_t2 = yu + hu
        ep2, h12, orn2 = 0.9, 1.5, 2.0
        zt0, zt1 = zu0 - 3.6, zu1 + 3.4
        h22 = H_MAX - y_t2 - ep2 - h12 - 0.5 - max(orn2, EPI_H)
        r2 = _toit(b, -xu - 4.5, xu + 4.5, zt0, zt1, y_t2, a=3.4, ax=3.6, h1=h12, h2=h22, ep=ep2, releve=2.1,
                   l_releve=4.6, h_orn=orn2, epi=True, **toit_kw)
    # tours d'angle (pavillons) de part et d'autre de la façade
    with b.group("Tours"):
        for sx in (-1, 1):
            _tour(b, sx * (W - 4.2), zh0 - 1.2, 5.2, 6.0, yp, 16.0, toit_kw, rng=rng, fenetres_x=sx)
    with b.group("Braseros"):
        for sx in (-1, 1):
            _brasero(b, sx * 15.5, zf + 2.0)
    top = max(r2["top"], 38.0)
    return {"emprise": (largeur, profondeur), "hauteur": round(min(top, 38.0), 2)}


# ---------------------------------------------------------------------------
# 4) Tribune de spectateurs
# ---------------------------------------------------------------------------

AUVENTS = [("bande_rouge", "blanc"), ("bande_bleue", "blanc"), ("bande_orange", "bande_jaune"),
           ("bande_rouge", "bande_jaune")]


def tribune(b, variant=0, longueur=28, rangs=5) -> dict:
    """Gradins de spectateurs face à l'arène (avant vers -Z) : marches de pierre de 2 de profondeur et 1,2 de
    haut à studs, bancs rouges / blancs / bleus, escaliers latéraux, mur de fond et auvent rayé sur poteaux
    rouges, mâts à fanion aux deux bouts. Emprise longueur × (2·rangs + 4)."""
    v = variant % 4
    ca, cb = (c(n) for n in AUVENTS[v])
    L = longueur / 2
    D = rangs + 2.0                        # demi-profondeur : (2·rangs + 4) / 2
    z0 = -D + 2.0                          # devant des gradins (allée de 2 devant)
    hr = 1.2
    xg = L - 1.6                           # les gradins s'arrêtent avant les escaliers latéraux
    rouge = c("laque_rouge")
    bancs = ("banniere_rouge", "banniere_blanche", "banniere_bleue")
    with b.group("Gradins"):
        b.box((-L, 0, -D), (L, 0.3, D), c("pierre_fonce"), studs="top", name="Dalle")
        b.box((-xg, 0.3, -D), (xg, 1.2, -D + 0.6), rouge, name="Parapet")
        b.box((-xg - 0.1, 1.2, -D - 0.1), (xg + 0.1, 1.5, -D + 0.7), c("or"), studs="top", name="Chaperon")
        for i in range(rangs):
            za_ = z0 + 2 * i
            top = hr * (i + 1)
            b.box((-xg, 0.3, za_), (xg, top, za_ + 2.0), c("pierre_claire") if i % 2 == 0 else c("pierre"),
                  studs="top", name="Gradin")
            b.box((-xg + 0.3, top, za_ + 0.9), (xg - 0.3, top + 0.45, za_ + 1.8), c(bancs[i % 3]), studs="top",
                  name="Banc")
        zb_ = z0 + 2 * rangs                 # fond des gradins
        y_dos = 10.4
        b.box((-L, 0.3, zb_), (L, y_dos, D), vary("enduit", b.rng, 0.02), name="Mur_fond")
        b.box((-L - 0.1, y_dos - 1.4, zb_ - 0.1), (L + 0.1, y_dos - 0.8, D + 0.1), rouge, collide=False, name="Bandeau")
    with b.group("Escaliers"):
        for sx in (-1, 1):
            xa_, xb_ = sorted((sx * xg, sx * L))
            n = 2 * rangs
            for j in range(n):
                za_ = z0 - 1.0 + j * (zb_ - z0 + 1.0) / n
                b.box((xa_, 0.3, za_), (xb_, 0.3 + (hr * rangs - 0.3) * (j + 1) / n, za_ + (zb_ - z0 + 1.0) / n),
                      c("pierre_fonce"), studs="top", name="Marche")
            xr = sx * (L - 0.25)
            _barre(b, (xr, 1.6, z0 - 1.0), (xr, hr * rangs + 1.4, zb_), 0.3, 0.3, rouge, collide=False, name="Rampe")
            b.box((xr - 0.2, 0.3, z0 - 1.2), (xr + 0.2, 1.8, z0 - 0.8), rouge, collide=False, name="Pilastre")
    with b.group("Auvent"):
        y_ar, y_av = y_dos + 0.6, y_dos - 1.8           # bord arrière posé sur le mur, bord avant plus bas
        z_ar, z_av = D - 0.1, z0 + 0.2
        pente = (y_ar - y_av) / (z_ar - z_av)
        zp = z0 + 0.9                                   # poteaux sur le premier gradin
        for x in (-xg + 0.6, -xg / 3, xg / 3, xg - 0.6):
            b.box((x - 0.3, hr, zp - 0.3), (x + 0.3, y_av + (zp - z_av) * pente - 0.3, zp + 0.3), rouge, name="Poteau")
        nb = int(round(2 * L / 2.0))
        lb = 2 * L / nb
        for k in range(nb):
            x = -L + (k + 0.5) * lb
            _barre(b, (x, y_ar, z_ar), (x, y_av, z_av), 0.3, lb + (0.06 if k % 2 else 0.0),
                   ca if k % 2 == 0 else cb, collide=False, name="Toile")
            b.wedge_under((x - lb / 2 + 0.05, y_av - 1.0, z_av - 0.25), (x + lb / 2 - 0.05, y_av - 0.1, z_av - 0.1),
                          ca if k % 2 == 1 else cb, down="-x", collide=False, shadow=False, name="Lambrequin")
        b.box((-L - 0.1, y_ar - 0.3, D - 0.8), (L + 0.1, y_ar + 0.35, D), c("or"), collide=False, name="Faitiere")
    with b.group("Mats"):
        for sx in (-1, 1):
            x, z = sx * (L - 0.6), -D + 0.35
            b.box((x - 0.35, 0.3, z - 0.35), (x + 0.35, 1.0, z + 0.35), c("pierre_fonce"), name="Pied")
            b.cyl((x, 1.0 + (11.3 - 1.0) / 2, z), 0.18, 11.3 - 1.0, c("laque_rouge_fonce"), collide=False, name="Mat")
            b.cyl((x, 11.65, z), 0.3, 0.7, c("or"), collide=False, name="Pointe")
            xa_, xb_ = sorted((x - sx * 0.15, x - sx * 2.8))
            b.wedge_under((xa_, 9.7, z - 0.05), (xb_, 11.2, z + 0.05), ca, down="-x" if sx > 0 else "+x",
                          collide=False, shadow=False, name="Fanion")
    return {"emprise": (longueur, 2 * D), "hauteur": 12.0}


# ---------------------------------------------------------------------------
# 5) Dojo (salle d'entraînement)
# ---------------------------------------------------------------------------

STYLES_DOJO = [
    dict(tuile="tuile_orange", faitage="or", ornement="or", rive=None),
    dict(tuile="tuile_verte", faitage="tuile_orange", ornement="tuile_orange", rive=None),
    dict(tuile="tuile_orange_fonce", faitage="laque_rouge", ornement="or", rive="laque_rouge"),
    dict(tuile="tuile_orange", faitage="laque_rouge", ornement="or", rive=None),
]


def dojo(b, variant=0, largeur=24, profondeur=18) -> dict:
    """Petite salle d'entraînement : socle de pierre, plancher de bois surélevé à véranda, poteaux rouge-brun,
    murs blancs à colombages et fenêtres à treillis, portes coulissantes, planche 道場 au-dessus de la porte,
    toit à deux pans de tuiles (faîtage, coins relevés), lanternes, brûle-parfums devant les marches."""
    rng = b.rng
    v = variant % 4
    st = STYLES_DOJO[v]
    W, D = largeur / 2, profondeur / 2
    brun = mix(c("laque_rouge_fonce"), c("bois"), 0.45)          # bois rouge-brun
    brun_f = shade(brun, 0.75)
    y_pl = 2.0                       # dessus du plancher
    zv = -D + 3.0                    # bord de la véranda
    zw0, zw1 = zv + 3.2, D - 1.2     # murs
    xw = W - 2.6
    with b.group("Socle"):
        b.box((-W + 0.6, 0, zv - 0.5), (W - 0.6, 1.4, D - 0.4), c("pierre"), studs="top", name="Socle")
        b.box((-W + 1.0, 1.4, zv), (W - 1.0, y_pl, D - 0.8), c("bois_clair"), studs="top", name="Plancher")
        for j, (za_, top) in enumerate(((-D, 0.67), (-D + 0.85, 1.33), (-D + 1.7, y_pl))):
            b.box((-3.4, 0, za_), (3.4, top, zv), c("pierre_claire") if j < 2 else c("bois_clair"), studs="top",
                  name="Marche")
    with b.group("Salle"):
        H = 10.0
        b.box((-xw, y_pl, zw0), (xw, H, zw1), vary("enduit", rng, 0.015), name="Murs")
        b.box((-xw - 0.15, y_pl, zw0 - 0.15), (xw + 0.15, y_pl + 0.6, zw1 + 0.15), brun_f, name="Sabliere")
        b.box((-xw - 0.2, H - 0.8, zw0 - 0.2), (xw + 0.2, H, zw1 + 0.2), brun, name="Poutre")
        for x in (-xw, xw, -3.2, 3.2):
            zs = (zw0,) if abs(x) < xw else (zw0, zw1)
            for z in zs:
                b.box((x - 0.4, y_pl, z - 0.4), (x + 0.4, H - 0.8, z + 0.4), brun, name="Poteau")
        # portes coulissantes à treillis
        b.box((-2.8, y_pl + 0.6, zw0 - 0.3), (2.8, 7.4, zw0 + 0.1), c("enduit_creme"), collide=False, name="Porte")
        for x in (-1.9, -0.05, 1.9):
            b.box((x - 0.14, y_pl + 0.6, zw0 - 0.45), (x + 0.14, 7.4, zw0 - 0.25), brun_f, collide=False, name="Montant")
        for y in (4.4, 6.0):
            b.box((-2.8, y - 0.12, zw0 - 0.45), (2.8, y + 0.12, zw0 - 0.25), brun_f, collide=False, name="Traverse")
        b.box((-3.0, 7.4, zw0 - 0.4), (3.0, 7.75, zw0 + 0.1), brun_f, collide=False, name="Linteau")
        _plaque(b, 0, 7.95, 5.6, 1.7, zw0 - 0.1, -1, "道場", fond="bois_fonce", encre="or", cadre="or", marge=0.3)
        for sx in (-1, 1):
            _fenetre_treillis(b, sx * 6.4, 4.0, 3.6, 3.4, zw0, -1, cadre=brun, fond="enduit_creme", barreaux=brun_f, n=3)
            with b.at((sx * xw, 0, (zw0 + zw1) / 2), yaw=-90 * sx):
                _fenetre_treillis(b, 0, 4.0, 4.0, 3.4, 0.0, -1, cadre=brun, fond="enduit_creme", barreaux=brun_f, n=3)
    with b.group("Veranda"):
        for x in (-W + 1.6, -3.2, 3.2, W - 1.6):
            b.box((x - 0.5, 1.4, zv + 0.1), (x + 0.5, y_pl, zv + 1.1), c("pierre_claire"), name="Base")
            b.box((x - 0.4, y_pl, zv + 0.2), (x + 0.4, H, zv + 1.0), brun, name="Poteau")
        b.box((-W + 1.2, H - 0.8, zv + 0.1), (W - 1.2, H, zv + 1.1), brun, name="Poutre")
        for sx in (-1, 1):
            xa_, xb_ = sorted((sx * 3.6, sx * (W - 2.0)))
            b.box((xa_, y_pl + 1.6, zv + 0.45), (xb_, y_pl + 1.9, zv + 0.75), c("laque_rouge"), collide=False, name="Garde_corps")
            b.box((xa_, y_pl + 0.7, zv + 0.5), (xb_, y_pl + 0.9, zv + 0.7), c("laque_rouge"), collide=False, name="Lisse")
            _lanterne(b, sx * 7.2, H - 0.8, zv + 0.6, r=0.75, h=1.5)
    with b.group("Toit"):
        h_max = 16.0
        _toit(b, -W + 0.5, W - 0.5, zv - 0.6, D - 0.1, H, a=2.6, h1=0.9, h2=h_max - H - 0.6 - 0.9 - 0.5 - 1.0,
              ep=0.6, hanches=(False, False), cornes=(True, True), releve=1.5, l_releve=3.4, h_orn=1.0,
              dessous=st["rive"] or "laque_rouge_fonce", fonce=st["rive"], tuile=st["tuile"], faitage=st["faitage"],
              ornement=st["ornement"], rng=rng, pignon_bouts=True)
    with b.group("Brule_parfums"):
        for sx in (-1, 1):
            x, z = sx * 6.6, -D + 1.3
            b.box((x - 0.9, 0, z - 0.9), (x + 0.9, 0.5, z + 0.9), c("pierre_fonce"), studs="top", name="Socle")
            b.cyl((x, 1.3, z), 0.9, 1.6, c("bronze"), name="Cuve")
            b.cyl((x, 2.15, z), 1.05, 0.25, shade(c("bronze"), 0.8), collide=False, name="Levre")
            for dx in (-0.55, 0.55):
                b.box((x + dx - 0.12, 2.2, z - 0.12), (x + dx + 0.12, 2.9, z + 0.12), c("bronze"), collide=False, name="Anse")
            b.box((x - 0.1, 2.25, z - 0.1), (x + 0.1, 3.6, z + 0.1), c("blanc"), collide=False, shadow=False, name="Fumee")
    return {"emprise": (largeur, profondeur), "hauteur": 16.0}


# ---------------------------------------------------------------------------
# 6) Pagode
# ---------------------------------------------------------------------------

STYLES_PAGODE = [
    dict(tuile="tuile_orange", faitage="or", ornement="or"),
    dict(tuile="tuile_verte", faitage="tuile_orange", ornement="or"),
    dict(tuile="tuile_orange_fonce", faitage="or", ornement="or"),
    dict(tuile="tuile_orange_claire", faitage="or", ornement="or"),
]


def pagode(b, variant=0, etages=3) -> dict:
    """Pagode chinoise : socle de pierre 10 × 10 à studs, étages carrés qui rétrécissent (poteaux rouges, murs
    blancs, porte puis fenêtres rondes), avant-toits de tuiles à coins relevés, toit en pavillon et flèche
    dorée de disques empilés (jamais une boule). ≈ 8 de haut par étage + la flèche."""
    rng = b.rng
    st = STYLES_PAGODE[variant % 4]
    toit_kw = dict(tuile=st["tuile"], faitage=st["faitage"], ornement=st["ornement"], rng=rng)
    rouge = c("laque_rouge")
    with b.group("Socle"):
        b.box((-5, 0, -5), (5, 1.2, 5), c("pierre_fonce"), studs="top", name="Socle")
        b.box((-4.3, 1.2, -4.3), (4.3, 1.8, 4.3), c("pierre"), studs="top", name="Socle")
        b.box((-1.6, 0, -5.9), (1.6, 0.8, -5), c("pierre_claire"), studs="top", name="Marche")
    y = 1.8
    w = 3.4
    for k in range(etages):
        h = 4.6 - 0.5 * k
        with b.group(f"Etage{k + 1}"):
            b.box((-w, y, -w), (w, y + h, w), vary("enduit", rng, 0.02), name="Mur")
            for sx in (-1, 1):
                for sz in (-1, 1):
                    xa_, xb_ = sorted((sx * (w - 0.45), sx * (w + 0.15)))
                    za_, zb_ = sorted((sz * (w - 0.45), sz * (w + 0.15)))
                    b.box((xa_, y, za_), (xb_, y + h, zb_), rouge, name="Poteau")
            b.box((-w - 0.2, y + h - 0.7, -w - 0.2), (w + 0.2, y + h, w + 0.2), rouge, name="Bandeau")
            if k == 0:
                b.box((-1.1, y, -w - 0.3), (1.1, y + 3.0, -w + 0.1), c("laque_rouge_fonce"), collide=False, name="Porte")
                b.box((-1.3, y + 3.0, -w - 0.35), (1.3, y + 3.35, -w + 0.1), c("or"), collide=False, name="Linteau")
            else:
                _fenetre_ronde(b, 0, y + h * 0.45, 0.9, -w, -1, cadre="laque_rouge", barreaux="or")
            for yaw in (90, 180, -90):
                with b.at((0, 0, 0), yaw=yaw):
                    _fenetre_ronde(b, 0, y + h * 0.45, 0.8 if k == 0 else 0.7, -w, -1, cadre="laque_rouge", barreaux="or")
            debord = 2.0 - 0.15 * k
            if k < etages - 1:
                r = _toit(b, -w - debord, w + debord, -w - debord, w + debord, y + h, a=debord + 0.2, ax=debord + 0.2,
                          h1=1.1, h2=0, ep=0.5, releve=1.3, l_releve=2.6, aretiers=False, rive=False, **toit_kw)
                y = r["ya"]
                w = w - 0.6
            else:
                r = _toit(b, -w - debord, w + debord, -w - debord, w + debord, y + h, a=debord + 0.4, ax=debord + 0.4,
                          h1=1.4, h2=0, ep=0.5, releve=1.4, l_releve=2.8, aretiers=False, rive=False, **toit_kw)
                r2 = _toit(b, -w + 0.6, w - 0.6, -w + 0.6, w - 0.6, r["ya"], a=1.2, ax=1.2, h1=1.0, h2=0, ep=0,
                           cornes=(False, False), aretiers=False, rive=False, **toit_kw)
                y = r2["ya"]
    with b.group("Fleche"):
        orr, orf = c("or"), c("or_fonce")
        b.cyl((0, y + 0.3, 0), 1.0, 0.6, orf, name="Base")
        yy = y + 0.6
        n = 5 if etages >= 3 else 3
        for i in range(n):
            r_ = 0.75 - i * 0.08
            b.cyl((0, yy + 0.25, 0), r_, 0.5, orr if i % 2 == 0 else orf, collide=False, name="Anneau")
            yy += 0.6
            if i < n - 1:
                b.cyl((0, yy - 0.05, 0), 0.25, 0.1 + 0.0, orf, collide=False, name="Tige")
        b.cyl((0, yy + 0.6, 0), 0.18, 1.2, orr, collide=False, name="Pointe")
        top = yy + 1.2
    return {"emprise": (10, 11.8), "hauteur": round(top, 2)}
