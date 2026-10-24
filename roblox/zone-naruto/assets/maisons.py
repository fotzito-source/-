"""Bâtiments de rue de Konoha, style « stud » : boutiques, immeubles à citernes, stand de ramen, maisons.

Ce sont les assets les plus vus de la zone (20 à 30 exemplaires le long du couloir) : chaque fonction
a 4 variantes nettement différentes (couleurs, nombre d'étages, type de toit, enseignes, détails),
et `variant // 4` décale encore la palette pour les exemplaires suivants.

Repère (voir CONVENTIONS.md) : origine au centre de l'emprise au sol, y = 0 au sol, l'AVANT regarde -Z
(la rue). `largeur` est le long de X, `profondeur` le long de Z. Les débords vers la rue (auvents,
enseignes, marches) restent sous 4 studs ; les débords latéraux sous 0,6 stud (les voisins sont à 2 studs).

Les sous-ensembles « de façade » (fenêtres, enseignes, climatiseurs, tuyaux) se dessinent dans un repère
où la façade est le plan z = 0 et où l'extérieur est vers -z ; on les pose avec `b.at(...)`
(yaw = -90 pour la façade droite +X, yaw = 90 pour la façade gauche -X).
"""

from __future__ import annotations

import math

from kit import hexrgb, mix, rot_z, shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Couleurs locales (en plus de la palette)
# ---------------------------------------------------------------------------
FER = "#3A3F44"            # rambardes, ferrures
PAPIER = "#F7F0DA"         # papier des shoji
INTERIEUR = "#3A2A22"      # fond sombre d'une boutique ouverte
BOIS_SOMBRE = "#4A2E1C"
POT_TERRE = "#B5643A"
POT_BLEU = "#4F79A8"
DANGO = ("#F4A7B9", "#FAF3E3", "#9CCB6B")   # rose, blanc, vert (dango tricolore)


def col(x):
    """Nom de palette, '#hex' ou tuple → tuple RGB."""
    if isinstance(x, tuple):
        return x
    if isinstance(x, str) and x.startswith("#"):
        return hexrgb(x)
    return c(x)


def vr(x, rng, amount=0.06):
    """`vary` qui accepte aussi '#hex' et les tuples."""
    return vary(col(x), rng, amount)


# ---------------------------------------------------------------------------
# Sous-ensembles de façade (plan z = 0, extérieur vers -z)
# ---------------------------------------------------------------------------

def _fenetre(b, x, y, w, h, cadre, vitre, *, croix="v", cotes=True, appui=None, auvent=None, volets=None):
    """Fenêtre : vitre en retrait, cadre en saillie, appui stud, petit auvent optionnel. (x, y) = milieu bas."""
    hw = w / 2
    cadre = col(cadre)
    b.box((x - hw, y, -0.15), (x + hw, y + h, 0.3), col(vitre), name="Vitre")
    b.box((x - hw - 0.4, y + h, -0.45), (x + hw + 0.4, y + h + 0.45, 0.3), cadre, name="Linteau")
    if cotes:
        b.box((x - hw - 0.4, y, -0.45), (x - hw, y + h, 0.3), cadre, name="Montant")
        b.box((x + hw, y, -0.45), (x + hw + 0.4, y + h, 0.3), cadre, name="Montant")
    b.box((x - hw - 0.6, y - 0.5, -0.8), (x + hw + 0.6, y, 0.3), col(appui) if appui else cadre, studs="top", name="Appui")
    if croix in ("v", "+"):
        b.box((x - 0.15, y, -0.35), (x + 0.15, y + h, 0.3), cadre, name="Meneau")
    if croix in ("h", "+"):
        b.box((x - hw, y + h * 0.55 - 0.15, -0.3), (x + hw, y + h * 0.55 + 0.15, 0.3), cadre, name="Traverse")
    if volets is not None:
        for s in (-1, 1):
            xa = x + s * (hw + 0.4)
            b.box((min(xa, xa + s * 1.4), y + 0.1, -0.3), (max(xa, xa + s * 1.4), y + h - 0.1, 0.3), col(volets), name="Volet")
    if auvent is not None:
        b.wedge((x - hw - 0.9, y + h + 0.45, -1.7), (x + hw + 0.9, y + h + 1.45, 0.3), col(auvent), down="-z",
                studs="top", name="Auvent")


def _porte(b, x, y, w, h, bois, fond, *, montants=True):
    """Porte pleine en bois (deux battants) avec chambranle."""
    hw = w / 2
    b.box((x - hw, y, -0.2), (x + hw, y + h, 0.3), col(fond), name="Porte")
    b.box((x - 0.1, y, -0.3), (x + 0.1, y + h, 0.3), col(bois), name="Porte")
    b.box((x - hw - 0.5, y + h, -0.5), (x + hw + 0.5, y + h + 0.5, 0.3), col(bois), name="Chambranle")
    if montants:
        b.box((x - hw - 0.5, y, -0.5), (x - hw, y + h, 0.3), col(bois), name="Chambranle")
        b.box((x + hw, y, -0.5), (x + hw + 0.5, y + h, 0.3), col(bois), name="Chambranle")


