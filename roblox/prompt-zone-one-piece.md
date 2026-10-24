# Prompt pour Claude Code : zone « One Piece » (pirates) en style stud pour Roblox

> Copier tout ce qui suit dans Claude Code, à la racine du dépôt (branche qui contient `roblox/zone-naruto/`).
> Joindre si possible les captures du jeu actuel (vue aérienne du couloir, entrée « ZONE RARE »).

---

Tu vas créer la **deuxième zone** d'un jeu Roblox du genre « Volez un œuf » (type *Steal a Brainrot*) :
les joueurs courent le long d'un **long couloir rectiligne** découpé en zones à thème d'animé. Chaque zone
demande une vitesse minimale. On attrape un œuf au bout de la zone, puis on revient en courant vers sa base.
Ordre des zones : Naruto (zone 1, déjà faite), **One Piece (zone 2, à faire)**, puis L'Attaque des Titans, etc.

## 1. Ce que je veux

- Une zone **One Piece / pirates**, **magnifique**, en **style stud** Roblox : blocs simples, couleurs franches et
  saturées, studs Roblox classiques sur les sols, les murs d'enceinte et les dessus de toits.
- **Au milieu, un couloir de course vide**, et tout le décor autour. La zone peut être ouverte ou fermée.
- Elle doit être **un peu plus longue que la zone Naruto**, parce que les joueurs y arrivent plus rapides
  (la porte d'entrée affiche « ZONE RARE — VITESSE CONSEILLÉE : 200 »). Vise environ **400 studs**
  de la porte d'entrée à la sortie, contre environ 360 pour la zone Naruto.
- Elle doit pouvoir être **déposée directement dans le jeu** : un fichier `.rbxm` à insérer dans Roblox Studio,
  plus une place de démo `.rbxl` et des rendus PNG pour la valider.
- Tu dois utiliser **Blender** (`pip install bpy` sous Python 3.13, ou le MCP Blender s'il est connecté)
  pour les rendus et la scène `.blend`. Tu génères aussi toutes les textures nécessaires.

## 2. Reprendre le pipeline de la zone Naruto (obligatoire)

Tout existe déjà dans `roblox/zone-naruto/`. **Lis d'abord** `README.md`, `CONVENTIONS.md`, `kit.py`, `zone.py`,
`rendu.py`, `roblox_export.luau` et un asset (`assets/porte.py`). Ensuite, crée `roblox/zone-one-piece/` sur le
même modèle : copie le pipeline, puis remplace le plan et les assets.

- La carte est décrite en **Parts Roblox natives** (bloc, coin, cylindre, boule) par des scripts Python :
  collisions exactes, pas de limite de triangles, rien à téléverser, tout reste modifiable dans Studio.
- Les **studs** sont ceux intégrés à Roblox : matériau Plastic + `SurfaceType.Studs` sur les faces marquées
  (`studs="top"` dans le kit). Aucune image à importer. La texture HD reste optionnelle via `Outils.AppliquerStuds`.
- **Rendu** : `rendu.py` (bpy 5.2, Cycles sur CPU, vue « Standard », ciel en dégradé, brume de distance).
  EEVEE ne marche pas sans GPU.
- **Export** : `roblox_export.luau` avec **Lune** (binaire de github.com/lune-org/lune, release 0.10+), qui produit
  `export/ZoneOnePiece.rbxm` et `export/ZoneOnePiece-demo.rbxl`. Les fichiers sont relus et vérifiés.
- Pour accélérer, fais construire les assets **en parallèle par des sous-agents** (un fichier `assets/*.py`
  chacun). Chacun fait au moins trois tours de rendu et de correction avec `apercu.py`. Ensuite, un relecteur
  indépendant critique et corrige chaque asset.

## 3. Repère et dimensions (mêmes conventions que Naruto)

- Repère Roblox : Y en haut, 1 unité = 1 stud. Un personnage mesure environ 5 studs de haut.
- L'origine du modèle est au **centre de l'entrée** (sol de la porte d'entrée). On court vers **-Z**.
- **Couloir de course : `x ∈ [-30, 30]`, rien de solide dedans** au sol. Vérifie-le avec la fonction
  `couloir_libre`, qui doit trouver 0 élément.
- Trottoirs ou quais jusqu'à `|x| = 40`, puis le décor. Largeur totale d'environ 260 studs, plus le fond.
- **Rien au-dessus du couloir sous 30 studs** (guirlandes, cordages, mâts, ponts), sinon la caméra Roblox saute.
- Longueur : porte à z = 0 ; plage de la rue ou du port jusqu'à environ -300 ; **place des œufs**
  (cercle de rayon environ 34) vers -330 ; sortie vers -400 vers la zone 3.
- Repères invisibles dans un dossier `Reperes` : `ZoneOeufs`, `Entree`, `Sortie`, `Couloir`.
- Budget : **12 000 pièces au maximum**. Pas de collision ni d'ombre sur les petits détails, et grands
  ensembles découpés en blocs de 64 studs pour le streaming.

## 4. Ce que montrent les captures du jeu actuel (zone One Piece, à rendre plus belle)

- Elle suit la zone Naruto. Elle s'ouvre par un portique bleu marine à piliers roses
  « ZONE RARE / VITESSE CONSEILLÉE : 200 ». C'est l'élément de gameplay du jeu : **garde une arche d'entrée
  avec un panneau lisible des deux côtés**, lettres d'au moins 4-5 studs, en SurfaceGui.
- Allée de **sable clair** bordée de **palmiers**, **guirlandes de fanions colorés**, une **rivière bleue**
  de chaque côté, un **bateau pirate** amarré sur la rivière (coque brune, voiles blanches), un **phare
  rayé rouge et blanc**, une cabane en bois, un **coffre au trésor**, une grosse **pièce de viande sur l'os**
  au bord de l'allée, et des falaises vertes en blocs sur les côtés.
- Ces éléments sont aujourd'hui trop simples et clairsemés : il faut une composition riche, lisible et cohérente.

## 5. Direction artistique One Piece (inspiration générique, sans copier la licence)

Repères à exploiter (voir références visuelles d'East Blue, de Water 7, de Sabaody et de la plage de Fuchsia Village) :
- **Port pirate tropical** : quais en planches, pontons, bittes d'amarrage, cordages, tonneaux, caisses,
  filets, ancres, canons. L'eau turquoise est visible de chaque côté du couloir.
- **Deux ou trois navires pirates** à quai, qui servent de grands repères visuels : coques bois rouge-brun
  et jaune, voiles blanches gonflées, figure de proue animale **générique** (mouton, lion ou dragon stylisé),
  pavillons à tête de mort **générique** (aucun chapeau de paille, aucun emblème précis de la série).
- **Village de pêcheurs coloré** : maisons de bois et d'enduit, toits rouges, bleus et turquoise, auvents rayés,
  stands de fruits, marchand de viande sur l'os, taverne, tonneaux de rhum.
- **Phare rayé rouge et blanc** et **grands palmiers** courbés, plage de sable, rochers, coquillages, crabes.
- **Repère final derrière la place des œufs** : une grande **arche de rochers marins** ou une **crique**
  avec un énorme navire échoué ou un rocher en forme de crâne. Le couloir passe dessous ou entre les deux
  vers la zone suivante, comme le passage dans le rocher des Hokage.
- Palette : sable `#F2DFA7`, eau `#3FC1E0` / `#2AA3D0`, bois `#8A5A36` / `#5E3B24`, voiles `#F8F4E8`,
  rouge `#D63A2F`, jaune `#F5C842`, turquoise `#3FB8A8`, palmier `#4FA23A` / `#6CBF45`, tronc `#9C6B3E`.
  Pas de gris sale.
- Guirlandes de fanions colorés au-dessus du couloir (au-dessus de 30 studs), lanternes de navire, filets.

## 6. Règles pour éviter une restriction Roblox (propriété intellectuelle)

Roblox retire les jeux qui utilisent une licence sans autorisation. Respecte donc ces règles :
- **Aucun nom** de la licence dans la zone : One Piece, Luffy, Thousand Sunny, Going Merry, Baratie, etc.
- **Aucun emblème exact** : pas de tête de mort au chapeau de paille, pas de logo de la Marine, pas de figure
  de proue en lion du Sunny ni en mouton du Merry identiques.
- Aucun personnage représenté. Uniquement des éléments génériques de pirates et de mer tropicale.
- Côté jeu, éviter aussi ces noms dans le titre, les miniatures et le nom de la zone.

## 7. Étapes attendues

1. Lire le pipeline Naruto (section 2) et les captures. Proposer le plan de la zone en 10 lignes.
2. Créer `roblox/zone-one-piece/` : copier `kit.py`, `blender_scene.py`, `textures.py`, `apercu.py`,
   `rendu.py` et `roblox_export.luau`, puis adapter les noms (`ZoneOnePiece`).
3. Écrire `palette.py` et les assets en parallèle :
   - `porte.py` : arche « ZONE RARE / VITESSE CONSEILLÉE : 200 » en style pirate, avec cordages et bouées ;
   - `navires.py` ;
   - `port.py` : quais, pontons, eau, bittes ;
   - `maisons.py` : village, taverne, stands ;
   - `phare.py` ;
   - `nature.py` : palmiers, rochers, plage ;
   - `mobilier.py` : tonneaux, canons, coffres, fanions, filets ;
   - `crique.py` : le repère final avec le passage.
4. Écrire `zone.py` : sol en pixels (planches et sable), eau, rangées d'éléments, place des œufs, repères.
   Vérifier `couloir_libre` et le budget de pièces.
5. Lancer `rendu.py` pour produire les vues aérienne, entrée, rue, place, retour, côté, repère final et plan,
   puis l'export `.blend`, `.rbxm` et `.rbxl`. Me montrer les images.
6. Écrire un `README.md` en français : comment importer la zone, les dimensions, les réglages.
   Committer et pousser.

Critère de réussite : en regardant les rendus, on doit penser immédiatement « port pirate façon One Piece »,
c'est beau et lisible à grande vitesse, le couloir est vide, et le `.rbxm` s'insère tel quel dans Roblox Studio.
