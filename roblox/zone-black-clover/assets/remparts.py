"""Remparts de la zone Black Clover : porte d'entrée et enceinte (refBC2), ruines du champ de bataille des mages
(refBC4), aqueduc ruiné qui enjambe le couloir (refBC3).

Fonctions publiques (signatures appelées par `zone.py`, fiches dans SPECS.md) :
- `porte_entree` : deux tours rondes massives (talus, assises, mâchicoulis, toit conique très pointu d'ardoise
  violette, épi doré) de part et d'autre du couloir, vantaux de bois cerclés de fer ouverts contre le couloir,
  piliers de liaison avec l'enceinte ;
- `mur_enceinte` : segment d'enceinte crénelée (assises de 4, cordon, chemin de ronde) ; variantes : sobre,
  lierre et archères, brèche, échauguette ;
- `ruine_tour`, `ruine_mur`, `arche_effondree` : ruines calcinées du champ de bataille ;
- `aqueduc` : aqueduc ruiné et sombre en travers du couloir (arche centrale de 94, dessous ≥ 36), grande brèche
  à droite avec cascade, travée effondrée à gauche, parapets édentés, travées affaissées.

Repère : origine au centre de l'emprise au sol, avant vers -Z local. Pierre gris-violet en assises de 3-4 tons,
ruines plus sombres (`pierre_noire`, `pierre_ombre`, `bois_brule`), ardoise violette, lierre ; lueurs Neon avec
mesure (archères et fenêtres à la bougie, cicatrices magiques violettes). Aucun emblème, aucun trèfle, aucune
croix : bannières unies (`mobilier.banniere_murale`), maçonnerie nue.
"""

from __future__ import annotations

import math

import numpy as np

from assets import mobilier
from kit import rot_x, rot_y, rot_z, shade
from palette import c, vary

DECO = dict(collide=False)
FIN = dict(collide=False, shadow=False)
NEON = dict(material="Neon", collide=False, shadow=False)

PIERRES = ("pierre", "pierre_claire", "pierre_fonce")
SOMBRES = ("pierre_fonce", "pierre_noire", "pierre_ombre", "pierre")
MOTIF_TOIT = ("ardoise_fonce", "ardoise_fonce", "ardoise", "ardoise", "ardoise_claire", "ardoise", "ardoise",
              "ardoise_fonce", "ardoise", "ardoise_claire")


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

def _rng(b, cle: int, variant: int, *extra, lieu: bool = True) -> np.random.Generator:
    """Aléatoire reproductible : même asset, même variante, même pose → mêmes pierres."""
    graine = [cle, variant % 97]
    if lieu:
        graine += [int(round(float(v) * 4)) + 100000 for v in b.to_world((0, 0, 0))]
    graine += [int(round(float(e) * 8)) + 100000 for e in extra]
    return np.random.default_rng(graine)


def _ton(rng, noms=PIERRES, poids=None, amount: float = 0.05) -> tuple:
    if poids is None:
        nom = noms[int(rng.integers(len(noms)))]
    else:
        p = np.asarray(poids, float)
        nom = noms[int(rng.choice(len(noms), p=p / p.sum()))]
    return vary(nom, rng, amount)


def _repere(d):
    """Longueur et matrice dont l'axe X suit d (Y aussi vertical que possible)."""
    d = np.asarray(d, float)
    n = float(np.linalg.norm(d))
    x = d / n
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return n, np.column_stack([x, y, z])


def _poutre(b, a, bb, ep, col, name: str = "Poutre", ep_z: float | None = None, **kw):
    """Bloc de section ep × ep_z tendu de a à bb."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    n, R = _repere(bb - a)
    return b.part("block", (n, ep, ep if ep_z is None else ep_z), (a + bb) / 2, R, col, name=name, **kw)


def _radial(b, cx: float, cz: float, r: float, psi: float, y: float = 0.0):
    """Sous-repère posé sur un cercle d'axe vertical (cx, cz) et de rayon r, à l'angle psi (degrés ; 0 = vers -Z,
    90 = vers -X) : -Z local regarde vers l'extérieur, X local est tangent, l'origine est sur le cercle."""
    a = math.radians(psi)
    return b.at((cx - r * math.sin(a), y, cz - r * math.cos(a)), yaw=psi)


def _plaque(b, cx, cz, r, psi, y0, y1, w, saillie, col, prise=None, name: str = "Pierre", **kw):
    """Bloc plaqué sur un cylindre vertical : face extérieure à r + saillie, enfoncé de `prise` (courbure comprise)."""
    if prise is None:
        prise = w * w / (8.0 * r) + 0.12
    with _radial(b, cx, cz, r, psi):
        return b.box((-w / 2, y0, -saillie), (w / 2, y1, prise), col, name=name, **kw)


def _angle(w: float, r: float) -> float:
    """Demi-angle (degrés) qu'occupe une plaque de largeur w sur un cercle de rayon r."""
    return math.degrees(math.atan2(w / 2, r))


def _ecart(a: float, bb: float) -> float:
    return abs((a - bb + 180.0) % 360.0 - 180.0)


def _bloc_pose(b, xz, taille, col, yaw: float = 0.0, tilt=(0.0, 0.0), enfonce: float = 0.25, studs="top",
               name: str = "Eboulis", **kw):
    """Bloc posé au sol, éventuellement penché : son point le plus bas est enfoncé de `enfonce` (rien ne flotte)."""
    R = rot_y(yaw) @ rot_x(tilt[0]) @ rot_z(tilt[1])
    half = np.abs(R) @ (np.asarray(taille, float) / 2)
    return b.part("block", taille, (xz[0], float(half[1]) - enfonce, xz[1]), R, col, studs=studs, name=name, **kw)


def _eboulis(b, rng, pts, tons=SOMBRES, tailles=(1.2, 3.2), claveaux: int = 0, name: str = "Eboulis") -> None:
    """Tas de blocs tombés aux positions (x, z) ; les `claveaux` premiers sont des claveaux clairs allongés."""
    for i, (x, z) in enumerate(pts):
        if i < claveaux:
            t = (float(rng.uniform(1.4, 2.2)), float(rng.uniform(1.6, 2.4)), float(rng.uniform(2.6, 4.2)))
            col = vary("pierre_pale" if i % 2 == 0 else "pierre", rng, 0.05)
        else:
            s = float(rng.uniform(*tailles))
            t = (s * float(rng.uniform(0.8, 1.3)), s * float(rng.uniform(0.5, 0.8)), s * float(rng.uniform(0.8, 1.2)))
            col = _ton(rng, tons)
        _bloc_pose(b, (x, z), t, col, yaw=float(rng.uniform(0, 90)),
                   tilt=(float(rng.uniform(-14, 14)), float(rng.uniform(-14, 14))), name=name, **DECO)


def _cicatrice(b, rng, x: float, y0: float, y1: float, zf: float, larg: float = 1.5) -> None:
    """Cicatrice magique sur une face plane z = zf tournée vers -Z : brûlure noire en saillie et fente violette
    en zigzag (Neon) devant elle."""
    b.box((x - larg, y0 - 0.7, zf - 0.12), (x + larg, y1 + 0.7, zf + 0.3), c("obsidienne"), name="Brulure", **DECO)
    n = 3
    pts = [(x + (0.0 if i in (0, n) else (0.55 if i % 2 else -0.55) * larg) + float(rng.uniform(-0.15, 0.15)),
            y0 + (y1 - y0) * i / n) for i in range(n + 1)]
    for i in range(n):
        (xa, ya), (xb, yb) = pts[i], pts[i + 1]
        L = math.hypot(xb - xa, yb - ya)
        ang = math.degrees(math.atan2(yb - ya, xb - xa))
        b.part("block", (L + 0.3, 0.34, 0.16), ((xa + xb) / 2, (ya + yb) / 2, zf - 0.2), rot_z(ang),
               c("lueur_violette"), name="Fente", **NEON)


# ---------------------------------------------------------------------------
# Arcs « en gradins »
# ---------------------------------------------------------------------------

def _courbe(x: float, xl: float, xr: float, ys: float, f: float, kind: str, t: float = 0.0) -> float:
    """Hauteur de l'intrados (t = 0) ou de l'extrados (t = épaisseur du claveau) d'un arc, en x.
    'seg' : arc de cercle (plein cintre si f = demi-ouverture, surbaissé si f est plus petit) ;
    'brise' : arc brisé, deux arcs de cercle (f > demi-ouverture)."""
    w = xr - xl
    xm = 0.5 * (xl + xr)
    if kind == "brise":
        R = (f * f + w * w / 4.0) / w
        cx = xl + R if x <= xm else xr - R
        rr, d = R + t, x - cx
        return ys + math.sqrt(rr * rr - d * d) if abs(d) < rr else ys
    R = (w * w / 4.0 + f * f) / (2.0 * f)
    cy = ys + f - R
    rr, d = R + t, x - xm
    return max(ys, cy + math.sqrt(rr * rr - d * d)) if abs(d) < rr else ys


def _portee(xl: float, xr: float, f: float, kind: str, t: float) -> float:
    """Demi-largeur de l'extrados au niveau des naissances."""
    w = xr - xl
    if kind == "brise":
        return w / 2 + t
    R = (w * w / 4.0 + f * f) / (2.0 * f)
    return math.sqrt((R + t) ** 2 - (R - f) ** 2)


def _arc(b, rng, xl, xr, ys, f, kind, t, z0, z1, n, y_rempl, *, y_pied=None, dedans=False,
         claveaux=("pierre_pale", "pierre"), mur=PIERRES, z_mur=None, x_coupe=None, cle=True, archivolte=None) -> list:
    """Arc en gradins dans le plan XY : ouverture de xl à xr, naissances à ys, flèche f, claveaux d'épaisseur t,
    profondeur z0 → z1. Colonnes de claveaux alternés (clair / foncé), clé au milieu (n impair), tympan au-dessus de
    chaque claveau jusqu'à y_rempl (nombre, ou fonction (xa, xb) → hauteur ; profondeur z_mur, en retrait).
    `dedans` : le bas de chaque claveau suit le point le plus bas de l'intrados (naissances franches) ; sinon le
    plus haut (ouverture dégagée). y_pied : bas des colonnes posées sur les piles. x_coupe = (xa, xb) : ne garde
    que cette partie de l'arc (arc brisé d'une ruine). archivolte = (épaisseur, couleur, saillie) : second rouleau
    continu au-dessus des claveaux, qui dessine la courbe. Renvoie [(xa, xb, y_bas, y_haut)] des claveaux."""
    y_pied = ys if y_pied is None else y_pied
    z_mur = (z0, z1) if z_mur is None else z_mur
    xm = 0.5 * (xl + xr)
    ea = archivolte[0] if archivolte else 0.0
    reach = _portee(xl, xr, f, kind, t + ea)
    m = max(1, n - 2)
    xs = [xm - reach, xl] + [xl + (xr - xl) * k / m for k in range(1, m)] + [xr, xm + reach]
    out = []
    for k in range(len(xs) - 1):
        xa, xb = xs[k], xs[k + 1]
        est_cle = cle and xa < xm < xb
        if x_coupe is not None:
            xa, xb = max(xa, x_coupe[0]), min(xb, x_coupe[1])
            if xb - xa < 0.25:
                continue
        if xb <= xl + 1e-6 or xa >= xr - 1e-6:
            y0 = y_pied
        else:
            ya = _courbe(max(xa, xl), xl, xr, ys, f, kind)
            yb = _courbe(min(xb, xr), xl, xr, ys, f, kind)
            y0 = min(ya, yb) if dedans else max(ya, yb)
        cands = [xa, xb] + ([xm] if xa < xm < xb else [])
        y1 = max(_courbe(x, xl, xr, ys, f, kind, t) for x in cands)
        y0, y1 = round(y0 * 20) / 20, round(y1 * 20) / 20
        if est_cle:
            b.box((xa, y0 - 0.3, z0 - 0.3), (xb, y1 + ea + 0.6, z1 + 0.3), c(claveaux[0]), name="Cle")
            y1 += ea + 0.6
        else:
            if y1 - y0 > 0.1:
                b.box((xa, y0, z0), (xb, y1, z1), vary(claveaux[k % 2], rng, 0.04), name="Claveau")
            if archivolte:
                y2 = round(max(_courbe(x, xl, xr, ys, f, kind, t + ea) for x in cands) * 20) / 20
                y2 = max(y2, y1 + 0.5)
                sa = archivolte[2]
                b.box((xa, y1, z0 - sa), (xb, y2, z1 + sa), vary(archivolte[1], rng, 0.03), name="Archivolte")
                y1 = y2
        yr = y_rempl(xa, xb) if callable(y_rempl) else y_rempl
        if yr - y1 > 0.15:
            b.box((xa, y1, z_mur[0]), (xb, yr, z_mur[1]), _ton(rng, mur), name="Tympan")
        out.append((xa, xb, y0, y1))
    return out


