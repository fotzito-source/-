#!/usr/bin/env python3
"""Rendus Blender et exports de la zone Jujutsu Kaisen.

À lancer avec le Python qui contient `bpy` (Blender 5.2 en module) ou via Blender :
    python rendu.py                          # zone.py → build/parts.json → rendus/*.png + exports
    python rendu.py --vues entree,aerienne   # seulement certaines vues
    python rendu.py --rapide                 # petites images, peu d'échantillons (contrôle)
    python rendu.py --sans-rendu             # exports seulement
    blender -b -P rendu.py -- --vues plan

Exports : export/ZoneJujutsuKaisen.blend (scène Blender), export/ZoneJujutsuKaisen.glb (maillages, couleurs
par sommet), puis export/ZoneJujutsuKaisen.rbxmx et export/ZoneJujutsuKaisen-demo.rbxl via Lune si disponible.
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
    "aerienne": ((230, 250, 150), (0, 0, -250), 50),
    "entree": ((0, 9, 30), (0, 27, -160), 72),          # devant le viaduc, la rue commerçante en enfilade
    "rue": ((6, 8, -24), (0, 22, -200), 70),             # rue commerçante, passerelle 1 au fond
    "tours": ((-6, 8, -158), (0, 34, -330), 70),         # quartier des tours et des écrans
    "approche": ((-10, 9, -262), (12, 32, -400), 72),    # tour cylindrique, immeuble à écrans, carrefour
    "place": ((44, 52, -322), (0, 0, -412), 64),         # vue plongeante sur le carrefour « scramble »
    "retour": ((-4, 9, -470), (0, 16, 0), 70),           # retour vers la base, depuis l'incident
    "cote": ((-320, 180, -60), (0, 10, -260), 45),
    "final": ((0, 10, -414), (0, 44, -496), 74),         # l'immeuble effondré en arche, la sortie, les dômes
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
    ap.add_argument("--vues", default="aerienne,entree,rue,tours,approche,place,retour,cote,final,plan")
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
        # soleil bas derrière la montagne, ciel violet : les lanternes (Neon) ressortent
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
                cam = bs.add_camera("plan", (0, 900, -232), (0, 0, -232.01), fov=30)
                cam.data.type = "ORTHO"
                cam.data.ortho_scale = 580
                cam.data.clip_end = 2000
                bs.render(cam, out / f"{name}{args.suffixe}.png", res=(h * 9 // 10, int(h * 1.1)), samples=max(8, samples // 3))
            else:
                pos, tgt, fov = VUES[name]
                cam = bs.add_camera(name, pos, tgt, fov=fov)
                bs.render(cam, out / f"{name}{args.suffixe}.png", res=(w, h), samples=samples)
            bpy.data.objects.remove(cam, do_unlink=True)
            print(f"vue {name} : {time.time() - t0:.0f} s")

    if not args.sans_export:
        exp = HERE / "export"
        exp.mkdir(exist_ok=True)
        bs.export(blend=exp / "ZoneJujutsuKaisen.blend", glb=exp / "ZoneJujutsuKaisen.glb")
        lune = lune_path()
        if lune:
            r = subprocess.run([lune, "run", str(HERE / "roblox_export.luau"), "--", str(pj), str(exp)],
                               capture_output=True, text=True)
            print(r.stdout.strip() or r.stderr.strip())
        else:
            print("Lune introuvable : export Roblox ignoré (voir README).")


if __name__ == "__main__":
    main()
