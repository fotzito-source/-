"""Tapis roulant du centre (« tapis de transfert du labo », G06) et portail de tête de voie (facultatif).

    python apercu.py assets.tapis:tapis --no-ground ...        (le tapis entier, en coordonnées de la carte)
    python apercu.py assets.tapis:portail --variant 0 --res 1200x675 --samples 12

`tapis(b)` se construit **en coordonnées de la carte** (carte.py : `with b.at((0, 0, 0), group="Tapis")`) et suit
exactement la géométrie de `plan.py`, sans aucune cote en dur : les quadrilatères de `plan.tapis_bandes()` (onglets
aux joints) et les poses de `plan.chevrons()`. U ouvert (aujourd'hui) ou boucle fermée : le code ne change pas.
- Chaque quadrilatère (bordure intérieure, bande, bordure extérieure d'un tronçon) = un bloc pour sa partie
  rectangulaire + un coin posé à plat (triangle rectangle, faces triangulaires horizontales, studs dessus) à chaque
  bout biseauté : les joints sont exacts, sans jour ni recouvrement (pas de triangles noirs dans les virages).
- Deux tronçons qui se touchent n'ont jamais leurs dessus au même niveau (paliers de 0,02, trois niveaux si une
  boucle fermée a un nombre impair de tronçons).
- Liseré Neon cyan sur l'arête de chaque bordure côté bande (un par tronçon et par côté).
- Bouts ouverts (têtes d'un U) : embout carré, bordure blanche en travers et filet Neon cyan (LAYOUT : « embout carré
  et filet blanc en travers de la bande ») ; rien sur une boucle fermée.
- Chevrons blancs en « V » (2 bras), pointe dans le sens du flux ; près d'un joint, le « V » suit la courbe (les
  bouts des bras sont pris sur l'axe 3,5 en arrière, comme les chevrons pliés de la référence).
- Les pièces de la bande portent les attributs Roblox `Troncon`, `FluxX`, `FluxZ` (sens du flux, pour scripter le
  défilement : `part.AssemblyLinearVelocity = Vector3.new(FluxX, 0, FluxZ) * vitesse`).

`portail(b, variant)` : porte de tête de voie, posée seulement si `plan.PORTAILS` en donne (le plan final : têtes
sans portail, « embout carré » ; la fonction reste pour un portail voulu) (variante 0 = entrée, Neon violet ; 1 =
sortie, Neon cyan) :
socles arrondis à studs de part et d'autre de la bande, colonnes rayées, grande arche d'or, fine arche Neon devant,
fond fermé arrondi blanc à hublot lumineux (cœur Neon sous une bulle de verre), petit dôme et antenne au sommet.
Avant (-Z local) vers le tapis ; la bande passe dessous dans l'axe x = 0, de z = -profondeur/2 au fond.
"""

from __future__ import annotations

import math

import numpy as np

import plan
from kit import mix, rot_z, shade
from palette import c

# --------------------------------------------------------------------------------------------------------------
# Géométrie plane (x, z) : quadrilatère = bloc + coins à plat
# --------------------------------------------------------------------------------------------------------------

EPS = 1e-6
TAILLE_MIN = 0.1          # aucune pièce plus fine (règle de la carte)
BAS = -0.1                # toutes les pièces du tapis descendent 0,1 dans la pelouse (aucun dessous à y = 0 :
#                           les lignes de la grille ont leur dessous à 0)
PALIER = 0.02             # décalage de hauteur entre deux tronçons qui se touchent


def _v(p) -> np.ndarray:
    return np.asarray(p, float)


def _cross(a, b) -> float:
    return float(a[0] * b[1] - a[1] * b[0])


