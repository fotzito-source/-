# Vidéo 03 : « What if you could grow at will? » (version anglaise, YouTube 16/9, plus d'une minute)

La version anglaise et longue de l'épisode 02, faite avec le même skill
([what-if-animation](https://github.com/kelano86/what-if-animation), copie dans `.claude/skills/what-if-animation/`).

- **Format :** 2560 × 1440 (1440p), 30 i/s, 16/9.
  - Rendu à 2880 × 1620, puis réduit en Lanczos : contours plus nets.
  - Fichier livré : H.264 High en 2 passes à 11,3 Mbit/s (91 Mo), dans ce que YouTube recommande pour le 1440p. Le
    master en CRF 14 (336 Mo) dépasse la limite de 100 Mo de GitHub et reste dans `what-if-studio/out/grow/`.
  - YouTube réencode le 1440p en VP9, ce qui donne une bien meilleure image à la diffusion qu'un envoi en 1080p.
- **Durée :** 64,5 s, avec un carton de fin « PART 1 / WHAT WOULD YOU DO? ».
- **Structure :** 32 plans sur les 7 temps de la formule What If, dont 8 nouveaux plans par rapport à la version
  française :
  - Pip grandit dans le bureau ;
  - le colosse au-dessus de la ville ;
  - les pigeons sur sa capuche ;
  - Mo assis dans sa paume ;
  - deux schémas de plus (la charge ×10 par pouce carré, puis le fémur qui casse vers ×10 le poids du corps) ;
  - la nuit où Pip rétrécit sur le toit ;
  - le carton de fin.
- **Son :** −14,0 LUFS intégrés, crête vraie −1,46 dBTP.

| Fichier | Contenu |
|---|---|
| `grow-final.mp4` | La vidéo finale, 1440p |
| `cartesia-script.txt` | Le texte anglais, à coller tel quel dans Cartesia (une seule prise) |
| `storyboard.jpg` | Les 32 plans, une image clé chacun |
| `thumbnail.jpg` | Miniature YouTube 1280 × 720 |
| `grow.srt` | Sous-titres anglais pour l'import YouTube |
| `report.json` | Durée, loudness, crête, rythme |
| `../../what-if-studio/src/episodes/grow/` | Les sources : `episode.json` (script, science, montage, son), `shots.tsx` (plans anglais et nouveaux plans, les autres repris de `grandir`), `index.tsx` (le look GROW) |

> **La voix est provisoire.** C'est une voix de synthèse locale (Piper `en_US-ryan-high`, licence CC BY-NC-SA, donc
> pas pour une vidéo monétisée), en attendant la prise Cartesia. Elle sert à caler le montage.

## Mettre la voix Cartesia

Génère `cartesia-script.txt` en une seule prise sur le site de Cartesia et exporte-la en WAV. Ensuite, depuis
`what-if-studio/` (`S` désigne le dossier des scripts du skill) :

```bash
S=../.claude/skills/what-if-animation/scripts
python3 $S/voice_fr.py grow --from-audio /chemin/vers/cartesia.wav   # horaires des mots par alignement DTW
python3 $S/plan.py grow && python3 $S/sfx.py grow && python3 $S/mixcheck.py grow
npx remotion render src/index.ts Grow out/grow/grow-hi.mp4 --concurrency=4 --scale=1.5 --crf=12 --x264-preset=slow
ffmpeg -y -i out/grow/grow-hi.mp4 -vf scale=2560:1440:flags=lanczos -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -c:a copy out/grow/grow-raw.mp4
python3 $S/master.py grow --skip-render && python3 $S/srt.py grow
```

Pour retrouver chaque mot dans la prise, `--from-audio` l'aligne sur la lecture locale du même texte (DTW sur MFCC,
avec librosa). Sur un essai dont les vrais horaires étaient connus, l'erreur médiane est de 11 ms et l'erreur
maximale de 58 ms.

Tout le montage est ancré sur ces mots :

- les coupes ;
- les actions de chaque plan, calées sur la fin de leur segment ;
- les bruitages, repérés depuis le plan suivant (`S4-6`).

Le montage suit donc la nouvelle voix sans retouche.

## La science (vérifiée)

- **×10 de hauteur, ×1 000 de poids :** le volume est multiplié par 10 × 10 × 10.
- **Os ×100 plus solides seulement :** la solidité d'un os suit l'aire de sa section, multipliée par 10 × 10.
- **Charge ×10 par pouce carré :** 1 000 / 100 = 10.
- **Un fémur humain casse vers dix fois le poids du corps,** d'où « Snap » au premier pas.

Source : J. B. S. Haldane, *On Being the Right Size*, 1926 (les géants Pope et Pagan). La loi carré-cube vient de
Galilée, *Two New Sciences*, 1638. Les détails et les liens sont dans `../02-what-if-grandir/script.md`.

## Son

Mêmes provenances que la vidéo 02 :

- **Bibliothèque du skill :** sons ElevenLabs générés par son auteur et livrés sous licence MIT. La musique est
  bouclée par `sfx_local.py` (recette `music_loop`) pour couvrir l'ouverture plus longue.
- **Sons synthétisés** par `sfx_local.py`.

Vérifie les droits de la bibliothèque avant de monétiser. La musique s'enlève en supprimant `"music"` dans
`episode.json`.
