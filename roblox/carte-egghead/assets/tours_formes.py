"""Tours « de formes » de la couronne (rang 2) et front de rue non rond (rang 1).

Dix fonctions (SPECS.md, fiche « assets/tours_formes.py » ; recettes STYLE.md T04, T05, T06, T12, T14, T15, T17,
K01, K02, K03, K04, K07, M11, M12, M14, M15, M17, C02), toutes de la forme `f(b, variant=0, **params) -> dict` :

    tour_manette(b, variant=0, hauteur=195, diametre=48, largeur_manette=72)    # T04 enseigne-manette
    cone_etoile(b, variant=0, hauteur=130, diametre=40)                         # T15 cône rayé à étoile d'or
    tour_damier(b, variant=0, hauteur=170, diametre=44)                         # T06 bouteille à damier
    tour_bourrelets(b, variant=0, hauteur=160, diametre=44, quai=None)          # T05 bourrelets / disques
    tour_bureaux(b, variant=0, hauteur=180, largeur=34, quai=None)              # T12 tour à gradins
    plateau_disques(b, variant=0, hauteur=75, diametre=56)                      # T14 station de nacelles
    tour_anneau(b, variant=0, hauteur=125, diametre=40, quai=None)              # T17 tour blanche à anneau
    boutique_arche(b, variant=0, largeur=30, profondeur=16, hauteur=28)         # K01 boutique à arche
    kiosque(b, variant=0, type="dome", largeur=26, profondeur=26, hauteur=24)   # K04 / K02 / K03 / K07
    connecteur(b, variant=0, largeur=8, profondeur=12, hauteur=16, couleur="lavande", accent="turquoise")

Conventions : origine au centre de l'emprise au sol (y = 0), avant vers -Z local. Tours : `diametre` = Ø maximal
au sol et jusqu'à y = 40 (seuls les bords, anneaux et la manette le dépassent plus haut), `hauteur` = sommet de la
coiffe (antenne : + 10 au plus) ; retour avec "ame" (rayon du fût plein, pour les tubes de verre). Quais : fût nu
sur ± 6 (± 9 pour un tube géant) et deux bagues R(âme + 0,8) à ± 4,5 (± 7,6). Front de rue : chaque fonction
remplit exactement largeur × profondeur, l'avant sur la ligne des façades (z = -profondeur/2), rien devant sous
y = 8 (au-dessus : enseignes plates de saillie ≤ 1,5). Studs sur les dessus plats seulement. Aucun texte ni logo.
"""

from __future__ import annotations

import math

import numpy as np

import plan
from kit import bornes, mix, repere_direction, rot_x, rot_y, rot_z, shade
from palette import c, schema

# --------------------------------------------------------------------------------------------------------------
# Outils communs
# --------------------------------------------------------------------------------------------------------------

HUBLOT = c("hublot")             # verre opaque des hublots et des bandes vitrées
NUIT = c("bleu_nuit")            # panneaux de porte, fonds de niche
BLANC = c("blanc_labo")
TUYAU = mix(c("indigo"), c("dalle_labo"), 0.4)
HAIE = (c("haie_claire"), c("haie"))
CLAIRS = ("blanc_labo", "creme", "dalle_labo", "jaune_citron", "lavande")


def _u(theta: float) -> np.ndarray:
    """Direction horizontale à l'azimut `theta` (degrés) : 0 = avant (-Z), 90 = +X, 180 = arrière (+Z)."""
    t = math.radians(theta)
    return np.array([math.sin(t), 0.0, -math.cos(t)])


def _t(theta: float) -> np.ndarray:
    """Tangente horizontale au cercle à l'azimut theta."""
    t = math.radians(theta)
    return np.array([math.cos(t), 0.0, math.sin(t)])


def _repere_mur(theta: float) -> np.ndarray:
    """Rotation d'un bloc posé sur un mur rond à l'azimut theta : X tangent, Y vertical, Z vers l'intérieur."""
    x = _t(theta)
    y = np.array([0.0, 1.0, 0.0])
    return np.column_stack([x, y, np.cross(x, y)])


def _repere_surface(n, t) -> np.ndarray:
    """Rotation : Z local = normale n (vers l'extérieur), X local au plus près de t."""
    z = np.asarray(n, float) / np.linalg.norm(n)
    x = np.asarray(t, float) - (np.asarray(t, float) @ z) * z
    x = x / np.linalg.norm(x)
    return np.column_stack([x, np.cross(z, x), z])


def _cyl_axe(b, centre, axe, longueur, rayon, couleur, **kw):
    """Cylindre d'axe quelconque, centré en `centre`. 1 pièce."""
    return b.part("cyl", (longueur, 2 * rayon, 2 * rayon), centre, repere_direction(axe), couleur, **kw)


def _rentre(R: float, s: float) -> float:
    """Flèche d'un mur courbe de rayon R à la distance latérale s (0 pour un mur plat)."""
    return R - math.sqrt(max(R * R - s * s, 0.0)) if R else 0.0


def _hublot(b, p, n, f, rho, cadre, verre=HUBLOT, *, allume=False, bord=None):
    """Hublot rond sur une surface (point p, normale n, rayon de courbure rho, 0 = plat) : cadre d'épaisseur
    0,4 + f²/(2 rho), face avant à +0,3 ; vitre (opaque, ou Neon si `allume`) de rayon f - bord, face avant à +0,4.
    2 pièces, sans collision."""
    n = np.asarray(n, float)
    n = n / np.linalg.norm(n)
    p = np.asarray(p, float)
    ep = 0.4 + (f * f / (2 * rho) if rho else 0.1)
    _cyl_axe(b, p + n * (0.3 - ep / 2), n, ep, f, cadre, collide=False, name="Cadre")
    rv = max(0.5, f - (bord if bord is not None else max(0.6, 0.28 * f)))
    _cyl_axe(b, p + n * 0.25, n, 0.3, rv, verre, material="Neon" if allume else "SmoothPlastic",
             collide=False, shadow=not allume, name="Hublot")


def _hublot_mur(b, R, theta, y, f, cadre, verre=HUBLOT, **kw):
    u = _u(theta)
    _hublot(b, u * R + np.array([0.0, y, 0.0]), u, f, R, cadre, verre, **kw)


def _sur_ellipsoide(C, a, h, theta, s):
    """Point et normale d'un ellipsoïde de révolution (centre C, rayon a, demi-hauteur h) à l'azimut theta et à la
    hauteur relative s (y - yC = s h)."""
    r = a * math.sqrt(max(0.0, 1.0 - s * s))
    u = _u(theta)
    p = np.asarray(C, float) + u * r + np.array([0.0, h * s, 0.0])
    n = u * (r / (a * a)) + np.array([0.0, s / h, 0.0])
    return p, n / np.linalg.norm(n)


def _hublot_ellipsoide(b, C, a, h, theta, s, f, cadre, verre=HUBLOT, **kw):
    p, n = _sur_ellipsoide(C, a, h, theta, s)
    rho = min(a, h) ** 2 / max(a, h)
    _hublot(b, p, n, f, rho, cadre, verre, **kw)


def _bloc_mur(b, R, theta, y, larg, haut, saillie, couleur, **kw):
    """Petit bloc posé sur un mur rond (fente, poteau, meneau) : face avant à R + saillie, dos enfoncé."""
    ep = saillie + 0.25 + _rentre(R, larg / 2)
    ctr = _u(theta) * (R + saillie - ep / 2) + np.array([0.0, y, 0.0])
    return b.part("block", (larg, haut, ep), ctr, _repere_mur(theta), couleur, **kw)


def _pilule_mur(b, R, theta, y, long_, haut, saillie, couleur, **kw):
    """Pilule (ellipsoïde) tangente à un mur rond : grand axe horizontal, face avant à R + saillie."""
    prof = 2 * saillie + 0.6
    ctr = _u(theta) * (R + saillie - prof / 2) + np.array([0.0, y, 0.0])
    return b.part("ellipsoid", (long_, haut, prof), ctr, _repere_mur(theta), couleur, **kw)


def _porte(b, origine, u, R, y0, panneau, cadre, *, largeur=5.0, haut=6.0, chevrons=None):
    """Porte en arche (STYLE § 3.0) : panneau largeur × haut + arche R largeur/2, cadre 0,8 plus large, 0,2 en
    retrait. `origine` = axe de la tour (R = rayon du mur) ou point du mur plat (R = 0) ; `u` = normale sortante.
    `chevrons` : couleur d'une paire « < > » sur le panneau (+4 pièces). 4 pièces (8 avec chevrons)."""
    u = np.asarray(u, float)
    o = np.asarray(origine, float)
    up = np.array([0.0, 1.0, 0.0])
    tg = np.cross(u, up)
    M = np.column_stack([tg, up, np.cross(tg, up)])
    rc, rp = largeur / 2 + 0.8, largeur / 2
    ec, ep = _rentre(R, rc), _rentre(R, rp)
    with b.group("Porte"):
        a0, a1 = R - ec - 0.2, R + 0.25
        hb = haut + 0.1
        b.part("block", (2 * rc, hb, a1 - a0), o + u * (a0 + a1) / 2 + up * (y0 - 0.2 + hb / 2), M, cadre,
               name="Cadre")
        a0, a1 = R - ec - 0.25, R + 0.2
        _cyl_axe(b, o + u * (a0 + a1) / 2 + up * (y0 + haut), u, a1 - a0, rc, cadre, name="Cadre")
        a0, a1 = R - ep - 0.1, R + 0.45
        b.part("block", (2 * rp, haut + 0.1, a1 - a0), o + u * (a0 + a1) / 2 + up * (y0 - 0.1 + (haut + 0.1) / 2), M,
               panneau, name="Porte")
        a0, a1 = R - ep - 0.15, R + 0.4
        _cyl_axe(b, o + u * (a0 + a1) / 2 + up * (y0 + haut), u, a1 - a0, rp, panneau, name="Porte")
        if chevrons is not None:
            yc = y0 + 0.55 * haut
            lg = 0.32 * largeur
            for sx in (-1, 1):
                for sy in (-1, 1):
                    ang = -35 * sx * sy
                    ctr = o + u * (R + 0.5) + tg * (sx * 0.2 * largeur) + up * (yc + sy * 0.28 * lg)
                    Rm = M @ rot_z(ang)
                    b.part("block", (lg, 0.35, 0.2), ctr, Rm, chevrons, collide=False, name="Chevron")


