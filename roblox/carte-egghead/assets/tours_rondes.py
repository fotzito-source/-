"""Tours rondes de la couronne (rang 2), repères d'angle et tambours / fusées du front de rue (rang 1).

Neuf fonctions (SPECS.md, fiche « assets/tours_rondes.py » ; recettes STYLE.md T01, T02, T03, T07, T08, T10, T11,
T13, T16), toutes de la forme `f(b, variant=0, **params) -> dict` :

    tour_galettes(b, variant=0, hauteur=200, diametre=54, quai=None)      # T01 pile de galettes à fentes
    tour_champignon(b, variant=0, hauteur=170, diametre=56, quai=None)    # T02 champignon sur pilier et halo
    tour_soucoupe(b, variant=0, hauteur=150, diametre=56)                 # T08 soucoupe sur gobelet
    tour_tete_boule(b, variant=0, hauteur=150, diametre=42)               # T03 cône rayé à tête-boule
    tour_pneus(b, variant=0, hauteur=240, diametre=72)                    # T07 tour en pneus (repère d'angle)
    tour_ruban(b, variant=0, hauteur=250, diametre=72)                    # T10 champignon géant à ruban (angle)
    tour_bulbe(b, variant=0, hauteur=115, diametre=46)                    # T13 bulbe à cheminée qui fume
    tour_fusee(b, variant=0, hauteur=55, diametre=20, type="blanche")     # T11 fusée (rang 1)
    tour_hublots(b, variant=0, hauteur=42, diametre=30)                   # T16 tambour à fenêtres (rang 1)

Conventions : origine au centre de l'emprise au sol (y = 0), avant vers -Z local ; `diametre` = Ø maximal au sol et
jusqu'à y = 40 (seuls les bords de chapeau, soucoupes et halos le dépassent, plus haut ; la fusée a en plus son socle
rond R D/2 + 1 demandé par la fiche) ; `hauteur` = sommet de la coiffe (antenne ou flèche : + 10 au plus ; la fumée
du bulbe monte jusqu'à 1,35 H). Gros détails sur la moitié avant (avant ± 70°), dos en aplats. Studs sur tous les
dessus plats, jamais sur un flanc ni un ellipsoïde. Couleurs : `palette.schema(<archétype>, variant)`. Les tours
hautes ajoutent des éléments répétés (galettes, pneus, rangs de hublots, rainures) au lieu de les étirer.

Quais (`quai`, galettes et champignon) : hauteurs où un tube de verre de carte.py entre dans l'âme (bout dans
l'axe). Le fût reste nu sur ± 6 avec deux bagues R(âme + 0,8) · ép 1,2 à ± 4,5 ; pour un tube géant (rayon 6,
`plan.TUBES`), la bande nue et l'écart des bagues s'élargissent (± 9 et ± 7,6) pour que le tube passe entre elles.
Le type du tube est retrouvé dans `plan.CEINTURE` / `plan.TUBES` ; on peut aussi le donner :
`quai=[(100, 6.0), 150]` (hauteur, rayon du tube).

Retour : {"emprise": (d, d), "hauteur": h, "ame": rayon du fût plein, "sommet": y le plus haut, "pieces": n,
"neon": n, "transparentes": n, ...}.
"""

from __future__ import annotations

import math

import numpy as np

import plan
from kit import bornes, mix, repere_direction, rot_x, rot_y, shade
from palette import c, schema

# --------------------------------------------------------------------------------------------------------------
# Outils communs
# --------------------------------------------------------------------------------------------------------------

PORTE = c("bleu_nuit")          # panneau des portes (le cadre prend la couleur vive du bâtiment)
NEON_MAX_GALETTES = plan.BUDGET_FONCTION.get("tours_rondes.tour_galettes", (140, 40, 0))[1]   # Neon par appel
HUBLOT = c("hublot")            # verre opaque des hublots et des bandes vitrées


def _u(theta: float) -> np.ndarray:
    """Direction horizontale à l'azimut `theta` (degrés) : 0 = avant (-Z), 90 = +X, 180 = arrière (+Z)."""
    t = math.radians(theta)
    return np.array([math.sin(t), 0.0, -math.cos(t)])


def _t(theta: float) -> np.ndarray:
    """Tangente horizontale au cercle à l'azimut `theta` (vers les azimuts croissants)."""
    t = math.radians(theta)
    return np.array([math.cos(t), 0.0, math.sin(t)])


def _repere_mur(theta: float) -> np.ndarray:
    """Rotation d'un bloc posé sur un mur rond à l'azimut theta : X tangent, Y vertical, Z vers l'intérieur."""
    x = _t(theta)
    y = np.array([0.0, 1.0, 0.0])
    return np.column_stack([x, y, np.cross(x, y)])


def _cyl_axe(b, centre, axe, longueur, rayon, couleur, **kw):
    """Cylindre d'axe quelconque (vecteur), centré en `centre`. 1 pièce."""
    return b.part("cyl", (longueur, 2 * rayon, 2 * rayon), centre, repere_direction(axe), couleur, **kw)


def _rentre(R: float, s: float) -> float:
    """Profondeur du mur courbe (rayon R) à la distance latérale s de l'axe d'un détail plat."""
    return R - math.sqrt(max(R * R - s * s, 0.0)) if R else 0.0


def _y(v: float) -> np.ndarray:
    return np.array([0.0, v, 0.0])


def _hublot(b, p, n, f, rho, cadre, verre=HUBLOT, *, allume=False, bord=None, extra=0.0):
    """Hublot rond posé sur une surface (point p, normale n, rayon de courbure rho) : cadre d'épaisseur
    0,4 + f²/(2 rho), face avant à +0,3 ; vitre (opaque, ou Neon si `allume`) de rayon f - bord, face avant à +0,4.
    2 pièces, sans collision."""
    n = np.asarray(n, float)
    n = n / np.linalg.norm(n)
    p = np.asarray(p, float)
    ep = 0.4 + f * f / (2 * rho) + extra
    _cyl_axe(b, p + n * (0.3 - ep / 2), n, ep, f, cadre, collide=False, name="Cadre")
    rv = max(0.5, f - (bord if bord is not None else max(0.6, 0.28 * f)))
    _cyl_axe(b, p + n * 0.25, n, 0.3, rv, verre, material="Neon" if allume else "SmoothPlastic",
             collide=False, shadow=not allume, name="Hublot")


def _hublot_mur(b, R, theta, y, f, cadre, verre=HUBLOT, **kw):
    """Hublot sur un mur cylindrique vertical de rayon R."""
    u = _u(theta)
    _hublot(b, u * R + _y(y), u, f, R, cadre, verre, **kw)


def _sur_ellipsoide(C, a, h, theta, s):
    """Point et normale de l'ellipsoïde de centre C, rayon horizontal a, demi-hauteur h, à l'azimut theta et à la
    hauteur relative s (y - yC = s h)."""
    r = a * math.sqrt(max(0.0, 1.0 - s * s))
    u = _u(theta)
    p = np.asarray(C, float) + u * r + _y(h * s)
    n = u * (r / (a * a)) + _y(s / h)
    return p, n / np.linalg.norm(n)


def _hublot_ellipsoide(b, C, a, h, theta, s, f, cadre, verre=HUBLOT, **kw):
    p, n = _sur_ellipsoide(C, a, h, theta, s)
    rho = min(a, h) ** 2 / max(a, h)
    _hublot(b, p, n, f, rho, cadre, verre, **kw)


def _bloc_mur(b, R, theta, y, larg, haut, saillie, couleur, **kw):
    """Petit bloc posé sur un mur rond (fente, meneau, rainure) : face avant à R + saillie, dos enfoncé."""
    ep = saillie + 0.25 + _rentre(R, larg / 2)
    ctr = _u(theta) * (R + saillie - ep / 2) + _y(y)
    return b.part("block", (larg, haut, ep), ctr, _repere_mur(theta), couleur, **kw)


def _fente(b, R, theta, y, L, hs, couleur, saillie=0.45, p=2.0):
    """Fente lumineuse (pilule Neon `L × hs`) incrustée dans un bord cylindrique de rayon R : seule sa face
    avant dépasse (`saillie` au milieu, 0 aux bouts) ; elle épouse la courbure sur toute sa longueur. 1 pièce."""
    ctr = _u(theta) * (R + saillie - p / 2) + _y(y)
    return b.ellipsoid(ctr, (L, hs, p), couleur, rot=rot_y(-theta), material="Neon", collide=False, shadow=False,
                       name="Fente")


