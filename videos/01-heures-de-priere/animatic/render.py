#!/usr/bin/env python3
"""Animatic « Pourquoi l'heure de la prière change chaque jour ? »

Prototype de mise en scène, pas la vidéo finale :
- monde en pixel art procédural (grille 216 × 384, agrandie ×5 en 1080 × 1920) ;
- textes en Poppins (pleine résolution), étiquettes « HUD » en VT323, arabe en Amiri ;
- identité Nuraq : fond #1D1D1D, violet #6157F8, lavande, blanc cassé ;
- ambiance sonore synthétisée (vent, oiseaux, grillons, petits signaux) : aucune musique ;
- sous-titres incrustés = texte de la voix off.

Usage :
    python3 render.py                       # rend animatic.mp4 + sous-titres.srt (sans voix)
    python3 render.py --voix voix           # cale tout sur la voix générée par voix.py
                                            #   → video-voix-off.mp4 + sous-titres-voix-off.srt
    python3 render.py --stills 2,24,38      # images fixes PNG pour contrôle
    python3 render.py --no-subs             # sans sous-titres incrustés

Dépendances : Python 3.10+, numpy, Pillow (avec libraqm pour l'arabe), ffmpeg.
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing
import os
import re
import subprocess
import sys
import urllib.request
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONT_CACHE = HERE / ".cache" / "fonts"

W, H, FPS = 1080, 1920, 30
PX = 5
LW, LH = W // PX, H // PX  # 216 × 384
DURATION = 86.0

# ---------------------------------------------------------------------------
# Identité Nuraq
# ---------------------------------------------------------------------------

INK = "#1D1D1D"
VIOLET = "#6157F8"
LAVENDER = "#A9A3FF"
LAVENDER_LIGHT = "#DAD7FF"
OFFWHITE = "#F3F0EA"
CORAL = "#E8917C"  # lueur rouge du crépuscule : touche ponctuelle, jamais dominante
TWILIGHT_WHITE = "#D8D4F2"


def rgb(h: str) -> np.ndarray:
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)


def mix(a, b, k):
    return a + (b - a) * k


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ramp(t, t0, t1):
    if t1 <= t0:
        return float(t >= t0)
    return clamp((t - t0) / (t1 - t0))


# ---------------------------------------------------------------------------
# Polices
# ---------------------------------------------------------------------------

GOOGLE_FONTS = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FONTS = {
    "xb": "poppins/Poppins-ExtraBold.ttf",
    "b": "poppins/Poppins-Bold.ttf",
    "sb": "poppins/Poppins-SemiBold.ttf",
    "m": "poppins/Poppins-Medium.ttf",
    "pixel": "vt323/VT323-Regular.ttf",
    "ar": "amiri/Amiri-Bold.ttf",
    "ar-r": "amiri/Amiri-Regular.ttf",
}


def font_path(key: str) -> Path:
    rel = FONTS[key]
    path = FONT_CACHE / Path(rel).name
    if not path.exists():
        FONT_CACHE.mkdir(parents=True, exist_ok=True)
        print(f"téléchargement de {rel}…", file=sys.stderr)
        urllib.request.urlretrieve(GOOGLE_FONTS + rel, path)
    return path


@lru_cache(maxsize=None)
def font(key: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(font_path(key)), size, layout_engine=ImageFont.Layout.RAQM)


# ---------------------------------------------------------------------------
# Interpolation douce de l'horloge du ciel (PCHIP, monotone)
# ---------------------------------------------------------------------------

class Pchip:
    def __init__(self, keys):
        self.x = np.array([k[0] for k in keys], dtype=float)
        self.y = np.array([k[1] for k in keys], dtype=float)
        h = np.diff(self.x)
        d = np.diff(self.y) / h
        m = np.zeros_like(self.y)
        m[0], m[-1] = d[0], d[-1]
        for i in range(1, len(self.y) - 1):
            if d[i - 1] * d[i] <= 0:
                m[i] = 0.0
            else:
                w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
        self.m = m

    def __call__(self, t):
        x, y, m = self.x, self.y, self.m
        if t <= x[0]:
            return float(y[0])
        if t >= x[-1]:
            return float(y[-1])
        i = int(np.searchsorted(x, t)) - 1
        h = x[i + 1] - x[i]
        s = (t - x[i]) / h
        h00 = 2 * s ** 3 - 3 * s ** 2 + 1
        h10 = s ** 3 - 2 * s ** 2 + s
        h01 = -2 * s ** 3 + 3 * s ** 2
        h11 = s ** 3 - s ** 2
        return float(h00 * y[i] + h10 * h * m[i] + h01 * y[i + 1] + h11 * h * m[i + 1])


# ---------------------------------------------------------------------------
# Modèle solaire stylisé (journée symétrique 6 h → 18 h)
# ---------------------------------------------------------------------------

HORIZON = 226          # base de la ligne d'horizon (grille basse résolution)
FLOOR = 276            # sol de la terrasse au premier plan
ARC_X0, ARC_X1, ARC_TOP = 14, 202, 152
MAX_ALT = 60.0
NIGHT_RATE = 9.0       # degrés sous l'horizon par heure (stylisé)
POST_X, POST_H = 150, 30


def solar(u: float):
    """Renvoie (altitude en degrés, s) pour une heure stylisée u (peut dépasser 24)."""
    h = u % 24
    if 6 <= h <= 18:
        s = (h - 6) / 12
        alt = MAX_ALT * math.sin(math.pi * s)
    else:
        since_sunset = h - 18 if h > 18 else h + 6
        dist = min(since_sunset, 12 - since_sunset)
        alt = -min(40.0, NIGHT_RATE * dist)
        s = (h - 6) / 12 if h > 18 else (h - 6) / 12
    return alt, s


def sun_xy(s: float):
    x = ARC_X0 + (ARC_X1 - ARC_X0) * s
    y = HORIZON - (HORIZON - ARC_TOP) * math.sin(math.pi * s)
    return x, y


def shadow_len(alt: float) -> float:
    if alt <= 0.5:
        return 999.0
    return POST_H / math.tan(math.radians(alt))


NOON_SHADOW = shadow_len(MAX_ALT)


def u_for_shadow(target: float) -> float:
    """Heure stylisée de l'après-midi où l'ombre atteint `target` pixels."""
    lo, hi = 12.0, 17.99
    for _ in range(60):
        mid = (lo + hi) / 2
        if shadow_len(solar(mid)[0]) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


U_ASR_1 = 24 + u_for_shadow(NOON_SHADOW + POST_H)       # ombre = objet + ombre de midi
U_ASR_2 = 24 + u_for_shadow(NOON_SHADOW + 2 * POST_H)   # avis d'Abou Hanifa : deux fois
U_MAGHRIB = 24 + 18.1
U_RED_GONE = 24 + 18 + 12 / NIGHT_RATE    # ≈ −12° : la lueur rouge s'éteint
U_WHITE_GONE = 24 + 18 + 18 / NIGHT_RATE  # ≈ −18° : la lueur blanche s'éteint
U_DAWN = 24 + 6 - 18 / NIGHT_RATE         # ≈ −18° : l'aube apparaît

# Horloge du ciel en fonction du temps de la vidéo (secondes → heure stylisée)
SKY_CLOCK = Pchip([
    (0.0, 17.40), (3.4, 17.5), (9.4, 17.62), (11.6, 17.68), (13.9, 18.02),
    (17.7, 22.2), (21.4, U_DAWN - 0.45), (22.8, U_DAWN), (28.8, 29.93),
    (31.0, 36.05), (34.4, 36.5), (38.6, U_ASR_1), (42.6, U_ASR_2), (45.0, 40.95),
    (47.0, U_MAGHRIB), (48.4, 42.35), (51.6, U_RED_GONE), (54.0, U_WHITE_GONE),
    (56.6, 44.3),
])

# Couleurs du ciel selon l'altitude du soleil : (altitude, haut du ciel, horizon)
SKY_KEYS = [
    (-40, "#0D0C17", "#15132A"),
    (-18, "#100E1D", "#1C1934"),
    (-12, "#13112A", "#272150"),
    (-6, "#1A163B", "#433479"),
    (-2, "#221C4D", "#664896"),
    (1, "#29285F", "#B07391"),
    (5, "#2F316D", "#CB968F"),
    (12, "#353B83", "#A6A2D6"),
    (25, "#39418D", "#9AA0DD"),
    (60, "#3C4694", "#A2A9E3"),
]


def sky_colors(alt: float):
    keys = SKY_KEYS
    if alt <= keys[0][0]:
        return rgb(keys[0][1]), rgb(keys[0][2])
    for (a0, t0, h0), (a1, t1, h1) in zip(keys, keys[1:]):
        if alt <= a1:
            k = (alt - a0) / (a1 - a0)
            return mix(rgb(t0), rgb(t1), k), mix(rgb(h0), rgb(h1), k)
    return rgb(keys[-1][1]), rgb(keys[-1][2])


def warm_glow(alt):
    """Lueur rouge-orangée : s'éteint vers −12°."""
    if alt < -2:
        return smooth((alt + 12) / 10)
    if alt <= 2:
        return 1.0
    return 1 - smooth((alt - 2) / 10)


