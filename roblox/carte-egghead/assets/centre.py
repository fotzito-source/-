"""Pièces de jeu du centre (dans le U du tapis) : stand de vente, machine, monument de l'œuf, podium-vitrine,
panneau des quêtes, plaque d'apparition. STYLE.md § 8.2 (G01, G02, G03, G07), SPECS.md (assets/centre.py).

    python apercu.py assets.centre:stand_vente --res 1200x675 --samples 12
    python apercu.py assets.centre:monument --res 1200x675 --samples 12

Poses : `plan.CENTRE` (carte.py : `with b.at((x, 0, z), yaw, group="Centre/<nom>")`). Origine au centre de
l'emprise, y = 0 sur la pelouse, avant vers -Z local. Vues de près par tous les joueurs : formes nettes, rondes,
façon jouet, aucun texte. Rien de plus haut que 0,3 dans les zones libres (zone de vente, centre du podium).
Pièces que l'on touche (socles, comptoir, plateaux, mâts) : collision franche ; ellipsoïdes et détails fins :
`collide=False` (l'œuf du monument : collision par un cylindre invisible).

Aucune face d'un asset dans le plan des lignes de la grille du sol (dessus à 0,15 / 0,20) : les pièces au sol
ont leur dessus à 0,3 au moins et leurs côtés ne sont jamais alignés sur les axes à moins de 0,3 du sol, sauf
les socles qui commencent à y = 0 (contrôlé à la pose sur la carte par le script de contrôle du constructeur).
"""

from __future__ import annotations

import math

import numpy as np

import plan
from kit import mix, rot_x, rot_y, rot_z, shade
from palette import c

try:   # petits objets du mobilier (écrit en parallèle) : repli sur des versions simples si absent ou en erreur
    from assets import mobilier as _mobilier
except Exception:   # noqa: BLE001
    _mobilier = None

try:
    from assets.tapis import coin_plat
except Exception:   # noqa: BLE001 — même module du constructeur ; repli minimal
    coin_plat = None


# --------------------------------------------------------------------------------------------------------------
# Outils communs
# --------------------------------------------------------------------------------------------------------------

def boite_ronde(b, x0, x1, z0, z1, y0, y1, r, couleur, *, studs=True, **kw) -> list:
    """Boîte aux coins arrondis (vue de dessus) à **dessus plat** : bloc central sur toute la largeur, deux bandes
    avant et arrière qui le prolongent sans le recouvrir (même dessus, joints sans recouvrement), 4 cylindres
    d'angle 0,05 plus bas (dessous 0,03 plus haut). 7 pièces."""
    st = "top" if studs else ()
    nom = kw.pop("name", "Socle")
    out = [b.box((x0, y0, z0 + r), (x1, y1, z1 - r), couleur, studs=st, name=nom, **kw),
           b.box((x0 + r, y0, z0), (x1 - r, y1, z0 + r), couleur, studs=st, name=nom, **kw),
           b.box((x0 + r, y0, z1 - r), (x1 - r, y1, z1), couleur, studs=st, name=nom, **kw)]
    ya, yb = y0 + 0.03, y1 - 0.05
    for x in (x0 + r, x1 - r):
        for z in (z0 + r, z1 - r):
            out.append(b.cyl((x, (ya + yb) / 2, z), r, yb - ya, couleur, studs=st, name=nom, **kw))
    return out


def gelule(b, centre, largeur, hauteur, epaisseur, couleur, **kw) -> list:
    """Gélule plate face à -Z (stade : bloc + 2 demi-cylindres d'axe Z) de `largeur` × `hauteur`, centrée en
    `centre`. Les bouts ronds sont 0,04 et 0,08 plus minces (aucune face confondue). 3 pièces."""
    cx, cy, cz = centre
    r = hauteur / 2
    nom = kw.pop("name", "Gelule")
    out = [b.boxc((cx, cy, cz), (largeur - hauteur, hauteur, epaisseur), couleur, name=nom, **kw)]
    for j, sx in enumerate((-1, 1)):    # les deux bouts peuvent se recouvrir : longueurs différentes
        out.append(b.cyl((cx + sx * (largeur / 2 - r), cy, cz), r, epaisseur - 0.04 - 0.04 * j, couleur, axis="z",
                         name=nom, **kw))
    return out


