#!/usr/bin/env python3
"""Plan de la carte « île du futur » (CarteEgghead) : toutes les cotes, en un seul endroit.

Ce module ne dépend que de la bibliothèque standard (pas de bpy, pas de numpy) : carte.py, les assets et les
scripts de contrôle l'importent. Une correction du plan se fait ici et nulle part ailleurs.

Repère (celui de Roblox et du kit) : origine = centre de la carte au niveau du sol (dessus de la pelouse, y = 0) ;
+X = droite de la capture refEH1 (est), +Z = vers la caméra de refEH1 (sud), le nord est -Z ; 1 unité = 1 stud ;
yaw en degrés autour de Y. L'avant d'un asset regarde -Z local ; posé avec `b.at(pos, yaw)`, son avant regarde
(-sin yaw, 0, -cos yaw) et son axe X local devient (cos yaw, 0, -sin yaw).

Source des formes et des tailles : la reconstruction métrique de l'analyste A (deux caméras calibrées, échelle
vérifiée de trois façons ; moitié sud ±0,5 à 3 studs, moitié nord en miroir ±10 à 25), arrondie au stud entier
quand la mesure le permet (±0,5). Le thème change l'aspect, jamais la géométrie.

    python plan.py          # imprime un résumé (bandes, tapis, couronne, comptes)
"""

from __future__ import annotations

import math

# =====================================================================================================
# 1. Bandes du sol (rectangles concentriques centrés sur l'origine ; demi-largeur en X, demi-longueur en Z)
# =====================================================================================================

PELOUSE_X = 205            # pelouse : |x| ≤ 205 (mesuré 204,5 ± 0,7)
PELOUSE_Z = 301            # pelouse : |z| ≤ 301 (mesuré 300,9 au sud ; nord en miroir)
TROTTOIR_INT_X = 217       # trottoir intérieur : 205 → 217 (12) à l'est et à l'ouest
TROTTOIR_INT_Z = 313       # trottoir intérieur : 301 → 313 (12) au nord et au sud
ROUTE_X = 253              # route : 217 → 253 (36)
ROUTE_Z = 349              # route : 313 → 349 (36)
TROTTOIR_EXT_X = 271       # trottoir extérieur : 253 → 271 (18)
TROTTOIR_EXT_Z = 367       # trottoir extérieur : 349 → 367 (18)
ALIGNEMENT_X = TROTTOIR_EXT_X   # ligne des façades de la couronne (est / ouest)
ALIGNEMENT_Z = TROTTOIR_EXT_Z   # ligne des façades de la couronne (nord / sud)
COURONNE_PROFONDEUR = 80        # profondeur de la couronne de bâtiments derrière la ligne des façades
COURONNE_X = ALIGNEMENT_X + COURONNE_PROFONDEUR   # 351 : bord extérieur de la couronne
COURONNE_Z = ALIGNEMENT_Z + COURONNE_PROFONDEUR   # 447
MUR_FOND_EPAISSEUR = 2          # mur de fond continu au bord extérieur de la couronne (filet de sécurité)
MUR_FOND_HAUTEUR = 36           # ferme toute vue à hauteur d'œil, même par une ruelle

TROTTOIR_LARGEUR_INT = TROTTOIR_INT_X - PELOUSE_X      # 12
ROUTE_LARGEUR = ROUTE_X - TROTTOIR_INT_X                # 36
TROTTOIR_LARGEUR_EXT = TROTTOIR_EXT_X - ROUTE_X         # 18

# Niveaux (dessus des surfaces). Le sol de référence (y = 0) est la pelouse ; route et couronne sont aussi à 0
# sauf la couronne, posée au niveau des trottoirs pour que les parvis d'angle prolongent le trottoir.
NIVEAU_PELOUSE = 0.0
NIVEAU_ROUTE = 0.0
NIVEAU_TROTTOIR = 0.4      # trottoirs intérieur et extérieur : marche de 0,4 depuis la pelouse et la route
NIVEAU_COURONNE = 0.4      # sol de la couronne (prolonge le trottoir extérieur) : y de pose des bâtiments
NIVEAU_MARQUAGE = 0.1      # dessus des marquages de la route (épaisseur 0,1 posée sur la route)
EPAISSEUR_DALLE = 2.0      # toutes les dalles de sol descendent jusqu'à y = -2

# Grille de la pelouse (marqueur n° 1 de l'île) : lignes d'1 stud au pas de 8, chacune sur [8k, 8k + 1]
GRILLE_PAS = 8
GRILLE_LARGEUR = 1
GRILLE_HAUT_LIGNES_Z = 0.15   # lignes le long de Z (x fixe) : dessus à 0,15
GRILLE_HAUT_LIGNES_X = 0.20   # lignes le long de X (z fixe) : dessus à 0,20 (elles passent dessus aux croisements)
DALLE_SOL = 64                # dalles de 64 × 64 alignées sur les multiples de 64 (bandes de bord pour compléter)

# Route : deux voies de 18, ligne médiane en tirets, lignes de rive, flèches, passages piétons
ROUTE_AXE_X = (TROTTOIR_INT_X + ROUTE_X) / 2     # 235 : axe des routes est / ouest
ROUTE_AXE_Z = (TROTTOIR_INT_Z + ROUTE_Z) / 2     # 331 : axe des routes nord / sud
VOIE_LARGEUR = ROUTE_LARGEUR / 2                  # 18
TIRET_LARGEUR = 1                                 # tirets sur [235, 236] (coins entiers)
TIRET_LONGUEUR = 6
TIRET_PAS = 16                                    # 6 de trait, 10 de vide
TIRET_ARRET_COIN = 4                              # les tirets s'arrêtent à 4 studs des carrés d'angle
LIGNE_RIVE_LARGEUR = 1
LIGNE_RIVE_RETRAIT = 2                            # ligne de rive sur [217 + 2, 217 + 3] et [253 - 3, 253 - 2]
FLECHE_PAS = 96                                   # une flèche par voie tous les 96, décalée de 48 d'une voie à l'autre
FLECHE_LONGUEUR = 9                               # hampe 1,4 × 6 + tête en chevron de 3
BORDURE_LARGEUR = 1                               # bordure rayée rouge et blanc côté route des deux trottoirs
BORDURE_DESSUS = NIVEAU_TROTTOIR + 0.2            # 0,6 : la bordure dépasse le trottoir de 0,2
BORDURE_RAYURE = 4                                # 4 rouges, 4 blancs (bloc rouge en saillie de 0,1)

# Sens de circulation (flèches) : voie intérieure dans le sens antihoraire vu du dessus (sud : vers +X, est :
# vers -Z, nord : vers -X, ouest : vers +Z), voie extérieure en sens inverse (mesuré sur la route sud).
SENS_VOIE_INTERIEURE = "antihoraire"

# Passages piétons (zébras de 2 × 10, 9 bandes) : sur la route est en z ≈ 134 (mesuré), répétés en miroir
PASSAGE_LARGEUR = 10
PASSAGE_BANDE = 2
PASSAGE_ECART = 2
PASSAGES_PIETONS = [
    {"id": "Passage_E_Sud", "cote": "est", "s": 134.0},
    {"id": "Passage_E_Nord", "cote": "est", "s": -134.0},
    {"id": "Passage_O_Sud", "cote": "ouest", "s": 134.0},
    {"id": "Passage_O_Nord", "cote": "ouest", "s": -134.0},
]

# =====================================================================================================
# 2. Tapis roulant (U ouvert, refermé au sud ; sens antihoraire vu du dessus)
# =====================================================================================================

TAPIS_LARGEUR = 16.1        # bande = bordure 3,1 + tapis 9,9 + bordure 3,1
TAPIS_BANDE = 9.9
TAPIS_BORDURE = 3.1
TAPIS_AXE_X = 48.38          # axes des deux voies droites : x = ±48,38
TAPIS_BORD_INT_X = 40.33     # bords intérieurs ±40,33
TAPIS_BORD_EXT_X = 56.43     # bords extérieurs ±56,43
TAPIS_DESSUS = 0.6           # dessus de la bande sombre
TAPIS_DESSUS_BORDURE = 1.0   # dessus des bordures (la bande est en creux de 0,4 entre elles)
TAPIS_Z_TETE = -281.0        # tête des voies (mesurée) : là où la bande entre dans les portails
TAPIS_Z_FOND = -293.0        # bout physique de la bande, sous le portail, contre son fond
TAPIS_Z_APPARITION = -287.0  # point où les objets apparaissent (ouest) et disparaissent (est)
TAPIS_Z_VIRAGE = 258.46      # début du demi-octogone au sud

# Axe du tapis dans le sens du flux : tête ouest → vers le sud → demi-tour d'ouest en est → tête est
TAPIS_AXE = [
    (-48.38, TAPIS_Z_APPARITION),
    (-48.38, 258.46),
    (-40.43, 276.22),
    (-28.69, 286.28),
    (28.69, 286.28),
    (40.43, 276.22),
    (48.38, 258.46),
    (48.38, TAPIS_Z_APPARITION),
]
# Polygones du demi-tour (mesurés, ajustés au 1/10 de stud) : bord intérieur et bord extérieur de la bande
TAPIS_VIRAGE_INT = [(-40.33, 256.72), (-33.91, 271.25), (-25.77, 278.22),
                    (25.77, 278.22), (33.91, 271.25), (40.33, 256.72)]
TAPIS_VIRAGE_EXT = [(-56.43, 260.15), (-47.05, 281.16), (-31.67, 294.34),
                    (31.67, 294.34), (47.05, 281.16), (56.43, 260.15)]
