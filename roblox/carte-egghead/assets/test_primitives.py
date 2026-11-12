"""Vitrine de test du kit : toutes les primitives et tous les assemblages arrondis, en petit (≈ 90 × 50 studs).

    python apercu.py assets.test_primitives:vitrine --res 1200x675 --samples 12

Sert à vérifier le rendu Blender et l'export Roblox des formes (ellipsoïdes = SpecialMesh, anneaux Neon, dômes de
verre, tubes, cônes rayés, capsule flottante, œuf). Les couleurs sont celles d'un jouet en plastique, en attendant
la palette de la carte. Origine au centre de la vitrine, au sol ; avant = -Z.
"""

from __future__ import annotations

from kit import VERRE, rot_x, rot_z

BLANC = "#F2F4F8"
ROUGE = "#E8423F"
JAUNE = "#FFC93C"
CYAN = "#3DE8FF"
ROSE = "#FF7EB6"
VIOLET = "#8C6CFF"
ORANGE = "#FF8A3D"
MENTHE = "#6FE3B5"
MARINE = "#2E3A59"


def vitrine(b, variant: int = 0):
    """Neuf îlots de démonstration, sur deux rangs (z = -18 devant, z = +14 derrière). 235 pièces."""
    accent = (CYAN, ROSE, JAUNE)[variant % 3]

    # 1. Primitives de base : bloc (studs), coin (pente stud), coin retourné, cylindre, boule, bloc tourné, panneau
    with b.at((-38, 0, -18), group="Primitives"):
        b.box((-6, 0, -5), (6, 1, 5), BLANC, studs="top")
        b.wedge((-6, 0, -9), (6, 1, -5), BLANC, down="-z", studs="top")
        mur = b.box((-6, 1, 3), (6, 6, 4.5), MARINE)
        mur.label = {"face": "Front", "text": "KIT 01", "color": (240, 244, 250), "font": "rond"}
        b.wedge_under((-2, 4, 4.5), (2, 5, 6.1), ORANGE, down="+z")             # console au dos du mur
        b.box((-2.5, 5, 4.5), (2.5, 5.4, 6.3), ORANGE, studs="top")
        b.cyl((-4, 2.5, -2.5), 1.4, 3, ROUGE, axis="y", studs="top")
        b.ball((3.5, 2.6, -2.5), 1.6, JAUNE)
        b.boxc((0, 1.75, -3), (2.6, 1.5, 1.6), accent, yaw=30)
        b.part("block", (0.6, 6, 0.6), (4.5 + 3 * 0.342, 6 + 3 * 0.94, 3.75), rot_z(-20), BLANC, name="Antenne")
        b.bloc_entre((-13, 0, 0), (-6, 1, 0), 3, 0.6, BLANC, studs="top")       # rampe stud
        b.cyl_entre((-13, 1.8, -1.4), (-6, 2.8, -1.4), 0.15, MARINE)           # main courante…
        for x in (-12.4, -6.6):                                                # … sur deux potelets
            y_rampe = (x + 13) / 7 + 0.3
            b.cyl_entre((x, y_rampe - 0.1, -1.4), (x, 1.8 + (x + 13) / 7, -1.4), 0.1, MARINE, collide=False)

    # 2. Cône rayé en étages sur un disque stud, anneau Neon au pied
    with b.at((-20, 0, -18), group="ConeRaye"):
        b.disque((0, 0.3, 0), 6, 0.6, BLANC, studs="top")
        b.cone_etage((0, 0.6, 0), 5, 0.4, 16, [ROUGE, BLANC], etages=8, pointe=JAUNE)
        b.anneau((0, 0.95, 0), 5.25, 0.6, CYAN, 24, material="Neon")

    # 3. Dôme opaque sur tambour (rebord stud), bague Neon, flèche
    with b.at((0, 0, -18), group="Dome"):
        d = b.dome((0, 5, 0), 7, 6, BLANC, tambour=5, couleur_tambour=ROSE, studs_tambour="top")
        b.anneau((0, 2.5, 0), 7.1, 0.6, CYAN, 28, material="Neon", collide=False)
        b.cone_etage(d.info["sommet"], 0.7, 0.15, 3.5, [JAUNE, BLANC], etages=4, pointe=(ROUGE, 0.35))

    # 4. Dôme de verre sur plateau stud, cœur lumineux dedans
    with b.at((20, 0, -18), group="DomeVerre"):
        b.disque((0, 0.5, 0), 7.5, 1.0, BLANC, studs="top")
        b.dome((0, 1, 0), 7.5, 6.5, VERRE, material="Glass", transparency=0.4)
        b.cyl((0, 1.75, 0), 0.5, 1.5, BLANC, axis="y")
        b.ball((0, 3.6, 0), 1.6, ROSE, material="Neon")
        b.anneau((0, 3.6, 0), 2.8, 0.25, JAUNE, 16, rot=rot_x(70), material="Neon", collide=False)

    # 5. Œuf sur socle, anneau incliné autour
    with b.at((40, 0, -18), group="Oeuf"):
        b.disque((0, 0.4, 0), 5.5, 0.8, MARINE, studs="top")
        o = b.oeuf((0, 0.8, 0), 4, 11, BLANC, ventre=0.38, enfonce=0.6)
        b.anneau((0, 6, 0), 6.4, 0.6, ROSE, 24, rot=rot_x(18) @ rot_z(10), material="Neon", collide=False)
        b.ball(o.info["sommet"], 0.5, ROUGE)

    # 6. Tubes entre deux tours : tube de verre à colliers et cœur Neon ; en bas, tube creux à bagues creuses
    #    (forme seulement : un couloir praticable demande rayon ≥ 4, voir OUTILS.md)
    with b.at((-30, 0, 14), group="Tubes"):
        b.cyl((-12, 7, 0), 3, 14, BLANC, axis="y", studs="top")
        b.cyl((12, 5, 0), 3, 10, MENTHE, axis="y", studs="top")
        b.dome((-12, 14, 0), 3, 2.5, ROUGE)
        b.dome((12, 10, 0), 3, 2.5, ROUGE)
        b.tube((-9, 10.5, 0), (9, 8, 0), 1.3, colliers=3, coeur=CYAN)
        b.tube((-9, 2.2, 0), (9, 2.2, 0), 2.2, creux=10, colliers=2)

    # 7. Capsule en lévitation (coque, bulle de verre, ceinture, halo, faisceau, socle)
    with b.at((2, 0, 16), group="Capsule"):
        b.boule_flottante((0, 9, 0), 4, ORANGE, ceinture=BLANC)

    # 8. Arches (anneaux verticaux partiels) et rondelle percée autour d'une colonne
    with b.at((20, 0, 14), group="Arches"):
        b.anneau((0, 0, -2), 6, 1.0, CYAN, 20, axe="z", arc=180, material="Neon")
        b.anneau((0, 0, 2), 6, 1.0, [BLANC, ROUGE], 20, axe="z", arc=180, section="carre")
        b.cyl((0, 4, 7), 1.2, 8, BLANC, axis="y", studs="top")
        b.disque((0, 5, 7), 3.5, 0.4, ROSE, rayon_int=1.2, n=16)

    # 9. Ellipsoïdes : lampe Neon aplatie, ellipsoïde incliné, bosse aplatie au sol, bulles de verre
    with b.at((38, 0, 14), group="Ellipsoides"):
        b.cyl((0, 3, 0), 0.4, 6, BLANC, axis="y")
        b.ellipsoid((0, 6.6, 0), (4, 1.4, 4), JAUNE, material="Neon")
        b.ellipsoid((5, 2.7, 3), (3, 6, 2), VIOLET, rot=rot_z(25) @ rot_x(10))
        b.ellipsoid((-4, 0, 4), (6, 3, 6), MENTHE)
        for i, (x, y, z, r) in enumerate(((-4, 3.4, 4, 1.0), (-3.2, 4.8, 3.4, 0.7), (-4.6, 5.7, 4.6, 0.5))):
            b.ellipsoid((x, y, z), (2 * r, 2 * r * 1.1, 2 * r), VERRE, material="Glass", transparency=0.35,
                        collide=False)

    return {"emprise": (96, 52), "hauteur": 17}
