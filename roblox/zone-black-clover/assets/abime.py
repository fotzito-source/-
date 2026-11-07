"""Royaume démoniaque de la fin de course (zone Black Clover), version « stud ».

Château démoniaque gothique sur sa falaise (repère final : sa porte en arc brisé est la sortie de la zone), arbre
démoniaque colossal, îlots de roche flottants enchaînés au sol, falaises noires latérales, obélisques de la place
rituelle, racines géantes et grappes de cristaux.

Palette : pierre noire du château (`chateau`, `chateau_clair`, arêtes `chateau_arete`), basalte et roches noires
(`roche(rng)`), racines noires, cramoisi et violet profond ; lueurs en Neon (`lueur_violette`, `lueur_cramoisie`,
`cristal`, `feu_violet`, `feu_cramoisi`). Tout se lit sombre en plein jour : chaque masse noire porte des lueurs.
Propriété intellectuelle : aucun nom, aucun emblème, aucune statue ni gargouille à visage, aucun trèfle ni
quadrilobe, aucune étoile, aucune lettre ; fenêtres lancéolées et oculi simples ; clé de la porte lisse.
"""

from __future__ import annotations

import math
from contextlib import contextmanager

import numpy as np

from assets import mobilier
from kit import mix, rot_x, rot_y, rot_z, shade
from palette import c, roche, vary

DECO = dict(collide=False)
FIN = dict(collide=False, shadow=False)
NEON = dict(material="Neon", collide=False, shadow=False)


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

def _v(p) -> np.ndarray:
    return np.asarray(p, float)


def _repere(d):
    """Longueur et matrice dont l'axe X suit d (Y aussi vertical que possible)."""
    d = _v(d)
    n = float(np.linalg.norm(d))
    x = d / n
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return n, np.column_stack([x, y, z])


def _poutre(b, a, bb, ep, col, ep_z=None, ext=0.0, tors=0.0, name="Poutre", **kw):
    """Bloc de section ep × ep_z tendu de a à bb, prolongé de `ext` à chaque bout (joints fermés), tourné de
    `tors` degrés autour de son axe (torsion des troncs et des racines)."""
    a, bb = _v(a), _v(bb)
    n, R = _repere(bb - a)
    if tors:
        R = R @ rot_x(tors)
    return b.part("block", (n + 2 * ext, ep, ep if ep_z is None else ep_z), (a + bb) / 2, R, col, name=name, **kw)


def _barre(b, xa, ya, xb, yb, z0, z1, ep, col, ext=0.0, name="Barre", **kw):
    """Barre dans un plan de façade (x, y), de (xa, ya) à (xb, yb), largeur `ep` dans le plan, profondeur z0..z1."""
    L = math.hypot(xb - xa, yb - ya) + 2 * ext
    ang = math.degrees(math.atan2(yb - ya, xb - xa))
    return b.part("block", (L, ep, z1 - z0), ((xa + xb) / 2, (ya + yb) / 2, (z0 + z1) / 2), rot_z(ang), col,
                  name=name, **kw)


def _tri(b, M, C, A, ep, col, dehors, studs=False, name="Pan", **kw):
    """Fine plaque triangulaire (coin Roblox d'épaisseur `ep`) : triangle rectangle en M, MC le long de la base,
    MA vers le sommet ; la face extérieure est dans le plan du triangle, l'épaisseur part à l'opposé de `dehors`."""
    M, C, A = _v(M), _v(C), _v(A)
    h = float(np.linalg.norm(A - M))
    d = float(np.linalg.norm(C - M))
    Y = (A - M) / h
    Z = (M - C) / d
    X = np.cross(Y, Z)
    s = 1.0 if float(np.dot(X, dehors)) > 0 else -1.0
    ctr = M + Y * h / 2 - Z * d / 2 - s * X * ep / 2
    face = "Right" if s > 0 else "Left"
    return b.part("wedge", (ep, h, d), ctr, np.column_stack([X, Y, Z]), col, studs=(face,) if studs else (),
                  name=name, **kw)


def _facette(b, P, Q, A, ep, col, interieur, **kw) -> int:
    """Triangle PQA (pied de la hauteur issue de A dans [PQ]) en un ou deux triangles rectangles."""
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
        _tri(b, F, P, A, ep, col, nrm, **kw)
        n += 1
    if t < L - 0.02:
        _tri(b, F, Q, A, ep, col, nrm, **kw)
        n += 1
    return n


def _fleche(b, cx, y0, cz, diag, H, col, ep=0.45, rot45=True, studs=True, name="Fleche", **kw) -> float:
    """Flèche pyramidale lisse à quatre pans (8 pièces). rot45 : base en losange (une arête face à chaque axe),
    `diag` = distance entre deux sommets opposés de la base. Renvoie la hauteur du sommet."""
    r = diag / 2
    if rot45:
        pts = [(cx + r, y0, cz), (cx, y0, cz + r), (cx - r, y0, cz), (cx, y0, cz - r)]
    else:
        pts = [(cx - r, y0, cz - r), (cx + r, y0, cz - r), (cx + r, y0, cz + r), (cx - r, y0, cz + r)]
    A = (cx, y0 + H, cz)
    for i in range(4):
        _facette(b, pts[i], pts[(i + 1) % 4], A, ep, col, (cx, y0 + H * 0.3, cz), studs=studs, name=name, **kw)
    return y0 + H


def _sx(s: int, u0: float, u1: float):
    """Bornes x triées d'un intervalle [u0, u1] pris du côté s (u = |x|)."""
    return (s * u0, s * u1) if s > 0 else (s * u1, s * u0)


def _bx(b, s, u0, u1, y0, y1, z0, z1, col, **kw):
    """Bloc aligné donné en u = |x| du côté s."""
    x0, x1 = _sx(s, u0, u1)
    return b.box((x0, y0, z0), (x1, y1, z1), col, **kw)


@contextmanager
def _face(b, cote: str, coord: float):
    """Repère de façade : plan local z = 0 sur la face (`cote` = direction extérieure : -z, +z, -x, +x, placée en
    `coord`), extérieur vers -z local, x local le long de la face (voir `_u`)."""
    yaw = {"-z": 0, "+z": 180, "+x": -90, "-x": 90}[cote]
    pos = (0, 0, coord) if cote in ("-z", "+z") else (coord, 0, 0)
    with b.at(pos, yaw=yaw):
        yield


def _u(cote: str, x: float, z: float = 0.0) -> float:
    """Coordonnée le long d'une façade (x local du repère `_face`) d'un point (x, z)."""
    return {"-z": x, "+z": -x, "+x": z, "-x": -z}[cote]


# --- éléments de façade (repère `_face` : plan z = 0, extérieur vers -z) -----------------------------------

def _lancette(b, u, y0, w, h, col=None, pointe=None, prof=0.2, appui=True) -> None:
    """Fenêtre lancéolée lumineuse (Neon) en saillie de `prof`, pointe en arc brisé (deux coins), appui de pierre."""
    col = c("lueur_violette") if col is None else col
    b.box((u - w / 2, y0, -prof), (u + w / 2, y0 + h, 0.1), col, name="Fenetre", **NEON)
    t = (w * 0.9 if w >= 2.15 else 0.0) if pointe is None else pointe
    if t > 0.05:
        b.wedge((u - w / 2, y0 + h, -prof), (u, y0 + h + t, 0.1), col, down="-x", name="Fenetre", **NEON)
        b.wedge((u, y0 + h, -prof), (u + w / 2, y0 + h + t, 0.1), col, down="+x", name="Fenetre", **NEON)
    if appui:
        b.box((u - w / 2 - 0.4, y0 - 0.6, -prof - 0.3), (u + w / 2 + 0.4, y0, 0.1), c("chateau_arete"),
              name="Appui", **DECO)


def _archere(b, u, y0, h=4.0, col=None) -> None:
    """Archère lumineuse (fente verticale)."""
    col = c("lueur_cramoisie") if col is None else col
    b.box((u - 0.35, y0, -0.15), (u + 0.35, y0 + h, 0.1), col, name="Archere", **NEON)


def _oculus(b, u, y, r, col=None, cadre=True) -> None:
    """Oculus rond et simple (disque Neon dans une couronne de pierre) ; aucun remplage."""
    col = c("lueur_cramoisie") if col is None else col
    if cadre:
        b.cyl((u, y, -0.15), r + 0.8, 0.5, c("chateau_arete"), axis="z", name="Oculus", **DECO)
    b.cyl((u, y, -0.35), r, 0.5, col, axis="z", name="Oculus", **NEON)


def _banniere(b, u, y_haut, w, L, col=None) -> None:
    """Bannière unie (liseré sombre) pendue à une tringle scellée dans la façade, pointe en V en bas (5 pièces)."""
    col = c("cramoisi") if col is None else col
    yb = y_haut - L
    t = w * 0.45
    b.box((u - w / 2 - 0.6, y_haut - 0.3, -1.4), (u + w / 2 + 0.6, y_haut + 0.3, 0.1), c("fer_fonce"), name="Tringle",
          **DECO)
    b.box((u - w / 2, yb, -1.15), (u + w / 2, y_haut - 0.3, -0.8), col, name="Banniere", **DECO)
    b.wedge_under((u - w / 2, yb - t, -1.15), (u, yb, -0.8), col, down="-x", name="Banniere", **DECO)
    b.wedge_under((u, yb - t, -1.15), (u + w / 2, yb, -0.8), col, down="+x", name="Banniere", **DECO)
    b.box((u - w / 2 - 0.1, yb + 1.0, -1.3), (u + w / 2 + 0.1, yb + 1.8, -1.1), c("cramoisi_fonce"), name="Lisere", **FIN)


def _pinacle(b, x, y0, z, w, h, col=None, aiguille=None) -> float:
    """Pinacle : dé carré puis aiguille effilée en deux tronçons tournés de 45° (3 pièces). Renvoie le sommet."""
    col = c("chateau_clair") if col is None else col
    b.box((x - w / 2, y0, z - w / 2), (x + w / 2, y0 + h, z + w / 2), col, name="Pinacle")
    p = 1.6 * h if aiguille is None else aiguille
    y1 = y0 + h
    b.boxc((x, y1 + 0.3 * p, z), (0.55 * w, 0.6 * p, 0.55 * w), c("obsidienne"), yaw=45, name="Aiguille", **DECO)
    b.boxc((x, y1 + 0.8 * p, z), (0.28 * w, 0.4 * p, 0.28 * w), c("obsidienne"), yaw=45, name="Aiguille", **DECO)
    return y1 + p


