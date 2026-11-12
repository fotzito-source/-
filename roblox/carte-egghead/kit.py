"""Kit de construction « stud » : la carte est décrite comme une liste de Parts Roblox.

Tout est exprimé dans le repère Roblox (Y vers le haut, 1 unité = 1 stud) et avec les seules formes que Roblox sait
afficher sans maillage importé : bloc, coin, cylindre, boule, plus l'ellipsoïde (Part bloc + SpecialMesh « Sphere »).
La même liste sert ensuite à deux choses :
- `blender_scene.py` la transforme en maillages Blender pour les rendus et le fichier .blend ;
- `roblox_export.luau` (Lune) la transforme en vrai modèle Roblox (.rbxm / .rbxmx / place .rbxl).

Conventions Roblox reprises telles quelles :
- WedgePart : face pleine au fond (+Z local), la pente descend vers l'avant (-Z local) ;
- cylindre : l'axe est le X local (Size.X = longueur, Size.Y = Size.Z = diamètre) ;
- ellipsoïde : Part de forme Block qui porte un SpecialMesh (MeshType Sphere, Scale 1, 1, 1, sans décalage). Roblox
  affiche l'ellipsoïde inscrit dans la boîte de la pièce : ses diamètres sont Size.X, Size.Y, Size.Z. Sa COLLISION
  reste la boîte entière (les coins de la boîte bloquent les joueurs) : à l'appelant de choisir `collide`. Jamais de
  studs ni de panneau texte sur un ellipsoïde (le maillage cache les surfaces de la pièce) ;
- CFrame : matrice de rotation dont les colonnes sont les axes X, Y, Z locaux dans le monde.

Assemblages arrondis (méthodes du Builder, faits uniquement de primitives) : `anneau`, `disque`, `cone_etage`, `dome`,
`oeuf`, `tube`, `boule_flottante` ; outils : `cyl_entre`, `bloc_entre`, `repere`, `decouper`. Chacun renvoie un objet
`Pieces` (la liste des Parts créées, plus un dictionnaire `info`). Mode d'emploi complet : OUTILS.md.
"""

from __future__ import annotations

import json
import math
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

FACES = ("Top", "Bottom", "Front", "Back", "Left", "Right")
SHAPES = ("block", "wedge", "cyl", "ball", "ellipsoid")
MATERIALS = (
    "SmoothPlastic", "Plastic", "Wood", "WoodPlanks", "Slate", "Concrete", "Brick",
    "Cobblestone", "Rock", "Sand", "Grass", "Fabric", "Metal", "Neon", "Glass",
)
NOMS_DEFAUT = {"block": "Part", "wedge": "Wedge", "cyl": "Cylinder", "ball": "Ball", "ellipsoid": "Ellipsoide"}
# Les studs intégrés de Roblox ne s'affichent que sur Plastic : l'export passe toute pièce à studs en Plastic. Un Neon
# ou un verre y perdrait son aspect : studs refusés sur ces matériaux.
MATERIAUX_SANS_STUDS = ("Neon", "Glass")
TAILLE_MAX = 2048.0     # taille maximale d'une Part Roblox sur chaque axe
GROUPE_REPERES = "Reperes"

# Couleurs par défaut des assemblages (remplaçables à chaque appel)
VERRE = "#AEE6FF"         # verre bleuté des tubes et des hublots
NEON_CYAN = "#3DE8FF"     # halo de lévitation
BLANC_LABO = "#EEF1F6"    # blanc cassé des socles et colliers


def rot_x(deg: float) -> np.ndarray:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)


def rot_y(deg: float) -> np.ndarray:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)


def rot_z(deg: float) -> np.ndarray:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)


# Orientation des assemblages plans (anneau, disque, cône, dôme) : repère canonique = plan XZ, normale +Y.
# axe="z" : plan XY, normale +Z (arche face à Z) ; axe="x" : plan YZ, normale +X.
_AXES = {"y": np.eye(3), "z": rot_x(90), "x": rot_y(90) @ rot_x(90)}


def _clean(v: float, chiffres: int = 4) -> float:
    """Arrondit les erreurs flottantes (0.9999999 → 1) pour garder des tailles « en studs ». Les matrices de rotation
    gardent 6 décimales (4 décimales les déformeraient de 1e-4, soit 0,1 stud au bout d'une pièce de 1 000 studs)."""
    r = round(float(v), chiffres)
    return 0.0 if r == 0 else r


def _mat(rot) -> np.ndarray:
    """None → identité ; nombre → rotation autour de Y (degrés) ; sinon matrice 3 × 3."""
    if rot is None:
        return np.eye(3)
    if isinstance(rot, (int, float)):
        return rot_y(rot)
    return np.asarray(rot, float).reshape(3, 3)


def _unit(v) -> np.ndarray:
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    assert n > 1e-9, "vecteur nul"
    return v / n


def repere_normale(n) -> np.ndarray:
    """Rotation dont l'axe Y local est la direction `n` (X et Z choisis de façon stable)."""
    y = _unit(n)
    x0 = np.array([1.0, 0, 0]) if abs(y[0]) < 0.9 else np.array([0, 0, 1.0])
    x = _unit(x0 - (x0 @ y) * y)
    return np.column_stack([x, y, np.cross(x, y)])


def repere_direction(d, haut=(0, 1, 0)) -> np.ndarray:
    """Rotation dont l'axe X local est la direction `d` et l'axe Y local le plus proche possible de `haut`."""
    x = _unit(d)
    h = np.asarray(haut, float)
    if abs(_unit(h) @ x) > 0.999:          # direction verticale : on prend -Z comme « haut »
        h = np.array([0, 0, -1.0])
    y = _unit(h - (h @ x) * x)
    return np.column_stack([x, y, np.cross(x, y)])


def _pt(v) -> tuple:
    """Point en flottants simples (pour `Pieces.info`)."""
    return tuple(round(float(x), 4) for x in v)


def _orient(axe="y", rot=None) -> np.ndarray:
    """Repère d'un assemblage : `axe` ("x", "y", "z" ou vecteur normal), puis `rot` (matrice ou yaw en degrés)."""
    base = _AXES[axe] if isinstance(axe, str) else repere_normale(axe)
    return _mat(rot) @ base


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
    label: dict | None = None  # panneau texte : {face, text, color, bg?, font?, glow?}
    attrs: dict = field(default_factory=dict)


