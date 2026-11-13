"""Mobilier urbain et petits objets de la carte « île du futur » (CarteEgghead).

Palmiers à cocos, jardinières rayées rouge et blanc à haies en boules, lampadaires (à écran ou soucoupe), bancs
arrondis, poubelles-capsules, feux tricolores, potelets, coupoles de verre à miniature, panneaux-pictogrammes sans
texte, champignons lumineux à pois, rambardes blanches à boules (STYLE.md § 4, recettes M01-M16).

Posés par carte.py d'après `plan.MOBILIER` (≈ 200 poses) ; les autres modules peuvent importer les petits objets
(import gardé). Conventions : origine au pied (centre de l'emprise, y = 0), **avant = -Z local** (écran, assise,
feux, pictogramme), largeur le long de X local. Tout est construit dans le repère courant : n'importe quel yaw,
n'importe quel groupe parent. Chaque fonction renvoie {"emprise": (x, z), "hauteur": h, "pieces", "neon",
"transparentes"} (emprise et hauteur mesurées dans le repère local de l'appel).

Plafonds par appel (plan.BUDGET_FONCTION) : palmier 28 ; groupe_palmiers 16 + 28 n ; jardiniere 70 ; lampadaire 10
(1 Neon) ; banc 10 ; poubelle 6 ; feu_tricolore 14 (3 Neon) ; potelet 5 ; coupole_miniature 14 (1 verre) ;
panneau 14 (3 Neon) ; champignon_lumineux 11 (5 Neon) ; rambarde 1 + 5 par travée de 8.

    python apercu.py assets.mobilier:palmier --variant 0 --res 1200x675 --samples 12
"""

from __future__ import annotations

import math

import numpy as np

from kit import rot_x, rot_y, rot_z, shade, varier
from palette import c

# Détails fins : ni collision ni ombre ; décor sans collision qui garde son ombre
FIN = {"collide": False, "shadow": False}
SANS = {"collide": False}

VERRE_T = 0.45          # transparence du verre des coupoles


# ---------------------------------------------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------------------------------------------

def _repere(b):
    """Repère courant (R, t) : colonnes de R = axes locaux dans la carte, t = origine locale."""
    t = np.asarray(b.to_world((0.0, 0.0, 0.0)), float)
    R = np.column_stack([np.asarray(b.to_world(e), float) - t for e in np.eye(3)])
    return R, t


def _resume(b, n0: int, **extra) -> dict:
    """Résumé d'un appel : emprise (x, z) et hauteur dans le repère local, pièces, Neon, transparentes."""
    R, t = _repere(b)
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    neon = transp = 0
    parts = b.parts[n0:]
    for p in parts:
        neon += p.material == "Neon"
        transp += 0 < p.transparency < 1
        if p.transparency >= 0.99:
            continue
        Rp = R.T @ np.asarray(p.rot, float).reshape(3, 3)
        cp = R.T @ (np.asarray(p.pos, float) - t)
        half = np.abs(Rp) @ (np.asarray(p.size, float) / 2)
        lo, hi = np.minimum(lo, cp - half), np.maximum(hi, cp + half)
    out = {"emprise": (round(float(hi[0] - lo[0]), 2), round(float(hi[2] - lo[2]), 2)),
           "hauteur": round(float(hi[1]), 2), "pieces": len(parts), "neon": int(neon),
           "transparentes": int(transp),
           "bornes": ([round(float(v), 2) for v in lo], [round(float(v), 2) for v in hi])}
    out.update(extra)
    return out


def _cadre(d, cote=None, roulis: float = 0.0) -> np.ndarray:
    """Rotation dont l'axe Z local suit `d` (long axe d'une palme), l'axe X local reste horizontal (largeur de la
    palme), puis un roulis (degrés) autour de Z."""
    z = np.asarray(d, float)
    z = z / np.linalg.norm(z)
    x = np.cross((0.0, 1.0, 0.0), z) if cote is None else np.asarray(cote, float)
    if np.linalg.norm(x) < 1e-6:
        x = np.array([1.0, 0.0, 0.0])
    x = x - (x @ z) * z
    x = x / np.linalg.norm(x)
    if roulis:
        y0 = np.cross(z, x)
        a = math.radians(roulis)
        x = x * math.cos(a) + y0 * math.sin(a)
    y = np.cross(z, x)
    return np.column_stack([x, y, z])


def _dir(azimut: float, elevation: float) -> np.ndarray:
    """Direction d'azimut (0 = +X, 90 = -Z, comme `anneau`) et d'élévation (degrés, > 0 vers le haut)."""
    a, e = math.radians(azimut), math.radians(elevation)
    return np.array([math.cos(a) * math.cos(e), math.sin(e), -math.sin(a) * math.cos(e)])


def _pilule(b, centre, largeur: float, hauteur: float, epaisseur: float, couleur, *, rebord: float = 0.05,
            raccourci: float = 0.0, **kw) -> list:
    """Gélule plate face à -Z (boîte aux bouts ronds) : 1 bloc + 2 cylindres d'axe Z (bouts en retrait de
    `rebord` sur les faces avant et arrière, aucune face confondue). 3 pièces."""
    cx, cy, cz = centre
    r = hauteur / 2
    lb = max(largeur - hauteur, 0.1)
    out = [b.boxc((cx, cy, cz), (lb - raccourci, hauteur, epaisseur), couleur, **kw)]
    for i, s in enumerate((-1, 1)):
        ep = max(epaisseur - 2 * rebord - 0.02 * i, 0.1)       # deux bouts jamais dans le même plan
        out.append(b.cyl((cx + s * lb / 2, cy, cz), r, ep, couleur, axis="z", **kw))
    return out


# ---------------------------------------------------------------------------------------------------------------
# M01 · Palmier à cocos
# ---------------------------------------------------------------------------------------------------------------

