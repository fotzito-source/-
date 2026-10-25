"""Murailles colossales de la ville fortifiée (style stud) : muraille à porte (entrée et repère final),
segments de rempart latéraux, tours d'angle, monte-charges et escaliers de rempart.

Vocabulaire commun (un rempart de ville réel agrandi, pierre beige-gris pâle, aucun emblème) :
- noyau d'un seul bloc (`mur`), talus au pied (y 0 → 10, débord 3, `mur_base`, studs) ;
- pilastres verticaux réguliers de 10 à 80 (4 de large et 1,5 de saillie côté extérieur, 3 et 1,0 côté ville),
  chapiteau `mur_pale` de 76 à 80 ; cordon de 40 à 41,5 (saillie 0,6) et corniche de 80 à 82 (saillie 1,2) ;
- chemin de ronde dont le dessus est à 84 (studs), parapet extérieur 84 → 87 et merlons 87 → 90 (3 de large,
  tous les 6), parapet côté ville 84 → 86, lisse sur les remparts latéraux ; sur les deux murailles à porte, le
  côté ville est crénelé lui aussi (84 → 87 et merlons), pour que leur silhouette se lise depuis la grand-rue ;
- « pixels » de pierre dans chaque baie : assises d'un seul bloc en tons alternés (saillie 0,15), pierres isolées
  (saillie 0,3), meurtrières sombres, coulures sous les gargouilles, lierre au pied.

Toutes les fonctions suivent les conventions de la zone : origine au centre de l'emprise au sol, avant vers -Z
local, renvoient {"emprise": (largeur, profondeur), "hauteur": h}. Les tunnels de porte dégagent |x| < 52 de
y = 0 à y = 46 sur toute l'épaisseur ; ce qui enjambe le couloir (voûte, herse relevée, corps de garde) est
au-dessus de 46.
"""

from __future__ import annotations

import math

import numpy as np

from assets import mobilier
from kit import shade
from palette import c, pierre_mur

# ---------------------------------------------------------------------------
# Niveaux communs (identiques dans toutes les fonctions : murs, tours et portes se raccordent)
# ---------------------------------------------------------------------------
TALUS = 3.0                      # débord du talus au pied de chaque grande face
S_BANDE, S_PIERRE, S_FENTE, S_COULURE = 0.15, 0.3, 0.1, 0.2
X_TOUR, COTE_TOUR = 135.0, 32.0  # tours d'angle posées par zone.py : |x| ∈ [119, 151] (décor inutile dedans)
TOUR0, TOUR1 = X_TOUR - COTE_TOUR / 2, X_TOUR + COTE_TOUR / 2
TONS_ASSISES = ("mur_clair", "mur_fonce", "mur_pale", "mur_fonce", "mur_clair", "mur_ombre")


def _niv(H: float = 90.0) -> dict:
    """Hauteurs communes pour une muraille de hauteur H (90 dans la zone)."""
    return {
        "talus": 10.0, "cordon": (40.0, 41.5), "corniche": (H - 10, H - 8), "chap": (H - 14, H - 10),
        "dalle": H - 6.5, "chemin": H - 6, "par_int": H - 4, "par_ext": H - 3, "merlon": H, "pil0": 4.0,
        "deco": (11.0, H - 15.5),
    }


# ---------------------------------------------------------------------------
# Outils géométriques
# ---------------------------------------------------------------------------

def _poutre(b, a, bb, ep, col, name: str = "Poutre", **kw):
    """Bloc tendu de a à bb (section ep ou (ep_x, ep_y)) : jambes de force, flèches, croix, limons."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    d = bb - a
    n = float(np.linalg.norm(d))
    zax = d / n
    up = np.array([0.0, 1.0, 0.0]) if abs(zax[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    xax = np.cross(up, zax)
    xax /= np.linalg.norm(xax)
    yax = np.cross(zax, xax)
    ex, ey = (ep, ep) if np.isscalar(ep) else ep
    return b.part("block", (ex, ey, n), (a + bb) / 2, np.column_stack([xax, yax, zax]), col, name=name, **kw)


def _corde(b, a, bb, r: float = 0.12, col=None, name: str = "Corde"):
    """Corde (cylindre fin, sans collision) de a à bb."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    d = bb - a
    n = float(np.linalg.norm(d))
    x = d / n
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return b.part("cyl", (n, 2 * r, 2 * r), (a + bb) / 2, np.column_stack([x, y, z]), col or c("corde"),
                  collide=False, shadow=False, name=name)


def _intervalles(xa: float, xb: float, coupes=()) -> list:
    """[xa, xb] privé des intervalles `coupes`."""
    res = [(xa, xb)]
    for c0, c1 in coupes:
        nouv = []
        for a, bb in res:
            if c1 <= a or c0 >= bb:
                nouv.append((a, bb))
                continue
            if c0 > a:
                nouv.append((a, c0))
            if c1 < bb:
                nouv.append((c1, bb))
        res = nouv
    return [(a, bb) for a, bb in res if bb - a > 0.05]


def _chevauche(r, liste, marge: float = 0.0) -> bool:
    x0, x1, y0, y1 = r
    return any(x0 < q1 + marge and x1 > q0 - marge and y0 < p1 + marge and y1 > p0 - marge for q0, q1, p0, p1 in liste)


def _sym(s: int, a: float, bb: float):
    """Intervalle [s·a, s·bb] trié (côté gauche s = -1, droit s = +1)."""
    return tuple(sorted((s * a, s * bb)))


# ---------------------------------------------------------------------------
# Parement d'une grande face (repère : face dans le plan z = z0, tournée vers -Z)
# ---------------------------------------------------------------------------

def _talus(b, xa, xb, z0, niv, coupes=()):
    for a, bb in _intervalles(xa, xb, coupes):
        b.wedge((a, 0, z0 - TALUS), (bb, niv["talus"], z0), c("mur_base"), down="-z", studs="top", name="Talus")


def _bandeau(b, xa, xb, z0, y0, y1, saillie, coupes=(), col=None, name="Cordon"):
    for a, bb in _intervalles(xa, xb, coupes):
        b.box((a, y0, z0 - saillie), (bb, y1, z0), col or c("mur_pale"), name=name)


def _pilastres(b, xs, z0, larg, saillie, niv, chapiteau=True):
    """Nervures verticales (fût clair et chapiteau pâle) ; le fût part de l'intérieur du talus."""
    yc0, yc1 = niv["chap"]
    for x in xs:
        b.box((x - larg / 2, niv["pil0"], z0 - saillie), (x + larg / 2, yc0 if chapiteau else yc1, z0),
              c("mur_fonce"), name="Pilastre")
        if chapiteau:
            b.box((x - larg / 2 - 0.2, yc0, z0 - saillie - 0.4), (x + larg / 2 + 0.2, yc1, z0), c("mur_pale"),
                  name="Chapiteau")


def _parapet(b, xa, xb, z0, niv, crenele: bool, merlons=(), coupes=()):
    """Parapet d'un pas d'épaisseur dont la face est dans le plan z0 ; merlons (centres `merlons`) s'il est crénelé."""
    y_haut = niv["par_ext"] if crenele else niv["par_int"]
    for a, bb in _intervalles(xa, xb, coupes):
        b.box((a, niv["dalle"], z0), (bb, y_haut, z0 + 1), c("mur"), name="Parapet")
    if crenele:
        for xm in merlons:
            b.box((xm - 1.5, y_haut, z0), (xm + 1.5, niv["merlon"], z0 + 1), c("mur_clair"), name="Merlon")


def _baies(xa, xb, separateurs, y0, y1, ext: float = 0.4, larg_min: float = 1.5) -> list:
    """Baies entre séparateurs (x0, x1) : (x0, x1, prolongement gauche, prolongement droit, y0, y1).
    Les assises se prolongent de `ext` sous les pilastres, jamais au-delà des extrémités du mur."""
    seps = sorted((s0, s1) for s0, s1 in separateurs if s1 > xa and s0 < xb)
    res, cur, e_cur = [], xa, 0.0
    for s0, s1 in seps:
        if s0 > cur + larg_min:
            res.append((cur, s0, e_cur, ext, y0, y1))
        if s1 > cur:
            cur, e_cur = s1, ext
    if xb > cur + larg_min:
        res.append((cur, xb, e_cur, 0.0, y0, y1))
    return res


def _appareil(b, rng, baies, z0, niv, n_bandes=(1, 2), n_pierres=(1, 2), occupe=None, k_ton=None, grappe: int = 1):
    """Assises en tons alternés (un bloc par baie) puis pierres « pixel » isolées. Les assises sont aux y entiers,
    les pierres à x,25 / x,75 : jamais de face commune. `occupe` : rectangles (x0, x1, y0, y1) déjà pris."""
    occupe = [] if occupe is None else occupe
    cz0, cz1 = niv["cordon"]
    k_ton = int(rng.integers(0, len(TONS_ASSISES))) if k_ton is None else k_ton
    n = 0
    for (x0, x1, e0, e1, ymin, ymax) in baies:
        nb = int(rng.integers(n_bandes[0], n_bandes[1] + 1))
        prises = []
        for _ in range(nb * 8):
            if len(prises) >= nb:
                break
            h = float(rng.choice((2.0, 3.0, 3.0, 4.0)))
            lo, hi = int(math.ceil(ymin)), int(math.floor(ymax - h))
            if hi < lo:
                break
            y0 = float(rng.integers(lo, hi + 1))
            y1 = y0 + h
            if y0 < cz1 + 1.0 and y1 > cz0 - 1.0:
                continue
            if any(y0 < q1 + 1.0 and y1 > q0 - 1.0 for q0, q1 in prises):
                continue
            if _chevauche((x0, x1, y0, y1), occupe):
                continue
            prises.append((y0, y1))
            col = c(TONS_ASSISES[k_ton % len(TONS_ASSISES)])
            k_ton += 1
            b.box((x0 - e0, y0, z0 - S_BANDE), (x1 + e1, y1, z0), col, collide=False, name="Assise")
            n += 1
        npier = int(rng.integers(n_pierres[0], n_pierres[1] + 1))
        for _ in range(npier * 10):
            if npier <= 0:
                break
            w = float(rng.choice((2.0, 3.0, 3.0, 4.0)))
            if x1 - x0 < w + 1.6:
                break
            hh = float(rng.choice((1.5, 2.0)))
            x = round(float(rng.uniform(x0 + 0.8, x1 - 0.8 - w)) * 2) / 2
            x = min(max(x, x0 + 0.8), x1 - 0.8 - w)
            lo, hi = int(math.ceil(ymin)), int(math.floor(ymax - hh - 0.5))
            if hi < lo:
                break
            y = float(rng.integers(lo, hi + 1)) + 0.25
            if y < cz1 + 0.6 and y + hh > cz0 - 0.6:
                continue
            r = (x, x + w, y, y + hh)
            if _chevauche(r, occupe, 0.3):
                continue
            # grappe : 1 à `grappe` pierres jointives sur la même assise, en tons différents
            k_g = int(rng.integers(1, grappe + 1))
            pierres, xx = [], x
            for g in range(k_g):
                wg = w if g == 0 else float(rng.choice((2.0, 3.0)))
                hg = hh if g == 0 else float(rng.choice((1.5, 2.0)))
                rg = (xx, xx + wg, y, y + hg)
                if xx + wg > x1 - 0.8 or (g > 0 and _chevauche(rg, occupe, 0.3)):
                    break
                pierres.append(rg)
                xx += wg
            occupe.append((x, xx, y, y + 2.0))
            prev = None
            for (qa, qb, ya, yb) in pierres:
                col = c("mur_ombre") if rng.random() < 0.22 else pierre_mur(rng)
                while prev is not None and col == prev:
                    col = pierre_mur(rng)
                prev = col
                b.box((qa, ya, z0 - S_PIERRE), (qb, yb, z0), col, collide=False, name="Pierre")
                n += 1
            npier -= 1
    return n


