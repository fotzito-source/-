"""Porte principale de Konoha (« porte A-Un ») : entrée de la zone Naruto.

Repère : origine au centre de l'ouverture, au sol ; le plan de la porte et du rempart est centré sur z = 0.
L'EXTÉRIEUR (d'où arrivent les joueurs) est +Z ; le village et le couloir de course s'étendent vers -Z.
Exception à la règle « l'avant regarde -Z » : la face principale est la face +Z, mais la face -Z est vue
au retour, elle est donc soignée aussi.

Éléments :
- deux piliers massifs en enduit crème (assises « pixel » en trois tons), montants de bois sombre, socle de
  pierre à deux degrés, chapiteau à deux degrés ;
- un linteau à poutres sombres : bandeau crème portant 忍 en pixels rouges de part et d'autre d'un grand
  cadre (gaku) où la spirale de la feuille de Konoha est en relief ; le tout sur les deux faces ;
- un grand toit de tuiles vert-de-gris au profil japonais (pente basse douce, pente haute raide), rangs de
  tuiles en deux tons, abouts ronds, faîtage, épis et pignons sombres à disque doré ;
- deux immenses vantaux vert pâle ouverts vers l'extérieur (あ à gauche, ん à droite, sur la face tournée
  vers le couloir), planches, cadre, clous de fer, pentures ;
- deux grands lampions rouges (chōchin) suspendus sous le linteau, deux lanternes sur la face village ;
- le rempart en enduit orangé à motif « pixel » (studs sur les faces), chaperon de tuiles, contreforts ;
- trois gros tuyaux gris le long du rempart droit (x > 0, face extérieure) qui plongent au sol au bout ;
- une petite guérite de gardes côté village, à gauche (bureau, deux tabourets, lampion), un tableau
  d'affichage côté village, à droite.

Les glyphes (あ, ん, 忍, feuille) sont dessinés en pixels au « pinceau carré » le long de tracés faits à la
main : à cette taille (22 à 28 cases), une police pixelisée donne des traits irréguliers et des bavures.
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
BOIS_SOMBRE = "#4E3020"    # poutres, cadres, consoles
FAITAGE = "#56654A"        # faîtage, épis, abouts
FER = "#3A3F44"            # ferrures, pentures, clous
OR = "#D9A23E"             # ferrures dorées (coins du gaku, disques des pignons)
LAQUE = "#A3281F"          # laque rouge du cadre central (gaku)
PIERRE = "#BDB3A0"
PIERRE_FONCE = "#A39985"
REMPART_CLAIR = "#EBBF8E"
REMPART_MOYEN = "#D49B60"
JOINT_PORTE = "#7DAE87"    # âme des vantaux, visible dans les joints des planches


# ----------------------------------------------------------------------------
# Glyphes pixel : tracés au pinceau carré (cases de la grille, y vers le bas)
# ----------------------------------------------------------------------------

def _bresenham(x0: int, y0: int, x1: int, y1: int) -> list:
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return pts
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _trace(w: int, h: int, traits) -> np.ndarray:
    """Masque w × h : chaque trait est une polyligne (points en cases) peinte avec un pinceau (bw, bh)."""
    m = np.zeros((h, w), bool)
    for pts, (bw, bh) in traits:
        pts = [(int(round(x)), int(round(y))) for x, y in pts]
        segs = list(zip(pts[:-1], pts[1:])) or [(pts[0], pts[0])]
        for a, z in segs:
            for x, y in _bresenham(*a, *z):
                x0, y0 = x - bw // 2, y - bh // 2
                m[max(0, y0):max(0, y0 + bh), max(0, x0):max(0, x0 + bw)] = True
    return m


def _remplir(m: np.ndarray, poly) -> np.ndarray:
    """Remplit un polygone convexe (coordonnées en cases) dans le masque."""
    h, w = m.shape
    Y, X = np.mgrid[0:h, 0:w] + 0.5
    poly = list(poly)
    signes = [(bx - ax) * (Y - ay) - (by - ay) * (X - ax) for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1])]
    m |= np.all([s >= 0 for s in signes], axis=0) | np.all([s <= 0 for s in signes], axis=0)
    return m


_P3 = (3, 3)


def masque_a() -> np.ndarray:
    """あ (26 × 28 cases) : barre, verticale, diagonale et boucle, traits de 3 cases."""
    return _trace(26, 28, [
        ([(3, 7), (10, 7)], _P3), ([(11, 6), (22, 6)], _P3),
        ([(11, 2), (11, 20)], _P3),
        ([(19, 9), (7, 24)], _P3),
        ([(7, 24), (5, 24), (3, 22), (3, 19), (5, 16), (8, 14), (12, 12), (17, 12), (21, 14), (23, 18),
          (22, 22), (19, 24), (14, 25)], _P3),
    ])


def masque_n() -> np.ndarray:
    """ん (24 × 28 cases)."""
    return _trace(24, 28, [
        ([(13, 2), (4, 25)], _P3),
        ([(7, 17), (9, 15), (12, 14), (14, 15), (15, 17), (15, 22), (16, 24), (18, 24), (20, 22), (22, 18)], _P3),
    ])


def masque_nin() -> np.ndarray:
    """忍 (22 × 22 cases) : 刃 en haut (𠃌, 丿, 丶), 心 en bas (point, crochet, deux points)."""
    return _trace(22, 22, [
        ([(2, 2), (19, 2)], _P3), ([(19, 2), (19, 8), (18, 10), (15, 10)], _P3),
        ([(11, 3), (10, 6), (7, 9), (2, 11)], _P3),
        ([(4, 5), (6, 7)], _P3),
        ([(2, 15), (1, 18)], _P3),
        ([(6, 13), (6, 18), (8, 19), (16, 19), (17, 17)], _P3),
        ([(10, 14), (12, 16)], _P3),
        ([(17, 14), (20, 17)], _P3),
    ])


_GLYPHES = {"あ": masque_a, "ん": masque_n, "忍": masque_nin}


def _masque(ch: str, cases: int = 22) -> np.ndarray:
    """Glyphe dessiné à la main s'il existe, sinon police pixelisée (repli)."""
    f = _GLYPHES.get(ch)
    return f() if f else glyph_mask(ch, cases, font="sans", threshold=0.5)