def coin_plat(b, V, e1, L1, e2, L2, y0, y1, couleur, *, studs=True, **kw):
    """Triangle rectangle horizontal extrudé de y0 à y1 (WedgePart couché) : angle droit en V (x, z), côtés
    V → V + e1·L1 et V → V + e2·L2 (e1 ⟂ e2, unitaires). La face triangulaire du dessus (face « Right » du coin)
    porte les studs. 1 pièce."""
    V, e1, e2 = _v(V), _v(e1) / np.linalg.norm(e1), _v(e2) / np.linalg.norm(e2)
    # Repère du coin : X local = haut ; Y local = e1 ; Z local = -e2, avec X × Y = Z (repère direct) :
    # haut × (e1x, 0, e1z) = (e1z, 0, -e1x) doit valoir -e2, c.-à-d. e1 × e2 > 0 (plan x, z) ; sinon on échange.
    if _cross(e1, e2) < 0:
        e1, e2, L1, L2 = e2, e1, L2, L1
    X = np.array([0.0, 1.0, 0.0])
    Y = np.array([e1[0], 0.0, e1[1]])
    Z = np.array([-e2[0], 0.0, -e2[1]])
    assert np.allclose(np.cross(X, Y), Z, atol=1e-9), (e1, e2)
    ctr2 = V + e1 * L1 / 2 + e2 * L2 / 2
    R = np.column_stack([X, Y, Z])
    return b.part("wedge", (y1 - y0, L1, L2), (ctr2[0], (y0 + y1) / 2, ctr2[1]), R, couleur,
                  studs=("Right",) if studs else (), name=kw.pop("name", "Coin"), **kw)


def _bloc_plat(b, centre2, d, longueur, largeur, y0, y1, couleur, *, studs=True, **kw):
    """Bloc horizontal de `longueur` le long de d (x, z), `largeur` en travers, de y0 à y1."""
    d = _v(d) / np.linalg.norm(d)
    X = np.array([d[0], 0.0, d[1]])
    Y = np.array([0.0, 1.0, 0.0])
    Z = np.cross(X, Y)
    R = np.column_stack([X, Y, Z])
    return b.part("block", (longueur, y1 - y0, largeur), (centre2[0], (y0 + y1) / 2, centre2[1]), R, couleur,
                  studs=("Top",) if studs else (), name=kw.pop("name", "Dalle"), **kw)


def _triangle(b, A, B, C, y0, y1, couleur, *, studs=True, **kw):
    """Triangle quelconque (x, z) extrudé : 2 coins à plat de part et d'autre de la hauteur issue du sommet opposé
    au plus long côté (1 seul si le triangle est rectangle). Recours pour les quadrilatères trop courts."""
    P = [_v(A), _v(B), _v(C)]
    cotes = [(np.linalg.norm(P[(i + 1) % 3] - P[i]), i) for i in range(3)]
    _, i = max(cotes)
    U, W, S = P[i], P[(i + 1) % 3], P[(i + 2) % 3]           # [U, W] = plus long côté, S = sommet opposé
    base = W - U
    Lb = float(np.linalg.norm(base))
    t = float((S - U) @ base) / Lb
    H = U + base / Lb * t                                     # pied de la hauteur (sur [U, W] : angles aigus)
    h = float(np.linalg.norm(S - H))
    out = []
    if h < TAILLE_MIN:
        return out
    eh = (S - H) / h
    for (Q, L) in ((U, t), (W, Lb - t)):
        if L >= TAILLE_MIN:
            out.append(coin_plat(b, H, (Q - H) / L, L, eh, h, y0, y1, couleur, studs=studs, **dict(kw)))
    return out