def _meurtrieres(b, rng, baies, z0, nombre: int, occupe, niv, hauteurs=(18.0, 30.0, 52.0, 64.0)):
    """Fentes sombres de 1 × 4 (saillie 0,1) avec un petit linteau clair, au milieu de baies tirées au hasard."""
    larges = [bb for bb in baies if bb[1] - bb[0] > 5]
    if not larges:
        return
    for k in range(nombre):
        x0, x1, _, _, ymin, ymax = larges[int(rng.integers(0, len(larges)))]
        x = round((x0 + x1) / 2 * 2) / 2 + float(rng.choice((-1.0, 0.0, 1.0)))
        y = float(rng.choice(hauteurs))
        if y < ymin or y + 5 > ymax:
            continue
        r = (x - 0.5, x + 0.5, y, y + 4.6)
        if _chevauche(r, occupe, 0.6):
            continue
        occupe.append((x - 1.0, x + 1.0, y - 0.2, y + 5.0))
        b.box((x - 0.5, y, z0 - S_FENTE), (x + 0.5, y + 4, z0), c("mur_joint"), collide=False, name="Meurtriere")
        b.box((x - 0.9, y + 4.0, z0 - 0.25), (x + 0.9, y + 4.6, z0), c("mur_pale"), collide=False, name="Linteau")


def _gargouille(b, x, z0, niv, occupe, y_bas: float = 57.6):
    """Gargouille de pierre sous la corniche et coulure de pluie (saillie 0,2, devant les assises)."""
    y_g = niv["corniche"][0] - 2.0
    b.box((x - 0.5, y_g, z0 - 1.8), (x + 0.5, y_g + 1.0, z0), c("mur_fonce"), collide=False, name="Gargouille")
    b.box((x - 0.6, y_bas, z0 - S_COULURE), (x + 0.6, y_g, z0), c("mur_coulure"), collide=False, name="Coulure")
    occupe.append((x - 0.9, x + 0.9, y_bas, y_g + 1.0))


def _lierre(b, rng, x, z0, occupe, h: float = 12.0):
    """Touffe de lierre au pied du mur (au ras du talus), en deux tons : nappe large en bas qui s'effiloche en montant
    d'un côté (une tige droite à bras se lisait comme un cactus) ; emprise x ∈ [x - 2,5, x + 2,5]. Sans tirage
    aléatoire (le côté dépend de x) pour ne pas décaler l'appareil des murs."""
    w = 2.0
    y0 = 9.0
    s = 1 if int(round(x)) % 2 == 0 else -1          # côté vers lequel le lierre grimpe
    b.box((x - 2.2, y0 - 0.2, z0 - 0.4), (x + 2.2, y0 + 0.42 * h, z0), c("lierre"), collide=False, name="Lierre")
    b.box((x - 1.2 * s, y0 + 0.25 * h, z0 - 0.55), (x + 1.9 * s, y0 + 0.72 * h, z0), c("lierre_clair"),
          collide=False, name="Lierre")
    b.box((x + 0.2 * s, y0 + 0.6 * h, z0 - 0.45), (x + 1.6 * s, y0 + h, z0), c("lierre"), collide=False,
          name="Lierre")
    b.box((x - 2.5 * s, y0 + 0.3 * h, z0 - 0.62), (x - 1.1 * s, y0 + 0.52 * h, z0), c("lierre_clair"), collide=False,
          name="Lierre")
    b.box((x - 2.4, y0 - 0.5, z0 - 0.75), (x + 2.4, y0 + 1.0, z0), c("mur_mousse"), collide=False, name="Mousse")
    occupe.append((x - w / 2 - 1.8, x + w / 2 + 1.8, 0, y0 + h + 1.8))


def _lanterne_compacte(b, x, y, z0):
    """Lanterne murale compacte (4 pièces) : potence, verre Neon, chapeau et culot de fonte. Origine : mur en z0."""
    fer = c("fonte")
    b.box((x - 0.15, y + 0.6, z0 - 1.9), (x + 0.15, y + 0.9, z0 + 0.3), fer, collide=False, shadow=False, name="Potence")
    b.box((x - 0.55, y - 1.4, z0 - 1.95), (x + 0.55, y, z0 - 0.85), c("lampe"), material="Neon", collide=False,
          shadow=False, name="Lanterne")
    b.box((x - 0.75, y, z0 - 2.15), (x + 0.75, y + 0.6, z0 - 0.65), fer, collide=False, name="Chapeau")
    b.box((x - 0.45, y - 1.75, z0 - 1.85), (x + 0.45, y - 1.4, z0 - 0.95), fer, collide=False, name="Culot")


def _banniere(b, x, y_haut, z0, long_: float = 12.0, larg: float = 3.0, cols=("drapeau_rouge", "toile_creme"),
              saillie: float = 1.8):
    """Bannière de tissu uni à bande (aucun emblème) sur une tringle qui sort du mur (face z0, vers -Z)."""
    zc = z0 - saillie
    fonte = c("fonte")
    b.box((x - 0.15, y_haut - 0.35, zc - 0.1), (x + 0.15, y_haut - 0.05, z0 + 0.3), fonte, collide=False, name="Potence")
    b.box((x - larg / 2 - 0.4, y_haut - 0.6, zc - 0.15), (x + larg / 2 + 0.4, y_haut - 0.3, zc + 0.15), fonte,
          collide=False, name="Tringle")
    b.box((x - larg / 2, y_haut - long_ + 1.4, zc - 0.08), (x + larg / 2, y_haut - 0.6, zc + 0.08), c(cols[0]),
          collide=False, shadow=False, name="Banniere")
    b.box((x - larg / 2, y_haut - long_, zc - 0.08), (x + larg / 2, y_haut - long_ + 1.4, zc + 0.08), c(cols[1]),
          collide=False, shadow=False, name="Banniere")
    b.box((x - 0.4, y_haut - long_ + 1.4, zc - 0.2), (x + 0.4, y_haut - 0.6, zc - 0.08), c(cols[1]),
          collide=False, shadow=False, name="Bande")


def _petit_drapeau(b, x, y, z, h: float = 5.0, cols=("drapeau_rouge", "drapeau_blanc")):
    """Petit drapeau à deux bandes (4 pièces) : hampe, pommeau, deux lés horizontaux."""
    b.cyl((x, y + h / 2, z), 0.15, h, c("fonte"), axis="y", collide=False, name="Hampe")
    b.ball((x, y + h + 0.2, z), 0.3, c("or"), collide=False, name="Pommeau")
    b.box((x + 0.15, y + h - 1.9, z - 0.06), (x + 3.1, y + h - 1.0, z + 0.06), c(cols[0]), collide=False, shadow=False,
          name="Drapeau")
    b.box((x + 0.15, y + h - 2.8, z - 0.06), (x + 3.1, y + h - 1.9, z + 0.06), c(cols[1]), collide=False, shadow=False,
          name="Drapeau")


def _toit_gradins(b, cx, y0, cz, w, d, n, dh, retrait, cols=("ardoise", "ardoise_fonce"), name="Toit") -> float:
    """Toit en pavillon « stud » : gradins de blocs qui rétrécissent (studs sur chaque dessus). Renvoie le sommet."""
    rx, rz = (retrait, retrait) if np.isscalar(retrait) else retrait
    y = y0
    for i in range(n):
        ww, dd = w - 2 * rx * i, d - 2 * rz * i
        if ww <= 0.6 or dd <= 0.6:
            break
        b.box((cx - ww / 2, y, cz - dd / 2), (cx + ww / 2, y + dh, cz + dd / 2), c(cols[i % len(cols)]), studs="top",
              name=name)
        y += dh
    return y


def _baie_cintree(b, x, y0, w, h, z0, vitre=None, neon=False, meneau=False):
    """Fenêtre cintrée « stud » sur une face z0 (vers -Z) : appui clair, baie sombre, tête en gradin, arc clair."""
    p = c("mur_pale")
    b.box((x - w / 2 - 0.5, y0 - 0.7, z0 - 0.5), (x + w / 2 + 0.5, y0, z0), p, name="Appui")
    b.box((x - w / 2 - 0.7, y0 + h, z0 - 0.25), (x + w / 2 + 0.7, y0 + h + w * 0.3 + 1.0, z0), p, name="Arc")
    vit = vitre if vitre is not None else c("noir")
    kw = dict(material="Neon") if neon else {}
    b.box((x - w / 2, y0, z0 - 0.12), (x + w / 2, y0 + h, z0), vit, collide=False, name="Baie", **kw)
    b.box((x - w * 0.32, y0 + h, z0 - 0.35), (x + w * 0.32, y0 + h + w * 0.3, z0), vit, collide=False,
          name="Baie", **kw)
    if meneau:
        b.box((x - 0.3, y0, z0 - 0.45), (x + 0.3, y0 + h, z0), p, collide=False, name="Meneau")


# ---------------------------------------------------------------------------
# Équipements du chemin de ronde (canon sur rails, grue, tourelle de guet)
# ---------------------------------------------------------------------------

def _canon_rail(b, sens: int = -1):
    """Canon de rempart sur affût à roulettes et rails (19 pièces), artillerie générique.
    Origine : sur le chemin de ronde, contre la face intérieure du parapet crénelé ; tire vers -Z (sens = -1)
    ou vers +Z (sens = +1) à travers un créneau (axe à 4,5 au-dessus du chemin : 88,5 dans la zone)."""
    if sens > 0:
        with b.at((0, 0, 0), yaw=180):
            _canon_rail(b, -1)
        return
    fonte, bois, fer = c("fonte"), c("bois_moyen"), c("fer")
    with b.group("Canon"):
        for z in (1.4, 7.4):
            b.box((-2.2, 0, z - 0.45), (2.2, 0.3, z + 0.45), c("bois"), studs="top", name="Traverse")
        for x in (-1.3, 1.3):
            b.box((x - 0.25, 0.3, 0.4), (x + 0.25, 0.7, 8.4), c("rail"), name="Rail")
        for x in (-1.3, 1.3):
            for z in (2.6, 6.0):
                b.cyl((x, 1.35, z), 0.65, 0.4, fer, axis="x", name="Roue")
        b.box((-1.0, 1.0, 1.8), (1.0, 2.4, 6.8), bois, name="Affut")
        for x in (-0.8, 0.8):
            b.box((x - 0.2, 2.4, 2.0), (x + 0.2, 4.0, 6.4), bois, name="Flasque")
        b.cyl((0, 4.5, 0.6), 1.05, 7.2, fonte, axis="z", name="Tube")
        b.cyl((0, 4.5, -2.75), 1.3, 0.5, fonte, axis="z", collide=False, name="Bouche")
        b.cyl((0, 4.5, 3.4), 1.3, 1.6, fonte, axis="z", collide=False, name="Culasse")
        b.ball((0, 4.5, 4.6), 0.6, fonte, collide=False, name="Bouton")
        for (x, y, z) in ((3.0, 0.55, 5.4), (3.0, 0.55, 6.5), (4.05, 0.55, 5.95), (3.35, 1.45, 5.95)):
            b.ball((x, y, z), 0.55, fonte, collide=False, name="Boulet")


