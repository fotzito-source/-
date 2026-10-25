"""Végétation et pièces de terrain de la zone 4 (style « stud ») : campagne terrestre, terres de combat,
planète extraterrestre.

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :
- palmier(hauteur=14) : tronc courbe en tronçons vrillés (bagues sombres), couronne de 5 à 8 palmes coudées
    (montée, palier, pointe tombante en coin), cœur et pousse, noix de coco brunes. ≤ 36 pièces, tout tient
    dans un rayon de 8 autour de l'origine. v0 droit, v1 penché, v2 double tronc, v3 court et touffu.
- arbre_rond(hauteur=12) : feuillu de la campagne, tronc brun et couronne « sphère en voxels » (trois pavés
    croisés, dessous sombre, chapeau clair, bosses ; studs sur les dessus), rayon de couronne ≤ 5. ≤ 24 pièces.
    v0 rond, v1 ovale haut, v2 à deux lobes, v3 rond fleuri.
- arbre_boule(hauteur=24) : arbre extraterrestre, tronc pâle très fin coudé, couronne de boules bleu-vert
    (claire dessus, foncée dessous), rayon ≤ 6. ≤ 20 pièces. v0 boule seule, v1 boule et petite boule de côté,
    v2 tronc fourchu à deux couronnes, v3 toute petite couronne sur un tronc très haut.
- buisson(teinte="vert"|"alien") : 2 à 6 pièces, emprise ≤ 4 × 4, hauteur ≤ 3.
- rocher(taille=1, teinte="violet"|"gris"|"orange"|"sable") : blocs trapus tournés et coins, tout dans ±2·taille
    en X et en Z, ≈ 4 × 4 × 2,5 à la taille 1. ≤ 8 pièces.
- mesa(largeur, profondeur, hauteur) : butte à sommet plat des terres de combat : 4 ou 5 lobes verticaux qui se
    chevauchent presque à la même hauteur (sommet plat au contour irrégulier) et au plus un épaulement bas,
    strates violettes continues (filet sombre sur les grandes), une ou deux strates roses en saillie, côtes
    rocheuses verticales en gradins qui reprennent les strates, éboulis en pente au pied des faces visibles et
    rochers aux angles, chapeau d'herbe débordant et coulures, plaque d'herbe claire et buissons sur le dessus.
    ≤ 100 pièces. v0 butte seule, v1 buttes jumelles et col, v2 tour étroite sur un épaulement bas d'un côté,
    v3 large et basse à terrasse avant.
- pic_rocheux(hauteur=40, teinte="orange"|"violet"|"sable") : aiguille karstique en tronçons empilés qui
    s'affinent en zigzag (du sombre au clair), filets de strate, bosses aux angles, éboulis au pied, replat et
    chapeau d'herbe à coulures, arbre ou buisson au sommet. Emprise ≤ 10 × 10 (≤ 12 × 12 au-delà de 46 de haut).
    ≤ 40 pièces. v0 droit, v1 penché, v2 sommet fendu, v3 avec un épaulement herbu.
- cratere(rayon=10) : bourrelet de terre brûlée et de gravats (pente intérieure sombre, pente extérieure kaki),
    fond brûlé et fissures en étoile, cailloux projetés. VIDE. Emprise 2r + 4. ≤ 40 pièces.
- cascade(hauteur=26, largeur=8) : chute d'eau plaquée contre une falaise (face = plan z = 0 local, falaise
    derrière), lèvre sur le dessus, nappe en paliers, filets clairs, écume, brume, vasque bordée de pierres.
    Emprise (largeur + 4) × 10. ≤ 40 pièces.
- ile_herbeuse(largeur, profondeur, hauteur) : îlot du lac (flancs jusqu'à y = -2,1 sous l'eau), contour
    arrondi, strates de sable ocre, dessus d'herbe sarcelle débordant, plage, liseré d'écume. ≤ 40 pièces.

Repère (voir CONVENTIONS.md) : origine au centre de l'emprise au sol, y = 0 au sol, l'AVANT regarde -Z.
Les emprises ne dépendent pas de la largeur du couloir : c'est `zone.py` qui place les assets hors du couloir.
Avec le couloir élargi (rien de collidable dans |x| < 45 sous y = 12, rien du tout dans |x| < 46 entre 12 et 30),
les distances minimales au centre du couloir sont (voir PORTEE, mesurées sur toutes les variantes) :
palmier |x| ≥ 54 ; arbre_rond |x| ≥ 51 ; arbre_boule |x| ≥ 55 (≥ 50 pour v3) ; buisson |x| ≥ 48 ;
rocher |x| ≥ 45 + 2,9·taille (sans collision sous la taille 0,8) ; cratere |x| ≥ 45 + rayon + 2 ;
pic_rocheux |x| ≥ 46 + 5 (+ 6 au-delà de 46 de haut) ; mesa tournée de ±90° : |x| ≥ 46 + profondeur / 2 + 1 ;
cascade : la vasque avance de 10 devant la face de la falaise ; ile_herbeuse : son emprise.

Règles tenues partout : aucune face coplanaire de couleurs différentes (les saillies sont de 0,2 à 0,6 et les
arêtes des grands blocs sont sur une grille de 0,5 : les faces des détails tombent entre deux crans), rien ne
flotte (coulures accrochées aux chapeaux, palmes noyées dans le cœur, noix collées au tronc), feuillage fin,
coulures, fleurs et cailloux sans collision ni ombre. Propriété intellectuelle : nature générique seulement ;
aucune sphère orange, aucune étoile, les cratères restent vides, aucun petit nuage jaune.
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, rot_y, shade
from palette import c, vary
from textures import mask_rects

Y = np.array([0.0, 1.0, 0.0])
DETAIL = dict(collide=False, shadow=False)

# Distance horizontale maximale de toute pièce à l'origine (studs, pire cas mesuré sur les variantes 0 à 3),
# pour la mise en page : un asset posé en |x| ≥ 46 + PORTEE ne déborde jamais au-dessus du couloir.
PORTEE = {"palmier": 8.0, "arbre_rond": 4.9, "arbre_boule": 8.7, "buisson": 2.2,
          "rocher_par_taille": 2.9, "cratere_plus_rayon": 2.0}

# ---------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------


def _u(v) -> np.ndarray:
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _q(v: float, pas: float = 0.5) -> float:
    """Arrondi sur la grille des grands blocs (0,5 stud)."""
    return round(v / pas) * pas


def _poutre(b, p0, p1, w, d, col, twist=0.0, ext0=0.0, ext1=0.0, **kw):
    """Bloc de section w × d dont l'axe Y local va de p0 à p1 (prolongé de ext0 / ext1), vrillé de `twist`."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    u = _u(p1 - p0)
    ref = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    x = _u(np.cross(u, ref))
    z = np.cross(x, u)
    R = np.column_stack([x, u, z]) @ rot_y(twist)
    a, e = p0 - u * ext0, p1 + u * ext1
    return b.part("block", (w, float(np.linalg.norm(e - a)), d), (a + e) / 2, R, col, **kw)


def _lame(b, p0, d, L, larg, ep, col, pointe=False, cote=1, roulis=0.0, **kw):
    """Lame plate (palme) qui part de p0 dans la direction d sur une longueur L.

    Bloc : largeur `larg` à l'horizontale, épaisseur `ep`. Pointe (`pointe=True`) : coin couché dans le plan de la
    lame, large à la base et effilé au bout (triangle rectangle, pointe du côté `cote`). `roulis` : rotation de la
    lame autour de son axe (degrés), pour que la lumière accroche les plis."""
    d = _u(d)
    X = np.cross(d, Y)
    X = _u(X) if np.linalg.norm(X) > 1e-6 else np.array([1.0, 0.0, 0.0])
    Zl = -d
    Yl = np.cross(Zl, X)
    if roulis:
        r = math.radians(roulis)
        X, Yl = X * math.cos(r) + np.cross(d, X) * math.sin(r), Yl * math.cos(r) + np.cross(d, Yl) * math.sin(r)
    centre = np.asarray(p0, float) + d * L / 2
    if pointe:
        R = np.column_stack([cote * Yl, -cote * X, Zl])
        return b.part("wedge", (ep, larg, L), centre, R, col, **kw)
    return b.part("block", (larg, ep, L), centre, np.column_stack([X, Yl, Zl]), col, **kw)


def _cadre(b, n0):
    """Bornes (repère de l'asset) des pièces ajoutées depuis n0, coins de chaque pièce compris."""
    o = b.to_world((0, 0, 0))
    M = np.vstack([b.to_world(e) - o for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))])
    signes = np.array([(sx, sy, sz) for sx in (1, -1) for sy in (1, -1) for sz in (1, -1)], float)
    pts = []
    for p in b.parts[n0:]:
        R = np.asarray(p.rot, float).reshape(3, 3)
        half = np.asarray(p.size, float) / 2
        coins = np.asarray(p.pos, float) + (signes * half) @ R.T
        pts.append((coins - o) @ M.T)
    if not pts:
        return np.zeros(3), np.zeros(3), M, np.zeros((0, 3))
    pts = np.vstack(pts)
    return pts.min(axis=0), pts.max(axis=0), M, pts


def _infos(b, n0) -> dict:
    lo, hi, _, _ = _cadre(b, n0)
    return {"emprise": (round(float(hi[0] - lo[0]), 1), round(float(hi[2] - lo[2]), 1)),
            "hauteur": round(float(hi[1]), 1), "pieces": len(b.parts) - n0}


def _rayon_max(b, n0) -> float:
    """Plus grande distance horizontale à l'origine (coins des pièces, repère de l'asset)."""
    _, _, _, pts = _cadre(b, n0)
    return float(np.max(np.hypot(pts[:, 0], pts[:, 2]))) if len(pts) else 0.0


def _recentrer(b, n0) -> None:
    """Décale les pièces ajoutées depuis n0 pour centrer leur emprise au sol sur l'origine."""
    lo, hi, M, _ = _cadre(b, n0)
    d = np.array([-(lo[0] + hi[0]) / 2, 0.0, -(lo[2] + hi[2]) / 2])
    d = np.round(d * 4) / 4
    if not d.any():
        return
    dw = M.T @ d
    for p in b.parts[n0:]:
        p.pos = tuple(round(float(v), 4) for v in np.asarray(p.pos, float) + dw)


def _union(rects, nd: int = 4) -> list:
    """Rectangles (x0, z0, x1, z1) qui se chevauchent → rectangles disjoints couvrant leur union (pour les dessus
    studdés : deux faces studdées coplanaires qui se recouvrent scintilleraient)."""
    xs = sorted({round(v, nd) for r in rects for v in (r[0], r[2])})
    zs = sorted({round(v, nd) for r in rects for v in (r[1], r[3])})
    ix, iz = {v: i for i, v in enumerate(xs)}, {v: i for i, v in enumerate(zs)}
    m = np.zeros((len(zs) - 1, len(xs) - 1), bool)
    for x0, z0, x1, z1 in rects:
        m[iz[round(z0, nd)]:iz[round(z1, nd)], ix[round(x0, nd)]:ix[round(x1, nd)]] = True
    return [(xs[i], zs[j], xs[i + w], zs[j + h]) for (i, j, w, h) in mask_rects(m)]


def _demi_emprise(sx, sz, yaw):
    a = math.radians(yaw)
    ca, sa = abs(math.cos(a)), abs(math.sin(a))
    return ca * sx / 2 + sa * sz / 2, sa * sx / 2 + ca * sz / 2


def _ajuster(specs, lim: float) -> float:
    """specs [forme, [x, y, z], [sx, sy, sz], yaw, ...] : réduit en X et Z (positions et tailles, même facteur, ce
    qui garde la forme des blocs tournés autour de Y) pour que tout tienne dans ±lim. Renvoie le facteur."""
    ext = 0.0
    for sp in specs:
        (x, _, z), (sx, _, sz), yw = sp[1], sp[2], sp[3]
        if sp[0] == "ball":
            ex = ez = sx / 2
        else:
            ex, ez = _demi_emprise(sx, sz, yw)
        ext = max(ext, abs(x) + ex, abs(z) + ez)
    if ext > lim:
        k = lim / ext
        for sp in specs:
            sp[1][0] *= k
            sp[1][2] *= k
            sp[2][0] *= k
            sp[2][2] *= k
            if sp[0] == "ball":
                sp[2][1] *= k
        return k
    return 1.0


