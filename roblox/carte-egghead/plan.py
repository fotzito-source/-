#!/usr/bin/env python3
"""Plan de la carte « île du futur » (CarteEgghead) : toutes les cotes, en un seul endroit.

Ce module ne dépend que de la bibliothèque standard (pas de bpy, pas de numpy) : carte.py, les assets et les
scripts de contrôle l'importent. Une correction du plan se fait ici et nulle part ailleurs.

Repère (celui de Roblox et du kit) : origine = centre de la carte au niveau du sol (dessus de la pelouse, y = 0) ;
+X = droite de la capture refEH1 (est), +Z = vers la caméra de refEH1 (sud), le nord est -Z ; 1 unité = 1 stud ;
yaw en degrés autour de Y. L'avant d'un asset regarde -Z local ; posé avec `b.at(pos, yaw)`, son avant regarde
(-sin yaw, 0, -cos yaw) et son axe X local devient (cos yaw, 0, -sin yaw).

Source des formes et des tailles : le plan final du juge (/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/eh/plan/LAYOUT.md
et layout.json, 13/11), qui fusionne les reconstructions des analystes A, B et C (deux caméras calibrées ; moitié
sud ±0,5 à 3 studs, rangées nord et têtes du tapis ±3 à 8, bord nord de la pelouse et esplanade ±8 à 25), arrondies
au stud entier pour les dalles (studs alignés). Origine = centre de jeu : milieu du tapis et du bloc des 8
parcelles (repère de A) ; la pelouse et la couronne ne sont PAS centrées dessus : elles vont 35 studs plus loin au
nord qu'au sud, comme dans la référence. Le thème change l'aspect, jamais la géométrie.

    python plan.py          # imprime un résumé (bandes, tapis, couronne, comptes)
"""

from __future__ import annotations

import math

# =====================================================================================================
# 1. Bandes du sol (rectangles concentriques ; demi-largeur en X, et en Z une valeur au sud, une au nord)
# =====================================================================================================
# Le juge mesure 12,5 / 36 / 17,5 (bords à 217,5 et 253,5) : les dalles gardent des bords entiers (studs
# alignés), 217 et 253, à 0,5 près ; le nord prolonge le même anneau 35 plus loin (pelouse jusqu'à -336).

PELOUSE_X = 205            # pelouse : |x| ≤ 205
PELOUSE_Z_SUD = 301        # pelouse : z ≤ 301 au sud
PELOUSE_Z_NORD = 336       # pelouse : z ≥ -336 au nord (mesuré -329 / -332 / -340 : 35 de plus qu'au sud)
DECALAGE_NORD = PELOUSE_Z_NORD - PELOUSE_Z_SUD   # 35 : tout l'anneau nord recule d'autant
TROTTOIR_INT_X = 217       # trottoir intérieur : 205 → 217 (12, juge 12,5) à l'est et à l'ouest
TROTTOIR_INT_Z_SUD = 313   # 301 → 313 au sud
TROTTOIR_INT_Z_NORD = 348  # -336 → -348 au nord
ROUTE_X = 253              # route : 217 → 253 (36)
ROUTE_Z_SUD = 349          # 313 → 349
ROUTE_Z_NORD = 384         # -348 → -384
TROTTOIR_EXT_X = 271       # trottoir extérieur : 253 → 271 (18, juge 17,5)
TROTTOIR_EXT_Z_SUD = 367   # 349 → 367
TROTTOIR_EXT_Z_NORD = 402  # -384 → -402
ALIGNEMENT_X = TROTTOIR_EXT_X        # ligne des façades de la couronne (est / ouest)
ALIGNEMENT_Z_SUD = TROTTOIR_EXT_Z_SUD    # 367
ALIGNEMENT_Z_NORD = TROTTOIR_EXT_Z_NORD  # 402
COURONNE_PROFONDEUR = 80        # profondeur de la couronne de bâtiments derrière la ligne des façades
COURONNE_X = ALIGNEMENT_X + COURONNE_PROFONDEUR             # 351 : bord extérieur de la couronne
COURONNE_Z_SUD = ALIGNEMENT_Z_SUD + COURONNE_PROFONDEUR     # 447
COURONNE_Z_NORD = ALIGNEMENT_Z_NORD + COURONNE_PROFONDEUR   # 482
MUR_FOND_EPAISSEUR = 2          # mur de fond continu au bord extérieur de la couronne (filet de sécurité)
MUR_FOND_HAUTEUR = 36           # ferme toute vue à hauteur d'œil, même par une ruelle

# Esplanade nord (renfoncement de la couronne, juge § 7) : pour |x| < 140, la couronne nord s'ouvre sur une
# esplanade de z -402 à -490 (sol sombre à rangées de tirets blancs : aire des navettes) ; ses deux flancs (x = ±140)
# et son fond (z = -490) portent un front de rue tourné vers elle ; derrière le fond, la couronne du fond (80 de
# profondeur, jusqu'à z -572) porte les deux tours qui cadrent l'œuf et le plateau du laboratoire.
ESPLANADE_X = 140               # |x| < 140 (±15)
ESPLANADE_Z = 490               # fond de l'esplanade : z = -490 (±25) = ligne des façades du fond
FLANC_PROFONDEUR = 17           # bâtiments des flancs : de x = ±140 à ±157
FOND_X = ESPLANADE_X + FLANC_PROFONDEUR + 3    # 160 : demi-largeur de la couronne du fond (mur compris)
FOND_Z = ESPLANADE_Z + COURONNE_PROFONDEUR + 2   # 572 : bord extérieur de la couronne du fond (tours Ø 58 à d 50)

# Les dalles de la couronne commencent 1 stud derrière la ligne des façades (le trottoir, ou l'esplanade, passe sous
# le pied des bâtiments) : la face avant d'un socle posé sur la ligne ne se confond jamais avec un bord de dalle.
JOINT_COURONNE = 1

TROTTOIR_LARGEUR_INT = TROTTOIR_INT_X - PELOUSE_X      # 12
ROUTE_LARGEUR = ROUTE_X - TROTTOIR_INT_X                # 36
TROTTOIR_LARGEUR_EXT = TROTTOIR_EXT_X - ROUTE_X         # 18

