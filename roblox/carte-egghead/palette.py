#!/usr/bin/env python3
"""Palette de la carte « île du futur » (CarteEgghead) : les 44 couleurs de la bible de style (STYLE.md § 2),
leurs groupes d'usage, les accords (rayures, anneaux), les zones de couleur des quatre côtés de la couronne et
les schémas de couleurs de chaque archétype (variantes 0 à 3 = V1 à V4 de la bible).

Règles (STYLE.md § 2.3) : une dominante (60-70 %) + une secondaire (20-30 %) + un accent (≤ 10 %), plus blanc_labo
ou creme pour piliers, socles et dessous ; chaud contre froid ; rayures à deux valeurs opposées ; l'or seulement
pour anneaux, pièces, étoiles, flèches et bagues ; une seule couleur de Neon par bâtiment ; ni gris, ni noir, ni
métal ; sol_vert réservé au sol. Tons dérivés permis : shade(c, 0,6 à 1,25) et mix(a, b, t) du kit ;
varier(c, rng, 0,03) seulement pour le végétal et les nuages.

    from palette import P, c, rgb, SCHEMAS, ZONES
    b.cyl((0, 5, 0), 4, 10, c("orange"))            # "#F27A22"
    s = SCHEMAS["tour_galettes"][variant]           # {"fut": "jaune_or", "galettes": "orange", ...}
"""

from __future__ import annotations

P = {
    # corps de bâtiments (11)
    "jaune_or": "#EDBF3D", "orange": "#F27A22", "rose_bonbon": "#F28CD0", "magenta": "#C05CC6",
    "violet": "#5634E0", "indigo": "#3C42B6", "bleu_roi": "#3670E2", "turquoise": "#17B3AD",
    "blanc_labo": "#EEF1F6", "creme": "#EFE4D0", "prune": "#6F2C62",
    # bandes et rayures (4)
    "bleu_nuit": "#1E3CA6", "rouge": "#E3374A", "vert_lime": "#9BCB45", "vert_pomme": "#52B840",
    # dômes et coiffes (2)
    "jaune_citron": "#F6E66E", "lavande": "#BCA8F2",
    # anneaux, or et lueurs (6) — cyan, neon_orange, neon_blanc, neon_violet : matériau Neon
    "or": "#F4D04A", "or_fonce": "#D99E2B", "cyan": "#3DE8FF", "neon_orange": "#FF9640",
    "neon_blanc": "#E8FBFF", "neon_violet": "#A898FF",
    # verre (2) — verre : Glass 0,45-0,6 ; hublot : verre OPAQUE (SmoothPlastic)
    "verre": "#AEE6FF", "hublot": "#63E2E3",
    # sol à grille et voies (5)
    "sol_vert": "#1FB45A", "sol_vert_clair": "#40CB6A", "sol_ligne": "#E4FBEC", "voie": "#2D3A8E",
    "dalle_labo": "#DDE3F5",
    # végétation (6)
    "haie": "#2CA03C", "haie_claire": "#55C64C", "palme": "#36B84A", "palme_fonce": "#0F6A37",
    "tronc": "#8A632E", "coco": "#D2842D",
    # repères du ciel (8)
    "oeuf_rose": "#F2C4E4", "oeuf_mauve": "#9C6EDB", "oeuf_violet": "#5A2FA0", "oeuf_interieur": "#2A2354",
    "cube_bleu": "#A9D6F7", "nuage": "#F7FBFF", "nuage_ombre": "#C8DCF0", "skyline": "#A7DCE9",
}
assert len(P) == 44

GROUPES = {
    "corps": ("jaune_or", "orange", "rose_bonbon", "magenta", "violet", "indigo", "bleu_roi", "turquoise",
              "blanc_labo", "creme", "prune"),
    "rayures": ("bleu_nuit", "rouge", "vert_lime", "vert_pomme"),
    "domes": ("jaune_citron", "lavande", "rose_bonbon", "turquoise", "rouge", "orange"),
    "or": ("or", "or_fonce"),
    "neon": ("cyan", "neon_orange", "neon_blanc", "neon_violet"),
    "verre": ("verre", "hublot"),
    "sol": ("sol_vert", "sol_vert_clair", "sol_ligne", "voie", "dalle_labo"),
    "vegetal": ("haie", "haie_claire", "palme", "palme_fonce", "tronc", "coco"),
    "ciel": ("oeuf_rose", "oeuf_mauve", "oeuf_violet", "oeuf_interieur", "cube_bleu", "nuage", "nuage_ombre",
             "skyline"),
}
# Couleurs à poser en matériau Neon (et seulement en petites pièces) ; cyan peut aussi servir en SmoothPlastic
NEON = ("cyan", "neon_orange", "neon_blanc", "neon_violet")
# Couleurs de sol : rien d'autre au sol (pas de gris)
SOL = ("sol_vert", "sol_vert_clair", "sol_ligne", "voie", "dalle_labo", "blanc_labo", "rouge")


def hexrgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def c(nom: str) -> str:
    """Nom de la palette → "#RRGGBB" (accepte aussi un "#RRGGBB" déjà résolu)."""
    if nom.startswith("#"):
        return nom
    return P[nom]


def rgb(nom: str) -> tuple[int, int, int]:
    return hexrgb(c(nom))


# --- Accords --------------------------------------------------------------------------------------------------
# Rayures à deux valeurs opposées (foncé, clair) : cônes, fûts, mâts, auvents, bordures
RAYURES = {
    "phare": ("bleu_nuit", "jaune_citron"),
    "vibreur": ("rouge", "blanc_labo"),          # bordures, mâts, auvents, cônes sucre d'orge : jamais une façade
    "raisin": ("violet", "lavande"),
    "lagon": ("turquoise", "blanc_labo"),
    "damier": ("jaune_citron", "vert_pomme"),
    "fraise": ("rouge", "blanc_labo"),
    "nuit": ("bleu_nuit", "blanc_labo"),         # pylônes de la machine
    "soleil": ("orange", "jaune_or"),
}
# Anneaux : halos flottants (souvent Neon fin), anneaux d'or des tubes, bords de chapeau rayés
ANNEAUX = {
    "or": ("or", "or_fonce"),                    # anneaux d'or hexagonaux des tubes fins, pièces, étoiles
    "tube_geant": ("jaune_or", "orange"),        # épais anneaux des tubes géants (alterner)
    "halo_cyan": "cyan",                         # Neon
    "halo_blanc": "neon_blanc",                  # Neon (halos des flèches, hublots allumés)
    "halo_violet": "neon_violet",                # Neon (œuf, machines, cœurs lumineux)
    "bord_citron": ("rouge", "turquoise", "rouge"),
    "bord_bonbon": ("violet", "vert_lime", "violet"),
    "bord_lagon": ("orange", "blanc_labo", "orange"),
    "bord_menthe": ("magenta", "lavande", "magenta"),
}

# --- Zones de couleur de la couronne (orientation : chaque côté a sa famille) ---------------------------------
ZONES = {
    "nord": {"nom": "côté du labo (sous l'œuf)", "dominantes": ("violet", "lavande", "rose_bonbon", "magenta"),
             "calmes": ("blanc_labo", "lavande", "creme"), "accents": ("turquoise", "jaune_citron"),
             "neon": "neon_violet"},
    "est": {"nom": "côté soleil", "dominantes": ("orange", "jaune_or", "jaune_citron", "rouge"),
            "calmes": ("creme", "blanc_labo", "jaune_citron"), "accents": ("bleu_roi", "turquoise", "violet"),
            "neon": "neon_orange"},
    "sud": {"nom": "côté bonbon", "dominantes": ("rose_bonbon", "magenta", "rouge", "creme"),
            "calmes": ("blanc_labo", "creme", "lavande"), "accents": ("turquoise", "vert_lime"),
            "neon": "neon_blanc"},
    "ouest": {"nom": "côté lagon", "dominantes": ("turquoise", "bleu_roi", "blanc_labo", "vert_lime"),
              "calmes": ("blanc_labo", "creme", "dalle_labo"), "accents": ("orange", "jaune_or"),
              "neon": "cyan"},
}

