"""Montagne aux glycines (fond de la zone) et train à vapeur de l'ère Taishō, en style stud.

montagne_glycines (budget ≤ 3150 pièces, 2900 à 3150 selon la variante)
    Origine = centre de l'entrée de la gorge, au niveau du sol. Exception à la règle « l'avant regarde -Z » :
    la montagne regarde +Z (vers les joueurs qui arrivent), sa face avant suit z ≈ 0 et la masse s'étend
    vers -Z sur `profondeur` (la peau du dos s'arrête en z = -profondeur ; devant, escaliers, lanternes,
    grand torii et glycines remarquables débordent d'environ 23 studs).
    - plan en colonnes (10 à 18 studs) et en gradins vers l'arrière (avant, milieu, sommet, dos) : une carte de
      hauteurs en gros blocs, plus haute près de la gorge (aiguilles comprises), qui descend en marches vers
      les côtés ; les colonnes voisines partagent leurs corniches par groupes (rideaux de glycines continus) ;
    - strates horizontales continues (bleu nuit → bleu-violet clair, filets lavande) ; bancs plus épais
      (moins de pièces) sur les gradins hauts et au dos ; la face avant, les parois de la gorge et le dos ont
      une « peau » de masses en saillie, en gradins (petites corniches) et avec des fissures ;
    - gorge à ciel ouvert pour le couloir : parois en gradins, mur de pierre (ishigaki) au pied, allée de
      dix « senbon torii » vermillon (tout ce qui enjambe le couloir est au-dessus de y = 34), lanternes de
      pierre entre les piliers, grand torii d'entrée à plaque 藤 (panneau texte), grande corde sacrée
      (shimenawa) à shide tendue d'une paroi à l'autre au-dessus des torii ;
    - glycines : nuages de blocs sur les corniches, rideaux à l'ourlet irrégulier et grappes effilées en
      dégradé (glycine nuit/foncée → glycine → claire → pâle aux pointes), balcons rocheux fleuris sur les
      grandes faces, touffes sur les petites corniches, glycines bas et cèdres/pins sur les crêtes, deux
      grands glycines retombants qui encadrent la porte ;
    - escaliers de pierre sur des éperons, à petits torii rouges et lanternes : l'un mène à un petit
      sanctuaire (toit de cuivre, chigi, katsuogi, shimenawa), l'autre à un belvédère.
    Si un tirage dépasse le budget, la montagne est reconstruite avec des rideaux un peu moins denses.

train_vapeur (≈ 385 pièces)
    Train de l'ère Taishō à l'arrêt sur un court remblai (herbe, ballast, traverses, rails, heurtoirs) :
    locomotive noire (chaudière cerclée de laiton, porte ronde, phare, cheminée, dômes, roues motrices
    rouges à rayons, bielles, chasse-pierres, panache de vapeur blanche), tender à charbon et voitures
    marron (fenêtres en partie éclairées, toit à lanterneau, plates-formes d'extrémité, bogies). Il suit
    l'axe Z local, le nez de la locomotive vers -Z ; origine au centre de sa longueur, au sol. Aucun texte.
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, rot_x, rot_z, shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Couleurs locales
# ---------------------------------------------------------------------------
TONS = {"N": c("roche_nuit"), "F": c("roche_fonce"), "R": c("roche"), "C": c("roche_claire"),
        "L": mix(c("roche_claire"), c("glycine_pale"), 0.28)}
FISSURE = mix(c("roche_nuit"), c("roche_fonce"), 0.35)
NOYAU = c("roche_fonce")
VERM = c("vermillon")
VERM_F = c("vermillon_fonce")
LAQUE = c("noir_laque")
PIERRE = c("pierre")
PIERRE_F = c("pierre_fonce")
PIERRE_C = c("pierre_claire")

# Couloir : rien au sol pour |x| < 30 ; tout ce qui enjambe |x| < 31 passe au-dessus de y = 34.
X_COULOIR = 30.0
Y_ENJAMBE = 34.0

# Strates : fines lignes sombres et filets clairs entre de gros bancs (face avant, gorge, flancs)
MOTIF = [(6, "F"), (2, "N"), (10, "R"), (2, "L"), (10, "C"), (8, "R"), (2, "N"), (12, "C"), (6, "F"),
         (10, "R"), (2, "L"), (12, "C"), (2, "N"), (8, "R"), (10, "C"), (2, "F")]


def _grossier(motif):
    """Même motif sans les filets fins (fusionnés avec le banc du dessous) : mêmes limites, moins de pièces.
    Sert aux gradins hauts et au dos, vus de loin."""
    out = []
    for e, t in motif:
        if e <= 2 and out:
            out[-1] = (out[-1][0] + e, out[-1][1])
        else:
            out.append((e, t))
    return out


MOTIF_GROS = _grossier(MOTIF)
# Dos (vu de loin depuis la zone suivante) : bancs encore plus épais
MOTIF_DOS = [(18, "F"), (20, "R"), (16, "C"), (20, "R"), (14, "F"), (22, "C"), (18, "R")]


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------
def _q2(v: float) -> float:
    return 2.0 * round(v / 2.0)


def _colonnes(x0: float, x1: float, rng, largeurs) -> list:
    xs = [x0]
    while xs[-1] < x1 - 1e-6:
        nx = xs[-1] + float(rng.choice(largeurs))
        if x1 - nx < min(largeurs) * 0.6:
            nx = x1
        xs.append(nx)
    return list(zip(xs[:-1], xs[1:]))


def _strates(top: float, motif=MOTIF) -> list:
    """Strates horizontales communes : (y0, y1, ton)."""
    out, y, i = [], 0.0, 0
    while y < top:
        e, t = motif[i % len(motif)]
        out.append((y, y + e, t))
        y, i = y + e, i + 1
    return out


class _Face:
    """Paroi : u le long de la paroi, y vers le haut, d = saillie vers l'extérieur de la roche."""

    def __init__(self, b, axis: str, n0: float, sens: int):
        self.b, self.axis, self.n0, self.sens = b, axis, n0, sens

    def pt(self, u, y, d):
        n = self.n0 + self.sens * d
        return (u, y, n) if self.axis == "z" else (n, y, u)

    def box(self, u0, u1, y0, y1, d0, d1, col, **kw):
        return self.b.box(self.pt(u0, y0, d0), self.pt(u1, y1, d1), col, **kw)


def _bandes(box_fn, y0, y1, strates, rng) -> int:
    """Découpe [y0, y1] selon les strates ; box_fn(lo, hi, couleur) pose un bloc par bande."""
    n = 0
    for s0, s1, t in strates:
        lo, hi = max(s0, y0), min(s1, y1)
        if hi - lo > 0.05:
            box_fn(lo, hi, vary(TONS[t], rng, 0.03))
            n += 1
    return n


def _peau(F, u0, u1, y0, y1, strates, rng, saillies=(1.0, 1.5, 2.0, 2.5, 3.0), larg=(6, 8, 10, 12),
          fissures=0.25, coupes=None, coupes_forcees=(), limites=(), gradins=0.55):
    """Masses rocheuses en saillie devant la paroi F (u0 → u1, y0 → y1), recoupées par les strates.

    Les masses d'une même colonne reculent souvent en montant (`gradins`) : petites corniches.
    `limites` : [(y_bas, y_haut, saillie_max)].
    Renvoie (masses [(u0, u1, y0, y1, saillie)], corniches [(u0, u1, y, saillie_haut, saillie_bas)])."""
    masses, replats = [], []
    if y1 - y0 < 0.5 or u1 - u0 < 0.5:
        return masses, replats
    if coupes is None:
        coupes = [s[0] for s in strates if y0 + 6 < s[0] < y1 - 6]
    else:
        coupes = [v for v in coupes if y0 + 6 < v < y1 - 6]
    for c0, c1 in _colonnes(u0, u1, rng, larg):
        subs = [(c0, c1, False)]
        if c1 - c0 >= 9 and rng.random() < fissures:
            xf = c0 + float(rng.integers(3, int(c1 - c0) - 4))
            subs = [(c0, xf, False), (xf, xf + 1.5, True), (xf + 1.5, c1, False)]
        ys = {y0, y1, *[f for f in coupes_forcees if y0 + 0.5 < f < y1 - 0.5]}
        kk = int(rng.integers(1, 4)) if coupes else 0
        if kk:
            ys |= {float(v) for v in rng.choice(coupes, size=min(kk, len(coupes)), replace=False)}
        ys = sorted(ys)
        for a, bb, fiss in subs:
            prev = None
            for m0, m1 in zip(ys[:-1], ys[1:]):
                if fiss:
                    sa = 0.5
                else:
                    sa = float(rng.choice(saillies))
                    if prev is not None and rng.random() < gradins:
                        sa = max(min(saillies), prev - float(rng.choice([1.5, 2.0, 2.5])))
                for l0, l1, smax in limites:
                    if m0 < l1 and m1 > l0:
                        sa = min(sa, smax)
                if prev is not None and not fiss and prev - sa >= 1.25 and bb - a >= 4:
                    replats.append((a, bb, m0, sa, prev))
                prev = sa
                masses.append((a, bb, m0, m1, sa))
                if fiss:
                    F.box(a, bb, m0, m1, 0, sa, vary(FISSURE, rng, 0.03))
                    continue
                _bandes(lambda lo, hi, col: F.box(a, bb, lo, hi, 0, sa, col, studs="top"), m0, m1, strates, rng)
    return masses, replats


def _sa_haut(masses, u0, u1, y) -> float:
    """Saillie maximale des masses dont le dessus est à la hauteur y, entre u0 et u1."""
    best = 0.0
    for a, bb, m0, m1, sa in masses:
        if a < u1 - 1e-6 and bb > u0 + 1e-6 and m0 < y - 1e-6 <= m1:
            best = max(best, sa)
    return best


def _bas_libre(masses, u0, u1, y_top, d) -> float:
    """Plus bas y atteignable par une grappe (u0 → u1) qui pend depuis y_top à la distance d de la paroi."""
    low = -1e9
    for a, bb, m0, m1, sa in masses:
        if a < u1 - 1e-6 and bb > u0 + 1e-6 and sa > d - 0.05 and m0 < y_top:
            low = max(low, min(m1, y_top))
    return low


# ---------------------------------------------------------------------------
# Glycines
# ---------------------------------------------------------------------------
def _grappes(F, u0, u1, y_top, d, rng, masses=(), long_max=10.0, long_min=2.0, ep=0.8, sol=None,
             densite=1.0, larg=(1.5, 2.0, 2.0, 2.5, 3.0)) -> float:
    """Rideau de grappes pendantes devant la paroi F : grappes serrées, effilées, foncées en haut et
    claires à la pointe, de longueurs très variables. Elles s'arrêtent au-dessus des masses rocheuses
    qui avancent davantage (`masses`) et au-dessus de `sol`. Renvoie le plus bas y atteint."""
    y_bas = y_top
    alt = bool(rng.random() < 0.5)
    u = u0 + float(rng.uniform(0.0, 0.3))
    tons = ("glycine_nuit", "glycine_fonce", "glycine", "glycine_claire", "glycine_pale")
    while u < u1 - 0.9:
        w = min(float(rng.choice(larg)), u1 - u)
        if w < 0.9:
            break
        if rng.random() > densite:
            u += w
            continue
        L = long_min + (long_max - long_min) * float(rng.random()) ** 0.6
        dd = d + (0.35 if alt else 0.0)
        alt = not alt
        low = _bas_libre(masses, u, u + w, y_top, dd) if masses else -1e9
        if sol is not None:
            low = max(low, sol)
        L = min(L, y_top - low - 0.3)
        if L >= 1.2:
            t0 = int(rng.choice([0, 1, 1, 1, 2]))
            c1, c2, c3 = tons[t0], tons[t0 + 1], tons[min(3 + (rng.random() < 0.12), t0 + 2)]
            if L < 6.0:
                l1, l2, l3 = round(L * 0.65, 2), 0.0, L - round(L * 0.65, 2)
            else:
                l3 = round(min(2.0, L * 0.2), 2)
                l1 = round((L - l3) * 0.55, 2)
                l2 = L - l1 - l3
            y = y_top
            F.box(u, u + w, y - l1, y, dd, dd + ep, vary(c1, rng, 0.04), collide=False)
            if l2 > 0:
                i2 = 0.25 if w >= 1.5 else 0.1
                F.box(u + i2, u + w - i2, y - l1 - l2, y - l1, dd + 0.05, dd + ep - 0.05, vary(c2, rng, 0.04),
                      collide=False)
            i3 = min(w / 2 - 0.25, 0.5 if w >= 1.5 else 0.25)
            F.box(u + i3, u + w - i3, y - L, y - l1 - l2, dd + 0.12, dd + ep - 0.12, vary(c3, rng, 0.03),
                  collide=False)
            y_bas = min(y_bas, y - L)
        u += w + float(rng.choice([0.0, 0.0, 0.0, 0.3]))
    return y_bas


