"""Terrains d'entraînement et stade de l'académie (zone My Hero Academia, zone 8), style « stud ».

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :
- stade(passage=104, largeur=280, longueur=128, arene=(76, 46), hauteur=36, y_portique=38) — ≈ 1 260 pièces :
    le stade qui accueille la place des œufs. Posé sans rotation au centre de l'arène, la route le traverse
    selon Z local. Tribunes latérales de 12 gradins (gros blocs de sièges : grand chevron lavande à liseré blanc
    sur fond violet, rangs bleus en haut et en bas ; allées à demi-marches ; ruban LED cyan entre les deux
    anneaux ; loges vitrées en haut), angles extérieurs en pan coupé, façade arrière de béton blanc à nervures,
    bandeaux vitrés et lignes néon ; verrières cantilever (mâts à drapeaux, fermes blanches, haubans, verre,
    bannières sous la rive, jamais au-dessus de |x| < 84) ; abris des bancs de touche ; tribunes basses aux
    extrémités et murs d'extrémité de 22 à portes vitrées ; deux portiques treillis à ÉCRAN GÉANT (image
    abstraite de couchant et d'étincelle, aucun texte) au-dessus des ouvertures de la route (dessous à 38,
    ouverture |x| < 52 libre jusque-là), panneau STADE sur la face extérieure ; quatre mâts d'éclairage.
    L'arène (|x| < 76, |z| < 46) reste vide : zone.py y peint la pelouse, la piste et la mosaïque.
- dome_entrainement(rayon=52, hauteur=50) — ≈ 640 pièces : parc d'entraînement sous dôme de verre (anneau de
    béton blanc à ligne néon cyan, coupole à facettes de verre teinté en 6 anneaux de 24 panneaux, méridiens
    et cerces blancs, lanterneau) ; dedans : pelouse, allées, place à fontaine et anneau lumineux, étang,
    montagne rocheuse artificielle à deux pics et cascade, bâtiment en dôme rouge à porte ronde, petit îlot
    de ville, arbres ronds. Entrée de 27 de large vers -Z local sous un auvent ENTRAÎNEMENT à liseré cyan.
- immeuble_factice(largeur, profondeur, hauteur, degats=0..2) — ≤ 44 pièces : immeuble d'entraînement de la
    ville factice (intact avec cible sur le toit, écorné ou très endommagé avec pans déchiquetés, brèches,
    dalles et fers à nu, gravats et ruban de danger).
- decombres() — 13 pièces : tas de gravats (butte, dalles basculées, poutre rouillée, blocs).
- robot_entrainement() — 18 à 25 pièces : robots d'entraînement de dessin original (cubiques, un seul œil
    rond, bandes de danger) : v0 petit robot à roues, v1 marcheur bipède, v2 drone sur son pylône de
    recharge, v3 chenillé à bras de sparring rembourré.
- cible() — 7 à 8 pièces : v0 ronde sur trépied, v1 panneau carré, v2 cible escamotable sur mât.

Repère (voir CONVENTIONS.md) : origine au centre de l'emprise au sol, y = 0 au sol, l'AVANT regarde -Z local.
Exception : `stade` est posé sans rotation (yaw 0), symétrique, la route suit son axe Z local.

Propriété intellectuelle : installations d'entraînement génériques. Aucun nom, aucune lettre (sauf les mots
génériques STADE et ENTRAÎNEMENT, police « sans »), aucun emblème, aucun personnage. Les robots sont des
dessins originaux sans chiffres ni marques ; les écrans n'affichent que des aplats de couleur abstraits.
"""

from __future__ import annotations

import math

import numpy as np

from assets.mobilier import _label, _segment
from kit import hexrgb, mix, rot_z
from palette import c, tirer, vary
from textures import mask_rects

# ---------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------


def col(x):
    """Nom de palette, '#hex' ou tuple → tuple RGB."""
    if isinstance(x, tuple):
        return x
    if isinstance(x, str) and x.startswith("#"):
        return hexrgb(x)
    return c(x)


