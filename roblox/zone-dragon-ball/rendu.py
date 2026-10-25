#!/usr/bin/env python3
"""Rendus Blender et exports de la zone Dragon Ball.

À lancer avec le Python qui contient `bpy` (Blender 5.2 en module) ou via Blender :
    python rendu.py                          # zone.py → build/parts.json → rendus/*.png + exports
    python rendu.py --vues entree,aerienne   # seulement certaines vues
    python rendu.py --rapide                 # petites images, peu d'échantillons (contrôle)
    python rendu.py --sans-rendu             # exports seulement
    blender -b -P rendu.py -- --vues plan

Exports : export/ZoneDragonBall.blend (scène Blender), export/ZoneDragonBall.glb (maillages, couleurs
par sommet), puis export/ZoneDragonBall.rbxmx et export/ZoneDragonBall-demo.rbxl via Lune si disponible.
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
    "aerienne": ((236, 236, 136), (0, 0, -232), 46),      # toute la zone en 3/4
    "entree": ((0, 10, 46), (0, 30, -60), 80),             # porte de temple et rue, vue joueur (sol de l'approche)
    "village": ((0, 26, 10), (0, 10, -120), 62),           # rue des grands dômes (couloir de 90)
    "friche": ((6, 14, -140), (0, 30, -300), 74),          # terres de combat, mesas, pont de roche
    "alien": ((46, 9, -278), (108, 4, -322), 72),          # planète : lac, îlots, arbres boules, dômes
    "vaisseau": ((-34, 10, -342), (-96, 13, -310), 70),     # planète : vaisseau rond, canal, passerelles
    "place": ((22, 11, -334), (0, 34, -470), 72),          # arène des œufs, temple, tribunes, arche au fond
    "retour": ((-6, 9, -426), (0, 14, 0), 70),             # demi-tour avec l'œuf
    "cote": ((-150, 150, 60), (10, 0, -250), 50),          # vue de côté au-dessus des crêtes
    "arche": ((0, 58, -348), (0, 48, -452), 66),           # arche finale et nuages dorés
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
    ap.add_argument("--vues", default="aerienne,entree,village,friche,alien,vaisseau,place,retour,cote,arche,plan")
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
    # rendus de contrôle sans export : fichier propre au processus (plusieurs équipes rendent en parallèle)
    pj = build / ("parts.json" if not args.sans_export else f"parts-{os.getpid()}.json")
    b.save_json(pj, meta=zone.meta())
    attente = sorted({p.name for p in b.parts if p.name.startswith("ATTENTE_")})
    gene = zone.couloir_libre(b)
    print(json.dumps({"pieces": len(b.parts), "en_attente": attente, "couloir_encombre": len(gene)}, ensure_ascii=False))

    bs.reset_scene()
    st = bs.build(pj)
    print(json.dumps({k: v for k, v in st.items() if k != "tris_by_object"}))
    if args.ambiance == "crepuscule":
        # soleil bas derrière l'arche, ciel violet : lampes et braseros (Neon) ressortent
        bs.setup_world(sun_elev=11, sun_azim=20, view="AgX", look="AgX - Punchy", exposure=1.0,
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
                cam = bs.add_camera("plan", (0, 900, -211), (0, 0, -211.01), fov=30)
                cam.data.type = "ORTHO"
                cam.data.ortho_scale = 540
                cam.data.clip_end = 2000
                bs.render(cam, out / f"{name}{args.suffixe}.png", res=(h * 9 // 10, int(h * 1.1)), samples=max(8, samples // 3))
            else:
                pos, tgt, fov = VUES[name]
                cam = bs.add_camera(name, pos, tgt, fov=fov)
                bs.render(cam, out / f"{name}{args.suffixe}.png", res=(w, h), samples=samples)
            bpy.data.objects.remove(cam, do_unlink=True)
            print(f"vue {name} : {time.time() - t0:.0f} s")

    if args.sans_export:
        pj.unlink(missing_ok=True)
    else:
        exp = HERE / "export"
        exp.mkdir(exist_ok=True)
        bs.export(blend=exp / "ZoneDragonBall.blend", glb=exp / "ZoneDragonBall.glb")
        lune = lune_path()
        if lune:
            r = subprocess.run([lune, "run", str(HERE / "roblox_export.luau"), "--", str(pj), str(exp)],
                               capture_output=True, text=True)
            print(r.stdout.strip() or r.stderr.strip())
        else:
            print("Lune introuvable : export Roblox ignoré (voir README).")


if __name__ == "__main__":
    main()
