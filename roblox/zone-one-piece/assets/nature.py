"""Nature de la zone 2 (mer de l'Est) en style stud : moulins à vent, butte herbue, palmiers, mandariniers,
buissons fleuris, rochers de plage et îlots rocheux.

Les moulins sont les repères de la campagne (vus de loin, dans les deux sens de course) :
- variante 0 : moulin de bois sur tréteau, caisse en planches, toit en gradins, grandes ailes JAUNES en treillis,
  gouvernail rouge à l'arrière, échelle et porte à l'arrière ;
- variante 1 : tour ROSE en cylindres qui s'affinent, galerie de bois sous la calotte de bois brun, ailes blanches ;
- variante 2 : tour de pierre claire, galerie à mi-hauteur, DÔME bleu-gris en rangs de tuiles, ailes blanches ;
- variante 3 : moulin à calotte (corps octogonal de bois sombre) sur socle de pierre, plate-forme, calotte BLEUE,
  ailes crème.

Principes :
- les ailes sont dans un plan vertical devant le moulin (-Z local), placé devant tout ce qu'elles balaient
  (galerie, plate-forme, calotte) ; chaque aile = une vergue + un cadre en treillis (lattes, longeron extérieur)
  et une toile en retrait de 0,1 derrière les lattes ; ailes inclinées « de guingois » (pas un + parfait) ;
- pas de faces coplanaires de couleurs différentes : tout détail dépasse d'au moins 0,1, les toiles sont noyées
  dans leurs lattes, les gradins sont empilés ou découpés en bandes qui ne se recouvrent pas ;
- rien ne flotte : ailes sur le moyeu, palmes sur le haut du tronc, oranges à moitié dans le feuillage ;
- les troncs, tours et rochers collisionnent ; feuilles, ailes, fleurs, fruits et petits détails non (`collide=False`).
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, rot_x, rot_y, rot_z, shade
from palette import c, vary

ND = dict(collide=False)

# ---------------------------------------------------------------------------
# Outils géométriques
# ---------------------------------------------------------------------------


def _unit(v) -> np.ndarray:
    v = np.asarray(v, float)
    return v / float(np.linalg.norm(v))


def _poutre(b, p0, p1, w, d, col, ext0=0.0, ext1=0.0, **kw):
    """Bloc de section w × d dont l'axe Y local va de p0 à p1 (prolongé de ext0 / ext1) : pieds, échelles, jambes."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    u = _unit(p1 - p0)
    ref = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    x = _unit(np.cross(u, ref))
    z = np.cross(x, u)
    a, e = p0 - u * ext0, p1 + u * ext1
    return b.part("block", (w, float(np.linalg.norm(e - a)), d), (a + e) / 2, np.column_stack([x, u, z]), col, **kw)


def _cyl_entre(b, p0, p1, r, col, ext0=0.0, ext1=0.0, **kw):
    """Cylindre de rayon r dont l'axe va de p0 à p1 (troncs de palmier)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    u = _unit(p1 - p0)
    ref = np.array([0.0, 1.0, 0.0]) if abs(u[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    a = _unit(np.cross(ref, u))
    R = np.column_stack([u, a, np.cross(u, a)])
    s, e = p0 - u * ext0, p1 + u * ext1
    return b.part("cyl", (float(np.linalg.norm(e - s)), 2 * r, 2 * r), (s + e) / 2, R, col, **kw)


def _lame(b, p0, p1, w, t, col, coin=False, **kw):
    """Feuille de largeur w (horizontale) et d'épaisseur t, de p0 à p1. En coin (`coin=True`), le talon épais est
    en p0 et la pointe fine en p1, pente sur le dessus."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    zax = _unit(p0 - p1)
    x = np.cross(np.array([0.0, 1.0, 0.0]), zax)
    x = _unit(x) if np.linalg.norm(x) > 1e-6 else np.array([1.0, 0.0, 0.0])
    y = np.cross(zax, x)
    L = float(np.linalg.norm(p1 - p0))
    return b.part("wedge" if coin else "block", (w, t, L), (p0 + p1) / 2, np.column_stack([x, y, zax]), col, **kw)


def _cadre(b, n0):
    """Bornes (repère de l'asset) des pièces ajoutées depuis n0, et matrice monde → repère de l'asset."""
    o = b.to_world((0, 0, 0))
    M = np.vstack([b.to_world(e) - o for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))])
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    signes = [(sx, sy, sz) for sx in (1, -1) for sy in (1, -1) for sz in (1, -1)]
    for p in b.parts[n0:]:
        R = np.asarray(p.rot, float).reshape(3, 3)
        half = np.asarray(p.size, float) / 2
        for s in signes:
            loc = M @ (np.asarray(p.pos, float) + R @ (half * s) - o)
            lo, hi = np.minimum(lo, loc), np.maximum(hi, loc)
    return lo, hi, M


def _infos(b, n0) -> dict:
    """Emprise (x, z) et hauteur réelles des pièces ajoutées depuis n0, dans le repère de l'asset."""
    lo, hi, _ = _cadre(b, n0)
    if not np.isfinite(lo).all():
        return {"emprise": (0, 0), "hauteur": 0}
    return {"emprise": (round(float(hi[0] - lo[0]), 1), round(float(hi[2] - lo[2]), 1)), "hauteur": round(float(hi[1]), 1)}


def _recentrer(b, n0):
    """Décale (en x et z) les pièces ajoutées depuis n0 pour centrer leur emprise au sol sur l'origine."""
    lo, hi, M = _cadre(b, n0)
    if not np.isfinite(lo).all():
        return
    d = np.round(np.array([-(lo[0] + hi[0]) / 2, 0.0, -(lo[2] + hi[2]) / 2]) * 4) / 4
    if not d.any():
        return
    dw = M.T @ d
    for p in b.parts[n0:]:
        p.pos = tuple(round(float(v), 4) for v in np.asarray(p.pos, float) + dw)


# ---------------------------------------------------------------------------
# Moulins : pièces communes
# ---------------------------------------------------------------------------


def _plaque(b, alpha, y0, y1, w, r, col, sortie=0.15, rond=True, **kw):
    """Bloc plaqué sur une tour (ronde de rayon r, ou face plane à la distance r si `rond=False`), dans la direction
    `alpha` (0 = avant -Z, 90 = côté -X, 180 = arrière), qui dépasse de `sortie` : portes, fenêtres, pierres."""
    fond = (math.sqrt(max(r * r - (w / 2) ** 2, 0.01)) if rond else r) - 0.35
    with b.at((0, 0, 0), yaw=alpha):
        return b.box((-w / 2, y0, -(r + sortie)), (w / 2, y1, -fond), col, **kw)


def _fenetre(b, alpha, y, r, w=1.4, h=1.8, cadre=None, rond=True):
    """Petite fenêtre : cadre clair + vitre sombre qui dépasse de 0,1 devant le cadre."""
    cadre = c("blanc") if cadre is None else cadre
    _plaque(b, alpha, y - h / 2, y + h / 2, w, r, cadre, 0.15, rond, name="CadreFenetre", **ND)
    _plaque(b, alpha, y - h / 2 + 0.3, y + h / 2 - 0.3, w - 0.6, r, c("fenetre"), 0.25, rond, name="Fenetre", **ND)