# Tronçons droits de la bande (axe), dans le sens du flux ; la voie ouest descend vers +Z, la voie est remonte
TAPIS_TRONCONS = [
    {"id": "Voie_Ouest", "de": (-48.38, TAPIS_Z_FOND), "a": (-48.38, 258.46)},
    {"id": "Virage_O1", "de": (-48.38, 258.46), "a": (-40.43, 276.22)},
    {"id": "Virage_O2", "de": (-40.43, 276.22), "a": (-28.69, 286.28)},
    {"id": "Virage_Sud", "de": (-28.69, 286.28), "a": (28.69, 286.28)},
    {"id": "Virage_E2", "de": (28.69, 286.28), "a": (40.43, 276.22)},
    {"id": "Virage_E1", "de": (40.43, 276.22), "a": (48.38, 258.46)},
    {"id": "Voie_Est", "de": (48.38, 258.46), "a": (48.38, TAPIS_Z_FOND)},
]
CHEVRON_PAS = 8.5            # un chevron blanc tous les 8,5 le long de l'axe (mesuré ≈ 8,5)
CHEVRON_LARGEUR = 9.0        # envergure du « V » à travers la bande (≤ 9,9)
CHEVRON_PROFONDEUR = 3.5     # flèche du « V » dans le sens du flux
CHEVRON_TRAIT = 1.2          # largeur d'un bras

# Portails des têtes de voies (nord) : arche au-dessus de la bande, ouverture vers le sud (le tapis)
PORTAIL_LARGEUR = 30         # emprise en X (centrée sur l'axe de la voie)
PORTAIL_PROFONDEUR = 16      # emprise en Z : de -297 à -281
PORTAIL_HAUTEUR = 36
PORTAIL_OUVERTURE = 18.5     # passage libre entre les piliers (la bande fait 16,1)
PORTAILS = [
    {"id": "Portail_Ouest", "role": "entree", "x": -48.38, "z": -289.0, "yaw": 180, "variante": 0},
    {"id": "Portail_Est", "role": "sortie", "x": 48.38, "z": -289.0, "yaw": 180, "variante": 1},
]

# =====================================================================================================
# 3. Pièces du centre (dans le U) et apparition
# =====================================================================================================
# Chaque pièce : centre (x, z), emprise (x, z), hauteur, yaw (avant = côté où l'on joue), fonction de SPECS.md
CENTRE = {
    "Vente": {"x": -17.0, "z": 242.0, "emprise": (28, 28), "hauteur": 18, "yaw": 0,
              "fonction": "centre.stand_vente", "variante": 0,
              "note": "stand ; l'avant regarde le nord ; zone de vente = demi-disque r 14 au nord (pointillés)"},
    "Machine": {"x": 25.0, "z": 240.0, "emprise": (12, 10), "hauteur": 15, "yaw": 0,
                "fonction": "centre.machine", "variante": 0},
    "Monument": {"x": 0.0, "z": 127.0, "emprise": (34, 34), "hauteur": 32, "yaw": 180,
                 "fonction": "centre.monument", "variante": 0,
                 "note": "à la place du sanctuaire ; l'avant regarde le sud (l'apparition)"},
    "Vitrine": {"x": 0.0, "z": 34.0, "emprise": (36, 36), "hauteur": 2.5, "yaw": 180,
                "fonction": "centre.vitrine", "variante": 0,
                "note": "podium octogonal Ø 36 ; disque central de Ø 20 LIBRE (statue du jeu)"},
    "Quetes": {"x": 0.0, "z": 151.0, "emprise": (12, 4), "hauteur": 16, "yaw": 180,
               "fonction": "centre.panneau_quetes", "variante": 0,
               "note": "panneau holographique sans texte devant le monument (le PNJ des quêtes y était)"},
    "Apparition": {"x": -3.0, "z": 206.5, "emprise": (14, 14), "hauteur": 1.5, "yaw": 0,
                   "fonction": "centre.apparition", "variante": 0,
                   "note": "plaque dorée sous le repère Spawn"},
}
ZONE_VENTE = {"x": -17.0, "z": 228.0, "rayon": 14.0}   # demi-disque au nord du stand (bord nord du socle en z 228)
VITRINE_RAYON_LIBRE = 10.0                              # centre du podium : rien au-dessus du dessus du podium
SPAWN = {"x": -3.0, "z": 206.5, "yaw": 0}               # le joueur de refEH1 ; regard vers le nord (-Z)

# =====================================================================================================
# 4. Parcelles (8, NON construites : emprises et escaliers laissés vides, marqués par des repères)
# =====================================================================================================
PARCELLE_LARGEUR = 111       # en X : bord intérieur |x| = 80, bord extérieur |x| = 191
PARCELLE_PROFONDEUR = 105    # en Z
PARCELLE_X_INT = 80.0
PARCELLE_X_EXT = 191.0
PARCELLE_X_CENTRE = 135.5
RANGEES_Z = {1: 215.5, 2: 71.75, 3: -72.0, 4: -215.75}   # rangée 1 = sud ; pas 143,75 ; écart 38,75
ESCALIER_X_EXT = 65.0        # escalier / rampe côté tapis : de |x| = 80 à |x| = 65
ESCALIER_LONGUEUR = 55.0     # le long de Z, centré sur la rangée
ETIQUETTE_Y = 38.7           # hauteur des étiquettes « Plot » du jeu (référence) au-dessus de |x| = 76,5
ETIQUETTE_X = 76.5
PLATEAU_BAS = 1.5            # hauteurs des plateaux des bases de référence (information)
PLATEAU_HAUT = 5.0


def _parcelles() -> list[dict]:
    out = []
    for cote, signe in (("W", -1), ("E", 1)):
        for rang, zc in RANGEES_Z.items():
            x_in, x_out = signe * PARCELLE_X_INT, signe * PARCELLE_X_EXT
            out.append({
                "id": f"{cote}{rang}", "cote": cote, "rangee": rang,
                "x": signe * PARCELLE_X_CENTRE, "z": zc,
                "x0": min(x_in, x_out), "x1": max(x_in, x_out),
                "z0": zc - PARCELLE_PROFONDEUR / 2, "z1": zc + PARCELLE_PROFONDEUR / 2,
                "escalier": {"x0": min(signe * ESCALIER_X_EXT, x_in), "x1": max(signe * ESCALIER_X_EXT, x_in),
                             "z0": zc - ESCALIER_LONGUEUR / 2, "z1": zc + ESCALIER_LONGUEUR / 2},
            })
    return out


PARCELLES = _parcelles()
# Écarts entre rangées (passages vers les parcelles) : centres z
ECARTS_RANGEES_Z = [(RANGEES_Z[1] - PARCELLE_PROFONDEUR / 2 + RANGEES_Z[2] + PARCELLE_PROFONDEUR / 2) / 2,
                    (RANGEES_Z[2] - PARCELLE_PROFONDEUR / 2 + RANGEES_Z[3] + PARCELLE_PROFONDEUR / 2) / 2,
                    (RANGEES_Z[3] - PARCELLE_PROFONDEUR / 2 + RANGEES_Z[4] + PARCELLE_PROFONDEUR / 2) / 2]

# Allées de marche à garder libres (rien de solide) : entre le tapis et les parcelles, sur toute la longueur des
# rangées et 7 studs au-delà. Les escaliers des parcelles y sont compris.
COULOIRS_MARCHE = [
    {"id": "Allee_Ouest", "x0": -80.0, "x1": -56.5, "z0": -275.0, "z1": 275.0},
    {"id": "Allee_Est", "x0": 56.5, "x1": 80.0, "z0": -275.0, "z1": 275.0},
]
# Zones où le décor est permis sur la pelouse (hors couloirs, parcelles, escaliers)
DECOR_PELOUSE = {
    "marge_exterieure": "bande |x| 191 → 205 (14 de large) le long des parcelles",
    "ecarts": "écarts de 38,75 entre rangées, |x| 80 → 191, sans barrer le passage (îlots ≤ 8 × 16 au centre)",
    "u_interieur": "dans le U (|x| < 40,33) autour des pièces du centre, sans gêner leurs abords",
    "marges_nord_sud": "pelouse au nord des rangées 4 et au sud des rangées 1, hors tapis et portails",
}
HAUTEUR_LIBRE = 40.0     # rien de large (aire > 64 studs²) suspendu entre 5 et 40 au-dessus d'une zone praticable

# =====================================================================================================
# 5. La couronne de bâtiments (CEINTURE)
# =====================================================================================================
# Coordonnées de côté : s le long de la ligne des façades, d la profondeur vers l'extérieur (d = 0 sur la ligne).
#   est   : s = z de -367 (nord) à +367 (sud) ; (x, z) = (271 + d, s) ; yaw 90  (l'avant regarde -X)
#   ouest : s = z de -367 à +367             ; (x, z) = (-271 - d, s) ; yaw 270 (l'avant regarde +X)
#   nord  : s = x de -271 (ouest) à +271     ; (x, z) = (s, -367 - d) ; yaw 180 (l'avant regarde +Z)
#   sud   : s = x de -271 à +271             ; (x, z) = (s, 367 + d)  ; yaw 0   (l'avant regarde -Z)
# Dans le repère de l'asset, la largeur suit X local (le long de la façade), la profondeur suit Z local (avant en -Z).
COTES = {
    "est": {"s0": -ALIGNEMENT_Z, "s1": ALIGNEMENT_Z, "yaw": 90},
    "ouest": {"s0": -ALIGNEMENT_Z, "s1": ALIGNEMENT_Z, "yaw": 270},
    "nord": {"s0": -ALIGNEMENT_X, "s1": ALIGNEMENT_X, "yaw": 180},
    "sud": {"s0": -ALIGNEMENT_X, "s1": ALIGNEMENT_X, "yaw": 0},
}
COINS_CENTRES = {"ne": (311.0, -407.0, 135), "no": (-311.0, -407.0, 225),
                 "se": (311.0, 407.0, 45), "so": (-311.0, 407.0, 315)}
D_RANG2 = 50.0          # profondeur de l'axe des tours du rang 2
RAYON_RANG2_MAX = 29.0  # Ø ≤ 58 au sol : leur avant reste à d ≥ 21, derrière le rang 1 (d ≤ 17)
PROF_RANG1_MAX = 17.0   # profondeur des éléments du rang 1 posés devant une tour


