"""Maisons de la ville entre les murailles (zone 7), style « stud » : maisons à colombages, maisons bourgeoises,
maisons à arcades de la grand-place, maisons du fond et fermes de la prairie.

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :
- maison_colombages(largeur=18, profondeur=18, etages=3, enseigne=None) ≤ 100 pièces (enseigne comprise) ;
    v0 pignon sur rue, enduit crème, bois brun sombre, croix de Saint-André, volets verts, tuile ;
    v1 gouttereau sur rue à deux lucarnes, enduit ocre, bois sang-de-bœuf, tuile claire ;
    v2 pignon sur rue à deux forts encorbellements, enduit blanc, bois brun, volets bleus, poulie de grenier ;
    v3 rez de pierre à grande arcade de boutique, étages d'enduit saumon, lucarne-pignon à colombages ;
    v4 haute maison à pignon, enduit jaune, oriel d'angle (côté +x) coiffé d'ardoise, tuile rouge.
    Rez de 7, étages de 6 ; les étages sans encorbellement entre eux forment un « bloc » (un hourdis, des poteaux
    d'un seul tenant, une sablière par étage). Porte et enseigne côté +x (v0, v2) ou -x (v1, v3, v4).
- maison_bourgeoise(largeur=22, profondeur=18, etages=4, enseigne=None) ≤ 110 pièces ;
    v0 pignon à redents en pierre de taille ; v1 gouttereau enduit, trois lucarnes, balcon à garde-corps de fer ;
    v2 pignon à volutes (gradins et coins), enduit ocre ; v3 pierre, oriel central, toit d'ardoise.
- maison_arcades(largeur=26, profondeur=18, etages=3) ≤ 110 pièces : rez à arcades (galerie couverte de 4) ;
    v0 étages à colombages ; v1 pierre et pignon à redents ; v2 enduit, gouttereau et lucarnes ; v3 façade peinte et oriel.
- maison_fond(largeur=14, profondeur=12, etages=2) ≤ 30 pièces : maison simple des secondes rangées (v0-v3).
- ferme() ≤ 75 pièces, emprise 24 × 14, hauteur ≤ 16 : v0 chaume et pierre, v1 colombages et pigeonnier,
    v2 grange de pierre à tuiles rouges.

Repère (voir CONVENTIONS.md) : origine au centre de l'emprise au sol, y = 0 au sol, l'AVANT (la façade sur la rue)
regarde -Z ; `largeur` le long de X, `profondeur` le long de Z. Vu de la rue (depuis -z), +x est à GAUCHE.
Le mur avant du rez est exactement en z = -profondeur/2 ; encorbellements, oriels, rives de toit et lanternes
dépassent d'au plus 4 vers -Z ; l'enseigne en drapeau (mobilier.enseigne) dépasse d'au plus 8,6 (elle reste en
|x| ≥ 46 une fois posée en façade, en |x| = 55). Débords latéraux ≤ 0,5 (les voisins sont à 2 ou 3 studs).

Règles : une seule pièce par aplat (le hourdis d'un étage est UN bloc, les bois sont posés dessus), aucun
recouvrement coplanaire (reliefs en façade : cadre 0,12, écharpe 0,16, vitre 0,2, poteau 0,22, volet 0,26,
sablière 0,3), rien ne flotte, studs sur les pans de toit et les rebords horizontaux, jamais sur les murs.
Chaque fonction se construit au niveau de détail le plus riche qui tient dans son budget (on recommence avec
moins de détails si besoin, en gardant les mêmes couleurs ; les volets, géraniums et auvents partent en dernier).
Couleurs : chaque variante a deux ou trois palettes (enduit, bois, volets, toit, fleurs) ; `_choix` en tire une
d'après les paramètres et la position de la pose dans la zone (`b.to_world`), avec le sel `SEL` réglé pour que
deux maisons voisines ou face à face n'aient jamais le même enduit. Une maison sur deux a une fenêtre éclairée
(vitrage Neon) dans le comble.
Uniquement des éléments génériques de ville médiévale d'Europe centrale : aucun nom, aucun emblème, aucun
personnage ; les seuls textes sont ceux des enseignes permises (mobilier.TEXTES_ENSEIGNES).
"""

from __future__ import annotations

import math

from kit import hexrgb, rot_x, rot_z, shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Couleurs et outils
# ---------------------------------------------------------------------------

INTERIEUR = "#2E241D"      # fond sombre d'une boutique, d'une galerie, d'une porte de grange ouverte

# reliefs en façade (sortie vers -z depuis le plan du mur)
R_CADRE, R_ECHARPE, R_VITRE, R_POTEAU, R_VOLET, R_SABLIERE = 0.12, 0.16, 0.2, 0.22, 0.26, 0.3


def col(x):
    """Nom de palette, '#hex' ou tuple → tuple RGB."""
    if isinstance(x, tuple):
        return x
    if isinstance(x, str) and x.startswith("#"):
        return hexrgb(x)
    return c(x)


def vr(x, rng, amount=0.04):
    """`vary` qui accepte aussi '#hex' et les tuples."""
    return vary(col(x), rng, amount)


def _cle(*vals) -> int:
    """Petit hachage déterministe (FNV-1a) des paramètres d'une pose : choix de la palette secondaire, pour qu'une
    même variante posée plusieurs fois ne se répète pas à l'identique."""
    h = 2166136261
    for v in vals:
        for ch in str(v) + "|":
            h = ((h ^ ord(ch)) * 16777619) % 2 ** 32
    return h >> 5


SEL = 112    # sel du hachage des palettes (réglé pour que deux voisines n'aient jamais le même enduit)


def _choix(b, n, *vals) -> int:
    """Indice de palette secondaire (0..n-1) tiré des paramètres ET de la position de la pose dans la zone
    (`b.to_world`) : deux poses identiques à deux endroits différents n'ont pas forcément les mêmes couleurs."""
    o = b.to_world((0.0, 0.0, 0.0))
    return _cle(SEL, *vals, int(round(float(o[0]))), int(round(float(o[2])))) % n


def _budget(b, n0, budget, construire, niveaux=5):
    """Construit au niveau de détail le plus riche (0) qui tient dans `budget` pièces ; mêmes tirages de
    couleurs à chaque essai. `construire(niveau)` renvoie le dict d'informations de l'asset."""
    etat = b.rng.bit_generator.state
    info = None
    for niveau in range(niveaux):
        b.rng.bit_generator.state = etat
        info = construire(niveau)
        if len(b.parts) - n0 <= budget or niveau == niveaux - 1:
            break
        del b.parts[n0:]
    return info


# ---------------------------------------------------------------------------
# Dalles inclinées (pans de toit)
# ---------------------------------------------------------------------------

def _pan_z(b, za, ya, zb, yb, x0, x1, ep, couleur, *, ext_a=0.0, ext_b=0.0, studs="top", name="Pan", **kw):
    """Dalle inclinée dans le plan YZ : sa face supérieure passe par (za, ya) et (zb, yb) (za < zb), épaisseur
    `ep` sous cette ligne, étendue sur x0..x1 ; `ext_a` / `ext_b` l'allongent (le long de la pente) côté a / b."""
    dz, dy = zb - za, yb - ya
    L = math.hypot(dz, dy)
    uz, uy = dz / L, dy / L
    phi = math.atan2(dy, dz)
    ny, nz = math.cos(phi), -math.sin(phi)
    if ny < 0:
        ny, nz = -ny, -nz
    s = (ext_b - ext_a) / 2
    cz = (za + zb) / 2 + uz * s - nz * ep / 2
    cy = (ya + yb) / 2 + uy * s - ny * ep / 2
    return b.part("block", (x1 - x0, ep, L + ext_a + ext_b), ((x0 + x1) / 2, cy, cz), rot_x(-math.degrees(phi)),
                  col(couleur), studs=studs, name=name, **kw)


def _pan_x(b, xa, ya, xb, yb, z0, z1, ep, couleur, *, ext_a=0.0, ext_b=0.0, studs="top", name="Pan", **kw):
    """Dalle inclinée dans le plan XY (xa < xb) : face supérieure par (xa, ya) et (xb, yb), épaisseur `ep`
    sous cette ligne, étendue sur z0..z1 ; `ext_a` / `ext_b` l'allongent côté a / côté b."""
    dx, dy = xb - xa, yb - ya
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    s = (ext_b - ext_a) / 2
    cx = (xa + xb) / 2 + ux * s - nx * ep / 2
    cy = (ya + yb) / 2 + uy * s - ny * ep / 2
    return b.part("block", (L + ext_a + ext_b, ep, z1 - z0), (cx, cy, (z0 + z1) / 2), rot_z(math.degrees(math.atan2(dy, dx))),
                  col(couleur), studs=studs, name=name, **kw)


def _barre(b, xa, ya, xb, yb, z, couleur, ep=0.45, relief=R_ECHARPE, name="Echarpe"):
    """Pièce de bois oblique (écharpe, croix de Saint-André, contre-fiche) dans le plan de façade z, de
    (xa, ya) à (xb, yb) ; ses bouts carrés se perdent dans les poteaux et les sablières, plus saillants."""
    L = math.hypot(xb - xa, yb - ya)
    ang = math.degrees(math.atan2(yb - ya, xb - xa))
    b.part("block", (L, ep, relief + 0.2), ((xa + xb) / 2, (ya + yb) / 2, z - relief + (relief + 0.2) / 2),
           rot_z(ang), col(couleur), collide=False, name=name)


# ---------------------------------------------------------------------------
# Éléments de façade (plan de façade z, extérieur vers -z)
# ---------------------------------------------------------------------------

def _fenetre(b, x, y, w, h, z, *, cadre="fenetre_cadre", verre="fenetre", meneau=True, volets=None, larg_volet=None,
             fleurs=None, bac="bois", m=0.22, name="Fenetre", allumee=False):
    """Fenêtre : cadre clair en saillie, vitrage sombre (deux battants séparés par un meneau si `meneau`),
    volets ouverts de part et d'autre, jardinière de géraniums sous l'appui. (x, y) = milieu du bas du vitrage.
    `allumee` : vitrage chaud lumineux (Neon), une fenêtre par maison au plus."""
    kw_v = {"material": "Neon"} if allumee else {}
    if allumee:
        verre = "fenetre_lumiere"
    b.box((x - w / 2 - m, y - m, z - R_CADRE), (x + w / 2 + m, y + h + m, z + 0.2), col(cadre), collide=False,
          name=name)
    if meneau:
        g = 0.24
        for s in (-1, 1):
            xa, xb = sorted((x + s * g / 2, x + s * w / 2))
            b.box((xa, y, z - R_VITRE), (xb, y + h, z - 0.05), col(verre), collide=False, name="Vitre", **kw_v)
    else:
        b.box((x - w / 2, y, z - R_VITRE), (x + w / 2, y + h, z - 0.05), col(verre), collide=False, name="Vitre", **kw_v)
    if volets:
        lv = larg_volet or w / 2
        for s in (-1, 1):
            xa, xb = sorted((x + s * (w / 2 + m + 0.05), x + s * (w / 2 + m + 0.05 + lv)))
            b.box((xa, y - m, z - R_VOLET), (xb, y + h + m, z + 0.05), col(volets), collide=False, name="Volet")
    if fleurs:
        yb = y - m
        b.box((x - w / 2 - 0.25, yb - 0.85, z - 0.95), (x + w / 2 + 0.25, yb - 0.05, z + 0.1), col(bac),
              collide=False, name="Jardiniere")
        b.box((x - w / 2 - 0.1, yb - 0.05, z - 0.85), (x + w / 2 + 0.1, yb + 0.55, z - 0.3), col(fleurs),
              collide=False, name="Geraniums")


def _porte(b, x, w, h, z, *, bois="porte", encadrement="pierre_maison_claire", arc=True, m=0.45, seuil=True):
    """Porte : encadrement (pierre ou bois) en saillie, vantail sombre, linteau en plein cintre (cylindre) si
    `arc`, seuil de pierre (≤ 0,5 devant le mur). (x, 0) = milieu du bas, h = hauteur sous la clé."""
    b.box((x - w / 2 - m, 0.3 if seuil else 0, z - 0.15), (x + w / 2 + m, h + m, z + 0.2), col(encadrement),
          collide=False, name="Encadrement")
    hs = h - w / 2 if arc else h
    b.box((x - w / 2, 0.3 if seuil else 0, z - 0.27), (x + w / 2, hs, z - 0.05), col(bois), collide=False,
          name="Porte")
    if arc:
        b.cyl((x, hs, z - 0.17), w / 2, 0.24, col(bois), axis="z", collide=False, name="Porte")
    if seuil:
        b.box((x - w / 2 - m - 0.2, 0, z - 0.5), (x + w / 2 + m + 0.2, 0.3, z + 0.1), col("pierre_brune"),
              studs="top", name="Seuil")


