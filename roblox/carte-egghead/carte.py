#!/usr/bin/env python3
"""Carte « île du futur » (CarteEgghead) : assemble toute la carte d'après plan.py (cotes) et assets/*.py.

Interface attendue par rendu.py :
- `build_carte(seed=7) -> Builder` : toute la carte, pivot = origine = centre de la pelouse au niveau du sol (y = 0) ;
- `meta() -> dict` : {"nom": "CarteEgghead", "version": …} (nom du modèle et des fichiers exportés) ;
- `verifications(b) -> dict` : contrôles (la liste « problemes » doit rester vide ; « provisoires » informe) ;
- `VUES` = plan.VUES : {nom: ((x, y, z) caméra, (x, y, z) cible, champ vertical en degrés)}.

Ordre de construction (SPECS.md, fiche carte.py) :
1. sol : pelouse à studs (dalles de 64) et sa grille de lignes en relief, trottoirs, bordures rayées rouge et blanc,
   routes et marquages (tirets, lignes de rive, flèches, passages piétons), sol de la couronne et esplanade nord,
   mur de fond, traces des parcelles (facultatives), repères du jeu (dossier Reperes) ;
2. tapis roulant (assets/tapis.py ; portails de tête seulement si plan.PORTAILS en contient : le plan final n'en a
   pas), pièces du U (assets/centre.py, kiosques et portail violet de assets/tours_formes.py) ;
3. couronne : chaque emplacement de plan.CEINTURE (assets/tours_rondes.py, assets/tours_formes.py) ;
4. tubes de verre entre les tours (posés ici), ciel (assets/ciel.py), mobilier (assets/mobilier.py) ;
5. découpage du groupe Sol en blocs de 64 × 64.

Chaque module d'assets est importé à part : un module ou une fonction absente, ou qui lève une exception, est
remplacé par un bloc provisoire lavande à l'emprise de l'emplacement (groupe Provisoire/<id>) et listé dans
`verifications(b)["provisoires"]` : la carte se construit toujours. Chaque appel est mesuré (pièces, Neon,
transparentes) et comparé à plan.budget_appel (par appel), plan.BUDGETS (par module) et plan.BUDGET_CARTE.

    python carte.py                     # build/parts.json + vérifications (résumé)
    python carte.py --stats             # + pièces par groupe racine et par module, appels hors budget
    python carte.py --export DOSSIER    # + export Roblox avec Lune (.rbxm, .rbxmx, -demo.rbxl), sans Blender
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import plan  # noqa: E402
from kit import (GROUPE_REPERES, Builder, _faces_confondues, bornes, controles, exporter_roblox,  # noqa: E402
                 mix)
from palette import c as coul  # noqa: E402

NOM = "CarteEgghead"
VERSION = "1.0"
VUES = dict(plan.VUES)

MODULES_ASSETS = ("tapis", "centre", "tours_rondes", "tours_formes", "ciel", "mobilier", "esplanade")

# --- Couleurs du sol (palette.py ; tons dérivés par mix / shade seulement) ----------------------------------------
SOL_VERT = coul("sol_vert")
# Lignes de la grille : la grille de l'île (refEH4) est un fin quadrillage vert clair, pas un carrelage blanc. La
# ligne fait 1 stud (studs alignés), soit 1/8 de la case contre ≈ 1/25 dans l'anime : on baisse donc son contraste
# (sol_ligne mêlé à 10 % au vert clair, essais du 12-13/11 sous la lumière de la carte : à 22 %, la grille paraît
# blanche dans capture2).
LIGNE_GRILLE = mix(coul("sol_vert_clair"), coul("sol_ligne"), 0.10)
SOL_COURONNE = coul("sol_vert_clair")
DALLE = coul("dalle_labo")
VOIE = coul("voie")
BLANC = coul("blanc_labo")
ROUGE = coul("rouge")
OR = coul("or")
MUR = coul("skyline")                 # finition : le mur de fond se lit comme une façade lointaine (bande vitrée)
VITRE_MUR = coul("hublot")
FOND_BAIE = mix(coul("lavande"), coul("blanc_labo"), 0.55)
BANDEAU = coul("lavande")
PROVISOIRE = coul("lavande")
VERRE_TUBE = coul("verre")

EP = plan.EPAISSEUR_DALLE          # toutes les dalles descendent à y = -2
DECALAGE_PELOUSE = 4               # joints des dalles de pelouse en 64k + 4 : jamais au pied d'une ligne de grille


# =====================================================================================================================
# Suivi des appels d'assets (mesure, budgets, provisoires)
# =====================================================================================================================

class Suivi:
    """Modules chargés, appels mesurés, blocs provisoires, résultats des assets (âme des tours…)."""

    def __init__(self):
        self.modules: dict = {}
        self.erreurs_import: dict = {}
        self.appels: list[dict] = []
        self.provisoires: list[dict] = []
        self.resultats: dict = {}
        for nom in MODULES_ASSETS:
            try:
                self.modules[nom] = importlib.import_module(f"assets.{nom}")
            except Exception as e:  # module absent, en cours d'écriture, ou en erreur
                self.modules[nom] = None
                self.erreurs_import[nom] = f"{type(e).__name__}: {e}"[:200]

    def fonction(self, cle: str):
        mod, nom = cle.split(".")
        m = self.modules.get(mod)
        if m is None:
            raison = self.erreurs_import.get(mod, "module absent")
            return None, f"assets/{mod}.py : {raison}"
        f = getattr(m, nom, None)
        if f is None:
            return None, f"fonction {cle} absente"
        return f, None


def _module_budget(cle: str) -> str:
    m = cle.split(".")[0]
    return "tapis+centre" if m in ("tapis", "centre") else m


def _compter(parts) -> tuple[int, int, int]:
    return (len(parts), sum(1 for p in parts if p.material == "Neon"),
            sum(1 for p in parts if 0 < p.transparency < 0.99))


def _provisoire(b: Builder, spec) -> None:
    """Bloc provisoire (repère local de l'emplacement) : ("rond", rayon, hauteur, y0) ou ("rect", lx, lz, hauteur, y0)
    ou une fonction f(b)."""
    if callable(spec):
        spec(b)
        return
    if spec[0] == "rond":
        _, r, h, y0 = spec
        b.cyl((0, y0 + h / 2, 0), max(r, 0.5), max(h, 0.2), PROVISOIRE, name="Provisoire")
    elif spec[0] == "boule":
        _, r = spec
        b.ellipsoid((0, 0, 0), (2 * r, r, 2 * r), PROVISOIRE, collide=False, name="Provisoire")
    else:
        _, lx, lz, h, y0 = spec      # retrait de 0,03 : jamais une face dans le plan d'une ligne de grille
        b.box((-lx / 2 + 0.03, y0, -lz / 2 + 0.03), (lx / 2 - 0.03, y0 + max(h, 0.2), lz / 2 - 0.03), PROVISOIRE,
              name="Provisoire")


def poser(b: Builder, suivi: Suivi, ident: str, cle: str, variante: int, params: dict, pos, yaw: float,
          groupe: str, prov) -> dict:
    """Appelle l'asset `cle` (« module.fonction ») dans le repère (pos, yaw), groupe `groupe` ; mesure l'appel ; en cas
    d'absence ou d'erreur, pose un bloc provisoire (groupe Provisoire/<ident>)."""
    f, raison = suivi.fonction(cle)
    n0 = len(b.parts)
    res = None
    if f is not None:
        try:
            with b.at(pos, yaw=yaw, group=groupe):
                res = f(b, variant=variante, **params)
        except Exception as e:
            del b.parts[n0:]
            raison = f"{type(e).__name__}: {e}"[:200]
            f = None
    if f is None:
        with b.at(pos, yaw=yaw, group=f"Provisoire/{ident}"):
            _provisoire(b, prov)
        suivi.provisoires.append({"id": ident, "fonction": cle, "raison": raison})
    n, neon, transp = _compter(b.parts[n0:])
    suivi.appels.append({"id": ident, "fonction": cle, "variante": variante, "params": params, "pieces": n,
                         "neon": neon, "transp": transp, "provisoire": f is None})
    suivi.resultats[ident] = res if isinstance(res, dict) else {}
    return suivi.resultats[ident]


# =====================================================================================================================
# 1. Le sol
# =====================================================================================================================

def _coupes(a: float, b: float, pas: int = 64, decalage: float = 0.0) -> list[float]:
    """[a, …, b] : les deux bornes et les multiples de `pas` (+ `decalage`) strictement entre elles."""
    out = [a]
    k = math.floor((a - decalage) / pas) + 1
    while k * pas + decalage < b - 1e-9:
        v = k * pas + decalage
        if v > a + 1e-9:
            out.append(v)
        k += 1
    out.append(b)
    return out


def dalles(b: Builder, x0, x1, z0, z1, y1, couleur, nom: str, decalage: float = 0.0) -> int:
    """Rectangle de sol [x0, x1] × [z0, z1], de y = -2 à y1, coupé aux multiples de 64 ; studs sur le dessus."""
    x0, x1 = sorted((x0, x1))
    z0, z1 = sorted((z0, z1))
    xs, zs = _coupes(x0, x1, plan.DALLE_SOL, decalage), _coupes(z0, z1, plan.DALLE_SOL, decalage)
    n = 0
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            b.box((xs[i], -EP, zs[j]), (xs[i + 1], y1, zs[j + 1]), couleur, studs="top", name=nom)
            n += 1
    return n


def _bornes_bande(bx: float, bz_sud: float, bz_nord: float) -> tuple[float, float, float, float]:
    """Rectangle (x0, x1, z0, z1) d'une bande : |x| ≤ bx, de z = -bz_nord (nord) à z = bz_sud (sud)."""
    return (-bx, bx, -bz_nord, bz_sud)


def cadre(b: Builder, dedans, dehors, y1, couleur, nom: str) -> None:
    """Anneau de sol entre deux rectangles (x0, x1, z0, z1) emboîtés : bandes est et ouest sur toute la hauteur,
    bandes nord et sud entre elles ; dalles coupées aux multiples de 64, studs dessus."""
    ix0, ix1, iz0, iz1 = dedans
    ex0, ex1, ez0, ez1 = dehors
    dalles(b, ex0, ix0, ez0, ez1, y1, couleur, nom)        # ouest (angles compris)
    dalles(b, ix1, ex1, ez0, ez1, y1, couleur, nom)        # est (angles compris)
    dalles(b, ix0, ix1, ez0, iz0, y1, couleur, nom)        # nord
    dalles(b, ix0, ix1, iz1, ez1, y1, couleur, nom)        # sud


def pelouse(b: Builder) -> None:
    """Pelouse sol_vert (dessus à 0 ; |x| ≤ 205, z de -336 à 301) et grille : lignes d'1 stud au pas de 8 sur
    [8k, 8k + 1], en relief (0,15 le long de Z, 0,20 le long de X). Les lignes descendent sous le dessus de la pelouse
    (dessous à -0,47 et -0,43 : jamais dans le plan y = 0 où se posent les objets) et s'arrêtent à 0,05 des bords ;
    aucune ligne sur le bord même de la pelouse ; les joints des dalles (64k + 4) tombent entre deux lignes."""
    PX, PZS, PZN = plan.PELOUSE_X, plan.PELOUSE_Z_SUD, plan.PELOUSE_Z_NORD
    pas, larg = plan.GRILLE_PAS, plan.GRILLE_LARGEUR
    with b.group("Sol"):
        with b.group("Pelouse"):
            dalles(b, -PX, PX, -PZN, PZS, plan.NIVEAU_PELOUSE, SOL_VERT, "Pelouse", decalage=DECALAGE_PELOUSE)
        with b.group("Grille"):
            for k in range(math.ceil((-PX + 1) / pas), math.floor((PX - larg - 1) / pas) + 1):
                x = k * pas
                b.box((x, -0.47, -PZN + 0.05), (x + larg, plan.GRILLE_HAUT_LIGNES_Z, PZS - 0.05), LIGNE_GRILLE,
                      studs="top", name="LigneZ")
            for k in range(math.ceil((-PZN + 1) / pas), math.floor((PZS - larg - 1) / pas) + 1):
                z = k * pas
                b.box((-PX + 0.05, -0.43, z), (PX - 0.05, plan.GRILLE_HAUT_LIGNES_X, z + larg), LIGNE_GRILLE,
                      studs="top", name="LigneX")


def _phase_rayures(a0: float, a1: float) -> float:
    """Phase a (rayures rouges sur [8k + a, 8k + a + 4], a ∈ {2, 6}) qui équilibre les deux bouts blancs du segment
    [a0, a1] (jamais un segment rouge coupé aux angles, qui restent blancs). a = 2 ou 6 : les faces des blocs rouges
    (8k ± 2) ne tombent jamais sur un joint de dalle de la route (multiples de 64) qu'elles débordent de 0,1."""
    R = plan.BORDURE_RAYURE
    best = None
    for a in (2.0, 6.0):
        k0 = math.ceil((a0 - a) / (2 * R))
        k1 = math.floor((a1 - a - R) / (2 * R))
        if k1 < k0:
            continue
        reste0 = (2 * R * k0 + a) - a0
        reste1 = a1 - (2 * R * k1 + a + R)
        score = abs(reste0 - reste1)
        if best is None or score < best[1]:
            best = (a, score)
    return best[0] if best else 0.0


def bordure(b: Builder, dedans, route_dehors: bool) -> None:
    """Bordure rayée d'1 stud en anneau rectangulaire autour du rectangle `dedans` (x0, x1, z0, z1).
    Base blanc_labo continue (y -2 → 0,6) ; blocs rouges de 4 tous les 8, en saillie de 0,1 sur le dessus (0,7) et
    sur la face côté route, côté trottoir en retrait de 0,05 ; carrés blancs aux angles."""
    B = plan.BORDURE_LARGEUR
    x0, x1, z0, z1 = dedans
    yb = plan.BORDURE_DESSUS
    yr0, yr1 = -0.5, yb + 0.1
    R = plan.BORDURE_RAYURE
    with b.group("Base"):
        b.box((x0 - B, -EP, z0 - B), (x0, yb, z1 + B), BLANC, studs="top", name="Bordure")      # ouest
        b.box((x1, -EP, z0 - B), (x1 + B, yb, z1 + B), BLANC, studs="top", name="Bordure")      # est
        b.box((x0, -EP, z0 - B), (x1, yb, z0), BLANC, studs="top", name="Bordure")              # nord
        b.box((x0, -EP, z1), (x1, yb, z1 + B), BLANC, studs="top", name="Bordure")              # sud
    # bloc rouge : saillie de 0,1 côté route, retrait de 0,05 côté trottoir ; e_in / e_out = décalage de sa face
    # intérieure / extérieure (vers le dehors de l'anneau) par rapport à la base
    e_in, e_out = (0.05, 0.1) if route_dehors else (-0.1, -0.05)
    with b.group("Rayures"):
        a = _phase_rayures(z0, z1)
        for (xa, xb) in ((x0 - B - e_out, x0 - e_in), (x1 + e_in, x1 + B + e_out)):   # ouest, est
            k = math.ceil((z0 - a) / (2 * R))
            while 2 * R * k + a + R <= z1 + 1e-9:
                zz = 2 * R * k + a
                b.box((xa, yr0, zz), (xb, yr1, zz + R), ROUGE, studs="top", name="Rayure")
                k += 1
        a = _phase_rayures(x0, x1)
        for (za, zb) in ((z0 - B - e_out, z0 - e_in), (z1 + e_in, z1 + B + e_out)):   # nord, sud
            k = math.ceil((x0 - a) / (2 * R))
            while 2 * R * k + a + R <= x1 + 1e-9:
                xx = 2 * R * k + a
                b.box((xx, yr0, za), (xx + R, yr1, zb), ROUGE, studs="top", name="Rayure")
                k += 1


def trottoirs(b: Builder) -> None:
    B = plan.BORDURE_LARGEUR
    yt = plan.NIVEAU_TROTTOIR
    pel = _bornes_bande(plan.PELOUSE_X, plan.PELOUSE_Z_SUD, plan.PELOUSE_Z_NORD)
    tin = _bornes_bande(plan.TROTTOIR_INT_X, plan.TROTTOIR_INT_Z_SUD, plan.TROTTOIR_INT_Z_NORD)
    rte = _bornes_bande(plan.ROUTE_X, plan.ROUTE_Z_SUD, plan.ROUTE_Z_NORD)
    j = plan.JOINT_COURONNE      # le trottoir extérieur passe d'1 stud sous le pied des façades
    tex = _bornes_bande(plan.TROTTOIR_EXT_X + j, plan.TROTTOIR_EXT_Z_SUD + j, plan.TROTTOIR_EXT_Z_NORD + j)
    tin_sans_bordure = (tin[0] + B, tin[1] - B, tin[2] + B, tin[3] - B)      # le dernier stud est la bordure
    rte_bordure = (rte[0] - B, rte[1] + B, rte[2] - B, rte[3] + B)
    with b.group("Trottoirs"):
        with b.group("Interieur"):
            cadre(b, pel, tin_sans_bordure, yt, DALLE, "Trottoir")
            with b.group("Bordure"):
                bordure(b, tin_sans_bordure, route_dehors=True)
        with b.group("Exterieur"):
            cadre(b, rte_bordure, tex, yt, DALLE, "Trottoir")
            with b.group("Bordure"):
                bordure(b, rte, route_dehors=False)


def _fleche(b: Builder, x: float, z: float, d: tuple[float, float]) -> None:
    """Flèche au sol pointant dans la direction d (unitaire, le long d'un axe) : hampe 1,4 × 6 + tête en chevron
    (2 bras à ±45°) ; longueur 9 ; hauteurs et dessous décalés (aucune face confondue)."""
    yaw = plan.yaw_direction(d[0], d[1])
    L = plan.FLECHE_LONGUEUR
    with b.at((x, 0, z), yaw=yaw):
        # avant = -Z local ; pointe en z = -L/2
        b.box((-0.7, 0, -L / 2 + 3), (0.7, plan.NIVEAU_MARQUAGE, L / 2), BLANC, studs="top", name="Fleche")
        lb = 4.6
        for i, sgn in enumerate((-1, 1)):
            dx, dz = sgn * math.sqrt(0.5), math.sqrt(0.5)          # vers l'arrière, à gauche puis à droite
            cx, cz = 0 + dx * (lb / 2 - 0.55), -L / 2 + dz * (lb / 2 - 0.55)
            y0, y1 = 0.01 * (i + 1), plan.NIVEAU_MARQUAGE + 0.02 * (i + 1)
            b.boxc((cx, (y0 + y1) / 2, cz), (1.3, y1 - y0, lb), BLANC, yaw=45 * sgn, studs="top", name="Fleche")


def routes(b: Builder) -> None:
    """Route à 2 voies de 18 (anneau entre les trottoirs), marquages blancs : tirets de l'axe 1 × 6 tous les 16,
    lignes de rive à 2 des bords, flèches (voie intérieure antihoraire), passages piétons zébrés."""
    TX, RX = plan.TROTTOIR_INT_X, plan.ROUTE_X
    TZS, TZN = plan.TROTTOIR_INT_Z_SUD, plan.TROTTOIR_INT_Z_NORD
    RZS, RZN = plan.ROUTE_Z_SUD, plan.ROUTE_Z_NORD
    hm = plan.NIVEAU_MARQUAGE
    rr = plan.LIGNE_RIVE_RETRAIT
    passages = defaultdict(list)          # côté → centres s
    for p in plan.PASSAGES_PIETONS:
        passages[p["cote"]].append(p["s"])
    demi_p = plan.PASSAGE_LARGEUR / 2
    tin = _bornes_bande(TX, TZS, TZN)
    rte = _bornes_bande(RX, RZS, RZN)
    with b.group("Routes"):
        with b.group("Voies"):
            cadre(b, tin, rte, plan.NIVEAU_ROUTE, VOIE, "Voie")
        with b.group("Marquages"):
            T, P_ = plan.TIRET_LONGUEUR, plan.TIRET_PAS
            arret = plan.TIRET_ARRET_COIN
            # --- tirets de l'axe : 1 × 6 tous les 16, centrés sur 16k, arrêtés à 4 des carrés d'angle ----------
            ax = int(plan.ROUTE_AXE_X)
            for s, cote in ((1, "est"), (-1, "ouest")):
                x0 = ax if s > 0 else -ax - 1
                for k in range(math.ceil((-TZN + arret + T / 2) / P_), math.floor((TZS - arret - T / 2) / P_) + 1):
                    c = k * P_
                    if any(abs(c - sp) < demi_p + T / 2 + 1 for sp in passages[cote]):
                        continue
                    b.box((x0, 0, c - T / 2), (x0 + 1, hm, c + T / 2), BLANC, studs="top", name="Tiret")
            for z0 in (int(plan.ROUTE_AXE_Z_SUD), -int(plan.ROUTE_AXE_Z_NORD) - 1):
                for k in range(math.ceil((-TX + arret + T / 2) / P_), math.floor((TX - arret - T / 2) / P_) + 1):
                    c = k * P_
                    b.box((c - T / 2, 0, z0), (c + T / 2, hm, z0 + 1), BLANC, studs="top", name="Tiret")
            # --- lignes de rive : anneau intérieur et anneau extérieur, raccordés aux angles sans recouvrement --
            anneaux = ((TX + rr, TZS + rr, TZN + rr), (RX - rr - 1, RZS - rr - 1, RZN - rr - 1))
            if not getattr(plan, "LIGNES_DE_RIVE", True):
                anneaux = ()
            for (lx, lzs, lzn) in anneaux:        # ligne sur [lx, lx + 1] (et symétriques), [lzs, lzs + 1], …
                for s, cote in ((1, "est"), (-1, "ouest")):
                    # le long de Z, entre les lignes nord et sud (qui couvrent les angles), coupée aux passages
                    bornes_z = [-lzn]
                    for sp in sorted(passages[cote]):
                        bornes_z += [sp - demi_p, sp + demi_p]
                    bornes_z.append(lzs)
                    x0 = lx if s > 0 else -lx - 1
                    for i in range(0, len(bornes_z), 2):
                        b.box((x0, 0, bornes_z[i]), (x0 + 1, hm, bornes_z[i + 1]), BLANC, studs="top",
                              name="LigneRive")
                b.box((-lx - 1, 0, lzs), (lx + 1, hm, lzs + 1), BLANC, studs="top", name="LigneRive")
                b.box((-lx - 1, 0, -lzn - 1), (lx + 1, hm, -lzn), BLANC, studs="top", name="LigneRive")
            # --- flèches : voie intérieure antihoraire vue du dessus, voie extérieure en sens inverse ----------
            c_int = TX + (RX - TX) / 4                # milieu de la voie intérieure (226)
            c_ext = RX - (RX - TX) / 4                 # milieu de la voie extérieure (244)
            ci_s, ce_s = TZS + (RZS - TZS) / 4, RZS - (RZS - TZS) / 4
            ci_n, ce_n = TZN + (RZN - TZN) / 4, RZN - (RZN - TZN) / 4
            Lf = plan.FLECHE_LONGUEUR
            # (côté, coordonnée fixe des voies intérieure / extérieure, direction intérieure, bornes de s)
            sens = (("est", c_int, c_ext, (0, -1), (-TZN, TZS)), ("ouest", -c_int, -c_ext, (0, 1), (-TZN, TZS)),
                    ("sud", ci_s, ce_s, (1, 0), (-TX, TX)), ("nord", -ci_n, -ce_n, (-1, 0), (-TX, TX)))
            for cote, fi, fe, d, (s0, s1) in sens:
                phase = getattr(plan, "FLECHE_PHASE", 0.0)
                for voie, fixe, dirv, decal in (("int", fi, d, phase), ("ext", fe, (-d[0], -d[1]), phase)):
                    k = math.ceil((s0 - decal) / plan.FLECHE_PAS)
                    while k * plan.FLECHE_PAS + decal <= s1:
                        sc = k * plan.FLECHE_PAS + decal
                        k += 1
                        if sc - Lf / 2 < s0 + arret + 4 or sc + Lf / 2 > s1 - arret - 4:
                            continue
                        if any(abs(sc - sp) < demi_p + Lf / 2 + 12 for sp in passages.get(cote, [])):
                            continue
                        if cote in ("est", "ouest"):
                            _fleche(b, fixe, sc, dirv)
                        else:
                            _fleche(b, sc, fixe, dirv)
            # --- passages piétons : 9 bandes 2 × 10 au pas de 4 sur toute la largeur de la route --------------
            for p in plan.PASSAGES_PIETONS:
                s = 1 if p["cote"] == "est" else -1
                with b.group(p["id"]):
                    k = 0
                    while TX + 1 + 4 * k + plan.PASSAGE_BANDE <= RX - 1 + 1e-9:
                        x0 = TX + 1 + 4 * k
                        b.box((s * x0, 0, p["s"] - demi_p), (s * (x0 + plan.PASSAGE_BANDE), hm, p["s"] + demi_p),
                              BLANC, studs="top", name="Zebra")
                        k += 1


def sol_couronne(b: Builder) -> None:
    """Sol de la couronne (sol_vert_clair, dessus à 0,4) de la ligne des façades (+1 : le trottoir passe sous leur
    pied) au bord extérieur, avec le renfoncement nord : esplanade (voie, rangées de tirets blancs : aire des
    navettes) entre ses deux flancs, et la couronne du fond derrière elle."""
    j = plan.JOINT_COURONNE
    AX, AZS, AZN = plan.ALIGNEMENT_X + j, plan.ALIGNEMENT_Z_SUD + j, plan.ALIGNEMENT_Z_NORD + j
    CX, CZS, CZN = plan.COURONNE_X, plan.COURONNE_Z_SUD, plan.COURONNE_Z_NORD
    EX, EZ = plan.ESPLANADE_X + j, plan.ESPLANADE_Z + j        # l'esplanade passe sous le pied des flancs et du fond
    FX, FZ = plan.FOND_X, plan.FOND_Z
    y = plan.NIVEAU_COURONNE
    with b.group("Sol"):
        with b.group("Couronne"):
            for s in (1, -1):
                dalles(b, s * AX, s * CX, -CZN, CZS, y, SOL_COURONNE, "SolCouronne")    # est / ouest + angles
                dalles(b, s * EX, s * AX, -CZN, -AZN, y, SOL_COURONNE, "SolCouronne")   # nord, de part et d'autre
                dalles(b, s * EX, s * FX, -EZ, -CZN, y, SOL_COURONNE, "SolCouronne")    # pied des flancs
            dalles(b, -AX, AX, AZS, CZS, y, SOL_COURONNE, "SolCouronne")                 # sud
            dalles(b, -FX, FX, -FZ, -EZ, y, SOL_COURONNE, "SolCouronne")                 # couronne du fond
        with b.group("Esplanade"):
            dalles(b, -EX, EX, -EZ, -AZN, y, VOIE, "Esplanade")
            # rangées de tirets blancs (comme les places de la référence) : 3 rangées de tirets 6 × 1 tous les 12
            z_f = plan.ALIGNEMENT_Z_NORD
            for zr in (-z_f - 22, -z_f - 66):          # la rangée du milieu laisse place au port de nacelles
                for k in range(-10, 11):
                    xc = 12 * k
                    if abs(xc) + 3 > plan.ESPLANADE_X - 8:
                        continue
                    b.box((xc - 3, y, zr), (xc + 3, y + plan.NIVEAU_MARQUAGE, zr + 1), BLANC, studs="top",
                          name="Tiret")


def _mur(b: Builder, x0, x1, z0, z1, y0, yb, y1, bandeau_x, bandeau_z) -> None:
    """Un pan du mur de fond (boîte x0 → x1, z0 → z1, de y0 à yb) et son bandeau (yb → y1), qui déborde de
    bandeau_x / bandeau_z de chaque côté (saillies de 0,1, ou bouts arrêtés au bandeau voisin)."""
    b.box((x0, y0, z0), (x1, yb, z1), MUR, name="Mur")
    b.box((x0 - bandeau_x[0], yb, z0 - bandeau_z[0]), (x1 + bandeau_x[1], y1, z1 + bandeau_z[1]), BANDEAU,
          studs="top", name="Bandeau")
    # bande vitrée de 2,5 vers y 24 (mêmes débords que le bandeau) : une façade lointaine, pas un mur nu
    b.box((x0 - bandeau_x[0], 23.0, z0 - bandeau_z[0]), (x1 + bandeau_x[1], 25.5, z1 + bandeau_z[1]), VITRE_MUR,
          name="Vitrage")


def mur_de_fond(b: Builder) -> None:
    """Mur continu de 2 au bord extérieur de la couronne (avec le décrochement de la couronne du fond), jusqu'à
    y 36 ; bandeau lavande d'1,5 en haut (saillie 0,1). Le mur part de y -0,6 (enfoncé dans le sol de la couronne :
    son dessous n'est jamais dans le plan y 0,4 où se posent les tours) et sa face extérieure dépasse le bord du sol
    de 0,05. Les pans le long de Z couvrent les angles ; les pans le long de X s'arrêtent contre eux."""
    CX, CZS, CZN = plan.COURONNE_X, plan.COURONNE_Z_SUD, plan.COURONNE_Z_NORD
    FX, FZ = plan.FOND_X, plan.FOND_Z
    e = plan.MUR_FOND_EPAISSEUR
    y0, y1 = plan.NIVEAU_COURONNE - 1.0, plan.MUR_FOND_HAUTEUR
    yb = y1 - 1.5
    o = 0.05                     # débord extérieur sur le bord du sol
    t = 0.1                      # saillie du bandeau
    with b.group("Tours"):
        with b.group("MurDeFond"):
            for s in (1, -1):
                # pans le long de Z : bords est et ouest (z de -482 à 447), flancs de la couronne du fond
                xa, xb = sorted((s * (CX - e), s * (CX + o)))
                _mur(b, xa, xb, -CZN - o, CZS + o, y0, yb, y1, (t, t), (t, t))
                xa, xb = sorted((s * (FX - e), s * (FX + o)))
                _mur(b, xa, xb, -FZ - o, -CZN + e, y0, yb, y1, (t, t), (t, t))
                # pans nord le long de X, entre le bord est (ou ouest) et le flanc du fond ; leur bandeau s'arrête
                # contre ceux des pans le long de Z
                xa, xb = sorted((s * (CX - e), s * (FX + o)))
                _mur(b, xa, xb, -CZN - o, -CZN + e, y0, yb, y1, (-t, -t), (t, t))
            # pan sud et pan du fond, entre les pans le long de Z
            _mur(b, -(CX - e), CX - e, CZS - e, CZS + o, y0, yb, y1, (-t, -t), (t, t))
            _mur(b, -(FX - e), FX - e, -FZ - o, -FZ + e, y0, yb, y1, (-t, -t), (t, t))


def traces_parcelles(b: Builder) -> None:
    """Groupe facultatif (supprimable) : équerres dorées aux coins des plateformes des parcelles, contour blanc des
    bandes d'entrée. Au ras du sol (0 → 0,3), sans collision : de la peinture."""
    h = 0.3
    j = 0.05            # retrait vers l'intérieur : aucune face dans le plan d'une ligne de grille (8k, 8k + 1)
    kw = dict(studs="top", collide=False, shadow=False)
    with b.group("TracesParcelles"):
        for p in plan.PARCELLES:
            with b.group(f"Parcelle_{p['id']}"):
                for (cx, sx) in ((p["x0"] + j, 1), (p["x1"] - j, -1)):
                    for (cz, sz) in ((p["z0"] + j, 1), (p["z1"] - j, -1)):
                        b.box((cx, 0, cz), (cx + sx * 8, h, cz + sz * 1), OR, name="Equerre", **kw)
                        b.box((cx, 0, cz + sz * 1), (cx + sx * 1, h, cz + sz * 8), OR, name="Equerre", **kw)
                e = p["escalier"]
                s = 1 if p["cote"] == "E" else -1
                xa = s * (plan.ESCALIER_X_EXT + j)           # bord côté tapis (|x| = 65)
                xb = s * (plan.PARCELLE_X_INT - j)           # bord de la plateforme (|x| = 81)
                z0, z1 = e["z0"] + j, e["z1"] - j
                b.box((xa, 0, z0), (xa + s * 1, h, z1), BLANC, name="BordEntree", **kw)
                b.box((xa + s * 1, 0, z0), (xb, h, z0 + 1), BLANC, name="BordEntree", **kw)
                b.box((xa + s * 1, 0, z1 - 1), (xb, h, z1), BLANC, name="BordEntree", **kw)


def reperes(b: Builder) -> None:
    for r in plan.REPERES:
        b.repere(r["nom"], r["centre"], taille=r["taille"], yaw=r["yaw"])


# =====================================================================================================================
# 2. Tapis, portails, pièces du centre
# =====================================================================================================================

def _tapis_provisoire(b: Builder) -> None:
    """Tapis provisoire (si assets/tapis.py manque) : chaque bande en bloc tourné, dessus alternés de 0,02."""
    larg = {"bordure_int": plan.TAPIS_BORDURE, "bande": plan.TAPIS_BANDE, "bordure_ext": plan.TAPIS_BORDURE}
    for i, t in enumerate(plan.tapis_bandes()):
        d = t["direction"]
        yaw = math.degrees(math.atan2(d[0], d[1]))          # Z local le long du tronçon
        for nom, col, h in (("bordure_int", BLANC, plan.TAPIS_DESSUS_BORDURE),
                            ("bande", coul("bleu_nuit"), plan.TAPIS_DESSUS),
                            ("bordure_ext", BLANC, plan.TAPIS_DESSUS_BORDURE)):
            q = t[nom]
            cx, cz = sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4
            L = (math.dist(q[0], q[1]) + math.dist(q[3], q[2])) / 2
            y0, y1 = -0.03 * (i % 2), h + 0.02 * (i % 2)
            b.boxc((cx, (y0 + y1) / 2, cz), (larg[nom], y1 - y0, L), col, yaw=yaw, studs="top", name="Provisoire")


def tapis_et_centre(b: Builder, suivi: Suivi) -> None:
    poser(b, suivi, "Tapis", "tapis.tapis", 0, {}, (0, 0, 0), 0, "Tapis", _tapis_provisoire)
    for p in plan.PORTAILS:
        params = {"largeur": plan.PORTAIL_LARGEUR, "profondeur": plan.PORTAIL_PROFONDEUR,
                  "hauteur": plan.PORTAIL_HAUTEUR}
        poser(b, suivi, p["id"], "tapis.portail", p["variante"], params, (p["x"], 0, p["z"]), p["yaw"],
              f"Tapis/{p['id']}", ("rect", plan.PORTAIL_LARGEUR, plan.PORTAIL_PROFONDEUR, plan.PORTAIL_HAUTEUR, 0))
    for nom, e in plan.CENTRE.items():
        lx, lz = e["emprise"]
        poser(b, suivi, nom, e["fonction"], e["variante"], dict(e.get("params", {})), (e["x"], 0, e["z"]),
              e["yaw"], f"Centre/{nom}", ("rect", lx, lz, e["hauteur"], 0))


# =====================================================================================================================
# 3. La couronne
# =====================================================================================================================

def couronne(b: Builder, suivi: Suivi) -> None:
    for e in plan.CEINTURE:
        cle = f"{e['module']}.{e['fonction']}"
        h = e.get("hauteur") or 20
        if e["forme"] == "rond":
            prov = ("rond", (e.get("diametre_sol") or min(e["largeur"], e["profondeur"])) / 2, h, 0)
        else:
            prov = ("rect", e["largeur"], e["profondeur"], h, 0)
        poser(b, suivi, e["id"], cle, e["variante"], dict(e["params"]), (e["x"], plan.NIVEAU_COURONNE, e["z"]),
              e["yaw"], f"Tours/{e['id']}", prov)


def limites(b: Builder) -> None:
    """Barrière de collision invisible et continue sur la ligne des façades (plan.LIMITE_FACADES), qui suit le
    renfoncement de l'esplanade : 8 blocs (est, ouest, sud, nord ×2, flancs ×2, fond), de y 0,4 à 40, transparence 1,
    collision, sans ombre ni studs, groupe Tours/Limites. On ne passe plus dans les coulisses de la couronne."""
    L = plan.LIMITE_FACADES
    r, e = L["retrait"], L["epaisseur"]
    y0, y1 = L["bas"], L["haut"]
    AX, AZS, AZN = plan.ALIGNEMENT_X, plan.ALIGNEMENT_Z_SUD, plan.ALIGNEMENT_Z_NORD
    EX, EZ = plan.ESPLANADE_X, plan.ESPLANADE_Z
    kw = dict(transparency=1.0, collide=True, shadow=False, name="Limite")
    blocs = []
    for s in (1, -1):
        blocs.append((s * (AX + r), s * (AX + r + e), -(AZN + r + e), AZS + r + e))            # est / ouest
        blocs.append((s * (EX + r), s * (AX + r + e), -(AZN + r + e), -(AZN + r)))             # nord, de part et d'autre
        blocs.append((s * (EX + r), s * (EX + r + e), -(EZ + r + e), -(AZN + r)))              # flancs de l'esplanade
    blocs.append((-(AX + r), AX + r, AZS + r, AZS + r + e))                                     # sud
    blocs.append((-(EX + r + e), EX + r + e, -(EZ + r + e), -(EZ + r)))                        # fond de l'esplanade
    with b.group("Tours"):
        with b.group("Limites"):
            for (xa, xb, za, zb) in blocs:
                x0, x1 = sorted((xa, xb))
                z0, z1 = sorted((za, zb))
                b.box((x0, y0, z0), (x1, y1, z1), coul("blanc_labo"), **kw)


def _intervalles_vides() -> list[tuple[str, float, float]]:
    """Intervalles du rang 1 réservés aux repères de milieu de côté (fonction None, largeur ≤ 60) : (côté, s0, s1)."""
    out = []
    for cote, seq in plan.RANG1.items():
        s = plan.COTES[cote]["s0"]
        for item in seq:
            if item[1] is None and item[0] <= 60:
                out.append((cote, s, s + item[0]))
            s += item[0]
    return out


def fonds_de_baie(b: Builder) -> None:
    """Murs pleins derrière les éléments ronds du rang 1 (tours en baie, kiosques ronds), de toute la largeur de leur
    intervalle, à la profondeur de leur axe ; et derrière les repères de milieu de côté, à la profondeur des ailes
    (14) : les interstices de part et d'autre d'un cylindre montrent une façade, pas les coulisses. Dessus à studs."""
    F = plan.FONDS_DE_BAIE
    hy, ep, rb = F["hauteur"], F["epaisseur"], F["retrait_bouts"]
    y0 = plan.NIVEAU_COURONNE - 0.3
    murs = [(e["cote"], e["s0"], e["s1"], e["d"]) for e in plan.CEINTURE if e["rang"] == 1 and e["forme"] == "rond"]
    murs += [(cote, s0, s1, 14.0) for (cote, s0, s1) in _intervalles_vides()]
    with b.group("Tours"):
        with b.group("FondsDeBaie"):
            for (cote, s0, s1, d) in murs:
                pts = [plan.cote_vers_monde(cote, s, dd)[:2] for s in (s0 + rb, s1 - rb) for dd in (d - ep / 2, d + ep / 2)]
                xs, zs = [p[0] for p in pts], [p[1] for p in pts]
                b.box((min(xs), y0, min(zs)), (max(xs), plan.NIVEAU_COURONNE + hy, max(zs)), FOND_BAIE, studs="top",
                      name="FondDeBaie")
            # carrés d'angle : deux murs le long de leurs bords côté rue (x = ±271, z = ±367 / -402), du coin de la
            # rue au mur de fond : vu du carrefour, la placette d'angle (palmiers, grande tour) a des côtés pleins
            AX, CX = plan.ALIGNEMENT_X, plan.COURONNE_X
            e_m = plan.MUR_FOND_EPAISSEUR
            for sx in (1, -1):
                for sz, az, cz in ((1, plan.ALIGNEMENT_Z_SUD, plan.COURONNE_Z_SUD),
                                   (-1, plan.ALIGNEMENT_Z_NORD, plan.COURONNE_Z_NORD)):
                    xa, xb = sorted((sx * (AX + 0.2), sx * (AX + 0.2 + ep)))
                    za, zb = sorted((sz * (az + 0.2), sz * (cz - e_m - 0.1)))
                    b.box((xa, y0, za), (xb, plan.NIVEAU_COURONNE + hy, zb), FOND_BAIE, studs="top", name="FondDAngle")
                    xa, xb = sorted((sx * (AX + 0.2 + ep), sx * (CX - e_m - 0.1)))
                    za, zb = sorted((sz * (az + 0.2), sz * (az + 0.2 + ep)))
                    b.box((xa, y0, za), (xb, plan.NIVEAU_COURONNE + hy, zb), FOND_BAIE, studs="top", name="FondDAngle")


def esplanade(b: Builder, suivi: Suivi) -> None:
    """Port de nacelles de l'esplanade nord : aires rondes à nacelle garée (plan.AIRES_NACELLES)."""
    for a in plan.AIRES_NACELLES:
        R = plan.AIRE_NACELLE_RAYON
        poser(b, suivi, a["id"], "esplanade.aire_nacelle", a["variante"], {"rayon": R},
              (a["x"], plan.NIVEAU_COURONNE, a["z"]), 0, f"Mobilier/{a['id']}", ("rond", R, 0.3, 0))


def _ame(suivi: Suivi, e: dict) -> float:
    r = suivi.resultats.get(e["id"]) or {}
    a = r.get("ame")
    if isinstance(a, (int, float)) and a > 0:
        return float(a)
    return 0.35 * (e.get("diametre_sol") or e["largeur"])


def tubes(b: Builder, suivi: Suivi) -> None:
    """Tubes de verre entre deux tours (plan.TUBES) : bouts dans l'axe des tours (cachés dans leur âme), anneaux sur
    la partie visible seulement ; « fin » : anneaux d'or hexagonaux tous les 24 et fil Neon cyan au cœur ; « geant » :
    anneaux épais jaune d'or / orange tous les 36, tournés de 15° l'un après l'autre ; onde > 0 : tronçons de 24 sur
    une sinusoïde verticale (un anneau à chaque jonction). Sans collision."""
    with b.group("Tours"):
        with b.group("Tubes"):
            for t in plan.TUBES:
                A, B_ = plan.CEINTURE_PAR_ID[t["de"]], plan.CEINTURE_PAR_ID[t["vers"]]
                y = plan.NIVEAU_COURONNE + t["y"]
                pa, pb = np.array([A["x"], y, A["z"]]), np.array([B_["x"], y, B_["z"]])
                L = float(np.linalg.norm(pb - pa))
                u = (pb - pa) / L
                s0, s1 = _ame(suivi, A) + 3, L - _ame(suivi, B_) - 3
                geant = t["type"] == "geant"
                r = plan.TUBE_RAYON[t["type"]]
                pas = plan.TUBE_PAS_ANNEAUX[t["type"]]
                with b.group(t["id"]):
                    # axe : droite, ou sinusoïde verticale sur la partie visible (bouts à la hauteur des quais)
                    if t.get("onde", 0) > 0 and s1 - s0 > 2 * pas:
                        n = max(2, round((s1 - s0) / 24))
                        ss = [0.0] + [s0 + (s1 - s0) * i / n for i in range(n + 1)] + [L]
                        pts = []
                        for s in ss:
                            dy = t["onde"] * math.sin(2 * math.pi * (s - s0) / (s1 - s0)) if s0 <= s <= s1 else 0.0
                            pts.append(pa + u * s + np.array([0, dy, 0]))
                        anneaux_s = ss[1:-1]
                    else:
                        pts = [pa, pb]
                        m = max(1, int((s1 - s0) // pas) + 1) if s1 > s0 else 0
                        debut = (s0 + s1) / 2 - (m - 1) * pas / 2
                        anneaux_s = [debut + i * pas for i in range(m)]
                    for i in range(len(pts) - 1):
                        res = b.tube(pts[i], pts[i + 1], r, VERRE_TUBE, materiau="Glass", transparence=0.5,
                                     coeur=None if geant else coul("cyan"), collide=False, name="Tube")
                        res.regler(collide=False)
                    for i, s in enumerate(anneaux_s):
                        # point et direction sur la polyligne
                        c, d = None, u
                        acc = 0.0
                        for j in range(len(pts) - 1):
                            seg = float(np.linalg.norm(pts[j + 1] - pts[j]))
                            if s <= acc + seg + 1e-6 or j == len(pts) - 2:
                                f = (s - acc) / seg
                                c = pts[j] + (pts[j + 1] - pts[j]) * f
                                d = (pts[j + 1] - pts[j]) / seg
                                if j + 1 < len(pts) - 1 and abs(s - (acc + seg)) < 1e-6:   # jonction
                                    d2 = (pts[j + 2] - pts[j + 1]) / float(np.linalg.norm(pts[j + 2] - pts[j + 1]))
                                    d = (d + d2) / float(np.linalg.norm(d + d2))
                                break
                            acc += seg
                        if geant:
                            col = coul("jaune_or") if i % 2 == 0 else coul("orange")
                            b.anneau(tuple(c), plan.TUBE_RAYON_ANNEAU["geant"], 2.4, col, 12, axe=tuple(d),
                                     section="carre", depart=15 * i,
                                     collide=False, name="Anneau")
                        else:
                            b.anneau(tuple(c), plan.TUBE_RAYON_ANNEAU["fin"], 1.2, OR, 6, axe=tuple(d),
                                     section="carre", collide=False,
                                     name="Anneau")


# =====================================================================================================================
# 4. Le ciel et le mobilier
# =====================================================================================================================

def ciel(b: Builder, suivi: Suivi) -> None:
    o = plan.OEUF
    k = o["echelle"]
    poser(b, suivi, "Oeuf", o["fonction"], o["variante"], {"echelle": k}, (o["x"], o["y"], o["z"]), o["yaw"],
          "Ciel/Oeuf", ("boule", 150 * k))
    cb = plan.CABLE
    poser(b, suivi, "Cable", cb["fonction"], cb["variante"], {"depart": cb["de"], "arrivee": cb["a"]}, (0, 0, 0), 0,
          "Ciel/Cable", lambda bb: bb.cyl_entre(cb["de"], cb["a"], 1.0, PROVISOIRE, collide=False, name="Provisoire"))
    n_volants = len(b.parts)
    for n in plan.NACELLES:
        poser(b, suivi, n["id"], "ciel.nacelle", n["variante"],
              {"rayon": n["rayon"], "inclinaison": plan.NACELLE_INCLINAISON}, (n["x"], n["y"], n["z"]), n["yaw"],
              f"Ciel/Nacelles/{n['id']}", ("boule", n["rayon"]))
    for i, pc in enumerate(plan.PIECES_OR):
        v = 1 if i % 4 == 2 else 0
        poser(b, suivi, pc["id"], plan.PIECE_FONCTION, v, {"rayon": plan.PIECE_RAYON}, (pc["x"], pc["y"], pc["z"]),
              pc["yaw"], f"Ciel/PiecesOr/{pc['id']}",
              lambda bb: bb.cyl((0, 0, 0), plan.PIECE_RAYON, 1.6, PROVISOIRE, axis="z", collide=False,
                                name="Provisoire"))
    dg = plan.DIRIGEABLE
    poser(b, suivi, "Dirigeable", dg["fonction"], dg["variante"], {"longueur": dg["longueur"]},
          (dg["x"], dg["y"], dg["z"]), dg["yaw"], "Ciel/Dirigeable", ("boule", dg["longueur"] / 4))
    # objets volants (nacelles, pièces d'or, dirigeable) sans ombre portée : pas de taches sombres sur la pelouse ni
    # sur les parcelles des joueurs (CastShadow = false dans Roblox ; l'œuf, son nuage et les cumulus n'en ont pas)
    for p in b.parts[n_volants:]:
        p.shadow = False
    for cu in plan.CUMULUS:
        poser(b, suivi, cu["id"], plan.CUMULUS_FONCTION, cu["variante"], {"largeur": cu["largeur"]},
              (cu["x"], cu["y"], cu["z"]), 0, f"Ciel/Cumulus/{cu['id']}", ("boule", cu["largeur"] / 2))
    # skyline lointaine C07 (coordonnées de la carte : pose à l'origine), dans le modèle Ciel (Persistent)
    poser(b, suivi, "Skyline", plan.SKYLINE_FONCTION, 0, {"tours": plan.SKYLINE}, (0, 0, 0), 0, "Ciel/Skyline",
          lambda bb: None)


_PROV_MOBILIER = {"lampadaire": ("rond", 0.6, 9, 0), "groupe_palmiers": None, "jardiniere": None,
                  "banc": ("rect", 5, 2, 2, 0), "poubelle": ("rond", 1, 3, 0), "feu_tricolore": ("rond", 0.6, 10, 0),
                  "potelet": ("rond", 0.5, 3.5, 0), "coupole_miniature": ("rond", 3, 5, 0),
                  "panneau": ("rect", 6, 1, 7, 0), "champignon_lumineux": ("rond", 1.5, 3, 0), "rambarde": None}


def mobilier(b: Builder, suivi: Suivi) -> None:
    for m in plan.MOBILIER:
        nom = m["fonction"].split(".")[1]
        prov = _PROV_MOBILIER.get(nom)
        if nom == "groupe_palmiers":
            prov = ("rond", m["params"].get("diametre", 8) / 2, 20, 0)
        elif nom == "jardiniere":
            prov = ("rect", m["params"].get("largeur", 12), m["params"].get("profondeur", 6), 3, 0)
        elif nom == "rambarde":
            prov = ("rect", m["params"].get("longueur", 16), 0.6, 2.5, 0)
        elif prov is None:
            prov = ("rond", 1, 3, 0)
        poser(b, suivi, m["id"], m["fonction"], m["variante"], dict(m["params"]), (m["x"], m["y"], m["z"]),
              m["yaw"], f"Mobilier/{m['id']}", prov)


# =====================================================================================================================
# Construction
# =====================================================================================================================

def build_carte(seed: int = 7) -> Builder:
    t0 = time.time()
    b = Builder(seed=seed)
    suivi = Suivi()
    pelouse(b)
    trottoirs(b)
    routes(b)
    sol_couronne(b)
    mur_de_fond(b)
    traces_parcelles(b)
    reperes(b)
    tapis_et_centre(b, suivi)
    couronne(b, suivi)
    limites(b)
    fonds_de_baie(b)
    esplanade(b, suivi)
    tubes(b, suivi)
    ciel(b, suivi)
    mobilier(b, suivi)
    b.decouper(("Sol",), taille=plan.DALLE_SOL)
    b._suivi = suivi                       # lu par verifications()
    b._duree = round(time.time() - t0, 1)
    return b


def meta() -> dict:
    return {"nom": NOM, "version": VERSION}


# =====================================================================================================================
# Vérifications
# =====================================================================================================================

def _racine(g: str) -> str:
    return g.split("/")[0]


def _boites(parts):
    pos = np.array([p.pos for p in parts], float)
    size = np.array([p.size for p in parts], float)
    R = np.abs(np.array([p.rot for p in parts], float).reshape(-1, 3, 3))
    half = np.einsum("nij,nj->ni", R, size / 2)
    return pos - half, pos + half


def _inter_rect(lo, hi, x0, x1, z0, z1, marge=0.01):
    """Masque des boîtes dont l'emprise (x, z) coupe le rectangle (strictement, à `marge` près)."""
    return (lo[:, 0] < x1 - marge) & (hi[:, 0] > x0 + marge) & (lo[:, 2] < z1 - marge) & (hi[:, 2] > z0 + marge)


def _points_forme(p, pas: float = 1.0, nmax: int = 48) -> np.ndarray:
    """Points (monde) qui échantillonnent le volume réel d'une pièce (bloc et coin : la boîte ; boule et
    ellipsoïde : l'ellipsoïde inscrit ; cylindre : axe X local, comme dans Roblox). Sert à juger l'emprise vraie
    d'une forme ronde, que sa boîte englobante surestime (un pneu de Ø 100 n'occupe pas les coins de sa boîte)."""
    size = np.asarray(p.size, float)
    n = [int(min(nmax, max(2, math.ceil(s / pas) + 1))) for s in size]
    axes = [np.linspace(-1.0, 1.0, k) for k in n]
    u, v, w = np.meshgrid(*axes, indexing="ij")
    u, v, w = u.ravel(), v.ravel(), w.ravel()
    if p.shape in ("ball", "ellipsoid"):
        m = u * u + v * v + w * w <= 1.0 + 1e-9
    elif p.shape == "cyl":
        m = v * v + w * w <= 1.0 + 1e-9
    else:
        m = np.ones(u.shape, bool)
    loc = np.stack([u[m], v[m], w[m]], axis=1) * (size / 2)
    R = np.asarray(p.rot, float).reshape(3, 3)
    return loc @ R.T + np.asarray(p.pos, float)


def _aire_praticable(pts: np.ndarray, ymin: float = -1e9, ymax: float = 1e9) -> int:
    """Aire (studs², cases de 1 × 1) de la projection au sol des points dont y ∈ [ymin, ymax], au-dessus d'une zone
    praticable (pelouse, trottoirs, route : en deçà de la ligne des façades)."""
    m = (pts[:, 1] >= ymin) & (pts[:, 1] <= ymax) & (_profondeur_praticable(pts) > 0)
    if not m.any():
        return 0
    cases = np.unique(np.floor(pts[m][:, [0, 2]]).astype(np.int64), axis=0)
    return int(len(cases))


def _cases_praticables(pts: np.ndarray) -> np.ndarray:
    """Cases (1 × 1, indices entiers) couvertes par la projection au sol des points, en deçà de la ligne des façades
    (zones praticables : pelouse, trottoirs, route, esplanade)."""
    m = _profondeur_praticable(pts) > 0
    if not m.any():
        return np.zeros((0, 2), np.int64)
    return np.unique(np.floor(pts[m][:, [0, 2]]).astype(np.int64), axis=0)


def _aire_sous(parts, lo, hi, i: int, porteuses: np.ndarray) -> int:
    """Aire praticable (studs²) sous la pièce i : cases de son emprise vraie où la hauteur libre entre le dessus du
    plus haut support placé dessous (pièce à collision qui monte du sol ; à défaut le sol, y 0) et le dessous de la
    pièce vaut de 5 à 40 (un personnage peut s'y tenir, la caméra Roblox y sauterait)."""
    cases = _cases_praticables(_points_forme(parts[i], pas=1.0, nmax=128))
    if not len(cases):
        return 0
    y_bas = float(lo[i, 1])
    # obstacles de la colonne : pièces à collision qui commencent sous la pièce (un volume qui la traverse, comme
    # le cylindre de collision d'un œuf posé, bouche toute la hauteur : dessus effectif = y_bas)
    cand = porteuses & (lo[:, 0] < hi[i, 0]) & (hi[:, 0] > lo[i, 0]) & (lo[:, 2] < hi[i, 2]) & \
        (hi[:, 2] > lo[i, 2]) & (lo[:, 1] < y_bas - 1e-6)
    cand[i] = False
    dessus = {}
    cles = {(int(a), int(c)) for a, c in cases}
    for j in np.flatnonzero(cand):
        haut_j = min(float(hi[j, 1]), y_bas)
        for a, c in _cases_praticables(_points_forme(parts[j], pas=1.0, nmax=64)):
            k = (int(a), int(c))
            if k in cles and haut_j > dessus.get(k, 0.0):
                dessus[k] = haut_j
    return sum(1 for k in cles if 5.0 <= y_bas - dessus.get(k, 0.0) < plan.HAUTEUR_LIBRE)


def _profondeur_praticable(pts: np.ndarray) -> np.ndarray:
    """Distance signée de chaque point (x, z) au bord des zones praticables (plan.ZONES_PRATICABLES : tout ce qui est
    en deçà de la ligne des façades, esplanade nord comprise) : > 0 dedans, ≤ 0 dans la couronne ou au-delà."""
    out = np.full(len(pts), -1e9)
    for (x0, x1, z0, z1) in plan.ZONES_PRATICABLES:
        d = np.minimum.reduce([pts[:, 0] - x0, x1 - pts[:, 0], pts[:, 2] - z0, z1 - pts[:, 2]])
        out = np.maximum(out, d)
    return out


def _devant_facade(pts: np.ndarray) -> np.ndarray:
    """Profondeur de chaque point devant la ligne des façades (> 0 : côté rue ; ≤ 0 : dans la couronne)."""
    return _profondeur_praticable(pts)


def _hors_emprise(e: dict, pts: np.ndarray) -> np.ndarray:
    """Distance de chaque point (x, z) hors de l'emprise au sol de l'emplacement e (0 dedans). Rang 1 : tout le
    rectangle largeur × profondeur de l'intervalle (le socle d'une fusée, R D/2 + 1, ou le socle carré d'un kiosque
    rond y ont droit) ; rang 2 et coins : le disque du diamètre au sol."""
    forme = plan.emprise_slot(e) if e.get("rang") != 1 else ("rect",)
    if forme[0] == "cercle":
        _, cx, cz, r = forme
        return np.clip(np.hypot(pts[:, 0] - cx, pts[:, 2] - cz) - r, 0, None)
    yaw = math.radians(e["yaw"])
    ux, uz = math.cos(yaw), -math.sin(yaw)
    vx, vz = math.sin(yaw), math.cos(yaw)
    dx, dz = pts[:, 0] - e["x"], pts[:, 2] - e["z"]
    a, c = dx * ux + dz * uz, dx * vx + dz * vz
    return np.hypot(np.clip(np.abs(a) - e["largeur"] / 2, 0, None), np.clip(np.abs(c) - e["profondeur"] / 2, 0, None))


def verifications(b: Builder) -> dict:
    """Contrôles de la carte : toutes les listes de « problemes » doivent rester vides."""
    parts = b.parts
    suivi: Suivi | None = getattr(b, "_suivi", None)
    ctl = controles(parts)
    lo, hi = _boites(parts)
    groupes = [p.group for p in parts]
    racines = np.array([_racine(g) for g in groupes])
    solide = np.array([p.collide and p.transparency < 0.99 for p in parts])
    visible = np.array([p.transparency < 0.99 for p in parts])
    problemes = dict(ctl["problemes"])
    pb: dict[str, list] = defaultdict(list)

    def nomme(i):
        return f"{groupes[i]}/{parts[i].name}"

    # --- parcelles et escaliers vides (seuls Sol, Reperes, TracesParcelles) entre y 0,3 et 80 -----------------------
    exempt = np.isin(racines, ["Sol", GROUPE_REPERES, "TracesParcelles"])
    haut = (hi[:, 1] > 0.3) & (lo[:, 1] < 80) & ~exempt
    for p in plan.PARCELLES:
        m = haut & _inter_rect(lo, hi, p["x0"], p["x1"], p["z0"], p["z1"])
        pb["parcelles_occupees"] += [(p["id"], nomme(i)) for i in np.flatnonzero(m)[:3]]
        e = p["escalier"]
        m = haut & _inter_rect(lo, hi, e["x0"], e["x1"], e["z0"], e["z1"])
        pb["escaliers_occupes"] += [(p["id"], nomme(i)) for i in np.flatnonzero(m)[:3]]
    # --- allées de marche libres : rien de solide entre y 0,3 et 12 --------------------------------------------------
    for c in plan.COULOIRS_MARCHE:
        m = solide & (hi[:, 1] > 0.3) & (lo[:, 1] < 12) & ~exempt & _inter_rect(lo, hi, c["x0"], c["x1"], c["z0"], c["z1"])
        pb["allees_encombrees"] += [(c["id"], nomme(i)) for i in np.flatnonzero(m)[:5]]
    # --- hauteur libre : rien de large dont le dessous est entre 5 et 40 au-dessus d'une zone praticable -------------
    aire = np.zeros(len(parts))
    for (x0, x1, z0, z1) in plan.ZONES_PRATICABLES:
        ix0, ix1 = np.maximum(lo[:, 0], x0), np.minimum(hi[:, 0], x1)
        iz0, iz1 = np.maximum(lo[:, 2], z0), np.minimum(hi[:, 2], z1)
        aire += np.clip(ix1 - ix0, 0, None) * np.clip(iz1 - iz0, 0, None)
    # liste blanche : toits du stand et des kiosques du U, lampadaires, palmes, panneaux (SPECS), et l'œuf du monument, une sculpture posée
    # sur son plateau (sa coquille déborde de 2,5 au plus de son cylindre de collision : personne ne passe dessous)
    blanche = np.array([g.startswith(("Centre/Vente", "Centre/Kiosque_", "Centre/Monument/Oeuf", "Tapis/Portail_",
                                      "Mobilier/Lampe", "Mobilier/Palmier", "Mobilier/Panneau", "Provisoire/"))
                        for g in groupes])
    m = visible & (lo[:, 1] > 5) & (lo[:, 1] < plan.HAUTEUR_LIBRE) & (aire > 64) & ~blanche
    # supports possibles : pièces à collision (même invisibles) qui montent du sol (hors dalles de sol)
    porteuses = np.array([p.collide for p in parts]) & (hi[:, 1] > 1.0) & \
        ~np.isin(racines, ["Sol", "Trottoirs", "Routes", GROUPE_REPERES, "TracesParcelles"])
    for i in np.flatnonzero(m):
        # emprise vraie (une forme ronde n'occupe pas les coins de sa boîte) ; une case ne compte que si l'on peut se
        # tenir dessous : entre le dessus du support le plus haut sous la pièce (le sol sinon) et son dessous, 5 à 40
        a = _aire_sous(parts, lo, hi, i, porteuses)
        if a > 64 and len(pb["hauteur_libre"]) < 8:
            pb["hauteur_libre"].append((nomme(i), round(float(lo[i, 1]), 1), a))
    # --- couronne : rien devant la ligne des façades sous y 8 ; au plus 1,5 de saillie entre 8 et 40 -----------------
    tours = np.array([g.startswith("Tours/") and not g.startswith(("Tours/Tubes", "Tours/MurDeFond")) for g in groupes])
    yc = plan.NIVEAU_COURONNE
    dans_zone = np.zeros(len(parts), bool)
    for (x0, x1, z0, z1) in plan.ZONES_PRATICABLES:
        dans_zone |= _inter_rect(lo, hi, x0, x1, z0, z1, marge=0.05)
    m = tours & visible & (lo[:, 1] < yc + 40) & dans_zone
    for i in np.flatnonzero(m):
        pts = _points_forme(parts[i], pas=0.5)
        prof = _devant_facade(pts)
        y = pts[:, 1] - yc
        bas = (y < 8) & (prof > 0.05)
        milieu = (y >= 8) & (y < 40) & (prof > 1.5)
        if (bas | milieu).any() and len(pb["devant_facades"]) < 10:
            pb["devant_facades"].append((nomme(i), round(float(prof[bas | milieu].max()), 2),
                                         round(float(y[bas | milieu].min()), 1)))
    # --- emplacements de la couronne : sous y 40, chaque asset reste dans son emprise (information, à 0,5 près) ------
    debord: dict = {}
    for i in np.flatnonzero(tours & visible & (lo[:, 1] < yc + 40)):
        ident = groupes[i].split("/")[1]
        e = plan.CEINTURE_PAR_ID.get(ident)
        if e is None:
            continue
        coins = np.array([[x, z] for x in (lo[i, 0], hi[i, 0]) for z in (lo[i, 2], hi[i, 2])])
        if _hors_emprise(e, np.stack([coins[:, 0], np.zeros(4), coins[:, 1]], axis=1)).max() <= 0.5:
            continue
        pts = _points_forme(parts[i], pas=1.0, nmax=20)
        pts = pts[pts[:, 1] < yc + 40]
        if len(pts):
            d = float(_hors_emprise(e, pts).max())
            if d > 0.5 and d > debord.get(ident, (0, ""))[0]:
                debord[ident] = (round(d, 1), parts[i].name)
    # --- tailles : 0,1 stud au moins sur chaque axe (règle de la carte) ------------------------------------------------
    fines = [nomme(i) for i, p in enumerate(parts) if min(p.size) < 0.1 - 1e-6 and p.group != GROUPE_REPERES]
    if fines:
        pb["trop_fines"] += fines[:10]
    # --- fenêtre de l'œuf : aucun bâtiment au-dessus de la hauteur maximale dans |x| < 70, au fond de l'esplanade ----
    F = plan.FENETRE_OEUF
    m = tours & visible & (hi[:, 1] > F["hauteur_max"] + plan.NIVEAU_COURONNE + 1e-6) & \
        _inter_rect(lo, hi, F["x0"], F["x1"], F["z0"], F["z1"])
    pb["fenetre_oeuf"] += [(nomme(i), round(float(hi[i, 1]), 1)) for i in np.flatnonzero(m)[:8]]
    # --- repères des parcelles et des entrées : boîte monde = géométrie du plan (0,01 près), avant vers le tapis -------
    rep = {p.name: i for i, p in enumerate(parts) if p.group == GROUPE_REPERES}
    for pc in plan.PARCELLES:
        es = pc["escalier"]
        signe = 1 if pc["cote"] == "E" else -1
        for nom, (x0, x1, z0, z1) in ((f"Parcelle_{pc['id']}", (pc["x0"], pc["x1"], pc["z0"], pc["z1"])),
                                     (f"Entree_{pc['id']}", (es["x0"], es["x1"], es["z0"], es["z1"]))):
            i = rep.get(nom)
            if i is None:
                continue
            ecarts = [abs(float(v) - w) for v, w in ((lo[i, 0], x0), (hi[i, 0], x1), (lo[i, 2], z0), (hi[i, 2], z1))]
            avant = -np.array(parts[i].rot, float).reshape(3, 3)[:, 2]        # LookVector (-Z local)
            if max(ecarts) > 0.01 or avant[0] * -signe < 0.999 or abs(float(lo[i, 1])) > 0.01:
                pb["reperes_parcelles"].append((nom, [round(float(v), 2) for v in (lo[i, 0], hi[i, 0], lo[i, 2],
                                                                                    hi[i, 2])],
                                                [round(float(v), 3) for v in avant]))
    # --- visée de l'œuf : depuis l'œil d'apparition, les bâtiments de la fenêtre restent sous le dessous du nuage ----
    ox, oy, oz = plan.OEIL_APPARITION
    dans_f = tours & visible & _inter_rect(lo, hi, F["x0"], F["x1"], F["z0"], F["z1"])
    elev_bat = [math.degrees(math.atan2(hi[i, 1] - oy, oz - hi[i, 2])) for i in np.flatnonzero(dans_f)
                if oz - hi[i, 2] > 1]
    nuage = [i for i, g in enumerate(groupes) if g.startswith("Ciel/Oeuf/Nuage")]
    # minorant de l'angle du bas du nuage : coin bas et avant de la boîte de chaque flocon (plus bas et plus proche que
    # la surface réelle) ; on ne garde que les flocons dans le cône de la fenêtre (|azimut| ≤ 20°)
    elev_nuage = [math.degrees(math.atan2(lo[i, 1] - oy, oz - hi[i, 2])) for i in nuage
                  if abs(math.degrees(math.atan2(pos_x := (lo[i, 0] + hi[i, 0]) / 2 - ox, oz - hi[i, 2]))) <= 20]
    visee = {"batiments_max_deg": round(max(elev_bat), 2) if elev_bat else None,
             "nuage_bas_deg": round(min(elev_nuage), 2) if elev_nuage else None}
    if elev_bat and elev_nuage and max(elev_bat) >= min(elev_nuage):
        pb["visee_oeuf"].append(visee)
    # --- repères ----------------------------------------------------------------------------------------------------
    noms_rep = [p.name for p in parts if p.group == GROUPE_REPERES]
    spawn = [p for p in parts if p.group == GROUPE_REPERES and p.name == "Spawn"]
    if len(spawn) != 1:
        pb["spawn"].append(f"{len(spawn)} repère(s) Spawn au lieu de 1")
    manquants = sorted({r["nom"] for r in plan.REPERES} - set(noms_rep))
    if manquants:
        pb["reperes_manquants"] += manquants
    doublons = sorted({n for n in noms_rep if noms_rep.count(n) > 1})
    if doublons:
        pb["reperes_doublons"] += doublons
    # --- sol à studs ------------------------------------------------------------------------------------------------
    for i in np.flatnonzero(np.isin(racines, ["Sol", "Trottoirs", "Routes"])):
        if parts[i].shape == "block" and "Top" not in parts[i].studs:
            pb["sol_sans_studs"].append(nomme(i))
    # --- faces confondues du sol (toutes, même teinte comprise : taches noires dans Cycles) -------------------------
    sol_parts = [p for p in parts if _racine(p.group) in ("Sol", "Trottoirs", "Routes", "TracesParcelles")
                 or p.group.startswith("Tours/MurDeFond")]
    fc_pb, fc_memes = _faces_confondues(sol_parts)
    fc_sol = fc_pb + fc_memes
    if fc_sol:
        pb["faces_confondues_sol"] += fc_sol[:10]
    # --- budgets ----------------------------------------------------------------------------------------------------
    BC = plan.BUDGET_CARTE
    if ctl["pieces"] > BC["pieces"]:
        pb["hors_budget"].append(f"carte : {ctl['pieces']} pièces > {BC['pieces']}")
    if ctl["neon"] > BC["neon"]:
        pb["hors_budget"].append(f"carte : {ctl['neon']} Neon > {BC['neon']}")
    if ctl["transparentes"] > BC["transparentes"]:
        pb["hors_budget"].append(f"carte : {ctl['transparentes']} transparentes > {BC['transparentes']}")
    par_module: dict = {}
    appels_hors = []
    provisoires = []
    if suivi is not None:
        tot = defaultdict(lambda: [0, 0, 0])
        for a in suivi.appels:
            if a["provisoire"]:
                tot["provisoires"][0] += a["pieces"]
                continue
            mod = _module_budget(a["fonction"])
            for k, v in enumerate((a["pieces"], a["neon"], a["transp"])):
                tot[mod][k] += v
            cap = plan.budget_appel(a["fonction"], a["params"], a["variante"])
            if a["pieces"] > cap[0] or a["neon"] > cap[1] or a["transp"] > cap[2]:
                appels_hors.append((a["id"], a["fonction"], a["variante"], (a["pieces"], a["neon"], a["transp"]),
                                    tuple(round(v) for v in cap)))
        propres = _compter([p for p in parts if not p.group.startswith(("Provisoire/",)) and
                            _racine(p.group) in ("Sol", "Trottoirs", "Routes", "TracesParcelles", GROUPE_REPERES)
                            or p.group.startswith(("Tours/MurDeFond", "Tours/Tubes", "Tours/Limites",
                                                   "Tours/FondsDeBaie"))])
        tot["carte"] = list(propres)
        for mod, (cap, capn, capt) in plan.BUDGETS.items():
            v = tot.get(mod, [0, 0, 0])
            par_module[mod] = {"pieces": v[0], "plafond": cap, "neon": v[1], "plafond_neon": capn,
                               "transp": v[2], "plafond_transp": capt}
            if v[0] > cap or v[1] > capn or v[2] > capt:
                pb["hors_budget"].append(f"module {mod} : {tuple(v)} > {(cap, capn, capt)}")
        par_module["provisoires"] = {"pieces": tot["provisoires"][0]}
        if appels_hors:
            pb["hors_budget"] += [f"appel {a[0]} ({a[1]} v{a[2]}) : {a[3]} > {a[4]}" for a in appels_hors[:20]]
        provisoires = suivi.provisoires
    problemes.update({k: v for k, v in pb.items() if v})
    lo_all, hi_all = bornes(parts)
    return {
        "pieces": ctl["pieces"],
        "par_forme": ctl["par_forme"],
        "neon": ctl["neon"],
        "verre": ctl["verre"],
        "transparentes": ctl["transparentes"],
        "pieces_a_studs": ctl["pieces_a_studs"],
        "sans_collision": ctl["sans_collision"],
        "reperes": len(noms_rep),
        "spawn": [round(v, 2) for v in spawn[0].pos] if spawn else None,
        "emprise": {"min": [round(float(v), 1) for v in lo_all], "max": [round(float(v), 1) for v in hi_all]},
        "par_module": par_module,
        "provisoires": [f"{p['id']} ({p['fonction']}) : {p['raison']}" for p in provisoires],
        "nb_provisoires": len(provisoires),
        # information : emplacements de la couronne dont l'asset sort de son emprise sous y 40 (id → (écart, pièce))
        "debordements": dict(sorted(debord.items(), key=lambda kv: -kv[1][0])),
        "visee_oeuf": visee,
        "faces_confondues_meme_teinte": ctl["faces_confondues_meme_teinte"],
        "problemes": problemes,
    }


def faces_par_module(b: Builder) -> dict:
    """Diagnostic pour les constructeurs : faces confondues comptées module par module (chaque module seul ; les
    coïncidences entre deux modules restent dans verifications()["problemes"]["faces_confondues"])."""
    suivi: Suivi = b._suivi
    mod_de = {a["id"]: ("provisoires" if a["provisoire"] else _module_budget(a["fonction"])) for a in suivi.appels}
    paquets = defaultdict(list)
    for p in b.parts:
        g = p.group.split("/")
        if g[0] in ("Tours", "Centre", "Mobilier") and len(g) > 1 and g[1] in mod_de:
            mod = mod_de[g[1]]
        elif g[0] == "Tapis":
            mod = "tapis+centre"
        elif g[0] == "Ciel":
            mod = "ciel"
        elif g[0] == "Provisoire":
            mod = "provisoires"
        else:
            mod = "carte"
        paquets[mod].append(p)
    out = {}
    module_de_part = {}
    for mod in sorted(paquets):
        pbs, memes = _faces_confondues(paquets[mod], limite=400)
        out[mod] = (len(pbs), len(memes), pbs[:2])
        for p in paquets[mod]:
            module_de_part[f"{p.group}/{p.name}"] = mod
    # coïncidences entre deux modules (un asset contre le sol, deux poses voisines…)
    pbs, _ = _faces_confondues(b.parts, limite=3000)
    inter = [(a, c, ar) for (a, c, ar) in pbs
             if module_de_part.get(a.rsplit(".", 1)[0]) != module_de_part.get(c.rsplit(".", 1)[0])]
    out["inter-modules"] = (len(inter), 0, inter[:3])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / "build" / "parts.json"))
    ap.add_argument("--stats", action="store_true", help="pièces par groupe racine et par module")
    ap.add_argument("--export", default=None, help="dossier : export Roblox avec Lune (sans Blender)")
    args = ap.parse_args()
    b = build_carte()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    b.save_json(out, meta=meta())
    v = verifications(b)
    court = {k: x for k, x in v.items() if k not in ("provisoires", "par_module")}
    print(json.dumps({"fichier": str(out), "secondes": b._duree, **court}, ensure_ascii=False, default=str))
    if args.stats:
        print("pièces par groupe racine :")
        for k, n in b.stats().items():
            print(f"  {n:6d}  {k}")
        print("par module (pièces, Neon, transparentes / plafonds) :")
        for k, d in v["par_module"].items():
            print(f"  {k:14s} {json.dumps(d, ensure_ascii=False)}")
        print("faces confondues par module (problèmes, même teinte ; premiers cas) :")
        for k, (n_pb, n_memes, ex) in faces_par_module(b).items():
            print(f"  {k:14s} {n_pb:4d} {n_memes:4d}  {json.dumps(ex, ensure_ascii=False)[:400]}")
        hors = [a for a in b._suivi.appels if not a["provisoire"]
                and any(x > c for x, c in zip((a["pieces"], a["neon"], a["transp"]),
                                              plan.budget_appel(a["fonction"], a["params"], a["variante"])))]
        if hors:
            print(f"appels hors budget ({len(hors)}) :")
            for a in hors:
                cap = tuple(round(x) for x in plan.budget_appel(a["fonction"], a["params"], a["variante"]))
                print(f"  {a['id']:16s} {a['fonction']:30s} v{a['variante']} {(a['pieces'], a['neon'], a['transp'])}"
                      f" > {cap}")
    if v["provisoires"]:
        print(f"provisoires ({len(v['provisoires'])}) :")
        par_raison = defaultdict(list)
        for p in b._suivi.provisoires:
            par_raison[(p["fonction"], p["raison"])].append(p["id"])
        for (f, r), ids in sorted(par_raison.items()):
            print(f"  {f:34s} x{len(ids):3d}  {r}  [{', '.join(ids[:4])}{' …' if len(ids) > 4 else ''}]")
    if args.export:
        print(json.dumps(exporter_roblox(out, args.export), ensure_ascii=False))


if __name__ == "__main__":
    main()