def _coin_plat(b, V, e1, L1, e2, L2, y0, y1, couleur, **kw):
    """Coin posé à plat (triangle rectangle horizontal) : assets.tapis.coin_plat, ou repli local identique."""
    if coin_plat is not None:
        return coin_plat(b, V, e1, L1, e2, L2, y0, y1, couleur, **kw)
    V, e1, e2 = np.asarray(V, float), np.asarray(e1, float), np.asarray(e2, float)
    if e1[0] * e2[1] - e1[1] * e2[0] < 0:
        e1, e2, L1, L2 = e2, e1, L2, L1
    X = np.array([0.0, 1.0, 0.0])
    Y = np.array([e1[0], 0.0, e1[1]])
    Z = np.array([-e2[0], 0.0, -e2[1]])
    ctr = V + e1 * L1 / 2 + e2 * L2 / 2
    studs = kw.pop("studs", True)
    return b.part("wedge", (y1 - y0, L1, L2), (ctr[0], (y0 + y1) / 2, ctr[1]), np.column_stack([X, Y, Z]),
                  couleur, studs=("Right",) if studs else (), name=kw.pop("name", "Coin"), **kw)


def octogone(b, apotheme, y0, y1, couleur, *, studs=True, **kw) -> list:
    """Octogone régulier plein (entre plats = 2 × apothème, côtés face à ±X, ±Z et aux diagonales) : un bloc sur
    toute la largeur en X, deux blocs qui le prolongent en Z (sans recouvrement : dessus plat continu), 4 coins
    posés à plat aux angles (jamais deux carrés à 45°). 7 pièces."""
    A = float(apotheme)
    h = A * math.tan(math.pi / 8)          # demi-côté
    nom = kw.pop("name", "Octogone")
    st = "top" if studs else ()
    out = [b.box((-A, y0, -h), (A, y1, h), couleur, studs=st, name=nom, **kw),
           b.box((-h, y0, h), (h, y1, A), couleur, studs=st, name=nom, **kw),
           b.box((-h, y0, -A), (h, y1, -h), couleur, studs=st, name=nom, **kw)]
    for sx in (-1, 1):
        for sz in (-1, 1):
            out.append(_coin_plat(b, (sx * h, sz * h), (sx, 0.0), A - h, (0.0, sz), A - h, y0, y1, couleur,
                                  studs=bool(studs), name=nom + "_Coin", **dict(kw)))
    return out


def etoile(b, centre, rayon, epaisseur, couleur, *, normale="z", **kw) -> list:
    """Étoile-jouet à 5 branches dans un plan vertical face à Z (ou X) : 5 ellipsoïdes effilés autour d'un
    disque central. 6 pièces."""
    ctr0 = np.asarray(centre, float)
    nom = kw.pop("name", "Etoile")
    R = rot_y(90) if normale == "x" else np.eye(3)
    out = [b.part("cyl", (epaisseur + 0.1, rayon * 0.72, rayon * 0.72), ctr0, R @ rot_y(90), couleur, name=nom,
                  **kw)]
    L = rayon * 1.25                       # longueur d'une branche (ellipsoïde), du centre à la pointe
    for k in range(5):
        a = math.radians(90 + 72 * k)
        d = np.array([math.cos(a), math.sin(a), 0.0])
        out.append(b.part("ellipsoid", (L, rayon * 0.5, epaisseur), ctr0 + R @ (d * (rayon - L / 2)),
                          R @ rot_z(math.degrees(a)), couleur, name=nom, **kw))
    return out


def _potelet(b, x, z, y=0.0):
    """Potelet M06 (H ≈ 3,6) : celui de assets.mobilier si disponible, sinon une version simple (4 pièces)."""
    if _mobilier is not None and hasattr(_mobilier, "potelet"):
        try:
            n0 = len(b.parts)
            with b.at((x, y, z)):
                _mobilier.potelet(b, variant=0)
            return len(b.parts) - n0
        except Exception:   # noqa: BLE001
            pass
    with b.at((x, y, z)):
        b.cone_etage((0, 0, 0), 0.75, 0.5, 1.3, [c("indigo"), shade(c("indigo"), 0.85)], etages=2, name="Potelet")
        b.cyl((0, 2.25, 0), 0.38, 1.9, c("blanc_labo"), name="Potelet")
        b.cyl((0, 1.45, 0), 0.5, 0.3, c("or"), name="Bague", collide=False)
        b.ball((0, 3.4, 0), 0.48, c("cyan"), name="Pommeau", collide=False)
    return 4


