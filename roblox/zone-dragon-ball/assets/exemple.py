"""Exemple de référence : petit kiosque de temple (montre les conventions des assets)."""

from __future__ import annotations

from palette import c, vary


def kiosque(b, variant: int = 0, largeur: int = 10, profondeur: int = 8):
    """Kiosque ouvert : socle de pierre, 4 piliers laqués, toit de tuiles orange à deux pans, plaque 武."""
    rng = b.rng
    w, d = largeur / 2, profondeur / 2
    toit = ("tuile_orange", "tuile_verte", "tuile_orange_fonce")[variant % 3]
    # Socle (studs sur le dessus)
    b.box((-w, 0, -d), (w, 0.8, d), c("pierre"), studs="top")
    # Piliers rouges (avant = -Z)
    for x in (-w + 0.8, w - 0.8):
        for z in (-d + 0.8, d - 0.8):
            b.box((x - 0.5, 0.8, z - 0.5), (x + 0.5, 8, z + 0.5), vary("laque_rouge", rng, 0.04))
    # Linteau, puis toit à deux pans avec studs sur les pentes
    b.box((-w - 0.5, 8, -d - 0.5), (w + 0.5, 8.8, d + 0.5), c("laque_rouge_fonce"))
    b.wedge((-w - 1.2, 8.8, -d - 1.6), (w + 1.2, 11.6, 0), c(toit), down="-z", studs="top")
    b.wedge((-w - 1.2, 8.8, 0), (w + 1.2, 11.6, d + 1.6), c(toit), down="+z", studs="top")
    b.box((-w - 1.4, 11.6, -0.5), (w + 1.4, 12.2, 0.5), c("tuile_orange_fonce"))
    # Plaque à l'avant, texte en SurfaceGui
    p = b.box((-1.6, 6.2, -d - 0.7), (1.6, 8.0, -d - 0.4), c("encre"), collide=False)   # accrochée au linteau
    p.label = {"face": "Front", "text": "武", "color": (242, 194, 48), "font": "brush"}
    return {"emprise": (largeur + 2.4, profondeur + 3.2), "hauteur": 12.2}
