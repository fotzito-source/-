"""Step 2, for a French episode: the voice, with word timings, then the pauses tightened exactly as voice.py does.

Two engines, so the pipeline runs with or without a TTS account (voice.py stays the ElevenLabs path):
  cartesia  the Cartesia API (key in CARTESIA_API_KEY, never in a file; api.cartesia.ai must be reachable).
            A few sentences per request (one long take drifts: whispered words, words that drop in level), several
            takes of each, the best one kept: every word voiced and at level, and, when the speech recogniser is
            installed, every word of the text heard. Words levelled, a gentle compressor. Word timestamps from the API.
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
  "cartesia": {"model": "sonic-3", "id": null, "language": "fr", "speed": null, "emotion": null, "volume": null,
                "takes": 3, "chunk": 180, "chunking": "beat"}}
  emotion: a Cartesia emotion ("excited", "happy", "content"...); takes: tries per chunk; chunk: characters per request;
  chunking: "beat" (chunks never cross a beat, a beat may set its own "emotion") or "text" (the whole script, run on)
  --offline builds the take from .cache/voice/<slug>/ only: every take is kept there, named by its text and sound settings
  The takes the voice is built from are also copied (FLAC, lossless) to src/episodes/<slug>/takes/, which is versioned:
  on a fresh clone, --offline rebuilds the same voice from them without the cache and without credits.
Speech check (optional, for the cartesia takes): a NeMo Parakeet model through sherpa-onnx in .cache/asr/ of the studio:
  pip install sherpa-onnx; then from the studio folder
  curl -L https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8.tar.bz2 | tar xj -C .cache/asr
Setup for local: pip install piper-tts onnx  (the voice model downloads once into .cache/tts/ in the studio)
"""
import argparse, base64, hashlib, json, os, pathlib, re, sys, tarfile, time, urllib.error, urllib.parse, urllib.request

import numpy as np

from wi import SR, STUDIO, decode, ep_dir, load_episode, load_json, out_dir, pub_dir, save_json, write_wav

ap = argparse.ArgumentParser()
ap.add_argument('slug')
ap.add_argument('--backend', choices=['auto', 'cartesia', 'local'])
ap.add_argument('--force', action='store_true')
ap.add_argument('--list', action='store_true')
ap.add_argument('--from-audio', help='a take recorded elsewhere (the Cartesia site, a microphone): word timings by aligning it on the local voice')
ap.add_argument('--offline', action='store_true', help='cartesia: use only the takes already in .cache/voice (no API call, no credits)')
args = ap.parse_args()
slug = args.slug
ep = load_episode(slug)
V = {'backend': 'auto', 'local': {}, 'cartesia': {}}
V.update(ep.get('voice', {}))
LOCAL = {'model': 'fr_FR-tom-medium', 'length_scale': 0.92, 'noise_scale': 0.62, 'noise_w_scale': 0.8, **V.get('local', {})}
CART = {'model': 'sonic-3', 'id': None, 'language': 'fr', 'speed': None, 'emotion': None, 'volume': None, 'takes': 3, 'chunk': 180, 'chunking': 'beat', **V.get('cartesia', {})}
backend = args.backend or V.get('backend', 'auto')
if backend == 'auto':
    backend = 'cartesia' if args.offline or os.environ.get('CARTESIA_API_KEY', '').strip() else 'local'

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
        hint = '\n  The takes already made are in .cache/voice/: --offline builds the voice from them.' if e.code == 402 else ''
        raise SystemExit(f'Cartesia HTTP {e.code} on {path}: {e.read().decode("utf-8", "replace")[:400]}{hint}')
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


def cart_take(text, voice_id, emotion=None):
    body = {'model_id': CART['model'], 'transcript': text, 'voice': {'mode': 'id', 'id': voice_id}, 'language': CART['language'],
            'output_format': {'container': 'raw', 'encoding': 'pcm_s16le', 'sample_rate': SR}, 'add_timestamps': True}
    gen = {k: CART[k] for k in ('speed', 'volume', 'emotion') if CART.get(k)}
    if emotion:
        gen['emotion'] = emotion
    if gen:
        body['generation_config'] = gen
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


def chunks(text, limit):
    """Whole sentences, a few per request, at most `limit` characters (a longer sentence goes alone)."""
    sents = [m.strip() for m in re.findall(r'.+?(?:[.!?…]+["»)]*(?=\s|$)|$)', text.strip()) if m.strip()]
    out = []
    for snt in sents:
        if out and len(out[-1]) + 1 + len(snt) <= limit:
            out[-1] += ' ' + snt
        else:
            out.append(snt)
    return out


_asr = None


