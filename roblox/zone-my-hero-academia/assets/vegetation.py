"""Végétation du campus (zone My Hero Academia) en style stud : conifères taillés en colonnes, arbres ronds,
haies taillées, ceinture d'arbres le long du mur d'enceinte, parterres de fleurs et rochers.

Principes :
- feuillages en blocs empilés et décalés (« nuages » cubiques), studs sur les dessus ; trois ou quatre tons par
  masse : dessous sombre (le volume se lit d'en bas), corps, étage plus clair, sommet ensoleillé ;
- deux familles de silhouettes bien distinctes : les **colonnes** (conifères taillés de la référence 2 : étages
  droits et à 45° alternés en fuseau, cône en gradins ou croix de blocs, profil en escalier qui s'affine vers le
  haut) et les **nuages ronds** (arbres feuillus, blocs droits et blocs tournés de 45° alternés : contour
  octogonal, arrondi sous tous les angles) ;
- troncs, souches, bordures et rochers collisionnent ; feuillages et fleurs non (`collide=False`) ;
- cotes de conception données pour `taille = 1` sur une grille de 0,125, puis multipliées par l'échelle sans
  réarrondi : deux faces de même orientation qui se recouvrent restent séparées d'au moins 0,125 × échelle (pas de
  z-fighting) quelle que soit la taille demandée par la mise en page ; dans les bosquets, deux arbres voisins ont
  des familles de hauteurs décalées de 0,125 (contrôlé par script : faces parallèles à moins de 0,09 l'une de
  l'autre, pièces flottantes, emprises et budgets) ;
- verts francs tirant vers le jaune-vert (pas d'émeraude dominant) ; les conifères gardent le vert sombre bleuté de
  la référence, réchauffé par des pointes plus claires.

Toutes les fonctions renvoient {"emprise": (largeur x, profondeur z), "hauteur": h} mesurés sur les pièces posées.
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, shade
from palette import c, vary

# Couleurs locales dérivées de la palette (aucune couleur nouvelle dans palette.py)
SOLEIL = mix(c("feuille_pale"), c("fleur_jaune"), 0.25)          # pointe ensoleillée des houppiers
OMBRE = shade(c("feuille_fonce"), 0.82)                            # dessous des houppiers
POINTE_CONIF = mix(c("conifere_clair"), c("feuille_claire"), 0.5)  # pousses claires des conifères
HAIE_FONCE = shade(mix(c("haie"), c("feuille_fonce"), 0.5), 0.8)          # pied de la haie (ombre portée)
HAIE_CORPS = (mix(c("haie"), c("feuille_fonce"), 0.35), mix(c("haie"), c("haie_claire"), 0.3))  # corps, tons alternés
HAIE_SOMMET = (mix(c("haie_claire"), c("feuille_pale"), 0.6), mix(c("haie_claire"), c("feuille_pale"), 0.35))  # dessus taillé
ROSE_OMBRE = shade(c("fleur_rose"), 0.8)
ROSE_CLAIR = mix(c("fleur_rose"), c("fleur_blanche"), 0.45)
ROSE_PALE = mix(c("fleur_rose"), c("fleur_blanche"), 0.75)
TRONC_CERISIER = mix(c("tronc"), c("violet_fonce"), 0.18)


# ---------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------

class _K:
    """Cotes de conception (taille 1) multipliées par l'échelle : `t` en hauteur, `th` à l'horizontale."""

    def __init__(self, b, t: float = 1.0, th: float | None = None):
        self.b = b
        self.t = float(t)
        self.th = float(t if th is None else th)

    def p(self, x, y, z):
        return (x * self.th, y * self.t, z * self.th)

    def s(self, sx, sy, sz):
        return (sx * self.th, sy * self.t, sz * self.th)

    def bloc(self, cx, y0, cz, sx, sy, sz, col, yaw=0.0, **kw):
        """Bloc de feuillage donné par le centre de sa base, sa taille et sa rotation (0° ou 45° le plus souvent)."""
        kw.setdefault("studs", "top")
        kw.setdefault("collide", False)
        kw.setdefault("name", "Feuillage")
        return self.b.boxc(self.p(cx, y0 + sy / 2, cz), self.s(sx, sy, sz), col, yaw=yaw, **kw)

    def bois(self, cx, y0, cz, sx, sy, sz, col, yaw=0.0, **kw):
        """Tronçon de tronc ou de branche (solide par défaut, sans studs)."""
        kw.setdefault("name", "Tronc")
        return self.b.boxc(self.p(cx, y0 + sy / 2, cz), self.s(sx, sy, sz), col, yaw=yaw, **kw)

    def coin(self, x0, y0, z0, x1, y1, z1, col, down, **kw):
        kw.setdefault("name", "Racine")
        return self.b.wedge(self.p(x0, y0, z0), self.p(x1, y1, z1), col, down=down, **kw)

    def poutre(self, p0, p1, w, d, col, **kw):
        """Bloc de section w × d tendu de p0 à p1 (branche ou fût penché) ; l'axe local Y suit la poutre."""
        a = np.array(self.p(*p0), float)
        e = np.array(self.p(*p1), float)
        u = e - a
        L = float(np.linalg.norm(u))
        u /= L
        h = np.cross(u, (0.0, 0.0, 1.0))
        if np.linalg.norm(h) < 1e-6:
            h = np.cross(u, (1.0, 0.0, 0.0))
        h /= np.linalg.norm(h)
        z = np.cross(h, u)
        R = np.column_stack([h, u, z])
        kw.setdefault("name", "Branche")
        return self.b.part("block", (w * self.th, L, d * self.th), (a + e) / 2, R, col, **kw)


