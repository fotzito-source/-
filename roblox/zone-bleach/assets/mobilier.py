"""Mobilier de la zone Bleach : petits objets du faubourg et de la cité blanche.

Toutes les fonctions suivent CONVENTIONS.md : origine au centre de l'emprise au sol, avant vers -Z local
(tourné vers le couloir par la mise en page), au plus 40 pièces chacune. Détails fins sans collision.

    lanterne_pierre      lanterne de pierre (tōrō), 3 variantes                      ≈ 11 pièces
    lanterne_poteau      lanterne de papier carrée (andon) sur poteau : bois / blanc / laque rouge   ≈ 14
    pilier_lanterne      haut pilier blanc coiffé d'une lanterne (repère d'allée, entrée de la place) ≈ 13
    mat_guirlande        mât qui porte une guirlande au-dessus du couloir (crochet vers l'avant)     6
    guirlande_lampions   fil affaissé et lampions suspendus entre deux points (au-dessus de 30 studs)
    panneau              enseigne sur pied (texte vertical)                                     ≈ 8
    nobori               bannière verticale sur mât, lisible des deux sens de la course          8
    tonneaux, caisses, sacs_riz, seaux_incendie, charrette, puits, banc, etal, pot_plante
    cloture_bois, cloture_bambou   clôtures le long de X local
"""

from __future__ import annotations

import numpy as np

from kit import shade
from palette import c, vary

# Enseignes autorisées (mots courants, aucun mot de la licence) : voir CONVENTIONS.md.
TEXTES = ("茶", "宿", "米", "湯", "薬", "団子", "蕎麦", "甘味", "呉服", "豆腐", "本", "花", "桜", "門", "静", "白")


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

def _segment(b, a, bb, rayon: float, col, name: str = "Cable") -> None:
    """Cylindre fin de a à bb (l'axe d'un cylindre Roblox est son X local)."""
    a, bb = np.asarray(a, float), np.asarray(bb, float)
    d = bb - a
    n = float(np.linalg.norm(d))
    if n < 1e-3:
        return
    x = d / n
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    b.part("cyl", (n + rayon * 0.6, 2 * rayon, 2 * rayon), (a + bb) / 2, np.column_stack([x, y, z]), col,
           collide=False, shadow=False, name=name)


def _chainette(p0, p1, creux: float, n: int):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    pts = []
    for i in range(n + 1):
        t = i / n
        p = p0 + (p1 - p0) * t
        p[1] -= creux * 4 * t * (1 - t)
        pts.append(p)
    return pts


def _toit_deux_pans(b, cx, y, cz, demi, h, couleur, studs="top", collide=False):
    """Petit toit à deux pans (faîtage le long de X) : deux coins pleins, pentes vers -Z et +Z."""
    b.wedge((cx - demi, y, cz - demi), (cx + demi, y + h, cz), couleur, down="-z", studs=studs, collide=collide, name="Toit")
    b.wedge((cx - demi, y, cz), (cx + demi, y + h, cz + demi), couleur, down="+z", studs=studs, collide=collide, name="Toit")


# ---------------------------------------------------------------------------
# Lumières
# ---------------------------------------------------------------------------

def lanterne_pierre(b, variant: int = 0) -> dict:
    """Lanterne de pierre (tōrō) : socle stud, fût, plateau, chambre éclairée, toit débordant, bouton."""
    p, pf = c("pierre"), c("pierre_fonce")
    if variant % 3 == 1:
        p, pf = c("pierre_claire"), c("pierre")
    with b.group("LanternePierre"):
        b.box((-1.4, 0, -1.4), (1.4, 0.7, 1.4), pf, studs="top", name="Socle")
        b.box((-0.6, 0.7, -0.6), (0.6, 3.4, 0.6), p, name="Fut")
        b.box((-1.15, 3.4, -1.15), (1.15, 3.85, 1.15), pf, name="Plateau")
        b.box((-0.9, 3.85, -0.9), (0.9, 5.4, 0.9), p, name="Chambre")
        b.box((-0.55, 4.1, -0.95), (0.55, 5.15, 0.95), c("jaune_lampion"), material="Neon", collide=False, shadow=False, name="Lumiere")
        b.box((-0.95, 4.1, -0.55), (0.95, 5.15, 0.55), c("jaune_lampion"), material="Neon", collide=False, shadow=False, name="Lumiere")
        b.box((-1.7, 5.4, -1.7), (1.7, 5.9, 1.7), pf, studs="top", name="Toit")
        b.box((-1.05, 5.9, -1.05), (1.05, 6.4, 1.05), p, studs="top", name="Toit")
        b.box((-0.4, 6.4, -0.4), (0.4, 7.0, 0.4), pf, name="Bouton")
        if variant % 3 == 2:  # mousse au pied
            b.box((-1.5, 0.7, -1.5), (1.5, 0.9, 0.1), c("mousse"), collide=False, name="Mousse")
    return {"emprise": (3.4, 3.4), "hauteur": 7.0}