def asr_text(x, sr):
    """What a speech recogniser hears in the take, or None when none is installed (see the docstring)."""
    global _asr
    if _asr is False:
        return None
    if _asr is None:
        import glob
        found = glob.glob(str(STUDIO / '.cache' / 'asr' / 'sherpa-onnx-nemo-parakeet*'))
        try:
            import sherpa_onnx
        except ImportError:
            found = []
        if not found:
            print('  (no speech recogniser in .cache/asr: takes checked on level and voicing only)')
            _asr = False
            return None
        d = found[0]
        _asr = sherpa_onnx.OfflineRecognizer.from_transducer(encoder=f'{d}/encoder.int8.onnx', decoder=f'{d}/decoder.int8.onnx',
                                                             joiner=f'{d}/joiner.int8.onnx', tokens=f'{d}/tokens.txt',
                                                             model_type='nemo_transducer', num_threads=4)
    import librosa
    st = _asr.create_stream()
    st.accept_waveform(16000, librosa.resample(np.asarray(x, dtype=np.float32), orig_sr=sr, target_sr=16000))
    _asr.decode_stream(st)
    return st.result.text


SAME = {'mum': 'mom', 'mom': 'mom', 'anytime': 'any time', 'okay': 'ok', 'ok': 'ok'}
NUMS = {'1': 'one', '2': 'two', '3': 'three', '8': 'eight', '9': 'nine', '10': 'ten', '100': 'hundred', '1000': 'thousand'}


def heard_errors(text, heard):
    import difflib
    norm = lambda t: ' '.join(SAME.get(w, NUMS.get(w, w)) for w in re.findall(r"[a-z0-9']+", t.lower().replace('’', "'"))).split()
    a, b = norm(text), norm(heard)
    ops = difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes()
    return [(' '.join(a[i1:i2]), ' '.join(b[j1:j2])) for op, i1, i2, j1, j2 in ops if op != 'equal']


def take_report(x, sr, words, text):
    """A take's faults: words that drop in level, long words with no voice in them (whispered, creaky), words the
    recogniser doesn't hear. The score is what we minimise across takes."""
    hop = sr // 100
    db = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, mode='same'))[::hop] + 1e-9)
    per = periodicity(x, sr)
    vflag = per > 0.55
    lv, quiet, unvoiced = [], [], []
    for w in words:
        sl = slice(int(w['s'] * 100), max(int(w['s'] * 100) + 1, int(w['e'] * 100)))
        lv.append(float(np.percentile(db[sl], 90)) if len(db[sl]) else -99.0)
    med = float(np.median(lv)) if lv else 0.0
    for w, l in zip(words, lv):
        sl = slice(int(w['s'] * 100), max(int(w['s'] * 100) + 1, min(len(vflag), int(w['e'] * 100))))
        if l < med - 9:
            quiet.append(w['w'])
        if w['e'] - w['s'] > 0.14 and len(vflag[sl]) and float(np.mean(vflag[sl])) < 0.3:
            unvoiced.append(w['w'])
    heard = asr_text(x, sr)
    errs = heard_errors(text, heard) if heard is not None else []
    count_off = abs(len(words) - len(tokens(text)))
    speech = db[:len(per)] > np.median(lv) - 25 if lv else per > 0
    clarity = float(np.mean(per[speech])) if speech.any() else 0.0  # how clean the voice is (breathy and creaky are lower)
    score = len(quiet) + 3 * len(unvoiced) + 8 * sum(max(len(a.split()), len(b.split())) for a, b in errs) + 20 * count_off
    return {'score': score, 'clarity': round(clarity, 3), 'quiet': quiet, 'unvoiced': unvoiced, 'heard_wrong': errs, 'word_count_off': count_off}