# ---------------------------------------------------------------------------
# Porte d'entrée : deux tours rondes à toit conique (refBC2)
# ---------------------------------------------------------------------------

def _toit_conique(b, rng, cx, cz, y0, r0, y1, n=14, p=1.25, q=1.12, motif=MOTIF_TOIT) -> list:
    """Toit conique très pointu en anneaux de cylindres qui rétrécissent (gradins à studs, égout évasé)."""
    ts = [(i / n) ** q for i in range(n + 1)]
    anneaux = []
    for i in range(n):
        ya, yb = y0 + (y1 - y0) * ts[i], y0 + (y1 - y0) * ts[i + 1]
        r = max(0.45, r0 * (1.0 - ts[i]) ** p)
        b.cyl((cx, 0.5 * (ya + yb), cz), r, yb - ya, vary(motif[i % len(motif)], rng, 0.03), studs="top", name="Ardoise")
        anneaux.append((ya, yb, r))
    return anneaux


def _archere(b, cx, cz, r, psi, y0, h: float = 4.2, allumee: bool = True) -> None:
    """Archère sur un cylindre : encadrement clair en saillie, fente sombre ou éclairée à la bougie (Neon)."""
    _plaque(b, cx, cz, r, psi, y0 - 0.6, y0 + h + 0.6, 1.8, 0.14, c("pierre_pale"), name="Encadrement", **DECO)
    if allumee:
        _plaque(b, cx, cz, r, psi, y0, y0 + h, 0.6, 0.26, c("lueur_bougie"), name="Archere", **NEON)
    else:
        _plaque(b, cx, cz, r, psi, y0, y0 + h, 0.6, 0.26, c("obsidienne"), name="Archere", **DECO)


def _lierre_cyl(b, rng, cx, cz, r, psi, y0, y1, w, pendant: bool = False) -> None:
    """Lierre sur un cylindre : grappes de feuilles en quinconce (3 tons sombres), touffues au pied (ou en haut
    s'il pend d'une corniche), qui s'effilent ; saillies et angles tous différents (aucune face confondue)."""
    tons = (shade(c("lierre"), 0.78), c("lierre"), c("lierre"), c("lierre_clair"))
    h = y1 - y0
    n = max(3, int(round(h / 2.3)))
    for i in range(n):
        t = i / (n - 1)
        u = 1.0 - t if pendant else t                              # 0 au point d'accroche, 1 au bout effilé
        hh = float(rng.uniform(1.7, 2.6))
        yy = y0 + (h - hh) * t
        larg = w * (1.05 - 0.55 * u) * float(rng.uniform(0.75, 1.1))
        dpsi = math.degrees(float(rng.uniform(-0.45, 0.45)) * w / r) * (0.4 + u)
        _plaque(b, cx, cz, r, psi + dpsi, yy, yy + hh, max(0.8, larg), 0.17 + 0.06 * (i % 3),
                vary(tons[int(rng.integers(len(tons)))], rng, 0.05), name="Lierre", **DECO)


def _demi(x: float) -> float:
    """Ramène x sur la demi-grille (k + 1/2) × 0,25 : un détail ne tombe jamais dans le plan d'un bloc posé sur la
    grille de 0,25."""
    return math.floor(x * 4.0) / 4.0 + 0.125


def _lierre_plan(b, rng, xc, y0, y1, zf, w, pendant: bool = True, n: int = 0) -> None:
    """Lierre sur une face plane z = zf (tournée vers -Z ; zf = face du mur moins la saillie voulue) : grappes en
    quinconce, larges au point d'accroche (en haut s'il pend d'un parapet), effilées au bout."""
    tons = (shade(c("lierre"), 0.78), c("lierre"), c("lierre"), c("lierre_clair"))
    h = y1 - y0
    n = n or max(3, int(round(h / 2.6)))
    bords_x, bords_y = set(), set()
    for i in range(n):
        t = i / (n - 1)
        u = 1.0 - t if pendant else t
        hh = float(rng.uniform(1.8, 3.0))
        yy = y0 + (h - hh) * t
        larg = max(0.8, w * (1.05 - 0.6 * u) * float(rng.uniform(0.75, 1.1)))
        dx = float(rng.uniform(-0.35, 0.35)) * w * (0.4 + u)
        # bords sur la demi-grille (jamais dans le plan d'une pierre), profondeurs propres à chaque feuille
        xa, xb = _demi(xc + dx - larg / 2), _demi(xc + dx + larg / 2)
        ya, yb = _demi(yy), _demi(yy + hh)
        while xa in bords_x:                       # deux feuilles ne partagent jamais un plan de côté
            xa += 0.25
        while xb in bords_x:
            xb -= 0.25
        while ya in bords_y:
            ya += 0.25
        while yb in bords_y:
            yb -= 0.25
        if xb - xa < 0.5 or yb - ya < 0.5:
            continue
        bords_x.update((xa, xb))
        bords_y.update((ya, yb))
        b.box((xa, ya, zf - 0.035 * i), (xb, yb, zf + 0.55 - 0.02 * i),
              vary(tons[int(rng.integers(len(tons)))], rng, 0.05), name="Lierre", **DECO)


