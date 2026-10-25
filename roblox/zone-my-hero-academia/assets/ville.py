"""Ville moderne et entrée de l'académie (zone My Hero Academia), style « stud ».

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :
- boutique(largeur, profondeur, etages, enseigne) : boutique vitrée de rue japonaise moderne ; v0 façade
    carrelée blanche et store rayé rouge, v1 immeuble étroit pastel à enseigne verticale et balconnets,
    v2 étages en mur-rideau bleu ciel et store bleu, v3 supérette d'un niveau (bandeau violet / orange /
    lavande, enseigne de toit, niche à distributeurs) ;
- immeuble_bureaux(largeur, profondeur, hauteur, simple) : tour de bureaux (hall vitré éclairé, corps,
    couronne blanche et mât à feu rouge) ; v0 béton blanc à bandeaux bleus et angle vitré, v1 mur-rideau
    bleu ciel, v2 tour à gradin (socle puis fût étroit) blanche à liseré violet ;
- viaduc_train(longueur, hauteur, passage) : viaduc ferroviaire le long de X, dessous du tablier à
    `hauteur`, piles hors de |x| < passage / 2, train de banlieue blanc à bandes arrêté au-dessus de la route ;
- portail_securite(ouverture, hauteur, profondeur, mur, h_mur) : grand portail de sécurité high-tech
    (deux pylônes d'acier bleu nuit et de verre, linteau, guérite, caméras, barrières escamotées) et le mur
    d'enceinte avant de panneaux gris tachés entre des piles de brique ;
- mur_campus(longueur, hauteur) : tronçon du mur d'enceinte latéral ;
- silhouette_lointaine(largeur, profondeur, hauteur) : immeuble lointain très simple (≤ 8 pièces).

Repère (voir CONVENTIONS.md) : origine au centre de l'emprise au sol, y = 0 au sol, l'AVANT regarde -Z
local (zone.py tourne l'asset vers la route). Exceptions posées sans rotation, face principale vers +Z
(les joueurs qui arrivent) et les deux faces finies : `viaduc_train` et `portail_securite`.

Couloir : rien sous y = 36 dans |x| < 56 pour le viaduc et dans |x| < 50 pour le portail ; aucun sol dans
|x| < 52 (zone.py peint la chaussée et le seuil). Textes : uniquement des mots génériques (ACADÉMIE et les
noms de commerces permis), pas de logo, pas de marque, rien qui rappelle la licence.
"""

from __future__ import annotations

import math


from assets.mobilier import _label, _segment
from kit import hexrgb, mix, rot_z, shade
from palette import c, tirer, vary

# ---------------------------------------------------------------------------
# Couleurs locales (dérivées de la palette)
# ---------------------------------------------------------------------------
BALLAST = "#5B5A60"           # ballast sombre sous les rails
INTERIEUR_BOUTIQUE = "#FFE7B8"  # fond éclairé d'une vitrine (chaud)
ETAGERE = "#C9A27A"           # rayonnages vus à travers la vitrine
CLIM = "#D9DCE2"              # climatiseurs


def col(x):
    """Nom de palette, '#hex' ou tuple → tuple RGB."""
    if isinstance(x, tuple):
        return x
    if isinstance(x, str) and x.startswith("#"):
        return hexrgb(x)
    return c(x)


def vr(x, rng, amount: float = 0.05):
    """`vary` qui accepte aussi '#hex' et les tuples."""
    return vary(col(x), rng, amount)


def _neon(b, a, bb, couleur="neon_cyan", name: str = "Neon"):
    """Bande lumineuse fine (matériau Neon), sans collision ni ombre."""
    return b.box(a, bb, col(couleur), material="Neon", collide=False, shadow=False, name=name)


def _deco(b, a, bb, couleur, name: str = "Detail", **kw):
    """Petit détail décoratif sans collision."""
    return b.box(a, bb, col(couleur), collide=False, name=name, **kw)


def _verre(b, a, bb, couleur="vitre_claire", transparence: float = 0.35, name: str = "Vitre", **kw):
    """Vitre à travers laquelle on voit (matériau Glass, transparente)."""
    return b.box(a, bb, col(couleur), material="Glass", transparency=transparence, name=name, **kw)


def _diag(b, p0, p1, ep_y: float, z0: float, z1: float, couleur, **kw):
    """Barre droite dans le plan XY, de p0 = (x, y) à p1 = (x, y), épaisseur `ep_y`, étendue sur z0..z1."""
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0)
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    return b.part("block", (L, ep_y, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), rot_z(ang),
                  col(couleur), **kw)


# ---------------------------------------------------------------------------
# 4. Portail de sécurité et mur d'enceinte avant
# ---------------------------------------------------------------------------

def _q(v: float) -> float:
    """Arrondi au demi-stud (taches « pixel »)."""
    return round(v * 2) / 2


def _tache(b, u0: float, u1: float, ya: float, yb: float, z0: float, z1: float, rng, morceaux: int = 3) -> int:
    """Tache de ruissellement « pixel » dans la case u0..u1 × ya..yb, sur la tranche z0..z1 : un aplat large en
    haut, puis une ou deux coulures plus étroites qui pendent dessous. Les morceaux se touchent par un bord,
    sans jamais se superposer. Renvoie le nombre de pièces posées."""
    w, h = u1 - u0, yb - ya
    if w < 1.5 or h < 1.5:
        return 0
    col_t = vr("panneau_mur_tache", rng, 0.03)
    tw = max(1.0, _q(float(rng.uniform(0.45, 0.9)) * w))
    tx = _q(u0 + float(rng.uniform(0, max(0.0, w - tw))))
    h1 = max(0.5, _q(h * float(rng.uniform(0.3, 0.45))))
    top = _q(yb)
    _deco(b, (tx, top - h1, z0), (tx + tw, top, z1), col_t, name="Tache")
    n = 1
    xa, xb, y = tx, tx + tw, top - h1
    for k in range(1, morceaux):
        lw = max(0.5, _q((xb - xa) * float(rng.uniform(0.35, 0.6))))
        if lw >= xb - xa:
            break
        lx = _q(xa + float(rng.uniform(0, (xb - xa) - lw)))
        lh = max(0.5, _q(h * float(rng.uniform(0.15, 0.3))))
        if y - lh < ya or lx + lw > xb or lx < xa:
            break
        _deco(b, (lx, y - lh, z0), (lx + lw, y, z1), col_t, name="Coulure")
        n += 1
        xa, xb, y = lx, lx + lw, y - lh
    return n


def _pan_mur(b, x0: float, x1: float, y0: float, y1: float, ep: float, rng, faces=(1, -1), taches: int = 2,
             couleur=None) -> int:
    """Grand panneau gris clair du mur d'enceinte (x0..x1, épaisseur `ep` centrée sur z = 0) et ses taches
    plus sombres en saillie de 0,1 sur les faces demandées (+1 : face +Z, -1 : face -Z). Renvoie le nombre de
    pièces posées."""
    n = 0
    b.box((x0, y0, -ep / 2), (x1, y1, ep / 2), couleur or tirer(["panneau_mur", "panneau_mur_clair"], rng),
          name="Panneau")
    n += 1
    w, h = x1 - x0, y1 - y0
    for sz in faces:
        z_a, z_b = sorted((sz * ep / 2, sz * (ep / 2 + 0.1)))
        # taches en coulure dans des cases disjointes : sous la couvertine (moitié gauche ou droite), et une plus
        # petite en bas de l'autre moitié
        gauche = rng.random() < 0.5
        xm = (x0 + x1) / 2
        cases = [((x0 + 0.5, xm - 0.25) if gauche else (xm + 0.25, x1 - 0.5), (y0 + h * 0.35, y1 - 0.2)),
                 ((xm + 0.25, x1 - 0.5) if gauche else (x0 + 0.5, xm - 0.25), (y0 + h * 0.5, y1 - 0.2)),
                 ((x0 + 0.5, x1 - 0.5), (y0 + 0.6, y0 + h * 0.3))][:taches + 1]
        for (u0, u1), (ya, yb) in cases:
            n += _tache(b, u0, u1, ya, yb, z_a, z_b, rng, morceaux=3 if yb > y0 + h * 0.5 else 2)
    return n


def _pile_brique(b, x: float, y1: float, rng, larg: float = 2.0, prof: float = 4.0, cap: bool = True) -> int:
    """Pile de brique (larg × prof, centrée en x, z = 0) jusqu'à y1, avec un chapeau stud."""
    b.box((x - larg / 2, 0, -prof / 2), (x + larg / 2, y1, prof / 2), tirer(["brique", "brique_fonce", "brique_claire"], rng),
          material="Brick", name="PileBrique")
    if cap:
        b.box((x - larg / 2 - 0.3, y1, -prof / 2 - 0.3), (x + larg / 2 + 0.3, y1 + 0.6, prof / 2 + 0.3), c("chaperon"),
              studs="top", name="ChapeauPile")
        return 2
    return 1


def _mur_avant(b, x0: float, x1: float, h: float, rng, s: int) -> int:
    """Mur d'enceinte avant entre x0 et x1 (côté s), épaisseur 3 centrée sur z = 0 : socle, panneaux tachés
    entre des piles de brique tous les ≈ 16 studs, couvertine stud, pile d'angle 4 × 4 au bout."""
    n = 0
    xa, xb = sorted((s * x0, s * x1))
    b.box((xa, 0, -1.7), (xb, 0.8, 1.7), c("beton_fonce"), name="Soubassement")
    b.box((xa, h - 1, -1.9), (xb, h, 1.9), c("chaperon"), studs="top", name="Couvertine")
    n += 2
    L = x1 - x0
    nb = max(1, round(L / 16))
    pas = L / nb
    for i in range(nb):
        u0 = x0 + i * pas + (1.0 if i else 0.0)
        u1 = x0 + (i + 1) * pas - 1.0
        if i == nb - 1:
            u1 = x1 - 2.0              # la pile d'angle (4 × 4) ferme le dernier panneau
        pa, pb = sorted((s * u0, s * u1))
        n += _pan_mur(b, pa, pb, 0.8, h - 1, 3.0, rng)
        if i < nb - 1:
            n += _pile_brique(b, s * (x0 + (i + 1) * pas), h + 0.6, rng)
    # pile d'angle où commence le mur latéral (mur_campus)
    n += _pile_brique(b, s * x1, h + 0.8, rng, larg=4.0, prof=4.0)
    return n


def _camera_paroi(b, s: int, xo: float, xi: float, y: float, z: float, sz: int) -> int:
    """Caméra de sécurité sur la face d'un pylône tournée vers le passage (x de xo à xi, côté s), près d'une
    arête, regardant vers sz (±Z). Moins d'un stud de saillie, sans collision."""
    xa, xb = sorted((s * (xi - 0.3), s * xi))
    _deco(b, (xa, y - 0.2, z - 0.25), (xb, y + 0.4, z + 0.25), "acier_fonce", name="SupportCamera")
    xa, xb = sorted((s * (xo + 0.2), s * (xi - 0.3)))
    za, zb = sorted((z - sz * 0.5, z + sz * 0.5))
    _deco(b, (xa, y - 0.5, za), (xb, y + 0.2, zb), "blanc", name="Camera")
    za, zb = sorted((z + sz * 0.5, z + sz * 0.6))
    _deco(b, (xa + 0.1, y - 0.35, za), (xb - 0.1, y + 0.05, zb), "noir", name="Objectif")
    return 3