# Zones praticables (pelouse, trottoirs, route et esplanade) : rectangles (x0, x1, z0, z1)
ZONES_PRATICABLES = [
    (-ALIGNEMENT_X, ALIGNEMENT_X, -ALIGNEMENT_Z_NORD, ALIGNEMENT_Z_SUD),
    (-ESPLANADE_X, ESPLANADE_X, -ESPLANADE_Z, -ALIGNEMENT_Z_NORD),
]

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
ROUTE_AXE_X = (TROTTOIR_INT_X + ROUTE_X) / 2     # 235 : axe des routes est / ouest (tirets sur [235, 236])
ROUTE_AXE_Z_SUD = (TROTTOIR_INT_Z_SUD + ROUTE_Z_SUD) / 2      # 331 : route sud (tirets sur [331, 332])
ROUTE_AXE_Z_NORD = (TROTTOIR_INT_Z_NORD + ROUTE_Z_NORD) / 2   # 366 : route nord (tirets sur [-367, -366])
VOIE_LARGEUR = ROUTE_LARGEUR / 2                  # 18
TIRET_LARGEUR = 1                                 # tirets sur [235, 236] (coins entiers)
TIRET_LONGUEUR = 6
TIRET_PAS = 16                                    # 6 de trait, 10 de vide
TIRET_ARRET_COIN = 4                              # les tirets s'arrêtent à 4 studs des carrés d'angle
LIGNE_RIVE_LARGEUR = 1
LIGNE_RIVE_RETRAIT = 2                            # ligne de rive à 2 du bord : [219, 220] et [250, 251] (de même en Z)
FLECHE_PAS = 96                                   # une flèche par voie tous les 96, décalée de 48 d'une voie à l'autre
FLECHE_LONGUEUR = 9                               # hampe 1,4 × 6 + tête en chevron de 3
BORDURE_LARGEUR = 1                               # bordure rayée rouge et blanc côté route des deux trottoirs
BORDURE_DESSUS = NIVEAU_TROTTOIR + 0.2            # 0,6 : la bordure dépasse le trottoir de 0,2
BORDURE_RAYURE = 4                                # 4 rouges, 4 blancs (bloc rouge en saillie de 0,1)

# Sens de circulation (flèches) : voie intérieure dans le sens antihoraire vu du dessus (sud : vers +X, est :
# vers -Z, nord : vers -X, ouest : vers +Z), voie extérieure en sens inverse (mesuré sur la route sud).
SENS_VOIE_INTERIEURE = "antihoraire"

# Passages piétons (zébras de 2 × 10, 9 bandes) : sur la route est en z ≈ 137 (mesuré, juge), en miroir sur la
# route ouest, et deux autres au nord (z -137) pour l'équilibre des rues
PASSAGE_LARGEUR = 10
PASSAGE_BANDE = 2
PASSAGE_ECART = 2
PASSAGES_PIETONS = [
    {"id": "Passage_E_Sud", "cote": "est", "s": 137.0},
    {"id": "Passage_E_Nord", "cote": "est", "s": -137.0},
    {"id": "Passage_O_Sud", "cote": "ouest", "s": 137.0},
    {"id": "Passage_O_Nord", "cote": "ouest", "s": -137.0},
]

# =====================================================================================================
# 2. Tapis roulant (U ouvert, refermé au sud ; sens antihoraire vu du dessus)
# =====================================================================================================

TAPIS_LARGEUR = 16.0        # bande = bordure 3 + tapis 10 + bordure 3 (juge ; A : 3,1 + 9,9 + 3,1)
TAPIS_BANDE = 10.0
TAPIS_BORDURE = 3.0
TAPIS_AXE_X = 48.5           # axes des deux voies droites : x = ±48,5
TAPIS_BORD_INT_X = 40.5      # bords intérieurs ±40,5 (îlot de pelouse de 81 entre les voies)
TAPIS_BORD_EXT_X = 56.5      # bords extérieurs ±56,5
TAPIS_DESSUS = 0.6           # dessus de la bande sombre
TAPIS_DESSUS_BORDURE = 1.0   # dessus des bordures (la bande est en creux de 0,4 entre elles)
TAPIS_Z_TETE = -294.0        # têtes nord des deux voies : embout carré, filet blanc en travers, RIEN de haut dessus
TAPIS_Z_FOND = TAPIS_Z_TETE  # bout physique de la bande (= la tête : pas de portail)
TAPIS_Z_APPARITION = -290.0  # milieu de la zone de tête (16 × 8) où les objets apparaissent (ouest) / disparaissent (est)
TAPIS_Z_VIRAGE = 258.5       # début du demi-octogone au sud

# Axe du tapis dans le sens du flux : tête ouest → vers le sud → demi-tour d'ouest en est → tête est
TAPIS_AXE = [
    (-48.5, TAPIS_Z_TETE),
    (-48.5, 258.5),
    (-40.5, 276.3),
    (-28.75, 286.3),
    (28.75, 286.3),
    (40.5, 276.3),
    (48.5, 258.5),
    (48.5, TAPIS_Z_TETE),
]
# Polygones du demi-tour (juge) : bord intérieur et bord extérieur de la bande ; plan.tapis_bandes() les retrouve à
# 0,1 près par décalage de l'axe (onglets aux joints)
TAPIS_VIRAGE_INT = [(-40.5, 256.7), (-33.9, 271.3), (-25.8, 278.3),
                    (25.8, 278.3), (33.9, 271.3), (40.5, 256.7)]
TAPIS_VIRAGE_EXT = [(-56.5, 260.2), (-47.1, 281.2), (-31.7, 294.3),
                    (31.7, 294.3), (47.1, 281.2), (56.5, 260.2)]