def _porte(b, alpha, y0, r, w=2.2, h=3.6, bois=None, cadre=None, rond=True):
    """Porte de bois dans un encadrement (qui dépasse de 0,25, la porte de 0,35)."""
    bois = c("bois_fonce") if bois is None else bois
    cadre = c("pierre_fonce") if cadre is None else cadre
    _plaque(b, alpha, y0, y0 + h + 0.5, w + 0.8, r, cadre, 0.25, rond, name="Encadrement")
    _plaque(b, alpha, y0, y0 + h, w, r, bois, 0.35, rond, name="Porte")


def _galerie(b, y, r, n, plancher, garde, h=1.5):
    """Galerie circulaire : plancher rond studdé (y → y + 0,5), n poteaux et un garde-corps en polygone."""
    b.cyl((0, y + 0.25, 0), r, 0.5, plancher, axis="y", studs="top", name="Galerie")
    rp = r - 0.3
    pts = [(rp * math.cos(2 * math.pi * (k + 0.5) / n), rp * math.sin(2 * math.pi * (k + 0.5) / n)) for k in range(n)]
    for x, z in pts:
        b.box((x - 0.15, y + 0.5, z - 0.15), (x + 0.15, y + 0.5 + h, z + 0.15), garde, name="Poteau", **ND)
    for k in range(n):
        (xa, za), (xb, zb) = pts[k], pts[(k + 1) % n]
        L = math.hypot(xb - xa, zb - za) + 0.3
        yaw = math.degrees(math.atan2(-(zb - za), xb - xa))
        b.boxc(((xa + xb) / 2, y + 0.5 + h - 0.16, (za + zb) / 2), (L, 0.25, 0.25), garde, yaw=yaw, name="GardeCorps", **ND)


def _pots(b, y, r, alphas, fleurs, rng):
    """Pots de fleurs en terre cuite posés en y, au pied de la tour (à la distance r), dans les directions `alphas`."""
    for k, a in enumerate(alphas):
        with b.at((0, 0, 0), yaw=a):
            b.box((-0.5, y, -r - 0.5), (0.5, y + 0.8, -r + 0.5), vary("toit_orange", rng, 0.04), name="Pot", **ND)
            b.box((-0.4, y + 0.8, -r - 0.4), (0.4, y + 1.4, -r + 0.4), fleurs[k % len(fleurs)], name="Fleurs", **ND)


def _octogone(b, y0, y1, r, col, **kw):
    """Prisme octogonal d'apothème r (4 blocs tournés de 45° ; leur réunion est exactement l'octogone)."""
    s = r * math.tan(math.radians(22.5))
    for k in range(4):
        b.boxc((0, (y0 + y1) / 2, 0), (2 * r, y1 - y0, 2 * s), col, yaw=45 * k, **kw)


def _ailes(b, hub_y, z_dep, z_s, R, a0, vergue, cadre, toile, nez, n_lattes=4, larg=0.25, ouvert=True):
    """Arbre, moyeu et quatre ailes en treillis dans le plan vertical z = z_s (devant le moulin), moyeu en (0, hub_y).

    Repère d'une aile : u le long de la vergue (du moyeu vers la pointe), v sur le côté (la toile est du côté +v),
    w = z local. Épaisseurs : vergue ±0,3, longeron ±0,2, lattes ±0,15, toile ±0,05 (noyée dans les lattes)."""
    hub = np.array([0.0, hub_y, 0.0])
    W, r1 = larg * R, 0.24 * R
    us = [r1 + (R - 0.2 - r1) * i / (n_lattes - 1) for i in range(n_lattes)]
    with b.group("Ailes"):
        b.cyl((0, hub_y, (z_dep + z_s) / 2), 0.55, abs(z_dep - z_s), shade(vergue, 0.9), axis="z", name="Arbre", **ND)
        b.cyl((0, hub_y, z_s - 0.5), 1.1, 0.7, c("bois_fonce"), axis="z", name="Moyeu", **ND)
        b.cyl((0, hub_y, z_s - 1.05), 0.6, 0.5, nez, axis="z", name="Nez", **ND)
        for k in range(4):
            Rz = rot_z(a0 + 90 * k)
            u, v = Rz[:, 0], Rz[:, 1]

            def blk(u0, u1, v0, v1, w0, w1, col, name):
                ctr = hub + u * (u0 + u1) / 2 + v * (v0 + v1) / 2 + np.array([0.0, 0.0, z_s + (w0 + w1) / 2])
                b.part("block", (u1 - u0, v1 - v0, w1 - w0), ctr, Rz, col, name=name, **ND)

            blk(0.6, R + 0.3, -0.3, 0.3, -0.3, 0.3, vergue, "Vergue")
            blk(r1 - 0.2, R, W - 0.35, W, -0.2, 0.2, cadre, "Longeron")
            for ui in us:
                blk(ui - 0.2, ui + 0.2, -0.75, W - 0.1, -0.15, 0.15, cadre, "Latte")
            ua = us[1] if ouvert else us[0]
            blk(ua, us[-1], 0.1, W - 0.2, -0.05, 0.05, toile, "Toile")


def _toit_pignon(b, y0, demi_x, demi_z, h, col, faitage, rng):
    """Calotte à deux pans (faîtage le long de Z, pentes vers ±X) studdée, poutre de faîtage qui dépasse."""
    b.wedge((-demi_x, y0, -demi_z), (0, y0 + h, demi_z), vary(col, rng, 0.03), down="-x", studs="top", name="Calotte")
    b.wedge((0, y0, -demi_z), (demi_x, y0 + h, demi_z), vary(col, rng, 0.03), down="+x", studs="top", name="Calotte")
    b.box((-0.35, y0 + h - 0.3, -demi_z - 0.2), (0.35, y0 + h + 0.3, demi_z + 0.2), faitage, name="Faitage")


def _tour_ronde(b, y0, y1, r0, r1, n, couleurs, rng):
    """Tour de n cylindres empilés qui s'affinent (r0 en bas, r1 en haut) ; renvoie [(ya, yb, r), …]."""
    tiers = []
    for i in range(n):
        ya, yb = y0 + (y1 - y0) * i / n, y0 + (y1 - y0) * (i + 1) / n
        r = r0 + (r1 - r0) * i / max(1, n - 1)
        b.cyl((0, (ya + yb) / 2, 0), r, yb - ya, vary(couleurs[i % len(couleurs)], rng, 0.025), axis="y", name="Tour")
        tiers.append((ya, yb, r))
    return tiers


def _hors_joints(tiers, y, marge=0.3):
    """Décale y (plancher de galerie) s'il tombe trop près d'un joint entre deux cylindres de la tour."""
    if any(abs(y - ya) < marge for ya, _yb, _r in tiers[1:]):
        return y + 0.45
    return y


def _rayon_a(tiers, y, y1=None):
    """Rayon de la tour en y ; avec y1, le plus grand rayon entre y et y1 (un détail plaqué qui chevauche deux
    cylindres dépasse ainsi des deux)."""
    y1 = y if y1 is None else y1
    rs = [r for ya, yb, r in tiers if ya <= y1 and yb >= y]
    return max(rs) if rs else tiers[-1][2]


# ---------------------------------------------------------------------------
# Moulins : les quatre corps
# ---------------------------------------------------------------------------