def _vitrine(b, x, y, w, h, z, *, cadre="bois", verre="fenetre", meneaux=1, auvent=None, appui=True):
    """Devanture de boutique : cadre de bois, vitrage sombre, meneaux, tablette d'étalage et auvent de toile."""
    b.box((x - w / 2 - 0.35, y - 0.35, z - 0.14), (x + w / 2 + 0.35, y + h + 0.35, z + 0.2), col(cadre), collide=False,
          name="Devanture")
    b.box((x - w / 2, y, z - 0.22), (x + w / 2, y + h, z - 0.05), col(verre), collide=False, name="Vitrine")
    for i in range(1, meneaux + 1):
        xx = x - w / 2 + i * w / (meneaux + 1)
        b.box((xx - 0.14, y - 0.05, z - 0.3), (xx + 0.14, y + h + 0.05, z - 0.1), col(cadre), collide=False,
              name="Meneau")
    if appui:
        b.box((x - w / 2 - 0.5, y - 0.6, z - 0.8), (x + w / 2 + 0.5, y - 0.2, z + 0.1), shade(col(cadre), 0.9),
              studs="top", collide=False, name="Etalage")
    if auvent:
        b.wedge((x - w / 2 - 0.5, y + h + 0.4, z - 1.9), (x + w / 2 + 0.5, y + h + 1.3, z + 0.05), col(auvent),
                down="-z", studs="top", collide=False, material="Fabric", name="Auvent")


def _cheminee(b, x, z, y0, y1, *, brique="brique", cote=2.0):
    """Haute cheminée carrée de brique (y0 noyé dans le comble, y1 = haut du fût) et chapeau plus sombre."""
    br = col(brique)
    b.box((x - cote / 2, y0, z - cote / 2), (x + cote / 2, y1, z + cote / 2), br, name="Cheminee")
    b.box((x - cote / 2 - 0.3, y1, z - cote / 2 - 0.3), (x + cote / 2 + 0.3, y1 + 0.6, z + cote / 2 + 0.3),
          shade(br, 0.72), studs="top", collide=False, name="Chapeau")
    return y1 + 0.6


def _lanterne(b, x, y, z, *, fer="fonte"):
    """Petite lanterne murale (3 pièces) : potence de fer, verre lumineux, chapeau. (x, y, z) = point
    d'attache sur le mur."""
    b.box((x - 0.12, y, z - 1.4), (x + 0.12, y + 0.25, z + 0.1), col(fer), collide=False, name="Potence")
    b.box((x - 0.4, y - 1.5, z - 1.55), (x + 0.4, y - 0.4, z - 0.75), col("lampe"), material="Neon", collide=False,
          shadow=False, name="Lanterne")
    b.box((x - 0.55, y - 0.4, z - 1.7), (x + 0.55, y, z - 0.6), col(fer), collide=False, name="Chapeau")


def _pignon_toit(b, x0, x1, zg, zb, H, pente, toit, mur, *, rng, ep=0.6, rive_av=0.6, rive_ar=0.4, bois=None,
                 deb=0.1):
    """Toit à deux pans dont le PIGNON regarde la rue (faîtage le long de Z) sur des murs x0..x1 / zg..zb de
    hauteur H : triangle de pignon (`mur`, deux coins qui couvrent aussi le pignon arrière), deux pans stud qui
    débordent devant (`rive_av`) et derrière, planches de rive sur le pignon avant, faîtière.
    Renvoie (y_faite (dessus des pans au faîte), y_haut)."""
    xm = (x0 + x1) / 2
    run = xm - x0
    rise = run * pente
    k = ep * math.hypot(1, pente)
    m = vr(mur, rng, 0.02)
    b.wedge((x0, H, zg), (xm, H + rise, zb), m, down="-x", name="Pignon")
    b.wedge((xm, H, zg), (x1, H + rise, zb), m, down="+x", name="Pignon")
    za, zz = zg - rive_av, zb + rive_ar
    t = col(toit)
    _pan_x(b, x0, H + k, xm, H + rise + k, za, zz, ep, vr(t, rng, 0.03), ext_a=deb, ext_b=0.45)
    _pan_x(b, xm, H + rise + k, x1, H + k, za, zz, ep, vr(t, rng, 0.03), ext_a=0.45, ext_b=deb)
    yr = H + rise + k
    if bois is not None:
        # planches de rive : suivent les deux pentes du pignon avant, un peu plus hautes que les pans
        for i, (xa, ya, xb, yb, ea, eb) in enumerate(((x0, H + k + 0.12, xm, yr + 0.12, deb, 0.3),
                                                      (xm, yr + 0.12, x1, H + k + 0.12, 0.3, deb))):
            dz = 0.04 * i
            _pan_x(b, xa, ya, xb, yb, za - 0.22 - dz, za + 0.2 - dz, ep + 0.3, col(bois), ext_a=ea, ext_b=eb,
                   studs="none", collide=False, name="Rive")
    b.box((xm - 0.75, yr - 0.75 * pente - 0.3, za - 0.3), (xm + 0.75, yr + 0.55, zz + 0.15), shade(t, 0.72),
          studs="top", name="Faitage")
    return yr, yr + 0.55


def _gouttereau_toit(b, x0, x1, zf, zb, H, pente, toit, mur, *, rng, ep=0.6, deb_av=1.0, deb_ar=0.7, rive=0.35):
    """Toit à deux pans dont le GOUTTEREAU regarde la rue (faîtage le long de X) sur des murs x0..x1 / zf..zb de
    hauteur H : deux coins de comble (pignons latéraux en `mur`), pans stud qui débordent devant (`deb_av`,
    horizontal) et derrière, faîtière. Renvoie (y_faite, y_haut, f) où f(z) = dessus du pan avant en z."""
    zm = (zf + zb) / 2
    run = zm - zf
    rise = run * pente
    k = ep * math.hypot(1, pente)
    cosa = 1 / math.hypot(1, pente)
    m = vr(mur, rng, 0.02)
    b.wedge((x0, H, zf), (x1, H + rise, zm), m, down="-z", name="Comble")
    b.wedge((x0, H, zm), (x1, H + rise, zb), m, down="+z", name="Comble")
    t = col(toit)
    _pan_z(b, zf, H + k, zm, H + rise + k, x0 - rive, x1 + rive, ep, vr(t, rng, 0.03), ext_a=deb_av / cosa, ext_b=0.45)
    _pan_z(b, zm, H + rise + k, zb, H + k, x0 - rive, x1 + rive, ep, vr(t, rng, 0.03), ext_a=0.45, ext_b=deb_ar / cosa)
    yr = H + rise + k
    b.box((x0 - rive - 0.1, yr - 0.75 * pente - 0.3, zm - 0.75), (x1 + rive + 0.1, yr + 0.55, zm + 0.75), shade(t, 0.72),
          studs="top", name="Faitage")

    def dessus(z):
        return H + k + (z - zf) * pente

    return yr, yr + 0.55, dessus


def _lucarne(b, xd, zf, dessus, pente, toit, mur, *, rng, w=3.4, h=3.2, recul=1.6, forme="pignon", cadre="fenetre_cadre",
             bois=None, volets=None, allumee=False):
    """Lucarne sur un pan avant (gouttereau) : joues et fronton (un bloc), fenêtre, petit toit stud à deux pans
    (`forme="pignon"`) ou rampant (`"rampant"`). `dessus(z)` = dessus du pan principal. Renvoie le haut."""
    zd = zf + recul
    ys = dessus(zd)
    t = col(toit)
    rd = 1.5 if forme == "pignon" else 0.9
    prof = (h + rd + 0.5) / pente + 0.4
    b.box((xd - w / 2, ys - 1.2, zd), (xd + w / 2, ys + h, zd + prof), vr(mur, rng, 0.02), name="Lucarne")
    _fenetre(b, xd, ys + 0.45, w - 1.5, h - 1.25, zd, cadre=cadre, meneau=False, m=0.2, volets=volets,
             larg_volet=0.4 if volets else None, allumee=allumee)
    if bois is not None:
        for s in (-1, 1):
            xa, xb = sorted((xd + s * (w / 2 - 0.5), xd + s * (w / 2 + 0.06)))
            b.box((xa, ys - 0.1, zd - R_POTEAU), (xb, ys + h - 0.05, zd + 0.3), col(bois), collide=False, name="Poteau")
    if forme == "pignon":
        b.wedge((xd - w / 2 - 0.35, ys + h, zd - 0.45), (xd, ys + h + rd, zd + prof), vr(t, rng, 0.03), down="-x",
                studs="top", name="ToitLucarne")
        b.wedge((xd, ys + h, zd - 0.45), (xd + w / 2 + 0.35, ys + h + rd, zd + prof), vr(t, rng, 0.03), down="+x",
                studs="top", name="ToitLucarne")
    else:
        b.wedge((xd - w / 2 - 0.35, ys + h, zd - 0.5), (xd + w / 2 + 0.35, ys + h + rd, zd + prof), vr(t, rng, 0.03),
                down="-z", studs="top", name="ToitLucarne")
    return ys + h + rd


# ---------------------------------------------------------------------------
# Étage à colombages
# ---------------------------------------------------------------------------

def _travees(L, n_fen, coin):
    """Découpe une façade de largeur L : deux travées d'angle de largeur `coin` (écharpes) et `n_fen` travées
    de fenêtres au milieu. Renvoie la liste des x de poteaux (angles compris) et les travées (xa, xb, genre)."""
    x0, x1 = -L / 2 + 0.3, L / 2 - 0.3
    xa, xb = x0 + coin, x1 - coin
    pas = (xb - xa) / max(1, n_fen)
    poteaux = [x0, x1] + [xa + i * pas for i in range(n_fen + 1)]
    travees = [(x0, xa, "coin"), (xb, x1, "coin")] + [(xa + i * pas, xa + (i + 1) * pas, "fen") for i in range(n_fen)]
    return sorted(poteaux), travees


def _bloc_colombage(b, y0, etages, z, zb, L, *, enduit, bois, motifs, n_fen, coin, meneaux, volets, fleurs,
                    fleurs_idx, bac="bois", masque=None, riegel=False):
    """Bloc d'étages à colombages sans encorbellement entre eux : UN hourdis pour tout le bloc, une sablière par
    étage (elle fait le tour de la maison), poteaux d'un seul tenant sur la hauteur du bloc, écharpes des travées
    d'angle selon le motif de chaque étage ("croix", "v", "chevron", "losange"), fenêtres des travées du milieu.
    z = plan de façade du bloc, zb = arrière ; `motifs`, `meneaux`, `volets`, `fleurs_idx` : un élément par étage."""
    x0, x1 = -L / 2, L / 2
    h = 6.0 * etages
    b.box((x0, y0, z), (x1, y0 + h, zb), enduit, name="Hourdis")
    for j in range(etages):
        yj = y0 + 6 * j
        b.box((x0 - 0.25, yj - 0.3, z - R_SABLIERE), (x1 + 0.25, yj + 0.5, zb + 0.2), bois, name="Sabliere")
    poteaux, travees = _travees(L, n_fen, coin)

    def cache(xa_, xb_):
        return masque is not None and masque[0] <= xa_ and xb_ <= masque[1]

    ya, yb = y0 + 0.5, y0 + h - 0.3
    for i, xp in enumerate(poteaux):
        if cache(xp - 0.3, xp + 0.3):
            continue
        if i in (0, len(poteaux) - 1):
            s = -1 if xp < 0 else 1
            xa_, xb_ = sorted((xp - s * 0.3, xp + s * 0.52))
            b.box((xa_, ya, z - R_POTEAU), (xb_, yb, z + 0.6), bois, collide=False, name="Poteau")
        else:
            b.box((xp - 0.27, ya, z - R_POTEAU), (xp + 0.27, yb, z + 0.3), bois, collide=False, name="Poteau")
    fen = [(xa, xb) for (xa, xb, g) in travees if g == "fen" and not cache(xa - 0.3, xb + 0.3)]
    for j in range(etages):
        yj = y0 + 6 * j
        ya, yb = yj + 0.5, yj + 5.7
        if riegel and fen:
            # traverse d'allège (Brustriegel) sous les fenêtres, de poteau à poteau
            b.box((min(f[0] for f in fen), yj + 1.0, z - 0.18), (max(f[1] for f in fen), yj + 1.38, z + 0.2), bois,
                  collide=False, name="Riegel")
        k = 0
        for (xa, xb, genre) in travees:
            if cache(xa - 0.3, xb + 0.3):
                continue
            if genre == "coin":
                dehors = xa if xa < 0 else xb          # côté de l'angle de la maison
                dedans = xb if xa < 0 else xa
                motif = motifs[j]
                if motif == "croix":
                    _barre(b, xa, ya, xb, yb, z, bois)
                    _barre(b, xa, yb, xb, ya, z, bois)
                elif motif == "v":                       # contre-fiches en V
                    _barre(b, dehors, yb, dedans, ya + 0.3, z, bois)
                elif motif == "chevron":                 # écharpes en chevron (Λ)
                    _barre(b, dehors, ya, dedans, yb, z, bois)
                elif motif == "losange":
                    xm, ym = (xa + xb) / 2, (ya + yb) / 2
                    _barre(b, xa + 0.2, ym, xm, yb - 0.1, z, bois)
                    _barre(b, xm, ya + 0.1, xb - 0.2, ym, z, bois)
            else:
                xc = (xa + xb) / 2
                libre = xb - xa - 0.54
                w = min(2.4, libre - 0.6)
                lv, vol = None, volets[j]
                if vol:
                    lv = min(w / 2, (libre - w - 0.44) / 2 - 0.1)
                    if lv < 0.7:
                        vol = None
                _fenetre(b, xc, yj + 1.6, w, 3.2, z, meneau=meneaux[j], volets=vol, larg_volet=lv,
                         fleurs=fleurs if k in fleurs_idx[j] else None, bac=bac)
                k += 1
    return poteaux