def _porte(b, R, y0, couleur=PORTE, cadre="#F27A22", *, theta=0.0, largeur=5.0, haut=6.0):
    """Porte en arche sur un mur rond de rayon R, seuil à y0 (STYLE § 3.0) : panneau 5 × 6 + arche R2,5 (sommet à
    y0 + 8,5), cadre de 6,6 et R3,3 en retrait de 0,2. Les pieds descendent sous le seuil (cadre -0,2, panneau -0,1)
    dans le socle : aucune face confondue avec le bas du mur. 4 pièces."""
    u = _u(theta)
    M = _repere_mur(theta)
    rc, rp = largeur / 2 + 0.8, largeur / 2
    ec, ep = _rentre(R, rc), _rentre(R, rp)
    with b.group("Porte"):
        a0, a1 = R - ec - 0.2, R + 0.25
        hc = haut + 0.1
        b.part("block", (2 * rc, hc, a1 - a0), u * (a0 + a1) / 2 + _y(y0 - 0.2 + hc / 2), M, cadre, name="Cadre")
        a0, a1 = R - ec - 0.25, R + 0.2
        _cyl_axe(b, u * (a0 + a1) / 2 + _y(y0 + haut), u, a1 - a0, rc, cadre, name="Cadre")
        a0, a1 = R - ep - 0.1, R + 0.45
        b.part("block", (2 * rp, haut + 0.1, a1 - a0), u * (a0 + a1) / 2 + _y(y0 - 0.1 + (haut + 0.1) / 2), M,
               couleur, name="Porte")
        a0, a1 = R - ep - 0.15, R + 0.4
        _cyl_axe(b, u * (a0 + a1) / 2 + _y(y0 + haut), u, a1 - a0, rp, couleur, name="Porte")


def _antenne(b, y0, h, couleur, boule, *, r=0.5, rb=1.2, disque=None, rd=2.0):
    """Antenne : tige + boule (+ disque facultatif à 60 %). 2-3 pièces, sans collision. Renvoie le sommet."""
    with b.group("Antenne"):
        b.cyl((0, y0 + h / 2, 0), r, h, couleur, collide=False, shadow=False, name="Tige")
        if disque is not None:
            b.disque((0, y0 + 0.6 * h, 0), rd, 0.4, disque, collide=False, name="Disque")
        b.ball((0, y0 + h + 0.6 * rb, 0), rb, boule, collide=False, name="Boule")
    return y0 + h + 1.6 * rb


def _meridiens(b, C, rd, h, couleur, epaisseur=0.5):
    """3 méridiens de dôme : tranches minces de même centre (0,1 plus grandes que le dôme), tournées de 0, 60,
    120° (STYLE § 3.0). Leur moitié basse doit être cachée comme celle du dôme. 3 pièces."""
    for ang in (0, 60, 120):
        b.ellipsoid(C, (epaisseur, 2 * h + 0.2, 2 * rd + 0.2), couleur, rot=rot_y(ang), collide=False,
                    name="Meridien")


def _rayon_tube(fonction: str, variant: int, hauteur: float, diametre: float, y: float) -> float:
    """Rayon du tube qui entre à la hauteur y dans la tour (retrouvée dans plan.CEINTURE par ses paramètres) ;
    tube fin par défaut."""
    for e in plan.CEINTURE:
        if e["module"] != "tours_rondes" or e["fonction"] != fonction or e["variante"] != variant:
            continue
        p = e["params"]
        if abs(p.get("hauteur", -1) - hauteur) > 1e-6 or abs(p.get("diametre", -1) - diametre) > 1e-6:
            continue
        for t in plan.TUBES:
            if e["id"] in (t["de"], t["vers"]) and abs(t["y"] - y) < 1e-6:
                return float(plan.TUBE_RAYON[t["type"]])
    return float(plan.TUBE_RAYON["fin"])


def _quais(quai, fonction, variant, hauteur, diametre):
    """quai → [(y, demi-hauteur de la bande nue, écart des bagues)]."""
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
        r = _rayon_tube(fonction, variant, hauteur, diametre, y) if r is None else float(r)
        out.append((y, max(6.0, r + 3.0), max(4.5, r + 1.6)))
    return out


def _bagues(b, quais, R_ame, couleur):
    """Deux bagues cyl R(âme + 0,8) · ép 1,2 de part et d'autre de chaque quai (studs sur le dessus)."""
    with b.group("Quai"):
        for (y, _demi, ecart) in quais:
            for sgn in (-1, 1):
                b.cyl((0, y + sgn * ecart, 0), R_ame + 0.8, 1.2, couleur, studs="top", collide=False, name="Bague")


def _hors_quais(y0, y1, quais, marge=0.0):
    """Intervalle [y0, y1] privé des bandes nues des quais (± demi + marge) → liste d'intervalles."""
    morceaux = [(y0, y1)]
    for (yq, demi, _) in quais:
        a, z = yq - demi - marge, yq + demi + marge
        nouveaux = []
        for (u0, u1) in morceaux:
            if z <= u0 or a >= u1:
                nouveaux.append((u0, u1))
                continue
            if a > u0:
                nouveaux.append((u0, a))
            if z < u1:
                nouveaux.append((z, u1))
        morceaux = nouveaux
    return [(u0, u1) for (u0, u1) in morceaux if u1 - u0 > 1.0]


def _bilan(b, i0, D, H, ame, emprise=None, **extra):
    parts = b.parts[i0:]
    lo, hi = bornes(parts)
    w = float(emprise) if emprise else D
    out = {"emprise": (w, w), "hauteur": H, "ame": round(float(ame), 2), "sommet": round(float(hi[1]), 2),
           "pieces": len(parts), "neon": sum(1 for p in parts if p.material == "Neon"),
           "transparentes": sum(1 for p in parts if 0 < p.transparency < 1)}
    out.update(extra)
    return out


# --------------------------------------------------------------------------------------------------------------
# T01 · Tour à galettes
# --------------------------------------------------------------------------------------------------------------

def tour_galettes(b, variant=0, hauteur=200, diametre=54, quai=None, antenne=True, pas=None, epaisseur=None, **_):
    """Pile de galettes (T01) : socle à studs, pied rayé, fût, galettes au pas de 0,2 D (on en ajoute pour remplir
    la hauteur, jamais étirées ; tour élancée, H > 3,5 D : pas 0,28 D et lentilles de 0,18 D, des galettes épaisses
    et bien détachées comme EH5 au lieu d'un ressort ; `pas` / `epaisseur` en fraction de D pour forcer) faites
    d'un bord vertical (cylindre) et d'une lentille bombée (ellipsoïde),
    longues fentes Neon incrustées dans le bord (3 à -50, 0, +50° sur une galette sur deux, 1 au milieu sur les
    autres : colonnes régulières), dernière galette sous la bande d'évents qui porte le dôme à deux yeux et
    3 méridiens, porte, antenne. Tout reste dans le disque D à toute hauteur. ≈ 80-95 pièces (≤ 140), ≈ 25-36 Neon (≤ 40)."""
    i0 = len(b.parts)
    s = schema("tour_galettes", variant)
    H, D = float(hauteur), float(diametre)
    kf = min(D / 40.0, 1.6)
    R_f = 0.34 * D                      # fût (âme)
    R_p = 0.37 * D                      # pied rayé
    R_g = D / 2 - 0.5                   # bord des galettes (les fentes dépassent de 0,45 : Ø ≤ D)
    h_r = 0.075 * D                     # hauteur du bord vertical
    elancee = H > 3.5 * D
    e = (epaisseur if epaisseur is not None else (0.18 if elancee else 0.15)) * D   # lentille, au centre
    pas = (pas if pas is not None else (0.28 if elancee else 0.20)) * D
    R_b = R_f + 1.2                     # bande d'évents, support du dôme (le dôme est plus large que le fût)
    h_d = 0.9 * R_f                     # dôme
    y_d = H - h_d
    rd = R_b - max(0.2, 0.04 * R_b)
    # la moitié basse du dôme (et de ses méridiens, rd + 0,1) dépasse le fût sur z_cache sous sa base
    z_cache = (h_d + 0.1) * math.sqrt(max(0.0, 1 - (R_f / (rd + 0.1)) ** 2))
    h_b = max(2.5, 0.022 * H, z_cache + 0.6)
    y_b0 = y_d - h_b
    y_p1 = 0.12 * H
    quais = _quais(quai, "tour_galettes", variant, H, D)
    demi_g = max(h_r / 2, (e / 2) * math.sqrt(max(0.0, 1 - (R_f / R_g) ** 2)))   # demi-épaisseur au ras du fût

    with b.group("Socle"):
        b.disque((0, 1.5, 0), 0.5 * D, 3.0, s["galettes"], studs="top", name="Socle")
        hp = (y_p1 - 3.0) / 5
        for k in range(5):
            b.cyl((0, 3.0 + hp * (k + 0.5), 0), R_p, hp, s["pied"][k % 2], studs="top" if k == 4 else (),
                  name="Pied")
        _porte(b, R_p, 3.0, PORTE, s["cadres"])
    with b.group("Fut"):
        b.cyl((0, (y_p1 - 0.5 + y_b0 + 0.3) / 2, 0), R_f, y_b0 + 0.3 - (y_p1 - 0.5), s["fut"], name="Fut")
        _bagues(b, quais, R_f, s["cadres"])
    # galettes régulières de y_g0 jusqu'à la dernière, collée sous la bande d'évents
    y_g0 = y_p1 + 0.1 * D
    y_g1 = y_b0 - 0.4 * h_r
    n = max(3, int(round((y_g1 - y_g0) / pas)) + 1)
    p2 = (y_g1 - y_g0) / (n - 1)
    fl, fh = 0.2 * D, 1.2 * kf          # fente : longueur, hauteur
    gal = [k for k in range(n)
           if not any(abs(y_g0 + k * p2 - yq) < demi + demi_g + 0.6 for (yq, demi, _) in quais)]
    # 3 fentes sur une galette sur deux (et la dernière), 1 au milieu de l'avant sur les autres : colonnes
    # régulières ; au-delà de 40 Neon (tour très haute), les fentes seules s'effacent d'abord en bas
    fentes = {k: ((-50, 0, 50) if k % 2 == 0 or k == n - 1 else (0,)) for k in gal}
    for k in gal:
        if sum(len(v) for v in fentes.values()) <= NEON_MAX_GALETTES:
            break
        if len(fentes[k]) == 1:
            fentes[k] = ()
    for k in gal:
        if sum(len(v) for v in fentes.values()) <= NEON_MAX_GALETTES:
            break
        fentes[k] = ()
    with b.group("Galettes"):
        for k in gal:
            y = y_g0 + k * p2
            rg = R_g                    # toutes dans le disque D à toute hauteur (F-T-100 borde la fenêtre de l'œuf)
            b.cyl((0, y, 0), rg, h_r, s["galettes"], studs="top", collide=False, name="Bord")
            b.ellipsoid((0, y, 0), (2 * rg, e, 2 * rg), s["galettes"], collide=False, name="Galette")
            for th in fentes[k]:
                _fente(b, rg, th, y, fl, fh, s["neon"])
    with b.group("Coiffe"):
        b.cyl((0, y_b0 + h_b / 2, 0), R_b, h_b, s["cadres"], studs="top", name="Bande")
        for j in range(7):
            _bloc_mur(b, R_b, -67.5 + 22.5 * j, y_b0 + h_b / 2, 1.6 * kf, min(1.6 * kf, h_b - 1.0), 0.15,
                      shade(s["cadres"], 0.55), collide=False, name="Event")
        dome = b.dome((0, y_d, 0), R_b, h_d, s["dome"], collide=False)
        _meridiens(b, (0, y_d, 0), rd, h_d, shade(s["dome"], 0.86), 0.5 * kf)
        for th in (-22, 22):
            _hublot_ellipsoide(b, (0, y_d, 0), rd, h_d, th, 0.32, 0.19 * R_f, s["cadres"])
        if antenne:
            _antenne(b, H - 0.6, 6.5, s["cadres"], s["pied"][0], r=0.45 * kf, rb=1.0 * kf)
    return _bilan(b, i0, D, H, R_f, galettes=len(gal), dome_dessous_visible=dome.info["dessous_visible"])


