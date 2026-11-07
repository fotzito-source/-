"""Bâtiments de la zone Black Clover, style « stud » : le village abandonné des confins (chaumières, maisons de
pierre, ruines incendiées, grange, moulin-tour, église) et le bourg serré autour de la tour aux grimoires (maisons
hautes à colombages noirs, taverne, halle du marché), plus les maisons simples du second rang.

Fonctions publiques (chacune `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}), budgets de SPECS.md :
- chaumiere(largeur=14, profondeur=12) ≤ 60 : moellons sombres, chaume épais en gradins ;
    v0 faîtage parallèle à la rue ; v1 pignon sur rue et lucarne ; v2 toit d'ardoise moussu ; v3 en L, appentis
    et tas de bois ; v4 toit à moitié effondré (trou, chevrons calcinés, intérieur noir).
- maison_pierre(largeur=16, profondeur=14, etages=2, enseigne=None) ≤ 90 : pignon d'ardoise très pentu ;
    v0 moellons (FORGE : baie ouverte, foyer rougeoyant, hotte, enclume) ; v1 pierre gris-violet, toit en pavillon
    et lucarne ; v2 étage à colombages noirs en encorbellement, pignon essenté d'ardoise (AUBERGE : tonneaux) ;
    v3 comme v0, sans forge.
- maison_ruine(largeur=12, profondeur=12) ≤ 50 : ruine incendiée ; v0 pignon debout ; v1 deux murs d'angle ;
    v2 souche de cheminée debout et braises rouges.
- grange(largeur=20, profondeur=14) ≤ 65 : planches grises sur soubassement de pierre, pignon sur rue ;
    v0 chaume sombre, vantail entrouvert, fenil et palan ; v1 ardoise ; v2 chaume crevé.
- moulin() ≤ 95 : moulin-tour de pierre, toit conique, quatre ailes de lattes tournées vers -Z ;
    v0 deux toiles déchirées et une aile cassée ; v1 ailes entoilées ; v2 ailes nues arrêtées en croix ; v3 v0 sous ardoise.
- eglise(largeur=26, profondeur=44) ≤ 300 : clocher-porche, flèche octogonale d'ardoise (pointe de fer et boule
    dorée, aucune croix), cloche, portail en arc brisé, baies lancéolées, oculus, contreforts, chœur ;
    v0 toit de la nef crevé (chevrons calcinés) ; v1 intacte.
- maison_haute(largeur=14, profondeur=14, etages=3, enseigne=None) ≤ 95 : rez de pierre sombre à devanture
    éclairée, étages à colombages noirs en encorbellement, pignon d'ardoise à ≈ 60° ;
    v0 enduit gris ; v1 ocre, toit à lucarnes ; v2 sang-de-bœuf, pignon essenté d'ardoise ; v3 vert éteint,
    dernier étage de travers ; v4 crème sali, oriel ; v5 gris-violet, tourelle d'angle à toit conique.
- taverne(largeur=24, profondeur=16) ≤ 150 ; halle(largeur=26, profondeur=14) ≤ 110 ;
- maison_fond(largeur=12, profondeur=10, etages=1) ≤ 28 : v0 ardoise ; v1 chaume ; v2 pignon d'ardoise ; v3 ruine.

Repère : origine au centre de l'emprise au sol, y = 0 au sol ; l'AVANT (façade sur la rue) est en
z = -profondeur/2 et regarde -Z ; `largeur` le long de X (vu de la rue, +x est à gauche). Débords latéraux ≤ 0,5 ;
vers la rue, encorbellements, auvents, rives et lanternes ≤ 3 ; les enseignes (mobilier.enseigne) s'arrêtent à
8,6 de la façade (|x| ≥ 46,4 une fois la façade en |x| = 55) : leur platine s'enfonce dans le mur si le mot est long.
Règles : un aplat = une pièce ; détails en saillie ≥ 0,1, aucune face coplanaire de couleurs différentes ; rien ne
flotte ; studs sur les toits et les rebords, jamais sur les murs ; petits détails sans collision. Chaque fonction se
construit au niveau de détail le plus riche qui tient dans son budget. Aucune croix, aucune étoile, aucun emblème ;
textes : seulement ceux des enseignes permises (mobilier.TEXTES_ENSEIGNES).
"""

from __future__ import annotations

import math

import numpy as np

from assets import mobilier
from kit import hexrgb, mix, rot_x, rot_y, rot_z, shade
from palette import c, vary

DECO = dict(collide=False)
FIN = dict(collide=False, shadow=False)
NEON = dict(material="Neon", collide=False, shadow=False)

PIXELS = ("moellon_clair", "moellon_fonce", "pierre_fonce", "pierre_ombre", "moellon")
VITRAUX = ("vitrail_violet", "vitrail_ambre", "vitrail_rouge")


# ---------------------------------------------------------------------------
# Couleurs, tirages, budget
# ---------------------------------------------------------------------------

def col(x):
    """Nom de palette, '#hex' ou tuple → tuple RGB."""
    if isinstance(x, (tuple, list)):
        return tuple(int(v) for v in x)
    if isinstance(x, str) and x.startswith("#"):
        return hexrgb(x)
    return c(x)


def vr(x, rng, amount=0.05):
    """`vary` qui accepte aussi '#hex' et les tuples."""
    return vary(col(x), rng, amount)


def _v(p):
    return np.asarray(p, float)


def _cle(*vals) -> int:
    """Petit hachage déterministe (FNV-1a)."""
    h = 2166136261
    for v in vals:
        for ch in str(v) + "|":
            h = ((h ^ ord(ch)) * 16777619) % 2 ** 32
    return h


def _rng(b, *vals):
    """Aléatoire propre à une pose : paramètres + position de l'origine dans la zone (deux poses identiques à deux
    endroits ne sont pas tout à fait les mêmes)."""
    o = b.to_world((0.0, 0.0, 0.0))
    return np.random.default_rng(_cle(*vals, int(round(float(o[0]))), int(round(float(o[2])))))


def _budget(b, n0, budget, construire, niveaux=4):
    """Construit au niveau de détail le plus riche (0) qui tient dans `budget` pièces."""
    info = None
    for niv in range(niveaux):
        info = construire(niv)
        if len(b.parts) - n0 <= budget or niv == niveaux - 1:
            break
        del b.parts[n0:]
    return info


def _mur(rng, sombre=0.35):
    """Moellons gris-brun assombris (village des confins)."""
    return vary(mix(c("moellon"), c("moellon_fonce"), sombre), rng, 0.04)


def _pivoter(b, n0, pivot, R):
    """Tourne les pièces b.parts[n0:] de la rotation locale R autour du point local `pivot` (étage de travers)."""
    Rf = b._R[-1]
    q = b.to_world(pivot)
    Rw = Rf @ R @ Rf.T
    for p in b.parts[n0:]:
        pos = q + Rw @ (np.asarray(p.pos, float) - q)
        rot = Rw @ np.asarray(p.rot, float).reshape(3, 3)
        p.pos = tuple(round(float(v), 4) for v in pos)
        p.rot = tuple(round(float(v), 4) for v in rot.reshape(-1))


# ---------------------------------------------------------------------------
# Géométrie : poutres, pans inclinés, triangles, flèches
# ---------------------------------------------------------------------------