def _couronne(b, x0, x1, z0, z1, y, h_fleche, *, w_tambour=None, h_tambour=7.0, pinacles=(0, 1, 2, 3),
              fenetre=True, col_fleche=None, saillie=1.0, h_pinacle=4.5, finial=True, cz_tambour=None) -> float:
    """Couronnement d'une tour carrée (x0..x1, z0..z1) posé en y : mâchicoulis, parapet à studs, pinacles d'angle
    (indices 0 : avant gauche, 1 : avant droit, 2 : arrière droit, 3 : arrière gauche), tambour, corniche et flèche
    en losange. Renvoie le sommet."""
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    w = min(x1 - x0, z1 - z0)
    b.box((x0 - saillie, y, z0 - saillie), (x1 + saillie, y + 2, z1 + saillie), c("chateau_arete"), name="Machicoulis")
    m = saillie - 0.5
    b.box((x0 - m, y + 2, z0 - m), (x1 + m, y + 5, z1 + m), c("chateau"), studs="top", name="Parapet")
    yp = y + 5
    e = max(1.6, min(3.0, 0.2 * w))
    coins = [(x0 - m + e / 2, z0 - m + e / 2), (x1 + m - e / 2, z0 - m + e / 2), (x1 + m - e / 2, z1 + m - e / 2),
             (x0 - m + e / 2, z1 + m - e / 2)]
    for i in pinacles:
        px, pz = coins[i]
        _pinacle(b, px, yp, pz, e, h_pinacle)
    wt = w_tambour or round(0.62 * w)
    if cz_tambour is not None:
        cz = cz_tambour
    b.box((cx - wt / 2, yp, cz - wt / 2), (cx + wt / 2, yp + h_tambour, cz + wt / 2), c("chateau_clair"), name="Tambour")
    if fenetre:
        with _face(b, "-z", cz - wt / 2):
            _lancette(b, cx, yp + 1.2, max(1.0, 0.16 * wt), h_tambour - 3.2 - 0.9 * max(1.0, 0.16 * wt), appui=False)
    yc = yp + h_tambour
    b.box((cx - wt / 2 - 0.5, yc, cz - wt / 2 - 0.5), (cx + wt / 2 + 0.5, yc + 1, cz + wt / 2 + 0.5),
          c("chateau_arete"), studs="top", name="Corniche")
    top = _fleche(b, cx, yc + 1, cz, wt + 1, h_fleche, c("ardoise_fonce") if col_fleche is None else col_fleche)
    if finial:
        b.box((cx - 0.3, top - 1.5, cz - 0.3), (cx + 0.3, top + 2.5, cz + 0.3), c("fer_fonce"), name="Epi", **FIN)
        top += 2.5
    return top


def _corne(b, p, dx, dz, L=3.2, ep=0.9) -> None:
    """Pointe d'angle recourbée (gargouille stylisée, sans visage) : deux segments qui sortent de l'angle (p) vers
    (dx, dz) puis plongent ; 2 pièces."""
    p = _v(p)
    n = math.hypot(dx, dz) or 1.0
    ux, uz = dx / n, dz / n
    q = p + _v((ux * L, -0.25 * L, uz * L))
    r = q + _v((ux * 0.45 * L, -0.55 * L, uz * 0.45 * L))
    _poutre(b, p - _v((ux, 0, uz)) * 0.6, q, ep, c("obsidienne"), ext=0.2, name="Corne", **DECO)
    _poutre(b, q, r, ep * 0.55, c("obsidienne"), ext=0.15, name="Corne", **FIN)


def _merlons(b, xa, xb, y0, z0, z1, larg=2.5, pas=5.0, h=3.0, col=None) -> None:
    """Merlons réguliers de xa à xb (créneaux entre eux)."""
    col = c("chateau_arete") if col is None else col
    n = max(1, int(round((xb - xa - larg) / pas)) + 1)
    gap = (xb - xa - larg) / (n - 1) if n > 1 else 0.0
    for i in range(n):
        x = xa + i * gap
        b.box((x, y0, z0), (x + larg, y0 + h, z1), col, studs="top", name="Merlon")


# ---------------------------------------------------------------------------
# 1) Château démoniaque (repère final et sortie)
# ---------------------------------------------------------------------------

YG = 90.0          # dessus de la masse de la porte (chemin de ronde)


def _arc_brise(xo: float, hp: float, ya: float, n: int = 11, lam: float = 0.5, expo: float = 1.45,
               cle: float = 2.5) -> list:
    """Gradins d'un arc brisé surbaissé, côté x > 0, de la naissance vers la clé : [(x_int, x_ext, y_intrados)],
    puis la clé [(0, cle, ya)]. L'intrados part verticalement de (xo, hp) et monte en pointe jusqu'à la clé."""
    xs = [round((cle + (xo - cle) * (1 - (k / n) ** expo)) * 2) / 2 for k in range(n + 1)]
    xs[0], xs[-1] = xo, cle
    out = []
    for k in range(n):
        t = 1 - xs[k] / xo
        f = (1 - lam) * math.sqrt(max(0.0, t * (2 - t))) + lam * t
        out.append((xs[k + 1], xs[k], round((hp + (ya - hp) * f) * 2) / 2))
    out.append((0.0, cle, ya))
    return out


def _h_falaise(u: float) -> float:
    """Hauteur de la falaise du château selon |x| (haute contre les tours, creux vers 180, remonte au bord)."""
    pts = ((68, 52), (96, 49), (126, 45), (150, 38), (176, 26), (204, 28), (239, 36))
    for (u0, h0), (u1, h1) in zip(pts, pts[1:]):
        if u <= u1:
            t = (u - u0) / (u1 - u0)
            return h0 + (h1 - h0) * max(0.0, min(1.0, t))
    return pts[-1][1]


def _falaise_chateau(b, rng, L2, D, xt) -> dict:
    """Falaise de basalte de part et d'autre des tours de porte (|x| de xt à L2), en ressauts : colonnes de roche à
    deux assises (corniche à studs ou pan incliné entre les deux, liseré de strate plus clair), rampes de crête entre
    colonnes de hauteurs différentes, lèvres, pics, éperons tournés, talus d'éboulis, cristaux violets dans les
    failles, racines noires, deux arbres morts. Renvoie {s: [(u0, u1, h, zf)]} (h : dessus, zf : avant)."""
    ZF = -D
    res = {}
    for s in (-1, 1):
        cols = []
        u = xt
        while u < L2 - 0.5:
            u1 = u + float(rng.uniform(5, 12))
            if L2 - u1 < 4:
                u1 = L2
            h = round(_h_falaise((u + u1) / 2) + float(rng.uniform(-4, 4)))
            zf = ZF + float(rng.choice((-2.0, -1.0, 0.0, 0.0, 1.0, 2.0, 3.0)))
            cols.append((u, u1, h, zf))
            u = u1
        res[s] = cols
        with b.group("Roche"):
            hauts = []
            for i, (u0, u1, h, zf) in enumerate(cols):
                x0, x1 = _sx(s, u0, u1)
                if h > 30:
                    h1, h2 = round(h * float(rng.uniform(0.22, 0.4))), round(h * float(rng.uniform(0.58, 0.78)))
                    d1, d2 = float(rng.choice((1.5, 2.0, 3.0))), float(rng.choice((1.5, 2.0, 3.0)))
                    assises = [(0, h1, zf), (h1, h2, zf + d1), (h2, h, zf + d1 + d2)]
                else:
                    h1 = round(h * float(rng.uniform(0.35, 0.6)))
                    assises = [(0, h1, zf), (h1, h, zf + float(rng.choice((2.0, 3.0))))]
                dos = [D, D - float(rng.choice((0.0, 2.0, 3.0))), D - float(rng.choice((3.0, 4.0, 6.0)))]
                for k, (ya, yb, z) in enumerate(assises):
                    col = roche(rng) if rng.random() < 0.8 else vary("basalte_clair", rng, 0.08)
                    zb = dos[k] if (u0 + u1) / 2 > xt + 12 else D
                    b.box((x0, ya, z), (x1, yb, zb), col, studs="top", name="Roche")
                    if k == 0:
                        continue
                    zp = assises[k - 1][2]
                    r = rng.random()
                    if r < 0.35:
                        b.wedge((x0, ya, zp), (x1, ya + float(rng.uniform(2.5, 5)), z), vary("basalte_clair", rng, 0.08),
                                down="-z", studs="top", name="Pan")
                    elif r < 0.65 and z - zp >= 1.5:
                        a_, b_ = _sx(s, u0 + 0.3, u1 - 0.3)
                        b.box((a_, ya - 0.8, max(zp - 0.4, ZF - 1.9)), (b_, ya + 0.4, zp + 1.0),
                              vary("basalte_clair", rng, 0.06), studs="top", name="Strate")
                hauts.append((assises[-1][2], h, assises[1][0], assises[0][2], assises[1][2]))
                dz = assises[-1][2] - zf
                if (u0 + u1) / 2 < 150:
                    if rng.random() < 0.55:
                        a, bb = float(rng.uniform(0, 2)), float(rng.uniform(0, 2))
                        _bx(b, s, u0 + a, u1 - bb, h, h + float(rng.uniform(2, 4)), zf + dz + 0.5,
                            zf + dz + float(rng.uniform(3, 5)), roche(rng), studs="top", name="Crete")
                else:
                    for k in range(1 if rng.random() < 0.5 else 2):
                        hp_ = float(rng.uniform(6, 16)) / (k + 1)
                        w = float(rng.uniform(4, 7)) / (k + 1)
                        um = min((u0 + u1) / 2 + float(rng.uniform(-2, 2)), L2 - 0.8 * w - 0.5)
                        zc = zf + dz + float(rng.uniform(3, 16))
                        b.part("block", (w, hp_ + 2, w * 0.8), (s * um, h + hp_ / 2 - 1 + k * hp_ * 0.8, zc),
                               rot_y(float(rng.uniform(0, 90))) @ rot_z(float(rng.uniform(-14, 14))), roche(rng),
                               studs="top", name="Pic")
                if zf >= ZF - 0.01 and rng.random() < 0.55:
                    b.wedge((x0, 0, zf - 2.0), (x1, float(rng.uniform(3, 6)), zf), vary("basalte_clair", rng, 0.08),
                            down="-z", studs="top", name="Eboulis")
            # rampes de crête : un coin adossé à la colonne la plus haute, posé sur la plus basse
            for i in range(len(cols) - 1):
                (u0, u1, h, zf), (v0, v1, g, zg) = cols[i], cols[i + 1]
                if abs(h - g) < 4 or rng.random() < 0.25:
                    continue
                if h > g:          # la colonne i est plus haute : rampe sur i + 1, qui descend vers +u
                    za = max(hauts[i + 1][0], hauts[i][0])
                    w = min((v1 - v0) / 2 - 0.3, float(rng.uniform(3, 6)))
                    x0, x1 = _sx(s, v0 - 0.05, v0 + w)
                    down = "+x" if s > 0 else "-x"
                    b.wedge((x0, g - 0.2, za), (x1, h - float(rng.uniform(0.5, 2.5)), D), roche(rng), down=down,
                            studs="top", name="Rampe")
                else:
                    za = max(hauts[i + 1][0], hauts[i][0])
                    w = min((u1 - u0) / 2 - 0.3, float(rng.uniform(3, 6)))
                    x0, x1 = _sx(s, u1 - w, u1 + 0.05)
                    down = "-x" if s > 0 else "+x"
                    b.wedge((x0, h - 0.2, za), (x1, g - float(rng.uniform(0.5, 2.5)), D), roche(rng), down=down,
                            studs="top", name="Rampe")
        with b.group("Eperons"):
            for i in range(1, len(cols), 3):
                u0, _, h, zf = cols[i]
                zmin = min(zf, cols[i - 1][3])
                hh = 0.4 * min(h, cols[i - 1][2]) + float(rng.uniform(0, 5))
                zc = max(zmin + 1.0, ZF - 2.0 + 3.6)
                b.boxc((s * u0, hh / 2, zc), (5.0, hh, 5.0), roche(rng), yaw=45 + float(rng.uniform(-6, 6)),
                       studs="top", name="Eperon")
        with b.group("Cristaux"):
            for i in range(1, len(cols), 4):
                u0, u1, h, zf = cols[i]
                _, _, h1, z0, z1 = hauts[i]
                _grappe_corniche(b, rng, s * (u0 + u1) / 2, h1, (z0 + z1) / 2, 1.0 + 0.25 * (i % 3))
    with b.group("Racines"):
        for s, k in ((1, 2), (-1, 3), (1, 7), (-1, 9), (1, 13), (-1, 15)):
            cols = res[s]
            if k >= len(cols):
                continue
            u0, u1, h, zf = cols[k]
            um = (u0 + u1) / 2
            pts = [(um, h + 1.0, zf + 9.0), (um + 2.0, h - 0.2, zf + 4.0), (um + 3.5, h * 0.6, max(ZF + 1.6, zf + 1.0)),
                   (um + 6.0, h * 0.25, ZF + 0.8), (um + 9.0, 0.3, ZF + 0.9)]
            for j in range(4):
                (ua, ya_, za), (ub, yb_, zb) = pts[j], pts[j + 1]
                _poutre(b, (s * ua, ya_, za), (s * ub, yb_, zb), (2.6, 2.2, 1.8, 1.4)[j], c(("racine", "racine_claire")[j % 2]),
                        ext=0.5, tors=float(rng.uniform(0, 45)), name="Racine", **(DECO if j == 3 else {}))
            b.box((s * (um + 9.0) - 1.0, -0.2, ZF + 1.6 - 1.0), (s * (um + 9.0) + 1.0, 0.25, ZF + 1.6 + 1.0),
                  c("brulis"), name="Terre", **DECO)
        for s, k in ((1, 4), (-1, 11)):
            cols = res[s]
            if k >= len(cols):
                continue
            u0, u1, h, zf = cols[k]
            p0 = (s * (u0 + 2), h * 0.45, max(zf + 0.5, ZF + 1.2))
            p1 = (s * (u0 + 4), h * 0.25, max(ZF + 0.2, zf - 1.0))
            p2 = (s * (u0 + 7.5), 0.6, max(ZF + 0.4, zf - 1.2))
            _poutre(b, p0, p1, 2.0, c("racine"), ext=0.6, name="Racine")
            _poutre(b, p1, p2, 1.6, c("racine_claire"), ext=0.5, name="Racine")
            _poutre(b, p2, (p2[0] + s * 3.0, -0.4, p2[2] + 0.3), 1.2, c("racine"), ext=0.3, name="Racine", **DECO)
    with b.group("ArbresMorts"):
        for s, k, v in ((1, 14, 1), (-1, 16, 3)):
            cols = res[s]
            if k >= len(cols):
                continue
            u0, u1, h, zf = cols[k]
            with b.at((s * (u0 + u1) / 2, h, zf + 10.0), yaw=float(rng.uniform(0, 360))):
                mobilier.arbre_mort(b, variant=v, hauteur=12.0)
    return res


