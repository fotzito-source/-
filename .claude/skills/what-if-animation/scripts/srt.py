"""Subtitles for the platform's caption upload (YouTube, TikTok...), never burnt in: the genre keeps the voice off
the picture. One cue per sentence on one or two lines (broken at the comma nearest the middle), timed on the voice's words.

python <skill>/scripts/srt.py <slug> [--max 42]
Reads  src/episodes/<slug>/words.json (after voice.py or voice_fr.py) and episode.json (the script's own spelling)
Writes out/<slug>/<slug>.srt
"""
import re, sys

from wi import ep_dir, load_episode, load_json, out_dir

slug = sys.argv[1]
MAX = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 42
words = load_json(ep_dir(slug) / 'words.json')
if not words:
    raise SystemExit('No words.json: run the voice step first.')
ep = load_episode(slug)
# the script's own spelling and punctuation, word by word (words.json carries the same words in the same order)
shown = re.findall(r"[\w'’]+[^\w'’\s]*(?:\s+[^\w'’\s]+)?", ' '.join(b['text'] for b in ep['script']))
if len(shown) != len(words):
    shown = [w['w'] + w.get('p', '') for w in words]

# words that shouldn't end a line: they belong with the word after them
GLUE = set('le la les un une des du de ta ton tes ma mon mes sa son ses en à au aux et ou que qui ne petite petit the a an of to your my'.split())


def lines(ix):
    """One or two lines of at most MAX characters: break at the punctuation nearest the middle, else the space."""
    text = ' '.join(shown[k] for k in ix)
    if len(text) <= MAX or len(ix) < 2:
        return text
    best, score = 1, 1e9
    for k in range(1, len(ix)):
        a, b = ' '.join(shown[j] for j in ix[:k]), ' '.join(shown[j] for j in ix[k:])
        last = re.sub(r'[^\w\'’]', '', shown[ix[k - 1]]).lower()
        sc = abs(len(a) - len(b)) - (12 if re.search(r'[,:;]$', shown[ix[k - 1]]) else 0) + (100 if max(len(a), len(b)) > MAX else 0) + (10 if last in GLUE else 0)
        if sc < score:
            best, score = k, sc
    return ' '.join(shown[j] for j in ix[:best]) + '\n' + ' '.join(shown[j] for j in ix[best:])


# one cue per sentence (two lines at most); a sentence too long for two lines splits at its commas
cues, cur = [], []
for i, w in enumerate(words):
    cur.append(i)
    end_of_sentence = re.search(r'[.?!…]\s*$', shown[i])
    full = len(' '.join(shown[k] for k in cur)) > 2 * MAX - 6 and re.search(r'[,:;]$', shown[i])
    if end_of_sentence or full or i == len(words) - 1:
        cues.append(cur)
        cur = []


def stamp(s):
    ms = int(round(s * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


out = []
for n, c in enumerate(cues):
    a = words[c[0]]['s']
    b = words[c[-1]]['e'] + 0.3
    if n + 1 < len(cues):
        b = min(b, words[cues[n + 1][0]]['s'] - 0.04)
    out.append(f"{n + 1}\n{stamp(a)} --> {stamp(b)}\n{lines(c)}\n")
p = out_dir(slug) / f'{slug}.srt'
p.write_text('\n'.join(out), encoding='utf-8')
print(p, f'{len(cues)} cues')