def _boite_y(b, x0, x1, y0, y1, z0, z1, r, couleur, studs="top", **kw):
    """Boîte aux arêtes verticales arrondies (vue de dessus : rectangle à coins de rayon r). 6 pièces.
    Dessus décalés de 0,05 (bloc A à y1, bloc B à y1 - 0,05, cylindres à y1 - 0,1), bas enfoncés d'autant."""
    out = [b.box((x0, y0, z0 + r), (x1, y1, z1 - r), couleur, studs=studs, **kw),
           b.box((x0 + r, y0 - 0.05, z0), (x1 - r, y1 - 0.05, z1), couleur, studs=studs, **kw)]
    for sx in (x0 + r, x1 - r):
        for sz in (z0 + r, z1 - r):
            out.append(b.cyl((sx, (y0 + y1) / 2 - 0.1, sz), r, y1 - y0, couleur, studs=studs, **kw))
    return out


def _boite_z(b, centre, lx, ly, lz, r, couleur, studs_dessus=False, **kw):
    """Boîte arrondie vue de face (coins ronds dans le plan XY, cylindres d'axe Z) : manette, gélule. 6 pièces.
    Faces avant décalées de 0,05 (A, B, cylindres)."""
    cx, cy, cz = centre
    out = [b.boxc((cx, cy, cz), (lx, ly - 2 * r, lz), couleur, **kw),
           b.boxc((cx, cy, cz), (lx - 2 * r, ly, lz - 0.1), couleur, studs="top" if studs_dessus else (), **kw)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(b.cyl((cx + sx * (lx / 2 - r), cy + sy * (ly / 2 - r), cz), r, lz - 0.2, couleur,
                             axis="z", **kw))
    return out


def _gelule(b, centre, lx, ly, lz, couleur, **kw):
    """Gélule plate face à -Z (bloc + 2 cylindres d'axe Z aux bouts). 3 pièces."""
    cx, cy, cz = centre
    r = ly / 2
    out = [b.boxc((cx, cy, cz), (lx - 2 * r, ly, lz), couleur, **kw)]
    for sx in (-1, 1):
        out.append(b.cyl((cx + sx * (lx / 2 - r), cy, cz + 0.02), r, lz - 0.04, couleur, axis="z", **kw))
    return out


def _etoile(b, centre, Ro, ep, couleur, R=None, **kw):
    """Étoile pleine à 5 branches dans le plan XY local (normale Z), pointe vers +Y : 10 coins (demi-branches en
    triangles rectangles) + un moyeu cylindrique. 11 pièces."""
    R = np.eye(3) if R is None else np.asarray(R, float)
    C = np.asarray(centre, float)
    Ri = Ro * 0.382
    c36, s36 = math.cos(math.radians(36)), math.sin(math.radians(36))
    a = Ro - Ri * c36
    cc = Ri * s36
    for k in range(5):
        phi = math.radians(90 + 72 * k)
        d = R @ np.array([math.cos(phi), math.sin(phi), 0.0])
        pl = R @ np.array([-math.sin(phi), math.cos(phi), 0.0])
        M = C + d * (Ri * c36)
        for sgn in (1, -1):
            p = pl * sgn
            Y, Z = d, -p
            rot = np.column_stack([np.cross(Y, Z), Y, Z])
            b.part("wedge", (ep, a, cc), M + d * a / 2 + p * cc / 2, rot, couleur, name="Branche", **kw)
    _cyl_axe(b, C, R @ np.array([0.0, 0.0, 1.0]), ep + 0.3, Ri, couleur, name="Moyeu", **kw)


def _picto(b, kind, centre, taille, couleur, ep=0.3, **kw):
    """Pictogramme M12 en relief dans le plan XY (face vers -Z), centré en `centre` (dos à z + ep/2) :
    « etoile » (11), « etoile_rayons » (6), « coeur » (3), « piece » (2), « eclair » (3), « nuage » (4)."""
    cx, cy, cz = centre
    s = float(taille)
    kw.setdefault("collide", False)
    if kind == "etoile":
        _etoile(b, (cx, cy, cz), 0.5 * s, ep, couleur, **kw)
    elif kind == "etoile_rayons":
        for k in range(5):
            ang = 72 * k
            Rm = rot_z(ang)
            ctr = np.array([cx, cy, cz]) + Rm @ np.array([0.0, 0.25 * s, 0.0])
            b.part("block", (0.16 * s, 0.5 * s, ep), ctr, Rm, couleur, name="Rayon", **kw)
        b.cyl((cx, cy, cz - 0.05), 0.14 * s, ep + 0.1, couleur, axis="z", name="Moyeu", **kw)
    elif kind == "coeur":
        r = 0.28 * s
        for sx in (-1, 1):
            b.cyl((cx + sx * 0.72 * r, cy + 0.3 * r, cz), r, ep, couleur, axis="z", name="Lobe", **kw)
        b.part("block", (1.95 * r, 1.95 * r, ep - 0.04), (cx, cy - 0.5 * r, cz), rot_z(45), couleur,
               name="Pointe", **kw)
    elif kind == "piece":
        b.cyl((cx, cy, cz), 0.5 * s, ep, c("or_fonce"), axis="z", name="Piece", **kw)
        b.cyl((cx, cy, cz - 0.08), 0.36 * s, ep, couleur, axis="z", name="Piece", **kw)
    elif kind == "eclair":
        pts = [(0.22, 0.5), (-0.14, 0.04), (0.16, 0.04), (-0.22, -0.5)]
        for i, (p0, p1) in enumerate(zip(pts[:-1], pts[1:])):
            a = np.array([cx + p0[0] * s, cy + p0[1] * s, cz - 0.02 * i])
            q = np.array([cx + p1[0] * s, cy + p1[1] * s, cz - 0.02 * i])
            d = q - a
            L = float(np.linalg.norm(d))
            ang = math.degrees(math.atan2(d[1], d[0]))
            b.part("block", (L + 0.12 * s, 0.15 * s, ep), (a + q) / 2, rot_z(ang), couleur, name="Eclair", **kw)
    elif kind == "nuage":
        for i, (dx, dy, rr) in enumerate(((-0.27, -0.06, 0.17), (0.02, 0.06, 0.25), (0.28, -0.07, 0.16))):
            b.cyl((cx + dx * s, cy + dy * s, cz - 0.03 * i), rr * s, ep, couleur, axis="z", name="Nuage", **kw)
        b.boxc((cx + 0.01 * s, cy - 0.15 * s, cz + 0.04), (0.56 * s, 0.16 * s, ep), couleur, name="Nuage", **kw)
    else:
        raise ValueError(kind)


def _rayon_tube(fonction, variant, hauteur, taille, y):
    """Rayon du tube de verre qui entre à la hauteur y (tour retrouvée dans plan.CEINTURE par ses paramètres)."""
    for e in plan.CEINTURE:
        if e["module"] != "tours_formes" or e["fonction"] != fonction or e["variante"] != variant:
            continue
        p = e["params"]
        if abs(p.get("hauteur", -1) - hauteur) > 1e-6:
            continue
        if abs(p.get("diametre", p.get("largeur", -1)) - taille) > 1e-6:
            continue
        for t in plan.TUBES:
            if e["id"] in (t["de"], t["vers"]) and abs(t["y"] - y) < 1e-6:
                return float(plan.TUBE_RAYON[t["type"]])
    return float(plan.TUBE_RAYON["fin"])


def _quais(quai, fonction, variant, hauteur, taille):
    """quai (None, nombre, liste ; (y, rayon_tube) accepté) → [(y, demi-bande nue, écart des bagues)]."""
    if quai is None:
        return []
    items = list(quai) if isinstance(quai, (list, tuple)) else [quai]
    out = []
    for it in items:
        if isinstance(it, dict):
            y, r = float(it["y"]), it.get("rayon")
        elif isinstance(it, (list, tuple)):
            y, r = float(it[0]), (it[1] if len(it) > 1 else None)
        else:
            y, r = float(it), None
        r = _rayon_tube(fonction, variant, hauteur, taille, y) if r is None else float(r)
        out.append((y, max(6.0, r + 3.0), max(4.5, r + 1.6)))
    return out


def _libre(y, demi_ep, quais, marge=0.0):
    """True si un élément centré en y (demi-épaisseur demi_ep) n'empiète sur aucune bande nue de quai."""
    return all(abs(y - q) >= d + demi_ep + marge for (q, d, _e) in quais)


def _bagues(b, quais, R_ame, couleur):
    with b.group("Quai"):
        for (y, _d, ecart) in quais:
            for sg in (-1, 1):
                b.cyl((0, y + sg * ecart, 0), R_ame + 0.8, 1.2, couleur, collide=False, name="Bague")


def _bilan(b, i0, emprise, H, ame=None, **extra):
    parts = b.parts[i0:]
    lo, hi = bornes(parts)
    y_sol = float(b.to_world((0, 0, 0))[1])
    out = {"emprise": emprise, "hauteur": H, "sommet": round(float(hi[1]) - y_sol, 2), "pieces": len(parts),
           "neon": sum(1 for p in parts if p.material == "Neon"),
           "transparentes": sum(1 for p in parts if 0 < p.transparency < 1)}
    if ame is not None:
        out["ame"] = round(float(ame), 2)
    out.update(extra)
    return out


def _haies(b, xs, y, z, taille=3.2):
    """Boules de haie posées sur un toit (enfoncées de 0,3), alternées clair / foncé, sans collision."""
    with b.group("Haie"):
        for i, x in enumerate(xs):
            h = 0.8 * taille
            b.ellipsoid((x, y + h / 2 - 0.3, z), (taille, h, taille * 0.9), HAIE[i % 2], collide=False,
                        name="Haie")


# --------------------------------------------------------------------------------------------------------------
# T04 · Tour à enseigne-manette (repère du milieu est)
# --------------------------------------------------------------------------------------------------------------

def tour_manette(b, variant=0, hauteur=195, diametre=48, largeur_manette=72, **_):
    """Tambour à colonnade et grands hublots cerclés, portant sur deux pieds une manette géante arrondie
    (croix, 4 boutons d'une seule couleur, panneau à 2 fentes Neon, évents). Variantes : 0 console, 1 menthe,
    2 cerise. ≤ 160 pièces, ≤ 8 Neon."""
    s = schema("tour_manette", variant)
    H, D, Lm = float(hauteur), float(diametre), float(largeur_manette)
    i0 = len(b.parts)
    tam, cad, col, man, fac, bou = s["tambour"], s["cadres"], s["colonnade"], s["manette"], s["facade"], s["boutons"]
    R = D / 2 - 0.6                      # tambour (bagues et poteaux restent dans Ø D sous y 40)
    yc1 = 0.14 * H                       # haut de la colonnade
    yc0 = yc1 - max(6.5, 0.04 * H)
    yt1 = 0.72 * H                       # haut du tambour
    hm, lzm = 0.45 * Lm, 12.0            # manette : largeur_manette × 0,45 L × 12
    ycm = 0.87 * H
    ybm, ytm = ycm - hm / 2, ycm + hm / 2
    zf = -lzm / 2                        # face avant du corps de la manette
    with b.group("Socle"):
        b.cyl((0, 0.6, 0), D / 2, 1.2, col, studs="top", name="Plinthe")
        Rs = R - 0.5                      # le tambour du pied, un peu plus mince : la porte reste dans Ø D
        b.cyl((0, (1.2 + yc0) / 2 + 0.05, 0), Rs, yc0 - 1.1, tam, name="Socle")
        _porte(b, (0, 0, 0), _u(0), Rs, 1.2, NUIT, cad, largeur=8.0, haut=8.0, chevrons=col)
        for a in (-24, 24):
            _hublot_mur(b, Rs, a, 1.2 + 6.5, 2.4, cad)
    with b.group("Colonnade"):
        b.cyl((0, yc0 + 0.6, 0), D / 2, 1.2, cad, name="Bague")
        b.cyl((0, (yc0 + yc1) / 2, 0), R - 0.5, yc1 - yc0 - 2.0, col, name="Coeur")
        b.cyl((0, yc1 - 0.6, 0), D / 2, 1.2, cad, name="Bague")
        hp = yc1 - yc0 - 2.4
        for k in range(16):
            _bloc_mur(b, R - 0.5, 360 * k / 16 + 11.25, (yc0 + yc1) / 2, 1.5, hp + 0.1, 0.8, cad, name="Poteau")
    with b.group("Tambour"):
        b.cyl((0, (yc1 + yt1) / 2, 0), R, yt1 - yc1, tam, name="Tambour")
        dy = (yt1 - yc1) / 3
        f = min(5.6, 0.11 * D)
        azs = (-64, -32, 0, 32, 64)
        for a in azs:   # montants dorés qui relient les hublots (comme EH5)
            _bloc_mur(b, R, a, (yc1 + yt1) / 2, 0.9, yt1 - yc1 - 0.2, 0.15, cad, collide=False, name="Filet")
        for k in range(3):
            yk = yc1 + (k + 0.5) * dy
            b.cyl((0, yk, 0), R + 0.15, 2.0, cad, collide=False, name="Bande")
            for a in azs:
                _hublot_mur(b, R + 0.15, a, yk, f, cad)
        for k in (1, 2):
            b.cyl((0, yc1 + k * dy, 0), R + 0.4, 1.6, col, collide=False, name="Lisere")
        b.cyl((0, yt1 + 1.1, 0), D / 2 + 0.8, 2.2, cad, studs="top", name="Rebord")
    yr = yt1 + 2.2
    xf = 0.22 * Lm
    with b.group("Pieds"):
        for sx in (-1, 1):
            b.cyl((sx * xf, yr + 0.6, 0), 4.0, 1.2, cad, studs="top", name="Semelle")
            b.cyl((sx * xf, (yr + 1.2 + ybm + 0.4) / 2, 0), 2.7, ybm + 0.4 - yr - 1.2, col, name="Pied")
            b.cyl((sx * xf, ybm - 1.0, 0), 3.4, 2.0, cad, name="Cheville")
    with b.group("Manette"):
        rr = 0.27 * hm
        _boite_z(b, (0, ycm, 0), Lm, hm, lzm, rr, man, studs_dessus=True)
        _boite_z(b, (0, ycm, zf - 0.2), Lm - 4, hm - 4, 0.4, rr - 2, fac, collide=False)
        zp = zf - 0.4                     # face avant de la façade claire
        sock = shade(man, 0.78)
        xd, yd = 0.27 * Lm, ycm - 0.02 * hm
        b.cyl((xd, yd, zp - 0.15), 0.118 * Lm, 0.3, sock, axis="z", collide=False, name="Socle_croix")
        bw, bl = 0.068 * Lm, 0.2 * Lm
        b.boxc((xd, yd, zp - 0.3 - 0.3), (bw, bl, 0.6), bou, collide=False, name="Croix")
        b.boxc((xd, yd, zp - 0.3 - 0.325), (bl, bw, 0.75), bou, collide=False, name="Croix")
        xb = -0.27 * Lm
        b.cyl((xb, yd, zp - 0.15), 0.118 * Lm, 0.3, sock, axis="z", collide=False, name="Socle_boutons")
        e = 0.072 * Lm
        for (dx, dy_) in ((e, 0), (-e, 0), (0, e), (0, -e)):
            b.cyl((xb + dx, yd + dy_, zp - 0.3 - 0.4 + 0.05), 0.034 * Lm, 0.8, bou, axis="z", collide=False,
                  name="Bouton")
        yp = ycm - 0.14 * hm
        b.boxc((0, yp, zp - 0.15), (0.2 * Lm, 0.17 * hm, 0.3), NUIT, collide=False, name="Panneau")
        for sx in (-1, 1):
            b.boxc((sx * 0.045 * Lm, yp, zp - 0.3 - 0.1), (0.055 * Lm, 0.055 * hm, 0.2), s["neon"],
                   material="Neon", collide=False, shadow=False, name="Fente")
        yv = ytm - 2 - 0.12 * hm
        for k in range(6):
            b.boxc(((k - 2.5) * 0.028 * Lm, yv, zp - 0.1), (0.012 * Lm, 0.1 * hm, 0.2), shade(man, 0.6),
                   collide=False, name="Event")
    with b.group("Antenne"):
        xa = -0.3 * Lm
        b.cyl((xa, (ytm - 0.3 + H - 2.6) / 2, 0), 0.8, H - 2.6 - ytm + 0.3, col, collide=False, name="Mat")
        b.cyl((xa, H - 5.0, 0), 3.0, 0.5, cad, collide=False, name="Disque")
        b.ball((xa, H - 1.6, 0), 1.6, c("rouge"), collide=False, name="Boule")
    return _bilan(b, i0, (D, D), H, R, largeur_manette=Lm)


# --------------------------------------------------------------------------------------------------------------
# T15 · Cône rayé à étoile d'or
# --------------------------------------------------------------------------------------------------------------

def cone_etoile(b, variant=0, hauteur=130, diametre=40, **_):
    """Socle foncé à porte, cône rayé de 14 rayures, anneau incliné de 8° bien détaché, tige et étoile pleine à
    5 branches face à la carte. Variantes : 0 rouge, 1 bleu nuit, 2 violet, 3 turquoise et blanc. ≤ 70 pièces."""
    s = schema("cone_etoile", variant)
    H, D = float(hauteur), float(diametre)
    i0 = len(b.parts)
    kx, ky = D / 22.0, H / 60.0
    R0 = D / 2
    hs = max(4 * ky, 10.0)
    with b.group("Socle"):
        b.cyl((0, hs / 2, 0), R0 - 0.6, hs, s["socle"], studs="top", name="Socle")
        _porte(b, (0, 0, 0), _u(0), R0 - 0.6, 0.0, NUIT, s["anneau"], largeur=5.0, haut=5.8)
    Rc0, Rc1 = R0 - 1.6, max(1.5 * kx, 1.4)
    hc = 44 * ky
    yct = hs + hc
    with b.group("Cone"):
        b.cone_etage((0, hs, 0), Rc0, Rc1, hc, list(s["cone"]), etages=14, profil="milieu", studs="top")
    Ra, ea, tilt = 15 * kx, max(1.6 * kx, 2.4), 8.0
    ya = max(0.33 * H, 40 + Ra * math.sin(math.radians(tilt)) + ea / 2 + 0.6)
    with b.group("Anneau"):
        b.anneau((0, ya, 0), Ra, ea, s["anneau"], 32, rot=rot_z(tilt), collide=False)
    Ro = 5.5 * kx
    yst = H - Ro
    with b.group("Etoile"):
        b.cyl((0, (yct - 0.5 + yst) / 2, 0), max(0.45 * kx, 0.6), yst - yct + 0.5, s["etoile"], collide=False,
              name="Tige")
        _etoile(b, (0, yst, 0), Ro, max(1.6, 1.0 * kx), s["etoile"], collide=False)
    r_mi = Rc0 + (Rc1 - Rc0) * 0.5
    return _bilan(b, i0, (D, D), H, r_mi)


# --------------------------------------------------------------------------------------------------------------
# T06 · Bouteille à damier
# --------------------------------------------------------------------------------------------------------------

def tour_damier(b, variant=0, hauteur=170, diametre=44, **_):
    """Socle à studs, corps à damier (plaques carrées tangentes à un dodécagone, une facette sur deux, rangs
    décalés de 30°), épaule bombée cannelée, col, disque, tête-soucoupe à filet et 6 feux Neon, antenne.
    Variantes : 0 citron-pomme, 1 fraise, 2 raisin, 3 lagon. ≤ 140 pièces, ≤ 8 Neon."""
    s = schema("tour_damier", variant)
    H, D = float(hauteur), float(diametre)
    i0 = len(b.parts)
    kx = D / 34.0
    ca, cb = s["damier"]
    Rb = 16 * kx
    ys = 2.4
    yb1 = 0.62 * H
    with b.group("Socle"):
        b.cyl((0, ys / 2, 0), D / 2, ys, s["socle"], studs="top", name="Socle")
    with b.group("Corps"):
        b.cyl((0, (ys + yb1) / 2, 0), Rb, yb1 - ys, ca, name="Corps")
        _porte(b, (0, 0, 0), _u(0), Rb, ys, NUIT, s["epaule"], largeur=5.0, haut=6.0)
    with b.group("Damier"):
        y_lo, y_hi = ys + 0.3, yb1 - 1.6
        w = min(8 * kx, 0.96 * 2 * Rb * math.tan(math.radians(15)))
        n = max(7, min(10, int(round((y_hi - y_lo) / w))))
        ph = (y_hi - y_lo) / n
        db = math.sqrt(Rb * Rb - (w / 2) ** 2) - 0.05
        t = 1.2
        for i in range(n):
            y = y_lo + (i + 0.5) * ph
            azs = (-90, -30, 30, 90) if i % 2 == 0 else (-120, -60, 0, 60, 120)
            for a in azs:
                b.part("block", (w, ph, t), _u(a) * (db + t / 2) + np.array([0.0, y, 0.0]), _repere_mur(a), cb,
                       name="Case")
    ep_ = s["epaule"]
    Re, he = Rb - 0.05, 0.8 * Rb
    with b.group("Epaule"):
        b.cyl((0, yb1 - 0.6, 0), Rb + 0.45, 2.0, ep_, name="Collier")
        b.ellipsoid((0, yb1, 0), (2 * Re, 2 * he, 2 * Re), ep_, collide=False, name="Epaule")
        for ang in (0, 60, 120):
            b.ellipsoid((0, yb1, 0), (0.6, 2 * he + 0.2, 2 * Re + 0.2), shade(ep_, 0.78), rot=rot_y(ang),
                        collide=False, name="Cannelure")
    Rh = 16 * kx
    hh = 0.36 * Rh
    yh = H - hh
    Rn = 5 * kx
    with b.group("Col"):
        b.cyl((0, (yb1 + 0.5 * he + yh) / 2, 0), Rn, yh - yb1 - 0.5 * he, BLANC if ca != BLANC else ep_, name="Col")
        yk = (yb1 + he + yh - hh) / 2
        b.cyl((0, yk, 0), 13 * kx, 1.4 * kx, s["disque"], studs="top", name="Disque")
    with b.group("Tete"):
        b.ellipsoid((0, yh, 0), (2 * Rh, 2 * hh, 2 * Rh), s["tete"], collide=False, name="Tete")
        b.cyl((0, yh, 0), Rh + 0.2, 0.7, s["disque"], collide=False, name="Filet")
        for k in range(6):
            _hublot_ellipsoide(b, (0, yh, 0), Rh, hh, -62.5 + 25 * k, -0.45, 1.3 * min(kx, 1.6), s["feux"],
                               s["neon"], allume=True, bord=0.45)
    with b.group("Antenne"):
        b.cyl((0, H + 2.8, 0), 0.5 * kx, 6.6, BLANC, collide=False, name="Mat")
        b.cyl((0, H + 3.8, 0), 2 * kx, 0.4, s["disque"], collide=False, name="Disque")
        b.ball((0, H + 6.1 + 0.9 * kx, 0), 0.9 * kx, s["disque"], collide=False, name="Boule")
    return _bilan(b, i0, (D, D), H, Rb, rangs=n)


# --------------------------------------------------------------------------------------------------------------
# T05 · Tour à bourrelets (recette A) / à disques liserés (recette B, variante 1)
# --------------------------------------------------------------------------------------------------------------

def tour_bourrelets(b, variant=0, hauteur=160, diametre=44, quai=None, **_):
    """Variantes 0, 2, 3 : fût, pied rayé, bourrelets épais réguliers à pilules Neon alignées (moitié avant), dôme
    à deux yeux, porte. Variante 1 : fût indigo, disques violets à liseré Neon cyan de 0,2, dôme lavande, un œil
    sombre. Quai : fût nu ± 6 (± 9 tube géant) et deux bagues. ≤ 120 pièces, ≤ 40 Neon."""
    s = schema("tour_bourrelets", variant)
    H, D = float(hauteur), float(diametre)
    i0 = len(b.parts)
    quais = _quais(quai, "tour_bourrelets", variant, H, D)
    if variant % 4 == 1:
        kx = D / 26.0
        Rf = 9 * kx
        hd = 8 * kx
        yf1 = H - hd
        Rd = D / 2 - 0.25
        ed, pas = 2.4 * kx, 6 * kx
        with b.group("Socle"):
            b.cyl((0, 0.6, 0), Rf + 2.0, 1.2, s["disques"], studs="top", name="Socle")
        with b.group("Fut"):
            b.cyl((0, (1.2 + yf1) / 2, 0), Rf, yf1 - 1.2, s["fut"], name="Fut")
            _porte(b, (0, 0, 0), _u(0), Rf, 1.2, NUIT, s["disques"], largeur=5.0, haut=6.0)
        with b.group("Disques"):
            y = max(8 * kx, 14.0)
            while y + ed / 2 <= yf1 - 4:
                if _libre(y, ed / 2, quais, 0.3):
                    b.cyl((0, y, 0), Rd, ed, s["disques"], studs="top", name="Disque")
                    b.cyl((0, y, 0), Rd + 0.2, 0.6, s["neon"], material="Neon", collide=False, shadow=False,
                          name="Lisere")
                y += pas
        with b.group("Dome"):
            b.dome((0, yf1, 0), Rf, hd, s["dome"])
            _hublot_ellipsoide(b, (0, yf1, 0), Rf - max(0.2, 0.04 * Rf), hd, 0, 0.32, 0.24 * Rf, s["disques"],
                               NUIT)
        _bagues(b, quais, Rf, s["disques"])
        return _bilan(b, i0, (D, D), H, Rf, recette="B")
    # recette A
    kx = D / 36.0
    Rf = 15 * kx
    hd = Rf
    yf1 = H - hd
    e, pas = 6 * kx, 9 * kx
    corps = s["corps"]
    fut = s.get("fut", shade(corps, 0.78))
    pied = s.get("pied", (corps, fut))
    cad = s["cadres"]
    Re = D - 0.8
    with b.group("Socle"):
        b.cyl((0, 0.75, 0), Rf + 2.5, 1.5, pied[0], studs="top", name="Socle")
        yp1 = 1.5 + 8 * kx
        hp = (yp1 - 1.5) / 4
        for k in range(4):
            b.cyl((0, 1.5 + (k + 0.5) * hp, 0), Rf + 0.4, hp, pied[k % 2], name="Pied")
    with b.group("Fut"):
        b.cyl((0, (yp1 + yf1) / 2, 0), Rf, yf1 - yp1 + 0.2, fut, name="Fut")
        _porte(b, (0, 0, 0), _u(0), Rf + 0.4, 1.5, NUIT, cad, largeur=5.0, haut=6.0)
    ys = []
    y = yp1 + e
    while y + e / 2 <= yf1 - e / 2:
        if _libre(y, e / 2, quais, 0.3):
            ys.append(y)
        y += pas
    npil = 3 if 3 * len(ys) <= 39 else 2
    azp = (-36, 0, 36) if npil == 3 else (-22, 22)
    with b.group("Bourrelets"):
        for i, y in enumerate(ys):
            b.ellipsoid((0, y, 0), (Re, e, Re), corps if i % 2 == 0 else shade(corps, 1.15), collide=False,
                        name="Bourrelet")
            for a in azp:
                _pilule_mur(b, Re / 2, a, y, 3.2 * kx, 1.2 * kx, 0.25, s["neon"], material="Neon", collide=False,
                            shadow=False, name="Pilule")
    with b.group("Dome"):
        b.cyl((0, yf1 - 0.6, 0), Rf + 0.6, 1.2, cad, name="Bague")
        res = b.dome((0, yf1, 0), Rf, hd, s["dome"])
        rd = res.info["rayon_dome"]
        for a in (-23, 23):
            _hublot_ellipsoide(b, (0, yf1, 0), rd, hd, a, 0.34, 0.2 * Rf, cad)
    _bagues(b, quais, Rf, cad)
    return _bilan(b, i0, (D, D), H, Rf, recette="A", bourrelets=len(ys))


# --------------------------------------------------------------------------------------------------------------
# T12 · Tour de bureaux à gradins
# --------------------------------------------------------------------------------------------------------------

def tour_bureaux(b, variant=0, hauteur=180, largeur=34, quai=None, **_):
    """Trois gradins : corps bas en boîte arrondie largeur × 0,5 H, corps haut (largeur - 8) jusqu'à 0,84 H,
    cabine ronde vitrée, corniche, dôme à 3 fentes et un œil ; bandes vitrées opaques tous les 9 sur l'avant et
    les côtés. Quai : bandeau nu ± 6, cadres en boîte arrondie à ± 4,5. ≤ 100 pièces, ≤ 6 Neon."""
    s = schema("tour_bureaux", variant)
    H, L = float(hauteur), float(largeur)
    i0 = len(b.parts)
    quais = _quais(quai, "tour_bureaux", variant, H, L)
    corps, bandes, dome, corn = s["corps"], s["bandes"], s["dome"], s["corniche"]
    y1, y2 = 0.5 * H, 0.84 * H
    L2 = L - 8
    rc1, rc2 = 5.0, 4.0
    Lb = L - 1.0                          # bandes vitrées (saillie 0,2) et porte (0,45) restent dans L × L
    with b.group("CorpsBas"):
        _boite_y(b, -Lb / 2, Lb / 2, 0, y1, -Lb / 2, Lb / 2, rc1, corps)
        _porte(b, (0, 0, -Lb / 2), (0, 0, -1), 0.0, 0.0, NUIT, corn, largeur=5.0, haut=6.0)
    with b.group("CorpsHaut"):
        _boite_y(b, -L2 / 2, L2 / 2, y1 - 0.3, y2, -L2 / 2, L2 / 2, rc2, corps)

    def bandes_corps(demi, rc, ya, yb, cotes=True):
        lg = 2 * (demi - rc) - 0.6
        y = ya
        while y + 1.5 <= yb:
            if _libre(y, 1.5, quais):
                b.boxc((0, y, -demi), (lg, 3.0, 0.4), bandes, collide=False, name="Bande")
                if cotes:
                    for sx in (-1, 1):
                        b.boxc((sx * demi, y, 0), (0.4, 3.0, lg), bandes, collide=False, name="Bande")
            y += 9.0

    with b.group("Bandes"):
        bandes_corps(Lb / 2, rc1, 13.5, y1 - 3.0)
        bandes_corps(L2 / 2, rc2, y1 + 6.0, y2 - 3.0, cotes=False)
        # flancs du corps haut : bande verticale à petites fenêtres (T12)
        ya_, yb_ = y1 + 3.0, y2 - 3.0
        nf = max(3, int((yb_ - ya_) // 8))
        for sx in (-1, 1):
            b.boxc((sx * L2 / 2, (ya_ + yb_) / 2, 0), (0.4, yb_ - ya_, 5.0), corn, collide=False, name="BandeLaterale")
            for k in range(nf):
                yk = ya_ + (k + 0.5) * (yb_ - ya_) / nf
                b.boxc((sx * (L2 / 2 + 0.25), yk, 0), (0.3, 2.4, 2.6), bandes, collide=False, name="Fenetre")
    Rd = L2 / 2
    hd = 0.85 * Rd
    y4 = H - hd
    y3 = y4 - 2.5
    Rc = L2 / 2 + 0.5
    with b.group("Cabine"):
        b.cyl((0, (y2 - 0.2 + y3) / 2, 0), Rc, y3 - y2 + 0.2, corps, name="Cabine")
        hc = y3 - y2
        nb = 2 if hc > 9 else 1
        for k in range(nb):
            b.cyl((0, y2 + hc * (k + 1) / (nb + 1), 0), Rc + 0.2, min(3.0, 0.3 * hc), bandes, collide=False,
                  name="Vitrage")
        Rk = L / 2 - 0.5
        b.cyl((0, (y3 + y4) / 2, 0), Rk, y4 - y3, corn, studs="top", name="Corniche")
        b.cyl((0, y3 + 0.2, 0), Rk + 0.5, 1.0, shade(corn, 0.85), collide=False, name="Corniche")
    with b.group("Dome"):
        res = b.dome((0, y4, 0), Rd, hd, dome)
        rd = res.info["rayon_dome"]
        for a in (-24, 0, 24):
            p, n = _sur_ellipsoide((0, y4, 0), rd, hd, a, 0.2)
            b.part("ellipsoid", (2.6, 0.8, 1.0), p - n * 0.25, _repere_surface(n, _t(a)), c("cyan"),
                   material="Neon", collide=False, shadow=False, name="Fente")
        _hublot_ellipsoide(b, (0, y4, 0), rd, hd, 0, 0.55, 0.17 * Rd, corn)
    ame = L / 2
    with b.group("Quai"):
        for (q, _d, ecart) in quais:
            demi, rc = (Lb / 2, rc1) if q < y1 else (L2 / 2, rc2)
            ame = demi
            for sg in (-1, 1):
                yq = q + sg * ecart
                _boite_y(b, -demi - 0.8, demi + 0.8, yq - 0.6, yq + 0.6, -demi - 0.8, demi + 0.8, rc + 0.7, corn,
                         studs=(), collide=False)
    return _bilan(b, i0, (L, L), H, ame)


# --------------------------------------------------------------------------------------------------------------
# T14 · Plateau à disques étagés (station de nacelles)
# --------------------------------------------------------------------------------------------------------------

def _nacelle_garee(b, base, coque, ceinture, k=0.78):
    """Nacelle C02 simplifiée posée (plot sur le disque) : plot, coque, ceinture, pont, bulle de verre, siège.
    8 pièces dont 1 transparente. Renvoie la hauteur totale."""
    x, y, z = base
    with b.group("Nacelle"):
        hp = 1.6 * k
        b.cyl((x, y + hp / 2, z), 1.5 * k, hp, NUIT, name="Plot")
        hb = 9 * k
        yb = y + hp - 0.4 + hb / 2
        b.ellipsoid((x, yb, z), (14 * k, hb, 14 * k), coque, collide=False, name="Coque")
        b.cyl((x, yb + 0.25 * hb, z), 6.75 * k, 0.8 * k, ceinture, collide=False, name="Ceinture")
        b.cyl((x, yb + 0.37 * hb, z), 6.5 * k, 0.5 * k, BLANC, collide=False, name="Ceinture")
        yd = yb + 0.42 * hb
        b.cyl((x, yd, z), 6.0 * k, 0.6 * k, BLANC, studs="top", collide=False, name="Pont")
        b.boxc((x, yd + 1.5 * k, z + 1.2 * k), (3.2 * k, 3.0 * k, 2.0 * k), c("rouge"), collide=False,
               name="Siege")
        b.boxc((x, yd + 1.0 * k, z - 2.4 * k), (3.0 * k, 2.0 * k, 1.2 * k), NUIT, collide=False, name="Console")
        hv = 9.5 * k
        b.ellipsoid((x, yd + 0.3 * k, z), (10.6 * k, hv, 10.6 * k), c("verre"), material="Glass",
                    transparency=0.5, collide=False, name="Bulle")
        return yd + 0.3 * k + hv / 2 - y


def plateau_disques(b, variant=0, hauteur=75, diametre=56, **_):
    """Socle, mât blanc, 4 disques à studs de rayons 0,5 / 0,41 / 0,31 / 0,22 D à sous-faces plus sombres, points
    Neon sur deux bords, boule au sommet, 2 nacelles garées (bulles de verre). ≤ 90 pièces, ≤ 12 Neon,
    ≤ 2 transparentes."""
    s = schema("plateau_disques", variant)
    H, D = float(hauteur), float(diametre)
    i0 = len(b.parts)
    t = 3.2
    radii = [D / 2 - 0.6] + [f * D for f in (0.41, 0.31, 0.22)]
    Rbou = 0.07 * D
    y1 = 0.32 * H
    y4 = H - Rbou - t / 2
    ys = [y1 + (y4 - y1) * f for f in (0.0, 0.37, 0.70, 1.0)]
    Rm = 0.075 * D
    mat, disq, dess, pts = s["mat"], s["disques"], s["dessous"], s["points"]
    hp = min(9.0, 0.6 * (y1 - t / 2))
    with b.group("Socle"):
        b.cyl((0, 0.6, 0), 0.2 * D, 1.2, mat, studs="top", name="Socle")
        b.cyl((0, 1.2 + hp / 2 - 0.1, 0), Rm + 3.0, hp + 0.2, disq, name="Pied")
        b.cyl((0, 1.2 + hp + 0.5, 0), Rm + 3.5, 1.0, mat, studs="top", name="Pied")
        _porte(b, (0, 0, 0), _u(0), Rm + 3.0, 1.0, NUIT, mat, largeur=3.6, haut=4.2)
    with b.group("Mat"):
        b.cyl((0, (1.2 + hp + 1.0 + ys[3]) / 2, 0), Rm, ys[3] - 1.2 - hp - 1.0, mat, name="Mat")
    with b.group("Disques"):
        for i, (r, y) in enumerate(zip(radii, ys)):
            b.cyl((0, y, 0), r, t, disq, studs="top", name="Disque")
            b.cyl((0, y - t / 2 - 0.25 + 0.05, 0), r - 0.5, 0.6, dess, name="Dessous")
            b.cyl((0, y - t / 2 - 0.55 - 0.6, 0), Rm + 0.7, 1.2, mat, collide=False, name="Bague")
            if i < 2:
                for a in (-75, -45, -15, 15, 45, 75):
                    b.ball(tuple(_u(a) * (r - 0.1) + np.array([0.0, y, 0.0])), 0.6, pts, material="Neon",
                           collide=False, shadow=False, name="Point")
            else:
                b.cyl((0, y + 0.2, 0), r + 0.25, 0.8, mat, collide=False, name="Lisere")
        b.ball((0, ys[3] + t / 2, 0), Rbou, mat, name="Boule")
    with b.group("Nacelles"):
        haut1 = (ys[1] - t / 2 - 0.85) - (ys[0] + t / 2)
        haut2 = (ys[2] - t / 2 - 0.85) - (ys[1] + t / 2)
        for (ri, a, coque, ceint, libre) in ((0, -50, c("jaune_citron"), c("turquoise"), haut1),
                                             (1, 55, c("orange"), c("bleu_roi"), haut2)):
            k = min(0.8, (libre - 0.6) / 13.3)
            p = _u(a) * (0.7 * radii[ri])
            _nacelle_garee(b, (p[0], ys[ri] + t / 2, p[2]), coque, ceint, k=k)
    return _bilan(b, i0, (D, D), H, Rm)


# --------------------------------------------------------------------------------------------------------------
# T17 · Tour blanche à anneau et dôme
# --------------------------------------------------------------------------------------------------------------

def tour_anneau(b, variant=0, hauteur=125, diametre=40, quai=None, **_):
    """Fût lisse à deux fines bandes vitrées (≈ 0,66 H, porte le quai), anneau épais et bombé (Ø = diametre) à
    8 fentes Neon, dôme dont le bas est caché par l'anneau, flèche rayée, mât à boule, porte en arche sombre.
    ≤ 55 pièces, ≤ 8 Neon."""
    s = schema("tour_anneau", variant)
    H, D = float(hauteur), float(diametre)
    i0 = len(b.parts)
    quais = _quais(quai, "tour_anneau", variant, H, D)
    kx = D / 32.0
    Rf = max(12.2, 10 * kx)
    ea = 8.5 * kx
    ya = max([0.66 * H] + [q + d + ea / 2 + 0.5 for (q, d, _e) in quais])
    fut, ann, dome = s["fut"], s["anneau"], s["dome"]
    f1, f2 = s["fleche"]
    with b.group("Socle"):
        b.cyl((0, 0.6, 0), min(Rf + 1.6, D / 2), 1.2, shade(ann, 0.9), studs="top", name="Socle")
    with b.group("Fut"):
        b.cyl((0, (1.2 + ya) / 2, 0), Rf, ya - 1.2, fut, name="Fut")
        _porte(b, (0, 0, 0), _u(0), Rf, 1.2, NUIT, ann, largeur=5.0, haut=6.5)
        for fr in (0.3, 0.55):
            y = fr * ya
            if not _libre(y, 1.2, quais, 0.5):
                y = min(y + 14, ya - 8)
            if _libre(y, 1.2, quais, 0.5):
                b.cyl((0, y, 0), Rf + 0.2, 2.4, HUBLOT, collide=False, name="BandeVitree")
        b.cyl((0, ya - ea / 2 - 0.4, 0), Rf + 0.35, 1.6, shade(ann, 0.75), collide=False, name="Collier")
    with b.group("Anneau"):
        b.ellipsoid((0, ya, 0), (D, ea, D), ann, collide=False, name="Anneau")
        for k in range(8):
            _pilule_mur(b, D / 2, -84 + 24 * k, ya, 4.0, 1.2, 0.2, s["neon"], material="Neon", collide=False,
                        shadow=False, name="Fente")
    rdx, rdy = 12 * kx, 9 * kx
    yd = ya + 3 * kx
    with b.group("Dome"):
        b.ellipsoid((0, yd, 0), (2 * rdx, 2 * rdy, 2 * rdx), dome, collide=False, name="Dome")
        for ang in (0, 60, 120):
            b.ellipsoid((0, yd, 0), (0.5, 2 * rdy + 0.2, 2 * rdx + 0.2), shade(dome, 0.85), rot=rot_y(ang),
                        collide=False, name="Meridien")
    ytop = yd + rdy
    with b.group("Fleche"):
        hf = max(6.0, 0.55 * (H - ytop))
        b.cone_etage((0, ytop - 1.0, 0), 2.6 * kx, 0.8, hf, [f1, f2], etages=6, collide=False)
        ym = ytop - 1.0 + hf
        b.cyl((0, (ym - 0.3 + H - 1.4) / 2, 0), 0.35, H - 1.4 - ym + 0.3, BLANC, collide=False, name="Mat")
        b.ball((0, H - 0.8, 0), 0.8, f1, collide=False, name="Boule")
    _bagues(b, quais, Rf, ann)
    return _bilan(b, i0, (D, D), H, Rf)


# --------------------------------------------------------------------------------------------------------------
# K01 · Boutique à porte en arche (front de rue)
# --------------------------------------------------------------------------------------------------------------

PICTOS_BOUTIQUE = ("etoile", "coeur", "eclair", "nuage")


def boutique_arche(b, variant=0, largeur=30, profondeur=16, hauteur=28, picto=None, **_):
    """Façade aux arêtes avant arrondies, cadre épais, listel, grande arche (porte blanche à chevron rouge et
    rivets, fermée), gélule d'enseigne à liseré Neon et pictogramme, 2 × 3 fentes, panneau latéral, tuyau en J,
    toit plat à studs et acrotère. Remplit largeur × profondeur. ≤ 65 pièces, ≤ 4 Neon."""
    s = schema("boutique_arche", variant)
    W, P, H = float(largeur), float(profondeur), float(hauteur)
    i0 = len(b.parts)
    fac, cad, arc_, gel = s["facade"], s["cadre"], s["arche"], s["gelule"]
    zf = -P / 2
    zfa = zf + 1.2                         # plan de la façade (les détails vivent entre zf et zfa)
    Hb = H - 1.2                           # dessus du corps (toit), acrotère au-dessus
    rr = 2.0
    with b.group("Corps"):
        b.box((-W / 2, 0, zfa + rr), (W / 2, Hb, P / 2), fac, studs="top", name="Corps")
        b.box((-W / 2 + rr, -0.02, zfa), (W / 2 - rr, Hb - 0.05, P / 2 - 0.1), fac, studs="top", name="Facade")
        for sx in (-1, 1):
            b.cyl((sx * (W / 2 - rr), Hb / 2 - 0.1, zfa + rr), rr, Hb, fac, studs="top", name="Arete")
    with b.group("Cadre"):
        xm = W / 2 - rr - 1.1
        for sx in (-1, 1):
            b.box((sx * xm - 1.0, -0.05, zfa - 1.0), (sx * xm + 1.0, H - 3.4, zfa + 0.1), cad, name="Montant")
        b.box((-W / 2 + rr + 0.05, H - 3.5, zfa - 1.0), (W / 2 - rr - 0.05, H, zfa + 0.15), cad, studs="top",
              name="Linteau")
        b.box((-W / 2, Hb, zfa + 0.6), (-W / 2 + 0.8, H, P / 2), cad, studs="top", name="Acrotere")
        b.box((W / 2 - 0.8, Hb, zfa + 0.6), (W / 2, H, P / 2), cad, studs="top", name="Acrotere")
        b.box((-W / 2 + 0.8, Hb, P / 2 - 0.8), (W / 2 - 0.8, H - 0.05, P / 2), cad, studs="top", name="Acrotere")
    ya = 9.0                                # naissance de l'arche
    ra = min(7.0, xm - 4.5)                 # demi-largeur du cadre de l'arche (place pour tuyau et panneau)
    with b.group("Arche"):
        # trois couches en relief (cadre doré, joint sombre, porte blanche) : faces jamais confondues
        for i, (rw, dz, col_, nom) in enumerate(((ra, 0.8, arc_, "Arche"), (ra - 0.8, 0.95, NUIT, "Joint"),
                                                 (ra - 1.6, 1.08, BLANC, "Porte"))):
            b.box((-rw, -0.05 * (i + 1), zfa - dz), (rw, ya - 0.02 * i, zfa + 0.1 + 0.05 * i), col_, name=nom)
            z0, z1 = zfa - dz + 0.02, zfa + 0.08 + 0.05 * i
            b.cyl((0, ya, (z0 + z1) / 2), rw, z1 - z0, col_, axis="z", name=nom)
        b.box((-0.15, 0.3, zfa - 1.14), (0.15, ya + ra - 2.0, zfa - 1.0), NUIT, collide=False, name="Joint")
        yc = 5.6
        for sy in (-1, 1):
            b.part("block", (2.4, 0.55, 0.14), (0.3 * ra, yc + sy * 0.72, zfa - 1.11), rot_z(-38 * sy), c("rouge"),
                   collide=False, name="Chevron")
        for k in range(7):
            ang = math.radians(-90 + 180 * k / 6)
            px, py = (ra - 0.4) * math.sin(ang), ya + (ra - 0.4) * math.cos(ang)
            b.cyl((px, py, zfa - 0.85), 0.32, 0.2, NUIT, axis="z", collide=False, name="Rivet")
    with b.group("Enseigne"):
        yl = ya + ra + 0.6
        b.box((-xm + 1.0, yl, zfa - 1.2), (xm - 1.0, yl + 0.6, zfa + 0.1), arc_, collide=False, name="Listel")
        yg = (yl + 0.6 + H - 3.5) / 2
        hg = min(4.6, (H - 3.5) - (yl + 0.6) - 1.4)
        lg = min(15.0, 2 * xm - 4.0)
        _gelule(b, (0, yg, zfa - 1.25), lg, hg, 0.5, gel, collide=False)
        _gelule(b, (0, yg, zfa - 1.05), lg + 0.5, hg + 0.4, 0.5, s["neon"], material="Neon", collide=False,
                shadow=False)
        kind = picto or PICTOS_BOUTIQUE[variant % 4]
        pc = BLANC if gel in (c("rose_bonbon"), c("violet"), c("turquoise")) else c("jaune_citron")
        _picto(b, kind, (0, yg, zfa - 1.5 - 0.15), (1.25 if kind == "nuage" else 0.95) * hg, pc)
        ysl = H - 3.5 - 2.6
        for sx in (-1, 1):
            for k in (-1, 0, 1):
                b.boxc((sx * (xm - 3.2) + k * 1.3, ysl, zfa - 0.1), (0.6, 3.0, 0.3), shade(cad, 0.55),
                       collide=False, name="Fente")
    with b.group("Equipement"):
        xp0, xp1 = -xm + 1.6, -xm + 3.5
        zp = zfa - 0.45
        for x in (xp0, xp1):
            b.cyl((x, 2.9, zp), 0.7, 6.2, TUYAU, name="Tuyau")
            b.ball((x, 6.0, zp), 0.72, TUYAU, collide=False, name="Coude")
        b.cyl(((xp0 + xp1) / 2, 6.0, zp), 0.7, xp1 - xp0, TUYAU, axis="x", collide=False, name="Tuyau")
        b.box((xm - 3.6, 3.0, zfa - 0.3), (xm - 1.2, 7.4, zfa + 0.1), BLANC, collide=False, name="Panneau")
        b.box((xm - 3.3, 3.4, zfa - 0.45), (xm - 1.5, 7.0, zfa), HUBLOT, collide=False, name="Ecran")
    return _bilan(b, i0, (W, P), H)


# --------------------------------------------------------------------------------------------------------------
# Kiosques : dôme (K04), boutons (K02), arcade (K03), hublots (K07)
# --------------------------------------------------------------------------------------------------------------

def _socle_carre(b, W, P, couleur, h=1.0, r=4.0):
    with b.group("Socle"):
        _boite_y(b, -W / 2, W / 2, 0, h, -P / 2, P / 2, min(r, W / 4, P / 4), couleur)


def _kiosque_dome(b, s, W, P, H):
    Rb = (P - 2) / 2
    Rt = 0.78 * Rb
    _socle_carre(b, W, P, s["socle"])
    yb = 0.5 * H
    hd = 0.4 * H
    with b.group("Kiosque"):
        b.cyl((0, 2.0, 0), Rt + 0.5, 2.0, s["bord"], studs="top", name="Plinthe")
        b.cyl((0, (3.0 + yb) / 2, 0), Rt, yb - 3.0, s["tambour"], name="Tambour")
        _porte(b, (0, 0, 0), _u(0), Rt, 3.0, NUIT, s["bord"], largeur=4.6, haut=4.6)
        hf = min(4.6, yb - 3.0 - 3.2)
        for a in (-62, -31, 31, 62):
            u = _u(a)
            M = _repere_mur(a)
            yw = 3.0 + (yb - 3.0) * 0.52
            b.part("ellipsoid", (3.8, hf + 0.8, 0.8), u * (Rt - 0.15) + np.array([0, yw, 0]), M, s["bord"],
                   collide=False, name="Cadre")
            b.part("ellipsoid", (3.0, hf, 0.8), u * (Rt - 0.05) + np.array([0, yw, 0]), M, HUBLOT,
                   collide=False, name="Fenetre")
        b.ellipsoid((0, yb, 0), (2 * Rb, 3.0, 2 * Rb), s["bord"], collide=False, name="Bord")
        res = b.dome((0, yb, 0), Rt, hd, s["dome"], collide=False)
        rd = res.info["rayon_dome"]
        for (dy, col_) in ((1.9, BLANC), (3.0, s["bord"])):
            rr = rd * math.sqrt(max(0.0, 1 - (dy / hd) ** 2)) + 0.15
            b.cyl((0, yb + dy, 0), rr, 0.5, col_, collide=False, name="Filet")
        for a in (-75, -45, -15, 15, 45, 75):
            p, n = _sur_ellipsoide((0, yb, 0), rd, hd, a, 0.55)
            b.ball(tuple(p + n * 0.1), 0.55, BLANC, collide=False, name="Point")
        ytop = yb + hd
        b.cyl((0, (ytop - 0.4 + H - 1.4) / 2, 0), 0.35, H - 1.4 - ytop + 0.4, BLANC, collide=False, name="Mat")
        b.ball((0, H - 0.8, 0), 0.8, s["bord"], collide=False, name="Boule")


def _kiosque_boutons(b, s, W, P, H):
    R = (P - 2) / 2
    Rt = R - 1.0
    _socle_carre(b, W, P, BLANC)
    yt0, yt1 = 2.4, H - 6.0
    with b.group("Kiosque"):
        b.cyl((0, 1.7, 0), R, 1.4, s["bandeau"], studs="top", name="Base")
        b.cyl((0, (yt0 + yt1) / 2, 0), Rt, yt1 - yt0, s["tambour"], name="Tambour")
        for y in (yt0 + 0.4, yt1 - 0.4):
            b.cyl((0, y, 0), Rt + 0.3, 0.6, s["bandeau"], collide=False, name="Bague")
        cols = s["boutons"]
        for i, fy in enumerate((0.23, 0.5, 0.77)):
            y = yt0 + (yt1 - yt0) * fy
            dec = 6.0 if i == 1 else 0.0
            for j, a0 in enumerate((-66, -45, -24, 24, 45, 66)):
                a = a0 + (dec if a0 < 0 else -dec)
                u = _u(a)
                r = 1.25
                ep = 0.4 + r * r / (2 * Rt)
                _cyl_axe(b, u * (Rt + 0.3 - ep / 2) + np.array([0, y, 0]), u, ep, r, cols[(i + j) % len(cols)],
                         collide=False, name="Bouton")
        hpn = yt1 - yt0 - 1.6
        _bloc_mur(b, Rt, 0, (yt0 + yt1) / 2, 5.4, hpn, 0.3, s["bandeau"], collide=False, name="Panneau")
        _bloc_mur(b, Rt, 0, yt0 + 0.72 * (yt1 - yt0), 3.4, 1.8, 0.45, s["neon"], material="Neon", collide=False,
                  shadow=False, name="Ecran")
        for k in range(4):
            _bloc_mur(b, Rt, 0, yt0 + (0.22 + 0.11 * k) * (yt1 - yt0), 2.6, 0.7, 0.45, cols[k % len(cols)],
                      collide=False, name="Pilule")
        b.cyl((0, yt1 + 1.4, 0), Rt + 0.3, 2.8, s["bandeau"], name="Bandeau")
        b.cyl((0, yt1 + 2.8 + 0.7, 0), Rt - 1.0, 1.4, s["tambour"], studs="top", name="Chapeau")
        b.dome((0, yt1 + 4.2, 0), 0.5 * Rt, H - yt1 - 4.2, BLANC, collide=False)


def _kiosque_arcade(b, s, W, P, H):
    corps, lis, neon = s["corps"], s["liseres"], s["neon"]
    zf = -P / 2
    zfa = zf + 1.0
    Wb = W - 8 if W > 24 else W
    x0, x1 = -W / 2, -W / 2 + Wb
    xc = (x0 + x1) / 2
    hb = H - P / 2
    with b.group("Borne"):
        b.box((x0, 0, zfa), (x1, hb, P / 2), corps, name="Borne")
        b.cyl((xc, hb, 0.5), P / 2 - 0.5, Wb - 0.2, corps, axis="x", name="Toit")
        b.box((x0 + 0.15, hb - 0.3, zfa - 0.3), (x1 - 0.15, hb + 0.3, zfa + 0.1), lis, collide=False,
              name="Lisere")
        b.box((x0 + 0.15, 8.3, zfa - 0.3), (x1 - 0.15, 8.9, zfa + 0.1), lis, collide=False, name="Lisere")
        ys0 = 8.9 + (hb - 0.3 - 8.9) / 2
        hs_ = min(4.6, hb - 0.3 - 8.9 - 0.6)
        b.box((xc - Wb / 2 + 1.5, ys0 - hs_ / 2, zfa - 0.15), (xc + Wb / 2 - 1.5, ys0 + hs_ / 2, zfa + 0.05), NUIT,
              collide=False, name="Ecran")
        for row, yy in enumerate((ys0 + 1.0, ys0 - 1.0)):
            for k in range(3):
                lg = (3.6, 2.4, 3.0)[(k + row) % 3]
                xx = xc - 5.0 + 5.0 * k + (0.6 if row else 0.0)
                b.boxc((xx, yy, zfa - 0.25), (lg, 0.8, 0.2), neon, material="Neon", collide=False, shadow=False,
                       name="Fente")
        b.wedge((x0 + 0.6, 6.6, zf), (x1 - 0.6, 8.3, zfa), shade(corps, 0.8), down="-z", name="Console")
        b.box((xc - Wb / 2 + 2.0, 1.2, zfa - 0.4), (xc + Wb / 2 - 2.0, 5.8, zfa + 0.1), shade(corps, 1.18),
              collide=False, name="PanneauBas")
        xcr = xc - Wb / 2 + 5.0
        b.boxc((xcr, 3.5, zfa - 0.55), (3.2, 1.0, 0.3), BLANC, collide=False, name="Croix")
        b.boxc((xcr, 3.5, zfa - 0.6), (1.0, 3.2, 0.4), BLANC, collide=False, name="Croix")
        for k in range(3):
            b.boxc((xcr + 4.0 + 2.2 * k, 3.5, zfa - 0.5), (1.4, 0.6, 0.2), lis, collide=False, name="Tiret")
    if W > 24:
        xa, xb_ = x1, W / 2
        xm = (xa + xb_) / 2
        with b.group("Presentoir"):
            b.box((xa, 0, zf + 0.2), (xb_, 1.4, P / 2), BLANC, studs="top", name="Socle")
            b.box((xa, 1.4, P / 2 - 2.0), (xb_, 10.0, P / 2), shade(corps, 0.85), studs="top", name="Fond")
            cubes = ((5.6, 1.4, 1.6, 12, c("orange")), (4.6, 7.0, 2.2, -10, lis),
                     (3.6, 11.6, 1.8, 18, c("jaune_or")))
            for (sz, y0, dz, yaw, col_) in cubes:
                b.boxc((xm + 0.2 * (yaw > 0), y0 + sz / 2, zf + 0.2 + dz + sz / 2), (sz, sz, sz), col_, yaw=yaw,
                       studs="top", name="Cube")
            yt = 11.6 + 3.6
            zc = zf + 0.2 + 1.2 + 2.0
            b.cyl((xm, yt + 1.0, zc), 0.35, 2.0, BLANC, collide=False, name="Pied")
            b.ellipsoid((xm, yt + 2.6, zc), (5.0, 1.2, 5.0), BLANC, rot=rot_x(40), collide=False,
                        name="Parabole")
            b.cyl_entre((xm, yt + 2.6, zc), (xm, yt + 4.2, zc - 1.3), 0.12, BLANC, collide=False, name="Bras")
            b.ball((xm, yt + 4.2, zc - 1.3), 0.3, c("rouge"), collide=False, name="Capteur")


def _kiosque_hublots(b, s, W, P, H):
    tam, cad, vit = s["tambour"], s["cadre"], s["vitre"]
    zf = -P / 2
    Rt = min(6.4, (P - 1.3) / 2, (W / 2 - 2.45) / 2)
    zc = zf + 1.1 + Rt
    with b.group("Socle"):
        b.box((-W / 2, 0, zf), (W / 2, 1.0, P / 2), BLANC, studs="top", name="Socle")
        b.box((-W / 2, 1.0, P / 2 - 2.0), (W / 2, H - 4.0, P / 2), shade(tam, 0.8), studs="top", name="Fond")
    xs = (-(1.55 + Rt), 1.55 + Rt)
    yt1 = H - 1.6
    for i, x in enumerate(xs):
        with b.group("Tambour"):
            b.cyl((x, (0.8 + yt1) / 2, zc), Rt, yt1 - 0.8, tam, name="Tambour")
            b.cyl((x, yt1 + 0.4, zc), Rt + 0.2, 0.8, cad, studs="top", name="Couvercle")
            b.cyl((x, yt1 + 1.0, zc), 0.35 * Rt, 0.8, cad, studs="top", name="Bouchon")
            yh = 1.0 + (yt1 - 1.0) * 0.48
            zh = zc - Rt
            b.cyl((x, yh, zh - 0.2), 4.5, 0.8, cad, axis="z", collide=False, name="Cadre")
            b.cyl((x, yh, zh - 0.45), 3.6, 0.8, vit, axis="z", collide=False, name="Hublot")
            b.boxc((x + 3.6, yh, zh - 0.75), (0.8, 2.2, 0.5), cad, collide=False, name="Poignee")
            b.cyl((x, yh - 1.2, zh - 0.88), 1.2, 0.2, shade(vit, 1.25), axis="z", collide=False, name="Reflet")
        with b.group("Tuyau"):
            sx = -1 if i == 0 else 1
            xo = x + sx * (Rt - 0.3)
            xe = x + sx * (Rt + 0.35)
            yj = yt1 - 2.5
            zj = zc + 1.5
            b.cyl(((xo + xe) / 2, yj, zj), 0.5, abs(xe - xo), TUYAU, axis="x", collide=False, name="Tuyau")
            b.ball((xe, yj, zj), 0.52, TUYAU, collide=False, name="Coude")
            b.cyl((xe, (1.0 + yj) / 2, zj), 0.5, yj - 1.0, TUYAU, collide=False, name="Tuyau")
    with b.group("Commande"):
        b.box((-1.5, 0.9, zf + 1.2), (1.5, 7.5, zf + 4.0), cad, studs="top", name="Boitier")
        b.box((-1.1, 5.0, zf + 0.95), (1.1, 6.8, zf + 1.2), NUIT, collide=False, name="Ecran")
        b.boxc((0, 5.9, zf + 0.85), (1.4, 0.6, 0.2), c("cyan"), material="Neon", collide=False, shadow=False,
               name="Voyant")
        for k, col_ in enumerate((c("rouge"), c("jaune_citron"))):
            b.cyl((-0.6 + 1.2 * k, 3.4, zf + 1.05), 0.42, 0.3, col_, axis="z", collide=False, name="Bouton")


def kiosque(b, variant=0, type="dome", largeur=26, profondeur=26, hauteur=24, **_):
    """Kiosques du front de rue. `type` : « dome » (K04, kiosque rond à dôme sur socle carré), « boutons » (K02,
    tambour à 18 boutons, panneau à écran Neon, bandeau sans texte), « arcade » (K03, borne à toit en
    demi-cylindre, 6 fentes Neon, présentoir de cubes et parabole si largeur > 24), « hublots » (K07, paire de
    tambours à grand hublot et tuyaux en J, boîtier de commande). ≤ 50 pièces, ≤ 6 Neon."""
    W, P, H = float(largeur), float(profondeur), float(hauteur)
    i0 = len(b.parts)
    t = str(type)
    if t == "dome":
        _kiosque_dome(b, schema("kiosque_dome", variant), W, P, H)
    elif t == "boutons":
        _kiosque_boutons(b, schema("kiosque_boutons", variant), W, P, H)
    elif t == "arcade":
        _kiosque_arcade(b, schema("kiosque_arcade", variant), W, P, H)
    elif t == "hublots":
        _kiosque_hublots(b, schema("kiosque_hublots", variant), W, P, H)
    else:
        raise ValueError(f"kiosque : type inconnu {t!r}")
    return _bilan(b, i0, (W, P), H, type=t)


# --------------------------------------------------------------------------------------------------------------
# Connecteurs bas (ferment la couronne entre deux bâtiments)
# --------------------------------------------------------------------------------------------------------------

def _niche(b, x, zw, larg, ys, cadre, fond=NUIT):
    """Niche en plein cintre : cadre (bloc + cylindre) puis fond sombre devant lui (0,1 plus en avant). 4 pièces."""
    rc, rn = larg / 2 + 0.75, larg / 2
    b.box((x - rc, -0.04, zw - 0.12), (x + rc, ys, zw + 0.1), cadre, name="Cadre")
    b.cyl((x, ys, zw - 0.01), rc, 0.18, cadre, axis="z", name="Cadre")
    b.box((x - rn, -0.08, zw - 0.22), (x + rn, ys - 0.03, zw + 0.06), fond, name="Niche")
    b.cyl((x, ys, zw - 0.08), rn, 0.24, fond, axis="z", name="Niche")


def _colonne_rayee(b, x, z, r, y0, y1, cols, n=5):
    h = (y1 - y0) / n
    for k in range(n):
        b.cyl((x, y0 + (k + 0.5) * h, z), r + (0.03 if k % 2 else 0.0), h, cols[k % len(cols)], name="Colonne")


def connecteur(b, variant=0, largeur=8, profondeur=12, hauteur=16, couleur="lavande", accent="turquoise", **_):
    """Volume bas fermé qui remplit largeur × profondeur × hauteur, toit plat à studs (avant sur la ligne des
    façades, mur 0,3 en retrait). Variantes : 0 arcade (niches en plein cintre tous les 8, boules de haie ;
    galerie de l'axe nord si largeur ≥ 40 : grand arc Ø 14 entre deux colonnes rayées), 1 rayé (deux bandeaux,
    hublots tous les 8, jardinière), 2 vitrine (bande vitrée à meneaux, auvent en demi-cylindre, pictogramme),
    3 portique (deux piliers, linteau, petit dôme, fond bleu nuit à liseré Neon). ≤ 14 + 0,7 × largeur pièces,
    ≤ 1 Neon."""
    W, P, H = float(largeur), float(profondeur), float(hauteur)
    i0 = len(b.parts)
    col, acc = c(couleur), c(accent)
    v = variant % 4
    zf = -P / 2
    galerie = v == 0 and W >= 40
    zw = zf + (1.6 if galerie else 0.3)
    hr = 1.0
    toit = BLANC if couleur not in CLAIRS else acc
    with b.group("Corps"):
        b.box((-W / 2, 0, zw), (W / 2, H - hr, P / 2), NUIT if v == 3 else col, name="Mur")
        b.box((-W / 2, H - hr, zf), (W / 2, H, P / 2), toit, studs="top", name="Toit")
    n = max(1, int(round(W / 8)))
    if v == 0 and not galerie:
        with b.group("Arcade"):
            for k in range(n):
                x = -W / 2 + (k + 0.5) * W / n
                _niche(b, x, zw, min(4.6, W / n - 2.6), 0.42 * H, acc)
            xs = [-W / 2 + (k + 0.5) * W / (2 * n) for k in range(2 * n)]
            _haies(b, xs, H, zf + 2.6, taille=min(3.4, W / (2 * n) + 0.2))
    elif galerie:
        with b.group("Galerie"):
            ys = H - 10.5
            _niche(b, 0, zw, 14.0, ys, acc)
            # liseré lumineux du grand arc (seul son bord dépasse entre le fond sombre et le cadre)
            nc = c(accent) if accent in ("cyan", "neon_orange", "neon_blanc", "neon_violet") else c("neon_violet")
            b.cyl((0, ys, zw - 0.1), 7.0 + 0.3, 0.1, nc, axis="z", material="Neon", collide=False, shadow=False,
                  name="Lisere")
            xc = 7.75 + 1.9
            for sx in (-1, 1):
                _colonne_rayee(b, sx * xc, zw + 0.05, 1.6, -0.05, H - hr + 0.3, (acc, BLANC), n=5)
                b.ball((sx * xc, H + 1.0, zw + 0.05), 1.3, c("or"), collide=False, name="Boule")
            x_in, x_out = xc + 1.6 + 0.4, W / 2 - 0.4
            m = 4
            pas = (x_out - x_in) / m
            for sx in (-1, 1):
                for k in range(m):
                    x = sx * (x_in + (k + 0.5) * pas)
                    _niche(b, x, zw, pas - 2.4, 0.45 * H, acc)
            xs = [sx * (x_in + (k + 0.5) * pas) for sx in (-1, 1) for k in range(m)]
            _haies(b, xs, H, zf + 3.2, taille=3.6)
    elif v == 1:
        with b.group("Raye"):
            for (y0, h, cc) in ((0.28 * H, 1.4, acc), (0.74 * H, 1.0, BLANC)):
                b.box((-W / 2 + 0.03, y0, zf), (W / 2 - 0.03, y0 + h, zw + 0.1), cc, collide=False, name="Bandeau")
            yh = 0.51 * H
            for k in range(n):
                x = -W / 2 + (k + 0.5) * W / n
                f = min(2.2, 0.17 * H)
                b.cyl((x, yh, zw - 0.0), f, 0.5, acc, axis="z", collide=False, name="Cadre")
                b.cyl((x, yh, zw - 0.1), f - 0.6, 0.4, HUBLOT, axis="z", collide=False, name="Hublot")
            b.box((-W / 2 + 0.6, H, zf + 1.2), (W / 2 - 0.6, H + 1.0, zf + 3.6), acc, studs="top",
                  name="Jardiniere")
            xs = [-W / 2 + (k + 0.5) * W / (2 * n) for k in range(2 * n)]
            _haies(b, xs, H + 1.0, zf + 2.4, taille=min(3.0, W / (2 * n) + 0.1))
    elif v == 2:
        with b.group("Vitrine"):
            yv0, yv1 = 1.0, min(8.0, 0.5 * H)
            b.box((-W / 2 + 0.8, -0.05, zw - 0.2), (W / 2 - 0.8, yv0, zw + 0.1), BLANC, name="Allege")
            b.box((-W / 2 + 0.8, yv0, zw - 0.1), (W / 2 - 0.8, yv1, zw + 0.1), HUBLOT, collide=False,
                  name="Vitre")
            nm = max(1, n * 2 - 1)
            for k in range(nm):
                x = -W / 2 + 0.8 + (k + 1) * (W - 1.6) / (nm + 1)
                b.box((x - 0.3, yv0 + 0.02, zw - 0.25), (x + 0.3, yv1 + 0.02, zw + 0.05), BLANC, collide=False,
                      name="Meneau")
            b.box((-W / 2 + 0.8, yv1, zw - 0.25), (W / 2 - 0.8, yv1 + 0.5, zw + 0.1), BLANC, collide=False,
                  name="Meneau")
            ya = max(2 * H / 3, 9.6)
            b.cyl((0, ya, zf + 0.1), 1.4, W - 0.2, acc, axis="x", collide=False, name="Auvent")
            yp = (ya + 1.4 + H - hr) / 2
            kind = ("piece", "coeur", "nuage", "eclair")[int(abs(W * 7 + H * 3)) % 4]
            _picto(b, kind, (0, yp, zw - 0.25), min(3.6, H - hr - ya - 2.2), acc if acc != col else BLANC)
    else:
        with b.group("Portique"):
            hp = H - hr - 1.8
            for sx in (-1, 1):
                x = sx * (W / 2 - 0.95)
                b.box((x - 0.9, -0.05, zf + 0.9), (x + 0.9, hp, zf + 2.4), col, name="Pilier")
                b.cyl((x, hp / 2 - 0.05, zf + 0.9), 0.9, hp + 0.1, col, name="Pilier")
            b.box((-W / 2 + 0.03, hp, zf + 0.05), (W / 2 - 0.03, H - hr + 0.3, zf + 2.4), col, name="Linteau")
            nc = c(accent) if accent in ("cyan", "neon_orange", "neon_blanc", "neon_violet") else c("cyan")
            b.box((-W / 2 + 1.8, 0.36 * H, zw - 0.15), (W / 2 - 1.8, 0.36 * H + 0.35, zw + 0.1), nc,
                  material="Neon", collide=False, shadow=False, name="Lisere")
            rdm = min(W / 2 - 1.2, 3.2)
            b.dome((0, H, zf + P / 2), rdm, 0.8 * rdm, acc, collide=False)
    return _bilan(b, i0, (W, P), H)