# --- Schémas de couleurs des archétypes (variante k = V(k+1) de STYLE.md) -------------------------------------
# Les clés nomment les parties de la recette ; chaque valeur est un nom de la palette (ou un tuple de noms pour
# des rayures alternées). « neon » = la seule couleur de Neon du bâtiment.
SCHEMAS = {
    # ---------------- assets/tours_rondes.py
    "tour_galettes": [   # T01
        {"fut": "jaune_or", "galettes": "orange", "pied": ("turquoise", "bleu_roi"), "dome": "jaune_citron",
         "cadres": "orange", "neon": "cyan"},                                         # V1 soleil (EH5)
        {"fut": "turquoise", "galettes": "blanc_labo", "pied": ("orange", "bleu_nuit"), "dome": "orange",
         "cadres": "orange", "neon": "cyan"},                                         # V2 lagon
        {"fut": "lavande", "galettes": "rose_bonbon", "pied": ("violet", "blanc_labo"), "dome": "jaune_citron",
         "cadres": "violet", "neon": "neon_orange"},                                  # V3 bonbon
        {"fut": "bleu_roi", "galettes": "jaune_or", "pied": ("rouge", "blanc_labo"), "dome": "turquoise",
         "cadres": "jaune_or", "neon": "cyan"},                                       # V4 marine
    ],
    "tour_champignon": [   # T02
        {"base": "jaune_or", "bord": ("rouge", "turquoise", "rouge"), "dome": "jaune_citron", "halo": "turquoise",
         "cloche": "creme", "pilier": "blanc_labo", "hublots": "hublot"},             # V1 citron (EH5)
        {"base": "rouge", "liseré_base": "blanc_labo", "bord": ("violet", "vert_lime", "violet"),
         "dome": "rose_bonbon", "halo": "vert_lime", "cloche": "creme", "pilier": "blanc_labo",
         "hublots": "hublot"},                                                        # V2 bonbon (EH5)
        {"base": "bleu_roi", "bord": ("orange", "blanc_labo", "orange"), "dome": "turquoise", "halo": "or",
         "cloche": "creme", "pilier": "blanc_labo", "hublots": "hublot"},             # V3 lagon
        {"base": "blanc_labo", "bord": ("magenta", "lavande", "magenta"), "dome": "vert_lime", "halo": "magenta",
         "cloche": "creme", "pilier": "blanc_labo", "hublots": "hublot"},             # V4 menthe
    ],
    "tour_soucoupe": [   # T08
        {"corps": "turquoise*0.78", "corniche": "lavande", "plateau": "rouge", "soucoupe": "bleu_nuit",
         "dome": "rouge", "gobelet": "dalle_labo", "neon": "cyan"},                   # V1 EH4
        {"corps": "orange", "corniche": "blanc_labo", "plateau": "jaune_or", "soucoupe": "bleu_roi",
         "dome": "jaune_citron", "gobelet": "dalle_labo", "neon": "cyan"},            # V2 coucher
        {"corps": "rose_bonbon", "corniche": "creme", "plateau": "turquoise", "soucoupe": "violet",
         "dome": "turquoise", "gobelet": "blanc_labo", "neon": "neon_blanc"},         # V3 fraise
        {"corps": "blanc_labo", "corniche": "lavande", "plateau": "orange", "soucoupe": "turquoise",
         "dome": "orange", "gobelet": "creme", "neon": "cyan"},                       # V4 neige
    ],
    "tour_tete_boule": [   # T03
        {"cone": ("bleu_nuit", "jaune_citron"), "base": "orange", "balcon": "rouge", "halo": "rouge",
         "tete": "jaune_citron", "menton": "bleu_roi", "porte": "bleu_roi"},          # V1 phare (EH5)
        {"cone": ("rouge", "blanc_labo"), "base": "jaune_or", "balcon": "turquoise", "halo": "or",
         "tete": "blanc_labo", "menton": "rouge", "porte": "bleu_nuit"},              # V2 sucre d'orge
        {"cone": ("turquoise", "blanc_labo"), "base": "bleu_roi", "balcon": "orange", "halo": "orange",
         "tete": "jaune_citron", "menton": "turquoise", "porte": "orange"},           # V3 lagune
        {"cone": ("bleu_nuit", "jaune_citron"), "base": "orange", "balcon": "rouge", "halo": "rouge",
         "tete": "rouge", "menton": "blanc_labo", "porte": "bleu_roi",
         "soucoupe": ("rouge", "blanc_labo", "bleu_roi")},                            # V4 anime
    ],
    "tour_pneus": [   # T07
        {"pneus": "bleu_roi", "bandes": "turquoise", "dome": "turquoise", "anneaux": "orange",
         "halo": "neon_blanc", "socle": "blanc_labo", "fleche": "or"},                # V1 EH3
        {"pneus": ("orange", "orange*0.85"), "bandes": "creme", "dome": "bleu_roi", "anneaux": "or",
         "halo": "neon_blanc", "socle": "blanc_labo", "fleche": "or"},                # V2 rouille
        {"pneus": "rose_bonbon", "bandes": "blanc_labo", "dome": "violet", "anneaux": "or", "halo": "cyan",
         "socle": "blanc_labo", "fleche": "or"},                                      # V3 bonbon
        {"pneus": "vert_lime", "bandes": "bleu_nuit", "dome": "jaune_citron", "anneaux": "rouge",
         "halo": "neon_blanc", "socle": "blanc_labo", "fleche": "or"},                # V4 menthe
    ],
    "tour_ruban": [   # T10
        {"base": "orange", "colonne": ("lavande", "jaune_citron"), "chapeau": "prune", "ruban": "orange",
         "vitres": "hublot", "neon": "neon_orange"},                                  # V1 EH3
        {"base": "bleu_roi", "colonne": ("rose_bonbon", "blanc_labo"), "chapeau": "rouge", "ruban": "jaune_or",
         "vitres": "hublot", "neon": "neon_blanc"},                                   # V2
        {"base": "turquoise", "colonne": ("blanc_labo", "jaune_citron"), "chapeau": "violet",
         "ruban": "rose_bonbon", "vitres": "hublot", "neon": "neon_violet"},          # V3
    ],
    "tour_bulbe": [   # T13
        {"bulbe": "violet", "tambour": "lavande", "bagues": "or", "fumee": "blanc_labo"},       # V1 (image 7)
        {"bulbe": "rose_bonbon", "tambour": "blanc_labo", "bagues": "turquoise", "fumee": "nuage"},  # V2
        {"bulbe": "orange", "tambour": "bleu_nuit", "bagues": "jaune_citron", "fumee": "blanc_labo"},  # V3
        {"bulbe": "turquoise", "tambour": "blanc_labo", "bagues": "rouge", "fumee": "nuage"},  # V4
    ],
    "tour_fusee": [   # T11 (type « blanche » = recette A, « capsule » = recette B)
        {"corps": "blanc_labo", "bandes": "orange", "ailerons": "orange", "hublots": "hublot",
         "cadres": "orange"},                                                         # V1 (EH5)
        {"corps": "vert_pomme", "bandes": "jaune_citron", "ailerons": "jaune_citron", "hublots": "hublot",
         "cadres": "jaune_citron"},                                                   # V2 (EH4)
        {"corps": "rouge", "bandes": "blanc_labo", "ailerons": "blanc_labo", "hublots": "hublot",
         "cadres": "blanc_labo"},                                                     # V3
        {"corps": "bleu_roi", "bandes": "jaune_or", "ailerons": "jaune_or", "hublots": "hublot",
         "cadres": "jaune_or"},                                                       # V4
    ],
    "tour_hublots": [   # T16 tambour à fenêtres / cylindre à hublots
        {"corps": "orange", "vitres": "hublot", "toit": "blanc_labo", "dome": "turquoise"},   # V1 (image 6)
        {"corps": "rose_bonbon", "vitres": "blanc_labo", "toit": "blanc_labo", "dome": "turquoise"},  # V2
        {"corps": "jaune_or", "vitres": "bleu_roi", "toit": "blanc_labo", "dome": "rouge"},   # V3
        {"corps": "blanc_labo", "vitres": "violet", "toit": "lavande", "dome": "jaune_citron"},  # V4
    ],
    # ---------------- assets/tours_formes.py
    "tour_manette": [   # T04
        {"tambour": "bleu_roi", "manette": "magenta", "facade": "magenta*1.18", "cadres": "orange",
         "boutons": "blanc_labo", "colonnade": "creme", "neon": "cyan"},              # V1 console (EH5)
        {"tambour": "turquoise", "manette": "violet", "facade": "violet*1.18", "cadres": "jaune_or",
         "boutons": "blanc_labo", "colonnade": "blanc_labo", "neon": "cyan"},         # V2 menthe
        {"tambour": "blanc_labo", "manette": "rouge", "facade": "rouge*1.15", "cadres": "bleu_nuit",
         "boutons": "jaune_citron", "colonnade": "jaune_citron", "neon": "neon_blanc"},  # V3 cerise
    ],
    "cone_etoile": [   # T15
        {"cone": ("rouge", "rouge*1.12"), "socle": "rouge*0.75", "anneau": "orange", "etoile": "or"},   # V1
        {"cone": ("bleu_nuit", "bleu_nuit*1.15"), "socle": "bleu_nuit*0.8", "anneau": "jaune_citron",
         "etoile": "or"},                                                             # V2
        {"cone": ("violet", "violet*1.15"), "socle": "violet*0.8", "anneau": "turquoise",
         "etoile": "jaune_citron"},                                                   # V3
        {"cone": ("turquoise", "blanc_labo"), "socle": "turquoise*0.8", "anneau": "rouge", "etoile": "or"},  # V4
    ],
    "tour_damier": [   # T06
        {"damier": ("jaune_citron", "vert_pomme"), "epaule": "bleu_roi", "tete": "jaune_citron",
         "feux": "rouge", "disque": "rouge", "socle": "blanc_labo", "neon": "neon_orange"},   # V1 citron-pomme
        {"damier": ("blanc_labo", "rouge"), "epaule": "turquoise", "tete": "jaune_citron", "feux": "rouge",
         "disque": "rouge", "socle": "blanc_labo", "neon": "neon_blanc"},             # V2 fraise
        {"damier": ("lavande", "violet"), "epaule": "orange", "tete": "blanc_labo", "feux": "neon_orange",
         "disque": "orange", "socle": "blanc_labo", "neon": "neon_orange"},           # V3 raisin
        {"damier": ("blanc_labo", "turquoise"), "epaule": "jaune_or", "tete": "rose_bonbon", "feux": "rouge",
         "disque": "rouge", "socle": "blanc_labo", "neon": "neon_blanc"},             # V4 lagon
    ],
    "tour_bourrelets": [   # T05 (variantes 0, 2, 3 : recette A bourrelets ; variante 1 : recette B disques)
        {"corps": "violet", "pied": ("orange", "jaune_or"), "dome": "violet*1.15", "cadres": "orange",
         "neon": "neon_orange"},                                                      # V1 (EH5) A
        {"fut": "indigo", "disques": "violet", "dome": "lavande", "neon": "cyan"},    # V2 (EH4) B
        {"corps": "rose_bonbon", "fut": "blanc_labo", "dome": "jaune_citron", "cadres": "blanc_labo",
         "neon": "cyan"},                                                             # V3 A
        {"corps": "turquoise", "pied": ("bleu_nuit", "blanc_labo"), "dome": "orange", "cadres": "orange",
         "neon": "neon_orange"},                                                      # V4 A
    ],
    "tour_bureaux": [   # T12
        {"corps": "bleu_nuit", "bandes": "hublot", "dome": "turquoise", "corniche": "blanc_labo"},  # V1 (EH5)
        {"corps": "blanc_labo", "bandes": "bleu_roi", "dome": "orange", "corniche": "bleu_roi"},    # V2
        {"corps": "violet", "bandes": "rose_bonbon", "dome": "lavande", "corniche": "rose_bonbon"},  # V3
        {"corps": "orange", "bandes": "creme", "dome": "turquoise", "corniche": "creme"},            # V4
    ],
    "plateau_disques": [   # T14
        {"disques": "turquoise", "mat": "blanc_labo", "dessous": "turquoise*0.8", "points": "cyan"},  # V1
        {"disques": "jaune_or", "mat": "blanc_labo", "dessous": "orange", "points": "neon_orange"},   # V2
        {"disques": "rose_bonbon", "mat": "blanc_labo", "dessous": "rose_bonbon*0.8", "points": "neon_blanc"},
        {"disques": "bleu_roi", "mat": "blanc_labo", "dessous": "bleu_roi*0.8", "points": "cyan"},  # V4
    ],
    "tour_anneau": [   # T17
        {"fut": "blanc_labo", "anneau": "violet", "dome": "jaune_citron", "fleche": ("orange", "jaune_citron"),
         "neon": "cyan"},                                                             # V1 (EH4)
        {"fut": "blanc_labo", "anneau": "rouge", "dome": "turquoise", "fleche": ("rouge", "blanc_labo"),
         "neon": "neon_blanc"},                                                       # V2
        {"fut": "creme", "anneau": "bleu_roi", "dome": "orange", "fleche": ("or", "or"), "neon": "cyan"},  # V3
        {"fut": "lavande", "anneau": "turquoise", "dome": "rose_bonbon", "fleche": ("jaune_citron", "jaune_citron"),
         "neon": "neon_blanc"},                                                       # V4
    ],
    "boutique_arche": [   # K01
        {"facade": "magenta", "cadre": "violet", "arche": "jaune_or", "gelule": "bleu_roi", "neon": "cyan"},
        {"facade": "turquoise", "cadre": "bleu_nuit", "arche": "orange", "gelule": "rose_bonbon",
         "neon": "neon_blanc"},
        {"facade": "jaune_or", "cadre": "rouge", "arche": "bleu_roi", "gelule": "turquoise", "neon": "cyan"},
        {"facade": "rose_bonbon", "cadre": "blanc_labo", "arche": "turquoise", "gelule": "violet",
         "neon": "neon_blanc"},
    ],
    # kiosque : un schéma par type et par variante
    "kiosque_dome": [   # K04
        {"tambour": "blanc_labo", "bord": "orange", "dome": "jaune_citron", "socle": "violet"},
        {"tambour": "blanc_labo", "bord": "rose_bonbon", "dome": "turquoise", "socle": "bleu_nuit"},
        {"tambour": "bleu_roi", "bord": "jaune_or", "dome": "rouge", "socle": "blanc_labo"},
        {"tambour": "lavande", "bord": "vert_lime", "dome": "violet", "socle": "blanc_labo"},
    ],
    "kiosque_boutons": [   # K02
        {"tambour": "bleu_nuit", "bandeau": "rose_bonbon",
         "boutons": ("rose_bonbon", "jaune_citron", "vert_lime", "orange"), "neon": "cyan"},
        {"tambour": "blanc_labo", "bandeau": "turquoise", "boutons": ("orange", "rouge", "bleu_roi"),
         "neon": "neon_orange"},
        {"tambour": "violet", "bandeau": "jaune_citron", "boutons": ("cyan", "rose_bonbon", "blanc_labo"),
         "neon": "cyan"},
        {"tambour": "turquoise", "bandeau": "orange", "boutons": ("jaune_citron", "blanc_labo"),
         "neon": "neon_blanc"},
    ],
    "kiosque_arcade": [   # K03
        {"corps": "magenta", "liseres": "vert_lime", "neon": "cyan"},
        {"corps": "bleu_roi", "liseres": "jaune_citron", "neon": "neon_orange"},
        {"corps": "rouge", "liseres": "turquoise", "neon": "cyan"},
        {"corps": "violet", "liseres": "orange", "neon": "neon_blanc"},
    ],
    "kiosque_hublots": [   # K07 (paire de tambours « machine à laver »)
        {"tambour": "indigo", "cadre": "lavande", "vitre": "bleu_nuit"},
        {"tambour": "turquoise", "cadre": "blanc_labo", "vitre": "hublot"},
        {"tambour": "rose_bonbon", "cadre": "blanc_labo", "vitre": "violet"},
        {"tambour": "jaune_or", "cadre": "blanc_labo", "vitre": "bleu_roi"},
    ],
}