def cote_vers_monde(cote: str, s: float, d: float) -> tuple[float, float, float]:
    """(s, d) d'un côté de la couronne → (x, z, yaw) dans la carte."""
    if cote == "est":
        return (ALIGNEMENT_X + d, s, 90.0)
    if cote == "ouest":
        return (-ALIGNEMENT_X - d, s, 270.0)
    if cote == "nord":
        return (s, -ALIGNEMENT_Z - d, 180.0)
    if cote == "sud":
        return (s, ALIGNEMENT_Z + d, 0.0)
    raise ValueError(cote)


# --- Rang 1 : front de rue continu, en intervalles jointifs de s (largeur, fonction, variante, params) ---------
# « baie » = élément rond posé entre deux tours du rang 2 (profondeur jusqu'à 34) ; « devant » = élément peu
# profond (≤ 17) posé devant une tour ; None = intervalle réservé à un repère de milieu de côté (il occupe la rue).
RF, RR = "tours_formes", "tours_rondes"
C = RF + ".connecteur"


def _cx(v, h, coul, acc):
    """Connecteur bas (largeur posée par la séquence) : variante, hauteur, couleur dominante, accent."""
    return (C, v, {"hauteur": h, "profondeur": 12, "couleur": coul, "accent": acc})


RANG1 = {
    "est": [   # côté soleil : orange, jaune d'or, rouge, citron ; accents bleu roi, turquoise
        (24, RR + ".tour_fusee", 0, {"hauteur": 52, "diametre": 20, "type": "blanche"}),          # bout nord
        (8,) + _cx(0, 16, "jaune_or", "bleu_roi"),
        (30, RF + ".boutique_arche", 2, {"hauteur": 28, "profondeur": 16}),                      # devant -320
        (8,) + _cx(1, 14, "orange", "turquoise"),
        (34, RR + ".tour_hublots", 0, {"hauteur": 44, "diametre": 30}),                          # baie -280
        (8,) + _cx(2, 16, "jaune_citron", "rouge"),
        (30, RF + ".kiosque", 1, {"type": "arcade", "hauteur": 22, "profondeur": 14}),           # devant -240
        (8,) + _cx(3, 18, "orange", "bleu_roi"),
        (34, RF + ".kiosque", 0, {"type": "dome", "hauteur": 24, "profondeur": 28}),             # baie -200
        (8,) + _cx(0, 16, "rouge", "jaune_citron"),
        (30, RF + ".boutique_arche", 1, {"hauteur": 26, "profondeur": 16}),                      # devant -160
        (8,) + _cx(1, 14, "jaune_or", "turquoise"),
        (34, RR + ".tour_fusee", 2, {"hauteur": 58, "diametre": 22, "type": "capsule"}),        # baie -120
        (8,) + _cx(2, 16, "orange", "bleu_roi"),
        (30, RF + ".kiosque", 0, {"type": "hublots", "hauteur": 16, "profondeur": 14}),         # devant -80
        (8,) + _cx(3, 18, "jaune_or", "rouge"),
        (27, RR + ".tour_fusee", 3, {"hauteur": 48, "diametre": 20, "type": "blanche"}),         # baie -43,5
        (8, C, 1, {"hauteur": 16, "profondeur": 14, "couleur": "jaune_or", "accent": "violet"}),  # aile du repère
        (44, None, 0, {}),                                                                      # repère E (manette)
        (8, C, 1, {"hauteur": 16, "profondeur": 14, "couleur": "jaune_or", "accent": "violet"}),  # aile du repère
        (27, RR + ".tour_fusee", 1, {"hauteur": 46, "diametre": 20, "type": "capsule"}),        # baie 43,5
        (8,) + _cx(0, 16, "orange", "turquoise"),
        (30, RF + ".boutique_arche", 0, {"hauteur": 28, "profondeur": 16}),                      # devant 80
        (8,) + _cx(1, 14, "jaune_citron", "bleu_roi"),
        (34, RR + ".tour_hublots", 1, {"hauteur": 42, "diametre": 30}),                          # baie 120
        (8,) + _cx(2, 16, "rouge", "jaune_citron"),
        (30, RF + ".kiosque", 2, {"type": "arcade", "hauteur": 22, "profondeur": 14}),           # devant 160
        (8,) + _cx(3, 18, "jaune_or", "turquoise"),
        (34, RF + ".kiosque", 2, {"type": "boutons", "hauteur": 18, "profondeur": 28}),          # baie 200
        (8,) + _cx(0, 16, "orange", "bleu_roi"),
        (30, RF + ".boutique_arche", 2, {"hauteur": 26, "profondeur": 16}),                      # devant 240
        (8,) + _cx(1, 14, "jaune_or", "rouge"),
        (34, RR + ".tour_hublots", 2, {"hauteur": 40, "diametre": 30}),                          # baie 280
        (8,) + _cx(2, 16, "orange", "turquoise"),
        (30, RF + ".kiosque", 1, {"type": "hublots", "hauteur": 16, "profondeur": 14}),         # devant 320
        (8,) + _cx(3, 18, "jaune_citron", "bleu_roi"),
        (24, RR + ".tour_fusee", 3, {"hauteur": 50, "diametre": 20, "type": "blanche"}),         # bout sud
    ],
    "ouest": [   # côté lagon : turquoise, bleu roi, blanc labo, vert lime ; accents orange, jaune
        (24, RR + ".tour_fusee", 1, {"hauteur": 48, "diametre": 20, "type": "capsule"}),        # bout nord
        (8,) + _cx(0, 16, "turquoise", "orange"),
        (30, RF + ".kiosque", 3, {"type": "arcade", "hauteur": 22, "profondeur": 14}),           # devant -320
        (8,) + _cx(1, 14, "bleu_roi", "jaune_citron"),
        (34, RR + ".tour_hublots", 3, {"hauteur": 42, "diametre": 30}),                          # baie -280
        (8,) + _cx(2, 16, "blanc_labo", "turquoise"),
        (30, RF + ".boutique_arche", 1, {"hauteur": 28, "profondeur": 16}),                      # devant -240
        (8,) + _cx(3, 18, "turquoise", "orange"),
        (34, RR + ".tour_fusee", 3, {"hauteur": 56, "diametre": 22, "type": "capsule"}),        # baie -200
        (8,) + _cx(0, 16, "bleu_roi", "jaune_or"),
        (30, RF + ".kiosque", 2, {"type": "hublots", "hauteur": 16, "profondeur": 14}),         # devant -160
        (8,) + _cx(1, 14, "vert_lime", "bleu_roi"),
        (34, RF + ".kiosque", 1, {"type": "dome", "hauteur": 24, "profondeur": 28}),             # baie -120
        (8,) + _cx(2, 16, "turquoise", "orange"),
        (30, RF + ".boutique_arche", 3, {"hauteur": 26, "profondeur": 16}),                      # devant -80
        (8,) + _cx(3, 18, "bleu_roi", "jaune_citron"),
        (27, RR + ".tour_fusee", 2, {"hauteur": 50, "diametre": 20, "type": "blanche"}),         # baie -43,5
        (8, C, 1, {"hauteur": 16, "profondeur": 14, "couleur": "bleu_roi", "accent": "orange"}),  # aile du repère
        (44, None, 0, {}),                                                                      # repère O (tête-boule)
        (8, C, 1, {"hauteur": 16, "profondeur": 14, "couleur": "bleu_roi", "accent": "orange"}),  # aile du repère
        (27, RR + ".tour_fusee", 1, {"hauteur": 46, "diametre": 20, "type": "capsule"}),        # baie 43,5
        (8,) + _cx(0, 16, "turquoise", "jaune_or"),
        (30, RF + ".kiosque", 0, {"type": "arcade", "hauteur": 22, "profondeur": 14}),           # devant 80
        (8,) + _cx(1, 14, "blanc_labo", "bleu_roi"),
        (34, RR + ".tour_hublots", 3, {"hauteur": 44, "diametre": 30}),                          # baie 120
        (8,) + _cx(2, 16, "bleu_roi", "orange"),
        (30, RF + ".boutique_arche", 1, {"hauteur": 28, "profondeur": 16}),                      # devant 160
        (8,) + _cx(3, 18, "turquoise", "jaune_citron"),
        (34, RR + ".tour_fusee", 0, {"hauteur": 58, "diametre": 22, "type": "blanche"}),         # baie 200
        (8,) + _cx(0, 16, "vert_lime", "bleu_roi"),
        (30, RF + ".kiosque", 3, {"type": "hublots", "hauteur": 16, "profondeur": 14}),         # devant 240
        (8,) + _cx(1, 14, "turquoise", "orange"),
        (34, RF + ".kiosque", 3, {"type": "dome", "hauteur": 24, "profondeur": 28}),             # baie 280
        (8,) + _cx(2, 16, "bleu_roi", "jaune_or"),
        (30, RF + ".boutique_arche", 2, {"hauteur": 26, "profondeur": 16}),                      # devant 320
        (8,) + _cx(3, 18, "blanc_labo", "turquoise"),
        (24, RR + ".tour_fusee", 0, {"hauteur": 52, "diametre": 20, "type": "blanche"}),         # bout sud
    ],
    "nord": [   # côté du labo (sous l'œuf) : violet, lavande, rose, magenta ; accents turquoise, citron
        (16,) + _cx(0, 16, "lavande", "turquoise"),                                             # bout ouest
        (30, RF + ".kiosque", 3, {"type": "arcade", "hauteur": 22, "profondeur": 14}),           # devant -240
        (8,) + _cx(1, 14, "violet", "jaune_citron"),
        (24, RR + ".tour_fusee", 1, {"hauteur": 46, "diametre": 18, "type": "capsule"}),        # baie -205
        (8,) + _cx(2, 16, "rose_bonbon", "turquoise"),
        (30, RF + ".boutique_arche", 0, {"hauteur": 28, "profondeur": 16}),                      # devant -170
        (8,) + _cx(3, 18, "lavande", "turquoise"),
        (24, RR + ".tour_hublots", 3, {"hauteur": 36, "diametre": 22}),                          # baie -135
        (8,) + _cx(0, 16, "magenta", "jaune_citron"),
        (30, RF + ".kiosque", 0, {"type": "hublots", "hauteur": 16, "profondeur": 14}),         # devant -100
        (8,) + _cx(1, 14, "violet", "turquoise"),
        (30, RF + ".kiosque", 3, {"type": "dome", "hauteur": 22, "profondeur": 28}),             # fenêtre -62
        (8,) + _cx(2, 14, "lavande", "jaune_citron"),
        (78, C, 0, {"hauteur": 20, "profondeur": 14, "couleur": "blanc_labo", "accent": "violet"}),  # galerie de l'axe
        (8,) + _cx(2, 14, "lavande", "jaune_citron"),
        (30, RF + ".kiosque", 1, {"type": "boutons", "hauteur": 18, "profondeur": 28}),          # fenêtre 62
        (8,) + _cx(1, 14, "violet", "turquoise"),
        (30, RF + ".boutique_arche", 3, {"hauteur": 26, "profondeur": 16}),                      # devant 100
        (8,) + _cx(0, 16, "magenta", "jaune_citron"),
        (24, RR + ".tour_fusee", 2, {"hauteur": 50, "diametre": 18, "type": "blanche"}),         # baie 135
        (8,) + _cx(3, 18, "lavande", "turquoise"),
        (30, RF + ".kiosque", 2, {"type": "arcade", "hauteur": 22, "profondeur": 14}),           # devant 170
        (8,) + _cx(2, 16, "rose_bonbon", "turquoise"),
        (24, RR + ".tour_hublots", 1, {"hauteur": 38, "diametre": 22}),                          # baie 205
        (8,) + _cx(1, 14, "violet", "jaune_citron"),
        (30, RF + ".boutique_arche", 0, {"hauteur": 28, "profondeur": 16}),                      # devant 240
        (16,) + _cx(0, 16, "lavande", "turquoise"),                                             # bout est
    ],
    "sud": [   # côté bonbon : rose, magenta, rouge et blanc, crème ; accents turquoise, vert lime
        (16,) + _cx(0, 16, "rose_bonbon", "turquoise"),                                         # bout ouest
        (30, RF + ".boutique_arche", 3, {"hauteur": 26, "profondeur": 16}),                      # devant -240
        (8,) + _cx(1, 14, "creme", "rouge"),
        (34, RR + ".tour_hublots", 1, {"hauteur": 44, "diametre": 30}),                          # baie -200
        (8,) + _cx(2, 16, "magenta", "vert_lime"),
        (30, RF + ".kiosque", 0, {"type": "arcade", "hauteur": 22, "profondeur": 14}),           # devant -160
        (8,) + _cx(3, 18, "rose_bonbon", "turquoise"),
        (34, RR + ".tour_fusee", 2, {"hauteur": 54, "diametre": 22, "type": "capsule"}),        # baie -120
        (8,) + _cx(0, 16, "creme", "magenta"),
        (30, RF + ".boutique_arche", 0, {"hauteur": 28, "profondeur": 16}),                      # devant -80
        (8,) + _cx(1, 14, "rose_bonbon", "vert_lime"),
        (27, RR + ".tour_hublots", 3, {"hauteur": 38, "diametre": 24}),                          # baie -43,5
        (8, C, 1, {"hauteur": 16, "profondeur": 14, "couleur": "rose_bonbon", "accent": "turquoise"}),  # aile
        (44, None, 0, {}),                                                                      # repère S (damier)
        (8, C, 1, {"hauteur": 16, "profondeur": 14, "couleur": "rose_bonbon", "accent": "turquoise"}),  # aile
        (27, RR + ".tour_fusee", 0, {"hauteur": 50, "diametre": 20, "type": "blanche"}),         # baie 43,5
        (8,) + _cx(2, 16, "magenta", "turquoise"),
        (30, RF + ".kiosque", 2, {"type": "hublots", "hauteur": 16, "profondeur": 14}),         # devant 80
        (8,) + _cx(3, 18, "creme", "rouge"),
        (34, RF + ".kiosque", 1, {"type": "dome", "hauteur": 24, "profondeur": 28}),             # baie 120
        (8,) + _cx(0, 16, "rose_bonbon", "vert_lime"),
        (30, RF + ".boutique_arche", 3, {"hauteur": 26, "profondeur": 16}),                      # devant 160
        (8,) + _cx(1, 14, "magenta", "turquoise"),
        (34, RR + ".tour_fusee", 1, {"hauteur": 48, "diametre": 22, "type": "capsule"}),        # baie 200
        (8,) + _cx(2, 16, "creme", "rouge"),
        (30, RF + ".kiosque", 0, {"type": "arcade", "hauteur": 22, "profondeur": 14}),           # devant 240
        (16,) + _cx(3, 16, "rose_bonbon", "turquoise"),                                         # bout est
    ],
}