def white_glow(alt):
    """Lueur blanche : persiste jusque vers −18°."""
    if alt < -10:
        return smooth((alt + 18) / 8)
    if alt <= -4:
        return 1.0
    return 1 - smooth((alt + 4) / 6)


BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) + 0.5) / 16
BAYER_LR = np.tile(BAYER4, (LH // 4, LW // 4))
YY, XX = np.mgrid[0:LH, 0:LW].astype(np.float32)


def dither(img: np.ndarray, step: float = 7.0) -> np.ndarray:
    return np.floor(img / step + BAYER_LR[..., None]) * step


# ---------------------------------------------------------------------------
# Décor procédural (généré une fois)
# ---------------------------------------------------------------------------

rng = np.random.default_rng(7)

STARS = [
    (int(rng.integers(2, LW - 2)), int(rng.integers(3, 200)), float(rng.uniform(0.35, 1.0)),
     float(rng.uniform(0.15, 0.55)), float(rng.uniform(0, 6.28)), bool(rng.random() < 0.12))
    for _ in range(85)
]


GAP_X = 172


def build_far_skyline():
    top = np.zeros(LW, dtype=np.int32)  # hauteur au-dessus de l'horizon
    windows = []
    x = 0
    while x < LW:
        w = int(rng.integers(6, 15))
        h = int(rng.integers(7, 20))
        if x >= GAP_X:  # trouée à l'ouest : parc, cimes basses, le soleil s'y couche
            top[x:] = 2
            for tx in range(x, LW, 5):
                th = int(rng.integers(3, 6))
                top[tx:tx + 4] = np.maximum(top[tx:tx + 4], [th - 1, th, th, th - 1][:len(top[tx:tx + 4])])
            break
        top[x:x + w] = np.maximum(top[x:x + w], h)
        for wy in range(HORIZON - h + 3, HORIZON + 6, 3):
            for wx in range(x + 2, min(LW, x + w - 1), 3):
                if rng.random() < 0.33:
                    windows.append((wx, wy, float(rng.random()), bool(rng.random() < 0.22)))
        x += w
    # mosquée : coupole + minaret, en silhouette (architecture seulement)
    dome_cx, dome_r, base = 56, 10, 9
    for x in range(36, 77):
        top[x] = max(top[x], base)
    for x in range(dome_cx - dome_r, dome_cx + dome_r + 1):
        top[x] = max(top[x], base + int(round(math.sqrt(max(0, dome_r ** 2 - (x - dome_cx) ** 2)))))
    top[dome_cx] = max(top[dome_cx], base + dome_r + 3)
    for x in range(78, 82):
        top[x] = max(top[x], 40)
    for x in range(77, 83):
        top[x] = max(top[x], 31)
    top[79:81] = 44
    windows = [w for w in windows if not 34 <= w[0] <= 84]
    return top, windows


FAR_TOP, FAR_WINDOWS = build_far_skyline()
MINARET_BALCONY = [(x, HORIZON - 32) for x in (77, 82)]


def build_near_roofs():
    top = np.full(LW, 40, dtype=np.int32)  # ligne de toit (y)
    chimneys, dormers = [], []
    x = -int(rng.integers(0, 10))
    while x < LW:
        w = int(rng.integers(24, 42))
        ridge = int(rng.integers(HORIZON + 12, HORIZON + 20))
        for xi in range(max(0, x), min(LW, x + w)):
            edge = min(xi - x, x + w - 1 - xi)
            top[xi] = ridge + max(0, 3 - edge) * 2
        cx = x + int(rng.integers(4, max(5, w - 6)))
        chimneys.append((cx, ridge - 5))
        for dx in range(6, w - 6, 9):
            dormers.append((x + dx, ridge + 9, float(rng.random())))
        x += w
    return top, chimneys, dormers


NEAR_TOP, CHIMNEYS, DORMERS = build_near_roofs()


def make_cloud(w, h, seed):
    r = np.random.default_rng(seed)
    m = np.zeros((h, w), dtype=bool)
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(6):
        cx, cy = r.uniform(w * 0.2, w * 0.8), r.uniform(h * 0.45, h * 0.75)
        rx, ry = r.uniform(w * 0.15, w * 0.32), r.uniform(h * 0.25, h * 0.45)
        m |= ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
    m[int(h * 0.82):, :] = False
    return m


CLOUDS = [(make_cloud(40, 12, 1), 20.0, 46), (make_cloud(30, 10, 2), 120.0, 78),
          (make_cloud(46, 13, 3), 200.0, 30), (make_cloud(26, 9, 4), 300.0, 104)]


# ---------------------------------------------------------------------------
# Rendu du monde (basse résolution)
# ---------------------------------------------------------------------------

def render_world(t: float, alt: float, s: float, show_sun=True, show_post=True, u=None):
    top_c, hor_c = sky_colors(alt)
    k = np.clip(YY / HORIZON, 0, 1) ** 1.5
    img = top_c[None, None, :] * (1 - k[..., None]) + hor_c[None, None, :] * k[..., None]

    sx, sy = sun_xy(s)
    gx = min(max(sx, -30), LW + 30)
    near = np.exp(-np.clip(HORIZON - YY, 0, None) / 26.0)
    wg = warm_glow(alt)
    if wg > 0.01:
        g = wg * 0.62 * np.exp(-((XX - gx) / 72.0) ** 2) * near
        img = img + (rgb(CORAL) - img) * g[..., None]
    vg = white_glow(alt)
    if vg > 0.01:
        # lumière blanche étalée le long de l'horizon (vraie aube / crépuscule blanc)
        above = np.clip(HORIZON - YY, 0, None)
        g = vg * (0.42 * np.exp(-above / 20.0) + 0.35 * np.exp(-above / 3.0)) \
            * np.exp(-((XX - gx) / 150.0) ** 2)
        img = img + (rgb(TWILIGHT_WHITE) - img) * np.clip(g, 0, 0.85)[..., None]

    # étoiles
    night = smooth((-alt - 5) / 11)
    if night > 0.01:
        for x, y, b, f, ph, big in STARS:
            a = night * b * (0.72 + 0.28 * math.sin(6.283 * f * t + ph))
            c = rgb("#ECE9FF")
            img[y, x] = mix(img[y, x], c, a)
            if big and a > 0.45:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    img[y + dy, x + dx] = mix(img[y + dy, x + dx], rgb(LAVENDER), a * 0.45)

    # nuages (dérive par pas entiers de pixel)
    day = smooth((alt + 4) / 14)
    cloud_c = mix(mix(rgb("#2B2747"), rgb("#E3A28F"), warm_glow(alt) * 0.8), rgb("#C3C7F0"), day)
    for mask, x0, y0 in CLOUDS:
        x = int((x0 - t * 2.2) % (LW + 60)) - 50
        h_, w_ = mask.shape
        for yy in range(h_):
            for xx in np.nonzero(mask[yy])[0]:
                X = x + xx
                if 0 <= X < LW:
                    edge = yy == 0 or not mask[yy - 1, xx]
                    a = 0.30 + 0.20 * day + (0.15 if edge else 0.0)
                    img[y0 + yy, X] = mix(img[y0 + yy, X], cloud_c, a)

    # soleil + halo tramé
    if show_sun and sy < HORIZON + 8:
        core = mix(rgb("#FFB97A"), rgb("#FFE6AE"), smooth(alt / 18))
        ix, iy = int(round(sx)), int(round(sy))
        d2 = (XX - ix) ** 2 + (YY - iy) ** 2
        halo = (d2 <= 13 ** 2) & (d2 > 7 ** 2)
        halo_k = np.where(d2 <= 10 ** 2, 0.30, 0.14) * (BAYER_LR > 0.35)
        img = np.where(halo[..., None], mix(img, core, halo_k[..., None]), img)
        img = np.where((d2 <= 6 ** 2)[..., None], core, img)
        img = np.where((d2 <= 3 ** 2)[..., None], mix(core, rgb("#FFF6DD"), 0.6), img)

    img = dither(img)

    # silhouette lointaine (perspective atmosphérique)
    far_c = mix(hor_c, rgb("#14121F"), 0.70)
    far_mask = YY >= (HORIZON - FAR_TOP[None, :])
    img = np.where(far_mask[..., None], far_c, img)
    lit = smooth((-alt - 2) / 8)
    for x, y in MINARET_BALCONY:
        img[y, x] = mix(far_c, rgb(LAVENDER), 0.25)
    if lit > 0:
        for x, y, thr, lav in FAR_WINDOWS:
            if thr < lit * 0.9:
                img[y, x] = mix(far_c, rgb(LAVENDER if lav else "#F4C77E"), 0.75)

    # toits proches
    near_c = rgb("#110F18")
    rim = mix(near_c, top_c * 1.5 + 20, 0.55)
    near_mask = YY >= NEAR_TOP[None, :]
    img = np.where(near_mask[..., None], near_c, img)
    for x in range(LW):
        img[NEAR_TOP[x], x] = rim
    for cx, cy in CHIMNEYS:
        if 0 <= cx < LW - 3:
            img[cy:cy + 6, cx:cx + 3] = near_c
            img[cy, cx:cx + 3] = rim
    if lit > 0:
        for dx, dy, thr in DORMERS:
            if 0 <= dx < LW - 2 and thr < lit * 0.8:
                img[dy:dy + 2, dx:dx + 2] = rgb("#E9B56E")

    # terrasse au premier plan (le sol s'éclaire avec le ciel pour que l'ombre se lise)
    floor_c = mix(rgb("#2A2638"), hor_c, 0.18 + 0.30 * day)
    img[FLOOR:FLOOR + 5] = floor_c
    img[FLOOR] = mix(floor_c, rgb(OFFWHITE), 0.10 + 0.12 * day)
    img[FLOOR + 5] = rgb("#0F0E15")
    img[FLOOR + 6:] = rgb("#16141D")
    # façade de l'immeuble : fenêtres sobres (zone couverte par l'interface TikTok)
    for i, wy in enumerate(range(FLOOR + 16, LH - 8, 30)):
        for j, wx in enumerate(range(10 + (i % 2) * 12, LW - 10, 26)):
            img[wy - 1:wy + 10, wx - 1:wx + 7] = rgb("#1D1A27")
            on = lit > 0 and ((i * 7 + j * 13) % 10) / 10 < lit * 0.35
            glass_c = mix(rgb("#E9B56E"), rgb("#16141D"), 0.55) if on else mix(rgb("#0F0E15"), top_c, 0.18)
            img[wy:wy + 9, wx:wx + 6] = glass_c
            img[wy + 4, wx:wx + 6] = rgb("#1D1A27")

    # bâton (gnomon) et son ombre
    if show_post:
        if u is not None and (u % 24) >= 12.0 and alt > 1.0:
            L = shadow_len(alt)
            appear = smooth(((u % 24) - 12.0) / 0.35)
            x0 = int(round(POST_X - min(L, 140)))
            mask = (BAYER_LR[FLOOR + 1:FLOOR + 4, x0:POST_X] < appear)
            seg = img[FLOOR + 1:FLOOR + 4, x0:POST_X]
            img[FLOOR + 1:FLOOR + 4, x0:POST_X] = np.where(mask[..., None], rgb("#0E0C15"), seg)
        img[FLOOR - POST_H:FLOOR, POST_X] = rgb("#8C86C4")
        img[FLOOR - POST_H:FLOOR, POST_X + 1] = rgb("#D6D1FA")
        img[FLOOR - 2:FLOOR, POST_X - 1:POST_X + 3] = rgb("#6A6499")
    return img


# ---------------------------------------------------------------------------
# Couche « HUD » pixel (RGBA basse résolution) : piste, crochets, schémas
# ---------------------------------------------------------------------------

class Hud:
    def __init__(self):
        self.rgb = np.zeros((LH, LW, 3), dtype=np.float32)
        self.a = np.zeros((LH, LW), dtype=np.float32)

    def px(self, x, y, color, a=1.0):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < LW and 0 <= y < LH and a > 0:
            c = rgb(color) if isinstance(color, str) else color
            old = self.a[y, x]
            na = a + old * (1 - a)
            if na > 0:
                self.rgb[y, x] = (c * a + self.rgb[y, x] * old * (1 - a)) / na
            self.a[y, x] = na

    def line(self, x0, y0, x1, y1, color, a=1.0, dotted=0):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n):
            if dotted and i % dotted:
                continue
            k = i / max(1, n - 1)
            self.px(x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, color, a)

    def diamond(self, cx, cy, r, color, a=1.0, outline_only=False):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                d = abs(dx) + abs(dy)
                if d <= r and (not outline_only or d == r):
                    self.px(cx + dx, cy + dy, color, a)

    def disc(self, cx, cy, r, color, a=1.0):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r + 0.5:
                    self.px(cx + dx, cy + dy, color, a)


TRACK_Y = 54
TRACK_X = [34, 71, 108, 145, 182]
PRAYERS = ["FAJR", "DHUHR", "ASR", "MAGHRIB", "ISHA"]
NODE_TIMES = [22.8, 31.2, 38.6, 47.0, 51.6]
OUTRO_NODE_TIMES = [80.9, 81.15, 81.4, 81.65, 81.9]


def node_lit_time(i, t):
    return OUTRO_NODE_TIMES[i] if t >= 80.6 else NODE_TIMES[i]


def draw_track(hud: Hud, t: float, k: float):
    for i in range(4):
        x0, x1 = TRACK_X[i] + 5, TRACK_X[i + 1] - 5
        lit = t >= node_lit_time(i + 1, t)
        for x in range(x0, x1 + 1, 2):
            hud.px(x, TRACK_Y, "#8F88FF" if lit else "#3D3868", k)
    for i, x in enumerate(TRACK_X):
        tl = node_lit_time(i, t)
        if t >= tl:
            pulse = ramp(t, tl, tl + 0.7)
            if pulse < 1:
                r = 4 + int(pulse * 5)
                hud.diamond(x, TRACK_Y, r, LAVENDER, k * (1 - pulse) * 0.8, outline_only=True)
            hud.diamond(x, TRACK_Y, 3, LAVENDER, k)
            hud.diamond(x, TRACK_Y, 2, VIOLET, k)
            hud.px(x, TRACK_Y, LAVENDER_LIGHT, k)
        else:
            hud.diamond(x, TRACK_Y, 3, "#4B4675", k * 0.9, outline_only=True)
            hud.px(x, TRACK_Y, "#4B4675", k * 0.9)


def draw_brackets(hud: Hud, cx, cy, t, t0, k):
    if t < t0 or (t - t0 < 0.5 and int((t - t0) * 8) % 2):
        return
    r = 11
    for sx_ in (-1, 1):
        for sy_ in (-1, 1):
            x, y = cx + sx_ * r, cy + sy_ * r
            for i in range(4):
                hud.px(x - sx_ * i, y, LAVENDER_LIGHT, k)
                hud.px(x, y - sy_ * i, LAVENDER_LIGHT, k)


def draw_arc_path(hud: Hud, x0, x1, top, k, color=LAVENDER, progress=1.0, step=4, head=False):
    n = int((x1 - x0) * progress)
    last = None
    for i in range(0, n + 1):
        x = x0 + i
        s = (x - x0) / (x1 - x0)
        y = HORIZON - (HORIZON - top) * math.sin(math.pi * s)
        in_sky = 0 <= x < LW and y < HORIZON - FAR_TOP[int(x)] - 1
        if i % step == 0 and in_sky:
            hud.px(x, y, color, k)
        last = (x, y)
    if head and last and progress < 1:
        hud.disc(last[0], last[1], 3, "#FFE2A6", k)


EARTH = None


def draw_earth(hud: Hud, cx, cy, k):
    r = 17
    for i in range(-27, 28, 3):
        hud.px(cx, cy + i, "#C9C5EE", k * 0.6)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                lit = (dx + dy * 0.4) < 1
                land = ((dx - 4) ** 2 + (dy + 6) ** 2 < 26) or ((dx + 7) ** 2 + (dy - 6) ** 2 < 18) \
                    or ((dx - 8) ** 2 + (dy - 8) ** 2 < 9) or ((dx + 9) ** 2 + (dy + 7) ** 2 < 7)
                c = "#7E77DA" if land else "#3F3888"
                if lit:
                    c = "#B9B3FF" if land else "#6157F8"
                if dx * dx + dy * dy > (r - 1) ** 2:
                    c = "#2B2660"
                hud.px(cx + dx, cy + dy, c, k)
    tilt = math.radians(23.4)
    for i in range(-27, 28):
        if abs(i) > r - 1:
            hud.px(cx + math.sin(tilt) * i, cy - math.cos(tilt) * i, OFFWHITE, k)


GAUGE_X, GAUGE_TOP, GAUGE_PER_DEG = 30, HORIZON, 2.6


def gauge_y(deg):
    return GAUGE_TOP + deg * GAUGE_PER_DEG


def draw_gauge(hud: Hud, depth, k, ticks_lit):
    hud.line(GAUGE_X, GAUGE_TOP, GAUGE_X, gauge_y(20), "#4B4675", k)
    for d in (0, 6, 12, 15, 18):
        lit = d in ticks_lit
        c = LAVENDER_LIGHT if lit else "#6F6A99"
        hud.line(GAUGE_X - 2, gauge_y(d), GAUGE_X + 2, gauge_y(d), c, k)
    hud.disc(GAUGE_X, gauge_y(depth), 3, "#FFE2A6", k)


# ---------------------------------------------------------------------------
# Éléments typographiques (pleine résolution)
# ---------------------------------------------------------------------------

class Sprite:
    def __init__(self, img: Image.Image):
        arr = np.asarray(img.convert("RGBA")).astype(np.float32)
        self.rgb = arr[..., :3]
        self.a = arr[..., 3] / 255.0
        self.h, self.w = self.a.shape


def with_shadow(img: Image.Image, radius=9, offset=4, strength=0.6) -> Image.Image:
    pad = radius * 3
    out = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    alpha = Image.new("L", out.size, 0)
    alpha.paste(img.getchannel("A"), (pad, pad + offset))
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: int(v * strength))
    shadow = Image.new("RGBA", out.size, (10, 9, 18, 255))
    shadow.putalpha(alpha)
    out.alpha_composite(shadow)
    out.alpha_composite(img, (pad, pad))
    return out


