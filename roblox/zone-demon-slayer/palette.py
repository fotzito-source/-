"""Palette de la zone Demon Slayer (village de l'ère Taishō, glycines, sanctuaires), version « stud ».

Ambiance « crépuscule en plein jour » : sol vert-bleu profond, glycines mauves, bois sombre,
enduit blanc, tuiles bleu nuit, vermillon des sanctuaires et lampions chauds. Les noms servent dans
tous les modules d'assets ; `vary()` casse les grands aplats.
"""

from __future__ import annotations

from kit import hexrgb, mix, shade

P = {
    # Sol
    "pierre": "#BDB8AC",          # dalles de l'allée (pierre froide)
    "pierre_fonce": "#A39E92",
    "pierre_claire": "#D2CEC4",
    "bordure": "#8E897E",
    "mousse": "#7DA05A",
    "herbe": "#4F9468",           # herbe vert-bleu (rappelle le sol sombre de la zone actuelle)
    "herbe_fonce": "#3F7D59",
    "herbe_claire": "#66AC79",
    "terre": "#7A5F48",
    "terre_fonce": "#5E4836",
    "gravier": "#C9C2B2",
    "eau": "#4A8FC8",
    "eau_fonce": "#3A73A8",

    # Bois, enduit, tuiles (maisons de l'ère Taishō)
    "bois_fonce": "#3F2C20",
    "bois": "#5E4030",
    "bois_moyen": "#7A5640",
    "bois_clair": "#A8805C",
    "enduit": "#F2EEE6",
    "enduit_creme": "#E8DDC6",
    "enduit_gris": "#CFCBC2",
    "tuile": "#2F3B5C",           # tuiles bleu nuit
    "tuile_fonce": "#232B45",
    "tuile_claire": "#43507A",
    "tuile_ardoise": "#3B3F4A",
    "cuivre_vert": "#5E9C8A",     # toits de cuivre patiné des sanctuaires
    "papier": "#F4EEDC",          # shoji
    "noren_bleu": "#2E3F73",
    "noren_violet": "#5B3F7E",
    "noren_rouge": "#A8352C",

    # Sanctuaires
    "vermillon": "#D2402F",       # piliers et torii
    "vermillon_fonce": "#A92F24",
    "noir_laque": "#1F1F24",
    "or": "#D9B24A",
    "corde": "#D8C79A",           # shimenawa
    "shide": "#FAFAF5",           # papiers en zigzag

    # Glycines et végétation
    "glycine": "#A98AE8",
    "glycine_claire": "#C9B4FA",
    "glycine_pale": "#E2D6FF",
    "glycine_fonce": "#7F63C9",
    "glycine_nuit": "#5E47A6",
    "feuille": "#4E8A44",
    "feuille_claire": "#6BA85A",
    "feuille_fonce": "#386B35",
    "tronc": "#4A3A33",           # troncs de glycine, gris-brun tordus
    "tronc_clair": "#6A5649",
    "bambou": "#7DB84A",
    "bambou_fonce": "#5E9A3A",
    "pin": "#2F6B48",

    # Montagne aux glycines (falaises bleu-violet comme la zone actuelle)
    "roche": "#4B4F95",
    "roche_claire": "#5D62AE",
    "roche_fonce": "#3B3F7A",
    "roche_nuit": "#2E3163",

    # Détails
    "noir": "#222226",
    "blanc": "#FAFAF5",
    "rouge": "#D63A2F",
    "orange_lampion": "#FFB24D",
    "jaune_lampion": "#FFD86B",
    "lampion_papier": "#F2DDB0",
    "metal": "#A3ADB3",
    "metal_fonce": "#5F676E",
    "fenetre": "#2E3A52",
    "fenetre_lumiere": "#FFD27A",  # fenêtres éclairées (Neon)

    # Train à vapeur
    "loco": "#26262C",
    "loco_rouge": "#9E2B25",
    "voiture": "#6B2E2A",
    "voiture_toit": "#3A3A40",
    "laiton": "#C9A24A",
}


def c(name: str) -> tuple:
    return hexrgb(P[name])


def vary(name_or_rgb, rng, amount: float = 0.06) -> tuple:
    """Légère variation de luminosité, pour casser les aplats."""
    base = c(name_or_rgb) if isinstance(name_or_rgb, str) else name_or_rgb
    f = 1 + float(rng.uniform(-amount, amount))
    return shade(base, f)


__all__ = ["P", "c", "vary", "mix", "shade"]
