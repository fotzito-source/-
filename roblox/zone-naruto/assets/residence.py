"""Résidence du Hokage et tour au toit bleu : les deux monuments de la place des œufs.

Repère de chaque asset : origine au centre de l'emprise, y = 0 au sol, l'avant regarde -Z.

- `residence_hokage` : le grand bâtiment rond et rouge. Tambour principal (un seul cylindre), bandeau
  blanc et couronnes de fenêtres, tambour supérieur en retrait, terrasses à garde-corps, édicule et antenne
  sur le toit. En façade (-Z), le grand disque blanc portant 火 en pixels rouges, au-dessus d'un porche
  à colonnes et à escalier. Deux ailes rectangulaires (murs rouges « pixel », chaînages blancs, toits de
  tuiles stud à pignon blanc) l'encadrent à gauche et à droite.
- `tour_bleue` : la haute tour blanche à colombages de bois, coiffée d'un cône de tuiles bleues en gradins.

Les fenêtres et garde-corps des tambours sont des blocs posés tangentiellement (rotation `yaw`),
légèrement enfoncés dans le cylindre : rien ne flotte, aucune face coplanaire.
"""

from __future__ import annotations

import math

import numpy as np

from kit import shade
from palette import c, vary
from textures import glyph_mask, mask_rects

# Couleurs locales (en plus de la palette)
ROUGE_SOMBRE = "#A93A30"      # soubassement, poteaux, contour du disque
ROUGE_TAMBOUR2 = "#BF4236"    # tambour supérieur, un rien plus sombre que le principal
LETTRE = "#D3302A"            # 火
CREME_SOL = "#EADFC8"         # dallage des terrasses
OR = "#E8B84A"                # boule de faîte
VITRE = "#33536A"


# ----------------------------------------------------------------------------
# Outils : objets posés autour d'un cylindre vertical centré sur l'origine du repère courant
# ----------------------------------------------------------------------------

def _pol(r: float, deg: float) -> tuple:
    """Point à la distance r, angle `deg` compté depuis l'avant (-Z) vers +X."""
    a = math.radians(deg)
    return r * math.sin(a), -r * math.cos(a)


def _ecart(deg: float) -> float:
    """Écart angulaire à l'avant (0°), dans [0, 180]."""
    return abs((deg + 180) % 360 - 180)


def _plaque(b, r, deg, y0, y1, w, saillie, color, **kw):
    """Bloc de largeur w collé sur un cylindre de rayon r, face avant tournée vers l'extérieur.

    Le dos est enfoncé dans le cylindre (même aux bords, malgré la courbure) ; la face avant
    dépasse de `saillie` au milieu."""
    sink = 0.15 + w * w / (8 * r)
    d = saillie + sink
    x, z = _pol(r - sink + d / 2, deg)
    return b.boxc((x, (y0 + y1) / 2, z), (w, y1 - y0, d), color, yaw=-deg, **kw)


def _fenetre_courbe(b, r, deg, y0, y1, w, cadre, vitre=VITRE):
    """Fenêtre sur un mur courbe : cadre (saillie 0,25), vitre (saillie 0,35), appui."""
    _plaque(b, r, deg, y0 - 0.35, y1 + 0.35, w + 0.7, 0.25, cadre, collide=False)
    _plaque(b, r, deg, y0, y1, w, 0.35, vitre, collide=False, name="Fenetre")
    _plaque(b, r, deg, y0 - 0.75, y0 - 0.35, w + 1.1, 0.55, cadre, collide=False, name="Appui")


def _garde_corps(b, r, y0, h, n, poteau, lisse, skip=lambda d: False, ep=0.3):
    """Garde-corps circulaire : n poteaux aux sommets d'un polygone, n lisses entre eux."""
    L = 2 * r * math.tan(math.pi / n) + 0.1
    for i in range(n):
        d0, dm, d1 = 360 * i / n, 360 * (i + 0.5) / n, 360 * (i + 1) / n
        if not skip(d0):
            x, z = _pol(r, d0)
            b.boxc((x, y0 + h / 2, z), (0.5, h, 0.5), poteau, yaw=-d0, collide=False, name="Poteau")
        if not (skip(d0) or skip(dm) or skip(d1)):
            x, z = _pol(r, dm)
            b.boxc((x, y0 + h - 0.25, z), (L, 0.4, ep), lisse, yaw=-dm, collide=False, name="Lisse")