def _infos(b, n0: int) -> dict:
    """Emprise (x, z) et hauteur réelles des pièces ajoutées depuis `n0`, dans le repère de l'asset."""
    o = b.to_world((0, 0, 0))
    M = np.vstack([b.to_world(e) - o for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))])
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for p in b.parts[n0:]:
        R = np.asarray(p.rot, float).reshape(3, 3)
        half = np.asarray(p.size, float) / 2
        for s in ((1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1), (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1)):
            loc = M @ (np.asarray(p.pos, float) + R @ (half * s) - o)
            lo, hi = np.minimum(lo, loc), np.maximum(hi, loc)
    if not np.isfinite(lo).all():
        return {"emprise": (0, 0), "hauteur": 0}
    return {"emprise": (round(float(hi[0] - lo[0]), 2), round(float(hi[2] - lo[2]), 2)), "hauteur": round(float(hi[1]), 2)}


# ---------------------------------------------------------------------------
# 1. Conifères taillés en colonnes (référence 2 : rangée dense à gauche de l'avenue)
# ---------------------------------------------------------------------------

def _tons_conif(rng):
    """(foncé, moyen, clair, pointe) d'un conifère : vert sombre bleuté de la référence, réchauffé vers le haut."""
    base = (c("conifere_fonce"), mix(c("conifere"), c("conifere_clair"), 0.45),
            mix(c("conifere_clair"), c("feuille"), 0.4), POINTE_CONIF)
    return tuple(vary(col, rng, 0.035) for col in base)