def _grappe_corniche(b, rng, x, y, z, t=1.0, zmin_abs=-26.4) -> None:
    """Grappe de cristaux violets posée sur une corniche (centre du pied en (x, y, z)) : un grand prisme Neon, un
    prisme sombre et un petit prisme Neon, inclinés en éventail (3 pièces) ; rien en avant de zmin_abs."""
    a0 = float(rng.uniform(0, 360))
    for k, (L, e, col, neon) in enumerate(((7.5, 1.8, "cristal", True), (5.5, 1.4, "cristal_fonce", False),
                                            (4.0, 1.1, "lueur_violette", True))):
        a = math.radians(a0 + 120 * k)
        el = math.radians((72, 52, 48)[k])
        d = np.array([math.cos(a) * math.cos(el), math.sin(el), math.sin(a) * math.cos(el)])
        p0 = np.array([x + 0.8 * math.cos(a) * (k > 0), y - 0.8, z + 0.8 * math.sin(a) * (k > 0)])
        p0[2] = max(p0[2], zmin_abs + e * t)
        if p0[2] + d[2] * L * t - 0.8 * e * t < zmin_abs:
            d[2] = abs(d[2])
        p1 = p0 + d * L * t
        _poutre(b, p0, p1, e * t, c(col), tors=45, name="Cristal", **(NEON if neon else DECO))


def _porte_chateau(b, rng, arc, arc_dos, xo, hp, D, YC) -> None:
    """Porte : arc brisé à claveaux alternés et clé lisse en façade (anneau de 3,9 de profondeur), écoinçons, passage
    rectangulaire derrière (plafond plat à YC), arc de revers plus simple, masse jusqu'au chemin de ronde,
    mâchicoulis, parapet, merlons, pinacle sur la clé, oculi cramoisis et lancettes dans les écoinçons, herse de fer
    relevée (bas à 42)."""
    ZF = -D
    zt = ZF + 0.6                       # plan des écoinçons (en retrait de l'anneau)
    ZR = ZF + 3.0                       # arrière de l'anneau de façade
    hv = 5.0
    ya = arc[-1][2]
    ch, cc, ca = c("chateau"), c("chateau_clair"), c("chateau_arete")
    with b.group("Arc"):
        for k, (xa, xb, y) in enumerate(arc[:-1]):
            col = ca if k % 2 == 0 else cc
            for s in (-1, 1):
                x0, x1 = _sx(s, xa, xb)
                b.box((x0, y, ZF - 0.9), (x1, y + hv, ZR), col, name="Claveau")
                b.box((x0, y + hv, zt), (x1, YG, ZR), ch, name="Ecoincon")
        cl = arc[-1][1]
        b.box((-cl, ya - 0.5, ZF - 1.6), (cl, YG + 0.5, ZR), ca, name="Cle")
    with b.group("Voute"):
        b.box((-xo, YC, ZR), (xo, YG, D - 3.0), ch, studs="top", name="Plafond")
        for (xa, xb, y) in arc_dos[:-1]:
            for s in (-1, 1):
                x0, x1 = _sx(s, xa, xb)
                b.box((x0, y, D - 3.0), (x1, YG, D), ch, studs="top", name="ArcRevers")
        cl = arc_dos[-1][1]
        b.box((-cl, arc_dos[-1][2], D - 3.0), (cl, YG, D), ch, studs="top", name="ArcRevers")
    with b.group("Ecoincons"):
        with _face(b, "-z", zt):
            yl = max(y for (xa, xb, y) in arc if not (43.2 <= xa or 40.8 >= xb)) + hv + 2.0
            for s in (-1, 1):
                _oculus(b, s * 33.0, 76.0, 3.6)
                _lancette(b, s * 17.0, 77.0, 1.8, 7.0)
                _lancette(b, s * 42.0, yl, 2.2, 84.0 - yl - 2.2)
        poses: list = [(29.0 - 5, 76 - 5, 37.0 + 5, 76 + 5), (-37.0 - 5, 71, -29.0 + 5, 81), (14.5, 75.5, 19.5, 87.5),
                       (-19.5, 75.5, -14.5, 87.5), (39.5, 50, 44.5, 88), (-44.5, 50, -39.5, 88), (23.8, 50, 28.2, 92),
                       (-28.2, 50, -23.8, 92)]
        n = essais = 0
        while n < 12 and essais < 300:
            essais += 1
            x = float(rng.uniform(5, xo - 3)) * (1 if rng.random() < 0.5 else -1)
            w, h = float(rng.choice((2.0, 3.0, 4.0))), float(rng.choice((1.0, 1.5)))
            ext = max(y for (xa, xb, y) in arc if not (abs(x) + w / 2 < xa or abs(x) - w / 2 > xb)) + hv + 0.8
            ytop = YG - 3.0
            if ytop - ext < h + 0.5:
                continue
            y = float(rng.uniform(ext, ytop - h))
            r = (x - w / 2 - 0.5, y - 0.5, x + w / 2 + 0.5, y + h + 0.5)
            if any(r[0] < q[2] and q[0] < r[2] and r[1] < q[3] and q[1] < r[3] for q in poses):
                continue
            poses.append(r)
            b.box((x - w / 2, y, zt - 0.2), (x + w / 2, y + h, zt + 0.1), vary("chateau_arete", rng, 0.06),
                  name="Pierre", **DECO)
            n += 1
    with b.group("Couronne"):
        b.box((-xo, YG - 2, ZF - 1.0), (xo, YG, zt), ca, name="Machicoulis")
        b.box((-xo, YG, ZF - 0.4), (xo, YG + 3.5, ZF + 1.6), ch, studs="top", name="Parapet")
        for s in (-1, 1):
            for x in (9.0, 16.0, 22.0, 30.0, 37.0, 44.0):
                b.box((s * x - 1.5, YG + 3.5, ZF - 0.4), (s * x + 1.5, YG + 6.5, ZF + 1.6), ca, studs="top",
                      name="Merlon")
        _pinacle(b, 0.0, YG + 3.5, ZF + 0.6, 3.2, 5.0, aiguille=11.0)
        for s in (-1, 1):
            u0, u1 = 24.8, 27.2
            y0 = max(y for (xa, xb, y) in arc if not (u1 <= xa or u0 >= xb)) + hv - 0.3
            _bx(b, s, u0, u1, y0, YG + 3.7, ZF - 1.3, zt + 0.2, cc, name="Pilastre")
            _pinacle(b, s * (u0 + u1) / 2, YG + 3.7, ZF - 0.1, 2.4, 3.5, aiguille=8.0)
    with b.group("Revers"):
        b.box((-xo, YG, D - 1.6), (xo, YG + 2.5, D), ch, studs="top", name="Parapet")
        for s in (-1, 1):
            for x in (25.0, 32.0, 39.0, 46.0):
                b.box((s * x - 1.4, YG + 2.5, D - 1.6), (s * x + 1.4, YG + 5.0, D), ca, studs="top", name="Merlon")
    with b.group("Herse"):
        zh = ZR + 1.2
        fer = c("fer_fonce")
        for x in range(-42, 43, 7):
            b.box((x - 0.4, hp + 2.8, zh - 0.4), (x + 0.4, YC + 1.0, zh + 0.4), fer, name="Barreau")
            b.part("block", (0.8, 0.8, 0.8), (x, hp + 2.6, zh), rot_z(45), fer, name="Pointe", **DECO)
        for y in (hp + 4.5, hp + 8.0):
            b.box((-(xo + 0.5), y, zh - 0.3), (xo + 0.5, y + 0.7, zh + 0.3), fer, name="Traverse")


