# Contexte du projet (à lire par Claude Code)

On produit des vidéos TikTok verticales (9:16) sur des notions de l'islam. Le style est en pixel art, inspiré d'une vidéo de référence, et reprend l'identité visuelle de l'application **Nuraq**.
Ce ne sont **pas** des publicités : aucune démo de l'app, aucun appel à l'installer, pas de signature sauf si on la demande.

## Fichiers
- `direction-artistique.md` : analyse de la vidéo de référence, plus la charte commune (palette, polices, composants, zones de sécurité TikTok, mouvement, son, check-list religieuse). **La relire avant toute nouvelle vidéo.**
- `videos/01-heures-de-priere/` : vidéo 01, « Pourquoi l'heure de la prière change chaque jour ? »
  - `brief.md` : brief en 7 points, avec un tableau de sources et leurs réserves (§ 7)
  - `transcription-voix-off.txt` : texte de la voix off, en version générateur de voix et en version horodatée
  - `animatic/render.py` : générateur de la vidéo (Python 3.10+, numpy, Pillow avec libraqm, ffmpeg). `python3 render.py` produit `animatic.mp4` et `sous-titres.srt`. `--stills 12.5,40` exporte des images de contrôle. Les polices se téléchargent toutes seules depuis google/fonts.
  - `animatic/animatic.mp4` : prototype de 86 s, sans voix
  - `images/` : images clés du storyboard et planche

## Règles à respecter (brief du client)
- **Identité Nuraq** :
  - fond `#1D1D1D`, accent violet `#6157F8`, lavande, texte blanc cassé ;
  - Poppins pour le français, une police arabe lisible (Amiri) ;
  - **pas de vert émeraude** comme couleur dominante.
- **Mise en page** :
  - une idée par séquence ;
  - textes courts, grands et stables : ils ne défilent pas et n'ondulent pas ;
  - halos et effets de verre très discrets.
- **Religion** :
  - n'inventer aucune citation, aucun hadith, aucune traduction, aucune règle ;
  - vérifier chaque référence et signaler les divergences ;
  - ne pas représenter les prophètes ;
  - ne jamais utiliser un texte sacré comme décor ;
  - pas d'accroche sensationnaliste ni culpabilisante.
- **Son** : sobre, pas de musique par défaut, droits vérifiés pour tout son ajouté.
- **Vidéo de référence** : s'inspirer des principes, ne pas copier ses plans, ses textes, ses images ou sa musique.

## Voix off avec Cartesia (vidéo 01)
La clé API se lit **uniquement** dans la variable d'environnement `CARTESIA_API_KEY`. Ne jamais l'écrire dans un fichier du dépôt ni la committer.

```bash
cd videos/01-heures-de-priere/animatic
export CARTESIA_API_KEY=…            # clé fournie par l'utilisateur
python3 voix.py --list               # voix françaises masculines, les plus douces en premier
python3 voix.py                      # voix d'homme douce choisie automatiquement → voix/
python3 voix.py --voice-id <id>      # ou une voix imposée
python3 voix.py --only 9 --force     # régénérer une réplique mal prononcée
python3 render.py --voix voix        # → video-voix-off.mp4 + sous-titres-voix-off.srt
```

- **Texte prononcé** : liste `VO_TTS` de `render.py` (graphies phonétiques). **Texte affiché** : liste `VO`.
- **Recalage** : chaque réplique prend sa durée réelle (classe `Timing`). L'image est étirée entre les répliques, les sous-titres sont calés sur les mots quand l'API fournit leurs horaires.
- **Mixage** : voix à environ −18 dBFS RMS, ambiance 21 dB en dessous (`AMBIENCE_UNDER_VOICE_DB`).
- **Voix demandée** : une voix d'homme, douce.

## Prochaines étapes (vidéo 01)
1. Générer la voix (ci-dessus), l'écouter, régénérer les répliques mal prononcées.
2. Faire relire le texte par une personne compétente, puis ouvrir une fois les liens du § 7 de `brief.md`.
3. Exporter la version finale (avec ou sans sous-titres incrustés, selon l'usage des sous-titres automatiques de TikTok).

## Vidéos « What If » (YouTube 16/9), à part de la série Nuraq
- Skill : `.claude/skills/what-if-animation/` (FreshStack, MIT). **Lire d'abord son `VENDORED.md`** : le studio est `what-if-studio/` (pas `<skill>/studio`), la voix se fait avec `scripts/voice_fr.py` (Cartesia si `CARTESIA_API_KEY`, sinon Piper local), les sons manquants avec `scripts/sfx_local.py` (pas d'appel ElevenLabs).
- Studio Remotion : `what-if-studio/` (`npm install` une fois). Épisode 02 : `what-if-studio/src/episodes/grandir/` ; livrables dans `videos/02-what-if-grandir/` (vidéo, storyboard, sous-titres, README avec l'analyse du skill et toutes les commandes).
- Conteneur cloud uniquement : Remotion ne peut pas y télécharger Chrome. Après `npm install`, lancer `what-if-studio/cloud-chrome.sh` (branche le Chromium préinstallé, à travers le proxy pour les Google Fonts).
- Épisode 03 (anglais, rendu en 1440p) : partie 1 dans `what-if-studio/src/episodes/grow/` (les plans de `grandir` y sont rejoués, ancrés sur la fin de leur segment), partie 2 dans `what-if-studio/src/episodes/grow2/`. Livrables dans `videos/03-what-if-grow/` : les deux parties à la suite (2 min 15), en 16/9 pour YouTube et en 9:16 pour TikTok.
- Voix de l'épisode 03 : Cartesia « Garrett – Enthusiastic Pal », émotion `excited`, vitesse 1,0.
  - Elle remplace « Carson », qui chuchotait et faisait tomber des mots de 20 à 40 dB.
  - Elle se génère par petits groupes de phrases ; pour chaque groupe on garde la meilleure de plusieurs prises (voir `VENDORED.md`).
  - `voice_fr.py <slug> --offline` la refait à partir des prises déjà payées, sans clé ni crédit. Les prises retenues sont versionnées dans `src/episodes/<slug>/takes/` (FLAC) : la voix se refait aussi sur un clone neuf.
  - Après `sfx.py`, lancer `duck.py` (la voix d'abord), puis `mixcheck.py`.
- Clé Cartesia : la session lit `CARTESIA_API_KEY` à son démarrage. Une clé changée dans les réglages de l'environnement ne sert qu'à partir d'une nouvelle session.
  - Crédit épuisé : l'API répond HTTP 402.
  - Les tests de voix coûtent des crédits, il faut les faire sur un court extrait.
- Version TikTok : chaque épisode a un `vertical.ts` (cadre 9:16 plan par plan), d'où les compositions `GrowVertical` et `Grow2Vertical`. Le moteur est décrit dans `VENDORED.md`, et toutes les commandes dans le README de la vidéo 03.
- Voix de l'épisode 02 : **provisoire** (Piper). Prochaine étape : voix Cartesia (domaine `api.cartesia.ai` autorisé + `CARTESIA_API_KEY` dans l'environnement), puis relancer `plan.py`, `sfx.py`, `master.py`.