RUN_RE = re.compile(r"\[\[(.+?)\]\]")


def runs_of(line, color, accent):
    out, pos = [], 0
    for m in RUN_RE.finditer(line):
        if m.start() > pos:
            out.append((line[pos:m.start()], color))
        out.append((m.group(1), accent))
        pos = m.end()
    if pos < len(line):
        out.append((line[pos:], color))
    return out


def text_sprite(text, fkey="xb", size=80, color=OFFWHITE, accent=LAVENDER, line_gap=1.14,
                shadow=True, tracking=0):
    f = font(fkey, size)
    lines = text.split("\n")
    asc, desc = f.getmetrics()
    lh = int(size * line_gap)
    widths = [sum(f.getlength(r) + tracking * len(r) for r, _ in runs_of(l, color, accent)) for l in lines]
    w = int(max(widths)) + 8
    h = lh * (len(lines) - 1) + asc + desc + 8
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        x = (w - widths[i]) / 2
        for r, c in runs_of(l, color, accent):
            if tracking:
                for ch in r:
                    d.text((x, i * lh + 4), ch, font=f, fill=c)
                    x += f.getlength(ch) + tracking
            else:
                d.text((x, i * lh + 4), r, font=f, fill=c)
                x += f.getlength(r)
    return Sprite(with_shadow(img) if shadow else img)


