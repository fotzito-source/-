# Provenance de ce skill

Copie du skill **what-if-animation** de FreshStack (licence MIT, voir `LICENSE`) :
<https://github.com/kelano86/what-if-animation>, commit `8092fb5`.

Ce qui diffère de l'original :

- **Pas de dossier `studio/` ici.** Le studio est déjà copié et installé à la racine du dépôt, dans `what-if-studio/`.
  `SKILL.md` dit `<skill>/studio` : dans ce dépôt, c'est `what-if-studio/`.
- **`scripts/voice_fr.py` (ajouté)** : l'étape 2 pour un épisode en français, sans ElevenLabs. Deux moteurs :
  - Cartesia, si la variable d'environnement `CARTESIA_API_KEY` est définie et que `api.cartesia.ai` est joignable ;
  - Piper en local (`pip install piper-tts onnx`), voix provisoire.

  Dans les deux cas, il écrit les mêmes fichiers que `voice.py` (`voice.wav`, `words.json`) avec le même resserrage
  des pauses. Ce resserrage ne coupe que dans le silence mesuré, à 30 ms de tout son.

  Avec Cartesia, la voix ne se fait pas en une seule prise : sur un texte long, le modèle dérive (mots chuchotés, mots
  qui tombent de 20 à 40 dB). Elle se fait par petits groupes de phrases :
  - jamais à cheval sur deux temps du script, et un temps peut avoir sa propre `emotion` ;
  - plusieurs prises de chaque groupe (`takes`), dont on garde la meilleure. Une prise perd des points pour chaque mot
    trop faible, chaque mot sans voix (mesure de périodicité) et chaque mot que la reconnaissance vocale n'entend pas ;
  - la reconnaissance vocale est NeMo Parakeet, avec sherpa-onnx, si son modèle est dans `.cache/asr/` (lien dans le
    docstring) ;
  - ensuite, les mots sont égalisés un à un, puis passés dans un compresseur doux.

  Chaque prise reste dans `.cache/voice/<slug>/`, qui n'est pas versionné. Son nom ne dépend que du texte et des
  réglages qui changent le son. Les prises retenues sont aussi copiées en FLAC (sans perte) dans
  `src/episodes/<slug>/takes/`, qui est versionné. `--offline` refait la voix à partir de ces prises seulement, sans
  appel ni crédit : sur un clone neuf et sans clé, il redonne la même voix au bit près. Le script sert aussi pour
  l'anglais : la langue se règle dans `episode.json`. `--from-audio prise.wav`
  reprend une prise faite ailleurs (le site de Cartesia, par exemple) : les horaires des mots viennent d'un alignement
  DTW sur la voix locale. Les mots qu'espeak fusionne (« of the ») sont redécoupés.
- **`scripts/sfx_local.py` (ajouté)** : synthétise en numpy les bruitages marqués `procedural:` dans `episode.json`. Il
  les range dans `library/sfx/` sous le nom que `sfx.py` attend : `sfx.py` les trouve et n'appelle pas l'API.
- **Recette `music_loop`** dans `sfx_local.py` : la musique de la bibliothèque, bouclée en fondu enchaîné pour les
  ouvertures plus longues que ses 17 s.
- **`scripts/srt.py` (ajouté)** : sous-titres SRT pour l'import sur YouTube (jamais incrustés, comme le veut le style).
- **Moteur** (`what-if-studio/src/engine/sets/rooftop.tsx`) : `Rooftop` accepte `between`, un calque placé entre la
  ville et notre toit. C'est là que se tient un géant debout dans la rue derrière l'immeuble. `strings={false}`
  retire les guirlandes.
- **Recette `heartbeat`** dans `sfx_local.py` (partie 2 de `grow`).
- **`scripts/duck.py` (ajouté), à lancer après `sfx.py`** : pendant que quelqu'un parle, les bruitages restent au moins
  5 dB sous la voix et la musique 8 dB sous la voix (options `--sfx`, `--music`, `--max`). La baisse est rapide et la
  remontée lente. Dans les pauses, chaque impact garde toute sa force. `mixcheck.py` le vérifie ensuite.
- **Version verticale 9:16** (`what-if-studio/src/engine/episode.tsx`) : un épisode qui passe `vertical` à
  `defineEpisode` gagne deux compositions de 1080 × 1920, `<Id>Vertical` et `<Id>VerticalBoard` (déclarées dans
  `src/Root.tsx`). `vertical` donne, plan par plan, la fenêtre 9:16 sur l'image 16:9 :
  - `{ cx, w }` : centre et largeur de la fenêtre, en unités 1920 × 1080 (608 = toute la hauteur, sans bandes) ;
  - `cx2` et `span` : un panoramique vers `cx2` entre deux fractions du plan ;
  - `{ fit: true, cx, w }` : une bande nette de toute la hauteur, posée sur une copie floue du même plan (titres,
    schémas, plans larges à plusieurs personnages).

  Les surcouches des looks (le compteur GROW) sont redessinées sur toute la largeur verticale.

Le reste (`SKILL.md`, `references/`, les autres scripts) est inchangé.
