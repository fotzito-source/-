"""Exemple de référence : petit kiosque rond (montre les conventions des assets de la carte).

    python apercu.py assets.exemple:kiosque --variant 1 --res 1200x675 --samples 12

Conventions illustrées : origine au centre de l'emprise au sol (y = 0) ; avant = -Z local (le comptoir et
l'enseigne regardent -Z) ; groupes nommés ; studs sur les dessus praticables ; formes arrondies du kit (disque,
anneau en arc, dôme sur tambour, cône rayé) ; Neon avec mesure ; panneau texte sur un bloc ; budget annoncé.
Les couleurs sont provisoires (constantes ci-dessous) : la palette de la carte les remplacera.
"""

from __future__ import annotations

BLANC = "#F2F4F8"
GRIS_CLAIR = "#C9D1DE"
ROUGE = "#E8423F"
CYAN = "#3DE8FF"
ACCENTS = ("#FF7EB6", "#FFC93C", "#6FE3B5")


def kiosque(b, variant: int = 0, rayon: float = 6.0):
    """Kiosque rond : socle stud, comptoir en arc devant (-Z), colonne, toit en dôme sur tambour, bague Neon,
    antenne rayée, enseigne « INFO ». ≈ 40 pièces. `variant` change la couleur d'accent (0-2)."""
    accent = ACCENTS[variant % 3]
    r = float(rayon)
    with b.group("Socle"):
        b.disque((0, 0.4, 0), r + 1, 0.8, GRIS_CLAIR, studs="top")
    with b.group("Comptoir"):
        # arc de 140° centré sur l'avant (-Z = angle 90 pour un anneau horizontal) ; section « plat » :
        # 3 studs de haut (le long de la normale), 0,8 d'épaisseur (dans le rayon)
        b.anneau((0, 0.8 + 1.5, 0), r - 0.6, 3.0, BLANC, 24, arc=140, depart=20, section="plat", largeur=0.8)
        b.anneau((0, 0.8 + 3.1, 0), r - 0.6, 0.2, accent, 24, arc=140, depart=20, section="plat", largeur=1.2,
                 studs="top")
    with b.group("Colonne"):
        b.cyl((0, 0.8 + 4, 0), 0.8, 8, BLANC, axis="y")
    with b.group("Toit"):
        toit = b.dome((0, 10.8, 0), r + 0.5, 3.2, BLANC, tambour=2.0, couleur_tambour=accent)
        b.anneau((0, 9.2, 0), r + 0.55, 0.35, CYAN, 16, material="Neon", collide=False, shadow=False)
        b.cone_etage(toit.info["sommet"], 0.5, 0.12, 3.0, [ROUGE, BLANC], etages=4, pointe=(ROUGE, 0.3),
                     collide=False)
    with b.group("Enseigne"):
        # panneau à l'avant du tambour (le texte se lit depuis -Z), son dos enfoncé dans le tambour, au-dessus de
        # la bague Neon
        p = b.box((-2.2, 9.45, -(r + 0.95)), (2.2, 10.65, -(r - 0.1)), accent)
        p.label = {"face": "Front", "text": "INFO", "color": (255, 255, 255), "font": "rond"}
    return {"emprise": (2 * (r + 1), 2 * (r + 1)), "hauteur": round(toit.info["sommet"][1] + 3.6, 1)}