# --- Rang 2 : tours (s, d, fonction, variante, hauteur, diametre, extra) ; d = 50 sauf repères de milieu de côté
RANG2 = {
    "est": [
        (-320, 50, RR + ".tour_galettes", 0, 200, 54, {}),
        (-240, 50, RF + ".tour_bourrelets", 3, 150, 44, {}),
        (-160, 50, RF + ".cone_etoile", 0, 130, 40, {}),
        (-80, 50, RF + ".tour_bureaux", 3, 180, 34, {}),
        (0, 26, RF + ".tour_manette", 1, 195, 48, {"largeur_manette": 72, "repere": "milieu_est"}),
        (80, 50, RR + ".tour_soucoupe", 1, 160, 56, {}),
        (160, 50, RR + ".tour_tete_boule", 2, 150, 42, {}),
        (240, 50, RF + ".tour_damier", 0, 170, 44, {}),
        (320, 50, RR + ".tour_galettes", 3, 190, 54, {}),
    ],
    "ouest": [
        (-320, 50, RR + ".tour_soucoupe", 0, 170, 56, {}),
        (-240, 50, RR + ".tour_bulbe", 3, 115, 46, {}),
        (-160, 50, RR + ".tour_galettes", 1, 210, 54, {}),
        (-80, 50, RF + ".tour_anneau", 1, 125, 40, {}),
        (0, 27, RR + ".tour_tete_boule", 0, 215, 50, {"repere": "milieu_ouest"}),
        (80, 50, RF + ".tour_bureaux", 0, 185, 34, {}),
        (160, 50, RR + ".tour_champignon", 2, 170, 56, {}),
        (240, 50, RF + ".tour_bourrelets", 1, 150, 42, {}),
        (320, 50, RF + ".cone_etoile", 3, 135, 40, {}),
    ],
    "nord": [
        (-240, 50, RR + ".tour_bulbe", 0, 130, 46, {}),
        (-170, 50, RR + ".tour_champignon", 3, 165, 54, {}),
        (-100, 50, RR + ".tour_galettes", 2, 245, 58, {"repere": "fenetre_ouest"}),
        (0, 50, RF + ".plateau_disques", 0, 75, 56, {"repere": "fenetre_oeuf"}),
        (100, 50, RF + ".tour_bourrelets", 0, 240, 52, {"repere": "fenetre_est"}),
        (170, 50, RF + ".tour_damier", 2, 165, 44, {}),
        (240, 50, RR + ".tour_soucoupe", 3, 150, 48, {}),
    ],
    "sud": [
        (-240, 50, RR + ".tour_tete_boule", 1, 150, 42, {}),
        (-160, 50, RR + ".tour_bulbe", 1, 115, 46, {}),
        (-80, 50, RF + ".tour_bureaux", 2, 175, 34, {}),
        (0, 28, RF + ".tour_damier", 1, 215, 52, {"repere": "milieu_sud"}),
        (80, 50, RR + ".tour_champignon", 1, 170, 56, {}),
        (160, 50, RF + ".tour_anneau", 3, 125, 40, {}),
        (240, 50, RF + ".cone_etoile", 2, 140, 40, {}),
    ],
}

# --- Coins : un grand repère par coin, centré dans le carré d'angle de 80 × 80, avant vers le centre ----------
COINS = [
    {"id": "Coin_NE", "coin": "ne", "fonction": RR + ".tour_ruban", "variante": 0, "hauteur": 250, "diametre": 72},
    {"id": "Coin_NO", "coin": "no", "fonction": RR + ".tour_pneus", "variante": 0, "hauteur": 240, "diametre": 72},
    {"id": "Coin_SE", "coin": "se", "fonction": RR + ".tour_pneus", "variante": 1, "hauteur": 230, "diametre": 70},
    {"id": "Coin_SO", "coin": "so", "fonction": RR + ".tour_soucoupe", "variante": 2, "hauteur": 230, "diametre": 70},
]

# Fenêtre de l'œuf : sur le côté nord, |x| < 70, rien au-dessus de 80 (rang 1 ≤ 30, plateau à disques 75) :
# depuis l'apparition, le dessous du nuage (y ≈ 202, à 1 100 studs) reste visible au-dessus du plateau.
FENETRE_OEUF = {"x0": -70.0, "x1": 70.0, "hauteur_max": 80.0}

