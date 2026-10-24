"""Glycines et végétation de la zone 3 en style stud : glycines tordues aux longues grappes, glycines géantes,
treille fujidana, arche de glycines au-dessus du couloir, bambous, pin taillé en nuages, buissons, rochers moussus,
souches et touffes d'herbe.

Principes :
- les grappes sont l'âme de la zone. Deux formes, toujours 2 à 5 segments empilés qui s'affinent et pâlissent vers la
  pointe sur la rampe glycine_fonce → glycine → glycine_claire → glycine_pale (départ plus ou moins sombre selon la
  grappe) : les « rubans » (rideaux) tangents au bord des masses, qui en habillent le flanc et se terminent en escalier
  irrégulier (de face plusieurs grappes inégales, de profil une grappe fine), et les « colonnes » dessous. Longueurs
  qui ondulent autour de chaque masse (ourlet festonné) : de loin, on lit des glycines ;
- rien ne flotte et rien ne se traverse : chaque grappe est noyée dans la masse ou le bloc qui la porte (registre des
  « plafonds »), ne traverse aucun autre bloc plus bas, aucun bois sous son accroche (registre des « obstacles ») ni
  aucune autre grappe (test d'emprise exact) ;
- bois tordu : tiges en poutres inclinées et vrillées autour de leur axe, deux ou trois tiges tressées, racines en
  coins ; le bois collisionne ; fleurs, feuilles et grappes ont `collide=False` ;
- studs sur les dessus des masses de fleurs et des feuilles uniquement (pas sur les grappes) ;
- pas de faces coplanaires : chaque masse a sa « famille » de hauteurs (fraction de y0 modulo 0,5 sur la grille du
  1/16, distincte de celles des masses qu'elle touche), les faces horizontales des grappes et des feuilles sont sur un
  1/32 impair (jamais sur la grille du 1/16) ;
- chaque fonction remplit son budget de pièces avec des grappes, réparties à tour de rôle entre les masses, sans
  jamais le dépasser ;
- les arbres sont recentrés : l'origine est le centre de leur emprise au sol (même pour les arbres penchés).
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, rot_y, shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Couleurs
# ---------------------------------------------------------------------------

BLANC = c("blanc")
# Dégradés de fleurs : (dessous, foncé, mauve, clair, pointe)
TEINTES = {
    "mauve": (c("glycine_nuit"), c("glycine_fonce"), c("glycine"), c("glycine_claire"), c("glycine_pale")),
    "violet": (shade(c("glycine_nuit"), 0.84), c("glycine_nuit"), c("glycine_fonce"), c("glycine"), c("glycine_claire")),
    "blanc": (mix(c("glycine_nuit"), c("glycine_claire"), 0.5), mix(c("glycine_fonce"), c("glycine_pale"), 0.55),
              mix(c("glycine_claire"), BLANC, 0.35), mix(c("glycine_pale"), BLANC, 0.55), BLANC),
}
TRONC = c("tronc")
TRONC_CLAIR = c("tronc_clair")
ECORCE_PIN = mix(c("tronc_clair"), c("terre"), 0.55)
FEUILLES = (c("feuille_fonce"), c("feuille"), c("feuille_claire"))
GRIS = (mix(c("pierre_fonce"), c("roche"), 0.12), mix(c("bordure"), c("roche"), 0.12), c("pierre"), c("pierre_claire"))

# Grappes : part de la longueur, largeur relative de chaque segment (du haut vers la pointe)
_FR = {2: (0.56, 0.44), 3: (0.38, 0.33, 0.29), 4: (0.28, 0.26, 0.24, 0.22), 5: (0.23, 0.21, 0.2, 0.19, 0.17)}
# Rubans (rideaux de grappes) : largeur relative de chaque segment
_LR = {2: (1.0, 0.56), 3: (1.0, 0.62, 0.34), 4: (1.0, 0.7, 0.46, 0.26)}
_LG = {2: (1.0, 0.68), 3: (1.0, 0.78, 0.58), 4: (1.0, 0.82, 0.66, 0.5), 5: (1.0, 0.85, 0.71, 0.57, 0.45)}


# ---------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------

def _local(dx, dz, yaw):
    """Monde → repère d'un bloc tourné de `yaw` (même convention que kit.rot_y)."""
    a = math.radians(yaw)
    ca, sa = math.cos(a), math.sin(a)
    return ca * dx - sa * dz, sa * dx + ca * dz


def _monde(lx, lz, yaw):
    a = math.radians(yaw)
    ca, sa = math.cos(a), math.sin(a)
    return ca * lx + sa * lz, -sa * lx + ca * lz


