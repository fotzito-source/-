"""Construit la scène Blender à partir de `parts.json`, rend les vues et exporte les fichiers.

S'exécute avec Blender (`blender -b -P blender_scene.py -- …`) ou avec le module Python `bpy`
(`pip install bpy`, Python 3.13 pour bpy 5.2). Le rendu imite l'éclairage « Future » de Roblox :
soleil net, ciel bleu, couleurs saturées, aucun biseau sur les arêtes (les Parts Roblox n'en ont pas).

Repères : Roblox (x, y, z) avec Y en haut → Blender (x, -z, y) avec Z en haut ; 1 stud = 1 unité.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from textures import TEX_DIR, label_image  # noqa: E402

# Roblox → Blender
C = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)

MAT_PROPS = {
    # matériau Roblox : (rugosité, métal, émission)
    "SmoothPlastic": (0.45, 0.0, 0.0),
    "Plastic": (0.6, 0.0, 0.0),
    "Wood": (0.75, 0.0, 0.0),
    "WoodPlanks": (0.75, 0.0, 0.0),
    "Slate": (0.85, 0.0, 0.0),
    "Concrete": (0.9, 0.0, 0.0),
    "Brick": (0.9, 0.0, 0.0),
    "Cobblestone": (0.9, 0.0, 0.0),
    "Rock": (0.9, 0.0, 0.0),
    "Sand": (0.95, 0.0, 0.0),
    "Grass": (0.95, 0.0, 0.0),
    "Fabric": (0.95, 0.0, 0.0),
    "Metal": (0.35, 0.7, 0.0),
    "Neon": (0.5, 0.0, 2.2),
    "Glass": (0.08, 0.0, 0.0),
}

# --------------------------------------------------------------------------
# Gabarits de géométrie (repère local de la pièce, cube unité [-0.5, 0.5])
# --------------------------------------------------------------------------

# Bloc : (nom de face Roblox, 4 coins, axes U et V pour les UV en studs)
BOX_FACES = [
    ("Top", [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)], (0, 2)),
    ("Bottom", [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)], (0, 2)),
    ("Front", [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)], (0, 1)),
    ("Back", [(1, -1, 1), (1, 1, 1), (-1, 1, 1), (-1, -1, 1)], (0, 1)),
    ("Left", [(-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1)], (2, 1)),
    ("Right", [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)], (2, 1)),
]

# Coin Roblox : arête haute au fond (+Z), pente vers l'avant (-Z)
WEDGE_FACES = [
    ("Bottom", [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)], (0, 2)),
    ("Back", [(1, -1, 1), (1, 1, 1), (-1, 1, 1), (-1, -1, 1)], (0, 1)),
    ("Top", [(-1, -1, -1), (-1, 1, 1), (1, 1, 1), (1, -1, -1)], (0, 2)),  # la pente
    ("Left", [(-1, -1, 1), (-1, 1, 1), (-1, -1, -1)], (2, 1)),
    ("Right", [(1, -1, -1), (1, 1, 1), (1, -1, 1)], (2, 1)),
]


class MeshAccum:
    """Accumule les faces d'un objet Blender avec leurs attributs par face."""

    def __init__(self):
        self.verts: list = []
        self.faces: list = []
        self.uvs: list = []  # par coin de face, dans l'ordre des faces
        self.col: list = []
        self.studs: list = []
        self.rough: list = []
        self.metal: list = []
        self.emit: list = []
        self.alpha: list = []
        self.smooth: list = []

    def add_face(self, pts_world, uvs, color, studs, mp, alpha, smooth=False, idx=None):
        if idx is None:
            base = len(self.verts)
            self.verts.extend(pts_world)
            idx = list(range(base, base + len(pts_world)))
        self.faces.append(idx)
        self.uvs.extend(uvs)
        self.col.append(color)
        self.studs.append(studs)
        self.rough.append(mp[0])
        self.metal.append(mp[1])
        self.emit.append(mp[2])
        self.alpha.append(alpha)
        self.smooth.append(smooth)