def _grue(b, charge: int = 0, y_ch: float = -9.0):
    """Grue de bois du chemin de ronde (≤ 16 pièces) : sole, mât, jambes de force, flèche penchée vers -Z
    au-dessus de la ville (porte-à-faux ≤ 8 au-delà de la face), poulie, corde et charge suspendue, treuil.
    Origine : sur le chemin de ronde, contre la face intérieure du parapet côté ville (le parapet occupe z ∈ [-1, 0])."""
    bois = c("bois_echafaud")
    fonce = shade(bois, 0.78)
    with b.group("Grue"):
        b.box((-2.2, 0, 0.3), (2.2, 0.6, 5.2), fonce, studs="top", name="Sole")
        b.box((-0.6, 0.6, 2.0), (0.6, 13.4, 3.2), bois, name="Mat")
        _poutre(b, (0, 0.6, 5.0), (0, 6.5, 3.2), 0.5, bois, name="JambeForce")
        _poutre(b, (-2.0, 0.6, 2.6), (-0.6, 5.5, 2.6), 0.45, bois, name="JambeForce")
        _poutre(b, (0, 11.2, 2.6), (0, 17.2, -7.6), 0.8, bois, name="Fleche")
        _poutre(b, (0, 13.4, 2.6), (0, 15.2, -3.0), 0.3, fonce, collide=False, name="Tirant")
        b.box((-0.75, 13.4, 1.85), (0.75, 13.9, 3.35), fonce, name="Chapeau")
        b.cyl((0, 16.6, -7.3), 0.75, 0.5, c("fer"), axis="x", collide=False, name="Poulie")
        zq = -8.0
        b.cyl((0, (16.6 + y_ch + 2.4) / 2, zq), 0.1, 16.6 - (y_ch + 2.4), c("corde"), axis="y", collide=False,
              shadow=False, name="Corde")
        if charge % 2 == 0:
            b.box((-1.2, y_ch, zq - 1.2), (1.2, y_ch + 2.4, zq + 1.2), c("bois_clair"), name="Caisse")
            b.box((-1.3, y_ch + 0.9, zq - 1.3), (1.3, y_ch + 1.5, zq + 1.3), c("bois_moyen"), collide=False, name="Cerclage")
        else:
            b.cyl((-0.6, y_ch + 1.3, zq), 1.0, 2.6, c("bois_moyen"), axis="y", name="Tonneau")
            b.cyl((0.9, y_ch + 1.3, zq), 0.9, 2.6, c("bois_moyen"), axis="y", name="Tonneau")
        b.cyl((0, 1.6, 4.4), 0.7, 2.6, fonce, axis="x", name="Treuil")
        _corde(b, (0, 2.3, 4.4), (0, 13.0, 2.6), 0.1)
    return 16


def _tourelle(b, rng, drapeau: int = 0, h: float = 10.0):
    """Tourelle de guet carrée de 7 × 7 (≈ 24 pièces) posée sur le chemin de ronde : socle, fût de pierre claire,
    baies sombres cintrées sur les 4 faces, porte, corniche, toit d'ardoise en gradins, petit drapeau à bandes."""
    with b.group("Tourelle"):
        b.box((-3.9, 0, -3.9), (3.9, 1.0, 3.9), c("mur_fonce"), studs="top", name="Socle")
        b.box((-3.5, 1.0, -3.5), (3.5, h - 0.8, 3.5), c("mur_clair"), name="Fut")
        b.box((-3.75, 1.0, -3.75), (-2.6, h - 0.8, -2.6), c("mur_pale"), name="Chaine")
        b.box((2.6, 1.0, 2.6), (3.75, h - 0.8, 3.75), c("mur_pale"), name="Chaine")
        b.box((-4.1, h - 0.8, -4.1), (4.1, h, 4.1), c("mur_pale"), name="Corniche")
        for yaw in (0, 90, 180, 270):
            with b.at((0, 0, 0), yaw=yaw):
                b.box((-0.9, 5.0, -3.62), (0.9, 7.6, -3.5), c("noir"), collide=False, name="Baie")
                b.box((-0.5, 7.6, -3.62), (0.5, 8.1, -3.5), c("noir"), collide=False, name="Baie")
        b.box((-1.0, 1.0, -3.62), (1.0, 4.4, -3.5), c("porte"), collide=False, name="Porte")
        b.box((-3.9, h, -3.9), (3.9, h + 0.6, 3.9), c("chemin_ronde"), studs="top", name="Toit")
        for (mx, mz) in ((-3.9, -3.9), (2.4, -3.9), (-3.9, 2.4), (2.4, 2.4)):
            b.box((mx, h + 0.6, mz), (mx + 1.5, h + 2.4, mz + 1.5), c("mur_clair"), name="Merlon")
        top = h + 0.6
        cols = (("drapeau_rouge", "drapeau_blanc"), ("drapeau_vert", "drapeau_blanc"), ("drapeau_bleu", "toile_jaune"),
                ("drapeau_rouge", "toile_jaune"))[drapeau % 4]
        _petit_drapeau(b, 0, top, 0, 5.0, cols)


# ---------------------------------------------------------------------------
# 1) Muraille à porte : entrée (variante 0) et repère final (variante 1)
# ---------------------------------------------------------------------------

def _x_claveaux(xo: float, n: int = 13, alpha: float = 0.3) -> list:
    """Bornes des claveaux : plus étroits aux naissances, plus larges vers la clé (mélange linéaire / cosinus)."""
    xs = []
    for k in range(n + 1):
        u = k / n
        x = xo * (alpha * -math.cos(math.pi * u) + (1 - alpha) * (2 * u - 1))
        xs.append(round(x * 2) / 2)
    xs[0], xs[-1] = -xo, xo
    return xs


def _intrados(xs, xo, hp, crown) -> list:
    """Hauteur de l'intrados de chaque claveau (ellipse évaluée au bord extérieur du claveau, au demi-stud)."""
    ys = []
    n = len(xs) - 1
    for k in range(n):
        xe = max(abs(xs[k]), abs(xs[k + 1])) if k != n // 2 else 0.0
        y = hp + (crown - hp) * math.sqrt(max(0.0, 1 - (xe / xo) ** 2))
        ys.append(round(y * 2) / 2)
    return ys


def _arc(b, xs, ys, z0, y_haut, prof: float = 3.0, hv: float = 6.0):
    """Arc surbaissé à claveaux alternés clairs et foncés, clé lisse (aucun emblème) ; tympans jusqu'à y_haut.
    Face dans le plan z0 (vers -Z) ; l'arc a `prof` d'épaisseur (la lunette dessous reste ouverte)."""
    n = len(xs) - 1
    with b.group("Arc"):
        for k in range(n):
            x0, x1, y = xs[k], xs[k + 1], ys[k]
            if k == n // 2:
                b.box((x0 - 0.3, y - 0.6, z0 - 1.0), (x1 + 0.3, y + hv + 1.6, z0 + prof), c("mur_pale"), name="Cle")
                top = y + hv + 1.6
            else:
                col = c("mur_pale") if k % 2 == 0 else c("mur_fonce")
                b.box((x0, y, z0 - 0.6), (x1, y + hv, z0 + prof), col, name="Claveau")
                top = y + hv
            if top < y_haut - 0.05:
                b.box((x0, top, z0), (x1, y_haut, z0 + prof), c("mur"), name="Tympan")


def _herse(b, xs, ys, xo, z0):
    """Herse de fer relevée dans la lunette de l'arc, à 2 derrière la face : pointes à 47, barreaux montant
    dans les claveaux, deux traverses qui entrent dans les piédroits (|x| ≤ 52,5, au-dessus de 47)."""
    fer, fonte = c("fer"), c("fonte")
    zc = z0 + 2.0

    def intr(x):
        for k in range(len(xs) - 1):
            if xs[k] - 0.4 <= x <= xs[k + 1] + 0.4:
                yield ys[k]

    with b.group("Herse"):
        for x in (-22.5, -15.0, -7.5, 0.0, 7.5, 15.0, 22.5):
            y_top = max(intr(x)) + 1.0
            b.box((x - 0.4, 47.6, zc - 0.4), (x + 0.4, y_top, zc + 0.4), fer, name="Barreau")
            b.box((x - 0.25, 47.0, zc - 0.25), (x + 0.25, 47.6, zc + 0.25), fonte, collide=False, name="Pointe")
        for y in (48.6, 51.6):
            b.box((-(xo + 0.5), y, zc - 0.3), (xo + 0.5, y + 0.7, zc + 0.3), fonte, name="Traverse")


def _vantail(b, s: int, xo: float, z_a: float, z_b: float, hp: float):
    """Vantail de bois clouté (planches, pentures de fer, gros rivets) rabattu dans sa niche (|x| ≥ 52,4)."""
    face = s * (xo + 1.0)
    xa, xb = sorted((face, s * (xo + 2.6)))
    with b.group("Vantail"):
        b.box((xa, 0.2, z_a + 0.2), (xb, hp - 1.8, z_b - 0.2), c("porte"), name="Vantail")
        for t in (1 / 3, 2 / 3):
            z = z_a + (z_b - z_a) * t
            x0, x1 = sorted((face, face - s * 0.15))
            b.box((x0, 0.4, z - 0.15), (x1, hp - 2.0, z + 0.15), c("bois"), collide=False, name="Joint")
        for y in (7.0, 21.5, 36.0):
            x0, x1 = sorted((face, face - s * 0.3))
            b.box((x0, y, z_a + 0.7), (x1, y + 1.6, z_b - 0.7), c("fer"), collide=False, name="Penture")
            for t in (0.12, 0.5, 0.88):
                z = z_a + (z_b - z_a) * t
                x0, x1 = sorted((face - s * 0.3, face - s * 0.6))
                b.box((x0, y + 0.45, z - 0.35), (x1, y + 1.15, z + 0.35), c("fonte"), collide=False, name="Rivet")