def arabic_img(text, size=72, color=LAVENDER, key="ar"):
    f = font(key, size)
    bbox = f.getbbox(text, direction="rtl", language="ar")
    w, h = bbox[2] - bbox[0] + 12, bbox[3] - bbox[1] + 12
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((6 - bbox[0], 6 - bbox[1]), text, font=f, fill=color,
                             direction="rtl", language="ar")
    return img


def title_sprite(latin, arabic):
    f = font("xb", 96)
    asc, desc = f.getmetrics()
    lat = Image.new("RGBA", (int(f.getlength(latin)) + 8, asc + desc), (0, 0, 0, 0))
    ImageDraw.Draw(lat).text((4, 0), latin, font=f, fill=OFFWHITE)
    lat = lat.crop(lat.getbbox())
    ar = arabic_img(arabic, 74)
    gap = 34
    h = max(lat.height, ar.height)
    img = Image.new("RGBA", (lat.width + gap + ar.width, h), (0, 0, 0, 0))
    img.alpha_composite(lat, (0, h - lat.height))
    img.alpha_composite(ar, (lat.width + gap, h - ar.height + 6))
    return Sprite(with_shadow(img))


def tag_sprite(text, color=LAVENDER_LIGHT, border=VIOLET, size=46):
    f = font("pixel", size)
    tw = int(f.getlength(text))
    asc, desc = f.getmetrics()
    padx, pady, b = 22, 6, 5
    w, h = tw + 2 * padx, asc + desc + 2 * pady
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], fill=(22, 20, 32, 225))
    d.rectangle([0, 0, w - 1, b - 1], fill=border)
    d.rectangle([0, h - b, w - 1, h - 1], fill=border)
    d.rectangle([0, 0, b - 1, h - 1], fill=border)
    d.rectangle([w - b, 0, w - 1, h - 1], fill=border)
    for cx, cy in ((0, 0), (w - b, 0), (0, h - b), (w - b, h - b)):
        d.rectangle([cx, cy, cx + b - 1, cy + b - 1], fill=(0, 0, 0, 0))
    d.fontmode = "1"
    d.text((padx, pady), text, font=f, fill=color)
    return Sprite(img)


