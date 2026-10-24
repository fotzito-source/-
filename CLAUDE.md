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

## Autre projet du dépôt : carte Roblox « zone Naruto » (`roblox/zone-naruto/`)
Zone Konoha en style stud pour un jeu Roblox de type « Volez un œuf » (couloir de course vide au centre, décor autour).
- Tout est décrit en **Parts Roblox** (bloc, coin, cylindre, boule) par des scripts Python : `zone.py` (plan), `assets/*.py` (assets), `kit.py`, `palette.py`. Lire `CONVENTIONS.md` avant d'ajouter un asset.
- `rendu.py` (Python avec `bpy` 5.2, Cycles CPU) fait les rendus `rendus/*.png` et exporte `export/` ; `roblox_export.luau` (Lune) écrit le modèle `.rbxm` et la place `.rbxl`.
- Studs : `SurfaceType.Studs` sur matériau Plastic par défaut (aucune image à téléverser) ; texture HD optionnelle via `Outils.AppliquerStuds`.
- Le couloir `|x| < 30` reste vide ; rien au-dessus du couloir sous 30 studs (caméra Roblox).
