# Conception : carte « île du futur » (CarteEgghead)

**L'idée.** On garde **à l'identique la forme et la taille** de la carte de référence (refEH1, refEH2 : un jeu
« Steal a … » à parcelles et tapis central) et on change tout l'habillage : la ville nocturne de gratte-ciel devient
**une ville-jouet rétro-futuriste en plein midi tropical**, l'île scientifique de l'anime (tours rondes en bonbon,
dômes à hublots, cônes rayés, soucoupes, anneaux et tubes de verre, palmiers, sol vert quadrillé), et, tout au bout
de l'axe du tapis, **l'œuf-laboratoire fêlé posé sur son cumulus** domine le ciel. Tout le sol est en studs. Les
8 parcelles des joueurs restent **vides** (l'utilisateur construira les bases) et sont marquées par des repères.

Fichiers : `plan.py` (toutes les cotes), `palette.py` (couleurs), `CONVENTIONS.md` (règles), `SPECS.md` (fiche de
chaque module), bible de style `/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/eh/style/STYLE.md` (archétypes T01-T18, K01-K07,
mobilier M01-M21, ciel C01-C16, pièces de jeu G01-G07). Plan de contrôle :
`/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/eh/conception/plan_conception.png` (vue de dessus, chaque emplacement coloré par module).

## 1. Ce qu'on garde de la référence (formes et tailles, analyste A)

| Élément | Cote | Source |
|---|---|---|
| Pelouse | 410 × 602 (|x| ≤ 205, |z| ≤ 301) | mesuré 409 × 602, ±0,5 |
| Trottoir intérieur, route, trottoir extérieur | 12, **36** (2 voies), 18 | mesuré 12-13, 35,5-36,75, 17,5 |
| Ligne des façades de la couronne | |x| = 271, |z| = 367 ; profondeur 80 → emprise 702 × 894 | façades mesurées à l'est et au sud |
| Tapis (U ouvert, refermé au sud) | bande 16,1 = 3,1 + 9,9 + 3,1 ; voies à x = ±48,38 ; demi-octogone au sud (z 258 → 294) ; têtes en z = -281 | rms < 0,3 px sur 4 lignes |
| Parcelles | 8 × (111 × 105), |x| 80 → 191, rangées z = 215,5 / 71,75 / -72 / -215,75 ; escaliers |x| 80 → 65 sur 55 | ±2 au sud, ±10 au nord |
| Stand de vente, machine, sanctuaire, socle | 28 × 28 en (-17, 242) ; 12 × 10 en (25, 240) ; 34 × 34 en (0, 127) ; Ø 36 en (0, 34) | ±0,5 à ±5 |
| Joueur de refEH1 → `Spawn` | (-3, 206,5), regard vers le nord | ±0,5 |
| Caméras des deux captures | vues `capture1` et `capture2` (plan.VUES) | calibrées (f = 760 px) |

Les nombres arrondis au stud entier restent dans l'erreur de mesure. La moitié nord (rangées 3-4, têtes du tapis,
portails) est en miroir de la moitié sud (±10 à 25) : si l'analyse finale (`plan/LAYOUT.md`) corrige une cote, on
la change dans `plan.py` et tout suit.

## 2. Table de correspondance : chaque élément des captures → l'île

