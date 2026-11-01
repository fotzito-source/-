"""Step 2, for a French episode: the voice, with word timings, then the pauses tightened exactly as voice.py does.

Two engines, so the pipeline runs with or without a TTS account (voice.py stays the ElevenLabs path):
  cartesia  the Cartesia API (key in CARTESIA_API_KEY, never in a file; api.cartesia.ai must be reachable).
            One take for the whole script, word timestamps from the API.
  local     a Piper voice run offline (piper-tts + onnx). One chunk per sentence, word timings from the model's own
            phoneme durations. Good enough to time the edit and the sound; a provisional voice, not the final one.
  auto      cartesia when CARTESIA_API_KEY is set, local otherwise.

python <skill>/scripts/voice_fr.py <slug> [--backend auto|cartesia|local] [--force] [--list] [--from-audio take.wav]
  --list         Cartesia voices in the episode's language, male first (needs the key)
  --from-audio   use a finished take (exported from Cartesia's site, recorded...): its word timings come from aligning
                 it (DTW on MFCCs, librosa) on the local Piper reading of the same text
Reads  src/episodes/<slug>/episode.json: script (each beat's "text", or "tts" for a phonetic spelling with the same
       number of words), voice, gaps
Writes public/<slug>/voice_raw.wav, public/<slug>/voice.wav (tightened), src/episodes/<slug>/words.json,
       out/<slug>/words_raw.json, out/<slug>/voice_meta.json, a line in out/<slug>/costs.json.
The engine is only called when the text, the engine or its settings change (cached by a hash): retuning the gaps is free.

episode.json "voice": {"backend": "auto",
  "local": {"model": "fr_FR-tom-medium", "length_scale": 0.92, "noise_scale": 0.62, "noise_w_scale": 0.8},
  "cartesia": {"model": "sonic-3", "id": null, "language": "fr", "speed": null}}
Setup for local: pip install piper-tts onnx  (the voice model downloads once into .cache/tts/ in the studio)
"""
import argparse, base64, hashlib, json, os, re, sys, tarfile, time, urllib.error, urllib.parse, urllib.request

import numpy as np

from wi import SR, STUDIO, decode, ep_dir, load_episode, load_json, out_dir, pub_dir, save_json, write_wav

ap = argparse.ArgumentParser()
ap.add_argument('slug')
ap.add_argument('--backend', choices=['auto', 'cartesia', 'local'])
ap.add_argument('--force', action='store_true')
ap.add_argument('--list', action='store_true')
ap.add_argument('--from-audio', help='a take recorded elsewhere (the Cartesia site, a microphone): word timings by aligning it on the local voice')
args = ap.parse_args()
slug = args.slug
ep = load_episode(slug)
V = {'backend': 'auto', 'local': {}, 'cartesia': {}}
V.update(ep.get('voice', {}))
LOCAL = {'model': 'fr_FR-tom-medium', 'length_scale': 0.92, 'noise_scale': 0.62, 'noise_w_scale': 0.8, **V.get('local', {})}
CART = {'model': 'sonic-3', 'id': None, 'language': 'fr', 'speed': None, **V.get('cartesia', {})}
backend = args.backend or V.get('backend', 'auto')
if backend == 'auto':
    backend = 'cartesia' if os.environ.get('CARTESIA_API_KEY', '').strip() else 'local'

shown = ' '.join(b['text'].strip() for b in ep['script'])
spoken = ' '.join(b.get('tts', b['text']).strip() for b in ep['script'])


def tokens(text):
    """Words and the punctuation after each, the way voice.py reads ElevenLabs' characters: a word is a run of
    letters, digits and apostrophes; anything else that isn't a space belongs to the word before it."""
    words, cur = [], None
    for ch in text:
        if re.match(r"[\w'’]", ch):
            if cur is None:
                cur = {'w': '', 'p': ''}
            cur['w'] += ch
        else:
            if cur is not None:
                words.append(cur)
                cur = None
            if words and ch.strip():
                words[-1]['p'] += ch
    if cur:
        words.append(cur)
    return words