def _contrefort(b, x0, x1, z0, saillie, niv, h_haut):
    """Contrefort massif encadrant l'ouverture (face z0 vers -Z) : petit talus propre (1), fût, imposte, cordon,
    chaperon studs. Saillie totale au sol : saillie + 1."""
    p = c("mur_pale")
    b.wedge((x0, 0, z0 - saillie - 1.0), (x1, 5.0, z0 - saillie), c("mur_base"), down="-z", studs="top",
            name="Talus")
    b.box((x0, niv["pil0"], z0 - saillie), (x1, h_haut, z0), c("mur_clair"), name="Contrefort")
    b.box((x0, h_haut, z0 - saillie - 0.4), (x1, h_haut + 1.5, z0), p, studs="top", name="Chaperon")
    b.box((x0, 44.5, z0 - saillie - 0.3), (x1, 46.0, z0 - saillie), p, name="Imposte")
    b.box((x0, niv["cordon"][0], z0 - saillie - 0.3), (x1, niv["cordon"][1], z0 - saillie), p, name="Cordon")


def _merlons_porte(x_min: float, x_max: float, exclus=()) -> list:
    """Centres des merlons d'une muraille à porte : phase commune 3 + 6k (créneaux centrés sur les multiples de 6)."""
    out = []
    k = 0
    while True:
        x = 3.0 + 6.0 * k
        if x + 1.5 > x_max:
            break
        if x - 1.5 >= x_min and not any(x + 1.6 > e0 and x - 1.6 < e1 for e0, e1 in exclus):
            out += [x, -x]
        k += 1
    return sorted(out)


def _pilastres_porte(x_first: float, x_max: float, larg: float, pas: float = 13.5) -> list:
    """Positions (côté droit puis miroir) des pilastres d'une muraille à porte, hors des tours d'angle."""
    out = []
    x = x_first
    while x + larg / 2 < x_max - 1.0:
        if not (x + larg / 2 > TOUR0 - 0.5 and x - larg / 2 < TOUR1 + 0.5):
            out += [x, -x]
        x += pas
    return sorted(out)


def _face_porte(b, rng, *, W2, xo, z0, niv, exterieur, abords, pil_first, y_arc, coupe_parapet=0.0,
                masque_centre=0.0, bandes=(1, 3), pierres=(2, 3), fentes=4, lierres=0, gargouilles=1, grappe=3,
                creneaux_ville=False):
    """Parement d'une grande face de muraille à porte (face z0 vers -Z) : talus, pilastres, cordon, corniche,
    parapet (crénelé côté extérieur ; côté ville aussi si `creneaux_ville`, jusqu'aux tours d'angle), assises et
    pierres pixel. `abords` = demi-largeur occupée par les contreforts ou les tours de porte de part et d'autre
    de l'ouverture (|x| < abords sans pilastre)."""
    larg, sail = (4.0, 1.5) if exterieur else (3.0, 1.0)
    pil = _pilastres_porte(pil_first, W2, larg)
    _talus(b, -W2, W2, z0, niv, coupes=((-xo, xo),))
    _pilastres(b, pil, z0, larg, sail, niv, chapiteau=True)
    _bandeau(b, -W2, W2, z0, *niv["cordon"], 0.6, coupes=((-xo - 0.5, xo + 0.5),), name="Cordon")
    _bandeau(b, -W2, W2, z0, *niv["corniche"], 1.2, name="Corniche")
    coupes_par = ((-coupe_parapet, coupe_parapet),) if coupe_parapet else ()
    exclus = [(-coupe_parapet, coupe_parapet)] if coupe_parapet else []
    exclus += [(TOUR0, TOUR1), (-TOUR1, -TOUR0)]
    crenele = exterieur or creneaux_ville
    if exterieur:
        merl = _merlons_porte(0.0, W2, exclus)
    elif creneaux_ville:
        merl = _merlons_porte(0.0, TOUR0, exclus + [(-abords - 2.0, -xo), (xo, abords + 2.0)])
    else:
        merl = ()
    _parapet(b, -W2, W2, z0, niv, crenele=crenele, merlons=merl, coupes=coupes_par)
    # baies visibles : de l'abord de la porte à la tour d'angle, au-delà de la tour, et au-dessus de l'arc
    seps = [(x - larg / 2, x + larg / 2) for x in pil]
    seps += [(-abords, abords), (TOUR0, TOUR1), (-TOUR1, -TOUR0)]
    y0, y1 = niv["deco"]
    baies = _baies(-W2, W2, seps, y0, y1)
    baies += _baies(-xo, xo, [(-masque_centre, masque_centre)] if masque_centre else [], y_arc + 0.5, y1, ext=0.0)
    occupe = []
    loin = [bb for bb in baies if min(abs(bb[0]), abs(bb[1])) >= TOUR1 - 0.1]
    pres = [bb for bb in baies if bb not in loin]
    _meurtrieres(b, rng, [bb for bb in pres if bb[4] < 20], z0, fentes, occupe, niv)
    for k in range(gargouilles):
        cand = [bb for bb in pres if bb[1] - bb[0] > 7 and bb[4] < 20]
        if cand:
            x0, x1 = cand[int(rng.integers(0, len(cand)))][:2]
            _gargouille(b, round((x0 + x1) / 2) + 0.5, z0, niv, occupe)
    for k in range(lierres):
        cand = [bb for bb in pres if bb[1] - bb[0] > 7 and bb[4] < 20]
        if cand:
            x0, x1 = cand[int(rng.integers(0, len(cand)))][:2]
            _lierre(b, rng, round((x0 + x1) / 2), z0, occupe, h=float(rng.choice((8.0, 12.0, 16.0))))
    _appareil(b, rng, pres, z0, niv, n_bandes=bandes, n_pierres=pierres, occupe=occupe, grappe=grappe)
    _appareil(b, rng, loin, z0, niv, n_bandes=(1, 1), n_pierres=(0, 1), occupe=occupe)
    return pil


def _tour_porte(b, rng, s: int, z0: float, niv, h_corps: float = 104.0, drapeau: int = 0):
    """Tour carrée de 16 × 16 flanquant la porte finale (centre |x| = 62, avance de 6 sur la face z0, talus de 2 :
    8 au sol) : talus, chaînes d'angle, cordons, meurtrières, couronnement crénelé jusqu'à 125, tambour et haut
    toit d'ardoise en gradins (≈ 146), drapeau, lanterne et bannière unie. Rien sous |x| = 52."""
    xc = s * 62.0
    xi, xe = s * 54.0, s * 70.0           # face intérieure (côté porte) et extérieure
    za, zr = z0 - 6.0, z0 + 10.0          # avance de 6 (+ talus de 2 : 8 au sol) ; 16 de profondeur
    X = lambda a, bb: tuple(sorted((a, bb)))   # noqa: E731
    with b.group(f"TourPorte{'G' if s < 0 else 'D'}"):
        x0, x1 = X(xi, xe)
        b.box((x0, 0, za), (x1, h_corps, zr), c("mur"), name="Corps")
        # talus : devant et côté extérieur (débord 3), côté porte réduit à 2 (|x| ≥ 52)
        x0, x1 = X(s * 52.0, s * 73.0)
        b.wedge((x0, 0, za - 2.0), (x1, 12.0, za), c("mur_base"), down="-z", studs="top", name="Talus")
        x0, x1 = X(xe, xe + s * TALUS)
        b.wedge((x0, 0, za - 2.0), (x1, 12.0, z0), c("mur_base"), down="+x" if s > 0 else "-x", studs="top", name="Talus")
        x0, x1 = X(s * 52.0, xi)
        b.wedge((x0, 0, za), (x1, 8.0, z0), c("mur_base"), down="-x" if s > 0 else "+x", studs="top", name="Talus")
        # chaînes d'angle (4 × 4, saillie 1,5) et nervure centrale
        for xa_ in (s * 52.5, s * 67.5):
            x0, x1 = X(xa_, xa_ + s * 4.0)
            b.box((x0, 8.0, za - 1.5), (x1, h_corps - 5.0, za + 2.5), c("mur_clair"), name="Chaine")
        x0, x1 = X(xc - 1.5, xc + 1.5)
        b.box((x0, 10.0, za - 1.0), (x1, h_corps - 5.0, za + 0.5), c("mur_clair"), name="Pilastre")
        # cordons alignés sur la muraille, corniche haute
        for (y0, y1), sl in ((niv["cordon"], 0.6), (niv["corniche"], 1.2)):
            x0, x1 = X(xi - s * sl, xe + s * sl)
            b.box((x0, y0, za - sl), (x1, y1, z0), c("mur_pale"), name="Cordon")
        x0, x1 = X(xi - s * 1.2, xe + s * 1.2)
        b.box((x0, h_corps - 5.0, za - 1.2), (x1, h_corps - 3.5, zr + 1.2), c("mur_pale"), name="Corniche")
        # meurtrières
        for (x, y) in ((xc - s * 4.5, 24.0), (xc + s * 4.5, 56.0), (xc - s * 4.5, 90.0)):
            x0, x1 = X(x - 0.5, x + 0.5)
            b.box((x0, y, za - S_FENTE), (x1, y + 4.0, za + 0.4), c("mur_joint"), collide=False, name="Meurtriere")
        for (z, y) in ((za + 3.5, 62.0), (za + 3.5, 90.0)):
            x0, x1 = X(xe, xe + s * S_FENTE)
            b.box((x0, y, z - 0.5), (x1, y + 4.0, z + 0.5), c("mur_joint"), collide=False, name="Meurtriere")
        # couronnement : parapet, merlons, plateforme, toit en gradins
        y_p = h_corps
        x0, x1 = X(xi, xe)
        for (za_, zb_) in ((za, za + 1), (zr - 1, zr)):
            b.box((x0, y_p, za_), (x1, y_p + 3.5, zb_), c("mur"), name="Parapet")
        for xx in (xi, xe - s * 1.0):
            xa_, xb_ = X(xx, xx + s * 1.0)
            b.box((xa_, y_p, za + 1), (xb_, y_p + 3.5, zr - 1), c("mur"), name="Parapet")
        for dx in (-6.5, 0.0, 6.5):
            for zz in (za, zr - 1):
                xa_, xb_ = X(xc + dx - 1.5, xc + dx + 1.5)
                b.box((xa_, y_p + 3.5, zz), (xb_, y_p + 7.5, zz + 1), c("mur_clair"), name="Merlon")
        for zz in ((za + zr) / 2,):
            for xx in (xi, xe - s * 1.0):
                xa_, xb_ = X(xx, xx + s * 1.0)
                b.box((xa_, y_p + 3.5, zz - 1.5), (xb_, y_p + 7.5, zz + 1.5), c("mur_clair"), name="Merlon")
        zm = (za + zr) / 2
        x0, x1 = X(xi + s * 1.0, xe - s * 1.0)
        b.box((x0, y_p, za + 1), (x1, y_p + 0.5, zr - 1), c("chemin_ronde"), studs="top", name="Plateforme")
        with b.at((xc, y_p + 0.5, zm), yaw=90 if s < 0 else -90):
            mobilier.drapeau(b, hauteur=9, variant=drapeau)
        # bannière et lanterne sur la face avant
        _banniere(b, xc, 78.0, za - 1.0, long_=14.0, larg=3.6, cols=(("drapeau_rouge", "toile_creme"),
                                                                       ("drapeau_vert", "toile_creme"))[drapeau % 2],
                  saillie=1.0)
        with b.at((xc + s * 4.5, 18.0, za)):
            mobilier.lanterne_murale(b, variant=0)


