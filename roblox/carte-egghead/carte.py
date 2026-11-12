#!/usr/bin/env python3
"""Plan de la carte « île du futur » (CarteEgghead) — ÉBAUCHE DE L'ATELIER OUTILS, à remplacer par la conception.

Interface attendue par rendu.py (à garder telle quelle en remplaçant l'ébauche) :
- `build_carte(seed=7) -> Builder` : toute la carte, pivot = origine = centre de la carte au niveau du sol (y = 0) ;
- `meta() -> dict` : au moins {"nom": "CarteEgghead", "version": …} (nom du modèle et des fichiers exportés) ;
- `verifications(b) -> dict` : contrôles affichés par rendu.py et par `python carte.py` ;
- `VUES` (facultatif) : {nom: ((x, y, z) caméra, (x, y, z) cible, champ vertical en degrés)}, ajoutées aux vues
  de rendu.py (aerienne, plan, joueur) ou qui les remplacent.

L'ébauche pose un sol stud de 200 × 200 (16 dalles de 50, rangées en blocs de 64 pour le streaming), la vitrine
de test des formes au centre (assets/test_primitives.py) et le repère « Spawn » au sud, tourné vers la vitrine.

    python carte.py                     # build/parts.json + vérifications
    python carte.py --stats             # + pièces par groupe
    python carte.py --export DOSSIER    # + export Roblox avec Lune (.rbxm, .rbxmx, -demo.rbxl), sans Blender
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from assets import test_primitives  # noqa: E402
from kit import GROUPE_REPERES, Builder, bornes, bornes_part, controles, exporter_roblox  # noqa: E402

NOM = "CarteEgghead"
VERSION = "0.1-ebauche-outils"
DEMI_COTE = 100                    # sol de 200 × 200 studs, centré sur l'origine
DALLE = 50                         # dalles de sol (tailles entières : studs alignés d'une dalle à l'autre)
EPAISSEUR_SOL = 2
SOL = ("#5DBB63", "#55B35B")       # deux verts voisins en damier (provisoire : la palette viendra de la conception)
BUDGET_PIECES = 20000              # plafond indicatif pour une carte en streaming (voir OUTILS.md)

# Vues propres à la carte (facultatif) : nom → (caméra, cible, champ vertical). rendu.py calcule déjà aerienne,
# plan et joueur à partir de l'emprise et du repère Spawn.
VUES = {
    "vitrine": ((-30, 34, -78), (2, 3, -2), 42),
}


def sol(b: Builder) -> None:
    """Sol stud : dalles jointives, dessus à y = 0, studs intégrés sur le dessus (Plastic + SurfaceType.Studs)."""
    with b.group("Sol"):
        n = 2 * DEMI_COTE // DALLE
        for i in range(n):
            for j in range(n):
                x0, z0 = -DEMI_COTE + i * DALLE, -DEMI_COTE + j * DALLE
                b.box((x0, -EPAISSEUR_SOL, z0), (x0 + DALLE, 0, z0 + DALLE), SOL[(i + j) % 2], studs="top",
                      name="Dalle")


def vitrine(b: Builder) -> None:
    with b.at((0, 0, 0), group="Vitrine"):
        test_primitives.vitrine(b)


def reperes(b: Builder) -> None:
    """Repères invisibles du jeu (dossier Reperes). Spawn : au sud, regard vers -Z (la vitrine)."""
    b.repere("Spawn", (0, 0, 62), taille=(8, 1, 8), yaw=0)


def build_carte(seed: int = 7) -> Builder:
    b = Builder(seed=seed)
    sol(b)
    vitrine(b)
    reperes(b)
    b.decouper(("Sol",), taille=64)
    return b


def meta() -> dict:
    return {"nom": NOM, "version": VERSION}


def verifications(b: Builder) -> dict:
    """Contrôles de la carte : les listes de « problemes » doivent rester vides."""
    ctl = controles(b.parts)
    sol_parts = [p for p in b.parts if p.group == "Sol" or p.group.startswith("Sol/")]
    aire = sum(p.size[0] * p.size[2] for p in sol_parts)
    spawn = [p for p in b.parts if p.group == GROUPE_REPERES and p.name == "Spawn"]
    hors_sol = []
    for p in b.parts:
        lo, hi = bornes_part(p)
        if p.transparency < 0.99 and (lo[0] < -DEMI_COTE - 0.01 or hi[0] > DEMI_COTE + 0.01
                                      or lo[2] < -DEMI_COTE - 0.01 or hi[2] > DEMI_COTE + 0.01):
            hors_sol.append((p.name, p.group))
    lo, hi = bornes(b.parts)
    problemes = dict(ctl["problemes"])
    pb_carte = {
        "sol_sans_studs": [p.group for p in sol_parts if "Top" not in p.studs][:10],
        "sol_incomplet": [] if abs(aire - (2 * DEMI_COTE) ** 2) < 1e-6 else [f"aire {aire} au lieu de {(2 * DEMI_COTE) ** 2}"],
        "spawn": [] if len(spawn) == 1 else [f"{len(spawn)} repère(s) Spawn au lieu de 1"],
        "hors_du_sol": hors_sol[:10],
        "hors_budget": [] if len(b.parts) <= BUDGET_PIECES else [f"{len(b.parts)} pièces > {BUDGET_PIECES}"],
    }
    problemes.update({k: v for k, v in pb_carte.items() if v})
    return {
        "pieces": ctl["pieces"],
        "par_forme": ctl["par_forme"],
        "ellipsoides": ctl["par_forme"].get("ellipsoid", 0),
        "neon": ctl["neon"],
        "verre": ctl["verre"],
        "transparentes": ctl["transparentes"],
        "pieces_a_studs": ctl["pieces_a_studs"],
        "sol_dalles": len(sol_parts),
        "reperes": ctl["reperes"],
        "spawn": [round(v, 2) for v in spawn[0].pos] if spawn else None,
        "emprise": {"min": [round(float(v), 2) for v in lo], "max": [round(float(v), 2) for v in hi]},
        "problemes": problemes,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / "build" / "parts.json"))
    ap.add_argument("--stats", action="store_true", help="pièces par groupe racine")
    ap.add_argument("--export", default=None, help="dossier : export Roblox avec Lune (sans Blender)")
    args = ap.parse_args()
    b = build_carte()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    b.save_json(out, meta=meta())
    print(json.dumps({"fichier": str(out), **verifications(b)}, ensure_ascii=False))
    if args.stats:
        for k, v in b.stats().items():
            print(f"{v:6d}  {k}")
    if args.export:
        print(json.dumps(exporter_roblox(out, args.export), ensure_ascii=False))


if __name__ == "__main__":
    main()
