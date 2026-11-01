"""Step 7 without an API: synthesizes the episode's procedural sound clips into the library, under the exact file
names sfx.py looks for, so sfx.py then finds every clip present and never calls ElevenLabs.

python <skill>/scripts/sfx_local.py <slug> [--force]
In episode.json "sound.clips", a clip whose prompt starts with "procedural:" is made here by the recipe of the same
name (grow, creak, tick, rumble, slide, bone_snap, giant_step, flaps); any other clip must already be in the library
(reuse a library clip by its exact name, prompt and length). Then run sfx.py as usual.
Needs numpy and scipy. Every clip is deterministic (seeded), so a re-run rebuilds the same sound.
"""
import subprocess, sys

import numpy as np
from scipy.signal import butter, sosfilt

from wi import SR, clip_path, load_episode

slug = sys.argv[1]
force = '--force' in sys.argv


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, btype=kind, fs=SR, output='sos'), x)


def tt(secs):
    return np.arange(int(secs * SR)) / SR


def noise(n, seed):
    return np.random.default_rng(seed).standard_normal(n)


def place(buf, x, at):
    i = int(at * SR)
    j = min(len(buf), i + len(x))
    if j > i:
        buf[i:j] += x[: j - i]


def norm(x, peak=0.95):
    x = x - np.mean(x)
    return x / max(1e-9, np.abs(x).max()) * peak


def fade(x, a=0.004, b=0.03):
    x = x.copy()
    na, nb = int(a * SR), int(b * SR)
    if na:
        x[:na] *= np.linspace(0, 1, na)
    if nb:
        x[-nb:] *= np.linspace(1, 0, nb)
    return x


# ---------------------------------------------------------------- recipes
def grow(secs):
    """The power: a low swell rising into a springy overshoot (the boing of the overshoot), a whoosh climbing with it,
    a gold shimmer at the top."""
    t = tt(secs)
    top = min(0.2, 0.55 * secs)  # a short rise: the power answers its word, it doesn't sit under it
    rise = np.clip(t / top, 0, 1)
    f = 58 * (150 / 58) ** (rise ** 1.4)
    after = t > top
    f[after] = 150 + 28 * np.exp(-(t[after] - top) / 0.09) * np.cos(2 * np.pi * 7.5 * (t[after] - top))
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = sum(np.sin(k * ph) / k for k in range(1, 7))
    tone = filt(tone, 'low', 1800)
    amp = np.where(t < top, rise ** 1.6, np.exp(-(t - top) / (0.16 * secs)))
    out = 0.6 * tone * amp
    n = noise(len(t), 11)
    bands = [(250, 500, 0.15), (500, 1000, 0.3), (1000, 2000, 0.45), (2000, 4200, 0.58)]
    for lo, hi, c in bands:
        env = np.exp(-(((t / secs) - c * top / (0.55 * secs)) / 0.12) ** 2)
        out += 0.22 * filt(n, 'band', [lo, hi]) * env
    rng = np.random.default_rng(12)
    for k in range(7):
        at = top * 0.9 + rng.random() * 0.3 * secs
        fr = 2200 + rng.random() * 2800
        p = tt(0.12)
        place(out, 0.05 * np.sin(2 * np.pi * fr * p) * np.exp(-p / 0.04) * np.linspace(1, 0, len(p)) ** 0.5, at)
    return fade(norm(out), 0.01, 0.06)


def creak(secs):
    """A wooden creak: stick-slip pulses through a few narrow resonances."""
    t = tt(secs)
    rng = np.random.default_rng(21)
    pulses = np.zeros(len(t))
    at = 0.03
    while at < secs - 0.03:
        u = at / secs
        rate = 55 + 80 * np.sin(np.pi * u) + rng.normal(0, 8)
        i = int(at * SR)
        pulses[i] = (0.4 + 0.6 * np.sin(np.pi * u)) * (0.7 + 0.3 * rng.random())
        at += 1 / max(25, rate)
    body = sum(g * filt(pulses, 'band', [f * 0.95, f * 1.05]) for f, g in [(430, 1.0), (780, 0.7), (1380, 0.45), (2300, 0.2)])
    body += 0.15 * filt(noise(len(t), 22), 'band', [600, 3000]) * np.sin(np.pi * t / secs) ** 2
    return fade(norm(body), 0.01, 0.08)