def _tour_porte(b, rng, s, xo, xt, hp, D) -> None:
    """Tour de porte carrée (|x| de xo à xt) : talus, contreforts d'angle à larmiers, cordons, bannière cramoisie,
    lancette violette, archères cramoisies, couronne à mâchicoulis, pinacles, tambour et flèche (≈ 140)."""
    ZF = -D
    ZT = ZF + 20.0
    H = 92.0
    um = (xo + xt) / 2
    ch, cc, ca = c("chateau"), c("chateau_clair"), c("chateau_arete")
    x0, x1 = _sx(s, xo, xt)
    b.wedge((x0, 0, ZF - 2.0), (x1, 10, ZF), cc, down="-z", studs="top", name="Talus")
    b.box((x0, 0, ZF), (x1, H, ZT), ch, name="Tour")
    for (u0, u1) in ((xo + 0.05, xo + 2.6), (xt - 2.6, xt - 0.05)):
        _bx(b, s, u0, u1, 4, 84, ZF - 1.4, ZF + 0.1, cc, name="Contrefort")
        xa, xb = _sx(s, u0, u1)
        b.wedge((xa, 84, ZF - 1.4), (xb, 87, ZF), ca, down="-z", studs="top", name="Larmier")
        b.wedge((xa, 40, ZF - 2.0), (xb, 44, ZF - 1.4), ca, down="-z", studs="top", name="Larmier")
        _bx(b, s, u0 + 0.3, u1 - 0.3, 4, 40, ZF - 2.0, ZF - 1.4, cc, name="Contrefort")
    for y in (hp, 68.0):
        _bx(b, s, xo + 2.6, xt - 2.6, y, y + 1.2, ZF - 0.6, ZF, ca, name="Cordon")
    with _face(b, "-z", ZF):
        _banniere(b, s * um, 84.0, 6.0, 32.0)
        _lancette(b, s * um, 21.0, 2.4, 10.0)
        _archere(b, s * (um - 3.6), 12.0)
        _archere(b, s * (um + 3.6), 12.0)
    x0, x1 = _sx(s, xo, xt)
    _couronne(b, x0, x1, ZF, ZT, H, 32.0, w_tambour=11.0, h_tambour=8.0, h_pinacle=5.0)
    _corne(b, (s * (xt - 0.4), H - 3.0, ZF + 0.6), s * 3.0, -0.55)
    _corne(b, (s * (xo + 0.4), H - 3.0, ZF + 0.6), -s * 3.0, -0.55)


def _tunnel(b, xo, xt, hp, D, YC) -> None:
    """Parois du passage (nervures à impostes, lanternes violettes) ; rien sous 40 au-dessus de |x| < xo."""
    ZT = -D + 20.0
    ch, ca = c("chateau"), c("chateau_arete")
    for s in (-1, 1):
        _bx(b, s, xo + 3.0, xt, 0, hp, ZT, D, ch, name="Paroi")
        _bx(b, s, xo, xt, hp, YG, ZT, D, ch, name="Paroi")
        for (z0, z1) in ((ZT, ZT + 3.0), (9.0, 12.0), (D - 3.0, D)):
            _bx(b, s, xo + 0.3, xo + 3.0, 0, hp - 1.5, z0, z1, c("chateau_clair"), name="Nervure")
            _bx(b, s, xo, xo + 3.0, hp - 1.5, hp, max(ZT, z0 - 0.4), min(D, z1 + 0.4), ca, name="Imposte")
        for zl in (3.5, 17.0):
            with b.at((s * (xo + 3.0), 27.0, zl), yaw=90 * s):
                mobilier.lanterne_murale(b, variant=1)


def _donjon(b, D) -> None:
    """Donjon central en retrait de 9 sur la façade (z -16 → 23, 42 de large), au-dessus de la porte : contreforts à
    larmiers, lancettes, couronne et la plus haute flèche (≈ 164)."""
    z0, z1 = -16.0, D - 2.0
    ch, cc, ca = c("chateau"), c("chateau_clair"), c("chateau_arete")
    b.box((-21, YG, z0), (21, 116, z1), cc, name="Donjon")
    for s in (-1, 1):
        _bx(b, s, 17.5, 21.5, YG, 110, z0 - 2.5, z0, ch, name="Contrefort")
        x0, x1 = _sx(s, 17.5, 21.5)
        b.wedge((x0, 110, z0 - 2.5), (x1, 113, z0), ca, down="-z", studs="top", name="Larmier")
        f = "+x" if s > 0 else "-x"
        with _face(b, f, s * 21.0):
            _lancette(b, _u(f, 0, 2.0), 100.0, 1.6, 12.0)
    with _face(b, "-z", z0):
        for u, h in ((-9.0, 11.0), (0.0, 13.0), (9.0, 11.0)):
            _lancette(b, u, 101.0, 2.6, h)
    with _face(b, "+z", z1):
        for u in (-8.0, 8.0):
            _lancette(b, u, 100.0, 1.6, 10.0, appui=False)
    _couronne(b, -21, 21, z0, z1, 116, 27.0, w_tambour=12.0, h_tambour=11.0, h_pinacle=7.0, saillie=1.2,
              cz_tambour=z0 + 7.5)
    with b.group("ArcsBoutants"):
        for s in (-1, 1):
            for zc in (-9.0, 6.0):
                pa = (s * 21.0, 110.0, zc)                    # tête contre le donjon
                pb = (s * 51.5, 97.5, max(zc, -12.0))         # pied sur le parapet de la tour de porte
                _poutre(b, pa, pb, 1.6, ca, ep_z=1.4, ext=0.4, name="ArcBoutant")
                m = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2 - 1.2, (pa[2] + pb[2]) / 2)
                _poutre(b, (s * 24.0, 107.5, zc), m, 1.1, ch, ext=0.3, name="ArcBoutant", **DECO)


def _toit(b, s, u0, u1, z0, z1, y, h, col=None) -> None:
    """Toit à deux pans d'ardoise violette, faîtage le long de x, débord de 0,8 (studs sur les pans)."""
    col = c("violet_profond") if col is None else col
    x0, x1 = _sx(s, u0, u1)
    zm = (z0 + z1) / 2
    b.wedge((x0, y, z0 - 0.8), (x1, y + h, zm), col, down="-z", studs="top", name="Toit")
    b.wedge((x0, y, zm), (x1, y + h, z1 + 0.8), shade(col, 0.85), down="+z", studs="top", name="Toit")


def _tourelle(b, s, u0, u1, z0, z1, y0, y1, h_fleche, *, fen=(), cote=None, oculus=None, h_tambour=6.0,
              pin=(0, 1, 2, 3), col=None, fen_tambour=True) -> float:
    """Tourelle carrée posée sur la falaise : fût, lancettes en façade (y, w, h), lancette de côté, oculus, couronne."""
    x0, x1 = _sx(s, u0, u1)
    b.box((x0, y0, z0), (x1, y1, z1), c("chateau") if col is None else col, name="Tourelle")
    um = (u0 + u1) / 2
    with _face(b, "-z", z0):
        for (yy, w, h) in fen:
            _lancette(b, s * um, yy, w, h)
        if oculus:
            _oculus(b, s * um, oculus[0], oculus[1])
    if cote:
        f = "+x" if s > 0 else "-x"
        with _face(b, f, s * u1):
            yy, w, h = cote
            _lancette(b, _u(f, 0, (z0 + z1) / 2), yy, w, h)
    return _couronne(b, x0, x1, z0, z1, y1, h_fleche, h_tambour=h_tambour, pinacles=pin, fenetre=fen_tambour,
                     h_pinacle=3.5)


def _socle(cols, u0, u1) -> float:
    """Base d'un bâtiment posé sur la falaise : 3 sous la colonne la plus basse qu'il recouvre."""
    hs = [h for (a, bb, h, zf) in cols if not (bb <= u0 or a >= u1)]
    return (min(hs) if hs else 40.0) - 3.3