def _palmier(b, variant: int = 0, hauteur: float = 18.0, courbure: float = 1.0, palmes: int | None = None,
             ouverture: float = 360.0, pointe: float | None = None) -> None:
    """Construit un palmier dans le repère courant (pied en (0, 0, 0)), sans groupe ni résumé.

    variant : pair = courbure vers +X local, impair = vers -X ; 0-1 : 8 palmes, 2-3 : 6 palmes.
    ouverture : secteur (degrés) où se répartissent les palmes, centré sur le sens de la courbure (360 = tout
    autour ; 240 contre une façade). pointe : azimut (degrés) imposé au sens de la courbure (sinon ±X)."""
    v = int(variant) % 4
    sens = 1.0 if v % 2 == 0 else -1.0
    n_p = int(palmes) if palmes else (8 if v < 2 else 6)
    H = max(float(hauteur), 6.0)
    k = H / 18.0
    kc = k ** 0.7                    # couronne : s'élargit moins vite que la hauteur
    kr = k ** 0.5                    # rayon du stipe
    rng = b.rng
    az_c = (0.0 if sens > 0 else 180.0) if pointe is None else float(pointe)
    ca, sa = math.cos(math.radians(az_c)), -math.sin(math.radians(az_c))   # sens horizontal de la courbure

    # --- stipe : 7 cylindres annelés le long d'un arc (2° → 20° × courbure), alternés clair / foncé
    n_s = 7
    angles = [courbure * (2.0 + 3.0 * i) for i in range(n_s)]
    haut_couronne = 2.3 * kc
    y_t = H - haut_couronne
    L = (y_t + 0.2) / sum(math.cos(math.radians(a)) for a in angles)
    P = np.array([0.0, -0.2, 0.0])
    tronc, tronc_f = shade(c("tronc"), 1.14), shade(c("tronc"), 0.78)
    with b.group("Stipe"):
        for i, a in enumerate(angles):
            d = np.array([ca * math.sin(math.radians(a)), math.cos(math.radians(a)), sa * math.sin(math.radians(a))])
            Q = P + L * d
            r = kr * (1.08 - 0.34 * i / (n_s - 1)) + (0.05 if i % 2 == 0 else -0.03)
            col = varier(tronc if i % 2 == 0 else tronc_f, rng, 0.03)
            b.cyl_entre(P - 0.14 * d, Q + 0.14 * d, r, col, name="Stipe")
            P = Q
    T = P

    # --- couronne : cœur, palmes (2 ellipsoïdes : lame qui monte puis lame qui retombe), noix de coco
    with b.group("Couronne"):
        b.ball(T + np.array([0.0, 0.25 * kc, 0.0]), 0.95 * kc, c("palme_fonce"), name="Coeur", **SANS)
        phi0 = float(rng.uniform(0, 360))
        plein = ouverture >= 359.0
        for j in range(n_p):
            if plein:
                phi = phi0 + j * 360.0 / n_p + float(rng.uniform(-7, 7))
            else:
                f = (j + 0.5) / n_p - 0.5
                phi = az_c + f * ouverture + float(rng.uniform(-5, 5))
            haute = j % 2 == 0
            e1 = float(rng.uniform(17, 25) if haute else rng.uniform(1, 8))
            e2 = float(rng.uniform(-30, -22) if haute else rng.uniform(-50, -40))
            if not plein:                       # contre une façade : les palmes du dos se relèvent
                dos = abs(((phi - az_c + 180) % 360) - 180) / 180.0
                e1 += 10 * max(0.0, dos - 0.4)
            L1 = (7.4 if haute else 6.9) * kc * float(rng.uniform(0.93, 1.07))
            L2 = (7.0 if haute else 6.4) * kc * float(rng.uniform(0.93, 1.07))
            w1, w2 = 2.15 * kc, 1.85 * kc
            ep = 0.34 * kc ** 0.5
            d1, d2 = _dir(phi, e1), _dir(phi, e2)
            racine = T - d1 * 0.5 * kc
            col1 = varier(c("palme") if haute else shade(c("palme"), 0.88), rng, 0.03)
            col2 = varier(shade(c("palme"), 1.12) if haute else shade(c("palme"), 1.0), rng, 0.03)
            roul = float(rng.uniform(-14, 14))
            b.ellipsoid(racine + d1 * L1 / 2, (w1, ep, L1), col1, rot=_cadre(d1, roulis=roul), name="Palme", **SANS)
            J = racine + d1 * 0.8 * L1
            b.ellipsoid(J + d2 * (L2 / 2 - 0.75 * kc), (w2, ep * 0.9, L2), col2, rot=_cadre(d2, roulis=-roul * 1.4),
                        name="Palme", **SANS)
        psi0 = float(rng.uniform(0, 90))
        for m in range(4):
            psi = math.radians(psi0 + 90 * m + float(rng.uniform(-14, 14)))
            rr = 0.92 * kc
            p = T + np.array([rr * math.cos(psi), -0.95 * kc + 0.18 * (m % 2) * kc, -rr * math.sin(psi)])
            b.ball(p, 0.72 * kc * float(rng.uniform(0.94, 1.06)), varier(c("coco"), rng, 0.04), name="Coco", **SANS)


def palmier(b, variant: int = 0, hauteur: float = 18, courbure: float = 1.0, **params) -> dict:
    """M01 · palmier à cocos (≤ 28 pièces) : stipe annelé courbe (7 segments alternés tronc / tronc foncé),
    cœur, 8 palmes (variantes 0, 1) ou 6 (variantes 2, 3) en 2 ellipsoïdes (lame qui monte, lame qui retombe),
    4 noix de coco orangées. Pair : courbure vers +X local ; impair : vers -X. `hauteur` = sommet des palmes
    (18 → 28 dans les groupes). Paramètres facultatifs : `palmes`, `ouverture` (secteur des palmes, degrés),
    `pointe` (azimut du sens de la courbure). Stipe solide ; palmes et noix sans collision."""
    n0 = len(b.parts)
    with b.group("Palmier"):
        _palmier(b, variant, hauteur, courbure, **params)
    return _resume(b, n0)


# ---------------------------------------------------------------------------------------------------------------
# M02 · haies en boules (outil)
# ---------------------------------------------------------------------------------------------------------------

def _boule_haie(b, centre, taille, ton: str = "milieu", **kw):
    """Une boule de haie (ellipsoïde sans collision) : `ton` bas (foncé), milieu, haut (clair)."""
    base = {"bas": shade(c("haie"), 0.8), "milieu": c("haie"), "haut": c("haie_claire")}[ton]
    return b.ellipsoid(centre, taille, varier(base, b.rng, 0.03), name="Haie", **{**SANS, **kw})


