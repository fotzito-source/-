"""Banc d'aperçu d'un asset isolé, sur un petit sol stud.

Usage (avec le Python qui contient bpy) :
    python apercu.py assets.maisons:boutique --variant 1
    python apercu.py assets.porte:build --cam "60,30,80" --target "0,15,0" --res 1200x675

Écrit apercus/<module>-<fonction>-v<variant>-{a,b}.png et affiche le nombre de pièces,
la boîte englobante et le nombre de triangles.
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
from kit import Builder  # noqa: E402
from palette import c  # noqa: E402
from textures import write_stud_textures  # noqa: E402


def bbox(parts):
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    for p in parts:
        R = np.asarray(p.rot).reshape(3, 3)
        half = np.abs(R) @ (np.asarray(p.size) / 2)
        lo = np.minimum(lo, np.asarray(p.pos) - half)
        hi = np.maximum(hi, np.asarray(p.pos) + half)
    return lo, hi


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="module:fonction, ex. assets.maisons:boutique")
    ap.add_argument("--variant", type=int, default=0)
    ap.add_argument("--params", default="{}", help="paramètres JSON passés à la fonction")
    ap.add_argument("--cam", default=None, help="position caméra Roblox x,y,z (sinon automatique)")
    ap.add_argument("--target-pt", dest="target_pt", default=None)
    ap.add_argument("--res", default="960x540")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--no-ground", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args([a for a in sys.argv[1:] if a != "--"] if "--" not in sys.argv else sys.argv[sys.argv.index("--") + 1:])

    write_stud_textures()
    mod_name, fn_name = args.target.split(":")
    fn = getattr(importlib.import_module(mod_name), fn_name)
    b = Builder(seed=11 + args.variant)
    with b.group("Asset"):
        info = fn(b, variant=args.variant, **json.loads(args.params)) or {}
    n_asset = len(b.parts)
    lo, hi = bbox(b.parts)
    if not args.no_ground:
        with b.group("Sol"):
            pad = 24
            b.box((lo[0] - pad, -1, lo[2] - pad), (hi[0] + pad, 0, hi[2] + pad), c("herbe"), studs="top")
    out_dir = HERE / "apercus"
    out_dir.mkdir(exist_ok=True)
    stem = args.out or f"{mod_name.split('.')[-1]}-{fn_name}-v{args.variant}"
    pj = out_dir / f"{stem}.json"
    b.save_json(pj)

    bs.reset_scene()
    st = bs.build(pj)
    bs.setup_world()
    ctr = (lo + hi) / 2
    ext = float(np.max(hi - lo))
    w, h = (int(v) for v in args.res.split("x"))
    if args.cam:
        cams = [tuple(float(v) for v in args.cam.split(","))]
    else:
        # vue A : 3/4 avant (l'avant d'un asset regarde -Z) ; vue B : 3/4 arrière, plus haute
        cams = [(ctr[0] - ext * 0.75, ctr[1] + ext * 0.45, ctr[2] - ext * 1.05),
                (ctr[0] + ext * 0.9, ctr[1] + ext * 0.8, ctr[2] + ext * 0.8)]
    tgt = tuple(float(v) for v in args.target_pt.split(",")) if args.target_pt else (ctr[0], ctr[1] * 0.8, ctr[2])
    t0 = time.time()
    for i, cp in enumerate(cams):
        cam = bs.add_camera(f"cam{i}", cp, tgt, fov=50)
        bs.render(cam, out_dir / f"{stem}-{'ab'[i]}.png", res=(w, h), samples=args.samples)
    pj.unlink(missing_ok=True)
    print(json.dumps({
        "pieces_asset": n_asset,
        "bbox_min": [round(v, 2) for v in lo], "bbox_max": [round(v, 2) for v in hi],
        "triangles": st["tris"], "info": info,
        "images": [str(out_dir / f"{stem}-{'ab'[i]}.png") for i in range(len(cams))],
        "secondes": round(time.time() - t0, 1),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
