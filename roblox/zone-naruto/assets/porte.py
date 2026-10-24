"""Porte principale de Konoha (« porte A-Un ») : entrée de la zone Naruto.

Repère : origine au centre de l'ouverture, au sol ; le plan de la porte et du rempart est centré sur z = 0.
L'EXTÉRIEUR (d'où arrivent les joueurs) est +Z ; le village et le couloir de course s'étendent vers -Z.
Exception à la règle « l'avant regarde -Z » : la face principale est la face +Z, mais la face -Z est vue
au retour, elle est donc soignée aussi.

Éléments :
- deux piliers massifs en enduit crème (assises « pixel » en trois tons) sur socle de pierre ;
- un linteau à colombages (poutres brun sombre) portant 忍 · spirale de la feuille · 忍 en pixels rouges,
  sur les deux faces ; consoles sous la corniche ;
- un grand toit de tuiles vert-de-gris à deux pans (rangs de tuiles en deux tons, abouts ronds, faîtage, épis) ;
- deux immenses vantaux vert pâle ouverts vers l'extérieur (あ à gauche, ん à droite, sur la face tournée
  vers le couloir), planches, cadre, pentures de fer ;
- le rempart en enduit orangé à motif « pixel » (studs sur les faces), chaperon de tuiles, contreforts ;
- trois gros tuyaux gris le long du rempart droit (x > 0, face extérieure) qui plongent au sol au bout ;
- une petite guérite de gardes côté village, à gauche (bureau, deux tabourets, lampion).
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, shade
from palette import c, vary
from textures import glyph_mask, mask_rects

# Couleurs locales (en plus de la palette)
CREME = "#EADCBC"          # enduit des piliers
CREME_CLAIR = "#F2E7CC"
CREME_FONCE = "#DFCDA6"
PLAQUE = "#F6EEDB"         # fond des signes du linteau
BOIS_SOMBRE = "#4E3020"    # colombages, consoles
FAITAGE = "#56654A"        # faîtage et épis
FER = "#3A3F44"            # ferrures, pentures
PIERRE = "#BDB3A0"
PIERRE_FONCE = "#A39985"
REMPART_CLAIR = "#EBBF8E"
REMPART_MOYEN = "#D49B60"
JOINT_PORTE = "#7DAE87"    # âme des vantaux, visible dans les joints des planches


# ----------------------------------------------------------------------------
# Motifs pixel
# ----------------------------------------------------------------------------

def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-12), 0, 1)
    return np.hypot(px - (ax + t * dx), py - (ay + t * dy))


def spirale_feuille(n: int = 24) -> np.ndarray:
    """Emblème de la feuille de Konoha en pixels (n × n, lignes = haut → bas), dessiné sans police :
    spirale en haut à droite, queue effilée qui descend en bas à gauche, petite pointe triangulaire à gauche."""
    ss = 8
    g = (np.arange(n * ss) + 0.5) / (n * ss)
    X, Y = np.meshgrid(g, g)
    cx, cy, r0, r1, turns = 0.60, 0.39, 0.03, 0.37, 1.6
    w_out, w_in = 0.08, 0.07 * 0.55
    pts = []
    m = 300
    for i in range(m + 1):
        s = i / m
        th = math.pi + turns * 2 * math.pi * (1 - s)   # de l'intérieur vers l'extérieur ; finit à gauche
        r = r0 + (r1 - r0) * s ** 0.9
        pts.append((cx + r * math.cos(th), cy + r * math.sin(th), w_in + (w_out - w_in) * s))
    ex, ey, ew = pts[-1]
    mid, tip = (ex - 0.05, ey + 0.22), (0.05, 0.97)
    for i in range(1, 81):
        s = i / 80
        bx = (1 - s) ** 2 * ex + 2 * (1 - s) * s * mid[0] + s * s * tip[0]
        by = (1 - s) ** 2 * ey + 2 * (1 - s) * s * mid[1] + s * s * tip[1]
        pts.append((bx, by, ew * (1 - 0.85 * s)))
    inside = np.zeros(X.shape, bool)
    for (ax, ay, wa), (bx, by, wb) in zip(pts[:-1], pts[1:]):
        inside |= _seg_dist(X, Y, ax, ay, bx, by) <= (wa + wb) / 2
    # pointe de feuille à gauche
    (ax, ay), (bx, by), (qx, qy) = (0.04, 0.40), (0.24, 0.33), (0.21, 0.53)

    def edge(ax, ay, bx, by):
        return (bx - ax) * (Y - ay) - (by - ay) * (X - ax)

    e0, e1, e2 = edge(ax, ay, bx, by), edge(bx, by, qx, qy), edge(qx, qy, ax, ay)
    inside |= ((e0 >= 0) & (e1 >= 0) & (e2 >= 0)) | ((e0 <= 0) & (e1 <= 0) & (e2 <= 0))
    return inside.reshape(n, ss, n, ss).mean(axis=(1, 3)) > 0.45


def _motif_rempart(rng, ncol: int, nrow: int) -> np.ndarray:
    """Indices de teinte par case (0 = base, 1 = clair, 2 = moyen, 3 = foncé), comme les murs stud de la
    référence : des traînées horizontales de 2 à 6 cases, regroupées en taches en escalier par un bruit grossier."""
    gx, gy = ncol // 6 + 3, nrow // 3 + 3
    coarse = rng.random((gy, gx))
    out = np.zeros((nrow, ncol), int)
    for y in range(nrow):
        x = int(rng.integers(0, 3))
        while x < ncol:
            w = int(rng.integers(2, 7))
            xm = min(ncol - 1, x + w // 2)
            f = coarse[int(y / 3.0) + 1][int(xm / 6.0) + 1] * 0.8 + rng.random() * 0.2
            out[y, x:x + w] = 1 if f > 0.66 else (3 if f < 0.16 else (2 if f < 0.34 else 0))
            x += w
    return out


# ----------------------------------------------------------------------------
# Sous-ensembles
# ----------------------------------------------------------------------------

def _glyphe_face(b, mask, p, xc, yc, z_face, sens, prof, couleur, **kw):
    """Pose un masque de pixels (lignes haut → bas) sur une face verticale perpendiculaire à Z.

    sens = +1 : face qui regarde +Z (colonnes vers +X) ; sens = -1 : face qui regarde -Z (colonnes vers -X),
    pour que le signe se lise à l'endroit des deux côtés. Les pixels vont de z_face à z_face + sens * prof.
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
    fonce = c("porte_vert_fonce")

    with b.at((side * half, 0, z_gond), yaw=yaw):
        def box(u0, u1, v0, v1, w0, w1, col, **kw):
            return b.box((u0, v0, zs * w0), (u1, v1, zs * w1), col, **kw)

        # âme (visible dans les joints) puis cadre (montants, traverses) et planches verticales
        box(0.6, W - 0.6, 0.6, H - 0.6, 0.35, T - 0.35, JOINT_PORTE)
        box(0, 2.4, 0, H, -0.3, T + 0.3, fonce, name="Montant")
        box(W - 2.4, W, 0, H, -0.3, T + 0.3, fonce, name="Montant")
        box(2.4, W - 2.4, H - 3.0, H, -0.3, T + 0.3, fonce, name="Traverse")
        box(2.4, W - 2.4, 0, 3.0, -0.3, T + 0.3, fonce, name="Traverse")
        box(2.4, W - 2.4, H * 0.5 - 0.8, H * 0.5 + 0.8, T, T + 0.3, fonce, name="Traverse")  # dos seulement
        n_pl = max(3, int(round((W - 4.8) / 5.2)))
        pw = (W - 4.8) / n_pl
        for i in range(n_pl):
            u0 = 2.4 + i * pw
            box(u0 + (0.15 if i else 0), u0 + pw - (0.15 if i < n_pl - 1 else 0), 3.0, H - 3.0, 0, T,
                vary("porte_vert", rng, 0.03), name="Planche")

        # pentures (bandes de fer) : longues sur la face arrière, courtes côté couloir (hors lettre)
        for vb in (H * 0.15, H * 0.85):
            box(-0.3, W * 0.55, vb - 1.0, vb + 1.0, T + 0.3, T + 0.7, FER, name="Penture")
            box(-0.3, 3.4, vb - 1.0, vb + 1.0, -0.7, -0.3, FER, name="Penture")
            b.cyl((0, vb, zs * T / 2), 1.1, 2.8, FER, axis="y", name="Gond")
        # gros clous sur la face arrière (sur la traverse du milieu)
        for k in range(5):
            uu = W * (0.62 + 0.08 * k)
            b.cyl((uu, H * 0.5, zs * (T + 0.55)), 0.55, 0.5, FER, axis="z", name="Clou", collide=False)
        # poignée en anneau côté couloir, au bout du vantail
        box(W - 1.9, W - 0.9, H * 0.5 - 2.5, H * 0.5 + 2.5, -0.9, -0.3, FER, name="Poignee", collide=False)

        # grande lettre rouge sur la face côté couloir
        m = glyph_mask(lettre, 22, font="sans", threshold=0.5)
        p = 1.25
        nr, nc = m.shape
        uc, vc = W / 2 + 0.2, H / 2 + 1.0
        for (x, y, w, h) in mask_rects(m):
            vt = vc + nr * p / 2 - y * p
            if side < 0:   # face côté couloir vue depuis +x : les colonnes de l'image vont vers -u
                u1 = uc + nc * p / 2 - x * p
                u0 = u1 - w * p
            else:          # vantail droit, vu depuis -x : les colonnes vont vers +u
                u0 = uc - nc * p / 2 + x * p
                u1 = u0 + w * p
            box(u0, u1, vt - h * p, vt, -0.55, 0, c("lettre_rouge"), name="Lettre")


