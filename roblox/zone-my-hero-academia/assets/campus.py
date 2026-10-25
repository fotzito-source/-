"""Bâtiments du campus de l'académie (zone My Hero Academia, zone 8), style « stud ».

Fonctions publiques (chacune : `f(b, variant=0, ...)` → {"emprise": (x, z), "hauteur": h}) :
- dortoir(largeur=40, profondeur=22, etages=4, simple=False) : résidence de brique rouge à balcons blancs et toit
    en croupe sombre (référence 2) ; v0 balcons sur toute la largeur, v1 deux ailes et cage d'escalier vitrée en
    retrait au centre, v2 balcons au centre et travées d'about en saillie à pilastres blancs ;
    `simple=True` : version d'arrière-plan (volume, toit, bandes de balcons, une porte) ;
- batiment_cours(largeur=52, profondeur=24, hauteur=26) : bâtiment de cours en béton blanc à grandes grilles
    vitrées, tour d'escalier vitrée, auvent d'entrée à liseré cyan, panneaux solaires ; v0 atrium à l'extrémité
    +X, v1 galerie vitrée en façade au 2e niveau et atrium à l'extrémité -X ;
- halle_entrainement(largeur=36, profondeur=36, hauteur=22) : gymnase à grande verrière en berceau, porte de
    hangar coulissante entrouverte, bandeau ENTRAÎNEMENT / GYMNASE ;
- tours_jumelles(passage=116, largeur_tour=44, profondeur=38, hauteurs=(120, 134), y_passerelle=46) : le repère
    final, deux tours de bureaux de verre bleu-violet (deux prismes décalés chacune), reliées par une passerelle
    vitrée au-dessus de la route (dessous à 46) et une seconde plus fine plus haut.

Repère (voir CONVENTIONS.md) : origine au centre de l'emprise au sol, y = 0 au sol, l'AVANT regarde -Z local
(la zone tourne l'asset vers la route). Exception : `tours_jumelles` est posé sans rotation, sa grande façade
regarde +Z (les joueurs qui arrivent) et la structure occupe z ∈ [-profondeur, 0].
Vu de la route (depuis -z), +x est à GAUCHE.

Propriété intellectuelle : tours de bureaux vitrées génériques (comme les tours reliées d'Osaka ou de Kuala
Lumpur), résidences et bâtiments scolaires génériques. Aucun nom, aucune lettre, aucun emblème ; seuls textes :
ENTRAÎNEMENT, GYMNASE, DORTOIRS (police « sans »).
"""

from __future__ import annotations

import math

from assets.mobilier import _label
from kit import hexrgb, mix, rot_z
from palette import c, tirer, vary

# ---------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------

ROUGE_BALISAGE = "#FF3B30"      # feux d'obstacle (Neon)
INTERIEUR = "#2A2F55"           # fond sombre d'un hall, d'une porte de hangar ouverte
PANNEAU_SOLAIRE = "#24346E"


def col(x):
    """Nom de palette, '#hex' ou tuple → tuple RGB."""
    if isinstance(x, tuple):
        return x
    if isinstance(x, str) and x.startswith("#"):
        return hexrgb(x)
    return c(x)


def vr(x, rng, amount=0.05):
    """`vary` qui accepte aussi '#hex' et les tuples."""
    return vary(col(x), rng, amount)


def _sur_face(b, face, ua, ub, ya, yb, e0, e1, couleur, **kw):
    """Bloc posé sur une face verticale. `face` = (axe, signe, plan, ...) : axe 'z' (u = x) ou 'x' (u = z),
    signe = sens de la normale extérieure, plan = coordonnée de la face. e0..e1 = saillie (négatif = en retrait)."""
    axe, s, plan = face[0], face[1], face[2]
    if axe == "z":
        return b.box((ua, ya, plan + s * e0), (ub, yb, plan + s * e1), col(couleur), **kw)
    return b.box((plan + s * e0, ya, ua), (plan + s * e1, yb, ub), col(couleur), **kw)


def _moins(intervalle, trous):
    """Intervalle (u0, u1) privé d'une liste de trous (a, b) → liste d'intervalles."""
    segs = [intervalle]
    for a, bb in trous:
        nouv = []
        for u, v in segs:
            if bb <= u or a >= v:
                nouv.append((u, v))
                continue
            if a > u:
                nouv.append((u, a))
            if bb < v:
                nouv.append((bb, v))
        segs = nouv
    return [(u, v) for u, v in segs if v - u > 0.6]


# ---------------------------------------------------------------------------
# Tours jumelles : prismes de verre à quadrillage blanc
# ---------------------------------------------------------------------------

RETRAIT = 0.3          # le verre est en retrait de 0,3 sur l'enveloppe : les montants (saillie 0,25) restent dedans
EP_M = 0.25            # saillie des montants et des lignes d'étage
L_M = 0.4              # largeur d'un montant vertical
H_LIGNE = 0.45         # hauteur d'une ligne d'étage
Y_SOCLE = 14.6         # dessus de la dalle de transfert blanche (le verre des tours commence là)
PAS_ETAGE = 6.0


class _Prisme:
    """Volume de verre d'une tour : enveloppe x0..x1, z0..z1, verre de y0 à la couronne, hauteur h (couronne
    comprise). `transfert` : dalle blanche sous le verre (dessus du hall) ; sinon le prisme est posé sur un toit."""

    def __init__(self, nom, x0, x1, z0, z1, h, denses=(), y0=Y_SOCLE, transfert=True):
        self.nom, self.x0, self.x1, self.z0, self.z1, self.h = nom, x0, x1, z0, z1, h
        self.denses = set(denses)        # faces à quadrillage serré : 'avant', 'arriere', 'gauche', 'droite'
        self.y0, self.transfert = y0, transfert
        r = RETRAIT
        self.cx0, self.cx1, self.cz0, self.cz1 = x0 + r, x1 - r, z0 + r, z1 - r

    def faces(self):
        """(nom, (axe, signe, plan, u0, u1)) des quatre faces du noyau de verre."""
        return [
            ("avant", ("z", 1, self.cz1, self.cx0, self.cx1)),
            ("arriere", ("z", -1, self.cz0, self.cx0, self.cx1)),
            ("droite", ("x", 1, self.cx1, self.cz0, self.cz1)),
            ("gauche", ("x", -1, self.cx0, self.cz0, self.cz1)),
        ]

    def contient(self, x, z):
        return self.cx0 < x < self.cx1 and self.cz0 < z < self.cz1


def _caches(face, autres):
    """Parties d'une face masquées par les prismes voisins qui la touchent ou la traversent : [(a, b, h)]."""
    axe, s, plan, u0, u1 = face
    out = []
    for Q in autres:
        if axe == "z":
            q0, q1, qa, qb = Q.cz0, Q.cz1, Q.cx0, Q.cx1
        else:
            q0, q1, qa, qb = Q.cx0, Q.cx1, Q.cz0, Q.cz1
        ok = (q0 <= plan + 1e-6 and q1 > plan + 0.05) if s > 0 else (q1 >= plan - 1e-6 and q0 < plan - 0.05)
        if ok:
            a, bb = max(u0, qa - 0.6), min(u1, qb + 0.6)
            if bb > a:
                out.append((a, bb, Q.h))
    return out


def _etages(y0, y1, pas):
    ys, y = [], y0 + pas
    while y < y1 - 1.5:
        ys.append(y)
        y += pas
    return ys