def row_sprite(label, value, width=620):
    fl, fv = font("pixel", 54), font("b", 62)
    img = Image.new("RGBA", (width, 92), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    d.text((0, 22), label, font=fl, fill=LAVENDER)
    d.fontmode = "L"
    d.text((width - fv.getlength(value), 6), value, font=fv, fill=OFFWHITE)
    return Sprite(img)


def pixel_sprite(rows, palette, scale=PX):
    h, w = len(rows), max(len(r) for r in rows)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in palette:
                img.putpixel((x, y), palette[ch])
    return Sprite(img.resize((w * scale, h * scale), Image.NEAREST))


BOOK = [
    "..LLLL.....LLLL..",
    ".LwwwwLL.LLwwwwL.",
    ".LwwwwwwLwwwwwwL.",
    ".LwwwwwwLwwwwwwL.",
    ".LwwwwwwLwwwwwwL.",
    ".LwwwwwwLwwwwwwL.",
    ".LwwwwwwLwwwwwwL.",
    ".LLLLwwwLwwwLLLL.",
    "VVVVVLLLLLLLVVVVV",
    ".VVVVVVVVVVVVVVV.",
]
BOOK_PAL = {"L": (169, 163, 255, 255), "w": (40, 36, 62, 255), "V": (97, 87, 248, 255)}


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

class El:
    def __init__(self, sprite, x, y, t0, t1, fade_in=0.35, fade_out=0.3, rise=10, anchor="c", sfx=None):
        self.s, self.x, self.y, self.t0, self.t1 = sprite, x, y, t0, t1
        self.fi, self.fo, self.rise, self.anchor, self.sfx = fade_in, fade_out, rise, anchor, sfx

    def state(self, t):
        if t < self.t0 or t > self.t1:
            return 0.0, 0.0
        a = ease_out(ramp(t, self.t0, self.t0 + self.fi)) * (1 - smooth(ramp(t, self.t1 - self.fo, self.t1)))
        dy = self.rise * (1 - ease_out(ramp(t, self.t0, self.t0 + self.fi)))
        return a, dy


VO = [
    (0.2, 3.2, "Pourquoi l'heure de la prière change chaque jour ?"),
    (3.6, 9.2, "À Paris, le soleil se couche vers 17 heures en décembre… et vers 22 heures en juin."),
    (9.6, 13.8, "Parce que la prière ne suit pas l'horloge. Elle suit le soleil."),
    (14.1, 17.5, "Le Coran parle d'une prescription « à des temps déterminés »."),
    (17.8, 21.2, "Et ces temps, la Sunna les décrit avec des repères dans le ciel."),
    (21.6, 26.5, "Fajr : dès que l'aube apparaît, quand la lumière s'étend le long de l'horizon…"),
    (26.7, 28.6, "… et jusqu'au lever du soleil."),
    (29.0, 34.2, "Dhuhr : quand le soleil a passé son point le plus haut et commence à décliner."),
    (34.6, 40.6, "Asr : quand l'ombre d'un objet devient égale à sa taille, en plus de son ombre de midi."),
    (40.9, 44.8, "Selon l'imam Abou Hanifa : quand elle atteint deux fois sa taille."),
    (45.2, 48.0, "Maghrib : dès que le soleil s'est couché."),
    (48.6, 51.6, "Isha : quand la lueur du crépuscule a disparu."),
    (51.9, 56.3, "La lueur rouge pour la majorité des savants, la lueur blanche selon Abou Hanifa."),
    (56.9, 62.3, "Mais pourquoi ces heures bougent-elles chaque jour ? Parce que l'axe de la Terre est incliné."),
    (62.6, 67.8, "Au fil de l'année, la course du soleil change… et les cinq repères glissent avec elle."),
    (68.3, 71.1, "Aujourd'hui, ces moments sont calculés à l'avance."),
    (71.4, 78.0, "Mais pour l'aube et la nuit, tous les calendriers ne retiennent pas le même angle du soleil sous l'horizon."),
    (78.2, 80.4, "D'où des écarts, parfois importants."),
    (81.0, 84.4, "Cinq rendez-vous par jour… réglés sur le ciel."),
]

# Même texte, écrit pour la synthèse vocale (nombres en lettres, graphies phonétiques).
# Une entrée par réplique de VO : voix.py génère un fichier audio par ligne.
VO_TTS = [
    "Pourquoi l'heure de la prière change chaque jour ?",
    "À Paris, le soleil se couche vers dix-sept heures en décembre… et vers vingt-deux heures en juin.",
    "Parce que la prière ne suit pas l'horloge. Elle suit le soleil.",
    "Le Coran parle d'une prescription, à des temps déterminés.",
    "Et ces temps, la Souna les décrit avec des repères dans le ciel.",
    "Fadjr : dès que l'aube apparaît, quand la lumière s'étend le long de l'horizon…",
    "Et jusqu'au lever du soleil.",
    "Dohr : quand le soleil a passé son point le plus haut, et commence à décliner.",
    "Asr : quand l'ombre d'un objet devient égale à sa taille, en plus de son ombre de midi.",
    "Selon l'imam Abou Hanifa : quand elle atteint deux fois sa taille.",
    "Maghrib : dès que le soleil s'est couché.",
    "Icha : quand la lueur du crépuscule a disparu.",
    "La lueur rouge pour la majorité des savants, la lueur blanche selon Abou Hanifa.",
    "Mais pourquoi ces heures bougent-elles chaque jour ? Parce que l'axe de la Terre est incliné.",
    "Au fil de l'année, la course du soleil change… et les cinq repères glissent avec elle.",
    "Aujourd'hui, ces moments sont calculés à l'avance.",
    "Mais pour l'aube et la nuit, tous les calendriers ne retiennent pas le même angle du soleil sous l'horizon.",
    "D'où des écarts, parfois importants.",
    "Cinq rendez-vous par jour… réglés sur le ciel.",
]
assert len(VO_TTS) == len(VO)

# Texte arabe : Tanzil (écriture simple) ; traduction : Hamidullah, version Tanzil « fr.hamidullah ».
QURAN_AR = "إِنَّ الصَّلَاةَ كَانَتْ عَلَى الْمُؤْمِنِينَ كِتَابًا مَّوْقُوتًا"
QURAN_FR = "« … la Salât demeure, pour les\ncroyants, une prescription,\nà des temps déterminés. »"
QURAN_REF = "CORAN 4:103 · TRAD. HAMIDULLAH"


def subtitle_chunks(start, end, text, max_chars=52):
    """Découpe une réplique en sous-titres courts, de préférence aux ponctuations."""
    clauses = [c.strip() for c in re.split(r"(?<=[.?!…:,])\s+", text) if c.strip()]
    pieces = []
    for c in clauses:
        words = c.split()
        n = math.ceil(len(c) / max_chars)
        target = len(c) / n
        cur = ""
        for wd in words:
            if cur and len(cur) + 1 + len(wd) / 2 > target and len(pieces) < 99:
                pieces.append(cur)
                cur = wd
            else:
                cur = f"{cur} {wd}".strip()
        pieces.append(cur)
    chunks, cur = [], ""
    for p in pieces:
        fits = len(cur) + 1 + len(p) <= max_chars and not cur.endswith((".", "?", "!"))
        tiny = (len(cur) < 14 or len(p) < 10) and len(cur) + 1 + len(p) <= 64
        if cur and (fits or tiny):
            cur = f"{cur} {p}"
        else:
            if cur:
                chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)
    total = sum(len(c) for c in chunks)
    out, t = [], start
    for c in chunks:
        d = (end - start) * len(c) / total
        out.append((t, t + d, c))
        t += d
    return out


def word_tokens(text):
    return [w for w in text.split() if any(ch.isalnum() for ch in w)]


class Timing:
    """Fait correspondre le temps de l'animatic (τ) au temps réel de la vidéo (t).

    Sans voix, les deux sont identiques. Avec une voix générée par voix.py (manifest.json),
    chaque réplique prend la durée réelle de son enregistrement, en gardant l'ordre et les
    silences d'origine : l'image est étirée ou resserrée de façon linéaire entre ces repères.
    """

    def __init__(self, voice_dir=None):
        self.voice_dir = Path(voice_dir) if voice_dir else None
        self.clips = [None] * len(VO)
        self.words = [None] * len(VO)
        if self.voice_dir is None:
            self.lines = [(a, b) for a, b, _ in VO]
            self.total = DURATION
        else:
            manifest = json.loads((self.voice_dir / "manifest.json").read_text(encoding="utf-8"))
            items = manifest["lines"]
            if len(items) != len(VO):
                raise SystemExit(f"manifest.json : {len(items)} répliques, {len(VO)} attendues")
            self.lines, t = [], VO[0][0]
            for i, ((a, _, _), item) in enumerate(zip(VO, items)):
                if i:
                    t += max(0.3, a - VO[i - 1][1])
                self.lines.append((t, t + item["duration"]))
                t += item["duration"]
                self.clips[i] = self.voice_dir / item["file"]
                self.words[i] = item.get("words")
            self.total = t + (DURATION - VO[-1][1])
        old, new = [0.0], [0.0]
        for (a, b, _), (s, e) in zip(VO, self.lines):
            old += [a, b]
            new += [s, e]
        self.old = np.array(old + [DURATION])
        self.new = np.array(new + [self.total])

    def tau(self, t):
        return float(np.interp(t, self.new, self.old))

    def real(self, tau):
        return float(np.interp(tau, self.old, self.new))

    def subtitles(self):
        """Sous-titres en temps réel : calés sur les mots si la synthèse a fourni leurs horaires."""
        out = []
        for (_, _, text), (s, e), words in zip(VO, self.lines, self.words):
            chunks = subtitle_chunks(s, e, text)
            counts = [len(word_tokens(c)) for _, _, c in chunks]
            if words and sum(counts) == len(words):
                timed, k = [], 0
                for (_, _, c), n in zip(chunks, counts):
                    timed.append([s + words[k]["start"], c])
                    k += n
                timed[0][0] = s
                chunks = [(t0, timed[j + 1][0] if j + 1 < len(timed) else e, c)
                          for j, (t0, c) in enumerate(timed)]
            out += chunks
        return out


def wrap2(text, f, max_w=860):
    words = text.split()
    best = text
    if f.getlength(text) <= max_w:
        return text
    best_diff = 1e9
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        diff = abs(f.getlength(a) - f.getlength(b))
        if diff < best_diff and f.getlength(a) <= max_w and f.getlength(b) <= max_w:
            best, best_diff = a + "\n" + b, diff
    return best


def subtitle_sprite(text):
    f = font("sb", 44)
    text = wrap2(text, f)
    lines = text.split("\n")
    lh = 58
    w = int(max(f.getlength(l) for l in lines)) + 56
    h = lh * len(lines) + 30
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=22, fill=(20, 19, 26, 200))
    for i, l in enumerate(lines):
        d.text(((w - f.getlength(l)) / 2, 12 + i * lh), l, font=f, fill=OFFWHITE)
    return Sprite(img)


