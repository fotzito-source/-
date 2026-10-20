#!/usr/bin/env python3
"""Génère la voix off de la vidéo 01 avec l'API Cartesia, une réplique par fichier.

La clé API est lue dans la variable d'environnement CARTESIA_API_KEY. Ne jamais l'écrire
dans un fichier du dépôt.

    export CARTESIA_API_KEY=sk_car_…
    python3 voix.py --list                  # voix françaises masculines, de la plus douce à la moins douce
    python3 voix.py                         # choisit une voix d'homme douce et remplit voix/
    python3 voix.py --voice-id <id>         # impose une voix précise
    python3 voix.py --only 9,10 --force     # régénère seulement certaines répliques
    python3 render.py --voix voix           # vidéo calée sur la voix → video-voix-off.mp4

Sortie : voix/ligne_01.wav … ligne_19.wav (mono, 48 kHz, silences de début et de fin coupés)
et voix/manifest.json (durées, voix utilisée, horaires des mots quand l'API les fournit).
Le texte vient de VO_TTS dans render.py : on corrige une prononciation là-bas.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from render import VO, VO_TTS  # noqa: E402

API = "https://api.cartesia.ai"
API_VERSION = "2025-04-16"
SAMPLE_RATE = 48000

SOFT_WORDS = ("calm", "soft", "gentle", "warm", "sooth", "relax", "narrat", "serene", "smooth",
              "kind", "friendly", "reassur", "doux", "douce", "calme", "chaleur", "posé", "apais")
HARD_WORDS = ("stern", "angry", "energetic", "excit", "upbeat", "sport", "announc", "intense",
              "commercial", "promo", "aggress", "loud", "salesman")
FEMALE_WORDS = ("woman", "female", "lady", "girl", "femme", "feminine")
MALE_WORDS = ("man", "male", "guy", "homme", "masculine", "gentleman")


def api_key():
    key = os.environ.get("CARTESIA_API_KEY", "").strip()
    if not key:
        raise SystemExit("Définis la variable d'environnement CARTESIA_API_KEY.")
    return key


def request(method, path, body=None, params=None, stream=False):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "X-API-Key": api_key(),
        "Cartesia-Version": API_VERSION,
        "Content-Type": "application/json",
        "Accept": "text/event-stream" if stream else "*/*",
    })
    try:
        return urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"HTTP {e.code} sur {path} : {detail}") from None


# ---------------------------------------------------------------------------
# Voix
# ---------------------------------------------------------------------------

def list_voices():
    voices, params = [], {"limit": 100, "language": "fr"}
    while True:
        payload = json.load(request("GET", "/voices/", params=params))
        page = payload.get("data", []) if isinstance(payload, dict) else payload
        voices += page
        if not (isinstance(payload, dict) and payload.get("has_more") and page):
            break
        params["starting_after"] = page[-1]["id"]
    return [v for v in voices if str(v.get("language", "fr")).lower().startswith("fr")]


def softness(v):
    text = f"{v.get('name', '')} {v.get('description', '')}".lower()
    gender = str(v.get("gender") or "").lower()
    if gender.startswith("fem") or any(w in text for w in FEMALE_WORDS):
        return None
    score = 3 if gender.startswith("masc") or any(w in text.split() for w in MALE_WORDS) else 0
    score += 2 * sum(w in text for w in SOFT_WORDS)
    score -= 2 * sum(w in text for w in HARD_WORDS)
    return score


def ranked_male_voices():
    scored = [(softness(v), v) for v in list_voices()]
    scored = [(s, v) for s, v in scored if s is not None]
    return [v for s, v in sorted(scored, key=lambda sv: -sv[0])]


# ---------------------------------------------------------------------------
# Synthèse
# ---------------------------------------------------------------------------

def tts_body(text, voice_id, model, container):
    fmt = {"container": container, "encoding": "pcm_s16le", "sample_rate": SAMPLE_RATE}
    return {"model_id": model, "transcript": text, "voice": {"mode": "id", "id": voice_id},
            "output_format": fmt, "language": "fr"}


def synth_with_timestamps(text, voice_id, model):
    """Flux SSE : audio PCM brut + horaires des mots."""
    body = tts_body(text, voice_id, model, "raw")
    body["add_timestamps"] = True
    pcm, words = bytearray(), {"words": [], "start": [], "end": []}
    with request("POST", "/tts/sse", body, stream=True) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            ev = json.loads(line[5:].strip() or "{}")
            if ev.get("type") == "error" or ev.get("error"):
                raise RuntimeError(f"erreur Cartesia : {ev}")
            if ev.get("data"):
                pcm += base64.b64decode(ev["data"])
            wt = ev.get("word_timestamps")
            if wt:
                for k in words:
                    words[k] += wt.get(k, [])
            if ev.get("done") or ev.get("type") == "done":
                break
    x = np.frombuffer(bytes(pcm), dtype=np.int16)
    w = [{"w": a, "start": float(b), "end": float(c)} for a, b, c in zip(words["words"], words["start"], words["end"])]
    return x, w


def synth_bytes(text, voice_id, model):
    """Repli sans horaires des mots : fichier WAV complet."""
    with request("POST", "/tts/bytes", tts_body(text, voice_id, model, "wav")) as resp:
        blob = resp.read()
    tmp = HERE / ".cache" / "tts.wav"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(blob)
    with wave.open(str(tmp), "rb") as wv:
        if wv.getframerate() != SAMPLE_RATE or wv.getsampwidth() != 2:
            raise RuntimeError("format WAV inattendu")
        x = np.frombuffer(wv.readframes(wv.getnframes()), dtype=np.int16)
        if wv.getnchannels() > 1:
            x = x.reshape(-1, wv.getnchannels()).mean(axis=1).astype(np.int16)
    return x, None


def trim(x, words, pad=0.04):
    """Coupe les silences de début et de fin, décale les horaires des mots en conséquence."""
    if not len(x):
        raise RuntimeError("audio vide")
    a = np.abs(x.astype(np.float64)) / 32768
    win = int(0.01 * SAMPLE_RATE)
    env = np.convolve(a, np.ones(win) / win, mode="same")
    loud = np.nonzero(env > max(10 ** (-45 / 20), env.max() * 0.02))[0]
    i0 = max(0, loud[0] - int(pad * SAMPLE_RATE)) if len(loud) else 0
    i1 = min(len(x), loud[-1] + int(pad * SAMPLE_RATE)) if len(loud) else len(x)
    shift = i0 / SAMPLE_RATE
    if words:
        words = [dict(w, start=max(0.0, w["start"] - shift), end=max(0.0, w["end"] - shift)) for w in words]
    y = x[i0:i1].astype(np.float64)
    fade = int(0.01 * SAMPLE_RATE)
    y[:fade] *= np.linspace(0, 1, fade)
    y[-fade:] *= np.linspace(1, 0, fade)
    return y.astype(np.int16), words


def save_wav(path, x):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(x.tobytes())


def synthesize(text, voice_id, models):
    last = None
    for model in models:
        for fn in (synth_with_timestamps, synth_bytes):
            try:
                x, words = fn(text, voice_id, model)
                return x, words, model
            except Exception as e:  # on essaie le mode ou le modèle suivant
                last = e
                print(f"  ({fn.__name__} / {model} : {e})", file=sys.stderr)
    raise SystemExit(f"Synthèse impossible : {last}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="liste les voix françaises masculines")
    ap.add_argument("--voice-id", help="identifiant Cartesia de la voix (sinon : la plus douce trouvée)")
    ap.add_argument("--model", default="sonic-3", help="modèle Cartesia (repli automatique sur sonic-2)")
    ap.add_argument("--out", default=str(HERE / "voix"))
    ap.add_argument("--only", help="numéros de répliques à (re)générer, ex. 9,10")
    ap.add_argument("--force", action="store_true", help="régénère même si le fichier existe")
    args = ap.parse_args()

    if args.list:
        for v in ranked_male_voices()[:25]:
            print(f"{v['id']}  {v.get('name', '')} — {str(v.get('description', ''))[:90]}")
        return

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    voice_id = args.voice_id or manifest.get("voice", {}).get("id")
    voice_name = manifest.get("voice", {}).get("name", "") if voice_id == manifest.get("voice", {}).get("id") else ""
    if not voice_id:
        ranked = ranked_male_voices()
        if not ranked:
            raise SystemExit("Aucune voix française masculine trouvée : passe --voice-id.")
        voice_id, voice_name = ranked[0]["id"], ranked[0].get("name", "")
        print(f"Voix choisie : {voice_name} ({voice_id})")
    only = {int(v) for v in args.only.split(",")} if args.only else None
    if manifest.get("voice", {}).get("id") not in (None, voice_id):
        args.force, only = True, None  # changement de voix : tout régénérer
    lines = manifest.get("lines") or [None] * len(VO)
    models = [args.model] + [m for m in ("sonic-2",) if m != args.model]
    used_model = manifest.get("model")
    for i, text in enumerate(VO_TTS, start=1):
        path = out / f"ligne_{i:02d}.wav"
        exists = bool(lines[i - 1]) and path.exists()
        todo = (i in only or not exists) if only is not None else (args.force or not exists)
        if not todo:
            continue
        print(f"[{i:02d}/{len(VO_TTS)}] {text}")
        x, words, used_model = synthesize(text, voice_id, models)
        x, words = trim(x, words)
        save_wav(path, x)
        lines[i - 1] = {"file": path.name, "text": VO[i - 1][2], "tts": text,
                        "duration": round(len(x) / SAMPLE_RATE, 3), "words": words}

    manifest = {"voice": {"id": voice_id, "name": voice_name}, "model": used_model,
                "sample_rate": SAMPLE_RATE, "lines": lines}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(l["duration"] for l in lines)
    print(f"{len(lines)} répliques, {total:.1f} s de voix → {manifest_path}")


if __name__ == "__main__":
    main()
