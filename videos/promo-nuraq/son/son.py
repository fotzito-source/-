#!/usr/bin/env python3
"""Design sonore du spot Nuraq : sans musique, uniquement des effets synthétisés.

Chaque son est calé sur un événement de l'animation (temps en secondes, voir spot/spot.js).
Grille rythmique 100 BPM : une musique sous licence peut être ajoutée plus tard sans recaler l'image.

    python3 son/son.py   →  son/nuraq-spot.wav (48 kHz, stéréo)
"""

from pathlib import Path
import wave

import numpy as np

SR = 48000
DURATION = 26.4
HERE = Path(__file__).resolve().parent
rng = np.random.default_rng(5)


def noise(n):
    return rng.standard_normal(n)


def band(x, lo, hi):
    """Filtre passe-bande doux par FFT."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    spec = np.fft.rfft(x)
    shape = 1 / np.sqrt(1 + (f / hi) ** 4)
    if lo > 0:
        shape *= 1 - 1 / np.sqrt(1 + (f / lo) ** 4)
    return np.fft.irfft(spec * shape, n)


def sweep_band(x, f0, f1, q=0.9, block=1024):
    """Passe-bande dont la fréquence centrale glisse de f0 à f1 (addition-recouvrement)."""
    n = len(x)
    hop = block // 2
    win = np.hanning(block)
    out = np.zeros(n + block)
    xp = np.concatenate([x, np.zeros(block)])
    freqs = np.fft.rfftfreq(block, 1 / SR)
    steps = max(1, (n + hop - 1) // hop)
    for i in range(steps):
        k = i / max(1, steps - 1)
        fc = f0 * (f1 / f0) ** k
        bw = fc * q
        shape = np.exp(-0.5 * ((freqs - fc) / bw) ** 2)
        seg = xp[i * hop:i * hop + block] * win
        out[i * hop:i * hop + block] += np.fft.irfft(np.fft.rfft(seg) * shape, block)
    return out[:n]


def env_adsr(n, a, r, curve=2.0):
    t = np.arange(n) / SR
    dur = n / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.clip((dur - t) / max(r, 1e-4), 0, 1) ** curve
    return e


def norm(x):
    m = np.abs(x).max()
    return x / m if m > 0 else x


buf = np.zeros((2, int(DURATION * SR)))


def put(t, sig, gain_db=0.0, pan=0.0):
    """Place un son mono à l'instant t, avec un gain (dB) et un panoramique (-1 à 1)."""
    i = int(t * SR)
    if i >= buf.shape[1]:
        return
    sig = sig * 10 ** (gain_db / 20)
    j = min(buf.shape[1], i + len(sig))
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[0, i:j] += sig[:j - i] * l * 1.414
    buf[1, i:j] += sig[:j - i] * r * 1.414


# ---------------------------------------------------------------- bibliothèque de sons

def whoosh(dur, f0, f1, attack=0.6):
    n = int(dur * SR)
    x = sweep_band(noise(n), f0, f1, q=0.7)
    t = np.arange(n) / n
    e = np.where(t < attack, (t / attack) ** 1.6, ((1 - t) / (1 - attack)) ** 1.3)
    return norm(x * e)


def shimmer(dur):
    n = int(dur * SR)
    x = band(noise(n), 5000, 11000)
    t = np.arange(n) / SR
    trem = 0.7 + 0.3 * np.sin(2 * np.pi * 9 * t)
    e = np.sin(np.pi * np.arange(n) / n) ** 1.5
    return norm(x * trem * e)


def bloom(dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 52 + 30 * np.exp(-t * 9)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.6)
    air = band(noise(n), 200, 2200) * np.exp(-t * 3.5) * np.minimum(1, t / 0.03)
    return norm(0.85 * sub + 0.35 * norm(air))


def click():
    n = int(0.045 * SR)
    t = np.arange(n) / SR
    x = band(noise(n), 1800, 6000) * np.exp(-t * 160)
    tone = np.sin(2 * np.pi * 1400 * t) * np.exp(-t * 90) * 0.5
    return norm(x + tone)


def ding():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    e = np.exp(-t * 4.2) * np.minimum(1, t / 0.004)
    x = np.sin(2 * np.pi * 988 * t) + 0.55 * np.sin(2 * np.pi * 1482 * t) + 0.12 * np.sin(2 * np.pi * 2964 * t)
    return norm(x * e)


def tink():
    """Étincelle de l'étoile : très bref, aigu, doux."""
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    e = np.exp(-t * 9) * np.minimum(1, t / 0.003)
    x = np.sin(2 * np.pi * 2637 * t) + 0.5 * np.sin(2 * np.pi * 3951 * t) + 0.25 * np.sin(2 * np.pi * 5274 * t)
    air = band(noise(n), 6000, 14000) * np.exp(-t * 22) * 0.5
    return norm(x * e + air)


def tick():
    """Petit déclic doux pour chaque lettre."""
    n = int(0.03 * SR)
    t = np.arange(n) / SR
    return norm(band(noise(n), 2500, 7000) * np.exp(-t * 220))


def pop(f0=680, f1=340, dur=0.11):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 45)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32) * np.minimum(1, t / 0.002)
    return norm(x)


def thump(dur=0.35):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 48 + 60 * np.exp(-t * 25)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    nz = band(noise(n), 80, 900) * np.exp(-t * 30) * 0.4
    return norm(x + nz)