def _moulin_bois(b, H, hub_y, petit, rng):
    """Moulin de bois sur tréteau (réf. 1 haut) : caisse en planches sur un pivot, toit en gradins, gouvernail rouge.
    Renvoie (z de départ de l'arbre, z le plus avancé du corps dans le disque des ailes)."""
    W = 6.0 if petit else 7.0
    D = W
    yb0 = round(0.40 * H, 1)
    yb1 = round(hub_y + 2.4, 1)
    bf, bo, bc = c("bois_fonce"), c("bois"), c("bois_clair")
    lf = W / 2 + 0.6                       # pieds du tréteau
    yt = yb0 - 1.0                         # haut des jambes (sous la sellette)
    with b.group("Treteau"):
        for sx in (-1, 1):
            for sz in (-1, 1):
                b.box((sx * lf - 0.9, 0, sz * lf - 0.9), (sx * lf + 0.9, 0.7, sz * lf + 0.9), vary("pierre", rng, 0.04),
                      studs="top", name="Plot")
                _poutre(b, (sx * lf, 0.3, sz * lf), (sx * 1.6, yt, sz * 1.6), 0.8, 0.8, bf, name="Jambe")
        ym = 0.45 * yt
        p = lf - (lf - 1.6) * 0.45
        for s in (-1, 1):
            b.box((-p - 0.25, ym - 0.25, s * p - 0.25), (p + 0.25, ym + 0.25, s * p + 0.25), bo, name="Traverse")
            b.box((s * p - 0.25, ym - 0.25, -p - 0.25), (s * p + 0.25, ym + 0.25, p + 0.25), bo, name="Traverse")
        # écharpes en zigzag sur les quatre faces (du pied d'un coin à la traverse du coin opposé)
        for (x0, z0, x1, z1) in ((-lf, -lf, p, -p), (lf, lf, -p, p), (-lf, lf, -p, -p), (lf, -lf, p, p)):
            _poutre(b, (x0, 0.7, z0), (x1, ym, z1), 0.45, 0.45, bo, ext1=0.2, name="Echarpe")
        b.cyl((0, (0.7 + yt - 0.4) / 2, 0), 0.9, yt - 1.1, bo, axis="y", name="Pivot")
        b.box((-2.1, yt - 0.4, -2.1), (2.1, yb0 - 0.6, 2.1), bf, name="Sellette")
    with b.group("Caisse"):
        b.box((-W / 2 - 0.3, yb0 - 0.6, -D / 2 - 0.3), (W / 2 + 0.3, yb0, D / 2 + 0.3), bf, name="Socle")
        nb = 5
        for i in range(nb):
            ya, yb = yb0 + (yb1 - yb0) * i / nb, yb0 + (yb1 - yb0) * (i + 1) / nb
            b.box((-W / 2, ya, -D / 2), (W / 2, yb, D / 2), vary(c("bois_pale") if i % 2 == 0 else bc, rng, 0.03),
                  name="Planches")
        for sx in (-1, 1):
            for sz in (-1, 1):
                b.box((sx * W / 2 - 0.35, yb0, sz * D / 2 - 0.35), (sx * W / 2 + 0.35, yb1, sz * D / 2 + 0.35), bf,
                      name="Montant")
        # toit en gradins (croupe en escalier), studs sur chaque marche
        toit = c("toit_rouge")
        for i, demi in enumerate((W / 2 + 1, W / 2, W / 2 - 1, W / 2 - 2)):
            y0 = yb1 + 0.8 * i
            b.box((-demi, y0, -demi), (demi, y0 + 0.8, demi), vary(toit, rng, 0.04) if i else shade(toit, 0.85),
                  studs="top", name="Toit")
        # fanion rouge et blanc planté au sommet du toit
        yf = yb1 + 3.2
        b.box((-0.15, yf - 0.4, 0.45), (0.15, yf + 3.0, 0.75), bf, name="Hampe", **ND)
        b.wedge((-0.1, yf + 1.6, 0.75), (0.1, yf + 2.9, 3.2), c("rouge"), down="+z", name="Fanion", **ND)
        # fenêtres (avant sous le moyeu, côtés) et porte arrière avec palier et échelle
        _fenetre(b, 0, yb0 + 3.0, D / 2, cadre=bf, rond=False)
        for sx in (-1, 1):   # couvre-joints verticaux sur la face avant
            b.box((sx * 1.6 - 0.25, yb0, -D / 2 - 0.15), (sx * 1.6 + 0.25, yb1, -D / 2 + 0.3), bf, name="CouvreJoint")
        for a in (90, -90):
            _fenetre(b, a, yb0 + 6.8, W / 2, cadre=bf, rond=False)
            for dx in (-1.15, 1.15):   # volets rouges ouverts
                with b.at((0, 0, 0), yaw=a):
                    b.box((dx - 0.4, yb0 + 5.9, -W / 2 - 0.2), (dx + 0.4, yb0 + 7.7, -W / 2 + 0.3), c("rouge"),
                          name="Volet", **ND)
        _plaque(b, 180, yb0 + 0.1, yb0 + 3.5, 2.0, D / 2, bf, 0.2, rond=False, name="Porte")
        b.box((-1.6, yb0 - 0.4, D / 2), (1.6, yb0 + 0.1, D / 2 + 1.2), bo, studs="top", name="Palier")
        zp, zs = D / 2 + 1.1, D / 2 + 1.1 + 0.18 * yb0
        for sx in (-1, 1):
            _poutre(b, (sx * 0.95, yb0 - 0.2, zp), (sx * 0.95, 0, zs), 0.3, 0.3, bf, name="Echelle")
        for k in range(1, 6):
            t = k / 6
            yk, zk = yb0 * (1 - t), zp + (zs - zp) * t
            b.box((-0.95, yk - 0.12, zk - 0.12), (0.95, yk + 0.12, zk + 0.12), bo, name="Barreau", **ND)
    with b.group("Gouvernail"):
        yq = hub_y + 1.0
        b.box((-0.25, yq - 0.25, D / 2 - 0.5), (0.25, yq + 0.25, D / 2 + 7.0), bf, name="Queue", **ND)
        _poutre(b, (0, yb0 + 5.0, D / 2), (0, yq - 0.2, D / 2 + 3.0), 0.4, 0.4, bf, ext1=0.1, name="Jambe", **ND)
        rouge = c("rouge")
        b.box((-0.15, yq - 1.6, D / 2 + 3.6), (0.15, yq + 1.6, D / 2 + 7.4), rouge, name="Gouvernail", **ND)
        b.wedge((-0.15, yq, D / 2 + 2.0), (0.15, yq + 1.6, D / 2 + 3.6), rouge, down="-z", name="Gouvernail", **ND)
        b.wedge_under((-0.15, yq - 1.6, D / 2 + 2.0), (0.15, yq, D / 2 + 3.6), rouge, down="-z", name="Gouvernail", **ND)
        b.box((-0.3, yq - 1.7, D / 2 + 5.2), (0.3, yq + 1.7, D / 2 + 5.8), c("blanc"), name="Bande", **ND)
    return -D / 2 + 1.0, -D / 2 - 1.0      # le premier gradin du toit déborde de 1 devant la caisse