def _aile(b, rng, s, xt, D, cols) -> None:
    """Aile du château sur la falaise (côté s) : courtine crénelée, haute tourelle, grande salle à toit violet et
    contreforts (s > 0) ou chapelle à pignon, grande lancette et oculus (s < 0), seconde tourelle, courtine basse,
    échauguette ; les flèches descendent en dents de scie vers le bord."""
    ch, cc, ca = c("chateau"), c("chateau_clair"), c("chateau_arete")
    # courtine contre la tour de porte
    y0 = _socle(cols, xt, 82)
    _bx(b, s, xt + 0.1, 82, y0, 70, -12.3, 8, ch, name="Courtine")
    x0, x1 = _sx(s, xt + 0.5, 81.5)
    _merlons(b, x0, x1, 70.4, -12.6, -10.6, larg=2.5, pas=4.5)
    _bx(b, s, xt + 0.3, 81.7, 69, 70.4, -12.6, -10.6, ca, name="Chaperon")
    with _face(b, "-z", -12.3):
        _lancette(b, s * 75.0, 56.0, 2.0, 8.0)
    # haute tourelle
    yt = 104.0 if s > 0 else 96.0
    y0 = _socle(cols, 82, 94)
    _tourelle(b, s, 82, 94, -17.3, -5, y0, yt, 28.0 if s > 0 else 24.0, fen=((62.0, 2.2, 10.0),),
              cote=(74.0, 1.8, 8.0) if s > 0 else None, oculus=(yt - 8.0, 1.8), h_tambour=7.0)
    with _face(b, "-z", -17.3):
        _banniere(b, s * 88.0, yt - 12.0, 4.0, 18.0, c("cramoisi") if s > 0 else c("violet_profond"))
    for u, sg in ((82.0, -1.0), (94.0, 1.0)):
        _corne(b, (s * (u + 0.4 * sg), yt - 2.5, -16.7), s * sg * 2.6, -0.5, L=2.6, ep=0.75)
    if s > 0:
        # grande salle : contreforts, trois lancettes, toit d'ardoise violette, pinacles sur le faîtage
        y0 = _socle(cols, 94, 124)
        _bx(b, s, 94, 124, y0, 64, -14.3, 8, ch, name="Salle")
        _toit(b, s, 94, 124, -14.3, 8, 64, 16.0)
        for u in (101.5, 109.0, 116.5):
            _bx(b, s, u - 0.9, u + 0.9, y0 + 0.3, 60, -16.0, -14.0, cc, name="Contrefort")
            xa, xb = _sx(s, u - 0.9, u + 0.9)
            b.wedge((xa, 60, -16.0), (xb, 63, -14.0), ca, down="-z", studs="top", name="Larmier")
        with _face(b, "-z", -14.3):
            for u in (105.25, 112.75, 120.25):
                _lancette(b, s * u, max(50.3, y0 + 8.3), 2.0, 8.0)
        for u in (100.0, 118.0):
            _pinacle(b, s * u, 78.0, -3.0, 1.8, 2.5, aiguille=6.0)
    else:
        # chapelle à pignon sur la façade : grande lancette, oculus cramoisi, pinacles aux rampants
        y0 = _socle(cols, 96, 116)
        _bx(b, s, 96, 116, y0, 72, -13.3, 7, ch, name="Chapelle")
        xa, xm, xb = s * 96, s * 106, s * 116
        lo, hi = sorted((xa, xm))
        b.wedge((lo, 72, -12.4), (hi, 89, 7.6), c("violet_profond"), down="+x" if s > 0 else "-x", studs="top",
                name="Toit")
        lo, hi = sorted((xm, xb))
        b.wedge((lo, 72, -12.4), (hi, 89, 7.6), shade(c("violet_profond"), 0.85), down="-x" if s > 0 else "+x",
                studs="top", name="Toit")
        lo, hi = sorted((s * 95.5, xm))
        b.wedge((lo, 71, -13.6), (hi, 91, -12.4), cc, down="+x" if s > 0 else "-x", name="Pignon")
        lo, hi = sorted((xm, s * 116.5))
        b.wedge((lo, 71, -13.6), (hi, 91, -12.4), cc, down="-x" if s > 0 else "+x", name="Pignon")
        for u in (95.0, 117.0):
            _bx(b, s, u - 1.0, u + 1.0, y0 + 0.3, 70, -15.0, -13.0, cc, name="Contrefort")
            _pinacle(b, s * u, 70, -14.0, 2.0, 3.0, aiguille=7.0)
        _pinacle(b, s * 106.0, 91.0, -13.0, 1.8, 2.0, aiguille=7.0)
        with _face(b, "-z", -13.3):
            _lancette(b, s * 106.0, max(50.3, y0 + 7.3), 3.4, 13.0)
        with _face(b, "-z", -13.6):
            _oculus(b, s * 106.0, 78.5, 2.4)
        y0 = _socle(cols, 116, 124)
        _bx(b, s, 116, 124, y0, 58, -10.3, 6, ch, name="Courtine")
        x0, x1 = _sx(s, 117.5, 123.5)
        _merlons(b, x0, x1, 58, -10.6, -8.6, larg=2.2, pas=4.0)
    # seconde tourelle
    yt = 88.0 if s > 0 else 80.0
    y0 = _socle(cols, 124, 134)
    _tourelle(b, s, 124, 134, -15.3, -5, y0, yt, 24.0 if s > 0 else 20.0, fen=((yt - 20.0, 1.8, 9.0),), h_tambour=6.0,
              fen_tambour=False)
    # courtine basse et échauguette
    y0 = _socle(cols, 134, 152)
    _bx(b, s, 134, 152, y0, 52, -10.3, 6, ch, name="Courtine")
    x0, x1 = _sx(s, 135, 151)
    _merlons(b, x0, x1, 52, -10.6, -8.6, larg=2.2, pas=4.0)
    with _face(b, "-z", -10.3):
        _archere(b, s * 143.0, 42.0, 5.0)
    yt = 66.0 if s > 0 else 62.0
    y0 = _socle(cols, 152, 160)
    _tourelle(b, s, 152, 160, -13.3, -5, y0, yt, 16.0, h_tambour=5.0, fen_tambour=False, pin=(0, 1),
              fen=((yt - 12.0, 1.4, 6.0),))


def chateau_demon(b, variant: int = 0, largeur: float = 478, profondeur: float = 50, ouverture: float = 100,
                  h_passage: float = 40) -> dict:
    """Château démoniaque gothique noir sur sa falaise (repère final, refBC3). Posé en (0, 0, -523) avec yaw = 180 :
    -Z local regarde les arrivants ; z local de -25 (façade) à +25 (revers, sortie). Porte : ouverture `ouverture`
    (|x| < 50), montants jusqu'à `h_passage`, arc brisé en gradins au-dessus (clé à 74) ; rien sous 40 au-dessus
    du passage."""
    rng = np.random.default_rng(4242 + 31 * variant)
    L2, D, xo, hp = largeur / 2, profondeur / 2, ouverture / 2, h_passage
    xt = xo + 18.0
    arc = _arc_brise(xo, hp, hp + 34.0, n=13)
    arc_dos = _arc_brise(xo, hp, hp + 34.0, n=6)
    YC = arc[-1][2] + 2.0
    with b.group("Falaise"):
        cols = _falaise_chateau(b, rng, L2, D, xt)
    with b.group("Porte"):
        _porte_chateau(b, rng, arc, arc_dos, xo, hp, D, YC)
    for s in (-1, 1):
        with b.group("TourPorte"):
            _tour_porte(b, rng, s, xo, xt, hp, D)
    with b.group("Tunnel"):
        _tunnel(b, xo, xt, hp, D, YC)
    with b.group("Donjon"):
        _donjon(b, D)
    for s in (-1, 1):
        with b.group("Aile"):
            _aile(b, rng, s, xt, D, cols[s])
    return {"emprise": (largeur, profondeur), "hauteur": 165}


# ---------------------------------------------------------------------------
# 2) Outils organiques : prismes, veines
# ---------------------------------------------------------------------------

def _cadre_y(d, roll: float = 0.0) -> np.ndarray:
    """Repère dont l'axe Y suit d, tourné de `roll` degrés autour de d."""
    d = _v(d) / float(np.linalg.norm(d))
    ref = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    X = np.cross(d, ref)
    X /= np.linalg.norm(X)
    Z = np.cross(X, d)
    R = np.column_stack([X, d, Z])
    return R @ rot_y(roll) if roll else R


def _prisme(b, p0, d, L, w, col, neon=False, roll=45.0, coupe=0.32, name="Cristal") -> None:
    """Prisme de cristal : fût carré de p0 le long de d, pointe taillée en biseau (un coin) ; 2 pièces."""
    R = _cadre_y(d, roll)
    d = R[:, 1]
    Lb, Lt = L * (1 - coupe), L * coupe
    kw = NEON if neon else DECO
    p0 = _v(p0)
    b.part("block", (w, Lb, w), p0 + d * Lb / 2, R, col, name=name, **kw)
    b.part("wedge", (w, Lt, w), p0 + d * (Lb + Lt / 2), R, col, name=name, **kw)


def _segment_veine(b, p, q, ep, tors, col, centre, veine=False, ext=None, name="Branche", **kw) -> None:
    """Segment organique (bloc tendu de p à q, section ep, torsion `tors`), avec en option une veine Neon violette
    collée sur la face la plus éloignée de `centre` (saillie 0,2)."""
    p, q = _v(p), _v(q)
    n, R = _repere(q - p)
    if tors:
        R = R @ rot_x(tors)
    e = 0.3 * ep if ext is None else ext
    b.part("block", (n + 2 * e, ep, ep), (p + q) / 2, R, col, name=name, **kw)
    if veine:
        m = (p + q) / 2
        out = m - _v(centre)
        out -= R[:, 0] * float(np.dot(out, R[:, 0]))
        cands = [(R[:, 1], 1), (-R[:, 1], 1), (R[:, 2], 2), (-R[:, 2], 2)]
        nrm, ax = max(cands, key=lambda t: float(np.dot(t[0], out)))
        size = [n * 0.8, 0.5, 0.5]
        size[ax] = 0.3
        b.part("block", tuple(size), m + nrm * (ep / 2 + 0.05), R, c("lueur_violette"), name="Veine", **NEON)


# ---------------------------------------------------------------------------
# 3) Arbre démoniaque
# ---------------------------------------------------------------------------

