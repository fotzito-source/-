"""Palette de la zone Black Clover (royaume de mages aux portes d'un royaume démoniaque), version « stud ».

Ambiance : la zone doit se lire SOMBRE et DÉMONIAQUE en plein jour (l'éclairage Roblox est le même pour tout le
jeu). On l'obtient par la matière, pas par la lumière :
- village des confins : moellons gris-brun, chaume sombre, ardoises violet-gris, herbe olive éteinte, labours
  bruns et blé doré terni ;
- bourg de la tour : pierre gris-violet, colombages noirs sur enduits sourds (gris-violet, ocre foncé, sang-de-bœuf),
  fenêtres éclairées à la bougie ;
- champ de bataille : prairie gris-vert piétinée, cendre, brûlis, ruines de pierre noire ;
- royaume démoniaque : basalte et obsidienne presque noirs, racines noires, cramoisi, violet profond.
Contrastes qui portent la lecture : os ivoire du crâne contre pierre noire ; LUEURS (Neon) violettes, cramoisies,
vert maladif, dorées et feu. Pas de vert émeraude : les verts sont olive, mousse ou gris-vert sapin.
`vary()` casse les grands aplats ; `pierre(rng)`, `moellon(rng)`, `roche(rng)` tirent une pierre parmi 3-4 tons.
"""

from __future__ import annotations

from kit import hexrgb, mix, shade