TONS_ROCHE = {  # (foncé, base, clair, accent)
    "violet": ("mesa_violet_fonce", "mesa_violet", "mesa_violet_clair", "mesa_nuit"),
    "gris": ("rocher_fonce", "rocher", "rocher_clair", "rocher_fonce"),
    "orange": ("falaise_orange_fonce", "falaise_orange", "falaise_orange_claire", "falaise_brune"),
    "sable": ("falaise_sable_fonce", "falaise_sable", "falaise_sable_claire", "falaise_sable_fonce"),
}


# ---------------------------------------------------------------------------
# 1. Palmier
# ---------------------------------------------------------------------------

TONS_PALME = ("palme", "palme_claire", "palme_fonce")


def _tronc_palmier(b, base, H, lean, n, w0, w1, rng, courbe=1.7, anneaux=(1, 3), twist0=0.0):
    """Tronc en n tronçons vrillés qui s'affinent, courbé vers `lean` (décalage horizontal du sommet).
    Renvoie (sommet, largeur du haut)."""
    base, lean = np.asarray(base, float), np.asarray(lean, float)
    pts = [base + lean * (i / n) ** courbe + Y * (H * i / n) for i in range(n + 1)]
    pts[0] = pts[0] - Y * 0.4                      # pied enfoncé dans le sol
    for i in range(n):
        w = w0 + (w1 - w0) * i / max(1, n - 1)
        col = vary("palmier_tronc" if i % 2 == 0 else "palmier_tronc_clair", rng, 0.04)
        tw = twist0 + i * 22
        _poutre(b, pts[i], pts[i + 1], w, w, col, twist=tw, ext1=0.25 if i < n - 1 else 0.0, name="Tronc")
        if i + 1 in anneaux and i + 1 < n:
            u = _u(pts[i + 1] - pts[i])
            _poutre(b, pts[i + 1] - u * 0.3, pts[i + 1] + u * 0.15, w + 0.3, w + 0.3,
                    vary("palmier_tronc_fonce", rng, 0.04), twist=tw, collide=False, name="Bague")
    return pts[-1], w1


def _couronne_palmier(b, T, n, s, rng, etages=3, a0=None, coeur=True, pousse=True):
    """Couronne de n palmes coudées autour du point T (sommet du tronc).

    Palme à 3 pièces : montée, palier, pointe tombante (coin couché) ; à 2 pièces : montée et pointe.
    Une palme sur deux est plus haute et plus courte (deux étages de palmes)."""
    a0 = float(rng.uniform(0, 360)) if a0 is None else a0
    for k in range(n):
        a = math.radians(a0 + k * 360 / n + float(rng.uniform(-9, 9)))
        u = np.array([math.cos(a), 0.0, math.sin(a)])
        haut = k % 2 == 1
        if etages == 3:
            if haut:
                pentes = (rng.uniform(42, 54), rng.uniform(2, 12), rng.uniform(-48, -36))
                Ls, larg = (2.1, 2.1, 2.1), (1.7, 1.55, 1.4)
            else:
                pentes = (rng.uniform(20, 30), rng.uniform(-14, -4), rng.uniform(-66, -54))
                Ls, larg = (2.5, 2.6, 2.6), (1.8, 1.65, 1.5)
        else:
            pentes = (rng.uniform(28, 40), rng.uniform(-62, -48)) if not haut else (rng.uniform(44, 56), rng.uniform(-42, -30))
            Ls, larg = ((2.9, 2.7), (1.7, 1.5)) if not haut else ((2.4, 2.3), (1.6, 1.45))
        ton = TONS_PALME[k % 3]
        p = np.asarray(T, float) + u * 0.3 + Y * (0.35 if haut else 0.1)
        m = len(pentes)
        for i, (pd, L, lg) in enumerate(zip(pentes, Ls, larg)):
            pr = math.radians(float(pd))
            d = math.cos(pr) * u + math.sin(pr) * Y
            Ls_ = L * s
            roul = (14 if (i + k) % 2 else -14) * (1 if k % 3 else -1)
            if i < m - 1:
                _lame(b, p - d * 0.15, d, Ls_ + 0.3, lg, 0.35, vary(ton, rng, 0.04), roulis=roul, name="Palme", **DETAIL)
            else:
                col = vary(mix(c(ton), c("palme_claire"), 0.35), rng, 0.04)
                _lame(b, p - d * 0.1, d, Ls_ + 0.1, lg, 0.3, col, pointe=True, cote=1 if k % 2 else -1, roulis=roul,
                      name="Palme", **DETAIL)
            p = p + d * Ls_
    T = np.asarray(T, float)
    if coeur:
        b.boxc(T + Y * 0.3, (1.3, 0.9, 1.3), vary("palme_fonce", rng, 0.04), yaw=45, collide=False, name="Coeur")
    if pousse:
        _poutre(b, T, T + np.array([0.1, 1.8 * s, 0.05]), 0.5, 0.5, vary("palme_claire", rng, 0.04), twist=20,
                name="Pousse", **DETAIL)


def _noix(b, T, w1, n, rng, a0=0.0):
    for j in range(n):
        a = math.radians(a0 + 40 + j * 360 / max(n, 3) + float(rng.uniform(-15, 15)))
        u = np.array([math.cos(a), 0.0, math.sin(a)])
        b.ball(np.asarray(T, float) - Y * (0.55 + 0.15 * (j % 2)) + u * (w1 / 2 + 0.3), 0.5,
               vary("noix_coco", rng, 0.05), name="Noix", **DETAIL)


def _palmier(b, v, H, s, rng, ep=1.0):
    a = float(rng.uniform(0, 360))
    ua = np.array([math.cos(math.radians(a)), 0.0, math.sin(math.radians(a))])
    if v == 2:  # double tronc d'une même souche
        w0 = 1.55 * ep
        b.boxc((0, 0.25, 0), (w0 + 0.9, 1.1, w0 + 0.9), vary("palmier_tronc_fonce", rng, 0.04), yaw=a + 45, name="Souche")
        ub = np.array([math.cos(math.radians(a + 150)), 0.0, math.sin(math.radians(a + 150))])
        Ta, wa = _tronc_palmier(b, ua * 0.35, H, ua * 2.6, 4, 1.35 * ep, 1.0 * ep, rng, courbe=1.4, anneaux=(2,))
        Tb, wb = _tronc_palmier(b, ub * 0.35, H * 0.7, ub * 2.3, 3, 1.25 * ep, 0.95 * ep, rng, courbe=1.3, anneaux=(1,),
                                twist0=30)
        _couronne_palmier(b, Ta, 5, s * 0.95, rng, etages=2, pousse=False)
        _couronne_palmier(b, Tb, 5, s * 0.85, rng, etages=2, pousse=False)
        _noix(b, Ta, wa, 2, rng, a)
        _noix(b, Tb, wb, 1, rng, a + 90)
        return
    if v == 3:  # court et touffu
        w0, w1 = 1.8 * ep, 1.35 * ep
        b.boxc((0, 0.25, 0), (w0 + 0.8, 1.0, w0 + 0.8), vary("palmier_tronc_fonce", rng, 0.04), yaw=a + 45, name="Souche")
        T, w = _tronc_palmier(b, (0, 0, 0), H * 0.55, ua * 0.7, 3, w0, w1, rng, anneaux=(2,))
        _couronne_palmier(b, T, 8, s * 1.05, rng)
        _noix(b, T, w, 3, rng, a)
        return
    lean = (0.9 if v == 0 else 3.4) * max(1.0, H / 16)
    w0, w1 = 1.5 * ep, 1.1 * ep
    b.boxc((0, 0.25, 0), (w0 + 0.8, 1.0, w0 + 0.8), vary("palmier_tronc_fonce", rng, 0.04), yaw=a + 45, name="Souche")
    T, w = _tronc_palmier(b, (0, 0, 0), H, ua * lean, 5, w0, w1, rng, courbe=1.7 if v == 0 else 1.45, anneaux=(1, 3))
    _couronne_palmier(b, T, 7, s, rng)
    _noix(b, T, w, 3, rng, a)


def palmier(b, variant: int = 0, hauteur: float = 14, rayon_max: float = 7.9) -> dict:
    """Palmier de la campagne terrestre (≤ 36 pièces, rayon ≤ `rayon_max` autour de l'origine, 7,9 par défaut).

    Les grands palmiers (hauteur > 16) ont un tronc plus épais et, si `rayon_max` le permet, une couronne plus
    large (jusqu'à 1,6 fois). v0 droit à peine courbé, v1 penché, v2 double tronc d'une même souche, v3 court et
    touffu."""
    v = variant % 4
    H = max(6.0, float(hauteur))
    n0 = len(b.parts)
    s = min(1.15 if rayon_max <= 8 else 1.6, max(0.85, H / 14))
    ep = min(1.4, max(1.0, H / 17))
    for _ in range(10):
        del b.parts[n0:]
        with b.group("Palmier"):
            _palmier(b, v, H, s, b.rng, ep)
        _recentrer(b, n0)
        if _rayon_max(b, n0) <= rayon_max:
            break
        s *= 0.92
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 2. Arbre rond (campagne)
# ---------------------------------------------------------------------------

K_TOUFFE = 1.32          # rayon des coins extrêmes de la couronne, en unités k
H_TOUFFE = 1.27          # dessus de la couronne au-dessus de son centre, en unités k (× étirement)


def _touffe_ronde(b, ctr, R, rng, yaw0=0.0, haut=1.0, fleurs=0, tons=("feuillage_fonce", "feuillage", "feuillage_clair"),
                  simple=False):
    """Couronne ronde « sphère en voxels » : trois pavés croisés (large, profond, haut) donnent un profil en
    escalier arrondi sous tous les angles, dessous sombre tourné à 45°, chapeau clair, deux bosses (une sombre en
    bas, une claire en haut). Coins extrêmes à R de l'axe ; studs sur les dessus. 7 pièces (+ fleurs)."""
    k = R / K_TOUFFE
    hk = k * haut
    kw = dict(studs="top", collide=False, name="Feuillage")
    T = [c(t) for t in tons]
    with b.at(ctr, yaw=yaw0):
        b.boxc((0, -0.05 * hk, 0), (2.0 * k, 1.1 * hk, 1.6 * k), vary(T[1], rng, 0.04), **kw)
        b.boxc((0, 0.0, 0), (1.6 * k, 1.3 * hk, 2.0 * k), vary(mix(T[1], T[2], 0.2), rng, 0.04), **kw)
        b.boxc((0, 0.05 * hk, 0), (1.45 * k, 1.9 * hk, 1.45 * k), vary(mix(T[1], T[2], 0.4), rng, 0.04), **kw)
        b.boxc((0.08 * k, 1.12 * hk, -0.06 * k), (0.95 * k, 0.3 * hk, 0.95 * k), vary(T[2], rng, 0.04), yaw=30, **kw)
        if simple:
            return ctr[1] + H_TOUFFE * hk
        b.boxc((0, -0.92 * hk, 0), (1.25 * k, 0.36 * hk, 1.25 * k), vary(T[0], rng, 0.04), yaw=45, **kw)
        a = float(rng.uniform(0, 360))
        for i, (dy, t, sz) in enumerate(((-0.38, 0, 0.8), (0.42, 2, 0.66))):
            aa = math.radians(a + 150 * i)
            b.boxc((0.68 * k * math.cos(aa), dy * hk, 0.68 * k * math.sin(aa)), (sz * k, sz * hk * 0.9, sz * k),
                   vary(T[t], rng, 0.05), yaw=20 + 35 * i, **kw)
        # fleurs posées sur les bandes visibles des dessus (pavé large, pavé profond, chapeau)
        spots = [(0.9, 0.5, 0.3), (-0.9, 0.5, -0.25), (0.3, 0.65, -0.9), (-0.25, 0.65, 0.9), (0.1, 1.27, -0.05),
                 (-0.9, 0.5, 0.35)]
        cols = ("fleur_rose", "blanc", "fleur_rose", "fleur_jaune", "fleur_rose", "blanc")
        for i in range(min(fleurs, len(spots))):
            fx, y, fz = spots[i]
            # sur le bord d'un pavé (|f| = 0,9) : la fleur dépasse de 0,15 de sa face, quelle que soit la taille
            x = math.copysign(k + 0.15 - 0.4, fx) if abs(fx) > 0.85 else fx * k
            z = math.copysign(k + 0.15 - 0.4, fz) if abs(fz) > 0.85 else fz * k
            y = y * hk
            # la fleur dépasse d'au moins 0,1 des faces du pavé qui la porte (jamais coplanaire)
            b.box((x - 0.4, y - 0.1, z - 0.4), (x + 0.4, y + 0.55, z + 0.4), vary(cols[i], rng, 0.03), name="Fleur",
                  **DETAIL)
    return ctr[1] + H_TOUFFE * hk


