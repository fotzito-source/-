"""Port pirate de la zone 2 (mer de l'Est) : galions, caravelle, barques, phare rayé et pontons, en style stud.

Navires génériques de dessin animé, sans nom, sans emblème d'équipage et sans figure de proue reconnaissable
(proue à simple volute) ; pavillons : `mobilier.drapeau_pirate` uniquement.

Repères :
- navires et barques : origine au centre de la coque **à la flottaison** (y = 0 local = surface de l'eau), coque le
  long de Z, **proue vers -Z local** ; la zone les pose en y = -1,5, le dessus du quai est donc en y = +1,5 local.
  La coque descend 1,5 sous la flottaison ; un mince anneau d'écume l'entoure (y 0 → 0,15).
- phare : origine au centre de l'îlot, dessus de l'îlot en y = 0 (l'eau est en y = -1,5) ; palier plat côté -X
  pour la jetée (x local ≤ -10).
- pontons : origine au milieu du bout côté quai, plancher à y = 0, le ponton s'étend vers -Z local.

Les voiles sont « gonflées » : trois tranches décalées (ventre vers la proue, vent arrière : flammes et pavillons
flottent aussi vers la proue). Les vergues sont brassées (`brasse`, en degrés) pour que les voiles se lisent de face
depuis le couloir : galion (proue vers -Z monde) +25°, le dos des voiles regarde les joueurs qui arrivent et le ventre
ceux qui reviennent ; caravelle (posée à yaw 180, proue vers +Z monde) -25°, le ventre regarde les joueurs qui arrivent.

Rien ne dépend de la largeur du couloir : la zone règle `passerelle` (distance du centre du navire à la margelle du
quai) et `longueur` des pontons et de la jetée selon l'alignement des quais.
"""

from __future__ import annotations

import math

import numpy as np

from assets.mobilier import barre_navire, bitte, bouee, caisses, cordage, drapeau_pirate, filet_peche, tonneaux
from kit import mix, rot_x, rot_z, shade
from palette import c, vary

ND = dict(collide=False)            # petit détail sans collision
NDS = dict(collide=False, shadow=False)


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------


class _Ech:
    """Builder à l'échelle : toutes les coordonnées et tailles sont multipliées par `s` (navires de longueur variable)."""

    def __init__(self, b, s: float):
        self.b, self.s, self.rng = b, float(s), b.rng

    def v(self, p):
        return tuple(float(x) * self.s for x in p)

    def box(self, a, bb, col, **kw):
        return self.b.box(self.v(a), self.v(bb), col, **kw)

    def boxc(self, ctr, size, col, yaw: float = 0.0, **kw):
        return self.b.boxc(self.v(ctr), self.v(size), col, yaw=yaw, **kw)

    def wedge(self, a, bb, col, down: str = "-z", **kw):
        return self.b.wedge(self.v(a), self.v(bb), col, down=down, **kw)

    def wedge_under(self, a, bb, col, down: str = "-z", **kw):
        return self.b.wedge_under(self.v(a), self.v(bb), col, down=down, **kw)

    def cyl(self, ctr, r, h, col, axis: str = "y", **kw):
        return self.b.cyl(self.v(ctr), r * self.s, h * self.s, col, axis=axis, **kw)

    def ball(self, ctr, r, col, **kw):
        return self.b.ball(self.v(ctr), r * self.s, col, **kw)

    def part(self, shape, size, ctr, R, col, **kw):
        return self.b.part(shape, self.v(size), self.v(ctr), R, col, **kw)

    def at(self, pos=(0, 0, 0), yaw: float = 0.0, group=None):
        return self.b.at(self.v(pos), yaw=yaw, group=group)

    def group(self, name):
        return self.b.group(name)


def _seg(S, a, bb, r, col, name="Corde", **kw):
    """Cylindre de a à bb (cordages, beaupré, vergue de voile latine)."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    d = bb - a
    n = float(np.linalg.norm(d))
    if n < 1e-3:
        return None
    x = d / n
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    kw.setdefault("collide", False)
    return S.part("cyl", (n + r * 0.6, 2 * r, 2 * r), (a + bb) / 2, np.column_stack([x, y, z]), col, name=name, **kw)


def _poutre(S, a, bb, ep, haut, col, name="Poutre", **kw):
    """Bloc de section ep × haut de a à bb (a et bb dans un même plan vertical ; ép. horizontale perpendiculaire)."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    d = bb - a
    n = float(np.linalg.norm(d))
    x = d / n
    h = np.array([d[0], 0.0, d[2]])
    if np.linalg.norm(h) < 1e-6:
        h = np.array([1.0, 0.0, 0.0])
    z = np.cross(x, np.array([0.0, 1.0, 0.0])) if abs(x[1]) < 0.999 else np.array([0.0, 0.0, 1.0])
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return S.part("block", (n, haut, ep), (a + bb) / 2, np.column_stack([x, y, z]), col, name=name, **kw)


def _coin_plan(S, cx, cz, lx, lz, y0, y1, col, studs=False, **kw):
    """Coin « vu de dessus » : son profil horizontal est un triangle rectangle, angle droit en (cx, cz), un côté de
    longueur signée lx le long de X, l'autre de longueur signée lz le long de Z ; épaisseur de y0 à y1.
    Sert aux proues en pointe et aux coins de pont. `studs=True` met des studs sur la face du dessus."""
    Y = np.array([math.copysign(1.0, lx), 0.0, 0.0])
    Z = np.array([0.0, 0.0, -math.copysign(1.0, lz)])
    X = np.cross(Y, Z)
    R = np.column_stack([X, Y, Z])
    faces = (("Right",) if X[1] > 0 else ("Left",)) if studs else ()
    return S.part("wedge", (y1 - y0, abs(lx), abs(lz)), (cx + lx / 2, (y0 + y1) / 2, cz + lz / 2), R, col,
                  studs=faces, **kw)


def _etage(S, y0, y1, hw, z_av, z_ar, l_proue, col, studs=False, poupe_ronde=False, name="Coque", **kw):
    """Tranche de coque : bloc de z_av à z_ar (demi-largeur hw), proue en pointe jusqu'à z_av - l_proue,
    poupe carrée ou ronde (demi-cylindre de rayon hw)."""
    st = "top" if studs else ()
    S.box((-hw, y0, z_av), (hw, y1, z_ar), col, studs=st, name=name, **kw)
    if l_proue > 0:
        for sg in (-1, 1):
            _coin_plan(S, 0, z_av, sg * hw, -l_proue, y0, y1, col, studs=studs, name=name, **kw)
    if poupe_ronde:
        S.cyl((0, (y0 + y1) / 2, z_ar), hw, y1 - y0, col, studs=st, name=name, **kw)


def _rambarde(S, p0, p1, y, col_pot, col_rampe, h=1.6, pas=2.4, bouts=True, name="Rambarde"):
    """Garde-corps (poteaux + main courante) en ligne droite de p0 = (x, z) à p1, posé à la hauteur y."""
    (x0, z0), (x1, z1) = p0, p1
    L = math.hypot(x1 - x0, z1 - z0)
    n = max(1, round(L / pas))
    yaw = math.degrees(math.atan2(-(z1 - z0), x1 - x0))
    for i in range(0 if bouts else 1, n + 1 if bouts else n):
        t = i / n
        S.boxc((x0 + (x1 - x0) * t, y + h / 2, z0 + (z1 - z0) * t), (0.3, h, 0.3), col_pot, yaw=yaw, name="Balustre", **ND)
    S.boxc(((x0 + x1) / 2, y + h + 0.15, (z0 + z1) / 2), (L + 0.3, 0.3, 0.45), col_rampe, yaw=yaw, name="MainCourante",
           **ND)


def _fanal(S, x, y, z, cadre, t=1.0, name="Fanal"):
    """Fanal de navire : socle, verre éclairé (Neon), chapeau et pomme dorée (4 pièces), posé en y."""
    S.box((x - 0.6 * t, y, z - 0.6 * t), (x + 0.6 * t, y + 0.3 * t, z + 0.6 * t), cadre, name=name, **ND)
    S.box((x - 0.45 * t, y + 0.3 * t, z - 0.45 * t), (x + 0.45 * t, y + 1.6 * t, z + 0.45 * t), c("lanterne"),
          material="Neon", name=name, **NDS)
    S.box((x - 0.65 * t, y + 1.6 * t, z - 0.65 * t), (x + 0.65 * t, y + 1.95 * t, z + 0.65 * t), cadre, name=name, **ND)
    S.ball((x, y + 2.15 * t, z), 0.3 * t, c("or"), name=name, **ND)


def _voile(S, y_haut, y_bas, larg, col, ombre, z0=-1.4, bande=None, name="Voile"):
    """Voile carrée gonflée (repère du mât, vergue le long de X) : dos plein en `ombre`, deux tranches de plus en plus
    étroites poussées vers la proue (-Z) en `col`. `bande` : couleur d'une bande horizontale (voiles rayées)."""
    h = y_haut - y_bas
    d1, d2 = max(0.8, 0.09 * h), max(1.5, 0.19 * h)
    tr = [((-larg / 2, y_bas, z0 - 0.2), (larg / 2, y_haut, z0 + 0.2), ombre),
          ((-larg * 0.4, y_bas + 0.1 * h, z0 - d1), (larg * 0.4, y_haut - 0.05 * h, z0 + 0.35), col),
          ((-larg * 0.25, y_bas + 0.24 * h, z0 - d2), (larg * 0.25, y_haut - 0.22 * h, z0 - d1 + 0.1), shade(col, 1.05))]
    for a, bb, cc in tr:
        S.box(a, bb, cc, name=name, **ND)
    if bande is not None:
        yb0, yb1 = y_bas + 0.36 * h, y_bas + 0.52 * h
        for k, (a, bb, _) in enumerate(tr):
            ya, yb = max(a[1], yb0), min(bb[1], yb1)
            e = 0.12 + 0.02 * k
            S.box((a[0] - 0.05, ya, a[2] - e), (bb[0] + 0.05, yb, bb[2] + e), bande, name="Bande", **ND)
    S.cyl((0, y_haut + 0.35, z0), 0.38, larg + 1.4, c("bois_fonce"), axis="x", name="Vergue", **ND)
    # racage : collier qui tient la vergue contre le mât (aucun jour entre les deux)
    S.box((-0.3, y_haut + 0.05, z0), (0.3, y_haut + 0.65, -0.2), c("bois_fonce"), name="Racage", **NDS)


