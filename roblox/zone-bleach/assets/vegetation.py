"""Végétation de la zone Bleach (la cité blanche aux toits ocre) en style stud : cerisiers, cerisiers géants,
pins taillés en nuages, massifs d'arbres verts, buissons taillés, rochers et jardin d'étang au pont rouge.

Fonctions (signatures appelées par `zone.py`) :
- `cerisier(b, variant, taille)` : ≤ 40 pièces, 13 à 18 × taille de haut, houppier dans un rayon de 7 × taille ;
  0 rond, 1 parasol, 2 ovale élancé, 3 pleureur (shidare), 4 blanc-rosé ;
- `cerisier_geant(b, variant, taille)` : ≤ 150 pièces, 26 à 34 de haut, houppier dans un rayon de 16 ;
  0 dôme large et anneau de pierres, 1 arbre sacré élancé à corde shimenawa, 2 pleureur géant,
  3 double tronc penché, corde et pierres ;
- `pin(b, variant)` : ≤ 40 pièces, niwaki de 12 à 18, emprise ≤ 12 × 12 ;
- `massif_arbres(b, variant, largeur, profondeur)` : ≤ 70 pièces, 3 à 5 feuillus verts dans largeur × profondeur ;
- `buisson(b, variant)` : ≤ 8 pièces dans 2,6 × 2,6, haut de 2,4 au plus (2 et 3 : azalées fleuries) ;
- `rocher(b, variant, taille)` : ≤ 10 pièces, pierre pâle chaude et plaque de mousse ou de lichen ;
- `bassin_pont(b, variant, largeur, profondeur)` : ≤ 80 pièces, étang bordé de pierres, pont tambour laqué
  rouge le long de Z local, pas japonais, rochers, lanterne de pierre, iris.

Principes :
- houppiers en « lobes » : semelle sombre en retrait (le dessous se lit d'en bas), corps, corps tourné de 45°
  (contour octogonal), deux bouffées décalées plus claires et studdées ; jamais de boules ;
- quatre ou cinq roses du plus foncé (dessous) au plus pâle (sommet ensoleillé) ; les verts restent en petites
  masses, jamais émeraude ;
- bois tordu : segments inclinés et vrillés (`_poutre`), racines en coins ; troncs et racines solides,
  feuillage, pétales et petits détails `collide=False` ;
- pas de faces coplanaires : chaque lobe a sa « famille » de hauteurs (fraction de son y0 modulo 0,5 sur la
  grille du 1/32, toutes ses faces horizontales sur y0 + k/2) ; les rameaux pendants finissent sur un 1/64 impair ;
- l'emprise annoncée est garantie par construction : chaque lobe est rétréci jusqu'à tenir dans le rayon (ou la
  boîte) de l'asset, chaque rameau est rentré sous son lobe ;
- rien ne flotte : chaque lobe est porté par une branche ou mord dans un lobe porté, chaque rameau est noyé dans
  son lobe, les pétales sont posés au sol.
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
SAK, SAK_CL, SAK_PA, SAK_VIF, SAK_FO = c("sakura"), c("sakura_clair"), c("sakura_pale"), c("sakura_vif"), c("sakura_fonce")
# Dégradés de lobe : (dessous, corps, facette, dessus, sommet)
ROSES = {
    "rose": (SAK_FO, mix(SAK_VIF, SAK, 0.3), SAK, mix(SAK, SAK_CL, 0.6), mix(SAK_CL, SAK_PA, 0.5)),
    "vif": (shade(SAK_FO, 0.9), SAK_FO, SAK_VIF, mix(SAK_VIF, SAK, 0.6), SAK_CL),
    "pale": (mix(SAK_VIF, SAK, 0.55), mix(SAK, SAK_CL, 0.35), mix(SAK_CL, SAK_PA, 0.4), SAK_PA, mix(SAK_PA, BLANC, 0.6)),
}
VERTS = (c("feuille_nuit"), c("feuille_fonce"), c("feuille"), c("feuille_claire"),
         mix(c("feuille_claire"), c("herbe_claire"), 0.6))
VERTS_SOMBRES = (shade(c("feuille_nuit"), 0.9), c("feuille_nuit"), c("feuille_fonce"), c("feuille"), c("feuille_claire"))
TRONC, TRONC_CL = c("tronc"), c("tronc_clair")
ECORCE_PIN = mix(mix(c("tronc_clair"), c("bois_moyen"), 0.35), c("terre_cuite"), 0.18)
ECORCE_FEUILLU = mix(c("tronc_clair"), c("bois_gris"), 0.45)
ROCHE = (c("roche_ombre"), c("roche_fonce"), c("roche"), c("roche_claire"))


# ---------------------------------------------------------------------------
# Outils géométriques
# ---------------------------------------------------------------------------

def _monde(lx, lz, yaw):
    """Repère d'un bloc tourné de `yaw` → monde (même convention que kit.rot_y)."""
    a = math.radians(yaw)
    ca, sa = math.cos(a), math.sin(a)
    return ca * lx + sa * lz, -sa * lx + ca * lz


def _local(dx, dz, yaw):
    """Monde → repère d'un bloc tourné de `yaw`."""
    a = math.radians(yaw)
    ca, sa = math.cos(a), math.sin(a)
    return ca * dx - sa * dz, sa * dx + ca * dz


def _coins(cx, cz, sx, sz, yaw):
    out = []
    for lx in (-sx / 2, sx / 2):
        for lz in (-sz / 2, sz / 2):
            dx, dz = _monde(lx, lz, yaw)
            out.append((cx + dx, cz + dz))
    return out


def _sortie(px, pz, ux, uz, cx, cz, sx, sz, yaw):
    """Distance que parcourt le rayon (P, U) avant de sortir du rectangle (0 si P est dehors)."""
    lx, lz = _local(px - cx, pz - cz, yaw)
    dx, dz = _local(ux, uz, yaw)
    t = math.inf
    for p, d, h in ((lx, dx, sx / 2), (lz, dz, sz / 2)):
        if abs(p) > h:
            return 0.0
        if abs(d) > 1e-9:
            t = min(t, (h - p) / d if d > 0 else (-h - p) / d)
    return t


def _poutre(b, p0, p1, w, d, col, twist=0.0, ext0=0.0, ext1=0.0, **kw):
    """Bloc de section w × d dont l'axe Y local va de p0 à p1 (prolongé de ext0 / ext1 aux bouts), vrillé de
    `twist` degrés autour de son axe : troncs, branches, rampes, feuilles d'iris."""
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


def _impair64(y):
    """Multiple impair de 1/64 : le bas des rameaux ne tombe jamais au niveau d'une face de lobe (grille du 1/32)."""
    return (math.floor(y * 32) + 0.5) / 32


def _r2(v):
    """Arrondi au demi-stud (au moins 1)."""
    return max(1.0, round(v * 2) / 2)


def _infos(b, n0) -> dict:
    """Emprise (x, z) et hauteur réelles des pièces ajoutées depuis n0, dans le repère de l'asset."""
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
    if not np.isfinite(lo).all():
        return {"emprise": (0, 0), "hauteur": 0}
    return {"emprise": (round(float(hi[0] - lo[0]), 1), round(float(hi[2] - lo[2]), 1)), "hauteur": round(float(hi[1]), 1)}


# ---------------------------------------------------------------------------
# Atelier d'arbre : cotes de conception × t, emprise garantie, lobes, bois, rameaux, pétales
# ---------------------------------------------------------------------------