def _consoles(b, xs, y, z_av, z_ar, bois, *, h=1.0, w=0.55):
    """Rangée de consoles (abouts de solives sculptés) sous un encorbellement : coins retournés collés au mur
    du dessous (z_ar) et à la sablière (dessous en y)."""
    for x in xs:
        b.wedge_under((x - w / 2, y - h, z_av), (x + w / 2, y, z_ar), bois, down="-z", collide=False, name="Console")


def _corniche(b, x0, x1, y, z_av, z_ar, bois, h=0.9):
    """Gorge continue (un coin retourné) sous un encorbellement."""
    b.wedge_under((x0, y - h, z_av), (x1, y, z_ar), bois, down="-z", collide=False, name="Gorge")


# ---------------------------------------------------------------------------
# 1) Maison à colombages
# ---------------------------------------------------------------------------

# Style de base par variante et palette secondaire (pour qu'une même variante ne se répète pas à l'identique)
_STYLES_COLOMBAGES = (
    dict(toit_forme="pignon", rez="pierre", motif="croix", encorb=(1.0, 0.0, 0.9, 0.0), enc_pignon=0.5,
         pal=(("enduit_creme", "colombage", "volet_vert", "tuile", "fleur_rouge"),
              ("enduit_jaune", "colombage_brun", "volet_rouge", "tuile_rouge", "fleur_rose"),
              ("enduit_blanc", "colombage", "volet_vert", "tuile_fonce", "fleur_rouge"))),
    dict(toit_forme="gouttiere", rez="enduit", motif="v", encorb=(0.9, 0.9, 0.0, 0.0), lucarnes=2,
         pal=(("enduit_ocre", "colombage_rouge", "volet_brun", "tuile_claire", "fleur_rouge"),
              ("enduit_creme", "colombage_rouge", "volet_vert", "tuile", "fleur_rose"),
              ("enduit_jaune", "colombage_rouge", "volet_bleu", "tuile_claire", "fleur_rouge"))),
    dict(toit_forme="pignon", rez="pierre", motif="losange", encorb=(1.3, 1.3, 0.0, 0.0), enc_pignon=0.0, poulie=True,
         pal=(("enduit_blanc", "colombage_brun", "volet_bleu", "tuile_fonce", "fleur_rouge"),
              ("enduit_gris", "colombage", "volet_bleu", "tuile_brune", "fleur_rose"),
              ("enduit_creme", "colombage_brun", "volet_rouge", "tuile_fonce", "fleur_rouge"))),
    dict(toit_forme="gouttiere", rez="arcade", motif=None, encorb=(0.0, 0.0, 0.0, 0.0), zwerch=True,
         pal=(("enduit_saumon", "colombage", "volet_vert", "tuile_brune", "fleur_rouge"),
              ("enduit_bleu", "colombage_brun", "volet_brun", "tuile_brune", "fleur_rose"),
              ("enduit_saumon", "colombage_rouge", "volet_bleu", "tuile_fonce", "fleur_rouge"))),
    dict(toit_forme="pignon", rez="enduit", motif="chevron", encorb=(0.9, 0.0, 0.9, 0.0), enc_pignon=0.0, oriel=True,
         pal=(("enduit_jaune", "colombage", "volet_rouge", "tuile_rouge", "fleur_rouge"),
              ("enduit_ocre", "colombage_brun", "volet_vert", "tuile", "fleur_rouge"),
              ("enduit_creme", "colombage_rouge", "volet_vert", "tuile_rouge", "fleur_rose"))),
)


def maison_colombages(b, variant=0, largeur=18, profondeur=18, etages=3, enseigne=None):
    """Maison à colombages de la grand-rue : rez de 7 (pierre ou enduit) avec porte, devanture et enseigne en
    drapeau ; `etages` étages de 6 en encorbellement (hourdis d'enduit, sablières, poteaux, écharpes, fenêtres à
    meneau, volets, géraniums) ; toit de tuiles à forte pente (pignon sur rue ou gouttereau à lucarnes) ;
    haute cheminée de brique. ≤ 100 pièces, enseigne comprise."""
    n0 = len(b.parts)
    v = variant % len(_STYLES_COLOMBAGES)
    S = _STYLES_COLOMBAGES[v]
    pal = S["pal"][_choix(b, len(S["pal"]), "c", variant, largeur, etages, enseigne or "")]
    with b.group("MaisonColombages"):
        return _budget(b, n0, 100, lambda niv: _colombages(b, v, S, pal, largeur, profondeur, etages, enseigne, niv),
                       niveaux=7)


def _details(niv):
    """Niveau de détail → réglages (0 = complet). Les couleurs (volets, géraniums, auvents) partent en dernier ;
    on retire d'abord la troisième fenêtre des façades larges, les meneaux, les consoles et les lanternes."""
    niv = min(niv, 6)
    f2 = {1: (0,), 2: (1,), 3: (0,)}
    return dict(
        fen_large=niv < 1,                                       # 3 fenêtres par étage sur les façades ≥ 20
        motif=("tous", "tous", "tous", "bords", "premier", "aucun", "aucun")[niv],
        meneau_max=(99, 99, 2, 1, 1, 1, 0)[niv],
        volets=({1, 2}, {1, 2}, {1, 2}, {1, 2}, {1, 2}, {1}, set())[niv],
        fleurs=(f2, f2, f2, f2, {1: (0,), 2: (1,)}, {1: (0,)}, {1: (0,)})[niv],
        consoles=niv < 2, auvent=True, lanterne=niv < 2, echarpes_pignon=niv < 3, oculus=niv < 4, riegel=niv < 3,
        lucarnes_bois=niv < 2,
    )


_SIMPLE = {"croix": "v", "losange": "chevron", "v": "v", "chevron": "chevron", None: None}


def _arcade_boutique(b, xa, wa, z, *, pierre, y0=0.9, yt=6.3):
    """Grande baie de boutique à arc surbaissé : chambranle de pierre claire, vitrage sombre, écoinçons en coins
    (arc à pans), meneaux et tablette d'étalage."""
    b.box((xa - wa / 2 - 0.6, y0, z - 0.16), (xa + wa / 2 + 0.6, yt + 0.6, z + 0.2), pierre, collide=False,
          name="Chambranle")
    b.box((xa - wa / 2, y0 + 0.4, z - 0.26), (xa + wa / 2, yt, z - 0.05), col("fenetre"), collide=False, name="Vitrine")
    c_ = min(2.2, wa / 3)
    b.wedge_under((xa - wa / 2, yt - c_ * 0.75, z - 0.36), (xa - wa / 2 + c_, yt, z - 0.1), pierre, down="+x",
                  collide=False, name="Ecoincon")
    b.wedge_under((xa + wa / 2 - c_, yt - c_ * 0.75, z - 0.36), (xa + wa / 2, yt, z - 0.1), pierre, down="-x",
                  collide=False, name="Ecoincon")
    for xx in (xa - wa / 6, xa + wa / 6):
        b.box((xx - 0.15, y0 + 0.4, z - 0.4), (xx + 0.15, yt, z - 0.2), col("bois"), collide=False, name="Meneau")
    b.box((xa - wa / 2 - 0.3, y0, z - 0.75), (xa + wa / 2 + 0.3, y0 + 0.4, z + 0.1), col("bois"), studs="top",
          collide=False, name="Etalage")