def _shoji(b, xa, xb, y0, y1, bois, papier=PAPIER, pas=0.95):
    """Portes coulissantes à claire-voie (koshi) : papier derrière, lattes verticales, plinthe et traverses."""
    bois = col(bois)
    b.box((xa, y0, -0.15), (xb, y1, 0.3), col(papier), name="Papier")
    b.box((xa, y0, -0.45), (xb, y0 + 1.4, -0.15), bois, name="Plinthe")
    b.box((xa, y1 - 0.8, -0.45), (xb, y1, -0.15), bois, name="Traverse")
    ym = y0 + 1.4 + (y1 - 0.8 - y0 - 1.4) * 0.45
    b.box((xa, ym - 0.15, -0.35), (xb, ym + 0.15, -0.15), bois, name="Traverse")
    n = max(2, int(round((xb - xa) / pas)))
    for i in range(1, n):
        xx = xa + i * (xb - xa) / n
        wl = 0.18 if i != n // 2 else 0.3
        b.box((xx - wl, y0 + 1.4, -0.42 if i != n // 2 else -0.5), (xx + wl, y1 - 0.8, -0.15), bois, name="Latte")


def _noren(b, xa, xb, y_haut, h, z, fond, encre, texte, n=None, font="brush"):
    """Rideau noren : tringle + lés séparés, un caractère par lé (texte plus court → lés unis)."""
    n = n or max(2, len(texte))
    gap = 0.18
    lw = (xb - xa - gap * (n - 1)) / n
    b.box((xa - 0.2, y_haut - 0.3, z - 0.2), (xb + 0.2, y_haut, z + 0.2), col(BOIS_SOMBRE), collide=False, name="Tringle")
    fond = col(fond)
    for i in range(n):
        x = xa + i * (lw + gap)
        p = b.box((x, y_haut - 0.3 - h, z - 0.1), (x + lw, y_haut - 0.3, z + 0.1), fond, collide=False,
                  material="Fabric", name="Noren")
        ch = texte[i] if i < len(texte) else ""
        if ch.strip():
            p.label = {"face": "Front", "text": ch, "color": col(encre), "font": font}


def _enseigne_v(b, x, y0, h, texte, fond, encre, cadre, *, larg=2.2, sortie=1.4, bras=None, chapeau=None):
    """Enseigne verticale perpendiculaire à la façade : lisible des deux sens de la rue.
    Bras de fixation aux hauteurs `bras` (sinon haut et bas du panneau)."""
    zc = -(sortie + larg / 2 + 0.3)
    z_av, z_ar = zc - larg / 2, zc + larg / 2
    b.box((x - 0.2, y0 - 0.3, z_av - 0.3), (x + 0.2, y0 + h + 0.3, z_ar + 0.3), col(cadre), collide=False, name="Cadre")
    for s, face in ((-1, "Left"), (1, "Right")):
        xa, xb = sorted((x + s * 0.2, x + s * 0.34))
        p = b.box((xa, y0, z_av), (xb, y0 + h, z_ar), col(fond), collide=False, name="Enseigne")
        p.label = {"face": face, "text": texte, "color": col(encre), "font": "brush", "vertical": True}
    for yb in (bras or (y0 + 0.2, y0 + h - 0.6)):
        b.box((x - 0.15, yb, z_ar + 0.3), (x + 0.15, yb + 0.35, 0.25), col(FER), collide=False, name="Bras")
    if chapeau is not None:
        b.box((x - 0.55, y0 + h + 0.3, z_av - 0.6), (x + 0.55, y0 + h + 0.7, z_ar + 0.6), col(chapeau), collide=False,
              studs="top", name="Chapeau")


def _enseigne_h(b, x, y, w, h, texte, fond, encre, cadre, *, font="brush"):
    """Panneau horizontal (kanban) plaqué sur la façade."""
    b.box((x - w / 2 - 0.35, y - 0.35, -0.4), (x + w / 2 + 0.35, y + h + 0.35, 0.25), col(cadre), name="Cadre")
    p = b.box((x - w / 2, y, -0.6), (x + w / 2, y + h, -0.3), col(fond), name="Kanban")
    p.label = {"face": "Front", "text": texte, "color": col(encre), "font": font}
    return p


def _balcon(b, xa, xb, y, prof, sol, garde, *, h=2.4, pas=1.1, plein=False, rng=None):
    """Balcon (plan z = 0) : dalle stud en y, garde-corps à barreaux (ou plein) avec lisse haute."""
    b.box((xa, y - 0.6, -prof), (xb, y, 0.3), col(sol), studs="top", name="Balcon")
    g = col(garde)
    b.box((xa, y + h - 0.3, -prof), (xb, y + h, -prof + 0.3), g, studs="top", name="Lisse")
    for xx in (xa, xb - 0.3):
        b.box((xx, y + h - 0.3, -prof + 0.3), (xx + 0.3, y + h, 0.2), g, studs="top", name="Lisse")
    if plein:
        pc = col(plein) if not isinstance(plein, bool) else g
        b.box((xa + 0.05, y, -prof + 0.05), (xb - 0.05, y + h - 0.3, -prof + 0.3), pc, name="Garde")
        for xx in (xa + 0.05, xb - 0.3):
            b.box((xx, y, -prof + 0.3), (xx + 0.25, y + h - 0.3, 0.2), pc, name="Garde")
    else:
        n = max(2, int(round((xb - xa - 0.3) / pas)))
        for i in range(n + 1):
            xx = xa + 0.15 + i * (xb - xa - 0.3) / n
            b.box((xx - 0.1, y, -prof + 0.05), (xx + 0.1, y + h - 0.3, -prof + 0.25), g, name="Barreau")
        for xx in (xa + 0.15, xb - 0.15):
            b.box((xx - 0.1, y, -prof / 2 - 0.1), (xx + 0.1, y + h - 0.3, -prof / 2 + 0.1), g, name="Barreau")


def _garde_corps(b, pts, y, couleur=FER, h=2.2, pas=1.2):
    """Garde-corps le long d'une polyligne horizontale [(x, z), ...] (segments parallèles aux axes) posé en y."""
    g = col(couleur)
    for (xa, za), (xb, zb) in zip(pts[:-1], pts[1:]):
        lo_x, hi_x, lo_z, hi_z = min(xa, xb), max(xa, xb), min(za, zb), max(za, zb)
        b.box((lo_x - 0.15, y + h - 0.3, lo_z - 0.15), (hi_x + 0.15, y + h, hi_z + 0.15), g, studs="top", name="Lisse")
        L = max(hi_x - lo_x, hi_z - lo_z)
        n = max(1, int(round(L / pas)))
        for i in range(n):
            t = i / n
            px, pz = xa + (xb - xa) * t, za + (zb - za) * t
            b.box((px - 0.1, y, pz - 0.1), (px + 0.1, y + h - 0.3, pz + 0.1), g, name="Barreau")
    px, pz = pts[-1]
    b.box((px - 0.1, y, pz - 0.1), (px + 0.1, y + h - 0.3, pz + 0.1), g, name="Barreau")


def _porte_fenetre(b, x, y, w, h, cadre, vitre):
    """Porte-fenêtre de balcon : vitre pleine hauteur, montants, traverse, linteau."""
    _fenetre(b, x, y + 0.5, w, h - 0.5, cadre, vitre, croix="+", appui=None)


def _clim(b, x, y, corps="blanc"):
    """Climatiseur posé sur la façade sur deux équerres. (x, y) = milieu bas."""
    b.box((x - 1.3, y, -1.3), (x + 1.3, y + 1.8, 0.2), col(corps), name="Clim")
    b.cyl((x + 0.4, y + 0.9, -1.35), 0.62, 0.2, col("metal_fonce"), axis="z", collide=False, name="Ventilateur")
    b.box((x - 1.05, y + 0.35, -1.36), (x - 0.55, y + 1.45, -1.25), col("metal"), collide=False, name="Grille")
    for xx in (x - 0.9, x + 0.9):
        b.box((xx - 0.1, y - 0.5, -1.0), (xx + 0.1, y, 0.2), col(FER), collide=False, name="Equerre")


def _motif(b, xa, xb, ya, yb, base, rng, dens=0.14, cell=(2.0, 1.0), teintes=(0.93, 1.05, 0.96)):
    """Murs « pixel » : taches rectangulaires de teinte voisine (comme les murs stud de la référence).
    Plaquées à 0,08 stud du mur, sans chevauchement, à 0,5 stud des arêtes (pas de z-fighting)."""
    cw, ch = cell
    xa, xb, ya, yb = xa + 0.5, xb - 0.5, ya + 0.3, yb - 0.3
    nx, ny = int((xb - xa) / cw), int((yb - ya) / ch)
    if nx < 2 or ny < 1:
        return
    occ = [[False] * nx for _ in range(ny)]
    base = col(base)
    for _ in range(int(nx * ny * dens)):
        w = int(rng.choice((1, 1, 2, 2, 3)))
        h = int(rng.choice((1, 1, 2)))
        i = int(rng.integers(0, max(1, nx - w + 1)))
        j = int(rng.integers(0, max(1, ny - h + 1)))
        if any(occ[jj][ii] for jj in range(max(0, j - 1), min(ny, j + h + 1)) for ii in range(max(0, i - 1), min(nx, i + w + 1))):
            continue
        for jj in range(j, min(ny, j + h)):
            for ii in range(i, min(nx, i + w)):
                occ[jj][ii] = True
        f = float(teintes[int(rng.integers(0, len(teintes)))])
        b.box((xa + i * cw, ya + j * ch, -0.08), (xa + min(nx, i + w) * cw, ya + min(ny, j + h) * ch, 0.1), shade(base, f),
              collide=False, name="Pixel")


def _tuyau(b, pts, r=0.3, couleur="tuyau", ancre_haut=True, ancre_bas=False):
    """Tuyau qui court sur la façade : polyligne de segments horizontaux / verticaux (x, y), coudes en boule."""
    cc = col(couleur)
    z = -r * 0.85
    for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
        if abs(xa - xb) < 1e-6:
            b.cyl((xa, (ya + yb) / 2, z), r, abs(yb - ya), cc, axis="y", collide=False, name="Tuyau")
        else:
            b.cyl(((xa + xb) / 2, ya, z), r, abs(xb - xa), cc, axis="x", collide=False, name="Tuyau")
    for (xa, ya) in pts[1:-1]:
        b.ball((xa, ya, z), r * 1.15, cc, collide=False, name="Coude")
    ends = []
    if ancre_haut:
        ends.append(pts[0])
    if ancre_bas:
        ends.append(pts[-1])
    for (xa, ya) in ends:  # le tuyau ressort du mur
        b.cyl((xa, ya, z / 2 + 0.1), r * 1.2, abs(z) + 0.2, shade(cc, 0.85), axis="z", collide=False, name="Bride")


def _lampion(b, x, y_haut, z, r=0.8, couleur="rouge", corde=0.5, cap="noir"):
    """Lampion rond suspendu (cordon, chapeau, boule, culot)."""
    b.box((x - 0.07, y_haut - corde, z - 0.07), (x + 0.07, y_haut, z + 0.07), col("noir"), collide=False, name="Cordon")
    cy = y_haut - corde - r
    b.cyl((x, cy + r * 0.92, z), r * 0.5, 0.3, col(cap), axis="y", collide=False, name="Chapeau")
    b.ball((x, cy, z), r, col(couleur), collide=False, name="Lampion")
    b.cyl((x, cy - r * 0.92, z), r * 0.5, 0.3, col(cap), axis="y", collide=False, name="Culot")


def _plante(b, x, y, z, r=0.9, pot=POT_TERRE, feuille="feuille", fleur=None, rng=None):
    """Plante en pot : pot cylindrique + boule de feuillage (+ fleurs)."""
    b.cyl((x, y + 0.6, z), r * 0.75, 1.2, col(pot), axis="y", studs="top", name="Pot")
    b.ball((x, y + 1.2 + r * 0.75, z), r, col(feuille) if rng is None else vr(feuille, rng, 0.08), collide=False, name="Feuillage")
    if fleur is not None:
        b.ball((x + r * 0.45, y + 1.35 + r * 1.2, z - r * 0.35), r * 0.38, col(fleur), collide=False, name="Fleur")


def _citerne(b, x, y, z, r, h, couleur="citerne", pieds=1.4, cerclage=None):
    """Citerne d'eau verticale sur pieds (le grand signe des toits de Konoha) : fût, dôme, cerclages."""
    cc = col(couleur)
    for dx, dz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        px, pz = x + dx * r * 0.62, z + dz * r * 0.62
        b.box((px - 0.25, y, pz - 0.25), (px + 0.25, y + pieds + 0.2, pz + 0.25), col(FER), name="Pied")
    b.cyl((x, y + pieds + 0.15, z), r * 0.92, 0.3, col("metal_fonce"), axis="y", name="Socle")
    b.cyl((x, y + pieds + 0.3 + h / 2, z), r, h, cc, axis="y", name="Citerne")
    cer = col(cerclage) if cerclage else shade(cc, 0.82)
    for f in (0.25, 0.75):
        b.cyl((x, y + pieds + 0.3 + h * f, z), r + 0.12, 0.35, cer, axis="y", name="Cerclage")
    b.ball((x, y + pieds + 0.3 + h, z), r * 0.97, cc, name="Dome")
    b.cyl((x, y + pieds + 0.3 + h + r * 0.97, z), 0.3, 0.5, cer, axis="y", name="Event")
    return y + pieds + 0.3 + h + r


def _abri_toit(b, x, y, z, w, d, h, mur, toit, porte="bois"):
    """Petit édicule de toit (cage d'escalier) : boîte, porte, toit en appentis."""
    b.box((x - w / 2, y, z - d / 2), (x + w / 2, y + h, z + d / 2), col(mur), name="Edicule")
    with b.at((x, y, z - d / 2)):
        b.box((-0.9, 0, -0.2), (0.9, 3.4, 0.3), col(porte), name="Porte")
    b.wedge((x - w / 2 - 0.4, y + h, z - d / 2 - 0.8), (x + w / 2 + 0.4, y + h + 1.2, z + d / 2 + 0.4), col(toit),
            down="-z", studs="top", name="Appentis")


# ---------------------------------------------------------------------------
# Toits
# ---------------------------------------------------------------------------

def _toit_kirizuma(b, x0, x1, z0, z1, y, h, toit, *, rive=None, faitage=None, oni=True):
    """Toit à deux pans, faîtage parallèle à X (rue) : rive épaisse, deux coins stud, faîtage, épis."""
    t = col(toit)
    zm = (z0 + z1) / 2
    b.box((x0, y - 0.6, z0), (x1, y, z1), col(rive) if rive else shade(t, 0.7), name="Rive")
    b.wedge((x0, y, z0), (x1, y + h, zm), t, down="-z", studs="top", name="Pan")
    b.wedge((x0, y, zm), (x1, y + h, z1), t, down="+z", studs="top", name="Pan")
    fa = col(faitage) if faitage else shade(t, 0.62)
    b.box((x0 - 0.2, y + h - 0.45, zm - 0.75), (x1 + 0.2, y + h + 0.45, zm + 0.75), fa, studs="top", name="Faitage")
    if oni:
        for xe in (x0 + 0.15, x1 - 0.15):
            b.box((xe - 0.45, y + h - 0.25, zm - 0.95), (xe + 0.45, y + h + 0.85, zm + 0.95), fa, name="Epi")
    return y + h + (0.85 if oni else 0.45)


def _dalle_pente(b, xa, ya, xb, yb, z0, z1, ep, couleur, *, prolonge=0.0, studs="top", name="Pan"):
    """Dalle inclinée dans le plan XY : sa face supérieure passe par (xa, ya) et (xb, yb) (xa < xb),
    épaisseur `ep` sous cette ligne, étendue sur z0..z1 ; `prolonge` l'allonge côté b (faîtage)."""
    dx, dy = xb - xa, yb - ya
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux                      # normale vers le haut
    ang = math.degrees(math.atan2(dy, dx))
    Lt = L + abs(prolonge)
    sh = prolonge / 2                     # décalage du centre le long de la pente
    cx = (xa + xb) / 2 + ux * sh - nx * ep / 2
    cy = (ya + yb) / 2 + uy * sh - ny * ep / 2
    return b.part("block", (Lt, ep, z1 - z0), (cx, cy, (z0 + z1) / 2), rot_z(ang), col(couleur), studs=studs, name=name)


def _toit_pignon(b, xw0, xw1, zw0, zw1, H, pente, toit, mur, *, deb=1.4, deb_av=1.6, ep=0.8, bordure=None,
                 oculus=None, rng=None):
    """Pignon sur rue : faîtage parallèle à Z, triangle d'enduit face à la rue, deux dalles stud inclinées
    qui débordent largement (avant-toit), planches de rive, faîtage ; `oculus` = couleur des œils-de-bœuf."""
    t = col(toit)
    xm = (xw0 + xw1) / 2
    run = xm - xw0
    hu = run * pente                                   # hauteur du dessous du toit au faîtage
    k = ep * math.hypot(1, pente)                      # épaisseur verticale de la dalle
    z0, z1 = zw0 - deb_av, zw1 + deb
    # triangle d'enduit (tout le comble), légèrement plus pentu pour pénétrer la dalle
    m = col(mur) if rng is None else vr(mur, rng, 0.03)
    b.wedge((xw0, H, zw0), (xm, H + hu + 0.25, zw1), m, down="-x", name="Pignon")
    b.wedge((xm, H, zw0), (xw1, H + hu + 0.25, zw1), m, down="+x", name="Pignon")
    # dalles : ligne du dessus = dessous + k
    xe0, xe1 = xw0 - deb, xw1 + deb
    ye = H - deb * pente + k
    _dalle_pente(b, xe0, ye, xm, H + hu + k, z0, z1, ep, t, prolonge=0.5)
    _dalle_pente(b, xm, H + hu + k, xe1, ye, z0, z1, ep, t, prolonge=-0.5)
    # planches de rive (hafu) sur l'avant
    bo = col(bordure) if bordure else shade(t, 0.62)
    for (xa, ya, xb, yb, pr) in ((xe0, ye + 0.15, xm, H + hu + k + 0.15, 0.4), (xm, H + hu + k + 0.15, xe1, ye + 0.15, -0.4)):
        _dalle_pente(b, xa, ya, xb, yb, z0 - 0.35, z0 + 0.25, ep + 0.45, bo, prolonge=pr, studs="none", name="Rive")
    yr = H + hu + k
    b.box((xm - 0.8, yr - 0.4, z0 - 0.4), (xm + 0.8, yr + 0.55, z1 + 0.2), bo, studs="top", name="Faitage")
    # gegyo : pendentif décoratif sous le faîtage (cache la jonction des planches de rive)
    b.box((xm - 0.75, yr - 2.3, z0 - 0.55), (xm + 0.75, yr + 0.3, z0 + 0.3), bo, name="Gegyo")
    b.box((xm - 0.45, yr - 2.0, z0 - 0.7), (xm + 0.45, yr - 0.9, z0 - 0.5), col("jaune_lampion"), name="Gegyo")
    if oculus is not None:
        yo = H + hu * 0.42
        for xo in ((xm,) if run < 9 else (xm - 1.6, xm + 1.6)):
            b.cyl((xo, yo, zw0 - 0.1), 1.05, 0.5, col(BOIS_SOMBRE), axis="z", name="Oculus")
            b.cyl((xo, yo, zw0 - 0.25), 0.65, 0.5, col(oculus), axis="z", name="Oculus")
    return yr + 0.55


def _toit_irimoya(b, x0, x1, z0, z1, y, toit, mur, *, jupe=3.0, hj=1.8, hc=1.6, ht=3.6, rng=None):
    """Toit à croupe et pignon : jupe basse sur les 4 côtés, corps d'enduit, petit toit à deux pans au-dessus."""
    t = col(toit)
    b.box((x0, y - 0.6, z0), (x1, y, z1), shade(t, 0.7), name="Rive")
    b.wedge((x0, y, z0), (x1, y + hj, z0 + jupe), t, down="-z", studs="top", name="Jupe")
    b.wedge((x0, y, z1 - jupe), (x1, y + hj, z1), t, down="+z", studs="top", name="Jupe")
    b.wedge((x0, y, z0 + jupe), (x0 + jupe, y + hj, z1 - jupe), t, down="-x", studs="top", name="Jupe")
    b.wedge((x1 - jupe, y, z0 + jupe), (x1, y + hj, z1 - jupe), t, down="+x", studs="top", name="Jupe")
    m = col(mur) if rng is None else vr(mur, rng, 0.03)
    xa, xb, za, zb = x0 + jupe, x1 - jupe, z0 + jupe, z1 - jupe
    b.box((xa, y, za), (xb, y + hj + hc, zb), m, name="Comble")
    # petites poutres sous le toit haut
    b.box((xa - 0.2, y + hj + hc - 0.5, za - 0.2), (xb + 0.2, y + hj + hc, zb + 0.2), col(BOIS_SOMBRE), name="Poutre")
    return _toit_kirizuma(b, xa - 1.2, xb + 1.2, za - 1.6, zb + 1.6, y + hj + hc + 0.6, ht, t)


def _toit_croupe(b, x0, x1, z0, z1, y, h, toit, *, r=None):
    """Toit « à croupes » en coins : pans avant/arrière au milieu, pans latéraux sur toute la profondeur,
    petit faîtage. Les angles montrent un triangle vertical (lecture « bloc » assumée)."""
    t = col(toit)
    r = r or min((z1 - z0) / 2 - 0.5, (x1 - x0) / 2 - 0.5)
    b.box((x0, y - 0.6, z0), (x1, y, z1), shade(t, 0.7), name="Rive")
    b.wedge((x0 + r, y, z0), (x1 - r, y + h, z0 + r), t, down="-z", studs="top", name="Pan")
    b.wedge((x0 + r, y, z1 - r), (x1 - r, y + h, z1), t, down="+z", studs="top", name="Pan")
    b.wedge((x0, y, z0), (x0 + r, y + h, z1), t, down="-x", studs="top", name="Pan")
    b.wedge((x1 - r, y, z0), (x1, y + h, z1), t, down="+x", studs="top", name="Pan")
    if z1 - z0 - 2 * r > 0.1 and x1 - x0 - 2 * r > 0.1:
        b.box((x0 + r, y, z0 + r), (x1 - r, y + h, z1 - r), t, name="Coeur")
    fa = shade(t, 0.62)
    b.box((x0 + r - 0.6, y + h - 0.3, (z0 + z1) / 2 - 0.7), (x1 - r + 0.6, y + h + 0.5, (z0 + z1) / 2 + 0.7), fa,
          studs="top", name="Faitage")
    return y + h + 0.5


def _toit_plat(b, x0, x1, z0, z1, y, bord, sol="pave", *, acrotere=0.9):
    """Toit-terrasse : dalle de rive colorée qui déborde, sol stud, petit acrotère."""
    bc = col(bord)
    b.box((x0 - 0.4, y, z0 - 0.4), (x1 + 0.4, y + 0.8, z1 + 0.4), bc, studs="top", name="Rive")
    if acrotere:
        e = 0.6
        ya, yb = y + 0.8, y + 0.8 + acrotere
        b.box((x0 - 0.4, ya, z0 - 0.4), (x1 + 0.4, yb, z0 - 0.4 + e), bc, studs="top", name="Acrotere")
        b.box((x0 - 0.4, ya, z1 + 0.4 - e), (x1 + 0.4, yb, z1 + 0.4), bc, studs="top", name="Acrotere")
        b.box((x0 - 0.4, ya, z0 - 0.4 + e), (x0 - 0.4 + e, yb, z1 + 0.4 - e), bc, studs="top", name="Acrotere")
        b.box((x1 + 0.4 - e, ya, z0 - 0.4 + e), (x1 + 0.4, yb, z1 + 0.4 - e), bc, studs="top", name="Acrotere")
    return y + 0.8


def _mansarde(b, x0, x1, z0, z1, y, toit, *, jupe=2.6, hj=2.6, deb=1.0):
    """Jupe de toit pentue tout autour (comme les toits de cuivre de Konoha) avec terrasse au sommet."""
    t = col(toit)
    xa, xb, za, zb = x0 - deb, x1 + deb, z0 - deb, z1 + deb
    b.box((xa, y - 0.6, za), (xb, y, zb), shade(t, 0.7), name="Rive")
    b.wedge((xa, y, za), (xb, y + hj, za + jupe), t, down="-z", studs="top", name="Jupe")
    b.wedge((xa, y, zb - jupe), (xb, y + hj, zb), t, down="+z", studs="top", name="Jupe")
    b.wedge((xa, y, za + jupe), (xa + jupe, y + hj, zb - jupe), t, down="-x", studs="top", name="Jupe")
    b.wedge((xb - jupe, y, za + jupe), (xb, y + hj, zb - jupe), t, down="+x", studs="top", name="Jupe")
    b.box((xa + jupe, y, za + jupe), (xb - jupe, y + hj, zb - jupe), shade(t, 0.9), name="Coeur")
    b.box((xa + jupe - 0.3, y + hj, za + jupe - 0.3), (xb - jupe + 0.3, y + hj + 0.6, zb - jupe + 0.3), shade(t, 0.62),
          studs="top", name="Terrasse")
    return (xa + jupe, xb - jupe, za + jupe, zb - jupe, y + hj + 0.6)


# ---------------------------------------------------------------------------
# Petits accessoires de rue
# ---------------------------------------------------------------------------

def _banc(b, x, z, w, couleur="rouge"):
    """Banc bas (devant les salons de thé) avec tissu rouge."""
    for xx in (x - w / 2 + 0.4, x + w / 2 - 0.4):
        b.box((xx - 0.25, 0, z - 0.6), (xx + 0.25, 1.4, z + 0.6), col("bois_fonce"), name="Pied")
    b.box((x - w / 2, 1.4, z - 0.8), (x + w / 2, 1.8, z + 0.8), col("bois"), name="Banc")
    b.box((x - w / 2 + 0.3, 1.8, z - 0.7), (x + w / 2 - 0.3, 1.95, z + 0.7), col(couleur), material="Fabric", name="Tissu")


def _caisses(b, x, z, rng, couleurs=("bois_clair", "bois")):
    """Pile de caisses de livraison."""
    b.box((x - 1.0, 0, z - 0.9), (x + 1.0, 1.6, z + 0.9), vr(couleurs[0], rng, 0.05), studs="top", name="Caisse")
    b.box((x - 0.7, 1.6, z - 0.6), (x + 0.6, 2.8, z + 0.6), vr(couleurs[1], rng, 0.05), studs="top", name="Caisse")


def _dango(b, x, y, z):
    """Brochette de dango tricolore posée debout."""
    b.box((x - 0.06, y, z - 0.06), (x + 0.06, y + 2.3, z + 0.06), col("bois_clair"), collide=False, name="Pique")
    for i, cc in enumerate(DANGO[::-1]):
        b.ball((x, y + 0.6 + i * 0.6, z), 0.33, col(cc), collide=False, name="Dango")


def _distributeur(b, x, z, couleur="rouge"):
    """Distributeur de boissons (repère de rue de Konoha). Avant vers -z, posé contre un mur en z."""
    cc = col(couleur)
    b.box((x - 1.1, 0, z - 1.6), (x + 1.1, 4.4, z), cc, studs="top", name="Distributeur")
    b.box((x - 0.85, 2.0, z - 1.7), (x + 0.85, 3.9, z - 1.5), col("fenetre_claire"), material="Glass", name="Vitrine")
    for i, cc2 in enumerate(("#F2C14E", "#4FB6E0", "#E9573F", "#7BC86C")):
        b.box((x - 0.75 + i * 0.4, 2.3, z - 1.75), (x - 0.5 + i * 0.4, 3.0, z - 1.65), col(cc2), collide=False, name="Canette")
    b.box((x - 0.8, 0.6, z - 1.7), (x + 0.8, 1.2, z - 1.5), col("noir"), name="Trappe")


# ---------------------------------------------------------------------------
# BOUTIQUE
# ---------------------------------------------------------------------------

_BOUTIQUES = [
    # 0 : salon de thé & dango — saumon, toit rouge à deux pans, store rayé rouge/crème
    dict(etages=2, mur="saumon", toit="toit_rouge", forme="kirizuma", cadre="bois_fonce", vitre="fenetre",
         store=("rouge", "panneau"), noren=("noren_bleu", "blanc", "茶"), v=("甘味処", "panneau", "rouge_fonce", "bois_fonce"),
         h=("団子", "blanc", "rouge"), etal="dango", portes="droite", lampions="rouge", poteaux=False, banc=True),
    # 1 : boutique d'outils ninja — bleu pâle, 3 étages, jupe de toit en cuivre vert, citerne
    dict(etages=3, mur="bleu_pale", toit="toit_vert", forme="mansarde", cadre="bois", vitre="fenetre",
         store=("toit_vert",), noren=("noren_rouge", "blanc", "忍具"), v=("忍具屋", "blanc", "rouge", "rouge_fonce"),
         h=("手裏剣", "panneau", "noir"), etal="ninja", portes="gauche", lampions="orange_lampion", poteaux=False, banc=False,
         balcon=True),
    # 2 : fleuriste — crème à colombages, pignon bleu sur rue avec œils-de-bœuf
    dict(etages=2, mur="creme", toit="toit_bleu", forme="pignon", cadre="poutre", vitre="fenetre",
         store=("toit_bleu_clair", "blanc"), noren=("blanc", "noren_bleu", "花"), v=("花屋", "noren_bleu", "blanc", "bois_fonce"),
         h=("生花", "panneau", "toit_bleu"), etal="fleurs", portes="droite", lampions="blanc", poteaux=True, banc=False),
    # 3 : herboristerie — blanc cassé, 3 étages, auvent intermédiaire, toit irimoya orange
    dict(etages=3, mur="enduit", toit="toit_orange", forme="irimoya", cadre="bois_fonce", vitre="fenetre",
         store=("toit_brun",), noren=("noren_bleu", "blanc", "薬"), v=("漢方薬", "rouge", "blanc", "bois_fonce"),
         h=("薬", "panneau", "rouge_fonce"), etal="remedes", portes="gauche", lampions="rouge", poteaux=True, banc=False),
]

_MURS_ALT = ["rose_pale", "jaune_pale", "vert_pale", "saumon", "bleu_pale", "creme"]
_TOITS_ALT = ["toit_vert", "toit_bleu", "toit_rouge", "toit_orange", "toit_brun"]


def _style(table, variant):
    S = dict(table[variant % 4])
    k = variant // 4
    if k:
        S["mur"] = _MURS_ALT[(variant * 2 + k) % len(_MURS_ALT)]
        S["toit"] = _TOITS_ALT[(variant + k) % len(_TOITS_ALT)]
    return S


def _etal(b, kind, xa, xb, y, z, rng):
    """Marchandises posées sur le comptoir (plan y, devant en z, de xa à xb)."""
    w = xb - xa
    if kind == "dango":
        n = max(2, int(w / 1.6))
        for i in range(n):
            x = xa + (i + 0.5) * w / n
            if i % 2 == 0:
                _dango(b, x, y, z + 0.9)
            else:
                b.cyl((x, y + 0.75, z + 0.9), 0.55, 1.5, vr("#7B9E5A", rng, 0.06), axis="y", studs="top", name="Pot_the")
    elif kind == "ninja":
        b.box((xa + 0.3, y, z + 0.3), (xa + 2.3, y + 1.2, z + 1.5), col("bois_clair"), studs="top", name="Caisse")
        for i in range(3):  # rouleaux
            b.cyl((xa + 3.6 + i * 1.0, y + 0.4, z + 0.9), 0.4, 1.4, col("panneau"), axis="z", name="Rouleau")
        for i in range(4):  # kunaï plantés dans un présentoir
            xx = xb - 3.2 + i * 0.7
            b.box((xx - 0.1, y, z + 0.6), (xx + 0.1, y + 1.4, z + 0.8), col("metal_fonce"), collide=False, name="Kunai")
        b.box((xb - 3.5, y, z + 0.4), (xb - 0.4, y + 0.4, z + 1.0), col(BOIS_SOMBRE), name="Presentoir")
    elif kind == "fleurs":
        fl = ("sakura", "rouge", "jaune_lampion", "blanc", "sakura_fonce", "orange_lampion")
        n = max(2, int(w / 1.9))
        for i in range(n):
            x = xa + (i + 0.5) * w / n
            b.cyl((x, y + 0.5, z + 0.9), 0.6, 1.0, col(POT_TERRE if i % 2 else POT_BLEU), axis="y", name="Pot")
            b.ball((x, y + 1.5, z + 0.9), 0.75, col(fl[(i + int(rng.integers(0, 3))) % len(fl)]), collide=False, name="Bouquet")
    elif kind == "remedes":
        b.box((xa + 0.3, y, z + 0.4), (xa + 3.0, y + 1.8, z + 1.6), col("bois"), name="Tiroirs")
        for i in range(3):
            for j in range(2):
                b.box((xa + 0.6 + i * 0.8, y + 0.35 + j * 0.8, z + 0.3), (xa + 0.9 + i * 0.8, y + 0.55 + j * 0.8, z + 0.4),
                      col("jaune_lampion"), collide=False, name="Bouton")
        for i in range(3):
            b.cyl((xb - 1.0 - i * 1.3, y + 0.6, z + 0.9), 0.5, 1.2, col(("#E8E1D0", "#B5643A", "#4F79A8")[i]), axis="y",
                  studs="top", name="Bocal")


def boutique(b, variant=0, largeur=24, profondeur=20):
    """Échoppe de 2-3 étages : devanture en bois (étal ouvert + portes à claire-voie), store, noren, lampions,
    enseigne verticale perpendiculaire à la rue, kanban, fenêtres à cadre bois, climatiseur, tuyaux, toit stud."""
    rng = b.rng
    S = _style(_BOUTIQUES, variant)
    v = variant % 4
    W, D = float(largeur), float(profondeur)
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    n_et = S["etages"]
    H0, HE = 9.0, 7.0
    H = H0 + HE * (n_et - 1)
    ret = 1.6
    zr = zf + ret
    mur = S["mur"]
    cadre = col(S["cadre"])
    bois = col("bois_fonce")

    # --- rez-de-chaussée (devanture en retrait sous l'étage) -------------------------------
    with b.group("RezDeChaussee"):
        b.box((x0, 0, zr), (x1, H0, zb), shade(vr(mur, rng, 0.03), 0.92), name="Mur_rdc")
        b.box((x0 + 1, 0, zf - 0.8), (x1 - 1, 0.4, zr + 0.3), col("pave"), studs="top", name="Seuil")
        b.box((x0 - 0.15, 0, zr), (x1 + 0.15, 1.0, zb + 0.15), col("pave_fonce"), studs="top", name="Soubassement")
        for xa in (x0, x1 - 1):
            b.box((xa, 0, zf), (xa + 1, H0 - 1.2, zr), bois, name="Poteau")
        b.box((x0, H0 - 1.2, zf), (x1, H0, zr), bois, name="Linteau")
        xa, xb = x0 + 1, x1 - 1
        frac = 0.56 if W >= 20 else 0.5
        if S["portes"] == "droite":
            xs = xa + (xb - xa) * frac
            e0, e1, p0, p1 = xa, xs - 0.4, xs + 0.4, xb
        else:
            xs = xb - (xb - xa) * frac
            p0, p1, e0, e1 = xa, xs - 0.4, xs + 0.4, xb
        b.box((xs - 0.4, 0.4, zf + 0.3), (xs + 0.4, H0 - 1.2, zr), bois, name="Poteau")
        # étal ouvert : fond sombre, étagère, comptoir stud, marchandises
        with b.at((0, 0, zr)):
            b.box((e0, 0.4, -0.1), (e1, H0 - 1.2, 0.1), col(INTERIEUR), name="Fond")
            b.box((e0 + 0.3, 4.6, -1.0), (e1 - 0.3, 4.9, -0.1), col("bois_clair"), studs="top", name="Etagere")
            for i in range(max(2, int((e1 - e0) / 1.6))):
                xx = e0 + 0.9 + i * 1.5
                if xx > e1 - 0.8:
                    break
                b.box((xx - 0.45, 4.9, -0.85), (xx + 0.45, 5.9 + 0.3 * (i % 2), -0.2),
                      vr(("rouge", "jaune_pale", "toit_bleu_clair", "panneau")[i % 4], rng, 0.05), name="Article")
            b.box((e0 + 0.4, 0.4, -1.9), (e1 - 0.4, 3.0, -0.1), vr("bois", rng, 0.04), material="WoodPlanks", name="Comptoir")
            b.box((e0 + 0.2, 3.0, -2.1), (e1 - 0.2, 3.4, -0.1), col("bois_clair"), studs="top", name="Plateau")
            _etal(b, S["etal"], e0 + 0.4, e1 - 0.4, 3.4, -2.0, rng)
            # portes coulissantes
            _shoji(b, p0, p1, 0.4, H0 - 1.2, S["cadre"])
        # noren devant l'entrée, accroché sous le linteau
        nfond, nencre, ntxt = S["noren"]
        _noren(b, p0 + 0.2, p1 - 0.2, H0 - 1.2, 2.9, zf + 0.7, nfond, nencre, ntxt, n=max(2, int(round((p1 - p0) / 2.2))))

    # --- store / auvent au-dessus de la devanture ------------------------------------------
    with b.group("Store"):
        sy0, sy1, sz0 = H0 - 0.4, H0 + 1.6, zf - 3.0
        cols = S["store"]
        if len(cols) == 2:
            n = max(4, int(round((W + 0.8) / 2.0)))
            sw = (W + 0.8) / n
            for i in range(n):
                cc = col(cols[i % 2])
                xa = x0 - 0.4 + i * sw
                b.wedge((xa, sy0, sz0), (xa + sw, sy1, zf + 0.4), cc, down="-z", studs="top", material="Fabric", name="Store")
                b.box((xa, sy0 - 0.7, sz0), (xa + sw, sy0, sz0 + 0.25), cc, material="Fabric", name="Lambrequin")
        else:
            t = col(cols[0])
            b.box((x0 - 0.4, sy0 - 0.5, sz0), (x1 + 0.4, sy0, zf + 0.4), shade(t, 0.7), name="Rive")
            b.wedge((x0 - 0.4, sy0, sz0), (x1 + 0.4, sy1, zf + 0.4), t, down="-z", studs="top", name="Auvent")
        lc = S["lampions"]
        for xx in (x0 + 1.6, x1 - 1.6):
            _lampion(b, xx, sy0 - (0.7 if len(cols) == 2 else 0.5), sz0 + 0.9, r=0.75, couleur=lc)

    # --- étages ------------------------------------------------------------------------------
    with b.group("Etages"):
        for k in range(n_et - 1):
            ya, yb = H0 + k * HE, H0 + (k + 1) * HE
            b.box((x0, ya, zf), (x1, yb, zb), vr(mur, rng, 0.035), name="Mur")
        # soubassement de l'étage (bande sous le store, plus foncée) et bandeaux entre étages
        for k in range(1, n_et - 1):
            y = H0 + k * HE
            b.box((x0 - 0.35, y - 0.35, zf - 0.35), (x1 + 0.35, y + 0.35, zb + 0.35), cadre, studs="top", name="Bandeau")
        b.box((x0 - 0.35, H - 0.7, zf - 0.35), (x1 + 0.35, H, zb + 0.35), cadre, name="Sabliere")
        # murs « pixel » : façade avant des étages, côtés
        with b.at((0, 0, zf)):
            _motif(b, x0, x1, H0, H - 0.7, mur, rng, 0.10)
        for side in (-1, 1):
            with b.at((x1 if side > 0 else x0, 0, 0), yaw=-90 * side):
                _motif(b, -D / 2 + (ret if side > 0 else 0), D / 2 - (0 if side > 0 else ret), 1.0, H - 0.7,
                       mur, rng, 0.10)
        if S["poteaux"]:
            for xa in (x0 - 0.2, x1 - 0.7):
                b.box((xa, H0, zf - 0.2), (xa + 0.9, H - 0.7, zf + 0.7), cadre, name="Colombage")
                b.box((xa, H0, zb - 0.7), (xa + 0.9, H - 0.7, zb + 0.2), cadre, name="Colombage")

    # --- façade avant des étages -------------------------------------------------------------
    gauche = v in (0, 2)              # côté de l'enseigne verticale
    xv = (x0 + 0.85) if gauche else (x1 - 0.85)
    with b.group("Facade"), b.at((0, 0, zf)):
        auvent_f = None if v in (0, 1) else S["toit"]
        for k in range(n_et - 1):
            yb = H0 + k * HE
            top = k == n_et - 2
            if k == 0:
                # kanban au centre, une fenêtre de chaque côté
                hx = min(W - 13.0, 10.0)
                if hx >= 4:
                    t, f, e = S["h"]
                    _enseigne_h(b, 0, yb + 1.9, hx, 2.3, t, f, e, BOIS_SOMBRE)
                    xs_f = [x0 + 3.6, x1 - 3.6]
                    yw, hw_ = yb + 2.6, 3.2
                else:
                    xs_f = [x0 + 3.6, x1 - 3.6] if W >= 16 else [0.0]
                    yw, hw_ = yb + 2.4, 3.4
                for xx in xs_f:
                    _fenetre(b, xx, yw, 3.2, hw_, cadre, S["vitre"], croix="+" if v != 1 else "v", auvent=auvent_f)
            else:
                n = max(2, int((W - 2) / 6.5))
                bal = S.get("balcon") and top and n >= 3
                for i in range(n):
                    xx = x0 + (i + 0.5) * W / n
                    if abs(xx - xv) < 2.6:
                        xx += 1.2 if gauche else -1.2
                    if bal and i == n // 2:
                        hb = min(3.6, W / n - 1.4)
                        _porte_fenetre(b, xx, yb + 0.4, 2.6, 5.0, cadre, S["vitre"])
                        _balcon(b, xx - hb, xx + hb, yb + 0.5, 2.2, "bois_clair", FER, pas=1.0)
                        _plante(b, xx - hb + 0.9, yb + 0.5, -1.1, r=0.7, pot=POT_BLEU, fleur="sakura")
                        continue
                    _fenetre(b, xx, yb + 2.0, 3.0, 3.4 if not top else 3.0, cadre, S["vitre"], croix="v",
                             auvent=S["toit"] if (v == 3 and top) else None)
        # enseigne verticale (dépasse au-dessus de l'avant-toit pour la silhouette)
        t, f, e, cdr = S["v"]
        hv = 2.0 * len(t)
        yv = H0 + 2.2
        _enseigne_v(b, xv, yv, hv, t, f, e, cdr, sortie=1.8, bras=(yv + 0.3, min(yv + hv - 0.6, H - 1.6)),
                    chapeau=S["toit"])
        # tuyau qui descend du toit sur l'avant et plonge dans le store
        xt = (x1 - 0.7) if gauche else (x0 + 0.7)
        _tuyau(b, [(xt, H - 0.7), (xt, H0 + 1.2)], r=0.28)
        # climatiseur entre deux fenêtres du dernier étage (ou du premier)
        if n_et == 3 and not S.get("balcon"):
            n = max(2, int((W - 2) / 6.5))
            _clim(b, (x0 + W / n) if not gauche else (x1 - W / n), H0 + HE + 0.9)

    # --- façades latérales et arrière ----------------------------------------------------------
    with b.group("Cotes"):
        for side in (-1, 1):
            xs_ = x1 if side > 0 else x0
            with b.at((xs_, 0, 0), yaw=-90 * side):
                # repère local : x = profondeur (vers l'avant pour le côté gauche), façade en z = 0
                for k in range(n_et - 1):
                    yb = H0 + k * HE
                    _fenetre(b, 2.0 * side, yb + 2.2, 2.6, 3.0, cadre, S["vitre"], croix="v", cotes=False)
                if side > 0:
                    zt = -D / 2 + 1.4
                    _tuyau(b, [(zt, H - 0.7), (zt, H0 + 3.0), (zt + 3.0, H0 + 3.0), (zt + 3.0, 0.3)], r=0.32,
                           ancre_bas=False)
        with b.at((0, 0, zb), yaw=180):
            for k in range(n_et - 1):
                _fenetre(b, -W / 4, H0 + k * HE + 2.2, 2.6, 3.0, cadre, S["vitre"], croix="v", cotes=False)
            _porte(b, W / 4, 0, 2.6, 6.0, "bois", "bois_fonce")
            _clim(b, -W / 4, 1.2, "citerne")

    # --- toit --------------------------------------------------------------------------------
    with b.group("Toit"):
        forme = S["forme"]
        if forme == "kirizuma":
            top = _toit_kirizuma(b, x0 - 0.5, x1 + 0.5, zf - 1.4, zb + 1.2, H, min(5.0, D * 0.24), S["toit"])
        elif forme == "pignon":
            top = _toit_pignon(b, x0, x1, zf, zb, H, 0.62, S["toit"], mur, deb=0.6, deb_av=1.5,
                               oculus="fenetre", rng=rng)
        elif forme == "irimoya":
            top = _toit_irimoya(b, x0 - 0.6, x1 + 0.6, zf - 1.6, zb + 1.2, H, S["toit"], mur, jupe=3.2, hj=2.0,
                                hc=1.4, ht=min(4.2, D * 0.2), rng=rng)
        else:  # mansarde + citerne + édicule
            xa, xb, za, zb2, yt = _mansarde(b, x0, x1, zf, zb, H, S["toit"], jupe=2.8, hj=2.8, deb=0.6)
            top = _citerne(b, xa + 3.2, yt, za + 3.6, 2.2, 3.6, "citerne")
            _abri_toit(b, xb - 3.0, yt, zb2 - 3.2, 4.0, 4.0, 4.2, mur, S["toit"])
    if S.get("banc"):
        with b.group("Rue"):
            _banc(b, (x1 - 4.5) if S["portes"] == "gauche" else (x0 + 4.5), zf - 2.2, 4.0)
    return {"emprise": (W, D), "hauteur": round(top, 2)}


# ---------------------------------------------------------------------------
# IMMEUBLE
# ---------------------------------------------------------------------------

def _volume(b, x0, x1, z0, z1, ya, yb, cc, coin=None, R=0.0, e=0.0, name="Mur", **kw):
    """Bloc, éventuellement à angle avant arrondi (coin 'g' : angle x0/z0, 'd' : angle x1/z0).
    `e` = débord sur tout le pourtour (bandeaux, rives). Renvoie le centre de l'arrondi."""
    cc = col(cc)
    x0e, x1e, z0e, z1e = x0 - e, x1 + e, z0 - e, z1 + e
    if not coin:
        b.box((x0e, ya, z0e), (x1e, yb, z1e), cc, name=name, **kw)
        return None
    if coin == "g":
        cx, cz = x0 + R, z0 + R
        b.box((cx, ya, z0e), (x1e, yb, z1e), cc, name=name, **kw)
        b.box((x0e, ya, cz), (cx, yb, z1e), cc, name=name, **kw)
    else:
        cx, cz = x1 - R, z0 + R
        b.box((x0e, ya, z0e), (cx, yb, z1e), cc, name=name, **kw)
        b.box((cx, ya, cz), (x1e, yb, z1e), cc, name=name, **kw)
    b.cyl((cx, (ya + yb) / 2, cz), R + e, yb - ya, cc, axis="y", name=name, **kw)
    return (cx, cz)


def _rangee(b, xa, xb, y, n, w, h, cadre, vitre, **kw):
    """n fenêtres réparties sur [xa, xb] (repère de façade)."""
    out = []
    for i in range(n):
        x = xa + (i + 0.5) * (xb - xa) / n
        _fenetre(b, x, y, w, h, cadre, vitre, **kw)
        out.append(x)
    return out


def _devanture(b, xa, xb, H0, S, rng, *, store=None):
    """Petite boutique de rez-de-chaussée (repère de façade) : vitrine, store, noren, kanban."""
    cadre = col(S["cadre"])
    w = xb - xa
    b.box((xa, 0.8, -0.15), (xb, H0 - 2.2, 0.3), col(INTERIEUR), name="Vitrine")
    b.box((xa - 0.4, H0 - 2.2, -0.5), (xb + 0.4, H0 - 1.6, 0.3), cadre, name="Linteau")
    b.box((xa - 0.6, 0.0, -0.9), (xb + 0.6, 0.8, 0.3), cadre, studs="top", name="Allege")
    for xx in (xa - 0.4, xb):
        b.box((xx, 0.8, -0.5), (xx + 0.4, H0 - 2.2, 0.3), cadre, name="Montant")
    nf, ne, nt = S["noren"]
    _noren(b, xa + 0.3, xb - 0.3, H0 - 2.2, 2.4, -0.7, nf, ne, nt, n=max(2, int(round(w / 2.2))))
    b.box((xa + 0.4, 0.8, -1.2), (xb - 0.4, 2.8, -0.15), col("bois"), material="WoodPlanks", name="Etal")
    for i in range(max(2, int(w / 1.8))):
        xx = xa + 1.0 + i * 1.7
        if xx > xb - 0.9:
            break
        b.box((xx - 0.5, 2.8, -1.0), (xx + 0.5, 3.5 + 0.3 * (i % 2), -0.3),
              vr(("rouge", "jaune_pale", "toit_bleu_clair", "panneau", "feuille_claire")[i % 5], rng, 0.05), name="Article")
    sc = col(store or S["auvent"])
    b.wedge((xa - 0.8, H0 - 1.6, -2.6), (xb + 0.8, H0 - 0.2, 0.3), sc, down="-z", studs="top", name="Store")
    b.box((xa - 0.8, H0 - 2.0, -2.6), (xb + 0.8, H0 - 1.6, 0.3), shade(sc, 0.7), name="Rive")
    t, f, e = S["kanban"]
    if w >= 6:
        _enseigne_h(b, (xa + xb) / 2, H0 - 0.1, min(w - 1, 6.5), 1.6, t, f, e, BOIS_SOMBRE)


def _entree(b, x, H0, S, *, distributeur=None):
    """Entrée d'immeuble : porte double, marquise, marche, lampe ; distributeur optionnel à côté."""
    _porte(b, x, 0.4, 3.2, 5.6, S["cadre"], "bois")
    b.box((x - 2.4, 0, -1.4), (x + 2.4, 0.4, 0.3), col("pave"), studs="top", name="Marche")
    b.wedge((x - 2.6, 6.6, -2.4), (x + 2.6, 7.4, 0.3), col(S["auvent"]), down="-z", studs="top", name="Marquise")
    b.box((x - 2.6, 6.2, -2.4), (x + 2.6, 6.6, 0.3), shade(col(S["auvent"]), 0.7), name="Marquise")
    _lampion(b, x + 2.0, 6.2, -1.6, r=0.5, couleur="jaune_lampion", corde=0.3)
    if distributeur is not None:
        _distributeur(b, distributeur, 0.0, "rouge")


_IMMEUBLES = [
    # 0 : angle arrondi, blanc, rives rouges, balcons à auvents verts, 2 citernes
    dict(mur="enduit", bord="rouge_hokage", auvent="toit_vert", cadre="bois_fonce", vitre="fenetre",
         forme="arrondi", noren=("noren_rouge", "blanc", "米屋"), kanban=("お米", "panneau", "rouge_fonce")),
    # 1 : gradins — socle crème, attique bleu pâle en retrait sur une terrasse, rives bleues
    dict(mur="creme", mur2="bleu_pale", bord="toit_bleu", auvent="toit_bleu", cadre="poutre", vitre="fenetre",
         forme="gradin", noren=("noren_bleu", "blanc", "本"), kanban=("書店", "blanc", "toit_bleu")),
    # 2 : tour de Konoha — jaune pâle, colonne de bow-windows à petits toits de cuivre, jupe verte, citernes
    dict(mur="jaune_pale", bord="toit_vert", auvent="toit_vert", cadre="bois", vitre="fenetre",
         forme="tour", noren=("noren_bleu", "blanc", "茶"), kanban=("茶屋", "panneau", "toit_vert_fonce")),
    # 3 : rotonde — rose pâle, tour ronde d'angle à toit en disques étagés, balcons pleins orange
    dict(mur="rose_pale", bord="toit_orange", auvent="toit_rouge", cadre="bois_fonce", vitre="fenetre",
         forme="rotonde", noren=("noren_rouge", "blanc", "花"), kanban=("花", "blanc", "rouge")),
]


def immeuble(b, variant=0, largeur=26, profondeur=24, etages=5):
    """Immeuble de Konoha (4-6 niveaux) : volumes empilés (angle arrondi, retrait en gradins, colonne de
    bow-windows ou tour ronde), rangées de fenêtres, balcons à garde-corps, tuyaux en façade,
    toit-terrasse à rive colorée avec citernes sur pieds et édicule."""
    rng = b.rng
    S = _style(_IMMEUBLES, variant)
    v = variant % 4
    forme = S["forme"]
    n = int(max(4, min(6, etages)))
    W, D = float(largeur), float(profondeur)
    x0, x1, zf, zb = -W / 2, W / 2, -D / 2, D / 2
    H0 = 7.5 if n <= 5 else 7.0
    HE = 6.0 if n <= 5 else 5.5
    H = H0 + HE * (n - 1)
    mur, bord = S["mur"], col(S["bord"])
    cadre, vitre = col(S["cadre"]), S["vitre"]
    coin, R = None, 0.0
    if forme == "arrondi":
        coin, R = "g", min(5.0, W * 0.2)
    elif forme == "rotonde":
        coin, R = "d", min(5.0, W * 0.2, D * 0.25)
    n_bas = n if forme != "gradin" else n - 2          # niveaux du volume principal
    H_bas = H0 + HE * (n_bas - 1)
    # volume du haut pour « gradin »
    gx0, gx1, gz0 = x0, x1 - min(9.0, W * 0.35), zf + min(5.0, D * 0.25)

    # --- volumes ---------------------------------------------------------------------------
    with b.group("Volumes"):
        _volume(b, x0, x1, zf, zb, 0, 1.0, "pave_fonce", coin, R, e=0.15, studs="top", name="Soubassement")
        _volume(b, x0, x1, zf, zb, 1.0, H0, shade(vr(mur, rng, 0.03), 0.9), coin, R, name="Mur_rdc")
        for k in range(1, n_bas):
            _volume(b, x0, x1, zf, zb, H0 + (k - 1) * HE, H0 + k * HE, vr(mur, rng, 0.035), coin, R)
        for k in range(1, n_bas):
            _volume(b, x0, x1, zf, zb, H0 + (k - 1) * HE - 0.3, H0 + (k - 1) * HE + 0.3,
                    bord if k == 1 else cadre, coin, R, e=0.35, studs="top", name="Bandeau")
        if forme == "gradin":
            m2 = S.get("mur2", mur)
            for k in range(n_bas, n):
                b.box((gx0, H0 + (k - 1) * HE, gz0), (gx1, H0 + k * HE, zb), vr(m2, rng, 0.03), name="Mur")
            b.box((gx0 - 0.35, H0 + (n - 2) * HE - 0.3, gz0 - 0.35), (gx1 + 0.35, H0 + (n - 2) * HE + 0.3, zb + 0.35),
                  cadre, studs="top", name="Bandeau")
        if forme == "rotonde":
            cx, cz = x1 - R, zf + R
            # la tour ronde dépasse d'un niveau
            HT = min(HE, 36.0 - H)
            b.cyl((cx, H + 0.9 + HT / 2, cz), R, HT, vr(mur, rng, 0.03), axis="y", name="Tour")
            b.cyl((cx, H + 0.9 + 0.3, cz), R + 0.35, 0.6, cadre, axis="y", studs="top", name="Bandeau")

    # --- façade avant ------------------------------------------------------------------------
    with b.group("Facade"), b.at((0, 0, zf)):
        # rez-de-chaussée : boutique + entrée
        xa_f = x0 + (R + 0.8 if coin == "g" else 1.2)
        xb_f = x1 - (R + 0.8 if coin == "d" else 1.2)
        mid = (xa_f + xb_f) / 2
        if v in (0, 2):
            _devanture(b, xa_f + 0.6, mid + 2.0, H0, S, rng)
            _entree(b, mid + 5.0, H0, S, distributeur=(xb_f - 1.4) if (xb_f - mid) > 9.5 else None)
        else:
            _entree(b, xa_f + 2.8, H0, S, distributeur=(xa_f + 6.4) if v == 1 else None)
            _devanture(b, xa_f + (8.4 if v == 1 else 5.6), xb_f - 0.6, H0, S, rng)

        # tuyau principal (descend du toit jusqu'au sol en faisant un décrochement)
        xt = (x1 - 0.8) if coin != "d" else (x0 + 0.8)
        dx = -1.6 if coin != "d" else 1.6
        yj = H0 + HE * max(1, n_bas - 3) + 0.9
        _tuyau(b, [(xt, H_bas - 0.4), (xt, yj), (xt + dx, yj), (xt + dx, H0 - 0.1)], r=0.3, couleur="tuyau")

        # étages
        fa, fb = xa_f, xb_f - 1.4 * (coin != "d") + 1.4 * (coin == "d")
        if coin == "d":
            fa, fb = x0 + 2.6, x1 - R - 0.8
        elif coin == "g":
            fa, fb = x0 + R + 0.8, x1 - 2.6
        else:
            fa, fb = x0 + 1.4, x1 - 2.6
        nf = max(2, int((fb - fa) / 5.6))
        bay = None
        if forme == "tour":
            bw = min(8.0, W * 0.3)
            bay = (x0 + 2.0, x0 + 2.0 + bw)
            fa = bay[1] + 1.2
            nf = max(2, int((fb - fa) / 5.6))
        for k in range(1, n_bas):
            yb = H0 + (k - 1) * HE
            top = k == n_bas - 1
            balc = (forme == "arrondi" and k in (2, 4)) or (forme == "rotonde" and k % 2 == 1) \
                or (forme == "gradin" and k == 1) or (forme == "tour" and k >= 2)
            if balc and nf >= 2:
                if forme == "rotonde":
                    bx0, bx1 = fa - 0.6, fa + (fb - fa) * 0.5
                elif forme == "tour":
                    bx0, bx1 = fb - (fb - fa) * 0.55, fb + 0.4
                else:
                    bx0, bx1 = mid - 4.2, mid + 4.2
                _porte_fenetre(b, (bx0 + bx1) / 2, yb + 0.3, 2.6, 4.8, cadre, vitre)
                plein = bord if forme == "rotonde" else False
                _balcon(b, bx0, bx1, yb + 0.6, 2.4, "pave" if forme != "gradin" else "bois_clair",
                        FER if not plein else bord, plein=plein, pas=1.0, h=2.2)
                if forme in ("arrondi", "tour"):
                    b.wedge((bx0 - 0.3, yb + HE - 1.1, -2.9), (bx1 + 0.3, yb + HE - 0.3, 0.3), col(S["auvent"]),
                            down="-z", studs="top", name="Auvent")
                _plante(b, bx0 + 1.0, yb + 0.6, -1.2, r=0.7, pot=POT_TERRE, fleur=("rouge", "sakura", "jaune_lampion")[k % 3])
                # fenêtres restantes hors balcon
                rest = [(fa, bx0 - 0.8), (bx1 + 0.8, fb)]
                for (ra, rb) in rest:
                    m = int((rb - ra) / 5.0)
                    if m >= 1:
                        _rangee(b, ra, rb, yb + 1.8, m, 2.8, 3.0, cadre, vitre, croix="v", cotes=False)
            else:
                _rangee(b, fa, fb, yb + 1.8, nf, 2.8, 3.0 if not top else 2.8, cadre, vitre, croix="v", cotes=False,
                        auvent=(S["auvent"] if (top and forme == "gradin") else None))
            # climatiseur sur un trumeau
            if k == 2 and nf >= 3 and not balc:
                xs_ = fa + (fb - fa) / nf
                _clim(b, xs_, yb + 0.8)
        if bay is not None:
            # colonne de bow-windows : boîte en saillie, une baie et un petit toit de cuivre par niveau
            ba, bb_ = bay
            b.box((ba, H0 - 0.6, -2.4), (bb_, H_bas - 1.2, 0.3), vr(mur, rng, 0.03), name="Bow")
            b.box((ba - 0.3, H0 - 1.2, -2.7), (bb_ + 0.3, H0 - 0.6, 0.3), cadre, name="Console")
            with b.at((0, 0, -2.4)):
                for k in range(1, n_bas):
                    yb = H0 + (k - 1) * HE
                    _fenetre(b, (ba + bb_) / 2, yb + 1.4, bb_ - ba - 2.0, 3.0, cadre, vitre, croix="+", cotes=True)
                    b.wedge((ba - 0.6, yb + HE - 1.5, -1.6), (bb_ + 0.6, yb + HE - 0.4, 2.7), col(S["auvent"]),
                            down="-z", studs="top", name="Toit_bow")
        if coin is not None:
            cx, cz = (x0 + R, zf + R) if coin == "g" else (x1 - R, zf + R)
            yaw = 45 if coin == "g" else -45
            with b.at((cx, 0, cz - zf), yaw=yaw), b.at((0, 0, -R)):
                for k in range(1, n_bas + (1 if forme == "rotonde" else 0)):
                    yb = H0 + (k - 1) * HE + (0.9 if (forme == "rotonde" and k == n_bas) else 0)
                    _fenetre(b, 0, yb + 1.8, 2.2, 3.0, cadre, vitre, croix="v", cotes=True)
                _fenetre(b, 0, 2.4, 2.2, 3.4, cadre, vitre, croix="+", cotes=True)

    # --- côtés et arrière ------------------------------------------------------------------------
    with b.group("Cotes"):
        for side in (-1, 1):
            xs_ = x1 if side > 0 else x0
            with b.at((xs_, 0, 0), yaw=-90 * side):
                # repère local : x = profondeur (signe selon le côté), façade en z = 0
                lo, hi = -D / 2 + 2.0, D / 2 - 2.0
                if (coin == "d" and side > 0) or (coin == "g" and side < 0):
                    if side > 0:
                        lo = -D / 2 + R + 1.0
                    else:
                        hi = D / 2 - R - 1.0
                ns = 2 if (hi - lo) >= 11 else 1
                top_k = n_bas if not (forme == "gradin" and side > 0) else n_bas
                for k in range(1, top_k):
                    _rangee(b, lo, hi, H0 + (k - 1) * HE + 1.8, ns, 2.4, 3.0, cadre, vitre, croix="v", cotes=False)
                if side > 0 and forme != "rotonde":
                    _tuyau(b, [(lo - 1.0, H_bas - 0.4), (lo - 1.0, 0.4)], r=0.3)
        with b.at((0, 0, zb), yaw=180):
            for k in range(1, n_bas):
                _fenetre(b, 0, H0 + (k - 1) * HE + 1.8, 2.4, 3.0, cadre, vitre, croix="v", cotes=False)
            _porte(b, -W / 4, 0, 2.6, 5.6, "bois", "bois_fonce")
            _clim(b, W / 4, 1.4, "citerne")

    # --- toits ------------------------------------------------------------------------------------
    with b.group("Toit"):
        if forme == "arrondi" or forme == "rotonde":
            _volume(b, x0, x1, zf, zb, H, H + 0.9, bord, coin, R, e=0.4, studs="top", name="Rive")
            yt = H + 0.9
            if forme == "rotonde":
                cx, cz = x1 - R, zf + R
                yy = H + 0.9 + min(HE, 36.0 - H)
                for i, (rr, hh) in enumerate(((R + 0.9, 0.8), (R - 0.3, 1.0), (R - 1.6, 1.0), (R - 2.8, 1.0))):
                    b.cyl((cx, yy + hh / 2, cz), rr, hh, shade(col(S["auvent"]), 1.0 - 0.06 * i), axis="y",
                          studs="top", name="Toit_tour")
                    yy += hh
                b.ball((cx, yy + 0.4, cz), 0.6, col("jaune_lampion"), name="Epi")
                top = yy + 1.0
            else:
                top = yt
            # acrotère arrière et latéral (le devant arrondi reste dégagé)
            b.box((x0 - 0.4, yt, zb - 0.2), (x1 + 0.4, yt + 0.9, zb + 0.4), bord, studs="top", name="Acrotere")
            tank_zone = (x0 + (R + 1 if coin == "g" else 2), x1 - (R + 1 if coin == "d" else 2), zf + 3, zb - 2)
        elif forme == "gradin":
            # terrasse du socle + attique
            yt0 = _toit_plat(b, x0, x1, zf, zb, H_bas, bord, acrotere=0)
            _garde_corps(b, [(x0 + 0.2, gz0), (x0 + 0.2, zf + 0.2), (x1 - 0.2, zf + 0.2), (x1 - 0.2, zb - 0.2),
                             (gx1, zb - 0.2)], yt0, FER, pas=1.3)
            yt = _toit_plat(b, gx0, gx1, gz0, zb, H, bord)
            tank_zone = (gx0 + 2, gx1 - 2, gz0 + 2.5, zb - 2)
            top = yt
            # mobilier de terrasse
            _plante(b, x1 - 2.0, yt0, zf + 2.0, r=1.0, pot=POT_TERRE, fleur="sakura", rng=rng)
            _plante(b, x0 + 2.0, yt0, zf + 2.0, r=0.9, pot=POT_BLEU, rng=rng)
            with b.at((0, yt0, 0)):
                _banc(b, (gx1 + x1) / 2, zb - 5.0, 3.6, couleur="noren_rouge")
        else:  # tour : jupe de cuivre + terrasse
            xa, xb, za, zb2, yt = _mansarde(b, x0, x1, zf, zb, H, S["bord"], jupe=3.2, hj=3.2, deb=0.8)
            tank_zone = (xa + 1, xb - 1, za + 1, zb2 - 1)
            top = yt
        # citernes et édicule
        tx0, tx1, tz0, tz1 = tank_zone
        dispo = 41.8 - yt
        hh = max(2.0, min(3.6, dispo - 4.0))
        rr = 2.0 if hh >= 3.0 else 1.6
        nt = 2 if (tx1 - tx0) > 12 else 1
        if v == 3:
            nt = 1
        tops = [top]
        for i in range(nt):
            xc = tx0 + rr + 0.8 + i * (2 * rr + 1.6)
            tops.append(_citerne(b, xc, yt, tz0 + rr + 1.0 + (i % 2) * 1.5, rr, hh, ("citerne", "blanc", "bleu_pale")[(v + i) % 3],
                                 pieds=1.2))
        _abri_toit(b, tx1 - 2.4, yt, tz1 - 2.4, 4.0, 4.0, 3.8, S.get("mur2", mur), S["bord"])
        tops.append(yt + 5.0)
        top = max(tops)

    return {"emprise": (W, D), "hauteur": round(top, 2)}


def ramen(b, variant=0):
    raise NotImplementedError


def maison(b, variant=0, largeur=20, profondeur=18):
    raise NotImplementedError