class _Atelier:
    """Cotes de conception (taille 1) multipliées par `t`. `rmax` : rayon que rien ne dépasse (cotes de
    conception, autour de l'origine) ; `boite` : demi-largeur et demi-profondeur à ne pas dépasser."""

    def __init__(self, b, t=1.0, rmax=None, boite=None):
        self.b = b
        self.t = float(t)
        self.rng = b.rng
        self.n0 = len(b.parts)
        self.rmax = rmax
        self.boite = boite
        self.masses = []  # {"c": (cx, cz), "y0", "top", "blocs": [(cx, cz, sx, sz, yaw)]}
        self.familles = []
        self.n_brins = 0

    def famille(self, y0) -> float:
        """Recale y0 sur une famille de hauteurs (fraction modulo 0,5 sur la grille du 1/32) qu'aucun autre lobe
        de l'arbre n'utilise : deux lobes n'ont jamais de faces horizontales au même niveau."""
        f = next((k / 32 for k in _FAMILLES if k / 32 not in self.familles), _FAMILLES[len(self.familles) % 16] / 32)
        self.familles.append(f)
        base = math.floor(y0 * 2) / 2
        return min((base - 0.5 + f, base + f, base + 0.5 + f), key=lambda y: abs(y - y0))

    def p(self, *v):
        return tuple(float(x) * self.t for x in v)

    def V(self, col, a=0.03):
        return vary(col, self.rng, a)

    def dedans(self, cx, cz, sx, sz, yaw, marge=0.05) -> bool:
        for (x, z) in _coins(cx, cz, sx, sz, yaw):
            if self.rmax is not None and math.hypot(x, z) > self.rmax - marge:
                return False
            if self.boite is not None and (abs(x) > self.boite[0] - marge or abs(z) > self.boite[1] - marge):
                return False
        return True

    def bloc(self, cx, y0, cz, sx, sy, sz, col, yaw=0.0, **kw):
        kw.setdefault("studs", "top")
        kw.setdefault("collide", False)
        kw.setdefault("name", "Feuillage")
        return self.b.boxc(self.p(cx, y0 + sy / 2, cz), self.p(sx, sy, sz), col, yaw=yaw, **kw)

    # -- bois --------------------------------------------------------------
    def tige(self, pts, w, cols, torsions=(0.0,), name="Tronc", collide=True, effile=1.0):
        """Tige en segments inclinés et vrillés (de w à w × effile) ; un segment qui part du sol y est un peu
        enfoncé pour qu'aucun coin ne flotte."""
        pts = [np.asarray(q, float) for q in pts]
        n = len(pts) - 1
        for i in range(n):
            p0, p1 = pts[i], pts[i + 1]
            u = (p1 - p0) / np.linalg.norm(p1 - p0)
            wi = w * (1 - (1 - effile) * (i / max(1, n - 1)))
            if i == 0 and p0[1] <= 1e-6:
                horiz = math.sqrt(max(0.0, 1.0 - u[1] ** 2))
                e0 = (wi * 0.72 * horiz + 0.1) / max(u[1], 0.3)
            else:
                e0 = wi * 0.45
            e1 = wi * 0.45 if i < n - 1 else wi * 0.3
            col = cols[i % len(cols)] if isinstance(cols, list) else cols
            _poutre(self.b, self.p(*p0), self.p(*p1), wi * self.t, wi * self.t, col, torsions[i % len(torsions)],
                    e0 * self.t, e1 * self.t, name=name, collide=collide)

    def racines(self, specs, col, cx=0.0, cz=0.0):
        """Racines en coins rayonnants : (angle, longueur, hauteur, largeur)."""
        for (ang, lg, h, lw) in specs:
            with self.b.at(self.p(cx, 0, cz), yaw=ang):
                self.b.wedge(self.p(-lw / 2, 0, 0.3), self.p(lw / 2, h, 0.3 + lg), self.V(col, 0.04), down="+z",
                             name="Racine")

    # -- lobes ---------------------------------------------------------------
    @staticmethod
    def _geo(cx, cz, w, d, h, rot, detail):
        """Blocs d'un lobe : (rôle, cx, cz, sx, sz, yaw, y_bas relatif, hauteur)."""
        out = []
        if detail >= 2:
            out.append(("dessous", cx, cz, max(1.0, w - 2), max(1.0, d - 2), rot, -0.5, 0.5))
        out.append(("corps", cx, cz, w, d, rot, 0.0, h))
        s = _r2(min(w, d) * 0.86)
        ox, oz = _monde(0.25, -0.25, rot)
        out.append(("facette", cx + ox, cz + oz, s, s, rot + 45, 0.5, h))
        if detail >= 0:
            he = max(1.5, round(h * 0.6 * 2) / 2)
            ox, oz = _monde(w * 0.12, -d * 0.1, rot)
            out.append(("dessus", cx + ox, cz + oz, _r2(w * 0.6), _r2(d * 0.56), rot, h, he))
            if detail >= 3:
                hc = max(1.0, round(h * 0.4 * 2) / 2)
                ox, oz = _monde(-w * 0.16, d * 0.14, rot)
                e = _r2(min(w, d) * 0.42)
                out.append(("sommet", cx + ox, cz + oz, e, e, rot + 45, h - 0.5, he + hc + 0.5))
        return out

    def lobe(self, cx, y0, cz, w, d, h, rot, pal, detail=3, studs_dessous="none"):
        """Lobe de fleurs ou de feuilles : semelle sombre en retrait, corps droit, corps à 45°, bouffées claires.
        detail −1 : corps + facette ; 0 et 1 : + dessus ; 2 : + semelle ; 3 : + sommet pâle.
        Rétréci jusqu'à tenir dans l'emprise. Renvoie l'indice du lobe (pour ses rameaux)."""
        cols = dict(zip(("dessous", "corps", "facette", "dessus", "sommet"), pal))
        h = max(1.0, round(h * 2) / 2)
        y0 = y0 if y0 <= 0 else self.famille(y0)
        for _ in range(40):
            geo = self._geo(cx, cz, w, d, h, rot, detail)
            if all(self.dedans(g[1], g[2], g[3], g[4], g[5]) for g in geo):
                break
            w, d = max(1.5, w - 0.5), max(1.5, d - 0.5)
        top = y0
        for (role, x, z, sx, sz, yaw, yb, hh) in geo:
            dessous = role == "dessous"
            self.bloc(x, y0 + yb, z, sx, hh, sz, self.V(cols[role]), yaw, studs=studs_dessous if dessous else "top",
                      name="Dessous" if dessous else "Feuillage")
            top = max(top, y0 + yb + hh)
        blocs = [(g[1], g[2], g[3], g[4], g[5]) for g in geo if g[0] in ("corps", "facette")]
        self.masses.append({"c": (cx, cz), "y0": y0, "top": top, "blocs": blocs, "w": w, "d": d})
        return len(self.masses) - 1

    def brin(self, im, ang, L, larg=0.6, ep=0.6, col=None, bas_min=3.2, prof=0.9, L2=0.0, col2=None, bord=False):
        """Rameau pendant sous le lobe n° im, vers la direction `ang` (degrés), rentré sous le bord du lobe (ou,
        avec `bord`, en rideau qui affleure le flanc du lobe et le dépasse de 0,12) ; le haut est noyé de `prof`
        dans le lobe, le bas tombe sur un 1/64 impair. Avec L2 > 0, une pointe plus fine et plus claire
        prolonge le rameau (rameau en deux gradins)."""
        m = self.masses[im]
        cx, cz = m["c"]
        a = math.radians(ang)
        ux, uz = math.cos(a), math.sin(a)
        r = max(_sortie(cx, cz, ux, uz, *blc) for blc in m["blocs"]) - ep / 2 + (0.12 if bord else -0.35)
        yaw = 90 - ang
        while r > 0 and not self.dedans(cx + r * ux, cz + r * uz, larg, ep, yaw):
            r -= 0.25
        r = max(0.0, r)
        x, z = cx + r * ux, cz + r * uz
        k = self.n_brins
        self.n_brins += 1
        haut = m["y0"] + prof + 0.03 * (k % 8)            # hors de la grille du 1/32 et distinct de ses voisins
        bas = _impair64(max(bas_min + (L2 if L2 else 0.0), m["y0"] - L)) + (k % 3) / 32
        p = self.bloc(x, bas, z, larg, haut - bas, ep, col, yaw, studs="none", name="Rameau")
        if L2 > 0:
            bas2 = _impair64(max(bas_min, bas - L2)) + ((k + 1) % 3) / 32
            if bas - bas2 > 0.3:
                self.bloc(x, bas2, z, larg * 0.6, bas + 0.25 - bas2, ep * 0.8, col2 or col, yaw, studs="none",
                          name="Rameau")
        return p

    def petales(self, specs, cols):
        """Tapis de pétales posés au sol : (angle, rayon, sx, sz) ; épaisseurs 0,1 à 0,19 (non mises à l'échelle)."""
        for i, (ang, r, sx, sz) in enumerate(specs):
            a = math.radians(ang)
            yaw = float(self.rng.uniform(0, 90))
            while r > 0 and not self.dedans(r * math.cos(a), r * math.sin(a), sx, sz, yaw, marge=0.2):
                r -= 0.25
            x, z = self.p(r * math.cos(a), r * math.sin(a))
            hh = 0.1 + 0.0125 * (i % 8)                     # épaisseurs toutes différentes : pas de dessus coplanaires
            self.b.boxc((x, hh / 2, z), (sx * self.t, hh, sz * self.t), self.V(cols[i % len(cols)], 0.02), yaw=yaw,
                        studs="none", collide=False, shadow=False, name="Petales")


_FAMILLES = (0, 5, 10, 15, 3, 8, 13, 2, 7, 12, 1, 6, 11, 4, 9, 14)


def _polaire(ang, r):
    a = math.radians(ang)
    return r * math.cos(a), r * math.sin(a)