def hexrgb(h: str) -> tuple:
    """« #RRGGBB » ou « #RGB » → (r, g, b) 0-255."""
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    assert len(h) == 6, f"couleur invalide : #{h}"
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


def varier(c, rng, ecart: float = 0.05) -> tuple:
    """Petite variation de clarté (± `ecart`) : casse les grands aplats en « pixels » de tons voisins."""
    return shade(c, 1 + float(rng.uniform(-ecart, ecart)))


def _est_couleur(c) -> bool:
    return isinstance(c, str) or (isinstance(c, (tuple, list)) and len(c) == 3
                                  and all(isinstance(v, (int, float, np.integer, np.floating)) for v in c))


def _couleurs(c) -> list:
    """Une couleur, ou une liste de couleurs (utilisées tour à tour)."""
    if _est_couleur(c):
        return [c]
    out = list(c)
    assert out and all(_est_couleur(v) for v in out), f"couleur invalide : {c!r}"
    return out


class Pieces(list):
    """Pièces créées par un assemblage (liste de `Part`), plus `info` : quelques repères utiles (sommet, segments…),
    exprimés dans le repère courant au moment de l'appel."""

    def __init__(self, parts=(), **info):
        super().__init__(parts)
        self.info = dict(info)

    def regler(self, **props) -> "Pieces":
        """Change un attribut sur toutes les pièces, ex. `regler(collide=False, shadow=False)`."""
        for k, v in props.items():
            if k == "material":
                assert v in MATERIALS, v
            for p in self:
                if not hasattr(p, k):
                    raise AttributeError(f"Part n'a pas d'attribut {k!r}")
                setattr(p, k, v)
        return self


