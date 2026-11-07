"""Kit de construction « stud » : la carte est décrite comme une liste de Parts Roblox.

Tout est exprimé dans le repère Roblox (Y vers le haut, 1 unité = 1 stud) et avec les seules
formes que Roblox sait afficher nativement (bloc, coin, cylindre, boule). La même liste sert
ensuite à deux choses :
- `blender_scene.py` la transforme en maillages Blender pour les rendus et le fichier .blend ;
- `roblox_export.luau` (Lune) la transforme en vrai modèle Roblox (.rbxmx / .rbxl).

Conventions Roblox reprises telles quelles :
- WedgePart : face pleine au fond (+Z local), la pente descend vers l'avant (-Z local) ;
- cylindre : l'axe est le X local (Size.X = longueur, Size.Y = Size.Z = diamètre) ;
- CFrame : matrice de rotation dont les colonnes sont les axes X, Y, Z locaux dans le monde.
"""

from __future__ import annotations

import json
import math
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

FACES = ("Top", "Bottom", "Front", "Back", "Left", "Right")
SHAPES = ("block", "wedge", "cyl", "ball")
MATERIALS = (
    "SmoothPlastic", "Plastic", "Wood", "WoodPlanks", "Slate", "Concrete", "Brick",
    "Cobblestone", "Rock", "Sand", "Grass", "Fabric", "Metal", "Neon", "Glass",
)


def rot_x(deg: float) -> np.ndarray:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)


def rot_y(deg: float) -> np.ndarray:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)


def rot_z(deg: float) -> np.ndarray:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)


def _clean(v: float) -> float:
    """Arrondit les erreurs flottantes (0.9999999 → 1) pour garder des tailles « en studs »."""
    r = round(v, 4)
    return 0.0 if r == 0 else r


@dataclass
class Part:
    shape: str
    size: tuple
    pos: tuple
    rot: tuple  # 9 nombres, ligne par ligne (R00 R01 R02 R10 … R22)
    color: tuple  # RGB 0-255
    material: str = "SmoothPlastic"
    studs: tuple = ()  # faces (repère local de la pièce) qui reçoivent la texture stud
    transparency: float = 0.0
    reflectance: float = 0.0
    group: str = ""
    name: str = "Part"
    collide: bool = True
    shadow: bool = True
    label: dict | None = None  # panneau texte : {face, text, color, bg?, font?}
    attrs: dict = field(default_factory=dict)


def hexrgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shade(c, f: float) -> tuple:
    """Assombrit (f < 1) ou éclaircit (f > 1) une couleur."""
    c = hexrgb(c) if isinstance(c, str) else c
    if f <= 1:
        return tuple(int(round(v * f)) for v in c)
    return tuple(int(round(v + (255 - v) * (f - 1))) for v in c)


def mix(a, b, t: float) -> tuple:
    a = hexrgb(a) if isinstance(a, str) else a
    b = hexrgb(b) if isinstance(b, str) else b
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