def arbre_rond(b, variant: int = 0, hauteur: float = 12) -> dict:
    """Feuillu de la campagne terrestre : tronc brun, couronne ronde en pavés croisés (≤ 24 pièces, rayon ≤ 5).

    v0 rond, v1 ovale haut, v2 à deux lobes, v3 rond semé de fleurs roses et blanches."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    H = max(6.0, float(hauteur))
    R = min(4.9, max(2.8, 0.4 * H))
    tr = vary("tronc", rng, 0.04)
    trf = shade(c("tronc"), 0.8)
    wt = 0.9 + 0.06 * H
    yaw0 = float(rng.uniform(0, 90))
    with b.group("Arbre"):
        if v == 2:
            R2 = R * 0.6
            k2 = R2 / K_TOUFFE
            yf = H * 0.38
            b.box((-wt / 2, -0.3, -wt / 2), (wt / 2, yf + 0.4, wt / 2), tr, name="Tronc")
            a = math.radians(yaw0)
            ux, uz = math.cos(a), math.sin(a)
            d = R - R2
            for sgn, hh in ((1, 1.0), (-1, 0.84)):
                cx, cz = sgn * d * ux, sgn * d * uz
                cy = H * hh - H_TOUFFE * k2
                _poutre(b, (0, yf, 0), (cx, cy - 0.5 * k2, cz), wt * 0.7, wt * 0.7, tr, name="Branche")
                _touffe_ronde(b, (cx, cy, cz), R2, rng, yaw0=yaw0 + 25 * sgn)
        else:
            haut = 1.4 if v == 1 else 1.0
            Rr = R * (0.8 if v == 1 else 1.0)
            k = Rr / K_TOUFFE
            yc = H - H_TOUFFE * k * haut
            b.box((-wt / 2, -0.3, -wt / 2), (wt / 2, yc - 0.3 * k * haut, wt / 2), tr, name="Tronc")
            _touffe_ronde(b, (0, yc, 0), Rr, rng, yaw0=yaw0, haut=haut, fleurs=6 if v == 3 else 0)
        for i in range(3):  # racines en coins
            with b.at((0, 0, 0), yaw=yaw0 + 40 + 120 * i):
                b.wedge((-0.35, 0, wt / 2 - 0.2), (0.35, 0.8, wt / 2 + 0.9), trf, down="+z", collide=False, name="Racine")
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 3. Arbre boule (planète extraterrestre)
# ---------------------------------------------------------------------------

HAUT_BOULES = 1.11      # dessus de la couronne au-dessus de son centre (en rayons)


def _boules(b, ctr, Rc, rng, n=3):
    """Couronne en boules : boule principale, ventre foncé dessous, boule claire décalée dessus et, si n ≥ 4,
    deux petites bouffées sur le pourtour (silhouette de nuage). Rayon horizontal ≤ 1,1 Rc."""
    ctr = np.asarray(ctr, float)
    a = math.radians(float(rng.uniform(0, 360)))
    u = np.array([math.cos(a), 0.0, math.sin(a)])
    w = np.array([-u[2], 0.0, u[0]])
    kw = dict(collide=False, name="Couronne")
    b.ball(ctr - Y * 0.42 * Rc + u * 0.1 * Rc, 0.78 * Rc, vary("boule_alien_fonce", rng, 0.04), **kw)
    b.ball(ctr, Rc, vary("boule_alien", rng, 0.04), **kw)
    b.ball(ctr + Y * 0.45 * Rc - u * 0.22 * Rc, 0.66 * Rc, vary("boule_alien_claire", rng, 0.04), **kw)
    if n >= 4:
        b.ball(ctr + w * 0.7 * Rc + Y * 0.12 * Rc, 0.4 * Rc, vary("boule_alien_claire", rng, 0.05), **kw)
        b.ball(ctr - w * 0.6 * Rc - u * 0.32 * Rc - Y * 0.18 * Rc, 0.4 * Rc, vary("boule_alien", rng, 0.05), **kw)


def _tige(b, pts, w, rng, tons=("tronc_alien", "tronc_alien")):
    for i in range(len(pts) - 1):
        col = vary(mix(c(tons[i % 2]), c("tronc_alien_fonce"), 0.25 * (i == 0)), rng, 0.03)
        _poutre(b, pts[i], pts[i + 1], w, w, col, twist=15 * i, ext1=0.15 if i < len(pts) - 2 else 0.0, name="Tronc")


def arbre_boule(b, variant: int = 0, hauteur: float = 24) -> dict:
    """Arbre « boule » de la planète extraterrestre (≤ 20 pièces, rayon de couronne ≤ 6) : tronc pâle très fin
    (0,6 à 1) en tronçons un peu coudés, couronne de boules bleu-vert (claire dessus, foncée dessous).

    v0 boule seule à bouffées, v1 boule et petite boule sur une branche de côté, v2 tronc fourchu à deux
    couronnes, v3 petite couronne au bout d'un tronc très haut."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    H = max(8.0, float(hauteur))
    t = min(1.0, max(0.0, (H - 14) / 28))
    w = 0.6 + 0.4 * t
    Rc = min(5.4, 3.5 + 2.0 * t)
    with b.group("ArbreBoule"):
        b.boxc((0, 0.2, 0), (w + 0.9, 0.7, w + 0.9), vary("tronc_alien_fonce", rng, 0.04), yaw=float(rng.uniform(0, 90)),
               name="Pied")

        def kink(y, amp=0.5):
            return np.array([float(rng.uniform(-amp, amp)), y, float(rng.uniform(-amp, amp))])

        if v == 2:
            Rc2 = min(Rc * 0.72, 3.8)
            yf = H * 0.45
            pts = [np.array([0.0, -0.3, 0.0]), kink(yf * 0.5, 0.3), kink(yf, 0.3)]
            _tige(b, pts, w, rng)
            a = math.radians(float(rng.uniform(0, 360)))
            u = np.array([math.cos(a), 0.0, math.sin(a)])
            for sgn, hh in ((1, 1.0), (-1, 0.8)):
                yc = H * hh - HAUT_BOULES * Rc2
                top = pts[-1] + u * sgn * (Rc2 + 0.8) + Y * (yc - pts[-1][1])
                mid = pts[-1] + u * sgn * (Rc2 + 0.8) * 0.7 + Y * ((top[1] - pts[-1][1]) * 0.45)
                _tige(b, [pts[-1], mid, top - Y * 0.4 * Rc2], w * 0.85, rng)
                _boules(b, top, Rc2, rng, n=3)
        elif v == 3:
            Rc3 = 2.4 + 0.6 * t
            yc = H - HAUT_BOULES * Rc3
            pts = [np.array([0.0, -0.3, 0.0]), kink(yc * 0.35), kink(yc * 0.7), kink(yc - 0.5 * Rc3, 0.4)]
            _tige(b, pts, w * 0.85, rng)
            ctr = pts[-1] + Y * 0.5 * Rc3
            b.cyl(ctr - Y * 0.95 * Rc3, 0.4 * Rc3, 0.5, vary("boule_alien_fonce", rng, 0.04), collide=False, name="Collerette")
            _boules(b, ctr, Rc3, rng, n=3)
        else:
            yc = H - HAUT_BOULES * Rc
            pts = [np.array([0.0, -0.3, 0.0]), kink(yc * 0.4), kink(yc * 0.75), kink(yc - 0.5 * Rc, 0.35)]
            _tige(b, pts, w, rng)
            ctr = pts[-1] + Y * 0.5 * Rc
            _boules(b, ctr, Rc, rng, n=4 if v == 0 else 3)
            if v == 1:
                a = math.radians(float(rng.uniform(0, 360)))
                u = np.array([math.cos(a), 0.0, math.sin(a)])
                r2 = 0.45 * Rc
                p0 = pts[1] + (pts[2] - pts[1]) * 0.35
                side = p0 + u * (r2 + 2.2) + Y * 2.6
                _tige(b, [p0, p0 + u * 1.0 + Y * 1.4, side - Y * 0.6 * r2], w * 0.7, rng)
                b.ball(side - Y * 0.3 * r2, 0.8 * r2, vary("boule_alien_fonce", rng, 0.04), collide=False, name="Couronne")
                b.ball(side, r2, vary("boule_alien", rng, 0.04), collide=False, name="Couronne")
                b.ball(side + Y * 0.4 * r2 - u * 0.2 * r2, 0.62 * r2, vary("boule_alien_claire", rng, 0.04),
                       collide=False, name="Couronne")
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 4. Buisson
# ---------------------------------------------------------------------------

BUISSONS_VERTS = [
    # (forme, centre, taille, yaw relatif, ton) ; les points de fleurs suivent
    ([("block", (0.0, 0.8, 0.0), (3.2, 1.6, 2.8), 0, "buisson"), ("block", (0.1, 1.15, -0.1), (2.4, 2.3, 2.4), 45, "feuillage"),
      ("block", (-0.1, 2.55, 0.1), (1.3, 0.5, 1.2), 20, "feuillage_clair")], [(1.0, 1.75, -0.7)]),
    ([("block", (-0.7, 0.9, 0.0), (2.2, 1.8, 2.2), 0, "buisson"), ("block", (0.85, 0.7, 0.3), (1.8, 1.4, 1.8), 35, "feuillage"),
      ("block", (-0.6, 2.05, -0.1), (1.3, 0.5, 1.2), 15, "feuillage_clair")], [(0.9, 1.5, 0.3), (-1.3, 1.9, 0.5)]),
    ([("block", (0.0, 0.55, 0.0), (3.4, 1.1, 2.4), 0, "buisson"), ("block", (0.5, 0.9, 0.2), (1.9, 1.0, 1.9), 40, "feuillage"),
      ("block", (-1.0, 0.75, -0.2), (1.3, 0.9, 1.3), 10, "feuillage_clair")], [(-1.0, 1.25, -0.2)]),
    ([("block", (0.0, 0.8, 0.0), (3.0, 1.6, 2.6), 0, "buisson"), ("block", (0.1, 1.1, -0.1), (2.2, 2.2, 2.2), 45, "feuillage"),
      ("block", (-0.1, 2.4, 0.1), (1.2, 0.5, 1.1), 20, "feuillage_clair")], [(1.0, 1.7, -0.6), (-0.9, 1.85, 0.6), (0.2, 2.6, 0.1)]),
]
BUISSONS_ALIEN = [
    [((0.0, 0.0), 1.35, "boule_alien_fonce"), ((1.0, 0.5), 0.95, "buisson_alien"), ((-1.0, -0.4), 0.85, "boule_alien_claire")],
    [((-0.6, 0.0), 1.2, "buisson_alien"), ((0.9, 0.2), 1.0, "boule_alien_claire"), ((0.2, -0.9), 0.75, "boule_alien_fonce")],
    [((0.0, 0.0), 1.0, "buisson_alien"), ((1.0, 0.3), 0.8, "boule_alien_fonce"), ((-0.9, 0.4), 0.8, "boule_alien_claire"),
     ((0.1, -0.9), 0.7, "boule_alien")],
    [((0.0, 0.0), 1.35, "boule_alien_fonce"), ((1.0, 0.5), 0.95, "buisson_alien"), ((-0.9, -0.5), 0.8, "boule_alien_claire")],
]


