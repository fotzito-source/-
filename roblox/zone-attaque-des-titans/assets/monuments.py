"""Monuments de la ville entre les murailles : les grands repères verticaux et les objets singuliers.

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :
- eglise(largeur=52, profondeur=30) ≤ 400 pièces : église-halle de grès blond, nef à contreforts et lancettes à
  vitraux, chevet polygonal, grand toit d'ardoise à lucarnes, clocher-porche carré (portail brisé, rose, étage des
  cloches ouvert) ; flèche de cuivre (v0), flèche d'ardoise à clochetons (v1) ou bulbe (v2) ;
- clocher(hauteur=66) ≤ 95 : campanile roman carré (lésènes, cordons, baies géminées ouvertes, cloche) ; brique et
  pavillon d'ardoise (v0), pierre brune et casque de cuivre à lanternon (v1), casque rhénan (v2), crénelé (v3) ;
- beffroi(largeur=44, profondeur=30) ≤ 340 : hôtel de ville à arcades et pignons à redents, tour d'horloge enduite
  d'ocre (cadrans sur trois faces, galerie à échauguettes, lanternon ouvert, flèche, ≈ 88) au centre (v0) ou à
  gauche (v1) ; v2 : toits de tuiles ;
- fontaine() ≤ 70 : fontaine de marché à colonne (aucune statue) ; octogonale (v0), carrée (v1), à deux vasques (v2) ;
- moulin() ≤ 80 : moulin sur pivot (v0), moulin-tour de pierre (v1), moulin sur pivot à ailes en croix (v2) ;
- depot_ravitaillement(largeur=36, profondeur=20) ≤ 150 : hangar ouvert, caisses, tonneaux, grue, charrette, boulets
  (appentis de tuiles v0, d'ardoise v1) ;
- tour_guet(hauteur=40) ≤ 60 : tour de guet de charpente (toit de tuiles, d'ardoise, socle de pierre selon v) ;
- mat_fete(hauteur=40) ≤ 40 : mât de fête à bandes, couronne de feuillage, rubans et plaques unies.

Les clochers, le clocher-porche de l'église et le beffroi ont des teintes (brique, grès sombre, enduit ocre) qui
tranchent sur la pierre pâle des murailles : vus de la rue, ils rythment la ligne des toits.

Repère (voir CONVENTIONS.md) : Roblox, Y vers le haut, 1 stud ; origine au centre de l'emprise au sol ;
l'AVANT regarde -Z local. Tout reste dans l'emprise annoncée : une fois posés par `zone.py`, rien n'entre dans le
couloir (|x| < 46).

Propriété intellectuelle : ville médiévale générique. Aucune statue ni figure, aucun visage, aucun blason ni
insigne, aucun texte ; drapeaux unis ou à bandes ; cadrans à simples marques d'heure ; l'église n'a qu'une boule
dorée et une girouette à flèche.

Outils géométriques propres au module : `_tri` pose un triangle rectangle quelconque avec un coin Roblox très mince
(sa face latérale), ce qui donne des flèches et des toits en pavillon lisses (`_pyramide`, `_fleche`) en 2 pièces
par pan ; `_arc_octo` découpe un plein cintre en six pièces (coins + bloc) autour d'une baie réellement ouverte.
"""

from __future__ import annotations

import math

import numpy as np

from kit import rot_x, rot_z, shade
from palette import c, vary

from assets import mobilier

FACES = (0, 90, 180, -90)    # lacet des repères de face : avant (-Z), gauche (-X), arrière (+Z), droite (+X)


# ---------------------------------------------------------------------------
# Couleurs
# ---------------------------------------------------------------------------

def col(x):
    """Nom de la palette ou triplet RGB → triplet RGB."""
    return c(x) if isinstance(x, str) else tuple(int(v) for v in x)


def vr(x, rng, amount=0.04):
    """Variation légère de luminosité (nom de palette ou RGB)."""
    if isinstance(x, str):
        return vary(x, rng, amount)
    return shade(x, 1 + float(rng.uniform(-amount, amount)))


# ---------------------------------------------------------------------------
# Outils géométriques
# ---------------------------------------------------------------------------

def _v(p):
    return np.asarray(p, float)