def _moulin_rose(b, H, hub_y, petit, rng):
    """Tour ROSE (réf. 2) : cylindres qui s'affinent, bandeaux, galerie de bois sous une calotte à deux pans brune."""
    yt = hub_y - 1.6
    r0, r1 = 0.18 * H, 0.14 * H
    rose, rose_f = c("rose"), c("rose_fonce")
    with b.group("Tour"):
        b.cyl((0, 0.5, 0), r0 + 0.7, 1.0, vary("pierre", rng, 0.03), axis="y", studs="top", name="Socle")
        tiers = _tour_ronde(b, 1.0, yt, r0, r1, 5, (rose, mix(rose, rose_f, 0.3)), rng)
        b.cyl((0, 1.25, 0), r0 + 0.15, 0.5, rose_f, axis="y", name="Bandeau")
        y_g = _hors_joints(tiers, yt - 3.4)
        r_g = _rayon_a(tiers, y_g) + 1.7
        b.cyl((0, yt - 0.25, 0), r1 + 0.15, 0.5, c("blanc"), axis="y", name="Bandeau")
        _porte(b, 0, 1.0, r0, cadre=c("blanc"))
        _pots(b, 1.0, r0 + 0.2, (-32, 32), (c("fleur_rouge"), c("fleur_jaune")), rng)
        _fenetre(b, 0, yt - 7.5, _rayon_a(tiers, yt - 8.4, yt - 6.6))
        for a in (95, -95):
            _fenetre(b, a, 0.42 * yt, _rayon_a(tiers, 0.42 * yt - 0.9, 0.42 * yt + 0.9))
        _plaque(b, 180, y_g + 0.5, y_g + 3.0, 1.6, _rayon_a(tiers, y_g + 0.5, y_g + 3.0), c("bois_fonce"), 0.2,
                name="Porte")
    with b.group("Galerie"):
        _galerie(b, y_g, r_g, 6 if petit else 8, c("bois"), c("bois_fonce"))
    with b.group("Calotte"):
        b.cyl((0, yt + 0.35, 0), r1 + 0.5, 0.7, c("bois_fonce"), axis="y", name="Collier")
        _toit_pignon(b, yt + 0.7, r1 + 0.9, r1 + 1.2, 3.4, c("toit_brun"), c("bois_fonce"), rng)
    return -(r1 - 0.5), min(-r_g, -(r1 + 1.4))


def _moulin_pierre(b, H, hub_y, petit, rng):
    """Tour de pierre claire (réf. 3) : quelques pierres plus sombres, galerie à mi-hauteur, dôme bleu-gris en rangs."""
    yt = hub_y - 1.5
    r0, r1 = 0.175 * H, 0.135 * H
    pc, pm, pf = c("pierre_claire"), mix(c("pierre_claire"), c("pierre"), 0.55), c("pierre_fonce")
    with b.group("Tour"):
        b.cyl((0, 0.4, 0), r0 + 0.8, 0.8, vary(pf, rng, 0.03), axis="y", studs="top", name="Socle")
        tiers = _tour_ronde(b, 0.8, yt, r0, r1, 5, (pc, pm), rng)
        y_g = _hors_joints(tiers, round(0.42 * H, 1))
        r_g = _rayon_a(tiers, y_g) + 1.6
        # pierres plus sombres, en saillie
        for k in range(4 if petit else 6):
            a = float(rng.uniform(0, 360))
            y = float(rng.uniform(1.6, yt - 1.0))
            if abs(y - y_g) < 1.4:      # pas de pierre contre la galerie
                y = y_g - 2.0 if y_g - 2.0 > 1.6 else y_g + 2.6
            w = float(rng.uniform(1.0, 1.6))
            col = vary(pf if k % 2 else c("pierre"), rng, 0.03)
            h = float(rng.uniform(0.5, 0.8))
            _plaque(b, a, y, y + h, w, _rayon_a(tiers, y, y + h), col, 0.12, name="Pierre", **ND)
        _porte(b, 0, 0.8, r0, cadre=pf)
        _pots(b, 0.8, r0 + 0.25, (-34, 34), (c("fleur_rose"), c("fleur_blanche")), rng)
        _fenetre(b, 0, yt - 2.6, _rayon_a(tiers, yt - 3.5, yt - 1.7), cadre=c("bois_fonce"))
        yf = 0.24 * H + 1.0
        for a in (100, -100):
            _fenetre(b, a, yf, _rayon_a(tiers, yf - 0.9, yf + 0.9), cadre=c("bois_fonce"))
        _plaque(b, 180, y_g + 0.5, y_g + 3.0, 1.6, _rayon_a(tiers, y_g + 0.5, y_g + 3.0), c("bois_fonce"), 0.2,
                name="Porte")
    with b.group("Galerie"):
        _galerie(b, y_g, r_g, 6 if petit else 8, c("bois"), c("bois_fonce"))
    with b.group("Dome"):
        dome, dome_f = c("dome"), c("dome_fonce")
        b.cyl((0, yt + 0.35, 0), r1 + 0.7, 0.7, dome_f, axis="y", studs="top", name="Avancee")
        y = yt + 0.7
        for i, (dr, h) in enumerate(((0.35, 1.1), (-0.4, 1.0), (-1.25, 0.9), (-2.1, 0.8))):
            col = vary(dome if i % 2 == 0 else mix(dome, dome_f, 0.45), rng, 0.02)
            b.cyl((0, y + h / 2, 0), r1 + dr, h, col, axis="y", studs="top", name="Dome")
            y += h
        b.ball((0, y + 0.3, 0), 0.75, dome_f, name="Epi")
        b.box((-1.0, hub_y - 1.0, -(r1 + 1.0)), (1.0, hub_y + 1.0, -(r1 - 0.6)), dome_f, studs="top", name="Lucarne")
    return -(r1 - 0.3), min(-r_g, -(r1 + 1.0))


def _moulin_calotte(b, H, hub_y, petit, rng):
    """Moulin à calotte : socle octogonal de pierre, plate-forme, corps octogonal de bois sombre, calotte BLEUE."""
    yt = hub_y - 1.5
    rb = 0.19 * H + 0.2
    yb = round(0.15 * H, 1)
    ra = 0.165 * H
    rbb = ra - 0.45
    bf = c("bois_fonce")
    with b.group("Socle"):
        _octogone(b, 0, yb, rb, vary("pierre", rng, 0.03), name="Socle")
        _porte(b, 0, 0, rb, w=2.0, h=3.0, cadre=c("pierre_fonce"), rond=False)
        for a in (135, -135, 90):
            y = float(rng.uniform(1.0, yb - 1.2))
            _plaque(b, a, y, y + 0.7, float(rng.uniform(1.2, 1.8)), rb, vary("pierre_fonce", rng, 0.04), 0.12, rond=False,
                    name="Pierre", **ND)
    with b.group("Plateforme"):
        _galerie(b, yb, rb + 0.9, 6 if petit else 8, c("bois"), bf, h=1.3)
    with b.group("Corps"):
        ymid = yb + 0.5 + (yt - yb - 0.5) * 0.55
        _octogone(b, yb + 0.5, ymid, ra, vary(bf, rng, 0.03), name="Corps")
        _octogone(b, ymid, yt, rbb, vary(mix(bf, c("bois"), 0.3), rng, 0.03), name="Corps")
        _octogone(b, ymid - 0.25, ymid + 0.25, ra + 0.15, c("blanc"), name="Ceinture", **ND)
        _fenetre(b, 0, (yb + ymid) / 2 + 0.6, ra, cadre=c("blanc"), rond=False)
        for a in (90, -90):
            _fenetre(b, a, (ymid + yt) / 2, rbb, cadre=c("blanc"), rond=False)
        _plaque(b, 180, yb + 0.5, yb + 3.4, 1.8, ra, c("bois"), 0.2, rond=False, name="Porte")
    with b.group("Calotte"):
        b.cyl((0, yt + 0.3, 0), rbb + 0.5, 0.6, bf, axis="y", name="Collier")
        _toit_pignon(b, yt + 0.6, rbb + 0.6, rbb + 1.0, 2.8, c("toit_bleu"), c("blanc"), rng)
    return -(rbb - 0.4), min(-(rb + 0.9), -(rbb + 1.2))