def _colombages(b, v, S, pal, L, P, n, enseigne, niv):
    rng = b.rng
    D = _details(niv)
    lumiere = _choix(b, 2, "l", v, L, n) == 0           # une maison sur deux a une fenêtre éclairée
    n = max(1, int(n))
    enduit_n, bois_n, volet_n, toit_n, fleur_n = pal
    enduit = vr(enduit_n, rng, 0.03)
    bois = vr(bois_n, rng, 0.05)
    x0, x1 = -L / 2, L / 2
    zf0 = -P / 2
    zb = P / 2 - 0.25
    # encorbellements : total ≤ 3 (avec la rive du toit, rien ne dépasse de plus de 4 devant le rez)
    encs = (list(S["encorb"]) + [0.0] * 8)[:n]
    zs = [zf0]
    for j in encs:
        zs.append(zs[-1] - j)
    z_haut = zs[-1]
    H = 7 + 6 * n
    n_fen = 3 if (L >= 20 and D["fen_large"] and not S.get("oriel")) else 2
    cible = 5.2 if n_fen == 2 else 4.4          # largeur visée d'une travée de fenêtre (volets compris)
    coin = max(2.6, min(4.0, (L - 0.6 - n_fen * cible) / 2))
    masque = None
    if S.get("oriel"):
        coin = 3.8
        masque = (L / 2 - 0.3 - coin - 0.35, L / 2 + 1.0)   # travée d'angle cachée par l'oriel
    sp = (1, -1, 1, -1, -1)[v]                   # côté de la porte et de l'enseigne (l'oriel est en +x)

    # --- rez-de-chaussée --------------------------------------------------
    with b.group("Rez"):
        if S["rez"] in ("pierre", "arcade"):
            rez_col = vr("pierre_maison" if v != 3 else "gres", rng, 0.03)
        else:
            rez_col = vr("enduit_blanc" if enduit_n != "enduit_blanc" else "enduit_creme", rng, 0.02)
        b.box((x0, 0, zf0), (x1, 7, zb), rez_col, name="Rez")
        b.box((x0 - 0.2, 0, zf0 - 0.2), (x1 + 0.2, 0.9, zb + 0.15), vr("soubassement", rng, 0.03), name="Soubassement")
        xp = sp * (L / 2 - 3.2)
        _porte(b, xp, 2.4, 5.4, zf0, arc=S["rez"] != "enduit" or v == 4,
               encadrement="pierre_maison_claire" if S["rez"] != "enduit" else bois_n)
        if S["rez"] == "arcade":
            wa = min(L - 9.0, 8.5)
            _arcade_boutique(b, -sp * (L / 2 - 1.6 - wa / 2 - 0.6), wa, zf0, pierre=vr("pierre_maison_claire", rng, 0.02))
        else:
            wv = min(L - 10.5, 7.0)
            aw = ("toile_rouge", "toile_verte", "toile_bleue", "toile_jaune", "toile_rouge")[v] if D["auvent"] else None
            _vitrine(b, -sp * 1.4, 1.9, wv, 3.3, zf0, cadre=bois_n if S["rez"] == "enduit" else "bois", auvent=aw)
        if S["rez"] == "enduit" and niv < 2:
            # rez enduit : poteaux d'angle de bois apparents
            for s_ in (-1, 1):
                xa_, xb_ = sorted((s_ * (L / 2 - 0.3), s_ * (L / 2 + 0.2)))
                b.box((xa_, 0.9, zf0 - R_POTEAU), (xb_, 6.7, zf0 + 0.5), bois, collide=False, name="Poteau")
        if D["lanterne"] and not enseigne:
            _lanterne(b, xp - sp * 2.2, 6.2, zf0)

    # --- étages ---------------------------------------------------------------
    motif = S["motif"]

    def motif_etage(k):
        if motif is None:
            return None
        if D["motif"] == "tous" or (D["motif"] == "bords" and k in (1, n)) or (D["motif"] == "premier" and k == 1):
            return motif
        return _SIMPLE[motif]

    blocs = []                                     # (premier étage, dernier étage, plan de façade)
    for k in range(1, n + 1):
        if blocs and abs(blocs[-1][2] - zs[k]) < 1e-6:
            blocs[-1][1] = k
        else:
            blocs.append([k, k, zs[k]])
    poteaux_1 = None
    for (ka, kb, z) in blocs:
        y0 = 7 + 6 * (ka - 1)
        ks = list(range(ka, kb + 1))
        with b.group(f"Etages{ka}" if ka == kb else f"Etages{ka}-{kb}"):
            if motif is None:
                # étages d'enduit sans bois apparent (v3) : un bloc, bandeaux de pierre, fenêtres à volets
                b.box((x0, y0, z), (x1, y0 + 6 * len(ks), zb), enduit, name="Enduit")
                nf = 3 if L >= 17 else 2
                pas = (L - 3) / nf
                for k in ks:
                    yk = 7 + 6 * (k - 1)
                    b.box((x0 - 0.2, yk - 0.2, z - 0.25), (x1 + 0.2, yk + 0.35, zb + 0.15),
                          vr("pierre_maison_claire", rng, 0.02), name="Bandeau")
                    for i in range(nf):
                        xc = x0 + 1.5 + pas * (i + 0.5)
                        _fenetre(b, xc, yk + 1.6, 2.0, 3.0, z, meneau=k <= D["meneau_max"],
                                 volets=volet_n if (k in D["volets"] and pas >= 4.6) else None,
                                 larg_volet=min(1.0, (pas - 2.44) / 2 - 0.25),
                                 fleurs=fleur_n if (i % 2 == 0 and i in D["fleurs"].get(k, ())) or
                                 (k == 1 and i % 2 == 0 and niv < 4) else None)
                continue
            pt = _bloc_colombage(b, y0, len(ks), z, zb, L, enduit=enduit, bois=bois,
                                 motifs=[motif_etage(k) for k in ks], n_fen=n_fen, coin=coin,
                                 meneaux=[k <= D["meneau_max"] for k in ks],
                                 volets=[volet_n if k in D["volets"] else None for k in ks],
                                 fleurs=fleur_n, fleurs_idx=[D["fleurs"].get(k, ()) for k in ks], masque=masque,
                                 riegel=D["riegel"])
            if ka == 1:
                poteaux_1 = pt
            # encorbellement : consoles sous le premier, gorge continue sous les suivants
            j = zs[ka - 1] - zs[ka]
            if j > 0.05:
                if ka == 1 and D["consoles"]:
                    _consoles(b, [x for x in pt if not (masque and masque[0] <= x <= masque[1])], y0 - 0.3, z - 0.1,
                              zs[ka - 1], bois)
                else:
                    _corniche(b, x0, x1, y0 - 0.3, z - 0.1, zs[ka - 1], bois)

    # --- toit -------------------------------------------------------------------
    t_n = toit_n
    with b.group("Toit"):
        if S["toit_forme"] == "pignon":
            jg = S.get("enc_pignon", 0.0)
            zg = z_haut - jg
            b.box((x0 - 0.25, H - 0.3, zg - R_SABLIERE), (x1 + 0.25, H + 0.5, zb + 0.2), bois, name="Sabliere")
            pente = 1.1
            rise = pente * L / 2
            rive = min(0.6, 3.75 - (zf0 - zg))
            yr, ytop = _pignon_toit(b, x0, x1, zg, zb, H, pente, t_n, enduit, rng=rng, bois=bois, rive_av=rive)
            # bois du pignon : entrait, poinçon, fenêtres du comble, écharpes
            yc = H + 0.5 + rise * 0.42
            demi = (L / 2) * (1 - (yc - H) / rise)
            b.box((-demi, yc - 0.25, zg - R_POTEAU), (demi, yc + 0.35, zg + 0.3), bois, collide=False, name="Entrait")
            # poinçon jusqu'à l'entrait seulement (la lucarne du haut reste dégagée), sauf sous la poulie
            y_poincon = (yc - 0.25) if (S.get("poulie") or D["oculus"]) else (yr - 0.6)
            b.box((-0.27, H + 0.5, zg - R_POTEAU), (0.27, y_poincon, zg + 0.3), bois, collide=False, name="Poincon")
            xw = L / 5.2
            hw = min(2.6, yc - 0.25 - (H + 0.5) - 1.0)
            for s_ in (-1, 1):
                if S.get("oriel") and s_ > 0:
                    continue                      # côté de l'oriel : sa flèche d'ardoise masque ce coin du pignon
                _fenetre(b, s_ * xw, H + 1.0, 1.7, hw, zg, meneau=False, m=0.2, allumee=(s_ < 0 and lumiere))
                if D["echarpes_pignon"]:
                    # contre-fiches en V renversé entre le poinçon et les fenêtres du comble
                    _barre(b, s_ * 0.27, yc - 0.25, s_ * max(1.0, xw - 1.6), H + 0.5, zg, bois)
            if S.get("poulie"):
                # porte de grenier, poutre de levage et poulie (la poutre dépasse la rive de 0,8)
                yd = yc + 0.4
                b.box((-0.9, yd, zg - 0.18), (0.9, yd + 2.2, zg + 0.1), col("bois_gris"), collide=False, name="Grenier")
                zp = zg - rive - 0.7
                b.box((-0.3, yd + 2.5, zp), (0.3, yd + 3.1, zg + 0.3), bois, collide=False, name="Poutre")
                b.cyl((0, yd + 2.15, zp + 0.4), 0.42, 0.25, col("fer"), axis="x", collide=False, name="Poulie")
                b.box((-0.05, yd - 1.2, zp + 0.05), (0.05, yd + 1.8, zp + 0.15), col("corde"), collide=False,
                      shadow=False, name="Corde")
            elif D["oculus"]:
                _fenetre(b, 0.0, yc + 1.0, 1.2, min(1.8, (yr - yc) * 0.32), zg, meneau=False, m=0.2)
            xc = -(L / 4) * (1 if v % 2 else -1)
            ych = H + (L / 2 - abs(xc)) * pente
            ytop = max(ytop, _cheminee(b, xc, zb - 4.0, H, max(ych + 5.0, yr + 3.5)))
        else:
            b.box((x0 - 0.25, H - 0.3, z_haut - R_SABLIERE), (x1 + 0.25, H + 0.5, zb + 0.2), bois, name="Sabliere")
            pente = 1.0
            sina = pente / math.hypot(1, pente)
            deb = max(0.4, min(1.0, 3.9 - (zf0 - z_haut) - 0.6 * sina))
            yr, ytop, dessus = _gouttereau_toit(b, x0, x1, z_haut, zb, H, pente, t_n, enduit, rng=rng, deb_av=deb)
            if S.get("zwerch"):
                # lucarne-pignon (Zwerchhaus) à colombages au milieu de la façade, lucarnes rampantes de part et d'autre
                ytop = max(ytop, _zwerchhaus(b, 0.0, z_haut, H, pente, min(8.0, L - 6), t_n, enduit, bois, rng, niv))
                if niv < 3 and L >= 17:
                    for s_ in (-1, 1):
                        _lucarne(b, s_ * (L / 2 - 2.4), z_haut, dessus, pente, t_n, enduit, rng=rng, w=2.6, h=2.6,
                                 forme="rampant")
            else:
                nl = S.get("lucarnes", 2)
                for i in range(nl):
                    xd = -L / 2 + L * (i + 0.5) / nl
                    _lucarne(b, xd, z_haut, dessus, pente, t_n, enduit, rng=rng,
                             bois=bois if D["lucarnes_bois"] else None, allumee=(i == 0 and lumiere))
            zm = (z_haut + zb) / 2
            xc = (L / 2 - 2.5) * (1 if v % 2 else -1)
            ytop = max(ytop, _cheminee(b, xc, zm + 1.8, H, yr + 4.5))

    # --- oriel d'angle (v4) -----------------------------------------------------
    if S.get("oriel"):
        with b.group("Oriel"):
            ytop = max(ytop, _oriel(b, L, zs, n, H, enduit, bois, rng, niv))

    # --- enseigne en drapeau ------------------------------------------------------
    if enseigne:
        from assets import mobilier
        long_ = min(max(1.2 + 0.9 * len(enseigne), 3.0), 7.0)
        sortie = 0.8 + long_ + 0.4
        z1 = zs[1]
        zm_ = max(z1 - (0.1 if poteaux_1 else 0.0), zf0 - (8.6 - sortie))
        if poteaux_1 and abs((zm_ - 0.2) - (z1 + 0.3)) < 0.03:
            zm_ += 0.05                           # le dos de la potence ne doit pas tomber dans le plan du poteau
        # du côté de la porte, sur le premier poteau après l'angle
        xs = sp * abs(poteaux_1[1]) if poteaux_1 else sp * (L / 2 - 1.0)
        with b.at((xs, 9.6, zm_)):
            mobilier.enseigne(b, texte=enseigne, variant=v)
    return {"emprise": (L, P), "hauteur": round(ytop, 2)}


def _zwerchhaus(b, xc, zf, H, pente, w, toit, enduit, bois, rng, niv):
    """Lucarne-pignon (Zwerchhaus) dans le plan de la façade : mur d'un étage au-dessus de la corniche, pignon à
    colombages (poteaux, entrait, écharpes), fenêtre double, petit toit stud à rives de bois."""
    hz = 5.0
    prof = (hz + w / 2 * 1.1 + 1.0) / pente + 1.0
    b.box((xc - w / 2, H - 0.3, zf), (xc + w / 2, H + hz, zf + prof), enduit, name="Zwerch")
    b.box((xc - w / 2 - 0.2, H - 0.3, zf - R_SABLIERE), (xc + w / 2 + 0.2, H + 0.5, zf + 0.5), bois, name="Sabliere")
    b.box((xc - w / 2 - 0.2, H + hz - 0.3, zf - R_SABLIERE), (xc + w / 2 + 0.2, H + hz + 0.4, zf + prof), bois,
          name="Sabliere")
    for s in (-1, 1):
        xa_, xb_ = sorted((xc + s * (w / 2 - 0.3), xc + s * (w / 2 + 0.22)))
        b.box((xa_, H + 0.5, zf - R_POTEAU), (xb_, H + hz - 0.3, zf + 0.4), bois, collide=False, name="Poteau")
        if niv < 3:
            _barre(b, xc + s * (w / 2 - 0.3), H + 0.5, xc + s * (w / 2 - 1.6), H + hz - 0.3, zf, bois)
    _fenetre(b, xc, H + 1.4, 2.6, 2.6, zf, meneau=True)
    Hz = H + hz + 0.4
    yr, ytop = _pignon_toit(b, xc - w / 2, xc + w / 2, zf, zf + prof, Hz, 1.1, toit, enduit, rng=rng, bois=bois,
                            rive_av=0.5, rive_ar=0.0)
    b.box((xc - 0.25, Hz, zf - R_POTEAU), (xc + 0.25, yr - 0.7, zf + 0.3), bois, collide=False, name="Poincon")
    if niv < 2:
        b.box((xc - 0.6, Hz + 0.6, zf - 0.15), (xc + 0.6, Hz + 1.8, zf + 0.1), col("fenetre"), collide=False,
              name="Oculus")
    return ytop


def _oriel(b, L, zs, n, H, enduit, bois, rng, niv):
    """Oriel d'angle (tourelle en encorbellement) : de l'étage 1 au faîte des murs, sur consoles, fenêtres sur
    trois faces, bandeaux de bois, flèche d'ardoise en gradins et pommeau."""
    wo = 4.6
    xo1 = L / 2 - 0.6
    xo0 = xo1 - wo
    z_av = zs[-1] - 0.9                       # l'oriel dépasse de 0,9 devant l'étage le plus avancé
    z_ar = zs[1] + 0.2
    y_bas, y_haut = 6.2, H + 1.2
    b.box((xo0, y_bas, z_av), (xo1, y_haut, z_ar), enduit, name="Oriel")
    # culot en encorbellement sous l'oriel
    b.wedge_under((xo0, y_bas - 2.2, z_av), (xo1, y_bas, zs[0]), bois, down="-z", name="Culot")
    xm = (xo0 + xo1) / 2
    for k in range(1, n + 1):
        y0 = 7 + 6 * (k - 1)
        b.box((xo0 - 0.15, y0 - 0.3, z_av - 0.25), (xo1 + 0.15, y0 + 0.4, z_ar), bois, name="Bandeau")
        _fenetre(b, xm, y0 + 1.5, 2.4, 3.2, z_av, meneau=k <= _details(niv)["meneau_max"], m=0.2)
    b.box((xo0 - 0.15, y_haut - 0.4, z_av - 0.25), (xo1 + 0.15, y_haut + 0.2, z_ar), bois, name="Bandeau")
    # flèche d'ardoise en gradins (stud) et pommeau
    zc = z_av + wo / 2                      # flèche carrée centrée sur l'avant de l'oriel
    y = y_haut + 0.2
    for i, (f, h) in enumerate(((1.12, 1.4), (0.74, 1.8), (0.36, 2.0))):
        hw = wo * f / 2
        b.box((xm - min(hw, wo / 2 + 0.3), y, max(zc - hw, z_av - 0.2)), (xm + min(hw, wo / 2 + 0.3), y + h, zc + hw),
              vr("ardoise" if i % 2 == 0 else "ardoise_claire", rng, 0.03), studs="top", name="Fleche")
        y += h
    b.ball((xm, y + 0.4, zc), 0.5, col("or"), collide=False, name="Pommeau")
    return y + 0.9


# ---------------------------------------------------------------------------
# Façades de pierre ou d'enduit (maisons bourgeoises, maisons à arcades)
# ---------------------------------------------------------------------------