# --------------------------------------------------------------------------------------------------------------
# T02 · Champignon sur pilier
# --------------------------------------------------------------------------------------------------------------

def tour_champignon(b, variant=0, hauteur=170, diametre=56, quai=None, **_):
    """Champignon (T02) : plinthe et tambour Ø 0,75 D à porte, rangée de hublots et liseré, gradin à hublots,
    pilier blanc fin à rainures, halo plat flottant, cloche crème sous le bord rayé à 3 couches (Ø D), dôme à
    3 méridiens et 4 hublots. `diametre` = Ø du bord (l'emprise au sol est le tambour). ≈ 75 pièces (≤ 110),
    aucun Neon."""
    i0 = len(b.parts)
    s = schema("tour_champignon", variant)
    H, D = float(hauteur), float(diametre)
    kx, ky = D / 40.0, H / 93.0
    kf = min(kx, 1.6)
    R_pl, R_t, R_g, R_p = 0.3875 * D, 0.375 * D, 0.30 * D, 0.11 * D
    y_t1, y_g1 = 26 * ky, 32 * ky
    rd, h = 0.40 * D, 0.325 * D                 # dôme : rayon, demi-hauteur
    eps = (1.5 * kx, 1.3 * kx, 1.2 * kx)        # bord rayé : 3 couches
    d = sum(eps)
    hc = h - d + 0.8                            # cloche : la plus courte qui cache la moitié basse du dôme
    y_bt = H - h                                # dessus du bord = centre du dôme
    y_bb = y_bt - d                             # dessous du bord = centre de la cloche
    y_pil1 = y_bb - 0.5 * hc                    # haut du pilier (caché dans la cloche)
    quais = _quais(quai, "tour_champignon", variant, H, D)
    y_halo = 0.58 * H
    for (yq, demi, _) in quais:                 # le halo reste hors des bandes nues des quais
        if abs(y_halo - yq) < demi + 2:
            y_halo = yq + demi + 2
    acc = s["halo"]
    with b.group("Base"):
        b.cyl((0, 1.25, 0), R_pl, 2.5, s["base"], studs="top", name="Plinthe")
        b.cyl((0, (2.5 + y_t1) / 2, 0), R_t, y_t1 - 2.5, s["base"], studs="top", name="Tambour")
        lis = s.get("liseré_base", acc)
        ys_lis = (0.8 * y_t1, 0.8 * y_t1 + 2.4 * kf) if "liseré_base" in s else (0.8 * y_t1,)
        for yy in ys_lis:
            b.cyl((0, yy, 0), R_t + 0.15, 1.2 * kf, lis, name="Lisere")
        for th in (-56, -28, 0, 28, 56):
            _hublot_mur(b, R_t, th, 0.5 * y_t1, 2.2 * kf, acc, s["hublots"])
        b.cyl((0, (y_t1 + y_g1) / 2, 0), R_g, y_g1 - y_t1, s.get("liseré_base", s["base"]),
              studs="top", name="Gradin")
        for th in (-60, -30, 0, 30, 60):
            _hublot_mur(b, R_g, th, (y_t1 + y_g1) / 2, 1.8 * kf, acc, s["hublots"])
        _porte(b, R_t, 2.5, PORTE, s["bord"][0])
    with b.group("Pilier"):
        b.cyl((0, (y_g1 - 0.5 + y_pil1) / 2, 0), R_p, y_pil1 - (y_g1 - 0.5), s["pilier"], name="Pilier")
        _bagues(b, quais, R_p, acc)
        # rainures verticales sur l'avant, interrompues aux quais (le tube entre dans un fût nu)
        y_r1 = y_bb - hc * math.sqrt(max(0.0, 1 - (R_p / rd) ** 2)) + 0.6
        for (u0, u1) in _hors_quais(y_g1 + 1.0, y_r1, quais, 0.3):
            for th in (-40, 0, 40):
                _bloc_mur(b, R_p, th, (u0 + u1) / 2, 0.5 * kf, u1 - u0, 0.15, shade(s["pilier"], 0.84),
                          collide=False, name="Rainure")
        b.anneau((0, y_halo, 0), 3.1 * R_p, 1.2 * kx, acc, 24, section="plat", largeur=4.0 * kx,
                 studs="top", collide=False, shadow=True, name="Halo")
    with b.group("Chapeau"):
        b.ellipsoid((0, y_bb, 0), (2 * rd, 2 * hc, 2 * rd), s["cloche"], collide=False, name="Cloche")
        y = y_bb
        for k, (r, ep) in enumerate(zip((0.5 * D, 0.4875 * D, 0.46875 * D), eps)):
            b.disque((0, y + ep / 2, 0), r, ep, s["bord"][k], studs="top", collide=False, name="Bord")
            y += ep
        b.ellipsoid((0, y_bt, 0), (2 * rd, 2 * h, 2 * rd), s["dome"], collide=False, name="Dome")
        _meridiens(b, (0, y_bt, 0), rd, h, shade(s["dome"], 0.86), 0.5 * kf)
        for th in (-75, -25, 25, 75):
            _hublot_ellipsoide(b, (0, y_bt, 0), rd, h, th, 0.3, 2.2 * kf, acc, s["hublots"])
    return _bilan(b, i0, D, H, R_p, emprise_sol=round(2 * R_pl, 2))


# --------------------------------------------------------------------------------------------------------------
# T08 · Tour-soucoupe (ovni sur gobelet)
# --------------------------------------------------------------------------------------------------------------