SUB_Y = 1478


def build_timeline():
    E = []

    def add(sprite, y, t0, t1, x=540, **kw):
        E.append(El(sprite, x, y, t0, t1, **kw))

    # 0 · Accroche
    add(text_sprite("Pourquoi l'heure\nde la prière change\n[[chaque jour]] ?", "xb", 84), 500, 0.15, 3.35, fade_in=0.25)
    # 1 · Coucher du soleil à Paris
    add(tag_sprite("COUCHER DU SOLEIL · PARIS"), 610, 3.6, 9.3, sfx="blip")
    add(row_sprite("21 DÉC.", "≈ 16 h 56"), 712, 4.4, 9.3, sfx="blip")
    add(row_sprite("21 JUIN", "≈ 21 h 58"), 812, 6.6, 9.3, sfx="blip")
    # 2 · Elle suit le soleil
    add(text_sprite("Elle ne suit pas l'horloge.", "b", 62), 440, 9.6, 13.8)
    add(text_sprite("Elle suit le [[soleil]].", "xb", 88), 540, 11.6, 13.8)
    # 3 · Coran 4:103
    add(pixel_sprite(BOOK, BOOK_PAL), 528, 14.25, 17.6, rise=0)
    add(Sprite(arabic_img(QURAN_AR, 54, LAVENDER_LIGHT, "ar-r")), 602, 14.4, 17.6, rise=0)
    add(text_sprite(QURAN_FR, "m", 46, line_gap=1.3, shadow=False), 752, 14.6, 17.6, rise=0)
    add(tag_sprite(QURAN_REF, size=40), 880, 14.8, 17.6, rise=0, sfx="blip")
    add(text_sprite("La Sunna décrit ces temps", "sb", 50), 420, 17.9, 21.3)
    add(text_sprite("avec des repères\ndans le [[ciel]].", "xb", 80), 535, 18.4, 21.3)
    add(tag_sprite("D'APRÈS SAHIH MUSLIM 612"), 668, 19.0, 21.3, sfx="blip")

    # 4–8 · Les cinq temps
    chapters = [
        ("Fajr", "الفجر", 21.6, 28.7, [("Dès que l'[[aube]] apparaît", 21.9, 28.7)],
         [("lumière étalée sur l'horizon", 23.6, 26.5), ("… jusqu'au lever du soleil", 26.7, 28.7)]),
        ("Dhuhr", "الظهر", 29.0, 34.3, [("Le soleil [[décline]]", 29.2, 34.3)],
         [("juste après son point le plus haut", 31.2, 34.3)]),
        ("Asr", "العصر", 34.6, 44.9, [("L'ombre [[égale]] l'objet", 34.9, 44.9)],
         [("en plus de l'ombre de midi", 36.2, 44.9)]),
        ("Maghrib", "المغرب", 45.2, 48.3, [("Dès le [[coucher]] du soleil", 45.4, 48.3)], []),
        ("Isha", "العشاء", 48.6, 56.4, [("La lueur du soir [[disparaît]]", 48.8, 56.4)], []),
    ]
    for latin, ar, t0, t1, lines, details in chapters:
        add(title_sprite(latin, ar), 398, t0, t1)
        for txt, a, b in lines:
            add(text_sprite(txt, "sb", 56), 494, a, b)
        for txt, a, b in details:
            add(text_sprite(txt, "m", 42, color=LAVENDER, shadow=True), 560, a, b)

    for i, name in enumerate(PRAYERS):
        for (a, b) in ((21.4, 56.5), (80.6, 85.3)):
            lab_dim = tag_label(name, False)
            lab_lit = tag_label(name, True)
            lit_t = NODE_TIMES[i] if a < 60 else OUTRO_NODE_TIMES[i]
            add(lab_dim, 318, a, min(b, lit_t + 0.15), x=TRACK_X[i] * PX + 2, rise=0, fade_out=0.15)
            add(lab_lit, 318, lit_t, b, x=TRACK_X[i] * PX + 2, rise=0, fade_in=0.15,
                sfx="chime")

    add(tag_sprite("ZÉNITH", size=40), ARC_TOP * PX - 95, 30.8, 34.3, x=540, rise=0, sfx="blip")
    x_noon = (POST_X - NOON_SHADOW) * PX
    lab_y = FLOOR * PX - 44
    add(tag_sprite("MIDI", size=34), lab_y, 35.6, 44.9, x=int(x_noon) + 12, rise=0, anchor="l", sfx="blip")
    add(tag_sprite("1×", size=34), lab_y, 37.1, 44.9, x=int(x_noon - POST_H * PX) + 12, rise=0, anchor="l",
        sfx="blip")
    add(tag_sprite("2×", size=34), lab_y, 41.3, 44.9, x=int(x_noon - 2 * POST_H * PX) + 12, rise=0,
        anchor="l", sfx="blip")
    add(tag_sprite("SELON ABOU HANIFA : 2×"), 650, 41.0, 44.9, sfx="blip")
    add(tag_sprite("LUEUR ROUGE · MAJORITÉ DES SAVANTS", border=CORAL), 640, 51.9, 56.4, sfx="blip")
    add(tag_sprite("LUEUR BLANCHE · ABOU HANIFA", border=TWILIGHT_WHITE), 712, 53.6, 56.4, sfx="blip")

    # 9 · Les saisons
    add(text_sprite("Pourquoi ça [[bouge]] ?", "xb", 84), 420, 56.9, 67.8)
    add(text_sprite("L'axe de la Terre est incliné", "sb", 54), 520, 59.6, 62.4)
    add(tag_sprite("≈ 23°", size=40), 790, 60.4, 62.4, x=735, rise=0, sfx="blip")
    add(text_sprite("La course du soleil change", "sb", 54), 520, 62.6, 67.8)
    add(tag_sprite("ÉTÉ", size=40), 880, 63.6, 67.8, x=170, rise=0, sfx="blip")
    add(tag_sprite("HIVER", size=40), 1010, 65.0, 67.8, x=880, rise=0, sfx="blip")
    add(text_sprite("les cinq repères glissent avec elle", "m", 42, color=LAVENDER), 584, 66.0, 67.8)

    # 10 · Angles de calcul
    add(text_sprite("Et d'un calendrier\n[[à l'autre]] ?", "xb", 76), 440, 68.3, 80.4)
    add(text_sprite("L'angle retenu [[varie]]", "sb", 54), 590, 71.4, 80.4)
    add(text_sprite("selon les institutions", "m", 42, color=LAVENDER), 652, 72.4, 77.9)
    add(text_sprite("d'où des écarts, parfois importants", "m", 42, color=LAVENDER), 652, 78.2, 80.4)
    gx = GAUGE_X * PX + 40
    add(tag_sprite("0°", size=36), int(gauge_y(0) * PX), 70.0, 80.4, x=gx + 30, rise=0, anchor="l")
    for deg, t in ((18, 72.9), (15, 74.7), (12, 76.5)):
        add(tag_sprite(f"−{deg}°", size=36), int(gauge_y(deg) * PX), t, 80.4, x=gx + 30, rise=0,
            anchor="l", sfx="blip")
    add(tag_sprite("SOLEIL SOUS L'HORIZON", size=36), int(gauge_y(0) * PX) - 70, 70.4, 80.4,
        x=GAUGE_X * PX - 40, rise=0, anchor="l")

    # 11 · Fin
    add(text_sprite("Cinq rendez-vous par jour,", "sb", 60), 470, 81.0, 85.3)
    add(text_sprite("réglés sur le [[ciel]].", "xb", 88), 562, 82.4, 85.3)
    add(tag_sprite("SOURCES EN DESCRIPTION", size=38), 690, 83.4, 85.3)

    return E


def subtitle_elements(entries):
    """Sous-titres incrustés ; leurs temps sont en temps réel (voir Timing.subtitles)."""
    return [El(subtitle_sprite(c), 540, SUB_Y, c0, c1, fade_in=0.06, fade_out=0.06, rise=0)
            for c0, c1, c in entries]