def dalle_quad(b, quad, y0, y1, couleur, *, studs=True, **kw) -> list:
    """Quadrilatère plat (x, z) extrudé de y0 à y1, exactement : [P0, P1, P2, P3] avec P0 → P1 et P3 → P2 parallèles
    (côtés longs d'un tronçon), P0-P3 et P1-P2 les bouts (droits ou biseautés). Bloc pour la partie rectangulaire,
    un coin à plat par bout biseauté (biais ≥ 0,1 ; en dessous, le bloc va jusqu'au milieu du biais : écart ≤ 0,05).
    Si les côtés ne sont pas parallèles ou si la partie rectangulaire est trop courte : deux triangles."""
    P = [_v(p) for p in quad]
    u = P[1] - P[0]
    La = float(np.linalg.norm(u))
    v = P[2] - P[3]
    Lb = float(np.linalg.norm(v))
    if La < EPS or Lb < EPS:
        return _triangle(b, P[0], P[1], P[2], y0, y1, couleur, studs=studs, **kw) + \
            _triangle(b, P[0], P[2], P[3], y0, y1, couleur, studs=studs, **kw)
    d = u / La
    parallele = abs(_cross(d, v / Lb)) < 1e-6 and float(d @ (v / Lb)) > 0
    w_vec = (P[3] - P[0]) - float((P[3] - P[0]) @ d) * d
    w = float(np.linalg.norm(w_vec))
    if not parallele or w < TAILLE_MIN:
        return _triangle(b, P[0], P[1], P[2], y0, y1, couleur, studs=studs, **kw) + \
            _triangle(b, P[0], P[2], P[3], y0, y1, couleur, studs=studs, **kw)
    n = w_vec / w
    s0a, s1a = 0.0, La
    s0b = float((P[3] - P[0]) @ d)
    s1b = float((P[2] - P[0]) @ d)
    biais0, biais1 = abs(s0a - s0b), abs(s1a - s1b)
    lo = max(s0a, s0b) if biais0 >= TAILLE_MIN else (s0a + s0b) / 2
    hi = min(s1a, s1b) if biais1 >= TAILLE_MIN else (s1a + s1b) / 2
    if hi - lo < TAILLE_MIN:
        return _triangle(b, P[0], P[1], P[2], y0, y1, couleur, studs=studs, **kw) + \
            _triangle(b, P[0], P[2], P[3], y0, y1, couleur, studs=studs, **kw)
    out = [_bloc_plat(b, P[0] + d * (lo + hi) / 2 + n * w / 2, d, hi - lo, w, y0, y1, couleur, studs=studs,
                      **dict(kw))]
    nom_coin = kw.pop("name", "Dalle") + "_Coin"
    if biais0 >= TAILLE_MIN:
        if s0a < s0b:     # le côté a commence plus tôt : angle droit sur le côté a, en face du début du côté b
            out.append(coin_plat(b, P[0] + d * s0b, -d, s0b - s0a, n, w, y0, y1, couleur, studs=studs,
                                 name=nom_coin, **dict(kw)))
        else:
            out.append(coin_plat(b, P[0] + n * w + d * s0a, -d, s0a - s0b, -n, w, y0, y1, couleur, studs=studs,
                                 name=nom_coin, **dict(kw)))
    if biais1 >= TAILLE_MIN:
        if s1a > s1b:     # le côté a finit plus tard : angle droit sur le côté a, en face de la fin du côté b
            out.append(coin_plat(b, P[0] + d * s1b, d, s1a - s1b, n, w, y0, y1, couleur, studs=studs,
                                 name=nom_coin, **dict(kw)))
        else:
            out.append(coin_plat(b, P[0] + n * w + d * s1a, d, s1b - s1a, -n, w, y0, y1, couleur, studs=studs,
                                 name=nom_coin, **dict(kw)))
    return out


# --------------------------------------------------------------------------------------------------------------
# Axe du tapis (reconstruit depuis les bandes : il suit toujours la géométrie du plan)
# --------------------------------------------------------------------------------------------------------------

class Axe:
    """Polyligne de l'axe du tapis dans le sens du flux, reconstruite depuis les quadrilatères de la bande (milieux
    des bouts) ; fermée si le dernier point rejoint le premier."""

    def __init__(self, bandes):
        pts = [(_v(bandes[0]["bande"][0]) + _v(bandes[0]["bande"][3])) / 2]
        for t in bandes:
            pts.append((_v(t["bande"][1]) + _v(t["bande"][2])) / 2)
        self.ferme = bool(np.linalg.norm(pts[-1] - pts[0]) < 0.05)
        if self.ferme:
            pts[-1] = pts[0].copy()
        self.pts = pts
        self.cum = [0.0]
        for i in range(len(pts) - 1):
            self.cum.append(self.cum[-1] + float(np.linalg.norm(pts[i + 1] - pts[i])))
        self.L = self.cum[-1]

    def point(self, s):
        """(p, d) à l'abscisse s (repliée si l'axe est fermé, bornée sinon)."""
        if self.ferme:
            s = s % self.L
        s = min(max(s, 0.0), self.L)
        for i in range(len(self.pts) - 1):
            if s <= self.cum[i + 1] + 1e-9 or i == len(self.pts) - 2:
                a, bb = self.pts[i], self.pts[i + 1]
                Lseg = self.cum[i + 1] - self.cum[i]
                t = (s - self.cum[i]) / Lseg if Lseg > EPS else 0.0
                return a + (bb - a) * t, (bb - a) / Lseg
        raise ValueError("axe vide")

    def projeter(self, p) -> float:
        """Abscisse du point de l'axe le plus proche de p."""
        p = _v(p)
        best, s_best = 1e18, 0.0
        for i in range(len(self.pts) - 1):
            a, bb = self.pts[i], self.pts[i + 1]
            ab = bb - a
            L2 = float(ab @ ab)
            t = 0.0 if L2 < EPS else max(0.0, min(1.0, float((p - a) @ ab) / L2))
            dist = float(np.linalg.norm(a + ab * t - p))
            if dist < best - 1e-9:
                best, s_best = dist, self.cum[i] + t * math.sqrt(L2)
        return s_best