def _coupole(b, y, z, k, socle, bague, scene):
    """Coupole de verre à miniature (M16) posée en (0, y, z) à l'échelle k. Prend
    assets.mobilier.coupole_miniature s'il existe (écrit en parallèle) et reste dans son gabarit (4-16 pièces,
    1 verre), sinon cette version simple : socle, bague, coupole de verre (moitié basse dans le socle), planète
    opaque à anneau sur une tige. 6 pièces (verre 1)."""
    n0 = len(b.parts)
    try:
        from assets import mobilier  # noqa: PLC0415
        with b.at((0, y, z), group="Coupole"):
            mobilier.coupole_miniature(b, variant=0)
        ajout = b.parts[n0:]
        if not (4 <= len(ajout) <= 16 and sum(1 for p in ajout if 0 < p.transparency < 1) <= 1):
            raise ValueError("coupole hors gabarit")
        return
    except Exception:            # module absent, en cours d'écriture ou hors gabarit : version simple
        del b.parts[n0:]
    with b.at((0, y, z), group="Coupole"):
        b.cyl((0, 1.5 * k, 0), 7 * k, 3 * k, socle, studs="top", name="Socle")
        b.cyl((0, 2.2 * k, 0), 7 * k + 0.2, 0.6 * k, bague, name="Bague")
        b.ellipsoid((0, 3 * k, 0), (13 * k, 12 * k, 13 * k), c("verre"), material="Glass", transparency=0.45,
                    collide=False, name="Coupole")
        b.ball((0, 6.6 * k, 0), 2.2 * k, scene, collide=False, name="Planete")
        b.disque((0, 6.6 * k, 0), 3.3 * k, 0.2 * k, bague, rot=rot_x(23), collide=False, shadow=False,
                 name="AnneauPlanete")
        b.cyl((0, 3 * k + 0.9 * k, 0), 0.35 * k, 1.8 * k, c("blanc_labo"), collide=False, name="Tige")


def _fenetre_arrondie(b, R, theta, y, larg, haut, cadre, vitre):
    """Fenêtre en boîte arrondie sur un mur rond : 2 blocs en croix + 4 cylindres d'angle (faces avant et dos
    décalés de 0,05) et une vitre en saillie. 7 pièces."""
    rr = min(larg, haut) * 0.28
    M = _repere_mur(theta)
    u = _u(theta)
    with b.group("Fenetre"):
        def bloc(w, hh, saillie, dos):
            ep = saillie + dos + _rentre(R, w / 2)
            b.part("block", (w, hh, ep), u * (R + saillie - ep / 2) + _y(y), M, cadre, collide=False, name="Cadre")
        bloc(larg, haut - 2 * rr, 0.40, 0.25)
        bloc(larg - 2 * rr, haut, 0.35, 0.30)
        for sx in (-1, 1):
            for sy in (-1, 1):
                lat = sx * (larg / 2 - rr)
                sa = 0.30 if sy > 0 else 0.27          # coins du haut et du bas : faces jamais dans le même plan
                ep = sa + (0.35 if sy > 0 else 0.42) + _rentre(R, abs(lat) + rr)
                p = u * (R + sa - ep / 2) + _t(theta) * lat + _y(y + sy * (haut / 2 - rr))
                _cyl_axe(b, p, u, ep, rr, cadre, collide=False, name="Coin")
        ep = 0.55 + 0.25 + _rentre(R, larg / 2 - 0.7)
        b.part("block", (larg - 1.4, haut - 1.4, ep), u * (R + 0.55 - ep / 2) + _y(y), M, vitre,
               collide=False, name="Vitre")


def tour_soucoupe(b, variant=0, hauteur=150, diametre=56, soucoupe=None, **_):
    """Tour-soucoupe (T08) : pied évasé à studs, gros corps rythmé de bandes couleur corniche à rainure sombre
    (une tous les 0,55 D, 0,45 D pour le corps haut du coin SO : jamais étiré), fenêtres en boîte arrondie et rangs
    de hublots en alternance entre elles, porte, rebord et large corniche, plateau à coupole de verre (M16), tige,
    gobelet (cloche) sous l'épaisse soucoupe à 10 fentes Neon, dôme, antenne à disque et boule. Soucoupe Ø 1,25 D
    (1,3 D au-delà de H 200 : coin SO). ≈ 70-95 pièces (≤ 100), 10 Neon (≤ 14), 1 verre."""
    i0 = len(b.parts)
    s = schema("tour_soucoupe", variant)
    H, D = float(hauteur), float(diametre)
    kx = D / 56.0
    kf = min(kx, 1.6)
    S = float(soucoupe) if soucoupe else (1.3 if H >= 200 else 1.25) * D
    a = S / 3.0                                 # rayon du dôme et du gobelet
    hd = 0.2333 * S                             # demi-hauteur du dôme
    ts = 0.15 * S                               # épaisseur de la soucoupe
    dd = (ts / 2) * math.sqrt(1 - (a / (S / 2)) ** 2)    # épaisseur de soucoupe au droit du dôme
    hg = hd + 0.6 * dd                          # demi-hauteur du gobelet (hd - dd ≤ hg ≤ hd + dd)
    y_top = H - 4.0
    y_c = y_top - hd
    y_g = y_c - dd
    y_g0 = y_g - hg
    y_t1 = y_g0 + 0.9                           # haut de la tige (dans le gobelet)
    y_pl1 = y_t1 - 8 * kx                       # dessus du plateau
    y_pl0 = y_pl1 - 4 * kx
    y_co0 = y_pl0 - 3 * kx                      # corniche
    y_re0 = y_co0 - 1 * kx                      # rebord
    R_c = 0.446 * D
    with b.group("Pied"):
        b.cyl((0, 1.5, 0), 0.5 * D, 3.0, s["gobelet"], studs="top", name="Pied")
        b.cyl((0, 4.5, 0), 0.473 * D, 3.0, s["corps"], studs="top", name="Pied")
    with b.group("Corps"):
        y_c1 = y_re0 + 0.5
        b.cyl((0, (6.0 - 0.3 + y_c1) / 2, 0), R_c, y_c1 - 5.7, s["corps"], name="Corps")
        # paires de rainures au pas de 0,55 D depuis le haut (0,45 D pour un corps haut, qui en reçoit plus : jamais
        # d'étirement) ; bandes entre elles : fenêtres arrondies et rangs de hublots en alternance
        pas_r = (0.45 if y_re0 > 2.15 * D else 0.55) * D
        hauts = []
        yr = y_re0 - 4.0 * kx
        while yr - 2.6 * kx > 17.0 and len(hauts) < 6:
            hauts.append(yr)
            # bande de la couleur de la corniche (lisible de loin), bordée en haut d'une rainure sombre
            b.cyl((0, yr - 1.3 * kx - 0.3 * kf, 0), R_c + 0.25, 2.6 * kx + 0.6 * kf, s["corniche"], name="Bande")
            b.cyl((0, yr, 0), R_c + 0.4, 0.6 * kf, shade(s["corps"], 0.82), name="Rainure")
            yr -= pas_r
        bandes = [((h1 - 2.6 * kx) + h0) / 2 for h0, h1 in zip(hauts[1:], hauts[:-1])]
        if not bandes:
            bandes = [(6.0 + (hauts[-1] if hauts else y_re0)) / 2 + 4.0]
        for k, yf in enumerate(bandes):
            if k % 2 == 0:
                for th in (-38, 38):
                    _fenetre_arrondie(b, R_c, th, yf, 0.21 * D, min(0.13 * D, pas_r - 8.0), s["corniche"], HUBLOT)
            else:
                for th in (-42, 0, 42):
                    _hublot_mur(b, R_c, th, yf, min(3.4 * kf, 0.3 * (pas_r - 2.6 * kx)), s["corniche"])
        _porte(b, R_c, 6.0, PORTE, s["corniche"])
    with b.group("Corniche"):
        b.cyl((0, (y_re0 + y_co0) / 2, 0), 0.577 * D, y_co0 - y_re0, s["corniche"], studs="top", name="Rebord")
        b.cyl((0, (y_co0 + y_pl0) / 2, 0), 0.571 * D, y_pl0 - y_co0, s["corniche"], studs="top", name="Corniche")
        b.cyl((0, (y_pl0 + y_pl1) / 2, 0), 0.357 * D, y_pl1 - y_pl0, s["plateau"], studs="top", name="Plateau")
        _coupole(b, y_pl1, -0.21 * D, 0.62 * kf, c("blanc_labo"), s["dome"], s["soucoupe"])
        b.cyl((0, (y_pl1 - 0.3 + y_t1) / 2, 0), 0.071 * D, y_t1 - y_pl1 + 0.3, s["gobelet"], name="Tige")
    with b.group("Soucoupe"):
        b.ellipsoid((0, y_g, 0), (2 * a, 2 * hg, 2 * a), s["gobelet"], collide=False, name="Gobelet")
        b.ellipsoid((0, y_c, 0), (S, ts, S), s["soucoupe"], collide=False, name="Soucoupe")
        b.ellipsoid((0, y_c + 0.22 * ts, 0), (0.86 * S, 0.62 * ts, 0.86 * S), shade(s["soucoupe"], 1.22),
                    collide=False, name="Lisere")
        fl, fh, fp = 5.0 * kf, 1.3 * kf, 1.6 * kf
        for k in range(10):
            th = -135 + 30 * k
            ctr = _u(th) * (S / 2 - 0.25 * fp) + _y(y_c)
            b.ellipsoid(ctr, (fl, fh, fp), s["neon"], rot=rot_y(-th), material="Neon", collide=False,
                        shadow=False, name="Fente")
        b.ellipsoid((0, y_c, 0), (2 * a, 2 * hd, 2 * a), s["dome"], collide=False, name="Dome")
        _antenne(b, y_top - 1.0, 8.5 * kf, s["dome"], s["dome"], r=0.6 * kf, rb=1.3 * kf, disque=s["dome"],
                 rd=2.0 * kf)
    return _bilan(b, i0, D, H, R_c, soucoupe=round(S, 1), y_soucoupe=round(y_c, 1))