def buisson(b, variant: int = 0, teinte: str = "vert") -> dict:
    """Petit buisson (emprise ≤ 4 × 4, hauteur ≤ 3, ≤ 8 pièces). teinte « vert » (campagne et friche : blocs
    studdés et petites fleurs roses ou jaunes) ou « alien » (boules bleu-vert sur une galette).
    v0 rond, v1 deux lobes, v2 bas et étalé, v3 fleuri (vert) ou à bourgeon (alien)."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    kw = dict(collide=False, name="Buisson")
    yaw0 = float(rng.uniform(0, 90))
    a = math.radians(yaw0)
    ca, sa = math.cos(a), math.sin(a)
    specs = []
    if teinte == "alien":
        for (x, z), r, ton in BUISSONS_ALIEN[v]:
            specs.append(["ball", [ca * x + sa * z, 0.75 * r, -sa * x + ca * z], [2 * r, 2 * r, 2 * r], 0.0, ton])
        specs.append(["block", [0.0, 0.2, 0.0], [2.4, 0.4, 2.0], yaw0, "buisson_alien"])
        fleurs = [(0.0, 2.0, 0.0)] if v == 3 else []
    else:
        blocs, fleurs = BUISSONS_VERTS[v]
        for forme, (x, y, z), (sx, sy, sz), yw, ton in blocs:
            specs.append([forme, [ca * x + sa * z, y, -sa * x + ca * z], [sx, sy, sz], yaw0 + yw, ton])
    k = _ajuster(specs, 1.97)
    with b.group("Buisson"):
        for forme, ctr, size, yw, ton in specs:
            if forme == "ball":
                b.ball(tuple(ctr), size[0] / 2, vary(ton, rng, 0.04), **kw)
            else:
                b.boxc(tuple(ctr), tuple(size), vary(ton, rng, 0.05), yaw=yw, studs="top", **kw)
        for i, (x, y, z) in enumerate(fleurs):
            X, Z = (ca * x + sa * z) * k, (-sa * x + ca * z) * k
            if teinte == "alien":
                b.box((X - 0.25, 2.1, Z - 0.25), (X + 0.25, 2.5, Z + 0.25), c("vitre_verte"), name="Bourgeon", **DETAIL)
            else:
                col = c(("fleur_rose" if v % 2 == 0 else "fleur_jaune") if i % 2 == 0 else "blanc")
                b.box((X - 0.25, y - 0.15, Z - 0.25), (X + 0.25, y + 0.3, Z + 0.25), col, name="Fleur", **DETAIL)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 5. Rocher
# ---------------------------------------------------------------------------

ROCHERS = [
    # (forme, centre (x, y, z), taille (sx, sy, sz), yaw, ton 0..3 ; pour un coin : sens de la pente « -z » local)
    [("block", (0.0, 0.95, 0.1), (3.0, 1.9, 2.6), 12, 1), ("block", (0.25, 1.2, -0.15), (2.4, 2.4, 2.3), 55, 0),
     ("block", (-0.15, 2.55, 0.05), (1.6, 0.5, 1.4), 30, 2), ("block", (1.35, 0.45, 1.0), (1.2, 0.9, 1.0), -20, 0),
     ("wedge", (-1.2, 0.5, -1.0), (1.4, 1.0, 1.2), 200, 1)],
    [("block", (-0.55, 1.2, 0.0), (2.0, 2.4, 2.2), 8, 1), ("block", (0.9, 0.85, 0.3), (1.9, 1.7, 2.0), -28, 0),
     ("block", (-0.5, 2.55, 0.1), (1.4, 0.4, 1.5), 20, 2), ("wedge", (0.9, 1.95, 0.3), (1.6, 0.5, 1.7), 152, 1),
     ("block", (0.2, 0.3, -1.4), (1.1, 0.6, 0.9), 40, 3)],
    [("block", (0.0, 0.55, 0.0), (3.6, 1.1, 2.8), 18, 1), ("block", (0.3, 1.35, -0.2), (2.4, 0.7, 1.8), 40, 2),
     ("block", (-1.25, 1.0, 0.9), (1.3, 1.6, 1.2), -10, 0), ("block", (1.5, 0.3, 1.2), (0.9, 0.6, 0.8), 60, 3)],
    [("block", (0.2, 1.0, 0.3), (2.8, 2.0, 2.4), 8, 1), ("wedge", (-1.6, 0.85, 0.3), (2.4, 1.7, 0.9), 98, 0),
     ("wedge", (0.25, 0.75, -1.3), (2.6, 1.5, 0.8), 8, 0), ("block", (0.6, 2.2, 0.6), (1.5, 0.45, 1.3), 35, 2),
     ("block", (1.5, 0.3, -1.2), (0.8, 0.6, 0.7), -20, 3)],
]


def rocher(b, variant: int = 0, taille: float = 1.0, teinte: str = "violet") -> dict:
    """Rocher trapu de blocs tournés et de coins (≤ 8 pièces). Tout reste dans ±2·taille en X et en Z.

    v0 bloc arrondi, v1 rocher fendu en deux, v2 dalle plate et cailloux, v3 arête en toit.
    Les petits rochers (taille < 0,8) sont sans collision ni ombre."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    tons = TONS_ROCHE.get(teinte, TONS_ROCHE["violet"])
    t = max(0.2, float(taille))
    yaw0 = float(rng.uniform(0, 360))
    specs = []
    a = math.radians(yaw0)
    ca, sa = math.cos(a), math.sin(a)
    for forme, (x, y, z), (sx, sy, sz), yw, ti in ROCHERS[v]:
        X, Z = ca * x + sa * z, -sa * x + ca * z          # rotation de l'ensemble (même sens que kit.rot_y)
        specs.append([forme, [X * t, y * t, Z * t], [sx * t, sy * t, sz * t], yw + yaw0, ti])
    _ajuster(specs, 2.0 * t - 0.02)
    kw = dict(collide=True) if t >= 0.8 else dict(DETAIL)
    with b.group("Rocher"):
        for forme, ctr, size, yw, ti in specs:
            col = vary(tons[ti], rng, 0.04)
            b.part(forme, tuple(size), tuple(ctr), rot_y(yw), col, studs="top", name="Rocher", **kw)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 6. Mesa (terres de combat)
# ---------------------------------------------------------------------------

PLANS_MESA = [
    # lobes (x0, x1, z0, z1, h) : x et z en fractions de la surface utile (hors éboulis), h en fraction de H.
    # Les lobes d'une même butte ont presque la même hauteur (sommet plat) ; un seul épaulement bas au plus.
    [(-0.36, 0.30, -0.30, 0.38, 1.0), (-0.50, -0.08, -0.04, 0.50, 0.955), (0.08, 0.50, -0.22, 0.30, 0.93),
     (-0.42, -0.02, -0.50, -0.06, 0.975)],
    [(-0.50, -0.08, -0.36, 0.44, 1.0), (-0.40, -0.14, -0.50, 0.50, 0.965), (0.16, 0.50, -0.20, 0.50, 0.88),
     (0.20, 0.44, -0.50, 0.10, 0.85), (-0.16, 0.24, -0.12, 0.34, 0.52)],
    [(-0.50, -0.04, -0.34, 0.30, 1.0), (-0.40, 0.04, -0.12, 0.50, 0.965), (-0.12, 0.50, -0.50, 0.40, 0.44),
     (0.10, 0.44, -0.30, 0.50, 0.41)],
    [(-0.44, 0.50, -0.10, 0.50, 1.0), (-0.50, 0.12, 0.00, 0.44, 0.975), (0.22, 0.46, -0.32, 0.26, 0.955),
     (-0.46, 0.06, -0.50, 0.04, 0.56)],
]

ROSE = "mesa_rose"
# Bandes sombres communes à toutes les mesas (même « géologie » sur toute la plaine) : (bas, épaisseur)
BANDES_NUIT = ((11.5, 1.5), (27.5, 2.0), (45.5, 2.0), (63.5, 2.0))
EBOULIS = mix(c("mesa_violet_clair"), c("kaki_clair"), 0.35)       # éboulis clairs, lisibles de loin


def _strates_mesa(H, rng):
    """Strates horizontales communes à tous les lobes : (y0, y1, ton), du pied au sommet. Tons violets alternés
    et bandes sombres (mesa_nuit) aux hauteurs fixes de BANDES_NUIT (si elles tombent sous le chapeau)."""
    tons = ["mesa_violet_fonce", "mesa_violet", "mesa_violet_clair", "mesa_violet", "mesa_violet_clair",
            "mesa_violet", "mesa_violet_clair", "mesa_violet"]
    bornes = [0.0]
    for (yb, e) in BANDES_NUIT:
        if yb + e < H - 4.0:
            bornes += [yb, yb + e]
    bornes.append(H + 2)
    out = []
    k = 0
    for y0, y1 in zip(bornes[:-1], bornes[1:]):
        if any(abs(y0 - yb) < 1e-6 for yb, _ in BANDES_NUIT):
            out.append((y0, y1, "mesa_nuit"))
            continue
        # les grands intervalles sont recoupés en deux tons
        if y1 - y0 > 14:
            ym = _q(y0 + (y1 - y0) * float(rng.uniform(0.4, 0.6)))
            out += [(y0, ym, tons[k % len(tons)]), (ym, y1, tons[(k + 1) % len(tons)])]
            k += 2
        else:
            out.append((y0, y1, tons[k % len(tons)]))
            k += 1
    return out