P = {
    # Herbe et campagne (olive éteint, jamais émeraude)
    "herbe": "#55663E",            # herbe olive sombre (ton de base des bas-côtés)
    "herbe_claire": "#66784A",
    "herbe_fonce": "#43532F",
    "herbe_seche": "#857C4E",      # bords de chemin, chaumes
    "herbe_morte": "#6E6849",
    "herbe_grise": "#55594A",      # prairie brumeuse du champ de bataille
    "mousse": "#4C5E33",
    "terre": "#6A5240",            # chemin de terre
    "terre_claire": "#7E6450",
    "terre_fonce": "#4E3C2E",      # ornières
    "boue": "#463A30",
    "labour": "#6B4934",           # sillons des champs labourés
    "labour_fonce": "#4F3526",
    "labour_clair": "#80593F",
    "ble": "#B8933F",              # blé doré terni (refBC1)
    "ble_clair": "#CDA850",
    "ble_fonce": "#9A7A34",
    "foin": "#A88A48",
    "cendre": "#5A5658",           # cendre du champ de bataille
    "cendre_fonce": "#403D42",
    "brulis": "#2B2628",           # sol calciné des cratères

    # Pavés et dalles du couloir
    "pave": "#5A5560",             # pavés gris-violet
    "pave_clair": "#6C6772",
    "pave_fonce": "#46424D",
    "pave_brun": "#625548",        # pavés usés du village
    "pave_brun_clair": "#736558",
    "dalle": "#4A4652",            # dalles sombres du bourg
    "dalle_claire": "#5C5764",
    "dalle_noire": "#2A2730",      # place rituelle
    "dalle_rituelle": "#221F28",
    "bordure": "#3A3640",          # bordures, caniveaux
    "joint": "#2E2B33",

    # Pierre des tours, murailles et ruines (gris-violet, 4 tons pour les « pixels »)
    "pierre": "#6E6878",
    "pierre_claire": "#827C8C",
    "pierre_pale": "#968FA0",      # arêtes, cordons, chaperons
    "pierre_fonce": "#5A5464",
    "pierre_ombre": "#46404F",     # creux, embrasures, bas de mur
    "pierre_noire": "#34303B",     # ruines calcinées
    "moellon": "#6B635C",          # moellons gris-brun des maisons du village
    "moellon_clair": "#7F766D",
    "moellon_fonce": "#554E48",
    "lierre": "#3E5A34",           # lierre sombre (tours d'entrée, ruines)
    "lierre_clair": "#52703F",

    # Toits
    "ardoise": "#4A4360",          # ardoise violet-gris (dominante des toits)
    "ardoise_claire": "#5D557A",
    "ardoise_fonce": "#363049",
    "ardoise_bleue": "#3E4A62",
    "chaume": "#7C6A45",           # chaume vieilli
    "chaume_fonce": "#5F5034",
    "chaume_clair": "#93804F",
    "tuile_sombre": "#6E3A30",     # tuiles brun-rouge éteint (rare)

    # Bois
    "bois": "#5A4030",
    "bois_clair": "#76573F",
    "bois_fonce": "#3C2B22",
    "bois_noir": "#2A211C",        # colombages du bourg
    "bois_gris": "#6E645A",        # bois patiné (granges, clôtures)
    "bois_brule": "#2B2422",       # poutres calcinées des ruines

    # Enduits des maisons hautes du bourg (sourds, jamais pastel)
    "enduit_gris": "#8C8590",
    "enduit_ocre": "#9C8460",
    "enduit_rouge": "#7E4A44",
    "enduit_vert": "#5E6B58",
    "enduit_creme": "#B4A88E",     # crème sali (avec parcimonie)

    # Fenêtres, vitraux et lumières
    "fenetre": "#24212B",          # vitre sombre
    "fenetre_cadre": "#4A3C33",
    "lueur_bougie": "#FFB85C",     # fenêtre éclairée (Neon)
    "lueur_lanterne": "#FFC86E",   # verre des lanternes (Neon)
    "vitrail_violet": "#7A4BC4",
    "vitrail_rouge": "#A3303E",
    "vitrail_ambre": "#D49A3C",

    # Os du démon (crâne, côtes)
    "os": "#E6DFCB",
    "os_clair": "#F2ECDD",
    "os_ombre": "#C8BEA5",
    "os_fonce": "#A39880",
    "os_brule": "#5C5346",         # os noirci au ras du sol
    "fissure": "#3A332C",          # fissures (saillie de 0,1 au moins)

    # Royaume démoniaque
    "obsidienne": "#1C1922",
    "basalte": "#2A2631",
    "basalte_clair": "#3A3543",
    "roche_noire": "#312C38",
    "roche_violette": "#3E3350",
    "racine": "#241C26",           # racines démoniaques
    "racine_claire": "#38293A",
    "chateau": "#2C2834",          # pierre noire du château
    "chateau_clair": "#3E3948",
    "chateau_arete": "#4E4858",    # arêtes, cordons, merlons
    "cramoisi": "#8E1B2C",
    "cramoisi_fonce": "#5E1220",
    "violet_profond": "#3F2463",
    "violet": "#5E3591",
    "pourpre": "#6E2A6A",

    # Lueurs (toujours en Neon, avec parcimonie : <= ~900 pièces Neon pour toute la zone)
    "lueur_violette": "#B36BFF",
    "lueur_violette_pale": "#D6A8FF",
    "lueur_cramoisie": "#FF2F55",
    "lueur_verte": "#9DFF5C",      # vert maladif (orbes, chaudrons)
    "lueur_doree": "#FFD66B",      # lucioles dorées (refBC2)
    "feu": "#FF8A2B",
    "feu_coeur": "#FFD45E",
    "feu_violet": "#C46BFF",
    "feu_cramoisi": "#FF3B3B",
    "cristal": "#A564FF",
    "cristal_fonce": "#6A35C2",

    # Grimoires (couvertures unies, pages crème)
    "cuir_rouge": "#8C2531",
    "cuir_bleu": "#2E4C8C",
    "cuir_vert": "#3D6A3E",
    "cuir_violet": "#5C2F80",
    "cuir_brun": "#6B4429",
    "cuir_noir": "#2A2430",
    "cuir_or": "#A8822E",
    "page": "#EEE3C6",
    "page_ombre": "#D3C5A2",
    "dorure": "#D6AA45",

    # Végétation
    "sapin": "#2F4636",            # sapins gris-vert très sombres
    "sapin_clair": "#3C5842",
    "sapin_fonce": "#243829",
    "feuille_sombre": "#3F5531",
    "feuille_rouille": "#7A5A2E",  # feuillage roussi (rare)
    "bois_mort": "#4A403B",        # arbres morts
    "bois_mort_clair": "#665A52",
    "epine": "#1F1A21",

    # Tissus (bannières unies ou à liseré, jamais d'emblème)
    "toile_cramoisie": "#8E1F2E",
    "toile_violette": "#4F2A6E",
    "toile_noire": "#25222B",
    "toile_nuit": "#26305A",
    "toile_or": "#B68A2F",
    "toile_grise": "#6C6672",
    "toile_ecru": "#B9AD92",

    # Métal
    "fer": "#4A4C55",
    "fer_fonce": "#2D2F35",
    "acier": "#8C909A",
    "rouille": "#7A4A33",
    "laiton": "#A8843A",
    "or": "#D4A73C",
    "chaine": "#3E4048",

    # Lointain (montagne de la capitale : bleu-violet désaturé, lu comme une silhouette lointaine)
    "lointain": "#7D7F9A",
    "lointain_clair": "#9496AE",
    "lointain_fonce": "#666883",
    "chateau_royal": "#C9C6D2",
    "toit_royal": "#5B6690",

    # Divers
    "eau": "#2F4A66",
    "eau_claire": "#46698A",
    "noir": "#1A181E",
    "blanc": "#EDE8DF",
}


