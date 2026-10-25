"""Colline finale de la cité blanche (zone 6) : grande tour blanche, monolithe sacré et tunnel de sortie,
en style stud.

colline_tour(b, variant=0, passage=96, largeur=420, profondeur=46, hauteur=46, sol_tunnel=36, appuis=(80, 150),
             texte="門")                                                  → 1 340 à 1 470 pièces (budget 1 700)
    Origine = centre de l'entrée du tunnel, au niveau du sol. Exception à la règle « l'avant regarde -Z » : la
    colline regarde +Z (vers la cour des œufs et les joueurs qui arrivent) ; sa masse s'étend vers -Z jusqu'à
    z = -profondeur, où commence la zone suivante. Emprise x ∈ [-largeur/2, largeur/2], z ∈ [-profondeur, +5,8]
    (rien au-delà de +1 pour |x| < 56). Si un tirage dépasse le budget, la colline est reconstruite avec moins
    d'arbres et de saillies (densité affichée dans le résultat).

    - Mur de soutènement (ishigaki) de pierre pâle sur toute la largeur : assises de 3 studs qui reculent de 0,6
      (fruit), studs sur les gradins, 30 de haut jusqu'à |x| ≈ 156 puis en marches jusqu'à 18 au bout. Sur sa
      crête court un mur d'enduit blanc à chaperon ocre et meurtrières (dobei). Des appuis verticaux (|x| des
      `appuis`) reçoivent les murs de la cour et les remparts qui viennent buter contre la colline.
    - Portail : bastions de pierre appareillée claire (assises alternées, 43 de haut) de part et d'autre du
      passage, poutre de linteau sombre ferrée, lanternes ; corps de garde blanc (poteaux sombres, fenêtres à
      barreaux, balcon laqué rouge, toit ocre irimoya à pignon central, plaque 門 ou 静) entre deux tours d'angle
      blanches à deux étages et toits ocre (sommet vers 74).
    - Tunnel : |x| < passage/2 vide de y = 0,05 à y = 38 sur toute la profondeur ; murs de pierre sombre en
      bandes, piliers et arcs de pierre claire (arcs au-dessus de 38), appliques lumineuses (saillie de 0,75 au
      plus, en |x| ≥ passage/2 + 0,25), plafond sombre, bouche de sortie encadrée de pierre en z = -profondeur.
      Le sol du tunnel vient de zone.py (|x| < sol_tunnel) ; la colline complète la bande entre sol_tunnel et
      les murs, 0,1 plus bas (aucun conflit si zone.py élargit son sol).
    - Colline : gradins de roche pâle en strates (roche claire, roche, roche foncée, filets d'ombre) qui montent
      à `hauteur` au centre et descendent vers les côtés (≈ 34 en |x| = 150, ≈ 22 au bout), buttes et saillies
      rocheuses, butte boisée au-dessus du tunnel ; masses d'arbres en gros blocs (verts tendres, dessus clairs,
      quelques cerisiers roses), cèdres et pins. Le vert reste en masses, jamais dominant.
    - Grande tour blanche (à gauche en variante 0, x ≈ ±(passage/2 + 30)) : socle de pierre, quatre corps qui se
      rétrécissent, pilastres d'angle, bandes laquées rouges en saillie, fenêtres sombres sur toutes les faces,
      balcon rouge, couronne de flèches sombres (sommet ≈ 149), deux tours annexes à flèche, deux ailes basses
      blanches à toits ocre. Fenêtres à barreaux en alternance avec des panneaux d'enduit, jupes de tuiles ocre
      entre les corps. Aucune passerelle vers le monolithe.
    - Monolithe (de l'autre côté) : pierre sacrée générique (iwakura) grise et chaude, large à la base (≈ 28 × 18)
      et resserrée vers 18 en haut : cinq colonnes accolées de hauteurs et de fruits différents (blocs empilés
      un peu décalés, tons en facettes), fissure verticale sombre, longues arêtes claires, sommet coupé en biais
      (coins, jamais une pointe, sommet ≈ 143), jupe d'éboulis au pied ; corde sacrée (shimenawa) épaisse et
      affaissée vers le quart de la hauteur, grands papiers blancs en zigzag (shide), franges ; terrasse de
      pierre, marches, deux lanternes ; grande masse d'arbres à son pied.
    - Butte au-dessus du tunnel : trois gradins de roche derrière le corps de garde (jusqu'à 68), affleurements
      clairs, masse d'arbres et cèdres qui dépassent nettement son toit.
    - Escalier de pierre à lanternes : deux volées en zigzag contre le mur (hors de |x| < passage/2 + 8), puis une
      volée taillée dans la colline jusqu'à la terrasse de la tour (variantes 0, 1) ou du monolithe (2, 3).

    Variantes : 0 tour à gauche, monolithe à droite, escalier à gauche ; 1 l'inverse ; 2 comme 0 avec un autre
    tirage et l'escalier à droite (côté monolithe) ; 3 comme 1 avec l'escalier à gauche (côté monolithe).
    Paramétrique : passage = 96 pour le couloir élargi (|x| < 45 ; rien dans |x| < 48 sous 38) ; l'ancien plan
    (passage = 68) fonctionne aussi. Bastions, escalier, tour et monolithe se décalent avec passage/2.

Uniquement des éléments japonais génériques : aucun nom, aucun emblème, aucun chiffre, aucune arme, aucun
échafaud ; la tour n'a pas de pont vers le monolithe. Textes : 門 ou 静 seulement.
"""

from __future__ import annotations

import math

import numpy as np

from kit import hexrgb, mix, rot_z, shade
from palette import c, vary

try:
    from assets import mobilier
except ImportError:  # pragma: no cover - module importé hors du paquet
    import mobilier  # type: ignore

BUDGET = 1700
H_ASSISE = 3.0       # hauteur d'une assise du mur de soutènement
RETRAIT = 0.6        # fruit : chaque assise recule de 0,6
Y_LIBRE = 38.0       # hauteur libre du tunnel (dessous des arcs et du linteau)
Y_PLAFOND = 40.0     # sous-face du plafond entre les arcs
Y_MUR = 30.0         # crête du mur de soutènement
Z_MUR = -8.0         # arrière du mur de soutènement (pied des gradins)
Z_BASTION = -13.0    # arrière des bastions de la porte (le corps de garde est posé dessus)
Y_BASTION = 43.0     # dessus des bastions (base du corps de garde)

# ---------------------------------------------------------------------------
# Couleurs
# ---------------------------------------------------------------------------
TONS = {"O": "roche_ombre", "F": "roche_fonce", "R": "roche", "C": "roche_claire"}
STRATES_FINES = [(0, 9, "F"), (9, 11, "O"), (11, 22, "R"), (22, 24, "F"), (24, 33, "C"), (33, 35, "O"),
                 (35, 42, "R"), (42, 44, "F"), (44, 400, "C")]
# dos de la colline (vu depuis la zone suivante) : bancs épais en bas, strates fines en haut
STRATES_DOS = [(0, 11, "F"), (11, 13, "O"), (13, 26, "R"), (26, 28, "F"), (28, 33, "C"), (33, 35, "O"),
               (35, 42, "R"), (42, 44, "F"), (44, 400, "C")]
RETRAIT_DOS = 1.0    # le dos de la colline recule d'un stud : le cadre de la bouche de sortie ressort
PIERRES = ("pierre_claire", "pierre", "roche_claire", "pierre", "roche", "pierre_claire", "dallage_ombre")
TAILLE = ("pierre_claire", "dallage", "pierre_claire", "dallage_ombre")     # pierre appareillée (portail)
BLANCS = ("blanc", "blanc_creme", "blanc_pur", "blanc", "blanc_ombre")
PLAFOND = mix(c("roche_ombre"), c("monolithe_nuit"), 0.55)
MUR_TUNNEL = mix(c("pierre_fonce"), c("roche_ombre"), 0.5)
FEUILLES = ("feuille_nuit", "feuille_fonce", "feuille", "feuille_claire")
DESSUS_CLAIR = mix(c("feuille_claire"), hexrgb("#DDEBA0"), 0.35)
SAKURAS = ("sakura_fonce", "sakura", "sakura_clair", "sakura_pale")


def col(x):
    """Nom de palette, '#hex' ou tuple → tuple RGB."""
    if isinstance(x, tuple):
        return x
    if isinstance(x, str) and x.startswith("#"):
        return hexrgb(x)
    return c(x)


def vr(x, rng, a=0.04):
    return vary(col(x), rng, a)


def _suite(rng, n, noms, a=0.0):
    """n couleurs tirées dans `noms`, jamais deux voisines identiques."""
    out, prev = [], None
    for _ in range(n):
        k = noms[int(rng.integers(0, len(noms)))]
        while k == prev and len(set(noms)) > 1:
            k = noms[int(rng.integers(0, len(noms)))]
        prev = k
        out.append(vr(k, rng, a) if a else c(k))
    return out


def _bx(b, s, u0, u1, y0, y1, z0, z1, couleur, **kw):
    """Bloc en coordonnée miroir : u = |x| du côté s (−1 gauche, +1 droite)."""
    return b.box((s * u0, y0, z0), (s * u1, y1, z1), couleur, **kw)


# ---------------------------------------------------------------------------
# Toits (mêmes profils que les portes de la cité)
# ---------------------------------------------------------------------------
def _jupe(b, x0, x1, z0, z1, y, h1, a, toit, rng, *, sous="ocre_fonce", rive="ocre_clair", coeur=True, name="Toit"):
    """Avant-toit à quatre pans : sous-face sombre, quatre coins stud, cœur ; a = (z0, z1, x0, x1)."""
    t = col(toit)
    az0, az1, ax0, ax1 = a
    xi0, xi1, zi0, zi1 = x0 + ax0, x1 - ax1, z0 + az0, z1 - az1
    if sous:
        b.box((x0, y - 0.45, z0), (x1, y, z1), col(sous), name=f"{name}_sous")
    b.wedge((x0, y, z0), (x1, y + h1, zi0), vr(t, rng, 0.02), down="-z", studs="top", name=name)
    b.wedge((x0, y, zi1), (x1, y + h1, z1), vr(t, rng, 0.02), down="+z", studs="top", name=name)
    b.wedge((x0, y, zi0), (xi0, y + h1, zi1), vr(t, rng, 0.02), down="-x", studs="top", name=name)
    b.wedge((xi1, y, zi0), (x1, y + h1, zi1), vr(t, rng, 0.02), down="+x", studs="top", name=name)
    if coeur:
        b.box((xi0, y, zi0), (xi1, y + h1, zi1), shade(t, 0.8), name=f"{name}_coeur")
    if rive:
        rc = col(rive)
        b.box((x0 - 0.1, y - 0.2, z0 - 0.1), (x1 + 0.1, y + 0.3, z0 + 0.5), rc, collide=False, name=f"{name}_rive")
        b.box((x0 - 0.1, y - 0.2, z1 - 0.5), (x1 + 0.1, y + 0.3, z1 + 0.1), rc, collide=False, name=f"{name}_rive")
        b.box((x0 - 0.1, y - 0.2, z0 + 0.5), (x0 + 0.5, y + 0.3, z1 - 0.5), rc, collide=False, name=f"{name}_rive")
        b.box((x1 - 0.5, y - 0.2, z0 + 0.5), (x1 + 0.1, y + 0.3, z1 - 0.5), rc, collide=False, name=f"{name}_rive")
    return xi0, xi1, zi0, zi1, y + h1