def portail_securite(b, variant: int = 0, ouverture: float = 100.0, hauteur: float = 48.0, profondeur: float = 16.0,
                     mur: float = 185.0, h_mur: float = 14.0) -> dict:
    """Grand portail de sécurité high-tech de l'académie, posé en travers de la route (yaw 0).

    Deux pylônes d'acier bleu nuit (x de ±ouverture/2 à ±(ouverture/2 + 24), z ∈ [-profondeur/2, profondeur/2]) :
    verrière bleu-violet en dégradé enfoncée de 1,5 dans des jambages profonds, cadre blanc, couronnement en
    pente vers l'extérieur ; un linteau (dessous à 40, coins chanfreinés jusqu'à 36 contre les pylônes) dont
    le contour intérieur est souligné d'un néon cyan continu ; une plaque violette lumineuse « ACADÉMIE » côté
    ville (+Z) et une plaque nue côté campus ; une guérite vitrée au pied du pylône gauche côté ville ; des
    caméras ; sur les faces tournées vers le passage, les tranches des barrières de sécurité escamotées derrière
    une vitre. Le mur d'enceinte avant (panneaux gris tachés, piles de brique) court jusqu'à |x| = mur.
    Rien dans |x| < ouverture/2 sous y = 36 ; aucun sol dans |x| < 52."""
    rng = b.rng
    xo = ouverture / 2                 # face du passage (les détails en saillie s'arrêtent là)
    xi = xo + 1.0                      # face intérieure du noyau et des jambages
    xe = xo + 24.0                     # face extérieure du pylône (le mur commence là)
    xm = xo + 12.0                     # début de la pente du couronnement
    zd = profondeur / 2
    zn = zd - 2.0                      # faces avant / arrière du noyau (fond de la verrière)
    zj = zd - 0.2                      # faces avant / arrière des jambages, du linteau et de la pente
    H = hauteur
    y_lin = 40.0                       # dessous du linteau (chanfreins jusqu'à 36 contre les pylônes)
    y_cour = H - 3.0                   # bas de la couronne
    ga, gb = xi + 2.5, xe - 3.5        # ouverture de la verrière en x
    n0 = len(b.parts)
    marine, marine_c = c("marine"), c("marine_clair")
    blanc = c("cadre_blanc")
    degrade = [mix(c("vitre_bleue"), c("vitre_violette"), t) for t in (0.0, 0.35, 0.7, 1.0)]

    for s in (-1, 1):
        cote = "Gauche" if s < 0 else "Droite"
        guerite = s < 0
        with b.group(f"Pylone{cote}"):
            def X(u):
                return s * u

            # socle stud et noyau d'acier bleu nuit
            b.box((X(xo), 0, -zd), (X(xe), 1.5, zd), c("acier_fonce"), studs="top", name="Socle")
            if guerite:
                # la guérite occupe le pied avant du pylône gauche, côté passage (x de xi + 0,5 à xi + 10,5, z ≥ 1)
                b.box((X(xi), 10.6, -zn), (X(xe - 1), y_lin, zn), marine, name="Noyau")
                b.box((X(xi), 1.5, -zn), (X(xe - 1), 10.6, 0.8), marine, name="Noyau")
                b.box((X(xi + 10.5), 1.5, 0.8), (X(xe - 1), 10.6, zn), marine, name="Noyau")
            else:
                b.box((X(xi), 1.5, -zn), (X(xe - 1), y_lin, zn), marine, name="Noyau")
            # couronnement en pente vers l'extérieur (studs sur la pente)
            b.wedge((X(xm), y_lin, -zj), (X(xe - 1), H, zj), marine_c, down="+x" if s > 0 else "-x", studs="top",
                    name="Pente")

            for sz in (1, -1):
                def Z(a, e):
                    return sorted((sz * a, sz * e))

                face_guerite = guerite and sz > 0
                gy0 = 13.0 if face_guerite else 4.0
                gy1 = 38.0
                # jambages profonds autour de la verrière (le fond est le noyau en z = zn)
                za, zb = Z(zn, zj)
                y_jamb = 10.6 if face_guerite else 1.5
                b.box((X(xi), y_jamb, za), (X(ga), y_lin, zb), marine, name="Jambage")
                b.box((X(gb), 1.5, za), (X(xe - 1), y_lin, zb), marine, name="Jambage")
                b.box((X(ga), gy1, za), (X(gb), y_lin, zb), marine, name="Linteau")
                if face_guerite:
                    b.box((X(ga), 10.6, za), (X(gb), gy0, zb), marine, name="Appui")
                    b.box((X(xi + 10.5), 1.5, za), (X(gb), 10.6, zb), marine, name="Appui")
                else:
                    b.box((X(ga), 1.5, za), (X(gb), gy0, zb), marine, name="Appui")
                # verrière en dégradé bleu → violet (4 rangs), montants et traverses blancs, reflets
                rangs = [gy0 + (gy1 - gy0) * k / 4 for k in range(5)]
                za, zb = Z(zn, zn + 0.3)
                for k in range(4):
                    b.box((X(ga), rangs[k], za), (X(gb), rangs[k + 1], zb), vary(degrade[k], rng, 0.02), name="Verriere")
                xc = (ga + gb) / 2
                za, zb = Z(zn, zn + 0.7)
                _deco(b, (X(xc - 0.4), gy0, za), (X(xc + 0.4), gy1, zb), blanc, name="Montant")
                za, zb = Z(zn, zn + 0.6)
                for k in (1, 2, 3):
                    for u0, u1 in ((ga, xc - 0.4), (xc + 0.4, gb)):
                        _deco(b, (X(u0), rangs[k] - 0.3, za), (X(u1), rangs[k] + 0.3, zb), blanc, name="Traverse")
                za, zb = Z(zn + 0.3, zn + 0.4)
                for u0, u1, v0, v1 in ((ga + 1.0, ga + 2.2, rangs[3] + 2.0, gy1 - 1.0),
                                       (ga + 2.2, ga + 3.0, rangs[3] + 0.8, rangs[3] + 4.0),
                                       (xc + 1.5, xc + 2.5, rangs[1] + 1.5, rangs[2] - 1.5)):
                    _deco(b, (X(u0), v0, za), (X(u1), v1, zb), "vitre_reflet", name="Reflet")
                # cadre blanc sur le nu des jambages, arête blanche extérieure
                za, zb = Z(zj, zd)
                b.box((X(ga - 0.6), gy0 - 0.6, za), (X(ga), gy1 + 0.6, zb), blanc, name="Cadre")
                b.box((X(gb), gy0 - 0.6, za), (X(gb + 0.6), gy1 + 0.6, zb), blanc, name="Cadre")
                b.box((X(ga), gy0 - 0.6, za), (X(gb), gy0, zb), blanc, name="Cadre")
                b.box((X(ga), gy1, za), (X(gb), gy1 + 0.6, zb), blanc, name="Cadre")
                b.box((X(xe - 1.8), 1.5, za), (X(xe - 1.0), y_lin, zb), blanc, name="Arete")
                # néon cyan : arête intérieure (contour du passage), bande sous la verrière
                _neon(b, (X(xi + 0.2), y_jamb + 0.6, za), (X(xi + 1.0), 36.2, zb), "neon_cyan", name="NeonContour")
                _neon(b, (X(ga), gy0 - 2.2, za), (X(gb), gy0 - 1.7, zb), "neon_cyan", name="BandeLumineuse")
                # néon sur la face tournée vers le passage, le long de l'arête
                za, zb = Z(zn + 0.4, zj - 0.4)
                _neon(b, (X(xo + 0.8), y_jamb + 0.6, za), (X(xi), 36.0, zb), "neon_cyan", name="NeonPassage")
                # pente : arête blanche et néon cyan le long du couronnement
                za, zb = Z(zj, zd)
                p0, p1 = (X(xm), H), (X(xe - 1), y_lin)
                d = 0.5
                _diag(b, (p0[0], p0[1] - d), (p1[0] + s * 0.2, p1[1] - d), 1.0, za, zb, blanc, name="AretePente")
                _diag(b, (p0[0], p0[1] - 2.2), (p1[0] - s * 0.6, p1[1] - 1.6), 0.4, za, zb, "neon_cyan",
                      material="Neon", collide=False, shadow=False, name="NeonPente")
                # caméra sur la face du passage, près de l'arête, tournée vers l'extérieur
                _camera_paroi(b, s, xo, xi, 35.0, sz * 5.0, sz)

            # face tournée vers le passage : tranches des barrières escamotées derrière une vitre
            with b.group("Barriere"):
                ys0, ys1 = (12.0 if guerite else 4.0), 33.0
                zs = zn - 0.6
                b.box((X(xo + 0.8), ys0, -zs), (X(xi), ys1, zs), c("vitre_nuit"), name="Fente")
                nb = 4
                pas = 2 * zs / nb
                for k in range(nb):
                    z0 = -zs + k * pas + 0.4
                    z1 = -zs + (k + 1) * pas - 0.4
                    b.box((X(xo + 0.45), ys0 + 0.4, z0), (X(xo + 0.8), ys1 - 0.4, z1), vr("acier", rng, 0.04),
                          collide=False, name="TrancheBarriere")
                    _deco(b, (X(xo + 0.35), ys0 + 0.4, (z0 + z1) / 2 - 0.15), (X(xo + 0.45), ys1 - 0.4, (z0 + z1) / 2 + 0.15),
                          "danger_jaune", name="LisereDanger")
                _neon(b, (X(xo + 0.38), (ys0 + ys1) / 2 - 0.2, -zs + 0.2), (X(xo + 0.48), (ys0 + ys1) / 2 + 0.2, zs - 0.2),
                      "neon_cyan", name="Veilleuse")
                _verre(b, (X(xo + 0.2), ys0, -zs), (X(xo + 0.35), ys1, zs), "vitre_claire", 0.5, collide=False, name="VitreBarriere")
                for z0, z1 in ((-zs - 0.6, -zs), (zs, zs + 0.6)):
                    b.box((X(xo), ys0 - 0.6, z0), (X(xo + 0.8), ys1 + 0.6, z1), blanc, name="CadreFente")
                b.box((X(xo), ys0 - 0.6, -zs), (X(xo + 0.8), ys0, zs), blanc, name="CadreFente")
                b.box((X(xo), ys1, -zs), (X(xo + 0.8), ys1 + 0.6, zs), blanc, name="CadreFente")

            # face extérieure au-dessus du mur : deux bandes lumineuses
            for y in (24.0, 32.0):
                _neon(b, (X(xe - 1), y, -zn), (X(xe - 0.8), y + 0.4, zn), "neon_cyan", name="BandeLumineuse")
            # toit : édicule, mât à capteur
            xt = (xi + xm) / 2
            b.box((X(xt - 4), H, -3), (X(xt + 4), H + 1.5, 3), c("beton_clair"), studs="top", name="Edicule")
            b.cyl((X(xt + 2), H + 3.0, 0), 0.3, 3.0, c("acier"), collide=False, name="Mat")
            b.ball((X(xt + 2), H + 4.8, 0), 0.6, c("neon_cyan"), material="Neon", collide=False, shadow=False, name="Capteur")

    # --- guérite vitrée au pied du pylône gauche, côté ville ---
    with b.group("Guerite"):
        xa, xb = -(xi + 10.5), -(xi + 0.5)
        b.box((xa, 1.5, 1.0), (xb, 10.0, 3.6), c("fenetre_lumiere"), material="Neon", name="Interieur")
        b.box((xa + 1.0, 1.5, 3.6), (xb - 1.0, 4.0, 5.2), c("marine_clair"), name="Bureau")
        for k in range(2):
            u = xa + 2.0 + k * 3.4
            _deco(b, (u, 4.0, 4.0), (u + 2.4, 5.8, 4.4), "ecran_lumiere", material="Neon", shadow=False, name="Ecran")
        _verre(b, (xa, 1.5, zj - 0.4), (xb, 10.0, zj), "vitre_claire", 0.4, name="VitreGuerite")
        _verre(b, (xb, 1.5, 1.0), (xb + 0.4, 10.0, zj - 0.6), "vitre_claire", 0.4, name="VitreGuerite")
        b.box((xb - 0.1, 1.5, zj - 0.6), (xb + 0.6, 10.0, zj + 0.15), blanc, name="Montant")
        _deco(b, (xa + 1.0, 4.2, zj), (xb - 1.0, 4.6, zj + 0.2), "blanc", name="Comptoir")
        b.box((xa - 0.5, 10.0, 0.8), (xb + 1.3, 10.6, zd), blanc, studs="top", name="Auvent")
        _neon(b, (xa - 0.3, 9.6, zd - 0.3), (xb + 1.1, 10.0, zd), "neon_cyan", name="Liseré")

    # --- linteau, couronne et plaques ---
    with b.group("Linteau"):
        b.box((-xm, y_lin, -zj), (xm, y_cour, zj), marine, name="Linteau")
        b.box((-xm, y_cour, -zj), (xm, H - 1.0, zj), marine_c, name="Couronne")
        b.box((-xm, H - 1.0, -zd), (xm, H, zd), blanc, studs="top", name="Chaperon")
        for s in (-1, 1):
            # chanfreins des angles du passage (36 contre le pylône, 36,5 en |x| = ouverture / 2)
            xa, xb = sorted((s * (xi - 8.0), s * xi))
            b.wedge_under((xa, 36.0, -zj), (xb, y_lin, zj), marine, down="-x" if s > 0 else "+x", name="Chanfrein")
        for sz in (1, -1):
            def Z(a, e):
                return sorted((sz * a, sz * e))

            # contour lumineux cyan : bas du linteau et chanfreins
            za, zb = Z(zj, zd)
            _neon(b, (-(xi - 8.0), y_lin - 0.1, za), (xi - 8.0, y_lin + 0.4, zb), "neon_cyan", name="NeonContour")
            for s in (-1, 1):
                # barre décalée vers l'intérieur du chanfrein : son bord bas suit l'hypoténuse
                _diag(b, (s * (xi - 7.9), y_lin + 0.27), (s * (xi + 0.1), 36.27), 0.45, za, zb, "neon_cyan",
                      material="Neon", collide=False, shadow=False, name="NeonContour")
            # bandeau vitré du linteau de part et d'autre de la plaque, montants et lisérés blancs (tout tient
            # dans z ∈ [-zd, zd])
            zv0, zv1 = Z(zj, zj + 0.1)
            za2, zb2 = Z(zj + 0.1, zd)
            zl0, zl1 = Z(zj, zd)
            for s in (-1, 1):
                xa, xb = sorted((s * 15.0, s * (xi - 4)))
                b.box((xa, y_lin + 1.6, zv0), (xb, y_cour - 0.8, zv1), vr("vitre_bleue", rng, 0.02), name="BandeauVitre")
                for k in (2, 3, 4):
                    _deco(b, (s * k * 11.0 - 0.4, y_lin + 1.6, za2), (s * k * 11.0 + 0.4, y_cour - 0.8, zb2), blanc,
                          name="Montant")
                b.box((xa, y_lin + 1.2, zl0), (xb, y_lin + 1.6, zl1), blanc, name="Liseré")
                b.box((xa, y_cour - 0.8, zl0), (xb, y_cour - 0.4, zl1), blanc, name="Liseré")
            # bande lumineuse sur la couronne, sur toute la largeur
            za3, zb3 = Z(zj, zd)
            _neon(b, (-xm, y_cour + 0.8, za3), (xm, y_cour + 1.2, zb3), "neon_cyan", name="BandeCouronne")
            # plaque centrale lumineuse : violette, filet lavande ; « ACADÉMIE » côté ville
            za4, zb4 = Z(zj, zj + 0.1)
            b.box((-15.0, y_lin + 0.6, za4), (15.0, y_cour + 0.4, zb4), c("lavande"), name="FiletPlaque")
            za5, zb5 = Z(zj + 0.1, zd)
            p = b.box((-14.2, y_lin + 1.3, za5), (14.2, y_cour - 0.3, zb5), c("violet"), material="Neon", name="Plaque")
            if sz > 0:
                _label(p, "ACADÉMIE", face="Back", couleur=(255, 255, 255), fond=c("violet"), glow=1.5)
            else:
                # côté campus : trois chevrons en pixels blancs lumineux (sans texte), saillie 0,15
                ya_, yb_ = y_lin + 1.3, y_cour - 0.3
                cel = 0.9
                n_ = 5
                y_top = (ya_ + yb_) / 2 + (n_ * cel + cel) / 2
                for xc in (-8.5, 0.0, 8.5):
                    for k in range(n_):
                        y_ = y_top - k * cel
                        for sx_ in ((0,) if k == 0 else (-1, 1)):
                            x_ = xc + sx_ * k * cel
                            _neon(b, (x_ - cel / 2, y_ - 2 * cel, -zd - 0.15), (x_ + cel / 2, y_, -zd), "neon_blanc",
                                  name="Chevron")
        # dessous du linteau : bande vitrée et filet lumineux blanc, capteurs
        _verre(b, (-(xi - 8.5), y_lin - 0.4, -4.0), (xi - 8.5, y_lin, 4.0), "vitre_claire", 0.25, collide=False, name="VitreSousFace")
        _neon(b, (-(xi - 9.0), y_lin - 0.6, -0.6), (xi - 9.0, y_lin - 0.4, 0.6), "neon_blanc", name="FiletSousFace")
        for x in (-30.0, -10.0, 10.0, 30.0):
            b.ball((x, y_lin - 0.4, 3.0), 0.5, c("blanc"), collide=False, name="Capteur")

    n_portail = len(b.parts) - n0
    # --- mur d'enceinte avant, de part et d'autre ---
    with b.group("MurAvant"):
        for s in (-1, 1):
            _mur_avant(b, xe - 1.0, mur, h_mur, rng, s)
    return {"emprise": (2 * mur + 4, profondeur), "hauteur": H + 5.4, "pieces_portail": n_portail,
            "pieces_mur": len(b.parts) - n0 - n_portail}