# --------------------------------------------------------------------------------------------------------------
# T03 · Cône rayé à tête-boule
# --------------------------------------------------------------------------------------------------------------

def tour_tete_boule(b, variant=0, hauteur=150, diametre=42, **_):
    """Cône rayé à tête-boule (T03) : plinthe, tambour à porte, rangs de hublots et bagues (un rang de plus pour
    les tours hautes), balcon à studs (poteaux, bande vitrée opaque, main courante), grand cône à 12-14 rayures
    égales, col, halo octogonal épais plus large que le cône (variante 3 : soucoupe de 3 disques), tête sphérique
    (0,7 × le Ø du cône) à menton et deux yeux. ≈ 70-80 pièces (≤ 100), aucun Neon."""
    i0 = len(b.parts)
    s = schema("tour_tete_boule", variant)
    H, D = float(hauteur), float(diametre)
    kx, ky = D / 30.0, H / 100.0
    kf = min(kx, 1.6)
    R_b = 0.48 * D
    R_t = 0.30 * D                              # tête
    y_t = H - R_t
    y_halo = y_t - R_t                          # niveau du bas de la tête
    y_b1 = 34 * ky                              # haut du tambour
    e_bal = 1.2 * kf
    h_bal = 4.5 * kf
    y_bal1 = y_b1 + e_bal                       # dessus du balcon
    y_mc1 = y_bal1 + h_bal + 0.6 * kf           # dessus de la main courante
    y_c1 = y_halo - 6 * ky                      # haut du cône
    n_et = 12 if H < 180 else 14
    haute = H >= 180
    with b.group("Base"):
        b.cyl((0, 0.6, 0), 0.5 * D, 1.2, s["base"], studs="top", name="Plinthe")
        b.cyl((0, (1.2 + y_b1) / 2, 0), R_b, y_b1 - 1.2, s["base"], name="Tambour")
        _porte(b, R_b, 1.2, s["porte"], s["balcon"])
        f = 2.0 * kf
        rangs = ((0.36, (-36, 36)), (0.62, (-58, -20, 20, 58)), (0.85, (-36, 0, 36))) if haute else \
            ((0.42, (-38, 38)), (0.74, (-62, 0, 62)))
        for fy, ths in rangs:
            for th in ths:
                _hublot_mur(b, R_b, th, y_b1 * fy, f, s["balcon"])
        for fy in ((0.49, 0.735) if haute else (0.58,)):
            b.cyl((0, y_b1 * fy, 0), R_b + 0.2, 1.4 * kf, s["balcon"], name="Bague")
    with b.group("Balcon"):
        b.disque((0, y_b1 + e_bal / 2, 0), 0.533 * D, e_bal, s["balcon"], studs="top", name="Balcon")
        b.cyl((0, y_bal1 + h_bal / 2, 0), 0.487 * D, h_bal, HUBLOT, name="Vitrage")
        n_po = 16 if D >= 36 else 12
        for k in range(n_po):
            th = 360.0 * k / n_po
            p = _u(th) * (0.5 * D + 0.1) + _y(y_bal1 + h_bal / 2)
            b.cyl(p, 0.4 * kf, h_bal, s["balcon"], collide=False, name="Poteau")
        b.disque((0, y_bal1 + h_bal + 0.3 * kf, 0), 0.52 * D, 0.6 * kf, s["balcon"], studs="top",
                 name="MainCourante")
    with b.group("Cone"):
        b.cone_etage((0, y_mc1 - 0.05, 0), 0.433 * D, 0.1 * D, y_c1 - y_mc1 + 0.05, list(s["cone"]),
                     etages=n_et, collide=False, name="Cone")
        b.cyl((0, (y_c1 - 1.0 + y_t) / 2, 0), 0.0833 * D, y_t - y_c1 + 1.0, s["cone"][0], collide=False,
              name="Col")
    with b.group("Tete"):
        if "soucoupe" in s:     # variante « anime » : soucoupe de 3 disques à la place du halo
            for k, (rr, coul) in enumerate(zip((0.62 * D, 0.54 * D, 0.45 * D), s["soucoupe"])):
                b.disque((0, y_halo - 2.2 * kf + k * 1.1 * kf, 0), rr, 1.1 * kf, coul, studs="top",
                         collide=False, name="Soucoupe")
        else:
            b.anneau((0, y_halo, 0), 0.55 * D, 1.5 * kf, s["halo"], 8, section="plat", largeur=3.4 * kx,
                     studs="top", collide=False, name="Halo")
        b.ball((0, y_t, 0), R_t, s["tete"], collide=False, name="Tete")
        b.ellipsoid((0, y_t - 0.1333 * D, 0), (0.6133 * D, 0.3667 * D, 0.6133 * D), s["menton"], collide=False,
                    name="Menton")
        for th in (-24, 24):
            _hublot_ellipsoide(b, (0, y_t, 0), R_t, R_t, th, 0.12, 2.2 * kf, s["menton"])
    return _bilan(b, i0, D, H, R_b, etages=n_et)


# --------------------------------------------------------------------------------------------------------------
# T07 · Tour en pneus (repère d'angle)
# --------------------------------------------------------------------------------------------------------------

def tour_pneus(b, variant=0, hauteur=240, diametre=72, **_):
    """Tour en pneus (T07), version haute : socle blanc à porte et hublots, âme sombre continue, 9 pneus
    (épaisseur 10 kx, Ø de D à 0,9 D) séparés de bandes alternées (vitrée à meneaux / hublots allumés sur l'âme,
    moitié avant), dôme à hublots et méridiens, flèche dorée, halo Neon incliné, 3 grands anneaux verticaux
    accrochés aux flancs. ≈ 170 pièces (≤ 220), ≈ 36 Neon (≤ 40)."""
    i0 = len(b.parts)
    s = schema("tour_pneus", variant)
    H, D = float(hauteur), float(diametre)
    kx = D / 62.0
    kf = min(kx, 1.6)
    pneus = s["pneus"] if isinstance(s["pneus"], tuple) else (s["pneus"],)
    R_s, R_pl, R_a, R_v = 0.42 * D, 0.427 * D, 0.403 * D, 0.435 * D
    e = 10.0 * kx
    h_s = max(22.0 * kx, 0.15 * H)
    h_dome = 16.0 * kx
    y_dtop = H - 4.0
    y_d = y_dtop - h_dome
    n = 9
    y_0 = h_s + 0.45 * e
    y_n = y_d - 0.2 * e
    pas = (y_n - y_0) / (n - 1)
    ys = [y_0 + k * pas for k in range(n)]
    diam = [D * (1 - 0.1 * k / (n - 1)) for k in range(n)]
    ame = shade(pneus[0], 0.62)
    with b.group("Socle"):
        b.cyl((0, 1.0, 0), R_pl, 2.0, s["socle"], studs="top", name="Plinthe")
        b.cyl((0, (2.0 + h_s) / 2, 0), R_s, h_s - 2.0, s["socle"], studs="top", name="Socle")
        _porte(b, R_s, 2.0, PORTE, s["anneaux"])
        for th in (-28, 28):
            _hublot_mur(b, R_s, th, 0.55 * h_s, 3.6 * kf, s["anneaux"], s["bandes"])
    with b.group("Pneus"):
        b.cyl((0, (h_s - 0.4 + y_d) / 2, 0), R_a, y_d - (h_s - 0.4), ame, name="Ame")
        for k in range(n):
            b.ellipsoid((0, ys[k], 0), (diam[k], e, diam[k]), pneus[k % len(pneus)], collide=False, name="Pneu")

        def demi(j, r):     # demi-épaisseur du pneu j au rayon r
            return (e / 2) * math.sqrt(max(0.0, 1 - (r / (diam[j] / 2)) ** 2))
        for k in range(n - 1):
            if k % 2 == 0:      # bande vitrée (opaque) à meneaux
                y0 = ys[k] + demi(k, R_v) + 0.3
                y1 = ys[k + 1] - demi(k + 1, R_v) - 0.3
                b.cyl((0, (y0 + y1) / 2, 0), R_v, y1 - y0, s["bandes"], name="BandeVitree")
                for j in range(7):
                    _bloc_mur(b, R_v, -67.5 + 22.5 * j, (y0 + y1) / 2, 1.0 * kf, y1 - y0 - 0.1, 0.3,
                              pneus[0], collide=False, name="Meneau")
            else:               # hublots allumés sur l'âme sombre
                ym = (ys[k] + ys[k + 1]) / 2
                for j in range(5):
                    _hublot_mur(b, R_a, -60 + 30 * j, ym, 2.4 * kf, s["bandes"], s["halo"], allume=True)
    with b.group("Coiffe"):
        rd = R_a - max(0.2, 0.04 * R_a)
        b.dome((0, y_d, 0), R_a, h_dome, s["dome"], collide=False)
        _meridiens(b, (0, y_d, 0), rd, h_dome, shade(s["dome"], 0.86), 0.5 * kf)
        for th, sh in ((-50, 0.28), (-17, 0.28), (17, 0.28), (50, 0.28), (-33, 0.62), (33, 0.62)):
            _hublot_ellipsoide(b, (0, y_d, 0), rd, h_dome, th, sh, 2.4 * kf, s["anneaux"])
        h_f = 13.0
        b.cone_etage((0, y_dtop - 1.5, 0), 5.0 * kf, 0.9 * kf, h_f, [s["fleche"], shade(s["fleche"], 0.88)],
                     etages=5, collide=False, name="Fleche")
        b.ball((0, y_dtop - 1.5 + h_f + 0.6 * kf, 0), 1.2 * kf, s["fleche"], collide=False, name="Pointe")
        b.anneau((0, y_dtop + 6.0, 0), 15.0 * kx, 0.8 * kf, s["halo"], 16, rot=rot_x(8), material="Neon",
                 collide=False, shadow=False, name="Halo")
    with b.group("Anneaux"):
        rr, ep_a = 0.12 * D, 2.0 * kx
        for th, k in ((-74, 2), (70, 4), (24, 6)):
            r_k = diam[k] / 2
            ctr = _u(th) * (r_k + rr - 1.2 * kx) + _y(ys[k])
            # anneau vertical dans le plan radial (normale = tangente horizontale), qui mord le pneu de 1,2 kx
            b.anneau(ctr, rr, ep_a, s["anneaux"], 12, axe=_t(th), collide=False, name="Anneau")
    return _bilan(b, i0, D, H, R_a, pas_pneus=round(pas, 2))