def _lampe_soucoupe(b, x, z, y, hauteur=5.5, coque="bleu_roi"):
    """Lampadaire-soucoupe bas (M08 réduit, 6 pièces, 1 Neon) : pied indigo, mât blanc, soucoupe blanche et
    coque de couleur, disque Neon cyan dessous."""
    with b.at((x, y, z), group="Lampe"):
        b.cone_etage((0, 0, 0), 0.75, 0.45, 1.2, [c("indigo"), shade(c("indigo"), 0.85)], etages=2, name="Pied")
        b.cyl((0, 1.2 + (hauteur - 1.2) / 2 - 0.05, 0), 0.24, hauteur - 1.2 - 0.1, c("blanc_labo"), name="Mat")
        b.cyl((0, hauteur + 0.12, 0), 1.7, 0.3, c("blanc_labo"), studs="top", name="Soucoupe", collide=False)
        b.ellipsoid((0, hauteur + 0.3, 0), (2.6, 1.3, 2.6), c(coque), name="Coque", collide=False)
        b.cyl((0, hauteur - 0.07, 0), 1.15, 0.12, c("cyan"), material="Neon", collide=False, shadow=False,
              name="Lueur")
    return 6


# --------------------------------------------------------------------------------------------------------------
# Stand de vente (G01)
# --------------------------------------------------------------------------------------------------------------

