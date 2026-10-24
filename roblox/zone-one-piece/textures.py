"""Textures générées : la texture « stud » (calque RGBA) et les panneaux de texte.

La texture stud est un calque : transparente là où la couleur de la pièce doit rester pure,
blanche ou noire (semi-transparente) pour les reflets et les ombres du stud. Dans Roblox, un
objet Texture posé sur une face se superpose à Part.Color : une seule image sert donc pour
toutes les couleurs de la carte. Le rendu Blender applique exactement le même mélange.
"""

from __future__ import annotations

import urllib.request
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
TEX_DIR = HERE / "textures"
FONT_CACHE = HERE / ".cache" / "fonts"

FONTS = {
    # Pinceau, pour les grands signes (porte, enseignes) — OFL, google/fonts
    "brush": ("YujiSyuku-Regular.ttf", "https://raw.githubusercontent.com/google/fonts/main/ofl/yujisyuku/YujiSyuku-Regular.ttf"),
    # Gothique lisible pour les petites enseignes
    "sans": ("NotoSansJP[wght].ttf", "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"),
}


def font_path(key: str) -> Path:
    name, url = FONTS[key]
    path = FONT_CACHE / name
    if not path.exists():
        FONT_CACHE.mkdir(parents=True, exist_ok=True)
        print(f"téléchargement de la police {name}…")
        urllib.request.urlretrieve(url, path)
    return path


def _disc(n: int, cx: float, cy: float, r: float, soft: float = 1.0) -> np.ndarray:
    y, x = np.mgrid[0:n, 0:n] + 0.5
    d = np.hypot(x - cx, y - cy)
    return np.clip((r - d) / soft + 0.5, 0, 1)


def _rounded_square(n: int, half: float, radius: float, cx: float, cy: float) -> np.ndarray:
    """Distance signée (négative dedans) à un carré arrondi centré en (cx, cy), en pixels."""
    y, x = np.mgrid[0:n, 0:n] + 0.5
    qx = np.abs(x - cx) - (half - radius)
    qy = np.abs(y - cy) - (half - radius)
    outside = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
    inside = np.minimum(np.maximum(qx, qy), 0)
    return outside + inside - radius


def stud_tile(n: int = 128) -> Image.Image:
    """Stud Roblox actuel : petit carré arrondi (≈ 0,48 stud), bord clair en haut à droite,
    bord sombre en bas à gauche, dessus plat. C'est l'aspect de SurfaceType.Studs sur Plastic,
    ce qui rend les aperçus Blender fidèles au jeu."""
    c = n / 2
    sd = _rounded_square(n, n * 0.24, n * 0.07, c, c)
    body = np.clip(0.5 - sd / 1.2, 0, 1)
    rim = np.clip(1 - np.abs(sd + n * 0.025) / (n * 0.03), 0, 1)
    y, x = np.mgrid[0:n, 0:n] + 0.5
    # côté du bord : +1 en haut à droite (éclairé), -1 en bas à gauche (ombre)
    side = np.clip(((x - c) - (y - c)) / (n * 0.24), -1, 1)
    hi = rim * np.clip(side, 0, 1)
    lo = rim * np.clip(-side, 0, 1)
    # ombre très légère qui déborde en bas à gauche
    sh = _rounded_square(n, n * 0.24, n * 0.07, c - n * 0.03, c + n * 0.03)
    drop = np.clip(0.5 - sh / (n * 0.03), 0, 1) * (1 - body)
    white = np.clip(hi * 0.42 + body * 0.07, 0, 1)
    black = np.clip(lo * 0.34 + drop * 0.16, 0, 1)
    alpha = np.clip(white + black, 0, 1)
    lum = np.where(alpha > 1e-4, white / np.maximum(alpha, 1e-4), 0)
    rgb = np.repeat((lum * 255)[..., None], 3, axis=2)
    return Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")


def stud_colormap(tile: Image.Image) -> Image.Image:
    """Version opaque en niveaux de gris (multiplicateur) pour un MaterialVariant teinté par Part.Color."""
    a = np.asarray(tile, float) / 255
    base = 0.86
    val = base * (1 - a[..., 3]) + a[..., 0] * a[..., 3]
    val = np.clip(val / base * 0.86 + (1 - 0.86) * 0, 0, 1)
    g = (val * 255).astype(np.uint8)
    return Image.fromarray(np.dstack([g, g, g]), "RGB")