def _niveaux(bandes) -> list[int]:
    """Palier de hauteur de chaque tronçon (0, 1 ou 2) : deux tronçons qui se touchent (voisins, et le dernier avec
    le premier si le tapis est fermé) ont des paliers différents."""
    n = len(bandes)
    fin0 = (_v(bandes[0]["bande"][0]) + _v(bandes[0]["bande"][3])) / 2
    finN = (_v(bandes[-1]["bande"][1]) + _v(bandes[-1]["bande"][2])) / 2
    ferme = n > 2 and float(np.linalg.norm(finN - fin0)) < 0.05
    niv = []
    for i in range(n):
        pris = set()
        if i > 0:
            pris.add(niv[i - 1])
        if ferme and i == n - 1:
            pris.add(niv[0])
        k = 0
        while k in pris:
            k += 1
        niv.append(k)
    return niv


def _cote_vers(quad, cible) -> tuple:
    """Côté long d'un quadrilatère le plus proche du point `cible` : (S0, S1, T0, T1) = bout de début et de fin de ce
    côté, puis bouts correspondants de l'autre côté."""
    P = [_v(p) for p in quad]
    ma = (P[0] + P[1]) / 2
    mb = (P[3] + P[2]) / 2
    if np.linalg.norm(ma - cible) <= np.linalg.norm(mb - cible):
        return P[0], P[1], P[3], P[2]
    return P[3], P[2], P[0], P[1]


# --------------------------------------------------------------------------------------------------------------
# Le tapis
# --------------------------------------------------------------------------------------------------------------

LISERE_LARGEUR = 0.3
LISERE_EPAISSEUR = 0.15
LISERE_RETRAIT = 0.02          # le liseré n'affleure pas la face de la bordure côté bande (pas de face confondue)
CHEVRON_HAUTS = (0.70, 0.72)   # dessus des deux bras (un bras 0,02 plus haut)
EMBOUT_LONGUEUR = 1.2          # embout carré des têtes ouvertes (le long du flux)
EMBOUT_DESSUS = 1.05           # au-dessus des bordures (1,0 / 1,02 / 1,04) : aucun dessus confondu
EMBOUT_BAS = -0.17             # dessous différent de ceux des bandes (-0,10 / -0,12 / -0,14) et bordures
CHEVRON_BAS = (0.56, 0.54)     # dessous des bras : dans la bande (au-dessus de y 0,6 : aucun jour)