def stand_vente(b, variant=0, **params):
    """Stand de vente : kiosque rond à toit-dôme rouge, lambrequin rayé rouge et blanc et pièce d'or géante, sur un
    socle carré arrondi 28 × 28 blanc à bord rayé rouge ; zone de vente en demi-disque pointillé (rayon 14) devant
    (au nord, -Z local). ≤ 90 pièces, ≤ 6 Neon. Aucun texte."""
    W = float(params.get("largeur", plan.CENTRE["Vente"]["emprise"][0]))
    D = float(params.get("profondeur", plan.CENTRE["Vente"]["emprise"][1]))
    rz = float(params.get("rayon_zone", plan.ZONE_VENTE["rayon"]))
    rouge, blanc, dalle = c("rouge"), c("blanc_labo"), c("dalle_labo")
    accent = c("turquoise")
    h_socle = 1.0
    r_coin = 2.5
    # -- socle : boîte arrondie blanche à studs, bord « vibreur » (blocs rouges en saillie de 0,1 sur le dessus et
    #    sur la face), plancher rond du kiosque
    with b.group("Socle"):
        boite_ronde(b, -W / 2, W / 2, -D / 2, D / 2, 0.0, h_socle, r_coin, blanc, name="Socle")
        n_r = 4                                         # 4 rouges par côté : R B R B R B R entre deux angles blancs
        for axe in ("x", "z"):
            L = (W if axe == "x" else D) / 2 - r_coin - 0.15
            pas = 2 * L / (2 * n_r - 1)
            for sgn in (-1, 1):
                for k in range(n_r):
                    s0 = -L + 2 * k * pas
                    if axe == "x":    # bords nord et sud (le long de X)
                        z_out = sgn * D / 2
                        b.box((s0, h_socle - 0.6, z_out - sgn * 0.9), (s0 + pas, h_socle + 0.1, z_out + sgn * 0.1),
                              rouge, studs="top", name="Rayure")
                    else:
                        x_out = sgn * W / 2
                        b.box((x_out - sgn * 0.9, h_socle - 0.6, s0), (x_out + sgn * 0.1, h_socle + 0.1, s0 + pas),
                              rouge, studs="top", name="Rayure")
        b.cyl((0, h_socle + 0.1, 0), 11.2, 0.4, dalle, studs="top", name="Plancher")
    y_pl = h_socle + 0.3                                # dessus du plancher rond
    # -- comptoir en arc de 220° tourné vers l'avant (-Z) : paroi turquoise, tablette blanche à studs
    r_cpt = 8.2
    h_cpt = 3.0
    with b.group("Comptoir"):
        b.anneau((0, y_pl - 0.1 + h_cpt / 2, 0), r_cpt, h_cpt, accent, 16, arc=220, depart=-20, section="plat",
                 largeur=0.9, name="Paroi")
        b.anneau((0, y_pl - 0.1 + h_cpt + 0.17, 0), r_cpt, 0.3, blanc, 16, arc=220, depart=-20, section="plat",
                 largeur=1.6, studs="top", name="Tablette")
    # -- colonne centrale à bagues d'or (pied sur le plancher, collier sous la cloche du toit)
    y_bord = 11.6                                       # dessous du bord du toit
    e_bord = 1.0
    h_dome = 5.2
    h_cl = 4.4                                          # demi-hauteur de la cloche : h - d ≤ h' ≤ h + d
    with b.group("Colonne"):
        b.cyl((0, (y_pl - 0.1 + y_bord + 0.2) / 2, 0), 1.25, y_bord + 0.2 - (y_pl - 0.1), blanc, name="Colonne")
        b.cyl((0, y_pl + 0.2, 0), 1.75, 0.5, c("or"), studs="top", name="Bague")
        b.cyl((0, y_bord - h_cl + 0.05, 0), 1.6, 0.6, c("or"), name="Collier", collide=False)
    # -- toit : bord blanc à studs, dôme rouge, cloche blanche dessous (cache la moitié basse du dôme),
    #    lambrequin rayé rouge et blanc, guirlande de points Neon cyan
    r_bord = 12.5
    with b.group("Toit"):
        b.cyl((0, y_bord + e_bord / 2, 0), r_bord, e_bord, blanc, studs="top", name="Bord", collide=False)
        toit = b.dome((0, y_bord + e_bord, 0), r_bord, h_dome, rouge, rebord=1.2, collide=False)
        rd = toit.info["rayon_dome"]
        assert h_dome - e_bord <= h_cl <= h_dome + e_bord
        b.ellipsoid((0, y_bord, 0), (2 * rd, 2 * h_cl, 2 * rd), blanc, name="Cloche", collide=False)
        h_lb = 2.4                                      # lambrequin : dépasse de 0,2 le dessus du bord
        y_lb = y_bord + e_bord + 0.2 - h_lb / 2
        b.anneau((0, y_lb, 0), r_bord + 0.22, h_lb, [rouge, blanc], 16, depart=0, section="plat",
                 largeur=0.42, name="Lambrequin", collide=False)
        y_g = y_lb - h_lb / 2 - 0.32
        for k in range(6):
            a = math.radians(90 + 30 + 60 * k)          # un point devant à ±30° de l'avant, puis tous les 60°
            b.ball((math.cos(a) * (r_bord + 0.22), y_g, -math.sin(a) * (r_bord + 0.22)), 0.36, c("cyan"),
                   material="Neon", collide=False, shadow=False, name="Ampoule")
    y_sommet = y_bord + e_bord + h_dome
    # -- mât et pièce d'or géante debout, faces vers le nord et le sud
    r_piece = 3.1
    with b.group("Piece"):
        y_p = y_sommet + 1.15 + r_piece
        b.cyl((0, y_sommet + 0.6, 0), 0.45, 1.9, blanc, name="Mat", collide=False)
        b.cyl((0, y_p, 0), r_piece, 0.9, c("or"), axis="z", name="Piece", collide=False)
        b.cyl((0, y_p, 0), r_piece * 0.74, 1.04, c("or_fonce"), axis="z", name="PieceCentre", collide=False)
        b.cyl((0, y_p, 0), r_piece * 0.38, 1.18, c("or"), axis="z", name="PieceBouton", collide=False)
    # -- zone de vente : demi-disque en pointillés blancs au nord (centre au milieu du bord nord du socle)
    n_t = int(params.get("tirets", 12))
    with b.group("ZoneVente"):
        for k in range(n_t):
            a = math.radians(180.0 * (k + 0.5) / n_t)   # jamais 0, 90 ni 180° : aucun tiret aligné sur les axes
            x, z = rz * math.cos(a), -D / 2 - rz * math.sin(a)
            b.boxc((x, 0.15, z), (2.0, 0.3, 0.6), blanc, yaw=math.degrees(a) + 90.0, studs="top", name="Tiret",
                   collide=False)                      # X local du tiret = tangente (-sin a, -cos a)
    return {"emprise": (W, D), "hauteur": round(y_p + r_piece, 2), "hauteur_toit": round(y_sommet, 2),
            "zone_vente": {"centre_z": -D / 2, "rayon": rz}}


# --------------------------------------------------------------------------------------------------------------
# Machine à bulle du labo (G02)
# --------------------------------------------------------------------------------------------------------------