# --- Tubes de verre entre tours (≥ 60 de haut) : extrémités dans l'âme des tours (cachées), colliers visibles --
# type « fin » : C04, rayon 2,5, anneaux d'or hexagonaux tous les 24 (sinusoïde si « onde » > 0) ;
# type « geant » : C05, rayon 6, anneaux épais jaune d'or tous les 36, tournés de 15° l'un après l'autre ;
# un tube géant n'entre que dans une âme de rayon ≥ 12 (galettes, bourrelets, anneau), jamais dans un pilier fin.
TUBES = [
    {"id": "Tube_Est_Nord", "de": "E-T-320", "vers": "E-T-240", "y": 100.0, "type": "geant", "onde": 0},
    {"id": "Tube_Ouest_Nord", "de": "O-T-160", "vers": "O-T-80", "y": 75.0, "type": "geant", "onde": 0},
    {"id": "Tube_Ouest_Sud", "de": "O-T80", "vers": "O-T160", "y": 75.0, "type": "fin", "onde": 0},
    {"id": "Tube_Nord_Ouest", "de": "N-T-170", "vers": "N-T-100", "y": 70.0, "type": "fin", "onde": 0},
    {"id": "Tube_Coin_NE", "de": "N-T100", "vers": "E-T-320", "y": 150.0, "type": "fin", "onde": 0},
    {"id": "Tube_Coin_SE", "de": "S-T80", "vers": "E-T320", "y": 80.0, "type": "fin", "onde": 6},
]
TUBE_RAYON = {"fin": 2.5, "geant": 6.0}
TUBE_PAS_ANNEAUX = {"fin": 24.0, "geant": 36.0}

_PREFIXES = {"est": "E", "ouest": "O", "nord": "N", "sud": "S"}


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}".replace(".", "_")


def _ceinture() -> list[dict]:
    """Construit la liste explicite des emplacements de la couronne (rang 1, rang 2, coins)."""
    out = []
    quais = {}
    for t in TUBES:
        for cle in ("de", "vers"):
            quais.setdefault(t[cle], []).append(t["y"])
    for cote, seq in RANG1.items():
        p = _PREFIXES[cote]
        s = COTES[cote]["s0"]
        for k, item in enumerate(seq):
            largeur, fonction, variante, params = item[0], item[1], item[2], dict(item[3])
            s0, s1 = s, s + largeur
            s = s1
            if fonction is None:
                continue
            module, nom = fonction.split(".")
            if nom in ("tour_hublots", "tour_fusee"):
                # tour ronde : Ø donné, avant à d = 1 ; la fonction ne reçoit que hauteur, diametre (et type)
                forme, prof, diam = "rond", params["diametre"] + 2, params["diametre"]
            elif nom == "kiosque" and params.get("type") in ("dome", "boutons"):
                # kiosque rond dans une baie : Ø = profondeur - 2, socle carré arrondi dans largeur × profondeur
                forme, prof = "rond", params["profondeur"]
                diam = prof - 2
                params["largeur"] = largeur
            else:
                # bâtiment rectangulaire qui remplit exactement largeur × profondeur, avant sur la façade (d = 0)
                forme, prof, diam = "rect", params["profondeur"], None
                params["largeur"] = largeur
            sc, dc = (s0 + s1) / 2, prof / 2
            x, z, yaw = cote_vers_monde(cote, sc, dc)
            out.append({
                "id": f"{p}-R1-{k:02d}", "cote": cote, "rang": 1, "s0": s0, "s1": s1, "s": sc, "d": dc,
                "x": round(x, 3), "z": round(z, 3), "yaw": yaw, "largeur": largeur, "profondeur": prof,
                "hauteur": params.get("hauteur"), "diametre_sol": diam, "module": module, "fonction": nom,
                "variante": variante, "forme": forme, "params": params,
            })
        if abs(s - COTES[cote]["s1"]) > 1e-6:
            raise ValueError(f"rang 1 {cote} : la séquence couvre {s - COTES[cote]['s0']} au lieu de "
                             f"{COTES[cote]['s1'] - COTES[cote]['s0']}")
    for cote, seq in RANG2.items():
        p = _PREFIXES[cote]
        for (s, d, fonction, variante, h, diam, extra) in seq:
            module, nom = fonction.split(".")
            x, z, yaw = cote_vers_monde(cote, s, d)
            ident = f"{p}-T{_fmt(s)}"
            params = {"hauteur": h, "diametre": diam}
            extra = dict(extra)
            repere = extra.pop("repere", None)
            params.update(extra)
            if nom == "tour_bureaux":
                params["largeur"] = params.pop("diametre")
            if ident in quais:
                params["quai"] = sorted(quais[ident])
            emprise = diam
            if nom == "tour_manette":
                emprise = max(diam, params.get("largeur_manette", diam))
            # la tour de bureaux est une boîte arrondie : emprise carrée (vérifiée comme rectangle)
            forme = "rect" if nom == "tour_bureaux" else "rond"
            out.append({
                "id": ident, "cote": cote, "rang": 2, "s": s, "d": d, "x": round(x, 3), "z": round(z, 3),
                "yaw": yaw, "largeur": emprise, "profondeur": diam, "hauteur": h, "diametre_sol": diam,
                "module": module, "fonction": nom, "variante": variante, "forme": forme, "params": params,
                "repere": repere,
            })
    for c in COINS:
        x, z, yaw = COINS_CENTRES[c["coin"]]
        params = {"hauteur": c["hauteur"], "diametre": c["diametre"]}
        module, nom = c["fonction"].split(".")
        out.append({
            "id": c["id"], "cote": "coin_" + c["coin"], "rang": 0, "s": 0.0, "d": 40.0, "x": x, "z": z,
            "yaw": float(yaw), "largeur": c["diametre"], "profondeur": c["diametre"], "hauteur": c["hauteur"],
            "diametre_sol": c["diametre"], "module": module, "fonction": nom, "variante": c["variante"],
            "forme": "rond", "params": params, "repere": "coin",
        })
    return out


CEINTURE = _ceinture()
CEINTURE_PAR_ID = {e["id"]: e for e in CEINTURE}

# =====================================================================================================
# 6. Ciel : l'œuf-laboratoire sur son nuage, son câble, les nacelles, les pièces d'or, le dirigeable
# =====================================================================================================
# L'œuf est au bout de l'axe du tapis, au-delà de la couronne nord, dans la « fenêtre » |x| < 70.
# Vu de l'apparition (œil à 8) : nuage de 10° à 17,6° au-dessus de l'horizon, œuf de 17,6° à 29° : il passe
# au-dessus du monument du centre (16° de là) ; les tours qui encadrent la fenêtre (245 et 240 à ±100) montent à
# 21° : l'œuf les dépasse. Vu du centre : nuage 12-21°, œuf 21-34°.
OEUF = {
    "x": 0.0, "z": -900.0, "y": 290.0,      # pied de la coquille (repère local y = 0 de la recette C01)
    "echelle": 1.6,                          # k : coquille 240 × 320, nuage ≈ 610 × 150 × 480
    "yaw": 180,                              # cassure et intérieur visibles depuis la carte (avant vers +Z)
    "fonction": "ciel.oeuf_labo", "variante": 0,
}
# Bas du nuage ≈ y 202, dessus ≈ y 354, coquille visible de 354 à 610, extension z ≈ -1140 → -660, |x| ≤ 305
CABLE = {"de": (-80.0, 216.0, -760.0), "a": (-80.0, 0.0, -560.0), "fonction": "ciel.cable", "variante": 0,
         "note": "du dessous du nuage à une station d'ancrage posée sur son propre socle derrière la couronne nord"}

NACELLES = [
    # file au-dessus de la route est, vers le nord (inclinées de 6°), 55-61 de haut
    {"id": "Nacelle_E1", "x": 235.0, "y": 55.0, "z": 180.0, "yaw": 0, "variante": 0, "rayon": 7},
    {"id": "Nacelle_E2", "x": 235.0, "y": 58.0, "z": 130.0, "yaw": 0, "variante": 1, "rayon": 6.5},
    {"id": "Nacelle_E3", "x": 235.0, "y": 61.0, "z": 80.0, "yaw": 0, "variante": 2, "rayon": 7},
    {"id": "Nacelle_E4", "x": 235.0, "y": 58.0, "z": 30.0, "yaw": 0, "variante": 0, "rayon": 6},
    # file au-dessus de la route ouest, vers le sud, 62-68
    {"id": "Nacelle_O1", "x": -235.0, "y": 64.0, "z": -150.0, "yaw": 180, "variante": 1, "rayon": 7},
    {"id": "Nacelle_O2", "x": -235.0, "y": 66.0, "z": -100.0, "yaw": 180, "variante": 2, "rayon": 6.5},
    {"id": "Nacelle_O3", "x": -235.0, "y": 68.0, "z": -50.0, "yaw": 180, "variante": 0, "rayon": 7},
    {"id": "Nacelle_O4", "x": -235.0, "y": 66.0, "z": 0.0, "yaw": 180, "variante": 1, "rayon": 6},
    {"id": "Nacelle_O5", "x": -235.0, "y": 64.0, "z": 50.0, "yaw": 180, "variante": 2, "rayon": 7},
    # trio devant la fenêtre de l'œuf, au-dessus de la marge nord de la pelouse, 120-128
    {"id": "Nacelle_N1", "x": -60.0, "y": 120.0, "z": -330.0, "yaw": 90, "variante": 0, "rayon": 8},
    {"id": "Nacelle_N2", "x": 0.0, "y": 128.0, "z": -345.0, "yaw": 90, "variante": 1, "rayon": 8},
    {"id": "Nacelle_N3", "x": 60.0, "y": 120.0, "z": -330.0, "yaw": 90, "variante": 2, "rayon": 8},
    # couche haute, éparse, 160-210
    {"id": "Nacelle_H1", "x": -150.0, "y": 170.0, "z": -120.0, "yaw": 30, "variante": 0, "rayon": 9},
    {"id": "Nacelle_H2", "x": 150.0, "y": 180.0, "z": 60.0, "yaw": 200, "variante": 1, "rayon": 9},
    {"id": "Nacelle_H3", "x": -120.0, "y": 190.0, "z": 250.0, "yaw": 120, "variante": 2, "rayon": 9},
    {"id": "Nacelle_H4", "x": 100.0, "y": 200.0, "z": -250.0, "yaw": 300, "variante": 0, "rayon": 9},
    {"id": "Nacelle_H5", "x": 0.0, "y": 210.0, "z": -520.0, "yaw": 90, "variante": 1, "rayon": 10},
    {"id": "Nacelle_H6", "x": 210.0, "y": 165.0, "z": -470.0, "yaw": 250, "variante": 2, "rayon": 9},
]
NACELLE_INCLINAISON = 6.0    # degrés, vers l'avant

