"""Palette de la zone 5 (ville de nuit pendant un incident surnaturel), version « stud ».

Idée : une grande ville japonaise « de nuit » mais lisible sous le ciel bleu du jeu. Les bâtiments
restent dans les bleus nuit, ardoise et acier (jamais noirs), relevés par du béton clair, de la brique
et du carrelage blanc ; les accents viennent des néons (magenta, cyan, jaune, vert, orange), des
fenêtres éclairées chaudes ou froides et des passages piétons blancs. Après la place, l'incident :
gravats gris, fissures sombres, lueurs violettes et dômes de barrière violet nuit.

Les noms servent dans tous les modules d'assets ; `vary()` casse les grands aplats.
"""

from __future__ import annotations

from kit import hexrgb, mix, shade

P = {
    # --- Sol : chaussée, marquages, trottoirs ---------------------------------
    "asphalte": "#3D4363",          # chaussée bleu-gris (comme la rue actuelle du jeu, en plus lisible)
    "asphalte_fonce": "#343A57",
    "asphalte_clair": "#4B5275",
    "asphalte_place": "#454C6E",    # carrefour, légèrement plus clair
    "marquage": "#F2F4F8",          # passages piétons et lignes blanches
    "marquage_jaune": "#F2C531",    # ligne médiane, lignes de stop des rues
    "trottoir": "#ABB0BE",          # dalles gris clair bleuté
    "trottoir_clair": "#C3C7D2",
    "trottoir_fonce": "#9298A8",
    "bordure": "#7E8494",           # bordure de trottoir
    "guidage": "#F2C531",           # bandes podotactiles jaunes (typiques des trottoirs japonais)
    "ruelle": "#4A4F66",            # ruelles et arrière-cours
    "ruelle_fonce": "#3F4459",
    "parking": "#5A6078",

    # --- Façades -------------------------------------------------------------
    "bleu_nuit": "#27315C",
    "bleu_marine": "#34437D",
    "bleu_ardoise": "#4A5D98",
    "bleu_acier": "#6A80B2",
    "bleu_gris": "#8A98BA",
    "bleu_pale": "#B7C3DE",
    "beton": "#B8BDC9",
    "beton_clair": "#D5D9E2",
    "beton_fonce": "#8C92A2",
    "carrelage": "#EBEEF4",         # carrelage blanc des petits immeubles
    "creme": "#E4DACA",
    "brique": "#B04B3F",
    "brique_fonce": "#87362F",
    "bordeaux": "#7C2D47",
    "violet_nuit": "#3E3168",
    "anthracite": "#3A3E4C",
    "gris_chaud": "#A49D96",

    # --- Vitres et fenêtres --------------------------------------------------
    "vitre": "#22304F",             # vitre sombre (fenêtre éteinte)
    "vitre_bleue": "#3F6FB2",
    "vitre_cyan": "#68C6E6",
    "vitre_claire": "#A9D8F0",
    "fenetre_chaude": "#FFD27A",    # fenêtres éclairées (Neon)
    "fenetre_froide": "#DCE9FF",    # bureaux éclairés (Neon)
    "fenetre_rose": "#FFB3D9",

    # --- Néons et écrans (matériau Neon) -------------------------------------
    "neon_magenta": "#FF3FB4",
    "neon_rose": "#FF7AC8",
    "neon_cyan": "#2EE6FF",
    "neon_bleu": "#3D7BFF",
    "neon_jaune": "#FFE14A",
    "neon_orange": "#FF9A2E",
    "neon_rouge": "#FF3B4E",
    "neon_vert": "#5CFF8E",         # accent ponctuel seulement (pas de vert dominant)
    "neon_violet": "#A35CFF",
    "neon_blanc": "#F4F8FF",
    "ecran_fond": "#151B36",        # cadre / fond d'écran géant
    "ecran_bleu": "#2F6BFF",
    "ecran_violet": "#7A3CFF",
    "ecran_rose": "#FF5FA8",
    "ecran_orange": "#FF8A3D",

    # --- Commerces -------------------------------------------------------------
    "rideau_metal": "#9AA3B0",      # rideaux métalliques baissés
    "rideau_fonce": "#747C8A",
    "auvent_rouge": "#D2453A",
    "auvent_bleu": "#2F5FB8",
    "auvent_jaune": "#F2B632",
    "auvent_violet": "#6A4FC8",
    "noren_rouge": "#B8322C",
    "noren_bleu": "#2E3F73",
    "lampion": "#FF8A3D",           # lampion rouge-orangé (Neon)
    "enseigne_blanc": "#F7F8FA",
    "enseigne_noir": "#1E2030",
    "graffiti_1": "#FF5FA8",
    "graffiti_2": "#2EC8E6",
    "graffiti_3": "#F2C531",

    # --- Mobilier urbain -------------------------------------------------------
    "metal": "#A3ADB8",
    "metal_clair": "#CDD4DD",
    "metal_fonce": "#5E6672",
    "poteau_beton": "#BDBDB4",      # poteau électrique en béton
    "transfo": "#8F98A0",
    "cable": "#1E1F26",
    "feu_boitier": "#4B4F5A",
    "feu_vert": "#2FE0C0",          # le « vert » des feux japonais, bleuté
    "feu_jaune": "#FFC93A",
    "feu_rouge": "#FF3A3A",
    "rambarde": "#E9EDF3",          # garde-corps blancs
    "distrib_rouge": "#D63A3A",
    "distrib_bleu": "#2F6FD6",
    "distrib_blanc": "#F2F4F7",
    "boisson_1": "#FF6A3D",
    "boisson_2": "#3DB8FF",
    "boisson_3": "#FFE04A",
    "boisson_4": "#7DE07A",
    "velo_1": "#D94A4A",
    "velo_2": "#3A6FD0",
    "velo_3": "#E8E8E8",
    "pneu": "#26272D",

    # --- Végétation (arbres d'alignement) ------------------------------------
    "feuille": "#4F9A55",
    "feuille_claire": "#6FBF5E",
    "feuille_fonce": "#3C7B45",
    "ginkgo": "#F2C440",            # ginkgo jaune d'automne (variante)
    "ginkgo_clair": "#FFD966",
    "tronc": "#5A4636",
    "terre": "#5E4A3C",
    "herbe": "#5DA05A",

    # --- Viaduc, train, passerelles -------------------------------------------
    "viaduc": "#A9AFBC",
    "viaduc_fonce": "#868D9C",
    "viaduc_clair": "#C6CBD5",
    "acier_bleu": "#3E5C9A",        # poutres d'acier peintes
    "acier_bleu_fonce": "#2E4677",
    "train_inox": "#CBD0D8",
    "train_inox_fonce": "#A4AAB4",
    "train_bande": "#7A5CFF",       # livrée générique violette et cyan (aucune livrée réelle)
    "train_bande_2": "#2EC8E6",
    "train_vitre": "#2A3550",
    "train_toit": "#7D8590",
    "ballast": "#6E6A66",
    "rail": "#8A8F98",

    # --- Incident : ruines, barrière --------------------------------------------
    "gravats": "#8E9099",
    "gravats_clair": "#B5B7BE",
    "gravats_fonce": "#64676F",
    "ferraille": "#6B5A50",         # fers à béton rouillés
    "fissure": "#1B1C28",
    "lueur_violette": "#9B4DFF",    # lueurs étranges (Neon)
    "lueur_bleue": "#4D6BFF",
    "lueur_rose": "#E04DFF",
    "verre_brise": "#9FD6EE",       # éclats de verre (transparence 0,3-0,5)
    "voile": "#2A1748",             # dôme de barrière violet nuit
    "voile_moyen": "#3A2163",
    "voile_clair": "#4E2D84",
    "voile_bord": "#8A4DFF",        # liserés lumineux du dôme (Neon)
    "chantier_jaune": "#F2C531",
    "chantier_noir": "#23242B",
    "barriere_rouge": "#E0453A",
    "barriere_blanc": "#F4F4F4",
    "carrosserie_1": "#E8EAEE",     # voitures (génériques)
    "carrosserie_2": "#C23B3B",
    "carrosserie_3": "#2F4E8C",
    "carrosserie_4": "#F2C531",     # taxi jaune générique

    # --- Divers ------------------------------------------------------------------
    "noir": "#1F2026",
    "blanc": "#F7F8FA",
    "rouge": "#D9433A",
    "jaune": "#F2C531",
    "orange": "#F28A2E",
    "or": "#D9B24A",
    "rouge_balise": "#FF2E3A",      # feux d'obstacle rouges sur les toits (Neon)
    "citerne": "#C9CED6",           # citernes et clims sur les toits
    "clim": "#E2E5EA",
}


def c(name: str) -> tuple:
    return hexrgb(P[name])


def vary(name_or_rgb, rng, amount: float = 0.06) -> tuple:
    """Légère variation de luminosité, pour casser les aplats."""
    base = c(name_or_rgb) if isinstance(name_or_rgb, str) else name_or_rgb
    f = 1 + float(rng.uniform(-amount, amount))
    return shade(base, f)


# Familles utiles pour tirer des couleurs au hasard (toujours via b.rng)
FACADES_BLEUES = ["bleu_nuit", "bleu_marine", "bleu_ardoise", "bleu_acier"]
FACADES_CLAIRES = ["beton", "beton_clair", "carrelage", "creme", "bleu_pale"]
FACADES_CHAUDES = ["brique", "brique_fonce", "bordeaux", "gris_chaud"]
NEONS = ["neon_magenta", "neon_cyan", "neon_jaune", "neon_orange", "neon_vert", "neon_violet", "neon_rouge", "neon_bleu"]

__all__ = ["P", "c", "vary", "mix", "shade", "FACADES_BLEUES", "FACADES_CLAIRES", "FACADES_CHAUDES", "NEONS"]