def periodicity(x, sr):
    """Per 10 ms frame, the best normalised autocorrelation for a pitch between 60 and 400 Hz: about 0.7 to 0.95 in a
    voiced vowel, under 0.4 in a whisper."""
    import librosa
    y = librosa.resample(np.asarray(x, dtype=np.float64), orig_sr=sr, target_sr=16000)
    win, hop, lo, hi = 480, 160, 16000 // 400, 16000 // 60
    n = max(0, (len(y) - win - hi) // hop)
    per = np.zeros(n)
    for i in range(n):
        f = y[i * hop: i * hop + win + hi]
        a = f[:win]
        e = float(np.dot(a, a))
        if e < 1e-8:
            continue
        segs = np.lib.stride_tricks.sliding_window_view(f, win)[lo:hi + 1]
        per[i] = float(np.max((segs @ a) / (np.sqrt(e * np.einsum('ij,ij->i', segs, segs)) + 1e-12)))
    return per


def trim(x, sr, words, pad=0.04):
    """Cut the silence before the first word and after the last, keeping `pad` seconds; shift the words."""
    env = np.convolve(np.abs(x), np.ones(sr // 100) / (sr // 100), mode='same')
    on = np.nonzero(env > env.max() * 0.01)[0]
    a = max(0, on[0] - int(pad * sr)) if len(on) else 0
    b = min(len(x), on[-1] + int(pad * sr)) if len(on) else len(x)
    if words:
        a = min(a, max(0, int((words[0]['s'] - pad) * sr)))
        b = max(b, min(len(x), int((words[-1]['e'] + pad) * sr)))
    return x[a:b], [{**w, 's': w['s'] - a / sr, 'e': w['e'] - a / sr} for w in words]


def level_words(x, sr, words, up=8.0, down=3.0):
    """Even out the words: each word's loud part is brought toward the median, at most +up / -down dB, through a
    gain curve that moves between words, never inside one."""
    hop = sr // 100
    db = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, mode='same'))[::hop] + 1e-9)
    lv = []
    for w in words:
        sl = slice(int(w['s'] * 100), max(int(w['s'] * 100) + 1, int(w['e'] * 100)))
        lv.append(float(np.percentile(db[sl], 90)) if len(db[sl]) else None)
    ok = [l for l in lv if l is not None]
    if not ok:
        return x
    med = float(np.median(ok))
    pts_t, pts_g = [0.0], [0.0]
    for w, l in zip(words, lv):
        g = 0.0 if l is None else float(np.clip(med - l, -down, up))
        pts_t += [w['s'], w['e']]
        pts_g += [g, g]
    pts_t.append(len(x) / sr)
    pts_g.append(pts_g[-1])
    order = np.argsort(pts_t, kind='stable')
    t = np.arange(len(x)) / sr
    gdb = np.interp(t, np.array(pts_t)[order], np.array(pts_g)[order])
    return x * 10 ** (gdb / 20)


def compress(x, sr):
    """A gentle voice compressor (ffmpeg acompressor): 2.5:1 above about -24 dBFS of speech, 8 ms attack."""
    import subprocess, tempfile
    x = x / max(1e-9, np.sqrt(np.mean(x[np.abs(x) > 0.01] ** 2))) * 10 ** (-20 / 20)
    with tempfile.TemporaryDirectory() as d:
        write_wav(pathlib.Path(d) / 'in.wav', np.clip(x, -1, 1))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{d}/in.wav', '-af',
                        'acompressor=threshold=0.063:ratio=2.5:attack=8:release=120:knee=4:makeup=1.6', '-c:a', 'pcm_f32le', f'{d}/out.wav'], check=True)
        return decode(f'{d}/out.wav')


def take_files(cache, chunk, voice_id, emo, k):
    """A take's files, named by what shapes its sound only (text, voice, model, language, speed, volume, emotion) and
    its number: changing the number of takes or the chunk size keeps every take already paid for."""
    sound = [chunk, voice_id, CART['model'], CART['language'], CART.get('speed'), CART.get('volume'), emo or CART.get('emotion'), k]
    key = hashlib.sha1(json.dumps(sound).encode()).hexdigest()[:16]
    return cache / f'{key}.wav', cache / f'{key}.json'


KEPT = ep_dir(slug) / 'takes'


def kept_files(chunk, voice_id, emo, k):
    """The versioned copy of a take the voice is built from (src/episodes/<slug>/takes/, FLAC): .cache is not."""
    wav, js = take_files(KEPT, chunk, voice_id, emo, k)
    return wav.with_suffix('.flac'), js


def keep_takes(todo, report, voice_id):
    """Copy the chosen takes next to episode.json and drop the copies no chunk uses any more."""
    import subprocess
    cache = STUDIO / '.cache' / 'voice' / slug
    KEPT.mkdir(exist_ok=True)
    used = set()
    for (chunk, emo), r in zip(todo, report):
        k = r['take'] - 1
        wav, js = take_files(cache, chunk, voice_id, emo, k)
        kf, kj = kept_files(chunk, voice_id, emo, k)
        used |= {kf.name, kj.name}
        if not (kf.exists() and kj.exists()):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(wav), '-c:a', 'flac', '-compression_level', '8', str(kf)], check=True)
            save_json(kj, load_json(js))
    for f in KEPT.iterdir():
        if f.name not in used:
            f.unlink()


