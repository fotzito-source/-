#!/usr/bin/env python3
"""Rendus Blender et exports de la carte (île du futur, style stud).

À lancer avec le Python qui contient `bpy` (Blender 5.2 en module) ou via Blender :
    python rendu.py                              # carte.py → build/parts.json → rendus/*.png + exports
    python rendu.py --vues aerienne,plan         # seulement certaines vues
    python rendu.py --rapide                     # images deux fois plus petites, 12 échantillons (contrôle)
    python rendu.py --sans-rendu                 # exports seulement
    python rendu.py --sans-export --dossier /tmp/controle --res 1200x675 --echantillons 12
    python rendu.py --sans-rendu --export /tmp/essai_export      # exports dans un autre dossier
    blender -b -P rendu.py -- --vues plan

Vues (calculées à partir de l'emprise de la carte, aucune coordonnée à régler) :
- « aerienne » : 3/4 plongeante, depuis le côté du soleil, toute la carte dans le cadre ;
- « plan » : vue de dessus orthographique, cadrée sur l'emprise (le haut de l'image = -Z, l'avant) ;
- « joueur » : PROVISOIRE, caméra à la Roblox (12 studs derrière et 7 au-dessus du repère Spawn, regard vers
  l'avant du repère) ;
- `carte.VUES` (dict nom → (caméra, cible, champ vertical)) ajoute des vues ou remplace celles-ci.

Exports (NOM = carte.meta()["nom"]) : <export>/NOM.blend (scène Blender), NOM.glb (maillages, couleurs par sommet),
puis NOM.rbxm / NOM.rbxmx / NOM-demo.rbxl via Lune (roblox_export.luau, avec relecture et contrôles).
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import blender_scene as bs  # noqa: E402
import carte  # noqa: E402
from kit import GROUPE_REPERES, bornes, exporter_roblox  # noqa: E402
from textures import write_stud_textures  # noqa: E402

PLAN = "plan"   # vue spéciale : dessus orthographique


def vues_par_defaut(b) -> dict:
    """aerienne, joueur et plan, cadrées sur l'emprise des pièces visibles."""
    lo, hi = bornes(b.parts)
    ctr = (lo + hi) / 2
    sol = max(0.0, float(lo[1]))
    rayon = float(np.linalg.norm(hi - lo)) / 2
    fov = 45.0
    # Le soleil vient de -X / +Z (azimut 215 dans blender_scene) : la caméra aérienne se place de ce côté.
    d = np.array([-0.55, 0.62, 0.75])
    d /= np.linalg.norm(d)
    cible = np.array([ctr[0], sol + 0.12 * (hi[1] - sol), ctr[2]])
    pos = cible + d * rayon / math.tan(math.radians(fov / 2)) * 0.76
    vues = {"aerienne": (tuple(pos), tuple(cible), fov)}
    # Vue joueur (provisoire) : caméra Roblox par défaut derrière le personnage posé sur le repère Spawn
    sp = next((p for p in b.parts if p.group == GROUPE_REPERES and p.name == "Spawn"), None)
    if sp is not None:
        R = np.asarray(sp.rot).reshape(3, 3)
        bas = np.asarray(sp.pos) - R[:, 1] * sp.size[1] / 2
        avant = -R[:, 2]
    else:
        bas = np.array([ctr[0], 0.0, hi[2] - 10])
        avant = np.array([0.0, 0.0, -1.0])
    avant = np.array([avant[0], 0.0, avant[2]])
    avant /= max(np.linalg.norm(avant), 1e-9)
    vues["joueur"] = (tuple(bas - avant * 12 + (0, 7, 0)), tuple(bas + avant * 40 + (0, 5, 0)), 70.0)
    vues[PLAN] = PLAN
    return vues