SHOWN = tokens(shown)

# ---------------------------------------------------------------- Cartesia
CART_API = 'https://api.cartesia.ai'
CART_VERSION = '2025-04-16'


def cart(method, path, body=None, params=None, stream=False):
    key = os.environ.get('CARTESIA_API_KEY', '').strip()
    if not key:
        raise SystemExit('No Cartesia key: set CARTESIA_API_KEY in the environment (never in a file).')
    url = CART_API + path + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method, headers={
        'X-API-Key': key, 'Cartesia-Version': CART_VERSION, 'Content-Type': 'application/json',
        'Accept': 'text/event-stream' if stream else '*/*'})
    try:
        return urllib.request.urlopen(req, timeout=180)
    except urllib.error.HTTPError as e:
        raise SystemExit(f'Cartesia HTTP {e.code} on {path}: {e.read().decode("utf-8", "replace")[:400]}')
    except urllib.error.URLError as e:
        raise SystemExit(f'Cartesia unreachable ({e.reason}): is api.cartesia.ai allowed by the network policy?')


def cart_voices():
    out, params = [], {'limit': 100, 'language': CART['language']}
    while True:
        page = json.load(cart('GET', '/voices/', params=params))
        data = page.get('data', []) if isinstance(page, dict) else page
        out += data
        if not (isinstance(page, dict) and page.get('has_more') and data):
            break
        params['starting_after'] = data[-1]['id']
    return [v for v in out if str(v.get('language', CART['language'])).lower().startswith(CART['language'])]


def narrator_score(v):
    """A What If narrator: a man's voice, young and lively, made for storytelling. None for women's voices."""
    txt = f"{v.get('name', '')} {v.get('description', '')}".lower()
    gender = str(v.get('gender') or '').lower()
    if gender.startswith('fem') or any(w in txt for w in ('woman', 'female', 'lady', 'girl', 'femme')):
        return None
    s = 3 if gender.startswith('masc') or re.search(r'\b(man|male|guy|homme)\b', txt) else 0
    s += 2 * sum(w in txt for w in ('narrat', 'story', 'young', 'energetic', 'friendly', 'conversational', 'expressive', 'engaging'))
    s -= 2 * sum(w in txt for w in ('old', 'deep', 'calm', 'sooth', 'whisper', 'meditat', 'announc', 'commercial'))
    return s


def cart_pick():
    ranked = sorted(((narrator_score(v), v) for v in cart_voices()), key=lambda sv: -(sv[0] if sv[0] is not None else -99))
    ranked = [v for s, v in ranked if s is not None]
    if not ranked:
        raise SystemExit('No French male voice found on Cartesia: set voice.cartesia.id in episode.json.')
    return ranked


def cart_take(text, voice_id):
    body = {'model_id': CART['model'], 'transcript': text, 'voice': {'mode': 'id', 'id': voice_id}, 'language': CART['language'],
            'output_format': {'container': 'raw', 'encoding': 'pcm_s16le', 'sample_rate': SR}, 'add_timestamps': True}
    if CART.get('speed'):
        body['generation_config'] = {'speed': CART['speed']}
    pcm, ts = bytearray(), {'words': [], 'start': [], 'end': []}
    with cart('POST', '/tts/sse', body, stream=True) as resp:
        for raw in resp:
            line = raw.decode('utf-8', 'replace').strip()
            if not line.startswith('data:'):
                continue
            ev = json.loads(line[5:].strip() or '{}')
            if ev.get('type') == 'error' or ev.get('error'):
                raise SystemExit(f'Cartesia error: {ev}')
            if ev.get('data'):
                pcm += base64.b64decode(ev['data'])
            wt = ev.get('word_timestamps')
            if wt:
                for k in ts:
                    ts[k] += wt.get(k, [])
            if ev.get('done') or ev.get('type') == 'done':
                break
    x = np.frombuffer(bytes(pcm), dtype=np.int16).astype(np.float64) / 32768
    words = []
    for w, s, e in zip(ts['words'], ts['start'], ts['end']):
        tk = tokens(w)
        if not tk:  # a bare punctuation mark: it belongs to the word before
            if words:
                words[-1]['p'] += w.strip()
            continue
        words.append({'w': tk[0]['w'], 's': float(s), 'e': float(e), 'p': tk[0]['p']})
    return x, SR, words