def _prisme_verre(b, P, autres, verre, rng, *, pas_dense=4.6, pas_clair=9.5, reflets=True, decal=0, fonce=None,
                  haut=None, neon_couronne=False):
    """Noyau de verre (en 3 tons du bas vers le haut), coins blancs, quadrillage de montants et de lignes
    d'étage (une ligne sur cinq en bandeau technique plus épais), bandes de reflet en escalier sur les faces
    denses, couronne blanche à parapet stud (liseré néon cyan en option)."""
    y_c = P.h - 3.0                    # base de la couronne
    Y0 = P.y0
    fonce = fonce or mix(col(verre), c("vitre_violette_fonce"), 0.55)
    haut = haut or mix(col(verre), c("vitre_violette_claire"), 0.35)
    y1 = min(Y0 + 3 * PAS_ETAGE, y_c)
    y2 = max(y_c - 4 * PAS_ETAGE, y1)
    with b.group(P.nom):
        # dalle de transfert blanche (dessus du hall) et noyau de verre en trois tons
        if P.transfert:
            b.box((P.x0, 13.0, P.z0), (P.x1, Y0, P.z1), c("blanc"), name="DalleTransfert")
            tons = ((Y0, y1, fonce), (y1, y2, col(verre)), (y2, y_c, haut))
        else:
            tons = ((Y0, y_c, haut),)
        for ya, yb, couleur in tons:
            if yb - ya > 0.5:
                b.box((P.cx0, ya, P.cz0), (P.cx1, yb, P.cz1), couleur, material="Glass", reflectance=0.25,
                      name="Verre")
        # couronne blanche (déborde de 0,3 sur le verre), dessus stud, parapet
        b.box((P.x0, y_c, P.z0), (P.x1, P.h - 0.8, P.z1), c("blanc"), studs="top", name="Couronne")
        e = 0.7
        for (xa, xb, za, zb) in ((P.x0, P.x1, P.z0, P.z0 + e), (P.x0, P.x1, P.z1 - e, P.z1),
                                 (P.x0, P.x0 + e, P.z0 + e, P.z1 - e), (P.x1 - e, P.x1, P.z0 + e, P.z1 - e)):
            b.box((xa, P.h - 0.8, za), (xb, P.h + 0.6, zb), c("blanc_casse"), studs="top", name="Parapet")
        # liseré néon cyan à mi-hauteur de la couronne, sur les faces denses
        if neon_couronne:
            for nom, face in P.faces():
                if nom in P.denses:
                    axe, s, plan, u0, u1 = face
                    _sur_face(b, face, u0 + 0.6, u1 - 0.6, y_c + 0.8, y_c + 1.2, RETRAIT - 0.05, RETRAIT + 0.15,
                              "neon_cyan", material="Neon", collide=False, shadow=False, name="NeonCouronne")
        # coins blancs : un poteau carré à chaque arête verticale (s'il n'est pas noyé dans un voisin)
        for x in (P.cx0, P.cx1):
            for z in (P.cz0, P.cz1):
                y_bas = Y0
                for Q in autres:
                    if Q.contient(x, z):
                        y_bas = max(y_bas, Q.h)
                if y_bas < y_c - 1:
                    sx = -1 if x == P.cx0 else 1
                    sz = -1 if z == P.cz0 else 1
                    b.box((x - sx * 0.25, y_bas, z - sz * 0.25), (x + sx * RETRAIT, y_c, z + sz * RETRAIT),
                          c("cadre_blanc"), collide=False, name="Coin")
        # quadrillage par face
        for nom, face in P.faces():
            dense = nom in P.denses
            axe, s, plan, u0, u1 = face
            caches = _caches(face, autres)
            pas_u = pas_dense if dense else pas_clair
            n = max(1, round((u1 - u0) / pas_u))
            du = (u1 - u0) / n
            us = [u0 + k * du for k in range(1, n)]
            pas_y = PAS_ETAGE if dense else 2 * PAS_ETAGE
            ys = _etages(Y0, y_c, pas_y)
            for u in us:
                y_bas = Y0
                for a, bb, h in caches:
                    if a < u < bb:
                        y_bas = max(y_bas, h)
                if y_bas < y_c - 1:
                    _sur_face(b, face, u - L_M / 2, u + L_M / 2, y_bas, y_c, -0.05, EP_M, "cadre_blanc",
                              collide=False, name="Montant")
            for j, y in enumerate(ys, start=1):
                technique = (j * pas_y / PAS_ETAGE) % 5 == 0          # bandeau technique tous les 5 étages
                hl, ep = (1.1, RETRAIT) if technique else (H_LIGNE, EP_M)
                for ua, ub in _moins((u0, u1), [(a, bb) for a, bb, h in caches if h > y]):
                    _sur_face(b, face, ua, ub, y - hl / 2, y + hl / 2, -0.05, ep, "cadre_blanc",
                              collide=False, name="Etage")
            # bandes de reflet en escalier (faces denses) : un panneau par travée, montant en diagonale
            if dense and reflets:
                ys_all = [Y0] + _etages(Y0, y_c, PAS_ETAGE) + [y_c]
                nb_et = len(ys_all) - 1
                bords = [u0] + us + [u1]
                for k in range(len(bords) - 1):
                    ua, ub = bords[k], bords[k + 1]
                    um = (ua + ub) / 2
                    y_min = Y0
                    for a, bb, h in caches:
                        if a < um < bb:
                            y_min = max(y_min, h)
                    # grande diagonale claire (3 étages) liserée de reflet blanc, petite diagonale plus bas
                    base = nb_et // 4 + k + decal + 2 * len(nom)        # départ différent selon la face
                    for (j0, long_, couleur) in ((base, 3, "vitre_violette_claire"),
                                                 (base + 4, 1, "vitre_reflet")):
                        if j0 < 0 or j0 >= nb_et:
                            continue
                        ja, jb = j0, min(nb_et, j0 + long_)
                        ya, yb = ys_all[ja], ys_all[jb]
                        ya = max(ya, y_min)
                        if yb - ya < 2:
                            continue
                        _sur_face(b, face, ua, ub, ya, yb, -0.05, 0.12, couleur, material="Glass",
                                  collide=False, name="Reflet")


def _hall(b, P, faces_hall, rng, *, rec=1.5, rec_passage=4.0, cote_passage=None):
    """Hall vitré clair sur deux niveaux sous un prisme : verre en retrait, poteaux blancs, bandeau
    intermédiaire, meneaux. `faces_hall` = faces où l'on dessine meneaux et poteaux intermédiaires."""
    rx0 = rec_passage if cote_passage == "gauche" else rec
    rx1 = rec_passage if cote_passage == "droite" else rec
    x0, x1, z0, z1 = P.cx0 + rx0, P.cx1 - rx1, P.cz0 + rec, P.cz1 - rec
    with b.group(P.nom + "Hall"):
        b.box((x0, 0.6, z0), (x1, 13.0, z1), c("vitre_claire"), material="Glass", name="HallVerre")
        # bandeau intermédiaire (plancher du 2e niveau), en saillie de 0,3 sur le verre
        b.box((x0 - 0.3, 6.6, z0 - 0.3), (x1 + 0.3, 7.2, z1 + 0.3), c("blanc"), name="Plancher")
        # poteaux d'angle
        for xa, xb in ((P.x0, P.x0 + 1.4), (P.x1 - 1.4, P.x1)):
            for za, zb in ((P.z0, P.z0 + 1.4), (P.z1 - 1.4, P.z1)):
                b.box((xa, 0.6, za), (xb, 13.0, zb), c("blanc"), name="Poteau")
        faces = dict(P.faces())
        for nom in faces_hall:
            axe, s, plan, u0, u1 = faces[nom]
            r = rx0 if nom == "gauche" else rx1 if nom == "droite" else rec
            plan_v = plan - s * r                      # plan du verre du hall
            fv = (axe, s, plan_v)
            ua, ub = (x0, x1) if axe == "z" else (z0, z1)
            # meneaux fins tous les ~3,5
            n = max(2, round((ub - ua) / 3.5))
            for k in range(1, n):
                u = ua + k * (ub - ua) / n
                _sur_face(b, fv, u - 0.15, u + 0.15, 0.6, 13.0, -0.05, 0.15, "cadre_blanc", collide=False,
                          name="Meneau")
            # poteaux intermédiaires (au droit de la façade de la tour) tous les ~9
            n = max(2, round((u1 - u0) / 9))
            for k in range(1, n):
                u = u0 + k * (u1 - u0) / n
                _sur_face(b, (axe, s, plan), u - 0.6, u + 0.6, 0.6, 13.0, -r, RETRAIT, "blanc", name="Poteau")
    return (x0, x1, z0, z1)


def _auvent(b, face, ua, ub, y, prof, *, neon="neon_cyan"):
    """Auvent blanc en porte-à-faux depuis `face` (plan de départ), profondeur `prof`, liseré néon à l'avant."""
    _sur_face(b, face, ua, ub, y, y + 0.8, -0.2, prof, "blanc", studs="top", name="Auvent")
    _sur_face(b, face, ua - 0.1, ub + 0.1, y + 0.1, y + 0.5, prof, prof + 0.2, neon, material="Neon",
              collide=False, shadow=False, name="LisereAuvent")
    _sur_face(b, face, ua, ub, y - 0.2, y, prof - 1.0, prof - 0.6, neon, material="Neon", collide=False,
              shadow=False, name="LisereSous")


def _entree(b, face, uc, larg, *, n_portes=2):
    """Portes vitrées sombres à cadre blanc au pied d'une façade vitrée (plan = verre du hall)."""
    w = larg / n_portes
    _sur_face(b, face, uc - larg / 2 - 0.4, uc + larg / 2 + 0.4, 0.6, 6.3, -0.05, 0.3, "cadre_blanc", name="Cadre")
    for k in range(n_portes):
        ua = uc - larg / 2 + k * w
        _sur_face(b, face, ua + 0.2, ua + w - 0.2, 0.6, 5.8, 0.3, 0.45, "vitre_nuit", material="Glass",
                  collide=False, name="Porte")


