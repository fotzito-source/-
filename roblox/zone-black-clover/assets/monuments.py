"""Monuments de la zone Black Clover : les grands repères de la première moitié.

- `colline_crane` : colline boisée sombre en terrasses (plateau sommital où zone.py pose le crâne) ;
- `crane_demon` : crâne de démon cornu, ivoire fissuré, à moitié enterré (refBC1) ;
- `cotes_geantes` : cage thoracique du démon qui sort des labours ;
- `tour_grimoires` : tour ronde claire, baies lumineuses, spirale de grimoires volants ;
- `montagne_capitale` : montagne couronnée d'un château clair, silhouette lointaine (refBC5).

Conventions : origine au centre de l'emprise au sol, avant vers -Z local (voir CONVENTIONS.md, SPECS.md).
Propriété intellectuelle : crâne à deux orbites, aucune statue ni figure, étendard uni, tour sans nom, grimoires
à couvertures unies, aucun trèfle, aucune étoile, aucun texte hors liste.
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, rot_x, rot_z, shade
from palette import c, os_teinte, vary
from textures import mask_rects

DECO = dict(collide=False)
FIN = dict(collide=False, shadow=False)
NEON = dict(material="Neon", collide=False, shadow=False)


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

def _rng(variant: int, sel: int) -> np.random.Generator:
    """Aléatoire propre à l'asset et à sa variante (indépendant de l'ordre des poses)."""
    return np.random.default_rng(7919 * (variant + 1) + sel)


def _frame(d, ref=(0.0, 1.0, 0.0)):
    """Longueur de d et rotation dont l'axe X suit d, l'axe Y aussi proche que possible de `ref`."""
    d = np.asarray(d, float)
    n = float(np.linalg.norm(d))
    x = d / n
    r = np.asarray(ref, float)
    y = r - float(np.dot(r, x)) * x
    if np.linalg.norm(y) < 1e-6:
        r = np.array([1.0, 0.0, 0.0]) if abs(x[0]) < 0.9 else np.array([0.0, 0.0, 1.0])
        y = r - float(np.dot(r, x)) * x
    y /= np.linalg.norm(y)
    z = np.cross(x, y)
    return n, np.column_stack([x, y, z])


def _poutre(b, a, bb, ep, col, ep_z=None, ref=(0.0, 1.0, 0.0), ext=0.0, roll=0.0, name="Poutre", **kw):
    """Bloc de section ep × ep_z tendu de a à bb (prolongé de `ext` à chaque bout), tourné de `roll` sur son axe."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    n, R = _frame(bb - a, ref)
    if roll:
        R = R @ rot_x(roll)
    u = (bb - a) / n
    a2, b2 = a - u * ext, bb + u * ext
    return b.part("block", (n + 2 * ext, ep, ep if ep_z is None else ep_z), (a2 + b2) / 2, R, col, name=name, **kw)


def _voxels(b, codes, xe, ye, ze, couleurs, rng, var=0.025, name="Os", **kw) -> int:
    """Modèle en voxels → blocs : découpe gloutonne de chaque tranche horizontale par code, puis fusion verticale
    des rectangles identiques d'une tranche à l'autre. codes[i, j, k] (x, y, z), 0 = vide. Renvoie le nombre de blocs."""
    nx, ny, nz = codes.shape
    actifs: dict = {}
    sortie = []
    for j in range(ny):
        cur = set()
        sl = codes[:, j, :]
        for code in np.unique(sl):
            if code == 0:
                continue
            m = sl == code
            r1 = mask_rects(m.T)                                     # (i, k, w, h)
            r2 = [(r[1], r[0], r[3], r[2]) for r in mask_rects(m)]   # même repère, autre sens de balayage
            for (i, k, w, h) in (r1 if len(r1) <= len(r2) else r2):
                cur.add((int(code), i, k, w, h))
        for key in sorted(actifs):
            if key not in cur:
                sortie.append((key, actifs.pop(key), j))
        for key in sorted(cur):
            if key not in actifs:
                actifs[key] = j
    for key in sorted(actifs):
        sortie.append((key, actifs[key], ny))
    for (code, i, k, w, h), j0, j1 in sortie:
        col = couleurs[code]
        if var:
            col = vary(col, rng, var)
        b.box((xe[i], ye[j0], ze[k]), (xe[i + w], ye[j1], ze[k + h]), col, name=name, **kw)
    return len(sortie)


# ---------------------------------------------------------------------------
# Crâne de démon cornu (refBC1)
# ---------------------------------------------------------------------------

# Codes des voxels du crâne
OS_CLAIR, OS, OS_OMBRE, OS_FONCE, OS_MI, OS_BRULE, FOND = 1, 2, 3, 4, 5, 6, 7


def _crane_grille():
    """Grille de conception (crâne de 64 de haut) : arêtes des cellules de 2 studs."""
    xe = np.arange(-32.0, 32.01, 2.0)
    ye = np.arange(0.0, 64.01, 2.0)
    ze = np.arange(-30.0, 28.01, 2.0)
    return xe, ye, ze


