"""Exemple de référence : petite cabane de pêcheur (montre les conventions des assets de la zone)."""

from __future__ import annotations

from palette import c, vary


def cabane_peche(b, variant: int = 0, largeur: int = 10, profondeur: int = 8):
    """Cabane de planches sur un plancher : porte à l'avant (-Z), toit à deux pans studdé, auvent rayé, bouée."""
    rng = b.rng
    w, d = largeur / 2, profondeur / 2
    toit = ("toit_rouge", "toit_bleu", "toit_turquoise")[variant % 3]
    # Plancher et murs de planches (bandes de teintes proches)
    b.box((-w, 0, -d), (w, 0.6, d), c("bois_fonce"), studs="top")
    for i in range(4):
        y0 = 0.6 + i * 1.6
        b.box((-w + 0.4, y0, -d + 0.4), (w - 0.4, y0 + 1.6, d - 0.4), vary("bois_flotte", rng, 0.07))
    # Porte et fenêtre (dépassent de 0,1)
    b.box((-1.2, 0.6, -d + 0.3), (1.2, 4.6, -d + 0.4), c("bois_fonce"))
    b.box((w - 3.4, 3.2, -d + 0.3), (w - 1.4, 5.0, -d + 0.4), c("vitre"))
    # Toit à deux pans (pentes vers -Z et +Z) avec studs sur les pentes
    b.box((-w - 0.6, 7.0, -d - 0.8), (w + 0.6, 7.4, d + 0.8), c("bois_fonce"))
    b.wedge((-w - 0.6, 7.4, -d - 0.8), (w + 0.6, 10.0, 0), c(toit), down="-z", studs="top")
    b.wedge((-w - 0.6, 7.4, 0), (w + 0.6, 10.0, d + 0.8), c(toit), down="+z", studs="top")
    # Auvent rayé rouge et blanc au-dessus de la porte
    for i in range(4):
        x0 = -2.4 + i * 1.2
        b.wedge((x0, 5.2, -d - 1.6), (x0 + 1.2, 6.0, -d + 0.4), c("toile_rouge") if i % 2 == 0 else c("blanc"),
                down="-z", collide=False)
    # Bouée accrochée au mur
    from assets.mobilier import bouee
    with b.at((-w + 2.2, 2.0, -d + 0.3)):
        bouee(b, variant=1, rayon=0.9)
    return {"emprise": (largeur + 1.2, profondeur + 2.4), "hauteur": 10.0}