PIECE_RAYON = 6.0


def _ligne_pieces(ident, p0, p1, n, y0, amplitude, periodes, plan="vertical_long"):
    """n pièces de p0 à p1 (x, z), hauteur y0 + amplitude·sin ; faces parallèles à la ligne (on voit des disques
    depuis la place). Renvoie des dicts {id, x, y, z, yaw} : yaw = orientation de l'axe X local de la pièce, qui
    porte la ligne ; la normale des faces est l'axe Z local."""
    out = []
    dx, dz = p1[0] - p0[0], p1[1] - p0[1]
    yaw = math.degrees(math.atan2(-dz, dx))     # axe X local (cos yaw, 0, -sin yaw) le long de la ligne
    for i in range(n):
        t = i / (n - 1)
        y = y0 + amplitude * math.sin(2 * math.pi * periodes * t)
        out.append({"id": f"{ident}_{i + 1:02d}", "x": round(p0[0] + t * dx, 2), "y": round(y, 2),
                    "z": round(p0[1] + t * dz, 2), "yaw": round(yaw, 2)})
    return out


PIECES_OR = (
    _ligne_pieces("Pieces_Ouest", (-262.0, -280.0), (-262.0, 80.0), 14, 74.0, 8.0, 1.5)
    + [dict(p, y=round(100 + 25 * math.sin(math.pi * i / 12), 2))
       for i, p in enumerate(_ligne_pieces("Pieces_Nord", (-150.0, -322.0), (150.0, -322.0), 13, 100.0, 0.0, 1))]
    + _ligne_pieces("Pieces_Est", (235.0, 200.0), (235.0, 330.0), 6, 86.0, 4.0, 1)
)
PIECE_FONCTION = "ciel.piece_or"

DIRIGEABLE = {"x": -160.0, "y": 235.0, "z": 560.0, "yaw": 270, "longueur": 90, "fonction": "ciel.dirigeable",
              "variante": 0, "note": "au-delà de la couronne sud, cap à l'est ; visible en se retournant"}
CUMULUS = [
    {"id": "Cumulus_Ouest", "x": -720.0, "y": 230.0, "z": -260.0, "largeur": 220, "variante": 0},
    {"id": "Cumulus_Est", "x": 700.0, "y": 260.0, "z": 180.0, "largeur": 260, "variante": 1},
    {"id": "Cumulus_Sud", "x": 220.0, "y": 210.0, "z": 880.0, "largeur": 200, "variante": 2},
]
CUMULUS_FONCTION = "ciel.cumulus"

# Index du ciel (tout ce que pose assets/ciel.py, plus les tubes posés par carte.py)
CIEL = {"oeuf": OEUF, "cable": CABLE, "nacelles": NACELLES, "pieces_or": PIECES_OR, "dirigeable": DIRIGEABLE,
        "cumulus": CUMULUS}

# =====================================================================================================
# 7. Mobilier (listes de poses : id, fonction de assets/mobilier.py, variante, x, y, z, yaw, params)
# =====================================================================================================


def _yaw_vers(x, z, cx, cz) -> float:
    """yaw qui tourne l'avant (-Z local) de (x, z) vers (cx, cz)."""
    return round(math.degrees(math.atan2(-(cx - x), -(cz - z))) % 360, 2)


def _proche_passage(cote, s, marge=10.0) -> bool:
    return any(p["cote"] == cote and abs(p["s"] - s) < PASSAGE_LARGEUR / 2 + marge for p in PASSAGES_PIETONS)


def _mobilier() -> list[dict]:
    m = []

    def pose(ident, fonction, x, z, yaw, variante=0, y=0.0, **params):
        m.append({"id": ident, "fonction": fonction, "variante": variante, "x": round(x, 2), "y": y,
                  "z": round(z, 2), "yaw": round(yaw % 360, 2), "params": params})

    yt = NIVEAU_TROTTOIR
    # Lampadaires à écran : trottoir intérieur (écran vers la pelouse), tous les 64, côté route
    k = 0
    for cote, signe in (("est", 1), ("ouest", -1)):
        for i in range(10):
            s = -288 + 64 * i
            if _proche_passage(cote, s):
                continue
            k += 1
            pose(f"Lampe_Int_{k:02d}", "mobilier.lampadaire", signe * (TROTTOIR_INT_X - 4), s,
                 90 if signe > 0 else 270, variante=0, y=yt)
    for cote, signe in (("sud", 1), ("nord", -1)):
        for i in range(7):
            s = -192 + 64 * i
            k += 1
            pose(f"Lampe_Int_{k:02d}", "mobilier.lampadaire", s, signe * (TROTTOIR_INT_Z - 4),
                 0 if signe > 0 else 180, variante=0, y=yt)
    # Trottoir extérieur : lampadaires-soucoupes côté route, tous les 64 décalés de 32
    k = 0
    for cote, signe in (("est", 1), ("ouest", -1)):
        for i in range(11):
            s = -320 + 64 * i
            if _proche_passage(cote, s):
                continue
            k += 1
            pose(f"Lampe_Ext_{k:02d}", "mobilier.lampadaire", signe * (ROUTE_X + 2.5), s,
                 270 if signe > 0 else 90, variante=1, y=yt)
    for cote, signe in (("sud", 1), ("nord", -1)):
        for i in range(8):
            s = -224 + 64 * i
            k += 1
            pose(f"Lampe_Ext_{k:02d}", "mobilier.lampadaire", s, signe * (ROUTE_Z + 2.5),
                 180 if signe > 0 else 0, variante=1, y=yt)
    # Marge extérieure de la pelouse (|x| 191 → 205) : jardinières rondes à deux palmiers
    k = 0
    for signe in (1, -1):
        for z in [round(v, 2) for v in ECARTS_RANGEES_Z] + [284.5, -284.5]:
            k += 1
            pose(f"Palmiers_Marge_{k:02d}", "mobilier.groupe_palmiers", signe * 198, z,
                 _yaw_vers(signe * 198, z, 0, 0), variante=k % 4, n=2, diametre=8)
    # Écarts entre rangées : un lampadaire de chaque côté au bout extérieur (|x| = 186), rien au milieu
    k = 0
    for signe in (1, -1):
        for z in ECARTS_RANGEES_Z:
            k += 1
            pose(f"Lampe_Ecart_{k:02d}", "mobilier.lampadaire", signe * 186, z + 15,
                 _yaw_vers(signe * 186, z + 15, signe * 186, z), variante=0)
    # Angles du trottoir intérieur : grandes jardinières rondes à trois palmiers
    for i, (sx, sz) in enumerate(((1, 1), (-1, 1), (1, -1), (-1, -1))):
        x, z = sx * (PELOUSE_X + 6), sz * (PELOUSE_Z + 6)
        pose(f"Palmiers_Angle_{i + 1}", "mobilier.groupe_palmiers", x, z, _yaw_vers(x, z, 0, 0),
             variante=i, y=yt, n=3, diametre=10)
    # Dans le U : quatre palmiers en pot autour du monument, deux coupoles près du podium, bancs
    for i, (x, z) in enumerate(((-27, 113), (27, 113), (-27, 141), (27, 141))):
        pose(f"Palmier_U_{i + 1}", "mobilier.groupe_palmiers", x, z, _yaw_vers(x, z, 0, 127), variante=i,
             n=1, diametre=6)
    for i, x in enumerate((-30, 30)):
        pose(f"Coupole_U_{i + 1}", "mobilier.coupole_miniature", x, 62, 180, variante=i)
    for i, (x, z, yaw) in enumerate(((-30, 180, 90), (30, 180, 270), (-30, 80, 90), (30, 80, 270))):
        pose(f"Banc_U_{i + 1}", "mobilier.banc", x, z, yaw, variante=i % 4)
    # Bancs du trottoir intérieur, face à la pelouse, au droit du centre de chaque rangée
    k = 0
    for signe in (1, -1):
        for z in RANGEES_Z.values():
            k += 1
            pose(f"Banc_Int_{k:02d}", "mobilier.banc", signe * (PELOUSE_X + 3), z,
                 90 if signe > 0 else 270, variante=k % 4, y=yt)
    # Trottoir extérieur : jardinières à haie et palmier devant certains connecteurs (contre la façade)
    k = 0
    for e in CEINTURE:
        if e["fonction"] != "connecteur" or e["largeur"] != 8:
            continue
        idx = int(e["id"].split("-")[-1])
        if idx % 4 != 1:
            continue
        x, z, yaw = cote_vers_monde(e["cote"], e["s"], -4.0)   # contre la façade : d de -7 à -1
        k += 1
        pose(f"Jardiniere_Ext_{k:02d}", "mobilier.jardiniere", x, z, yaw, variante=k % 4, y=yt,
             largeur=12, profondeur=6, palmier=True)
    # Bancs et poubelles du trottoir extérieur, devant les boutiques (assise tournée vers la rue)
    k = 0
    for e in CEINTURE:
        if e["fonction"] != "boutique_arche":
            continue
        k += 1
        x, z, yaw = cote_vers_monde(e["cote"], e["s"] - 9, -4.0)
        pose(f"Banc_Ext_{k:02d}", "mobilier.banc", x, z, yaw, variante=k % 4, y=yt)
        if k % 2:
            x, z, yaw = cote_vers_monde(e["cote"], e["s"] + 11, -2.0)
            pose(f"Poubelle_Ext_{k:02d}", "mobilier.poubelle", x, z, yaw, variante=k % 3, y=yt)
    # Feux tricolores et potelets aux passages piétons (un feu de chaque côté, deux potelets de chaque côté)
    k = 0
    for p in PASSAGES_PIETONS:
        signe = 1 if p["cote"] == "est" else -1
        for (xa, ds) in ((TROTTOIR_INT_X - 2.5, -(PASSAGE_LARGEUR / 2 + 3.5)), (ROUTE_X + 2.5, PASSAGE_LARGEUR / 2 + 3.5)):
            k += 1
            x, z = signe * xa, p["s"] + ds
            # le feu regarde la route : yaw 270 = avant vers +X, yaw 90 = avant vers -X
            pose(f"Feu_{k:02d}", "mobilier.feu_tricolore", x, z, 270 if (signe > 0) == (xa < ROUTE_X) else 90,
                 variante=k % 4, y=yt)
            for j, dz in enumerate((-1, 1)):
                pose(f"Potelet_{k:02d}_{j + 1}", "mobilier.potelet", x, p["s"] + dz * (PASSAGE_LARGEUR / 2 + 0.6),
                     0, variante=0, y=yt)
    # Parvis des coins de la couronne : palmiers devant chaque repère d'angle, coupole et panneau au trottoir
    for i, (cle, (cx, cz, yaw)) in enumerate(COINS_CENTRES.items()):
        sx, sz = (1 if cx > 0 else -1), (1 if cz > 0 else -1)
        x, z = sx * (ALIGNEMENT_X + 10), sz * (ALIGNEMENT_Z + 10)
        pose(f"Palmiers_Coin_{cle.upper()}", "mobilier.groupe_palmiers", x, z, yaw, variante=i, y=NIVEAU_COURONNE,
             n=2, diametre=8)
        x, z = sx * (TROTTOIR_EXT_X - 9), sz * (TROTTOIR_EXT_Z - 9)
        pose(f"Coupole_Coin_{cle.upper()}", "mobilier.coupole_miniature", x, z, yaw, variante=(i + 2) % 4, y=yt)
    # Panneaux-pictogrammes : angles de la pelouse (sur le trottoir intérieur) et abords du centre
    for i, (x, z, picto) in enumerate(((211, 270, "etoile"), (-211, 270, "piece"), (211, -270, "eclair"),
                                       (-211, -270, "planete"))):
        pose(f"Panneau_{i + 1}", "mobilier.panneau", x, z, 90 if x > 0 else 270, variante=i % 4, y=yt,
             picto=picto)
    for i, (x, z, yaw, picto) in enumerate(((-30, 264, 0, "piece"), (33, 222, 0, "eclair"),
                                            (-33, -268, 180, "cornet"), (33, -268, 180, "etoile"))):
        pose(f"Panneau_Centre_{i + 1}", "mobilier.panneau", x, z, yaw, variante=(i + 1) % 4, picto=picto)
    # Champignons lumineux en bordure intérieure du U (petits, sans collision)
    k = 0
    for z in (-250, -190, -130, -70, 200):
        for signe in (1, -1):
            k += 1
            pose(f"Champignon_{k:02d}", "mobilier.champignon_lumineux", signe * 37, z, 0, variante=k % 2)
    # Rambardes blanches à boules : aux quatre angles du trottoir intérieur, le long de la bordure (garde-corps
    # de carrefour, parallèles à la rue : elles ne barrent pas le trottoir), deux tronçons de 16 par angle
    k = 0
    for sx, sz in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        k += 1
        pose(f"Rambarde_{k}a", "mobilier.rambarde", sx * (TROTTOIR_INT_X - 1.8), sz * (PELOUSE_Z - 9), 90,
             variante=0, y=yt, longueur=16)
        pose(f"Rambarde_{k}b", "mobilier.rambarde", sx * (PELOUSE_X - 9), sz * (TROTTOIR_INT_Z - 1.8), 0,
             variante=0, y=yt, longueur=16)
    return m