def spirale_feuille(n: int = 24) -> np.ndarray:
    """Emblème de la feuille de Konoha en pixels (n × n, lignes = haut → bas), dessiné sans police :
    spirale ronde qui part de la queue et tourne dans le sens horaire vers le centre, pointe triangulaire à
    gauche, queue effilée en bas à gauche. Dessin de référence sur 26 cases, mis à l'échelle ; le trait passe
    à 2 cases sous 25 cases (1 case sous 14) pour que les spires restent séparées."""
    s = n / 26.0
    bw = 1 if n < 14 else (2 if n < 25 else max(3, int(round(3 * s))))
    cx, cy = 14.4 * s, 11.8 * s
    rayons = [r * s for r in (9.6, 9.4, 9.0, 8.0, 4.4, 1.8)]
    angles = (225, 120, 30, -60, -170, -300)        # degrés, sens horaire à l'écran
    pts = []
    for (pa, ra), (pb, rb) in zip(zip(angles, rayons), zip(angles[1:], rayons[1:])):
        k = max(4, int(abs(pa - pb) / 6))
        for i in range(k):
            t = i / k
            phi = math.radians(pa + (pb - pa) * t)
            r = ra + (rb - ra) * t
            pts.append((cx + r * math.cos(phi), cy - r * math.sin(phi)))
    phi = math.radians(angles[-1])
    pts.append((cx + rayons[-1] * math.cos(phi), cy - rayons[-1] * math.sin(phi)))
    q = [(x * s, y * s) for x, y in ((7.6, 18.8), (4.8, 21.8), (1.4, 25.0))]
    m = _trace(n, n, [(pts, (bw, bw)), (q[:2], (bw, bw)), (q[1:], (max(1, bw - 1),) * 2)])
    return _remplir(m, [(x * s, y * s) for x, y in ((0.3, 8.6), (6.3, 6.2), (5.6, 13.0))])


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