def _toiture(b, P, rng, *, balisage=False, machinerie=1, edicule=True):
    """Équipements de toit : édicule technique, `machinerie + 1` caissons de climatisation (aucun si 0),
    feux d'obstacle rouges sur mâts aux deux coins opposés."""
    y = P.h - 0.8
    cxm, czm = (P.x0 + P.x1) / 2, (P.z0 + P.z1) / 2
    w, d = P.x1 - P.x0, P.z1 - P.z0
    with b.group(P.nom + "Toit"):
        if machinerie and edicule:
            ex0, ex1 = cxm - w * 0.22, cxm + w * 0.12
            ez0, ez1 = czm - d * 0.2, czm + d * 0.18
            b.box((ex0, y, ez0), (ex1, y + 5, ez1), c("beton_clair"), studs="top", name="Edicule")
            b.box((ex0 - 0.1, y + 3.2, ez0 - 0.1), (ex1 + 0.1, y + 4.2, ez1 + 0.1), c("acier"), collide=False,
                  name="Ventelles")
        if machinerie:
            for k in range(machinerie + 1):
                xa = cxm + w * 0.18 if edicule else cxm - 2.0
                za = czm - d * 0.3 + k * 6
                b.box((xa, y, za), (xa + 4, y + 2.4, za + 3), c("acier"), studs="top", name="Clim")
        if balisage:
            for (x, z) in ((P.x0 + 1.2, P.z1 - 1.2), (P.x1 - 1.2, P.z0 + 1.2)):
                b.cyl((x, P.h + 1.4, z), 0.2, 4.4, c("acier"), collide=False, name="MatBalise")
                b.box((x - 0.45, P.h + 3.6, z - 0.45), (x + 0.45, P.h + 4.5, z + 0.45), col(ROUGE_BALISAGE),
                      material="Neon", collide=False, shadow=False, name="FeuObstacle")


def _passerelle(b, xa, xb, y_bas, haut, z0, z1, verre, verre2, *, niveaux=2, pas=5.3, x_col=None, sous_face=True):
    """Passerelle vitrée entre les tours : dalles blanches, verre en deux tons, montants (un sur quatre en
    grosse nervure), colliers blancs aux deux bouts, sous-face lavande à néons. `y_bas` = point le plus bas
    (les néons) ; la structure commence 0,4 plus haut. `x_col` = |x| des faces des tours (colliers)."""
    yb = y_bas + 0.4
    yt = y_bas + haut
    e_dalle = 1.6
    with b.group("Passerelle"):
        # sous-face : néons blancs le long des deux rives, panneau lavande et ligne cyan au centre
        for z in (z1 - 1.2, z0 + 1.2):
            b.box((xa + 0.5, y_bas, z - 0.25), (xb - 0.5, yb, z + 0.25), c("neon_blanc"), material="Neon",
                  collide=False, shadow=False, name="NeonDessous")
        if sous_face:
            b.box((xa + 0.5, y_bas + 0.15, z0 + 2.4), (xb - 0.5, yb, z1 - 2.4), c("lavande_pale"), collide=False,
                  name="SousFace")
            zm = (z0 + z1) / 2
            b.box((xa + 0.5, y_bas + 0.05, zm - 0.3), (xb - 0.5, y_bas + 0.15, zm + 0.3), c("neon_cyan"),
                  material="Neon", collide=False, shadow=False, name="NeonAxe")
        b.box((xa, yb, z0 - 0.5), (xb, yb + e_dalle, z1 + 0.5), c("blanc"), name="DalleBasse")
        yv0, yv1 = yb + e_dalle, yt - 1.6
        b.box((xa, yv0, z0), (xb, yv1, z1), col(verre), material="Glass", reflectance=0.25, name="Verre")
        b.box((xa, yv1, z0 - 0.5), (xb, yt, z1 + 0.5), c("blanc"), studs="top", name="DalleHaute")
        hn = (yv1 - yv0) / niveaux
        for k in range(1, niveaux):
            y = yv0 + k * hn
            b.box((xa, y - 0.35, z0 - 0.3), (xb, y + 0.35, z1 + 0.3), c("blanc"), name="Plancher")
        # colliers blancs contre les tours (la passerelle « sort » de la façade)
        if x_col is not None:
            for s in (-1, 1):
                ua, ub = sorted((s * x_col, s * (x_col - 1.6)))
                b.box((ua, yb - 0.3, z0 - 0.9), (ub, yt + 0.5, z1 + 0.9), c("blanc_casse"), name="Collier")
        # bandeau de verre clair au niveau haut (reflet du ciel), montants et nervures sur les deux faces
        for face in (("z", 1, z1), ("z", -1, z0)):
            if niveaux >= 2:
                _sur_face(b, face, xa, xb, yv0 + hn + 0.35, yv1, -0.05, 0.1, verre2, material="Glass",
                          collide=False, name="VerreHaut")
            n = max(2, round((xb - xa) / pas))
            for k in range(1, n):
                u = xa + k * (xb - xa) / n
                if k % 4 == 0:
                    _sur_face(b, face, u - 0.5, u + 0.5, yb + e_dalle, yv1, -0.05, 0.5, "cadre_blanc", name="Nervure")
                else:
                    _sur_face(b, face, u - 0.25, u + 0.25, yv0, yv1, -0.05, 0.25, "cadre_blanc", collide=False,
                              name="Montant")


