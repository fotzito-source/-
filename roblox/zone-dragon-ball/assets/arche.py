"""Grands repères de la zone 4 (style « stud ») : arche de roche finale, pont de roche naturel des terres de
combat, bancs de nuages dorés et vaisseau rond sur pattes.

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h, "pieces": n}) :
- arche_finale(passage=104, largeur=400, profondeur=34, hauteur=96) : arche de roche géante qui ferme toute la
    largeur de la zone et sous laquelle le couloir sort vers la zone suivante. ORIGINE : centre de l'entrée du
    passage, au sol. Exception à « l'avant regarde -Z » : sa façade (z = 0 local) regarde +Z, vers les joueurs
    qui arrivent ; la masse occupe z ∈ [-profondeur, 0]. Strates horizontales de sable ocre, bandes violettes et
    filets roses en saillie, couronne d'herbe sarcelle débordante à coulures, arbres « boules » et buissons sur
    le dessus, contreforts et baies en retrait, deux cascades dans des fentes des jambes (vasques au pied), deux
    pitons géants (110-130) qui l'encadrent, masses extérieures en deux gradins (arrière haut, avant bas) qui
    rejoignent les falaises latérales. ≤ 1 500 pièces (repli de densité si un tirage déborde).
    v0 arche ronde ; v1 arche irrégulière à fenêtre dans une jambe ; v2 arche et petite arche secondaire au pied
    d'un piton.
- pont_rocheux(portee=100, hauteur=36, epaisseur=12, largeur_pile=30) : pont naturel au-dessus du couloir.
    Origine au centre du pont, au sol, sur l'axe du couloir ; symétrique en X, profondeur ≈ 20 (z ∈ [-10, 10]).
    Deux piles-mesas (strates violettes, filets roses en saillie, dessus d'herbe verte) à |x| ∈ [portee/2,
    portee/2 + largeur_pile] et un tablier dont le dessous reste ≥ hauteur - 2 au-dessus de |x| < 46. ≤ 350.
    v0 arc régulier ; v1 dissymétrique (pile gauche plus haute) ; v2 tablier mince à lianes, pile droite fendue.
- nuages_dores(largeur=50, profondeur=26, hauteur=24) : banc de nuages dorés posé sur sa base (y = 0) ;
    coussin de galettes, rangées de boules or et or clair, couronnes crème, dessous ombre et orange. ≤ 70 pièces.
    v0 banc long et bas ; v1 banc en tour ; v2 banc à deux lobes.
- vaisseau_rond(rayon=13) : vaisseau générique en lentille blanche à bande lavande (ou turquoise), coupole sur
    le dessus, trois hublots à l'AVANT seulement (-Z), trois ou quatre pattes inclinées à semelles studdées,
    rampe d'accès depuis une trappe avant, petite antenne. Emprise ≈ (2r + 6)², hauteur ≈ r + 11. ≤ 220.
    v0 lavande, 4 pattes ; v1 lavande, 3 pattes ; v2 turquoise, ailerons ; v3 turquoise, 3 pattes, ailerons.

Couloir élargi (demande du client) : couloir |x| < 45 (90 studs), trottoirs jusqu'à |x| = 55. Rien de
collidable dans |x| < 45 entre y = 0,05 et 12 ; rien du tout au-dessus de |x| < 46 sous y = 30. Tout ce qui
enjambe le couloir (arche, pont) a ses appuis à |x| ≥ 46 et son dessous à y ≥ 34 au-dessus de |x| < 46 :
l'arche impose passage ≥ 96 (104 par défaut), le pont portee ≥ 92 (100 par défaut). Les valeurs plus petites
(ancien couloir de 64) sont relevées à ces minimums.

Règles tenues : pas de faces coplanaires de couleurs différentes (limites de strates sur les demi-studs,
dessus d'herbe sur les studs pairs, arêtes de l'arche sur une grille de 2 en x, pitons sur les quarts de stud,
saillies de 0,4 et débords de 0,6) ; rien ne flotte (coulures accrochées aux chapeaux, nuages posés sur leur
base, pattes du vaisseau jusqu'aux semelles) ; détails fins sans collision ni ombre. Propriété intellectuelle :
formes génériques seulement, aucun texte, aucun dragon, aucune sphère orange, aucune étoile ; le vaisseau n'a
pas d'anneau de hublots tout autour (trois hublots à l'avant), il est en lentille sur pattes, blanc et lavande.
"""

from __future__ import annotations

import math

import numpy as np

from kit import mix, shade
from palette import c, vary

# ---------------------------------------------------------------------------
# Couloir (élargi) et constantes
# ---------------------------------------------------------------------------
X_COULOIR = 45.0      # rien de collidable en deçà, entre y = 0,05 et 12
X_CIEL = 46.0         # rien du tout en deçà sous y = 30
Y_ENJAMBE = 34.0      # dessous minimal de ce qui enjambe le couloir
PASSAGE_MIN = 96.0    # sortie sous l'arche : au moins 96 studs de large
PORTEE_MIN = 92.0     # pont : au moins 92 studs entre les piles

DETAIL = dict(collide=False, shadow=False)
YV = np.array([0.0, 1.0, 0.0])

TONS = {
    "SF": "falaise_sable_fonce", "S": "falaise_sable", "SC": "falaise_sable_claire",
    "P": "mesa_rose", "V": "mesa_violet", "VC": "mesa_violet_clair", "VF": "mesa_violet_fonce", "N": "mesa_nuit",
}

# Strates (épaisseur, ton). Elles commencent sur un demi-stud et ont des épaisseurs entières : leurs limites
# tombent toutes sur des demi-studs, alors que les dessus d'herbe sont sur des studs pairs (jamais confondus).
# Arche : sable ocre dominant, bandes violettes, filets roses « P » qui avancent de 0,4 devant la paroi.
MOTIF_ARCHE = [(6, "SF"), (7, "S"), (2, "PR"), (8, "SC"), (5, "S"), (4, "V"), (2, "PR"), (8, "SC"), (6, "S"),
               (5, "VC"), (2, "PR"), (8, "S"), (5, "SC"), (5, "V"), (2, "PR"), (7, "SC"), (5, "S"), (5, "VC"),
               (2, "PR"), (7, "V"), (6, "SC"), (2, "PR"), (8, "S")]
# Pitons géants : même famille, bancs plus épais (limites sur les quarts de stud : départ à -0,75)
MOTIF_PITON = [(7, "SF"), (8, "S"), (2, "PR"), (9, "SC"), (6, "V"), (2, "PR"), (9, "SC"), (8, "S"), (2, "PR"),
               (8, "VC"), (8, "SC"), (6, "V"), (2, "PR"), (9, "S"), (8, "SC"), (2, "PR"), (7, "VC"), (8, "S"),
               (2, "PR"), (9, "SC"), (8, "V")]
# Pont de roche (terres de combat) : flancs violets de mesa, pied nuit, filets roses
MOTIF_PONT = [(3, "N"), (6, "VF"), (6, "V"), (2, "P"), (7, "VC"), (6, "V"), (5, "VF"), (2, "P"), (6, "VC"),
              (5, "V"), (2, "P"), (6, "VC"), (6, "V"), (6, "VF")]


ROSE_VIF = mix(c("mesa_rose"), c("rose_ciel"), 0.4)      # filets roses de l'arche : rappel du ciel magenta
SAILLANTS = ("P", "PR")
CREME_CHAUD = mix(c("nuage_creme"), c("nuage_or_clair"), 0.35)   # couronnes des nuages (crème doré)
# dessous des nuages : ombre dorée (jamais de boules orange, propriété intellectuelle)
OMBRE_DOREE = mix(c("nuage_ombre"), c("nuage_or"), 0.45)


def _ton(code: str):
    return ROSE_VIF if code == "PR" else c(TONS[code])


def _strates(motif, y0: float, y_max: float) -> list:
    """Strates horizontales (y0, y1, ton) de y0 jusqu'au-delà de y_max."""
    out, y, i = [], float(y0), 0
    while y < y_max:
        e, t = motif[i % len(motif)]
        out.append((y, y + e, t))
        y, i = y + e, i + 1
    return out