def _vantail(b, side, half, H, z_gond, angle, masque, rng):
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
        # rangées de clous de fer sur les traverses haute et basse, côté couloir
        for vv in (1.5, H - 1.5):
            for k in range(5):
                uu = 6.0 + k * (W - 10.0) / 4
                b.cyl((uu, vv, zs * -0.55), 0.6, 0.5, FER, axis="z", name="Clou", collide=False)
        # poignée en anneau côté couloir, au bout du vantail
        box(W - 1.9, W - 0.9, H * 0.5 - 2.5, H * 0.5 + 2.5, -0.9, -0.3, FER, name="Poignee", collide=False)

        # grande lettre rouge sur la face côté couloir (1 case = 1 stud)
        p = 1.0
        nr, nc = masque.shape
        uc, vc = W / 2, H / 2 + 0.5
        for (x, y, w, h) in mask_rects(masque):
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
    b.box((x - 0.3, y_attache - 0.6, min(z_mur, zc + sens * 0.3)), (x + 0.3, y_attache, max(z_mur, zc + sens * 0.3)),
          FER, collide=False, name="Potence")
    b.box((x - 0.15, y_attache - 1.6, zc - 0.15), (x + 0.15, y_attache - 0.6, zc + 0.15), FER, collide=False)
    b.cyl((x, y_attache - 1.9, zc), 0.8, 0.6, c("noir"), axis="y", collide=False)
    b.ball((x, y_attache - 4.3, zc), 2.3, couleur, material="Neon", collide=False, name="Lanterne")
    b.cyl((x, y_attache - 6.75, zc), 0.8, 0.5, c("noir"), axis="y", collide=False)


