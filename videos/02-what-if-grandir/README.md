# Vidéo 02 : « Et si tu pouvais grandir à volonté ? » (What If, YouTube 16/9)

Un épisode **What If** complet, fait avec le skill [what-if-animation](https://github.com/kelano86/what-if-animation)
de FreshStack (copie dans `.claude/skills/what-if-animation/`, voir son `VENDORED.md`).

- **Format :** 1920 × 1080, 30 i/s, 16/9 pour YouTube.
- **Durée :** {DUREE} s.
- **Structure :** 24 plans sur les 7 temps de la formule What If, en version longue. La version courte du skill
  (15 à 25 s) n'en garde que l'ouverture.
- **Image :** tout est dessiné en code (SVG rendu par Remotion). Il n'y a ni modèle d'image, ni modèle vidéo.
- **Son :** mixage à {LUFS} LUFS intégrés, crête vraie {TP} dBTP. La norme YouTube est −14 LUFS et moins de −1 dBTP.

| Fichier | Contenu |
|---|---|
| `grandir-final.mp4` | La vidéo finale, prête à téléverser |
| `storyboard.jpg` | Le storyboard : une image clé par plan, avec le texte dit et la note de plan |
| `miniature.jpg` | Une miniature YouTube 1280 × 720 : le plan S10 et le titre dans la police du skill (Bricolage Grotesque, OFL) |
| `grandir.srt` | Sous-titres pour l'import YouTube (à ne pas incruster : le style du genre n'en met pas à l'image) |
| `script.md` | Le texte, temps par temps, et la science avec ses sources |
| `../../what-if-studio/src/episodes/grandir/` | Les sources de l'épisode : `episode.json` (script, science, plans, montage, son), `shots.tsx` (les 24 plans), `index.tsx` (le look du pouvoir) |

> **La voix est provisoire.** C'est une voix de synthèse locale (Piper, `fr_FR-tom-medium`), utilisée parce que ni
> Cartesia ni ElevenLabs ne sont joignables depuis l'environnement cloud où la vidéo a été faite. Le passage à
> Cartesia est décrit plus bas : une commande régénère la voix, et le montage, les bruitages et le mixage se recalent
> sur les mots de la nouvelle voix.

## Ce que fait le skill (analyse)

Le skill transforme une ligne de sujet en épisode fini. Il travaille en 8 étapes, et chacune s'arrête sur quelque chose
qu'on regarde avant de passer à la suivante.

1. **Script.** La formule en 7 temps, décodée sur cinq scripts de quatre chaînes :
   - ouverture en pleine action, avec trois démos ;
   - prémisse au carton titre ;
   - le plaisir ;
   - le revers, avec un vrai fait chiffré suivi de « C'est réel » ;
   - quelqu'un de puissant remarque ;
   - la famille en jeu ;
   - un cliffhanger.

   Les phrases sont à la 2e personne, courtes, et chacune doit être une image. Chaque fait est calculé et sourcé dans le
   champ `science` avant d'entrer dans le texte.
2. **Voix.** ElevenLabs donne les horaires de chaque caractère. Les pauses sont ensuite coupées au rythme du genre :
   0,12 s entre deux mots, 0,3 s après un point.
3. **Plan de montage.** Une coupe par image du texte. Chaque coupe est calée sur un mot, 2 images avant lui. `plan.py`
   mesure le rythme : le genre fait 27 coupes par minute en ouverture, et aucun plan fixe ne dépasse 3 s.
4. **Storyboard.** Une image clé par plan (`stills.mjs`), rassemblées dans une planche légendée (`board.py`).
5. **Auto-contrôle.** Une check-list de 11 points :
   - lecture en une seconde ;
   - tailles de plan qui changent ;
   - lumière qui vient d'une source visible ;
   - personnage qui ressort ;
   - profondeur ;
   - monde plein ;
   - perspective ;
   - jeu d'acteur ;
   - continuité ;
   - texte réduit au titre et aux affichages ;
   - originalité.

   On corrige, on recommence, et on n'anime rien avant que la planche passe.
6. **Animation.** Poses clés avec anticipation, dépassement et retour, visages qui changent en un clignement,
   mouvements de caméra, look du pouvoir. Chaque plan est une fonction pure de son horloge `t` : le moteur peut donc
   jouer un plan à l'envers ou le figer.
7. **Son.** Un effet par action visible, aligné sur son attaque. Une ambiance par lieu, et une nappe musicale qui se
   coupe au revers. Un choc qui illustre un mot tombe dans la pause *après* ce mot. `mixcheck.py` liste les endroits où
   les effets couvrent la voix.
8. **Master.** Rendu, puis −14 LUFS et crête sous −1 dBTP, avec un rapport (durée, loudness, rythme, crédits).

Le moteur (`what-if-studio/src/engine`) contient :

- une seule ossature de personnage, avec un costume par personnage : Pip, Mo, la sœur, la mère, l'homme en costume ;
- des décors en vraie perspective à un point de fuite : cuisine, escalier, toit, chambre, bureau, classe, schéma ;
- une lumière qui vient toujours d'une source (fenêtre au soleil couchant, suspensions, appliques), un voile qui
  assombrit les tons moyens, une lumière de contour chaude et du grain.

Le personnage ne dérive jamais d'un plan à l'autre, puisque c'est la même fonction qui le dessine.

**Points forts.** La méthode est rigoureuse : storyboard d'abord, contrôle visuel et sonore mesuré, faits sourcés. Le
rendu « crépuscule » est très soigné, et le montage reste calé sur les mots, donc il suit une nouvelle voix tout seul.

**Limites.** Le jeu d'acteur reste simple : la main ne peut pas toucher la tête, et les poses assises sont délicates.
Chaque plan s'écrit à la main, en code. Le skill dépend d'ElevenLabs pour la voix et les sons. Il est écrit pour des
épisodes de 15 à 25 s en anglais.

## Ce qui a été adapté pour cette vidéo

- **Français et version longue :** les 7 temps en 35,9 s au lieu de 15 à 25 s.
- **Voix :** `voice_fr.py`, ajouté au skill.
  - Avec Cartesia, une seule prise et les horaires de mots donnés par l'API.
  - Sinon, Piper en local, avec les horaires de mots tirés de la durée de chaque phonème.

  Whisper a servi à vérifier la prononciation, d'où quelques graphies phonétiques dans le champ `tts`.
- **Sons :** aucun appel API.
  - 16 sons viennent de la bibliothèque livrée avec le skill, réutilisés avec leur invite exacte.
  - 8 sons sont synthétisés par `sfx_local.py` : la pousse, le craquement de bois, le tic d'horloge, le grondement,
    la photo qui glisse, l'os qui casse, le pas de géant, les ailes de pigeons.
- **Décor du toit :** un calque `between` pour placer un géant entre la ville et le toit.
- **Sous-titres :** `srt.py`.

## Régénérer la vidéo

Une fois par machine :

```bash
cd what-if-studio && npm install
```

```bash
pip install numpy pillow scipy piper-tts onnx
```

Dans un conteneur Claude Code cloud, lance aussi `./cloud-chrome.sh` depuis `what-if-studio/`. Remotion ne peut pas y
télécharger son Chrome : le script branche le Chromium préinstallé et le fait passer par le proxy pour les Google Fonts.
Sur ta machine, c'est inutile.

Puis, depuis `what-if-studio/` (`S` désigne le dossier des scripts du skill) :

```bash
S=../.claude/skills/what-if-animation/scripts
python3 $S/voice_fr.py grandir          # voix → public/grandir/voice.wav + words.json
python3 $S/plan.py grandir              # montage calé sur les mots → timeline.json
python3 $S/sfx_local.py grandir         # sons synthétisés manquants → library/sfx/
python3 $S/sfx.py grandir               # pistes effets + musique, niveaux
python3 $S/mixcheck.py grandir          # voix bien au-dessus des effets ?
node $S/stills.mjs grandir && python3 $S/board.py grandir   # storyboard
python3 $S/master.py grandir            # rendu + −14 LUFS → out/grandir/grandir-final.mp4
python3 $S/srt.py grandir               # sous-titres → out/grandir/grandir.srt
```

## Passer à la voix Cartesia

1. Dans les réglages de l'environnement cloud, ouvre **Accès réseau** et ajoute `api.cartesia.ai` aux domaines
   autorisés.
2. Ajoute la clé en variable d'environnement `CARTESIA_API_KEY`. Elle ne va jamais dans un fichier du dépôt.
3. Ouvre une nouvelle session, puis lance ceci depuis `what-if-studio/` :

```bash
python3 ../.claude/skills/what-if-animation/scripts/voice_fr.py grandir --list
```

```bash
python3 ../.claude/skills/what-if-animation/scripts/voice_fr.py grandir --backend cartesia
```

La première commande liste les voix d'homme françaises ; la seconde génère la voix. Pour imposer une voix, mets son
identifiant dans `voice.cartesia.id` de `episode.json`. Relance ensuite `plan.py`, `sfx.py`, `mixcheck.py`, `master.py`
et `srt.py`, dans cet ordre. Les coupes et les bruitages suivent les mots.

## Son : provenance et droits

- **Bibliothèque du skill.** Ambiances, boum du titre, nappe sombre, croc de cookie, lunettes, étincelle, compteur,
  etc. Ces sons ont été générés avec ElevenLabs par l'auteur du skill, sur un forfait payant, et sont livrés dans son
  dépôt sous licence MIT pour être réutilisés. Vérifie que cela te suffit avant de monétiser.
- **Nappe musicale.** Pizzicato et glockenspiel, de la même bibliothèque. Elle joue sous l'ouverture et se coupe au
  revers (« Un détail »). Pour la retirer, supprime `"music"` dans `episode.json`, puis relance `sfx.py` et `master.py`.
- **Sons synthétisés** par `sfx_local.py` : faits ici, sans droits tiers.
- **Voix provisoire** (Piper `fr_FR-tom-medium`) : le modèle est publié sous AGPLv3. Pour une diffusion, mieux vaut la
  remplacer par la voix Cartesia.

## Ce que j'améliorerais encore

- La voix Cartesia, plus vivante que Piper, surtout sur « Grandis » et sur la question finale.
- Une démo du « plaisir » plus longue, si tu veux une version d'une minute : un autre usage du pouvoir avant le revers.
- Des marches et des jeux de mains plus fins. C'est la limite connue du skill : l'ossature est simple.