_POTEAUX = (  # (poteau, socle, chapeau, cadre)
    ("bois_fonce", "pierre_fonce", "tuile_grise", "bois_fonce"),     # faubourg
    ("blanc", "pierre", "ocre", "bois_fonce"),                       # cité blanche
    ("laque_rouge", "pierre_fonce", "ocre", "laque_noire"),          # place, passerelle
)


def lanterne_poteau(b, variant: int = 0, hauteur: float = 6.2) -> dict:
    """Lanterne de papier carrée (andon) sur poteau : socle stud, poteau, plateau, cadre de bois à quatre
    montants autour du papier allumé (Neon), chapeau pyramidal stud et bouton."""
    poteau, socle, chapeau, cadre = (c(n) for n in _POTEAUX[variant % 3])
    y0 = hauteur
    with b.group("LanternePoteau"):
        b.box((-0.85, 0, -0.85), (0.85, 0.8, 0.85), socle, studs="top", name="Socle")
        b.box((-0.35, 0.8, -0.35), (0.35, y0, 0.35), poteau, name="Poteau")
        b.box((-0.8, y0, -0.8), (0.8, y0 + 0.3, 0.8), cadre, name="Plateau")
        b.box((-0.6, y0 + 0.3, -0.6), (0.6, y0 + 2.1, 0.6), c("jaune_lampion"), material="Neon", collide=False, shadow=False, name="Papier")
        for sx in (-0.68, 0.68):
            for sz in (-0.68, 0.68):
                b.box((sx - 0.12, y0 + 0.3, sz - 0.12), (sx + 0.12, y0 + 2.1, sz + 0.12), cadre, collide=False, name="Montant")
        b.box((-0.72, y0 + 1.15, -0.72), (0.72, y0 + 1.27, 0.72), cadre, collide=False, shadow=False, name="Traverse")
        b.box((-1.05, y0 + 2.1, -1.05), (1.05, y0 + 2.4, 1.05), chapeau, collide=False, name="Chapeau")
        _toit_deux_pans(b, 0, y0 + 2.4, 0, 1.05, 0.7, chapeau)
        b.box((-0.2, y0 + 3.1, -0.2), (0.2, y0 + 3.5, 0.2), cadre, collide=False, name="Bouton")
    return {"emprise": (2.1, 2.1), "hauteur": y0 + 3.5}


