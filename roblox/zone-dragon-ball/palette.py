"""Palette de la zone Dragon Ball (campagne terrestre, terres de combat, planète extraterrestre), version « stud ».

Trois paysages se suivent dans la même course, chacun avec sa famille de couleurs :
- la **campagne terrestre** : herbe vert vif, falaises orange en strates, maisons-dômes blanches à bandes
  colorées, palmiers, toits de temple en tuiles vernissées orange et piliers laqués rouges ;
- les **terres de combat** : plaine verte trouée de terre kaki et ocre, mesas aux flancs violets
  couronnées d'herbe, cratères et rochers ;
- la **planète extraterrestre** : herbe bleu-vert, eau turquoise, îlots aux bords de sable ocre, arbres
  « boules » bleu-vert, dômes blancs aux hublots verts, vaisseau blanc et lavande, bancs de nuages dorés.

Le ciel du jeu reste bleu : le rose-magenta et le doré des ciels de la série passent par les nuages, les
strates de roche et quelques accents. Couleurs franches et saturées, pas de gris sale.
Interdits de couleur (propriété intellectuelle) : pas de sphère orange (ni lampe, ni fruit, ni pommeau),
pas d'étoile rouge, pas de combinaison « tenue orange et bleue » sur un objet en forme de personnage.

Les noms servent dans tous les modules d'assets ; `vary()` casse les grands aplats.
"""

from __future__ import annotations

from kit import hexrgb, mix, shade