def _chaines(b, L, zf, y0, y1, pierre, *, par_etage=2, etages=3, h0=7.0):
    """Chaînages d'angle des deux angles avant : bande claire continue et harpes alternées (une longue sur la
    façade, une longue sur le côté), `par_etage` harpes par étage."""
    for s in (-1, 1):
        xa, xb = sorted((s * (L / 2 - 1.0), s * (L / 2 + 0.15)))
        b.box((xa, y0, zf - 0.15), (xb, y1, zf + 1.0), pierre, collide=False, name="Chaine")
        if par_etage <= 0:
            continue
        i = 0
        for k in range(etages):
            for j in range(par_etage):
                yh = h0 + 6 * k + (0.9 + j * 2.8 if par_etage == 2 else 2.2)
                if yh + 1.3 > y1:
                    continue
                longue_facade = (i % 2 == 0)
                lx = 2.0 if longue_facade else 1.0
                lz = 1.0 if longue_facade else 2.0
                xa, xb = sorted((s * (L / 2 - lx), s * (L / 2 + 0.28)))
                b.box((xa, yh, zf - 0.28), (xb, yh + 1.3, zf + lz), pierre, collide=False, name="Harpe")
                i += 1


def _rangs_fenetres(b, L, zf, ks, nfen, *, cadre, meneau_k, volets, volets_k, fleurs, fleurs_k, h0=7.0, w=2.0, h=3.2,
                    sauf=None):
    """Fenêtres régulières des étages `ks` d'une façade plane : `nfen` par étage, volets et jardinières sur
    certains étages ; `sauf(k, i)` → True pour sauter une fenêtre (balcon, oriel)."""
    pas = (L - 3.0) / nfen
    lv = min(1.0, (pas - w - 0.7) / 2 - 0.15)
    for k in ks:
        yk = h0 + 6 * (k - 1)
        for i in range(nfen):
            if sauf and sauf(k, i):
                continue
            xc = -L / 2 + 1.5 + pas * (i + 0.5)
            _fenetre(b, xc, yk + 1.5, w, h, zf, cadre=cadre, meneau=k in meneau_k, m=0.32,
                     volets=volets if (k in volets_k and lv >= 0.7) else None, larg_volet=lv,
                     fleurs=fleurs if (k in fleurs_k and (i + k) % 2 == 0) else None)


def _pignon_redents(b, L, zf, H, pente, pierre, couronne, *, rng, marches=4, ep=1.4, cadre="fenetre_cadre",
                    n_fen=5):
    """Pignon à redents (gradins) en pierre de taille devant le comble : un bloc et un chaperon clair par gradin,
    pommeau au sommet ; les fenêtres du pignon (au plus `n_fen`) restent chacune dans la hauteur d'un gradin,
    entre deux chaperons. Le toit, derrière, reste caché par les gradins. Renvoie le haut."""
    rise = pente * L / 2
    pas = (L / 2) / marches
    y_bas = H - 0.2
    zw = zf - 0.25                                   # plan de façade des gradins
    poses = []
    for i in range(marches):
        hw = L / 2 - i * pas
        top = H + (i + 1) * pas * pente + 0.9
        b.box((-hw, y_bas, zw), (hw, top, zf + ep), vr(pierre, rng, 0.025), name="Redent")
        b.box((-hw - 0.2, top, zf - 0.5), (hw + 0.2, top + 0.45, zf + ep + 0.2), couronne, studs="top", name="Chaperon")
        y0 = (H + 0.4) if i == 0 else (y_bas + 0.45)  # bas libre du gradin (au-dessus de la corniche ou du chaperon)
        h = top - y0 - 1.2
        if h >= 1.0:
            if i == 0:
                poses += [(s_ * L / 5, y0 + 0.6, min(2.8, h), 1.9) for s_ in (-1, 1)]
            elif i == 1 and hw >= 6.5:
                poses += [(s_ * (hw - pas) / 1.6, y0 + 0.6, min(2.2, h), 1.5) for s_ in (-1, 1)]
            else:
                poses.append((0.0, y0 + 0.6, min(1.8, h), 1.2))
        y_bas = top
    for (x, y, h, w) in poses[:n_fen]:
        _fenetre(b, x, y, w, h, zw, cadre=cadre, meneau=False, m=0.3)
    hw = pas * 0.55
    b.box((-hw, y_bas + 0.45, zf - 0.1), (hw, y_bas + 1.6, zf + ep - 0.2), vr(pierre, rng, 0.02), name="Redent")
    b.ball((0, y_bas + 2.1, zf + ep / 2 - 0.1), 0.55, couronne, collide=False, name="Pommeau")
    return max(y_bas + 2.65, H + rise)


def _pignon_volutes(b, L, zf, H, pente, enduit, pierre, *, rng, ep=1.4, cadre="fenetre_cadre", n_fen=4):
    """Pignon à volutes (Renaissance) devant le comble : trois gradins d'enduit bordés de coins de pierre qui
    dessinent les volutes, corniches, fronton triangulaire et pommeau ; fenêtres dans la hauteur de chaque
    gradin (au plus `n_fen`). Renvoie le haut."""
    o = [L / 2, L / 2 * 0.68, L / 2 * 0.40, L / 2 * 0.16]
    y_bas = H - 0.2
    zw = zf - 0.25
    poses = []
    pierre = col(pierre)
    volute = shade(pierre, 0.86)                     # volutes un ton plus sombre que les corniches : lisibles
    for i in range(3):
        top = H + (L / 2 - o[i + 1]) * pente + 1.0
        b.box((-o[i + 1], y_bas, zw), (o[i + 1], top, zf + ep), vr(enduit, rng, 0.02), name="Gradin")
        for s in (-1, 1):
            xa, xb = sorted((s * o[i + 1], s * (o[i] + 0.15)))
            b.wedge((xa, y_bas, zf - 0.4), (xb, top, zf + ep + 0.1), volute, down="-x" if s < 0 else "+x", name="Volute")
        b.box((-o[i + 1] - 0.3, top - 0.05, zf - 0.5), (o[i + 1] + 0.3, top + 0.35, zf + ep + 0.2), pierre,
              studs="top", name="Corniche")
        y0 = (H + 0.4) if i == 0 else y_bas
        h = top - 0.05 - y0 - 1.2
        if h >= 1.0:
            if i == 0:
                poses += [(s_ * min(L / 5, o[1] - 1.6), y0 + 0.6, min(3.0, h), 1.9) for s_ in (-1, 1)]
            elif i == 1 and o[2] >= 3.2:
                poses += [(s_ * o[2] / 2, y0 + 0.6, min(2.2, h), 1.3) for s_ in (-1, 1)]
            else:
                poses.append((0.0, y0 + 0.6, min(1.8, h), min(1.3, 2 * o[i + 1] - 1.4)))
        y_bas = top + 0.35
    for (x, y, h, w) in poses[:n_fen]:
        _fenetre(b, x, y, w, h, zw, cadre=cadre, meneau=False, m=0.3)
    w = o[3] + 0.6
    b.wedge((-w, y_bas, zf - 0.3), (0, y_bas + 1.6, zf + ep), volute, down="-x", name="Fronton")
    b.wedge((0, y_bas, zf - 0.3), (w, y_bas + 1.6, zf + ep), volute, down="+x", name="Fronton")
    b.ball((0, y_bas + 2.0, zf + ep / 2), 0.5, col("or"), collide=False, name="Pommeau")
    return y_bas + 2.5


def _porte_cochere(b, x, zf, *, pierre, bois="porte", w=3.6, h=5.6, cle=True):
    """Porte cochère en plein cintre : encadrement de pierre, vantaux de bois, clé d'arc saillante."""
    _porte(b, x, w, h, zf, bois=bois, encadrement=pierre, arc=True, m=0.5)
    b.box((x - 0.12, 0.35, zf - 0.32), (x + 0.12, h - w / 2 - 0.05, zf - 0.2), shade(col(bois), 0.75), collide=False,
          name="Battement")
    if cle:
        b.box((x - 0.45, h - 0.45, zf - 0.32), (x + 0.45, h + 0.65, zf + 0.1), shade(col(pierre), 1.06), collide=False,
              name="Cle")


# ---------------------------------------------------------------------------
# 2) Maison bourgeoise
# ---------------------------------------------------------------------------

# (mur, encadrements/chaînages, volets, toit, fleurs)
_STYLES_BOURGEOISE = (
    dict(forme="redents", mur="pierre",
         pal=(("pierre_maison", "pierre_maison_claire", "volet_rouge", "tuile_fonce", "fleur_rouge"),
              ("gres", "pierre_maison_claire", "volet_vert", "tuile", "fleur_rose"))),
    dict(forme="gouttiere", mur="enduit",
         pal=(("enduit_saumon", "pierre_maison_claire", "volet_vert", "tuile_claire", "fleur_rouge"),
              ("enduit_bleu", "pierre_maison_claire", "volet_rouge", "tuile", "fleur_rose"),
              ("enduit_gris", "gres", "volet_bleu", "tuile_rouge", "fleur_rouge"))),
    dict(forme="volutes", mur="enduit",
         pal=(("enduit_ocre", "pierre_maison_claire", "volet_vert", "tuile_rouge", "fleur_rouge"),
              ("enduit_jaune", "gres", "volet_bleu", "tuile", "fleur_rose"))),
    dict(forme="pignon", mur="pierre", oriel=True,
         pal=(("gres", "pierre_maison_claire", "volet_bleu", "ardoise", "fleur_rouge"),
              ("pierre_maison_claire", "gres_fonce", "volet_vert", "ardoise_claire", "fleur_rose"))),
)


def maison_bourgeoise(b, variant=0, largeur=22, profondeur=18, etages=4, enseigne=None):
    """Maison bourgeoise de pierre ou d'enduit pastel (quartier du canal) : rez de pierre à porte cochère
    centrale, chaînages d'angle à harpes, bandeaux entre les étages, fenêtres régulières à encadrement de pierre,
    volets et géraniums, deux hautes cheminées ; v0 pignon à redents, v1 gouttereau à trois lucarnes et balcon
    de fer, v2 pignon à volutes, v3 pierre, oriel central et toit d'ardoise. ≤ 110 pièces, enseigne comprise."""
    n0 = len(b.parts)
    v = variant % len(_STYLES_BOURGEOISE)
    S = _STYLES_BOURGEOISE[v]
    pal = S["pal"][_choix(b, len(S["pal"]), "b", variant, largeur, etages, enseigne or "")]
    with b.group("MaisonBourgeoise"):
        return _budget(b, n0, 110, lambda niv: _bourgeoise(b, v, S, pal, largeur, profondeur, etages, enseigne, niv),
                       niveaux=6)