class Builder:
    """Accumule des Parts, avec une pile de repères (position + rotation) et de groupes."""

    def __init__(self, seed: int = 7):
        self.parts: list[Part] = []
        self._R = [np.eye(3)]
        self._t = [np.zeros(3)]
        self._groups = [""]
        self.rng = np.random.default_rng(seed)

    # -- repères et groupes -------------------------------------------------
    @contextmanager
    def at(self, pos=(0, 0, 0), yaw: float = 0.0, group: str | None = None, rot=None):
        """Sous-repère : translation `pos`, rotation `yaw` (degrés, autour de Y) puis `rot` (matrice), sous-groupe."""
        R = self._R[-1] @ rot_y(yaw) @ _mat(rot)
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
        rot_local = np.eye(3) if rot_local is None else np.asarray(rot_local, float)
        R = self._R[-1] @ rot_local
        p = self._R[-1] @ np.asarray(center, float) + self._t[-1]
        color = hexrgb(color) if isinstance(color, str) else tuple(int(round(v)) for v in color)
        if isinstance(studs, str):
            studs = {"top": ("Top",), "all": FACES, "none": (), "sides": ("Front", "Back", "Left", "Right"),
                     "top+sides": ("Top", "Front", "Back", "Left", "Right")}[studs]
        if shape == "ellipsoid" and studs:
            raise ValueError("ellipsoïde : jamais de studs (le SpecialMesh cache les surfaces de la pièce)")
        mat = kw.get("material", "SmoothPlastic")
        assert mat in MATERIALS, mat
        if studs and mat in MATERIAUX_SANS_STUDS:
            raise ValueError(f"{mat} : jamais de studs (une pièce à studs est exportée en Plastic, elle perdrait son "
                             f"{mat}) ; pour un sol transparent à studs : material=\"Plastic\", transparency=0.5")
        part = Part(
            shape=shape,
            size=tuple(_clean(v) for v in size),
            pos=tuple(_clean(v) for v in p),
            rot=tuple(_clean(v, 6) for v in R.reshape(-1)),
            color=color,
            studs=tuple(studs),
            group=self._groups[-1],
            name=name or NOMS_DEFAUT[shape],
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
        """Boule (Part Ball) : diamètre unique 2 r. Pour des diamètres différents : `ellipsoid`."""
        return self.part("ball", (2 * r, 2 * r, 2 * r), center, None, color, **kw)

    def ellipsoid(self, center, size, color, rot=None, **kw) -> Part:
        """Ellipsoïde de diamètres `size` = (dx, dy, dz) dans son repère local, centré en `center`.

        Roblox : Part de forme Block (taille `size`) + SpecialMesh Sphere (Scale 1, 1, 1). `rot` : matrice
        (rot_x(20) @ rot_y(30)…) ou yaw en degrés. Collision = la boîte de la pièce (pas la forme) : passer
        `collide=False` pour un décor qu'on ne doit pas « toucher » par ses coins. Jamais de studs (refusés).
        1 pièce.
        """
        return self.part("ellipsoid", size, center, _mat(rot), color, **kw)

    # -- outils de placement --------------------------------------------------
    def cyl_entre(self, p0, p1, r: float, color, **kw) -> Part:
        """Cylindre de rayon `r` tendu de `p0` à `p1` (barre, rampe, conduite). 1 pièce."""
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        d = p1 - p0
        return self.part("cyl", (float(np.linalg.norm(d)), 2 * r, 2 * r), (p0 + p1) / 2, repere_direction(d),
                         color, **kw)

    def bloc_entre(self, p0, p1, largeur: float, epaisseur: float, color, haut=(0, 1, 0), **kw) -> Part:
        """Poutre de section `largeur` × `epaisseur` de `p0` à `p1` ; sa face Top regarde au plus près de `haut`
        (studs="top" pour une passerelle). 1 pièce."""
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        d = p1 - p0
        return self.part("block", (float(np.linalg.norm(d)), epaisseur, largeur), (p0 + p1) / 2,
                         repere_direction(d, haut), color, **kw)

    def repere(self, nom: str, centre, taille=(6, 1, 6), yaw: float = 0.0) -> Part:
        """Repère invisible pour le jeu, rangé dans le dossier racine `Reperes` quel que soit le groupe courant.

        `centre` = point au sol (bas de la boîte, dans le repère courant) ; l'avant (-Z local, tourné de `yaw`)
        donne la direction du regard. « Spawn » : la place de démo y pose son SpawnLocation. Roblox : Transparency
        1, CanCollide false, CanTouch et CanQuery true (détectable par .Touched et par les raycasts). 1 pièce.
        """
        c = np.asarray(centre, float)
        self._groups.append(GROUPE_REPERES)
        try:
            return self.part("block", taille, c + (0, taille[1] / 2, 0), rot_y(yaw) if yaw else None, "#ffffff",
                             name=nom, transparency=1.0, collide=False, shadow=False)
        finally:
            self._groups.pop()

    # -- assemblages arrondis ------------------------------------------------
    def anneau(self, centre, rayon: float, epaisseur: float, couleur, n: int = 24, *, axe="y", rot=None,
               arc: float = 360.0, depart: float = 0.0, section: str = "rond", largeur: float | None = None,
               **kw) -> Pieces:
        """Anneau (tore) de rayon `rayon` (ligne médiane), fait de segments droits tangents au cercle.

        - `section` : "rond" (cylindres de diamètre `epaisseur`), "carre" (blocs `epaisseur` × `epaisseur`) ou
          "plat" (blocs : `epaisseur` le long de la normale, `largeur` dans le rayon ; rondelle, bord de chapeau).
        - Orientation : `axe` "y" (anneau horizontal, normale +Y), "z" (anneau vertical face à Z, en arche),
          "x", ou un vecteur normal ; puis `rot` (matrice, ex. rot_x(25) pour l'incliner) appliquée en plus.
        - `arc` (degrés) et `depart` : arc partiel. Angles dans le plan de l'anneau : axe "y" : 0 = +X, 90 = -Z ;
          axe "z" : 0 = +X, 90 = +Y ; axe "x" : 0 = -Z, 90 = +Y (pour "z" et "x", arc=180 donne une arche posée au
          sol).
        - `couleur` : une couleur ou une liste (alternance par segment) ; matériaux comme les primitives
          (`material="Neon"` pour un anneau lumineux).
        Les segments sont allongés pour fermer les joints côté extérieur (recouvrement côté intérieur). Les bouts d'un
        arc partiel sont allongés de même : le coin extérieur de la face extrême tombe exactement sur le demi-plan de
        l'angle `depart` (et `depart + arc`), le reste dépasse un peu côté intérieur. Une arche posée au sol (centre
        à la hauteur du sol, `axe="z"` ou `"x"`, `arc=180`) a donc ses pieds entièrement sous le sol, sans jour.
        En "carre" et "plat", deux segments qui se recouvrent n'ont jamais la même épaisseur (paliers de +0,04,
        soit 0,02 de chaque côté ; une rondelle large à petit trou en demande 3 à 5) : aucune face n'est confondue
        avec celle d'un voisin (sinon scintillement dans Roblox, taches noires dans Cycles).
        Pièces : round(n × arc / 360), soit 24 pour un anneau complet par défaut (12-16 suffisent sous 6 studs de
        rayon).
        """
        assert section in ("rond", "carre", "plat"), section
        F = _orient(axe, rot)
        c = np.asarray(centre, float)
        m = max(1, int(round(n * arc / 360.0)))
        step = math.radians(arc) / m
        plein = abs(arc - 360.0) < 1e-6
        w = float(largeur if (section == "plat" and largeur) else epaisseur)   # étendue dans le rayon
        demi = rayon * math.tan(step / 2)                                     # demi-côté du polygone tangent
        ext = (w / 2) * math.tan(step / 2)                                    # allongement qui ferme le joint
        cols = _couleurs(couleur)
        studs = kw.pop("studs", ())
        if section == "rond":
            studs = ()                     # bouts de cylindres cachés dans le voisin : rien à montrer
        # Paliers d'épaisseur (blocs) : deux segments dont les rectangles se recouvrent (au bord intérieur, chacun
        # s'étend sur ± alpha autour de son axe) reçoivent des paliers différents.
        paliers = [0] * m
        if section != "rond":
            alpha = math.atan2(demi + ext, max(rayon - w / 2, 1e-6))
            portee = max(1, math.ceil(2 * alpha / step - 1e-9) - 1)
            for k in range(m):
                pris = set()
                for j in range(k):
                    dist = min(k - j, m - (k - j)) if plein else k - j
                    if dist <= portee:
                        pris.add(paliers[j])
                while paliers[k] in pris:
                    paliers[k] += 1
        nom = kw.pop("name", "Anneau")
        out = Pieces(segments=m, rayon=rayon, centre=_pt(c), paliers=max(paliers) + 1)
        for k in range(m):
            th = math.radians(depart) + (k + 0.5) * step
            radial = np.array([math.cos(th), 0.0, -math.sin(th)])
            tang = np.array([-math.sin(th), 0.0, -math.cos(th)])
            # Allongement `ext` aux deux bouts de chaque segment : il ferme les joints, et aux bouts d'un arc il amène
            # le coin extérieur de la face extrême sur le demi-plan de l'angle de départ / d'arrivée.
            long_ = 2 * (demi + ext)
            pos = c + F @ (rayon * radial)
            X = F @ tang
            Y = F @ np.array([0.0, 1.0, 0.0])
            R = np.column_stack([X, Y, np.cross(X, Y)])          # Z local = rayon vers l'extérieur
            bosse = 0.04 * paliers[k]
            col = cols[k % len(cols)]
            if section == "rond":
                p = self.part("cyl", (long_, epaisseur, epaisseur), pos, R, col, name=nom, **kw)
            else:
                p = self.part("block", (long_, epaisseur + bosse, w), pos, R, col, studs=studs, name=nom, **kw)
            out.append(p)
        return out

    def disque(self, centre, rayon: float, epaisseur: float, couleur, *, rayon_int: float = 0.0, n: int = 24,
               axe="y", rot=None, **kw) -> Pieces:
        """Disque plat centré en `centre` (milieu de l'épaisseur) : plateau rond, bord de chapeau, auvent, halo.

        Plein : 1 cylindre (1 pièce) ; `studs="top"` pose les studs sur la face du dessus (côté +normale).
        Percé (`rayon_int` > 0) : rondelle de n blocs (anneau section "plat"), n pièces (24 par défaut). Le bord
        intérieur (polygone) est inscrit dans le cercle de rayon `rayon_int` : autour d'une colonne de ce rayon,
        il reste caché dedans (aucun jour entre la rondelle et la colonne).
        Orientation : `axe` / `rot` comme `anneau`.
        """
        F = _orient(axe, rot)
        if rayon_int > 0:
            assert rayon_int < rayon, (rayon_int, rayon)
            r_in = rayon_int * math.cos(math.pi / max(3, n))     # sommets du polygone intérieur sur le cercle
            out = self.anneau(centre, (rayon + r_in) / 2, epaisseur, couleur, n, axe=axe, rot=rot,
                              section="plat", largeur=rayon - r_in, name=kw.pop("name", "Disque"), **kw)
            out.info.update(rayon=rayon, rayon_int=rayon_int)
            return out
        studs = kw.pop("studs", ())
        if isinstance(studs, str):
            studs = {"top": ("Top",), "all": ("Top", "Bottom"), "none": (), "sides": (), "bottom": ("Bottom",),
                     "top+sides": ("Top",)}[studs]
        cap = tuple(dict.fromkeys({"Top": "Right", "Bottom": "Left"}[f] for f in studs if f in ("Top", "Bottom")))
        p = self.part("cyl", (epaisseur, 2 * rayon, 2 * rayon), centre, F @ rot_z(90), couleur, studs=cap,
                      name=kw.pop("name", "Disque"), **kw)
        return Pieces([p], rayon=rayon)

    def cone_etage(self, base, rayon_bas: float, rayon_haut: float, hauteur: float, couleurs, etages: int = 8, *,
                   axe="y", rot=None, pointe=None, profil: str = "milieu", hauteurs=None, **kw) -> Pieces:
        """Cône en étages : cylindres empilés de plus en plus fins (tour conique, flèche, cône rayé).

        - `base` : centre du disque du bas ; le cône monte le long de la normale (`axe` / `rot` comme `anneau`).
        - `couleurs` : une couleur, ou une liste alternée d'étage en étage (cône rayé rouge et blanc).
        - `profil` : "milieu" (rayon pris à mi-hauteur de l'étage : silhouette au plus près du cône) ou "bas"
          (rayon du bas de l'étage : gradins bien marqués, « pièce montée »). `rayon_haut` peut valoir 0.
        - `hauteurs` : liste des hauteurs d'étage (remise à l'échelle de `hauteur`) pour des rayures inégales.
        - `pointe` : None, une couleur, ou (couleur, rayon) : boule au sommet (+1 pièce).
        - `studs="top"` : studs sur les marches visibles (dessus de chaque étage).
        Pièces : `etages` (+1 avec la pointe).
        """
        assert profil in ("milieu", "bas"), profil
        F = _orient(axe, rot)
        b0 = np.asarray(base, float)
        hs = list(hauteurs) if hauteurs else [1.0] * etages
        tot = float(sum(hs))
        hs = [h * hauteur / tot for h in hs]
        cols = _couleurs(couleurs)
        studs = kw.pop("studs", ())
        if isinstance(studs, str):
            studs = {"top": ("Top",), "none": ()}[studs]
        cap = ("Right",) if "Top" in studs else ()
        nom = kw.pop("name", "Cone")
        R = F @ rot_z(90)
        out = Pieces()
        y = 0.0
        for i, h in enumerate(hs):
            f = (y + h / 2) / hauteur if profil == "milieu" else y / hauteur
            r = rayon_bas + (rayon_haut - rayon_bas) * f
            assert r > 0, ("cone_etage : rayon nul", i)
            out.append(self.part("cyl", (h, 2 * r, 2 * r), b0 + F @ np.array([0.0, y + h / 2, 0.0]), R,
                                 cols[i % len(cols)], studs=cap, name=nom, **kw))
            y += h
        sommet = b0 + F @ np.array([0.0, hauteur, 0.0])
        if pointe is not None:
            pc, pr = (pointe, max(rayon_haut, 0.3)) if _est_couleur(pointe) else pointe
            out.append(self.ball(sommet, pr, pc, name="Pointe", **{k: v for k, v in kw.items() if k != "material"}))
            sommet = sommet + F @ np.array([0.0, pr, 0.0])
        out.info.update(sommet=_pt(sommet), etages=len(hs))
        return out

    def dome(self, base, rayon: float, hauteur: float, couleur, *, rebord: float | None = None,
             tambour: float = 0.0, couleur_tambour=None, materiau_tambour: str = "SmoothPlastic", studs_tambour=(),
             axe="y", rot=None, collision: str = "boite", **kw) -> Pieces:
        """Dôme : demi-ellipsoïde posé sur un plan (dessus d'un tambour, d'une tour ou d'un toit), sans couture.

        - `base` : centre du plan d'appui (dessus du tambour). Le dôme monte de `hauteur` au-dessus.
        - `rayon` : rayon du SUPPORT (tambour créé ici, ou tour existante). Le dôme lui-même mesure
          `rayon - rebord` : le petit rebord visible (par défaut max(0,2 ; 4 % du rayon)) évite la couture
          dentelée et le scintillement là où l'ellipsoïde rejoindrait le flanc du cylindre. `rebord=0` pour un
          dôme qui affleure (sur un toit plat plus large, par exemple).
        - L'ellipsoïde est entier (Roblox ne coupe pas) : sa moitié basse descend de `hauteur` sous `base` et
          doit être cachée dans un volume plein : `tambour` ≥ `hauteur`, ou une tour / un bâtiment dessous.
          Sinon elle dépasse dessous (`info["dessous_visible"]` vaut alors True quand `tambour` > 0).
        - `tambour` (> 0) : cylindre de rayon `rayon` sous `base` (couleur `couleur_tambour`, matériau et studs
          propres, ex. `studs_tambour="top"` pour le rebord).
        - `collision` : "boite" (l'ellipsoïde garde `collide` de l'appel : sa boîte bloque), "aucune"
          (ellipsoïde sans collision) ou "gradins" (ellipsoïde sans collision + 4 cylindres invisibles en
          escalier qui suivent la forme : on peut marcher dessus).
        - `material="Glass", transparency=0.4` pour un dôme de verre (le tambour reste opaque).
        Pièces : 1 (+1 tambour, +4 gradins).
        """
        assert collision in ("boite", "aucune", "gradins"), collision
        F = _orient(axe, rot)
        b0 = np.asarray(base, float)
        rb = max(0.2, 0.04 * rayon) if rebord is None else float(rebord)
        rd = rayon - rb
        assert rd > 0, ("dome : rebord trop large", rayon, rb)
        ekw = dict(kw)
        if collision != "boite":
            ekw["collide"] = False
        out = Pieces()
        out.append(self.ellipsoid(b0, (2 * rd, 2 * hauteur, 2 * rd), couleur, rot=F, name=ekw.pop("name", "Dome"),
                                  **ekw))
        if tambour > 0:
            tkw = {k: v for k, v in kw.items() if k in ("collide", "shadow")}
            out.append(self.disque(b0 - F @ np.array([0.0, tambour / 2, 0.0]), rayon, tambour,
                                   couleur_tambour if couleur_tambour is not None else couleur, axe=axe, rot=rot,
                                   material=materiau_tambour, studs=studs_tambour, name="Tambour", **tkw)[0])
        if collision == "gradins":
            k = 4
            for i in range(k):
                y0, y1 = hauteur * i / k, hauteur * (i + 1) / k
                r = rd * math.sqrt(max(0.0, 1 - ((y0 + y1) / 2 / hauteur) ** 2))
                out.append(self.disque(b0 + F @ np.array([0.0, (y0 + y1) / 2, 0.0]), r, y1 - y0, "#ffffff",
                                       axe=axe, rot=rot, transparency=1.0, shadow=False, name="CollisionDome")[0])
        out.info.update(sommet=_pt(b0 + F @ np.array([0.0, hauteur, 0.0])), rayon_dome=rd,
                        dessous_visible=bool(0 < tambour < hauteur))
        return out

    def oeuf(self, base, rayon: float, hauteur: float, couleur, *, ventre: float = 0.4, enfonce: float = 0.0,
             rot=None, **kw) -> Pieces:
        """Œuf debout : bas arrondi, haut plus pointu. `base` = point le plus bas (posé au sol), `rayon` = rayon
        maximal (atteint à mi-hauteur), `hauteur` = hauteur totale.

        Deux ellipsoïdes : un « ventre » bas et rond (hauteur 2 × `ventre` × `hauteur`) et un grand ellipsoïde
        sur toute la hauteur ; sous la ligne du ventre, le grand reste caché dans le petit (vérifié), au-dessus
        c'est lui qu'on voit. `ventre` = 0,5 : un seul ellipsoïde ; 0,35-0,42 : œuf franc. `enfonce` : enfonce
        l'œuf dans le sol (assise plate). `rot` : inclinaison. Pièces : 2 (1 si `ventre` ≥ 0,5).
        """
        assert 0.2 <= ventre <= 0.5, ventre
        F = _mat(rot)
        b0 = np.asarray(base, float) - F @ np.array([0.0, enfonce, 0.0])
        H = float(hauteur)
        a = ventre * H                                         # demi-hauteur du ventre
        nom = kw.pop("name", "Oeuf")
        out = Pieces()
        if ventre >= 0.5 - 1e-9:
            out.append(self.ellipsoid(b0 + F @ np.array([0.0, H / 2, 0.0]), (2 * rayon, H, 2 * rayon), couleur,
                                      rot=F, name=nom, **kw))
        else:
            r_bas = rayon * 2 * math.sqrt(a * (H - a)) / H     # rayon du ventre : les deux se rejoignent en y = a
            # Contrôle : sous y = a, le grand ellipsoïde reste dans le ventre (aucune bosse sous l'œuf)
            for y in np.linspace(0.0, a, 41)[1:-1]:
                r_grand = rayon * math.sqrt(max(0.0, 1 - ((y - H / 2) / (H / 2)) ** 2))
                r_ventre = r_bas * math.sqrt(max(0.0, 1 - ((y - a) / a) ** 2))
                assert r_grand <= r_ventre + 1e-6, ("oeuf : forme impossible", y)
            out.append(self.ellipsoid(b0 + F @ np.array([0.0, a, 0.0]), (2 * r_bas, 2 * a, 2 * r_bas), couleur,
                                      rot=F, name=nom, **kw))
            out.append(self.ellipsoid(b0 + F @ np.array([0.0, H / 2, 0.0]), (2 * rayon, H, 2 * rayon), couleur,
                                      rot=F, name=nom, **kw))
        out.info.update(sommet=_pt(b0 + F @ np.array([0.0, H, 0.0])))
        return out

    def tube(self, p0, p1, rayon: float, couleur=VERRE, *, materiau: str = "Glass", transparence: float | None = None,
             colliers=0, couleur_collier=BLANC_LABO, epaisseur_collier: float | None = None,
             longueur_collier: float | None = None, coeur=None, creux: int = 0, **kw) -> Pieces:
        """Tube de `p0` à `p1` (verre par défaut) : passerelle vitrée, conduite, colonne de verre.

        - Plein (par défaut) : 1 cylindre. `creux=n` (8-16) : tube creux de n lames (une lame à plat au fond) :
          on peut marcher dedans (couloir vitré). Les lames se recouvrent un peu aux arêtes ; une lame sur deux est
          plus longue de 0,04 (leurs faces de bout ne sont jamais dans le même plan). Un
          personnage mesure environ 5 studs : hauteur intérieure 2 × (rayon − épaisseur des lames), donc rayon ≥ 4
          pour un couloir praticable.
        - `colliers` : 0, un nombre (1 = au milieu ; 2 = aux deux bouts ; k = régulièrement, bouts compris) ou une
          liste de fractions (0 → p0, 1 → p1) : bagues opaques un peu plus larges (`couleur_collier`). Une bague
          posée à un bout dépasse de 0,05 stud (sa face ne se confond pas avec le bout du tube). Tube plein : bague
          = 1 cylindre ; tube creux : bague creuse (`anneau` plat de `creux` segments posés sur les lames, le
          couloir reste ouvert).
        - `coeur` : une couleur → fil Neon dans l'axe, arrêté 0,05 avant chaque bout (tube plein seulement).
        - `materiau`, `transparence` : Glass et 0,45 par défaut (0 pour un autre matériau, sauf valeur donnée) ;
          `materiau="SmoothPlastic"` pour une conduite opaque.
        Pièces : plein 1 + colliers (+1 cœur) ; creux `creux` × (1 + colliers).
        """
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        d = p1 - p0
        L = float(np.linalg.norm(d))
        Rd = repere_direction(d)
        out = Pieces(longueur=L)
        tkw = {k2: v for k2, v in kw.items() if k2 not in ("material", "transparency")}
        tkw["material"] = kw.get("material", materiau)
        if transparence is None:
            transparence = kw.get("transparency", 0.45 if tkw["material"] == "Glass" else 0.0)
        tkw["transparency"] = transparence
        nom = tkw.pop("name", "Tube")
        radiaux = []                                                  # directions des lames (tube creux)
        if creux:
            nl = int(creux)
            assert nl >= 6, "tube creux : au moins 6 lames"
            ep = max(0.2, 0.08 * rayon)
            larg = 2 * rayon * math.tan(math.pi / nl) + 0.05          # côté du polygone tangent (+ recouvrement)
            for k in range(nl):
                phi = -math.pi / 2 + 2 * math.pi * k / nl             # k = 0 : lame du fond, à plat
                radial = np.array([0.0, math.sin(phi), math.cos(phi)])   # dans le repère du tube : -Y = bas
                radiaux.append(radial)
                ctr = (p0 + p1) / 2 + Rd @ (radial * (rayon - ep / 2))
                Y = Rd @ radial
                X = Rd[:, 0]
                R = np.column_stack([X, Y, np.cross(X, Y)])
                # Paliers de longueur (+0,04) : les faces de bout de deux lames voisines se recouvrent dans le coin
                # intérieur ; décalées de 0,02, elles ne sont jamais dans le même plan.
                pal = 2 if (nl % 2 and k == nl - 1) else k % 2
                out.append(self.part("block", (L + 0.04 * pal, ep, larg), ctr, R, couleur, name=nom, **tkw))
        else:
            out.append(self.cyl_entre(p0, p1, rayon, couleur, name=nom, **tkw))
        if isinstance(colliers, (int, np.integer)):
            k = int(colliers)
            fr = [] if k <= 0 else [0.5] if k == 1 else [i / (k - 1) for i in range(k)]
        else:
            fr = list(colliers)
        ec = epaisseur_collier if epaisseur_collier is not None else max(0.25, 0.15 * rayon)
        lc = longueur_collier if longueur_collier is not None else max(0.6, 0.5 * rayon)
        ckw = {k2: v for k2, v in kw.items() if k2 in ("collide", "shadow")}
        deb = 0.05          # une bague posée à un bout dépasse du tube : pas de face confondue avec son bout
        for f in fr:
            s = min(max(f * L, lc / 2 - deb), L - lc / 2 + deb)
            ctr = p0 + d / L * s
            if creux:
                # Bague creuse : anneau « plat » autour de l'axe, un segment sur chaque lame (mêmes directions), du
                # milieu de l'épaisseur des lames (bord intérieur caché dans la lame, jamais dans le couloir) jusqu'à
                # rayon + ec. L'anneau gère les recouvrements (paliers de longueur le long de l'axe).
                r_in, r_out = rayon - ep / 2, rayon + ec
                Fa = repere_normale(d)                               # repère de l'anneau : Y = axe du tube
                bas = Rd @ radiaux[0]                                # direction de la lame du fond
                th0 = math.degrees(math.atan2(-(bas @ Fa[:, 2]), bas @ Fa[:, 0]))
                out.extend(self.anneau(ctr, (r_in + r_out) / 2, lc, couleur_collier, nl, axe=d,
                                       depart=th0 - 180.0 / nl, section="plat", largeur=r_out - r_in,
                                       name="Collier", **ckw))
            else:
                out.append(self.part("cyl", (lc, 2 * (rayon + ec), 2 * (rayon + ec)), ctr, Rd, couleur_collier,
                                     name="Collier", **ckw))
        if coeur is not None and not creux:
            ins = min(0.05, L / 4)       # arrêté avant les bouts : ses disques ne se confondent pas avec ceux du tube
            out.append(self.cyl_entre(p0 + d / L * ins, p1 - d / L * ins, max(0.1, 0.18 * rayon), coeur,
                                      material="Neon", collide=False, shadow=False, name="Coeur"))
        return out

    def boule_flottante(self, centre, rayon: float, couleur, *, aplatissement: float = 0.8, hublot=VERRE,
                        ceinture=None, halo=NEON_CYAN, faisceau: bool = True, socle=BLANC_LABO,
                        sol: float = 0.0, **kw) -> Pieces:
        """Capsule en lévitation (pod) : coque ellipsoïdale, bulle de verre dessus, halo Neon dessous, faisceau
        lumineux jusqu'à un socle émetteur au sol. Rien ne flotte « par erreur » : le faisceau relie la capsule
        à son socle.

        - `centre` : centre de la coque ; `sol` : hauteur du sol (repère courant) pour le faisceau et le socle.
        - `aplatissement` : hauteur / largeur de la coque. `hublot`, `ceinture` (anneau de 16 segments autour de
          l'équateur), `halo`, `socle` : une couleur, ou None pour s'en passer. `faisceau=False` : pas de faisceau.
        - `**kw` (collide, shadow…) s'applique à la coque et à la bulle ; halo et faisceau sont sans collision.
        Pièces : coque 1 + hublot 1 + halo 1 + faisceau 1 + socle 2 = 6 par défaut (+16 avec la ceinture).
        """
        c = np.asarray(centre, float)
        hy = rayon * aplatissement                       # demi-hauteur de la coque
        out = Pieces()
        out.append(self.ellipsoid(c, (2 * rayon, 2 * hy, 2 * rayon), couleur, name=kw.pop("name", "Capsule"), **kw))
        if hublot is not None:
            hkw = {k: v for k, v in kw.items() if k in ("collide", "shadow")}
            out.append(self.ellipsoid(c + (0, 0.42 * hy, 0), (1.16 * rayon, 1.3 * hy, 1.16 * rayon), hublot,
                                      material="Glass", transparency=0.35, name="Hublot", **hkw))
        if ceinture is not None:
            out.extend(self.anneau(c, rayon * 0.99, max(0.2, 0.16 * rayon), ceinture, 16, name="Ceinture",
                                   collide=False))
        bas = c[1] - hy
        if halo is not None:
            out.extend(self.disque((c[0], bas - 0.35 * rayon, c[2]), 0.62 * rayon, max(0.12, 0.06 * rayon), halo,
                                   material="Neon", transparency=0.15, collide=False, shadow=False, name="Halo"))
        if socle is not None:
            out.extend(self.disque((c[0], sol + 0.3, c[2]), 0.5 * rayon, 0.6, socle, name="Socle"))
            out.extend(self.disque((c[0], sol + 0.66, c[2]), 0.32 * rayon, 0.12, halo or NEON_CYAN,
                                   material="Neon", collide=False, shadow=False, name="Emetteur"))
        if faisceau and bas - 0.35 * rayon > sol + 0.7:
            out.append(self.cyl_entre((c[0], sol + 0.7, c[2]), (c[0], bas - 0.35 * rayon, c[2]),
                                      max(0.12, 0.1 * rayon), halo or NEON_CYAN, material="Neon", transparency=0.55,
                                      collide=False, shadow=False, name="Faisceau"))
        out.info.update(sommet=_pt(c + (0, (0.42 + 0.65) * hy if hublot is not None else hy, 0)))
        return out

    # -- découpage (streaming) -------------------------------------------------
    def decouper(self, prefixes=("Sol",), taille: float = 64) -> int:
        """Range les pièces des groupes `prefixes` (et de leurs sous-groupes) dans des sous-modèles Bloc_i_j de
        `taille` × `taille` studs selon leur centre (X, Z). « Sol/Dalles » devient « Sol/Bloc_+0_-1/Dalles ».
        Avec StreamingEnabled, Roblox envoie de toute façon les pièces d'un modèle ordinaire (non atomique) une à
        une selon leur position : ce découpage range surtout l'Explorer par quartiers, et permet de régler un
        quartier entier (ModelStreamingMode, par exemple Atomic) d'un coup. Renvoie le nombre de pièces rangées."""
        n = 0
        for p in self.parts:
            for pre in prefixes:
                pre = pre.rstrip("/")
                if p.group == pre or p.group.startswith(pre + "/"):
                    i, j = math.floor(p.pos[0] / taille), math.floor(p.pos[2] / taille)
                    p.group = f"{pre}/Bloc_{i:+d}_{j:+d}{p.group[len(pre):]}"
                    n += 1
                    break
        return n

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


# ---------------------------------------------------------------------------
# Export Roblox (Lune) : utilisé par rendu.py et par `python carte.py --export DOSSIER`
# ---------------------------------------------------------------------------

LUNE_SCRATCH = "/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/tools/lune/lune"


def lune_path() -> str | None:
    """Exécutable Lune : variable LUNE, sinon `lune` dans le PATH, sinon la copie de l'atelier."""
    import os
    import shutil
    for cand in (os.environ.get("LUNE"), shutil.which("lune"), LUNE_SCRATCH):
        if cand and Path(cand).exists():
            return cand
    return None


def exporter_roblox(parts_json, dossier, *options: str) -> dict:
    """Lance roblox_export.luau sur `parts_json` : écrit NOM.rbxm, NOM.rbxmx et NOM-demo.rbxl dans `dossier`, relit
    les fichiers (contrôles) et renvoie le résumé JSON imprimé par le script. Lève RuntimeError en cas d'échec."""
    import subprocess
    lune = lune_path()
    if not lune:
        raise RuntimeError("Lune introuvable (variable LUNE, PATH) : export Roblox impossible")
    script = Path(__file__).resolve().parent / "roblox_export.luau"
    r = subprocess.run([lune, "run", str(script), "--", str(parts_json), str(dossier), *options],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"export Roblox en échec :\n{r.stdout}\n{r.stderr}")
    return json.loads(r.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------------------
# Contrôles génériques (utilisés par carte.verifications et apercu.py)
# ---------------------------------------------------------------------------

def bornes_part(p: Part):
    """Boîte englobante (min, max) d'une pièce, dans le repère de la carte."""
    R = np.asarray(p.rot).reshape(3, 3)
    half = np.abs(R) @ (np.asarray(p.size) / 2)
    return np.asarray(p.pos) - half, np.asarray(p.pos) + half


def bornes(parts, visibles: bool = True):
    """Boîte englobante d'une liste de pièces (sans les pièces invisibles si `visibles`)."""
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for p in parts:
        if visibles and p.transparency >= 0.99:
            continue
        a, b = bornes_part(p)
        lo, hi = np.minimum(lo, a), np.maximum(hi, b)
    return lo, hi


_COINS_BLOC = {"Top": [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)],
               "Bottom": [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)],
               "Front": [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)],
               "Back": [(1, -1, 1), (1, 1, 1), (-1, 1, 1), (-1, -1, 1)],
               "Left": [(-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1)],
               "Right": [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]}