def porte_colossale(b, variant=0, largeur=270, hauteur=90, epaisseur=24, ouverture=104, h_passage=46):
    """Muraille colossale percée d'une porte monumentale.

    variant 0 : muraille extérieure (entrée de la zone), vue d'abord de la prairie : face avant (-Z) extérieure,
                crénelée, contreforts à bannières et corps de garde à échauguettes au-dessus du tunnel ; revers (+Z)
                côté ville, crénelé aussi, avec escalier de bois, monte-charge, lanternes et bannières ; sur le
                chemin de ronde : 4 canons tournés vers la prairie, 2 grues penchées sur la ville, 2 tourelles.
    variant 1 : muraille intérieure (repère final, 470 de large) : face avant (-Z) vers la ville, porte fortifiée
                entre deux tours carrées (couronnement à 125, haut toit d'ardoise), corps de garde à mâchicoulis et
                baie éclairée, bannières ; revers (+Z) extérieur crénelé ; 6 canons vers l'extérieur, 2 grues,
                2 tourelles.
    variant 2 : comme 0, sans le toit du corps de garde.
    Tunnel : |x| < ouverture/2 libre de y = 0 à h_passage sur toute l'épaisseur ; plafond à h_passage + 2,
    doubleaux à h_passage ; vantaux dans des niches (|x| ≥ 52,4) ; herse relevée (pointes à 47)."""
    rng = b.rng
    v = variant % 3
    final = v == 1
    W2, H, e = largeur / 2, float(hauteur), float(epaisseur)
    xo, hp = ouverture / 2, float(h_passage)
    niv = _niv(H)
    zf, zb = -e / 2, e / 2
    crown = hp + 10.0                    # sommet de l'intrados (clé)
    y_arc = hp + 18.0                    # dessus des tympans = bas du corps de garde
    xn = xo + 2.6                        # fond des niches des vantaux
    yn = hp - 1.4                        # linteau des niches
    ld = min(22.0, e - 4.0)
    zn0, zn1 = zf + 1.5, zf + 1.5 + ld
    xs = _x_claveaux(xo)
    ys = _intrados(xs, xo, hp, crown)
    gh = 20.0                            # demi-largeur du corps de garde

    # -- masses ---------------------------------------------------------------
    with b.group("Masses"):
        for s in (-1, 1):
            b.box((_sym(s, xn, W2)[0], 0, zf), (_sym(s, xn, W2)[1], yn, zb), c("mur"), name="Massif")
            b.box((_sym(s, xo, W2)[0], yn, zf), (_sym(s, xo, W2)[1], niv["dalle"], zb), c("mur"), name="Massif")
            x0, x1 = _sym(s, xo, xn)
            b.box((x0, 0, zf), (x1, yn, zn0), c("mur"), name="Piedroit")
            b.box((x0, 0, zn1), (x1, yn, zb), c("mur"), name="Piedroit")
        b.box((-xo, hp + 2.0, zf + 3.0), (xo, y_arc, zb - 3.0), c("mur_ombre"), name="Voute")
        b.box((-xo, y_arc, zf), (xo, niv["dalle"], zb), c("mur"), name="Massif")
        b.box((-W2, niv["dalle"], zf + 1), (W2, niv["chemin"], zb - 1), c("chemin_ronde"), studs="top", name="CheminRonde")

    # -- tunnel : doubleaux, vantaux, herse, arcs des deux faces ---------------
    with b.group("Tunnel"):
        for k in range(3):
            z = zf + 3.0 + (e - 6.0) * (k + 1) / 4
            b.box((-xo, hp, z - 1.0), (xo, hp + 2.0, z + 1.0), c("mur_fonce"), name="Doubleau")
        for s in (-1, 1):
            _vantail(b, s, xo, zn0, zn1, hp)
    _arc(b, xs, ys, zf, y_arc)
    _herse(b, xs, ys, xo, zf)
    with b.at((0, 0, 0), yaw=180):
        _arc(b, xs, ys, -zb, y_arc)

    # -- faces ----------------------------------------------------------------
    if not final:
        # face avant extérieure : contreforts de 8 (saillie 3) de part et d'autre de l'ouverture
        with b.group("FaceExterieure"):
            for s in (-1, 1):
                x0, x1 = _sym(s, xo, xo + 8.0)
                _contrefort(b, x0, x1, zf, 3.0, niv, niv["par_int"])
                with b.at((s * (xo + 4.0), 30.0, zf - 3.0)):
                    mobilier.lanterne_murale(b, variant=0)
                _banniere(b, s * (xo + 4.0), 78.0, zf - 3.0, long_=24.0, larg=4.6,
                          cols=(("drapeau_rouge", "toile_creme"), ("drapeau_vert", "toile_creme"))[s > 0], saillie=0.6)
            _face_porte(b, rng, W2=W2, xo=xo, z0=zf, niv=niv, exterieur=True, abords=xo + 8.0,
                        pil_first=xo + 8.0 + 9.5, y_arc=y_arc, coupe_parapet=gh, masque_centre=gh,
                        bandes=(2, 3), pierres=(2, 3), fentes=4, lierres=0, gargouilles=1, grappe=2)
        # revers côté ville
        with b.at((0, 0, 0), yaw=180, group="FaceVille"):
            for s in (-1, 1):
                x0, x1 = _sym(s, xo, xo + 6.0)
                _contrefort(b, x0, x1, -zb, 2.0, niv, niv["corniche"][1])
                with b.at((s * (xo + 3.0), 30.0, -zb - 2.0)):
                    mobilier.lanterne_murale(b, variant=1)
                _banniere(b, s * 32.0, niv["par_int"], -zb, long_=20.0, larg=4.0, cols=("drapeau_rouge", "toile_creme"))
            _face_porte(b, rng, W2=W2, xo=xo, z0=-zb, niv=niv, exterieur=False, abords=xo + 6.0,
                        pil_first=xo + 6.0 + 11.5, y_arc=y_arc, bandes=(2, 3), pierres=(1, 2), fentes=2,
                        lierres=2, gargouilles=1, grappe=2, creneaux_ville=True)
        # escalier de bois et monte-charge contre le revers (≤ 8 de profondeur)
        with b.at((90.0, 0, zb + 4.0), yaw=180, group="Escalier"):
            escalier_mur(b, variant=1, hauteur=H, longueur=40)
        with b.at((-112.0, 0, zb + 4.0), yaw=180, group="MonteCharge"):
            monte_charge(b, variant=0, hauteur=H, profondeur=8.0)
    else:
        # face avant vers la ville : tours de porte de 16 × 16 au lieu des contreforts
        with b.group("FaceVille"):
            for s in (-1, 1):
                _tour_porte(b, rng, s, zf, niv, drapeau=(0, 1)[s > 0])
                # longues bannières unies sur la courtine, entre le corps de garde et les tours
                _banniere(b, s * 36.0, niv["par_int"], zf, long_=22.0, larg=4.4,
                          cols=(("drapeau_vert", "toile_creme"), ("drapeau_rouge", "toile_creme"))[s > 0])
                _banniere(b, s * 109.25, niv["par_int"], zf, long_=18.0, larg=4.0,
                          cols=(("drapeau_bleu", "toile_jaune"), ("drapeau_bleu", "toile_jaune"))[s > 0])
            _face_porte(b, rng, W2=W2, xo=xo, z0=zf, niv=niv, exterieur=False, abords=70.0,
                        pil_first=75.5, y_arc=y_arc, masque_centre=gh, bandes=(2, 3), pierres=(2, 3), fentes=4,
                        lierres=2, gargouilles=2, coupe_parapet=gh, creneaux_ville=True)
        with b.at((0, 0, 0), yaw=180, group="FaceExterieure"):
            for s in (-1, 1):
                x0, x1 = _sym(s, xo, xo + 8.0)
                _contrefort(b, x0, x1, -zb, 3.0, niv, niv["par_int"])
                with b.at((s * (xo + 4.0), 30.0, -zb - 3.0)):
                    mobilier.lanterne_murale(b, variant=1)
            _face_porte(b, rng, W2=W2, xo=xo, z0=-zb, niv=niv, exterieur=True, abords=xo + 8.0,
                        pil_first=xo + 8.0 + 9.5, y_arc=y_arc, bandes=(1, 2), pierres=(1, 2), fentes=3,
                        lierres=0, gargouilles=0)

    # -- corps de garde ---------------------------------------------------------
    with b.group("CorpsDeGarde"):
        _couronne_porte(b, zf, niv, gh, y_arc)

    # -- chemin de ronde : canons vers l'extérieur, grues au-dessus de la ville, tourelles --------------------
    yc = niv["chemin"]
    with b.group("CheminRonde"):
        if not final:
            z_ext, z_ville, sens_ext = zf + 1.0, zb - 1.0, -1
            canons, grues, tourelles = (72.0, 108.0), (87.0,), (99.5,)
        else:
            z_ext, z_ville, sens_ext = zb - 1.0, zf + 1.0, 1
            canons, grues, tourelles = (78.0, 108.0, 204.0), (95.0,), (186.0,)
        for s in (-1, 1):
            for x in canons:
                with b.at((s * x, yc, z_ext), yaw=0 if sens_ext < 0 else 180):
                    _canon_rail(b, -1)
            for i, x in enumerate(grues):
                with b.at((s * x, yc, z_ville), yaw=180 if sens_ext < 0 else 0):
                    _grue(b, charge=i + (s > 0), y_ch=-3.5 if (not final and s > 0) else -9.0)
            for i, x in enumerate(tourelles):
                with b.at((s * x, yc, (zf + zb) / 2), yaw=0 if not final else 180):
                    _tourelle(b, rng, drapeau=i + (s > 0) + 2 * final)
    h_tot = 116.0 if final else 100.0
    return {"emprise": (largeur, epaisseur), "hauteur": h_tot}