def pilier_lanterne(b, variant: int = 0, hauteur: float = 16.0) -> dict:
    """Haut pilier d'enduit blanc sur socle de pierre, bandeau ocre (ou laque rouge), coiffé d'une lanterne
    carrée allumée sous un petit toit ocre. Sert de repère rythmique et d'entrée de la place."""
    bande = c("laque_rouge") if variant % 2 else c("ocre")
    H = hauteur
    with b.group("PilierLanterne"):
        b.box((-2.0, 0, -2.0), (2.0, 1.2, 2.0), c("pierre_fonce"), studs="top", name="Socle")
        b.box((-1.6, 1.2, -1.6), (1.6, 2.4, 1.6), c("pierre"), studs="top", name="Base")
        b.box((-1.25, 2.4, -1.25), (1.25, H, 1.25), c("blanc"), name="Fut")
        b.box((-1.4, H - 3.0, -1.4), (1.4, H - 2.2, 1.4), bande, name="Bandeau")
        b.box((-1.5, H, -1.5), (1.5, H + 0.4, 1.5), c("blanc_pur"), studs="top", name="Corniche")
        b.box((-0.85, H + 0.4, -0.85), (0.85, H + 2.4, 0.85), c("jaune_lampion"), material="Neon", collide=False, shadow=False, name="Lumiere")
        for sx in (-0.95, 0.95):
            for sz in (-0.95, 0.95):
                b.box((sx - 0.15, H + 0.4, sz - 0.15), (sx + 0.15, H + 2.4, sz + 0.15), c("bois_fonce"), collide=False, name="Montant")
        b.box((-1.7, H + 2.4, -1.7), (1.7, H + 2.7, 1.7), c("ocre_fonce"), collide=False, name="Avant-toit")
        _toit_deux_pans(b, 0, H + 2.7, 0, 1.7, 1.0, c("ocre"))
        b.box((-0.25, H + 3.7, -0.25), (0.25, H + 4.3, 0.25), c("or"), collide=False, name="Epi")
    return {"emprise": (4, 4), "hauteur": H + 4.3}


def mat_guirlande(b, variant: int = 0, hauteur: float = 39.0, bras: float = 2.4) -> dict:
    """Mât qui porte une guirlande au-dessus du couloir : pied de pierre, mât, potence vers l'avant (-Z local,
    donc vers le couloir une fois tourné), chapeau. `accroche` = point d'attache du fil (repère de l'asset)."""
    bois = c("bois_fonce") if variant % 2 == 0 else c("laque_rouge")
    chap = c("tuile_grise") if variant % 2 == 0 else c("ocre")
    with b.group("MatGuirlande"):
        b.box((-1.0, 0, -1.0), (1.0, 1.2, 1.0), c("pierre_fonce"), studs="top", name="Pied")
        b.box((-0.6, 1.2, -0.6), (0.6, hauteur + 2.0, 0.6), bois, name="Mat")
        b.box((-0.4, hauteur - 0.4, -bras), (0.4, hauteur + 0.4, -0.6), bois, name="Potence")
        b.box((-0.25, hauteur - 2.2, -1.5), (0.25, hauteur - 0.4, -1.0), bois, collide=False, name="Jambe")
        b.box((-0.85, hauteur + 2.0, -0.85), (0.85, hauteur + 2.6, 0.85), chap, studs="top", name="Chapeau")
        b.box((-0.3, hauteur + 2.6, -0.3), (0.3, hauteur + 3.1, 0.3), c("bois_fonce"), collide=False, name="Bouton")
    return {"emprise": (2, 2 + bras), "hauteur": hauteur + 3.1, "accroche": (0.0, hauteur, -bras)}


PALETTES_LAMPIONS = [
    [("lampion_papier", True), ("rouge", False), ("lampion_papier", True)],          # faubourg
    [("lampion_papier", True), ("orange_lampion", True), ("lampion_papier", True)],  # fête
    [("blanc_pur", True), ("laque_rouge", False), ("blanc_pur", True)],              # cité blanche
]


def _corps_lampion(b, x, y, z, col, neon: bool, r: float = 0.95, h: float = 1.8) -> None:
    noir = c("noir")
    b.cyl((x, y + 0.15, z), r * 0.62, 0.3, noir, collide=False, name="Capuchon")
    b.cyl((x, y + 0.3 + h / 2, z), r, h, c(col), material="Neon" if neon else "SmoothPlastic",
          collide=False, shadow=False, name="Lampion")
    b.cyl((x, y + 0.3 + h * 0.5, z), r + 0.05, 0.18, noir, collide=False, shadow=False, name="Cerclage")
    b.cyl((x, y + 0.45 + h, z), r * 0.62, 0.3, noir, collide=False, name="Capuchon")