| Dans refEH1 / refEH2 | Dans la carte | Module (fonction) |
|---|---|---|
| Pelouse verte en damier de deux verts, à studs | **Sol holographique** : dalles `sol_vert` à studs + **grille de lignes blanc menthe** d'1 stud au pas de 8 (lignes en relief à studs). Pas de damier sous la grille (STYLE § 5.1) | carte.py |
| Trottoir intérieur gris clair | **Pavé clair** `dalle_labo` (lavande très pâle) à studs, 0,4 au-dessus de la pelouse, **bordure rayée rouge et blanc** côté route | carte.py |
| Route sombre, ligne médiane en tirets, flèches blanches, passage piéton sur la route est | **Voie des navettes** `voie` (indigo) à studs, mêmes largeurs et marquages blancs : tirets 1 × 6 tous les 16, lignes de rive, flèches (voie intérieure antihoraire), 4 passages piétons (z = ±134 sur les routes est et ouest) | carte.py |
| Trottoir extérieur gris clair | Même pavé clair, bordure rayée côté route, lampadaires-soucoupes, jardinières à haie et palmier contre les façades, bancs | carte.py + mobilier.py |
| Couronne de gratte-ciel sombres à fenêtres allumées et néons rouges/bleus (≥ 200 de haut, hors cadre) | **Couronne de la ville-jouet** : front de rue continu de boutiques, kiosques, tambours et fusées (16-58) ; derrière, 32 tours rondes et de formes (75-245) ; 4 repères d'angle (230-250) ; 3 repères de milieu de côté ; couleurs par côté | tours_rondes.py, tours_formes.py |
| Grand écran vert au sommet de la façade nord (vue lointaine) | **La fenêtre de l'œuf** : au milieu du côté nord, rien au-dessus de 80 sur |x| < 70, encadré par deux tours de 245 et 240 ; au-dessus, le nuage et l'œuf | plan.py, ciel.py |
| Tapis roulant noir à chevrons blancs, bordures grises à liserés blancs | **Tapis de transfert** : bande `bleu_nuit` à studs en léger creux, **chevrons blancs** dans le sens du flux tous les 8,5, bordures `blanc_labo` à studs avec un fin liseré Neon `cyan` côté bande ; aucune arche au-dessus (caméra) | tapis.py |
| Deux grandes portes rouge sombre à sommets bleu-violet aux têtes nord des voies | **Deux portails** d'anneaux sur colonnes rayées, cœur lumineux où les objets apparaissent (ouest, `neon_violet`) et disparaissent (est, `cyan`) | tapis.py (`portail`) |
| Stand « VENDRE » à auvent rayé rouge et blanc sur socle de pierre | **Kiosque de vente rond** à toit-dôme et lambrequin rayé rouge et blanc, comptoir en arc vers le nord, pièce d'or géante au sommet, sur un socle 28 × 28 ; **demi-disque en pointillés** au nord (zone de vente) ; aucun texte | centre.py (`stand_vente`) |
| « DOMAIN MACHINE » : deux piliers rayés à boules sur socle bleu marine | **Machine à bulle du labo** : deux pylônes rayés `bleu_nuit`/`blanc_labo` à boules Neon, bulle de verre à cœur `neon_violet`, anneau orbital d'or | centre.py (`machine`) |
| Sanctuaire rouge à crânes, toit noir (PNJ des quêtes) | **Monument de l'œuf** : plateau de disques turquoise, réplique de l'œuf fêlé, anneau de données et petits cubes (rime avec l'œuf du ciel) | centre.py (`monument`) |
| Étiquette « Quêtes à durée limitée » au-dessus du sanctuaire | **Panneau holographique** sans texte sur mât fin, devant le monument (repère `Quetes`) ; le texte reste à l'interface du jeu | centre.py (`panneau_quetes`) |
| Socle octogonal + statue géante « meilleure unité du serveur » | **Podium octogonal** Ø 36 à anneau lumineux ; **centre de Ø 20 laissé libre** pour la statue du jeu (repère `Vitrine`) | centre.py (`vitrine`) |
| Parcelles des joueurs (dalles gris foncé, bords rayés, 2 × 4 emplacements, escaliers, collecteurs, arbres) | **Non construites** : pelouse quadrillée, repères `Parcelle_*` et `Entree_*`, et (facultatif) **traces au sol** : coins dorés et bord blanc de la zone d'escalier | carte.py (`TracesParcelles`) |
| Pilier orange sur E1 (et poutre à l'ouest) ; pastilles blanches « meilleure unité » devant les parcelles | Éléments des bases des joueurs : **non construits** | — |
| Arbres low-poly sur la pelouse et le trottoir est | **Palmiers à cocos** (groupes de 1 à 3) en jardinières rondes à bordure rayée et haies en boules | mobilier.py |
| Lampadaire bleu sur le trottoir sud | **Lampadaires à écran** (trottoir intérieur, écran vers la pelouse) et **lampadaires-soucoupes** (trottoir extérieur) tous les 64 | mobilier.py |
| Ciel de nuit (invisible dans les captures) | **Plein midi tropical** ; l'œuf sur son nuage (au-delà de la couronne nord), 18 nacelles en files, 3 lignes de pièces d'or, 6 tubes de verre entre les tours, un dirigeable en forme de baleine, 3 cumulus | ciel.py, carte.py |
| Interface (Sell / Home / Plaza, Shop, Inventory, Index, Rewards, Upgrades, argent, dés, bonus, bannière « token », étiquettes « Plot », « Production ») | Interface du jeu : **rien dans la carte** | — |

## 3. Composition

### 3.1 La couronne (un côté = une famille de couleurs)

Trois profondeurs, de la rue vers l'extérieur :
- **Rang 1, front de rue** (d = 0 à 17 au plus devant une tour, 34 dans une baie) : un ruban **continu** de boutiques à
  arche (K01), kiosques (arcade K03, paire de tambours K07, dôme K04, boutons K02), tambours à hublots (T16) et
  fusées (T11), reliés par des **connecteurs bas** (arcades, murs rayés, vitrines, portiques, 14-20 de haut) :
  intervalles jointifs qui couvrent exactement chaque côté (vérifié). Hauteurs 16-30, fusées et tambours 36-58.
- **Rang 2, la ligne des tours** (axe à d = 50, Ø ≤ 58 au sol) : 7 à 9 tours par côté, tous les 80 (70 au nord),
  hauteurs alternées 115-245. Les repères de milieu de côté avancent jusqu'à la rue (d = 26-28), leurs ailes basses
  ferment le trottoir.
- **Coins** (carré de 80 × 80) : un grand repère de 230-250, avant tourné vers le centre ; parvis planté de palmiers.
- **Mur de fond** continu (2 × 36 de haut, pâle) au bord extérieur : filet de sécurité. Sans lui, 1 % des rayons à
  hauteur d'œil (pelouse et trottoirs, 90 000 rayons) passent entre deux bâtiments ; avec lui, aucun.

| Côté | Famille | Rang 2 (s → tour, hauteur) | Repère |
|---|---|---|---|
| **Nord** (sous l'œuf), s = x | violet, lavande, rose, magenta ; accents turquoise, citron | -240 bulbe violet 130 · -170 champignon menthe 165 · **-100 galettes bonbon 245** · **0 plateau à disques turquoise 75** · **100 bourrelets violets 240** · 170 damier raisin 165 · 240 soucoupe neige 150 | la **fenêtre de l'œuf** (|x| < 70, ≤ 80) encadrée par les deux tours de 245 / 240 ; galerie basse de 78 sur l'axe |
| **Est** (soleil), s = z | orange, jaune d'or, citron, rouge ; accents bleu roi, turquoise | -320 galettes soleil 200 · -240 bourrelets lagon 150 · -160 cône à étoile rouge 130 · -80 bureaux orange 180 · **0 tour-manette 195** · 80 soucoupe coucher 160 · 160 tête-boule lagune 150 · 240 damier citron-pomme 170 · 320 galettes marine 190 | **tour à enseigne-manette violette** (tambour turquoise), face à la pelouse |
| **Sud** (bonbon), s = x | rose, magenta, rouge et blanc, crème ; accents turquoise, lime | -240 tête-boule sucre d'orge 150 · -160 bulbe rose 115 · -80 bureaux violet-rose 175 · **0 bouteille à damier fraise 215** · 80 champignon bonbon 170 · 160 tour à anneau lavande 125 · 240 cône à étoile violet 140 | **bouteille à damier rouge et blanc** |
| **Ouest** (lagon), s = z | turquoise, bleu roi, blanc, lime ; accents orange, jaune | -320 soucoupe EH4 170 · -240 bulbe turquoise 115 · -160 galettes lagon 210 · -80 tour à anneau rouge 125 · **0 cône rayé à tête-boule « phare » 215** · 80 bureaux bleu nuit 185 · 160 champignon lagon 170 · 240 disques à liserés indigo 150 · 320 cône à étoile turquoise 135 | **cône rayé bleu nuit et citron à tête-boule** |
| **Coins** | transitions | **NE** champignon géant à ruban (orange, colonne lavande → citron, chapeau prune) 250 · **NO** tour en pneus bleu roi et turquoise 240 · **SE** tour en pneus orange « rouille » 230 · **SO** tour-soucoupe fraise 230 | les plus hautes, visibles de partout |

Règles tenues par la liste : jamais deux dominantes identiques côte à côte, un très saturé entre deux calmes, jamais
le même archétype face à face d'un côté à l'autre, hauteurs qui alternent (bas 16-30 / moyen 36-75 / haut 115-250),
fronts de rue sans trou. Six **tubes de verre** relient des tours entre 70 et 150 de haut (deux géants à épais
anneaux jaunes, quatre fins à anneaux d'or hexagonaux, dont deux qui coupent les coins NE et SE au-dessus des rues) ;
les tours reliées gardent un **quai** (fût nu entre deux bagues) à la hauteur du tube.

### 3.2 Le repère du ciel : l'œuf fêlé sur son cumulus

- Axe du tapis prolongé : œuf en **(0, -900)**, pied de la coquille à **y 290**, échelle **k = 1,6** (coquille 240 × 320,
  nuage ≈ 610 × 150 × 480, bas du nuage y ≈ 202, dessus y ≈ 354, sommet de l'œuf y ≈ 610), cassure tournée vers la
  carte ; câble du dessous du nuage jusqu'à une station d'ancrage derrière la couronne nord (-80, -560).
- **Depuis l'apparition** (œil à 8, regard vers le nord) : nuage de 10° à 17° au-dessus de l'horizon, œuf de 17° à
  28,5°, demi-largeur 6,2° ; la réplique de l'œuf du monument, au premier plan, monte à 18° (13,7° depuis la caméra
  Roblox, plus haute et 12,5 en arrière) : le petit œuf devant, le grand au-dessus. La fenêtre laisse 6,5-6,8° de
  chaque côté et ses deux tours montent à 21° : l'œuf est cadré par elles et les dépasse. **Depuis le centre** :
  nuage 12-21°, œuf 21-34°, les tours de la fenêtre à 29° : il les domine. Maquette en volumes vérifiée :
  `/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/eh/conception/apercus/maquette-b.png` (avant ce rehaussement de 40).
- **Dans les deux captures**, comme dans la référence, le haut du cadre est rempli de tours et l'œuf est hors cadre :
  `capture1` montre tout juste le bas du nuage dans la fenêtre (bord haut de l'image) ; `capture2` montre le nuage en
  haut à droite (y < 117 px sur 1050) au-dessus des tours nord. Maquette en volumes de capture1 :
  `/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/eh/conception/apercus/maquette-a.png`. La vue `ciel` (et la vue `joueur`) montrent l'œuf entier.
- Couches du ciel (STYLE § 6.1) : nacelles en files au-dessus des routes est (55-61) et ouest (64-68), trio devant la
  fenêtre (120-128), couche haute (165-210) ; pièces d'or en lignes au-dessus du trottoir ouest (66-82), de la marge
  nord (100-125) et de la route est (82-90) ; dirigeable-baleine au-delà de la couronne sud (235) ; cumulus lointains.

### 3.3 Le sol

Pelouse `sol_vert` à studs + grille `sol_ligne` (1 stud, pas de 8, lignes en relief : 0,15 le long de Z, 0,20 le
long de X) ; trottoirs `dalle_labo` à 0,4 ; bordures rayées rouge et blanc (4 + 4) côté route ; route `voie` à 0 et
marquages blancs ; sol de la couronne `sol_vert_clair` à 0,4 (parvis d'angle). Aucun Neon au sol, aucun gris.

### 3.4 Le tapis et les pièces du centre

Le tapis suit exactement l'axe et les polygones du plan (voies droites, deux facettes par côté, bande sud) ; flux
de la tête ouest vers le sud, demi-tour d'ouest en est, remontée à l'est. Dans le U, du sud au nord : stand de
vente (avant au nord, zone de vente en demi-disque) et machine ; l'apparition (plaque dorée) ; le panneau des quêtes
devant le monument de l'œuf (avant au sud) ; le podium (avant au sud, centre libre) ; au nord, les deux portails.

### 3.5 Ce qui reste VIDE et comment on le voit

- Les **8 parcelles** (111 × 105) et leurs **zones d'escalier** (15 × 55 côté tapis) : seulement la pelouse et sa
  grille, les repères `Parcelle_*` / `Entree_*` (invisibles), et le groupe facultatif `TracesParcelles` (équerres
  dorées aux quatre coins de chaque parcelle, bord blanc de la zone d'escalier, au ras du sol : supprimable).
- Les **allées** entre le tapis et les parcelles (|x| 56,5 → 80) : rien de solide. Les écarts entre rangées : un
  lampadaire au bout extérieur, rien qui barre le passage.
- Le **centre du podium** (Ø 20) : libre pour la statue du jeu. La **zone de vente** : un tracé au sol seulement.
- **Au-dessus** des zones praticables : rien de large entre 5 et 40 (caméra) ; tubes ≥ 70, nacelles ≥ 55.

## 4. Hauteurs

| Couche | Hauteur |
|---|---|
| Sol, marquages, bordures | 0 → 0,6 |
| Mobilier (bancs, potelets, feux, lampadaires, palmiers) | 1 → 30 |
| Pièces du centre | podium 2,5 · stand 18 · machine 15 · panneau 16 · monument 32 · portails 36 |
| Rang 1 de la couronne | connecteurs 14-20 · boutiques et kiosques 16-28 · tambours 36-44 · fusées 46-58 |
| Rang 2 | 115-245 ; fenêtre de l'œuf ≤ 80 |
| Repères de milieu de côté / d'angle | 195-215 / 230-250 |
| Tubes, nacelles, pièces d'or | 55-210 |
| Œuf et nuage | 202 → 610 |

## 5. Budget (plafonds par module ; carte entière ≤ 24 000 pièces, ≤ 1 500 Neon, ≤ 400 transparentes)

| Module | Plafond pièces | Neon | Transp. | Estimation au plafond par appel |
|---|---|---|---|---|
| carte.py (sol, grille, routes, trottoirs, bordures, marquages, mur de fond, repères, traces, tubes) | 2 600 | 40 | 60 | ≈ 1 400 |
| assets/tours_rondes.py (45 poses) | 4 400 | 400 | 40 | ≈ 3 750 |
| assets/tours_formes.py (116 poses dont 65 connecteurs) | 5 200 | 450 | 30 | ≈ 4 950 |
| assets/ciel.py | 1 300 | 220 | 60 | ≈ 770 |
| assets/tapis.py + assets/centre.py | 1 400 | 160 | 12 | ≈ 1 040 |
| assets/mobilier.py (203 poses) | 4 600 | 220 | 30 | ≈ 4 470 |
| **Total** | **19 500** | **1 490** | **232** | **≈ 16 400** |

La marge (≈ 4 500 pièces) sert à la finition (détails ajoutés après les critiques). Plafonds par appel :
`plan.BUDGET_FONCTION` ; `carte.py` mesure chaque pose et liste les dépassements.

## 6. Vues de rendu (`plan.VUES`, reprises par `carte.VUES`)

| Vue | Caméra → cible, champ vertical | But |
|---|---|---|
| `capture1` | (2,03 ; 66,1 ; 319) → (-2,06 ; 18,23 ; 231,29), 70,6° ; **2000 × 1077** (ou 1000 × 539) | reproduire refEH1 : les formes doivent coïncider (tapis, stand, machine, parcelles, couronne) |
| `capture2` | (156,2 ; 52,7 ; 361,3) → (112,97 ; 16,7 ; 278,62), 69,3° ; **2000 × 1050** (ou 1000 × 525) | reproduire refEH2 |
| `aerienne`, `plan` | calculées par rendu.py sur l'emprise | vue d'ensemble, contrôle du plan |
| `aerienne_sud` | (420, 520, 980) → (0, 40, -60), 48° | la carte et l'œuf derrière |
| `joueur` | (-3, 8, 219) → (-3, 5,5, 206,5), 70° | ce que voit un joueur à l'apparition |
| `ciel` | (-3, 6, 215) → (0, 230, -900), 62° | l'œuf dans la fenêtre, au-dessus des tours |
| `oeuf` | (0, 30, -250) → (0, 400, -900), 46° | l'œuf de près (contrôle de la recette) |
| `rue` | (262, 7, 150) → (264, 30, -60), 66° | le trottoir est et le front de rue |
| `coin` | (140, 18, -190) → (311, 120, -407), 66° | le repère d'angle NE et son tube |
| `nord` | (0 ; 66,1 ; -319) → (0 ; 18,23 ; -231,3), 70,6° | le pendant de capture1, vers le sud |
| `centre` | (32, 34, 292) → (-4, 6, 170), 60° | stand, machine, monument, podium |

## 7. Propriété intellectuelle

Voir `CONVENTIONS.md` § 8 et STYLE.md § 7 : aucun texte (même « VENDRE » : le jeu l'affiche), aucun nom de la
licence, aucun personnage ni robot ni statue, aucune marque ; l'œuf fêlé sur un nuage, les tours rondes, les cônes
rayés, les nacelles et les tubes sont des formes génériques recomposées dans notre propre plan.

## 8. Décisions et points ouverts

- La pièce des quêtes est **devant le monument** (le PNJ des quêtes de la référence était au sanctuaire, son étiquette
  flotte juste au-dessus) et non vers (0, 10) : à déplacer dans `plan.CENTRE["Quetes"]` si le jeu la veut ailleurs.
- Aucun texte, même « VENDRE » (la bible l'exclut ; l'interface du jeu l'affiche).
- Trottoirs en pavé clair `dalle_labo` (lecture des bandes de la référence) plutôt qu'en terrasse vert clair ; le sol
  de la couronne est vert clair.
- Œuf à k = 1,6 (au-delà du 0,8-1,3 de la bible) pour dominer des tours de 240-250 ; sa fenêtre est réglée par
  `plan.FENETRE_OEUF`.
- Si `plan/LAYOUT.md` (analyse finale) arrive, ses cotes remplacent celles de l'analyste A dans `plan.py` (bandes,
  tapis, parcelles, pièces du centre) ; la couronne suit (elle se calcule depuis la ligne des façades).

## 9. Plan final (13/11, plan du juge : `plan/LAYOUT.md`)

Le plan final du juge (fusion des analystes A, B et C, arbitrée sur les captures) remplace les cotes de l'analyste A
dans `plan.py` ; l'origine ne change pas (milieu du tapis et des 8 parcelles). Ce qui change :

1. **Pelouse plus longue au nord** : z de -336 à +301 (410 × 637). Tout l'anneau nord recule de 35 : trottoir
   -336 → -348, route -348 → -384, trottoir extérieur → -402, façades nord à z = -402. Sud, est et ouest inchangés ;
   la carte n'est plus symétrique en Z. Les dalles gardent des bords entiers (trottoirs 12 et 18, route 36 ; le juge
   mesure 12,5 / 36 / 17,5).
2. **Esplanade nord en renfoncement** (|x| < 140, z -402 → -490) : sol `voie` à trois rangées de tirets blancs (aire
   des navettes, comme la place sombre de la référence), deux flancs et un fond à front de rue bas tourné vers elle
   (galerie de l'axe au centre du fond), deux palmiers au pied du laboratoire. Derrière le fond (z -540) : les deux
   tours qui cadrent l'œuf (x = ±102 ; 245 et 240) et le plateau à disques (75). L'esplanade devient la fenêtre de
   l'œuf : aucun bâtiment au-dessus de 80 dans |x| < 70 (vérifié). Le bâtiment à écran géant de la référence
   (≈ 220 de haut) n'est pas copié en hauteur : l'œuf, au-dessus, tient ce rôle.
3. **Couronne régénérée** (173 emplacements au lieu de 161) : côtés est et ouest allongés de 35 au nord (un kiosque,
   un connecteur et une tour de plus : bulbe orange à l'est, tour à anneau à l'ouest) ; côté nord en deux tronçons de
   114 (rang 2 : bulbe -240, champignon -182, damier 182 ramené à 130 pour laisser passer le tube du coin NE à 150,
   soucoupe 240) ; nouveaux côtés `fond`, `flanc_ouest`, `flanc_est` (ids `F-…`, `FO-…`, `FE-…`) ; repères d'angle
   nord en z -442 ; mur de fond qui suit le décrochement (couronne du fond jusqu'à z -572 pour |x| ≤ 160).
4. **Tapis** : axes à ±48,5, bords ±40,5 / ±56,5, bande de 16 (3 + 10 + 3), chevrons tous les 8 ; demi-tour sud
   inchangé à 0,1 près. Têtes nord à z -294, embout carré, **sans portail** (rien de haut sur les têtes dans la
   référence) : `plan.PORTAILS` est vide ; zones d'apparition et de disparition en tête de voie (repères
   `Tapis_Debut` / `Tapis_Fin` à z -290).
5. **Dans le U** : les « portails » de A sont **deux kiosques à dôme** en (±29,5 ; -170,5) (`tours_formes.kiosque`,
   dôme, 20 × 20), tournés vers l'axe ; **portail violet** (portique à liseré Neon violet, 10 × 4 × 14) en
   (0 ; -105), face au sud. Stand de vente 28 × 24 en (-16,5 ; 244,5), machine (25 ; 240), monument (0 ; 126),
   podium Ø 38 en (0 ; 35,5), apparition neutre et repère `Spawn` en (0 ; 205).
6. **Parcelles** : centres x ±136, z ±72 et ±216 (pas de 144), plateformes 110 × 102 (|x| 81 → 191), bande d'entrée
   réservée |x| 65 → 81 sur toute la profondeur (repères `Entree_*` de 16 × 102) ; allées libres |x| 56,5 → 81 ; un
   point d'apparition par parcelle en (±62 ; rangée), repères `Apparition_W1…E4` tournés vers leur parcelle.
7. **Décor** : passages piétons à z ±137 ; palmiers aux places des arbres de la référence (un palmier en bac dans
   chaque écart entre rangées vers |x| 170 ; jardinières aux coins de la pelouse et dans la marge arrière, au droit
   des écarts : les palmes ne couvrent pas les parcelles) ; câble de l'œuf ancré en (-80 ; -600), derrière la
   couronne du fond ; tubes `Tube_Nord_Ouest` (N-T-182 → F-T-102) et `Tube_Coin_NE` (F-T102 → E-T-320).
8. **Non construits** : les piliers orange (effets de parcelle), comme prévu.