_COINS_COIN = {"Bottom": _COINS_BLOC["Bottom"], "Back": _COINS_BLOC["Back"],
               "Top": [(-1, -1, -1), (-1, 1, 1), (1, 1, 1), (1, -1, -1)],      # la pente
               "Left": [(-1, -1, 1), (-1, 1, 1), (-1, -1, -1)], "Right": [(1, -1, -1), (1, 1, 1), (1, -1, 1)]}


def _faces_planes(p: Part):
    """Faces planes d'une pièce : (nom, sommets monde (k × 3), normale unitaire). Blocs, coins, disques des cylindres."""
    R = np.asarray(p.rot, float).reshape(3, 3)
    t = np.asarray(p.pos, float)
    h = np.asarray(p.size, float) / 2
    polys = []
    if p.shape in ("block", "wedge"):
        for nom, cs in (_COINS_BLOC if p.shape == "block" else _COINS_COIN).items():
            polys.append((nom, (np.asarray(cs, float) * h) @ R.T + t))
    elif p.shape == "cyl":
        r = min(h[1], h[2])
        a = np.linspace(0, 2 * math.pi, 24, endpoint=False)
        for sx, nom in ((1, "Right"), (-1, "Left")):
            loc = np.column_stack([np.full(24, sx * h[0]), r * np.cos(sx * a), r * np.sin(sx * a)])
            polys.append((nom, loc @ R.T + t))
    out = []
    for nom, P in polys:
        n = np.cross(P[1] - P[0], P[2] - P[1])
        if np.linalg.norm(n) > 1e-12:
            out.append((nom, P, n / np.linalg.norm(n)))
    return out