@lru_cache(maxsize=None)
def tag_label(name, lit):
    f = font("pixel", 40)
    w = int(f.getlength(name)) + 4
    img = Image.new("RGBA", (w, 46), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    d.text((2, 2), name, font=f, fill=LAVENDER_LIGHT if lit else "#7E79A8")
    return Sprite(with_shadow(img, radius=5, offset=2, strength=0.8))


# ---------------------------------------------------------------------------
# Composition d'une image
# ---------------------------------------------------------------------------

def blit(frame, sp: Sprite, x, y, k, anchor="c"):
    if k <= 0:
        return
    x0 = int(round(x - sp.w / 2)) if anchor == "c" else int(round(x))
    y0 = int(round(y - sp.h / 2))
    sx0, sy0 = max(0, -x0), max(0, -y0)
    x1, y1 = min(W, x0 + sp.w), min(H, y0 + sp.h)
    if x1 <= max(0, x0) or y1 <= max(0, y0):
        return
    a = sp.a[sy0:sy0 + (y1 - max(0, y0)), sx0:sx0 + (x1 - max(0, x0))][..., None] * k
    src = sp.rgb[sy0:sy0 + (y1 - max(0, y0)), sx0:sx0 + (x1 - max(0, x0))]
    region = frame[max(0, y0):y1, max(0, x0):x1]
    region *= (1 - a)
    region += src * a


CARD_BOX = (90, 470, 990, 925)  # verre du verset (Coran 4:103)
ROWS_BOX = (200, 655, 880, 865)  # verre des heures de coucher


@lru_cache(maxsize=None)
def card_masks(box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    m = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=56, fill=255)
    m = m.resize((w, h), Image.LANCZOS)
    b = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(b).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=56, outline=255, width=4)
    b = b.resize((w, h), Image.LANCZOS)
    return (np.asarray(m, dtype=np.float32) / 255)[..., None], (np.asarray(b, dtype=np.float32) / 255)[..., None]


def glass(frame, box, k):
    if k <= 0:
        return
    x0, y0, x1, y1 = box
    crop = Image.fromarray(np.clip(frame[y0:y1, x0:x1], 0, 255).astype(np.uint8))
    blur = np.asarray(crop.filter(ImageFilter.GaussianBlur(18)), dtype=np.float32)
    tinted = blur * 0.42 + rgb(INK) * 0.58
    m, b = card_masks(box)
    region = frame[y0:y1, x0:x1]
    region[:] = region * (1 - m * k) + tinted * m * k
    region[:] = region * (1 - b * k * 0.28) + rgb(LAVENDER) * b * k * 0.28


def dissolve(a, b, p):
    mask = (BAYER_LR < p)[..., None]
    return np.where(mask, b, a)


def world_at(t):
    """Image basse résolution du monde + couche HUD pour le temps t."""
    hud = Hud()
    if t < 56.6:
        u = SKY_CLOCK(t)
        alt, s = solar(u)
        img = render_world(t, alt, s, u=u)
        sx, sy = sun_xy(s)
        if 9.0 <= t <= 13.9:
            draw_brackets(hud, round(sx), round(sy), t, 11.6, 1 - ramp(t, 13.5, 13.9))
        if 21.4 <= t:
            k = ease_out(ramp(t, 21.4, 21.9)) * (1 - ramp(t, 56.2, 56.6))
            draw_track(hud, t, k)
            draw_arc_path(hud, ARC_X0, ARC_X1, ARC_TOP, 0.22 * k)
        if 30.6 <= t <= 34.4:
            k = ramp(t, 30.6, 31.0) * (1 - ramp(t, 34.0, 34.4))
            for i in range(0, 8, 2):
                hud.px(108, ARC_TOP - 16 + i, LAVENDER_LIGHT, k)
        if 35.4 <= t <= 45.0:
            k = ramp(t, 35.4, 35.8) * (1 - ramp(t, 44.6, 45.0))
            xn = POST_X - NOON_SHADOW
            for x, t0 in ((xn, 35.6), (xn - POST_H, 37.1), (xn - 2 * POST_H, 41.3)):
                if t >= t0:
                    hud.line(x, FLOOR - 3, x, FLOOR + 7, LAVENDER_LIGHT, k)
            for pivot, t0 in ((xn, 36.2), (xn - POST_H, 40.4)):
                if t >= t0:
                    ang = math.radians(90 + 90 * ease_out(ramp(t, t0, t0 + 0.8)))
                    x1 = pivot + math.cos(ang) * POST_H
                    y1 = FLOOR - 1 - math.sin(ang) * POST_H
                    hud.line(pivot, FLOOR - 1, x1, y1, LAVENDER, k * 0.9)
        return img, hud

    if t < 68.0:
        img = render_world(t, 35.0, 0.3, show_sun=False, show_post=False)
        k_e = ramp(t, 59.6, 59.9) * (1 - ramp(t, 62.1, 62.4))
        if k_e > 0:
            draw_earth(hud, 108, 175, k_e)
        if t >= 62.8:
            draw_arc_path(hud, 4, 212, 150, 0.95, LAVENDER_LIGHT, ramp(t, 62.8, 64.2), step=2, head=True)
        if t >= 64.2:
            draw_arc_path(hud, 62, 154, 198, 0.95, LAVENDER, ramp(t, 64.2, 65.4), step=2, head=True)
        base = img
        if t < 57.1:
            u = SKY_CLOCK(56.6)
            alt, s = solar(u)
            prev = render_world(t, alt, s, u=u)
            base = dissolve(prev, img, ramp(t, 56.6, 57.1))
        return base, hud

    if t < 80.6:
        depth = 20.0
        for d0, d1, t0, t1 in ((20, 18, 71.4, 72.9), (18, 15, 73.3, 74.7), (15, 12, 75.1, 76.5)):
            if t >= t0:
                depth = d0 + (d1 - d0) * smooth(ramp(t, t0, t1))
        alt = -depth
        s = -0.17
        img = render_world(t, alt, s, show_sun=False, show_post=False)
        lit = {d for d, tt in ((18, 72.9), (15, 74.7), (12, 76.5)) if t >= tt} | {0}
        k = ramp(t, 70.0, 70.4) * (1 - ramp(t, 80.2, 80.6))
        draw_gauge(hud, depth, k, lit)
        if t < 68.5:
            prev = render_world(t, 35.0, 0.3, show_sun=False, show_post=False)
            img = dissolve(prev, img, ramp(t, 68.0, 68.5))
        return img, hud

    img = render_world(t, -28.0, 1.3, show_sun=False)
    k = ease_out(ramp(t, 80.7, 81.0))
    draw_track(hud, t, k)
    if t < 81.1:
        prev = render_world(t, -12.0, -0.17, show_sun=False, show_post=False)
        img = dissolve(prev, img, ramp(t, 80.6, 81.1))
    return img, hud