def _chochin(b, x, y_haut, z, couleur):
    """Grand lampion rouge (chōchin) suspendu sous une poutre dont le dessous est en y_haut : corps en
    tonneau (cylindre + boule pour le renflement), capuchons noirs, pompon doré."""
    noir = c("noir")
    b.box((x - 0.15, y_haut - 1.2, z - 0.15), (x + 0.15, y_haut, z + 0.15), noir, collide=False, name="Attache")
    b.cyl((x, y_haut - 1.5, z), 1.9, 0.6, noir, axis="y", collide=False, name="Capuchon")
    yc = y_haut - 5.6
    b.cyl((x, yc, z), 2.8, 7.6, couleur, axis="y", collide=False, name="Chochin")
    b.ball((x, yc, z), 3.3, couleur, collide=False, name="Chochin")
    b.cyl((x, y_haut - 9.7, z), 1.9, 0.6, noir, axis="y", collide=False, name="Capuchon")
    b.box((x - 0.35, y_haut - 11.2, z - 0.35), (x + 0.35, y_haut - 10.0, z + 0.35), OR, collide=False, name="Pompon")


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
    PW = 14.0                     # largeur d'un pilier
    PD = 7.0                      # demi-profondeur des piliers
    xo = half + PW                # face extérieure des piliers
    y_lin = H + 1                 # sous-face du linteau (hauteur libre)
    y_b0, y_b1 = y_lin + 3, y_lin + 29          # bandeau des signes (entre deux poutres)
    y_top = y_b1 + 3                             # dessus de la poutre haute
    tuile = (mix(c("rempart_tuile"), c("toit_vert"), 0.25), mix(c("rempart_tuile"), c("toit_bleu"), 0.25),
             mix(c("rempart_tuile"), c("toit_vert"), 0.5), shade(c("rempart_tuile"), 0.92))[v]
    tuile_f = shade(tuile, 0.86)
    lampe = (c("orange_lampion"), c("jaune_lampion"), c("orange_lampion"), c("jaune_lampion"))[v]
    rouge_chochin = (c("rouge"), c("rouge"), c("noren_rouge"), c("rouge_fonce"))[v]
    # angle d'ouverture : les bouts des vantaux restent à |x| ≥ 31 (couloir dégagé)
    angle = math.degrees(math.acos(max(0.0, min(1.0, (half - 32.4) / half)))) + (0, 0.5, 1.0, 0.3)[v]
    angle = max(80.0, min(85.0, angle))
    tons_pilier = (CREME, CREME_CLAIR, CREME_FONCE)

    # ------------------------------------------------------------- piliers
    with b.group("Piliers"):
        for s in (-1, 1):
            x_in = s * half

            def span(a0, a1):
                """Intervalle en x mesuré depuis l'ouverture (a = 0 au bord de l'ouverture)."""
                xa, xb = x_in + s * a0, x_in + s * a1
                return min(xa, xb), max(xa, xb)

            # socle de pierre à deux degrés (ne déborde pas dans l'ouverture)
            sa, sb = span(0, PW + 1)
            b.box((sa, 0, -PD - 1), (sb, 3, PD + 1), c("pave"), studs="top", name="Socle")
            sa, sb = span(0, PW)
            b.box((sa, 3, -PD - 0.5), (sb, 5, PD + 0.5), PIERRE_FONCE, studs="top", name="Socle")
            # assises « pixel » : blocs décalés d'une assise à l'autre, trois tons proches
            y, k, prev = 5.0, 0, -1
            while y < y_lin - 3.01:
                y1 = min(y_lin - 3, y + 4)
                cut = (8, 6)[k % 2]
                for (a0, a1) in ((0, cut), (cut, PW)):
                    t = int(rng.integers(3))
                    if t == prev:
                        t = (t + 1) % 3
                    prev = t
                    xa, xb = span(a0, a1)
                    b.box((xa, y, -PD), (xb, y1, PD), tons_pilier[t], name="Assise")
                y, k = y1, k + 1
            # montants de bois sombre aux arêtes des deux faces
            for sz in (-1, 1):
                for (a0, a1) in ((0, 1.6), (PW - 1.6, PW)):
                    xa, xb = span(a0, a1)
                    za, zb = sorted((sz * PD, sz * (PD + 0.4)))
                    b.box((xa, 5, za), (xb, y_lin - 3, zb), c("bois_fonce"), name="Montant")
            # chapiteau à deux degrés en bois sombre
            sa, sb = span(0, PW + 0.5)
            b.box((sa, y_lin - 3, -PD - 0.5), (sb, y_lin - 2, PD + 0.5), c("bois_fonce"), name="Chapiteau")
            sa, sb = span(0, PW + 1)
            b.box((sa, y_lin - 2, -PD - 1), (sb, y_lin, PD + 1), BOIS_SOMBRE, name="Chapiteau")

    # ------------------------------------------------------------- linteau : 忍 · gaku de la feuille · 忍
    with b.group("Linteau"):
        xl = xo + 1
        b.box((-xl, y_lin, -PD - 0.5), (xl, y_b0, PD + 0.5), BOIS_SOMBRE, name="Poutre_basse")
        b.box((-xo, y_b0, -5.5), (xo, y_b1, 5.5), PLAQUE, name="Bandeau")
        b.box((-xl, y_b1, -PD - 0.5), (xl, y_top, PD + 0.5), BOIS_SOMBRE, name="Poutre_haute")
        ninb = masque_nin()
        feuille = spirale_feuille(26)
        yc = (y_b0 + y_b1) / 2
        xg = 17.0                                  # demi-largeur du cadre central
        xn = (xg + xo - 3) / 2                     # centre des 忍
        for sens in (1, -1):
            z0 = sens * 5.5
            # poteaux d'about au-dessus des piliers (colombages en saillie)
            for s in (-1, 1):
                xa, xb = sorted((s * (xo - 3), s * xo))
                za, zb = sorted((z0, z0 + sens * 1.0))
                b.box((xa, y_b0, za), (xb, y_b1, zb), BOIS_SOMBRE, name="Colombage")
            with b.group("Glyphes"):
                for xc in (-xn, xn):
                    _glyphe_face(b, ninb, 1.0, xc, yc, z0, sens, 0.6, c("lettre_rouge"), name="Pixel")
            # gaku : grand cadre laqué rouge en saillie, qui monte jusque sous l'avant-toit ; panneau crème
            # en relief, feuille rouge, coins dorés
            with b.group("Gaku"):
                zf = sens * 8.6
                y_g0, y_g1 = y_lin + 0.6, y_top + 3.0
                za, zb = sorted((z0, zf))
                b.box((-xg, y_g0, za), (xg, y_g1, zb), LAQUE, name="Cadre")
                bd = 2.2                                         # largeur de la bordure laquée
                za, zb = sorted((zf, zf + sens * 0.2))
                b.box((-xg + bd - 0.45, y_g0 + bd - 0.45, za), (xg - bd + 0.45, y_g1 - bd - 0.35, zb), OR,
                      collide=False, name="Filet")
                za, zb = sorted((zf, zf + sens * 0.4))
                b.box((-xg + bd, y_g0 + bd, za), (xg - bd, y_g1 - bd - 0.8, zb), PLAQUE, name="Panneau")
                for gx in (-xg + 1.1, xg - 1.1):
                    for gy in (y_g0 + 1.1, y_g1 - 1.5):
                        za, zb = sorted((zf, zf + sens * 0.3))
                        b.box((gx - 0.7, gy - 0.7, za), (gx + 0.7, gy + 0.7, zb), OR, collide=False, name="Ferrure")
                ycg = (y_g0 + bd + y_g1 - bd - 0.8) / 2
                _glyphe_face(b, feuille, 1.0, 0.0, ycg, zf + sens * 0.4, sens, 0.6, c("lettre_rouge"), name="Pixel")
        # cache-clous dorés sur la poutre basse (deux faces)
        for sens in (1, -1):
            for xk in (-(xo - 5), -(xg + 6), xg + 6, xo - 5):
                za, zb = sorted((sens * (PD + 0.5), sens * (PD + 0.8)))
                b.box((xk - 0.9, y_lin + 0.6, za), (xk + 0.9, y_b0 - 0.6, zb), OR, collide=False, name="CacheClou")
        # frise crème et consoles sous la corniche
        b.box((-xo, y_top, -5.5), (xo, y_top + 2, 5.5), CREME_FONCE, name="Frise")
        for sens in (1, -1):
            x = -xo + 2
            while x <= xo - 2 + 0.01:
                if abs(x) > xg + 0.8:
                    za, zb = sorted((sens * 5.5, sens * 9.0))
                    b.box((x - 0.8, y_top, za), (x + 0.8, y_top + 2, zb), BOIS_SOMBRE, name="Console", collide=False)
                x += 8

    # ------------------------------------------------------------- toit (profil japonais à deux pentes)
    y_r = y_top + 2
    with b.group("Toit"):
        xr = xo + 10.0                      # demi-longueur du toit
        zr, zm = 17.0, 8.0                  # débord, cassure du profil
        y0 = y_r + 1.5                      # bas des tuiles (rive)
        ym = y0 + 3.0                       # cassure : pente basse 3/9
        y1 = ym + 9.0                       # faîtage : pente haute 9/8
        b.box((-xr + 1, y_r, -zr + 1), (xr - 1, y0, zr - 1), c("bois_fonce"), name="Rive")
        b.box((-xr, y0, -zm), (xr, ym, zm), tuile_f, name="Comble")
        n = int(round(2 * xr / 4))
        wst = 2 * xr / n
        # coins relevés : les deux rangs de chaque bout ont leur égout surélevé (bord du toit en escalier)
        releve = {0: 1.6, 1: 0.8, n - 2: 0.8, n - 1: 1.6}
        for i in range(n):
            x0 = -xr + i * wst
            col = tuile if i % 2 == 0 else tuile_f
            dy = releve.get(i, 0.0)
            for sz in (-1, 1):
                d = "+z" if sz > 0 else "-z"
                za, zb = sorted((sz * zm, sz * zr))
                b.wedge((x0, y0 + dy, za), (x0 + wst, ym, zb), col, down=d, studs="top", name="Tuiles")
                if dy:
                    b.box((x0, y0, za), (x0 + wst, y0 + dy, zb), c("bois_fonce"), name="Coyau")
                za, zb = sorted((0.0, sz * zm))
                b.wedge((x0, ym, za), (x0 + wst, y1, zb), col, down=d, studs="top", name="Tuiles")
                if i % 2 == 0:
                    b.cyl((x0 + wst / 2, y0 + dy + 0.5, sz * (zr + 0.25)), 1.0, 0.5, FAITAGE, axis="z", name="About",
                          collide=False)
        # faîtage et épis (onigawara stylisés)
        b.box((-xr - 0.5, y1 - 2.5, -2.2), (xr + 0.5, y1 + 1.0, 2.2), FAITAGE, name="Faitage")
        b.box((-xr + 1, y1 + 1.0, -2.0), (xr - 1, y1 + 1.7, 2.0), CREME_FONCE, name="Faitage")
        b.box((-xr + 1, y1 + 1.7, -2.5), (xr - 1, y1 + 3.0, 2.5), shade(FAITAGE, 1.1), studs="top", name="Faitage")
        for s in (-1, 1):
            xa, xb = sorted((s * (xr - 3.5), s * (xr + 1)))
            b.box((xa, y1 - 3.0, -3.0), (xb, y1 + 4.0, 3.0), FAITAGE, name="Epi")
            b.wedge((xa, y1 + 4.0, -2.2), (xb, y1 + 8.0, 2.2), shade(FAITAGE, 0.9), down="-x" if s > 0 else "+x",
                    name="Epi")
            b.cyl((s * (xr + 1.2), y1 + 0.8, 0), 1.6, 0.4, OR, axis="x", name="Epi", collide=False)
        # chevrons sous l'avant-toit, entre la corniche et le bord du toit
        for sz in (-1, 1):
            x = -xr + 3
            while x <= xr - 3 + 0.01:
                za, zb = sorted((sz * 9.0, sz * (zr - 1.5)))
                b.box((x - 0.5, y_r - 1.0, za), (x + 0.5, y_r, zb), c("bois_fonce"), collide=False, name="Chevron")
                x += 6
        # pignons : planches de rive sombres qui suivent le profil (0,5 stud au-dessus des tuiles)
        p_bas, p_haut = (3.0 - releve[0]) / (zr - zm), (y1 - ym) / zm
        for s in (-1, 1):
            xa = s * xr
            lo, hi = (xa - 0.6, xa) if s < 0 else (xa, xa + 0.6)
            yh = ym + 0.5                                  # haut de la planche à la cassure
            b.box((lo, y0 - 0.5, -zm), (hi, yh, zm), BOIS_SOMBRE, name="Pignon")
            for sz in (-1, 1):
                d = "+z" if sz > 0 else "-z"
                za, zb = sorted((0.0, sz * zm))
                b.wedge((lo, yh, za), (hi, yh + p_haut * zm, zb), BOIS_SOMBRE, down=d, name="Pignon")
                z_bout = zr + 0.5
                y_bas = yh - p_bas * (z_bout - zm)
                za, zb = sorted((sz * zm, sz * z_bout))
                b.box((lo, y0 - 0.5, za), (hi, y_bas, zb), BOIS_SOMBRE, name="Pignon")
                b.wedge((lo, y_bas, za), (hi, yh, zb), BOIS_SOMBRE, down=d, name="Pignon")
            # disque décoratif (gegyo) sous le faîtage
            b.cyl((xa + s * 0.85, y1 - 6.0, 0), 1.8, 0.5, OR, axis="x", name="Gegyo", collide=False)
    y_faite = y1 + 8.0

    # ------------------------------------------------------------- vantaux
    with b.group("Vantaux"):
        _vantail(b, -1, half, H, PD + 1.4, angle, _masque("あ"), rng)
        _vantail(b, 1, half, H, PD + 1.4, angle, _masque("ん"), rng)

    # ------------------------------------------------------------- lampions et lanternes
    with b.group("Lanternes"):
        for s in (-1, 1):
            _chochin(b, s * (half - 8), y_lin, 0.0, rouge_chochin)
            _lanterne(b, s * (half + PW / 2), 36.0, -PD, -1, lampe)

    # ------------------------------------------------------------- rempart
    HM = 30.0         # hauteur du corps du mur
    TM = 3.5          # demi-épaisseur
    CF = 2.5          # saillie des contreforts
    cell_w, cell_h = 4, 3
    teintes = (c("rempart"), REMPART_CLAIR, REMPART_MOYEN, c("rempart_fonce"))
    with b.group("Rempart"):
        for s in (-1, 1):
            if mur <= xo + 8:
                break
            with b.group("Gauche" if s < 0 else "Droite"):
                xe = mur - 5                     # début de la pile d'extrémité
                L = xe - xo
                b.box((s * (xo + 1), 0, -TM - 0.6), (s * xe, 3, TM + 0.6), PIERRE, studs="top", name="Soubassement")
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
                # chaperon : poutre, deux pans de tuiles, faîtage, abouts
                b.box((s * xo, HM, -TM - 0.5), (s * xe, HM + 1, TM + 0.5), c("bois_fonce"), name="Chaperon")
                b.wedge((s * xo, HM + 1, -TM - 2), (s * xe, HM + 3.5, 0), tuile, down="-z", studs="top", name="Chaperon")
                b.wedge((s * xo, HM + 1, 0), (s * xe, HM + 3.5, TM + 2), tuile, down="+z", studs="top", name="Chaperon")
                b.box((s * xo, HM + 2.6, -1.0), (s * xe, HM + 4.4, 1.0), FAITAGE, studs="top", name="Faitage")
                xa = xo + 4
                while xa < xe - 2:
                    for sz in (-1, 1):
                        b.cyl((s * xa, HM + 1.4, sz * (TM + 2.25)), 0.75, 0.5, FAITAGE, axis="z", name="About",
                              collide=False)
                    xa += 8
                # contreforts sur les deux faces : pied de pierre, corps d'enduit foncé, chapeau de tuiles
                xb = xo + 12
                while xb < xe - 6:
                    for sz in (-1, 1):
                        face = ("Back",) if sz > 0 else ("Front",)
                        za, zb = sorted((sz * (TM + 0.6), sz * (TM + CF + 1.0)))
                        b.box((s * xb - 3.5, 0, za), (s * xb + 3.5, 3, zb), PIERRE_FONCE, studs="top", name="Contrefort")
                        za, zb = sorted((sz * TM, sz * (TM + CF)))
                        b.box((s * xb - 3, 3, za), (s * xb + 3, 20, zb), c("rempart_fonce"), studs=face, name="Contrefort")
                        b.wedge((s * xb - 3.4, 20, za), (s * xb + 3.4, 23, sz * (TM + CF + 0.4)), tuile,
                                down="+z" if sz > 0 else "-z", studs="top", name="Contrefort")
                    xb += 24
                # pile d'extrémité
                b.box((s * xe, 0, -TM - 1.5), (s * mur, HM + 4.6, TM + 1.5), PIERRE_FONCE, name="Pile")
                b.box((s * (xe - 0.5), HM + 4.6, -TM - 2), (s * mur, HM + 5.6, TM + 2), FAITAGE, studs="top", name="Pile")

    # ------------------------------------------------------------- tuyaux (côté droit, face extérieure)
    with b.group("Tuyaux"):
        r = 2.4
        zc = TM + CF + 0.5 + r              # devant les contreforts
        x_dep = xo + 5
        contreforts = [xo + 12 + 24 * k for k in range(64) if xo + 12 + 24 * k < mur - 11]
        trous = [(a + 3.5, z - 3.5) for a, z in zip(contreforts, contreforts[1:]) if z - a - 7 >= 16.5]
        if trous and trous[-1][0] > x_dep + 20:
            mil = sum(trous[-1]) / 2
            fins = [mil - 5.6, mil, mil + 5.6]          # descentes entre deux contreforts
            gris = c("tuyau")
            for (yp, xf) in zip((15.0, 20.5, 26.0), fins):
                b.cyl((x_dep, yp, (TM - 0.5 + zc) / 2), r, zc - TM + 0.5, gris, axis="z", name="Tuyau")
                b.ball((x_dep, yp, zc), r, gris, name="Coude")
                b.cyl(((x_dep + xf) / 2, yp, zc), r, xf - x_dep, gris, axis="x", name="Tuyau")
                b.ball((xf, yp, zc), r, gris, name="Coude")
                b.cyl((xf, (yp + 1.2) / 2, zc), r, yp - 1.2, gris, axis="y", name="Tuyau")
                b.box((xf - 2.6, 0, zc - 2.6), (xf + 2.6, 1.2, zc + 2.6), PIERRE_FONCE, studs="top", name="Massif")
                b.cyl((x_dep, yp, TM + 0.4), r + 0.3, 0.8, c("metal_fonce"), axis="z", name="Bride")
                b.cyl((xf, 2.6, zc), r + 0.3, 0.8, c("metal_fonce"), axis="y", name="Bride")
                xb = xo + 12
                while xb < xf - 4:
                    b.cyl((xb + 4, yp, zc), r + 0.3, 1.0, c("metal_fonce"), axis="x", name="Bride")
                    xb += 24
            # colliers : pattes fixées aux contreforts, qui tiennent les trois tuyaux
            xb = xo + 12
            while xb < fins[0] - 3:
                b.box((xb - 0.5, 12.0, TM + CF), (xb + 0.5, 28.2, zc - r + 0.3), c("metal_fonce"), name="Collier")
                for yp in (12.0, 17.75, 23.25, 27.2):
                    b.box((xb - 0.5, yp, zc - r + 0.3), (xb + 0.5, yp + 1.0, zc + 0.5), c("metal_fonce"), name="Collier")
                xb += 24

    # ------------------------------------------------------------- tableau d'affichage (côté village, à droite)
    if mur > xo + 40:
        with b.group("Affichage"):
            xa, xb2, z0 = xo + 17, xo + 29, -TM
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
            b.box((xa + 8.95, 12.2, z0 - 1.15), (xa + 9.95, 13.2, z0 - 1.0), c("lettre_rouge"), collide=False,
                  name="Tampon")

    # ------------------------------------------------------------- guérite (côté village, à gauche)
    with b.group("Guerite"):
        toit_g = (c("toit_rouge"), c("toit_brun"), c("toit_rouge"), c("toit_orange"))[v]
        with b.at((-(half + 6), 0, -14.25), yaw=-90):
            _guerite(b, rng, toit_g, lampe)

    z_min = -(14.25 + 5.5)
    z_max = PD + 1.4 + half * math.sin(math.radians(angle)) + 1.0
    return {"emprise": (2 * max(mur, xo + 10), round(z_max - z_min, 1)), "hauteur": round(y_faite, 1),
            "ouverture": ouverture}
