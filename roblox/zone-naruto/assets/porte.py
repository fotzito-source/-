"""Porte principale de Konoha (« porte A-Un ») : entrée de la zone Naruto.

Repère : origine au centre de l'ouverture, au sol ; le plan de la porte et du rempart est centré sur z = 0.
L'EXTÉRIEUR (d'où arrivent les joueurs) est +Z ; le village et le couloir de course s'étendent vers -Z.
Exception à la règle « l'avant regarde -Z » : la face principale est la face +Z, mais la face -Z est vue
au retour, elle est donc soignée aussi.

Éléments : deux piliers massifs sur socle de pierre, un linteau (attique) portant 忍 · spirale de la feuille · 忍
en pixels rouges sur les deux faces, un toit de tuiles vert-de-gris à deux pans, deux immenses vantaux
vert pâle ouverts vers l'extérieur (あ à gauche, ん à droite, sur la face tournée vers le couloir),
le rempart orangé à motif « pixel » avec chaperon de tuiles et contreforts, trois gros tuyaux le long
du rempart côté droit (x > 0, face extérieure) et une petite guérite de gardes côté village.
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, shade
from palette import c, vary
from textures import glyph_mask, mask_rects

# Couleurs locales (en plus de la palette)
PILIER = "#86B694"        # vert sauge des piliers et du linteau
PILIER_CLAIR = "#93C2A0"
PILIER_FONCE = "#78A886"
CORNICHE = "#557B63"      # moulures vert sombre
TUILE_FONCE = "#6C7D5B"   # tuiles vert-de-gris (bandes sombres)
FAITAGE = "#56654A"
FER = "#3A3F44"           # ferrures, pentures
PIERRE = "#BDB3A0"
PIERRE_FONCE = "#A39985"
REMPART_CLAIR = "#E6B47E"
REMPART_MOYEN = "#D49B60"
JOINT_PORTE = "#7DAE87"   # fond des joints entre planches des vantaux


# ----------------------------------------------------------------------------
# Motifs pixel
# ----------------------------------------------------------------------------

def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-12), 0, 1)
    return np.hypot(px - (ax + t * dx), py - (ay + t * dy))


def spirale_feuille(n: int = 20) -> np.ndarray:
    """Emblème de la feuille de Konoha en pixels (n × n) : spirale, queue effilée vers le bas à gauche,
    petite épine triangulaire à gauche. Dessiné à la main (aucune police), lignes = haut → bas."""
    ss = 6
    g = (np.arange(n * ss) + 0.5) / (n * ss)
    X, Y = np.meshgrid(g, g)
    cx, cy, r0, r1, thick, turns = 0.60, 0.42, 0.02, 0.35, 0.085, 1.5
    pts = []
    m = 200
    for i in range(m + 1):
        s = i / m
        th = math.pi + turns * 2 * math.pi * (1 - s)  # trace anti-horaire à l'écran, finit à gauche
        r = r0 + (r1 - r0) * s
        pts.append((cx + r * math.cos(th), cy + r * math.sin(th), thick * (0.7 + 0.3 * s)))
    ex, ey, _ = pts[-1]
    tip, mid = (0.05, 0.97), (ex, ey + 0.22)
    for i in range(1, 51):
        s = i / 50
        bx = (1 - s) ** 2 * ex + 2 * (1 - s) * s * mid[0] + s * s * tip[0]
        by = (1 - s) ** 2 * ey + 2 * (1 - s) * s * mid[1] + s * s * tip[1]
        pts.append((bx, by, thick * (1 - 0.7 * s)))
    inside = np.zeros(X.shape, bool)
    for (ax, ay, wa), (bx, by, wb) in zip(pts[:-1], pts[1:]):
        inside |= _seg_dist(X, Y, ax, ay, bx, by) <= (wa + wb) / 2
    # épine (pointe de feuille) à gauche
    (ax, ay), (bx, by), (qx, qy) = (0.0, 0.40), (0.15, 0.30), (0.15, 0.50)

    def edge(ax, ay, bx, by):
        return (bx - ax) * (Y - ay) - (by - ay) * (X - ax)

    e0, e1, e2 = edge(ax, ay, bx, by), edge(bx, by, qx, qy), edge(qx, qy, ax, ay)
    inside |= ((e0 >= 0) & (e1 >= 0) & (e2 >= 0)) | ((e0 <= 0) & (e1 <= 0) & (e2 <= 0))
    return inside.reshape(n, ss, n, ss).mean(axis=(1, 3)) > 0.45


def _motif_rempart(rng, ncol: int, nrow: int) -> np.ndarray:
    """Indices de teinte 0..3 par case : taches « pixel » douces (bruit grossier agrandi + grain)."""
    gx, gy = ncol // 5 + 3, nrow // 3 + 3
    coarse = rng.random((gy, gx))
    ys = np.linspace(0, gy - 1.001, nrow)
    xs = np.linspace(0, gx - 1.001, ncol)
    y0, x0 = ys.astype(int), xs.astype(int)
    fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
    a = coarse[y0][:, x0]
    b_ = coarse[y0][:, x0 + 1]
    c_ = coarse[y0 + 1][:, x0]
    d = coarse[y0 + 1][:, x0 + 1]
    field = (a * (1 - fx) + b_ * fx) * (1 - fy) + (c_ * (1 - fx) + d * fx) * fy
    field = field + rng.normal(0, 0.10, field.shape)
    q = np.quantile(field, [0.18, 0.40, 0.80])
    out = np.zeros(field.shape, int)          # 0 = teinte de base
    out[field < q[1]] = 2                     # moyen
    out[field < q[0]] = 3                     # foncé
    out[field > q[2]] = 1                     # clair
    return out


# ----------------------------------------------------------------------------
# Sous-ensembles
# ----------------------------------------------------------------------------

def _glyphe_face(b, mask, p, xc, yc, z_face, sens, prof, couleur, **kw):
    """Pose un masque de pixels (lignes haut → bas) sur une face verticale perpendiculaire à Z.

    sens = +1 : face qui regarde +Z (colonnes vers +X) ; sens = -1 : face qui regarde -Z (colonnes vers -X).
    Les pixels vont de z_face à z_face + sens * prof.
    """
    nr, nc = mask.shape
    W, H = nc * p, nr * p
    for (x, y, w, h) in mask_rects(mask):
        y_top = yc + H / 2 - y * p
        if sens > 0:
            x0 = xc - W / 2 + x * p
        else:
            x0 = xc + W / 2 - (x + w) * p
        b.box((x0, y_top - h * p, z_face), (x0 + w * p, y_top, z_face + sens * prof), couleur, **kw)


def _vantail(b, side, half, H, z_gond, angle, lettre, rng):
    """Vantail vert pâle (half × H × 2) ouvert vers +Z, gond en (side·half, z_gond).

    Coordonnées du vantail : u = largeur depuis le gond (0..half), v = hauteur, w = épaisseur
    (w = 0 sur la face tournée vers le couloir, w = 2 sur la face arrière tournée vers le rempart).
    """
    if side < 0:
        yaw, zs = -angle, 1.0          # X local → (+cos, 0, +sin) ; Z local → vers -x (arrière)
    else:
        yaw, zs = angle - 180.0, -1.0  # X local → (-cos, 0, +sin) ; Z local → vers le couloir
    W, T = half, 2.0

    with b.at((side * half, 0, z_gond), yaw=yaw):
        def box(u0, u1, v0, v1, w0, w1, col, **kw):
            return b.box((u0, v0, zs * w0), (u1, v1, zs * w1), col, **kw)

        # âme sombre (visible dans les joints) puis montants, traverses et planches
        box(0.6, W - 0.6, 0.6, H - 0.6, 0.35, T - 0.35, JOINT_PORTE)
        box(0, 2.2, 0, H, -0.25, T + 0.25, c("porte_vert_fonce"), name="Montant")
        box(W - 2.2, W, 0, H, -0.25, T + 0.25, c("porte_vert_fonce"), name="Montant")
        box(2.2, W - 2.2, H - 2.6, H, -0.25, T + 0.25, c("porte_vert_fonce"), name="Traverse")
        box(2.2, W - 2.2, 0, 3.0, -0.25, T + 0.25, c("porte_vert_fonce"), name="Traverse")
        n_pl = max(3, int(round((W - 4.4) / 6.4)))
        pw = (W - 4.4) / n_pl
        for i in range(n_pl):
            u0 = 2.2 + i * pw
            box(u0 + (0.15 if i else 0), u0 + pw - (0.15 if i < n_pl - 1 else 0), 3.0, H - 2.6, 0, T,
                vary("porte_vert", rng, 0.025), name="Planche")

        # pentures (bandes de fer) : longues sur la face arrière, courtes côté couloir (hors lettre)
        for vb in (H * 0.17, H * 0.5, H * 0.83):
            box(-0.3, W * 0.42, vb - 1.0, vb + 1.0, T + 0.25, T + 0.6, FER, name="Penture")
            box(-0.3, 3.2, vb - 1.0, vb + 1.0, -0.6, -0.25, FER, name="Penture")
            b.cyl((0, vb, zs * T / 2), 1.0, 2.6, FER, axis="y", name="Gond")
        # gros clous décoratifs sur la face arrière
        for vb in (H * 0.17, H * 0.5, H * 0.83):
            for uu in (W * 0.62, W * 0.8):
                b.cyl((uu, vb, zs * (T + 0.2)), 0.55, 0.6, FER, axis="z", name="Clou", collide=False)

        # grande lettre rouge sur la face côté couloir
        m = glyph_mask(lettre, 22, font="sans", threshold=0.5)
        p = min(1.3, (W - 6.0) / m.shape[1])
        nr, nc = m.shape
        uc, vc = W / 2 + 0.3, H / 2 + 0.6
        for (x, y, w, h) in mask_rects(m):
            vt = vc + nr * p / 2 - y * p
            if side < 0:   # face avant locale (-Z) : les colonnes de l'image vont vers -u
                u1 = uc + nc * p / 2 - x * p
                u0 = u1 - w * p
            else:          # face arrière locale (+Z) : les colonnes vont vers +u
                u0 = uc - nc * p / 2 + x * p
                u1 = u0 + w * p
            box(u0, u1, vt - h * p, vt, -0.5, 0, c("lettre_rouge"), name="Lettre")


def _lanterne(b, x, y_attache, z_mur, sens, couleur):
    """Lanterne ronde suspendue à une potence fixée sur une face (z_mur), saillie vers sens·Z."""
    zc = z_mur + sens * 3.2
    b.box((x - 0.3, y_attache - 0.5, z_mur), (x + 0.3, y_attache, zc + sens * 0.3), FER, collide=False, name="Potence")
    b.box((x - 0.15, y_attache - 1.6, zc - 0.15), (x + 0.15, y_attache - 0.5, zc + 0.15), FER, collide=False)
    b.cyl((x, y_attache - 1.9, zc), 0.8, 0.6, c("noir"), axis="y", collide=False)
    b.ball((x, y_attache - 3.9, zc), 1.8, couleur, collide=False, name="Lanterne")
    b.cyl((x, y_attache - 5.9, zc), 0.7, 0.5, c("noir"), axis="y", collide=False)


def _guerite(b, rng, toit):
    """Petite guérite en bois (repère local : avant = -Z), bureau, deux tabourets, lanterne."""
    bois, bois_c, bois_f, poutre = c("bois"), c("bois_clair"), c("bois_fonce"), c("poutre")
    b.box((-6.5, 0, -6), (6.5, 0.8, 6), bois_f, studs="top", name="Plancher")
    # mur du fond, murets latéraux, poteaux avant
    b.box((-6.5, 0.8, 4.8), (6.5, 11.2, 6), vary("bois", rng), material="WoodPlanks", name="Fond")
    for sx in (-1, 1):
        b.box((sx * 5.5, 0.8, -5), (sx * 6.5, 4.6, 4.8), bois, material="WoodPlanks")
        b.box((sx * 5.5, 10, -5), (sx * 6.5, 11.2, 4.8), poutre)
        b.box((sx * 5.5, 0.8, -6), (sx * 6.5, 11.2, -5), poutre, name="Poteau")
        b.box((sx * 5.6, 4.6, -5), (sx * 6.4, 5.0, 4.8), bois_c, studs="top")
    b.box((-6.5, 10, -6.2), (6.5, 11.2, -5), poutre, name="Linteau")
    # bureau
    b.box((-5.5, 0.8, -6), (5.5, 4.2, -5), bois, material="WoodPlanks", name="Bureau")
    b.box((-6, 4.2, -6.5), (6, 4.7, -3.6), bois_c, studs="top", name="Plateau")
    b.box((-3.4, 4.7, -5.9), (-1.0, 4.85, -4.2), c("blanc"), collide=False, name="Papiers")
    b.box((-0.6, 4.7, -5.6), (1.4, 4.95, -4.4), c("panneau"), collide=False, name="Registre")
    b.cyl((3.0, 5.05, -4.9), 0.35, 0.7, c("noir"), axis="y", collide=False, name="Encrier")
    # deux tabourets
    for x in (-2.6, 2.6):
        b.cyl((x, 1.8, -2.0), 0.35, 2.0, bois_f, axis="y", name="Pied")
        b.cyl((x, 3.05, -2.0), 1.05, 0.5, bois_c, axis="y", studs=("Right",), name="Tabouret")
    # enseigne sous le linteau
    s = b.box((-2.8, 8.0, -6.45), (2.8, 10, -6.2), c("panneau"), collide=False, name="Enseigne")
    s.label = {"face": "Front", "text": "受付", "color": (60, 35, 25), "bg": None, "font": "brush"}
    # toit à deux pans (faîtage le long de X local)
    b.box((-7.5, 11.2, -7.5), (7.5, 11.8, 7.5), bois_f, name="Rive")
    b.wedge((-7.5, 11.8, -7.5), (7.5, 14.6, 0), toit, down="-z", studs="top")
    b.wedge((-7.5, 11.8, 0), (7.5, 14.6, 7.5), shade(toit, 0.92), down="+z", studs="top")
    b.box((-7.9, 14.2, -0.7), (7.9, 15.0, 0.7), shade(toit, 0.7), studs="top", name="Faitage")
    # lanterne accrochée sous l'avant-toit
    b.box((5.85, 10.2, -7.15), (6.15, 11.2, -6.85), c("noir"), collide=False)
    b.cyl((6.0, 9.95, -7.0), 0.5, 0.5, c("noir"), axis="y", collide=False)
    b.cyl((6.0, 8.6, -7.0), 0.85, 2.2, c("orange_lampion"), axis="y", material="Neon", collide=False, name="Lampion")
    b.cyl((6.0, 7.25, -7.0), 0.5, 0.5, c("noir"), axis="y", collide=False)


# ----------------------------------------------------------------------------
# Asset principal
# ----------------------------------------------------------------------------

def porte_konoha(b, variant: int = 0, ouverture: float = 72, hauteur: float = 46, mur: float = 170) -> dict:
    """Porte A-Un de Konoha + rempart. Voir le docstring du module pour le repère (extérieur = +Z)."""
    rng = b.rng
    v = variant % 4
    half = ouverture / 2
    H = hauteur
    PW = 11.0                     # largeur d'un pilier
    PD = 6.5                      # demi-profondeur des piliers
    xo = half + PW                # face extérieure des piliers
    y_lin = H + 1                 # sous-face du linteau (hauteur libre)
    y_att0, y_att1 = y_lin + 2.5, y_lin + 25.5
    y_toit = y_att1 + 2.0
    tuile = (c("rempart_tuile"), mix(c("rempart_tuile"), c("toit_bleu"), 0.18), c("rempart_tuile"), mix(c("rempart_tuile"), c("toit_vert"), 0.3))[v]
    tuile_f = shade(tuile, 0.87)
    lampe = (c("orange_lampion"), c("rouge"), c("jaune_lampion"), c("orange_lampion"))[v]
    angle = math.degrees(math.acos(max(0.0, min(1.0, (half - 32.2) / half)))) + (0, 0.6, 1.2, 0.3)[v]
    angle = max(80.0, min(90.0, angle))

    # ------------------------------------------------------------- piliers
    with b.group("Piliers"):
        for s in (-1, 1):
            x_in, x_out = s * half, s * xo
            lo, hi = min(x_in, x_out), max(x_in, x_out)
            lo_s, hi_s = (lo - 1, hi) if s < 0 else (lo, hi + 1)
            b.box((lo_s, 0, -PD - 1), (hi_s, 3, PD + 1), c("pave"), studs="top", name="Socle")
            # assises de 4 studs en trois verts proches
            y = 3.0
            k = 0
            while y < y_lin - 0.01:
                y1 = min(y_lin, y + 4)
                col = (PILIER, PILIER_CLAIR, PILIER, PILIER_FONCE)[k % 4]
                b.box((lo, y, -PD), (hi, y1, PD), col, name="Assise")
                y, k = y1, k + 1
            # chambranle (montant de gond) entre le pilier et le vantail
            jl, jh = (x_in - 2.5, x_in) if s < 0 else (x_in, x_in + 2.5)
            b.box((jl, 3, PD), (jh, H, PD + 1), FER, name="Chambranle")
            # chapiteau du pilier
            cl, ch = (lo - 0.5, hi) if s < 0 else (lo, hi + 0.5)   # rien ne déborde dans l'ouverture
            b.box((cl, y_lin - 3, -PD - 0.5), (ch, y_lin - 2, PD + 0.5), CORNICHE, name="Chapiteau")

    # ------------------------------------------------------------- linteau (attique)
    with b.group("Linteau"):
        b.box((-xo - 1.5, y_lin, -PD - 0.5), (xo + 1.5, y_att0, PD + 0.5), CORNICHE, studs="top", name="Corniche_basse")
        b.box((-xo, y_att0, -5.5), (xo, y_att1, 5.5), PILIER, name="Attique")
        b.box((-xo - 2, y_att1, -7.5), (xo + 2, y_toit, 7.5), CORNICHE, name="Corniche_haute")
        ninb = glyph_mask("忍", 19, font="sans", threshold=0.65)
        feuille = spirale_feuille(20)
        pl = 21.0
        xs = (-(half - 10.0), 0.0, half - 10.0)
        yc = (y_att0 + y_att1) / 2
        for sens in (1, -1):
            zf = sens * 5.5
            for xc, m in zip(xs, (ninb, feuille, ninb)):
                # plaque crème encadrée de bois sombre
                b.box((xc - pl / 2, yc - pl / 2, zf), (xc + pl / 2, yc + pl / 2, zf + sens * 0.3), c("panneau"), name="Plaque")
                fz = (zf, zf + sens * 0.6)
                b.box((xc - pl / 2 - 1, yc + pl / 2, fz[0]), (xc + pl / 2 + 1, y_att1, fz[1]), c("bois_fonce"), name="Cadre")
                b.box((xc - pl / 2 - 1, y_att0, fz[0]), (xc + pl / 2 + 1, yc - pl / 2, fz[1]), c("bois_fonce"), name="Cadre")
                b.box((xc - pl / 2 - 1, yc - pl / 2, fz[0]), (xc - pl / 2, yc + pl / 2, fz[1]), c("bois_fonce"), name="Cadre")
                b.box((xc + pl / 2, yc - pl / 2, fz[0]), (xc + pl / 2 + 1, yc + pl / 2, fz[1]), c("bois_fonce"), name="Cadre")
                with b.group("Glyphes"):
                    _glyphe_face(b, m, 1.0, xc, yc, zf + sens * 0.3, sens, 0.5, c("lettre_rouge"), name="Pixel")
            # bandes verticales au droit des piliers
            for s in (-1, 1):
                xm = s * (half + PW / 2)
                b.box((xm - 1.5, y_att0, zf), (xm + 1.5, y_att1, zf + sens * 0.4), CORNICHE, name="Pilastre")

    # ------------------------------------------------------------- toit
    with b.group("Toit"):
        xr = xo + 7.0                       # demi-longueur du toit
        zr = 11.5                           # débord
        y0 = y_toit + 1.5
        y1 = y0 + 8.0
        b.box((-xr + 1, y_toit, -zr), (xr - 1, y0, zr), c("bois_fonce"), name="Rive")
        n = int(round(2 * xr / 4))
        wst = 2 * xr / n
        for i in range(n):
            x0 = -xr + i * wst
            col = tuile if i % 2 == 0 else tuile_f
            b.wedge((x0, y0, -zr), (x0 + wst, y1, 0), col, down="-z", studs="top", name="Tuiles")
            b.wedge((x0, y0, 0), (x0 + wst, y1, zr), col, down="+z", studs="top", name="Tuiles")
            if i % 2 == 0:
                for sz in (-1, 1):
                    b.cyl((x0 + wst / 2, y0 + 0.2, sz * (zr + 0.3)), 0.95, 0.6, FAITAGE, axis="z", name="About", collide=False)
        b.box((-xr - 1, y1 - 1.0, -1.4), (xr + 1, y1 + 1.4, 1.4), FAITAGE, studs="top", name="Faitage")
        # épis de faîtage (onigawara stylisés)
        for s in (-1, 1):
            xa = s * (xr + 1)
            lo, hi = (xa - 2.2, xa) if s < 0 else (xa, xa + 2.2)
            b.box((lo, y1 - 2.0, -2.2), (hi, y1 + 3.2, 2.2), FAITAGE, studs="top", name="Epi")
            b.wedge((lo, y1 + 3.2, -2.2), (hi, y1 + 5.2, 2.2), shade(FAITAGE, 0.9), down="-x" if s > 0 else "+x", name="Epi")
        # chevrons sous l'avant-toit
        for sz in (-1, 1):
            x = -xr + 3
            while x <= xr - 3 + 0.01:
                b.box((x - 0.45, y_toit - 0.9, sz * 7.5), (x + 0.45, y_toit, sz * (zr - 0.8)), c("bois_fonce"), collide=False, name="Chevron")
                x += 4

    # ------------------------------------------------------------- vantaux
    with b.group("Vantaux"):
        _vantail(b, -1, half, H, PD + 1, angle, "あ", rng)
        _vantail(b, 1, half, H, PD + 1, angle, "ん", rng)

    # ------------------------------------------------------------- lanternes des piliers
    with b.group("Lanternes"):
        for s in (-1, 1):
            for sens in (1, -1):
                _lanterne(b, s * (half + PW / 2), 33.0, sens * PD, sens, lampe)

    # ------------------------------------------------------------- rempart
    HM = 30.0         # hauteur du corps du mur
    TM = 3.5          # demi-épaisseur
    cell_w, cell_h = 4, 3
    with b.group("Rempart"):
        for s in (-1, 1):
            if mur <= xo + 4:
                break
            with b.group("Gauche" if s < 0 else "Droite"):
                xe = mur - 4                     # début de la pile d'extrémité
                L = xe - xo
                b.box((s * (xo + 1), 0, -TM - 0.5), (s * xe, 3, TM + 0.5), PIERRE, studs="top", name="Soubassement")
                ncol = int(math.ceil(L / cell_w))
                nrow = int(round((HM - 3) / cell_h))
                motif = _motif_rempart(rng, ncol, nrow)
                teintes = (c("rempart"), REMPART_CLAIR, REMPART_MOYEN, c("rempart_fonce"))
                for k, col in enumerate(teintes):
                    for (x, y, w, h) in mask_rects(motif == k):
                        a0 = xo + x * cell_w
                        a1 = min(xe, xo + (x + w) * cell_w)
                        y_hi = HM - y * cell_h
                        b.box((s * a0, y_hi - h * cell_h, -TM), (s * a1, y_hi, TM), col,
                              studs=("Front", "Back"), name="Enduit")
                # chaperon de tuiles
                b.box((s * xo, HM, -TM - 1), (s * xe, HM + 1, TM + 1), c("bois_fonce"), name="Chaperon")
                b.wedge((s * xo, HM + 1, -TM - 1), (s * xe, HM + 3.4, 0), tuile, down="-z", studs="top", name="Chaperon")
                b.wedge((s * xo, HM + 1, 0), (s * xe, HM + 3.4, TM + 1), tuile_f, down="+z", studs="top", name="Chaperon")
                b.box((s * xo, HM + 3.0, -0.8), (s * xe, HM + 4.2, 0.8), FAITAGE, studs="top", name="Faitage")
                # contreforts sur les deux faces
                xb = xo + 12
                while xb < mur - 6:
                    for sz in (-1, 1):
                        b.box((s * xb - 2, 0, sz * TM), (s * xb + 2, HM - 5, sz * (TM + 2.5)), c("rempart_fonce"),
                              name="Contrefort")
                        b.wedge((s * xb - 2, HM - 5, sz * TM), (s * xb + 2, HM - 2.5, sz * (TM + 2.5)), shade(c("rempart_fonce"), 0.92),
                                down="+z" if sz > 0 else "-z", studs="top", name="Contrefort")
                    xb += 24
                # pile d'extrémité
                b.box((s * xe, 0, -TM - 1.5), (s * mur, HM + 4.6, TM + 1.5), PIERRE_FONCE, name="Pile")
                b.box((s * (xe - 0.5), HM + 4.6, -TM - 2), (s * mur, HM + 5.6, TM + 2), FAITAGE, studs="top", name="Pile")

    # ------------------------------------------------------------- tuyaux (côté droit, face extérieure)
    with b.group("Tuyaux"):
        r = 2.4
        zc = TM + 2.5 + 0.4 + r
        x_dep = xo + 5
        if mur > x_dep + 40:
            fins = [min(mur - 8 - 12, x_dep + 100) + d for d in (0, 6, 12)]
            for (yp, xf) in zip((14.5, 20.0, 25.5), fins):
                gris = c("tuyau")
                b.cyl((x_dep, yp, (TM + zc) / 2), r, zc - TM, gris, axis="z", name="Tuyau")
                b.ball((x_dep, yp, zc), r, gris, name="Coude")
                b.cyl(((x_dep + xf) / 2, yp, zc), r, xf - x_dep, gris, axis="x", name="Tuyau")
                b.ball((xf, yp, zc), r, gris, name="Coude")
                b.cyl((xf, yp / 2 + 0.6, zc), r, yp - 1.2, gris, axis="y", name="Tuyau")
                b.box((xf - 2.9, 0, zc - 2.9), (xf + 2.9, 1.2, zc + 2.9), PIERRE_FONCE, studs="top", name="Massif")
                b.cyl((x_dep, yp, TM + 0.4), r + 0.5, 0.8, c("metal_fonce"), axis="z", name="Bride")
                b.cyl((xf, 2.4, zc), r + 0.5, 0.8, c("metal_fonce"), axis="y", name="Bride")
                xb = xo + 12
                while xb < xf - 3:
                    b.cyl((xb, yp, zc), r + 0.45, 1.0, c("metal_fonce"), axis="x", name="Bride")
                    xb += 24
            # colliers : pattes fixées aux contreforts
            xb = xo + 12
            while xb < fins[0] - 3:
                b.box((xb - 0.6, 12.0, TM + 2.5), (xb + 0.6, 28.0, zc), FER, name="Collier")
                xb += 24

    # ------------------------------------------------------------- guérite (côté village, à gauche)
    with b.group("Guerite"):
        toit_g = (c("toit_rouge"), c("toit_brun"), c("toit_rouge"), c("toit_orange"))[v]
        with b.at((-(half + 6), 0, -18), yaw=-90):
            _guerite(b, rng, toit_g)

    z_min = -26.0
    z_max = PD + 1 + half * math.sin(math.radians(angle)) + 0.5
    return {"emprise": (2 * mur, round(z_max - z_min, 1)), "hauteur": round(y_toit + 1.5 + 8 + 5.2, 1), "ouverture": ouverture}