def _tour_porte(b, rng, s: int, xt: float, r: float, h: float, h_mur: float, v: int) -> float:
    """Tour ronde de la porte d'entrée, d'axe (s·xt, 0). Renvoie la hauteur du sommet."""
    cx, cz = s * xt, 0.0
    pin, pout = 90.0 * s, -90.0 * s                 # face intérieure (couloir), face extérieure (enceinte)
    y_cons, y_hourd = h - 8.0, h - 5.0              # consoles des mâchicoulis (50), galerie en encorbellement (53)
    reserve = [(0.0, 180.0, 27.5, 29.3), (pout, 32.0, 0.0, h_mur + 3.0), (107.5 * s, 9.0, 0.0, 27.0)]

    def libre(psi, da, y0, y1):
        return all(not (_ecart(psi, p) < d + da and y0 < a1 and y1 > a0) for (p, d, a0, a1) in reserve)

    def reserver(psi, w, y0, y1):
        reserve.append((psi, _angle(w, r) + 1.5, y0, y1))

    # --- talus, fût en assises de 4, cordon ---
    niveaux = [4.0 + 4.0 * k for k in range(int((y_hourd - 4.0) // 4.0))] + [y_hourd]
    with b.group("Fut"):
        b.cyl((cx, 1.0, cz), r + 1.5, 2.0, vary("pierre_ombre", rng, 0.03), studs="top", name="Talus")
        b.cyl((cx, 3.0, cz), r + 0.75, 2.0, vary("pierre_fonce", rng, 0.03), studs="top", name="Talus")
        prec = ""
        for k in range(len(niveaux) - 1):
            y0, y1 = niveaux[k], niveaux[k + 1]
            if k < 2:
                nom = ("pierre_ombre", "pierre_fonce")[k]
            else:
                choix = [n_ for n_ in ("pierre", "pierre_fonce", "pierre_fonce", "pierre_claire") if n_ != prec]
                nom = choix[int(rng.integers(len(choix)))] if rng.random() < 0.8 else "pierre"
            prec = nom
            b.cyl((cx, 0.5 * (y0 + y1), cz), r, y1 - y0, vary(nom, rng, 0.03), name="Assise")
        b.cyl((cx, 28.4, cz), r + 0.35, 1.2, c("pierre_pale"), name="Cordon")

    # --- mâchicoulis, galerie, bandeau ---
    with b.group("Machicoulis"):
        n_cons = 20
        for k in range(n_cons):
            with _radial(b, cx, cz, r, 360.0 * (k + 0.5) / n_cons):
                b.wedge_under((-0.65, y_cons, -1.25), (0.65, y_hourd + 0.2, 0.35), vary("pierre_pale", rng, 0.03),
                              down="-z", name="Console")
        b.cyl((cx, 0.5 * (y_hourd + h), cz), r + 1.3, h - y_hourd, vary("pierre", rng, 0.03), name="Galerie")
        for psi in (24.0 * s, 104.0 * s, 180.0 + 30.0 * s):
            _plaque(b, cx, cz, r + 1.3, psi, y_hourd + 1.0, y_hourd + 3.4, 1.1, 0.12, c("lueur_bougie"),
                    name="Fenetre", **NEON)
        b.cyl((cx, h + 0.6, cz), r + 1.9, 1.2, c("pierre_pale"), studs="top", name="Bandeau")

    # --- toit conique d'ardoise violette, épi doré, fanion uni ---
    y0t = h + 1.2
    y1t = y0t + 52.0                                  # aiguille d'ardoise : 1,65 × le diamètre (refBC2)
    with b.group("Toit"):
        _toit_conique(b, rng, cx, cz, y0t, r + 2.7, y1t, n=24, p=1.25, q=1.1)
        # lucarne éclairée tournée vers les arrivants, côté couloir
        with _radial(b, cx, cz, r, -24.0 * s):
            b.box((-1.5, y0t + 2.4, -2.5), (1.5, y0t + 6.4, 2.0), vary("pierre_claire", rng, 0.03), name="Lucarne")
            b.box((-0.65, y0t + 3.1, -2.65), (0.65, y0t + 5.5, -2.4), c("lueur_bougie"), name="Fenetre", **NEON)
            b.wedge((-1.85, y0t + 6.4, -2.8), (0.0, y0t + 8.6, 2.0), c("ardoise_fonce"), down="-x", studs="top", name="Lucarne")
            b.wedge((0.0, y0t + 6.4, -2.8), (1.85, y0t + 8.6, 2.0), c("ardoise_fonce"), down="+x", studs="top", name="Lucarne")
        b.cyl((cx, y1t + 0.45, cz), 0.6, 0.9, c("or"), name="Epi")
        b.ball((cx, y1t + 1.55, cz), 0.75, c("or"), name="Epi")
        b.cyl((cx, y1t + 3.85, cz), 0.16, 3.9, c("or"), name="Hampe", **FIN)
        fy0, fy1 = y1t + 3.2, y1t + 5.0
        xa, xb = sorted((cx + s * 0.12, cx + s * 3.0))
        sens = "+x" if s > 0 else "-x"
        b.wedge((xa, 0.5 * (fy0 + fy1), cz - 0.06), (xb, fy1, cz + 0.06), c("toile_cramoisie"), down=sens,
                name="Fanion", **FIN)
        b.wedge_under((xa, fy0, cz - 0.06), (xb, 0.5 * (fy0 + fy1), cz + 0.06), c("toile_cramoisie"), down=sens,
                      name="Fanion", **FIN)
    top = y1t + 5.85

    # --- échauguette en encorbellement (avant, côté extérieur) : casse la silhouette du cylindre ---
    pe = 40.0 * s
    with b.group("Echauguette"):
        a = math.radians(pe)
        ex, ez = cx - (r + 2.0) * math.sin(a), cz - (r + 2.0) * math.cos(a)
        for (rr, ya, yb, dd) in ((1.2, 32.0, 33.8, 0.6), (2.1, 33.8, 35.6, 1.2), (2.9, 35.6, 37.2, 1.8)):
            b.cyl((cx - (r + dd) * math.sin(a), 0.5 * (ya + yb), cz - (r + dd) * math.cos(a)), rr, yb - ya,
                  c("pierre_pale") if rr > 2.5 else vary("pierre_fonce", rng, 0.03), name="CulDeLampe")
        b.cyl((ex, 42.0, ez), 3.2, 9.6, vary("pierre_claire", rng, 0.03), name="Echauguette")
        b.cyl((ex, 47.1, ez), 3.6, 0.6, c("pierre_pale"), studs="top", name="Bandeau")
        _toit_conique(b, rng, ex, ez, 47.4, 4.1, 63.0, n=6, p=1.15, q=1.05)
        b.ball((ex, 63.4, ez), 0.45, c("or"), name="Epi")
        _archere(b, ex, ez, 3.2, pe, 40.0, 3.2, True)
    reserver(pe, 8.0, 31.0, 48.0)

    # --- archères (deux ou trois éclairées) ---
    with b.group("Archeres"):
        for (psi, y0, lit) in ((-30.0 * s, 17.0, True), (62.0 * s, 31.0, True), (150.0 * s, 21.0, v == 2),
                               (-128.0 * s, 39.5, True)):
            _archere(b, cx, cz, r, psi, y0, 4.2, lit)
            reserver(psi, 2.4, y0 - 1.0, y0 + 5.4)

    # --- bannières unies (avant et revers), lanterne au-dessus des vantaux ---
    yb = h - 11.0
    teintes = ((0, 1), (1, 0), (0, 0), (2, 1))[v]
    for (psi, var) in ((-16.0 * s, teintes[0] if s < 0 else teintes[1]), (180.0 - 14.0 * s, teintes[1] if s < 0 else teintes[0])):
        with _radial(b, cx, cz, r - 0.12, psi, y=yb):
            mobilier.banniere_murale(b, variant=var, hauteur=13.0)
        reserver(psi, 4.8, yb - 14.5, yb + 0.6)
    with _radial(b, cx, cz, r - 0.05, pin, y=14.0):
        mobilier.lanterne_murale(b, variant=0)
    reserver(pin, 1.8, 10.5, 15.0)

    # --- lierre (faces avant et intérieure, revers) ---
    with b.group("Lierre"):
        for (psi, y0, y1, w, pend) in ((24.0 * s, 0.0, 18.0, 3.4, False), (-10.0 * s, 0.0, 9.0, 2.6, False),
                                       (70.0 * s, 0.0, 22.0, 3.2, False), (74.0 * s, 37.5, 49.8, 2.6, True),
                                       (-112.0 * s, 38.6, 49.8, 2.4, True), (163.0 * s, 0.0, 14.0, 3.2, False)):
            _lierre_cyl(b, rng, cx, cz, r, psi, y0, y1, w, pend)
            reserver(psi, 1.8 * w, y0, y1 + 0.6)

    # --- pierres isolées en saillie (appareil en « pixels ») ---
    with b.group("Appareil"):
        for k in range(len(niveaux) - 1):
            ya, yb = niveaux[k], min(niveaux[k + 1], y_cons - 0.3)
            for _ in range(4):
                for _essai in range(16):
                    psi = float(rng.uniform(-180.0, 180.0))
                    w = float(rng.choice((2.0, 2.5, 3.0, 3.5)))
                    hh = float(rng.choice((1.5, 2.0, 2.5)))
                    if yb - ya < hh + 0.4:
                        break
                    y0 = ya + float(rng.uniform(0.2, yb - ya - hh - 0.2))
                    da = _angle(w, r) + 1.2
                    if not libre(psi, da, y0 - 0.4, y0 + hh + 0.4):
                        continue
                    if y0 < h_mur + 2.0 and _ecart(psi, pout) < 48.0:
                        continue
                    nom = ("pierre_claire", "pierre_pale", "pierre_fonce", "pierre_ombre")[
                        int(rng.choice(4, p=(0.35, 0.15, 0.35, 0.15)))]
                    _plaque(b, cx, cz, r, psi, y0, y0 + hh, w, float(rng.choice((0.18, 0.26, 0.34))),
                            vary(nom, rng, 0.04), name="Pierre", **DECO)
                    reserve.append((psi, da, y0, y0 + hh))
                    break
    return top


def _vantail(b, s: int, x_face: float, x_dos: float, za: float, zb: float, hv: float, x_tour: float) -> None:
    """Vantail de bois sombre cerclé de fer, ouvert à 90° et plaqué le long du couloir (face côté couloir en
    |x| = x_face) ; gonds de fer jusque dans la tour (|x| = x_tour)."""
    def X(a, bb):
        return sorted((s * a, s * bb))

    fer = c("fer_fonce")
    xa, xb = X(x_face + 0.6, x_dos)
    b.box((xa, 0.0, za), (xb, hv, zb), c("bois_fonce"), name="Vantail")
    for t in (0.2, 0.4, 0.6, 0.8):
        z = za + (zb - za) * t
        xa, xb = X(x_face + 0.45, x_face + 0.7)
        b.box((xa, 0.4, z - 0.12), (xb, hv - 0.4, z + 0.12), c("bois_noir"), name="Joint", **FIN)
    for y in (3.2, 0.5 * hv - 0.65, hv - 4.5):
        xa, xb = X(x_face + 0.25, x_face + 0.75)
        b.box((xa, y, za + 0.3), (xb, y + 1.3, zb - 0.3), fer, name="Penture", **DECO)
        for t in (0.1, 0.5, 0.9):
            z = za + (zb - za) * t
            xa, xb = X(x_face, x_face + 0.3)
            b.box((xa, y + 0.35, z - 0.3), (xb, y + 0.95, z + 0.3), c("fer"), name="Rivet", **FIN)
        xa, xb = X(x_dos - 0.4, x_tour)
        b.box((xa, y + 0.1, za - 0.45), (xb, y + 1.2, za + 0.55), fer, name="Gond", **DECO)
    xa, xb = X(x_face + 0.45, x_dos + 0.15)
    b.box((xa, hv, za - 0.15), (xb, hv + 0.5, zb + 0.15), fer, name="Chapeau", **DECO)


def _pilier_liaison(b, rng, s: int, x0: float, x1: float, hp: float) -> None:
    """Pilier qui lie la tour à l'enceinte (le premier segment d'enceinte s'y encastre)."""
    xa, xb = sorted((s * x0, s * x1))
    nv = (0.0, 12.0, 24.0, hp)
    for k in range(3):
        b.box((xa, nv[k], -5.5), (xb, nv[k + 1], 5.5), _ton(rng, PIERRES, (0.5, 0.25, 0.25), 0.04), name="Pilier")
    xa, xb = sorted((s * (x0 - 0.4), s * (x1 + 0.4)))
    b.box((xa, hp, -5.9), (xb, hp + 1.0, 5.9), c("pierre_pale"), studs="top", name="Chaperon")


def porte_entree(b, variant=0, ouverture=100, rayon_tour=13, hauteur_tour=58, hauteur_mur=34):
    """Porte d'entrée (refBC2) : deux tours rondes massives d'axes x = ±(ouverture/2 + rayon_tour), faces
    intérieures en |x| = ouverture/2 ; talus, assises de 4 en 3-4 tons et pierres en saillie, cordon, archères à la
    bougie, mâchicoulis sous une galerie en encorbellement, bandeau, toit conique très pointu d'ardoise violette
    (≈ 111) et épi doré à fanion uni, lierre, bannières unies avant et revers, lanterne au-dessus des vantaux ;
    vantaux de bois cerclés de fer ouverts vers le village (+Z local) le long du couloir (|x| 47-49) ; piliers de
    liaison avec l'enceinte (|x| 71-77). Rien en |x| < 47. Avant (-Z local) = côté des arrivants."""
    v = variant % 4
    rng = _rng(b, 1, v, lieu=False)
    r, h = float(rayon_tour), float(hauteur_tour)
    o2 = ouverture / 2.0
    xt = o2 + r
    # vantaux : ils commencent là où le talus de la tour dégage leur dos
    za = math.sqrt(max(0.0, (r + 1.5) ** 2 - (xt - (o2 - 1.0)) ** 2)) + 0.2
    zb = za + 13.0
    x_gond = xt - math.sqrt(max(0.0, r * r - (za + 0.55) ** 2)) + 0.3
    top = 0.0
    for s in (-1, 1):
        cote = "Droite" if s > 0 else "Gauche"
        with b.group(f"Tour{cote}"):
            top = max(top, _tour_porte(b, rng, s, xt, r, h, float(hauteur_mur), v))
        with b.group(f"Vantail{cote}"):
            _vantail(b, s, o2 - 3.0, o2 - 1.0, za, zb, 26.0, x_gond)
        with b.group(f"Liaison{cote}"):
            _pilier_liaison(b, rng, s, xt + r - 5.0, xt + r + 1.0, float(hauteur_mur) + 3.0)
    return {"emprise": (round(2 * (xt + r + 2.7), 1), round(r + 2.7 + zb, 1)), "hauteur": round(top, 1)}


# ---------------------------------------------------------------------------
# Enceinte
# ---------------------------------------------------------------------------

def _decoupe(rng, xa: float, xb: float, lmin: float, lmax: float, forces=()) -> list:
    """Découpe [xa, xb] en tronçons de lmin à lmax environ ; les bornes imposées (`forces`) sont gardées."""
    imposes = {xa, xb} | {f for f in forces if xa + 0.3 < f < xb - 0.3}
    pts = set(imposes)
    x = xa
    while True:
        x += float(rng.uniform(lmin, lmax))
        if x > xb - lmin:
            break
        pts.add(round(x * 4) / 4)
    res = []
    for p in sorted(pts):
        if res and p - res[-1] < 0.6:
            if p in imposes and res[-1] not in imposes:
                res[-1] = p
            elif p in imposes:
                res.append(p)
            continue
        res.append(p)
    return res


def _archere_plane(b, x: float, y0: float, zf: float, h: float = 3.8, allumee: bool = True) -> None:
    """Archère sur une face plane z = zf tournée vers -Z."""
    b.box((x - 0.9, y0 - 0.6, zf - 0.14), (x + 0.9, y0 + h + 0.6, zf + 0.2), c("pierre_pale"), name="Encadrement", **DECO)
    if allumee:
        b.box((x - 0.3, y0, zf - 0.26), (x + 0.3, y0 + h, zf + 0.2), c("lueur_bougie"), name="Archere", **NEON)
    else:
        b.box((x - 0.3, y0, zf - 0.26), (x + 0.3, y0 + h, zf + 0.2), c("obsidienne"), name="Archere", **DECO)


def mur_enceinte(b, variant=0, longueur=40.75, hauteur=34, epaisseur=8):
    """Segment d'enceinte crénelée le long de X local (centré, |x| ≤ longueur/2), épaisseur ±epaisseur/2 en z ;
    assises de 4 (mêmes hauteurs pour tous les segments, qui se touchent bout à bout), talus à la base, cordon clair
    à hauteur - 8, chemin de ronde à studs à hauteur - 4, parapet crénelé côté avant (-Z, merlons de 3 au pas de
    ≈ 4) et parapet bas côté village, deux contreforts à gradins sur l'avant.
    Variantes : 0 sobre (bannière murale) ; 1 rideaux de lierre et deux archères éclairées ; 2 brèche en V et
    éboulis ; 3 échauguette en encorbellement au milieu de l'avant."""
    v = variant % 4
    rng = _rng(b, 2, v, longueur)
    L, H, e = float(longueur), float(hauteur), float(epaisseur)
    x0, x1 = -L / 2, L / 2
    zf, zb = -e / 2, e / 2
    y_ch, y_co = H - 4.0, H - 8.0
    niveaux = [4.0 * k for k in range(int(y_ch // 4.0) + 1) if 4.0 * k < y_ch - 0.5] + [y_ch]

    # profil du haut du mur (brèche en V de la variante 2, en escalier)
    xb_c = x0 + L * float(rng.uniform(0.56, 0.68))
    marches = ((1.5, H - 12.0), (3.0, H - 10.0), (4.5, H - 8.0), (6.0, H - 6.0)) if v == 2 else ()
    coupes = sorted({xb_c + sg * hw for (hw, _) in marches for sg in (-1, 1)})

    def haut(xa, xb_):
        y = y_ch
        for (hw, yh) in marches:
            if xa < xb_c + hw - 1e-6 and xb_ > xb_c - hw + 1e-6:
                y = min(y, yh)
        return y

    bre = (xb_c - 6.0, xb_c + 6.0) if v == 2 else None
    ech = 0.0 if v == 3 else None                      # échauguette au milieu de l'avant
    lmin, lmax = (12.0, 21.0) if v in (1, 3) else (9.0, 17.0)   # blocs plus longs quand le décor coûte cher

    with b.group("Mur"):
        for k in range(len(niveaux) - 1):
            ya, yb = niveaux[k], niveaux[k + 1]
            utiles = []
            for xc_ in coupes:                                  # coupes de brèche qui changent le haut du bloc
                ga, gd = min(max(haut(xc_ - 0.2, xc_ - 0.1), ya), yb), min(max(haut(xc_ + 0.1, xc_ + 0.2), ya), yb)
                if abs(ga - gd) > 1e-6:
                    utiles.append(xc_)
            if bre is not None and utiles:
                cut = _decoupe(rng, x0, min(utiles), lmin, lmax) + sorted(utiles)[1:] + _decoupe(rng, max(utiles), x1, lmin, lmax)[1:]
                cut = sorted(set(cut))
            else:
                cut = _decoupe(rng, x0, x1, lmin, lmax, utiles)
            for i in range(len(cut) - 1):
                xa, xb_ = cut[i], cut[i + 1]
                lim = haut(xa, xb_)
                if ya >= lim - 0.05:
                    continue
                y1 = min(yb, lim)
                nom = ("pierre_ombre", "pierre_fonce", "pierre") if k == 0 else PIERRES
                poids = (0.4, 0.4, 0.2) if k == 0 else (0.42, 0.18, 0.4)
                b.box((xa, ya, zf), (xb_, y1, zb), _ton(rng, nom, poids, 0.04),
                      studs="top" if abs(y1 - lim) < 1e-6 else "none", name="Assise")
        b.wedge((x0, 0.0, zf - 1.0), (x1, 2.5, zf), vary("pierre_ombre", rng, 0.03), down="-z", studs="top", name="Talus")
        b.wedge((x0, 0.0, zb), (x1, 2.5, zb + 1.0), vary("pierre_ombre", rng, 0.03), down="+z", studs="top", name="Talus")
        # cordon (avant et arrière), interrompu par la brèche
        tron = [(x0, x1)] if bre is None else [(x0, xb_c - 4.5), (xb_c + 4.5, x1)]
        for (xa, xb_) in tron:
            if xb_ - xa > 0.3:
                b.box((xa, y_co, zf - 0.4), (xb_, y_co + 1.0, zf), c("pierre_pale"), name="Cordon")
                b.box((xa, y_co, zb), (xb_, y_co + 1.0, zb + 0.4), c("pierre_pale"), name="Cordon")

    with b.group("Parapets"):
        tron = [(x0, x1)] if bre is None else [(x0, bre[0]), (bre[1], x1)]
        for (xa, xb_) in tron:
            if xb_ - xa < 0.3:
                continue
            b.box((xa, y_ch, zf), (xb_, y_ch + 1.0, zf + 1.5), vary("pierre_claire", rng, 0.04), studs="top", name="Parapet")
            b.box((xa, y_ch, zb - 1.2), (xb_, y_ch + 2.0, zb), vary("pierre", rng, 0.04), studs="top", name="ParapetBas")
        n_m = max(1, int(round(L / 4.0)))
        pas = L / n_m
        for k in range(n_m):
            xm = x0 + pas * (k + 0.5)
            if bre is not None and bre[0] - 1.5 < xm < bre[1] + 1.5:
                continue
            if ech is not None and abs(xm - ech) < 3.6:
                continue
            b.box((xm - 1.5, y_ch + 1.0, zf), (xm + 1.5, H, zf + 1.5), _ton(rng, PIERRES, (0.5, 0.3, 0.2), 0.04),
                  studs="top", name="Merlon")

    with b.group("Contreforts"):
        for xc in (x0 + L * 0.25 + float(rng.uniform(-1.5, 1.5)), x0 + L * 0.75 + float(rng.uniform(-1.5, 1.5))):
            for (hw, d, ya, yb) in ((1.8, 3.0, 0.0, 8.0), (1.5, 2.0, 8.0, 14.0), (1.2, 1.0, 14.0, 20.0)):
                b.box((xc - hw, ya, zf - d), (xc + hw, yb, zf), _ton(rng, PIERRES, (0.4, 0.2, 0.4), 0.04),
                      studs="top", name="Contrefort")

    if v == 0:
        with b.at((float(rng.uniform(-2.0, 2.0)), y_co - 0.6, zf)):
            mobilier.banniere_murale(b, variant=int(rng.integers(2)), hauteur=10.0)
    elif v == 1:
        with b.group("Lierre"):
            for xc in (x0 + L * 0.14, x0 + L * 0.5 + float(rng.uniform(-2, 2)), x0 + L * 0.86):
                _lierre_plan(b, rng, xc, float(rng.uniform(14.0, 19.0)), H - 0.4, zf - 0.45, float(rng.uniform(3.0, 4.0)),
                             pendant=True, n=4)
        with b.group("Archeres"):
            for xc in (x0 + L * 0.36, x0 + L * 0.64):
                _archere_plane(b, xc, 15.0, zf, 3.8, True)
    elif v == 2:
        pts = []
        for sz in (-1, 1):
            for _ in range(4):
                pts.append((xb_c + float(rng.uniform(-6.5, 6.5)), sz * float(rng.uniform(e / 2 + 1.2, e / 2 + 5.0))))
        with b.group("Eboulis"):
            _eboulis(b, rng, pts, PIERRES + ("pierre_ombre",), (1.4, 3.0))
    else:
        zc = zf - 2.0                                  # axe de l'échauguette (enfoncée de 1 dans le mur)
        with b.group("Echauguette"):
            for (rr, ya, yb) in ((0.9, 19.0, 20.6), (1.7, 20.6, 22.2), (2.5, 22.2, 24.0)):
                b.cyl((ech, 0.5 * (ya + yb), zf + 0.4 - rr), rr, yb - ya,
                      c("pierre_pale") if rr > 2 else vary("pierre", rng, 0.04), name="Cul_de_lampe")
            b.cyl((ech, 28.5, zc), 3.0, 9.0, vary("pierre_claire", rng, 0.04), name="Echauguette")
            b.cyl((ech, 33.3, zc), 3.4, 0.6, c("pierre_pale"), studs="top", name="Bandeau")
            _toit_conique(b, rng, ech, zc, 33.6, 3.8, 42.0, n=5, p=1.1, q=1.0)
            b.ball((ech, 42.4, zc), 0.45, c("or"), name="Epi")
            _archere(b, ech, zc, 3.0, 0.0, 26.0, 3.0, True)
    avant = {0: e / 2 + 3.0, 1: e / 2 + 3.0, 2: 10.0, 3: e / 2 + 5.8}[v]     # contreforts, éboulis, échauguette
    arriere = 10.0 if v == 2 else e / 2 + 1.0
    return {"emprise": (L, round(avant + arriere, 1)), "hauteur": H if v != 3 else 42.9}


# ---------------------------------------------------------------------------
# Ruines du champ de bataille
# ---------------------------------------------------------------------------

def ruine_tour(b, variant=0, rayon=10, hauteur=44):
    """Tour ronde brisée et creuse (refBC4) : anneau de 12 douves de pierre noircie (2 d'épaisseur) en assises,
    chaque douve à sa hauteur (couronne déchiquetée, avant plus bas qui montre le vide), brèche, poutres calcinées
    en travers, archère, éboulis au pied, lierre et mousse.
    Variantes : 0 haute, brèche vers le couloir ; 1 moignon (moitié de hauteur) et pan de mur couché ; 2 la plus
    haute, arc de parapet crénelé encore debout et cicatrice magique violette ; 3 tour fendue en deux."""
    v = variant % 4
    rng = _rng(b, 3, v, rayon, hauteur)
    r, H = float(rayon), float(hauteur)
    n, ep = 12, 2.0
    w = 2.0 * r * math.tan(math.pi / n) + 0.04
    hmax = H * (0.55 if v == 1 else 1.0)
    pas = max(6.0, H / 6.0)
    hs = []
    for k in range(n):
        u = (1.0 - math.cos(math.radians(360.0 * k / n))) / 2.0        # 0 devant (couloir), 1 derrière
        hs.append(hmax * (0.34 + 0.66 * u ** 0.75) * float(rng.uniform(0.8, 1.0)))
    if v == 0:
        hs[0], hs[1] = 2.4, 5.2
    elif v == 1:
        hs[2], hs[1] = 1.6, 4.0
    elif v == 2:
        hs[3], hs[4] = 3.2, 9.0
        for j, k in enumerate((5, 6, 7, 8)):
            hs[k] = H - 3.6 + 0.15 * j
    else:
        hs[0], hs[6], hs[7] = 1.2, 2.0, 6.5
    hs = [round(hk * 2) / 2 + 0.1 * (k % 3) for k, hk in enumerate(hs)]

    # fenêtres : une douve haute (deux en v2) percée d'une baie, appui et linteau clairs
    fen = {}
    for k in sorted(range(n), key=lambda k: -hs[k])[: (2 if v == 2 else 1) if v != 1 else 0]:
        if hs[k] > 22.0:
            yw = round(hs[k] * 0.52 * 2) / 2
            fen[k] = (yw, yw + 4.5)
    with b.group("Douves"):
        for k in range(n):
            psi = 360.0 * k / n
            with _radial(b, 0.0, 0.0, r, psi):
                ya, j = 0.0, 0
                premier = pas * (1.0 if k % 2 else 0.55)       # assises décalées d'une douve à l'autre
                tranches = [(0.0, hs[k])] if k not in fen else [(0.0, fen[k][0] - 0.6), (fen[k][1] + 0.8, hs[k])]
                for (t0, t1) in tranches:
                    ya, j = t0, (0 if t0 == 0.0 else 1)
                    while ya < t1 - 0.05:
                        yb = min(t1, premier if (j == 0 and t0 == 0.0) else ya + pas)
                        if t1 - yb < 1.2:
                            yb = t1
                        nom = ("pierre_ombre", "pierre_noire", "pierre_fonce") if ya == 0.0 else SOMBRES
                        b.box((-w / 2, ya, 0.0), (w / 2, yb, ep), _ton(rng, nom, None, 0.05),
                              studs="top" if yb >= hs[k] - 1e-6 else "none", name="Douve")
                        ya, j = yb, j + 1
                if k in fen:
                    y0w, y1w = fen[k]
                    b.box((-w / 2 - 0.05, y0w - 0.6, -0.25), (w / 2 + 0.05, y0w, ep), vary("pierre_pale", rng, 0.04),
                          studs="top", name="Appui")
                    b.box((-w / 2 - 0.05, y1w, -0.2), (w / 2 + 0.05, y1w + 0.8, ep), vary("pierre_pale", rng, 0.04),
                          name="Linteau")
                    for sx in (-1, 1):                           # piédroits qui resserrent la baie
                        b.box((sx * w / 2 - (0.9 if sx > 0 else 0.0), y0w, -0.1), (sx * w / 2 + (0.9 if sx < 0 else 0.0),
                              y1w, ep - 0.1), vary("pierre_fonce", rng, 0.04), name="Piedroit")

    def point(k, y, rr):
        a = math.radians(360.0 * k / n)
        return np.array([-rr * math.sin(a), y, -rr * math.cos(a)])

    with b.group("Poutres"):
        for (ka, kb, f) in ((4, 8, 0.62), (3, 9, 0.38)):
            y = min(hs[ka], hs[kb]) * f
            if y > 4.0 and min(hs[ka], hs[kb]) - y > 1.5:
                _poutre(b, point(ka, y, r - 0.6), point(kb, y + 0.8, r - 0.6), 1.1, vary("bois_brule", rng, 0.08),
                        name="PoutreCalcinee", **DECO)
        k_dos = int(np.argmax(hs))
        _poutre(b, (float(rng.uniform(-1.5, 1.5)), 0.4, -0.25 * r), point(k_dos, min(hs[k_dos] - 1.5, 0.45 * H), r - 2.4),
                1.0, vary("bois_brule", rng, 0.08), name="PoutreTombee", **DECO)

    with b.group("Details"):
        k_arch = 5 if hs[5] > 12 else int(np.argmax(hs))
        with _radial(b, 0.0, 0.0, r, 360.0 * k_arch / n):
            ya = min(hs[k_arch] * 0.55, hs[k_arch] - 5.0)
            b.box((-0.45, ya, -0.12), (0.45, ya + 3.6, 0.3), c("obsidienne"), name="Archere", **DECO)
        hauts = sorted(range(n), key=lambda k: -hs[k])
        for k in (hauts[1], hauts[4], hauts[7]):
            with _radial(b, 0.0, 0.0, r, 360.0 * k / n):
                b.box((-w / 2 + 0.45, hs[k], 0.35), (w / 2 - 0.45, hs[k] + 0.25, ep - 0.35), vary("mousse", rng, 0.08),
                      name="Mousse", **FIN)
        for k in (10, 2, 9) if v != 3 else (2, 4, 10):
            if hs[k] < 8:
                continue
            with _radial(b, 0.0, 0.0, r, 360.0 * k / n):
                hl = hs[k] * float(rng.uniform(0.45, 0.75))
                _lierre_plan(b, rng, float(rng.uniform(-0.15, 0.15)) * w, 0.0, hl, -0.3, w * 0.7, pendant=False,
                             n=max(3, int(hl / 3.2)))

    if v == 2:
        with b.group("Parapet"):
            for k in (5, 6, 7, 8):
                with _radial(b, 0.0, 0.0, r, 360.0 * k / n):
                    for xc in (-w * 0.27, w * 0.27):
                        b.wedge_under((xc - 0.5, hs[k] - 2.4, -1.2), (xc + 0.5, hs[k], 0.3), c("pierre_fonce"),
                                      down="-z", name="Console", **DECO)
                    b.box((-w / 2 - 0.3, hs[k], -1.2), (w / 2 + 0.3, hs[k] + 1.0, 0.7), _ton(rng, SOMBRES), name="Parapet")
                    b.box((-w * 0.27, hs[k] + 1.0, -1.2), (w * 0.27, hs[k] + 3.4, 0.4), _ton(rng, SOMBRES),
                          studs="top", name="Merlon")
        with _radial(b, 0.0, 0.0, r, 330.0):
            _cicatrice(b, rng, 0.2, 4.0, min(hs[11] - 2.0, 14.0), 0.0, 1.3)

    # éboulis au pied (surtout devant la brèche), pan de mur couché (v1)
    pts = []
    k_b = {0: 0, 1: 2, 2: 3, 3: 0}[v]
    for i in range(7):
        a = math.radians(360.0 * k_b / n + float(rng.uniform(-50, 50)) + (180.0 if i == 6 else 0.0))
        d = r + float(rng.uniform(0.8, 5.0))
        pts.append((-d * math.sin(a), -d * math.cos(a)))
    pts.append((float(rng.uniform(-2, 2)), float(rng.uniform(-2, 2))))
    with b.group("Eboulis"):
        _eboulis(b, rng, pts, SOMBRES, (1.3, 3.2))
        if v == 1:
            with _radial(b, 0.0, 0.0, r + 3.3, 360.0 * 2 / n + 12.0):
                _bloc_pose(b, (0.0, 0.0), (min(1.6 * w, 9.0), ep, 3.6), _ton(rng, SOMBRES), yaw=6.0, tilt=(5.0, 3.0),
                           name="PanCouche")
    return {"emprise": (2 * r + 12, 2 * r + 12), "hauteur": round(max(hs) + (3.4 if v == 2 else 0.0), 1)}


def _courses_ruine(b, rng, x0, x1, z0, z1, hauteur_de, pas=4.0, lmin=3.5, lmax=7.0, exclus=None, tons=SOMBRES,
                   socle=0.0) -> dict:
    """Maçonnerie en ruine le long de X : assises de `pas` en appareil décalé, chaque bloc coupé par le profil
    `hauteur_de(xa, xb)` et posé sur un appui complet (aucun bloc en surplomb). exclus(y0, y1) → [(xa, xb)]
    réservés (porte). Renvoie la hauteur réelle par tranche de 0,25 (dict index → y)."""
    q = 0.25
    n = int(round((x1 - x0) / q))
    appui = [socle] * n

    def idx(x):
        return int(round((x - x0) / q))

    prof = [hauteur_de(x0 + j * q, x0 + (j + 1) * q) for j in range(n)]
    ya = 0.0
    k = 0
    while True:
        yb = ya + pas
        cut = _decoupe(rng, x0, x1, lmin, lmax)
        if k % 2:                                   # appareil décalé d'une assise à l'autre
            cut = sorted({x0, x1} | {min(x1 - 0.5, max(x0 + 0.5, round((p_ + 0.5 * lmin) * 4) / 4)) for p_ in cut[1:-1]})
        bloque = exclus(ya, yb) if exclus else []
        pose = False
        for i in range(len(cut) - 1):
            xa, xb = cut[i], cut[i + 1]
            # appui complet sur l'assise du dessous, hors zone réservée
            seg, debut = [], None
            for j in range(idx(xa), idx(xb)):
                xx = x0 + (j + 0.5) * q
                ok = appui[j] >= ya - 1e-6 and not any(a_ <= xx <= b_ for (a_, b_) in bloque)
                if ok and debut is None:
                    debut = j
                if (not ok or j == idx(xb) - 1) and debut is not None:
                    fin = j + 1 if ok else j
                    seg.append((debut, fin))
                    debut = None
            for (ja, jb) in seg:
                # sous-blocs là où le profil dépasse le bas de l'assise (le bloc se brise sur les chutes du profil)
                runs, deb = [], None
                for j in range(ja, jb + 1):
                    ok = j < jb and prof[j] >= ya + 0.9
                    if ok and deb is None:
                        deb = j
                    if not ok and deb is not None:
                        runs.append((deb, j))
                        deb = None
                for (ra, rb) in runs:
                    sa, sb = x0 + ra * q, x0 + rb * q
                    if sb - sa < 1.4:
                        continue
                    top = min(yb, round(min(prof[ra:rb]) * 2) / 2)
                    if top < ya + 0.5:
                        continue
                    b.box((sa, ya, z0), (sb, top, z1), _ton(rng, tons, None, 0.05), studs="top", name="Assise")
                    pose = True
                    for j in range(ra, rb):
                        appui[j] = top
        if not pose:
            break
        ya, k = yb, k + 1
    return appui


def _lierre_mur(b, rng, x, y_haut, hl, zf, w) -> None:
    """Coulée de lierre qui pend du haut d'un mur plan (face z = zf tournée vers -Z)."""
    _lierre_plan(b, rng, x, max(0.4, y_haut - hl), y_haut + 0.3, zf - 0.3, w, pendant=True,
                 n=max(3, int(round(hl / 2.8))))


def ruine_mur(b, variant=0, longueur=36, hauteur=18, epaisseur=5):
    """Courtine en ruine le long de X local : assises de pierres noircies en appareil décalé, haut en escalier
    (chaque bloc posé sur un appui complet), fragment de créneaux, éboulis au pied, lierre et mousse. Emprise
    ≤ longueur × (epaisseur + 6).
    Variantes : 0 déchiquetée avec deux merlons ; 1 percée d'une porte en arc brisé (6 × 10) ; 2 effondrée au
    milieu (deux moignons et un tas d'éboulis) ; 3 basse, avec un contrefort tombé."""
    v = variant % 4
    rng = _rng(b, 4, v, longueur, hauteur)
    L, H, e = float(longueur), float(hauteur), float(epaisseur)
    x0, x1 = -L / 2, L / 2
    zf, zb = -e / 2, e / 2
    porte = (-3.0, 3.0) if v == 1 else None
    t_p = 1.2
    y_porte = 12.0                                             # dessus des tympans de la porte (3 assises)
    bruit = rng.uniform(0.8, 1.0, size=int(L) + 2)

    def profil(x):
        u = (x - x0) / L
        if v == 0:
            f = 0.42 + 0.58 * math.exp(-((u - 0.3) / 0.24) ** 2)
        elif v == 1:
            f = 0.9 + 0.1 * math.cos(u * 6.0)
        elif v == 2:
            f = 1.0 if u < 0.2 else (0.78 if u > 0.8 else 0.0)
        else:
            f = 0.62 + 0.2 * math.sin(u * 6.5 + 0.8)
        return H * f * bruit[min(len(bruit) - 1, max(0, int(x - x0)))]

    def hauteur_de(xa, xb):
        h_ = min(profil(xa + (xb - xa) * t) for t in (0.1, 0.5, 0.9))
        if porte:
            h_ = max(h_, y_porte + 1.0) if xa < porte[1] + 6 and xb > porte[0] - 6 else h_
        return h_

    def exclus(ya, yb):
        return [(porte[0] - t_p, porte[1] + t_p)] if porte and ya < y_porte - 1e-6 else []

    with b.group("Mur"):
        appui = _courses_ruine(b, rng, x0, x1, zf, zb, hauteur_de, exclus=exclus)
        if porte:
            for (xa, xb) in ((porte[0] - t_p, porte[0]), (porte[1], porte[1] + t_p)):
                b.box((xa, 0.0, zf - 0.2), (xb, 6.5, zb + 0.2), vary("pierre_fonce", rng, 0.04), name="Jambage")
            _arc(b, rng, porte[0], porte[1], 6.5, 3.5, "brise", t_p, zf - 0.2, zb + 0.2, 7, y_porte, y_pied=6.5,
                 claveaux=("pierre_claire", "pierre_fonce"), mur=SOMBRES, z_mur=(zf, zb))
    q = 0.25
    tops = [(x0 + (j + 0.5) * q, y) for j, y in enumerate(appui)]
    j_max = int(np.argmax(appui))
    x_max, h_max = tops[j_max]
    with b.group("Details"):
        if v in (0, 3):
            # deux merlons sur le bloc le plus haut
            ja = j_max
            while ja > 0 and abs(appui[ja - 1] - h_max) < 1e-6:
                ja -= 1
            jb = j_max
            while jb < len(appui) - 1 and abs(appui[jb + 1] - h_max) < 1e-6:
                jb += 1
            xa, xb = x0 + ja * q, x0 + (jb + 1) * q
            mer = ((xa + 0.3, xa + 1.6), (xb - 1.6, xb - 0.3)) if xb - xa >= 3.9 else ((xa + 0.3, xb - 0.3),)
            for (lo, hi) in mer:
                if hi - lo > 0.8:
                    b.box((lo, h_max, zf), (hi, h_max + 2.2, zf + 1.4), _ton(rng, SOMBRES), studs="top", name="Merlon")
        # lierre qui pend des parties hautes, mousse sur quelques arases
        hauts = sorted(range(0, len(appui), 12), key=lambda j: -appui[j])
        poses = []
        for j in hauts:
            x = x0 + (j + 0.5) * q
            if appui[j] < 6.0 or any(abs(x - p_) < 5.0 for p_ in poses) or (porte and abs(x) < 6.0) \
                    or not (x0 + 3.0 < x < x1 - 3.0):
                continue
            _lierre_mur(b, rng, x, appui[j], appui[j] * float(rng.uniform(0.45, 0.8)), zf, float(rng.uniform(2.4, 3.4)))
            poses.append(x)
            if len(poses) >= 2:
                break
        moss = [j for j in range(0, len(appui), 9) if appui[j] > 3.0 and abs(appui[j] - h_max) > 0.4]
        for j in moss[1::3][:2]:
            x = x0 + (j + 0.5) * q
            b.box((x - 0.9, appui[j], zf + 0.5), (x + 0.9, appui[j] + 0.3, zb - 0.5), vary("mousse", rng, 0.08),
                  name="Mousse", **FIN)
    pts = []
    for i in range(9 if v == 2 else 6):
        x = float(rng.uniform(x0 + 0.25 * L, x0 + 0.75 * L)) if v == 2 else float(rng.uniform(x0 + 2, x1 - 2))
        pts.append((x, (-1 if (i % 3) else 1) * float(rng.uniform(e / 2 + 0.7, e / 2 + 1.5))))
    with b.group("Eboulis"):
        _eboulis(b, rng, pts, SOMBRES, (1.0, 2.2))
        if v == 3:
            xc = x0 + L * 0.62
            b.box((xc - 1.3, 0.0, zf - 2.2), (xc + 1.3, 2.4, zf), _ton(rng, SOMBRES), studs="top", name="Contrefort")
            _bloc_pose(b, (xc + 3.6, zf - 1.5), (2.0, 1.8, 6.0), _ton(rng, SOMBRES), yaw=84.0, tilt=(0.0, 8.0),
                       name="ContrefortTombe")
    return {"emprise": (L, e + 6.0), "hauteur": round(h_max + (2.2 if v in (0, 3) else 0.0), 1)}


def arche_effondree(b, variant=0, largeur=30, hauteur=26):
    """Arcade isolée le long de X local (profondeur 6) sur piles massives, arcs à claveaux alternés et archivolte,
    mur au-dessus au haut déchiqueté, lierre (refBC4). Variantes : 0 trois arcs dont un tombé (moignon de pile,
    claveaux au sol) ; 1 deux arcs, le second réduit à une pile penchée ; 2 un seul grand arc brisé encore debout ;
    3 trois arcs debout, crête ruinée."""
    v = variant % 4
    rng = _rng(b, 5, v, largeur, hauteur)
    W, H = float(largeur), float(hauteur)
    x0 = -W / 2
    d = 3.0
    if v in (0, 3):
        n_arc, wp, ys, kind, t = 3, 3.4, 0.46 * H, "seg", 1.3
    elif v == 1:
        n_arc, wp, ys, kind, t = 2, 4.0, 0.4 * H, "seg", 1.6
    else:
        n_arc, wp, ys, kind, t = 1, 5.0, 0.36 * H, "brise", 1.8
    wo = (W - (n_arc + 1) * wp) / n_arc
    f = wo / 2 if kind == "seg" else 0.66 * wo
    piles = [x0 + k * (wp + wo) for k in range(n_arc + 1)]          # bord gauche de chaque pile
    tombe = {0: (2,), 1: (1,), 2: (), 3: ()}[v]
    crete = []
    colonnes = []
    graines = rng.uniform(0.0, 1.0, size=64)

    def rempl(xa, xb):
        u = (0.5 * (xa + xb) - x0) / W
        base = ys + f + t + 1.0
        y = base + (H - 1.0 - base) * (0.5 + 0.5 * math.sin(u * 8.0 + 1.3)) * (0.55 + 0.45 * graines[int(u * 63) % 64])
        y = round(y * 2) / 2
        crete.append(y)
        colonnes.append((xa, xb, y))
        return y

    with b.group("Piles"):
        for k, xp in enumerate(piles):
            if v == 1 and k == 2:
                with b.at((xp + wp / 2, -0.4, 0.0)):
                    R = rot_z(-11.0)
                    for (ya, yb, nom) in ((0.0, ys * 0.5, "pierre_fonce"), (ys * 0.5, ys, "pierre")):
                        b.part("block", (wp, yb - ya, 2 * d), R @ np.array([0.0, 0.5 * (ya + yb), 0.0]), R,
                               vary(nom, rng, 0.05), name="PilePenchee")
                    b.part("block", (wp + 1.4, 2.4, 2 * d + 0.4), R @ np.array([0.7, ys + 1.2, 0.0]), R, c("pierre_pale"),
                           studs="top", name="Claveau")
                continue
            hp = 4.5 if (v == 0 and k == 3) else ys
            b.box((xp - 0.4, 0.0, -d - 0.4), (xp + wp + 0.4, 1.4, d + 0.4), vary("pierre_ombre", rng, 0.04), studs="top",
                  name="Socle")
            mid = round(hp * 0.55 * 2) / 2
            b.box((xp, 1.4, -d), (xp + wp, mid, d), _ton(rng, SOMBRES), studs="top" if hp < ys else "none", name="Pile")
            if hp >= ys - 0.01:
                b.box((xp, mid, -d), (xp + wp, ys - 0.8, d), _ton(rng, ("pierre", "pierre_fonce")), name="Pile")
                b.box((xp - 0.3, ys - 0.8, -d - 0.3), (xp + wp + 0.3, ys, d + 0.3), c("pierre_pale"), name="Imposte")

    with b.group("Arcs"):
        for k in range(n_arc):
            if k in tombe:
                continue
            xl, xr = piles[k] + wp, piles[k + 1]
            coupe = (piles[k] + wp / 2 if k > 0 else -1e9, xr + wp / 2 if k < n_arc - 1 else 1e9)
            if k + 1 in tombe:
                coupe = (coupe[0], xr + (1.0 if v == 0 else wp * 0.5))
            _arc(b, rng, xl, xr, ys, f, kind, t, -d, d, 7 if wo < 9 else 11, rempl, dedans=True,
                 claveaux=("pierre_claire", "pierre_fonce"), mur=("pierre_fonce", "pierre", "pierre_noire"),
                 z_mur=(-d + 0.3, d - 0.3), x_coupe=coupe, archivolte=None if v == 3 else (0.7, "pierre_pale", 0.15))
        # crête au-dessus des piles intérieures encore debout
        for k in range(1, n_arc):
            if k in tombe or k - 1 in tombe:
                continue
            xa = piles[k] + wp * 0.5 - 0.7
            yb_ = rempl(xa, xa + 1.4) + 1.6
            b.box((xa, yb_ - 2.4, -d), (xa + 1.4, yb_, d), _ton(rng, SOMBRES), studs="top", name="Crete")

    with b.group("Lierre"):
        for k in (0, n_arc - 1 if n_arc > 1 else 1):
            xp = piles[k] + wp * 0.5
            hl = float(rng.uniform(0.55, 0.9)) * ys
            _lierre_plan(b, rng, xp, 1.4, hl, -d - 0.25, wp * 0.8, pendant=False, n=max(3, int(hl / 3.0)))
        # coulée qui pend du haut d'une colonne de tympan encore debout (accrochée à son arase)
        hautes = [col_ for col_ in colonnes if col_[1] - col_[0] > 1.2 and col_[2] > ys + f + t + 1.5]
        if hautes:
            xa, xb, yh = hautes[int(rng.integers(len(hautes)))]
            _lierre_plan(b, rng, 0.5 * (xa + xb), ys + f + t - 1.0, yh - 0.2, -d + 0.05, min(2.6, xb - xa), pendant=True,
                         n=3)

    pts = []
    for k in tombe:
        xa, xb = piles[k] + wp, piles[k + 1]
        for i in range(5):
            pts.append((float(rng.uniform(xa, xb + 1.0)), float(rng.choice((-1, 1))) * float(rng.uniform(d + 0.3, d + 0.9))))
    for i in range(3):
        pts.append((float(rng.uniform(x0 + 2, -x0 - 2)), float(rng.choice((-1, 1))) * float(rng.uniform(d + 0.4, d + 0.9))))
    with b.group("Eboulis"):
        _eboulis(b, rng, pts, SOMBRES, (0.9, 1.7), claveaux=4 if tombe else 0)
    return {"emprise": (W, 2 * d + 2.0), "hauteur": round(max(crete + [ys + f + t]) + 1.6, 1)}


# ---------------------------------------------------------------------------
# Aqueduc ruiné (refBC3)
# ---------------------------------------------------------------------------

def aqueduc(b, variant=0, largeur=478, ouverture=94, dessous=36, hauteur=62, rupture=(100.0, 164.0), affaisse=None):
    """Aqueduc ruiné le long de X local, en travers du couloir. Piles de 10 × 10 sur socles (piles du couloir de
    |x| = ouverture/2 à ouverture/2 + 10, socles à 0,5 près), les autres au pas de 32 ; arche centrale surbaissée
    au-dessus du couloir (naissances à `dessous`, rien sous `dessous` au-dessus de |x| < ouverture/2), arches
    latérales de 22 en plein cintre (dessous ≈ 44) ; tympans en retrait, corniche, tablier, deux parapets bas
    édentés (une travée sur trois a perdu le sien hors du couloir) et canal d'eau sombre jusqu'à `hauteur`. Pierre
    sombre (gris-violet foncé, ombre, noire) : seuls les claveaux et l'archivolte de l'arche centrale sont clairs,
    la ligne qui encadre le château. Ruptures (`rupture` : (x0, x1) ou liste de tronçons en x local ; la première
    est la grande brèche) : tablier et arcs disparus, piles réduites à des moignons, bouts cassés, éboulis,
    cicatrices magiques violettes ; la grande brèche a sa cascade qui tombe du canal brisé dans une flaque.
    `affaisse` : {(x0, x1) d'une travée : affaissement} (tablier, parapets et canal plus bas sur cette travée).
    Variantes : 0 conforme au plan ; 1 intact ; 2 ruptures en miroir ; 3 comme 0, plus de lierre."""
    v = variant % 4
    rng = _rng(b, 6, v, lieu=False)
    X = largeur / 2.0
    o2 = ouverture / 2.0
    wp, dz = 10.0, 5.0                         # piles 10 × 10
    zt = 4.6                                   # tympans en retrait de 0,4 (0,8 sur l'arche centrale)
    y_cor = hauteur - 9.0                      # 53 : corniche
    y_tab = y_cor + 1.5                        # 54,5 : tablier
    y_par = hauteur - 3.5                      # 58,5 : pied des parapets, fond du canal
    y_imp = y_cor - 20.0                       # 33 : naissance des arches latérales, haut des impostes
    t_lat, t_cen = 2.5, 3.0
    f_cen = y_cor - t_cen - dessous            # flèche de l'arche centrale (14)
    centres = []
    u = o2 + wp / 2
    while u + wp / 2 <= X - 20.0:
        centres.append(u)
        u += 32.0
    if v == 1 or rupture is None:
        rups = []
    else:
        liste = [rupture] if isinstance(rupture[0], (int, float)) else list(rupture)
        rups = [(min(r_), max(r_)) for r_ in liste]
        if v == 2:
            rups = [(-hi, -lo) for (lo, hi) in rups]
    affaisse = {} if v == 1 or not affaisse else {tuple(sorted(k_)): float(d_) for k_, d_ in affaisse.items()}

    def casse(x):
        """Indice de la rupture où tombe x (local), ou None."""
        for i_, (lo, hi) in enumerate(rups):
            if lo < x < hi:
                return i_
        return None

    def coupe_rupture(xa, xb):
        """Partie de [xa, xb] hors ruptures (None si tout est dedans, l'intervalle si rien n'est coupé)."""
        for (lo, hi) in rups:
            if xb <= lo or xa >= hi:
                continue
            if xa < lo:
                return (xa, lo)
            if xb > hi:
                return (hi, xb)
            return None
        return (xa, xb)

    lierre = 0.7 if v == 3 else 0.5
    SOMBRES_P = (0.4, 0.15, 0.25, 0.2)         # poids de SOMBRES : foncé, noire, ombre, pierre

    # ---- piles ----
    moignons = {}
    with b.group("Piles"):
        for s in (-1, 1):
            for k, u in enumerate(centres):
                xc = s * u
                ir = casse(xc)
                if ir is not None:
                    moignons.setdefault(ir, []).append(xc)
                    continue
                b.box((xc - wp / 2 - 0.5, 0.0, -dz - 0.5), (xc + wp / 2 + 0.5, 3.0, dz + 0.5), vary("pierre_ombre", rng, 0.04),
                      studs="top", name="Socle")
                nv = (3.0, 12.0, 22.0, y_imp - 1.0)
                for j in range(3):
                    if j == 0:
                        col = _ton(rng, ("pierre_ombre", "pierre_fonce", "pierre"), (0.35, 0.45, 0.2), 0.04)
                    else:
                        col = _ton(rng, SOMBRES, SOMBRES_P, 0.04)
                    b.box((xc - wp / 2, nv[j], -dz), (xc + wp / 2, nv[j + 1], dz), col, name="Pile")
                ia, ib = xc - wp / 2 - 0.4, xc + wp / 2 + 0.4
                if k == 0:                                     # piles du couloir : imposte affleurante côté couloir
                    ia, ib = (xc - wp / 2, ib) if s > 0 else (ia, xc + wp / 2)
                b.box((ia, y_imp - 1.0, -dz - 0.4), (ib, y_imp, dz + 0.4), c("pierre_pale") if k == 0 else
                      vary("pierre", rng, 0.03), name="Imposte")
        # culées pleines aux deux bouts (elles s'enfoncent dans les falaises)
        u_fin = centres[-1] + wp / 2
        for s in (-1, 1):
            xa, xb = sorted((s * (u_fin + 0.5), s * X))       # le socle de la dernière pile déborde déjà de 0,5
            b.box((xa, 0.0, -dz - 0.5), (xb, 3.0, dz + 0.5), vary("pierre_ombre", rng, 0.04), studs="top", name="Socle")
            xa, xb = sorted((s * u_fin, s * X))
            for (ya, yb) in ((3.0, 18.0), (18.0, 36.0), (36.0, y_cor)):
                b.box((xa, ya, -dz), (xb, yb, dz), _ton(rng, SOMBRES, SOMBRES_P, 0.04), name="Culee")
        # moignons dans les ruptures
        for ir, lst in sorted(moignons.items()):
            for i, xc in enumerate(sorted(lst, key=abs)):
                hm = (30.0, 18.0, 24.0, 20.0)[i % 4] if ir == 0 else (22.0, 16.0)[i % 2]
                b.box((xc - wp / 2 - 0.5, 0.0, -dz - 0.5), (xc + wp / 2 + 0.5, 3.0, dz + 0.5),
                      vary("pierre_ombre", rng, 0.04), studs="top", name="Socle")
                b.box((xc - wp / 2, 3.0, -dz), (xc + wp / 2, hm * 0.55, dz), _ton(rng, SOMBRES), studs="top", name="Moignon")
                b.box((xc - wp / 2, hm * 0.55, -dz), (xc + 0.5, hm * 0.85, dz), _ton(rng, SOMBRES), studs="top",
                      name="Moignon")
                b.box((xc + 0.5, hm * 0.55, -dz + 1.0), (xc + wp / 2, hm - 0.5, dz), _ton(rng, SOMBRES), studs="top",
                      name="Moignon")
                b.part("block", (4.2, 2.6, 6.0), (xc - 2.0, hm * 0.85 + 0.9, -1.0), rot_z(14.0) @ rot_y(9.0),
                       _ton(rng, SOMBRES), studs="top", name="Moignon")

    # ---- arches ----
    claves = []
    with b.group("Arches"):
        # arche centrale surbaissée au-dessus du couloir : la seule ligne claire de l'aqueduc
        claves += _arc(b, rng, -o2, o2, dessous, f_cen, "seg", t_cen - 1.0, -dz - 0.4, dz + 0.4, 33, y_cor,
                       y_pied=y_imp, dedans=True, claveaux=("pierre_claire", "pierre_fonce"),
                       mur=("pierre_fonce", "pierre_ombre", "pierre"), z_mur=(-zt + 0.2, zt - 0.2),
                       archivolte=(1.0, "pierre_pale", 0.25))
        # mousse qui pend de l'arche centrale (toujours au-dessus de 37 au-dessus du couloir)
        for (xm_, zs, drop) in ((-31.0, 1, 3.5), (-9.0, 1, 4.5), (17.0, 1, 3.0), (-22.0, -1, 4.0), (6.0, -1, 3.5),
                                (29.0, -1, 4.5)):
            yb_ = _courbe(xm_, -o2, o2, dessous, f_cen, "seg") - 0.6
            y_bas = max(37.0, yb_ - drop)
            za, zb_ = sorted((zs * (dz + 0.65), zs * (dz + 0.2)))
            b.box((xm_ - 0.8, y_bas, za), (xm_ + 0.9, yb_ + 2.4, zb_), vary("mousse", rng, 0.08), name="Mousse", **DECO)
            za, zb_ = sorted((zs * (dz + 0.8), zs * (dz + 0.3)))
            b.box((xm_ + 0.2, y_bas + 1.2, za), (xm_ + 1.7, yb_ + 1.6, zb_), vary("lierre", rng, 0.08), name="Mousse", **DECO)
        # losange de lumière violette sur la clé (magie des mages, aucune étoile)
        for zs in (-1, 1):
            zf_ = zs * (dz + 0.4 + 0.3)
            for (tt, col, ep_) in ((1.5, "obsidienne", 0.12), (0.95, "lueur_violette", 0.24)):
                b.part("block", (tt, tt, ep_), (0.0, y_cor - 1.6, zf_ + zs * (ep_ / 2 - 0.02)), rot_z(45.0), c(col),
                       name="Losange", **(NEON if col.startswith("lueur") else DECO))
        for s in (-1, 1):
            for k in range(len(centres) - 1):
                ua, ub = centres[k] + wp / 2, centres[k + 1] - wp / 2
                xl, xr = sorted((s * ua, s * ub))
                reach = _portee(xl, xr, (xr - xl) / 2, "seg", t_lat)
                xm = 0.5 * (xl + xr)
                part = coupe_rupture(xm - reach, xm + reach)
                if part is None:
                    continue
                coupe = None if part == (xm - reach, xm + reach) else part
                if coupe is not None:
                    # bout cassé : tympans en escalier
                    bord = coupe[1] if coupe[1] < xm + reach - 1e-6 else coupe[0]

                    def rempl(xa, xb, bord=bord):
                        dd = min(abs(xa - bord), abs(xb - bord))
                        return y_cor if dd > 4.0 else (y_cor - 2.5 if dd > 1.8 else y_cor - 5.5)
                else:
                    rempl = y_cor
                claves += _arc(b, rng, xl, xr, y_imp, (xr - xl) / 2, "seg", t_lat, -dz, dz, 9, rempl, z_mur=(-zt, zt),
                               x_coupe=coupe, claveaux=("pierre", "pierre_ombre"),
                               mur=("pierre_fonce", "pierre_ombre", "pierre_noire", "pierre"))
        # remplissages au-dessus des piles, entre les extrados de deux arches voisines
        reach_c = _portee(-o2, o2, f_cen, "seg", t_cen)
        lat = []
        for k in range(len(centres) - 1):
            ua, ub = centres[k] + wp / 2, centres[k + 1] - wp / 2
            lat.append((0.5 * (ua + ub), _portee(ua, ub, (ub - ua) / 2, "seg", t_lat)))
        for s in (-1, 1):
            for k, u in enumerate(centres):
                ga = reach_c if k == 0 else lat[k - 1][0] + lat[k - 1][1]
                gb = lat[k][0] - lat[k][1] if k < len(lat) else u + wp / 2
                if gb - ga < 0.2 or casse(s * u) is not None:
                    continue
                xa, xb = sorted((s * ga, s * gb))
                b.box((xa, y_imp, -dz), (xb, y_cor, dz), _ton(rng, SOMBRES, SOMBRES_P, 0.04), name="Pilastre")

    # ---- corniche, tablier, parapets, canal ----
    def sections(a, bb):
        """Tronçons du tablier [(xa, xb)] entre les ruptures : marge `a` au bord intérieur (côté couloir) de chaque
        brèche, `bb` au bord extérieur (signes en miroir pour une brèche à gauche)."""
        out, cur = [], -X
        for (lo, hi) in sorted(rups):
            ga, gb = (a, bb) if lo > 0 else (-bb, -a)
            out.append((cur, lo + ga))
            cur = hi + gb
        out.append((cur, X))
        return out

    baies = sorted(set([-X] + [s * u for s in (-1, 1) for u in centres] + [X]))
    travees = list(zip(baies[:-1], baies[1:]))

    def chute(xa, xb):
        """Affaissement de la travée qui contient [xa, xb]."""
        xm_ = 0.5 * (xa + xb)
        for (ta, tb), d_ in affaisse.items():
            if ta - 1e-6 <= xm_ <= tb + 1e-6:
                return d_
        return 0.0

    def morceaux(xa_s, xb_s):
        """Tronçon [xa_s, xb_s] coupé aux travées : [(i, xa, xb, affaissement)]."""
        out = []
        for i, (ta, tb) in enumerate(travees):
            xa, xb = max(ta, xa_s), min(tb, xb_s)
            if xb - xa >= 0.3:
                out.append((i, xa, xb, chute(ta, tb)))
        return out

    with b.group("Tablier"):
        for (xa, xb) in sections(-1.8, 2.0):
            b.box((xa, y_cor, -dz - 1.0), (xb, y_tab, dz + 1.0), vary("pierre_fonce", rng, 0.03), studs="top", name="Corniche")
        for (xa_s, xb_s) in sections(0.6, -1.4):
            for (i, xa, xb, d_) in morceaux(xa_s, xb_s):
                b.box((xa, y_tab, -dz), (xb, y_par - d_, dz), _ton(rng, SOMBRES, SOMBRES_P, 0.04), name="Tablier")
        for (zs, marges) in ((-1, (-1.0, 1.0)), (1, (2.2, -2.6))):
            for (xa_s, xb_s) in sections(*marges):
                for (i, xa, xb, d_) in morceaux(xa_s, xb_s):
                    if min(abs(xa), abs(xb)) >= 60.0 and (i + (1 if zs > 0 else 0)) % 3 == 0:
                        continue                                # parapet tombé (une travée sur trois)
                    za, zb_ = sorted((zs * dz, zs * (dz - 1.4)))
                    b.box((xa, y_par - d_, za), (xb, hauteur - d_, zb_), _ton(rng, ("pierre_fonce", "pierre_ombre", "pierre"),
                                                                             (0.45, 0.3, 0.25), 0.04), studs="top",
                          name="Parapet")
        for (xa_s, xb_s) in sections(1.0, 3.0):
            runs = []
            for (i, xa, xb, d_) in morceaux(xa_s, xb_s):
                if runs and abs(runs[-1][2] - d_) < 1e-6 and abs(runs[-1][1] - xa) < 1e-6:
                    runs[-1][1] = xb
                else:
                    runs.append([xa, xb, d_])
            for (xa, xb, d_) in runs:
                b.box((xa, y_par - d_, -(dz - 1.4)), (xb, y_par - d_ + 0.8, dz - 1.4), c("eau"), name="Canal")

    # ---- cascade, flaque, éboulis, cicatrices ----
    for ir, (lo, hi) in enumerate(rups):
        sx = 1 if lo > 0 else -1                    # sens vers l'extérieur
        xg = lo if lo > 0 else hi                   # bord intérieur (côté couloir)
        xd = hi if lo > 0 else lo                   # bord extérieur
        if ir == 0:
            with b.group("Cascade"):
                eau = dict(material="Glass", transparency=0.15, collide=False, shadow=False)
                clair = tuple(int(round(x + (y - x) * 0.3)) for x, y in zip(c("eau_claire"), c("blanc")))
                for (a0, a1, ya, yb, hz) in ((1.0, 3.4, 40.0, y_par + 0.8, 3.1), (1.4, 4.4, 20.5, 40.4, 3.4),
                                             (1.8, 5.6, 0.4, 20.9, 3.8)):
                    xa, xb = sorted((xg + sx * a0, xg + sx * a1))
                    b.box((xa, ya, -hz), (xb, yb, hz), clair, name="Cascade", **eau)
                xa, xb = sorted((xg + sx * 0.4, xg + sx * 1.6))
                b.box((xa, y_par + 0.3, -3.3), (xb, y_par + 1.3, 3.3), _ecume(), name="Ecume", **DECO)
                for (a0, a1, hz, yh) in ((0.4, 6.0, 3.6, 1.4), (1.6, 4.8, 4.6, 2.4)):
                    xa, xb = sorted((xg + sx * a0, xg + sx * a1))
                    b.box((xa, 0.2, -hz), (xb, yh, hz), _ecume(), name="Ecume", **DECO)
                xa, xb = sorted((xg - sx * 4.0, xg + sx * 9.0))
                b.box((xa, 0.0, -6.5), (xb, 0.2, 6.5), c("eau"), name="Flaque", **DECO)
        with b.group("Bouts"):
            for (xe, sgn_e) in ((xg, sx), (xd, -sx)):
                b.part("block", (3.2, 2.6, 5.4), (xe - sgn_e * 0.6, y_tab - 0.6, -1.9), rot_z(-sgn_e * 24.0) @ rot_y(8.0),
                       _ton(rng, SOMBRES), studs="top", name="BlocPenche")
        n_pts = 15 if ir == 0 else 9
        pts = []
        for i in range(n_pts):
            u = float(rng.uniform(abs(xg) + 5.0, abs(xd) - 4.0))
            pts.append((sx * u, float(rng.uniform(-6.0, 6.0))))
        with b.group("Eboulis"):
            nc = 5 if ir == 0 else 3
            _eboulis(b, rng, pts[:nc], SOMBRES, (1.2, 2.2))
            for (x, z) in pts[nc:nc + 4]:
                _bloc_pose(b, (x, z), (float(rng.uniform(4.0, 6.5)), float(rng.uniform(2.5, 3.5)), float(rng.uniform(5.0, 8.0))),
                           _ton(rng, SOMBRES), yaw=float(rng.uniform(0, 90)),
                           tilt=(float(rng.uniform(-18, 18)), float(rng.uniform(-18, 18))), name="Bloc", **DECO)
            _eboulis(b, rng, pts[nc + 4:], SOMBRES, (1.0, 2.2))
        with b.group("Cicatrices"):
            stubs = sorted(moignons.get(ir, []), key=abs)
            for xc in stubs[:1]:
                with b.at((xc, 0.0, dz), yaw=180.0):
                    _cicatrice(b, rng, 0.8, 7.0, 15.5 if ir == 0 else 11.0, 0.0, 1.6)
            if ir == 0:
                avant = [u for u in centres if u < abs(xg)]
                apres = [u for u in centres if u > abs(xd)]
                if apres:
                    with b.at((sx * apres[0], 0.0, dz), yaw=180.0):
                        _cicatrice(b, rng, -0.6, 12.0, 22.0, 0.0, 1.4)
                if avant:
                    with b.at((sx * avant[-1], 0.0, -dz)):
                        _cicatrice(b, rng, 0.5, 15.0, 24.0, 0.0, 1.3)

    # ---- lierre et mousse qui pendent des arches (jamais au-dessus du couloir sous `dessous`) ----
    with b.group("Lierre"):
        for (xa, xb, y0, y1) in claves:
            if abs(xa) < o2 + 1 or abs(xb) < o2 + 1 or rng.random() > lierre:
                continue
            if y0 < y_imp + 4.0:
                continue
            for zs in (-1, 1):
                if rng.random() < 0.5:
                    continue
                drop = float(rng.uniform(2.0, 5.5))
                za, zb_ = sorted((zs * (dz + 0.45), zs * (dz - 0.1)))      # devant la clé (saillie 0,3) de 0,15
                b.box((xa + 0.2, y0 - drop, za), (min(xb - 0.2, xa + 1.6), y0 + 1.0, zb_), vary("mousse", rng, 0.08),
                      name="Mousse", **DECO)
        for s in (-1, 1):
            for u in centres:
                xc = s * u
                if casse(xc) is not None or rng.random() > lierre + 0.2:
                    continue
                zs = 1 if rng.random() < 0.65 else -1
                hl = float(rng.uniform(8.0, 22.0))
                xm = xc + float(rng.uniform(-2.5, 2.5))
                za, zb_ = sorted((zs * (dz + 0.3), zs * (dz - 0.12)))
                b.box((xm - 1.2, 3.0, za), (xm + 1.0, hl, zb_), vary("lierre", rng, 0.07), name="Lierre", **DECO)
                za, zb_ = sorted((zs * (dz + 0.42), zs * (dz - 0.12)))
                b.box((xm - 1.9, hl - 3.0, za), (xm + 0.6, hl + 0.8, zb_), vary("lierre_clair", rng, 0.07), name="Lierre", **DECO)
    return {"emprise": (largeur, 2 * dz + 2.0), "hauteur": hauteur}


def _ecume() -> tuple:
    """Écume claire au pied de la cascade."""
    a, bb = c("eau_claire"), c("blanc")
    return tuple(int(round(x + (y - x) * 0.35)) for x, y in zip(a, bb))