# ---------------------------------------------------------------- local (Piper)
MODELS = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-{name}.tar.bz2'


def local_model(name):
    d = STUDIO / '.cache' / 'tts' / f'vits-piper-{name}'
    onnx = d / f'{name}.onnx'
    if not onnx.exists():
        d.parent.mkdir(parents=True, exist_ok=True)
        tar = d.parent / f'{name}.tar.bz2'
        print(f'downloading the Piper voice {name} (once)')
        urllib.request.urlretrieve(MODELS.format(name=name), tar)
        with tarfile.open(tar) as tf:
            tf.extractall(d.parent, filter='data')
        tar.unlink()
    return onnx


def local_take(text):
    try:
        from piper import PiperVoice, SynthesisConfig
    except ImportError:
        raise SystemExit('The local voice needs piper-tts and onnx: pip install piper-tts onnx')
    voice = PiperVoice.load(str(local_model(LOCAL['model'])), include_alignments=True)
    cfg = SynthesisConfig(length_scale=LOCAL['length_scale'], noise_scale=LOCAL['noise_scale'], noise_w_scale=LOCAL['noise_w_scale'])
    sr = voice.config.sample_rate
    gap = np.zeros(int(0.5 * sr))  # between sentences; the tightening below cuts it to the gaps in episode.json
    parts, words, at = [], [], 0
    for ch in voice.synthesize(text, cfg, include_alignments=True):
        if not ch.phoneme_alignments:
            raise SystemExit('This Piper voice gives no phoneme alignments: try another model.')
        # walk the phonemes: a space or a pause mark closes a word; the samples before it are the word's span.
        # espeak's "-" is a link inside a word ("te-z ˈɔs" for "tes os"), not a break.
        n, cur, groups = 0, None, []
        for al in ch.phoneme_alignments:
            ph = al.phoneme
            if ph in (' ', '^', '$', '_') or re.match(r'^[.,:;!?…—–"«»()]+$', ph):
                if cur is not None:
                    groups.append(cur)
                    cur = None
            else:
                if cur is None:
                    cur = [n, n, '']
                cur[1] = n + int(al.num_samples)
                cur[2] += ph
            n += int(al.num_samples)
        if cur is not None:
            groups.append(cur)
        for s, e, ph in groups:
            words.append({'s': (at + s) / sr, 'e': (at + e) / sr, 'ph': ph})
        parts += [ch.audio_float_array.astype(np.float64), gap]
        at += len(ch.audio_float_array) + len(gap)
    x = np.concatenate(parts)
    return x, sr, split_merged(voice, text, words)


def plen(voice, word):
    ph = ''.join(''.join(p) for p in voice.phonemize(word))
    return max(1, len(re.sub(r"[ˈˌː.,:;!?…\s-]", '', ph)))


def split_merged(voice, text, groups):
    """espeak joins some words into one phoneme group ("of the", "in the", "her… or"): give each script word its own
    span, splitting a joined group in proportion to the words' own phoneme lengths."""
    names = [w['w'] for w in tokens(text)]
    if len(names) == len(groups):
        return groups
    L = [plen(voice, w) for w in names]
    G = [max(1, len(re.sub(r"[ˈˌː-]", '', g['ph']))) for g in groups]
    out, i = [], 0
    for j, g in enumerate(groups):
        k, tot = 1, L[i]
        while i + k < len(names) and len(names) - (i + k) > len(groups) - (j + 1) and abs(tot + L[i + k] - G[j]) < abs(tot - G[j]):
            tot += L[i + k]
            k += 1
        if j == len(groups) - 1:
            k = len(names) - i
            tot = sum(L[i:i + k])
        at = g['s']
        for m in range(k):
            d = (g['e'] - g['s']) * L[i + m] / tot
            out.append({'s': at, 'e': at + d})
            at += d
        i += k
    return out