def c(name: str) -> tuple:
    return hexrgb(P[name])


def vary(name_or_rgb, rng, amount: float = 0.06) -> tuple:
    """Légère variation de luminosité, pour casser les aplats."""
    base = c(name_or_rgb) if isinstance(name_or_rgb, str) else name_or_rgb
    f = 1 + float(rng.uniform(-amount, amount))
    return shade(base, f)


PIERRES = ("pierre", "pierre_claire", "pierre_fonce", "pierre_pale")
MOELLONS = ("moellon", "moellon_clair", "moellon_fonce")
ROCHES = ("basalte", "basalte_clair", "roche_noire", "roche_violette")
ARDOISES = ("ardoise", "ardoise_claire", "ardoise_fonce", "ardoise_bleue")
CHAUMES = ("chaume", "chaume_fonce", "chaume_clair")
ENDUITS = ("enduit_gris", "enduit_ocre", "enduit_rouge", "enduit_vert", "enduit_creme")
CUIRS = ("cuir_rouge", "cuir_bleu", "cuir_vert", "cuir_violet", "cuir_brun", "cuir_noir")
LUEURS = ("lueur_violette", "lueur_cramoisie", "lueur_verte", "lueur_doree")
TOILES = ("toile_cramoisie", "toile_violette", "toile_noire", "toile_nuit", "toile_or")


def _tirage(noms, rng, poids=None) -> tuple:
    if poids is None:
        return c(noms[int(rng.integers(len(noms)))])
    return c(noms[int(rng.choice(len(noms), p=poids))])


def pierre(rng, poids=(0.4, 0.25, 0.25, 0.1)) -> tuple:
    """Une des quatre pierres gris-violet (tours, murailles, ruines)."""
    return _tirage(PIERRES, rng, poids)


def moellon(rng) -> tuple:
    """Un des trois moellons gris-brun des maisons du village."""
    return _tirage(MOELLONS, rng, (0.5, 0.25, 0.25))


def roche(rng) -> tuple:
    """Une des quatre roches noires du royaume démoniaque (basalte, roche violette)."""
    return _tirage(ROCHES, rng, (0.35, 0.25, 0.25, 0.15))


def os_teinte(t: float) -> tuple:
    """Os ivoire (t = 0) → os ombré (0,5) → os noirci au ras du sol (1)."""
    t = min(max(t, 0.0), 1.0)
    if t < 0.5:
        return mix(c("os"), c("os_fonce"), t * 2)
    return mix(c("os_fonce"), c("os_brule"), (t - 0.5) * 2)


__all__ = ["P", "c", "vary", "mix", "shade", "pierre", "moellon", "roche", "os_teinte", "PIERRES", "MOELLONS",
           "ROCHES", "ARDOISES", "CHAUMES", "ENDUITS", "CUIRS", "LUEURS", "TOILES"]
