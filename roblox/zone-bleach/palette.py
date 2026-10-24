"""Palette de la zone Bleach (la cité blanche aux toits ocre), version « stud ».

Ambiance « cité céleste en plein midi » : murs blanc cassé dominants (trois ou quatre blancs proches pour
casser les aplats), tuiles ocre-orangé des toits et des chaperons de murs, pierre pâle et chaude au sol,
cerisiers roses, quelques touches de laque rouge et de bleu profond. Le faubourg d'entrée, lui, est en bois
sombre chaud et tuiles grises, sur une route de sable. Les noms servent dans tous les modules d'assets ;
`vary()` casse les grands aplats.

Pas de vert émeraude dominant : les verts sont tendres (jeunes feuilles) ou sombres (pins), en petites masses.
"""

from __future__ import annotations

from kit import hexrgb, mix, shade

P = {
    # --- Sol -------------------------------------------------------------------------------------
    "dallage": "#E4DED2",          # grandes dalles claires de la cité (presque blanches, chaudes)
    "dallage_ombre": "#D6CFC0",
    "pierre_claire": "#D3CCBD",
    "pierre": "#BDB4A3",           # pierre pâle chaude (socles, bordures)
    "pierre_fonce": "#A0968A",
    "bordure": "#8B8275",
    "joint": "#9C9283",            # joints entre dalles
    "gravier": "#E9E5DC",          # gravier blanc ratissé des cours
    "gravier_ombre": "#DAD5CA",
    "sable": "#DCC596",            # route de sable du faubourg
    "sable_clair": "#E6D3AA",
    "sable_fonce": "#C9AE7C",
    "terre": "#9E7E59",            # terre battue, ruelles, champs
    "terre_fonce": "#7C6146",
    "dalle_chemin": "#CFC8BA",     # grandes dalles du chemin central du faubourg
    "dalle_chemin_fonce": "#B9B1A2",
    "herbe": "#8DB565",            # herbe tendre (petites surfaces seulement)
    "herbe_fonce": "#73A052",
    "herbe_claire": "#A5C77A",
    "mousse": "#96AE62",
    "culture": "#6FA548",          # rangs de légumes des jardins du faubourg
    "eau": "#5C9FD6",
    "eau_fonce": "#3F80BC",
    "eau_claire": "#8BC0E6",

    # --- Cité blanche ----------------------------------------------------------------------------
    "blanc": "#F5F2EB",            # enduit blanc principal (murs, tours)
    "blanc_pur": "#FBFAF6",        # rehauts (corniches, bandeaux hauts)
    "blanc_creme": "#EDE7D9",      # variation chaude
    "blanc_ombre": "#DFD9CC",      # faces en retrait, joints de panneaux
    "blanc_gris": "#CEC9BE",       # soubassements d'enduit, revers ombrés
    "ocre": "#D8924A",             # tuiles ocre-orangé (toits, chaperons) : la couleur signature
    "ocre_clair": "#E8AE68",       # tuiles de rive, faîtages éclairés
    "ocre_fonce": "#B36F36",       # sous-faces, ombres de toits, rangs alternés
    "ocre_brun": "#8E5530",        # about de tuiles, épis
    "terre_cuite": "#C9673A",      # accent plus rouge (rangs de tuiles, rives)
    "bleu": "#3C62B4",             # toits d'accent (quelques tours), rideaux
    "bleu_profond": "#2B4688",
    "bleu_clair": "#6F92D8",
    "laque_rouge": "#C8352D",      # laque rouge : passerelle, balcons, bandes de la tour finale
    "laque_rouge_fonce": "#9B2823",
    "laque_noire": "#24242B",      # flèches sombres, ferrures
    "ardoise_fleche": "#34363F",   # flèches et pointes de la grande tour
    "or": "#D9B24A",               # plaques, boutons de porte, épis dorés
    "bronze": "#9A7438",
    "fenetre": "#2C3346",          # ouvertures sombres (meurtrières, fenêtres hautes)
    "fenetre_bois": "#3E3A3A",

    # --- Faubourg (bois sombre et tuiles grises) -------------------------------------------------
    "bois_fonce": "#45301F",
    "bois": "#634330",
    "bois_moyen": "#82603F",
    "bois_clair": "#AE875C",
    "bois_gris": "#7B6E5E",        # bois patiné des tours de guet et des clôtures
    "bois_gris_clair": "#9A8C79",
    "tuile_grise": "#6E7581",
    "tuile_grise_fonce": "#555B67",
    "tuile_grise_claire": "#8C939E",
    "torchis": "#D9CBB0",          # murs de torchis beige entre les poteaux
    "papier": "#F4EEDC",           # shoji
    "sudare": "#C8AE78",           # stores de bambou
    "noren_bleu": "#2E4A80",       # rideaux de boutique
    "noren_indigo": "#253863",
    "noren_ocre": "#C98A3C",
    "noren_blanc": "#F2EEE4",
    "noren_rouge": "#B03A30",
    "chaume": "#B79A62",

    # --- Cerisiers et végétation -----------------------------------------------------------------
    "sakura": "#F3A6C0",
    "sakura_clair": "#F8C6D7",
    "sakura_pale": "#FCE2EB",
    "sakura_vif": "#E97FA5",
    "sakura_fonce": "#D3628B",
    "tronc": "#4C3631",            # tronc de cerisier brun-violacé
    "tronc_clair": "#6D5148",
    "feuille": "#5F9C4A",
    "feuille_claire": "#82B85C",
    "feuille_fonce": "#41793D",
    "feuille_nuit": "#2F5E34",
    "pin": "#376B46",
    "pin_clair": "#4D8558",
    "azalee": "#E2588A",

    # --- Colline finale, rocher, monolithe -------------------------------------------------------
    "roche": "#B9AD96",            # roche pâle chaude de la colline
    "roche_claire": "#D0C5AF",
    "roche_fonce": "#9A8D77",
    "roche_ombre": "#7D715F",
    "monolithe": "#8D9098",        # grand monolithe gris-bleu
    "monolithe_clair": "#A9ACB3",
    "monolithe_fonce": "#6F727B",
    "monolithe_nuit": "#585B64",
    "lichen": "#A7B07A",

    # --- Lumières et détails ---------------------------------------------------------------------
    "noir": "#222226",
    "corde": "#D8C79A",            # corde sacrée (shimenawa) du monolithe
    "shide": "#FAFAF5",
    "lampion_papier": "#F2DDB0",
    "jaune_lampion": "#FFD86B",    # lumière (Neon)
    "orange_lampion": "#FFB24D",
    "fenetre_lumiere": "#FFD27A",
    "rouge": "#D63A2F",
    "metal": "#A3ADB3",
    "metal_fonce": "#5F676E",
    "fer": "#4A4D55",
    "vert_bambou": "#86B84E",
    "vert_bambou_fonce": "#5E9A3A",
    "toile_ecrue": "#E9DFC8",      # bâches d'échoppes
}


def c(name: str) -> tuple:
    return hexrgb(P[name])


def vary(name_or_rgb, rng, amount: float = 0.06) -> tuple:
    """Légère variation de luminosité, pour casser les aplats."""
    base = c(name_or_rgb) if isinstance(name_or_rgb, str) else name_or_rgb
    f = 1 + float(rng.uniform(-amount, amount))
    return shade(base, f)


def blanc_pixel(rng) -> tuple:
    """Un des blancs de la cité, tiré au hasard (murs en « pixels » de teintes proches)."""
    return c(("blanc", "blanc", "blanc_creme", "blanc_pur", "blanc_ombre")[int(rng.integers(0, 5))])


__all__ = ["P", "c", "vary", "blanc_pixel", "mix", "shade"]
