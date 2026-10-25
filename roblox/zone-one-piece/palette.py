"""Palette de la zone One Piece (mer de l'Est ensoleillée : moulins, port pirate, crique du crâne), version « stud ».

Ambiance : plein soleil, couleurs franches et joyeuses. Sable clair, eau turquoise et bleu profond, bois
chaud des quais et des navires, voiles crème, rouge et jaune pirates, prairies vert pomme, murs de couleur
(blanc, crème, jaune, bleu, rose, rouge) et toits rouges, bleus ou turquoise. Pas de gris sale : les pierres
et les roches tirent vers le beige chaud. Les noms servent dans tous les modules d'assets ; `vary()` casse
les grands aplats.
"""

from __future__ import annotations

from kit import hexrgb, mix, shade

P = {
    # --- Sol : sable, chemin de terre, prairie -------------------------------------------------
    "sable": "#F2DFA7",            # plage et allées de sable (couleur de la zone actuelle)
    "sable_clair": "#F8EBC4",
    "sable_fonce": "#E3C98A",
    "sable_mouille": "#D8BC82",    # bord de l'eau, fond de la crique
    "chemin": "#D6AE70",           # chemin de terre de la campagne
    "chemin_clair": "#E0BE86",
    "chemin_fonce": "#B98B52",     # ornières
    "herbe": "#6CBF45",            # prairie vert pomme (jamais d'émeraude)
    "herbe_claire": "#86D05A",
    "herbe_fonce": "#4FA23A",
    "herbe_seche": "#A9C85A",      # touches jaunies des collines
    "terre": "#9C6B3E",            # flancs de collines, strates
    "terre_fonce": "#7A5230",
    "terre_claire": "#C08A55",

    # --- Pierre chaude : pavés du bourg, quais, murets -------------------------------------
    "pave": "#E6D5AE",             # pavés ocre clair du bourg
    "pave_fonce": "#D0BA8E",
    "pave_rose": "#E8C4A8",        # pavés rosés (motifs)
    "pave_clair": "#F2E8CF",       # chemin clair dans l'axe de la rue du bourg
    "pierre": "#D9CDB4",           # quais, murs de soutènement
    "pierre_claire": "#ECE3CF",
    "pierre_fonce": "#B9AA8C",
    "bordure": "#A8977A",          # bordures de trottoir, margelles du quai

    # --- Eau ----------------------------------------------------------------------------------
    "eau": "#2AA3D0",              # bassins du port
    "eau_claire": "#3FC1E0",
    "eau_lagon": "#62D6E4",        # haut-fond turquoise le long des quais et des plages
    "eau_profonde": "#1E86C0",     # pleine mer
    "ecume": "#E6F8FC",            # écume blanche (bords, sillages)
    "cascade": "#BDEFF8",

    # --- Bois (quais, navires, maisons de pêcheurs) ----------------------------------------
    "bois": "#8A5A36",
    "bois_fonce": "#5E3B24",
    "bois_clair": "#B07D4F",
    "bois_pale": "#CFA272",        # planches neuves, caisses
    "bois_quai": "#9E6E45",        # planches des pontons
    "bois_flotte": "#BFA88A",      # bois délavé par le sel
    "coque_rouge": "#8E3B2A",      # coque brun-rouge des navires
    "coque_jaune": "#E3B23C",      # coque jaune (caravelle)
    "coque_noire": "#2F2A2C",

    # --- Voiles, cordages, toiles --------------------------------------------------------------
    "voile": "#F8F4E8",
    "voile_ombre": "#E6DECA",
    "voile_rouge": "#D63A2F",
    "corde": "#D8C08A",
    "corde_fonce": "#B39A66",
    "filet": "#7E6A4C",
    "toile_rouge": "#E04A3C",      # auvents rayés (avec blanc)
    "toile_bleue": "#3A86D4",
    "toile_jaune": "#F5C842",
    "toile_verte": "#4FB06A",

    # --- Accents francs ------------------------------------------------------------------------
    "rouge": "#D63A2F",
    "rouge_fonce": "#A92A22",
    "jaune": "#F5C842",
    "jaune_fonce": "#D9A92E",
    "orange": "#F28C28",
    "turquoise": "#3FB8A8",
    "turquoise_fonce": "#2E9488",
    "bleu": "#3A6FC4",
    "bleu_fonce": "#284E91",
    "bleu_marine": "#1B2150",      # fond du panneau « ZONE RARE » (comme le portique actuel du jeu)
    "violet_rare": "#B48CFF",      # lettres « ZONE RARE »
    "rose": "#F2A0B5",             # moulin rose
    "rose_fonce": "#D97A96",
    "blanc": "#FAFAF5",
    "noir": "#26262B",
    "or": "#F2C230",
    "or_clair": "#FFE37A",
    "rubis": "#E0315A",
    "emeraude_gemme": "#3CCB7F",   # petites gemmes du trésor seulement
    "saphir": "#3C7BE0",

    # --- Murs et toits des maisons du port ---------------------------------------------------
    "mur_blanc": "#F6F1E6",
    "mur_creme": "#F1E2BF",
    "mur_jaune": "#F7D877",
    "mur_bleu": "#86B8E6",
    "mur_rose": "#F4B8A6",
    "mur_rouge": "#D9574A",
    "mur_turquoise": "#8FD6CC",
    "colombage": "#6B4428",        # pans de bois
    "toit_rouge": "#D63A2F",
    "toit_rouge_fonce": "#B02E25",
    "toit_bleu": "#3A6FC4",
    "toit_turquoise": "#3FB8A8",
    "toit_orange": "#E8763A",
    "toit_brun": "#8A4B2E",
    "dome": "#8D9AAE",             # dômes de pierre bleu-gris des moulins de pierre
    "dome_fonce": "#6F7C91",
    "volet_bleu": "#2F6DB5",
    "volet_vert": "#3E9A6A",
    "volet_rouge": "#C23B2E",
    "fenetre": "#2E4A6B",
    "vitre": "#9ED8F0",
    "fenetre_lumiere": "#FFD27A",  # fenêtres éclairées (Neon)

    # --- Nature ---------------------------------------------------------------------------------
    "palme": "#4FA23A",
    "palme_claire": "#6CBF45",
    "palme_fonce": "#3B8A2E",
    "tronc": "#9C6B3E",
    "tronc_fonce": "#7E5530",
    "tronc_clair": "#B9875A",
    "coco": "#6B4A2B",
    "feuillage": "#58AE3E",        # arbres fruitiers, buissons
    "feuillage_fonce": "#3F8C32",
    "agrume": "#FF9A1F",           # mandarines, oranges
    "fleur_rouge": "#E8453C",
    "fleur_jaune": "#FFD23F",
    "fleur_blanche": "#FFFFFF",
    "fleur_rose": "#FF8FB8",
    "roche": "#B4AA98",            # rochers de bord de mer (beige-gris chaud)
    "roche_claire": "#CDC5B4",
    "roche_fonce": "#8F8576",
    "roche_mousse": "#8DB05A",
    "os": "#EADFC4",               # rocher du crâne (ivoire)
    "os_clair": "#F5EEDB",
    "os_fonce": "#CDBF9E",
    "os_ombre": "#A99B7C",
    "grotte": "#3A3346",           # orbites, bouche, intérieur des grottes
    "os_fissure": "#7E7266",       # fissures du crâne (modelé)
    "dent": "#FBF6EA",             # dents du crâne, plus claires que le visage
    "gres": "#C49A6C",             # falaises de grès chaud autour du crâne
    "gres_clair": "#D8B98A",
    "gres_fonce": "#9C7650",
    "gres_mouille": "#7A5A3E",     # pied des falaises, à la ligne d'eau

    # --- Animaux ---------------------------------------------------------------------------------
    "vache_blanc": "#FAFAF5",
    "vache_noir": "#2A2A2E",
    "vache_rose": "#F2A7A7",
    "corne": "#EFE6CF",
    "foin": "#E9C85C",
    "foin_fonce": "#CFA941",
    "crabe": "#E8503A",
    "mouette": "#F7F7F2",
    "mouette_gris": "#B9C2CC",
    "bec": "#F5B530",

    # --- Métal, lumière, divers -------------------------------------------------------------
    "metal": "#6F7680",
    "metal_fonce": "#3F444C",
    "fer": "#4A4F57",
    "laiton": "#C9A24A",
    "lanterne": "#FFD27A",         # verre éclairé (Neon)
    "flamme": "#FFB24D",
    "drapeau_noir": "#1E1E22",
    "tete_mort": "#F4F1E8",

    # --- Étals --------------------------------------------------------------------------------
    "pomme": "#E0412F",
    "banane": "#F7D84A",
    "pasteque": "#3E9A3A",
    "pasteque_chair": "#F2545B",
    "raisin": "#7E4FB0",
    "poisson": "#8FB7C9",
    "poisson_fonce": "#5E8AA3",
    "viande": "#A8552E",           # viande sur l'os
    "viande_fonce": "#7A3B1E",
    "viande_claire": "#C9703F",
    "os_viande": "#F4EBD9",
    "glace": "#DDF3F8",
}


def c(name: str) -> tuple:
    return hexrgb(P[name])


def vary(name_or_rgb, rng, amount: float = 0.06) -> tuple:
    """Légère variation de luminosité, pour casser les aplats."""
    base = c(name_or_rgb) if isinstance(name_or_rgb, str) else name_or_rgb
    f = 1 + float(rng.uniform(-amount, amount))
    return shade(base, f)


__all__ = ["P", "c", "vary", "mix", "shade"]
