"""L'incident surnaturel de la ville de nuit, en style stud : immeuble effondré en arche au-dessus de la
sortie (repère final), dômes de barrière violet nuit, tours de verre endommagées, tas de gravats et voitures
abandonnées. Une catastrophe GÉNÉRIQUE dans une ville : aucun nom, aucun personnage, aucun symbole, aucun
texte (les barrières 立入禁止 viennent de `mobilier.py`).

Le couloir de course suit `passage` (largeur du couloir, 90 pour le couloir élargi x ∈ [-45, 45]) :
- rien de solide dans |x| < passage/2 entre y = 0,05 et 12 ; rien du tout au-dessus de |x| < passage/2 + 1
  sous y = 30 ; ce qui enjambe le couloir a son dessous à `hauteur_libre` ou plus (ici 8 de plus) ;
- les façades (et les moignons de l'immeuble effondré) commencent en |x| = passage/2 + 10 (55 pour 90,
  42 pour l'ancien couloir de 64) : la sortie offre donc 110 studs de large.

immeuble_effondre (≤ 900 pièces, un exemplaire ; ≈ 820 pièces)
    Repère final et porte de sortie, posé en (0, 0, -485) sans rotation : tout reste dans z ∈ [-11, 11].
    Deux moignons de tours encadrent le couloir à partir de |x| = passage/2 + 10 : à gauche une tour de béton
    écrasée (~42, mur arrière déchiqueté jusqu'à 64, angle avant côté couloir effondré qui montre ses
    planchers) ; à droite la tour bleu marine à rubans blancs qui s'est cassée (~95, sommet déchiqueté,
    cratère à lueur violette). Le haut de cette tour est tombé en travers : deux tronçons cassés (2° côté
    toit, 20° côté cassure) qui forment une arche brisée au-dessus du couloir. La cassure s'ouvre vers le
    bas (fers tendus, dents de béton, dalle qui pend, lueur violette) et une encoche en V la marque en
    haut. Les faces du haut de tour montrent la même grille que sa tour, tournée de 90° (planchers
    verticaux, meneaux horizontaux) ; son toit (acrotère, couronne néon, local technique, citerne,
    antenne, feu) dépasse à gauche, l'arrachement (dalles à nu, poteaux, fers) s'appuie dans l'encoche du
    moignon droit. Dessous ≥ hauteur_libre + 8 au-dessus du couloir (42 pour 34), câbles et fers qui pendent
    jamais sous hauteur_libre + 3, tas de gravats au pied des moignons (trottoirs seulement).
    variant 1 : miroir (le haut à gauche) et autres couleurs (tour de verre bleu, moignon gris chaud).

voile_dome (≤ 260 pièces pour rayon 72 : ≈ 253 ; ≤ 190 pour rayon 48 : ≈ 188)
    Dôme de barrière générique : demi-sphère en gradins (anneaux de dalles tangentes, translucides, violet
    nuit → violet clair), liserés au néon, anneau lumineux au sol, calotte opaque plus sombre, quelques
    méridiens lumineux. Aucun texte, aucun motif.

tour_endommagee (≤ 220 pièces ; ≈ 175 pour 26 × 32 × 70, ≈ 150 pour 32 × 24 × 58)
    Tour de bureaux vitrée abîmée : mur-rideau (allèges, meneaux) aux vitres manquantes, grand cratère à
    mi-hauteur dans la façade avant (planchers cassés, intérieur sombre, lueur violette), angle du sommet
    arraché (dalles à nu, fers), fissures, éclats de verre. Rez-de-chaussée : hall éventré (variantes paires)
    ou boutiques aux rideaux métalliques baissés et tagués de taches abstraites (variantes impaires).

gravats (≤ 30 pièces, 16 à 20) : tas de gravats dans un cercle de rayon 3·taille, hauteur ≤ 3,5·taille.
voiture_abandonnee (≤ 30 pièces, 23 à 27) : petite voiture japonaise générique, 4,6 × 9, avant vers -Z.
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, rot_x, rot_y, rot_z, shade
from palette import c, vary
from textures import mask_rects

PETIT = dict(collide=False, shadow=False)


# ---------------------------------------------------------------------------
# Outils géométriques
# ---------------------------------------------------------------------------

def _col(x):
    return c(x) if isinstance(x, str) else tuple(x)


def _d(b, a, bb, couleur, **kw):
    """Petit détail aligné sur les axes (sans collision ni ombre)."""
    return b.box(a, bb, _col(couleur), **{**PETIT, **kw})


def _n(b, a, bb, couleur, **kw):
    """Détail lumineux (matériau Neon)."""
    return b.box(a, bb, _col(couleur), material="Neon", **{**PETIT, **kw})


def _barre(b, p0, p1, larg, ep, normale, couleur, rallonge=0.0, **kw):
    """Bloc allongé de p0 à p1 : section `larg` × `ep`, l'épaisseur `ep` suivant `normale`."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = float(np.linalg.norm(d))
    if L < 1e-3:
        return None
    X = d / L
    Z = np.asarray(normale, float)
    Z = Z - X * float(Z @ X)
    if np.linalg.norm(Z) < 1e-6:
        Z = np.cross(X, [0.0, 1.0, 0.0]) if abs(X[1]) < 0.9 else np.cross(X, [1.0, 0.0, 0.0])
    Z /= np.linalg.norm(Z)
    Y = np.cross(Z, X)
    R = np.column_stack([X, Y, Z])
    return b.part("block", (L + rallonge, larg, ep), (p0 + p1) / 2, R, _col(couleur), **kw)