def _poutre(b, a, bb, ep, couleur, ep2=None, ext=0.0, name="Poutre", **kw):
    """Bloc de section ep × ep2 tendu de a à bb (allongé de `ext` à chaque bout) : jambes de force, écharpes,
    montants inclinés, rayons d'ailes de moulin."""
    a, bb = _v(a), _v(bb)
    d = bb - a
    n = float(np.linalg.norm(d))
    x = d / n
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([0.0, 0.0, 1.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return b.part("block", (n + 2 * ext, ep, ep2 if ep2 else ep), (a + bb) / 2, np.column_stack([x, y, z]),
                  col(couleur), name=name, **kw)


def _corde(b, a, bb, r=0.08, couleur="corde", name="Corde"):
    """Corde ou filet d'eau (cylindre fin, sans collision ni ombre) de a à bb."""
    a, bb = _v(a), _v(bb)
    d = bb - a
    n = float(np.linalg.norm(d))
    x = d / n
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return b.part("cyl", (n, 2 * r, 2 * r), (a + bb) / 2, np.column_stack([x, y, z]), col(couleur),
                  collide=False, shadow=False, name=name)


def _barre(b, xa, ya, xb, yb, z0, z1, ep, couleur, name="Arc", **kw):
    """Barre dans un plan de façade (x, y), de (xa, ya) à (xb, yb), largeur `ep` dans le plan, profondeur z0..z1."""
    L = math.hypot(xb - xa, yb - ya)
    ang = math.degrees(math.atan2(yb - ya, xb - xa))
    return b.part("block", (L, ep, z1 - z0), ((xa + xb) / 2, (ya + yb) / 2, (z0 + z1) / 2), rot_z(ang),
                  col(couleur), name=name, **kw)


def _tri(b, M, C, A, ep, couleur, dehors, studs=False, name="Pan", **kw):
    """Fine plaque triangulaire : triangle rectangle en M (MC le long de la base, MA vers le sommet), posée avec un
    coin Roblox d'épaisseur `ep` dont la face latérale est le triangle ; l'épaisseur part à l'opposé de `dehors`."""
    M, C, A = _v(M), _v(C), _v(A)
    h = float(np.linalg.norm(A - M))
    d = float(np.linalg.norm(C - M))
    Y = (A - M) / h
    Z = (M - C) / d
    X = np.cross(Y, Z)
    s = 1.0 if float(np.dot(X, dehors)) > 0 else -1.0
    ctr = M + Y * h / 2 - Z * d / 2 - s * X * ep / 2
    face = "Right" if s > 0 else "Left"
    return b.part("wedge", (ep, h, d), ctr, np.column_stack([X, Y, Z]), col(couleur),
                  studs=(face,) if studs else (), name=name, **kw)


def _facette(b, P, Q, A, ep, couleur, interieur, **kw) -> int:
    """Triangle PQA quelconque (pied de la hauteur issue de A dans [PQ]) en un ou deux triangles rectangles.
    `interieur` : un point à l'intérieur du volume (pour orienter l'épaisseur). Renvoie le nombre de pièces."""
    P, Q, A = _v(P), _v(Q), _v(A)
    L = float(np.linalg.norm(Q - P))
    u = (Q - P) / L
    t = float(np.dot(A - P, u))
    F = P + u * t
    nrm = np.cross(Q - P, A - P)
    if float(np.dot(nrm, P - _v(interieur))) < 0:
        nrm = -nrm
    n = 0
    if t > 0.02:
        _tri(b, F, P, A, ep, couleur, nrm, **kw)
        n += 1
    if t < L - 0.02:
        _tri(b, F, Q, A, ep, couleur, nrm, **kw)
        n += 1
    return n


def _pyramide(b, cx, y0, cz, w, d, H, couleur, ep=0.5, **kw) -> float:
    """Toit en pavillon lisse sur le rectangle w × d (centre cx, cz, base y0), sommet à y0 + H : 8 pièces."""
    k = [(cx - w / 2, y0, cz - d / 2), (cx + w / 2, y0, cz - d / 2), (cx + w / 2, y0, cz + d / 2),
         (cx - w / 2, y0, cz + d / 2)]
    A = (cx, y0 + H, cz)
    for i in range(4):
        _facette(b, k[i], k[(i + 1) % 4], A, ep, couleur, (cx, y0 + H * 0.3, cz), **kw)
    return y0 + H


def _fleche(b, cx, y0, cz, R, H, couleur, n=8, ep=0.45, **kw) -> float:
    """Flèche polygonale lisse (n pans, rayon R aux sommets, côtés face aux axes) : 2n pièces."""
    a0 = math.pi / n
    pts = [(cx + R * math.cos(a0 + 2 * math.pi * i / n), y0, cz + R * math.sin(a0 + 2 * math.pi * i / n))
           for i in range(n)]
    A = (cx, y0 + H, cz)
    for i in range(n):
        _facette(b, pts[i], pts[(i + 1) % n], A, ep, couleur, (cx, y0 + H * 0.3, cz), **kw)
    return y0 + H


def _ogive(b, x, y0, w, h, tip, z0, z1, couleur, name="Baie", **kw):
    """Baie à arc brisé dans un plan de façade : rectangle w × h puis pointe de hauteur `tip` (deux coins)."""
    b.box((x - w / 2, y0, z0), (x + w / 2, y0 + h, z1), col(couleur), name=name, **kw)
    b.wedge((x - w / 2, y0 + h, z0), (x, y0 + h + tip, z1), col(couleur), down="-x", name=name, **kw)
    b.wedge((x, y0 + h, z0), (x + w / 2, y0 + h + tip, z1), col(couleur), down="+x", name=name, **kw)


def _arc_octo(b, x0, x1, y_cle, z0, z1, couleur, name="Arc", **kw):
    """Plein cintre « octogonal » au-dessus d'une baie ouverte [x0, x1] dont la clé est en y_cle : les écoinçons
    sont remplis par deux coins et un bloc de chaque côté (6 pièces)."""
    r = (x1 - x0) / 2
    ys = y_cle - r
    a, k = 0.293 * r, 0.707 * r
    cc = col(couleur)
    for s in (-1, 1):
        if s < 0:
            xa = x0
            b.wedge_under((xa, ys, z0), (xa + a, ys + k, z1), cc, down="+x", name=name, **kw)
            b.wedge_under((xa + a, ys + k, z0), (xa + r, y_cle, z1), cc, down="+x", name=name, **kw)
            b.box((xa, ys + k, z0), (xa + a, y_cle, z1), cc, name=name, **kw)
        else:
            xb = x1
            b.wedge_under((xb - a, ys, z0), (xb, ys + k, z1), cc, down="-x", name=name, **kw)
            b.wedge_under((xb - r, ys + k, z0), (xb - a, y_cle, z1), cc, down="-x", name=name, **kw)
            b.box((xb - a, ys + k, z0), (xb, y_cle, z1), cc, name=name, **kw)
    return ys


def _pierres(b, rng, n, xr, yr, z0, eviter, couleurs, prot=0.12):
    """Quelques pierres isolées en légère saillie sur une façade (plan z0, extérieur -z), hors des rectangles
    `eviter` [(x0, y0, x1, y1)] : casse l'aplat en « pixels » de 3-4 teintes proches."""
    poses: list = []
    essais = 0
    while len(poses) < n and essais < 40 * n:
        essais += 1
        w = float(rng.choice((1.5, 2.0, 2.5, 3.0)))
        h = float(rng.choice((0.8, 1.0, 1.2)))
        if xr[1] - xr[0] < w + 0.2 or yr[1] - yr[0] < h:
            break
        x = float(rng.uniform(xr[0] + w / 2, xr[1] - w / 2))
        y = round(float(rng.uniform(yr[0], yr[1] - h)) * 2) / 2
        r = (x - w / 2, y, x + w / 2, y + h)
        if any(r[0] < e[2] + 0.3 and e[0] < r[2] + 0.3 and r[1] < e[3] + 0.3 and e[1] < r[3] + 0.3
               for e in list(eviter) + poses):
            continue
        poses.append(r)
        b.box((r[0], r[1], z0 - prot), (r[2], r[3], z0), vr(couleurs[int(rng.integers(len(couleurs)))], rng, 0.02),
              collide=False, name="Pierre")
    return len(poses)


def _cloche(b, x, y_haut, z, r=1.4, couleur="cloche"):
    """Cloche de bronze suspendue sous un joug : y_haut = dessus de la couronne (3 pièces)."""
    cc = col(couleur)
    b.cyl((x, y_haut - 0.3, z), 0.38 * r, 0.6, shade(cc, 0.85), axis="y", collide=False, name="Couronne")
    hb = 1.25 * r
    b.cyl((x, y_haut - 0.6 - hb / 2, z), 0.82 * r, hb, cc, axis="y", collide=False, name="Cloche")
    b.cyl((x, y_haut - 0.6 - hb - 0.15 * r, z), 1.05 * r, 0.3 * r, shade(cc, 1.08), axis="y", collide=False,
          name="Cloche")
    return y_haut - 0.6 - hb - 0.3 * r


def _horloge(b, y, r, z0=0.0, marques=12, cadran="cadran", cercle="or"):
    """Cadran d'horloge sur une façade (repère de façade : plan z0, extérieur vers -z), centre (0, y) : cerclage
    doré, cadran clair, marques d'heure (aucun chiffre), aiguilles noires vers 10 h 10, axe."""
    noir = col("noir")
    b.cyl((0, y, z0 - 0.25), r + 0.45, 0.5, col(cercle), axis="z", collide=False, name="Cerclage")
    b.cyl((0, y, z0 - 0.35), r, 0.7, col(cadran), axis="z", collide=False, name="Cadran")
    for k in range(marques):
        a = math.radians(90 - k * 360 / marques)
        longue = (k * 12 // marques) % 3 == 0
        L = 0.95 if longue else 0.55
        rr = r - 0.25 - L / 2
        b.part("block", (L, 0.34 if longue else 0.26, 0.2), (rr * math.cos(a), y + rr * math.sin(a), z0 - 0.8),
               rot_z(math.degrees(a)), noir, collide=False, shadow=False, name="Marque")
    for ang, L, zz, ep in ((150, 0.55 * r, z0 - 0.85, 0.42), (30, 0.82 * r, z0 - 1.0, 0.3)):
        a = math.radians(ang)
        b.part("block", (L, ep, 0.15), (L / 2 * math.cos(a), y + L / 2 * math.sin(a), zz), rot_z(ang), noir,
               collide=False, shadow=False, name="Aiguille")
    b.cyl((0, y, z0 - 0.92), 0.38, 0.45, col("or"), axis="z", collide=False, name="Axe")


def _girouette(b, x, y, z, h=3.6):
    """Boule dorée, tige et girouette à flèche (aucun symbole) : 5 pièces. y = pied de la boule."""
    b.ball((x, y + 0.7, z), 0.75, col("or"), collide=False, name="Boule")
    b.cyl((x, y + 1.4 + h / 2, z), 0.12, h, col("fonte"), axis="y", collide=False, shadow=False, name="Tige")
    yv = y + 1.4 + h * 0.7
    b.box((x - 1.4, yv - 0.09, z - 0.06), (x + 1.2, yv + 0.09, z + 0.06), col("fonte"), collide=False,
          shadow=False, name="Fleche")
    b.wedge((x + 1.2, yv - 0.3, z - 0.06), (x + 1.8, yv + 0.3, z + 0.06), col("or"), down="+x", collide=False,
            shadow=False, name="Fleche")
    b.box((x - 1.6, yv - 0.1, z - 0.05), (x - 1.0, yv + 0.65, z + 0.05), col("or"), collide=False, shadow=False,
          name="Empennage")


def _pan_z(b, x0, x1, za, ya, zb, yb, ep, couleur, studs="top", name="Pan", **kw):
    """Dalle inclinée dans le plan YZ : sa face supérieure passe par (za, ya) et (zb, yb), épaisseur ep dessous."""
    dz, dy = zb - za, yb - ya
    L = math.hypot(dz, dy)
    phi = math.atan2(dy, dz)
    ny, nz = math.cos(phi), -math.sin(phi)
    if ny < 0:
        ny, nz = -ny, -nz
    cz = (za + zb) / 2 - nz * ep / 2
    cy = (ya + yb) / 2 - ny * ep / 2
    return b.part("block", (x1 - x0, ep, L), ((x0 + x1) / 2, cy, cz), rot_x(-math.degrees(phi)), col(couleur),
                  studs=studs, name=name, **kw)


def _lanterne(b, x, y, z, fer="fonte"):
    """Petite lanterne murale (3 pièces) accrochée en (x, y, z) sur un plan de façade, dépasse vers -z."""
    b.box((x - 0.12, y, z - 1.4), (x + 0.12, y + 0.25, z + 0.05), col(fer), collide=False, name="Potence")
    b.box((x - 0.4, y - 1.5, z - 1.55), (x + 0.4, y - 0.4, z - 0.75), col("lampe"), material="Neon", collide=False,
          shadow=False, name="Lanterne")
    b.box((x - 0.55, y - 0.4, z - 1.7), (x + 0.55, y, z - 0.6), col(fer), collide=False, name="Chapeau")


# ---------------------------------------------------------------------------
# Étage des cloches (clochers, église)
# ---------------------------------------------------------------------------

def _etage_cloches(b, a, y0, y1, *, pierre, accent, rng, pile=2.2, ep=0.9, geminees=True, r_cloche=1.4,
                   faces=FACES):
    """Étage des cloches ouvert, dans le repère du centre de la tour (carré de demi-côté a), de y0 à y1 :
    piles d'angle, sur chaque face un appui bas, deux baies géminées (colonnette et chapiteau) à têtes cintrées
    (coussinets en biais), et une cloche pendue à une poutre qui repose sur les chapiteaux latéraux.
    L'entablement au-dessus de y1 est posé par l'appelant. On voit le ciel à travers la tour."""
    p = pile
    for sx in (-1, 1):
        for sz in (-1, 1):
            xa, xb = sorted((sx * a, sx * (a - p)))
            za, zb = sorted((sz * a, sz * (a - p)))
            b.box((xa, y0, za), (xb, y1, zb), vr(pierre, rng, 0.02), name="Pile")
    yg = y0 + 1.1
    for yaw in faces:
        with b.at((0, 0, 0), yaw=yaw):
            z0 = -a
            b.box((-a + p, y0, z0), (a - p, yg, z0 + ep), col(accent), studs="top", name="Appui")
            if geminees:
                wc = 0.7
                b.cyl((0, (yg + y1 - 0.7) / 2, z0 + ep / 2), 0.36, y1 - 0.7 - yg, col(accent), axis="y",
                      name="Colonnette")
                b.box((-wc, y1 - 0.7, z0 - 0.1), (wc, y1, z0 + ep), col(accent), name="Chapiteau")
                baies = ((-a + p, -wc), (wc, a - p))
            else:
                baies = ((-a + p, a - p),)
            for xa, xb in baies:
                s = min(1.6, 0.42 * (xb - xa))
                b.wedge_under((xa, y1 - s, z0), (xa + s, y1, z0 + ep), col(pierre), down="+x", collide=False,
                              name="Arc")
                b.wedge_under((xb - s, y1 - s, z0), (xb, y1, z0 + ep), col(pierre), down="-x", collide=False,
                              name="Arc")
    if r_cloche:
        b.box((-a + 0.3, y1 - 0.7, -0.35), (a - 0.3, y1, 0.35), col("bois"), name="Joug")
        _cloche(b, 0, y1 - 0.7, 0, r=r_cloche)


# ---------------------------------------------------------------------------
# 1) Église
# ---------------------------------------------------------------------------

_EGLISES = (
    dict(mur="gres", tour="gres_fonce", accent="pierre_maison_claire", sombre="pierre_brune", toit="ardoise",
         fleche="cuivre_vert"),
    dict(mur="pierre_maison", tour="pierre_brune", accent="pierre_maison_claire", sombre="soubassement",
         toit="ardoise", fleche="ardoise_fonce"),
    dict(mur="gres", tour="gres_fonce", accent="pierre_maison_claire", sombre="pierre_brune",
         toit="ardoise_fonce", fleche="cuivre_vert"),
)

VITRAUX = (("vitrail_bleu", "vitrail_rouge"), ("vitrail_or", "vitrail_bleu"), ("vitrail_bleu", "vitrail_rouge"))


def _lancette(b, x, y0, w, h, tip, z0, *, pierre, rng, vitrail=True, m=0.5):
    """Grande lancette gothique (repère de façade : plan z0, extérieur vers -z) : encadrement de pierre à pointe,
    baie sombre et, si `vitrail`, mosaïque de 6 verres colorés et losange doré dans la pointe."""
    tip_c = tip * (w / 2 + m) / (w / 2)
    b.box((x - w / 2 - m, y0 - m, z0 - 0.15), (x + w / 2 + m, y0 + h, z0), col(pierre), collide=False,
          name="Encadrement")
    b.wedge((x - w / 2 - m, y0 + h, z0 - 0.15), (x, y0 + h + tip_c, z0), col(pierre), down="-x", collide=False,
            name="Encadrement")
    b.wedge((x, y0 + h, z0 - 0.15), (x + w / 2 + m, y0 + h + tip_c, z0), col(pierre), down="+x", collide=False,
            name="Encadrement")
    _ogive(b, x, y0, w, h, tip, z0 - 0.27, z0 - 0.05, "fenetre", name="Baie", collide=False)
    if not vitrail:
        return
    g = 0.28
    pw = (w - 3 * g) / 2
    ph = (h - 4 * g) / 3
    for j in range(3):
        for i in range(2):
            xa = x - w / 2 + g + i * (pw + g)
            ya = y0 + g + j * (ph + g)
            couleur = VITRAUX[j][(i + j) % 2]
            b.box((xa, ya, z0 - 0.38), (xa + pw, ya + ph, z0 - 0.2), vr(couleur, rng, 0.05), collide=False,
                  shadow=False, name="Vitrail")
    s = min(w / 2, tip) * 0.55
    b.part("block", (s, s, 0.18), (x, y0 + h + tip * 0.38, z0 - 0.29), rot_z(45), col("vitrail_or"),
           collide=False, shadow=False, name="Vitrail")


def _contrefort(b, pierre, larmier, *, l=2.0, p1=3.0, p2=1.8, h1=12.0, h2=19.0, hc=1.6):
    """Contrefort à deux ressauts et larmiers (repère de façade : plan z = 0, extérieur vers -z) : 4 pièces."""
    b.box((-l / 2, 0, -p1), (l / 2, h1, 0.2), col(pierre), name="Contrefort")
    b.wedge((-l / 2, h1, -p1), (l / 2, h1 + hc, 0.2), col(larmier), down="-z", studs="top", name="Larmier")
    b.box((-l / 2 + 0.25, h1, -p2), (l / 2 - 0.25, h2, 0.2), col(pierre), name="Contrefort")
    b.wedge((-l / 2 + 0.25, h2, -p2), (l / 2 - 0.25, h2 + hc * 1.3, 0.2), col(larmier), down="-z", studs="top",
            name="Larmier")


def _portail(b, w, h, tip, *, pierre, sombre, prof=1.2, jamb=1.0, y0=0.0):
    """Portail à arc brisé (repère de façade : plan z = 0, extérieur vers -z) : piédroits et chapiteaux saillants,
    arc en deux barres, tympan, vantaux cloutés de fer. (0, y0) = milieu du seuil."""
    for s in (-1, 1):
        xa, xb = sorted((s * w / 2, s * (w / 2 + jamb)))
        b.box((xa, 0, -prof), (xb, y0 + h, 0), col(pierre), name="Piedroit")
        xc = s * (w / 2 + jamb / 2)
        b.box((xc - jamb / 2 - 0.25, y0 + h, -prof - 0.2), (xc + jamb / 2 + 0.25, y0 + h + 0.5, 0), col(pierre),
              name="Chapiteau")
        _barre(b, xc, y0 + h + 0.3, 0.0, y0 + h + tip + 0.9, -prof, 0.0, jamb, pierre, name="Voussure")
    b.wedge((-w / 2, y0 + h, -0.45), (0, y0 + h + tip, 0), col(sombre), down="-x", collide=False, name="Tympan")
    b.wedge((0, y0 + h, -0.45), (w / 2, y0 + h + tip, 0), col(sombre), down="+x", collide=False, name="Tympan")
    b.box((-w / 2, y0, -0.45), (w / 2, y0 + h, 0), col("porte"), name="Vantaux")
    b.box((-0.15, y0 + 0.05, -0.6), (0.15, y0 + h - 0.05, -0.4), shade(col("porte"), 0.75), collide=False,
          name="Battement")
    for yy in (y0 + h * 0.28, y0 + h * 0.72):
        b.box((-w / 2 + 0.2, yy - 0.15, -0.58), (w / 2 - 0.2, yy + 0.15, -0.4), col("fer"), collide=False,
              name="Penture")


def _rose(b, y, r, *, pierre, rng):
    """Rose (repère de façade : plan z = 0, extérieur vers -z) : couronne de pierre, disque sombre, remplage,
    huit pétales de verre bleu et rouge, cœur doré (15 pièces)."""
    b.cyl((0, y, -0.3), r + 0.6, 0.6, col(pierre), axis="z", collide=False, name="Rosace")
    b.cyl((0, y, -0.35), r, 0.7, col("fenetre"), axis="z", collide=False, name="Rosace")
    for k in range(4):
        b.part("block", (2 * r - 0.2, 0.3, 0.15), (0, y, -0.76), rot_z(k * 45 + 22.5), col(pierre),
               collide=False, shadow=False, name="Remplage")
    for k in range(8):
        a = math.radians(k * 45)
        rr = r * 0.58
        coul = ("vitrail_bleu", "vitrail_rouge")[k % 2]
        b.part("block", (r * 0.62, r * 0.32, 0.15), (rr * math.cos(a), y + rr * math.sin(a), -0.86),
               rot_z(k * 45), vr(coul, rng, 0.04), collide=False, shadow=False, name="Vitrail")
    b.cyl((0, y, -0.85), r * 0.22, 0.4, col("vitrail_or"), axis="z", collide=False, shadow=False, name="Vitrail")


def _lucarne_toit(b, x, zf, y0, w, h, toit, joue, *, prof=3.0):
    """Lucarne à pignon sur un pan de toit qui monte vers +z : front en zf, cadre blanc, vitre sombre (5 pièces)."""
    b.box((x - w / 2, y0, zf), (x + w / 2, y0 + h, zf + prof), col(joue), name="Lucarne")
    b.box((x - w / 2 + 0.25, y0 + 0.3, zf - 0.12), (x + w / 2 - 0.25, y0 + h - 0.15, zf + 0.1), col("fenetre_cadre"),
          collide=False, name="Cadre")
    b.box((x - w / 2 + 0.55, y0 + 0.6, zf - 0.22), (x + w / 2 - 0.55, y0 + h - 0.45, zf + 0.1), col("fenetre"),
          collide=False, name="Vitre")
    b.wedge((x - w / 2 - 0.3, y0 + h, zf - 0.3), (x, y0 + h + w * 0.55, zf + prof), col(toit), down="-x",
            studs="top", name="Toit")
    b.wedge((x, y0 + h, zf - 0.3), (x + w / 2 + 0.3, y0 + h + w * 0.55, zf + prof), col(toit), down="+x",
            studs="top", name="Toit")


def eglise(b, variant=0, largeur=52, profondeur=30):
    """Église-halle de grès blond sur la place (avant = -Z, côté rue) ; clocher-porche à l'extrémité +X, chevet à -X.

    Nef de 22 de haut à quatre travées : contreforts à ressauts, grandes lancettes à vitraux, portail latéral sous
    un auvent de pierre ; toit d'ardoise très pentu (faîte vers 38) à lucarnes et pignons à rampant de pierre ;
    chevet à trois pans et toit en demi-pavillon. Clocher-porche de 12 × 12 : contreforts d'angle en biais,
    portail brisé à tympan, rose, lancettes, étage des cloches ouvert à baies géminées et cloche, corniche et
    galerie ; v0 flèche octogonale de cuivre vert-de-gris à lucarnes, v1 flèche d'ardoise et quatre clochetons,
    v2 bulbe de cuivre et lanternon. Boule dorée et girouette à flèche au sommet (≈ 76-77)."""
    rng = b.rng
    v = variant % 3
    S = _EGLISES[v]
    L2, P2 = largeur / 2, profondeur / 2
    mur, tour, acc, sombre, toit = S["mur"], S["tour"], S["accent"], S["sombre"], S["toit"]
    XT = L2 - 12.0                 # face est du clocher (= pignon ouest de la nef)
    TX = L2 - 6.0                  # axe du clocher
    XA = -L2 + 11.0                # pignon est de la nef (chevet au-delà)
    ZN = min(11.0, P2 - 4.0)       # demi-largeur de la nef (murs)
    ZR = ZN + 1.0                  # bord de l'avant-toit
    YW, YR = 25.0, 25.0 + ZR * 4 / 3   # haut des murs, faîtage
    contreforts = [XA + (XT - XA) * k / 4 for k in range(5)]
    baies = [(contreforts[k] + contreforts[k + 1]) / 2 for k in range(4)]
    PORTAIL = 2                    # travée du portail latéral

    # --- nef --------------------------------------------------------------------------------------------------
    with b.group("Nef"):
        b.box((XA, 0, -ZN), (XT, YW, ZN), vr(mur, rng, 0.02), name="Murs")
        b.box((XA - 0.3, 0, -ZN - 0.3), (XT + 0.3, 1.6, ZN + 0.3), col("soubassement"), studs="top", name="Socle")
        b.box((XA - 0.6, YW - 1.0, -ZN - 0.6), (XT + 0.6, YW + 0.15, ZN + 0.6), col(acc), name="Corniche")
        b.box((XA - 0.15, 5.0, -ZN - 0.25), (XT, 5.6, -ZN), col(acc), collide=False, name="Cordon")
        # façade sur la rue (-Z) : lancettes, portail latéral, contreforts, pierres
        eviter = []
        for k, xw in enumerate(baies):
            with b.at((xw, 0, -ZN)):
                if k == PORTAIL:
                    _lancette(b, 0, 11.6, 2.6, 7.4, 2.6, 0, pierre=acc, rng=rng)
                    _portail(b, 3.0, 5.2, 2.4, pierre=acc, sombre=sombre, prof=0.9, jamb=0.9, y0=0.5)
                    b.box((-3.4, 0, -2.0), (3.4, 0.5, 0), col(sombre), studs="top", name="Perron")
                    eviter.append((xw - 3.5, 0, xw + 3.5, YW))
                else:
                    _lancette(b, 0, 6.5, 2.6, 12.0, 2.8, 0, pierre=acc, rng=rng)
                    eviter.append((xw - 2.0, 5.5, xw + 2.0, YW))
        for xb in contreforts:
            eviter.append((xb - 1.2, 0, xb + 1.2, YW))
            with b.at((xb, 0, -ZN)):
                _contrefort(b, mur, sombre, h1=14.0, h2=22.0)
            with b.at((xb, 0, ZN), yaw=180):
                _contrefort(b, mur, sombre, h1=14.0, h2=22.0)
        _pierres(b, rng, 9, (XA, XT), (1.8, YW - 1.2), -ZN, eviter, (mur, sombre, acc, "pierre_maison"))
        # façade arrière (+Z, vers le rempart) : lancettes simples
        with b.at((0, 0, ZN), yaw=180):
            for xw in baies:
                _ogive(b, -xw, 6.5, 2.6, 12.0, 2.8, -0.15, 0, acc, name="Encadrement", collide=False)
                _ogive(b, -xw, 7.0, 1.8, 11.3, 2.2, -0.3, -0.05, "fenetre", collide=False)

    # --- toit de la nef ----------------------------------------------------------------------------------------
    with b.group("Toit"):
        b.wedge((XA, YW, -ZR), (XT, YR, 0), vr(toit, rng, 0.02), down="-z", studs="top", name="Toit")
        b.wedge((XA, YW, 0), (XT, YR, ZR), vr(toit, rng, 0.02), down="+z", studs="top", name="Toit")
        b.box((XA, YR - 0.4, -0.5), (XT, YR + 0.6, 0.5), col("ardoise_fonce"), name="Faitage")
        for xa, xb in ((XA - 1.2, XA), (XT, XT + 1.2)):
            b.wedge((xa, YW, -ZR - 0.4), (xb, YR + 0.8, 0), col(acc), down="-z", studs="top", name="Pignon")
            b.wedge((xa, YW, 0), (xb, YR + 0.8, ZR + 0.4), col(acc), down="+z", studs="top", name="Pignon")
        pente = (YR - YW) / ZR
        for xd, yd, wd in ((contreforts[1], 29.0, 3.2), (contreforts[2], 29.0, 3.2), (contreforts[3], 29.0, 3.2),
                           (baies[1], 35.2, 2.4), (baies[2], 35.2, 2.4)):
            zf = -ZR + (yd - YW) / pente
            _lucarne_toit(b, xd, zf, yd - 0.6, wd, 2.8 if wd > 2.8 else 2.2, "ardoise_fonce", toit, prof=2.4)
        # deux bandes d'ardoise claire sur le pan côté rue (saillie 0,12)
        for ya, yb_ in ((26.2, 27.9), (32.6, 34.0)):
            za, zb_ = -ZR + (ya - YW) / pente, -ZR + (yb_ - YW) / pente
            _pan_z(b, XA + 0.2, XT - 0.2, za - 0.09, ya + 0.12, zb_ - 0.09, yb_ + 0.12, 0.3, "ardoise_claire",
                   collide=False, name="Bande")

    # --- chevet ------------------------------------------------------------------------------------------------
    with b.group("Chevet"):
        YA = 19.0
        b.box((XA - 4.0, 0, -7.0), (XA + 0.5, YA, 7.0), vr(mur, rng, 0.02), name="Chevet")
        b.box((XA - 8.0, 0, -3.0), (XA - 3.9, YA, 3.0), vr(mur, rng, 0.02), name="Chevet")
        t = 2.83
        for s in (-1, 1):
            ctr = (XA - 5.0, YA / 2, s * 4.0)
            b.boxc(ctr, (5.9, YA, t), vr(mur, rng, 0.02), yaw=-45 * s, name="Chevet")
        b.box((XA - 8.3, 0, -3.3), (XA - 3.9, 1.6, 3.3), col("soubassement"), studs="top", name="Socle")
        # lancettes des trois pans
        for (px, pz, yaw) in ((XA - 8.0, 0.0, 90), (XA - 6.0, 5.0, 135), (XA - 6.0, -5.0, 45)):
            with b.at((px, 0, pz), yaw=yaw):
                _ogive(b, 0, 5.5, 2.4, 7.5, 2.2, -0.15, 0, acc, name="Encadrement", collide=False)
                _ogive(b, 0, 6.0, 1.6, 6.8, 1.8, -0.3, -0.05, "fenetre", collide=False)
                b.box((-0.8, 6.0, -0.4), (0.8, 9.2, -0.28), col("vitrail_bleu"), collide=False, shadow=False,
                      name="Vitrail")
        # contreforts d'angle du chevet
        for (px, pz, yaw) in ((XA - 8.0, 3.0, 112.5), (XA - 8.0, -3.0, 67.5), (XA - 4.0, 7.0, 157.5),
                              (XA - 4.0, -7.0, 22.5)):
            with b.at((px, 0, pz), yaw=yaw):
                b.box((-0.8, 0, -2.2), (0.8, 12.5, 0.3), col(mur), name="Contrefort")
                b.wedge((-0.8, 12.5, -2.2), (0.8, 15.0, 0.3), col(sombre), down="-z", studs="top", name="Larmier")
        # toit en demi-pavillon (sommet contre le pignon est de la nef)
        o = 0.6
        poly = [(XA, -7.0 - o), (XA - 4.2, -7.0 - o), (XA - 8.0 - o, -3.2), (XA - 8.0 - o, 3.2),
                (XA - 4.2, 7.0 + o), (XA, 7.0 + o)]
        A = (XA, YA + 11.5, 0.0)
        inter = (XA - 3.0, YA + 2.0, 0.0)
        for (pa, pb) in zip(poly, poly[1:]):
            _facette(b, (pa[0], YA, pa[1]), (pb[0], YA, pb[1]), A, 0.5, vr(toit, rng, 0.02), inter, studs=True,
                     name="Toit")
        b.box((XA - 8.0 - o, YA - 0.8, -3.2), (XA - 7.6, YA + 0.15, 3.2), col(acc), collide=False, name="Corniche")

    # --- clocher-porche ----------------------------------------------------------------------------------------
    YB0, YB1, YE, YC = 47.0, 55.5, 57.5, 58.5
    with b.group("Clocher"):
        b.box((XT - 0.5, 0, -6.5), (L2 + 0.5, 1.0, 6.5), col("soubassement"), studs="top", name="Socle")
        b.box((XT, 0, -6.0), (L2, YB0, 6.0), vr(tour, rng, 0.02), name="Tour")
        for y in (26.0, 37.0, YB0 + 0.1):
            b.box((XT - 0.4, y - 0.7, -6.4), (L2 + 0.4, y, 6.4), col(acc), name="Cordon")
        # contreforts d'angle en biais (angles ouest)
        for s in (-1, 1):
            with b.at((L2, 0, s * 6.0), yaw=-135 if s > 0 else -45):
                b.box((-0.8, 0, -2.0), (0.8, 22.0, 0.6), col(tour), name="Contrefort")
                b.wedge((-0.8, 22.0, -2.0), (0.8, 23.6, 0.6), col(sombre), down="-z", studs="top", name="Larmier")
                b.box((-0.6, 22.0, -1.3), (0.6, 37.0, 0.6), col(tour), name="Contrefort")
                b.wedge((-0.6, 37.0, -1.3), (0.6, 38.8, 0.6), col(sombre), down="-z", studs="top", name="Larmier")
        # façade ouest : perron, portail, rose, lancettes géminées
        with b.at((L2, 0, 0), yaw=-90):
            b.box((-3.6, 0, -1.9), (3.6, 0.5, 0.5), col(sombre), studs="top", name="Perron")
            b.box((-3.1, 0.5, -1.1), (3.1, 1.1, 0.5), col(sombre), studs="top", name="Perron")
            _portail(b, 4.4, 6.4, 3.0, pierre=acc, sombre=sombre, prof=1.3, jamb=1.1, y0=1.0)
            _rose(b, 18.0, 3.0, pierre=acc, rng=rng)
        # lancettes : géminées sous l'étage des cloches (3 faces), simples plus bas
        for (fx, fz, yaw, bas) in ((L2, 0, -90, False), (TX, -6.0, 0, True), (TX, 6.0, 180, True)):
            with b.at((fx, 0, fz), yaw=yaw):
                for xw in (-1.7, 1.7):
                    _ogive(b, xw, 39.0, 2.0, 5.0, 1.6, -0.12, 0, acc, name="Encadrement", collide=False)
                    _ogive(b, xw, 39.5, 1.2, 4.4, 1.2, -0.25, -0.05, "fenetre", collide=False)
                _ogive(b, 0, 29.0, 1.2, 4.2, 1.0, -0.2, 0, "fenetre", collide=False)
                if bas:
                    _ogive(b, 0, 12.0, 1.2, 4.2, 1.0, -0.2, 0, "fenetre", collide=False)
        # étage des cloches, entablement, corniche
        with b.at((TX, 0, 0)):
            _etage_cloches(b, 6.0, YB0, YB1, pierre=tour, accent=acc, rng=rng, pile=2.2, r_cloche=1.5)
            b.box((-6.0, YB1, -6.0), (6.0, YE, 6.0), vr(tour, rng, 0.02), name="Entablement")
            b.box((-6.6, YE, -6.6), (6.6, YC, 6.6), col(acc), studs="top", name="Corniche")
            # couronnement
            if v == 0:
                for yaw in FACES:
                    with b.at((0, 0, 0), yaw=yaw):
                        b.box((-6.6, YC, -6.6), (6.1, YC + 1.0, -6.1), col(acc), studs="top", name="Parapet")
                yt = _fleche(b, 0, YC, 0, 5.0, 18.0, S["fleche"], ep=0.45, name="Fleche")
                for yaw in FACES:
                    with b.at((0, 0, 0), yaw=yaw):
                        zf = -4.62 + 1.2
                        b.box((-1.1, YC + 2.0, zf), (1.1, YC + 5.0, zf + 2.2), col("cuivre_vert_fonce"),
                              name="Lucarne")
                        b.box((-0.6, YC + 2.5, zf - 0.12), (0.6, YC + 4.6, zf + 0.2), col("noir"), collide=False,
                              name="Vitre")
                        b.wedge((-1.4, YC + 5.0, zf - 0.3), (0, YC + 6.5, zf + 2.2), col(S["fleche"]), down="-x",
                                name="Lucarne")
                        b.wedge((0, YC + 5.0, zf - 0.3), (1.4, YC + 6.5, zf + 2.2), col(S["fleche"]), down="+x",
                                name="Lucarne")
                _girouette(b, 0, yt - 0.3, 0)
                h_tot = yt - 0.3 + 1.4 + 3.6 + 0.2
            elif v == 1:
                yt = _pyramide(b, 0, YC, 0, 10.6, 10.6, 17.5, S["fleche"], ep=0.5, studs=True, name="Fleche")
                for sx in (-1, 1):
                    for sz in (-1, 1):
                        x, z = sx * 5.6, sz * 5.6
                        b.box((x - 0.8, YC, z - 0.8), (x + 0.8, YC + 3.2, z + 0.8), col(acc), name="Clocheton")
                        b.box((x - 0.55, YC + 3.2, z - 0.55), (x + 0.55, YC + 4.4, z + 0.55), col(S["fleche"]),
                              studs="top", name="Clocheton")
                        b.box((x - 0.3, YC + 4.4, z - 0.3), (x + 0.3, YC + 5.6, z + 0.3), col(S["fleche"]),
                              name="Clocheton")
                        b.ball((x, YC + 5.9, z), 0.4, col("or"), collide=False, name="Boule")
                _girouette(b, 0, yt - 0.3, 0)
                h_tot = yt - 0.3 + 1.4 + 3.6 + 0.2
            else:
                cv, cvf = col("cuivre_vert"), col("cuivre_vert_fonce")
                b.box((-5.6, YC, -5.6), (5.6, YC + 1.4, 5.6), cvf, studs="top", name="Base")
                b.ball((0, YC + 4.6, 0), 5.0, cv, name="Bulbe")
                b.cyl((0, YC + 10.2, 0), 1.4, 1.6, cvf, axis="y", name="Col")
                b.cyl((0, YC + 12.6, 0), 1.9, 3.2, col(acc), axis="y", name="Lanternon")
                b.box((-2.0, YC + 11.6, -0.4), (2.0, YC + 13.6, 0.4), col("noir"), collide=False, name="Baie")
                b.box((-0.4, YC + 11.6, -2.0), (0.4, YC + 13.6, 2.0), col("noir"), collide=False, name="Baie")
                b.cyl((0, YC + 14.4, 0), 2.2, 0.4, cvf, axis="y", name="Corniche")
                b.ball((0, YC + 16.1, 0), 1.7, cv, name="Bulbe")
                b.cyl((0, YC + 18.6, 0), 0.25, 2.4, cvf, axis="y", collide=False, name="Pointe")
                _girouette(b, 0, YC + 19.6, 0)
                h_tot = YC + 19.6 + 1.4 + 3.6 + 0.2
    return {"emprise": (largeur, profondeur), "hauteur": round(h_tot, 1)}


# ---------------------------------------------------------------------------
# 2) Clocher (campanile roman)
# ---------------------------------------------------------------------------

_CLOCHERS = (
    dict(pierre="brique", accent="pierre_maison_claire", toit="ardoise", f_toit=0.30),
    dict(pierre="pierre_brune", accent="pierre_maison_claire", toit="cuivre_vert", f_toit=0.27),
    dict(pierre="gres_fonce", accent="pierre_maison_claire", toit="tuile_brune", f_toit=0.26),
    dict(pierre="pierre_maison", accent="pierre_maison_claire", toit="ardoise", f_toit=0.12),
)


def clocher(b, variant=0, hauteur=66):
    """Campanile roman carré de 12 × 12 (socle 14 × 14) : lésènes d'angle, trois cordons, fentes, porte cintrée,
    étage des cloches ouvert à baies géminées (on voit la cloche et le ciel au travers), entablement et corniche.
    v0 : brique, pavillon d'ardoise lisse et épi doré ; v1 : pierre brune, casque de cuivre en dôme, lanternon et
    bulbe ; v2 : grès sombre, casque rhénan (quatre pignons et toit en losanges, tuiles brunes) ; v3 : pierre claire,
    couronnement crénelé et drapeau. Les teintes tranchent sur la pierre pâle des murailles."""
    rng = b.rng
    v = variant % 4
    S = _CLOCHERS[v]
    H = float(hauteur)
    a = 6.0
    pierre, acc = S["pierre"], S["accent"]
    y_corn = H - S["f_toit"] * H           # dessus de la corniche
    y_ent0 = y_corn - 3.2                  # dessus des baies = dessous de l'entablement
    y_bf = y_ent0 - 9.0                    # plancher des cloches
    h_tot = H
    with b.group("Clocher"):
        b.box((-7.0, 0, -7.0), (7.0, 2.4, 7.0), col("soubassement"), studs="top", name="Socle")
        b.box((-5.5, 0, -5.5), (5.5, y_bf, 5.5), vr(pierre, rng, 0.02), name="Fut")
        for sx in (-1, 1):
            for sz in (-1, 1):
                xa, xb = sorted((sx * 6.0, sx * 4.4))
                za, zb = sorted((sz * 6.0, sz * 4.4))
                b.box((xa, 2.4, za), (xb, y_bf, zb), vr(acc, rng, 0.02), name="Lesene")
        hs = y_bf - 2.4
        for y in (2.4 + hs * 0.36, 2.4 + hs * 0.70, y_bf + 0.1):
            b.box((-6.3, y - 0.7, -6.3), (6.3, y, 6.3), col(acc), name="Cordon")
        # porte cintrée sur l'avant, fentes sur les quatre faces
        with b.at((0, 0, -5.5)):
            b.box((-2.0, 0, -0.65), (2.0, 5.8, 0), col(acc), name="Encadrement")
            b.box((-1.3, 0, -0.8), (1.3, 4.2, -0.5), col("bois_moyen"), name="Porte")
            b.cyl((0, 4.2, -0.7), 1.3, 0.3, col("bois_moyen"), axis="z", collide=False, name="Porte")
            for yy in (1.2, 3.2):
                b.box((-1.15, yy, -0.92), (1.15, yy + 0.3, -0.75), col("fer"), collide=False, name="Penture")
        y1, y2 = 2.4 + hs * 0.52, 2.4 + hs * 0.86
        bif = {0: FACES, 1: FACES, 2: (), 3: (0, 180)}[v]       # baies géminées selon le budget
        for i, yaw in enumerate(FACES):
            with b.at((0, 0, 0), yaw=yaw):
                fentes = [(-1.8 if i % 2 else 1.8, y1)] if i else []
                if yaw in bif:
                    yb_ = 2.4 + hs * 0.70 + 1.2
                    b.box((-2.4, yb_ - 0.6, -5.7), (2.4, yb_ + 5.4, -5.5), col(acc), collide=False, name="Biforium")
                    for xx in (-1.15, 1.15):
                        b.box((xx - 0.7, yb_, -5.85), (xx + 0.7, yb_ + 4.0, -5.6), col("fenetre"), collide=False,
                              name="Baie")
                        b.cyl((xx, yb_ + 4.0, -5.72), 0.7, 0.26, col("fenetre"), axis="z", collide=False, name="Baie")
                    b.box((-0.32, yb_ - 0.6, -6.0), (0.32, yb_ + 4.6, -5.6), col(acc), collide=False,
                          name="Colonnette")
                else:
                    fentes.append((0.0, y2))
                for (xx, yy) in fentes:
                    b.box((xx - 0.4, yy, -5.65), (xx + 0.4, yy + 2.8, -5.5), col("fenetre"), collide=False,
                          name="Fente")
        # quelques pierres en saillie (face avant et faces latérales)
        for yaw in (0, 90, -90):
            with b.at((0, 0, 0), yaw=yaw):
                _pierres(b, rng, 0 if v == 3 else 2, (-4.3, 4.3), (3.0, 2.4 + hs * 0.70 - 1.0), -5.5,
                         [(-1.8, 0, 1.8, 6.0), (-2.3, y1 - 0.5, 2.3, y1 + 3.3), (-0.8, y2 - 0.5, 0.8, y2 + 3.3),
                          (-6, 2.4 + hs * 0.36 - 1.0, 6, 2.4 + hs * 0.36 + 0.3),
                          (-6, 2.4 + hs * 0.70 - 1.0, 6, 2.4 + hs * 0.70 + 0.3)],
                         (pierre, acc, "soubassement"), prot=0.12)
        # étage des cloches
        _etage_cloches(b, a, y_bf, y_ent0, pierre=pierre, accent=acc, rng=rng, pile=2.1, r_cloche=1.35)
        b.box((-a, y_ent0, -a), (a, y_corn - 0.8, a), vr(pierre, rng, 0.02), name="Entablement")
        if v != 2:
            b.box((-a - 0.6, y_corn - 0.8, -a - 0.6), (a + 0.6, y_corn, a + 0.6), col(acc), studs="top",
                  name="Corniche")
        # toits
        if v == 0:
            yt = _pyramide(b, 0, y_corn, 0, 12.4, 12.4, H - y_corn - 2.2, S["toit"], ep=0.5, studs=True, name="Toit")
            b.cyl((0, yt + 0.5, 0), 0.18, 1.6, col("fonte"), axis="y", collide=False, name="Epi")
            b.ball((0, yt + 1.4, 0), 0.6, col("or"), collide=False, name="Epi")
            h_tot = yt + 2.0
        elif v == 1:
            cv, cvf = col("cuivre_vert"), col("cuivre_vert_fonce")
            hr = H - y_corn
            k = hr / 16.2
            b.box((-5.6, y_corn, -5.6), (5.6, y_corn + 1.0 * k, 5.6), cvf, studs="top", name="Base")
            b.ball((0, y_corn + 1.0 * k, 0), 5.3, cv, name="Dome")
            yl = y_corn + 1.0 * k + 5.0
            b.cyl((0, yl + 0.6, 0), 1.2, 1.2, cvf, axis="y", name="Col")
            b.cyl((0, yl + 2.6, 0), 1.6, 2.8, col(acc), axis="y", name="Lanternon")
            b.box((-1.7, yl + 1.7, -0.35), (1.7, yl + 3.4, 0.35), col("noir"), collide=False, name="Baie")
            b.box((-0.35, yl + 1.7, -1.7), (0.35, yl + 3.4, 1.7), col("noir"), collide=False, name="Baie")
            b.cyl((0, yl + 4.2, 0), 1.9, 0.4, cvf, axis="y", name="Corniche")
            b.ball((0, yl + 5.6, 0), 1.4, cv, name="Bulbe")
            b.cyl((0, yl + 7.6, 0), 0.18, 2.2, cvf, axis="y", collide=False, name="Pointe")
            b.ball((0, yl + 8.9, 0), 0.45, col("or"), collide=False, name="Boule")
            h_tot = yl + 9.35
        elif v == 2:
            # casque rhénan : 4 pignons (h) et 4 losanges jusqu'au sommet (2h)
            hg = (H - y_corn - 1.6) / 2
            y0 = y_corn - 0.8
            b.box((-a - 0.4, y0 - 0.6, -a - 0.4), (a + 0.4, y0, a + 0.4), col(acc), name="Cordon")
            cen = (0, y0 + hg * 0.5, 0)
            for yaw in FACES:
                with b.at((0, 0, 0), yaw=yaw):
                    _facette(b, (-a, y0, -a), (a, y0, -a), (0, y0 + hg, -a), 0.6, vr(pierre, rng, 0.02), cen,
                             name="Pignon")
                    b.box((-0.6, y0 + 0.8, -a - 0.12), (0.6, y0 + 2.8, -a + 0.2), col("fenetre"), collide=False,
                          name="Fente")
                    K, G1, G2, A = (-a, y0, -a), (0, y0 + hg, -a), (-a, y0 + hg, 0), (0, y0 + 2 * hg, 0)
                    _facette(b, K, G1, G2, 0.5, vr(S["toit"], rng, 0.03), cen, studs=True, name="Toit")
                    _facette(b, G1, A, G2, 0.5, vr(S["toit"], rng, 0.03), cen, studs=True, name="Toit")
            yt = y0 + 2 * hg
            b.cyl((0, yt + 0.5, 0), 0.18, 1.4, col("fonte"), axis="y", collide=False, name="Epi")
            b.ball((0, yt + 1.3, 0), 0.55, col("or"), collide=False, name="Epi")
            h_tot = yt + 1.85
        else:
            # couronnement crénelé : mâchicoulis, parapet, merlons, terrasse, drapeau
            yp = y_corn
            b.box((-a + 0.2, y_corn - 0.8, -a + 0.2), (a - 0.2, yp + 0.4, a - 0.2), col("pierre_brune"),
                  studs="top", name="Terrasse")
            for yaw in FACES:
                with b.at((0, 0, 0), yaw=yaw):
                    b.box((-a - 0.6, yp, -a - 0.6), (a + 0.0, yp + 1.6, -a + 0.4), col(pierre), name="Parapet")
                    for xm in (-4.6, 0.0, 4.6):
                        b.box((xm - 1.0, yp + 1.6, -a - 0.6), (xm + 1.0, yp + 3.0, -a + 0.4), vr(pierre, rng, 0.03),
                              studs="top", name="Merlon")
                    b.wedge_under((-a - 0.6, yp - 2.0, -a - 0.6), (a + 0.6, y_corn - 0.8, -a), col(acc), down="-z",
                                  name="Machicoulis")
            hf = max(5.0, H - yp - 1.0)
            b.cyl((0, yp + 0.4 + hf / 2, 0), 0.2, hf, col("bois"), axis="y", name="Hampe")
            b.ball((0, yp + 0.4 + hf + 0.25, 0), 0.35, col("or"), collide=False, name="Pommeau")
            for k_, coul in enumerate(("drapeau_rouge", "drapeau_blanc")):
                yy = yp + 0.4 + hf - 0.4 - (k_ + 1) * 1.2
                b.box((0.2, yy, -0.08), (4.2, yy + 1.2, 0.08), col(coul), collide=False, shadow=False, name="Drapeau")
            h_tot = yp + 0.4 + hf + 0.6
    return {"emprise": (14.0, 14.0), "hauteur": round(h_tot, 1)}


# ---------------------------------------------------------------------------
# 3) Beffroi : hôtel de ville et tour d'horloge de la grand-place
# ---------------------------------------------------------------------------

_BEFFROIS = (
    dict(hall="enduit_saumon", pierre="gres", tour="enduit_ocre", acc="pierre_maison_claire", toit="ardoise",
         fleche="ardoise"),
    dict(hall="pierre_maison_claire", pierre="gres", tour="pierre_brune", acc="gres", toit="ardoise",
         fleche="cuivre_vert"),
    dict(hall="enduit_jaune", pierre="gres", tour="enduit_ocre", acc="pierre_maison_claire", toit="tuile",
         fleche="cuivre_vert"),
)


def _fenetre_hall(b, x, y, w, h, z0, *, cadre, allumee=False):
    """Haute fenêtre à croisée et linteau saillant (repère de façade, plan z0, extérieur -z) : 4 pièces."""
    b.box((x - w / 2 - 0.4, y - 0.4, z0 - 0.15), (x + w / 2 + 0.4, y + h + 0.3, z0), col(cadre), collide=False,
          name="Encadrement")
    kw = {"material": "Neon"} if allumee else {}
    b.box((x - w / 2, y, z0 - 0.28), (x + w / 2, y + h, z0 - 0.05), col("fenetre_lumiere" if allumee else "fenetre"),
          collide=False, name="Vitre", **kw)
    b.box((x - 0.12, y + 0.05, z0 - 0.38), (x + 0.12, y + h - 0.05, z0 - 0.1), col(cadre), collide=False,
          name="Croisee")
    b.box((x - w / 2 - 0.8, y + h + 0.3, z0 - 0.6), (x + w / 2 + 0.8, y + h + 0.9, z0), col(cadre), collide=False,
          studs="top", name="Linteau")


def _arcade(b, xa, xb, n, *, pile_g, pile_d, zf, zg, y_cle, pierre, acc, rng):
    """Rez à arcades (Laubengang) entre xa et xb : piles de façade (zf → zf + 1,6), piles d'extrémité sur toute la
    profondeur (jusqu'à zg), impostes, pleins cintres octogonaux, portes et vitrines au fond de la galerie (zg)."""
    wp = 2.0
    n_piles = (n - 1) + int(pile_g) + int(pile_d)
    wo = (xb - xa - wp * n_piles) / n
    x = xa
    piles = []
    if pile_g:
        piles.append((x, x + wp, True))
        x += wp
    ouvertures = []
    for i in range(n):
        ouvertures.append((x, x + wo))
        x += wo
        if i < n - 1:
            piles.append((x, x + wp, False))
            x += wp
    if pile_d:
        piles.append((x, x + wp, True))
    r = wo / 2
    ys = y_cle - r
    for (p0, p1, bout) in piles:
        b.box((p0, 0, zf - 0.4), (p1, y_cle, zg if bout else zf + 1.6), vr(pierre, rng, 0.02), name="Pile")
        b.box((p0 - 0.3, ys - 0.5, zf - 0.6), (p1 + 0.3, ys, zf + 1.5), col(acc), collide=False, name="Imposte")
    for k, (o0, o1) in enumerate(ouvertures):
        _arc_octo(b, o0, o1, y_cle, zf - 0.3, zf + 1.2, vr(pierre, rng, 0.02), collide=False)
        xc = (o0 + o1) / 2
        with b.at((xc, 0, zg)):
            if k % 2 == 0:
                b.box((-1.7, 0.3, -0.15), (1.7, 6.0, 0), col(acc), collide=False, name="Encadrement")
                b.box((-1.2, 0.3, -0.3), (1.2, 5.5, -0.05), col("porte"), collide=False, name="Porte")
            else:
                b.box((-2.0, 1.4, -0.15), (2.0, 5.6, 0), col("bois"), collide=False, name="Devanture")
                b.box((-1.6, 1.8, -0.3), (1.6, 5.2, -0.05), col("fenetre_lumiere" if k == 1 else "fenetre"),
                      collide=False, name="Vitrine", **({"material": "Neon"} if k == 1 else {}))
    return ouvertures


def beffroi(b, variant=0, largeur=44, profondeur=30):
    """Hôtel de ville et tour d'horloge de la grand-place (repère de la place des œufs ; avant = -Z sur la place).

    Hôtel de ville de deux niveaux : rez à arcades en plein cintre (galerie couverte, portes et vitrines au fond),
    étage à hautes fenêtres à croisée (deux éclairées), cordon et corniche, grand toit à lucarnes entre deux
    pignons à redents surmontés de drapeaux (mobilier.drapeau), cheminées. Tour d'horloge de 13 × 13 en avant de
    la façade : passage voûté, balcon sur consoles, fenêtres cintrées, cadrans sur trois faces (marques d'heure,
    aiguilles à 10 h 10), galerie à garde-corps de fer sur consoles, lanternon ouvert à quatre arcs et sa cloche,
    flèche octogonale et boule dorée (≈ 84). v0 : tour au centre ; v1 : tour à l'extrémité gauche ; v2 : toits
    de tuiles et flèche de cuivre."""
    rng = b.rng
    v = variant % 3
    S = _BEFFROIS[v]
    L2, P2 = largeur / 2, profondeur / 2
    ZF, ZG, ZB = -(P2 - 2.0), -(P2 - 8.0), P2 - 2.0      # façade de l'étage, fond de galerie, façade arrière
    Y1, YC = 9.0, 20.0                                    # dessous de l'étage, dessus des murs
    th = 6.5
    xt = 0.0 if v != 1 else -L2 + th + 1.0
    ZT0, ZT1 = ZF - 1.0, -1.0                             # tour : avant / arrière
    zc = (ZT0 + ZT1) / 2
    hall, pierre, tour, acc = S["hall"], S["pierre"], S["tour"], S["acc"]
    toit = S["toit"]
    YG = 51.0                                             # dessous de la galerie de la tour
    H_TOT = 88.0

    # --- hôtel de ville ----------------------------------------------------------------------------------------
    with b.group("HotelDeVille"):
        b.box((-L2, 0, ZG), (L2, Y1, ZB), vr(hall, rng, 0.02), name="Rez")
        b.box((-L2, Y1, ZF), (L2, YC, ZB), vr(hall, rng, 0.02), name="Etage")
        b.box((-L2 + 0.1, 0, ZF - 0.2), (L2 - 0.1, 0.3, ZG), col("dalle"), studs="top", name="Galerie")
        b.box((-L2 - 0.3, 0, ZG + 0.01), (L2 + 0.3, 1.2, ZB + 0.3), col("soubassement"), name="Socle")
        b.box((-L2 - 0.2, Y1 - 0.4, ZF - 0.55), (L2 + 0.2, Y1 + 0.4, ZF), col(acc), name="Cordon")
        b.box((-L2 - 0.6, YC - 0.6, ZF - 0.6), (L2 + 0.6, YC + 0.4, ZB + 0.6), col(acc), name="Corniche")
        # travées d'arcades de part et d'autre de la tour
        spans = []
        if xt - th - 0.4 > -L2 + 3:
            spans.append((-L2, xt - th - 0.4, True, False))
        if xt + th + 0.4 < L2 - 3:
            spans.append((xt + th + 0.4, L2, False, True))
        for (xa, xb, pg, pd) in spans:
            n = max(1, int(round((xb - xa) / 7.8)))
            _arcade(b, xa, xb, n, pile_g=pg, pile_d=pd, zf=ZF, zg=ZG, y_cle=Y1, pierre=pierre, acc=acc, rng=rng)
            # fenêtres de l'étage
            nf = max(1, int(round((xb - xa) / 5.4)))
            for i in range(nf):
                xw = xa + (xb - xa) * (i + 0.5) / nf
                _fenetre_hall(b, xw, 11.2, 2.0, 5.6, ZF, cadre=acc, allumee=(i == nf // 2 and pg))
        # façade arrière : fenêtres simples
        with b.at((0, 0, ZB), yaw=180):
            for xw in (-15.0, -5.0, 5.0, 15.0):
                for yw in (3.0, 11.6):
                    b.box((xw - 1.4, yw - 0.3, -0.15), (xw + 1.4, yw + 5.0, 0), col(acc), collide=False,
                          name="Encadrement")
                    b.box((xw - 1.0, yw, -0.28), (xw + 1.0, yw + 4.5, -0.05), col("fenetre"), collide=False,
                          name="Vitre")

    # --- toit et pignons à redents -----------------------------------------------------------------------------
    with b.group("Toit"):
        ZR = ZB + 0.6
        YR = YC + 0.4 + ZR * 1.15
        b.wedge((-L2 + 1.2, YC + 0.4, -ZR), (L2 - 1.2, YR, 0), vr(toit, rng, 0.02), down="-z", studs="top",
                name="Toit")
        b.wedge((-L2 + 1.2, YC + 0.4, 0), (L2 - 1.2, YR, ZR), vr(toit, rng, 0.02), down="+z", studs="top",
                name="Toit")
        b.box((-L2 + 1.2, YR - 0.4, -0.5), (L2 - 1.2, YR + 0.6, 0.5), shade(col(toit), 0.8), name="Faitage")
        nst = 5
        dh = (YR + 1.0 - (YC + 0.4)) / nst
        for s in (-1, 1):
            xa, xb = sorted((s * (L2 - 1.2), s * L2))
            for k in range(nst):
                w = ZR * (1 - k / nst)
                b.box((xa, YC + 0.4 + k * dh, -w), (xb, YC + 0.4 + (k + 1) * dh, w),
                      vr(acc, rng, 0.02), studs="top", name="Redent")
            ytop = YC + 0.4 + nst * dh
            with b.at((s * (L2 - 0.6), ytop, 0), yaw=0 if s < 0 else 180):
                mobilier.drapeau(b, hauteur=7.0, variant=(0 if s < 0 else 1) + (2 if v == 2 else 0), longueur=4.0)
        # lucarnes sur le pan avant (hors de la tour)
        pente = (YR - YC - 0.4) / ZR
        yl = YC + 4.2
        zl = -ZR + (yl - YC - 0.4) / pente
        for xd in (-15.0, 15.0) if v != 1 else (0.0, 15.0):
            _lucarne_toit(b, xd, zl, yl - 0.6, 3.4, 3.0, toit, hall, prof=2.6)
        for xd in (-11.0, 11.0):
            zch = 4.0
            ych = YC + 0.4 + (ZR - zch) * pente
            b.box((xd - 1.0, ych - 1.5, zch - 1.0), (xd + 1.0, ych + 3.2, zch + 1.0), col("brique"),
                  name="Cheminee")
            b.box((xd - 1.3, ych + 3.2, zch - 1.3), (xd + 1.3, ych + 3.8, zch + 1.3), col("brique_fonce"),
                  studs="top", collide=False, name="Chapeau")

    # --- tour d'horloge ----------------------------------------------------------------------------------------
    with b.group("TourHorloge"):
        with b.at((xt, 0, 0)):
            # passage voûté entre deux piles
            for s in (-1, 1):
                xa, xb = sorted((s * th, s * 3.25))
                b.box((xa, 0, ZT0), (xb, 10.0, ZT1), vr(tour, rng, 0.02), name="Pile")
                b.box((s * 3.25 - 0.3 if s > 0 else -3.55, 6.25, ZT0 - 0.5),
                      (s * 3.25 + 0.3 if s < 0 else 3.55, 6.75, ZT0 + 1.0), col(acc), collide=False, name="Imposte")
            _arc_octo(b, -3.25, 3.25, 10.0, ZT0 - 0.3, ZT0 + 1.4, vr(tour, rng, 0.02), collide=False)
            with b.at((0, 0, ZG)):
                b.box((-2.2, 0.3, -0.15), (2.2, 7.4, 0), col(acc), collide=False, name="Encadrement")
                b.box((-1.6, 0.3, -0.3), (1.6, 6.8, -0.05), col("porte"), collide=False, name="Porte")
                _lanterne(b, 0, 8.6, -0.15)
            b.box((-th, 10.0, ZT0), (th, YG, ZT1), vr(tour, rng, 0.02), name="Tour")
            for sx in (-1, 1):
                for zz in (ZT0, ZT1):
                    xa, xb = sorted((sx * (th + 0.4), sx * (th - 1.2)))
                    za, zb = (zz - 0.4, zz + 1.2) if zz == ZT0 else (zz - 1.2, zz + 0.4)
                    b.box((xa, 0 if zz == ZT0 else YC, za), (xb, YG, zb), vr(acc, rng, 0.02), name="Chaine")
            for y in (YC + 0.4, YG - 15.0, YG - 0.2):
                b.box((-th - 0.5, y - 0.6, ZT0 - 0.5), (th + 0.5, y, ZT1 + 0.5), col(acc), name="Cordon")
            # balcon sur consoles au-dessus du passage, porte-fenêtre éclairée
            b.box((-4.0, 10.0, ZT0 - 1.4), (4.0, 10.6, ZT0), col(acc), studs="top", name="Balcon")
            for xx in (-3.2, 3.2):
                b.wedge_under((xx - 0.45, 8.6, ZT0 - 1.4), (xx + 0.45, 10.0, ZT0), col(acc), down="-z",
                              collide=False, name="Console")
            b.box((-4.0, 10.6, ZT0 - 1.4), (4.0, 11.9, ZT0 - 1.1), col("fonte"), collide=False, name="Garde_corps")
            for s in (-1, 1):
                xa, xb = sorted((s * 4.0, s * 3.7))
                b.box((xa, 10.6, ZT0 - 1.1), (xb, 11.9, ZT0), col("fonte"), collide=False, name="Garde_corps")
            b.box((-1.6, 10.6, ZT0 - 0.15), (1.6, 15.8, ZT0), col(acc), collide=False, name="Encadrement")
            b.box((-1.1, 10.6, ZT0 - 0.3), (1.1, 15.2, ZT0 - 0.05), col("fenetre_lumiere"), material="Neon",
                  collide=False, name="Vitre")
            # fenêtres à croisée (avant : paire ; côtés : une)
            for (fx, fz, yaw, xs) in ((0, ZT0, 0, (-2.4, 2.4)), (-th, zc, 90, (0.0,)), (th, zc, -90, (0.0,))):
                with b.at((fx, 0, fz), yaw=yaw):
                    for xw in xs:
                        _fenetre_hall(b, xw, 24.6, 1.8, 4.8, 0, cadre=acc)
            # cadrans sur trois faces
            for (fx, fz, yaw, n) in ((0, ZT0, 0, 12), (-th, zc, 90, 4), (th, zc, -90, 4)):
                with b.at((fx, 0, fz), yaw=yaw):
                    b.box((-5.4, YG - 13.6, -0.2), (5.4, YG - 1.4, 0), col(acc), collide=False, name="Panneau")
                    _horloge(b, YG - 7.5, 4.2, z0=-0.2, marques=n)
            # galerie sur consoles, garde-corps de fer, pots à feu
            b.box((-th - 1.0, YG, ZT0 - 1.0), (th + 1.0, YG + 0.8, ZT1 + 1.0), col(acc), studs="top", name="Galerie")
            b.wedge_under((-th - 1.0, YG - 1.4, ZT0 - 1.0), (th + 1.0, YG, ZT0), col(acc), down="-z", name="Console")
            b.wedge_under((-th - 1.0, YG - 1.4, ZT1), (th + 1.0, YG, ZT1 + 1.0), col(acc), down="+z", name="Console")
            b.wedge_under((-th - 1.0, YG - 1.4, ZT0), (-th, YG, ZT1), col(acc), down="-x", name="Console")
            b.wedge_under((th, YG - 1.4, ZT0), (th + 1.0, YG, ZT1), col(acc), down="+x", name="Console")
            yg = YG + 0.8
            gx, gz0, gz1 = th + 0.75, ZT0 - 0.75, ZT1 + 0.75
            fer = col("fonte")
            b.box((-gx, yg + 1.6, gz0 - 0.12), (gx, yg + 1.85, gz0 + 0.12), fer, collide=False, name="Main_courante")
            b.box((-gx, yg + 1.6, gz1 - 0.12), (gx, yg + 1.85, gz1 + 0.12), fer, collide=False, name="Main_courante")
            b.box((-gx - 0.12, yg + 1.6, gz0), (-gx + 0.12, yg + 1.85, gz1), fer, collide=False, name="Main_courante")
            b.box((gx - 0.12, yg + 1.6, gz0), (gx + 0.12, yg + 1.85, gz1), fer, collide=False, name="Main_courante")
            for px in (-gx, -gx / 3, gx / 3, gx):
                for pz in (gz0, gz1):
                    b.box((px - 0.13, yg, pz - 0.13), (px + 0.13, yg + 1.6, pz + 0.13), fer, collide=False,
                          name="Barreau")
            for pz in (zc - 2.5, zc + 2.5):
                for px in (-gx, gx):
                    b.box((px - 0.13, yg, pz - 0.13), (px + 0.13, yg + 1.6, pz + 0.13), fer, collide=False,
                          name="Barreau")
            # échauguettes d'angle sur la galerie
            for px in (-gx, gx):
                for pz in (gz0, gz1):
                    b.cyl((px, yg + 1.5, pz), 0.95, 3.0, vr(tour, rng, 0.02), axis="y", name="Echauguette")
                    b.cyl((px, yg + 3.2, pz), 1.15, 0.4, col(acc), axis="y", studs="top", name="Echauguette")
                    b.cyl((px, yg + 3.85, pz), 0.8, 0.9, col(S["fleche"]), axis="y", name="Echauguette")
                    b.cyl((px, yg + 4.65, pz), 0.42, 0.7, col(S["fleche"]), axis="y", collide=False, name="Echauguette")
                    b.ball((px, yg + 5.2, pz), 0.3, col("or"), collide=False, name="Epi")
            # lanternon ouvert à quatre arcs, cloche
            with b.at((0, 0, zc)):
                la, lp = 4.5, 1.6
                yl0, yl1 = yg, yg + 8.0
                for sx in (-1, 1):
                    for sz in (-1, 1):
                        xa, xb = sorted((sx * la, sx * (la - lp)))
                        za, zb = sorted((sz * la, sz * (la - lp)))
                        b.box((xa, yl0, za), (xb, yl1, zb), vr(tour, rng, 0.02), name="Pile")
                for yaw in FACES:
                    with b.at((0, 0, 0), yaw=yaw):
                        s_ = 1.5
                        b.wedge_under((-la + lp, yl1 - s_, -la), (-la + lp + s_, yl1, -la + 0.9), col(tour), down="+x",
                                      collide=False, name="Arc")
                        b.wedge_under((la - lp - s_, yl1 - s_, -la), (la - lp, yl1, -la + 0.9), col(tour), down="-x",
                                      collide=False, name="Arc")
                b.box((-la, yl1, -la), (la, yl1 + 1.6, la), vr(tour, rng, 0.02), name="Entablement")
                b.box((-la - 0.6, yl1 + 1.6, -la - 0.6), (la + 0.6, yl1 + 2.2, la + 0.6), col(acc), studs="top",
                      name="Corniche")
                b.box((-la + 0.3, yl1 - 0.6, -0.3), (la - 0.3, yl1, 0.3), col("bois"), name="Joug")
                _cloche(b, 0, yl1 - 0.6, 0, r=1.3)
                yf = yl1 + 2.2
                yt = _fleche(b, 0, yf, 0, 4.4, H_TOT - 2.6 - yf, S["fleche"], ep=0.45,
                             studs=(S["fleche"] == "ardoise"), name="Fleche")
                b.ball((0, yt + 0.5, 0), 0.8, col("or"), collide=False, name="Boule")
                b.cyl((0, yt + 1.9, 0), 0.15, 1.8, col("fonte"), axis="y", collide=False, name="Pointe")
                h_tot = yt + 2.8
    return {"emprise": (largeur, profondeur + 0.4), "hauteur": round(h_tot, 1)}


# ---------------------------------------------------------------------------
# 4) Fontaine de marché
# ---------------------------------------------------------------------------

def _anneau(b, n, r_axe, ep, y0, y1, couleur, rng, studs="none", name="Margelle", **kw):
    """Anneau polygonal de n segments (murets tangents) : axe à r_axe du centre, épaisseur ep, de y0 à y1."""
    L = 2 * r_axe * math.tan(math.pi / n) + ep * math.tan(math.pi / n)
    for k in range(n):
        phi = 2 * math.pi * k / n
        b.boxc((r_axe * math.cos(phi), (y0 + y1) / 2, r_axe * math.sin(phi)), (L, y1 - y0, ep),
               vr(couleur, rng, 0.015), yaw=90 - math.degrees(phi), studs=studs, name=name, **kw)


def fontaine(b, variant=0):
    """Fontaine de marché (Marktbrunnen) sur deux marches : bassin de pierre (octogonal v0, carré v1, rond à deux
    vasques v2) à margelle studdée, eau, pile centrale à quatre becs de bronze et filets d'eau, colonne à base
    moulurée, chapiteau orné et amortissement doré (boule, pomme de pin ou lanternon) — aucune statue ;
    pots de géraniums sur la marche."""
    rng = b.rng
    v = variant % 3
    pierre, claire, sombre = "pierre_maison", "pierre_maison_claire", "gres_fonce"
    with b.group("Fontaine"):
        # marches
        if v == 1:
            b.box((-8.0, 0, -8.0), (8.0, 0.5, 8.0), col(sombre), studs="top", name="Marche")
            b.box((-7.2, 0.5, -7.2), (7.2, 1.0, 7.2), col(claire), studs="top", name="Marche")
        else:
            b.cyl((0, 0.25, 0), 8.0, 0.5, col(sombre), axis="y", studs="top", name="Marche")
            b.cyl((0, 0.75, 0), 7.3, 0.5, col(claire), axis="y", studs="top", name="Marche")
        y_b = 1.0
        # bassin
        if v == 0:
            _anneau(b, 8, 6.0, 1.0, y_b, 3.4, pierre, rng, name="Bassin")
            _anneau(b, 8, 6.0, 1.6, 3.4, 3.8, claire, rng, studs="top", name="Margelle")
            b.cyl((0, 2.0, 0), 6.0, 2.0, col("eau"), axis="y", name="Eau")
            rv = 6.0 / math.cos(math.pi / 8)
            for k in range(8):
                phi = 2 * math.pi * (k + 0.5) / 8
                b.boxc((rv * math.cos(phi), (y_b + 4.1) / 2, rv * math.sin(phi)), (1.9, 4.1 - y_b, 1.9),
                       col(claire), yaw=-math.degrees(phi), studs="top", name="Borne")
            y_eau = 3.0
        elif v == 1:
            for yaw in FACES:
                with b.at((0, 0, 0), yaw=yaw):
                    b.box((-6.5, y_b, -6.5), (5.5, 3.4, -5.5), vr(pierre, rng, 0.015), name="Bassin")
                    b.box((-6.8, 3.4, -6.8), (5.2, 3.8, -5.2), col(claire), studs="top", name="Margelle")
                    b.box((-3.5, 1.6, -6.62), (3.5, 2.9, -6.5), col(sombre), collide=False, name="Panneau")
            b.box((-5.5, y_b, -5.5), (5.5, 3.0, 5.5), col("eau"), name="Eau")
            y_eau = 3.0
        else:
            b.cyl((0, 2.0, 0), 6.6, 2.0, col(pierre), axis="y", name="Bassin")
            b.cyl((0, 3.1, 0), 6.0, 0.25, col("eau"), axis="y", name="Eau")
            _anneau(b, 10, 6.3, 0.8, 3.0, 3.7, claire, rng, studs="top", name="Margelle")
            rv = 6.3 / math.cos(math.pi / 10)
            for k in range(10):
                phi = 2 * math.pi * (k + 0.5) / 10
                b.cyl((rv * math.cos(phi), 3.4, rv * math.sin(phi)), 0.55, 0.9, col(claire), axis="y", studs="top",
                      name="Borne")
            y_eau = 3.22
        # pile centrale et becs
        hp = 5.4 if v != 2 else 4.4
        b.box((-1.3, y_b, -1.3), (1.3, hp, 1.3), vr(pierre, rng, 0.02), name="Pile")
        b.box((-1.6, hp, -1.6), (1.6, hp + 0.5, 1.6), col(claire), studs="top", name="Pile")
        y_bec = hp - 0.9
        for yaw in FACES:
            with b.at((0, 0, 0), yaw=yaw):
                if v == 1:
                    b.box((-0.35, y_bec - 0.3, -2.1), (0.35, y_bec + 0.3, -1.3), col("bronze"), collide=False,
                          name="Bec")
                else:
                    b.cyl((0, y_bec, -1.85), 0.2, 1.1, col("bronze"), axis="z", collide=False, name="Bec")
                    b.ball((0, y_bec + 0.05, -1.35), 0.35, col("bronze"), collide=False, name="Bec")
                pts = [(0, y_bec, -2.3), (0, y_bec - 0.5, -3.1), (0, y_eau, -3.5)]
                _corde(b, pts[0], pts[1], 0.16, "eau_claire", name="Jet")
                _corde(b, pts[1], pts[2], 0.16, "eau_claire", name="Jet")
        # colonne, chapiteau, amortissement
        yc0 = hp + 0.5
        if v == 2:
            # vasque haute portée par la colonne
            b.cyl((0, yc0 + 0.6, 0), 0.75, 1.2, col(claire), axis="y", name="Colonne")
            b.cyl((0, yc0 + 1.5, 0), 1.6, 0.6, col(pierre), axis="y", name="Vasque")
            b.cyl((0, yc0 + 2.2, 0), 2.9, 0.8, col(claire), axis="y", studs="top", name="Vasque")
            b.cyl((0, yc0 + 2.65, 0), 2.5, 0.12, col("eau_claire"), axis="y", collide=False, name="Eau")
            for k in range(4):
                phi = math.radians(45 + 90 * k)
                x, z = 2.95 * math.cos(phi), 2.95 * math.sin(phi)
                _corde(b, (x, yc0 + 2.5, z), (x * 1.05, y_eau, z * 1.05), 0.1, "eau_claire", name="Filet")
            yc0 = yc0 + 2.6
            hcol = 2.6
        else:
            hcol = 3.4
        b.cyl((0, yc0 + 0.25, 0), 1.0, 0.5, col(claire), axis="y", name="Base")
        b.cyl((0, yc0 + 0.5 + hcol / 2, 0), 0.7, hcol, col(claire), axis="y", name="Colonne")
        yk = yc0 + 0.5 + hcol
        b.cyl((0, yk + 0.2, 0), 1.0, 0.4, col(pierre), axis="y", name="Chapiteau")
        b.boxc((0, yk + 0.75, 0), (2.0, 0.7, 2.0), col(claire), yaw=45, name="Chapiteau")
        b.box((-1.0, yk + 1.1, -1.0), (1.0, yk + 1.5, 1.0), col(pierre), studs="top", name="Tailloir")
        ya = yk + 1.5
        if v == 0:
            # petit obélisque doré (pointe effilée, pas de silhouette en boule)
            b.box((-0.55, ya, -0.55), (0.55, ya + 0.4, 0.55), col("bronze"), collide=False, name="Amortissement")
            b.box((-0.35, ya + 0.4, -0.35), (0.35, ya + 1.6, 0.35), col("or"), collide=False, name="Amortissement")
            yo = _pyramide(b, 0, ya + 1.6, 0, 0.7, 0.7, 1.4, "or", ep=0.2, collide=False, name="Amortissement")
            h_tot = yo
        elif v == 1:
            b.cyl((0, ya + 0.35, 0), 0.7, 0.7, col("or"), axis="y", collide=False, name="Pomme_de_pin")
            b.ball((0, ya + 1.2, 0), 0.75, col("or"), collide=False, name="Pomme_de_pin")
            b.cyl((0, ya + 2.0, 0), 0.38, 0.8, col("or"), axis="y", collide=False, name="Pomme_de_pin")
            h_tot = ya + 2.4
        else:
            b.box((-0.6, ya, -0.6), (0.6, ya + 1.2, 0.6), col("lampe"), material="Neon", collide=False,
                  name="Lanternon")
            b.box((-0.8, ya + 1.2, -0.8), (0.8, ya + 1.5, 0.8), col("fonte"), collide=False, name="Lanternon")
            b.ball((0, ya + 1.8, 0), 0.4, col("or"), collide=False, name="Amortissement")
            h_tot = ya + 2.2
        # pots de fleurs sur la marche
        fleurs = ("fleur_rouge", "fleur_rose", "fleur_rouge", "fleur_jaune")
        for k in range(4):
            phi = math.radians(45 + 90 * k)
            rr = 7.0 if v != 1 else 6.6
            x, z = rr * math.cos(phi), rr * math.sin(phi)
            b.cyl((x, 1.45, z), 0.55, 0.9, col("brique"), axis="y", name="Pot")
            b.ball((x, 2.15, z), 0.7, col(fleurs[k]), collide=False, name="Geraniums")
    return {"emprise": (16.0, 16.0), "hauteur": round(h_tot, 1)}


# ---------------------------------------------------------------------------
# 5) Moulins
# ---------------------------------------------------------------------------

def _ailes(b, cx, cy, zc, R, angle0, *, toiles=(0, 2), r0=2.2, larg=2.6, n=4):
    """Quatre ailes à claire-voie dans le plan z = zc autour du moyeu (cx, cy) : verge, longeron extérieur,
    barreaux et, pour les ailes de `toiles`, une toile tendue. Tout est tourné librement (rot_z)."""
    bois, clair, toile = col("bois"), col("bois_clair"), col("voile_moulin")
    for k in range(n):
        a = angle0 + k * 360 / n
        ar = math.radians(a)
        d = np.array([math.cos(ar), math.sin(ar)])
        p = np.array([-math.sin(ar), math.cos(ar)])      # côté du bord de fuite
        ctr = np.array([cx, cy]) + d * (R / 2 + 0.2)
        b.part("block", (R + 0.4, 0.55, 0.5), (ctr[0], ctr[1], zc), rot_z(a), bois, collide=False, name="Verge")
        # longeron extérieur
        c2 = np.array([cx, cy]) + d * ((r0 + R) / 2) + p * larg
        b.part("block", (R - r0, 0.3, 0.3), (c2[0], c2[1], zc - 0.05), rot_z(a), clair, collide=False,
               name="Longeron")
        # barreaux
        for t in np.linspace(r0, R, 4):
            c3 = np.array([cx, cy]) + d * t + p * larg / 2
            b.part("block", (0.25, larg + 0.3, 0.25), (c3[0], c3[1], zc - 0.1), rot_z(a), clair, collide=False,
                   name="Barreau")
        if k in toiles:
            c4 = np.array([cx, cy]) + d * ((r0 + R) / 2) + p * (larg / 2 + 0.05)
            b.part("block", (R - r0 - 0.2, larg - 0.25, 0.12), (c4[0], c4[1], zc + 0.12), rot_z(a), toile,
                   collide=False, shadow=False, material="Fabric", name="Toile")


def _moulin_pivot(b, rng, *, angle, butte, toiles=(0, 2)):
    """Moulin sur pivot (Bockwindmühle) : piles de pierre, chevalet de bois en croix, pivot, cage de planches,
    toit à deux pans, échelle et queue à l'arrière, ailes à l'avant (plan z ≈ -7)."""
    gris = col("bois_gris")
    y0 = 0.0
    if butte:
        b.cyl((0, 0.5, 0), 6.5, 1.0, col("herbe"), axis="y", studs="top", name="Butte")
        b.cyl((0, 1.3, 0), 4.8, 0.6, col("herbe_claire"), axis="y", studs="top", name="Butte")
        y0 = 1.6
    for (x, z) in ((3.6, 0), (-3.6, 0), (0, 3.6), (0, -3.6)):
        b.box((x - 0.7, y0, z - 0.7), (x + 0.7, y0 + 1.2, z + 0.7), col("pierre_brune"), studs="top", name="Pile")
    yt = y0 + 1.2
    trav = col("bois")
    b.box((-4.2, yt, -0.45), (4.2, yt + 0.8, 0.45), trav, name="Sole")
    b.box((-0.45, yt, -4.2), (0.45, yt + 0.8, 4.2), trav, name="Sole")
    for (x, z) in ((3.4, 0), (-3.4, 0), (0, 3.4), (0, -3.4)):
        _poutre(b, (x, yt + 0.8, z), (x * 0.15, yt + 5.0, z * 0.15), 0.5, trav, name="Contrefiche")
    b.box((-0.6, yt + 0.8, -0.6), (0.6, 9.0, 0.6), col("bois_moyen"), name="Pivot")
    # cage
    yb, yh = 9.0, 20.0
    b.box((-3.8, yb, -4.6), (3.8, yh, 4.6), vr(gris, rng, 0.03), name="Cage")
    for sx in (-1, 1):
        for sz in (-1, 1):
            xa, xb = sorted((sx * 3.95, sx * 3.35))
            za, zb = sorted((sz * 4.75, sz * 4.15))
            b.box((xa, yb, za), (xb, yh, zb), col("bois"), collide=False, name="Cornier")
    b.box((-3.95, yb - 0.4, -4.75), (3.95, yb + 0.3, 4.75), col("bois"), name="Sabliere")
    b.box((-1.2, 12.0, -4.75), (1.2, 13.6, -4.5), col("fenetre"), collide=False, name="Fenetre")
    for sx in (-1, 1):
        xa, xb = sorted((sx * 3.8, sx * 4.0))
        b.box((xa, 14.5, -1.0), (xb, 16.0, 1.0), col("fenetre"), collide=False, name="Fenetre")
    toitc = shade(gris, 0.78)
    b.wedge((-4.3, yh, -5.3), (0, yh + 3.4, 5.3), toitc, down="-x", studs="top", name="Toit")
    b.wedge((0, yh, -5.3), (4.3, yh + 3.4, 5.3), toitc, down="+x", studs="top", name="Toit")
    b.box((-0.35, yh + 3.2, -5.4), (0.35, yh + 3.7, 5.4), col("bois"), name="Faitage")
    # échelle et queue
    b.box((-1.6, yb - 0.3, 4.6), (1.6, yb + 0.2, 6.0), col("bois"), studs="top", name="Palier")
    b.box((-0.9, yb + 0.2, 4.55), (0.9, yb + 3.6, 4.7), col("porte"), collide=False, name="Porte")
    for sx in (-1, 1):
        _poutre(b, (sx * 0.95, yb, 5.6), (sx * 0.95, y0 + 0.1, 11.0), 0.3, col("bois_clair"), name="Echelle")
    for t in (0.2, 0.4, 0.6, 0.8):
        b.box((-0.95, yb - (yb - y0) * t, 5.6 + 5.4 * t - 0.12), (0.95, yb - (yb - y0) * t + 0.22, 5.6 + 5.4 * t + 0.12),
              col("bois_clair"), collide=False, name="Echelon")
    _poutre(b, (0, yb + 0.6, 4.6), (0, y0 + 0.3, 11.6), 0.6, col("bois"), name="Queue")
    # arbre moteur et ailes
    yh_ = 17.6
    b.cyl((0, yh_, -5.6), 0.8, 2.2, col("bois_moyen"), axis="z", name="Arbre")
    b.cyl((0, yh_, -6.9), 1.1, 0.6, col("bois"), axis="z", collide=False, name="Moyeu")
    _ailes(b, 0, yh_, -7.2, 12.4, angle, toiles=toiles)
    return yh_ + 12.4


def moulin(b, variant=0):
    """Moulins de la prairie. v0 : moulin sur pivot de bois sur une butte herbeuse, ailes inclinées à 17° (deux
    toilées) ; v1 : moulin-tour de pierre blanchie (fût en trois tambours, cordons, porte, fenêtres, calotte),
    ailes à 35° ; v2 : moulin sur pivot aux ailes en croix, appentis et sacs de grain. Ailes dans le plan
    z ≈ -7 (avant), rayon ≈ 12,4."""
    rng = b.rng
    v = variant % 3
    with b.group("Moulin"):
        if v == 0:
            h = _moulin_pivot(b, rng, angle=17, butte=True)
        elif v == 2:
            h = _moulin_pivot(b, rng, angle=0, butte=False, toiles=(1, 3))
            # appentis et sacs
            b.box((-6.4, 0, 1.2), (-3.0, 3.4, 6.2), vr("bois_gris", rng, 0.03), name="Appentis")
            b.wedge((-6.8, 3.4, 0.8), (-2.7, 4.8, 6.6), col("tuile_brune"), down="-x", studs="top", name="Appentis")
            b.box((-3.12, 0, 2.6), (-2.95, 2.6, 4.4), col("porte"), collide=False, name="Porte")
            with b.at((-3.2, 0, -3.0), yaw=20):
                mobilier.sacs(b, variant=1)
        else:
            blanc, sombre = "enduit_blanc", "pierre_maison"
            b.cyl((0, 0.6, 0), 5.3, 1.2, col("soubassement"), axis="y", studs="top", name="Socle")
            tambours = ((4.7, 1.2, 8.0), (4.3, 8.0, 14.0), (3.9, 14.0, 19.0))
            for i, (r, ya, yb) in enumerate(tambours):
                b.cyl((0, (ya + yb) / 2, 0), r, yb - ya, vr(blanc, rng, 0.02), axis="y", name="Tour")
                if i < 2:
                    b.cyl((0, yb - 0.2, 0), r + 0.15, 0.4, col(sombre), axis="y", collide=False, name="Cordon")
            b.box((-1.3, 1.2, -4.85), (1.3, 5.2, -4.2), col(sombre), name="Encadrement")
            b.box((-0.9, 1.2, -4.95), (0.9, 4.8, -4.5), col("porte"), name="Porte")
            for (yy, r, ang) in ((10.0, 4.3, 0), (15.5, 3.9, 120), (5.5, 4.7, 200)):
                with b.at((0, 0, 0), yaw=ang):
                    b.box((-0.6, yy, -r - 0.12), (0.6, yy + 1.6, -r + 0.6), col("fenetre"), collide=False,
                          name="Fenetre")
            b.cyl((0, 19.3, 0), 4.3, 0.6, col("bois"), axis="y", name="Calotte")
            b.ball((0, 19.6, 0), 3.9, col("bois_gris"), name="Calotte")
            b.box((-0.5, 22.6, 1.5), (0.5, 23.8, 2.5), col("bois"), collide=False, name="Lucarne")
            b.cyl((0, 21.0, -4.4), 0.8, 2.4, col("bois_moyen"), axis="z", name="Arbre")
            b.cyl((0, 21.0, -5.8), 1.1, 0.6, col("bois"), axis="z", collide=False, name="Moyeu")
            _ailes(b, 0, 21.0, -6.1, 12.4, 35, toiles=(0, 1, 2, 3))
            with b.at((3.6, 0, -4.4), yaw=-30):
                mobilier.sacs(b, variant=0)
            h = 21.0 + 12.4
    return {"emprise": (24.8, 12.0), "hauteur": round(h, 1)}


# ---------------------------------------------------------------------------
# 6) Dépôt de ravitaillement
# ---------------------------------------------------------------------------

def depot_ravitaillement(b, variant=0, largeur=36, profondeur=20):
    """Dépôt de ravitaillement au pied de la muraille (avant = -Z) : cour pavée, long hangar ouvert de charpente
    (poteaux, sablières, aisseliers, appentis de tuiles qui descend vers l'arrière, fond de planches), caisses,
    tonneaux, sacs et bâche à l'abri ; grue de bois (mât, flèche, hauban, treuil, charge suspendue), charrette,
    pyramide de boulets, cour fermée d'une clôture à portail, deux lanternes."""
    rng = b.rng
    v = variant % 2
    L2, P2 = largeur / 2, profondeur / 2
    bois, gris = col("bois"), col("bois_gris")
    toit = "tuile_brune" if v == 0 else "ardoise"
    x0, x1 = -L2 + 0.5, 3.5            # hangar
    zf, zb = -P2 + 5.0, P2 - 1.2
    with b.group("Depot"):
        b.box((-L2, 0, -P2), (L2, 0.25, P2), col("pave_brun"), studs="top", name="Cour")
        y = 0.25
        # charpente
        xs = [x0 + 0.5 + (x1 - x0 - 1.0) * k / 3 for k in range(4)]
        for xp in xs:
            b.box((xp - 0.4, y, zf - 0.4), (xp + 0.4, 9.0, zf + 0.4), bois, name="Poteau")
            b.box((xp - 0.4, y, zb - 0.4), (xp + 0.4, 6.6, zb + 0.4), bois, name="Poteau")
        b.box((x0 - 0.3, 8.4, zf - 0.5), (x1 + 0.3, 9.2, zf + 0.5), bois, name="Sabliere")
        b.box((x0 - 0.3, 6.0, zb - 0.5), (x1 + 0.3, 6.8, zb + 0.5), bois, name="Sabliere")
        for xp in (xs[0], xs[3]):
            for s in (-1, 1):
                if (xp == xs[0] and s < 0) or (xp == xs[3] and s > 0):
                    continue
                _poutre(b, (xp + s * 0.2, 6.6, zf), (xp + s * 2.2, 8.6, zf), 0.4, bois, collide=False,
                        name="Aisselier")
        for xp in (xs[1], xs[2]):
            for s in (-1, 1):
                _poutre(b, (xp + s * 0.2, 6.6, zf), (xp + s * 2.2, 8.6, zf), 0.4, bois, collide=False,
                        name="Aisselier")
        b.box((x0, y, zb - 0.3), (x1, 6.0, zb + 0.3), vr(gris, rng, 0.03), name="Fond")
        b.box((x0 - 0.3, y, zf + 0.5), (x0 + 0.3, 6.0, zb), vr(gris, rng, 0.03), name="Pignon")
        _pan_z(b, x0 - 0.8, x1 + 0.8, zf - 1.6, 9.9, zb + 1.0, 6.9, 0.5, vr(toit, rng, 0.02), name="Appentis")
        b.box((x0 - 0.8, 9.0, zf - 1.75), (x1 + 0.8, 9.6, zf - 1.45), col("bois_moyen"), collide=False, name="Rive")
        # marchandises à l'abri
        with b.at((-13.0, y, 2.5)):
            mobilier.caisses(b, variant=2)
        with b.at((-7.0, y, 5.2), yaw=8):
            mobilier.tonneaux(b, variant=2)
        with b.at((-1.5, y, 4.0), yaw=-10):
            mobilier.sacs(b, variant=1)
        b.box((-9.0, y, -1.5), (-4.0, 2.6, 1.5), col("bois_clair"), studs="top", name="Pile")
        b.box((-9.2, y + 1.0, -1.7), (-3.8, 3.0, 1.7), col("toile_verte" if v == 0 else "toile_creme"),
              material="Fabric", studs="top", collide=False, name="Bache")
        # grue de bois
        gx, gz = 11.0, 5.5
        b.box((gx - 1.8, y, gz - 0.4), (gx + 1.8, y + 0.8, gz + 0.4), bois, name="Pied")
        b.box((gx - 0.4, y, gz - 1.8), (gx + 0.4, y + 0.8, gz + 1.8), bois, name="Pied")
        b.box((gx - 0.5, y + 0.8, gz - 0.5), (gx + 0.5, 15.0, gz + 0.5), col("bois_echafaud"), name="Mat")
        zt = -1.8
        tip = (gx, 13.4, zt)
        _poutre(b, (gx, 2.4, gz - 0.4), tip, 0.6, col("bois_echafaud"), name="Fleche")
        _corde(b, (gx, 14.8, gz), tip, 0.1, name="Hauban")
        b.cyl((gx, 13.0, zt), 0.45, 0.6, col("fer"), axis="x", collide=False, name="Poulie")
        _corde(b, (gx, 12.6, zt), (gx, 7.3, zt), 0.08, name="Corde")
        b.boxc((gx, 6.2, zt), (2.2, 2.0, 2.2), col("bois_clair"), yaw=12, studs="top", collide=False, name="Charge")
        b.cyl((gx + 1.3, 2.0, gz - 1.4), 0.6, 1.8, col("bois_moyen"), axis="x", collide=False, name="Treuil")
        b.box((gx + 2.2, 1.0, gz - 1.55), (gx + 2.4, 2.6, gz - 1.25), col("fer"), collide=False, name="Manivelle")
        # charrette, boulets
        with b.at((10.4, y, -6.4), yaw=95):
            mobilier.charrette(b, variant=1 if v == 0 else 2)
        with b.at((-2.5, y, -7.6)):
            mobilier.pile_boulets(b, variant=0)
        # clôture de la cour et portail
        cl = col("bois_clair")
        for zz in (-P2 + 0.5, -2.0, 4.5, P2 - 0.6):
            b.box((L2 - 0.9, y, zz - 0.3), (L2 - 0.3, 3.6, zz + 0.3), bois, name="Piquet")
        for yy in (1.4, 2.8):
            b.box((L2 - 0.75, yy, -P2 + 0.5), (L2 - 0.45, yy + 0.35, P2 - 0.6), cl, collide=False, name="Lisse")
        for xx in (4.6, 13.0):
            b.box((xx - 0.3, y, -P2 + 0.2), (xx + 0.3, 4.0, -P2 + 0.8), bois, name="Piquet")
        for yy in (1.4, 2.8):
            b.box((13.0, yy, -P2 + 0.35), (L2 - 0.6, yy + 0.35, -P2 + 0.65), cl, collide=False, name="Lisse")
        for s, xh in ((1, 4.9), (-1, 12.7)):
            with b.at((xh, 0, -P2 + 0.5)):
                b.box((0 if s > 0 else -3.85, 0.6, -0.12), (3.85 if s > 0 else 0, 3.2, 0.12), cl, collide=False,
                      name="Vantail")
                _barre(b, 0.3 * s, 0.9, 3.55 * s, 2.9, -0.27, -0.12, 0.3, "bois", collide=False, name="Echarpe")
        # lanternes sur les poteaux avant
        for xp in (xs[1], xs[2]):
            with b.at((xp, 0, zf - 0.4)):
                _lanterne(b, 0, 7.4, 0)
    return {"emprise": (largeur, profondeur), "hauteur": 15.0}


# ---------------------------------------------------------------------------
# 7) Tour de guet
# ---------------------------------------------------------------------------

def tour_guet(b, variant=0, hauteur=40):
    """Tour de guet de charpente : quatre poteaux légèrement inclinés, lisses et croix de Saint-André sur deux
    niveaux, échelle, plate-forme à garde-corps de planches vers 0,8 h, poteaux de toit, toit en pavillon lisse
    (tuiles brunes v0, ardoise v1, tuiles en gradins v2), cloche d'alarme, drapeau uni.
    v1 : socle de pierre ; v2 : piles de pierre sous les poteaux."""
    rng = b.rng
    v = variant % 3
    H = float(hauteur)
    Hp = round(H * 0.7)
    bois, clair = col("bois"), col("bois_echafaud")
    y0 = 0.0
    with b.group("TourGuet"):
        if v == 1:
            b.box((-5.0, 0, -5.0), (5.0, 3.0, 5.0), vr("pierre_maison", rng, 0.02), studs="top", name="Socle")
            y0 = 3.0
        elif v == 2:
            for sx in (-1, 1):
                for sz in (-1, 1):
                    b.box((sx * 4.3 - 0.9, 0, sz * 4.3 - 0.9), (sx * 4.3 + 0.9, 1.6, sz * 4.3 + 0.9),
                          col("pierre_brune"), studs="top", name="Pile")
            y0 = 1.6

        def poteau(sx, sz, y):
            t = (y - y0) / (Hp - y0)
            r = 4.3 - 1.0 * t
            return (sx * r, y, sz * r)

        for sx in (-1, 1):
            for sz in (-1, 1):
                _poutre(b, poteau(sx, sz, y0), poteau(sx, sz, Hp + 0.6), 0.8, bois, name="Poteau")
        ym = (y0 + Hp) / 2
        coins = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        for i in range(4):
            (ax, az), (bx, bz) = coins[i], coins[(i + 1) % 4]
            _poutre(b, poteau(ax, az, ym), poteau(bx, bz, ym), 0.45, bois, ext=0.3, name="Lisse")
            for (ya, yb) in ((y0 + 0.6, ym), (ym, Hp)):
                _poutre(b, poteau(ax, az, ya), poteau(bx, bz, yb), 0.32, clair, collide=False, name="Croix")
                _poutre(b, poteau(bx, bz, ya), poteau(ax, az, yb), 0.32, clair, collide=False, name="Croix")
        # échelle intérieure
        for sx in (-1, 1):
            _poutre(b, (sx * 0.7, y0, 2.6), (sx * 0.7, Hp + 0.6, 0.6), 0.28, clair, collide=False, name="Echelle")
        n_ech = 4
        for k in range(1, n_ech + 1):
            t = k / (n_ech + 1)
            yy = y0 + (Hp + 0.6 - y0) * t
            zz = 2.6 - 2.0 * t
            b.box((-0.75, yy - 0.12, zz - 0.12), (0.75, yy + 0.12, zz + 0.12), clair, collide=False, name="Echelon")
        # plate-forme et garde-corps
        b.box((-4.6, Hp, -4.6), (4.6, Hp + 0.6, 4.6), col("bois_moyen"), studs="top", name="Plateforme")
        for yaw in FACES:
            with b.at((0, 0, 0), yaw=yaw):
                b.box((-4.6, Hp + 0.6, -4.6), (4.25, Hp + 2.2, -4.25), vr("bois_gris", rng, 0.04), name="Garde_corps")
        yr = Hp + 5.6
        for sx in (-1, 1):
            for sz in (-1, 1):
                b.box((sx * 4.1 - 0.3, Hp + 0.6, sz * 4.1 - 0.3), (sx * 4.1 + 0.3, yr, sz * 4.1 + 0.3), bois,
                      name="Poteau_toit")
        b.box((-4.5, yr - 0.6, -4.5), (4.5, yr, 4.5), bois, name="Plafond")
        # cloche d'alarme
        _cloche(b, 0, yr - 0.6, 0, r=0.9)
        # toit
        hr = H - yr
        if v == 2:
            yt = yr
            dh = hr / 5
            for i, w in enumerate((11.2, 9.0, 6.8, 4.6, 2.4)):
                b.box((-w / 2, yt, -w / 2), (w / 2, yt + dh, w / 2), col(("tuile", "tuile_fonce")[i % 2]),
                      studs="top", name="Toit")
                yt += dh
        else:
            yt = _pyramide(b, 0, yr, 0, 11.2, 11.2, hr, "tuile_brune" if v == 0 else "ardoise", ep=0.5, studs=True,
                           name="Toit")
        # drapeau uni
        hf = 3.0
        b.cyl((0, yt + hf / 2 - 0.3, 0), 0.15, hf, bois, axis="y", collide=False, name="Hampe")
        coul = ("drapeau_rouge", "drapeau_vert", "drapeau_bleu")[v]
        b.box((0.15, yt + hf - 2.2, -0.07), (2.8, yt + hf - 0.6, 0.07), col(coul), collide=False, shadow=False,
              name="Drapeau")
    return {"emprise": (10.0, 10.0), "hauteur": round(yt + hf - 0.3, 1)}


# ---------------------------------------------------------------------------
# 8) Mât de fête
# ---------------------------------------------------------------------------

def mat_fete(b, variant=0, hauteur=40):
    """Mât de fête (Maibaum) : socle de pierre à jardinières, mât à bandes alternées (rouge et blanc v0, vert et
    blanc v1, bleu et blanc v2), trois paires de bras portant des plaques unies (ni texte ni symbole), couronne
    de feuillage à rubans, cime de sapin et petit drapeau uni."""
    v = variant % 3
    H = float(hauteur)
    bande = ("drapeau_rouge", "drapeau_vert", "drapeau_bleu")[v]
    with b.group("MatFete"):
        b.box((-1.6, 0, -1.6), (1.6, 1.2, 1.6), col("pierre_maison"), name="Socle")
        b.box((-1.8, 1.2, -1.8), (1.8, 1.5, 1.8), col("pierre_maison_claire"), studs="top", name="Socle")
        for s, fl in ((-1, "fleur_rouge"), (1, "fleur_jaune")):
            za, zb = sorted((s * 0.75, s * 1.7))
            b.box((-1.7, 1.5, za), (1.7, 2.2, zb), col("bois"), name="Jardiniere")
            b.box((-1.5, 2.2, za + 0.1), (1.5, 2.7, zb - 0.1), col(fl), collide=False, name="Fleurs")
        y_top = H - 3.5
        n = 11
        hseg = (y_top - 1.5) / n
        for k in range(n):
            ya = 1.5 + k * hseg
            b.cyl((0, ya + hseg / 2, 0), 0.45, hseg, col(bande if k % 2 else "drapeau_blanc"), axis="y", name="Mat")
        # bras et plaques unies
        plaques = ("toile_rouge", "toile_bleue", "toile_jaune", "toile_verte", "toile_creme", "drapeau_rouge")
        for i, yb in enumerate((y_top * 0.42, y_top * 0.58, y_top * 0.74)):
            with b.at((0, 0, 0), yaw=90 * (i % 2)):
                b.box((-3.0, yb, -0.15), (3.0, yb + 0.3, 0.15), col("bois"), collide=False, name="Bras")
                for s in (-1, 1):
                    xp = s * 2.4
                    coul = col(plaques[(2 * i + (s > 0)) % len(plaques)])
                    if (i + (s > 0)) % 2:
                        b.cyl((xp, yb - 0.75, 0), 0.75, 0.15, coul, axis="z", collide=False, name="Plaque")
                    else:
                        b.box((xp - 0.7, yb - 1.4, -0.08), (xp + 0.7, yb, 0.08), coul, collide=False,
                              name="Plaque")
        # couronne et rubans
        yw = y_top - 2.0
        for k in range(5):
            phi = 2 * math.pi * k / 5
            b.boxc((1.5 * math.cos(phi), yw, 1.5 * math.sin(phi)), (1.95, 0.9, 0.7),
                   col("feuille" if k % 2 else "feuille_fonce"), yaw=90 - math.degrees(phi), collide=False,
                   name="Couronne")
        for k, coul in enumerate(("drapeau_rouge", "drapeau_blanc", bande)):
            phi = 2 * math.pi * (k + 0.5) / 3
            x, z = 1.6 * math.cos(phi), 1.6 * math.sin(phi)
            b.box((x - 0.15, yw - 3.4, z - 0.06), (x + 0.15, yw - 0.45, z + 0.06), col(coul), collide=False,
                  shadow=False, name="Ruban")
        # cime de sapin et drapeau
        b.cyl((0, y_top + 0.7, 0), 1.0, 1.4, col("feuille_fonce"), axis="y", collide=False, name="Cime")
        b.cyl((0, y_top + 1.9, 0), 0.55, 1.0, col("feuille"), axis="y", collide=False, name="Cime")
        b.cyl((0, y_top + 2.4, 0), 0.1, 2.2, col("bois"), axis="y", collide=False, shadow=False, name="Hampe")
        b.box((0.1, H - 1.5, -0.06), (1.9, H - 0.4, 0.06), col(bande), collide=False, shadow=False, name="Drapeau")
    return {"emprise": (6.0, 4.0), "hauteur": H}