def _voile_ferlee(S, y_vergue, larg, col, z0=-1.4):
    """Voile ferlée sur sa vergue (navire au mouillage) : vergue, rouleau de toile, deux rabans."""
    S.cyl((0, y_vergue, z0), 0.38, larg + 1.4, c("bois_fonce"), axis="x", name="Vergue", **ND)
    S.box((-0.3, y_vergue - 0.3, z0), (0.3, y_vergue + 0.3, -0.2), c("bois_fonce"), name="Racage", **NDS)
    S.cyl((0, y_vergue - 0.75, z0), 0.62, larg * 0.92, col, axis="x", name="VoileFerlee", **ND)
    for x in (-larg * 0.25, larg * 0.25):
        S.cyl((x, y_vergue - 0.75, z0), 0.7, 0.35, c("corde"), axis="x", name="Raban", **NDS)


def _mat(S, z, y0, y_hune, y_top, r=0.9, hune=1.9, nid=False, bois=None):
    """Mât en deux tronçons (bas-mât et mât de hune plus fin), hune (plateforme), pomme ; nid-de-pie en option."""
    bois = bois or c("bois_fonce")
    S.cyl((0, (y0 + y_hune + 0.8) / 2, z), r, y_hune + 0.8 - y0, bois, name="BasMat")
    S.cyl((0, (y_hune + y_top) / 2, z), r * 0.66, y_top - y_hune, shade(bois, 1.1), name="MatHune")
    S.cyl((0, y_hune + 0.25, z), hune, 0.5, c("bois"), studs="top", name="Hune", **ND)
    S.ball((0, y_top + 0.25, z), r * 0.75, c("or"), name="Pomme", **ND)
    if nid:
        yn = nid
        S.cyl((0, yn + 1.25, z), 2.2, 2.5, c("bois"), name="NidDePie", **ND)
        S.cyl((0, yn + 2.45, z), 2.35, 0.35, c("bois_fonce"), name="NidDePie", **ND)
        S.cyl((0, yn + 0.1, z), 2.35, 0.3, c("bois_fonce"), name="NidDePie", **ND)


def _haubans(S, z, y_pied, hw, y_hune, hune, y_top, cote=(-1, 1), col=None, enfle=4, dz=2.6):
    """Haubans en éventail du pavois à la hune (trois par bord), `enfle` enfléchures (échelons de corde) entre eux,
    et un galhauban de la hune vers le haut du mât de hune."""
    col = col or c("corde_fonce")
    for sg in cote:
        pieds = [np.array((sg * hw, y_pied, z + d)) for d in (-dz, 0.0, dz)]
        tete = np.array((sg * hune * 0.8, y_hune, z))
        for pd in pieds:
            _seg(S, pd, tete, 0.14, col, name="Hauban", **NDS)
        for k in range(enfle):
            t = (k + 0.7) / (enfle + 0.6)
            a, bb = pieds[0] + (tete - pieds[0]) * t, pieds[2] + (tete - pieds[2]) * t
            _seg(S, a, bb, 0.08, c("corde"), name="Enflechure", **NDS)
        _seg(S, (sg * hune * 0.9, y_hune + 0.5, z), (0, y_top - 2.5, z), 0.1, col, name="Hauban", **NDS)


def _flamme(S, x, y, z, long, col, sens=-1):
    """Flamme (longue banderole triangulaire) qui flotte vers l'avant (sens = -1, vent arrière comme les voiles)
    ou vers l'arrière (sens = +1)."""
    z0, z1 = sorted((z, z + sens * long))
    S.wedge((x - 0.08, y - 1.1, z0), (x + 0.08, y, z1), col, down="-z" if sens < 0 else "+z", name="Flamme", **NDS)


def _ecume(S, hw, z_av, z_ar, l_proue, ronde=False, marge=0.9):
    """Anneau d'écume à la flottaison (y 0 → 0,15) autour de la tranche basse de la coque."""
    k = (hw + marge) / hw
    col = c("ecume")
    for sg in (-1, 1):
        S.box((sg * hw, 0, z_av), (sg * (hw + marge), 0.15, z_ar), col, name="Ecume", **NDS)
        _coin_plan(S, 0, z_av, sg * (hw + marge), -l_proue * k, 0, 0.15, col, name="Ecume", **NDS)
    if ronde:
        S.cyl((0, 0.075, z_ar), hw + marge, 0.15, col, name="Ecume", **NDS)
    else:
        S.box((-hw - marge, 0, z_ar), (hw + marge, 0.15, z_ar + marge), col, name="Ecume", **NDS)


def _ancre_suspendue(S, sg, x, y, z, col, t=1.0):
    """Ancre pendue au bossoir contre le bordé (plan y-z), côté sg ; (x, y, z) = haut de la verge."""
    with S.group("Ancre"):
        S.box((x - 0.25 * t, y - 4.2 * t, z - 0.25 * t), (x + 0.25 * t, y, z + 0.25 * t), col, name="Verge", **ND)
        S.box((x - 0.35 * t, y - 0.8 * t, z - 1.6 * t), (x + 0.35 * t, y - 0.4 * t, z + 1.6 * t), c("bois_fonce"),
              name="Jas", **ND)
        for s2 in (-1, 1):
            S.part("block", (0.5 * t, 0.45 * t, 2.2 * t), (x, y - 3.85 * t, z + s2 * 0.9 * t), rot_x(-s2 * 35), col,
                   name="Bras", **ND)
        S.cyl((x, y + 0.3 * t, z), 0.4 * t, 0.25 * t, c("fer"), axis="x", name="Organeau", **ND)