def arbre_demon(b, variant: int = 0, hauteur: float = 150) -> dict:
    """Arbre noir colossal du royaume démoniaque : tronc de quatre brins torsadés (Ø ≈ 24 au pied, ≈ 8 vers 84), cœur
    cramoisi lumineux dans une loge du tronc (côté couloir, vers 20), six maîtresses branches en griffes et une
    flèche centrale jusqu'à `hauteur`, rameaux crochus, cosses cramoisies pendues, rares touffes violettes, sept
    racines en arcs qui replongent dans le sol (rayon ≤ 34), veines violettes (Neon) le long du tronc et des
    branches. Avant vers -Z local (posé yaw 90 à droite du couloir)."""
    rng = np.random.default_rng(777 + 13 * variant)
    H = float(hauteur)
    k = H / 150.0
    ra, rc, ob = c("racine"), c("racine_claire"), c("obsidienne")
    Ht = 84.0 * k                               # sommet du tronc torsadé
    tw = 170.0                                  # torsion des brins (degrés, du pied au sommet du tronc)
    yh = 20.0 * k                               # hauteur du cœur
    # loge du cœur face au couloir (-Z) : on cale la torsion pour qu'un creux entre deux brins y soit en yh
    a0 = -135.0 - tw * yh / Ht + 90.0 * (variant % 2)
    N = 7
    centre_axe = np.array([0.0, 0.0, 0.0])

    def brin(kb, i):
        t = i / N
        r = (7.5 - 5.5 * t) * k
        a = math.radians(a0 + 90.0 * kb + tw * t)
        return np.array([r * math.cos(a), Ht * t - 0.6 * (i == 0), r * math.sin(a)])

    with b.group("Tronc"):
        for kb in range(4):
            for i in range(N):
                p, q = brin(kb, i), brin(kb, i + 1)
                ep = (9.6 - 5.4 * (i + 0.5) / N) * k
                col = (ra, rc, ra, ob)[kb]
                ax = np.array([0.0, (p[1] + q[1]) / 2, 0.0])
                _segment_veine(b, p, q, ep, 45.0 * i + 20 * kb, col, ax, veine=(i + kb) % 3 == 0 and i < 6,
                               ext=0.35 * ep, name="Tronc")
        # cœur cramoisi dans sa loge
        af = math.radians(-90.0)
        rh = 6.4 * k
        b.ball((rh * math.cos(af) * 0.95, yh, rh * math.sin(af) * 0.95), 4.0 * k, c("cramoisi_fonce"), name="Loge")
        b.ball((rh * math.cos(af) * 1.12, yh + 0.2, rh * math.sin(af) * 1.12), 3.0 * k, c("lueur_cramoisie"), name="Coeur",
               **NEON)
        b.ball((rh * math.cos(af) * 1.3, yh + 2.9 * k, rh * math.sin(af) * 1.3), 1.1 * k, c("cramoisi"), name="Coeur",
               **DECO)
    with b.group("Racines"):
        n_r = 7
        for r_ in range(n_r):
            psi = math.radians(a0 + 25 + 360.0 * r_ / n_r + float(rng.uniform(-12, 12)))
            dr = float(rng.uniform(-0.12, 0.12))
            reach = float(rng.uniform(26, 33)) * k
            prof = [(5.5, 4.0), (12.0, 9.5 + float(rng.uniform(-1.5, 2.5))), (19.0, 8.0), (25.5, 3.5), (reach / k, -1.2)]
            pts = []
            for j, (rr, yy) in enumerate(prof):
                ps = psi + dr * j
                pts.append(np.array([rr * k * math.cos(ps), yy * k, rr * k * math.sin(ps)]))
            for j in range(4):
                ep = (5.0, 4.0, 3.2, 2.4)[j] * k
                _segment_veine(b, pts[j], pts[j + 1], ep, 30.0 * j, (ra, rc)[j % 2], centre_axe,
                               veine=(j == 1 and r_ % 2 == 0), name="Racine")
            e = pts[-1]
            b.boxc((e[0], 0.15, e[2]), (3.4 * k, 0.6, 3.0 * k), c("brulis"), yaw=math.degrees(psi), studs="top",
                   name="Terre", **DECO)
    with b.group("Branches"):
        pointes = []
        # flèche centrale jusqu'à H
        p = np.array([0.0, Ht - 4.0 * k, 0.0])
        cible = [(1.5, Ht + 18 * k), (-1.5, Ht + 36 * k), (2.0, H - 22 * k), (0.5, H - 8 * k), (-1.0, H)]
        for j, (dx, yy) in enumerate(cible):
            q = np.array([dx * k, yy, -0.8 * dx * k])
            _segment_veine(b, p, q, (5.0, 3.9, 2.9, 2.0, 1.2)[j] * k, 25.0 * j, (rc, ra)[j % 2], centre_axe,
                           veine=j in (0, 2), name="Fleche")
            p = q
        pointes.append(p)
        for sg in (-1, 1):                           # deux crochets au sommet
            a = cible_pt = p
            for m, (L3, el3) in enumerate(((4.0, 20), (3.2, -35))):
                ph3 = math.radians(150 + 70 * sg)
                d3 = np.array([math.cos(ph3) * math.cos(math.radians(el3)), math.sin(math.radians(el3)),
                               math.sin(ph3) * math.cos(math.radians(el3))])
                q3 = a + d3 * L3 * k
                _poutre(b, a, q3, (1.0 - 0.3 * m) * k, ob, ext=0.25, name="Griffe", **FIN)
                a = q3
        # maîtresses branches en griffes, jamais vers le château (+x local) : de 75° à 285° autour de l'axe
        angles = [75.0 + 35.0 * i + float(rng.uniform(-8, 8)) for i in range(7)]
        hauts_b = (58, 82, 66, 90, 62, 86, 74)
        for nb, phd in enumerate(angles):
            phi = math.radians(phd)
            haute = nb % 2 == 1
            els = (62, 48, 32, 12, -24) if haute else (48, 36, 22, 4, -30)
            Ls = (20, 17, 14, 11, 8) if haute else (17, 14.5, 12, 9.5, 7)
            eps = (6.4, 5.1, 3.9, 2.9, 1.9)
            yb = hauts_b[nb] * k
            rt = (7.5 - 5.5 * min(1.0, yb / Ht)) * k
            p = np.array([rt * 0.6 * math.cos(phi), yb, rt * 0.6 * math.sin(phi)])
            ph = phi
            pod = None
            for j in range(5):
                ph += math.radians(float(rng.uniform(-9, 9)))
                el = math.radians(els[j] + float(rng.uniform(-5, 5)))
                d = np.array([math.cos(ph) * math.cos(el), math.sin(el), math.sin(ph) * math.cos(el)])
                q = p + d * Ls[j] * k
                rq = math.hypot(q[0], q[2])
                if rq > 49.0 * k:                    # houppier dans un rayon de 55 (griffes comprises)
                    q[0] *= 49.0 * k / rq
                    q[2] *= 49.0 * k / rq
                _segment_veine(b, p, q, eps[j] * k, 35.0 * j, (ra, rc)[(j + nb) % 2], centre_axe,
                               veine=(j == 1) or (j == 0 and nb % 3 == 0), name="Branche")
                if j in (1, 2, 3) and not (j == 3 and nb % 2):          # rameaux secondaires en griffes
                    ps_ = q
                    ph2 = ph + math.radians((44.0 if (j + nb) % 2 else -44.0) + float(rng.uniform(-10, 10)))
                    for m, (L2, el2, e2) in enumerate(((9.0, 42, 2.6), (7.0, 16, 1.8), (5.0, -26, 1.1))):
                        if j == 3 and m == 2:
                            break
                        d2 = np.array([math.cos(ph2) * math.cos(math.radians(el2)), math.sin(math.radians(el2)),
                                       math.sin(ph2) * math.cos(math.radians(el2))])
                        q2 = ps_ + d2 * L2 * k * (0.8 if j == 3 else 1.0)
                        _segment_veine(b, ps_, q2, e2 * k, 20.0 * m, rc if m % 2 else ra, centre_axe,
                                       name="Rameau", **DECO)
                        ps_ = q2
                        ph2 += math.radians(12.0 if (j + nb) % 2 else -12.0)
                    pointes.append(ps_)
                if j == 3:
                    pod = q
                p = q
            # griffe : trois doigts crochus au bout
            for sg in (-1, 0, 1):
                ph3 = ph + sg * math.radians(34)
                a = p
                for m, (L3, el3) in enumerate(((4.2, 12 + 10 * (sg == 0)), (3.4, -42))):
                    d3 = np.array([math.cos(ph3) * math.cos(math.radians(el3)), math.sin(math.radians(el3)),
                                   math.sin(ph3) * math.cos(math.radians(el3))])
                    q3 = a + d3 * L3 * k
                    _poutre(b, a, q3, (1.2 - 0.4 * m) * k, ob, ext=0.25, name="Griffe", **FIN)
                    a = q3
            pointes.append(p)
            # cosse cramoisie pendue sous la branche (tige + boule)
            if pod is not None and nb % 3 != 1:
                b.box((pod[0] - 0.2, pod[1] - 4.6 * k, pod[2] - 0.2), (pod[0] + 0.2, pod[1] - 0.8, pod[2] + 0.2), ra,
                      name="Tige", **FIN)
                b.ball((pod[0], pod[1] - 5.6 * k, pod[2]), 1.4 * k, c("lueur_cramoisie"), name="Cosse", **NEON)
    return {"emprise": (68, 68), "hauteur": H}


# ---------------------------------------------------------------------------
# 4) Îlots flottants enchaînés
# ---------------------------------------------------------------------------

def _arbre_mort_mini(b, rng, x, y, z, h) -> None:
    """Petit arbre mort (6 pièces) : tronc coudé, trois branches nues."""
    col, cl = c("bois_mort"), c("bois_mort_clair")
    p0, p1, p2 = _v((x, y - 0.3, z)), _v((x + 0.4, y + 0.5 * h, z + 0.2)), _v((x - 0.3, y + 0.85 * h, z - 0.3))
    _poutre(b, p0, p1, 0.9, col, ext=0.2, name="Tronc")
    _poutre(b, p1, p2, 0.65, col, ext=0.15, name="Tronc", **DECO)
    for i, a in enumerate((20.0, 140.0, 260.0)):
        base = p0 + (p2 - p0) * (0.55 + 0.18 * i)
        aa = math.radians(a + float(rng.uniform(-20, 20)))
        L = h * (0.45 - 0.07 * i)
        q = base + _v((L * math.cos(aa), L * 0.55, L * math.sin(aa)))
        _poutre(b, base, q, 0.4, cl if i % 2 else col, ext=0.1, name="Branche", **FIN)
    b.boxc((x + 0.2, y + 0.2, z), (1.6, 0.4, 1.4), c("racine"), yaw=30, name="Souche", **DECO)