def tours_jumelles(b, variant=0, passage=116.0, largeur_tour=44.0, profondeur=38.0, hauteurs=(120.0, 134.0),
                   y_passerelle=46.0):
    """Repère final : deux tours de bureaux de verre bleu-violet, reliées par une passerelle au-dessus de la route.

    Posé sans rotation, origine au centre de la route au pied de la façade avant (z = 0) ; la grande façade
    regarde +Z, la structure occupe z ∈ [-profondeur, 0] (auvents d'entrée jusqu'à z = +3,2). Tour gauche
    x ∈ [-(passage/2 + largeur_tour), -passage/2], tour droite symétrique. Chaque tour = deux prismes décalés
    (silhouette en gradins) plus un couronnement vitré en retrait de 8 au sommet du prisme principal :
    - tour gauche : prisme principal côté route (sommet à hauteurs[0]), aile basse à l'extérieur et à l'arrière ;
    - tour droite : prisme principal à l'extérieur, en retrait (sommet à hauteurs[1], mât d'antenne de 14 au-dessus),
      aile basse côté route, à l'avant.
    Verre en trois tons, quadrillage de montants blancs (tous les ≈ 4,6 sur l'avant et côté route, ≈ 9,5 ailleurs),
    lignes d'étage tous les 6 (bandeau technique tous les 5 étages), reflets en escalier, néons cyan aux angles
    avant côté route et sur les couronnes, halls vitrés clairs sur deux niveaux, auvents à liseré cyan, galerie
    à colonnes côté route. Passerelle basse sur deux niveaux (dessous à `y_passerelle`, 13 de haut, 16 de
    profondeur, sous-face lavande à néons), passerelle haute plus fine (dessous à y_passerelle + 42, 8 de haut).
    `|x| < passage / 2` reste entièrement libre du sol jusqu'à `y_passerelle` (le néon sous la passerelle est
    le point le plus bas, à y_passerelle exactement). Variantes impaires : verre plus bleu."""
    rng = b.rng
    xi = passage / 2
    W = largeur_tour
    D = profondeur
    hL, hR = float(hauteurs[0]), float(hauteurs[1])
    verre = ("vitre_violette", "vitre_bleue")[variant % 2]

    def ronde(v):
        return float(round(v))

    # prismes (enveloppes) ; denses = faces vues par les joueurs (avant et côté route)
    hc = 8.0                                       # couronnement vitré en retrait au sommet des prismes principaux
    LA = _Prisme("TourG/Principal", -(xi + ronde(0.773 * W)), -xi, -ronde(0.842 * D), 0.0, hL - hc, ("avant", "droite"))
    LB = _Prisme("TourG/Aile", -(xi + W), -(xi + ronde(0.636 * W)), -D, -6.0, ronde(0.78 * hL), ("avant",))
    RA = _Prisme("TourD/Principal", xi + 8.0, xi + W, -(D - 2.0), -4.0, hR - hc, ("avant",))
    RB = _Prisme("TourD/Aile", xi, xi + 14.0, -D, 0.0, ronde(0.78 * hR), ("avant", "gauche"))
    LC = _Prisme("TourG/Couronnement", LA.x0 + 5.0, LA.x1 - 4.0, LA.z0 + 5.0, LA.z1 - 4.0, hL, ("avant", "droite"),
                 y0=LA.h - 0.8, transfert=False)
    RC = _Prisme("TourD/Couronnement", RA.x0 + 4.0, RA.x1 - 5.0, RA.z0 + 5.0, RA.z1 - 4.0, hR, ("avant", "gauche"),
                 y0=RA.h - 0.8, transfert=False)
    tours = {"G": (LA, LB), "D": (RA, RB)}

    with b.group("Tours"):
        for cle, (A, B_) in tours.items():
            _prisme_verre(b, A, [B_], verre, rng, decal=0 if cle == "G" else 3)
            _prisme_verre(b, B_, [A], verre, rng, decal=2 if cle == "G" else 1, neon_couronne=True)
        for Cn in (LC, RC):
            _prisme_verre(b, Cn, [], verre, rng, pas_dense=4.4, reflets=False, neon_couronne=True)

        # socle : dalle stud autour du pied des tours (jamais dans |x| < passage / 2)
        for s in (-1, 1):
            xa, xb = sorted((s * xi, s * (xi + W + 2)))
            b.box((xa, 0, -D), (xb, 0.6, 2.0), c("dalle_claire"), studs="top", name="Socle")

        # halls vitrés sur deux niveaux, auvents à liseré cyan, entrées
        hall_LA = _hall(b, LA, ("avant", "droite"), rng, cote_passage="droite")
        _hall(b, LB, ("avant",), rng)
        _hall(b, RA, ("avant",), rng)
        hall_RB = _hall(b, RB, ("avant", "gauche"), rng, cote_passage="gauche")
        with b.group("Entrees"):
            # entrée principale de chaque tour, face aux joueurs (+Z), grand auvent jusqu'à z = +3
            xc = (LA.x0 + LA.x1) / 2
            f = ("z", 1, LA.cz1 - 1.5)
            _entree(b, f, xc, 8.0)
            _auvent(b, ("z", 1, LA.cz1 - 1.5), xc - 10, xc + 10, 7.4, 4.5 + 0.3)
            xc = (RA.x0 + RA.x1) / 2
            f = ("z", 1, RA.cz1 - 1.5)
            _entree(b, f, xc, 8.0)
            _auvent(b, f, xc - 10, xc + 10, 7.4, 3.0 - (RA.cz1 - 1.5))
            # côté route : galerie sous auvent continu, portes au centre
            for P, hall, s in ((LA, hall_LA, 1), (RB, hall_RB, -1)):
                plan_v = hall[1] if s > 0 else hall[0]
                f = ("x", s, plan_v)
                zc = (P.z0 + P.z1) / 2
                _entree(b, f, zc, 6.0)
                L = abs((-s * xi) - plan_v) - 0.3       # jusqu'à |x| = xi + 0,5 (néon compris : xi + 0,3)
                _auvent(b, f, P.cz0 + 1.7, P.cz1 - 1.7, 7.4, L - 0.2)

        # bandes lumineuses verticales cyan à l'angle avant côté route de chaque tour
        with b.group("Neons"):
            for P, xa_, xb_ in ((LA, LA.cx1 - 1.2, LA.cx1 - 0.7), (RB, RB.cx0 + 0.7, RB.cx0 + 1.2)):
                b.box((xa_, Y_SOCLE, P.cz1 - 0.05), (xb_, P.h - 3.0, P.cz1 + 0.4), c("neon_cyan"), material="Neon",
                      collide=False, shadow=False, name="NeonAngle")

        # jardinières blanches à haie taillée devant les halls (sur le socle, jamais dans |x| < passage / 2)
        with b.group("Jardinieres"):
            xcL, xcR = (LA.x0 + LA.x1) / 2, (RA.x0 + RA.x1) / 2
            for xa_, xb_, za_ in ((LA.x0 + 1.0, xcL - 11.0, 0.2), (xcL + 11.0, LA.x1 - 2.0, 0.2),
                                  (RB.x0 + 2.0, RB.x1 - 1.0, 0.2), (xcR + 11.0, RA.x1 - 1.0, 0.2),
                                  (LB.x0 + 1.0, LA.x0 - 1.0, LB.z1 + 0.6)):
                if xb_ - xa_ < 2.0:
                    continue
                b.box((xa_, 0.6, za_), (xb_, 1.6, za_ + 1.8), c("blanc_casse"), name="Jardiniere")
                b.box((xa_ + 0.2, 1.6, za_ + 0.2), (xb_ - 0.2, 2.8, za_ + 1.6), vr("haie", rng, 0.04),
                      material="Grass", studs="top", collide=False, name="Haie")

        # passerelles
        zc = -D / 2
        with b.group("PasserelleBasse"):
            _passerelle(b, -xi - 0.6, xi + 0.6, y_passerelle, 20.0, zc - 10, zc + 10, verre,
                        "vitre_violette_claire", niveaux=3, pas=5.3, x_col=xi)
        with b.group("PasserelleHaute"):
            y2 = float(round(0.78 * hL))
            _passerelle(b, -xi - 0.6, xi + 0.6, y2, 8.0, zc - 5, zc + 5, "vitre_violette_claire", "vitre_claire",
                        niveaux=1, pas=7.3, x_col=xi, sous_face=False)
            b.box((-xi + 0.5, y2 + 0.05, zc - 0.3), (xi - 0.5, y2 + 0.4, zc + 0.3), c("neon_cyan"), material="Neon",
                  collide=False, shadow=False, name="NeonAxe")

        # toits : édicules, climatiseurs, feux d'obstacle
        _toiture(b, LC, rng, balisage=True, machinerie=1)
        _toiture(b, LB, rng, machinerie=1, edicule=False)
        _toiture(b, RC, rng, balisage=True, machinerie=0)
        _toiture(b, RB, rng, machinerie=1, edicule=False)
        # mât d'antenne sur la tour haute (feu rouge au sommet)
        with b.group("TourD/Antenne"):
            xa_, za_ = (RC.x0 + RC.x1) / 2 + 3.0, (RC.z0 + RC.z1) / 2
            b.box((xa_ - 1.5, hR - 0.8, za_ - 1.5), (xa_ + 1.5, hR + 1.2, za_ + 1.5), c("acier"), studs="top",
                  name="SocleAntenne")
            b.cyl((xa_, hR + 1.2 + 6.0, za_), 0.45, 12.0, c("blanc"), collide=False, name="Antenne")
            b.cyl((xa_, hR + 1.2 + 4.0, za_), 0.8, 0.6, c("acier"), collide=False, name="Bague")
            b.box((xa_ - 0.5, hR + 13.2, za_ - 0.5), (xa_ + 0.5, hR + 14.2, za_ + 0.5), col(ROUGE_BALISAGE),
                  material="Neon", collide=False, shadow=False, name="FeuObstacle")

    return {"emprise": (passage + 2 * W, D), "hauteur": max(hL, hR + 14.2)}


# ---------------------------------------------------------------------------
# Dortoirs de brique (référence 2)
# ---------------------------------------------------------------------------

def _toit_croupe(b, X0, X1, Z0, Z1, y, h, n, rng, couleurs=("toit_ardoise", "toit_ardoise_claire", "toit_ardoise")):
    """Toit en croupe en `n` assises : à chaque assise, quatre coins (avant, arrière et deux croupes) autour d'un
    bloc central ; les pans sont continus et les arêtiers dessinent un petit escalier (style stud).
    Base X0..X1 × Z0..Z1 à la hauteur y, faîtage à y + h, faîtage parallèle à X."""
    t = (Z1 - Z0) / (2 * n)
    dy = h / n
    with b.group("Toit"):
        for k in range(n):
            xa, xb, za, zb = X0 + k * t, X1 - k * t, Z0 + k * t, Z1 - k * t
            y0, y1 = y + k * dy, y + (k + 1) * dy
            teinte = vr(couleurs[k % len(couleurs)], rng, 0.03)
            if xb - xa - 2 * t > 0.1:
                b.wedge((xa + t, y0, za), (xb - t, y1, za + t), teinte, down="-z", studs="top", name="PanAvant")
                b.wedge((xa + t, y0, zb - t), (xb - t, y1, zb), teinte, down="+z", studs="top", name="PanArriere")
            b.wedge((xa, y0, za), (xa + t, y1, zb), teinte, down="-x", studs="top", name="Croupe")
            b.wedge((xb - t, y0, za), (xb, y1, zb), teinte, down="+x", studs="top", name="Croupe")
            if zb - za - 2 * t > 0.1 and xb - xa - 2 * t > 0.1:
                b.box((xa + t, y0, za + t), (xb - t, y1, zb - t), teinte, studs="top", name="Coeur")
        # faîtage
        k = n - 1
        xa, xb = X0 + n * t, X1 - n * t
        zm = (Z0 + Z1) / 2
        if xb - xa > 0.5:
            b.box((xa - 0.2, y + h - 0.1, zm - 0.4), (xb + 0.2, y + h + 0.4, zm + 0.4), c("toit_ardoise_fonce"),
                  name="Faitage")


def _fenetre(b, face, ua, ub, ya, yb, *, cadre="cadre_blanc", verre="vitre_nuit", e=0.0, cad=0.3, **kw):
    """Fenêtre sur une face : cadre blanc (saillie e + 0,15) et vitre (saillie e + 0,25) un peu plus petite."""
    _sur_face(b, face, ua - cad, ub + cad, ya - cad, yb + cad, e - 0.05, e + 0.15, cadre, collide=False,
              name="Cadre")
    mat = "SmoothPlastic" if verre == "fenetre_lumiere" else "Glass"
    _sur_face(b, face, ua, ub, ya, yb, e - 0.05, e + 0.25, verre, material=mat, collide=False, name="Vitre", **kw)


def _verre_fenetre(rng, p_lumiere=0.18):
    return "fenetre_lumiere" if rng.random() < p_lumiere else "vitre_nuit"