def _poutre(b, a, bb, ep, couleur, ep2=None, ext=0.0, name="Poutre", **kw):
    """Bloc de section ep × ep2 tendu de a à bb (chevrons, écharpes inclinées, lattes d'ailes)."""
    a, bb = _v(a), _v(bb)
    d = bb - a
    n = float(np.linalg.norm(d))
    x = d / n
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([0.0, 0.0, 1.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return b.part("block", (n + 2 * ext, ep, ep2 if ep2 else ep), (a + bb) / 2, np.column_stack([x, y, z]),
                  col(couleur), name=name, **kw)


def _barre(b, xa, ya, xb, yb, z0, z1, ep, couleur, name="Echarpe", **kw):
    """Barre dans un plan de façade, de (xa, ya) à (xb, yb), largeur `ep`, profondeur z0..z1."""
    L = math.hypot(xb - xa, yb - ya)
    ang = math.degrees(math.atan2(yb - ya, xb - xa))
    return b.part("block", (L, ep, z1 - z0), ((xa + xb) / 2, (ya + yb) / 2, (z0 + z1) / 2), rot_z(ang),
                  col(couleur), name=name, **kw)


def _pan_x(b, xa, ya, xb, yb, z0, z1, ep, couleur, *, ext_a=0.0, ext_b=0.0, studs="top", name="Pan", **kw):
    """Dalle inclinée dans le plan XY (xa < xb) : face supérieure par (xa, ya) et (xb, yb), épaisseur `ep` dessous,
    étendue sur z0..z1 ; `ext_a` / `ext_b` l'allongent le long de la pente côté a / côté b."""
    dx, dy = xb - xa, yb - ya
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    s = (ext_b - ext_a) / 2
    cx = (xa + xb) / 2 + ux * s - nx * ep / 2
    cy = (ya + yb) / 2 + uy * s - ny * ep / 2
    return b.part("block", (L + ext_a + ext_b, ep, z1 - z0), (cx, cy, (z0 + z1) / 2), rot_z(math.degrees(math.atan2(dy, dx))),
                  col(couleur), studs=studs, name=name, **kw)


def _pan_z(b, za, ya, zb, yb, x0, x1, ep, couleur, *, ext_a=0.0, ext_b=0.0, studs="top", name="Pan", **kw):
    """Dalle inclinée dans le plan YZ (za < zb) : face supérieure par (za, ya) et (zb, yb), épaisseur `ep` dessous,
    étendue sur x0..x1 ; `ext_a` / `ext_b` l'allongent le long de la pente côté a / côté b."""
    dz, dy = zb - za, yb - ya
    L = math.hypot(dz, dy)
    uz, uy = dz / L, dy / L
    phi = math.atan2(dy, dz)
    ny, nz = math.cos(phi), -math.sin(phi)
    s = (ext_b - ext_a) / 2
    cz = (za + zb) / 2 + uz * s - nz * ep / 2
    cy = (ya + yb) / 2 + uy * s - ny * ep / 2
    return b.part("block", (x1 - x0, ep, L + ext_a + ext_b), ((x0 + x1) / 2, cy, cz), rot_x(-math.degrees(phi)),
                  col(couleur), studs=studs, name=name, **kw)


def _decale(A, B, d):
    """Segment AB (points (u, y) avec uA < uB) décalé de d vers l'extérieur (côté y croissant)."""
    du, dy = B[0] - A[0], B[1] - A[1]
    L = math.hypot(du, dy)
    nu, ny = -dy / L, du / L
    if ny < 0:
        nu, ny = -nu, -ny
    return (A[0] + nu * d, A[1] + ny * d), (B[0] + nu * d, B[1] + ny * d)


def _lerp(A, B, t):
    return (A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t)


def _tri(b, M, C, A, ep, couleur, dehors, studs=False, name="Pan", **kw):
    """Fine plaque triangulaire, triangle rectangle en M (MC le long de la base, MA vers le sommet) : un coin Roblox
    d'épaisseur `ep` dont la face latérale est le triangle ; l'épaisseur part à l'opposé de `dehors`."""
    M, C, A = _v(M), _v(C), _v(A)
    h = float(np.linalg.norm(A - M))
    d = float(np.linalg.norm(C - M))
    Y = (A - M) / h
    Z = (M - C) / d
    X = np.cross(Y, Z)
    s = 1.0 if float(np.dot(X, dehors)) > 0 else -1.0
    ctr = M + Y * h / 2 - Z * d / 2 - s * X * ep / 2
    face = "Right" if s > 0 else "Left"
    return b.part("wedge", (ep, h, d), ctr, np.column_stack([X, Y, Z]), col(couleur),
                  studs=(face,) if studs else (), name=name, **kw)


def _facette(b, P, Q, A, ep, couleur, interieur, **kw) -> int:
    """Triangle PQA quelconque (pied de la hauteur issue de A dans [PQ]) en un ou deux triangles rectangles."""
    P, Q, A = _v(P), _v(Q), _v(A)
    L = float(np.linalg.norm(Q - P))
    u = (Q - P) / L
    t = float(np.dot(A - P, u))
    F = P + u * t
    nrm = np.cross(Q - P, A - P)
    if float(np.dot(nrm, P - _v(interieur))) < 0:
        nrm = -nrm
    n = 0
    if t > 0.02:
        _tri(b, F, P, A, ep, couleur, nrm, **kw)
        n += 1
    if t < L - 0.02:
        _tri(b, F, Q, A, ep, couleur, nrm, **kw)
        n += 1
    return n


def _fleche(b, rng, cx, y0, cz, R, H, couleurs, n=8, ep=0.45, **kw) -> float:
    """Flèche polygonale lisse (n pans, rayon R aux sommets, un pan face à -z) : 2n pièces, deux tons alternés."""
    a0 = math.pi / n + math.pi / 2
    pts = [(cx + R * math.cos(a0 + 2 * math.pi * i / n), y0, cz + R * math.sin(a0 + 2 * math.pi * i / n))
           for i in range(n)]
    A = (cx, y0 + H, cz)
    for i in range(n):
        _facette(b, pts[i], pts[(i + 1) % n], A, ep, vr(couleurs[i % len(couleurs)], rng, 0.02),
                 (cx, y0 + H * 0.3, cz), **kw)
    return y0 + H


def _croupe(b, rng, x0, x1, z0, z1, ye, pente, toit, *, ep=0.6, ext=0.4, name="Toit", **kw) -> float:
    """Toit en croupe (ou en pavillon) dont le dessus passe par le rectangle d'égout [x0, x1] × [z0, z1] à la
    hauteur ye ; faîtage le long de X (x1 - x0 ≥ z1 - z0). Pans longs : un rectangle et deux triangles ; croupes :
    deux triangles. Renvoie la hauteur du faîtage."""
    t = col(toit)
    run = (z1 - z0) / 2
    zm = (z0 + z1) / 2
    yr = ye + run * pente
    xa, xb = x0 + run, x1 - run
    ins = ((x0 + x1) / 2, ye - 2.0, zm)
    if xb - xa > 0.1:
        _pan_z(b, z0, ye, zm, yr, xa, xb, ep, vr(t, rng, 0.02), ext_b=ext, name=name, **kw)
        _pan_z(b, zm, yr, z1, ye, xa - 0.0, xb + 0.0, ep, vr(t, rng, 0.02), ext_a=ext, name=name, **kw)
        for (zz, s) in ((z0, -1), (z1, 1)):
            dehors = _v((0.0, 1.0, s * pente))
            _tri(b, (xa, ye, zz), (x0, ye, zz), (xa, yr, zm), ep, vr(t, rng, 0.02), dehors, studs=True, name=name, **kw)
            _tri(b, (xb, ye, zz), (x1, ye, zz), (xb, yr, zm), ep, vr(t, rng, 0.02), dehors, studs=True, name=name, **kw)
    else:
        xa = xb = (x0 + x1) / 2
        for (zz, s) in ((z0, -1), (z1, 1)):
            _facette(b, (x0, ye, zz), (x1, ye, zz), (xa, yr, zm), ep, vr(t, rng, 0.02), ins, studs=True, name=name, **kw)
    _facette(b, (x0, ye, z0), (x0, ye, z1), (xa, yr, zm), ep, vr(t, rng, 0.02), ins, studs=True, name=name, **kw)
    _facette(b, (x1, ye, z0), (x1, ye, z1), (xb, yr, zm), ep, vr(t, rng, 0.02), ins, studs=True, name=name, **kw)
    return yr


# ---------------------------------------------------------------------------
# Toits à deux pans
# ---------------------------------------------------------------------------

def _toit_gouttereau(b, rng, x0, x1, zf, zb, H, pente, toit, mur, *, ep=0.6, deb_av=0.8, deb_ar=0.6, rive=0.4,
                     comble="plein", ep_pignon=0.9, av=None, ar=None, faitage="ardoise", gradins=0.0,
                     couleur_gradins=None, boudins=False):
    """Toit à deux pans dont le GOUTTEREAU regarde la rue (faîtage le long de X) sur des murs x0..x1 / zf..zb de
    hauteur H. comble : "plein" (deux coins pleine profondeur couleur `mur`), "pignons" (deux pignons minces, comble
    vide pour un toit crevé) ou None. av / ar : morceaux de pan [(xa, xb, t0, t1)] (t de l'égout 0 au faîtage 1),
    par défaut le pan entier. faitage : "ardoise" (bloc), "chaume" (boudin), None. gradins > 0 : seconde couche de
    chaume sur le bas de chaque pan, décalée d'autant. Renvoie un dict (yr, dessus(z), zm, k, rise)."""
    zm = (zf + zb) / 2
    run = zm - zf
    rise = run * pente
    k = ep * math.hypot(1, pente)
    yr = H + rise + k
    m = col(mur)
    if comble == "plein":
        b.wedge((x0, H, zf), (x1, H + rise, zm), m, down="-z", name="Comble")
        b.wedge((x0, H, zm), (x1, H + rise, zb), m, down="+z", name="Comble")
    elif comble == "pignons":
        for (xa, xb) in ((x0, x0 + ep_pignon), (x1 - ep_pignon, x1)):
            b.wedge((xa, H, zf), (xb, H + rise, zm), m, down="-z", name="Pignon")
            b.wedge((xa, H, zm), (xb, H + rise, zb), m, down="+z", name="Pignon")
    t = col(toit)
    E_av = (zf - deb_av, H + k - deb_av * pente)
    E_ar = (zb + deb_ar, H + k - deb_ar * pente)
    Rg = (zm, yr)
    av = av if av is not None else [(x0 - rive, x1 + rive, 0.0, 1.0)]
    ar = ar if ar is not None else [(x0 - rive - 0.1, x1 + rive + 0.1, 0.0, 1.0)]
    for (xa, xb, t0, t1) in av:
        A, B = _lerp(E_av, Rg, t0), _lerp(E_av, Rg, t1)
        _pan_z(b, A[0], A[1], B[0], B[1], xa, xb, ep, vr(t, rng, 0.025), ext_b=0.45 if t1 >= 1 else 0.0)
    for (xa, xb, t0, t1) in ar:
        A, B = _lerp(E_ar, Rg, t1), _lerp(E_ar, Rg, t0)
        _pan_z(b, A[0], A[1], B[0], B[1], xa, xb, ep, vr(t, rng, 0.025), ext_a=0.45 if t1 >= 1 else 0.0)
    if gradins > 0:
        cg = col(couleur_gradins or toit)
        for i, (E, sens) in enumerate(((E_av, 1), (E_ar, -1))):
            morceaux = av if sens > 0 else ar
            if not any(t0 <= 0.0 for (_, _, t0, _) in morceaux):
                continue
            xa = min(m_[0] for m_ in morceaux if m_[2] <= 0.0) + 0.15
            xb = max(m_[1] for m_ in morceaux if m_[2] <= 0.0) - 0.15
            P0, P1 = E, _lerp(E, Rg, 0.42)
            A, B = (P0, P1) if sens > 0 else (P1, P0)
            A2, B2 = _decale(A, B, gradins)
            _pan_z(b, A2[0], A2[1], B2[0], B2[1], xa, xb, 0.55 + gradins, vr(cg, rng, 0.03),
                   ext_a=0.25 if sens > 0 else 0.0, ext_b=0.25 if sens < 0 else 0.0, name="Gradin")
    if boudins:
        # égout de chaume arrondi : un boudin le long de chaque égout entier
        e_tot = ep + max(gradins, 0.0)
        for (E, sens, morceaux) in ((E_av, 1, av), (E_ar, -1, ar)):
            bas = [m_ for m_ in morceaux if m_[2] <= 0.0]
            if not bas:
                continue
            xa = min(m_[0] for m_ in bas) + 0.12
            xb = max(m_[1] for m_ in bas) - 0.12
            A, B = (E, Rg) if sens > 0 else (Rg, E)
            du, dy = B[0] - A[0], B[1] - A[1]
            L_ = math.hypot(du, dy)
            nu, ny = -dy / L_, du / L_
            if ny < 0:
                nu, ny = -nu, -ny
            cz = E[0] + nu * (gradins - ep) / 2
            cy = E[1] + ny * (gradins - ep) / 2
            b.cyl(((xa + xb) / 2, cy, cz), e_tot / 2 + 0.06, xb - xa, shade(col(couleur_gradins or toit), 0.88), axis="x",
                  name="Egout")
    if faitage == "ardoise":
        b.box((x0 - rive - 0.25, yr - 0.75 * pente - 0.3, zm - 0.75), (x1 + rive + 0.25, yr + 0.5, zm + 0.75),
              shade(t, 0.72), studs="top", name="Faitage")
    elif faitage == "chaume":
        b.cyl(((x0 + x1) / 2, yr - 0.25, zm), 1.0, (x1 - x0) + 2 * rive + 0.5, shade(t, 0.82), axis="x",
              name="Faitage")

    def dessus(z):
        return H + k + (z - zf) * pente if z <= zm else H + k + (zb - z) * pente

    return dict(yr=yr, dessus=dessus, zm=zm, k=k, rise=rise, haut=yr + (0.5 if faitage == "ardoise" else 0.75))


def _toit_pignon(b, rng, x0, x1, zf, zb, H, pente, toit, mur, *, ep=0.6, rive_av=0.5, rive_ar=0.4, deb=0.5,
                 comble="plein", ep_pignon=0.9, gauche=None, droite=None, faitage="ardoise", gradins=0.0,
                 couleur_gradins=None, rives=None, boudins=False):
    """Toit à deux pans dont le PIGNON regarde la rue (faîtage le long de Z) sur des murs x0..x1 / zf..zb de
    hauteur H. comble : "plein", "pignons" ou None (voir _toit_gouttereau). gauche / droite : morceaux de pan
    [(za, zb, t0, t1)] côté x0 / côté x1. rives : couleur des planches de rive du pignon avant (None : aucune).
    Renvoie un dict (yr, xm, k, rise, dessus(x))."""
    xm = (x0 + x1) / 2
    run = xm - x0
    rise = run * pente
    k = ep * math.hypot(1, pente)
    yr = H + rise + k
    m = col(mur)
    if comble == "plein":
        b.wedge((x0, H, zf), (xm, H + rise, zb), m, down="-x", name="Pignon")
        b.wedge((xm, H, zf), (x1, H + rise, zb), m, down="+x", name="Pignon")
    elif comble == "pignons":
        for (za, zz) in ((zf, zf + ep_pignon), (zb - ep_pignon, zb)):
            b.wedge((x0, H, za), (xm, H + rise, zz), m, down="-x", name="Pignon")
            b.wedge((xm, H, za), (x1, H + rise, zz), m, down="+x", name="Pignon")
    t = col(toit)
    za, zz = zf - rive_av, zb + rive_ar
    E_g = (x0 - deb, H + k - deb * pente)
    E_d = (x1 + deb, H + k - deb * pente)
    Rg = (xm, yr)
    gauche = gauche if gauche is not None else [(za, zz, 0.0, 1.0)]
    droite = droite if droite is not None else [(za - 0.1, zz + 0.1, 0.0, 1.0)]
    for (z0, z1, t0, t1) in gauche:
        A, B = _lerp(E_g, Rg, t0), _lerp(E_g, Rg, t1)
        _pan_x(b, A[0], A[1], B[0], B[1], z0, z1, ep, vr(t, rng, 0.025), ext_b=0.45 if t1 >= 1 else 0.0)
    for (z0, z1, t0, t1) in droite:
        A, B = _lerp(E_d, Rg, t1), _lerp(E_d, Rg, t0)
        _pan_x(b, A[0], A[1], B[0], B[1], z0, z1, ep, vr(t, rng, 0.025), ext_a=0.45 if t1 >= 1 else 0.0)
    if gradins > 0:
        cg = col(couleur_gradins or toit)
        for (E, sens, morceaux) in ((E_g, 1, gauche), (E_d, -1, droite)):
            bas = [m_ for m_ in morceaux if m_[2] <= 0.0]
            if not bas:
                continue
            z0 = min(m_[0] for m_ in bas) + 0.15
            z1 = max(m_[1] for m_ in bas) - 0.15
            P0, P1 = E, _lerp(E, Rg, 0.42)
            A, B = (P0, P1) if sens > 0 else (P1, P0)
            A2, B2 = _decale(A, B, gradins)
            _pan_x(b, A2[0], A2[1], B2[0], B2[1], z0, z1, 0.55 + gradins, vr(cg, rng, 0.03),
                   ext_a=0.12 if sens > 0 else 0.0, ext_b=0.12 if sens < 0 else 0.0, name="Gradin")
    if rives is not None:
        # planches de rive le long des deux rampants du pignon avant, plus saillantes que les pans
        rc = col(rives)
        for (A, B, ea, eb) in ((E_g, Rg, 0.15, 0.3), (Rg, E_d, 0.3, 0.15)):
            A2, B2 = _decale(A, B, 0.12)
            _pan_x(b, A2[0], A2[1], B2[0], B2[1], za - 0.25, za + 0.2, ep + 0.25, rc, ext_a=ea, ext_b=eb,
                   studs="none", name="Rive", **DECO)
    if boudins:
        e_tot = ep + max(gradins, 0.0)
        for (E, sens, morceaux) in ((E_g, 1, gauche), (E_d, -1, droite)):
            bas = [m_ for m_ in morceaux if m_[2] <= 0.0]
            if not bas:
                continue
            z0 = min(m_[0] for m_ in bas) + 0.12
            z1 = max(m_[1] for m_ in bas) - 0.12
            A, B = (E, Rg) if sens > 0 else (Rg, E)
            du, dy = B[0] - A[0], B[1] - A[1]
            L_ = math.hypot(du, dy)
            nu, ny = -dy / L_, du / L_
            if ny < 0:
                nu, ny = -nu, -ny
            cx = E[0] + nu * (gradins - ep) / 2
            cy = E[1] + ny * (gradins - ep) / 2
            b.cyl((cx, cy, (z0 + z1) / 2), e_tot / 2 + 0.06, z1 - z0, shade(col(couleur_gradins or toit), 0.88), axis="z",
                  name="Egout")
    if faitage == "ardoise":
        b.box((xm - 0.75, yr - 0.75 * pente - 0.3, za - 0.35), (xm + 0.75, yr + 0.5, zz + 0.35), shade(t, 0.72),
              studs="top", name="Faitage")
    elif faitage == "chaume":
        b.cyl((xm, yr - 0.25, (za + zz) / 2), 1.0, (zz - za) + 0.5, shade(t, 0.82), axis="z", name="Faitage")

    def dessus(x):
        return H + k + (x - x0) * pente if x <= xm else H + k + (x1 - x) * pente

    return dict(yr=yr, xm=xm, k=k, rise=rise, dessus=dessus, haut=yr + (0.5 if faitage == "ardoise" else 0.75))


# ---------------------------------------------------------------------------
# Éléments de façade (plan z, extérieur vers -z)
# ---------------------------------------------------------------------------

def _pierres(b, rng, n, xr, yr, z0, eviter, couleurs=None, prot=0.14, name="Pierre", base=None):
    """Pierres isolées en saillie (« pixels » de 3-4 tons) sur une façade (plan z0, extérieur -z), hors des
    rectangles `eviter` [(x0, y0, x1, y1)]. Sans `couleurs`, les tons sont tirés du mur `base` (plus sombres et plus
    clairs que lui, pour que les pierres se lisent de loin)."""
    if couleurs is None:
        couleurs = PIXELS if base is None else (shade(base, 0.7), shade(base, 0.82), shade(base, 1.14), shade(base, 1.24))
    poses: list = []
    essais = 0
    while len(poses) < n and essais < 40 * max(1, n):
        essais += 1
        w = float(rng.choice((1.2, 1.6, 2.0, 2.6)))
        h = float(rng.choice((0.6, 0.8, 1.0, 1.2)))
        if xr[1] - xr[0] < w + 0.2 or yr[1] - yr[0] < h + 0.1:
            break
        x = round(float(rng.uniform(xr[0] + w / 2, xr[1] - w / 2)) * 10) / 10
        y = round(float(rng.uniform(yr[0], yr[1] - h)) * 10) / 10
        r = (x - w / 2, y, x + w / 2, y + h)
        if any(r[0] < e[2] + 0.25 and e[0] < r[2] + 0.25 and r[1] < e[3] + 0.25 and e[1] < r[3] + 0.25
               for e in list(eviter) + poses):
            continue
        poses.append(r)
        b.box((r[0], r[1], z0 - prot), (r[2], r[3], z0 + 0.05), vr(couleurs[int(rng.integers(len(couleurs)))], rng, 0.03),
              name=name, **DECO)
    return poses


def _lierre(b, rng, x, y_haut, z, n=4, sens=1, larg=1.6):
    """Lierre qui dégouline d'un point haut (x, y_haut) d'un mur (plan z, extérieur -z) : n plaques de feuillage de
    deux verts, décalées en quinconce (bords écartés d'au moins 0,12) et de plus en plus saillantes."""
    tons = (col("lierre"), col("lierre_clair"), shade(col("lierre"), 0.8))
    bords = ((-0.5, 0.5), (-0.3, 0.38), (-0.62, 0.22), (-0.16, 0.62))
    y = y_haut
    for i in range(n):
        ga, gb = bords[i % 4]
        xa, xb = sorted((x + sens * ga * larg, x + sens * gb * larg))
        h = float(rng.uniform(1.4, 2.4))
        b.box((xa, max(0.4, y - h), z - 0.36 - 0.1 * i), (xb, y, z + 0.05), tons[i % 3], name="Lierre", **DECO)
        y -= h * float(rng.uniform(0.55, 0.8))
        if y < 1.2:
            break


def _pale(base, f=1.3):
    """Pierre d'angle plus claire que le mur."""
    return shade(base, f)


def _chaine(b, rng, xc, zc, sx, y0, y1, couleur, prot=0.22, h=1.3, a=1.2, c_=0.7, pas=1):
    """Chaîne d'angle sur l'angle avant (xc, zc) : pierres alternées qui enveloppent l'angle (longue sur la façade
    puis sur le flanc), en saillie `prot`. sx = +1 si la façade s'étend vers +x depuis l'angle. Renvoie le nombre."""
    y, i, n = y0, 0, 0
    while y + 0.4 < y1:
        hh = min(h, y1 - y)
        if i % pas == 0:
            la, lc = (a, c_) if (i // pas) % 2 == 0 else (c_, a)
            xa, xb = sorted((xc - sx * prot, xc + sx * la))
            b.box((xa, y, zc - prot), (xb, y + hh, zc + lc), vr(couleur, rng, 0.04), name="Chaine", **DECO)
            n += 1
        y += hh
        i += 1
    return n


def _fenetre(b, x, y, w, h, z, *, verre="fenetre", allumee=False, linteau="bois_noir", appui=None, volets=None,
             planches=None, meneau=None, name="Fenetre"):
    """Petite fenêtre profonde : vitre (sombre, ou chaude en Neon si `allumee`) en léger retrait, linteau et appui
    en saillie ; volets ouverts, planches clouées ou meneau en option. (x, y) = milieu du bas de la vitre."""
    vc = col("lueur_bougie") if allumee else col(verre)
    b.box((x - w / 2, y, z - 0.12), (x + w / 2, y + h, z + 0.05), vc, name=name, **(NEON if allumee else DECO))
    if linteau:
        b.box((x - w / 2 - 0.35, y + h, z - 0.3), (x + w / 2 + 0.35, y + h + 0.5, z + 0.05), col(linteau),
              name="Linteau", **DECO)
    if appui:
        b.box((x - w / 2 - 0.25, y - 0.3, z - 0.42), (x + w / 2 + 0.25, y, z + 0.05), col(appui), studs="top",
              name="Appui", **DECO)
    if meneau:
        b.box((x - 0.11, y - 0.1, z - 0.24), (x + 0.11, y + h + 0.1, z + 0.05), col(meneau), name="Meneau", **FIN)
    if volets:
        lv = w / 2 + 0.15
        for s in (-1, 1):
            xa, xb = sorted((x + s * (w / 2 + 0.4), x + s * (w / 2 + 0.4 + lv)))
            b.box((xa, y - 0.1, z - 0.25), (xb, y + h + 0.1, z + 0.05), col(volets), name="Volet", **DECO)
    if planches:
        for (dy, ang) in ((0.28, 8.0), (0.7, -6.0)):
            b.part("block", (w + 0.5, 0.4, 0.14), (x, y + h * dy, z - 0.25), rot_z(ang), col(planches),
                   name="Planche", **DECO)


def _porte(b, x, w, h, z, *, bois="bois_fonce", linteau="bois_noir", fer="fer_fonce", seuil="moellon_fonce",
           pentures=True, noire=False):
    """Porte de planches : seuil de pierre, vantail (ou ouverture noire si `noire`), linteau, pentures de fer."""
    y0 = 0.25 if seuil else 0.0
    if seuil:
        b.box((x - w / 2 - 0.3, 0, z - 0.5), (x + w / 2 + 0.3, 0.25, z + 0.05), col(seuil), studs="top", name="Seuil")
    b.box((x - w / 2, y0, z - 0.14), (x + w / 2, h, z + 0.05), col("noir") if noire else col(bois), name="Porte",
          **DECO)
    if linteau:
        b.box((x - w / 2 - 0.4, h, z - 0.3), (x + w / 2 + 0.4, h + 0.55, z + 0.05), col(linteau), name="Linteau", **DECO)
    if pentures and not noire:
        for yy in (y0 + 0.7, h - 1.0):
            b.box((x - w / 2 + 0.15, yy, z - 0.26), (x + w / 2 - 0.45, yy + 0.22, z - 0.1), col(fer), name="Penture", **FIN)


def _ogive(b, x, y0, w, h, tip, z0, z1, couleur, name="Baie", **kw):
    """Baie à arc brisé : rectangle w × h puis pointe de hauteur `tip` (deux coins)."""
    cc = col(couleur)
    if h > 0.05:
        b.box((x - w / 2, y0, z0), (x + w / 2, y0 + h, z1), cc, name=name, **kw)
    b.wedge((x - w / 2, y0 + h, z0), (x, y0 + h + tip, z1), cc, down="-x", name=name, **kw)
    b.wedge((x, y0 + h, z0), (x + w / 2, y0 + h + tip, z1), cc, down="+x", name=name, **kw)


def _cheminee(b, rng, x, z, y0, y1, couleur, cote=1.5, penche=0.0, axe="z", suie=True):
    """Cheminée de pierre (pied y0 noyé dans le toit, haut y1), éventuellement penchée, chapeau et bouche de suie."""
    R = rot_z(penche) if axe == "z" else rot_x(penche)
    h = y1 - y0
    base = _v((x, y0, z))
    b.part("block", (cote, h, cote), base + R @ _v((0, h / 2, 0)), R, vr(couleur, rng, 0.04), name="Cheminee")
    b.part("block", (cote + 0.5, 0.45, cote + 0.5), base + R @ _v((0, h + 0.225, 0)), R, vr("pierre_ombre", rng, 0.03),
           studs="top", name="Chapeau", **DECO)
    if suie:
        b.part("block", (cote * 0.55, 0.4, cote * 0.55), base + R @ _v((0, h + 0.65, 0)), R, col("noir"), name="Suie",
               **DECO)
    return y1 + (0.85 if suie else 0.45)


def _lanterne(b, x, y, z, niv=0, verre="lueur_lanterne"):
    """Lanterne murale : celle du mobilier (11 pièces) au niveau 0, sinon une petite (3 pièces).
    (x, y, z) = point d'attache sur le mur (la lanterne pend jusqu'à y - 2,6)."""
    if niv == 0:
        with b.at((x, y, z)):
            mobilier.lanterne_murale(b, variant=0 if verre == "lueur_lanterne" else 1)
        return
    fer = col("fer_fonce")
    b.box((x - 0.12, y, z - 1.5), (x + 0.12, y + 0.25, z + 0.05), fer, name="Potence", **DECO)
    b.box((x - 0.4, y - 1.6, z - 1.6), (x + 0.4, y - 0.45, z - 0.8), col(verre), name="Lanterne", **NEON)
    b.box((x - 0.55, y - 0.45, z - 1.75), (x + 0.55, y - 0.05, z - 0.65), fer, name="Chapeau", **DECO)


def _saillie_enseigne(texte):
    long_ = min(max(1.0 + 0.75 * len(texte), 3.0), 8.0)
    return 0.9 + long_ + 0.75


def _enseigne(b, texte, variant, x, y, z_mur, z_lim):
    """Enseigne en drapeau du mobilier, platine sur le mur (plan z_mur) ; si le mot est long, la platine s'enfonce
    dans le mur pour que rien ne dépasse z_lim (vers -z)."""
    if not texte:
        return
    z0 = max(z_mur, z_lim + _saillie_enseigne(texte))
    with b.at((x, y, z0)):
        mobilier.enseigne(b, texte, variant=variant)


def _lucarne(b, rng, ys, w, h, prof, toit, mur, *, allumee=False, cadre="bois_noir", rd=1.5, avant_toit=0.45,
             chaume=False):
    """Lucarne à fronton dans un repère local : façade en z = 0 (extérieur -z), centrée en x = 0, appui sur le pan
    en y = ys, corps enfoncé de `prof` dans le toit ; petit toit à deux pans (faîtage le long de z)."""
    b.box((-w / 2, ys - 1.2, 0), (w / 2, ys + h, prof), col(mur), name="Lucarne")
    b.box((-w / 2 + 0.45, ys + 0.3, -0.12), (w / 2 - 0.45, ys + h - 0.35, 0.05),
          col("lueur_bougie") if allumee else col("fenetre"), name="Fenetre", **(NEON if allumee else DECO))
    t = shade(col(toit), 0.88)
    e = 0.35 if not chaume else 0.55
    b.wedge((-w / 2 - e, ys + h, -avant_toit), (0, ys + h + rd, prof), vr(t, rng, 0.03), down="-x", studs="top",
            name="ToitLucarne")
    b.wedge((0, ys + h, -avant_toit), (w / 2 + e, ys + h + rd, prof), vr(t, rng, 0.03), down="+x", studs="top",
            name="ToitLucarne")
    return ys + h + rd


# ---------------------------------------------------------------------------
# 1) Chaumière
# ---------------------------------------------------------------------------

def chaumiere(b, variant=0, largeur=14, profondeur=12):
    """Chaumière basse d'un niveau et combles (hauteur ≤ 15) : murs de moellons sombres en pixels, chaînes d'angle
    claires, chaume épais en gradins (ardoise moussue en v2), petites fenêtres profondes (une allumée), porte de
    planches à pentures, cheminée de pierre penchée. ≤ 60 pièces."""
    n0 = len(b.parts)
    with b.group("Chaumiere"):
        return _budget(b, n0, 60, lambda niv: _chaumiere(b, variant % 5, float(largeur), float(profondeur), niv))


def _chaumiere(b, v, L, P, niv):
    rng = _rng(b, "chaumiere", v, L, P)
    x0, x1 = -L / 2 + 0.5, L / 2 - 0.5
    zf, zb = -P / 2, P / 2 - 0.5
    mur = _mur(rng)
    s = L / 14.0
    pignon = v == 1
    H = 4.8 if pignon else 5.4
    zbc = zf + min(6.6, P - 5.0) if v == 3 else zb              # v3 : corps le long de la rue, aile derrière
    chaume_toit = vary(mix(c("chaume_fonce"), c("bois_fonce"), 0.22), rng, 0.03)
    chaume_clair = vary(mix(c("chaume"), c("chaume_fonce"), 0.25), rng, 0.03)
    b.box((x0, 0, zf), (x1, H, zbc), mur, name="Mur")
    b.box((x0 - 0.2, 0, zf - 0.2), (x1 + 0.2, 0.7, zbc + 0.2), vr("moellon_fonce", rng, 0.04), studs="top",
          name="Soubassement")
    eviter: list = []

    def fen(x, y, w, h, **kw):
        _fenetre(b, x, y, w, h, zf, **kw)
        eviter.append((x - w / 2 - 0.6, y - 0.5, x + w / 2 + 0.6, y + h + 0.7))

    def porte(x, w, h, **kw):
        _porte(b, x, w, h, zf, **kw)
        eviter.append((x - w / 2 - 0.6, 0, x + w / 2 + 0.6, h + 0.7))

    sombre = col("bois_noir")
    if v == 0:
        porte(1.2 * s, 2.2, 4.1, bois="cramoisi_fonce")
        fen(-3.3 * s, 1.8, 1.8, 1.7, allumee=True, meneau="bois_noir", appui="moellon_clair")
        fen(4.0 * s, 1.9, 1.4, 1.5, appui="moellon_clair", planches="bois_gris" if niv < 2 else None)
    elif v == 1:
        porte(2.6 * s, 2.2, 4.0)
        fen(-2.8 * s, 1.7, 1.8, 1.7, appui="moellon_clair", volets="bois_fonce" if niv < 2 else None)
    elif v == 2:
        porte(-1.2 * s, 2.2, 4.1)
        fen(3.0 * s, 1.8, 1.8, 1.7, appui="moellon_clair", volets="cramoisi_fonce" if niv < 2 else None)
        fen(-4.3 * s, 1.9, 1.4, 1.5, allumee=True, appui="moellon_clair")
    elif v == 3:
        porte(-1.4 * s, 2.0, 4.0, bois=shade(col("toile_nuit"), 0.85))
        fen(2.4 * s, 1.8, 1.6, 1.6, allumee=True, meneau="bois_noir", appui="moellon_clair")
    else:
        porte(1.2 * s, 2.2, 4.1, noire=True, linteau="bois_brule")
        fen(-3.3 * s, 1.8, 1.8, 1.7, appui="moellon_fonce", planches="bois_gris", linteau="bois_brule")
        fen(4.0 * s, 1.9, 1.4, 1.5, verre="noir", linteau="bois_brule")
        # suie au-dessus des baies
        for (xa, xb, y0_) in ((-3.3 * s - 0.7, -3.3 * s + 0.9, 4.0), (1.2 * s - 0.6, 1.2 * s + 0.9, 4.65)):
            b.box((xa, y0_, zf - 0.11), (xb, H - 0.1, zf + 0.0), col("noir"), name="Suie", **DECO)
            eviter.append((xa - 0.3, 3.8, xb + 0.3, H))
    # chaînes d'angle et pierres en saillie
    if niv < 3:
        for (xc, sx) in ((x0, 1), (x1, -1)):
            _chaine(b, rng, xc, zf, sx, 0.7, H - 0.05, _pale(mur), h=1.18, a=1.1, c_=0.7)
        eviter += [(x0 - 0.3, 0, x0 + 1.4, H), (x1 - 1.4, 0, x1 + 0.3, H)]
    if niv < 2:
        _pierres(b, rng, 6 if niv == 0 else 3, (x0 + 1.4, x1 - 1.4), (0.9, H - 0.4), zf, eviter, base=mur)
    if v == 0 and niv < 2:
        _lierre(b, rng, x0 + 1.15, H - 0.1, zf, n=3, sens=-1, larg=1.3)

    # --- toits
    if pignon:
        R = _toit_pignon(b, rng, x0, x1, zf, zb, H, 1.1, chaume_toit, mur, ep=1.15, rive_av=0.9, rive_ar=0.6, deb=0.5,
                         faitage="chaume", gradins=0.32 if niv < 2 else 0.0, couleur_gradins=chaume_clair,
                         boudins=niv < 3)
        haut = R["haut"]
        # fenêtre du comble, allumée
        _fenetre(b, 0, H + 1.6, 1.3, 1.5, zf, allumee=True, linteau="bois_noir", appui=None)
        # lucarne sur le pan gauche (-x), au milieu de la profondeur
        if niv < 2:
            xd = x0 + 2.3
            ys = R["dessus"](xd)
            with b.at((xd, 0, 0.6), yaw=90):
                _lucarne(b, rng, ys, 2.6, 2.0, 3.2, chaume_toit, mur, allumee=False, rd=1.3, chaume=True)
        yc = _cheminee(b, rng, x1 - 2.2, zb - 2.6, H + 2.0, min(14.1, R["yr"] + 1.2), "moellon_fonce", penche=-3.0)
        haut = max(haut, yc)
    elif v == 2:
        ardoise = vary(mix(c("ardoise_fonce"), c("ardoise_bleue"), 0.4), rng, 0.03)
        R = _toit_gouttereau(b, rng, x0, x1, zf, zbc, H, 1.3, ardoise, mur, ep=0.55, deb_av=0.7, deb_ar=0.6, rive=0.4,
                             faitage="ardoise")
        haut = R["haut"]
        # plaques de mousse sur le pan avant (en saillie de 0,12 sur l'ardoise)
        if niv < 2:
            E = (zf - 0.7, H + R["k"] - 0.7 * 1.3)
            Rg = (R["zm"], R["yr"])
            for (xa, xb, t0, t1) in ((x0 + 0.6, x0 + 3.4, 0.04, 0.3), (1.0, 3.6, 0.15, 0.4), (x1 - 2.6, x1 + 0.2, 0.55, 0.8)):
                A, B = _decale(_lerp(E, Rg, t0), _lerp(E, Rg, t1), 0.12)
                _pan_z(b, A[0], A[1], B[0], B[1], xa, xb, 0.3, vary(mix(c("mousse"), c("herbe_morte"), 0.35), rng, 0.05),
                       name="Mousse", **DECO)
        yc = _cheminee(b, rng, x0 + 2.0, R["zm"] + 0.8, H + 3.0, min(14.1, R["yr"] + 1.0), "moellon_fonce", penche=4.0)
        haut = max(haut, yc)
    elif v == 4:
        # toit à moitié effondré : comble vide, pan avant crevé à gauche, pan arrière affaissé, chevrons calcinés
        rv = 0.45
        av = [(0.8 * s, x1 + rv, 0.0, 1.0), (-1.6 * s, 0.8 * s, 0.5, 1.0), (-3.2 * s, -1.6 * s, 0.78, 1.0)]
        ar = [(-0.5 * s, x1 + rv + 0.1, 0.0, 1.0)]
        R = _toit_gouttereau(b, rng, x0, x1, zf, zb, H, 1.1, chaume_toit, mur, ep=1.15, deb_av=0.9, deb_ar=0.7, rive=rv,
                             comble="pignons", av=av, ar=ar, faitage=None, gradins=0.32 if niv < 2 else 0.0,
                             couleur_gradins=chaume_clair, boudins=niv < 3)
        zm, yr, k = R["zm"], R["yr"], R["k"]
        # boudin de faîtage sur la moitié restée debout
        xg, xd_ = 0.8 * s - 0.6, x1 + rv + 0.2
        b.cyl(((xg + xd_) / 2, yr - 0.25, zm), 1.0, xd_ - xg, shade(chaume_toit, 0.82), axis="x", name="Faitage")
        # pan arrière gauche affaissé dans la maison
        _pan_z(b, zm + 0.6, yr - k - 2.6, zb + 0.5, H + 0.3, x0 + 0.95, -0.5 * s, 0.9, shade(chaume_toit, 0.8),
               name="PanEffondre")
        # intérieur calciné vu par le trou
        b.box((x0 + 0.9, H, zf + 0.6), (0.8 * s, H + 0.25, zb - 0.6), col("bois_brule"), name="Calcine", **DECO)
        # panne faîtière et chevrons calcinés (un cassé)
        b.box((x0 + 0.6, yr - k - 0.75, zm - 0.3), (0.8 * s + 0.2, yr - k - 0.15, zm + 0.3), col("bois_brule"),
              name="Panne", **DECO)
        for i, xr_ in enumerate((-5.2 * s, -3.8 * s, -2.3 * s)):
            top = (xr_, yr - k - 0.5, zm - 0.1)
            if i == 1:
                top = (xr_ + 0.3, H + 3.1, zf + 2.6)
            _poutre(b, (xr_, H + 0.1, zf + 0.35), top, 0.45, col("bois_brule"), name="Chevron", **DECO)
        haut = R["yr"] + 0.75
        yc = _cheminee(b, rng, x1 - 2.0, zm + 0.9, H + 2.0, 14.1, "moellon_fonce", penche=-5.0)
        haut = max(haut, yc)
    else:
        # v0 et v3 : chaume en gradins, faîtage parallèle à la rue
        R = _toit_gouttereau(b, rng, x0, x1, zf, zbc, H, 1.02 if v == 0 else 1.2, chaume_toit, mur, ep=1.15, deb_av=0.9,
                             deb_ar=0.7, rive=0.45, faitage="chaume", gradins=0.32 if niv < 2 else 0.0,
                             couleur_gradins=chaume_clair, boudins=niv < 3)
        haut = R["haut"]
        if v == 0:
            yc = _cheminee(b, rng, x1 - 1.6, R["zm"] + 0.6, H + 2.0, min(14.1, R["yr"] + 1.4), "moellon_fonce",
                           penche=-3.5)
        else:
            yc = _cheminee(b, rng, x0 + 1.6, R["zm"] - 0.4, H + 2.0, min(14.1, R["yr"] + 1.6), "moellon_fonce",
                           penche=3.0)
        haut = max(haut, yc)

    # --- annexes
    if v == 0 and niv < 2:
        # tas de bois contre le flanc droit (+x), à l'abri du débord de toit
        b.box((x1 + 0.1, 0, zf + 2.2), (x1 + 0.95, 2.2, zf + 7.0), vr("bois", rng, 0.05), name="TasBois")
        for i, yy in enumerate((0.45, 1.25)):
            b.cyl((x1 + 0.55, yy, zf + 2.1), 0.36, 0.3, col("bois_clair"), axis="z", name="Buche", **DECO)
    if v == 3:
        # aile en retour (pignon à l'arrière) et appentis dans l'angle, tas de bois
        wx0, wx1 = x0, -0.5 * s
        Hw = H
        Rw = _toit_pignon(b, rng, wx0, wx1, zbc - 3.2, zb, Hw, 1.2, chaume_toit, mur, ep=1.15, rive_av=0.0, rive_ar=0.6,
                          deb=0.6, comble="plein", faitage=None)
        b.box((wx0, 0, zbc), (wx1, Hw, zb), mur, name="Aile")
        b.cyl(((wx0 + wx1) / 2, Rw["yr"] - 0.25, (zbc + zb) / 2 + 0.6), 0.95, zb - zbc + 0.6, shade(chaume_toit, 0.82),
              axis="z", name="Faitage")
        ax0, ax1 = wx1, x1
        b.box((ax1 - 0.6, 0, zb - 0.7), (ax1 - 0.1, 3.4, zb - 0.2), col("bois_fonce"), name="Poteau")
        b.box((ax1 - 0.6, 0, zbc + 0.4), (ax1 - 0.1, 3.4, zbc + 0.9), col("bois_fonce"), name="Poteau")
        _pan_x(b, ax0, 4.6, ax1 + 0.3, 3.5, zbc + 0.1, zb + 0.4, 0.5, vr("chaume", rng, 0.03), ext_a=0.0, name="Appentis")
        b.box((ax0 + 0.3, 0, zbc + 1.2), (ax1 - 1.0, 2.0, zb - 1.0), vr("bois", rng, 0.05), name="TasBois")
        if niv < 2:
            for yy in (0.5, 1.4):
                b.cyl((ax1 - 0.85, yy, (zbc + zb) / 2), 0.38, 0.3, col("bois_clair"), axis="x", name="Buche", **DECO)
    return {"emprise": (L, P), "hauteur": round(haut, 2)}


# ---------------------------------------------------------------------------
# Étage à colombages noirs (maisons hautes, taverne, auberge)
# ---------------------------------------------------------------------------

def _etage(b, x0, x1, y, h, z, zb, zprev, enduit, bois, fenetres, motif, panneaux, *, gorge=True, poteaux=None,
           rail=True, haut_fen=0.6):
    """Étage à colombages (plan de façade z, en encorbellement sur zprev) : hourdis (un bloc), sablière qui fait le
    tour, gorge sous l'encorbellement, poteaux, lisse d'allège, fenêtres [(x, w, allumee)] de la lisse jusqu'à
    haut_fen sous le plafond, écharpes dans les panneaux [(xa, xb)] selon le motif ("croix", "echarpe", "chevron")."""
    b.box((x0, y, z), (x1, y + h, zb), enduit, name="Hourdis")
    b.box((x0 - 0.15, y, z - 0.3), (x1 + 0.15, y + 0.6, zb + 0.15), bois, name="Sabliere")
    if gorge and zprev - z > 0.05:
        b.wedge_under((x0, y - 0.6, z - 0.3), (x1, y, zprev), bois, down="-z", name="Gorge", **DECO)
    ya, yb = y + 0.6, y + h - 0.05
    for xp in (poteaux if poteaux is not None else (x0 + 0.3, 0.0, x1 - 0.3)):
        if xp <= x0 + 0.31:
            b.box((x0 - 0.1, ya, z - 0.24), (x0 + 0.55, yb, z + 0.3), bois, name="Poteau", **DECO)
        elif xp >= x1 - 0.31:
            b.box((x1 - 0.55, ya, z - 0.24), (x1 + 0.1, yb, z + 0.3), bois, name="Poteau", **DECO)
        else:
            b.box((xp - 0.25, ya, z - 0.24), (xp + 0.25, yb, z + 0.05), bois, name="Poteau", **DECO)
    yl = y + 1.3
    if rail:
        b.box((x0 + 0.55, yl, z - 0.18), (x1 - 0.55, yl + 0.4, z + 0.05), bois, name="Lisse", **DECO)
    for (xc, w, allumee) in fenetres:
        yt = y + h - haut_fen
        b.box((xc - w / 2, yl + 0.4, z - 0.12), (xc + w / 2, yt, z + 0.05),
              col("lueur_bougie") if allumee else col("fenetre"), name="Fenetre", **(NEON if allumee else DECO))
        if allumee:
            b.box((xc - 0.1, yl + 0.3, z - 0.2), (xc + 0.1, yt + 0.1, z + 0.05), bois, name="Meneau", **FIN)
    for (xa, xb) in panneaux:
        ext = xa < 0          # panneau du côté -x
        lo, hi = ya, yb - 0.05
        if motif == "croix":
            _barre(b, xa, lo, xb, hi, z - 0.16, z + 0.05, 0.38, bois, **DECO)
            _barre(b, xa, hi, xb, lo, z - 0.16, z + 0.05, 0.38, bois, **DECO)
        elif motif == "echarpe":
            if ext:
                _barre(b, xa, lo, xb, hi, z - 0.16, z + 0.05, 0.42, bois, **DECO)
            else:
                _barre(b, xa, hi, xb, lo, z - 0.16, z + 0.05, 0.42, bois, **DECO)
        else:   # chevron
            if ext:
                _barre(b, xa, hi, xb, lo, z - 0.16, z + 0.05, 0.42, bois, **DECO)
            else:
                _barre(b, xa, lo, xb, hi, z - 0.16, z + 0.05, 0.42, bois, **DECO)


def _cote_entree(b) -> int:
    """+1 si le +x local regarde l'entrée de la zone (+Z monde), sinon -1 : on y met les détails vus à l'aller."""
    d = b._R[-1] @ np.array([1.0, 0.0, 0.0])
    return 1 if d[2] >= -1e-6 else -1


# ---------------------------------------------------------------------------
# 2) Maison de pierre
# ---------------------------------------------------------------------------

def maison_pierre(b, variant=0, largeur=16, profondeur=14, etages=2, enseigne=None):
    """Maison de pierre à deux niveaux (≈ 26 de haut) : pignon d'ardoise très pentu sur rue (v1 : toit en pavillon),
    lucarne, cheminée, volets, porte sous un petit auvent, lanterne murale ; enseigne en drapeau à l'étage.
    FORGE : grande baie au rez avec foyer rougeoyant, hotte et enclume ; AUBERGE : tonneaux à la porte. ≤ 90 pièces."""
    n0 = len(b.parts)
    with b.group("MaisonPierre"):
        return _budget(b, n0, 90, lambda niv: _maison_pierre(b, variant % 4, float(largeur), float(profondeur),
                                                             max(1, int(etages)), enseigne, niv), niveaux=5)


def _maison_pierre(b, v, L, P, n, enseigne, niv):
    rng = _rng(b, "pierre", v, L, P, n, enseigne)
    sx = _cote_entree(b)
    x0, x1 = -L / 2 + 0.5, L / 2 - 0.5
    zf, zb = -P / 2, P / 2 - 0.5
    H1, He = 6.5, 6.0
    H = H1 + He * (n - 1)
    forge = enseigne == "FORGE"
    auberge = enseigne == "AUBERGE"
    colomb = v == 2 and n >= 2
    if v == 1:
        mur = vary(mix(c("pierre_fonce"), c("pierre"), 0.3), rng, 0.03)
        clair = "pierre_pale"
    else:
        mur = _mur(rng, 0.3)
        clair = "moellon_clair"
    Hm = H1 if colomb else H
    eviter: list = []
    # --- corps (la forge a une baie ouverte au rez)
    if forge:
        bx0, bx1, by1, pb = x0 + 1.2, x0 + 8.4, 4.8, 2.6
        b.box((x0, 0, zf + pb), (x1, Hm, zb), mur, name="Mur")
        b.box((x0, by1, zf), (x1, Hm, zf + pb), mur, name="Mur")
        b.box((x0, 0, zf), (bx0, by1, zf + pb), mur, name="Mur")
        b.box((bx1, 0, zf), (x1, by1, zf + pb), mur, name="Mur")
        eviter.append((bx0 - 0.6, 0, bx1 + 0.6, by1 + 1.3))
    else:
        b.box((x0, 0, zf), (x1, Hm, zb), mur, name="Mur")
    b.box((x0 - 0.25, 0, zf - 0.25), (x1 + 0.25, 0.8, zb + 0.2), vr("moellon_fonce", rng, 0.04), studs="top",
          name="Soubassement")
    # cordon entre rez et étage
    if n >= 2 and not colomb:
        b.box((x0 - 0.3, H1 - 0.45, zf - 0.3), (x1 + 0.3, H1, zb + 0.25), vr(clair, rng, 0.03), studs="top",
              name="Cordon", **DECO)
    # chaînes d'angle
    if niv < 3:
        for (xc, s_) in ((x0, 1), (x1, -1)):
            if forge and s_ > 0:
                continue
            _chaine(b, rng, xc, zf, s_, 0.8, (H1 - 0.5) if n >= 2 else Hm - 0.05, _pale(mur), h=1.4, a=1.2, c_=0.75)
            if n >= 2 and not colomb:
                _chaine(b, rng, xc, zf, s_, H1, Hm - 0.05, _pale(mur), h=1.5, a=1.2, c_=0.75, pas=2 if niv > 0 else 1)
        eviter += [(x0 - 0.3, 0, x0 + 1.5, Hm), (x1 - 1.5, 0, x1 + 0.3, Hm)]

    # --- rez
    if forge:
        # intérieur noir de suie, linteau de bois, foyer, braises, hotte, enclume
        b.box((bx0, 0, zf + pb - 0.1), (bx1, by1, zf + pb), col("noir"), name="Fond", **DECO)
        b.box((bx0 - 0.4, by1 - 0.3, zf - 0.25), (bx1 + 0.4, by1 + 0.7, zf + 0.6), col("bois_noir"), name="Linteau",
              **DECO)
        fx0, fx1 = bx0 + 0.6, bx0 + 4.2
        b.box((fx0, 0, zf + 1.1), (fx1, 2.0, zf + pb - 0.1), vr("pierre_fonce", rng, 0.03), studs="top", name="Foyer")
        b.box((fx0 + 0.4, 2.0, zf + 1.4), (fx1 - 0.4, 2.35, zf + pb - 0.3), col("feu"), name="Braises", **NEON)
        b.boxc(((fx0 + fx1) / 2, 2.8, zf + 1.9), (1.0, 0.9, 0.7), col("feu_coeur"), yaw=20, name="Flamme", **NEON)
        b.wedge_under((fx0 - 0.3, 3.2, zf + 0.8), (fx1 + 0.3, by1 - 0.3, zf + pb - 0.1), vr("pierre_ombre", rng, 0.03),
                      down="-z", name="Hotte", **DECO)
        ax = bx1 - 1.6
        b.cyl((ax, 0.8, zf + 1.0), 0.6, 1.6, col("bois_fonce"), name="Billot", **DECO)
        b.box((ax - 0.8, 1.6, zf + 0.7), (ax + 0.5, 2.2, zf + 1.3), col("fer_fonce"), name="Enclume", **DECO)
        b.wedge((ax + 0.5, 1.75, zf + 0.75), (ax + 1.2, 2.2, zf + 1.25), col("fer_fonce"), down="+x", name="Bigorne",
                **DECO)
        if niv < 2:
            b.box((bx1 - 0.35, 1.2, zf + 1.0), (bx1 - 0.05, 3.6, zf + 1.3), col("fer"), name="Tenaille", **FIN)
        xp = (bx1 + x1) / 2 + 0.2
        _porte(b, xp, 2.2, 4.4, zf)
        eviter.append((xp - 1.7, 0, xp + 1.7, 5.2))
        xl = xp + 1.85 * (1 if xp < 0 else -1)
    elif v == 1:
        xp = 0.0
        _porte(b, xp, 2.4, 4.6, zf, bois="bois_fonce")
        for xw in (-4.6, 4.6):
            _fenetre(b, xw, 1.9, 1.8, 2.2, zf, allumee=(xw * sx > 0), meneau="bois_noir" if xw * sx > 0 else None,
                     linteau="pierre_pale", appui="pierre_pale")
            eviter.append((xw - 1.5, 1.3, xw + 1.5, 4.7))
        eviter.append((-1.9, 0, 1.9, 5.5))
        xl = -2.1
    else:
        xp = 0.0 if v == 2 else 1.4
        _porte(b, xp, 2.4, 4.6, zf, bois="bois_fonce" if v != 2 else "cramoisi_fonce")
        eviter.append((xp - 1.9, 0, xp + 1.9, 5.5))
        if v == 2:
            for xw in (-4.4, 4.4):
                _fenetre(b, xw, 1.9, 2.0, 2.2, zf, allumee=True, meneau="bois_noir", linteau="bois_noir",
                         appui="moellon_clair")
                eviter.append((xw - 1.5, 1.3, xw + 1.5, 4.7))
            xl = -2.1
        else:
            _fenetre(b, -4.2, 1.9, 1.8, 2.2, zf, allumee=True, meneau="bois_noir", appui="moellon_clair")
            _fenetre(b, 5.0, 2.0, 1.4, 2.0, zf, appui="moellon_clair", planches="bois_gris" if niv < 2 else None)
            eviter += [(-5.7, 1.3, -2.7, 4.7), (3.9, 1.3, 6.1, 4.6)]
            xl = xp - 2.0
    # petit auvent d'ardoise sur deux consoles au-dessus de la porte
    hp = 4.4 if forge else 4.6
    if niv < 3:
        b.wedge((xp - 1.9, hp + 0.75, zf - 1.3), (xp + 1.9, hp + 1.7, zf + 0.05), vr("ardoise_fonce", rng, 0.03),
                down="-z", studs="top", name="Auvent")
        for s_ in (-1, 1):
            b.wedge_under((xp + s_ * 1.6 - 0.15, hp + 0.0, zf - 1.1), (xp + s_ * 1.6 + 0.15, hp + 0.75, zf + 0.05),
                          col("bois_noir"), down="-z", name="Console", **DECO)
    _lanterne(b, xl, 4.9, zf, niv=0 if niv < 2 else 1)
    if auberge and niv < 4:
        with b.at((xp + (2.8 if xp <= 0 else -2.8), 0, zf - 1.3)):
            mobilier.tonneaux(b, variant=1)
    if niv < 2:
        _pierres(b, rng, 5, (x0 + 1.5, x1 - 1.5), (1.0, H1 - 0.8), zf, eviter + [(xl - 0.7, 1.9, xl + 0.7, 5.5)],
                 base=mur)

    # --- étage
    if colomb:
        bois = vary(c("bois_noir"), rng, 0.04)
        enduit = vary(c("enduit_ocre"), rng, 0.03)
        zj = zf - 1.0
        fen = [(-3.6, 2.0, False), (3.6, 2.0, True)]
        _etage(b, x0, x1, H1, He, zj, zb, zf, enduit, bois, fen, "croix", [(x0 + 0.55, -4.75), (4.75, x1 - 0.55)],
               poteaux=(x0 + 0.3, -2.5, 0.0, 2.5, x1 - 0.3) if niv < 2 else None)
        zg = zj
        fen_y = None
    else:
        zg = zf
        if v == 1:
            for xw, vol in ((-3.6, True), (0.0, False), (3.6, True)):
                al = xw * sx > 1.0
                _fenetre(b, xw, H1 + 1.6, 1.6 if vol else 1.4, 2.4, zf, allumee=al, linteau="pierre_pale",
                         appui="pierre_pale", volets="cramoisi_fonce" if (vol and niv < 2) else None)
        else:
            for xw, al in ((-4.2, False), (3.0, True)):
                _fenetre(b, xw, H1 + 1.6, 1.8, 2.4, zf, allumee=al, linteau="bois_noir", appui=clair,
                         volets=("bois_fonce" if v == 0 else "cramoisi_fonce") if niv < 1 else None)
        if niv < 2 and n >= 2:
            _pierres(b, rng, 3, (x0 + 1.5, x1 - 1.5), (H1 + 0.6, H - 0.6), zf, base=mur, eviter=
                     [(-6.6, H1, -1.8, H), (-0.1, H1, 6.2, H), (-1.2, H1 + 2.5, 0.2, H1 + 5.5)])
    if enseigne:
        if forge:
            _enseigne(b, enseigne, 0, -0.6, H1 + 4.3, zf, zf - 8.5)
        elif colomb:
            _enseigne(b, enseigne, 1, 0.0, H1 + 4.2, zg, zf - 8.5)
        else:
            _enseigne(b, enseigne, 2, 0.0, H1 + 4.2, zg, zf - 8.5)

    # --- toit
    ardoise = vary(mix(c("ardoise_fonce"), c(("ardoise_bleue", "ardoise_fonce", "ardoise", "ardoise_bleue")[v]), 0.35),
                   rng, 0.03)
    if v == 1:
        ye = H + 0.6
        yr = _croupe(b, rng, x0 - 0.45, x1 + 0.45, zf - 0.6, zb + 0.5, ye, 1.25, ardoise, ep=0.6)
        b.box((-0.9 - (x1 - x0 + 0.9 - (zb - zf + 1.1)) / 2, yr - 0.4, (zf + zb) / 2 - 0.5),
              (0.9 + (x1 - x0 + 0.9 - (zb - zf + 1.1)) / 2, yr + 0.45, (zf + zb) / 2 + 0.5), shade(ardoise, 0.72),
              studs="top", name="Faitage")
        # bandeau sous l'égout (le toit en pavillon repose sur une corniche)
        b.box((x0 - 0.35, H - 0.1, zf - 0.35), (x1 + 0.35, H + 0.6, zb + 0.35), vr("pierre_fonce", rng, 0.03),
              name="Corniche")
        haut = yr + 0.45
        # lucarne sur le pan avant
        if niv < 3:
            zd = zf - 0.6 + 1.9
            ys = ye + 1.9 * 1.25
            with b.at((0.0, 0, zd)):
                _lucarne(b, rng, ys, 2.8, 2.4, 3.0, ardoise, mur, allumee=True, rd=1.6)
        yc = _cheminee(b, rng, 2.6 * sx, (zf + zb) / 2 + 1.2, yr - 3.0, yr + 2.4, "pierre_fonce", penche=2.5 * sx)
        haut = max(haut, yc)
    else:
        mur_pignon = vr("ardoise_fonce", rng, 0.03) if colomb else mur
        R = _toit_pignon(b, rng, x0, x1, zg, zb, H, 1.65, ardoise, mur_pignon, ep=0.6, rive_av=0.45, rive_ar=0.4,
                         deb=0.4, rives="bois_noir" if niv < 2 else None)
        haut = R["haut"]
        # fenêtres du comble
        _fenetre(b, 0, H + 1.6, 1.4, 1.9, zg, allumee=(v != 0), linteau="bois_noir" if not colomb else None,
                 appui=None)
        if not colomb and niv < 2:
            # porte de grenier dans le pignon, poutre de palan et poulie
            yg = H + 5.4
            b.box((-0.9, yg, zg - 0.14), (0.9, yg + 2.3, zg + 0.05), col("bois_fonce"), name="PorteGrenier", **DECO)
            b.box((-1.2, yg + 2.3, zg - 0.3), (1.2, yg + 2.75, zg + 0.05), col("bois_noir"), name="Linteau", **DECO)
            b.box((-0.25, yg + 3.3, zg - 1.9), (0.25, yg + 3.8, zg + 0.6), col("bois_noir"), name="Palan")
            b.cyl((0, yg + 3.0, zg - 1.6), 0.28, 0.3, col("fer_fonce"), axis="x", name="Poulie", **DECO)
            _pierres(b, rng, 2, (-4.0, 4.0), (H + 0.6, H + 4.6), zg, [(-1.6, H + 1.0, 1.6, H + 4.4)], base=mur)
        elif niv < 2:
            _fenetre(b, 0, H + 6.6, 0.9, 1.3, zg, linteau=None, verre="fenetre")
        # lucarne sur le pan tourné vers l'entrée
        if niv < 3:
            xd = sx * (x1 - 2.4)
            with b.at((xd, 0, 1.4), yaw=-90 * sx):
                _lucarne(b, rng, R["dessus"](xd), 2.4, 2.2, 3.4, ardoise, mur, allumee=False, rd=1.4)
        xc = -sx * 3.2 if not forge else (bx0 + bx1) / 2 - 1.2
        yc = _cheminee(b, rng, xc, zf + 4.6 if forge else zb - 3.0, H + 1.0, R["yr"] + (1.6 if forge else 1.2),
                       "pierre_fonce", cote=1.9 if forge else 1.5, penche=-2.5 * sx)
        haut = max(haut, yc)
    return {"emprise": (L, P), "hauteur": round(haut, 2)}


# ---------------------------------------------------------------------------
# 3) Ruine incendiée
# ---------------------------------------------------------------------------

def maison_ruine(b, variant=0, largeur=12, profondeur=12):
    """Ruine incendiée (hauteur ≤ 12) : murs de moellons noircis aux arêtes en escalier, pas de toit, chevrons
    calcinés penchés, trous de fenêtres noirs et traînées de suie, éboulis dedans et au pied.
    v0 pignon encore debout ; v1 deux murs d'angle seulement ; v2 souche de cheminée debout et braises rouges. ≤ 50."""
    n0 = len(b.parts)
    with b.group("Ruine"):
        return _budget(b, n0, 50, lambda niv: _ruine(b, variant % 3, float(largeur), float(profondeur), niv))


def _ruine(b, v, L, P, niv):
    rng = _rng(b, "ruine", v, L, P)
    s = L / 12.0
    x0, x1 = -L / 2 + 0.4, L / 2 - 0.4
    zf, zb = -P / 2, P / 2 - 0.4
    e = 0.9
    brule = col("bois_brule")

    def pierre():
        if rng.random() < 0.25:
            return vary(mix(c("moellon_fonce"), c("pierre_noire"), 0.6), rng, 0.03)
        return vary(mix(c("moellon"), c("moellon_fonce"), float(rng.uniform(0.3, 0.8))), rng, 0.04)

    def mur(xa, xb, za, zz, h, y0=0.0, name="Mur"):
        if h - y0 > 0.1 and xb - xa > 0.1 and zz - za > 0.1:
            b.box((xa, y0, za), (xb, h, zz), pierre(), name=name)

    def suie(xa, xb, ya, yb, z=zf):
        b.box((xa, ya + 0.1, z - 0.1), (xb, yb, z + 0.05), col("noir"), name="Suie", **DECO)

    haut = 0.0
    if v == 0:
        # façade : porte et fenêtre béantes, pignon debout au-dessus (pointe droite écroulée)
        mur(x0, -3.6 * s, zf, zf + e, 6.0)
        mur(-3.6 * s, -1.4 * s, zf, zf + e, 6.0, y0=4.8)
        b.box((-3.6 * s - 0.2, 4.2, zf - 0.1), (-1.4 * s + 0.2, 4.8, zf + e - 0.12), brule, name="Linteau")
        mur(-1.4 * s, 1.4 * s, zf, zf + e, 6.0)
        mur(1.4 * s, 3.2 * s, zf, zf + e, 2.0)
        mur(1.4 * s, 3.2 * s, zf, zf + e, 6.0, y0=3.8)
        mur(3.2 * s, 4.4 * s, zf, zf + e, 6.0)
        mur(4.4 * s, x1, zf, zf + e, 4.6)
        g = pierre()
        b.wedge((x0, 6.0, zf), (0, 6.0 + (0 - x0) * 0.98, zf + e), g, down="-x", name="Pignon")
        b.box((0, 6.0, zf), (1.6 * s, 9.6, zf + e), g, name="Pignon")
        b.wedge((1.6 * s, 6.0, zf), (3.4 * s, 7.9, zf + e), g, down="+x", name="Pignon")
        b.box((-1.3, 7.3, zf - 0.12), (0.1, 9.0, zf + 0.05), col("noir"), name="TrouFenetre", **DECO)
        suie(-3.4 * s, -1.6 * s, 4.8, 6.6)
        suie(1.5 * s, 3.1 * s, 3.8, 5.5)
        haut = 6.0 + (0 - x0) * 0.98
        # flancs et fond en escalier
        for (za, zz, h) in ((zf + e, -1.5, 5.4), (-1.5, 2.0, 3.6), (2.0, zb, 2.0)):
            mur(x0, x0 + e, za, zz, h)
        for (za, zz, h) in ((zf + e, -2.5, 3.8), (-2.5, 1.5, 2.2), (1.5, zb, 0.9)):
            mur(x1 - e, x1, za, zz, h)
        for (xa, xb, h) in ((x0 + e, -1.5, 1.8), (-1.5, 2.5, 0.8), (2.5, x1 - e, 2.4)):
            mur(xa, xb, zb - e, zb, h)
        dents = ((x0, x0 + 0.6, zf + e, zf + 2.6, 5.4, 6.3), (x0, x0 + e, -1.5, -0.3, 3.6, 4.4),
                 (x1 - e, x1, -2.5, -1.4, 2.2, 3.0))
        chev = (((-1.0, 9.6, zf + e), (-2.4, 0.2, 3.0)), ((x0 + e / 2, 5.4, -2.5), (2.0, 0.2, 1.0)),
                ((0.5, 0.25, -2.0), (4.0, 0.5, 3.0)))
    elif v == 1:
        # deux murs d'angle (façade gauche et flanc gauche), le reste arasé
        mur(x0, -3.2 * s, zf, zf + e, 7.0)
        mur(-3.2 * s, -1.6 * s, zf, zf + e, 2.2)
        mur(-3.2 * s, -1.6 * s, zf, zf + e, 6.2, y0=4.0)
        mur(-1.6 * s, -0.4 * s, zf, zf + e, 5.2)
        mur(-0.4 * s, 0.6 * s, zf, zf + e, 3.0)
        mur(0.6 * s, x1, zf, zf + e, 1.1)
        suie(-3.0 * s, -1.8 * s, 4.0, 5.8)
        for (za, zz, h) in ((zf + e, -2.0, 6.6), (-2.0, 0.5, 4.2), (0.5, 3.0, 2.0), (3.0, zb, 0.7)):
            mur(x0, x0 + e, za, zz, h)
        mur(x1 - e, x1, zf + e, zb, 0.9)
        mur(x0 + e, x1 - e, zb - e, zb, 0.6)
        haut = 7.0
        dents = ((x0, x0 + 1.2, zf, zf + e, 7.0, 7.9), (x0, x0 + e, zf + e, zf + 2.4, 6.6, 7.4))
        chev = (((x0 + e / 2, 6.4, -1.0), (1.8, 0.2, 2.6)), ((-0.9 * s, 5.0, zf + e), (0.6, 0.2, 1.8)),
                ((2.0, 0.3, -3.5), (3.6, 0.6, 2.4)))
    else:
        # façade basse percée d'une brèche, souche de cheminée debout à l'arrière gauche, braises
        mur(x0, -2.0 * s, zf, zf + e, 3.4)
        mur(-2.0 * s, 1.0 * s, zf, zf + e, 1.2)
        mur(1.0 * s, 2.0 * s, zf, zf + e, 4.6)
        mur(2.0 * s, 3.6 * s, zf, zf + e, 1.8)
        b.box((2.0 * s - 0.2, 3.4, zf - 0.1), (3.6 * s + 0.2, 3.9, zf + e - 0.12), brule, name="Linteau")
        mur(2.0 * s, 3.6 * s, zf, zf + e, 4.6, y0=3.9)
        mur(3.6 * s, x1, zf, zf + e, 4.0)
        suie(2.1 * s, 3.5 * s, 3.9, 4.5)
        for (za, zz, h) in ((zf + e, -1.0, 3.0), (-1.0, 2.5, 2.0), (2.5, zb - 2.4, 1.0)):
            mur(x0, x0 + e, za, zz, h)
        for (za, zz, h) in ((zf + e, -1.0, 3.6), (-1.0, zb, 2.2)):
            mur(x1 - e, x1, za, zz, h)
        mur(x0 + 2.6, -1.0, zb - e, zb, 2.4)
        mur(-1.0, x1 - e, zb - e, zb, 1.4)
        # cheminée : souche, âtre noir, chapeau
        cx0, cz0 = x0, zb - 2.4
        b.box((cx0, 0, cz0), (cx0 + 2.6, 9.0, zb), vary(c("moellon_fonce"), rng, 0.03), name="Souche")
        b.box((cx0 + 0.4, 9.0, cz0 + 0.4), (cx0 + 2.2, 11.4, zb - 0.4), vary(c("moellon_fonce"), rng, 0.03),
              name="Souche")
        b.box((cx0 + 0.25, 11.4, cz0 + 0.25), (cx0 + 2.35, 11.85, zb - 0.25), col("pierre_ombre"), studs="top",
              name="Chapeau", **DECO)
        b.box((cx0 + 0.6, 0.0, cz0 - 0.1), (cx0 + 2.0, 1.9, cz0 + 0.6), col("noir"), name="Atre", **DECO)
        b.box((cx0 + 0.5, 1.9, cz0 - 0.12), (cx0 + 2.1, 6.5, cz0 + 0.05), col("noir"), name="Suie", **DECO)
        haut = 11.85
        dents = ((x1 - e, x1, zf + e, -2.4, 3.6, 4.4), (1.0 * s, 2.0 * s, zf, zf + e, 4.6, 5.3))
        chev = (((x1 - e / 2, 3.4, -1.5), (-1.0, 0.2, 2.0)), ((x0 + 2.6, 6.0, zb - 1.2), (1.5, 0.2, -2.0)))
    # dents des arêtes, chevrons calcinés, sol brûlé, éboulis
    for (xa, xb, za, zz, ya, yb) in dents[: (3 if niv < 2 else 1)]:
        b.box((xa + 0.05, ya, za + 0.05), (xb - 0.05, yb, zz - 0.05), pierre(), name="Dent")
    for (a, bb) in chev:
        _poutre(b, a, bb, 0.5, brule, name="Chevron", **DECO)
    b.box((x0 + e, 0, zf + e), (x1 - e, 0.2, zb - e), vary(c("brulis"), rng, 0.03), name="SolBrule", **DECO)
    nb = 5 if niv < 2 else 3
    for i in range(nb):
        xx = float(rng.uniform(x0 + e + 0.8, x1 - e - 0.8))
        zz = float(rng.uniform(zf + e + 0.8, zb - e - 0.8))
        sz = float(rng.uniform(0.9, 1.6))
        hy = sz * 0.6 + 0.07 * i
        b.boxc((xx, 0.15 + hy / 2, zz), (sz * 1.3, hy, sz), pierre(), yaw=float(rng.uniform(0, 90)), studs="top",
               name="Eboulis", **DECO)
    for (xx, zz, sz) in ((x1 - 0.6, zf - 0.9, 1.1), (x0 + 1.4, zf - 0.6, 0.85))[: (2 if niv < 3 else 0)]:
        b.boxc((xx, sz * 0.3, zz), (sz * 1.2, sz * 0.6, sz), pierre(), yaw=float(rng.uniform(0, 90)), studs="top",
               name="Eboulis", **DECO)
    if v == 2:
        # braises encore rouges dans les décombres
        for i, (xx, zz) in enumerate(((-0.6, 0.4), (1.4, 1.6), (0.4, -1.4), (2.4, -0.2))[: (4 if niv < 2 else 2)]):
            b.boxc((xx * s, 0.35, zz), (0.9, 0.3, 0.7), col("lueur_cramoisie" if i % 2 == 0 else "feu"),
                   yaw=float(rng.uniform(0, 90)), name="Braise", **NEON)
    if niv < 2:
        _pierres(b, rng, 2, (x0 + 0.8, x1 - 0.8), (0.6, 3.0), zf,
                 [(-4.2 * s, 0, -0.8 * s, 6.8), (0.8 * s, 1.5, 4.0 * s, 6.2)], couleurs=("moellon", "pierre_noire"))
    return {"emprise": (L, P), "hauteur": round(haut, 2)}


# ---------------------------------------------------------------------------
# 4) Grange
# ---------------------------------------------------------------------------

def grange(b, variant=0, largeur=20, profondeur=14):
    """Grange de planches verticales grises en deux tons sur un soubassement de pierre de 2, grand toit pignon sur rue
    (v0 chaume sombre en gradins, v1 ardoise, v2 chaume crevé), double porte (v0 un vantail entrouvert), fenil ouvert
    avec du foin, poutre de palan et poulie. Hauteur ≈ 16. ≤ 65 pièces."""
    n0 = len(b.parts)
    with b.group("Grange"):
        return _budget(b, n0, 65, lambda niv: _grange(b, variant % 3, float(largeur), float(profondeur), niv))


def _grange(b, v, L, P, niv):
    rng = _rng(b, "grange", v, L, P)
    x0, x1 = -L / 2 + 0.6, L / 2 - 0.6
    zf, zb = -P / 2, P / 2 - 0.5
    H = 7.0
    socle = vary(mix(c("moellon_fonce"), c("pierre_ombre"), 0.35), rng, 0.03)
    planche = vary(mix(c("bois_gris"), c("bois_clair"), 0.3), rng, 0.03)
    planche2 = vary(mix(c("bois_gris"), c("bois_mort"), 0.6), rng, 0.03)
    noir = col("noir")
    b.box((x0, 0, zf), (x1, 2.0, zb), socle, studs="top", name="Soubassement")
    b.box((x0 + 0.25, 2.0, zf + 0.25), (x1 - 0.25, H, zb - 0.25), planche, name="Planches")
    xa0, xa1 = x0 + 0.25, x1 - 0.25
    zw = zf + 0.25                                   # plan des planches
    pente = 0.86
    chaume = v != 1
    toit = vr("chaume_fonce", rng, 0.03) if chaume else vr("ardoise_fonce", rng, 0.03)
    ep = 1.15 if chaume else 0.6
    gauche = droite = None
    if v == 2:
        gauche = [(zf - 0.8, -0.6, 0.0, 1.0), (-0.6, 3.4, 0.62, 1.0), (3.4, zb + 0.6, 0.0, 1.0)]
    R = _toit_pignon(b, rng, xa0, xa1, zw, zb - 0.25, H, pente, toit, planche, ep=ep, rive_av=1.05, rive_ar=0.8,
                     deb=0.5, faitage="chaume" if chaume else "ardoise", gradins=0.3 if (chaume and niv < 2) else 0.0,
                     couleur_gradins=vr("chaume", rng, 0.03), gauche=gauche, droite=droite)
    xm, yr = R["xm"], R["yr"]
    haut = R["haut"]
    # --- double porte : huisserie, fond noir, vantaux (v0 : un vantail entrouvert), écharpes
    wp, hp = 6.0, 6.2
    b.box((-wp / 2, 0, zf - 0.1), (wp / 2, hp, zf + 0.3), noir, name="Fond", **DECO)
    for s_ in (-1, 1):
        xa, xb = sorted((s_ * wp / 2, s_ * (wp / 2 + 0.55)))
        b.box((xa, 0, zf - 0.32), (xb, hp + 0.5, zf + 0.3), col("bois_fonce"), name="Montant")
    b.box((-wp / 2 - 0.55, hp, zf - 0.32), (wp / 2 + 0.55, hp + 0.6, zf + 0.3), col("bois_fonce"), name="Linteau")
    vantaux = ((-1, 0.0), (1, 0.0)) if v != 0 else ((-1, 0.0), (1, 38.0))
    for (s_, ang) in vantaux:
        with b.at((s_ * wp / 2, 0, zf - 0.3), yaw=(-ang if s_ > 0 else ang)):
            # repère sur la charnière ; le vantail s'étend vers le milieu de la porte (-s_ en x)
            xa, xb = sorted((0.0, -s_ * (wp / 2 - 0.05)))
            b.box((xa, 0.1, -0.12), (xb, hp - 0.1, 0.1), planche2 if s_ > 0 else planche, name="Vantail", **DECO)
            if niv < 2:
                b.box((xa + 0.2, 1.0, -0.26), (xb - 0.2, 1.45, -0.12), col("bois_fonce"), name="Barre", **DECO)
                b.box((xa + 0.2, hp - 1.6, -0.26), (xb - 0.2, hp - 1.15, -0.12), col("bois_fonce"), name="Barre", **DECO)
                _barre(b, xa + 0.4, 1.45, xb - 0.4, hp - 1.6, -0.25, -0.12, 0.38, col("bois_fonce"), **DECO)
    # --- bardage : couvre-joints verticaux en deux tons sur le pignon avant (hors porte et fenil)
    xs = [x for x in np.arange(xa0 + 0.9, xa1 - 0.5, 1.7)]
    for i, xx in enumerate(xs):
        xx = float(xx)
        top = H + (xm - xa0 - abs(xx - xm)) * pente - 0.35
        if abs(xx) < wp / 2 + 0.9:
            if abs(xx) < 2.2:
                continue                             # fenil
            y0 = hp + 0.6
        else:
            y0 = 2.0
        if top - y0 < 0.6:
            continue
        b.box((xx - 0.3, y0, zw - 0.14), (xx + 0.3, top, zw + 0.05), planche2 if i % 2 else shade(planche, 0.86),
              name="CouvreJoint", **DECO)
    # --- fenil ouvert, foin, poutre de palan, poulie et corde
    yf0, yf1 = hp + 1.6, hp + 4.1
    b.box((-1.8, yf0 - 0.15, zw - 0.1), (1.8, yf1, zw + 0.05), noir, name="Fenil", **DECO)
    b.box((-1.6, yf0, zw - 0.7), (1.3, yf0 + 0.9, zw + 0.05), vr("foin", rng, 0.04), studs="top", name="Foin", **DECO)
    if niv < 2:
        b.box((-1.0, yf0 + 0.9, zw - 0.45), (0.7, yf0 + 1.5, zw + 0.05), vr("ble_fonce", rng, 0.04), name="Foin", **DECO)
    yh = yf1 + 0.9
    b.box((-0.3, yh, zw - 2.2), (0.3, yh + 0.55, zw + 1.0), col("bois_fonce"), name="Palan")
    if niv < 3:
        b.cyl((0, yh - 0.35, zw - 1.8), 0.32, 0.3, col("fer_fonce"), axis="x", name="Poulie", **DECO)
        b.box((-0.05, yf0 - 1.4, zw - 1.88), (0.05, yh - 0.5, zw - 1.78), col("toile_ecru"), name="Corde", **FIN)
    # --- flancs : couvre-joints et une lucarne d'aération de chaque côté
    if niv < 2:
        for s_ in (-1, 1):
            xw = xa1 if s_ > 0 else xa0
            for zz in (zf + 2.6, zf + 6.4, zf + 10.2):
                if zz > zb - 1.0:
                    continue
                xa, xb = sorted((xw, xw + s_ * 0.14))
                b.box((xa, 2.0, zz - 0.3), (xb, H - 0.1, zz + 0.3), planche2, name="CouvreJoint", **DECO)
            xa, xb = sorted((xw - s_ * 0.05, xw + s_ * 0.12))
            b.box((xa, 4.0, zf + 4.0), (xb, 5.2, zf + 5.2), noir, name="Aeration", **DECO)
    # --- abords : bottes de foin, roue appuyée
    if niv < 3:
        b.box((x1 - 2.8, 0, zf - 2.6), (x1 - 0.4, 1.2, zf - 0.6), vr("foin", rng, 0.04), studs="top", name="Botte")
        b.box((x1 - 2.4, 1.2, zf - 2.3), (x1 - 0.9, 2.2, zf - 1.0), vr("ble_fonce", rng, 0.04), studs="top", name="Botte")
    if v == 1 and niv < 3:
        b.part("cyl", (0.3, 2.6, 2.6), (x0 + 1.4, 1.45, zf - 0.35), rot_y(90) @ rot_x(8), col("bois_fonce"), name="Roue",
               **DECO)
    if v == 2:
        # trou du toit : chevrons nus au-dessus du foin
        for zz in (0.2, 1.6, 3.0):
            _poutre(b, (xa0 + 0.3, H + 0.1, zz), (xm - 0.2, yr - R["k"] - 0.3, zz), 0.4, col("bois_brule"), name="Chevron",
                    **DECO)
        b.box((xa0 + 0.3, H, -0.6), (xm - 0.4, H + 0.3, 3.4), col("bois_brule"), name="Calcine", **DECO)
    return {"emprise": (L, P), "hauteur": round(haut, 2)}


# ---------------------------------------------------------------------------
# 5) Maison du second rang
# ---------------------------------------------------------------------------

def maison_fond(b, variant=0, largeur=12, profondeur=10, etages=1):
    """Maison simple vue de loin : bloc de moellons, toit à deux pans (v0 ardoise, faîtage le long de la rue ;
    v1 chaume, pignon sur rue ; v2 ardoise, pignon sur rue, cheminée de l'autre côté), cheminée, une ou deux fenêtres
    (une allumée) ; v3 ruine. ≤ 28 pièces."""
    n0 = len(b.parts)
    with b.group("MaisonFond"):
        return _budget(b, n0, 28, lambda niv: _fond(b, variant % 4, float(largeur), float(profondeur),
                                                     max(1, int(etages)), niv))


def _fond(b, v, L, P, n, niv):
    rng = _rng(b, "fond", v, L, P, n)
    x0, x1 = -L / 2 + 0.5, L / 2 - 0.5
    zf, zb = -P / 2, P / 2 - 0.4
    mur = _mur(rng, 0.25 + 0.15 * (v % 2))
    H = 5.4 + 5.0 * (n - 1)
    if v == 3:
        # ruine : murs arasés en escalier, trou noir, deux chevrons calcinés
        pierre = vary(mix(c("moellon_fonce"), c("pierre_noire"), 0.4), rng, 0.03)
        e = 0.9
        hs = (H + 2.0, H, H - 2.2)
        for i, (xa, xb) in enumerate(((x0, -1.5), (-1.5, 2.5), (2.5, x1))):
            b.box((xa, 0, zf), (xb, max(1.2, hs[i] - (1.4 if i == 1 else 0)), zf + e), pierre, name="Mur")
        b.box((x0, 0, zf + e), (x0 + e, H - 1.0, zb), pierre, name="Mur")
        b.box((x1 - e, 0, zf + e), (x1, 2.2, zb), pierre, name="Mur")
        b.box((x0 + e, 0, zb - e), (x1 - e, 1.4, zb), pierre, name="Mur")
        b.box((x0 + 1.0, 2.2, zf - 0.12), (x0 + 2.6, 4.2, zf + 0.05), col("noir"), name="Trou", **DECO)
        b.box((x0 + 0.9, 4.2, zf - 0.11), (x0 + 2.7, H + 0.8, zf + 0.05), col("noir"), name="Suie", **DECO)
        _poutre(b, (x0 + e / 2, H - 1.2, -0.5), (1.5, 0.2, 1.8), 0.45, col("bois_brule"), name="Chevron", **DECO)
        _poutre(b, (-0.5, H - 0.4, zf + e), (0.8, 0.2, 2.6), 0.45, col("bois_brule"), name="Chevron", **DECO)
        b.box((x0 + e, 0, zf + e), (x1 - e, 0.2, zb - e), col("brulis"), name="SolBrule", **DECO)
        for (xx, zz) in ((1.5, 0.5), (-1.8, 2.0)):
            b.boxc((xx, 0.45, zz), (1.6, 0.9, 1.2), pierre, yaw=float(rng.uniform(0, 90)), studs="top", name="Eboulis",
                   **DECO)
        return {"emprise": (L, P), "hauteur": round(H + 2.0, 2)}
    b.box((x0, 0, zf), (x1, H, zb), mur, name="Mur")
    sp = 1 if v % 2 else -1
    if niv < 2:
        for (xc, s_) in ((x0, 1), (x1, -1)):
            xa, xb = sorted((xc - s_ * 0.2, xc + s_ * 0.9))
            b.box((xa, 0.0, zf - 0.2), (xb, H - 0.05, zf + 0.9), vr("moellon_clair", rng, 0.04), name="Chaine", **DECO)
    xd = sp * (L / 2 - 2.9)
    _porte(b, xd, 1.9, 3.9, zf, seuil=None, pentures=False)
    _fenetre(b, -sp * (L / 2 - 3.4), 1.9, 1.6, 1.6, zf, allumee=(n == 1), linteau="bois_noir", appui=None)
    for k in range(1, n):
        for i, xw in enumerate((-sp * (L / 2 - 3.4), sp * (L / 2 - 3.4))):
            _fenetre(b, xw, 5.4 + 5.0 * (k - 1) + 1.4, 1.5, 1.9, zf, allumee=(i == 0 and k == n - 1),
                     linteau="bois_noir" if niv < 1 else None, appui=None)
    if v == 0:
        R = _toit_gouttereau(b, rng, x0, x1, zf, zb, H, 1.2, vr("ardoise_fonce", rng, 0.03), mur, ep=0.55, deb_av=0.6,
                             deb_ar=0.5, rive=0.4)
        yc = _cheminee(b, rng, (L / 2 - 2.2) * -sp, R["zm"] + 0.8, H + 1.5, R["yr"] + 1.6, "moellon_fonce", penche=3.0)
    elif v == 1:
        R = _toit_pignon(b, rng, x0, x1, zf, zb, H, 1.1, vr("chaume_fonce", rng, 0.03), mur, ep=1.0, rive_av=0.7,
                         rive_ar=0.5, deb=0.4, faitage="chaume")
        yc = _cheminee(b, rng, -sp * 2.4, zb - 2.2, H + 1.5, R["yr"] + 1.0, "moellon_fonce", penche=-3.0)
    else:
        R = _toit_pignon(b, rng, x0, x1, zf, zb, H, 1.5, vr("ardoise", rng, 0.03), mur, ep=0.55, rive_av=0.45,
                         rive_ar=0.4, deb=0.4)
        yc = _cheminee(b, rng, sp * 2.6, zb - 2.0, H + 1.5, R["yr"] + 1.4, "moellon_fonce", penche=2.0 * sp)
    if v != 0:
        _fenetre(b, 0, H + 1.4, 1.1, 1.4, zf, allumee=(n > 1 and v == 1), linteau=None, appui=None)
    return {"emprise": (L, P), "hauteur": round(max(R["haut"], yc), 2)}


# ---------------------------------------------------------------------------
# 6) Moulin-tour
# ---------------------------------------------------------------------------

def _sur_tour(b, r, alpha_deg, y=0.0):
    """Repère tangent à une tour ronde de rayon r (axe vertical à l'origine), à l'azimut alpha (0 : face -z, positif
    vers +x) : la surface est le plan z = 0, l'extérieur vers -z."""
    a = math.radians(alpha_deg)
    return b.at((r * math.sin(a), y, -r * math.cos(a)), yaw=-alpha_deg)


def _aile(b, hub, theta, R, w, bois, *, toile=None, dechiree=False, cassee=False, zs=0.0):
    """Aile de moulin dans le plan z = zs : vergue depuis le moyeu jusqu'à R, latte extérieure à la distance w,
    barreaux, toile (entière ou déchirée en lanières)."""
    th = math.radians(theta)
    u = np.array([math.cos(th), math.sin(th), 0.0])
    p = np.array([-math.sin(th), math.cos(th), 0.0])
    Hb = np.asarray(hub, float)
    Rz = rot_z(theta)
    bc = col(bois)

    def pt(r, s, z):
        q = Hb + u * r + p * s
        return np.array([q[0], q[1], z])
    b.part("block", (R, 0.55, 0.55), pt(R / 2, 0, zs - 0.35), Rz, bc, name="Vergue")
    r0 = 2.2
    rl = R if not cassee else R * 0.8
    b.part("block", (rl - r0, 0.32, 0.25), pt((rl + r0) / 2, w, zs - 0.3), Rz, bc, name="Latte", **DECO)
    nb = max(2, int(round((rl - r0) / 2.4)))
    for i in range(nb + 1):
        r = r0 + (rl - r0) * i / nb
        b.part("block", (0.26, w + 0.32, 0.25), pt(r, w / 2, zs - 0.3), Rz, bc, name="Barreau", **DECO)
    if cassee:
        # un barreau arraché pend au bout de la latte
        b.part("block", (0.24, w * 0.8, 0.22), pt(rl + 0.5, w * 0.62, zs - 0.3), Rz @ rot_z(28), bc, name="Barreau",
               **DECO)
    if toile:
        tc = col(toile)
        if dechiree:
            for (ra, rb, sa, sb) in ((r0, rl * 0.78, 0.32, w * 0.52), (r0, rl * 0.5, w * 0.52, w - 0.12)):
                b.part("block", (rb - ra, sb - sa, 0.1), pt((ra + rb) / 2, (sa + sb) / 2, zs - 0.125), Rz, tc,
                       name="Toile", **FIN)
        else:
            b.part("block", (rl - 0.4 - r0, w - 0.44, 0.1), pt((rl - 0.4 + r0) / 2, (w + 0.32) / 2 + 0.06, zs - 0.125), Rz,
                   tc, name="Toile", **FIN)


def moulin(b, variant=0):
    """Moulin-tour de pierre (emprise 13 × 13, hauteur ≤ 40) : corps rond en trois tambours qui s'amincissent, toit
    conique (chaume sombre ; ardoise en v1-v3) jusqu'à ≈ 29, arbre et moyeu vers -Z, quatre ailes de lattes sombres
    (envergure ≈ 25) dans le plan X-Y en z ≈ -7 ; porte, trois petites fenêtres (une allumée), sacs et meule.
    v0 deux toiles déchirées et une aile cassée ; v1 ailes entoilées ; v2 ailes nues arrêtées en croix ; v3 comme v0
    sous ardoise. ≤ 95 pièces."""
    n0 = len(b.parts)
    with b.group("Moulin"):
        return _budget(b, n0, 95, lambda niv: _moulin(b, variant % 4, niv))


def _moulin(b, v, niv):
    rng = _rng(b, "moulin", v)
    pierre = [vary(mix(c("moellon"), c("moellon_fonce"), t), rng, 0.03) for t in (0.45, 0.25, 0.35)]
    b.cyl((0, 0.5, 0), 6.3, 1.0, vr("pierre_fonce", rng, 0.03), studs="top", name="Socle")
    tambours = ((5.1, 1.0, 8.0), (4.8, 8.0, 15.0), (4.5, 15.0, 21.6))
    for i, (r, y0, y1) in enumerate(tambours):
        b.cyl((0, (y0 + y1) / 2, 0), r, y1 - y0, pierre[i], studs="top", name="Tour")
    b.cyl((0, 21.9, 0), 5.0, 0.6, vr("bois_noir", rng, 0.03), studs="top", name="Rail")
    # galerie de bois à mi-hauteur : plancher, jambes de force, poteaux de garde-corps
    if niv < 2:
        yg = 9.5
        b.cyl((0, yg - 0.2, 0), 6.5, 0.4, vr("bois_fonce", rng, 0.03), studs="top", name="Galerie")
        for k_ in range(6):
            ar = math.radians(60 * k_)
            ux, uz = math.sin(ar), -math.cos(ar)
            _poutre(b, (4.9 * ux, yg - 2.3, 4.9 * uz), (6.1 * ux, yg - 0.35, 6.1 * uz), 0.3, col("bois_noir"),
                    name="Jambe", **DECO)
            b.box((6.15 * ux - 0.15, yg, 6.15 * uz - 0.15), (6.15 * ux + 0.15, yg + 1.4, 6.15 * uz + 0.15),
                  col("bois_noir"), name="Poteau", **DECO)
    # pierres en saillie (pixels), porte, fenêtres
    if niv < 2:
        for k in range(11 if niv == 0 else 4):
            a = float(rng.uniform(-80, 80))
            y = float(rng.uniform(2.0, 20.5))
            r = next(t[0] for t in tambours if t[1] <= y < t[2])
            if (-30 < a < 0 and y < 6.0) or (abs(a - 30) < 9 and 5.0 < y < 8.5) or (abs(a + 20) < 9 and 11.5 < y < 15.0) \
                    or (abs(a - 50) < 9 and 16.0 < y < 19.5):
                continue
            with _sur_tour(b, r, a, y):
                w, h = float(rng.choice((1.0, 1.4, 1.8))), float(rng.choice((0.6, 0.8)))
                b.box((-w / 2, 0, -0.16), (w / 2, h, 0.35), vr(PIXELS[k % len(PIXELS)], rng, 0.03), name="Pierre", **DECO)
    with _sur_tour(b, 5.1, -18):
        _porte(b, 0, 2.2, 4.4, -0.08, seuil="pierre_fonce", bois="bois_fonce")
    for (r, a, y, al) in ((5.1, 30, 5.6, False), (4.8, -20, 12.0, True), (4.5, 50, 16.6, False)):
        with _sur_tour(b, r, a, y):
            _fenetre(b, 0, 0, 1.2, 1.7, 0.08, allumee=al, linteau="moellon_clair", appui=None)
    # toit conique en anneaux
    chaume = v == 0
    tons = ("chaume_fonce", "chaume") if chaume else ("ardoise_fonce", "ardoise")
    anneaux = ((5.7, 0.9), (5.0, 0.9), (4.3, 0.9), (3.6, 0.9), (2.9, 0.9), (2.2, 0.9), (1.5, 0.9), (0.85, 1.0))
    y = 22.2
    for i, (r, h) in enumerate(anneaux[: (8 if niv < 3 else 6)]):
        b.cyl((0, y + h / 2, 0), r, h, vr(tons[i % 2], rng, 0.03), studs="top", name="Toit")
        y += h
    b.ball((0, y + 0.25, 0), 0.45, col("bois_noir"), name="Epi", **DECO)
    haut = y + 0.7
    # arbre, moyeu
    hub = (0.0, 24.6, -6.9)
    b.cyl((0, 24.6, -4.8), 0.5, 4.6, col("bois_noir"), axis="z", name="Arbre")
    b.box((-0.8, 23.8, -7.95), (0.8, 25.4, -6.15), col("fer_fonce"), name="Moyeu")
    # ailes
    theta0 = (22.0, 8.0, 0.0, 34.0)[v]
    bois = "bois_fonce" if v != 2 else "bois_noir"
    for i in range(4):
        th = theta0 + 90 * i
        if v in (0, 3):
            toile = (shade(col("toile_grise"), 0.82), None, shade(col("toile_ecru"), 0.68), None)[i]
            _aile(b, hub, th, 12.4 if i != 3 else 6.8, 2.5, bois, toile=toile, dechiree=True, cassee=(i == 3), zs=-7.6)
        elif v == 1:
            _aile(b, hub, th, 12.4, 2.5, bois, toile=shade(col(("toile_ecru", "toile_grise")[i % 2]), 0.72), zs=-7.6)
        else:
            _aile(b, hub, th, 12.4, 2.5, bois, zs=-7.6)
    # sacs et meule au pied de la porte
    if niv < 3:
        with _sur_tour(b, 5.1, -46):
            b.boxc((0.0, 0.55, -0.9), (1.2, 1.1, 0.9), col("toile_ecru"), yaw=12, name="Sac", **DECO)
            b.boxc((1.1, 0.45, -0.8), (1.0, 0.9, 0.8), col("toile_grise"), yaw=-8, name="Sac", **DECO)
        with _sur_tour(b, 5.1, 22):
            b.part("cyl", (0.5, 2.6, 2.6), (0, 1.35, -0.55), rot_x(-8) @ rot_y(90), vr("pierre", rng, 0.03), name="Meule",
                   **DECO)
    return {"emprise": (13.0, 13.0), "hauteur": round(max(haut, 24.6 + 12.4), 2)}


# ---------------------------------------------------------------------------
# 7) Église abandonnée
# ---------------------------------------------------------------------------

def _lancette(b, x, y0, w, h, tip, z, verre, *, neon=False, appui="pierre", cadre=None):
    """Baie lancéolée sur un plan de façade z (extérieur -z) : vitrail (rectangle et pointe) en saillie, appui de
    pierre ; embrasure sombre en option (bordure de 0,25 derrière le vitrail)."""
    if cadre:
        _ogive(b, x, y0 - 0.25, w + 0.5, h + 0.1, tip + 0.45, z - 0.1, z + 0.05, cadre, name="Embrasure", **DECO)
    _ogive(b, x, y0, w, h, tip, z - 0.18, z + 0.05, verre, name="Vitrail", **(NEON if neon else DECO))
    if appui:
        b.box((x - w / 2 - 0.3, y0 - 0.35, z - 0.45), (x + w / 2 + 0.3, y0, z + 0.05), col(appui), studs="top",
              name="Appui", **DECO)


def _contrefort(b, x, zc, sens, H1, H2, couleur, cap, l1=2.4, l2=1.2, ep=1.6, d=1.0):
    """Contrefort à deux ressauts contre un mur latéral (plan x, extérieur du côté sens·x) : bloc bas de saillie l1
    jusqu'à H1 et son glacis, bloc haut de saillie l2 jusqu'à H2 et son glacis (studs sur les glacis)."""
    down = "+x" if sens > 0 else "-x"
    xa, xb = sorted((x, x + sens * l1))
    b.box((xa, 0, zc - ep / 2), (xb, H1, zc + ep / 2), couleur, name="Contrefort")
    xa2, xb2 = sorted((x + sens * l2, x + sens * l1))
    b.wedge((xa2, H1, zc - ep / 2), (xb2, H1 + d, zc + ep / 2), col(cap), down=down, studs="top", name="Glacis")
    xa3, xb3 = sorted((x, x + sens * l2))
    b.box((xa3, H1, zc - ep / 2 + 0.15), (xb3, H2, zc + ep / 2 - 0.15), couleur, name="Contrefort")
    b.wedge((xa3, H2, zc - ep / 2 + 0.15), (xb3, H2 + d, zc + ep / 2 - 0.15), col(cap), down=down, studs="top",
            name="Glacis")


def eglise(b, variant=0, largeur=26, profondeur=44):
    """Petite église de village abandonnée, en pierre sombre (≤ 300 pièces) : clocher-porche carré de 10 × 10 au
    centre de la façade (portail en arc brisé, oculus simple, chambre des cloches ouverte avec sa cloche de laiton,
    abat-sons, pinacles d'angle), flèche octogonale d'ardoise très aiguë avec deux lucarnes, terminée par une pointe de
    fer et une boule dorée (aucune croix) ; nef à contreforts et baies lancéolées à vitraux sourds (trois en Neon
    faible, d'autres brisés), chœur plus bas ; lierre. v0 : toit de la nef crevé côté +x (chevrons calcinés,
    intérieur noir) ; v1 : intacte. Emprise largeur × profondeur, façade du clocher en z = -profondeur/2."""
    n0 = len(b.parts)
    with b.group("Eglise"):
        return _budget(b, n0, 300, lambda niv: _eglise(b, variant % 2, float(largeur), float(profondeur), niv),
                       niveaux=4)


def _eglise(b, v, L, P, niv):
    rng = _rng(b, "eglise", v, L, P)
    sx = _cote_entree(b)
    zf = -P / 2
    a = 5.0
    zt1 = zf + 2 * a
    zmt = zf + a
    wn = min(9.0, L / 2 - 4.0)
    zn0, zn1 = zf + 8.0, P / 2 - 7.0
    wc = wn - 2.5
    zc1 = P / 2 - 0.4
    Hn, Hc = 12.5, 10.5
    mur = vary(mix(c("pierre_fonce"), c("moellon_fonce"), 0.45), rng, 0.03)
    mur_t = vary(mix(c("pierre_fonce"), c("moellon_fonce"), 0.25), rng, 0.03)
    vitrail_neon = 0.62
    clair = "pierre"
    ardoise = vr("ardoise_fonce", rng, 0.03)
    ardoise2 = vr("ardoise", rng, 0.03)

    # ===== nef
    b.box((-wn, 0, zn0), (wn, Hn, zn1), mur, name="Nef")
    b.box((-wn - 0.3, 0, zn0 - 0.3), (wn + 0.3, 1.2, zn1 + 0.3), vr("pierre_ombre", rng, 0.03), studs="top",
          name="Soubassement")
    for s_ in (-1, 1):
        xa, xb = sorted((s_ * (wn - 0.1), s_ * (wn + 0.4)))
        b.box((xa, Hn - 0.75, zn0 - 0.2), (xb, Hn - 0.05, zn1 + 0.2), vr(clair, rng, 0.03), name="Corniche", **DECO)
    zcf = (zn0 + 5.0, zn0 + 12.5, zn0 + 20.0, zn0 + 27.5)
    for s_ in (-1, 1):
        for zc in zcf:
            if zc > zn1 - 1.0:
                continue
            _contrefort(b, s_ * wn, zc, s_, 7.0, 10.6, mur_t, clair)
    # baies lancéolées (vitraux sourds, quelques-uns brisés, trois en Neon faible)
    baies = [(zn0 + 2.1), (zn0 + 8.75), (zn0 + 16.25), (zn0 + 23.75)]
    n_neon = 0
    for s_ in (-1, 1):
        for i, zc in enumerate(baies):
            if zc > zn1 - 1.2:
                continue
            k = (i + (s_ > 0)) % 4
            brise = (k == 3) or (v == 0 and s_ == sx and i == 2)
            neon = (not brise) and n_neon < 3 and ((s_ == sx and i in (0, 3)) or (s_ != sx and i == 1))
            verre = col("fenetre") if brise else (shade(col(VITRAUX[k % 3]), vitrail_neon) if neon else
                                                  shade(col(VITRAUX[k % 3]), 0.85))
            n_neon += neon
            with b.at((s_ * wn, 0, zc), yaw=-90 * s_):
                _lancette(b, 0, 3.8, 1.6, 5.0, 1.7, 0.0, verre, neon=neon, appui=clair,
                          cadre="pierre_ombre" if niv < 1 else None)
    # toit de la nef (crevé côté entrée en v0)
    pente = 1.2
    za, zz = zn0 - 0.5, zn1 + 0.4
    kw = {}
    if v == 0:
        d = 0.1 if sx > 0 else 0.0              # le pan droit déborde de 0,1 de plus (pas de faces coplanaires)
        morceaux = [(za - d, -3.0, 0.0, 1.0), (-3.0, 0.5, 0.32, 1.0), (0.5, 6.0, 0.58, 1.0), (6.0, zz + d, 0.0, 1.0)]
        kw = dict(droite=morceaux) if sx > 0 else dict(gauche=morceaux)
    R = _toit_pignon(b, rng, -wn, wn, zn0, zn1, Hn, pente, ardoise, mur, ep=0.6, rive_av=0.5, rive_ar=0.4, deb=0.6,
                     comble="pignons" if v == 0 else "plein", ep_pignon=0.9, **kw)
    yr, k = R["yr"], R["k"]
    if v == 0:
        brule = col("bois_brule")
        xin = sx * wn
        xa, xb = sorted((sx * 0.4, xin - sx * 0.3))
        b.box((xa, Hn, -2.8), (xb, Hn + 0.3, 5.8), brule, name="Calcine", **DECO)
        for zr in (-2.0, 1.0, 4.2):
            _poutre(b, (xin - sx * 0.3, Hn + 0.2, zr), (sx * 0.4, yr - k - 0.3, zr), 0.45, brule, name="Chevron", **DECO)
        _poutre(b, (xin - sx * 0.6, Hn + 0.3, 2.6), (sx * 2.6, Hn + 4.6, 4.9), 0.45, brule, name="ChevronTombe", **DECO)
        b.box((sx * 0.4 - 0.3, yr - k - 0.9, -3.4), (sx * 0.4 + 0.3, yr - k - 0.3, 6.4), brule, name="Panne", **DECO)
    # ===== chœur
    b.box((-wc, 0, zn1), (wc, Hc, zc1), mur, name="Choeur")
    b.box((-wc - 0.3, 0, zn1), (wc + 0.3, 1.2, zc1 + 0.3), vr("pierre_ombre", rng, 0.03), studs="top", name="Soubassement")
    Rc = _toit_pignon(b, rng, -wc, wc, zn1 - 1.5, zc1, Hc, pente, ardoise2, mur, ep=0.6, rive_av=0.0, rive_ar=0.45, deb=0.5)
    for s_ in (-1, 1):
        _contrefort(b, s_ * wc, zc1 - 1.0, s_, 5.5, 8.4, mur_t, clair, l1=2.0, l2=1.0, ep=1.4)
        with b.at((s_ * wc, 0, zn1 + 2.6), yaw=-90 * s_):
            _lancette(b, 0, 3.4, 1.4, 4.0, 1.5, 0.0, col(VITRAUX[(s_ + 1) % 3]), appui=clair)

    # ===== clocher-porche
    b.box((-a, 0, zf), (a, 24.4, zt1), mur_t, name="Clocher")
    b.box((-a - 0.35, 0, zf - 0.35), (a + 0.35, 1.2, zt1 + 0.35), vr("pierre_ombre", rng, 0.03), studs="top",
          name="Soubassement")
    for s_ in (-1, 1):
        xa, xb = sorted((s_ * (a + 0.8), s_ * (a - 1.4)))
        b.box((xa, 0, zf - 0.8), (xb, 12.6, zf + 1.4), vr("pierre_fonce", rng, 0.03), name="Contrefort")
        xa, xb = sorted((s_ * (a + 0.4), s_ * (a - 1.0)))
        b.box((xa, 12.6, zf - 0.4), (xb, 18.0, zf + 1.0), vr("pierre_fonce", rng, 0.03), studs="top", name="Contrefort")
    for yc in (12.6, 24.4):
        b.box((-a - 0.3, yc, zf - 0.3), (a + 0.3, yc + 0.6, zt1 + 0.3), vr(clair, rng, 0.03), studs="top", name="Cordon",
              **DECO)
    # portail en arc brisé : chambranle clair, embrasure sombre, vantaux de bois, ferrures ; marches
    _ogive(b, 0, 1.2, 5.0, 5.0, 2.6, zf - 0.3, zf + 0.05, vr(clair, rng, 0.03), name="Portail", **DECO)
    _ogive(b, 0, 1.2, 4.0, 4.85, 2.1, zf - 0.38, zf + 0.05, col("pierre_ombre"), name="Embrasure", **DECO)
    _ogive(b, 0, 1.2, 3.2, 4.7, 1.7, zf - 0.46, zf + 0.05, col("bois_fonce"), name="Porte", **DECO)
    if niv < 2:
        for yy in (2.4, 4.8):
            b.box((-1.45, yy, zf - 0.58), (1.45, yy + 0.3, zf - 0.4), col("fer_fonce"), name="Ferrure", **FIN)
    b.box((-3.4, 0, zf - 1.9), (3.4, 0.4, zf - 0.35), vr("pierre_fonce", rng, 0.03), studs="top", name="Marche")
    b.box((-2.9, 0.4, zf - 1.1), (2.9, 0.8, zf - 0.35), vr("pierre_fonce", rng, 0.03), studs="top", name="Marche")
    # oculus (rond simple, pas de remplage)
    b.cyl((0, 18.4, zf - 0.15), 2.0, 0.5, vr(clair, rng, 0.03), axis="z", name="Oculus", **DECO)
    b.cyl((0, 18.4, zf - 0.22), 1.45, 0.56, shade(col("vitrail_violet"), 0.68), axis="z", name="Oculus", **NEON)
    # pilastres d'angle au-dessus des contreforts, arcatures aveugles de part et d'autre de l'oculus
    for s_ in (-1, 1):
        xa, xb = sorted((s_ * (a + 0.25), s_ * (a - 0.75)))
        b.box((xa, 18.0, zf - 0.25), (xb, 24.4, zf + 0.75), vr("pierre_fonce", rng, 0.03), name="Pilastre", **DECO)
        if niv < 2:
            _ogive(b, s_ * 3.15, 15.2, 0.9, 4.2, 1.0, zf - 0.12, zf + 0.05, col("pierre_ombre"), name="Arcature", **DECO)
    # gargouilles sous la corniche, aux quatre angles
    if niv < 2:
        for xs_ in (-1, 1):
            for zs_ in (-1, 1):
                b.boxc((xs_ * (a + 0.35), 33.9, zmt + zs_ * (a + 0.35)), (0.55, 0.5, 1.9), col("pierre_ombre"),
                       yaw=45 * xs_ * zs_, name="Gargouille", **DECO)
    # fentes des flancs du clocher
    if niv < 2:
        for s_ in (-1, 1):
            with b.at((s_ * a, 0, zmt), yaw=-90 * s_):
                _ogive(b, 0, 15.6, 0.8, 2.6, 0.7, -0.12, 0.05, col("noir"), name="Fente", **DECO)
    # chambre des cloches : piles d'angle, arcs brisés (écoinçons), dalle, abat-sons, cloche
    p, e = 2.3, 0.9
    yb0, ysp, yb1 = 25.0, 30.2, 33.6
    for xs_ in (-1, 1):
        for zs_ in (-1, 1):
            xa, xb = sorted((xs_ * a, xs_ * (a - p)))
            za_, zz_ = sorted((zmt + zs_ * a, zmt + zs_ * (a - p)))
            b.box((xa, yb0, za_), (xb, yb1, zz_), mur_t, name="Pile")
    for zz0 in (zf, zt1 - e):
        b.wedge_under((-a + p, ysp, zz0), (0, yb1, zz0 + e), mur_t, down="+x", name="Ecoincon")
        b.wedge_under((0, ysp, zz0), (a - p, yb1, zz0 + e), mur_t, down="-x", name="Ecoincon")
    for xx0 in (-a, a - e):
        b.wedge_under((xx0, ysp, zf + p), (xx0 + e, yb1, zmt), mur_t, down="+z", name="Ecoincon")
        b.wedge_under((xx0, ysp, zmt), (xx0 + e, yb1, zt1 - p), mur_t, down="-z", name="Ecoincon")
    b.box((-a, yb1, zf), (a, yb1 + 1.0, zt1), mur_t, name="Dalle")
    if niv < 2:
        for s_ in (-1, 1):
            for yy in (26.4, 28.0, 29.6):
                b.part("block", (0.22, 1.4, 2 * (a - p)), (s_ * (a - 0.5), yy, zmt), rot_z(-32 * s_), col("bois_fonce"),
                       name="AbatSon", **DECO)
    b.box((-1.7, 33.0, zmt - 0.3), (1.7, yb1, zmt + 0.3), col("bois_noir"), name="Joug", **DECO)
    b.cyl((0, 32.7, zmt), 0.5, 0.6, shade(col("laiton"), 0.85), name="Cloche", **DECO)
    b.cyl((0, 31.3, zmt), 1.15, 2.2, col("laiton"), name="Cloche", **DECO)
    b.cyl((0, 30.0, zmt), 1.5, 0.4, shade(col("laiton"), 1.08), name="Cloche", **DECO)
    b.ball((0, 29.55, zmt), 0.35, col("fer_fonce"), name="Battant", **DECO)
    # corniche, pinacles d'angle
    yc0 = yb1 + 1.0
    b.box((-a - 0.6, yc0, zf - 0.6), (a + 0.6, yc0 + 0.8, zt1 + 0.6), vr(clair, rng, 0.03), studs="top", name="Corniche")
    yc1 = yc0 + 0.8
    for xs_ in (-1, 1):
        for zs_ in (-1, 1):
            xp, zp = xs_ * (a - 0.1), zmt + zs_ * (a - 0.1)
            b.box((xp - 0.5, yc1, zp - 0.5), (xp + 0.5, yc1 + 2.4, zp + 0.5), mur_t, name="Pinacle")
            _ogive(b, xp, yc1 + 2.4, 1.0, 0.0, 1.6, zp - 0.5, zp + 0.5, ardoise, name="Pinacle", **DECO)
    # flèche octogonale d'ardoise, lucarnes, pointe de fer et boule dorée (aucune croix)
    Hf = 19.0
    ytop = _fleche(b, rng, 0, yc1, zmt, 4.5, Hf, (ardoise, ardoise2), n=8, ep=0.45, studs=True, name="Fleche")
    if niv < 3:
        r_in = 4.5 * math.cos(math.pi / 8)
        ys = yc1 + 2.6
        zd = r_in * (1 - (ys - yc1) / Hf)
        with b.at((0, 0, zmt - zd)):
            _lucarne(b, rng, ys, 1.5, 1.9, 2.4, ardoise, ardoise, rd=1.1, avant_toit=0.3)
        with b.at((sx * zd, 0, zmt), yaw=-90 * sx):
            _lucarne(b, rng, ys, 1.5, 1.9, 2.4, ardoise, ardoise, rd=1.1, avant_toit=0.3)
    b.cyl((0, ytop + 1.0, zmt), 0.14, 3.0, col("fer_fonce"), name="Pointe", **FIN)
    b.ball((0, ytop + 1.1, zmt), 0.55, col("or"), name="Boule", **DECO)
    haut = ytop + 2.5

    # ===== lierre, pierres en saillie
    if niv < 2:
        lierre = (col("lierre"), col("lierre_clair"))
        # lierre : sur le pignon de la nef à côté du clocher, et au pied du clocher (côté opposé à l'entrée)
        _lierre(b, rng, -sx * 7.0, Hn + 0.4, zn0, n=4, sens=-sx, larg=1.8)
        with b.at((-sx * a, 0, zmt + 1.5), yaw=90 * sx):
            _lierre(b, rng, 0.0, 9.0, 0.0, n=3, sens=1, larg=1.5)
        _pierres(b, rng, 7, (-a + 1.6, a - 1.6), (1.5, 24.0), zf,
                 [(-2.9, 0, 2.9, 9.2), (-2.4, 15.9, 2.4, 20.9), (-a, 12.3, a, 13.5), (-a, 14.8, -2.3, 21.0),
                  (2.3, 14.8, a, 21.0)], base=mur_t)
        for s_ in (-1, 1):
            with b.at((s_ * wn, 0, 0.0), yaw=-90 * s_):
                _pierres(b, rng, 3, (-12.0, 13.0), (1.5, 3.2), 0.0,
                         [(zc - 1.2, 0, zc + 1.2, 12) for zc in zcf] + [(bz - 1.4, 2.8, bz + 1.4, 12) for bz in baies],
                         base=mur)
    return {"emprise": (L, P), "hauteur": round(haut, 2)}


# ---------------------------------------------------------------------------
# 8) Maison haute du bourg (colombages noirs)
# ---------------------------------------------------------------------------

_STYLES_HAUTE = (
    dict(enduit="enduit_gris", toit="pignon", motifs=("croix", "echarpe"), pignon="enduit", bois="bois_noir"),
    dict(enduit="enduit_ocre", toit="lucarnes", motifs=("echarpe", "chevron"), pignon="enduit", bois="bois_noir"),
    dict(enduit="enduit_rouge", toit="pignon", motifs=("chevron", "croix"), pignon="ardoise", bois="bois_noir"),
    dict(enduit="enduit_vert", toit="pignon", motifs=("croix", "chevron"), pignon="enduit", bois="bois_fonce",
         travers=True),
    dict(enduit="creme_sali", toit="pignon", motifs=("echarpe", "chevron"), pignon="enduit", bois="bois_noir",
         oriel=True),
    dict(enduit="gris_violet", toit="pignon", motifs=("chevron", "echarpe"), pignon="ardoise", bois="bois_noir",
         tourelle=True),
)
_MARCHANDISES = {"POTIONS": ("lueur_verte", "cuir_rouge", "lueur_violette", "cuir_bleu"),
                 "BIBLIOTHÈQUE": ("cuir_rouge", "cuir_bleu", "cuir_vert", "cuir_brun"),
                 "HERBORISTE": ("mousse", "herbe_seche", "feuille_sombre", "foin")}


def _enduit(nom, rng):
    """Enduit sourd et sali (jamais pastel)."""
    if nom == "gris_violet":
        base = mix(c("enduit_gris"), c("violet_profond"), 0.25)
    elif nom == "creme_sali":
        base = mix(c("enduit_creme"), c("pierre"), 0.4)
    else:
        base = c(nom)
    return vary(shade(mix(base, c("pierre_fonce"), 0.16), 0.88), rng, 0.03)


def maison_haute(b, variant=0, largeur=14, profondeur=14, etages=3, enseigne=None):
    """Maison haute et étroite du bourg (≈ 6 + 5,5 × étages + toit ≈ 35-42) : rez de pierre sombre à devanture
    éclairée (étalage et marchandises), étages à colombages noirs (poteaux, sablières, croix de Saint-André ou
    écharpes) sur enduit sourd, chacun en encorbellement vers la rue (≤ 2,5 en tout), pignon d'ardoise à ≈ 59° avec
    planches de rive noires et petite lucarne, cheminée de pierre penchée, deux fenêtres par étage (une sur trois à la
    bougie), lanterne murale, enseigne en drapeau au rez si demandée. Variantes : v0 enduit gris ; v1 ocre, toit à
    lucarnes sur rue ; v2 sang-de-bœuf, pignon essenté d'ardoise ; v3 vert éteint, dernier étage de travers ; v4 crème
    sali, oriel sur deux étages ; v5 gris-violet, tourelle d'angle à toit conique. ≤ 95 pièces."""
    n0 = len(b.parts)
    with b.group("MaisonHaute"):
        return _budget(b, n0, 95, lambda niv: _maison_haute(b, variant % 6, float(largeur), float(profondeur),
                                                            max(1, int(etages)), enseigne, niv), niveaux=6)


def _maison_haute(b, v, L, P, n, enseigne, niv):
    S = _STYLES_HAUTE[v]
    rng = _rng(b, "haute", v, L, P, n, enseigne)
    sx = _cote_entree(b)
    x0, x1 = -L / 2 + 0.3, L / 2 - 0.3
    zf, zb = -P / 2, P / 2 - 0.3
    H0, He = 6.0, 5.5
    if S.get("oriel"):
        inc = [0.8, 0.0, 0.7, 0.5]
    elif S.get("tourelle"):
        inc = [0.9, 0.0, 0.0, 0.0]
    elif S.get("travers"):
        inc = [0.7, 0.6, 0.5, 0.0] if n >= 4 else [0.8, 0.7, 0.0]
    else:
        inc = [0.8, 0.7, 0.6, 0.4] if n >= 4 else [0.9, 0.8, 0.7]
    inc = (inc + [0.0] * 8)[:n]
    J = [min(2.5, float(t)) for t in np.cumsum(inc)]
    enduit = _enduit(S["enduit"], rng)
    bois = vary(c(S["bois"]), rng, 0.04)
    rez = vary(mix(c("pierre_fonce"), c("moellon_fonce"), 0.5), rng, 0.03)
    ardoise = vr(("ardoise", "ardoise_fonce", "ardoise_bleue")[v % 3], rng, 0.03)
    flip = -1 if v % 2 else 1                       # miroir de la disposition du rez

    # ===== rez de pierre sombre : piles d'angle, devanture éclairée, porte, lanterne, enseigne
    b.box((x0, 0, zf), (x1, H0, zb), rez, name="Rez")
    b.box((x0 - 0.2, 0, zf - 0.2), (x1 + 0.2, 0.7, zb + 0.1), vr("pierre_ombre", rng, 0.03), studs="top",
          name="Soubassement")
    if niv < 4:
        for (xc, s_) in ((x0, 1), (x1, -1)):
            xa, xb = sorted((xc - s_ * 0.25, xc + s_ * 0.95))
            b.box((xa, 0.7, zf - 0.25), (xb, H0 - 0.05, zf + 0.95), vr("pierre", rng, 0.03), name="Pile", **DECO)
    xa_, xb_ = x0 + 0.95, x1 - 0.95
    tourelle = bool(S.get("tourelle"))
    if tourelle:
        # la tourelle occupe l'angle côté sx : enseigne côté -sx, devanture au milieu, porte sous la tourelle
        flip = -sx
        sf0, sf1 = sorted((flip * (xb_ - 1.5), -flip * 0.9))
    else:
        sf0, sf1 = sorted((flip * (xa_ + 1.5), flip * 0.4))
    b.box((sf0 - 0.45, 0.7, zf - 0.2), (sf1 + 0.45, 5.0, zf + 0.05), bois, name="Devanture", **DECO)
    b.box((sf0, 1.4, zf - 0.3), (sf1, 4.55, zf + 0.05), col("lueur_bougie"), name="Vitrine", **NEON)
    nm = 2 if (sf1 - sf0) > 4.2 and niv < 2 else 1
    for i in range(nm):
        xm = sf0 + (sf1 - sf0) * (i + 1) / (nm + 1)
        b.box((xm - 0.14, 1.3, zf - 0.42), (xm + 0.14, 4.65, zf + 0.05), bois, name="Meneau", **FIN)
    b.box((sf0 - 0.6, 0.7, zf - 0.85), (sf1 + 0.6, 1.4, zf + 0.05), vr("bois", rng, 0.04), studs="top", name="Etalage",
          **DECO)
    if niv < 2 and enseigne:
        couleurs = _MARCHANDISES.get(enseigne, ("bois_clair", "cuir_brun", "bois"))
        for i in range(3):
            xg = sf0 + (sf1 - sf0) * (i + 0.5) / 3
            cg = col(couleurs[i % len(couleurs)])
            if enseigne == "POTIONS":
                b.cyl((xg, 1.9, zf - 0.55), 0.3, 1.0, cg, name="Fiole", **(NEON if i == 0 else DECO))
            elif enseigne == "HERBORISTE":
                b.boxc((xg, 1.75, zf - 0.55), (1.1, 0.7, 0.5), cg, yaw=6.0 * (i - 1), name="Herbes", **DECO)
            else:
                b.boxc((xg, 1.85, zf - 0.55), (1.0, 0.9, 0.5), cg, yaw=8.0 * (i - 1), name="Livre", **DECO)
    wd = 2.0 if L >= 13 else 1.8
    if tourelle:
        xd = sx * (xb_ - 1.0 - wd / 2)
    else:
        xd = flip * (2.1 if L >= 13 else 2.0)
    _porte(b, xd, wd, 4.3, zf, bois="bois_fonce", seuil="pierre_fonce" if niv < 2 else None, pentures=niv < 2)
    if not tourelle:
        _lanterne(b, flip * (xa_ + 0.55), 4.6, zf, niv=0 if niv < 1 else 1)
    if enseigne:
        _enseigne(b, enseigne, v % 4, (-sx if tourelle else flip) * (xb_ - 0.6), 4.7, zf, zf - 8.6)

    # ===== étages à colombages
    W = x1 - x0
    xw = 3.2 if L >= 13 else 2.7
    ww = 2.0 if L >= 13 else 1.8
    xt = sx * (x1 - 1.3)                            # tourelle (v5)
    zprev = zf
    n_top = len(b.parts)
    lit_idx = int(rng.integers(0, 2 * n))
    for k in range(n):
        y = H0 + He * k
        z = zf - J[k]
        if k == n - 1:
            n_top = len(b.parts)
        motif = S["motifs"][k % 2]
        fen = [(-xw, ww, False), (xw, ww, False)]
        pan = [(x0 + 0.55, -xw - ww / 2 - 0.1), (xw + ww / 2 + 0.1, x1 - 0.55)]
        pot = [x0 + 0.3, 0.0, x1 - 0.3]
        if S.get("oriel") and k in (0, 1):
            fen = [(-4.4, 1.4, False), (4.4, 1.4, False)] if L >= 13 else [(-3.6, 1.2, False), (3.6, 1.2, False)]
            pan = []
            pot = [x0 + 0.3, -2.75, 2.75, x1 - 0.3]
        if S.get("tourelle"):
            fen = [f for f in fen if f[0] * sx < 0]
            pan = [p_ for p_ in pan if (p_[0] + p_[1]) * sx < 0]
            pot = [p_ for p_ in pot if p_ * sx < 1.0]
        fen = [(xc_, w_, (2 * k + i) % 3 == lit_idx % 3) for i, (xc_, w_, _) in enumerate(fen)]
        if niv >= 2 and k == n - 1:
            pan = []
        if niv >= 3:
            pot = [x0 + 0.3, x1 - 0.3]
        _etage(b, x0, x1, y, He, z, zb, zprev, enduit, bois, fen, motif, pan, poteaux=pot, gorge=niv < 5)
        zprev = z
    H = H0 + He * n
    zn = zf - J[-1]

    # ===== oriel (v4), tourelle d'angle (v5)
    if S.get("oriel") and n >= 2:
        z1 = zf - J[0]
        yo0, yo1 = H0 + 0.6, H0 + 2 * He - 0.3
        b.box((-1.5, yo0, z1 - 1.2), (1.5, yo1, z1), enduit, name="Oriel")
        for s_ in (-1, 1):
            b.boxc((s_ * (2.1 - 0.16), (yo0 + yo1) / 2, z1 - 0.6 + 0.16), (1.72, yo1 - yo0, 0.45), enduit,
                   yaw=-45 * s_, name="Oriel")
        b.wedge_under((-1.5, H0 - 0.6, z1 - 1.2), (1.5, yo0, zf), bois, down="-z", name="Console")
        for kk in range(2):
            yk = H0 + He * kk
            b.box((-1.1, yk + 1.5, z1 - 1.32), (1.1, yk + He - 0.9, z1 - 1.15), col("lueur_bougie") if kk == 0 else
                  col("fenetre"), name="Fenetre", **(NEON if kk == 0 else DECO))
            b.box((-1.52, yk + 0.6 if kk else yo0 + 0.1, z1 - 1.38), (1.52, (yk + 1.1) if kk else (yo0 + 0.5), z1 - 1.15),
                  bois, name="Lisse", **DECO)
        b.wedge((-2.75, yo1, z1 - 1.5), (2.75, yo1 + 0.9, z1 + 0.05), ardoise, down="-z", studs="top", name="ToitOriel")
    if S.get("tourelle"):
        zt = zf - 0.4
        for (r, ya, yb) in ((1.1, 4.9, 5.4), (1.7, 5.4, 5.8)):
            b.cyl((xt, (ya + yb) / 2, zt), r, yb - ya, rez, name="Encorbellement")
        yt1 = H + 6.0
        b.cyl((xt, (5.8 + yt1) / 2, zt), 2.1, yt1 - 5.8, enduit, name="Tourelle")
        if niv < 3:
            for yy in (H0, H0 + He * 2):
                b.cyl((xt, yy + 0.25, zt), 2.25, 0.5, bois, name="Bandeau", **DECO)
        yy = yt1
        for i, (r, h) in enumerate(((2.55, 1.0), (2.15, 1.0), (1.72, 1.0), (1.3, 1.0), (0.9, 1.1), (0.55, 1.3))):
            b.cyl((xt, yy + h / 2, zt), r, h, vr(("ardoise_fonce", "ardoise")[i % 2], rng, 0.03), studs="top",
                  name="ToitTourelle")
            yy += h
        b.cyl((xt, yy + 0.7, zt), 0.12, 1.4, col("fer_fonce"), name="Epi", **FIN)
        b.ball((xt, yy + 0.9, zt), 0.3, col("or"), name="Epi", **DECO)
        for (a_, yy0, al) in ((-25 * sx, H0 + 1.6, True), (35 * sx, H0 + He + 1.6, False), (0, H0 + 2 * He + 1.6, False)):
            ar = math.radians(a_)
            with b.at((xt + 2.1 * math.sin(ar), 0, zt - 2.1 * math.cos(ar)), yaw=-a_):
                b.box((-0.4, yy0, -0.12), (0.4, yy0 + 2.0, 0.3), col("lueur_bougie") if al else col("fenetre"),
                      name="Fenetre", **(NEON if al else DECO))
        haut_t = yy + 1.4
    else:
        haut_t = 0.0

    # ===== toit
    if S["toit"] == "lucarnes":
        R = _toit_gouttereau(b, rng, x0, x1, zn, zb, H, 1.45, ardoise, enduit, ep=0.55, deb_av=0.25, deb_ar=0.4,
                             rive=0.25)
        for i, xd_ in enumerate((-W / 4, W / 4)):
            if niv >= 4 and i == 1:
                continue
            zd = zn + 1.5
            with b.at((xd_, 0, zd)):
                _lucarne(b, rng, R["dessus"](zd), 2.4, 2.3, 3.0, ardoise, enduit, allumee=(i == 0), rd=1.5)
        haut = R["haut"]
        yc = _cheminee(b, rng, -sx * (x1 - 2.0), R["zm"] + 1.0, H + 2.0, R["yr"] + 2.2, "pierre_fonce", penche=3.0 * sx)
    else:
        mur_p = vr("ardoise_fonce", rng, 0.03) if S["pignon"] == "ardoise" else enduit
        R = _toit_pignon(b, rng, x0, x1, zn, zb, H, 1.65, ardoise, mur_p, ep=0.55, rive_av=0.15, rive_ar=0.35,
                         deb=0.25, rives=S["bois"] if niv < 3 else None)
        haut = R["haut"]
        rise = R["rise"]
        run = (x1 - x0) / 2
        yc_ = H + rise * 0.45
        if S["pignon"] == "enduit" and niv < 3:
            hw = run * (1 - 0.45) - 0.5
            b.box((-hw, yc_, zn - 0.2), (hw, yc_ + 0.45, zn + 0.05), bois, name="Entrait", **DECO)
            b.box((-0.25, yc_ + 0.45, zn - 0.22), (0.25, H + rise - 1.0, zn + 0.05), bois, name="Poincon", **DECO)
        al = (lit_idx % 2 == 0)
        b.box((-0.9, H + 1.0, zn - 0.12), (0.9, yc_ - 0.4, zn + 0.05), col("lueur_bougie") if al else col("fenetre"),
              name="Fenetre", **(NEON if al else DECO))
        if niv < 4 and not S.get("tourelle"):
            xd_ = sx * (x1 - 2.2)
            with b.at((xd_, 0, (zn + zb) / 2 + 1.0), yaw=-90 * sx):
                _lucarne(b, rng, R["dessus"](xd_), 1.9, 1.9, 3.0, ardoise, mur_p, allumee=False, rd=1.2)
        yc = _cheminee(b, rng, -sx * 2.6, zb - 2.6, H + 1.0, R["yr"] + 2.0, "pierre_fonce", penche=-3.0 * sx)
    haut = max(haut, yc, haut_t)
    if S.get("travers"):
        # dernier étage, toit et cheminée de travers : penchés vers la rue et vers -sx, pied enfoncé dans l'étage
        _pivoter(b, n_top, (sx * x1 * 1.0, H - He, zb), rot_z(3.4 * sx) @ rot_x(-2.1))
    return {"emprise": (L, P), "hauteur": round(haut, 2)}


# ---------------------------------------------------------------------------
# 9) Taverne
# ---------------------------------------------------------------------------

def _baie_cintree(b, x, y, w, h, z, *, allumee=True, pierre=None, bois=None, appui=None):
    """Fenêtre en plein cintre (rectangle + demi-disque) sur un plan de façade z : encadrement de pierre, vitrage
    chaud (Neon) ou sombre, meneau, appui."""
    r = w / 2
    pc = col(pierre or "pierre")
    vc = col("lueur_bougie") if allumee else col("fenetre")
    kv = NEON if allumee else DECO
    b.box((x - r - 0.35, y, z - 0.1), (x + r + 0.35, y + h, z + 0.05), pc, name="Encadrement", **DECO)
    b.cyl((x, y + h, z - 0.025), r + 0.35, 0.15, pc, axis="z", name="Encadrement", **DECO)
    b.box((x - r, y, z - 0.2), (x + r, y + h, z + 0.05), vc, name="Fenetre", **kv)
    b.cyl((x, y + h, z - 0.075), r, 0.25, vc, axis="z", name="Fenetre", **kv)
    if bois is not None:
        b.box((x - 0.12, y, z - 0.32), (x + 0.12, y + h + r - 0.15, z + 0.05), col(bois), name="Meneau", **FIN)
    if appui is not None:
        b.box((x - r - 0.5, y - 0.35, z - 0.5), (x + r + 0.5, y, z + 0.05), col(appui), studs="top", name="Appui", **DECO)


def taverne(b, variant=0, largeur=24, profondeur=16):
    """Grande taverne (≈ 32 de haut) : rez de pierre à fenêtres en plein cintre chaudement éclairées, porte cintrée
    sous un auvent d'ardoise sur deux poteaux (poteaux à 2,6 de la façade), deux étages de colombages noirs sur enduit
    ocre en encorbellement, toit d'ardoise à grand pignon central sur rue (lucarne-pignon éclairée) et deux lucarnes,
    deux cheminées penchées, enseigne TAVERNE en drapeau, lanternes, tonneaux et banc à la porte. ≤ 150 pièces."""
    n0 = len(b.parts)
    with b.group("Taverne"):
        return _budget(b, n0, 150, lambda niv: _taverne(b, variant % 2, float(largeur), float(profondeur), niv),
                       niveaux=5)


def _taverne(b, v, L, P, niv):
    rng = _rng(b, "taverne", v, L, P)
    sx = _cote_entree(b)
    x0, x1 = -L / 2 + 0.4, L / 2 - 0.4
    zf, zb = -P / 2, P / 2 - 0.4
    H0, He = 7.0, 6.0
    rez = vary(mix(c("pierre_fonce"), c("moellon"), 0.4), rng, 0.03)
    enduit = vary(shade(mix(c("enduit_ocre" if v == 0 else "enduit_rouge"), c("pierre_fonce"), 0.2), 0.88), rng, 0.03)
    bois = vary(c("bois_noir"), rng, 0.04)
    ardoise = vr("ardoise_fonce", rng, 0.03)
    clair = vr("pierre", rng, 0.03)
    # ===== rez
    b.box((x0, 0, zf), (x1, H0, zb), rez, name="Rez")
    b.box((x0 - 0.25, 0, zf - 0.25), (x1 + 0.25, 0.8, zb + 0.15), vr("pierre_ombre", rng, 0.03), studs="top",
          name="Soubassement")
    for (xc, s_) in ((x0, 1), (x1, -1)):
        xa, xb = sorted((xc - s_ * 0.25, xc + s_ * 1.0))
        b.box((xa, 0.8, zf - 0.25), (xb, H0 - 0.05, zf + 1.0), clair, name="Pile", **DECO)
    for xw in (-9.0, -4.8, 4.8, 9.0):
        _baie_cintree(b, xw, 1.9, 2.4, 2.4, zf, allumee=True, pierre=clair, bois="bois_noir",
                      appui="pierre" if niv < 2 else None)
    # porte cintrée
    b.box((-1.75, 0.3, zf - 0.1), (1.75, 5.0, zf + 0.05), clair, name="Encadrement", **DECO)
    b.cyl((0, 5.0, zf - 0.025), 1.75, 0.15, clair, axis="z", name="Encadrement", **DECO)
    b.box((-1.3, 0.3, zf - 0.22), (1.3, 5.0, zf + 0.05), col("bois_fonce"), name="Porte", **DECO)
    b.cyl((0, 5.0, zf - 0.085), 1.3, 0.27, col("bois_fonce"), axis="z", name="Porte", **DECO)
    b.box((-2.1, 0, zf - 0.6), (2.1, 0.3, zf + 0.05), vr("pierre_fonce", rng, 0.03), studs="top", name="Seuil")
    if niv < 2:
        for yy in (1.4, 3.8):
            b.box((-1.15, yy, zf - 0.34), (0.6, yy + 0.22, zf - 0.2), col("fer_fonce"), name="Penture", **FIN)
    # auvent d'ardoise sur deux poteaux et deux jambes de force
    zp = zf - 2.55
    for s_ in (-1, 1):
        b.box((s_ * 2.6 - 0.25, 0, zp - 0.25), (s_ * 2.6 + 0.25, 4.6, zp + 0.25), bois, name="Poteau")
        if niv < 3:
            _poutre(b, (s_ * 2.6, 3.7, zp), (s_ * 2.6, 4.6, zf - 0.05), 0.25, bois, name="Jambe", **DECO)
    b.box((-3.0, 4.6, zp - 0.3), (3.0, 5.1, zp + 0.3), bois, name="Sabliere")
    b.wedge((-3.3, 5.1, zf - 3.0), (3.3, 6.3, zf + 0.05), ardoise, down="-z", studs="top", name="Auvent")
    if niv < 3:
        zl = zp + 0.2
        b.box((-0.05, 3.5, zl - 0.05), (0.05, 4.6, zl + 0.05), col("chaine"), name="Tige", **FIN)
        b.box((-0.4, 2.3, zl - 0.4), (0.4, 3.2, zl + 0.4), col("lueur_lanterne"), name="Lanterne", **NEON)
        b.box((-0.55, 3.2, zl - 0.55), (0.55, 3.55, zl + 0.55), col("fer_fonce"), name="Chapeau", **DECO)
    # tonneaux et banc
    if niv < 4:
        with b.at((sx * -6.9, 0, zf - 1.4)):
            mobilier.tonneaux(b, variant=1)
    if niv < 3:
        xa, xb = sorted((sx * 3.5, sx * 6.9))
        b.box((xa + 0.3, 0, zf - 1.0), (xb - 0.3, 0.9, zf - 0.6), col("bois_fonce"), name="Banc")
        b.box((xa, 0.9, zf - 1.25), (xb, 1.2, zf - 0.35), col("bois"), studs="top", name="Banc", **DECO)
    if niv < 1:
        _pierres(b, rng, 2, (x0 + 1.5, x1 - 1.5), (1.0, H0 - 0.6), zf,
                 [(-10.9, 1.1, -7.1, 5.6), (-6.7, 1.1, -2.9, 5.6), (2.9, 1.1, 6.7, 5.6), (7.1, 1.1, 10.9, 5.6),
                  (-2.3, 0, 2.3, 7.0)], couleurs=("pierre", "pierre_ombre", "moellon_fonce"))

    # ===== deux étages à colombages
    z1, z2 = zf - 0.9, zf - 1.7
    fen = [(-8.4, 2.0), (-2.75, 2.0), (2.75, 2.0), (8.4, 2.0)]
    pan = [(x0 + 0.55, -9.5), (-7.3, -5.75), (5.75, 7.3), (9.5, x1 - 0.55)]
    pot = [x0 + 0.3, -5.5, 0.0, 5.5, x1 - 0.3]
    for k, (z, zp_, motif) in enumerate(((z1, zf, "croix"), (z2, z1, "echarpe"))):
        y = H0 + He * k
        allum = [(xc, w, (i + 2 * k) % 3 == 0) for i, (xc, w) in enumerate(fen)]
        _etage(b, x0, x1, y, He, z, zb, zp_, enduit, bois, allum, motif if niv < 2 else "echarpe",
               pan if niv < 3 else [], poteaux=pot if niv < 3 else None)
    H = H0 + 2 * He
    _enseigne(b, "TAVERNE", 0, sx * 4.6, H0 + 4.3, z1, zf - 8.5)
    _lanterne(b, -sx * 2.6, 4.9, zf, niv=0 if niv < 1 else 1)

    # ===== toit : gouttereau sur rue, grand pignon central, deux lucarnes, deux cheminées
    R = _toit_gouttereau(b, rng, x0, x1, z2, zb, H, 1.15, ardoise, enduit, ep=0.6, deb_av=0.3, deb_ar=0.5, rive=0.3)
    yr, zm = R["yr"], R["zm"]
    gw = 4.2
    hz = 3.0
    b.box((-gw, H, z2), (gw, H + hz, z2 + 4.5), enduit, name="Pignon")
    b.box((-gw - 0.15, H, z2 - 0.3), (gw + 0.15, H + 0.6, z2 + 4.5), bois, name="Sabliere")
    Rg = _toit_pignon(b, rng, -gw, gw, z2, z2 + 8.0, H + hz, 1.35, ardoise, enduit, ep=0.55, rive_av=0.25, rive_ar=0.0,
                      deb=0.3, rives="bois_noir" if niv < 2 else None)
    b.box((-1.6, H + 1.0, z2 - 0.12), (1.6, H + hz + 1.9, z2 + 0.05), col("lueur_bougie"), name="Fenetre", **NEON)
    for xm_ in (-0.12, ):
        b.box((xm_, H + 0.9, z2 - 0.24), (xm_ + 0.24, H + hz + 2.0, z2 + 0.05), bois, name="Meneau", **FIN)
    b.box((-gw + 0.3, H + hz + 2.0, z2 - 0.2), (gw - 0.3, H + hz + 2.45, z2 + 0.05), bois, name="Entrait", **DECO)
    if niv < 3:
        for xd_ in (-8.0, 8.0):
            zd = z2 + 1.8
            with b.at((xd_, 0, zd)):
                _lucarne(b, rng, R["dessus"](zd), 2.4, 2.1, 3.0, ardoise, enduit, allumee=(xd_ * sx > 0), rd=1.4)
    haut = max(R["haut"], Rg["haut"])
    for s_ in (-1, 1):
        yc = _cheminee(b, rng, s_ * (x1 - 1.6), zm + 1.2, H + 2.0, yr + 2.4, "pierre_fonce", cote=1.7,
                       penche=2.5 * s_ * (1 if s_ * sx > 0 else -0.6))
        haut = max(haut, yc)
    return {"emprise": (L, P), "hauteur": round(haut, 2)}


# ---------------------------------------------------------------------------
# 10) Halle du marché
# ---------------------------------------------------------------------------

def halle(b, variant=0, largeur=26, profondeur=14):
    """Halle de marché couverte (≈ 20 de haut) : dallage, poteaux de bois sombre sur dés de pierre, jambes de force,
    côtés ouverts, grand toit d'ardoise en croupe avec arêtiers et lanternon au faîtage, étals intérieurs (comptoirs,
    caisses, sacs, fioles colorées dont quelques-unes en Neon), lanternes suspendues, planche MARCHÉ sous l'avant-toit
    côté couloir. Rien devant la façade (les étals de l'accotement sont posés par zone.py). ≤ 110 pièces."""
    n0 = len(b.parts)
    with b.group("Halle"):
        return _budget(b, n0, 110, lambda niv: _halle(b, variant % 2, float(largeur), float(profondeur), niv),
                       niveaux=4)


def _halle(b, v, L, P, niv):
    rng = _rng(b, "halle", v, L, P)
    zf, zb = -P / 2, P / 2
    xp = L / 2 - 1.0
    zpf, zpb = zf + 1.0, zb - 1.0
    bois = vary(c("bois_noir"), rng, 0.04)
    bois2 = vary(c("bois_fonce"), rng, 0.04)
    ardoise = vr("ardoise_fonce", rng, 0.03)
    yp = 8.6
    b.box((-xp - 0.6, 0, zpf - 0.6), (xp + 0.6, 0.35, zpb + 0.6), vr("dalle", rng, 0.03), studs="top", name="Dallage")
    xs = [-xp + i * (2 * xp) / 4 for i in range(5)]
    for zz in (zpf, zpb):
        for xx in xs:
            b.box((xx - 0.7, 0.35, zz - 0.7), (xx + 0.7, 1.3, zz + 0.7), vr("pierre_fonce", rng, 0.04), studs="top",
                  name="De")
            b.box((xx - 0.4, 1.3, zz - 0.4), (xx + 0.4, yp, zz + 0.4), bois, name="Poteau")
    # sablières, entraits
    b.box((-xp - 0.6, yp, zpf - 0.5), (xp + 0.6, yp + 0.8, zpf + 0.5), bois2, name="Sabliere")
    b.box((-xp - 0.6, yp, zpb - 0.5), (xp + 0.6, yp + 0.8, zpb + 0.5), bois2, name="Sabliere")
    for xx in (-xp, xp):
        b.box((xx - 0.5, yp, zpf + 0.5), (xx + 0.5, yp + 0.8, zpb - 0.5), bois2, name="Sabliere")
    for xx in xs[1:4]:
        b.box((xx - 0.35, yp + 0.1, zpf + 0.5), (xx + 0.35, yp + 0.7, zpb - 0.5), bois2, name="Entrait", **DECO)
    # jambes de force sur la façade côté couloir
    if niv < 2:
        for i, xx in enumerate(xs):
            for s_ in (-1, 1):
                if (i == 0 and s_ < 0) or (i == 4 and s_ > 0):
                    continue
                _poutre(b, (xx + s_ * 0.3, yp - 1.8, zpf), (xx + s_ * 1.7, yp + 0.05, zpf), 0.32, bois, name="Jambe",
                        **DECO)
    # toit en croupe
    pente = 0.95
    ep = 0.6
    k = ep * math.hypot(1, pente)
    deb = 1.15
    ye = yp + 0.8 + k - deb * pente
    xe, ze0, ze1 = xp + 0.95, zpf - 0.5 - deb, zpb + 0.5 + deb
    yr = _croupe(b, rng, -xe, xe, ze0, ze1, ye, pente, ardoise, ep=ep, name="Toit")
    run = (ze1 - ze0) / 2
    zm = (ze0 + ze1) / 2
    b.box((-xe + run - 0.4, yr - 0.4, zm - 0.6), (xe - run + 0.4, yr + 0.45, zm + 0.6), shade(ardoise, 0.72), studs="top",
          name="Faitage")
    if niv < 2:
        for (sxx, szz) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            a = _v((sxx * xe, ye, ze0 if szz < 0 else ze1))
            bb = _v((sxx * (xe - run), yr, zm))
            nrm = _v((sxx * 0.5, 1.0, szz * 0.5))
            nrm /= np.linalg.norm(nrm)
            _poutre(b, a + nrm * 0.12, bb + nrm * 0.12, 0.42, shade(ardoise, 0.72), name="Arretier", **DECO)
    # lanternon au faîtage : caisse à claire-voie sombre, petit toit, épi
    lw, ld = 2.2, 1.6
    b.box((-lw, yr - 0.3, zm - ld), (lw, yr + 1.6, zm + ld), bois2, name="Lanternon")
    b.box((-lw + 0.3, yr + 0.5, zm - ld - 0.1), (lw - 0.3, yr + 1.3, zm + ld + 0.1), col("noir"), name="ClaireVoie",
          **DECO)
    b.wedge((-lw - 0.3, yr + 1.6, zm - ld - 0.4), (lw + 0.3, yr + 2.5, zm), ardoise, down="-z", studs="top", name="Toit")
    b.wedge((-lw - 0.3, yr + 1.6, zm), (lw + 0.3, yr + 2.5, zm + ld + 0.4), ardoise, down="+z", studs="top", name="Toit")
    b.cyl((0, yr + 3.0, zm), 0.12, 1.0, col("fer_fonce"), name="Epi", **FIN)
    b.ball((0, yr + 3.6, zm), 0.32, col("or"), name="Epi", **DECO)
    haut = yr + 3.9
    # planche MARCHÉ sous l'avant-toit, côté couloir (accrochée à la sablière par deux chaînettes)
    pl = b.box((-3.2, yp - 1.9, zpf - 0.72), (3.2, yp - 0.5, zpf - 0.52), vr("bois_fonce", rng, 0.03), name="Planche", **DECO)
    pl.label = {"face": "Front", "text": "MARCHÉ", "color": col("dorure"), "bg": None, "font": "serif"}
    for xx in (-2.6, 2.6):
        b.box((xx - 0.05, yp - 0.5, zpf - 0.67), (xx + 0.05, yp, zpf - 0.57), col("chaine"), name="Chainette", **FIN)
    # étals intérieurs
    for (xa, xb, zc, sens) in ((-10.0, -3.2, zpf + 3.2, 1), (2.6, 9.4, zpb - 3.2, -1)):
        b.box((xa, 0.35, zc - 1.0), (xb, 2.9, zc + 1.0), vr("bois", rng, 0.04), name="Comptoir")
        b.box((xa - 0.2, 2.9, zc - 1.2), (xb + 0.2, 3.2, zc + 1.2), vr("bois_clair", rng, 0.04), studs="top",
              name="Plateau", **DECO)
    marchandises = (("cyl", -9.0, "lueur_verte", True), ("cyl", -8.2, "cuir_rouge", False),
                    ("cyl", -7.4, "lueur_violette", True), ("box", -5.8, "foin", False), ("box", -4.3, "toile_ecru", False))
    for (forme, xx, cc, neon) in marchandises[: (5 if niv < 2 else 3)]:
        if forme == "cyl":
            b.cyl((xx, 3.65, zpf + 2.9), 0.3, 0.9, col(cc), name="Fiole", **(NEON if neon else DECO))
        else:
            b.boxc((xx, 3.7, zpf + 3.2), (1.2, 1.0, 1.0), col(cc), yaw=12, name="Sac", **DECO)
    if niv < 3:
        b.boxc((3.9, 3.75, zpb - 3.2), (1.5, 1.1, 1.2), vr("bois_clair", rng, 0.05), yaw=-8, name="Caisse", **DECO)
        b.boxc((5.8, 3.65, zpb - 3.0), (1.3, 0.9, 1.1), col("ble_fonce"), yaw=10, name="Panier", **DECO)
        b.cyl((7.6, 3.6, zpb - 3.3), 0.32, 0.8, col("lueur_doree"), name="Fiole", **NEON)
        b.box((-1.0, 0.35, zpb - 1.9), (1.0, 1.6, zpb - 0.4), vr("bois_clair", rng, 0.05), name="Caisse")
    # lanternes suspendues aux entraits
    if niv < 3:
        for xx in (xs[1], xs[3]):
            b.box((xx - 0.05, yp - 1.7, -0.05), (xx + 0.05, yp + 0.1, 0.05), col("chaine"), name="Chainette", **FIN)
            mobilier._lanterne(b, xx, yp - 3.5, 0.0, col("fer_fonce"), "lueur_lanterne", 0.65, name="Lanterne")
    return {"emprise": (L, P), "hauteur": round(haut, 2)}