# Tronçons droits de la bande (axe), dans le sens du flux ; la voie ouest descend vers +Z, la voie est remonte
TAPIS_TRONCONS = [
    {"id": "Voie_Ouest", "de": TAPIS_AXE[0], "a": TAPIS_AXE[1]},
    {"id": "Virage_O1", "de": TAPIS_AXE[1], "a": TAPIS_AXE[2]},
    {"id": "Virage_O2", "de": TAPIS_AXE[2], "a": TAPIS_AXE[3]},
    {"id": "Virage_Sud", "de": TAPIS_AXE[3], "a": TAPIS_AXE[4]},
    {"id": "Virage_E2", "de": TAPIS_AXE[4], "a": TAPIS_AXE[5]},
    {"id": "Virage_E1", "de": TAPIS_AXE[5], "a": TAPIS_AXE[6]},
    {"id": "Voie_Est", "de": TAPIS_AXE[6], "a": TAPIS_AXE[7]},
]
CHEVRON_PAS = 8.0            # un chevron blanc tous les 8,0 le long de l'axe (juge : 17 chevrons par voie, 8,0 à 8,2)
CHEVRON_LARGEUR = 9.0        # envergure du « V » à travers la bande (≤ 10)
CHEVRON_PROFONDEUR = 3.5     # flèche du « V » dans le sens du flux
CHEVRON_TRAIT = 1.2          # largeur d'un bras

# Portails des têtes de voies : SUPPRIMÉS (juge : rien de haut sur les têtes ; les deux « portails » que A voyait
# sont les deux kiosques à dôme du U, voir CENTRE). Les cotes restent pour tapis.portail (non posé).
PORTAIL_LARGEUR = 30
PORTAIL_PROFONDEUR = 16
PORTAIL_HAUTEUR = 36
PORTAIL_OUVERTURE = 18.5
PORTAILS: list[dict] = []

# =====================================================================================================
# 3. Pièces du centre (dans le U) et apparition
# =====================================================================================================
# Chaque pièce : centre (x, z), emprise (x, z), hauteur, yaw (avant = côté où l'on joue), fonction de SPECS.md,
# paramètres facultatifs (« params ») passés à la fonction. Cotes du juge (LAYOUT.md § 5).
CENTRE = {
    "Vente": {"x": -16.5, "z": 244.5, "emprise": (28, 24), "hauteur": 18, "yaw": 0,
              "fonction": "centre.stand_vente", "variante": 0,
              "note": "stand 28 × 24 (x -30,5 → -2,5 ; z 232,5 → 256,5) ; l'avant regarde le nord ; zone de vente en "
                      "demi-disque pointillé devant le bord nord (ZONE_VENTE)"},
    "Machine": {"x": 25.0, "z": 240.0, "emprise": (12, 10), "hauteur": 17, "yaw": 0,
                "fonction": "centre.machine", "variante": 0},
    "Monument": {"x": 0.0, "z": 126.0, "emprise": (34, 36), "hauteur": 32, "yaw": 180,
                 "fonction": "centre.monument", "variante": 0,
                 "note": "à la place du sanctuaire des quêtes (x -17 → 17, z 108 → 144) ; l'avant regarde le sud"},
    "Vitrine": {"x": 0.0, "z": 35.5, "emprise": (38, 38), "hauteur": 2.5, "yaw": 180,
                "fonction": "centre.vitrine", "variante": 0, "params": {"diametre": 38},
                "note": "podium octogonal Ø 38 (juge) ; disque central de Ø 20 LIBRE (statue du jeu) ; z 35,5 (mesuré "
                        "35 ± 5) : ses faces nord et sud (16,5 et 54,5) ne tombent pas sur une ligne de la grille"},
    "Quetes": {"x": 0.0, "z": 151.0, "emprise": (12, 4), "hauteur": 16, "yaw": 180,
               "fonction": "centre.panneau_quetes", "variante": 0,
               "note": "panneau holographique sans texte devant le monument (le PNJ des quêtes est au sanctuaire)"},
    "Apparition": {"x": 0.0, "z": 205.0, "emprise": (14, 14), "hauteur": 1.5, "yaw": 0,
                   "fonction": "centre.apparition", "variante": 0,
                   "note": "point d'apparition neutre (juge : sur l'axe ; le joueur de refEH1 est en (-3 ; 207))"},
    # deux kiosques à dôme contre le bord intérieur des voies, au nord du U (les « portails » de A), tournés vers l'axe ;
    # centres au demi-stud (juge : (±29 ; -170) ±12) : les faces de leurs socles ne tombent pas sur la grille
    "Kiosque_Ouest": {"x": -29.5, "z": -170.5, "emprise": (20, 20), "hauteur": 27, "yaw": 270,
                      "fonction": "tours_formes.kiosque", "variante": 0,
                      "params": {"type": "dome", "largeur": 20, "profondeur": 20, "hauteur": 26},
                      "note": "kiosque à dôme (±12) ; avant vers +X"},
    "Kiosque_Est": {"x": 29.5, "z": -170.5, "emprise": (20, 20), "hauteur": 27, "yaw": 90,
                    "fonction": "tours_formes.kiosque", "variante": 3,
                    "params": {"type": "dome", "largeur": 20, "profondeur": 20, "hauteur": 26},
                    "note": "même modèle, autre schéma (dôme violet) ; avant vers -X"},
    # portail violet lumineux (cadre de 10 × 3, 14 de haut, rôle inconnu : téléporteur ?) : portique à fond bleu nuit
    # et liseré Neon violet, face au sud
    "Portail": {"x": 0.0, "z": -105.0, "emprise": (10, 4), "hauteur": 14, "yaw": 180,
                "fonction": "tours_formes.connecteur", "variante": 3,
                "params": {"largeur": 10, "profondeur": 4, "hauteur": 14, "couleur": "violet",
                           "accent": "neon_violet"},
                "note": "portail violet (±20)"},
}
# Zone de vente : demi-disque de rayon 14 en pointillés, centré au milieu du bord nord du stand (le juge mesure un
# demi-disque r 20 centré sur le stand, ouvert vers le nord : z 225 → 245 ; centre.stand_vente le trace devant
# le bord nord, à rayon_zone près)
ZONE_VENTE = {"x": -16.5, "z": 232.5, "rayon": 14.0}
VITRINE_RAYON_LIBRE = 10.0                              # centre du podium : rien au-dessus du dessus du podium
SPAWN = {"x": 0.0, "z": 205.0, "yaw": 0}                # point d'apparition neutre ; regard vers le nord (-Z)