def machine(b, variant=0, **params):
    """Machine : deux pylônes rayés bleu nuit et blanc à boules Neon cyan, bulle de verre à cœur Neon violet sur
    un piédestal, anneau orbital d'or incliné, deux arcs Neon des boules vers la bulle, tuyaux en J à l'arrière, sur
    un socle arrondi 12 × 10 (bord indigo, dessus à studs). ≤ 50 pièces, ≤ 6 Neon, ≤ 1 verre."""
    W = float(params.get("largeur", 12.0))
    D = float(params.get("profondeur", 10.0))
    indigo, blanc, dalle = c("indigo"), c("blanc_labo"), c("dalle_labo")
    h0, h1 = 0.7, 1.2
    with b.group("Socle"):
        boite_ronde(b, -W / 2, W / 2, -D / 2, D / 2, 0.0, h0, 1.6, indigo, name="Socle")
        # plateau clair en stade (bouts ronds le long de X), 0,6 en retrait : le bord indigo l'entoure
        lp, dp = W - 1.2, D - 1.2
        b.box((-(lp - dp) / 2, h0 - 0.1, -dp / 2), ((lp - dp) / 2, h1, dp / 2), dalle, studs="top", name="Plateau")
        for j, sx in enumerate((-1, 1)):          # les deux bouts se recouvrent : dessus et dessous décalés
            ya, yb = h0 - 0.08 + 0.02 * j, h1 - 0.04 - 0.03 * j
            b.cyl((sx * (lp - dp) / 2, (ya + yb) / 2, 0), dp / 2, yb - ya, dalle, studs="top", name="Plateau")
    # pylônes à l'arrière (z +1,6), bulle à l'avant (z -1,3) : l'anneau orbital passe entre eux
    xp, zp = 4.2, 1.5
    zb = -1.3
    h_pyl = 11.4
    r_boule = 1.15
    with b.group("Pylones"):
        for sx in (-1, 1):
            x = sx * xp
            b.cyl((x, h1 + 0.2, zp), 1.75, 0.4, c("or"), studs="top", name="Bague")
            b.cone_etage((x, h1 + 0.4, zp), 1.35, 0.8, h_pyl - 0.4, [c("bleu_nuit"), blanc], etages=6,
                         name="Pylone")
            b.ball((x, h1 + h_pyl + r_boule - 0.25, zp), r_boule, c("cyan"), material="Neon", collide=False,
                   shadow=False, name="Boule")
    y_boule = h1 + h_pyl + r_boule - 0.25
    r_bulle = 3.1
    y_ped = h1 + 3.0
    with b.group("Bulle"):
        b.cyl((0, (h1 - 0.1 + y_ped) / 2, zb), 2.0, y_ped - h1 + 0.1, blanc, studs="top", name="Piedestal")
        b.cyl((0, y_ped - 0.35, zb), 2.25, 0.5, c("or"), name="Bague", collide=False)
        yc = y_ped + r_bulle - 0.3
        b.ball((0, yc, zb), r_bulle, c("verre"), material="Glass", transparency=0.5, name="Bulle")
        b.ball((0, yc, zb), 1.35, c("neon_violet"), material="Neon", collide=False, shadow=False, name="Coeur")
        b.anneau((0, yc + 0.2, zb), r_bulle + 0.9, 0.36, c("or"), 12, rot=rot_x(24) @ rot_z(-14), name="Orbite",
                 collide=False, shadow=False)
        # arcs Neon : des boules des pylônes vers le haut de la bulle (droits, fins)
        for sx in (-1, 1):
            p0 = np.array([sx * (xp - 0.55), y_boule - 0.75, zp - 0.45])
            cible = np.array([0.0, yc, zb])
            d = p0 - cible
            p1 = cible + d / np.linalg.norm(d) * (r_bulle + 0.15)
            b.cyl_entre(p0, p1, 0.13, c("cyan"), material="Neon", collide=False, shadow=False, name="Arc")
    # tuyaux en J à l'arrière : montée depuis le plateau, coude, retour vers le piédestal
    col_t = mix(c("indigo"), c("dalle_labo"), 0.4)
    with b.group("Tuyaux"):
        for sx in (-1, 1):
            x = sx * 1.25
            zt = D / 2 - 1.3
            yt = h1 + 2.2
            b.cyl((x, (h1 - 0.1 + yt) / 2, zt), 0.5, yt - h1 + 0.1, col_t, name="Tuyau")
            b.ball((x, yt, zt), 0.5, col_t, name="Coude")
            b.cyl_entre((x, yt, zt), (x, yt, zb + 1.3), 0.5, col_t, name="Tuyau")
    return {"emprise": (W, D), "hauteur": round(y_boule + r_boule, 2)}


# --------------------------------------------------------------------------------------------------------------
# Monument de l'œuf (G03)
# --------------------------------------------------------------------------------------------------------------