def compose(t, elements, subs=(), t_real=None):
    """Image au temps d'animatic t ; les sous-titres suivent le temps réel t_real."""
    img, hud = world_at(t)
    a = hud.a[..., None]
    img = img * (1 - a) + hud.rgb * a
    frame = np.repeat(np.repeat(img.astype(np.float32), PX, axis=0), PX, axis=1)

    glass(frame, ROWS_BOX, ease_out(ramp(t, 3.9, 4.3)) * (1 - ramp(t, 9.0, 9.3)))
    glass(frame, CARD_BOX, ease_out(ramp(t, 14.1, 14.5)) * (1 - ramp(t, 17.3, 17.6)))

    for el in elements:
        k, dy = el.state(t)
        if k > 0:
            blit(frame, el.s, el.x, el.y + dy, k, el.anchor)
    for el in subs:
        k, dy = el.state(t if t_real is None else t_real)
        if k > 0:
            blit(frame, el.s, el.x, el.y + dy, k, el.anchor)

    fade = ramp(t, 85.0, 86.0) + (1 - ramp(t, 0.0, 0.25))
    if fade > 0:
        frame = frame * (1 - min(1, fade)) + rgb(INK) * min(1, fade)
    return np.clip(frame, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Son : ambiance synthétisée, sans musique
# ---------------------------------------------------------------------------

SR = 48000


def env(n, attack, release):
    e = np.ones(n)
    a, r = max(1, int(attack * SR)), max(1, int(release * SR))
    e[:a] = np.linspace(0, 1, a)
    e[-r:] *= np.linspace(1, 0, r)
    return e


def add_at(buf, t, sig, pan=0.0):
    i = int(t * SR)
    if i >= buf.shape[1]:
        return
    j = min(buf.shape[1], i + len(sig))
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buf[0, i:j] += sig[:j - i] * l
    buf[1, i:j] += sig[:j - i] * r


def shaped_noise(n, lo, hi, seed):
    r = np.random.default_rng(seed)
    spec = np.fft.rfft(r.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    shape = 1 / np.sqrt(1 + (f / hi) ** 4) * (1 - 1 / np.sqrt(1 + (f / lo) ** 4))
    out = np.fft.irfft(spec * shape, n)
    return out / (np.abs(out).max() + 1e-9)


def read_wav_mono(path):
    with wave.open(str(path), "rb") as w:
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if sw != 2:
        raise SystemExit(f"{path} : seul le PCM 16 bits est géré")
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if sr != SR:  # rééchantillonnage simple ; voix.py demande déjà du 48 kHz
        n = int(len(x) * SR / sr)
        x = np.interp(np.arange(n) * sr / SR, np.arange(len(x)), x)
    return x


AMBIENCE_UNDER_VOICE_DB = 21  # l'ambiance reste 18 à 24 dB sous la voix


def synth_audio(path, elements, timing):
    total = timing.total
    R = timing.real
    n = int(total * SR)
    buf = np.zeros((2, n))
    tt = np.arange(n) / SR
    rng_a = np.random.default_rng(11)

    # vent très bas, lent
    wind = shaped_noise(n, 40, 380, 1)
    wind2 = shaped_noise(n, 40, 380, 2)
    lfo = 0.65 + 0.35 * np.sin(2 * np.pi * 0.06 * tt + 1.0)
    buf[0] += wind * lfo * 0.05
    buf[1] += wind2 * lfo * 0.05

    # oiseaux à l'aube et pendant la journée
    def chirp(dur, f0, f1):
        m = int(dur * SR)
        x = np.arange(m) / SR
        f = f0 + (f1 - f0) * (x / dur)
        ph = 2 * np.pi * np.cumsum(f) / SR
        return np.sin(ph) * np.sin(np.pi * x / dur) ** 2

    for a, b, density in ((22.6, 34.0, 1.6), (56.8, 67.8, 0.9)):
        t, end = R(a), R(b)
        while t < end:
            f0 = rng_a.uniform(2800, 4300)
            for j in range(int(rng_a.integers(2, 5))):
                sig = chirp(rng_a.uniform(0.05, 0.11), f0, f0 * rng_a.uniform(0.75, 1.3)) * 0.022
                add_at(buf, t + j * 0.1, sig, rng_a.uniform(-0.7, 0.7))
            t += rng_a.exponential(1 / density) + 0.25

    # grillons la nuit
    def cricket():
        m = int(0.022 * SR)
        x = np.arange(m) / SR
        return np.sin(2 * np.pi * 4700 * x) * np.sin(np.pi * x / 0.022) ** 2

    for a, b in ((14.0, 21.4), (50.8, 56.6), (68.5, 80.6), (80.8, 86.0)):
        for pan in (-0.5, 0.45):
            t, end = R(a) + rng_a.uniform(0, 0.5), R(b)
            while t < end:
                for j in range(3):
                    add_at(buf, t + j * 0.04, cricket() * 0.006, pan)
                t += rng_a.uniform(0.75, 1.2)

    # souffle du « jour qui passe »
    for a, b in ((28.8, 31.2),):
        m = int((R(b) - R(a)) * SR)
        sig = shaped_noise(m, 500, 2600, 5) * np.sin(np.pi * np.arange(m) / m) ** 2 * 0.035
        add_at(buf, R(a), sig, 0.0)
    for t in (56.6, 68.0, 80.6):
        m = int(0.5 * SR)
        sig = shaped_noise(m, 900, 4000, int(t)) * env(m, 0.15, 0.3) * 0.018
        add_at(buf, R(t), sig)

    # petits signaux d'interface
    def blip():
        m = int(0.07 * SR)
        x = np.arange(m) / SR
        f = 1046 - 260 * (x / 0.07)
        ph = 2 * np.pi * np.cumsum(f) / SR
        return (np.sin(ph) + 0.15 * np.sin(3 * ph)) * env(m, 0.004, 0.05) * 0.03

    def chime():
        m = int(0.9 * SR)
        x = np.arange(m) / SR
        e = np.exp(-x / 0.32) * env(m, 0.006, 0.1)
        return (np.sin(2 * np.pi * 659.25 * x) + 0.45 * np.sin(2 * np.pi * 987.77 * x)) * e * 0.032

    for el in elements:
        if el.sfx == "blip":
            add_at(buf, R(el.t0), blip(), 0.0)
        elif el.sfx == "chime":
            add_at(buf, R(el.t0), chime(), 0.0)

    buf *= np.minimum(1, np.minimum(tt / 0.4, (total - tt) / 1.2))[None, :]

    if timing.voice_dir is None:
        peak = np.abs(buf).max()
        if peak > 0:
            buf *= 0.4 / peak  # crête ≈ −8 dBFS : l'ambiance reste sous une future voix off
    else:
        voice = np.zeros(n)
        spoken = np.zeros(n, dtype=bool)
        for (s, _), clip in zip(timing.lines, timing.clips):
            x = read_wav_mono(clip)
            i = int(s * SR)
            j = min(n, i + len(x))
            voice[i:j] += x[:j - i]
            spoken[i:j] = True
        v_rms = np.sqrt(np.mean(voice[spoken] ** 2)) + 1e-12
        voice *= 10 ** (-18 / 20) / v_rms  # voix ≈ −18 dBFS RMS
        if np.abs(voice).max() > 0.89:
            voice *= 0.89 / np.abs(voice).max()
        v_rms = np.sqrt(np.mean(voice[spoken] ** 2))
        a_rms = np.sqrt(np.mean(buf ** 2)) + 1e-12
        buf *= v_rms * 10 ** (-AMBIENCE_UNDER_VOICE_DB / 20) / a_rms
        buf += voice[None, :]
        peak = np.abs(buf).max()
        if peak > 0.97:
            buf *= 0.97 / peak

    data = (np.clip(buf.T, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# ---------------------------------------------------------------------------
# Sous-titres SRT
# ---------------------------------------------------------------------------

def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(path, entries):
    lines = []
    for i, (c0, c1, chunk) in enumerate(entries, start=1):
        lines += [str(i), f"{srt_time(c0)} --> {srt_time(c1)}", chunk, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------

_ELEMENTS = _SUBS = _TIMING = None


def _init_worker(subs, voice_dir):
    global _ELEMENTS, _SUBS, _TIMING
    _TIMING = Timing(voice_dir)
    _ELEMENTS = build_timeline()
    _SUBS = subtitle_elements(_TIMING.subtitles()) if subs else []


def _render_frame(f):
    t = f / FPS
    return compose(_TIMING.tau(t), _ELEMENTS, _SUBS, t).tobytes()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="vidéo de sortie (défaut : animatic.mp4, ou video-voix-off.mp4 avec --voix)")
    ap.add_argument("--voix", help="dossier produit par voix.py : cale l'image et les sous-titres sur la voix")
    ap.add_argument("--stills", help="liste de temps (s) à exporter en PNG, ex. 2,24,38")
    ap.add_argument("--still-dir", default=str(HERE / "stills"))
    ap.add_argument("--no-subs", action="store_true")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()

    timing = Timing(args.voix)
    elements = build_timeline()
    subs = [] if args.no_subs else subtitle_elements(timing.subtitles())

    if args.stills:
        out = Path(args.still_dir)
        out.mkdir(parents=True, exist_ok=True)
        for v in args.stills.split(","):
            t = float(v)
            Image.fromarray(compose(timing.tau(t), elements, subs, t)).save(out / f"t{t:05.1f}.png")
        return

    out = Path(args.out) if args.out else HERE / ("video-voix-off.mp4" if args.voix else "animatic.mp4")
    wav = out.with_suffix(".wav")
    synth_audio(wav, elements, timing)
    write_srt(HERE / ("sous-titres-voix-off.srt" if args.voix else "sous-titres.srt"), timing.subtitles())

    end = timing.total if args.end is None else args.end
    n0, n1 = int(args.start * FPS), int(end * FPS)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-ss", f"{args.start}", "-i", str(wav),
           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
           "-tune", "animation", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
           "-shortest", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with multiprocessing.Pool(args.jobs, _init_worker, (not args.no_subs, args.voix)) as pool:
        for f, buf in enumerate(pool.imap(_render_frame, range(n0, n1), chunksize=6), start=n0):
            proc.stdin.write(buf)
            if f % (FPS * 5) == 0:
                print(f"{f / FPS:5.1f} s", file=sys.stderr, flush=True)
    proc.stdin.close()
    proc.wait()
    wav.unlink(missing_ok=True)
    print(out)


if __name__ == "__main__":
    main()
