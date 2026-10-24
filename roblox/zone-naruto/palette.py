"""Palette de la zone Naruto (Konoha), version « stud » : couleurs franches, peu de gris.

Les noms servent dans tous les modules d'assets ; `vary()` donne de petites variations
de teinte pour éviter les grands aplats identiques (comme les murs « pixel » de la référence).
"""

from __future__ import annotations

from kit import hexrgb, mix, shade

P = {
    # Sol
    "sable": "#E6D2A2",          # terre battue de la rue principale
    "sable_fonce": "#D6BC85",
    "pave": "#C9C0AE",           # dallage de pierre
    "pave_fonce": "#AFA591",
    "bordure": "#9C9383",
    "herbe": "#78C043",          # herbe stud vive (référence « an egg »)
    "herbe_fonce": "#5FA735",
    "herbe_claire": "#93D35A",
    "terre": "#A87A4C",
    "eau": "#4FB6E0",
    "eau_fonce": "#3A95C4",

    # Murs
    "enduit": "#F3EEE2",         # blanc cassé des maisons
    "creme": "#EED9B0",
    "jaune_pale": "#F0D58C",
    "saumon": "#DE9470",         # façade terre cuite (rue de Konoha)
    "bleu_pale": "#A8C8DE",
    "vert_pale": "#B5CFA8",
    "rose_pale": "#E9B9A8",
    "rouge_hokage": "#C9473B",

    # Bois et structure
    "bois_fonce": "#5E3B24",
    "bois": "#875736",
    "bois_clair": "#C08A57",
    "poutre": "#6E4529",

    # Toits
    "toit_rouge": "#C94A36",
    "toit_orange": "#E5813A",
    "toit_vert": "#5E9F63",      # cuivre patiné, très Konoha
    "toit_vert_fonce": "#467F4E",
    "toit_bleu": "#3D73B8",
    "toit_bleu_clair": "#5A93D1",
    "toit_ardoise": "#5D6A7A",
    "toit_brun": "#8B4E2F",

    # Détails
    "fenetre": "#2E4A5C",        # vitre sombre
    "fenetre_claire": "#8FC3DE",
    "metal": "#A3ADB3",
    "metal_fonce": "#6F7980",
    "citerne": "#D3D7D9",
    "tuyau": "#9AA4AA",
    "noir": "#262626",
    "blanc": "#FAFAF5",
    "rouge": "#D63A2F",
    "rouge_fonce": "#A82A24",
    "orange_lampion": "#FFB24D",
    "jaune_lampion": "#FFD86B",
    "noren_bleu": "#2F4F8C",
    "noren_rouge": "#B8352C",
    "panneau": "#F4E6C8",

    # Falaise des Hokage
    "roche": "#C99A62",
    "roche_claire": "#DDB47E",
    "roche_fonce": "#A97A45",
    "roche_ombre": "#8E6239",

    # Végétation
    "feuille": "#4FA23A",
    "feuille_claire": "#6CBF45",
    "feuille_fonce": "#3A8530",
    "sakura": "#F5A9C4",
    "sakura_clair": "#FAC8DA",
    "sakura_fonce": "#E487AA",
    "tronc": "#7A5232",

    # Porte et remparts de Konoha
    "rempart": "#DDA56B",        # enduit orangé du mur d'enceinte
    "rempart_fonce": "#C88E55",
    "rempart_tuile": "#7D8F6A",  # tuiles vert-de-gris du chaperon
    "porte_vert": "#A9D3AE",     # vantaux vert pâle
    "porte_vert_fonce": "#88B990",
    "lettre_rouge": "#C8322B",
}


def c(name: str) -> tuple:
    return hexrgb(P[name])


def vary(name_or_rgb, rng, amount: float = 0.06) -> tuple:
    """Légère variation de luminosité, pour casser les aplats."""
    base = c(name_or_rgb) if isinstance(name_or_rgb, str) else name_or_rgb
    f = 1 + float(rng.uniform(-amount, amount))
    return shade(base, f)


__all__ = ["P", "c", "vary", "mix", "shade"]
