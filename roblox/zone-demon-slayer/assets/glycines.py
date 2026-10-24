"""Glycines et végétation de la zone 3 en style stud : glycines tordues aux longues grappes, glycines géantes,
treille fujidana, arche de glycines au-dessus du couloir, bambous, pin taillé en nuages, buissons, rochers moussus,
souches et touffes d'herbe.

Principes :
- les grappes sont l'âme de la zone : bandes verticales de blocs empilés qui s'affinent et pâlissent vers la pointe
  (glycine_fonce / glycine en haut → glycine_claire → glycine_pale à la pointe), de longueurs variées, un peu tournées
  et décalées ; leurs longueurs ondulent autour de chaque masse (ourlet festonné) : de loin, on lit des glycines ;
- chaque grappe est accrochée : son sommet est noyé dans le bloc de fleurs le plus bas qui la couvre entièrement,
  aucun autre bloc n'est traversé (registre des « plafonds »), aucune grappe ne traverse le bois (registre des
  « obstacles ») ni une autre grappe ; rien ne flotte ;
- bois tordu : tiges en poutres inclinées et vrillées (rotation autour de leur axe), deux ou trois tiges tressées,
  racines en coins ; le bois collisionne ; fleurs, feuilles et grappes ont `collide=False` ;
- studs sur les dessus des masses de fleurs et de feuilles uniquement (pas sur les grappes) ;
- les masses ont chacune leur « famille » de hauteurs (partie fractionnaire de y0 modulo 0,5 distincte, les cotes
  internes étant des multiples du demi-stud) : jamais deux faces horizontales de masses différentes au même niveau ;
- chaque fonction remplit son budget de pièces avec des grappes (passe de remplissage), sans jamais le dépasser ;
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


class _Arbre:
    """Atelier d'un arbre à glycines : cotes de conception (taille 1) multipliées par `t`, registre des blocs de
    fleurs (plafonds où accrocher les grappes), du bois (obstacles) et des grappes posées, budget de pièces.

    `interdit = (x0, y0)` : aucune grappe dont l'emprise entre dans |x| < x0 ne descend sous y0 (arche)."""

    def __init__(self, b, t=1.0, teinte="mauve", budget=90, interdit=None):
        self.b = b
        self.t = float(t)
        self.rng = b.rng
        self.n0 = len(b.parts)
        self.budget = budget
        self.g = TEINTES.get(teinte, TEINTES["mauve"])
        self.interdit = interdit
        self.plafonds = []  # (cx, cz, sx, sz, yaw, y_bas, y_haut, masse)
        self.masses = []    # (cx, cz, w, d, rot, y_bas, y_haut du corps)
        self.bois = []      # (p0, p1, demi-épaisseur)
        self.grappes = []   # (x, z, demi-largeur, demi-profondeur, yaw, y_haut, y_bas)
        self._m = -1
        self._fams = []     # (cx, cz, demi-largeur, demi-profondeur, rot, famille)

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
        detail 1 : corps + sommet ; 2 : + semelle sombre dessous ; 3 : + corps tourné de 45° (contour octogonal)
        et étage. Renvoie le haut."""
        nuit, fonce, mauve, claire, _pale = self.g
        self._m += 1
        self.masses.append((cx, cz, w, d, rot, y0, y0 + h))
        if detail >= 2:  # semelle sombre, un peu en retrait : le dessous se lit d'en bas
            self.bloc(cx, y0 - 0.5, cz, w - 0.4, 0.5, d - 0.4, self.V(mix(nuit, fonce, 0.4)), rot, studs="none",
                      name="Dessous")
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
        fr = np.asarray(_FR[n]) * rng.uniform(0.88, 1.12, n)
        fr = fr / fr.sum()
        yt = y + embed
        for i in range(n):
            h = L * fr[i] + (embed if i == 0 else 0.0)
            wi = larg * _LG[n][i]
            jx, jz = (rng.uniform(-0.05, 0.05, 2) * larg) if i else (0.0, 0.0)
            dyaw = float(rng.uniform(-8, 8)) if i else 0.0
            self.b.boxc(self.p(x + jx, yt - h / 2, z + jz), self.p(wi, h, wi), cols[i],
                        yaw=yaw + dyaw, studs="none", collide=False, name="Grappe")
            yt -= h
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
        L = self._longueur(x, L, demi + ep / 2 + 0.12)(y)
        if L < 1.6:
            return False
        if not self.place_libre(x, z, demi, ep / 2, yaw, y + embed, y - L, demi):
            return False
        n = n or (2 if L < 5.0 else 3 if L < 9.0 else 4)
        n = min(n, self.reste())
        if n < 2:
            return False
        cols = self.degrade(n, s0)
        fr = np.asarray(_FR[n]) * rng.uniform(0.88, 1.12, n)
        fr = fr / fr.sum()
        yt, off, wprev = y + embed, 0.0, larg
        for i in range(n):
            h = L * fr[i] + (embed if i == 0 else 0.0)
            wi = larg * _LR[n][i]
            if i:
                jeu = (wprev - wi) / 2
                off += float(rng.choice((-1, 1))) * jeu * float(rng.uniform(0.35, 0.95))
            dx, dz = _monde(off, 0.0, yaw)
            self.b.boxc(self.p(x + dx, yt - h / 2, z + dz), self.p(wi, h, ep * (1 - 0.12 * i)), cols[i],
                        yaw=yaw, studs="none", collide=False, name="Grappe")
            wprev = wi
            yt -= h
        self.grappes.append((x, z, demi, ep / 2, yaw, y + embed, y - L))
        return True

    def degrade(self, n, s0=None):
        """Couleurs des n segments, prises sur la rampe foncé → mauve → clair → pointe : départ s0 (plus ou moins
        sombre selon la grappe), pointe toujours pâle."""
        nuit, fonce, mauve, claire, pale = self.g
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

    def grappes_branche(self, p0, p1, n, L, larg=1.4):
        """n grappes pendues sous une branche (sommet noyé dans le bois), réparties entre 25 % et 90 % de sa longueur."""
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        for i in range(n):
            f = 0.25 + 0.65 * (i + 0.5) / n + float(self.rng.uniform(-0.05, 0.05))
            q = p0 + (p1 - p0) * f
            Lg = float(self.rng.uniform(*L))
            # la grappe est noyée dans la branche : on la teste sans le bois porteur
            bois, self.bois = self.bois, [o for o in self.bois if not (np.allclose(o[0], p0) and np.allclose(o[1], p1))]
            self.grappe(float(q[0]), float(q[2]), Lg, larg, y=float(q[1]) - 0.2, embed=0.3)
            self.bois = bois

    def frange(self, im, n, L, larg=1.5, vague=0.55, mode="rideau", nseg=None, ep=0.5, differe=False):
        """n grappes autour de la masse n° im, longueurs entre L[0] et L[1] (sous la masse) qui ondulent autour
        d'elle (ourlet festonné) avec une part d'aléatoire.
        mode "rideau" : rubans tangents au bord, qui partent du haut du flanc et l'habillent ;
        mode "bord" : colonnes à cheval sur le bord, depuis le milieu du flanc ;
        mode "dessous" : colonnes sous la masse, en retrait du bord."""
        rng = self.rng
        cx, cz, w, d, rot, y0, y1 = self.masses[im]
        ph2 = rng.uniform(0, 2 * math.pi)
        out = []
        if mode == "rideau":
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
                tx, tz = px[k + 1] - px[k], pz[k + 1] - pz[k]
                dx, dz = _monde(lx, lz, rot)
                wtx, wtz = _monde(tx, tz, rot)
                yaw = math.degrees(math.atan2(-wtz, wtx)) + float(rng.uniform(-10, 10))
                th = math.atan2(lz / az, lx / ax)
                s = 0.5 + 0.5 * math.sin(3 * th + ph2)
                Lg = L[0] + (L[1] - L[0]) * (vague * s + (1 - vague) * rng.uniform())
                yh = y1 - 0.25 - float(rng.uniform(0.0, 0.35))
                out.append((self.ruban, (cx + dx, cz + dz, Lg, larg * rng.uniform(0.85, 1.15), yaw, y0, yh - y0),
                            dict(sauf=im, n=nseg, ep=ep)))
            return out if differe else [f(*a, **k) for f, a, k in out]
        if mode == "bord":
            marge = larg * 0.22
        else:
            marge = larg * 0.81 + 0.25
        rx, rz = w / 2 - marge, d / 2 - marge
        ph = rng.uniform(0, 2 * math.pi)
        for i in range(n):
            th = ph + 2 * math.pi * (i + rng.uniform(-0.2, 0.2)) / n
            cth, sth = math.cos(th), math.sin(th)
            k = 1.0 / max(abs(cth), abs(sth)) ** 0.5
            lx, lz = rx * cth * min(k, 1.25), rz * sth * min(k, 1.25)
            lx, lz = max(-rx, min(rx, lx)), max(-rz, min(rz, lz))
            dx, dz = _monde(lx, lz, rot)
            s = 0.5 + 0.5 * math.sin(3 * th + ph2)
            Lg = L[0] + (L[1] - L[0]) * (vague * s + (1 - vague) * rng.uniform())
            lg = larg * rng.uniform(0.9, 1.1)
            if mode == "bord":  # sommet à mi-flanc : la grappe habille le bord sans faire de « pied » massif
                yh = y0 + (y1 - y0) * float(rng.uniform(0.35, 0.7))
                out.append((self.grappe, (cx + dx, cz + dz, Lg, lg), dict(y=y0, embed=yh - y0, sauf=im, n=nseg)))
            else:
                out.append((self.grappe, (cx + dx, cz + dz, Lg, lg), dict(n=nseg)))
        return out if differe else [f(*a, **k) for f, a, k in out]

    def remplir(self, L, larg=1.4, essais=900, bord=0.7, reserve=0):
        """Passe de remplissage : des grappes sous les grandes masses jusqu'à épuisement du budget."""
        rng = self.rng
        grands = [q for q in self.plafonds if min(q[2], q[3]) >= 2 * larg + 1]
        if not grands:
            return
        aires = np.array([q[2] * q[3] for q in grands], float)
        pr = aires / aires.sum()
        for _ in range(essais):
            if self.reste() - reserve < 2:
                break
            cx, cz, sx, sz, yaw, _y0, _y1, _m = grands[int(rng.choice(len(grands), p=pr))]
            r = larg * 0.8 + 0.1
            th = rng.uniform(0, 2 * math.pi)
            f = rng.uniform(0.7, 1.0) if rng.uniform() < bord else rng.uniform(0.0, 0.7)
            dx, dz = _monde((sx / 2 - r) * f * math.cos(th), (sz / 2 - r) * f * math.sin(th), yaw)
            self.grappe(cx + dx, cz + dz, float(rng.uniform(*L)), larg * rng.uniform(0.9, 1.1))


