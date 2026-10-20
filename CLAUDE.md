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

## Prochaines étapes (vidéo 01)
1. Générer la voix off à partir de `transcription-voix-off.txt` (version A).
2. Recaler l'animatic sur la vraie voix :
   - dans `render.py`, mettre à jour les temps de la liste `VO`, ceux des éléments de `build_timeline()`, les clés de `SKY_CLOCK` et les `NODE_TIMES` ;
   - ajouter une option `--voix fichier.mp3` qui mixe la voix avec l'ambiance, en plaçant l'ambiance 18 à 24 dB sous la voix.
3. Faire relire le texte par une personne compétente, puis ouvrir une fois les liens du § 7 de `brief.md`.
4. Exporter la version finale (avec ou sans sous-titres incrustés, selon l'usage des sous-titres automatiques de TikTok).
