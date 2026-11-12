"""Banc d'aperçu d'un asset isolé, sur un petit sol stud.

Usage (avec le Python qui contient bpy) :
    python apercu.py assets.exemple:kiosque --variant 1
    python apercu.py assets.test_primitives:vitrine --res 1200x675 --samples 12
    python apercu.py assets.labo:dome --cam "60,30,80" --target-pt "0,15,0" --dossier /tmp/apercus

Écrit <dossier>/<module>-<fonction>-v<variant>-{a,b,…}.png (par défaut dans apercus/) et affiche le nombre de
pièces, la boîte englobante, le nombre de triangles et les contrôles du kit (kit.controles).
Sans --cam : vue A en 3/4 avant (l'avant d'un asset regarde -Z), vue B en 3/4 arrière, plus haute.
Plusieurs caméras dans la même scène : --cam "x,y,z;x,y,z" --target-pt "x,y,z;x,y,z" (images -a, -b, -c…).
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import blender_scene as bs  # noqa: E402
from kit import Builder, bornes, controles  # noqa: E402
from textures import write_stud_textures  # noqa: E402

SOL_APERCU = "#5DBB63"   # vert franc du sol stud des aperçus (--sol pour en changer)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="module:fonction, ex. assets.exemple:kiosque")
    ap.add_argument("--variant", type=int, default=0)
    ap.add_argument("--params", default="{}", help="paramètres JSON passés à la fonction")
    ap.add_argument("--cam", default=None,
                    help="caméra(s) Roblox « x,y,z » ou « x,y,z;x,y,z;… » (sinon deux vues automatiques)")
    ap.add_argument("--target-pt", dest="target_pt", default=None,
                    help="point visé « x,y,z », ou un par caméra séparés par « ; »")
    ap.add_argument("--fov", type=float, default=50.0, help="champ vertical en degrés")
    ap.add_argument("--res", default="960x540")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--no-ground", action="store_true")
    ap.add_argument("--sol", default=SOL_APERCU, help="couleur du sol stud (#RRGGBB)")
    ap.add_argument("--dossier", default=None, help="dossier des images (par défaut apercus/)")
    ap.add_argument("--out", default=None, help="nom de base des images")
    args = ap.parse_args([a for a in sys.argv[1:] if a != "--"] if "--" not in sys.argv else sys.argv[sys.argv.index("--") + 1:])

    write_stud_textures()
    mod_name, fn_name = args.target.split(":")
    fn = getattr(importlib.import_module(mod_name), fn_name)
    b = Builder(seed=11 + args.variant)
    with b.group("Asset"):
        info = fn(b, variant=args.variant, **json.loads(args.params)) or {}
    n_asset = len(b.parts)
    ctl = controles(b.parts)
    lo, hi = bornes(b.parts)
    if not args.no_ground:
        with b.group("Sol"):
            pad = 24
            x0, z0 = np.floor(lo[0] - pad), np.floor(lo[2] - pad)
            x1, z1 = np.ceil(hi[0] + pad), np.ceil(hi[2] + pad)
            b.box((x0, -1, z0), (x1, 0, z1), args.sol, studs="top")
    out_dir = Path(args.dossier) if args.dossier else HERE / "apercus"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.out or f"{mod_name.split('.')[-1]}-{fn_name}-v{args.variant}"
    pj = out_dir / f"{stem}.json"
    b.save_json(pj, meta={"nom": "Apercu"})

    bs.reset_scene()
    st = bs.build(pj)
    bs.setup_world()
    ctr = (lo + hi) / 2
    ext = float(np.max(hi - lo))
    w, h = (int(v) for v in args.res.split("x"))
    def points(txt):
        return [tuple(float(v) for v in t.split(",")) for t in txt.split(";") if t.strip()]

    if args.cam:
        cams = points(args.cam)
    else:
        # vue A : 3/4 avant (l'avant d'un asset regarde -Z) ; vue B : 3/4 arrière, plus haute
        cams = [(ctr[0] - ext * 0.75, ctr[1] + ext * 0.45, ctr[2] - ext * 1.05),
                (ctr[0] + ext * 0.9, ctr[1] + ext * 0.8, ctr[2] + ext * 0.8)]
    tgts = points(args.target_pt) if args.target_pt else [(ctr[0], ctr[1] * 0.8, ctr[2])]
    assert len(tgts) in (1, len(cams)), "--target-pt : un point, ou un par caméra"
    t0 = time.time()
    images = []
    for i, cp in enumerate(cams):
        tgt = tgts[i if len(tgts) > 1 else 0]
        cam = bs.add_camera(f"cam{i}", cp, tgt, fov=args.fov)
        img = out_dir / f"{stem}-{'abcdefghijklmnopqrstuvwxyz'[i]}.png"
        bs.render(cam, img, res=(w, h), samples=args.samples)
        images.append(str(img))
    pj.unlink(missing_ok=True)

    def _json(v):
        return v if isinstance(v, (str, int, float, bool, type(None), list, dict, tuple)) else str(v)

    print(json.dumps({
        "pieces_asset": n_asset,
        "bbox_min": [round(float(v), 2) for v in lo], "bbox_max": [round(float(v), 2) for v in hi],
        "triangles": st["tris"], "info": {k: _json(v) for k, v in dict(info).items()},
        "controles": {k: v for k, v in ctl.items() if k != "pieces"},
        "images": images,
        "secondes": round(time.time() - t0, 1),
    }, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