MOBILIER = _mobilier()

# =====================================================================================================
# 8. Repères invisibles du jeu (dossier Reperes)
# =====================================================================================================


def _reperes() -> list[dict]:
    r = [{"nom": "Spawn", "centre": (SPAWN["x"], 0.0, SPAWN["z"]), "taille": (8, 1, 8), "yaw": SPAWN["yaw"]}]
    for p in PARCELLES:
        r.append({"nom": f"Parcelle_{p['id']}", "centre": (p["x"], 0.0, p["z"]),
                  "taille": (PARCELLE_LARGEUR, 1, PARCELLE_PROFONDEUR), "yaw": 0})
    for p in PARCELLES:
        e = p["escalier"]
        r.append({"nom": f"Entree_{p['id']}", "centre": ((e["x0"] + e["x1"]) / 2, 0.0, p["z"]),
                  "taille": (e["x1"] - e["x0"], 1, ESCALIER_LONGUEUR), "yaw": 90 if p["cote"] == "W" else 270})
    r.append({"nom": "Tapis_Debut", "centre": (TAPIS_AXE[0][0], TAPIS_DESSUS, TAPIS_AXE[0][1]),
              "taille": (TAPIS_BANDE, 1, 4), "yaw": 180})
    r.append({"nom": "Tapis_Fin", "centre": (TAPIS_AXE[-1][0], TAPIS_DESSUS, TAPIS_AXE[-1][1]),
              "taille": (TAPIS_BANDE, 1, 4), "yaw": 0})
    for i, (x, z) in enumerate(TAPIS_AXE):
        r.append({"nom": f"Tapis_{i + 1:02d}", "centre": (x, TAPIS_DESSUS, z), "taille": (2, 1, 2), "yaw": 0})
    for nom in ("Vente", "Machine", "Monument", "Vitrine", "Quetes"):
        c = CENTRE[nom]
        r.append({"nom": nom, "centre": (c["x"], 0.0, c["z"]), "taille": (c["emprise"][0], 1, c["emprise"][1]),
                  "yaw": c["yaw"]})
    r.append({"nom": "ZoneVente", "centre": (ZONE_VENTE["x"], 0.0, ZONE_VENTE["z"] - ZONE_VENTE["rayon"] / 2),
              "taille": (2 * ZONE_VENTE["rayon"], 1, ZONE_VENTE["rayon"]), "yaw": 0})
    return r


REPERES = _reperes()

# =====================================================================================================
# 9. Vues de rendu (caméra, cible, champ vertical en degrés) ; résolutions conseillées dans SPECS.md
# =====================================================================================================
VUES = {
    # les deux captures de l'utilisateur, à reproduire exactement (2000 × 1077 et 2000 × 1050, ou moitié)
    "capture1": ((2.03, 66.1, 319.0), (-2.06, 18.23, 231.29), 70.6),
    "capture2": ((156.2, 52.7, 361.3), (112.97, 16.7, 278.62), 69.3),
    # le joueur à l'apparition, caméra Roblox par défaut (12,5 derrière, regard vers le nord)
    "joueur": ((-3.0, 8.0, 219.0), (-3.0, 5.5, 206.5), 70.0),
    # l'œuf au-dessus de la fenêtre nord, vu de la pelouse
    "ciel": ((-3.0, 8.0, 219.0), (0.0, 300.0, -900.0), 62.0),
    "oeuf": ((0.0, 30.0, -250.0), (0.0, 440.0, -900.0), 46.0),
    # rues et couronne
    "rue": ((262.0, 7.0, 150.0), (264.0, 30.0, -60.0), 66.0),
    "coin": ((140.0, 18.0, -190.0), (311.0, 120.0, -407.0), 66.0),
    "nord": ((0.0, 66.1, -319.0), (0.0, 18.23, -231.3), 70.6),
    "centre": ((32.0, 34.0, 292.0), (-4.0, 6.0, 170.0), 60.0),
    "aerienne_sud": ((420.0, 520.0, 980.0), (0.0, 40.0, -60.0), 48.0),
}
RESOLUTIONS = {"capture1": (2000, 1077), "capture2": (2000, 1050)}

# =====================================================================================================
# 10. Budgets (pièces, Neon, verre/transparentes) — plafonds par module ; la carte entière ≤ 24 000 / 1 500 / 400
# =====================================================================================================
BUDGET_CARTE = {"pieces": 24000, "neon": 1500, "transparentes": 400, "cible": 21000}
BUDGETS = {
    # module: (pièces, Neon, transparentes) — totaux de tout ce que le module pose sur la carte
    "carte": (2600, 40, 60),           # sol, routes, trottoirs, bordures, marquages, mur de fond, repères, tubes
    "tours_rondes": (4400, 400, 40),
    "tours_formes": (5200, 450, 30),
    "ciel": (1300, 220, 60),
    "tapis+centre": (1400, 160, 12),
    "mobilier": (4600, 220, 30),       # poses de carte.py (MOBILIER)
}
# Plafond par appel (pièces, Neon, transparentes). « L » = largeur du connecteur.
BUDGET_FONCTION = {
    "tours_rondes.tour_galettes": (140, 40, 0),
    "tours_rondes.tour_champignon": (110, 0, 0),
    "tours_rondes.tour_soucoupe": (100, 14, 1),
    "tours_rondes.tour_tete_boule": (100, 0, 0),
    "tours_rondes.tour_pneus": (220, 40, 0),
    "tours_rondes.tour_ruban": (200, 12, 0),
    "tours_rondes.tour_bulbe": (60, 0, 6),
    "tours_rondes.tour_fusee": (50, 1, 0),
    "tours_rondes.tour_hublots": (60, 6, 0),
    "tours_formes.tour_manette": (160, 8, 0),
    "tours_formes.cone_etoile": (70, 0, 0),
    "tours_formes.tour_damier": (140, 8, 0),
    "tours_formes.tour_bourrelets": (120, 40, 0),
    "tours_formes.tour_bureaux": (100, 6, 0),
    "tours_formes.plateau_disques": (90, 12, 2),
    "tours_formes.tour_anneau": (55, 8, 0),
    "tours_formes.boutique_arche": (65, 4, 0),
    "tours_formes.kiosque": (50, 6, 0),
    "tours_formes.connecteur": ("14 + 0.7 L", 1, 0),
    "ciel.oeuf_labo": (320, 90, 4),
    "ciel.cable": (22, 8, 0),
    "ciel.nacelle": (12, 1, 1),
    "ciel.piece_or": (2, 0, 0),
    "ciel.dirigeable": (60, 6, 0),
    "ciel.cumulus": (30, 0, 0),
    "tapis.tapis": (480, 40, 0),
    "tapis.portail": (90, 12, 1),
    "centre.stand_vente": (90, 6, 0),
    "centre.machine": (50, 6, 1),
    "centre.monument": (120, 20, 0),
    "centre.vitrine": (60, 10, 0),
    "centre.panneau_quetes": (25, 4, 2),
    "centre.apparition": (40, 16, 0),
    "mobilier.lampadaire": (10, 1, 0),
    "mobilier.groupe_palmiers": ("16 + 28 n", 0, 0),
    "mobilier.palmier": (28, 0, 0),
    "mobilier.jardiniere": (70, 0, 0),
    "mobilier.banc": (10, 0, 0),
    "mobilier.poubelle": (6, 0, 0),
    "mobilier.feu_tricolore": (14, 3, 0),
    "mobilier.potelet": (5, 0, 0),
    "mobilier.coupole_miniature": (14, 0, 1),
    "mobilier.panneau": (14, 3, 0),
    "mobilier.champignon_lumineux": (11, 5, 0),
    "mobilier.rambarde": ("1 + 5 par travée de 8", 0, 0),
}