def guirlande_lampions(b, p0, p1, n: int = 8, creux: float = 2.5, variant: int = 0) -> dict:
    """Guirlande de lampions de papier entre deux points (fil affaissé, lampions dessous).
    Au-dessus du couloir : le bas des lampions descend à (y des accroches) - creux - 3,6 ; garder ≥ 31."""
    pts = _chainette(p0, p1, creux, 16)
    pal = PALETTES_LAMPIONS[variant % len(PALETTES_LAMPIONS)]
    with b.group("Guirlande"):
        for a, bb in zip(pts, pts[1:]):
            _segment(b, a, bb, 0.08, c("noir"), name="Fil")
        p0a, p1a = np.asarray(p0, float), np.asarray(p1, float)
        for i in range(n):
            t = (i + 1) / (n + 1)
            p = p0a + (p1a - p0a) * t
            y = p[1] - creux * 4 * t * (1 - t)
            col, neon = pal[i % len(pal)]
            b.box((p[0] - 0.06, y - 0.6, p[2] - 0.06), (p[0] + 0.06, y, p[2] + 0.06), c("noir"), collide=False, shadow=False, name="Attache")
            _corps_lampion(b, p[0], y - 0.6 - 2.4, p[2], col, neon)
    return {"lampions": n}


# ---------------------------------------------------------------------------
# Enseignes
# ---------------------------------------------------------------------------

def panneau(b, texte: str = "茶", variant: int = 0) -> dict:
    """Enseigne sur pied (kanban) : patin, deux pieds, planche à texte vertical, chapeau (tuiles grises au
    faubourg, ocre dans la cité selon la variante)."""
    fond = (c("papier"), c("bois_clair"), c("blanc"))[variant % 3]
    chap = (c("tuile_grise"), c("tuile_grise_fonce"), c("ocre"))[variant % 3]
    h = 1.6 + 1.5 * len(texte)
    with b.group("Panneau"):
        b.box((-1.2, 0, -0.4), (1.2, 0.3, 0.4), c("bois_fonce"), name="Patin")
        for x in (-0.9, 0.9):
            b.box((x - 0.15, 0.3, -0.15), (x + 0.15, 1.2, 0.15), c("bois_fonce"), name="Pied")
        b.box((-1.25, 1.2, -0.12), (1.25, 1.35 + h, 0.25), c("bois_fonce"), collide=False, name="Cadre")
        board = b.box((-1.05, 1.35, -0.25), (1.05, 1.2 + h, 0.2), fond, name="Planche")
        board.label = {"face": "Front", "text": texte, "color": (40, 30, 30), "font": "brush", "vertical": True}
        b.box((-1.45, 1.35 + h, -0.4), (1.45, 1.75 + h, 0.5), chap, studs="top", name="Chapeau")
    return {"emprise": (2.9, 0.9), "hauteur": 1.75 + h}


_NOBORI = (("noren_bleu", (245, 240, 230)), ("noren_blanc", (40, 52, 96)), ("noren_rouge", (250, 244, 232)),
           ("noren_ocre", (60, 34, 20)))


def nobori(b, texte: str = "茶", variant: int = 0, hauteur: float = 9.0) -> dict:
    """Bannière nobori : pied lesté, mât, bras en haut, toile verticale dans le plan YZ local (une fois l'asset
    tourné vers le couloir, la toile est perpendiculaire à la course : texte lisible dans les deux sens)."""
    fond, encre = _NOBORI[variant % len(_NOBORI)]
    larg = 1.5
    with b.group("Nobori"):
        b.box((-0.7, 0, -0.7), (0.7, 0.6, 0.7), c("pierre_fonce"), studs="top", name="Lest")
        b.cyl((0, 0.6 + hauteur / 2, 0), 0.16, hauteur, c("bois_fonce"), collide=False, name="Mat")
        b.box((-0.1, hauteur - 0.2, -larg - 0.4), (0.1, hauteur + 0.05, -0.1), c("bois_fonce"), collide=False, name="Bras")
        y1, y0 = hauteur - 0.2, hauteur - 0.2 - (1.2 + 1.6 * len(texte))
        for sx, face in ((-1, "Left"), (1, "Right")):
            xa, xb = sorted((0.0, sx * 0.07))
            t = b.box((xa, y0, -larg - 0.3), (xb, y1, -0.3), c(fond), collide=False, shadow=False, name="Toile")
            t.label = {"face": face, "text": texte, "color": encre, "font": "brush", "vertical": True}
        b.box((-0.11, y0, -larg - 0.4), (0.11, y0 + 0.4, -larg - 0.2), c(fond), collide=False, shadow=False, name="Ourlet")
    return {"emprise": (1.4, larg + 1.2), "hauteur": hauteur + 0.6}