def mesa(b, variant: int = 0, largeur: float = 30, profondeur: float = 26, hauteur: float = 26) -> dict:
    """Mesa (butte à sommet plat) des terres de combat. Emprise largeur (X local) × profondeur (Z local), débord
    du chapeau compris ; l'avant (-Z) regarde le couloir.

    Plan : 3 à 5 lobes verticaux aux angles abattus (deux pavés croisés : plan en octogone à gradins), presque à la
    même hauteur (sommet plat au contour irrégulier), plus un épaulement bas selon la variante. Flancs : strates
    violettes continues et bandes sombres à hauteurs fixes (communes à toutes les mesas), une ou deux strates roses
    en saillie, une fissure sombre. Pied : grands éboulis clairs en pente sur toutes les faces visibles et blocs
    d'éboulis aux angles. Dessus : chapeau d'herbe épais (2 studs) qui déborde de 1, coulures dessous, plaque
    d'herbe claire et buissons. v0 butte seule, v1 buttes jumelles et col, v2 tour étroite sur un épaulement bas
    d'un côté, v3 large et basse à terrasse avant. ≤ 110 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    W, D, H = float(largeur), float(profondeur), float(hauteur)
    BUDGET = 110 if H < 50 else 135
    CAP, DEB = 2.0, 1.0
    TAL = _q(min(5.0, max(2.5, 0.14 * min(W, D))))      # profondeur des éboulis du pied

    def reste():
        return BUDGET - (len(b.parts) - n0)

    # -- plan : surface utile (éboulis autour), grille de 0,5, plans de faces tous distincts ----------------
    ux0, ux1 = -W / 2 + TAL, W / 2 - TAL
    uz0, uz1 = -D / 2 + TAL, D / 2 - TAL
    blocs, hs = [], []
    plans_x, plans_z = set(), set()
    for (fx0, fx1, fz0, fz1, fh) in PLANS_MESA[v]:
        X = lambda f: _q(ux0 + (f + 0.5) * (ux1 - ux0))  # noqa: E731
        Z = lambda f: _q(uz0 + (f + 0.5) * (uz1 - uz0))  # noqa: E731
        x0, x1, z0, z1 = X(fx0), X(fx1), Z(fz0), Z(fz1)
        while x0 in plans_x:
            x0 += 0.5
        while x1 in plans_x or x1 <= x0 + 1:
            x1 -= 0.5
        while z0 in plans_z:
            z0 += 0.5
        while z1 in plans_z or z1 <= z0 + 1:
            z1 -= 0.5
        if x1 - x0 < 3 or z1 - z0 < 3:
            continue
        # angles abattus : chanfrein c (plans x0 + c, x1 - c, z0 + c, z1 - c distincts eux aussi)
        cf = _q(0.24 * min(x1 - x0, z1 - z0)) if min(x1 - x0, z1 - z0) >= 7 else 0.0
        for _ in range(6):
            if cf == 0 or not ({x0 + cf, x1 - cf} & plans_x or {z0 + cf, z1 - cf} & plans_z):
                break
            cf += 0.5
        plans_x |= {x0, x1} | ({x0 + cf, x1 - cf} if cf else set())
        plans_z |= {z0, z1} | ({z0 + cf, z1 - cf} if cf else set())
        h = H if fh >= 1 else _q(fh * H)
        while any(abs(h - o) < 0.49 for o in hs):
            h -= 0.5
        hs.append(h)
        blocs.append(dict(x0=x0, x1=x1, z0=z0, z1=z1, c=cf, h=h, top=h - CAP))
    # angles abattus seulement sur les deux plus hauts lobes (les autres restent d'un seul pavé : budget)
    for B in sorted(blocs, key=lambda B: -B["h"])[2:]:
        B["c"] = 0.0
    principal = max(blocs, key=lambda B: B["h"])
    strates = _strates_mesa(H, rng)
    ep_rose = 1.0 if H < 30 else 1.5
    roses = []
    for f in (0.38, 0.62, 0.5, 0.74, 0.28):
        yr = _q(f * H) + 0.25
        loin_nuit = all(yr + ep_rose < yb - 0.6 or yr > yb + e + 0.6 for yb, e in BANDES_NUIT)
        if loin_nuit and all(not (B["top"] - 1.5 < yr + ep_rose and yr < B["h"] + 0.5) for B in blocs) and \
                all(abs(yr - r) > 5 for r in roses):
            roses.append(yr)
        if len(roses) == (2 if H >= 34 else 1):
            break

    # retrait maximal : le plus petit lobe garde au moins 3 studs de large
    r_max = max(0.0, min((min(B["x1"] - B["x0"], B["z1"] - B["z0"]) - 2 * B["c"]) / 2 - 1.5 for B in blocs))
    r_max = 0.25 * math.floor(4 * r_max)

    def retrait(y):
        """Fruit des flancs : retrait (multiple de 0,25) des strates qui commencent à la hauteur y, le même pour
        tous les lobes (leurs faces restent dans des plans distincts) ; petites corniches alternées."""
        k = int(round(y / 3.0))
        return min(r_max, 0.25 * round(4 * 0.045 * y) + (0.25 if k % 3 == 1 else 0.0))

    def pavés(B, g=0.0):
        """Les deux pavés croisés d'un lobe (élargis de g ; g < 0 : rentrés) : [(x0, x1, z0, z1)]."""
        x0, x1, z0, z1, cf = B["x0"] - g, B["x1"] + g, B["z0"] - g, B["z1"] + g, B["c"]
        if cf <= 0:
            return [(x0, x1, z0, z1)]
        return [(x0 + cf, x1 - cf, z0, z1), (x0, x1, z0 + cf, z1 - cf)]

    def dedans(px, pz, py, sauf):
        """Le point est-il dans un autre lobe (corps et chapeau compris) ?"""
        for o in blocs:
            if o is sauf:
                continue
            if py <= o["h"] and any(a - DEB <= px <= b_ + DEB and c_ - DEB <= pz <= d + DEB for a, b_, c_, d in pavés(o)):
                return True
        return False

    with b.group("Mesa"):
        # -- 1. corps en strates (pavés croisés), chapeaux d'herbe épais, strates roses en saillie -------------
        for B in blocs:
            r_haut = 0.0
            for y0, y1, ton in strates:
                lo, hi = y0, min(y1, B["top"])
                if hi - lo < 0.1:
                    continue
                col = vary(ton, rng, 0.03)
                r_haut = retrait(y0)
                for (a, b_, c_, d) in pavés(B, -r_haut):
                    b.box((a, lo, c_), (b_, hi, d), col, name="Strate")
            B["r"] = r_haut                      # retrait des flancs sous le chapeau
            col = vary("herbe", rng, 0.02)
            # chapeau : les deux pavés croisés ont des dessus décalés de 0,1 (jamais coplanaires)
            for j, (a, b_, c_, d) in enumerate(pavés(B, DEB - r_haut)):
                b.box((a, B["top"], c_), (b_, B["h"] - 0.1 * j, d), col, studs="top", name="Herbe")
            for yr in roses:
                if yr + ep_rose < B["top"] - 0.6:
                    ry = max(retrait(y0) for y0, _, _ in strates if y0 <= yr + 1e-6)
                    for (a, b_, c_, d) in pavés(B, 0.3 - ry):
                        b.box((a, yr, c_), (b_, yr + ep_rose, d), c(ROSE), collide=False, name="StrateRose")
        # -- 2. grands éboulis clairs au pied des faces visibles, blocs aux angles abattus ----------------------
        for B in sorted(blocs, key=lambda B: -B["h"]):
            ht = _q(min(0.3 * H, 0.34 * B["h"], 10.0))
            cf = B["c"]
            faces = (("-z", B["x0"] + cf, B["x1"] - cf, B["z0"]), ("+z", B["x0"] + cf, B["x1"] - cf, B["z1"]),
                     ("-x", B["z0"] + cf, B["z1"] - cf, B["x0"]), ("+x", B["z0"] + cf, B["z1"] - cf, B["x1"]))
            for sens, u0, u1, n_ in faces:
                if u1 - u0 < 2.5:
                    continue
                um = (u0 + u1) / 2
                px, pz = {"-z": (um, n_ - 1.0), "+z": (um, n_ + 1.0), "-x": (n_ - 1.0, um), "+x": (n_ + 1.0, um)}[sens]
                if dedans(px, pz, 1.0, B):
                    continue
                lim = {"-z": n_ + D / 2, "+z": D / 2 - n_, "-x": n_ + W / 2, "+x": W / 2 - n_}[sens]
                dd = min(TAL, lim - 0.2)
                if dd < 1.2:
                    continue
                hh = ht * float(rng.uniform(0.8, 1.0))
                col = vary(EBOULIS, rng, 0.05)
                if sens == "-z":
                    b.wedge((u0 + 0.3, 0, n_ - dd), (u1 - 0.3, hh, n_ + 0.2), col, down="-z", studs="top", name="Eboulis")
                elif sens == "+z":
                    b.wedge((u0 + 0.3, 0, n_ - 0.2), (u1 - 0.3, hh, n_ + dd), col, down="+z", studs="top", name="Eboulis")
                elif sens == "-x":
                    b.wedge((n_ - dd, 0, u0 + 0.3), (n_ + 0.2, hh, u1 - 0.3), col, down="-x", studs="top", name="Eboulis")
                else:
                    b.wedge((n_ - 0.2, 0, u0 + 0.3), (n_ + dd, hh, u1 - 0.3), col, down="+x", studs="top", name="Eboulis")
            # blocs d'éboulis aux quatre angles abattus (lavande clair, ocre)
            for sx in (-1, 1):
                for sz in (-1, 1):
                    if reste() < 12 or (cf == 0 and B is not principal):
                        break
                    x = (B["x0"] if sx < 0 else B["x1"]) - sx * cf * 0.5
                    z = (B["z0"] if sz < 0 else B["z1"]) - sz * cf * 0.5
                    if dedans(x + sx * 1.0, z + sz * 1.0, 1.0, B):
                        continue
                    if abs(x) > W / 2 - 1.8 or abs(z) > D / 2 - 1.8:
                        x, z = x - sx * 0.8, z - sz * 0.8
                    s_ = float(rng.uniform(2.6, 3.6))
                    b.boxc((x, s_ * 0.36, z), (s_, s_ * 0.72, s_ * 0.85),
                           vary(("mesa_violet_clair", "ocre", "kaki_clair")[int(rng.integers(3))], rng, 0.04),
                           yaw=45 + float(rng.uniform(-12, 12)), studs="top", name="Rocher")
        # -- 3. dessus : plaque d'herbe claire, buissons ---------------------------------------------------------
        top = principal
        for k in range(3):
            if reste() < 14:
                break
            sx, sz = float(rng.choice([3.0, 4.0, 5.0])), float(rng.choice([3.0, 4.0]))
            if top["x1"] - top["x0"] < sx + 4 or top["z1"] - top["z0"] < sz + 4:
                continue
            x = _q(float(rng.uniform(top["x0"] + sx / 2 + 2, top["x1"] - sx / 2 - 2)))
            z = _q(float(rng.uniform(top["z0"] + sz / 2 + 2, top["z1"] - sz / 2 - 2)))
            if k == 0:
                b.box((x - sx / 2 + 0.25, top["h"], z - sz / 2 + 0.25), (x + sx / 2 + 0.25, top["h"] + 0.3, z + sz / 2 + 0.25),
                      vary("herbe_claire", rng, 0.03), studs="top", name="Herbe", **DETAIL)
            else:
                yaw = float(rng.uniform(0, 90))
                b.boxc((x, top["h"] + 0.7, z), (2.6, 1.4, 2.2), vary("buisson", rng, 0.04), yaw=yaw, studs="top",
                       collide=False, name="Buisson")
                b.boxc((x + 0.2, top["h"] + 1.65, z - 0.1), (1.5, 0.5, 1.3), vary("feuillage", rng, 0.04), yaw=yaw + 30,
                       studs="top", collide=False, name="Buisson")
        # -- 4. une fissure sombre sur la face avant du lobe principal -------------------------------------------
        cf = principal["c"]
        u0, u1, n_ = principal["x0"] + cf, principal["x1"] - cf, principal["z0"]
        if u1 - u0 >= 6 and reste() > 8:
            uc = _q(float(rng.uniform(u0 + 2, u1 - 2))) + 0.25
            ya = min(0.3 * H, 0.34 * principal["h"]) + 0.5
            yb = min(principal["top"] - float(rng.uniform(1.5, 3.0)), ya + 0.5 * H)
            # la fissure suit le fruit des flancs : un tronçon par palier de retrait
            ys = sorted({ya, yb} | {y0 for y0, _, _ in strates if ya < y0 < yb})
            col = vary(mix(c("mesa_nuit"), c("mesa_violet_fonce"), 0.3), rng, 0.03)
            for y_a, y_b in zip(ys[:-1], ys[1:]):
                r_ = retrait(max(y0 for y0, _, _ in strates if y0 <= y_a + 1e-6))
                if y_b - y_a >= 0.3:
                    b.box((uc - 0.4, y_a, n_ + r_ - 0.2), (uc + 0.4, y_b, n_ + r_ + 0.1), col, name="Fissure", **DETAIL)
        # -- 5. coulures d'herbe sous les chapeaux débordants, jusqu'au budget ------------------------------------
        cands = []
        for B in blocs:
            cf, r_ = B["c"], B.get("r", 0.0)
            for sens, u0, u1, n_ in (("-z", B["x0"] + cf, B["x1"] - cf, B["z0"] + r_),
                                     ("-x", B["z0"] + cf, B["z1"] - cf, B["x0"] + r_),
                                     ("+x", B["z0"] + cf, B["z1"] - cf, B["x1"] - r_),
                                     ("+z", B["x0"] + cf, B["x1"] - cf, B["z1"] - r_)):
                for _ in range(max(1, int((u1 - u0) / 4))):
                    cands.append((float(rng.uniform(0, 1)) + (0.6 if sens == "+z" else 0.0), B, sens, u0, u1, n_))
        cands.sort(key=lambda t: t[0])
        pris: dict = {}
        for _, B, sens, u0, u1, n_ in cands:
            if reste() < 1:
                break
            wd = float(rng.choice([1.0, 1.4, 2.0, 2.4]))
            if u1 - u0 < wd + 2:
                continue
            uc = _q(float(rng.uniform(u0 + wd / 2 + 0.75, u1 - wd / 2 - 0.75))) + 0.25
            if any(abs(uc - o) < (wd + w2) / 2 + 0.6 for o, w2 in pris.get((id(B), sens), ())):
                continue
            px, pz = {"-z": (uc, n_ - 1.4), "+z": (uc, n_ + 1.4), "-x": (n_ - 1.4, uc), "+x": (n_ + 1.4, uc)}[sens]
            if dedans(px, pz, B["top"] - 0.5, B):
                continue
            pris.setdefault((id(B), sens), []).append((uc, wd))
            ld = float(rng.choice([1.2, 1.8, 2.4, 3.0, 3.6])) * (1.0 if H < 34 else 1.4)
            y0, y1 = B["top"] - ld, B["top"] + 0.1
            a_, b_ = uc - wd / 2, uc + wd / 2
            if sens == "-z":
                b.box((a_, y0, n_ - DEB + 0.2), (b_, y1, n_ + 0.1), c("herbe"), name="Coulure", **DETAIL)
            elif sens == "+z":
                b.box((a_, y0, n_ - 0.1), (b_, y1, n_ + DEB - 0.2), c("herbe"), name="Coulure", **DETAIL)
            elif sens == "-x":
                b.box((n_ - DEB + 0.2, y0, a_), (n_ + 0.1, y1, b_), c("herbe"), name="Coulure", **DETAIL)
            else:
                b.box((n_ - 0.1, y0, a_), (n_ + DEB - 0.2, y1, b_), c("herbe"), name="Coulure", **DETAIL)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 7. Piton rocheux