def _irimoya(b, x0, x1, z0, z1, y, h1, h2, a, toit, rng, *, tri="blanc", deb_g=0.8, ornement="or", h_orn=2.2,
             rive="ocre_clair", bouts=True, name="Toit"):
    """Toit irimoya (croupe et pignon), faîtage le long de X : jupe, deux pans raides, pignons blancs,
    pendentifs dorés, faîtage et ornements (bouts=False : sans pignons ni ornements, pour un toit dont les
    extrémités entrent dans des tours). Renvoie les cotes utiles."""
    t = col(toit)
    xi0, xi1, zi0, zi1, ya = _jupe(b, x0, x1, z0, z1, y, h1, a, toit, rng, rive=rive, name=name)
    zm = (zi0 + zi1) / 2
    xg0, xg1 = xi0 - deb_g, xi1 + deb_g
    b.wedge((xg0, ya, zi0), (xg1, ya + h2, zm), vr(t, rng, 0.02), down="-z", studs="top", name=name)
    b.wedge((xg0, ya, zm), (xg1, ya + h2, zi1), vr(t, rng, 0.02), down="+z", studs="top", name=name)
    pente = h2 / (zm - zi0)
    bord = 0.45
    zs = zi0 + (0.35 + bord) / pente
    if bouts:
        for xe, s in ((xg0, -1), (xg1, 1)):
            xa_, xb_ = sorted((xe, xe + 0.15 * s))
            b.wedge((xa_, ya + 0.35, zs), (xb_, ya + h2 - bord, zm), col(tri), down="-z", collide=False,
                    name=f"{name}_pignon")
            b.wedge((xa_, ya + 0.35, zm), (xb_, ya + h2 - bord, 2 * zm - zs), col(tri), down="+z", collide=False,
                    name=f"{name}_pignon")
            ga, gb = sorted((xe + 0.15 * s, xe + 0.45 * s))
            b.box((ga, ya + h2 - 2.2, zm - 0.5), (gb, ya + h2 - 0.6, zm + 0.5), col("or"), collide=False,
                  name=f"{name}_gegyo")
    yr = ya + h2
    ext = 0.3 if bouts else -0.1
    b.box((xg0 - ext, yr - (0.9 * pente + 0.35), zm - 0.9), (xg1 + ext, yr + 0.8, zm + 0.9), col("ocre_fonce"),
          studs="top", name=f"{name}_faite")
    top = yr + 0.8
    if ornement and bouts:
        for xe, s in ((xg0 - 0.3, 1), (xg1 + 0.3, -1)):
            xa_, xb_ = sorted((xe - s * 0.15, xe + s * 1.3))
            b.box((xa_, yr - 0.4, zm - 0.65), (xb_, yr + 0.8 + h_orn, zm + 0.65), col(ornement), collide=False,
                  name=f"{name}_ornement")
        top = yr + 0.8 + h_orn
    return {"top": top, "yr": yr, "zm": zm, "ya": ya, "zi1": zi1}


def _chidori(b, xc, demi, y0, h, z_fond, z_face, toit, rng, name="Chidori"):
    """Pignon de lucarne posé sur le pan avant (faîtage le long de Z), triangle blanc et pendentif doré."""
    t = col(toit)
    za, zb = sorted((z_fond, z_face))
    b.wedge((xc - demi, y0, za), (xc, y0 + h, zb), vr(t, rng, 0.02), down="-x", studs="top", name=name)
    b.wedge((xc, y0, za), (xc + demi, y0 + h, zb), vr(t, rng, 0.02), down="+x", studs="top", name=name)
    b.box((xc - 0.6, y0 + h - 0.45, za), (xc + 0.6, y0 + h + 0.5, zb + 0.3), shade(t, 0.72), studs="top",
          name=f"{name}_faite")
    b.wedge((xc - demi + 0.8, y0 + 0.35, zb), (xc, y0 + h - 0.55, zb + 0.15), col("blanc"), down="-x",
            collide=False, name=f"{name}_pignon")
    b.wedge((xc, y0 + 0.35, zb), (xc + demi - 0.8, y0 + h - 0.55, zb + 0.15), col("blanc"), down="+x",
            collide=False, name=f"{name}_pignon")
    b.box((xc - 0.55, y0 + h - 2.6, zb + 0.15), (xc + 0.55, y0 + h - 0.8, zb + 0.45), col("or"), collide=False,
          name=f"{name}_gegyo")


def _plaque(b, xc, y0, w, h, z_mur, texte):
    """Plaque (gaku) contre une façade tournée vers +Z : cadre doré, planche bleu profond, caractère doré."""
    b.box((xc - w / 2 - 0.35, y0 - 0.35, z_mur), (xc + w / 2 + 0.35, y0 + h + 0.35, z_mur + 0.3), col("or"),
          collide=False, name="Plaque_cadre")
    p = b.box((xc - w / 2, y0, z_mur + 0.1), (xc + w / 2, y0 + h, z_mur + 0.45), col("bleu_profond"),
              collide=False, name="Plaque")
    p.label = {"face": "Back", "text": texte, "color": col("or"), "bg": None, "font": "brush", "vertical": True}
    return p


# ---------------------------------------------------------------------------
# Mur de soutènement (ishigaki), dobei, appuis
# ---------------------------------------------------------------------------
def _r(k: int) -> float:
    return RETRAIT * k


def _z_face(y: float) -> float:
    """Front du mur juste sous la hauteur y (l'assise qui contient y - ε)."""
    return -_r(max(0, math.floor((y - 1e-6) / H_ASSISE)))


def _fin_assise(y1: float, W: float, u_plein: float) -> float:
    """Bout (|x|) d'une assise dont le dessus est en y1 : pleine hauteur jusqu'à u_plein, puis en marches."""
    if y1 <= 18 + 1e-6:
        return W
    return u_plein + (Y_MUR - y1) / (Y_MUR - 18) * (W - u_plein)


def _h_mur(u: float, W: float, u_plein: float) -> float:
    """Hauteur du mur de soutènement en |x| = u."""
    h = 0.0
    for k in range(int(round(Y_MUR / H_ASSISE))):
        y1 = (k + 1) * H_ASSISE
        if _fin_assise(y1, W, u_plein) >= u - 1e-6:
            h = y1
    return h


def _mur(b, s, rng, u0, W, u_plein):
    """Assises de pierre pâle en gradins, de u0 au bout de la colline ; studs sur les gradins."""
    for k in range(int(round(Y_MUR / H_ASSISE))):
        y0, y1 = k * H_ASSISE, (k + 1) * H_ASSISE
        ue = _fin_assise(y1, W, u_plein)
        cuts = [u0]
        while cuts[-1] < ue - 1e-6:
            nx = cuts[-1] + float(rng.choice([10, 12, 14, 16, 18, 20, 22, 24]))
            if ue - nx < 6:
                nx = ue
            cuts.append(nx)
        for (a, bb), cc in zip(zip(cuts, cuts[1:]), _suite(rng, len(cuts) - 1, PIERRES, 0.03)):
            _bx(b, s, a, bb, y0, y1, Z_MUR, -_r(k), cc, studs="top", name="Ishigaki")


def _chaperon(b, s, u0, u1, zc, demi, y, deb, h, rng, name="Chaperon"):
    """Chaperon de tuiles ocre à deux pentes le long de X (côté s) : sous-face, deux coins stud, faîtage."""
    za, zb = zc - demi - deb, zc + demi + deb
    _bx(b, s, u0, u1, y, y + 0.3, za, zb, col("ocre_fonce"), name=f"{name}_sous")
    y1 = y + 0.3
    t = col("ocre")
    b.wedge((s * u0, y1, za), (s * u1, y1 + h, zc), vr(t, rng, 0.02), down="-z", studs="top", name=name)
    b.wedge((s * u0, y1, zc), (s * u1, y1 + h, zb), vr(t, rng, 0.02), down="+z", studs="top", name=name)
    pente = h / (demi + deb)
    _bx(b, s, u0 + 0.1, u1 - 0.1, y1 + h - 0.5 * pente - 0.2, y1 + h + 0.45, zc - 0.5, zc + 0.5, col("ocre_brun"),
        studs="top", name=f"{name}_faite")
    return y1 + h + 0.45


def _dobei(b, s, rng, ua, ub):
    """Mur d'enduit blanc à chaperon ocre sur la crête du mur de soutènement, avec meurtrières carrées."""
    if ub - ua < 4:
        return
    y0, y1 = Y_MUR, Y_MUR + 3.2
    zf = _z_face(Y_MUR) - 0.4          # face avant (0,4 en retrait du nez de la crête)
    zr = zf - 1.0
    n = max(1, int(round((ub - ua) / 16)))
    w = (ub - ua) / n
    for i, cc in enumerate(_suite(rng, n, BLANCS)):
        _bx(b, s, ua + i * w, ua + (i + 1) * w, y0, y1, zr, zf, cc, name="Dobei")
        for f in (0.3, 0.72):
            um = ua + (i + f) * w
            _bx(b, s, um - 0.45, um + 0.45, y0 + 1.3, y0 + 2.2, zr - 0.1, zf + 0.1, col("fenetre"), collide=False,
                name="Meurtriere")
    m = max(1, int(round((ub - ua) / 30)))
    L = (ub - ua) / m
    for j in range(m):
        _chaperon(b, s, ua + j * L, ua + (j + 1) * L, (zf + zr) / 2, 0.5, y1, 0.8, 1.0, rng)
    # poteaux d'about (blanc pur) aux deux bouts
    for u in (ua, ub):
        _bx(b, s, u - 0.5, u + 0.5, y0, y1 + 0.2, zr - 0.15, zf + 0.15, col("blanc_pur"), name="Dobei_about")


def _appui(b, s, rng, u, y_haut):
    """Appui vertical (sans fruit) où viennent buter un mur de la cour ou un rempart : deux pierres et un
    chapeau stud."""
    za = _z_face(y_haut)
    ym = round(y_haut * 0.45)
    _bx(b, s, u - 1.8, u + 1.8, 0, ym, za, 0.2, vr("pierre_claire", rng, 0.03), name="Appui")
    _bx(b, s, u - 1.8, u + 1.8, ym, y_haut, za, 0.2, vr("pierre", rng, 0.03), name="Appui")
    _bx(b, s, u - 2.1, u + 2.1, y_haut, y_haut + 0.8, za - 0.3, 0.5, col("pierre_fonce"), studs="top",
        name="Appui_chapeau")