# ---------------------------------------------------------------------------
# Marchandises et objets de rue
# ---------------------------------------------------------------------------

def tonneaux(b, variant: int = 0) -> dict:
    """Deux ou trois tonneaux de bois cerclés (eau, sauce, saké exclu : rien d'écrit)."""
    with b.group("Tonneaux"):
        for x, z in ((-1.1, 0), (1.1, 0.3), (0, 1.9))[: 2 + variant % 2]:
            b.cyl((x, 1.4, z), 1.0, 2.8, c("bois_moyen"), axis="y", name="Tonneau")
            for y in (0.6, 2.2):
                b.cyl((x, y, z), 1.06, 0.25, c("bois_fonce"), axis="y", collide=False, name="Cercle")
            b.cyl((x, 2.85, z), 0.85, 0.1, c("bois_clair"), axis="y", collide=False, name="Couvercle")
    return {"emprise": (4.2, 4), "hauteur": 2.9}


def caisses(b, variant: int = 0) -> dict:
    """Pile de caisses de bois cerclées, légèrement de travers."""
    rng = b.rng
    pile = [((-1.2, 0, 0), 2.2), ((1.3, 0, 0.3), 2.0), ((-0.2, 2.2, 0.1), 1.8)][: 2 + variant % 2]
    with b.group("Caisses"):
        for (x, y, z), s in pile:
            yaw = float(rng.uniform(-12, 12))
            b.boxc((x, y + s / 2, z), (s, s, s), c("bois_clair"), yaw=yaw, studs="top", name="Caisse")
            b.boxc((x, y + s / 2, z), (s + 0.12, s * 0.22, s + 0.12), c("bois_moyen"), yaw=yaw, collide=False, name="Cerclage")
    return {"emprise": (5, 3), "hauteur": 4.0}


def sacs_riz(b, variant: int = 0) -> dict:
    """Ballots de riz en paille (tawara) couchés et empilés, liens de corde sombres."""
    paille = c("chaume")
    pile = [(-1.0, 0.95), (1.0, 0.95), (0.0, 2.65)] if variant % 2 == 0 else [(-1.0, 0.95), (1.0, 0.95), (3.0, 0.95), (2.0, 2.65)]
    with b.group("SacsRiz"):
        for i, (x, y) in enumerate(pile):
            col = paille if i % 2 == 0 else shade(paille, 0.92)
            b.cyl((x, y, 0), 0.95, 3.0, col, axis="z", name="Ballot")
            for z in (-0.9, 0.9):
                b.cyl((x, y, z), 1.0, 0.18, c("bois_fonce"), axis="z", collide=False, shadow=False, name="Lien")
    return {"emprise": (2.2 + 2 * (variant % 2), 3.0), "hauteur": 3.6}


def seaux_incendie(b, variant: int = 0) -> dict:
    """Seaux d'incendie empilés en pyramide sur un petit chevalet, à côté d'un tonneau d'eau (motif des rues
    de bois, qui répond aux tours de guet). Seaux rouges ou bois selon la variante."""
    seau = c("laque_rouge") if variant % 2 == 0 else c("bois_moyen")
    with b.group("SeauxIncendie"):
        b.box((-2.0, 0, -0.9), (2.0, 0.9, 0.9), c("bois_fonce"), studs="top", name="Chevalet")
        rangs = ((-1.35, 0.9), (0.0, 0.9), (1.35, 0.9), (-0.68, 2.1), (0.68, 2.1), (0.0, 3.3))
        for x, y in rangs:
            b.cyl((x, y + 0.6, 0), 0.62, 1.2, seau, axis="y", name="Seau")
            b.cyl((x, y + 1.0, 0), 0.68, 0.12, c("noir"), axis="y", collide=False, shadow=False, name="Bord")
        b.cyl((3.3, 1.3, 0.2), 1.1, 2.6, c("bois_moyen"), axis="y", name="Tonneau")
        b.cyl((3.3, 2.65, 0.2), 0.95, 0.12, c("eau"), axis="y", collide=False, shadow=False, name="Eau")
        b.cyl((3.3, 0.6, 0.2), 1.16, 0.25, c("bois_fonce"), axis="y", collide=False, name="Cercle")
        b.cyl((3.3, 2.1, 0.2), 1.16, 0.25, c("bois_fonce"), axis="y", collide=False, name="Cercle")
    return {"emprise": (6.5, 2.4), "hauteur": 4.5}