# ---------------------------------------------------------------------------
# 3. Viaduc ferroviaire et train de banlieue
# ---------------------------------------------------------------------------

def _voiture_train(b, x0: float, x1: float, zt: float, yr: float, rng, nez_g: bool, nez_d: bool,
                   pantographe: bool, y_cat: float) -> None:
    """Voiture de train de banlieue de x0 à x1 (le long de X) sur la voie centrée en z = zt (dessus des rails
    à yr) : caisse blanche, bande bleue et filet violet, bandeau vitré sombre, portes, toit gris clair et
    climatiseur, bogies ; nez inclinés aux extrémités du train (nez_g côté -x, nez_d côté +x)."""
    blanc = vr("train_blanc", rng, 0.015)
    yb0, yb1 = yr + 1.4, yr + 6.0             # caisse
    w = 2.3
    L = x1 - x0
    # bogies et châssis
    for xb in (x0 + 3.5, x1 - 3.5):
        b.box((xb - 1.8, yr, zt - 1.6), (xb + 1.8, yr + 1.1, zt + 1.6), c("noir"), name="Bogie")
    b.box((x0 + 0.8, yr + 0.9, zt - w + 0.2), (x1 - 0.8, yb0, zt + w - 0.2), c("acier_fonce"), name="Chassis")
    # caisse, bandes enveloppantes (dépassent de 0,1), toit
    b.box((x0, yb0, zt - w), (x1, yb1, zt + w), blanc, name="Caisse")
    b.box((x0 - 0.1, yr + 2.2, zt - w - 0.1), (x1 + 0.1, yr + 2.9, zt + w + 0.1), c("train_bande"), name="BandeBleue")
    b.box((x0 - 0.1, yr + 3.05, zt - w - 0.1), (x1 + 0.1, yr + 3.35, zt + w + 0.1), c("train_bande2"), name="BandeViolette")
    b.box((x0 - 0.1, yr + 3.7, zt - w - 0.1), (x1 + 0.1, yr + 5.3, zt + w + 0.1), c("vitre_nuit"), name="Vitrage")
    b.box((x0 + 0.2, yb1, zt - w + 0.3), (x1 - 0.2, yb1 + 0.5, zt + w - 0.3), c("beton_clair"), studs="top", name="Toit")
    xm = (x0 + x1) / 2
    b.box((xm - 2.6 + (L * 0.2 if pantographe else 0), yb1 + 0.5, zt - 1.3),
          (xm + 2.6 + (L * 0.2 if pantographe else 0), yb1 + 1.2, zt + 1.3), c("acier"), studs="top", name="Climatiseur")
    # portes : trois de chaque côté, gris clair à hublot sombre (dépassent les bandes de 0,1)
    for sz in (-1, 1):
        za, zb = sorted((zt + sz * (w + 0.1), zt + sz * (w + 0.2)))
        for t in (0.2, 0.5, 0.8):
            xd = x0 + L * t
            b.box((xd - 1.2, yr + 1.6, za), (xd + 1.2, yr + 5.6, zb), c("acier"), collide=False, name="Porte")
            za2, zb2 = sorted((zt + sz * (w + 0.2), zt + sz * (w + 0.3)))
            _deco(b, (xd - 0.8, yr + 3.8, za2), (xd + 0.8, yr + 5.2, zb2), "vitre_nuit", name="HublotPorte")
    # nez inclinés : bloc bas (bande bleue, phares) et pare-brise en pente
    for actif, sx, xb in ((nez_g, -1, x0), (nez_d, 1, x1)):
        if not actif:
            continue
        xa, xc = sorted((xb, xb + sx * 2.4))
        b.box((xa, yb0, zt - w), (xc, yr + 3.7, zt + w), blanc, name="Nez")
        b.wedge((xa, yr + 3.7, zt - w), (xc, yb1, zt + w), c("vitre_nuit"), down="-x" if sx < 0 else "+x",
                name="PareBrise")
        xa2, xc2 = sorted((xb + sx * 0.1, xb + sx * 2.5))
        b.box((xa2, yr + 2.2, zt - w - 0.1), (xc2, yr + 2.9, zt + w + 0.1), c("train_bande"), name="BandeBleue")
        xf = xb + sx * 2.4
        for zz in (zt - 1.5, zt + 1.5):
            xa3, xc3 = sorted((xf, xf + sx * 0.1))
            _neon(b, (xa3, yr + 1.7, zz - 0.4), (xc3, yr + 2.1, zz + 0.4), "phare", name="Phare")
    if pantographe:
        xp = xm - L * 0.2
        _deco(b, (xp - 1.0, yb1 + 0.5, zt - 1.0), (xp + 1.0, yb1 + 0.9, zt + 1.0), "acier_fonce", name="SocleCaptage")
        y_haut = y_cat - 0.1
        _segment(b, (xp - 0.8, yb1 + 0.9, zt), (xp + 0.6, (yb1 + 0.9 + y_haut) / 2, zt), 0.1, c("acier_fonce"), name="Bras")
        _segment(b, (xp + 0.6, (yb1 + 0.9 + y_haut) / 2, zt), (xp - 0.2, y_haut - 0.1, zt), 0.1, c("acier_fonce"), name="Bras")
        _deco(b, (xp - 0.5, y_haut - 0.2, zt - 1.3), (xp + 0.1, y_haut, zt + 1.3), "acier", name="Archet")