def _rideau(F, u0, u1, y, d_in, d_out, rng, masses=(), long_max=10.0, sol=None, densite=0.95, ep=0.8,
            pans=(2.5, 3.5, 4.5), larg=(1.5, 2.0, 2.5, 3.0, 3.5)) -> float:
    """Rideau de glycine sous y : pans sombres à l'ourlet irrégulier (de d_in à d_out), puis grappes sous
    chaque pan (devant d_in + 0,1). Renvoie le plus bas y atteint."""
    y_bas = y
    u = u0 + 0.2
    i = 0
    while u < u1 - 0.6:
        ws = min(float(rng.choice(pans)), u1 - 0.2 - u)
        if u1 - 0.2 - (u + ws) < 1.5:
            ws = u1 - 0.2 - u
        hf = float(rng.choice([1.0, 1.5, 2.5, 3.5]))
        if sol is not None:
            hf = min(hf, max(0.5, y - sol - 0.3))
        F.box(u, u + ws, y - hf, y, d_in, d_out, vary(("glycine_nuit", "glycine_fonce")[i % 2], rng, 0.04),
              collide=False)
        y_bas = min(y_bas, y - hf,
                    _grappes(F, u + 0.05, u + ws - 0.05, y - hf, d_in + 0.1, rng, masses, long_max,
                             long_min=min(3.0, long_max), ep=ep, sol=sol, densite=densite, larg=larg))
        u += ws
        i += 1
    return y_bas