def charrette(b, variant: int = 0) -> dict:
    """Charrette à bras (daihachi) : deux grandes roues à moyeu, plateau de planches, deux brancards et leur
    traverse vers l'avant (-Z), chargement de ballots ou de caisses selon la variante."""
    bois, bois_f = c("bois_moyen"), c("bois_fonce")
    with b.group("Charrette"):
        for sx in (-1, 1):
            x = sx * 2.0
            b.cyl((x, 1.8, 0.6), 1.8, 0.35, bois_f, axis="x", name="Roue")
            b.cyl((x + sx * 0.12, 1.8, 0.6), 1.25, 0.36, bois, axis="x", collide=False, name="Jante")
            b.cyl((x + sx * 0.2, 1.8, 0.6), 0.4, 0.5, c("fer"), axis="x", collide=False, name="Moyeu")
        b.cyl((0, 1.8, 0.6), 0.18, 4.4, c("fer"), axis="x", collide=False, name="Essieu")
        b.box((-1.7, 2.1, -1.6), (1.7, 2.5, 3.0), c("bois_clair"), studs="top", name="Plateau")
        for sx in (-1, 1):
            b.box((sx * 1.5 - 0.15, 2.0, -5.2), (sx * 1.5 + 0.15, 2.3, -1.6), bois_f, collide=False, name="Brancard")
        b.box((-1.65, 2.0, -5.2), (1.65, 2.3, -4.9), bois_f, collide=False, name="Traverse")
        b.box((-0.2, 0, -5.15), (0.2, 2.0, -4.95), bois_f, collide=False, name="Bequille")
        if variant % 2 == 0:
            for i, z in enumerate((-0.6, 1.0, 2.4)):
                b.cyl((0, 3.35, z), 0.85, 3.0, c("chaume") if i % 2 == 0 else shade(c("chaume"), 0.92), axis="x", collide=False, name="Ballot")
        else:
            b.box((-1.4, 2.5, -1.3), (0.1, 4.0, 0.3), c("bois_clair"), studs="top", collide=False, name="Caisse")
            b.box((0.2, 2.5, -0.4), (1.5, 3.8, 1.2), shade(c("bois_clair"), 0.92), studs="top", collide=False, name="Caisse")
            b.box((-1.2, 2.5, 1.0), (0.4, 3.4, 2.6), c("toile_ecrue"), collide=False, name="Sac")
    return {"emprise": (4.4, 8.2), "hauteur": 4.2}