# ---------------------------------------------------------------------------
# Portail, tunnel, corps de garde
# ---------------------------------------------------------------------------
def _bastions(b, rng, P, XJ):
    """Jambages du portail : pierre appareillée claire en assises de 3, joints alternés (long/court)."""
    for s in (-1, 1):
        for k in range(14):
            y0, y1 = k * H_ASSISE, (k + 1) * H_ASSISE
            cut = P + (5.0 if k % 2 == 0 else 3.0)
            ca, cb = _suite(rng, 2, TAILLE, 0.02)
            _bx(b, s, P, cut, y0, y1, Z_BASTION, 0.0, ca, studs="top", name="Jambage")
            _bx(b, s, cut, XJ, y0, y1, Z_BASTION, 0.0, cb, studs="top", name="Bastion")
    # chapeau commun (sur les deux bastions et le linteau) : base du corps de garde
    b.box((-XJ - 0.4, 42.0, Z_BASTION), (XJ + 0.4, Y_BASTION, 0.4), col("pierre_claire"), studs="top",
          name="Corniche_portail")
    # poutre de linteau en bois sombre, ferrures
    b.box((-P - 1.5, Y_LIBRE, -1.2), (P + 1.5, 41.0, 0.8), col("bois_fonce"), name="Linteau")
    b.box((-P, 41.0, -1.2), (P, 42.0, 0.0), col("pierre"), name="Linteau_pierre")
    nf = max(4, int(round(2 * P / 12)))
    for i in range(nf + 1):
        x = -P + 2 * P * i / nf
        b.box((x - 0.7, 38.6, 0.8), (x + 0.7, 40.4, 0.95), col("fer"), collide=False, name="Ferrure")
    b.box((-P - 1.5, 39.35, 0.8), (P + 1.5, 39.65, 0.92), col("or"), collide=False, name="Lisere")
    # lanternes de part et d'autre du portail, sur la face avant des jambages
    for s in (-1, 1):
        u = P + 3.0
        _bx(b, s, u - 0.35, u + 0.35, 15.6, 16.0, 0.0, 0.8, col("fer"), collide=False, name="Console")
        _bx(b, s, u - 0.55, u + 0.55, 14.0, 15.6, 0.2, 0.95, col("jaune_lampion"), material="Neon", collide=False,
            shadow=False, name="Lanterne")
        _bx(b, s, u - 0.7, u + 0.7, 15.6, 15.9, 0.15, 1.0, col("noir"), collide=False, name="Lanterne_chapeau")


def _lanterne_murale(b, s, u_mur, y, z):
    """Applique de tunnel : console de fer, boîte lumineuse (Neon), chapeau ; saillie de 0,75 au plus."""
    _bx(b, s, u_mur - 0.75, u_mur, y - 0.35, y, z - 0.35, z + 0.35, col("fer"), collide=False, name="Console")
    _bx(b, s, u_mur - 0.65, u_mur - 0.05, y, y + 1.7, z - 0.5, z + 0.5, col("jaune_lampion"), material="Neon",
        collide=False, shadow=False, name="Applique")
    _bx(b, s, u_mur - 0.75, u_mur, y + 1.7, y + 2.0, z - 0.6, z + 0.6, col("noir"), collide=False,
        name="Applique_chapeau")


def _tunnel(b, rng, P, XJ, D, sol_tunnel):
    """Murs du tunnel en bandes de pierre, piliers et arcs de pierre claire (tout au-dessus de 38), plafond
    sombre, appliques, bouche de sortie encadrée, dessus en plateau."""
    z_sortie = -D + 3.0
    n_baies = 3
    baie = (Z_BASTION - z_sortie - 2.0 * n_baies) / n_baies
    arcs = []
    z = Z_BASTION
    for _ in range(n_baies):
        arcs.append((z - 2.0, z))
        z -= 2.0 + baie
    bandes = ((0.0, 15.0, MUR_TUNNEL), (15.0, 29.0, shade(MUR_TUNNEL, 1.07)), (29.0, Y_BASTION, shade(MUR_TUNNEL, 0.93)))
    for s in (-1, 1):
        for (ya, yb, cc) in bandes:
            _bx(b, s, P + 1, XJ, ya, yb, z_sortie, Z_BASTION, cc, name="Tunnel_mur")
        _bx(b, s, P + 0.6, P + 1, 0, 2.4, z_sortie, Z_BASTION, col("bordure"), name="Tunnel_plinthe")
        for (za, zb) in arcs:
            _bx(b, s, P, P + 1, 0, Y_PLAFOND, za, zb, vr("pierre_claire", rng, 0.02), name="Pilier")
            zc = za - baie / 2
            _lanterne_murale(b, s, P + 1, 10.0, zc)
        # bouche de sortie : jambage en deux pierres, remplissage
        _bx(b, s, P, P + 5, 0, 20, -D, z_sortie, vr("pierre_claire", rng, 0.02), name="Sortie_jambage")
        _bx(b, s, P, P + 5, 20, Y_BASTION, -D, z_sortie, vr("dallage_ombre", rng, 0.02), name="Sortie_jambage")
        _pile(b, s, P + 5, XJ, -D + RETRAIT_DOS, z_sortie, 0, Y_BASTION, STRATES_DOS, rng, name="Sortie_mur",
              studs_haut=False)
        # sol entre le sol du couloir (zone.py) et le mur, 0,1 plus bas (aucun conflit s'il est élargi)
        if P + 1 > sol_tunnel + 0.05:
            _bx(b, s, sol_tunnel, P + 1, -1.1, -0.1, -D, 0.0, col("pierre_fonce"), studs="top", name="Tunnel_sol")
    b.box((-P - 1, Y_PLAFOND, z_sortie), (P + 1, Y_BASTION, Z_BASTION), PLAFOND, name="Plafond")
    b.box((-P, Y_PLAFOND, Z_BASTION), (P, 42.0, -1.0), PLAFOND, name="Plafond")
    for (za, zb) in arcs:
        b.box((-P, Y_LIBRE, za), (P, Y_PLAFOND, zb), vr("pierre_claire", rng, 0.02), name="Arc")
    b.box((-P, Y_LIBRE, -D), (P, 40.5, z_sortie), col("bois_fonce"), name="Sortie_linteau")
    b.box((-P, 40.5, -D), (P, Y_BASTION, z_sortie), vr("pierre_claire", rng, 0.02), name="Sortie_linteau")
    # dessus : plateau au-dessus du tunnel et des murs
    cp = vr("roche_claire", rng, 0.02)
    b.box((-P - 5, Y_BASTION, -D), (P + 5, Y_BASTION + 3, Z_BASTION), cp, studs="top", name="Plateau")
    for s in (-1, 1):
        _bx(b, s, P + 5, XJ, Y_BASTION, Y_BASTION + 3, -D + RETRAIT_DOS, Z_BASTION, cp, studs="top", name="Plateau")



def _corps_de_garde(b, rng, P, XJ, texte):
    """Corps de garde blanc sur le portail, entre deux tours d'angle : enduit en panneaux, poteaux sombres,
    fenêtres à barreaux, balcon laqué rouge, toit irimoya ocre à pignon central, plaque."""
    y0 = Y_BASTION
    xg = P + 1.0                 # le corps entre dans les tours d'angle
    z0, z1 = -11.0, -3.0
    H1 = 8.0
    b.box((-xg, y0, z0 - 0.2), (xg, y0 + 0.8, z1 + 0.2), col("bois_fonce"), name="Seuil")
    n = max(4, 2 * int(round(xg / 13)))
    w = 2 * xg / n
    for i, cc in enumerate(_suite(rng, n, BLANCS)):
        b.box((-xg + i * w, y0 + 0.8, z0), (-xg + (i + 1) * w, y0 + H1, z1), cc, name="Enduit")
    for i in range(1, n):
        x = -xg + i * w
        b.box((x - 0.35, y0 + 0.8, z0 - 0.2), (x + 0.35, y0 + H1, z1 + 0.2), col("bois_fonce"), name="Poteau")
    for zz, sens in ((z1, 1), (z0, -1)):
        za, zb = sorted((zz, zz + 0.15 * sens))
        b.box((-xg, y0 + H1 - 1.7, za), (xg, y0 + H1 - 1.1, zb), col("bois_fonce"), collide=False, name="Nageshi")
    for i in range(n):
        xc = -xg + (i + 0.5) * w
        if abs(xc) < w:   # travées centrales : plaque
            continue
        b.box((xc - 1.7, y0 + 2.6, z0 - 0.1), (xc + 1.7, y0 + 5.4, z1 + 0.1), col("fenetre"), name="Fenetre")
        for dx in (-0.6, 0.6):
            b.box((xc + dx - 0.16, y0 + 2.65, z0 - 0.2), (xc + dx + 0.16, y0 + 5.35, z1 + 0.2), col("bois_fonce"),
                  collide=False, name="Barreau")
    _plaque(b, 0.0, y0 + 1.9, 3.4, 4.4, z1, texte)
    # balcon laqué rouge sur la corniche du portail, d'une tour à l'autre
    yb = y0 + 0.6
    xbal = P + 0.45
    b.box((-xbal, y0, z1 + 0.2), (xbal, yb, 0.4), col("laque_rouge_fonce"), studs="top", name="Balcon_plancher")
    zr = -0.15
    nb = max(4, int(round(2 * xbal / 7.5)))
    for i in range(nb + 1):
        x = -(xbal - 0.35) + 2 * (xbal - 0.35) * i / nb
        b.box((x - 0.3, yb, zr - 0.3), (x + 0.3, yb + 3.15, zr + 0.3), col("laque_rouge"), collide=False,
              name="Balcon_poteau")
    b.box((-xbal, yb + 2.85, zr - 0.4), (xbal, yb + 3.3, zr + 0.4), col("laque_noire"), collide=False,
          name="Balcon_main_courante")
    b.box((-xbal, yb + 1.1, zr - 0.2), (xbal, yb + 1.5, zr + 0.2), col("laque_rouge"), collide=False,
          name="Balcon_lisse")
    # toit (ses bouts entrent dans les tours d'angle)
    yt = y0 + H1
    t = _irimoya(b, -xg - 2.6, xg + 2.6, z0 - 2.4, z1 + 2.6, yt, 2.4, 4.6, (2.4, 2.6, 3.4, 3.4), "ocre", rng,
                 bouts=False, name="Toit")
    _chidori(b, 0.0, 6.5, yt + 0.2, 2.4 + 4.6 - 1.0, t["zm"], z1 + 1.6, "ocre", rng)
    top = t["top"]
    # tours d'angle sur les bastions
    for s in (-1, 1):
        top = max(top, _tourelle(b, rng, s, P + 0.5, XJ + 0.3, -12.5, -1.0, y0))
    return top