def _poutre(b, p0, p1, w, d, col, twist=0.0, ext0=0.0, ext1=0.0, **kw):
    """Bloc de section w × d dont l'axe Y local va de p0 à p1 (prolongé de ext0 / ext1 aux bouts), vrillé de
    `twist` degrés autour de son axe : tiges, branches, bambous, brins d'herbe."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    v = p1 - p0
    u = v / np.linalg.norm(v)
    ref = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    x = np.cross(u, ref)
    x /= np.linalg.norm(x)
    z = np.cross(x, u)
    R = np.column_stack([x, u, z]) @ rot_y(twist)
    a, e = p0 - u * ext0, p1 + u * ext1
    return b.part("block", (w, float(np.linalg.norm(e - a)), d), (a + e) / 2, R, col, **kw)


def _dist_segments(p1, q1, p2, q2) -> float:
    """Distance minimale entre deux segments 3D."""
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e, f = d1 @ d1, d2 @ d2, d2 @ r
    if a < 1e-9 and e < 1e-9:
        return float(np.linalg.norm(r))
    if a < 1e-9:
        s, t = 0.0, min(max(f / e, 0.0), 1.0)
    else:
        cc = d1 @ r
        if e < 1e-9:
            t, s = 0.0, min(max(-cc / a, 0.0), 1.0)
        else:
            bb = d1 @ d2
            den = a * e - bb * bb
            s = min(max((bb * f - cc * e) / den, 0.0), 1.0) if den > 1e-9 else 0.0
            t = (bb * s + f) / e
            if t < 0:
                t, s = 0.0, min(max(-cc / a, 0.0), 1.0)
            elif t > 1:
                t, s = 1.0, min(max((bb - cc) / a, 0.0), 1.0)
    return float(np.linalg.norm((p1 + d1 * s) - (p2 + d2 * t)))


def _impair32(y):
    """Arrondit à un multiple impair de 1/32 de stud : les faces horizontales des grappes ne tombent jamais sur la
    grille du 1/16 où sont toutes les faces des masses de fleurs (pas de faces coplanaires possibles)."""
    return (math.floor(y * 16) + 0.5) / 16


def _sous(p0, p1, y):
    """Partie du segment [p0, p1] située sous la hauteur y (None si tout est au-dessus)."""
    if p0[1] > y and p1[1] > y:
        return None
    if p0[1] <= y and p1[1] <= y:
        return p0, p1
    t = (y - p0[1]) / (p1[1] - p0[1])
    q = p0 + (p1 - p0) * t
    return (p0, q) if p0[1] <= y else (q, p1)


def _rects_chevauchent(r1, r2, marge=0.05) -> bool:
    """Deux rectangles (x, z, demi-largeur, demi-profondeur, yaw) se recouvrent-ils (axes séparateurs) ?"""
    x1, z1, a1, b1, y1 = r1
    x2, z2, a2, b2, y2 = r2
    d = np.array([x2 - x1, z2 - z1])

    def axes(yaw):
        t = math.radians(yaw)
        return np.array([math.cos(t), -math.sin(t)]), np.array([math.sin(t), math.cos(t)])

    A, B = axes(y1), axes(y2)
    for ax in (*A, *B):
        ra = a1 * abs(A[0] @ ax) + b1 * abs(A[1] @ ax)
        rb = a2 * abs(B[0] @ ax) + b2 * abs(B[1] @ ax)
        if abs(d @ ax) > ra + rb + marge:
            return False
    return True


def _cadre(b, n0):
    """Bornes (repère de l'asset) des pièces ajoutées depuis n0, et matrice monde → repère de l'asset."""
    o = b.to_world((0, 0, 0))
    M = np.vstack([b.to_world(e) - o for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))])
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    signes = [(sx, sy, sz) for sx in (1, -1) for sy in (1, -1) for sz in (1, -1)]
    for p in b.parts[n0:]:
        R = np.asarray(p.rot, float).reshape(3, 3)
        half = np.asarray(p.size, float) / 2
        for s in signes:
            loc = M @ (np.asarray(p.pos, float) + R @ (half * s) - o)
            lo, hi = np.minimum(lo, loc), np.maximum(hi, loc)
    return lo, hi, M


def _infos(b, n0) -> dict:
    """Emprise (x, z) et hauteur réelles des pièces ajoutées depuis n0, dans le repère de l'asset."""
    lo, hi, _ = _cadre(b, n0)
    if not np.isfinite(lo).all():
        return {"emprise": (0, 0), "hauteur": 0}
    return {"emprise": (round(float(hi[0] - lo[0]), 1), round(float(hi[2] - lo[2]), 1)), "hauteur": round(float(hi[1]), 1)}


def _recentrer(b, n0, x=True, z=True):
    """Décale les pièces ajoutées depuis n0 pour que leur emprise au sol soit centrée sur l'origine de l'asset."""
    lo, hi, M = _cadre(b, n0)
    if not np.isfinite(lo).all():
        return
    d = np.array([-(lo[0] + hi[0]) / 2 if x else 0.0, 0.0, -(lo[2] + hi[2]) / 2 if z else 0.0])
    d = np.round(d * 4) / 4
    if not d.any():
        return
    dw = M.T @ d
    for p in b.parts[n0:]:
        p.pos = tuple(round(float(v), 4) for v in np.asarray(p.pos, float) + dw)


def _bornes(top, embed, L, n, rng):
    """Hauteurs des n + 1 bornes des segments d'une grappe (du haut vers la pointe), longueurs un peu irrégulières,
    chaque borne sur un multiple impair de 1/32 (voir `_impair32`)."""
    fr = np.asarray(_FR[n]) * rng.uniform(0.88, 1.12, n)
    fr = fr / fr.sum()
    ys = [top]
    for i in range(n):
        ys.append(ys[-1] - (L * fr[i] + (embed if i == 0 else 0.0)))
    ys = [_impair32(v) for v in ys]
    for i in range(1, n + 1):  # chaque segment garde au moins 1/4 de stud
        ys[i] = min(ys[i], ys[i - 1] - 0.25)
    return ys


class _Arbre:
    """Atelier d'un arbre à glycines : cotes de conception (taille 1) multipliées par `t`, registre des blocs de
    fleurs (plafonds où accrocher les grappes), du bois (obstacles) et des grappes posées, budget de pièces.

    `interdit = (x0, y0)` : aucune grappe dont l'emprise entre dans |x| < x0 ne descend sous y0 (arche)."""

    def __init__(self, b, t=1.0, teinte="mauve", budget=90, interdit=None, melange=None):
        self.b = b
        self.t = float(t)
        self.rng = b.rng
        self.n0 = len(b.parts)
        self.budget = budget
        self.g = TEINTES.get(teinte, TEINTES["mauve"])
        self.interdit = interdit
        self.melange = melange  # (teinte, proportion) : une grappe sur n prend cette autre teinte
        self.plafonds = []  # (cx, cz, sx, sz, yaw, y_bas, y_haut, masse)
        self.masses = []    # (cx, cz, w, d, rot, y_bas, y_haut du corps)
        self.bois = []      # (p0, p1, demi-épaisseur)
        self.grappes = []   # (x, z, demi-largeur, demi-profondeur, yaw, y_haut, y_bas)
        self._m = -1
        self._fams = []     # (cx, cz, demi-largeur, demi-profondeur, rot, famille)
        self.dessous = 0.4  # semelle des masses : mélange glycine_nuit → glycine_fonce

    def p(self, *v):
        return tuple(float(x) * self.t for x in v)

    def reste(self) -> int:
        return self.budget - (len(self.b.parts) - self.n0)

    def V(self, col, a=0.03):
        return vary(col, self.rng, a)

    # -- bois --------------------------------------------------------------
    def ecorce(self, ton=0):
        return self.V((TRONC, TRONC_CLAIR, mix(TRONC, TRONC_CLAIR, 0.5))[ton % 3], 0.04)

    def tige(self, pts, w, col, torsions=None, name="Tronc", collide=True, obstacle=True):
        """Tige en segments inclinés et vrillés ; le premier segment, s'il part du sol, y est un peu enfoncé
        pour qu'aucun coin ne flotte."""
        pts = [np.asarray(q, float) for q in pts]
        n = len(pts) - 1
        for i in range(n):
            p0, p1 = pts[i], pts[i + 1]
            u = (p1 - p0) / np.linalg.norm(p1 - p0)
            if i == 0 and p0[1] <= 1e-6:
                horiz = math.sqrt(max(0.0, 1.0 - u[1] ** 2))
                e0 = (w * 0.72 * horiz + 0.1) / max(u[1], 0.3)
            else:
                e0 = w * 0.45
            e1 = w * 0.45 if i < n - 1 else w * 0.3
            tw = torsions[i % len(torsions)] if torsions else 0.0
            if obstacle:
                self.bois.append((p0, p1, w * 0.72))
            _poutre(self.b, self.p(*p0), self.p(*p1), w * self.t, w * self.t, col, tw, e0 * self.t, e1 * self.t,
                    name=name, collide=collide)

    def racines(self, cx, cz, specs, col=None):
        """Racines en coins rayonnants : (angle, longueur, hauteur, largeur)."""
        for (ang, lg, h, lw) in specs:
            with self.b.at(self.p(cx, 0, cz), yaw=ang):
                self.b.wedge(self.p(-lw / 2, 0, 0.2), self.p(lw / 2, h, 0.2 + lg),
                             self.V(col or shade(TRONC, 0.86), 0.04), down="+z", name="Racine")

    # -- fleurs et feuilles -------------------------------------------------
    def bloc(self, cx, y0, cz, sx, sy, sz, col, yaw=0.0, plafond=True, **kw):
        kw.setdefault("studs", "top")
        kw.setdefault("collide", False)
        kw.setdefault("name", "Fleurs")
        if plafond:
            self.plafonds.append((cx, cz, sx, sz, yaw, y0, y0 + sy, self._m))
        return self.b.boxc(self.p(cx, y0 + sy / 2, cz), self.p(sx, sy, sz), col, yaw=yaw, **kw)

    def masse(self, cx, y0, cz, w, d, h, rot=0.0, detail=3):
        """Masse de fleurs plate, du sombre (dessous) au clair (sommet ensoleillé).
        detail 0 : plaque seule ; 1 : corps + sommet ; 2 : + semelle sombre dessous ; 3 : + corps tourné de 45°
        (contour octogonal) et étage. Renvoie le haut."""
        nuit, fonce, mauve, claire, _pale = self.g
        self._m += 1
        self.masses.append((cx, cz, w, d, rot, y0, y0 + h))
        if detail <= 0:  # simple plaque (nappe de treille)
            self.bloc(cx, y0, cz, w, h, d, self.V(mix(fonce, mauve, 0.6)), rot)
            return y0 + h
        if detail >= 2:  # semelle sombre, un peu en retrait : le dessous se lit d'en bas
            self.bloc(cx, y0 - 0.5, cz, w - 0.4, 0.5, d - 0.4, self.V(mix(nuit, fonce, self.dessous)), rot,
                      studs="none", name="Dessous")
        self.bloc(cx, y0, cz, w, h, d, self.V(mix(fonce, mauve, 0.45)), rot)
        top = y0 + h
        if detail >= 3:
            s = round(min(w, d) * 0.86 * 2) / 2
            self.bloc(cx + 0.25, y0 + 0.5, cz - 0.25, s, h, s, self.V(mix(fonce, mauve, 0.75)), rot + 45)
            he = max(1.5, round(h * 0.6 * 2) / 2)
            hc = max(1.0, round(h * 0.4 * 2) / 2)
            # deux bouffées décalées, l'une plus haute et plus claire : un dessus en nuage, pas en pièce montée
            ox, oz = _monde(w * 0.14, -d * 0.1, rot)
            self.bloc(cx + ox, top, cz + oz, round(w * 0.6 * 2) / 2, he, round(d * 0.56 * 2) / 2,
                      self.V(mix(mauve, claire, 0.25)), rot + 14)
            ox, oz = _monde(-w * 0.17, d * 0.14, rot)
            e = round(min(w, d) * 0.42 * 2) / 2
            self.bloc(cx + ox, top, cz + oz, e, he + hc, e, self.V(mix(claire, _pale, 0.25)), rot + 45)
            return top + he + hc
        hc = max(1.0, round(h * 0.5 * 2) / 2)
        e = round(min(w, d) * 0.56 * 2) / 2
        self.bloc(cx + 0.25, top, cz - 0.25, e, hc, e, self.V(mix(mauve, claire, 0.5)), rot + 45)
        return top + hc

    def famille(self, cx, cz, w, d, rot) -> float:
        """Famille de hauteurs (fraction modulo 0,5 sur la grille du 1/16) qu'aucune masse voisine n'utilise :
        coloration gloutonne du graphe des recouvrements, 8 familles disponibles."""
        prises = {f for (x, z, a, bb, r, f) in self._fams
                  if _rects_chevauchent((cx, cz, w / 2 + 1.5, d / 2 + 1.5, rot), (x, z, a, bb, r), 0.0)}
        f = next((k / 16 for k in (0, 3, 6, 1, 4, 7, 2, 5) if k / 16 not in prises), 0.0)
        self._fams.append((cx, cz, w / 2 + 1.5, d / 2 + 1.5, rot, f))
        return f

    def feuilles(self, cx, y0, cz, sx, sy, sz, yaw=0.0, ton=1):
        return self.bloc(cx, y0, cz, sx, sy, sz, self.V(FEUILLES[ton % 3], 0.04), yaw, plafond=False, name="Feuilles")

    def feuilles_sur(self, im, fx, fz, sx, sz, yaw=0.0, ton=1):
        """Bouquet de feuilles posé sur le corps de la masse n° im, en (fx, fz) ∈ [-1, 1] de sa demi-emprise.
        Hauteurs sur le 1/32 de stud impair : jamais au niveau d'une face de masse (grille du 1/16)."""
        cx, cz, w, d, rot, _y0, y1 = self.masses[im]
        dx, dz = _monde(fx * w / 2, fz * d / 2, rot)
        return self.feuilles(cx + dx, y1 - 0.15625, cz + dz, sx, 0.875, sz, rot + yaw, ton)

    # -- grappes -------------------------------------------------------------
    def accroche(self, x, z, r, L):
        """Bloc de fleurs le plus bas au-dessus de la grappe (il couvre son centre, avec un petit retrait) :
        (y_bas, y_haut), ou None si rien ne la porte ou si elle traverserait un autre bloc plus bas."""
        best = None
        for (cx, cz, sx, sz, yaw, y0, y1, _m) in self.plafonds:
            lx, lz = _local(x - cx, z - cz, yaw)
            if abs(lx) <= sx / 2 - 0.3 * r and abs(lz) <= sz / 2 - 0.3 * r and (best is None or y0 < best[0]):
                best = (y0, y1)
        if best is None or self.traverse(x, z, r, best[0], best[0] - L):
            return None
        return best

    def traverse(self, x, z, r, y_haut, y_bas, sauf=None) -> bool:
        """Vrai si une grappe (x, z, r) entre y_bas et y_haut traverserait un bloc de fleurs (sauf ceux de la masse
        `sauf`)."""
        for (cx, cz, sx, sz, yaw, y0, y1, m) in self.plafonds:
            if m == sauf:
                continue
            lx, lz = _local(x - cx, z - cz, yaw)
            if abs(lx) < sx / 2 + r and abs(lz) < sz / 2 + r and y0 < y_haut - 1e-6 and y1 > y_bas - 0.05:
                return True
        return False

    def place_libre(self, x, z, a, bb, yaw, y_haut, y_bas, r_bois) -> bool:
        """Vrai si l'emprise (rectangle a × bb tourné de yaw) est libre entre y_bas et y_haut : pas d'autre grappe
        et pas de bois sous le point d'accroche."""
        for g in self.grappes:
            gx, gz, ga, gb, gyaw, gyt, gyb = g
            if gyb < y_haut and y_bas < gyt and _rects_chevauchent((x, z, a, bb, yaw), (gx, gz, ga, gb, gyaw)):
                return False
        top, bot = np.array([x, y_haut, z]), np.array([x, y_bas, z])
        for (p0, p1, hw) in self.bois:
            # seul compte le bois sous le point d'accroche (au-dessus, il est noyé dans les fleurs)
            q = _sous(p0, p1, y_haut - 0.1)
            if q is not None and _dist_segments(top, bot, q[0], q[1]) < hw + r_bois:
                return False
        return True

    def _longueur(self, x, L, demi):
        """Longueur autorisée (zone interdite de l'arche : rien sous y0 au-dessus de |x| < x0)."""
        if self.interdit is not None:
            x0, y0 = self.interdit
            if abs(x) - demi < x0:
                return lambda y: min(L, y - y0 - 0.25)
        return lambda y: L

    def grappe(self, x, z, L, larg=1.6, y=None, n=None, s0=None, embed=0.5, sauf=None) -> bool:
        """Grappe pendante (colonne) de longueur L sous son point d'accroche : 2 à 5 segments qui s'affinent et
        pâlissent vers la pointe, un peu tournés et décalés. Accrochée au plafond le plus bas (ou à la hauteur `y`
        donnée, noyée de `embed` dans ce qui la porte). Renvoie False si elle n'a pas sa place."""
        rng = self.rng
        r = larg * 0.75
        if y is None:
            a = self.accroche(x, z, r, L)
            if a is None:
                return False
            y, embed = a[0], min(embed, a[1] - a[0] - 0.05)
        elif self.traverse(x, z, r, y, y - L, sauf):
            return False
        L = self._longueur(x, L, r + 0.12)(y)
        if L < 1.6:
            return False
        yaw = float(rng.uniform(0, 90))
        if not self.place_libre(x, z, larg / 2, larg / 2, yaw, y + embed, y - L, r):
            return False
        n = n or (2 if L < 4.6 else 3 if L < 8.2 else 4 if L < 11.5 else 5)
        n = min(n, self.reste())
        if n < 2:
            return False
        cols = self.degrade(n, s0)
        ys = _bornes(y + embed, embed, L, n, rng)
        for i in range(n):
            h = ys[i] - ys[i + 1]
            wi = larg * _LG[n][i]
            jx, jz = (rng.uniform(-0.05, 0.05, 2) * larg) if i else (0.0, 0.0)
            dyaw = float(rng.uniform(-8, 8)) if i else 0.0
            self.b.boxc(self.p(x + jx, ys[i] - h / 2, z + jz), self.p(wi, h, wi), cols[i],
                        yaw=yaw + dyaw, studs="none", collide=False, name="Grappe")
        self.grappes.append((x, z, larg / 2, larg / 2, yaw, y + embed, y - L))
        return True

    def ruban(self, x, z, L, larg, yaw, y, embed, sauf=None, n=None, s0=None, ep=0.5) -> bool:
        """Rideau de grappes : lame de largeur `larg` (posée le long d'un bord), 2 à 4 segments qui se rétrécissent
        en escalier irrégulier (chaque segment est décalé d'un côté) et pâlissent vers la pointe. De face, on lit
        plusieurs grappes de longueurs inégales ; de profil, une grappe fine."""
        rng = self.rng
        demi = larg / 2
        if self.traverse(x, z, demi, y, y - L, sauf):
            return False
        t = math.radians(yaw)  # demi-emprise réelle en x de la lame tournée (les segments du bas restent dedans)
        L = self._longueur(x, L, demi * abs(math.cos(t)) + ep / 2 * abs(math.sin(t)) + 0.12)(y)
        if L < 1.6:
            return False
        if not self.place_libre(x, z, demi, ep / 2, yaw, y + embed, y - L, 0.6 * demi + 0.2):
            return False
        n = n or (2 if L < 5.0 else 3 if L < 9.0 else 4)
        n = min(n, self.reste())
        if n < 2:
            return False
        cols = self.degrade(n, s0)
        ys = _bornes(y + embed, embed, L, n, rng)
        off, wprev = 0.0, larg
        for i in range(n):
            h = ys[i] - ys[i + 1]
            wi = larg * _LR[n][i]
            if i:
                jeu = (wprev - wi) / 2
                off += float(rng.choice((-1, 1))) * jeu * float(rng.uniform(0.35, 0.95))
            dx, dz = _monde(off, 0.0, yaw)
            self.b.boxc(self.p(x + dx, ys[i] - h / 2, z + dz), self.p(wi, h, ep * (1 - 0.12 * i)), cols[i],
                        yaw=yaw, studs="none", collide=False, name="Grappe")
            wprev = wi
        self.grappes.append((x, z, demi, ep / 2, yaw, y + embed, y - L))
        return True

    def degrade(self, n, s0=None):
        """Couleurs des n segments, prises sur la rampe foncé → mauve → clair → pointe : départ s0 (plus ou moins
        sombre selon la grappe), pointe toujours pâle."""
        _nuit, fonce, mauve, claire, pale = self.g
        if self.melange and self.rng.uniform() < self.melange[1]:
            _nuit, fonce, mauve, claire, pale = TEINTES[self.melange[0]]
        if s0 is None:
            s0 = float(self.rng.uniform(0.08, 0.45))
        stops = ((0.0, fonce), (0.33, mauve), (0.68, claire), (1.0, pale))

        def rampe(s):
            for (a, ca), (b_, cb) in zip(stops, stops[1:]):
                if s <= b_:
                    return mix(ca, cb, (s - a) / (b_ - a))
            return pale

        out = []
        for i in range(n):
            s = s0 + (1.0 - s0) * (i / (n - 1)) ** 0.9
            out.append(self.V(rampe(min(1.0, s)), 0.025))
        return out

    def frange(self, im, n, L, larg=1.5, vague=0.55, nseg=None, ep=0.5, differe=False, faces=None):
        """Rideau de n grappes en rubans tangents au bord de la masse n° im : ils partent du haut du flanc (qu'ils
        habillent) et pendent de L[0] à L[1] sous la masse, longueurs qui ondulent autour d'elle (ourlet festonné)
        avec une part d'aléatoire. `faces="z"` : seulement les bords qui regardent ±Z. `differe` : renvoie les
        poses à faire au lieu de les faire (pour les répartir entre plusieurs masses, voir `_franges`)."""
        rng = self.rng
        cx, cz, w, d, rot, y0, y1 = self.masses[im]
        ph2 = rng.uniform(0, 2 * math.pi)
        out = []
        # contour en rectangle arrondi (super-ellipse p = 8), le ruban dépasse du flanc de 0,15
        ax, az = w / 2 + 0.15 - ep / 2, d / 2 + 0.15 - ep / 2
        ts = np.linspace(0, 2 * math.pi, 361)
        ct, st = np.cos(ts), np.sin(ts)
        px = ax * np.sign(ct) * np.abs(ct) ** 0.25
        pz = az * np.sign(st) * np.abs(st) ** 0.25
        seg = np.hypot(np.diff(px), np.diff(pz))
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        per = cum[-1]
        pas = per / n
        s_dep = rng.uniform(0, pas)
        for i in range(n):
            sx = (s_dep + i * pas + rng.uniform(-0.15, 0.15) * pas) % per
            k = int(np.searchsorted(cum, sx, side="right") - 1)
            k = min(max(k, 0), len(seg) - 1)
            f = (sx - cum[k]) / max(seg[k], 1e-9)
            lx, lz = px[k] + (px[k + 1] - px[k]) * f, pz[k] + (pz[k + 1] - pz[k]) * f
            dx, dz = _monde(lx, lz, rot)
            wtx, wtz = _monde(px[k + 1] - px[k], pz[k + 1] - pz[k], rot)  # tangente au bord
            if faces == "z" and abs(wtx) < 0.75 * math.hypot(wtx, wtz):
                continue
            yaw = math.degrees(math.atan2(-wtz, wtx)) + float(rng.uniform(-10, 10))
            s = 0.5 + 0.5 * math.sin(3 * math.atan2(lz / az, lx / ax) + ph2)
            Lg = L[0] + (L[1] - L[0]) * (vague * s + (1 - vague) * rng.uniform())
            yh = y1 - 0.25 - float(rng.uniform(0.0, 0.35))
            out.append((self.ruban, (cx + dx, cz + dz, Lg, larg * rng.uniform(0.85, 1.15), yaw, y0, yh - y0),
                        dict(sauf=im, n=nseg, ep=ep)))
        return out if differe else [fn(*a, **kw) for fn, a, kw in out]

    def remplir(self, L, larg=1.4, essais=900, bord=0.7, reserve=0, quota=None, masses=None):
        """Passe de remplissage : des grappes sous les grandes masses jusqu'à épuisement du budget (ou jusqu'à
        `quota` pièces posées par cet appel ; `masses` : n'utiliser que ces masses)."""
        rng = self.rng
        n_dep = len(self.b.parts)
        grands = [q for q in self.plafonds if min(q[2], q[3]) >= 2 * larg + 1 and (masses is None or q[7] in masses)]
        if not grands:
            return
        aires = np.array([q[2] * q[3] for q in grands], float)
        pr = aires / aires.sum()
        for _ in range(essais):
            if self.reste() - reserve < 2 or (quota is not None and len(self.b.parts) - n_dep >= quota):
                break
            cx, cz, sx, sz, yaw, _y0, _y1, _m = grands[int(rng.choice(len(grands), p=pr))]
            r = larg * 0.8 + 0.1
            th = rng.uniform(0, 2 * math.pi)
            f = rng.uniform(0.7, 1.0) if rng.uniform() < bord else rng.uniform(0.0, 0.7)
            dx, dz = _monde((sx / 2 - r) * f * math.cos(th), (sz / 2 - r) * f * math.sin(th), yaw)
            self.grappe(cx + dx, cz + dz, float(rng.uniform(*L)), larg * rng.uniform(0.9, 1.1))


def _franges(T, specs, ep=0.5):
    """Pose les rideaux de plusieurs masses à tour de rôle (une grappe de chaque masse, puis la suivante…) : si le
    budget s'épuise, toutes les masses restent habillées de façon égale. specs : (masse, nombre, (Lmin, Lmax),
    largeur[, segments, faces, poids]) ; une masse de poids p pose p grappes par tour."""
    files = [T.frange(im, n, L, larg, nseg=opt[0] if opt else None, ep=ep, differe=True,
                      faces=opt[1] if len(opt) > 1 else None)
             for (im, n, L, larg, *opt) in specs]
    poids = [opt[2] if len(opt) > 2 else 1 for (_im, _n, _L, _l, *opt) in specs]
    k = 0
    while any(files) and T.reste() >= 2:
        f = files[k % len(files)]
        for _ in range(poids[k % len(files)]):  # une masse de poids p pose p grappes par tour
            if f and T.reste() >= 2:
                fn, a, kw = f.pop(0)
                fn(*a, **kw)
        k += 1


def _construire(T, S):
    """Construit un arbre décrit par un dictionnaire de spécifications (tiges, racines, branches, masses, feuilles,
    franges, grappes de branches, remplissage)."""
    b = T.b
    with b.group("Bois"):
        for (pts, w, ton, tors) in S["tiges"]:
            T.tige(pts, w, T.ecorce(ton), tors)
        T.racines(*S["pied"], S["racines"])
        for (pts, w, tw) in S.get("branches", ()):
            T.tige(pts, w, T.ecorce(0), (tw,), name="Branche")
    with b.group("Fleurs"):
        for m in S["masses"]:
            T.masse(*m)
        for f in S.get("feuilles", ()):
            T.feuilles_sur(*f)
    with b.group("Grappes"):
        _franges(T, S["franges"], S.get("ep", 0.5))
        L, larg = S["remplir"]
        T.remplir(L, larg)


# ---------------------------------------------------------------------------
# Glycine (arbre de l'allée)
# ---------------------------------------------------------------------------

# Cotes à taille 1. masses : (cx, y0, cz, largeur, profondeur, hauteur, rotation, détail) — chaque y0 a sa propre
# partie fractionnaire modulo 0,5 (.0, .0625, .125, .1875, .25, .3125, .375, .4375).
# franges : (masse, nombre, (Lmin, Lmax), largeur) ; branches : (points, largeur, torsion).
GLYCINES = [
    # 0 : parasol — tronc tressé droit, ombrelle bombée : un plateau central et quatre lobes plus bas tout autour
    dict(
        tiges=[([(-0.4, 0, 0.2), (0.6, 4.5, -0.4), (-0.4, 8.5, 0.3), (0.2, 12.4, 0.0)], 2.0, 0, (12, 38, 64)),
               ([(1.1, 0, -0.7), (-0.9, 3.8, 0.6), (0.9, 7.6, 0.7), (-0.3, 11.4, -0.4)], 1.3, 1, (-20, 15, -35))],
        pied=(0.2, 0.0),
        racines=[(25, 2.6, 1.5, 1.4), (150, 2.4, 1.2, 1.3), (265, 2.8, 1.4, 1.4)],
        branches=[([(0.2, 10.4, 0.0), (6.2, 11.9, 1.6)], 1.1, 20),
                  ([(-0.2, 9.4, 0.0), (-6.1, 10.7, -1.4)], 1.1, -15),
                  ([(0.0, 10.4, -0.3), (1.3, 11.6, -5.8)], 1.0, 30),
                  ([(0.0, 9.8, 0.3), (-1.5, 11.0, 5.8)], 1.0, -25)],
        masses=[(0.3, 12.0, 0.0, 12, 11, 2.5, 10, 3),
                (6.4, 11.0625, 1.6, 7.5, 6.5, 2.0, -12, 1),
                (-6.3, 9.875, -1.4, 7.5, 7, 2.0, 20, 1),
                (1.3, 10.8125, -6.0, 7, 6.5, 2.0, 5, 1),
                (-1.5, 10.1875, 6.0, 6.5, 6.5, 2.0, -25, 1)],
        feuilles=[(1, 0.55, 0.3, 3.2, 2.2, 35, 2), (2, -0.5, -0.2, 2.8, 2.4, -20, 1), (0, -0.45, -0.5, 2.6, 2.0, 15, 2)],
        franges=[(1, 13, (2.5, 8.0), 1.5), (2, 13, (2.5, 8.0), 1.5), (3, 13, (3.0, 8.5), 1.5),
                 (4, 12, (2.5, 7.5), 1.5), (0, 14, (2.0, 5.0), 1.5)],
        remplir=((2.5, 6.0), 0.85),
    ),
    # 1 : penché — tronc qui s'incline vers l'avant (-Z), auvent de fleurs en surplomb aux grappes les plus longues,
    #     une branche basse vers l'arrière fait contrepoids
    dict(
        tiges=[([(0.0, 0, 2.4), (0.5, 4.0, 0.8), (-0.5, 8.0, -1.4), (0.3, 11.5, -3.4), (0.0, 14.0, -4.4)], 2.1, 0,
                (8, 30, 52, 70)),
               ([(-1.1, 0, 3.0), (0.9, 3.4, 1.6), (-0.8, 7.0, -0.2), (0.7, 10.6, -2.6)], 1.3, 1, (-15, 20, -30))],
        pied=(0.0, 2.6),
        racines=[(10, 2.6, 1.5, 1.4), (125, 2.2, 1.2, 1.2), (235, 2.6, 1.4, 1.3)],
        branches=[([(0.3, 6.2, 1.0), (1.2, 8.4, 4.6), (0.8, 10.4, 7.4)], 1.0, 15),
                  ([(-0.3, 12.0, -3.6), (-5.6, 12.8, -4.8)], 1.0, -20),
                  ([(0.3, 12.0, -3.8), (5.0, 12.6, -6.6)], 1.0, 25)],
        masses=[(0.0, 13.5, -4.6, 12, 10, 2.5, -6, 3),
                (0.5, 12.3125, -9.4, 10, 5.5, 2.0, 8, 1),
                (-6.0, 12.4375, -4.6, 5.5, 6, 2.0, 15, 1),
                (5.6, 12.1875, -6.4, 5.5, 5.5, 2.0, -20, 1),
                (0.8, 9.875, 7.4, 7, 6, 2.0, 10, 1)],
        feuilles=[(2, -0.4, 0.3, 2.8, 2.6, 25, 2), (4, 0.4, 0.5, 2.8, 2.0, -15, 1), (0, 0.5, 0.6, 2.6, 2.0, 10, 2)],
        franges=[(1, 16, (5.0, 9.5), 1.5), (2, 9, (3.0, 7.5), 1.5), (3, 9, (3.0, 7.5), 1.5),
                 (4, 12, (3.0, 6.5), 1.5), (0, 13, (2.5, 6.0), 1.5)],
        remplir=((3.0, 6.5), 0.85),
    ),
    # 2 : fourchu — deux fûts qui s'écartent en V, deux ombrelles à des hauteurs différentes
    dict(
        tiges=[([(0.0, 0, 0.0), (0.4, 3.6, 0.3)], 2.4, 0, (15,)),
               ([(0.0, 3.0, 0.2), (-1.9, 7.0, 0.7), (-3.3, 10.4, 0.1), (-4.0, 13.2, 0.4)], 1.6, 0, (30, 50, 70)),
               ([(0.5, 3.0, 0.0), (2.0, 7.5, -0.6), (2.7, 12.0, 0.3), (3.6, 16.4, -0.4)], 1.7, 1, (-10, -35, -55)),
               ([(1.3, 0, 0.9), (1.5, 4.5, -1.1), (2.9, 9.0, 0.9), (2.4, 12.5, -0.9)], 0.8, 2, (0, 20, 40))],
        pied=(0.3, 0.2),
        racines=[(40, 2.6, 1.6, 1.5), (170, 2.4, 1.3, 1.3), (290, 2.8, 1.5, 1.4)],
        branches=[([(-3.4, 11.4, 0.2), (-8.0, 12.2, -1.0)], 0.9, 10),
                  ([(3.0, 14.6, -0.2), (7.8, 15.4, 1.2)], 0.9, -10)],
        masses=[(-4.6, 12.5, 0.4, 10, 9, 2.0, -15, 3),
                (4.0, 15.8125, -0.3, 9.5, 9, 2.0, 20, 3),
                (-8.6, 11.6875, -1.2, 5.5, 5.5, 2.0, 10, 1),
                (8.2, 14.9375, 1.4, 5.5, 5.5, 2.0, -10, 1)],
        feuilles=[(0, 0.5, 0.55, 3.0, 2.2, 30, 2), (1, 0.45, -0.5, 2.6, 2.4, -25, 1)],
        franges=[(2, 10, (2.5, 7.0), 1.5), (3, 10, (3.5, 8.5), 1.5), (0, 14, (2.5, 7.0), 1.5),
                 (1, 14, (4.0, 9.0), 1.5)],
        remplir=((2.5, 6.5), 0.85),
    ),
    # 3 : fontaine — tronc haut, dôme en deux étages et rideau continu de longues grappes tout autour
    dict(
        tiges=[([(0.0, 0, 0.0), (0.6, 5.0, 0.4), (-0.4, 10.0, -0.3), (0.2, 15.0, 0.2)], 2.0, 0, (10, 34, 58)),
               ([(1.0, 0, -0.6), (-0.8, 4.5, 0.7), (0.8, 9.5, 0.6), (-0.3, 14.3, -0.5)], 1.2, 1, (-15, 20, -30))],
        pied=(0.1, 0.0),
        racines=[(30, 2.6, 1.5, 1.4), (150, 2.6, 1.3, 1.3), (270, 2.4, 1.4, 1.3)],
        branches=[([(0.0, 13.0, 0.0), (4.6, 14.6, 2.6)], 0.9, 20),
                  ([(0.0, 13.0, 0.0), (-4.8, 14.7, 1.6)], 0.9, -20),
                  ([(0.0, 13.2, 0.0), (0.6, 14.7, -5.0)], 0.9, 40)],
        masses=[(0.0, 14.5, 0.0, 15, 15, 2.0, 0, 3),
                (0.3, 17.5625, -0.2, 8, 8, 2.0, 22, 1)],
        feuilles=[(0, 0.6, -0.55, 3.0, 2.2, 20, 2), (0, -0.55, 0.5, 2.6, 2.8, -30, 1)],
        franges=[(0, 35, (7.0, 10.5), 1.5, 3)],
        remplir=((2.5, 5.0), 0.85),
    ),
]


def glycine(b, variant: int = 0, taille: float = 1.0, teinte: str = "mauve") -> dict:
    """Glycine de l'allée (14 à 22 studs à taille 1), quatre silhouettes : 0 parasol, 1 penché vers l'avant (-Z),
    2 fourchu à deux ombrelles, 3 fontaine (rideau de longues grappes). Tronc tordu en tiges tressées, masses de
    fleurs plates, 20 à 25 grappes qui pâlissent vers la pointe. `teinte` : "mauve" (défaut), "violet" ou "blanc".
    ≤ 90 pièces."""
    T = _Arbre(b, taille, teinte, budget=90)
    with b.group("Glycine"):
        _construire(T, GLYCINES[variant % 4])
    _recentrer(b, T.n0)
    return _infos(b, T.n0)


# ---------------------------------------------------------------------------
# Glycine géante (repère, fond de décor)
# ---------------------------------------------------------------------------

def _rayon(theta, R, y):
    """Point à l'angle `theta` (degrés, depuis +Z vers +X) et à la distance R de l'axe."""
    a = math.radians(theta)
    return (R * math.sin(a), y, R * math.cos(a))


def _geante_couronne(angles, R1, R2, yb, y1, y2, sats, w=13, d=12, h=2.5):
    """Branches maîtresses (deux segments, du tronc vers chaque lobe) et lobes satellites à leur bout."""
    branches, masses = [], []
    for (th, y0), rot in zip(zip(angles, sats), (14, -18, 9, -6, 21, -12)):
        branches.append(([(0.0, yb, 0.0), _rayon(th, R1, y1), _rayon(th + 8, R2, y2)], 2.2, rot))
        x, _, z = _rayon(th + 8, R2 + 1, 0)
        masses.append((round(x, 2), y0, round(z, 2), w, d, h, rot, 2))
    return branches, masses


_B0, _M0 = _geante_couronne((18, 90, 162, 234, 306), 7.5, 14.0, 19.5, 22.0, 23.0,
                            (22.0625, 22.4375, 21.6875, 22.3125, 22.125))
_B3, _M3 = _geante_couronne((40, 130, 220, 310), 7.0, 13.0, 17.5, 19.5, 20.5,
                            (19.5625, 19.9375, 19.1875, 19.8125), w=14, d=12, h=2.5)

GEANTES = [
    # 0 : dôme — trois fûts tressés, cinq branches maîtresses, large ombrelle bombée (≈ 50 × 50, 31 de haut)
    dict(
        tiges=[([(-1.0, 0, 0.6), (1.4, 6.5, -0.9), (-0.9, 13, 0.9), (0.8, 18.5, -0.5), (0.0, 24.5, 0.0)], 4.2, 0,
                (10, 32, 54, 76)),
               ([(2.6, 0, -1.8), (-1.6, 5.5, 1.8), (1.9, 11.5, 1.4), (-0.9, 17.5, -1.5), (0.6, 23.5, 0.6)], 3.0, 1,
                (-12, 18, -26, 8)),
               ([(-2.6, 0, -2.0), (0.8, 4.5, -2.6), (2.6, 9.5, -0.4), (1.2, 15.0, 2.0)], 2.2, 2, (25, 50, 75))],
        pied=(0.0, 0.0),
        racines=[(15, 5.5, 3.0, 2.6), (85, 4.5, 2.5, 2.2), (160, 5.0, 2.8, 2.4), (230, 4.2, 2.2, 2.0),
                 (300, 5.2, 2.6, 2.4)],
        branches=_B0,
        masses=[(0.0, 24.0, 0.0, 24, 22, 3.0, 8, 3)] + _M0,
        feuilles=[(0, 0.6, -0.5, 4.0, 3.0, 25, 2), (0, -0.7, 0.4, 3.6, 3.2, -15, 1),
                  (2, 0.4, 0.4, 3.0, 2.6, 40, 2), (4, -0.4, -0.3, 3.4, 2.8, 10, 1)],
        franges=[(1, 22, (6.0, 12.0), 2.2), (2, 22, (6.0, 12.0), 2.2),
                 (3, 22, (6.0, 12.0), 2.2), (4, 22, (6.0, 12.0), 2.2),
                 (5, 22, (6.0, 12.0), 2.2), (0, 26, (4.0, 8.0), 2.2)],
        remplir=((4.0, 9.0), 1.2),
        ep=0.7,
    ),
    # 1 : penché — le géant s'incline vers l'avant (-Z) : grand auvent de longues grappes en surplomb,
    #     une branche basse vers l'arrière fait contrepoids
    dict(
        tiges=[([(0.0, 0, 6.0), (1.2, 7.0, 3.6), (-0.8, 14.0, 0.4), (0.6, 20.0, -3.4), (0.0, 26.5, -7.0)], 4.4, 0,
                (6, 28, 50, 72)),
               ([(2.4, 0, 7.6), (-1.8, 6.0, 5.2), (1.6, 12.5, 1.8), (-1.2, 18.5, -1.8), (0.8, 24.5, -5.6)], 3.0, 1,
                (-10, 20, -24, 6)),
               ([(-2.6, 0, 7.4), (0.4, 5.5, 6.8), (2.4, 10.5, 4.0), (1.0, 16.0, 1.0)], 2.2, 2, (25, 50, 75))],
        pied=(0.0, 6.0),
        racines=[(0, 5.5, 3.0, 2.6), (70, 4.6, 2.5, 2.2), (150, 5.0, 2.8, 2.4), (220, 4.4, 2.2, 2.0),
                 (290, 5.2, 2.6, 2.4)],
        branches=[([(0.0, 21.0, -4.0), (0.6, 23.5, -12.0), (-0.4, 24.5, -19.0)], 2.2, 12),
                  ([(0.0, 21.5, -4.5), (-8.0, 23.8, -7.0), (-14.0, 24.4, -9.5)], 2.0, -15),
                  ([(0.0, 21.5, -4.5), (8.0, 23.6, -7.5), (14.0, 24.2, -10.5)], 2.0, 20),
                  ([(0.6, 11.0, 2.6), (1.4, 14.0, 8.0), (1.0, 16.5, 13.0)], 1.8, 8)],
        masses=[(0.0, 26.0, -8.0, 24, 18, 3.0, -5, 3),
                (0.0, 23.3125, -19.5, 22, 9, 2.5, 6, 2),
                (-14.0, 23.4375, -9.5, 11, 12, 2.5, 15, 2),
                (14.0, 23.1875, -10.5, 11, 12, 2.5, -12, 2),
                (1.0, 16.0625, 13.5, 13, 10, 2.5, 8, 2)],
        feuilles=[(2, -0.5, 0.3, 3.6, 3.0, 20, 2), (0, 0.5, 0.6, 3.6, 2.8, -10, 1),
                  (4, 0.4, 0.5, 3.2, 2.6, 30, 2), (3, 0.3, -0.5, 3.2, 2.4, 0, 1)],
        franges=[(1, 24, (8.0, 14.0), 2.2), (2, 16, (6.0, 11.0), 2.2),
                 (3, 16, (6.0, 11.0), 2.2), (4, 18, (5.0, 9.0), 2.2),
                 (0, 22, (4.0, 8.0), 2.2)],
        remplir=((4.0, 9.0), 1.2),
        ep=0.7,
    ),
    # 2 : jumeaux — deux fûts géants tressés à la base puis écartés, deux couronnes à des hauteurs différentes
    dict(
        tiges=[([(-0.8, 0, 0.4), (1.0, 5.0, -0.6), (-0.4, 9.0, 0.5)], 4.8, 0, (10, 35)),
               ([(-0.6, 8.0, 0.4), (-3.4, 14.0, 1.4), (-6.2, 20.0, 0.2), (-8.4, 26.5, 1.0)], 3.4, 0, (45, 65, 85)),
               ([(0.4, 8.0, 0.0), (2.6, 15.0, -1.2), (4.6, 22.0, 0.4), (6.4, 29.0, -0.8), (7.6, 34.0, -1.0)], 3.6, 1,
                (-10, -32, -54, -70)),
               ([(1.8, 0, 1.8), (2.2, 6.0, -1.8), (4.4, 12.0, 1.2), (3.4, 18.0, -1.6)], 1.8, 2, (0, 25, 50))],
        pied=(0.0, 0.0),
        racines=[(30, 5.0, 2.8, 2.6), (110, 4.4, 2.4, 2.2), (190, 5.2, 2.8, 2.4), (270, 4.4, 2.2, 2.0),
                 (330, 4.6, 2.4, 2.2)],
        branches=[([(-7.0, 22.5, 0.6), (-13.0, 23.8, -1.0), (-17.5, 24.4, -2.0)], 1.8, 10),
                  ([(-6.6, 22.0, 0.4), (-7.0, 22.8, -6.0), (-6.4, 23.2, -10.0)], 1.6, -12),
                  ([(5.6, 29.5, -0.6), (11.0, 30.8, 1.0), (16.0, 31.4, 2.0)], 1.8, 18),
                  ([(5.4, 29.0, -0.2), (6.0, 30.0, 5.5), (6.4, 30.4, 9.5)], 1.6, -8)],
        masses=[(-9.0, 26.0, 1.0, 18, 16, 3.0, -12, 3),
                (8.0, 33.5625, -1.0, 17, 16, 3.0, 18, 3),
                (-17.5, 24.1875, -2.0, 11, 10, 2.5, 8, 2),
                (-6.4, 22.9375, -10.5, 10, 8, 2.5, -20, 2),
                (16.0, 31.3125, 2.0, 11, 10, 2.5, -10, 2),
                (6.4, 30.4375, 10.0, 10, 8, 2.5, 25, 2)],
        feuilles=[(0, 0.6, 0.4, 3.4, 2.8, 25, 2), (1, 0.5, -0.5, 3.2, 2.8, -20, 1),
                  (2, -0.4, -0.3, 3.0, 2.4, 15, 2), (5, 0.3, 0.5, 3.0, 2.4, 40, 1)],
        franges=[(2, 16, (6.0, 11.0), 2.2), (3, 14, (5.0, 10.0), 2.2),
                 (4, 16, (7.0, 13.0), 2.2), (5, 14, (6.0, 12.0), 2.2),
                 (0, 22, (5.0, 10.0), 2.2), (1, 22, (6.0, 12.0), 2.2)],
        remplir=((4.0, 9.0), 1.2),
        ep=0.7,
    ),
    # 3 : étagé — fût haut, large étage bas de quatre lobes et couronne haute plus étroite
    dict(
        tiges=[([(-0.8, 0, 0.6), (1.2, 7.0, -0.8), (-0.8, 14.0, 0.8), (0.8, 21.0, -0.4), (0.0, 28.0, 0.2),
                 (0.4, 32.5, 0.0)], 3.8, 0, (10, 30, 50, 70, 90)),
               ([(2.2, 0, -1.6), (-1.4, 6.0, 1.6), (1.6, 12.5, 1.2), (-0.8, 19.0, -1.4), (0.6, 25.0, 0.6)], 2.6, 1,
                (-12, 18, -26, 8)),
               ([(-2.4, 0, -1.8), (0.8, 5.0, -2.4), (2.2, 10.0, -0.4), (1.0, 15.5, 1.8)], 2.0, 2, (25, 50, 75))],
        pied=(0.0, 0.0),
        racines=[(20, 5.0, 2.8, 2.4), (100, 4.4, 2.4, 2.2), (180, 5.0, 2.6, 2.4), (260, 4.2, 2.2, 2.0),
                 (330, 4.6, 2.4, 2.2)],
        branches=_B3 + [([(0.0, 27.0, 0.0), (6.0, 30.0, 3.0)], 1.8, 15), ([(0.0, 27.5, 0.0), (-6.0, 30.2, -2.5)], 1.8, -15)],
        masses=[(0.0, 31.0, 0.0, 18, 16, 3.0, 12, 3)] + _M3 + [(0.0, 20.75, 0.0, 16, 16, 2.0, 45, 1)],
        feuilles=[(0, 0.6, -0.5, 3.4, 2.8, 25, 2), (2, -0.4, 0.5, 3.2, 2.6, -15, 1),
                  (3, 0.5, -0.4, 3.0, 2.4, 30, 2), (0, -0.5, 0.45, 3.0, 2.4, 0, 1)],
        franges=[(1, 18, (7.0, 13.0), 2.2), (2, 18, (7.0, 13.0), 2.2),
                 (3, 18, (7.0, 13.0), 2.2), (4, 18, (7.0, 13.0), 2.2),
                 (0, 22, (3.0, 7.0), 2.2)],
        remplir=((4.0, 9.0), 1.2),
        ep=0.7,
    ),
]


def glycine_geante(b, variant: int = 0, taille: float = 1.0, teinte: str = "mauve") -> dict:
    """Glycine géante millénaire (30 à 45 studs à taille 1) pour les repères et le fond de décor : fûts tressés de
    rayon 2 à 4, racines en contreforts, branches maîtresses, vaste ombrelle de lobes et rideaux de grappes de 6 à
    14 studs. 0 dôme, 1 penché vers l'avant (-Z), 2 jumeaux à deux couronnes, 3 étagé. ≤ 220 pièces."""
    T = _Arbre(b, taille, teinte, budget=220)
    with b.group("GlycineGeante"):
        _construire(T, GEANTES[variant % 4])
    _recentrer(b, T.n0)
    return _infos(b, T.n0)


# ---------------------------------------------------------------------------
# Arche de glycines au-dessus du couloir
# ---------------------------------------------------------------------------

COULOIR_X = 31.0  # |x| < 31 : couloir (30) + marge ; rien sous `hauteur` au-dessus


def arche_glycines(b, portee: float = 76, hauteur: float = 34, variant: int = 0) -> dict:
    """Arche de glycines qui enjambe le couloir de course (comme le tunnel de glycines) : deux troncs tordus enracinés
    en x = ±portee/2 (jamais à |x| < 32), branches maîtresses qui montent et s'entrelacent au-dessus du couloir,
    bandeau de fleurs bombé et deux rideaux de grappes face au coureur (avant -Z et arrière +Z, les deux sens de
    course), masses latérales d'où retombent de longs rideaux sur les trottoirs.
    Au-dessus de |x| < 31, rien ne descend sous `hauteur` (la caméra Roblox ne saute pas) ; le bois reste à
    |x| ≥ 32 sous `hauteur` (une portée inférieure à 76 est portée à 76).
    0 berceau symétrique, 1 asymétrique violet (un côté plus haut), 2 tunnel profond (bandeau plus large),
    3 sommet en pointe, glycines mauves et blanches mêlées. ≤ 220 pièces."""
    v = variant % 4
    rng = b.rng
    P = max(float(portee) / 2, 38.0)       # les troncs restent hors de |x| < 32 (portée minimale 76)
    H = float(hauteur)
    X0 = COULOIR_X
    D = (16.0, 16.0, 24.0, 18.0)[v]       # profondeur du bandeau (le long du couloir, axe Z)
    teinte = ("mauve", "violet", "mauve", "mauve")[v]
    T = _Arbre(b, 1.0, teinte, budget=220, interdit=(X0, H), melange=("blanc", 0.4) if v == 3 else None)
    T.dessous = 0.8                        # l'arche se voit d'en dessous : semelle moins sombre
    asym = (0.0, 3.5, 0.0, 0.0)[v]         # côté +x plus haut de `asym`
    pointe = (0.0, 0.0, 0.0, 3.5)[v]       # sommet relevé (arc brisé)

    def masse(cx, y0, cz, w, d, h, rot, det):
        # famille de hauteurs propre à chaque masse (aucune voisine ne la partage)
        T.masse(cx, math.floor(y0 * 2) / 2 + T.famille(cx, cz, w, d, rot), cz, w, d, h, rot, det)

    def y_plafond(x):
        """Dessous du bandeau : bombé, plus haut au milieu (pointe en v3), relevé côté +x en v1."""
        f = min(1.0, abs(x) / (P - 6))
        return H + 10.5 - 4.0 * f ** 2 + pointe * (1 - f) + (asym * f if x > 0 else 0.0)

    with b.group("ArcheGlycines"):
        with b.group("Bois"):
            for s in (-1, 1):
                dh = asym if s > 0 else 0.0
                z0 = float(rng.uniform(-0.6, 0.6))
                X = lambda dx: s * (P + dx)  # noqa: E731  (dx < 0 : vers le couloir)
                T.tige([(X(0.0), 0, z0 - 1.2), (X(-1.8), 12, z0 + 1.3), (X(-3.0), 24, z0 - 1.0),
                        (X(-3.6), H + 3.0 + dh, z0)], 3.6, T.ecorce(0), (10 * s, 38 * s, 66 * s))
                T.tige([(X(2.0), 0, z0 + 2.2), (X(-0.6), 9, z0 - 2.1), (X(-0.4), 19, z0 + 2.0),
                        (X(-3.0), H + dh, z0 + 0.6)], 2.6, T.ecorce(1), (-15 * s, 20 * s, -30 * s))
                T.tige([(X(0.9), 0, z0 - 3.4), (X(1.6), 13, z0 - 1.6)], 1.8, T.ecorce(2), (25 * s,))
                T.racines(X(0.4), z0, [(90 * s + a, lg, h, lw) for (a, lg, h, lw) in
                                       ((-10, 5.0, 3.0, 2.8), (75, 4.2, 2.4, 2.4))])
                # maîtresse : monte au-dessus de `hauteur`, passe le milieu et s'entrelace avec l'autre
                yb = H + dh
                T.tige([(X(-3.6), yb + 1.5, z0), (X(-12), y_plafond(s * (P - 12)) + 1.0, z0 - 0.8),
                        (X(-24), y_plafond(s * (P - 24)) + 1.4, 0.6), (-s * 3.0, y_plafond(0) + 1.8, -0.4 * s)],
                       2.6, T.ecorce(0), (12 * s, -14 * s, 20 * s), name="Branche")
                # branche secondaire vers l'avant ou l'arrière (une de chaque côté, en quinconce)
                zd = (D / 2 - 2.5) * s
                T.tige([(X(-3.4), yb + 2.0, z0), (X(-11), y_plafond(s * (P - 11)) + 0.8, zd)], 1.7, T.ecorce(1),
                       (20 * s,), name="Branche")
                # branche basse vers l'extérieur : porte le lobe extérieur
                T.tige([(X(-2.4), H - 13.0 + dh, z0), (X(4.0), H - 4.6 + dh, 1.25 * s)], 1.6, T.ecorce(2),
                       (-25 * s,), name="Branche")
        with b.group("Fleurs"):
            # bandeau au-dessus du couloir : un grand lobe central et deux lobes latéraux, dessus en nuage
            xl = P - 17.0
            masse(0.0, y_plafond(0), float(rng.uniform(-0.8, 0.8)), 22, D, 3.0, float(rng.uniform(-4, 4)), 3)
            for s in (-1, 1):
                masse(s * xl, y_plafond(s * xl), float(rng.uniform(-0.8, 0.8)), 20, D - 1, 3.0,
                      float(rng.uniform(-5, 5)), 2)
            # masses latérales, toutes hors couloir (|x| ≥ 31,5) : au-dessus des troncs, autour, et plus bas dehors
            for s in (-1, 1):
                dh = asym if s > 0 else 0.0
                masse(s * (P + 0.5), H + 1.0 + dh, 0.0, 8, D - 3, 3.0, 0, 1)
                wl = min(10.0, 2 * (P - 2 - X0 - 0.5))
                masse(s * (P - 2), H - 3.0 + dh, 0.0, wl, D, 3.0, 0, 2)
                masse(s * (P + 4.0), H - 6.0 + dh, 1.25 * s, 8, D - 3, 3.5, 0, 2)
            for (im, fx, fz, sx, sz, yaw, ton) in ((0, 0.45, -0.5, 3.4, 2.6, 20, 2), (2, 0.4, 0.5, 3.0, 2.4, 35, 1)):
                T.feuilles_sur(im, fx, fz, sx, sz, yaw, ton)
        with b.group("Grappes"):
            # d'abord quelques grappes sous le bandeau (vues en passant dessous), puis les rideaux
            T.remplir((3.5, 9.0), 1.2, quota=(30, 30, 45, 30)[v], bord=0.3, masses=(0, 1, 2))
            specs = []
            for im, (cx, _cz, _w, _d, _r, _y0, _y1) in enumerate(T.masses):
                if abs(cx) >= X0 + 2:      # côtés : longs rideaux sur les trottoirs, tout autour
                    specs.append((im, 16, (8.0, 15.0), 2.2, None, None, 2))
                else:                      # bandeau : rideaux avant et arrière, bornés par la zone interdite
                    specs.append((im, 22, (4.5, 11.0), 2.6, None, "z", 2))
            _franges(T, specs, ep=0.6)
            T.remplir((3.0, 9.0), 1.1)
    return _infos(b, T.n0)


# ---------------------------------------------------------------------------
# Treille (fujidana)
# ---------------------------------------------------------------------------

def treille(b, longueur: float = 20, largeur: float = 8, hauteur: float = 9, variant: int = 0) -> dict:
    """Treille de glycines (fujidana) le long de l'axe X local : poteaux sur dés de pierre, sablières, traverses et
    treillis de lattes, deux glycines tordues qui grimpent aux poteaux, nappe de fleurs sur le treillis et grappes
    qui pendent au travers jusqu'à environ hauteur - 4 (on passe dessous). Avant = -Z.
    0 bois sombre et glycines mauves, 1 bois brun et glycines violettes, 2 bois clair et glycines blanches,
    3 poteaux vermillon (treille de sanctuaire). ≤ 130 pièces."""
    v = variant % 4
    rng = b.rng
    L, W, H = float(longueur), float(largeur), float(hauteur)
    teinte = ("mauve", "violet", "blanc", "mauve")[v]
    bois = (c("bois_fonce"), c("bois"), c("bois_clair"), c("vermillon"))[v]
    bois2 = (c("bois"), c("bois_fonce"), c("bois_moyen"), c("noir_laque"))[v]  # sablières et traverses
    T = _Arbre(b, 1.0, teinte, budget=130)
    nx = max(2, int(round(L / 6.5)) + 1)
    xs = [float(x) for x in np.linspace(-L / 2 + 0.6, L / 2 - 0.6, nx)]
    zs = (-W / 2 + 0.6, W / 2 - 0.6)
    with b.group("Treille"):
        with b.group("Bois"):
            for x in xs:
                for z in zs:
                    b.box((x - 0.5, 0, z - 0.5), (x + 0.5, H - 1.3, z + 0.5), vary(bois, rng, 0.03), name="Poteau")
                    b.box((x - 0.8, 0, z - 0.8), (x + 0.8, 0.45, z + 0.8), vary(c("pierre_fonce"), rng, 0.04),
                          studs="top", name="Socle")
                # traverse (le long de Z), posée sur les sablières, débordante
                b.box((x - 0.4, H - 1.0, -W / 2 - 0.5), (x + 0.4, H - 0.4, W / 2 + 0.5), vary(bois2, rng, 0.03),
                      name="Traverse")
                T.bois.append((np.array([x, H - 0.7, -W / 2 - 0.5]), np.array([x, H - 0.7, W / 2 + 0.5]), 0.45))
            for z in zs:  # sablières (le long de X)
                b.box((-L / 2 - 0.8, H - 2.0, z - 0.6), (L / 2 + 0.8, H - 1.0, z + 0.6), vary(bois2, rng, 0.03),
                      name="Sabliere")
                T.bois.append((np.array([-L / 2 - 0.8, H - 1.5, z]), np.array([L / 2 + 0.8, H - 1.5, z]), 0.65))
            # treillis : lattes le long de X sur les traverses, puis lattes le long de Z par-dessus
            nzl = max(3, int(round(W / 2.0)))
            for z in np.linspace(-W / 2 + 1.0, W / 2 - 1.0, nzl):
                b.box((-L / 2 - 0.5, H - 0.4, z - 0.2), (L / 2 + 0.5, H - 0.1, z + 0.2), vary(bois, rng, 0.03),
                      name="Latte", collide=False)
            nxl = max(2, int(round(L / 3.2)))
            for x in np.linspace(-L / 2 + 1.4, L / 2 - 1.4, nxl):
                b.box((x - 0.2, H - 0.1, -W / 2 - 0.6), (x + 0.2, H + 0.2, W / 2 + 0.6), vary(bois, rng, 0.03),
                      name="Latte", collide=False)
            # deux glycines tordues grimpent à des poteaux opposés puis courent sur le treillis
            for (xp, zp, sx, sz) in ((xs[0], zs[0], 1, -1), (xs[-1] if nx > 2 else xs[-1], zs[1], -1, 1)):
                T.tige([(xp + 0.9 * sx, 0, zp + 0.8 * sz), (xp - 0.6 * sx, 3.0, zp + 1.0 * sz),
                        (xp + 0.8 * sx, 6.0, zp - 0.4 * sz), (xp + 0.2 * sx, H - 0.6, zp + 0.5 * sz),
                        (xp + 4.0 * sx, H + 0.6, zp * 0.4)], 0.8, T.ecorce(1), (20, 45, 70, 95))
        with b.group("Fleurs"):
            # nappe de fleurs : deux rangées de plaques un peu tournées (avant / arrière) qui débordent des sablières,
            # avec parfois un trou où l'on voit le treillis
            npx = max(1, int(round(L / 5.5)))
            pas = L / npx
            for i in range(npx):
                for j, sz in enumerate((-1, 1)):
                    if 0 < i < npx - 1 and rng.uniform() < 0.12:
                        continue
                    cx = -L / 2 + pas * (i + 0.5) + float(rng.uniform(-0.5, 0.5))
                    w = round(pas * float(rng.uniform(0.92, 1.08)) * 2) / 2
                    d = round((W / 2 + 1.6 + float(rng.uniform(0.0, 0.6))) * 2) / 2
                    zc = sz * (d / 2 - 0.2)
                    rot = float(rng.uniform(-6, 6))
                    y0 = H + 0.2 - T.famille(cx, zc, w, d, rot) / 2 - 0.05
                    T.masse(cx, y0, zc, w, d, 1.0 + 0.5 * ((i + j) % 2), rot, 0)
            # quelques bouffées plus claires sur la nappe
            _nuit, _fonce, mauve, claire, _pale = T.g
            choix = rng.permutation(len(T.masses))[:max(2, npx)]
            for k, im in enumerate(choix):
                cx, cz, w, d, rot, _y0, y1 = T.masses[int(im)]
                dx, dz = _monde(float(rng.uniform(-0.2, 0.2)) * w, float(rng.uniform(-0.15, 0.15)) * d, rot)
                T.bloc(cx + dx, y1 - 0.15625, cz + dz, round(w * 0.4 * 2) / 2, (0.875, 0.75)[k % 2],
                       round(d * 0.4 * 2) / 2, T.V(mix(mauve, claire, 0.4 + 0.3 * (k % 2))), rot + 30 + 15 * k,
                       plafond=False)
        with b.group("Grappes"):
            # rideaux devant et derrière (hors des sablières), pointes vers H - 4, puis grappes entre les sablières
            specs = [(im, 14, (3.4, 5.4), 1.1) for im in range(len(T.masses))]
            _franges(T, specs, ep=0.45)
            T.remplir((3.0, 5.0), 0.95)
    return _infos(b, T.n0)


# ---------------------------------------------------------------------------
# Bambous
# ---------------------------------------------------------------------------

def bambous(b, variant: int = 0, n: int = 7) -> dict:
    """Bosquet de bambous : n tiges fines de 18 à 30 studs, segmentées par des nœuds, légèrement écartées en
    éventail, bouquets de feuilles en haut. 0 touffe ronde, 1 rangée le long de X (haie de fond), 2 éventail (tiges
    très penchées), 3 touffe avec vieilles tiges sombres et jeunes pousses. ≤ 50 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    n = int(max(1, min(int(n), 16)))
    sol = 2 if v == 3 else 1
    par = max(2, (50 - sol) // n)                 # pièces par tige
    feuilles = min(3, max(1, par - 1 - 2))        # bouquets de feuilles par tige
    noeuds = max(0, min(4, par - 1 - feuilles))
    with b.group("Bambous"):
        # positions : spirale de tournesol (touffe), ligne, ou touffe lâche
        pos = []
        for i in range(n):
            if v == 1:
                x = (i - (n - 1) / 2) * 1.9 + float(rng.uniform(-0.3, 0.3))
                z = float(rng.uniform(-0.9, 0.9))
            else:
                r = (1.05 if v != 2 else 1.25) * math.sqrt(i + 0.5)
                a = i * 2.39996 + float(rng.uniform(-0.2, 0.2))
                x, z = r * math.cos(a), r * math.sin(a)
            pos.append((x, z))
        cx = sum(q[0] for q in pos) / n
        cz = sum(q[1] for q in pos) / n
        touffes = []
        for i, (x, z) in enumerate(pos):
            dx, dz = x - cx, z - cz
            dist = math.hypot(dx, dz)
            centre = 1.0 - min(1.0, dist / 4.0)
            h = 18.0 + 10.0 * centre + float(rng.uniform(-1.5, 2.0))
            h = min(30.0, max(18.0, h)) if v != 3 or i % 3 else 18.0 + float(rng.uniform(0, 2))  # vieilles tiges
            dia = 0.7 + 0.3 * (h - 18.0) / 12.0
            inc = {0: (1.5, 4.0), 1: (0.5, 2.5), 2: (5.0, 11.0), 3: (1.5, 5.0)}[v]
            tilt = math.radians(float(rng.uniform(*inc)))
            if dist > 1e-6:
                ux, uz = dx / dist, dz / dist
            else:
                a = float(rng.uniform(0, 2 * math.pi))
                ux, uz = math.cos(a), math.sin(a)
            if v == 1:
                ux, uz = 0.3 * ux, 1.0 if z < 0 else -1.0  # la rangée s'ouvre un peu vers l'avant et l'arrière
                nn = math.hypot(ux, uz)
                ux, uz = ux / nn, uz / nn
            u = np.array([math.sin(tilt) * ux, math.cos(tilt), math.sin(tilt) * uz])
            p0 = np.array([x, 0.0, z])
            vieux = v == 3 and i % 3 == 0
            col = vary(c("bambou_fonce") if (i % 2 or vieux) else c("bambou"), rng, 0.04)
            if vieux:
                col = mix(col, c("terre"), 0.35)
            tw = float(rng.uniform(0, 90))
            # le pied est un peu enfoncé : aucun coin ne flotte
            e0 = (dia * 0.72 * math.sin(tilt) + 0.05) / max(math.cos(tilt), 0.3)
            _poutre(b, p0, p0 + u * h, dia, dia, col, tw, e0, 0.0, name="Bambou")
            # nœuds : anneaux un peu plus larges et plus sombres
            for k in range(noeuds):
                f = 0.14 + 0.6 * ((k + 0.5) / noeuds) ** 1.1
                q = p0 + u * h * f
                _poutre(b, q - u * 0.15, q + u * 0.15, dia + 0.24, dia + 0.24, shade(col, 0.78), tw, 0, 0,
                        name="Noeud", collide=False)
            # bouquets de feuilles étagés au sommet, chacun déporté d'un côté (éventail), studs dessus
            a0 = float(rng.uniform(0, 360))
            for k in range(feuilles):
                q = p0 + u * (h - 0.4 - 1.8 * k)
                a = math.radians(a0 + 125 * k)
                lg = (3.6, 3.0, 2.5)[k] + float(rng.uniform(-0.3, 0.3))
                ox, oz = math.cos(a) * lg * 0.32, math.sin(a) * lg * 0.32
                col_f = vary((FEUILLES[2], c("bambou"), FEUILLES[1])[(i + k) % 3], rng, 0.05)
                y0 = float(q[1]) - 0.3
                # pas deux bouquets qui se recouvrent avec des faces presque au même niveau
                while any(math.hypot(q[0] + ox - tx, q[2] + oz - tz) < (lg + tl) * 0.5 and abs(y0 - ty) < 0.12
                          for (tx, tz, tl, ty) in touffes):
                    y0 += 0.15
                touffes.append((q[0] + ox, q[2] + oz, lg, y0))
                b.boxc((q[0] + ox, y0 + 0.3, q[2] + oz), (lg, 0.6, lg * 0.55), col_f,
                       yaw=-math.degrees(a) + float(rng.uniform(-15, 15)), studs="top", collide=False, name="Feuilles")
        # sol : litière de feuilles sèches, pousses de bambou (takenoko)
        rx = max(abs(q[0] - cx) for q in pos) + 1.6
        rz = max(abs(q[1] - cz) for q in pos) + 1.6
        litiere = mix(c("terre"), c("bambou_fonce"), 0.35)
        b.boxc((cx, 0.15, cz), (round(rx * 2 * 2) / 2, 0.3, round(rz * 2 * 2) / 2), vary(litiere, rng, 0.04),
               yaw=float(rng.uniform(-10, 10)), studs="top", collide=False, name="Litiere")
        if v == 3:
            px, pz = cx + rx * 0.6, cz - rz * 0.5
            b.wedge((px - 0.5, 0.3, pz - 0.6), (px + 0.5, 1.9, pz + 0.6), vary(mix(litiere, c("bambou"), 0.3), rng, 0.04),
                    down="-z", collide=False, name="Pousse")
    _recentrer(b, n0)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Pin taillé en nuages (niwaki)
# ---------------------------------------------------------------------------

PINS = [
    # 0 : droit — tronc en S, cinq plateaux étagés en alternance et un plateau sommital
    dict(tronc=[(0.0, 0, 0.0), (0.8, 4.0, 0.3), (-0.6, 8.0, -0.2), (0.4, 12.0, 0.3), (0.0, 14.5, 0.0)], w=1.6,
         plateaux=[((-0.4, 5.5, 0.0), (-5.0, 6.5, -0.5), 7, 5.5, 1.5, 15), ((0.6, 8.5, 0.0), (5.0, 9.0, 0.5), 6.5, 5, 1.5, -20),
                   ((-0.3, 10.8, 0.0), (-3.6, 11.5, 1.0), 5.5, 4.5, 1.5, 30),
                   ((0.3, 12.6, 0.0), (3.2, 13.0, -0.6), 5, 4, 1.5, -10),
                   (None, (0.0, 14.4, 0.0), 5.5, 5.5, 2.0, 45)]),
    # 1 : penché (nagare) — tronc qui s'incline fortement d'un côté, plateaux en escalier vers le bas
    dict(tronc=[(0.0, 0, 0.0), (1.4, 4.0, 0.2), (3.6, 7.5, -0.3), (6.4, 9.6, 0.2), (8.8, 10.2, 0.0)], w=1.6,
         plateaux=[((1.6, 4.6, 0.1), (-1.6, 7.0, 0.6), 5.5, 4.5, 1.5, 20), ((4.0, 7.8, -0.2), (4.2, 11.2, -1.2), 6, 5, 1.5, -15),
                   ((6.6, 9.6, 0.1), (8.0, 10.0, 2.2), 5.5, 5, 1.5, 10), (None, (9.6, 10.6, -0.2), 6, 5, 1.5, 35),
                   ((2.6, 6.2, 0.0), (1.8, 9.6, 2.4), 4.5, 4, 1.5, -30)]),
    # 2 : large (monkaburi) — tronc court et coudé, une longue branche basse horizontale, couronne plate
    dict(tronc=[(0.0, 0, 0.0), (0.6, 3.5, 0.2), (-0.3, 7.0, -0.2), (0.2, 10.5, 0.1)], w=1.8,
         plateaux=[((0.2, 4.0, 0.0), (-7.5, 4.8, 0.4), 7.5, 5, 1.5, 10), ((-3.5, 4.4, 0.2), (-3.4, 6.0, -2.4), 4, 3.5, 1.0, -20),
                   ((0.4, 7.0, 0.0), (5.5, 7.6, -0.4), 6.5, 5, 1.5, -15), (None, (0.0, 10.4, 0.0), 8.5, 7, 2.0, 25),
                   ((-0.2, 8.8, 0.0), (-4.5, 9.4, 1.6), 5, 4, 1.5, 40)]),
    # 3 : élancé — tronc haut et fin, trois étages de plateaux de plus en plus petits
    dict(tronc=[(0.0, 0, 0.0), (0.5, 6.0, 0.3), (-0.4, 12.0, -0.2), (0.2, 17.5, 0.2)], w=1.4,
         plateaux=[((0.3, 7.0, 0.1), (-4.0, 8.0, 0.4), 6, 5, 1.5, 15), ((0.2, 7.5, 0.0), (4.0, 8.4, -0.6), 5.5, 4.5, 1.5, -25),
                   ((-0.3, 12.5, 0.0), (-3.0, 13.2, 0.6), 4.5, 4, 1.5, 30),
                   ((-0.1, 13.0, 0.0), (3.0, 13.6, -0.4), 4.5, 3.5, 1.5, -10),
                   (None, (0.2, 17.5, 0.2), 4.5, 4.5, 2.0, 45)]),
]


def pin(b, variant: int = 0) -> dict:
    """Pin japonais taillé en nuages (niwaki) : tronc brun-roux en S, branches qui portent des plateaux d'aiguilles
    vert bleuté sombre, dessus plus clair et studdé. 0 droit, 1 penché (nagare), 2 large à branche basse,
    3 élancé. ≤ 40 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    S = PINS[v]
    T = _Arbre(b, 1.0, "mauve", budget=40)
    ecorce = vary(ECORCE_PIN, rng, 0.04)
    aig = c("pin")
    with b.group("Pin"):
        T.tige(S["tronc"], S["w"], ecorce, (10, 35, 60, 85), name="Tronc")
        x0, _y, z0 = S["tronc"][0]
        T.racines(x0, z0, [(30, 2.0, 1.2, 1.2), (160, 1.8, 1.0, 1.1), (270, 2.0, 1.1, 1.2)], shade(ECORCE_PIN, 0.85))
        for k, (dep, (cx, y0, cz), w, d, h, rot) in enumerate(S["plateaux"]):
            if dep is not None:  # branche du tronc au plateau (noyée dedans)
                T.tige([dep, (cx, y0 + h * 0.4, cz)], 0.6, ecorce, (20 * k,), name="Branche", collide=False)
            y0f = y0 + (k % 4) * 0.125  # chaque plateau a sa propre famille de hauteurs
            b.boxc((cx, y0f + h / 2, cz), (w, h, d), vary(aig, rng, 0.04), yaw=rot, studs="top", collide=False,
                   name="Aiguilles")
            b.boxc((cx + 0.2, y0f + h + 0.25, cz - 0.1), (max(1.0, w - 2.2), 0.5, max(1.0, d - 2.0)),
                   vary(mix(aig, c("feuille_claire"), 0.45), rng, 0.04), yaw=rot + 12, studs="top", collide=False,
                   name="Aiguilles")
            b.boxc((cx - 0.1, y0f - 0.25, cz + 0.1), (max(1.0, w - 1.6), 0.5, max(1.0, d - 1.4)),
                   vary(shade(aig, 0.78), rng, 0.04), yaw=rot - 8, studs="none", collide=False, name="Aiguilles")
    _recentrer(b, n0)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Petits éléments : buissons, rochers moussus, souches, herbes
# ---------------------------------------------------------------------------

MOUSSE = c("mousse")
CHAMPIGNON = mix(c("lampion_papier"), c("terre"), 0.15)
CHAMPIGNON_ROUGE = c("rouge")


def _brin(b, x, z, h, w, col, ax=0.0, az=0.0, tw=0.0, name="Brin", d=None):
    """Brin ou feuille fine qui part du sol (pied un peu enfoncé), incliné de (ax, az) par stud de hauteur."""
    p0 = np.array([x, 0.0, z])
    p1 = np.array([x + ax * h, h, z + az * h])
    u = (p1 - p0) / np.linalg.norm(p1 - p0)
    e0 = (max(w, d or w) * 0.72 * math.sqrt(max(0.0, 1 - u[1] ** 2)) + 0.03) / max(u[1], 0.3)
    return _poutre(b, p0, p1, w, d or w, col, tw, e0, 0.0, collide=False, shadow=False, name=name)


def buisson(b, variant: int = 0) -> dict:
    """Petit buisson (2 à 4 studs) : 0 boule verte, 1 azalée lilas en fleurs, 2 hortensia bleu-violet,
    3 fougère (frondes en étoile). ≤ 12 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    F = lambda i, a=0.04: vary(FEUILLES[i], rng, a)  # noqa: E731

    def bloc(cx, y0, cz, sx, sy, sz, col, yaw=0.0, **kw):
        kw.setdefault("studs", "top")
        kw.setdefault("collide", False)
        kw.setdefault("name", "Feuillage")
        return b.boxc((cx, y0 + sy / 2, cz), (sx, sy, sz), col, yaw=yaw, **kw)

    with b.group("Buisson"):
        if v == 0:  # boule : blocs droit et à 45°, dessus clair, deux bosses sur les côtés
            bloc(0, 0, 0, 4, 2, 3.5, F(1))
            bloc(0.25, 0, -0.25, 3.5, 2.5, 3.5, vary(mix(FEUILLES[1], FEUILLES[2], 0.3), rng, 0.04), 45)
            bloc(-0.25, 2.5, 0.25, 2.5, 0.75, 2, F(2))
            bloc(2.25, 0, 1, 2, 1.5, 2, F(0), 30)
            bloc(-2.25, 0, -0.75, 1.5, 1.0, 1.5, F(0), -20)
            bloc(0, 3.25, 0, 1, 0.5, 1, vary(c("herbe_claire"), rng, 0.04), 45)
        elif v == 1:  # azalée lilas : dôme taillé piqué de fleurs
            bloc(0, 0, 0, 5, 2, 3, F(0))
            bloc(0, 0, 0, 3.5, 2.5, 3.5, vary(mix(FEUILLES[0], FEUILLES[1], 0.5), rng, 0.04), 45)
            fl = (c("glycine_claire"), c("glycine"), c("glycine_pale"), mix(c("glycine_claire"), c("rouge"), 0.2))
            for i, (x, y, z) in enumerate(((-1.2, 2.0, -0.3), (0.6, 2.25, 0.5), (1.7, 1.75, -0.6), (-0.2, 2.2, -0.9),
                                           (-2.3, 1.3, 0.4), (1.0, 1.0, -1.4), (-0.9, 1.5, 1.3))):
                b.box((x - 0.4, y - 0.4, z - 0.4), (x + 0.4, y + 0.45, z + 0.4), vary(fl[i % 4], rng, 0.04), studs="top",
                      collide=False, name="Fleur")
        elif v == 2:  # hortensia : feuillage sombre et grosses têtes bleu-violet
            bloc(0, 0, 0, 4, 2.5, 3, F(0))
            bloc(0.5, 0, 1, 3, 2, 3, F(1), 45)
            cols = (mix(c("eau"), c("glycine"), 0.5), c("glycine"), mix(c("eau"), c("glycine_claire"), 0.4),
                    c("glycine_fonce"), mix(c("glycine_claire"), c("blanc"), 0.3))
            for i, (x, y, z) in enumerate(((-1.1, 2.5, -0.7), (1.1, 2.5, 0.2), (-0.4, 2.0, -1.5), (1.6, 2.0, 1.6),
                                           (-1.6, 1.8, 0.9))):
                b.box((x - 0.7, y - 0.5, z - 0.7), (x + 0.7, y + 0.65, z + 0.7), vary(cols[i], rng, 0.04), studs="top",
                      collide=False, name="Fleur")
        else:  # fougère : frondes fines qui s'ouvrent en étoile
            for k in range(8):
                a = math.radians(k * 45 + float(rng.uniform(-12, 12)))
                h = 2.0 + 0.8 * (k % 3) + float(rng.uniform(-0.2, 0.3))
                ouv = 0.75 + 0.15 * (k % 2)
                _brin(b, 0.15 * math.cos(a), 0.15 * math.sin(a), h, 0.55, F(k % 3), ouv * math.cos(a), ouv * math.sin(a),
                      tw=math.degrees(a), name="Feuille", d=0.18)
            bloc(0, 0, 0, 1.2, 0.6, 1.2, F(0), 20)
    return _infos(b, n0)


def rocher_deco(b, variant: int = 0) -> dict:
    """Rochers gris-bleu moussus (comme ceux du sanctuaire en forêt) : 0 amas de blocs arrondis, 1 pierre dressée
    entourée de petites pierres, 2 pas japonais (pierres plates), 3 gros rocher couvert de mousse avec une touffe de
    fougère. Studs sur les dessus, mousse en plaques. ≤ 12 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    g0, g1, g2, g3 = GRIS

    def R(cx, cy, cz, sx, sy, sz, col, yaw, **kw):
        kw.setdefault("studs", "top")
        kw.setdefault("name", "Rocher")
        return b.boxc((cx, cy, cz), (sx, sy, sz), vary(col, rng, 0.03), yaw=yaw, **kw)

    def M(cx, y0, cz, sx, sz, yaw):
        return R(cx, y0 + 0.15, cz, sx, 0.3, sz, MOUSSE, yaw, collide=False, name="Mousse")

    with b.group("Rochers"):
        if v == 0:
            R(0, 1.5, 0, 5, 3, 4, g0, 12)
            R(0.25, 1.75, -0.25, 4, 3.5, 4.5, g1, 57)
            R(-0.3, 3.75, 0.2, 3, 1.0, 2.5, g2, 20)
            M(-0.6, 4.25, 0.4, 2.0, 1.6, 20)
            R(3.4, 0.75, 1.6, 2.4, 1.5, 2.0, g1, -20)
            M(3.3, 1.5, 1.6, 1.4, 1.2, -20)
            R(-3.1, 0.55, 1.9, 1.8, 1.1, 1.6, g2, 35)
            R(1.6, 0.35, -2.9, 1.2, 0.7, 1.0, g0, 8)
        elif v == 1:
            R(0, 2.75, 0, 2.2, 5.5, 1.8, g0, 10)
            R(0.1, 5.75, 0.05, 1.5, 0.5, 1.3, g2, 25)
            R(0.2, 2.5, -0.3, 1.6, 5.0, 2.2, g1, 55)
            R(1.9, 0.6, 1.0, 2.0, 1.2, 1.8, g1, -25)
            R(-1.8, 0.45, -0.9, 1.6, 0.9, 1.4, g2, 40)
            M(-0.1, 1.2, 1.25, 1.4, 0.9, 10)
            M(1.9, 1.2, 1.0, 1.2, 1.0, -25)
        elif v == 2:
            for i, (x, z, sx, sz, h, yaw) in enumerate(((0, 0, 2.6, 2.0, 0.6, 8), (2.4, 1.4, 1.8, 1.5, 0.5, -25),
                                                         (-2.2, 1.0, 1.8, 1.6, 0.55, 40), (0.7, -2.2, 1.5, 1.3, 0.45, 15),
                                                         (-1.3, -2.1, 1.1, 1.0, 0.4, -10))):
                R(x, h / 2, z, sx, h, sz, (g2, g3, g1, g2, g3)[i], yaw)
            M(-0.3, 0.6, 0.1, 1.0, 0.8, 8)
        else:
            R(0, 2.0, 0, 6, 4, 5, g0, 15)
            R(0.3, 2.25, 0.2, 5, 4.5, 5.5, g1, 60)
            R(-0.2, 4.75, -0.2, 3.5, 1.0, 3.0, g2, 30)
            M(-0.4, 5.25, -0.1, 2.6, 2.0, 30)
            M(1.6, 4.0, 1.8, 2.2, 1.8, 60)
            M(-2.3, 4.0, -1.0, 1.8, 2.2, 15)
            R(3.6, 0.6, -1.6, 1.8, 1.2, 1.6, g2, -15)
            for k in range(3):  # touffe de fougère au pied
                a = math.radians(200 + k * 50)
                _brin(b, -3.3, 1.6, 1.8 + 0.3 * k, 0.5, vary(FEUILLES[k % 3], rng, 0.04), 0.7 * math.cos(a),
                      0.7 * math.sin(a), tw=math.degrees(a), name="Feuille", d=0.18)
    return _infos(b, n0)


def souche(b, variant: int = 0) -> dict:
    """Souche (comme celle du sanctuaire en forêt) : 0 souche coupée net (cernes clairs, racines, mousse),
    1 souche cassée en pointes, 2 tronc couché, 3 souche moussue aux champignons. ≤ 12 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    e = vary(TRONC_CLAIR, rng, 0.04)
    e2 = vary(mix(TRONC, TRONC_CLAIR, 0.5), rng, 0.04)
    coeur = vary(c("bois_clair"), rng, 0.04)
    rac = shade(TRONC_CLAIR, 0.85)

    def racines(specs):
        for (ang, lg, h, lw) in specs:
            with b.at((0, 0, 0), yaw=ang):
                b.wedge((-lw / 2, 0, 0.6), (lw / 2, h, 0.6 + lg), vary(rac, rng, 0.04), down="+z", name="Racine")

    with b.group("Souche"):
        if v in (0, 3):
            hs = 2.2 if v == 0 else 1.8
            b.boxc((0, hs / 2, 0), (3, hs, 3), e)
            b.boxc((0, (hs - 0.25) / 2, 0), (3.1, hs - 0.25, 3.1), e2, yaw=45)
            b.boxc((0, hs + 0.05, 0), (2.2, 0.1, 2.2), coeur, studs="top", name="Coeur")
            racines(((20, 1.6, 1.2, 1.2), (140, 1.4, 1.0, 1.1), (260, 1.8, 1.3, 1.2)))
            if v == 0:
                b.boxc((0.9, hs + 0.15, -0.6), (1.2, 0.2, 1.0), MOUSSE, yaw=20, collide=False, studs="top", name="Mousse")
            else:  # mousse épaisse et champignons sur le flanc
                b.boxc((0.2, hs + 0.2, 0.3), (2.0, 0.3, 1.8), MOUSSE, yaw=10, collide=False, studs="top", name="Mousse")
                for k, (x, y, z, col) in enumerate(((1.75, 0.9, 0.3, CHAMPIGNON), (1.7, 1.4, -0.5, CHAMPIGNON),
                                                    (-0.6, 0.25, -2.0, CHAMPIGNON_ROUGE))):
                    b.boxc((x, y, z), (0.9 if k < 2 else 0.8, 0.25, 0.9 if k < 2 else 0.8), col, yaw=15 * k,
                           collide=False, studs="top", name="Champignon")
                b.boxc((-0.6, 0.1, -2.0), (0.25, 0.2, 0.25), c("blanc"), collide=False, name="Champignon")
        elif v == 1:  # cassée : fût plus haut, sommet en pointes de hauteurs différentes
            b.boxc((0, 1.6, 0), (2.6, 3.2, 2.6), e)
            b.boxc((0, 1.45, 0), (2.7, 2.9, 2.7), e2, yaw=45)
            for (x, z, sx, sz, h) in ((-0.6, -0.5, 1.0, 1.1, 1.8), (0.7, 0.3, 0.9, 1.0, 1.1), (-0.2, 0.8, 0.8, 0.7, 0.7)):
                b.box((x - sx / 2, 3.2, z - sz / 2), (x + sx / 2, 3.2 + h, z + sz / 2), e, name="Echarde")
            racines(((40, 1.6, 1.2, 1.1), (170, 1.5, 1.0, 1.0), (290, 1.7, 1.2, 1.1)))
        else:  # tronc couché le long de X, souche de branche, mousse dessus
            b.box((-3.5, 0, -0.9), (3.5, 1.8, 0.9), e, name="Tronc")
            with b.at((0, 0.9, 0)):
                _poutre(b, (-3.45, 0, 0), (3.45, 0, 0), 2.1, 2.1, e2, 45, 0, 0, name="Tronc")
            b.box((3.5, 0.2, -0.7), (3.6, 1.6, 0.7), coeur, name="Coeur")
            b.box((-3.6, 0.2, -0.7), (-3.5, 1.6, 0.7), coeur, name="Coeur")
            _poutre(b, (0.8, 1.6, 0.2), (1.6, 2.8, -0.6), 0.6, 0.6, e, 20, 0.2, 0, name="Branche")
            b.boxc((-1.0, 2.0, 0.1), (2.6, 0.3, 1.4), MOUSSE, yaw=8, collide=False, studs="top", name="Mousse")
    return _infos(b, n0)


def herbes(b, variant: int = 0) -> dict:
    """Touffes d'herbe : 0 touffe courte, 1 hautes herbes à plumets (susuki), 2 bambou nain (sasa),
    3 herbes et petites fleurs mauves. ≤ 12 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    cols = (c("herbe_fonce"), c("herbe"), c("herbe_claire"), c("feuille"))
    with b.group("Herbes"):
        if v == 0:
            for k in range(6):
                a = math.radians(k * 60 + float(rng.uniform(-15, 15)))
                _brin(b, 0.2 * math.cos(a), 0.2 * math.sin(a), 0.9 + 0.35 * (k % 3), 0.3, vary(cols[k % 4], rng, 0.05),
                      0.35 * math.cos(a), 0.35 * math.sin(a), tw=k * 30)
        elif v == 1:
            for k in range(5):
                a = math.radians(k * 72 + float(rng.uniform(-15, 15)))
                h = 3.0 + 0.6 * (k % 3)
                _brin(b, 0.2 * math.cos(a), 0.2 * math.sin(a), h, 0.25, vary(cols[k % 4], rng, 0.05), 0.18 * math.cos(a),
                      0.18 * math.sin(a), tw=k * 20)
                if k < 3:  # plumet clair au bout de la tige
                    tip = np.array([0.2 * math.cos(a) + 0.18 * math.cos(a) * h, h, 0.2 * math.sin(a) + 0.18 * math.sin(a) * h])
                    b.boxc(tuple(tip + np.array([0, -0.45, 0])), (0.45, 1.2, 0.45), vary(c("lampion_papier"), rng, 0.04),
                           yaw=k * 25, collide=False, shadow=False, name="Plumet")
        elif v == 2:
            for k in range(7):
                a = math.radians(k * 51 + float(rng.uniform(-10, 10)))
                _brin(b, 0.15 * math.cos(a), 0.15 * math.sin(a), 1.4 + 0.3 * (k % 3), 0.6, vary(FEUILLES[k % 3], rng, 0.05),
                      0.8 * math.cos(a), 0.8 * math.sin(a), tw=math.degrees(a), name="Feuille", d=0.14)
        else:
            for k in range(5):
                a = math.radians(k * 72 + float(rng.uniform(-15, 15)))
                _brin(b, 0.2 * math.cos(a), 0.2 * math.sin(a), 1.0 + 0.4 * (k % 3), 0.3, vary(cols[k % 4], rng, 0.05),
                      0.3 * math.cos(a), 0.3 * math.sin(a), tw=k * 30)
            for k, (x, z) in enumerate(((0.9, 0.5), (-0.7, 0.9), (0.2, -1.0))):
                h = 1.3 + 0.25 * k
                _brin(b, x, z, h, 0.14, vary(cols[0], rng, 0.05), name="Tige")
                b.boxc((x, h + 0.2, z), (0.55, 0.4, 0.55), vary((c("glycine"), c("glycine_claire"), c("glycine_pale"))[k],
                       rng, 0.04), yaw=20 * k, collide=False, shadow=False, studs="top", name="Fleur")
    return _infos(b, n0)