def tick(secs):
    """One wall-clock tick: a hard click and a short metal ping."""
    t = tt(secs)
    out = np.zeros(len(t))
    click = filt(noise(int(0.002 * SR), 31), 'high', 2000) * np.hanning(int(0.002 * SR))
    place(out, click, 0.005)
    p = tt(0.12)
    place(out, 0.55 * np.sin(2 * np.pi * 3150 * p) * np.exp(-p / 0.016) + 0.45 * np.sin(2 * np.pi * 1240 * p) * np.exp(-p / 0.028), 0.005)
    return fade(norm(out), 0.0005, 0.02)


def rumble(secs):
    """A building groaning: low brown noise swelling and fading, a creak inside it, grit trickling down."""
    t = tt(secs)
    br = np.cumsum(noise(len(t), 41))
    br = filt(filt(br, 'high', 25), 'low', 160)
    amp = np.clip(t / 0.25, 0, 1) * np.clip((secs - t) / 0.6, 0, 1) * (0.75 + 0.25 * np.sin(2 * np.pi * 3.3 * t))
    out = norm(br * amp, 0.8)
    c = creak(0.7) * 0.25
    place(out, c, 0.35 * secs)
    rng = np.random.default_rng(42)
    for k in range(18):
        at = 0.2 * secs + rng.random() * 0.7 * secs
        g = filt(noise(int(0.01 * SR), 43 + k), 'high', 2500) * np.exp(-tt(0.01) / 0.003) * (0.04 + 0.05 * rng.random())
        place(out, g, at)
    return fade(norm(out), 0.02, 0.1)


def slide(secs):
    """A photo slid across a stone worktop: a dry hiss with grain, then it stops with a soft tap."""
    t = tt(secs)
    n = filt(noise(len(t), 51), 'band', [900, 5000])
    stop = 0.72 * secs
    grain = 0.7 + 0.3 * np.sign(np.sin(2 * np.pi * (24 + 10 * np.sin(2 * np.pi * 1.7 * t)) * t))
    amp = np.clip(t / 0.03, 0, 1) * np.clip((stop - t) / 0.08, 0, 1) * grain
    out = 0.6 * n * amp
    p = tt(0.06)
    place(out, 0.5 * filt(noise(len(p), 52), 'low', 900) * np.exp(-p / 0.012), stop)
    return fade(norm(out), 0.004, 0.03)


def bone_snap(secs):
    """A dry snap: a cluster of hard cracks, a woody body, a low thump, a few splinters."""
    t = tt(secs)
    out = np.zeros(len(t))
    for k, (at, g) in enumerate([(0.0, 1.0), (0.004, 0.8), (0.009, 0.9), (0.013, 0.6), (0.022, 0.5)]):
        b = filt(noise(int(0.012 * SR), 61 + k), 'high', 1500) * np.exp(-tt(0.012) / 0.004) * g
        place(out, b, 0.01 + at)
    p = tt(0.3)
    place(out, 0.5 * np.sin(2 * np.pi * 320 * p) * np.exp(-p / 0.04) + 0.3 * np.sin(2 * np.pi * 610 * p) * np.exp(-p / 0.025), 0.012)
    fth = 72 * (52 / 72) ** np.clip(p / 0.2, 0, 1)
    place(out, 0.7 * np.sin(2 * np.pi * np.cumsum(fth) / SR) * np.exp(-p / 0.12), 0.012)
    rng = np.random.default_rng(66)
    for k in range(9):
        at = 0.04 + rng.random() * 0.14
        s = filt(noise(int(0.004 * SR), 67 + k), 'high', 3000) * np.hanning(int(0.004 * SR)) * (0.15 + 0.2 * rng.random()) * (1 - at * 4)
        place(out, s, at)
    return fade(norm(out), 0.0005, 0.05)