def tapis(b, variant=0, **params):
    """Le tapis entier (bande, bordures, liserés, chevrons), en coordonnées de la carte, sur la géométrie exacte de
    plan.py. Budget ≤ 480 pièces, ≤ 40 Neon. Paramètres facultatifs : `bandes` (liste au format de
    plan.tapis_bandes()) et `chevrons` (format de plan.chevrons()) pour essayer une autre géométrie."""
    bandes = params.get("bandes") or plan.tapis_bandes()
    poses = params.get("chevrons")
    if poses is None:
        poses = plan.chevrons()
    col_bande = c("bleu_nuit")
    col_bord = c("blanc_labo")
    col_lisere = c("cyan")
    col_chevron = c("blanc_labo")
    niv = _niveaux(bandes)
    dessus_bande = plan.TAPIS_DESSUS
    dessus_bord = plan.TAPIS_DESSUS_BORDURE

    for i, t in enumerate(bandes):
        dy = PALIER * niv[i]
        d = _v(t["direction"])
        flux = {"Troncon": t["id"], "FluxX": round(float(d[0]), 4), "FluxZ": round(float(d[1]), 4)}
        # dessous décalés eux aussi (bande / bordures, tronçon / voisin) : aucun dessous confondu, même avec les
        # arrondis au 1/10 000 des positions
        with b.group("Bande"):
            dalle_quad(b, t["bande"], BAS - dy, dessus_bande + dy, col_bande, name=f"Bande_{t['id']}", attrs=flux)
        with b.group("Bordures"):
            for cle in ("bordure_int", "bordure_ext"):
                dalle_quad(b, t[cle], BAS - 0.01 - dy, dessus_bord + dy, col_bord, name=f"Bordure_{t['id']}")
        # Liseré Neon sur l'arête de chaque bordure côté bande : un bloc par tronçon et par côté, posé sur la
        # bordure, couvrant tout son biais (les bouts des tronçons voisins se chevauchent à des hauteurs différentes)
        ctr_bande = sum(_v(p) for p in t["bande"]) / 4
        with b.group("Liseres"):
            for cle in ("bordure_int", "bordure_ext"):
                S0, S1, T0, T1 = _cote_vers(t[cle], ctr_bande)
                dl = S1 - S0
                L = float(np.linalg.norm(dl))
                if L < TAILLE_MIN:
                    continue
                dl = dl / L
                nl = (T0 - S0) - float((T0 - S0) @ dl) * dl
                wq = float(np.linalg.norm(nl))
                nl = nl / wq
                a0 = LISERE_RETRAIT
                a1 = LISERE_RETRAIT + LISERE_LARGEUR
                # abscisses des quatre coins de la bande du liseré (les bouts suivent les onglets du quadrilatère)
                ss = []
                for (A, Bq) in ((S0, T0), (S1, T1)):
                    for f in (a0 / wq, a1 / wq):
                        Q = A + (Bq - A) * f
                        ss.append(float((Q - S0) @ dl))
                s_lo, s_hi = min(ss), max(ss)
                ctr = S0 + dl * (s_lo + s_hi) / 2 + nl * (a0 + a1) / 2
                y0 = dessus_bord + dy
                _bloc_plat(b, ctr, dl, s_hi - s_lo, LISERE_LARGEUR, y0, y0 + LISERE_EPAISSEUR, col_lisere,
                           studs=False, material="Neon", collide=False, shadow=False, name=f"Lisere_{t['id']}")

    # Embouts : aux bouts ouverts (têtes d'un U), une bordure blanche en travers de toute la largeur (0,1 plus large et
    # plus longue que la bande : aucune face confondue), dessus à 1,05, et un filet Neon cyan sur son arête côté
    # bande, qui rejoint les deux liserés ; rien si le tapis est fermé.
    axe = Axe(bandes)
    if not axe.ferme:
        with b.group("Embouts"):
            for t, debut in ((bandes[0], True), (bandes[-1], False)):
                d = _v(t["direction"]) / np.linalg.norm(t["direction"])
                if debut:      # bout de départ : coins « début » des bordures, la bande continue vers +d
                    A, B = _v(t["bordure_ext"][0]), _v(t["bordure_int"][3])
                    vers = d
                else:          # bout d'arrivée : coins « fin », la bande vient de -d
                    A, B = _v(t["bordure_ext"][1]), _v(t["bordure_int"][2])
                    vers = -d
                larg = float(np.linalg.norm(B - A))
                mil = (A + B) / 2
                e = EMBOUT_LONGUEUR
                ctr = mil + vers * (e / 2) - vers * 0.05
                _bloc_plat(b, ctr, vers, e + 0.1, larg + 0.2, EMBOUT_BAS, EMBOUT_DESSUS, col_bord,
                           name="Embout")
                _bloc_plat(b, mil + vers * (e - LISERE_RETRAIT - LISERE_LARGEUR / 2), vers, LISERE_LARGEUR,
                           plan.TAPIS_BANDE + 2 * LISERE_RETRAIT + 2 * LISERE_LARGEUR + 0.1, EMBOUT_DESSUS,
                           EMBOUT_DESSUS + LISERE_EPAISSEUR, col_lisere, studs=False, material="Neon",
                           collide=False, shadow=False, name="Lisere_Embout")

    # Chevrons : pointe sur l'axe (pose du plan), bouts des bras 3,5 en arrière le long de l'axe (V plié près d'un
    # joint), envergure 9, bras de 1,2.
    prof = plan.CHEVRON_PROFONDEUR
    demi = plan.CHEVRON_LARGEUR / 2
    trait = plan.CHEVRON_TRAIT
    with b.group("Chevrons"):
        for k, ch in enumerate(poses):
            T = _v((ch["x"], ch["z"]))
            s = axe.projeter(T)
            _, dT = axe.point(s)
            pB, dB = axe.point(s - prof)
            nB = np.array([dB[1], -dB[0]])
            bouts = (pB + nB * demi, pB - nB * demi)
            us = [(E - T) / np.linalg.norm(E - T) for E in bouts]
            nf = []
            for u in us:
                cand = np.array([-u[1], u[0]])
                nf.append(cand if cand @ dT > 0 else -cand)
            # pointe avant F : intersection des deux arêtes avant (bras de largeur `trait`)
            h = trait / 2
            A0, A1 = T + nf[0] * h, T + nf[1] * h
            det = _cross(us[0], -us[1])
            if abs(det) > 1e-6:
                r = A1 - A0
                t0 = _cross(r, -us[1]) / det
                F = A0 + us[0] * t0
            else:
                F = A0
            for j, (E, u) in enumerate(zip(bouts, us)):
                s_av = float((F - T) @ u)
                s_ar = float(np.linalg.norm(E - T))
                _bloc_plat(b, T + u * (s_av + s_ar) / 2, u, s_ar - s_av, trait, CHEVRON_BAS[j], CHEVRON_HAUTS[j],
                           col_chevron, collide=False, name="Chevron")

    xs = [p[0] for t in bandes for cle in ("bordure_int", "bande", "bordure_ext") for p in t[cle]]
    zs = [p[1] for t in bandes for cle in ("bordure_int", "bande", "bordure_ext") for p in t[cle]]
    return {"emprise": (round(max(xs) - min(xs), 2), round(max(zs) - min(zs), 2)),
            "hauteur": round(max(dessus_bord + PALIER * max(niv), EMBOUT_DESSUS if not axe.ferme else 0.0)
                             + LISERE_EPAISSEUR, 2),
            "chevrons": len(poses), "troncons": len(bandes), "ferme": axe.ferme,
            "longueur_axe": round(axe.L, 2)}