def _tige(b, p0, p1, r, couleur, **kw):
    """Cylindre fin de p0 à p1 (fer à béton, câble). L'axe d'un cylindre Roblox est son X local."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = float(np.linalg.norm(d))
    if L < 1e-3:
        return None
    X = d / L
    up = np.array([0.0, 1.0, 0.0]) if abs(X[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    Z = np.cross(X, up)
    Z /= np.linalg.norm(Z)
    Y = np.cross(Z, X)
    return b.part("cyl", (L + r * 0.6, 2 * r, 2 * r), (p0 + p1) / 2, np.column_stack([X, Y, Z]), _col(couleur),
                  **{**PETIT, **kw})


def _fer(b, p0, coude, p1, r=0.16, couleur="ferraille"):
    """Fer à béton tordu : deux segments (p0 → coude → p1)."""
    _tige(b, p0, coude, r, couleur, name="Fer")
    _tige(b, coude, p1, r, couleur, name="Fer")


def _moins(a, bb, coupes, mini=0.3):
    """Intervalle [a, bb] privé des intervalles `coupes` (liste d'intervalles restants, longueur ≥ mini)."""
    out = [(a, bb)]
    for (u, w) in coupes:
        nouv = []
        for (p, q) in out:
            if w <= p or u >= q:
                nouv.append((p, q))
                continue
            if u > p:
                nouv.append((p, u))
            if w < q:
                nouv.append((w, q))
        out = nouv
    return [(p, q) for (p, q) in out if q - p >= mini]


def _rects_moins(x0, x1, y0, y1, trous):
    """Rectangle [x0, x1] × [y0, y1] privé des rectangles `trous` (x0, x1, y0, y1), découpé en peu de blocs."""
    xs = sorted({x0, x1, *[v for t in trous for v in (t[0], t[1]) if x0 < v < x1]})
    ys = sorted({y0, y1, *[v for t in trous for v in (t[2], t[3]) if y0 < v < y1]})
    mask = np.ones((len(ys) - 1, len(xs) - 1), bool)
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if any(t[0] <= cx <= t[1] and t[2] <= cy <= t[3] for t in trous):
                mask[j, i] = False
    return [(xs[i], xs[i + w], ys[j], ys[j + h]) for (i, j, w, h) in mask_rects(mask)]


def _repere_courant(b):
    return b._R[-1], b._t[-1]


def _miroir_x(b, n0):
    """Symétrise par rapport au plan x = 0 du repère courant les pièces ajoutées depuis n0.
    Blocs, coins et cylindres sont symétriques selon leur X local : la rotation devient M·R·diag(-1, 1, 1)."""
    Rf, tf = _repere_courant(b)
    nx = Rf[:, 0]
    Mw = np.eye(3) - 2.0 * np.outer(nx, nx)
    Ml = np.diag([-1.0, 1.0, 1.0])
    for p in b.parts[n0:]:
        pos = np.asarray(p.pos, float)
        R = np.asarray(p.rot, float).reshape(3, 3)
        p.pos = tuple(round(float(v), 4) + 0.0 for v in tf + Mw @ (pos - tf))
        p.rot = tuple(round(float(v), 4) + 0.0 for v in (Mw @ R @ Ml).reshape(-1))


def _tourner(b, n0, Q, pivot):
    """Applique la rotation Q (repère courant), autour du point `pivot`, aux pièces ajoutées depuis n0."""
    Rf, tf = _repere_courant(b)
    pivot = np.asarray(pivot, float)
    G = Rf @ Q @ Rf.T
    for p in b.parts[n0:]:
        pos = np.asarray(p.pos, float)
        loc = Rf.T @ (pos - tf)
        loc2 = pivot + Q @ (loc - pivot)
        p.pos = tuple(round(float(v), 4) + 0.0 for v in tf + Rf @ loc2)
        R = np.asarray(p.rot, float).reshape(3, 3)
        p.rot = tuple(round(float(v), 4) + 0.0 for v in (G @ R).reshape(-1))


def _boite_locale(b, n0):
    """Boîte englobante, dans le repère courant, des pièces ajoutées depuis n0."""
    Rf, tf = _repere_courant(b)
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for p in b.parts[n0:]:
        R = Rf.T @ np.asarray(p.rot, float).reshape(3, 3)
        half = np.abs(R) @ (np.asarray(p.size, float) / 2)
        c0 = Rf.T @ (np.asarray(p.pos, float) - tf)
        lo, hi = np.minimum(lo, c0 - half), np.maximum(hi, c0 + half)
    return lo, hi


def _eclat(b, rng, x, y, z, s=1.0):
    """Éclat de verre brisé posé à plat (légèrement incliné) sur une surface à la hauteur y."""
    L, l, e = 1.3 * s, 0.8 * s, 0.12
    tilt = float(rng.uniform(6, 16))
    R = rot_y(float(rng.uniform(0, 180))) @ rot_x(tilt)
    h = 0.5 * (l * math.sin(math.radians(tilt)) + e * math.cos(math.radians(tilt)))
    return b.part("block", (L, e, l), (x, y + h, z), R, c("verre_brise"), transparency=0.4, name="Eclat", **PETIT)


def _bloc_libre(b, rng, cx, cz, sx, sy, sz, couleur, x_min=None, x_max=None, z_min=None, z_max=None, y=0.0,
                yaw=None, **kw):
    """Bloc de gravats tourné au hasard autour de Y, recalé pour rester dans les bornes données (repère courant)."""
    yaw = float(rng.uniform(0, 90)) if yaw is None else yaw
    a = math.radians(yaw)
    ex = abs(sx / 2 * math.cos(a)) + abs(sz / 2 * math.sin(a))
    ez = abs(sx / 2 * math.sin(a)) + abs(sz / 2 * math.cos(a))
    if x_min is not None:
        cx = max(cx, x_min + ex)
    if x_max is not None:
        cx = min(cx, x_max - ex)
    if z_min is not None:
        cz = max(cz, z_min + ez)
    if z_max is not None:
        cz = min(cz, z_max - ez)
    return b.boxc((cx, y + sy / 2, cz), (sx, sy, sz), _col(couleur), yaw=yaw, **kw)


# ---------------------------------------------------------------------------
# Façades vitrées abîmées
# ---------------------------------------------------------------------------

def _facade(b, rng, axe, plan, sens, t0, t1, y0, y1, *, pas=6.0, hb=1.4, bande="bleu_marine", meneau=None,
            n_meneaux=3, trous=(), p_allume=0.12, p_casse=0.25, p_brise=0.08, lumiere="fenetre_froide",
            sombre="fissure", w_men=0.5, cellules=True, sauter=()):
    """Façade vitrée posée sur un plan vertical du bâtiment.
    axe "z" : plan z = `plan`, la façade regarde `sens`·Z et s'étend sur x ∈ [t0, t1] ;
    axe "x" : plan x = `plan`, la façade regarde `sens`·X et s'étend sur z ∈ [t0, t1].
    Allèges horizontales (une par étage, saillie 0,2), meneaux verticaux (saillie 0,32) et cases de vitres
    éclairées (Neon), arrachées (sombres) ou brisées (verre translucide), en saillie 0,12.
    `trous` : rectangles (t0, t1, y0, y1) sans façade (cratère, angle arraché, au-dessus d'un sommet cassé)."""

    def bx(ta, tb, ya, yb, da, db, couleur, **kw):
        if axe == "z":
            return _d(b, (ta, ya, plan + sens * da), (tb, yb, plan + sens * db), couleur, **kw)
        return _d(b, (plan + sens * da, ya, ta), (plan + sens * db, yb, tb), couleur, **kw)

    def dans_trou(ta, tb, ya, yb):
        return any(t[0] < tb - 1e-6 and t[1] > ta + 1e-6 and t[2] < yb - 1e-6 and t[3] > ya + 1e-6 for t in trous)

    lignes = []
    y = y0
    while y + hb <= y1 + 1e-6:
        lignes.append(y)
        y += pas
    bcol = _col(bande)
    for y in lignes:
        if any(abs(y - ys) < 1e-6 for ys in sauter):
            continue
        coupes = [(t[0], t[1]) for t in trous if t[2] < y + hb - 1e-6 and t[3] > y + 1e-6]
        for ta, tb in _moins(t0, t1, coupes):
            bx(ta, tb, y, y + hb, 0.0, 0.2, bcol, name="Allege")
    tm = [t0 + (i + 1) * (t1 - t0) / (n_meneaux + 1) for i in range(n_meneaux)]
    if meneau is not None:
        mcol = _col(meneau)
        for t in tm:
            coupes = [(tr[2], tr[3]) for tr in trous if tr[0] < t + w_men / 2 and tr[1] > t - w_men / 2]
            for ya, yb in _moins(y0, y1, coupes, mini=0.8):
                bx(t - w_men / 2, t + w_men / 2, ya, yb, 0.0, 0.32, mcol, name="Meneau")
    if not cellules:
        return
    bords = [t0] + tm + [t1]
    for k, y in enumerate(lignes):
        ya = y + hb + 0.25
        yb = (lignes[k + 1] if k + 1 < len(lignes) else y1) - 0.25
        if yb - ya < 1.0:
            continue
        for i in range(len(bords) - 1):
            ta = bords[i] + (w_men / 2 + 0.2 if i > 0 else 0.4)
            tb = bords[i + 1] - (w_men / 2 + 0.2 if i < len(bords) - 2 else 0.4)
            if tb - ta < 1.0 or dans_trou(ta - 0.3, tb + 0.3, ya, yb):
                continue
            r = float(rng.random())
            if r < p_allume:
                p = bx(ta, tb, ya, yb, 0.0, 0.12, c(lumiere), material="Neon", name="VitreAllumee")
            elif r < p_allume + p_casse:
                bx(ta, tb, ya, yb, 0.0, 0.12, c(sombre), name="VitreArrachee")
            elif r < p_allume + p_casse + p_brise:
                # vitre brisée : il ne reste qu'un morceau translucide accroché en haut de la case
                yh = ya + (yb - ya) * float(rng.uniform(0.35, 0.6))
                bx(ta, tb, ya, yb, 0.0, 0.1, c(sombre), name="VitreArrachee")
                bx(ta + 0.2, tb - 0.2, yh, yb, 0.1, 0.2, c("verre_brise"), transparency=0.4, name="VitreBrisee")


def _fissure(b, rng, axe, plan, sens, t, y, *, n=3, longueur=4.0, direction=-90.0, larg=0.35, couleur="fissure",
             neon=False, d=0.22, bornes=None):
    """Fissure en zigzag sur un plan de façade (mêmes conventions que `_facade`), partant de (t, y).
    `direction` en degrés dans le plan (t, y). Les points restent dans `bornes` = (t0, t1, y0, y1)."""
    pts = [(t, y)]
    a = direction
    for _ in range(n):
        a += float(rng.uniform(-38, 38))
        L = longueur * float(rng.uniform(0.6, 1.1))
        t2 = pts[-1][0] + L * math.cos(math.radians(a))
        y2 = pts[-1][1] + L * math.sin(math.radians(a))
        if bornes:
            t2 = min(max(t2, bornes[0]), bornes[1])
            y2 = min(max(y2, bornes[2]), bornes[3])
        pts.append((t2, y2))
    normale = (0.0, 0.0, float(sens)) if axe == "z" else (float(sens), 0.0, 0.0)

    def P(tt, yy):
        return (tt, yy, plan + sens * (d + 0.11)) if axe == "z" else (plan + sens * (d + 0.11), yy, tt)

    for (ta, ya), (tb, yb) in zip(pts, pts[1:]):
        _barre(b, P(ta, ya), P(tb, yb), larg, 0.22, normale, couleur, rallonge=larg,
               material="Neon" if neon else "SmoothPlastic", name="Fissure", **PETIT)
    return pts


def _cone_gravats(b, rng, x_mur, sens, z0, z1, largeur, hauteur, *, n=9, x_lim=None, dalles=2, eclats=2,
                  lueurs=1, tons=("gravats", "gravats_clair", "gravats_fonce"), facade=None):
    """Tas de gravats contre un mur vertical (plan x = x_mur), étalé vers `sens`·X sur `largeur`,
    entre z0 et z1 ; il ne dépasse jamais x_lim (bord du couloir). Gros blocs près du mur, plus bas vers
    l'extérieur ; dalles cassées appuyées contre le mur, éclats de verre, lueur violette."""
    xa, xb = sorted((x_mur, x_mur + sens * largeur))
    if x_lim is not None:
        if sens > 0:
            xb = min(xb, x_lim)
        else:
            xa = max(xa, x_lim)
    W = xb - xa
    for k in range(n):
        f = (k + float(rng.uniform(0, 0.8))) / n          # 0 près du mur → 1 au bord du tas
        dist = 0.6 + f * (W - 1.6)
        hh = max(0.8, hauteur * (1.0 - 0.85 * f) * float(rng.uniform(0.75, 1.05)))
        sx = float(rng.uniform(1.8, 3.4)) * (1.15 - 0.4 * f)
        sz = float(rng.uniform(1.8, 3.6))
        cz = float(rng.uniform(z0 + 1.0, z1 - 1.0))
        cx = x_mur + sens * dist
        col = facade if (facade is not None and k % 4 == 1) else tons[k % len(tons)]
        _bloc_libre(b, rng, cx, cz, sx, hh, sz, vary(_col(col), rng, 0.05), x_min=xa, x_max=xb, z_min=z0, z_max=z1,
                    studs="top", name="Gravats")
    for k in range(dalles):
        # dalle cassée appuyée contre le mur
        cz = z0 + (k + 0.5) * (z1 - z0) / max(1, dalles) + float(rng.uniform(-1.0, 1.0))
        L = min(W - 0.6, hauteur * 1.1)
        haut = hauteur * float(rng.uniform(0.9, 1.25))
        p0 = (x_mur + sens * (L * 0.8), 0.25, cz)
        p1 = (x_mur + sens * 0.5, haut, cz + float(rng.uniform(-0.8, 0.8)))
        _barre(b, p0, p1, float(rng.uniform(2.4, 3.6)), 0.6, (sens * 0.6, 1.0, 0.0), vary(c("beton_clair"), rng, 0.04),
               name="DalleCassee", studs="top")
        _fer(b, p1, (p1[0] + sens * 0.6, p1[1] + 1.2, p1[2] + 0.4), (p1[0] + sens * 1.6, p1[1] + 1.6, p1[2] + 0.9),
             r=0.14)
    for k in range(eclats):
        x = xa + float(rng.uniform(0.3, 0.8)) * W
        _eclat(b, rng, x, 0.0, float(rng.uniform(z0 + 1, z1 - 1)), s=float(rng.uniform(0.9, 1.4)))
    for k in range(lueurs):
        x = xa + float(rng.uniform(0.25, 0.6)) * W
        z = float(rng.uniform(z0 + 1.5, z1 - 1.5))
        _n(b, (x - 0.6, 0.0, z - 0.9), (x + 0.6, 0.6, z + 0.9), "lueur_violette", name="Lueur")


# ---------------------------------------------------------------------------
# 1) Immeuble effondré : le repère final, la porte de sortie
# ---------------------------------------------------------------------------

PALETTES_TOUR = {
    # corps (vitrage), allèges, meneaux, socle, lumière
    "verre": ("vitre_bleue", "bleu_marine", "bleu_pale", "bleu_nuit", "fenetre_froide"),
    "marine": ("bleu_marine", "carrelage", "bleu_ardoise", "bleu_nuit", "fenetre_froide"),
    "beton": ("beton", "bleu_ardoise", "beton_fonce", "anthracite", "fenetre_chaude"),
    "chaud": ("gris_chaud", "creme", "brique_fonce", "anthracite", "fenetre_chaude"),
    "ardoise": ("bleu_ardoise", "bleu_pale", "bleu_nuit", "anthracite", "fenetre_froide"),
    "cyan": ("vitre_cyan", "bleu_acier", "beton_clair", "bleu_marine", "fenetre_froide"),
}


def immeuble_effondre(b, variant=0, passage=90, hauteur_libre=34) -> dict:
    """Immeuble effondré en arche au-dessus de la sortie (voir l'en-tête du module).
    `passage` : largeur du couloir (90 pour x ∈ [-45, 45], 64 pour l'ancien) ; `hauteur_libre` : dessous minimal
    de ce qui enjambe le couloir (le bloc tombé passe 8 studs plus haut, la cassure encore plus haut)."""
    rng = b.rng
    n0 = len(b.parts)
    v = variant % 2
    demi = passage / 2.0
    libre = demi + 1.0                    # au-dessus de |x| < libre : rien sous y = 30
    F = demi + 10.0                       # faces intérieures des moignons (alignement des façades)
    WL, WR = 48.0, 48.0                   # largeur des moignons bas (gauche) et haut (droit)
    HD = 10.5                             # demi-profondeur des moignons (détails compris : z ∈ [-11, 11])
    G, YP, PAS, HB = 9.0, 10.5, 6.0, 1.4  # rez-de-chaussée, haut du socle, hauteur d'étage, allège
    T, DK = 16.0, 9.0                     # épaisseur et demi-profondeur du haut de tour tombé
    thA, thB = 2.0, 20.0                  # inclinaisons des deux tronçons (A : côté toit, B : côté cassure)
    y_bas = hauteur_libre + 8.0           # dessous du tronçon A au bord du couloir
    xH = 8.0                              # charnière : arête haute de la cassure, au-dessus du couloir
    sA, cA = math.sin(math.radians(thA)), math.cos(math.radians(thA))
    sB, cB = math.sin(math.radians(thB)), math.cos(math.radians(thB))
    uA_lib = (-libre - xH - T * sA) / cA
    yH = y_bas - uA_lib * sA + T * cA
    Hc = np.array([xH, yH, 0.0])
    RA, RB = rot_z(thA), rot_z(thB)

    def dessous(x):
        """Dessous du haut de tour tombé à l'abscisse x (tronçon A à gauche de la cassure, B à droite)."""
        if x <= xH + T * sA:
            return yH + (x - xH - T * sA) / cA * sA - T * cA
        return yH + (x - xH - T * sB) / cB * sB - T * cB

    pal_haut, pal_bas = (PALETTES_TOUR["marine"], PALETTES_TOUR["beton"]) if v == 0 else \
        (PALETTES_TOUR["verre"], PALETTES_TOUR["chaud"])

    xL0, xL1 = -(F + WL), -F              # moignon bas (gauche)
    xR0, xR1 = F, F + WR                  # moignon haut (droit)
    x_l = xL0 - 4.0                       # le toit du haut de tour dépasse un peu du moignon bas
    x_r = F + round(0.42 * WR)            # bas de l'extrémité cassée (posée dans l'encoche du moignon haut)
    LA = -(x_l - xH - T * sA) / cA
    LB = (x_r - xH - T * sB) / cB

    with b.group("Effondre"):
        # ------------------------------------------------------------------
        # Le haut de tour tombé : deux tronçons cassés à la charnière (arête haute),
        # la cassure s'ouvre vers le bas (on la voit en courant dessous)
        # ------------------------------------------------------------------
        corps, allege, men, socle_c, lum = pal_haut
        corps_c = shade(c(corps), 0.92)

        ENC_U, ENC_V = 3.0, 6.0               # encoche de la cassure en haut de chaque tronçon (silhouette en V)

        def troncon(R, ua, ub, nom):
            def P(u, vv, w):
                return Hc + R @ np.array([u, vv, w], float)

            def blk(size, centre, couleur, **kw):
                return b.part("block", size, P(*centre), R, _col(couleur), **kw)

            with b.group(nom):
                blk((ub - ua, T - ENC_V, 2 * DK), ((ua + ub) / 2, -T / 2 - ENC_V / 2, 0), corps_c, name="CorpsTombe")
                ga, gb = (ua, ub - ENC_U) if ub <= 0 else (ua + ENC_U, ub)
                blk((gb - ga, ENC_V, 2 * DK), ((ga + gb) / 2, -ENC_V / 2, 0), corps_c, name="CorpsTombe")
                # planchers de la tour couchée : bandes perpendiculaires à la longueur (sur les 4 faces)
                pas_u = 6.0
                us = []
                u = ua + 3.5
                while u < ub - 2.5:
                    if abs(u) > ENC_U + 1.0:
                        us.append(u)
                        blk((1.3, T - 1.2, 2 * DK + 0.4), (u, -T / 2, 0), c(allege), name="Plancher", **PETIT)
                        blk((1.3, T + 0.4, 2 * DK - 1.2), (u, -T / 2, 0), shade(c(allege), 0.9), name="Plancher", **PETIT)
                    u += pas_u
                # meneaux de la tour couchée (devenus horizontaux) : 2 lignes, sur les deux grandes faces
                for vm in (-T / 3, -2 * T / 3):
                    blk((ub - ua - 3.0, 0.7, 2 * DK + 0.7), ((ua + ub) / 2, vm, 0), shade(c(men), 0.95), name="Meneau", **PETIT)
                # cases vitrées (3 rangées par travée) : éclairées, arrachées, brisées ou vitre bleue
                rangs = [(-T + 1.0, -2 * T / 3 - 0.6), (-2 * T / 3 + 0.6, -T / 3 - 0.6), (-T / 3 + 0.6, -1.0)]
                for ua_, ub_ in zip(us, us[1:]):
                    if ub_ - ua_ > pas_u + 0.5:
                        continue
                    for sw in (-1, 1):
                        for (va, vb) in rangs:
                            r = float(rng.random())
                            taille = (ub_ - ua_ - 2.2, vb - va, 0.3)
                            centre = ((ua_ + ub_) / 2, (va + vb) / 2, sw * (DK + 0.05))
                            if r < 0.13:
                                blk(taille, centre, c(lum), material="Neon", name="Vitre", **PETIT)
                            elif r < 0.45:
                                blk(taille, centre, c("fissure"), name="VitreArrachee", **PETIT)
                            elif r < 0.55:
                                blk(taille, centre, c("fissure"), name="VitreArrachee", **PETIT)
                                blk((taille[0] - 0.6, (vb - va) * 0.45, 0.2), ((ua_ + ub_) / 2, vb - (vb - va) * 0.225, sw * (DK + 0.25)),
                                    c("verre_brise"), transparency=0.4, name="VitreBrisee", **PETIT)
                            elif r < 0.7:
                                blk(taille, centre, mix(c("vitre_bleue"), c("vitre"), 0.45), name="Vitre", **PETIT)
            return P, blk

        PA, blkA = troncon(RA, -LA, 0.0, "TronconToit")
        PB, blkB = troncon(RB, 0.0, LB - 7.0, "TronconCasse")

        with b.group("Toit"):
            # toit de l'ancienne tour, à l'extrémité gauche : dalle, acrotère, local technique, citerne, antenne, feu
            ue = -LA
            blkA((0.5, T - 0.8, 2 * DK - 0.8), (ue - 0.2, -T / 2, 0), c("beton_fonce"), name="DalleToit")
            for vv in (-T + 0.4, -0.4):
                blkA((1.6, 0.8, 2 * DK), (ue - 0.6, vv, 0), c("beton_clair"), name="Acrotere", **PETIT)
            for ww in (-DK + 0.4, DK - 0.4):
                blkA((1.6, T, 0.8), (ue - 0.6, -T / 2, ww), c("beton_clair"), name="Acrotere", **PETIT)
            blkA((4.0, 6.0, 7.0), (ue - 2.2, -4.5, -3.5), c("beton"), name="LocalTechnique")
            blkA((0.3, 2.4, 1.6), (ue - 4.3, -5.8, -1.8), c("metal_fonce"), name="Porte", **PETIT)
            b.part("cyl", (3.2, 4.0, 4.0), PA(ue - 1.8, -4.0, 4.6), RA, c("citerne"), name="Citerne")
            b.part("cyl", (0.3, 4.2, 4.2), PA(ue - 3.5, -4.0, 4.6), RA, shade(c("citerne"), 0.8), name="Couvercle", **PETIT)
            _tige(b, PA(ue - 0.5, -11.5, 0.0), PA(ue - 9.0, -9.8, 1.4), 0.25, c("metal_clair"), name="Antenne")
            _tige(b, PA(ue - 6.0, -10.5, 0.9), PA(ue - 6.0, -8.5, 2.8), 0.15, c("metal_clair"), name="Antenne")
            blkA((0.9, 0.9, 0.9), (ue - 9.2, -9.6, 1.4), c("rouge_balise"), material="Neon", name="Balise", **PETIT)
            blkA((0.8, T + 0.5, 2 * DK + 0.5), (ue + 2.0, -T / 2, 0), c("neon_cyan"), material="Neon", name="Couronne", **PETIT)
            # gravats tombés sur le tronçon presque plat
            for k in range(4):
                u = float(rng.uniform(-LA + 10, -12))
                s = float(rng.uniform(1.6, 3.0))
                b.part("block", (s, s * 0.6, s * 0.9), PA(u, s * 0.3 - 0.1, float(rng.uniform(-DK + 2, DK - 2))),
                       RA @ rot_y(float(rng.uniform(0, 90))), vary(c(("gravats", "gravats_clair", "gravats_fonce")[k % 3]), rng),
                       studs="top", name="Gravats", **PETIT)
            # dalle arrachée dressée sur le dessus et fers
            p0 = PA(-34.0, -0.2, -2.0)
            p1 = PA(-28.0, 5.0, 1.0)
            _barre(b, p0, p1, 5.0, 0.7, RA @ np.array([0.6, 0.3, 0.0]), c("beton_clair"), name="DalleDressee", studs="top")
            for k in range(3):
                q = PA(float(rng.uniform(-60, -20)), 0.0, float(rng.uniform(-DK + 1, DK - 1)))
                _fer(b, q, q + np.array([0.6, 2.2, 0.3]), q + np.array([2.0, 3.0, float(rng.uniform(-1, 1))]))

        with b.group("Cassure"):
            # faces de la cassure : intérieur sombre, planchers à nu, fers tendus d'un tronçon à l'autre, lueur violette
            blkA((0.4, T - ENC_V - 0.6, 2 * DK - 0.6), (-0.25, -T / 2 - ENC_V / 2, 0), c("fissure"), name="Interieur", **PETIT)
            blkB((0.4, T - ENC_V - 0.6, 2 * DK - 0.6), (0.25, -T / 2 - ENC_V / 2, 0), c("fissure"), name="Interieur", **PETIT)
            # encoche en V : faces sombres, dalles à nu et lueur au fond
            blkA((0.4, ENC_V - 0.3, 2 * DK - 0.6), (-ENC_U - 0.25, -ENC_V / 2, 0), c("fissure"), name="Interieur", **PETIT)
            blkB((0.4, ENC_V - 0.3, 2 * DK - 0.6), (ENC_U + 0.25, -ENC_V / 2, 0), c("fissure"), name="Interieur", **PETIT)
            blkA((ENC_U + 0.4, 0.7, 2 * DK - 2.0), (-ENC_U / 2, -ENC_V + 0.35, 0), c("beton_clair"), name="DalleANu", studs="top")
            blkB((ENC_U + 0.4, 0.7, 2 * DK - 2.0), (ENC_U / 2, -ENC_V + 0.35, 0), c("beton_clair"), name="DalleANu", studs="top")
            blkA((1.2, 1.0, 2 * DK - 6.0), (-1.0, -ENC_V + 1.2, 0), c("lueur_violette"), material="Neon", name="Lueur", **PETIT)
            blkB((1.2, 1.0, 2 * DK - 6.0), (1.0, -ENC_V + 1.2, 0), c("lueur_violette"), material="Neon", name="Lueur", **PETIT)
            for k in range(4):
                ww = float(rng.uniform(-DK + 1.5, DK - 1.5))
                q0 = PA(-ENC_U + 0.2, float(rng.uniform(-ENC_V + 1, -0.5)), ww)
                q1 = PB(ENC_U - 0.2, float(rng.uniform(-ENC_V + 1, -0.5)), ww + float(rng.uniform(-1, 1)))
                mid = (q0 + q1) / 2 + np.array([0.0, float(rng.uniform(1.0, 2.5)), 0.0])
                _tige(b, q0, mid, 0.16, c("ferraille"), name="Fer")
                _tige(b, mid, q1, 0.16, c("ferraille"), name="Fer")
            for (vv, ww, lg) in ((-4.0, -3.0, 1.0), (-9.0, 4.0, 1.6), (-13.5, -1.0, 2.2)):
                blkA((lg, 0.7, 7.0), (lg / 2 - 0.2, vv, ww), c("beton_clair"), name="DalleANu")
                blkB((lg * 0.8, 0.7, 6.0), (-lg * 0.4 + 0.2, vv - 0.6, -ww), c("beton_clair"), name="DalleANu")
            for k in range(9):
                vv = float(rng.uniform(-T + 1.0, -1.5))
                ww = float(rng.uniform(-DK + 1, DK - 1))
                a = PA(-0.2, vv, ww)
                bb = PB(0.2, vv, ww + float(rng.uniform(-1, 1)))
                m = (a + bb) / 2 + np.array([0.0, -0.4 - 0.08 * abs(vv), 0.0])
                _tige(b, a, m, 0.16, c("ferraille"), name="Fer")
                _tige(b, m, bb, 0.16, c("ferraille"), name="Fer")
            for (vv, ww) in ((-6.0, -4.0), (-11.0, 3.0), (-14.0, -6.0)):
                _barre(b, PA(-0.3, vv, ww), PB(0.3, vv, ww), 0.7, 0.7, (0, 0, 1), c("lueur_violette"), material="Neon",
                       name="Lueur", **PETIT)
            # dents de béton et de façade arrachées qui avancent dans la cassure (silhouette déchiquetée)
            for (lg, hh, ww, wd) in ((1.8, 3.5, -5.5, 5.0), (1.2, 6.0, 2.0, 4.0), (2.2, 2.4, 6.5, 3.5)):
                blkA((lg, hh, wd), (lg / 2 - 0.1, -T + hh / 2, ww), vary(c("gravats_clair"), rng, 0.04), name="Dent")
            for (lg, hh, ww, wd) in ((1.6, 4.5, 4.5, 6.0), (2.0, 2.6, -3.0, 4.5)):
                blkB((lg, hh, wd), (-lg / 2 + 0.1, -T + hh / 2, ww), vary(c("gravats"), rng, 0.04), name="Dent")
            # dalle de plancher qui pend sous la cassure, retenue par ses fers (au-dessus de hauteur_libre + 4)
            q = PB(1.2, -T, -1.0)
            bas_dalle = max(hauteur_libre + 4.0, q[1] - 6.5)
            bout = np.array([q[0] - 2.2, bas_dalle, q[2] + 1.0])
            _barre(b, q + np.array([0.0, -1.0, 0.0]), bout, 4.5, 0.6, (1.0, 0.4, 0.0), vary(c("beton_clair"), rng, 0.03),
                   name="DallePendante", **PETIT)
            for dw in (-1.6, 0.0, 1.6):
                _tige(b, PB(0.8, -T + 0.2, -1.0 + dw), q + np.array([0.0, -1.0, dw]), 0.14, c("ferraille"), name="Fer")
            for sw in (-1, 1):
                _barre(b, PA(-0.5, -1.5, sw * 6.0), PA(-0.5, -T + 1.5, sw * 3.0), 0.6, 0.3, RA @ np.array([1.0, 0, 0]),
                       c("lueur_violette"), material="Neon", name="Lueur", **PETIT)
            # fers qui pendent sous la cassure (au-dessus du couloir : jamais sous hauteur_libre + 3)
            for (vv, ww, chute) in ((-T, -5.0, 5.0), (-T, 2.5, 7.0), (-T, 6.5, 4.0)):
                a = PB(0.6, vv, ww)
                fin = max(hauteur_libre + 3.0, a[1] - chute)
                _fer(b, a, (a[0] - 0.4, (a[1] + fin) / 2, a[2] + 0.3), (a[0] + 0.3, fin, a[2] - 0.2), r=0.15)

        with b.group("Arrachement"):
            # extrémité arrachée du tronçon B : dalles à nu, poteaux, intérieur sombre, fers tordus
            ut = LB - 7.0
            blkB((0.4, T - 1.0, 2 * DK - 1.0), (ut + 0.1, -T / 2, 0), c("fissure"), name="Interieur", **PETIT)
            for (du, (va, vb), (wa, wb)) in ((1.2, (-T, -3.0), (-DK, DK - 5.0)), (3.6, (-T + 2, 0.0), (-DK + 3.0, DK)),
                                             (5.9, (-T, -6.5), (-DK + 1.0, DK - 2.0))):
                blkB((0.9, vb - va, wb - wa), (ut + du, (va + vb) / 2, (wa + wb) / 2), c("beton_clair"), name="DalleCassee")
            for (vv, ww, lu) in ((-T + 0.7, -DK + 0.7, 6.4), (-0.7, DK - 0.7, 4.2), (-T + 0.7, DK - 0.7, 2.6), (-0.7, -DK + 0.7, 5.2)):
                blkB((lu, 1.4, 1.4), (ut + lu / 2, vv, ww), c("beton"), name="Poteau")
            for k in range(6):
                vv = float(rng.uniform(-T + 1.5, -1.5))
                ww = float(rng.uniform(-DK + 1.5, DK - 1.5))
                _fer(b, PB(ut + 1.5, vv, ww), PB(ut + 4.0 + float(rng.uniform(0, 2)), vv + float(rng.uniform(-1.5, 2.5)), ww),
                     PB(ut + 6.0 + float(rng.uniform(0, 2)), vv + float(rng.uniform(-3, 3)), ww + float(rng.uniform(-2, 2))), r=0.18)

        with b.group("Fissures"):
            # fissures violettes lumineuses : grandes faces des deux tronçons et dessous (vu en courant dessous)
            for (P_, R_, ua, ub) in ((PA, RA, -LA + 12, -6.0), (PB, RB, 6.0, LB - 12)):
                for sw in (-1, 1):
                    u0 = float(rng.uniform(ua, ub))
                    pts = [(u0, -0.8)]
                    a = -90.0 + float(rng.uniform(-25, 25))
                    for _ in range(3):
                        a += float(rng.uniform(-40, 40))
                        Ls = float(rng.uniform(3.0, 5.0))
                        pts.append((pts[-1][0] + Ls * math.cos(math.radians(a)),
                                    max(-T + 0.6, min(-0.6, pts[-1][1] + Ls * math.sin(math.radians(a))))))
                    for (u1, v1), (u2, v2) in zip(pts, pts[1:]):
                        _barre(b, P_(u1, v1, sw * (DK + 0.35)), P_(u2, v2, sw * (DK + 0.35)), 0.5, 0.25,
                               R_ @ np.array([0.0, 0.0, sw]), c("lueur_violette"), rallonge=0.5, material="Neon",
                               name="Fissure", **PETIT)
                w0 = float(rng.uniform(-3, 3))
                pts = [(ua + 4.0, w0)]
                for _ in range(4):
                    pts.append((pts[-1][0] + float(rng.uniform(4, 7)), max(-DK + 1, min(DK - 1, pts[-1][1] + float(rng.uniform(-4, 4))))))
                for (u1, w1), (u2, w2) in zip(pts, pts[1:]):
                    _barre(b, P_(u1, -T - 0.35, w1), P_(u2, -T - 0.35, w2), 0.5, 0.25, R_ @ np.array([0.0, -1.0, 0.0]),
                           c("lueur_violette"), rallonge=0.5, material="Neon", name="Fissure", **PETIT)

        # ------------------------------------------------------------------
        # Moignons de tours : corps en colonnes (cœur + couche avant, pour de vrais trous)
        # ------------------------------------------------------------------
        def corps_colonnes(colonnes, trous_av, couleur, nom):
            """colonnes : (xa, xb, sommet, ef) ; la couche avant z ∈ [HD - ef, HD] est privée des `trous_av`."""
            for (xa, xb, yt, ef) in colonnes:
                b.box((xa, YP, -HD), (xb, yt, HD - ef), couleur, studs="top", name=nom)
                for (pa, pb, qa, qb) in _rects_moins(xa, xb, YP, yt, trous_av):
                    b.box((pa, qa, HD - ef), (pb, qb, HD), couleur, studs="top", name=nom)

        def socle_et_rdc(x0, x1, pal, cote_couloir):
            """Rez-de-chaussée éventré (intérieur sombre en retrait, piliers, vitres brisées) et bandeau de socle."""
            b.box((x0 + 1.2, 0, -HD + 1.2), (x1 - 1.2, G, HD - 1.2), shade(c("vitre"), 0.7), name="HallSombre")
            b.box((x0 - 0.2, G, -HD - 0.2), (x1 + 0.2, YP, HD + 0.2), vary(c(pal[3]), rng, 0.03), studs="top", name="Socle")
            for x in (x0 + 0.6, x1 - 0.6, (x0 + x1) / 2 - 8, (x0 + x1) / 2 + 8):
                for z in (-HD + 0.6, HD - 0.6):
                    b.box((x - 0.6, 0, z - 0.6), (x + 0.6, G, z + 0.6), c("beton_clair"), name="Pilier")
            xc = x1 if cote_couloir > 0 else x0
            for z in (-3.5, 3.5):
                b.box((xc - 0.6, 0, z - 0.6), (xc + 0.6, G, z + 0.6), c("beton_clair"), name="Pilier")
            xg = xc - cote_couloir * 0.9
            for (za, zb_) in ((-HD + 1.6, -4.3), (4.3, HD - 1.6)):
                _d(b, (xg - 0.1, G - 3.2, za), (xg + 0.1, G - 0.2, zb_), c("verre_brise"), transparency=0.4, name="VitreHall")
            for (xa, xb) in ((x0 + 1.6, (x0 + x1) / 2 - 8.8), ((x0 + x1) / 2 + 8.8, x1 - 1.6)):
                _d(b, (xa, G - 2.6, HD - 0.95), (xb, G - 0.2, HD - 0.75), c("verre_brise"), transparency=0.4, name="VitreHall")

        def interieur(xa, xb, ya, yb, z, sens_z=1):
            """Fond sombre d'un trou (plan z), avec lueur violette."""
            _d(b, (xa, ya, z - 0.6), (xb, yb, z + 0.12), c("fissure"), name="Interieur")

        def facades(x0, x1, colonnes, trous_av, trous_couloir, pal, cote_couloir, n_men=6):
            corps_col, allege_c, men_c, _, lum_c = pal
            ymax = max(cl[2] for cl in colonnes)
            sommets = [(xa, xb, yt, ymax + 1) for (xa, xb, yt, _) in colonnes]
            _facade(b, rng, "z", HD, 1, x0, x1, YP + 0.6, ymax, pas=PAS, hb=HB, bande=allege_c, meneau=men_c,
                    n_meneaux=n_men, trous=sommets + list(trous_av), p_allume=0.13, p_casse=0.28, p_brise=0.1, lumiere=lum_c)
            _facade(b, rng, "z", -HD, -1, x0, x1, YP + 0.6, ymax, pas=PAS, hb=HB, bande=allege_c, meneau=men_c,
                    n_meneaux=n_men, trous=sommets, p_allume=0.08, p_casse=0.2, p_brise=0.05, lumiere=lum_c)
            xc, xe = (x1, x0) if cote_couloir > 0 else (x0, x1)
            yc = [cl[2] for cl in colonnes if abs((cl[1] if cote_couloir > 0 else cl[0]) - xc) < 1e-6][0]
            ye = [cl[2] for cl in colonnes if abs((cl[0] if cote_couloir > 0 else cl[1]) - xe) < 1e-6][0]
            _facade(b, rng, "x", xc, cote_couloir, -HD, HD, YP + 0.6, yc, pas=PAS, hb=HB, bande=allege_c, meneau=men_c,
                    n_meneaux=3, trous=trous_couloir, p_allume=0.14, p_casse=0.32, p_brise=0.1, lumiere=lum_c)
            _facade(b, rng, "x", xe, -cote_couloir, -HD, HD, YP + 0.6, ye, pas=PAS, hb=HB, bande=allege_c, meneau=None,
                    cellules=False)

        def dalle_a_nu(xa, xb, y, za, zb_, deb=1.2):
            b.box((xa - deb, y - 0.8, za), (xb + deb, y, zb_), vary(c("beton_clair"), rng, 0.04), studs="top", name="DalleANu")

        def fers_sommet(xa, xb, yt, n=3):
            for k in range(n):
                xx = float(rng.uniform(xa + 0.8, xb - 0.8))
                zz = float(rng.uniform(-HD + 1.5, HD - 1.5))
                _fer(b, (xx, yt, zz), (xx + float(rng.uniform(-1, 1)), yt + 2.2, zz + float(rng.uniform(-0.6, 0.6))),
                     (xx + float(rng.uniform(-2, 2)), yt + 3.4, zz + float(rng.uniform(-1.5, 1.5))))

        # --- moignon bas (gauche) : sommet écrasé sous le tronçon A, angle avant côté couloir effondré ---
        with b.group("MoignonBas"):
            socle_et_rdc(xL0, xL1, pal_bas, +1)
            col_bas = vary(shade(c(pal_bas[0]), 0.92), rng, 0.02)
            xm = xL1 - 16.0
            colonnes = [(xL0, xL0 + 16, dessous(xL0 + 16) + 0.3 + 0.8, 3.0), (xL0 + 16, xm, dessous(xm) + 0.3 + 0.2, 3.0),
                        (xm, xm + 8, dessous(xm + 8) + 0.3, 8.5), (xm + 8, xL1, dessous(xL1) + 0.3, 8.5)]
            angle = [(xm, xm + 8, 31.0, 60.0), (xm + 8, xL1, 22.5, 60.0)]          # angle effondré (face avant)
            corps_colonnes(colonnes, angle, col_bas, "Moignon")
            facades(xL0, xL1, colonnes, angle, [(HD - 8.5, HD, 22.5, 60.0)], pal_bas, +1)
            # intérieur de l'angle effondré : fond sombre, planchers cassés, fers, gravats, lueur
            interieur(xm, xL1, 22.5, dessous(xm) + 0.2, HD - 8.5)
            _d(b, (xm + 8 - 0.12, 22.5, HD - 8.5), (xm + 8 + 0.6, 31.0, HD), c("fissure"), name="Interieur")
            for k, y in enumerate((28.5, 34.5, 40.0)):
                if y < dessous(xm) - 0.5:
                    deb = (3.2, 2.0, 4.2)[k]
                    xa = xm + (0.0 if y > 31 else 8.0)
                    b.box((xa, y - 0.8, HD - 8.5), (xL1 - float(rng.uniform(0.5, 3.0)), y, HD - 8.5 + deb),
                          vary(c("beton_clair"), rng, 0.04), studs="top", name="DalleANu")
                    for j in range(2):
                        xx = float(rng.uniform(xa + 1, xL1 - 3))
                        zz = HD - 8.5 + deb
                        _fer(b, (xx, y - 0.4, zz - 0.3), (xx + 0.4, y - 0.1, zz + 0.9), (xx + 0.9, y - 1.4, zz + 1.6))
            for (xa, xb, yt) in ((xm, xm + 8, 31.0), (xm + 8, xL1, 22.5)):
                for k in range(2):
                    _bloc_libre(b, rng, float(rng.uniform(xa + 1, xb - 1)), HD - 3.0, float(rng.uniform(1.6, 2.6)),
                                float(rng.uniform(0.8, 1.4)), float(rng.uniform(1.4, 2.4)), vary(c("gravats"), rng), y=yt,
                                x_min=xa, x_max=xb, z_min=HD - 8.5, z_max=HD, studs="top", name="Gravats", **PETIT)
            _fissure(b, rng, "z", HD - 8.5 - 0.1, 1, xm + 6, 36.0, n=3, longueur=4.0, direction=-80.0, neon=True,
                     couleur="lueur_violette", larg=0.55, d=0.15, bornes=(xm + 0.5, xL1 - 0.5, 23.0, dessous(xm) - 0.5))
            # mur arrière déchiqueté qui monte derrière le tronçon A (jusqu'à ~64)
            dents = [(xL0, xL0 + 7, 64.0), (xL0 + 7, xL0 + 14, 58.0), (xL0 + 14, xL0 + 22, 52.0)]
            y_ext = dessous(xL0 + 22) - 1.0
            for (xa, xb, yt) in dents:
                b.box((xa, y_ext, -HD), (xb, yt, -HD + 3.0), col_bas, studs="top", name="MurCasse")
                fers_sommet(xa, xb, yt, n=2)
            sous = [(xa, xb, 0.0, yt + 0.05) for (xa, xb, yt, _) in colonnes]
            y_mur = max(yt for (xa, xb, yt, _) in colonnes if xa < xL0 + 22) + 0.3
            _facade(b, rng, "z", -HD, -1, xL0, xL0 + 22, y_mur, 64.0, pas=PAS, hb=HB, bande=pal_bas[1], meneau=pal_bas[2],
                    n_meneaux=3, trous=[(xa, xb, yt, 65) for (xa, xb, yt) in dents] + sous, p_allume=0.1, p_casse=0.3)
            _facade(b, rng, "x", xL0, -1, -HD, -HD + 3.0, y_mur, 64.0, pas=PAS, hb=HB, bande=pal_bas[1], cellules=False)
            # fissures violettes autour de l'appui (face avant, face côté couloir) et fissures sombres
            for (t, y, dirn) in ((xL0 + 30, 38.0, -100.0), (xL0 + 8, 36.0, -70.0)):
                _fissure(b, rng, "z", HD, 1, t, y, n=3, longueur=5.5, direction=dirn, neon=True, couleur="lueur_violette",
                         larg=0.55, bornes=(xL0 + 1, xm - 1, YP + 1, 40))
            _fissure(b, rng, "x", xL1, 1, -2.0, dessous(xL1) - 1.0, n=3, longueur=5.0, direction=-95.0, neon=True,
                     couleur="lueur_violette", larg=0.55, bornes=(-HD + 1, HD - 9.5, YP + 1, 44))
            _fissure(b, rng, "z", HD, 1, xL0 + 20, 26.0, n=3, longueur=4.0, direction=-60.0, bornes=(xL0 + 1, xm - 1, YP + 1, 40))

        # --- moignon haut (droit) : encoche où s'appuie le tronçon B, cratère, sommet déchiqueté ~95 ---
        with b.group("MoignonHaut"):
            socle_et_rdc(xR0, xR1, pal_haut, -1)
            col_haut = vary(shade(c(pal_haut[0]), 0.95), rng, 0.02)
            x_enc = x_r + 8.0
            colonnes = []
            x = xR0
            while x + 6.0 <= x_enc + 0.5:
                colonnes.append((x, x + 6.0, dessous(x + 6.0) + 0.3, 3.0))
                x += 6.0
            if x < x_enc - 0.5:
                colonnes.append((x, x_enc, dessous(x_enc) + 0.3, 3.0))
                x = x_enc
            sommets = [(x, x + 6.0, 86.0), (x + 6.0, x + 13.0, 95.0), (x + 13.0, xR1, 90.0)]
            colonnes += [(xa, xb, yt, 3.0) for (xa, xb, yt) in sommets if xb - xa > 0.5]
            # cratère dans la face avant, à mi-hauteur
            xc, yc = xR0 + 18.0, 33.0
            crat = [(xc - 7.0, xc + 6.0, yc - 5.0, yc + 5.0), (xc - 5.0, xc + 7.5, yc + 5.0, yc + 7.5),
                    (xc - 3.0, xc + 4.0, yc + 7.5, yc + 9.5), (xc - 6.0, xc + 3.5, yc - 7.5, yc - 5.0),
                    (xc - 2.5, xc + 1.5, yc - 9.5, yc - 7.5), (xc + 6.0, xc + 8.5, yc - 2.5, yc + 3.5),
                    (xc - 9.0, xc - 7.0, yc - 1.5, yc + 3.0)]
            corps_colonnes(colonnes, crat, col_haut, "Moignon")
            facades(xR0, xR1, colonnes, crat, [], pal_haut, -1)
            interieur(xc - 9.5, xc + 9.0, yc - 10.0, yc + 10.0, HD - 3.0)
            for y in (28.5, 34.5, 40.5):
                xa = xc - float(rng.uniform(3.5, 6.5))
                xb = xc + float(rng.uniform(2.5, 6.0))
                b.box((xa, y - 0.8, HD - 3.0), (xb, y, HD - float(rng.uniform(0.3, 1.2))), vary(c("beton_clair"), rng, 0.03),
                      studs="top", name="DalleCassee")
                xx = float(rng.uniform(xa + 0.5, xb - 0.5))
                _fer(b, (xx, y - 0.4, HD - 1.0), (xx + 0.4, y - 0.2, HD + 0.1), (xx - 0.3, y - 1.4, HD + 0.2))
            _n(b, (xc - 2.0, yc - 2.0, HD - 3.25), (xc + 2.0, yc + 1.6, HD - 3.0), "lueur_rose", name="Coeur")
            for dirn in (30.0, 160.0, -100.0, 80.0):
                _fissure(b, rng, "z", HD - 3.0, 1, xc, yc, n=2, longueur=4.0, direction=dirn, neon=True,
                         couleur="lueur_violette", larg=0.5, d=0.0, bornes=(xc - 8, xc + 7.5, yc - 9, yc + 9))
            for (t, y, dirn) in ((xc - 9.0, yc + 2.0, 160.0), (xc + 8.5, yc - 1.0, -20.0), (xc - 1.0, yc - 9.5, -95.0),
                                 (xc + 2.0, yc + 9.5, 75.0)):
                _fissure(b, rng, "z", HD, 1, t, y, n=2, longueur=3.5, direction=dirn, larg=0.4,
                         bornes=(xR0 + 0.5, xR1 - 0.5, YP + 1, 85))
            # mur arrière déchiqueté qui monte derrière le tronçon B (il le « coince »)
            y_enc = dessous(xR0) + 0.3
            dents = [(xR0 + 3.0, xR0 + 11.0, 80.0), (xR0 + 11.0, xR0 + 19.0, 86.0), (xR0 + 19.0, x_enc, 91.0)]
            for (xa, xb, yt) in dents:
                b.box((xa, y_enc, -HD), (xb, yt, -HD + 2.0), col_haut, studs="top", name="MurCasse")
                fers_sommet(xa, xb, yt, n=1)
            sous = [(xa, xb, 0.0, yt + 0.05) for (xa, xb, yt, _) in colonnes]
            _facade(b, rng, "z", -HD, -1, xR0 + 3.0, x_enc, y_enc + 0.5, 91.0, pas=PAS, hb=HB, bande=pal_haut[1],
                    meneau=pal_haut[2], n_meneaux=3, trous=[(xa, xb, yt, 92) for (xa, xb, yt) in dents] + sous, p_allume=0.1,
                    p_casse=0.3)
            # planchers à nu, fers et feu d'obstacle au sommet cassé
            for (xa, xb, yt) in sommets:
                dalle_a_nu(xa, xb, yt - 3.0, -HD + 1.0, HD - 1.0, deb=1.2)
                fers_sommet(xa, xb, yt, n=3)
            _n(b, (xR1 - 5.0, 90.0, -2.0), (xR1 - 3.8, 91.2, -0.8), "rouge_balise", name="Balise")
            # impact : fissures violettes qui rayonnent sous l'appui du tronçon B
            for (t, y, dirn) in ((xR0 + 4, dessous(xR0 + 4) - 1.0, -100.0), (xR0 + 26, dessous(xR0 + 26) - 1.0, -70.0),
                                 (xR1 - 10, 80.0, -110.0)):
                _fissure(b, rng, "z", HD, 1, t, y, n=3, longueur=5.5, direction=dirn, neon=True, couleur="lueur_violette",
                         larg=0.55, bornes=(xR0 + 1, xR1 - 1, YP + 1, 88))
            _fissure(b, rng, "x", xR0, -1, -1.0, dessous(xR0) - 1.0, n=4, longueur=5.0, direction=-85.0, neon=True,
                     couleur="lueur_violette", larg=0.55, bornes=(-HD + 1, HD - 1, YP + 1, 58))

        # ------------------------------------------------------------------
        # Pendants : câbles et poutre (au-dessus du couloir, jamais sous hauteur_libre + 2)
        # ------------------------------------------------------------------
        with b.group("Pendants"):
            for (x, chute, dz) in ((-30.0, 7.0, 4.0), (-24.0, 4.5, -3.0), (24.0, 6.0, 5.5), (34.0, 8.0, -5.0)):
                y0 = dessous(x) - 0.2
                y_fin = max(hauteur_libre + 3.0, y0 - chute)
                _tige(b, (x, y0, dz), (x + 0.6, (y0 + y_fin) / 2, dz + 0.3), 0.2, c("cable"), name="Cable")
                _tige(b, (x + 0.6, (y0 + y_fin) / 2, dz + 0.3), (x + 0.3, y_fin, dz + 0.6), 0.2, c("cable"), name="Cable")
            # poutre d'acier tordue qui pend de l'extrémité basse, au-dessus du trottoir gauche
            xp = -(libre + 4.0)
            yp0 = dessous(xp) - 0.2
            _barre(b, (xp, yp0, 6.5), (xp - 1.5, yp0 - 9.0, 7.5), 0.9, 0.5, (0, 0, 1), c("metal_fonce"), name="Poutre", **PETIT)
            _barre(b, (xp - 1.5, yp0 - 9.0, 7.5), (xp - 0.5, yp0 - 14.0, 8.5), 0.9, 0.5, (0, 0, 1), c("metal_fonce"),
                   name="Poutre", **PETIT)

        # ------------------------------------------------------------------
        # Tas de gravats au pied des moignons (trottoirs |x| ∈ [libre + 0,5 ; F], jamais dans le couloir)
        # ------------------------------------------------------------------
        with b.group("Gravats"):
            _cone_gravats(b, rng, xL1, +1, -HD + 0.5, HD - 0.5, F - libre - 0.5, 7.5, n=11, x_lim=-(libre + 0.5),
                          dalles=2, eclats=3, lueurs=2, facade=pal_bas[0])
            _cone_gravats(b, rng, xR0, -1, -HD + 0.5, HD - 0.5, F - libre - 0.5, 8.5, n=11, x_lim=libre + 0.5,
                          dalles=2, eclats=3, lueurs=2, facade=pal_haut[0])
            for (x0, x1, col) in ((xL0 + 4, xL1 - 4, pal_bas[0]), (xR0 + 4, xR1 - 4, pal_haut[0])):
                for k in range(4):
                    x = float(rng.uniform(x0, x1))
                    _bloc_libre(b, rng, x, HD - 1.5, float(rng.uniform(2, 3.5)), float(rng.uniform(1.0, 2.2)),
                                float(rng.uniform(1.5, 2.6)), vary(c(("gravats", "gravats_clair", "gravats_fonce")[k % 3]), rng),
                                z_max=HD, x_min=x0, x_max=x1, studs="top", name="Gravats")

    if v == 1:
        _miroir_x(b, n0)
    return {"emprise": (2 * (F + max(WL, WR)) + 8, 2 * HD), "hauteur": 98.0,
            "dessous_min_couloir": round(min(dessous(-libre), dessous(libre)), 1), "passage_sortie": 2 * F}



# ---------------------------------------------------------------------------
# 2) Dôme de barrière
# ---------------------------------------------------------------------------

def voile_dome(b, variant=0, rayon=72) -> dict:
    """Dôme de barrière violet nuit en gradins (forme générique, sans texte ni motif)."""
    rng = b.rng
    r = float(rayon)
    v = variant % 2
    grand = r >= 60
    n = 10 if grand else 8                                   # anneaux + calotte
    segs = [20, 20, 20, 20, 20, 16, 16, 12, 12] if grand else [16] * (n - 2) + [12]
    h = r / n
    r_eff = r - 1.2
    R = [r_eff * math.sqrt(max(0.0, 1.0 - ((k + 0.5) / n) ** 2)) for k in range(n)]
    haut = mix(c("voile_clair"), c("voile_bord"), 0.3)
    tons = ([mix(c("voile"), c("voile_moyen"), 0.5), c("voile_moyen"), c("voile_clair"), haut] if v == 0 else
            [c("voile_moyen"), c("voile_moyen"), c("voile_clair"), haut])
    off = float(rng.uniform(0, 360))
    coutures = {2, 5, 7} if grand else {2, 4, 6}
    meridiens = 5 if grand else 8
    k_mer = 4 if grand else 1
    with b.group("Voile"):
        for k in range(n - 1):
            N = segs[k]
            t_k = max(2.0, R[k] - R[k + 1] + 2.0)
            w_k = 2 * R[k] * math.tan(math.pi / N) + 0.05
            y0 = k * h - (0.5 if k else 0.0)
            y1 = (k + 1) * h
            f = k / (n - 2)
            base = tons[0] if f < 0.3 else tons[1] if f < 0.6 else tons[2] if f < 0.9 else tons[3]
            for j in range(N):
                a = math.radians(off) + 2 * math.pi * j / N
                rm = R[k] - t_k / 2
                b.boxc((rm * math.sin(a), (y0 + y1) / 2, rm * math.cos(a)), (w_k, y1 - y0, t_k), vary(base, rng, 0.04),
                       yaw=math.degrees(a), transparency=0.34, studs="top", name="Anneau")
            if k in coutures:
                # liseré lumineux en haut de l'anneau
                wc = 2 * (R[k] + 0.3) * math.tan(math.pi / N) + 0.05
                for j in range(N):
                    a = math.radians(off) + 2 * math.pi * j / N
                    b.boxc(((R[k] + 0.15) * math.sin(a), y1 - 0.65, (R[k] + 0.15) * math.cos(a)), (wc, 0.8, 0.3),
                           c("voile_bord"), yaw=math.degrees(a), material="Neon", name="Liseré", **PETIT)
            if k <= k_mer:
                # méridiens lumineux (quadrillage de champ de force), alignés sur les centres de dalles
                for m in range(meridiens):
                    j = m * N // meridiens
                    a = math.radians(off) + 2 * math.pi * j / N
                    ya, yb = k * h + 0.3, (k + 1) * h - 0.3
                    b.boxc(((R[k] + 0.15) * math.sin(a), (ya + yb) / 2, (R[k] + 0.15) * math.cos(a)), (0.6, yb - ya, 0.3),
                           c("voile_bord"), yaw=math.degrees(a), material="Neon", name="Meridien", **PETIT)
        # anneau lumineux au sol, aligné sur l'anneau du bas
        N0 = segs[0]
        for j in range(N0):
            a = math.radians(off) + 2 * math.pi * j / N0
            w0 = 2 * (R[0] + 1.0) * math.tan(math.pi / N0) + 0.05
            b.boxc(((R[0] + 0.5) * math.sin(a), 0.25, (R[0] + 0.5) * math.cos(a)), (w0, 0.5, 1.0), c("lueur_violette"),
                   yaw=math.degrees(a), material="Neon", name="AnneauSol", **PETIT)
        # calotte opaque plus sombre, en deux gradins, cerclée d'un anneau lumineux ; lueur au centre (vue à travers le voile)
        yc0 = (n - 1) * h - 0.5
        b.cyl((0, yc0 + (h + 0.5) / 2, 0), R[n - 1] + 1.0, h + 0.5, shade(c("voile"), 0.8), studs="top", name="Calotte")
        b.cyl((0, yc0 + h * 0.55, 0), R[n - 1] + 1.4, 0.7, c("voile_bord"), material="Neon", name="AnneauCalotte", **PETIT)
        b.cyl((0, n * h + h * 0.2, 0), R[n - 1] * 0.55, h * 0.4, shade(c("voile"), 0.65), studs="top", name="Calotte")
        b.cyl((0, 0.15, 0), r * 0.28, 0.3, c("lueur_violette"), material="Neon", name="LueurCentre", **PETIT)
    return {"emprise": (2 * r, 2 * r), "hauteur": n * h + 0.5}


# ---------------------------------------------------------------------------
# 3) Tour de bureaux endommagée
# ---------------------------------------------------------------------------

def tour_endommagee(b, variant=0, largeur=26, profondeur=32, hauteur=70) -> dict:
    """Tour de verre abîmée (voir l'en-tête). Avant = -Z ; variantes paires : hall éventré, angle arraché
    en haut à gauche (l'avant et la face gauche se voient) ; impaires : boutiques aux rideaux baissés, angle
    arraché en haut à droite."""
    rng = b.rng
    v = variant % 4
    W, D, H = float(largeur), float(profondeur), float(hauteur)
    hw, hd = W / 2, D / 2
    zf, zb = -hd, hd
    G, YP, PAS, HB = 9.0, 10.5, 6.5, 1.4
    EF = 3.0                                      # épaisseur de la couche de façade avant (cratère)
    pal = (PALETTES_TOUR["verre"], PALETTES_TOUR["marine"], PALETTES_TOUR["cyan"], PALETTES_TOUR["ardoise"])[v]
    corps_c = vary(shade(c(pal[0]), 0.88), rng, 0.02)
    allege_c, men_c, socle_c, lum_c = pal[1], pal[2], pal[3], pal[4]
    cx = -1 if v % 2 == 0 else 1                  # côté de l'angle arraché

    # lignes d'étage et niveaux de l'angle arraché (calés sur les étages)
    lignes = []
    y = YP
    while y + HB <= H - 1.0:
        lignes.append(y)
        y += PAS
    k_cut = max(2, int(len(lignes) * 0.58))
    y_cut = lignes[k_cut]
    niveaux = []                                  # (ya, yb, largeur manquante, profondeur manquante)
    ys = [y_cut, y_cut + 2 * PAS, y_cut + 3 * PAS, H]
    if ys[2] > H - 2.0:
        ys = [y_cut, y_cut + (H - y_cut) * 0.5, y_cut + (H - y_cut) * 0.78, H]
    fr = ((0.32, 0.36), (0.5, 0.52), (0.66, 0.68))
    for i in range(3):
        niveaux.append((ys[i], ys[i + 1], W * fr[i][0], D * fr[i][1]))

    def mx(mw):        # intervalle en x de l'angle manquant
        return (-hw, -hw + mw) if cx < 0 else (hw - mw, hw)

    # cratère dans la façade avant, à mi-hauteur, loin de l'angle arraché
    xc = -cx * W * 0.1
    yc = round(H * 0.45)
    k_c = 1.3
    crat = [(-5.0, 4.0, -3.5, 3.5), (-3.0, 5.0, 3.5, 5.5), (-2.0, 3.0, 5.5, 6.5), (-4.0, 2.5, -5.5, -3.5),
            (-1.5, 1.0, -6.5, -5.5), (4.0, 5.5, -1.5, 2.5), (-6.0, -5.0, -1.0, 2.0)]
    crat = [(max(-hw + 1.5, xc + k_c * a), min(hw - 1.5, xc + k_c * bb), yc + k_c * c0, yc + k_c * c1)
            for (a, bb, c0, c1) in crat]

    with b.group("TourEndommagee"):
        # ---------------- rez-de-chaussée ----------------
        with b.group("RezDeChaussee"):
            b.box((-hw - 0.2, G, zf - 0.2), (hw + 0.2, YP, zb + 0.2), vary(c(socle_c), rng, 0.03), studs="top", name="Socle")
            if v % 2 == 0:
                # hall éventré : intérieur sombre en retrait, piliers, vitres brisées, auvent cassé
                b.box((-hw + 1.2, 0, zf + 1.2), (hw - 1.2, G, zb - 1.2), shade(c("vitre"), 0.65), name="HallSombre")
                for x in (-hw + 0.6, hw - 0.6, -hw / 3, hw / 3):
                    b.box((x - 0.6, 0, zf), (x + 0.6, G, zf + 1.2), c("beton_clair"), name="Pilier")
                for x in (-hw + 0.6, hw - 0.6):
                    b.box((x - 0.6, 0, zb - 1.2), (x + 0.6, G, zb), c("beton_clair"), name="Pilier")
                for z in (zf + D / 3, zf + 2 * D / 3):
                    b.box((-hw, 0, z - 0.6), (-hw + 1.2, G, z + 0.6), c("beton_clair"), name="Pilier")
                # vitres du hall : une intacte, des morceaux accrochés, une travée vide
                xs_ = [-hw + 1.2, -hw / 3 - 0.6, -hw / 3 + 0.6, hw / 3 - 0.6, hw / 3 + 0.6, hw - 1.2]
                baies = [(xs_[0], xs_[1]), (xs_[2], xs_[3]), (xs_[4], xs_[5])]
                for i, (xa, xb) in enumerate(baies):
                    if i == 1:
                        _d(b, (xa, G - 2.4, zf + 0.7), (xb, G - 0.2, zf + 0.9), c("verre_brise"), transparency=0.4, name="VitreHall")
                    elif i == 0:
                        _d(b, (xa, 0.3, zf + 0.7), (xb, G - 0.2, zf + 0.9), c("verre_brise"), transparency=0.45, name="VitreHall")
                        _barre(b, (xa + 0.8, 1.0, zf + 0.6), (xb - 1.5, 7.0, zf + 0.6), 0.25, 0.12, (0, 0, -1), c("fissure"),
                               name="Fele", **PETIT)
                for (za, zb_) in ((zf + 1.2, zf + D / 3 - 0.6), (zf + 2 * D / 3 + 0.6, zb - 1.2)):
                    _d(b, (-hw + 0.7, G - 3.0, za), (-hw + 0.9, G - 0.2, zb_), c("verre_brise"), transparency=0.4, name="VitreHall")
                b.box((-5.0, 7.4, zf - 2.6), (1.5, 8.0, zf), c("metal"), studs="top", name="Auvent")
                _barre(b, (1.5, 7.7, zf - 1.3), (4.5, 7.2, zf - 1.0), 2.4, 0.4, (0, 1, 0), c("metal"), name="AuventCasse", **PETIT)
                for k in range(3):
                    _eclat(b, rng, float(rng.uniform(-hw + 2, hw - 2)), 0.0, zf + float(rng.uniform(0.7, 1.4)))
                for k in range(2):
                    _bloc_libre(b, rng, float(rng.uniform(-hw + 3, hw - 3)), zf + 3.0, 2.2, 1.4, 1.8,
                                vary(c("gravats"), rng), z_min=zf + 1.3, studs="top", name="Gravats")
            else:
                # boutiques : rideaux métalliques baissés, tags abstraits (taches, aucune lettre), bandeau d'enseignes vides
                b.box((-hw, 0, zf + 1.2), (hw, G, zb), vary(c("beton_fonce"), rng, 0.03), name="MurRdc")
                n_b = 3
                lb = W / n_b
                for i in range(n_b + 1):
                    x = -hw + i * lb
                    xa, xb = max(-hw, x - 0.6), min(hw, x + 0.6)
                    b.box((xa, 0, zf), (xb, G, zf + 1.2), c("beton"), name="Pilier")
                for i in range(n_b):
                    xa, xb = -hw + i * lb + 0.6, -hw + (i + 1) * lb - 0.6
                    b.box((xa, 0, zf + 0.5), (xb, 6.4, zf + 1.2), vary(c("rideau_metal"), rng, 0.03), name="Rideau")
                    _d(b, (xa, 3.0, zf + 0.4), (xb, 3.3, zf + 0.5), c("rideau_fonce"), name="Lame")
                    b.box((xa, 6.4, zf + 0.2), (xb, 7.4, zf + 1.2), c("rideau_fonce"), name="Coffre")
                    for g in range(2):
                        gx = float(rng.uniform(xa + 0.6, xb - 3.0))
                        gy = float(rng.uniform(0.8, 3.6))
                        gw, gh = float(rng.uniform(1.6, 2.8)), float(rng.uniform(1.0, 2.2))
                        _d(b, (gx, gy, zf + 0.38), (gx + gw, gy + gh, zf + 0.5), c(("graffiti_1", "graffiti_2", "graffiti_3")[(i + g) % 3]),
                           name="Tag")
                p = b.box((-hw, 7.4, zf - 0.3), (hw, 8.9, zf + 1.2), c("enseigne_noir"), name="Bandeau")
                for i in range(n_b):
                    xa = -hw + i * lb + 1.0
                    _d(b, (xa, 7.6, zf - 0.42), (xa + lb - 2.0, 8.7, zf - 0.3),
                       shade(c(("enseigne_blanc", "auvent_bleu", "auvent_jaune")[i % 3]), 0.75 if i == 1 else 1.0),
                       name="EnseigneVide")
                for k in range(2):
                    _eclat(b, rng, float(rng.uniform(-hw + 2, hw - 2)), 0.0, zf + float(rng.uniform(0.2, 0.5)), s=0.6)

        # ---------------- corps ----------------
        with b.group("Corps"):
            b.box((-hw, YP, zf + EF), (hw, y_cut, zb), corps_c, name="Corps")
            for (xa, xb, ya, yb) in _rects_moins(-hw, hw, YP, y_cut, crat):
                if xb - xa < 0.1:                 # pas de lamelle de moins de 0,1 au bord du cratère
                    xa, xb = (xa + xb) / 2 - 0.05, (xa + xb) / 2 + 0.05
                if yb - ya < 0.1:
                    ya, yb = (ya + yb) / 2 - 0.05, (ya + yb) / 2 + 0.05
                b.box((xa, ya, zf), (xb, yb, zf + EF), corps_c, name="CoucheAvant")
            # niveaux de l'angle arraché : chaque niveau = un L (deux blocs), de plus en plus entaillé vers le haut
            for (ya, yb, mw, md) in niveaux:
                ma, mb = mx(mw)
                if cx < 0:
                    b.box((mb, ya, zf), (hw, yb, zb), corps_c, studs="top", name="Corps")
                else:
                    b.box((-hw, ya, zf), (ma, yb, zb), corps_c, studs="top", name="Corps")
                b.box((ma, ya, zf + md), (mb, yb, zb), corps_c, studs="top", name="Corps")
            # intérieur sombre visible dans l'angle arraché + planchers cassés
            fond = mix(c("fissure"), c("bleu_ardoise"), 0.3)
            for (ya, yb, mw, md) in niveaux:
                ma, mb = mx(mw)
                xi = mb if cx < 0 else ma
                _d(b, (xi - 0.12, ya, zf), (xi + 0.12, yb, zf + md), fond, name="Interieur")
                _d(b, (ma, ya, zf + md - 0.12), (mb, yb, zf + md + 0.12), fond, name="Interieur")
                etages = [y for y in lignes if ya + 1.0 < y < yb - 0.5] or [round((ya + yb) / 2 + 0.35, 2)]
                for y in etages:
                    if True:
                        # nez de plancher (gris clair) sur les deux faces intérieures
                        _d(b, (xi + cx * 0.45, y - 0.7, zf), (xi, y, zf + md + 0.4), c("beton_clair"), name="NezPlancher")
                        _d(b, (ma, y - 0.7, zf + md - 0.45), (mb, y, zf + md), c("beton_clair"), name="NezPlancher")
            for i, (ya, yb, mw, md) in enumerate(niveaux):
                ma, mb = mx(mw)
                deb = (2.6, 1.6, 3.4)[i]
                if cx < 0:
                    b.box((mb - deb, ya - 0.7, zf + md - deb * 0.8), (mb + 0.1, ya, zf + md + 0.1), vary(c("beton_clair"), rng, 0.03),
                          studs="top", name="DalleANu")
                else:
                    b.box((ma - 0.1, ya - 0.7, zf + md - deb * 0.8), (ma + deb, ya, zf + md + 0.1), vary(c("beton_clair"), rng, 0.03),
                          studs="top", name="DalleANu")
                for k in range(1):
                    xx = (mb - deb * float(rng.uniform(0.2, 0.9))) if cx < 0 else (ma + deb * float(rng.uniform(0.2, 0.9)))
                    zz = zf + md - deb * 0.8 * float(rng.uniform(0.2, 0.8))
                    _fer(b, (xx, ya, zz), (xx + cx * 0.8, ya + 1.4, zz - 0.5), (xx + cx * 1.8, ya + 2.0, zz - 1.3))
            # toit : acrotère, local technique et citerne sur la partie intacte, feu d'obstacle
            ma, mb = mx(niveaux[-1][2])
            xr0, xr1 = (mb, hw) if cx < 0 else (-hw, ma)
            b.box((xr0 + 0.0, H, zb - 0.8), (xr1, H + 1.2, zb), shade(corps_c, 0.85), name="Acrotere", **PETIT)
            xt = (xr0 + xr1) / 2
            b.box((xt - 3.0, H, zb - 9.0), (xt + 3.0, H + 4.0, zb - 3.0), c("beton"), studs="top", name="LocalTechnique")
            b.cyl((xt + cx * 0.0, H + 4.0 + 1.4, zb - 6.0), 1.6, 2.8, c("citerne"), studs="top", name="Citerne")
            _n(b, (xt - 0.5, H + 4.0, zb - 3.6), (xt + 0.5, H + 5.0, zb - 2.6), "rouge_balise", name="Balise")

        # ---------------- façades ----------------
        with b.group("Facades"):
            trous_av = list(crat)
            trous_g, trous_d = [], []
            for (ya, yb, mw, md) in niveaux:
                ma, mb = mx(mw)
                trous_av.append((ma, mb, ya, yb + 0.01))
                (trous_g if cx < 0 else trous_d).append((zf, zf + md, ya, yb + 0.01))
            y_f0 = YP + 0.4

            def libre_(trous, y):
                return not any(t[2] < y + HB - 1e-6 and t[3] > y + 1e-6 for t in trous)

            lignes_f = []
            y = y_f0
            while y + HB <= H + 1e-6:
                lignes_f.append(y)
                y += PAS
            ceint_z = [y for y in lignes_f if libre_(trous_av, y)]
            ceint_x = [y for y in lignes_f if libre_(trous_g + trous_d, y)]
            for y in ceint_z:
                _d(b, (-hw + 0.05, y, zf - 0.2), (hw - 0.05, y + HB, zb + 0.2), allege_c, name="Allege")
            for y in ceint_x:
                _d(b, (-hw - 0.2, y, zf + 0.05), (hw + 0.2, y + HB, zb - 0.05), allege_c, name="Allege")
            _facade(b, rng, "z", zf, -1, -hw, hw, y_f0, H, pas=PAS, hb=HB, bande=allege_c, meneau=men_c, n_meneaux=4,
                    trous=trous_av, p_allume=0.12, p_casse=0.3, p_brise=0.1, lumiere=lum_c, sauter=ceint_z)
            gauche_vue = v % 2 == 0
            _facade(b, rng, "x", -hw, -1, zf, zb, y_f0, H, pas=PAS, hb=HB, bande=allege_c,
                    meneau=men_c if gauche_vue else None, n_meneaux=4, trous=trous_g, cellules=gauche_vue,
                    p_allume=0.12, p_casse=0.3, p_brise=0.08, lumiere=lum_c, sauter=ceint_x)
            _facade(b, rng, "x", hw, 1, zf, zb, y_f0, H, pas=PAS, hb=HB, bande=allege_c, meneau=None, trous=trous_d,
                    cellules=False, sauter=ceint_x)
            _facade(b, rng, "z", zb, 1, -hw, hw, y_f0, H, pas=PAS, hb=HB, bande=allege_c, meneau=None, cellules=False,
                    sauter=ceint_z)

        # ---------------- cratère ----------------
        with b.group("Cratere"):
            xa_c = min(t[0] for t in crat) - 0.5
            xb_c = max(t[1] for t in crat) + 0.5
            ya_c = min(t[2] for t in crat) - 0.5
            yb_c = max(t[3] for t in crat) + 0.5
            b.box((xa_c, ya_c, zf + EF - 0.15), (xb_c, yb_c, zf + EF + 0.6), shade(c("fissure"), 1.0), name="Fond")
            # planchers cassés qui avancent dans le trou
            for y in lignes:
                if ya_c + 0.5 < y < yb_c - 1.0:
                    xa = xc - float(rng.uniform(2.5, 4.5))
                    xb = xc + float(rng.uniform(1.5, 4.0))
                    b.box((xa, y - 0.8, zf + float(rng.uniform(0.4, 1.4))), (xb, y, zf + EF), vary(c("beton_clair"), rng, 0.03),
                          studs="top", name="DalleCassee")
                    for k in range(1):
                        xx = float(rng.uniform(xa + 0.5, xb - 0.5))
                        _fer(b, (xx, y - 0.4, zf + 1.0), (xx + float(rng.uniform(-0.6, 0.6)), y - 0.2, zf - 0.6),
                             (xx + float(rng.uniform(-1, 1)), y - 1.6, zf - 1.2))
            # lueur violette au fond (fissures lumineuses et cœur)
            _n(b, (xc - 1.5, yc - 1.2, zf + EF - 0.35), (xc + 1.5, yc + 1.2, zf + EF - 0.15), "lueur_rose", name="Coeur")
            for dirn in (30.0, 160.0, -100.0):
                _fissure(b, rng, "z", zf + EF - 0.15, -1, xc, yc, n=2, longueur=3.0, direction=dirn, neon=True,
                         couleur="lueur_violette", larg=0.4, d=0.0, bornes=(xa_c + 0.5, xb_c - 0.5, ya_c + 0.5, yb_c - 0.5))
            # fissures sombres qui rayonnent sur la façade autour du trou
            for (t, y, dirn) in ((xc - 5.0, yc + 2.0, 160.0), (xc + 5.5, yc - 1.0, -20.0), (xc - 1.0, yc - 6.5, -95.0),
                                 (xc + 2.0, yc + 6.5, 75.0)):
                _fissure(b, rng, "z", zf, -1, t, y, n=2, longueur=3.5, direction=dirn, larg=0.35,
                         bornes=(-hw + 0.5, hw - 0.5, YP + 1, H - 2))
            # éclats du bord du cratère
            for k in range(3):
                t = crat[k]
                _bloc_libre(b, rng, (t[0] + t[1]) / 2 + float(rng.uniform(-1, 1)), zf - 0.2, 1.4, 1.0, 1.0,
                            vary(c("gravats_clair"), rng), y=t[2] - 1.0 if k != 1 else t[3], z_max=zf + 0.4, z_min=zf - 0.8,
                            name="Eclat", **PETIT)

        # ---------------- fissures et lueurs sur les autres faces ----------------
        with b.group("Fissures"):
            if v % 2 == 0:
                _fissure(b, rng, "x", -hw, -1, zf + D * 0.6, H * 0.62, n=4, longueur=5.0, direction=-80.0, neon=True,
                         couleur="lueur_violette", larg=0.5, bornes=(zf + 1, zb - 1, YP + 2, y_cut - 1))
                _fissure(b, rng, "x", -hw, -1, zf + D * 0.3, H * 0.35, n=3, longueur=4.0, direction=-60.0,
                         bornes=(zf + 1, zb - 1, YP + 2, y_cut - 1))
            else:
                _fissure(b, rng, "z", zf, -1, cx * hw * 0.6, H * 0.7, n=4, longueur=4.5, direction=-100.0, neon=True,
                         couleur="lueur_violette", larg=0.5, bornes=(-hw + 1, hw - 1, YP + 2, y_cut - 1))
    return {"emprise": (W, D), "hauteur": H + 6.0}


# ---------------------------------------------------------------------------
# 4) Tas de gravats
# ---------------------------------------------------------------------------

def gravats(b, variant=0, taille=1.0) -> dict:
    """Tas de gravats (blocs de béton, dalle cassée, fers, éclats de verre) dans un cercle de rayon 3·taille.
    variant 1 : un morceau de façade bleue ; variant 2 : éclat de lueur violette ; variant 3 : tas plus plat."""
    rng = b.rng
    t = float(taille)
    v = variant % 4
    Rmax = 3.0 * t
    tons = [c("gravats"), c("gravats_clair"), c("gravats_fonce")]

    def bloc(cx, cz, sx, sy, sz, couleur, y=0.0, gros=True):
        yaw = float(rng.uniform(0, 90))
        demi = 0.5 * math.hypot(sx, sz)
        r = math.hypot(cx, cz)
        if r + demi > Rmax - 0.05:
            k = max(0.0, (Rmax - 0.05 - demi)) / max(r, 1e-6)
            cx, cz = cx * k, cz * k
        kw = {} if gros else PETIT
        return b.boxc((cx, y + sy / 2, cz), (sx, sy, sz), couleur, yaw=yaw, studs="top", name="Gravats", **kw)

    plat = v == 3
    with b.group("Gravats"):
        # cœur du tas
        h0 = (1.1 if plat else 1.7) * t
        bloc(0.0, 0.0, 2.2 * t, h0, 2.0 * t, vary(tons[0], rng))
        # couronne de gros blocs au sol
        n_bas = 5
        a0 = float(rng.uniform(0, 2 * math.pi))
        for i in range(n_bas):
            a = a0 + 2 * math.pi * i / n_bas + float(rng.uniform(-0.3, 0.3))
            rr = float(rng.uniform(1.2, 1.7)) * t
            col = tons[(i + 1) % 3]
            if v == 1 and i == 2:
                col = c("bleu_ardoise")
            bloc(rr * math.cos(a), rr * math.sin(a), float(rng.uniform(1.2, 1.9)) * t, float(rng.uniform(0.6, 1.1)) * t,
                 float(rng.uniform(1.0, 1.6)) * t, vary(col, rng))
        # blocs posés sur le cœur
        for i in range(2 if not plat else 1):
            a = a0 + math.pi * i + 0.7
            bloc(0.5 * t * math.cos(a), 0.5 * t * math.sin(a), float(rng.uniform(0.9, 1.3)) * t, float(rng.uniform(0.6, 0.9)) * t,
                 float(rng.uniform(0.8, 1.2)) * t, vary(tons[(i + 2) % 3], rng), y=h0 - 0.15 * t, gros=False)
        if not plat:
            bloc(0.1 * t, -0.1 * t, 0.8 * t, 0.7 * t, 0.7 * t, vary(tons[1], rng), y=h0 + 0.45 * t, gros=False)
        if v == 1:
            # bande de façade (allège blanche) sur le morceau bleu
            a = a0 + 2 * math.pi * 2 / n_bas
            rr = 1.45 * t
            b.boxc((rr * math.cos(a), 1.0 * t, rr * math.sin(a)), (0.9 * t, 0.3 * t, 0.9 * t), c("carrelage"), yaw=float(rng.uniform(0, 90)),
                   name="Facade", **PETIT)
        # dalle cassée inclinée : un bout au sol, l'autre sur le cœur
        a = a0 + 0.35
        p0 = np.array([2.35 * t * math.cos(a), 0.18 * t, 2.35 * t * math.sin(a)])
        p1 = np.array([0.5 * t * math.cos(a), h0 + 0.1 * t, 0.5 * t * math.sin(a)])
        _barre(b, p0, p1, 1.4 * t, 0.35 * t, (0.0, 1.0, 0.0), vary(c("beton_clair"), rng, 0.03), name="Dalle", studs="top")
        if not plat:
            a2 = a0 + math.pi + 0.5
            p0 = np.array([2.2 * t * math.cos(a2), 0.15 * t, 2.2 * t * math.sin(a2)])
            p1 = np.array([0.9 * t * math.cos(a2), h0 * 0.8, 0.9 * t * math.sin(a2)])
            _barre(b, p0, p1, 1.1 * t, 0.3 * t, (0.0, 1.0, 0.0), vary(c("gravats_clair"), rng, 0.03), name="Dalle", **PETIT)
        # fers à béton tordus qui sortent du tas
        for i in range(3):
            a = a0 + 2.1 * i + 0.4
            base = np.array([0.6 * t * math.cos(a), h0 * 0.85, 0.6 * t * math.sin(a)])
            coude = base + np.array([0.5 * t * math.cos(a), 0.9 * t, 0.5 * t * math.sin(a)])
            bout = coude + np.array([0.7 * t * math.cos(a + 0.8), 0.25 * t, 0.7 * t * math.sin(a + 0.8)])
            _fer(b, base, coude, bout, r=0.1 * max(1.0, t))
        # éclats de verre au sol
        for i in range(2):
            a = a0 + 1.3 + 2.4 * i
            _eclat(b, rng, 2.2 * t * math.cos(a), 0.0, 2.2 * t * math.sin(a), s=0.7 * t)
        if v == 2:
            a = a0 + 1.9
            x, z = 1.2 * t * math.cos(a), 1.2 * t * math.sin(a)
            b.boxc((x, 0.35 * t, z), (0.9 * t, 0.7 * t, 0.7 * t), c("lueur_violette"), yaw=float(rng.uniform(0, 90)),
                   material="Neon", name="Lueur", **PETIT)
    return {"emprise": (6 * t, 6 * t), "hauteur": 3.5 * t}


# ---------------------------------------------------------------------------
# 5) Voiture abandonnée
# ---------------------------------------------------------------------------

def voiture_abandonnee(b, variant=0) -> dict:
    """Petite voiture japonaise générique (aucune marque, aucun texte), avant vers -Z, 4,6 × 9, ≤ 4,5 de haut.
    0 : monospace blanc à pare-brise étoilé et porte coulissante ouverte ; 1 : citadine rouge couverte de
    poussière et de gravats ; 2 : citadine bleu foncé, capot écrasé, un côté soulevé par un bloc de béton ;
    3 : taxi jaune générique (lanterneau de toit vierge)."""
    rng = b.rng
    v = variant % 4
    n0 = len(b.parts)
    corps = c(("carrosserie_1", "carrosserie_2", "carrosserie_3", "carrosserie_4")[v])
    vitre = c("vitre")
    hx = 1.8                                        # demi-largeur de la caisse
    zf, zb = -4.35, 4.35
    yb_, yc = 0.55, 1.9                             # bas et haut de la caisse
    # (z début capot / pare-brise, z début habitacle, z fin habitacle, z fin lunette, haut du toit)
    forme = {0: (-3.5, -2.3, 4.2, 4.2, 4.1), 1: (-2.7, -1.3, 2.7, 3.8, 3.55), 2: (-2.7, -1.3, 2.7, 3.8, 3.55),
             3: (-2.4, -1.1, 1.5, 2.6, 3.45)}[v]
    zp, zh0, zh1, zl, yt = forme
    with b.group("Voiture"):
        b.box((-hx, yb_, zf), (hx, yc, zb), corps, name="Caisse")
        b.box((-hx + 0.2, yc, zh0), (hx - 0.2, yt, zh1), corps, studs="top", name="Habitacle")
        b.wedge((-hx + 0.2, yc, zp), (hx - 0.2, yt, zh0), vitre, down="-z", name="PareBrise")
        if zl > zh1 + 0.05:
            b.wedge((-hx + 0.2, yc, zh1), (hx - 0.2, yt, zl), vitre, down="+z", name="Lunette")
        else:
            _d(b, (-hx + 0.6, yc + 0.5, zh1), (hx - 0.6, yt - 0.35, zh1 + 0.12), vitre, name="Lunette")
        _d(b, (-hx + 0.1, yc + 0.35, zh0 + 0.15), (hx - 0.1, yt - 0.3, zh1 - 0.2), vitre, name="VitresLaterales")
        _d(b, (-hx, yc + 0.3, zh0 + 1.6), (hx, yt - 0.25, zh0 + 1.9), corps, name="Montant")
        for x in (-1.55, 1.55):
            for z in (-2.85, 2.85):
                b.cyl((x * 1.0 + (0.1 if x > 0 else -0.1), 0.7, z), 0.7, 0.5, c("pneu"), axis="x", name="Roue")
        _d(b, (-hx + 0.05, yb_ - 0.05, zf - 0.15), (hx - 0.05, 1.05, zf + 0.25), shade(corps, 0.7) if v != 0 else c("metal"),
           name="ParechocAvant")
        _d(b, (-hx + 0.05, yb_ - 0.05, zb - 0.25), (hx - 0.05, 1.05, zb + 0.15), shade(corps, 0.7) if v != 0 else c("metal"),
           name="ParechocArriere")
        _d(b, (-0.55, 1.15, zf - 0.1), (0.55, 1.6, zf), c("anthracite"), name="Calandre")
        for s in (-1, 1):
            _n(b, (s * 1.05 - 0.4, 1.25, zf - 0.12), (s * 1.05 + 0.4, 1.7, zf), "neon_blanc", name="Phare")
            _d(b, (s * 1.15 - 0.35, 1.3, zb), (s * 1.15 + 0.35, 1.75, zb + 0.12), c("feu_rouge"), name="FeuArriere")
            xr = s * (hx + 0.2)
            _d(b, (min(xr, s * hx), yc + 0.2, zh0 + 0.1), (max(xr, s * hx), yc + 0.65, zh0 + 0.6), corps, name="Retro")
        if v == 0:
            # pare-brise étoilé : verre brisé translucide posé sur la pente, éclats sombres
            n_pb = np.array([0.0, zh0 - zp, -(yt - yc)])
            n_pb /= np.linalg.norm(n_pb)
            pa = np.array([0.0, yc + 0.25, zp + 0.25]) + n_pb * 0.12
            pb = np.array([0.0, yt - 0.2, zh0 - 0.05]) + n_pb * 0.12
            _barre(b, pa, pb, 2.6, 0.1, n_pb, c("verre_brise"), transparency=0.35, name="PareBriseEtoile", **PETIT)
            for ang in (0.6, 2.2, 3.9):
                q0 = (pa + pb) / 2 + n_pb * 0.06
                q1 = q0 + np.array([0.9 * math.cos(ang), 0.0, 0.0]) + (pb - pa) / np.linalg.norm(pb - pa) * 0.8 * math.sin(ang)
                _barre(b, q0, q1, 0.12, 0.1, n_pb, c("fissure"), name="Fele", **PETIT)
            # porte coulissante ouverte (côté droit, +X) : ouverture sombre, siège, porte glissée vers l'arrière
            za, zb2 = zh0 + 2.0, zh0 + 4.2
            _d(b, (hx - 0.02, yb_ + 0.3, za), (hx + 0.1, yt - 0.2, zb2), c("fissure"), name="Ouverture")
            _d(b, (hx + 0.1, yb_ + 0.5, za + 0.3), (hx + 0.2, yc - 0.1, za + 1.4), c("anthracite"), name="Siege")
            _d(b, (hx + 0.12, yb_ + 0.3, za + 1.6), (hx + 0.32, yt - 0.25, min(zb2 + 1.6, zb - 0.2)), corps, name="PorteCoulissee")
            _d(b, (hx + 0.32, yc + 0.35, za + 1.8), (hx + 0.42, yt - 0.45, min(zb2 + 1.4, zb - 0.4)), vitre, name="VitrePorte")
        elif v == 1:
            # poussière et gravats tombés sur le toit et le capot
            _d(b, (-hx + 0.4, yt, zh0 + 0.3), (hx - 0.6, yt + 0.12, zh1 - 0.3), c("gravats_clair"), name="Poussiere")
            _d(b, (-hx + 0.3, yc, zf + 0.3), (hx - 0.5, yc + 0.12, zp - 0.2), c("gravats_clair"), name="Poussiere")
            for (x, z, s, col) in ((-0.5, 0.2, 1.0, "gravats"), (0.6, 1.6, 0.8, "gravats_fonce"), (0.2, -0.9, 0.55, "gravats_clair")):
                b.boxc((x, yt + 0.12 + 0.35 * s, z), (1.1 * s, 0.7 * s, 0.9 * s), vary(c(col), rng), yaw=float(rng.uniform(0, 90)),
                       studs="top", name="Gravats", **PETIT)
            b.boxc((0.3, yc + 0.12 + 0.3, zf + 1.2), (1.0, 0.6, 0.8), vary(c("gravats"), rng), yaw=25, name="Gravats", **PETIT)
            n_l = np.array([0.0, zl - zh1, yt - yc])
            n_l /= np.linalg.norm(n_l)
            _barre(b, np.array([0.0, yt - 0.3, zh1 + 0.15]) + n_l * 0.1, np.array([0.0, yc + 0.45, zl - 0.3]) + n_l * 0.1, 2.4, 0.1,
                   n_l, c("verre_brise"), transparency=0.4, name="LunetteBrisee", **PETIT)
        elif v == 2:
            # capot écrasé : tôle pliée en toit (deux plaques) et bloc de béton tombé dessus
            zm = (zf + zp) / 2
            _barre(b, (0.0, yc - 0.1, zf + 0.25), (0.0, yc + 0.55, zm), 2 * hx - 0.5, 0.2, (0, 1, 0), shade(corps, 0.9),
                   name="CapotPlie", **PETIT)
            _barre(b, (0.0, yc + 0.55, zm), (0.0, yc - 0.05, zp - 0.1), 2 * hx - 0.5, 0.2, (0, 1, 0), shade(corps, 0.8),
                   name="CapotPlie", **PETIT)
            b.boxc((0.5, yc + 0.6 + 0.45, zf + 1.4), (1.4, 0.9, 1.2), vary(c("gravats"), rng), yaw=35, studs="top", name="Gravats",
                   **PETIT)
            n_pb = np.array([0.0, zh0 - zp, -(yt - yc)])
            n_pb /= np.linalg.norm(n_pb)
            _barre(b, np.array([-0.6, yc + 0.3, zp + 0.2]) + n_pb * 0.1, np.array([-0.6, yt - 0.25, zh0 - 0.05]) + n_pb * 0.1, 1.9,
                   0.1, n_pb, c("verre_brise"), transparency=0.4, name="PareBriseBrise", **PETIT)
        else:
            # taxi : lanterneau de toit vierge, voyant « libre » rouge (sans texte), bas de caisse sombre
            b.box((-0.7, yt, -0.6), (0.7, yt + 0.15, 0.6), c("anthracite"), name="SocleLanterneau", **PETIT)
            _n(b, (-0.6, yt + 0.15, -0.4), (0.6, yt + 0.75, 0.4), "neon_blanc", name="Lanterneau")
            _n(b, (0.4, yc + 0.6, zh0 - 0.6), (1.0, yc + 0.9, zh0 - 0.4), "feu_rouge", name="Voyant")
            _d(b, (-hx - 0.1, 1.45, zf + 0.6), (hx + 0.1, 1.7, zb - 0.6), c("chantier_noir"), name="Ceinture")
    if v == 2:
        # un côté (gauche) soulevé : rotation autour de la ligne de contact des roues droites, bloc dessous
        pivot = (1.75 + 0.25, 0.0, 0.0)
        _tourner(b, n0, rot_z(-7.0), pivot)
        lo, hi = _boite_locale(b, n0)
        dx = min(0.0, 2.28 - float(hi[0]))           # rester dans l'emprise de ±2,3 après la rotation
        if dx:
            for p in b.parts[n0:]:
                p.pos = tuple(round(float(v), 4) + 0.0 for v in np.asarray(p.pos) + _repere_courant(b)[0] @ np.array([dx, 0.0, 0.0]))
        b.box((-1.9 + dx, 0.0, -1.5), (-0.6 + dx, 0.62, 1.4), vary(c("gravats"), rng), studs="top", name="BlocSousCaisse")
    lo, hi = _boite_locale(b, n0)
    return {"emprise": (4.6, 9.0), "hauteur": round(float(hi[1]), 2)}