def _lanterne(b, x, y_attache, z_mur, sens, couleur):
    """Lanterne ronde suspendue à une potence fixée sur une face (z_mur), saillie vers sens·Z."""
    zc = z_mur + sens * 3.6
    b.box((x - 0.3, y_attache - 0.6, z_mur), (x + 0.3, y_attache, zc + sens * 0.3), FER, collide=False, name="Potence")
    b.box((x - 0.15, y_attache - 1.6, zc - 0.15), (x + 0.15, y_attache - 0.6, zc + 0.15), FER, collide=False)
    b.cyl((x, y_attache - 1.9, zc), 0.8, 0.6, c("noir"), axis="y", collide=False)
    b.ball((x, y_attache - 4.3, zc), 2.3, couleur, material="Neon", collide=False, name="Lanterne")
    b.cyl((x, y_attache - 6.75, zc), 0.8, 0.5, c("noir"), axis="y", collide=False)


def _guerite(b, rng, toit, lampe):
    """Petite guérite en bois (repère local : avant = -Z), 9 × 8 au sol : bureau, deux tabourets, lampion."""
    bois, bois_c, bois_f, poutre = c("bois"), c("bois_clair"), c("bois_fonce"), c("poutre")
    b.box((-4.5, 0, -4), (4.5, 0.6, 4), bois_f, studs="top", name="Plancher")
    # mur du fond et murets latéraux, poteaux d'angle
    b.box((-4.5, 0.6, 3), (4.5, 9.6, 4), vary("bois", rng), material="WoodPlanks", name="Fond")
    for sx in (-1, 1):
        b.box((sx * 3.7, 0.6, -2.8), (sx * 4.5, 4.0, 3), bois, material="WoodPlanks", name="Muret")
        b.box((sx * 3.6, 4.0, -2.8), (sx * 4.6, 4.4, 3), bois_c, studs="top", name="Lisse")
        b.box((sx * 3.7, 0.6, -4), (sx * 4.5, 9.6, -2.8), poutre, name="Poteau")
    b.box((-4.5, 8.6, -4.3), (4.5, 9.6, -2.8), poutre, name="Linteau")
    # bureau (comptoir) à l'avant
    b.box((-3.7, 0.6, -4), (3.7, 3.6, -3.0), bois, material="WoodPlanks", name="Bureau")
    b.box((-4.0, 3.6, -4.6), (4.0, 4.1, -2.2), bois_c, studs="top", name="Plateau")
    b.box((-2.6, 4.1, -4.1), (-0.6, 4.25, -2.7), c("blanc"), collide=False, name="Papiers")
    b.box((0.0, 4.1, -4.0), (1.6, 4.4, -2.8), c("panneau"), collide=False, name="Registre")
    b.cyl((2.6, 4.45, -3.4), 0.35, 0.7, c("noir"), axis="y", collide=False, name="Encrier")
    # deux tabourets derrière le bureau
    for x in (-1.8, 1.8):
        b.cyl((x, 1.6, 0.0), 0.35, 2.0, bois_f, axis="y", name="Pied")
        b.cyl((x, 2.85, 0.0), 1.0, 0.5, bois_c, axis="y", studs="top", name="Tabouret")
    # enseigne sous le linteau
    s = b.box((-2.4, 7.0, -4.55), (2.4, 8.6, -4.3), c("panneau"), collide=False, name="Enseigne")
    s.label = {"face": "Front", "text": "受付", "color": (60, 35, 25), "bg": None, "font": "brush"}
    # toit à deux pans (faîtage le long de X local), débord 1 stud
    b.box((-5.5, 9.6, -5), (5.5, 10.2, 5), bois_f, name="Rive")
    b.wedge((-5.5, 10.2, -5), (5.5, 12.6, 0), toit, down="-z", studs="top", name="Toit")
    b.wedge((-5.5, 10.2, 0), (5.5, 12.6, 5), shade(toit, 0.9), down="+z", studs="top", name="Toit")
    b.box((-5.8, 12.2, -0.6), (5.8, 13.0, 0.6), shade(toit, 0.7), studs="top", name="Faitage")
    # lampion accroché sous l'avant-toit, à l'angle avant
    b.box((3.85, 8.8, -4.75), (4.15, 9.6, -4.45), c("noir"), collide=False)
    b.cyl((4.0, 8.55, -4.6), 0.45, 0.5, c("noir"), axis="y", collide=False)
    b.cyl((4.0, 7.3, -4.6), 0.8, 2.0, lampe, axis="y", material="Neon", collide=False, name="Lampion")
    b.cyl((4.0, 6.05, -4.6), 0.45, 0.5, c("noir"), axis="y", collide=False)


