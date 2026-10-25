"""Palette de la zone My Hero Academia (académie d'entraînement futuriste et sa ville moderne), version « stud ».

Ambiance « héroïque et lumineuse » : verre bleu-violet à reflets clairs, béton blanc et gris clair,
brique rouge des dortoirs, verts francs et touffus, trottoirs roses de la ville, accents orangés du
couchant et violets, bandes lumineuses (Neon) cyan et blanches. Pas de vert émeraude dominant : les
verts tirent vers le jaune-vert, le violet `violet` sert d'accent principal.

Les noms servent dans tous les modules d'assets ; `vary()` casse les grands aplats.
Dosage conseillé : 45 % de blancs et gris clairs (béton, dalles), 25 % de verre bleu-violet et de bleus,
20 % de verts, 10 % d'accents (brique, rose, orange, néons).
"""

from __future__ import annotations

from kit import hexrgb, mix, shade

P = {
    # --- Sol de la ville (chaussée et trottoirs roses) ---------------------------------
    "asphalte": "#5D6275",          # chaussée bleu-gris, claire pour rester lisible
    "asphalte_fonce": "#4E5366",
    "asphalte_clair": "#6E7488",
    "marquage": "#F4F4F0",          # lignes blanches, passages piétons
    "marquage_jaune": "#F2C94C",
    "trottoir_rose": "#E8A6AE",     # dalles roses des trottoirs de la ville
    "trottoir_rose_clair": "#F2C4C9",
    "trottoir_rose_fonce": "#D38F9A",
    "bordure": "#DCDDE2",           # bordure de trottoir blanc-gris
    "bordure_fonce": "#B9BBC4",
    "guidage": "#F5CD45",           # bande podotactile jaune

    # --- Sol du campus ---------------------------------------------------------------
    "pave_campus": "#D9D4E4",       # avenue du campus : dalles gris-lavande pâle (référence 2)
    "pave_campus_clair": "#E8E4F0",
    "pave_campus_fonce": "#C4BDD4",
    "dalle": "#CDD0D7",             # dalles de béton (parvis, terrains)
    "dalle_claire": "#E1E3E8",
    "dalle_fonce": "#B3B7C1",
    "piste": "#C9573E",             # piste d'athlétisme (terrains d'entraînement)
    "piste_fonce": "#B04A35",
    "piste_claire": "#D86C50",
    "arene": "#C4C7CF",             # sol de l'arène du stade (grandes dalles)
    "arene_claire": "#D7DAE0",
    "arene_fonce": "#AEB2BC",
    "herbe": "#62AE4C",             # pelouses touffues, vert franc (pas d'émeraude)
    "herbe_fonce": "#509B40",
    "herbe_claire": "#7DC25A",
    "terre": "#8C6B4E",
    "terre_fonce": "#6F5440",
    "gravier": "#CFC8BA",
    "eau": "#4FA3E0",
    "eau_fonce": "#3D86C4",

    # --- Béton, acier, façades blanches ------------------------------------------------
    "blanc": "#F6F7F9",
    "blanc_casse": "#ECEDF0",
    "beton_clair": "#DDE0E5",
    "beton": "#C4C8D0",
    "beton_fonce": "#A0A5AF",
    "gris_acier": "#7E8696",
    "acier": "#AAB3C0",
    "acier_fonce": "#5E6677",
    "marine": "#2F3B68",            # acier bleu nuit (portail, cadres)
    "marine_clair": "#43548C",
    "noir": "#26272D",
    "bois": "#B07A4E",              # lattes de bancs, terrasses
    "bois_clair": "#C99566",
    "bois_fonce": "#7A5236",

    # --- Façades de la ville ------------------------------------------------------------
    "facade_blanche": "#F1F2F5",
    "facade_ciel": "#C3DCF3",       # bureaux bleu clair
    "facade_ciel_fonce": "#9EC3E8",
    "facade_creme": "#F1E7D6",
    "facade_rose": "#F2D3D7",
    "carrelage": "#E3E6EB",
    "store_rouge": "#D9534A",       # stores et auvents
    "store_bleu": "#4C7BD9",
    "store_jaune": "#F2B84B",

    # --- Verre (tours jumelles, bâtiments de cours, ville) ------------------------------
    "vitre_violette": "#7468E3",    # verre bleu-violet des tours jumelles (références 1 et 2)
    "vitre_violette_claire": "#9A8FF2",
    "vitre_violette_fonce": "#5348B8",
    "vitre_bleue": "#5B8BE8",
    "vitre_bleue_fonce": "#3F66C2",
    "vitre_ciel": "#8FC6F2",        # bureaux de la ville
    "vitre_claire": "#C2E2F8",
    "vitre_reflet": "#E2EEFF",      # reflets (bandes claires sur les grandes vitres)
    "vitre_nuit": "#2F3A78",        # intérieurs sombres vus à travers le verre
    "verre_dome": "#BFE6F5",        # panneaux du dôme (Glass, transparence 0,35 à 0,5)
    "cadre_blanc": "#F4F5F8",       # montants et cadres des façades vitrées

    # --- Brique des dortoirs (référence 2) ----------------------------------------------
    "brique": "#B6533C",
    "brique_fonce": "#96412F",
    "brique_claire": "#CA6A50",
    "toit_ardoise": "#4B403D",      # toits en croupe brun-gris foncé
    "toit_ardoise_fonce": "#3A312F",
    "toit_ardoise_claire": "#5E524E",

    # --- Accents héroïques et couchant --------------------------------------------------
    "violet": "#6157F8",            # accent principal
    "violet_fonce": "#4A40D0",
    "lavande": "#B7AEFF",
    "lavande_pale": "#DAD5FF",
    "orange_couchant": "#FF9A4D",
    "orange": "#F28C28",
    "jaune": "#FFD34D",
    "rouge": "#E04A3A",
    "rouge_dome": "#D9443A",        # bâtiment en dôme rouge du parc d'entraînement
    "rouge_fonce": "#B53A2E",
    "bleu_vif": "#2F6BFF",

    # --- Lumières (matériau Neon) -------------------------------------------------------
    "neon_cyan": "#5CF0FF",
    "neon_blanc": "#F2FBFF",
    "neon_violet": "#9A84FF",
    "neon_orange": "#FFB25C",
    "fenetre_lumiere": "#FFE2A8",   # fenêtres éclairées chaudes
    "led": "#EAF6FF",               # têtes de lampadaires

    # --- Végétation ---------------------------------------------------------------------
    "feuille": "#4F9A3E",
    "feuille_claire": "#6DB54E",
    "feuille_pale": "#8DCB63",
    "feuille_fonce": "#3D7E35",
    "conifere": "#2F6B40",          # conifères taillés (référence 2)
    "conifere_clair": "#3F8550",
    "conifere_fonce": "#25573A",
    "haie": "#4A923D",
    "haie_claire": "#5DA84A",
    "tronc": "#6B4A35",
    "tronc_fonce": "#523826",
    "fleur_rose": "#F28DB5",
    "fleur_blanche": "#FFF6F0",
    "fleur_jaune": "#FFD34D",
    "fleur_violette": "#9B87F5",

    # --- Parc d'entraînement sous dôme : montagne artificielle ---------------------------
    "roche": "#948778",
    "roche_claire": "#AFA394",
    "roche_fonce": "#73695F",

    # --- Robots et matériel d'entraînement (dessins originaux) --------------------------
    "robot_gris": "#9AA3B0",
    "robot_blanc": "#E8EBEF",
    "robot_orange": "#F28C28",
    "robot_bleu": "#3F6FD8",
    "danger_jaune": "#F5C518",      # bandes de danger jaunes et noires
    "lentille": "#FF5A4D",          # « œil » des robots (Neon)
    "cible_rouge": "#E0473A",
    "cible_blanc": "#F7F4EE",

    # --- Stade --------------------------------------------------------------------------
    "siege_violet": "#6A5CE8",
    "siege_lavande": "#A99EF5",
    "siege_bleu": "#4072DA",
    "siege_blanc": "#E9EAF1",
    "ecran_fond": "#1C2140",        # écrans géants (aplats lumineux par-dessus)

    # --- Mur d'enceinte du campus (référence 1 : panneaux gris clair tachés, piles de brique) ---
    "panneau_mur": "#D9DBE0",
    "panneau_mur_clair": "#E6E8EC",
    "panneau_mur_tache": "#C5C8CF",
    "chaperon": "#A9AEB8",          # couvertine du mur

    # --- Viaduc et train de banlieue (générique : blanc à bandes, sans logo) ----------------
    "viaduc": "#CED2DA",
    "viaduc_fonce": "#A9AEB9",
    "rail": "#7C8391",
    "train_blanc": "#F3F5F8",
    "train_bande": "#3F78D8",
    "train_bande2": "#7468E3",

    # --- Stade : verrière et tribunes -------------------------------------------------------
    "verre_canopee": "#CFE8F7",     # verrière (Glass, transparence 0,3 à 0,45)
    "beton_tribune": "#D5D8DF",
    "ecran_lumiere": "#7FD8FF",     # écran géant allumé (Neon, aplats sans texte)

    # --- Voitures ----------------------------------------------------------------------
    "voiture_blanche": "#F1F2F4",
    "voiture_rouge": "#D8443A",
    "voiture_bleue": "#3F78D8",
    "voiture_jaune": "#F2C12E",
    "voiture_argent": "#B8BEC8",
    "voiture_menthe": "#8FD3C2",
    "pneu": "#2A2B30",
    "phare": "#FFF4D6",
    "feu_arriere": "#E0473A",
}


def c(name: str) -> tuple:
    return hexrgb(P[name])


def tirer(noms, rng) -> tuple:
    """Une couleur au hasard parmi une liste de noms (murs « pixel » en 2-4 teintes proches)."""
    return c(noms[int(rng.integers(len(noms)))])


def vary(name_or_rgb, rng, amount: float = 0.06) -> tuple:
    """Légère variation de luminosité, pour casser les aplats."""
    base = c(name_or_rgb) if isinstance(name_or_rgb, str) else name_or_rgb
    f = 1 + float(rng.uniform(-amount, amount))
    return shade(base, f)


__all__ = ["P", "c", "vary", "tirer", "mix", "shade"]