def cart_story(voice_id):
    """The whole script, beat by beat and a few sentences at a time, best of CART['takes'] takes each (a beat may
    set its own "emotion"); cached per chunk and take."""
    cache = STUDIO / '.cache' / 'voice' / slug
    cache.mkdir(parents=True, exist_ok=True)
    parts, words, at, report = [], [], 0.0, []
    if CART['chunking'] == 'text':
        todo = [(c, None) for c in chunks(spoken, int(CART['chunk']))]
    else:
        todo = [(c, b.get('emotion')) for b in ep['script'] for c in chunks(b.get('tts', b['text']), int(CART['chunk']))]
    for ci, (chunk, emo) in enumerate(todo):
        best, new_takes = None, 0
        for k in range(int(CART['takes'])):
            wav, js = take_files(cache, chunk, voice_id, emo, k)
            kf, kj = kept_files(chunk, voice_id, emo, k)
            if js.exists() and wav.exists() and not args.force:
                x, w = decode(wav), load_json(js)
            elif kf.exists() and kj.exists() and not args.force:
                x, w = decode(kf), load_json(kj)
            elif args.offline:
                continue
            else:
                x, sr, w = cart_take(chunk, voice_id, emo)
                new_takes += 1
                write_wav(wav, np.clip(x, -1, 1))
                save_json(js, w)
            x, w = trim(x, SR, w)
            rep = take_report(x, SR, w, chunk)
            if best is None or (rep['score'], -rep['clarity']) < (best[2]['score'], -best[2]['clarity']):
                best = (x, w, rep, k)
            if rep['score'] == 0 and rep['clarity'] >= 0.6:
                break
        if best is None:
            raise SystemExit(f'--offline: no take of chunk {ci + 1} in {cache} ("{chunk[:60]}…")')
        x, w, rep, k = best
        print(f"  chunk {ci + 1}: take {k + 1}, score {rep['score']}, clarity {rep['clarity']}" + (f"  quiet {rep['quiet']}" if rep['quiet'] else '') +
              (f"  unvoiced {rep['unvoiced']}" if rep['unvoiced'] else '') + (f"  heard {rep['heard_wrong']}" if rep['heard_wrong'] else ''))
        report.append({'chunk': chunk, 'take': k + 1, 'new_takes': new_takes, **rep})
        parts += [x, np.zeros(int(0.6 * SR))]
        words += [{**q, 's': q['s'] + at, 'e': q['e'] + at} for q in w]
        at += len(x) / SR + 0.6
    save_json(out_dir(slug) / 'voice_takes.json', report)
    keep_takes(todo, report, voice_id)
    x = np.concatenate(parts[:-1])
    x = level_words(x, SR, words)
    x = compress(x, SR)
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
sig = hashlib.sha1(json.dumps([spoken, backend, settings, src_sig, [b.get('emotion') for b in ep['script']]], sort_keys=True).encode()).hexdigest()[:12]
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
        if args.offline:
            print(f'Cartesia takes from .cache/voice/{slug}/ only (--offline: no API call)')
        else:
            print(f'{len(spoken)} characters to Cartesia ({CART["model"]}), up to {CART["takes"]} takes per chunk (takes already made are reused)')
        x, sr, timed = cart_story(vid)
        info = {'backend': 'cartesia', 'voice_id': vid, 'voice_name': CART.get('name', name), 'model': CART['model']}
        made = sum(r.get('new_takes', 0) for r in load_json(out_dir(slug) / 'voice_takes.json', []) or [])
        cost = {'step': 'voice (Cartesia)', 'credits': 0, 'note': f'{made} new takes billed by Cartesia (characters), not ElevenLabs'}
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
    if args.offline:
        rows.pop()
        save_json(out_dir(slug) / 'costs.json', rows)
else:
    print('Voice unchanged since the last call: reusing it.')

# ---------------------------------------------------------------- tighten the pauses (as voice.py)
words = load_json(raw_words)
G = {'word': 0.12, 'comma': 0.2, 'sentence': 0.3, 'question': 0.45, 'pairs': {}}
G.update(ep.get('gaps', {}))
x = decode(raw_wav)
cuts = []
_hop = SR // 100
env_db = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(_hop) / _hop, mode='same'))[::_hop] + 1e-9)
speech_db = float(np.median([np.percentile(env_db[int(w['s'] * 100):max(int(w['s'] * 100) + 1, int(w['e'] * 100))], 90) for w in words]))


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
        # cut only inside the silence: the frames of the gap that are quiet, 30 ms clear of any sound
        f0, f1 = int(a['e'] * 100), int(b['s'] * 100)
        quiet = env_db[f0:f1] < speech_db - 32
        best_run, run = (0, 0), None
        for i, q in enumerate(list(quiet) + [False]):
            if q and run is None:
                run = i
            elif not q and run is not None:
                if i - run > best_run[1] - best_run[0]:
                    best_run = (run, i)
                run = None
        s0, s1 = (f0 + best_run[0]) / 100 + 0.03, (f0 + best_run[1]) / 100 - 0.03
        rm = min(gap - keep, s1 - s0)
        if rm > 0.01:
            mid = (s0 + s1) / 2
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