def _lin(c):
    """sRGB 0-255 → linéaire (attribut couleur Blender)."""
    c = np.asarray(c, float) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def add_part(acc: MeshAccum, p: dict, stud_scale: float) -> None:
    size = np.asarray(p["size"], float)
    R = np.asarray(p["rot"], float).reshape(3, 3)
    t = np.asarray(p["pos"], float)
    M = C @ R
    tw = C @ t
    col = tuple(_lin(p["color"])) + (1.0,)
    mp = MAT_PROPS.get(p["material"], MAT_PROPS["SmoothPlastic"])
    alpha = 1.0 - float(p.get("transparency", 0.0))
    studs = set(p.get("studs") or ())

    def world(local_unit):
        return (M @ (np.asarray(local_unit, float) * size / 2)) + tw

    shape = p["shape"]
    if shape in ("block", "wedge"):
        faces = BOX_FACES if shape == "block" else WEDGE_FACES
        for name, corners, (ua, va) in faces:
            pts = [world(c) for c in corners]
            loc = [np.asarray(c, float) * size / 2 for c in corners]
            if shape == "wedge" and name == "Top":
                # UV le long de la pente : V = distance réelle sur la pente
                slope = math.hypot(size[1], size[2])
                uvs = [((l[0] + size[0] / 2) / stud_scale, (l[2] + size[2] / 2) / size[2] * slope / stud_scale) for l in loc]
            else:
                uvs = [((l[ua] + size[ua] / 2) / stud_scale, (l[va] + size[va] / 2) / stud_scale) for l in loc]
            acc.add_face(pts, uvs, col, 1.0 if name in studs else 0.0, mp, alpha)
    elif shape == "cyl":
        n = max(12, min(48, int(math.pi * size[1] / 1.2)))
        h, r = size[0] / 2, min(size[1], size[2]) / 2
        ring = [(math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)) for i in range(n)]
        base = len(acc.verts)
        for sx in (-1, 1):
            for cy, cz in ring:
                acc.verts.append((M @ np.array([sx * h, cy * r, cz * r])) + tw)
        circ = 2 * math.pi * r
        side_studs = 0.0  # Roblox : pas de texture stud fiable sur la surface courbe
        for i in range(n):
            j = (i + 1) % n
            idx = [base + i, base + j, base + n + j, base + n + i]
            u0, u1 = circ * i / n / stud_scale, circ * (i + 1) / n / stud_scale
            acc.add_face(None, [(u0, 0), (u1, 0), (u1, 2 * h / stud_scale), (u0, 2 * h / stud_scale)],
                         col, side_studs, mp, alpha, smooth=True, idx=idx)
        for sx, name in ((-1, "Left"), (1, "Right")):
            pts = [(M @ np.array([sx * h, cy * r, cz * r])) + tw for cy, cz in (ring if sx > 0 else ring[::-1])]
            uvs = [((cy + 1) * r / stud_scale, (cz + 1) * r / stud_scale) for cy, cz in (ring if sx > 0 else ring[::-1])]
            acc.add_face(pts, uvs, col, 1.0 if name in studs else 0.0, mp, alpha)
    elif shape == "ball":
        r = min(size) / 2
        nu, nv = 16, 10
        base = len(acc.verts)
        for j in range(nv + 1):
            th = math.pi * j / nv
            for i in range(nu):
                ph = 2 * math.pi * i / nu
                acc.verts.append((M @ np.array([r * math.sin(th) * math.cos(ph), r * math.cos(th), r * math.sin(th) * math.sin(ph)])) + tw)
        for j in range(nv):
            for i in range(nu):
                i2 = (i + 1) % nu
                idx = [base + j * nu + i, base + j * nu + i2, base + (j + 1) * nu + i2, base + (j + 1) * nu + i]
                acc.add_face(None, [(0, 0)] * 4, col, 0.0, mp, alpha, smooth=True, idx=idx)


def build_object(name: str, acc: MeshAccum, material, collection) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in acc.verts], [], acc.faces)
    me.update()
    nf = len(acc.faces)
    assert len(me.polygons) == nf, (name, len(me.polygons), nf)

    def fattr(attr, kind, values, dom="FACE"):
        a = me.attributes.new(attr, kind, dom)
        flat = np.asarray(values, np.float32).reshape(-1) if kind != "BOOLEAN" else np.asarray(values, bool)
        a.data.foreach_set("color" if kind == "FLOAT_COLOR" else "value", flat)

    fattr("col", "FLOAT_COLOR", acc.col)
    fattr("studs", "FLOAT", acc.studs)
    fattr("rough", "FLOAT", acc.rough)
    fattr("metal", "FLOAT", acc.metal)
    fattr("emit", "FLOAT", acc.emit)
    fattr("alpha", "FLOAT", acc.alpha)
    fattr("sharp_face", "BOOLEAN", [not s for s in acc.smooth])
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", np.asarray(acc.uvs, np.float32).reshape(-1))
    me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