def giant_step(secs):
    """A giant's footstep: a deep boom falling in pitch, a wooden thud, things rattling after it."""
    t = tt(secs)
    f = 66 * (36 / 66) ** np.clip(t / 0.5, 0, 1)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.38) + 0.25 * np.sin(4 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.2)
    thud = filt(noise(len(t), 71), 'low', 260) * np.exp(-t / 0.07)
    wood = filt(noise(len(t), 72), 'band', [380, 1300]) * np.exp(-t / 0.03)
    out = 0.8 * boom + 0.9 * norm(thud, 1) * 0.5 + 0.35 * norm(wood, 1)
    rng = np.random.default_rng(73)
    for k in range(16):
        at = 0.08 + rng.random() * 0.6
        c = filt(noise(int(0.008 * SR), 74 + k), 'high', 2800) * np.exp(-tt(0.008) / 0.002) * (0.08 + 0.08 * rng.random()) * (1 - at)
        place(out, c, at)
    return fade(norm(out), 0.001, 0.1)


def flaps(secs):
    """Pigeons' wings: soft feathery bursts at about nine a second, coming and going."""
    t = tt(secs)
    out = np.zeros(len(t))
    rng = np.random.default_rng(81)
    at = 0.02
    while at < secs - 0.06:
        b = filt(noise(int(0.045 * SR), int(at * 1000)), 'band', [350, 2600]) * np.hanning(int(0.045 * SR))
        place(out, b * (0.5 + 0.5 * np.sin(np.pi * at / secs)) * (0.6 + 0.4 * rng.random()), at)
        at += 1 / (8 + 3 * rng.random())
    return fade(norm(out, 0.8), 0.01, 0.05)


def music_loop(secs):
    """The library's music bed, looped to `secs` with a two-second crossfade (it was generated at 17 s)."""
    from wi import decode
    src = clip_path('music', 'playful quirky cartoon background music, pizzicato strings, glockenspiel and soft bass, light and curious, 110 bpm, no vocals', 17.0)
    if not src.exists():
        raise SystemExit('music_loop needs the library clip music-*.mp3 (the skill ships it)')
    x = decode(src)
    n, xf = int(secs * SR), int(2.0 * SR)
    out = x[: min(len(x), n)].copy()
    while len(out) < n:
        k = min(xf, len(out))
        ramp = np.linspace(0, 1, k)
        nxt = x.copy()
        out[-k:] = out[-k:] * (1 - ramp) + nxt[:k] * ramp
        out = np.concatenate([out, nxt[k:]])
    return fade(norm(out[:n], 0.9), 0.01, 1.0)


RECIPES = {f.__name__: f for f in [grow, creak, tick, rumble, slide, bone_snap, giant_step, flaps, music_loop]}


def write_mp3(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2').tobytes()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '-', '-c:a', 'libmp3lame', '-b:a', '192k', str(path)], input=pcm, check=True)


ep = load_episode(slug)
made, kept, missing = [], [], []
for name, (prompt, secs) in ep['sound']['clips'].items():
    p = clip_path(name, prompt, secs)
    if not prompt.startswith('procedural:'):
        (kept if p.exists() else missing).append(name)
        continue
    if p.exists() and not force:
        kept.append(name)
        continue
    base = name if name in RECIPES else name.split('_v')[0]
    if base not in RECIPES:
        raise SystemExit(f'No recipe for the procedural clip "{name}": recipes are {", ".join(RECIPES)}')
    write_mp3(p, RECIPES[base](float(secs)))
    made.append(name)
print(f'procedural clips made: {", ".join(made) or "none"}; already in the library: {", ".join(kept) or "none"}')
if missing:
    print(f'! not in the library and not procedural (sfx.py would generate them with ElevenLabs): {", ".join(missing)}')