# ----------------------------------------------------------------------------
# Asset principal
# ----------------------------------------------------------------------------

def porte_konoha(b, variant: int = 0, ouverture: float = 72, hauteur: float = 46, mur: float = 170) -> dict:
    """Porte A-Un de Konoha + rempart. Voir le docstring du module pour le repère (extérieur = +Z)."""
    rng = b.rng
    v = variant % 4
    half = ouverture / 2
    H = hauteur
    PW = 12.0                     # largeur d'un pilier
    PD = 7.0                      # demi-profondeur des piliers
    xo = half + PW                # face extérieure des piliers
    y_lin = H + 1                 # sous-face du linteau (hauteur libre)
    y_b0, y_b1 = y_lin + 3, y_lin + 30          # bandeau des signes (entre deux poutres)
    y_top = y_b1 + 3                             # dessus de la poutre haute
    tuile = (c("rempart_tuile"), mix(c("rempart_tuile"), c("toit_bleu"), 0.22),
             mix(c("rempart_tuile"), c("toit_vert"), 0.35), shade(c("rempart_tuile"), 0.92))[v]
    tuile_f = shade(tuile, 0.86)
    lampe = (c("orange_lampion"), c("rouge"), c("jaune_lampion"), c("orange_lampion"))[v]
    # angle d'ouverture : les bouts des vantaux restent à |x| ≥ 31 (couloir dégagé)
    angle = math.degrees(math.acos(max(0.0, min(1.0, (half - 32.4) / half)))) + (0, 0.5, 1.0, 0.3)[v]
    angle = max(80.0, min(85.0, angle))
    tons_pilier = (CREME, CREME_CLAIR, CREME_FONCE)

    # ------------------------------------------------------------- piliers
    with b.group("Piliers"):
        for s in (-1, 1):
            x_in, x_out = s * half, s * xo
            lo, hi = min(x_in, x_out), max(x_in, x_out)

            def span(a0, a1):
                """Intervalle en x mesuré depuis l'ouverture (a = 0 au bord de l'ouverture)."""
                xa, xb = x_in + s * a0, x_in + s * a1
                return min(xa, xb), max(xa, xb)

            # socle de pierre (ne déborde pas dans l'ouverture)
            sa, sb = span(0, PW + 1)
            b.box((sa, 0, -PD - 1), (sb, 4, PD + 1), c("pave"), studs="top", name="Socle")
            sa, sb = span(0, PW + 0.5)
            b.box((sa, 4, -PD - 0.5), (sb, 5, PD + 0.5), PIERRE_FONCE, studs="top", name="Socle")
            # assises « pixel » : blocs décalés d'une assise à l'autre, trois tons proches
            y, k, prev = 5.0, 0, -1
            while y < y_lin - 2.01:
                y1 = min(y_lin - 2, y + 4)
                cut = (7, 5)[k % 2]
                for (a0, a1) in ((0, cut), (cut, PW)):
                    t = int(rng.integers(3))
                    if t == prev:
                        t = (t + 1) % 3
                    prev = t
                    xa, xb = span(a0, a1)
                    b.box((xa, y, -PD), (xb, y1, PD), tons_pilier[t], name="Assise")
                y, k = y1, k + 1
            # chapiteau en bois sombre
            sa, sb = span(0, PW + 0.5)
            b.box((sa, y_lin - 2, -PD - 0.5), (sb, y_lin, PD + 0.5), BOIS_SOMBRE, name="Chapiteau")
            # montant de gond (fer) le long de l'arête extérieure côté ouverture
            jl, jh = span(0, 2.0)
            b.box((jl, 5, PD), (jh, y_lin - 2, PD + 1.1), FER, name="Chambranle")

    # ------------------------------------------------------------- linteau à colombages
    with b.group("Linteau"):
        xl = xo + 1
        b.box((-xl, y_lin, -PD - 0.5), (xl, y_b0, PD + 0.5), BOIS_SOMBRE, name="Poutre_basse")
        b.box((-xo, y_b0, -5.5), (xo, y_b1, 5.5), PLAQUE, name="Bandeau")
        b.box((-xl, y_b1, -PD - 0.5), (xl, y_top, PD + 0.5), BOIS_SOMBRE, name="Poutre_haute")
        # 3 panneaux de 28 séparés par des poteaux de 3 (colombages en saillie de 1 stud)
        post = 3.0
        pw = (2 * xo - 4 * post) / 3          # 28 pour une ouverture de 72
        xs = (-(pw + post), 0.0, pw + post)
        posts = [-xo, -pw / 2 - post, pw / 2, xo - post]
        ninb = glyph_mask("忍", 24, font="sans", threshold=0.5)
        feuille = spirale_feuille(24)
        yc = (y_b0 + y_b1) / 2
        for sens in (1, -1):
            zf = sens * 5.5
            for x0 in posts:
                b.box((x0, y_b0, zf), (x0 + post, y_b1, zf + sens * 1.0), BOIS_SOMBRE, name="Colombage")
            with b.group("Glyphes"):
                for xc, m in zip(xs, (ninb, feuille, ninb)):
                    _glyphe_face(b, m, 1.0, xc, yc, zf, sens, 0.6, c("lettre_rouge"), name="Pixel")
            # consoles sous la corniche (petits blocs de bois) devant une frise crème
            if sens > 0:
                b.box((-xo, y_top, -5.5), (xo, y_top + 2, 5.5), CREME_FONCE, name="Frise")
            x = -xo + 2
            while x <= xo - 2 + 0.01:
                b.box((x - 0.8, y_top, sens * 5.5), (x + 0.8, y_top + 2, sens * 9.0), BOIS_SOMBRE, name="Console",
                      collide=False)
                x += 8

    # ------------------------------------------------------------- toit
    y_rive = y_top + 2
    with b.group("Toit"):
        xr = xo + 10.0                      # demi-longueur du toit
        zr = 16.0                           # débord
        y0 = y_rive + 1.5
        y1 = y0 + 13.0
        b.box((-xr + 1, y_rive, -zr + 1), (xr - 1, y0, zr - 1), c("bois_fonce"), name="Rive")
        n = int(round(2 * xr / 4))
        wst = 2 * xr / n
        for i in range(n):
            x0 = -xr + i * wst
            col = tuile if i % 2 == 0 else tuile_f
            b.wedge((x0, y0, -zr), (x0 + wst, y1, 0), col, down="-z", studs="top", name="Tuiles")
            b.wedge((x0, y0, 0), (x0 + wst, y1, zr), col, down="+z", studs="top", name="Tuiles")
            if i % 2 == 0:
                for sz in (-1, 1):
                    b.cyl((x0 + wst / 2, y0 + 0.5, sz * (zr + 0.25)), 1.0, 0.5, FAITAGE, axis="z", name="About",
                          collide=False)
        # faîtage et épis (onigawara stylisés)
        b.box((-xr - 0.5, y1 - 1.2, -2.0), (xr + 0.5, y1 + 1.8, 2.0), FAITAGE, studs="top", name="Faitage")
        b.box((-xr + 2, y1 + 1.8, -1.2), (xr - 2, y1 + 2.6, 1.2), shade(FAITAGE, 1.12), studs="top", name="Faitage")
        for s in (-1, 1):
            xa = s * (xr + 0.5)
            lo, hi = (xa - 3.0, xa) if s < 0 else (xa, xa + 3.0)
            b.box((lo, y1 - 2.6, -2.8), (hi, y1 + 3.6, 2.8), FAITAGE, studs="top", name="Epi")
            b.wedge((lo, y1 + 3.6, -2.8), (hi, y1 + 7.0, 2.8), shade(FAITAGE, 0.9), down="-x" if s > 0 else "+x",
                    name="Epi")
        # chevrons sous l'avant-toit, entre la corniche et le bord du toit
        for sz in (-1, 1):
            x = -xr + 3
            while x <= xr - 3 + 0.01:
                b.box((x - 0.5, y_rive - 1.0, sz * 9.0), (x + 0.5, y_rive, sz * (zr - 1.5)), c("bois_fonce"),
                      collide=False, name="Chevron")
                x += 6
        # pignons : planches de rive sombres
        for s in (-1, 1):
            xa = s * xr
            lo, hi = (xa - 0.6, xa) if s < 0 else (xa, xa + 0.6)
            b.wedge((lo, y0 - 0.5, -zr - 0.5), (hi, y1 + 0.5, 0), c("bois_fonce"), down="-z", name="Pignon")
            b.wedge((lo, y0 - 0.5, 0), (hi, y1 + 0.5, zr + 0.5), c("bois_fonce"), down="+z", name="Pignon")
            # disque décoratif (gegyo) sous le faîtage
            b.cyl((xa + s * 0.85, y1 - 5.0, 0), 1.8, 0.5, c("jaune_lampion"), axis="x", name="Gegyo", collide=False)
    y_faite = y1 + 7.0

    # ------------------------------------------------------------- vantaux
    with b.group("Vantaux"):
        _vantail(b, -1, half, H, PD + 1.4, angle, "あ", rng)
        _vantail(b, 1, half, H, PD + 1.4, angle, "ん", rng)

    # ------------------------------------------------------------- lanternes des piliers
    with b.group("Lanternes"):
        for s in (-1, 1):
            for sens in (1, -1):
                _lanterne(b, s * (half + PW / 2), 34.0, sens * PD, sens, lampe)

    # ------------------------------------------------------------- rempart
    HM = 30.0         # hauteur du corps du mur
    TM = 3.5          # demi-épaisseur
    cell_w, cell_h = 4, 3
    teintes = (c("rempart"), REMPART_CLAIR, REMPART_MOYEN, c("rempart_fonce"))
    with b.group("Rempart"):
        for s in (-1, 1):
            if mur <= xo + 8:
                break
            with b.group("Gauche" if s < 0 else "Droite"):
                xe = mur - 5                     # début de la pile d'extrémité
                L = xe - xo
                b.box((s * xo, 0, -TM - 0.6), (s * xe, 3, TM + 0.6), PIERRE, studs="top", name="Soubassement")
                ncol = int(math.ceil(L / cell_w))
                nrow = int(round((HM - 3) / cell_h))
                motif = _motif_rempart(rng, ncol, nrow)
                for k, col in enumerate(teintes):
                    for (x, y, w, h) in mask_rects(motif == k):
                        a0 = xo + x * cell_w
                        a1 = min(xe, xo + (x + w) * cell_w)
                        if a1 - a0 < 0.1:
                            continue
                        y_hi = HM - y * cell_h
                        b.box((s * a0, y_hi - h * cell_h, -TM), (s * a1, y_hi, TM), col,
                              studs=("Front", "Back"), name="Enduit")
                # chaperon : poutre, deux pans de tuiles, faîtage
                b.box((s * xo, HM, -TM - 0.5), (s * xe, HM + 1, TM + 0.5), c("bois_fonce"), name="Chaperon")
                b.wedge((s * xo, HM + 1, -TM - 1.5), (s * xe, HM + 3.4, 0), tuile, down="-z", studs="top", name="Chaperon")
                b.wedge((s * xo, HM + 1, 0), (s * xe, HM + 3.4, TM + 1.5), tuile_f, down="+z", studs="top", name="Chaperon")
                b.box((s * xo, HM + 3.0, -0.8), (s * xe, HM + 4.2, 0.8), FAITAGE, studs="top", name="Faitage")
                xa = xo + 4
                while xa < xe - 2:
                    for sz in (-1, 1):
                        b.cyl((s * xa, HM + 1.5, sz * (TM + 1.25)), 0.7, 0.5, FAITAGE, axis="z", name="About",
                              collide=False)
                    xa += 8
                # contreforts sur les deux faces
                xb = xo + 12
                while xb < xe - 6:
                    for sz in (-1, 1):
                        z0, z1 = sz * (TM + 0.6), sz * (TM + 3.0)
                        b.box((s * xb - 2, 3, sz * TM), (s * xb + 2, HM - 8, z1), c("rempart_fonce"), name="Contrefort")
                        b.box((s * xb - 2.5, 0, z0), (s * xb + 2.5, 3, sz * (TM + 3.5)), PIERRE_FONCE, studs="top",
                              name="Contrefort")
                        b.wedge((s * xb - 2.5, HM - 8, sz * TM), (s * xb + 2.5, HM - 5, sz * (TM + 3.5)), tuile_f,
                                down="+z" if sz > 0 else "-z", studs="top", name="Contrefort")
                    xb += 24
                # pile d'extrémité
                b.box((s * xe, 0, -TM - 1.5), (s * mur, HM + 4.6, TM + 1.5), PIERRE_FONCE, name="Pile")
                b.box((s * (xe - 0.5), HM + 4.6, -TM - 2), (s * mur, HM + 5.6, TM + 2), FAITAGE, studs="top", name="Pile")

    # ------------------------------------------------------------- tuyaux (côté droit, face extérieure)
    with b.group("Tuyaux"):
        r = 2.4
        zc = TM + 3.0 + 0.5 + r              # devant les contreforts
        x_dep = xo + 5
        if mur > x_dep + 40:
            fins = [min(mur - 5 - 26, x_dep + 100) + d for d in (0, 7, 14)]
            gris = c("tuyau")
            for (yp, xf) in zip((15.0, 20.5, 26.0), fins):
                b.cyl((x_dep, yp, (TM + zc) / 2), r, zc - TM, gris, axis="z", name="Tuyau")
                b.ball((x_dep, yp, zc), r, gris, name="Coude")
                b.cyl(((x_dep + xf) / 2, yp, zc), r, xf - x_dep, gris, axis="x", name="Tuyau")
                b.ball((xf, yp, zc), r, gris, name="Coude")
                b.cyl((xf, (yp + 1.2) / 2, zc), r, yp - 1.2, gris, axis="y", name="Tuyau")
                b.box((xf - 3, 0, zc - 3), (xf + 3, 1.2, zc + 3), PIERRE_FONCE, studs="top", name="Massif")
                b.cyl((x_dep, yp, TM + 0.4), r + 0.5, 0.8, c("metal_fonce"), axis="z", name="Bride")
                b.cyl((xf, 2.6, zc), r + 0.5, 0.8, c("metal_fonce"), axis="y", name="Bride")
                xb = xo + 12
                while xb < xf - 4:
                    b.cyl((xb + 4, yp, zc), r + 0.45, 1.0, c("metal_fonce"), axis="x", name="Bride")
                    xb += 24
            # colliers : pattes fixées aux contreforts, qui tiennent les trois tuyaux
            xb = xo + 12
            while xb < fins[0] - 3:
                b.box((xb - 0.5, 12.0, TM + 3.0), (xb + 0.5, 29.0, zc - r + 0.3), c("metal_fonce"), name="Collier")
                for yp in (12.0, 17.75, 23.25, 28.0):
                    b.box((xb - 0.5, yp, zc - r + 0.3), (xb + 0.5, yp + 1.0, zc + 0.5), c("metal_fonce"), name="Collier")
                xb += 24

    # ------------------------------------------------------------- tableau d'affichage (côté village, à droite)
    if mur > xo + 40:
        with b.group("Affichage"):
            xa, xb2, z0 = xo + 15, xo + 27, -TM
            b.box((xa, 5.5, z0 - 0.8), (xb2, 15.5, z0), c("bois"), material="WoodPlanks", name="Tableau")
            b.box((xa - 0.5, 15.5, z0 - 1.8), (xb2 + 0.5, 16.2, z0), c("bois_fonce"), name="Auvent")
            b.wedge((xa - 0.5, 16.2, z0 - 1.8), (xb2 + 0.5, 17.2, z0), tuile, down="-z", studs="top", name="Auvent")
            for xp in (xa + 0.5, xb2 - 1.5):
                b.box((xp, 0, z0 - 1.6), (xp + 1, 15.5, z0 - 0.8), c("bois_fonce"), name="Pied")
            feuilles = ((1.8, 9.6, 3.0, 4.2), (5.4, 10.6, 2.8, 3.6), (8.6, 9.2, 1.7, 4.4), (2.4, 6.6, 3.2, 2.4),
                        (6.2, 6.8, 2.2, 3.0))
            for k, (dx, y0f, w, h) in enumerate(feuilles):
                col = c("blanc") if k != 2 else c("panneau")
                b.box((xa + dx, y0f, z0 - 1.0), (xa + dx + w, y0f + h, z0 - 0.8), col, collide=False, name="Affiche")
            # tampon rouge (feuille de Konoha stylisée) sur une affiche
            b.box((xa + 8.95, 12.2, z0 - 1.15), (xa + 9.95, 13.2, z0 - 1.0), c("lettre_rouge"), collide=False,
                  name="Tampon")

    # ------------------------------------------------------------- guérite (côté village, à gauche)
    with b.group("Guerite"):
        toit_g = (c("toit_rouge"), c("toit_brun"), c("toit_rouge"), c("toit_orange"))[v]
        with b.at((-(half + 6), 0, -14.25), yaw=-90):
            _guerite(b, rng, toit_g, lampe)

    z_min = -(PD + 1 + 13.0)
    z_max = PD + 1.4 + half * math.sin(math.radians(angle)) + 0.5
    return {"emprise": (2 * max(mur, xo + 10), round(z_max - z_min, 1)), "hauteur": round(y_faite, 1),
            "ouverture": ouverture}