def _couronne_porte(b, zf, niv, gh, y_arc, canons=True):
    """Au-dessus du tunnel : la muraille reste lisse et nervurée jusqu'au chemin de ronde (sobre, pas de donjon).
    Nervures de 4 (saillie 1,5) de y_arc à la corniche, parapet crénelé continu, plateforme de guet en bois
    en encorbellement avec deux canons et un drapeau."""
    for x in (-15.0, -5.0, 5.0, 15.0):
        b.box((x - 2.0, y_arc, zf - 1.5), (x + 2.0, niv["chap"][0], zf), c("mur_fonce"), name="Pilastre")
        b.box((x - 2.2, niv["chap"][0], zf - 1.9), (x + 2.2, niv["chap"][1], zf), c("mur_pale"), name="Chapiteau")
    b.box((-gh, niv["dalle"], zf), (gh, niv["par_ext"], zf + 1), c("mur"), name="Parapet")
    for x in (-21.0, -15.0, -9.0, -3.0, 3.0, 9.0, 15.0, 21.0):
        b.box((x - 1.5, niv["par_ext"], zf), (x + 1.5, niv["merlon"], zf + 1), c("mur_clair"), name="Merlon")
    # plateforme de guet : plancher de bois sur aisseliers, garde-corps, deux canons tournés vers l'avant
    bois, fonce = c("bois_echafaud"), c("bois")
    zp = zf - 5.0
    y = niv["corniche"][1]
    for x in (-9.0, -3.0, 3.0, 9.0):
        b.wedge_under((x - 0.5, y - 5.0, zp + 0.5), (x + 0.5, y - 0.6, zf - 1.2), fonce, down="-z", name="Aisselier")
    b.box((-10.0, y - 0.6, zp), (10.0, y, zf - 1.2), bois, studs="top", name="Plancher")
    b.box((-10.0, y, zp), (10.0, y + 2.6, zp + 0.4), fonce, collide=False, name="GardeCorps")
    if canons:
        for x in (-5.0, 5.0):
            with b.at((x, y, zp + 3.0)):
                b.box((-1.2, 0, -1.0), (1.2, 1.0, 1.0), c("bois"), name="Affut")
                b.cyl((0, 1.6, -0.5), 0.6, 4.0, c("fonte"),
                      axis="z", collide=False, name="Canon")


# ---------------------------------------------------------------------------
# 2) Segment de rempart latéral
# ---------------------------------------------------------------------------

def mur_colossal(b, variant=0, longueur=71, hauteur=90, epaisseur=20, canons=1, guet=False):
    """Segment de rempart colossal (bout à bout : x local exactement dans [-L/2, L/2]).
    Avant (-Z) = face intérieure, vers la ville ; arrière (+Z) = face extérieure, vers les champs.
    variant 0 : lisse, deux lanternes ; 1 : hourd de bois couvert de tuiles en surplomb sur la face ville ;
    2 : brèche réparée en pierres claires et échafaudage ; 3 : poterne au pied (porte cintrée, lanterne, banc).
    `canons` canons sur rails tirent vers +Z ; `guet` : tourelle de guet au milieu du chemin de ronde."""
    rng = b.rng
    v = variant % 4
    L, H, e = float(longueur), float(hauteur), float(epaisseur)
    niv = _niv(H)
    xa, xb = -L / 2, L / 2
    zf, zb = -e / 2, e / 2
    pil = [xa + L / 12 + k * L / 6 for k in range(6)]
    n_m = max(1, round(L / 6))
    pas = L / n_m
    merlons = [xa + pas * (k + 0.5) for k in range(n_m)]
    with b.group("Rempart"):
        b.box((xa, 0, zf), (xb, niv["dalle"], zb), c("mur"), name="Noyau")
        b.box((xa, niv["dalle"], zf + 1), (xb, niv["chemin"], zb - 1), c("chemin_ronde"), studs="top", name="CheminRonde")

    # -- face ville (avant) ---------------------------------------------------
    with b.group("FaceVille"):
        coupes_talus = ((-3.0, 3.0),) if v == 3 else ()
        _talus(b, xa, xb, zf, niv, coupes=coupes_talus)
        _pilastres(b, pil, zf, 3.0, 1.0, niv, chapiteau=True)
        _bandeau(b, xa, xb, zf, *niv["cordon"], 0.6, name="Cordon")
        _bandeau(b, xa, xb, zf, *niv["corniche"], 1.2, name="Corniche")
        _parapet(b, xa, xb, zf, niv, crenele=False)
        y0, y1 = niv["deco"]
        baies = _baies(xa, xb, [(x - 1.5, x + 1.5) for x in pil], y0, y1)
        occupe = []
        # éléments propres à chaque variante (avant les pierres, qui les évitent)
        if v == 1:
            occupe.append((-12.0, 12.0, 70.0, 90.0))
            _hourd(b, zf, niv)
        elif v == 2:
            occupe.append((-14.0, 2.0, 11.0, 60.0))
            _breche(b, rng, zf, niv)
        elif v == 3:
            occupe.append((-4.0, 4.0, 0.0, 13.0))
            _poterne(b, rng, zf, niv)
        # gargouille et coulure, lanternes, lierre
        pleines = baies[1:-1]
        bx = pleines[int(rng.integers(0, len(pleines)))]
        _gargouille(b, round((bx[0] + bx[1]) / 2) + 0.5, zf, niv, occupe, y_bas=float(rng.choice((49.6, 55.6, 61.6))))
        if v != 3:
            for x in (-L / 4 - 3.0, L / 4 + 3.0):
                _lanterne_compacte(b, x, 15.0, zf)
                occupe.append((x - 1.0, x + 1.0, 12.0, 16.0))
        if v in (0, 2):
            bl = pleines[int(rng.integers(0, len(pleines)))]
            _lierre(b, rng, round((bl[0] + bl[1]) / 2), zf, occupe, h=float(rng.choice((9.0, 13.0))))
        nb = (2, 2) if v in (0, 3) else (1, 1)
        _appareil(b, rng, baies, zf, niv, n_bandes=nb, n_pierres=(1, 1), occupe=occupe)

    # -- face champs (arrière, repère tourné) -----------------------------------
    with b.at((0, 0, 0), yaw=180, group="FaceChamps"):
        _talus(b, -xb, -xa, -zb, niv)
        _pilastres(b, [-x for x in pil], -zb, 4.0, 1.5, niv, chapiteau=False)
        _bandeau(b, -xb, -xa, -zb, *niv["cordon"], 0.6, name="Cordon")
        _bandeau(b, -xb, -xa, -zb, *niv["corniche"], 1.2, name="Corniche")
        _parapet(b, -xb, -xa, -zb, niv, crenele=True, merlons=[-m for m in merlons])

    # -- chemin de ronde ----------------------------------------------------------
    with b.group("CheminRonde"):
        xs_c = [(-L / 4) if v % 2 == 0 else (L / 4)] if canons == 1 else [-L / 4, L / 4][:max(0, canons)]
        for x in xs_c:
            with b.at((x, niv["chemin"], zb - 1.0), yaw=180):
                _canon_rail(b, -1)
        if guet:
            with b.at((0, niv["chemin"], 0)):
                _tourelle(b, rng, drapeau=v)
    return {"emprise": (L, e + 2 * TALUS), "hauteur": H + (17.0 if guet else 0.0)}


def _hourd(b, zf, niv, x0=-10.0, x1=10.0):
    """Hourd : galerie de bois couverte de tuiles brunes, en surplomb sur la face ville entre 78 et 86."""
    bois, fonce = c("bois"), c("colombage")
    zp = zf - 4.0
    with b.group("Hourd"):
        for x in (x0 + 1.0, -3.4, 3.4, x1 - 1.0):
            b.wedge_under((x - 0.5, 73.0, zp + 0.4), (x + 0.5, 77.6, zf), fonce, down="-z", name="Aisselier")
        b.box((x0, 77.6, zp), (x1, 78.4, zf), fonce, studs="top", name="Plancher")
        b.box((x0, 78.4, zp), (x1, 85.6, zp + 0.6), bois, name="Bardage")
        for x in (x0, x1 - 0.6):
            b.box((x, 78.4, zp + 0.6), (x + 0.6, 85.6, zf), bois, name="Bardage")
        for x in (x0 + 0.2, -3.4, 3.4, x1 - 0.8):
            b.box((x - 0.0, 78.4, zp - 0.15), (x + 0.6, 85.6, zp), fonce, collide=False, name="Poteau")
        for x in (-6.7, 0.0, 6.7):
            b.box((x - 0.6, 81.0, zp - 0.12), (x + 0.6, 83.6, zp), c("noir"), collide=False, name="Archere")
        b.box((x0 - 0.2, 85.6, zp - 0.2), (x1 + 0.2, 85.9, zf + 0.6), fonce, name="Sabliere")
        b.wedge((x0 - 0.6, 86.0, zp - 1.0), (x1 + 0.6, 89.2, zf + 1.0), c("tuile_brune"), down="-z", studs="top",
                name="Toit")
        b.box((x0 - 0.6, 89.2, zf), (x1 + 0.6, 89.6, zf + 1.4), c("tuile_fonce"), name="Faitage")


def _breche(b, rng, zf, niv):
    """Brèche réparée : plaque de pierres neuves plus claires et échafaudage de perches (6) et de planches (2)."""
    perche = c("bois_echafaud")
    with b.group("Breche"):
        blocs = ((-12.0, -2.0, 14.0, 26.0, "mur_pale", 0.35), (-10.0, 1.0, 26.0, 40.0, "mur_clair", 0.45),
                 (-13.0, -5.0, 41.5, 52.0, "mur_pale", 0.35), (-8.0, 0.0, 52.0, 58.0, "mur_clair", 0.25),
                 (-4.0, 1.0, 16.0, 22.0, "mur_fonce", 0.55), (-12.0, -8.0, 30.0, 34.0, "mur_fonce", 0.6))
        for (x0, x1, y0, y1, col, sl) in blocs:
            b.box((x0, y0, zf - sl), (x1, y1, zf), c(col), collide=False, name="PierreNeuve")
        for x in (-14.0, -6.0, 2.0):
            for z in (zf - 4.5, zf - 1.2):
                b.box((x - 0.3, 0, z - 0.3), (x + 0.3, 50.0, z + 0.3), perche, name="Perche")
        for y in (24.0, 42.0):
            b.box((-14.6, y, zf - 5.0), (2.6, y + 0.5, zf - 0.7), c("bois_clair"), studs="top", name="Planche")
        b.box((-15.0, 0, zf - 7.5), (-11.0, 1.6, zf - 5.0), c("mur_pale"), studs="top", name="Moellons")


def _poterne(b, rng, zf, niv):
    """Poterne au pied du mur : arc clair, porte de bois cintrée à pentures, lanterne, banc et caisses."""
    with b.group("Poterne"):
        b.box((-3.0, 0, zf - 1.2), (3.0, 1.0, zf), c("mur_base"), studs="top", name="Seuil")
        b.box((-3.4, 1.0, zf - 0.5), (3.4, 10.2, zf), c("mur_pale"), name="Encadrement")
        b.box((-2.2, 1.0, zf - 0.7), (2.2, 7.6, zf - 0.5), c("porte"), name="Porte")
        b.box((-1.4, 7.6, zf - 0.7), (1.4, 8.6, zf - 0.5), c("porte"), name="Porte")
        for y in (2.6, 5.6):
            b.box((-2.2, y, zf - 0.85), (1.2, y + 0.4, zf - 0.7), c("fer"), collide=False, name="Penture")
        b.box((-0.6, 8.9, zf - 0.9), (0.6, 10.2, zf - 0.5), c("mur_fonce"), name="Cle")
        _lanterne_compacte(b, 0.0, 12.6, zf)
        with b.at((9.0, 0, zf - 4.0)):
            for x in (-2.4, 2.4):
                b.box((x - 0.3, 0, -0.6), (x + 0.3, 1.6, 0.6), c("bois"), name="Pied")
            b.box((-3.0, 1.6, -0.8), (3.0, 2.0, 0.8), c("bois_clair"), studs="top", name="Banc")
        with b.at((-8.0, 0, zf - 4.0)):
            b.boxc((0, 1.1, 0), (2.2, 2.2, 2.2), c("bois_clair"), yaw=8, studs="top", name="Caisse")
            b.boxc((2.3, 0.9, 0.4), (1.8, 1.8, 1.8), c("bois_moyen"), yaw=-6, studs="top", name="Caisse")