# --------------------------------------------------------------------------------------------------------------
# T10 · Champignon géant à colonne dégradée et ruban (repère d'angle NE)
# --------------------------------------------------------------------------------------------------------------

def tour_ruban(b, variant=0, hauteur=250, diametre=72, tours_ruban=2.0, **_):
    """Champignon géant (T10) : plinthe Ø D, tambour à porte et hublots, bande de fenêtres à meneaux, corniche à
    studs, pied de colonne, colonne de 10 cylindres dégradés (bas `colonne[0]` → haut `colonne[1]`), collier sous
    le chapeau, chapeau géant (≤ 120) à dessous plus sombre et 8 fenêtres Neon, ruban continu en hélice (2 tours
    de 24 segments, ses deux bouts plongent dans la colonne), épi jusqu'à H. ≈ 100 pièces (≤ 200), 8 Neon
    (≤ 12)."""
    i0 = len(b.parts)
    s = schema("tour_ruban", variant)
    H, D = float(hauteur), float(diametre)
    kx, ky = D / 40.0, H / 125.0
    kf = min(kx, 1.6)
    R_t = 0.5 * D - 0.6                         # tambour (hublots et porte restent dans le disque D)
    y_t1 = 20 * ky                              # haut du tambour
    y_v1 = 27 * ky                              # haut de la bande de fenêtres
    y_k1 = y_v1 + 2.5 * kx                      # haut de la corniche
    y_p1 = y_k1 + 6.5 * ky                      # haut du pied de colonne
    Sx = min(1.6 * D, 120.0)                    # chapeau
    Sy = 36.0 * min(1.0, kx / 1.8)
    y_ch = 0.89 * H
    y_col1 = y_ch - 0.25 * Sy                   # haut de la colonne (dans le chapeau)
    n_col = 10
    h_col = (y_col1 - y_p1) / n_col
    c_bas, c_haut = s["colonne"]                # EH3 : lavande en bas, citron sous le chapeau
    Sx2, Sy2 = 0.949 * Sx, 0.75 * Sy            # dessous plus sombre
    y_ds = y_ch - Sy / 6

    def dessous(r):     # y du dessous du chapeau au rayon r
        return y_ds - (Sy2 / 2) * math.sqrt(max(0.0, 1 - (r / (Sx2 / 2)) ** 2))
    with b.group("Base"):
        b.cyl((0, 0.5, 0), 0.5 * D, 1.0, c("blanc_labo"), studs="top", name="Plinthe")
        b.cyl((0, (1.0 + y_t1) / 2, 0), R_t, y_t1 - 1.0, s["base"], studs="top", name="Tambour")
        _porte(b, R_t, 1.0, PORTE, s["ruban"] if s["ruban"] != s["base"] else c("blanc_labo"))
        for th in (-62, -34, 34, 62):
            _hublot_mur(b, R_t, th, y_t1 * 0.48, 3.0 * kf, c("blanc_labo"), s["vitres"])
        R_v = 0.475 * D
        b.cyl((0, (y_t1 - 0.3 + y_v1) / 2, 0), R_v, y_v1 - y_t1 + 0.3, s["vitres"], name="BandeFenetres")
        for j in range(9):
            _bloc_mur(b, R_v, -80 + 20 * j, (y_t1 + y_v1) / 2, 1.2 * kf, y_v1 - y_t1 - 0.2, 0.35, s["base"],
                      collide=False, name="Meneau")
        b.cyl((0, (y_v1 + y_k1) / 2, 0), 0.575 * D, y_k1 - y_v1, c("blanc_labo"), studs="top", name="Corniche")
        b.cyl((0, (y_k1 + y_p1) / 2, 0), 0.275 * D, y_p1 - y_k1, s["base"], studs="top", name="PiedColonne")
    rcol = []
    with b.group("Colonne"):
        for k in range(n_col):
            r = (0.225 - (0.225 - 0.1625) * k / (n_col - 1)) * D
            rcol.append(r)
            y0 = y_p1 + k * h_col
            b.cyl((0, y0 + h_col / 2, 0), r, h_col + (0.01 if k < n_col - 1 else 0.0),
                  mix(c_bas, c_haut, k / (n_col - 1)), studs="top" if k < n_col - 1 else (), name="Colonne")
        r_col = 0.1875 * D                      # collier juste sous le chapeau (son haut dans le dessous)
        y_col_haut = dessous(r_col) + 0.6
        b.cyl((0, y_col_haut - 1.5 * ky, 0), r_col, 3.0 * ky, s["ruban"], name="Collier")
    with b.group("Chapeau"):
        b.ellipsoid((0, y_ch, 0), (Sx, Sy, Sx), s["chapeau"], collide=False, name="Chapeau")
        b.ellipsoid((0, y_ds, 0), (Sx2, Sy2, Sx2), shade(s["chapeau"], 0.75), collide=False, name="Dessous")
        # 8 fenêtres Neon sur le bord, un peu sous l'équateur, sur l'avant ± 105°
        yy = y_ch - 0.12 * Sy
        for j in range(8):
            th = -105 + 30 * j
            p, nn = _sur_ellipsoide((0, y_ch, 0), Sx / 2, Sy / 2, th, (yy - y_ch) / (Sy / 2))
            M = repere_direction(_t(th), haut=(0, 1, 0))
            b.part("block", (4.0, 2.0, 0.8), p + nn * 0.05, M, s["neon"], material="Neon", collide=False,
                   shadow=False, name="Fenetre")
        y_top = y_ch + Sy / 2
        pr = 0.9 * kf
        b.cone_etage((0, y_top - 1.2, 0), 2.6 * kf, 0.7 * kf, max(2.0, H - pr - (y_top - 1.2)),
                     [s["ruban"], c("blanc_labo")], etages=3, pointe=(s["ruban"], pr), collide=False, name="Epi")
    with b.group("Ruban"):
        n_seg = int(round(24 * tours_ruban))
        y_r0, y_r1 = y_p1 + 0.12 * (y_col1 - y_p1), y_col1 - 0.16 * (y_col1 - y_p1)
        larg, ep = 3.0 * kx, 0.6 * kx

        def rayon(y, g):
            f = min(1.0, max(0.0, (y - y_p1) / (y_col1 - y_p1)))
            return (0.225 - (0.225 - 0.1625) * f) * D + ep / 2 - 0.3 + (2.6 * kf + 0.3) * g
        pts = []
        for i in range(n_seg + 1):
            ph = 360.0 * tours_ruban * i / n_seg
            y = y_r0 + (y_r1 - y_r0) * i / n_seg
            g = min(1.0, i / 3.0, (n_seg - i) / 3.0)      # les deux bouts plongent dans la colonne : rien ne flotte
            pts.append(_u(ph) * rayon(y, g) + _y(y))
        for i in range(n_seg):
            p0, p1 = pts[i], pts[i + 1]
            dd = p1 - p0
            ext = dd / float(np.linalg.norm(dd)) * 0.25
            b.bloc_entre(p0 - ext, p1 + ext, ep, larg, s["ruban"], collide=False, name="Ruban")
    return _bilan(b, i0, D, H, rcol[-1], chapeau=round(Sx, 1))


# --------------------------------------------------------------------------------------------------------------
# T13 · Bulbe à cheminée (usine à nuages)
# --------------------------------------------------------------------------------------------------------------