def _glyphe(b, mask, cell, xc, yc, z_face, prof, color, **kw):
    """Masque de pixels (lignes haut → bas) sur une face qui regarde -Z : colonnes vers -X."""
    nr, nc = mask.shape
    W, H = nc * cell, nr * cell
    for (x, y, w, h) in mask_rects(mask):
        y_top = yc + H / 2 - y * cell
        x0 = xc + W / 2 - (x + w) * cell
        b.box((x0, y_top - h * cell, z_face + 0.1), (x0 + w * cell, y_top, z_face - prof), color, **kw)


def _masque_feu(cells: int = 15) -> np.ndarray:
    m = glyph_mask("火", cells, font="sans", bold=0.4, threshold=0.5)
    p = np.pad(m, 1)
    voisins = p[:-2, 1:-1].astype(int) + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]
    return m & (voisins > 0)          # retire les pixels isolés


def _motif_pixels(rng, nu: int, nv: int, densite: float = 0.3) -> np.ndarray:
    """Motif « mur pixel » : 0 = fond, 1 = teinte claire, 2 = teinte sombre, par petites grappes."""
    m = np.zeros((nv, nu), int)
    for _ in range(int(nu * nv * densite / 2.2)):
        u, v = int(rng.integers(0, nu)), int(rng.integers(0, nv))
        k = 1 if rng.random() < 0.6 else 2
        m[v, u] = k
        if rng.random() < 0.6 and u + 1 < nu:
            m[v, u + 1] = k
    return m


def _lampion(b, x, y_attache, z, couleur, r=0.9, h=1.9):
    """Lampion de papier suspendu (cylindre néon, chapeaux noirs)."""
    b.box((x - 0.08, y_attache - 0.9, z - 0.08), (x + 0.08, y_attache, z + 0.08), c("noir"), collide=False)
    b.cyl((x, y_attache - 1.1, z), r * 0.55, 0.4, c("noir"), collide=False)
    b.cyl((x, y_attache - 1.3 - h / 2, z), r, h, couleur, material="Neon", collide=False, name="Lampion")
    b.cyl((x, y_attache - 1.5 - h, z), r * 0.55, 0.4, c("noir"), collide=False)


def _citerne(b, x, z, y, r=1.8, h=3.2):
    """Citerne de toit : socle métallique, cuve, dôme, cerclage."""
    b.box((x - r - 0.2, y, z - r - 0.2), (x + r + 0.2, y + 0.6, z + r + 0.2), c("metal_fonce"), studs="top")
    b.cyl((x, y + 0.5 + h / 2, z), r, h, c("citerne"))
    b.ball((x, y + 0.5 + h, z), r * 0.98, c("citerne"))
    b.cyl((x, y + 0.5 + h * 0.3, z), r + 0.12, 0.35, c("metal"), collide=False)


def _lanterne_pierre(b, x, z):
    """Petite lanterne de pierre (tōrō) au pied de l'escalier."""
    pierre, pierre_f = c("pave"), c("pave_fonce")
    b.box((x - 0.9, 0, z - 0.9), (x + 0.9, 0.5, z + 0.9), pierre_f, studs="top")
    b.box((x - 0.35, 0.5, z - 0.35), (x + 0.35, 2.4, z + 0.35), pierre)
    b.box((x - 0.8, 2.4, z - 0.8), (x + 0.8, 3.9, z + 0.8), pierre)
    b.box((x - 0.55, 2.7, z - 0.85), (x + 0.55, 3.6, z + 0.85), c("jaune_lampion"), material="Neon", collide=False)
    b.wedge((x - 1.1, 3.9, z - 1.1), (x + 1.1, 4.7, z), pierre_f, down="-z", studs="top")
    b.wedge((x - 1.1, 3.9, z), (x + 1.1, 4.7, z + 1.1), pierre_f, down="+z", studs="top")
    b.ball((x, 4.9, z), 0.35, pierre_f, collide=False)


def _jardiniere(b, x, z, y, rng):
    """Bac de pierre et buisson arrondi."""
    b.box((x - 1.4, y, z - 1.4), (x + 1.4, y + 1.6, z + 1.4), c("pave_fonce"), studs="top")
    b.ball((x, y + 2.5, z), 1.5, vary("feuille", rng, 0.05), collide=False)
    b.ball((x + 0.5, y + 3.3, z - 0.3), 0.9, c("feuille_claire"), collide=False)


