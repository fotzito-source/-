"""Végétation et terrain de la zone 7 (« la ville entre les murailles ») en style stud : arbres de la ville et de
la prairie, grand arbre feuillu de la prairie et sa butte fleurie, buissons, parterres de fleurs, meules de foin,
champs cultivés, canal (« petite Venise ») et ponts de pierre en arc.

Principes :
- feuillages en blocs empilés qui rétrécissent vers le haut, studs sur les dessus ; quatre tons par masse : dessous
  sombre (`feuille_ombre`, le volume se lit d'en bas), corps foncé, étage moyen ou clair, sommet ensoleillé
  (`feuille_jaune`) ; blocs droits et blocs tournés de 45° alternés : contours octogonaux, arrondis sous tous les
  angles. Les verts tirent vers le jaune (aucun vert émeraude) ;
- pas de faces coplanaires : les blocs qui se recouvrent diffèrent par leurs trois dimensions ou sont tournés ;
  les masses du grand arbre ont chacune leur « famille » de hauteurs (partie fractionnaire propre) ; les détails
  posés sur une face la dépassent d'au moins 0,1 ; les pièces au sol s'enfoncent un peu dans le sol ;
- rien ne flotte : feuillages portés par le tronc et les branches, fleurs et fruits à moitié noyés dans ce qui les
  porte, cordes accrochées aux branches ;
- troncs, branches maîtresses, pierres, quais, ponts et barques collisionnent ; feuillages, fleurs, brindilles,
  cordes, lierre et petits détails non (`collide=False`) ;
- cotes de conception données pour `taille = 1` (arbres), puis multipliées par `taille` sans réarrondi ;
- canal et ponts : repère de l'asset = repère du monde à une translation près (pas de rotation à la pose) ; le
  canal remplit exactement le trou laissé dans le sol par `zone.py` (x 55 → 75, z -404 → -268) et les ponts restent
  dans x ∈ [55, 79].

Propriété intellectuelle : rien que de la campagne et des jardins européens génériques (tilleul, chêne,
marronnier, pommier, blé, potager, foin, canal de ville alsacienne) ; aucun personnage, aucun épouvantail,
aucun texte, aucun emblème.
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, rot_y, rot_z, shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------


def _poutre(b, p0, p1, w, d, col, twist=0.0, ext0=0.0, ext1=0.0, **kw):
    """Bloc de section w × d dont l'axe Y local va de p0 à p1 (prolongé de ext0 / ext1 aux bouts), vrillé de
    `twist` degrés autour de son axe : troncs penchés, branches, rames."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    v = p1 - p0
    u = v / np.linalg.norm(v)
    ref = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    x = np.cross(u, ref)
    x /= np.linalg.norm(x)
    z = np.cross(x, u)
    R = np.column_stack([x, u, z]) @ rot_y(twist)
    a, e = p0 - u * ext0, p1 + u * ext1
    kw.setdefault("name", "Branche")
    return b.part("block", (w, float(np.linalg.norm(e - a)), d), (a + e) / 2, R, col, **kw)


def _corde(b, a, bb, r, col, **kw):
    """Cylindre fin de a à bb (l'axe d'un cylindre Roblox est son X local) : cordes, amarres."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    d = bb - a
    n = float(np.linalg.norm(d))
    x = d / n
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    kw.setdefault("name", "Corde")
    kw.setdefault("collide", False)
    kw.setdefault("shadow", False)
    return b.part("cyl", (n, 2 * r, 2 * r), (a + bb) / 2, np.column_stack([x, y, z]), col, **kw)


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
    return {"emprise": (round(float(hi[0] - lo[0]), 1), round(float(hi[2] - lo[2]), 1)),
            "hauteur": round(float(hi[1]), 2)}


class _K:
    """Cotes de conception (taille 1) multipliées par `t` : feuillages, bois, racines."""

    def __init__(self, b, t: float = 1.0):
        self.b = b
        self.t = float(t)
        self.rng = b.rng

    def p(self, *v):
        return tuple(float(x) * self.t for x in v)

    def bloc(self, cx, y0, cz, sx, sy, sz, col, yaw=0.0, **kw):
        """Bloc de feuillage donné par le centre de sa base, sa taille et sa rotation autour de Y."""
        kw.setdefault("studs", "top")
        kw.setdefault("collide", False)
        kw.setdefault("name", "Feuillage")
        return self.b.boxc(self.p(cx, y0 + sy / 2, cz), self.p(sx, sy, sz), col, yaw=yaw, **kw)

    def bois(self, cx, y0, cz, sx, sy, sz, col, yaw=0.0, **kw):
        """Bloc de bois (tronc) : centre de la base, taille, rotation ; collisionne."""
        kw.setdefault("name", "Tronc")
        return self.b.boxc(self.p(cx, y0 + sy / 2, cz), self.p(sx, sy, sz), col, yaw=yaw, **kw)

    def poutre(self, p0, p1, w, col, twist=0.0, ext0=0.0, ext1=0.0, **kw):
        return _poutre(self.b, self.p(*p0), self.p(*p1), w * self.t, w * self.t, col, twist, ext0 * self.t,
                       ext1 * self.t, **kw)

    def racine(self, ang, r0, long_, h, w, col, y0=-0.3):
        """Racine en coin rayonnant : part du tronc (rayon r0) et descend vers l'extérieur."""
        with self.b.at((0, 0, 0), yaw=ang):
            self.b.wedge(self.p(-w / 2, y0, r0), self.p(w / 2, h, r0 + long_), col, down="+z", name="Racine")

    def point(self, cx, cy, cz, s, col, **kw):
        """Petit cube (fleur, fruit) centré en (cx, cy, cz)."""
        kw.setdefault("collide", False)
        kw.setdefault("name", "Fleur")
        return self.b.boxc(self.p(cx, cy, cz), self.p(s, s, s), col, **kw)


def _tons(rng):
    """Tons de feuillage d'un arbre (dessous, foncé, moyen, clair, soleil), légèrement variés."""
    return (vary("feuille_ombre", rng, 0.03), vary("feuille_fonce", rng, 0.03), vary("feuille", rng, 0.03),
            vary("feuille_claire", rng, 0.03), vary("feuille_jaune", rng, 0.03))


# ---------------------------------------------------------------------------
# Arbres de la ville et de la prairie
# ---------------------------------------------------------------------------