def rendre_plan(b, chemin: Path, hauteur_px: int, samples: int):
    """Dessus orthographique : image au rapport de l'emprise (X en largeur, Z en hauteur), -Z en haut."""
    lo, hi = bornes(b.parts)
    ctr = (lo + hi) / 2
    wx, wz = max(hi[0] - lo[0], 1.0), max(hi[2] - lo[2], 1.0)
    rapport = float(np.clip(wx / wz, 0.4, 2.5))
    res = (int(round(hauteur_px * rapport)), int(hauteur_px))
    marge = 1.04
    if res[0] >= res[1]:
        echelle = max(wx * marge, wz * marge * res[0] / res[1])
    else:
        echelle = max(wz * marge, wx * marge * res[1] / res[0])
    haut = float(hi[1]) + 60
    cam = bs.add_camera(PLAN, (ctr[0], haut, ctr[2]), (ctr[0], 0, ctr[2] - 0.01), fov=30)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = echelle
    cam.data.clip_end = haut - float(lo[1]) + 100
    bs.render(cam, chemin, res=res, samples=samples)
    return cam


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vues", default=None, help="liste séparée par des virgules (par défaut : toutes)")
    ap.add_argument("--rapide", action="store_true")
    ap.add_argument("--sans-rendu", action="store_true")
    ap.add_argument("--sans-export", action="store_true")
    ap.add_argument("--echantillons", type=int, default=48)
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--ambiance", choices=("jour", "crepuscule"), default="jour",
                    help="jour : plein soleil tropical (comme le jeu) ; crepuscule : rendus bonus au soleil couchant")
    ap.add_argument("--suffixe", default="", help="ajouté au nom des images (ex. --suffixe=-crepuscule)")
    ap.add_argument("--dossier", default=None, help="dossier des images (par défaut rendus/)")
    ap.add_argument("--export", dest="dossier_export", default=None, help="dossier des exports (par défaut export/)")
    args = ap.parse_args(argv)

    write_stud_textures()
    b = carte.build_carte()
    meta = carte.meta()
    nom = meta.get("nom") or "CarteEgghead"
    if args.sans_export:
        # rendus de contrôle sans export : dossier temporaire propre au processus (plusieurs rendus peuvent tourner
        # en parallèle, et rien n'est laissé dans le projet)
        tmp = Path(tempfile.mkdtemp(prefix="carte-rendu-"))
        pj = tmp / "parts.json"
    else:
        build = HERE / "build"
        build.mkdir(exist_ok=True)
        pj = build / "parts.json"
    b.save_json(pj, meta=meta)
    print(json.dumps({"carte": nom, "verifications": carte.verifications(b)}, ensure_ascii=False, default=str))

    vues = vues_par_defaut(b)
    vues.update(getattr(carte, "VUES", {}) or {})
    noms = [v for v in (args.vues.split(",") if args.vues else list(vues)) if v]
    inconnues = [v for v in noms if v not in vues]
    if inconnues:
        sys.exit(f"vues inconnues : {inconnues} (connues : {sorted(vues)})")

    bs.reset_scene()
    st = bs.build(pj)
    print(json.dumps({k: v for k, v in st.items() if k != "tris_by_object"}))
    lo, hi = bornes(b.parts)
    rayon = float(np.linalg.norm(hi - lo)) / 2
    if args.ambiance == "crepuscule":
        # soleil bas à l'ouest (azimut 250), ciel orangé et rose : silhouettes, Neon qui ressortent
        bs.setup_world(sun_elev=10, sun_azim=250, exposure=0.0, ciel=bs.CIEL_CREPUSCULE, soleil=(1.0, 0.62, 0.38),
                       soleil_energie=3.6, ciel_force=1.4)
        bs.setup_brume(debut=max(80.0, rayon * 0.6), profondeur=1000, maximum=0.35, couleur=(0.78, 0.50, 0.42))
    else:
        bs.setup_world()
        bs.setup_brume(debut=max(150.0, rayon * 1.1), profondeur=1400, maximum=0.30, couleur=bs.CIEL_JOUR[0])

    out = Path(args.dossier) if args.dossier else HERE / "rendus"
    w, h = (int(v) for v in args.res.split("x"))
    samples = args.echantillons
    if args.rapide:
        w, h, samples = w // 2, h // 2, 12
    if not args.sans_rendu:
        import bpy
        import plan as _plan
        out.mkdir(parents=True, exist_ok=True)
        for name in noms:
            t0 = time.time()
            chemin = out / f"{name}{args.suffixe}.png"
            if vues[name] == PLAN:
                cam = rendre_plan(b, chemin, h, max(8, samples // 2))
            else:
                pos, tgt, fov = vues[name]
                cam = bs.add_camera(name, pos, tgt, fov=fov)
                # résolution propre à la vue (plan.RESOLUTIONS : captures au format des captures de l'utilisateur),
                # moitié en --rapide, sauf si --res est donné
                rv = getattr(_plan, "RESOLUTIONS", {}).get(name) if args.res == "1920x1080" else None
                wv, hv = (rv[0] // 2, rv[1] // 2) if (rv and args.rapide) else (rv if rv else (w, h))
                bs.render(cam, chemin, res=(wv, hv), samples=samples)
            bpy.data.objects.remove(cam, do_unlink=True)
            print(f"vue {name} : {time.time() - t0:.0f} s → {chemin}")

    if args.sans_export:
        shutil.rmtree(pj.parent, ignore_errors=True)
    else:
        exp = Path(args.dossier_export) if args.dossier_export else HERE / "export"
        exp.mkdir(parents=True, exist_ok=True)
        bs.export(blend=exp / f"{nom}.blend", glb=exp / f"{nom}.glb")
        try:
            print(json.dumps(exporter_roblox(pj, exp), ensure_ascii=False))
        except RuntimeError as e:
            sys.exit(str(e))


if __name__ == "__main__":
    main()