def _unit(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else v


def _repere(X, Y):
    """Matrice de rotation (colonnes X, Y, Z) à partir de deux axes presque orthogonaux."""
    X = _unit(X)
    Y = np.asarray(Y, float)
    Y = _unit(Y - X * float(X @ Y))
    Z = np.cross(X, Y)
    return np.column_stack([X, Y, Z])


def _piece(b, forme, taille, centre, X, Y, couleur, **kw):
    """Pièce quelconque orientée par ses axes locaux X et Y (Z = X × Y)."""
    return b.part(forme, taille, centre, _repere(X, Y), col(couleur), **kw)


def _neon(b, a, bb, couleur="neon_cyan", **kw):
    kw.setdefault("name", "Neon")
    return b.box(a, bb, col(couleur), material="Neon", collide=False, shadow=False, **kw)


def _oblique(b, A, B, y0, y1, ep, couleur, *, off=0.0, ext=0.0, forme="block", **kw):
    """Mur vertical le long du segment horizontal A → B (points (x, z)), d'épaisseur `ep`, décalé de `off`
    vers l'extérieur (côté gauche de A → B vu de dessus, normale = X local). En « wedge », la pente
    monte de A vers B (face pleine du côté de B)."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    u = _unit(np.array([B[0] - A[0], 0.0, B[1] - A[1]]))
    X = np.array([u[2], 0.0, -u[0]])            # X × Y = u
    L = float(np.hypot(*(B - A))) + 2 * ext
    m = (A + B) / 2
    ctr = np.array([m[0], (y0 + y1) / 2, m[1]]) + X * off
    return b.part(forme, (ep, y1 - y0, L), ctr, np.column_stack([X, [0, 1, 0], u]), col(couleur), **kw)


def _poutre_xy(b, P0, P1, ep_y, ep_z, z, couleur, *, off=0.0, **kw):
    """Poutre dans le plan (x, y) de P0 à P1 (points (x, y)), section ep_y × ep_z, centrée en z,
    décalée de `off` selon sa normale « vers le haut »."""
    P0, P1 = np.asarray(P0, float), np.asarray(P1, float)
    d = P1 - P0
    a = math.degrees(math.atan2(d[1], d[0]))
    R = rot_z(a)
    n = R @ np.array([0.0, 1.0, 0.0])
    m = (P0 + P1) / 2
    ctr = np.array([m[0], m[1], z]) + n * off
    return b.part("block", (float(np.hypot(*d)), ep_y, ep_z), ctr, R, col(couleur), **kw)


def _pixels(b, grille, x0, y0, cw, ch, z0, z1, materiau="Neon"):
    """Image en pixels (liste de chaînes, une lettre par case, '.' = vide) posée dans le plan (x, y),
    entre z0 et z1 ; les cases de même couleur sont fusionnées en rectangles. Lettres :
    v violet clair, V violet, l lavande, b blanc, c cyan, o orange, j jaune, r rose, n bleu vif."""
    couleurs = {"v": c("violet"), "l": c("lavande"), "b": c("neon_blanc"), "c": c("ecran_lumiere"),
                "o": c("orange"), "j": c("jaune"), "r": hexrgb("#E2629E"), "n": c("bleu_vif"), "V": c("violet_fonce")}
    h = len(grille)
    w = max(len(r) for r in grille)
    arr = np.array([list(r.ljust(w, ".")) for r in grille])
    n = 0
    for k, nom in couleurs.items():
        mask = arr == k
        if not mask.any():
            continue
        for (i, j, ww, hh) in mask_rects(mask):
            # ligne 0 = haut de l'image
            ya = y0 + (h - j - hh) * ch
            b.box((x0 + i * cw, ya, z0), (x0 + (i + ww) * cw, ya + hh * ch, z1), nom, material=materiau,
                  collide=False, shadow=False, name="Pixel")
            n += 1
    return n


# ---------------------------------------------------------------------------
# 1. Stade (place des œufs)
# ---------------------------------------------------------------------------

N_RANGS = 12            # gradins des tribunes latérales
PROF_RANG = 4.5
ALLEES = (-48, -32, -16, 0, 16, 32, 48)
DEMI_ALLEE = 1.0
Z_BANC = 8.0            # abri des bancs de touche : |z| < 8, au pied de la tribune
Y_PLINTHE = 22.0        # mur d'extrémité (bout des tribunes) et hauteur des tribunes basses


def _siege(i, u, cote):
    """Couleur d'un bloc de sièges : rang i (0 en bas), position u le long de la tribune (côté ±1).
    Un grand chevron en V centré sur le milieu de la tribune : bande lavande à liseré blanc sur fond violet,
    deux rangs bleus en bas et en haut pour cadrer (motif abstrait, aucun emblème)."""
    k = math.floor(abs(u) / 7.0)
    d = (k + i) % 10
    if d == 0:
        return "siege_blanc"
    if d in (1, 2, 3):
        return "siege_lavande"
    if i < 2 or i >= N_RANGS - 2:
        return "siege_bleu"
    return "siege_violet"


def _ligne_chanfrein(AX, PZ, hauteur):
    """Pan coupé des angles : segment A (bout du mur d'extrémité) → B (coin du mur arrière), en (x, z)."""
    x_fond = AX + 1 + N_RANGS * PROF_RANG + 4.0          # axe du mur arrière (135)
    A = (AX + 1 + 6 * PROF_RANG + 0.5, PZ - 1.2)          # (104.5, 62.8)
    B = (x_fond, 46.5)
    return A, B, x_fond


def _z_chanfrein(A, B, x):
    return A[1] + (x - A[0]) * (B[1] - A[1]) / (B[0] - A[0])


def _tribune_laterale(b, rng, AX, AZ, PZ, H, cote):
    """Tribune latérale côté +X du repère courant (le stade la pose deux fois, yaw 0 et 180)."""
    x0 = AX + 1.0
    xs = [x0 + PROF_RANG * i for i in range(N_RANGS + 1)]
    tops = [4.0 + i * (H - 4.0) / (N_RANGS - 1) for i in range(N_RANGS)]
    montee = (H - 4.0) / (N_RANGS - 1)
    A, B, x_fond = _ligne_chanfrein(AX, PZ, H)
    Ls = []
    for i in range(N_RANGS):
        L = PZ - 1.5
        if xs[i + 1] > A[0] + 0.01:
            L = min(L, _z_chanfrein(A, B, xs[i + 1]))
        Ls.append(L)

    with b.group("Gradins"):
        for i in range(N_RANGS):
            xa, xb, top, L = xs[i], xs[i + 1], tops[i], Ls[i]
            beton = vary("beton_tribune", rng, 0.03)
            if i < 2:          # gradins coupés par l'abri des bancs de touche
                for s in (-1, 1):
                    b.box((xa, 0, s * Z_BANC), (xb, top, s * L), beton, studs="top", name="Gradin")
            else:
                b.box((xa, 0, -L), (xb, top, L), beton, studs="top", name="Gradin")
            # sièges : un bloc par demi-section, entre les allées
            bornes = [-L] + [v for a in ALLEES for v in (a - DEMI_ALLEE, a + DEMI_ALLEE)] + [L]
            for k in range(0, len(bornes), 2):
                za, zb = bornes[k], bornes[k + 1]
                if zb - za < 2.5:
                    continue
                zm = (za + zb) / 2
                for (u0, u1) in ((za, zm), (zm, zb)):
                    if u1 - u0 < 1.5:
                        continue
                    if i < 2 and abs((u0 + u1) / 2) < Z_BANC:
                        continue
                    nom = _siege(i, (u0 + u1) / 2, cote)
                    b.box((xa + 0.9, top, u0 + 0.05), (xb - 0.3, top + montee - 0.4, u1 - 0.05), c(nom), studs="top",
                          name="Sieges")
            # demi-marches des allées
            if i < N_RANGS - 1:
                for a in ALLEES:
                    if abs(a) + DEMI_ALLEE > L - 0.5 or (i < 2 and abs(a) < Z_BANC):
                        continue
                    b.box((xa + PROF_RANG / 2, top, a - 0.9), (xb, top + montee / 2, a + 0.9), c("beton_clair"),
                          studs="top", name="Marche")
        # ruban LED sur la contremarche du rang 6 : sépare l'anneau bas de l'anneau haut
        r = 6
        b.box((xs[r] - 0.25, tops[r - 1] + montee - 0.35, -Ls[r - 1] + 0.5), (xs[r], tops[r] - 0.05, Ls[r - 1] - 0.5),
              c("neon_cyan"), material="Neon", collide=False, shadow=False, name="RubanLED")
        # coursive haute derrière le dernier rang
        Lc = _z_chanfrein(A, B, x_fond - 0.8)
        b.box((xs[-1], 0, -Lc), (x_fond - 0.8, H, Lc), c("dalle_claire"), studs="top", name="Coursive")
        # loges vitrées sur la coursive, sous la verrière
        xl = xs[-1] + 0.4
        zl = Lc - 1.0
        b.box((xl, H, -zl), (x_fond - 0.8, H + 3.4, zl), c("vitre_violette_claire"), name="Loges")
        b.box((xl - 0.3, H + 3.4, -zl - 0.2), (x_fond - 0.8, H + 4.0, zl + 0.2), c("blanc"), studs="top", name="Loges")
        _neon(b, (xl - 0.25, H + 3.0, -zl), (xl, H + 3.3, zl), "neon_violet")
        z = -zl + 0.6
        while z < zl:
            b.box((xl - 0.2, H, z - 0.3), (xl, H + 3.4, z + 0.3), c("blanc"), name="Montant")
            z += 7.0

    with b.group("Lisse"):
        # muret du bord de l'arène, coupé au droit de l'abri des bancs
        for s in (-1, 1):
            za, zb = sorted((s * Z_BANC, s * (AZ + 0.2)))
            b.box((AX + 0.2, 0, za), (AX + 1.4, 5.0, zb), c("blanc"), name="Muret")
            b.box((AX + 0.0, 1.8, za), (AX + 0.2, 3.4, zb), c("violet"), collide=False, name="Bande")
            b.box((AX + 0.05, 3.8, za), (AX + 0.2, 4.2, zb), c("lavande"), collide=False, name="Filet")
            b.box((AX + 0.0, 5.0, za), (AX + 1.6, 5.4, zb), c("blanc_casse"), studs="top", name="Chaperon")

    with b.group("BancsDeTouche"):
        xa, xb = AX + 0.2, xs[2]
        b.box((xa, 0, -Z_BANC), (xb, 0.3, Z_BANC), c("beton_fonce"), studs="top", name="Sol")
        b.box((xb - 0.2, 0.3, -Z_BANC + 0.6), (xb, 4.6, Z_BANC - 0.6), c("violet"), name="Fond")
        b.box((xb - 2.6, 0.3, -6.5), (xb - 0.6, 1.8, 6.5), c("siege_bleu"), studs="top", name="Banc")
        b.box((xb - 0.6, 0.3, -6.5), (xb - 0.2, 3.4, 6.5), c("siege_bleu"), name="Dossier")
        b.box((xa + 0.2, 5.5, -Z_BANC + 0.3), (xb + 0.2, 5.8, Z_BANC - 0.3), c("verre_canopee"), material="Glass",
              transparency=0.35, name="Toit")
        b.box((xa, 5.2, -Z_BANC + 0.2), (xa + 0.6, 6.0, Z_BANC - 0.2), c("blanc"), name="Rive")
        _neon(b, (xa - 0.1, 5.25, -Z_BANC + 0.4), (xa, 5.75, Z_BANC - 0.4))
        for s in (-1, 1):
            b.box((xa, 0.3, s * (Z_BANC - 0.5) - 0.2), (xa + 0.4, 5.2, s * (Z_BANC - 0.5) + 0.2), c("blanc"),
                  collide=False, name="Poteau")

    with b.group("Facade"):
        # mur arrière
        za = _z_chanfrein(A, B, x_fond) + 0.8
        ext = x_fond + 0.8
        b.box((x_fond - 0.8, 0, -za), (ext, 40, za), c("blanc_casse"), name="MurArriere")
        b.box((x_fond - 1.2, 40, -za), (ext + 0.4, 40.6, za), c("blanc"), studs="top", name="Couvertine")
        for (ya, yb, v) in ((4, 10, "vitre_violette_claire"), (15, 20, "vitre_bleue"), (25, 30, "vitre_violette")):
            b.box((ext, ya, -za + 0.6), (ext + 0.2, yb, za - 0.6), c(v), name="Bandeau")
        _neon(b, (ext, 35.6, -za + 0.6), (ext + 0.35, 36.0, za - 0.6))
        _neon(b, (ext, 11.2, -za + 0.6), (ext + 0.3, 11.5, za - 0.6), "neon_violet")
        for z in (-35, -21, -7, 7, 21, 35):
            b.box((ext, 0, z - 0.6), (ext + 1.0, 40, z + 0.6), c("blanc"), name="Nervure")
        for z in (-42, -28, -14, 0, 14, 28, 42):          # portes d'accès entre les nervures
            if abs(z) == 42:
                continue
            b.box((ext, 0, z + 2.0), (ext + 0.15, 3.2, z + 5.0), c("vitre_nuit"), name="Porte")
        # pans coupés : base verticale puis rampant de 22 à 40
        for s in (-1, 1):
            Aa, Bb = (A[0], s * A[1]), (B[0], s * B[1])
            P, Q = (Aa, Bb) if s > 0 else (Bb, Aa)
            # (P → Q) : la normale X locale pointe vers l'extérieur du stade
            if s > 0:
                _oblique(b, P, Q, 0, Y_PLINTHE, 1.6, "blanc_casse", ext=0.8, name="PanCoupe")
                _oblique(b, P, Q, Y_PLINTHE, 40, 1.6, "blanc_casse", forme="wedge", ext=0.8, name="PanCoupe")
            else:
                _oblique(b, P, Q, 0, Y_PLINTHE, 1.6, "blanc_casse", ext=0.8, name="PanCoupe")
                # la pente doit monter vers le mur arrière (P = coin du mur arrière ici) : wedge de Q vers P
                _oblique(b, Q, P, Y_PLINTHE, 40, 1.6, "blanc_casse", forme="wedge", ext=0.8, off=0.0,
                         name="PanCoupe")
            sgn = -1                       # la normale X locale de _oblique pointe ici vers l'intérieur
            _oblique(b, P, Q, 4, 10, 0.2, "vitre_violette_claire", off=sgn * 0.9, ext=-1.2, name="Bandeau")
            _oblique(b, P, Q, 14, 18, 0.2, "vitre_bleue", off=sgn * 0.9, ext=-1.2, name="Bandeau")
            _oblique(b, P, Q, 19.8, 20.2, 0.35, "neon_cyan", off=sgn * 0.95, ext=-0.6, material="Neon",
                     collide=False, shadow=False, name="Neon")
            for t in (0.25, 0.5, 0.75):
                Pm = (P[0] + (Q[0] - P[0]) * t, P[1] + (Q[1] - P[1]) * t)
                Pn = (P[0] + (Q[0] - P[0]) * (t + 0.035), P[1] + (Q[1] - P[1]) * (t + 0.035))
                yh = Y_PLINTHE + (40 - Y_PLINTHE) * ((Pm[0] - A[0]) / (B[0] - A[0])) - 0.5
                _oblique(b, Pm, Pn, 0, yh, 1.0, "blanc", off=sgn * 1.2, name="Nervure")

    return {"xs": xs, "tops": tops, "x_fond": x_fond, "A": A, "B": B}


def _verriere(b, rng, AX, x_fond, n_fermes=7, pas=14.0):
    """Verrière cantilever au-dessus de la tribune côté +X : mâts derrière la façade, fermes, haubans,
    panneaux de verre, rive avant à néon cyan. Jamais au-dessus de |x| < 84."""
    x_mat = x_fond + 2.8                     # axe des mâts (137.8)
    x_av = AX + 8.0                          # rive avant (84)
    y_ar, y_av = 41.5, 46.0
    zs = [(k - (n_fermes - 1) / 2) * pas for k in range(n_fermes)]
    z_bord = zs[-1] + 6.0
    with b.group("Verriere"):
        for k, z in enumerate(zs):
            b.box((x_mat - 1.0, 0, z - 1.0), (x_mat + 1.0, 54, z + 1.0), c("blanc"), name="Mat")
            b.box((x_mat - 1.3, 0, z - 1.3), (x_mat + 1.3, 1.0, z + 1.3), c("beton_fonce"), studs="top", name="Platine")
            _neon(b, (x_mat + 1.0, 6, z - 0.25), (x_mat + 1.25, 50, z + 0.25))
            _poutre_xy(b, (x_mat, y_ar), (x_av, y_av), 1.2, 1.4, z, c("blanc"), name="Ferme")
            _segment(b, (x_mat, 53.6, z), (x_av + 3.0, y_av + 0.2, z), 0.22, c("acier"), name="Hauban")
            _segment(b, (x_mat, 53.6, z), (x_av + 26.0, y_av - 2.0 + 0.25, z), 0.18, c("acier"), name="Hauban")
            # drapeau au sommet du mât
            b.cyl((x_mat, 56.5, z), 0.15, 5.0, c("acier"), collide=False, name="Hampe")
            dr = ("violet", "lavande", "orange_couchant", "bleu_vif", "blanc", "violet", "lavande")[k % 7]
            b.box((x_mat - 0.05, 56.2, z + 0.15), (x_mat + 0.05, 58.8, z + 3.8), c(dr), collide=False, shadow=False,
                  name="Drapeau")
        # panneaux de verre entre les fermes (+ deux bouts)
        bords = [-z_bord] + zs + [z_bord]
        for za, zb in zip(bords, bords[1:]):
            y_dep = y_ar + (y_av - y_ar) * 1.0 / (x_mat - x_av)
            _poutre_xy(b, (x_mat - 1.0, y_dep), (x_av, y_av), 0.3, (zb - za) - 1.0, (za + zb) / 2,
                       c("verre_canopee"), off=0.78, material="Glass", transparency=0.35, name="Verre")
        # pannes longitudinales sous le verre et rive avant
        for t in (0.35, 0.7):
            x = x_mat + (x_av - x_mat) * t
            y = y_ar + (y_av - y_ar) * t
            b.box((x - 0.4, y - 0.5, -z_bord), (x + 0.4, y + 0.4, z_bord), c("blanc"), collide=False, name="Panne")
        b.box((x_av - 0.6, y_av - 0.9, -z_bord), (x_av + 0.9, y_av + 1.2, z_bord), c("blanc"), name="Rive")
        _neon(b, (x_av - 0.8, y_av - 0.6, -z_bord + 0.2), (x_av - 0.6, y_av - 0.1, z_bord - 0.2))
        # bannières suspendues sous la rive (une par travée), motifs de bandes seulement
        for k, (za, zb) in enumerate(zip(zs, zs[1:])):
            zm = (za + zb) / 2
            fond, bande = (("violet", "blanc"), ("blanc", "violet"), ("lavande", "orange_couchant"))[k % 3]
            b.box((x_av + 0.0, y_av - 8.5, zm - 1.8), (x_av + 0.2, y_av - 0.9, zm + 1.8), c(fond), collide=False,
                  shadow=False, name="Banniere")
            b.box((x_av - 0.1, y_av - 6.0, zm - 1.8), (x_av + 0.3, y_av - 5.0, zm + 1.8), c(bande), collide=False,
                  shadow=False, name="Bande")
    return {"z_bord": z_bord}


def _tribune_bout(b, rng, AX, AZ, PZ, P2, sx):
    """Tribune basse d'extrémité (côté +Z du repère courant), entre |x| = passage/2 et l'arène.
    `sx` = côté en x (±1). Gradins montant vers +Z, mur latéral rampant côté route."""
    xa_int = P2 + 0.8                        # face côté route (52,8), en retrait de la face des pylônes (52,4)
    x_mur = xa_int + 1.6                     # 54,4
    z_mur = PZ - 2.0                         # 62 : face intérieure du mur d'extrémité
    n = 5
    zs = [AZ + 1.0 + 3.0 * j for j in range(n + 1)]   # 47 → 62
    zs[-1] = z_mur + 0.5
    tops = [4.5 + 3.0 * j for j in range(n)]

    def X(x):
        return sx * x

    def bx(a, bb, couleur, **kw):
        return b.box((X(a[0]), a[1], a[2]), (X(bb[0]), bb[1], bb[2]), couleur, **kw)

    with b.group("TribuneBout"):
        for j in range(n):
            bx((x_mur, 0, zs[j]), (AX + 0.8, tops[j], zs[j + 1]), vary("beton_tribune", rng, 0.03), studs="top",
               name="Gradin")
            for (u0, u1) in ((58.8, 66.8), (68.6, AX + 0.6)):
                nom = ("siege_bleu", "siege_violet", "siege_violet", "siege_lavande", "siege_blanc")[j]
                if (j + (u0 > 60) + (sx > 0)) % 3 == 0:
                    nom = "siege_lavande" if nom != "siege_lavande" else "siege_blanc"
                bx((u0, tops[j], zs[j] + 1.0), (u1, tops[j] + 2.6, zs[j + 1] - (0.8 if j == n - 1 else 0.3)), c(nom),
                   studs="top", name="Sieges")
            if j < n - 1:
                bx((66.9, tops[j], zs[j] + 1.5), (68.5, tops[j] + 1.5, zs[j + 1]), c("beton_clair"), studs="top",
                   name="Marche")
        # muret du bord de l'arène
        bx((x_mur, 0, AZ + 0.2), (AX + 1.4, 5.0, AZ + 1.4), c("blanc"), name="Muret")
        bx((x_mur, 1.8, AZ + 0.0), (AX + 0.2, 3.4, AZ + 0.2), c("violet"), collide=False, name="Bande")
        bx((x_mur, 3.8, AZ + 0.05), (AX + 0.2, 4.2, AZ + 0.2), c("lavande"), collide=False, name="Filet")
        bx((x_mur, 5.0, AZ + 0.0), (AX + 1.6, 5.4, AZ + 1.6), c("blanc_casse"), studs="top", name="Chaperon")
        # mur latéral rampant (face côté route)
        bx((xa_int, 0, AZ), (x_mur, 6.0, z_mur), c("blanc_casse"), name="MurRoute")
        xa, xb = sorted((X(xa_int), X(x_mur)))
        b.wedge((xa, 6.0, AZ), (xb, Y_PLINTHE, z_mur), c("blanc_casse"), down="-z", name="MurRoute")
        z_stop = PZ - 9.1                    # s'arrête avant les pylônes du portique (face en |x| = 52,4 dès PZ - 9)
        bx((xa_int - 0.4, 1.4, AZ + 0.6), (xa_int, 3.0, z_stop), c("violet"), collide=False, name="Bande")
        # liseré néon le long du rampant
        y_ramp = 6.0 + (Y_PLINTHE - 6.0) * (z_stop - AZ) / (z_mur - AZ)
        p0 = np.array([X(xa_int - 0.2), 6.0 - 1.2, AZ + 0.6])
        p1 = np.array([X(xa_int - 0.2), y_ramp - 1.2, z_stop])
        d = p1 - p0
        _piece(b, "block", (0.4, 0.4, float(np.linalg.norm(d))), (p0 + p1) / 2, (1, 0, 0), (0, d[2], -d[1]),
               "neon_cyan", material="Neon", collide=False, shadow=False, name="Neon")


def _mur_bout(b, rng, AX, PZ, P2, x_fin):
    """Mur d'extrémité (z ≈ +PZ du repère courant) des deux côtés de l'ouverture : de |x| = passage/2 au pan
    coupé. Face extérieure : nervures blanches, bandeau vitré, néon cyan, portes."""
    z0, z1 = PZ - 2.0, PZ - 0.4
    with b.group("MurBout"):
        for s in (-1, 1):
            xa, xb = sorted((s * (P2 + 0.8), s * x_fin))
            b.box((xa, 0, z0), (xb, Y_PLINTHE, z1), c("blanc_casse"), name="Mur")
            b.box((xa, Y_PLINTHE, z0 - 0.2), (xb, Y_PLINTHE + 0.6, z1 + 0.4), c("blanc"), studs="top",
                  name="Couvertine")
            xa2, xb2 = sorted((s * (P2 + 6.5), s * (x_fin - 0.5)))
            b.box((xa2, 9.0, z1), (xb2, 15.0, z1 + 0.2), c("vitre_violette_claire"), name="Bandeau")
            _neon(b, (xa2, 18.6, z1), (xb2, 19.0, z1 + 0.3))
            # bandeau intérieur (vu de l'arène, au-dessus des gradins)
            xa3, xb3 = sorted((s * (P2 + 2.0), s * (x_fin - 1.0)))
            _neon(b, (xa3, 19.2, z0 - 0.25), (xb3, 19.6, z0), "neon_violet")
            for x in (64, 72, 80, 88, 96):
                b.box((s * x - 0.6, 0, z1), (s * x + 0.6, Y_PLINTHE, z1 + 0.4), c("blanc"), name="Nervure")
            for x in (76, 92):              # portes d'accès vitrées
                b.box((s * x - 3.2, 0, z1), (s * x + 3.2, 6.6, z1 + 0.12), c("vitre_nuit"), name="Porte")
                b.box((s * x - 3.8, 6.6, z1), (s * x + 3.8, 7.4, z1 + 0.35), c("blanc"), name="Linteau")
                _neon(b, (s * x - 3.3, 6.7, z1 + 0.3), (s * x + 3.3, 7.0, PZ))


def _image_ecran(nx=47, ny=13):
    """Image abstraite de l'écran géant (aucun texte) : ciel du couchant en dégradé (violet → rose → orange),
    grande étincelle blanche à huit branches et cœur jaune au centre, bandeau bas multicolore.
    Renvoie une liste de chaînes (voir `_pixels`)."""
    ciel = ["V", "V", "v", "v", "v", "r", "r", "o", "o", "j", "o"]
    lignes = []
    for j in range(ny):
        row = []
        for i in range(nx):
            dx = (i - (nx - 1) / 2) * 2.0           # cases de 2 × 1,08 studs
            dy = ((ny - 2) / 2 - j) * 1.08
            if j == ny - 1:                          # bandeau bas
                k = int(abs(i - (nx - 1) / 2)) // 4
                row.append("cnVvoV"[k % 6])
                continue
            if j == ny - 2:
                row.append(".")
                continue
            u, v = (dx + dy * 2) / math.sqrt(5), (dx - dy * 2) / math.sqrt(5)
            if abs(dx) < 2.2 and abs(dy) < 1.0:
                row.append("j")
            elif abs(dx) * abs(dy) < 8.5 and abs(dx) < 17.5 and abs(dy) < 6.0:
                row.append("b")
            elif abs(u) * abs(v) < 4.0 and max(abs(u), abs(v)) < 10.5:
                row.append("l")
            else:
                row.append(ciel[min(j, len(ciel) - 1)])
        lignes.append("".join(row))
    return lignes


ECRAN = _image_ecran()


def _portique(b, rng, AX, PZ, P2, y_bas, hauteur_ecran=14.0):
    """Portique à écran géant au-dessus de l'ouverture côté +Z du repère courant : deux pylônes au bord de
    l'ouverture, poutre treillis blanche (membrures, âme sombre en retrait, diagonales) dont le dessous est
    à y_bas, écran tourné vers l'arène (-Z), panneau STADE tourné vers l'extérieur (+Z)."""
    za, zb = PZ - 10.0, PZ - 2.0             # 54 → 62
    y0, y1 = y_bas, y_bas + 16.0             # 38 → 54
    xp = P2 + 6.4                            # face extérieure des pylônes (58,4)
    with b.group("Portique"):
        for s in (-1, 1):
            xa, xb = sorted((s * (P2 + 0.4), s * xp))
            b.box((xa, 0, za + 1.0), (xb, y1 + 4.0, zb + 1.0), c("blanc"), name="Pylone")
            b.box((xa - 0.3, y1 + 4.0, za + 0.7), (xb + 0.3, y1 + 4.6, zb + 1.3), c("blanc_casse"), studs="top",
                  name="Chapeau")
            b.box((xa - 0.3, 0, za + 0.7), (xb + 0.3, 1.2, zb + 1.3), c("beton_fonce"), studs="top", name="Socle")
            xi = s * (P2 + 0.4)
            xn = sorted((xi, xi - s * 0.4))
            _neon(b, (xn[0], 1.5, za + 3.4), (xn[1], y1 + 3.0, za + 4.6))
            xg = sorted((xi, xi - s * 0.2))
            b.box((xg[0], 2.0, za + 5.4), (xg[1], y0 - 2.0, za + 8.4), c("vitre_violette"), name="Vitrage")
            b.box((xg[0], 2.0, za + 1.6), (xg[1], y0 - 2.0, za + 2.8), c("vitre_violette_claire"), name="Vitrage")
            # balise rouge au sommet
            b.box((s * (P2 + 3.4) - 0.4, y1 + 4.6, za + 4.6), (s * (P2 + 3.4) + 0.4, y1 + 5.4, za + 5.4), "#FF3B30",
                  material="Neon", collide=False, shadow=False, name="Balise")
        # poutre treillis : membrures blanches, âme sombre en retrait, diagonales sur la face extérieure
        xe = xp - 0.5                        # la poutre se termine dans les pylônes (pas de face commune)
        b.box((-xe, y1 - 4.0, za), (xe, y1, zb), c("blanc"), studs="top", name="MembrureHaute")
        b.box((-xe, y0, za), (xe, y0 + 3.0, zb), c("blanc"), name="MembrureBasse")
        b.box((-xe, y0 + 3.0, za + 1.5), (xe, y1 - 4.0, zb - 1.5), c("marine"), name="Ame")
        for z in (za, zb):
            zn = sorted((z, z + (-0.3 if z < (za + zb) / 2 else 0.3)))
            _neon(b, (-xp + 1.0, y0 + 0.5, zn[0]), (xp - 1.0, y0 + 0.9, zn[1]))
        # face extérieure (+Z) : panneau violet STADE, diagonales blanches, néons
        p = b.box((-26, y0 + 3.6, zb - 1.0), (26, y1 - 4.6, zb + 0.4), c("violet"), name="PanneauSTADE")
        _label(p, "STADE", face="Back", couleur=c("blanc"), fond=c("violet"))
        b.box((-27, y0 + 3.0, zb - 1.0), (27, y0 + 3.6, zb + 0.5), c("lavande"), collide=False, name="Filet")
        b.box((-27, y1 - 4.6, zb - 1.0), (27, y1 - 4.0, zb + 0.5), c("lavande"), collide=False, name="Filet")
        for s in (-1, 1):
            xs_ = [27.0, 35.4, 43.8, 52.2]
            for k in range(3):
                xa, xb = s * xs_[k], s * xs_[k + 1]
                ya, yb = (y0 + 3.0, y1 - 4.0) if k % 2 == 0 else (y1 - 4.0, y0 + 3.0)
                _poutre_xy(b, (xa, ya), (xb, yb), 1.0, 1.0, zb - 1.0, c("blanc_casse"), name="Diagonale")
            for x in (27.0, 52.2):
                b.box((s * x - 0.6, y0 + 3.0, zb - 1.6), (s * x + 0.6, y1 - 4.0, zb - 0.4), c("blanc_casse"),
                      name="Montant")
            xa, xb = sorted((s * 28, s * (xp - 1.0)))
            _neon(b, (xa, y1 - 2.2, zb), (xb, y1 - 1.8, zb + 0.3))
        # face intérieure (-Z) : écran géant
        w = 47
        b.box((-(xp - 1.0), y0 + 1.0, za - 0.3), (xp - 1.0, y1 - 0.5, za), c("blanc"), name="CadreEcran")
        b.box((-w, y0 + 1.5, za - 0.7), (w, y1 - 1.0, za - 0.3), c("ecran_fond"), name="Ecran")
        hh = (y1 - 1.0) - (y0 + 1.5)
        _pixels(b, ECRAN, -w, y0 + 1.5, 2.0, hh / len(ECRAN), za - 0.9, za - 0.7)
        for s in (-1, 1):
            xa, xb = sorted((s * (w + 1.5), s * (xp - 1.0)))
            _neon(b, (xa, y0 + 7.0, za - 0.6), (xb, y0 + 7.4, za - 0.3))
            # haut-parleurs sur la membrure haute
            b.box((s * 30 - 1.5, y1, za + 1.0), (s * 30 + 1.5, y1 + 2.4, za + 3.5), c("gris_acier"), name="HautParleur")


def _mat_eclairage(b, x, z, h=56.0):
    """Mât d'éclairage : fût blanc à bague néon, rampe de projecteurs tournée vers le centre de l'arène."""
    a = math.atan2(-x, -z)                      # direction du centre
    d = np.array([math.sin(a), 0.0, math.cos(a)])
    with b.group("MatEclairage"):
        b.box((x - 2.0, 0, z - 2.0), (x + 2.0, 1.2, z + 2.0), c("beton"), studs="top", name="Socle")
        b.cyl((x, 1.2 + 15.0, z), 1.1, 30.0, c("blanc"), name="Fut")
        b.cyl((x, 31.2 + 10.0, z), 0.8, 20.0, c("blanc_casse"), name="Fut")
        b.cyl((x, 30.6, z), 1.25, 0.8, c("neon_cyan"), material="Neon", collide=False, shadow=False, name="Bague")
        # rampe inclinée vers l'arène
        X = np.array([d[2], 0.0, -d[0]])
        Y = _unit(np.array([0.0, 1.0, 0.0]) + d * 0.45)
        ctr = np.array([x, h - 2.0, z]) + d * 0.6
        _piece(b, "block", (9.0, 6.0, 1.0), ctr, X, Y, "acier_fonce", collide=False, name="Rampe")
        Zl = np.cross(_unit(X), Y)                 # normale (vers l'extérieur de la rampe)
        sens = 1.0 if float(Zl @ d) > 0 else -1.0
        for i in range(3):
            for j in range(2):
                cc = ctr + _unit(X) * (-3.0 + 3.0 * i) + Y * (-1.4 + 2.8 * j) + Zl * sens * 0.6
                _piece(b, "block", (2.4, 2.2, 0.4), cc, X, Y, "led", material="Neon", collide=False, shadow=False,
                       name="Projecteur")
        b.box((x - 0.5, 50.0, z - 0.5), (x + 0.5, h - 4.0, z + 0.5), c("acier_fonce"), collide=False, name="Support")


def stade(b, variant=0, passage=104.0, largeur=280.0, longueur=128.0, arene=(76, 46), hauteur=36.0, y_portique=38.0):
    """Stade de la place des œufs (voir l'en-tête du module). Posé avec yaw 0 au centre de l'arène."""
    rng = b.rng
    AX, AZ = float(arene[0]), float(arene[1])
    PZ = longueur / 2
    P2 = passage / 2
    with b.group("Stade"):
        info = {}
        for k, yaw in enumerate((0, 180)):
            with b.at((0, 0, 0), yaw=yaw, group=("TribuneEst", "TribuneOuest")[k]):
                info = _tribune_laterale(b, rng, AX, AZ, PZ, hauteur, 1 if k == 0 else -1)
                _verriere(b, rng, AX, info["x_fond"])
        A = info["A"]
        for k, yaw in enumerate((0, 180)):
            with b.at((0, 0, 0), yaw=yaw, group=("BoutNord", "BoutSud")[k]):
                for sx in (-1, 1):
                    _tribune_bout(b, rng, AX, AZ, PZ, P2, sx)
                _mur_bout(b, rng, AX, PZ, P2, A[0] + 0.8)
                _portique(b, rng, AX, PZ, P2, y_portique)
        with b.group("Mats"):
            for sx in (-1, 1):
                for sz in (-1, 1):
                    _mat_eclairage(b, sx * 126.0, sz * 59.0)
    return {"emprise": (largeur, longueur), "hauteur": 60.0}


# ---------------------------------------------------------------------------
# 2. Parc d'entraînement sous dôme de verre
# ---------------------------------------------------------------------------

DOME_PHI = (0.0, 14.0, 28.0, 42.0, 55.0, 67.0, 78.0)    # anneaux du dôme (élévation, degrés)
DOME_N = 24                                              # panneaux par anneau (méridiens tous les 15°)
VERRE_DOME = mix(c("verre_dome"), c("vitre_bleue"), 0.15)     # verre teinté bleu : l'intérieur se lit au travers
VERRE_DOME_CLAIR = mix(c("verre_dome"), c("vitre_reflet"), 0.5)


def _profil_dome(R, y_mur, hauteur):
    Rd = R - 0.6
    Hd = hauteur - y_mur - 1.9
    return [(Rd * math.cos(math.radians(p)), y_mur + Hd * math.sin(math.radians(p))) for p in DOME_PHI]


def _sous_dome(R, y_mur, hauteur, r, marge=1.5):
    """Hauteur libre sous le verre à la distance r du centre (pour garder l'intérieur sous la coupole)."""
    prof = _profil_dome(R, y_mur, hauteur)
    if r >= prof[0][0] - 0.8:
        return y_mur - marge
    for (r0, y0), (r1, y1) in zip(prof, prof[1:]):
        if r1 <= r <= r0:
            return y0 + (y1 - y0) * (r0 - r) / (r0 - r1) - marge
    return prof[-1][1] - marge


def _arbre_rond(b, x, z, rng, s=1.0, y0=0.4):
    """Arbre en blocs (style stud) : tronc, houppier droit, houppier tourné à 45°, cime (4 pièces)."""
    b.box((x - 0.5 * s, y0, z - 0.5 * s), (x + 0.5 * s, y0 + 4.2 * s, z + 0.5 * s), c("tronc"), name="Tronc")
    b.boxc((x, y0 + 5.6 * s, z), (6.0 * s, 3.2 * s, 6.0 * s), vary("feuille", rng, 0.04), studs="top", name="Feuillage")
    b.boxc((x, y0 + 7.0 * s, z), (5.0 * s, 3.0 * s, 5.0 * s), vary("feuille_claire", rng, 0.04), yaw=45, studs="top",
           collide=False, name="Feuillage")
    b.boxc((x, y0 + 9.0 * s, z), (3.0 * s, 1.6 * s, 3.0 * s), vary("feuille_pale", rng, 0.04), studs="top",
           collide=False, name="Feuillage")


def _montagne(b, rng, cx, cz):
    """Montagne rocheuse artificielle : strates de masses tournées (sombre en bas, claire en haut), deux pics,
    éperons basculés pour une silhouette déchiquetée, corniches herbeuses et buissons, cascade vers l'étang,
    sentier en marches."""
    # roches chaudes (référence 3) : base terre cuite, milieu ocre, sommet sable ; échelle 1,2 (1,15 en hauteur)
    tons = {"F": (178, 96, 66), "R": (204, 138, 78), "C": (222, 178, 116), "S": (236, 214, 168)}
    K, KY = 1.2, 1.15
    # (dx, y0, dz, sx, h, sz, yaw, ton)
    masses = [
        (0, 0, 0, 32, 5, 22, 8, "F"), (11, 0, 7, 16, 4.5, 14, -14, "F"), (-12, 0, -4, 14, 4, 13, 22, "F"),
        (-3, 0, 9, 18, 4.75, 10, -30, "R"),
        (1, 5, 2, 23, 6, 15, -6, "R"), (10, 4.5, 6, 12, 6, 10, 18, "R"), (-10, 4, -4, 10, 5.5, 9, -20, "C"),
        (-7, 4.5, 8, 11, 7, 8, 35, "F"),
        (-1, 11, 3, 16, 6, 11, 12, "C"), (8, 10.5, 7, 9, 7, 8, -25, "R"), (-7, 9.5, 0, 7, 5, 7, 30, "R"),
        (-2, 17, 3, 11, 6, 8, -10, "R"), (9, 17.5, 8, 6, 5, 5, 20, "C"), (9.5, 22.5, 8.5, 3.5, 3, 3.5, 35, "S"),
        (-2.5, 23, 3, 7, 5, 6, 25, "C"), (-3, 28, 3, 4.4, 3.2, 4, 40, "S"), (-3.2, 31.2, 3.3, 2.2, 1.8, 2.2, 10, "S"),
    ]
    with b.group("Montagne"):
        for (dx, y0, dz, sx, h, sz, yaw, t) in masses:
            b.boxc((cx + K * dx, KY * (y0 + h / 2), cz + K * dz), (K * sx, KY * h, K * sz), vary(tons[t], rng, 0.04),
                   yaw=yaw, studs="top", name="Roche")
        # éperons basculés (silhouette déchiquetée)
        for (dx, y, dz, sx, h, sz, yaw, tilt, t) in ((12.5, 8.0, -3.0, 5, 12, 4, -20, 18, "R"),
                                                     (-14.5, 7.0, 6.0, 4, 11, 4, 40, -16, "C"),
                                                     (4.5, 21.0, -1.0, 3, 8, 3, 15, 14, "C"),
                                                     (-9.0, 15.0, 6.0, 3.5, 8, 3, -35, -12, "R")):
            _dalle_penchee(b, (cx + K * dx, KY * y, cz + K * dz), (K * sx, KY * h, K * sz), yaw, tilt,
                           vary(tons[t], rng, 0.04), name="Eperon")
        # corniches herbeuses et buissons
        for (dx, y, dz, sx, sz, yaw) in ((-10, 5.0, -8.2, 7, 4, 22), (11, 10.5, 2, 6, 4, -25),
                                         (-7, 15.0, -3.5, 5, 3, 30),
                                         (6, 17.0, 1.5, 4, 3, -10)):
            yc = KY * y + 0.45
            b.boxc((cx + K * dx, yc, cz + K * dz), (K * sx, 0.6, K * sz), vary("herbe_claire", rng, 0.04), yaw=yaw,
                   studs="top", name="Corniche")
            if sx >= 5:     # petit arbre en blocs sur les grandes corniches
                _arbre_rond(b, cx + K * dx, cz + K * dz, rng, 0.45, y0=yc + 0.3)
        for (dx, y, dz, r) in ((-11, 5.6, -9, 1.5), (12, 11.2, 1.2, 1.3), (-6, 15.8, -4, 1.1), (14, 0.4, -6, 1.8),
                               (-16, 0.4, -9, 1.6)):
            b.ball((cx + K * dx, KY * y + 0.45 + r * 0.6, cz + K * dz), K * r, tirer(["feuille", "feuille_claire", "feuille_fonce"], rng),
                   collide=False, name="Buisson")
        # cascade vers l'étang (face avant, -Z)
        b.box((cx - 6.6 * K, 0.4, cz - 11.6 * K), (cx - 4.4 * K, 12.0 * KY, cz - 10.9 * K), c("eau"), material="Glass", transparency=0.15,
              collide=False, name="Cascade")
        b.box((cx - 6.2 * K, 0.4, cz - 11.9 * K - 0.1), (cx - 4.8 * K, 8.5 * KY, cz - 11.5 * K), c("vitre_reflet"), collide=False, shadow=False,
              name="Cascade")
        # sentier en marches vers une corniche
        for k in range(5):
            b.boxc((cx + K * (13 - k * 1.6), 0.4 + 1.1 * (k + 1) - 0.55, cz + K * (-7 + k * 1.4)), (3.0, 1.1, 2.2),
                   c("dalle_claire"), yaw=-35, studs="top", name="Marche")


def _mini_ville(b, rng, x0, z0):
    """Petit îlot de ville d'entraînement dans le parc (trois immeubles cubiques, un toit plat chacun)."""
    with b.group("MiniVille"):
        for (dx, dz, w, d, h, corps) in ((0, 0, 7, 6, 9, "facade_creme"), (8.5, 1, 6, 7, 13, "beton_clair"),
                                         (3.5, 9, 9, 6, 6, "facade_rose")):
            x, z = x0 + dx, z0 + dz
            b.box((x - w / 2, 0.4, z - d / 2), (x + w / 2, h, z + d / 2), vary(corps, rng, 0.03), name="Immeuble")
            b.box((x - w / 2 - 0.2, h, z - d / 2 - 0.2), (x + w / 2 + 0.2, h + 0.5, z + d / 2 + 0.2), c("blanc"),
                  studs="top", name="Toit")
            yy = 2.2
            while yy + 1.4 < h - 0.8:
                b.box((x - w / 2 - 0.1, yy, z - d / 2 - 0.1), (x + w / 2 + 0.1, yy + 1.4, z + d / 2 + 0.1),
                      c("vitre_bleue_fonce"), name="Fenetres")
                yy += 3.4


def _dome_rouge(b, rng, x, z, r=11.0, porte_vers=(0.0, 0.0)):
    """Bâtiment en dôme rouge : demi-sphère en cylindres empilés, bandeau blanc, porte ronde cerclée de blanc."""
    with b.group("DomeRouge"):
        k_ = r / 11.0
        couches = [(0.4, 3.0 * k_, 1.0), (3.0 * k_, 5.4 * k_, 0.96), (5.4 * k_, 7.4 * k_, 0.87),
                   (7.4 * k_, 8.9 * k_, 0.74), (8.9 * k_, 9.9 * k_, 0.58), (9.9 * k_, 10.6 * k_, 0.40)]
        for k, (ya, yb, f) in enumerate(couches):
            b.cyl((x, (ya + yb) / 2, z), r * f, yb - ya, vary("rouge_dome", rng, 0.03) if k % 2 else c("rouge_dome"),
                  studs="top", name="Coque")
        b.cyl((x, 3.0 * k_ + 0.15, z), r * 1.0 + 0.15, 0.5, c("blanc"), collide=False, name="Bandeau")
        b.cyl((x, 10.6 * k_ + 0.3, z), r * 0.22, 0.6, c("blanc"), name="Lanterneau")
        b.cyl((x, 10.6 * k_ + 0.75, z), r * 0.12, 0.3, c("neon_cyan"), material="Neon", collide=False, shadow=False, name="Feu")
        d = _unit(np.array([porte_vers[0] - x, 0.0, porte_vers[1] - z]))
        up = np.array([0.0, 1.0, 0.0])
        for (rr, ep, coul, saillie) in ((3.4, 0.8, "blanc", 0.35), (2.7, 0.8, "rouge_fonce", 0.5)):
            ctr = np.array([x, 3.4, z]) + d * (r - 0.2 + saillie)
            _piece(b, "cyl", (ep, 2 * rr, 2 * rr), ctr, d, up, coul, name="Porte")
        ctr = np.array([x, 1.9, z]) + d * (r + 0.6)
        _piece(b, "block", (1.6, 3.0, 4.2), ctr, d, up, "vitre_nuit", name="Porte")


def dome_entrainement(b, variant=0, rayon=52.0, hauteur=50.0):
    """Parc d'entraînement sous dôme de verre (voir l'en-tête du module). Entrée vers -Z local."""
    rng = b.rng
    R = float(rayon)
    y_mur = 6.0
    n = DOME_N
    da = 360.0 / n
    prof = _profil_dome(R, y_mur, hauteur)

    def pt(r, y, th):
        t = math.radians(th)
        return np.array([r * math.sin(t), y, r * math.cos(t)])

    def tang(th):
        t = math.radians(th)
        return np.array([math.cos(t), 0.0, -math.sin(t)])

    # méridiens aux angles 180 + k·15 : l'entrée (-Z) est centrée entre les méridiens k = 23 et k = 1
    thetas = [180.0 + k * da for k in range(n)]
    ouverture = {0, n - 1}                    # panneaux k (entre θk et θk+1) ouverts dans l'anneau du bas

    with b.group("Dome"):
        # --- anneau de base (mur blanc, ligne néon, couvertine) ---------------------------------
        with b.group("Anneau"):
            for k in range(n):
                if k in ouverture:
                    continue
                th = thetas[k] + da / 2
                L = 2 * R * math.sin(math.radians(da / 2)) + 0.25
                ctr = pt((R - 0.75) * math.cos(math.radians(da / 2)), y_mur / 2, th)
                b.boxc(tuple(ctr), (L, y_mur, 1.5), vary("blanc_casse", rng, 0.02), yaw=th, name="Mur")
                ctr = pt((R - 0.75) * math.cos(math.radians(da / 2)) + 0.85, 4.2, th)
                b.boxc(tuple(ctr), (L - 0.6, 0.35, 0.3), c("neon_cyan"), yaw=th, material="Neon", collide=False,
                       shadow=False, name="Neon")
                ctr = pt((R - 0.75) * math.cos(math.radians(da / 2)) + 0.85, 1.2, th)
                b.boxc(tuple(ctr), (L - 0.6, 1.0, 0.3), c("beton"), yaw=th, collide=False, name="Plinthe")
                ctr = pt((R - 0.75) * math.cos(math.radians(da / 2)), y_mur + 0.3, th)
                b.boxc(tuple(ctr), (L + 0.2, 0.6, 2.1), c("blanc"), yaw=th, studs="top", name="Couvertine")
        # --- coupole : panneaux de verre, méridiens, cerces ---------------------------------------
        with b.group("Coupole"):
            for i in range(len(prof) - 1):
                (r0, y0), (r1, y1) = prof[i], prof[i + 1]
                cd = math.cos(math.radians(da / 2))
                sd = math.sin(math.radians(da / 2))
                for k in range(n):
                    th = thetas[k]
                    thc = th + da / 2
                    # panneau
                    if not (i == 0 and k in ouverture):
                        B0 = pt(r0 * cd, y0, thc)
                        T0 = pt(r1 * cd, y1, thc)
                        X = tang(thc)
                        Y = _unit(T0 - B0)
                        w = (r0 + r1) * sd
                        clair = (k + 2 * i) % 7 == 0 or (k + 2 * i) % 7 == 3
                        _piece(b, "block", (w, float(np.linalg.norm(T0 - B0)), 0.3), (B0 + T0) / 2, X, Y,
                               VERRE_DOME_CLAIR if clair else VERRE_DOME, material="Glass",
                               transparency=0.55 if clair else 0.65, collide=False, shadow=False, name="Verre")
                    # méridien (le long de l'arête θk)
                    if not (i == 0 and k in (0, 1, n - 1)):
                        V0, V1 = pt(r0, y0, th), pt(r1, y1, th)
                        X = tang(th)
                        Y = _unit(V1 - V0)
                        Z = np.cross(X, Y)
                        maitre = k % 2 == 0
                        wm, dm = (1.6, 1.2) if maitre else (1.1, 0.8)
                        _piece(b, "block", (wm, float(np.linalg.norm(V1 - V0)) + 0.6, dm), (V0 + V1) / 2 + Z * 0.3,
                               X, Y, "blanc" if maitre else "cadre_blanc", collide=False, name="Meridien")
                    # cerce au sommet de l'anneau
                    ctr = pt(r1 * cd, y1, thc)
                    ep = 1.4 if i == len(prof) - 2 else 0.9
                    b.boxc(tuple(ctr + np.array([0, 0, 0])), (2 * r1 * sd + 0.4, ep, ep), c("blanc"), yaw=thc,
                           collide=False, name="Cerce")
            # lanterneau sommital
            r_top, y_top = prof[-1]
            b.cyl((0, y_top + 0.3, 0), r_top + 0.6, 1.2, c("blanc"), studs="top", name="Oculus")
            b.cyl((0, y_top + 1.4, 0), r_top * 0.55, 1.0, c("verre_dome"), material="Glass", transparency=0.3,
                  name="Lanterneau")
            b.cyl((0, y_top + 1.0, 0), r_top * 0.55 + 0.15, 0.25, c("neon_cyan"), material="Neon", collide=False,
                  shadow=False, name="Neon")
            b.cyl((0, y_top + 2.05, 0), r_top * 0.55 + 0.4, 0.3, c("blanc"), studs="top", name="Chapeau")
        # --- entrée (-Z) ----------------------------------------------------------------------
        with b.group("Entree"):
            r1, y1 = prof[1]
            for s in (-1, 1):
                V = pt(R - 0.75, 0, 180 + s * da)
                b.boxc((V[0], (y1 + 0.5) / 2, V[2]), (1.8, y1 + 0.5, 1.8), c("blanc"), yaw=s * da, name="Montant")
            zf = -R * math.cos(math.radians(da)) - 0.2          # face de l'ouverture (≈ -50,4)
            za = -R - 5.0                                       # avant de l'auvent (-57)
            b.box((-12, 12.4, za), (12, 13.0, zf + 1.0), c("blanc"), studs="top", name="Auvent")
            p = b.box((-12, 11.6, za - 0.4), (12, 13.4, za), c("blanc"), name="Bandeau")
            _label(p, "ENTRAÎNEMENT", face="Front", couleur=c("violet"), fond=c("blanc"))
            _neon(b, (-11.8, 11.4, za - 0.4), (11.8, 11.6, za + 0.1))
            for s in (-1, 1):
                xa, xb = sorted((s * 12.0, s * 12.25))
                _neon(b, (xa, 12.5, za), (xb, 12.8, zf + 1.0))
                b.cyl((s * 10.5, 6.2, za + 1.0), 0.35, 12.4, c("blanc"), name="Poteau")
            b.wedge((-11, 0, za + 0.2), (11, 0.45, zf + 0.6), c("dalle_claire"), down="-z", studs="top", name="Rampe")
            b.box((-13, 0, zf + 0.6), (13, 0.45, zf + 3.6), c("dalle_claire"), studs="top", name="Seuil")
        # --- intérieur --------------------------------------------------------------------------
        with b.group("Interieur"):
            ri = R - 1.7
            for zc in range(-46, 47, 8):
                zo = max(abs(zc - 4), abs(zc + 4))
                if zo >= ri:
                    continue
                hw = math.floor(math.sqrt(ri * ri - zo * zo))
                b.box((-hw, 0, zc - 4), (hw, 0.4, zc + 4), vary("herbe_claire", rng, 0.03), studs="top", name="Pelouse")
            # allées et place centrale
            b.box((-3, 0.4, zf + 3.6), (3, 0.55, -10), c("dalle_claire"), studs="top", name="Allee")
            b.boxc((14.5, 0.475, 2.5), (22, 0.15, 5), c("dalle_claire"), yaw=-38, studs="top", name="Allee")
            b.boxc((-9.5, 0.475, 9.5), (18, 0.15, 5), c("dalle_claire"), yaw=40, studs="top", name="Allee")
            b.boxc((-20, 0.475, -10), (18, 0.15, 4), c("dalle_claire"), yaw=-28, studs="top", name="Allee")
            b.boxc((17, 0.475, -16), (20, 0.15, 4), c("dalle_claire"), yaw=40, studs="top", name="Allee")
            b.cyl((0, 0.5, -2), 10.0, 0.2, c("dalle_claire"), studs="top", name="Place")
            b.cyl((0, 0.65, -2), 7.0, 0.1, c("neon_cyan"), material="Neon", collide=False, shadow=False, name="Anneau")
            b.cyl((0, 0.675, -2), 6.4, 0.15, c("blanc_casse"), studs="top", name="Place")
            b.cyl((0, 1.15, -2), 3.0, 0.9, c("blanc"), name="Vasque")
            b.cyl((0, 1.2, -2), 2.5, 1.05, c("eau"), name="Eau")
            b.cyl((0, 2.6, -2), 0.4, 2.8, c("vitre_reflet"), material="Neon", collide=False, shadow=False, name="Jet")
            # étang au pied de la cascade
            b.cyl((-22, 0.5, 9), 8.0, 0.2, c("eau"), name="Etang")
            b.cyl((-22, 0.45, 9), 8.6, 0.12, c("gravier"), name="Rive")
            for (dx, dz, s_) in ((-7.5, 4, 1.4), (6.5, -5, 1.1), (-3, -8, 1.0), (8, 3, 1.3)):
                b.boxc((-22 + dx, 0.4 + s_ / 2, 9 + dz), (s_ * 1.6, s_, s_ * 1.3), vary("roche_claire", rng, 0.05),
                       yaw=float(rng.uniform(0, 90)), studs="top", name="Galet")
            _montagne(b, rng, -6.0, 22.0)
            _dome_rouge(b, rng, 26.0, -14.0, r=15.0, porte_vers=(0.0, -2.0))
            _mini_ville(b, rng, 24.0, 14.0)
            for (x, z, s_) in ((-36, -16, 1.0), (-26, -32, 0.9), (4, -33, 0.8), (-41, 4, 0.85), (-12, -40, 0.75),
                               (-36, 22, 0.8)):
                _arbre_rond(b, x, z, rng, s_)
    return {"emprise": (2 * R + 1, 2 * R + 5.4), "hauteur": hauteur + 0.6}


# ---------------------------------------------------------------------------
# 3. Ville factice : immeubles d'entraînement et décombres
# ---------------------------------------------------------------------------

STYLES_FACTICES = [
    # (corps, bandeaux d'étage, vitrage, style de fenêtres)
    ("facade_rose", "robot_orange", "vitre_nuit", "bandes"),
    ("facade_ciel", "blanc", "acier_fonce", "rubans"),
    ("facade_creme", "violet", "vitre_bleue_fonce", "colonnes"),
]
ETAGE = 4.0


def _ferraille(b, x, y, z, rng, n=3, long=1.6):
    """Fers à béton tordus qui dépassent d'une cassure (fins cylindres d'acier, sans collision)."""
    for _ in range(n):
        dx, dz = float(rng.uniform(-1.2, 1.2)), float(rng.uniform(-1.2, 1.2))
        a = np.array([x + dx, y - 0.2, z + dz])
        bb = a + np.array([float(rng.uniform(-0.6, 0.6)), long * float(rng.uniform(0.7, 1.1)),
                           float(rng.uniform(-0.6, 0.6))])
        _segment(b, a, bb, 0.09, c("acier_fonce"), name="Ferraille")


def _gravats(b, cx, cz, rng, n=4, taille=1.6, couleurs=("beton", "beton_fonce", "beton_clair")):
    """Quelques blocs de gravats posés au sol (légèrement enfoncés), tournés au hasard."""
    for _ in range(n):
        s = taille * float(rng.uniform(0.6, 1.2))
        x = cx + float(rng.uniform(-2.0, 2.0))
        z = cz + float(rng.uniform(-1.5, 1.5))
        b.boxc((x, s * 0.4, z), (s * 1.3, s * 0.9, s), vary(couleurs[int(rng.integers(len(couleurs)))], rng, 0.05),
               yaw=float(rng.uniform(0, 90)), studs="top", name="Gravat")


def _dalle_penchee(b, ctr, taille, yaw, tilt, couleur, **kw):
    """Dalle inclinée : tournée de `yaw` autour de Y puis basculée de `tilt` degrés autour de son X local."""
    ty, tt = math.radians(yaw), math.radians(tilt)
    X = np.array([math.cos(ty), 0.0, -math.sin(ty)])
    Zh = np.array([math.sin(ty), 0.0, math.cos(ty)])
    Y = np.array([0.0, math.cos(tt), 0.0]) - Zh * math.sin(tt)
    return _piece(b, "block", taille, ctr, X, Y, couleur, **kw)


def _trou(b, x0, x1, y0, y1, zf, sens, rng):
    """Brèche sombre aux bords irréguliers (deux blocs décalés) sur une face d'axe Z (zf, normale `sens`)."""
    za, zb = sorted((zf, zf + sens * 0.22))
    zs_, zt_ = sorted((zf, zf + sens * 0.1))
    w, h = x1 - x0, y1 - y0
    b.box((x0 - 0.7, y0 - 0.6, zs_), (x1 + 0.6, y1 + 0.7, zt_), c("gris_acier"), name="Brulure")
    b.box((x0, y0, za), (x1, y1, zb), c("noir"), name="Breche")
    dx = w * float(rng.uniform(0.25, 0.45))
    if rng.uniform() < 0.5:
        b.box((x0 + dx, y1, za), (x1 - w * 0.1, y1 + h * 0.35, zb), c("noir"), name="Breche")
    else:
        b.box((x0 - w * 0.25, y0 + h * 0.2, za), (x0, y1 - h * 0.25, zb), c("noir"), name="Breche")


def _cassure(b, bloc, corps, rng, cote_haut=-1):
    """Haut d'un volume cassé : pans de mur déchiquetés (coins) sur la façade avant et un flanc, dalle de plancher
    à nu, fers à béton."""
    x0, x1, z0, z1, hb = bloc[:5]
    w = x1 - x0
    h1 = min(3.2, 0.9 + w * 0.25)
    # pan de façade avant : haut côté `cote_haut`, la cassure descend en biais
    if cote_haut < 0:
        b.wedge((x0, hb, z0), (x0 + w * 0.6, hb + h1, z0 + 0.8), corps, down="+x", name="Pan")
    else:
        b.wedge((x1 - w * 0.6, hb, z0), (x1, hb + h1, z0 + 0.8), corps, down="-x", name="Pan")
    # pan du flanc opposé, vers l'arrière
    xf = x1 if cote_haut < 0 else x0
    xa, xb = sorted((xf, xf - (0.8 if cote_haut < 0 else -0.8)))
    b.wedge((xa, hb, z1 - (z1 - z0) * 0.55), (xb, hb + h1 * 0.8, z1), corps, down="-z", name="Pan")
    b.box((x0 + 0.8, hb - 0.3, z0 + 1.0), (x1 - 0.8, hb + 0.25, z1 - 0.8), c("beton_fonce"), studs="top",
          name="DalleNue")
    _ferraille(b, (x0 + x1) / 2, hb + 0.25, (z0 + z1) / 2, rng, n=2)


def immeuble_factice(b, variant=0, largeur=20.0, profondeur=20.0, hauteur=26.0, degats=0):
    """Immeuble d'entraînement de la ville factice (béton nu, fenêtres sombres, citerne sur le toit).
    degats 0 intact ; 1 angle avant droit grignoté en gradins (pans déchiquetés, dalles et fers à nu, brèche,
    gravats au pied) ; 2 très endommagé : étages hauts effondrés, silhouette en dents de scie, murs percés,
    citerne tombée, gros tas de gravats. Les variantes changent les couleurs et le style des fenêtres.
    Avant = -Z local ; tout reste dans l'emprise largeur × profondeur."""
    rng = b.rng
    corps_nom, bande, vitre, style = STYLES_FACTICES[variant % 3]
    W, D, H = float(largeur), float(profondeur), float(hauteur)
    w, d = W / 2 - 0.4, D / 2 - 0.4           # corps en retrait de 0,4 : bandeaux et fenêtres restent dans l'emprise
    df = D / 2 - 1.4                          # façade avant plus en retrait : la marquise reste dans l'emprise
    # volumes (x0, x1, z0, z1, haut, cassé)
    if degats == 0:
        blocs = [(-w, w, -df, d, H, False)]
    elif degats == 1:
        # toute la moitié haute arrachée sur la moitié de la largeur (lisible de loin)
        h1 = max(ETAGE * 2, math.floor(H / 2 / ETAGE) * ETAGE + 1.0)
        blocs = [(-w, 0.0, -df, d, H, False), (0.0, w, -df, d, h1, True)]
    else:
        fr = (0.62, 0.9, 0.45)
        xs_ = np.linspace(-w, w, 4)
        blocs = []
        for k in range(3):
            hk = max(ETAGE + 2, math.floor(H * fr[k] / 2) * 2)
            zf = -df + (1.6 if k == 1 else 0.0)
            blocs.append((float(xs_[k]), float(xs_[k + 1]), zf, d, hk, True))
    corps = vary(corps_nom, rng, 0.03)
    h_min = min(bl[4] for bl in blocs)
    with b.group("ImmeubleFactice"):
        b.box((-w - 0.2, 0, -df - 0.2), (w + 0.2, 0.6, d + 0.2), c("beton_fonce"), studs="top", name="Socle")
        for (x0, x1, z0, z1, hb, casse) in blocs:
            b.box((x0, 0.6, z0), (x1, hb, z1), corps, name="Corps")
            if not casse:
                b.box((x0 - 0.3, hb, z0 - 0.3), (x1 + 0.3, hb + 0.5, z1 + 0.3), c(bande), studs="top", name="Acrotere")
        # bandeaux d'étage : anneaux communs sous le plus bas des volumes, puis anneaux du seul volume intact
        y = ETAGE
        while y < H - 1:
            haut = [bl for bl in blocs if bl[4] > y + 1.0]
            if len(haut) == len(blocs):
                z0 = min(bl[2] for bl in blocs)
                b.box((-w - 0.2, y - 0.25, z0 - 0.2), (w + 0.2, y + 0.25, d + 0.2), c(bande), name="Bandeau")
            elif degats == 1:
                for (bx0, bx1, bz0, bz1, hb, casse) in haut:
                    if not casse:
                        b.box((bx0 - 0.2, y - 0.25, bz0 - 0.2), (bx1 + 0.2, y + 0.25, bz1 + 0.2), c(bande),
                              name="Bandeau")
            y += ETAGE
        # fenêtres : bandes verticales (face avant et flancs extérieurs) ou rubans filants
        for (x0, x1, z0, z1, hb, casse) in blocs:
            ya, yb = 1.6, hb - (0.6 if casse else 1.2)
            if style == "rubans":
                yy = 1.8
                while yy + 1.6 < hb - 0.6:
                    b.box((x0 - 0.12, yy, z0 - 0.12), (x1 + 0.12, yy + 1.6, z1 + 0.12), c(vitre), name="Fenetres")
                    yy += ETAGE * (2 if degats else 1)
                continue
            n_col = max(1, int((x1 - x0) // (5.5 if style == "bandes" else 7.0)))
            if degats == 2:
                n_col = 1
            pas = (x1 - x0) / n_col
            lw = 2.2 if style == "bandes" else 3.4
            for k in range(n_col):
                xc = x0 + pas * (k + 0.5)
                b.box((xc - lw / 2, ya, z0 - 0.12), (xc + lw / 2, yb, z0), c(vitre), name="Fenetres")
            zc = (z0 + z1) / 2
            for xf, sgn in ((x0, -1), (x1, 1)):
                if abs(abs(xf) - w) > 0.01:
                    continue          # flanc intérieur, collé à un autre volume
                xa_, xb_ = sorted((xf, xf + sgn * 0.12))
                b.box((xa_, ya, zc - lw / 2), (xb_, yb, zc + lw / 2), c(vitre), name="Fenetres")
        # porte d'entrée sur la face avant du premier volume
        x0, x1, z0 = blocs[0][0], blocs[0][1], blocs[0][2]
        xc = (x0 + x1) / 2
        b.box((xc - 1.6, 0.6, z0 - 0.15), (xc + 1.6, 3.6, z0), c("acier_fonce"), name="Porte")
        b.box((xc - 2.2, 3.6, z0 - 0.9), (xc + 2.2, 4.0, z0), c(bande), studs="top", name="Marquise")
        # citerne sur le toit du volume intact le plus haut, ou tombée au pied
        intacts = [bl for bl in blocs if not bl[5]]
        if intacts:
            top = intacts[0]
            hb = top[4]
            tx, tz = (top[0] + top[1]) / 2 - (top[1] - top[0]) * 0.15, (top[2] + top[3]) / 2 + 1.0
            for sx in (-1, 1):
                b.box((tx + sx * 1.3 - 0.25, hb + 0.5, tz - 1.5), (tx + sx * 1.3 + 0.25, hb + 2.0, tz + 1.5),
                      c("acier_fonce"), name="Pied")
            b.cyl((tx, hb + 3.6, tz), 1.9, 3.2, c("cible_blanc") if variant % 2 else c("robot_gris"), studs="top",
                  name="Citerne")
            b.cyl((tx, hb + 5.4, tz), 1.2, 0.4, c("acier"), name="Couvercle")
        else:
            _piece(b, "cyl", (3.2, 3.6, 3.6), (w - 2.6, 1.75 + 0.6, -df + 2.6), (0.8, 0.0, -0.6), (0, 1, 0),
                   "robot_gris", name="Citerne")
        # repères d'entraînement : cible ronde sur l'acrotère avant (intact), ruban de danger au pied (endommagé)
        if degats == 0:
            x0, x1, z0, _, hb, _ = blocs[0]
            xc = x0 + (x1 - x0) * (0.3 if variant % 2 else 0.7)
            b.box((xc - 0.3, hb + 0.5, z0 + 0.4), (xc + 0.3, hb + 2.6, z0 + 1.0), c("acier_fonce"), name="Support")
            for k, (r, coul) in enumerate(((2.3, "cible_rouge"), (1.6, "cible_blanc"), (0.8, "cible_rouge"))):
                avant, arriere = z0 + 0.1 - 0.12 * k, z0 + 0.4 - 0.04 * k
                b.cyl((xc, hb + 3.0, (avant + arriere) / 2), r, arriere - avant, c(coul), axis="z", collide=False,
                      name="Cible")
        else:
            b.box((-w - 0.15, 0.6, -df - 0.15), (w + 0.15, 1.1, d + 0.15), c("danger_jaune"), collide=False,
                  name="Ruban")
        # dégâts
        casses = [bl for bl in blocs if bl[5]]
        for k, bl in enumerate(casses):
            _cassure(b, bl, corps, rng, cote_haut=-1 if k % 2 == 0 else 1)
        if degats == 1:
            x0, x1, z0, z1, hb, _ = blocs[0]
            _trou(b, x1 - 5.0, x1 - 1.6, hb - 9.0, hb - 6.0, z0, -1, rng)
            _gravats(b, w * 0.5, -df + 1.0, rng, n=4, taille=1.8)
            # taches de brûlure noires autour des brèches (saillie 0,15)
            for (xa_, xb_, ya_, yb_) in ((x0 + 1.5, x0 + 5.5, hb - 5.0, hb - 2.0), (x1 - 4.0, x1 - 0.5, 2.0, 5.5),
                                         (w * 0.3, w * 0.75, blocs[1][4] - 3.5, blocs[1][4] - 1.0)):
                b.box((xa_, ya_, z0 - 0.15), (xb_, yb_, z0), c("noir"), collide=False, name="Brulure")
        elif degats == 2:
            for (x0, x1, z0, z1, hb, _) in blocs[:2]:
                if hb > 9:
                    xm = (x0 + x1) / 2
                    _trou(b, xm - 1.2, xm + 1.8, hb - 5.5, hb - 2.6, z0, -1, rng)
            b.wedge((-w * 0.6, 0.6, -d - 2.0), (w * 0.9, 5.0, -df + 3.0), c("beton_fonce"), down="-z", studs="top",
                    name="Tas")
            _gravats(b, w * 0.05, -df - 1.0, rng, n=5, taille=2.0)
            # grand pan de façade basculé contre le volume (≈ 8 × 12 × 1, à 30°)
            tt = math.radians(30)
            ctr = (-w * 0.55, 6.0 * math.cos(tt) + 0.3, -df - 0.6 - 6.0 * math.sin(tt))
            _dalle_penchee(b, ctr, (8.0, 12.0, 1.0), 0, -30, vary(corps_nom, rng, 0.03), name="PanBascule")
    return {"emprise": (W, D), "hauteur": max(bl[4] for bl in blocs) + (5.6 if degats < 2 else 3.2)}


def decombres(b, variant=0):
    """Tas de gravats (≈ 10 × 10, hauteur ≤ 3,5) : butte basse, dalles basculées, poutre cassée, blocs.
    Tout repose au sol (pièces légèrement enfoncées). 3 variantes."""
    rng = b.rng
    v = variant % 3
    tons = (("beton", "gris_acier", "beton_clair"), ("facade_creme", "beton_fonce", "facade_rose"),
            ("beton_clair", "acier_fonce", "beton"))[v]
    with b.group("Decombres"):
        # butte : deux coins dos à dos
        b.wedge((-3.2, 0, -2.6), (3.0, 1.3, 0.2), c(tons[1]), down="-z", studs="top", name="Butte")
        b.wedge((-3.2, 0, 0.2), (3.0, 1.3, 2.8), c(tons[1]), down="+z", studs="top", name="Butte")
        # dalles basculées appuyées sur la butte
        for (x, z, sx, sz, yaw, tilt, t) in ((-1.0, -1.2, 4.6, 3.6, 18 + 30 * v, 22, 0),
                                             (2.4, 1.6, 3.8, 3.0, -40, -26, 2),
                                             (-2.8, 2.0, 3.2, 2.6, 70, 18, 0)):
            ep = 0.6
            tt = math.radians(abs(tilt))
            yc = (ep / 2) * math.cos(tt) + (sz / 2) * math.sin(tt) - 0.15
            _dalle_penchee(b, (x, yc, z), (sx, ep, sz), yaw, tilt, vary(tons[t], rng, 0.05), studs="top", name="Dalle")
        # poutre cassée en travers
        a = math.radians(25 + 40 * v)
        L = 6.5
        p0 = np.array([-L / 2 * math.cos(a), 0.35, L / 2 * math.sin(a)])
        p1 = np.array([L / 2 * math.cos(a), 1.6, -L / 2 * math.sin(a)])
        dd = p1 - p0
        rouille = mix(c("bois_fonce"), c("rouge_fonce"), 0.35)
        _piece(b, "block", (float(np.linalg.norm(dd)), 0.7, 0.7), (p0 + p1) / 2, dd, (0, 1, 0),
               rouille if v != 1 else c("acier_fonce"), name="Poutre")
        _segment(b, p1, p1 + np.array([0.3, 1.1, -0.2]), 0.08, c("acier_fonce"), name="Ferraille")
        _segment(b, p1, p1 + np.array([-0.2, 0.9, 0.4]), 0.08, c("acier_fonce"), name="Ferraille")
        # blocs épars
        for (x, z, s) in ((3.6, -2.6, 1.2), (-3.9, -1.6, 0.9), (0.6, 3.8, 1.0), (4.0, 2.8, 0.8), (-0.6, -3.9, 0.7)):
            b.boxc((x, s * 0.42, z), (s * 1.4, s, s * 1.1), vary(tons[int(rng.integers(3))], rng, 0.05),
                   yaw=float(rng.uniform(0, 90)), studs="top", name="Bloc")
    return {"emprise": (10.0, 10.0), "hauteur": 3.2}


# ---------------------------------------------------------------------------
# 4. Robots d'entraînement (dessins originaux) et cibles
# ---------------------------------------------------------------------------

def _oeil(b, x, y, z, r=0.55, cadre="blanc"):
    """Œil rond unique (lentille Neon) dans un cerclage, tourné vers -Z."""
    b.cyl((x, y, z - 0.15), r + 0.25, 0.3, c(cadre), axis="z", name="Cerclage")
    b.cyl((x, y, z - 0.35), r, 0.3, c("lentille"), axis="z", material="Neon", collide=False, shadow=False,
          name="Lentille")


def _antenne(b, x, y, z, h=1.6):
    b.cyl((x, y + h / 2, z), 0.09, h, c("acier_fonce"), collide=False, name="Antenne")
    b.ball((x, y + h + 0.2, z), 0.28, c("lentille"), material="Neon", collide=False, shadow=False, name="Balise")


def robot_entrainement(b, variant=0, taille=1.0):
    """Robot d'entraînement (voir _robot_base) agrandi de `taille` autour de son origine au sol."""
    n0 = len(b.parts)
    info = _robot_base(b, variant)
    if variant % 4 == 3:         # le chenillé posait ses chenilles à y = 0,25 : on le pose au sol
        for p in b.parts[n0:]:
            p.pos = (p.pos[0], p.pos[1] - 0.25, p.pos[2])
    k = float(taille)
    if k != 1.0:
        o = np.asarray(b._t[-1], float)
        for p in b.parts[n0:]:
            p.pos = tuple(float(v) for v in o + k * (np.asarray(p.pos) - o))
            p.size = tuple(float(v) * k for v in p.size)
        info = {"emprise": tuple(v * k for v in info["emprise"]), "hauteur": info["hauteur"] * k}
    return info


def _robot_base(b, variant=0):
    """Robots d'entraînement de dessin original (cubiques, UN œil rond, bandes de danger, aucune marque).
    v0 petit robot à quatre roues (≈ 6) ; v1 marcheur bipède (≈ 12) ; v2 drone posé sur son pylône de recharge
    (≈ 8) ; v3 chenillé lourd à bras de sparring rembourré (≈ 8). L'œil regarde -Z ; emprise ≤ 6 × 6."""
    rng = b.rng
    v = variant % 4
    with b.group("Robot"):
        if v == 0:
            corps = tirer(["robot_orange", "robot_bleu"], rng)
            b.box((-1.9, 0.8, -2.4), (1.9, 2.0, 2.4), c("robot_gris"), name="Chassis")
            for x in (-2.15, 2.15):
                for z in (-1.5, 1.5):
                    b.cyl((x, 1.0, z), 1.0, 0.7, c("pneu"), axis="x", name="Roue")
                    b.cyl((x + (0.4 if x > 0 else -0.4), 1.0, z), 0.45, 0.15, c("acier"), axis="x", collide=False,
                          name="Moyeu")
            b.box((-1.7, 2.0, -1.9), (1.7, 4.6, 2.0), corps, studs="top", name="Corps")
            b.box((-1.8, 2.3, -2.0), (1.8, 2.8, 2.1), c("danger_jaune"), collide=False, name="Bande")
            b.box((-1.8, 2.8, -2.0), (1.8, 3.1, 2.1), c("noir"), collide=False, name="Bande")
            b.box((-1.2, 4.6, -1.5), (1.2, 6.0, 1.3), c("robot_blanc"), studs="top", name="Tete")
            _oeil(b, 0, 5.3, -1.5, r=0.45)
            b.box((-1.9, 0.9, -2.9), (1.9, 1.6, -2.4), c("danger_jaune"), name="ParChoc")
            _antenne(b, 0.8, 6.0, 0.6, 1.4)
            return {"emprise": (5.4, 5.8), "hauteur": 7.6}
        if v == 1:
            corps = tirer(["robot_bleu", "robot_orange"], rng)
            for s in (-1, 1):
                x = s * 1.5
                b.box((x - 1.0, 0, -1.7), (x + 1.0, 0.8, 1.3), c("robot_gris"), studs="top", name="Pied")
                b.box((x - 0.7, 0.8, -0.7), (x + 0.7, 3.6, 0.7), c("robot_blanc"), name="Tibia")
                b.cyl((x, 3.8, 0), 0.75, 1.6, c("robot_gris"), axis="x", name="Genou")
                b.box((x - 0.8, 4.0, -0.8), (x + 0.8, 6.6, 0.8), corps, name="Cuisse")
                b.box((x - 0.85, 2.0, -0.75), (x + 0.85, 2.5, -0.6), c("danger_jaune"), collide=False, name="Bande")
            b.box((-2.0, 6.6, -1.2), (2.0, 7.6, 1.2), c("robot_gris"), name="Bassin")
            b.box((-1.8, 7.6, -1.6), (1.8, 10.6, 1.6), corps, studs="top", name="Torse")
            b.box((-1.6, 8.2, -1.75), (1.6, 8.8, -1.6), c("danger_jaune"), collide=False, name="Bande")
            b.box((-1.6, 8.8, -1.75), (1.6, 9.2, -1.6), c("noir"), collide=False, name="Bande")
            for s in (-1, 1):
                b.cyl((s * 2.2, 10.0, 0), 0.8, 0.8, c("robot_gris"), axis="x", name="Epaule")
                b.box((s * 2.3 - 0.5, 7.2, -0.5), (s * 2.3 + 0.5, 9.8, 0.5), c("robot_blanc"), name="Bras")
                b.box((s * 2.3 - 0.65, 5.8, -0.85), (s * 2.3 + 0.65, 7.2, 0.7), c("robot_orange"), studs="top",
                      name="Poing")
            b.box((-1.2, 10.6, -1.2), (1.2, 12.2, 1.2), c("robot_blanc"), studs="top", name="Tete")
            _oeil(b, 0, 11.4, -1.2, r=0.5)
            _antenne(b, -0.7, 12.2, 0.4, 1.2)
            return {"emprise": (5.9, 3.8), "hauteur": 13.6}
        if v == 2:
            # pylône de recharge
            b.box((-1.6, 0, -1.6), (1.6, 0.6, 1.6), c("beton_fonce"), studs="top", name="Socle")
            b.box((-0.7, 0.6, -0.7), (0.7, 6.4, 0.7), c("robot_gris"), name="Pylone")
            b.box((-0.75, 0.9, -0.75), (0.75, 1.5, 0.75), c("danger_jaune"), collide=False, name="Bande")
            b.box((-0.75, 1.5, -0.75), (0.75, 1.9, 0.75), c("noir"), collide=False, name="Bande")
            b.box((-0.25, 2.4, -0.85), (0.25, 5.8, -0.7), c("neon_cyan"), material="Neon", collide=False,
                  shadow=False, name="Charge")
            b.cyl((0, 6.6, 0), 2.7, 0.4, c("robot_blanc"), studs="top", name="Plateforme")
            b.cyl((0, 6.38, 0), 2.8, 0.14, c("neon_cyan"), material="Neon", collide=False, shadow=False, name="Anneau")
            b.cyl((0, 6.85, 0), 1.9, 0.1, c("danger_jaune"), name="Cible")
            # drone posé sur la plateforme
            for x in (-0.7, 0.7):
                b.box((x - 0.15, 6.9, -1.0), (x + 0.15, 7.2, 1.0), c("acier_fonce"), name="Patin")
            b.box((-0.9, 7.2, -0.9), (0.9, 8.0, 0.9), c("robot_orange"), studs="top", name="Corps")
            for a in (45, -45):
                b.boxc((0, 7.7, 0), (4.4, 0.25, 0.4), c("robot_gris"), yaw=a, collide=False, name="Bras")
            for x in (-1.55, 1.55):
                for z in (-1.55, 1.55):
                    b.cyl((x, 7.95, z), 0.85, 0.12, c("noir"), collide=False, name="Rotor")
                    b.cyl((x, 7.9, z), 0.18, 0.4, c("acier_fonce"), collide=False, name="Moteur")
            _oeil(b, 0, 7.55, -0.9, r=0.25)
            return {"emprise": (5.6, 5.6), "hauteur": 8.1}
        # v3 : chenillé lourd
        for s in (-1, 1):
            x = s * 2.1
            b.box((x - 0.7, 0.25, -2.2), (x + 0.7, 1.95, 2.2), c("pneu"), name="Chenille")
            for z in (-2.1, 2.1):
                b.cyl((x, 1.1, z), 0.85, 1.4, c("pneu"), axis="x", name="Barbotin")
            b.box((x - 0.85, 1.95, -2.4), (x + 0.85, 2.3, 2.4), c("robot_gris"), studs="top", name="GardeBoue")
        b.box((-1.4, 0.8, -2.0), (1.4, 2.6, 2.0), c("robot_gris"), name="Caisse")
        b.box((-1.8, 2.6, -1.6), (1.8, 5.0, 1.8), c("robot_orange"), studs="top", name="Tourelle")
        b.box((-1.9, 3.0, -1.7), (1.9, 3.5, 1.9), c("danger_jaune"), collide=False, name="Bande")
        b.box((-1.9, 3.5, -1.7), (1.9, 3.8, 1.9), c("noir"), collide=False, name="Bande")
        b.box((-1.1, 5.0, -1.3), (1.1, 6.2, 1.1), c("robot_blanc"), studs="top", name="Tete")
        _oeil(b, -0.2, 5.6, -1.3, r=0.42)
        # bras de sparring rembourré
        b.cyl((2.05, 4.2, 0), 0.6, 0.5, c("robot_gris"), axis="x", name="Epaule")
        b.box((1.95, 3.75, -2.2), (2.75, 4.55, 0.2), c("robot_blanc"), name="Bras")
        b.box((1.55, 3.0, -2.85), (2.85, 5.2, -2.1), c("cible_rouge"), studs="top", name="Coussin")
        b.box((1.5, 3.9, -2.95), (2.9, 4.3, -2.05), c("cible_blanc"), collide=False, name="Bande")
        _antenne(b, -1.2, 5.0, 1.2, 2.2)
        return {"emprise": (5.8, 6.0), "hauteur": 7.6}


def cible(b, variant=0):
    """Cibles d'entraînement tournées vers -Z (≈ 6 de haut).
    v0 cible ronde sur trépied ; v1 panneau carré à cercles sur deux poteaux ; v2 cible escamotable sur mât."""
    v = variant % 3
    with b.group("Cible"):
        if v == 0:
            y = 4.0
            for k, (r, coul) in enumerate(((2.2, "cible_blanc"), (1.6, "cible_rouge"), (1.0, "cible_blanc"),
                                           (0.45, "cible_rouge"))):
                avant, arriere = -(0.75 + 0.15 * k), -0.45 - 0.05 * k      # faces décalées : aucune face commune
                b.cyl((0, y, (avant + arriere) / 2), r, arriere - avant, c(coul), axis="z", name="Anneau")
            for a in (0, 120, 240):
                t = math.radians(a)
                pied = np.array([1.4 * math.sin(t), 0.0, 1.3 * math.cos(t)])
                tete = np.array([0.0, y - 0.6, -0.1])
                _segment(b, pied, tete, 0.13, c("acier_fonce"), name="Pied", collide=True)
            b.box((-0.4, y - 1.0, -0.45), (0.4, y - 0.2, 0.25), c("acier_fonce"), name="Rotule")
            return {"emprise": (4.4, 3.0), "hauteur": 6.2}
        if v == 1:
            for x in (-1.6, 1.6):
                b.box((x - 0.6, 0, -0.6), (x + 0.6, 0.3, 0.6), c("beton_fonce"), name="Platine")
                b.box((x - 0.2, 0.3, -0.2), (x + 0.2, 4.6, 0.2), c("bois"), name="Poteau")
            b.box((-2.2, 2.0, -0.5), (2.2, 6.2, -0.2), c("bois_clair"), name="Panneau")
            for k, (r, coul) in enumerate(((1.7, "cible_blanc"), (1.2, "cible_rouge"), (0.5, "cible_blanc"))):
                b.cyl((0, 4.1, -0.55 - 0.05 * k), r, 0.1 + 0.1 * k, c(coul), axis="z", name="Anneau")
            return {"emprise": (4.4, 1.2), "hauteur": 6.2}
        b.box((-1.0, 0, -1.0), (1.0, 0.8, 1.0), c("danger_jaune"), studs="top", name="Socle")
        b.box((-1.05, 0.25, -1.05), (1.05, 0.55, 1.05), c("noir"), collide=False, name="Bande")
        b.cyl((0, 0.8 + 2.4, 0), 0.18, 4.8, c("acier"), name="Mat")
        b.box((-0.35, 5.2, -0.35), (0.35, 5.8, 0.35), c("acier_fonce"), name="Charniere")
        for k, (r, coul) in enumerate(((1.5, "cible_rouge"), (1.0, "cible_blanc"), (0.45, "cible_rouge"))):
            avant, arriere = -(0.6 + 0.15 * k), -0.3 - 0.05 * k
            b.cyl((0, 6.0, (avant + arriere) / 2), r, arriere - avant, c(coul), axis="z", name="Disque")
        return {"emprise": (3.0, 2.0), "hauteur": 7.5}


def mur_obstacles(b, variant=0, longueur=14.0, hauteur=13.0):
    """Mur d'obstacles et d'escalade (face vers -Z) : voile de béton à bandes de danger, prises colorées en
    saillie, plateforme supérieure à garde-corps, poutres d'appui à l'arrière."""
    rng = b.rng
    L, H = float(longueur), float(hauteur)
    with b.group("MurObstacles"):
        b.box((-L / 2, 0, -0.8), (L / 2, H, 0.8), c("beton_clair"), name="Voile")
        for k in range(int(L // 2)):
            x0 = -L / 2 + 2 * k
            if k % 2 == 0:
                b.box((x0, 0, -0.95), (x0 + 2, 1.2, -0.8), c("danger_jaune"), collide=False, name="Danger")
                b.box((x0, H - 1.2, -0.95), (x0 + 2, H, -0.8), c("danger_jaune"), collide=False, name="Danger")
            else:
                b.box((x0, 0, -0.95), (x0 + 2, 1.2, -0.8), c("noir"), collide=False, name="Danger")
                b.box((x0, H - 1.2, -0.95), (x0 + 2, H, -0.8), c("noir"), collide=False, name="Danger")
        cols = ("robot_orange", "violet", "neon_cyan", "jaune", "rouge")
        for i in range(14):
            x = float(rng.uniform(-L / 2 + 1, L / 2 - 1))
            y = 1.8 + (H - 3.6) * i / 13
            b.box((x - 0.4, y, -1.35), (x + 0.4, y + 0.6, -0.8), c(cols[i % len(cols)]), collide=False, name="Prise")
        b.box((-L / 2 - 0.3, H, -1.2), (L / 2 + 0.3, H + 0.6, 2.4), c("acier"), studs="top", name="Plateforme")
        b.box((-L / 2 - 0.3, H + 0.6, 2.1), (L / 2 + 0.3, H + 2.2, 2.4), c("robot_orange"), collide=False,
              name="GardeCorps")
        for x in (-L / 2 + 0.6, L / 2 - 0.6):
            b.box((x - 0.3, 0, 0.8), (x + 0.3, H, 2.0), c("acier_fonce"), name="Appui")
    return {"emprise": (L + 0.6, 3.6), "hauteur": H + 2.2}


def mat_cibles(b, variant=0, hauteur=14.0):
    """Mât d'entraînement à trois cibles rondes étagées (face vers -Z), socle à bandes de danger."""
    H = float(hauteur)
    with b.group("MatCibles"):
        b.box((-1.4, 0, -1.4), (1.4, 0.9, 1.4), c("danger_jaune"), studs="top", name="Socle")
        b.box((-1.45, 0.3, -1.45), (1.45, 0.6, 1.45), c("noir"), collide=False, name="Bande")
        b.box((-0.35, 0.9, -0.35), (0.35, H, 0.35), c("acier"), name="Mat")
        for k, (y, dx) in enumerate(((5.0, -2.2), (8.6, 2.2), (12.2, -1.6))):
            b.box((min(0, dx) - 0.2, y - 0.2, -0.1), (max(0, dx) + 0.2, y + 0.2, 0.3), c("acier_fonce"),
                  collide=False, name="Bras")
            for j, (r, coul) in enumerate(((1.8, "cible_blanc"), (1.25, "cible_rouge"), (0.7, "cible_blanc"),
                                           (0.3, "cible_rouge"))):
                avant, arriere = -(0.45 + 0.12 * j), -0.2 - 0.04 * j
                b.cyl((dx, y, (avant + arriere) / 2), r, arriere - avant, c(coul), axis="z", collide=False,
                      name="Anneau")
        b.box((-0.5, H, -0.5), (0.5, H + 0.4, 0.5), c("neon_cyan"), material="Neon", collide=False, shadow=False,
              name="Feu")
    return {"emprise": (6.4, 2.8), "hauteur": H + 0.4}