def _franges(T, specs, ep=0.5):
    """Pose les franges de plusieurs masses à tour de rôle (une grappe de chaque masse, puis la suivante…) :
    si le budget s'épuise, toutes les masses restent habillées de façon égale."""
    files = [T.frange(im, n, L, larg, mode=mode, nseg=nseg[0] if nseg else None, ep=ep, differe=True)
             for (im, n, L, larg, mode, *nseg) in specs]
    k = 0
    while any(files) and T.reste() >= 2:
        f = files[k % len(files)]
        if f:
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
        for (ib, n, L, larg) in S.get("grappes_branches", ()):
            pts = S["branches"][ib][0]
            T.grappes_branche(pts[-2], pts[-1], n, L, larg)
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
        franges=[(1, 13, (2.5, 8.0), 1.5, "rideau"), (2, 13, (2.5, 8.0), 1.5, "rideau"), (3, 13, (3.0, 8.5), 1.5, "rideau"),
                 (4, 12, (2.5, 7.5), 1.5, "rideau"), (0, 14, (2.0, 5.0), 1.5, "rideau")],
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
        franges=[(1, 16, (5.0, 9.5), 1.5, "rideau"), (2, 9, (3.0, 7.5), 1.5, "rideau"), (3, 9, (3.0, 7.5), 1.5, "rideau"),
                 (4, 12, (3.0, 6.5), 1.5, "rideau"), (0, 13, (2.5, 6.0), 1.5, "rideau")],
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
        franges=[(2, 10, (2.5, 7.0), 1.5, "rideau"), (3, 10, (3.5, 8.5), 1.5, "rideau"), (0, 14, (2.5, 7.0), 1.5, "rideau"),
                 (1, 14, (4.0, 9.0), 1.5, "rideau")],
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
        franges=[(0, 35, (7.0, 10.5), 1.5, "rideau", 3)],
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
        feuilles=[(0, 0.6, -0.5, 4.0, 3.0, 25, 2), (0, -0.7, 0.4, 3.6, 3.2, -15, 1), (2, 0.4, 0.4, 3.0, 2.6, 40, 2), (4, -0.4, -0.3, 3.4, 2.8, 10, 1)],
        franges=[(1, 22, (6.0, 12.0), 2.2, "rideau"), (2, 22, (6.0, 12.0), 2.2, "rideau"),
                 (3, 22, (6.0, 12.0), 2.2, "rideau"), (4, 22, (6.0, 12.0), 2.2, "rideau"),
                 (5, 22, (6.0, 12.0), 2.2, "rideau"), (0, 26, (4.0, 8.0), 2.2, "rideau")],
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
        feuilles=[(2, -0.5, 0.3, 3.6, 3.0, 20, 2), (0, 0.5, 0.6, 3.6, 2.8, -10, 1), (4, 0.4, 0.5, 3.2, 2.6, 30, 2), (3, 0.3, -0.5, 3.2, 2.4, 0, 1)],
        franges=[(1, 24, (8.0, 14.0), 2.2, "rideau"), (2, 16, (6.0, 11.0), 2.2, "rideau"),
                 (3, 16, (6.0, 11.0), 2.2, "rideau"), (4, 18, (5.0, 9.0), 2.2, "rideau"),
                 (0, 22, (4.0, 8.0), 2.2, "rideau")],
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
        feuilles=[(0, 0.6, 0.4, 3.4, 2.8, 25, 2), (1, 0.5, -0.5, 3.2, 2.8, -20, 1), (2, -0.4, -0.3, 3.0, 2.4, 15, 2), (5, 0.3, 0.5, 3.0, 2.4, 40, 1)],
        franges=[(2, 16, (6.0, 11.0), 2.2, "rideau"), (3, 14, (5.0, 10.0), 2.2, "rideau"),
                 (4, 16, (7.0, 13.0), 2.2, "rideau"), (5, 14, (6.0, 12.0), 2.2, "rideau"),
                 (0, 22, (5.0, 10.0), 2.2, "rideau"), (1, 22, (6.0, 12.0), 2.2, "rideau")],
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
        feuilles=[(0, 0.6, -0.5, 3.4, 2.8, 25, 2), (2, -0.4, 0.5, 3.2, 2.6, -15, 1), (3, 0.5, -0.4, 3.0, 2.4, 30, 2), (0, -0.5, 0.45, 3.0, 2.4, 0, 1)],
        franges=[(1, 18, (7.0, 13.0), 2.2, "rideau"), (2, 18, (7.0, 13.0), 2.2, "rideau"),
                 (3, 18, (7.0, 13.0), 2.2, "rideau"), (4, 18, (7.0, 13.0), 2.2, "rideau"),
                 (0, 22, (3.0, 7.0), 2.2, "rideau")],
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
    en x = ±portee/2 (jamais à |x| < 32), branches qui montent et se rejoignent au-dessus du couloir, plafond de fleurs
    et rideaux de grappes. Au-dessus de |x| < 31, rien ne descend sous `hauteur` (la caméra Roblox ne saute pas) ;
    sur les côtés, de longs rideaux de grappes retombent sur les trottoirs.
    0 berceau symétrique, 1 asymétrique (un côté plus haut, plafond penché), 2 tunnel profond (deux rangées de lobes),
    3 glycines blanches et mauves mêlées, sommet en pointe. ≤ 220 pièces."""
    v = variant % 4
    rng = b.rng
    P = max(float(portee) / 2, 37.5)       # les troncs restent hors de |x| < 32
    H = float(hauteur)
    X0 = COULOIR_X
    D = (18.0, 16.0, 26.0, 20.0)[v]       # profondeur (le long du couloir, axe Z)
    teinte = ("mauve", "violet", "mauve", "blanc")[v]
    T = _Arbre(b, 1.0, teinte, budget=220, interdit=(X0, H))
    asym = (0.0, 3.5, 0.0, 0.0)[v]         # côté +x plus haut de `asym`
    pointe = (0.0, 0.0, 0.0, 3.0)[v]       # sommet relevé (arc brisé)

    def masse(cx, y0, cz, w, d, h, rot, det):
        # famille de hauteurs propre à chaque masse (aucune voisine ne la partage)
        T.masse(cx, math.floor(y0 * 2) / 2 + T.famille(cx, cz, w, d, rot), cz, w, d, h, rot, det)

    with b.group("ArcheGlycines"):
        with b.group("Bois"):
            for s in (-1, 1):
                dh = asym if s > 0 else 0.0
                z0 = rng.uniform(-0.6, 0.6)
                X = lambda dx: s * (P + dx)  # noqa: E731  (dx < 0 : vers le couloir)
                tA = [(X(0.0), 0, z0 - 1.2), (X(-1.6), 9.5, z0 + 1.0), (X(-2.8), 20, z0 - 0.9), (X(-3.4), 29, z0 + 0.6),
                      (X(-3.6), H + 2.5 + dh, z0)]
                tB = [(X(1.8), 0, z0 + 2.0), (X(-0.6), 7, z0 - 1.8), (X(-0.4), 15.5, z0 + 1.9), (X(-2.8), 24.5, z0 - 1.4),
                      (X(-3.0), H - 1 + dh, z0 + 0.8)]
                tC = [(X(0.6), 0, z0 - 3.4), (X(1.6), 10, z0 - 1.6), (X(-0.8), 21, z0 - 2.6)]
                T.tige(tA, 3.2, T.ecorce(0), (10 * s, 32 * s, 54 * s, 76 * s))
                T.tige(tB, 2.4, T.ecorce(1), (-15 * s, 20 * s, -30 * s, 8 * s))
                T.tige(tC, 1.6, T.ecorce(2), (25 * s, 50 * s))
                T.racines(X(0.4), z0, [(90 * s + a, lg, h, lw) for (a, lg, h, lw) in
                                       ((-10, 4.5, 2.6, 2.4), (60, 3.6, 2.0, 2.0), (-80, 3.8, 2.2, 2.0),
                                        (150, 3.2, 1.8, 1.8))])
                # branches au-dessus de `hauteur` : la maîtresse rejoint l'autre côté et s'y entrelace
                yb = H + dh
                ytop = H + 11.5 + pointe + dh * 0.5
                T.tige([(X(-3.6), yb + 1.0, z0), (X(-12), yb + 6.5, z0 - 0.8), (X(-23), yb + 9.5 + pointe * 0.6, 0.6),
                        (-s * 2.5, ytop, 0.0)], 2.4, T.ecorce(0), (12 * s, -14 * s, 20 * s), name="Branche")
                for sz in (-1, 1):
                    zd = (D / 2 - 2.0) * sz
                    T.tige([(X(-3.4), yb + 1.5, z0 + 0.6 * sz), (X(-10), yb + 6.0, zd * 0.7), (X(-18), yb + 8.6, zd)],
                           1.6, T.ecorce(1), (20 * sz,), name="Branche")
        with b.group("Fleurs"):
            # plafond au-dessus du couloir : lobes le long de la maîtresse
            for i, xc in enumerate((-0.64, -0.32, 0.0, 0.32, 0.64)):
                x = xc * P
                s = 1 if x >= 0 else -1
                dh = asym if x > 0 else 0.0
                # hauteur de la branche maîtresse à cet endroit (approchée), moins 1
                f = abs(x) / P
                y0 = H + 10.0 - 4.5 * f ** 2 + pointe * (1 - f) + dh * f - 1.0
                if v == 2:  # deux rangées de lobes décalées (tunnel profond)
                    for zr in (-D / 4, D / 4):
                        masse(x + rng.uniform(-1, 1) + zr * 0.1, y0 + rng.uniform(-0.5, 0.5), zr, 13, D / 2 + 1, 2.5,
                              rng.uniform(-10, 10), 2)
                else:
                    masse(x, y0, rng.uniform(-1, 1), 14, D, 3.0 if i == 2 else 2.5, rng.uniform(-8, 8), 3 if i == 2 else 2)
            # lobes au bout des branches de biais (avant et arrière)
            for s in (-1, 1):
                dh = asym if s > 0 else 0.0
                for sz in (-1, 1):
                    zd = (D / 2 - 2.0) * sz
                    masse(s * (P - 18), H + dh + 7.6, zd, 9, 7, 2.0, rng.uniform(-15, 15), 1)
            # raccord au-dessus des troncs, à la limite du couloir (bas à hauteur + 1,5)
            for s in (-1, 1):
                dh = asym if s > 0 else 0.0
                masse(s * (P - 6), H + 1.5 + dh, 0.0, 8, D - 4, 2.5, 0, 1)
            # masses latérales autour des troncs (hors couloir : |x| ≥ 31) et lobes extérieurs plus bas
            for s in (-1, 1):
                dh = asym if s > 0 else 0.0
                wl = min(10.0, 2 * (P - 2 - X0))
                masse(s * (P - 2), H - 4.0 + dh, 0.0, wl, D - 2, 3.0, 0, 2)
                masse(s * (P + 4), H - 7.0 + dh, 2.5 * s, 7, 10, 2.0, 0, 1)
            for (im, fx, fz, sx, sz, yaw, ton) in ((2, 0.45, -0.5, 3.4, 2.6, 20, 2), (1, -0.4, 0.45, 3.0, 2.4, -25, 1),
                                                   (3, 0.4, 0.5, 3.0, 2.4, 35, 2), (len(T.masses) - 3, 0.3, -0.4, 3.0, 2.2, 10, 1)):
                T.feuilles_sur(im, fx, fz, sx, sz, yaw, ton)
        with b.group("Grappes"):
            nm = len(T.masses)
            specs = []
            for im in range(nm):
                cx = T.masses[im][0]
                if abs(cx) >= X0 + 2:      # côtés : longs rideaux sur les trottoirs
                    specs.append((im, 16, (8.0, 15.0), 2.2, "rideau"))
                else:                      # plafond : grappes courtes, la zone interdite les borne
                    specs.append((im, 18, (4.0, 9.0), 2.0, "rideau"))
            _franges(T, specs, ep=0.6)
            T.remplir((3.0, 8.0), 1.1)
    return _infos(b, T.n0)