def resoudre(spec: str) -> str:
    """« orange » → "#F27A22" ; « turquoise*0.78 » → shade(turquoise, 0,78) en "#RRGGBB"."""
    if "*" not in spec:
        return c(spec)
    nom, f = spec.split("*")
    r, g, b = hexrgb(c(nom))
    f = float(f)
    if f <= 1:
        r, g, b = (round(v * f) for v in (r, g, b))
    else:   # éclaircir comme kit.shade : vers le blanc
        r, g, b = (round(v + (255 - v) * (f - 1)) for v in (r, g, b))
    return "#%02X%02X%02X" % (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def schema(archetype: str, variante: int) -> dict:
    """Schéma de couleurs résolu en "#RRGGBB" (tuples conservés) ; variante prise modulo le nombre de schémas."""
    s = SCHEMAS[archetype][variante % len(SCHEMAS[archetype])]
    out = {}
    for k, v in s.items():
        out[k] = tuple(resoudre(x) for x in v) if isinstance(v, tuple) else resoudre(v)
    return out


if __name__ == "__main__":
    for nom, liste in SCHEMAS.items():
        for i in range(len(liste)):
            schema(nom, i)
    print(f"{len(P)} couleurs, {len(SCHEMAS)} archétypes, schémas résolus sans erreur")