def _passerelle(b, x0, y0, x1, y1, larg=3.0):
    """Passerelle de planches (coordonnées réelles, plan x-y à z = 0) du pont (x0, y0) au quai (x1, y1),
    tasseaux, quatre poteaux et deux mains courantes de corde."""
    with b.group("Passerelle"):
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        R = rot_z(ang)
        b.part("block", (L + 0.6, 0.4, larg), ((x0 + x1) / 2, (y0 + y1) / 2 + 0.2, 0), R, c("bois_pale"), name="Planche")
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        nx, ny = -uy, ux                       # normale (vers le haut) au plan de la passerelle
        n = max(3, int(L // 1.6))
        for i in range(1, n):
            t = i / n
            px, py = x0 + (x1 - x0) * t + nx * 0.5, y0 + (y1 - y0) * t + ny * 0.5
            b.part("block", (0.3, 0.2, larg - 0.4), (px, py, 0), R, c("bois_fonce"), name="Tasseau", **ND)
        tops = []
        for (px, py) in ((x0 + 0.4, y0), (x1 - 0.5, y1)):
            for sz in (-1, 1):
                zz = sz * (larg / 2 + 0.15)
                b.box((px - 0.2, py, zz - 0.2), (px + 0.2, py + 3.2, zz + 0.2), c("bois_fonce"), name="Poteau", **ND)
                tops.append((px, py + 3.0, zz))
        for sz_i in (0, 1):
            a, bb = tops[sz_i], tops[2 + sz_i]
            cordage(b, a, bb, creux=0.9, n=3, rayon=0.12)


# ---------------------------------------------------------------------------
# Galion
# ---------------------------------------------------------------------------

_GALION = {
    0: dict(coque="coque_rouge", haut="coque_rouge", liseré="or", voile="voile", ombre="voile_ombre", pont="bois_quai"),
    1: dict(coque="coque_noire", haut="coque_noire", liseré="rouge", voile="blanc", ombre="voile_ombre", pont="bois_clair"),
    2: dict(coque="bois_fonce", haut="bois", liseré="or", voile="voile_rouge", ombre="rouge_fonce", pont="bois_quai"),
}


def galion(b, variant: int = 0, longueur: float = 72, passerelle: float = 0.0, brasse: float = 25.0) -> dict:
    """Grand galion pirate de dessin animé, coque en gradins, trois mâts à voiles gonflées.

    Origine au centre de la coque à la flottaison, proue vers -Z. `longueur` (beaupré compris) met tout à l'échelle
    (référence 72). `passerelle` > 0 : passerelle côté +X jusqu'à x = passerelle (posée sur le quai, y = +1,5).
    Variantes : 0 coque brun-rouge, liseré or, voiles crème ; 1 coque noire, liseré rouge, voiles blanches ;
    2 coque de bois sombre, liseré or, voiles rouges (basses voiles ferlées, au mouillage)."""
    v = variant % 3
    P = _GALION[v]
    s = longueur / 72.0
    S = _Ech(b, s)
    rng = b.rng
    coque, haut, lis = c(P["coque"]), c(P["haut"]), c(P["liseré"])
    voile, ombre = c(P["voile"]), c(P["ombre"])
    if v == 1:
        voile, ombre = c("blanc"), shade(c("blanc"), 0.9)
    bois_f = c("bois_fonce")
    pont = P["pont"]
    bande = shade(ombre, 0.93) if v != 2 else c("rouge_fonce")      # bande de ris sur les basses voiles

    # Cotes (repère de référence, longueur 72)
    HW = 10.5             # demi-largeur de la coque
    Y_PONT = 9.0          # pont principal (embelle)
    Y_GAIL = 13.5         # gaillard d'avant
    Y_DUN = 15.0          # dunette (château arrière)
    Y_POUPE = 19.0        # pont de poupe
    Z_GAIL, Z_DUN, Z_POUPE = -12.0, 14.0, 24.0

    with S.group("Coque"):
        # tranche basse (sous la flottaison et bouchain), sombre
        _etage(S, -1.5, 1.0, 8.5, -20, 29, 7, shade(coque, 0.72), name="Carene")
        for sg in (-1, 1):
            xa, xb = sorted((sg * 8.5, sg * HW))
            S.wedge_under((xa, 1.0, -20), (xb, 3.0, 29), shade(coque, 0.82), down="+x" if sg > 0 else "-x",
                          name="Bouchain")
            _coin_plan(S, 0, -20, sg * 9.6, -8.2, 1.0, 3.0, shade(coque, 0.82), name="Bouchain")
        S.wedge_under((-8.5, 1.0, 29), (8.5, 3.0, 31), shade(coque, 0.82), down="+z", name="Bouchain")
        # bordé principal en trois virures, de plus en plus longues vers l'avant (étrave inclinée)
        for (y0, y1, za, lp, f) in ((3.0, 5.0, -21, 8.0, 0.9), (5.0, 7.0, -22, 8.5, 1.0), (7.0, Y_PONT, -22, 9.5, 0.94)):
            _etage(S, y0, y1, HW, za, 31, lp, vary(shade(coque, f), rng, 0.03), name="Borde")
        # préceinte dorée (bande) sur les flancs et la proue
        k = (HW + 0.25) / HW
        for sg in (-1, 1):
            xa, xb = sorted((sg * HW, sg * (HW + 0.25)))
            S.box((xa, 7.2, -22), (xb, 8.0, 31), lis, name="Preceinte")
            _coin_plan(S, 0, -22, sg * (HW + 0.25), -9.5 * k, 7.2, 8.0, lis, name="Preceinte")
        for sg in (-1, 1):
            xa, xb = sorted((sg * HW, sg * (HW + 0.2)))
            S.box((xa, 3.0, -21), (xb, 3.4, 31), lis, name="Preceinte", **ND)
            _coin_plan(S, 0, -21, sg * (HW + 0.2), -8.0 * (HW + 0.2) / HW, 3.0, 3.4, lis, name="Preceinte", **ND)
        # gaillard d'avant
        _etage(S, Y_PONT, Y_GAIL, HW, -22, Z_GAIL, 11.5, shade(haut, 1.06), name="Gaillard")
        # dunette, débordant à l'arrière, et pont de poupe
        S.box((-HW, Y_PONT, Z_DUN), (HW, Y_DUN, 33), shade(haut, 1.06), name="Dunette")
        S.wedge_under((-HW, 7.0, 31), (HW, Y_PONT, 33), shade(coque, 0.94), down="+z", name="Voute")
        S.box((-9.5, Y_DUN, Z_POUPE), (9.5, Y_POUPE, 34.5), shade(haut, 1.12), name="Poupe")
        S.wedge_under((-9.5, Y_DUN - 1.5, 33), (9.5, Y_DUN, 34.5), shade(haut, 0.95), down="+z", name="Voute")
        # pilastres dorés aux angles du miroir et fronton sculpté au-dessus de la poupe
        for sg in (-1, 1):
            xa, xb = sorted((sg * (HW - 0.7), sg * (HW + 0.2)))
            S.box((xa, Y_PONT, 33), (xb, Y_DUN - 0.5, 33.25), lis, name="Pilastre", **ND)
            xa, xb = sorted((sg * 8.8, sg * 9.7))
            S.box((xa, Y_DUN, 34.5), (xb, Y_POUPE - 0.5, 34.75), lis, name="Pilastre", **ND)
        S.box((-3.0, Y_POUPE, 34.1), (3.0, Y_POUPE + 3.2, 34.6), shade(haut, 1.15), name="Fronton", **ND)
        for sg in (-1, 1):
            xa, xb = sorted((sg * 3.0, sg * 5.2))
            S.wedge((xa, Y_POUPE, 34.1), (xb, Y_POUPE + 3.2, 34.6), shade(haut, 1.15), down="+x" if sg > 0 else "-x",
                    name="Fronton", **ND)
        S.box((-1.6, Y_POUPE + 0.8, 34.6), (1.6, Y_POUPE + 2.6, 34.8), lis, name="Cartouche", **ND)
        S.box((-3.2, Y_POUPE + 3.2, 34.0), (3.2, Y_POUPE + 3.5, 34.7), lis, name="Fronton", **ND)
        S.ball((0, Y_POUPE + 3.9, 34.35), 0.55, lis, name="Pomme", **ND)
        # liserés dorés des châteaux
        for (y0, z0_, z1_, hw) in ((Y_GAIL - 0.5, -22, Z_GAIL, HW), (Y_DUN - 0.5, Z_DUN, 33, HW),
                                   (Y_POUPE - 0.5, Z_POUPE, 34.5, 9.5)):
            for sg in (-1, 1):
                xa, xb = sorted((sg * hw, sg * (hw + 0.2)))
                S.box((xa, y0, z0_), (xb, y0 + 0.5, z1_), lis, name="Lisere", **ND)
        for sg in (-1, 1):
            _coin_plan(S, 0, -22, sg * (HW + 0.2), -11.5 * (HW + 0.2) / HW, Y_GAIL - 0.5, Y_GAIL, lis, name="Lisere", **ND)
        S.box((-HW - 0.2, Y_DUN - 0.5, 33), (HW + 0.2, Y_DUN, 33.2), lis, name="Lisere", **ND)
        S.box((-9.7, Y_POUPE - 0.5, 34.5), (9.7, Y_POUPE, 34.7), lis, name="Lisere", **ND)
        # étrave dorée qui suit la proue inclinée puis se relève en crosse, volute de proue (sans figure)
        _poutre(S, (0, 0.2, -27.6), (0, Y_GAIL, -34.2), 0.8, 1.0, lis, name="Etrave", **ND)
        _poutre(S, (0, Y_GAIL - 0.3, -34.1), (0, 16.4, -35.3), 0.8, 1.0, lis, name="Etrave", **ND)
        S.cyl((0, 16.3, -35.6), 1.05, 1.0, lis, axis="x", name="Volute", **ND)
        S.cyl((0, 16.3, -35.6), 0.5, 1.3, shade(lis, 0.75), axis="x", name="Volute", **ND)
        # lisses de l'éperon : deux barres dorées du bordé à l'étrave, sous le beaupré
        for sg in (-1, 1):
            _poutre(S, (sg * 3.2, 9.6, -29.0), (sg * 0.3, 13.4, -33.8), 0.4, 0.5, lis, name="Eperon", **ND)

    with S.group("Sabords"):
        for sg in (-1, 1):
            for i in range(7):
                z = -16 + 6 * i
                x_out = sg * HW
                xa, xb = sorted((x_out - sg * 0.5, x_out + sg * 0.35))
                S.box((xa, 4.35, z - 0.95), (xb, 6.25, z + 0.95), shade(coque, 0.55), name="Cadre", **ND)
                xa, xb = sorted((x_out - sg * 0.3, x_out + sg * 0.45))
                S.box((xa, 4.5, z - 0.8), (xb, 6.1, z + 0.8), c("noir"), name="Sabord", **ND)
                S.cyl((x_out + sg * 0.6, 5.3, z), 0.42, 0.8, c("metal_fonce"), axis="x", name="Canon", **ND)
                # mantelet relevé (rouge vif) au-dessus du sabord
                S.part("block", (0.25, 1.7, 1.8), (x_out + sg * 0.55, 6.85, z), rot_z(-sg * 35),
                       c("rouge") if v != 1 else c("blanc"), name="Mantelet", **ND)
        # bouteilles : galeries de quart en saillie sur les flancs du château arrière (toit, cul-de-lampe, fenêtres)
        for sg in (-1, 1):
            xo = sg * (HW + 0.7)
            xa, xb = sorted((sg * HW, xo))
            S.box((xa, 10.0, 21.0), (xb, 14.2, 31.0), shade(haut, 1.14), name="Bouteille")
            S.wedge((xa, 14.2, 21.0), (xb, 15.0, 31.0), lis, down="+x" if sg > 0 else "-x", name="Bouteille", **ND)
            S.wedge_under((xa, 8.6, 21.0), (xb, 10.0, 31.0), shade(haut, 0.95), down="+x" if sg > 0 else "-x",
                          name="Bouteille", **ND)
            for z in (23.0, 26.0, 29.0):
                xa, xb = sorted((xo - sg * 0.05, xo + sg * 0.15))
                S.box((xa, 10.6, z - 1.1), (xb, 13.6, z + 1.1), bois_f, name="Cadre", **ND)
                xa, xb = sorted((xo - sg * 0.1, xo + sg * 0.3))
                S.box((xa, 10.9, z - 0.75), (xb, 13.3, z + 0.75), c("fenetre_lumiere"), material="Neon",
                      name="Fenetre", **NDS)

    with S.group("Poupe"):
        # rangée de fenêtres du château arrière (miroir) et de la poupe
        for x in (-6.4, -3.2, 0.0, 3.2, 6.4):
            S.box((x - 1.1, 10.3, 32.95), (x + 1.1, 13.6, 33.2), bois_f, name="Cadre", **ND)
            S.box((x - 0.75, 10.6, 32.9), (x + 0.75, 13.3, 33.35), c("fenetre_lumiere"), material="Neon",
                  name="Fenetre", **NDS)
        for x in (-4.5, -1.5, 1.5, 4.5):
            S.box((x - 1.0, 15.6, 34.45), (x + 1.0, 18.0, 34.7), bois_f, name="Cadre", **ND)
            S.box((x - 0.65, 15.9, 34.4), (x + 0.65, 17.7, 34.85), c("fenetre_lumiere"), material="Neon",
                  name="Fenetre", **NDS)
        # galerie de poupe : balcon sur consoles devant les fenêtres du miroir, balustres et main courante dorée
        S.box((-8.6, 9.4, 33.0), (8.6, 9.9, 35.6), shade(haut, 1.1), studs="top", name="Balcon")
        for x in (-6.0, 0.0, 6.0):
            S.wedge_under((x - 0.4, 7.6, 33.0), (x + 0.4, 9.4, 35.2), lis, down="+z", name="Console", **ND)
        for x in (-8.3, -4.8, -1.6, 1.6, 4.8, 8.3):
            S.box((x - 0.18, 9.9, 35.1), (x + 0.18, 11.3, 35.45), lis, name="Balustre", **ND)
        S.box((-8.6, 11.3, 35.0), (8.6, 11.65, 35.6), lis, name="MainCourante", **ND)
        for sg in (-1, 1):
            xa, xb = sorted((sg * 8.25, sg * 8.6))
            S.box((xa, 11.3, 33.0), (xb, 11.65, 35.0), lis, name="MainCourante", **ND)
        # fanaux de poupe sur consoles
        for sg in (-1, 1):
            S.box((sg * 8.4 - 0.4, Y_POUPE + 0.25, 33.6), (sg * 8.4 + 0.4, Y_POUPE + 2.2, 34.4), bois_f, name="Console", **ND)
            _fanal(S, sg * 8.4, Y_POUPE + 2.2, 34.0, c("fer"), t=1.3)

    with S.group("Ponts"):
        def planches(x0, x1, y, z0, z1, n=3):
            w = (x1 - x0) / n
            for i in range(n):
                col = c(pont) if i % 2 == 0 else c("bois_clair")
                S.box((x0 + i * w, y, z0), (x0 + (i + 1) * w, y + 0.25, z1), vary(col, rng, 0.04), studs="top",
                      name="Pont")
        planches(-9.9, 9.9, Y_PONT, Z_GAIL, Z_DUN)
        planches(-9.9, 9.9, Y_GAIL, -22, Z_GAIL)
        for sg in (-1, 1):
            _coin_plan(S, 0, -22, sg * 9.9, -11.5 * 9.9 / HW, Y_GAIL, Y_GAIL + 0.25, c(pont), studs=True, name="Pont")
        planches(-9.9, 9.9, Y_DUN, Z_DUN, Z_POUPE)
        planches(-8.9, 8.9, Y_POUPE, Z_POUPE, 34.0, n=2)
        # écoutille à caillebotis, cabestan
        for zc in (3.6, 8.6):
            S.box((-1.8, Y_PONT + 0.25, zc - 0.4), (1.8, Y_PONT + 0.9, zc + 0.4), bois_f, name="Chantier", **ND)
        S.cyl((0, Y_PONT + 1.15, 11.0), 1.1, 1.8, c("bois"), name="Cabestan")
        S.cyl((0, Y_PONT + 2.25, 11.0), 1.35, 0.4, bois_f, studs="top", name="Cabestan", **ND)
        S.box((-2.6, Y_PONT + 1.5, 10.8), (2.6, Y_PONT + 1.8, 11.2), c("bois_pale"), name="Barre", **ND)
        S.box((-0.2, Y_PONT + 1.5, 8.4), (0.2, Y_PONT + 1.8, 13.6), c("bois_pale"), name="Barre", **ND)
        # escaliers entre les ponts
        for sg in (-1, 1):
            xa, xb = sorted((sg * 5.5, sg * 8.0))
            S.wedge((xa, Y_PONT + 0.25, Z_GAIL), (xb, Y_GAIL, Z_GAIL + 4.0), c("bois_clair"), down="+z", studs="top",
                    name="Escalier")
            S.wedge((xa, Y_PONT + 0.25, Z_DUN - 5.0), (xb, Y_DUN, Z_DUN), c("bois_clair"), down="-z", studs="top",
                    name="Escalier")
        S.wedge((-1.5, Y_DUN + 0.25, Z_POUPE - 3.5), (1.5, Y_POUPE, Z_POUPE), c("bois_clair"), down="-z", studs="top",
                name="Escalier")

    with S.group("Rambardes"):
        pot, ram = c("bois_clair") if v != 1 else c("bois"), lis
        # pavois de l'embelle (plein), ouvert pour la passerelle à tribord
        for sg in (-1, 1):
            xa, xb = sorted((sg * 9.9, sg * HW))
            zs = [(Z_GAIL, -2.0), (2.0, Z_DUN)] if (sg > 0 and passerelle > 0) else [(Z_GAIL, Z_DUN)]
            for z0_, z1_ in zs:
                S.box((xa, Y_PONT, z0_), (xb, Y_PONT + 1.9, z1_), shade(haut, 1.06), name="Pavois")
                S.box((min(xa, xb) - 0.1, Y_PONT + 1.9, z0_), (max(xa, xb) + 0.1, Y_PONT + 2.2, z1_), ram,
                      name="Lisse", **ND)
        # gaillard d'avant : flancs, pointe, bord arrière
        y = Y_GAIL + 0.25
        for sg in (-1, 1):
            _rambarde(S, (sg * (HW - 0.3), Z_GAIL), (sg * (HW - 0.3), -22), y, pot, ram)
            _rambarde(S, (sg * (HW - 0.3), -22), (0, -32.9), y, pot, ram, bouts=False)
            _rambarde(S, (sg * (HW - 0.3), Z_GAIL + 0.2), (sg * 8.2, Z_GAIL + 0.2), y, pot, ram, bouts=False)
            _rambarde(S, (sg * 5.3, Z_GAIL + 0.2), (sg * 1.2, Z_GAIL + 0.2), y, pot, ram)
        # dunette : flancs et bord avant
        y = Y_DUN + 0.25
        for sg in (-1, 1):
            _rambarde(S, (sg * (HW - 0.3), Z_DUN - 0.2), (sg * (HW - 0.3), Z_POUPE), y, pot, ram)
            _rambarde(S, (sg * 5.3, Z_DUN - 0.2), (sg * 1.0, Z_DUN - 0.2), y, pot, ram)
        # poupe : flancs, arrière, avant
        y = Y_POUPE + 0.25
        for sg in (-1, 1):
            _rambarde(S, (sg * 9.2, Z_POUPE), (sg * 9.2, 34.2), y, pot, ram)
            _rambarde(S, (sg * 9.2, Z_POUPE - 0.0), (sg * 1.8, Z_POUPE), y, pot, ram, bouts=False)
        _rambarde(S, (-8.0, 34.2), (8.0, 34.2), y, pot, ram, bouts=False)

    # Mâture : (z, pied, hune, sommet, vergues [(y_vergue, y_bas, largeur)], nid)
    mats = [
        ("Misaine", -17.0, Y_GAIL, 27.0, 54.0, [(25.5, 16.8, 25.0), (37.5, 29.0, 20.0), (47.0, 40.5, 14.0)], None),
        ("GrandMat", 0.0, Y_PONT, 29.5, 64.0, [(28.0, 14.5, 30.0), (41.0, 32.0, 24.0), (55.0, 48.0, 17.0)], 43.0),
        ("Artimon", 18.0, Y_DUN, 29.0, 48.0, [(28.0, 19.5, 21.0), (38.5, 31.0, 15.0)], None),
    ]
    for nom, zm, y0, yh, yt, vergues, nid in mats:
        with S.group(f"Mature/{nom}"):
            _mat(S, zm, y0, yh, yt, r=0.95 if nom == "GrandMat" else 0.8, hune=2.0, nid=nid)
            with S.at((0, 0, zm), yaw=brasse):
                for i, (yv, yb, larg) in enumerate(vergues):
                    if v == 2 and i == 0:
                        _voile_ferlee(S, yv, larg, shade(voile, 0.9))
                    else:
                        _voile(S, yv - 0.3, yb, larg, voile, ombre, bande=bande if i == 0 else None)
            pied = Y_GAIL if nom == "Misaine" else (Y_PONT + 2.2 if nom == "GrandMat" else Y_DUN - 0.5)
            _haubans(S, zm, pied, HW + 0.2, yh, 2.0, yt)
            # porte-haubans
            yph = Y_DUN - 0.9 if nom == "Artimon" else pied - 1.6
            for sg in (-1, 1):
                xa, xb = sorted((sg * HW, sg * (HW + 0.45)))
                S.box((xa, yph, zm - 2.8), (xb, yph + 0.4, zm + 2.8), bois_f, name="PorteHauban", **ND)

    with S.group("Beaupre"):
        tip = np.array([0.0, 18.3, -37.0])
        _seg(S, (0, Y_GAIL + 0.3, -29.0), tip, 0.6, bois_f, name="Beaupre", collide=True)
        # foc : triangle gonflé entre le beaupré et le mât de misaine
        S.wedge((-0.15, 17.6, -36.0), (0.15, 37.0, -19.0), ombre, down="-z", name="Foc", **ND)
        for sg in (-1, 1):
            xa, xb = sorted((sg * 0.1, sg * 0.55))
            S.wedge((xa, 19.5, -32.0), (xb, 33.5, -20.0), voile, down="-z", name="Foc", **ND)
        # étais
        cr = c("corde_fonce")
        _seg(S, tip, (0, 53.0, -17.0), 0.12, cr, name="Etai", **NDS)
        _seg(S, (0, 63.0, 0.0), (0, 53.5, -17.0), 0.12, cr, name="Etai", **NDS)
        _seg(S, (0, 41.0, 0.0), (0, Y_GAIL + 1.0, -16.0), 0.12, cr, name="Etai", **NDS)
        _seg(S, (0, 47.5, 18.0), (0, 54.0, 0.0), 0.12, cr, name="Etai", **NDS)
        _seg(S, (0, 28.0, 18.0), (0, 18.0, 0.0), 0.12, cr, name="Etai", **NDS)
        for sg in (-1, 1):
            _seg(S, (sg * 9.2, Y_POUPE + 1.8, 33.5), (0, 47.0, 18.0), 0.1, cr, name="Pataras", **NDS)

    # Pavillon au grand mât, flammes aux autres mâts
    with S.at((0, 64.4, 0), yaw=90, group="Pavillon"):
        drapeau_pirate(b, variant=0, hauteur=6.0 * s, largeur=8.5 * s, mat=True)
    _flamme(S, 0, 54.2, -17.4, 7.0, c("rouge"))
    _flamme(S, 0, 48.2, 17.6, 6.0, c("jaune") if v != 2 else c("blanc"))

    # Bouées de sauvetage accrochées au pavois de l'embelle (deux côté quai, une côté large)
    for sg, zb in ((1, -7.5), (1, 7.0), (-1, 0.0)):
        with S.at((sg * (HW + 0.1), 8.4, zb), yaw=-90 * sg, group="Bouees"):
            bouee(b, variant=1, rayon=1.2 * s)

    # Ancres pendues aux bossoirs, des deux bords
    for sg in (-1, 1):
        S.box((sg * HW - (0.4 if sg > 0 else -0.4), 12.0, -21.6), (sg * (HW + 1.0), 12.6, -20.4), bois_f, name="Bossoir", **ND)
        _ancre_suspendue(S, sg, sg * (HW + 0.6), 11.3, -21.0, c("metal_fonce"))

    # Accessoires de pont (taille humaine, non mis à l'échelle)
    with S.at((5.0, Y_GAIL + 0.25, -17.0), yaw=90, group="Pont/Tonneaux"):
        tonneaux(b, variant=1)
    with S.at((-5.8, Y_PONT + 0.25, -7.5), yaw=0, group="Pont/Caisses"):
        caisses(b, variant=0 if v != 2 else 1)
    with S.at((6.5, Y_PONT + 0.25, 7.5), yaw=0, group="Pont/Tonneaux2"):
        tonneaux(b, variant=0)
    with S.at((0, Y_POUPE + 0.25, 28.5), yaw=0, group="Pont/Barre"):
        barre_navire(b, variant=(0, 1, 2)[v], taille=0.65)

    with S.at((0, Y_PONT + 2.1, 6.2), group="Pont/Chaloupe"):
        barque(b, variant=(1, 2, 0)[v], ecume=False)

    with S.group("Ecume"):
        _ecume(S, 8.5, -20, 29, 7)

    if passerelle > 0:
        _passerelle(b, (HW - 0.4) * s, (Y_PONT + 0.25) * s, float(passerelle), 1.5)

    return {"emprise": (2 * max(18 * s, passerelle), 72.0 * s), "hauteur": 70.0 * s}


# ---------------------------------------------------------------------------
# Caravelle
# ---------------------------------------------------------------------------


def caravelle(b, variant: int = 0, longueur: float = 52, passerelle: float = 0.0, brasse: float = -25.0) -> dict:
    """Caravelle pirate à poupe ronde : deux mâts à voiles carrées gonflées et un artimon à voile latine.

    Origine au centre de la coque à la flottaison, proue vers -Z ; `longueur` met tout à l'échelle (référence 52).
    Variantes : 0 coque jaune à liserés rouge et blanc, voiles crème à bande rouge ; 1 coque turquoise, voiles blanches."""
    v = variant % 2
    s = longueur / 52.0
    S = _Ech(b, s)
    rng = b.rng
    if v == 0:
        coque, lis1, lis2 = mix(c("coque_jaune"), c("jaune"), 0.45), c("rouge"), c("blanc")
        voile, ombre, bande = c("voile"), c("voile_ombre"), c("rouge")
    else:
        coque, lis1, lis2 = c("turquoise"), c("blanc"), c("bois_fonce")
        voile, ombre, bande = c("blanc"), shade(c("blanc"), 0.9), None
    bois_f = c("bois_fonce")
    HW = 7.5
    Y_PONT, Y_GAIL, Y_DUN, Y_POUPE = 7.0, 9.5, 11.0, 14.0
    Z_GAIL, Z_DUN, Z_AR = -8.0, 6.0, 14.0

    with S.group("Coque"):
        _etage(S, -1.5, 1.0, 5.8, -13, Z_AR, 6, shade(coque, 0.7), poupe_ronde=True, name="Carene")
        _etage(S, 1.0, 2.5, 6.8, -14, Z_AR, 7, shade(coque, 0.82), poupe_ronde=True, name="Bouchain")
        for (y0, y1, lp, f) in ((2.5, 4.5, 6.5, 0.92), (4.5, Y_PONT, 7.5, 1.0)):
            _etage(S, y0, y1, HW, -15, Z_AR, lp, vary(shade(coque, f), rng, 0.03), poupe_ronde=True, name="Borde")
        # filet blanc au-dessus de la flottaison (tour complet)
        kb = (HW + 0.15) / HW
        S.cyl((0, 2.675, Z_AR), HW + 0.15, 0.35, lis2, name="Filet", **ND)
        for sg in (-1, 1):
            xa, xb = sorted((sg * HW, sg * (HW + 0.15)))
            S.box((xa, 2.5, -15), (xb, 2.85, Z_AR), lis2, name="Filet", **ND)
            _coin_plan(S, 0, -15, sg * (HW + 0.15), -6.5 * kb, 2.5, 2.85, lis2, name="Filet", **ND)
        # liseré rouge (préceinte) qui fait tout le tour
        k = (HW + 0.25) / HW
        S.cyl((0, 5.0, Z_AR), HW + 0.25, 0.8, lis1, name="Preceinte")
        for sg in (-1, 1):
            xa, xb = sorted((sg * HW, sg * (HW + 0.25)))
            S.box((xa, 4.6, -15), (xb, 5.4, Z_AR), lis1, name="Preceinte")
            _coin_plan(S, 0, -15, sg * (HW + 0.25), -7.5 * k, 4.6, 5.4, lis1, name="Preceinte")
        # gaillard d'avant et château arrière rond (deux étages)
        _etage(S, Y_PONT, Y_GAIL, HW, -15, Z_GAIL, 9.0, shade(coque, 1.05), name="Gaillard")
        S.box((-HW, Y_PONT, Z_DUN), (HW, Y_DUN, Z_AR), shade(coque, 1.05), name="Chateau")
        S.cyl((0, (Y_PONT + Y_DUN) / 2, Z_AR), HW, Y_DUN - Y_PONT, shade(coque, 1.05), name="Chateau")
        S.box((-6.0, Y_DUN, 10.0), (6.0, Y_POUPE, Z_AR), shade(coque, 1.1), name="Poupe")
        S.cyl((0, (Y_DUN + Y_POUPE) / 2, Z_AR), 6.0, Y_POUPE - Y_DUN, shade(coque, 1.1), name="Poupe")
        # liserés blancs (v0) au bord des châteaux
        S.cyl((0, Y_DUN - 0.25, Z_AR), HW + 0.2, 0.5, lis2, name="Lisere", **ND)
        S.cyl((0, Y_POUPE - 0.25, Z_AR), 6.2, 0.5, lis2, name="Lisere", **ND)
        for sg in (-1, 1):
            xa, xb = sorted((sg * HW, sg * (HW + 0.2)))
            S.box((xa, Y_DUN - 0.5, Z_DUN), (xb, Y_DUN, Z_AR), lis2, name="Lisere", **ND)
            S.box((xa, Y_GAIL - 0.5, -15), (xb, Y_GAIL, Z_GAIL), lis2, name="Lisere", **ND)
            _coin_plan(S, 0, -15, sg * (HW + 0.2), -9.0 * (HW + 0.2) / HW, Y_GAIL - 0.5, Y_GAIL, lis2, name="Lisere", **ND)
        # étrave inclinée qui se relève en crosse à volute
        _poutre(S, (0, 0.2, -19.4), (0, Y_GAIL, -24.3), 0.7, 0.9, lis1, name="Etrave", **ND)
        _poutre(S, (0, Y_GAIL - 0.3, -24.2), (0, 11.4, -24.9), 0.7, 0.9, lis1, name="Etrave", **ND)
        S.cyl((0, 11.2, -25.15), 0.8, 0.9, lis1, axis="x", name="Volute", **ND)
        S.cyl((0, 11.2, -25.15), 0.38, 1.15, shade(lis1, 0.75), axis="x", name="Volute", **ND)

    with S.group("Sabords"):
        for sg in (-1, 1):
            for z in (-9.0, -4.0, 1.0, 6.0):
                x_out = sg * HW
                S.box((x_out - 0.7 + sg * 0.15, 2.9, z - 0.7), (x_out + 0.7 + sg * 0.15, 4.2, z + 0.7), c("noir"),
                      name="Sabord", **ND)
                S.cyl((x_out + sg * 0.6, 3.55, z), 0.33, 1.0, c("metal_fonce"), axis="x", name="Canon", **ND)
                S.part("block", (0.2, 1.1, 1.5), (x_out + sg * 0.42, 4.6, z), rot_z(-sg * 35), lis2,
                       name="Mantelet", **ND)
        # fenêtres éclairées sur les flancs du château arrière
        for sg in (-1, 1):
            for z in (8.6, 12.2):
                xa, xb = sorted((sg * (HW - 0.1), sg * (HW + 0.15)))
                S.box((xa, 7.9, z - 1.0), (xb, 10.1, z + 1.0), bois_f, name="Cadre", **ND)
                xa, xb = sorted((sg * (HW - 0.05), sg * (HW + 0.3)))
                S.box((xa, 8.2, z - 0.65), (xb, 9.8, z + 0.65), c("fenetre_lumiere"), material="Neon",
                      name="Fenetre", **NDS)
    with S.group("Poupe"):
        # fenêtres sur la poupe ronde (tournées radialement)
        for a in (-40, 0, 40):
            ra = math.radians(a)
            for (y0, y1, r) in ((Y_PONT + 1.0, Y_DUN - 1.1, HW), (Y_DUN + 0.4, Y_POUPE - 0.5, 6.0)):
                cx, cz = r * math.sin(ra), Z_AR + r * math.cos(ra)
                S.boxc((cx, (y0 + y1) / 2, cz), (1.6, y1 - y0 + 0.4, 0.5), bois_f, yaw=a, name="Cadre", **ND)
                cx2, cz2 = (r + 0.12) * math.sin(ra), Z_AR + (r + 0.12) * math.cos(ra)
                S.boxc((cx2, (y0 + y1) / 2, cz2), (1.1, y1 - y0, 0.5), c("fenetre_lumiere"), yaw=a, material="Neon",
                       name="Fenetre", **NDS)
        S.box((-0.3, Y_POUPE, 19.4), (0.3, Y_POUPE + 2.0, 20.0), bois_f, name="Console", **ND)
        _fanal(S, 0, Y_POUPE + 2.0, 19.7, c("fer"), t=1.2)

    with S.group("Ponts"):
        def planches(x0, x1, y, z0, z1, n=3):
            w = (x1 - x0) / n
            for i in range(n):
                col = c("bois_quai") if i % 2 == 0 else c("bois_clair")
                S.box((x0 + i * w, y, z0), (x0 + (i + 1) * w, y + 0.25, z1), vary(col, rng, 0.04), studs="top", name="Pont")
        planches(-6.9, 6.9, Y_PONT, Z_GAIL, Z_DUN)
        planches(-6.9, 6.9, Y_GAIL, -15, Z_GAIL, n=2)
        for sg in (-1, 1):
            _coin_plan(S, 0, -15, sg * 6.9, -9.0 * 6.9 / HW, Y_GAIL, Y_GAIL + 0.25, c("bois_quai"), studs=True, name="Pont")
        planches(-6.9, 6.9, Y_DUN, Z_DUN, 10.0, n=2)
        S.cyl((0, Y_POUPE + 0.125, Z_AR), 5.5, 0.25, c("bois_quai"), studs="top", name="Pont")
        S.box((-5.5, Y_POUPE, 10.0), (5.5, Y_POUPE + 0.25, Z_AR), c("bois_clair"), studs="top", name="Pont")
        S.wedge((-1.5, Y_DUN + 0.25, 7.0), (1.5, Y_POUPE, 10.0), c("bois_clair"), down="-z", studs="top", name="Escalier")
        for sg in (-1, 1):
            xa, xb = sorted((sg * 4.0, sg * 6.0))
            S.wedge((xa, Y_PONT + 0.25, Z_DUN - 3.5), (xb, Y_DUN, Z_DUN), c("bois_clair"), down="-z", studs="top",
                    name="Escalier")
            S.wedge((xa, Y_PONT + 0.25, Z_GAIL), (xb, Y_GAIL, Z_GAIL + 2.5), c("bois_clair"), down="+z", studs="top",
                    name="Escalier")

    with S.group("Rambardes"):
        pot, ram = c("bois_clair"), lis1
        for sg in (-1, 1):
            xa, xb = sorted((sg * 6.9, sg * HW))
            zs = [(Z_GAIL, -2.0), (2.0, Z_DUN)] if (sg > 0 and passerelle > 0) else [(Z_GAIL, Z_DUN)]
            for z0_, z1_ in zs:
                S.box((xa, Y_PONT, z0_), (xb, Y_PONT + 1.7, z1_), shade(coque, 1.05), name="Pavois")
                S.box((min(xa, xb) - 0.1, Y_PONT + 1.7, z0_), (max(xa, xb) + 0.1, Y_PONT + 2.0, z1_), ram, name="Lisse", **ND)
            _rambarde(S, (sg * 6.75, Z_GAIL), (sg * 6.75, -15), Y_GAIL + 0.25, pot, ram)
            _rambarde(S, (sg * 6.75, -15), (0, -23.3), Y_GAIL + 0.25, pot, ram, bouts=False)
            _rambarde(S, (sg * 6.75, Z_DUN), (sg * 6.75, 10.0), Y_DUN + 0.25, pot, ram)
            _rambarde(S, (sg * 3.6, Z_DUN - 0.2), (sg * 1.2, Z_DUN - 0.2), Y_DUN + 0.25, pot, ram)
        # garde-corps en arc sur la poupe ronde
        pts = [(5.6 * math.sin(math.radians(a)), Z_AR + 5.6 * math.cos(math.radians(a))) for a in (-90, -45, 0, 45, 90)]
        for p0, p1 in zip(pts, pts[1:]):
            _rambarde(S, p0, p1, Y_POUPE + 0.25, pot, ram, h=1.4, pas=3.0)

    mats = [
        ("Misaine", -9.0, Y_GAIL, 23.5, 40.0, [(22.0, 12.0, 20.0), (32.5, 25.0, 15.0)]),
        ("GrandMat", 2.0, Y_PONT, 26.5, 46.0, [(25.0, 11.0, 24.0), (37.0, 28.0, 18.0)]),
    ]
    for nom, zm, y0, yh, yt, vergues in mats:
        with S.group(f"Mature/{nom}"):
            _mat(S, zm, y0, yh, yt, r=0.75, hune=1.7, nid=(39.0 if nom == "GrandMat" else False))
            with S.at((0, 0, zm), yaw=brasse):
                for (yv, yb, larg) in vergues:
                    _voile(S, yv - 0.3, yb, larg, voile, ombre, z0=-1.2, bande=bande)
            pied = Y_GAIL if nom == "Misaine" else Y_PONT + 2.0
            _haubans(S, zm, pied, HW + 0.2, yh, 1.7, yt)
            for sg in (-1, 1):
                xa, xb = sorted((sg * HW, sg * (HW + 0.4)))
                S.box((xa, pied - 1.5, zm - 2.4), (xb, pied - 1.1, zm + 2.4), bois_f, name="PorteHauban", **ND)
    with S.group("Mature/Artimon"):
        zm = 11.0
        S.cyl((0, (Y_DUN + 32.0) / 2, zm), 0.6, 32.0 - Y_DUN, bois_f, name="Mat")
        S.ball((0, 32.3, zm), 0.5, c("or"), name="Pomme", **ND)
        # voile latine : triangle sous une longue vergue oblique
        S.wedge((-0.15, 15.6, zm - 4.5), (0.15, 30.0, zm + 8.5), ombre, down="-z", name="VoileLatine", **ND)
        for sg in (-1, 1):
            xa, xb = sorted((sg * 0.1, sg * 0.6))
            S.wedge((xa, 17.0, zm - 1.5), (xb, 26.8, zm + 7.5), voile, down="-z", name="VoileLatine", **ND)
        _seg(S, (0, 14.4, zm - 6.0), (0, 31.2, zm + 9.0), 0.3, bois_f, name="Antenne", collide=False)
        for sg in (-1, 1):
            _seg(S, (sg * 5.6, Y_POUPE + 1.5, zm), (0, 30.0, zm), 0.1, c("corde_fonce"), name="Hauban", **NDS)

    with S.group("Beaupre"):
        tip = np.array([0.0, 13.2, -27.8])
        _seg(S, (0, Y_GAIL + 0.3, -20.0), tip, 0.5, bois_f, name="Beaupre", collide=True)
        S.wedge((-0.15, 12.7, -27.0), (0.15, 30.0, -12.0), ombre, down="-z", name="Foc", **ND)
        for sg in (-1, 1):
            xa, xb = sorted((sg * 0.1, sg * 0.5))
            S.wedge((xa, 14.5, -23.5), (xb, 26.5, -13.0), voile, down="-z", name="Foc", **ND)
        cr = c("corde_fonce")
        _seg(S, tip, (0, 39.0, -9.0), 0.11, cr, name="Etai", **NDS)
        _seg(S, (0, 45.0, 2.0), (0, 39.5, -9.0), 0.11, cr, name="Etai", **NDS)
        _seg(S, (0, 32.0, zm), (0, 40.0, 2.0), 0.11, cr, name="Etai", **NDS)

    with S.at((0, 46.4, 2.0), yaw=90, group="Pavillon"):
        drapeau_pirate(b, variant=2 if v == 0 else 0, hauteur=5.0 * s, largeur=7.0 * s, mat=True)
    _flamme(S, 0, 40.2, -9.4, 6.0, c("rouge") if v == 0 else c("jaune"))

    for sg in (-1, 1):
        S.box((sg * HW - (0.4 if sg > 0 else -0.4), 8.4, -14.4), (sg * (HW + 1.2), 8.9, -13.4), bois_f, name="Bossoir", **ND)
        _ancre_suspendue(S, sg, sg * (HW + 0.7), 7.8, -13.9, c("metal_fonce"), t=0.85)

    for sg, zb in ((1, -5.5), (1, 8.5), (-1, -2.0)):
        with S.at((sg * (HW + 0.1), (6.3 if zb < Z_DUN else 7.6), zb), yaw=-90 * sg, group="Bouees"):
            bouee(b, variant=1, rayon=1.0 * s)

    with S.at((-3.6, Y_PONT + 0.25, 3.8), yaw=90, group="Pont/Tonneaux"):
        tonneaux(b, variant=2)
    with S.at((3.4, Y_GAIL + 0.25, -11.0), yaw=0, group="Pont/Caisses"):
        caisses(b, variant=2)
    with S.at((0, Y_DUN + 0.25, 8.0), yaw=0, group="Pont/Barre"):
        barre_navire(b, variant=0, taille=0.55)

    with S.group("Ecume"):
        _ecume(S, 5.8, -13, Z_AR, 6, ronde=True)

    if passerelle > 0:
        _passerelle(b, (HW - 0.4) * s, (Y_PONT + 0.25) * s, float(passerelle), 1.5)
    return {"emprise": (2 * max(15 * s, passerelle), 52.0 * s), "hauteur": 50.0 * s}


# ---------------------------------------------------------------------------
# Barque
# ---------------------------------------------------------------------------


def barque(b, variant: int = 0, ecume: bool = True) -> dict:
    """Barque à rames (≈ 8 × 3,5) amarrée, origine à la flottaison, proue vers -Z : coque en gradins, bancs, rames,
    rouleau de corde et fanal. Variantes : 0 bois naturel ; 1 rouge à bande blanche ; 2 bleu et blanc."""
    v = variant % 3
    S = _Ech(b, 1.0)
    coque, bande = [(c("bois"), c("bois_clair")), (c("rouge"), c("blanc")), (c("blanc"), c("bleu"))][v]
    with S.group("Barque"):
        _etage(S, -1.2, 0.5, 1.25, -2.6, 3.0, 1.4, shade(coque, 0.8), name="Coque")
        # bordé haut (flancs ouverts) et tableau arrière
        for sg in (-1, 1):
            xa, xb = sorted((sg * 1.35, sg * 1.75))
            S.box((xa, 0.4, -2.6), (xb, 1.3, 3.2), coque, name="Borde")
            _coin_plan(S, 0, -2.6, sg * 1.75, -1.9, 0.4, 1.3, coque, name="Borde")
            xa, xb = sorted((sg * 1.75, sg * 1.87))
            S.box((xa, 0.85, -2.4), (xb, 1.15, 3.0), bande, name="Bande", **ND)
        S.box((-1.9, 0.3, 3.0), (1.9, 1.45, 3.4), shade(coque, 0.9), name="Tableau")
        S.box((-1.3, 0.4, -2.5), (1.3, 0.55, 2.9), c("bois_pale"), name="Fond", **ND)
        for z in (-0.6, 1.6):
            S.box((-1.4, 0.9, z - 0.35), (1.4, 1.1, z + 0.35), c("bois_clair"), studs="top", name="Banc", **ND)
        for sg in (-1, 1):
            _seg(S, (sg * 0.8, 1.15, -0.2), (sg * 3.4, -0.1, 0.9), 0.14, c("bois_pale"), name="Rame")
        S.box((-0.15, 0.55, -2.5), (0.15, 2.3, -2.2), c("bois_fonce"), name="Mat", **ND)
        S.box((-0.35, 2.3, -2.7), (0.35, 3.1, -2.0), c("lanterne"), material="Neon", name="Fanal", **NDS)
        if ecume:
            _ecume(S, 1.25, -2.6, 3.0, 1.4, marge=0.4)
    return {"emprise": (4.0, 8.2), "hauteur": 3.2}


# ---------------------------------------------------------------------------
# Phare
# ---------------------------------------------------------------------------


def phare(b, variant: int = 0, hauteur: float = 64) -> dict:
    """Phare à bandes rouges et blanches sur son îlot rocheux, galerie à balustrade, lanterne éclairée, dôme rouge et
    girouette ; maison du gardien, porche, mouettes. Origine au centre de l'îlot (dessus en y = 0, eau en y = -1,5) ;
    palier plat côté -X (x de -10 à -6, z de -4,5 à 4,5) où arrive la jetée de pierre, prolongé jusqu'à x = -11 par
    un rebord plus bas (y = -0,3) que la jetée recouvre sans face coplanaire.
    Variantes : 0 rouge et blanc ; 1 bleu et blanc."""
    rng = b.rng
    k = hauteur / 64.0
    rouge, blanc = (c("rouge"), c("blanc")) if variant % 2 == 0 else (c("bleu"), c("blanc"))
    with b.group("Ilot"):
        # socle rocheux (sous l'eau et à fleur d'eau), dalle de pierre, palier de la jetée
        b.cyl((0, -1.85, 0), 9.6, 3.3, c("roche_fonce"), studs="top", name="Ilot")      # dessus en y = -0,2
        b.cyl((0, 0.15, 0), 8.2, 0.7, c("pierre"), studs="top", name="Parvis")          # dessus en y = 0,5
        b.box((-10.0, -3.0, -4.5), (-6.0, 0.0, 4.5), c("pierre"), studs="top", name="Palier")
        b.box((-9.0, -0.2, -1.8), (-8.0, 0.25, 1.8), c("pierre_claire"), studs="top", name="Marche")
        b.box((-11.0, -3.0, -4.5), (-10.0, -0.3, 4.5), c("pierre_fonce"), name="Rebord")
        b.cyl((0, -1.425, 0), 10.9, 0.15, c("ecume"), name="Ecume", **NDS)
        # couronne de gros rochers (sauf devant le palier), dessus studdés, touffes de mousse
        n = 11
        for i in range(n):
            a = 2 * math.pi * (i + 0.5) / n + rng.uniform(-0.12, 0.12)
            if math.cos(a) < -0.72:
                continue
            r = 9.0 + rng.uniform(-0.3, 0.5)
            w, d = rng.uniform(3.0, 4.2), rng.uniform(2.6, 3.4)
            top = rng.uniform(0.3, 1.8)
            col = vary(("roche", "roche_claire", "roche_fonce", "roche")[i % 4], rng, 0.05)
            with b.at((r * math.cos(a), 0, r * math.sin(a)), yaw=-math.degrees(a) + rng.uniform(-15, 15)):
                b.box((-d / 2, -3.2, -w / 2), (d / 2, top, w / 2), col, studs="top", name="Rocher")
                if i % 3 == 0:
                    b.box((-d / 2 + 0.4, top, -w / 2 + 0.5), (d / 2 - 0.6, top + 0.4, w / 2 - 1.0),
                          c("roche_mousse"), studs="top", name="Mousse", **ND)
                elif i % 3 == 1:
                    b.box((-d / 2 - 0.6, -1.5, -w / 2 + 0.3), (d / 2 + 0.6, -1.35, w / 2 - 0.3), c("ecume"),
                          name="Ecume", **NDS)
    yb = 0.5
    H = 48.0 * k                       # fût jusqu'à la galerie
    n = 8
    with b.group("Tour"):
        b.cyl((0, yb + 1.0, 0), 6.7, 2.0, c("pierre_fonce"), studs="top", name="Socle")
        b.cyl((0, yb + 2.15, 0), 6.35, 0.3, c("pierre_claire"), name="Socle", **ND)
        y = yb + 2.0
        for i in range(n):
            r = 6.0 - 1.9 * i / (n - 1)
            hh = (H - 0.8) / n
            b.cyl((0, y + hh / 2, 0), r, hh, rouge if i % 2 == 0 else blanc, name="Bande")
            y += hh
        y_gal = y
        # porte (côté -X, vers la jetée) : marches, porte, linteau, auvent, enseigne et fanal
        b.box((-7.0, yb, -1.8), (-5.6, yb + 6.4, 1.8), c("pierre_claire"), name="Encadrement")
        b.box((-7.1, yb, -1.2), (-6.95, yb + 5.4, 1.2), c("bois_fonce"), name="Porte", **ND)
        b.box((-7.25, yb + 2.6, 0.5), (-7.1, yb + 3.2, 0.9), c("laiton"), name="Poignee", **NDS)
        b.wedge((-8.4, yb + 6.4, -2.3), (-6.9, yb + 7.4, 2.3), c("toit_rouge"), down="-x", studs="top", name="Auvent", **ND)
        pan = b.box((-6.15, yb + 8.2, -2.4), (-5.6, yb + 9.7, 2.4), c("bois"), name="Enseigne", **ND)
        pan.label = {"face": "Left", "text": "PHARE", "color": c("blanc"), "bg": c("bois_fonce"), "font": "sans"}
        b.box((-6.5, yb + 4.4, 2.3), (-5.5, yb + 4.7, 3.0), c("fer"), name="Console", **ND)
        b.box((-6.4, yb + 3.3, 2.35), (-5.8, yb + 4.4, 2.95), c("lanterne"), material="Neon", name="Fanal", **NDS)
        # fenêtres en spirale (encadrées de blanc)
        for j, (a, fy) in enumerate(((60, 0.22), (150, 0.38), (230, 0.55), (320, 0.72), (40, 0.88), (200, 0.08))):
            yy = yb + 2.0 + H * fy
            r = 6.0 - 1.9 * (yy - yb - 2.0) / H
            ra = math.radians(a)
            b.boxc(((r - 0.2) * math.cos(ra), yy, (r - 0.2) * math.sin(ra)), (1.0, 3.6, 2.4), c("blanc"),
                   yaw=-a, name="Cadre", **ND)
            b.boxc(((r - 0.05) * math.cos(ra), yy, (r - 0.05) * math.sin(ra)), (1.0, 2.8, 1.6), c("fenetre"),
                   yaw=-a, name="Fenetre", **ND)
    with b.group("Galerie"):
        b.cyl((0, y_gal + 0.5, 0), 4.7, 1.0, blanc, name="Corniche")
        # consoles sous la galerie
        for i in range(10):
            a = i * 36
            ra = math.radians(a)
            with b.at((4.1 * math.cos(ra), 0, 4.1 * math.sin(ra)), yaw=-a - 90):
                b.wedge_under((-0.35, y_gal - 1.4, -1.9), (0.35, y_gal + 1.0, 0.1), c("noir"), down="-z",
                              name="Console", **ND)
        b.cyl((0, y_gal + 1.3, 0), 6.2, 0.6, c("noir"), studs="top", name="Galerie")
        yr = y_gal + 1.6
        for i in range(12):
            a = math.radians(i * 30)
            b.box((5.7 * math.cos(a) - 0.15, yr, 5.7 * math.sin(a) - 0.15),
                  (5.7 * math.cos(a) + 0.15, yr + 1.8, 5.7 * math.sin(a) + 0.15), c("fer"), name="Balustre", **ND)
        L8 = 2 * 5.8 * math.tan(math.radians(22.5)) + 0.3
        for i in range(8):
            a = i * 45 + 22.5
            ra = math.radians(a)
            b.boxc((5.8 * math.cos(ra), yr + 1.9, 5.8 * math.sin(ra)), (0.3, 0.3, L8), c("fer"), yaw=-a,
                   name="MainCourante", **ND)
        # trappe d'accès à la galerie (sur le soubassement de la lanterne, côté +Z) et mouette sur la main courante
        b.box((-0.7, yr + 0.15, 3.75), (0.7, yr + 1.45, 4.0), c("bois_fonce"), name="Trappe", **ND)
        with b.at((5.8 * math.cos(math.radians(112.5)), yr + 2.05, 5.8 * math.sin(math.radians(112.5))), yaw=30,
                  group="Mouette"):
            from assets.mobilier import mouette
            mouette(b, variant=0)
    with b.group("Lanterne"):
        y0 = yr
        b.cyl((0, y0 + 0.8, 0), 3.9, 1.6, rouge, name="Soubassement")
        b.cyl((0, y0 + 4.2, 0), 3.5, 5.2, c("vitre"), material="Glass", transparency=0.35, name="Vitrage", **ND)
        b.cyl((0, y0 + 4.2, 0), 2.3, 4.6, c("lanterne"), material="Neon", name="Feu", **NDS)
        for i in range(8):
            a = math.radians(i * 45 + 22.5)
            b.box((3.5 * math.cos(a) - 0.2, y0 + 1.6, 3.5 * math.sin(a) - 0.2),
                  (3.5 * math.cos(a) + 0.2, y0 + 6.8, 3.5 * math.sin(a) + 0.2), c("noir"), name="Montant", **ND)
        y1 = y0 + 6.8
        b.cyl((0, y1 + 0.25, 0), 4.3, 0.5, c("noir"), name="Corniche")
        for (r, h) in ((3.9, 1.1), (3.0, 1.0), (2.0, 0.9), (1.0, 0.8)):
            b.cyl((0, y1 + 0.5 + h / 2, 0), r, h, rouge, studs="top", name="Dome")
            y1 += h
        y1 += 0.5
        b.ball((0, y1 + 0.4, 0), 0.6, c("or"), name="Boule", **ND)
        b.cyl((0, y1 + 1.8, 0), 0.12, 2.4, c("fer"), name="Girouette", **NDS)
        b.box((-0.1, y1 + 2.0, -1.4), (0.1, y1 + 2.5, 1.4), c("fer"), name="Girouette", **NDS)
        b.wedge((-0.1, y1 + 1.8, -2.1), (0.1, y1 + 2.7, -1.4), c("or"), down="-z", name="Girouette", **NDS)
        y_top = y1 + 3.0
    with b.group("Maison"):
        # maison du gardien adossée à la tour (côté +Z), porte vers +X, cheminée, jardinière
        b.box((-3.5, yb, 4.5), (3.5, yb + 5.0, 9.0), c("mur_blanc"), name="Mur")
        b.box((-3.9, yb + 5.0, 4.3), (3.9, yb + 5.4, 9.4), c("bois_fonce"), name="Corniche")
        b.wedge((-3.9, yb + 5.4, 4.3), (3.9, yb + 7.6, 6.85), c("toit_rouge"), down="-z", studs="top", name="Toit")
        b.wedge((-3.9, yb + 5.4, 6.85), (3.9, yb + 7.6, 9.4), c("toit_rouge"), down="+z", studs="top", name="Toit")
        b.box((1.4, yb + 6.2, 7.4), (2.4, yb + 9.0, 8.4), c("pierre_claire"), name="Cheminee")
        b.box((1.25, yb + 9.0, 7.25), (2.55, yb + 9.4, 8.55), c("pierre_fonce"), studs="top", name="Cheminee", **ND)
        b.box((3.5, yb, 5.6), (3.65, yb + 3.6, 7.6), c("volet_bleu"), name="Porte", **ND)
        b.box((-1.2, yb + 1.8, 9.0), (1.2, yb + 3.6, 9.15), c("fenetre"), name="Fenetre", **ND)
        b.box((-1.7, yb + 1.8, 9.0), (-1.2, yb + 3.6, 9.25), c("volet_bleu"), name="Volet", **ND)
        b.box((1.2, yb + 1.8, 9.0), (1.7, yb + 3.6, 9.25), c("volet_bleu"), name="Volet", **ND)
        b.box((-1.5, yb + 1.3, 9.0), (1.5, yb + 1.8, 9.6), c("bois"), name="Jardiniere", **ND)
        for x, fl in ((-0.9, "fleur_rouge"), (0.0, "fleur_jaune"), (0.9, "fleur_rouge")):
            b.box((x - 0.3, yb + 1.8, 9.1), (x + 0.3, yb + 2.3, 9.5), c(fl), name="Fleurs", **NDS)
        with b.at((1.9, yb + 9.4, 7.9), yaw=-120, group="Mouette"):
            from assets.mobilier import mouette
            mouette(b, variant=0)
    with b.at((-8.6, 0.0, -3.7), yaw=90, group="Bouee"):
        bouee(b, variant=0)
    return {"emprise": (22.0, 22.0), "hauteur": y_top}


# ---------------------------------------------------------------------------
# Pontons
# ---------------------------------------------------------------------------


def ponton(b, variant: int = 0, longueur: float = 64, largeur: float = 8) -> dict:
    """Ponton depuis le quai (z = 0) vers -Z, plancher à y = 0.

    0 : ponton de bois (planches en travers, pieux tous les 8 studs, rambardes de corde, fanaux, plateforme en T,
    échelle, bitte) ; 1 : étroit ponton des pêcheurs (planches ajourées, perches, filet qui sèche, caisses de poisson) ;
    2 : jetée de pierre (gros blocs studdés, enrochements à la flottaison, bittes de fonte)."""
    rng = b.rng
    v = variant % 3
    L, w = float(longueur), float(largeur)
    hw = w / 2
    if v == 0:
        n = max(1, round(L / 4))
        dz = L / n
        nT = 2                                         # planches de la plateforme en T (plus larges)
        with b.group("Plancher"):
            # sous-plancher sombre : il apparaît dans les joints entre les planches
            b.box((-hw - 0.2, -1.1, -L + 0.2), (hw + 0.2, -0.45, -0.2), c("bois_fonce"), name="Solive")
            for i in range(n):
                z1, z0 = -i * dz - (0.0 if i == 0 else 0.15), -(i + 1) * dz + (0.15 if i < n - 1 else 0.0)
                ww = hw + (4.0 if i >= n - nT else 0.0)
                col = vary(("bois_quai", "bois_clair", "bois_flotte")[i % 3], rng, 0.04)
                b.box((-ww, -0.45, z0), (ww, 0.0, z1), col, studs="top", name="Planche")
            for sg in (-1, 1):
                xa, xb = sorted((sg * hw, sg * (hw + 0.4)))
                b.box((xa, -1.2, -L + nT * dz), (xb, -0.3, 0), c("bois_fonce"), name="Longeron")
        with b.group("Pieux"):
            tops = {-1: [], 1: []}
            m = max(1, round((L - nT * dz) / 8))
            for j in range(m + 1):
                z = -0.8 - j * (L - nT * dz - 0.8) / m
                for sg in (-1, 1):
                    b.cyl((sg * (hw + 0.3), -0.8, z), 0.7, 4.4, c("bois_fonce"), name="Pieu")
                    tops[sg].append((sg * (hw + 0.3), 1.2, z))
            zT = -L + 0.8
            for sg in (-1, 1):
                b.cyl((sg * (hw + 3.5), -0.8, zT), 0.7, 4.4, c("bois_fonce"), name="Pieu")
                b.cyl((sg * (hw + 3.5), -0.8, -L + nT * dz - 0.8), 0.7, 4.4, c("bois_fonce"), name="Pieu")
                tops[sg] += [(sg * (hw + 3.5), 1.2, -L + nT * dz - 0.8), (sg * (hw + 3.5), 1.2, zT)]
        with b.group("Rambardes"):
            for sg in (-1, 1):
                pts = tops[sg][:m + 1]
                for a, bb in zip(pts, pts[1:]):
                    cordage(b, a, bb, creux=0.35, n=2, rayon=0.13)
                # tour du T : du dernier pieu du ponton au coin du T, puis le long du bord extérieur du T
                cordage(b, pts[-1], tops[sg][m + 1], creux=0.25, n=1, rayon=0.13)
                cordage(b, tops[sg][m + 1], tops[sg][m + 2], creux=0.25, n=1, rayon=0.13)
        with b.group("Fanaux"):
            for j in range(2, m + 1, 3):
                sg = 1 if (j // 3) % 2 == 0 else -1
                x, _, z = tops[sg][j]
                b.box((x - 0.55, 1.4, z - 0.55), (x + 0.55, 2.8, z + 0.55), c("lanterne"), material="Neon", name="Fanal", **NDS)
                b.box((x - 0.75, 2.8, z - 0.75), (x + 0.75, 3.1, z + 0.75), c("fer"), name="Fanal", **ND)
        with b.group("Echelle"):
            # échelle de bain contre la face du bout du T (z = -L), montants jusqu'au-dessus du plancher
            for x in (hw + 1.0, hw + 2.3):
                b.box((x - 0.13, -3.0, -L - 0.3), (x + 0.13, 0.9, -L), c("bois_fonce"), name="Montant", **ND)
            for yy in (-2.4, -1.3):
                b.box((hw + 1.13, yy, -L - 0.25), (hw + 2.17, yy + 0.2, -L - 0.05), c("bois_fonce"), name="Barreau", **ND)
        with b.at((-(hw + 1.5), 0, -L + 2.0), group="Bitte"):
            bitte(b, variant=0)
        return {"emprise": (w + 9.0, L), "hauteur": 3.1}

    if v == 1:
        n = max(1, round(L / 3))
        dz = L / n
        with b.group("Plancher"):
            for sg in (-1, 1):
                b.box((sg * (hw - 1.0) - 0.4, -1.0, -L), (sg * (hw - 1.0) + 0.4, -0.5, 0), c("bois_fonce"), name="Longeron")
            for i in range(n):
                z1, z0 = -i * dz - 0.2, -(i + 1) * dz + 0.2
                col = vary(("bois_flotte", "bois_pale", "bois_quai")[i % 3], rng, 0.05)
                b.box((-hw, -0.5, z0), (hw, 0.0, z1), col, studs="top", name="Planche")
        with b.group("Pieux"):
            m = max(1, round(L / 8))
            for j in range(m + 1):
                z = -0.6 - j * (L - 1.2) / m
                for sg in (-1, 1):
                    haut = 4.0 if (j % 2 == 1 and sg > 0) else 0.8
                    b.cyl((sg * (hw + 0.25), (haut - 3.0) / 2, z), 0.45 if haut > 1 else 0.55, haut + 3.0,
                          c("bois_flotte") if haut > 1 else c("bois_fonce"), name="Pieu")
        with b.at((-(hw - 0.6), 0, -L * 0.45), yaw=90, group="Filet"):
            filet_peche(b, variant=0, largeur=6.0)
        with b.group("Caisses"):
            for (x, z) in ((1.4, -L * 0.25), (1.6, -L * 0.25 - 2.4), (-1.2, -L + 3.0)):
                b.box((x - 1.0, 0.0, z - 0.8), (x + 1.0, 1.0, z + 0.8), c("bois_pale"), studs="top", name="Caisse")
                b.box((x - 0.7, 1.0, z - 0.5), (x + 0.7, 1.35, z + 0.5), c("poisson"), name="Poissons", **ND)
        return {"emprise": (w + 1.0, L), "hauteur": 4.0}

    # v == 2 : jetée de pierre : dallage central, bordures en pierre sombre (arrêtées avant le bout, qui reste plat
    # pour rejoindre le palier du phare), enrochement à la flottaison, liseré d'écume
    n = max(1, round(L / 8))
    dz = L / n
    with b.group("Jetee"):
        for i in range(n):
            z1, z0 = -i * dz, -(i + 1) * dz
            col = vary(("pierre", "pierre_claire")[i % 2], rng, 0.03)
            b.box((-hw + 1.0, -3.0, z0), (hw - 1.0, 0.0, z1), col, studs="top", name="Dalle")
        for sg in (-1, 1):
            xa, xb = sorted((sg * (hw - 1.0), sg * hw))
            b.box((xa, -3.0, -L + 2.0), (xb, 0.4, 0), vary("pierre_fonce", rng, 0.03), studs="top", name="Bordure")
            b.box((xa, -3.0, -L), (xb, 0.0, -L + 2.0), c("pierre_fonce"), studs="top", name="Bordure")
            xa, xb = sorted((sg * hw, sg * (hw + 1.8)))
            b.box((xa, -1.5, -L + 1.0), (xb, -1.35, -0.5), c("ecume"), name="Ecume", **NDS)
    with b.group("Enrochement"):
        for i in range(n):
            for sg in (-1, 1):
                for j in range(2):
                    z = -(i + 0.25 + 0.5 * j) * dz + rng.uniform(-1.0, 1.0)
                    z = min(-1.5, max(-L + 1.5, z))
                    big = j == 0
                    sz = (rng.uniform(2.6, 3.4) if big else rng.uniform(1.8, 2.4), rng.uniform(2.4, 3.0) if big else
                          rng.uniform(1.8, 2.3), rng.uniform(3.2, 4.4) if big else rng.uniform(2.2, 3.0))
                    col = vary(("roche", "roche_claire", "roche_fonce")[(i + j + (sg > 0)) % 3], rng, 0.05)
                    b.boxc((sg * (hw + 0.6 + (0.3 if big else 0.9)), -3.2 + sz[1] / 2, z), sz, col,
                           yaw=rng.uniform(-20, 20), studs="top", name="Rocher")
    for j, z in enumerate((-L * 0.33, -L + 5.0)):
        sg = 1 if j % 2 == 0 else -1
        with b.at((sg * (hw - 1.9), 0, z), group="Bitte"):
            bitte(b, variant=0)
    return {"emprise": (w + 3.0, L), "hauteur": 2.4}