def tour_bulbe(b, variant=0, hauteur=115, diametre=46, **_):
    """Bulbe en oignon (T13), version haute : plinthe, tambour à porte (R 0,32 D) jusqu'à 0,3 H, bague de col,
    bulbe 1,1 D × 0,5 H enfoncé de 2 (il ne dépasse le disque D qu'au-dessus de y 40) à 3 côtes, bague de taille,
    4 hublots, pointe d'oignon (ellipsoïde élancé qui sort du haut du bulbe : col concave), flèche d'or et boule
    (0,96 H), cheminée à x = 0,3 D à bec sombre, 6 boules de fumée qui grossissent et pâlissent en dérivant avec le
    vent (jusqu'à ≈ 1,3 H). ≈ 40 pièces (≤ 60), 6 transparentes."""
    i0 = len(b.parts)
    s = schema("tour_bulbe", variant)
    H, D = float(hauteur), float(diametre)
    kx = D / 40.0
    kf = min(kx, 1.6)
    R_t = 0.32 * D
    y_t1 = 0.3 * H
    a, hb = 0.55 * D, 0.25 * H
    y_bc = y_t1 - 2.0 + hb                      # centre du bulbe (enfoncé de 2 dans le tambour)
    with b.group("Tambour"):
        b.cyl((0, 0.5, 0), R_t + 0.8, 1.0, s["bagues"], studs="top", name="Plinthe")
        b.cyl((0, (1.0 + y_t1) / 2, 0), R_t, y_t1 - 1.0, s["tambour"], studs="top", name="Tambour")
        _porte(b, R_t, 1.0, PORTE, s["bagues"])
        for th in (-50, 50):
            _hublot_mur(b, R_t, th, 0.62 * y_t1, 2.2 * kf, s["bagues"])
        b.cyl((0, y_t1 + 0.75 * kf, 0), 0.275 * D, 1.5 * kf, s["bagues"], studs="top", name="BagueCol")
    with b.group("Bulbe"):
        b.ellipsoid((0, y_bc, 0), (2 * a, 2 * hb, 2 * a), s["bulbe"], collide=False, name="Bulbe")
        _meridiens(b, (0, y_bc, 0), a, hb, shade(s["bulbe"], 0.76), 0.6 * kf)
        b.cyl((0, y_bc, 0), a + 0.3, 1.2 * kf, s["bagues"], name="BagueTaille")
        for th in (-90, -30, 30, 90):
            _hublot_ellipsoide(b, (0, y_bc, 0), a, hb, th, 0.3, 2.5 * kf, s["bagues"])
        # pointe d'oignon : ellipsoïde élancé centré dans le haut du bulbe (sa moitié basse y reste cachée) ; il
        # en sort tout près du sommet du bulbe, d'où le col concave de l'oignon
        rt, y_tc, y_ap = 0.3 * a, y_bc + 0.9 * hb, 0.92 * H
        b.ellipsoid((0, y_tc, 0), (2 * rt, 2 * (y_ap - y_tc), 2 * rt), s["bulbe"], collide=False, name="Pointe")
        rb = max(0.8, 0.9 * kx)
        y_p1 = 0.96 * H
        b.cone_etage((0, y_ap - 0.6, 0), 0.9 * kf, 0.3, y_p1 - rb - (y_ap - 0.6), [s["bagues"], shade(s["bagues"], 0.85)],
                     etages=3, collide=False, name="Fleche")
        b.ball((0, y_p1 - 0.2 * rb, 0), rb, s["bagues"], collide=False, name="Boule")
    with b.group("Cheminee"):
        xc, rc = 0.3 * D, 0.06 * D
        y_c0, y_c1 = 0.6 * H, 0.9 * H
        b.cyl((xc, (y_c0 + y_c1) / 2, 0), rc, y_c1 - y_c0, s["tambour"], collide=False, name="Cheminee")
        b.cyl((xc, y_c1 - 0.4, 0), rc + 0.7, 1.2, s["bagues"], studs="top", collide=False, name="Rebord")
        b.cyl((xc, y_c1 + 0.08, 0), max(0.3, rc - 0.35), 0.2, shade(s["tambour"], 0.35), collide=False,
              shadow=False, name="Bec")
        r0, r1 = 2.0 * kf, 7.5 * kf
        y, r_prec = y_c1, 0.0
        for k in range(6):
            r = r0 + (r1 - r0) * (k / 5) ** 1.1
            y = y_c1 + 0.55 * r if k == 0 else y + 0.62 * (r + r_prec)
            x = xc + 2.0 * kf * k ** 1.35          # le vent pousse la fumée vers +X et un peu vers l'arrière
            b.ball((x, y, 0.8 * k * kf), r, s["fumee"], transparency=0.25 + 0.04 * k, collide=False, shadow=False,
                   name="Fumee")
            r_prec = r
    return _bilan(b, i0, D, H, R_t)


# --------------------------------------------------------------------------------------------------------------
# T11 · Fusée (rang 1)
# --------------------------------------------------------------------------------------------------------------

def _aileron(b, theta, r0, r1, y0, h, ep, couleur, **kw):
    """Aileron en coin dans le plan radial : face pleine contre le corps (r0), pointe en bas à l'extérieur (r1)."""
    u = _u(theta)
    z = -u                                       # +Z local vers l'axe : la pente descend vers l'extérieur
    yv = np.array([0.0, 1.0, 0.0])
    M = np.column_stack([np.cross(yv, z), yv, z])
    ctr = u * (r0 + r1) / 2 + _y(y0 + h / 2)
    return b.part("wedge", (ep, h, r1 - r0), ctr, M, couleur, **kw)