def _glycine_corniche(F, u0, u1, y, d_back, d_front, rng, masses=(), long_max=10.0, sol=None, haut=1.0,
                      ov=None, grappes=True, densite=0.95, ov_max=None, devant=True):
    """Masse de glycine posée sur une corniche (dessus à y, de d_back à d_front) : nuage de blocs qui
    déborde, frange sombre, puis rideau de grappes. Le rideau pend devant la roche la plus saillante
    qu'il rencontre (`devant`), sinon il s'arrête au-dessus des masses (obstacles).

    Renvoie l'encombrement du rideau (u0, u1, y_bas, y_haut, d_max) ou None."""
    if u1 - u0 < 3 or d_front - d_back < 1.0:
        return None
    w = u1 - u0
    ov = float(rng.choice([1.5, 2.0, 2.5])) if ov is None else ov
    if grappes and masses and devant:
        reach = y - long_max - 2
        d_c = max([d_front] + [sa for a, bb, m0, m1, sa in masses
                               if a < u1 - 1e-6 and bb > u0 + 1e-6 and m0 < y - 1e-6 and m1 > reach])
    else:
        d_c = d_front
    if ov_max is not None:
        d_c = min(d_c, ov_max - ov)
    h1 = float(rng.choice([3.0, 3.5, 4.0])) * haut
    F.box(u0, u1, y, y + h1, d_back, d_c + ov, vary("glycine_fonce", rng, 0.04), studs="top")
    depth = d_c + ov - d_back
    if w > 4 and depth > 2.5:
        # bosses en nuage, dans des créneaux disjoints (jamais de faces confondues entre bosses)
        nk = min(3, 1 + int(w // 9))
        slot = (w - 1.0) / nk
        for kk in range(nk):
            ww = slot * float(rng.uniform(0.6, 0.95))
            ua = u0 + 0.5 + kk * slot + float(rng.uniform(0, slot - ww))
            e1 = d_c + ov - float(rng.choice([0.3, 0.6, 1.0]))
            e0 = max(d_back + 0.3, e1 - float(rng.uniform(3.0, 6.5)))
            if e1 - e0 < 1.0 or ww < 1.5:
                continue
            h2 = float(rng.choice([1.5, 2.0, 2.5, 3.0])) * haut
            col = ("glycine", "glycine_claire", "glycine")[kk]
            F.box(ua, ua + ww, y + h1, y + h1 + h2, e0, e1, vary(col, rng, 0.04), studs="top")
    if not grappes:
        return None
    ep = max(0.5, min(1.0, ov - 0.85))
    y_bas = _rideau(F, u0, u1, y, d_c + 0.2, d_c + ov - 0.15, rng, masses, long_max, sol, densite, ep)
    return (u0, u1, y_bas, y, d_c + ov)


def _touffe(F, u0, u1, y, d_back, d_front, rng, masses=(), long_max=5.0, sol=None) -> int:
    """Petite touffe de glycine sur une corniche de la peau : bloc bombé et quelques grappes courtes."""
    if u1 - u0 < 2.5:
        return 0
    ov = 1.1
    h = float(rng.choice([1.5, 2.0]))
    F.box(u0, u1, y, y + h, d_back + 0.2, d_front + ov, vary("glycine", rng, 0.05), studs="top", collide=False)
    n = 1
    if u1 - u0 > 4:
        ww = (u1 - u0) * float(rng.uniform(0.4, 0.65))
        ua = u0 + float(rng.uniform(0.3, u1 - u0 - ww - 0.3))
        F.box(ua, ua + ww, y + h, y + h + 1.0, d_back + 0.4, d_front + ov - 0.4, vary("glycine_claire", rng, 0.04),
              studs="top", collide=False)
        n += 1
    _grappes(F, u0 + 0.3, u1 - 0.3, y, d_front + 0.25, rng, masses, long_max, long_min=1.5, ep=0.5, sol=sol,
             densite=0.7, larg=(1.0, 1.5, 2.0))
    return n


def _glycine_arbre(b, x, y, z, rng, s=1.0, rideaux=(), sol=None, long_max=7.0, hx=None, hz=None,
                   densite=0.95, ht=None, xmin=None, xmax=None) -> dict:
    """Glycine en arbre, large et retombant : tronc épais gris-brun coudé, branche, houppier en dôme
    (3 étages décalés) ; rideaux de grappes sous les bords demandés ('avant' = +Z, 'arriere', 'gauche' = -X,
    'droite' = +X). `hx`, `hz` : demi-emprise du houppier (par défaut 9 × 6,5 à l'échelle s)."""
    S = lambda v: v * s  # noqa: E731
    sg = float(rng.choice([-1, 1]))
    xmin = x - 1e9 if xmin is None else xmin
    xmax = x + 1e9 if xmax is None else xmax
    if (x - xmin) > (xmax - x):
        sg = 1.0   # la branche part vers le côté le plus dégagé (-sg)
    elif (xmax - x) > (x - xmin):
        sg = -1.0
    ht = S(5.0) if ht is None else ht
    b.box((x - S(1.2), y, z - S(1.2)), (x + S(1.2), y + ht * 0.55, z + S(1.2)), vary("tronc", rng, 0.05))
    b.box((x + sg * S(0.7) - S(0.9), y + ht * 0.55, z - S(0.9)), (x + sg * S(0.7) + S(0.9), y + ht + 0.4, z + S(0.9)),
          vary("tronc", rng, 0.05))
    lb = min(S(4.0), (x - xmin - 0.3) if sg > 0 else (xmax - x - 0.3))
    if lb > S(1.5):
        b.box((x - sg * lb, y + ht * 0.62, z - S(0.6)), (x + sg * S(0.2), y + ht * 0.62 + S(1.0), z + S(0.6)),
              c("tronc_clair"))
    yc = y + ht
    hx = S(9.0) if hx is None else hx
    hz = S(6.5) if hz is None else hz
    b.box((x - hx, yc, z - hz), (x + hx, yc + S(2.6), z + hz), vary("glycine_fonce", rng, 0.04), studs="top")
    # bosses en nuage dans des créneaux disjoints, la plus haute éclaircie
    slot = (2 * hx - 1.0) / 3
    hauts = [S(float(rng.choice([2.0, 2.5]))), S(float(rng.choice([3.0, 3.5]))), S(float(rng.choice([2.0, 2.5])))]
    rng.shuffle(hauts)
    for kk in range(3):
        ww = slot * float(rng.uniform(0.7, 0.95))
        ua = x - hx + 0.5 + kk * slot + float(rng.uniform(0, slot - ww))
        dd = 2 * hz * float(rng.uniform(0.55, 0.85))
        za = z - hz + 0.4 + float(rng.uniform(0, 2 * hz - 0.8 - dd))
        col = "glycine_claire" if hauts[kk] == max(hauts) else "glycine"
        b.box((ua, yc + S(2.6), za), (ua + ww, yc + S(2.6) + hauts[kk], za + dd), vary(col, rng, 0.04), studs="top")
        if hauts[kk] == max(hauts) and ww > 3:
            b.box((ua + ww * 0.25, yc + S(2.6) + hauts[kk], za + dd * 0.25),
                  (ua + ww * 0.75, yc + S(2.6) + hauts[kk] + S(1.2), za + dd * 0.75), vary("glycine_pale", rng, 0.03),
                  studs="top")
    sol = y + 1.2 if sol is None else sol
    faces = {"avant": ("z", z + hz, 1, x - hx, x + hx), "arriere": ("z", z - hz, -1, x - hx, x + hx),
             "gauche": ("x", x - hx, -1, z - hz, z + hz), "droite": ("x", x + hx, 1, z - hz, z + hz)}
    for nom in rideaux:
        axis, n0, sens, u0, u1 = faces[nom]
        F = _Face(b, axis, n0, sens)
        F.box(u0 + 1.4, u1 - 1.4, yc - 1.0, yc, -1.4, -0.3, vary("glycine_nuit", rng, 0.04), collide=False)
        _grappes(F, u0 + 1.5, u1 - 1.5, yc - 1.0, -1.25, rng, (), min(long_max, yc - 1.0 - sol), long_min=2.0,
                 ep=0.8, sol=sol, densite=densite, larg=(1.0, 1.5, 2.0, 2.5))
    return {"rayon_x": hx, "rayon_z": hz, "hauteur": ht + S(7.3)}


def _glycine_maitre(b, x, y, z, rng, cotes=("avant",), densite=0.95) -> dict:
    """Grand glycine retombant, arbre remarquable au pied de la montagne : tronc tordu en trois tronçons
    et deux branches maîtresses, houppier en dôme (l'étage du milieu est le plus large), grappes longues
    à l'ourlet irrégulier jusque près du sol sur les côtés vus (`cotes` : 'avant' = +Z, 'gauche' = -X,
    'droite' = +X, 'arriere')."""
    for dx, y0, dz, w, h in ((0.0, 0.0, 0.0, 2.8, 3.4), (0.8, 3.4, 0.4, 2.4, 3.0), (0.1, 6.4, -0.3, 2.1, 3.2)):
        b.box((x + dx - w / 2, y + y0, z + dz - w / 2), (x + dx + w / 2, y + y0 + h, z + dz + w / 2),
              vary("tronc", rng, 0.06))
    for sx in (-1, 1):  # branches maîtresses vers les bords du houppier
        a, bb = sorted((x + sx * 1.0, x + sx * 5.5))
        b.box((a, y + 7.6, z - 0.6), (bb, y + 8.6, z + 0.6), c("tronc_clair"))
        a, bb = sorted((x + sx * 4.5, x + sx * 6.5))
        b.box((a, y + 8.6, z - 0.6), (bb, y + 9.4, z + 0.6), c("tronc_clair"))
    yc = y + 9.4
    hx, hz = 12.0, 9.0
    b.box((x - 8.0, yc, z - 6.0), (x + 8.0, yc + 2.0, z + 6.0), vary("glycine_fonce", rng, 0.04), studs="top")
    b.box((x - hx, yc + 2.0, z - hz), (x + hx, yc + 4.4, z + hz), vary("glycine_fonce", rng, 0.03), studs="top")
    dx = float(rng.uniform(-1.5, 1.5))
    b.box((x + dx - 8.5, yc + 4.4, z - 6.5), (x + dx + 8.5, yc + 6.4, z + 6.5), vary("glycine", rng, 0.04),
          studs="top")
    slot = 16.0 / 3
    for kk, (hh, col) in enumerate(((1.4, "glycine"), (2.2, "glycine_claire"), (1.6, "glycine"))):
        ww = slot * float(rng.uniform(0.7, 0.95))
        ua = x + dx - 8.0 + kk * slot + float(rng.uniform(0, slot - ww))
        dd = float(rng.uniform(6.0, 9.5))
        za = z - 6.0 + float(rng.uniform(0, 12.0 - dd))
        b.box((ua, yc + 6.4, za), (ua + ww, yc + 6.4 + hh, za + dd), vary(col, rng, 0.04), studs="top")
    faces = {"avant": ("z", z + hz, 1, x - hx, x + hx), "arriere": ("z", z - hz, -1, x - hx, x + hx),
             "gauche": ("x", x - hx, -1, z - hz, z + hz), "droite": ("x", x + hx, 1, z - hz, z + hz)}
    for nom in cotes:
        axis, n0, sens, u0, u1 = faces[nom]
        F = _Face(b, axis, n0, sens)
        _rideau(F, u0 + 2.0, u1 - 2.0, yc + 2.0, -1.8, -0.3, rng, (), long_max=yc + 2.0 - 1.0 - (y + 1.4),
                sol=y + 1.4, densite=densite, ep=0.8, pans=(2.0, 3.0, 4.0), larg=(1.0, 1.5, 2.0, 2.5))
    return {"rayon_x": hx, "rayon_z": hz, "hauteur": 18.0}


# ---------------------------------------------------------------------------
# Végétation
# ---------------------------------------------------------------------------
def _pin(b, x, y, z, rng, s=1.0) -> None:
    """Pin japonais : tronc coudé, plateaux de feuillage en nuages."""
    sg = float(rng.choice([-1, 1]))
    S = lambda v: v * s  # noqa: E731
    vert, vert_c = vary("pin", rng, 0.05), vary(mix(c("pin"), c("feuille"), 0.45), rng, 0.04)
    b.box((x - S(0.6), y, z - S(0.6)), (x + S(0.6), y + S(5.5), z + S(0.6)), c("tronc"))
    b.box((x - sg * S(0.5) - S(0.5), y + S(5.5), z - S(0.5)), (x - sg * S(0.5) + S(0.5), y + S(8.6), z + S(0.5)),
          c("tronc_clair"))
    b.box((x + sg * S(2.0) - S(3.3), y + S(4.4), z - S(2.6)), (x + sg * S(2.0) + S(3.3), y + S(5.8), z + S(2.6)),
          vert, studs="top", collide=False)
    b.box((x - sg * S(1.0) - S(2.6), y + S(6.6), z - S(2.1)), (x - sg * S(1.0) + S(2.6), y + S(8.0), z + S(2.1)),
          vert_c, studs="top", collide=False)
    b.box((x - sg * S(0.3) - S(1.6), y + S(8.6), z - S(1.4)), (x - sg * S(0.3) + S(1.6), y + S(9.8), z + S(1.4)),
          vert, studs="top", collide=False)


def _cedre(b, x, y, z, rng, s=1.0) -> None:
    """Cèdre (sugi) : tronc et étages carrés qui rétrécissent, silhouette pointue."""
    S = lambda v: v * s  # noqa: E731
    b.box((x - S(0.6), y, z - S(0.6)), (x + S(0.6), y + S(3.0), z + S(0.6)), c("tronc"))
    yy = y + S(2.4)
    for i, w in enumerate((6.4, 5.0, 3.6, 2.2)):
        h = S(2.6 if i < 3 else 2.2)
        col = vary(mix(c("pin"), c("feuille_fonce"), 0.3 * (i % 2)), rng, 0.04)
        b.box((x - S(w / 2), yy, z - S(w / 2)), (x + S(w / 2), yy + h, z + S(w / 2)), col, studs="top", collide=i == 0)
        yy += h
    b.box((x - S(0.5), yy, z - S(0.5)), (x + S(0.5), yy + S(1.4), z + S(0.5)), vary("pin", rng, 0.04), studs="top",
          collide=False)


# ---------------------------------------------------------------------------
# Torii et lanternes
# ---------------------------------------------------------------------------
def _torii(b, z, y0, demi, r, yn, hn, ys, hs, hk, ext=(1.0, 1.6, 2.4), hup=1.0, prof=1.0, xc=0.0, carre=False,
           tip=0.4) -> dict:
    """Torii vermillon : piliers en xc ± demi (pied à y0), nuki, gakuzuka, shimaki rouge, kasagi noir relevé.

    Hauteurs (yn, ys) relatives à y0 ; poutres le long de X, épaisseur `prof` le long de Z."""
    xo = demi + r
    hb = max(1.2, 1.5 * r)
    for sx in (-1, 1):
        x = xc + sx * demi
        if carre:
            b.box((x - r, y0 + hb * 0.5, z - r), (x + r, y0 + ys, z + r), VERM)
            b.box((x - r * 1.2, y0, z - r * 1.2), (x + r * 1.2, y0 + hb, z + r * 1.2), LAQUE, studs="top")
        else:
            b.cyl((x, y0 + (hb * 0.5 + ys) / 2, z), r, ys - hb * 0.5, VERM)
            b.cyl((x, y0 + hb / 2, z), r * 1.18, hb, LAQUE, studs="top")
    b.box((xc - xo - ext[0], y0 + yn, z - prof * 0.5), (xc + xo + ext[0], y0 + yn + hn, z + prof * 0.5), VERM)
    wg = max(0.5, r * 0.7)
    b.box((xc - wg, y0 + yn + hn, z - prof * 0.38), (xc + wg, y0 + ys, z + prof * 0.38), VERM)
    b.box((xc - xo - ext[1], y0 + ys, z - prof * 0.6), (xc + xo + ext[1], y0 + ys + hs, z + prof * 0.6), VERM)
    yk = y0 + ys + hs
    xk = xo + ext[2]
    b.box((xc - xk, yk, z - prof * 0.75), (xc + xk, yk + hk, z + prof * 0.75), LAQUE, studs="top")
    lw = min(6.0, xk * 0.25)
    b.wedge((xc + xk - lw, yk + hk, z - prof * 0.75), (xc + xk + tip, yk + hk + hup, z + prof * 0.75), LAQUE,
            down="-x", studs="top")
    b.wedge((xc - xk - tip, yk + hk, z - prof * 0.75), (xc - xk + lw, yk + hk + hup, z + prof * 0.75), LAQUE,
            down="+x", studs="top")
    return {"x_ext": xk + tip, "y_haut": yk + hk + hup}


def _lanterne(b, x, y, z, s=1.0) -> None:
    """Lanterne de pierre (tōrō) : socle, fût, plateau, foyer lumineux, toit, pointe (7 pièces)."""
    S = lambda v: v * s  # noqa: E731
    b.box((x - S(1.4), y, z - S(1.4)), (x + S(1.4), y + S(1.0), z + S(1.4)), PIERRE_F, studs="top")
    b.box((x - S(0.6), y + S(1.0), z - S(0.6)), (x + S(0.6), y + S(4.0), z + S(0.6)), PIERRE)
    b.box((x - S(1.2), y + S(4.0), z - S(1.2)), (x + S(1.2), y + S(4.7), z + S(1.2)), PIERRE_F, studs="top")
    b.box((x - S(0.85), y + S(4.7), z - S(0.85)), (x + S(0.85), y + S(6.3), z + S(0.85)), c("orange_lampion"),
          material="Neon", collide=False)
    b.box((x - S(1.6), y + S(6.3), z - S(1.6)), (x + S(1.6), y + S(7.0), z + S(1.6)), PIERRE_F, studs="top")
    b.box((x - S(0.9), y + S(7.0), z - S(0.9)), (x + S(0.9), y + S(7.6), z + S(0.9)), PIERRE, studs="top")
    b.ball((x, y + S(8.0), z), S(0.45), PIERRE)


# ---------------------------------------------------------------------------
# Escaliers, sanctuaire, belvédère
# ---------------------------------------------------------------------------
def _volees(montee_totale: float) -> list:
    """Découpe une montée en volées de 14 marches au plus."""
    n = int(round(montee_totale))
    out = []
    while n > 0:
        out.append(min(14, n))
        n -= out[-1]
    return out


def _plan_escalier(z_bas, volees, montee=1.0, giron=1.1, palier=4.0):
    """Profil d'un escalier qui monte vers -Z : [(type, z_avant, z_arriere, y_bas, y_haut)], z et y d'arrivée."""
    segs = []
    z, y = z_bas, 0.0
    for i, n in enumerate(volees):
        segs.append(("volee", z, z - n * giron, y, y + n * montee))
        z, y = z - n * giron, y + n * montee
        if i < len(volees) - 1:
            segs.append(("palier", z, z - palier, y, y))
            z -= palier
    return segs, z, y


def _y_escalier(segs, z) -> float:
    """Hauteur du dessus de l'escalier en z (0 devant le pied)."""
    for kind, z0, z1, y0, y1 in segs:
        if z1 - 1e-6 <= z <= z0 + 1e-6:
            if kind == "palier":
                return y0
            return y0 + (z0 - z) / (z0 - z1) * (y1 - y0)
    return 0.0 if z > segs[0][1] else segs[-1][4]


def _escalier(b, xc, segs, rng, demi_col=9.0, demi_marche=4.5, giron=1.1, montee=1.0) -> None:
    """Escalier de pierre vers -Z centré en xc : remblai (pierre devant la falaise, roche à strates dedans),
    talus moussus, marches claires, garde-corps inclinés."""
    x0, x1 = xc - demi_col, xc + demi_col
    ang = math.degrees(math.atan2(montee, giron))
    for kind, z0, z1, y0, y1 in segs:
        for za, zb, dedans in ((max(z1, 0.0), z0, False), (z1, min(z0, 0.0), True)):
            if za >= zb - 1e-6:
                continue
            ya = y0 + (z0 - zb) / (z0 - z1) * (y1 - y0) if kind == "volee" else y0
            yb = y0 + (z0 - za) / (z0 - z1) * (y1 - y0) if kind == "volee" else y0
            if ya > 0.05:
                b.box((x0, 0, za), (x1, ya, zb), NOYAU if dedans else vary(PIERRE_F, rng, 0.03), studs="top")
            if kind == "volee" and yb - ya > 0.05:
                b.wedge((x0, ya, za), (x1, yb, zb), vary("mousse" if dedans else PIERRE_F, rng, 0.04), down="+z",
                        studs="top")
        if kind == "volee":
            n = int(round((y1 - y0) / montee))
            for i in range(n):
                za = z0 - (i + 1) * giron
                col = PIERRE_C if i % 2 == 0 else PIERRE
                b.box((xc - demi_marche, y0 + i * montee, za), (xc + demi_marche, y0 + (i + 1) * montee, za + giron),
                      vary(col, rng, 0.03), studs="top")
            L = math.hypot(z0 - z1, y1 - y0)
            ym, zm = (y0 + y1) / 2, (z0 + z1) / 2
            nz, ny = math.sin(math.radians(ang)), math.cos(math.radians(ang))  # normale de la pente
            for sx in (-1, 1):
                xp = xc + sx * (demi_marche + 0.45)
                b.part("block", (0.9, 1.3, L - 0.6), (xp, ym + ny * 0.45, zm + nz * 0.45), rot_x(ang), PIERRE_F)


def _sanctuaire(b, xc, y, zc, rng) -> None:
    """Petit sanctuaire (honden) tourné vers +Z : socle de pierre, piliers vermillon, murs blancs,
    portes à treillis, toit de cuivre à deux pans débordants, chigi et katsuogi, shimenawa à shide."""
    W2, D2 = 6.0, 4.0
    z0, z1 = zc - D2, zc + D2
    b.box((xc - W2 - 1, y, z0 - 1), (xc + W2 + 1, y + 1.2, z1 + 1.5), PIERRE_F, studs="top")
    b.box((xc - 2.2, y, z1 + 1.5), (xc + 2.2, y + 0.6, z1 + 2.7), PIERRE, studs="top")
    yf = y + 1.2
    b.box((xc - W2, yf, z0), (xc + W2, yf + 1.0, z1), c("bois_fonce"), studs="top")
    yf += 1.0
    yh = yf + 7.0
    b.box((xc - W2 + 0.6, yf, z0 + 0.6), (xc + W2 - 0.6, yh, z1 - 2.6), vary("enduit", rng, 0.02))
    # portes à treillis (avant = +Z)
    b.box((xc - W2 + 1.2, yf, z1 - 2.6), (xc + W2 - 1.2, yf + 5.6, z1 - 2.3), c("bois_fonce"))
    for i in range(5):
        xx = xc - W2 + 2.0 + i * (2 * W2 - 4.0) / 4
        b.box((xx - 0.15, yf + 0.3, z1 - 2.3), (xx + 0.15, yf + 5.3, z1 - 2.15), c("or"), collide=False)
    b.box((xc - W2 + 1.2, yf + 5.6, z1 - 2.6), (xc + W2 - 1.2, yh, z1 - 2.45), vary("enduit", rng, 0.02))
    for xx in (xc - W2 + 0.6, xc + W2 - 0.6):
        for zz in (z0 + 0.6, z1 - 0.6):
            b.box((xx - 0.5, yf, zz - 0.5), (xx + 0.5, yh, zz + 0.5), VERM)
    b.box((xc - W2, yh, z0), (xc + W2, yh + 0.8, z1), VERM_F)
    yt = yh + 0.8
    zm = (z0 + z1) / 2
    toit = c("cuivre_vert")
    b.wedge((xc - W2 - 1.6, yt, zm), (xc + W2 + 1.6, yt + 4.2, z1 + 2.6), toit, down="+z", studs="top")
    b.wedge((xc - W2 - 1.6, yt, z0 - 2.2), (xc + W2 + 1.6, yt + 4.2, zm), shade(toit, 0.9), down="-z", studs="top")
    b.box((xc - W2 - 1.8, yt + 4.2, zm - 0.6), (xc + W2 + 1.8, yt + 4.9, zm + 0.6), LAQUE, studs="top")
    for xx in (xc - W2 + 0.1, xc + W2 - 0.3):
        b.wedge((xx, yt, zm), (xx + 0.2, yt + 3.8, z1 - 0.2), vary("enduit", rng, 0.02), down="+z")
        b.wedge((xx, yt, z0 + 0.2), (xx + 0.2, yt + 3.8, zm), vary("enduit", rng, 0.02), down="-z")
    for dx in (-3.0, 0.0, 3.0):
        b.cyl((xc + dx, yt + 5.3, zm), 0.4, 1.8, c("or"), axis="z")
    for sx in (-1, 1):
        for sz in (-1, 1):
            b.part("block", (0.3, 4.2, 0.6), (xc + sx * (W2 + 1.95), yt + 4.6, zm + sz * 0.7), rot_x(sz * 32.0), LAQUE)
    b.cyl((xc, yh - 0.6, z1 + 0.4), 0.45, 2 * W2 - 2.0, c("corde"), axis="x", collide=False)
    for i in range(4):
        xx = xc - W2 + 2.5 + i * (2 * W2 - 5.0) / 3
        b.box((xx - 0.3, yh - 2.4, z1 + 0.35), (xx + 0.3, yh - 1.05, z1 + 0.45), c("shide"), collide=False)
        b.box((xx + 0.1, yh - 3.2, z1 + 0.35), (xx + 0.7, yh - 2.4, z1 + 0.45), c("shide"), collide=False)
    b.box((xc - 1.8, yf, z1 + 0.2), (xc + 1.8, yf + 1.6, z1 + 1.6), c("bois"), studs="top")


def _pavillon(b, xc, y, zc, rng) -> None:
    """Belvédère : petit pavillon ouvert (4 piliers vermillon, toit de tuiles bleu nuit à deux pans), banc."""
    W2, D2 = 4.5, 3.5
    z0, z1 = zc - D2, zc + D2
    b.box((xc - W2 - 0.8, y, z0 - 0.8), (xc + W2 + 0.8, y + 0.8, z1 + 0.8), PIERRE_F, studs="top")
    yf = y + 0.8
    for xx in (xc - W2 + 0.5, xc + W2 - 0.5):
        for zz in (z0 + 0.5, z1 - 0.5):
            b.box((xx - 0.45, yf, zz - 0.45), (xx + 0.45, yf + 6.5, zz + 0.45), VERM)
    b.box((xc - W2, yf + 6.5, z0), (xc + W2, yf + 7.2, z1), VERM_F)
    yt = yf + 7.2
    zm = (z0 + z1) / 2
    b.wedge((xc - W2 - 1.4, yt, zm), (xc + W2 + 1.4, yt + 3.2, z1 + 1.8), c("tuile"), down="+z", studs="top")
    b.wedge((xc - W2 - 1.4, yt, z0 - 1.8), (xc + W2 + 1.4, yt + 3.2, zm), c("tuile_fonce"), down="-z", studs="top")
    b.box((xc - W2 - 1.6, yt + 3.2, zm - 0.5), (xc + W2 + 1.6, yt + 3.8, zm + 0.5), c("tuile_claire"), studs="top")
    b.box((xc - 2.5, yf, z0 + 0.8), (xc + 2.5, yf + 1.4, z0 + 1.8), c("bois_moyen"), studs="top")


# ---------------------------------------------------------------------------
# Montagne
# ---------------------------------------------------------------------------
BUDGET_MONTAGNE = 3150


def montagne_glycines(b, variant: int = 0, passage: float = 68, largeur: float = 440, profondeur: float = 68,
                      hauteur: float = 120) -> dict:
    """Montagne aux glycines traversée par une gorge à ciel ouvert (allée de senbon torii).

    variant : 0/2 sanctuaire à droite (+x) et belvédère à gauche, 1/3 l'inverse ; 2 et 3 changent le tirage.
    Si le tirage dépasse le budget de pièces, la montagne est reconstruite avec des rideaux de glycines un peu
    moins denses (même plan, même roche)."""
    n0 = len(b.parts)
    for dens in (1.0, 0.88, 0.76, 0.64, 0.52, 0.4):
        info = _montagne(b, variant, passage, largeur, profondeur, hauteur, dens)
        if len(b.parts) - n0 <= BUDGET_MONTAGNE or dens <= 0.4:
            break
        del b.parts[n0:]
    info["pieces"] = len(b.parts) - n0
    info.update(_mesures(b, n0))
    return info


def _mesures(b, n0) -> dict:
    """Hauteur réelle (arbres compris) et débord avant, mesurés sur les pièces posées (repère de l'asset)."""
    R = np.asarray(b._R[-1])
    t = np.asarray(b._t[-1])
    y_max, z_max = 0.0, 0.0
    for p in b.parts[n0:]:
        Rp = np.asarray(p.rot).reshape(3, 3)
        half = np.abs(Rp) @ (np.asarray(p.size) / 2)
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    q = R.T @ (np.asarray(p.pos) + np.array([sx, sy, sz]) * half - t)
                    y_max, z_max = max(y_max, q[1]), max(z_max, q[2])
    return {"hauteur": round(float(y_max), 1), "debord_avant": round(float(z_max), 1)}


def _montagne(b, variant, passage, largeur, profondeur, hauteur, dens) -> dict:
    rng = np.random.default_rng(4407 + 131 * variant)
    DENS = 0.95 * dens
    s_main = 1 if variant % 2 == 0 else -1
    P = passage / 2
    W = largeur / 2
    D = profondeur
    H = hauteur
    k = H / 120.0

    # -- repères de la gorge -----------------------------------------------------
    R_PIL = 1.3
    X_PIL = max(32.0 + R_PIL, P - 0.6)            # axe des piliers des senbon torii (face intérieure ≥ 32)
    G0 = max(P + 5.0, X_PIL + R_PIL + 4.3)        # pied des parois de la gorge (39 par défaut)
    GS = [G0, G0 + 5, G0 + 10, G0 + 16]           # gradins de la gorge (tranches parallèles au couloir)
    CAPS = [max(50.0, _q2(52 * k)), max(64.0, _q2(78 * k)), max(76.0, _q2(104 * k))]
    Y_ISHI = 8.0                                  # mur de pierre au pied des parois
    Y_KASA = 42.6                                 # au-dessus des kasagi des senbon torii (bouts relevés compris)
    ZBK = -D + 2.5                                # plan du dos (la peau arrière déborde jusqu'à -D)
    strates = _strates(H + 40)
    strates_gros = _strates(H + 40, MOTIF_GROS)
    strates_dos = _strates(H + 40, MOTIF_DOS)

    # -- escaliers --------------------------------------------------------------
    esc = {}
    for s, kind, frac, yt, zbas, prof_t in ((s_main, "sanctuaire", 0.46, _q2(40 * k), 14.0, 18.0),
                                            (-s_main, "belvedere", 0.64, _q2(28 * k), 12.0, 14.0)):
        while True:
            segs, zt0, _ = _plan_escalier(zbas, _volees(yt))
            if zt0 - prof_t >= ZBK + 4 or yt <= 8:
                break
            yt -= 2
        esc[s] = {"u": _q2(frac * W), "segs": segs, "zt0": zt0, "zt1": zt0 - prof_t, "yt": yt, "type": kind}

    # -- colonnes (repère monde) -----------------------------------------------------
    cols = []
    for s in (1, -1):
        e = esc[s]
        us = e["u"]
        LARG = (10, 12, 14, 16, 18)
        decoupe = _colonnes(GS[3], us - 9, rng, LARG) + [(us - 9, us + 9)] + _colonnes(us + 9, W, rng, LARG)
        # groupes de colonnes qui partagent leurs corniches (rideaux de glycines continus)
        massif = []
        reste, prec = 0.0, None
        for a, bb in decoupe:
            um = (a + bb) / 2
            kind = "escalier" if abs(um - us) < 1e-6 else "massif"
            v = min(1.0, max(0.0, (um - GS[3]) / (W - GS[3])))
            if reste <= 1e-6 or "escalier" in (kind, prec):
                reste = float(rng.choice([28, 36, 44, 52]))
                gA = H * (0.46 - 0.28 * v) + float(rng.choice([-4, -2, 0, 2, 4, 6])) * k
                gB = H * (0.80 - 0.38 * v) + float(rng.choice([-6, -2, 2, 6])) * k
                if a <= GS[3] + 1e-6:  # le premier groupe encadre la gorge
                    gA, gB = max(gA, CAPS[0]), max(gB, CAPS[0] + 24 * k)
                gZA = -_q2(D * float(rng.choice([0.18, 0.21, 0.24])))
                gZB = gZA - _q2(D * float(rng.choice([0.18, 0.21, 0.24])))
            reste -= bb - a
            prec = kind
            if v < 0.3:
                tC = H - float(rng.choice([0, 2, 4, 6, 8, 10])) * k
            else:
                tC = H * (1 - 0.5 * (v - 0.3) / 0.7) + float(rng.choice([-6, -2, 0, 2, 4])) * k
            if v < 0.4 and bb - a <= 14 and rng.random() < 0.3:
                tC += 12 * k  # aiguille rocheuse
            tB = min(gB, tC - 12 * k)
            tA = min(max(min(gA, tB - 14 * k), 16 * k), 64 * k)
            tD = tC - float(rng.choice([16, 20, 24])) * k
            ZC = ZBK + _q2(D * float(rng.choice([0.15, 0.18])))
            massif.append({"u0": a, "u1": bb, "kind": kind, "side": s,
                           "t": [_q2(tA), _q2(tB), _q2(tC), _q2(tD)], "z": [0.0, gZA, gZB, ZC, ZBK]})
        # voisins de l'escalier : éperon peu encaissé (juste au-dessus des marches), fond haut
        for m in massif:
            if m["kind"] != "massif":
                continue
            if min(abs(m["u0"] - (us + 9)), abs(m["u1"] - (us - 9))) < 1e-6:
                zs = m["z"]
                for j in range(4):
                    ymax = max(_y_escalier(e["segs"], zz) for zz in np.linspace(zs[j + 1], zs[j], 6))
                    if zs[j + 1] < e["zt0"]:
                        ymax = max(ymax, e["yt"] + (6 if j < 2 else 24))
                    m["t"][j] = _q2(ymax + 3) if j < 2 else max(m["t"][j], _q2(ymax + 3))
                m["t"][2] = max(m["t"][2], m["t"][1] + 16)
                m["t"][3] = min(m["t"][3], m["t"][2])
        # tranches de la gorge : mêmes gradins que le premier massif, hauteurs plafonnées
        m0 = massif[0]
        tranches = [{"u0": GS[i], "u1": GS[i + 1], "kind": f"gorge{i}", "side": s,
                     "t": [min(t, CAPS[i]) for t in m0["t"]], "z": list(m0["z"])} for i in range(3)]
        for m in tranches + massif:
            m["x0"], m["x1"] = sorted((s * m["u0"], s * m["u1"]))
            cols.append(m)
    cols.sort(key=lambda m: m["x0"])

    def h_col(m, za, zb):
        """Hauteur minimale de la colonne m entre zb et za (za > zb)."""
        if m["kind"] == "escalier":
            e = esc[m["side"]]
            hs = []
            if za > e["zt0"] + 1e-6:
                hs.append(min(_y_escalier(e["segs"], z) for z in np.linspace(max(zb, e["zt0"]), za, 6)))
            if za > e["zt1"] + 1e-6 and zb < e["zt0"] - 1e-6:
                hs.append(e["yt"])
            if zb < e["zt1"] - 1e-6:
                hs.append(m["t"][2])
            return min(hs) if hs else 0.0
        hs = [m["t"][j] for j in range(4) if m["z"][j + 1] < za - 1e-6 and m["z"][j] > zb + 1e-6]
        return min(hs) if hs else 0.0

    def h_max(m, za, zb):
        """Hauteur maximale de la colonne m entre zb et za (za > zb), arbres et glycines non compris."""
        if m["kind"] == "escalier":
            return 1e9  # pas de houppier au-dessus d'un escalier (fond rocheux et ses glycines)
        hs = [m["t"][j] for j in range(4) if m["z"][j + 1] < za - 1e-6 and m["z"][j] > zb + 1e-6]
        return max(hs) if hs else 0.0

    F_av = _Face(b, "z", 0.0, 1)
    F_dos = _Face(b, "z", ZBK, -1)
    peaux_av, peaux_dos, replats_av = {}, {}, []

    with b.group("Roche"):
        for i, m in enumerate(cols):
            gauche = cols[i - 1] if i > 0 and abs(cols[i - 1]["x1"] - m["x0"]) < 1e-6 else None
            droite = cols[i + 1] if i + 1 < len(cols) and abs(cols[i + 1]["x0"] - m["x1"]) < 1e-6 else None
            s = m["side"]
            x0, x1 = m["x0"], m["x1"]
            if m["kind"] == "escalier":
                e = esc[s]
                with b.group("Escaliers"):
                    _escalier(b, s * e["u"], e["segs"], rng)
                # terrasse (gravier) puis fond rocheux
                b.box((x0, 0, e["zt1"]), (x1, e["yt"] - 0.4, e["zt0"]), NOYAU)
                b.box((x0, e["yt"] - 0.4, e["zt1"]), (x1, e["yt"], e["zt0"]), vary("gravier", rng, 0.03), studs="top")
                hb = m["t"][2]
                b.box((x0, 0, ZBK), (x1, e["yt"], e["zt1"]), NOYAU)
                _bandes(lambda lo, hi, col: b.box((x0, lo, ZBK), (x1, hi, e["zt1"]), col, studs="top"),
                        e["yt"], hb, strates_gros, rng)
                _peau(F_dos, x0, x1, 0, hb, strates_dos, rng, saillies=(1.0, 1.5, 2.0, 2.5), larg=(14, 18, 22),
                      fissures=0.0, gradins=0.3, coupes=())
                continue
            interieur = m["kind"] == "gorge0"
            for j in range(4):
                za, zb, h = m["z"][j], m["z"][j + 1], m["t"][j]
                av = h if j == 0 else m["t"][j - 1]
                ar = h if j == 3 else m["t"][j + 1]
                hg = h if (interieur and s > 0) else (h_col(gauche, za, zb) if gauche else 0.0)
                hd = h if (interieur and s < 0) else (h_col(droite, za, zb) if droite else 0.0)
                ylo = max(0.0, min(av, ar, hg, hd, h))
                if ylo > 0.05:
                    b.box((x0, 0, zb), (x1, ylo, za), NOYAU)
                _bandes(lambda lo, hi, col: b.box((x0, lo, zb), (x1, hi, za), col, studs="top"), ylo, h,
                        strates if j < 2 else strates_gros, rng)
            # peau avant (tranches de la gorge et premier massif : saillie limitée pour dégager le grand torii)
            pres = m["kind"].startswith("gorge") or min(abs(x0), abs(x1)) < GS[3] + 1
            sail = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0) if pres else (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0)
            masses, replats = _peau(F_av, x0, x1, 0, m["t"][0], strates, rng, saillies=sail,
                                    larg=(5, 6, 8) if m["kind"].startswith("gorge") else (8, 10, 12, 14))
            peaux_av[i] = masses
            replats_av += [(r, masses) for r in replats]
            pres_sortie = min(abs(x0), abs(x1)) <= GS[3] + 24
            peaux_dos[i] = _peau(F_dos, x0, x1, 0, m["t"][3], strates_dos, rng,
                                 saillies=(0.5, 1.0) if pres_sortie else (1.0, 1.5, 2.0, 2.5),
                                 larg=(14, 18, 22), fissures=0.0, gradins=0.3, coupes=())[0]

    # -- gorge : parois, mur de pierre, allée -------------------------------------------
    gorge = {}
    with b.group("Gorge"):
        for s in (1, -1):
            F_g = _Face(b, "x", s * G0, -s)
            g0 = next(m for m in cols if m["kind"] == "gorge0" and m["side"] == s)
            masses, replats = [], []
            for j in range(4):
                za, zb, h = g0["z"][j], g0["z"][j + 1], g0["t"][j]
                ms, rp = _peau(F_g, zb, za, Y_ISHI, h, strates, rng, saillies=(1.0, 1.5, 2.0, 2.5),
                               larg=(6, 8, 10, 12), fissures=0.3, coupes_forcees=(28.0, Y_KASA + 1.4),
                               limites=((28.0, Y_KASA + 1.4, 0.75),))
                masses += ms
                replats += rp
            gorge[s] = (F_g, masses, replats)
            # ishigaki : deux assises de pierres de longueurs variées + couronnement
            for (y0, y1) in ((0.0, 3.5), (3.5, 7.0)):
                zz = -D
                while zz < -1e-6:
                    zn = min(0.0, zz + float(rng.choice([4, 5, 6, 7, 8])))
                    if -zn < 3:
                        zn = 0.0
                    F_g.box(zz, zn, y0, y1, 0, 0.5, vary(PIERRE if rng.random() < 0.6 else PIERRE_F, rng, 0.04))
                    zz = zn
            F_g.box(-D, 0, 7.0, Y_ISHI, 0, 0.9, vary(PIERRE_C, rng, 0.02), studs="top")
            # allée de pierre au pied des piliers (hors couloir)
            xa, xb = sorted((s * (X_COULOIR + 1.0), s * (G0 - 0.5)))
            b.box((xa, 0, -D), (xb, 0.4, 0), vary("gravier", rng, 0.02), studs="top")

    # -- torii --------------------------------------------------------------------------
    n_torii = 0
    with b.group("Torii"):
        pas = 7.0
        zs = [-3.0 - pas * i for i in range(int(D // pas) + 1) if 3.0 + pas * i <= D - 1.5]
        for zt in zs:
            _torii(b, zt, 0.4, X_PIL, R_PIL, yn=Y_ENJAMBE - 0.4, hn=1.6, ys=37.6, hs=1.4, hk=1.4,
                   ext=(1.1, 1.7, 2.5), hup=1.0, prof=1.4)
            n_torii += 1
        for i in range(0, len(zs) - 1, 2):
            zl = (zs[i] + zs[i + 1]) / 2
            for s in (1, -1):
                _lanterne(b, s * X_PIL, 0.4, zl, s=0.7)
        # grand torii d'entrée, plaque 藤 (panneau texte face aux joueurs)
        zt = 9.0
        _torii(b, zt, 0.0, 38.0, 2.2, yn=40.0, hn=2.5, ys=50.0, hs=2.5, hk=2.5, ext=(3.3, 4.8, 7.3),
               hup=2.0, prof=2.6, tip=1.0)
        zp = zt + 2.6 * 0.6 + 0.1
        b.box((-1.0, 44.0, zt + 0.9), (1.0, 48.0, zp + 0.05), LAQUE)
        b.box((-3.8, 41.6, zp), (3.8, 50.9, zp + 0.5), c("or"))
        plaque = b.box((-3.2, 42.2, zp + 0.5), (3.2, 50.3, zp + 0.8), LAQUE)
        plaque.label = {"face": "Back", "text": "藤", "color": c("or"), "bg": None, "font": "brush"}
        for s in (1, -1):
            _lanterne(b, s * 46.0, 0.0, 12.0, s=1.4)
    with b.group("Glycines"):
        for s in (1, -1):  # deux grands glycines retombants encadrent la porte, à hauteur des yeux
            _glycine_maitre(b, s * (G0 + 27.0), 0.0, 14.5, rng, cotes=("avant", "gauche" if s > 0 else "droite"),
                            densite=0.95)

    # -- grande corde sacrée (shimenawa) tendue au-dessus de la gorge, avec shide et glands de paille --------
    with b.group("Shimenawa"):
        g1 = [m for m in cols if m["kind"] == "gorge1"]
        y_bas_parois = min(min(m["t"][1] for m in g1), min(m["t"][2] for m in g1))
        ZA0 = g1[0]["z"][1]
        if y_bas_parois >= CAPS[0] + 18:
            zr = ZA0 - 3.0
            xa = GS[1] + 1.0                              # ancrée 1 stud dans les parois
            y_anc = min(y_bas_parois - 4.0, CAPS[0] + 20.0)
            fl = 7.0                                      # flèche
            yf = lambda x: y_anc - fl * (1 - (x / xa) ** 2)  # noqa: E731
            n = 9
            xs = np.linspace(-xa, xa, n + 1)
            for x0r, x1r in zip(xs[:-1], xs[1:]):
                y0r, y1r = yf(x0r), yf(x1r)
                ang = math.degrees(math.atan2(y1r - y0r, x1r - x0r))
                lg = math.hypot(x1r - x0r, y1r - y0r) + 0.7
                b.part("cyl", (lg, 3.0, 3.0), ((x0r + x1r) / 2, (y0r + y1r) / 2, zr), rot_z(ang),
                       vary("corde", rng, 0.04), name="Corde")
            for xg in (-0.62 * xa, -0.24 * xa, 0.24 * xa, 0.62 * xa):   # glands de paille
                b.box((xg - 0.6, yf(xg) - 4.6, zr - 0.6), (xg + 0.6, yf(xg) - 1.0, zr + 0.6), c("corde"), collide=False)
                b.box((xg - 0.75, yf(xg) - 2.0, zr - 0.75), (xg + 0.75, yf(xg) - 1.4, zr + 0.75),
                      shade(c("corde"), 0.8), collide=False)
            for xs_ in (-0.82 * xa, -0.43 * xa, 0.0, 0.43 * xa, 0.82 * xa):  # shide en zigzag
                y0s = yf(xs_) - 1.3
                for k, (dx, h) in enumerate(((0.0, 2.0), (0.9, 1.8), (0.0, 1.8))):
                    b.box((xs_ + dx - 0.6, y0s - h, zr - 0.08), (xs_ + dx + 0.6, y0s, zr + 0.08), c("shide"),
                          collide=False, shadow=False)
                    y0s -= h

    # -- escaliers : torii, lanternes, sanctuaire, belvédère ------------------------------------
    with b.group("Sanctuaire"):
        for s in (1, -1):
            e = esc[s]
            xc = s * e["u"]
            segs = e["segs"]
            spots = [(segs[0][1] + 1.5, 0.0)]
            spots += [((z0 + z1) / 2, y0) for kind, z0, z1, y0, _ in segs if kind == "palier"]
            spots += [(e["zt0"] - 1.2, e["yt"])]
            for zt, yt in spots:
                _torii(b, zt, yt, 5.4, 0.55, yn=7.4, hn=0.8, ys=9.6, hs=0.7, hk=0.7, ext=(0.7, 1.0, 1.5), hup=0.6,
                       prof=1.0, xc=xc, carre=True, tip=0.4)
            for sx in (-1, 1):
                _lanterne(b, xc + sx * 6.6, 0.0, segs[0][1] + 4.0, s=0.75)
                _lanterne(b, xc + sx * 6.8, e["yt"], e["zt0"] - 3.4, s=0.75)
            zc = e["zt0"] - (11.5 if e["type"] == "sanctuaire" else 8.5)
            (_sanctuaire if e["type"] == "sanctuaire" else _pavillon)(b, xc, e["yt"], zc, rng)

    # -- glycines -------------------------------------------------------------------------
    def touffes(F, items, masses, rideaux, sol, y_max=1e9, proba=0.4):
        proba *= dens
        """Touffes sur les petites corniches d'une peau, de haut en bas, hors des rideaux déjà posés ;
        chaque touffe (et ses grappes) devient un obstacle pour les suivantes."""
        occ = list(masses)
        gene = [r for r in rideaux if r]
        for a, bb, y, sa_h, sa_b in sorted(items, key=lambda r: -r[2]):
            if y > y_max or y < sol + 3 or bb - a < 4 or rng.random() > proba:
                continue
            lm = min(6.0, y - sol - 0.5)
            y0b, y1b = y - lm - 0.5, y + 3.6
            if any(r[0] < bb and r[1] > a and r[2] < y1b and r[3] > y0b for r in gene):
                continue
            _touffe(F, a + 0.3, bb - 0.3, y, sa_h, sa_b, rng, occ, long_max=lm, sol=sol)
            occ.append((a, bb, y0b, y1b, sa_b + 1.2))
            gene.append((a, bb, y0b, y1b, sa_b + 1.2))

    with b.group("Glycines"):
        for i, m in enumerate(cols):
            x0, x1 = m["x0"], m["x1"]
            if m["kind"] == "escalier":
                # fond rocheux derrière le sanctuaire / le belvédère : rideau au-dessus du toit
                e = esc[m["side"]]
                hb = m["t"][2]
                y_toit = e["yt"] + (17.0 if e["type"] == "sanctuaire" else 13.0)
                if hb > y_toit + 10:
                    _glycine_corniche(_Face(b, "z", e["zt1"], 1), x0, x1, hb, -(e["zt1"] - ZBK) + 1.0, 0.0, rng, (),
                                      densite=DENS, long_max=min(24.0, hb - y_toit - 2.0), sol=y_toit + 2.0, haut=1.2)
                continue
            masses = peaux_av[i]
            t0, ZA, tB, ZB = m["t"][0], m["z"][1], m["t"][1], m["z"][2]
            tranche = m["kind"].startswith("gorge")
            rideau = None
            # corniche avant : dessus du gradin avant, rideau sur la face avant
            if rng.random() < 0.92:
                dfront = _sa_haut(masses, x0, x1, t0)
                rideau = _glycine_corniche(F_av, x0, x1, t0, -5.0 if tranche else ZA + 1.8, dfront, rng, masses,
                                           densite=DENS, long_max=min(24.0, 0.5 * t0), haut=1.2,
                                           ov_max=6.3 if tranche else None)
            touffes(F_av, [r for r, ms in replats_av if ms is masses], masses, [rideau], sol=1.0, y_max=t0 - 4)
            # gradin du milieu : rideau sur la face du gradin (pas de peau), au-dessus de la masse avant ;
            # sur les grandes faces nues, un balcon rocheux à mi-hauteur porte sa propre glycine
            if tranche and tB > t0 + 8:
                _glycine_corniche(_Face(b, "z", ZA, 1), x0, x1, tB, -5.0, 0.0, rng, (), densite=DENS * 0.9,
                                  long_max=min(16.0, tB - t0 - 8.5), sol=t0 + 8.0, ov=1.5)
            elif tB > t0 + 8 and rng.random() < 0.6 + 0.2 * dens:
                F_B = _Face(b, "z", ZA, 1)
                obst = []
                if tB - t0 > 30 and x1 - x0 >= 8:
                    yb = _q2(t0 + 12 + float(rng.uniform(0, tB - t0 - 32)))
                    wb = min(x1 - x0 - 1.0, float(rng.choice([7, 8, 10, 12])))
                    ub = x0 + 0.5 + float(rng.uniform(0, x1 - x0 - 1.0 - wb))
                    pb = float(rng.choice([2.5, 3.0, 3.5]))
                    F_B.box(ub, ub + wb, yb - 2, yb, 0, pb, vary("roche_claire", rng, 0.03), studs="top")
                    b.wedge_under((ub + 0.5, yb - 5, ZA), (ub + wb - 0.5, yb - 2, ZA + pb - 0.5),
                                  vary("roche", rng, 0.03), down="+z")
                    r = _glycine_corniche(F_B, ub + 0.3, ub + wb - 0.3, yb, 0.3, pb, rng, (), densite=DENS,
                                          long_max=min(10.0, yb - t0 - 10.0), sol=t0 + 8.0, ov=1.5)
                    obst.append((ub - 0.5, ub + wb + 0.5, (r[2] if r else yb - 5) - 0.5, yb + 9.0, pb + 2.0))
                _glycine_corniche(F_B, x0, x1, tB, -(ZA - ZB) + 1.8, 0.0, rng, obst, devant=False, densite=DENS * 0.9,
                                  long_max=min(20.0, tB - t0 - 8.5), sol=t0 + 8.0, ov=float(rng.choice([1.5, 2.0])))
        # gorge : corniches des tranches, qui retombent dans la gorge (au-dessus des kasagi)
        for s in (1, -1):
            F_g0, gmasses, greplats = gorge[s]
            for gi in range(3):
                g = next(m for m in cols if m["kind"] == f"gorge{gi}" and m["side"] == s)
                prev = next(m for m in cols if m["kind"] == f"gorge{gi - 1}" and m["side"] == s) if gi else None
                F_g = _Face(b, "x", s * GS[gi], -s)
                masses = gmasses if gi == 0 else ()
                for j in range(4):
                    za, zb, h = g["z"][j], g["z"][j + 1], g["t"][j]
                    if prev is not None and h <= prev["t"][j] + 4:
                        continue
                    if j == 0:
                        za = -6.0  # l'avant de la tranche porte la corniche de la face avant
                    elif j == 1 and g["t"][1] > g["t"][0] + 8:
                        za = g["z"][1] - 6.0  # idem pour la corniche de la face du gradin du milieu
                    if j == 3:
                        zb = g["z"][4] + 6.0  # l'arrière de la tranche porte la corniche du dos
                    sol = prev["t"][j] + 8.0 if prev is not None else Y_KASA + 1.4
                    for a, bb in _colonnes(zb + 0.4, za - 0.4, rng, (8, 10, 12, 14)):
                        if rng.random() < 0.9 and bb - a > 3:
                            dfront = _sa_haut(masses, a, bb, h) if masses else 0.0
                            _glycine_corniche(F_g, a, bb, h, -(GS[gi + 1] - GS[gi]) + 1.8, dfront, rng, masses,
                                              densite=DENS, long_max=min(16.0, h - sol), sol=sol)
            # petites corniches basses de la paroi (sous les torii) : touffes courtes
            touffes(F_g0, greplats, gmasses, [], sol=Y_ISHI + 0.5, y_max=24.0, proba=0.6)
        # dos, près de la sortie de la gorge (vu depuis la zone suivante) : rideaux du gradin arrière
        for i, m in enumerate(cols):
            if m["kind"] == "escalier" or min(abs(m["x0"]), abs(m["x1"])) > GS[3] + 24:
                continue
            masses = peaux_dos.get(i, [])
            tD, ZC = m["t"][3], m["z"][3]
            dfront = _sa_haut(masses, m["x0"], m["x1"], tD)
            _glycine_corniche(F_dos, m["x0"], m["x1"], tD, -5.0 if m["kind"].startswith("gorge") else -(ZC - ZBK) + 1.8,
                              dfront, rng, masses, long_max=min(18.0, 0.4 * tD), ov=1.4, ov_max=D + ZBK,
                              densite=DENS * 0.9)

    # -- sommets : arbres et glycines ------------------------------------------------------
    with b.group("Vegetation"):
        occ = []  # boîtes déjà prises par la végétation des sommets (x0, x1, y0, y1, z0, z1)

        def coupe(bx):
            return any(o[0] < bx[1] and o[1] > bx[0] and o[2] < bx[3] and o[3] > bx[2] and o[4] < bx[5] and o[5] > bx[4]
                       for o in occ)

        for i, m in enumerate(cols):
            if m["kind"] == "escalier" or m["kind"].startswith("gorge"):
                continue
            x0, x1 = m["x0"], m["x1"]
            tC, ZB, ZC = m["t"][2], m["z"][2], m["z"][3]
            w = x1 - x0
            z_libre = ZB - 1.0  # devant : glycine en arbre ; derrière : cèdre ou pin
            if rng.random() < 0.75:
                sa = float(rng.uniform(0.75, 1.0))
                hz = 6.5 * sa
                zc = ZB - 1.0 - hz
                yc = tC + 2.2 * sa
                y_top = yc + 8.0 * sa
                # le houppier déborde au-dessus des voisins plus bas que lui (jamais sur un escalier)
                g = cols[i - 1] if i > 0 and abs(cols[i - 1]["x1"] - x0) < 1e-6 else None
                d = cols[i + 1] if i + 1 < len(cols) and abs(cols[i + 1]["x0"] - x1) < 1e-6 else None
                hg = h_max(g, zc + hz, zc - hz) if g is not None else 1e9
                hd = h_max(d, zc + hz, zc - hz) if d is not None else 1e9
                lim_g = 9.0 * sa if hg < yc - 1.2 else 0.0
                lim_d = 9.0 * sa if hd < yc - 1.2 else 0.0
                sol_arbre = max([tC] + [h for h, lim in ((hg, lim_g), (hd, lim_d)) if lim > 0]) + 1.2
                xa, xb = x0 - lim_g + 0.5, x1 + lim_d - 0.5
                for o in occ:
                    if o[2] < y_top and o[3] > tC - 0.5 and o[4] < zc + hz + 0.3 and o[5] > zc - hz - 0.3:
                        if (o[0] + o[1]) / 2 < (x0 + x1) / 2:
                            xa = max(xa, o[1] + 0.3)
                        else:
                            xb = min(xb, o[0] - 0.3)
                hx = min(9.0 * sa, (xb - xa) / 2)
                if hx >= 5.0 and xa >= x0 - lim_g and xb <= x1 + lim_d and xa < x1 - 2.0 and xb > x0 + 2.0:
                    lo, hi = max(xa + hx, x0 + 2.0), min(xb - hx, x1 - 2.0)
                    xx = float(rng.uniform(lo, hi)) if lo < hi else (x0 + x1) / 2
                    xx = min(max(xx, xa + hx), xb - hx)
                    _glycine_arbre(b, xx, tC, zc, rng, s=sa, hx=hx, hz=hz, rideaux=("avant",), long_max=4.0,
                                   densite=0.7 * dens, sol=sol_arbre, xmin=x0, xmax=x1, ht=2.2 * sa)
                    occ.append((xx - hx, xx + hx, tC, y_top, zc - hz, zc + hz))
                    z_libre = zc - hz - 1.0
            for essai in range(3):  # un à trois conifères derrière (silhouette verte des crêtes)
                if rng.random() > (0.85, 0.6, 0.35)[essai]:
                    continue
                cedre = rng.random() < 0.65
                sc = min(float(rng.uniform(0.9, 1.45)), (w - 1.0) / (6.4 if cedre else 10.6))
                half = sc * (3.2 if cedre else 5.3)
                half_z = sc * (3.2 if cedre else 2.6)
                if z_libre - (ZC + 0.5) >= 2 * half_z + 0.5:
                    xx = float(rng.uniform(x0 + half + 0.3, max(x0 + half + 0.3, x1 - half - 0.3)))
                    zz = float(rng.uniform(ZC + 0.5 + half_z, z_libre - half_z - 0.2))
                    boite = (xx - half - 0.2, xx + half + 0.2, tC, tC + sc * 14.0, zz - half_z - 0.2, zz + half_z + 0.2)
                    if not coupe(boite):
                        (_cedre if cedre else _pin)(b, xx, tC, zz, rng, s=sc)
                        occ.append(boite)

    return {"emprise": (largeur, profondeur), "hauteur": hauteur, "passage": passage, "debord_avant": 22,
            "torii": n_torii}


# ---------------------------------------------------------------------------
# Train à vapeur de l'ère Taishō
# ---------------------------------------------------------------------------
LOCO = c("loco")
LOCO_F = shade(c("loco"), 0.75)
CHARBON = mix(c("noir"), c("metal_fonce"), 0.35)
Y_RAIL = 2.8          # dessus des rails
X_RAIL = 3.2          # axe des rails (écartement 6,4)


def _essieu(b, y, z, r, rayons=True, demi=3.5) -> None:
    """Essieu vu de côté : tambour noir (bandages) et, de chaque côté, centre de roue rouge à rayons noirs
    et moyeu de laiton."""
    b.cyl((0.0, y, z), r, 2 * demi, LOCO_F, axis="x")
    for sx in (-1, 1):
        x_ext = sx * demi
        b.cyl((x_ext + sx * 0.075, y, z), r - 0.45, 0.15, c("loco_rouge"), axis="x")
        if rayons:
            for ang in (0.0, 60.0, 120.0):
                b.part("block", (0.1, 0.24, 2 * (r - 0.6)), (x_ext + sx * 0.2, y, z), rot_x(ang), LOCO_F,
                       collide=False)
        b.cyl((x_ext + sx * 0.25, y, z), min(0.45, r * 0.3), 0.3, c("laiton"), axis="x", collide=False)


def _voie(b, z0, z1, rng) -> None:
    """Remblai herbeux, ballast, traverses et rails entre z0 et z1."""
    b.box((-6.5, 0, z0), (6.5, 1.0, z1), vary("herbe_fonce", rng, 0.03), studs="top")
    for sx in (-1, 1):
        a, bb = sorted((sx * 6.5, sx * 8.5))
        b.wedge((a, 0, z0), (bb, 1.0, z1), vary("herbe", rng, 0.03), down="+x" if sx > 0 else "-x", studs="top")
    b.box((-4.8, 1.0, z0 + 0.5), (4.8, 1.8, z1 - 0.5), vary("gravier", rng, 0.02), studs="top")
    for sx in (-1, 1):
        a, bb = sorted((sx * 4.8, sx * 6.0))
        b.wedge((a, 1.0, z0 + 0.5), (bb, 1.8, z1 - 0.5), vary("pierre_fonce", rng, 0.03), down="+x" if sx > 0 else "-x",
                studs="top")
    n = int((z1 - z0 - 2.0) // 2.6)
    zz0 = z0 + (z1 - z0 - (n - 1) * 2.6) / 2
    for i in range(n):
        zz = zz0 + i * 2.6
        b.box((-4.4, 1.8, zz - 0.5), (4.4, 2.2, zz + 0.5), vary("bois_fonce", rng, 0.06), studs="top")
    for sx in (-1, 1):
        b.box((sx * X_RAIL - 0.25, 2.2, z0 + 2.2), (sx * X_RAIL + 0.25, Y_RAIL, z1 - 2.2), c("metal"), material="Metal")
    # heurtoirs en bout de voie : poutre rayée rouge et blanc sur deux poteaux
    for zz, sz in ((z0 + 1.6, -1), (z1 - 1.6, 1)):
        for sx in (-1, 1):
            b.box((sx * X_RAIL - 0.4, 1.8, zz - 0.4), (sx * X_RAIL + 0.4, 4.6, zz + 0.4), c("bois_fonce"))
        b.box((-4.2, 4.6, zz - 0.5), (-1.4, 5.6, zz + 0.5), c("rouge"))
        b.box((-1.4, 4.6, zz - 0.5), (1.4, 5.6, zz + 0.5), c("blanc"))
        b.box((1.4, 4.6, zz - 0.5), (4.2, 5.6, zz + 0.5), c("rouge"))


def _locomotive(b, zL, rng, deflecteurs=True) -> float:
    """Locomotive noire tournée vers -Z (traverse avant en z = zL) ; renvoie le z arrière de l'abri."""
    yb = 10.1  # axe de la chaudière
    # chasse-pierres et traverse rouge, tampons
    b.wedge((-3.4, Y_RAIL + 0.4, zL - 2.2), (3.4, 4.4, zL), LOCO, down="-z", studs="top")
    b.box((-3.9, 4.4, zL), (3.9, 5.6, zL + 0.8), c("loco_rouge"))
    for sx in (-1, 1):
        b.cyl((sx * 2.6, 5.0, zL - 0.35), 0.45, 0.7, LOCO_F, axis="z")
        b.cyl((sx * 2.6, 5.0, zL - 0.78), 0.6, 0.16, c("metal"), axis="z")
    # châssis, tabliers et liseré rouge
    b.box((-2.3, 4.0, zL + 0.8), (2.3, 7.8, zL + 20.6), LOCO)
    for sx in (-1, 1):
        a, bb = sorted((sx * 2.3, sx * 4.0))
        b.box((a, 7.8, zL + 0.8), (bb, 8.2, zL + 15.2), LOCO_F, studs="top")
        a, bb = sorted((sx * 3.85, sx * 4.05))
        b.box((a, 7.55, zL + 0.9), (bb, 7.8, zL + 15.1), c("loco_rouge"), collide=False)
    # boîte à fumée, porte ronde, phare
    b.cyl((0, yb, zL + 2.7), 2.85, 3.8, LOCO_F, axis="z")
    b.cyl((0, yb, zL + 0.65), 2.3, 0.3, LOCO, axis="z")
    b.cyl((0, yb, zL + 0.38), 0.35, 0.24, c("laiton"), axis="z")
    b.cyl((0, yb, zL + 0.45), 1.9, 0.1, c("metal_fonce"), axis="z", collide=False)
    b.box((-0.75, 12.8, zL + 1.1), (0.75, 14.2, zL + 2.7), c("laiton"))
    b.cyl((0, 13.5, zL + 1.02), 0.5, 0.16, c("jaune_lampion"), axis="z", material="Neon", collide=False)
    # cheminée
    b.cyl((0, 14.15, zL + 3.0), 0.9, 3.3, LOCO, axis="y")
    b.cyl((0, 15.7, zL + 3.0), 1.15, 0.6, LOCO_F, axis="y", studs="top")
    # écrans pare-fumée
    if deflecteurs:
        for sx in (-1, 1):
            a, bb = sorted((sx * 3.3, sx * 3.5))
            b.box((a, 8.2, zL + 1.3), (bb, 11.4, zL + 4.4), LOCO)
    # chaudière, cerclages de laiton, main courante
    b.cyl((0, yb, zL + 9.9), 2.6, 10.6, LOCO, axis="z")
    for zz in (6.6, 10.2, 13.8):
        b.cyl((0, yb, zL + zz), 2.66, 0.3, c("laiton"), axis="z", collide=False)
    for sx in (-1, 1):
        a, bb = sorted((sx * 2.62, sx * 2.8))
        b.box((a, 10.7, zL + 5.0), (bb, 10.88, zL + 15.1), c("laiton"), collide=False)
    # dômes (vapeur en laiton, sablière noire), sifflet
    b.cyl((0, 13.0, zL + 9.0), 1.1, 1.4, c("laiton"), axis="y")
    b.ball((0, 13.7, zL + 9.0), 1.1, c("laiton"))
    b.cyl((0, 12.9, zL + 12.0), 0.85, 1.2, LOCO, axis="y")
    b.ball((0, 13.5, zL + 12.0), 0.85, LOCO)
    b.cyl((0, 13.3, zL + 14.6), 0.25, 1.2, c("laiton"), axis="y", collide=False)
    # pompe à air sur le flanc droit, tuyau de laiton, turbo-générateur derrière la cheminée
    b.cyl((2.9, 9.6, zL + 11.6), 0.55, 2.6, LOCO_F, axis="y")
    b.cyl((2.9, 11.0, zL + 11.6), 0.62, 0.2, c("laiton"), axis="y", collide=False)
    b.box((2.66, 8.6, zL + 5.2), (2.86, 8.8, zL + 11.1), c("laiton"), collide=False)
    b.box((-0.5, 12.6, zL + 4.6), (0.5, 13.3, zL + 5.8), LOCO_F)
    # cylindres et bielles
    for sx in (-1, 1):
        b.cyl((sx * 3.45, 6.2, zL + 3.4), 1.0, 3.6, LOCO_F, axis="z")
        for zz in (1.55, 5.25):
            b.cyl((sx * 3.45, 6.2, zL + zz), 1.08, 0.1, c("laiton"), axis="z", collide=False)
        a, bb = sorted((sx * 3.95, sx * 4.15))
        b.box((a, 5.95, zL + 5.2), (bb, 6.3, zL + 13.4), c("metal"), material="Metal", collide=False)
        b.box((a, 4.3, zL + 7.8), (bb, 4.65, zL + 18.6), c("metal"), material="Metal", collide=False)
    # roues : bissel avant et trois essieux moteurs rouges
    _essieu(b, Y_RAIL + 1.1, zL + 3.0, 1.1, rayons=False, demi=3.4)
    for zz in (8.0, 13.2, 18.4):
        _essieu(b, Y_RAIL + 2.4, zL + zz, 2.4)
    # abri de conduite
    z0, z1 = zL + 15.2, zL + 20.6
    b.box((-3.9, 8.2, z0), (3.9, 14.8, z1), LOCO)
    for sx in (-1, 1):
        a, bb = sorted((sx * 1.4, sx * 3.3))
        b.box((a, 12.0, z0 - 0.12), (bb, 13.8, z0), c("fenetre"), collide=False)
        a, bb = sorted((sx * 3.9, sx * 4.0))
        b.box((a, 10.8, z0 + 0.9), (bb, 13.6, z0 + 4.1), c("laiton"), collide=False)
        a, bb = sorted((sx * 4.0, sx * 4.1))
        b.box((a, 11.1, z0 + 1.2), (bb, 13.3, z0 + 3.8), c("fenetre"), collide=False)
    b.box((-4.3, 14.8, z0 - 0.4), (4.3, 15.3, z1 + 0.6), c("voiture_toit"), studs="top")
    b.box((-3.0, 15.3, z0 + 0.2), (3.0, 15.7, z1), c("voiture_toit"), studs="top")
    b.box((-0.8, 15.7, z0 + 1.6), (0.8, 16.1, z0 + 3.4), LOCO_F, studs="top")
    return z1


def _tender(b, z0, rng) -> float:
    """Tender noir : caisse à eau, charbon en tas, liseré de laiton, trois essieux rouges."""
    z1 = z0 + 11.0
    b.box((-3.3, 4.0, z0 + 0.5), (3.3, 5.8, z1 - 0.5), LOCO_F)
    b.box((-3.7, 5.8, z0), (3.7, 11.2, z1), LOCO)
    b.box((-3.75, 10.3, z0 - 0.05), (3.75, 10.6, z1 + 0.05), c("laiton"), collide=False)
    b.box((-3.2, 11.2, z0 + 0.5), (3.2, 12.0, z0 + 7.5), vary(CHARBON, rng, 0.05), studs="top")
    b.box((-2.2, 12.0, z0 + 1.5), (2.0, 12.6, z0 + 5.5), vary(CHARBON, rng, 0.08), studs="top")
    for sx in (-1, 1):
        a, bb = sorted((sx * 3.35, sx * 3.7))
        b.box((a, 11.2, z0), (bb, 12.2, z0 + 8.0), LOCO_F)
    b.cyl((0, 11.5, z0 + 9.3), 0.9, 0.6, LOCO_F, axis="y", studs="top")
    for zz in (2.2, 5.5, 8.8):
        _essieu(b, Y_RAIL + 1.4, z0 + zz, 1.4, rayons=False)
    return z1


def _voiture(b, zc, rng, allumees) -> None:
    """Voiture à voyageurs marron (caisse en bois), fenêtres (certaines éclairées), toit à lanterneau sombre,
    plates-formes d'extrémité à garde-corps, deux bogies."""
    L = 24.0
    zb0, zb1 = zc + 1.2, zc + L - 1.2
    b.box((-3.4, 5.0, zc + 0.4), (3.4, 5.6, zc + L - 0.4), LOCO_F)
    # caisse : soubassement plus sombre, partie haute
    bas = shade(c("voiture"), 0.85)
    b.box((-3.6, 5.6, zb0), (3.6, 8.4, zb1), bas)
    b.box((-3.6, 8.4, zb0), (3.6, 11.8, zb1), vary("voiture", rng, 0.03))
    for sx in (-1, 1):
        a, bb = sorted((sx * 3.6, sx * 3.7))
        b.box((a, 8.4, zb0 + 0.3), (bb, 8.7, zb1 - 0.3), c("bois_clair"), collide=False)
        b.box((a, 10.7, zb0 + 0.3), (bb, 11.0, zb1 - 0.3), c("bois_clair"), collide=False)
        a, bb = sorted((sx * 3.6, sx * 3.72))
        for k in range(7):
            zz = zb0 + 1.4 + k * 2.8
            lum = allumees[(k + (sx > 0)) % len(allumees)]
            b.box((a, 8.7, zz), (bb, 10.7, zz + 1.6), c("fenetre_lumiere") if lum else c("fenetre"),
                  material="Neon" if lum else "SmoothPlastic", collide=False)
    for zz, sz in ((zb0, -1), (zb1, 1)):
        b.box((-0.9, 6.0, min(zz, zz + sz * 0.12)), (0.9, 10.6, max(zz, zz + sz * 0.12)), c("bois_fonce"),
              collide=False)
    # toit à lanterneau
    b.box((-3.9, 11.8, zc + 0.8), (3.9, 12.4, zc + L - 0.8), c("voiture_toit"), studs="top")
    for sx in (-1, 1):
        a, bb = sorted((sx * 1.9, sx * 3.9))
        b.wedge((a, 12.4, zc + 1.2), (bb, 12.9, zc + L - 1.2), c("voiture_toit"), down="+x" if sx > 0 else "-x",
                studs="top")
    b.box((-1.9, 12.4, zc + 2.4), (1.9, 13.4, zc + L - 2.4), shade(c("voiture_toit"), 0.85), studs="top")
    for k in range(3):
        zz = zc + 6.0 + k * 6.0
        b.box((-0.6, 13.4, zz - 0.6), (0.6, 13.9, zz + 0.6), LOCO_F, studs="top")
    # plates-formes et garde-corps
    for za, zbb, zr in ((zc + 0.2, zb0, zc + 0.2), (zb1, zc + L - 0.2, zc + L - 0.45)):
        b.box((-3.4, 5.6, za), (3.4, 6.0, zbb), c("bois_fonce"), studs="top")
        for sx in (-1, 1):  # marchepied
            a, bb = sorted((sx * 3.0, sx * 3.7))
            b.box((a, 4.1, za + 0.1), (bb, 4.35, zbb - 0.1), LOCO_F, studs="top", collide=False)
            b.box((sx * 3.35 - 0.08, 4.35, za + 0.25), (sx * 3.35 + 0.08, 5.0, za + 0.45), LOCO_F, collide=False)
        b.box((-3.3, 8.2, zr), (3.3, 8.45, zr + 0.25), LOCO_F, collide=False)
        for sx in (-1, 1):
            b.box((sx * 3.2 - 0.1, 6.0, zr), (sx * 3.2 + 0.1, 8.2, zr + 0.25), LOCO_F, collide=False)
    # bogies
    for zz in (zc + 4.6, zc + L - 4.6):
        b.box((-3.2, 3.4, zz - 2.3), (3.2, 5.0, zz + 2.3), LOCO_F)
        for dz in (-1.4, 1.4):
            b.cyl((0.0, Y_RAIL + 1.1, zz + dz), 1.1, 7.0, LOCO_F, axis="x")
            for sx in (-1, 1):
                b.cyl((sx * 3.56, Y_RAIL + 1.1, zz + dz), 0.7, 0.12, c("loco_rouge"), axis="x", collide=False)


def train_vapeur(b, variant: int = 0, voitures: int = 3) -> dict:
    """Train à vapeur de l'ère Taishō à l'arrêt sur un court remblai, nez de la locomotive vers -Z.

    variant : fenêtres éclairées et volute de vapeur ; 2 et 3 sans écrans pare-fumée."""
    rng = np.random.default_rng(907 + 53 * variant)
    voitures = max(0, int(voitures))
    L_train = 2.2 + 20.6 + 0.8 + 11.0 + voitures * (1.6 + 24.0)
    L = L_train + 20.0
    z_av = -L_train / 2
    with b.group("Voie"):
        _voie(b, -L / 2, L / 2, rng)
    with b.group("Locomotive"):
        zL = z_av + 2.2
        z_abri = _locomotive(b, zL, rng, deflecteurs=variant < 2)
        # volute de vapeur au-dessus de la cheminée, chassée vers l'arrière : colonne de boules qui grossissent,
        # avec des bouffées latérales (nuage, pas un collier de perles)
        pts = [(0.0, 16.9, 0.0, 1.0), (0.3, 18.3, 0.8, 1.35), (-0.4, 19.8, 2.0, 1.7), (0.5, 21.0, 3.8, 2.1),
               (-0.6, 21.9, 6.2, 2.4), (0.4, 22.3, 9.0, 2.2), (1.4, 20.6, 2.6, 1.2), (-1.5, 21.4, 4.6, 1.5),
               (1.6, 22.8, 6.6, 1.6), (-1.0, 23.6, 8.0, 1.5), (0.8, 21.2, 11.2, 1.6)]
        if variant % 2:
            pts = [(x, y - 0.6 + 0.03 * z * z, z * 1.15, r) for x, y, z, r in pts]
        for k, (x, y, z, r) in enumerate(pts):
            col = mix(c("blanc"), c("metal"), (0.0, 0.06, 0.12)[k % 3])
            b.ball((x, y, zL + 3.0 + z), r, col, collide=False, shadow=False)
    with b.group("Tender"):
        z_t = _tender(b, z_abri + 0.8, rng)
        b.box((-0.6, 4.6, z_abri), (0.6, 5.2, z_abri + 0.8), LOCO_F, collide=False)  # attelage
    zc = z_t + 1.6
    motifs = ([1, 0, 1, 1, 0, 1, 0], [1, 1, 0, 1, 0, 0, 1], [0, 1, 1, 0, 1, 1, 0], [1, 0, 0, 1, 1, 0, 1])
    for i in range(voitures):
        with b.group(f"Voiture{i + 1}"):
            allumees = motifs[(variant + i) % len(motifs)]
            _voiture(b, zc, rng, allumees)
            b.box((-0.6, 4.6, zc - 1.6), (0.6, 5.2, zc + 0.4), LOCO_F, collide=False)        # attelage
            b.box((-1.2, 5.65, zc - 1.6), (1.2, 5.95, zc + 0.2), c("bois_fonce"), collide=False)  # passerelle
        zc += 24.0 + 1.6
    if voitures:
        with b.group(f"Voiture{voitures}"):  # feu de queue rouge sur la dernière voiture
            zq = zc - 1.6 - 1.2  # paroi arrière de la caisse
            b.box((2.2, 9.0, zq), (3.0, 9.8, zq + 0.3), LOCO_F, collide=False)
            b.cyl((2.6, 9.4, zq + 0.4), 0.3, 0.2, c("rouge"), axis="z", material="Neon", collide=False)
    return {"emprise": (17.0, round(L, 2)), "hauteur": 16.0, "longueur": round(L, 2),
            "longueur_train": round(L_train, 2)}