def stud_tile_lego(n: int = 256) -> Image.Image:
    """Variante « brique LEGO » : stud rond éclairé du haut à gauche (non utilisée par défaut)."""
    c = n / 2
    r = n * 0.30
    y, x = np.mgrid[0:n, 0:n] + 0.5
    ang = np.arctan2(y - c, x - c)  # 0 = droite, +pi/2 = bas (image)
    d = np.hypot(x - c, y - c)

    # Ombre portée vers le bas à droite (douce)
    shadow = Image.fromarray((_disc(n, c + n * 0.05, c + n * 0.06, r * 1.02) * 255).astype(np.uint8))
    shadow = np.asarray(shadow.filter(ImageFilter.GaussianBlur(n * 0.025)), float) / 255
    body = _disc(n, c, c, r)
    shadow = shadow * (1 - body)

    # Anneau du bord : clair en haut à gauche, sombre en bas à droite
    rim = np.clip(1 - np.abs(d - r * 0.93) / (n * 0.035), 0, 1) * body
    light_dir = -3 * np.pi / 4  # haut gauche
    facing = np.cos(ang - light_dir)  # 1 face à la lumière, -1 à l'opposé
    hi = rim * np.clip(facing, 0, 1) ** 1.5
    lo = rim * np.clip(-facing, 0, 1) ** 1.2

    # Petit reflet en croissant sur le dessus du stud
    spec = _disc(n, c - r * 0.32, c - r * 0.32, r * 0.42, soft=n * 0.04) * (1 - _disc(n, c - r * 0.18, c - r * 0.18, r * 0.42, soft=n * 0.04))
    spec *= body

    # Joint très léger entre tuiles (lit les surfaces de loin)
    edge = np.minimum.reduce([x, y, n - x, n - y])
    seam = np.clip(1 - edge / (n * 0.012), 0, 1)

    white = np.clip(hi * 0.55 + spec * 0.22, 0, 1)
    black = np.clip(lo * 0.38 + shadow * 0.26 + seam * 0.10, 0, 1)
    alpha = np.clip(white + black, 0, 1)
    # Couleur prémultipliée → couleur droite : blanc là où domine le reflet
    lum = np.where(alpha > 1e-4, white / np.maximum(alpha, 1e-4), 0)
    rgb = np.repeat((lum * 255)[..., None], 3, axis=2)
    rgba = np.dstack([rgb, alpha * 255]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def write_stud_textures() -> dict:
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    tile = stud_tile(128)
    if not (TEX_DIR / "stud.png").exists() or (TEX_DIR / "stud.png").read_bytes() != _png_bytes(tile):
        tile.save(TEX_DIR / "stud.png")
        stud_colormap(tile).save(TEX_DIR / "stud-colormap.png")
        # Aperçu : 6 × 4 studs sur quelques couleurs de la palette
        swatches = ["#E6D2A2", "#C94A36", "#78C043", "#F3EEE2", "#3D73B8", "#DDA56B"]
        prev = Image.new("RGB", (6 * 128, 4 * 128 * len(swatches) // 3))
        for i, col in enumerate(swatches):
            ox, oy = (i % 3) * 256, (i // 3) * 512
            base = Image.new("RGBA", (256, 512), col)
            for ty in range(4):
                for tx in range(2):
                    base.alpha_composite(tile, (tx * 128, ty * 128))
            prev.paste(base.convert("RGB"), (ox, oy))
        prev.save(TEX_DIR / "stud-apercu.png")
    return {"stud": str(TEX_DIR / "stud.png")}


def _png_bytes(im: Image.Image) -> bytes:
    import io
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


@lru_cache(maxsize=None)
def _font(key: str, size: int) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(font_path(key)), size)
    if key == "sans":
        try:
            f.set_variation_by_axes([800])
        except Exception:
            pass
    return f


def glyph_mask(text: str, cells: int, font: str = "sans", vertical: bool = False, pad: float = 0.04,
               bold: int = 0, threshold: float = 0.3) -> np.ndarray:
    """Pixelise un texte sur une grille `cells` × `cells` (par caractère) : True = pixel plein.

    Chaque caractère est recadré sur son encre réelle puis agrandi pour remplir sa case ;
    `bold` épaissit les traits (en pixels de case) pour qu'ils survivent à la pixelisation.
    """
    chars = list(text)
    big = cells * 24
    f = _font(font, 400)
    w = big * (1 if vertical else len(chars))
    h = big * (len(chars) if vertical else 1)
    img = Image.new("L", (w, h), 0)
    for i, ch in enumerate(chars):
        ox, oy = (0, i * big) if vertical else (i * big, 0)
        tmp = Image.new("L", (560, 560), 0)
        ImageDraw.Draw(tmp).text((60, 40), ch, font=f, fill=255)
        bb = tmp.getbbox()
        if not bb:
            continue
        tmp = tmp.crop(bb)
        inner = big * (1 - 2 * pad)
        s = min(inner / tmp.width, inner / tmp.height)
        tmp = tmp.resize((max(1, int(tmp.width * s)), max(1, int(tmp.height * s))), Image.LANCZOS)
        if bold:
            tmp = tmp.filter(ImageFilter.MaxFilter(2 * int(bold * 24 / 2) + 1))
        img.paste(tmp, (ox + (big - tmp.width) // 2, oy + (big - tmp.height) // 2))
    gw = cells * (1 if vertical else len(chars))
    gh = cells * (len(chars) if vertical else 1)
    small = img.resize((gw, gh), Image.BOX)
    return np.asarray(small) > threshold * 255


def mask_rects(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Découpe gloutonne d'un masque en rectangles (x, y, w, h) : moins de pièces Roblox."""
    m = mask.copy()
    h, w = m.shape
    out = []
    for y in range(h):
        x = 0
        while x < w:
            if not m[y, x]:
                x += 1
                continue
            x1 = x
            while x1 < w and m[y, x1]:
                x1 += 1
            y1 = y + 1
            while y1 < h and m[y1, x:x1].all():
                y1 += 1
            m[y:y1, x:x1] = False
            out.append((x, y, x1 - x, y1 - y))
            x = x1
    return out


def label_image(text: str, fg, bg, w_px: int, h_px: int, font: str = "brush", vertical: bool = False) -> Image.Image:
    """Image d'un panneau de texte, pour les rendus Blender (Roblox utilise un SurfaceGui)."""
    img = Image.new("RGBA", (w_px, h_px), tuple(bg) + (255,) if bg is not None else (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    n = len(text)
    if vertical:
        size = int(min(w_px * 0.8, h_px * 0.86 / max(n, 1)))
    else:
        # texte latin (« VITESSE CONSEILLÉE : 200 ») : on mesure la vraie largeur au lieu de compter
        # un cadratin par caractère, comme le TextScaled de Roblox
        size = int(h_px * 0.72)
        tw = d.textbbox((0, 0), text, font=_font(font, max(size, 8)))
        if tw[2] - tw[0] > w_px * 0.92:
            size = int(size * w_px * 0.92 / (tw[2] - tw[0]))
    f = _font(font, max(size, 8))
    if vertical:
        step = h_px / n
        for i, ch in enumerate(text):
            bb = d.textbbox((0, 0), ch, font=f)
            d.text(((w_px - (bb[2] - bb[0])) / 2 - bb[0], step * i + (step - (bb[3] - bb[1])) / 2 - bb[1]), ch, font=f, fill=tuple(fg))
    else:
        bb = d.textbbox((0, 0), text, font=f)
        d.text(((w_px - (bb[2] - bb[0])) / 2 - bb[0], (h_px - (bb[3] - bb[1])) / 2 - bb[1]), text, font=f, fill=tuple(fg))
    return img


if __name__ == "__main__":
    print(write_stud_textures())
    m = glyph_mask("あ", 14)
    print("\n".join("".join("#" if v else "." for v in row) for row in m))
    print(len(mask_rects(m)), "rectangles")