def _dent(b, base, t, u, largeur, hauteur, epaisseur, couleur, **kw):
    """Dent du zigzag : triangle isocèle dans le plan (t, u) (t horizontal, u vers le haut), pied centré en `base`,
    2 coins dos à dos d'épaisseur `epaisseur`."""
    base, t, u = (np.asarray(v, float) for v in (base, t, u))
    for s in (1, -1):
        Z = -s * t                                   # dos du coin (face +Z) sur l'axe de la dent
        X = np.cross(u, Z)
        R = np.column_stack([X, u, Z])
        ctr = base + u * hauteur / 2 + s * t * largeur / 4
        b.part("wedge", (epaisseur, hauteur, largeur / 2), ctr, R, couleur, name="Dent", **kw)


def monument(b, variant=0, **params):
    """Monument de l'œuf : plateau de 3 disques (turquoise / blanc / turquoise, studs), halo Neon violet flottant,
    réplique de l'œuf fêlé (recette C01 à l'échelle k : 3 coquilles, intérieur sombre, 2 méridiens Neon, dents du
    zigzag), anneau de données en arcs, 5 petits cubes en arc, 4 lampadaires-soucoupes bas sur le plateau.
    Avant (-Z local) vers l'apparition (pose yaw 180). ≤ 120 pièces, ≤ 20 Neon, aucune transparence."""
    k = float(params.get("echelle", 0.14))
    turq, blanc = c("turquoise"), c("blanc_labo")
    R1, R2, R3 = 17.0, 14.0, 11.0
    e = 1.5
    with b.group("Plateau"):
        b.cyl((0, e / 2, 0), R1, e, turq, studs="top", name="Disque")
        b.cyl((0, e + e / 2 - 0.25, 0), R2, e + 0.5, blanc, studs="top", name="Disque")
        b.cyl((0, 2 * e + e / 2 - 0.25, 0), R3, e + 0.5, turq, studs="top", name="Disque")
    y_haut = 3 * e
    # halo Neon violet flottant autour du dernier disque (au-dessus du deuxième)
    with b.group("Halo"):
        b.anneau((0, y_haut + 0.75, 0), 12.6, 0.18, c("neon_violet"), 14, depart=90 / 7, section="plat",
                 largeur=0.55, material="Neon", collide=False, shadow=False, name="Halo")
    # -- l'œuf (repère local de la recette : y = 0 au bas de la coquille), enfoncé de 1,4 dans le dernier disque
    y0 = y_haut - 1.4
    with b.at((0, y0, 0), group="Oeuf"):
        b.ellipsoid((0, 80 * k, 0), (150 * k, 160 * k, 150 * k), c("oeuf_violet"), name="Coquille", collide=False)
        b.ellipsoid((0, 92 * k, 0), (148 * k, 156 * k, 148 * k), c("oeuf_mauve"), name="Coquille", collide=False)
        b.ellipsoid((0, 122 * k, 0), (134 * k, 156 * k, 134 * k), c("oeuf_rose"), name="Coquille", collide=False)
        yc = 168 * k
        b.ellipsoid((0, yc, 0), (109 * k, 64 * k, 109 * k), c("oeuf_interieur"), name="Interieur", collide=False)
        for a in (0, 90):
            b.ellipsoid((0, yc, 0), (max(0.6 * k, 0.12), 64.6 * k, 109.6 * k), c("neon_violet"), rot=rot_y(a + 45),
                        material="Neon", collide=False, shadow=False, name="Meridien")
        # dents du zigzag sur le bord de la cassure (cercle R 54 k, pied à 166 k), hauteurs irrégulières
        n_d = int(params.get("dents", 10))
        r_c = 54.6 * k
        hauts = [26, 20, 30, 22, 28, 18, 24, 29, 21, 25, 19, 27]
        for i in range(n_d):
            th = 2 * math.pi * (i + 0.25) / n_d
            radial = np.array([math.cos(th), 0.0, -math.sin(th)])
            t = np.array([-math.sin(th), 0.0, -math.cos(th)])
            pen = math.radians(14 + 4 * ((i * 7) % 3 - 1))
            u = math.cos(pen) * np.array([0.0, 1.0, 0.0]) - math.sin(pen) * radial
            larg = 2 * math.pi * r_c / n_d * 1.02
            _dent(b, radial * r_c + np.array([0.0, 165.0 * k, 0.0]), t, u, larg, hauts[i % len(hauts)] * k,
                  max(2.5 * k, 0.32), c("oeuf_rose"), collide=False, shadow=False)
        # collision de l'œuf : cylindre invisible dans sa partie basse
        b.cyl((0, (3.8 + 21.0) / 2, 0), 8.0, 21.0 - 3.8, blanc, transparency=1.0, shadow=False,
              name="CollisionOeuf")
    # -- anneau de données (arcs bleu roi / bleu nuit, incliné) et cubes en arc
    with b.group("Donnees"):
        y_a = y0 + 118 * k
        for j in range(2):
            b.anneau((0, y_a, 0), 13.4, 0.26, [c("bleu_roi"), c("bleu_nuit")], 24, arc=165, depart=7.5 + 180 * j,
                     rot=rot_x(7) @ rot_z(3), section="plat", largeur=1.15, collide=False, shadow=False,
                     name="Anneau")
    with b.group("Cubes"):
        cols = [c("cube_bleu"), c("lavande"), c("blanc_labo"), c("cube_bleu"), c("lavande")]
        arc = [(15, 158, 2.4), (42, 176, 1.8), (68, 192, 2.1), (94, 204, 1.6), (120, 213, 1.8)]
        for i, (th, yr, s_) in enumerate(arc):          # angle (0 = +X, 90 = avant), hauteur (recette), côté
            a = math.radians(th)
            rr = 88 * k
            b.part("block", (s_, s_, s_), (rr * math.cos(a), y0 + yr * k, -rr * math.sin(a)),
                   rot_y(15 + 23 * i) @ rot_x(20 + 9 * i), cols[i], name="Cube", collide=False, shadow=False)
    # -- 4 lampadaires-soucoupes bas sur le premier gradin (diagonales : l'avant reste dégagé)
    with b.group("Lampes"):
        for j in range(4):
            a = math.radians(45 + 90 * j)
            rr = (R1 + R2) / 2
            _lampe_soucoupe(b, rr * math.cos(a), -rr * math.sin(a), e, hauteur=5.5)
    return {"emprise": (2 * R1, 2 * R1), "hauteur": round(y0 + 200 * k, 2), "echelle_oeuf": k}