def viaduc_train(b, variant: int = 0, longueur: float = 478.0, hauteur: float = 36.0, passage: float = 112.0) -> dict:
    """Viaduc ferroviaire urbain le long de X (x de -longueur/2 à +longueur/2), posé en travers de la route
    (yaw 0), avec un train de banlieue arrêté au-dessus de la route.

    Tablier en caisson de béton clair (12 de large, z ∈ [-6, 6]) dont le DESSOUS est à `hauteur` et le dessus
    à hauteur + 4, en tronçons d'environ 60 ; écrans antibruit blancs à vitrage clair, deux voies (ballast et
    rails), portiques caténaires tous les ≈ 24, liseré lumineux blanc le long des deux arêtes basses. Piles en T
    (fût 4 × 4, chapiteau évasé) seulement en |x| ≥ passage/2 + 2. Train : trois voitures de 24 sur la voie +Z.
    Rien sous y = hauteur dans |x| < passage/2 ; les deux faces sont soignées (aller et retour).
    variant : couleur du filet décoratif du tablier (0 bleu, 1 violet, 2 cyan lumineux)."""
    rng = b.rng
    H = hauteur
    yt = H + 4.0                      # dessus du tablier
    yr = yt + 0.9                     # dessus des rails
    y_cat = yt + 8.5                  # fil de contact (touche le dessous des traverses des portiques)
    demi = longueur / 2
    zv = 2.6                          # axes des voies (z = ±zv)
    n0 = len(b.parts)
    filet = ("train_bande", "train_bande2", "neon_cyan")[variant % 3]

    with b.group("Tablier"):
        nseg = max(1, round(longueur / 60))
        pas = longueur / nseg
        for i in range(nseg):
            xa, xb = -demi + i * pas, -demi + (i + 1) * pas
            ton = c("viaduc") if i % 2 == 0 else mix(c("viaduc"), c("viaduc_fonce"), 0.35)
            b.box((xa, H, -4.5), (xb, H + 2.5, 4.5), c("viaduc_fonce"), name="Caisson")
            b.box((xa, H + 2.5, -6), (xb, yt, 6), ton, name="Hourdis")
            b.wedge_under((xa, H + 1.5, 4.5), (xb, H + 2.5, 6), c("viaduc_fonce"), down="+z", name="Console")
            b.wedge_under((xa, H + 1.5, -6), (xb, H + 2.5, -4.5), c("viaduc_fonce"), down="-z", name="Console")
            for sz in (-1, 1):
                za, zb = sorted((sz * 4.5, sz * 4.75))
                _neon(b, (xa, H, za), (xb, H + 0.3, zb), "neon_blanc", name="LisereLumineux")
                za, zb = sorted((sz * 6.0, sz * 6.1))
                kw = dict(material="Neon", shadow=False) if filet == "neon_cyan" else {}
                _deco(b, (xa, H + 3.0, za), (xb, H + 3.4, zb), filet, name="Filet", **kw)
                # écran antibruit : muret blanc et vitrage clair au-dessus
                za, zb = sorted((sz * 5.4, sz * 6.0))
                b.box((xa, yt, za), (xb, yt + 1.8, zb), c("blanc"), studs="top", name="EcranAntibruit")
                za, zb = sorted((sz * 5.6, sz * 5.8))
                _verre(b, (xa, yt + 1.8, za), (xb, yt + 2.8, zb), "vitre_claire", 0.45, collide=False, name="VitreAntibruit")
                # voie : ballast et deux rails
                za, zb = sorted((sz * (zv - 1.7), sz * (zv + 1.7)))
                b.box((xa, yt, za), (xb, yt + 0.5, zb), BALLAST, name="Ballast")
                for dz in (-0.75, 0.75):
                    zr = sz * zv + dz
                    b.box((xa, yt + 0.5, zr - 0.15), (xb, yr, zr + 0.15), c("rail"), name="Rail")

    with b.group("Catenaires"):
        nport = max(2, round(longueur / 24))
        pasp = longueur / nport
        for i in range(nport):
            x = -demi + (i + 0.5) * pasp
            for sz in (-1, 1):
                b.cyl((x, yt + 1.8 + 3.5, sz * 5.7), 0.22, 7.0, c("acier"), collide=False, name="Poteau")
            b.box((x - 0.2, yt + 8.6, -5.9), (x + 0.2, yt + 9.0, 5.9), c("acier"), collide=False, name="Traverse")
        for i in range(nseg):
            xa, xb = -demi + i * pas, -demi + (i + 1) * pas
            for sz in (-1, 1):
                b.cyl(((xa + xb) / 2, y_cat, sz * zv), 0.1, xb - xa, c("acier_fonce"), axis="x", collide=False,
                      shadow=False, name="FilContact")

    with b.group("Piles"):
        x = passage / 2 + 4.0
        while x < demi - 8:
            for s in (-1, 1):
                xc = s * x
                b.box((xc - 3.5, 0, -3.5), (xc + 3.5, 1.0, 3.5), c("beton"), studs="top", name="Semelle")
                b.box((xc - 2, 1.0, -2), (xc + 2, H - 3.0, 2), vr("viaduc", rng, 0.02), name="Fut")
                b.box((xc - 2, H - 3.0, -5.5), (xc + 2, H, 5.5), c("viaduc"), name="Chapiteau")
                b.wedge_under((xc - 2, H - 6.0, 2), (xc + 2, H - 3.0, 5.5), c("viaduc"), down="+z", name="Evasement")
                b.wedge_under((xc - 2, H - 6.0, -5.5), (xc + 2, H - 3.0, -2), c("viaduc"), down="-z", name="Evasement")
                for sz in (-1, 1):
                    za, zb = sorted((sz * 2.0, sz * 2.1))
                    _deco(b, (xc - 1.2, 3.0, za), (xc + 1.2, 3.4, zb), filet, name="Bague",
                          **(dict(material="Neon", shadow=False) if filet == "neon_cyan" else {}))
            x += 47.0

    with b.group("Train"):
        n = 3
        Lv, gap = 24.0, 1.0
        x_start = -(n * Lv + (n - 1) * gap) / 2
        for i in range(n):
            x0 = x_start + i * (Lv + gap)
            _voiture_train(b, x0, x0 + Lv, zv, yr, rng, i == 0, i == n - 1, i == 1, y_cat)
            if i:
                b.box((x0 - gap, yr + 1.8, zv - 1.4), (x0, yr + 5.6, zv + 1.4), c("noir"), name="Soufflet")
    return {"emprise": (longueur, 12.0), "hauteur": round(yt + 9.0, 2), "dessous": H, "pieces": len(b.parts) - n0}


# ---------------------------------------------------------------------------
# 1. Boutiques de la rue
# ---------------------------------------------------------------------------

ENSEIGNES = {
    # texte : (fond, texte) ; aucune marque réelle
    "CAFÉ": ("#5A3B2A", "blanc"),
    "FLEURS": ("fleur_rose", "blanc"),
    "LIVRES": ("marine", "jaune"),
    "MARCHÉ": ("blanc", "violet"),
    "RAMEN": ("rouge", "blanc"),
    "BOULANGERIE": ("store_jaune", "#5A3B2A"),
    "SPORT": ("bleu_vif", "blanc"),
    "PHARMACIE": ("blanc", "bleu_vif"),
}
PASTELS = ("#F6C8D0", "#F9D9B6", "#DCD4FA", "#F7E7A8", "#CFE5F7")   # façades pastel des immeubles étroits
MARCHANDISES = ("fleur_rose", "store_jaune", "bleu_vif", "violet", "orange", "feuille_claire", "lavande", "rouge")


def _ruban(b, xa: float, xb: float, ya: float, yb: float, zf: float, rng, verre="vitre_nuit", cadre="cadre_blanc",
           pas: float = 3.5, reflet: bool = True) -> None:
    """Ruban de fenêtres sur une façade (plan z = zf, extérieur vers -z) : appui et linteau blancs, vitrage
    sombre en saillie de 0,2, meneaux blancs en saillie de 0,35, petit reflet clair."""
    b.box((xa - 0.3, ya - 0.4, zf - 0.5), (xb + 0.3, ya, zf), col(cadre), name="Appui")
    b.box((xa, ya, zf - 0.2), (xb, yb, zf), vr(verre, rng, 0.04), name="Fenetre")
    b.box((xa - 0.3, yb, zf - 0.3), (xb + 0.3, yb + 0.3, zf), col(cadre), name="Linteau")
    n = max(1, round((xb - xa) / pas))
    for k in range(1, n):
        x = xa + (xb - xa) * k / n
        _deco(b, (x - 0.15, ya, zf - 0.35), (x + 0.15, yb, zf), cadre, name="Meneau")
    if reflet:
        u = xa + 0.6 + float(rng.uniform(0, max(0.1, (xb - xa) / n - 1.6)))
        _deco(b, (u, ya + 0.5, zf - 0.3), (u + 0.6, yb - 0.4, zf - 0.2), "vitre_reflet", name="Reflet")


