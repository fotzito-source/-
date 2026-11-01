#!/usr/bin/env python3
"""Pose la voix off sur le spot Nuraq et mixe avec les effets sonores.

    python3 mix-voix.py voix/                 # un fichier par réplique (01…12), placés à leur temps
    python3 mix-voix.py voix-off.mp3          # un seul fichier : découpé aux silences si possible
    python3 mix-voix.py voix-off.mp3 --tel-quel   # un seul fichier calé sur la vidéo, posé à 0:00
    python3 mix-voix.py --plan son/voix-placement.json   # placement exact, réplique par réplique

Sortie : son/nuraq-spot-voix.wav, puis nuraq-spot-9x16-voix.mp4 et nuraq-spot-16x9-voix.mp4
(image copiée telle quelle, son normalisé vers −16 LUFS). Les temps viennent de voix-off.txt.
"""

import argparse
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SR = 48000
DURATION = 26.4
# Début de chaque réplique (secondes), dans l'ordre de voix-off.txt.
LINES = [1.30, 2.60, 5.10, 7.15, 9.80, 12.85, 15.25, 17.50, 20.05, 20.65, 21.25, 23.60]
DUCK_DB = 9.0  # baisse des effets sous la voix


def load(path):
    """Décode n'importe quel fichier audio (mp3, m4a, wav…) en mono 48 kHz."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-ac", "1", "-ar", str(SR), str(wav)], check=True)
        with wave.open(str(wav), "rb") as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768


def load_stereo(path):
    with wave.open(str(path), "rb") as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
        return x.reshape(-1, w.getnchannels()).T


def envelope(x, win=0.02):
    n = max(1, int(win * SR))
    return np.sqrt(np.convolve(x ** 2, np.ones(n) / n, mode="same"))


def trim(x, pad=0.03):
    e = envelope(x)
    loud = np.nonzero(e > max(e.max() * 0.03, 1e-4))[0]
    if not len(loud):
        return x
    p = int(pad * SR)
    return x[max(0, loud[0] - p):loud[-1] + p]


def split_on_silence(x, min_sil=0.35, min_seg=0.12):
    e = envelope(x)
    on = e > max(e.max() * 0.04, 1e-4)
    segs, i, n = [], 0, len(x)
    while i < n:
        if not on[i]:
            i += 1
            continue
        j = i
        quiet = 0
        while j < n and quiet < int(min_sil * SR):
            quiet = quiet + 1 if not on[j] else 0
            j += 1
        end = j - quiet
        if end - i > int(min_seg * SR):
            segs.append(x[i:end])
        i = j
    return segs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("voix", nargs="?", help="dossier (un fichier par réplique) ou fichier unique")
    ap.add_argument("--tel-quel", action="store_true", help="fichier unique déjà calé sur la vidéo, posé à 0:00")
    ap.add_argument("--plan", help="placement JSON : passages du fichier source et instant de chaque réplique")
    args = ap.parse_args()

    n = int(DURATION * SR)
    voice = np.zeros(n)
    placements = []
    src = Path(args.voix) if args.voix else None
    if args.plan:
        plan_path = Path(args.plan)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        x = load(src or plan_path.parent / plan["source"])
        pad = plan.get("pad", 0.04)
        fade = int(0.008 * SR)
        extra = {}

        def cut(t0, t1, p0, p1, source=None):
            xs = x
            if source:  # réplique régénérée à part (autre fichier)
                if source not in extra:
                    extra[source] = load(plan_path.parent / source)
                xs = extra[source]
            c = xs[max(0, int((t0 - p0) * SR)):int((t1 + p1) * SR)].copy()
            c[:fade] *= np.linspace(0, 1, fade)
            c[-fade:] *= np.linspace(1, 0, fade)
            return c

        for line in plan["lines"]:
            if "pieces" in line:
                # réplique remontée à partir de plusieurs passages, séparés par de courtes pauses
                gaps = line.get("gaps", [0.05] * (len(line["pieces"]) - 1))
                parts = []
                for k, (t0, t1) in enumerate(line["pieces"]):
                    first, last = k == 0, k == len(line["pieces"]) - 1
                    parts.append(cut(t0, t1, pad if first else 0.012, pad if last else 0.012))
                    if not last:
                        parts.append(np.zeros(int(gaps[k] * SR)))
                clip = np.concatenate(parts)
                dur = sum(t1 - t0 for t0, t1 in line["pieces"]) + sum(gaps)
            else:
                clip = cut(line["from"], line["to"], pad, pad, line.get("source"))
                dur = line["to"] - line["from"]
            clip = clip * 10 ** (line.get("gain_db", 0) / 20)
            at = int((line["at"] - pad) * SR)
            j = min(n, at + len(clip))
            voice[at:j] += clip[:j - at]
            placements.append((line["n"], line["at"], dur))
        clips = None
    elif src.is_dir():
        files = sorted(p for p in src.iterdir() if p.suffix.lower() in {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"})
        clips = [trim(load(p)) for p in files]
    elif args.tel_quel:
        clips = None
        x = load(src)[:n]
        voice[:len(x)] = x
    else:
        x = load(src)
        clips = [trim(c) for c in split_on_silence(x)]
        if len(clips) != len(LINES):
            print(f"{len(clips)} répliques détectées au lieu de {len(LINES)} : le fichier est posé tel quel à 0:00.", file=sys.stderr)
            clips = None
            voice[:min(n, len(x))] = x[:n]

    if clips is not None:
        if len(clips) != len(LINES):
            print(f"Attention : {len(clips)} fichiers pour {len(LINES)} répliques ; placement dans l'ordre.", file=sys.stderr)
        t_free = 0.0
        for k, clip in enumerate(clips):
            t = max(LINES[k] if k < len(LINES) else t_free + 0.3, t_free + 0.12)
            if k < len(LINES) and t - LINES[k] > 0.25:
                print(f"Réplique {k + 1:02d} décalée de {t - LINES[k]:.2f} s (la précédente est longue).", file=sys.stderr)
            i = int(t * SR)
            j = min(n, i + len(clip))
            voice[i:j] += clip[:j - i]
            placements.append((k + 1, t, len(clip) / SR))
            t_free = t + len(clip) / SR
        if t_free > DURATION - 0.3:
            print(f"Attention : la voix finit à {t_free:.1f} s, après la fin du spot ({DURATION} s).", file=sys.stderr)

    # voix : coupe-bas doux (70 Hz), −3 dBFS de crête ; effets baissés sous la voix
    f = np.fft.rfftfreq(n, 1 / SR)
    voice = np.fft.irfft(np.fft.rfft(voice) * (1 - 1 / np.sqrt(1 + (f / 70) ** 4)), n)
    voice *= 10 ** (-3 / 20) / max(np.abs(voice).max(), 1e-9)
    sfx = load_stereo(HERE / "son" / "nuraq-spot.wav")[:, :n]
    env = envelope(voice, 0.05)
    env = np.convolve(env, np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")  # relâchement doux
    duck = 1 - (1 - 10 ** (-DUCK_DB / 20)) * np.clip(env / (env.max() * 0.25 + 1e-9), 0, 1)
    mix = sfx * duck[None, :] + voice[None, :] * 0.95
    mix /= max(1.0, np.abs(mix).max() / 0.98)

    out_wav = HERE / "son" / "nuraq-spot-voix.wav"
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix.T, -1, 1) * 32767).astype(np.int16).tobytes())
    for k, t, d in placements:
        print(f"réplique {k:02d} : {t:5.2f} s → {t + d:5.2f} s")

    for fmt in ("9x16", "16x9"):
        video = HERE / f"nuraq-spot-{fmt}.mp4"
        out = HERE / f"nuraq-spot-{fmt}-voix.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(out_wav), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", "-movflags", "+faststart", str(out)], check=True)
        print(out)


if __name__ == "__main__":
    main()