def _bourgeoise(b, v, S, pal, L, P, n, enseigne, niv):
    rng = b.rng
    n = max(1, int(n))
    mur_n, trim_n, volet_n, toit_n, fleur_n = pal
    mur = vr(mur_n, rng, 0.025)
    trim = vr(trim_n, rng, 0.02)
    x0, x1 = -L / 2, L / 2
    zf = -P / 2
    zb = P / 2 - 0.2
    H = 7 + 6 * n
    nfen = 4 if L >= 22 else 3
    niv = min(niv, 5)
    harpes = (2, 1, 1, 1, 0, 0)[niv]
    meneau_k = ({1, 2}, {1, 2}, {1}, {1}, {1}, set())[niv]
    volets_k = ({1, 2}, {1, 2}, {1, 2}, {1}, {1}, set())[niv]
    fleurs_k = ({1, 2}, {1}, {1}, {1}, {1}, set())[niv]
    cadre = trim_n if S["mur"] == "enduit" else "fenetre_cadre"

    # --- rez de pierre, porte cochère au milieu ---------------------------------
    with b.group("Rez"):
        rez = vr("pierre_maison" if mur_n != "pierre_maison" else "pierre_brune", rng, 0.03) if S["mur"] == "enduit" \
            else shade(mur, 0.94)
        b.box((x0, 0, zf), (x1, 7, zb), rez, name="Rez")
        b.box((x0 - 0.2, 0, zf - 0.2), (x1 + 0.2, 1.0, zb + 0.1), vr("soubassement", rng, 0.03), name="Soubassement")
        _porte_cochere(b, 0.0, zf, pierre=trim, cle=niv < 4)
        xg = L / 4 + 0.9
        for s in (-1, 1):
            if enseigne and s == 1:
                _vitrine(b, s * xg, 1.8, min(L / 2 - 5.0, 6.0), 3.4, zf, cadre="bois",
                         auvent=("toile_verte", "toile_rouge", "toile_bleue", "toile_jaune")[v] if niv < 3 else None)
            else:
                _fenetre(b, s * xg, 2.2, 2.2, 3.4, zf, cadre=trim, meneau=niv < 2, m=0.35)
        if niv < 3:
            _lanterne(b, -2.75, 6.4, zf)

    # --- corps des étages : un bloc, bandeaux, chaînages, fenêtres --------------------
    with b.group("Etages"):
        b.box((x0, 7, zf), (x1, H, zb), mur, name="Corps")
        for k in range(n):
            y = 7 + 6 * k
            b.box((x0 - 0.2, y - 0.3, zf - 0.3), (x1 + 0.2, y + 0.3, zb + 0.1), trim, studs="top", name="Bandeau")
        _chaines(b, L, zf, 7.3, H - 0.2, shade(trim, 0.97), par_etage=harpes, etages=n)

        def sauf(k, i):
            if S.get("oriel") and abs((-L / 2 + 1.5 + (L - 3.0) / nfen * (i + 0.5))) < 3.6:
                return True
            if v == 1 and k == 1 and nfen % 2 == 1 and i == nfen // 2:
                return True
            return False

        _rangs_fenetres(b, L, zf, range(1, n + 1), nfen, cadre=cadre, meneau_k=meneau_k, volets=volet_n,
                        volets_k=volets_k, fleurs=fleur_n, fleurs_k=fleurs_k, sauf=sauf)
        if v == 1:
            # balcon de fer devant la porte-fenêtre centrale (nombre impair) ou les deux fenêtres du milieu
            _balcon(b, 0.0, zf, 7.0, trim, niv, porte=nfen % 2 == 1,
                    w=5.0 if nfen % 2 == 1 else (L - 3.0) / nfen + 3.4)

    # --- toit ------------------------------------------------------------------------
    with b.group("Toit"):
        forme = S["forme"]
        if forme == "gouttiere":
            b.box((x0 - 0.3, H - 0.4, zf - 0.55), (x1 + 0.3, H + 0.4, zb + 0.3), trim, studs="top", name="Corniche")
            pente = 1.0
            yr, ytop, dessus = _gouttereau_toit(b, x0, x1, zf, zb, H + 0.4, pente, toit_n, mur, rng=rng, deb_av=1.2,
                                                rive=0.4)
            nl = 3 if niv < 4 else 2
            for i in range(nl):
                xd = -L / 2 + L * (i + 0.5) / nl
                _lucarne(b, xd, zf, dessus, pente, toit_n, mur, rng=rng, cadre=cadre, w=3.2, h=3.2, recul=1.4,
                         forme="pignon" if i % 2 == 0 or niv >= 3 else "rampant", allumee=(i == nl - 1))
            zc = (zf + zb) / 2 + 1.6
            for s in (-1, 1):
                ytop = max(ytop, _cheminee(b, s * (L / 2 - 2.2), zc, H, yr + 4.0))
        else:
            b.box((x0 - 0.3, H - 0.4, zf - 0.55), (x1 + 0.3, H + 0.4, zb + 0.3), trim, studs="top", name="Corniche")
            pente = 1.1 if forme != "pignon" else 1.15
            Hr = H + 0.4
            if forme == "pignon":
                yr, ytop = _pignon_toit(b, x0, x1, zf, zb, Hr, pente, toit_n, mur, rng=rng, bois=trim, rive_av=0.6)
                rise = pente * L / 2
                # fenêtres du comble (deux en bas, une en haut)
                xg = max(L / 5, 5.6) if S.get("oriel") else L / 5   # à l'écart de la flèche de l'oriel
                for s in (-1, 1):
                    _fenetre(b, s * xg, Hr + 1.2, 1.9, min(2.8, (L / 2 - xg - 1.3) * pente - 1.6), zf, cadre=cadre,
                             meneau=False, m=0.3)
                _fenetre(b, 0.0, Hr + rise * 0.5, 1.4, 1.8, zf, cadre=cadre, meneau=False, m=0.3, allumee=True)
            else:
                # comble caché derrière le pignon décoré : la rive avant du toit reste en retrait
                yr, ytop = _pignon_toit(b, x0, x1, zf + 1.4, zb, Hr, pente, toit_n, mur, rng=rng, rive_av=0.0)
                nfp = (5, 5, 4, 3, 3, 2)[niv]
                if forme == "redents":
                    ytop = max(ytop, _pignon_redents(b, L, zf, Hr, pente, mur, trim, rng=rng, cadre=cadre, n_fen=nfp))
                else:
                    ytop = max(ytop, _pignon_volutes(b, L, zf, Hr, pente, mur, trim, rng=rng, cadre=cadre, n_fen=nfp))
            for s in (-1, 1):
                xc = s * L / 4
                ych = Hr + (L / 2 - abs(xc)) * pente
                ytop = max(ytop, _cheminee(b, xc, zb - 3.0 - (2.5 if s > 0 else 0), Hr, max(ych + 4.5, yr + 2.5)))

    # --- oriel central (v3) --------------------------------------------------------------
    if S.get("oriel"):
        with b.group("Oriel"):
            ytop = max(ytop, _oriel_central(b, zf, n, mur, trim, rng, niv))

    # --- enseigne ----------------------------------------------------------------------------
    if enseigne:
        from assets import mobilier
        # sur le chaînage d'angle, côté de la vitrine (au-delà des volets de la dernière fenêtre)
        with b.at((L / 2 - 0.5, 9.6, zf - 0.15)):
            mobilier.enseigne(b, texte=enseigne, variant=v + 1)
    return {"emprise": (L, P), "hauteur": round(ytop, 2)}


def _balcon(b, x, zf, y, pierre, niv, *, porte=True, w=5.0, prof=1.6):
    """Balcon de pierre sur consoles devant la porte-fenêtre centrale du premier étage, garde-corps de fer."""
    fer = col("fonte")
    if porte:
        b.box((x - 1.5, y + 0.3, zf - 0.12), (x + 1.5, y + 5.2, zf + 0.2), col("fenetre_cadre"), collide=False,
              name="PorteFenetre")
        for s in (-1, 1):
            xa, xb = sorted((x + s * 0.12, x + s * 1.2))
            b.box((xa, y + 0.5, zf - 0.2), (xb, y + 4.9, zf - 0.05), col("fenetre"), collide=False, name="Vitre")
    b.box((x - w / 2, y - 0.1, zf - prof), (x + w / 2, y + 0.4, zf + 0.1), pierre, studs="top", name="Balcon")
    for s in (-1, 1):
        b.wedge_under((x + s * (w / 2 - 0.6) - 0.3, y - 1.4, zf - prof + 0.2), (x + s * (w / 2 - 0.6) + 0.3, y - 0.1, zf),
                      pierre, down="-z", collide=False, name="Console")
    b.box((x - w / 2 + 0.1, y + 2.6, zf - prof + 0.05), (x + w / 2 - 0.1, y + 2.85, zf - prof + 0.3), fer,
          collide=False, name="MainCourante")
    nb = 5 if niv < 3 else 4
    for i in range(nb):
        xx = x - w / 2 + 0.25 + i * (w - 0.5) / (nb - 1)
        b.box((xx - 0.1, y + 0.4, zf - prof + 0.07), (xx + 0.1, y + 2.6, zf - prof + 0.27), fer, collide=False,
              shadow=False, name="Barreau")


def _oriel_central(b, zf, nk, mur, pierre, rng, niv, w=6.0, sortie=2.0, y_bas=7.0):
    """Oriel central de pierre sur deux consoles, des étages 1 à `nk` : fenêtres sur la face avant et les côtés,
    bandeaux, petit toit d'ardoise en gradins et pommeau. Renvoie le haut."""
    y0, y1 = y_bas, y_bas + 6 * nk
    za = zf - sortie
    fonce = shade(pierre, 0.82)
    b.box((-w / 2, y0, za), (w / 2, y1, zf + 0.5), pierre, name="Oriel")
    b.box((-w / 2 - 0.2, y0 - 0.5, za - 0.2), (w / 2 + 0.2, y0, zf), fonce, name="Socle")
    for s in (-1, 1):
        b.wedge_under((s * (w / 2 - 0.5) - 0.4, y0 - 2.6, za + 0.2), (s * (w / 2 - 0.5) + 0.4, y0 - 0.5, zf), fonce,
                      down="-z", name="Console")
    for k in range(nk):
        yk = y0 + 6 * k
        if k:
            b.box((-w / 2 - 0.15, yk - 0.25, za - 0.2), (w / 2 + 0.15, yk + 0.25, zf), fonce, name="Bandeau")
        _fenetre(b, 0.0, yk + 1.5, 3.2, 3.2, za, meneau=True, m=0.3)
        if niv < 2:
            for s in (-1, 1):
                with b.at((s * w / 2, 0, za + sortie / 2 + 0.25), yaw=-90 * s):
                    _fenetre(b, 0.0, yk + 1.7, 0.9, 2.8, 0.0, meneau=False, m=0.18)
    # toit d'ardoise en gradins
    y = y1
    b.box((-w / 2 - 0.3, y, za - 0.3), (w / 2 + 0.3, y + 0.5, zf + 0.5), fonce, studs="top", name="Corniche")
    y += 0.5
    for i, (f, h) in enumerate(((1.0, 1.4), (0.66, 1.4), (0.33, 1.3))):
        hw = (w / 2) * f
        b.box((-hw, y, za + (w / 2 - hw) * 0.5), (hw, y + h, zf + 0.5), vr("ardoise" if i % 2 == 0 else "ardoise_claire",
                                                                       rng, 0.03), studs="top", name="Toiture")
        y += h
    b.ball((0, y + 0.4, za + w / 2 * 0.5), 0.45, col("or"), collide=False, name="Pommeau")
    return y + 0.85


# ---------------------------------------------------------------------------
# 3) Maison à arcades (grand-place)
# ---------------------------------------------------------------------------

_STYLES_ARCADES = (dict(haut="colombage"), dict(haut="redents"), dict(haut="gouttiere"), dict(haut="peinte"))
# (mur, bois ou encadrements, volets, toit, fleurs, pierre de l'arcade)
_PAL_ARCADES = (
    (("enduit_creme", "colombage", "volet_vert", "tuile", "fleur_rouge", "pierre_maison"),
     ("enduit_ocre", "colombage_rouge", "volet_brun", "tuile_claire", "fleur_rouge", "pierre_maison")),
    (("pierre_maison_claire", "gres", "volet_rouge", "tuile_fonce", "fleur_rouge", "gres"),
     ("gres", "pierre_maison_claire", "volet_vert", "tuile", "fleur_rose", "pierre_maison")),
    (("enduit_gris", "pierre_maison_claire", "volet_bleu", "tuile_claire", "fleur_rose", "pierre_maison"),
     ("enduit_saumon", "pierre_maison_claire", "volet_vert", "tuile_rouge", "fleur_rouge", "pierre_maison")),
    (("enduit_jaune", "pierre_maison_claire", "volet_rouge", "tuile_rouge", "fleur_rouge", "pierre_maison_claire"),
     ("enduit_saumon", "gres", "volet_bleu", "tuile", "fleur_rouge", "pierre_maison_claire")),
)


def maison_arcades(b, variant=0, largeur=26, profondeur=18, etages=3):
    """Maison de grand-place à rez en arcades (Laubengang) : arcs en plein cintre sur piliers, galerie couverte
    de 4 avec devantures sombres et lanternes ; étages et pignon sur la place ; v0 colombages, v1 pierre à pignon
    à redents, v2 enduit à gouttereau et lucarnes, v3 façade peinte et oriel. ≤ 110 pièces."""
    n0 = len(b.parts)
    v = variant % len(_STYLES_ARCADES)
    S = dict(_STYLES_ARCADES[v])
    S["pal"] = _PAL_ARCADES[v][_choix(b, len(_PAL_ARCADES[v]), "a", v, largeur, etages)]
    with b.group("MaisonArcades"):
        return _budget(b, n0, 110, lambda niv: _arcades(b, v, S, largeur, profondeur, etages, niv), niveaux=6)