def conifere(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Conifère taillé en colonne (cyprès d'Italie / thuya de la référence 2), 15 à 16 studs à taille 1, 4,1 studs
    de large au plus. 0 colonne élancée torsadée (étages droits et à 45° alternés, en fuseau), 1 cône en gradins,
    2 colonne bicolore en croix à pousses claires. ≤ 8 pièces.
    La largeur grandit quatre fois moins vite que la hauteur (les grands sujets restent élancés : dans l'avenue, la
    rangée reste en |x| ≥ 60)."""
    rng = b.rng
    v = variant % 3
    t = float(taille)
    k = _K(b, t, 1 + 0.25 * (t - 1))
    n0 = len(b.parts)
    fo, mo, cl, po = _tons_conif(rng)
    with b.group("Conifere"):
        k.bois(0, 0, 0, 1.0, 2.25, 1.0, vary("tronc", rng, 0.04))
        if v == 0:  # fuseau torsadé : six étages alternés droits / 45°, du plus sombre au plus clair
            k.bloc(0, 1.0, 0, 3.0, 4.75, 3.0, fo)
            k.bloc(0, 1.75, 0, 2.875, 7.0, 2.875, mix(fo, mo, 0.6), 45)
            k.bloc(0, 4.75, 0, 2.75, 6.25, 2.75, mo)
            k.bloc(0, 8.25, 0, 2.25, 4.75, 2.25, mix(mo, cl, 0.6), 45)
            k.bloc(0, 11.5, 0, 1.75, 2.75, 1.75, cl)
            k.bloc(0, 13.75, 0, 0.875, 2.25, 0.875, po, 45)
        elif v == 1:  # cône en gradins : trois étages droits + étages tournés de 45°, pointe
            k.bloc(0, 1.0, 0, 3.0, 4.75, 3.0, fo)
            k.bloc(0, 1.5, 0, 2.875, 3.75, 2.875, mix(fo, mo, 0.5), 45)
            k.bloc(0, 4.75, 0, 2.5, 4.75, 2.5, mo)
            k.bloc(0, 5.25, 0, 2.25, 4.0, 2.25, mix(mo, cl, 0.5), 45)
            k.bloc(0, 9.0, 0, 1.75, 4.0, 1.75, cl)
            k.bloc(0, 9.5, 0, 1.5, 3.25, 1.5, mix(cl, po, 0.5), 45)
            k.bloc(0, 12.5, 0, 0.75, 2.5, 0.75, po)
        else:  # thuya bicolore : croix de blocs (bras clair / bras sombre), épaule arrondie, pousses claires
            # posées sur les gradins des bras
            k.bloc(0, 1.25, 0, 4.0, 7.25, 2.5, mo)
            k.bloc(0, 1.5, 0, 2.5, 8.5, 4.0, fo)
            k.bloc(0, 1.0, 0, 3.25, 11.0, 3.25, mix(fo, mo, 0.5))
            k.bloc(0, 11.25, 0, 2.75, 2.5, 2.75, mix(mo, cl, 0.5), 45)
            k.bloc(0, 13.0, 0, 1.75, 2.0, 1.75, cl)
            k.bloc(1.375, 8.25, 0, 0.75, 1.25, 1.5, po, name="Pousse")
            k.bloc(0, 9.5, 1.5, 1.5, 1.25, 0.75, po, name="Pousse")
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 2. Arbres ronds (masse touffue de la référence 2, à droite de l'avenue)
# ---------------------------------------------------------------------------

def _tons_feuille(rng, rose=False):
    """(ombre, foncé, moyen, clair, soleil) d'un houppier, légèrement variés."""
    if rose:
        base = (shade(ROSE_OMBRE, 0.9), ROSE_OMBRE, c("fleur_rose"), ROSE_CLAIR, ROSE_PALE)
    else:
        base = (OMBRE, c("feuille_fonce"), c("feuille"), c("feuille_claire"), SOLEIL)
    return tuple(vary(col, rng, 0.035) for col in base)


def arbre_rond(b, variant: int = 0, taille: float = 1.0) -> dict:
    """Arbre feuillu rond (12 à 15 studs à taille 1, houppier ≤ 8,1 de large : ≤ 9 à taille 1,1) :
    tronc, une ou deux branches, houppier en nuage de blocs (dessous sombre, corps droit + corps à 45°, étage clair,
    sommet ensoleillé, bosses latérales décalées). 0 rond et large, 1 ovale plus haut, 2 deux houppiers sur un tronc
    fourchu, 3 cerisier en fleurs (rose, avec parcimonie). ≤ 20 pièces."""
    rng = b.rng
    v = variant % 4
    k = _K(b, taille)
    n0 = len(b.parts)
    om, fo, mo, cl, so = _tons_feuille(rng, rose=(v == 3))
    tr = vary(TRONC_CERISIER if v == 3 else c("tronc"), rng, 0.04)
    rac = shade(tr, 0.85)
    with b.group("Arbre"):
        if v in (0, 3):  # rond et large : boule octogonale bosselée, branche basse et sa touffe
            k.bois(0, 0, 0, 1.25, 6.25, 1.25, tr)
            k.coin(0.625, 0, -0.5, 1.75, 1.25, 0.5, rac, "+x")
            k.coin(-0.5, 0, -1.5, 0.5, 1.0, -0.625, rac, "-z")
            k.bois(1.5, 3.75, 0.125, 2.0, 0.75, 0.75, tr, collide=False, name="Branche")
            k.bloc(2.75, 3.25, 0.125, 2.0, 1.75, 2.0, fo, 20)
            k.bloc(0, 4.5, 0, 4.5, 1.0, 4.5, om)
            k.bloc(0, 5.0, 0, 4.25, 2.25, 4.25, mix(om, fo, 0.5), 45)
            k.bloc(0, 5.75, 0, 7.0, 3.5, 6.25, fo)
            k.bloc(0.25, 6.25, -0.25, 5.5, 3.5, 5.5, mix(fo, mo, 0.5), 45)
            k.bloc(-0.25, 8.75, 0.25, 6.0, 2.25, 6.0, mo)
            k.bloc(0.25, 10.0, 0, 4.25, 1.75, 4.25, cl, 45)
            k.bloc(-0.25, 11.25, 0.25, 2.75, 1.25, 2.75, mix(cl, so, 0.5))
            k.bloc(0.25, 12.0, 0, 1.25, 1.0, 1.25, so, 45)
            k.bloc(-2.75, 6.875, 2.25, 2.5, 2.0, 2.5, fo)
            k.bloc(2.5, 8.125, -2.25, 2.5, 1.75, 2.5, cl)
            k.bloc(-2.25, 9.625, -2.0, 2.25, 1.5, 2.0, mo, 30)
            k.bloc(1.75, 10.625, 1.5, 2.0, 1.25, 2.25, cl, 10)
            k.bloc(-2.0, 10.875, 1.25, 1.75, 1.125, 1.75, mix(cl, so, 0.3), -25)
        elif v == 1:  # ovale plus haut : étages alternés droits / 45°
            k.bois(0, 0, 0, 1.25, 6.5, 1.25, tr)
            k.coin(-1.75, 0, -0.5, -0.625, 1.25, 0.5, rac, "-x")
            k.coin(-0.5, 0, 0.625, 0.5, 1.0, 1.5, rac, "+z")
            k.bois(-1.375, 4.25, 0, 1.5, 0.75, 0.75, tr, collide=False, name="Branche")
            k.bloc(-2.5, 3.75, 0, 2.0, 1.5, 2.0, fo, -15)
            k.bloc(0, 4.75, 0, 4.0, 1.0, 4.0, om)
            k.bloc(0, 5.25, 0, 6.25, 4.5, 6.0, fo)
            k.bloc(0.25, 5.75, 0.25, 4.5, 4.75, 4.5, mix(fo, mo, 0.5), 45)
            k.bloc(-0.25, 9.5, -0.25, 5.25, 3.0, 5.25, mo)
            k.bloc(0, 10.0, 0, 3.5, 3.25, 3.5, mix(mo, cl, 0.5), 45)
            k.bloc(0.25, 12.5, 0.25, 3.25, 1.5, 3.25, cl)
            k.bloc(0, 13.75, 0, 1.75, 1.0, 1.75, so, 45)
            k.bloc(2.25, 7.375, -1.75, 2.25, 2.25, 2.25, mo, 10)
            k.bloc(-2.0, 10.875, 1.75, 2.25, 1.75, 2.0, cl, -10)
            k.bloc(-2.25, 6.625, -1.75, 2.0, 2.0, 2.25, fo, 25)
            k.bloc(1.75, 11.375, -1.25, 1.75, 1.25, 1.75, mix(cl, so, 0.3), 20)
        else:  # deux houppiers sur un tronc fourchu
            k.bois(0, 0, 0, 1.5, 4.0, 1.5, tr)
            k.coin(0.75, 0, -0.5, 1.875, 1.25, 0.5, rac, "+x")
            k.coin(-1.875, 0, -0.5, -0.75, 1.0, 0.5, rac, "-x")
            k.poutre((-0.25, 3.5, 0), (-1.75, 7.5, 0.25), 1.0, 1.0, tr, name="Fourche")
            k.poutre((0.25, 3.5, 0), (1.75, 8.25, -0.25), 1.0, 1.0, tr, name="Fourche")
            # houppier gauche (plus bas)
            k.bloc(-1.75, 6.75, 0.25, 3.5, 1.0, 3.5, om)
            k.bloc(-1.75, 7.25, 0.25, 4.25, 3.25, 5.25, fo)
            k.bloc(-1.5, 7.75, 0.0, 3.25, 3.0, 3.25, mix(fo, mo, 0.5), 45)
            k.bloc(-2.0, 10.0, 0.5, 3.0, 1.5, 3.5, mo)
            k.bloc(-1.75, 11.25, 0.25, 1.5, 0.75, 1.5, cl, 45)
            # houppier droit (plus haut)
            k.bloc(1.75, 7.625, -0.25, 3.25, 1.0, 3.25, om)
            k.bloc(1.75, 8.125, -0.25, 4.0, 3.5, 5.0, fo)
            k.bloc(1.875, 8.625, -0.5, 3.25, 3.5, 3.25, mix(fo, mo, 0.5), 45)
            k.bloc(1.5, 11.375, 0.0, 3.0, 1.75, 3.5, mo)
            k.bloc(1.75, 12.875, -0.25, 1.75, 1.0, 1.75, cl, 45)
            k.bloc(0.125, 9.875, 1.5, 2.25, 1.5, 2.25, so, 15)
            k.bloc(-2.5, 8.375, -1.5, 2.0, 1.75, 2.0, mo, 20)
            k.bloc(2.5, 10.875, 1.5, 1.75, 1.5, 1.75, cl, -15)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 3. Haies taillées (bord de l'avenue, |x| 55,5 → 58,5)
# ---------------------------------------------------------------------------

def haie(b, longueur: float = 24.0, hauteur: float = 3.5, variant: int = 0) -> dict:
    """Haie de buis taillée le long de X local (centrée, 3 studs de large) : 2 à 4 blocs de tons alternés, un
    chapeau plus clair en retrait de 0,2 (studs), extrémités carrées et nettes ; dessous un peu plus sombre.
    0 simple, 1 posée dans une bordure basse de béton blanc (0,6 de haut, saillie 0,2).
    ≤ ceil(3 + longueur / 6) pièces."""
    rng = b.rng
    v = variant % 2
    L, H = float(longueur), float(hauteur)
    n0 = len(b.parts)
    budget = int(math.ceil(3 + L / 6))
    n = 2 if L < 16 else (3 if L < 34 else 4)
    m = n
    if 1 + n + m > budget:
        m = max(1, budget - 1 - n)
    w = L / 2
    with b.group("Haie"):
        if v == 1:
            b.box((-w - 0.2, 0, -1.7), (w + 0.2, 0.6, 1.7), vary("blanc_casse", rng, 0.02), studs="top", name="Bordure")
            yb = 0.3
        else:
            b.box((-w, 0, -1.5), (w, 0.75, 1.5), vary(HAIE_FONCE, rng, 0.03), name="Pied")
            yb = 0.75
        # corps : n blocs de tons alternés, largeurs un peu inégales
        poids = [1.0 + 0.18 * ((i * 7) % 3 - 1) for i in range(n)]
        xs = np.concatenate([[0.0], np.cumsum(poids)]) / sum(poids) * L - w
        ton = HAIE_CORPS
        for i in range(n):
            b.box((xs[i], yb, -1.5), (xs[i + 1], H - 0.5, 1.5), vary(ton[i % 2], rng, 0.03), studs="top",
                  collide=True, name="Haie")
        # chapeau : m blocs clairs, joints décalés de ceux du corps
        e = 0.2
        poids = [1.0 + 0.15 * ((i * 5 + 1) % 3 - 1) for i in range(m)]
        xt = np.concatenate([[0.0], np.cumsum(poids)]) / sum(poids) * (L - 2 * e) - (w - e)
        tons_h = HAIE_SOMMET
        for i in range(m):
            b.box((xt[i], H - 0.9, -1.5 + e), (xt[i + 1], H, 1.5 - e), vary(tons_h[i % 2], rng, 0.03), studs="top",
                  collide=False, name="Taille")
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 4. Bosquets : ceinture d'arbres le long du mur d'enceinte (référence 1)
# ---------------------------------------------------------------------------

def _q(v):
    """Arrondi au quart de stud."""
    return round(v * 4) / 4


def _rond_simple(k, rng, cx, cz, h, w, fam, clair=False):
    """Arbre rond simplifié de la ceinture : tronc + 4 blocs de houppier (5 pièces). `h` hauteur totale, `w` largeur
    du houppier, `fam` décalage de la famille de hauteurs, `clair` décale la gamme d'un ton vers le clair."""
    om, fo, mo, cl, so = _tons_feuille(rng)
    if clair:
        fo, mo, cl = mix(fo, mo, 0.5), mix(mo, cl, 0.5), mix(cl, so, 0.4)
    yb = _q(h * 0.34) + fam
    hc = h - yb
    k.bois(cx, 0.75, cz, _q(max(1.0, w * 0.13)), yb + 1.0 - 0.75, _q(max(1.0, w * 0.13)), vary("tronc", rng, 0.04))
    k.bloc(cx, yb, cz, w, _q(hc * 0.5), _q(w * 0.86), fo)
    k.bloc(cx + 0.25, yb + 0.5, cz - 0.25, _q(w * 0.7), _q(hc * 0.56), _q(w * 0.7), mix(fo, mo, 0.55), 45)
    y3 = yb + _q(hc * 0.46)
    k.bloc(cx - 0.25, y3, cz + 0.25, _q(w * 0.68), _q(hc * 0.32), _q(w * 0.62), mo)
    y4 = yb + _q(hc * 0.72)
    k.bloc(cx + 0.25, y4, cz, _q(w * 0.4), h - y4, _q(w * 0.4), cl, 45)


def _conif_simple(k, rng, cx, cz, h, w, fam):
    """Conifère simplifié de la ceinture : tronc court planté dans le talus, fuseau de quatre étages alternés droits /
    45° qui s'affine vers la pointe (5 pièces). Le feuillage commence au-dessus du talus (y ≥ 2) : aucune face
    commune avec ses gradins."""
    fo, mo, cl, po = _tons_conif(rng)
    y0 = 2.25 + fam
    H = h - y0
    k.bois(cx, 0.75, cz, 1.0, y0 + 0.5 - 0.75, 1.0, vary("tronc", rng, 0.04))
    k.bloc(cx, y0, cz, _q(w * 0.72), _q(H * 0.46), _q(w * 0.72), fo)
    k.bloc(cx, y0 + 0.5, cz, _q(w * 0.66), _q(H * 0.6), _q(w * 0.66), mix(fo, mo, 0.6), 45)
    y3 = y0 + _q(H * 0.4)
    k.bloc(cx, y3, cz, _q(w * 0.5), _q(H * 0.45), _q(w * 0.5), mo)
    y4 = y0 + _q(H * 0.78)
    k.bloc(cx, y4, cz, _q(w * 0.27), h - y4, _q(w * 0.27), mix(cl, po, 0.4), 45)


BOSQUETS = [
    # (x, z, genre, hauteur, largeur) pour largeur 36 × profondeur 18 ; « r » rond, « c » conifère, « R » grand rond.
    # 0 : surtout des arbres ronds, deux conifères qui pointent derrière
    [(-12.0, -1.5, "r", 16, 12), (-1.0, 1.5, "r", 18.25, 12), (10.0, -1.0, "r", 15, 11), (-6.5, 4.75, "c", 21, 6),
     (14.5, 4.0, "c", 20, 6)],
    # 1 : surtout des conifères, serrés, et un rond en bout
    [(-14.0, 0.5, "c", 20, 6.5), (-8.0, -2.5, "c", 23, 7), (-2.0, 2.0, "c", 18, 6.5), (4.5, -1.0, "c", 24, 7),
     (12.5, 1.0, "r", 16, 11)],
    # 2 : mélange, avec un grand arbre au milieu
    [(-12.5, -1.0, "r", 15, 11), (-5.0, 3.5, "c", 19, 6), (3.0, -0.5, "R", 24, 13), (10.5, 4.0, "c", 21, 6),
     (13.25, -3.0, "r", 14, 8.5)],
]


def bosquet(b, variant: int = 0, largeur: float = 36.0, profondeur: float = 18.0) -> dict:
    """Morceau de la ceinture d'arbres qui ferme les côtés du campus et dépasse du mur d'enceinte : talus d'herbe
    bas en deux gradins (studs), 5 arbres de 14 à 24 studs mêlant colonnes de conifères et houppiers ronds, qui se
    touchent pour faire une masse continue vue de l'avenue comme du ciel. `largeur` suit le mur (X local),
    `profondeur` le traverse (Z local, l'avant -Z regarde la route). 0 surtout des ronds, 1 surtout des conifères,
    2 mélange avec un grand arbre. ≤ 30 pièces."""
    rng = b.rng
    v = variant % 3
    n0 = len(b.parts)
    sx, sz = largeur / 36.0, profondeur / 18.0
    with b.group("Bosquet"):
        # talus : deux gradins, studs (le sol de la zone reste dessous : pas de face à y = 0)
        hw, hd = largeur / 2, profondeur / 2
        b.box((-hw + 0.5, 0, -hd + 0.75), (hw - 0.5, 1.0, hd - 0.5), vary("herbe_claire", rng, 0.03), studs="top",
              name="Talus")
        b.box((-hw + 3.0, 0.5, -hd + 3.5), (hw - 4.0, 1.75, hd - 2.5), vary(mix(c("herbe_claire"), c("feuille_pale"), 0.4),
              rng, 0.03), studs="top", name="Talus")
        k = _K(b, 1.0)
        for i, (x, z, kind, h, w) in enumerate(BOSQUETS[v]):
            fam = 0.125 * (i % 2)          # familles de hauteurs alternées entre arbres voisins
            x, z = x * sx, z * sz
            if kind == "c":
                _conif_simple(k, rng, x, z, h, w, fam)
            elif kind == "R":  # grand arbre : houppier à deux étages
                _rond_simple(k, rng, x, z, h - 4, w, fam, clair=True)
                cl, so = _tons_feuille(rng)[3:]
                k.bloc(x - 0.75, h - 5.5 + fam, z + 0.5, _q(w * 0.42), 3.25, _q(w * 0.42), mix(cl, so, 0.35), 45)
            else:
                _rond_simple(k, rng, x, z, h, w, fam, clair=(i % 2 == 1))
        # deux touffes basses en lisière, côté route
        for j, (x, z) in enumerate(((-6.0, -6.0), (10.5, -5.75))[:1 if v == 2 else 2]):
            k.bloc(x * sx, 1.5 + 0.125 * j, z * sz, 3.0, 1.75, 2.5, vary(c("haie_claire"), rng, 0.04), 30 * j - 15)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 5. Parterres de fleurs (devant les dortoirs)
# ---------------------------------------------------------------------------

FLEURS = [
    ("fleur_rose", "fleur_blanche", "fleur_violette"),
    ("fleur_jaune", "fleur_blanche", "fleur_rose"),
    ("fleur_violette", "fleur_blanche", "fleur_jaune"),
    ("fleur_rose", "fleur_violette", "fleur_blanche"),
]


def parterre(b, longueur: float = 12.0, largeur: float = 3.0, variant: int = 0) -> dict:
    """Parterre de fleurs dans une bordure basse de béton blanc : terre (liseré visible), tapis de feuillage bas,
    deux petits buis ronds aux bouts, taches de fleurs (rose, blanc, jaune, violet) en quinconce sur deux rangs.
    Long de X local, avant vers -Z. ≤ 10 pièces."""
    rng = b.rng
    v = variant % 4
    n0 = len(b.parts)
    w, d = longueur / 2, largeur / 2
    cols = [c(n) for n in FLEURS[v]]
    with b.group("Parterre"):
        b.box((-w, 0, -d), (w, 0.8, d), vary("blanc_casse", rng, 0.02), name="Bordure")
        b.box((-w + 0.3, 0.4, -d + 0.3), (w - 0.3, 0.95, d - 0.3), vary("terre", rng, 0.03), studs="top", name="Terre")
        xb = w - 1.5
        b.box((-xb + 0.75, 0.75, -d + 0.55), (xb - 0.75, 1.25, d - 0.55), vary(mix(c("feuille"), c("haie"), 0.5), rng, 0.03),
              studs="top", collide=False, name="Feuillage")
        for j, x in enumerate((-xb, xb)):
            b.boxc((x, 0.625 + 0.9 - 0.125 * j, 0), (1.75, 1.8, 1.75), vary(c("haie") if j else c("feuille"), rng, 0.04),
                   yaw=45, studs="top", collide=False, name="Buis")
        # fleurs : 5 taches en quinconce sur le tapis de feuillage
        utile = 2 * (xb - 0.75) - 1.5
        for i in range(5):
            rang = i % 2
            x = -utile / 2 + utile * i / 4
            z = (-0.35 if rang == 0 else 0.35) * (largeur / 3.0)
            hfl = 0.375 + 0.125 * ((i * 2) % 3)
            b.box((x - 0.6, 1.0, z - 0.45), (x + 0.6, 1.25 + hfl, z + 0.45), cols[i % 3], studs="top",
                  collide=False, shadow=False, name="Fleurs")
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 6. Rochers (terrains d'entraînement)
# ---------------------------------------------------------------------------

def rocher(b, variant: int = 0) -> dict:
    """Petit groupe de rochers (≈ 3 studs de haut, emprise ≈ 4 × 4), blocs tournés en 3 tons de roche, studs sur
    les dessus. 0 amas arrondi, 1 dalles empilées, 2 pierre dressée et cailloux. ≤ 6 pièces."""
    rng = b.rng
    v = variant % 3
    n0 = len(b.parts)
    g0, g1, g2 = c("roche"), c("roche_claire"), c("roche_fonce")

    def R(cx, y0, cz, sx, sy, sz, col, yaw, **kw):
        kw.setdefault("studs", "top")
        kw.setdefault("name", "Rocher")
        return b.boxc((cx, y0 + sy / 2, cz), (sx, sy, sz), vary(col, rng, 0.03), yaw=yaw, **kw)

    with b.group("Rocher"):
        if v == 0:  # amas arrondi : deux blocs croisés, chapeau clair, deux galets
            R(0, 0, 0, 3.0, 2.25, 2.5, g0, 12)
            R(0.2, 0, -0.1, 2.5, 2.75, 2.75, g2, 57)
            R(-0.1, 2.25, 0.1, 1.75, 0.75, 1.5, g1, 25)
            R(1.5, 0, 1.0, 1.25, 1.0, 1.0, g1, -20)
            R(-1.6, 0, -1.1, 1.0, 0.625, 0.9, g0, 40)
        elif v == 1:  # dalles empilées, en gradins
            R(0, 0, 0, 3.75, 1.25, 3.0, g2, 8)
            R(-0.25, 1.0, 0.25, 2.75, 1.0, 2.25, g0, 28)
            R(0.25, 1.75, 0, 1.75, 1.0, 1.5, g1, -10)
            R(1.5, 0, -1.4, 1.0, 0.75, 0.9, g0, 35)
            R(-1.5, 0, 1.3, 0.9, 0.5, 0.8, g1, -25)
        else:  # pierre dressée et cailloux
            R(0, 0, 0, 1.5, 3.25, 1.25, g0, 10)
            R(0.1, 0, -0.1, 1.1, 2.75, 1.6, g2, 55)
            R(0.05, 3.0, 0.0, 1.0, 0.5, 0.9, g1, 25)
            R(1.4, 0, 0.9, 1.5, 0.875, 1.25, g1, -25)
            R(-1.3, 0, -0.9, 1.1, 0.625, 1.0, g0, 40)
            R(-0.8, 0, 1.5, 0.75, 0.375, 0.7, g2, 15)
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# Planche de contrôle
# ---------------------------------------------------------------------------

def planche(b, variant: int = 0, partie: int = 0) -> dict:
    """Plusieurs objets alignés pour un seul rendu de contrôle (apercu.py assets.vegetation:planche).
    `partie` 0 : conifères et arbres ronds ; 1 : haies, parterres, rochers ; 2 : bosquets ; 3 : rangée d'avenue ;
    4 : conifères seuls ; 5 : arbres ronds seuls."""
    n = {}
    if partie == 0:
        items = [(conifere, {"variant": i, "taille": t}, 5.5) for i in range(3) for t in (1.0, 1.3)]
        items += [(arbre_rond, {"variant": i, "taille": 1.0}, 10) for i in range(4)]
    elif partie == 1:
        items = [(haie, {"longueur": 11.5, "variant": 0}, 12), (haie, {"longueur": 24, "variant": 1}, 24),
                 (parterre, {"variant": 0}, 12), (parterre, {"variant": 1}, 12)]
        items += [(rocher, {"variant": i}, 5) for i in range(3)]
    elif partie == 2:
        items = [(bosquet, {"variant": i}, 36) for i in range(3)]
    elif partie == 4:
        items = [(conifere, {"variant": i, "taille": t}, 4.5) for i in range(3) for t in (1.0, 1.3)]
    elif partie == 5:
        items = [(arbre_rond, {"variant": i, "taille": 1.0}, 8.5) for i in range(4)]
    else:
        items = []
    x = 0.0
    for fn, kw, w in items:
        n0 = len(b.parts)
        with b.at((x + w / 2, 0, 0)):
            fn(b, **kw)
        n[f"{fn.__name__}{kw.get('variant', '')}"] = len(b.parts) - n0
        x += w + 2
    if partie == 3:  # coupe de l'avenue : haie, conifères à gauche, haie et arbres ronds à droite (z = longueur)
        for s in (-1, 1):
            with b.at((s * 8, 0, 0), yaw=90):
                haie(b, longueur=40, variant=0 if s < 0 else 1)
        for i in range(5):
            with b.at((-13.5, 0, -16 + 8 * i)):
                conifere(b, variant=i % 3, taille=1.0 + 0.15 * (i % 3))
        for i, z in enumerate((-15, -5, 5, 15)):
            with b.at((14.5, 0, z)):
                arbre_rond(b, variant=i % 3, taille=1.0 if i % 2 else 0.85)
    return {"pieces_par_objet": n}