# ----------------------------------------------------------------------------
# Résidence du Hokage
# ----------------------------------------------------------------------------

R_TAMBOUR = 20.0
Z_TAMBOUR = 4.25          # centre du tambour, en retrait : l'emprise (porche compris) reste centrée
U_IN, U_OUT, Z_AV, Z_AR, Y_MUR = 11.0, 30.8, -16.0, 10.0, 9.0   # ailes (repère du tambour)
U_FAITE, PENTE = (U_IN - 1.2 + U_OUT + 1.2) / 2, 0.464          # faîtage au milieu des deux égouts


def _aile(b, s, rng, toit, toit_f, mur):
    """Aile rectangulaire à droite (s = +1) ou à gauche (s = -1) du tambour, repère du tambour.

    u = distance au plan x = 0 (vers l'extérieur) ; l'aile s'enfonce dans le tambour côté intérieur."""
    def X(u):
        return s * u

    def bx(u0, u1, y0, y1, z0, z1, col, **kw):
        return b.box((X(u0), y0, z0), (X(u1), y1, z1), col, **kw)

    dehors, dedans = ("+x", "-x") if s > 0 else ("-x", "+x")
    blanc = c("blanc")
    # Murs rouges, soubassement de pierre, corniche blanche
    bx(U_IN, U_OUT, 0, Y_MUR, Z_AV, Z_AR, mur, name="Murs")
    bx(U_IN, U_OUT + 0.3, 0, 1.3, Z_AV - 0.3, Z_AR + 0.3, c("pave_fonce"), name="Soubassement")
    bx(U_IN, U_OUT + 0.4, Y_MUR - 0.6, Y_MUR + 0.4, Z_AV - 0.4, Z_AR + 0.4, blanc, name="Corniche")
    # Mur « pixel » : grappes de briques un peu plus claires ou plus sombres (saillie 0,1)
    teintes = {1: shade(mur, 1.13), 2: shade(mur, 0.86)}
    with b.group("Pixels"):
        for face in ("avant", "cote", "arriere"):
            if face == "avant":
                u0, u1 = 12.5, U_OUT - 0.8
            elif face == "arriere":
                u0, u1 = 17.8, U_OUT - 0.8
            else:
                u0, u1 = Z_AV + 0.8, Z_AR - 0.8
            nu, nv = int((u1 - u0) // 2), 3
            m = _motif_pixels(rng, nu, nv)
            for k, col in teintes.items():
                for (i, j, w, h) in mask_rects(m == k):
                    a0, a1 = u0 + i * 2, u0 + (i + w) * 2
                    y1 = Y_MUR - 0.6 - j * 2.2
                    y0 = y1 - h * 2.2
                    if face == "avant":
                        bx(a0, a1, y0, y1, Z_AV - 0.1, Z_AV + 0.1, col, collide=False)
                    elif face == "arriere":
                        bx(a0, a1, y0, y1, Z_AR - 0.1, Z_AR + 0.1, col, collide=False)
                    else:
                        bx(U_OUT - 0.1, U_OUT + 0.1, y0, y1, a0, a1, col, collide=False)
    # Chaînages d'angle blancs
    for z0, z1 in ((Z_AV - 0.4, Z_AV + 0.8), (Z_AR - 0.8, Z_AR + 0.4)):
        bx(U_OUT - 0.8, U_OUT + 0.4, 1.3, Y_MUR - 0.6, z0, z1, blanc, name="Chainage")
    # Fenêtres : façade avant, côté extérieur, arrière
    with b.group("Fenetres"):
        for u in (16.0, 21.0, 26.0):
            bx(u - 1.4, u + 1.4, 2.6, 7.4, Z_AV - 0.25, Z_AV + 0.1, blanc, collide=False)
            bx(u - 1.0, u + 1.0, 3.0, 7.0, Z_AV - 0.35, Z_AV + 0.1, VITRE, collide=False, name="Fenetre")
            bx(u - 1.6, u + 1.6, 2.2, 2.6, Z_AV - 0.6, Z_AV + 0.1, blanc, collide=False, name="Appui")
        for z in (-10.5, -3.0, 4.5):
            bx(U_OUT - 0.1, U_OUT + 0.25, 2.6, 7.4, z - 1.4, z + 1.4, blanc, collide=False)
            bx(U_OUT - 0.1, U_OUT + 0.35, 3.0, 7.0, z - 1.0, z + 1.0, VITRE, collide=False, name="Fenetre")
            bx(U_OUT - 0.1, U_OUT + 0.6, 2.2, 2.6, z - 1.6, z + 1.6, blanc, collide=False, name="Appui")
        for u in (22.5, 27.5):
            bx(u - 1.4, u + 1.4, 2.6, 7.4, Z_AR - 0.1, Z_AR + 0.25, blanc, collide=False)
            bx(u - 1.0, u + 1.0, 3.0, 7.0, Z_AR - 0.1, Z_AR + 0.35, VITRE, collide=False, name="Fenetre")
    # Toit à deux pans (faîtage le long de Z), pignons tournés vers l'avant et l'arrière
    YR = Y_MUR + 0.4
    UE, UI = U_OUT + 1.2, U_IN - 1.2
    YK = YR + PENTE * (UE - U_FAITE)
    ZR0, ZR1 = Z_AV - 1.0, Z_AR + 1.0
    with b.group("Toit"):
        b.wedge((X(U_FAITE), YR, ZR0), (X(UE), YK, ZR1), c(toit), down=dehors, studs="top")
        b.wedge((X(UI), YR, ZR0), (X(U_FAITE), YK, ZR1), c(toit), down=dedans, studs="top")
        # Rangs de tuiles : coins parallèles à la pente, surélevés de 0,15 (petite lèvre côté égout)
        bande = shade(c(toit), 0.87)
        for f0, f1 in ((0.18, 0.4), (0.6, 0.82)):
            ue, ur = UE - f0 * (UE - U_FAITE), UE - f1 * (UE - U_FAITE)
            b.wedge((X(ur), YR + PENTE * (UE - ue) + 0.15, ZR0 + 0.05), (X(ue), YR + PENTE * (UE - ur) + 0.15, ZR1 - 0.05),
                    bande, down=dehors, studs="top", collide=False, name="RangTuiles")
            ue, ur = UI + f0 * (U_FAITE - UI), UI + f1 * (U_FAITE - UI)
            b.wedge((X(ue), YR + PENTE * (ue - UI) + 0.15, ZR0 + 0.05), (X(ur), YR + PENTE * (ur - UI) + 0.15, ZR1 - 0.05),
                    bande, down=dedans, studs="top", collide=False, name="RangTuiles")
        bx(U_FAITE - 0.6, U_FAITE + 0.6, YK - 0.6, YK + 0.5, ZR0 - 0.2, ZR1 + 0.2, c(toit_f), studs="top", name="Faitage")
        bx(UE - 0.6, UE, YR - 0.5, YR, ZR0, ZR1, c("bois_fonce"), name="Rive")
        # Pignons blancs encadrés par la tuile (avant et arrière) + œil-de-bœuf
        du = 1.1 / PENTE      # pignon en retrait de 1 stud sous la tuile, décollé de 0,1 de la sous-face
        for zf, sens in ((ZR0, -1), (ZR1, +1)):
            za, zb = zf - sens * 0.05, zf + sens * 0.25
            b.wedge((X(U_FAITE), YR + 0.1, za), (X(UE - du), YK - 1.0, zb), blanc, down=dehors, name="Pignon")
            b.wedge((X(UI + du), YR + 0.1, za), (X(U_FAITE), YK - 1.0, zb), blanc, down=dedans, name="Pignon")
            b.cyl((X(U_FAITE), YR + 1.9, zf + sens * 0.3), 1.35, 0.25, c("bois_fonce"), axis="z", collide=False)
            b.cyl((X(U_FAITE), YR + 1.9, zf + sens * 0.4), 1.0, 0.3, VITRE, axis="z", collide=False)
        # Épi de faîtage (petite boule) à l'avant
        b.ball((X(U_FAITE), YK + 0.9, ZR0 + 0.3), 0.6, c(toit_f), collide=False)
    # Tuyau gris qui court le long du mur arrière puis descend au coin
    with b.group("Tuyaux"):
        zt, yt = Z_AR + 0.6, 7.95
        b.cyl((X((16.5 + U_OUT + 0.6) / 2), yt, zt), 0.35, U_OUT + 0.6 - 16.5, c("tuyau"), axis="x", collide=False)
        b.cyl((X(U_OUT + 0.6), yt / 2, zt), 0.35, yt, c("tuyau"), collide=False)
        b.ball((X(U_OUT + 0.6), yt, zt), 0.42, c("tuyau"), collide=False)
        for u in (20.0, 25.0):
            bx(u - 0.15, u + 0.15, yt - 0.5, yt + 0.5, Z_AR, zt + 0.1, c("metal_fonce"), collide=False)


def residence_hokage(b, variant: int = 0) -> dict:
    """Résidence ronde du Hokage (64 × 51,5 studs, 42,6 de haut avec l'antenne), avant vers -Z.

    variant : 0 et 2 toits verts, 1 et 3 toits orange ; 2 et 3 sans citernes, avec oriflammes."""
    rng = b.rng
    toit, toit_f = [("toit_vert", "toit_vert_fonce"), ("toit_orange", "toit_brun")][variant % 2]
    rouge = c("rouge_hokage")
    blanc = c("blanc")
    R = R_TAMBOUR
    r2 = 14.0

    with b.at((0, 0, Z_TAMBOUR), group="Tambour"):
        # -- Socle et tambour principal ------------------------------------------------
        b.cyl((0, 0.75, 0), R + 1.5, 1.5, c("pave"), studs="top", name="Socle")
        b.cyl((0, 9.6, 0), R, 16.8, rouge, name="Tambour")
        b.cyl((0, 2.1, 0), R + 0.25, 1.4, ROUGE_SOMBRE, name="Soubassement")
        b.cyl((0, 9.7, 0), R + 0.35, 0.9, blanc, name="Bandeau")
        b.cyl((0, 18.1, 0), R + 0.7, 1.4, blanc, name="Corniche")
        b.cyl((0, 17.2, 0), R + 0.3, 0.6, ROUGE_SOMBRE, name="Frise")
        b.cyl((0, 18.9, 0), R + 0.4, 0.6, CREME_SOL, studs="top", name="Terrasse")
        # -- Tambour supérieur -----------------------------------------------------------
        b.cyl((0, 23.1, 0), r2, 8.2, ROUGE_TAMBOUR2, name="TambourHaut")
        b.cyl((0, 27.0, 0), r2 + 0.4, 1.2, blanc, name="CornicheHaut")
        b.cyl((0, 27.65, 0), r2 + 0.2, 0.5, CREME_SOL, studs="top", name="Toit")
        y_toit = 27.9

        # -- Disque blanc au 火 (au-dessus du porche, à cheval sur la terrasse) -----------------
        yd, rd = 19.5, 9.0
        z_disque = -R - 0.9
        with b.group("Disque"):
            b.cyl((0, yd, z_disque + 1.5), rd, 3.0, blanc, axis="z", name="Disque")
            b.cyl((0, yd, z_disque + 0.95), rd + 0.6, 1.3, ROUGE_SOMBRE, axis="z", name="Contour")
            # deux jambes de force posées sur la terrasse, derrière le disque
            for x in (-4.5, 4.5):
                b.box((x - 0.5, 19.2, z_disque + 2.9), (x + 0.5, 23.5, z_disque + 4.6), ROUGE_SOMBRE)
            _glyphe(b, _masque_feu(15), 0.85, 0, yd, z_disque, 0.35, LETTRE, collide=False)

        # -- Couronnes de fenêtres --------------------------------------------------------------
        def cache_aile(d, y_bas):
            x, z = _pol(R, d)
            u = abs(x)
            if u < U_IN or not (Z_AV - 1.0 <= z <= Z_AR + 1.0):
                return False
            if y_bas < Y_MUR:
                return True
            h_toit = Y_MUR + 0.4 + PENTE * (U_FAITE - (U_IN - 1.2)) - PENTE * max(U_FAITE - u, 0)
            return h_toit > y_bas + 0.8

        with b.group("Fenetres"):
            for i in range(24):
                d = i * 15.0
                if _ecart(d) > 34 and not cache_aile(d, 11.8):
                    _fenetre_courbe(b, R, d, 11.8, 15.8, 2.2, blanc)
                if _ecart(d) > 24 and not cache_aile(d, 3.6):
                    _fenetre_courbe(b, R, d, 3.6, 7.6, 2.2, blanc)
            for i in range(16):
                d = i * 22.5
                if _ecart(d) > 40:
                    _fenetre_courbe(b, r2, d, 21.0, 24.6, 1.8, blanc)

        # -- Garde-corps -------------------------------------------------------------------------
        with b.group("GardeCorps"):
            _garde_corps(b, R - 0.2, 19.2, 1.7, 32, ROUGE_SOMBRE, blanc, skip=lambda d: _ecart(d) < 31)
            _garde_corps(b, r2 - 0.3, y_toit, 1.6, 20, ROUGE_SOMBRE, blanc)

        # -- Terrasse : citernes à l'arrière ou oriflammes -------------------------------------
        if variant % 4 < 2:
            with b.group("Citernes"):
                for d in (145, -145):
                    x, z = _pol(17.2, d)
                    _citerne(b, x, z, 19.2)
        else:
            with b.group("Oriflammes"):
                for d in (55, -55, 125, -125):
                    x, z = _pol(17.0, d)
                    b.box((x - 0.6, 19.2, z - 0.6), (x + 0.6, 19.8, z + 0.6), c("metal_fonce"))
                    b.cyl((x, 23.6, z), 0.18, 8.0, c("metal"), collide=False)
                    with b.at((x, 0, z), yaw=-d):
                        p = b.box((0.25, 23.0, -0.05), (0.25 + 1.6, 27.4, 0.05), c(toit), collide=False, name="Oriflamme")
                        p.label = {"face": "Front", "text": "火", "color": blanc, "bg": c(toit), "font": "brush",
                                   "vertical": True}

        # -- Tuyaux gris à l'arrière du tambour ---------------------------------------------------
        with b.group("Tuyaux"):
            for d in (172.5, -157.5):
                x, z = _pol(R + 0.55, d)
                b.cyl((x, 9.15, z), 0.4, 16.9, c("tuyau"), collide=False)
                for y in (4.0, 13.0):
                    _plaque(b, R, d, y - 0.25, y + 0.25, 1.0, 1.0, c("metal_fonce"), collide=False)

        # -- Édicule et antenne sur le toit ---------------------------------------------------
        with b.group("Edicule"):
            b.box((-4, y_toit - 0.2, 1), (4, y_toit + 4.6, 8.5), vary("enduit", rng))
            b.box((-4.6, y_toit + 4.6, 0.4), (4.6, y_toit + 5.2, 9.1), c(toit), studs="top")
            b.box((-1.2, y_toit, 0.75), (1.2, y_toit + 3.6, 1.1), c("bois_fonce"), name="Porte")
            b.box((3.9, y_toit + 1.8, 3.4), (4.25, y_toit + 3.4, 6.0), VITRE, collide=False)
            b.box((-4.25, y_toit + 1.8, 3.4), (-3.9, y_toit + 3.4, 6.0), VITRE, collide=False)
            ya = y_toit + 5.2
            b.cyl((2.6, ya + 4.5, 6.5), 0.22, 9.0, c("metal"), name="Antenne")
            b.boxc((2.6, ya + 6.5, 6.5), (3.2, 0.2, 0.2), c("metal"), collide=False)
            b.boxc((2.6, ya + 8.0, 6.5), (2.2, 0.2, 0.2), c("metal"), collide=False)
            b.ball((2.6, ya + 9.1, 6.5), 0.45, c("rouge"), material="Neon", collide=False)

        # -- Porche d'entrée (avant -Z) ---------------------------------------------------------
        with b.group("Porche"):
            zf = -R - 7.0     # avant du dallage du porche
            b.box((-8, 0, zf), (8, 1.5, -R - 1.5), c("pave"), studs="top", name="Parvis")
            for k in range(3):
                b.box((-6, 0, zf - 3 + k), (6, 0.5 * (k + 1), zf - 2 + k), c("pave_fonce") if k % 2 else c("pave"),
                      studs="top", name="Marche")
            for x in (-6.6, 6.6):
                b.box((x - 0.6, 0, zf - 3), (x + 0.6, 1.9, zf), c("pave_fonce"), studs="top", name="Limon")
            # Porte dans le tambour
            b.box((-3.2, 1.5, -R - 0.3), (3.2, 9.0, -R + 1.0), blanc, name="Encadrement")
            b.box((-2.5, 1.5, -R - 0.5), (2.5, 8.3, -R + 1.0), c("bois_fonce"), name="Porte")
            b.box((-0.1, 1.5, -R - 0.6), (0.1, 8.3, -R - 0.4), c("noir"), collide=False)
            # Colonnes, poutre, toit
            for x in (-6.8, 6.8):
                for z in (zf + 0.8, -R - 2.2):
                    b.box((x - 0.6, 1.5, z - 0.6), (x + 0.6, 8.0, z + 0.6), rouge, name="Colonne")
                    b.box((x - 0.8, 1.5, z - 0.8), (x + 0.8, 2.1, z + 0.8), blanc)
                    b.box((x - 0.8, 7.4, z - 0.8), (x + 0.8, 8.0, z + 0.8), blanc)
            b.box((-7.8, 8.0, zf), (7.8, 9.0, -R + 2.0), c("bois_fonce"), name="Poutre")
            b.box((-8.0, 8.2, zf - 0.2), (8.0, 8.8, zf + 0.1), blanc, name="Bandeau")
            b.wedge((-8.5, 9.0, zf - 1.5), (8.5, 11.6, -R - 0.6), c(toit), down="-z", studs="top")
            kp = 2.6 / (-R - 0.6 - (zf - 1.5))
            za, zb = zf - 1.5 + 2.0, zf - 1.5 + 4.5
            b.wedge((-8.45, 9.0 + kp * 2.0 + 0.15, za), (8.45, 9.0 + kp * 4.5 + 0.15, zb), shade(c(toit), 0.87),
                    down="-z", studs="top", collide=False, name="RangTuiles")
            b.box((-8.5, 9.0, -R - 0.6), (8.5, 11.6, -R + 2.5), c(toit_f), studs="top", name="Solin")
            # Lampions, enseigne, jardinières
            for x in (-4.6, 4.6):
                _lampion(b, x, 8.0, zf + 0.6, c("orange_lampion"))
            p = b.box((6.1, 3.0, zf + 0.0), (7.5, 7.0, zf + 0.2), c("panneau"), collide=False, name="Enseigne")
            p.label = {"face": "Front", "text": "火影", "color": c("rouge_fonce"), "bg": c("panneau"),
                       "font": "brush", "vertical": True}
            for x in (-10.4, 10.4):
                _jardiniere(b, x, -R - 2.6, 0.0, rng)
            for x in (-8.6, 8.6):
                _lanterne_pierre(b, x, zf - 1.6)

    # -- Ailes -----------------------------------------------------------------------------
    for s in (-1, 1):
        with b.at((0, 0, Z_TAMBOUR), group="AileGauche" if s < 0 else "AileDroite"):
            _aile(b, s, rng, toit, toit_f, vary(rouge, rng, 0.03))

    return {"emprise": (64.0, 51.5), "hauteur": 42.6}


# ----------------------------------------------------------------------------
# Tour au toit bleu
# ----------------------------------------------------------------------------

def tour_bleue(b, variant: int = 0) -> dict:
    """Tour blanche cylindrique à colombages et cône de tuiles bleues en gradins (≈ 22 × 22 × 60).

    variant : nombre de gradins (8, 7, 8, 7), balcon de guet (0, 2), bois clair ou sombre."""
    rng = b.rng
    n_gradins = (8, 7, 8, 7)[variant % 4]
    bois = c(("bois", "bois_fonce", "poutre", "bois")[variant % 4])
    balcon = variant % 4 in (0, 2)
    r = 8.5
    H = 32.0
    blanc = vary("enduit", rng, 0.02)

    with b.group("Fut"):
        b.cyl((0, 0.6, 0), r + 1.2, 1.2, c("pave"), studs="top", name="Socle")
        b.cyl((0, 1.0 + (H - 1.0) / 2, 0), r, H - 1.0, blanc, name="Fut")
        b.cyl((0, 2.2, 0), r + 0.25, 2.0, c("pave_fonce"), name="Soubassement")
        for y in (9.0, 17.0, 25.0):
            b.cyl((0, y, 0), r + 0.3, 0.8, bois, name="Bandeau")
        b.cyl((0, H - 0.6, 0), r + 0.5, 1.4, bois, name="Sabliere")
        # Poteaux de bois verticaux (colombage)
        for i in range(8):
            _plaque(b, r, 22.5 + 45 * i, 3.2, H - 1.3, 0.7, 0.2, bois, collide=False, name="Poteau")
        # Petites fenêtres, en quinconce d'un étage à l'autre (rien au-dessus de la porte au 1er)
        for k, (y0, y1) in enumerate([(4.6, 7.4), (11.0, 14.6), (19.0, 22.6), (26.6, 29.4)]):
            for j in range(4):
                d = (90 * j + (45 if k % 2 else 0)) % 360
                if k == 0 and _ecart(d) < 1:
                    continue
                _plaque(b, r, d, y0 - 0.3, y1 + 0.3, 2.0, 0.22, bois, collide=False)
                _plaque(b, r, d, y0, y1, 1.4, 0.32, VITRE, collide=False, name="Fenetre")
                _plaque(b, r, d, y0 - 0.65, y0 - 0.3, 2.4, 0.5, bois, collide=False, name="Appui")

    if balcon:
        with b.group("Balcon"):
            yb = 25.4
            b.cyl((0, yb, 0), r + 2.0, 0.6, c("bois_clair"), studs="top", name="Plancher")
            for i in range(8):
                with b.at((0, 0, 0), yaw=-(45 * i + 22.5)):
                    b.wedge_under((-0.3, yb - 2.2, -r - 1.8), (0.3, yb - 0.3, -r + 0.3), bois, down="-z")
            _garde_corps(b, r + 1.6, yb + 0.3, 1.5, 16, bois, bois, skip=lambda d: False)

    with b.group("Entree"):
        z0 = -r
        b.box((-2.0, 1.2, z0 - 0.4), (2.0, 7.2, z0 + 1.0), bois, name="Encadrement")
        b.box((-1.4, 1.2, z0 - 0.6), (1.4, 6.6, z0 + 1.0), c("bois_fonce"), name="Porte")
        b.box((-2.6, 0, z0 - 2.4), (2.6, 1.2, z0 + 0.5), c("pave"), studs="top", name="Marche")
        b.wedge((-2.8, 7.6, z0 - 2.2), (2.8, 9.2, z0 + 0.6), c("toit_bleu"), down="-z", studs="top", name="Auvent")
        b.box((-2.8, 7.2, z0 - 2.2), (2.8, 7.6, z0 + 0.6), bois)
        for x in (-2.4, 2.4):
            b.wedge_under((x - 0.25, 5.8, z0 - 1.8), (x + 0.25, 7.2, z0 + 0.4), bois, down="-z")
        _lampion(b, 0, 7.2, z0 - 1.6, c("orange_lampion"), r=0.6, h=1.2)

    with b.group("Cone"):
        # Consoles sous le premier gradin
        for i in range(8):
            with b.at((0, 0, 0), yaw=-(45 * i + 22.5)):
                b.wedge_under((-0.35, H - 2.6, -r - 2.0), (0.35, H - 0.2, -r + 0.3), bois, down="-z")
        y = H - 0.3
        r_base, r_haut = 10.8, 1.8
        hauteur_cone = 24.0
        poids = [1 - 0.25 * i / (n_gradins - 1) for i in range(n_gradins)]
        for i in range(n_gradins):
            t = i / (n_gradins - 1)
            ri = r_haut + (r_base - r_haut) * (1 - t) ** 1.2
            h_g = hauteur_cone * poids[i] / sum(poids) + 0.2
            col = c("toit_bleu") if i % 2 == 0 else c("toit_bleu_clair")
            b.cyl((0, y + h_g / 2, 0), ri, h_g, col, studs="top", name=f"Gradin{i + 1}")
            if i == 0:
                b.cyl((0, y + 0.175, 0), ri + 0.2, 0.55, shade(col, 0.75), collide=False, name="Larmier")
            y += h_g - 0.2
        b.cyl((0, y + 0.6, 0), 1.1, 1.6, bois, name="Pinacle")
        b.ball((0, y + 2.3, 0), 1.2, OR, name="Boule")
        b.cyl((0, y + 4.2, 0), 0.15, 2.4, OR, collide=False, name="Fleche")
        y_top = y + 5.4

    return {"emprise": (22.0, 22.0), "hauteur": round(y_top, 1)}
