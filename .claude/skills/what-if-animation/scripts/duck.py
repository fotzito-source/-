"""After sfx.py: the voice comes first. Wherever someone is speaking, the effects stem is pulled down to stay at least
`--sfx` dB under the voice and the music `--music` dB under it, at their mix volumes; in the pauses every hit keeps its
full weight. The gain moves fast down (20 ms) and slowly back up (250 ms), so a hit that starts in a pause and runs into
a word is tucked under the word instead of being cut.

python <skill>/scripts/duck.py <slug> [--sfx 6] [--music 10] [--max 18]
Reads  public/<slug>/voice.wav, sfx.wav, music.wav and the volumes sfx.py wrote in timeline.json
Writes public/<slug>/sfx.wav and music.wav (ducked); run mixcheck.py after it.
"""
import json
import sys

import numpy as np

from wi import SR, decode, ep_dir, pub_dir, stem, write_wav

slug = sys.argv[1]


def opt(name, default):
    return float(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


MARGIN = {'sfx': opt('--sfx', 6.0), 'music': opt('--music', 10.0)}
MAX = opt('--max', 18.0)
tl = json.loads((ep_dir(slug) / 'timeline.json').read_text(encoding='utf-8'))
A = tl['audio']
hop, win = SR // 100, SR // 20  # 10 ms frames, 50 ms windows


def env_db(x):
    p = np.convolve(x ** 2, np.ones(win) / win, mode='same')[::hop]
    return 10 * np.log10(p + 1e-12)


voice = decode(stem(slug, 'voice')) * A.get('voiceVol', 1)
v = env_db(voice)
speaking = float(np.percentile(v[v > -60], 70)) - 10  # frames this loud are words, not pauses
active = v > speaking
grow = 10  # hold the ducking 100 ms around each word
active = np.convolve(active.astype(float), np.ones(2 * grow + 1), mode='same') > 0
for name in ('sfx', 'music'):
    path = pub_dir(slug) / f'{name}.wav'
    if not path.exists():
        continue
    raw = decode(path)
    x = raw[:len(voice)] if len(raw) >= len(voice) else np.pad(raw, (0, len(voice) - len(raw)))
    e = env_db(x * A.get(f'{name}Vol', 1))
    n = min(len(e), len(v))
    need = np.zeros(len(e))
    need[:n] = np.where(active[:n], np.minimum(0.0, (v[:n] - MARGIN[name]) - e[:n]), 0.0)
    need = np.maximum(need, -MAX)
    # fast attack, slow release: hold the deepest cut 60 ms, then smooth up over 250 ms
    held = np.array([need[max(0, i - 3): i + 4].min() for i in range(len(need))])
    g = np.empty_like(held)
    cur = 0.0
    up = 1 - np.exp(-1 / 25.0)  # 250 ms back up
    for i, t in enumerate(held):
        cur = t if t < cur else cur + (t - cur) * up
        g[i] = cur
    gain = np.interp(np.arange(len(x)) / hop, np.arange(len(g)), 10 ** (g / 20))
    out = raw.copy()
    m = min(len(raw), len(gain))
    out[:m] = raw[:m] * gain[:m]
    write_wav(path, out)
    cut = g[g < -0.5]
    print(f'{name}: ducked under the voice for {len(cut) / 100:.1f} s, by {(-cut.mean() if len(cut) else 0):.1f} dB on average'
          f' (at most {(-g.min()):.1f} dB)')