# ---------------------------------------------------------------------------
# Escalier
# ---------------------------------------------------------------------------
def _escalier(b, s, rng, XJ, D, y_haut, u_palier=75.2):
    """Deux volées en zigzag contre le mur (voie avant puis voie arrière), puis une volée taillée dans la
    colline (vers -Z) jusqu'à y_haut. Chaque marche est une colonne de pierre posée au sol."""
    ZL, ZF = 2.8, 5.8
    u0 = XJ + 0.5
    u_haut = XJ + 8.0
    y1 = 18.0
    n1 = 20
    g1 = (u_palier - u0) / n1
    pierres = _suite(rng, 64, ("pierre_claire", "pierre", "dallage_ombre"), 0.02)
    k = 0
    for i in range(1, n1 + 1):
        _bx(b, s, u0 + (i - 1) * g1, u0 + i * g1, 0, round(i * y1 / n1, 2), ZL, ZF, pierres[k], studs="top",
            name="Marche")
        k += 1
    _bx(b, s, u_palier, u_palier + 3.0, 0, y1, _z_face(y1), ZF, col("pierre"), studs="top", name="Palier")
    n2 = int(round(Y_MUR - y1))
    g2 = (u_palier - u_haut) / n2
    for j in range(1, n2 + 1):
        yj = y1 + j * (Y_MUR - y1) / n2
        _bx(b, s, u_palier - j * g2, u_palier - (j - 1) * g2, 0, yj, _z_face(yj), ZL, pierres[k], studs="top",
            name="Marche")
        k += 1
    _bx(b, s, XJ, u_haut, 0, Y_MUR, _z_face(Y_MUR), ZL, col("pierre"), studs="top", name="Palier")
    # volée taillée dans la colline
    n3 = int(round(y_haut - Y_MUR))
    for i in range(1, n3 + 1):
        _bx(b, s, XJ, u_haut, 0, Y_MUR + i, Z_MUR - i, Z_MUR - i + 1, pierres[k % len(pierres)], studs="top",
            name="Marche")
        k += 1
    z_fin = Z_MUR - n3
    _pile(b, s, XJ, u_haut, -D + RETRAIT_DOS, z_fin, 0, y_haut, STRATES_DOS, rng, name="Roche")
    # lanternes : palier intermédiaire, palier haut
    with b.at((s * (u_palier + 1.5), y1, ZL + 1.4)):
        mobilier.lanterne_poteau(b, variant=1, hauteur=4.2)
    with b.at((s * (u_haut - 1.6), Y_MUR, ZL - 1.2)):
        mobilier.lanterne_poteau(b, variant=1, hauteur=4.2)
    return {"z_fin": z_fin, "u": (XJ, u_haut)}


# ---------------------------------------------------------------------------
# Roche : piles en strates, saillies
# ---------------------------------------------------------------------------
def _pile(b, s, u0, u1, z0, z1, y0, y1, strates, rng, name="Roche", studs_haut=True):
    """Bloc découpé selon les strates horizontales (une pièce par strate, studs sur la dernière)."""
    morceaux = []
    for a, bb, t in strates:
        lo, hi = max(a, y0), min(bb, y1)
        if hi - lo > 1e-6:
            morceaux.append([lo, hi, t])
    i = 0
    while i < len(morceaux) and len(morceaux) > 1:
        lo, hi, t = morceaux[i]
        if hi - lo < 0.6:
            if i + 1 < len(morceaux):
                morceaux[i + 1][0] = lo
            else:
                morceaux[i - 1][1] = hi
            del morceaux[i]
            continue
        i += 1
    for j, (lo, hi, t) in enumerate(morceaux):
        haut = studs_haut and j == len(morceaux) - 1
        _bx(b, s, u0, u1, lo, hi, z0, z1, vr(TONS[t], rng, 0.025), studs="top" if haut else (), name=name)
    return len(morceaux)


# ---------------------------------------------------------------------------
# Végétation
# ---------------------------------------------------------------------------
def _pin(b, x, y, z, rng, s=1.0):
    """Pin japonais : tronc coudé, plateaux de feuillage en nuages (5 pièces)."""
    sg = float(rng.choice([-1, 1]))
    S = lambda v: v * s  # noqa: E731
    vert, vert_c = vr("pin", rng, 0.05), vr(mix(c("pin"), c("feuille"), 0.45), rng, 0.04)
    b.box((x - S(0.6), y, z - S(0.6)), (x + S(0.6), y + S(5.5), z + S(0.6)), c("tronc"), name="Tronc")
    b.box((x - sg * S(0.5) - S(0.5), y + S(5.5), z - S(0.5)), (x - sg * S(0.5) + S(0.5), y + S(8.6), z + S(0.5)),
          c("tronc_clair"), name="Tronc")
    b.box((x + sg * S(2.0) - S(3.3), y + S(4.4), z - S(2.6)), (x + sg * S(2.0) + S(3.3), y + S(5.8), z + S(2.6)),
          vert, studs="top", collide=False, name="Aiguilles")
    b.box((x - sg * S(1.0) - S(2.6), y + S(6.6), z - S(2.1)), (x - sg * S(1.0) + S(2.6), y + S(8.0), z + S(2.1)),
          vert_c, studs="top", collide=False, name="Aiguilles")
    b.box((x - sg * S(0.3) - S(1.6), y + S(8.6), z - S(1.4)), (x - sg * S(0.3) + S(1.6), y + S(9.8), z + S(1.4)),
          vert, studs="top", collide=False, name="Aiguilles")


def _cedre(b, x, y, z, rng, s=1.0):
    """Cèdre : tronc et étages carrés qui rétrécissent (6 pièces)."""
    S = lambda v: v * s  # noqa: E731
    b.box((x - S(0.6), y, z - S(0.6)), (x + S(0.6), y + S(3.0), z + S(0.6)), c("tronc"), name="Tronc")
    yy = y + S(2.4)
    for i, w in enumerate((6.4, 5.0, 3.6, 2.2)):
        h = S(2.6 if i < 3 else 2.2)
        cc = vr(mix(c("pin"), c("feuille_fonce"), 0.3 * (i % 2)), rng, 0.04)
        b.box((x - S(w / 2), yy, z - S(w / 2)), (x + S(w / 2), yy + h, z + S(w / 2)), cc, studs="top",
              collide=i == 0, name="Aiguilles")
        yy += h
    b.box((x - S(0.5), yy, z - S(0.5)), (x + S(0.5), yy + S(1.4), z + S(0.5)), vr("pin", rng, 0.04), studs="top",
          collide=False, name="Aiguilles")


# ---------------------------------------------------------------------------
# Grande tour blanche
# ---------------------------------------------------------------------------
def _fenetres(b, half, yr, h, pos, w=1.8, decal=0):
    """Fenêtres traversantes (une pièce par colonne et par direction, deux faces opposées), en alternance avec
    des panneaux d'enduit en retrait de ton plus sombre : une colonne sur deux (selon `decal`) est une fenêtre
    sombre à barreau central, les autres des panneaux blanc ombré (decal=None : toutes des fenêtres)."""
    for j, p in enumerate(pos):
        if decal is None or (j + decal) % 2 == 0:
            b.box((p - w / 2, yr, -half - 0.1), (p + w / 2, yr + h, half + 0.1), col("fenetre"), name="Fenetre")
            b.box((-half - 0.1, yr, p - w / 2), (half + 0.1, yr + h, p + w / 2), col("fenetre"), name="Fenetre")
            b.box((p - 0.18, yr + 0.05, -half - 0.25), (p + 0.18, yr + h - 0.05, half + 0.25), col("bois_fonce"),
                  collide=False, name="Barreau")
            b.box((-half - 0.25, yr + 0.05, p - 0.18), (half + 0.25, yr + h - 0.05, p + 0.18), col("bois_fonce"),
                  collide=False, name="Barreau")
        else:
            b.box((p - w / 2 - 0.2, yr - 0.2, -half - 0.1), (p + w / 2 + 0.2, yr + h + 0.2, half + 0.1),
                  col("blanc_ombre"), name="Panneau")
            b.box((-half - 0.1, yr - 0.2, p - w / 2 - 0.2), (half + 0.1, yr + h + 0.2, p + w / 2 + 0.2),
                  col("blanc_ombre"), name="Panneau")


def _etage(b, rng, half, y0, y1, rangs, bande=True, corniche="blanc_pur", pil=True):
    """Corps carré blanc : pilastres d'angle, rangs de fenêtres (alternées avec des panneaux), bande laquée
    rouge, corniche stud."""
    b.box((-half, y0, -half), (half, y1, half), vr("blanc", rng, 0.015), name="Tour_corps")
    if pil:
        for sx in (-1, 1):
            for sz in (-1, 1):
                b.box((sx * (half + 0.3), y0, sz * (half + 0.3)), (sx * (half - 1.5), y1, sz * (half - 1.5)),
                      col("blanc_pur"), name="Pilastre")
    for r, (yr, h, pos) in enumerate(rangs):
        _fenetres(b, half, yr, h, pos, decal=r % 2 if len(pos) > 2 else None)
    if bande:
        b.box((-half - 0.5, y1 - 3.4, -half - 0.5), (half + 0.5, y1 - 1.6, half + 0.5), col("laque_rouge"),
              name="Bande_rouge")
    if corniche:
        b.box((-half - 1.0, y1, -half - 1.0), (half + 1.0, y1 + 0.8, half + 1.0), col(corniche), studs="top",
              name="Corniche")
    return y1 + (0.8 if corniche else 0.0)


def _fleche(b, x, z, y0, etages, couleurs=("ardoise_fleche", "laque_noire")):
    """Flèche sombre en blocs empilés qui s'affinent : etages = [(demi_largeur, hauteur)]."""
    y = y0
    for i, (hw, h) in enumerate(etages):
        b.box((x - hw, y, z - hw), (x + hw, y + h, z + hw), col(couleurs[i % len(couleurs)]),
              studs="top" if i == 0 else (), collide=i < 2, name="Fleche")
        y += h
    return y


def _annexe(b, rng, x0, x1, z0, z1, y0, y1, rangs, avec_fleche=True):
    """Tour annexe accolée (corps blanc, fenêtres, bande rouge, corniche, chapeau sombre, flèche)."""
    b.box((x0, y0, z0), (x1, y1, z1), vr("blanc_creme", rng, 0.015), name="Annexe")
    xc, zc = (x0 + x1) / 2, (z0 + z1) / 2
    for yr in rangs:
        b.box((xc - 0.8, yr, z0 - 0.1), (xc + 0.8, yr + 2.8, z1 + 0.1), col("fenetre"), name="Fenetre")
        b.box((x0 - 0.1, yr, zc - 0.8), (x1 + 0.1, yr + 2.8, zc + 0.8), col("fenetre"), name="Fenetre")
    b.box((x0 - 0.5, y1 - 3.2, z0 - 0.5), (x1 + 0.5, y1 - 1.5, z1 + 0.5), col("laque_rouge"), name="Bande_rouge")
    b.box((x0 - 0.9, y1, z0 - 0.9), (x1 + 0.9, y1 + 0.8, z1 + 0.9), col("blanc_pur"), studs="top", name="Corniche")
    hw = min(x1 - x0, z1 - z0) / 2 - 0.6
    b.box((xc - hw, y1 + 0.8, zc - hw), (xc + hw, y1 + 2.6, zc + hw), col("laque_noire"), studs="top",
          name="Chapeau")
    top = y1 + 2.6
    if avec_fleche:
        top = _fleche(b, xc, zc, top, [(hw * 0.55, 3.5), (hw * 0.35, 3.5), (hw * 0.17, 2.6)])
    return top