# =====================================================================================================
# 4. Parcelles (8, NON construites : emprises et bandes d'entrée laissées vides, marquées par des repères)
# =====================================================================================================
PARCELLE_LARGEUR = 110       # plateforme réservée en X : bord intérieur |x| = 81, bord extérieur |x| = 191
PARCELLE_PROFONDEUR = 102    # en Z
PARCELLE_X_INT = 81.0
PARCELLE_X_EXT = 191.0
PARCELLE_X_CENTRE = 136.0
RANGEES_Z = {1: 216.0, 2: 72.0, 3: -72.0, 4: -216.0}   # rangée 1 = sud ; pas 144 ; écart de 42 entre rangées
ESCALIER_X_EXT = 65.0        # bande d'entrée réservée côté tapis (rampe, borne, pastille) : de |x| = 81 à |x| = 65
ESCALIER_LONGUEUR = PARCELLE_PROFONDEUR   # sur toute la profondeur de la parcelle (juge)
ETIQUETTE_Y = 38.7           # hauteur des étiquettes « Plot » du jeu (référence) au-dessus de |x| = 76
ETIQUETTE_X = 76.0
PLATEAU_BAS = 1.75           # hauteurs des plateaux des bases de référence (information)
PLATEAU_HAUT = 5.0
APPARITION_PARCELLE_X = 62.0  # point d'apparition de chaque joueur, sur la pelouse devant son entrée (±62 ; rangée)


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

# Allées de marche à garder libres (rien de solide) : entre le tapis et les plateformes des parcelles, sur toute la
# longueur des rangées et 7 studs au-delà. Les bandes d'entrée des parcelles (|x| 65 → 81) y sont comprises.
COULOIRS_MARCHE = [
    {"id": "Allee_Ouest", "x0": -PARCELLE_X_INT, "x1": -TAPIS_BORD_EXT_X, "z0": -274.0, "z1": 274.0},
    {"id": "Allee_Est", "x0": TAPIS_BORD_EXT_X, "x1": PARCELLE_X_INT, "z0": -274.0, "z1": 274.0},
]
# Zones où le décor est permis sur la pelouse (hors couloirs, parcelles, bandes d'entrée)
DECOR_PELOUSE = {
    "marge_exterieure": "bande |x| 191 → 205 (14 de large) le long des parcelles",
    "ecarts": "écarts de 42 entre rangées, |x| 81 → 191, sans barrer le passage (un palmier en bac vers |x| 170)",
    "u_interieur": "dans le U (|x| < 40,5) autour des pièces du centre, sans gêner leurs abords",
    "marges_nord_sud": "pelouse au nord des rangées 4 (jusqu'à -336) et au sud des rangées 1, hors tapis",
}
# Points d'apparition des joueurs, un par parcelle (juge : sur la pelouse devant l'entrée), regard vers leur parcelle
APPARITIONS_PARCELLES = [
    {"id": p["id"], "x": (1 if p["cote"] == "E" else -1) * APPARITION_PARCELLE_X, "z": p["z"],
     "yaw": 270 if p["cote"] == "E" else 90} for p in PARCELLES]
HAUTEUR_LIBRE = 40.0     # rien de large (aire > 64 studs²) suspendu entre 5 et 40 au-dessus d'une zone praticable

