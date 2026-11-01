# Vidéo 03 : « What if you could grow at will? » (anglais, parties 1 et 2)

L'histoire en anglais, en deux parties montées à la suite, faite avec le skill
[what-if-animation](https://github.com/kelano86/what-if-animation) (copie dans `.claude/skills/what-if-animation/`).
Elle existe en deux formats : 16/9 pour YouTube et 9:16 pour TikTok.

| Fichier | Contenu |
|---|---|
| `grow-full-youtube.mp4` | **YouTube** : les parties 1 et 2 à la suite, 2 min 15 (134,6 s), 2560 × 1440 (1440p) |
| `grow-full-tiktok.mp4` | **TikTok** : la même vidéo recadrée en 9:16, 1080 × 1920 |
| `grow-full.srt` | Sous-titres anglais de la vidéo complète, à importer sur YouTube |
| `thumbnail.jpg` | Miniature YouTube 1280 × 720 |
| `tiktok-cover.jpg` | Couverture TikTok 1080 × 1920 |
| `storyboard.jpg`, `storyboard-part2.jpg` | Les plans des parties 1 (32 plans) et 2 (30 plans), une image clé chacun |
| `cartesia-script.txt`, `cartesia-script-part2.txt` | Le texte dit par la voix, partie par partie |
| `report.json` | Mesures des deux versions : durée, débit, loudness, crête |
| `../../what-if-studio/src/episodes/grow/`, `grow2/` | Les sources : `episode.json` (script, science, montage, son), `shots.tsx` (les plans), `index.tsx` (le look GROW), `vertical.ts` (le cadrage 9:16), `takes/` (les prises de voix retenues) |

## L'histoire

- **Partie 1 (68 s)** : Pip découvre qu'il grandit quand il dit « grow ». D'abord le bocal de cookies, puis il devient
  un colosse au-dessus de la ville, jusqu'au premier pas où son fémur casse. Le lendemain, un homme en costume
  l'attend dans la cuisine avec une photo de lui. Puis le plafond se fissure : à l'étage, sa petite sœur vient de dire
  le mot. Carton : « PART 1 / WHAT WOULD YOU DO? ».
- **Partie 2 (66 s), « The word »** : la suite immédiate.
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

- **Voix :** Cartesia `sonic-3`, « Garrett – Enthusiastic Pal », émotion `excited`, vitesse 1,0.
  - Sur dix voix Cartesia mesurées, c'est la plus proche de la toute première voix provisoire (Piper « Ryan ») :
    un timbre clair et jeune, autour de 180 Hz (170 Hz pour Ryan), une voix pleine et enjouée.
  - Ryan ne peut pas servir pour la version publiée : sa licence interdit l'usage commercial.
- **Pourquoi elle remplace « Carson » :** générée d'un seul bloc, la voix Carson dérivait. Elle chuchotait par
  endroits et faisait tomber certains mots de 20 à 40 dB, comme « He » ou « You ».
- **Génération :** par petits groupes de phrases (180 caractères au plus), avec jusqu'à trois prises par groupe.
  `voice_fr.py` garde la meilleure. Une prise perd des points pour chaque mot trop faible, chaque mot chuchoté et
  chaque mot que la reconnaissance vocale locale (NeMo Parakeet) n'entend pas.
- **Finition :** le volume est égalisé mot par mot, puis passé dans un compresseur doux. « Grow! » est dit comme un
  ordre.
- **Mesures sur la piste de voix finale**, niveau de chaque mot comparé au niveau médian des mots :

  | | Partie 1, Carson | Partie 1, Garrett | Partie 2, Carson | Partie 2, Garrett |
  |---|---|---|---|---|
  | Mots à plus de 6 dB sous les autres | 36 | 0 | 47 | 0 |
  | Mots à plus de 10 dB sous les autres | 16 | 0 | 30 | 0 |
  | Mot le plus faible | −33,7 dB (« He ») | −2,8 dB | −39,1 dB (« You ») | −4,7 dB |
  | Écart type des niveaux | 6,6 dB | 0,7 dB | 7,7 dB | 0,8 dB |

  Dans la nouvelle voix, la reconnaissance vocale retrouve tous les mots du texte. Elle écrit seulement « mom » pour
  « Mum » et « anytime » pour « any time ».
- **Prises versionnées :** les prises retenues sont dans `src/episodes/grow/takes/` et `grow2/takes/`, en FLAC (sans
  perte, 4,4 Mo en tout). `voice_fr.py <slug> --offline` refait la voix à partir d'elles, au bit près, sans clé ni
  crédit.
- **Clé :** lue uniquement dans la variable d'environnement `CARTESIA_API_KEY`, jamais écrite dans le dépôt.
  - Une session lit la clé à son démarrage : une clé changée dans les réglages ne sert qu'à partir d'une nouvelle
    session.
  - Si l'API répond HTTP 402, le crédit est épuisé.
- **Montage :** l'API donne l'horaire de chaque mot, et tout le montage s'y accroche : les coupes, les actions des
  plans et les bruitages.
- **Mixage :** pendant que l'on parle, `duck.py` garde les bruitages au moins 5 dB sous la voix et la musique au moins
  8 dB sous la voix. Dans les silences, les impacts gardent toute leur force.

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
  - fichier livré en H.264 High, 2 passes, au débit le plus haut qui reste sous 95 Mo (la limite de GitHub est
    100 Mo) ;
  - YouTube réencode le 1440p en VP9, ce qui donne une meilleure image à la diffusion qu'un envoi en 1080p.
- **TikTok :** rendu vectoriel direct en 1080 × 1920 (pas un agrandissement), puis H.264 High en 2 passes, sous 95 Mo
  aussi.
- **Son :** les deux versions ont la même bande son, à −14 LUFS intégrés, crête vraie sous −1 dBTP, en AAC
  256 kbit/s.

Les débits, les tailles et les mesures exactes de chaque version sont dans `report.json`.

## Refaire les rendus

Depuis `what-if-studio/`, après `npm install` et `./cloud-chrome.sh` dans le conteneur cloud :

```bash
S=../.claude/skills/what-if-animation/scripts
python3 $S/voice_fr.py grow2 --offline   # la voix, à partir des prises versionnées
python3 $S/plan.py grow2 && python3 $S/sfx.py grow2
python3 $S/duck.py grow2 --sfx 5 --music 8 --max 14 && python3 $S/mixcheck.py grow2
```

Si le texte change, il faut de nouvelles prises : `export CARTESIA_API_KEY=…`, puis `voice_fr.py grow2` sans
`--offline`. Chaque prise coûte des crédits Cartesia, donc les essais se font sur un court extrait.

Pour chaque partie (`grow` → `Grow`, `grow2` → `Grow2`) :

```bash
npx remotion render src/index.ts Grow2 out/grow2/grow2-hi.mp4 --concurrency=4 --scale=1.5 --crf=12 --x264-preset=slow
ffmpeg -y -i out/grow2/grow2-hi.mp4 -vf scale=2560:1440:flags=lanczos -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -c:a copy out/grow2/grow2-raw.mp4
python3 $S/master.py grow2 --skip-render && python3 $S/srt.py grow2
npx remotion render src/index.ts Grow2Vertical out/grow2/grow2-vertical-raw.mp4 --concurrency=4 --crf=14 --x264-preset=slow
```

La version verticale passe ensuite par la même normalisation à −14 LUFS. Les deux parties sont mises bout à bout avec
le filtre `concat` de ffmpeg. Chaque son est coupé à la durée exacte de son image (2 048 et 1 990 images), pour que
la partie 2 reste synchrone. La bande son complète est ramenée à −14 LUFS, puis limitée à −2 dBFS avec un
suréchantillonnage ×4, pour que la crête reste sous −1 dBTP après l'encodage AAC.

Pour revoir un cadrage vertical, change le plan dans `vertical.ts`, puis regarde la composition `Grow2VerticalBoard`
dans le studio Remotion : une image par plan.

## Son

- **Bibliothèque du skill :** sons ElevenLabs générés par son auteur et livrés sous licence MIT. La musique
  d'ouverture est bouclée par `sfx_local.py` (recette `music_loop`).
- **Sons synthétisés** par `sfx_local.py`, dont le battement de cœur de la partie 2.

Vérifie les droits de la bibliothèque avant de monétiser. La musique s'enlève en supprimant `"music"` dans
`episode.json`.
