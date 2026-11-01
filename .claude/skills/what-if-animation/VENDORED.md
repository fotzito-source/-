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
  des pauses.
- **`scripts/sfx_local.py` (ajouté)** : synthétise en numpy les bruitages marqués `procedural:` dans `episode.json`. Il
  les range dans `library/sfx/` sous le nom que `sfx.py` attend : `sfx.py` les trouve et n'appelle pas l'API.
- **`scripts/srt.py` (ajouté)** : sous-titres SRT pour l'import sur YouTube (jamais incrustés, comme le veut le style).
- **Moteur** (`what-if-studio/src/engine/sets/rooftop.tsx`) : `Rooftop` accepte `between`, un calque placé entre la
  ville et notre toit. C'est là que se tient un géant debout dans la rue derrière l'immeuble.

Le reste (`SKILL.md`, `references/`, les autres scripts) est inchangé.
