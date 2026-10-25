#!/usr/bin/env python3
"""Rendus Blender et exports de la zone My Hero Academia.

À lancer avec le Python qui contient `bpy` (Blender 5.2 en module) ou via Blender :
    python rendu.py                          # zone.py → build/parts.json → rendus/*.png + exports
    python rendu.py --vues entree,aerienne   # seulement certaines vues
    python rendu.py --rapide                 # petites images, peu d'échantillons (contrôle)
    python rendu.py --sans-rendu             # exports seulement
    blender -b -P rendu.py -- --vues plan

Exports : export/ZoneMyHeroAcademia.blend (scène Blender), export/ZoneMyHeroAcademia.glb (maillages, couleurs
par sommet), puis export/ZoneMyHeroAcademia.rbxmx et export/ZoneMyHeroAcademia-demo.rbxl via Lune si disponible.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import blender_scene as bs  # noqa: E402
import zone  # noqa: E402
from textures import write_stud_textures  # noqa: E402

# Vues : (position caméra, cible, champ vertical en degrés), en coordonnées Roblox
VUES = {
    "aerienne": ((-215, 300, 150), (10, 0, -285), 46),  # depuis le côté ensoleillé (-X, +Z)
    "entree": ((0, 9, 40), (0, 26, -150), 72),         # rue de la ville sous le viaduc, portail au bout
    "ville": ((10, 8, -40), (0, 24, -150), 70),         # boutiques, rue latérale, grand portail de sécurité
    "campus": ((6, 8, -150), (0, 34, -420), 70),        # avenue du campus, dortoirs, tours au fond
    "avenue": ((-30, 8, -146), (-38, 26, -300), 72),    # cadrage de la référence 2 : dortoirs, conifères, tours
    "terrains": ((0, 10, -292), (0, 20, -400), 82),     # dôme à droite, ville factice à gauche, stade et tours
    "place": ((20, 12, -416), (0, 30, -540), 72),       # arène du stade, place des œufs, tours derrière
    "retour": ((-4, 9, -500), (0, 18, 0), 70),          # demi-tour vers la base
    "cote": ((-300, 360, -170), (10, 0, -330), 44),      # au-dessus de la ville lointaine
    "tours": ((20, 96, -430), (0, 110, -560), 72),       # repère final vu du haut du stade, au-dessus du portique
    "plan": None,  # vue de dessus orthographique
}


def lune_path() -> str | None:
    for cand in (os.environ.get("LUNE"), shutil.which("lune"),
                 "/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/tools/lune/lune"):
        if cand and Path(cand).exists():
            return cand
    return None


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--vues", default="aerienne,entree,ville,campus,avenue,terrains,place,retour,cote,tours,plan")
    ap.add_argument("--rapide", action="store_true")
    ap.add_argument("--sans-rendu", action="store_true")
    ap.add_argument("--sans-export", action="store_true")
    ap.add_argument("--echantillons", type=int, default=48)
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--ambiance", choices=("jour", "crepuscule"), default="jour",
                    help="crepuscule : rendus bonus au soleil couchant (le jeu, lui, garde son éclairage)")
    ap.add_argument("--suffixe", default="", help="ajouté au nom des images (ex. --suffixe=-crepuscule)")
    args = ap.parse_args(argv)

    write_stud_textures()
    b = zone.build_zone()
    build = HERE / "build"
    build.mkdir(exist_ok=True)
    pj = build / "parts.json"
    b.save_json(pj, meta=zone.meta())
    attente = sorted({p.name for p in b.parts if p.name.startswith("ATTENTE_")})
    gene = zone.couloir_libre(b)
    print(json.dumps({"pieces": len(b.parts), "en_attente": attente, "couloir_encombre": len(gene)}, ensure_ascii=False))

    bs.reset_scene()
    st = bs.build(pj)
    print(json.dumps({k: v for k, v in st.items() if k != "tris_by_object"}))
    if args.ambiance == "crepuscule":
        # soleil bas côté entrée (les façades principales, tournées vers +Z, sont éclairées), ciel orangé et violet (références 1 et 2) : les néons ressortent
        bs.setup_world(sun_elev=11, sun_azim=190, view="AgX", look="AgX - Punchy", exposure=1.0,
                       ciel=bs.CIEL_CREPUSCULE, soleil=(1.0, 0.62, 0.42), soleil_energie=3.6, ciel_force=1.5)
        bs.setup_brume(debut=60, profondeur=900, maximum=0.5, couleur=(0.36, 0.26, 0.48))
    else:
        bs.setup_world()
        bs.setup_brume()

    out = HERE / "rendus"
    out.mkdir(exist_ok=True)
    w, h = (int(v) for v in args.res.split("x"))
    if args.rapide:
        w, h, samples = w // 2, h // 2, 12
    else:
        samples = args.echantillons
    if not args.sans_rendu:
        import bpy
        for name in [v for v in args.vues.split(",") if v]:
            t0 = time.time()
            if VUES[name] is None:
                cam = bs.add_camera("plan", (0, 900, -277), (0, 0, -277.01), fov=30)
                cam.data.type = "ORTHO"
                cam.data.ortho_scale = 640
                cam.data.clip_end = 2000
                # pas de brume sur le plan : le sol est à 900 de la caméra, tout serait voilé
                ms = bpy.context.scene.world.mist_settings
                debut = ms.start
                ms.start = 740
                bs.render(cam, out / f"{name}{args.suffixe}.png", res=(h * 9 // 10, int(h * 1.1)), samples=max(8, samples // 3))
                ms.start = debut
            else:
                pos, tgt, fov = VUES[name]
                cam = bs.add_camera(name, pos, tgt, fov=fov)
                bs.render(cam, out / f"{name}{args.suffixe}.png", res=(w, h), samples=samples)
            bpy.data.objects.remove(cam, do_unlink=True)
            print(f"vue {name} : {time.time() - t0:.0f} s")

    if not args.sans_export:
        exp = HERE / "export"
        exp.mkdir(exist_ok=True)
        bs.export(blend=exp / "ZoneMyHeroAcademia.blend", glb=exp / "ZoneMyHeroAcademia.glb")
        lune = lune_path()
        if lune:
            r = subprocess.run([lune, "run", str(HERE / "roblox_export.luau"), "--", str(pj), str(exp)],
                               capture_output=True, text=True)
            print(r.stdout.strip() or r.stderr.strip())
        else:
            print("Lune introuvable : export Roblox ignoré (voir README).")


if __name__ == "__main__":
    main()