def file_take(path, text):
    """A take made elsewhere: read it, trim its silences at both ends, then find each word in it by aligning it on the
    local voice reading the same text (whose word timings we know), with DTW over MFCCs."""
    try:
        import librosa
    except ImportError:
        raise SystemExit('--from-audio needs librosa: pip install librosa')
    y = decode(path)
    env = np.convolve(np.abs(y), np.ones(441) / 441, mode='same')
    loud = np.nonzero(env > max(1e-4, env.max() * 0.02))[0]
    y = y[max(0, loud[0] - 2205): loud[-1] + 2205]
    ref, rsr, rwords = local_take(text)
    hop, sr = 256, 22050
    def feats(x, xsr):
        x = librosa.resample(np.asarray(x, dtype=np.float32), orig_sr=xsr, target_sr=sr)
        m = librosa.feature.mfcc(y=x, sr=sr, n_mfcc=20, hop_length=hop)
        return (m - m.mean(axis=1, keepdims=True)) / (m.std(axis=1, keepdims=True) + 1e-6)
    A, B = feats(ref, rsr), feats(y, SR)
    _, wp = librosa.sequence.dtw(X=A, Y=B, metric='cosine')
    wp = wp[::-1]
    ta, tb = wp[:, 0] * hop / sr, wp[:, 1] * hop / sr
    ua, idx = np.unique(ta, return_index=True)
    m = lambda t: float(np.interp(t, ua, tb[idx]))
    words = [{'s': m(w['s']), 'e': max(m(w['s']) + 0.03, m(w['e']))} for w in rwords]
    return y, SR, words


# ---------------------------------------------------------------- the take
if args.list:
    for v in cart_pick()[:30]:
        print(f"{v['id']}  {v.get('name', '')}: {str(v.get('description', ''))[:100]}")
    sys.exit(0)

meta = load_json(out_dir(slug) / 'voice_meta.json', {}) or {}
settings = LOCAL if backend == 'local' else CART
src_sig = hashlib.sha1(open(args.from_audio, 'rb').read()).hexdigest() if args.from_audio else ''
sig = hashlib.sha1(json.dumps([spoken, backend, settings, src_sig], sort_keys=True).encode()).hexdigest()[:12]
raw_wav = pub_dir(slug) / 'voice_raw.wav'
raw_words = out_dir(slug) / 'words_raw.json'