def _aile(b, rng, x0, x1, z0, z1, y0, long_x=True):
    """Aile basse blanche à toit ocre en croupe : socle stud, corps en deux panneaux, fenêtres, toit."""
    b.box((x0, y0, z0), (x1, y0 + 1.0, z1), vr("pierre", rng, 0.03), studs="top", name="Aile_socle")
    xa, xb, za, zb = x0 + 0.6, x1 - 0.6, z0 + 0.6, z1 - 0.6
    yh = y0 + 6.5
    ca, cb = _suite(rng, 2, BLANCS)
    if long_x:
        xm = (xa + xb) / 2
        b.box((xa, y0 + 1.0, za), (xm, yh, zb), ca, name="Aile_mur")
        b.box((xm, y0 + 1.0, za), (xb, yh, zb), cb, name="Aile_mur")
        for f in (0.25, 0.75):
            xc = xa + f * (xb - xa)
            b.box((xc - 1.2, y0 + 3.0, za - 0.1), (xc + 1.2, y0 + 5.2, zb + 0.1), col("fenetre"), name="Fenetre")
    else:
        zm = (za + zb) / 2
        b.box((xa, y0 + 1.0, za), (xb, yh, zm), ca, name="Aile_mur")
        b.box((xa, y0 + 1.0, zm), (xb, yh, zb), cb, name="Aile_mur")
        for f in (0.25, 0.75):
            zc = za + f * (zb - za)
            b.box((xa - 0.1, y0 + 3.0, zc - 1.2), (xb + 0.1, y0 + 5.2, zc + 1.2), col("fenetre"), name="Fenetre")
    b.box((xa - 0.25, yh - 0.9, za - 0.25), (xb + 0.25, yh - 0.5, zb + 0.25), col("bois_fonce"), name="Aile_poutre")
    ax = min(xb - xa, zb - za) / 2 + 1.2
    a = (ax, ax, ax * 0.6, ax * 0.6) if long_x else (ax * 0.6, ax * 0.6, ax, ax)
    _jupe(b, xa - 1.4, xb + 1.4, za - 1.4, zb + 1.4, yh, 3.0, a, "ocre", rng, rive=None, coeur=True, name="Aile_toit")
    # faîtage court
    if long_x:
        b.box((xa - 1.4 + ax * 0.6 - 0.3, yh + 2.6, (za + zb) / 2 - 0.6),
              (xb + 1.4 - ax * 0.6 + 0.3, yh + 3.5, (za + zb) / 2 + 0.6), col("ocre_brun"), studs="top",
              name="Aile_faite")
    else:
        b.box(((xa + xb) / 2 - 0.6, yh + 2.6, za - 1.4 + ax * 0.6 - 0.3),
              ((xa + xb) / 2 + 0.6, yh + 3.5, zb + 1.4 - ax * 0.6 + 0.3), col("ocre_brun"), studs="top",
              name="Aile_faite")


def _tour(b, rng, y0, s_out):
    """Grande tour blanche (repère local centré sur la tour, au niveau y0 de la terrasse). Renvoie le sommet."""
    ext = 19.5
    xa, xb = sorted((-15.0 * s_out, ext * s_out))
    b.box((xa, y0, -15.0), (xb, y0 + 2.5, 15.0), vr("pierre_fonce", rng, 0.02), studs="top", name="Tour_socle")
    b.box((xa + 0.9, y0 + 2.5, -14.1), (xb - 0.9, y0 + 5.0, 14.1), vr("pierre", rng, 0.02), studs="top",
          name="Tour_socle")
    yb = y0 + 5.0
    # corps 1
    y = _etage(b, rng, 11.0, yb, yb + 26.0,
               [(yb + 4.5, 3.2, (-6.0, 6.0)), (yb + 11.0, 3.2, (-6.0, 0.0, 6.0)), (yb + 17.5, 3.2, (-6.0, 0.0, 6.0))])
    # porte d'entrée (face +Z) sous un auvent ocre
    b.box((-2.2, yb, 11.0), (2.2, yb + 6.0, 11.25), col("bois_fonce"), name="Porte")
    b.box((-2.8, yb + 6.0, 11.0), (2.8, yb + 6.6, 11.4), col("laque_rouge"), name="Porte_linteau")
    b.wedge((-3.4, yb + 6.6, 11.0), (3.4, yb + 7.8, 13.2), vr("ocre", rng, 0.02), down="+z", studs="top",
            name="Auvent")
    # jupe de tuiles ocre sur la corniche du premier corps (tour japonaise plutôt qu'immeuble)
    _jupe(b, -12.4, 12.4, -12.4, 12.4, y, 1.7, (2.9, 2.9, 2.9, 2.9), "ocre", rng, sous=None, coeur=False,
          name="Jupe_tour")
    y = _etage(b, rng, 9.5, y, y + 19.0, [(y + 4.0, 3.2, (-5.0, 0.0, 5.0)), (y + 10.5, 3.2, (-5.0, 0.0, 5.0))])
    _jupe(b, -10.9, 10.9, -10.9, 10.9, y, 1.4, (2.9, 2.9, 2.9, 2.9), "ocre", rng, sous=None, coeur=False,
          name="Jupe_tour")
    y = _etage(b, rng, 8.0, y, y + 13.0, [(y + 3.6, 3.0, (-3.5, 3.5)), (y + 7.6, 1.6, (-3.5, 3.5))], corniche=None)
    # balcon laqué rouge
    b.box((-10.5, y, -10.5), (10.5, y + 0.7, 10.5), col("laque_rouge_fonce"), studs="top", name="Balcon_tour")
    yb2 = y + 0.7
    for px in (-10.0, 0.0, 10.0):
        for pz in (-10.0, 0.0, 10.0):
            if px == 0.0 and pz == 0.0:
                continue
            b.box((px - 0.3, yb2, pz - 0.3), (px + 0.3, yb2 + 2.8, pz + 0.3), col("laque_rouge"), collide=False,
                  name="Balcon_poteau")
    for sgn in (-1, 1):
        b.box((-10.2, yb2 + 2.2, sgn * 10.0 - 0.2), (10.2, yb2 + 2.6, sgn * 10.0 + 0.2), col("laque_noire"),
              collide=False, name="Balcon_rail")
        b.box((sgn * 10.0 - 0.2, yb2 + 2.2, -9.8), (sgn * 10.0 + 0.2, yb2 + 2.6, 9.8), col("laque_noire"),
              collide=False, name="Balcon_rail")
    # corps 4 (lanterne de la tour) et couronne
    y = _etage(b, rng, 6.2, yb2, yb2 + 9.0, [(yb2 + 1.8, 3.2, (-2.6, 2.6))], corniche="ardoise_fleche")
    top = _fleche(b, 0.0, 0.0, y, [(2.8, 6.4), (2.1, 6.0), (1.5, 5.5), (1.0, 5.0), (0.55, 4.2)])
    b.ball((0.0, top + 0.5, 0.0), 0.7, col("or"), collide=False, name="Fleche_pointe")
    top += 1.2
    for sx in (-1, 1):
        for sz in (-1, 1):
            _fleche(b, sx * 5.2, sz * 5.2, y, [(1.15, 5.4), (0.8, 4.0), (0.45, 3.5)])
    for (px, pz) in ((0.0, 5.6), (0.0, -5.6), (5.6, 0.0), (-5.6, 0.0)):
        _fleche(b, px, pz, y, [(0.8, 3.9), (0.45, 3.0)])
    # tours annexes : côté extérieur (haute) et arrière (plus basse)
    ax0, ax1 = sorted((11.0 * s_out, 18.0 * s_out))
    _annexe(b, rng, ax0, ax1, -4.5, 4.5, yb, yb + 36.0, [yb + 7.0, yb + 15.0, yb + 23.0])
    _annexe(b, rng, -5.0, 5.0, -14.0, -11.0, yb, yb + 29.0, [yb + 9.0, yb + 18.0])
    return top


