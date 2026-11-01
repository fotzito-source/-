# Spot promotionnel Nuraq : « un seul fil de lumière »

Motion design de 26 s pour présenter l'app, inspiré de la grammaire du spot Duolingo. Deux versions :

| Fichier | Format | Usage |
|---|---|---|
| `nuraq-spot-9x16.mp4` | 1080 × 1920, 30 i/s | TikTok, Reels, Shorts |
| `nuraq-spot-16x9.mp4` | 1920 × 1080, 30 i/s | YouTube |

Tout est fabriqué à partir de l'app : vrais écrans (reconstitués avec les tokens de `app/theme/tokens.ts`), vrais contenus (`app/data`), vraies illustrations (îles, mascotte, logo).

## Ce qu'on reprend du spot Duolingo

| Principe Duolingo | Transposition Nuraq |
|---|---|
| Un fil lumineux unique relie toutes les scènes | Une lueur violette douce (pas un néon) : elle dessine le logo, parcourt la carte des îles, entoure le téléphone, souligne les jours, descend le long du parcours, se ramifie vers les îles |
| Une fonction = une action forte en 2 s | Exercice validé, lecture reprise, série qui s'allume, niveaux qui se valident, parcours qui s'ouvrent |
| Vraie interface du produit | Écrans reconstitués fidèlement : séance d'exercice, bibliothèque et lecteur du Coran, série, parcours des Piliers |
| Logo au début et à la fin | Le fil dessine le symbole Nuraq, puis le logo complet « Level up your iman » |
| Slogan en deux temps (« One path. Every skill. ») | « Comprendre. Pratiquer. Progresser. » sur un mini-parcours à trois étapes |

**Volontairement écarté** :
- la course au classement (le brief Nuraq exclut la compétition) ;
- tout effet sur le texte du Coran ;
- la mascotte et le slogan de Duolingo.

## Découpage (grille de 100 BPM, 1 temps = 0,6 s)

| Temps | Scène | Légende |
|---|---|---|
| 0:00 – 2:24 | L'étoile du logo scintille, la lumière dessine le symbole, anneau au remplissage, « NURAQ » lettre par lettre, puis le slogan | — |
| 2:24 – 4:48 | Carte des îles : Coran, Prière, Piliers, le fil suit le chemin | « Apprends l'islam / pas à pas » |
| 4:48 – 9:36 | Téléphone : « Combien de piliers l'Islam compte-t-il ? » → 5 → « Bien joué ! » + explication | « Des exercices courts / et une explication à chaque réponse » |
| 9:36 – 12:36 | Bibliothèque du Coran → reprise de la lecture → Al-Fatiha, verset 1 | « Lis le Coran / et reprends ta lecture » |
| 12:36 – 15:00 | Série : 7 jours qui s'allument | « Garde le rythme / un jour après l'autre » |
| 15:00 – 17:24 | Parcours des Piliers : Shahada → Hajj, 0 → 100 % | « Chaque niveau / débloque le suivant » |
| 17:24 – 19:48 | Le fil se ramifie vers 5 îles : Prière, Coran, Prophètes, Ramadan, Hajj & Umrah | « 12 parcours / des Piliers au Ramadan » |
| 19:48 – 22:48 | Mascotte + « Comprendre. Pratiquer. Progresser. » | — |
| 22:48 – 26:24 | Logo complet + mention des sources du texte coranique | — |

## Contenus et sources affichés

- **Exercice** : exercice `shahada-count` de `app/data/pillarsCourse.ts`.
  - Question : « Combien de piliers l'Islam compte-t-il ? »
  - Réponse : 5.
  - Explication : « Les cinq piliers sont la Shahada, la Salat, la Zakat, le Sawm et le Hajj. »
  - Titre du retour : « Bien joué ! », une des formules de `exerciseFeedback.ts`.