def puits(b, variant: int = 0) -> dict:
    """Puits de quartier : margelle carrée de pierre (ou de bois) creuse, eau sombre, deux poteaux, petit toit
    à deux pans (tuiles grises ou ocre), traverse, poulie et seau."""
    marg = c("pierre") if variant % 2 == 0 else c("bois_moyen")
    toit = c("tuile_grise") if variant % 2 == 0 else c("ocre")
    with b.group("Puits"):
        b.box((-2.2, 0, -2.2), (2.2, 0.4, 2.2), c("pierre_fonce"), studs="top", name="Dalle")
        b.box((-1.8, 0.4, -1.8), (1.8, 2.4, -1.2), marg, studs="top", name="Margelle")
        b.box((-1.8, 0.4, 1.2), (1.8, 2.4, 1.8), marg, studs="top", name="Margelle")
        b.box((-1.8, 0.4, -1.2), (-1.2, 2.4, 1.2), marg, studs="top", name="Margelle")
        b.box((1.2, 0.4, -1.2), (1.8, 2.4, 1.2), marg, studs="top", name="Margelle")
        b.box((-1.2, 0.4, -1.2), (1.2, 1.6, 1.2), c("eau_fonce"), collide=False, name="Eau")
        for sx in (-1, 1):
            b.box((sx * 1.5 - 0.25, 2.4, -0.25), (sx * 1.5 + 0.25, 6.6, 0.25), c("bois_fonce"), name="Poteau")
        b.box((-2.0, 6.6, -0.3), (2.0, 7.0, 0.3), c("bois_fonce"), name="Traverse")
        b.cyl((0, 6.2, 0), 0.45, 0.3, c("bois_moyen"), axis="x", collide=False, name="Poulie")
        b.box((-0.04, 3.6, -0.04), (0.04, 5.9, 0.04), c("corde"), collide=False, shadow=False, name="Corde")
        b.cyl((0.0, 3.2, 0.0), 0.45, 0.8, c("bois_moyen"), axis="y", collide=False, name="Seau")
        b.wedge((-2.4, 7.0, -1.8), (2.4, 8.4, 0), toit, down="-z", studs="top", name="Toit")
        b.wedge((-2.4, 7.0, 0), (2.4, 8.4, 1.8), toit, down="+z", studs="top", name="Toit")
    return {"emprise": (4.8, 4.4), "hauteur": 8.4}


def banc(b, variant: int = 0) -> dict:
    """Banc : 0 banc de thé à feutre rouge, 1 banc de pierre pâle, 2 banc de bois clair."""
    with b.group("Banc"):
        if variant % 3 == 1:
            for x in (-2.4, 2.4):
                b.box((x - 0.5, 0, -0.9), (x + 0.5, 1.4, 0.9), c("pierre_fonce"), name="Pied")
            b.box((-3.2, 1.4, -1.1), (3.2, 1.9, 1.1), c("pierre_claire"), studs="top", name="Assise")
            return {"emprise": (6.4, 2.2), "hauteur": 1.9}
        for x in (-2.6, 2.6):
            for z in (-0.8, 0.8):
                b.box((x - 0.25, 0, z - 0.25), (x + 0.25, 1.5, z + 0.25), c("bois_fonce"), name="Pied")
        b.box((-3.2, 1.5, -1.2), (3.2, 1.8, 1.2), c("bois") if variant % 3 == 0 else c("bois_clair"), studs="top", name="Plateau")
        if variant % 3 == 0:
            b.box((-3.3, 1.8, -1.3), (3.3, 2.0, 1.3), c("rouge"), studs="top", name="Feutre")
            b.box((-3.3, 1.2, -1.42), (3.3, 2.0, -1.3), c("rouge"), collide=False, name="Rabat")
    return {"emprise": (6.6, 2.8), "hauteur": 2.0}


def etal(b, variant: int = 0) -> dict:
    """Étal bas devant une boutique : table de bois, paniers ronds de fruits ou de légumes colorés."""
    rng = b.rng
    contenus = (("ocre_clair", "rouge", "feuille_claire"), ("sakura_vif", "jaune_lampion", "feuille"),
                ("blanc_creme", "orange_lampion", "culture"))[variant % 3]
    with b.group("Etal"):
        for x in (-2.3, 2.3):
            b.box((x - 0.2, 0, -0.9), (x + 0.2, 1.6, 0.9), c("bois_fonce"), name="Pied")
        b.box((-2.8, 1.6, -1.2), (2.8, 2.0, 1.2), c("bois_clair"), studs="top", name="Table")
        for i, x in enumerate((-1.75, 0.0, 1.75)):
            b.cyl((x, 2.3, 0), 0.8, 0.6, c("sudare"), axis="y", collide=False, name="Panier")
            b.box((x - 0.5, 2.6, -0.5), (x + 0.5, 3.0 + 0.1 * float(rng.integers(0, 3)), 0.5), c(contenus[i]), studs="top",
                  collide=False, name="Contenu")
    return {"emprise": (5.6, 2.4), "hauteur": 3.2}