# ---------------------------------------------------------------------------
# Monolithe
# ---------------------------------------------------------------------------
def _monolithe(b, rng, y0, top):
    """Pierre sacrée (iwakura) naturelle sur sa terrasse (repère local centré sur le monolithe, y0 = terrasse) :
    masse large à la base (≈ 28 × 18) qui se resserre vers 18 en haut, faite de cinq colonnes de pierre grise et
    chaude accolées, de hauteurs et de fruits différents (blocs empilés un peu décalés, tons clairs et sombres en
    facettes), fissure verticale sombre entre deux colonnes, longues arêtes claires en saillie, sommet coupé en
    biais (coins), jupe d'éboulis au pied ; corde sacrée épaisse et affaissée vers le quart de la hauteur, avec
    de grands papiers en zigzag (shide) et des franges de paille."""
    b.box((-15.5, y0, -12.5), (15.5, y0 + 1.5, 12.5), vr("pierre_fonce", rng, 0.02), studs="top", name="Terrasse")
    b.box((-14.2, y0 + 1.5, -11.2), (14.2, y0 + 3.0, 11.2), vr("pierre", rng, 0.02), studs="top", name="Terrasse")
    yb = y0 + 3.0
    H = top - yb
    clair = mix(c("monolithe"), c("monolithe_clair"), 0.7)
    sombre = mix(c("monolithe"), c("monolithe_fonce"), 0.75)
    tons = (c("monolithe"), c("monolithe"), clair, sombre, c("monolithe"), clair)
    # (x0, x1, demi-profondeur, décalage z, sommet, fruit par bloc côté extérieur, côté extérieur)
    colonnes = [(-13.6, -8.4, 6.6, 0.2, yb + H * 0.5 + float(rng.choice([-4, 0, 4])), 0.45, -1),
                (-8.4, -2.6, 8.4, 0.3, top - float(rng.choice([12, 15, 18])), 0.12, -1),
                (-2.0, 4.2, 8.8, -0.2, top, 0.0, 0),
                (4.2, 9.4, 8.0, 0.4, top - float(rng.choice([6, 8, 10])), 0.12, 1),
                (9.4, 13.6, 6.4, -0.5, yb + H * 0.38 + float(rng.choice([-4, 0, 4])), 0.5, 1)]
    blocs = []          # (x0, x1, z0, z1, y0, y1, côté)
    sommets = []        # dernier bloc de chaque colonne
    for (x0, x1, hd, oz, yt, fruit, cote) in colonnes:
        y = yb
        k = 0
        while y < yt - 1e-6:
            h = float(rng.choice([8, 10, 12, 14, 16]))
            if yt - (y + h) < 5:
                h = yt - y
            fr = fruit * k + float(rng.choice([-0.3, 0.0, 0.3])) * (k > 0) * (fruit > 0)
            xa = x0 + (fr if cote < 0 else 0.0)
            xb = x1 - (fr if cote > 0 else 0.0)
            hdk = hd - 0.18 * k
            za = oz - hdk + float(rng.choice([-0.6, -0.3, 0.0, 0.3, 0.6]))
            zb = oz + hdk + float(rng.choice([-0.6, -0.3, 0.0, 0.3]))
            tone = tons[int(rng.integers(0, len(tons)))]
            b.box((xa, y, za), (xb, y + h, zb), vr(tone, rng, 0.025), name="Monolithe")
            blocs.append((xa, xb, za, zb, y, y + h, cote))
            y += h
            k += 1
        sommets.append(blocs[-1])
    # fissure verticale sombre (0,6) entre la deuxième et la troisième colonne, en retrait des faces
    yf = min(colonnes[1][4], colonnes[2][4]) - 14.0
    b.box((-2.6, yb, -6.0), (-2.0, yf, 6.0), vr("monolithe_fonce", rng, 0.02), name="Fissure")
    # sommets coupés en biais : coins de pierre (jamais une pointe), mousse sur les colonnes basses
    for j, (xa, xb, za, zb, ya, yt, cote) in enumerate(sommets):
        if j in (0, 4):
            b.box((xa + 0.4, yt, za + 0.8), (xb - 0.3, yt + 0.6, zb - 1.5), vr("mousse", rng, 0.05), studs="top",
                  collide=False, name="Mousse")
            continue
        hh = (5.0, 4.0, 3.0)[j - 1]
        down = ("-x", "+z", "+x")[j - 1]
        b.wedge((xa + 0.2, yt, za + 0.4), (xb - 0.2, yt + hh, zb - 0.4), vr(clair if j == 2 else c("monolithe"), rng,
                0.03), down=down, studs="top", name="Monolithe_sommet")
    # lichen au pied, côté avant
    for xl in (-7.0, 2.0):
        b.box((xl, yb, 7.6), (xl + float(rng.uniform(2.5, 4.0)), yb + float(rng.uniform(1.6, 2.6)), 9.6),
              vr("lichen", rng, 0.05), studs="top", collide=False, name="Lichen")
    # jupe d'éboulis : blocs bas de roche qui se fondent dans la roche de la colline
    for (xa, xb, za, zb, h, ton) in ((-15.4, -13.0, -9.0, 1.0, 4.5, "roche_fonce"), (-15.0, -11.0, -12.4, -6.0, 3.0, "roche"),
                                     (13.0, 15.4, -6.0, 3.5, 3.6, "roche"), (11.0, 15.2, -12.4, -5.0, 5.0, "roche_fonce"),
                                     (-6.5, -2.5, 8.6, 11.0, 1.8, "roche_claire"), (4.0, 8.5, 8.2, 10.6, 2.6, "roche"),
                                     (-4.0, 6.0, -12.2, -8.4, 4.0, "roche_fonce")):
        b.box((xa, yb, za), (xb, yb + h, zb), vr(ton, rng, 0.03), studs="top", name="Eboulis")
    # arêtes claires : longues saillies verticales sur les faces avant et extérieures (pas de carrés sombres)
    poses = []
    for _ in range(10):
        xa, xb, za, zb, ya, yb_, cote = blocs[int(rng.integers(0, len(blocs)))]
        if any(abs(ya - q[0]) < 1e-6 and abs(xa - q[1]) < 1e-6 for q in poses):
            continue            # une arête par bloc au plus
        poses.append((ya, xa))
        bw, bh = float(rng.choice([1.2, 1.6, 2.0])), float(rng.choice([6.0, 8.0, 10.0]))
        if yb_ - ya < bh + 1 or xb - xa < bw + 1:
            continue
        by = ya + float(rng.uniform(0.5, yb_ - ya - bh - 0.5))
        sa = float(rng.choice([0.6, 0.8, 1.0]))
        if cote and rng.random() < 0.5:        # sur la face extérieure
            xe = xa if cote < 0 else xb
            bz = za + float(rng.uniform(0.5, zb - za - bw - 0.5))
            x0b, x1b = sorted((xe - cote * 0.3, xe + cote * sa))
            b.box((x0b, by, bz), (x1b, by + bh, bz + bw), vr(clair, rng, 0.03), name="Arete")
        else:                                  # sur la face avant
            bx = xa + float(rng.uniform(0.5, xb - xa - bw - 0.5))
            b.box((bx, by, zb - 0.3), (bx + bw, by + bh, zb + sa), vr(clair, rng, 0.03), name="Arete")
    # corde sacrée vers le quart de la hauteur, épaisse, serrée contre la roche, affaissée devant et derrière
    y_r = yb + H / 4.0
    joints = {round(bl[4], 2) for bl in blocs} | {round(bl[5], 2) for bl in blocs}
    for dy in np.arange(0.0, 20.0, 0.5):           # la corde ne tombe pas sur un joint
        ok = [cand for cand in (y_r + dy, y_r - dy) if all(abs(cand - j) >= 2.8 for j in joints)]
        if ok:
            y_r = float(ok[0])
            break
    autour = [bl for bl in blocs if bl[4] <= y_r <= bl[5]]
    xa_r = min(bl[0] for bl in autour)
    xb_r = max(bl[1] for bl in autour)
    za_r = min(bl[2] for bl in autour)
    zb_r = max(bl[3] for bl in autour)
    cx, cz = (xa_r + xb_r) / 2, (za_r + zb_r) / 2
    hw, hd = (xb_r - xa_r) / 2, (zb_r - za_r) / 2
    affaisse = 3.2
    for (rr, dy, ton) in ((2.0, 0.0, "corde"), (1.1, 1.9, mix(c("corde"), c("ocre_brun"), 0.25))):
        ex, ez = hw + rr - 1.2, hd + rr - 1.2
        for sz in (-1, 1):                      # devant et derrière : deux brins qui descendent vers le milieu
            for sx in (-1, 1):
                x_a, y_a = cx + sx * ex, y_r + dy
                x_b, y_b = cx, y_r + dy - affaisse
                L = math.hypot(x_a - x_b, y_a - y_b) + rr * 0.6
                a = math.degrees(math.atan2(y_a - y_b, x_a - x_b))
                b.part("cyl", (L, 2 * rr, 2 * rr), ((x_a + x_b) / 2, (y_a + y_b) / 2, cz + sz * ez), rot_z(a),
                       col(ton), collide=False, name="Corde")
        for sx in (-1, 1):
            b.cyl((cx + sx * ex, y_r + dy, cz), rr, 2 * ez, col(ton), axis="z", collide=False, name="Corde")
        for sx in (-1, 1):
            for sz in (-1, 1):
                b.ball((cx + sx * ex, y_r + dy, cz + sz * ez), rr * 1.05, col(ton), collide=False, name="Corde_noeud")
    ez = hd + 2.0 - 1.2 + 0.4

    def shide(x, z, y_haut, axe):
        for k, ddx in enumerate((0.0, 0.7, 0.0)):
            ya = y_haut - 2.2 * (k + 1)
            if axe == "x":
                b.box((x + ddx - 0.9, ya, z - 0.1), (x + ddx + 0.9, ya + 2.2, z + 0.1), col("shide"), collide=False,
                      shadow=False, name="Shide")
            else:
                b.box((x - 0.1, ya, z + ddx - 0.9), (x + 0.1, ya + 2.2, z + ddx + 0.9), col("shide"), collide=False,
                      shadow=False, name="Shide")
    for f in (-0.7, -0.3, 0.3, 0.7):
        yh = y_r - 1.6 - affaisse * (1 - abs(f))
        shide(cx + f * (hw + 0.8), cz + ez, yh, "x")
    for sx in (-1, 1):
        shide(cx + sx * (hw + 2.0 - 1.2 + 0.4), cz, y_r - 1.8, "z")
    for f in (-0.5, 0.0, 0.5):
        yh = y_r - 1.6 - affaisse * (1 - abs(f))
        b.box((cx + f * hw - 0.4, yh - 3.6, cz + ez - 0.5), (cx + f * hw + 0.4, yh, cz + ez + 0.3), col("chaume"),
              collide=False, name="Frange")
    return blocs


def _tourelle(b, rng, s, u0, u1, z0, z1, y0):
    """Tour d'angle blanche (sumi-yagura) sur un bastion du portail : grand étage à deux rangs de fenêtres,
    auvent ocre, étage haut en retrait, toit irimoya. Renvoie le sommet."""
    H1, H2 = 17.0, 6.5
    um, zm = (u0 + u1) / 2, (z0 + z1) / 2
    _bx(b, s, u0, u1 + 0.1, y0, y0 + 1.0, z0 - 0.2, z1 + 0.2, col("bois_fonce"), name="Seuil")
    ca, cb = _suite(rng, 2, BLANCS)
    _bx(b, s, u0, u1, y0 + 1.0, y0 + H1, z0, zm, ca, name="Enduit")
    _bx(b, s, u0, u1, y0 + 1.0, y0 + H1, zm, z1, cb, name="Enduit")
    for yr in (y0 + 4.5, y0 + 11.0):
        _bx(b, s, um - 1.3, um + 1.3, yr, yr + 3.0, z0 - 0.1, z1 + 0.1, col("fenetre"), name="Fenetre")
        _bx(b, s, u0 - 0.1, u1 + 0.1, yr, yr + 3.0, zm - 1.3, zm + 1.3, col("fenetre"), name="Fenetre")
    ye = y0 + H1
    xa, xb = sorted((s * (u0 - 1.4), s * (u1 + 1.4)))
    _jupe(b, xa, xb, z0 - 1.4, z1 + 1.4, ye, 1.6, (2.0, 2.0, 2.0, 2.0), "ocre", rng, rive=None, coeur=False,
          name="Auvent")
    _bx(b, s, u0 + 0.6, u1 - 0.6, ye, ye + H2, z0 + 0.6, z1 - 0.6, vr("blanc", rng, 0.015), name="Enduit")
    _bx(b, s, um - 1.0, um + 1.0, ye + 2.2, ye + 4.6, z0 + 0.5, z1 - 0.5, col("fenetre"), name="Fenetre")
    _bx(b, s, u0 + 0.5, u1 - 0.5, ye + 2.2, ye + 4.6, zm - 1.0, zm + 1.0, col("fenetre"), name="Fenetre")
    xa, xb = sorted((s * (u0 - 0.4), s * (u1 + 0.4)))
    t = _irimoya(b, xa, xb, z0 - 0.4, z1 + 0.4, ye + H2, 1.8, 3.4, (2.2, 2.2, 2.4, 2.4), "ocre", rng, rive=None,
                 h_orn=1.6, name="Toit_tour")
    return t["top"]


def _grille(v):
    """Cale v sur la grille 0,13 + k × 0,25 du feuillage : jamais sur la grille du demi-stud de la roche."""
    return round((v - 0.13) * 4) / 4 + 0.13


def _distinct(v, pris, ecart=0.2):
    """Cale v sur la grille du feuillage puis le décale (pas de 0,25) jusqu'à ce qu'il soit à plus de `ecart`
    de toutes les valeurs déjà prises."""
    v = _grille(v)
    for _ in range(12):
        if all(abs(v - q) >= ecart for q in pris):
            break
        v += 0.25
    pris.append(v)
    return v