# ---------------------------------------------------------------------------
# Cerisiers
# ---------------------------------------------------------------------------
# lobes : (angle, rayon, y0, w, d, h, detail, dyaw, branche, origine) — centre en polaire autour de l'axe,
#   yaw = -angle arrondi au multiple de 45° le plus proche + dyaw (blocs droits ou à 45° : silhouette nette) ;
#   branche = largeur de la branche qui le porte (0 : il mord dans un lobe voisin) ; origine = indice du point
#   du tronc d'où part la branche (-1 : fourche). Chaque y0 est recalé sur sa propre famille de hauteurs.
# rameaux : (lobe, angle, L) grappe trapue sous le bord ; (lobe, angle, L, largeur) rameau fin ;
#   (lobe, angle, L, L2, largeur) rideau en deux gradins au ras du flanc (pleureurs). Pétales : (angle, rayon, sx, sz).
CERISIERS = [
    # 0 : rond — tronc court en S, fourche à cinq branches, gros lobe central haut et quatre lobes plus bas autour
    dict(tronc=[(0, 0, 0), (0.5, 3.2, -0.3), (-0.2, 6.0, 0.3)], w=1.8, tors=(12, 38), pal="rose",
         racines=[(20, 2.2, 1.3, 1.3), (140, 2.0, 1.1, 1.2), (255, 2.3, 1.2, 1.3)],
         lobes=[(0, 0.0, 10.5, 8.5, 8, 3, 3, 0, 1.1, -1), (160, 3.6, 8.0, 6, 5.5, 2.5, 2, 0, 0.9, -1),
                (30, 3.7, 8.4, 6, 5.5, 2.5, 2, 0, 0.9, -1), (260, 3.5, 7.6, 5.5, 5, 2.5, 2, 0, 0.8, -1),
                (95, 3.4, 9.0, 5, 5, 2, 1, 0, 0.8, -1)],
         rameaux=[(1, 170, 1.6), (2, 20, 2.0), (3, 250, 1.4)],
         petales=[(40, 4.5, 1.8, 1.2), (170, 5.0, 1.4, 1.6), (280, 3.8, 1.6, 1.2)]),
    # 1 : parasol — tronc bas qui s'ouvre en quatre bras presque horizontaux, houppier large et plat
    dict(tronc=[(0, 0, 0), (-0.4, 3.0, 0.3), (0.3, 5.2, -0.2)], w=1.9, tors=(20, 50), pal="rose",
         racines=[(60, 2.3, 1.3, 1.3), (190, 2.1, 1.2, 1.2), (300, 2.2, 1.2, 1.3)],
         lobes=[(0, 0.0, 8.75, 7, 7, 2.5, 3, 0, 1.0, -1), (45, 4.3, 7.0, 6, 4.5, 2, 2, 0, 0.9, -1),
                (135, 4.4, 6.75, 6, 4.5, 2, 2, 0, 0.9, -1), (225, 4.3, 7.25, 6, 4.5, 2, 2, 0, 0.9, -1),
                (315, 4.4, 6.5, 6, 4.5, 2, 2, 0, 0.9, -1)],
         rameaux=[(1, 45, 1.4), (2, 135, 1.8), (3, 225, 1.5), (4, 315, 2.0)],
         petales=[(10, 5.0, 2.0, 1.3), (130, 4.6, 1.5, 1.7), (250, 5.2, 1.7, 1.2)]),
    # 2 : ovale élancé — tronc plus haut, anneau bas de trois lobes, lobe central haut et pointe
    dict(tronc=[(0, 0, 0), (0.3, 3.5, 0.2), (-0.3, 7.0, -0.2), (0.1, 9.6, 0.2)], w=1.6, tors=(10, 35, 60), pal="rose",
         racines=[(0, 2.0, 1.2, 1.2), (125, 1.9, 1.1, 1.1), (240, 2.1, 1.2, 1.2)],
         lobes=[(0, 0.0, 11.0, 7, 6.5, 3, 3, 0, 1.0, -1), (30, 2.9, 8.1, 5, 4.5, 2.5, 2, 0, 0.8, 2),
                (150, 2.9, 8.4, 5, 4.5, 2.5, 2, 0, 0.8, 2), (270, 2.7, 7.8, 5, 4.5, 2.5, 2, 0, 0.8, 2),
                (210, 1.6, 14.6, 4, 3.5, 1.5, 0, 0, 0, -1)],
         rameaux=[(1, 30, 1.6), (2, 150, 1.9), (3, 270, 1.4)],
         petales=[(60, 4.0, 1.6, 1.2), (190, 4.4, 1.4, 1.5), (300, 3.8, 1.5, 1.2)]),
    # 3 : pleureur (shidare) — tronc haut et souple, dôme rose soutenu d'où retombe un rideau de rameaux en deux
    #     gradins (sombre puis clair) et de rameaux fins
    dict(tronc=[(0, 0, 0), (0.6, 4.0, -0.3), (-0.2, 8.0, 0.4), (0.2, 10.4, 0.0)], w=1.7, tors=(15, 40, 70), pal="vif",
         racines=[(30, 2.2, 1.3, 1.3), (150, 2.0, 1.1, 1.2), (270, 2.2, 1.2, 1.3)],
         lobes=[(0, 0.0, 10.25, 9.5, 9.5, 2.5, 2, 0, 1.1, -1), (20, 0.8, 12.25, 6.5, 6, 2.0, 3, 0, 0, -1)],
         rameaux=[(0, a, L, L2, w) for (a, L, L2, w) in (
             (0, 3.0, 2.6, 1.6), (40, 2.2, 3.0, 1.4), (80, 3.4, 2.4, 1.6), (120, 2.6, 3.2, 1.4), (160, 3.2, 2.2, 1.6),
             (200, 2.4, 3.4, 1.4), (240, 3.4, 2.6, 1.6), (280, 2.0, 2.8, 1.4), (320, 3.0, 3.0, 1.6))]
         + [(0, 20, 4.4, 0.8), (0, 140, 5.0, 0.8), (0, 260, 4.6, 0.8)],
         petales=[(30, 4.6, 1.8, 1.2), (160, 4.2, 1.4, 1.7), (285, 4.8, 1.7, 1.3)]),
    # 4 : blanc-rosé — tronc penché à deux têtes, un gros nuage pâle et trois lobes en gradins
    dict(tronc=[(0, 0, 0), (0.8, 3.0, 0.2), (1.1, 5.6, -0.3)], w=1.7, tors=(18, 44), pal="pale",
         racines=[(80, 2.2, 1.2, 1.3), (200, 2.2, 1.3, 1.3), (320, 1.9, 1.1, 1.1)],
         lobes=[(30, 1.6, 9.5, 8, 7.5, 3, 3, 0, 1.1, -1), (200, 3.4, 7.9, 6.5, 5.5, 2.5, 3, 0, 0.9, -1),
                (300, 3.6, 8.4, 5.5, 5, 2.5, 2, 0, 0.8, -1), (110, 3.3, 10.6, 5, 4.5, 2, 1, 0, 0.8, -1)],
         rameaux=[(1, 210, 1.8), (2, 300, 1.5), (0, 20, 2.0)],
         petales=[(0, 4.8, 1.8, 1.3), (130, 4.2, 1.5, 1.5), (240, 5.0, 1.7, 1.2)]),
]


def _cerisier(b, S, t, rmax, rng, budget=40):
    A = _Atelier(b, t, rmax=rmax)
    pal = ROSES[S["pal"]]
    e = [A.V(TRONC, 0.03), A.V(mix(TRONC, TRONC_CL, 0.55), 0.03)]
    pts = S["tronc"]
    A.tige(pts, S["w"], e, S["tors"], name="Tronc")
    A.racines(S["racines"], shade(TRONC, 0.86))
    for k, (ang, r, y0, w, d, h, det, dyaw, br, org) in enumerate(S["lobes"]):
        ang = ang + float(rng.uniform(-8, 8)) if r > 0 else ang
        r = r + float(rng.uniform(-0.25, 0.25)) if r > 0 else r
        w = _r2(w + float(rng.uniform(-0.5, 0.5)))
        d = _r2(d + float(rng.uniform(-0.5, 0.5)))
        cx, cz = _polaire(ang, r)
        if br:
            o = pts[org]
            fin = (cx, y0 + h * 0.4, cz)
            A.tige([o, fin], br, e[1 - k % 2], (25 * k,), name="Branche", collide=False)
        A.lobe(cx, y0, cz, w, d, h, 45 * round(-ang / 45) + dyaw, pal, det)
    # pendants : grappes trapues sous le bord des lobes ; pleureur : rameaux en deux gradins (sombre puis clair)
    cols_r = (pal[1], pal[2], mix(pal[1], pal[2], 0.5))
    for i, rm in enumerate(S["rameaux"]):
        if len(b.parts) - A.n0 >= budget - len(S["petales"]) - (1 if len(rm) == 5 else 0):
            break
        im, ang, L = rm[:3]
        if len(rm) == 5:  # (lobe, angle, L, L2, largeur) : rideau en deux gradins qui prolonge le flanc du dôme
            A.brin(im, ang, L, rm[4], 0.5, A.V(cols_r[i % 3]), bas_min=max(2.5 / t, 3.0) + 0.1, L2=rm[3],
                   col2=A.V(mix(pal[2], pal[3], 0.3 + 0.35 * (i % 2))), bord=True)
        elif len(rm) == 4:  # (lobe, angle, L, largeur) : rameau fin et clair, un peu en retrait
            A.brin(im, ang, L, rm[3], 0.35, A.V(mix(pal[2], pal[3], 0.5)), bas_min=max(2.5 / t, 3.0) + 0.1)
        else:
            A.brin(im, ang, L, 1.2, 1.0, A.V(cols_r[i % 3]), bas_min=max(2.5 / t, 3.0) + 0.1)
    A.petales(S["petales"], (pal[2], pal[3], mix(pal[1], pal[2], 0.5)))
    return A