def budget_appel(fonction: str, params: dict | None = None) -> tuple[float, float, float]:
    """Plafond (pièces, Neon, transparentes) d'un appel, formules résolues avec ses paramètres."""
    p = params or {}
    pieces, neon, transp = BUDGET_FONCTION[fonction]
    if fonction.endswith("connecteur"):
        pieces = 14 + 0.7 * p.get("largeur", 8)
    elif fonction.endswith("groupe_palmiers"):
        pieces = 16 + 28 * p.get("n", 2)
    elif fonction.endswith("rambarde"):
        pieces = 1 + 5 * math.ceil(p.get("longueur", 16) / 8)
    return (pieces, neon, transp)

# =====================================================================================================
# 11. Outils de géométrie (sans bpy)
# =====================================================================================================


def longueur_polyligne(pts) -> float:
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def point_sur_polyligne(pts, s: float):
    """Point à l'abscisse curviligne s (x, z) et direction unitaire (dx, dz) de la polyligne pts [(x, z), …]."""
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        L = math.dist(a, b)
        if s <= L or i == len(pts) - 2:
            t = max(0.0, min(1.0, s / L if L else 0.0))
            return ((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])),
                    ((b[0] - a[0]) / L, (b[1] - a[1]) / L))
        s -= L
    raise ValueError("polyligne vide")


def echantillonner(pts, pas: float, debut: float = 0.0, fin_marge: float = 0.0):
    """Points réguliers le long de pts : liste de ((x, z), (dx, dz), s)."""
    out, L, s = [], longueur_polyligne(pts), debut
    while s <= L - fin_marge + 1e-9:
        p, d = point_sur_polyligne(pts, s)
        out.append((p, d, s))
        s += pas
    return out


def yaw_direction(dx: float, dz: float) -> float:
    """yaw qui fait regarder l'avant (-Z local) d'un asset dans la direction (dx, dz)."""
    return math.degrees(math.atan2(-dx, -dz)) % 360


def dans_rect(x, z, x0, x1, z0, z1, marge=0.0) -> bool:
    return x0 - marge <= x <= x1 + marge and z0 - marge <= z <= z1 + marge


def dans_parcelle(x, z, marge=0.0):
    """Id de la parcelle (emprise) qui contient (x, z), sinon None."""
    for p in PARCELLES:
        if dans_rect(x, z, p["x0"], p["x1"], p["z0"], p["z1"], marge):
            return p["id"]
    return None


def dans_escalier(x, z, marge=0.0):
    for p in PARCELLES:
        e = p["escalier"]
        if dans_rect(x, z, e["x0"], e["x1"], e["z0"], e["z1"], marge):
            return p["id"]
    return None


def dans_couloir(x, z, marge=0.0):
    for c in COULOIRS_MARCHE:
        if dans_rect(x, z, c["x0"], c["x1"], c["z0"], c["z1"], marge):
            return c["id"]
    return None


def zone_praticable(x, z) -> str | None:
    """Nature du sol praticable sous (x, z) : pelouse, trottoir, route, ou None (couronne, hors carte)."""
    ax, az = abs(x), abs(z)
    if ax <= PELOUSE_X and az <= PELOUSE_Z:
        return "pelouse"
    if ax <= TROTTOIR_INT_X and az <= TROTTOIR_INT_Z:
        return "trottoir_int"
    if ax <= ROUTE_X and az <= ROUTE_Z:
        return "route"
    if ax <= TROTTOIR_EXT_X and az <= TROTTOIR_EXT_Z:
        return "trottoir_ext"
    return None


def emprise_slot(e: dict):
    """Emprise au sol d'un emplacement de CEINTURE : ("cercle", cx, cz, r) ou ("rect", [(x, z) × 4])."""
    if e["forme"] == "rond":
        r = (e.get("diametre_sol") or e["params"].get("diametre") or min(e["largeur"], e["profondeur"])) / 2
        return ("cercle", e["x"], e["z"], r)
    yaw = math.radians(e["yaw"])
    ux, uz = math.cos(yaw), -math.sin(yaw)        # axe X local (largeur)
    vx, vz = math.sin(yaw), math.cos(yaw)         # axe Z local (+Z local = vers l'arrière)
    hw, hd = e["largeur"] / 2, e["profondeur"] / 2
    pts = []
    for a, b in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)):
        pts.append((e["x"] + a * ux + b * vx, e["z"] + a * uz + b * vz))
    return ("rect", pts)


def _normale_int(d):
    """Normale vers l'intérieur du U (à gauche du sens du flux, vu du dessus nord en haut) : (dz, -dx)."""
    return (d[1], -d[0])


def tapis_bandes() -> list[dict]:
    """Quadrilatères exacts (onglets aux joints) des trois bandes de chaque tronçon du tapis.

    Décalages le long de la normale intérieure : bordure intérieure [+4,95, +8,05], bande [-4,95, +4,95],
    bordure extérieure [-8,05, -4,95]. Chaque quadrilatère : [début côté a, fin côté a, fin côté b, début côté b]
    en (x, z) ; aux têtes nord les bouts sont droits. Les sommets reproduisent TAPIS_VIRAGE_INT et
    TAPIS_VIRAGE_EXT (onglets mesurés) au 1/20 de stud près. Construction : un bloc pour la partie rectangulaire,
    un coin posé à plat (triangle rectangle) à chaque bout biseauté, dessus à TAPIS_DESSUS (bande) ou
    TAPIS_DESSUS_BORDURE (bordures)."""
    tr = TAPIS_TRONCONS
    dirs = []
    for t in tr:
        (x0, z0), (x1, z1) = t["de"], t["a"]
        L = math.dist((x0, z0), (x1, z1))
        dirs.append(((x1 - x0) / L, (z1 - z0) / L))
    h, hb = TAPIS_LARGEUR / 2, TAPIS_BANDE / 2
    bandes = {"bordure_int": (hb, h), "bande": (-hb, hb), "bordure_ext": (-h, -hb)}
    out = []
    for i, t in enumerate(tr):
        n = _normale_int(dirs[i])

        def coin(V, voisin, off):
            if voisin is None:
                return (V[0] + off * n[0], V[1] + off * n[1])
            m = _normale_int(dirs[voisin])
            k = off / (1 + n[0] * m[0] + n[1] * m[1])
            return (V[0] + k * (n[0] + m[0]), V[1] + k * (n[1] + m[1]))
        prec = i - 1 if i > 0 else None
        suiv = i + 1 if i < len(tr) - 1 else None
        item = {"id": t["id"], "direction": dirs[i], "normale_int": n}
        for nom, (a, b) in bandes.items():
            item[nom] = [coin(t["de"], prec, a), coin(t["a"], suiv, a), coin(t["a"], suiv, b), coin(t["de"], prec, b)]
        out.append(item)
    return out


def chevrons() -> list[dict]:
    """Poses des chevrons blancs : centre (x, z) de la pointe du « V », yaw (avant = sens du flux), le long de
    l'axe tous les CHEVRON_PAS, hors des portails (z > TAPIS_Z_TETE - 1 sur les voies droites)."""
    out = []
    for (p, d, s) in echantillonner(TAPIS_AXE, CHEVRON_PAS, debut=CHEVRON_PAS / 2):
        if p[1] < TAPIS_Z_TETE + CHEVRON_PROFONDEUR:
            continue
        out.append({"x": round(p[0], 3), "z": round(p[1], 3), "yaw": round(yaw_direction(*d), 3), "s": round(s, 3)})
    return out


def resume() -> dict:
    from collections import Counter
    par_fonction = Counter(f"{e['module']}.{e['fonction']}" for e in CEINTURE)
    return {
        "pelouse": (2 * PELOUSE_X, 2 * PELOUSE_Z),
        "facades": (2 * ALIGNEMENT_X, 2 * ALIGNEMENT_Z),
        "emprise_totale": (2 * COURONNE_X, 2 * COURONNE_Z),
        "tapis_longueur_axe": round(longueur_polyligne(TAPIS_AXE), 2),
        "ceinture": len(CEINTURE),
        "ceinture_par_fonction": dict(sorted(par_fonction.items())),
        "tubes": len(TUBES), "nacelles": len(NACELLES), "pieces_or": len(PIECES_OR),
        "mobilier": len(MOBILIER), "reperes": len(REPERES),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(resume(), ensure_ascii=False, indent=1))