def _massif(b, x0, x1, z0, z1, y, rng, h=10.0, rose=False, bornes=None):
    """Masse d'arbres en gros blocs qui couvre le rectangle : socle sombre, lobes de hauteurs variées qui
    débordent un peu, dessus clairs (5 à 9 pièces). `bornes` = (xmin, xmax, zmin, zmax) à ne pas dépasser.
    Aucune face de deux blocs du massif n'est exactement dans le même plan (pas de scintillement)."""
    tons = SAKURAS if rose else FEUILLES
    clair = c("sakura_pale") if rose else DESSUS_CLAIR
    w, d = x1 - x0, z1 - z0
    if w < 2 or d < 2:
        return
    xmin, xmax, zmin, zmax = bornes or (-1e9, 1e9, -1e9, 1e9)
    hs = _grille(y + 0.45 * h) - y
    px, pz, py = [_grille(x0 + 0.1)], [_grille(z0 + 0.1)], [y + hs]
    px.append(_grille(x1 - 0.1))
    pz.append(_grille(z1 - 0.1))
    b.box((px[0], y, pz[0]), (px[1], y + hs, pz[1]), vr(tons[0], rng, 0.04), studs="top", name="Feuillage")
    n = int(np.clip(round(w * d / 60.0), 2, 4))
    lobes = []
    for i in range(n):
        lw = w * float(rng.uniform(0.4, 0.7))
        ld = d * float(rng.uniform(0.45, 0.8))
        lx = float(np.clip(x0 + rng.uniform(-0.7, w - lw + 0.7), xmin + rng.uniform(0, 0.2), xmax - lw - rng.uniform(0, 0.2)))
        lz = float(np.clip(z0 + rng.uniform(-0.7, d - ld + 0.7), zmin + rng.uniform(0, 0.2), zmax - ld - rng.uniform(0, 0.2)))
        lx0 = _distinct(lx, px)
        lx1 = _distinct(min(lx + lw, xmax), px) if lx + lw + 0.5 < xmax else _distinct(lx + lw - 0.5, px)
        lz0 = _distinct(lz, pz)
        lz1 = _distinct(min(lz + ld, zmax), pz) if lz + ld + 0.5 < zmax else _distinct(lz + ld - 0.5, pz)
        yt = _distinct(y + h * float(rng.uniform(0.62, 1.0)), py)
        ly = y + hs * float(rng.uniform(0.25, 0.7))
        b.box((lx0, ly, lz0), (lx1, yt, lz1), vr(tons[1 + i % 2], rng, 0.04), studs="top", collide=False,
              name="Feuillage")
        lobes.append((lx0, lz0, lx1 - lx0, lz1 - lz0, yt))
    for (lx, lz, lw, ld, yt) in sorted(lobes, key=lambda t: -t[4])[:2]:
        tw, td = 0.5 * lw, 0.5 * ld
        tx = _distinct(lx + float(rng.uniform(0.15, 0.35)) * lw, px)
        tz = _distinct(lz + float(rng.uniform(0.15, 0.35)) * ld, pz)
        tx1, tz1 = _distinct(tx + tw, px), _distinct(tz + td, pz)
        yh = _distinct(yt + float(rng.choice([1.0, 1.4, 1.8])), py)
        b.box((tx, yt - 0.4, tz), (tx1, yh, tz1), vr(clair, rng, 0.03), studs="top", collide=False, name="Feuillage")


# ---------------------------------------------------------------------------
# Mesures
# ---------------------------------------------------------------------------
def _mesures(b, n0) -> dict:
    """Hauteur, débord avant et bornes réelles, mesurés sur les pièces posées (repère de l'asset)."""
    R = np.asarray(b._R[-1])
    t = np.asarray(b._t[-1])
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    for p in b.parts[n0:]:
        Rp = np.asarray(p.rot).reshape(3, 3)
        half = np.abs(Rp) @ (np.asarray(p.size) / 2)
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    q = R.T @ (np.asarray(p.pos) + np.array([sx, sy, sz]) * half - t)
                    lo, hi = np.minimum(lo, q), np.maximum(hi, q)
    return {"hauteur": round(float(hi[1]), 1), "debord_avant": round(float(hi[2]), 2),
            "bornes": [[round(float(v), 2) for v in lo], [round(float(v), 2) for v in hi]]}


# ---------------------------------------------------------------------------
# Fonction publique
# ---------------------------------------------------------------------------
def colline_tour(b, variant: int = 0, passage: float = 96, largeur: float = 420, profondeur: float = 46,
                 hauteur: float = 46, sol_tunnel: float = 36, appuis=(80, 150), texte: str = "門") -> dict:
    """Colline de la grande tour blanche et du monolithe, percée du tunnel de sortie (voir l'en-tête).

    passage : largeur libre du tunnel (|x| < passage/2 vide jusqu'à y = 38) ; sol_tunnel : demi-largeur du sol
    du tunnel déjà posé par zone.py ; appuis : |x| des murs qui viennent buter contre la colline (cour, remparts).
    Si le tirage dépasse le budget, la colline est reconstruite avec moins d'arbres et de saillies."""
    if texte not in ("門", "静"):
        texte = "門"
    n0 = len(b.parts)
    graine = int(b.rng.integers(0, 1 << 30))
    info = {}
    for dens in (1.0, 0.85, 0.7, 0.55, 0.4, 0.25):
        info = _colline(b, variant, passage, largeur, profondeur, hauteur, dens, graine, sol_tunnel, appuis, texte)
        if len(b.parts) - n0 <= BUDGET or dens <= 0.25:
            break
        del b.parts[n0:]
    info["pieces"] = len(b.parts) - n0
    info.update(_mesures(b, n0))
    return info