# ---------------------------------------------------------------------------

TONS_PIC = {  # (tons des tronçons du pied au sommet, strate en saillie, herbe)
    "orange": (("falaise_orange", "falaise_orange_claire", "falaise_orange", "falaise_orange_claire", "falaise_orange",
                "falaise_orange_claire"), "falaise_brune", "herbe"),
    "violet": (("mesa_violet_fonce", "mesa_violet", "mesa_violet_fonce", "mesa_violet_clair", "mesa_violet",
                "mesa_violet_clair"), "mesa_rose", "herbe"),
    "sable": (("falaise_sable_fonce", "falaise_sable", "falaise_sable_claire", "falaise_sable", "falaise_sable_claire",
               "falaise_sable"), "falaise_sable_fonce", "herbe_alien"),
}


def _mini_arbre(b, x, y, z, teinte, rng):
    """Petit arbre ou buisson posé sur un sommet (y = dessus de l'herbe) : arbre rond (orange), arbre boule (sable),
    buisson (violet)."""
    if teinte == "orange":
        b.box((x - 0.4, y - 0.2, z - 0.4), (x + 0.4, y + 2.2, z + 0.4), vary("tronc", rng, 0.04), name="Tronc")
        _touffe_ronde(b, (x, y + 3.6, z), 2.6, rng, yaw0=float(rng.uniform(0, 90)), simple=True)
    elif teinte == "sable":
        _poutre(b, (x, y - 0.2, z), (x + 0.3, y + 3.4, z - 0.2), 0.5, 0.5, vary("tronc_alien", rng, 0.03), name="Tronc")
        b.ball((x + 0.4, y + 4.5, z - 0.3), 1.6, vary("boule_alien_fonce", rng, 0.04), collide=False, name="Couronne")
        b.ball((x + 0.3, y + 5.2, z - 0.25), 1.9, vary("boule_alien", rng, 0.04), collide=False, name="Couronne")
        b.ball((x + 0.1, y + 6.1, z - 0.5), 1.15, vary("boule_alien_claire", rng, 0.04), collide=False, name="Couronne")
    else:
        yaw = float(rng.uniform(0, 90))
        b.boxc((x, y + 0.7, z), (2.4, 1.4, 2.0), vary("buisson", rng, 0.04), yaw=yaw, studs="top", collide=False, name="Buisson")
        b.boxc((x + 0.2, y + 1.65, z - 0.1), (1.4, 0.5, 1.2), vary("feuillage", rng, 0.04), yaw=yaw + 30, studs="top",
               collide=False, name="Buisson")


def _coulures(b, T, y_cap, herbe, rng, n=4, out=0.35):
    """Coulures d'herbe sous un chapeau (une par face au plus), accrochées au chapeau, sans collision."""
    faces = [("-z", T["x0"], T["x1"], T["z0"]), ("+z", T["x0"], T["x1"], T["z1"]),
             ("-x", T["z0"], T["z1"], T["x0"]), ("+x", T["z0"], T["z1"], T["x1"])]
    for sens, u0, u1, n_ in faces[:n]:
        wd = float(rng.choice([1.0, 1.4]))
        if u1 - u0 < wd + 1.2:
            continue
        uc = min(u1 - wd / 2 - 0.15, max(u0 + wd / 2 + 0.15, _q(float(rng.uniform(u0 + wd / 2 + 0.5, u1 - wd / 2 - 0.5))) + 0.25))
        ld = float(rng.choice([0.9, 1.4, 2.0, 2.6]))
        y0, y1 = y_cap - ld, y_cap + 0.1
        if sens in ("-z", "+z"):
            za, zb = (n_ - out, n_ + 0.1) if sens == "-z" else (n_ - 0.1, n_ + out)
            b.box((uc - wd / 2, y0, za), (uc + wd / 2, y1, zb), c(herbe), name="Coulure", **DETAIL)
        else:
            xa, xb = (n_ - out, n_ + 0.1) if sens == "-x" else (n_ - 0.1, n_ + out)
            b.box((xa, y0, uc - wd / 2), (xb, y1, uc + wd / 2), c(herbe), name="Coulure", **DETAIL)