# ---------------------------------------------------------------------------
# 3) Tour d'angle
# ---------------------------------------------------------------------------

def tour_angle(b, variant=0, cote=32, hauteur=112):
    """Bastion carré des angles (cote × cote) : talus 0 → 12, chaînes d'angle 4 × 4, nervures, cordons à 40 et 80
    alignés sur les murailles, corniche haute, plateforme crénelée (studs).
    variant 0 : guérite à toit d'ardoise et drapeau ; 1 : plateforme à deux canons sur rails (vers -Z) ;
    2 : hourd de bois sur les quatre faces et toit en pavillon ; 3 : grand mât à drapeau et beffroi d'alarme."""
    rng = b.rng
    v = variant % 4
    d = cote / 2
    H = float(hauteur)
    niv = _niv(90.0)
    y_cor = H - 8.0           # corniche haute
    y_pf = H - 6.5            # dessus du noyau
    with b.group("Tour"):
        b.box((-d, 0, -d), (d, y_pf, d), c("mur_fonce"), name="Noyau")      # bastion plus sombre que les courtines
        # talus sur les quatre faces (débord 3, hauteur 12)
        b.wedge((-d - TALUS, 0, -d - TALUS), (d + TALUS, 12.0, -d), c("mur_base"), down="-z", studs="top", name="Talus")
        b.wedge((-d - TALUS, 0, d), (d + TALUS, 12.0, d + TALUS), c("mur_base"), down="+z", studs="top", name="Talus")
        b.wedge((-d - TALUS, 0, -d), (-d, 12.0, d), c("mur_base"), down="-x", studs="top", name="Talus")
        b.wedge((d, 0, -d), (d + TALUS, 12.0, d), c("mur_base"), down="+x", studs="top", name="Talus")
        # chaînes d'angle 4 × 4 (saillie 1,5 sur chaque face) et nervure au milieu de chaque face
        for sx in (-1, 1):
            for sz in (-1, 1):
                x0, x1 = sorted((sx * (d - 2.5), sx * (d + 1.5)))
                z0, z1 = sorted((sz * (d - 2.5), sz * (d + 1.5)))
                b.box((x0, 8.0, z0), (x1, y_cor, z1), c("mur_pale"), name="Chaine")
        for yaw in (0, 90, 180, 270):
            with b.at((0, 0, 0), yaw=yaw):
                b.box((-1.5, 10.0, -d - 1.0), (1.5, y_cor, -d), c("mur_clair"), name="Pilastre")
        # cordons à 40 et 80 (anneaux d'une pièce), corniche haute
        for (y0, y1), sl in ((niv["cordon"], 0.6), (niv["corniche"], 1.2), ((y_cor, y_cor + 1.4), 1.2)):
            b.box((-d - sl, y0, -d - sl), (d + sl, y1, d + sl), c("mur_pale"), name="Cordon")
        for yaw in (0, 90, 180, 270):      # encorbellement sous la corniche haute (ombre portée nette)
            with b.at((0, 0, 0), yaw=yaw):
                b.wedge_under((-d, y_cor - 3.0, -d - 1.0), (d, y_cor, -d), c("mur_ombre"), down="-z", name="Encorbellement")
        # assises, pierres et meurtrières sur les quatre faces
        for i, yaw in enumerate((0, 90, 180, 270)):
            with b.at((0, 0, 0), yaw=yaw):
                occupe = []
                baies = [(-d + 2.5, -1.5, 0.4, 0.4, 13.0, 78.0), (1.5, d - 2.5, 0.4, 0.4, 13.0, 78.0),
                         (-d + 2.5, -1.5, 0.4, 0.4, 83.0, y_cor - 1.0), (1.5, d - 2.5, 0.4, 0.4, 83.0, y_cor - 1.0)]
                for (x, y) in (((-7.0, 24.0), (7.0, 58.0)), ((7.0, 30.0), (-7.0, 92.0)))[i % 2]:
                    b.box((x - 0.5, y, -d - S_FENTE), (x + 0.5, y + 4.0, -d + 0.4), c("mur_joint"), collide=False,
                          name="Meurtriere")
                    occupe.append((x - 1.0, x + 1.0, y - 0.5, y + 4.5))
                if v != 1:
                    _appareil(b, rng, baies, -d, niv, n_bandes=(1, 1), n_pierres=(1, 1) if v in (0, 2) else (0, 0),
                              occupe=occupe)
                else:
                    _appareil(b, rng, baies[:1], -d, niv, n_bandes=(1, 1), n_pierres=(0, 0), occupe=occupe)
        # couronnement
        y_p = y_pf
        if v != 2:
            b.box((-d + 1, y_p, -d + 1), (d - 1, y_p + 0.5, d - 1), c("chemin_ronde"), studs="top", name="Plateforme")
            for yaw in (0, 90, 180, 270):
                with b.at((0, 0, 0), yaw=yaw):
                    b.box((-d, y_p, -d), (d - 1, H - 4.0, -d + 1), c("mur_fonce"), name="Parapet")
                    for x in (-d + 1.5, -7.5, 0.0, 7.5):
                        b.box((x - 1.5, H - 4.0, -d), (x + 1.5, H, -d + 1), c("mur_clair"), name="Merlon")
    if v == 0:
        with b.group("Guerite"):
            y = y_p + 0.5
            b.box((-6.0, y, -6.0), (6.0, y + 8.0, 6.0), c("mur_clair"), name="Guerite")
            b.box((-1.2, y, -6.12), (1.2, y + 4.6, -6.0), c("porte"), collide=False, name="Porte")
            for yaw in (90, 180, 270):
                with b.at((0, 0, 0), yaw=yaw):
                    b.box((-1.4, y + 3.4, -6.12), (1.4, y + 6.2, -6.0), c("noir"), collide=False, name="Fenetre")
            top = _toit_gradins(b, 0, y + 8.0, 0, 14.0, 14.0, 6, 2.2, 1.1, name="Toit")
            _petit_drapeau(b, 0.0, top, 0.0, 7.0, ("drapeau_rouge", "drapeau_blanc"))
    elif v == 1:
        for x in (-11.0, 11.0):
            with b.at((x, y_p + 0.5, -d + 1.0)):
                _canon_rail(b, -1)
        with b.group("Guerite"):
            y = y_p + 0.5
            b.box((-3.0, y, 7.0), (3.0, y + 6.0, 13.0), c("bois_moyen"), name="Guerite")
            top = _toit_gradins(b, 0, y + 6.0, 10.0, 7.6, 7.6, 3, 1.6, 1.3, name="Toit")
        _petit_drapeau(b, 0.0, top, 10.0, 7.0, ("drapeau_vert", "drapeau_blanc"))
    elif v == 2:
        with b.group("Hourd"):
            y = y_p
            b.box((-d - 1.5, y, -d - 1.5), (d + 1.5, y + 7.0, d + 1.5), c("bois_moyen"), name="Hourd")
            for yaw in (0, 90, 180, 270):
                with b.at((0, 0, 0), yaw=yaw):
                    b.wedge_under((-d - 1.5, y - 2.5, -d - 1.5), (d + 1.5, y, -d), c("colombage"), down="-z",
                                  name="Aisselier")
                    for x in (-10.0, 0.0, 10.0):
                        b.box((x - 1.2, y + 2.4, -d - 1.62), (x + 1.2, y + 4.8, -d - 1.5), c("noir"), collide=False,
                              name="Archere")
                    for x in (-d - 1.3, -5.0, 5.0):
                        b.box((x, y, -d - 1.65), (x + 0.6, y + 7.0, -d - 1.5), c("colombage"), collide=False,
                              name="Poteau")
            top = _toit_gradins(b, 0, y + 7.0, 0, 2 * d + 5.0, 2 * d + 5.0, 6, 2.6, 2.7, cols=("tuile_brune", "tuile_fonce"),
                                name="Toit")
            b.ball((0, top + 0.6, 0), 1.0, c("or"), collide=False, name="Epi")
    else:
        with b.group("Beffroi"):
            y = y_p + 0.5
            b.box((-6.0, y, -6.0), (6.0, y + 1.0, 6.0), c("bois_moyen"), studs="top", name="Plancher")
            for x in (-5.0, 5.0):
                for z in (-5.0, 5.0):
                    b.box((x - 0.6, y + 1.0, z - 0.6), (x + 0.6, y + 13.0, z + 0.6), c("bois"), name="Poteau")
            for z in (-5.0, 5.0):
                b.box((-5.8, y + 13.0, z - 0.7), (5.8, y + 14.2, z + 0.7), c("bois_moyen"), name="Poutre")
            b.box((-0.4, y + 13.0, -4.4), (0.4, y + 13.8, 4.4), c("bois_moyen"), name="Mouton")
            b.wedge((-6.8, y + 14.2, -6.8), (6.8, y + 18.4, 0), c("tuile_brune"), down="-z", studs="top", name="Toit")
            b.wedge((-6.8, y + 14.2, 0), (6.8, y + 18.4, 6.8), c("tuile_brune"), down="+z", studs="top", name="Toit")
            b.box((-0.25, y + 11.0, -0.25), (0.25, y + 13.0, 0.25), c("fer"), collide=False, name="Joug")
            b.cyl((0, y + 9.4, 0), 1.9, 3.0, c("cloche"), axis="y", collide=False, name="Cloche")
            b.cyl((0, y + 7.6, 0), 2.4, 0.7, c("cloche"), axis="y", collide=False, name="Cloche")
            b.ball((0, y + 10.9, 0), 1.5, c("cloche"), collide=False, name="Cloche")
            _corde(b, (0, y + 7.3, 0), (3.5, y + 1.2, 2.5), 0.12)
        with b.at((-9.0, y_p + 0.5, 9.0), yaw=135):
            mobilier.drapeau(b, hauteur=20, variant=2)
    h_tot = {0: H + 22.0, 1: H + 8.0, 2: H + 18.0, 3: H + 18.0}[v]
    return {"emprise": (cote + 2 * TALUS, cote + 2 * TALUS), "hauteur": h_tot}


# ---------------------------------------------------------------------------
# 4) Monte-charge de bois
# ---------------------------------------------------------------------------