P = {
    # ---------------------------------------------------------------- Sol de la campagne terrestre
    "herbe": "#62BE45",            # herbe vert vif (un peu jaune, pas émeraude)
    "herbe_claire": "#84D35A",
    "herbe_fonce": "#4AA03A",
    "herbe_ombre": "#3A8432",
    "dalle": "#EDE4CC",            # route du village : dalles crème
    "dalle_fonce": "#DCD0B2",
    "bordure": "#C9BC9C",          # bordure de trottoir
    "pave": "#D9774A",             # trottoirs en pavés terre cuite
    "pave_clair": "#E8986A",
    "pave_fonce": "#B95E38",
    "terre": "#B5814E",            # chemins de terre
    "terre_fonce": "#94653B",

    # ---------------------------------------------------------------- Terres de combat
    "kaki": "#BCA96A",             # terre nue kaki
    "kaki_clair": "#D3C186",
    "kaki_fonce": "#9C8A50",
    "ocre": "#D6A65A",
    "ocre_fonce": "#B38440",
    "fissure": "#6E5A36",          # fissures et terre brûlée
    "brule": "#5A4A3A",            # fond de cratère
    "gravats": "#A89D88",

    # ---------------------------------------------------------------- Planète extraterrestre
    "herbe_alien": "#3DB39B",      # herbe bleu-vert (sarcelle)
    "herbe_alien_claire": "#5FCCB2",
    "herbe_alien_fonce": "#2B9384",
    "sable": "#E8D096",            # bords d'îles et allée de sable clair
    "sable_clair": "#F3E2B4",
    "sable_fonce": "#CDAE6C",
    "eau": "#35C3D2",              # eau turquoise
    "eau_claire": "#7DE2EA",
    "eau_fonce": "#2399AE",
    "ecume": "#F2FCFF",

    # ---------------------------------------------------------------- Falaises et roches
    # Falaises orange en strates de la campagne (la référence actuelle, en mieux)
    "falaise_orange": "#E58B3A",
    "falaise_orange_claire": "#F2A85A",
    "falaise_orange_fonce": "#C06E2C",
    "falaise_brune": "#8E5530",
    # Mesas des terres de combat : flancs violets, strates rose-lavande
    "mesa_violet": "#8A5CC8",
    "mesa_violet_clair": "#A57FDC",
    "mesa_violet_fonce": "#6B45A8",
    "mesa_nuit": "#53358A",
    "mesa_rose": "#C27FCB",        # strate rose : rappel des ciels magenta
    # Falaises de sable ocre de la planète extraterrestre
    "falaise_sable": "#D7B06E",
    "falaise_sable_claire": "#EACB8C",
    "falaise_sable_fonce": "#B18B4E",
    # Rochers isolés
    "rocher": "#A8A2A0",
    "rocher_clair": "#C4BEBA",
    "rocher_fonce": "#7F7876",

    # ---------------------------------------------------------------- Maisons-dômes (rétro-futuristes)
    "blanc_dome": "#F5F5F1",
    "blanc_ombre": "#DDDFE4",
    "gris_tech": "#A9B1BB",
    "gris_tech_fonce": "#6C7581",
    "bande_orange": "#F28C28",     # bandes colorées autour des dômes
    "bande_bleue": "#3C7BE0",
    "bande_rouge": "#E0453A",
    "bande_jaune": "#F6C83C",
    "bande_turquoise": "#2DBFC2",
    "bande_violette": "#8E6BE8",
    "vitre": "#5CB6E6",            # fenêtres rondes
    "vitre_fonce": "#2F6E9E",
    "vitre_lumiere": "#C4F3FF",    # fenêtres éclairées (Neon)
    "vitre_verte": "#86DDA8",      # hublots verts des dômes extraterrestres
    "porte": "#3F86D8",

    # ---------------------------------------------------------------- Temple d'arts martiaux
    "tuile_orange": "#F0892A",     # tuiles vernissées orange
    "tuile_orange_claire": "#FFAF4E",
    "tuile_orange_fonce": "#C96A18",
    "tuile_verte": "#3E9E7C",      # tuiles vernissées vertes (accent rare, jamais dominant)
    "laque_rouge": "#D2392D",      # piliers et poutres laqués
    "laque_rouge_fonce": "#A62A22",
    "enduit": "#F6F0E2",           # murs blancs du temple
    "enduit_creme": "#EADCC0",
    "pierre": "#D0CABC",           # pierre claire (marches, socles)
    "pierre_claire": "#E3DED2",
    "pierre_fonce": "#AAA393",
    "arene": "#D9D9D3",            # dalles de l'arène d'arts martiaux
    "arene_fonce": "#BDBDB5",
    "arene_joint": "#93938A",
    "or": "#F2C230",
    "or_fonce": "#C99A1E",
    "bronze": "#B07A3A",
    "bois": "#8A5A32",
    "bois_fonce": "#5E3B22",
    "bois_clair": "#B98552",
    "banniere_rouge": "#D9372C",
    "banniere_jaune": "#F7C93A",
    "banniere_blanche": "#F8F4EA",
    "banniere_bleue": "#2F64C8",
    "encre": "#2A1E1A",

    # ---------------------------------------------------------------- Végétation
    "palmier_tronc": "#A97B48",
    "palmier_tronc_clair": "#C49660",
    "palmier_tronc_fonce": "#83603A",
    "palme": "#4DB848",
    "palme_claire": "#78D45C",
    "palme_fonce": "#379A3A",
    "noix_coco": "#6B4A2A",
    "feuillage": "#58BE47",        # arbres ronds de la campagne
    "feuillage_clair": "#7FD660",
    "feuillage_fonce": "#3E9C3A",
    "tronc": "#7A5434",
    "boule_alien": "#36AE9E",      # arbres « boules » bleu-vert
    "boule_alien_claire": "#5CCDB9",
    "boule_alien_fonce": "#24887E",
    "tronc_alien": "#A7957A",      # troncs fins pâles
    "tronc_alien_fonce": "#7F6E58",
    "buisson": "#3F9E3C",
    "buisson_alien": "#2C8F86",
    "fleur_rose": "#F27BC0",
    "fleur_jaune": "#FFD84A",

    # ---------------------------------------------------------------- Nuages dorés et ciel
    "nuage_or": "#FFD24A",
    "nuage_or_clair": "#FFE68C",
    "nuage_creme": "#FFF5CF",
    "nuage_ombre": "#F2B23C",
    "nuage_orange": "#EE9C3A",
    "rose_ciel": "#F06AB8",        # accents magenta (strates, fleurs, fanions)
    "rose_pale": "#F7A9D6",

    # ---------------------------------------------------------------- Vaisseau
    "coque": "#F2F0EA",
    "coque_ombre": "#CCC9D6",
    "coque_lavande": "#9C88E0",
    "coque_violet": "#6E58C2",
    "hublot": "#2E2A55",

    # ---------------------------------------------------------------- Détails
    "noir": "#222226",
    "blanc": "#FAFAF7",
    "rouge": "#E0403A",
    "jaune": "#FFD23F",
    "bleu": "#3C7BE0",
    "metal": "#A7B0B8",
    "metal_fonce": "#5E666E",
    "neon_blanc": "#F2FFFF",       # lampes (Neon)
    "neon_cyan": "#8CF0FF",
    "flamme": "#FF9E2C",           # flammes des braseros (blocs, jamais une boule)
    "flamme_coeur": "#FFE27A",
}


def c(name: str) -> tuple:
    return hexrgb(P[name])


def vary(name_or_rgb, rng, amount: float = 0.06) -> tuple:
    """Légère variation de luminosité, pour casser les aplats."""
    base = c(name_or_rgb) if isinstance(name_or_rgb, str) else name_or_rgb
    f = 1 + float(rng.uniform(-amount, amount))
    return shade(base, f)


__all__ = ["P", "c", "vary", "mix", "shade"]
