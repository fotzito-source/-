#!/usr/bin/env python3
"""Rendus Blender et exports de la zone Attaque des Titans.

À lancer avec le Python qui contient `bpy` (Blender 5.2 en module) ou via Blender :
    python rendu.py                          # zone.py → build/parts.json → rendus/*.png + exports
    python rendu.py --vues entree,aerienne   # seulement certaines vues
    python rendu.py --rapide                 # petites images, peu d'échantillons (contrôle)
    python rendu.py --sans-rendu             # exports seulement
    blender -b -P rendu.py -- --vues plan

Exports : export/ZoneAttaqueDesTitans.blend (scène Blender), export/ZoneAttaqueDesTitans.glb (maillages, couleurs
par sommet), puis export/ZoneAttaqueDesTitans.rbxmx et export/ZoneAttaqueDesTitans-demo.rbxl via Lune si disponible.
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
    "aerienne": ((-240, 340, 120), (10, 0, -285), 48),     # de haut, côté soleil : la ville au-dessus du rempart gauche
    "entree": ((0, 6, 7), (0, 40, -72), 80),             # vue joueur : chemin, prairie, muraille et porte colossale entières
    "prairie": ((-40, 9, 6), (70, 30, -50), 74),          # 3/4 sur la prairie : moulin, ferme, muraille et tunnel
    "rue": ((10, 9, -92), (0, 22, -300), 70),             # place de la porte → rue des colombages
    "eglise": ((24, 10, -192), (-56, 34, -252), 66),       # église et clocher à gauche, mât de fête
    "canal": ((40, 24, -262), (72, 0, -380), 64),          # le canal, ses ponts et la rive droite, vus du trottoir
    "place": ((-20, 12, -398), (70, 32, -462), 72),        # grand-place des œufs : cadran, beffroi, muraille intérieure
    "oeufs": ((30, 10, -420), (0, 6, -470), 66),          # fontaine de la place des œufs
    "retour": ((-4, 9, -470), (0, 22, -60), 70),           # vers la base : la rue et la muraille d'entrée
    "cote": ((-380, 260, -80), (0, 10, -300), 45),         # rempart gauche et champs ; la ville du canal par-dessus
    "final": ((0, 14, -398), (0, 64, -548), 68),           # muraille intérieure et tunnel de sortie
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
    ap.add_argument("--vues", default="aerienne,entree,prairie,rue,eglise,canal,place,oeufs,retour,cote,final,plan")
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
        # soleil bas derrière la muraille, ciel violet : les lanternes (Neon) ressortent
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
                cam = bs.add_camera("plan", (0, 420, -270), (0, 0, -270.01), fov=30)   # basse : moins de brume
                cam.data.type = "ORTHO"
                cam.data.ortho_scale = 600
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
        bs.export(blend=exp / "ZoneAttaqueDesTitans.blend", glb=exp / "ZoneAttaqueDesTitans.glb")
        lune = lune_path()
        if lune:
            r = subprocess.run([lune, "run", str(HERE / "roblox_export.luau"), "--", str(pj), str(exp)],
                               capture_output=True, text=True)
            print(r.stdout.strip() or r.stderr.strip())
        else:
            print("Lune introuvable : export Roblox ignoré (voir README).")


if __name__ == "__main__":
    main()