def _aire_inter(A, B) -> float:
    """Aire de l'intersection de deux polygones convexes 2D (Sutherland-Hodgman)."""
    def aire(q):                     # > 0 dans le sens trigonométrique
        return 0.5 * sum(q[i - 1][0] * q[i][1] - q[i][0] * q[i - 1][1] for i in range(len(q)))
    A = A if aire(A) > 0 else A[::-1]
    out = B if aire(B) > 0 else B[::-1]
    for i in range(len(A)):
        (ax, ay), (bx, by) = A[i - 1], A[i]
        inp, out = out, []
        for j in range(len(inp)):
            (px, py), (qx, qy) = inp[j - 1], inp[j]
            dp = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
            dq = (bx - ax) * (qy - ay) - (by - ay) * (qx - ax)
            if dq >= 0:
                if dp < 0:
                    out.append((px + (qx - px) * dp / (dp - dq), py + (qy - py) * dp / (dp - dq)))
                out.append((qx, qy))
            elif dp >= 0:
                out.append((px + (qx - px) * dp / (dp - dq), py + (qy - py) * dp / (dp - dq)))
        if len(out) < 3:
            return 0.0
    return abs(aire(out))


def _faces_confondues(parts, limite: int = 10) -> tuple[list, list]:
    """Une seule recherche, deux listes (au plus `limite` cas chacune) : (problèmes, paires de même teinte)."""
    seaux: dict = {}
    for i, p in enumerate(parts):
        if p.transparency >= 0.99:
            continue
        for nom, P, n in _faces_planes(p):
            cle = (tuple(np.round(n, 3)), int(math.floor(float(n @ P[0]) / 0.002)))
            seaux.setdefault(cle, []).append((i, nom, P, n))
    pbs, memes = [], []
    vus = set()
    for (nk, ok), liste in seaux.items():
        voisins = [f for d in (-1, 0, 1) for f in seaux.get((nk, ok + d), [])]
        for (i, na, Pa, n) in liste:
            lo_a, hi_a = Pa.min(axis=0) - 1e-3, Pa.max(axis=0) + 1e-3
            for (j, nb, Pb, m) in voisins:
                cle_paire = (i, na, j, nb) if i < j else (j, nb, i, na)
                if j == i or cle_paire in vus or n @ m < 0.99999:
                    continue
                if abs(n @ (Pb[0] - Pa[0])) > 1e-3 or (Pb.max(axis=0) < lo_a).any() or (Pb.min(axis=0) > hi_a).any():
                    continue
                vus.add(cle_paire)
                a, b = parts[i], parts[j]
                pareil = (a.color == b.color and a.material == b.material and a.transparency == b.transparency
                          and na not in a.studs and nb not in b.studs)
                cible = memes if pareil else pbs
                if len(cible) >= limite:
                    if len(pbs) >= limite and len(memes) >= limite:
                        return pbs, memes
                    continue
                u = (Pa[1] - Pa[0]) / np.linalg.norm(Pa[1] - Pa[0])
                v = np.cross(n, u)
                ar = _aire_inter([((q - Pa[0]) @ u, (q - Pa[0]) @ v) for q in Pa],
                                 [((q - Pa[0]) @ u, (q - Pa[0]) @ v) for q in Pb])
                if ar > 1e-3:
                    cible.append((f"{a.group}/{a.name}.{na}", f"{b.group}/{b.name}.{nb}", round(float(ar), 3)))
    return pbs, memes