# --------------------------------------------------------------------------------------------------------------
# Podium-vitrine octogonal (centre libre pour la statue du jeu)
# --------------------------------------------------------------------------------------------------------------

def vitrine(b, variant=0, **params):
    """Podium octogonal Ø 36 (entre plats), H 2,5 : deux gradins octogonaux (indigo, blanc, studs), anneau
    octogonal Neon cyan sur la contremarche du second, bords dorés, **disque central de Ø 20 laissé libre** (dessus
    plat à studs à 2,5 ; rien au-dessus de 2,6 : la statue du jeu s'y pose). ≤ 60 pièces, ≤ 10 Neon."""
    A1 = float(params.get("diametre", 36.0)) / 2
    A2 = A1 - 3.5
    r_libre = float(params.get("rayon_libre", plan.VITRINE_RAYON_LIBRE))
    y1, y2 = 1.2, 2.3
    with b.group("Gradins"):
        octogone(b, A1, 0.0, y1, c("indigo"), name="Gradin")
        octogone(b, A2, y1 - 0.2, y2, c("blanc_labo"), name="Gradin")
    with b.group("Bords"):
        # liseré d'or sur le bord du premier gradin (octogone plat posé sur le dessus, au ras du bord)
        b.anneau((0, y1 + 0.06, 0), A1 - 0.55, 0.12, c("or"), 8, depart=-22.5, section="plat", largeur=0.8,
                 studs="top", collide=False, name="Liseré")
        # anneau Neon sur la contremarche du second gradin
        b.anneau((0, (y1 + y2) / 2, 0), A2 + 0.08, 0.36, c("cyan"), 8, depart=-22.5, section="carre",
                 material="Neon", collide=False, shadow=False, name="AnneauNeon")
    with b.group("Centre"):
        # disque central libre : bague d'or et disque clair, dessus plat à studs à 2,5
        b.cyl((0, y2 + 0.05 - 0.1, 0), r_libre + 0.7, 0.3, c("or"), studs="top", name="Bague")
        b.cyl((0, y2 + 0.2 - 0.075, 0), r_libre, 0.25, c("dalle_labo"), studs="top", name="Disque")
        # 8 rivets d'or aux angles du second gradin
        for j in range(8):
            a = math.radians(22.5 + 45 * j)
            rr = (A2 - 1.1) / math.cos(math.pi / 8)
            b.cyl((rr * math.cos(a), y2 + 0.12, -rr * math.sin(a)), 0.55, 0.24, c("or"), studs="top",
                  collide=False, name="Rivet")
    return {"emprise": (2 * A1, 2 * A1), "hauteur": round(y2 + 0.2 + 0.05, 2), "centre_libre": 2 * r_libre}