# ---------------------------------------------------------------------------------------------------------------
# Groupe de palmiers en jardinière ronde
# ---------------------------------------------------------------------------------------------------------------

def groupe_palmiers(b, variant: int = 0, n: int = 2, diametre: float = 8, hauteur: float | None = None,
                    **params) -> dict:
    """Jardinière ronde de Ø `diametre` à bordure rayée rouge et blanc (anneau à section carrée de 10-14
    segments, studs), terre `haie` à studs, boules de haie, et `n` palmiers de hauteurs différentes (18 → 28 ;
    `hauteur` = le plus grand), courbures opposées vers l'extérieur. Pièces ≤ 16 + 28 n : le grand palmier a
    8 palmes (28), les autres 6 (24) ; la différence paie des boules de haie en plus."""
    n0 = len(b.parts)
    n = max(1, int(n))
    D = max(float(diametre), 5.0)
    v = int(variant) % 4
    rng = b.rng
    H = float(hauteur) if hauteur else {1: 22.0, 2: 26.0}.get(n, 28.0)
    if n == 1:
        hs = [H]
    else:
        bas = max(min(18.0, H * 0.8), H * 0.64)
        hs = [H + (bas - H) * i / (n - 1) for i in range(n)]
    budget = 16 + 28 * n
    pieces_palmiers = 28 + 24 * (n - 1)
    reste = budget - pieces_palmiers                    # bordure + terre + haies
    n_seg = 10 if D < 7 else (12 if reste < 24 else 14)
    n_haies = max(2, reste - n_seg - 1)
    e = 1.3 if D < 7 else 1.5                           # section de la bordure
    Rc = D / 2 - e / 2                                  # ligne médiane de la bordure
    Ri = Rc - e / 2                                     # bord intérieur
    y_terre = e - 0.35
    with b.group("Jardiniere"):
        b.anneau((0, e / 2, 0), Rc, e, [c("rouge"), c("blanc_labo")], n_seg, section="carre", studs="top",
                 depart=float(rng.uniform(0, 360.0 / n_seg)), name="Bordure")
        b.disque((0, (0.1 + y_terre) / 2, 0), Rc, y_terre - 0.1, shade(c("haie"), 0.78), studs="top", name="Terre")
        # haies : une couronne de boules basses qui débordent un peu sur la bordure, puis des boules claires au
        # milieu, plus hautes
        n_bas = max(2, min(n_haies, round(n_haies * 0.62)))
        n_haut = n_haies - n_bas
        a0 = float(rng.uniform(0, 360))
        for i in range(n_bas):
            a = math.radians(a0 + i * 360.0 / n_bas + float(rng.uniform(-10, 10)))
            rb = Ri * float(rng.uniform(0.5, 0.62))
            sx = Ri * float(rng.uniform(1.05, 1.25)) * (1.0 if n_bas > 3 else 1.25)
            sy = float(rng.uniform(2.1, 2.6)) * (D / 8) ** 0.4
            _boule_haie(b, (rb * math.cos(a), y_terre + sy * 0.32, -rb * math.sin(a)), (sx, sy, sx * 0.95),
                        "bas" if i % 2 else "milieu")
        for i in range(n_haut):
            a = math.radians(a0 + 360.0 / n_bas / 2 + i * 360.0 / max(n_haut, 1) + float(rng.uniform(-15, 15)))
            rb = Ri * float(rng.uniform(0.2, 0.38))
            sx = Ri * float(rng.uniform(0.85, 1.0))
            sy = float(rng.uniform(1.8, 2.3)) * (D / 8) ** 0.4
            _boule_haie(b, (rb * math.cos(a), y_terre + sy * 0.62, -rb * math.sin(a)), (sx, sy, sx), "haut")
    # palmiers : le plus grand au centre (n = 1) ou sur un petit cercle, chacun penché vers l'extérieur
    ar = Ri * (0.0 if n == 1 else (0.38 if n == 2 else 0.45))
    b0 = float(rng.uniform(0, 360)) + 90 * v
    for i, h in enumerate(hs):
        a = b0 + i * 360.0 / n
        pos = (ar * math.cos(math.radians(a)), y_terre - 0.05, -ar * math.sin(math.radians(a)))
        var = (0 if i == 0 else 2) + (v % 2 if n == 1 else 0)
        courb = (0.85 if i == 0 else 1.25) * (1.0 if n > 1 else 1.1)
        with b.at(pos, group="Palmier"):
            _palmier(b, var, h, courb, pointe=a if n > 1 else None)
    return _resume(b, n0, palmiers=[round(h, 1) for h in hs])


# ---------------------------------------------------------------------------------------------------------------
# M03 · Jardinière rectangulaire à haie (et palmier)
# ---------------------------------------------------------------------------------------------------------------