- **Coran** : Al-Fatiha, versets 1 et 2, tirés de `app/data/quran/chapters/1.json`.
  - Texte arabe : Tanzil Project.
  - Traduction : Rachid Maach (QuranEnc 1.0.3).
  - Le texte arabe est reproduit tel quel ; seul l'appel de note « [1] » est retiré de la traduction.
  - La mention des sources apparaît dans l'écran du lecteur et en fin de spot (licence Tanzil : copie à l'identique, source citée).
- **Parcours des Piliers** : titres et descriptions des 5 niveaux de `pillarsCourse.ts`.
- **12 parcours** : `LEARNING_PATH_IDS` de `app/data/learningPaths.ts`. Les noms courts des îles viennent de `shortTitle`.
- **Série** : écran `StreakDetailsScreen` (« jours de série », « Tes 7 derniers jours »), avec les icônes officielles de `ResourceIcon.tsx`.

## Licences des éléments

| Élément | Source | Licence |
|---|---|---|
| Logo, îles, mascotte, icônes de ressources | Dépôt `nuraq-app` | Propriété de Nuraq |
| Poppins, Amiri Quran | Google Fonts | SIL OFL (`spot/assets/fonts/OFL-*.txt`) |
| Icônes Feather | `feather-icons` | MIT (`spot/assets/LICENSE-feather.txt`) |
| Texte arabe du Coran | Tanzil Project | CC BY 3.0, copie à l'identique |
| Son | Synthétisé (`son/son.py`) | Libre, aucune musique |

## Voix off

- **Voix utilisée** : Solène (Cartesia, sonic-3.6, fr-FR, vitesse 1.1), fichier `son/voix-off-solene.wav`.
  - « Des exercices courts… et une explication à chaque réponse » est jouée d'une traite. L'exercice a été avancé pour que « Bien joué ! » arrive avec « et une explication ».
  - La réplique 5 a été régénérée avec la même voix (`son/voix-ligne05-solene.wav`) : « Lis le Coran et reprends ta lecture ». Dans la prise d'origine, « lis » était presque inaudible.
- **Placement** : `son/voix-placement.json` indique, pour chaque réplique, son passage dans le fichier et l'instant où elle démarre dans le spot. Ce placement est calé sur le texte à l'écran : la 2e ligne de chaque légende arrive avec la 2e moitié de la phrase.
- **Versions avec voix** : `nuraq-spot-9x16-voix.mp4` et `nuraq-spot-16x9-voix.mp4`, produites par `python3 mix-voix.py --plan son/voix-placement.json`.
  - Les effets baissent de 9 dB sous la voix, et le niveau final vise −16 LUFS.
  - Le script accepte aussi un dossier (un fichier par réplique) ou un fichier unique, découpé aux silences.
- **Texte de référence** : `voix-off.txt`.

## Son

Il n'y a pas de musique, seulement un design sonore synthétisé :
- souffles aux transitions ;
- impact doux au logo ;
- clics de toucher ;
- signal de bonne réponse ;
- petits « pops » quand un jour ou un niveau s'allume.

Niveau : environ −16,5 LUFS, crête à −1 dBFS.

Les changements de scène tombent sur une grille de 100 BPM. Une musique sous licence à ce tempo pourra être ajoutée sans recaler l'image.

## Refaire le rendu

Il faut Node 18 ou plus, Playwright avec Chromium, Python 3 avec numpy, et ffmpeg.

```bash
python3 son/son.py                       # → son/nuraq-spot.wav
node render.mjs                          # → nuraq-spot-9x16.mp4 et nuraq-spot-16x9.mp4
node render.mjs --format 16x9            # un seul format
node render.mjs --stills 6.6,11.9        # images de contrôle dans controle/
```

Pour prévisualiser une image précise dans un navigateur, ouvrir `spot/index.html?format=16x9`, puis taper `seek(7.8)` dans la console.

Les textes des légendes se trouvent dans `CAPTIONS`, en haut de `spot/spot.js`. Les tailles et positions par format se trouvent dans l'objet `LAY`.
