# Vidéo 03 : « What if you could grow at will? » (anglais, parties 1 et 2)

L'histoire en anglais, en deux parties montées à la suite, faite avec le skill
[what-if-animation](https://github.com/kelano86/what-if-animation) (copie dans `.claude/skills/what-if-animation/`).
Elle existe en deux formats : 16/9 pour YouTube et 9:16 pour TikTok.

| Fichier | Contenu |
|---|---|
| `grow-full-youtube.mp4` | **YouTube** : les parties 1 et 2 à la suite, 2 min 05 (124,8 s), 2560 × 1440 (1440p) |
| `grow-full-tiktok.mp4` | **TikTok** : la même vidéo recadrée en 9:16, 1080 × 1920 |
| `grow-full.srt` | Sous-titres anglais de la vidéo complète, à importer sur YouTube |
| `thumbnail.jpg` | Miniature YouTube 1280 × 720 |
| `tiktok-cover.jpg` | Couverture TikTok 1080 × 1920 |
| `storyboard.jpg`, `storyboard-part2.jpg` | Les plans des parties 1 (32 plans) et 2 (30 plans), une image clé chacun |
| `cartesia-script.txt`, `cartesia-script-part2.txt` | Le texte dit par la voix, partie par partie |
| `report.json` | Mesures de la version YouTube : durée, loudness, crête |
| `../../what-if-studio/src/episodes/grow/`, `grow2/` | Les sources : `episode.json` (script, science, montage, son), `shots.tsx` (les plans), `index.tsx` (le look GROW), `vertical.ts` (le cadrage 9:16) |

## L'histoire

- **Partie 1 (63 s)** : Pip découvre qu'il grandit quand il dit « grow ». D'abord le bocal de cookies, puis il devient
  un colosse au-dessus de la ville, jusqu'au premier pas où son fémur casse. Le lendemain, un homme en costume
  l'attend dans la cuisine avec une photo de lui. Puis le plafond se fissure : à l'étage, sa petite sœur vient de dire
  le mot. Carton : « PART 1 / WHAT WOULD YOU DO? ».
- **Partie 2 (62 s), « The word »** : la suite immédiate.
  1. Pip monte l'escalier avec sa béquille. La chambre de sa sœur n'est plus une chambre : elle est grande comme la
     maison, et elle adore ça.
  2. Puis elle vacille : à dix fois sa taille, son cœur ne peut plus monter le sang jusqu'au cerveau.
  3. Dix secondes avant qu'elle ne s'évanouisse, Pip redit le mot malgré son plâtre et la rattrape.
  4. En face, l'homme en costume filme tout.
  5. Le lendemain, une carte sur l'oreiller, avec un seul mot, et ce n'est pas « grow ». Carton : « PART 2 /
     WHAT DO YOU THINK IT SAYS? ».

## La science (vérifiée)

**Partie 1 :**

- **×10 de hauteur, ×1 000 de poids :** le volume est multiplié par 10 × 10 × 10.
- **Os ×100 plus solides seulement :** la solidité d'un os suit l'aire de sa section, multipliée par 10 × 10.
- **Charge ×10 par pouce carré :** 1 000 / 100 = 10.
- **Un fémur humain casse vers dix fois le poids du corps,** d'où « Snap » au premier pas.
- **Sources :** J. B. S. Haldane, *On Being the Right Size*, 1926. La loi carré-cube vient de Galilée, *Two New
  Sciences*, 1638.

**Partie 2 :**

- **Il faudrait environ trois fois la pression que son cœur produit :**
  - le cerveau d'une enfant est à environ 0,3 m au-dessus du cœur, soit 3 m à ×10 ;
  - pour monter le sang de 3 m : ρgh = 1 060 kg/m³ × 9,81 m/s² × 3 m ≈ 31 kPa ≈ 235 mmHg ;
  - la pression artérielle moyenne d'un enfant est d'environ 75 à 85 mmHg, donc environ un tiers de ce qu'il
    faudrait.
- **Sans sang, le cerveau décroche en une dizaine de secondes :** Rossen, Kabat et Anderson, *Acute arrest of
  cerebral circulation in man*, Archives of Neurology and Psychiatry, 1943. Ils mesurent une perte de conscience en
  environ 5 à 10 s, 6,8 s en moyenne.

## La voix

- **Voix :** Cartesia `sonic-3`, « Carson – Curious Conversationalist », vitesse 0,9.
- **Génération :** par l'API, avec la clé lue dans la variable d'environnement `CARTESIA_API_KEY` (jamais écrite dans
  le dépôt).
- **Montage :** l'API donne l'horaire de chaque mot, et tout le montage s'y accroche : les coupes, les actions des
  plans et les bruitages.

## La version TikTok (9:16)

La version TikTok n'est pas un simple recadrage au centre. Chaque plan a son propre cadre, choisi sur une planche de
contrôle et noté dans `vertical.ts`. Il y a trois cas :

- **Cadre serré sur le personnage :** l'image remplit tout l'écran vertical.
- **Panoramique :** quand Pip traverse le champ, le cadre le suit.
- **Bande nette sur fond flou :** pour les titres, les schémas et les plans larges à plusieurs personnages. La bande
  est resserrée pour que les textes restent lisibles sur un téléphone.

Le compteur GROW est redessiné sur toute la largeur. Le haut et le bas de l'écran restent libres pour les boutons et
la légende de TikTok.

Pour les sous-titres, active les sous-titres automatiques de TikTok : ils s'affichent par-dessus sans abîmer l'image.

## Qualité

- **YouTube :**
  - rendu à 2880 × 1620, réduit en Lanczos à 2560 × 1440 (contours plus nets), master en CRF 14 ;
  - fichier livré en H.264 High, 2 passes, 5,9 Mbit/s (91 Mo) pour rester sous la limite de 100 Mo de
    GitHub ;
  - YouTube réencode le 1440p en VP9, ce qui donne une meilleure image à la diffusion qu'un envoi en 1080p.
- **TikTok :** rendu vectoriel direct en 1080 × 1920 (pas un agrandissement), puis H.264 High en 2 passes,
  5,8 Mbit/s (90 Mo).
- **Son :** les deux versions sont à −14,1 LUFS intégrés, crête vraie −1,9 dBTP.

## Refaire les rendus

Depuis `what-if-studio/`, après `npm install` et `./cloud-chrome.sh` dans le conteneur cloud :

```bash
S=../.claude/skills/what-if-animation/scripts
export CARTESIA_API_KEY=…   # seulement pour régénérer la voix
python3 $S/voice_fr.py grow2 && python3 $S/plan.py grow2 && python3 $S/sfx.py grow2 && python3 $S/mixcheck.py grow2
```

Pour chaque partie (`grow` → `Grow`, `grow2` → `Grow2`) :

```bash
npx remotion render src/index.ts Grow2 out/grow2/grow2-hi.mp4 --concurrency=4 --scale=1.5 --crf=12 --x264-preset=slow
ffmpeg -y -i out/grow2/grow2-hi.mp4 -vf scale=2560:1440:flags=lanczos -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -c:a copy out/grow2/grow2-raw.mp4
python3 $S/master.py grow2 --skip-render && python3 $S/srt.py grow2
npx remotion render src/index.ts Grow2Vertical out/grow2/grow2-vertical-raw.mp4 --concurrency=4 --crf=14 --x264-preset=slow
```

La version verticale passe ensuite par la même normalisation à −14 LUFS. Les deux parties sont mises bout à bout avec
le filtre `concat` de ffmpeg. Chaque son est coupé à la durée exacte de son image (1 892 et 1 852 images), pour que
la partie 2 reste synchrone.

Pour revoir un cadrage vertical, change le plan dans `vertical.ts`, puis regarde la composition `Grow2VerticalBoard`
dans le studio Remotion : une image par plan.

## Son

- **Bibliothèque du skill :** sons ElevenLabs générés par son auteur et livrés sous licence MIT. La musique
  d'ouverture est bouclée par `sfx_local.py` (recette `music_loop`).
- **Sons synthétisés** par `sfx_local.py`, dont le battement de cœur de la partie 2.

Vérifie les droits de la bibliothèque avant de monétiser. La musique s'enlève en supprimant `"music"` dans
`episode.json`.