def _rez_arcades(b, L, zf, zb, pierre, rng, niv, *, galerie=4.0, h=7.5):
    """Rez à arcades : piliers à impostes, arcs (écoinçons en coins), mur d'arcade au-dessus, galerie dallée,
    fond de galerie avec devantures et portes sombres, lanternes suspendues. Renvoie y du haut du rez."""
    narc = max(3, int(round(L / 6.5)))
    pil = 1.4
    pas = (L - pil) / narc
    yc, ys = 5.9, 4.0                    # clé de l'arc, naissance de l'arc
    ep = 1.3
    zg = zf + galerie                    # fond de la galerie
    # fond de galerie (le rez proprement dit) et sol dallé de la galerie
    b.box((-L / 2, 0, zg), (L / 2, h, zb), vr("enduit_creme", rng, 0.03), name="Rez")
    b.box((-L / 2 + 0.05, 0, zf - 0.05), (L / 2 - 0.05, 0.3, zg), vr("pave_clair", rng, 0.02), studs="top",
          name="Galerie")
    # mur d'arcade au-dessus des arcs
    b.box((-L / 2, yc, zf), (L / 2, h, zf + ep), pierre, name="Arcade")
    b.box((-L / 2 - 0.2, yc + 0.1, zf - 0.2), (L / 2 + 0.2, yc + 0.5, zf + ep - 0.1), shade(pierre, 0.92), name="Cordon")
    for i in range(narc + 1):
        x = -L / 2 + pil / 2 + i * pas
        b.box((x - pil / 2, 0, zf), (x + pil / 2, yc, zf + ep), pierre, name="Pilier")
        if niv < 3:
            b.box((x - pil / 2 - 0.2, ys - 0.4, zf - 0.2), (x + pil / 2 + 0.2, ys, zf + ep + 0.2), shade(pierre, 1.06),
                  collide=False, name="Imposte")
    for i in range(narc):
        xa = -L / 2 + pil + i * pas
        xb = xa + pas - pil
        r = (xb - xa) / 2
        cw = min(r * 0.75, yc - ys)
        b.wedge_under((xa, yc - cw, zf), (xa + cw, yc, zf + ep), pierre, down="+x", name="Arc")
        b.wedge_under((xb - cw, yc - cw, zf), (xb, yc, zf + ep), pierre, down="-x", name="Arc")
    # devantures au fond de la galerie : alternance porte / vitrine
    for i in range(narc):
        xm = -L / 2 + pil / 2 + (i + 0.5) * pas
        if i % 2 == 0:
            _vitrine(b, xm, 1.4, min(pas - 2.6, 3.8), 3.4, zg, cadre="bois", appui=niv < 2)
        else:
            _porte(b, xm, 2.2, 4.8, zg, arc=True, encadrement="bois", seuil=False, m=0.35)
    if niv < 4:
        for i in range(1, narc, 2) if narc > 2 else (1,):
            xm = -L / 2 + pil / 2 + i * pas
            b.box((xm - 0.1, yc - 1.0, zf + ep + 0.6), (xm + 0.1, yc, zf + ep + 0.8), col("fonte"), collide=False,
                  shadow=False, name="Tige")
            b.box((xm - 0.4, yc - 2.2, zf + ep + 0.3), (xm + 0.4, yc - 1.0, zf + ep + 1.1), col("lampe"), material="Neon",
                  collide=False, shadow=False, name="Lanterne")
    return h


def _arcades(b, v, S, L, P, n, niv):
    rng = b.rng
    n = max(1, int(n))
    mur_n, trim_n, volet_n, toit_n, fleur_n, pierre_n = S["pal"]
    pierre = vr(pierre_n, rng, 0.02)
    mur = vr(mur_n, rng, 0.025)
    x0, x1 = -L / 2, L / 2
    zf = -P / 2
    zb = P / 2 - 0.2
    h_rez = 7.5
    H = h_rez + 6 * n
    niv = min(niv, 5)
    with b.group("Rez"):
        _rez_arcades(b, L, zf, zb, pierre, rng, niv, h=h_rez)
    haut = S["haut"]
    if haut == "colombage":
        D = _details(niv + 1)
        bois = vr(trim_n, rng, 0.05)
        nf = 3 if L >= 20 else 2
        coin = max(2.6, min(4.0, (L - 0.6 - nf * (5.2 if nf == 2 else 4.6)) / 2))
        with b.group("Etages"):
            # un léger encorbellement au-dessus de l'arcade, puis un bloc de colombages
            ze = zf - 0.8
            _corniche(b, x0, x1, h_rez - 0.3, ze - 0.1, zf, bois, h=0.8)
            mots = ["croix" if (k == 0 or D["motif"] == "tous") else "v" for k in range(n)]
            _bloc_colombage(b, h_rez, n, ze, zb, L, enduit=mur, bois=bois, motifs=mots, n_fen=nf, coin=coin,
                            meneaux=[k + 1 <= D["meneau_max"] for k in range(n)],
                            volets=[volet_n if (k + 1) in D["volets"] else None for k in range(n)],
                            fleurs=fleur_n, fleurs_idx=[D["fleurs"].get(k + 1, ()) for k in range(n)])
        with b.group("Toit"):
            b.box((x0 - 0.25, H - 0.3, ze - R_SABLIERE), (x1 + 0.25, H + 0.5, zb + 0.2), bois, name="Sabliere")
            pente = 1.0
            rise = pente * L / 2
            yr, ytop = _pignon_toit(b, x0, x1, ze, zb, H, pente, toit_n, mur, rng=rng, bois=bois, rive_av=0.6)
            yc = H + 0.5 + rise * 0.4
            demi = (L / 2) * (1 - (yc - H) / rise)
            b.box((-demi, yc - 0.25, ze - R_POTEAU), (demi, yc + 0.35, ze + 0.3), bois, collide=False, name="Entrait")
            b.box((-0.27, H + 0.5, ze - R_POTEAU), (0.27, yc - 0.25, ze + 0.3), bois, collide=False, name="Poincon")
            for s in (-1, 1):
                _fenetre(b, s * L / 5.5, H + 1.0, 2.0, min(2.8, yc - H - 1.9), ze, meneau=niv < 3, m=0.22)
                if niv < 4:
                    _barre(b, s * 0.27, yc - 0.25, s * max(1.0, L / 5.5 - 1.9), H + 0.5, ze, bois)
            _fenetre(b, 0.0, yc + 1.0, 1.4, min(2.0, (yr - yc) * 0.3), ze, meneau=False, m=0.2)
            ytop = max(ytop, _cheminee(b, L / 4, zb - 3.5, H, H + rise * 0.5 + 5.0))
    else:
        cadre = trim_n if haut in ("gouttiere", "peinte") else "fenetre_cadre"
        nfen = 4 if L >= 22 else 3
        with b.group("Etages"):
            b.box((x0, h_rez, zf), (x1, H, zb), mur, name="Corps")
            for k in range(1, n):
                y = h_rez + 6 * k
                b.box((x0 - 0.2, y - 0.3, zf - 0.3), (x1 + 0.2, y + 0.3, zb + 0.1), vr(trim_n, rng, 0.02), studs="top",
                      name="Bandeau")
            if haut == "redents":
                _chaines(b, L, zf, h_rez + 0.3, H - 0.2, vr(trim_n, rng, 0.02), par_etage=(2, 1, 1, 1, 0, 0)[niv],
                         etages=n, h0=h_rez)

            def sauf(k, i):
                if haut == "peinte" and k <= n:
                    xc = -L / 2 + 1.5 + (L - 3.0) / nfen * (i + 0.5)
                    return abs(xc) < 3.6
                return False

            _rangs_fenetres(b, L, zf, range(1, n + 1), nfen, cadre=cadre,
                            meneau_k=({1, 2}, {1, 2}, {1}, {1}, {1}, set())[niv], volets=volet_n,
                            volets_k=({1, 2}, {1, 2}, {1, 2}, {1}, set(), set())[niv], fleurs=fleur_n,
                            fleurs_k=({1, 2}, {1}, {1}, {1}, set(), set())[niv], h0=h_rez, sauf=sauf)
        with b.group("Toit"):
            trim = vr(trim_n, rng, 0.02)
            b.box((x0 - 0.3, H - 0.4, zf - 0.55), (x1 + 0.3, H + 0.4, zb + 0.3), trim, studs="top", name="Corniche")
            Hr = H + 0.4
            if haut == "gouttiere":
                pente = 1.0
                yr, ytop, dessus = _gouttereau_toit(b, x0, x1, zf, zb, Hr, pente, toit_n, mur, rng=rng, deb_av=1.2, rive=0.4)
                nl = 3 if L >= 22 else 2
                for i in range(nl):
                    _lucarne(b, -L / 2 + L * (i + 0.5) / nl, zf, dessus, pente, toit_n, mur, rng=rng, cadre=cadre,
                             w=3.2, h=3.0, recul=1.4)
                for s in (-1, 1):
                    ytop = max(ytop, _cheminee(b, s * (L / 2 - 2.2), (zf + zb) / 2 + 1.6, H, yr + 4.0))
            elif haut == "redents":
                pente = 1.1
                yr, ytop = _pignon_toit(b, x0, x1, zf + 1.4, zb, Hr, pente, toit_n, mur, rng=rng, rive_av=0.0)
                ytop = max(ytop, _pignon_redents(b, L, zf, Hr, pente, mur, trim, rng=rng,
                                                 n_fen=(5, 5, 4, 3, 3, 2)[niv]))
                rise = pente * L / 2
                ytop = max(ytop, _cheminee(b, -L / 4, zb - 3.0, Hr, Hr + rise * 0.5 + 4.5))
            else:  # façade peinte : pignon simple sur la place, oriel au milieu
                pente = 1.1
                yr, ytop = _pignon_toit(b, x0, x1, zf, zb, Hr, pente, toit_n, mur, rng=rng, bois=trim, rive_av=0.6)
                rise = pente * L / 2
                for s in (-1, 1):
                    _fenetre(b, s * L / 5, Hr + 1.2, 1.8, min(2.6, rise * 0.4 - 1.0), zf, cadre=cadre, meneau=False, m=0.3)
                _fenetre(b, 0.0, Hr + rise * 0.5, 1.3, 1.7, zf, cadre=cadre, meneau=False, m=0.3)
                ytop = max(ytop, _cheminee(b, L / 4, zb - 3.0, Hr, Hr + rise * 0.5 + 4.5))
        if haut == "peinte":
            with b.group("Oriel"):
                ytop = max(ytop, _oriel_central(b, zf, min(n, 2), mur, trim, rng, niv, w=5.6, sortie=1.8, y_bas=h_rez))
    return {"emprise": (L, P), "hauteur": round(ytop, 2)}


# ---------------------------------------------------------------------------
# 4) Maison du fond (secondes rangées)
# ---------------------------------------------------------------------------

_FORMES_FOND = ("pignon", "gouttiere", "pignon", "gouttiere")
# (enduit, bois, toit) par variante
_PAL_FOND = (
    (("enduit_creme", "colombage", "tuile"), ("enduit_ocre", "colombage_brun", "tuile_fonce"),
     ("enduit_blanc", "colombage", "tuile_rouge")),
    (("enduit_ocre", "colombage_rouge", "tuile_brune"), ("enduit_saumon", "colombage", "tuile"),
     ("enduit_jaune", "colombage_rouge", "tuile_claire")),
    (("enduit_blanc", "colombage_brun", "tuile_rouge"), ("enduit_gris", "colombage", "tuile_claire"),
     ("enduit_jaune", "colombage_brun", "tuile")),
    (("enduit_saumon", "pierre_maison_claire", "tuile_claire"), ("enduit_creme", "pierre_maison_claire", "tuile_fonce"),
     ("enduit_bleu", "pierre_maison_claire", "tuile_brune")),
)


def maison_fond(b, variant=0, largeur=14, profondeur=12, etages=2):
    """Maison simple des secondes rangées : un bloc d'enduit, une sablière de bois, porte et fenêtre au rez,
    deux ou trois fenêtres par étage (volets au premier), toit de tuiles raide (pignon sur rue ou gouttereau
    selon la variante), une cheminée. ≤ 30 pièces."""
    n0 = len(b.parts)
    with b.group("MaisonFond"):
        return _budget(b, n0, 30, lambda niv: _fond(b, variant, largeur, profondeur, etages, niv), niveaux=4)


def _fond(b, variant, L, P, n, niv):
    rng = b.rng
    v = variant % 4
    mur_n, bois_n, toit_n = _PAL_FOND[v][_choix(b, len(_PAL_FOND[v]), "f", v, L, n)]
    forme = _FORMES_FOND[v]
    n = max(1, int(n))
    x0, x1 = -L / 2, L / 2
    zf, zb = -P / 2, P / 2 - 0.2
    H = 7 + 6 * n
    mur = vr(mur_n, rng, 0.03)
    bois = vr(bois_n, rng, 0.05)
    sp = 1 if v % 2 else -1
    b.box((x0, 0, zf), (x1, H, zb), mur, name="Corps")
    if niv < 3:
        b.box((x0 - 0.2, 0, zf - 0.2), (x1 + 0.2, 1.0, zb + 0.1), vr("soubassement", rng, 0.03), name="Soubassement")
    b.box((x0 - 0.25, 6.7, zf - 0.3), (x1 + 0.25, 7.4, zb + 0.15), bois, name="Sabliere")
    _porte(b, sp * (L / 2 - 3.0), 2.2, 5.0, zf, arc=v % 2 == 0 and niv < 2, encadrement=bois_n, m=0.35, seuil=False)
    if niv < 2:
        _fenetre(b, -sp * (L / 2 - 3.5), 2.0, 1.8, 2.6, zf, meneau=False, m=0.22)
    nf = 3 if (L >= 14 and n <= 2 and niv < 1) else 2
    pas = (L - 2) / nf
    for k in range(n):
        for i in range(nf):
            xc = -L / 2 + 1 + pas * (i + 0.5)
            _fenetre(b, xc, 7 + 6 * k + 1.6, 1.8, 2.8, zf, meneau=False, m=0.22,
                     volets=("volet_vert", "volet_rouge", "volet_bleu", "volet_brun")[v]
                     if (k == 0 and i != 1 and niv < 2) else None, larg_volet=0.8)
    if forme == "pignon":
        yr, ytop = _pignon_toit(b, x0, x1, zf, zb, H, 1.1, toit_n, mur, rng=rng, rive_av=0.4, rive_ar=0.3)
        ytop = max(ytop, _cheminee(b, L / 4 * (1 if v % 4 < 2 else -1), zb - 2.5, H, H + L / 4 * 1.1 + 4.0))
    else:
        yr, ytop, _d = _gouttereau_toit(b, x0, x1, zf, zb, H, 1.0, toit_n, mur, rng=rng, deb_av=0.8, deb_ar=0.6,
                                        rive=0.3)
        ytop = max(ytop, _cheminee(b, (L / 2 - 2.0) * sp, (zf + zb) / 2 + 1.5, H, yr + 3.5))
    return {"emprise": (L, P), "hauteur": round(ytop, 2)}