# --------------------------------------------------------------------------------------------------------------
# Boîte arrondie (socles) : 2 blocs en croix + 4 cylindres aux coins ; dessus décalés (0,05 et 0,1)
# --------------------------------------------------------------------------------------------------------------

def boite_arrondie(b, x0, x1, z0, z1, y0, y1, rayon, couleur, *, studs=True, **kw) -> list:
    """Boîte aux coins arrondis (vue de dessus) de [x0, x1] × [z0, z1], de y0 à y1. Le bloc en Z est 0,05 plus
    bas que le bloc en X, les cylindres d'angle 0,1 plus bas (aucun dessus confondu) ; les dessous suivent
    (0,02 et 0,04 plus haut). 6 pièces."""
    r = rayon
    st = "top" if studs else ()
    nom = kw.pop("name", "Socle")
    out = [b.box((x0, y0, z0 + r), (x1, y1, z1 - r), couleur, studs=st, name=nom, **kw),
           b.box((x0 + r, y0 + 0.02, z0), (x1 - r, y1 - 0.05, z1), couleur, studs=st, name=nom, **kw)]
    for x in (x0 + r, x1 - r):
        for z in (z0 + r, z1 - r):
            out.append(b.cyl((x, (y0 + 0.04 + y1 - 0.1) / 2, z), r, (y1 - 0.1) - (y0 + 0.04), couleur, studs=st,
                             name=nom, **kw))
    return out


# --------------------------------------------------------------------------------------------------------------
# Portail des têtes de voies
# --------------------------------------------------------------------------------------------------------------

PORTAIL_SCHEMAS = [
    # 0 : entrée (les objets apparaissent) — famille violette ; 1 : sortie (ils disparaissent) — famille lagon
    {"neon": "neon_violet", "rayures": ("violet", "lavande"), "socle": "blanc_labo", "plateau": "lavande",
     "dome": "violet", "fond_bord": "violet", "hublot_cadre": "or", "hublot_fond": "indigo",
     "hublot_anneau": "lavande", "boule": "violet"},
    {"neon": "cyan", "rayures": ("turquoise", "blanc_labo"), "socle": "blanc_labo", "plateau": "turquoise",
     "dome": "turquoise", "fond_bord": "turquoise", "hublot_cadre": "or", "hublot_fond": "bleu_nuit",
     "hublot_anneau": "turquoise", "boule": "turquoise"},
]