def moulin(b, variant: int = 0, hauteur: float = 30) -> dict:
    """Moulin à vent (avant = ailes vers -Z local). `hauteur` fixe l'échelle : moyeu à 0,74 × hauteur, grandes ailes de
    rayon min(22, 0,5 × hauteur), pointe basse à 0,24 × hauteur du sol (plus de 3 studs). Emprise au sol ≤ 12 × 12 (hors ailes et
    gouvernail). Variantes : 0 bois et ailes jaunes, 1 tour rose, 2 tour de pierre à dôme, 3 calotte bleue.
    Budget : ≤ 150 pièces (hauteur ≥ 26), ≤ 110 sinon. Renvoie la hauteur du haut de l'aile la plus haute."""
    v = variant % 4
    H = float(hauteur)
    petit = H < 26
    rng = b.rng
    n0 = len(b.parts)
    hub_y = round(0.74 * H, 2)
    R = round(min(22.0, 0.5 * H), 2)
    with b.group("Moulin"):
        corps = (_moulin_bois, _moulin_rose, _moulin_pierre, _moulin_calotte)[v]
        z_dep, z_obst = corps(b, H, hub_y, petit, rng)
        z_s = z_obst - 1.0
        if v == 0:
            cols = (c("bois_fonce"), c("jaune_fonce"), c("jaune"), c("rouge"), 18, 0.27, False)
        elif v == 1:
            cols = (c("bois"), c("bois_fonce"), c("voile"), c("laiton"), -16, 0.26, True)
        elif v == 2:
            cols = (c("bois"), c("bois_fonce"), c("voile"), c("laiton"), 20, 0.25, True)
        else:
            cols = (c("bois_fonce"), c("bois"), mix(c("voile"), c("mur_creme"), 0.6), c("blanc"), 14, 0.25, False)
        vergue, cadre, toile, nez, a0, larg, ouvert = cols
        _ailes(b, hub_y, z_dep, z_s, R, a0, vergue, cadre, toile, nez, n_lattes=3 if petit else 4, larg=larg,
               ouvert=ouvert)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Butte herbue (sous le moulin de pierre de droite)
# ---------------------------------------------------------------------------


def _bandes(a, d, ox=0.0, oz=0.0, k=0.62, kz=0.8):
    """Ellipse approchée par trois bandes qui ne se recouvrent pas : (x0, x1, z0, z1, côtés extérieurs en x)."""
    return ((ox - k * a, ox + k * a, oz - d, oz + d, ()),
            (ox + k * a, ox + a, oz - kz * d, oz + kz * d, (1,)),
            (ox - a, ox - k * a, oz - kz * d, oz + kz * d, (-1,)))


def colline(b, variant: int = 0, largeur: float = 40, profondeur: float = 36, hauteur: float = 8) -> dict:
    """Butte en trois gradins à contour arrondi : flancs de terre avec une strate claire, chapeaux d'herbe studdés qui
    débordent de 0,3, plateau plat (au moins 16 × 16, centré) exactement à y = hauteur, escalier de pierre vers
    l'avant (-Z), fleurs et rochers sur les paliers. ≤ 40 pièces."""
    rng = b.rng
    n0 = len(b.parts)
    H = float(hauteur)
    a1, d1 = largeur / 2, profondeur / 2
    a3, d3 = max(0.56 * a1, 10.5), max(0.56 * d1, 10.5)
    a2, d2 = (a1 + a3) / 2, (d1 + d3) / 2
    ys = (0.0, round(0.4 * H, 1), round(0.7 * H, 1), H)
    sg = (-1, 1)[variant % 2]
    off2 = (sg * 0.8, -0.6 * sg)
    gradins = ((a1, d1, 0.0, 0.0), (a2, d2) + off2, (a3, d3, 0.0, 0.0))
    herbes = (c("herbe"), c("herbe_claire"), c("herbe_claire") if variant % 3 == 2 else c("herbe"))
    terres = (c("terre_fonce"), c("terre"), c("terre"))
    with b.group("Butte"):
        for t, (a, d, ox, oz) in enumerate(gradins):
            y0, y1 = ys[t], ys[t + 1]
            bas = -0.5 if t == 0 else y0
            for (x0, x1, z0, z1, ext) in _bandes(a, d, ox, oz):
                b.box((x0, bas, z0), (x1, y1 - 0.8, z1), terres[t], name="Flanc")
                ex0 = 0.3 if -1 in ext else 0.0
                ex1 = 0.3 if 1 in ext else 0.0
                b.box((x0 - ex0, y1 - 0.8, z0 - 0.3), (x1 + ex1, y1, z1 + 0.3), herbes[t], studs="top", name="Herbe")
                if t < 2:  # strate claire (déborde de 0,15)
                    ym = y0 + (y1 - 0.8 - y0) * 0.5
                    b.box((x0 - 0.15, ym - 0.25, z0 - 0.15), (x1 + 0.15, ym + 0.25, z1 + 0.15), c("terre_claire"),
                          name="Strate", **ND)
        # escalier de pierre vers l'avant : 3 marches au premier gradin, 2 au deuxième, 2 au troisième (largeurs
        # alternées 3,2 / 3,0 : deux marches qui se recouvrent n'ont pas de flanc commun)
        pierre = c("pierre_claire")
        km = 0
        for t, (n, z_bord) in enumerate(((3, -d1), (2, -d2 + off2[1]), (2, -d3))):
            y0, y1 = ys[t], ys[t + 1]
            for k in range(n):
                top = y0 + (y1 - y0) * (k + 1) / n + (0.1 if k == n - 1 else 0.0)
                zf = z_bord - 0.3 - (n - k) * 1.2
                hw = 1.6 if km % 2 == 0 else 1.5
                km += 1
                b.box((-hw, top - (y1 - y0) / n - 0.3, zf), (hw, top, z_bord + 0.6), vary(pierre, rng, 0.04),
                      studs="top", name="Marche")

        def dans(x, z, t, marge):
            a, d, ox, oz = gradins[t]
            return any(x0 + marge < x < x1 - marge and z0 + marge < z < z1 - marge
                       for (x0, x1, z0, z1, _e) in _bandes(a, d, ox, oz))

        def palier(t, marge=0.8):
            """Point au hasard sur l'anneau visible du gradin t (hors du gradin du dessus et de l'escalier)."""
            a, d = gradins[t][0], gradins[t][1]
            for _ in range(200):
                x, z = float(rng.uniform(-a, a)), float(rng.uniform(-d, d))
                if dans(x, z, t, marge) and not dans(x, z, t + 1, -marge) and not (abs(x) < 3.5 and z < 0):
                    return x, z
            return None

        # fleurs et rochers sur les paliers
        fleurs = (c("fleur_rouge"), c("fleur_jaune"), c("fleur_blanche"), c("fleur_rose"))
        for k in range(5):
            t = k % 2
            pt = palier(t)
            if pt:
                x, z = pt
                b.box((x - 0.4, ys[t + 1], z - 0.4), (x + 0.4, ys[t + 1] + 0.5, z + 0.4), fleurs[(k + variant) % 4],
                      name="Fleur", **ND)
        pt = palier(0, 1.6)
        if pt:
            x, z = pt
            b.boxc((x, ys[1] + 0.6, z), (2.2, 1.2, 1.8), vary("roche", rng, 0.04), yaw=20, studs="top", name="Rocher")
            b.boxc((x, ys[1] + 1.45, z), (1.2, 0.5, 1.0), vary("roche_claire", rng, 0.04), yaw=-15, studs="top",
                   name="Rocher")
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Palmiers
# ---------------------------------------------------------------------------