def tour_fusee(b, variant=0, hauteur=55, diametre=20, type="blanche", **_):
    """Fusée (T11) sur socle rond à studs (R D/2 + 1, emprise D + 2) avec une petite porte au pied.
    « blanche » (recette A) : jupe, corps en cigare (grand ellipsoïde dont le bas reste dans la jupe), 2 bandes,
    hublot emblème, flèche et feu Neon, 3 ailerons. « capsule » (recette B) : plinthe, corps à rainures et
    hublots, bande et filet, ogive pointue à 2 rangs de hublots (sa moitié basse reste dans le corps, jamais sous le
    sol), sommet et feu Neon, 4 ailerons. Fusée haute (70-100) : l'ogive garde au plus 1,25 D de demi-hauteur et
    le corps s'allonge avec 2 rangs de hublots et une bague de plus (capsule) ; la blanche reçoit un hublot et une
    bague de plus au-delà de 70. ≤ 50 pièces, 1 Neon."""
    i0 = len(b.parts)
    s = schema("tour_fusee", variant)
    H, D = float(hauteur), float(diametre)
    kf = min(D / 18.0, 1.6)
    with b.group("Socle"):
        b.disque((0, 0.5, 0), D / 2 + 1, 1.0, s["bandes"], studs="top", name="Socle")
    if type == "capsule":
        R_c = 0.42 * D
        y_o = (H - 3.0 * kf + 1.0) / 2          # centre de l'ogive : sa moitié basse descend jusqu'à y = 1
        ho_max = 1.25 * D                       # fusée haute : l'ogive garde ses proportions, le corps s'allonge
        if H - 3.0 * kf - y_o > ho_max:
            y_o = H - 3.0 * kf - ho_max
        y_b1 = y_o - 2.5 * kf                   # haut du corps
        ro, ho = R_c - 0.5, H - 3.0 * kf - y_o
        haut_ = y_b1 > 34.0
        with b.group("Corps"):
            b.cyl((0, (0.9 + y_b1) / 2, 0), R_c, y_b1 - 0.9, s["corps"], name="Corps")
            b.cyl((0, (0.92 + 2.0) / 2, 0), R_c + 0.5, 1.08, s["bandes"], studs="top", name="Plinthe")
            for th in (-150, -110, 110, 150, 180):
                _bloc_mur(b, R_c, th, (2.6 + y_b1) / 2, 0.6 * kf, y_b1 - 3.2, 0.25, shade(s["corps"], 0.82),
                          collide=False, name="Rainure")
            y_h = y_b1 - 7.0 if haut_ else 0.62 * y_b1 + 1.0
            for th in (-22, 22, -68, 68):
                _hublot_mur(b, R_c, th, y_h, 1.9 * kf, s["cadres"])
            if haut_:                           # corps long : 2 rangs de 2 hublots plus bas et une bague
                for k in (1, 2):
                    yk = y_h - k * (y_h - 12.0) / 3
                    for th in (-45, 45):
                        _hublot_mur(b, R_c, th, yk, 1.6 * kf, s["cadres"])
                b.cyl((0, (y_h + y_h - (y_h - 12.0) / 3) / 2, 0), R_c + 0.2, 1.2 * kf, s["bandes"],
                      collide=False, name="Bande")
            _porte(b, R_c, 2.0, PORTE, s["cadres"], largeur=4.0, haut=5.5)
            b.cyl((0, y_b1 + 1.25 * kf, 0), R_c + 0.2, 2.5 * kf, s["bandes"], studs="top", name="Bande")
            b.cyl((0, y_b1 + 1.25 * kf, 0), R_c + 0.35, 0.6 * kf, s["cadres"], name="Filet")
        with b.group("Ogive"):
            b.ellipsoid((0, y_o, 0), (2 * ro, 2 * ho, 2 * ro), s["corps"], collide=False, name="Ogive")
            for th, sh in ((-40, 0.22), (0, 0.22), (40, 0.22), (-20, 0.5), (20, 0.5)):
                _hublot_ellipsoide(b, (0, y_o, 0), ro, ho, th, sh, 1.7 * kf, s["cadres"])
            b.cyl((0, y_o + ho + 0.6 * kf, 0), 1.0 * kf, 2.0 * kf, s["bandes"], collide=False, name="Sommet")
            b.ball((0, y_o + ho + 2.4 * kf, 0), 1.0 * kf, s["cadres"], material="Neon", collide=False,
                   shadow=False, name="Feu")
        with b.group("Ailerons"):
            for th in (45, 135, 225, 315):
                _aileron(b, th, R_c - 0.4, D / 2 + 0.8, 0.95, 0.33 * H, 1.0 * kf, s["ailerons"], name="Aileron")
        ame = R_c
    else:
        R_e = 0.36 * D                          # corps en cigare (grand ellipsoïde posé dans la jupe)
        h_tip = 0.1 * H
        y_e0 = 0.5                              # bas de l'ellipsoïde, dans le socle
        h_e = (H - h_tip - y_e0) / 2
        y_e = y_e0 + h_e

        def r_corps(y):
            t = (y - y_e) / h_e
            return R_e * math.sqrt(max(0.0, 1 - t * t))
        y_j = max(0.18 * H, 10.5)               # haut de la jupe (elle cache le bas arrondi du corps)
        R_j = r_corps(y_j) + 0.3
        with b.group("Corps"):
            b.cyl((0, (0.75 + y_j) / 2, 0), R_j, y_j - 0.75, s["bandes"], studs="top", name="Jupe")
            b.ellipsoid((0, y_e, 0), (2 * R_e, 2 * h_e, 2 * R_e), s["corps"], collide=False, name="Corps")
            for yb, hb in ((y_j + 0.06 * H, 0.05 * H), (y_e + 0.42 * h_e, 0.035 * H)):
                # bague : un peu plus large que le corps sur toute sa hauteur
                r_max = R_e if yb - hb / 2 <= y_e <= yb + hb / 2 else max(r_corps(yb - hb / 2), r_corps(yb + hb / 2))
                b.cyl((0, yb, 0), r_max + 0.15, hb, s["bandes"], name="Bande")
            _hublot_ellipsoide(b, (0, y_e, 0), R_e, h_e, 0, (0.4 * H - y_e) / h_e, 2.2 * kf, s["cadres"])
            if H > 70:                          # fusée haute : un hublot et une bague de plus (pas d'aplat géant)
                _hublot_ellipsoide(b, (0, y_e, 0), R_e, h_e, 0, (0.53 * H - y_e) / h_e, 1.8 * kf, s["cadres"])
                yb3, hb3 = 0.78 * H, 0.03 * H
                b.cyl((0, yb3, 0), max(r_corps(yb3 - hb3 / 2), r_corps(yb3 + hb3 / 2)) + 0.15, hb3, s["bandes"],
                      name="Bande")
            _porte(b, R_j, 1.0, PORTE, s["corps"], largeur=4.0, haut=5.5)     # cadre clair sur la jupe vive
        with b.group("Pointe"):
            y_s = y_e + h_e - 0.35
            b.cone_etage((0, y_s, 0), 0.9 * kf, 0.25, H - 0.9 * kf - y_s, s["bandes"], etages=3, collide=False,
                         name="Fleche")
            b.ball((0, H - 0.5 * kf, 0), 0.5 * kf, s["cadres"], material="Neon", collide=False, shadow=False,
                   name="Feu")
        with b.group("Ailerons"):
            for th in (60, 180, 300):
                _aileron(b, th, R_j - 0.4, D / 2, 0.95, 0.3 * H, 1.0 * kf, s["ailerons"], name="Aileron")
        ame = R_j
    return _bilan(b, i0, D, H, ame, emprise=D + 2, type=type)


# --------------------------------------------------------------------------------------------------------------
# T16 · Tambour à fenêtres / cylindre à hublots (rang 1)
# --------------------------------------------------------------------------------------------------------------

def tour_hublots(b, variant=0, hauteur=42, diametre=30, **_):
    """Tambour (T16) : socle à studs, tambour à porte en arche, 3 bandes vitrées opaques à meneaux (variantes 0
    et 2) ou 3 rangs de 5 hublots à cadres épais (variantes 1 et 3, rang du haut allumé), bague, toit à studs
    débordant, petit dôme et épi. Tambour haut (hauteur > ≈ 48, front de rue relevé à 70-100) : rangs ajoutés au
    pas d'environ 10,5 (7 au plus ; bandes à 5 meneaux, ou hublots en quinconce 3 / 2) et une bague au milieu,
    au lieu d'étirer 3 rangs. ≤ 60 pièces, ≤ 6 Neon."""
    i0 = len(b.parts)
    s = schema("tour_hublots", variant)
    H, D = float(hauteur), float(diametre)
    kx = D / 40.0
    kf = min(max(kx, 0.75), 1.6)
    R_t = D / 2 - 1.0
    h_dome = 6.0 * max(kx, 0.7)
    e_toit = 1.5
    y_toit1 = H - h_dome
    y_toit0 = y_toit1 - e_toit
    with b.group("Corps"):
        b.disque((0, 0.4, 0), D / 2, 0.8, s["toit"], studs="top", name="Socle")
        b.cyl((0, (0.8 + y_toit0 + 0.3) / 2, 0), R_t, y_toit0 + 0.3 - 0.8, s["corps"], name="Tambour")
        _porte(b, R_t, 0.8, PORTE, s["dome"])
        y_lo, y_hi = 12.6, y_toit0 - 3.6
        # tambour haut (front de rue relevé) : on ajoute des rangs au pas d'environ 10,5 au lieu d'étirer les
        # 3 rangs (7 au plus, ≤ 60 pièces) ; une bague coupe le fût entre les deux rangs du milieu
        nr = 3 if y_hi - y_lo <= 26.0 else min(7, max(3, int(round((y_hi - y_lo) / 10.5)) + 1))
        rangs = [y_lo + (y_hi - y_lo) * k / (nr - 1) for k in range(nr)]
        haut_ = nr > 3
        if haut_:
            y_bg = (rangs[nr // 2 - 1] + rangs[nr // 2]) / 2
            b.cyl((0, y_bg, 0), R_t + 0.3, 1.0, s["dome"], collide=False, name="Bague")
        if variant % 2 == 0:            # bandes vitrées à meneaux
            hb = min(4.6, 0.36 * (rangs[1] - rangs[0]) + 1.0)
            angs = [-60 + 30 * j for j in range(5)] if haut_ else [-67.5 + 22.5 * j for j in range(7)]
            for y in rangs:
                b.cyl((0, y, 0), R_t + 0.2, hb, s["vitres"], name="BandeVitree")
                for a in angs:
                    _bloc_mur(b, R_t + 0.2, a, y, 0.8 * kf, hb - 0.1, 0.25, s["corps"],
                              collide=False, name="Meneau")
        else:                           # rangs de hublots à cadres épais, rang du haut allumé
            f = min(2.3, 0.3 * (rangs[1] - rangs[0]))
            # pas angulaire : au moins 1 stud entre deux cadres (un tambour étroit n'en reçoit que 3 par rang)
            pas_h = max(30.0, math.degrees(2 * math.asin(min(1.0, (f + 0.5) / R_t))))
            ths = (-60, -30, 0, 30, 60) if pas_h <= 30.0 else (-pas_h, 0.0, pas_h)
            st = max(40.0, pas_h)       # tambour haut : rangs en quinconce de 3 et 2 hublots
            for k, y in enumerate(rangs):
                if haut_:
                    ths = (-st, 0.0, st) if (nr - 1 - k) % 2 == 0 else (-st / 2, st / 2)
                for th in ths:
                    _hublot_mur(b, R_t, th, y, f, s["vitres"], c("neon_blanc") if k == nr - 1 else HUBLOT,
                                allume=(k == nr - 1), bord=0.42 * f)
    with b.group("Toit"):
        b.cyl((0, y_toit0 - 0.6, 0), R_t + 0.25, 1.2, s["dome"], name="Bague")
        b.disque((0, (y_toit0 + y_toit1) / 2, 0), D / 2, e_toit, s["toit"], studs="top", name="Toit")
        dome = b.dome((0, y_toit1, 0), 0.42 * R_t, h_dome, s["dome"], collide=False)
        _antenne(b, H - 0.4, 2.6, s["toit"], s["dome"], r=0.3, rb=0.7)
    return _bilan(b, i0, D, H, R_t, dome_dessous_visible=dome.info["dessous_visible"])