# =====================================================================================================
# 5. La couronne de bâtiments (CEINTURE)
# =====================================================================================================
# Coordonnées de côté : s le long de la ligne des façades, d la profondeur vers l'extérieur (d = 0 sur la ligne).
#   est        : s = z de -402 (nord) à +367 (sud) ; (x, z) = (271 + d, s)  ; yaw 90  (l'avant regarde -X)
#   ouest      : s = z de -402 à +367              ; (x, z) = (-271 - d, s) ; yaw 270 (l'avant regarde +X)
#   nord       : s = x de -271 (ouest) à +271      ; (x, z) = (s, -402 - d) ; yaw 180 (l'avant regarde +Z) ;
#                l'intervalle |x| < 157 est réservé au renfoncement (esplanade et ses flancs)
#   sud        : s = x de -271 à +271              ; (x, z) = (s, 367 + d)  ; yaw 0   (l'avant regarde -Z)
#   fond       : fond de l'esplanade, s = x de -140 à +140 ; (x, z) = (s, -490 - d) ; yaw 180
#   flanc_ouest: flanc ouest de l'esplanade, s = z de -490 à -402 ; (x, z) = (-140 - d, s) ; yaw 270
#   flanc_est  : flanc est de l'esplanade,   s = z de -490 à -402 ; (x, z) = (140 + d, s)  ; yaw 90
# Dans le repère de l'asset, la largeur suit X local (le long de la façade), la profondeur suit Z local (avant en -Z).
COTES = {
    "est": {"s0": -ALIGNEMENT_Z_NORD, "s1": ALIGNEMENT_Z_SUD, "yaw": 90},
    "ouest": {"s0": -ALIGNEMENT_Z_NORD, "s1": ALIGNEMENT_Z_SUD, "yaw": 270},
    "nord": {"s0": -ALIGNEMENT_X, "s1": ALIGNEMENT_X, "yaw": 180},
    "sud": {"s0": -ALIGNEMENT_X, "s1": ALIGNEMENT_X, "yaw": 0},
    "fond": {"s0": -ESPLANADE_X, "s1": ESPLANADE_X, "yaw": 180},
    "flanc_ouest": {"s0": -ESPLANADE_Z, "s1": -ALIGNEMENT_Z_NORD, "yaw": 270},
    "flanc_est": {"s0": -ESPLANADE_Z, "s1": -ALIGNEMENT_Z_NORD, "yaw": 90},
}
_CX = ALIGNEMENT_X + COURONNE_PROFONDEUR / 2                 # 311 : centre des carrés d'angle de 80 × 80
COINS_CENTRES = {"ne": (_CX, -(ALIGNEMENT_Z_NORD + 40.0), 135), "no": (-_CX, -(ALIGNEMENT_Z_NORD + 40.0), 225),
                 "se": (_CX, ALIGNEMENT_Z_SUD + 40.0, 45), "so": (-_CX, ALIGNEMENT_Z_SUD + 40.0, 315)}
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
        return (s, -ALIGNEMENT_Z_NORD - d, 180.0)
    if cote == "sud":
        return (s, ALIGNEMENT_Z_SUD + d, 0.0)
    if cote == "fond":
        return (s, -ESPLANADE_Z - d, 180.0)
    if cote == "flanc_ouest":
        return (-ESPLANADE_X - d, s, 270.0)
    if cote == "flanc_est":
        return (ESPLANADE_X + d, s, 90.0)
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
        (8,) + _cx(1, 16, "orange", "bleu_roi"),                                                # bout nord
        (27, RF + ".kiosque", 3, {"type": "hublots", "hauteur": 16, "profondeur": 14}),         # devant -376
        (24, RR + ".tour_fusee", 0, {"hauteur": 52, "diametre": 20, "type": "blanche"}),          # baie -355
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
        (8,) + _cx(1, 16, "turquoise", "jaune_or"),                                             # bout nord
        (27, RF + ".kiosque", 1, {"type": "arcade", "hauteur": 22, "profondeur": 14}),          # devant -376
        (24, RR + ".tour_fusee", 1, {"hauteur": 48, "diametre": 20, "type": "capsule"}),        # baie -355
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
        (20, RR + ".tour_hublots", 3, {"hauteur": 36, "diametre": 18}),                          # baie -215
        (8,) + _cx(1, 14, "violet", "jaune_citron"),
        (30, RF + ".boutique_arche", 0, {"hauteur": 28, "profondeur": 16}),                      # devant -182
        (10,) + _cx(2, 16, "rose_bonbon", "turquoise"),                                         # angle du renfoncement
        (314, None, 0, {}),                                                                     # renfoncement (esplanade)
        (10,) + _cx(2, 16, "rose_bonbon", "turquoise"),                                         # angle du renfoncement
        (30, RF + ".boutique_arche", 3, {"hauteur": 26, "profondeur": 16}),                      # devant 182
        (8,) + _cx(1, 14, "violet", "turquoise"),
        (20, RR + ".tour_fusee", 2, {"hauteur": 50, "diametre": 18, "type": "blanche"}),         # baie 215
        (30, RF + ".kiosque", 2, {"type": "arcade", "hauteur": 22, "profondeur": 14}),           # devant 240
        (16,) + _cx(0, 16, "lavande", "turquoise"),                                             # bout est
    ],
    # fond de l'esplanade (z = -490, avant vers le sud) : le front bas du laboratoire, galerie de l'axe au centre ;
    # rien au-dessus de 80 dans |x| < 70 (fenêtre de l'œuf)
    "fond": [
        (25,) + _cx(1, 14, "violet", "jaune_citron"),
        (30, RF + ".kiosque", 0, {"type": "hublots", "hauteur": 16, "profondeur": 14}),         # devant -100
        (8,) + _cx(3, 18, "lavande", "turquoise"),
        (30, RF + ".kiosque", 3, {"type": "dome", "hauteur": 22, "profondeur": 28}),             # fenêtre -62
        (8,) + _cx(2, 14, "lavande", "jaune_citron"),
        (78, C, 0, {"hauteur": 20, "profondeur": 14, "couleur": "blanc_labo", "accent": "violet"}),  # galerie de l'axe
        (8,) + _cx(2, 14, "lavande", "jaune_citron"),
        (30, RF + ".kiosque", 1, {"type": "boutons", "hauteur": 18, "profondeur": 28}),          # fenêtre 62
        (8,) + _cx(3, 18, "lavande", "turquoise"),
        (30, RF + ".boutique_arche", 3, {"hauteur": 26, "profondeur": 16}),                      # devant 100
        (25,) + _cx(1, 14, "magenta", "jaune_citron"),
    ],
    # flancs de l'esplanade (88 de long, de z -490 à -402 ; profondeur ≤ 17 : x de ±140 à ±157)
    "flanc_ouest": [
        (8,) + _cx(0, 16, "magenta", "jaune_citron"),
        (30, RF + ".boutique_arche", 1, {"hauteur": 26, "profondeur": 16}),
        (8,) + _cx(2, 16, "lavande", "turquoise"),
        (26, RF + ".kiosque", 0, {"type": "arcade", "hauteur": 22, "profondeur": 14}),
        (16,) + _cx(1, 16, "violet", "turquoise"),                                              # angle sur la rue
    ],
    "flanc_est": [
        (8,) + _cx(0, 16, "magenta", "turquoise"),
        (30, RF + ".kiosque", 2, {"type": "hublots", "hauteur": 16, "profondeur": 14}),
        (8,) + _cx(2, 16, "lavande", "jaune_citron"),
        (26, RF + ".boutique_arche", 2, {"hauteur": 28, "profondeur": 16}),
        (16,) + _cx(1, 16, "violet", "jaune_citron"),                                           # angle sur la rue
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
        (-376, 50, RR + ".tour_bulbe", 2, 120, 46, {}),             # ajoutée : le côté s'allonge de 35 au nord
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
        (-376, 50, RF + ".tour_anneau", 2, 120, 40, {}),            # ajoutée : le côté s'allonge de 35 au nord
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
        (-184, 50, RR + ".tour_champignon", 3, 165, 54, {}),        # son chapeau (R 27) reste hors du flanc ouest
        # damier ramené à 130 : le tube du coin NE (y 150) passe au-dessus de sa tête
        (182, 50, RF + ".tour_damier", 2, 130, 44, {}),
        (240, 50, RR + ".tour_soucoupe", 3, 150, 48, {}),
    ],
    # derrière le fond de l'esplanade : les deux tours qui cadrent l'œuf et le plateau du laboratoire au centre
    "fond": [
        # à ±102 : leurs galettes et coiffes (plus larges que le fût au-dessus de 40) restent hors de |x| < 70
        (-102, 50, RR + ".tour_galettes", 2, 245, 58, {"repere": "fenetre_ouest"}),
        (0, 50, RF + ".plateau_disques", 0, 75, 56, {"repere": "fenetre_oeuf"}),
        (102, 50, RF + ".tour_bourrelets", 0, 240, 52, {"repere": "fenetre_est"}),
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

# Fenêtre de l'œuf : au fond de l'esplanade nord, |x| < 70, aucun bâtiment au-dessus de 80 (front du fond ≤ 24,
# plateau du laboratoire 75) : depuis l'apparition, le dessous du nuage (y ≈ 202, à 1 100 studs) reste visible
# au-dessus du plateau ; les tours de 245 et 240 (x = ±100, z -540) cadrent l'œuf.
FENETRE_OEUF = {"x0": -70.0, "x1": 70.0, "z0": -FOND_Z, "z1": -ALIGNEMENT_Z_NORD, "hauteur_max": 80.0}

# --- Tubes de verre entre tours (≥ 60 de haut) : extrémités dans l'âme des tours (cachées), colliers visibles --
# type « fin » : C04, rayon 2,5, anneaux d'or hexagonaux tous les 24 (sinusoïde si « onde » > 0) ;
# type « geant » : C05, rayon 6, anneaux épais jaune d'or tous les 36, tournés de 15° l'un après l'autre ;
# un tube géant n'entre que dans une âme de rayon ≥ 12 (galettes, bourrelets, anneau), jamais dans un pilier fin.
TUBES = [
    {"id": "Tube_Est_Nord", "de": "E-T-320", "vers": "E-T-240", "y": 100.0, "type": "geant", "onde": 0},
    {"id": "Tube_Ouest_Nord", "de": "O-T-160", "vers": "O-T-80", "y": 75.0, "type": "geant", "onde": 0},
    {"id": "Tube_Ouest_Sud", "de": "O-T80", "vers": "O-T160", "y": 75.0, "type": "fin", "onde": 0},
    {"id": "Tube_Nord_Ouest", "de": "N-T-184", "vers": "F-T-102", "y": 70.0, "type": "fin", "onde": 0},
    {"id": "Tube_Coin_NE", "de": "F-T102", "vers": "E-T-320", "y": 150.0, "type": "fin", "onde": 0},
    {"id": "Tube_Coin_SE", "de": "S-T80", "vers": "E-T320", "y": 80.0, "type": "fin", "onde": 6},
]
TUBE_RAYON = {"fin": 2.5, "geant": 6.0}
TUBE_PAS_ANNEAUX = {"fin": 24.0, "geant": 36.0}

_PREFIXES = {"est": "E", "ouest": "O", "nord": "N", "sud": "S", "fond": "F", "flanc_ouest": "FO", "flanc_est": "FE"}


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
CABLE = {"de": (-80.0, 216.0, -760.0), "a": (-80.0, 0.0, -600.0), "fonction": "ciel.cable", "variante": 0,
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
        for s in range(-320, 300, 64):
            if _proche_passage(cote, s):
                continue
            k += 1
            pose(f"Lampe_Int_{k:02d}", "mobilier.lampadaire", signe * (TROTTOIR_INT_X - 4), s,
                 90 if signe > 0 else 270, variante=0, y=yt)
    for zt, yaw in ((TROTTOIR_INT_Z_SUD - 4, 0), (-(TROTTOIR_INT_Z_NORD - 4), 180)):
        for i in range(7):
            k += 1
            pose(f"Lampe_Int_{k:02d}", "mobilier.lampadaire", -192 + 64 * i, zt, yaw, variante=0, y=yt)
    # Trottoir extérieur : lampadaires-soucoupes côté route, tous les 64
    k = 0
    for cote, signe in (("est", 1), ("ouest", -1)):
        for s in range(-384, 360, 64):
            if _proche_passage(cote, s):
                continue
            k += 1
            pose(f"Lampe_Ext_{k:02d}", "mobilier.lampadaire", signe * (ROUTE_X + 2.5), s,
                 270 if signe > 0 else 90, variante=1, y=yt)
    for zt, yaw in ((ROUTE_Z_SUD + 2.5, 180), (-(ROUTE_Z_NORD + 2.5), 0)):
        for i in range(8):
            k += 1
            pose(f"Lampe_Ext_{k:02d}", "mobilier.lampadaire", -224 + 64 * i, zt, yaw, variante=1, y=yt)
    # Palmiers de la pelouse aux places des arbres de la référence (juge) : coins de pelouse et marge arrière, en
    # jardinières rondes à deux palmiers ; un palmier en bac dans chaque écart entre rangées (|x| ≈ 170). Les arbres
    # de la marge arrière (juge : (±198 ; ±88)) passent au droit des écarts : leurs palmes (rayon ≈ 13) ne doivent
    # pas couvrir les parcelles (|x| ≤ 191).
    k = 0
    for signe in (1, -1):
        for z in tuple(ECARTS_RANGEES_Z) + (PELOUSE_Z_SUD - 5.0, -(PELOUSE_Z_NORD - 6.0)):
            k += 1
            pose(f"Palmiers_Marge_{k:02d}", "mobilier.groupe_palmiers", signe * 199, z,
                 _yaw_vers(signe * 199, z, 0, 0), variante=k % 4, n=2, diametre=8)
    k = 0
    for signe in (1, -1):
        for z, x in zip(ECARTS_RANGEES_Z, (168.0, 172.0, 168.0)):
            k += 1
            pose(f"Palmier_Ecart_{k:02d}", "mobilier.groupe_palmiers", signe * x, z,
                 _yaw_vers(signe * x, z, 0, z), variante=k % 4, n=1, diametre=6)
    # Écarts entre rangées : un lampadaire de chaque côté au bout extérieur (|x| = 186), rien au milieu
    k = 0
    for signe in (1, -1):
        for z in ECARTS_RANGEES_Z:
            k += 1
            pose(f"Lampe_Ecart_{k:02d}", "mobilier.lampadaire", signe * 186, z + 15,
                 _yaw_vers(signe * 186, z + 15, signe * 186, z), variante=0)
    # Angles du trottoir intérieur : grandes jardinières rondes à trois palmiers
    for i, (sx, sz) in enumerate(((1, 1), (-1, 1), (1, -1), (-1, -1))):
        x, z = sx * (PELOUSE_X + 6), (PELOUSE_Z_SUD + 6 if sz > 0 else -(PELOUSE_Z_NORD + 6))
        pose(f"Palmiers_Angle_{i + 1}", "mobilier.groupe_palmiers", x, z, _yaw_vers(x, z, 0, 0),
             variante=i, y=yt, n=3, diametre=10)
    # Dans le U : quatre palmiers en pot autour du monument, deux coupoles près du podium, bancs
    zm = CENTRE["Monument"]["z"]
    for i, (x, dz) in enumerate(((-27, -14), (27, -14), (-27, 14), (27, 14))):
        pose(f"Palmier_U_{i + 1}", "mobilier.groupe_palmiers", x, zm + dz, _yaw_vers(x, zm + dz, 0, zm),
             variante=i, n=1, diametre=6)
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
    # Trottoir extérieur et esplanade : jardinières à haie et palmier devant certains connecteurs (contre la façade)
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
        az = ALIGNEMENT_Z_SUD if sz > 0 else ALIGNEMENT_Z_NORD
        x, z = sx * (ALIGNEMENT_X + 10), sz * (az + 10)
        pose(f"Palmiers_Coin_{cle.upper()}", "mobilier.groupe_palmiers", x, z, yaw, variante=i, y=NIVEAU_COURONNE,
             n=2, diametre=8)
        x, z = sx * (TROTTOIR_EXT_X - 9), sz * (az - 9)
        pose(f"Coupole_Coin_{cle.upper()}", "mobilier.coupole_miniature", x, z, yaw, variante=(i + 2) % 4, y=yt)
    # Esplanade nord : deux palmiers au pied du laboratoire (comme les deux arbres au pied de l'écran de la référence)
    for i, sx in enumerate((-1, 1)):
        x, z = sx * 46.0, -(ESPLANADE_Z - 9.0)
        pose(f"Palmiers_Esplanade_{i + 1}", "mobilier.groupe_palmiers", x, z, 180, variante=i + 1,
             y=NIVEAU_COURONNE, n=2, diametre=8)
    # Panneaux-pictogrammes : angles de la pelouse (sur le trottoir intérieur) et abords du centre
    for i, (x, z, picto) in enumerate(((211, 270, "etoile"), (-211, 270, "piece"), (211, -300, "eclair"),
                                       (-211, -300, "planete"))):
        pose(f"Panneau_{i + 1}", "mobilier.panneau", x, z, 90 if x > 0 else 270, variante=i % 4, y=yt,
             picto=picto)
    for i, (x, z, yaw, picto) in enumerate(((-30, 266, 0, "piece"), (33, 222, 0, "eclair"),
                                            (-33, -282, 180, "cornet"), (33, -282, 180, "etoile"))):
        pose(f"Panneau_Centre_{i + 1}", "mobilier.panneau", x, z, yaw, variante=(i + 1) % 4, picto=picto)
    # Champignons lumineux en bordure intérieure du U (petits, sans collision)
    k = 0
    for z in (-250, -205, -130, -70, 200):
        for signe in (1, -1):
            k += 1
            pose(f"Champignon_{k:02d}", "mobilier.champignon_lumineux", signe * 37, z, 0, variante=k % 2)
    # Rambardes blanches à boules : aux quatre angles du trottoir intérieur, le long de la bordure (garde-corps
    # de carrefour, parallèles à la rue : elles ne barrent pas le trottoir), deux tronçons de 16 par angle
    k = 0
    for sx, sz in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        k += 1
        pz = PELOUSE_Z_SUD if sz > 0 else PELOUSE_Z_NORD
        tz = TROTTOIR_INT_Z_SUD if sz > 0 else TROTTOIR_INT_Z_NORD
        pose(f"Rambarde_{k}a", "mobilier.rambarde", sx * (TROTTOIR_INT_X - 1.8), sz * (pz - 9), 90,
             variante=0, y=yt, longueur=16)
        pose(f"Rambarde_{k}b", "mobilier.rambarde", sx * (PELOUSE_X - 9), sz * (tz - 1.8), 0,
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
    # zones de tête (16 × 8 du juge, réduites à la bande) : apparition à l'ouest (regard vers le sud, sens du flux),
    # disparition à l'est (les objets y arrivent en remontant vers le nord)
    ht = 2 * abs(TAPIS_Z_APPARITION - TAPIS_Z_TETE)
    r.append({"nom": "Tapis_Debut", "centre": (TAPIS_AXE[0][0], TAPIS_DESSUS, TAPIS_Z_APPARITION),
              "taille": (TAPIS_BANDE, 1, ht), "yaw": 180})
    r.append({"nom": "Tapis_Fin", "centre": (TAPIS_AXE[-1][0], TAPIS_DESSUS, TAPIS_Z_APPARITION),
              "taille": (TAPIS_BANDE, 1, ht), "yaw": 0})
    for i, (x, z) in enumerate(TAPIS_AXE):
        r.append({"nom": f"Tapis_{i + 1:02d}", "centre": (x, TAPIS_DESSUS, z), "taille": (2, 1, 2), "yaw": 0})
    for nom in ("Vente", "Machine", "Monument", "Vitrine", "Quetes"):
        c = CENTRE[nom]
        r.append({"nom": nom, "centre": (c["x"], 0.0, c["z"]), "taille": (c["emprise"][0], 1, c["emprise"][1]),
                  "yaw": c["yaw"]})
    r.append({"nom": "ZoneVente", "centre": (ZONE_VENTE["x"], 0.0, ZONE_VENTE["z"] - ZONE_VENTE["rayon"] / 2),
              "taille": (2 * ZONE_VENTE["rayon"], 1, ZONE_VENTE["rayon"]), "yaw": 0})
    # un point d'apparition par parcelle (juge), regard vers la parcelle
    for a in APPARITIONS_PARCELLES:
        r.append({"nom": f"Apparition_{a['id']}", "centre": (a["x"], 0.0, a["z"]), "taille": (6, 1, 6),
                  "yaw": a["yaw"]})
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
    "joueur": ((0.0, 8.0, 217.5), (0.0, 5.5, 205.0), 70.0),
    # l'œuf au-dessus de la fenêtre nord, vu de la pelouse
    "ciel": ((0.0, 8.0, 217.5), (0.0, 300.0, -900.0), 62.0),
    "oeuf": ((0.0, 30.0, -250.0), (0.0, 440.0, -900.0), 46.0),
    # rues et couronne
    "rue": ((262.0, 7.0, 150.0), (264.0, 30.0, -60.0), 66.0),
    "coin": ((140.0, 18.0, -225.0), (311.0, 120.0, -442.0), 66.0),
    # pendant de capture1 vers le sud, symétrique par rapport au milieu de la pelouse (z -17,5)
    "nord": ((0.0, 66.1, -354.0), (0.0, 18.23, -266.3), 70.6),
    # l'esplanade nord, son laboratoire et l'œuf au-dessus, depuis la marge nord de la pelouse
    "esplanade": ((-40.0, 9.0, -318.0), (0.0, 60.0, -560.0), 68.0),
    "centre": ((32.0, 34.0, 292.0), (-4.0, 6.0, 170.0), 60.0),
    "aerienne_sud": ((420.0, 520.0, 980.0), (0.0, 40.0, -60.0), 48.0),
    # vue d'ensemble depuis le côté du soleil (-X / +Z) : toute la carte et l'œuf au fond (la vue « aerienne »
    # calculée par rendu.py se cadre sur l'emprise de toutes les pièces, ciel compris : la carte y serait petite)
    "aerienne": ((-700.0, 700.0, 1100.0), (0.0, 60.0, -250.0), 50.0),
    # dessus quasi orthographique de la carte seule, esplanade et couronne du fond comprises (z -572 → 447 ; le haut
    # de l'image = nord) ; rendre en 800 × 1000
    "plan_carte": ((0.0, 4500.0, -62.5), (0.0, 0.0, -62.55), 13.4),
}
RESOLUTIONS = {"capture1": (2000, 1077), "capture2": (2000, 1050)}

# =====================================================================================================
# 10. Budgets (pièces, Neon, verre/transparentes) — plafonds par module ; la carte entière ≤ 24 000 / 1 500 / 400
# =====================================================================================================
BUDGET_CARTE = {"pieces": 24000, "neon": 1500, "transparentes": 400, "cible": 21000}
BUDGETS = {
    # module: (pièces, Neon, transparentes) — totaux de tout ce que le module pose sur la carte
    "carte": (2400, 40, 60),           # sol, routes, trottoirs, bordures, marquages, mur de fond, repères, tubes
    "tours_rondes": (4400, 400, 40),
    "tours_formes": (5200, 450, 30),
    "ciel": (1300, 220, 60),
    "tapis+centre": (1400, 160, 12),
    "mobilier": (4800, 220, 30),       # poses de carte.py (MOBILIER) ; +200 (plan final : palmiers des écarts, esplanade)
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


def budget_appel(fonction: str, params: dict | None = None, variante: int = 0) -> tuple[float, float, float]:
    """Plafond (pièces, Neon, transparentes) d'un appel, formules résolues avec ses paramètres."""
    p = params or {}
    pieces, neon, transp = BUDGET_FONCTION[fonction]
    if fonction == "ciel.piece_or" and variante == 1:
        pieces = 8                      # une pièce sur quatre porte une petite étoile en relief (SPECS.md)
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


def _dans_bande(x, z, bx, bz_sud, bz_nord) -> bool:
    return abs(x) <= bx and -bz_nord <= z <= bz_sud


def zone_praticable(x, z) -> str | None:
    """Nature du sol praticable sous (x, z) : pelouse, trottoir, route, esplanade, ou None (couronne, hors carte)."""
    if _dans_bande(x, z, PELOUSE_X, PELOUSE_Z_SUD, PELOUSE_Z_NORD):
        return "pelouse"
    if _dans_bande(x, z, TROTTOIR_INT_X, TROTTOIR_INT_Z_SUD, TROTTOIR_INT_Z_NORD):
        return "trottoir_int"
    if _dans_bande(x, z, ROUTE_X, ROUTE_Z_SUD, ROUTE_Z_NORD):
        return "route"
    if _dans_bande(x, z, TROTTOIR_EXT_X, TROTTOIR_EXT_Z_SUD, TROTTOIR_EXT_Z_NORD):
        return "trottoir_ext"
    if abs(x) <= ESPLANADE_X and -ESPLANADE_Z <= z <= -ALIGNEMENT_Z_NORD:
        return "esplanade"
    return None


def profondeur_praticable(x, z) -> float:
    """Distance signée au bord des zones praticables (> 0 dedans, < 0 dans la couronne ou au-delà)."""
    return max(min(x - x0, x1 - x, z - z0, z1 - z) for (x0, x1, z0, z1) in ZONES_PRATICABLES)


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
        "pelouse": (2 * PELOUSE_X, PELOUSE_Z_SUD + PELOUSE_Z_NORD),
        "facades": (2 * ALIGNEMENT_X, ALIGNEMENT_Z_SUD + ALIGNEMENT_Z_NORD),
        "emprise_totale": (2 * COURONNE_X, COURONNE_Z_SUD + FOND_Z),
        "tapis_longueur_axe": round(longueur_polyligne(TAPIS_AXE), 2),
        "ceinture": len(CEINTURE),
        "ceinture_par_fonction": dict(sorted(par_fonction.items())),
        "tubes": len(TUBES), "nacelles": len(NACELLES), "pieces_or": len(PIECES_OR),
        "mobilier": len(MOBILIER), "reperes": len(REPERES),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(resume(), ensure_ascii=False, indent=1))