def monte_charge(b, variant=0, hauteur=90, profondeur=10.0):
    """Monte-charge de bois contre la face ville (arrière +Z contre le mur) : quatre poteaux jusqu'à hauteur + 4,
    contreventement tous les 15, portique au-dessus du parapet avec grande roue-poulie, cordes, plateau chargé.
    variant 0 : plateau de caisses et tonneau vers 40 ; 1 : cage ouverte de boulets près du sol ;
    2 : plateau de sacs à mi-hauteur et contrepoids de fonte sur la seconde corde."""
    v = variant % 3
    H4 = hauteur + 4.0
    d2 = profondeur / 2
    bois, clair = c("bois_echafaud"), c("bois_clair")
    fonce = shade(bois, 0.78)
    xp = 5.4
    zfp, zrp = -d2 + 0.5, d2 - 1.6           # poteaux avant / arrière (devant les pilastres du mur)
    zw = (zfp + zrp) / 2                      # plan de la roue
    with b.group("MonteCharge"):
        for x in (-xp, xp):
            for z in (zfp, zrp):
                b.box((x - 0.5, 0, z - 0.5), (x + 0.5, H4, z + 0.5), bois, name="Poteau")
        n = int(hauteur // 15)
        for k in range(n):
            y0, y1 = 15.0 * k, 15.0 * (k + 1)
            for x in (-xp, xp):
                za, zb_ = (zfp, zrp) if k % 2 == 0 else (zrp, zfp)
                _poutre(b, (x, y0 + 0.6, za), (x, y1 - 0.6, zb_), 0.35, fonce, collide=False, name="Croix")
            b.box((-xp + 0.5, y1 - 0.4, zfp - 0.3), (xp - 0.5, y1 + 0.4, zfp + 0.3), fonce, name="Moise")
        # portique au-dessus du parapet, posé sur deux potelets du chemin de ronde
        for x in (-xp, xp):
            b.box((x - 0.5, H4 - 1.0, zfp - 0.5), (x + 0.5, H4, d2 + 3.0), bois, name="Portique")
            b.box((x - 0.4, hauteur - 6.0, d2 + 2.0), (x + 0.4, H4 - 1.0, d2 + 2.8), bois, name="Potelet")
        b.box((-xp - 0.6, H4 - 1.0, zfp - 0.9), (xp + 0.6, H4, zfp - 0.5), fonce, name="Linteau")
        b.wedge((-xp - 0.8, H4, zfp - 1.2), (xp + 0.8, H4 + 1.6, d2 + 3.4), c("tuile_brune"), down="-z", studs="top",
                name="Auvent")
        y_ax = H4 - 1.25
        b.cyl((0, y_ax, zw), 0.25, 2 * xp, c("fer"), axis="x", name="Axe")
        b.cyl((0, y_ax, zw), 2.2, 0.6, clair, axis="x", name="Roue")
        b.box((-0.35, y_ax - 2.0, zw - 0.2), (0.35, y_ax + 2.0, zw + 0.2), fonce, collide=False, name="Rayon")
        b.box((-0.35, y_ax - 0.2, zw - 2.0), (0.35, y_ax + 0.2, zw + 2.0), fonce, collide=False, name="Rayon")
        # charge principale (corde avant) et corde arrière
        zc = zw - 2.1
        y_pl = {0: 40.0, 1: 1.0, 2: 56.0}[v]
        y_croc = y_pl + (7.5 if v != 1 else 8.0)
        b.cyl((0, (y_ax + y_croc) / 2, zc), 0.12, y_ax - y_croc, c("corde"), axis="y", collide=False, shadow=False,
              name="Corde")
        b.ball((0, y_croc, zc), 0.4, c("fer"), collide=False, name="Croc")
        for x in (-3.4, 3.4):
            _corde(b, (0, y_croc, zc), (x, y_pl + 0.6, zc), 0.09)
        b.box((-3.8, y_pl, zc - 2.6), (3.8, y_pl + 0.6, zc + 2.6), clair, studs="top", name="Plateau")
        if v == 0:
            b.box((-3.2, y_pl + 0.6, zc - 2.0), (-0.8, y_pl + 3.0, zc + 0.4), c("bois_clair"), name="Caisse")
            b.box((-2.4, y_pl + 0.6, zc + 0.6), (0.0, y_pl + 2.6, zc + 2.4), c("bois_moyen"), name="Caisse")
            b.cyl((2.0, y_pl + 2.0, zc), 1.0, 2.8, c("bois_moyen"), axis="y", name="Tonneau")
            b.cyl((2.0, y_pl + 2.0, zc), 1.06, 0.3, c("fer"), axis="y", collide=False, name="Cercle")
        elif v == 1:
            for x in (-3.5, 3.5):
                for z in (zc - 2.3, zc + 2.3):
                    b.box((x - 0.2, y_pl + 0.6, z - 0.2), (x + 0.2, y_pl + 6.6, z + 0.2), fonce, name="Barreau")
            b.box((-3.8, y_pl + 6.6, zc - 2.6), (3.8, y_pl + 7.0, zc + 2.6), fonce, name="Cadre")
            for (x, z) in ((-1.0, zc - 0.6), (0.3, zc - 0.6), (-0.35, zc + 0.5)):
                b.ball((x, y_pl + 1.25, z), 0.65, c("fonte"), collide=False, name="Boulet")
        else:
            for (x, z) in ((-2.0, zc - 0.8), (0.2, zc - 0.6), (-1.0, zc + 1.2)):
                b.boxc((x, y_pl + 1.25, z), (2.0, 1.3, 1.3), c("toile_creme"), name="Sac")
            b.box((-1.4, 26.0, zw + 0.7), (1.4, 30.0, zw + 3.0), c("fonte"), name="Contrepoids")
        # corde arrière : vers le cabestan (0, 1) ou vers le contrepoids (2)
        y_bas = 30.0 if v == 2 else 3.0
        b.cyl((0, (y_ax + y_bas) / 2, zw + 2.1), 0.12, y_ax - y_bas, c("corde"), axis="y", collide=False, shadow=False,
              name="Corde")
        if v != 2:
            b.cyl((0, 1.4, zw + 2.1), 0.9, 2.8, fonce, axis="y", name="Cabestan")
            b.box((-3.0, 2.5, zw + 1.85), (3.0, 2.8, zw + 2.35), clair, collide=False, name="Barre")
            b.box((-0.25, 2.5, zw + 2.1 - 2.4), (0.25, 2.8, zw + 2.1 + 2.4), clair, collide=False, name="Barre")
        with b.at((3.8, 0, -d2 + 2.6)):
            b.boxc((0, 1.0, 0), (2.0, 2.0, 2.0), c("bois_clair"), yaw=7, studs="top", name="Caisse")
            b.boxc((-0.2, 2.8, 0.1), (1.6, 1.6, 1.6), c("bois_moyen"), yaw=-9, studs="top", name="Caisse")
    return {"emprise": (12.0, profondeur), "hauteur": H4 + 1.6}


# ---------------------------------------------------------------------------
# 5) Escalier de rempart
# ---------------------------------------------------------------------------

def escalier_mur(b, variant=0, hauteur=90, longueur=40):
    """Escalier en zigzag de quatre volées et paliers jusqu'au chemin de ronde (84), contre la face ville
    (arrière +Z local, z = 4, contre le mur). Les volées alternent entre la voie du mur et la voie extérieure.
    variant 0 : pierre (marches en gradins, limons, paliers sur consoles) ; 1 : bois (marches ouvertes,
    poteaux) ; 2 : pierre en bas, bois en haut."""
    v = variant % 3
    niv = _niv(hauteur)
    L = float(longueur)
    xl = L / 2
    lp = 4.0
    y_top = niv["chemin"]
    n_vol = 4
    dh = y_top / n_vol
    n_m = 6
    zmur = 4.0
    voies = ((-0.4, 2.9), (-4.0, -0.6))
    pierre, pierre_f = c("mur_ombre"), c("mur_joint")
    bois, bois_c = c("bois"), c("bois_clair")
    with b.group("Escalier"):
        for i in range(n_vol):
            y0, y1 = i * dh, (i + 1) * dh
            sens = 1 if i % 2 == 0 else -1
            z0, z1 = voies[i % 2]
            en_bois = v == 1 or (v == 2 and i >= 2)
            xa_, xb_ = -sens * (xl - lp), sens * (xl - lp)      # départ, arrivée (bords des paliers)
            w = (xl - lp) * 2 / n_m
            r = dh / n_m
            # limon (rampant) sous les marches
            if i > 0 or en_bois:
                ya = y0 - 1.0 if i > 0 else 1.6
                _poutre(b, (xa_, ya, (z0 + z1) / 2), (xb_, y1 - 1.0, (z0 + z1) / 2),
                        (z1 - z0, 1.4), bois if en_bois else pierre_f, name="Limon")
            for j in range(n_m):
                xm0 = xa_ + sens * j * w
                xm1 = xm0 + sens * w
                t = y0 + (j + 1) * r
                bas = t - (1.0 if en_bois else r + 0.6)
                if i == 0 and not en_bois:
                    bas = 0.0
                x0, x1 = sorted((xm0, xm1))
                b.box((x0, bas, z0), (x1, t, z1), bois_c if en_bois else (c("mur_base") if j % 2 == 0 else pierre),
                      studs="top", name="Marche")
            # garde-corps : muret de pierre sur le bord extérieur, ou main courante de bois (voie extérieure)
            if not en_bois:
                _poutre(b, (xa_, y0 + (0.6 if i else 1.0), z0 + 0.15), (xb_, y1 + 0.6, z0 + 0.15), (0.6, 2.0), c("mur_fonce"),
                        collide=False, name="Garde-corps")
            elif i % 2 == 1:
                _poutre(b, (xa_, y0 + 3.4, -3.85), (xb_, y1 + 3.4, -3.85), 0.3, c("colombage"), collide=False,
                        name="Rampe")
            # palier d'arrivée (deux voies, contre le mur)
            xp0, xp1 = sorted((sens * (xl - lp), sens * xl))
            if en_bois:
                b.box((xp0, y1 - 0.8, -4.0), (xp1, y1, zmur), bois_c, studs="top", name="Palier")
                # poteaux aux angles avant, du sol (ou du palier de pierre) jusqu'au plus haut palier de ce côté
                if (v == 1 and i < 2) or v == 2:
                    y_pied = 0.0 if v == 1 else (i - 1) * dh
                    y_tete = (3 * dh if sens > 0 else y_top) if v == 1 else y1
                    for xx in (xp0 + 0.7, xp1 - 0.7):
                        b.box((xx - 0.5, y_pied, -4.1), (xx + 0.5, y_tete - 0.8, -3.1), bois, name="Poteau")
            else:
                b.box((xp0, y1 - 1.5, -4.0), (xp1, y1, zmur), c("mur_fonce"), studs="top", name="Palier")
                b.wedge_under((xp0, y1 - 7.0, -3.0), (xp1, y1 - 1.5, zmur), pierre_f, down="-z", name="Console")
        # lanternes au palier du milieu et en haut
        _lanterne_compacte(b, -xl + 2.0, 2 * dh + 5.0, zmur)
        _lanterne_compacte(b, xl - 2.0, dh + 5.0, zmur)
    return {"emprise": (L, 8.0), "hauteur": y_top + 4.8}


__all__ = ["porte_colossale", "mur_colossal", "tour_angle", "monte_charge", "escalier_mur"]