def faces_confondues(parts, limite: int = 10, meme_teinte: bool = False) -> list:
    """Faces planes de deux pièces différentes dans le même plan, tournées du même côté, qui se recouvrent (aire
    > 0,001 stud²) : scintillement dans Roblox, taches dans Cycles. Ignorées : pièces invisibles et, sauf si
    `meme_teinte` (qui ne renvoie qu'elles), paires de même couleur, même matériau, même transparence et sans studs
    (dans Roblox le scintillement ne se voit pas ; dans Cycles elles font encore des taches noires). Renvoie au plus
    `limite` cas (nom/groupe/face des deux pièces, aire)."""
    return _faces_confondues(parts, limite)[1 if meme_teinte else 0]


def controles(parts) -> dict:
    """Comptes et anomalies d'une liste de pièces (toutes doivent être vides pour les listes « problemes »)."""
    par_forme: dict[str, int] = {}
    for p in parts:
        par_forme[p.shape] = par_forme.get(p.shape, 0) + 1
    reperes = [p for p in parts if p.group == GROUPE_REPERES or p.group.startswith(GROUPE_REPERES + "/")]
    confondues, memes = _faces_confondues(parts)
    pb = {
        "trop_grandes": [(p.name, p.group, p.size) for p in parts if max(p.size) > TAILLE_MAX][:10],
        "trop_petites": [(p.name, p.group, p.size) for p in parts if min(p.size) < 0.05][:10],
        "ellipsoides_a_studs": [(p.name, p.group) for p in parts if p.shape == "ellipsoid" and p.studs][:10],
        "studs_sur_neon_ou_verre": [(p.name, p.group, p.material) for p in parts
                                    if p.studs and p.material in MATERIAUX_SANS_STUDS][:10],
        "panneaux_hors_bloc": [(p.name, p.group) for p in parts if p.label and p.shape != "block"][:10],
        "boules_non_rondes": [(p.name, p.group, p.size) for p in parts
                              if p.shape == "ball" and max(p.size) - min(p.size) > 1e-3][:10],
        "reperes_visibles": [p.name for p in reperes if p.transparency < 1 or p.collide][:10],
        "faces_confondues": confondues,
    }
    return {
        "pieces": len(parts),
        "par_forme": par_forme,
        # faces confondues de même teinte : invisibles dans Roblox, taches noires dans les rendus Cycles (10 au plus)
        "faces_confondues_meme_teinte": memes,
        "neon": sum(1 for p in parts if p.material == "Neon"),
        "verre": sum(1 for p in parts if p.material == "Glass"),
        "transparentes": sum(1 for p in parts if 0 < p.transparency < 1),
        "pieces_a_studs": sum(1 for p in parts if p.studs),
        "sans_collision": sum(1 for p in parts if not p.collide),
        "reperes": sorted(p.name for p in reperes),
        "problemes": {k: v for k, v in pb.items() if v},
    }