def ilot_flottant(b, variant: int = 0, taille: float = 14, ancres=()) -> dict:
    """Îlot de roche noire qui flotte par magie (origine au centre du dessus) : dessus presque plat à studs, cône
    renversé en gradins tournés jusqu'à une pointe, cristaux violets pendus dessous, décor selon la variante (v0 arbre
    mort, v1 colonne brisée, v2 petit obélisque à glyphe, v3 grappe de cristaux). Chaque ancre (décalage aligné sur le
    monde vers un point du sol) reçoit un anneau sous le bord, une chaîne tendue et un ancrage de pierre noire au sol."""
    v = variant % 4
    rng = np.random.default_rng(311 + 17 * v)
    t = float(taille)
    rx, rz = t / 2, 0.4 * t
    dessus = (c("herbe_grise"), c("cendre"), c("roche_noire"), c("cendre_fonce"))[v]
    with b.group("Ilot"):
        b.box((-rx, -1.4, -rz), (rx, 0, rz), dessus, studs="top", name="Dessus")
        b.boxc((0.06 * t, -1.0, -0.05 * t), (0.7 * t, 1.6, 0.56 * t), roche(rng), yaw=32, studs="top", name="Rebord")
        y = -1.4
        n = 5
        depth = 0.8 * t
        for i in range(n):
            f = 0.94 - 0.17 * i
            hh = depth / n * (1.15 - 0.08 * i)
            yaw = (18.0 if i % 2 else -14.0) + float(rng.uniform(-8, 8))
            b.boxc((0.04 * t * (i % 2), y - hh / 2, -0.03 * t * (i % 2)), (t * f, hh, 0.8 * t * f), roche(rng), yaw=yaw,
                   name="Roche")
            y -= hh
        s = 0.16 * t
        b.part("block", (s, s, s), (0, y - 0.3 * s, 0), rot_x(45) @ rot_z(35.26), c("basalte"), name="Pointe")
        # cristaux pendus sous la roche
        for i in range(3 if t >= 13 else 2):
            a = math.radians(40 + 120 * i + float(rng.uniform(-20, 20)))
            r = 0.24 * t
            p0 = _v((r * math.cos(a), -1.4 - depth * (0.2 + 0.15 * i), 0.8 * r * math.sin(a)))
            d = _v((0.45 * math.cos(a), -1.0, 0.45 * math.sin(a)))
            _prisme(b, p0, d, (0.46 - 0.07 * i) * t, (0.13 - 0.015 * i) * t, c("cristal") if i != 1 else c("cristal_fonce"),
                    neon=i != 1)
        for i in range(2):
            a = math.radians(200 + 110 * i + 40 * v)
            b.boxc((0.32 * t * math.cos(a), 0.45, 0.26 * t * math.sin(a)), (1.6 - 0.4 * i, 0.9, 1.3 - 0.3 * i),
                   vary("basalte_clair", rng, 0.08), yaw=float(rng.uniform(0, 90)), studs="top", name="Pierre")
        b.boxc((-0.05 * t, 0.06, 0.18 * t), (0.34 * t, 0.12, 0.2 * t), c("mousse") if v != 2 else c("brulis"), yaw=-12,
               name="Mousse", **FIN)
        # décor du dessus
        if v == 0:
            _arbre_mort_mini(b, rng, -0.2 * t, 0.0, 0.05 * t, 0.55 * t)
        elif v == 1:
            b.cyl((0.18 * t, 3.2, 0.05 * t), 1.5, 6.4, c("chateau_clair"), name="Colonne")
            b.box((0.18 * t - 1.9, 6.4, 0.05 * t - 1.9), (0.18 * t + 1.9, 7.4, 0.05 * t + 1.9), c("chateau_arete"),
                  studs="top", name="Chapiteau")
            b.part("cyl", (4.0, 3.0, 3.0), (-0.22 * t, 1.3, -0.08 * t), rot_y(35), c("chateau_clair"), name="Tambour")
        elif v == 2:
            b.box((-1.2, 0, -1.2), (1.2, 0.8, 1.2), c("basalte_clair"), studs="top", name="Socle")
            b.box((-0.7, 0.8, -0.7), (0.7, 5.6, 0.7), c("obsidienne"), name="Obelisque")
            b.wedge((-0.7, 5.6, -0.7), (0.7, 6.8, 0.7), c("obsidienne"), down="-z", name="Obelisque")
            b.box((-0.3, 3.0, -0.8), (0.3, 4.2, -0.7), c("lueur_violette"), name="Glyphe", **NEON)
        else:
            for i in range(2):
                a = math.radians(30 + 160 * i)
                _prisme(b, (0.6 * math.cos(a), -0.3, 0.6 * math.sin(a)), (0.3 * math.cos(a), 1.0, 0.3 * math.sin(a)),
                        (3.8 - 1.2 * i), (1.1 - 0.25 * i), c("cristal") if i == 0 else c("cristal_fonce"), neon=i == 0)
    with b.group("Chaines"):
        fer = c("fer_fonce")
        for (dx, dy, dz) in ancres:
            h = math.hypot(dx, dz) or 1.0
            ux, uz = dx / h, dz / h
            E = _v((ux * rx * 0.78, -2.2, uz * rz * 0.78))
            Rr = _cadre_y((-uz, 0.0, ux))
            b.part("cyl", (1.6, 0.35, 0.35), E + _v((0, 0.4, 0)), Rr @ rot_z(90), fer, name="Crochet", **FIN)
            b.part("cyl", (0.35, 1.6, 1.6), E - _v((0, 0.5, 0)), _repere((ux, 0.0, uz))[1], fer, name="Anneau", **FIN)
            A = _v((dx, dy + 1.5, dz))
            b.box((dx - 1.25, dy, dz - 1.25), (dx + 1.25, dy + 1.5, dz + 1.25), c("basalte"), studs="top",
                  name="Ancrage")
            b.part("cyl", (0.35, 1.4, 1.4), A + _v((0, 0.55, 0)), _repere((ux, 0.0, uz))[1], fer, name="Anneau", **FIN)
            gx = dx - ux * 1.3
            gz = dz - uz * 1.3
            b.boxc((gx, dy + 0.75, gz), (1.2, 0.5, 0.2), c("lueur_violette"), yaw=-math.degrees(math.atan2(uz, ux)) + 90,
                   name="Glyphe", **NEON)
            mobilier.chaine(b, E - _v((0, 1.2, 0)), A + _v((0, 1.2, 0)), maillon=3.0, epaisseur=0.4)
    return {"emprise": (t, t), "hauteur": 0.8 * t}


# ---------------------------------------------------------------------------
# 5) Falaises noires latérales
# ---------------------------------------------------------------------------

def falaise(b, variant: int = 0, longueur: float = 60, profondeur: float = 50, hauteur: float = 48) -> dict:
    """Falaise noire le long de X local, face avant (z = -profondeur/2) vers le couloir : colonnes de basalte en
    trois terrasses qui montent vers l'arrière jusqu'à `hauteur`, crête irrégulière (pics et encoches), corniches à
    studs, pans inclinés, 2-4 grappes de cristaux violets (Neon), racines noires, un arbre mort sur une corniche,
    une grotte à lueur violette (v1, v3). Extrémités un peu plus basses (raccord avec les segments voisins)."""
    v = variant % 4
    rng = np.random.default_rng(907 + 41 * v + int(longueur) + int(hauteur))
    L, P, H = float(longueur), float(profondeur), float(hauteur)
    zf0 = -P / 2
    cols = []
    x = -L / 2
    while x < L / 2 - 0.5:
        x1 = min(L / 2, x + float(rng.uniform(5.5, 9.5)))
        if L / 2 - x1 < 3.5:
            x1 = L / 2
        cols.append((x, x1))
        x = x1
    info = []
    with b.group("Roche"):
        for i, (x0, x1) in enumerate(cols):
            xm = (x0 + x1) / 2
            e = abs(xm) / (L / 2)
            hc = H * (0.66 + 0.34 * float(rng.random())) * (1 - 0.2 * e ** 3)
            if rng.random() < 0.3:
                hc *= 0.78                                     # encoche
            z0 = zf0 + float(rng.choice((0.0, 0.5, 1.0, 1.5, 2.0, 3.0)))
            h1, h2 = hc * float(rng.uniform(0.2, 0.42)), hc * float(rng.uniform(0.5, 0.8))
            z1 = z0 + P * float(rng.uniform(0.05, 0.22))
            z2 = z1 + P * float(rng.uniform(0.06, 0.24))
            dos = (P / 2, P / 2 - float(rng.choice((0.0, 2.0, 4.0))), P / 2 - float(rng.choice((4.0, 6.0, 9.0))))
            for k_, (ya, yb, z) in enumerate(((0, h1, z0), (h1, h2, z1), (h2, hc, z2))):
                col = roche(rng) if rng.random() < 0.82 else vary("basalte_clair", rng, 0.08)
                b.box((x0, ya, z), (x1, yb, max(dos[k_], z + 4.0)), col, studs="top", name="Roche")
            r = rng.random()
            if r < 0.3:
                b.wedge((x0, h1, z0), (x1, h1 + float(rng.uniform(2.5, 5)), z1), vary("basalte_clair", rng, 0.08),
                        down="-z", studs="top", name="Pan")
            elif r < 0.55:
                b.box((x0 + 0.3, h2 - 0.8, z1 - 0.4), (x1 - 0.3, h2 + 0.4, z1 + 1.2), vary("basalte_clair", rng, 0.06),
                      studs="top", name="Strate")
            if rng.random() < 0.7 and i not in (0, len(cols) - 1):
                for kk in range(1 if rng.random() < 0.55 else 2):
                    w = float(rng.uniform(3.5, 6.0)) * (0.65 if kk else 1.0)
                    hp_ = min(float(rng.uniform(6, 14)) * (0.6 if kk else 1.0), max(2.0, 1.1 * H - hc - 1.0 - 2.0 * kk))
                    zc = min(P / 2 - w, z2 + float(rng.uniform(2, 14)))
                    b.part("block", (w, hp_ + 2, w * 0.8), (xm + float(rng.uniform(-1.5, 1.5)), hc + hp_ / 2 - 1 + kk * 2.0,
                                                           zc), rot_y(float(rng.uniform(0, 90))) @ rot_z(float(rng.uniform(-14, 14))),
                           roche(rng), studs="top", name="Pic")
            if rng.random() < 0.3:
                w = float(rng.uniform(2.2, 3.4))
                xb_ = min(max(xm + float(rng.uniform(-1.5, 1.5)), x0 + 0.75 * w), x1 - 0.75 * w)
                b.part("block", (w, 0.8 * w, w), (xb_, 0.3 * w, max(z0 + 0.4, zf0 + 0.75 * w)),
                       rot_y(float(rng.uniform(0, 90))) @ rot_x(float(rng.uniform(-12, 12))), vary("basalte_clair", rng, 0.08),
                       studs="top", name="Bloc")
            info.append((x0, x1, h1, h2, hc, z0, z1, z2))
    with b.group("Cristaux"):
        n_g = 2 + v % 3
        idx = sorted(1 + rng.choice(len(cols) - 2, size=min(n_g, len(cols) - 2), replace=False))
        for j in idx:
            x0, x1, h1, h2, hc, z0, z1, z2 = info[j]
            _grappe_corniche(b, rng, (x0 + x1) / 2, h1, (z0 + z1) / 2, 0.9 + 0.2 * (j % 2), zmin_abs=zf0 + 0.3)
    with b.group("Racines"):
        for j in (1, len(cols) - 2):
            if j < 0 or j >= len(cols):
                continue
            x0, x1, h1, h2, hc, z0, z1, z2 = info[j]
            xm = (x0 + x1) / 2
            sg = -1.0 if xm > 0 else 1.0
            pts = [(xm, h2 + 0.5, z2 + 3.0), (xm + 1.5 * sg, h1 + 1.0, max(z1 + 0.5, zf0 + 2.0)),
                   (xm + 3.0 * sg, 1.0, max(z0 + 0.6, zf0 + 1.8)), (xm + 5.5 * sg, -0.4, max(zf0 + 1.4, z0 - 0.4))]
            for m in range(3):
                _poutre(b, pts[m], pts[m + 1], (2.4, 1.8, 1.3)[m], c(("racine", "racine_claire")[m % 2]), ext=0.4,
                        tors=20.0 * m, name="Racine", **(DECO if m == 2 else {}))
    with b.group("Arbre"):
        j = int(len(cols) * (0.3 if v % 2 else 0.7))
        x0, x1, h1, h2, hc, z0, z1, z2 = info[j]
        with b.at(((x0 + x1) / 2, h2, (z1 + z2) / 2 + 0.5), yaw=float(rng.uniform(0, 360))):
            mobilier.arbre_mort(b, variant=1 if v % 2 else 0, hauteur=min(10.0, 0.25 * H))
    cands = [j for j in range(1, len(cols) - 1) if info[j][5] >= zf0 + 0.95 and info[j][1] - info[j][0] >= 6.0]
    if v in (1, 3) and cands:
        with b.group("Grotte"):
            j = min(cands, key=lambda j: abs(info[j][0] + info[j][1]))
            x0, x1, h1, h2, hc, z0, z1, z2 = info[j]
            xm = (x0 + x1) / 2
            w = min(4.5, x1 - x0 - 1.0)
            hg = min(h1 - 1.0, 7.0)
            b.box((xm - w / 2 - 0.6, -0.2, z0 - 0.3), (xm + w / 2 + 0.6, hg + 0.6, z0 + 0.2), c("obsidienne"), name="Grotte")
            b.box((xm - w / 2, -0.1, z0 - 0.5), (xm + w / 2, hg, z0 - 0.3), c("violet_profond"), name="Grotte", **DECO)
            b.box((xm - w / 2 + 0.8, 0.2, z0 - 0.7), (xm + w / 2 - 0.8, hg - 1.2, z0 - 0.5), c("lueur_violette"),
                  name="Lueur", **NEON)
    return {"emprise": (longueur, profondeur), "hauteur": hauteur}


