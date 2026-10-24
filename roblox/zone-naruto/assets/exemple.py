"""Exemple de référence : petit stand de dango (montre les conventions des assets)."""

from __future__ import annotations

from palette import c, vary


def stand_dango(b, variant: int = 0, largeur: int = 12, profondeur: int = 8):
    """Stand ouvert : comptoir, 4 poteaux, toit à deux pans stud, rideau noren, lampions."""
    rng = b.rng
    w, d = largeur / 2, profondeur / 2
    toit = ("toit_rouge", "toit_vert", "toit_orange")[variant % 3]
    # Socle et plancher
    b.box((-w, 0, -d), (w, 0.6, d), c("bois_fonce"), studs="top")
    # Comptoir à l'avant (avant = -Z)
    b.box((-w + 0.5, 0.6, -d + 0.5), (w - 0.5, 3.6, -d + 2), vary("bois", rng))
    b.box((-w + 0.2, 3.6, -d + 0.2), (w - 0.2, 4.0, -d + 2.3), c("bois_clair"), studs="top")
    # Poteaux
    for x in (-w + 0.5, w - 0.5):
        for z in (-d + 0.5, d - 0.5):
            b.box((x - 0.5, 0.6, z - 0.5), (x + 0.5, 9, z + 0.5), c("poutre"))
    # Mur du fond
    b.box((-w + 1, 0.6, d - 1), (w - 1, 9, d - 0.4), vary("enduit", rng))
    # Toit à deux pans (pentes vers -Z et +Z) avec studs sur les pentes
    b.box((-w - 1, 9, -d - 1.5), (w + 1, 9.6, d + 1.5), c("poutre"))
    b.wedge((-w - 1, 9.6, -d - 1.5), (w + 1, 12.6, 0), c(toit), down="-z", studs="top")
    b.wedge((-w - 1, 9.6, 0), (w + 1, 12.6, d + 1.5), c(toit), down="+z", studs="top")
    b.box((-w - 1.2, 12.6, -0.6), (w + 1.2, 13.2, 0.6), c("bois_fonce"))
    # Noren (rideau) sous l'avant-toit, en 3 lés, avec enseigne texte
    for i in range(3):
        x0 = -w + 1.5 + i * (largeur - 3) / 3
        p = b.box((x0 + 0.1, 6.6, -d - 0.2), (x0 + (largeur - 3) / 3 - 0.1, 8.8, -d), c("noren_bleu"), collide=False)
        p.label = {"face": "Front", "text": "団子"[i % 2] if i != 1 else "茶", "color": (245, 240, 230), "font": "brush"}
    # Lampions aux coins avant
    for x in (-w - 0.2, w + 0.2):
        b.box((x - 0.15, 7.6, -d - 1.2), (x + 0.15, 8.9, -d - 0.9), c("noir"), collide=False)
        b.cyl((x, 6.6, -d - 1.05), 0.8, 2.0, c("orange_lampion"), axis="y", material="Neon", collide=False)
    return {"emprise": (largeur + 2, profondeur + 3), "hauteur": 13.2}