def pic_rocheux(b, variant: int = 0, hauteur: float = 40, teinte: str = "orange") -> dict:
    """Piton rocheux (aiguille karstique) : tronçons empilés qui s'affinent en zigzag, teintes du sombre (pied) au
    clair (haut), filets de strate en saillie aux joints, bosses aux angles, éboulis en pente autour du pied, chapeau
    d'herbe débordant (dessus de l'herbe à `hauteur`) avec coulures, petit arbre ou buisson au sommet (arbre rond pour
    « orange », arbre boule pour « sable », buisson pour « violet »). Emprise ≤ 10 × 10 (≤ 12 × 12 au-delà de 46).
    ≤ 40 pièces. v0 droit, v1 penché, v2 sommet fendu en deux aiguilles, v3 avec un épaulement herbu.
    teinte « sable » : pied plus large et sommet un peu évasé (pitons de la planète extraterrestre)."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    H = float(hauteur)
    F = 10.0 if H <= 46 else 12.0
    tons, strate, herbe = TONS_PIC.get(teinte, TONS_PIC["orange"])
    sable = teinte == "sable"
    n = (4 if H <= 50 else 5) if sable else (5 if H <= 40 else 6)     # pitons de sable : colonnes plus monolithiques
    cap = 1.0
    Hb = H - cap
    TAL = 1.3                                      # profondeur des éboulis du pied
    poids = np.array([1.25, 1.1, 1.0, 0.95, 0.9, 0.85][:n]) * rng.uniform(0.9, 1.1, n)
    ys = [0.0]
    for p in poids[:-1]:
        ys.append(_q(ys[-1] + Hb * p / poids.sum()))
    ys.append(Hb)
    prof = ([1.0, 0.8, 0.74, 0.72, 0.76][:n] if sable else [1.0, 0.84, 0.74, 0.66, 0.6, 0.56][:n])
    if sable:
        prof[-1] = max(prof[-1], 0.76)
    base = F - 2 * TAL - 0.4 - (2.0 if v == 3 else 0.0)
    a = math.radians(float(rng.uniform(0, 360)))
    ul = np.array([math.cos(a), math.sin(a)])
    tiers = []
    lim = F / 2 - 0.9                               # chapeau (0,5) et coulures (0,35) restent dans l'emprise
    for i in range(n):
        wx = min(base, _q(base * prof[i] * float(rng.uniform(0.97, 1.03))))
        wz = min(base, _q(wx * float(rng.uniform(0.86, 1.0))))
        if v == 1:
            off = ul * (F * 0.16) * (i / (n - 1)) ** 1.3
        elif i == 0:
            off = np.zeros(2)
        else:   # zigzag : chaque tronçon repart de l'autre côté
            off = np.array([(-1) ** i * float(rng.uniform(0.25, 0.6)), (-1) ** (i // 2) * float(rng.uniform(0.2, 0.5))])
        ox = max(-lim + wx / 2, min(lim - wx / 2, _q(off[0], 0.25)))
        oz = max(-lim + wz / 2, min(lim - wz / 2, _q(off[1], 0.25)))
        tiers.append(dict(x0=ox - wx / 2, x1=ox + wx / 2, z0=oz - wz / 2, z1=oz + wz / 2, y0=ys[i], y1=ys[i + 1]))
    fendu = v == 2
    corps = tiers[:-2] if fendu else tiers
    with b.group("Piton"):
        for i, T in enumerate(corps):
            b.box((T["x0"], T["y0"], T["z0"]), (T["x1"], T["y1"], T["z1"]), vary(tons[i], rng, 0.03), name="Roche")
        # bosses aux angles (même teinte, un peu plus sombre) : silhouette de roche, pas de « fenêtres »
        for i, T in enumerate(corps[:-1]):
            if i % 2 == 1 and len(corps) > 3:
                continue
            wx, wz = T["x1"] - T["x0"], T["z1"] - T["z0"]
            sx, sz = (1 if rng.uniform() < 0.5 else -1), (1 if rng.uniform() < 0.5 else -1)
            bx, bz = _q(wx * 0.45) + 0.1, _q(wz * 0.45) + 0.1
            cx = (T["x0"] + T["x1"]) / 2 + sx * (wx / 2 - bx / 2 + 0.7)
            cz = (T["z0"] + T["z1"]) / 2 + sz * (wz / 2 - bz / 2 + 0.7)
            if abs(cx) + bx / 2 > F / 2 - 0.05 or abs(cz) + bz / 2 > F / 2 - 0.05:
                continue
            th = T["y1"] - T["y0"]
            b.boxc((cx, T["y0"] + 0.1 * th + 0.4 * th, cz), (bx, 0.8 * th, bz), vary(shade(c(tons[i]), 0.93), rng, 0.03),
                   name="Bosse")
        # filets de strate en saillie (0,3) juste au-dessus de deux joints
        for i in (1, 3):
            if i >= len(corps):
                continue
            T = corps[i]
            ym = T["y0"] + 0.9                       # au-dessus du replat herbu du gradin inférieur
            b.box((T["x0"] - 0.3, ym, T["z0"] - 0.3), (T["x1"] + 0.3, ym + 0.7, T["z1"] + 0.3),
                  vary(strate, rng, 0.04), collide=False, name="Strate")
        # replat herbu sur le premier gradin
        T = corps[0]
        b.box((T["x0"] - 0.3, T["y1"], T["z0"] - 0.3), (T["x1"] + 0.3, T["y1"] + 0.6, T["z1"] + 0.3),
              vary(herbe, rng, 0.03), studs="top", name="Herbe")
        _coulures(b, dict(T, x0=T["x0"] - 0.3, x1=T["x1"] + 0.3, z0=T["z0"] - 0.3, z1=T["z1"] + 0.3), T["y1"] + 0.6,
                  herbe, rng, n=2, out=0.3)
        # éboulis en pente autour du pied
        hts = float(rng.uniform(1.8, 2.6)) + (1.0 if sable else 0.0)
        for sens in ("-z", "+z", "-x", "+x"):
            col = vary(shade(c(tons[0]), 0.86), rng, 0.04)
            hh = hts * float(rng.uniform(0.75, 1.0))
            if sens == "-z":
                b.wedge((T["x0"] + 0.4, 0, T["z0"] - TAL), (T["x1"] - 0.4, hh, T["z0"] + 0.2), col, down="-z", name="Eboulis")
            elif sens == "+z":
                b.wedge((T["x0"] + 0.6, 0, T["z1"] - 0.2), (T["x1"] - 0.6, hh, T["z1"] + TAL), col, down="+z", name="Eboulis")
            elif sens == "-x":
                b.wedge((T["x0"] - TAL, 0, T["z0"] + 0.5), (T["x0"] + 0.2, hh, T["z1"] - 0.5), col, down="-x", name="Eboulis")
            else:
                b.wedge((T["x1"] - 0.2, 0, T["z0"] + 0.7), (T["x1"] + TAL, hh, T["z1"] - 0.7), col, down="+x", name="Eboulis")

        def chapeau(T, y_haut):
            b.box((T["x0"] - 0.5, y_haut - cap, T["z0"] - 0.5), (T["x1"] + 0.5, y_haut, T["z1"] + 0.5),
                  vary(herbe, rng, 0.025), studs="top", name="Herbe")
            _coulures(b, dict(T, x0=T["x0"] - 0.5, x1=T["x1"] + 0.5, z0=T["z0"] - 0.5, z1=T["z1"] + 0.5), y_haut - cap,
                      herbe, rng, n=4)

        if fendu:
            # les deux derniers tronçons deviennent deux aiguilles côte à côte de hauteurs différentes
            T = tiers[-2]
            xm = _q((T["x0"] + T["x1"]) / 2)
            ga = dict(x0=T["x0"], x1=xm - 0.5, z0=T["z0"] + 0.5, z1=T["z1"] - 0.5)
            dr = dict(x0=xm + 0.5, x1=T["x1"], z0=T["z0"], z1=T["z1"] - 1.0)
            h_dr = _q(T["y0"] + (H - T["y0"]) * 0.62) + 0.3
            b.box((ga["x0"], T["y0"], ga["z0"]), (ga["x1"], H - cap, ga["z1"]), vary(tons[-2], rng, 0.03), name="Roche")
            b.box((dr["x0"], T["y0"], dr["z0"]), (dr["x1"], h_dr - cap, dr["z1"]), vary(tons[-3], rng, 0.03), name="Roche")
            chapeau(ga, H)
            chapeau(dr, h_dr)
            _mini_arbre(b, (ga["x0"] + ga["x1"]) / 2, H, (ga["z0"] + ga["z1"]) / 2, teinte, rng)
            _mini_arbre(b, (dr["x0"] + dr["x1"]) / 2, h_dr, (dr["z0"] + dr["z1"]) / 2, "violet", rng)
        else:
            T = tiers[-1]
            chapeau(T, H)
            _mini_arbre(b, (T["x0"] + T["x1"]) / 2, H, (T["z0"] + T["z1"]) / 2, teinte, rng)
        if v == 3:
            # épaulement : une colonne basse accolée d'un côté, chapeau d'herbe et buisson
            T = tiers[0]
            hs = _q(H * 0.42) + 0.3
            while any(abs(hs - y) < 0.35 or abs(hs - 1.0 - y) < 0.35 for y in ys):
                hs += 0.5
            side = 1 if float(rng.uniform()) < 0.5 else -1
            ep = dict(x0=T["x1"] - 1.1, x1=F / 2 - 0.55, z0=T["z0"] + 0.6, z1=T["z1"] - 0.6) if side > 0 else \
                dict(x0=-F / 2 + 0.55, x1=T["x0"] + 1.1, z0=T["z0"] + 0.6, z1=T["z1"] - 0.6)
            b.box((ep["x0"], 0, ep["z0"]), (ep["x1"], hs - cap, ep["z1"]), vary(tons[1], rng, 0.03), name="Roche")
            b.box((ep["x0"] - 0.5 if side < 0 else ep["x0"], hs - cap, ep["z0"] - 0.5),
                  (ep["x1"] + 0.5 if side > 0 else ep["x1"], hs, ep["z1"] + 0.5), vary(herbe, rng, 0.025), studs="top", name="Herbe")
            _mini_arbre(b, (ep["x0"] + ep["x1"]) / 2, hs, (ep["z0"] + ep["z1"]) / 2, "violet", rng)
        # rochers tombés au pied
        T = tiers[0]
        for k in range(2):
            sz = float(rng.uniform(1.0, 1.5))
            ang = float(rng.uniform(0, 2 * math.pi))
            r = min(F / 2 - sz * 0.75, max(T["x1"] - T["x0"], T["z1"] - T["z0"]) / 2 + 0.9)
            b.boxc((r * math.cos(ang), sz * 0.3, r * math.sin(ang)), (sz, sz * 0.7, sz * 0.9),
                   vary(tons[2], rng, 0.05), yaw=float(rng.uniform(0, 90)), studs="top", name="Caillou", **DETAIL)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 8. Cratère (vide)
# ---------------------------------------------------------------------------

def cratere(b, variant: int = 0, rayon: float = 10) -> dict:
    """Cratère d'impact sur sol plat : bourrelet de gravats (coins tournés vers l'intérieur et l'extérieur),
    fond brûlé en deux disques, fissures en étoile, cailloux projetés. Rien dans le cratère.
    Emprise 2r + 4 ; ≤ 40 pièces."""
    rng = b.rng
    n0 = len(b.parts)
    r = max(4.0, float(rayon))
    N = 10 if r < 9 else 12
    w_in = min(3.6, max(2.0, 0.3 * r))
    w_out = 1.4
    rm = r - 0.6
    L = 2 * math.pi * rm / N * 1.16
    interieur = (mix(c("kaki_fonce"), c("brule"), 0.35), mix(c("kaki_fonce"), c("brule"), 0.2), c("kaki_fonce"))
    exterieur = (c("kaki"), c("kaki_clair"), c("ocre"), c("kaki"))
    tons = ("kaki", "gravats", "kaki_fonce", "rocher", "kaki_clair")
    a0 = float(rng.uniform(0, 360))
    hs = []
    with b.group("Cratere"):
        for k in range(N):
            th = a0 + 360 * k / N + float(rng.uniform(-4, 4))
            h = float(rng.uniform(1.0, 2.5)) * (1.0 if variant % 2 == 0 else 0.85)
            rk = rm + float(rng.uniform(-0.35, 0.35))
            wi = w_in * float(rng.uniform(0.85, 1.1))
            hs.append((th, h, rk))
            tr = math.radians(th)
            with b.at((rk * math.cos(tr), 0, rk * math.sin(tr)), yaw=90 - th):
                b.wedge((-L / 2, 0, -wi), (L / 2, h, 0), vary(interieur[k % 3], rng, 0.05), down="-z", studs="top",
                        name="Bourrelet")
                b.wedge((-L / 2 * 0.9, 0, 0), (L / 2 * 0.9, h * 0.85, w_out), vary(exterieur[k % 4], rng, 0.05), down="+z",
                        studs="top", name="Bourrelet")
        # blocs de gravats sur la crête
        for j in range(3):
            th, h, rk = hs[(j * N) // 3 + 1]
            tr = math.radians(th)
            s = float(rng.uniform(1.0, 1.5))
            b.boxc((rk * math.cos(tr), h - 0.15 + s * 0.35, rk * math.sin(tr)), (s, s * 0.7, s * 0.85),
                   vary(("rocher", "gravats", "kaki_fonce")[j], rng, 0.04), yaw=float(rng.uniform(0, 90)), studs="top",
                   name="Gravat")
        # fond brûlé et fissures en étoile
        rd = rm - w_in + 0.4
        b.cyl((0, 0.06, 0), rd, 0.12, vary("brule", rng, 0.03), name="Fond", **DETAIL)
        ri = 0.42 * r
        b.cyl((0, 0.12, 0), ri, 0.24, mix(c("brule"), c("noir"), 0.35), name="Fond", **DETAIL)
        for k in range(7):
            th = math.radians(a0 + 30 + k * 360 / 7 + float(rng.uniform(-14, 14)))
            r0, r1 = ri + 0.15, rd + 0.4 - (0.0 if k % 2 else float(rng.uniform(0.5, 1.5)))
            if r1 - r0 < 0.6:
                continue
            rc = (r0 + r1) / 2
            b.boxc((rc * math.cos(th), 0.12, rc * math.sin(th)), (r1 - r0, 0.24, 0.32 + 0.12 * (k % 2)),
                   vary("fissure", rng, 0.04), yaw=-math.degrees(th), name="Fissure", **DETAIL)
        # cailloux projetés hors du cratère
        for k in range(3):
            th = math.radians(a0 + 70 + k * 120 + float(rng.uniform(-20, 20)))
            s = float(rng.uniform(0.7, 1.1))
            rr = r + 2.0 - s * 0.72
            b.boxc((rr * math.cos(th), s * 0.3, rr * math.sin(th)), (s, s * 0.6, s * 0.8),
                   vary(tons[(k + 1) % 4], rng, 0.05), yaw=float(rng.uniform(0, 90)), studs="top", name="Caillou", **DETAIL)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 9. Cascade
# ---------------------------------------------------------------------------

def cascade(b, variant: int = 0, hauteur: float = 26, largeur: float = 8) -> dict:
    """Cascade plaquée contre une falaise. Origine au pied de la falaise, au milieu de la chute ; la face de la
    falaise est le plan z = 0 local, la falaise derrière (z > 0). Tout est en z ≤ 0 sauf la lèvre d'eau posée
    sur le dessus de la falaise (z de 0 à 1,5, y de hauteur à hauteur + 0,6).

    Le chapeau d'herbe de la falaise déborde de 0,6 : la nappe tombe donc 0,75 à 1,15 devant la face (eau
    légèrement translucide, filets clairs en paliers), écume et brume au pied, vasque à fond d'eau 0,2 au-dessus
    du sol bordée de pierres (v0), de sable (v1) ou de rochers orange (v2). Emprise (largeur + 4) × 10. ≤ 40 pièces."""
    v = variant % 3
    rng = b.rng
    n0 = len(b.parts)
    h = float(hauteur)
    w = float(largeur)
    hw = w / 2
    eau = dict(collide=False, shadow=False)
    with b.group("Cascade"):
        # lèvre : l'eau arrive sur le dessus de la falaise, passe le chapeau et bascule dans une lèvre d'écume blanche
        b.box((-hw * 0.8, h, -0.9), (hw * 0.8, h + 0.6, 1.5), c("eau"), transparency=0.1, name="Eau", **eau)
        b.box((-hw * 0.8 - 0.15, h - 0.9, -1.4), (hw * 0.8 + 0.15, h + 0.75, -0.5), c("ecume"), name="Ecume", **eau)
        # nappe principale translucide puis élargissements plus clairs en paliers vers le bas
        b.box((-hw, 0.1, -1.15), (hw, h - 0.5, -0.75), c("eau"), transparency=0.2, name="Eau", **eau)
        b.box((-hw - 0.75, 0.05, -1.0), (hw + 0.75, h * 0.45, -0.7), c("eau_claire"), transparency=0.25, name="Eau", **eau)
        b.box((-hw - 1.5, 0.0, -0.9), (hw + 1.5, h * 0.18, -0.65), c("eau_claire"), transparency=0.25, name="Eau", **eau)
        # traînées d'écume blanches et d'eau claire (larges de 1 à 1,5), longueurs variées, accrochées à la nappe
        xs = np.linspace(-hw + 0.9, hw - 0.9, 6)
        for i, x in enumerate(xs):
            lw = (1.2, 1.5, 1.0, 1.4, 1.1, 1.3)[i]
            y_hi = h - 1.0 - float(rng.uniform(0, 0.3)) * h * (i % 2)
            y_lo = max(0.3, y_hi - h * float(rng.uniform(0.35, 0.8)))
            col = c("ecume") if i % 3 != 2 else c("eau_claire")
            b.box((x - lw / 2, y_lo, -1.4), (x + lw / 2, y_hi, -1.1), col, name="Filet", **eau)
        # gros bouillon blanc au pied
        for i, (x, y, z, sx, sy, sz, yw) in enumerate(((0.0, 1.0, -1.7, w * 0.85, 2.0, 2.2, 0),
                                                         (-hw * 0.7, 0.8, -2.6, 3.0, 1.6, 2.0, 20),
                                                         (hw * 0.65, 0.9, -2.4, 3.0, 1.8, 2.0, -15),
                                                         (0.4, 0.6, -3.4, 3.2, 1.2, 2.0, 35))):
            b.boxc((x, y, z), (sx, sy, sz), c("ecume"), yaw=yw, name="Ecume", **eau)
        # brume (blocs blancs translucides)
        for i, (x, y, z, s) in enumerate(((-hw * 0.45, 3.6, -2.4, 3.2), (hw * 0.5, 4.8, -2.0, 2.8), (0.2, 2.8, -3.6, 3.4))):
            b.boxc((x, y, z), (s * 1.4, s * 0.8, s), c("blanc"), yaw=float(rng.uniform(-20, 20)), transparency=0.55, name="Brume",
                   **eau)
        # vasque : fond d'eau 0,2 au-dessus du sol, rides claires, bordure
        b.box((-hw - 1.3, 0.0, -9.0), (hw + 1.3, 0.2, -0.3), c("eau"), transparency=0.1, name="Vasque", **eau)
        b.box((-hw * 0.9, 0.0, -9.6), (hw * 0.9, 0.2, -9.0), c("eau"), transparency=0.1, name="Vasque", **eau)
        for z, f in ((-4.2, 0.85), (-6.4, 0.6)):
            b.box((-hw * f, 0.08, z - 0.2), (hw * f, 0.32, z + 0.2), c("eau_claire"), name="Ride", **eau)
        bord = (("rocher_clair", "pierre", "rocher"), ("sable", "sable_clair", "sable_fonce"),
                ("falaise_orange_fonce", "falaise_orange", "rocher_clair"))[v]
        pierres = [(-hw - 1.15, -1.3, 1.6, 2.7), (-hw - 1.1, -4.0, 1.7, 2.8), (-hw - 0.9, -6.7, 1.8, 2.6),
                   (-hw + 0.9, -8.9, 2.8, 1.8), (0.4, -9.2, 3.0, 1.6), (hw - 0.6, -8.9, 2.8, 1.8),
                   (hw + 0.95, -6.6, 1.8, 2.6), (hw + 1.1, -3.9, 1.7, 2.8), (hw + 1.15, -1.3, 1.6, 2.6)]
        for i, (x, z, sx, sz) in enumerate(pierres):
            hy = round(float(rng.uniform(0.8, 1.3)) * 4) / 4 + (0.12 if i % 2 else 0.0)
            yw = float(rng.uniform(-10, 10))
            ex, ez = _demi_emprise(sx, sz, yw)
            x = max(-hw - 2 + ex, min(hw + 2 - ex, x))
            z = max(-10 + ez, min(-ez, z))
            b.boxc((x, hy / 2, z), (sx, hy, sz), vary(bord[i % 3], rng, 0.05), yaw=yw, studs="top", name="Bord")
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 10. Îlot herbeux (lac de la planète extraterrestre)
# ---------------------------------------------------------------------------

PLANS_ILE = [
    # rectangles (x0, z0, x1, z1) en fractions de largeur et profondeur ; plage : côté et position
    ([(-0.47, -0.22, 0.47, 0.30), (-0.34, -0.36, 0.36, 0.47), (-0.44, -0.30, 0.06, 0.40), (0.12, 0.10, 0.42, 0.42)], "-z"),
    ([(-0.45, -0.30, 0.30, 0.34), (-0.30, -0.47, 0.18, 0.47), (-0.20, -0.20, 0.47, 0.20)], "+x"),
    ([(-0.30, -0.47, 0.32, 0.30), (-0.47, -0.30, 0.47, 0.18), (-0.20, -0.36, 0.40, 0.45)], "+z"),
]


def ile_herbeuse(b, variant: int = 0, largeur: float = 24, profondeur: float = 18, hauteur: float = 3) -> dict:
    """Îlot herbeux du lac : contour arrondi (blocs qui se chevauchent), flancs en strates de sable ocre qui
    descendent sous l'eau jusqu'à y = -2,1 (la surface du lac est à -0,4 et il n'y a pas de sol dessous), liseré
    d'écume à la surface, dessus d'herbe sarcelle à `hauteur` qui déborde de 0,5, plage de sable d'un côté,
    coulures et petits buissons. ≤ 40 pièces. v0 ovale, v1 en haricot, v2 en goutte."""
    v = variant % 3
    rng = b.rng
    n0 = len(b.parts)
    W, D, h = float(largeur), float(profondeur), max(1.5, float(hauteur))
    plan, cote_plage = PLANS_ILE[v]
    # le corps laisse 0,5 de débord au chapeau, et la place de la plage de son côté
    mx = {"-x": 0.5, "+x": 0.5, "-z": 0.5, "+z": 0.5}
    mx[cote_plage] = min(3.5, 0.18 * (W if cote_plage in ("-x", "+x") else D))
    rects = []
    for i, (fx0, fz0, fx1, fz1) in enumerate(plan):
        # chaque lobe s'arrête à un cran différent du bord : jamais deux flancs dans le même plan
        x0 = _q(max(-W / 2 + mx["-x"] + 0.5 * i, fx0 * W))
        x1 = _q(min(W / 2 - mx["+x"] - 0.5 * i, fx1 * W))
        z0 = _q(max(-D / 2 + mx["-z"] + 0.5 * i, fz0 * D))
        z1 = _q(min(D / 2 - mx["+z"] - 0.5 * i, fz1 * D))
        for o in rects:                       # arêtes intérieures confondues : on rentre d'un cran
            if abs(x0 - o[0]) < 0.01 or abs(x0 - o[2]) < 0.01:
                x0 += 0.5
            if abs(x1 - o[0]) < 0.01 or abs(x1 - o[2]) < 0.01:
                x1 -= 0.5
            if abs(z0 - o[1]) < 0.01 or abs(z0 - o[3]) < 0.01:
                z0 += 0.5
            if abs(z1 - o[1]) < 0.01 or abs(z1 - o[3]) < 0.01:
                z1 -= 0.5
        if x1 - x0 >= 1 and z1 - z0 >= 1:
            rects.append([x0, z0, x1, z1])
    top = h - 1.0
    bas = -2.1
    if h >= 4:
        bandes = [(bas, 0.3, "falaise_sable_fonce"), (0.3, _q((0.3 + top) / 2) + 0.2, "falaise_sable"),
                  (_q((0.3 + top) / 2) + 0.2, top, "falaise_sable_claire")]
    else:
        bandes = [(bas, 0.3, "falaise_sable_fonce"), (0.3, top, "falaise_sable")]
    with b.group("Ile"):
        for x0, z0, x1, z1 in rects:
            for y0, y1, ton in bandes:
                if y1 - y0 >= 0.1:
                    b.box((x0, y0, z0), (x1, y1, z1), vary(ton, rng, 0.03), name="Flanc")
            # liseré d'écume à la surface de l'eau
            b.box((x0 - 0.35, -0.55, z0 - 0.35), (x1 + 0.35, -0.25, z1 + 0.35), c("ecume"), name="Ecume", **DETAIL)
            if h >= 3 and top - 0.3 > 1.6:
                b.box((x0 - 0.2, 1.05, z0 - 0.2), (x1 + 0.2, 1.4, z1 + 0.2), vary("falaise_sable_claire", rng, 0.03),
                      collide=False, name="Strate")
        # dessus d'herbe : union des rectangles élargis de 0,5, découpée en rectangles disjoints
        for x0, z0, x1, z1 in _union([(r[0] - 0.5, r[1] - 0.5, r[2] + 0.5, r[3] + 0.5) for r in rects]):
            b.box((x0, top, z0), (x1, h, z1), c("herbe_alien"), studs="top", name="Herbe")
        # plage de sable d'un côté : marche basse puis pente dans l'eau
        X0 = min(r[0] for r in rects)
        X1 = max(r[2] for r in rects)
        Z0 = min(r[1] for r in rects)
        Z1 = max(r[3] for r in rects)
        yp = min(0.3, top - 0.5)
        if cote_plage in ("-z", "+z"):
            lx = (X1 - X0) * 0.5
            cx = _q((X0 + X1) / 2 + float(rng.uniform(-1, 1))) + 0.25
            zf = Z0 if cote_plage == "-z" else Z1
            s = -1 if cote_plage == "-z" else 1
            ext = D / 2 - abs(zf) - 0.15
            b.box((cx - lx / 2, bas, zf - s * 0.5), (cx + lx / 2, yp, zf + s * ext * 0.55), vary("sable", rng, 0.03),
                  studs="top", name="Plage")
            b.wedge((cx - lx / 2 + 0.5, bas + 1.0, zf + s * ext * 0.55), (cx + lx / 2 - 0.5, yp, zf + s * ext),
                    vary("sable_clair", rng, 0.03), down=cote_plage, studs="top", name="Plage")
        else:
            lz = (Z1 - Z0) * 0.5
            cz = _q((Z0 + Z1) / 2 + float(rng.uniform(-1, 1))) + 0.25
            xf = X0 if cote_plage == "-x" else X1
            s = -1 if cote_plage == "-x" else 1
            ext = W / 2 - abs(xf) - 0.15
            b.box((xf - s * 0.5, bas, cz - lz / 2), (xf + s * ext * 0.55, yp, cz + lz / 2), vary("sable", rng, 0.03),
                  studs="top", name="Plage")
            b.wedge((xf + s * ext * 0.55, bas + 1.0, cz - lz / 2 + 0.5), (xf + s * ext, yp, cz + lz / 2 - 0.5),
                    vary("sable_clair", rng, 0.03), down=cote_plage, studs="top", name="Plage")
        # coulures d'herbe sous le débord (îlots assez hauts)
        if h >= 2.5:
            r = max(rects, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
            for k, (sens, u0, u1, n_) in enumerate((("-x", r[1], r[3], r[0]), ("+x", r[1], r[3], r[2]), ("+z", r[0], r[2], r[3]))):
                if sens == cote_plage or u1 - u0 < 3:
                    continue
                wd = float(rng.choice([1.0, 1.4, 2.0]))
                uc = min(u1 - wd / 2 - 0.15, max(u0 + wd / 2 + 0.15, _q(float(rng.uniform(u0 + wd / 2 + 0.5, u1 - wd / 2 - 0.5))) + 0.25))
                y0 = top - float(rng.choice([0.6, 0.9, 1.2]))
                px, pz = (n_ - 0.3, uc) if sens == "-x" else (n_ + 0.3, uc) if sens == "+x" else (uc, n_ + 0.3)
                if any(o[0] - 0.01 <= px <= o[2] + 0.01 and o[1] - 0.01 <= pz <= o[3] + 0.01 for o in rects):
                    continue
                if sens in ("-x", "+x"):
                    xa, xb = (n_ - 0.35, n_ + 0.1) if sens == "-x" else (n_ - 0.1, n_ + 0.35)
                    b.box((xa, y0, uc - wd / 2), (xb, top + 0.1, uc + wd / 2), c("herbe_alien"), name="Coulure", **DETAIL)
                else:
                    b.box((uc - wd / 2, y0, n_ - 0.1), (uc + wd / 2, top + 0.1, n_ + 0.35), c("herbe_alien"), name="Coulure", **DETAIL)
        # plaque d'herbe plus claire sur le dessus
        r = max(rects, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
        if r[2] - r[0] >= 6 and r[3] - r[1] >= 5:
            sx, sz = _q((r[2] - r[0]) * 0.4) + 0.2, _q((r[3] - r[1]) * 0.35) + 0.2
            x = _q(r[0] + 1.0 + float(rng.uniform(0, r[2] - r[0] - sx - 2.0))) + 0.25
            z = _q(r[1] + 1.0 + float(rng.uniform(0, r[3] - r[1] - sz - 2.0))) + 0.25
            b.box((x, h, z), (x + sx, h + 0.3, z + sz), c("herbe_alien_claire"), studs="top", name="Herbe", **DETAIL)
        # petits buissons boules sur le dessus (loin du centre où zone.py plante l'arbre)
        for k in range(2):
            r = rects[k % len(rects)]
            x = r[0] + 1.2 if k == 0 else r[2] - 1.2
            z = r[3] - 1.2 if k == 0 else r[1] + 1.2
            if math.hypot(x, z) < 2.5 or r[2] - r[0] < 3 or r[3] - r[1] < 3:
                continue
            rr = 0.9 if k == 0 else 0.7
            b.ball((x, h + 0.55 * rr, z), rr, vary("boule_alien" if k == 0 else "buisson_alien", rng, 0.04), collide=False,
                   name="Buisson")
            b.ball((x + 0.6 * rr, h + 0.4 * rr, z - 0.3 * rr), 0.6 * rr, vary("boule_alien_claire", rng, 0.04), collide=False,
                   name="Buisson")
    return _infos(b, n0)