def _repere(axe) -> np.ndarray:
    """Matrice de rotation dont la première colonne (axe d'un cylindre Roblox) est `axe`."""
    x = np.asarray(axe, float)
    x = x / np.linalg.norm(x)
    up = np.array([0.0, 1.0, 0.0]) if abs(x[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    z = np.cross(x, up)
    z /= np.linalg.norm(z)
    y = np.cross(z, x)
    return np.column_stack([x, y, z])


def _poutre(b, p0, p1, w, col, **kw):
    """Bloc de section w × w dont l'axe Y local va de p0 à p1 (troncs fins)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = float(np.linalg.norm(d))
    u = d / L
    ref = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    x = np.cross(u, ref)
    x /= np.linalg.norm(x)
    z = np.cross(x, u)
    return b.part("block", (w, L, w), (p0 + p1) / 2, np.column_stack([x, u, z]), col, **kw)


def _bornes_parts(b, n0):
    """Boîte englobante (repère courant) des pièces ajoutées depuis n0."""
    o = b.to_world((0, 0, 0))
    M = np.vstack([b.to_world(e) - o for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))])
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for p in b.parts[n0:]:
        R = np.asarray(p.rot, float).reshape(3, 3)
        half = np.abs(R) @ (np.asarray(p.size, float) / 2)
        pl = (np.asarray(p.pos, float) - o) @ M.T
        hl = np.abs(M) @ half
        lo, hi = np.minimum(lo, pl - hl), np.maximum(hi, pl + hl)
    return lo, hi


def _infos(b, n0) -> dict:
    lo, hi = _bornes_parts(b, n0)
    return {"emprise": (round(float(hi[0] - lo[0]), 1), round(float(hi[2] - lo[2]), 1)),
            "hauteur": round(float(hi[1]), 1), "pieces": len(b.parts) - n0}


# ---------------------------------------------------------------------------
# Masse rocheuse en colonnes et en strates (arche, pont)
# ---------------------------------------------------------------------------

def _col(x0, x1, iv, zb, zf, lisse=False, sans_saillie=False, grossier=False) -> dict:
    """Colonne de roche [x0, x1] : intervalles pleins iv = [(y0, y1, coiffe)], profondeur [zb, zf] nominale.

    `coiffe` : le dessus porte un chapeau d'herbe (la pierre s'arrête sous lui). `lisse` : paroi sans retrait ni
    saillie (fente de cascade). `grossier` : masses plus larges (parties lointaines)."""
    return dict(x0=float(x0), x1=float(x1), iv=list(iv), zb=float(zb), zf=float(zf), lisse=lisse,
                sans_saillie=sans_saillie or lisse, grossier=grossier)


def _plein(col, y0, y1) -> bool:
    """La colonne est-elle pleine entre y0 et y1 (chapeau compris) ?"""
    return any(a <= y0 + 1e-6 and t >= y1 - 1e-6 for (a, t, _) in col["iv"])


def _vide(col, y0, y1) -> bool:
    """La colonne est-elle entièrement vide entre y0 et y1 (chapeau compris) ?"""
    return not any(a < y1 - 1e-6 and t > y0 + 1e-6 for (a, t, _) in col["iv"])


def _masse(b, cols, strates, rng, *, cap=1.2, herbe=("herbe_alien", "herbe_alien_claire"), deux_faces=False,
           larg=(10, 14, 18, 22), larg_gros=(20, 26, 32), bande=12.0,
           retraits=(0.0, 0.5, 1.0, 2.0, 3.0, 4.0), saillie=0.4, debord=0.6, debord_arriere=None,
           ouvert=(True, True), coulures=0.5, coulure_max=4.0, fissures=0.0, name="Roche") -> list:
    """Masse rocheuse en strates horizontales continues, découpée en colonnes (cols triées en x et jointives).

    Chaque strate devient une rangée de blocs : les colonnes voisines identiques sont fusionnées, puis la rangée
    est recoupée en « masses » (largeurs `larg`, bandes de `bande` studs de haut, souvent prolongées d'une bande
    à l'autre) qui reculent chacune de 0 à 3 studs (relief). Les filets roses (« P ») restent continus et avancent
    de `saillie`. Chaque dessus coiffé reçoit un chapeau d'herbe qui déborde de `debord` (devant, derrière si
    `debord_arriere`, et aux bouts exposés ; `ouvert` dit si les deux bouts de la masse sont à l'air libre),
    avec quelques coulures sans collision dessous. Renvoie les dessus herbeux [(x0, x1, y, zb, zf)]."""
    debord_arriere = debord if debord_arriere is None else debord_arriere
    bornes = sorted({s[0] for s in strates} | {s[1] for s in strates})
    saillants = [(s[0], s[1]) for s in strates if s[2] in SAILLANTS]
    hauts_saillants = sorted(h for (_, h) in saillants)
    n = len(cols)
    # 1. intervalles de pierre : sous le chapeau, accrochés aux limites de strates (pas de tranche < 0,8)
    for col in cols:
        pierre = []
        for (y0, y1, coiffe) in col["iv"]:
            s = y1 - cap if coiffe else y1
            if coiffe:
                dessous = [v for v in bornes if v <= s + 1e-6]
                if dessous and s - dessous[-1] < 0.8 and dessous[-1] > y0 + 0.5:
                    s = dessous[-1]
                if s < y0 + 0.05:
                    s = y0
            dessus = [v for v in bornes if v >= y0 - 1e-6]
            if dessus and 1e-6 < dessus[0] - y0 < 0.8 and dessus[0] < s - 0.5:
                y0 = dessus[0]
            pierre.append((y0, s, y1 if coiffe else None))
        col["pierre"] = pierre

    X0, X1 = cols[0]["x0"], cols[-1]["x1"]
    masses: dict = {}

    def decoupe(k, gros):
        cle = (k, gros)
        if cle not in masses:
            prec = masses.get((k - 1, gros))
            if prec is not None and rng.random() < 0.5:
                xs, fis = list(prec[0]), list(prec[3])   # même découpe que la bande du dessous : masses hautes
            else:
                xs = [X0]
                choix = larg_gros if gros else larg
                while xs[-1] < X1 - 1e-6:
                    xs.append(xs[-1] + float(rng.choice(choix)))
                xs[-1] = X1
                # fissures : fentes de 2 studs, plus profondes, au milieu des masses larges
                nx, fis = [xs[0]], []
                for a0, a1 in zip(xs[:-1], xs[1:]):
                    if fissures > 0 and a1 - a0 >= 10 and rng.random() < fissures:
                        xf = a0 + 2.0 * int(rng.integers(2, int((a1 - a0) / 2) - 2))
                        nx += [xf, xf + 2.0, a1]
                        fis += [False, True, False]
                    else:
                        nx.append(a1)
                        fis.append(False)
                xs = nx
            m = len(xs) - 1
            pool = retraits[:3] if k == 0 else retraits     # la bande du pied avance (talus)
            prof = max(retraits) + 1.5
            rf = np.where(fis, prof, rng.choice(pool, size=m))
            rb = np.where(fis, prof, rng.choice(pool, size=m))
            masses[cle] = (np.array(xs), rf, rb, fis)
        return masses[cle]

    def emettre(xa, xb, lo, hi, zb, zf, col):
        b.box((xa, lo, zb), (xb, hi, zf), col, studs="top", name=name)

    # 2. strates
    for (y0, y1, ton) in strates:
        k = int((0.5 * (y0 + y1) - strates[0][0]) // bande)
        runs = []          # [x0, x1, cle, i0, i1]
        ouverts: dict = {}
        for i, col in enumerate(cols):
            cles = set()
            for (a, s, _) in col["pierre"]:
                lo, hi = max(y0, a), min(y1, s)
                if hi - lo >= 0.1:
                    cles.add((lo, hi, col["zb"], col["zf"], col["lisse"], col["sans_saillie"], col["grossier"]))
            for cle in list(ouverts):
                r = ouverts[cle]
                if cle in cles and abs(r[1] - col["x0"]) < 1e-6:
                    r[1] = col["x1"]
                    r[4] = i
                    cles.discard(cle)
                else:
                    runs.append(ouverts.pop(cle))
            for cle in cles:
                ouverts[cle] = [col["x0"], col["x1"], cle, i, i]
        runs.extend(ouverts.values())

        for (xa, xb, cle, i0, i1) in runs:
            lo, hi, zb, zf, lisse, sans_s, gros = cle
            if ton in SAILLANTS and not sans_s:
                ga = saillie if ((i0 == 0 and ouvert[0]) or (i0 > 0 and _vide(cols[i0 - 1], lo, hi))) else 0.0
                gb = saillie if ((i1 == n - 1 and ouvert[1]) or (i1 < n - 1 and _vide(cols[i1 + 1], lo, hi))) else 0.0
                if lo < Y_ENJAMBE:            # jamais de saillie dans le gabarit du couloir (|x| < 46 sous 34)
                    if ga and xa - ga < X_CIEL and xa > -X_CIEL:
                        ga = 0.0
                    if gb and xb < X_CIEL and xb + gb > -X_CIEL:
                        gb = 0.0
                emettre(xa - ga, xb + gb, lo, hi, zb - (saillie if deux_faces else 0.0), zf + saillie,
                        vary(_ton(ton), rng, 0.03))
                continue
            if lisse:
                emettre(xa, xb, lo, hi, zb, zf, vary(_ton(ton), rng, 0.03))
                continue
            xs, rf, rbk, _ = decoupe(k, gros)
            coupes = [float(x) for x in xs if xa + 2 <= x <= xb - 2]
            bords = [xa] + coupes + [xb]
            morceaux = []
            for u0, u1 in zip(bords[:-1], bords[1:]):
                j = int(np.searchsorted(xs, (u0 + u1) / 2) - 1)
                j = max(0, min(j, len(rf) - 1))
                f = zf - float(rf[j])
                bk = zb + (float(rbk[j]) if deux_faces else 0.0)
                if morceaux and morceaux[-1][2] == f and morceaux[-1][3] == bk:
                    morceaux[-1][1] = u1
                else:
                    morceaux.append([u0, u1, f, bk])
            for u0, u1, f, bk in morceaux:
                emettre(u0, u1, lo, hi, bk, f, vary(_ton(ton), rng, 0.03))

    # 3. chapeaux d'herbe (une pièce par suite de colonnes de même dessus) et coulures
    dessus = []
    ouverts = {}
    for i, col in enumerate(cols):
        cles = {(s, t, col["zb"], col["zf"], col["lisse"]) for (a, s, t) in col["pierre"] if t is not None}
        for cle in list(ouverts):
            r = ouverts[cle]
            if cle in cles and abs(r[1] - col["x0"]) < 1e-6:
                r[1], r[3] = col["x1"], i
                cles.discard(cle)
            else:
                dessus.append(ouverts.pop(cle))
        for cle in cles:
            ouverts[cle] = [col["x0"], col["x1"], cle, i, i]
    dessus.extend(ouverts.values())
    out = []
    for (xa, xb, (s, t, zb, zf, lisse), i0, i1) in dessus:
        ga = debord if ((i0 == 0 and ouvert[0]) or (i0 > 0 and not _plein(cols[i0 - 1], s, t))) else 0.0
        gb = debord if ((i1 == n - 1 and ouvert[1]) or (i1 < n - 1 and not _plein(cols[i1 + 1], s, t))) else 0.0
        b.box((xa - ga, s, zb - debord_arriere), (xb + gb, t, zf + debord), vary(herbe[0], rng, 0.025), studs="top",
              name="Herbe")
        out.append((xa, xb, t, zb, zf))
        if lisse or t - s < 0.5 or s < 3.0:
            continue                          # pas de coulure sur un sol ni dans une fente de cascade
        if any(y0s < s + 1e-6 and y1s > s - 0.5 for (y0s, y1s) in saillants):
            continue                          # chapeau posé sur un filet saillant : pas de coulure
        # coulures : sous le débord, devant la roche, au-dessus du filet saillant le plus proche
        plancher = max([h + 0.3 for h in hauts_saillants if h <= s - 0.5] + [s - coulure_max])
        faces = ((zf + 0.15, zf + 0.5),) + (((zb - 0.5, zb - 0.15),) if (deux_faces and debord_arriere > 0.5) else ())
        for (za, zb2) in faces:
            u = xa + float(rng.uniform(0.5, 3.0))
            while u < xb - 2.0:
                w = float(rng.choice((1.2, 1.6, 2.0, 2.4)))
                if rng.random() < coulures:
                    L = float(rng.uniform(1.2, coulure_max))
                    yb = max(s - L, plancher)
                    if s - yb >= 0.8:
                        b.box((u, yb, za), (min(u + w, xb - 0.3), s, zb2),
                              vary(herbe[int(rng.random() < 0.3)], rng, 0.03), name="Coulure", **DETAIL)
                u += w + float(rng.choice((2.0, 4.0, 6.0, 9.0)))
    return out


# ---------------------------------------------------------------------------
# Végétation posée sur la roche
# ---------------------------------------------------------------------------

def _arbre_boule(b, x, y, z, H, rng, Rc=None):
    """Arbre « boule » posé en (x, y, z) (y = dessus de l'herbe) : tronc pâle très fin coudé, couronne de boules
    (foncée dessous, claire dessus). 6 pièces, sans collision sauf le tronc."""
    Rc = Rc if Rc is not None else max(2.2, min(5.0, 0.26 * H))
    w = 0.45 + 0.03 * H
    yc = y + H - Rc
    p0 = np.array([x, y - 0.3, z])
    p1 = np.array([x + float(rng.uniform(-0.6, 0.6)), y + (yc - y) * 0.5, z + float(rng.uniform(-0.6, 0.6))])
    p2 = np.array([x + float(rng.uniform(-0.5, 0.5)), yc - 0.3 * Rc, z + float(rng.uniform(-0.5, 0.5))])
    b.boxc((x, y + 0.25, z), (w + 0.8, 0.5, w + 0.8), vary("tronc_alien_fonce", rng, 0.04),
           yaw=float(rng.uniform(0, 90)), name="Pied", **DETAIL)
    _poutre(b, p0, p1 + (p1 - p0) * 0.03, w, vary("tronc_alien", rng, 0.03), name="Tronc")
    _poutre(b, p1, p2, w * 0.85, vary("tronc_alien_fonce", rng, 0.03), name="Tronc")
    ctr = p2 + YV * 0.3 * Rc
    a = math.radians(float(rng.uniform(0, 360)))
    u = np.array([math.cos(a), 0.0, math.sin(a)])
    kw = dict(collide=False, name="Couronne")
    b.ball(ctr - YV * 0.3 * Rc + u * 0.12 * Rc, 0.82 * Rc, vary("boule_alien_fonce", rng, 0.04), **kw)
    b.ball(ctr, Rc, vary("boule_alien", rng, 0.04), **kw)
    b.ball(ctr + YV * 0.36 * Rc - u * 0.2 * Rc, 0.64 * Rc, vary("boule_alien_claire", rng, 0.04), **kw)


def _buisson(b, x, y, z, rng, alien=True, taille=1.0):
    """Buisson de boules (sarcelle) ou de blocs studdés (vert), posé sur l'herbe en (x, y, z). 2 à 3 pièces."""
    s = taille
    if alien:
        b.ball((x, y + 0.5 * s, z), 1.35 * s, vary("boule_alien", rng, 0.05), name="Buisson", **DETAIL)
        b.ball((x + 1.0 * s, y + 0.35 * s, z + 0.5 * s), 0.95 * s, vary("buisson_alien", rng, 0.05), name="Buisson",
               **DETAIL)
        b.ball((x - 0.9 * s, y + 0.3 * s, z - 0.4 * s), 0.8 * s, vary("boule_alien_claire", rng, 0.05), name="Buisson",
               **DETAIL)
    else:
        yaw = float(rng.uniform(0, 90))
        b.boxc((x, y + 0.7 * s, z), (2.6 * s, 1.4 * s, 2.2 * s), vary("buisson", rng, 0.04), yaw=yaw, studs="top",
               name="Buisson", **DETAIL)
        b.boxc((x + 0.2 * s, y + 1.65 * s, z - 0.1 * s), (1.5 * s, 0.5 * s, 1.3 * s), vary("feuillage", rng, 0.04),
               yaw=yaw + 30, studs="top", name="Buisson", **DETAIL)


def _dessus_a(dessus, x, marge=2.0, z=None):
    """Dessus herbeux (x0, x1, y, zb, zf) qui contient x (avec une marge) et z s'il est donné, le plus haut."""
    ok = [d for d in dessus if d[0] + marge <= x <= d[1] - marge and (z is None or d[3] + 1 <= z <= d[4] - 1)]
    return max(ok, key=lambda d: d[2]) if ok else None


# ---------------------------------------------------------------------------
# 1. Arche finale
# ---------------------------------------------------------------------------

def _interp(pts, x):
    xs, ys = zip(*pts)
    return float(np.interp(x, xs, ys))


def _piton(b, xc, zc, H, rng, demi=8.0, sens=1, herbe="herbe_alien"):
    """Piton géant : jupe d'éboulis au pied, tronçons empilés qui s'affinent et penchent un peu vers `sens`
    (x), bosses en saillie sur la face avant et le côté extérieur, évasement érodé au sommet, chapeau d'herbe à
    coulures. Strates sur les quarts de stud (départ à -0,75) et arêtes sur les quarts de stud (xc, zc ≡ 0,25 ;
    demi-côtés et décalages multiples de 0,5) : jamais de face confondue avec la masse de l'arche.
    Renvoie le dessus (x, y, z)."""
    strates = _strates(MOTIF_PITON, -0.75, H + 2)
    cap = 1.2
    Hs = H - cap
    tr = [(0.26, demi, 0.0, 0.0), (0.48, demi - 0.5, sens * 0.5, -0.5), (0.68, demi - 1.0, sens * 1.0, -1.0),
          (0.85, demi - 1.5, sens * 1.5, -1.0), (1.00, demi - 2.0, sens * float(rng.choice((0.5, 1.0))), -1.5)]
    bornes = [s_[0] for s_ in strates]

    def bandes(x0, x1, z0, z1, y0, y1, nom="Piton", plus=0.0):
        for (s0, s1, t) in strates:
            lo, hi = max(s0, y0), min(s1, y1)
            if hi - lo < 0.1:
                continue
            g = (0.4 if t in SAILLANTS else 0.0) + plus
            b.box((x0 - g, lo, z0 - g), (x1 + g, hi, min(z1 + g, 0.0)), vary(_ton(t), rng, 0.03), studs="top",
                  name=nom)

    # jupe d'éboulis au pied (côtés et arrière ; l'avant reste dans l'alignement de la base)
    yj = min(v for v in bornes if v >= 4.0)
    b.box((xc - demi - 1.5, -0.6, zc - demi - 1.5), (xc + demi + 1.5, yj - 0.6, zc + demi - 0.5),
          vary("falaise_sable_fonce", rng, 0.03), studs="top", name="Jupe")
    y = -0.75
    sommet = None
    for i, (fh, d, dx, dz) in enumerate(tr):
        if i == len(tr) - 1:
            y1 = Hs - 3.0                     # l'évasement du sommet prend les 3 derniers studs
        else:
            y1 = max(min(bornes, key=lambda v: abs(v - fh * Hs)), y + 6)
        x0, x1 = xc + dx - d, xc + dx + d
        z0, z1 = zc + dz - d, zc + dz + d
        bandes(x0, x1, z0, z1, y, y1)
        # bosses en saillie sur la face avant et sur le côté extérieur (masses rocheuses)
        if y1 - y > 12 and i < 4:
            for face in (0, 1):
                hb = float(rng.choice((6.0, 8.0, 10.0, 12.0)))
                yb = math.floor(y + float(rng.uniform(1, max(1.5, y1 - y - hb - 1)))) + 0.1
                wb = float(rng.choice((4.0, 5.0, 6.0)))
                ub = round(float(rng.uniform(0.5, 2 * d - wb - 0.5)) * 2) / 2
                col = vary(_ton(("SC", "S", "VC", "SF")[(i + face) % 4]), rng, 0.04)
                if face == 0:
                    b.box((x0 + ub, yb, z1 - 0.5), (x0 + ub + wb, yb + hb, min(z1 + 0.6, -0.15)), col, studs="top",
                          name="Bosse")
                else:
                    xe = x1 if sens > 0 else x0
                    xa, xb = sorted((xe - sens * 0.5, xe + sens * 0.9))
                    b.box((xa, yb, z0 + ub), (xb, yb + hb, z0 + ub + wb), col, studs="top", name="Bosse")
        y = y1
        sommet = (x0, x1, z0, z1)
    x0, x1, z0, z1 = sommet
    # évasement du sommet (piton érodé) puis chapeau d'herbe
    b.box((x0 - 0.5, Hs - 3.0, z0 - 0.5), (x1 + 0.5, Hs, z1 + 0.5), vary(_ton("SC"), rng, 0.03), studs="top",
          name="Piton")
    b.box((x0 - 1.1, Hs, z0 - 1.1), (x1 + 1.1, H, z1 + 1.1), vary(herbe, rng, 0.025), studs="top", name="Herbe")
    for (za, zb2) in ((z1 + 0.6, z1 + 0.95), (z0 - 0.95, z0 - 0.6)):
        u = x0 + float(rng.uniform(0.0, 1.5))
        while u < x1 - 1.5:
            w = float(rng.choice((1.2, 1.6, 2.0)))
            if rng.random() < 0.6:
                L = float(rng.uniform(1.5, 3.5))
                b.box((u, Hs - L, za), (u + w, Hs, zb2), vary("herbe_alien", rng, 0.03), name="Coulure", **DETAIL)
            u += w + float(rng.choice((1.5, 3.0, 4.5)))
    return ((x0 + x1) / 2, H, (z0 + z1) / 2)


def _cascade_fente(b, x0, x1, y_haut, z_mur, rng):
    """Cascade à deux chutes dans une fente de la jambe : ruisseau et lèvre sur le dessus, première nappe devant
    la paroi du fond (z_mur), rebord rocheux à mi-hauteur où l'eau rebondit (écume), seconde nappe plus large
    devant le rebord, filets clairs, écume et brume au pied, vasque entre z_mur et 0 (fond de pierre, bord de
    rochers). Rien ne dépasse z = 0."""
    eau = dict(collide=False, shadow=False)
    xm = (x0 + x1) / 2
    w = x1 - x0
    yl = math.floor(0.44 * y_haut) + 0.3          # dessus du rebord (hors des limites de strates et des dessus)
    zr = z_mur + 2.6                              # avant du rebord
    with b.group("Cascade"):
        # ruisseau sur le dessus et lèvre qui s'enroule devant le chapeau d'herbe
        b.box((xm - w * 0.3, y_haut, z_mur - 14.0), (xm + w * 0.3, y_haut + 0.4, z_mur + 0.3), c("eau"),
              transparency=0.1, name="Eau", **eau)
        b.box((xm - w * 0.34, y_haut - 1.4, z_mur + 0.65), (xm + w * 0.34, y_haut + 0.55, z_mur + 1.35),
              c("eau_claire"), name="Eau", **eau)
        # première chute (plus étroite) jusqu'au rebord
        b.box((x0 + 2.2, yl - 0.5, z_mur + 0.15), (x1 - 2.2, y_haut - 0.3, z_mur + 0.55), c("eau"), transparency=0.08,
              name="Eau", **eau)
        # rebord rocheux, écume qui rebondit, lèvre claire
        b.box((x0, yl - 2.5, z_mur), (x1, yl, zr), vary("falaise_sable_fonce", rng, 0.03), studs="top", name="Rebord")
        b.box((x0 + 1.4, yl - 0.1, z_mur + 0.3), (x1 - 1.4, yl + 1.0, zr - 0.4), c("ecume"), name="Ecume", **eau)
        b.box((x0 + 1.0, yl - 1.6, zr + 0.05), (x1 - 1.0, yl + 0.45, zr + 0.6), c("eau_claire"), name="Eau", **eau)
        # seconde chute (plus large) devant le rebord, élargie en bas
        b.box((x0 + 0.8, 0.1, zr + 0.1), (x1 - 0.8, yl - 1.2, zr + 0.5), c("eau"), transparency=0.08, name="Eau", **eau)
        b.box((x0 + 0.3, 0.2, zr + 0.25), (x1 - 0.3, yl * 0.35, zr + 0.65), shade(c("eau"), 0.94), transparency=0.1,
              name="Eau", **eau)
        # filets clairs (pixels de lumière qui descendent)
        for i, fx in enumerate((0.15, 0.4, 0.62, 0.85)):
            lw = (0.6, 0.9, 0.5, 0.8)[i]
            x = x0 + 2.4 + fx * (w - 4.8)
            y_lo = yl + (float(rng.uniform(0.1, 0.4)) * (y_haut - yl) if i % 2 else 0.9)
            b.box((x - lw / 2, y_lo, z_mur + 0.6), (x + lw / 2, y_haut - 1.0, z_mur + 0.75),
                  c("ecume") if i % 2 == 0 else c("eau_claire"), name="Filet", **eau)
        for i, fx in enumerate((0.08, 0.26, 0.47, 0.66, 0.9)):
            lw = (0.6, 1.0, 0.5, 0.9, 0.6)[i]
            x = x0 + 1.0 + fx * (w - 2.0)
            y_hi = yl - 1.4 - float(rng.uniform(0.0, 0.3)) * yl * (i % 2)
            y_lo = float(rng.uniform(0.25, 0.5)) * yl if i % 2 else 0.4
            b.box((x - lw / 2, y_lo, zr + 0.7), (x + lw / 2, y_hi, zr + 0.85),
                  c("ecume") if i % 2 == 0 else c("eau_claire"), name="Filet", **eau)
        # vasque : fond de pierre, eau, ride, bord de rochers, écume, brume
        b.box((x0, -1.0, z_mur), (x1, -0.3, 0.0), vary("falaise_sable_fonce", rng, 0.03), studs="top", name="Vasque")
        b.box((x0, -0.3, z_mur), (x1, 0.15, -0.2), c("eau"), transparency=0.1, name="Vasque", **eau)
        b.box((x0 + 1.5, 0.15, -2.2), (x1 - 1.5, 0.3, -1.8), c("eau_claire"), name="Ride", **eau)
        for i, (fx, sx, sz) in enumerate(((0.06, 2.2, 1.6), (0.28, 1.8, 1.3), (0.5, 1.6, 1.2), (0.74, 2.0, 1.5),
                                          (0.94, 1.8, 1.4))):
            x = x0 + fx * w
            hy = float(rng.uniform(0.7, 1.2))
            b.boxc((x, hy / 2 - 0.2, -0.9), (sx, hy + 0.4, sz), vary(("falaise_sable", "falaise_sable_claire",
                                                                    "rocher_clair")[i % 3], rng, 0.05),
                   yaw=float(rng.uniform(-20, 20)), studs="top", name="Bord")
        for (x, y, z, sx, sy, sz, yw) in ((xm, 0.8, zr + 1.1, w * 0.75, 1.6, 1.4, 0),
                                          (xm - w * 0.32, 0.5, zr + 1.6, 2.2, 1.0, 1.4, 20),
                                          (xm + w * 0.3, 0.55, zr + 1.5, 2.4, 1.1, 1.3, -15),
                                          (xm + w * 0.05, 0.4, zr + 2.3, 2.0, 0.8, 1.2, 35)):
            b.boxc((x, y, z), (sx, sy, sz), c("ecume"), yaw=yw, name="Ecume", **eau)
        for (x, y, z, s_) in ((xm - w * 0.22, 2.6, zr + 1.5, 2.6), (xm + w * 0.26, 3.4, zr + 1.2, 2.2),
                              (xm, 1.8, zr + 2.2, 2.0), (xm + w * 0.1, yl + 1.6, z_mur + 1.6, 2.0)):
            b.boxc((x, y, z), (s_ * 1.3, s_, s_), c("blanc"), yaw=float(rng.uniform(0, 45)), transparency=0.45,
                   name="Brume", **eau)


# Profils du dessus (|x| → hauteur pour une arche de 96) : bosse au-dessus du passage, épaules, col des
# cascades, massif des pitons, puis masses extérieures (gradin arrière) qui descendent vers les falaises.
PROFILS = {
    0: [(0, 96), (14, 94), (28, 90), (40, 86), (50, 80), (58, 74), (67, 66), (78, 66), (84, 70), (100, 72),
        (110, 64), (124, 56), (140, 52), (156, 46), (172, 42), (188, 38), (200, 36)],
    1: [(0, 94), (10, 96), (26, 92), (38, 86), (50, 78), (58, 72), (67, 64), (78, 68), (84, 74), (100, 70),
        (112, 60), (126, 56), (142, 50), (158, 46), (176, 42), (190, 38), (200, 34)],
    2: [(0, 96), (16, 94), (30, 88), (42, 84), (50, 80), (58, 74), (67, 66), (78, 66), (84, 70), (100, 70),
        (112, 70), (124, 64), (140, 54), (156, 48), (172, 42), (188, 38), (200, 36)],
}
Z_GRADIN = -16.0            # séparation du gradin avant (bas) et du gradin arrière (haut)


def _plan(a, W):
    """Repères en x de l'arche, relatifs au demi-passage `a` (les profils sont écrits pour a = 52, W = 200) :
    fentes des cascades, centre des pitons (≡ 0,25 : arêtes sur les quarts de stud), début des masses en gradins,
    et u(|x|) → abscisse des profils."""
    def u(ax):
        if ax < a:
            return ax * 52.0 / a
        return 52.0 + (ax - a) * 148.0 / max(1.0, W - a)
    return dict(f0=a + 8.0, f1=a + 22.0, xp=a + 40.25, xm=max(124.0, a + 72.0), u=u)


def _front(ax, a, P):
    """Face avant nominale (z) selon |x| : linteau en avant, contreforts, fente de cascade en retrait, baies."""
    if ax < a:
        return -0.5            # linteau : il avance au-dessus des jambes
    if ax < P["f0"]:
        return -2.5
    if ax < P["f1"]:
        return -6.5
    if ax < P["xp"] - 8.25:
        return -2.5
    if ax < P["xp"] + 7.75:
        return -4.5            # derrière le piton, qui avance jusqu'à z = -0,25
    return -1.5


def _arche(b, v, a, W, D, H, rng, dens):
    fh = H / 96.0
    P = _plan(a, W)
    f0, f1, xp, xm, u_ = P["f0"], P["f1"], P["xp"], P["xm"], P["u"]
    zb = -D
    gx = 2.0                                     # grille des colonnes (studs)
    # -- intrados (dessous du passage), par marches de 4 studs ----------------------------------------------
    y_s = {-1: 22.0, 1: 22.0}
    y_c = 0.62 * H
    p = 2.4
    if v == 1:
        y_s = {-1: 26.0, 1: 18.0}
        y_c = 0.6 * H
        p = 1.8
    bosses = {k: float(rng.choice((-2.0, 0.0, 0.0, 2.0, 4.0))) for k in range(-40, 41)}

    def intrados(x0, x1):
        """Dessous de la colonne [x0, x1] au-dessus du passage (marche de 4 prise à son bord extérieur)."""
        ax = min(a, 4.0 * math.ceil(max(abs(x0), abs(x1)) / 4.0 - 1e-9))
        s = -1 if (x0 + x1) < 0 else 1
        t = min(1.0, ax / a)
        y = y_s[s] + (y_c - y_s[s]) * (1 - t ** p) ** (1 / p)
        if v == 1:
            y += bosses[int(math.floor((x0 + x1) / 2 / 8))]
        y = 2.0 * math.ceil(y / 2.0)
        if min(abs(x0), abs(x1)) < X_CIEL:
            y = max(y, Y_ENJAMBE + (2.0 if v == 1 else 0.0))
        return y

    # -- dessus : paliers de largeur irrégulière ------------------------------------------------------------
    paliers = []
    for s in (-1, 1):
        prof = [(px, py * fh) for px, py in PROFILS[v]]
        if s > 0:
            prof = [(px, py + (2 * fh if 84 <= px <= 100 else 0)) for px, py in prof]
        x = 0.0
        while x < W - 1e-6:
            w = float(rng.choice((4.0, 6.0, 6.0, 8.0, 10.0)))
            x1 = min(W, x + w)
            if W - x1 < 4:
                x1 = W
            for bord in (f0, f1, xm, a):
                if x < bord < x1:
                    x1 = bord
            h = _interp(prof, u_((x + x1) / 2)) + float(rng.choice((-2.0, 0.0, 0.0, 2.0)))
            paliers.append((s, x, x1, 2.0 * round(h / 2.0)))
            x = x1

    def dessus(xc):
        s = -1 if xc < 0 else 1
        for (ss, x0, x1, h) in paliers:
            if ss == s and x0 <= abs(xc) < x1:
                return h
        return 30.0

    y_fente = 2.0 * round((_interp(PROFILS[v], u_(a + 15.0)) * fh - 4.0) / 2.0)
    fenetre = (-(xp + 27.75), -(xp + 11.75), 22.0 * fh, 46.0 * fh) if v == 1 else None   # 16 × 24, près du piton
    petite = (a + 52.0, a + 72.0, 18.0 * fh, 12.0) if v == 2 else None    # x0, x1, piédroits, rayon de voûte

    def colonne(x0, x1, zb_c, zf_c, top, lisse=False, sans_s=False):
        xc = (x0 + x1) / 2
        ax = abs(xc)
        if ax < a:
            iv = [(intrados(x0, x1), top, True)]
        else:
            iv = [(-1.0, top, True)]
        if fenetre and fenetre[0] <= xc < fenetre[1]:
            e = min(xc - fenetre[0], fenetre[1] - xc)          # coins arrondis en marches
            m = 4.0 if e < 2 else (2.0 if e < 4 else 0.0)
            ylo, yhi = fenetre[2] + m, fenetre[3] - m
            iv = [(-1.0, ylo, True), (yhi, max(top, yhi + 10.0), True)]
        if petite and petite[0] <= xc < petite[1]:
            m, r = (petite[0] + petite[1]) / 2, (petite[1] - petite[0]) / 2
            t = min(1.0, (abs(xc - m) + 1.0) / r)
            yv = 2.0 * math.ceil((petite[2] + petite[3] * math.sqrt(max(0.0, 1 - t * t))) / 2.0)
            iv = [(-1.0, 0.0, True), (yv, top, True)]
        return _col(x0, x1, iv, zb_c, zf_c, lisse=lisse, sans_saillie=sans_s, grossier=ax > xm + 4)

    cols, avant_g, avant_d = [], [], []
    x = -W
    while x < W - 1e-6:
        x0, x1 = x, x + gx
        xc = (x0 + x1) / 2
        ax = abs(xc)
        top = dessus(xc)
        if f0 <= ax < f1:
            cols.append(colonne(x0, x1, zb, -6.5, y_fente, lisse=True))
        elif ax >= xm:
            # gradin arrière (haut) dans la masse principale, gradin avant (bas) à part
            cols.append(colonne(x0, x1, zb, Z_GRADIN, top, sans_s=True))
            h_av = max(22.0, 2.0 * round((top * 0.62 + float(rng.choice((-2.0, 0.0, 2.0)))) / 2.0))
            (avant_g if xc < 0 else avant_d).append(colonne(x0, x1, Z_GRADIN, -0.5, h_av))
        else:
            cols.append(colonne(x0, x1, zb, _front(ax, a, P), top))
        x = x1
    # le gradin avant : paliers plus larges (même hauteur sur 6 à 12 studs)
    for lst in (avant_g, avant_d):
        k = 0
        while k < len(lst):
            m = int(rng.choice((3, 4, 5, 6)))
            h = lst[k]["iv"][0][1]
            for cc in lst[k:k + m]:
                cc["iv"] = [(cc["iv"][0][0], h, True)]
            k += m

    strates = _strates(MOTIF_ARCHE, -1.5, H + 4)
    larg = tuple(int(round(w / dens / 2)) * 2 for w in (10, 14, 18, 22))
    larg_gros = tuple(int(round(w / dens / 2)) * 2 for w in (20, 26, 32))
    kw = dict(larg=larg, larg_gros=larg_gros, bande=12.0 / max(dens, 0.5), coulures=0.5 * dens,
              fissures=0.2 * dens)
    with b.group("Roche"):
        tops = _masse(b, cols, strates, rng, **kw)
        for lst, ouv in ((avant_g, (True, False)), (avant_d, (False, True))):
            if lst:
                tops += _masse(b, lst, strates, rng, debord_arriere=0.0, ouvert=ouv, **kw)

    # -- socles d'éboulis dans le passage (|x| de 46 à a, dessus à 0,5) ----------------------------------------
    with b.group("Eboulis"):
        for s in (-1, 1):
            xa, xb = sorted((s * X_CIEL, s * a))
            if abs(xb - xa) > 0.05:
                b.box((xa, -1.0, zb), (xb, 0.5, -0.5), vary("falaise_sable_fonce", rng, 0.03), studs="top",
                      name="Socle")
            for k in range(3 if a - X_CIEL >= 2.0 else 0):
                zr = -4.0 - k * 11.0 - float(rng.uniform(0, 4))
                sx = float(rng.uniform(1.2, max(1.3, min(3.2, a - X_CIEL - 0.6))))
                xr = s * (a - sx / 2 - 0.3)
                b.boxc((xr, 0.5 + 0.7, zr), (sx, 1.4, float(rng.uniform(2.2, 3.4))),
                       vary(("falaise_sable", "falaise_sable_claire", "mesa_violet_clair")[k], rng, 0.04),
                       yaw=float(rng.uniform(-8, 8)), studs="top", name="Rocher")
            # talus au pied des jambes et des baies : masses de sable en saillie (arêtes sur les demi-studs,
            # dessus sur les trois-quarts : jamais confondus avec les strates)
            for (u0, u1) in ((a + 1.0, f0 - 1.0), (f1 + 1.0, xp - 9.25), (xp + 8.75, xm - 1.0)):
                u = u0 + float(rng.uniform(0.0, 3.0))
                while u < u1 - 4.0:
                    wt = float(rng.choice((4.0, 5.0, 6.0, 8.0)))
                    ua = math.floor(u) + 0.5
                    ub = min(ua + wt, u1)
                    ht = float(rng.choice((3.0, 4.0, 5.0, 6.0))) + 0.75
                    zf_t = _front(ua + 0.1, a, P)
                    if petite and s > 0 and ua < petite[1] + 1.0 and ub > petite[0] - 1.0:
                        u = ub + 2.0                # la petite arche reste dégagée
                        continue
                    xa, xb = sorted((s * ua, s * ub))
                    zt1 = min(zf_t + 2.0, -0.25)
                    b.box((xa, -0.75, zf_t - 4.5), (xb, ht, zt1),
                          vary(("falaise_sable_fonce", "falaise_sable")[int(rng.random() < 0.4)], rng, 0.04),
                          studs="top", name="Talus")
                    if rng.random() < 0.7:          # tapis d'herbe sarcelle sur le talus
                        b.box((xa - 0.3, ht, zf_t - 4.5), (xb + 0.3, ht + 0.5, min(zt1 + 0.3, 0.05)),
                              vary("herbe_alien", rng, 0.03), studs="top", name="Herbe", collide=False)
                    u = ub + float(rng.choice((3.0, 6.0, 10.0)))

    # -- cascades ---------------------------------------------------------------------------------------
    for s in (-1, 1):
        xa, xb = sorted((s * f0, s * f1))
        _cascade_fente(b, xa, xb, y_fente, -6.5, rng)

    # -- pitons géants ------------------------------------------------------------------------------------
    h_pit = {0: (120, 114), 1: (112, 126), 2: (124, 110)}[v]
    sommets = []
    with b.group("Pitons"):
        for s, hp in zip((-1, 1), h_pit):
            sommets.append(_piton(b, s * xp, -8.25, float(round(hp * fh)), rng, sens=s))

    # -- végétation sur la couronne, les épaules, les pitons et les gradins ----------------------------------
    with b.group("Vegetation"):
        for (xt, zt, ht) in ((-16, -7, 24), (21, -9, 20), (-40, -12, 18), (44, -20, 16), (-112, -8, 16),
                             (120, -22, 14), (-152, -6, 16), (162, -24, 18)):
            d = _dessus_a(tops, xt, z=zt)
            if d is None:
                continue
            _arbre_boule(b, xt, d[2], zt, ht * fh, rng)
        for (sx, sy, sz) in sommets:
            _arbre_boule(b, sx + 1.5, sy, sz - 1.0, 14 * fh, rng, Rc=3.8)
        # rideaux de lianes sarcelle sous la voûte, près de la façade (et quelques-uns au fond) : brins effilés en
        # trois tronçons (foncé → clair), groupés par deux ou trois ; dessous ≥ 36 au-dessus du couloir
        prof_max = 4.0 + 1.5 + 0.5                     # retrait maximal du linteau (masses 4, fissures +1,5) + marge
        for zl, dens_l in ((-0.5 - prof_max - 0.3, 0.8), (-D + 3.0, 0.35)):
            for col in cols:
                if not (-a + 4.0 <= col["x0"] and col["x1"] <= a - 4.0) or rng.random() > dens_l:
                    continue
                yi = col["pierre"][0][0]
                lmax = min(11.0, yi - (Y_ENJAMBE + 2.0))
                if lmax < 3.0:
                    continue
                # longueurs en k + 0,2 : bouts sur des dixièmes, jamais sur les strates (demi-studs) ni les dessus
                L = math.floor(float(rng.uniform(2.5, lmax))) + 0.2
                l1 = round(L * 0.45, 1) + 0.05
                l2 = round(L * 0.3, 1) + 0.05
                y = yi
                for k, (h_, w_, ton) in enumerate(((l1, 1.4, "herbe_alien_fonce"), (l2, 1.0, "herbe_alien"),
                                                   (L - l1 - l2, 0.6, "boule_alien_claire"))):
                    if h_ < 0.1:
                        break
                    xa_ = col["x0"] + 1.0 - w_ / 2
                    b.box((xa_, y - h_, zl - 0.5 + 0.1 * k), (xa_ + w_, y, zl - 0.1 * k), vary(ton, rng, 0.04),
                          name="Liane", **DETAIL)
                    y -= h_
        for (xt, zt) in ((-4, -6), (8, -28), (-30, -18), (34, -6), (-24, -28), (12, -16), (-70, -20), (78, -26),
                         (-118, -10), (130, -24), (106, -8), (-140, -8), (-176, -26), (184, -10), (150, -6),
                         (-132, -6), (140, -6), (-170, -6), (176, -4)):
            d = _dessus_a(tops, xt, 1.5, z=zt)
            if d is None:
                continue
            _buisson(b, xt, d[2], zt, rng, taille=float(rng.uniform(1.0, 1.6)))


def arche_finale(b, variant: int = 0, passage: float = 104, largeur: float = 400, profondeur: float = 34,
                 hauteur: float = 96) -> dict:
    """Arche de roche géante de la sortie (voir l'en-tête du module). ≤ 1 500 pièces."""
    v = variant % 3
    BUDGET = 1500
    a = 2.0 * math.ceil(max(float(passage), PASSAGE_MIN) / 4.0)       # demi-passage, sur la grille de 2
    W = 2.0 * round(float(largeur) / 4.0)
    D = float(profondeur)
    H = float(hauteur)
    graine = int(b.rng.integers(1 << 30))
    n0 = len(b.parts)
    with b.group("ArcheFinale"):
        for dens in (1.0, 0.85, 0.7, 0.55, 0.45):
            del b.parts[n0:]
            _arche(b, v, a, W, D, H, np.random.default_rng(graine), dens)
            if len(b.parts) - n0 <= BUDGET:
                break
    info = _infos(b, n0)
    info["passage"] = 2 * a
    return info


# ---------------------------------------------------------------------------
# 2. Pont de roche naturel
# ---------------------------------------------------------------------------

# Profils du dessus du pont (|x| / (portee/2 + largeur_pile) → hauteur au-dessus de `hauteur`) : arc continu qui
# monte des pieds extérieurs des piles jusqu'au tablier (une seule arche, pas deux tours et une planche).
PROFILS_PONT = {
    0: [(0.0, 14), (0.3, 14), (0.5, 12), (0.62, 12), (0.72, 10), (0.83, 6), (0.93, 0), (1.0, -6)],
    1: [(0.0, 14), (0.3, 13), (0.5, 12), (0.62, 14), (0.72, 16), (0.83, 10), (0.93, 2), (1.0, -4)],
    2: [(0.0, 10), (0.3, 10), (0.5, 10), (0.62, 12), (0.72, 10), (0.83, 4), (0.93, -2), (1.0, -8)],
}


def pont_rocheux(b, variant: int = 0, portee: float = 100, hauteur: float = 36, epaisseur: float = 12,
                 largeur_pile: float = 30) -> dict:
    """Pont de roche naturel des terres de combat (voir l'en-tête du module). ≤ 350 pièces.

    Les piles sont des mesas (strates violettes, pied nuit, filets roses en saillie, dessus d'herbe verte studdé à
    coulures) ; le tablier prolonge leurs strates. Dessous : ≥ hauteur - 2 (et ≥ 34) au-dessus de |x| < 46, en
    voûte surbaissée par marches de 4 ; entre |x| = 46 et la pile, deux encorbellements trapus. Rien au sol en
    deçà de portee/2. v0 arc régulier ; v1 dissymétrique (pile gauche plus haute, tablier en pente) ;
    v2 tablier mince à lianes et pile droite fendue."""
    v = variant % 3
    rng = b.rng
    n0 = len(b.parts)
    BUDGET = 350
    p = 2.0 * math.ceil(max(float(portee), PORTEE_MIN) / 4.0)       # demi-portée, sur la grille de 2
    L = 2.0 * max(8.0, round(float(largeur_pile) / 2.0))
    X = p + L
    h = float(hauteur)
    y_min = max(h - 2.0, Y_ENJAMBE)
    E = float(epaisseur) * (0.75 if v == 2 else 1.0)
    graine = int(rng.integers(1 << 30))

    def construire(dens):
        r = np.random.default_rng(graine)

        def intrados(x0, x1):
            ax_in, ax_out = min(abs(x0), abs(x1)), max(abs(x0), abs(x1))
            if ax_in < X_CIEL:
                t = min(1.0, (4.0 * math.ceil(ax_out / 4.0 - 1e-9)) / X_CIEL)
                y = y_min + (h + 4.0 - y_min) * math.sqrt(max(0.0, 1 - t * t))
                if v == 1:
                    y += 1.0 if x0 < 0 else -1.0
                return max(y_min, 2.0 * math.ceil(y / 2.0))
            # encorbellements entre |x| = 46 et la pile
            k = int((ax_in - X_CIEL) // 2)
            return max(h - 14.0, y_min - 4.0 - 4.0 * k)

        tops = {}
        for s in (-1, 1):
            prof = [(f * X, h + dh * (E / 12.0 if f < 0.55 else 1.0)) for f, dh in PROFILS_PONT[v]]
            if v == 1 and s > 0:
                prof = [(px, py - (4.0 if px > 0.55 * X else 2.0)) for px, py in prof]
            x = 0.0
            while x < X - 1e-6:
                w = float(r.choice((4.0, 6.0, 6.0, 8.0)))
                x1 = min(X, x + w)
                if X - x1 < 4:
                    x1 = X
                if x < p < x1:
                    x1 = p
                hh = _interp(prof, (x + x1) / 2) + float(r.choice((-2.0, 0.0, 0.0, 2.0)))
                tops[(s, x, x1)] = max(12.0, 2.0 * round(hh / 2.0))
                x = x1

        def dessus(xc):
            s = -1 if xc < 0 else 1
            for (ss, a0, a1), hh in tops.items():
                if ss == s and a0 <= abs(xc) < a1:
                    return hh
            return h

        cols = []
        x = -X
        while x < X - 1e-6:
            x0, x1 = x, x + 2.0
            xc = (x0 + x1) / 2
            ax = abs(xc)
            top = dessus(xc)
            dz = 10.0 if ax >= p else (8.5 if ax >= 30 else 7.0)
            if ax < p:
                yi = intrados(x0, x1)
                top = max(top, yi + 8.0)
                iv = [(yi, top, True)]
            else:
                iv = [(-0.5, top, True)]
                if v == 2 and 0 < xc and p + 12 <= ax < p + 14:
                    iv = [(-0.5, 2.0 * round(top * 0.45 / 2.0), True)]     # pile fendue
            cols.append(_col(x0, x1, iv, -dz, dz))
            x = x1
        strates = _strates(MOTIF_PONT, -0.5, h + E + 12)
        larg = tuple(int(round(w / dens / 2)) * 2 for w in (8, 10, 12, 14))
        with b.group("Roche"):
            dessus_herbe = _masse(b, cols, strates, r, herbe=("herbe", "herbe_claire"), deux_faces=True, larg=larg,
                                  larg_gros=larg, bande=8.0, retraits=(0.0, 0.5, 1.0, 1.5, 2.0, 3.0),
                                  coulures=0.55 * dens, coulure_max=3.5, fissures=0.12 * dens)
            # jupes d'éboulis au pied des piles (côtés et extérieur ; arêtes sur les quarts de stud)
            yj = min(v for (v, _, _) in strates if v >= 4.0) - 0.6
            for s in (-1, 1):
                xa, xb = sorted((s * (p + 2.25), s * (X + 1.25)))
                b.box((xa, -0.4, -11.25), (xb, yj, 11.25), vary("mesa_violet_fonce", r, 0.03), studs="top",
                      name="Jupe")
        # lianes sous le tablier (v2) : elles s'arrêtent à 34 au-dessus du couloir
        if v == 2:
            with b.group("Lianes"):
                for xl in (-30.0, -18.0, -7.0, 5.0, 16.0, 27.0):
                    xl += float(r.uniform(-1.5, 1.5))
                    col = next(cc for cc in cols if cc["x0"] <= xl < cc["x1"])
                    yi = col["pierre"][0][0]
                    lmax = yi - y_min - 1.3            # bout de liane compris (0,7) : tout reste au-dessus de 34
                    if lmax < 1.5:
                        continue
                    for sz in (-1, 1):
                        Lv = float(r.uniform(1.5, min(lmax, 7.0)))
                        z0 = sz * (col["zf"] - 1.6)
                        za, zb2 = sorted((z0, z0 + sz * 0.5))
                        b.box((xl - 0.35, yi - Lv, za), (xl + 0.35, yi, zb2), vary("feuillage_fonce", r, 0.05),
                              name="Liane", **DETAIL)
                        b.box((xl - 0.6, yi - Lv - 0.7, za - 0.1), (xl + 0.6, yi - Lv + 0.3, zb2 + 0.1),
                              vary("feuillage_clair", r, 0.05), name="Liane", **DETAIL)
        # éboulis et rochers au pied des piles (hors du passage)
        with b.group("Eboulis"):
            for s in (-1, 1):
                for k in range(5):
                    xr = s * float(r.uniform(p + 4.0, X - 2.0))
                    zr = float(r.choice((-1, 1))) * float(r.uniform(11.4, 12.2))
                    sx, sz_ = float(r.uniform(2.4, 4.0)), float(r.uniform(1.8, 2.6))
                    b.boxc((xr, 0.7, zr), (sx, 1.4 + 0.3 * (k % 3), sz_), vary(("mesa_violet", "mesa_violet_clair",
                                                                               "mesa_violet_fonce", "rocher",
                                                                               "mesa_violet")[k], r, 0.04),
                           yaw=float(r.uniform(-30, 30)), studs="top", name="Rocher")
                for sz in (-1, 1):
                    xw = s * (X - float(r.uniform(4.0, 10.0)))
                    za, zb2 = sorted((sz * 11.25, sz * 13.25))
                    b.wedge((xw - 2.0, -0.4, za), (xw + 2.0, 3.6, zb2), vary("mesa_violet_fonce", r, 0.04),
                            down="-z" if sz < 0 else "+z", studs="top", name="Talus")
        # buissons sur le tablier et les piles
        with b.group("Vegetation"):
            for (xt, zt) in ((-24, 3), (-6, -4), (12, 4), (30, -3), (-36, -4), (40, 4), (-(p + 10), 5),
                             (p + 8, -6), (-(p + 22), -4), (p + 20, 4), (-(p + 4), -5), (p + 14, 6)):
                d = _dessus_a(dessus_herbe, xt, 1.5, z=zt)
                if d is not None:
                    _buisson(b, xt, d[2], zt, r, alien=False, taille=float(r.uniform(1.2, 1.8)))

    with b.group("PontRocheux"):
        for dens in (1.0, 0.8, 0.65, 0.5):
            del b.parts[n0:]
            construire(dens)
            if len(b.parts) - n0 <= BUDGET:
                break
    info = _infos(b, n0)
    info["portee"] = 2 * p
    return info


# ---------------------------------------------------------------------------
# 3. Bancs de nuages dorés
# ---------------------------------------------------------------------------

def nuages_dores(b, variant: int = 0, largeur: float = 50, profondeur: float = 26, hauteur: float = 24) -> dict:
    """Banc de nuages dorés posé sur sa base (y = 0), dans l'emprise largeur (X) × profondeur (Z), sous `hauteur`.

    Coussin de galettes rondes à plat (le banc repose sur ce qui le porte : sol ou gradin de falaise), rangée
    basse de boules d'ombre et orangées devant, rangée avant de boules or, rangée arrière plus haute or clair qui
    suit le profil, couronnes crème au sommet. Un seul bloc collidable (la base, cachée dans les boules).
    L'avant (-Z) regarde le couloir. ≤ 70 pièces.
    v0 banc long et bas ; v1 banc en tour (cumulus au milieu) ; v2 banc à deux lobes."""
    v = variant % 3
    rng = b.rng
    n0 = len(b.parts)
    L, P, H = float(largeur), float(profondeur), float(hauteur)
    hl, hp = L / 2, P / 2
    kw = dict(collide=False, name="Nuage")

    def profil(u):
        u = max(-1.0, min(1.0, u))
        if v == 0:
            return H * (0.82 - 0.22 * u * u)
        if v == 1:
            return H * (1.0 - 0.5 * u * u)
        lobes = max(math.exp(-((u - 0.45) / 0.32) ** 2), 0.88 * math.exp(-((u + 0.42) / 0.3) ** 2))
        return H * (0.55 + 0.45 * lobes)

    def boule(x, y, z, r, ton, a=0.025):
        r = min(r, hp - 0.05, hl - 0.05)
        x = min(max(x, -hl + r), hl - r)
        z = min(max(z, -hp + r), hp - r)
        y = min(y, H - r)
        b.ball((x, y, z), r, vary(ton, rng, a), **kw)
        return x, y, z, r

    def rangee(z_off, haut, r_max, r_fac, ton, pas=1.25, r_min=2.0):
        """Boules le long de X ; le dessus de chaque boule suit haut(u). Renvoie [(x, y, z, r)]."""
        out = []
        r_max = max(r_min, min(r_max, hp - abs(z_off) - 0.05))
        x = -hl + min(r_max, max(r_min, r_fac * haut(-1.0)))
        while True:
            h = haut(x / hl)
            r = min(r_max, max(r_min, r_fac * h))
            if x > hl - r * 0.6:
                break
            zz = z_off + float(rng.uniform(-0.15, 0.15)) * hp
            f = float(rng.choice((0.72, 0.85, 1.0, 1.0)))
            out.append(boule(x, h - r * (0.9 + 0.25 * float(rng.random())), zz, r * f, ton))
            x += r * pas * float(rng.uniform(0.7, 1.05))
        return out

    with b.group("Nuages"):
        # coussin : galettes rondes à plat, dessus décalés (jamais deux dessus confondus)
        rd = min(hp * 0.96, hl * 0.42)
        nd = max(1, int(round((L - 2 * rd) / (1.6 * rd))) + 1)
        xs = np.linspace(-hl + rd, hl - rd, nd) if nd > 1 else [0.0]
        for i, x in enumerate(xs):
            b.cyl((float(x), 0.5 + 0.1 * i, 0.0), rd, 1.0 + 0.2 * i, vary("nuage_ombre", rng, 0.02), axis="y", **kw)
        # base (seule pièce collidable), cachée dans les boules
        b.box((-hl * 0.6, 0.0, -hp * 0.35), (hl * 0.6, min(0.25 * H, 4.0), hp * 0.35), c("nuage_or"), name="Base",
              shadow=False)
        # rangée arrière (haute, or clair au soleil), rangée avant (or), rangée basse (ombres dorées)
        arriere = rangee(0.3 * hp, profil, hp * 0.7, 0.36, "nuage_or_clair")
        avant = rangee(-0.32 * hp, lambda u: 0.72 * profil(u) + float(rng.uniform(-0.04, 0.04)) * H, hp * 0.66, 0.4,
                       "nuage_or")
        rb = min(hp * 0.48, 0.2 * H)
        nb = max(2, int(math.ceil((L - 2 * rb) / (1.5 * rb))) + 1)
        for i, x in enumerate(np.linspace(-hl + rb, hl - rb, nb)):
            boule(float(x) + float(rng.uniform(-0.3, 0.3)) * rb, 0.45 * rb, -hp + rb + float(rng.uniform(0, 0.15)) * hp,
                  rb * float(rng.uniform(0.85, 1.0)), ("nuage_ombre", OMBRE_DOREE)[i % 2])
        # couronnes crème sur les plus hautes boules (vers l'avant et le haut)
        for k, (x, y, z, r) in enumerate(sorted(arriere + avant, key=lambda t: -(t[1] + t[3]))[:4]):
            rc = 0.55 * r
            boule(x + float(rng.uniform(-0.3, 0.3)) * r, y + 0.45 * r, z - 0.3 * r, rc, CREME_CHAUD, 0.015)
        # bouffées or entre les rangées, au milieu de la hauteur (bouche les trous)
        for (x, y, z, r) in avant[1::2]:
            boule(x + 0.5 * r, y - 0.35 * r, z + 0.4 * r, 0.75 * r, "nuage_or")
    return _infos(b, n0)


# ---------------------------------------------------------------------------
# 4. Vaisseau rond sur pattes
# ---------------------------------------------------------------------------

def vaisseau_rond(b, variant: int = 0, rayon: float = 13) -> dict:
    """Vaisseau rond générique garé sur la planète extraterrestre (voir l'en-tête du module).

    Coque en lentille : disques empilés de rayon décroissant dessous et dessus (dessous de la coque à y = 7),
    bande d'équateur colorée, paroi à trois grands hublots à l'AVANT (-Z), coupole (anneau clair et dôme blanc à
    demi enfoui), petite antenne, feux sous la bande, pattes inclinées terminées par des semelles studdées,
    rampe depuis une trappe avant. Aucun anneau de hublots tout autour, aucun texte. ≤ 220 pièces."""
    v = variant % 4
    rng = b.rng
    n0 = len(b.parts)
    r = float(rayon)
    turq = v in (2, 3)
    acc = c("bande_turquoise") if turq else c("coque_violet")
    acc_c = c("eau_claire") if turq else c("coque_lavande")
    blanc, ombre = c("coque"), c("coque_ombre")
    n_pattes = 3 if v in (1, 3) else 4
    ailerons = v in (2, 3)
    y0 = 7.0
    # (rayon relatif, épaisseur, couleur) de bas en haut
    tiers = [(0.42, 0.7, ombre), (0.66, 0.8, ombre), (0.84, 0.8, blanc), (0.95, 0.9, blanc), (1.0, 1.0, acc),
             (0.97, 3.0, blanc), (0.86, 0.8, blanc), (0.68, 0.8, blanc), (0.46, 0.8, acc_c)]
    with b.group("Vaisseau"):
        y = y0
        niveaux = {}
        for k, (fr, e, col) in enumerate(tiers):
            b.cyl((0, y + e / 2, 0), fr * r, e, col, axis="y", name="Coque")
            niveaux[k] = (y, y + e, fr * r)
            y += e
        y_anneau0, y_anneau1, _ = niveaux[8]
        rd = 0.38 * r
        yd = (y_anneau0 + y_anneau1) / 2
        b.ball((0, yd, 0), rd, blanc, name="Coupole")
        # antenne
        b.cyl((0, yd + rd + 1.1, 0), 0.18, 2.6, c("metal"), axis="y", collide=False, name="Antenne")
        b.cyl((0, yd + rd + 0.15, 0), 0.7, 0.3, acc_c, axis="y", collide=False, name="Antenne")
        b.ball((0, yd + rd + 2.55, 0), 0.4, c("neon_cyan"), material="Neon", **DETAIL, name="Feu")
        # trois hublots à l'avant, sur la paroi
        yw0, yw1, rw = niveaux[5]
        yh = (yw0 + yw1) / 2
        for th in (-22.0, 0.0, 22.0):
            t = math.radians(th)
            u = np.array([math.sin(t), 0.0, -math.cos(t)])
            b.part("cyl", (0.4, 2.7, 2.7), u * (rw + 0.05) + YV * yh, _repere(u), acc_c, collide=False,
                   name="Cadre_hublot")
            b.part("cyl", (0.3, 2.0, 2.0), u * (rw + 0.3) + YV * yh, _repere(u), c("hublot"), reflectance=0.15,
                   collide=False, name="Hublot")
        # réacteur lumineux sous la coque
        b.cyl((0, y0 - 0.1, 0), 0.24 * r, 0.2, c("neon_cyan"), axis="y", material="Neon", name="Reacteur", **DETAIL)
        b.cyl((0, y0 - 0.25, 0), 0.12 * r, 0.3, acc_c, axis="y", name="Reacteur", **DETAIL)
        # feux sous la bande d'équateur
        yb0 = niveaux[4][0]
        for k in range(8):
            t = math.radians(22.5 + 45 * k)
            b.cyl((math.sin(t) * 0.975 * r, yb0 - 0.1, -math.cos(t) * 0.975 * r), 0.28, 0.2, c("neon_cyan"),
                  axis="y", material="Neon", name="Feu", **DETAIL)
        # nervures rayonnantes sur le dessus
        yn = niveaux[6][1]
        for k in range(8):
            t = 22.5 + 45 * k
            rm_ = (0.68 + 0.86) / 2 * r
            tr = math.radians(t)
            b.boxc((math.sin(tr) * rm_, yn + 0.075, -math.cos(tr) * rm_), (0.35, 0.15, 0.18 * r), ombre, yaw=-t,
                   name="Nervure", **DETAIL)
        # ailerons arrière (pente vers l'extérieur)
        if ailerons:
            for th in (140.0, -140.0):
                t = math.radians(th)
                u = np.array([math.sin(t), 0.0, -math.cos(t)])
                zl = -u
                yl = YV
                xl = np.cross(yl, zl)
                long_ = 5.0
                ctr = u * (rw - 0.3 + long_ / 2) + YV * (yw0 + 1.6)
                b.part("wedge", (0.6, 3.2, long_), ctr, np.column_stack([xl, yl, zl]), acc, name="Aileron")
        # pattes inclinées, rotules, semelles studdées
        a0 = 45.0 if n_pattes == 4 else 60.0
        for k in range(n_pattes):
            t = math.radians(a0 + k * 360.0 / n_pattes)
            u = np.array([math.sin(t), 0.0, -math.cos(t)])
            haut = u * (0.58 * r) + YV * (y0 + 1.0)
            bas = u * (r + 1.2) + YV * 1.1
            d = bas - haut
            n = float(np.linalg.norm(d))
            b.part("cyl", (n, 1.0, 1.0), (haut + bas) / 2, _repere(d), ombre, name="Patte")
            b.part("cyl", (n * 0.45, 1.3, 1.3), haut + d * 0.3, _repere(d), acc, name="Gaine")
            b.ball(haut, 1.05, acc_c, name="Rotule")
            b.ball(bas, 0.8, blanc, name="Cheville")
            b.cyl((bas[0], 0.3, bas[2]), 1.6, 0.6, ombre, axis="y", studs="top", name="Semelle")
        # rampe d'accès : planche inclinée de la trappe avant jusqu'au sol, rambardes, cadre de trappe
        zt = -0.36 * r
        p_bas = np.array([0.0, 0.3, -(r + 2.5)])
        p_haut = np.array([0.0, y0 + 0.1, zt])
        d = p_haut - p_bas
        Lr = float(np.linalg.norm(d))
        zl = d / Lr
        xl = np.array([1.0, 0.0, 0.0])
        yl = np.cross(zl, xl)
        Rr = np.column_stack([xl, yl, zl])
        mil = (p_bas + p_haut) / 2
        b.part("block", (3.4, 0.5, Lr), mil - yl * 0.25, Rr, ombre, studs="top", name="Rampe")
        for sx in (-1, 1):
            b.part("block", (0.25, 0.8, Lr - 0.4), mil + yl * 0.4 + xl * sx * 1.55, Rr, acc, name="Rampe_bord",
                   **DETAIL)
        b.box((-2.0, y0 - 0.3, zt - 0.3), (2.0, y0 + 0.05, zt + 0.4), acc_c, name="Trappe", collide=False)
        b.box((-1.4, y0 - 0.25, zt + 0.4), (1.4, y0 + 0.02, zt + 2.0), c("hublot"), name="Trappe", collide=False)
    return _infos(b, n0)