if args.force or meta.get('sig') != sig or not raw_wav.exists() or not raw_words.exists():
    t0 = time.time()
    if args.from_audio:
        print(f'aligning {args.from_audio} on the local voice ({LOCAL["model"]})')
        x, sr, timed = file_take(args.from_audio, spoken)
        info = {'backend': 'file', 'file': str(args.from_audio)}
        cost = {'step': 'voice (take from a file)', 'credits': 0, 'note': f'{args.from_audio}, made outside the pipeline'}
    elif backend == 'cartesia':
        vid = CART.get('id') or (meta.get('voice_id') if meta.get('backend') == 'cartesia' else None)
        name = ''
        if not vid:
            best = cart_pick()[0]
            vid, name = best['id'], best.get('name', '')
            print(f'Cartesia voice: {name} ({vid}); pin it with voice.cartesia.id in episode.json')
        print(f'{len(spoken)} characters to Cartesia ({CART["model"]})')
        x, sr, timed = cart_take(spoken, vid)
        info = {'backend': 'cartesia', 'voice_id': vid, 'voice_name': name, 'model': CART['model']}
        cost = {'step': 'voice (Cartesia)', 'credits': 0, 'note': f'{len(spoken)} characters billed by Cartesia, not ElevenLabs'}
    else:
        print(f'local Piper voice {LOCAL["model"]}: {len(spoken)} characters, no API, no cost')
        x, sr, timed = local_take(spoken)
        info = {'backend': 'local', 'model': LOCAL['model']}
        cost = {'step': 'voice (local Piper)', 'credits': 0, 'note': 'provisional offline voice, no API'}
    # the words on screen (and in the cues) are the script's, whatever spelling the engine was given
    if len(timed) != len(SHOWN):
        print(f'! the engine gave {len(timed)} words for the {len(SHOWN)} of the script: timings follow the engine, check words.json')
        names = tokens(spoken)
        words = [{'w': (names[i]['w'] if i < len(names) else w.get('w', '?')), 's': w['s'], 'e': w['e'], 'p': (names[i]['p'] if i < len(names) else w.get('p', ''))} for i, w in enumerate(timed)]
    else:
        words = [{'w': SHOWN[i]['w'], 's': w['s'], 'e': w['e'], 'p': SHOWN[i]['p']} for i, w in enumerate(timed)]
    for w in words:
        w['s'], w['e'] = round(w['s'], 3), round(w['e'], 3)
    x = x / max(1e-9, np.abs(x).max()) * 0.89
    import wave
    with wave.open(str(raw_wav), 'wb') as wv:
        wv.setnchannels(1)
        wv.setsampwidth(2)
        wv.setframerate(sr)
        wv.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    save_json(raw_words, words)
    save_json(out_dir(slug) / 'voice_meta.json', {'sig': sig, 'chars': len(spoken), **info})
    rows = load_json(out_dir(slug) / 'costs.json', []) or []
    rows.append(cost)
    save_json(out_dir(slug) / 'costs.json', rows)
    print(f'take: {len(x) / sr:.2f} s in {time.time() - t0:.1f} s ({cost["note"]})')
else:
    print('Voice unchanged since the last call: reusing it.')

# ---------------------------------------------------------------- tighten the pauses (as voice.py)
words = load_json(raw_words)
G = {'word': 0.12, 'comma': 0.2, 'sentence': 0.3, 'question': 0.45, 'pairs': {}}
G.update(ep.get('gaps', {}))
x = decode(raw_wav)
cuts = []


def bare(w):
    return re.sub(r'[^\w]', '', w)


for a, b in zip(words, words[1:]):
    gap = b['s'] - a['e']
    key = bare(a['w']) + '|' + bare(b['w'])
    if key in G['pairs']:
        keep = G['pairs'][key]
    elif '?' in a['p'] or '!' in a['p']:
        keep = G['question']
    elif '.' in a['p'] or ':' in a['p'] or ';' in a['p'] or '…' in a['p']:
        keep = G['sentence']
    elif ',' in a['p'] or '—' in a['p'] or '-' in a['p']:
        keep = G['comma']
    else:
        keep = G['word']
    if gap > keep:
        mid = (a['e'] + b['s']) / 2
        rm = gap - keep
        cuts.append((mid - rm / 2, mid + rm / 2))
parts, last = [], 0.0
for s, e in cuts:
    parts.append(x[int(last * SR):int(s * SR)])
    last = e
parts.append(x[int(last * SR):])
fade = int(0.004 * SR)
for i, part in enumerate(parts):
    part = part.copy()
    if i > 0 and len(part) > fade:
        part[:fade] *= np.linspace(0, 1, fade)
    if i < len(parts) - 1 and len(part) > fade:
        part[-fade:] *= np.linspace(1, 0, fade)
    parts[i] = part
y = np.concatenate(parts)
write_wav(pub_dir(slug) / 'voice.wav', y)


def shift(t):
    return t - sum(min(e, t) - s for s, e in cuts if t > s)


out = [{'w': w['w'], 's': round(shift(w['s']), 3), 'e': round(shift(w['e']), 3), 'p': w.get('p', '')} for w in words]
save_json(ep_dir(slug) / 'words.json', out)
print(f'Tightened {len(cuts)} pauses, removed {sum(e - s for s, e in cuts):.2f} s: {len(x) / SR:.2f} s -> {len(y) / SR:.2f} s')
print(' '.join(f"{w['w']}@{w['s']}" for w in out))