def air_bed():
    n = buf.shape[1]
    x = band(noise(n), 60, 900)
    t = np.arange(n) / SR
    return norm(x) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t))


# ---------------------------------------------------------------- partition (temps du spot)

bed = air_bed() * 10 ** (-42 / 20)
buf[0] += bed
buf[1] += np.roll(bed, 977)

# 1. Logo : l'étoile scintille, le fil dessine le symbole, remplissage, lettres
put(0.08, tink(), -17, 0.15)
put(0.30, shimmer(0.9), -21, -0.1)
put(0.32, whoosh(0.85, 300, 2400, 0.85), -24)
put(1.00, bloom(), -9)
for i in range(5):
    put(1.28 + i * 0.075, tick(), -27, -0.5 + i * 0.25)
put(1.24, whoosh(0.6, 1200, 5000, 0.5), -25, -0.4)
put(1.95, whoosh(0.5, 2600, 400, 0.4), -18)

# 2. Monde des parcours : le fil parcourt la carte
put(2.38, shimmer(2.0) * 0.6, -26, 0.3)
for k, f in enumerate((0.36, 0.68, 0.995)):
    put(2.38 + 1.97 * f, pop(1050, 760, 0.08), -24, (-0.4, 0.3, 0.1)[k])
put(4.42, whoosh(0.5, 500, 3000, 0.75), -16)

# 3. Exercice dans le téléphone
put(4.62, whoosh(0.7, 2200, 300, 0.25), -17, 0.4)
put(5.32, thump(), -17)
put(4.95, shimmer(0.9) * 0.7, -26, 0.2)
put(6.20, click(), -16, 0.1)
put(6.95, click(), -16, 0.1)
put(7.05, ding(), -15, 0.1)
put(8.95, click(), -17, 0.1)
put(9.22, whoosh(0.42, 800, 3200, 0.5), -21, 0.5)

# 4. Coran : lecture, sons très discrets
put(9.75, shimmer(0.75) * 0.5, -28, 0.2)
put(10.55, click(), -18, -0.1)
put(10.78, whoosh(0.42, 800, 3200, 0.5), -22, 0.5)

# 5. Série : les jours s'allument
put(12.22, whoosh(0.5, 2600, 350, 0.5), -15, -0.6)
put(12.45, whoosh(0.6, 400, 2400, 0.7), -18, 0.6)
put(13.05, pop(820, 520, 0.12), -17)
for i in range(7):
    put(13.05 + i * 0.2, pop(760 + 25 * i, 420 + 15 * i, 0.09), -22, -0.45 + i * 0.15)
put(14.62, whoosh(0.45, 600, 3000, 0.7), -18)

# 6. Parcours des Piliers : chaque niveau se valide
put(14.88, whoosh(0.6, 2400, 380, 0.3), -19, 0.4)
for i in range(5):
    put(15.55 + i * 0.3, pop(700, 380, 0.12), -19, 0.1)
put(17.10, whoosh(0.45, 2200, 500, 0.5), -19)

# 7. Les parcours en branches
for i in range(5):
    put(17.3 + i * 0.17, whoosh(0.45, 900, 3600, 0.85) * 0.6, -27, -0.7 + i * 0.35)
    put(17.72 + i * 0.17, pop(900, 560, 0.1), -20, -0.7 + i * 0.35)
put(19.40, whoosh(0.45, 3000, 600, 0.6), -19)

# 8. Comprendre. Pratiquer. Progresser.
put(19.85, pop(560, 280, 0.16), -15, -0.3)
for i in range(3):
    put(20.05 + i * 0.6, thump(0.3), -17 - i * 0.5)
put(22.38, whoosh(0.5, 500, 2600, 0.8), -17)

# 9. Logo final
put(22.78, tink(), -18, 0.15)
put(22.90, shimmer(0.6), -22)
put(23.36, bloom(2.2), -8)
for i in range(5):
    put(23.58 + i * 0.075, tick(), -28, -0.5 + i * 0.25)
put(23.54, whoosh(0.55, 1200, 5000, 0.5), -25, 0.4)

# fondu final, gain vers ≈ −16 LUFS, limiteur doux (crête ≈ −1 dBFS)
t = np.arange(buf.shape[1]) / SR
buf *= np.clip((DURATION - t) / 0.45, 0, 1)[None, :] * np.clip(t / 0.05, 0, 1)[None, :]
buf *= 10 ** (-1 / 20) / np.abs(buf).max() * 10 ** (4.5 / 20)
ceiling = 10 ** (-1 / 20)
blk = 240  # 5 ms
peak = np.abs(buf).max(axis=0)
nb = len(peak) // blk + 1
blocks = np.pad(peak, (0, nb * blk - len(peak))).reshape(nb, blk).max(axis=1)
blocks = np.maximum(blocks, np.roll(blocks, 1))  # anticipation d'un bloc
gain_b = np.minimum(1.0, ceiling / np.maximum(blocks, 1e-9))
for i in range(1, nb):  # relâchement progressif (~60 ms)
    gain_b[i] = min(gain_b[i], gain_b[i - 1] + (1 - gain_b[i - 1]) * 0.08)
gain = np.interp(np.arange(len(peak)), np.arange(nb) * blk, gain_b)
buf *= gain[None, :]
buf = np.clip(buf, -ceiling, ceiling)

out = HERE / "nuraq-spot.wav"
data = (np.clip(buf.T, -1, 1) * 32767).astype(np.int16)
with wave.open(str(out), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(data.tobytes())
print(out)