def _balcon(b, xa, xb, y, z_mur, prof, *, cotes=(True, True), garde=True):
    """Balcon filant blanc (dalle stud, rive blanche) à garde-corps de verre clair (transparence 0,4)."""
    zf = z_mur - prof
    b.box((xa, y - 0.8, zf), (xb, y, z_mur), c("blanc"), studs="top", name="Balcon")
    if not garde:
        return
    b.box((xa + 0.05, y, zf + 0.05), (xb - 0.05, y + 1.8, zf + 0.3), c("vitre_claire"), material="Glass",
          transparency=0.4, collide=False, name="GardeCorps")
    b.box((xa, y + 1.8, zf), (xb, y + 2.1, zf + 0.4), c("cadre_blanc"), collide=False, name="MainCourante")
    for ok, x in zip(cotes, (xa, xb)):
        if ok:
            xa_, xb_ = (x + 0.05, x + 0.3) if x == xa else (x - 0.3, x - 0.05)
            b.box((xa_, y, zf + 0.3), (xb_, y + 1.8, z_mur), c("vitre_claire"), material="Glass", transparency=0.4,
                  collide=False, name="GardeCorps")


def _portique(b, xc, larg, z_mur, z_av, y_haut, *, texte=None):
    """Portique d'entrée blanc : colonnes, chapiteau saillant, double porte vitrée encadrée de blanc."""
    with b.group("Portique"):
        b.box((xc - larg / 2, y_haut - 0.9, z_av), (xc + larg / 2, y_haut + 0.5, z_mur), c("blanc"), studs="top",
              name="Chapiteau")
        n = 4 if larg >= 9 else 2
        for k in range(n):
            x = xc - larg / 2 + 0.9 + k * (larg - 1.8) / (n - 1)
            b.box((x - 0.4, 1.0, z_av + 0.5), (x + 0.4, y_haut - 0.9, z_av + 1.3), c("blanc_casse"), name="Colonne")
        face = ("z", -1, z_mur)
        _sur_face(b, face, xc - 2.6, xc + 2.6, 1.0, 5.4, -0.05, 0.15, "cadre_blanc", collide=False, name="Cadre")
        for sx in (-1, 1):
            xa, xb = sorted((xc + sx * 0.15, xc + sx * 2.3))
            _sur_face(b, face, xa, xb, 1.0, 5.1, 0.1, 0.25, "vitre_claire", material="Glass", collide=False,
                      name="Porte")
        if texte:
            p = b.box((xc - larg / 2 + 1.0, y_haut - 0.7, z_av - 0.12), (xc + larg / 2 - 1.0, y_haut + 0.3, z_av),
                      c("violet"), collide=False, shadow=False, name="Plaque")
            _label(p, texte, face="Front", couleur=(255, 255, 255))


def dortoir(b, variant=0, largeur=40.0, profondeur=22.0, etages=4, simple=False):
    """Résidence de brique rouge à balcons blancs et toit en croupe brun-gris (référence 2).

    Emprise exacte largeur × profondeur (X × Z) ; socle de 1, étages de 5,5 (4 étages : murs à 23, faîtage ≈ 30,6).
    L'avant (-Z) porte des balcons filants blancs à garde-corps de verre et un portique d'entrée au centre du
    rez-de-chaussée. Le toit déborde de ≤ 1,5 au-delà de l'emprise sur les côtés et l'arrière.
    v0 balcons sur toute la largeur ; v1 deux ailes, cage d'escalier vitrée en retrait au centre ; v2 balcons au
    centre, travées d'about en saillie à pilastres blancs. `simple=True` : arrière-plan (≤ 70 pièces)."""
    rng = b.rng
    v = variant % 3
    w, d = float(largeur), float(profondeur)
    H0, fh = 1.0, 5.5
    n = max(2, int(etages))
    H = H0 + n * fh
    bx0, bx1 = -w / 2 + 0.5, w / 2 - 0.5
    zav = -d / 2                                  # bord avant de l'emprise
    zm = zav + 2.5                                # mur avant (les balcons avancent de 2)
    bz1 = d / 2 - 0.5
    brique = ("brique", "brique_claire", "brique")[variant % 3]
    briq = vr(brique, rng, 0.03)

    with b.group("Dortoir"):
        b.box((-w / 2, 0, zav + 0.8), (w / 2, H0, d / 2), c("beton_clair"), studs="top", name="Socle")
        soub = vr("brique_fonce", rng, 0.03)
        b.box((-w / 2 + 0.5, 0, zav), (w / 2 - 0.5, 0.5, zav + 0.8), c("beton"), studs="top", name="Marche")

        # --- volumes de brique (segments de façade) ---
        if v == 1 and not simple:
            cg = 4.5                                  # demi-largeur de la cage d'escalier
            segs = [(bx0, -cg, zm, "balcons"), (-cg, cg, zm + 2.5, "cage"), (cg, bx1, zm, "balcons")]
        elif v == 2 and not simple:
            xe = bx1 - 7.5
            segs = [(bx0, -xe, zav + 1.0, "baie"), (-xe, xe, zm, "balcons"), (xe, bx1, zav + 1.0, "baie")]
        else:
            segs = [(bx0, bx1, zm, "balcons")]
        for xa, xb, zf, kind in segs:
            mat = "SmoothPlastic" if kind == "cage" else "Brick"
            couleur = c("blanc") if kind == "cage" else briq
            b.box((xa, H0, zf), (xb, H, bz1), couleur, material=mat, name="Volume")
            if kind != "cage":
                # bande de brique sombre au rez-de-chaussée (pixel) et filet clair sous la corniche
                b.box((xa - 0.1, H0, zf - 0.1), (xb + 0.1, H0 + fh - 0.6, bz1 + 0.1), soub, material="Brick",
                      name="Soubassement")
        # corniche blanche sous le toit
        zf_min = min(s_[2] for s_ in segs)
        b.box((bx0 - 0.3, H - 1.2, zf_min - 0.3), (bx1 + 0.3, H, bz1 + 0.3), c("blanc"), name="Corniche")

        # --- toit en croupe ---
        X0, X1 = -w / 2 - 1.0, w / 2 + 1.0
        Z0, Z1 = zav - 0.5, d / 2 + 1.5
        b.box((X0, H, Z0), (X1, H + 0.6, Z1), c("toit_ardoise_fonce"), name="Rive")
        _toit_croupe(b, X0, X1, Z0, Z1, H + 0.6, 7.0 if n >= 4 else 5.0, 4, rng)

        if simple:
            # bandes de balcons blancs, rangées de fenêtres sombres, une porte
            for k in range(n):
                y = H0 + k * fh
                face = ("z", -1, zm)
                _sur_face(b, face, bx0 + 1.5, bx1 - 1.5, y + 1.0, y + 4.4, -0.05, 0.2,
                          "vitre_nuit" if k else "vitre_bleue_fonce", material="Glass", collide=False, name="Fenetres")
                if k:
                    _balcon(b, bx0 + 0.5, bx1 - 0.5, y, zm, 2.0, garde=(k % 2 == 1))
                for sx in (-1, 1):
                    xf = bx1 if sx > 0 else bx0
                    _sur_face(b, ("x", sx, xf), zm + 3, bz1 - 3, y + 1.4, y + 4.2, -0.05, 0.2, "vitre_nuit",
                              material="Glass", collide=False, name="Fenetres")
            _sur_face(b, ("z", -1, zm), -2.5, 2.5, H0, H0 + 4.6, 0.15, 0.35, "cadre_blanc", name="Porte")
            _sur_face(b, ("z", -1, zm), -2.0, 2.0, H0, H0 + 4.2, 0.3, 0.45, "vitre_claire", material="Glass",
                      collide=False, name="Porte")
            return {"emprise": (w, d), "hauteur": H + 0.6 + 7.0 + 0.4}

        # --- façade avant : fenêtres, portes-fenêtres, balcons ---
        for xa, xb, zf, kind in segs:
            face = ("z", -1, zf)
            if kind == "cage":
                # cage d'escalier vitrée : verre clair, cadre blanc, paliers et volées en diagonale
                _sur_face(b, face, xa + 0.9, xb - 0.9, H0 + 0.6, H - 1.6, -0.05, 0.12, "vitre_claire", material="Glass",
                          name="CageVerre")
                for k in range(1, n):
                    y = H0 + k * fh
                    _sur_face(b, face, xa + 0.7, xb - 0.7, y - 0.3, y + 0.3, -0.05, 0.3, "cadre_blanc",
                              collide=False, name="Palier")
                for k in range(n):
                    y = H0 + k * fh
                    L = math.hypot(xb - xa - 2.4, fh - 1.2)
                    ang = math.degrees(math.atan2(fh - 1.2, xb - xa - 2.4)) * (1 if k % 2 == 0 else -1)
                    b.part("block", (L, 0.7, 0.12), ((xa + xb) / 2, y + fh / 2, zf - 0.17), rot_z(ang),
                           c("gris_acier"), collide=False, name="Volee")
                continue
            nb = max(1, round((xb - xa) / 7.6))
            bay = (xb - xa) / nb
            ww = min(5.4, bay - 2.0)
            for i in range(nb):
                xc = xa + (i + 0.5) * bay
                for k in range(n):
                    y = H0 + k * fh
                    if k == 0 and abs(xc) < 5.5 and kind == "balcons":
                        continue                                  # portique
                    if k == 0:
                        _fenetre(b, face, xc - ww / 2, xc + ww / 2, y + 1.2, y + 4.2, verre=_verre_fenetre(rng), e=0.1)
                    else:
                        _fenetre(b, face, xc - ww / 2, xc + ww / 2, y + 0.0, y + 4.3,
                                 verre=_verre_fenetre(rng, 0.25 if kind == "baie" else 0.15))
            if kind == "balcons":
                for k in range(1, n):
                    y = H0 + k * fh
                    if v == 1:
                        cotes = (xa == bx0, xb == bx1)
                    elif v == 2:
                        cotes = (False, False)
                    else:
                        cotes = (True, True)
                    _balcon(b, xa, xb, y, zf, 2.0, cotes=cotes)
                    # quelques jardinières vertes sur les balcons
                    if rng.random() < 0.6:
                        xp = float(rng.uniform(xa + 1.5, xb - 1.5))
                        b.box((xp - 0.5, y, zf - 1.3), (xp + 0.5, y + 1.0, zf - 0.3), tirer(["feuille_claire", "haie_claire",
                              "feuille_pale"], rng), collide=False, name="Plante")
                # refends blancs verticaux à travers les balcons (référence 2)
                bords = [xa + i * bay for i in range(1, nb)]
                if len(bords) > 2:
                    bords = [bords[0], bords[-1]]
                for xr in bords:
                    b.box((xr - 0.3, H0 + fh - 0.8, zf - 1.8), (xr + 0.3, H - 1.2, zf), c("blanc"), name="Refend")
            if kind == "baie":
                # pilastres blancs aux angles de la travée en saillie
                for x in (xa, xb):
                    b.box((x - 0.5, H0, zf - 0.2), (x + 0.5, H - 1.2, zf + 0.8), c("blanc"), name="Pilastre")
        # pilastres blancs aux angles avant du volume (référence 2)
        if v != 2:
            for x, sx in ((bx0, -1), (bx1, 1)):
                b.box((x - sx * 0.6 if sx > 0 else x - 0.3, H0, zm - 0.3), (x + 0.3 if sx > 0 else x + 0.6, H - 1.2, zm + 0.8),
                      c("blanc"), name="Pilastre")
        # portique d'entrée au centre
        z_av = zav + 0.4
        z_m = segs[1][2] if v == 1 else zm
        _portique(b, 0.0, 10.0 if v != 1 else 9.0, z_m, z_av, H0 + fh, texte="DORTOIRS" if v == 0 else None)

        # --- côtés : deux colonnes de fenêtres (bande blanche + vitres par étage) ---
        for sx in (-1, 1):
            xf = bx1 if sx > 0 else bx0
            face = ("x", sx, xf)
            zf_c = segs[-1][2] if sx > 0 else segs[0][2]
            for zc in (zf_c + 0.3 * (bz1 - zf_c), zf_c + 0.72 * (bz1 - zf_c)):
                _sur_face(b, face, zc - 1.9, zc + 1.9, H0 + 0.9, H - 1.6, -0.05, 0.2, "blanc", collide=False,
                          name="BandeFenetres")
                for k in range(n):
                    y = H0 + k * fh
                    vt = _verre_fenetre(rng, 0.15)
                    _sur_face(b, face, zc - 1.5, zc + 1.5, y + 1.3, y + 4.4, -0.05, 0.32, vt,
                              material="SmoothPlastic" if vt == "fenetre_lumiere" else "Glass", collide=False,
                              name="Vitre")
        # --- arrière : rangées de fenêtres et trois meneaux ---
        face = ("z", 1, bz1)
        for k in range(n):
            y = H0 + k * fh
            _sur_face(b, face, bx0 + 2.5, bx1 - 2.5, y + 1.4, y + 4.2, -0.05, 0.2, "vitre_nuit", material="Glass",
                      collide=False, name="Fenetres")
        for k in range(1, 5):
            x = bx0 + k * (bx1 - bx0) / 5
            _sur_face(b, face, x - 0.3, x + 0.3, H0 + 1.0, H - 1.2, -0.05, 0.3, "blanc", collide=False, name="Meneau")
        # --- pixels de brique (claire / foncée) sur les côtés et l'avant ---
        for sx in (-1, 1):
            xf = bx1 if sx > 0 else bx0
            zf_c = segs[-1][2] if sx > 0 else segs[0][2]
            zc = zf_c + (bz1 - zf_c) * 0.51
            for k in range(1, n):
                if rng.random() < 0.75:
                    yc = H0 + k * fh + float(rng.uniform(0.6, 3.2))
                    dz = float(rng.uniform(-0.6, 0.6))
                    _sur_face(b, ("x", sx, xf), zc + dz - 1.5, zc + dz + 1.5, yc, yc + 1.0, -0.05, 0.1,
                              tirer(["brique_claire", "brique_fonce"], rng), material="Brick", collide=False,
                              name="Pixel")
    return {"emprise": (w, d), "hauteur": H + 0.6 + 7.0 + 0.4}