def palmier(b, variant: int = 0, hauteur: float = 14) -> dict:
    """Palmier courbé : tronc de 5 ou 6 cylindres annelés (tronc / tronc_clair) décalés en courbe, couronne de 6 palmes
    (une lame plate qui part vers l'extérieur + une lame en coin qui retombe ; une palme sur deux plus basse et plus
    tombante), 2-3 noix de coco. `hauteur` = hauteur de la couronne. 0 : courbe douce ; 1 : haut et presque droit ;
    2 : palmier de plage très penché. Emprise recentrée sur l'origine (rayon ≤ 6). ≤ 20 pièces."""
    v = variant % 3
    rng = b.rng
    n0 = len(b.parts)
    H = float(hauteur)
    n = 6 if v == 1 else 5
    lean = (2.4, 1.0, 4.0)[v]
    pts = []
    for i in range(n + 1):
        t = i / n
        off = lean * (math.sin(t * math.pi / 2) ** 0.8 if v == 2 else t ** 1.8)
        pts.append(np.array([off, -0.3 + (H - 0.1) * t, 0.0]))
    with b.group("Palmier"):
        for i in range(n):
            r = 0.7 - 0.26 * i / (n - 1)
            col = vary("tronc" if i % 2 == 0 else "tronc_clair", rng, 0.03)
            _cyl_entre(b, pts[i], pts[i + 1], r, col, ext0=0.0 if i == 0 else 0.25, ext1=0.25, name="Tronc")
        T = pts[-1] + np.array([0.0, 0.2, 0.0])
        phi0 = float(rng.uniform(0, 60))
        palmes = (c("palme_claire"), c("palme"), c("palme_fonce"))
        for k in range(6):
            # décalage ±5° entre les deux moitiés : deux palmes opposées ne sont jamais alignées (faces coplanaires)
            phi = math.radians(phi0 + k * 60 + (5 if k < 3 else -5) + float(rng.uniform(-3, 3)))
            dh = np.array([math.cos(phi), 0.0, math.sin(phi)])
            haute = k % 2 == 0
            e1 = math.radians(float(rng.uniform(12, 20) if haute else rng.uniform(-5, 5)))
            e2 = math.radians(float(rng.uniform(-35, -25) if haute else rng.uniform(-50, -40)))
            L1 = float(rng.uniform(3.0, 3.3) if haute else rng.uniform(2.8, 3.1)) * (1.04 if v == 1 else 1.0)
            L2 = float(rng.uniform(2.9, 3.2))
            d1 = dh * math.cos(e1) + np.array([0.0, math.sin(e1), 0.0])
            d2 = dh * math.cos(e2) + np.array([0.0, math.sin(e2), 0.0])
            a = T - d1 * 0.45
            m = T + d1 * L1
            p = m + d2 * L2
            _lame(b, a, m, 1.4, 0.3, vary(palmes[0 if haute else 1], rng, 0.04), studs="top", name="Palme", **ND)
            _lame(b, m - d2 * 0.3, p, 1.2, 0.4, vary(palmes[1 if haute else 2], rng, 0.04), coin=True, name="Palme", **ND)
        for k in range(2 if v == 1 else 3):
            ang = math.radians(phi0 + 30 + k * 120)
            b.ball(T + np.array([0.6 * math.cos(ang), -0.7, 0.6 * math.sin(ang)]), 0.45, vary("coco", rng, 0.05),
                   name="Coco", **ND)
    _recentrer(b, n0)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Mandariniers et buissons
# ---------------------------------------------------------------------------


def _dans_bloc(pt, bloc, marge=0.0) -> bool:
    """Le point (x, y, z) est-il dans le bloc (cy, sx, sy, sz, yaw) centré sur l'axe ?"""
    y0, sx, sy, sz, yaw = bloc[:5]
    a = math.radians(yaw)
    lx = math.cos(a) * pt[0] - math.sin(a) * pt[2]
    lz = math.sin(a) * pt[0] + math.cos(a) * pt[2]
    return abs(lx) < sx / 2 - marge and abs(pt[1] - y0) < sy / 2 - marge and abs(lz) < sz / 2 - marge


def oranger(b, variant: int = 0) -> dict:
    """Petit mandarinier : tronc court, feuillage en 3 blocs studdés (jupe sombre, cœur tourné de 45°, chapeau clair :
    silhouette octogonale), 8 mandarines à moitié dans le feuillage, cuvette de terre au pied. Hauteur 6-7, emprise
    ≈ 5 × 5. 0 boule, 1 large et plat, 2 haut et étroit. ≤ 16 pièces."""
    v = variant % 3
    rng = b.rng
    n0 = len(b.parts)
    f, ff, fc = c("feuillage"), c("feuillage_fonce"), mix(c("feuillage"), c("herbe_claire"), 0.4)
    # (centre y, taille x, taille y, taille z, yaw, couleur) : jupe, cœur, chapeau
    blocs = (((3.0, 5.0, 1.2, 5.0, 0, ff), (3.9, 4.2, 2.2, 4.2, 45, f), (5.5, 2.8, 1.0, 2.8, 0, fc)),
             ((2.9, 5.2, 1.2, 4.6, 15, ff), (3.8, 4.4, 1.8, 4.4, 60, f), (5.15, 3.0, 0.9, 2.6, 15, fc)),
             ((3.3, 4.2, 1.4, 4.2, 0, ff), (4.6, 3.6, 2.4, 3.6, 45, f), (6.3, 2.4, 1.0, 2.4, 0, fc)))[v]
    with b.group("Oranger"):
        b.cyl((0, 0.1, 0), 1.4, 0.2, c("terre_fonce"), axis="y", name="Cuvette", **ND)
        b.box((-0.4, 0, -0.4), (0.4, blocs[0][0] - 0.2, 0.4), vary("tronc", rng, 0.04), name="Tronc")
        for (y, sx, sy, sz, yaw, col) in blocs:
            b.boxc((0, y, 0), (sx, sy, sz), vary(col, rng, 0.03), yaw=yaw, studs="top", name="Feuillage", **ND)
        # mandarines : centre 0,1 hors d'une face (dessus de la jupe, flancs du cœur, dessus du chapeau)
        poses, essais = [], 0
        while len(poses) < 8 and essais < 200:
            essais += 1
            k = (0, 1, 1, 0, 1, 1, 2, 0)[len(poses)]
            y0, sx, sy, sz, yaw, _ = blocs[k]
            a = math.radians(yaw)
            if k == 1:   # flanc du cœur
                side = int(rng.integers(4))
                t = float(rng.uniform(-0.32, 0.32))
                lx, lz = ((sx / 2 + 0.1) * (1 if side % 2 else -1), t * sz) if side < 2 else \
                    (t * sx, (sz / 2 + 0.1) * (1 if side % 2 else -1))
                ly = y0 + float(rng.uniform(-0.3, 0.3)) * sy
            else:        # sur le dessus de la jupe ou du chapeau
                lx, lz = float(rng.uniform(-0.42, 0.42)) * sx, float(rng.uniform(-0.42, 0.42)) * sz
                ly = y0 + sy / 2 + 0.1
            pt = (math.cos(a) * lx + math.sin(a) * lz, ly, -math.sin(a) * lx + math.cos(a) * lz)
            if any(_dans_bloc(pt, bl, 0.05) for j, bl in enumerate(blocs) if j != k):
                continue
            if any(math.dist(pt, q) < 1.2 for q in poses):
                continue
            poses.append(pt)
        for pt in poses:
            b.ball(pt, 0.48, vary("agrume", rng, 0.05), name="Mandarine", **ND)
    return _infos(b, n0)