def arbre(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Arbre feuillu de stud (≈ 14 studs de haut et 11-12 de large à taille 1 ; tout le houppier tient dans un
    cercle de rayon 6 × taille autour du tronc) : 0 tilleul (houppier rond et dense, un peu ovoïde), 1 chêne (large
    et irrégulier, trois bouquets sur des branches basses), 2 marronnier (dôme haut, chandelles de fleurs blanches),
    3 pommier (petit et rond, tronc penché, pommes rouges, deux pommes tombées). Houppiers en croix de deux blocs
    plus un bloc à 45° (contour presque rond), étages plus clairs, sommet ensoleillé. ≤ 26 pièces."""
    v = variant % 4
    rng = b.rng
    k = _K(b, taille)
    n0 = len(b.parts)
    ombre, fonce, moyen, clair, soleil = _tons(rng)
    tr = vary(mix(c("tronc"), c("tronc_clair"), 0.4), rng, 0.03)
    tr2 = vary(c("tronc"), rng, 0.03)
    rac = shade(tr, 0.9)
    with b.group("Arbre"):
        if v == 0:  # tilleul : rond et dense, légèrement ovoïde, épaules en bouffées
            k.bois(0, -0.3, 0, 2, 8.3, 2, tr)
            k.bois(0, -0.2, 0, 2.2, 6.0, 2.2, tr2, yaw=45, name="Ecorce")
            for ang, L, h in ((20, 2.0, 1.4), (140, 1.8, 1.2), (255, 2.1, 1.5)):
                k.racine(ang, 0.7, L, h, 1.1, rac)
            k.poutre((0, 5.0, 0), (-2.7, 7.6, 0.9), 0.8, tr, 20, collide=False)
            k.poutre((0, 5.6, 0), (2.5, 8.0, -1.3), 0.7, tr, 55, collide=False)
            k.bloc(0, 6.25, 0, 5.6, 1.0, 5.6, ombre, studs="none", name="Dessous")
            k.bloc(0, 7.0, 0, 10.3, 3.0, 6.0, mix(fonce, ombre, 0.3))
            k.bloc(0, 7.25, 0, 6.25, 3.5, 10.2, fonce)
            k.bloc(0, 7.5, 0, 8.25, 4.0, 8.25, mix(fonce, moyen, 0.45), 45)
            for i, ang in enumerate((25, 115, 205, 295)):
                a = math.radians(ang)
                y0, h = ((10.1, 2.5), (9.85, 2.0), (10.35, 2.75), (9.6, 2.25))[i]
                k.bloc(math.sin(a) * 3.3, y0, math.cos(a) * 3.3, 3.4, h, 3.4, (moyen, mix(moyen, clair, 0.5))[i % 2], ang)
            k.bloc(0, 11.25, 0, 5.5, 2.5, 5.5, mix(moyen, clair, 0.25))
            k.bloc(0.25, 12.5, -0.25, 4.25, 2.0, 4.25, clair, 45)
            k.bloc(-0.25, 14.0, 0.25, 2.5, 1.0, 2.5, soleil)
            for ang, y in ((25, 12.6), (205, 13.1)):
                a = math.radians(ang)
                k.bloc(math.sin(a) * 4.0, y - 0.15, math.cos(a) * 4.0, 1.4, 0.5, 1.4, soleil, ang + 45, name="Soleil")
            k.bloc(-3.2, 5.6, -2.2, 1.6, 1.9, 1.6, fonce, 30, studs="none")
            k.bloc(2.3, 5.75, 2.6, 1.6, 1.85, 1.3, ombre, -10, studs="none")
        elif v == 1:  # chêne : large, irrégulier, branches basses et trois bouquets
            k.bois(0, -0.3, 0, 2.4, 5.8, 2.4, tr)
            k.bois(0, -0.2, 0, 2.5, 4.4, 2.5, tr2, yaw=45, name="Ecorce")
            for ang, L, h in ((30, 2.2, 1.5), (150, 2.0, 1.3), (265, 2.4, 1.6)):
                k.racine(ang, 0.8, L, h, 1.3, rac)
            k.poutre((0, 4.3, 0), (-3.2, 7.4, 1.2), 1.1, tr, 15)
            k.poutre((0, 4.6, 0), (2.9, 6.9, -1.4), 1.0, tr, 40)
            k.poutre((0, 5.0, 0), (0.6, 9.4, 0.4), 1.2, tr, 70)
            k.poutre((0, 3.5, 0), (-2.5, 4.9, -2.5), 0.6, tr, 10, collide=False)
            k.bloc(-2.8, 4.45, -2.8, 2.2, 1.5, 2.2, fonce, 15)
            k.bloc(-2.9, 5.95, -2.95, 1.2, 0.45, 1.2, clair, 40, name="Soleil")
            k.bloc(0.3, 5.9, -0.2, 6.5, 1.0, 4.0, ombre, 8, studs="none", name="Dessous")
            k.bloc(-2.5, 6.75, 1.0, 4.5, 3.0, 4.5, fonce, 10)
            k.bloc(-2.9, 7.0, 0.6, 5.0, 2.25, 3.0, mix(fonce, moyen, 0.4), 35)
            k.bloc(-2.4, 9.5, 0.9, 3.0, 1.5, 3.0, clair, 40)
            k.bloc(2.5, 6.25, -1.2, 4.5, 2.75, 4.5, fonce, -12)
            k.bloc(2.9, 6.5, -0.9, 4.8, 2.0, 3.0, mix(fonce, moyen, 0.4), 20)
            k.bloc(2.4, 8.75, -1.1, 3.2, 1.4, 2.8, moyen, 25)
            k.bloc(2.6, 10.05, -0.9, 1.5, 0.5, 1.5, soleil, 25, name="Soleil")
            k.bloc(0.4, 8.5, 0.2, 6.5, 3.0, 6.0, moyen)
            k.bloc(0.4, 9.0, 0.4, 5.5, 3.25, 5.5, mix(moyen, clair, 0.4), 45)
            k.bloc(0.2, 11.75, 0, 3.5, 1.25, 3.5, soleil)
            k.bloc(-1.6, 12.15, 1.4, 1.3, 0.6, 1.3, mix(clair, soleil, 0.5), 20, name="Soleil")
            k.bloc(-4.3, 5.75, 0.6, 1.4, 1.6, 1.4, ombre, 30, studs="none")
            k.bloc(3.8, 5.35, -3.0, 1.3, 1.5, 1.3, fonce, -15, studs="none")
        elif v == 2:  # marronnier : dôme haut et sombre, chandelles de fleurs blanches
            k.bois(0, -0.3, 0, 2, 7.3, 2, tr)
            k.bois(0, -0.2, 0, 2.2, 5.0, 2.2, tr2, yaw=45, name="Ecorce")
            for ang, L, h in ((50, 1.9, 1.3), (170, 2.0, 1.4), (290, 1.8, 1.2)):
                k.racine(ang, 0.7, L, h, 1.1, rac)
            k.poutre((0, 4.6, 0), (-2.8, 6.9, -0.8), 0.7, tr, 30, collide=False)
            k.poutre((0, 5.0, 0), (2.4, 7.2, 1.5), 0.7, tr, 65, collide=False)
            fo = shade(fonce, 0.94)
            k.bloc(0, 5.5, 0, 5.6, 1.0, 5.6, ombre, studs="none", name="Dessous")
            k.bloc(0, 6.25, 0, 10.0, 3.5, 6.4, mix(fo, ombre, 0.3))
            k.bloc(0, 6.5, 0, 6.6, 4.0, 9.8, fo)
            k.bloc(0, 6.75, 0, 8.2, 4.75, 8.2, mix(fo, moyen, 0.4), 45)
            puffs = ((40, 9.6, 3.0), (160, 10.1, 2.75), (280, 9.85, 2.5))
            for i, (ang, y0, h) in enumerate(puffs):
                a = math.radians(ang)
                k.bloc(math.sin(a) * 3.2, y0, math.cos(a) * 3.2, 3.6, h, 3.6, (mix(fo, moyen, 0.7), moyen)[i % 2], ang)
            k.bloc(0, 11.25, 0, 6.0, 2.75, 6.0, moyen, 45)
            k.bloc(-0.25, 13.5, 0.25, 4.0, 1.5, 3.5, mix(moyen, clair, 0.5))
            k.bloc(0, 14.75, 0, 2.0, 0.75, 2.0, soleil, 45)
            fl = (c("fleur_blanche"), mix(c("fleur_blanche"), c("fleur_rose"), 0.35))
            # chandelles : dressées sur les dessus découverts, à moitié noyées dans le bloc qui les porte
            cand = [(math.sin(math.radians(a_)) * 3.4, y0 + h, math.cos(math.radians(a_)) * 3.4) for (a_, y0, h) in puffs]
            cand += [(4.55, 9.75, 1.8), (-4.55, 9.75, -1.6), (1.6, 10.5, 4.45), (-1.7, 10.5, -4.45), (1.2, 15.0, -1.6)]
            for i, (x, y, z) in enumerate(cand):
                k.b.boxc(k.p(x, y + 0.3, z), k.p(0.8, 1.6, 0.8), fl[i % 2], collide=False, name="Fleur")
        else:  # pommier : petit, rond, tronc penché, pommes
            k.poutre((0, -0.3, 0), (0.9, 4.2, 0.3), 1.6, tr, 10, ext0=0.5, name="Tronc")
            k.poutre((0.9, 4.0, 0.3), (0.5, 5.8, 0.1), 1.4, tr2, 35, name="Tronc")
            for ang, L, h in ((70, 1.6, 1.0), (230, 1.8, 1.1)):
                k.racine(ang, 0.6, L, h, 1.0, rac)
            k.poutre((0.8, 4.0, 0.3), (-2.0, 5.6, 1.2), 0.7, tr, 20, collide=False)
            k.poutre((0.9, 4.0, 0.3), (3.0, 5.4, -1.0), 0.7, tr, 50, collide=False)
            cx, cz = 0.6, 0.2
            k.bloc(cx, 4.75, cz, 6.0, 0.75, 6.0, ombre, studs="none", name="Dessous")
            k.bloc(cx, 5.25, cz, 9.0, 2.5, 5.6, moyen)
            k.bloc(cx, 5.4, cz, 5.8, 2.75, 8.6, mix(moyen, fonce, 0.3))
            k.bloc(cx, 5.5, cz, 7.5, 3.0, 7.5, mix(moyen, clair, 0.3), 45)
            k.bloc(cx - 0.25, 8.0, cz + 0.25, 6.0, 2.0, 5.5, clair)
            k.bloc(cx, 9.5, cz, 3.0, 1.0, 3.0, soleil, 45)
            pom = (c("pomme"), shade(c("pomme"), 1.12))
            for i, (x, y, z) in enumerate(((5.1, 6.3, 1.6), (-3.9, 6.7, -1.2), (2.0, 6.4, -4.1), (-1.2, 7.0, 4.5),
                                           (3.6, 8.0, -1.0), (-1.9, 9.1, 1.8), (0.9, 4.45, 3.4), (-2.6, 4.55, -1.6))):
                k.point(x, y, z, 0.65, pom[i % 2], name="Pomme")
            k.point(2.6, 0.25, 2.2, 0.6, pom[0], name="Pomme")
            k.point(-1.9, 0.25, 2.8, 0.6, pom[1], name="Pomme")
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Grand arbre de la prairie et sa butte
# ---------------------------------------------------------------------------

def _masse(k, cx, y0, cz, w, d, h, rot, tons, sommet=True):
    """Masse de feuillage en nuage de blocs : dessous sombre en retrait, corps droit, corps tourné de 45° (contour
    octogonal), étage plus clair décalé, sommet ensoleillé. Toutes les cotes internes sont y0 + multiples du
    quart de stud : deux masses dont les y0 n'ont pas la même partie fractionnaire (modulo 0,25) n'ont jamais de
    faces horizontales au même niveau. Renvoie le haut."""
    dessous, corps, corps45, etage, haut = tons
    k.bloc(cx, y0 - 1.0, cz, w - 4.5, 1.5, d - 4.5, dessous, rot, studs="none", name="Dessous")
    k.bloc(cx, y0, cz, w, h, d, corps, rot)
    s = round(min(w, d) * 0.8 * 2) / 2
    k.bloc(cx + 0.25, y0 + 0.5, cz - 0.25, s, h + 0.75, s, corps45, rot + 45)
    he = max(2.0, round(h * 0.5 * 4) / 4)
    ox, oz = _tourne(-w * 0.08, d * 0.07, rot)
    k.bloc(cx + ox, y0 + h - 0.25, cz + oz, round(w * 0.62 * 2) / 2, he, round(d * 0.6 * 2) / 2, etage, rot + 9)
    top = y0 + h - 0.25 + he
    if sommet:
        e = round(min(w, d) * 0.36 * 2) / 2
        ox, oz = _tourne(w * 0.06, -d * 0.05, rot)
        k.bloc(cx + ox, top - 0.5, cz + oz, e, 1.75, e, haut, rot + 45)
        top += 1.25
    return top


def _degrade(rng, niveau):
    """Tons d'une masse selon son étage (0 jupe basse, 1 couronne, 2 sommet) : du sombre en bas au clair en haut."""
    ombre, fonce, moyen, clair, soleil = _tons(rng)
    if niveau == 0:
        return (ombre, mix(fonce, ombre, 0.25), fonce, mix(fonce, moyen, 0.6), moyen)
    if niveau == 1:
        return (ombre, mix(fonce, moyen, 0.35), mix(fonce, moyen, 0.75), mix(moyen, clair, 0.5), clair)
    return (ombre, moyen, mix(moyen, clair, 0.5), clair, mix(clair, soleil, 0.55))


def _tourne(lx, lz, yaw):
    """Vecteur (lx, lz) d'un repère tourné de `yaw` autour de Y, exprimé dans le repère parent (comme kit.rot_y)."""
    a = math.radians(yaw)
    return math.cos(a) * lx + math.sin(a) * lz, -math.sin(a) * lx + math.cos(a) * lz


def _rayon_masse(w, d, rot):
    """Rayon horizontal maximal d'une masse (corps droit, corps à 45°) autour de son centre."""
    return max(math.hypot(w / 2, d / 2), min(w, d) * 0.8 / math.sqrt(2) + 0.36)


# Grand arbre : tronc, branches et trois étages de masses (jupe basse, couronne moyenne, sommet).
#   anneaux : (rayon, y0 de base, largeur, profondeur, hauteur, angles) ; les y0 sont ensuite décalés d'une
#   « famille » (multiple de 1/32 de stud) choisie pour que deux masses qui se touchent n'en partagent pas.
#   basse : (angle, rayon, y0) de la branche basse à balançoire. À 340°, une fois l'arbre posé avec yaw 25, elle
#   pointe vers l'entrée (+Z du monde) : vue du couloir, la balançoire se présente de profil (deux cordes, planche).
GEANTS = [
    # 0 : chêne — dôme large et bas, jupe de six masses, branches maîtresses bien visibles
    dict(tronc=15.0, anneaux=[(12.5, 18.0, 11.0, 10.0, 5.0, (30, 82, 134, 186, 238, 290)),
                              (9.0, 25.0, 13.0, 12.0, 6.0, (8, 80, 152, 224, 296)),
                              (0.0, 34.5, 20.0, 19.0, 6.0, (0,))],
         basse=(340, 14.0, 11.5)),
    # 1 : tilleul — plus haut et ovoïde, jupe plus étroite
    dict(tronc=17.0, anneaux=[(10.5, 20.0, 10.5, 10.0, 5.5, (16, 88, 160, 232, 304)),
                              (6.0, 27.0, 12.5, 12.0, 6.5, (52, 142, 232, 322)),
                              (0.0, 35.5, 14.5, 14.0, 6.0, (0,)), (0.0, 41.5, 9.0, 8.5, 2.5, (0,))],
         basse=(340, 13.5, 12.5)),
]


def arbre_geant(b, variant: int = 0) -> dict:
    """Grand arbre feuillu de la prairie (≈ 46 studs de haut, houppier en dôme de 40 studs, tout dans un rayon de 20
    autour du tronc), sur sa butte : tronc 4 × 4 octogonal à deux tons d'écorce et pied évasé, contreforts de racines,
    branches maîtresses qui s'écartent sous le feuillage, longue branche basse qui porte une balançoire de corde ;
    houppier en trois étages de masses (jupe basse, couronne, sommet), quatre tons et reflets de soleil, bouquets
    pendants sous la jupe. 0 chêne, 1 tilleul, 2 chêne avec un banc et des fleurs au pied. Chêne ou tilleul
    ordinaire (aucune silhouette d'arbre de forêt « géante »). ≤ 200 pièces."""
    v = variant % 3
    P = GEANTS[1 if v == 1 else 0]
    rng = b.rng
    k = _K(b, 1.0)
    n0 = len(b.parts)
    tr = mix(c("tronc"), c("tronc_clair"), 0.3)
    ecorce = (vary(tr, rng, 0.03), vary(mix(c("tronc"), c("tronc_fonce"), 0.4), rng, 0.03),
              vary(mix(c("tronc"), c("tronc_clair"), 0.6), rng, 0.03))
    racine = shade(tr, 0.92)
    H = P["tronc"]

    # masses : centre, y0 (avec famille), taille, rotation
    masses = []
    for (R, y0, w, d, h, angles) in P["anneaux"]:
        for j, ang in enumerate(angles):
            a = math.radians(ang)
            masses.append(dict(x=math.sin(a) * R, z=math.cos(a) * R, y0=y0 + 0.75 * (j % 3) * (R > 0), w=w, d=d, h=h,
                               rot=(ang * 0.37 + 11 * len(masses)) % 90 - 45, R=R, ang=ang))
    ang_b, R_b, y_b = P["basse"]
    a = math.radians(ang_b)
    masses.append(dict(x=math.sin(a) * R_b, z=math.cos(a) * R_b, y0=y_b, w=7.5, d=6.5, h=3.0, rot=17.0, R=R_b,
                       ang=ang_b, basse=True))
    familles = []
    for m in masses:  # coloration gloutonne : deux masses qui se touchent n'ont pas la même famille de hauteurs
        r = _rayon_masse(m["w"], m["d"], m["rot"])
        prises = {f for (x, z, rr, y0, y1, f) in familles
                  if math.hypot(m["x"] - x, m["z"] - z) < r + rr + 0.5 and y0 < m["y0"] + m["h"] + 6 and m["y0"] - 2 < y1}
        f = next(kk / 32 for kk in (0, 3, 6, 1, 4, 7, 2, 5) if kk / 32 not in prises)
        m["y0"] += f
        familles.append((m["x"], m["z"], r, m["y0"] - 2, m["y0"] + m["h"] + 6, f))

    with b.group("ArbreGeant"):
        with b.group("Tronc"):
            k.bois(0, -0.6, 0, 4.0, H + 4.6, 4.0, ecorce[0])
            k.bois(0, -0.5, 0, 4.4, H - 1.5, 4.4, ecorce[1], yaw=45, name="Ecorce")
            k.bois(0, -0.4, 0, 5.8, 3.4, 5.8, ecorce[2], yaw=20, name="Pied")
            k.bois(0, -0.45, 0, 5.2, 5.1, 5.2, ecorce[1], yaw=65, name="Pied")
            # stries d'écorce (reliefs verticaux) et un nœud
            k.bois(2.05, 4.5, -0.6, 0.3, H - 6.0, 0.9, shade(tr, 0.8), name="Ecorce", collide=False)
            k.bois(-0.4, 5.5, -2.05, 1.0, H - 7.0, 0.3, shade(tr, 0.8), name="Ecorce", collide=False)
            k.bois(-1.0, 6.5, 2.1, 1.2, 1.3, 0.4, c("tronc_fonce"), name="Noeud", collide=False)
        with b.group("Racines"):
            for (ang, L, h, w) in ((15, 4.5, 4.0, 1.8), (75, 3.6, 3.2, 1.6), (135, 4.8, 4.4, 2.0), (195, 3.8, 3.4, 1.6),
                                   (250, 4.4, 4.0, 1.8), (310, 3.4, 3.0, 1.5)):
                a = ang + float(rng.uniform(-6, 6))
                k.racine(a, 1.8, L, h, w, vary(racine, rng, 0.03), y0=-0.6)
                k.racine(a + 24, 2.6, L * 0.55, h * 0.4, w * 0.6, shade(racine, 0.92), y0=-0.6)
        with b.group("Branches"):
            # branches maîtresses : du haut du tronc vers chaque masse de la jupe et de la couronne
            for i, m in enumerate(masses):
                if m.get("basse") or m["R"] <= 0:
                    continue
                dx, dz = math.sin(math.radians(m["ang"])), math.cos(math.radians(m["ang"]))
                y_dep = H - 2.0 + (i % 3) * 1.5
                frac = 0.62 if m["R"] > 10 else 0.5
                bout = (dx * m["R"] * frac, m["y0"] + 0.6, dz * m["R"] * frac)
                w = 2.0 if m["R"] > 10 else 1.7
                k.poutre((0, y_dep, 0), bout, w, ecorce[0] if i % 2 else ecorce[2], m["ang"] * 0.3, ext0=0.6)
            # fût central jusqu'au sommet
            top = [m for m in masses if m["R"] == 0][0]
            k.poutre((0, H + 2.0, 0), (0.6, top["y0"] + 0.5, -0.4), 2.6, ecorce[2], 15)
            # branche basse (balançoire) : longue, presque horizontale, dans le vide laissé par la jupe
            mb = masses[-1]
            dx, dz = math.sin(math.radians(mb["ang"])), math.cos(math.radians(mb["ang"]))
            pb0 = np.array([dx * 1.2, H - 4.5, dz * 1.2])
            pb1 = np.array([dx * (mb["R"] - 1.5), mb["y0"] + 0.7, dz * (mb["R"] - 1.5)])
            k.poutre(tuple(pb0), tuple(pb1), 1.7, ecorce[0], 5, ext0=0.5)
        with b.group("Feuillage"):
            for m in masses:
                niveau = 0 if (m["R"] > 10 or m.get("basse")) else (1 if m["R"] > 0 else 2)
                m["haut"] = _masse(k, m["x"], m["y0"], m["z"], m["w"], m["d"], m["h"], m["rot"], _degrade(rng, niveau),
                                   sommet=not m.get("basse"))
            # bouffées d'épaule autour du sommet : un dessus en nuage, pas en pièce montée
            sommet_m = [m for m in masses if m["R"] == 0][0]
            for i in range(5):
                a = math.radians(i * 72 + 18)
                rr = 6.6 + 0.6 * (i % 2)
                y0 = sommet_m["y0"] + sommet_m["h"] - 1.0 + (0.40625, 0.78125, 0.15625, 1.03125, 0.53125)[i]
                hh = (2.5, 2.0, 2.75, 1.75, 2.25)[i]
                col = vary(mix(c("feuille_claire"), c("feuille_jaune"), (0.15, 0.45, 0.3, 0.55, 0.2)[i]), rng, 0.03)
                k.bloc(math.sin(a) * rr, y0, math.cos(a) * rr, 5.0 - 0.5 * (i % 2), hh, 4.5, col, i * 72 + 18 + 7,
                       name="Bouffee")
            # bouquets pendants sous le bord de la jupe (le haut noyé dans la masse)
            jupe = [m for m in masses if m["R"] > 10 and not m.get("basse")]
            for i, m in enumerate(jupe):
                a = math.radians(m["ang"] + 12)
                rr = m["R"] + 1.5
                hh = (3.25, 2.5, 3.75)[i % 3]
                k.bloc(math.sin(a) * rr, m["y0"] - hh + 0.5, math.cos(a) * rr, 2.0, hh, 2.0,
                       vary("feuille_fonce", rng, 0.04), m["rot"] + 30, studs="none", name="Pendant")
            # reflets de soleil sur le bord découvert du dessus des corps (hors de l'étage, côté extérieur)
            for i, m in enumerate(masses):
                if m.get("basse"):
                    continue
                if m["R"] > 0:
                    a = math.radians(m["ang"] + (-30 if i % 2 else 30))
                    ox, oz = m["x"] + math.sin(a) * 3.6, m["z"] + math.cos(a) * 3.6
                    sz = (2.2, 0.5, 1.6)
                else:
                    ox, oz = _tourne(-6.5, 5.0, m["rot"])
                    ox, oz = m["x"] + ox, m["z"] + oz
                    sz = (3.0, 0.5, 2.4)
                k.bloc(ox, m["y0"] + m["h"] - 0.14, oz, sz[0], sz[1], sz[2],
                       vary(mix(c("feuille_jaune"), c("feuille_claire"), 0.3 * (i % 2)), rng, 0.04), m["rot"] + 20,
                       name="Soleil")
        with b.group("Balancoire"):
            qa = pb0 + (pb1 - pb0) * 0.56
            qb = pb0 + (pb1 - pb0) * 0.72
            for q in (qa, qb):
                _corde(b, (q[0], 2.3, q[2]), (q[0], q[1], q[2]), 0.12, c("corde"))
            mid = (qa + qb) / 2
            Lp = float(np.linalg.norm((qb - qa)[[0, 2]])) + 0.8
            b.boxc((mid[0], 2.15, mid[2]), (0.9, 0.3, Lp), c("bois_clair"), yaw=float(math.degrees(math.atan2(dx, dz))),
                   collide=False, name="Planche")
        if v == 2:
            with b.group("Pied"):
                # petit banc de bois tourné vers le couloir et couronne de fleurs entre les racines
                a = math.radians(ang_b + 40)
                with b.at((math.sin(a) * 7.0, 0, math.cos(a) * 7.0), yaw=ang_b + 40):
                    for x in (-1.6, 1.6):
                        b.box((x - 0.25, -0.3, -0.6), (x + 0.25, 1.4, 0.6), c("bois"), name="Pied")
                    b.box((-2.2, 1.4, -0.75), (2.2, 1.7, 0.75), c("bois_clair"), studs="top", name="Assise")
                    b.box((-2.2, 2.0, -0.8), (2.2, 2.8, -0.55), c("bois_clair"), name="Dossier")
                    b.box((-2.0, 1.7, -0.75), (-1.6, 2.0, -0.6), c("bois"), name="Montant")
                    b.box((1.6, 1.7, -0.75), (2.0, 2.0, -0.6), c("bois"), name="Montant")
                fl = ("fleur_blanche", "fleur_jaune", "fleur_bleue", "fleur_mauve", "fleur_rouge")
                for i in range(14):
                    a = math.radians(i * 360 / 14 + 9)
                    rr = 4.2 + (i % 3) * 0.9
                    b.box((math.sin(a) * rr - 0.45, -0.1, math.cos(a) * rr - 0.45),
                          (math.sin(a) * rr + 0.45, 0.25 + 0.15 * (i % 2), math.cos(a) * rr + 0.45),
                          c(fl[i % 5]), collide=False, name="Fleur")
    return _infos(b, n0)


def colline(b, variant: int = 0, largeur: float = 48, profondeur: float = 30, hauteur: float = 4) -> dict:
    """Butte herbeuse en gradins (3 étages de deux blocs croisés : coins arrondis en escalier), semée de pixels de
    fleurs blanches, jaunes, bleues et mauves, deux ou trois pierres et un petit sentier de terre côté couloir
    (-X). Renvoie la hauteur du plateau du sommet (où pousse le grand arbre). ≤ 40 pièces."""
    rng = b.rng
    n0 = len(b.parts)
    sx, sz, sy = largeur / 48.0, profondeur / 30.0, hauteur / 4.0
    # étages : (demi-largeur, demi-profondeur, haut) en cotes de conception (48 × 30 × 4)
    etages = [
        ((24, 10, 1.25), (19, 15, 1.5)),
        ((17, 8.5, 2.75), (13.5, 11.5, 3.0)),
        ((12.5, 7.0, 4.0), (9.5, 9.5, 3.75)),
    ]
    tons = (("herbe", "herbe_claire"), ("herbe_claire", "herbe"), ("herbe", "herbe_claire"))
    blocs = []
    with b.group("Colline"):
        for i, (a, bb) in enumerate(etages):
            for j, (hx, hz, top) in enumerate((a, bb)):
                y_bas = -0.5 + 0.1 * i
                col = vary(tons[i][j], rng, 0.025)
                b.box((-hx * sx, y_bas, -hz * sz), (hx * sx, top * sy, hz * sz), col, studs="top", name="Butte")
                blocs.append((hx * sx, hz * sz, top * sy))

        def dessus(x, z):
            hs = [t for (hx, hz, t) in blocs if abs(x) < hx and abs(z) < hz]
            return max(hs) if hs else None

        # pixels de fleurs : sur un seul niveau (les 4 coins du pixel au même étage)
        fleurs = ("fleur_blanche", "fleur_jaune", "fleur_blanche", "fleur_bleue", "fleur_jaune", "fleur_mauve")
        n_fl, essais = 0, 0
        prises = []
        while n_fl < 25 and essais < 3000:
            essais += 1
            x = float(rng.uniform(-23, 23)) * sx
            z = float(rng.uniform(-14.5, 14.5)) * sz
            if abs(x) < 6.5 * sx and abs(z) < 6.5 * sz:      # pas sous les racines du grand arbre
                continue
            hs = {dessus(x + dx, z + dz) for dx in (-0.85, 0.85) for dz in (-0.85, 0.85)}
            if len(hs) != 1 or None in hs:
                continue
            if any(abs(x - px) < 2.6 and abs(z - pz) < 2.6 for px, pz in prises):
                continue
            t = hs.pop()
            e = 0.7 if n_fl % 3 else 0.5
            b.box((x - e, t - 0.05, z - e), (x + e, t + 0.2, z + e), c(fleurs[n_fl % len(fleurs)]),
                  collide=False, shadow=False, name="Fleur")
            prises.append((x, z))
            n_fl += 1
        # pierres à demi enterrées (studs sur le dessus)
        gris = (mix(c("quai"), c("bordure"), 0.35), c("quai"), mix(c("pierre_maison"), c("bordure"), 0.5))
        for i, (x, z, w, d, h, yaw) in enumerate(((-15.5, 9.0, 2.4, 1.8, 1.0, 20), (16.5, -6.0, 1.8, 1.5, 0.8, -35),
                                                   (-20.0, -6.5, 1.5, 1.2, 0.6, 50))):
            t = dessus(x * sx, z * sz) or 0.0
            b.boxc((x * sx, t - 0.3 + h / 2, z * sz), (w, h, d), gris[i], yaw=yaw, studs="top", name="Pierre")
        # sentier de terre qui monte du côté du couloir (-X)
        for (xa, xb, et, j, lz, col) in ((-23.6, -19.2, 0, 0, 1.4, "terre"), (-18.8, -17.2, 0, 1, 1.3, "terre_claire"),
                                         (-16.8, -13.7, 1, 0, 1.2, "terre")):
            t = etages[et][j][2] * sy
            b.box((xa * sx, t - 0.4, -lz), (xb * sx, t + 0.1, lz), c(col), studs="top", name="Sentier")
    info = _infos(b, n0)
    info["hauteur"] = round(etages[2][0][2] * sy, 3)
    return info


# ---------------------------------------------------------------------------
# Petite végétation : buissons, parterres, meules, champs
# ---------------------------------------------------------------------------

def buisson(b, variant: int = 0) -> dict:
    """Buisson bas (≈ 4 × 4 × 3) : 0 boule verte, 1 buisson fleuri (rouge et rose), 2 haie taillée en cube,
    3 genêt jaune. ≤ 8 pièces."""
    v = variant % 4
    rng = b.rng
    k = _K(b, 1.0)
    n0 = len(b.parts)
    F = lambda n, a=0.04: vary(n, rng, a)  # noqa: E731
    with b.group("Buisson"):
        if v in (0, 1, 3):
            k.bloc(0, -0.2, 0, 4.0, 2.2, 3.5, F("feuille_fonce"))
            k.bloc(0.25, -0.1, -0.25, 3.5, 2.6, 3.5, F("feuille") if v != 3 else F("haie"), 45)
            k.bloc(-0.25, 2.25, 0.25, 2.5, 0.75, 2.0, F("feuille_claire"))
            k.bloc(2.0, -0.15, 1.0, 1.75, 1.6, 1.75, F("feuille_fonce"), 30)
            if v == 0:
                k.bloc(-2.0, -0.15, -0.75, 1.5, 1.2, 1.5, F("feuille"), -20)
                k.bloc(0, 2.75, 0, 1.0, 0.5, 1.0, F("feuille_jaune"), 45)
            else:
                cols = ("fleur_rouge", "fleur_rose") if v == 1 else ("fleur_jaune", "ble")
                for i, (x, y, z) in enumerate(((-1.2, 2.15, -0.6), (0.9, 2.95, 0.4), (1.7, 2.3, -0.9), (-1.3, 1.65, 1.45))):
                    k.point(x, y, z, 0.8, c(cols[i % 2]))
        else:  # haie taillée : pavé, dessus plus clair, socle sombre
            k.bloc(0, -0.2, 0, 4.0, 2.9, 3.0, F("haie"), studs="none")
            k.bloc(0, 2.6, 0, 3.6, 0.5, 2.6, F("feuille"))
            k.bloc(0, -0.1, 0, 4.3, 0.6, 3.3, F("feuille_ombre"), studs="none", name="Socle")
    return _infos(b, n0)


PARTERRES = (
    (("fleur_rouge", "fleur_rouge", "fleur_rose"), "pierre"),     # géraniums rouges
    (("fleur_jaune", "fleur_blanche", "fleur_jaune"), "bois"),    # jaune et blanc
    (("fleur_bleue", "fleur_mauve", "fleur_bleue"), "pierre"),    # bleu et mauve
    (("fleur_blanche", "fleur_jaune", "fleur_bleue", "fleur_rouge", "fleur_mauve"), "bois"),  # mélange de prairie
)


def parterre_fleurs(b, variant: int = 0, largeur: float = 8, profondeur: float = 6) -> dict:
    """Parterre de fleurs : bordure basse (pierre ou bois, studs), terre, trois rangs de feuillage piqués de fleurs.
    0 géraniums rouges ; 1 jaune et blanc ; 2 bleu et mauve ; 3 mélange de prairie. ≤ 16 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    fleurs, bord = PARTERRES[v]
    w, d = largeur / 2, profondeur / 2
    col_bord = vary("pierre_maison", rng, 0.03) if bord == "pierre" else vary("bois_moyen", rng, 0.03)
    with b.group("Parterre"):
        b.box((-w, -0.3, -d), (w, 0.6, d), col_bord, studs="top", name="Bordure")
        b.box((-w + 0.5, 0.5, -d + 0.5), (w - 0.5, 0.85, d - 0.5), c("terre_fonce"), studs="top", name="Terre")
        n_rangs = 3
        pas = (2 * d - 1.0) / n_rangs
        k = 0
        for i in range(n_rangs):
            z0 = -d + 0.5 + i * pas + 0.2
            z1 = z0 + pas - 0.4
            hh = 1.25 + 0.15 * (i % 2)
            b.box((-w + 0.75, 0.8, z0), (w - 0.75, hh, z1), vary("feuille" if i % 2 else "feuille_fonce", rng, 0.04),
                  studs="top", collide=False, name="Feuillage")
            n_f = max(2, int((2 * w - 1.5) / 2.1))
            for j in range(n_f):
                x = -w + 1.2 + (j + 0.5) * (2 * w - 2.4) / n_f + (0.3 if i % 2 else -0.3)
                zc = (z0 + z1) / 2 + (0.15 if j % 2 else -0.15)
                s = 1.0 if (i + j) % 2 else 0.8
                b.box((x - s / 2, hh - 0.2, zc - s / 2), (x + s / 2, hh + s * 0.55, zc + s / 2),
                      c(fleurs[k % len(fleurs)]), studs="top", collide=False, name="Fleur")
                k += 1
                if len(b.parts) - n0 >= 16:
                    break
            if len(b.parts) - n0 >= 16:
                break
    return _infos(b, n0)


def meule_foin(b, variant: int = 0) -> dict:
    """Meule de foin : 0 meule ronde en cylindres étagés et pointe, perche au sommet ; 1 meule carrée de bottes sous
    une bâche ; 2 petite meule penchée étayée d'une perche ; 3 deux petites meules. ≤ 10 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    foin, foin_f, ble = c("foin"), c("foin_fonce"), c("ble")

    def ronde(x, z, s=1.0, n=5, penche=0.0):
        """Cylindres empilés qui rétrécissent (studs sur le dessus de chaque tambour)."""
        rs = (2.4, 2.15, 1.75, 1.25, 0.7)[:n]
        hs = (1.5, 1.3, 1.1, 0.9, 0.7)[:n]
        cols = (foin_f, foin, vary(foin, rng, 0.05), ble, foin_f)
        y = -0.2
        for i in range(n):
            dx = penche * (y + hs[i] / 2)
            b.cyl((x + dx * s, (y + hs[i] / 2) * s, z), rs[i] * s, hs[i] * s + (0.2 * s if i == 0 else 0.0),
                  cols[i], axis="y", studs="top", name="Foin", collide=i < 2)
            y += hs[i] - (0.1 if i == 0 else 0.0)
        return y

    with b.group("Meule"):
        if v == 0:
            top = ronde(0, 0)
            b.box((-0.15, top - 1.0, -0.15), (0.15, top + 1.3, 0.15), c("bois"), collide=False, name="Perche")
            for i, (x, z, yaw) in enumerate(((2.6, 0.6, 20), (-1.2, -2.5, -35))):
                b.boxc((x, 0.08, z), (1.4, 0.25, 0.6), vary("foin", rng, 0.06), yaw=yaw, collide=False, name="Brins")
        elif v == 1:
            for i, x in enumerate((-1.15, 1.15)):
                b.box((x - 1.1, -0.2, -1.8), (x + 1.1, 1.4, 1.8), vary("foin", rng, 0.05), name="Botte")
            for i, z in enumerate((-1.1, 1.1)):
                b.box((-2.1, 1.4, z - 1.05), (2.1, 2.9, z + 1.05), vary("foin_fonce" if i else "foin", rng, 0.05), name="Botte")
            bache = c("toile_verte")
            b.wedge((-2.4, 2.8, -2.4), (2.4, 4.3, 0.0), bache, down="-z", studs="top", collide=False, name="Bache")
            b.wedge((-2.4, 2.8, 0.0), (2.4, 4.3, 2.4), shade(bache, 0.92), down="+z", studs="top", collide=False, name="Bache")
            for x in (-1.3, 1.3):
                b.box((x - 0.12, -0.1, -2.45), (x + 0.12, 2.9, -2.35), c("corde"), collide=False, name="Corde")
        elif v == 2:
            top = ronde(0, 0, 0.85, 4, penche=0.12)
            _poutre(b, (2.6, -0.2, -0.6), (1.2, top * 0.85 - 0.6, -0.2), 0.3, 0.3, c("bois"), 0, collide=False, name="Etai")
        else:
            ronde(-1.4, 0.3, 0.7, 4)
            ronde(1.7, -0.6, 0.55, 3)
            b.box((-1.55, 3.1, 0.15), (-1.25, 4.2, 0.45), c("bois"), collide=False, name="Perche")
    return _infos(b, n0)


def _cloture_champ(b, x0, x1, z, rng):
    """Clôture basse de bois : poteaux et deux lisses (7 à 9 pièces)."""
    n = max(2, int(round((x1 - x0) / 6)) + 1)
    for i in range(n):
        x = x0 + 0.4 + i * (x1 - x0 - 0.8) / (n - 1)
        b.box((x - 0.3, -0.3, z - 0.3), (x + 0.3, 2.3, z + 0.3), vary("bois_gris", rng, 0.05), name="Poteau")
    for y in (0.9, 1.7):
        b.box((x0, y - 0.15, z - 0.45), (x1, y + 0.15, z - 0.3), c("bois_clair"), name="Lisse")


def champ(b, variant: int = 0, largeur: float = 36, profondeur: float = 24) -> dict:
    """Champ cultivé sur une plaque de terre (studs, 0,6 de haut) : 0 blé (rangs dorés, quelques coquelicots) ;
    1 potager (rangs verts, tomates et potirons) ; 2 pré fauché (andains de foin, deux balles rondes). Clôture basse
    de bois sur le côté avant (-Z). Aucun épouvantail. ≤ 30 pièces."""
    v = variant % 3
    rng = b.rng
    n0 = len(b.parts)
    w, d = largeur / 2, profondeur / 2
    with b.group("Champ"):
        b.box((-w, -0.3, -d), (w, 0.6, d), vary("terre", rng, 0.03), studs="top", name="Terre")
        if v == 0:  # blé : rangs dorés à deux niveaux (tiges, épis plus clairs), coquelicots
            n = 7
            pas = (2 * d - 3.0) / n
            for i in range(n):
                z0 = -d + 2.0 + i * pas
                h = 1.5 + 0.25 * ((i * 7) % 3)
                xa = -w + 0.6 + 0.4 * (i % 2)
                xb = w - 0.6 - 0.3 * (i % 3)
                b.box((xa, 0.5, z0), (xb, h, z0 + pas - 0.7),
                      vary("ble_fonce" if i % 2 else "ble", rng, 0.03), studs="top", collide=False, name="Ble")
                b.box((xa + 0.5, h - 0.3, z0 + 0.3), (xb - 0.5, h + 0.45, z0 + pas - 1.0),
                      vary("ble" if i % 2 else mix(c("ble"), c("blanc"), 0.25), rng, 0.03), studs="top", collide=False,
                      name="Epis")
            for j in range(5):
                i = (j * 3 + 1) % n
                z0 = -d + 2.0 + i * pas
                h = 1.5 + 0.25 * ((i * 7) % 3) + 0.45
                x = -w + 4.0 + j * (2 * w - 8.0) / 4 + float(rng.uniform(-1.5, 1.5))
                b.box((x - 0.45, h - 0.2, z0 + 0.5), (x + 0.45, h + 0.35, z0 + 1.3), c("fleur_rouge"), collide=False,
                      name="Coquelicot")
        elif v == 1:  # potager : rangs de légumes (choux, tomates, potirons, salades)
            n = 5
            pas = (2 * d - 3.0) / n
            sortes = ((c("herbe_claire"), 1.3), (c("pomme"), 0.8), (c("tuile_claire"), 1.4), (c("feuille_claire"), 1.0),
                      (c("pomme"), 0.8))
            for i in range(n):
                z0 = -d + 2.0 + i * pas
                h = 1.2 + 0.2 * (i % 2)
                b.box((-w + 1.0, 0.5, z0), (w - 1.0, h, z0 + pas - 1.4), vary("potager" if i % 2 else "feuille", rng, 0.04),
                      studs="top", collide=False, name="Rang")
                col, sz = sortes[i]
                for j in range(3):
                    x = -w + 4.5 + (j + 0.5 * (i % 2)) * (2 * w - 9.0) / 3
                    zc = z0 + (pas - 1.4) / 2
                    b.box((x - sz / 2, h - 0.25, zc - sz / 2), (x + sz / 2, h - 0.25 + sz * 0.8, zc + sz / 2), col,
                          studs="top", collide=False, name="Legume")
        else:
            n = 6
            pas = (2 * d - 3.0) / n
            for i in range(n):
                z0 = -d + 2.0 + i * pas
                if i % 3 == 1:   # andain de foin (bourrelet arrondi)
                    b.box((-w + 1.0, 0.5, z0), (w - 1.0, 1.25, z0 + pas - 0.6), vary("foin", rng, 0.04), studs="top",
                          collide=False, name="Andain")
                    b.box((-w + 1.6, 1.1, z0 + 0.6), (w - 1.6, 1.55, z0 + pas - 1.2), vary("foin_fonce", rng, 0.04),
                          studs="top", collide=False, name="Andain")
                else:            # chaume coupé
                    b.box((-w + 0.8, 0.5, z0 + 0.2), (w - 0.8, 0.85, z0 + pas - 0.4), vary("herbe_seche", rng, 0.04),
                          studs="top", collide=False, name="Chaume")
            for x, z in ((-7.0, 2.6), (8.5, -4.2)):
                b.cyl((x, 0.5 + 1.45, z), 1.5, 2.2, vary("foin_fonce", rng, 0.04), axis="x", name="Balle")
                b.cyl((x, 0.5 + 1.45, z), 1.55, 0.3, c("foin"), axis="x", collide=False, name="Lien")
        _cloture_champ(b, -w, w, -d + 0.5, rng)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Canal et ponts en arc
# ---------------------------------------------------------------------------

Y_EAU = -1.2          # surface de l'eau
Y_FOND = -2.2         # dessus du fond (on y a pied : le joueur tombé à l'eau y marche)
Y_MUR_BAS = -3.4      # pied des murs de quai
MARGELLE = 2.0        # largeur des margelles


def _barque(b, x, z, yaw, rng, charge=0):
    """Barque plate amarrée (9 × 3) : fond, bordés, pointes relevées, deux bancs, une rame, une caisse ou des
    paniers. Flotte : le fond plonge sous la surface, le pont est au-dessus."""
    bois, clair = vary("bois", rng, 0.04), vary("bois_clair", rng, 0.04)
    peint = (c("toile_bleue"), c("toile_verte"), c("toile_rouge"))[charge % 3]
    with b.at((x, Y_EAU, z), yaw=yaw, group="Barque"):
        b.box((-1.25, -0.55, -3.6), (1.25, 0.15, 3.6), clair, name="Fond")
        for s in (-1, 1):
            xa, xb = sorted((s * 1.25, s * 1.55))
            b.box((xa, -0.5, -3.7), (xb, 0.45, 3.7), peint, name="Borde")
            xa, xb = sorted((s * 1.15, s * 1.65))
            b.box((xa, 0.45, -3.8), (xb, 0.6, 3.8), clair, collide=False, name="PlatBord")
        b.wedge_under((-1.55, -0.5, 3.7), (1.55, 0.45, 5.0), bois, down="+z", name="Pointe")
        b.wedge_under((-1.55, -0.5, -5.0), (1.55, 0.45, -3.7), bois, down="-z", name="Pointe")
        for zz in (-1.8, 1.6):
            b.box((-1.3, 0.25, zz - 0.4), (1.3, 0.5, zz + 0.4), clair, studs="top", name="Banc")
        _poutre(b, (-0.6, 0.56, -3.2), (0.7, 0.58, 2.9), 0.22, 0.14, c("bois_moyen"), 0, collide=False, name="Rame")
        b.boxc((0.66, 0.57, 3.3), (0.6, 0.12, 1.4), c("bois_moyen"), yaw=12, collide=False, name="Pelle")
        if charge % 2 == 0:
            b.boxc((0.3, 0.15 + 0.55, 0.0), (1.1, 1.1, 1.1), vary("bois_clair", rng, 0.08), yaw=10, studs="top",
                   collide=False, name="Caisse")
            b.boxc((-0.5, 0.15 + 0.4, -0.3), (0.8, 0.8, 0.8), c("pomme"), yaw=-15, collide=False, name="Pommes")
        else:
            b.cyl((0.2, 0.15 + 0.45, 0.1), 0.55, 0.9, c("chaume"), axis="y", studs="top", collide=False, name="Panier")
            b.cyl((-0.6, 0.15 + 0.35, -0.5), 0.45, 0.7, c("fleur_jaune"), axis="y", studs="top", collide=False,
                  name="Panier")


def canal(b, variant: int = 0, longueur: float = 136, largeur: float = 20) -> dict:
    """Canal de ville (« petite Venise ») posé dans le trou que `zone.py` laisse dans le sol : margelles de pierre
    de 2 (dessus à 0,4, studs) le long des deux rives, murs de quai qui descendent jusqu'au fond, eau à -1,2 (une
    nappe, des rides plus claires), fond sombre ; aux bouts une écluse (deux vantaux de bois, plancher, roue de fer)
    et l'arche d'un ponceau de pierre ; deux barques amarrées, deux escaliers de pierre qui descendent à l'eau sur la
    rive droite (+X), anneaux d'amarrage, lierre et mousse sur les murs.
    Repère : X à travers le canal (rive gauche = trottoir en -X), Z le long. 0 écluse en +Z, ponceau en -Z ;
    1 l'inverse ; 2 écluse en +Z, barques ailleurs. Les ponts de `pont_arche` (z = 54, 0, -54) sont évités.
    ≤ 160 pièces."""
    v = variant % 3
    rng = b.rng
    n0 = len(b.parts)
    W, L = largeur / 2, longueur / 2
    wi = W - MARGELLE                   # demi-largeur d'eau (face des murs de quai)
    ponts = [54.0, 0.0, -54.0]          # ponts du quartier (repère du canal), demi-largeur 3,5 (+ 0,5)
    quai = c("quai")
    with b.group("Canal"):
        # -- fond, eau, rides -------------------------------------------------------------
        b.box((-wi - 0.5, Y_MUR_BAS, -L + 1.5), (wi + 0.5, Y_FOND, L - 1.5), c("eau_fonce"), name="Fond")
        ecluse = L - 7.0 if v in (0, 2) else -(L - 7.0)     # z des vantaux de l'écluse
        sens = 1 if ecluse > 0 else -1
        z_haut = ecluse + sens * 0.6                         # bief amont, plus haut
        za, zb = sorted((-(L - 1.5) * sens, z_haut))
        # eau verte et profonde : bande centrale, bandes plus sombres à l'ombre des quais (faces jointives)
        e_centre = mix(mix(c("eau"), c("eau_fonce"), 0.5), c("haie"), 0.15)
        e_bord = mix(mix(c("eau"), c("eau_fonce"), 0.8), c("haie"), 0.15)
        for (xa, xb, col) in ((-wi - 0.5, -wi + 1.6, e_bord), (-wi + 1.6, wi - 1.6, e_centre), (wi - 1.6, wi + 0.5, e_bord)):
            b.box((xa, Y_FOND, za), (xb, Y_EAU, zb), col, material="Glass", collide=False, transparency=0.1, name="Eau")
        za, zb = sorted((z_haut, (L - 1.5) * sens))
        b.box((-wi - 0.5, Y_FOND, za), (wi + 0.5, Y_EAU + 0.55, zb), e_centre, material="Glass", collide=False,
              transparency=0.1, name="Eau")
        for i in range(13):
            z0 = -L + 5 + i * 10.0 + float(rng.uniform(-2, 2))
            if any(abs(z0 - zp) < 6 for zp in ponts) or abs(z0 - ecluse) < 6 or abs(z0) > L - 4:
                continue
            x0 = float(rng.uniform(-wi + 1.0, wi - 5.5))
            b.box((x0, Y_EAU - 0.05, z0), (x0 + 1.5 + 1.5 * (i % 3), Y_EAU + 0.06, z0 + 0.5),
                  c("eau_claire") if i % 3 else mix(c("eau_claire"), c("blanc"), 0.4), collide=False, shadow=False,
                  name="Ride")
        # -- murs de quai et margelles ----------------------------------------------------
        for s in (-1, 1):
            xa, xb = sorted((s * wi, s * W))
            b.box((xa, Y_MUR_BAS, -L + 2.0), (xb, 0.0, L - 2.0), vary(quai, rng, 0.02), name="MurQuai")
        for s in (-1, 1):  # murs des deux bouts
            zf = s * L
            za, zb = sorted((zf, zf - s * 2.0))
            b.box((-W, Y_MUR_BAS, za), (W, 0.0, zb), vary(quai, rng, 0.02), name="MurBout")
        tons_marg = (quai, c("pierre_maison_claire"), shade(quai, 0.93), mix(quai, c("pierre_maison"), 0.5))
        # retrait des margelles de bout : 2,3 (débord de 0,3 sur l'eau), 2,0 côté ponceau (son arche reste visible)
        e_bout = {sens: 2.3, -sens: 2.0}
        z_min, z_max = -(L - e_bout[-1]), L - e_bout[1]
        for s in (-1, 1):
            # margelle en tronçons de 9 à 14 (tons alternés) ; joints jamais sous un pont ; débord de 0,3 sur l'eau
            joints = [z_min]
            i = 0
            while joints[-1] < z_max - 1e-6:
                z1 = joints[-1] + (12.0, 9.5, 13.5, 10.5)[(i + (s > 0)) % 4]
                for zp in ponts:
                    if abs(z1 - zp) < 5.0:
                        z1 = zp + 5.5
                if z1 > z_max - 4.0:
                    z1 = z_max
                joints.append(z1)
                i += 1
            for i, (za, zb) in enumerate(zip(joints[:-1], joints[1:])):
                xa, xb = sorted((s * (wi - 0.3), s * W))
                b.box((xa, 0.0, za), (xb, 0.4, zb), vary(tons_marg[(i + (s > 0)) % 4], rng, 0.02), studs="top",
                      name="Margelle")
        for s in (-1, 1):
            za, zb = sorted((s * L, s * (L - e_bout[s])))
            b.box((-W, 0.0, za), (W, 0.4, zb), vary(c("pierre_maison_claire"), rng, 0.02), studs="top", name="Margelle")
        # -- pierres « pixel », mousse au fil de l'eau, lierre --------------------------------
        pierres = (c("pierre_maison"), c("pierre_brune"), c("pierre_maison_claire"), shade(quai, 0.88))
        for s in (-1, 1):
            xf = s * wi                                     # face du mur côté eau
            b.box((xf - s * 0.12 - 0.0 * s, Y_EAU - 0.3, -L + 2.0), (xf, Y_EAU + 0.22, L - 2.0),
                  c("mur_mousse"), collide=False, name="Mousse")
            for j in range(11):
                z0 = -L + 5.0 + j * 11.7 + float(rng.uniform(-2.5, 2.5)) + (3.0 if s > 0 else 0.0)
                if z0 > L - 6:
                    continue
                y0 = (-0.9, -0.55, -0.85, -0.6)[j % 4]
                lg = (2.0, 1.4, 2.6, 1.7)[(j + (s > 0)) % 4]
                xa, xb = sorted((xf, xf - s * 0.12))
                b.box((xa, y0, z0), (xb, y0 + 0.5, z0 + lg), pierres[(j + 2 * (s > 0)) % 4], collide=False,
                      name="Pierre")
        lierres = ((-1, 22.0, 1.6, 0.9), (-1, -30.0, 2.2, 1.0), (1, 41.0, 1.8, 0.85), (1, -12.0, 2.4, 1.0),
                   (-1, -60.0, 1.5, 0.8), (1, 63.0 if v == 1 else -40.0, 1.6, 0.9))
        for (s, z0, lg, h) in lierres:
            if any(abs(z0 - zp) < 5.5 for zp in ponts) or abs(z0 - ecluse) < 5:
                continue
            xf = s * wi
            xa, xb = sorted((xf - s * 0.3, xf - s * 0.15))
            b.box((xa, -h, z0), (xb, 0.0, z0 + lg), vary("lierre", rng, 0.05), collide=False, name="Lierre")
            xa, xb = sorted((xf - s * 0.42, xf + s * 0.3))
            b.box((xa, 0.4 - 0.05, z0 + 0.2), (xb, 0.52, z0 + lg * 0.75), vary("lierre", rng, 0.05), collide=False,
                  name="Lierre")
            xa, xb = sorted((xf - s * 0.27, xf - s * 0.12))
            b.box((xa, -h - 0.5, z0 + 0.3), (xb, -0.2, z0 + 0.3 + lg * 0.5), c("lierre_clair"), collide=False,
                  name="Lierre")
        # -- écluse : deux vantaux en V, plancher, roue de manœuvre ------------------------
        with b.group("Ecluse"):
            ze = ecluse
            ang = 12.0
            for s in (-1, 1):
                lg = wi / math.cos(math.radians(ang)) + 0.6
                cxv = s * wi / 2
                czv = ze - sens * (wi / 2) * math.tan(math.radians(ang))
                yaw = s * sens * ang
                ht = 0.8 if s < 0 else 0.7
                b.boxc((cxv, (Y_FOND - 0.8 + ht) / 2, czv), (lg, ht - Y_FOND + 0.8, 0.7), vary("bois", rng, 0.04),
                       yaw=yaw, name="Vantail")
                b.boxc((cxv, ht - 0.2 + 0.05 * (s > 0), czv), (lg - 0.4 - 0.3 * (s > 0), 0.25, 0.95), c("bois_clair"),
                       yaw=yaw, studs="top", name="Passerelle")
                b.boxc((cxv, -0.4, czv - sens * 0.45), (lg - 0.8, 0.22, 0.2), c("fer"), yaw=yaw, collide=False,
                       name="Ferrure")
            # roue de fer sur son socle, sur la margelle droite
            xr = wi + 1.0
            b.box((xr - 0.4, 0.4, ze - 0.4), (xr + 0.4, 2.3, ze + 0.4), c("fonte"), name="Socle")
            b.cyl((xr - 0.48, 2.3, ze), 0.9, 0.18, c("fer"), axis="x", collide=False, name="Roue")
            b.box((xr - 0.62, 2.12, ze - 0.14), (xr - 0.52, 2.48, ze + 0.14), c("fonte"), collide=False, name="Moyeu")
        # -- ponceau : arche de pierre dans le mur du bout, voûte sombre ---------------------
        with b.group("Ponceau"):
            sp = -sens
            zf = sp * (L - 2.0)                 # face du mur côté eau
            noir = mix(c("eau_fonce"), c("fonte"), 0.6)
            zz = sorted((zf, zf - sp * 0.12))
            for (hw, y0, y1) in ((3.3, Y_EAU - 0.1, -0.55), (2.5, -0.55, -0.3), (1.5, -0.3, -0.12)):
                b.box((-hw, y0, zz[0]), (hw, y1, zz[1]), noir, collide=False, name="Voute")
            clav = (c("pierre_maison_claire"), c("pierre_maison"))
            for i, (x0, x1, y0, y1) in enumerate(((-4.2, -3.3, Y_EAU - 0.05, -0.45), (-3.4, -2.4, -0.6, -0.2),
                                                  (-2.5, -1.4, -0.35, -0.02), (-1.5, -0.55, -0.18, -0.04),
                                                  (-0.6, 0.6, -0.26, 0.0), (0.55, 1.5, -0.18, -0.04),
                                                  (1.4, 2.5, -0.35, -0.02), (2.4, 3.4, -0.6, -0.2),
                                                  (3.3, 4.2, Y_EAU - 0.05, -0.45))):
                ep = 0.42 if i % 2 == 0 else 0.5
                zv = sorted((zf, zf - sp * ep))
                b.box((x0, y0, zv[0]), (x1, y1, zv[1]), clav[i % 2], collide=False, name="Claveau")
            # parapet de la rue qui passe sur le ponceau (garde-corps au bout du canal)
            za, zb = sorted((sp * (L - 1.4), sp * (L - 0.2)))
            b.box((-W + 0.3, 0.4, za), (W - 0.3, 1.5, zb), vary(c("pierre_maison"), rng, 0.02), name="Parapet")
            za, zb = sorted((sp * (L - 1.5), sp * (L - 0.1)))
            b.box((-W + 0.2, 1.5, za), (W - 0.2, 1.75, zb), c("pierre_maison_claire"), studs="top", name="Couvertine")
        # -- escaliers de pierre vers l'eau (rive droite) ------------------------------------
        for zs in ((26.0, -27.0) if v != 1 else (27.0, -24.0)):
            with b.group("Escalier"):
                x0, x1 = wi - 2.6, wi + 0.2
                marches = ((-0.4, 0.0, 3.6, 4.8), (-0.8, -0.4, 2.4, 3.6), (-1.2, -0.8, 1.2, 2.4))
                for (ya, yb, za, zb) in marches:
                    b.box((x0, ya, zs + za), (x1, yb, zs + zb), vary(c("pierre_maison_claire"), rng, 0.03), studs="top",
                          name="Marche")
                b.box((x0, Y_FOND, zs - 1.4), (x1, Y_EAU + 0.15, zs + 1.2), vary(c("pierre_maison"), rng, 0.03),
                      studs="top", name="Palier")
                b.wedge((x0 + 0.1, Y_FOND, zs + 1.2), (x1 - 0.05, -0.4, zs + 4.8), shade(quai, 0.9), down="-z",
                        name="Limon")
                b.cyl((wi - 0.06, -0.55, zs - 1.0), 0.32, 0.14, c("fer"), axis="x", collide=False, name="Anneau")
        # -- deux canards au fil de l'eau ------------------------------------------------------
        for (xc_, zc_, yaw) in (((-1.5, 33.0, 20.0), (0.4, 35.5, -10.0)) if v != 1 else ((1.0, -33.0, 160.0), (-0.8, -35.0, 200.0))):
            with b.at((xc_, Y_EAU, zc_), yaw=yaw, group="Canard"):
                b.box((-0.45, -0.25, -0.65), (0.45, 0.35, 0.65), c("blanc"), collide=False, name="Canard")
                b.box((-0.22, 0.3, -0.75), (0.22, 0.85, -0.3), c("blanc"), collide=False, name="Tete")
                b.box((-0.12, 0.5, -1.05), (0.12, 0.64, -0.7), c("toile_jaune"), collide=False, name="Bec")
        # -- barques amarrées ---------------------------------------------------------------
        if v == 0:
            barques = ((-wi + 1.9, 14.0, 4.0, 0), (wi - 1.9, -40.0, -3.0, 1))
        elif v == 1:
            barques = ((-wi + 1.9, -16.0, -5.0, 1), (wi - 1.9, 38.0, 4.0, 0))
        else:
            barques = ((-wi + 1.9, -36.0, 3.0, 2), (-wi + 1.9, 15.0, -4.0, 0))
        for (bx, bz, yaw, ch) in barques:
            _barque(b, bx, bz, yaw, rng, ch)
            s = -1 if bx < 0 else 1
            # amarre : de la pointe avant à un anneau du mur de quai
            av = np.array([bx, Y_EAU + 0.3, bz + 4.4])
            an = np.array([s * (wi - 0.1), -0.55, bz + 6.0])
            _corde(b, av, an, 0.09, c("corde"), name="Amarre")
            b.cyl((s * (wi - 0.06), -0.55, bz + 6.0), 0.3, 0.14, c("fer"), axis="x", collide=False, name="Anneau")
    return _infos(b, n0)


def pont_arche(b, variant: int = 0, portee: float = 24, largeur: float = 7, canal: float = 20.0,
               margelle: float = MARGELLE) -> dict:
    """Pont de pierre en arc pour piétons, du trottoir (x = -portee/2) au quai de la rive droite (x = +portee/2) :
    rampes de dalles à studs qui montent de y = 0 aux bouts jusqu'au tablier (y = 3), arche de pierre en gradins
    au-dessus de l'eau (clé claire, claveaux alternés), parapets de 1,2 sur le tablier et les rampes, bornes aux
    extrémités. L'arche est centrée sur l'eau du canal (x = -portee/2 + margelle → -portee/2 + canal - margelle).
    0 simple ; 1 avec un réverbère sur un parapet ; 2 avec des jardinières de géraniums. ≤ 45 pièces."""
    v = variant % 3
    rng = b.rng
    n0 = len(b.parts)
    P2, D = portee / 2, largeur / 2
    xe0, xe1 = -P2 + margelle, -P2 + canal - margelle          # eau : -10 → 6
    xc = (xe0 + xe1) / 2                                        # axe de l'arche : -2
    hs = (xe1 - xe0) / 2                                        # demi-ouverture : 8
    Y_T = 3.0                                                   # dessus du tablier
    xg, xd = xc - 5.0, xc + 5.0                                 # bouts du tablier plat
    dalle = vary("quai", rng, 0.02)
    pierres = (vary("pierre_maison", rng, 0.02), vary("pierre_maison_claire", rng, 0.02))
    cap = c("pierre_maison_claire")
    zs = D - 0.1                                                 # faces des rampes (3,4)
    zm = D - 0.3                                                 # faces de la maçonnerie (3,2)
    with b.group("Pont"):
        # tablier : rampes à studs et plateau
        b.wedge((-P2, -0.2, -zs), (xg, Y_T, zs), dalle, down="-x", studs="top", name="Rampe")
        b.wedge((xd, -0.2, -zs), (P2, Y_T, zs), dalle, down="+x", studs="top", name="Rampe")
        b.box((xg, Y_T - 0.6, -zs), (xd, Y_T, zs), shade(dalle, 1.04), studs="top", name="Tablier")
        # maçonnerie de l'arche : gradins symétriques autour de xc dont le dessous dessine un arc surbaissé ; sous les
        # rampes (|d| > 5), le dessous des coins sert d'intrados (y = -0,2) ; teintes du clair (clé) au foncé
        # (naissances) : on lit un arc, pas des piles
        ton = lambda t: vary(mix(c("pierre_maison_claire"), c("pierre_brune"), t), rng, 0.015)  # noqa: E731
        gradins = [(0.0, 1.5, 1.7, 0.0)]
        for (d0, d1, y0, t) in ((1.5, 3.0, 1.45, 0.2), (3.0, 4.25, 1.0, 0.4), (4.25, 5.0, 0.45, 0.55)):
            gradins += [(-d1, -d0, y0, t), (d0, d1, y0, t)]
        for (a, bb, y0, t) in gradins:
            b.box((xc + a, y0, -zm), (xc + bb, Y_T - 0.6, zm), ton(t), name="Arche")
        for (d0, d1, y0, t) in ((hs - 1.5, hs - 0.75, -0.55, 0.75), (hs - 0.75, hs, Y_EAU + 0.25, 0.9)):
            for sg in (-1, 1):
                xa, xb = sorted((xc + sg * d0, xc + sg * d1))
                b.box((xa, y0, -zm), (xb, -0.2, zm), ton(t), name="Arche")
        # clé de voûte (déborde sur les deux faces et sous l'intrados)
        b.box((xc - 0.7, 1.45, -(zm + 0.12)), (xc + 0.7, 2.55, zm + 0.12), c("pierre_maison_claire"), name="Cle")
        # parapets : rampants tournés sur la pente, plat sur le tablier, bornes aux bouts et aux angles
        epp, hp = 0.6, 1.2
        for s in (-1, 1):
            z0, z1 = sorted((s * (D - epp), s * D))
            zc = (z0 + z1) / 2
            b.box((xg, Y_T, z0), (xd, Y_T + hp, z1), pierres[1], name="Parapet")
            b.box((xg - 0.1, Y_T + hp, z0 - 0.08), (xd + 0.1, Y_T + hp + 0.25, z1 + 0.08), cap, studs="top",
                  collide=False, name="Couvertine")
            for (xa, xb) in ((-P2 + 1.0, xg), (xd, P2 - 1.0)):
                ya = -0.2 + (Y_T + 0.2) * ((xa + P2) / (xg + P2) if xa < 0 else (P2 - xa) / (P2 - xd))
                yb = -0.2 + (Y_T + 0.2) * ((xb + P2) / (xg + P2) if xb < 0 else (P2 - xb) / (P2 - xd))
                ang = math.degrees(math.atan2(yb - ya, xb - xa))
                Lr = math.hypot(xb - xa, yb - ya)
                nx, ny = -math.sin(math.radians(ang)), math.cos(math.radians(ang))
                cx = (xa + xb) / 2 + nx * (hp / 2 - 0.1)
                cy = (ya + yb) / 2 + ny * (hp / 2 - 0.1)
                b.part("block", (Lr, hp, epp), (cx, cy, zc), rot_z(ang), pierres[0], name="Parapet")
            for (xa, xb, y0, y1) in ((-P2 + 0.1, -P2 + 1.2, -0.3, 1.9), (P2 - 1.2, P2 - 0.1, -0.3, 1.9),
                                     (xg - 0.55, xg + 0.55, Y_T - 0.75, Y_T + hp + 0.5),
                                     (xd - 0.55, xd + 0.55, Y_T - 0.75, Y_T + hp + 0.5)):
                b.box((xa, y0, z0 - 0.1), (xb, y1, z1 + 0.1), pierres[0], name="Borne")
                if y0 < 0:  # chapeau sur les bornes des extrémités seulement
                    b.box((xa + 0.05, y1, z0 - 0.2), (xb - 0.05, y1 + 0.3, z1 + 0.2), cap, studs="top",
                          collide=False, name="Chapeau")
        if v == 1:  # réverbère sur le parapet (+Z), au milieu du tablier
            with b.group("Reverbere"):
                x, z = xc, D - epp / 2
                y = Y_T + hp + 0.25
                b.box((x - 0.2, y, z - 0.2), (x + 0.2, y + 3.2, z + 0.2), c("fonte"), name="Poteau")
                b.box((x - 0.5, y + 3.2, z - 0.5), (x + 0.5, y + 3.4, z + 0.5), c("fonte"), collide=False, name="Lanterne")
                b.box((x - 0.4, y + 3.4, z - 0.4), (x + 0.4, y + 4.5, z + 0.4), c("lampe"), material="Neon",
                      collide=False, shadow=False, name="Lanterne")
                b.wedge((x - 0.55, y + 4.5, z - 0.55), (x + 0.55, y + 5.0, z), c("fonte"), down="-z", collide=False,
                        name="Chapeau")
                b.wedge((x - 0.55, y + 4.5, z), (x + 0.55, y + 5.0, z + 0.55), c("fonte"), down="+z", collide=False,
                        name="Chapeau")
        elif v == 2:  # jardinières de géraniums sur les deux parapets
            for s in (-1, 1):
                z0, z1 = sorted((s * (D - epp - 0.05), s * (D + 0.05)))
                y = Y_T + hp + 0.25
                b.box((xc - 3.5, y, z0), (xc + 3.5, y + 0.55, z1), c("bois_moyen"), collide=False, name="Jardiniere")
                b.box((xc - 3.3, y + 0.5, z0 + 0.1), (xc + 3.3, y + 0.95, z1 - 0.1), c("feuille_fonce"), studs="top",
                      collide=False, name="Feuillage")
                for j, x in enumerate((-2.3, 0.1, 2.2)):
                    b.box((xc + x - 0.35, y + 0.8, (z0 + z1) / 2 - 0.3), (xc + x + 0.35, y + 1.25, (z0 + z1) / 2 + 0.3),
                          c("fleur_rouge" if j != 1 else "fleur_rose"), studs="top", collide=False, name="Geranium")
    return _infos(b, n0)
