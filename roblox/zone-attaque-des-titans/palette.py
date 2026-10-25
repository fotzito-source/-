"""Palette de la zone Attaque des Titans (ville médiévale européenne entre des murailles colossales), version « stud ».

Ambiance : plein soleil d'été. Prairie vert-jaune fleurie devant la muraille, murailles de pierre beige-gris
pâle (3-4 gris chauds en « pixels »), ville dense et chaleureuse : enduits crème et ocre, colombages brun
sombre ou rouge sang-de-bœuf, toits de tuiles terre cuite et quelques toits d'ardoise, pavés gris chauds,
canal bleu, touches de rouge et de vert (drapeaux, volets, auvents, géraniums).
Pas de vert émeraude dominant : les verts tirent vers le jaune. `vary()` casse les grands aplats ;
`pierre_mur(rng)` tire une des quatre pierres de la muraille.
"""

from __future__ import annotations

from kit import hexrgb, mix, shade

P = {
    # Prairie et campagne (devant la muraille, champs extérieurs)
    "herbe": "#7DB547",            # vert-jaune ensoleillé
    "herbe_claire": "#95C85A",
    "herbe_fonce": "#64A03E",
    "herbe_seche": "#B9BC5E",      # bords de chemin, chaume
    "terre": "#A58259",            # chemin de terre battue
    "terre_claire": "#BE9C70",
    "terre_fonce": "#82633F",
    "fleur_blanche": "#FAF6E6",
    "fleur_jaune": "#F4CF3F",
    "fleur_bleue": "#6F9CE6",
    "fleur_mauve": "#B48ADA",
    "fleur_rouge": "#E0503C",      # coquelicots, géraniums
    "fleur_rose": "#EE8FAE",
    "ble": "#E5C65C",              # champs de blé
    "ble_fonce": "#CDA944",
    "foin": "#E0C068",
    "foin_fonce": "#C4A04A",
    "potager": "#5F9440",

    # Végétation
    "feuille": "#5FA040",
    "feuille_claire": "#80BC52",
    "feuille_fonce": "#477F34",
    "feuille_jaune": "#A9C750",    # reflets de soleil sur les cimes
    "feuille_ombre": "#3A6A2E",
    "tronc": "#6B4B33",
    "tronc_fonce": "#4E3626",
    "tronc_clair": "#8A6648",
    "haie": "#518C3B",
    "pomme": "#D2453A",

    # Murailles colossales (pierre / béton beige-gris pâle, 4 tons pour les « pixels »)
    "mur": "#B9AE9C",              # ton de base
    "mur_clair": "#C5BBA9",
    "mur_pale": "#D0C7B5",         # arêtes éclairées, chaperons
    "mur_fonce": "#A39886",
    "mur_ombre": "#8C826F",        # creux, joints de pilastres, bas de mur
    "mur_joint": "#736A5A",        # joints profonds, embrasures
    "mur_base": "#867C69",         # soubassement taluté
    "mur_mousse": "#8FA05C",       # traînées de mousse au pied (rare)
    "mur_coulure": "#9C927F",      # coulures de pluie sous les gargouilles et les embrasures
    "lierre": "#5C8A3E",           # lierre au pied des remparts et des maisons (petites touches)
    "lierre_clair": "#78A64C",
    "chemin_ronde": "#AFA592",     # dallage du chemin de ronde (studs)
    "bois_echafaud": "#B8955F",    # grues, monte-charges, échafaudages de bois clair

    # Sol de la ville
    "pave": "#807C76",             # pavés gris chaud
    "pave_clair": "#8E8A84",
    "pave_fonce": "#6F6B66",
    "pave_brun": "#A39582",        # pavés ocre des cours et ruelles
    "pave_rouge": "#B08A74",       # pavés terre cuite (motifs de la place)
    "dalle": "#B3AB9A",            # dalles des trottoirs
    "dalle_fonce": "#9C9483",
    "bordure": "#5C5852",          # bordures de trottoir, caniveaux
    "gravier": "#C9BEA6",
    "eau": "#4F8FC2",
    "eau_fonce": "#3C73A2",
    "eau_claire": "#76B0DA",
    "quai": "#B4AA96",             # pierre des quais du canal

    # Maisons à colombages et maisons bourgeoises
    "enduit_creme": "#F1E5C9",
    "enduit_blanc": "#F6F0E3",
    "enduit_ocre": "#E8CB91",
    "enduit_saumon": "#EBC4A8",
    "enduit_jaune": "#F0DA9A",
    "enduit_gris": "#DCD6CA",
    "enduit_bleu": "#CBD6DE",      # bleu très pâle (rare)
    "colombage": "#4A3226",        # bois de colombage brun sombre
    "colombage_brun": "#5E3F2C",
    "colombage_rouge": "#7A3B2A",  # colombage sang-de-bœuf
    "bois": "#6E4B33",
    "bois_moyen": "#875E40",
    "bois_clair": "#A97E54",
    "bois_gris": "#8C7C69",        # bois patiné (granges, moulins)
    "pierre_maison": "#C4B69D",    # pierre de taille des maisons bourgeoises
    "pierre_maison_claire": "#D8CCB4",
    "pierre_brune": "#A8977C",
    "soubassement": "#8F8572",
    "tuile": "#C2603A",            # tuiles terre cuite
    "tuile_claire": "#D47548",
    "tuile_fonce": "#9E4A2D",
    "tuile_brune": "#8C5038",
    "tuile_rouge": "#B4412F",
    "ardoise": "#505A68",          # toits d'ardoise (église, beffroi, quelques maisons)
    "ardoise_fonce": "#3C4350",
    "ardoise_claire": "#66717F",
    "cuivre_vert": "#6FA593",      # flèches et bulbes de cuivre vert-de-gris (clochers, beffroi), en accent
    "cuivre_vert_fonce": "#548474",
    "gres": "#C9B48E",             # grès blond (église, encadrements)
    "gres_fonce": "#AE9774",
    "chaume": "#C9A85E",           # toits de chaume des fermes
    "chaume_fonce": "#A8884A",
    "brique": "#A9573F",           # cheminées
    "brique_fonce": "#87442F",
    "fenetre": "#34475E",          # vitres sombres
    "fenetre_cadre": "#F3EEE2",
    "fenetre_lumiere": "#FFD27A",  # vitres éclairées (Neon, avec parcimonie)
    "vitrail_bleu": "#4A6FB8",
    "vitrail_rouge": "#B8443A",
    "vitrail_or": "#E2B44A",
    "volet_vert": "#56804A",
    "volet_bleu": "#4E6F98",
    "volet_rouge": "#9E3B2E",
    "volet_brun": "#6B4630",
    "porte": "#5A3A26",

    # Tissus, drapeaux, auvents
    "toile_creme": "#EFE5CC",
    "toile_rouge": "#C8453A",
    "toile_verte": "#5E8F52",
    "toile_bleue": "#4F70A3",
    "toile_jaune": "#E7C152",
    "drapeau_rouge": "#C23B2F",
    "drapeau_vert": "#3F7D4C",
    "drapeau_blanc": "#F4EEDF",
    "drapeau_bleu": "#3F5F9A",
    "voile_moulin": "#EEE5D0",     # toile des ailes de moulin

    # Métal, artillerie, accents
    "fonte": "#33373D",            # canons, ferronnerie
    "fer": "#5A6068",
    "metal": "#8E959C",
    "rail": "#6A6E73",
    "laiton": "#C9A24A",
    "bronze": "#9C7A3C",
    "or": "#D9B24A",
    "cloche": "#B08A3E",
    "corde": "#C8B48A",
    "noir": "#26262B",
    "blanc": "#FAF8F2",
    "rouge": "#C9392F",
    "lampe": "#FFD27A",            # verre des lanternes (Neon)
    "lampe_chaude": "#FFB45A",
    "cadran": "#F2EEDC",           # cadran d'horloge
}


def c(name: str) -> tuple:
    return hexrgb(P[name])


def vary(name_or_rgb, rng, amount: float = 0.06) -> tuple:
    """Légère variation de luminosité, pour casser les aplats."""
    base = c(name_or_rgb) if isinstance(name_or_rgb, str) else name_or_rgb
    f = 1 + float(rng.uniform(-amount, amount))
    return shade(base, f)


PIERRES_MUR = ("mur", "mur_clair", "mur_fonce", "mur_pale")
ENDUITS = ("enduit_creme", "enduit_blanc", "enduit_ocre", "enduit_saumon", "enduit_jaune", "enduit_gris")
TUILES = ("tuile", "tuile_claire", "tuile_fonce", "tuile_brune", "tuile_rouge")


def pierre_mur(rng, poids=(0.4, 0.25, 0.25, 0.1)) -> tuple:
    """Une des quatre pierres de la muraille (pixels de 3-4 gris chauds)."""
    return c(PIERRES_MUR[int(rng.choice(len(PIERRES_MUR), p=poids))])


__all__ = ["P", "c", "vary", "mix", "shade", "pierre_mur", "PIERRES_MUR", "ENDUITS", "TUILES"]