def cerisier(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Cerisier en fleurs (13 à 18 × taille de haut, houppier dans un rayon de 7 × taille, dessous du houppier
    à 6 × taille au moins) : tronc brun-violet court et tordu, deux à cinq branches, houppier en lobes de blocs
    roses étagés (dessous foncés, dessus pâles et studdés), quelques rameaux pendants, pétales au sol.
    0 rond, 1 parasol, 2 ovale élancé, 3 pleureur (shidare, rideau de rameaux), 4 blanc-rosé. ≤ 40 pièces."""
    v = variant % len(CERISIERS)
    n0 = len(b.parts)
    with b.group("Cerisier"):
        _cerisier(b, CERISIERS[v], taille, 7.0, b.rng)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Cerisiers géants
# ---------------------------------------------------------------------------
# tronc : points de l'axe principal ; tronc2 : second fût (variante 3) ; membres : (indice du lobe, coude) ;
# lobes : comme les cerisiers (angle, rayon, y0, w, d, h, detail, dyaw, branche, origine) ; origine -2 = haut du
# second fût. Familles de hauteurs sur le 1/32 (16 familles).
GEANTS = [
    # 0 : dôme large — tronc massif à contreforts, cinq membres, grand anneau de lobes, anneau de pierres
    dict(tronc=[(0, 0, 0), (0, 7.5, 0), (0.6, 12.5, -0.4)], w=3.8, tors=(15, 45), pal="rose", h_corde=None,
         pierres=7.0,
         lobes=[(0, 0.0, 21.0, 13, 12, 3.5, 3, 0, 2.0, -1),
                (10, 9.6, 15.0, 10.5, 9.5, 3.5, 3, 0, 1.7, -1), (82, 9.8, 15.5, 10.5, 9.5, 3.5, 3, 0, 1.7, -1),
                (154, 9.4, 14.75, 10.5, 9.5, 3.5, 3, 0, 1.7, -1), (226, 9.8, 15.25, 10.5, 9.5, 3.5, 3, 0, 1.7, -1),
                (298, 9.6, 14.9, 10.5, 9.5, 3.5, 3, 0, 1.7, -1),
                (46, 6.0, 18.0, 9, 8, 3, 3, 0, 0, -1), (190, 6.0, 18.2, 9, 8, 3, 3, 0, 0, -1),
                (262, 5.5, 18.3, 8, 7.5, 3, 2, 0, 0, -1),
                (100, 12.4, 13.09375, 5.5, 4.5, 2, 1, 0, 0, -1), (316, 12.4, 13.21875, 5.5, 4.5, 2, 1, 0, 0, -1)],
         rameaux=[(i, a, L) for (i, a, L) in ((1, 0, 3.4), (1, 30, 2.4), (2, 70, 3.0), (2, 100, 2.2), (3, 150, 3.6),
                                               (3, 175, 2.6), (4, 215, 3.2), (4, 245, 2.4), (5, 290, 3.4), (5, 318, 2.6),
                                               (9, 100, 2.6), (10, 316, 2.8))],
         petales=[(0, 11, 3.0, 2.0), (50, 8, 2.0, 2.5), (100, 12, 2.5, 1.6), (150, 9, 3.0, 2.2), (200, 12.5, 2.2, 1.8),
                  (250, 8.5, 2.6, 2.0), (300, 11.5, 2.0, 2.4), (330, 6.5, 1.6, 1.4)]),
    # 1 : arbre sacré élancé — tronc haut ceint d'une corde à papiers, deux étages de lobes et une couronne
    dict(tronc=[(0, 0, 0), (0, 9.0, 0), (-0.5, 15.0, 0.5), (0.3, 19.5, -0.2)], w=3.6, tors=(10, 40, 70), pal="rose",
         h_corde=6.0, pierres=None,
         lobes=[(0, 0.0, 26.0, 9, 8.5, 3, 3, 20, 1.6, -1),
                (20, 8.4, 17.03125, 9, 8, 3, 3, 0, 1.6, 2), (110, 8.6, 16.53125, 9, 8, 3, 3, 0, 1.6, 2),
                (200, 8.4, 17.28125, 9, 8, 3, 3, 0, 1.6, 2), (290, 8.6, 16.78125, 9, 8, 3, 3, 0, 1.6, 2),
                (65, 5.0, 21.5625, 8, 7, 3, 3, 0, 1.3, -1), (185, 5.2, 21.0625, 8, 7, 3, 3, 0, 1.3, -1),
                (305, 5.0, 21.3125, 8, 7, 3, 2, 0, 1.3, -1),
                (125, 12.2, 14.09375, 5, 4.5, 2, 1, 0, 0, -1), (305, 12.2, 14.21875, 5, 4.5, 2, 1, 0, 0, -1)],
         rameaux=[(i, a, L) for (i, a, L) in ((1, 10, 3.0), (1, 40, 2.2), (2, 100, 3.4), (2, 130, 2.4), (3, 190, 3.0),
                                               (3, 220, 2.6), (4, 280, 3.2), (4, 310, 2.4), (8, 125, 2.6), (9, 305, 2.4))],
         petales=[(20, 10, 2.6, 2.0), (80, 7, 2.0, 2.2), (140, 11, 2.4, 1.6), (200, 8.5, 3.0, 2.0), (260, 11.5, 2.2, 1.8),
                  (320, 9, 2.6, 2.0)]),
    # 2 : pleureur géant — tronc tordu, dôme haut et large, longs rideaux de rameaux en couronne
    dict(tronc=[(0, 0, 0), (0.5, 7.0, -0.3), (-0.6, 13.0, 0.6), (0.2, 18.5, 0.0)], w=3.7, tors=(20, 50, 75), pal="vif",
         h_corde=None, pierres=None,
         lobes=[(0, 0.0, 22.0, 13, 12, 3.5, 3, 10, 2.0, -1),
                (0, 8.4, 20.03125, 9, 8, 3, 3, 0, 1.6, 2), (72, 8.6, 20.53125, 9, 8, 3, 3, 0, 1.6, 2),
                (144, 8.4, 19.78125, 9, 8, 3, 3, 0, 1.6, 2), (216, 8.6, 20.28125, 9, 8, 3, 3, 0, 1.6, 2),
                (288, 8.4, 19.90625, 9, 8, 3, 3, 0, 1.6, 2),
                (86, 12.0, 18.09375, 6, 5, 2.5, 1, 0, 0, -1), (158, 12.0, 18.21875, 6, 5, 2.5, 1, 0, 0, -1),
                (230, 12.0, 18.34375, 6, 5, 2.5, 1, 0, 0, -1)],
         rameaux=[(i, a, L, L2, w) for (i, a, L, L2, w) in (
             (1, -22, 5.0, 4.6, 2.0), (1, 0, 3.6, 4.0, 1.6), (1, 22, 5.4, 4.2, 2.0), (2, 50, 3.8, 4.4, 1.6),
             (2, 72, 5.6, 4.0, 2.0), (2, 94, 4.0, 3.6, 1.6), (3, 122, 5.2, 4.4, 2.0), (3, 144, 3.6, 4.2, 1.6),
             (3, 166, 5.6, 3.8, 2.0), (4, 194, 4.0, 4.4, 1.6), (4, 216, 5.4, 4.0, 2.0), (4, 238, 3.8, 3.6, 1.6),
             (5, 266, 5.6, 4.2, 2.0), (5, 288, 3.6, 4.4, 1.6), (5, 310, 5.0, 4.0, 2.0), (6, 86, 4.4, 3.6, 1.8),
             (7, 158, 4.6, 3.4, 1.8), (8, 230, 4.2, 3.8, 1.8), (1, 340, 4.4, 3.0, 1.4), (3, 110, 4.2, 3.2, 1.4))],
         petales=[(10, 11.5, 3.0, 2.0), (70, 9, 2.4, 2.4), (130, 12, 2.6, 1.8), (190, 10, 3.0, 2.2), (250, 12, 2.2, 2.0),
                  (310, 9.5, 2.6, 2.0), (350, 5.5, 1.6, 1.4)]),
    # 3 : double tronc penché — deux fûts tordus qui s'écartent, deux couronnes, corde et anneau de pierres
    dict(tronc=[(0, 0, 0), (0, 6.5, 0), (-2.0, 11.5, 0.8), (-4.2, 16.0, 1.2)], w=3.6, tors=(15, 40, 65), pal="rose",
         tronc2=[(0, 6.0, 0), (2.4, 10.5, -0.8), (4.6, 14.0, -1.6)], w2=2.6,
         h_corde=4.5, pierres=6.5,
         lobes=[(160, 5.0, 19.0, 10, 9.5, 3.5, 3, 0, 1.8, -1), (340, 5.6, 17.0, 9, 8.5, 3, 3, 0, 1.6, -2),
                (120, 10.2, 14.53125, 8, 7, 3, 3, 0, 1.5, 2), (200, 10.4, 15.28125, 8, 7, 3, 3, 0, 1.5, 2),
                (250, 9.0, 16.03125, 7, 6.5, 2.5, 2, 0, 0, -1),
                (300, 10.2, 13.78125, 8, 7, 3, 3, 0, 1.4, -2), (20, 10.4, 14.65625, 8, 7, 3, 3, 0, 1.4, -2),
                (70, 8.0, 16.90625, 7, 6.5, 2.5, 2, 0, 0, -1),
                (170, 2.0, 23.15625, 6.5, 6, 2.5, 2, 0, 0, -1)],
         rameaux=[(i, a, L) for (i, a, L) in ((2, 120, 3.2), (2, 150, 2.4), (3, 200, 3.4), (3, 230, 2.4), (5, 300, 3.0),
                                               (5, 270, 2.2), (6, 20, 3.4), (6, 50, 2.6), (4, 250, 2.6), (7, 80, 2.4))],
         petales=[(0, 10, 2.6, 2.0), (60, 11.5, 2.2, 1.8), (120, 8, 3.0, 2.2), (180, 11, 2.4, 2.0), (240, 9, 2.6, 1.8),
                  (300, 12, 2.0, 2.4)]),
]


def _corde(A, h, w_tronc, tw):
    """Corde sacrée (shimenawa) autour d'un fût vertical de section w_tronc (vrillé de tw) : quatre torons de
    paille et cinq papiers shide en zigzag qui pendent sur les faces."""
    b = A.b
    corde = A.V(c("corde"), 0.03)
    demi = w_tronc / 2
    with b.at(A.p(0, 0, 0), yaw=tw, group="Corde"):
        for k in range(4):  # torons alternés plus ou moins épais : pas de faces coplanaires aux angles
            with b.at((0, 0, 0), yaw=90 * k):
                b.boxc(A.p(0, h, -(demi + 0.4)), A.p(w_tronc + 1.8, 1.0 + 0.125 * (k % 2), 0.8 + 0.1 * (k % 2)), corde,
                       name="Corde", collide=False)
        for k, (lx, sens) in enumerate(((-0.9, 0), (0.9, 0), (0.0, 1), (-0.8, 2), (0.6, 3))):
            with b.at((0, 0, 0), yaw=90 * sens):
                z = -(demi + 0.7)
                b.boxc(A.p(lx, h - 0.75, z), A.p(0.5, 0.9, 0.1), c("shide"), name="Shide", collide=False, shadow=False)
                b.boxc(A.p(lx + 0.25, h - 1.65, z - 0.05), A.p(0.5, 0.9, 0.1), c("shide"), name="Shide", collide=False,
                       shadow=False)


def _anneau_pierres(A, r, n=10):
    """Anneau bas de pierres taillées autour du pied (studs sur le dessus), joints réguliers."""
    for k in range(n):
        ang = k * 360 / n
        x, z = _polaire(ang, r)
        lg = 2 * math.pi * r / n * 0.84
        h = (0.75, 0.875)[k % 2]
        A.bloc(x, 0, z, lg, h, 1.1, A.V((c("pierre"), c("pierre_claire"), c("pierre_fonce"))[k % 3]), 90 - ang,
               collide=True, name="Pierre")


def cerisier_geant(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Cerisier géant, repère rose au-dessus des murs blancs (26 à 34 de haut, houppier dans un rayon de 16,
    dessous à 8 au moins) : tronc massif à contreforts, quatre à six membres tordus, lobes étagés en cinq roses,
    rameaux pendants, tapis de pétales. 0 dôme large et anneau de pierres, 1 arbre sacré élancé à corde
    shimenawa, 2 pleureur géant, 3 double tronc penché avec corde et pierres. ≤ 150 pièces."""
    v = variant % len(GEANTS)
    S = GEANTS[v]
    rng = b.rng
    n0 = len(b.parts)
    t = taille
    with b.group("CerisierGeant"):
        A = _Atelier(b, t, rmax=16.0)
        pal = ROSES[S["pal"]]
        e = [A.V(TRONC, 0.03), A.V(mix(TRONC, TRONC_CL, 0.5), 0.03), A.V(shade(TRONC, 0.92), 0.03)]
        pts = S["tronc"]
        A.tige(pts, S["w"], e, S["tors"], name="Tronc", effile=0.62)
        if "tronc2" in S:
            A.tige(S["tronc2"], S["w2"], [e[1], e[0]], (30, 60), name="Tronc", effile=0.7)
        # contreforts : grandes racines en coins, plus hautes du côté du tronc
        nr = 6
        for k in range(nr):
            ang = k * 360 / nr + 20 * v + float(rng.uniform(-8, 8))
            lg = 3.6 + 0.8 * ((k + v) % 3)
            hr = 3.4 + 0.6 * ((k + 1) % 2)
            A.racines([(ang, lg, hr, 1.9)], shade(TRONC, 0.85))
        if S["h_corde"]:
            _corde(A, S["h_corde"], S["w"], S["tors"][0])
        if S["pierres"]:
            _anneau_pierres(A, S["pierres"])
        for k, (ang, r, y0, w, d, h, det, dyaw, br, org) in enumerate(S["lobes"]):
            ang = ang + float(rng.uniform(-5, 5)) if r > 0 else ang
            w = _r2(w + float(rng.uniform(-0.5, 0.5)))
            d = _r2(d + float(rng.uniform(-0.5, 0.5)))
            cx, cz = _polaire(ang, r)
            if br:
                o = np.asarray(S["tronc2"][-1] if org == -2 else pts[org], float)
                fin = np.array([cx, y0 + h * 0.4, cz])
                coude = o + (fin - o) * 0.55 + np.array([0.0, 1.2, 0.0])
                A.tige([o, coude, fin], br, [e[k % 3], e[(k + 1) % 3]], (20 * k, 20 * k + 35), name="Branche",
                       collide=False, effile=0.75)
            A.lobe(cx, y0, cz, w, d, h, 45 * round(-ang / 45) + dyaw, pal, det)
        cols_r = (pal[1], pal[2], mix(pal[1], pal[2], 0.5), pal[0], mix(pal[2], pal[3], 0.5))
        for i, rm in enumerate(S["rameaux"]):
            if len(b.parts) - n0 >= 150 - len(S["petales"]) - 1:
                break
            im, ang, L = rm[:3]
            if len(rm) == 5:  # rideau en deux gradins qui prolonge le flanc du lobe
                A.brin(im, ang, L, rm[4], 0.6, A.V(cols_r[i % 3]), bas_min=8.1, L2=rm[3],
                       col2=A.V(mix(pal[2], pal[3], 0.3 + 0.35 * (i % 2))), bord=True)
            else:  # grappe trapue sous le bord
                A.brin(im, ang, L, 1.6, 1.3, A.V(cols_r[i % len(cols_r)]), bas_min=8.1)
        A.petales(S["petales"], (pal[3], pal[4], pal[2], pal[3]))
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Pins taillés en nuages (niwaki)
# ---------------------------------------------------------------------------
# plateaux : (départ de la branche ou None, (cx, y0, cz), w, d, h, yaw) ; y0 sur des familles distinctes.
PINS = [
    # 0 : droit — tronc en S, cinq plateaux étagés en alternance et un plateau sommital
    dict(tronc=[(0.0, 0, 0.0), (0.8, 4.0, 0.3), (-0.6, 8.0, -0.2), (0.4, 12.0, 0.3), (0.0, 14.2, 0.0)], w=1.6,
         plateaux=[((-0.4, 5.5, 0.0), (-3.4, 6.03125, -0.5), 5.5, 5, 1.5, 15),
                   ((0.6, 8.5, 0.0), (3.2, 8.59375, 0.6), 5.5, 4.5, 1.5, -20),
                   ((-0.3, 10.8, 0.0), (-2.8, 11.15625, 1.2), 5, 4.5, 1.5, 30),
                   ((0.3, 12.6, 0.0), (2.6, 12.71875, -1.2), 4.5, 4, 1.5, -10),
                   ((-0.2, 7.0, 0.1), (0.4, 7.28125, -3.4), 4.5, 4, 1.5, 5),
                   (None, (0.0, 14.0, 0.0), 5.5, 5.5, 2.0, 45)]),
    # 1 : penché (nagare) — tronc qui part d'un côté et s'incline fortement, plateaux en escalier
    dict(tronc=[(-3.6, 0, 0.0), (-2.4, 4.0, 0.2), (-0.4, 7.5, -0.3), (2.0, 9.8, 0.2), (3.8, 10.6, 0.0)], w=1.6,
         plateaux=[((-2.2, 4.6, 0.1), (-3.2, 7.03125, 2.0), 4.5, 4, 1.5, 20),
                   ((-0.2, 7.8, -0.2), (-0.6, 10.59375, -2.0), 5, 4.5, 1.5, -15),
                   ((2.2, 9.8, 0.1), (2.8, 9.65625, 2.6), 5, 4.5, 1.5, 10),
                   (None, (3.4, 11.21875, -0.6), 5, 4.5, 1.5, 35),
                   ((-1.2, 6.2, 0.0), (0.0, 13.3125, 0.6), 4.5, 4, 1.5, -30)]),
    # 2 : large (monkaburi) — tronc court et coudé, longue branche basse horizontale, couronne plate
    dict(tronc=[(0.0, 0, 0.0), (0.6, 3.5, 0.2), (-0.3, 7.0, -0.2), (0.2, 10.5, 0.1)], w=1.8,
         plateaux=[((0.2, 4.0, 0.0), (-3.6, 4.53125, 0.4), 4.5, 4.5, 1.5, 10),
                   ((-1.0, 4.4, 0.2), (-2.4, 5.84375, -3.0), 4, 3.5, 1.0, -20),
                   ((0.4, 7.0, 0.0), (3.4, 7.59375, -0.4), 5, 4.5, 1.5, -15),
                   (None, (0.0, 10.40625, 0.0), 7.5, 6.5, 2.0, 25),
                   ((-0.2, 8.8, 0.0), (-2.8, 9.15625, 2.6), 4.5, 4, 1.5, 40),
                   (None, (0.4, 12.96875, -0.2), 4, 3.5, 1.5, 10)]),
    # 3 : élancé — tronc haut et fin, trois étages de plateaux de plus en plus petits
    dict(tronc=[(0.0, 0, 0.0), (0.5, 6.0, 0.3), (-0.4, 11.5, -0.2), (0.2, 15.6, 0.2)], w=1.4,
         plateaux=[((0.3, 7.0, 0.1), (-3.2, 8.03125, 0.4), 5, 4.5, 1.5, 15),
                   ((0.2, 7.5, 0.0), (3.2, 8.40625, -0.6), 5, 4, 1.5, -25),
                   ((-0.3, 12.5, 0.0), (-2.6, 13.21875, 0.6), 4.5, 4, 1.5, 30),
                   ((-0.1, 13.0, 0.0), (2.6, 13.59375, -0.4), 4, 3.5, 1.5, -10),
                   ((0.0, 10.0, 0.0), (0.2, 10.65625, 2.8), 4, 3.5, 1.5, 60),
                   (None, (0.2, 15.40625, 0.2), 4.5, 4.5, 1.5, 45)]),
]


def pin(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Pin japonais taillé en nuages (niwaki), 12 à 18 × taille de haut dans 12 × 12 × taille : tronc brun-roux
    tordu, branches qui portent des plateaux d'aiguilles (dessous vert nuit, corps vert pin, dessus plus clair et
    studdé). 0 droit, 1 penché (nagare), 2 large à branche basse, 3 élancé. ≤ 40 pièces."""
    v = variant % len(PINS)
    S = PINS[v]
    n0 = len(b.parts)
    with b.group("Pin"):
        A = _Atelier(b, taille, boite=(6.0, 6.0))
        ecorce = [A.V(ECORCE_PIN, 0.04), A.V(shade(ECORCE_PIN, 0.88), 0.04)]
        A.tige(S["tronc"], S["w"], ecorce, (10, 35, 60, 85), name="Tronc")
        x0, _y, z0 = S["tronc"][0]
        A.racines([(30, 1.8, 1.2, 1.2), (160, 1.6, 1.0, 1.1), (270, 1.8, 1.1, 1.2)], shade(ECORCE_PIN, 0.82), x0, z0)
        aig, aig_cl, nuit = c("pin"), c("pin_clair"), c("feuille_nuit")
        for k, (dep, (cx, y0, cz), w, d, h, rot) in enumerate(S["plateaux"]):
            if dep is not None:  # branche du tronc au plateau (noyée dedans)
                A.tige([dep, (cx, y0 + h * 0.4, cz)], 0.6, ecorce[k % 2], (20 * k,), name="Branche", collide=False)
            for _ in range(20):
                if A.dedans(cx, cz, w, d, rot) and A.dedans(cx + 0.2, cz - 0.1, w - 1.0, d - 1.0, rot + 12):
                    break
                w, d = w - 0.5, d - 0.5
            A.bloc(cx - 0.1, y0 - 0.5, cz + 0.1, max(1.0, w - 1.6), 0.5, max(1.0, d - 1.4), A.V(nuit, 0.04), rot - 8,
                   studs="none", name="Aiguilles")
            A.bloc(cx, y0, cz, w, h, d, A.V(aig, 0.04), rot, name="Aiguilles")
            A.bloc(cx + 0.2, y0 + h, cz - 0.1, max(1.0, w - 2.0), 0.5, max(1.0, d - 1.8),
                   A.V(mix(aig, aig_cl, 0.7), 0.04), rot + 12, name="Aiguilles")
            if w >= 4.5 and len(b.parts) - n0 < 40 - 4 * (len(S["plateaux"]) - k - 1):  # petite touffe claire
                e = max(1.0, min(w, d) - 3.0)
                A.bloc(cx - 0.3, y0 + h + 0.5, cz + 0.2, e, 0.5, e,
                       A.V(mix(aig_cl, c("feuille_claire"), 0.4), 0.04), rot + 45, name="Aiguilles")
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Massifs d'arbres verts
# ---------------------------------------------------------------------------
# Cotes pour 28 × 20 ; arbres : (pied (x, z) ou None pour une haie, coudes du tronc [(dx, y, dz)...], largeur du
# tronc, lobes) ; le tronc finit dans le premier lobe. Lobes : (x, y0, z, w, d, h, detail, yaw, palette) en
# coordonnées du massif (palettes : 0 verts tendres, 1 verts sombres, 2 verts clairs).
MASSIFS = [
    # 0 : trois feuillus (un grand, un moyen, un petit) et deux haies basses qui les lient
    [((-6.5, 1.0), [(0.4, 5, -0.3)], 1.6,
      [(-6.0, 8.5, 1.0, 11, 10, 3.5, 3, 10, 0), (-6.5, 13.5, 1.6, 7, 6.5, 2.5, 3, 35, 0),
       (-1.5, 7.5, -2.5, 6, 5, 2.5, 1, -20, 2), (-10.0, 7.0, 4.0, 5.5, 5, 2.5, 1, 30, 1)]),
     ((6.0, 3.0), [(0.3, 4, 0.2)], 1.3,
      [(6.0, 7.0, 3.0, 9, 8, 3, 3, -15, 0), (9.5, 6.0, -1.0, 5.5, 5, 2, 1, 20, 1), (5.5, 10.5, 3.5, 5.5, 5, 2, 2, 25, 2)]),
     ((8.5, -5.0), [], 1.1,
      [(8.5, 5.0, -5.0, 7, 6, 2.5, 3, 30, 1)]),
     (None, None, 0, [(-1.0, 0.0, -6.0, 9, 3.5, 1.5, -1, 5, 1), (2.0, 0.0, 6.5, 8, 3, 1.0, -1, -8, 1),
                      (0.5, 9.5, 2.0, 6, 5, 2.5, 2, 15, 1), (2.0, 12.0, -1.5, 5, 4.5, 2, 1, -10, 2)])],
    # 1 : cinq feuillus en pyramide autour d'un grand arbre central
    [((0.0, 0.5), [(0.4, 6, 0.2)], 1.7,
      [(0.0, 10.0, 0.5, 11, 10, 3.5, 3, 0, 0), (0.6, 14.5, 0.0, 7, 6.5, 2.5, 3, 30, 2)]),
     ((-8.5, -3.0), [], 1.2,
      [(-8.5, 6.0, -3.0, 8, 7, 2.5, 3, 15, 1)]),
     ((8.0, -3.5), [], 1.2,
      [(8.0, 7.0, -3.5, 8, 7, 2.5, 3, -20, 0)]),
     ((-6.5, 5.5), [], 1.1,
      [(-6.5, 5.0, 5.5, 7, 6, 2.5, 2, 40, 1)]),
     ((7.0, 5.0), [], 1.1,
      [(7.0, 5.5, 5.0, 7, 6, 2.5, 2, -35, 2)]),
     (None, None, 0, [(0.0, 0.0, -6.5, 10, 3, 1.5, -1, 0, 1), (-4.0, 8.5, 1.0, 5.5, 5, 2.5, 2, 20, 1),
                      (4.0, 9.0, 1.0, 5.5, 5, 2.5, 2, -15, 0)])],
    # 2 : cinq arbres mêlés, dont deux sombres et serrés, un tendre au premier plan
    [((-7.5, 2.0), [(0.3, 5, 0.3)], 1.5,
      [(-7.5, 9.5, 2.0, 9, 8.5, 3.5, 3, 20, 1), (-7.2, 14.5, 2.2, 6, 5.5, 2.5, 2, 45, 1)]),
     ((0.5, 4.5), [(0.2, 5.5, 0.2)], 1.6,
      [(0.5, 11.0, 4.5, 10, 9, 3.5, 3, -10, 0), (1.0, 15.5, 4.2, 6.5, 6, 2.0, 2, 25, 2)]),
     ((8.0, 2.5), [], 1.3,
      [(8.0, 8.0, 2.5, 8.5, 8, 3, 3, 10, 1)]),
     ((-3.0, -5.0), [], 1.1,
      [(-3.0, 5.0, -5.0, 7, 6, 2.5, 3, 35, 0)]),
     ((4.5, -5.5), [], 1.0,
      [(4.5, 4.5, -5.5, 6, 5, 2, 2, -25, 2)]),
     (None, None, 0, [(-3.5, 10.5, 3.0, 5.5, 5, 2.5, 2, 10, 1), (4.5, 10.0, 3.5, 5.5, 5, 2.5, 1, -20, 0)])],
    # 3 : un grand arbre étalé, deux petits, haie et touffe basse
    [((-2.0, 1.5), [(0.6, 5.5, 0.2)], 1.9,
      [(-2.5, 10.0, 1.5, 13, 11, 3.5, 3, 5, 0), (-2.0, 14.5, 1.0, 8, 7.5, 2.5, 3, 30, 2),
       (5.0, 9.0, 3.0, 7, 6, 2.5, 2, -15, 0), (-9.0, 9.0, 0.0, 6, 5.5, 2.5, 1, 25, 1)]),
     ((9.0, -4.5), [], 1.1,
      [(9.0, 5.0, -4.5, 7, 6, 2.5, 3, 15, 1)]),
     ((-9.0, -5.0), [], 1.0,
      [(-9.0, 4.0, -5.0, 6, 5, 2, 2, -10, 2)]),
     (None, None, 0, [(1.5, 0.0, -6.5, 10, 3.5, 1.5, -1, 0, 1), (8.5, 0.0, 5.5, 5, 4, 2.0, 0, 20, 1)])],
]


def massif_arbres(b, variant: int = 0, largeur: float = 28, profondeur: float = 20) -> dict:
    """Bouquet de trois à cinq feuillus en masses vertes trapues (12 à 20 de haut), troncs visibles, entièrement
    dans largeur × profondeur : verts tendres et sombres en lobes étagés (dessous vert nuit, dessus clair
    studdé), haies basses entre les pieds. 0 trois arbres et haies, 1 pyramide de cinq, 2 cinq arbres mêlés,
    3 un grand arbre étalé et deux petits. ≤ 70 pièces."""
    v = variant % len(MASSIFS)
    n0 = len(b.parts)
    fx, fz = largeur / 28.0, profondeur / 20.0
    k = min(fx, fz)
    pals = (VERTS, VERTS_SOMBRES, (VERTS[1], VERTS[2], VERTS[3], VERTS[4], mix(VERTS[4], BLANC, 0.25)))
    with b.group("Massif"):
        A = _Atelier(b, 1.0, boite=(largeur / 2, profondeur / 2))
        e = [A.V(ECORCE_FEUILLU, 0.04), A.V(shade(ECORCE_FEUILLU, 0.85), 0.04)]
        for (pied, coudes, wt, lobes) in MASSIFS[v]:
            if pied is not None:
                x0, z0 = pied[0] * fx, pied[1] * fz
                lx, ly, lz, *_r, lh = lobes[0][:6]
                pts = [(x0, 0, z0)] + [(x0 + dx * k, y, z0 + dz * k) for (dx, y, dz) in coudes]
                pts.append((lx * fx, ly + 0.4 * lh, lz * fz))
                A.tige(pts, wt * max(0.85, k), e, (15, 50), name="Tronc")
                A.racines([(40, 1.4, 0.9, 1.0), (200, 1.3, 0.8, 0.9)], shade(ECORCE_FEUILLU, 0.8), x0, z0)
            for (x, y0, z, w, d, h, det, yaw, ip) in lobes:
                g = 1.0 if pied is None and y0 <= 0 else 1.3   # houppiers élargis : les couronnes se touchent
                A.lobe(x * fx, y0, z * fz, w * k * g, d * k * g, h, yaw, pals[ip], det)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Buissons taillés (karikomi) et azalées
# ---------------------------------------------------------------------------

def buisson(b, variant: int = 0) -> dict:
    """Buisson taillé (karikomi) dans 2,6 × 2,6, haut de 2,4 au plus : dôme en gradins droits et à 45°,
    dessous sombre, sommet clair studdé. 0 dôme, 1 coussin double, 2 azalée rose piquée de fleurs,
    3 azalée blanc-rose en plateau. ≤ 8 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    nuit, fonce, moyen, clair, pointe = VERTS

    def B(cx, y0, cz, sx, sy, sz, col, yaw=0.0, **kw):
        kw.setdefault("studs", "top")
        kw.setdefault("collide", False)
        kw.setdefault("name", "Feuillage")
        return b.boxc((cx, y0 + sy / 2, cz), (sx, sy, sz), vary(col, rng, 0.04), yaw=yaw, **kw)

    def fleur(x, y, z, col, s=0.55):
        b.boxc((x, y, z), (s, 0.3, s), vary(col, rng, 0.03), studs="top", collide=False, name="Fleur")

    with b.group("Buisson"):
        if v == 0:  # dôme bas : deux blocs croisés (contour octogonal), gradin à 45°, sommet clair
            B(0, 0, 0, 2.5, 1.0, 2.0, fonce)
            B(0, 0.125, 0, 2.0, 1.0, 2.5, mix(fonce, moyen, 0.35))
            B(0, 0.25, 0, 1.8, 1.25, 1.8, moyen, 45)
            B(0.1, 1.0, -0.1, 1.7, 0.625, 1.5, mix(moyen, clair, 0.5))
            B(0, 1.5, 0, 1.1, 0.375, 1.1, clair, 45)
            B(0.05, 1.75, 0, 0.6, 0.25, 0.6, pointe)
        elif v == 1:  # coussin double : un grand et un petit dôme accolés
            B(-0.3, 0, 0.25, 1.9, 1.125, 2.0, fonce)
            B(-0.25, 0.25, 0.25, 1.45, 1.25, 1.45, moyen, 45)
            B(-0.35, 1.125, 0.3, 1.3, 0.5, 1.2, clair)
            B(0.65, 0, -0.55, 1.2, 0.75, 1.4, mix(fonce, moyen, 0.4))
            B(0.6, 0.125, -0.55, 0.95, 0.875, 0.95, clair, 45)
            B(-0.4, 1.5, 0.3, 0.7, 0.25, 0.7, pointe, 45)
        elif v == 2:  # azalée rose : dôme bas piqué de fleurs
            B(0, 0, 0, 2.5, 1.0, 2.0, fonce)
            B(0, 0.125, 0, 2.0, 1.0, 2.5, mix(fonce, moyen, 0.35))
            B(0, 0.25, 0, 1.8, 1.25, 1.8, moyen, 45)
            az = c("azalee")
            for (x, y, z, col) in ((-1.0, 0.75, -0.55, az), (0.7, 1.32, -0.6, mix(az, SAK_CL, 0.4)),
                                   (0.35, 1.47, 0.35, az), (-0.45, 1.42, 0.1, mix(az, SAK_CL, 0.4)), (0.8, 0.8, 1.0, az)):
                fleur(x, y, z, col)
        else:  # azalée blanc-rose en plateau : coussin bas et large, fleurs pâles et roses
            B(0, 0, 0, 2.5, 1.0, 2.2, mix(fonce, moyen, 0.3))
            B(0.05, 0.125, 0, 1.75, 1.25, 1.75, moyen, 45)
            B(-0.1, 1.0, 0.1, 1.9, 0.5, 1.6, clair)
            for (x, y, z, col) in ((-0.85, 1.6, -0.35, SAK_PA), (0.6, 1.62, 0.45, c("azalee")), (0.15, 1.55, -0.55, SAK_PA),
                                   (-1.0, 0.65, 0.6, SAK_PA)):
                fleur(x, y, z, col, 0.55)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Rochers
# ---------------------------------------------------------------------------

def rocher(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Rocher décoratif de pierre pâle chaude (emprise 3 à 5 × taille, 3 × taille de haut au plus), plaque de
    mousse ou de lichen sur le dessus. 0 amas arrondi, 1 pierre dressée et deux petites, 2 dalles plates en
    gradins, 3 rocher bas et large couvert de lichen. ≤ 10 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    t = taille
    g0, g1, g2, g3 = ROCHE
    mousse, lichen = c("mousse"), c("lichen")

    def R(cx, y0, cz, sx, sy, sz, col, yaw, **kw):
        kw.setdefault("studs", "top")
        kw.setdefault("name", "Rocher")
        return b.boxc((cx * t, (y0 + sy / 2) * t, cz * t), (sx * t, sy * t, sz * t), vary(col, rng, 0.03), yaw=yaw, **kw)

    def M(cx, y0, cz, sx, sz, yaw, col=mousse):
        return R(cx, y0, cz, sx, 0.25, sz, col, yaw, collide=False, name="Mousse")

    with b.group("Rocher"):
        if v == 0:  # amas arrondi : bloc droit + bloc à 45°, chapeau, petite pierre
            R(0, 0, 0, 3.2, 1.75, 2.6, g1, 12)
            R(0.15, 0, -0.1, 2.6, 2.125, 2.6, g2, 57)
            R(-0.15, 2.125, 0.1, 1.8, 0.5, 1.6, g3, 25)
            M(-0.25, 2.625, 0.15, 1.2, 1.0, 25)
            R(1.6, 0, 0.85, 1.3, 0.875, 1.1, g1, -20)
            M(1.6, 0.875, 0.85, 0.7, 0.6, -20, lichen)
            R(-1.5, 0, -0.9, 0.9, 0.5, 0.8, g2, 35)
        elif v == 1:  # pierre dressée (tateishi) et deux pierres couchées
            R(0, 0, 0, 1.4, 2.625, 1.2, g1, 10)
            R(0.1, 0, -0.05, 1.1, 2.875, 1.3, g2, 55)
            R(0.05, 2.875, 0, 0.6, 0.125, 0.6, g3, 30)
            R(1.5, 0, 0.6, 1.4, 0.75, 1.2, g2, -25)
            R(-1.4, 0, -0.6, 1.2, 0.5, 1.0, g1, 40)
            M(1.5, 0.75, 0.6, 0.9, 0.7, -25)
            M(-0.25, 1.375, -0.55, 0.5, 0.6, 10, lichen)
        elif v == 2:  # dalles plates en gradins (pierre de seuil et pas)
            R(0, 0, 0, 2.6, 0.625, 2.0, g2, 8)
            R(0.3, 0.625, 0.2, 1.6, 0.5, 1.3, g3, 20)
            R(1.5, 0, -0.95, 1.4, 0.375, 1.2, g1, -25)
            R(-1.5, 0, 0.85, 1.3, 0.4375, 1.1, g2, 40)
            M(0.2, 1.125, 0.25, 0.8, 0.7, 20, lichen)
            M(-1.5, 0.4375, 0.85, 0.7, 0.5, 40)
        else:  # rocher bas et large couvert de lichen, une pierre au pied
            R(0, 0, 0, 4.0, 1.25, 3.0, g1, 15)
            R(0.1, 0, 0.05, 3.3, 1.625, 3.3, g2, 60)
            R(-0.3, 1.625, 0, 2.2, 0.5, 1.8, g3, 30)
            M(-0.4, 2.125, 0.1, 1.4, 1.0, 30, lichen)
            M(1.2, 1.25, -1.0, 1.0, 0.8, 15)
            R(1.85, 0, 1.25, 1.0, 0.625, 0.9, g2, -10)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Jardin d'étang au pont tambour rouge
# ---------------------------------------------------------------------------

def bassin_pont(b, variant: int = 0, largeur: float = 28, profondeur: float = 18) -> dict:
    """Jardin d'étang (largeur le long de X local, profondeur le long de Z, avant vers -Z) : berge de mousse,
    étang bordé de pierres (dessus à 0,6), eau à 0,3 sous le bord, nénuphars, pont tambour (taiko-bashi) laqué
    rouge en arc le long de Z (tablier en gradins jusqu'à 2,5, rampes rouges, pommeaux noirs), pas japonais,
    rochers, lanterne de pierre et touffes d'iris. 0 pont au centre, 1 pont décalé et étang en miroir. ≤ 80 pièces."""
    from . import mobilier

    v = variant % 2
    rng = b.rng
    n0 = len(b.parts)
    sg = 1 if v == 0 else -1          # miroir de la variante 1 (selon X)
    W, D = largeur / 2, profondeur / 2
    fx, fz = largeur / 28.0, profondeur / 18.0

    def X(x):
        return sg * x * fx

    def Z(z):
        return z * fz

    def blk(x0, y0, z0, x1, y1, z1, col, **kw):
        xa, xb = sorted((X(x0), X(x1)))
        za, zb = sorted((Z(z0), Z(z1)))
        return b.box((xa, y0, za), (xb, y1, zb), col, **kw)

    pierres = (c("pierre"), c("pierre_fonce"), c("pierre_claire"))
    with b.group("Bassin"):
        # berge de mousse sous tout le jardin
        blk(-13.5, 0, -8.5, 13.5, 0.1, 8.5, vary(mix(c("mousse"), c("herbe"), 0.4), rng, 0.02), studs="top", collide=False,
            name="Berge")
        # eau : trois rectangles jointifs (aucun recouvrement), dessus à 0,3
        eau = vary(mix(c("eau"), c("eau_fonce"), 0.3), rng, 0.02)
        for (x0, z0, x1, z1) in ((-9.5, -4.5, 9.5, 4.5), (-12.0, -2.0, -9.5, 3.0), (9.5, -3.5, 12.0, 1.5)):
            blk(x0, 0.1, z0, x1, 0.3, z1, eau, collide=False, name="Eau")
        # reflets et nénuphars (posés sur l'eau)
        for (x, z, sx, sz, col) in ((-6.5, 1.8, 2.5, 0.4, c("eau_claire")),
                                    (-4.0, -2.6, 1.3, 1.1, c("feuille_claire")), (6.8, 2.4, 1.1, 1.0, c("feuille")),
                                    (-10.6, 0.8, 1.0, 0.9, c("feuille_claire"))):
            blk(x - sx / 2, 0.3, z - sz / 2, x + sx / 2, 0.4, z + sz / 2, vary(col, rng, 0.02), studs="none",
                collide=False, name="Nenuphar" if col != c("eau_claire") else "Reflet")
        # deux carpes koï à fleur d'eau (orange et blanche tachée)
        for (x, z, yaw, col) in ((-5.2, 1.0, 25, c("terre_cuite")), (3.6, -1.6, -40, mix(c("blanc"), c("ocre_clair"), 0.25))):
            b.boxc((X(x), 0.29, Z(z)), (1.1, 0.14, 0.4), col, yaw=sg * yaw, collide=False, shadow=False, name="Koi")
        # bord de pierres : blocs irréguliers à cheval sur l'eau (dessus 0,55 à 0,7, petits angles)
        bords = [(-9.5, -5.3, -3.0, -4.2, 0.6), (-3.0, -5.4, 3.0, -4.3, 0.55), (3.0, -5.2, 9.8, -4.2, 0.65),
                 (-9.4, 4.2, -3.2, 5.3, 0.65), (-3.2, 4.3, 3.2, 5.4, 0.6), (3.2, 4.2, 9.6, 5.2, 0.55),
                 (-12.9, -2.6, -11.8, 3.6, 0.6), (-12.4, 2.9, -9.2, 4.0, 0.7), (-12.3, -3.0, -9.3, -1.9, 0.55),
                 (11.9, -4.1, 13.0, 2.1, 0.6), (9.4, -4.4, 12.6, -3.3, 0.7), (9.4, 1.4, 12.6, 2.4, 0.65)]
        for i, (x0, z0, x1, z1, h) in enumerate(bords):
            xa, xb = sorted((X(x0), X(x1)))
            za, zb = sorted((Z(z0), Z(z1)))
            b.boxc(((xa + xb) / 2, h / 2, (za + zb) / 2), (xb - xa, h, zb - za), vary(pierres[i % 3], rng, 0.03),
                   yaw=(3, -4, 2, -3, 4, -2)[i % 6], studs="top", name="Bord")
        # pont tambour le long de Z, centré en x = bx
        bx = 0.0 if v == 0 else -1.5
        L = 7.5 * fz

        def y_tab(z):
            return 0.6 + 1.9 * (1 - (z / L) ** 2)

        rouge, rouge_f, noir = c("laque_rouge"), c("laque_rouge_fonce"), c("laque_noire")
        xb0 = X(bx)
        with b.group("Pont"):
            # culées de pierre aux deux bouts
            for s in (-1, 1):
                b.box((xb0 - 2.3, 0, s * L - 0.9), (xb0 + 2.3, 0.75, s * L + 0.9), vary("pierre_fonce", rng, 0.03),
                      studs="top", name="Culee")
            # tablier en sept gradins de bois
            n = 7
            for k in range(n):
                za = -L + k * 2 * L / n
                zb = za + 2 * L / n
                top = round(y_tab((za + zb) / 2) * 16) / 16 + 0.03125
                b.box((xb0 - 1.5, max(0.3, top - 0.9), za), (xb0 + 1.5, top, zb), vary("bois_moyen", rng, 0.03),
                      studs="top", material="WoodPlanks", name="Tablier")
            # rives laquées en arc (quatre segments par côté)
            zs = [-L - 0.3, -L / 2, 0.0, L / 2, L + 0.3]
            for sx in (-1, 1):
                for k in range(4):
                    p0 = (xb0 + sx * 1.75, y_tab(max(-L, min(L, zs[k]))) - 0.25, zs[k])
                    p1 = (xb0 + sx * 1.75, y_tab(max(-L, min(L, zs[k + 1]))) - 0.25, zs[k + 1])
                    # axe presque selon Z : la largeur w est verticale, l'épaisseur d est selon X
                    _poutre(b, p0, p1, 0.9, 0.5 + 0.06 * (k % 2), rouge_f if k % 2 else rouge, 0, 0.2, 0.2, name="Rive")
            # poteaux (bouts et milieu), rampes et pommeaux noirs
            zp = (-L + 0.6, 0.0, L - 0.6)
            for sx in (-1, 1):
                x = xb0 + sx * 1.75
                tops = []
                for zz in zp:
                    y0 = y_tab(zz) - 0.4
                    yt = y_tab(zz) + 1.35
                    b.box((x - 0.2, y0, zz - 0.2), (x + 0.2, yt, zz + 0.2), rouge, name="Poteau")
                    b.box((x - 0.26, yt, zz - 0.26), (x + 0.26, yt + 0.35, zz + 0.26), noir, collide=False,
                          name="Pommeau")
                    tops.append((x, yt - 0.3, zz))
                for k in range(2):  # deux épaisseurs : pas de faces coplanaires sur le poteau du milieu
                    _poutre(b, tops[k], tops[k + 1], 0.3 + 0.06 * k, 0.3 + 0.06 * k, rouge, 0, 0.1, 0.1, name="Rampe")
        # pas japonais (dans l'extension de l'étang opposée au pont décalé)
        for i, (x, z, s, h) in enumerate(((-11.0, -1.2, 1.3, 0.45), (-10.2, 0.6, 1.2, 0.5), (-11.2, 2.2, 1.1, 0.45),
                                          (10.8, -2.6, 1.2, 0.5))):
            b.boxc((X(x), h / 2, Z(z)), (s, h, s * 0.9), vary(pierres[(i + 2) % 3], rng, 0.03),
                   yaw=15 * i, studs="top", name="Pas")
        # rochers de berge
        for (x, z, sx, sy, sz, yaw, col) in ((8.0, 6.6, 2.6, 1.5, 2.0, 20, ROCHE[2]), (8.3, 6.5, 1.8, 2.0, 1.6, 65, ROCHE[3]),
                                             (-6.0, -6.8, 2.2, 1.1, 1.6, -15, ROCHE[1]),
                                             (-11.8, 6.4, 1.8, 1.3, 1.6, 30, ROCHE[2])):
            b.boxc((X(x), sy / 2, Z(z)), (sx, sy, sz), vary(col, rng, 0.03), yaw=yaw, studs="top", name="Rocher")
        # lanterne de pierre sur la berge (côté du grand rocher)
        with b.at((X(11.0), 0, Z(6.2)), yaw=180 + 25 * sg, group="Lanterne"):
            mobilier.lanterne_pierre(b, 0 if v == 0 else 1)
        # touffes d'iris au bord de l'eau : feuilles en lames et fleurs bleu-violet
        iris = mix(c("bleu_clair"), c("sakura_vif"), 0.3)
        for (x, z) in ((-8.6, -4.0), (4.6, 4.0)):
            for k in range(3):
                a = math.radians(70 + 110 * k)
                h = 1.9 + 0.3 * k
                p0 = np.array([X(x), 0.2, Z(z)])
                p1 = p0 + np.array([0.35 * math.cos(a), h, 0.35 * math.sin(a)])
                _poutre(b, p0, p1, 0.35, 0.12, vary("vert_bambou_fonce" if k % 2 else "vert_bambou", rng, 0.04),
                        math.degrees(a), 0.0, 0.0, collide=False, shadow=False, name="Iris")
            b.boxc((X(x) + 0.05, 1.95, Z(z) + 0.05), (0.5, 0.4, 0.5), vary(iris, rng, 0.03), yaw=30, collide=False,
                   name="Fleur")
    return _infos(b, n0)


__all__ = ["cerisier", "cerisier_geant", "pin", "massif_arbres", "buisson", "rocher", "bassin_pont"]