# --------------------------------------------------------------------------
# Matériau unique : couleur par face + calque stud, comme Part.Color + Texture dans Roblox
# --------------------------------------------------------------------------

def make_material() -> bpy.types.Material:
    m = bpy.data.materials.new("StudPart")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Specular IOR Level"].default_value = 0.35

    def attr(name, kind="Fac"):
        a = nt.nodes.new("ShaderNodeAttribute")
        a.attribute_type = "GEOMETRY"
        a.attribute_name = name
        return a

    col, studs, rough, metal, emit, alpha = (attr(n) for n in ("col", "studs", "rough", "metal", "emit", "alpha"))
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(str(TEX_DIR / "stud.png"), check_existing=True)
    img.alpha_mode = "STRAIGHT"
    tex.image = img
    tex.interpolation = "Cubic"
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "UVMap"
    nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])

    # facteur = alpha de la texture × drapeau stud de la face
    fac = nt.nodes.new("ShaderNodeMath")
    fac.operation = "MULTIPLY"
    nt.links.new(tex.outputs["Alpha"], fac.inputs[0])
    nt.links.new(studs.outputs["Fac"], fac.inputs[1])
    mixc = nt.nodes.new("ShaderNodeMix")
    mixc.data_type = "RGBA"
    nt.links.new(fac.outputs[0], mixc.inputs["Factor"])
    nt.links.new(col.outputs["Color"], mixc.inputs["A"])
    nt.links.new(tex.outputs["Color"], mixc.inputs["B"])

    nt.links.new(mixc.outputs["Result"], bsdf.inputs["Base Color"])
    nt.links.new(rough.outputs["Fac"], bsdf.inputs["Roughness"])
    nt.links.new(metal.outputs["Fac"], bsdf.inputs["Metallic"])
    nt.links.new(col.outputs["Color"], bsdf.inputs["Emission Color"])
    nt.links.new(emit.outputs["Fac"], bsdf.inputs["Emission Strength"])
    nt.links.new(alpha.outputs["Fac"], bsdf.inputs["Alpha"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def make_label_material(key: str, label: dict, w_px: int, h_px: int) -> bpy.types.Material:
    path = TEX_DIR / "panneaux" / f"{key}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        label_image(label["text"], label.get("color", (30, 20, 20)), label.get("bg"), w_px, h_px,
                    font=label.get("font", "brush"), vertical=label.get("vertical", False)).save(path)
    if f"Panneau_{key}" in bpy.data.materials:
        return bpy.data.materials[f"Panneau_{key}"]
    m = bpy.data.materials.new(f"Panneau_{key}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.6
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    if label.get("glow"):
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = float(label["glow"])
    return m


def add_label(p: dict, collection, idx: int) -> None:
    """Panneau texte (SurfaceGui côté Roblox) : un plan texturé collé contre la face."""
    lab = p["label"]
    size = np.asarray(p["size"], float)
    R = np.asarray(p["rot"], float).reshape(3, 3)
    t = np.asarray(p["pos"], float)
    face = lab.get("face", "Front")
    name, corners, (ua, va) = next(f for f in BOX_FACES if f[0] == face)
    nrm = {"Top": (0, 1, 0), "Bottom": (0, -1, 0), "Front": (0, 0, -1), "Back": (0, 0, 1), "Left": (-1, 0, 0), "Right": (1, 0, 0)}[face]
    off = np.asarray(nrm, float) * 0.03
    pts = [C @ (R @ (np.asarray(c, float) * size / 2 + off) + t) for c in corners]
    # orientation du texte : coins dans l'ordre bas-gauche, haut-gauche, haut-droite, bas-droite vus de face
    w_st, h_st = size[ua], size[va]
    w_px, h_px = max(32, int(w_st * 48)), max(32, int(h_st * 48))
    sig = json.dumps([lab.get("text"), lab.get("color"), lab.get("bg"), lab.get("font"), lab.get("vertical"), w_px, h_px], ensure_ascii=False)
    key = hashlib.sha1(sig.encode()).hexdigest()[:12]
    mat = make_label_material(key, lab, w_px, h_px)
    me = bpy.data.meshes.new(f"panneau_{key}")
    me.from_pydata([tuple(v) for v in pts], [], [[0, 1, 2, 3]])
    uv = me.uv_layers.new(name="UVMap")
    # Texte lu de face : « droite » du spectateur = haut × normale
    n = np.asarray(nrm, float)
    up = np.array([0, 0, -1.0]) if face in ("Top", "Bottom") else np.array([0, 1.0, 0])
    right = np.cross(up, n)
    uvs = []
    for c in corners:
        c = np.asarray(c, float)
        uvs += [(c @ right + 1) / 2, (c @ up + 1) / 2]
    uv.data.foreach_set("uv", uvs)
    me.materials.append(mat)
    ob = bpy.data.objects.new(f"panneau_{key}", me)
    collection.objects.link(ob)


# --------------------------------------------------------------------------
# Scène
# --------------------------------------------------------------------------

def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def build(parts_path: Path, stud_scale: float = 1.0, split_depth: int = 2) -> dict:
    data = json.loads(Path(parts_path).read_text(encoding="utf-8"))
    parts = data["parts"]
    mat = make_material()
    root = bpy.data.collections.new("ZoneJujutsuKaisen")
    bpy.context.scene.collection.children.link(root)
    accs: dict[str, MeshAccum] = {}
    cols: dict[str, bpy.types.Collection] = {}
    labels = []
    for p in parts:
        if float(p.get("transparency", 0)) >= 0.99:
            continue  # repères invisibles (zone des œufs, couloir…) : rien à rendre
        g = p["group"] or "Divers"
        key = "/".join(g.split("/")[:split_depth])
        accs.setdefault(key, MeshAccum())
        add_part(accs[key], p, stud_scale)
        if p.get("label"):
            labels.append(p)
    tris = {}
    for key, acc in accs.items():
        top = key.split("/")[0]
        if top not in cols:
            cols[top] = bpy.data.collections.new(top)
            root.children.link(cols[top])
        ob = build_object(key.replace("/", "_"), acc, mat, cols[top])
        tris[key] = sum(len(f) - 2 for f in acc.faces)
    lab_col = bpy.data.collections.new("Panneaux")
    root.children.link(lab_col)
    for i, p in enumerate(labels):
        add_label(p, lab_col, i)
    return {"objects": len(accs), "parts": len(parts), "labels": len(labels), "tris": sum(tris.values()), "tris_by_object": tris}


CIEL_JOUR = ((0.74, 0.86, 0.98), (0.50, 0.72, 0.97), (0.16, 0.42, 0.86))
# Crépuscule « glycines » : horizon rose-violet, zénith bleu nuit, soleil bas et orangé
CIEL_CREPUSCULE = ((0.62, 0.40, 0.55), (0.30, 0.22, 0.48), (0.04, 0.05, 0.16))


def setup_world(sun_elev: float = 50, sun_azim: float = 215, strength: float = 1.0, view: str = "Standard", look: str = "None",
                exposure: float = -0.3, ciel=CIEL_JOUR, soleil=(1.0, 0.95, 0.86), soleil_energie: float = 4.2,
                ciel_force: float = 0.9) -> None:
    sc = bpy.context.scene
    world = bpy.data.worlds.new("Ciel")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    # Ciel « Roblox » : dégradé horizon clair → zénith bleu franc, pas de sol sombre sous l'horizon
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    cr.elements[0].position = 0.0
    cr.elements[0].color = (*ciel[0], 1)
    cr.elements[1].position = 0.55
    cr.elements[1].color = (*ciel[2], 1)
    mid = cr.elements.new(0.12)
    mid.color = (*ciel[1], 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = ciel_force * strength
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    sun_data = bpy.data.lights.new("Soleil", "SUN")
    sun_data.energy = soleil_energie * strength
    sun_data.angle = math.radians(1.2)
    sun_data.color = soleil
    sun = bpy.data.objects.new("Soleil", sun_data)
    sc.collection.objects.link(sun)
    # direction : élévation / azimut (azimut mesuré depuis +Y Blender, sens horaire vu du dessus)
    el, az = math.radians(sun_elev), math.radians(sun_azim)
    d = np.array([math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)])  # vers le soleil
    sun.rotation_mode = "QUATERNION"
    from mathutils import Vector
    sun.rotation_quaternion = Vector(tuple(-d)).to_track_quat("-Z", "Y")

    sc.view_settings.view_transform = view
    try:
        sc.view_settings.look = look
    except TypeError:
        pass
    sc.view_settings.exposure = exposure


def setup_brume(debut: float = 120.0, profondeur: float = 1300.0, maximum: float = 0.42, couleur=(0.74, 0.86, 0.98)) -> None:
    """Brume de distance (équivalent de Lighting.Atmosphere) : passe « mist » mélangée vers la couleur
    de l'horizon, sauf sur le ciel. Compositeur sur CPU (pas de GPU dans le conteneur)."""
    sc = bpy.context.scene
    sc.render.compositor_device = "CPU"
    sc.view_layers[0].use_pass_mist = True
    ms = sc.world.mist_settings
    ms.start, ms.depth, ms.falloff = debut, profondeur, "LINEAR"
    tree = bpy.data.node_groups.new("Brume", "CompositorNodeTree")
    sc.compositing_node_group = tree
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = tree.nodes.new("CompositorNodeRLayers")
    pas_ciel = tree.nodes.new("ShaderNodeMath")
    pas_ciel.operation = "LESS_THAN"
    pas_ciel.inputs[1].default_value = 0.999
    fac = tree.nodes.new("ShaderNodeMath")
    fac.operation = "MULTIPLY"
    fac2 = tree.nodes.new("ShaderNodeMath")
    fac2.operation = "MULTIPLY"
    fac2.inputs[1].default_value = maximum
    mix = tree.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = (*couleur, 1)
    out = tree.nodes.new("NodeGroupOutput")
    L = tree.links
    L.new(rl.outputs["Mist"], pas_ciel.inputs[0])
    L.new(rl.outputs["Mist"], fac.inputs[0])
    L.new(pas_ciel.outputs[0], fac.inputs[1])
    L.new(fac.outputs[0], fac2.inputs[0])
    L.new(fac2.outputs[0], mix.inputs["Factor"])
    L.new(rl.outputs["Image"], mix.inputs["A"])
    L.new(mix.outputs["Result"], out.inputs[0])


def add_camera(name: str, loc_rbx, target_rbx, fov: float = 70.0, lens_shift=(0, 0)) -> bpy.types.Object:
    """Caméra placée en coordonnées Roblox ; `fov` vertical en degrés comme Camera.FieldOfView."""
    from mathutils import Vector
    cam = bpy.data.cameras.new(name)
    cam.sensor_fit = "VERTICAL"
    cam.angle_y = math.radians(fov)
    cam.clip_start = 0.5
    cam.clip_end = 6000
    cam.shift_x, cam.shift_y = lens_shift
    ob = bpy.data.objects.new(name, cam)
    bpy.context.scene.collection.objects.link(ob)
    loc = Vector(tuple(C @ np.asarray(loc_rbx, float)))
    tgt = Vector(tuple(C @ np.asarray(target_rbx, float)))
    ob.location = loc
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = (tgt - loc).to_track_quat("-Z", "Y")
    return ob


def render(cam: bpy.types.Object, path: Path, res=(1600, 900), samples: int = 48) -> None:
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 1
    sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def export(blend: Path | None = None, glb: Path | None = None, fbx: Path | None = None) -> None:
    if blend:
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    if glb:
        bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", export_yup=True, export_apply=True,
                                  export_vertex_color="ACTIVE", export_all_vertex_colors=True)
    if fbx:
        bpy.ops.export_scene.fbx(filepath=str(fbx), apply_unit_scale=True, global_scale=1.0, axis_forward="-Z", axis_up="Y",
                                 mesh_smooth_type="FACE", path_mode="COPY", embed_textures=True)