def portail(b, variant=0, largeur=30, profondeur=16, hauteur=36, **params):
    """Portail d'une tête de voie (≤ 90 pièces, ≤ 12 Neon, ≤ 1 verre). Avant (-Z local) vers le tapis ; la bande
    (16,1 de large) passe dessous dans l'axe x = 0, de z = -profondeur/2 jusqu'au fond fermé."""
    s = {k: (tuple(c(x) for x in v) if isinstance(v, tuple) else c(v))
         for k, v in PORTAIL_SCHEMAS[variant % len(PORTAIL_SCHEMAS)].items()}
    W, P, H = float(largeur), float(profondeur), float(hauteur)
    xo = plan.PORTAIL_OUVERTURE / 2                     # faces intérieures des socles (9,25)
    xe = W / 2                                          # faces extérieures (15)
    zf = -P / 2                                         # face avant (côté tapis)
    zb = P / 2
    # bout de la bande dans le repère du portail (le plan : tête à l'avant, fond 12 plus loin) ; si le plan ne fait
    # plus entrer la bande dans un portail (têtes sans portail), le fond garde sa place propre (3/4 de la profondeur)
    entree = abs(plan.TAPIS_Z_TETE - plan.TAPIS_Z_FOND)
    z_fin = zf + (entree if entree >= 0.5 * P else 0.75 * P)
    h_socle = 2.4
    xc = (xo + xe) / 2 + 0.2                            # axe des colonnes et rayon de l'arche (≈ 12,3)
    zc = z_fin - 3.4                                    # colonnes et arche juste devant le fond (≈ 0,6)
    r_col = 1.5
    t_arche = 1.8                                       # section carrée de l'arche d'or
    y_c = H - 2.4 - xc - t_arche / 2                    # centre de l'arche : sommet de l'arche ≈ H - 2,4
    n_arche = 24                                        # arche d'or : 12 segments sur 180° (joint au sommet)
    n_neon = 18                                         # arche Neon : 9 segments (un segment à plat au sommet)

    # -- socles : boîte arrondie blanche + plateau de couleur à studs ; bornes d'entrée à l'avant
    with b.group("Socles"):
        for sx in (-1, 1):
            xa, xb_ = sorted((sx * xo, sx * xe))
            boite_arrondie(b, xa, xb_, zf, zb, BAS, h_socle - 0.5, 1.4, s["socle"], studs=False)
            boite_arrondie(b, xa + 0.35, xb_ - 0.35, zf + 0.35, zb - 0.35, h_socle - 0.62, h_socle, 1.1,
                           s["plateau"], name="Plateau")
            xi = sx * (xo + 1.0)                        # borne au coin avant intérieur, au ras de la bande
            b.cyl((xi, h_socle + 1.6, zf + 1.1), 0.55, 3.3, c("blanc_labo"), name="Borne")
            b.ball((xi, h_socle + 3.55, zf + 1.1), 0.85, s["boule"], name="BorneBoule")
    # -- colonnes rayées sur bague d'or, chapiteau d'or
    with b.group("Colonnes"):
        for sx in (-1, 1):
            x = sx * xc
            b.cyl((x, h_socle + 0.35, zc), r_col + 0.55, 0.7, c("or_fonce"), studs="top", name="Bague")
            n_r = 6
            y0, y1 = h_socle + 0.7, y_c - 0.7
            hr = (y1 - y0) / n_r
            for k in range(n_r):
                b.cyl((x, y0 + hr * (k + 0.5), zc), r_col, hr, s["rayures"][k % 2], name="Rayure")
            b.cyl((x, y_c - 0.1, zc), r_col + 0.55, 1.4, c("or_fonce"), name="Chapiteau")
    # -- grande arche d'or (un segment à plat au sommet) et fine arche Neon sur sa face avant
    with b.group("Arche"):
        b.anneau((0, y_c, zc), xc, t_arche, c("or"), n_arche, axe="z", arc=180, section="carre", name="Arche")
        b.anneau((0, y_c, zc - t_arche / 2 - 0.13), xc, 0.38, s["neon"], n_neon, axe="z", arc=180,
                 section="rond", material="Neon", collide=False, shadow=False, name="ArcheNeon")
    # -- fond fermé arrondi : plaque blanche à demi-disque, plaque de couleur derrière (liseré), hublot lumineux
    #    devant (cœur Neon sous une bulle de verre), grand cercle d'or au dos
    with b.group("Fond"):
        r_f = xc - t_arche / 2 - 0.45                   # le demi-disque du fond reste dans l'arche
        z0f = z_fin - 0.1                               # la bande entre de 0,1 dans le fond
        e_f = 2.6                                       # épaisseur du fond (blanc devant et derrière)
        z1f = z0f + e_f
        b.box((-r_f, BAS - 0.1, z0f), (r_f, y_c - 0.05, z1f), s["socle"], name="Fond")
        b.cyl((0, y_c, (z0f + z1f) / 2), r_f, e_f - 0.1, s["socle"], axis="z", name="Fond")
        # liseré de couleur pris au milieu de l'épaisseur : il dépasse de 0,75 tout autour (devant comme derrière
        # on voit du blanc cerclé de couleur)
        r_b = r_f + 0.75
        zb0, zb1 = z0f + 0.95, z1f - 0.95
        b.box((-r_b, BAS - 0.15, zb0), (r_b, y_c + 0.05, zb1), s["fond_bord"], name="FondBord")
        b.cyl((0, y_c, (zb0 + zb1) / 2), r_b, zb1 - zb0 - 0.1, s["fond_bord"], axis="z", name="FondBord")
        y_h = 0.52 * y_c + 4.0                          # centre du hublot (≈ 14)
        b.cyl((0, y_h, z0f - 0.2), 6.6, 0.5, s["hublot_cadre"], axis="z", name="HublotCadre")
        b.cyl((0, y_h, z0f - 0.35), 5.6, 0.4, s["hublot_fond"], axis="z", name="HublotFond")
        b.cyl((0, y_h, z0f - 0.5), 3.7, 0.3, s["hublot_anneau"], axis="z", name="HublotAnneau")
        b.ball((0, y_h, z0f - 0.9), 1.9, s["neon"], material="Neon", collide=False, shadow=False, name="Coeur")
        b.ellipsoid((0, y_h, z0f - 0.6), (8.6, 8.6, 4.6), c("verre"), material="Glass", transparency=0.5,
                    collide=False, name="Bulle")
        # dos : le même hublot, éteint (le portail se voit aussi depuis le trottoir et la route du nord)
        b.cyl((0, y_h, z1f + 0.2), 6.6, 0.5, s["hublot_cadre"], axis="z", name="DosCadre")
        b.cyl((0, y_h, z1f + 0.35), 5.6, 0.4, s["hublot_fond"], axis="z", name="DosFond")
        b.cyl((0, y_h, z1f + 0.5), 3.7, 0.3, s["hublot_anneau"], axis="z", name="DosAnneau")
        b.cyl((0, y_h, z1f + 0.62), 1.9, 0.3, s["dome"], axis="z", name="DosPastille")
        # bandeau de couleur au dos, à la naissance du demi-disque (cache le raccord bloc / demi-disque)
        b.box((-(r_f + 0.25), y_c - 0.45, z1f - 0.3), (r_f + 0.25, y_c + 0.45, z1f + 0.15), s["fond_bord"],
              name="Bandeau")
    # -- couronnement : tambour, dôme, antenne à boule
    with b.group("Sommet"):
        y_top = y_c + xc + t_arche / 2                  # dessus du segment du sommet
        # tambour : descend de 0,3 sous le sommet de l'arche (joint de deux segments, faîte en pente de 7,5°)
        b.cyl((0, y_top + 0.575, zc), 2.9, 1.75, c("blanc_labo"), studs="top", name="Tambour")
        b.dome((0, y_top + 1.45, zc), 2.9, 2.6, s["dome"], collide=False)
        b.cyl((0, y_top + 1.45 + 2.6 + 0.9, zc), 0.22, 2.2, c("blanc_labo"), collide=False, name="Antenne")
        b.ball((0, y_top + 1.45 + 2.6 + 2.2, zc), 0.55, c("or"), collide=False, name="Pointe")
    return {"emprise": (W, P), "hauteur": round(y_top + 1.45 + 2.6 + 2.75, 2), "ouverture": 2 * xo,
            "dessous_arche": round(y_c, 2), "fond_z": round(z_fin, 2)}