# ---------------------------------------------------------------------------
# 6) Obélisques, racines géantes, cristaux de la place rituelle
# ---------------------------------------------------------------------------

GLYPHES = ((0.35, 1.0, 0.0), (0.9, 0.35, 0.0), (0.55, 0.55, 45.0), (0.35, 0.7, 0.0), (0.8, 0.3, 0.0))


def obelisque(b, variant: int = 0, hauteur: float = 16) -> dict:
    """Obélisque noir : socle à deux gradins (5 × 5), fût effilé en trois tronçons (2,2 → 1,4), bande de glyphes
    abstraits lumineux (barres, points, losanges ; aucune lettre ni étoile), arête claire ébréchée ; coupe de fer à
    flammes violettes (v0, v3) ou cramoisies (v1, fissure cramoisie), ou pyramidion sombre à pointe violette (v2)."""
    v = variant % 4
    H = float(hauteur)
    lueur = c("lueur_cramoisie") if v == 1 else c("lueur_violette")
    with b.group("Obelisque"):
        b.box((-2.5, 0, -2.5), (2.5, 1.0, 2.5), c("basalte"), studs="top", name="Socle")
        b.box((-1.9, 1.0, -1.9), (1.9, 2.0, 1.9), c("chateau_arete"), studs="top", name="Socle")
        ys = (2.0, 2.0 + 0.36 * (H - 2.5), 2.0 + 0.68 * (H - 2.5), H - 0.5)
        ws = (2.2, 1.85, 1.5)
        cols = (c("obsidienne"), c("chateau"), c("obsidienne"))
        for i in range(3):
            w = ws[i] / 2
            b.box((-w, ys[i], -w), (w, ys[i + 1], w), cols[i], name="Fut")
            if i:
                b.box((-w - 0.15, ys[i] - 0.05, -w - 0.15), (w + 0.15, ys[i] + 0.35, w + 0.15), c("chateau_arete"),
                      name="Cordon", **DECO)
        # glyphes sur la face avant du tronçon médian
        w = ws[1] / 2
        for j, (gw, gh, rot) in enumerate(GLYPHES[v % 3: v % 3 + 3]):
            y = ys[1] + 0.9 + j * 1.25
            b.part("block", (gw, gh, 0.25), (0, y, -w - 0.05), rot_z(rot) if rot else None, lueur, name="Glyphe", **NEON)
        # arête ébréchée (ou fissure cramoisie)
        w0 = ws[0] / 2
        if v == 1:
            b.box((w0 - 0.05, ys[0] + 1.5, -0.12), (w0 + 0.1, ys[0] + 4.0, 0.12), c("lueur_cramoisie"), name="Fissure",
                  **NEON)
            b.box((w0 - 0.05, ys[0] + 3.8, 0.0), (w0 + 0.1, ys[0] + 5.6, 0.24), c("lueur_cramoisie"), name="Fissure",
                  **NEON)
        else:
            b.box((-w0 - 0.1, ys[0] + 1.0, -w0 - 0.1), (-w0 + 0.4, ys[0] + 3.2, -w0 + 0.4), c("chateau_arete"),
                  name="Eclat", **DECO)
        top = ys[3]
        if v == 2:
            b.box((-0.85, top, -0.85), (0.85, top + 0.4, 0.85), c("chateau_arete"), name="Corniche")
            _fleche(b, 0.0, top + 0.4, 0.0, 2.0, 2.6, c("obsidienne"), ep=0.3, rot45=False, studs=False, name="Pyramidion")
            b.ball((0, top + 3.2, 0), 0.35, c("lueur_violette"), name="Pointe", **NEON)
        else:
            fer = c("fer_fonce")
            b.box((-0.6, top, -0.6), (0.6, top + 0.6, 0.6), fer, name="Pied")
            b.box((-1.3, top + 0.6, -1.3), (1.3, top + 1.3, 1.3), fer, name="Coupe")
            for sx in (-1, 1):
                b.box((sx * 1.3 - 0.15, top + 1.3, -1.3), (sx * 1.3 + 0.15, top + 1.8, 1.3), fer, name="Rebord", **FIN)
            ext, coeur = (c("feu_cramoisi"), c("feu")) if v == 1 else (c("feu_violet"), c("lueur_violette_pale"))
            b.boxc((0, top + 2.1, 0), (1.5, 1.6, 1.5), ext, yaw=45, name="Flamme", **NEON)
            b.boxc((0, top + 3.0, 0), (0.7, 2.2, 0.7), coeur, yaw=20, name="Flamme", **NEON)
    return {"emprise": (5, 5), "hauteur": H + 3}


def racine_geante(b, variant: int = 0, longueur: float = 24, hauteur: float = 10) -> dict:
    """Racine démoniaque noire qui sort du sol en un ou deux arcs le long de X local (section 3 → 1,5), épines,
    veine violette (Neon) sur le dessus, terre retournée aux deux bouts."""
    v = variant % 4
    rng = np.random.default_rng(1201 + 7 * v)
    L, Hh = float(longueur), float(hauteur)
    a, z_ = L / 2 - 1.7, 0.0
    arcs = {0: [(-a, 0.42 * L, Hh)], 1: [(-a, 0.06 * L, Hh), (-0.06 * L, a, 0.55 * Hh)],
            2: [(-0.42 * L, a, 0.85 * Hh)], 3: [(-a, 0.22 * L, Hh), (0.12 * L, a, 0.45 * Hh)]}[v]
    ra, rc = c("racine"), c("racine_claire")
    with b.group("Racine"):
        bouts = []
        for ia, (xa, xb, h) in enumerate(arcs):
            n = 5 if ia == 0 else 4
            pts = []
            for i in range(n + 1):
                t = i / n
                pts.append(_v((xa + (xb - xa) * t, h * math.sin(math.pi * t) - 0.8 * (1 - math.sin(math.pi * t)),
                               1.2 * math.sin(2.3 * math.pi * t + v) * (1 if ia == 0 else -0.6))))
            for i in range(n):
                t = (i + 0.5) / n
                ep = (3.0 - 1.5 * t) * (1.0 if ia == 0 else 0.8)
                _segment_veine(b, pts[i], pts[i + 1], ep, 30.0 * i, (ra, rc)[i % 2], _v((0, -20, 0)),
                               veine=(ia == 0 and i == 2), ext=0.3 * ep, name="Racine")
                if i in (1, 3) or (ia == 1 and i == 1):
                    m = (pts[i] + pts[i + 1]) / 2
                    a = float(rng.uniform(-30, 30))
                    _poutre(b, m + _v((0, ep * 0.35, 0)), m + _v((0.8 * math.sin(math.radians(a)), ep * 0.5 + 1.6,
                                                                  0.6 * math.cos(math.radians(a)))),
                            0.45, c("epine"), name="Epine", **FIN)
            bouts += [pts[0], pts[-1]]
        for e in bouts[:2] + bouts[-1:]:
            b.boxc((e[0], 0.15, e[2]), (3.2, 0.6, 2.8), c("brulis"), yaw=float(rng.uniform(0, 90)), studs="top",
                   name="Terre", **DECO)
            b.part("block", (1.4, 0.8, 1.2), (e[0] + 0.6, 0.45, e[2] - 0.4), rot_y(float(rng.uniform(0, 90))) @ rot_z(20),
                   c("terre_fonce"), name="Motte", **DECO)
    return {"emprise": (longueur, 6), "hauteur": hauteur}


def cristaux(b, variant: int = 0, taille: float = 6) -> dict:
    """Grappe de cristaux violets sur un socle de roche noire : cinq prismes inclinés taillés en biseau, deux ou
    trois en `cristal` Neon, les autres en `cristal_fonce` ; hauteur ≈ 1,2 × taille."""
    v = variant % 4
    rng = np.random.default_rng(1409 + 11 * v)
    t = float(taille)
    with b.group("Cristaux"):
        b.boxc((0, 0.35, 0), (0.8 * t, 0.7, 0.62 * t), roche(rng), yaw=float(rng.uniform(0, 90)), studs="top",
               name="Socle")
        b.part("block", (0.5 * t, 0.6, 0.42 * t), (0.18 * t, 0.75, 0.08 * t), rot_y(float(rng.uniform(0, 90))) @ rot_z(8),
               c("basalte_clair"), studs="top", name="Socle")
        lit = {0: (0, 2), 1: (0, 1, 3), 2: (0, 3), 3: (0, 2, 4)}[v]
        for i in range(5):
            if i == 0:
                p0, d, L, w = (0.0, 0.5, 0.0), (0.08, 1.0, -0.05), 1.15 * t, 0.26 * t
            else:
                a = math.radians(30 + 90 * i + float(rng.uniform(-20, 20)))
                r = 0.16 * t
                tilt = float(rng.uniform(0.35, 0.8))
                p0 = (r * math.cos(a), 0.5, r * math.sin(a))
                d = (tilt * math.cos(a), 1.0, tilt * math.sin(a))
                L, w = t * float(rng.uniform(0.45, 0.75)), t * float(rng.uniform(0.13, 0.19))
            _prisme(b, p0, d, L, w, c("cristal") if i in lit else c("cristal_fonce"), neon=i in lit,
                    roll=float(rng.uniform(0, 90)))
    return {"emprise": (taille, taille), "hauteur": 1.2 * taille}
