#!/usr/bin/env python3
"""Rendus Blender et exports de la zone Black Clover.

À lancer avec le Python qui contient `bpy` (Blender 5.2 en module) ou via Blender :
    python rendu.py                          # zone.py → build/parts.json → rendus/*.png + exports
    python rendu.py --vues entree,aerienne   # seulement certaines vues
    python rendu.py --rapide                 # petites images, peu d'échantillons (contrôle)
    python rendu.py --sans-rendu             # exports seulement
    blender -b -P rendu.py -- --vues plan

Exports : export/ZoneBlackClover.blend (scène Blender), export/ZoneBlackClover.glb (maillages, couleurs
par sommet), puis export/ZoneBlackClover.rbxmx et export/ZoneBlackClover-demo.rbxl via Lune si disponible.
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

# Vues : (position caméra, cible, champ vertical en degrés), en coordonnées Roblox.
# On court vers -Z ; le soleil de jour vient de -X/+Z (derrière l'entrée, à gauche) : la droite du couloir et le crâne
# (qui regarde l'entrée) sont éclairés de face.
VUES = {
    "aerienne": ((-250, 330, 150), (10, 0, -290), 48),      # de haut, côté soleil : crâne, tour, aqueduc, château
    "entree": ((0, 6, 34), (6, 30, -150), 76),             # vue joueur aux abords : les deux tours encadrent le crâne et le château
    "village": ((-10, 9, -44), (30, 30, -200), 70),        # rue du village, église à gauche, colline et crâne à droite
    "crane": ((6, 10, -66), (130, 64, -158), 62),          # le crâne cornu de 3/4 depuis le couloir, côtes géantes devant
    "tour": ((34, 10, -196), (-92, 64, -252), 64),         # tour aux grimoires et sa nuée de livres, placette, bourg
    "bataille": ((-24, 9, -292), (16, 34, -420), 72),      # champ de bataille : ruines, bâtons, cratères, aqueduc
    "place": ((-36, 30, -394), (8, 4, -462), 64),          # cercle magique, obélisques, racines, arbre et îlots
    "retour": ((4, 9, -486), (0, 26, -60), 70),            # vers la base : aqueduc, tour, crâne, tours d'entrée
    "cote": ((-400, 250, -110), (0, 10, -300), 45),        # côté gauche : forêt, montagne de la capitale, falaises
    "final": ((0, 12, -412), (0, 66, -548), 70),           # château démoniaque et sa porte en arc brisé
    "plan": None,  # vue de dessus orthographique
}

# Crépuscule démoniaque : horizon cramoisi-rose, ciel violet, zénith presque noir ; soleil bas derrière le château
CIEL_DEMON = ((0.66, 0.30, 0.40), (0.30, 0.17, 0.42), (0.04, 0.03, 0.12))


def lune_path() -> str | None:
    for cand in (os.environ.get("LUNE"), shutil.which("lune"),
                 "/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/tools/lune/lune"):
        if cand and Path(cand).exists():
            return cand
    return None


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--vues", default="aerienne,entree,village,crane,tour,bataille,place,retour,cote,final,plan")
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
    # rendus de contrôle sans export : fichier propre au processus (plusieurs rendus peuvent tourner en parallèle)
    pj = build / ("parts.json" if not args.sans_export else f"parts-{os.getpid()}.json")
    b.save_json(pj, meta=zone.meta())
    attente = sorted({p.name for p in b.parts if p.name.startswith("ATTENTE_")})
    gene = zone.couloir_libre(b)
    print(json.dumps({"pieces": len(b.parts), "en_attente": attente, "couloir_encombre": len(gene)}, ensure_ascii=False))

    bs.reset_scene()
    st = bs.build(pj)
    print(json.dumps({k: v for k, v in st.items() if k != "tris_by_object"}))
    if args.ambiance == "crepuscule":
        # soleil bas derrière le château (azimut 8 : un peu à droite), ciel violet et cramoisi : le château se
        # découpe en silhouette, les lueurs magiques, les braseros et les fenêtres (Neon) ressortent
        bs.setup_world(sun_elev=9, sun_azim=8, view="AgX", look="AgX - Punchy", exposure=1.0,
                       ciel=CIEL_DEMON, soleil=(1.0, 0.52, 0.44), soleil_energie=3.4, ciel_force=1.5)
        bs.setup_brume(debut=60, profondeur=850, maximum=0.55, couleur=(0.32, 0.20, 0.42))
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
                cam = bs.add_camera("plan", (0, 420, -254), (0, 0, -254.01), fov=30)   # basse : moins de brume
                cam.data.type = "ORTHO"
                cam.data.ortho_scale = 640
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
        bs.export(blend=exp / "ZoneBlackClover.blend", glb=exp / "ZoneBlackClover.glb")
        lune = lune_path()
        if lune:
            r = subprocess.run([lune, "run", str(HERE / "roblox_export.luau"), "--", str(pj), str(exp)],
                               capture_output=True, text=True)
            print(r.stdout.strip() or r.stderr.strip())
        else:
            print("Lune introuvable : export Roblox ignoré (voir README).")


if __name__ == "__main__":
    main()