def _crane_codes(xe, ye, ze, variant: int):
    xc, yc, zc = (xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2, (ze[:-1] + ze[1:]) / 2
    X, Y, Z = np.meshgrid(xc, yc, zc, indexing="ij")
    AX = np.abs(X)

    def se(cx, cy, cz, rx, ry, rz, n, x=X):
        return np.abs((x - cx) / rx) ** n + np.abs((Y - cy) / ry) ** n + np.abs((Z - cz) / rz) ** n

    voute = np.where(Y >= 36, se(0, 36, 1, 28, 28, 25, 2.6), se(0, 36, 1, 28, 31, 25, 2.4)) <= 1
    face = se(0, 17, -10, 24, 17, 17.5, 2.9) <= 1
    pommettes = se(19.5, 23.5, -18, 5.0, 3.4, 8.0, 2.4, x=AX) <= 1
    arcade = se(11.5, 37.4, -19.5, 10.5, 3.2, 8.0, 2.6, x=AX) <= 1
    machoire = se(0, -3, -7, 19, 4.5, 20, 2.6) <= 1
    plein = voute | face | pommettes | arcade | machoire

    # creux : deux grandes orbites (bord intérieur un peu abaissé : regard dur), cavité nasale en cœur renversé
    # (pointe en haut, deux lobes de part et d'autre de la cloison), bouche sombre derrière les dents
    orbite = ((((AX - 11.8) / 7.6) ** 2 + ((Y - 29.5) / 7.0) ** 2) <= 1.0) & (Y <= 34.8 + 0.3 * (AX - 11.8))
    nez = (((Y > 24) & (Y < 26) & (AX < 2)) | ((Y > 20) & (Y < 24) & (AX < 4)) | ((Y > 18) & (Y < 20) & (AX < 6))
           | ((Y > 16) & (Y < 18) & (AX > 2) & (AX < 6)) | ((Y > 14) & (Y < 16) & (AX > 2) & (AX < 4)))
    bouche = (Y >= 1) & (Y <= 8) & (AX <= 16)
    creux = orbite | nez | bouche
    plein &= ~(creux & (Z < -20))
    fond = plein & creux & (Z < -18)

    # teintes : ivoire en haut, ombré sous les pommettes, noirci au ras de la colline (os_brule)
    codes = np.zeros(X.shape, np.int8)
    base = np.select([Y < 2, Y < 4, Y < 7, Y < 13, Y < 50], [OS_BRULE, OS_MI, OS_FONCE, OS_OMBRE, OS], OS)
    codes[plein] = base[plein]
    codes[fond] = FOND
    return codes, (xc, yc, zc)


def _front_z(codes, xe, ze, i, j):
    """z de la face avant (la plus en -Z) de la colonne (i, j) du crâne, ou None."""
    col = np.nonzero(codes[i, j, :])[0]
    return None if len(col) == 0 else float(ze[col[0]])


def _fissures(b, codes, xe, ye, ze, lignes, k, col, larg=0.5, saillie=0.2, noyau=0.1, name="Fissure") -> int:
    """Fissures en saillie de 0,2 sur les faces avant du crâne en voxels : chaque ligne brisée (vue de face, en unités
    de conception) est coupée aux bords des cellules et chaque morceau est posé contre la face de sa cellule."""
    n = 0
    for pts in lignes:
        morceaux = []
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            # coupe le segment aux bords de cellules (x et y)
            ts = {0.0, 1.0}
            for e in xe:
                if (x0 - e) * (x1 - e) < 0:
                    ts.add((e - x0) / (x1 - x0))
            for e in ye:
                if (y0 - e) * (y1 - e) < 0:
                    ts.add((e - y0) / (y1 - y0))
            ts = sorted(ts)
            for ta, tb in zip(ts[:-1], ts[1:]):
                pa = (x0 + (x1 - x0) * ta, y0 + (y1 - y0) * ta)
                pb = (x0 + (x1 - x0) * tb, y0 + (y1 - y0) * tb)
                xm, ym = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
                i = int(np.searchsorted(xe, xm) - 1)
                j = int(np.searchsorted(ye, ym) - 1)
                if not (0 <= i < codes.shape[0] and 0 <= j < codes.shape[1]):
                    continue
                kk = np.nonzero(codes[i, j, :])[0]
                if len(kk) == 0 or codes[i, j, kk[0]] == FOND:
                    continue
                morceaux.append((pa, pb, float(ze[kk[0]])))
        # fusionne les morceaux consécutifs alignés sur la même face
        fus = []
        for m in morceaux:
            if fus and fus[-1][2] == m[2] and np.allclose(fus[-1][1], m[0]):
                d0 = np.subtract(fus[-1][1], fus[-1][0])
                d1 = np.subtract(m[1], m[0])
                if abs(d0[0] * d1[1] - d0[1] * d1[0]) < 1e-6:
                    fus[-1] = (fus[-1][0], m[1], m[2])
                    continue
            fus.append(m)
        for pa, pb, zf in fus:
            dx, dy = (pb[0] - pa[0]) * k, (pb[1] - pa[1]) * k
            L = math.hypot(dx, dy)
            if L < 0.3:
                continue
            ang = math.degrees(math.atan2(dy, dx))
            ctr = ((pa[0] + pb[0]) / 2 * k, (pa[1] + pb[1]) / 2 * k, zf * k + (noyau - saillie) / 2)
            b.part("block", (L + larg * 0.6, larg, saillie + noyau), ctr, rot_z(ang), col, name=name, **FIN)
            n += 1
    return n


def _dent(b, xa, xb, y_haut, y_pointe, za, zb, col, hp=None, vers_bas=True, name="Dent"):
    """Dent : corps + pointe en V (deux coins). vers_bas : pointe en bas (mâchoire supérieure)."""
    w = xb - xa
    hp = min(hp if hp is not None else 0.9 * w, abs(y_haut - y_pointe) * 0.7)
    xm = (xa + xb) / 2
    if vers_bas:
        b.box((xa, y_pointe + hp, za), (xb, y_haut, zb), col, name=name)
        b.wedge_under((xa, y_pointe, za), (xm, y_pointe + hp, zb), col, down="-x", name=name)
        b.wedge_under((xm, y_pointe, za), (xb, y_pointe + hp, zb), shade(col, 0.93), down="+x", name=name)
    else:
        b.box((xa, y_haut, za), (xb, y_pointe - hp, zb), col, name=name)
        b.wedge((xa, y_pointe - hp, za), (xm, y_pointe, zb), col, down="-x", name=name)
        b.wedge((xm, y_pointe - hp, za), (xb, y_pointe, zb), shade(col, 0.93), down="+x", name=name)


def _spline(ctrl, n):
    """Courbe de Catmull-Rom passant par les points de contrôle, échantillonnée en n segments."""
    P = [np.asarray(p, float) for p in ctrl]
    P = [2 * P[0] - P[1]] + P + [2 * P[-1] - P[-2]]
    seg = len(P) - 3
    out = []
    for m in range(n + 1):
        u = m / n * seg
        i = min(int(u), seg - 1)
        t = u - i
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return out


def _corne(b, ctrl, s0, s1, n, rng, ref=(0.0, 0.0, 1.0), torsion=3.0, anneaux=(2, 4, 6), name="Corne") -> None:
    """Corne : courbe lisse (Catmull-Rom) découpée en n blocs tendus de point à point (prolongés pour fermer les
    coudes), section décroissante de s0 à s1, légère torsion, dégradé os → os_fonce vers la pointe, anneaux de
    croissance en saillie de 0,25 à quelques coudes."""
    pts = _spline(ctrl, n)
    dirs = [(pts[i + 1] - pts[i]) / np.linalg.norm(pts[i + 1] - pts[i]) for i in range(n)]
    for i in range(n):
        t = i / max(1, n - 1)
        col = os_teinte(0.06 + 0.66 * t ** 1.4)
        s = s0 + (s1 - s0) * t ** 0.9
        roll = torsion * (1 if i % 2 else -1)
        _poutre(b, pts[i], pts[i + 1], s, vary(col, rng, 0.015), ref=ref, ext=s * 0.3 if i else 0.0, roll=roll,
                name=name)
        if i in anneaux:
            d = dirs[i - 1] + dirs[i]
            d /= np.linalg.norm(d)
            sp = s0 + (s1 - s0) * ((i - 1) / max(1, n - 1)) ** 0.9
            _poutre(b, pts[i] - d * 0.6, pts[i] + d * 0.6, sp + 0.5, shade(col, 0.86), ref=ref, roll=roll * 0.5,
                    name="Anneau", **DECO)


def crane_demon(b, variant: int = 0, hauteur: float = 64) -> dict:
    """Crâne de démon cornu, ivoire fissuré, mâchoire inférieure à moitié enterrée (refBC1).

    Origine : centre de l'emprise au niveau du plateau de la colline (y = 0) ; la face regarde -Z local.
    Volume en voxels de 2 studs (tranches horizontales en gradins), deux orbites profondes à braise cramoisie,
    cavité nasale en cœur renversé, pommettes, crocs, deux grandes cornes recourbées, petites pointes, fissures,
    étendard cramoisi uni et déchiré au sommet (aucune statue, aucune figure, pas de troisième orbite)."""
    rng = _rng(variant, 101)
    k = hauteur / 64.0
    xe, ye, ze = _crane_grille()
    codes, _ = _crane_codes(xe, ye, ze, variant)
    couleurs = {OS_CLAIR: c("os_clair"), OS: c("os"), OS_OMBRE: c("os_ombre"), OS_FONCE: c("os_fonce"),
                OS_MI: os_teinte(0.75), OS_BRULE: c("os_brule"), FOND: c("noir")}
    S = lambda p: tuple(float(v) * k for v in p)        # noqa: E731  (conception → studs)
    ye_s = ye * k
    ye_s[0] = -0.6                                       # la tranche du bas s'enfonce un peu dans le plateau
    with b.group("Crane"):
        _voxels(b, codes, xe * k, ye_s, ze * k, couleurs, rng, var=0.035, name="Os")

    # --- fissures (sombres, en saillie) et éclats ----------------------------------------------------
    lignes = [
        [(9, 37), (6, 42), (9, 46.5), (5, 51), (8, 55.5), (6, 59)],
        [(-14, 37.5), (-17, 42), (-13, 46), (-16, 50.5), (-13.5, 54)],
        [(-17, 46), (-22, 48.5), (-24.5, 44)],
        [(19.5, 26), (23, 30.5), (21.5, 35)],
        [(-16, 22.5), (-20, 18.5), (-17.5, 13.5)],
        [(1, 26.5), (2.5, 30), (-0.5, 33.5), (1.5, 37)],
        [(13.5, 12.5), (17, 16.5), (20.5, 13.5)],
        [(5, 51), (0, 53.5), (-3, 57.5)],
        [(15, 39), (19, 43), (23.5, 42)],
        [(-7, 14), (-10, 11)],
    ]
    taches = [[(7, 44), (8, 50), (6.5, 56)], [(-15, 43), (-15, 49)], [(21, 29), (21.5, 34)], [(-18, 20), (-18, 15)]]
    with b.group("Fissures"):
        _fissures(b, codes, xe, ye, ze, taches, k, c("os_ombre"), larg=2.6, saillie=0.1, noyau=0.05, name="Tache")
        _fissures(b, codes, xe, ye, ze, lignes, k, c("fissure"))

    # --- braises au fond des orbites -------------------------------------------------------------
    with b.group("Braises"):
        # lit de braises au fond de l'orbite : lueur vive en bas du mur du fond, halo cramoisi sombre au-dessus
        for s in (-1, 1):
            cx = s * 11.8
            b.box(S((cx - 3.6, 24.2, -20.5)), S((cx + 3.6, 26.6, -20.0)), c("feu_cramoisi"), name="Braise", **NEON)
            b.box(S((cx - 1.8, 26.6, -20.3)), S((cx + 1.4, 27.8, -20.0)), c("lueur_cramoisie"), name="Braise", **NEON)
            b.box(S((cx - 4.4, 22.4, -23.0)), S((cx + 4.4, 24.2, -20.0)), c("cramoisi_fonce"), name="Braise", **DECO)
            b.box(S((cx - 2.6, 24.2, -21.6)), S((cx + 1.0, 25.4, -20.5)), c("feu"), name="Braise", **NEON)

    # --- dents ------------------------------------------------------------------------------------
    j8 = int(np.searchsorted(ye, 8.0))           # rangée du maxillaire juste au-dessus de la bouche
    with b.group("Dents"):
        hautes = [(1.6, 2.8, 4.2, "i"), (4.7, 2.8, 4.6, "i"), (7.9, 3.0, -0.8, "croc"), (11.1, 2.8, 4.0, "p"),
                  (14.1, 2.6, 1.4, "croc")]
        casse = 1 if variant % 2 == 0 else -1
        for s in (-1, 1):
            for (xm, w, ybas, kind) in hautes:
                x = s * xm
                i = int(np.searchsorted(xe, x) - 1)
                zf = _front_z(codes, xe, ze, i, j8) or -26.0
                za, zb = zf + 0.4, -20.4
                col = c("os_clair") if kind == "croc" else vary(c("os"), rng, 0.03)
                if kind == "croc" and s == casse and xm > 10:          # croc cassé net, éclat sombre
                    b.box(S((x - w / 2, 4.4, za)), S((x + w / 2, 8.0, zb)), shade(col, 0.95), name="CrocCasse")
                    b.box(S((x - w / 2 + 0.4, 3.6, za + 0.3)), S((x + w / 2 - 0.8, 4.4, zb)), c("os_ombre"),
                          name="CrocCasse")
                else:
                    _dent(b, *S((x - w / 2, x + w / 2)), 8.0 * k, ybas * k, za * k, zb * k, col)
        basses = [(2.0, 2.4, 3.0), (5.4, 2.6, 2.4), (8.9, 2.4, 3.4), (12.2, 2.4, 2.2)]
        for s in (-1, 1):
            for n_, (xm, w, yh) in enumerate(basses):
                x = s * xm + float(rng.uniform(-0.3, 0.3))
                col = os_teinte(0.55 + 0.1 * n_)
                with b.at(S((x, 0, -23.2)), yaw=float(rng.uniform(-9, 9))):
                    _dent(b, *S((-w / 2, w / 2)), -1.5 * k, yh * k, *S((-1.6, 1.6)), col, vers_bas=False)

    # --- mousse et terre au pied (la mâchoire inférieure est enterrée ; les épaulements de la colline font le reste)
    with b.group("Terre"):
        for (x0, x1, h, z0, z1, nom) in ((-22, -12, 1.2, -29, -23, "mousse"), (12, 21, 0.9, -29.5, -24, "herbe_fonce"),
                                         (-4, 5, 0.5, -31, -27.5, "mousse")):
            b.box(S((x0, 0, z0)), S((x1, h, z1)), vary(nom, rng, 0.05), studs="top", name="Mousse", **DECO)

    # --- cornes et petites pointes --------------------------------------------------------------
    with b.group("Cornes"):
        # droite : sort de la tempe, s'écarte, monte et se recourbe vers l'avant, pointe vers l'intérieur ;
        # gauche : plus enroulée (asymétrie, refBC1)
        droite = [(17, 46, 3), (33, 51, 1), (46, 60, -2), (52.5, 75, -5.5), (50, 88, -7.5), (41, 95.5, -6)]
        gauche = [(-17, 46, 3), (-33, 51.5, 1.5), (-45, 61, -1), (-49, 76, -3.5), (-44, 87.5, -5), (-33.5, 91, -2.5)]
        if variant % 2:
            droite, gauche = [(-p[0], p[1], p[2]) for p in gauche], [(-p[0], p[1], p[2]) for p in droite]
        for n_, pts in enumerate((droite, gauche)):
            _corne(b, [S(p) for p in pts], 12.5 * k, 2.6 * k, 10, rng, torsion=3.0 if n_ == 0 else -3.0)
        pointes = [(((18, 3, -10), (30, 6, -9), (40, 11.5, -6.5), (46, 19, -4)), (4.0, 2.8, 1.6)),
                   (((24, 40, 7), (32, 44, 10), (37, 49.5, 13)), (3.2, 1.8)),
                   (((24, 22, -6), (31, 21, -5), (37, 23.5, -3)), (2.6, 1.5))]
        for s in (-1, 1):
            for (pts, secs) in pointes:
                q = [S((s * p[0], p[1], p[2])) for p in pts]
                for n_ in range(len(q) - 1):
                    _poutre(b, q[n_], q[n_ + 1], secs[n_] * k, os_teinte(0.15 + 0.25 * n_), ref=(0, 0, 1),
                            ext=0.3 * secs[n_] * k if n_ else 0.0, name="Pointe")

    # --- étendard cramoisi uni et déchiré au sommet ---------------------------------------------
    with b.group("Etendard"):
        base = np.array(S((-6.0, 57.0, -9.0)))
        top = base + np.array([1.2, 33.0, 1.5]) * k
        _poutre(b, base, top, 1.0 * k, c("bois_noir"), name="Mat", **DECO)
        haut = top - np.array([0, 1.4, 0]) * k
        _poutre(b, haut + np.array([-0.6, 0, 0]) * k, haut + np.array([10.6, 0, 0]) * k, 0.6 * k, c("bois_noir"),
                name="Traverse", **DECO)
        b.box(tuple(top + np.array([-0.4, 0, -0.4]) * k), tuple(top + np.array([0.4, 1.8, 0.4]) * k), c("fer"),
              name="Pointe", **FIN)
        x0, x1 = haut[0] + 0.5 * k, haut[0] + 10.0 * k
        y1 = haut[1] - 0.3 * k
        zt = haut[2]
        b.box((x0, y1 - 10.5 * k, zt - 0.1), (x1, y1, zt + 0.1), c("toile_cramoisie"), name="Toile", **DECO)
        b.box((x0, y1 - 1.2 * k, zt - 0.2), (x1, y1, zt - 0.1), c("toile_noire"), name="Liseré", **FIN)
        lw = (x1 - x0) / 4
        for n_, L in enumerate((4.2, 1.8, 5.2, 2.6)):
            col = shade(c("toile_cramoisie"), (0.92, 1.0, 0.86, 0.95)[n_])
            b.box((x0 + n_ * lw + 0.12, y1 - (10.5 + L) * k, zt - 0.1), (x0 + (n_ + 1) * lw - 0.12, y1 - 10.5 * k, zt + 0.1),
                  col, name="Lambeau", **DECO)
    return {"emprise": (round(112 * k, 1), round(60 * k, 1)), "hauteur": round(96 * k, 1)}


# ---------------------------------------------------------------------------
# Colline boisée du crâne
# ---------------------------------------------------------------------------

YAW_CRANE_REL = 35.0     # yaw du crâne (125) moins celui de la colline (90) dans zone.py


def _vers_colline(xs, zs, rel=YAW_CRANE_REL):
    """Repère du crâne (posé au centre du plateau, tourné de `rel`) → repère de la colline."""
    a = math.radians(rel)
    return math.cos(a) * xs + math.sin(a) * zs, -math.sin(a) * xs + math.cos(a) * zs


def colline_crane(b, variant: int = 0, largeur: float = 110, profondeur: float = 100, hauteur: float = 28) -> dict:
    """Colline boisée sombre en terrasses irrégulières (lobes, éperons), plateau sommital plat à y = hauteur où
    zone.py pose le crâne ; pente douce vers le couloir (-Z), raide derrière ; épaulements qui enveloppent les côtés
    et l'arrière du crâne (il paraît à moitié enfoui, refBC1) ; affleurements de roche noire, sapins sombres et
    arbres morts sur les flancs et l'arrière, os géants qui percent les pentes."""
    from assets import mobilier
    rng = _rng(variant, 202)
    H = float(hauteur)
    W2, P2 = largeur / 2, profondeur / 2
    cell = 4.0
    xe = np.arange(-W2, W2 + 0.01, cell)
    xe = xe if xe[-1] >= W2 - 0.01 else np.append(xe, W2)
    ze = np.arange(-P2, P2 + 0.01, cell)
    ze = ze if ze[-1] >= P2 - 0.01 else np.append(ze, P2)
    xc, zc = (xe[:-1] + xe[1:]) / 2, (ze[:-1] + ze[1:]) / 2
    X, Z = np.meshgrid(xc, zc, indexing="ij")
    TH = np.arctan2(Z, X)
    ph = 0.9 * variant
    lob = 1 + 0.11 * np.sin(3 * TH + 0.6 + ph) + 0.07 * np.sin(5 * TH + 2.0 - ph) + 0.05 * np.sin(2 * TH + 1.1)
    # terrasses : (dessus, demi-axe x, demi-axe z, centre z) ; plus larges vers le couloir (-Z), serrées derrière
    niveaux = [(H * 0.27, W2 * 0.98, P2 * 0.86, -P2 * 0.14), (H * 0.52, W2 * 0.84, P2 * 0.74, -P2 * 0.1),
               (H * 0.77, W2 * 0.7, P2 * 0.62, -P2 * 0.05), (H, max(32.0, W2 * 0.62), max(30.0, P2 * 0.58), 0.0)]
    masques = []
    for (yt, ax, az, cz) in niveaux:
        m = ((X / (ax * lob)) ** 2 + ((Z - cz) / (az * lob)) ** 2) <= 1.0
        if masques:
            m &= masques[-1]
        masques.append(m)
    masques[-1] |= (X ** 2 + Z ** 2) <= 30.0 ** 2          # plateau : rayon ≥ 26 autour de l'origine
    for m in masques[:-1]:
        m |= masques[-1]
    tons = [("herbe_fonce", "herbe"), ("herbe_fonce", "mousse"), ("mousse", "herbe_fonce"), ("herbe_fonce", "mousse")]
    y0 = 0.0
    with b.group("Terrasses"):
        for n_, ((yt, *_), m) in enumerate(zip(niveaux, masques)):
            for (i, kz, w, h) in mask_rects(m.T):
                col = vary(tons[n_][int(rng.integers(2))], rng, 0.05)
                b.box((xe[i], y0, ze[kz]), (xe[i + w], yt, ze[kz + h]), col, studs="top", name="Terrasse")
            y0 = yt

    # épaulements autour du crâne (repère du crâne : face vers -Z) : rien devant la face et les dents
    a = math.radians(YAW_CRANE_REL)
    XS = math.cos(a) * X - math.sin(a) * Z
    ZS = math.sin(a) * X + math.cos(a) * Z
    AXS = np.abs(XS)
    paliers = []
    for (dy, rx, rz, cz, x_libre, z_libre) in ((8.6, 46.0, 43.0, 2.0, 25.0, -16.0), (15.6, 41.0, 38.0, 6.0, 28.0, -8.0),
                                               (22.6, 36.0, 31.0, 13.0, 30.0, 4.0), (28.6, 30.0, 24.0, 20.0, 26.0, 12.0)):
        m = ((XS / (rx * lob)) ** 2 + ((ZS - cz) / (rz * lob)) ** 2) <= 1.0
        m &= ~((ZS < z_libre) & (AXS < x_libre))
        m &= masques[-1] | masques[-2]
        if paliers:
            m &= paliers[-1][1]
        paliers.append((H + dy, m))
    with b.group("Epaulements"):
        yb = H
        for n_, (yt, m) in enumerate(paliers):
            for (i, kz, w, h) in mask_rects(m.T):
                col = vary(("herbe_fonce", "sapin", "sapin_fonce", "sapin")[n_], rng, 0.05)
                b.box((xe[i], yb, ze[kz]), (xe[i + w], yt, ze[kz + h]), col, studs="top", name="Epaulement")
            yb = yt

    def niveau(x, z, epaulements=True) -> float:
        i = int(np.clip(np.searchsorted(xe, x) - 1, 0, len(xc) - 1))
        kz = int(np.clip(np.searchsorted(ze, z) - 1, 0, len(zc) - 1))
        y = 0.0
        for (yt, *_), m in zip(niveaux, masques):
            if m[i, kz]:
                y = yt
        for yt, m in paliers if epaulements else ():
            if m[i, kz]:
                y = yt
        return y

    def rebord(ang, n_min=1):
        """Point du bord extérieur d'une terrasse dans la direction `ang` (pour y enfoncer un rocher)."""
        best = None
        for r in np.arange(20.0, max(W2, P2) + 4, 2.0):
            x, z = r * math.cos(ang) * W2 / max(W2, P2), r * math.sin(ang) * P2 / max(W2, P2) - 4
            if abs(x) >= W2 or abs(z) >= P2:
                break
            y = niveau(x, z, epaulements=False)
            if best is not None and y < best[2] - 0.5 and abs(best[2] - niveaux[n_min - 1][0]) < 0.5:
                return (best[0] + x) / 2, (best[1] + z) / 2, best[2], y
            best = (x, z, y)
        return None

    # affleurements de roche noire : gros blocs enfoncés dans les ressauts des terrasses (côté couloir et flancs)
    with b.group("Rochers"):
        n_ok = 0
        for n_ in range(14):
            ang = math.pi * (1.05 + 0.9 * n_ / 13) + float(rng.uniform(-0.08, 0.08)) + 0.3 * ph
            r = rebord(ang, (2, 3, 1, 2, 4, 3, 1)[n_ % 7])
            if r is None:
                continue
            x, z, yh, yb = r
            s_ = float(rng.uniform(6, 9.5))
            if z - s_ * 0.5 < -P2:
                continue
            col = vary(("roche_noire", "basalte", "basalte_clair")[n_ % 3], rng, 0.05)
            b.boxc((x, yb + (yh - yb) * 0.5 - 0.4, z), (s_, (yh - yb) + 2.2, s_ * 0.75), col, yaw=float(rng.uniform(12, 78)),
                   studs="top", name="Roche")
            n_ok += 1
            if n_ok >= 9:
                break

    # sapins sombres (épaulements, flancs, arrière) et arbres morts (devant, sur les côtés)
    with b.group("Arbres"):
        dans_crane = [(-36, -14, 30), (37, -10, 28), (-40, 6, 27), (42, 10, 26), (-28, 26, 32), (30, 26, 30),
                      (-12, 36, 30), (12, 37, 31), (0, 40, 26)]
        places = [(_vers_colline(xs, zs) + (h, "s")) for (xs, zs, h) in dans_crane]
        places += [(-46, 20, 22, "s"), (44, 30, 21, "s"), (-45, -14, 15, "m"), (43, -24, 14, "m")]
        for n_, (x, z, h, kind) in enumerate(places):
            x = float(np.clip(x, -W2 + 0.25 * h, W2 - 0.25 * h))
            z = float(np.clip(z, -P2 + 0.25 * h, P2 - 0.25 * h))
            y = niveau(x, z) - 0.3
            with b.at((x, y, z), yaw=float(rng.uniform(10, 80))):
                if kind == "s":
                    mobilier.sapin_sombre(b, variant=(0, 2, 0, 3, 2, 0, 2, 0, 1, 2)[n_ % 10], hauteur=h)
                else:
                    mobilier.arbre_mort(b, variant=(0, 2)[n_ % 2], hauteur=h)

    # racines noires de la forêt qui descendent du plateau en arcs sur les terrasses (côté couloir)
    with b.group("Racines"):
        for n_, ang in enumerate((-2.25, -1.62, -0.95)):
            a = ang + 0.12 * math.sin(3.0 * n_ + ph)
            pts = []
            for r in (24.0, 31.0, 38.0, 44.0):
                x, z = r * math.cos(a) * W2 / 55.0, r * math.sin(a) * P2 / 50.0 + 2.0
                pts.append(np.array([x, niveau(x, z, epaulements=False) + (0.6 if r < 40 else -0.6), z]))
                a += 0.07 * (1 if n_ % 2 else -1)
            for m_ in range(3):
                mid = (pts[m_] + pts[m_ + 1]) / 2 + np.array([0.0, 1.6, 0.0])
                _poutre(b, pts[m_], mid, 1.5 - 0.3 * m_, c("racine"), ref=(0, 1, 0), ext=0.3, name="Racine", **DECO)
                _poutre(b, mid, pts[m_ + 1], 1.4 - 0.3 * m_, c("racine_claire" if m_ % 2 else "racine"), ref=(0, 1, 0),
                        ext=0.3, name="Racine", **DECO)

    # os géants qui percent les pentes : deux côtes en arc et un long os couché (échos des côtes des champs)
    with b.group("Os"):
        for (x0, z0, dx, dz, L, e) in ((-30, -38, -0.5, -1.0, 22, 3.4), (32, -36, 0.6, -1.0, 18, 3.0)):
            y0 = niveau(x0, z0)
            d = np.array([dx, 0.0, dz]) / math.hypot(dx, dz)
            pts = [np.array([x0, y0 - 1.0, z0])]
            for t in (0.3, 0.62, 0.9, 1.1):
                p = np.array([x0, y0, z0]) + d * L * t * 0.55
                p[1] = y0 - 1.0 + L * math.sin(math.pi * min(t, 1.0) * 0.85) * 0.75
                pts.append(p)
            for n_ in range(len(pts) - 1):
                _poutre(b, pts[n_], pts[n_ + 1], e * (1 - 0.18 * n_), os_teinte(0.35 + 0.12 * n_), ref=(0, 0, 1),
                        ext=0.4 if n_ else 0.0, name="Cote")
        x0, z0 = 6.0, -44.0
        y0 = niveau(x0, z0)
        a0 = np.array([x0 - 9, y0 - 0.8, z0 + 2]); a1 = np.array([x0 + 9, y0 + 2.2, z0 - 1])
        _poutre(b, a0, a1, 2.6, os_teinte(0.45), ref=(0, 1, 0), name="Femur")
        for q in (a0, a1):
            b.boxc(tuple(q + np.array([0, 0.4, 0])), (3.6, 3.4, 3.8), os_teinte(0.5), yaw=20, name="Femur")
    return {"emprise": (largeur, profondeur), "hauteur": hauteur}


# ---------------------------------------------------------------------------
# À venir
# ---------------------------------------------------------------------------

def cotes_geantes(b, variant: int = 0, longueur: float = 56, hauteur: float = 36) -> dict:
    """Cage thoracique du démon qui sort des labours : échine à demi enterrée le long de X local (vertèbres à
    apophyses en pointe), paires de côtes énormes qui montent des deux côtés (±Z) et se recourbent vers l'intérieur
    sans se rejoindre (les plus hautes au milieu), quelques côtes cassées, os ivoire en haut et noirci vers le sol,
    buttes de terre labourée au pied. v0 : posée ; v1 : plus petite et plus enterrée."""
    rng = _rng(variant, 303)
    v = variant % 2
    L2 = longueur / 2
    H = hauteur * (0.72 if v else 1.0)
    enf = 4.0 if v else 0.0                   # enfoncement supplémentaire (v1)
    npaires = 5 if v else 6
    larg = 16.2 * (0.82 if v else 1.0)        # demi-largeur de la cage (emprise ≤ 36 avec l'épaisseur des côtes)
    pas = (longueur - 10) / (npaires - 1) if npaires > 1 else 0
    xs = [-L2 + 5 + i * pas for i in range(npaires)]
    cassees = {(1, -1), (npaires - 2, 1)} if variant < 2 else {(2, 1), (0, -1)}
    with b.group("Echine"):
        n_v = 9 if not v else 7
        for i in range(n_v):
            x = -L2 + 1.5 + i * (longueur - 3) / (n_v - 1)
            t = abs(x) / L2
            yb = 1.6 - 0.8 * t - enf * 0.5
            col = os_teinte(0.55 + 0.25 * t)
            b.boxc((x, yb, 0), (3.6 - 0.8 * t, 3.4, 4.4 - 1.0 * t), vary(col, rng, 0.03), yaw=float(rng.uniform(-6, 6)),
                   name="Vertebre")
            hp = (4.6 - 1.6 * t) * (0.8 if v else 1.0)
            if yb + 1.7 + hp > 2.5:
                _poutre(b, (x, yb + 1.0, 0), (x + 0.9, yb + 1.7 + hp, 0), 1.3 - 0.3 * t, os_teinte(0.4 + 0.2 * t),
                        ref=(0, 0, 1), name="Apophyse")
            if i % 2 == 0:
                _poutre(b, (x, yb + 0.4, -2.0), (x + 0.3, yb + 1.2, -5.0 + 0.8 * t), 1.0, os_teinte(0.6), ref=(1, 0, 0),
                        name="Apophyse", **DECO)
                _poutre(b, (x, yb + 0.4, 2.0), (x + 0.3, yb + 1.2, 5.0 - 0.8 * t), 1.0, os_teinte(0.6), ref=(1, 0, 0),
                        name="Apophyse", **DECO)
    with b.group("Cotes"):
        for i, x in enumerate(xs):
            u = (x / (L2 - 3)) if L2 > 3 else 0.0
            h = H * (0.52 + 0.48 * (1 - min(1.0, abs(u)) ** 2)) - enf
            for s in (-1, 1):
                # profil de la côte : sort de l'échine, s'écarte, monte, puis se recourbe vers l'intérieur
                lw = larg * (0.86 + 0.14 * (1 - abs(u)))
                hh = h * float(rng.uniform(0.9, 1.04))
                dx = float(rng.uniform(1.5, 4.0))             # les côtes se couchent un peu vers l'arrière
                ctrl = [(x, -enf - 0.5, s * 2.5), (x + 0.2 * dx, hh * 0.22, s * lw * 0.78), (x + 0.5 * dx, hh * 0.55, s * lw),
                        (x + 0.8 * dx, hh * 0.86, s * lw * 0.86), (x + dx, hh, s * lw * 0.48)]
                pts = _spline(ctrl, 5)
                if (i, s) in cassees:
                    pts = pts[:4]
                nseg = len(pts) - 1
                for n_ in range(nseg):
                    tt = n_ / 4
                    col = os_teinte(0.72 - 0.72 * tt ** 0.8)
                    ep = (4.0 - 1.6 * tt) * (0.85 if v else 1.0)
                    _poutre(b, pts[n_], pts[n_ + 1], ep, vary(col, rng, 0.025), ep_z=ep * 0.72, ref=(1, 0, 0),
                            ext=0.35 * ep if n_ else 0.0, name="Cote")
                if (i, s) in cassees:                         # cassure : éclat oblique plus sombre
                    q = pts[-1]
                    d = pts[-1] - pts[-2]
                    d /= np.linalg.norm(d)
                    _poutre(b, q - d * 0.6, q + d * 1.4 + np.array([0.5, 0.0, 0.0]), 1.3, c("os_ombre"), ref=(1, 0, 0),
                            roll=25, name="Eclat", **DECO)
                    # le bout tombé gît au pied, le long de l'échine
                    b.boxc((x + 3.2, 0.5, s * (lw * 0.62)), (6.0, 1.0, 1.6), os_teinte(0.5), yaw=float(rng.uniform(-25, 25)),
                           name="Debris", **DECO)
    with b.group("Buttes"):
        for i, x in enumerate(xs):
            for s in (-1, 1):
                lw = larg * 0.76
                col = vary(("labour", "terre_fonce", "labour_fonce")[(i + (s > 0)) % 3], rng, 0.05)
                yw = float(rng.uniform(-14, 14))
                b.boxc((x + 0.6, 0.7, s * lw), (7.0, 1.4, 5.5 + 2 * ((i + s) % 2)), col, yaw=yw, studs="top", name="Butte")
                b.boxc((x + 0.8, 1.6, s * (lw - 0.6)), (3.6, 1.0, 3.2), shade(col, 0.9), yaw=yw + 9, studs="top",
                       name="Butte")
        b.boxc((0, 0.5, 0), (longueur - 4, 1.0, 7.0), c("terre_fonce"), studs="top", name="Butte")
        b.boxc((-2, 1.2, 0.3), (longueur * 0.6, 0.6, 4.4), c("labour_fonce"), yaw=2, studs="top", name="Butte")
    return {"emprise": (longueur, 36), "hauteur": round(H, 1)}


def _grimoire_rayon(ctr, R0, s=1.0, ouvert=22.0) -> float:
    """Distance horizontale maximale à l'axe Y des coins d'un grimoire (voir `_grimoire`)."""
    ctr = np.asarray(ctr, float)
    blocs = []
    for k_ in (-1, 1):
        Rk = R0 @ rot_z(k_ * ouvert)
        blocs.append((ctr + Rk @ np.array([k_ * 0.68 * s, 0.0, 0.0]), Rk, np.array([1.4, 0.14, 1.9]) * s))
    blocs.append((ctr + R0 @ np.array([0.0, 0.2 * s, 0.0]), R0, np.array([2.3, 0.3, 1.64]) * s))
    m = 0.0
    for (cc, Rb, sz) in blocs:
        for sg in ((-1, -1, -1), (-1, -1, 1), (-1, 1, -1), (-1, 1, 1), (1, -1, -1), (1, -1, 1), (1, 1, -1), (1, 1, 1)):
            q = cc + Rb @ (np.asarray(sg, float) * sz / 2)
            m = max(m, math.hypot(q[0], q[2]))
    return m


def _grimoire(b, ctr, R0, couv, page, s=1.0, ouvert=22.0, lumineux=False) -> None:
    """Grimoire ouvert en V (2 couvertures unies + bloc de pages : 3 pièces), orienté librement par R0
    (colonnes : axe des couvertures écartées, normale du V, dos du livre)."""
    ctr = np.asarray(ctr, float)
    for k_ in (-1, 1):
        Rk = R0 @ rot_z(k_ * ouvert)
        off = Rk @ np.array([k_ * 0.68 * s, 0.0, 0.0])
        b.part("block", (1.4 * s, 0.14 * s, 1.9 * s), ctr + off, Rk, couv, name="Couverture", **DECO)
    b.part("block", (2.3 * s, 0.3 * s, 1.64 * s), ctr + R0 @ np.array([0.0, 0.2 * s, 0.0]), R0, page, name="Pages",
           **(NEON if lumineux else FIN))


def _baie(b, R, y0, h, w, lueur, pierre, arc=2.4, prof=1.3) -> None:
    """Haute baie en arc brisé sur un mur rond de rayon R (face vers -Z du repère courant) : fond lumineux (Neon) en
    retrait, piédroits, appui et arc de pierre en saillie."""
    zf = -(R + 0.25)
    b.box((-w / 2, y0, zf + 0.75), (w / 2, y0 + h, zf), lueur, name="Baie", **NEON)
    b.box((-w / 2 + 0.55, y0 + h, zf + 0.75), (w / 2 - 0.55, y0 + h + arc * 0.55, zf), lueur, name="Baie", **NEON)
    zo = -(R + 0.25 + prof * 0.45)
    zi = -(R - 0.6)
    for sx in (-1, 1):
        b.box((sx * w / 2, y0 - 0.2, zi), (sx * (w / 2 + 0.8), y0 + h + 0.3, zo), pierre, name="Piedroit", **DECO)
    b.box((-w / 2 - 1.0, y0 - 0.75, zi + 0.1), (w / 2 + 1.0, y0, zo - 0.3), shade(pierre, 1.05), studs="top", name="Appui",
          **DECO)
    b.wedge((-w / 2 - 0.8, y0 + h + 0.3, zi), (0.0, y0 + h + 0.3 + arc, zo), pierre, down="-x", name="Arc", **DECO)
    b.wedge((0.0, y0 + h + 0.3, zi), (w / 2 + 0.8, y0 + h + 0.3 + arc, zo), shade(pierre, 0.95), down="+x", name="Arc",
            **DECO)


def tour_grimoires(b, variant: int = 0, rayon: float = 16, hauteur: float = 118) -> dict:
    """Tour aux grimoires : tour ronde de pierre claire (la plus claire du bourg), talus, trois étages séparés de
    cordons, hautes baies en arc lumineuses en quinconce, grande porte en arc surmontée de la planche GRIMOIRES,
    couronne de mâchicoulis et balcon, toit conique très élancé d'ardoise violette et épi doré, deux échauguettes ;
    spirale de grimoires volants (magie voulue, alignée sur la tour) qui monte autour d'elle et sort de ses baies,
    lucioles dorées le long de la spirale. Avant (porte) vers -Z local. Tout reste à moins de 24 de l'axe."""
    rng = _rng(variant, 404)
    R = float(rayon)
    H = float(hauteur)
    y_cour = H * 0.68                     # haut du corps, couronne de mâchicoulis et balcon (≈ 80)
    pale = shade(c("pierre_pale"), 1.14)
    pierres = (pale, shade(c("pierre_pale"), 1.08), shade(c("pierre_pale"), 1.11), shade(c("pierre_pale"), 1.06))
    with b.group("Corps"):
        b.cyl((0, 2.2, 0), R + 1.6, 4.4, vary("pierre_fonce", rng, 0.03), studs="top", name="Talus")
        b.cyl((0, 5.0, 0), R + 0.8, 1.2, c("pierre"), studs="top", name="Talus")
        y = 5.6
        n_ = 0
        joints = [0.0, 4.4, 5.6]
        cordons = [H * 0.235, H * 0.465]
        while y < y_cour - 6.5 - 0.01:
            prochain = min([cd for cd in cordons if cd > y + 1] + [y_cour - 6.5])
            h = min(5.5, prochain - y)
            b.cyl((0, y + h / 2, 0), R, h, vary(pierres[n_ % 4], rng, 0.012), name="Assise")
            y += h
            n_ += 1
            joints.append(y)
            if any(abs(y - cd) < 0.01 for cd in cordons):
                b.cyl((0, y + 0.6, 0), R + 0.6, 1.2, c("pierre_claire"), studs="top", name="Cordon")
                y += 1.2
                joints.append(y)
        b.cyl((0, y + (y_cour - 0.4 - y) / 2, 0), R, y_cour - 0.4 - y, vary(pale, rng, 0.012), name="Assise")
        joints.append(y_cour - 0.4)
    niveaux_baies = [(H * 0.1, (45, 135, -135, -45)), (H * 0.255, (0, 90, 180, -90)), (H * 0.4, (45, 135, -135, -45)),
                     (H * 0.53, (0, 90, 180, -90))]
    hb, arc_b = 8.5, 2.4

    def hors_joint(y0):
        # aucune face horizontale d'une baie dans le plan d'un joint d'assise (pas de faces confondues)
        for _ in range(8):
            plans = (y0 - 0.75, y0, y0 + hb, y0 + hb + 0.3, y0 + hb + 0.3 + arc_b, y0 + hb + arc_b * 0.55)
            if all(abs(pl - j) > 0.06 for pl in plans for j in joints):
                return y0
            y0 += 0.15
        return y0

    niveaux_baies = [(hors_joint(y0), angles) for (y0, angles) in niveaux_baies]
    with b.group("Corps"):
        # pierres en saillie (appareil irrégulier), à l'écart des baies
        for i in range(46):
            th = float(rng.uniform(0, 2 * math.pi))
            yy = float(rng.uniform(8, y_cour - 9))
            pres = False
            for (y0, angles) in niveaux_baies:
                for a_ in angles:
                    da = (math.degrees(th) - a_ + 180) % 360 - 180
                    if abs(da) < 16 and y0 - 3.0 < yy < y0 + hb + arc_b + 1.5:
                        pres = True
            if pres:
                continue
            while any(abs(yy - j) < 0.06 or abs(yy + 2.0 - j) < 0.06 or abs(yy + 1.6 - j) < 0.06
                      or abs(yy + 1.2 - j) < 0.06 for j in joints):
                yy += 0.17
            w_, h_ = float(rng.choice((2.4, 3.0, 3.6))), float(rng.choice((1.2, 1.6, 2.0)))
            col = (c("pierre_claire"), shade(c("pierre_pale"), 1.12), c("pierre"), c("pierre_fonce"))[i % 4]
            with b.at((0, 0, 0), yaw=-math.degrees(th)):
                b.box((-w_ / 2, yy, -(R - 0.4)), (w_ / 2, yy + h_, -(R + 0.35)), col, name="Moellon", **DECO)

    # baies en quinconce (2 × 8) : quatre niveaux, quatre directions, décalées de 45° d'un niveau à l'autre
    centres_baies = []
    with b.group("Baies"):
        for nv, (y0, angles) in enumerate(niveaux_baies):
            for j, th in enumerate(angles):
                lueur = c("lueur_violette") if (nv + j + variant) % 5 == 2 else c(("lueur_doree", "lueur_bougie")[(nv + j) % 2])
                with b.at((0, 0, 0), yaw=-th):
                    _baie(b, R, y0, hb, 3.4, lueur, vary("pierre_pale", rng, 0.03), arc=arc_b)
                centres_baies.append((th, y0 + 4.3))

    # porte en arc, planche GRIMOIRES, marches
    with b.group("Porte"):
        zf = -(R + 0.2)
        b.box((-3.0, 0.8, zf + 1.2), (3.0, 9.0, zf), c("bois_fonce"), name="Porte")
        b.box((-1.6, 9.0, zf + 1.2), (1.6, 10.4, zf), c("bois_fonce"), name="Porte")
        for yb_ in (2.4, 6.2):
            b.box((-3.0, yb_, zf - 0.15), (3.0, yb_ + 0.5, zf), c("fer"), name="Penture", **FIN)
        for xc_ in (-1.5, 0.0, 1.5):
            b.box((xc_ - 0.2, 4.2, zf - 0.25), (xc_ + 0.2, 4.6, zf), c("fer_fonce"), name="Clou", **FIN)
        zo = -(R + 1.6)
        for sx in (-1, 1):
            b.box((sx * 3.0, 0.0, zf + 1.5), (sx * 4.4, 10.0, zo), c("pierre_pale"), name="Piedroit")
        b.wedge((-4.4, 10.0, zf + 1.5), (0.0, 13.0, zo), c("pierre_pale"), down="-x", name="Arc")
        b.wedge((0.0, 10.0, zf + 1.5), (4.4, 13.0, zo), shade(c("pierre_pale"), 0.95), down="+x", name="Arc")
        planche = b.box((-5.0, 13.4, zo + 0.4), (5.0, 15.6, zo - 0.1), c("bois_fonce"), name="Enseigne", **DECO)
        planche.label = {"face": "Front", "text": "GRIMOIRES", "color": c("dorure"), "bg": None, "font": "serif"}
        b.box((-5.5, 0, -(R + 4.6)), (5.5, 0.8, -(R + 0.8)), c("pierre_fonce"), studs="top", name="Marche")
        b.box((-4.5, 0.8, -(R + 2.9)), (4.5, 1.2, -(R + 0.8)), c("pierre"), studs="top", name="Marche")
        for sx in (-1, 1):                                   # lanternes de part et d'autre de la porte
            b.box((sx * 5.2 - 0.3, 6.5, -(R + 0.2)), (sx * 5.2 + 0.3, 7.0, -(R + 1.6)), c("fer"), name="Potence", **FIN)
            b.box((sx * 5.2 - 0.6, 5.0, -(R + 1.0)), (sx * 5.2 + 0.6, 6.5, -(R + 2.2)), c("lueur_lanterne"),
                  name="Lanterne", **NEON)

    # couronne : mâchicoulis, balcon, échauguettes, toit conique élancé, épi doré
    with b.group("Couronne"):
        n_c = 20
        for i in range(n_c):
            th = 360.0 * i / n_c + 9.0
            with b.at((0, 0, 0), yaw=-th):
                b.box((-1.0, y_cour - 5.2, -(R - 0.5)), (1.0, y_cour - 2.6, -(R + 2.0)), c("pierre_pale"), name="Corbeau")
        b.cyl((0, y_cour - 1.3, 0), R + 2.6, 2.6, c("pierre_claire"), studs="top", name="Balcon")
        for i in range(16):                                  # garde-corps : petits merlons sur le balcon
            th = 360.0 * i / 16
            with b.at((0, 0, 0), yaw=-th):
                b.box((-1.1, y_cour, -(R + 1.5)), (1.1, y_cour + 1.6, -(R + 2.5)), c("pierre_pale"), name="Merlon",
                      **DECO)
        b.cyl((0, y_cour + 0.6, 0), R + 0.2, 1.2, c("pierre_pale"), name="Arase")
        # toit : anneaux de cylindres qui rétrécissent (profil légèrement concave : très élancé), studs sur les gradins
        y0 = y_cour + 1.2
        n_t = 13
        ht = (H - y0) / n_t
        for i in range(n_t):
            t = (i + 0.5) / n_t
            r = (R + 1.6) * (1 - t) ** 1.15 + 0.3
            col = vary(("ardoise", "ardoise_fonce", "ardoise_claire")[i % 3], rng, 0.03)
            b.cyl((0, y0 + (i + 0.5) * ht, 0), r, ht, col, studs="top", name="Toit")
        b.cyl((0, H + 1.6, 0), 0.35, 3.2, c("or"), name="Epi", **DECO)
        b.ball((0, H + 0.6, 0), 0.9, c("or"), name="Epi", **DECO)
        b.boxc((0, H + 3.6, 0), (0.6, 0.9, 0.6), c("or"), yaw=45, name="Epi", **DECO)
        # échauguettes (une ou deux selon la variante)
        for th in ((-62.0, 62.0) if variant % 2 == 0 else (-58.0,)):
            with b.at((0, 0, 0), yaw=-th):  # noqa: B007
                zc_ = -(R + 2.6)
                b.cyl((0, y_cour - 9.2, zc_), 1.6, 2.0, c("pierre_pale"), name="Culot")
                b.cyl((0, y_cour - 7.2, zc_), 2.6, 2.0, c("pierre_claire"), name="Culot")
                b.cyl((0, y_cour - 0.7, zc_), 3.4, 11.0, c("pierre_claire"), name="Echauguette")
                b.box((-0.6, y_cour - 3.0, zc_ - 3.2), (0.6, y_cour + 0.5, zc_ - 3.55), c("lueur_bougie"), name="Fente",
                      **NEON)
                for i in range(5):
                    t = (i + 0.5) / 5
                    r = 4.0 * (1 - t) ** 1.3 + 0.25
                    b.cyl((0, y_cour + 4.5 + (i + 0.5) * 2.0, zc_), r, 2.0, c(("ardoise", "ardoise_fonce")[i % 2]),
                          studs="top", name="ToitEchauguette")
                b.cyl((0, y_cour + 15.6, zc_), 0.25, 1.6, c("or"), name="Epi", **DECO)

    # lierre sombre qui grimpe sur le bas du corps (coulées irrégulières de petites plaques)
    with b.group("Lierre"):
        for (th, yb_, hh) in ((-118, 3, 26), (-146, 5, 17), (148, 4, 30), (112, 4, 14), (-96, 24, 10), (176, 6, 12)):
            with b.at((0, 0, 0), yaw=-th):
                y_ = yb_
                x_ = 0.0
                for n_ in range(3):
                    w_ = (4.4, 3.0, 1.8)[n_]
                    h_ = hh * (0.45, 0.33, 0.22)[n_]
                    col = c(("lierre", "lierre_clair", "lierre")[n_])
                    while any(abs(y_ - j) < 0.06 or abs(y_ + h_ - j) < 0.06 for j in joints):
                        y_ += 0.13                           # pas dans le plan d'un joint d'assise
                    b.box((x_ - w_ / 2, y_, -(R - 0.3 - 0.07 * n_)), (x_ + w_ / 2, y_ + h_, -(R + 0.3 + 0.08 * n_)), col,
                          name="Lierre", **DECO)
                    y_ += h_ * 0.85 + 0.07 * (n_ + 1)
                    x_ += round(float(rng.uniform(-1.2, 1.2)) / 0.3) * 0.3 + 0.11

    # spirale de grimoires volants (magie voulue) : 1,8 tour d'hélice de y ≈ 12 à y ≈ 100, orientés le long de
    # l'hélice, ailes ouvertes, légèrement penchés ; un sur quatre a des pages lumineuses
    from palette import CUIRS
    with b.group("Grimoires"):
        n_l = 40
        tours = 1.75
        a0 = math.pi * (0.75 + 0.5 * float(rng.random()))      # départ derrière la tour (la porte reste dégagée)
        y_a, y_b = 17.0, min(H - 16.0, 100.0)
        echauguettes = (-62.0, 62.0) if variant % 2 == 0 else (-58.0,)
        for i in range(n_l):
            t = i / (n_l - 1)
            a = a0 + 2 * math.pi * tours * t
            r = R + 4.4 + 0.8 * math.sin(7 * t + 1.0)
            y = y_a + (y_b - y_a) * t + float(rng.uniform(-1.2, 1.2))
            if y_cour - 4 < y < y_cour + 5:
                r += 1.4                                      # au large du balcon
            ad = (math.degrees(a) + 180) % 360 - 180
            if any(abs(ad - e_) < 16 for e_ in echauguettes) and y_cour - 12 < y < y_cour + 18:
                continue                                      # pas à travers une échauguette
            p = np.array([r * math.sin(a), y, -r * math.cos(a)])
            tang = np.array([math.cos(a), 0.0, math.sin(a)]) * r * 2 * math.pi * tours + np.array([0.0, y_b - y_a, 0.0])
            tang /= np.linalg.norm(tang)
            rad = np.array([math.sin(a), 0.0, -math.cos(a)])
            nrm = rad * 0.75 + np.array([0.0, 0.66, 0.0])       # les pages regardent dehors et vers le haut
            nrm -= np.dot(nrm, tang) * tang
            nrm /= np.linalg.norm(nrm)
            R0 = np.column_stack([np.cross(nrm, tang), nrm, tang])
            R0 = R0 @ rot_z(float(rng.uniform(-18, 18))) @ rot_x(float(rng.uniform(-12, 12)))
            couv = vary(CUIRS[int(rng.integers(len(CUIRS)))], rng, 0.05)
            lum = i % 4 == 1
            s_ = float(rng.uniform(2.2, 2.6))
            ouv = float(rng.uniform(16, 32))
            for _essai in range(3):                         # le livre entier reste à moins de 24 de l'axe
                ex = _grimoire_rayon(p, R0, s_, ouv) - 23.8
                if ex <= 0:
                    break
                r -= ex + 0.05
                p = np.array([r * math.sin(a), y, -r * math.cos(a)])
            _grimoire(b, p, R0, couv, c("lueur_doree") if lum else c(("page", "page_ombre")[i % 2]), s=s_,
                      ouvert=ouv, lumineux=lum)
        # grimoires qui sortent des baies (à moitié dans l'embrasure)
        sorties = [centres_baies[i] for i in (4, 9, 6, 13, 11) if i < len(centres_baies)]
        for n_, (th, yc_) in enumerate(sorties):
            a = math.radians(th)
            rad = np.array([math.sin(a), 0.0, -math.cos(a)])
            p = rad * (R + 1.1) + np.array([0.0, yc_ + 0.5, 0.0])
            side = np.array([math.cos(a), 0.0, math.sin(a)])
            dos = rad * math.cos(math.radians(28)) + np.array([0.0, math.sin(math.radians(28)), 0.0])
            up = np.cross(dos, side)
            if up[1] < 0:
                up = -up
            R0 = np.column_stack([side, up, dos])
            couv = c(CUIRS[(n_ * 2 + variant) % len(CUIRS)])
            _grimoire(b, p, R0, couv, c("lueur_doree") if n_ % 2 == 0 else c("page"), s=2.2, ouvert=26.0,
                      lumineux=n_ % 2 == 0)
        # lucioles dorées le long de la spirale
        for i in range(14):
            t = (i + 0.5) / 14
            a = a0 + 2 * math.pi * tours * t + 0.15
            r = R + float(rng.uniform(5.5, 7.2))
            y = y_a + (y_b - y_a) * t + float(rng.uniform(-3, 3))
            sz = float(rng.choice((0.45, 0.6, 0.75)))
            b.boxc((r * math.sin(a), y, -r * math.cos(a)), (sz, sz, sz), c("lueur_doree") if i % 3 else mix(
                c("lueur_doree"), (255, 255, 255), 0.45), yaw=float(rng.uniform(0, 90)), name="Luciole", **NEON)
    return {"emprise": (48, 48), "hauteur": H}


def montagne_capitale(b, variant: int = 0, largeur: float = 70, hauteur: float = 96) -> dict:
    """Capitale du royaume au loin (refBC5) : montagne rocheuse escarpée en gradins irréguliers qui rétrécissent, une
    face en falaise (côté +X local, vers l'entrée une fois posée), plateau sommital coiffé d'un petit château clair
    (enceinte, tours à toits pointus bleu-gris, donjon), quelques sapins sombres au pied. Couleurs de lointain,
    grands plans, peu de détails, deux fenêtres chaudes seulement."""
    rng = _rng(variant, 505)
    W2 = largeur / 2
    Hp = hauteur * 0.82                   # plateau sommital (≈ 79)
    cell = 5.0
    xe = np.arange(-W2, W2 + 0.01, cell)
    xe = xe if xe[-1] >= W2 - 0.01 else np.append(xe, W2)
    xc = (xe[:-1] + xe[1:]) / 2
    X, Z = np.meshgrid(xc, xc, indexing="ij")
    sx, sz = 4.0, 3.0                     # sommet décalé vers la falaise
    TH = np.arctan2(Z - sz, X - sx)
    ph = 1.3 * variant
    lob = 1 + 0.16 * np.sin(3 * TH + 0.4 + ph) + 0.09 * np.sin(5 * TH + 2.2) + 0.06 * np.sin(7 * TH + 1.0 - ph)
    # falaise : rayon écrasé côté +X (pente très raide), plus doux côté -X
    raide = 0.62 + 0.38 * (1 - np.clip(np.cos(TH), 0, 1)) ** 1.5
    D = np.hypot(X - sx, Z - sz) / (W2 * lob * raide)
    paliers = [Hp * f for f in (0.13, 0.26, 0.39, 0.52, 0.64, 0.76, 0.88, 1.0)]
    tons = ("lointain_fonce", "lointain_fonce", "lointain", "lointain", "lointain", "lointain_clair", "lointain_clair",
            "lointain_clair")
    masques = []
    for n_, yt in enumerate(paliers):
        # chaque gradin a ses propres lobes (contour irrégulier), le sommet est un plateau d'au moins 9 de rayon
        lob2 = 1 + 0.12 * np.sin(4 * TH + 1.7 * n_ + ph) + 0.07 * np.sin(6 * TH - 0.9 * n_)
        hn = Hp * np.clip(1 - D / lob2, 0, 1) ** 0.62
        m = hn >= yt - 0.5 * paliers[0]
        if n_ == len(paliers) - 1:
            m |= np.hypot(X - sx, Z - sz) <= 9.0
        masques.append(m)
    for n_ in range(len(masques) - 2, -1, -1):             # chaque gradin porte celui du dessus
        masques[n_] |= masques[n_ + 1]
    hmap = np.zeros(X.shape)
    for yt, m in zip(paliers, masques):
        hmap = np.where(m, yt, hmap)
    y0 = 0.0
    with b.group("Roche"):
        for n_, (yt, m) in enumerate(zip(paliers, masques)):
            if not m.any():
                break
            for (i, kz, w, h) in mask_rects(m.T):
                col = vary(tons[n_], rng, 0.04)
                b.box((xe[i], y0, xe[kz]), (xe[i + w], yt, xe[kz + h]), col, studs="top", name="Gradin")
            y0 = yt
        # éperons rocheux en saillie (cassent les gradins réguliers)
        for n_ in range(5):
            a = 2 * math.pi * n_ / 5 + 0.6 + ph
            r = W2 * float(rng.uniform(0.35, 0.55))
            x, z = sx + r * math.cos(a), sz + r * math.sin(a)
            yt = float(hmap[int(np.clip(np.searchsorted(xe, x) - 1, 0, len(xc) - 1)),
                            int(np.clip(np.searchsorted(xe, z) - 1, 0, len(xc) - 1))])
            if yt < 8:
                continue
            hh = float(rng.uniform(8, 14))
            b.boxc((x, yt - hh * 0.35, z), (float(rng.uniform(5, 8)), hh, float(rng.uniform(4, 7))),
                   vary("lointain_fonce", rng, 0.04), yaw=float(rng.uniform(15, 75)), studs="top", name="Eperon")
    # château clair sur le plateau
    cx, cz = sx, sz
    y = Hp
    with b.group("Chateau"):
        cr = c("chateau_royal")
        toit = c("toit_royal")
        b.box((cx - 7, y, cz - 6), (cx + 7, y + 6, cz - 5), cr, name="Enceinte")
        b.box((cx - 7, y, cz + 5), (cx + 7, y + 6, cz + 6), cr, name="Enceinte")
        b.box((cx - 7, y, cz - 5), (cx - 6, y + 6, cz + 5), cr, name="Enceinte")
        b.box((cx + 6, y, cz - 5), (cx + 7, y + 6, cz + 5), cr, name="Enceinte")
        b.box((cx - 1.4, y, cz - 6.3), (cx + 1.4, y + 3.4, cz - 6.0), c("bois_fonce"), name="Porte", **DECO)
        for (tx, tz, rr, hh) in ((-7, -6, 1.9, 11), (7, -6, 1.9, 12), (-7, 6, 1.7, 10), (7, 6, 1.7, 10)):
            b.cyl((cx + tx, y + hh / 2, cz + tz), rr, hh, cr, name="Tour")
            for i in range(3):
                t = (i + 0.5) / 3
                b.cyl((cx + tx, y + hh + (i + 0.5) * 1.6, cz + tz), (rr + 0.5) * (1 - t) + 0.2, 1.6, toit, studs="top",
                      name="Toit")
        # donjon et sa flèche
        hk = max(8.0, hauteur - y - 7.0)                   # donjon : la flèche (5,2) et l'épi finissent vers `hauteur`
        b.box((cx - 3.2, y, cz - 2.2), (cx + 3.2, y + hk, cz + 4.2), shade(cr, 1.04), name="Donjon")
        for i in range(4):
            t = (i + 0.5) / 4
            w_ = 7.4 * (1 - t) + 0.4
            b.boxc((cx, y + hk + (i + 0.5) * 1.3, cz + 1.0), (w_, 1.3, w_), toit, yaw=45 * (i % 2), studs="top",
                   name="Fleche")
        b.box((cx - 0.15, y + hk + 5.2, cz + 0.85), (cx + 0.15, y + hk + 7.0, cz + 1.15), c("or"), name="Epi", **FIN)
        for (fx, fy) in ((-1.4, 8.5), (1.4, 8.5)):
            b.box((cx + fx - 0.5, y + fy, cz - 2.35), (cx + fx + 0.5, y + fy + 1.4, cz - 2.2), c("lueur_bougie"),
                  name="Fenetre", **NEON)
    # sapins sombres au pied (côté couloir et côtés)
    with b.group("Sapins"):
        for n_ in range(7):
            a = math.pi * (0.9 + 1.2 * n_ / 6) + float(rng.uniform(-0.15, 0.15))
            r = W2 * float(rng.uniform(0.82, 0.95))
            x = float(np.clip(r * math.cos(a), -W2 + 3, W2 - 3))
            z = float(np.clip(r * math.sin(a), -W2 + 3, W2 - 3))
            hh = float(rng.uniform(9, 14))
            b.boxc((x, hh * 0.3, z), (hh * 0.42, hh * 0.6, hh * 0.42), vary("sapin_fonce", rng, 0.05), yaw=45,
                   studs="top", name="Sapin")
            b.boxc((x, hh * 0.78, z), (hh * 0.24, hh * 0.44, hh * 0.24), vary("sapin_fonce", rng, 0.05), studs="top",
                   name="Sapin")
    return {"emprise": (largeur, largeur), "hauteur": hauteur}