def _vitrine(b, xa: float, xb: float, yv: float, zf: float, rec: float, rng, cadre, porte: int | None = None,
             pas: float = 3.5) -> tuple:
    """Vitrine de rez-de-chaussée entre deux piliers (x de xa à xb, sous yv), dans un renfoncement de `rec`
    devant le plan z = zf : fond éclairé, rayonnages, glace transparente, soubassement, imposte, meneaux, porte
    vitrée dans la travée `porte` et marche. Renvoie (x0_porte, x1_porte)."""
    zr = zf + rec
    b.box((xa, 0, zr - 0.2), (xb, yv, zr), col(INTERIEUR_BOUTIQUE), material="Neon", shadow=False, name="FondEclaire")
    # rayonnages et comptoir vus à travers la vitre
    w = xb - xa
    for k, (u0, u1, h) in enumerate(((0.06, 0.3, yv - 2.4), (0.7, 0.94, yv - 2.4), (0.38, 0.62, 2.6))):
        _deco(b, (xa + w * u0, 0, zr - 0.6), (xa + w * u1, h, zr - 0.2),
              ETAGERE if k < 2 else tirer(list(MARCHANDISES), rng), name="Rayon")
    _verre(b, (xa, 0.6, zf + 0.6), (xb, yv - 0.5, zf + 0.8), "vitre_claire", 0.6, collide=True, name="Vitrine")
    b.box((xa, 0, zf + 0.5), (xb, 0.6, zf + 0.9), c("acier_fonce"), name="Soubassement")
    b.box((xa, yv - 0.5, zf + 0.4), (xb, yv, zf + 1.0), col(cadre), name="Imposte")
    nb = max(2, round(w / pas))
    bw = w / nb
    for k in range(1, nb):
        x = xa + k * bw
        _deco(b, (x - 0.15, 0.6, zf + 0.4), (x + 0.15, yv - 0.5, zf + 0.6), cadre, name="Meneau")
    kd = (nb // 2) if porte is None else max(0, min(nb - 1, porte))
    xd0, xd1 = xa + kd * bw + 0.15, xa + (kd + 1) * bw - 0.15
    _verre(b, (xd0, 0.4, zf + 0.45), (xd1, yv - 0.9, zf + 0.6), "vitre_ciel", 0.45, collide=False, name="Porte")
    _deco(b, (xd1 - 0.7, 2.4, zf + 0.25), (xd1 - 0.45, 4.6, zf + 0.45), "acier", name="Poignee")
    b.box((xd0 - 0.4, 0, zf - 0.8), (xd1 + 0.4, 0.4, zf + 0.5), c("beton_clair"), studs="top", name="Marche")
    return xd0, xd1


def _accessoire(b, enseigne, x0: float, x1: float, zf: float, porte: tuple, rng) -> None:
    """Petit accessoire de devanture selon le commerce (≤ 4 pièces, ≤ 1,5 devant la façade, sans collision)."""
    xd0, xd1 = porte
    libre = (x0 + 1.2, xd0 - 0.6) if xd0 - x0 > x1 - xd1 else (xd1 + 0.6, x1 - 1.2)   # côté le plus large
    if libre[1] - libre[0] < 2.2:
        return
    u0, u1 = libre[0], min(libre[1], libre[0] + 3.6)
    if enseigne == "FLEURS":
        _deco(b, (u0, 0, zf - 1.4), (u1, 1.0, zf - 0.2), "bois", name="Etal")
        t = (u1 - u0) / 3
        for k, f in enumerate(("fleur_rose", "fleur_jaune", "fleur_violette")):
            _deco(b, (u0 + k * t + 0.1, 1.0, zf - 1.3), (u0 + (k + 1) * t - 0.1, 1.8, zf - 0.3), f, name="Fleurs")
    elif enseigne == "LIVRES":
        _deco(b, (u0, 0, zf - 1.3), (u1, 1.4, zf - 0.2), "bois_fonce", name="Bac")
        _deco(b, (u0 + 0.2, 1.4, zf - 1.2), (u1 - 0.2, 2.0, zf - 0.75), tirer(["rouge", "bleu_vif", "jaune"], rng), name="Livres")
        _deco(b, (u0 + 0.2, 1.4, zf - 0.7), (u1 - 0.2, 2.2, zf - 0.3), tirer(["violet", "feuille_claire", "orange"], rng), name="Livres")
    elif enseigne == "CAFÉ":
        for x in (xd0 - 1.1, xd1 + 1.1):
            if x0 + 0.6 < x < x1 - 0.6:
                _deco(b, (x - 0.5, 0, zf - 1.2), (x + 0.5, 1.0, zf - 0.2), "beton_fonce", name="Pot")
                b.ball((x, 1.7, zf - 0.7), 0.75, vr("feuille_claire", rng, 0.05), collide=False, name="Arbuste")
    elif enseigne == "RAMEN":
        # noren indigo au-dessus de la porte et lanterne de papier rouge suspendue sous le store
        _deco(b, (xd0 - 0.2, 5.4, zf + 0.15), (xd1 + 0.2, 6.9, zf + 0.3), "marine", material="Fabric", name="Noren")
        xl = xd1 + 0.9
        if xl + 0.7 < x1 - 2.0:
            _deco(b, (xl - 0.1, 7.1, zf - 0.8), (xl + 0.1, 7.5, zf - 0.6), "noir", name="Crochet")
            b.cyl((xl, 6.45, zf - 0.7), 0.65, 1.3, c("rouge"), material="Neon", collide=False, shadow=False, name="Lanterne")
            _deco(b, (xl - 0.45, 5.7, zf - 1.15), (xl + 0.45, 5.8, zf - 0.25), "noir", name="Lanterne")
    elif enseigne == "BOULANGERIE":
        _deco(b, (u0, 0, zf - 1.0), (u0 + 1.4, 2.2, zf - 0.6), "noir", name="Ardoise")
        _deco(b, (u0 + 0.2, 0.9, zf - 1.1), (u0 + 1.2, 2.0, zf - 1.0), "blanc_casse", name="Menu")


def boutique(b, variant: int = 0, largeur: float = 16.0, profondeur: float = 16.0, etages: int = 2,
             enseigne: str | None = "CAFÉ") -> dict:
    """Boutique vitrée de rue japonaise moderne, avant vers -Z (la rue).

    Emprise exacte largeur (X) × profondeur (Z) ; hauteur 9 au rez-de-chaussée + 6,5 par étage (9 / 15,5 / 22 /
    28,5), plus l'acrotère et les équipements de toit (≤ 3). Devant la façade (≤ 1,5) : store, enseigne en
    drapeau, marche, accessoire. Rez : vitrine éclairée dans un renfoncement de 2, porte vitrée ; bandeau
    d'enseigne au-dessus du store (`enseigne`, ou bandeau uni si None) ; un ruban de fenêtres par étage.
    variant 0 façade carrelée blanche, store rayé rouge et blanc, climatiseurs en console, réservoir d'eau ;
    1 immeuble étroit pastel, enseigne verticale en drapeau, petits balcons vitrés ;
    2 étages en mur-rideau bleu ciel à montants blancs, cadre blanc, store bleu, cadre de panneau publicitaire vide ;
    3 supérette d'un seul niveau (etages ignoré) : bandeau violet / orange / lavande, enseigne de toit, niche à
    distributeurs, climatiseurs."""
    rng = b.rng
    v = variant % 4
    W, D = float(largeur), float(profondeur)
    if v == 3:
        return _superette(b, W, D, enseigne, rng)
    etages = max(1, int(etages))
    H = 9.0 + 6.5 * (etages - 1)
    x0, x1 = -W / 2, W / 2
    zf, zb = -D / 2, D / 2
    rec = 2.0
    yv = 7.5 if etages > 1 else 6.4
    fond, texte = ENSEIGNES.get(enseigne, ("violet", "blanc")) if enseigne else (None, None)
    if v == 0:
        mur = vr("carrelage", rng, 0.02)
        mur_av = c("facade_blanche")
        cadre = "cadre_blanc"
    elif v == 1:
        mur = vr(PASTELS[int(rng.integers(len(PASTELS)))], rng, 0.02)
        mur_av = mur
        cadre = "cadre_blanc"
    else:
        mur = c("facade_ciel")
        mur_av = c("blanc")
        cadre = "cadre_blanc"
    fond = fond or ("store_rouge", "lavande", "store_bleu")[v]

    with b.group("Volume"):
        b.box((x0, 0, zf + rec), (x1, H, zb), mur, studs="top", name="Corps")
        b.box((x0, yv, zf), (x1, H, zf + rec), mur_av, studs="top", name="Facade")
        b.box((x0, 0, zf), (x0 + 1, yv, zf + rec), mur_av, name="Pilier")
        b.box((x1 - 1, 0, zf), (x1, yv, zf + rec), mur_av, name="Pilier")
        # côtés : fenêtre haute de cage d'escalier (les boutiques d'about montrent leurs flancs)
        for k in range(1, etages):
            y0 = 9.0 + 6.5 * (k - 1)
            b.box((x0 - 0.1, y0 - 0.3, zf + 0.3), (x1 + 0.1, y0 + 0.2, zb + 0.1), shade(mur, 0.9), name="BandeauEtage")
            for sx in (-1, 1):
                xa, xc = sorted((sx * W / 2, sx * (W / 2 + 0.2)))
                za = zf + rec + 1.5 + (D - rec - 6.0) * (0.25 if k % 2 else 0.6)
                b.box((xa, y0 + 2.6, za), (xc, y0 + 5.4, za + 2.6), mix(c("vitre_nuit"), c("vitre_bleue"), 0.45),
                      name="FenetreCote")
    with b.group("RezDeChaussee"):
        porte = _vitrine(b, x0 + 1, x1 - 1, yv, zf, rec, rng, cadre, porte=0 if v == 1 else None)
        _accessoire(b, enseigne, x0, x1, zf, porte, rng)
        # store au-dessus de la vitrine (dessous à 7,5)
        if etages > 1:
            if v == 0:
                n_st = max(3, round((W - 1) / 1.8))
                sw = (W - 1) / n_st
                for k in range(n_st):
                    b.wedge((x0 + 0.5 + k * sw, 7.5, zf - 1.5), (x0 + 0.5 + (k + 1) * sw, 9.0, zf),
                            c("store_rouge") if k % 2 == 0 else c("blanc"), down="-z", material="Fabric",
                            collide=False, name="Store")
            elif v == 1:
                b.wedge((x0 + 0.5, 7.5, zf - 1.0), (x1 - 2.0, 8.7, zf), c("store_jaune"), down="-z", material="Fabric",
                        collide=False, name="Store")
            else:
                b.wedge((x0 + 0.5, 7.8, zf - 1.5), (x1 - 0.5, 9.0, zf), c("store_bleu"), down="-z", material="Fabric",
                        collide=False, name="Store")
                _deco(b, (x0 + 0.5, 7.5, zf - 1.5), (x1 - 0.5, 7.8, zf - 1.2), "blanc", material="Fabric", name="Lambrequin")
    with b.group("Enseigne"):
        if v == 1:
            # bandeau étroit uni et enseigne verticale en drapeau à l'angle droit
            y0b = 8.9 if etages > 1 else 6.6
            _deco(b, (x0 + 0.3, y0b, zf - 0.3), (x1 - 0.3, y0b + 0.7, zf), fond, name="Bandeau")
            hs = min(H - 8.1, max(5.0, 1.7 * len(enseigne or "") + 1.0))
            yb0 = 7.6
            p1 = _deco(b, (x1 - 0.95, yb0, zf - 1.5), (x1 - 0.65, yb0 + hs, zf), fond, name="Drapeau")
            p2 = _deco(b, (x1 - 0.65, yb0, zf - 1.5), (x1 - 0.35, yb0 + hs, zf), fond, name="Drapeau")
            _deco(b, (x1 - 1.05, yb0 + hs, zf - 1.5), (x1 - 0.25, yb0 + hs + 0.3, zf), "blanc", name="ChapeauDrapeau")
            if enseigne:
                _label(p1, enseigne, face="Left", couleur=col(texte), fond=col(fond), vertical=True)
                _label(p2, enseigne, face="Right", couleur=col(texte), fond=col(fond), vertical=True)
        else:
            ys0, ys1 = (9.2, 11.0) if etages > 1 else (6.6, 8.6)
            b.box((x0 + 0.2, ys0 - 0.2, zf - 0.3), (x1 - 0.2, ys1 + 0.2, zf), c("noir") if v == 0 else c("blanc"),
                  name="CadreEnseigne")
            p = b.box((x0 + 0.5, ys0, zf - 0.5), (x1 - 0.5, ys1, zf - 0.3), col(fond), name="Enseigne")
            if enseigne:
                _label(p, enseigne, face="Front", couleur=col(texte), fond=col(fond), glow=0.6)
            if v == 2 and etages > 1:
                _neon(b, (x0 + 0.4, H - 0.9, zf - 0.2), (x1 - 0.4, H - 0.6, zf), "neon_cyan", name="NeonCorniche")
    with b.group("Etages"):
        for k in range(1, etages):
            y0 = 9.0 + 6.5 * (k - 1)
            ya, yb = y0 + 2.6, y0 + 5.6
            if v == 0:
                _ruban(b, x0 + 1.5, x1 - 1.5, ya, yb, zf, rng, verre=mix(c("vitre_nuit"), c("vitre_bleue"), 0.45))
                # carreaux en pixels entre les étages (allège)
                if k < etages - 1:
                    _deco(b, (x0 + 0.3, yb + 0.3, zf - 0.1), (x1 - 0.3, y0 + 6.5 + 2.2, zf),
                          tirer(["carrelage", "blanc_casse", "beton_clair"], rng), name="Carreaux")
                if k >= 2 and k % 2 == 0:
                    _deco(b, (x1 - 3.6, y0 + 0.4, zf - 1.2), (x1 - 1.6, y0 + 1.8, zf), CLIM, name="Climatiseur")
                    _deco(b, (x1 - 3.4, y0 + 0.2, zf - 1.0), (x1 - 1.8, y0 + 0.4, zf), "acier_fonce", name="Console")
            elif v == 1:
                ys = y0 + 1.0
                b.box((x0 + 0.8, ys - 0.4, zf - 1.2), (x1 - 1.6, ys, zf), c("blanc"), studs="top", name="Balcon")
                _verre(b, (x0 + 0.8, ys, zf - 1.2), (x1 - 1.6, ys + 1.6, zf - 1.0), "vitre_claire", 0.4, collide=False,
                       name="GardeCorps")
                _deco(b, (x0 + 0.7, ys + 1.6, zf - 1.3), (x1 - 1.5, ys + 1.8, zf - 0.9), "blanc", name="MainCourante")
                b.box((x0 + 1.4, ys, zf - 0.2), (x1 - 2.2, y0 + 5.6, zf), vr(mix(c("vitre_nuit"), c("vitre_bleue"), 0.4), rng, 0.05),
                      name="PorteFenetre")
                _deco(b, (x0 + 1.2, y0 + 5.6, zf - 0.3), (x1 - 2.0, y0 + 5.9, zf), "blanc", name="Linteau")
                xm = (x0 + 1.4 + x1 - 2.2) / 2
                _deco(b, (xm - 0.15, ys, zf - 0.35), (xm + 0.15, y0 + 5.6, zf), "blanc", name="Meneau")
        if v == 2 and etages > 1:
            yc0, yc1 = 11.4, H - 1.2
            b.box((x0 + 0.8, yc0, zf - 0.2), (x1 - 0.8, yc1, zf), c("vitre_ciel"), name="MurRideau")
            for k in range(1, etages):
                y0 = 9.0 + 6.5 * (k - 1)
                if k % 2 == 0:
                    _deco(b, (x0 + 0.8, max(yc0, y0 + 0.3), zf - 0.3), (x1 - 0.8, min(yc1, y0 + 6.2), zf - 0.2),
                          "vitre_claire", name="SecondTon")
                if k > 1:
                    _deco(b, (x0 + 0.6, y0 - 0.25, zf - 0.5), (x1 - 0.6, y0 + 0.25, zf), "blanc", name="Nez")
            n = max(2, round((W - 1.6) / 3.5))
            for k in range(1, n):
                x = x0 + 0.8 + (W - 1.6) * k / n
                _deco(b, (x - 0.2, yc0 - 0.2, zf - 0.55), (x + 0.2, yc1 + 0.2, zf), "blanc", name="Montant")
            _deco(b, (x0 + 1.4, yc0 + 1.0, zf - 0.4), (x0 + 2.2, yc1 - 2.0, zf - 0.3), "vitre_reflet", name="Reflet")
    with b.group("Toit"):
        cor = c("blanc") if v != 1 else shade(mur, 0.93)
        b.box((x0, H, zf - 0.2), (x1, H + 1.0, zf + 0.6), cor, studs="top", name="Acrotere")
        b.box((x0, H, zf + 0.6), (x0 + 0.6, H + 0.8, zb), cor, studs="top", name="Acrotere")
        b.box((x1 - 0.6, H, zf + 0.6), (x1, H + 0.8, zb), cor, studs="top", name="Acrotere")
        b.box((x0 + 0.6, H, zb - 0.6), (x1 - 0.6, H + 0.8, zb), cor, studs="top", name="Acrotere")
        xc = x1 - 3.0 if W > 9.5 else x1 - 2.4
        b.box((xc - 1.2, H, zb - 4.6), (xc + 1.2, H + 1.4, zb - 2.6), CLIM, studs="top", name="Climatiseur")
        if v == 0:
            xt = x0 + 2.4
            b.box((xt - 1.3, H, zb - 4.3), (xt + 1.3, H + 0.6, zb - 1.7), c("acier_fonce"), name="SocleReservoir")
            b.cyl((xt, H + 0.6 + 0.9, zb - 3.0), 1.1, 1.8, c("blanc_casse"), studs="top", name="Reservoir")
        elif v == 1:
            b.cyl((x0 + 2.0, H + 1.5, zb - 3.0), 0.12, 3.0, c("acier"), collide=False, name="Antenne")
            _deco(b, (x0 + 1.2, H + 2.4, zb - 3.1), (x0 + 2.8, H + 2.6, zb - 2.9), "acier", name="Antenne")
        elif W >= 10:
            # cadre de panneau publicitaire vide (montants, deux lisses, croisillon)
            xa, xc2 = x0 + 1.5, min(x1 - 4.6, x0 + 9.5)
            for x in (xa, xc2):
                _deco(b, (x - 0.2, H, zf + 2.0), (x + 0.2, H + 2.8, zf + 2.4), "acier_fonce", name="MontantPanneau")
            _deco(b, (xa - 0.4, H + 2.6, zf + 1.9), (xc2 + 0.4, H + 3.0, zf + 2.5), "acier", name="LissePanneau")
            _deco(b, (xa - 0.4, H + 1.2, zf + 1.9), (xc2 + 0.4, H + 1.6, zf + 2.5), "acier", name="LissePanneau")
    return {"emprise": (W, D), "hauteur": H + (3.0 if v == 2 else 2.4 if v == 0 else 3.0 if v == 1 else 1.4)}


def _superette(b, W: float, D: float, enseigne, rng) -> dict:
    """Supérette d'un niveau (variante 3 de `boutique`) : grande boîte blanche, façade toute vitrée, bandeau
    à trois filets violet / orange / lavande (aucune marque), enseigne de toit, niche à distributeurs."""
    H = 9.0
    x0, x1 = -W / 2, W / 2
    zf, zb = -D / 2, D / 2
    rec = 1.5
    blanc = c("blanc")
    texte = ENSEIGNES.get(enseigne, ("blanc", "violet"))[1] if enseigne else "violet"
    xn = x1 - 4.2                         # niche à distributeurs de xn à x1 - 0.6
    with b.group("Volume"):
        b.box((x0, 0, zf + rec), (x1, H, zb), blanc, studs="top", name="Corps")
        b.box((x0, 6.4, zf), (x1, H, zf + rec), blanc, studs="top", name="Bandeau")
        b.box((x0, 0, zf), (x0 + 0.8, 6.4, zf + rec), blanc, name="Pilier")
        b.box((xn - 0.8, 0, zf), (xn, 6.4, zf + rec), blanc, name="Pilier")
        b.box((x1 - 0.6, 0, zf), (x1, 6.4, zf + rec), blanc, name="Pilier")
        # flanc : porte de service et grille d'aération
        b.box((x1, 0, zb - 6.0), (x1 + 0.2, 6.0, zb - 3.6), c("acier"), name="PorteService")
        b.box((x0 - 0.2, 5.0, zb - 6.0), (x0, 6.4, zb - 3.0), c("acier_fonce"), name="Aeration")
    with b.group("Bandeau"):
        for k, f in enumerate(("violet", "orange", "lavande")):
            _deco(b, (x0 + 0.2, 6.6 + 0.4 * k, zf - 0.1), (x1 - 0.2, 7.0 + 0.4 * k, zf), f, name="Filet")
        p = _deco(b, (x0 + 1.5, 7.95, zf - 0.15), (x1 - 1.5, 8.85, zf), "blanc", name="Enseigne")
        if enseigne:
            _label(p, enseigne, face="Front", couleur=col(texte), fond=c("blanc"))
    with b.group("Vitrine"):
        porte = _vitrine(b, x0 + 0.8, xn - 0.8, 6.4, zf, rec, rng, "cadre_blanc", pas=3.2)
        _deco(b, (porte[0], 6.0, zf + 0.2), (porte[1], 6.4, zf + 0.4), "acier_fonce", name="CapteurPorte")
    with b.group("Distributeurs"):
        for k, corps in enumerate(("violet", "blanc")):
            xa = xn + 0.2 + k * 1.7
            b.box((xa, 0, zf + 0.2), (xa + 1.6, 5.6, zf + rec), c(corps), name="Distributeur")
            _neon(b, (xa + 0.2, 3.0, zf + 0.1), (xa + 1.4, 5.2, zf + 0.2), "vitre_claire", name="Vitrine")
            _deco(b, (xa + 0.3, 3.5, zf), (xa + 1.3, 3.9, zf + 0.1), tirer(["rouge", "bleu_vif", "orange"], rng), name="Canettes")
            _deco(b, (xa + 0.4, 0.6, zf + 0.05), (xa + 1.2, 1.4, zf + 0.2), "noir", name="Trappe")
    with b.group("Toit"):
        b.box((x0, H, zf - 0.2), (x1, H + 0.8, zf + 0.6), blanc, studs="top", name="Acrotere")
        b.box((x0, H, zf + 0.6), (x0 + 0.6, H + 0.8, zb), blanc, studs="top", name="Acrotere")
        b.box((x1 - 0.6, H, zf + 0.6), (x1, H + 0.8, zb), blanc, studs="top", name="Acrotere")
        b.box((x0 + 0.6, H, zb - 0.6), (x1 - 0.6, H + 0.8, zb), blanc, studs="top", name="Acrotere")
        # enseigne de toit : caisson blanc à trois filets (sans texte, aucune marque)
        b.box((x0 + 1.0, H + 0.8, zf + 0.2), (x0 + 7.0, H + 2.8, zf + 1.2), blanc, studs="top", name="CaissonToit")
        for k, f in enumerate(("violet", "orange", "lavande")):
            _deco(b, (x0 + 1.4, H + 1.2 + 0.45 * k, zf + 0.1), (x0 + 6.6, H + 1.55 + 0.45 * k, zf + 0.2), f, name="Filet")
        for k in range(3):
            xa = x0 + 2.0 + k * (W - 5.0) / 3
            b.box((xa, H, zb - 6.0), (xa + 2.2, H + 1.3, zb - 3.8), CLIM, studs="top", name="Climatiseur")
            _deco(b, (xa + 0.4, H + 0.3, zb - 6.1), (xa + 1.8, H + 1.0, zb - 6.0), "acier_fonce", name="Grille")
    return {"emprise": (W, D), "hauteur": H + 2.8}


# ---------------------------------------------------------------------------
# 2. Tours de bureaux
# ---------------------------------------------------------------------------

def _hall(b, W: float, D: float, yl: float, rng) -> None:
    """Hall vitré éclairé au pied d'une tour, sous le corps qui déborde de 1,2 : fond lumineux, vitrage
    transparent sur les quatre faces, comptoir et plante, poteaux d'angle blancs, meneaux, porte tambour,
    néon cyan sous le débord avant."""
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    b.box((x0 + 3.0, 0, zf + 3.0), (x1 - 3.0, yl, zb - 3.0), col(INTERIEUR_BOUTIQUE), material="Neon", shadow=False,
          name="HallEclaire")
    _deco(b, (-3.5, 0, zf + 1.8), (3.5, 1.8, zf + 2.8), "marine_clair", name="Accueil")
    b.ball((x1 - 4.5, 1.6, zf + 2.2), 1.1, vr("feuille_claire", rng, 0.05), collide=False, name="Plante")
    _verre(b, (x0 + 1.2, 0, zf + 1.2), (x1 - 1.2, yl, zb - 1.2), "vitre_claire", 0.35, name="VitrageHall")
    for sx in (-1, 1):
        for sz in (-1, 1):
            xa, xc = sorted((sx * W / 2, sx * (W / 2 - 1.2)))
            za, zc = sorted((sz * D / 2, sz * (D / 2 - 1.2)))
            b.box((xa, 0, za), (xc, yl, zc), c("blanc"), name="Poteau")
    n = max(2, round((W - 2.4) / 4.0))
    for k in range(1, n):
        x = x0 + 1.2 + (W - 2.4) * k / n
        if abs(x) < 2.2:
            continue
        _deco(b, (x - 0.15, 0, zf + 1.0), (x + 0.15, yl, zf + 1.2), "cadre_blanc", name="Meneau")
    b.box((-2.4, 0, zf + 0.9), (2.4, 5.0, zf + 1.2), c("marine"), collide=False, name="CadrePorte")
    _verre(b, (-1.9, 0, zf + 0.8), (1.9, 4.5, zf + 0.9), "vitre_ciel", 0.35, collide=False, name="Porte")
    _neon(b, (x0 + 1.2, yl - 0.3, zf + 0.3), (x1 - 1.2, yl, zf + 0.6), "neon_cyan", name="NeonDebord")


def _sommet(b, W: float, D: float, h: float, xa: float, xb: float, za: float, zb: float, rng, simple: bool = False) -> None:
    """Couronne blanche (de h - 4 à h - 1,5, toit stud), néon cyan sur l'avant, édicules de toit jusqu'à h,
    mât d'antenne à feu d'obstacle rouge (≤ h + 6)."""
    yc = h - 4.0
    b.box((xa - 0.5, yc, za - 0.5), (xb + 0.5, h - 1.5, zb + 0.5), c("blanc"), studs="top", name="Couronne")
    if not simple:
        _neon(b, (xa - 0.5, yc + 0.9, za - 0.6), (xb + 0.5, yc + 1.3, za - 0.5), "neon_cyan", name="NeonCouronne")
        _neon(b, (xb + 0.5, yc + 0.9, za - 0.5), (xb + 0.6, yc + 1.3, zb + 0.5), "neon_cyan", name="NeonCouronne")
    w, d = xb - xa, zb - za
    b.box((xa + w * 0.15, h - 1.5, za + d * 0.35), (xa + w * 0.55, h, za + d * 0.8), c("beton_clair"), studs="top",
          name="Edicule")
    if not simple:
        b.box((xa + w * 0.65, h - 1.5, za + d * 0.2), (xa + w * 0.85, h - 0.5, za + d * 0.45), CLIM, studs="top",
              name="Climatiseur")
    xm, zm = xa + w * 0.75, za + d * 0.7
    b.cyl((xm, h - 1.5 + 3.25, zm), 0.25, 6.5, c("acier"), collide=False, name="Mat")
    b.ball((xm, h + 5.3, zm), 0.45, c("rouge"), material="Neon", collide=False, shadow=False, name="FeuObstacle")


def immeuble_bureaux(b, variant: int = 0, largeur: float = 24.0, profondeur: float = 24.0, hauteur: float = 60.0,
                     simple: bool = False) -> dict:
    """Tour de bureaux de la ville, avant vers -Z (la route). Emprise exacte largeur × profondeur ; sommet de
    la couronne et des édicules à `hauteur`, mât d'antenne jusqu'à hauteur + 5,8.

    Socle : hall vitré éclairé en retrait (sauf `simple`). Corps selon la variante, couronne blanche à néon
    cyan, édicules, mât à feu rouge.
    variant 0 béton blanc à bandeaux de fenêtres bleus enveloppants (3 de haut tous les 5,5), ailettes blanches
    et angle vitré ; 1 mur-rideau bleu ciel en deux tons, nez de dalle blancs, montants blancs tous les 4 sur
    l'avant et le flanc droit ; 2 tour à gradin : socle sur toute l'emprise jusqu'à 40 % de la hauteur (terrasse
    plantée), fût plus étroit en retrait, liseré violet.
    simple=True (arrière-plan) : volumes, 4 à 8 bandeaux, couronne et mât, ≤ 40 pièces."""
    rng = b.rng
    v = variant % 3
    W0, D0, h = float(largeur), float(profondeur), float(hauteur)
    W, D = W0 - 1.2, D0 - 1.2      # couronne, angles et nez de dalle débordent de 0,6 au plus : emprise exacte
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    yl = 7.0
    yc = h - 4.0
    n0 = len(b.parts)

    def bandes(xa, xb, za, zb_, y0, y1, pas, haut, tons, nmax=99, ep=0.2):
        """Bandeaux enveloppants (une pièce par bandeau : saillie de `ep` sur les quatre faces)."""
        y, k = y0, 0
        while y + haut <= y1 and k < nmax:
            b.box((xa - ep, y, za - ep), (xb + ep, y + haut, zb_ + ep), vary(tons[k % len(tons)], rng, 0.02), name="Bandeau")
            y += pas
            k += 1
        return k

    if simple:
        with b.group("Tour"):
            b.box((x0 + 0.2, 0, zf + 0.2), (x1 - 0.2, yl - 1.0, zb - 0.2), c("vitre_claire"), name="Socle")
            if v == 2:
                hp = round(0.4 * h)
                b.box((x0, yl - 1.0, zf), (x1, hp, zb), c("facade_blanche"), name="Podium")
                bandes(x0, x1, zf, zb, yl + 1.0, hp - 1.0, 5.5, 3.0, [c("vitre_bleue")], nmax=3)
                b.box((x0 - 0.3, hp, zf - 0.3), (x1 + 0.3, hp + 0.8, zb + 0.3), c("blanc"), studs="top", name="Terrasse")
                xa, xb, za, zb2 = x0 + 4, x1 - 4, zf + 5, zb - 2
                b.box((xa, hp + 0.8, za), (xb, yc, zb2), c("facade_blanche"), name="Fut")
                bandes(xa, xb, za, zb2, hp + 3.0, yc - 1.0, 5.5, 3.0, [c("vitre_bleue"), c("vitre_violette")], nmax=5)
                _deco(b, (xb - 2.5, hp + 0.8, za - 0.4), (xb - 1.0, yc, za), "violet", name="Liseré")
                _sommet(b, W, D, h, xa, xb, za, zb2, rng, simple=True)
            else:
                corps = c("facade_blanche") if v == 0 else c("vitre_ciel")
                b.box((x0, yl - 1.0, zf), (x1, yc, zb), corps, name="Corps")
                if v == 0:
                    bandes(x0, x1, zf, zb, yl + 1.0, yc - 1.0, (yc - yl) / 8.0, 3.0,
                           [c("vitre_bleue"), mix(c("vitre_bleue"), c("vitre_ciel"), 0.3)], nmax=8)
                else:
                    bandes(x0, x1, zf, zb, yl + 3.0, yc - 1.0, (yc - yl) / 7.0, 0.5, [c("blanc")], nmax=7, ep=0.25)
                    _deco(b, (x0 + 2.0, yl + 4.0, zf - 0.1), (x0 + W * 0.35, yc - 6.0, zf), "vitre_claire", name="SecondTon")
                _sommet(b, W, D, h, x0, x1, zf, zb, rng, simple=True)
        return {"emprise": (W0, D0), "hauteur": h, "pieces": len(b.parts) - n0}

    with b.group("Hall"):
        _hall(b, W, D, yl, rng)
    with b.group("Tour"):
        if v == 0:
            b.box((x0, yl, zf), (x1, yc, zb), vr("facade_blanche", rng, 0.02), name="Corps")
            nb = bandes(x0, x1, zf, zb, yl + 2.0, yc - 1.0, 5.5, 3.0,
                        [c("vitre_bleue"), mix(c("vitre_bleue"), c("vitre_ciel"), 0.3)])
            # ailettes blanches verticales (avant et flancs)
            nf = max(2, round(W / 4.0)) - 1
            ca = min(5.5, W * 0.25 - 0.6)          # largeur de l'angle vitré
            for i in range(nf):
                x = x0 + W * (i + 1) / (nf + 1)
                if x - 0.4 > x0 + ca + 0.2:
                    b.box((x - 0.4, yl, zf - 0.5), (x + 0.4, yc, zf), c("blanc"), name="Ailette")
            nz = max(2, round(D / 6.0)) - 1
            for sx in (-1, 1):
                xa, xc = sorted((sx * W / 2, sx * (W / 2 + 0.5)))
                for i in range(nz):
                    z = zf + D * (i + 1) / (nz + 1)
                    if z - 0.4 > zf + ca + 0.2 or sx > 0:
                        b.box((xa, yl, z - 0.4), (xc, yc, z + 0.4), c("blanc"), name="Ailette")
            # angle vitré (avant gauche) à nez de dalle blancs tous les deux étages, reflet
            b.box((x0 - 0.4, yl + 0.5, zf - 0.4), (x0 + ca, yc, zf + ca), c("vitre_ciel"), name="AngleVitre")
            y = yl + 2.0 + 5.5 - 1.0
            while y < yc - 1.0:
                b.box((x0 - 0.55, y, zf - 0.55), (x0 + ca + 0.15, y + 0.5, zf + ca + 0.15), c("blanc"), name="NezDalle")
                y += 11.0
            _deco(b, (x0 + 1.0, yl + 3.0, zf - 0.5), (x0 + 2.0, yc - 6.0, zf - 0.4), "vitre_reflet", name="Reflet")
            for k in range(3):
                yr = yl + 2.0 + 5.5 * (1 + 2 * k)
                if yr + 3 < yc - 1:
                    xr = x0 + W * (0.45 + 0.17 * k)
                    _deco(b, (xr, yr + 0.5, zf - 0.3), (xr + 1.2, yr + 2.5, zf - 0.2), "vitre_reflet", name="Reflet")
            _sommet(b, W, D, h, x0, x1, zf, zb, rng)
        elif v == 1:
            b.box((x0, yl, zf), (x1, yc, zb), c("vitre_ciel"), name="MurRideau")
            # second ton : balayage diagonal de verre clair sur l'avant et le flanc droit
            hh = yc - yl
            for k in range(4):
                xa = x0 + W * (0.08 + 0.21 * k)
                ya = yl + hh * (0.1 + 0.2 * k)
                _deco(b, (xa, ya, zf - 0.1), (xa + W * 0.2, min(yc - 1, ya + hh * 0.32), zf), "vitre_claire", name="SecondTon")
            for k in range(2):
                za = zf + D * (0.15 + 0.4 * k)
                ya = yl + hh * (0.3 + 0.3 * k)
                _deco(b, (x1, ya, za), (x1 + 0.1, min(yc - 1, ya + hh * 0.3), za + D * 0.35), "vitre_claire", name="SecondTon")
            _deco(b, (x0 + 1.4, yl + 2.0, zf - 0.2), (x0 + 2.0, yc - 2.0, zf - 0.1), "vitre_reflet", name="Reflet")
            # nez de dalle blancs enveloppants tous les 5, montants blancs tous les 4 (avant et flanc droit)
            bandes(x0, x1, zf, zb, yl + 4.75, yc - 1.0, 5.0, 0.5, [c("blanc")], ep=0.25)
            nm = max(2, round(W / 4.0))
            for k in range(1, nm):
                x = x0 + W * k / nm
                _deco(b, (x - 0.2, yl, zf - 0.35), (x + 0.2, yc, zf), "blanc", name="Montant")
            nm = max(2, round(D / 4.0))
            for k in range(1, nm):
                z = zf + D * k / nm
                _deco(b, (x1, yl, z - 0.2), (x1 + 0.35, yc, z + 0.2), "blanc", name="Montant")
            for sx in (-1, 1):
                for sz in (-1, 1):
                    xa, xc = sorted((sx * (W / 2 + 0.4), sx * (W / 2 - 0.8)))
                    za, zc = sorted((sz * (D / 2 + 0.4), sz * (D / 2 - 0.8)))
                    b.box((xa, yl, za), (xc, yc, zc), c("blanc"), name="Angle")
            _sommet(b, W, D, h, x0, x1, zf, zb, rng)
        else:
            hp = round(0.4 * h)
            b.box((x0, yl, zf), (x1, hp, zb), vr("facade_blanche", rng, 0.02), name="Podium")
            bandes(x0, x1, zf, zb, yl + 2.0, hp - 1.5, 5.5, 3.0, [c("vitre_bleue")])
            b.box((x0 - 0.3, hp, zf - 0.3), (x1 + 0.3, hp + 1.0, zb + 0.3), c("blanc"), studs="top", name="Terrasse")
            _deco(b, (x0 - 0.3, hp + 0.2, zf - 0.4), (x1 + 0.3, hp + 0.6, zf - 0.3), "violet", name="Liseré")
            _verre(b, (x0 + 0.2, hp + 1.0, zf + 0.2), (x1 - 0.2, hp + 2.4, zf + 0.4), "vitre_claire", 0.4, collide=False,
                   name="GardeCorps")
            for x in (x0 + 3.0, x1 - 3.0):
                b.box((x - 1.6, hp + 1.0, zf + 1.2), (x + 1.6, hp + 2.0, zf + 3.2), c("beton_clair"), studs="top", name="Jardiniere")
                b.ball((x, hp + 3.0, zf + 2.2), 1.5, vr("feuille_claire", rng, 0.06), collide=False, name="Arbuste")
            xa, xb, za, zb2 = x0 + 4.0, x1 - 4.0, zf + 6.0, zb - 2.0
            b.box((xa, hp + 1.0, za), (xb, yc, zb2), vr("facade_blanche", rng, 0.02), name="Fut")
            bandes(xa, xb, za, zb2, hp + 3.0, yc - 1.0, 5.5, 3.0,
                   [c("vitre_bleue"), mix(c("vitre_bleue"), c("vitre_violette"), 0.5)])
            _deco(b, (xb - 3.0, hp + 1.0, za - 0.5), (xb - 1.2, yc, za), "violet", name="Liseré")
            _deco(b, (xa + 1.0, hp + 4.0, za - 0.3), (xa + 1.8, yc - 4.0, za - 0.2), "vitre_reflet", name="Reflet")
            _sommet(b, W, D, h, xa, xb, za, zb2, rng)
    return {"emprise": (W0, D0), "hauteur": h, "pieces": len(b.parts) - n0}


# ---------------------------------------------------------------------------
# 5. Mur d'enceinte latéral et 6. silhouettes lointaines
# ---------------------------------------------------------------------------

def mur_campus(b, variant: int = 0, longueur: float = 31.0, hauteur: float = 12.0) -> dict:
    """Tronçon du mur d'enceinte latéral (le long de X local, épaisseur 3 en z ∈ [-1,5 ; 1,5]), avant -Z = côté
    campus. Grands panneaux gris clair à taches, couvertine stud, pile de brique près de x = -longueur/2 (en
    retrait de 1 pour ne pas doubler aux raccords) et au milieu si longueur > 20.
    variant 0 uni ; 1 filet violet (0,6) sur la face intérieure ; 2 néon blanc sous la couvertine (face intérieure).
    Au plus ceil(4 + longueur / 4) pièces."""
    rng = b.rng
    L, h = float(longueur), float(hauteur)
    x0, x1 = -L / 2, L / 2
    budget = int(math.ceil(4 + L / 4))
    n0 = len(b.parts)
    v = variant % 3
    b.box((x0, h - 1.0, -1.9), (x1, h, 1.9), c("chaperon"), studs="top", name="Couvertine")
    piles = [x0 + 2.0]
    if L > 20:
        piles.append(0.0)
    if len(piles) == 2:
        b.box((x0, 0, -1.5), (0, h - 1.0, 1.5), c("panneau_mur"), name="Panneau")
        b.box((0, 0, -1.5), (x1, h - 1.0, 1.5), c("panneau_mur_clair"), name="Panneau")
    else:
        b.box((x0, 0, -1.5), (x1, h - 1.0, 1.5), tirer(["panneau_mur", "panneau_mur_clair"], rng), name="Panneau")
    for x in piles:
        _pile_brique(b, x, h + 0.6, rng)
    if v == 1:
        _deco(b, (x0, h - 3.0, -1.6), (x1, h - 2.4, -1.5), "violet", name="Filet")
    elif v == 2:
        _neon(b, (x0, h - 1.4, -1.6), (x1, h - 1.0, -1.5), "neon_blanc", name="NeonMur")
    y_max = h - 3.2 if v == 1 else h - 1.6
    reste = budget - (len(b.parts) - n0)
    bords = [x0] + [p for x in piles for p in (x - 1.0, x + 1.0)] + [x1]
    travees = [(bords[i], bords[i + 1]) for i in range(0, len(bords), 2) if bords[i + 1] - bords[i] > 3.0]
    # taches en coulure (face intérieure d'abord), une par travée et par face, dans le budget restant
    places = [(-1, t) for t in range(len(travees))] + [(1, t) for t in range(len(travees))]
    for sz, t in places:
        if reste <= 0:
            break
        u0, u1 = travees[t]
        za, zb = sorted((sz * 1.5, sz * 1.6))
        reste -= _tache(b, u0 + 0.5, u1 - 0.5, h * 0.3, y_max, za, zb, rng, morceaux=min(3, reste))
    return {"emprise": (L, 4.0), "hauteur": h + 1.2, "pieces": len(b.parts) - n0}


def silhouette_lointaine(b, variant: int = 0, largeur: float = 24.0, profondeur: float = 18.0, hauteur: float = 60.0) -> dict:
    """Immeuble lointain de la métropole (≤ 8 pièces), avant vers -Z (la route) : volume principal, bandes de
    vitrage verticales plus sombres en saillie de 0,2, couronne stud. Tons moyens et brumeux (mélangés de 30 %
    de violet foncé) pour rester à l'arrière-plan.
    v0 blanc brumeux à deux bandes vitrées verticales ; v1 verre bleu ciel à nez de dalle ; v2 lavande à deux
    bandes verticales ; v3 à gradin (deux volumes)."""
    rng = b.rng
    v = variant % 4
    W, D, h = float(largeur), float(profondeur), float(hauteur)
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    n0 = len(b.parts)
    yc = h - 3.0
    fond = c("vitre_violette_fonce")

    def br(nom, t=0.3):
        return mix(c(nom), fond, t)

    if v == 3:
        hb = round(0.55 * h)
        b.box((x0, 0, zf), (x1, hb, zb), br("facade_blanche"), studs="top", name="Base")
        xa, xb, za, zb2 = x0 + 3.0, x1 - 3.0, zf + 3.0, zb - 2.0
        b.box((xa, hb, za), (xb, yc, zb2), br("beton_clair"), name="Haut")
        for t in (0.35, 0.7):
            y = hb * t
            b.box((x0 + 1.5, y, zf - 0.2), (x1 - 1.5, y + 3.0, zf), br("vitre_bleue", 0.4), name="Bandeau")
        for t in (0.3, 0.65):
            y = hb + (yc - hb) * t
            b.box((xa + 1.5, y, za - 0.2), (xb - 1.5, y + 3.0, za), br("vitre_ciel", 0.4), name="Bandeau")
        b.box((xa - 0.4, yc, za - 0.4), (xb + 0.4, h, zb2 + 0.4), br("blanc", 0.25), studs="top", name="Couronne")
    else:
        corps = (br("facade_blanche"), br("vitre_ciel"), br("lavande_pale"))[v]
        b.box((x0, 0, zf), (x1, yc, zb), vary(corps, rng, 0.02), name="Corps")
        if v in (0, 2):
            vit = br("vitre_bleue", 0.45) if v == 0 else br("vitre_violette", 0.45)
            for xa_, xb_ in ((x0 + 2.0, -1.0), (1.0, x1 - 2.0)):
                b.box((xa_, 4.0, zf - 0.2), (xb_, yc - 3.0, zf), vit, name="Vitrage")
        else:
            for t in (0.25, 0.5, 0.75):
                y = yc * t
                b.box((x0 - 0.2, y - 0.4, zf - 0.2), (x1 + 0.2, y + 0.4, zb + 0.2), br("blanc", 0.25), name="Bandeau")
            b.box((x0 + 3.0, 3.0, zf - 0.1), (x0 + 3.0 + W * 0.25, yc - 3.0, zf), br("vitre_claire"), name="Reflet")
        b.box((x0 - 0.4, yc, zf - 0.4), (x1 + 0.4, h, zb + 0.4), br("blanc", 0.25) if v != 2 else br("lavande"),
              studs="top", name="Couronne")
    return {"emprise": (W, D), "hauteur": h, "pieces": len(b.parts) - n0}


# ---------------------------------------------------------------------------
# Planche d'aperçu (non posée par zone.py)
# ---------------------------------------------------------------------------

BOUTIQUES_PLANCHE = {
    # comme zone.BOUTIQUES : (îlot, largeur, profondeur, etages, variante, enseigne)
    0: [("A", 14, 16, 3, 0, "CAFÉ"), ("A", 10, 14, 2, 1, "FLEURS"), ("B", 14, 16, 4, 2, "LIVRES"),
        ("B", 16, 18, 1, 3, "MARCHÉ"), ("B", 9, 14, 3, 1, "RAMEN")],
    1: [("A", 12, 16, 3, 2, "BOULANGERIE"), ("A", 12, 16, 2, 0, "SPORT"), ("B", 16, 18, 1, 3, "PHARMACIE"),
        ("B", 14, 14, 4, 0, "CAFÉ"), ("B", 9, 14, 2, 1, None)],
}


def planche(b, variant: int = 0, partie: int = 0) -> dict:
    """Aperçu : partie 0 boutiques du côté gauche, 1 côté droit (alignées le long de X, avant vers -Z, îlots
    séparés comme dans la rue), 2 les quatre tours de bureaux de gauche, 3 silhouettes et tronçons de mur."""
    if partie in (0, 1):
        x = 0.0
        ilot = "A"
        for (il, larg, prof, et, v, ens) in BOUTIQUES_PLANCHE[partie]:
            if il != ilot:
                x += 29.0          # rue latérale
                ilot = il
            with b.at((x + larg / 2, 0, prof / 2)):
                boutique(b, variant=v, largeur=larg, profondeur=prof, etages=et, enseigne=ens)
            x += larg + 1.0
        return {"emprise": (x, 18), "hauteur": 30}
    if partie == 2:
        for i, (x, larg, prof, h, v, simple) in enumerate(((0, 24, 24, 62, 0, False), (36, 36, 26, 84, 1, False),
                                                            (80, 24, 22, 50, 2, True), (116, 30, 24, 72, 0, True),
                                                            (156, 24, 24, 74, 1, False), (196, 36, 26, 58, 2, False))):
            with b.at((x, 0, prof / 2)):
                immeuble_bureaux(b, variant=v, largeur=larg, profondeur=prof, hauteur=h, simple=simple)
        return {"emprise": (220, 26), "hauteur": 90}
    x = 0.0
    for k, (larg, h) in enumerate(((20, 44), (24, 68), (28, 96), (24, 110), (20, 56), (28, 82))):
        with b.at((x + larg / 2, 0, 30)):
            silhouette_lointaine(b, variant=k % 4, largeur=larg, profondeur=18, hauteur=h)
        x += larg + 10
    x = 0.0
    for k in range(4):
        L = 31.0 if k < 3 else 6.5
        with b.at((x + L / 2, 0, 0)):
            mur_campus(b, variant=k % 3, longueur=L, hauteur=12)
        x += L
    return {"emprise": (x, 40), "hauteur": 110}