# --------------------------------------------------------------------------------------------------------------
# Panneau des quêtes (holographique, sans texte)
# --------------------------------------------------------------------------------------------------------------

def panneau_quetes(b, variant=0, **params):
    """Panneau holographique sans texte sur mât fin : émetteur rond à studs, mât blanc, cadre en gélule bleu nuit
    à bord blanc, écran Neon cyan translucide (3 tirets Neon blancs en faux texte), étoile d'or sur le cadre.
    Face à -Z local (pose yaw 180 : vers le sud). Le panneau ne collisionne pas, le mât et le socle oui.
    ≤ 25 pièces, ≤ 4 Neon, ≤ 2 transparentes."""
    blanc = c("blanc_labo")
    Wf, Hf = 10.0, 6.0
    yc = 11.6
    with b.group("Socle"):
        b.cyl((0, 0.3, 0), 2.1, 0.6, blanc, studs="top", name="Emetteur")
        b.cyl((0, 0.35, 0), 2.45, 0.3, c("indigo"), name="Bague")
        b.cyl((0, 0.85, 0), 0.9, 0.5, c("or"), studs="top", name="Collier")
    with b.group("Mat"):
        b.cyl((0, (1.1 + yc - 1.5) / 2, 0.5), 0.4, yc - 1.5 - 1.1, blanc, name="Mat")
        b.cyl((0, yc - Hf / 2 - 0.55, 0.5), 0.62, 0.5, c("or"), name="Bague", collide=False)
        b.cyl((0, (1.0 + 1.2) / 2, 0.5), 0.5, 0.25, blanc, name="Mat")
    with b.group("Cadre"):
        gelule(b, (0, yc, 0.55), Wf + 0.8, Hf + 0.7, 0.5, blanc, collide=False, name="Bord")
        gelule(b, (0, yc, 0.42), Wf, Hf, 0.5, c("bleu_nuit"), collide=False, name="Cadre")
        b.boxc((0, yc, 0.09), (Wf - Hf + 3.6, Hf - 1.4, 0.16), c("cyan"), material="Neon", transparency=0.35,
               collide=False, shadow=False, name="Ecran")
        x_g = -2.9                                      # bord gauche des lignes de « faux texte »
        for lx, dy in ((5.2, 1.15), (3.8, 0.0), (4.6, -1.15)):
            b.boxc((x_g + lx / 2, yc + dy, -0.04), (lx, 0.42, 0.12), c("neon_blanc"), material="Neon",
                   collide=False, shadow=False, name="FauxTexte")
        etoile(b, (0, yc + Hf / 2 + 1.25, 0.42), 1.5, 0.5, c("or"), collide=False, name="Etoile")
    return {"emprise": (Wf + 0.8, 4.9), "hauteur": round(yc + Hf / 2 + 1.25 + 1.5, 2)}


# --------------------------------------------------------------------------------------------------------------
# Plaque d'apparition (G07)
# --------------------------------------------------------------------------------------------------------------

def apparition(b, variant=0, **params):
    """Plaque d'apparition : plaque dorée M13 agrandie (anneau blanc à studs, disque d'or, disque d'or foncé, bouton
    central), halo Neon cyan au ras du sol (anneau plat de 16), 4 potelets M06 sur les diagonales (R 7,5). Dessus
    à 0,4 (au-dessus des lignes de la grille). ≤ 40 pièces, ≤ 16 Neon."""
    R = float(params.get("rayon", 5.0))
    with b.group("Plaque"):
        b.cyl((0, 0.125, 0), R + 0.7, 0.25, c("blanc_labo"), studs="top", name="Anneau")
        b.cyl((0, 0.17, 0), R, 0.3, c("or"), studs="top", name="Or")
        b.cyl((0, 0.215, 0), R * 0.7, 0.33, c("or_fonce"), studs="top", name="OrFonce")
        b.cyl((0, 0.25, 0), R * 0.3, 0.32, c("or"), studs="top", name="Bouton")
    with b.group("Halo"):
        b.anneau((0, 0.12, 0), R + 1.6, 0.28, c("cyan"), 16, depart=0, section="plat", largeur=0.5,
                 material="Neon", collide=False, shadow=False, name="Halo")
    with b.group("Potelets"):
        for j in range(4):
            a = math.radians(45 + 90 * j)
            _potelet(b, 7.5 * math.cos(a), -7.5 * math.sin(a))
    return {"emprise": (14.0, 14.0), "hauteur": 3.9}