def jardiniere(b, variant: int = 0, largeur: float = 12, profondeur: float = 6, palmier: bool = True,
               **params) -> dict:
    """M03 · jardinière rectangulaire `largeur` (X) × `profondeur` (Z) contre une façade (dos à +Z) : bordure
    rayée M04 (segments d'environ 2, rouge / blanc, poteaux d'angle ronds blancs un peu plus hauts, studs),
    terre à studs, 12-14 boules de haie sur deux rangs (+ deux claires sur le dessus), un palmier au centre
    penché vers l'avant (rue) dont les palmes évitent le dos (la façade est à 4 studs derrière le tronc).
    ≤ 70 pièces (palmier compris)."""
    n0 = len(b.parts)
    v = int(variant) % 4
    rng = b.rng
    W, Dp = max(float(largeur), 4.0), max(float(profondeur), 3.0)
    t, hb = 1.0, 1.8                                     # bordure : épaisseur, hauteur
    xs, zs = W / 2 - t / 2, Dp / 2 - t / 2               # ligne médiane de la bordure
    rouge, blanc = c("rouge"), c("blanc_labo")
    with b.group("Jardiniere"):
        # angles arrondis : cylindres blancs de rayon t centrés sur le coin intérieur de la bordure (quart de
        # cercle à l'extérieur), 0,06 plus hauts et 0,05 plus bas que les segments : aucune face confondue
        xa, za = W / 2 - t, Dp / 2 - t
        for sx in (-1, 1):
            for sz in (-1, 1):
                b.cyl((sx * xa, (hb + 0.06 - 0.05) / 2, sz * za), t, hb + 0.11, blanc, studs="top", name="Angle")

        def cote(lc, axe):
            nseg = max(1, int(round(lc / 2.0)))
            if nseg % 2 == 0:                         # nombre impair : rouge aux deux bouts
                nseg += 1 if lc / (nseg + 1) >= 1.2 else -1
            nseg = max(1, nseg)
            pas = lc / nseg
            for i in range(nseg):
                a, bb = -lc / 2 + i * pas, -lc / 2 + (i + 1) * pas
                col = rouge if i % 2 == 0 else blanc
                if axe == "x":
                    for sz in (-1, 1):
                        b.box((a, 0, sz * zs - t / 2), (bb, hb, sz * zs + t / 2), col, studs="top", name="Bordure")
                else:
                    for sx in (-1, 1):
                        b.box((sx * xs - t / 2, 0, a), (sx * xs + t / 2, hb, bb), col, studs="top", name="Bordure")

        cote(2 * xa, "x")          # entre les centres des angles : W - 2 (12 → 5 segments de 2)
        cote(2 * za, "z")          # Dp - 2 (6 → 3 segments de 1,33)
        y_terre = hb - 0.4
        b.box((-W / 2 + 0.6, 0.1, -Dp / 2 + 0.6), (W / 2 - 0.6, y_terre, Dp / 2 - 0.6), shade(c("haie"), 0.78),
              studs="top", name="Terre")
        # haies : rang arrière (plus haut, plus foncé) et rang avant, puis deux boules claires sur le dessus
        xi, zi = W / 2 - t, Dp / 2 - t                  # demi-intérieur
        n_rang = 6 if W >= 10 else max(2, int(W // 2))
        for rang, (z, sy, ton) in enumerate(((zi * 0.38, 2.9, "bas"), (-zi * 0.4, 2.5, "milieu"))):
            for i in range(n_rang):
                x = -xi + (i + 0.5) * (2 * xi / n_rang) + float(rng.uniform(-0.25, 0.25))
                sx = 2 * xi / n_rang * float(rng.uniform(1.25, 1.45))
                sz = zi * float(rng.uniform(1.15, 1.35))
                syy = sy * float(rng.uniform(0.92, 1.08))
                yc = y_terre + syy * (0.36 if rang == 0 else 0.3)
                _boule_haie(b, (x, yc, z), (sx, syy, sz), ton if i % 3 else "milieu")
        for s in (-1, 1):
            x = s * xi * float(rng.uniform(0.42, 0.58))
            _boule_haie(b, (x, y_terre + 2.0, float(rng.uniform(-0.3, 0.3))), (2.6, 1.9, 2.4), "haut")
    if palmier:
        # penché vers l'avant (-Z), légèrement de côté selon la variante ; palmes sur 240° (rien dans le dos)
        pointe = 90.0 + (-1, 1, -1, 1)[v] * float(rng.uniform(8, 22))
        with b.at((0, y_terre - 0.05, 0.3), group="Palmier"):
            _palmier(b, v % 2, 18.0 + (0.0, 1.0, -0.5, 1.5)[v], 1.0, ouverture=240.0, pointe=pointe)
    return _resume(b, n0)


# ---------------------------------------------------------------------------------------------------------------
# M07 / M08 · Lampadaires
# ---------------------------------------------------------------------------------------------------------------

def lampadaire(b, variant: int = 0, hauteur: float = 9, **params) -> dict:
    """Lampadaire (≤ 10 pièces, 1 Neon). Pair (v0, v2) : **à écran** M07 : boule-socle indigo, mât blanc en
    deux diamètres et bague d'or, écran Neon `cyan` incliné vers l'avant (-Z) dans un cadre, volet vert,
    bouton citron au sommet. Impair (v1, v3) : **soucoupe** M08 : pylône conique indigo à bague d'or, mât blanc,
    soucoupe (ventre bleu roi, bord, dôme) et lumière Neon `cyan` dessous. v2 / v3 : autres couleurs.
    `hauteur` = sommet. Socle solide, mât et tête sans collision."""
    n0 = len(b.parts)
    v = int(variant) % 4
    H = max(float(hauteur), 6.0)
    indigo, blanc = c("indigo"), c("blanc_labo")
    with b.group("Lampadaire"):
        if v % 2 == 0:
            cadre = (blanc, c("turquoise"))[v // 2]
            volet = (c("vert_lime"), c("orange"))[v // 2]
            b.disque((0, 0.15, 0), 1.15, 0.3, indigo, studs="top", name="Socle")
            b.ball((0, 1.05, 0), 0.85, indigo, name="Socle")
            y1 = 0.48 * H
            y_top = H - 0.75
            b.cyl((0, (1.6 + y1) / 2, 0), 0.3, y1 - 1.6, blanc, name="Mat", **FIN)
            b.cyl((0, (y1 - 0.1 + y_top) / 2, 0), 0.22, y_top - y1 + 0.1, blanc, name="Mat", **FIN)
            b.cyl((0, y1 + 0.02, 0), 0.36, 0.28, c("jaune_or"), name="Bague", **FIN)
            # écran : cadre incliné de 12° vers le bas, dalle Neon en saillie de 0,06 à l'avant
            ye = H - 1.95
            R = rot_x(-12)
            ze = -0.3
            b.part("block", (2.9, 2.1, 0.32), (0, ye, ze), R, cadre, name="Cadre", **SANS)
            avant = R @ np.array([0.0, 0.0, -1.0])
            b.part("block", (2.45, 1.65, 0.15), np.array([0, ye, ze]) + avant * (0.16 + 0.06 - 0.075), R,
                   c("cyan"), material="Neon", name="Ecran", **FIN)
            b.part("block", (0.75, 1.7, 0.18), (1.75, ye + 0.05, ze + 0.25), R @ rot_y(30), volet, name="Volet",
                   **FIN)
            b.ball((0, H - 0.4, 0), 0.4, c("jaune_citron"), name="Bouton", **FIN)
        else:
            ventre, bord, dome = ((c("bleu_roi"), c("turquoise"), blanc),
                                  (c("turquoise"), c("orange"), c("jaune_citron")))[v // 2]
            hp = 3.4
            b.cone_etage((0, 0, 0), 1.3, 0.75, hp, indigo, etages=3, studs="top", name="Pylone")
            b.cyl((0, hp + 0.12, 0), 0.82, 0.3, c("jaune_or"), name="Bague", **FIN)
            ys = H - 1.3
            b.cyl((0, (hp + ys) / 2, 0), 0.3, ys - hp, blanc, name="Mat", **FIN)
            b.ellipsoid((0, ys, 0), (4.8, 1.3, 4.8), ventre, name="Soucoupe", **SANS)
            b.disque((0, ys, 0), 3.0, 0.28, bord, name="Bord", **SANS)
            b.ellipsoid((0, ys + 0.45, 0), (2.6, 1.6, 2.6), dome, name="Dome", **SANS)
            b.ellipsoid((0, ys - 0.6, 0), (2.4, 0.42, 2.4), c("cyan"), material="Neon", name="Lumiere", **FIN)
    return _resume(b, n0)


# ---------------------------------------------------------------------------------------------------------------
# M10 · Banc arrondi
# ---------------------------------------------------------------------------------------------------------------

BANC_COULEURS = ("orange", "turquoise", "rose_bonbon", "jaune_citron")


def banc(b, variant: int = 0, **params) -> dict:
    """M10 · banc arrondi (10 pièces) : assise en gélule (bloc + 2 bouts ronds, studs) sur 2 pieds blancs,
    dossier en gélule à l'arrière (+Z) sur 2 montants ; on s'assoit face à -Z. Assise et dossier `orange`,
    `turquoise`, `rose_bonbon` ou `jaune_citron` selon la variante. 7 × 2 au sol, 3,9 de haut."""
    n0 = len(b.parts)
    col = c(BANC_COULEURS[int(variant) % 4])
    blanc = c("blanc_labo")
    with b.group("Banc"):
        for s in (-1, 1):
            b.cyl((s * 2.0, 0.85, 0), 0.55, 1.7, blanc, name="Pied")
        b.box((-2.5, 1.6, -1.0), (2.5, 2.2, 1.0), col, studs="top", name="Assise")
        for s in (-1, 1):
            b.cyl((s * 2.5, 1.9, 0), 1.0, 0.5, col, studs="top", name="Assise")      # 1,65 → 2,15
        b.box((-2.5, 2.45, 0.55), (2.5, 3.85, 0.95), col, studs="top", name="Dossier")
        for s in (-1, 1):
            b.cyl((s * 2.5, 3.15, 0.75), 0.7, 0.5, col, axis="z", name="Dossier")
            b.boxc((s * 1.6, 2.33, 0.75), (0.32, 0.56, 0.3), blanc, name="Montant", **FIN)
    return _resume(b, n0)


# ---------------------------------------------------------------------------------------------------------------
# Poubelle-capsule
# ---------------------------------------------------------------------------------------------------------------

POUBELLE_COULEURS = ("turquoise", "orange", "rose_bonbon", "vert_lime")


def poubelle(b, variant: int = 0, **params) -> dict:
    """Poubelle-capsule ronde (6 pièces) : pied indigo, corps blanc, bague de couleur, rebord et couvercle bombé
    de couleur, fente `bleu_nuit` à l'avant (-Z). Couleur selon la variante (turquoise, orange, rose, lime).
    Ø 2,2 × 3,4."""
    n0 = len(b.parts)
    col = c(POUBELLE_COULEURS[int(variant) % 4])
    with b.group("Poubelle"):
        b.cyl((0, 0.15, 0), 1.12, 0.3, c("indigo"), studs="top", name="Pied")
        b.cyl((0, 1.4, 0), 1.0, 2.4, c("blanc_labo"), name="Corps")                 # 0,2 → 2,6
        b.cyl((0, 1.775, 0), 1.06, 0.45, col, name="Bague", **SANS)
        b.cyl((0, 2.66, 0), 1.1, 0.22, col, studs="top", name="Rebord")             # 2,55 → 2,77
        b.ellipsoid((0, 2.77, 0), (1.9, 1.3, 1.9), shade(col, 1.12), name="Couvercle", **SANS)
        b.boxc((0, 2.3, -0.93), (1.0, 0.28, 0.3), c("bleu_nuit"), name="Fente", **FIN)
    return _resume(b, n0)


# ---------------------------------------------------------------------------------------------------------------
# K05 · Feu tricolore sur mât
# ---------------------------------------------------------------------------------------------------------------

FEU_COULEURS = (   # boîtier, plateau, visières (STYLE K05 V1-V4)
    (("vert_pomme", 0.62), "jaune_or", "bleu_nuit"),
    ("jaune_or", "bleu_roi", "bleu_nuit"),
    ("bleu_roi", "blanc_labo", "indigo"),
    ("blanc_labo", "rouge", "bleu_nuit"),
)


def _col(spec):
    return shade(c(spec[0]), spec[1]) if isinstance(spec, tuple) else c(spec)


def feu_tricolore(b, variant: int = 0, hauteur: float = 10, **params) -> dict:
    """K05 · feu tricolore sur mât (14 pièces, 3 Neon) : socle, mât blanc, boîtier en gélule debout, 3 feux Neon
    `rouge` / `jaune_citron` / `vert_lime` à l'avant (-Z) sous 3 visières, plateau à 2 points sur le dessus.
    Couleurs boîtier / plateau / visières : K05 V1-V4 selon la variante. `hauteur` = sommet du plateau."""
    n0 = len(b.parts)
    boitier, plateau, visiere = (_col(x) for x in FEU_COULEURS[int(variant) % 4])
    H = max(float(hauteur), 7.0)
    yb = H - 3.2                       # centre du boîtier : gélule de 2,4 × 6 (H 10 : de 3,9 à 9,7)
    with b.group("Feu"):
        b.disque((0, 0.15, 0), 1.2, 0.3, plateau, studs="top", name="Socle")
        b.cyl((0, (0.2 + yb - 2.0) / 2, 0), 0.38, yb - 2.2, c("blanc_labo"), name="Mat")
        b.boxc((0, yb, 0), (2.4, 3.4, 1.6), boitier, name="Boitier")
        for s in (-1, 1):
            b.cyl((0, yb + s * 1.7, 0), 1.2, 1.5, boitier, axis="z", name="Boitier")
        for i, nom in enumerate(("rouge", "jaune_citron", "vert_lime")):
            y = yb + 1.7 - 1.7 * i
            b.cyl((0, y, -0.8), 0.72, 0.2, c(nom), axis="z", material="Neon", name="Lumiere", **FIN)
            b.part("block", (1.75, 0.14, 0.85), (0, y + 0.86, -1.18), rot_x(-14), visiere, name="Visiere", **FIN)
        b.disque((0, yb + 2.95, 0), 1.55, 0.3, plateau, studs="top", name="Plateau", **SANS)
        for s in (-1, 1):
            b.ball((s * 0.65, yb + 3.1, -0.35), 0.3, c("rouge") if variant % 4 != 3 else c("jaune_citron"),
                   name="Point", **FIN)
    return _resume(b, n0)


# ---------------------------------------------------------------------------------------------------------------
# M06 · Potelet
# ---------------------------------------------------------------------------------------------------------------

def potelet(b, variant: int = 0, **params) -> dict:
    """M06 · potelet (5 pièces, H 3,6) : cône indigo en 2 étages, bague d'or, fût blanc, boule `cyan`
    (SmoothPlastic). Cône et fût solides."""
    n0 = len(b.parts)
    with b.group("Potelet"):
        b.cone_etage((0, 0, 0), 0.78, 0.44, 1.4, c("indigo"), etages=2, studs="top", name="Cone")
        b.cyl((0, 1.51, 0), 0.47, 0.22, c("jaune_or"), name="Bague", **FIN)
        b.cyl((0, 2.15, 0), 0.32, 1.9, c("blanc_labo"), name="Fut")                 # 1,2 → 3,1
        b.ball((0, 3.15, 0), 0.45, c("cyan"), name="Boule", **SANS)
    return _resume(b, n0)


# ---------------------------------------------------------------------------------------------------------------
# M16 · Coupole de verre à miniature
# ---------------------------------------------------------------------------------------------------------------

COUPOLE_BAGUES = ("turquoise", "rose_bonbon", "orange", "violet")


def _mini_palmier(b, x, y, z, h, rng, n_palmes=4):
    """Mini-palmier opaque (1 + n_palmes pièces)."""
    top = np.array([x + 0.35 * h / 4, y + h, z])
    b.cyl_entre((x, y - 0.1, z), top, 0.22 * h / 4, c("tronc"), name="MiniStipe", **SANS)
    a0 = float(rng.uniform(0, 90))
    for j in range(n_palmes):
        d = _dir(a0 + j * 360.0 / n_palmes, -22)
        b.ellipsoid(top + d * 0.75 * h / 4, (0.9 * h / 4, 0.14, 2.0 * h / 4), varier(c("palme"), rng, 0.03),
                    rot=_cadre(d), name="MiniPalme", **SANS)


def coupole_miniature(b, variant: int = 0, **params) -> dict:
    """M16 · coupole de verre à miniature (≤ 14 pièces, 1 verre) : socle rond blanc Ø 14 × 3 (studs) et bague de
    couleur, coupole `Glass` 0,45 (13 × 6 visibles ; moitié basse cachée dans le socle et le sol), deux cylindres
    invisibles de collision qui épousent la coupole, et dedans une scène **opaque** selon la variante :
    0 maisonnette-œuf et mini-palmier ; 1 cône rayé à pointe d'or ; 2 champignon-tour ; 3 fusée. 14 × 14 × 9."""
    n0 = len(b.parts)
    v = int(variant) % 4
    rng = b.rng
    blanc = c("blanc_labo")
    with b.group("Coupole"):
        b.cyl((0, 1.5, 0), 7.0, 3.0, blanc, studs="top", name="Socle")
        b.cyl((0, 2.3, 0), 7.2, 0.6, c(COUPOLE_BAGUES[v]), name="Bague", **SANS)       # 2,0 → 2,6
        b.ellipsoid((0, 3.0, 0), (13.0, 12.0, 13.0), c("verre"), material="Glass", transparency=VERRE_T,
                    name="Coupole", **SANS)
        # collision : deux gradins invisibles sous la surface de la coupole (aucun coin invisible au-dessus)
        for r, y0, y1 in ((6.2, 3.0, 4.75), (4.6, 4.75, 7.2)):
            b.cyl((0, (y0 + y1) / 2, 0), r, y1 - y0, "#FFFFFF", transparency=1.0, shadow=False,
                  name="CollisionCoupole")
    with b.group("Miniature"):
        y = 3.0
        if v == 0:      # maisonnette-œuf, mini-palmier, deux boules
            b.ellipsoid((-1.2, y + 1.55, 0.6), (2.8, 3.6, 2.8), c("vert_pomme"), name="MiniOeuf", **SANS)
            b.ellipsoid((-1.2, y + 0.95, -0.72), (1.1, 1.6, 0.4), c("orange"), name="MiniPorte", **SANS)
            _mini_palmier(b, 2.0, y, 0.9, 4.2, rng, 4)
            b.ball((1.3, y + 0.55, -2.4), 0.6, c("rose_bonbon"), name="MiniBoule", **SANS)
            b.ball((-3.4, y + 0.45, -1.4), 0.5, c("jaune_citron"), name="MiniBoule", **SANS)
        elif v == 1:    # cône rayé rouge et blanc à pointe d'or, mini-palmier
            b.cone_etage((-0.9, y, 0.3), 1.5, 0.35, 4.6, [c("rouge"), c("blanc_labo")], etages=3,
                         pointe=(c("or"), 0.45), name="MiniCone", **SANS)
            _mini_palmier(b, 2.3, y, -0.6, 3.6, rng, 3)
            b.ball((-2.6, y + 0.45, -2.0), 0.5, c("turquoise"), name="MiniBoule", **SANS)
        elif v == 2:    # champignon-tour : pied crème, chapeau rose à bord, boule
            b.cyl((-0.6, y + 1.4, 0.4), 0.55, 2.8, c("creme"), name="MiniPied", **SANS)
            b.disque((-0.6, y + 2.9, 0.4), 2.0, 0.3, c("violet"), name="MiniBord", **SANS)
            b.ellipsoid((-0.6, y + 3.05, 0.4), (3.6, 2.2, 3.6), c("rose_bonbon"), name="MiniChapeau", **SANS)
            b.ellipsoid((-0.6, y + 2.75, 0.4), (3.6, 1.7, 3.6), c("creme"), name="MiniCloche", **SANS)
            _mini_palmier(b, 2.4, y, -0.8, 3.4, rng, 3)
        else:           # fusée blanche à bandes orange, ailerons
            b.ellipsoid((-0.5, y + 2.1, 0.2), (1.9, 4.6, 1.9), blanc, name="MiniFusee", **SANS)
            b.cyl((-0.5, y + 2.0, 0.2), 1.0, 0.5, c("orange"), name="MiniBande", **SANS)
            b.ball((-0.5, y + 4.35, 0.2), 0.42, c("rouge"), name="MiniNez", **SANS)
            for s in (-1, 1):      # ailerons : coins dont la face pleine touche le corps, pente vers l'extérieur
                b.part("wedge", (0.2, 1.4, 1.0), (-0.5 + s * 1.15, y + 0.7, 0.2), rot_y(-90 * s), c("orange"),
                       name="MiniAileron", **SANS)
            _mini_palmier(b, 2.3, y, -0.5, 3.2, rng, 3)
    return _resume(b, n0)


# ---------------------------------------------------------------------------------------------------------------
# M11 + M12 · Panneau-pictogramme
# ---------------------------------------------------------------------------------------------------------------

PANNEAU_COULEURS = (   # gélule, Neon du contour
    ("bleu_roi", "cyan"), ("magenta", "neon_blanc"), ("turquoise", "cyan"), ("violet", "neon_orange"),
)
PICTOS = ("etoile", "coeur", "piece", "eclair", "nuage", "croix", "boutons", "cornet", "planete", "chevron")


def _picto(b, nom: str, cx: float, cy: float, zf: float, fond: str) -> None:
    """Pictogramme en relief devant la face avant (plan z = zf, avant vers -Z), centré en (cx, cy). ≤ 6 pièces."""
    kw = dict(FIN, name="Picto")
    clair = fond in (c("turquoise"),)
    compte = [0]

    def enfonce():          # chaque pièce s'enfonce d'une valeur différente : faces arrière toutes distinctes
        compte[0] += 1
        return 0.03 + 0.008 * compte[0]

    def bloc(x, y, sx, sy, ang=0.0, col=None, ep=0.16):
        e = enfonce()
        b.part("block", (sx, sy, ep + e), (cx + x, cy + y, zf - (ep - e) / 2), rot_z(ang), col, **kw)

    def rond(x, y, r, col, ep=0.16, dz=0.0):
        e = enfonce()
        b.cyl((cx + x, cy + y, zf - (ep + dz - e) / 2), r, ep + dz + e, col, axis="z", **kw)

    if nom == "etoile":
        col = c("jaune_citron") if clair else c("or")
        for i in range(5):
            a = math.radians(90 + 72 * i)
            bloc(0.62 * math.cos(a), 0.62 * math.sin(a), 0.62, 1.15, ang=72 * i, col=col, ep=0.15 + 0.01 * i)
        rond(0, 0, 0.5, col, ep=0.22)
    elif nom == "coeur":
        col = c("rouge") if fond not in (c("magenta"), c("violet")) else c("rose_bonbon")
        for s in (-1, 1):
            rond(s * 0.48, 0.22, 0.6, col, ep=0.165 + 0.01 * s)
        bloc(0, -0.28, 1.2, 1.2, ang=45, col=col, ep=0.14)
    elif nom == "piece":
        rond(0, 0, 1.1, c("or"))
        rond(0, 0, 0.72, c("or_fonce"), ep=0.16, dz=0.06)
    elif nom == "eclair":
        col = c("jaune_citron")
        bloc(0.28, 0.62, 0.55, 1.2, ang=-28, col=col)
        bloc(0.0, 0.0, 1.35, 0.42, ang=12, col=col, ep=0.15)
        bloc(-0.3, -0.62, 0.55, 1.2, ang=-28, col=col)
    elif nom == "nuage":
        col = c("blanc_labo")
        rond(-0.75, -0.12, 0.55, col, ep=0.15)
        rond(0.05, 0.18, 0.78, col, ep=0.16, dz=0.01)
        rond(0.85, -0.12, 0.55, col, ep=0.17, dz=0.02)
        bloc(0.05, -0.38, 1.6, 0.56, col=col, ep=0.14)
    elif nom == "croix":
        col = c("blanc_labo")
        bloc(0, 0, 2.0, 0.66, col=col, ep=0.16)
        bloc(0, 0, 0.66, 2.0, col=col, ep=0.18)
    elif nom == "boutons":
        col = c("jaune_citron") if not clair else c("blanc_labo")
        for x, y in ((0, 0.6), (0.6, 0), (0, -0.6), (-0.6, 0)):
            rond(x, y, 0.36, col)
    elif nom == "cornet":
        b.cone_etage((cx, cy - 0.2, zf + 0.12), 0.62, 0.12, 1.24, [c("orange"), shade(c("orange"), 0.85)],
                     etages=3, axe=(0, -1, 0), **kw)
        b.ball((cx - 0.3, cy + 0.32, zf + 0.12), 0.5, c("rose_bonbon"), **kw)
        b.ball((cx + 0.3, cy + 0.62, zf + 0.12), 0.46, c("jaune_citron"), **kw)
    elif nom == "planete":
        b.ball((cx, cy, zf + 0.1), 0.78, c("orange"), **kw)
        b.ellipsoid((cx, cy, zf + 0.1), (3.0, 0.42, 1.9), c("jaune_citron"), rot=rot_z(-18), **kw)
    else:   # chevron
        col = c("jaune_citron")
        bloc(-0.05, 0.36, 1.2, 0.5, ang=-38, col=col, ep=0.16)
        bloc(-0.05, -0.36, 1.2, 0.5, ang=38, col=col, ep=0.18)


def panneau(b, variant: int = 0, picto: str = "etoile", **params) -> dict:
    """M11 + M12 · panneau-pictogramme sans texte (≤ 14 pièces, 3 Neon) : 2 poteaux blancs, gélule 6 × 3
    (bloc + 2 bouts ronds), contour Neon (la même gélule 0,24 plus grande, plus mince, prise dans l'épaisseur :
    seul le bord brille, des deux côtés), pictogramme en relief à l'avant (-Z) : `etoile`, `coeur`, `piece`,
    `eclair`, `nuage`, `croix`, `boutons`, `cornet`, `planete`, `chevron`. Couleur de gélule et de Neon selon
    la variante. 6,2 × 0,6 au sol (poteaux 3,4 × 0,6), 7 de haut."""
    n0 = len(b.parts)
    v = int(variant) % 4
    fond, neon = (c(x) for x in PANNEAU_COULEURS[v])
    nom = picto if picto in PICTOS else "etoile"
    yc, W, Hp, ep = 5.4, 6.0, 3.0, 0.6
    with b.group("Panneau"):
        for s in (-1, 1):
            b.cyl((s * 1.7, (yc - 0.1) / 2, 0), 0.28, yc + 0.1, c("blanc_labo"), name="Poteau", **FIN)
        _pilule(b, (0, yc, 0), W, Hp, ep, fond, name="Gelule")
        _pilule(b, (0, yc, 0), W + 0.24, Hp + 0.24, 0.3, neon, rebord=0.02, raccourci=0.1, material="Neon",
                name="Contour", **FIN)
        _picto(b, nom, 0.0, yc, -ep / 2, fond)
    return _resume(b, n0, picto=nom)


# ---------------------------------------------------------------------------------------------------------------
# M09 · Champignon lumineux à pois
# ---------------------------------------------------------------------------------------------------------------

def champignon_lumineux(b, variant: int = 0, **params) -> dict:
    """M09 · champignon lumineux (11 pièces, 5 Neon) : socle `bleu_nuit`, pied `indigo`, chapeau `magenta`
    (variante paire) ou `rose_bonbon` (impaire) : dôme, bord et dessous (« cloche » sombre qui cache la moitié
    basse du dôme), 5 pois Neon `neon_orange` et 1 pois `jaune_citron`. Sans collision. Ø 3,5 × 4,4."""
    n0 = len(b.parts)
    v = int(variant) % 2
    chap = c(("magenta", "rose_bonbon")[v])
    rng = b.rng
    with b.group("Champignon"):
        b.disque((0, 0.15, 0), 0.85, 0.3, c("bleu_nuit"), studs="top", name="Socle", **SANS)
        yr = 3.3                                  # milieu du bord
        b.cyl((0, (0.25 + yr) / 2, 0), 0.25, yr - 0.25, c("indigo"), name="Pied", **FIN)
        d, h, hc, R = 0.24, 0.95, 0.75, 1.65      # bord, demi-hauteurs du dôme et de la cloche, rayon
        b.disque((0, yr, 0), R + 0.12, d, shade(chap, 0.82), name="Bord", **SANS)
        b.ellipsoid((0, yr + d / 2, 0), (2 * R, 2 * h, 2 * R), chap, name="Chapeau", **SANS)
        b.ellipsoid((0, yr - d / 2, 0), (2 * R, 2 * hc, 2 * R), c("prune"), name="Dessous", **SANS)
        a0 = float(rng.uniform(0, 60))
        pois = [(30, a0), (30, a0 + 120), (30, a0 + 240), (58, a0 + 60), (58, a0 + 180), (78, a0 + 300)]
        for i, (lat, az) in enumerate(pois):
            u, w = math.radians(lat), math.radians(az)
            p = (R * math.cos(u) * math.cos(w), yr + d / 2 + h * math.sin(u), -R * math.cos(u) * math.sin(w))
            if i < 5:
                b.ball(p, 0.3, c("neon_orange"), material="Neon", name="Pois", **FIN)
            else:
                b.ball(p, 0.3, c("jaune_citron"), name="Pois", **FIN)
    return _resume(b, n0)


# ---------------------------------------------------------------------------------------------------------------
# M05 · Rambarde blanche à boules
# ---------------------------------------------------------------------------------------------------------------

RAMBARDE_POMMEAUX = ("cyan", "jaune_citron", "rose_bonbon", "orange")


def rambarde(b, variant: int = 0, longueur: float = 16, solide: bool = True, **params) -> dict:
    """M05 · rambarde le long de X local, centrée (pièces ≤ 1 + 5 par travée de 8) : poteau blanc tous les ≤ 8
    (bouts compris), pommeau `cyan` (SmoothPlastic ; autre couleur selon la variante), bague `indigo`, 2 lisses
    `dalle_labo` d'un seul tenant. Poteaux et lisses solides (garde-corps ; `solide=False` pour un décor), boules
    sans collision. Une seule travée : sans bagues (budget)."""
    n0 = len(b.parts)
    L = max(float(longueur), 2.0)
    n = max(1, math.ceil(L / 8.0 - 1e-9))
    pas = L / n
    bagues = 3 * (n + 1) + 2 <= 1 + 5 * n
    pommeau = c(RAMBARDE_POMMEAUX[int(variant) % 4])
    col = {} if solide else {"collide": False}
    with b.group("Rambarde"):
        for i in range(n + 1):
            x = -L / 2 + i * pas
            b.cyl((x, 1.7, 0), 0.35, 3.4, c("blanc_labo"), name="Poteau", **col)
            b.ball((x, 3.7, 0), 0.55, pommeau, name="Pommeau", **SANS)
            if bagues:
                b.ball((x, 1.7, 0), 0.45, c("indigo"), name="Bague", **FIN)
        for y in (1.7, 3.3):
            b.cyl_entre((-L / 2, y, 0), (L / 2, y, 0), 0.22, c("dalle_labo"), name="Lisse", shadow=False, **col)
    return _resume(b, n0, travees=n)