def _colline(b, variant, passage, largeur, profondeur, hauteur, dens, graine, sol_tunnel, appuis, texte) -> dict:
    rng = np.random.default_rng(graine + 97 * variant)
    v = variant % 4
    P = passage / 2.0
    W = largeur / 2.0
    D = profondeur
    H = hauteur
    XJ = P + 8.0                         # bord extérieur des bastions du portail
    s_t = -1 if v % 2 == 0 else 1        # côté de la tour
    s_m = -s_t                           # côté du monolithe
    s_e = s_t if v in (0, 1) else s_m    # côté de l'escalier
    u_plein = min(156.0, 0.74 * W)
    X_T, Z_T = XJ + 22.0, -min(30.0, D - 16.0)
    X_M, Z_M = XJ + 22.0, -min(28.0, D - 18.0)
    H_T = H                              # terrasse de la tour
    H_M = H - 6.0                        # terrasse du monolithe
    ZB = -14.0                           # front des terrasses de la tour et du monolithe
    fin_tour = min(W - 6.0, X_T + 38.0)
    fin_mono = min(W - 6.0, X_M + 22.0)
    BORNES = (-W + 0.3, W - 0.3, -D + 0.3, Z_MUR + 0.6)

    # -- portail, tunnel, corps de garde ------------------------------------------------
    with b.group("Portail"):
        _bastions(b, rng, P, XJ)
    with b.group("Tunnel"):
        _tunnel(b, rng, P, XJ, D, sol_tunnel)
    with b.group("CorpsDeGarde"):
        top_porte = _corps_de_garde(b, rng, P, XJ, texte)

    def rect(s, u0, u1, z0, z1):
        x0, x1 = sorted((s * u0, s * u1))
        return (x0, x1, z0, z1)

    # emprises bâties (sans arbres)
    exclus = [(-XJ - 1, XJ + 1, Z_BASTION - 1.5, 8.0),
              rect(s_t, X_T - 16, X_T + 20.5, Z_T - 16, Z_T + 15.2),        # socle de la tour
              rect(s_t, X_T + 21, X_T + 37, Z_T - 13, Z_T + 11),            # aile extérieure
              rect(s_t, XJ - 7, XJ + 7, -D, Z_T - 1),                       # aile arrière
              rect(s_m, X_M - 16, X_M + 16, Z_M - 13, Z_M + 13),            # terrasse du monolithe
              rect(s_m, X_M - 8, X_M + 8, ZB - 1, Z_MUR + 1),               # marches du monolithe
              rect(s_e, XJ - 0.5, XJ + 8.5, -D, 8.0)]                       # escalier

    def libre(x0, x1, z0, z1):
        if x0 < -W + 0.3 or x1 > W - 0.3 or z0 < -D + 0.3:
            return False
        for (a0, a1, c0, c1) in exclus:
            if x0 < a1 and x1 > a0 and z0 < c1 and z1 > c0:
                return False
        return True

    vege = []     # (x0, x1, z0, z1, y, h, rose) : massifs posés après la roche

    def massif(x0, x1, z0, z1, y, h, p=1.0, rose=None):
        if rng.random() > p * dens or not libre(x0, x1, z0, z1):
            return False
        if rose is None:
            rose = rng.random() < 0.16
        vege.append((x0, x1, z0, z1, y, h, rose))
        exclus.append((x0, x1, z0, z1))
        return True

    conif = []    # (x, y, z, sorte, échelle)

    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        tour = s == s_t
        # -- mur de soutènement, dobei, appuis -----------------------------------------
        with b.group(f"Mur/{cote}"):
            _mur(b, s, rng, XJ, W, u_plein)
            ua = XJ + 8.0 if s == s_e else XJ
            _dobei(b, s, rng, ua, u_plein)
            for u in appuis:
                if XJ + 10 < u < W - 4:
                    _appui(b, s, rng, u, min(_h_mur(u, W, u_plein), 19.0 if u < 100 else Y_MUR))
        # -- colonnes de la colline --------------------------------------------------------
        cols = []
        u = XJ
        if s == s_e:
            cols.append({"u0": XJ, "u1": XJ + 8.0, "kind": "escalier"})
            u = XJ + 8.0
        fin = fin_tour if tour else fin_mono
        n = max(1, int(round((fin - u) / 12.0)))
        w = (fin - u) / n
        for i in range(n):
            cols.append({"u0": u + i * w, "u1": u + (i + 1) * w, "kind": "tour" if tour else "mono"})
        u = fin
        while u < W - 1e-6:
            nx = u + float(rng.choice([10, 12, 14, 16]))
            if W - nx < 7:
                nx = W
            cols.append({"u0": u, "u1": nx, "kind": "flanc"})
            u = nx
        with b.group(f"Colline/{cote}"):
            for m in cols:
                u0, u1 = m["u0"], m["u1"]
                hw = _h_mur(u0, W, u_plein)
                if m["kind"] == "escalier":
                    with b.group("Escalier"):
                        _escalier(b, s, rng, XJ, D, H_T if tour else H_M)
                    continue
                zc = None
                if m["kind"] == "tour":
                    hB, hC, zb = H_T - 8.0, H_T, ZB
                elif m["kind"] == "mono":
                    hB, hC, zb = H_M - 4.0, H_M, ZB
                else:
                    um = (u0 + u1) / 2
                    t = (um - fin) / max(1.0, W - fin)
                    hC = 2 * round((H - 4 - (H - 24) * t) / 2) + float(rng.choice([-2, 0, 2]))
                    hB = hC - float(rng.choice([4, 6, 8]))
                    hB = max(hB, hw + 2.0)
                    hC = max(hC, hB + 2.0)
                    zb = -float(rng.choice([12, 14, 16]))
                    hD = hC + float(rng.choice([0, 2, 4, 6, 8]))
                    if hD > hC:
                        zc = max(-D + 10.0, zb - float(rng.choice([6, 8, 10, 12])))
                # gradin intermédiaire : cœur caché derrière le mur, strates fines au-dessus
                yc = min(_h_mur(u1, W, u_plein), hB - 1.0)
                _bx(b, s, u0, u1, 0, yc, zb, Z_MUR, vr("roche_fonce", rng, 0.02), name="Roche_coeur")
                _pile(b, s, u0, u1, zb, Z_MUR, yc, hB, STRATES_FINES, rng)
                # plateau : cœur sombre puis strates (dos visible depuis la zone suivante)
                _pile(b, s, u0, u1, -D + RETRAIT_DOS, zb, 0, hC, STRATES_DOS, rng)
                # butte (gradin arrière plus haut)
                if zc is not None:
                    _pile(b, s, u0, u1, -D + RETRAIT_DOS, zc, hC, hD, STRATES_DOS, rng)
                # saillies rocheuses devant le plateau et la butte
                for (zf, ybas, yhaut, nmax) in ((zb, hB, hC, 2), (zc, hC, hD if zc is not None else hC, 1)):
                    if zf is None or m["kind"] != "flanc":
                        continue
                    nb = int(rng.integers(0, nmax + 1))
                    pris = []
                    for _ in range(nb):
                        if rng.random() > 0.5 + 0.5 * dens:
                            continue
                        lw = float(rng.choice([4, 5, 6, 8]))
                        if u1 - u0 < lw + 1:
                            continue
                        a = u0 + float(rng.uniform(0.5, u1 - u0 - lw - 0.5))
                        if any(a < pb + 0.5 and a + lw > pa - 0.5 for (pa, pb) in pris):
                            continue
                        pris.append((a, a + lw))
                        sa = float(rng.choice([1.5, 2.0, 2.5, 3.0]))
                        hh = max(2.0, (yhaut - ybas) * float(rng.uniform(0.5, 1.0)) + float(rng.choice([0, 0, 2, 3])))
                        hh = round(hh * 2) / 2
                        a = round(a * 2) / 2
                        for yref in (hC, hD if zc is not None else hC, hB):
                            if abs(ybas + hh - yref) < 0.4:
                                hh += 0.8
                        zfront = min(zf + sa, Z_MUR - 0.5) if zf == zb else zf + sa
                        _bx(b, s, a, a + lw, ybas, ybas + hh, zf - float(rng.choice([0.8, 1.2, 1.6])), zfront,
                            vr(["roche_claire", "roche", "roche_claire"][int(rng.integers(0, 3))], rng, 0.03),
                            studs="top", name="Saillie")
                # arbres
                x0, x1 = sorted((s * (u0 + 0.4), s * (u1 - 0.4)))
                massif(x0, x1, zb - 0.3, Z_MUR + 0.3, hB, float(rng.choice([5, 6, 7, 8])),
                       p=0.85 if m["kind"] != "mono" else 0.7)
                if m["kind"] == "flanc":
                    if zc is not None:
                        massif(x0, x1, zc + 0.3, zb - 1.0, hC, float(rng.choice([5, 6, 7])), p=0.45)
                        ztop0, ytop = zc - 0.6, hD
                    else:
                        ztop0, ytop = zb - 1.0, hC
                    prof = ztop0 - (-D + 0.6)
                    ua_, ub_ = u0 + 0.4, u1 - 0.4          # emprise du massif arrière
                    sorte = "pin" if rng.random() < 0.4 else "cedre"
                    ech = float(rng.choice([1.1, 1.3])) if sorte == "pin" else float(rng.choice([1.4, 1.7, 2.0]))
                    demi_x = (5.3 if sorte == "pin" else 3.2) * ech + 0.2
                    demi_z = (2.6 if sorte == "pin" else 3.2) * ech + 0.3
                    if rng.random() < 0.4 * dens + 0.1 and u1 - u0 >= 2 * demi_x + 4:   # un conifère au fond
                        if rng.random() < 0.5:
                            uc, ua_ = u0 + demi_x, u0 + 2 * demi_x + 0.4
                        else:
                            uc, ub_ = u1 - demi_x, u1 - 2 * demi_x - 0.4
                        conif.append((s * uc, ytop, -D + demi_z, sorte, ech))
                    xa_, xb_ = sorted((s * ua_, s * ub_))
                    if prof > 18:
                        zm_ = ztop0 - prof * float(rng.uniform(0.4, 0.6))
                        massif(x0, x1, zm_ + 0.4, ztop0, ytop, float(rng.choice([7, 8, 10])), p=0.85)
                        massif(xa_, xb_, -D + 0.6, zm_ - 0.4, ytop, float(rng.choice([9, 11, 13])), p=0.85)
                    else:
                        massif(xa_, xb_, -D + 0.6, ztop0, ytop, float(rng.choice([8, 10, 12])), p=0.9)

    # aires boisées des terrasses de la tour et du monolithe
    def zone(s, u0, u1, z0, z1, y, h, p=1.0):
        if u1 - u0 >= 3 and z1 - z0 >= 3:
            x0, x1 = sorted((s * u0, s * u1))
            massif(x0, x1, z0, z1, y, h, p=p)

    u_t0 = XJ + 8.0 if s_e == s_t else XJ
    zone(s_t, X_T + 20.5, fin_tour - 0.4, ZB - 5.0, ZB - 0.4, H_T, 6.0)                 # devant l'aile
    zone(s_t, X_T + 20.5, fin_tour - 0.4, -D + 0.6, Z_T - 13.5, H_T, 8.0)                # derrière l'aile
    zone(s_t, u_t0 + 0.4, X_T - 16.5, Z_T - 0.5, ZB - 0.4, H_T, 8.0)                     # entre aile et tour
    u_m0 = XJ + 8.0 if s_e == s_m else XJ
    zone(s_m, X_M + 16.5, fin_mono - 0.4, -D + 0.6, ZB - 0.4, H_M, 14.0)                 # grande masse
    zone(s_m, u_m0 + 0.4, X_M - 16.5, -D + 0.6, ZB - 1.0, H_M, 10.0)
    zone(s_m, 0.72 * P + 0.5, XJ - 0.4, -D + 0.6, Z_BASTION - 3.0, Y_BASTION + 3.0, 8.0)   # au-dessus du tunnel
    zone(s_t, 0.72 * P + 0.5, XJ - 7.5, Z_T - 1.0, Z_BASTION - 3.0, Y_BASTION + 3.0, 8.0)
    zone(s_m, X_M - 15.5, X_M + 15.5, -D + 0.6, Z_M - 13.5, H_M, 9.0)                    # derrière la terrasse

    # -- butte boisée au-dessus du tunnel : trois gradins de roche derrière le corps de garde, une masse d'arbres
    # et des cèdres qui dépassent nettement son toit ; le portail se lit comme un passage percé dans la colline
    yk = Y_BASTION + 3.0
    xk = 0.72 * P
    with b.group("Colline/Centre"):
        for (u, z0, ya, yb_, tons) in ((xk, -22.0, yk, yk + 8.0, ("roche_fonce", "roche")),
                                       (0.6 * P, -27.0, yk + 8.0, yk + 16.0, ("roche", "roche_claire")),
                                       (0.4 * P, -32.0, yk + 16.0, yk + 22.0, ("roche_claire", "roche"))):
            ym = round((ya + yb_) / 2)
            b.box((-u, ya, -D + RETRAIT_DOS), (u, ym, z0), vr(tons[0], rng, 0.02), name="Butte")
            b.box((-u, ym, -D + RETRAIT_DOS), (u, yb_, z0), vr(tons[1], rng, 0.02), studs="top", name="Butte")
        # affleurements de roche claire sur les flancs du premier gradin
        for sx in (-1, 1):
            _bx(b, sx, 0.6 * P - 1.0, xk + 1.6, yk + 8.0, yk + 13.5, -27.5, -23.4, vr("roche_claire", rng, 0.03),
                studs="top", name="Saillie")
            _bx(b, sx, 0.6 * P + 1.5, xk - 0.5, yk + 13.5, yk + 16.5, -28.5, -24.6, vr("roche", rng, 0.03),
                studs="top", name="Saillie")
    massif(-0.38 * P, 0.38 * P, -D + 0.6, -33.0, yk + 22.0, 13.0, p=1.0, rose=False)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * (0.4 * P + 0.5), sx * (0.6 * P - 0.5)))
        massif(x0, x1, -D + 0.6, -28.0, yk + 16.0, 10.0, p=1.0)
        x0, x1 = sorted((sx * (0.6 * P + 0.5), sx * (xk - 0.5)))
        massif(x0, x1, -D + 0.6, -29.0, yk + 8.0, 9.0, p=0.95)
        conif.append((sx * 0.85 * P, yk, -18.0, "pin", 1.6))
    # silhouette dissymétrique : un grand cèdre, un pin en nuages, un cèdre plus bas sur le gradin
    conif.append((-0.2 * P, yk + 22.0, -39.5, "cedre", 2.1))
    conif.append((0.12 * P, yk + 22.0, -37.0, "pin", 2.2))
    conif.append((0.5 * P, yk + 16.0, -40.0, "cedre", 1.6))

    # -- grande tour blanche ---------------------------------------------------------------
    with b.group("Tour"):
        with b.at((s_t * X_T, 0, Z_T)):
            top_tour = _tour(b, rng, H_T, s_t)
        xa, xb = sorted((s_t * (X_T + 22.0), s_t * (X_T + 36.0)))
        _aile(b, rng, xa, xb, Z_T - 12.0, Z_T + 10.0, H_T, long_x=False)
        xa, xb = sorted((s_t * (XJ - 6.0), s_t * (XJ + 6.0)))
        _aile(b, rng, xa, xb, -D + 1.5, Z_T - 2.0, H_T, long_x=False)

    # -- monolithe ---------------------------------------------------------------------------
    with b.group("Monolithe"):
        with b.at((s_m * X_M, 0, Z_M)):
            blocs = _monolithe(b, rng, H_M, H_M + 100.0)
        for k in range(1, 5):
            b.box((s_m * X_M - 6, H_M - 4.0, ZB + (4 - k) * 1.25), (s_m * X_M + 6, H_M - 4.0 + k, ZB + (5 - k) * 1.25),
                  vr("pierre_claire", rng, 0.02), studs="top", name="Marche")
        for sx in (-1, 1):
            with b.at((s_m * X_M + sx * 12.4, H_M + 3.0, Z_M + 9.3)):
                mobilier.lanterne_pierre(b, variant=1)

    # -- végétation ----------------------------------------------------------------------------
    with b.group("Vegetation"):
        for (x0, x1, z0, z1, y, h, rose) in vege:
            _massif(b, x0, x1, z0, z1, y, rng, h=h, rose=rose, bornes=BORNES)
        for (x, y, z, sorte, ech) in conif:
            if sorte == "pin":
                _pin(b, x, y, z, rng, s=ech)
            else:
                _cedre(b, x, y, z, rng, s=ech)

    return {"emprise": (largeur, profondeur + 6.0), "hauteur": round(top_tour, 1), "sommet_porte": round(top_porte, 1),
            "tour": (s_t * X_T, Z_T), "monolithe": (s_m * X_M, Z_M), "escalier": s_e,
            "sommet_monolithe": round(max(bl[5] for bl in blocs) + 2.6, 1), "densite": dens}