def pot_plante(b, variant: int = 0) -> dict:
    """Pot de céramique (bleu, ocre ou blanc) avec un arbuste taillé ou un petit pin."""
    pot = (c("bleu_profond"), c("ocre_fonce"), c("blanc_creme"))[variant % 3]
    with b.group("Pot"):
        b.box((-1.0, 0, -1.0), (1.0, 1.5, 1.0), pot, name="Pot")
        b.box((-1.15, 1.5, -1.15), (1.15, 1.8, 1.15), shade(pot, 0.85), name="Levre")
        b.box((-0.85, 1.8, -0.85), (0.85, 1.9, 0.85), c("terre_fonce"), collide=False, name="Terre")
        if variant % 2 == 0:
            b.box((-1.3, 1.9, -1.3), (1.3, 3.3, 1.3), c("feuille"), studs="top", collide=False, name="Feuillage")
            b.box((-0.8, 3.3, -0.8), (0.8, 4.0, 0.8), c("feuille_claire"), studs="top", collide=False, name="Feuillage")
        else:
            b.box((-0.15, 1.9, -0.15), (0.15, 3.4, 0.15), c("tronc"), collide=False, name="Tronc")
            b.box((-1.3, 3.0, -0.8), (0.4, 3.7, 0.8), c("pin"), studs="top", collide=False, name="Plateau")
            b.box((-0.2, 3.9, -0.7), (1.2, 4.5, 0.7), c("pin_clair"), studs="top", collide=False, name="Plateau")
    return {"emprise": (2.6, 2.6), "hauteur": 4.5}


# ---------------------------------------------------------------------------
# Clôtures
# ---------------------------------------------------------------------------

def cloture_bois(b, longueur: float = 12, variant: int = 0, hauteur: float = 3.4) -> dict:
    """Clôture basse de planches le long de X local : poteaux, lisses, planches jointives (un seul bloc par
    travée pour économiser les pièces). Bois patiné ou sombre selon la variante."""
    bois = c("bois_gris") if variant % 2 == 0 else c("bois")
    with b.group("ClotureBois"):
        n = max(2, int(longueur // 4) + 1)
        for i in range(n):
            x = -longueur / 2 + i * longueur / (n - 1)
            b.box((x - 0.3, 0, -0.3), (x + 0.3, hauteur + 0.4, 0.3), c("bois_fonce"), name="Poteau")
        b.box((-longueur / 2, 0.3, -0.08), (longueur / 2, hauteur, 0.12), bois, name="Planches")
        b.box((-longueur / 2, hauteur - 0.5, -0.42), (longueur / 2, hauteur - 0.1, -0.08), c("bois_fonce"), collide=False, name="Lisse")
        b.box((-longueur / 2, 0.6, -0.42), (longueur / 2, 1.0, -0.08), c("bois_fonce"), collide=False, name="Lisse")
    return {"emprise": (longueur, 0.7), "hauteur": hauteur + 0.4}


def cloture_bambou(b, longueur: float = 12, variant: int = 0, hauteur: float = 4.0) -> dict:
    """Clôture de bambou (yotsume-gaki) le long de X local : poteaux, traverses, liens noirs."""
    with b.group("ClotureBambou"):
        n = max(2, int(longueur // 2.5) + 1)
        for i in range(n):
            x = -longueur / 2 + i * longueur / (n - 1)
            b.cyl((x, hauteur / 2, 0), 0.28, hauteur, c("vert_bambou" if i % 2 else "vert_bambou_fonce"), axis="y", name="Poteau")
        for y in (hauteur * 0.35, hauteur * 0.75):
            b.cyl((0, y, -0.35), 0.2, longueur, c("vert_bambou"), axis="x", collide=False, name="Traverse")
    return {"emprise": (longueur, 0.8), "hauteur": hauteur}


__all__ = [
    "TEXTES", "lanterne_pierre", "lanterne_poteau", "pilier_lanterne", "mat_guirlande", "guirlande_lampions",
    "panneau", "nobori", "tonneaux", "caisses", "sacs_riz", "seaux_incendie", "charrette", "puits", "banc",
    "etal", "pot_plante", "cloture_bois", "cloture_bambou",
]