class Builder:
    """Accumule des Parts, avec une pile de repères (position + rotation autour de Y) et de groupes."""

    def __init__(self, seed: int = 7):
        self.parts: list[Part] = []
        self._R = [np.eye(3)]
        self._t = [np.zeros(3)]
        self._groups = [""]
        self.rng = np.random.default_rng(seed)

    # -- repères et groupes -------------------------------------------------
    @contextmanager
    def at(self, pos=(0, 0, 0), yaw: float = 0.0, group: str | None = None):
        R = self._R[-1] @ rot_y(yaw)
        t = self._R[-1] @ np.asarray(pos, float) + self._t[-1]
        self._R.append(R)
        self._t.append(t)
        if group is not None:
            self._groups.append(self._join(group))
        try:
            yield self
        finally:
            self._R.pop()
            self._t.pop()
            if group is not None:
                self._groups.pop()

    @contextmanager
    def group(self, name: str):
        self._groups.append(self._join(name))
        try:
            yield self
        finally:
            self._groups.pop()

    def _join(self, name: str) -> str:
        cur = self._groups[-1]
        return f"{cur}/{name}" if cur else name

    def to_world(self, p) -> np.ndarray:
        return self._R[-1] @ np.asarray(p, float) + self._t[-1]

    # -- émission -----------------------------------------------------------
    def part(self, shape: str, size, center, rot_local=None, color="#ff00ff", *, studs=(), name=None, **kw) -> Part:
        assert shape in SHAPES, shape
        rot_local = np.eye(3) if rot_local is None else rot_local
        R = self._R[-1] @ rot_local
        p = self._R[-1] @ np.asarray(center, float) + self._t[-1]
        color = hexrgb(color) if isinstance(color, str) else tuple(int(v) for v in color)
        if isinstance(studs, str):
            studs = {"top": ("Top",), "all": FACES, "none": (), "sides": ("Front", "Back", "Left", "Right"),
                     "top+sides": ("Top", "Front", "Back", "Left", "Right")}[studs]
        mat = kw.get("material", "SmoothPlastic")
        assert mat in MATERIALS, mat
        part = Part(
            shape=shape,
            size=tuple(_clean(v) for v in size),
            pos=tuple(_clean(v) for v in p),
            rot=tuple(_clean(v) for v in R.reshape(-1)),
            color=color,
            studs=tuple(studs),
            group=self._groups[-1],
            name=name or {"block": "Part", "wedge": "Wedge", "cyl": "Cylinder", "ball": "Ball"}[shape],
            **kw,
        )
        assert min(part.size) > 0, (part.name, part.size)
        self.parts.append(part)
        return part

    # -- primitives (coordonnées du repère courant) --------------------------
    def box(self, a, b, color, **kw) -> Part:
        """Bloc aligné sur les axes, donné par deux coins opposés."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        lo, hi = np.minimum(a, b), np.maximum(a, b)
        return self.part("block", hi - lo, (lo + hi) / 2, None, color, **kw)

    def boxc(self, center, size, color, yaw: float = 0.0, **kw) -> Part:
        """Bloc donné par son centre et sa taille, éventuellement tourné autour de Y."""
        return self.part("block", size, center, rot_y(yaw) if yaw else None, color, **kw)

    def wedge(self, a, b, color, down: str = "-z", **kw) -> Part:
        """Coin qui remplit la boîte [a, b] ; `down` = direction vers laquelle la pente descend."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        lo, hi = np.minimum(a, b), np.maximum(a, b)
        sx, sy, sz = hi - lo
        yaw = {"-z": 0, "+z": 180, "-x": 90, "+x": -90}[down]
        size = (sx, sy, sz) if down in ("-z", "+z") else (sz, sy, sx)
        return self.part("wedge", size, (lo + hi) / 2, rot_y(yaw) if yaw else None, color, **kw)

    def wedge_under(self, a, b, color, down: str = "-z", **kw) -> Part:
        """Coin retourné (pente vers le bas) : sous-faces d'avant-toits, consoles."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        lo, hi = np.minimum(a, b), np.maximum(a, b)
        sx, sy, sz = hi - lo
        # Retourné autour de l'axe de la pente : la face pleine reste du côté opposé à `down`.
        if down in ("-z", "+z"):
            R = rot_z(180) if down == "-z" else rot_y(180) @ rot_z(180)
            size = (sx, sy, sz)
        else:
            R = (rot_y(90) if down == "-x" else rot_y(-90)) @ rot_z(180)
            size = (sz, sy, sx)
        return self.part("wedge", size, (lo + hi) / 2, R, color, **kw)

    def cyl(self, center, r: float, h: float, color, axis: str = "y", **kw) -> Part:
        R = {"x": np.eye(3), "y": rot_z(90), "z": rot_y(90)}[axis]
        # Studs : seuls les disques des extrémités en reçoivent (faces Left/Right locales, l'axe étant X).
        # On traduit donc « top » d'un cylindre vertical en face Right, etc.
        studs = kw.pop("studs", ())
        if isinstance(studs, str):
            studs = {"top": ("Top",), "all": FACES, "none": (), "sides": (), "top+sides": ("Top",)}[studs]
        cap = {"y": {"Top": "Right", "Bottom": "Left"}, "x": {"Right": "Right", "Left": "Left"},
               "z": {"Front": "Right", "Back": "Left"}}[axis]
        studs = tuple(dict.fromkeys(cap[f] for f in studs if f in cap))
        return self.part("cyl", (h, 2 * r, 2 * r), center, R, color, studs=studs, **kw)

    def ball(self, center, r: float, color, **kw) -> Part:
        return self.part("ball", (2 * r, 2 * r, 2 * r), center, None, color, **kw)

    # -- export ------------------------------------------------------------
    def stats(self) -> dict:
        out: dict[str, int] = {}
        for p in self.parts:
            top = p.group.split("/")[0] or "(racine)"
            out[top] = out.get(top, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    def save_json(self, path: Path, meta: dict | None = None) -> None:
        data = {"meta": meta or {}, "parts": [asdict(p) for p in self.parts]}
        Path(path).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