def _chaume_finitions(b, x0, x1, zf, zb, H, pente, ep, rng):
    """Toit de chaume : faîtage arrondi (gros cylindre de chaume sombre le long de X, qui déborde un peu des
    pignons), comme le boudin de paille cousu des vraies chaumières."""
    zm = (zf + zb) / 2
    rise = (zm - zf) * pente
    k = ep * math.hypot(1, pente)
    yr = H + rise + k
    b.cyl(((x0 + x1) / 2, yr - 0.2, zm), 1.0, (x1 - x0) + 0.6, vr("chaume_fonce", rng, 0.03), axis="x",
          name="Faitage")


# ---------------------------------------------------------------------------
# 5) Ferme de la prairie
# ---------------------------------------------------------------------------

def ferme(b, variant=0):
    """Ferme hors les murs, emprise 24 × 14 (x ∈ [-12, 12], z ∈ [-7, 7]), hauteur ≤ 16 : logis bas (un niveau et
    comble) et grange accolée à grandes portes de planches, appentis à bois, potager clos, banc, roue de
    charrette. v0 logis de pierre et toits de chaume ; v1 logis à colombages, tuiles brunes et pigeonnier ;
    v2 grange de pierre à tuiles rouges. ≤ 75 pièces."""
    n0 = len(b.parts)
    v = variant % 3
    with b.group("Ferme"):
        return _budget(b, n0, 75, lambda niv: _ferme(b, v, niv), niveaux=4)


def _ferme(b, v, niv):
    rng = b.rng
    chaume = v == 0
    toit_logis = "chaume" if chaume else ("tuile_brune" if v == 1 else "tuile_rouge")
    toit_grange = "chaume_fonce" if chaume else ("tuile_brune" if v == 1 else "tuile_rouge")
    ep_toit = 1.0 if chaume else 0.6
    # --- logis : x ∈ [-11.5, -1], z ∈ [-3.5, 5.4] ----------------------------------------
    lx0, lx1, lz0, lz1 = -11.5, -1.0, -3.5, 5.4
    Hl = 5.0
    pl = 1.25 if chaume else 1.1
    with b.group("Logis"):
        if v == 1:
            mur = vr("enduit_creme", rng, 0.03)
            bois = vr("colombage", rng, 0.05)
            b.box((lx0, 0, lz0), (lx1, Hl, lz1), mur, name="Logis")
            b.box((lx0 - 0.2, 0, lz0 - 0.2), (lx1 - 0.1, 1.0, lz1 + 0.1), vr("pierre_maison", rng, 0.03),
                  name="Soubassement")
            b.box((lx0 - 0.25, Hl - 0.3, lz0 - 0.3), (lx1 - 0.1, Hl + 0.4, lz1 + 0.2), bois, name="Sabliere")
            for xp in (lx0 + 0.3, -2.9, lx1 - 0.3):
                b.box((xp - 0.27, 1.0, lz0 - R_POTEAU), (xp + 0.27, Hl - 0.3, lz0 + 0.3), bois, collide=False,
                      name="Poteau")
            _barre(b, -2.9, 1.0, lx1 - 0.3, Hl - 0.3, lz0, bois)
            _barre(b, -2.9, Hl - 0.3, lx1 - 0.3, 1.0, lz0, bois)
        else:
            mur = vr("pierre_maison" if v == 0 else "pierre_brune", rng, 0.03)
            b.box((lx0, 0, lz0), (lx1, Hl, lz1), mur, name="Logis")
            b.box((lx0 - 0.2, 0, lz0 - 0.2), (lx1 - 0.1, 0.8, lz1 + 0.1), vr("soubassement", rng, 0.03),
                  name="Soubassement")
            for xa_ in (lx0 - 0.15, lx1 - 0.9):
                b.box((xa_, 0.8, lz0 - 0.15), (xa_ + 1.05, Hl, lz0 + 0.9), vr("pierre_maison_claire", rng, 0.02),
                      collide=False, name="Chaine")
        _porte(b, -5.0, 2.0, 4.0, lz0, bois="bois", encadrement="bois_moyen" if v == 1 else "pierre_maison_claire",
               arc=False, m=0.3, seuil=niv < 3)
        _fenetre(b, -8.4, 1.7, 1.6, 1.8, lz0, meneau=False, m=0.22, volets="volet_vert" if v != 1 else "volet_rouge",
                 larg_volet=0.75, fleurs="fleur_rouge" if niv < 2 else None)
        yr, ytop, dessus = _gouttereau_toit(b, lx0, lx1, lz0, lz1, Hl, pl, toit_logis,
                                            "chaume_fonce" if chaume else mur, rng=rng, ep=ep_toit, deb_av=0.8,
                                            deb_ar=0.5, rive=0.5)
        if niv < 2:
            _lucarne(b, -6.0, lz0, dessus, pl, toit_logis, mur, rng=rng, w=2.4, h=1.8, recul=1.2, forme="rampant")
        if chaume:
            _chaume_finitions(b, lx0, lx1, lz0, lz1, Hl, pl, ep_toit, rng)
        ytop = max(ytop, _cheminee(b, lx0 + 2.2, (lz0 + lz1) / 2 + 1.0, Hl, min(15.2, yr + 2.6),
                                   brique="pierre_brune" if v != 1 else "brique"))
    # --- grange accolée au logis : x ∈ [-1, 11.6], z ∈ [-5, 5.6] -------------------------------------------------
    gx0, gx1, gz0, gz1 = -1.0, 11.6, -5.0, 5.6
    Hg = 6.0
    with b.group("Grange"):
        gm = vr("pierre_maison", rng, 0.03) if v == 2 else vr("bois_gris", rng, 0.03)
        b.box((gx0, 0, gz0), (gx1, Hg, gz1), gm, name="Grange")
        b.box((gx0 - 0.1, 0, gz0 - 0.2), (gx1 + 0.2, 0.8, gz1 + 0.15), vr("soubassement", rng, 0.03), name="Soubassement")
        if v != 2:
            for xx in (gx0 + 0.5, gx1 - 0.5):
                b.box((xx - 0.3, 0.8, gz0 - 0.18), (xx + 0.3, Hg, gz0 + 0.2), vr("bois", rng, 0.04), collide=False,
                      name="Poteau")
        else:
            for xx in (gx0 - 0.1, gx1 - 0.85):
                b.box((xx, 0.8, gz0 - 0.15), (xx + 0.95, Hg, gz0 + 0.9), vr("pierre_maison_claire", rng, 0.02),
                      collide=False, name="Chaine")
        if v != 2 and niv < 2:
            # couvre-joints sombres sur le bardage de la grange, de part et d'autre de la porte
            for xx in (gx0 + 2.4, gx1 - 2.3):
                b.box((xx - 0.15, 0.8, gz0 - 0.12), (xx + 0.15, Hg - 0.2, gz0 + 0.1), vr("bois", rng, 0.04),
                      collide=False, name="CouvreJoint")
        # grande porte de grange à deux vantaux, écharpes
        xc = 4.6
        wp, hp = 5.6, 5.0
        b.box((xc - wp / 2 - 0.4, 0, gz0 - 0.26), (xc + wp / 2 + 0.4, hp + 0.4, gz0 + 0.15), col("bois"), collide=False,
              name="Huisserie")
        for s_ in (-1, 1):
            xa, xb = sorted((xc + s_ * 0.06, xc + s_ * wp / 2))
            b.box((xa, 0.0, gz0 - 0.32), (xb, hp, gz0 - 0.1), vr("bois_gris", rng, 0.06) if v == 2 else
                  vr("bois_moyen", rng, 0.05), collide=False, name="Vantail")
            if niv < 3:
                _barre(b, xa + 0.3, 0.6, xb - 0.3, hp - 0.6, gz0 - 0.32, col("bois"), ep=0.35, relief=0.14, name="Echarpe")
        # porte du fenil sous le pan
        b.box((xc - 1.0, Hg - 2.2, gz0 - 0.15), (xc + 1.0, Hg - 0.3, gz0 + 0.2), col(INTERIEUR), collide=False,
              name="Fenil")
        pente = 1.05
        yr2, ytop2, _d = _gouttereau_toit(b, gx0, gx1, gz0, gz1, Hg, pente, toit_grange, gm, rng=rng, ep=ep_toit,
                                          deb_av=0.9, deb_ar=0.5, rive=0.15)
        ytop = max(ytop, ytop2)
        if chaume and niv < 3:
            _chaume_finitions(b, gx0, gx1, gz0, gz1, Hg, pente, ep_toit, rng)
        if v == 1 and niv < 3:
            # pigeonnier : tourelle carrée blanche à cheval sur le faîtage, toit en gradins et pommeau
            zc = (gz0 + gz1) / 2
            xp = gx1 - 3.0
            b.box((xp - 1.2, yr2 - 1.2, zc - 1.2), (xp + 1.2, yr2 + 1.5, zc + 1.2), vr("enduit_blanc", rng, 0.02),
                  name="Pigeonnier")
            b.box((xp - 0.6, yr2 + 0.3, zc - 1.3), (xp + 0.6, yr2 + 1.0, zc - 1.1), col(INTERIEUR), collide=False,
                  name="Trou")
            b.box((xp - 1.5, yr2 + 1.5, zc - 1.5), (xp + 1.5, yr2 + 2.0, zc + 1.5), vr("tuile_brune", rng, 0.03),
                  studs="top", name="ToitPigeonnier")
            b.box((xp - 0.8, yr2 + 2.0, zc - 0.8), (xp + 0.8, yr2 + 2.6, zc + 0.8), vr("tuile_brune", rng, 0.03),
                  studs="top", name="ToitPigeonnier")
            b.ball((xp, yr2 + 2.9, zc), 0.35, col("or"), collide=False, name="Pommeau")
            ytop = max(ytop, yr2 + 3.25)
    # --- abords : appentis à bois, potager clos, banc, roue de charrette -------------------------
    with b.group("Abords"):
        xa0, xa1 = 8.4, 11.4
        za0 = -6.6
        for xx in (xa0 + 0.2, xa1 - 0.2):
            b.box((xx - 0.2, 0, za0), (xx + 0.2, 2.8, za0 + 0.4), col("bois"), name="Poteau")
        b.wedge((xa0 - 0.2, 2.8, za0 - 0.3), (xa1 + 0.2, 3.6, gz0), vr(toit_grange, rng, 0.03), down="-z", studs="top",
                name="Appentis")
        b.box((xa0 + 0.5, 0, za0 + 0.5), (xa1 - 0.5, 1.6, gz0 - 0.1), vr("bois_clair", rng, 0.05), name="Buches")
        if niv < 3:
            b.box((xa0 + 0.7, 1.6, za0 + 0.7), (xa1 - 0.7, 2.1, gz0 - 0.3), vr("bois_moyen", rng, 0.05), collide=False,
                  name="Buches")
        px0, px1 = -11.5, -6.6
        b.box((px0, 0, -6.9), (px1, 0.35, -4.7), col("terre_fonce"), studs="top", name="Potager")
        for i, coul in enumerate(("potager", "feuille_claire", "potager")[: 3 if niv < 2 else 2]):
            zz = -6.5 + i * 0.7
            b.box((px0 + 0.4, 0.35, zz), (px1 - 0.4, 0.85, zz + 0.4), col(coul), collide=False, name="Legumes")
        fence = vr("bois_clair", rng, 0.04)
        for xx in (px0 + 0.35, (px0 + px1) / 2, px1 - 0.35):
            b.box((xx - 0.18, 0, -7.0), (xx + 0.18, 1.6, -6.64), fence, collide=False, name="Piquet")
        b.box((px0 + 0.2, 1.0, -6.98), (px1 - 0.2, 1.25, -6.86), fence, collide=False, name="Lisse")
        if niv < 2:
            b.box((-10.9, 0, -4.6), (-8.5, 1.0, -3.9), col("bois"), name="Banc")
            b.box((-11.0, 1.0, -4.7), (-8.4, 1.25, -3.8), col("bois_clair"), studs="top", collide=False, name="Banc")
        if niv < 3:
            b.cyl((-2.2, 1.6, lz0 - 0.4), 1.5, 0.3, col("bois"), axis="z", collide=False, name="Roue")
            b.cyl((-2.2, 1.6, lz0 - 0.6), 0.4, 0.3, col("fer"), axis="z", collide=False, name="Moyeu")
    return {"emprise": (24, 14), "hauteur": round(ytop, 2)}