# ---------------------------------------------------------------------------
# Bâtiments de cours (référence 3)
# ---------------------------------------------------------------------------

def _volee(b, face, xa, xb, y, fh, sens):
    """Volée d'escalier en diagonale dessinée sur une façade vitrée (plan `face`), avec palier blanc."""
    L = math.hypot(xb - xa, fh - 1.0)
    ang = math.degrees(math.atan2(fh - 1.0, xb - xa)) * sens
    axe, s, plan = face[0], face[1], face[2]
    zc = plan + s * 0.2
    b.part("block", (L, 0.8, 0.15), ((xa + xb) / 2, y + fh / 2, zc), rot_z(ang), c("gris_acier"), collide=False,
           name="Volee")


def batiment_cours(b, variant=0, largeur=52.0, profondeur=24.0, hauteur=26.0):
    """Bâtiment de cours moderne : ossature de béton blanc, grandes grilles vitrées en deux tons, dalles d'étage
    tous les 6,5 en saillie, tour d'escalier vitrée pleine hauteur, auvent d'entrée à liseré cyan au centre,
    bande verticale violette, toit stud à acrotère, panneaux solaires et climatiseurs.
    v0 bloc long, atrium à l'extrémité +X (à gauche vu de la route) ; v1 galerie vitrée en façade au 2e niveau
    (saillie 2,5) et atrium à l'extrémité -X. Emprise largeur × profondeur, `hauteur` = niveau du toit."""
    rng = b.rng
    v = variant % 2
    W, D, Hr = float(largeur), float(profondeur), float(hauteur)
    n = max(2, int(Hr // 6.5))
    g = Hr - (n - 1) * 6.5                         # rez-de-chaussée (plus haut si la hauteur le demande)
    niveaux = [0.0] + [g + k * 6.5 for k in range(n - 1)] + [Hr]
    zf = -D / 2 + 3.0                              # façade avant (auvent, atrium et galerie avancent jusqu'à -D/2)
    zb = D / 2 - 0.4                               # façade arrière (meneaux et soubassement restent dans l'emprise)
    aw = 9.0                                       # largeur de la tour d'escalier vitrée
    if v == 0:
        ax0, ax1 = W / 2 - aw, W / 2
        bx0, bx1 = -W / 2 + 0.3, ax0
    else:
        ax0, ax1 = -W / 2, -W / 2 + aw
        bx0, bx1 = ax1, W / 2 - 0.3
    gx0, gx1 = (bx0 + 3.0, bx1 - 0.6) if v == 0 else (bx0 + 0.6, bx1 - 3.0)
    verre = ("vitre_bleue", "vitre_ciel")[v]
    blanc = vr("blanc_casse", rng, 0.02)

    with b.group("Cours"):
        # volume principal et soubassement
        b.box((bx0, 0, zf), (bx1, Hr, zb), blanc, studs="top", name="Volume")
        b.box((bx0 - 0.2, 0, zf - 0.2), (bx1 + 0.2, 0.8, zb + 0.2), c("beton"), name="Soubassement")
        # acrotère stud
        e = 0.8
        for (xa, xb_, za, zb_) in ((bx0, bx1, zf, zf + e), (bx0, bx1, zb - e, zb), (bx0, bx0 + e, zf + e, zb - e),
                                   (bx1 - e, bx1, zf + e, zb - e)):
            b.box((xa, Hr, za), (xb_, Hr + 1.4, zb_), c("blanc"), studs="top", name="Acrotere")

        # --- façade avant : grille vitrée ---
        face = ("z", -1, zf)
        _sur_face(b, face, gx0, gx1, 0.8, Hr - 1.2, -0.05, 0.1, verre, material="Glass", reflectance=0.2,
                  name="Vitrage")
        for k in range(len(niveaux) - 1):
            y_top = niveaux[k + 1]
            # imposte claire en haut de chaque niveau (deuxième ton)
            _sur_face(b, face, gx0 + 0.15, gx1 - 0.15, y_top - 2.4, y_top - 0.7, -0.05, 0.2, "vitre_claire",
                      material="Glass", collide=False, name="Imposte")
        # dalles d'étage en saillie (casquettes) : ombres horizontales franches
        for y in niveaux[1:-1]:
            _sur_face(b, face, gx0 - 0.4, gx1 + 0.4, y - 0.7, y + 0.5, -0.05, 0.9, "blanc", name="Dalle")
        _sur_face(b, face, gx0 - 0.4, gx1 + 0.4, Hr - 1.2, Hr, -0.05, 0.9, "blanc", studs="top", name="Dalle")
        nm = max(2, round((gx1 - gx0) / 4.0))
        for k in range(1, nm):
            x = gx0 + k * (gx1 - gx0) / nm
            _sur_face(b, face, x - 0.25, x + 0.25, 0.8, Hr - 1.2, -0.05, 0.3, "cadre_blanc", collide=False,
                      name="Montant")

        # --- entrée : auvent à liseré cyan, portes, bande violette ---
        with b.group("Entree"):
            y_a = 5.0
            b.box((-7.5, y_a, -D / 2 + 0.2), (7.5, y_a + 0.8, zf), c("blanc"), studs="top", name="Auvent")
            b.box((-7.6, y_a + 0.15, -D / 2), (7.6, y_a + 0.55, -D / 2 + 0.2), c("neon_cyan"), material="Neon",
                  collide=False, shadow=False, name="LisereAuvent")
            for x in (-6.8, 6.8):
                b.box((x - 0.3, 0, -D / 2 + 0.8), (x + 0.3, y_a, -D / 2 + 1.4), c("blanc"), name="Poteau")
            _sur_face(b, face, -4.4, 4.4, 0.8, 4.6, 0.05, 0.3, "cadre_blanc", name="CadrePortes")
            for xa in (-4.0, 0.15):
                _sur_face(b, face, xa, xa + 3.85, 0.9, 4.3, 0.25, 0.42, "vitre_nuit", material="Glass", collide=False,
                          name="Porte")
            xv = -11.0
            _sur_face(b, face, xv - 1.2, xv + 1.2, 0.0, Hr + 1.0, -0.05, 1.2, "violet", name="BandeViolette")
            _sur_face(b, face, xv - 0.2, xv + 0.2, 1.5, Hr + 0.3, 1.2, 1.35, "neon_violet", material="Neon",
                      collide=False, shadow=False, name="NeonViolet")

        # --- galerie vitrée en façade au 2e niveau (v1, référence 3) ---
        if v == 1:
            with b.group("Galerie"):
                y0, y1 = niveaux[1], niveaux[2]
                xa, xb = -8.6, gx1 - 1.0
                zg = -D / 2 + 0.5
                b.box((xa, y0 - 0.8, zg), (xb, y0 + 0.2, zf), c("blanc"), name="Plancher")
                b.box((xa, y1 - 0.8, zg), (xb, y1, zf), c("blanc"), studs="top", name="Toit")
                b.box((xa + 0.1, y0 + 0.2, zg + 0.1), (xb - 0.1, y1 - 0.8, zg + 0.4), c("vitre_claire"),
                      material="Glass", transparency=0.3, collide=False, name="Verre")
                for x in (xa, xb - 0.4):
                    b.box((x, y0 + 0.2, zg), (x + 0.4, y1 - 0.8, zg + 0.5), c("cadre_blanc"), name="Montant")
                nm = max(2, round((xb - xa) / 3.0))
                for k in range(1, nm):
                    x = xa + k * (xb - xa) / nm
                    b.box((x - 0.2, y0 + 0.2, zg - 0.05), (x + 0.2, y1 - 0.8, zg + 0.5), c("cadre_blanc"),
                          collide=False, name="Meneau")
                b.box((xa, y0 + 1.2, zg - 0.05), (xb, y0 + 1.5, zg + 0.5), c("cadre_blanc"), collide=False,
                      name="Lisse")
                for x in (xa + 0.05, xb - 0.35):
                    b.box((x, y0 + 0.2, zg + 0.4), (x + 0.3, y1 - 0.8, zf), c("vitre_claire"), material="Glass",
                          transparency=0.3, collide=False, name="VerreBout")

        # --- tour d'escalier vitrée (atrium) ---
        with b.group("Atrium"):
            ha = Hr + 4.0
            za0 = -D / 2 + 1.0
            b.box((ax0 + 0.4, 0, za0 + 0.4), (ax1 - 0.4, ha, zb - 0.4), c("vitre_claire"), material="Glass",
                  reflectance=0.2, name="Verre")
            for x in (ax0, ax1 - 0.8):
                for z in (za0, zb - 0.8):
                    b.box((x, 0, z), (x + 0.8, ha, z + 0.8), c("blanc"), name="Poteau")
            b.box((ax0, ha, za0), (ax1, ha + 1.0, zb), c("blanc"), studs="top", name="Chapeau")
            fa = ("z", -1, za0 + 0.4)
            for k in range(len(niveaux) - 1):
                y = niveaux[k]
                hk = niveaux[k + 1] - y
                _volee(b, fa, ax0 + 1.2, ax1 - 1.2, y, hk, 1 if k % 2 == 0 else -1)
                if k:
                    _sur_face(b, fa, ax0 + 0.8, ax1 - 0.8, y - 0.35, y + 0.35, -0.05, 0.3, "blanc", collide=False,
                              name="Palier")
            # côté visible de la tour (vers l'extérieur du bâtiment) : lignes d'étage
            sx = 1 if v == 0 else -1
            fx = ("x", sx, ax1 - 0.4 if sx > 0 else ax0 + 0.4)
            for y in niveaux[1:-1]:
                _sur_face(b, fx, za0 + 0.8, zb - 0.8, y - 0.35, y + 0.35, -0.05, 0.3, "blanc", collide=False,
                          name="Palier")

        # --- pignon opposé : fenêtres par étage ---
        sx = -1 if v == 0 else 1
        fx = ("x", sx, bx0 if sx < 0 else bx1)
        for k in range(len(niveaux) - 1):
            y = niveaux[k]
            for zc in (zf + 5.5, zb - 5.5):
                _sur_face(b, fx, zc - 2.5, zc + 2.5, y + 1.4, min(y + 5.0, niveaux[k + 1] - 1.0), -0.05, 0.2, verre,
                          material="Glass", collide=False, name="Fenetre")
        # --- arrière : bandeaux vitrés et dalles ---
        fz = ("z", 1, zb)
        for k in range(len(niveaux) - 1):
            y = niveaux[k]
            _sur_face(b, fz, bx0 + 2.0, bx1 - 2.0, y + 1.4, niveaux[k + 1] - 1.4, -0.05, 0.15, verre, material="Glass",
                      collide=False, name="Bandeau")
        nm = max(2, round((bx1 - bx0 - 4) / 8.0))
        for k in range(1, nm):
            x = bx0 + 2 + k * (bx1 - bx0 - 4) / nm
            _sur_face(b, fz, x - 0.3, x + 0.3, 1.0, Hr - 1.0, -0.05, 0.3, "blanc", collide=False, name="Meneau")

        # --- toit : panneaux solaires inclinés, climatiseurs ---
        with b.group("Toit"):
            xs = [bx0 + 4 + k * 7.0 for k in range(int((bx1 - bx0 - 8) // 7.0))]
            for x in xs[:6]:
                for z in (zf + 4.0,):
                    b.box((x, Hr, z), (x + 6.0, Hr + 0.6, z + 4.0), c("acier"), name="Support")
                    b.wedge((x, Hr + 0.6, z), (x + 6.0, Hr + 2.0, z + 4.0), col(PANNEAU_SOLAIRE), down="-z",
                            reflectance=0.2, name="PanneauSolaire")
            for k, x in enumerate(xs[:3]):
                z = zb - 6.0
                b.box((x + 1, Hr, z), (x + 4.5, Hr + 2.2, z + 3.0), c("acier"), studs="top", name="Clim")
                b.cyl((x + 2.75, Hr + 2.3, z + 1.5), 1.1, 0.2, c("gris_acier"), collide=False, name="Ventilateur")
    return {"emprise": (W, D), "hauteur": Hr + 5.0}


# ---------------------------------------------------------------------------
# Halle d'entraînement à verrière en berceau (référence 3)
# ---------------------------------------------------------------------------

def halle_entrainement(b, variant=0, largeur=36.0, profondeur=36.0, hauteur=22.0):
    """Gymnase d'entraînement : murs blancs et gris clair (≈ 12) à hautes fenêtres étroites, grande verrière
    en berceau de l'avant à l'arrière (7 bandes de verre, nervures blanches tous les ≈ 6, faîtage à `hauteur`),
    pignons vitrés, grande porte de hangar coulissante entrouverte sur un intérieur sombre, bandeau
    ENTRAÎNEMENT (v0, v2) ou GYMNASE (v1, v3) à liseré cyan. Intérieur : terrain de sport visible par la verrière."""
    rng = b.rng
    W, D, Hr = float(largeur), float(profondeur), float(hauteur)
    hw = 12.0                                      # hauteur des murs
    xm = W / 2 - 0.6                               # faces extérieures des murs latéraux (rives jusqu'à W/2)
    zf, zbk = -D / 2 + 0.5, D / 2 - 0.5            # faces extérieures des murs avant / arrière
    ep = 1.0
    texte = "ENTRAÎNEMENT" if variant % 2 == 0 else "GYMNASE"
    porte = ("marine", "marine_clair")[variant % 2]
    with b.group("Halle"):
        # --- murs (creux : la verrière laisse voir le terrain) ---
        ox0, ox1 = -9.0, 9.0                       # ouverture de la porte de hangar
        hp = 9.5
        b.box((-xm, 0, zf + ep), (-xm + ep, hw, zbk - ep), c("blanc"), name="MurG")
        b.box((xm - ep, 0, zf + ep), (xm, hw, zbk - ep), c("blanc"), name="MurD")
        b.box((-xm, 0, zbk - ep), (xm, hw, zbk), c("blanc"), name="MurArriere")
        b.box((-xm, 0, zf), (ox0, hw, zf + ep), c("blanc"), name="MurAvant")
        b.box((ox1, 0, zf), (xm, hw, zf + ep), c("blanc"), name="MurAvant")
        b.box((ox0, hp, zf), (ox1, hw, zf + ep), c("blanc"), name="Linteau")
        # soubassement gris clair (panneaux sur les faces extérieures)
        for face, ua, ub in ((("x", -1, -xm), zf, zbk), (("x", 1, xm), zf, zbk), (("z", 1, zbk), -xm, xm),
                             (("z", -1, zf), -xm, ox0 - 0.0), (("z", -1, zf), ox1, xm)):
            _sur_face(b, face, ua, ub, 0, 3.0, 0.0, 0.15, "beton_clair", name="Soubassement")
        # couvertine
        for face, ua, ub in ((("x", -1, -xm), zf, zbk), (("x", 1, xm), zf, zbk)):
            _sur_face(b, face, ua - 0.2, ub + 0.2, hw - 0.8, hw, -0.05, 0.35, "beton_clair", name="Couvertine")
        # hautes fenêtres étroites
        for sx in (-1, 1):
            face = ("x", sx, sx * xm)
            for k in range(5):
                zc = zf + 5.0 + k * (zbk - zf - 10.0) / 4
                _sur_face(b, face, zc - 0.9, zc + 0.9, 3.6, hw - 1.6, -0.05, 0.2, "vitre_bleue", material="Glass",
                          collide=False, name="Fenetre")
        for k in range(4):
            xc = -xm + 6.0 + k * (2 * xm - 12.0) / 3
            _sur_face(b, ("z", 1, zbk), xc - 0.9, xc + 0.9, 3.6, hw - 1.6, -0.05, 0.2, "vitre_bleue", material="Glass",
                      collide=False, name="Fenetre")

        # --- intérieur : terrain de sport, sas sombre derrière la porte ---
        b.box((-xm + ep, 0, zf + ep), (xm - ep, 0.3, zbk - ep), c("bois_clair"), name="Terrain")
        for x in (-6.0, 6.0):
            b.box((x - 0.2, 0.3, zf + 6), (x + 0.2, 0.4, zbk - 4), c("blanc"), collide=False, name="Ligne")
        b.box((-xm + 4, 0.3, -0.2), (xm - 4, 0.4, 0.2), c("blanc"), collide=False, name="Ligne")
        b.box((ox0 - 0.5, 0.3, zf + ep), (ox1 + 0.5, hp, zf + ep + 3.0), col(INTERIEUR), name="Sas")

        # --- porte de hangar coulissante : un vantail fermé à droite, l'autre glissé sur le mur à gauche ---
        with b.group("Porte"):
            zp0, zp1 = zf - 0.3, zf - 0.05
            b.box((-xm + 0.5, hp, zp0 - 0.1), (ox1 + 0.5, hp + 0.6, zf), c("acier_fonce"), name="Rail")
            for xa, xb in ((0.0, ox1 + 0.3), (ox0 - 9.0 + 0.4, ox0 + 0.4)):
                b.box((xa, 0.2, zp0), (xb, hp, zp1), c(porte), name="Vantail")
                for y in (2.4, 4.8, 7.2):
                    b.box((xa + 0.3, y - 0.2, zp0 - 0.12), (xb - 0.3, y + 0.2, zp0), c("marine_clair") if porte ==
                          "marine" else c("marine"), collide=False, name="Nervure")
                b.box((xa + 0.4, 3.6, zp0 - 0.15), (xa + 0.7, 5.6, zp0), c("acier"), collide=False, name="Poignee")
        # bandeau texte et néon cyan au-dessus de la porte
        p = b.box((-8.5, hp + 0.8, zf - 0.35), (8.5, hw - 0.3, zf), c("marine"), collide=False, name="Bandeau")
        _label(p, texte, face="Front", couleur=(255, 255, 255))
        b.box((-8.7, hp + 0.6, zf - 0.5), (8.7, hp + 0.8, zf - 0.2), c("neon_cyan"), material="Neon", collide=False,
              shadow=False, name="NeonBandeau")

        # --- verrière en berceau ---
        R = (xm ** 2 + (Hr - hw) ** 2) / (2 * (Hr - hw))
        yc = Hr - R
        phi_max = math.asin(xm / R)
        nb = 7
        phis = [-phi_max + 2 * phi_max * k / nb for k in range(nb + 1)]
        pts = [(R * math.sin(f), yc + R * math.cos(f)) for f in phis]
        z0, z1 = -D / 2, D / 2
        verre_v = mix(c("verre_canopee"), c("vitre_ciel"), 0.45)
        with b.group("Verriere"):
            for k in range(nb):
                (xa, ya), (xb, yb) = pts[k], pts[k + 1]
                fm = (phis[k] + phis[k + 1]) / 2
                L = math.hypot(xb - xa, yb - ya)
                nx, ny = math.sin(fm), math.cos(fm)
                cx, cy = (xa + xb) / 2 - nx * 0.25, (ya + yb) / 2 - ny * 0.25
                b.part("block", (L + 0.3, 0.5, z1 - z0 - 0.6), (cx, cy, 0.0), rot_z(-math.degrees(fm)), verre_v,
                       material="Glass", transparency=0.35, collide=True, name="Verre")
            # nervures longitudinales aux jonctions des bandes
            for k in range(1, nb):
                xa, ya = pts[k]
                f = phis[k]
                b.part("block", (0.6, 0.6, z1 - z0), (xa + math.sin(f) * 0.1, ya + math.cos(f) * 0.1, 0.0),
                       rot_z(-math.degrees(f)), c("cadre_blanc"), collide=False, name="Nervure")
            # arcs transversaux tous les ≈ 6
            na = max(2, round((z1 - z0) / 6.0))
            for j in range(na + 1):
                z = z0 + 0.3 + j * (z1 - z0 - 0.6) / na
                for k in range(nb):
                    (xa, ya), (xb, yb) = pts[k], pts[k + 1]
                    fm = (phis[k] + phis[k + 1]) / 2
                    L = math.hypot(xb - xa, yb - ya)
                    nx, ny = math.sin(fm), math.cos(fm)
                    b.part("block", (L + 0.5, 0.7, 0.6), ((xa + xb) / 2 + nx * 0.2, (ya + yb) / 2 + ny * 0.2, z),
                           rot_z(-math.degrees(fm)), c("blanc"), collide=False, name="Arc")
            # poutres de rive sur les murs latéraux
            for sx in (-1, 1):
                b.box((sx * xm - 0.6, hw, z0), (sx * xm + 0.6, hw + 0.8, z1), c("blanc"), name="Rive")
            # pignons vitrés (avant et arrière) : un gradin et deux coins sous chaque paire de cordes
            for zp, nom in ((zf + 0.5, "PignonAvant"), (zbk - 0.5, "PignonArriere")):
                za, zb_ = zp - 0.25, zp + 0.25
                for k in range(nb // 2):
                    (x_out, y_lo), (x_in, y_hi) = pts[nb - k], pts[nb - k - 1]
                    b.box((-x_in, hw if k == 0 else y_lo, za), (x_in, y_hi, zb_), verre_v, material="Glass",
                          transparency=0.35, collide=False, name=nom)
                    for sx in (-1, 1):
                        xa_, xb_ = sorted((sx * x_in, sx * x_out))
                        b.wedge((xa_, y_lo, za), (xb_, y_hi, zb_), verre_v, down="+x" if sx > 0 else "-x",
                                material="Glass", transparency=0.35, collide=False, name=nom)
                for x in (-6.0, 0.0, 6.0):
                    y_haut = yc + math.sqrt(max(0.0, R * R - x * x)) - 0.6
                    b.box((x - 0.25, hw, za - 0.15), (x + 0.25, y_haut, zb_ + 0.15), c("cadre_blanc"), collide=False,
                          name="Meneau")
    return {"emprise": (W, D), "hauteur": Hr + 0.5}