def buisson(b, variant: int = 0) -> dict:
    """Buisson rond ≈ 3 × 3 × 2,5 : deux blocs de feuillage studdés (le haut tourné de 45°) et 4 fleurs (deux posées
    sur le dessus, deux piquées dans les flancs). 0 rouges, 1 jaunes (plus haut), 2 roses et blanches (plus large),
    3 rouges et jaunes. Sans collision. ≤ 6 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    fl = ((c("fleur_rouge"),) * 2, (c("fleur_jaune"),) * 2, (c("fleur_rose"), c("fleur_blanche")),
          (c("fleur_rouge"), c("fleur_jaune")))[v]
    # (bas : x, h, z), (haut : côté, h)
    (ax, ah, az), (bc, bh) = (((3.0, 1.4, 2.6), (2.1, 1.1)), ((2.7, 1.6, 2.6), (2.0, 1.2)),
                              ((3.4, 1.2, 2.8), (2.3, 1.0)), ((3.0, 1.4, 3.0), (2.2, 1.1)))[v]
    yaw = float(rng.uniform(0, 30))
    with b.group("Buisson"):
        b.boxc((0, ah / 2, 0), (ax, ah, az), vary("feuillage_fonce", rng, 0.04), yaw=yaw, studs="top", name="Feuillage",
               **ND)
        b.boxc((0, ah + bh / 2, 0), (bc, bh, bc), vary("feuillage", rng, 0.04), yaw=yaw + 45, studs="top",
               name="Feuillage", **ND)
        a = math.radians(yaw)
        haut = ah + bh
        pos = ((0.18 * bc, haut, 0.14 * bc, 0), (-0.24 * bc, haut, -0.24 * bc, 1),
               (ax / 2 + 0.05, 0.62 * ah, 0.1 * az, 0), (-0.15 * ax, 0.58 * ah, az / 2 + 0.05, 1))
        for i, (lx, y, lz, k) in enumerate(pos):
            x, z = math.cos(a) * lx + math.sin(a) * lz, -math.sin(a) * lx + math.cos(a) * lz
            if i < 2:      # posée sur le dessus
                b.box((x - 0.4, y, z - 0.4), (x + 0.4, y + 0.5, z + 0.4), fl[k], name="Fleur", **ND)
            else:          # piquée dans un flanc (dépasse de 0,45)
                b.boxc((x, y, z), (0.8, 0.8, 0.8), fl[k], yaw=yaw, name="Fleur", **ND)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Rochers et îlots
# ---------------------------------------------------------------------------


def rocher(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Amas de rochers de plage ≈ 6 × 6 × 4 × taille : blocs trapus légèrement basculés (beige-gris chaud, studs sur
    les dessus), le pied enfoncé de 0,6 × taille sous l'origine. 0 gros bloc et éboulis, 1 aiguille et sa compagne,
    2 bosse moussue (plaques de mousse), 3 dalles plates de bord de mer. ≤ 12 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    s = float(taille)
    g = _teintes_roche()
    y0 = -0.6

    def R(cx, cz, sx, sy, sz, col, yaw, tx=0.0, tz=0.0, base=None, mousse=0.0):
        """Bloc de roche (dessous à `base`, par défaut enfoncé de 0,6), basculé de tx / tz degrés ; `mousse` > 0 pose
        une plaque de mousse qui suit la bascule sur son dessus (fraction de la surface)."""
        bas = y0 if base is None else base
        Rm = rot_y(yaw) @ rot_x(tx) @ rot_z(tz)
        ctr = np.array([cx, bas + sy / 2, cz]) * s
        b.part("block", (sx * s, sy * s, sz * s), ctr, Rm, vary(col, rng, 0.035), studs="top", name="Rocher")
        if mousse:
            top = ctr + Rm @ np.array([0.0, sy * s / 2 + 0.15, 0.0])
            b.part("block", (sx * s * mousse, 0.3, sz * s * mousse * 0.85), top, Rm, vary("roche_mousse", rng, 0.04),
                   studs="top", name="Mousse", **ND)

    with b.group("Rochers"):
        if v == 0:
            R(0, 0, 4.6, 3.2, 3.8, g[0], 12, 4, -5)
            R(0.4, -0.3, 3.2, 3.9, 3.0, g[1], 55, -5, 4)
            R(0.3, -0.3, 2.2, 1.0, 1.8, g[2], 30, 7, 0, base=3.0)
            R(-2.8, 1.5, 2.0, 1.9, 1.6, g[1], -20, 0, 10)
            R(2.6, 1.8, 1.5, 1.3, 1.3, g[2], 35, 10, 5)
            R(2.0, -2.4, 1.1, 1.0, 1.0, g[0], 8, -8, 0)
            R(-1.2, -2.6, 1.8, 0.9, 1.3, g[2], 70, 0, -6)
        elif v == 1:
            R(0, 0, 2.8, 5.6, 2.4, g[1], 10, 3, -4)
            R(0.3, -0.2, 2.2, 4.3, 2.8, g[0], 55, -5, 6)
            R(0.1, 0.1, 2.0, 0.7, 1.8, g[2], 30, 0, 5, base=4.85)
            R(2.4, 1.3, 2.0, 2.7, 1.8, g[2], -25, 6, 8)
            R(-2.1, -1.4, 1.6, 1.2, 1.4, g[1], 40, -6, 0)
            R(-1.3, 2.3, 2.6, 1.0, 1.8, g[0], 15, 0, -5)
            R(1.4, -2.3, 1.2, 0.9, 1.0, g[2], -35, 8, 0)
        elif v == 2:
            R(0, 0, 5.0, 2.4, 4.2, g[1], 8, 3, -3, mousse=0.6)
            R(-0.4, 0.3, 3.4, 1.4, 2.8, g[2], 30, -4, 5, base=1.6, mousse=0.7)
            R(3.0, 1.2, 1.9, 1.7, 1.6, g[0], -20, 8, 6, mousse=0.6)
            R(-3.0, -1.0, 1.4, 1.1, 1.2, g[0], 25, 0, -8)
            R(1.0, 2.6, 1.3, 0.9, 1.0, g[2], 5, -6, 0)
        else:
            dalles = ((0, 0, 3.4, 2.6, 1.3, 8, 3, -4), (2.8, 1.6, 2.4, 2.0, 1.1, -25, -6, 3),
                      (-2.6, 1.2, 2.4, 2.2, 1.0, 40, 4, 6), (0.8, -2.6, 2.0, 1.6, 0.9, 15, 0, -6),
                      (-1.6, -2.4, 1.4, 1.2, 0.8, -10, 6, 0))
            for i, (x, z, sx, sz, h, yaw, tx, tz) in enumerate(dalles):
                R(x, z, sx, h, sz, g[(i + 1) % 3], yaw, tx, tz)
    return _infos(b, n0)


def _teintes_roche():
    """Roches chaudes de bord de mer : foncée (brun-gris), moyenne, claire (sablée)."""
    return (mix(c("roche_fonce"), c("terre_fonce"), 0.35), mix(c("roche"), c("terre"), 0.25),
            mix(c("roche"), c("sable_fonce"), 0.2))


def ilot(b, variant: int = 0, rayon: float = 14) -> dict:
    """Îlot posé dans l'eau : origine À LA SURFACE de l'eau (y = 0 local). Socle de roche (y -2 → 0,5), corps de sable
    (0,5 → 1,6) et petite dune, plage mouillée côté +X, éperon rocheux basculé côté -X, rochers dans l'eau, anneau
    d'écume (y 0,02 → 0,14). 0 : deux palmiers ; 1 : un palmier, mouette sur l'éperon, crabe sur la plage ; 2 : un
    palmier et un coffre à moitié enterré ; 3 : un palmier et un tronc échoué. Tout tient dans le rayon `rayon`.
    Buisson fleuri en plus sur les variantes 2 et 3. ≤ 55 pièces palmiers compris."""
    from assets.mobilier import coffre_tresor, crabe, mouette

    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    r = float(rayon)
    roc = _teintes_roche()
    ox = 0.06 * r
    with b.group("Ilot"):
        b.cyl((0, 0.08, 0), 0.95 * r, 0.12, c("ecume"), axis="y", name="Ecume", shadow=False, **ND)
        for (x0, x1, z0, z1, _e) in _bandes(0.8 * r, 0.72 * r, k=0.55, kz=0.75):
            b.box((x0, -2.0, z0), (x1, 0.5, z1), vary(roc[0], rng, 0.03), studs="top", name="Socle")
        for (x0, x1, z0, z1, _e) in _bandes(0.64 * r, 0.56 * r, ox=ox, k=0.55, kz=0.75):
            b.box((x0, 0.5, z0), (x1, 1.6, z1), c("sable"), studs="top", name="Sable")
        b.box((0.45 * r, -0.8, -0.32 * r), (0.93 * r, 0.55, 0.32 * r), c("sable_mouille"), studs="top", name="Plage")
        dune = (-0.24 * r + ox, -0.26 * r, 0.22 * r + ox, 0.22 * r)
        b.box((dune[0], 1.6, dune[1]), (dune[2], 2.3, dune[3]), c("sable_clair"), studs="top", name="Dune")
        # éperon rocheux côté -X : bloc principal basculé, compagnon, chapeau, petite pierre
        ex, ez = -0.6 * r, 0.18 * r
        he = min(7.5, 3.0 + 0.3 * r)
        Rm = rot_y(12) @ rot_x(4) @ rot_z(-5)
        ctr = np.array([ex, 0.2 + he / 2, ez])
        b.part("block", (0.26 * r, he, 0.24 * r), ctr, Rm, vary(roc[1], rng, 0.03), studs="top", name="Eperon")
        cap = ctr + Rm @ np.array([0.0, he / 2 + 0.2, 0.0])
        b.part("block", (0.18 * r, 0.5, 0.16 * r), cap, Rm, vary(roc[2], rng, 0.03), studs="top", name="Eperon")
        b.part("block", (0.2 * r, 0.62 * he, 0.22 * r), (ex + 0.15 * r, 0.2 + 0.31 * he, ez - 0.16 * r),
               rot_y(50) @ rot_x(-5) @ rot_z(6), vary(roc[0], rng, 0.03), studs="top", name="Eperon")
        b.part("block", (0.13 * r, 0.32 * he, 0.12 * r), (ex - 0.06 * r, 0.2 + 0.16 * he, ez + 0.2 * r),
               rot_y(-20) @ rot_z(8), vary(roc[2], rng, 0.03), studs="top", name="Eperon")
        # rochers dans l'eau
        for k, ang in enumerate((200 + 25 * v, 320 - 15 * v)):
            a = math.radians(ang)
            sz = 0.1 * r + 0.6
            b.part("block", (sz, 1.8 + 0.3 * k, sz * 0.8), (0.87 * r * math.cos(a), -0.3, 0.87 * r * math.sin(a)),
                   rot_y(float(rng.uniform(0, 60))) @ rot_x(6), vary(roc[k % 2], rng, 0.04), studs="top", name="RocherEau")
    # palmiers (hauteur adaptée au rayon : la couronne, de rayon ≤ 6, reste dans l'emprise)
    hp = min(13.0, 6.0 + 0.45 * r)
    if v == 0:
        k = 1.0 if r >= 12 else 0.6     # petits îlots : palmiers plus rapprochés (couronnes dans l'emprise)
        palm = ((-0.1 * r * k, 0.12 * r * k, 1, hp, 30), (0.3 * r * k, -0.2 * r * k, 2, hp - 2.5, 200))
    elif v == 2:
        palm = ((-0.05 * r, 0.05 * r, 0, hp - 0.5, 60),)
    else:
        palm = ((0.05 * r, 0.0, 2 if v == 1 else 0, hp, 160 if v == 1 else 20),)
    for i, (x, z, pv, h, yaw) in enumerate(palm):
        y = 2.3 if dune[0] + 0.8 < x < dune[2] - 0.8 and dune[1] + 0.8 < z < dune[3] - 0.8 else 1.6
        with b.at((x, y, z), yaw=yaw, group=f"Ilot/Palmier{i}"):
            palmier(b, variant=pv, hauteur=h)
    if v == 1:
        top = cap + Rm @ np.array([0.0, 0.25, 0.0])
        with b.at(tuple(top), yaw=110, group="Ilot/Mouette"):
            mouette(b, variant=0)
        with b.at((0.74 * r, 0.55, 0.1 * r), yaw=-60, group="Ilot/Crabe"):
            crabe(b, variant=0)
    elif v == 2:
        with b.at((0.3 * r, 1.6 - 0.9, -0.3 * r), yaw=24, group="Ilot/Coffre"):
            coffre_tresor(b, variant=1)
    if v in (2, 3):
        with b.at((0.15 * r, 1.6, 0.42 * r), group="Ilot/Buisson"):
            buisson(b, variant=2 if v == 2 else 0)
    if v == 3:
        with b.group("Ilot"):
            _cyl_entre(b, (0.78 * r, 0.9, -0.24 * r), (0.84 * r, 0.9, 0.26 * r), 0.35, c("bois_flotte"),
                       name="BoisFlotte", **ND)
    return _infos(b, n0)
