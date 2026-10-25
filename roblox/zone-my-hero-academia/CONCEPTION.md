# Conception : zone My Hero Academia, « l'académie des héros et sa ville »

Huitième et dernière zone du couloir. Le joueur arrive vite de la zone précédente. Il traverse une rue de
ville moderne et passe sous un viaduc de train. Il franchit le grand portail de sécurité d'une académie
futuriste et remonte l'avenue du campus. Il longe les terrains d'entraînement et le dôme de verre, puis prend son
œuf dans l'arène du stade. Les **tours jumelles de verre bleu-violet** ferment la perspective : on sort sous leur
passerelle, au bout de la carte.

**Route du milieu très large (demande de l'utilisateur)** : le couloir vide fait **90 studs** (`|x| < 45`),
contre 60 à 64 dans les autres zones. Avec les trottoirs (`|x|` de 45 à 55), le sol praticable fait **110 studs**.
Toutes les ouvertures sont plus larges que la route : portail 100, stade 104, passage des tours 116. Longueur : **574
studs** de l'entrée (z = 0) à la sortie (z = -574).

## 1. Ce qu'on garde des références, et ce qu'on corrige

| Source | À reprendre | À éviter |
|---|---|---|
| `refMHA1.png` (l'école au couchant) | **Deux tours de verre bleu-violet** à quadrillage clair, reliées par une **passerelle**. Devant, un **long mur d'enceinte** de panneaux gris clair tachés entre des piles de brique, avec un **portail high-tech** bleu nuit. Arbres et conifères qui dépassent du mur, ciel orangé | Les lettres et l'emblème sur le portail ; la silhouette exacte en « H » vue de face |
| `refMHA2.png` (l'avenue au crépuscule violet) | **Avenue très large** de dalles pâles. **Haies taillées** et rangée dense de **conifères en colonnes** à gauche, **dortoirs de brique rouge à balcons blancs et toits sombres** en enfilade, masse d'arbres ronds à droite, tours au fond | Rien |
| `refMHA3.png` (planche) | Grand escalier, couloir vitré, halle d'entraînement à **verrière**, **dôme de verre géant** avec une **montagne rocheuse artificielle**, un **bâtiment rouge en dôme**, des arbres et des allées | Les intérieurs (couloir à portes vertes) : on n'en garde que les couleurs |
| Rue de la ville (montrée par l'utilisateur) | **Trottoirs roses**, boutiques à vitrines et enseignes, **bureaux blancs et bleu ciel**, chaussée à voitures garées, ciel bleu vif | Personnages, enseignes de la licence |

**Recherche** (éléments génériques réels, réutilisables sans licence) :
- **Tours jumelles reliées en hauteur** : l'Umeda Sky Building d'Osaka est formé de deux tours de 40 étages reliées
  à leur sommet par des passerelles vitrées ; on retrouve la même idée aux tours Petronas. Notre repère final
  reste donc une **paire de tours de bureaux vitrées** générique : deux hauteurs, deux volumes décalés par tour,
  une passerelle basse au-dessus de la route et une plus fine plus haut.
- **Rue japonaise moderne** : larges chaussées marquées de blanc, ligne médiane jaune, **passages piétons à
  bandes**, trottoirs en pavés colorés avec une **bande podotactile jaune** (*tenji block*, inventée au Japon en
  1965 et généralisée depuis). On y voit aussi des distributeurs de boissons alignés, des abribus vitrés, des
  feux à potence, des arbres d'alignement en fosse carrée et des **poteaux électriques** de béton dans les rues
  secondaires. On y ajoute un **viaduc ferroviaire** urbain avec un train de banlieue blanc à bandes.
- **Campus japonais** : longues avenues de dalles, haies de buis, conifères taillés, résidences de brique,
  bâtiments de cours en béton blanc à grandes baies vitrées, gymnase à verrière, stade d'athlétisme.
- **Héroïque et futuriste** sans licence : verre bleu-violet, acier bleu nuit, **bandes lumineuses cyan**,
  robots d'entraînement **originaux** (cubiques, un seul œil rond), ville factice à demi détruite pour
  l'entraînement, dôme de verre sur anneau.

**En stud** : grands aplats de verre en 2-3 tons (`vitre_violette`, `vitre_violette_claire`, bandes de reflet
`vitre_reflet`). Des montants blancs en saillie de 0,2 dessinent le quadrillage. Béton blanc en « pixels » de
2-3 blancs proches, brique en 3 rouges. Toits et dalles studdés, néons fins (matériau `Neon`). Les silhouettes
doivent se lire de loin : tours verticales, portail massif, stade bas et large, dôme rond.

## 2. Séquence de la course (entrée → sortie)

| z | Moment | Repère | Vue à hauteur de joueur |
|---|---|---|---|
| +24 → 0 | **Approche** | Fin de la zone précédente. Abribus, jardinières, arbres d'alignement | La rue de 110 studs s'ouvre d'un coup, le viaduc la barre à 36 studs de haut |
| 0 → -26 | **Sous le viaduc** (z = -18) | **Viaduc ferroviaire** en béton clair qui traverse toute la zone. Tablier à 36 studs, piles hors de `|x| < 56`, **train de banlieue blanc à bandes bleues et violettes** arrêté au-dessus de la route, liseré lumineux sous le tablier | Effet de seuil urbain. Par-dessous, on voit la rue, les bureaux et, au fond, le portail |
| -26 → -122 | **Rue de la ville** | Dix **boutiques vitrées** (CAFÉ, FLEURS, LIVRES, MARCHÉ, RAMEN, BOULANGERIE, SPORT, PHARMACIE), une supérette d'un étage, auvents. Derrière, **8 tours de bureaux** blanches et bleu ciel (50-92). **Carrefour** en z = -66, avec des rues latérales, des voitures garées, des feux et des lignes électriques. Chaussée bleu-gris à ligne jaune, passages piétons, trottoirs roses à bande jaune | Rue japonaise moderne, lumineuse et très large, le portail high-tech en point de fuite |
| -124 → -140 | **Portail de sécurité** (z = -132) | Deux **pylônes d'acier bleu nuit et de verre** (48 de haut) à bandes cyan, linteau au-dessus de 36 studs, guérite vitrée, caméras. Le **mur d'enceinte** (14 de haut, panneaux gris tachés, piles de brique) court jusqu'à `|x| = 185`. Au sol, dalles bleu nuit et deux lignes lumineuses cyan | Passage de 100 studs : on « entre à l'académie » |
| -140 → -296 | **Avenue du campus** | Dallage lavande pâle en quinconce, trottoirs clairs. **Haies taillées** en `|x|` 55-58,5. À gauche, une rangée de **conifères** et **trois dortoirs de brique rouge** à balcons blancs et toits sombres, plus deux en retrait. À droite, des **arbres ronds**, **deux bâtiments de cours** à grandes grilles vitrées (l'un avec un couloir vitré en façade), une **halle d'entraînement à verrière** et un terrain de sport derrière. Lampadaires à bande cyan, bancs, totems CAMPUS, panneau STADE / CAMPUS / DORTOIRS | L'image de la référence 2. Les **tours jumelles** se dressent au fond, au-dessus du toit du stade |
| -296 → -400 | **Terrains d'entraînement** | Dalles de béton et **bandes de danger jaunes et noires** au bord de la route. À gauche, derrière un grillage, une **ville factice** : rues tous les 32 studs, 7 immeubles dont certains à demi détruits, décombres, **robots d'entraînement** originaux, cibles. À droite, le matériel (plots, pneus, haies, sac de frappe) et le **dôme de verre** (rayon 52, 50 de haut) : montagne rocheuse, bâtiment rouge en dôme et arbres à l'intérieur, entrée tournée vers la route | Le dôme brille à droite, les silhouettes cassées des immeubles à gauche |
| -400 → -528 | **Stade et place des œufs** (centre z = -464) | **Stade** de 280 × 128 : tribunes latérales à sièges violet, lavande et bleu, **verrières** sur les tribunes, tribunes basses aux extrémités. **Portiques à écran géant** au-dessus des deux ouvertures (dessous ≥ 38), mâts d'éclairage. Arène : pelouse rayée, **piste d'athlétisme ovale** rouge, **mosaïque d'une étincelle à huit branches** violette et lavande à cœur orangé (rayon 34) au centre. Bornes lumineuses, bannières | On entre sous un écran géant, l'arène s'ouvre, les tours remplissent le ciel derrière le portique de sortie |
| -528 → -536 | **Parvis** | Dalles blanches à filets violets, totems ACADÉMIE, arbres | — |
| -536 → -574 | **Tours jumelles** (repère final) | Deux tours de verre bleu-violet à cadres blancs (120 et 134 de haut), écartées de 116, **passerelle vitrée** au-dessus de la route (dessous à 46) | On passe sous la passerelle : fin de la carte |

**Côtés.** Le mur d'enceinte (`|x| = 185`) ferme le campus, doublé à l'intérieur d'une **ceinture d'arbres** sur
un talus. Au-delà, la **ville lointaine** (silhouettes blanches, bleu ciel et lavande de 44 à 110 de haut, en
`|x| ≈ 218`) rappelle que l'académie est au cœur d'une métropole.

**Retour.** Depuis l'arène, on voit la sortie du stade sous l'écran géant, l'avenue, le portail et la ville.
Les deux faces du portail, du viaduc, des portiques et de la passerelle sont soignées.

## 3. Repère final et sortie

`tours_jumelles` a pour origine le centre de la route au pied de la façade avant des tours (z = -536). Sa grande
façade regarde +Z, vers le joueur qui arrive.
- **Tour gauche** `x ∈ [-102, -58]`, 120 de haut ; **tour droite** `x ∈ [58, 102]`, 134 de haut. Chaque tour a
  deux volumes décalés pour ne pas faire une boîte : grandes nappes de verre bleu-violet, montants blancs tous les
  4-6 studs, lignes d'étage tous les 6, couronne blanche, feux d'obstacle rouges.
- **Socle** : un hall vitré clair sur deux niveaux, des auvents et des bandes cyan.
- **Passerelle** : une boîte vitrée sur 2-3 niveaux, de `x = -58` à `x = 58`, dessous à **46 studs** et liseré lumineux
  dessous. Une seconde passerelle, plus fine et plus haute (≈ 86), dessine la figure des tours reliées.
- **Passage** : `|x| < 58` entièrement libre jusqu'à 46 studs, de z = -536 à z = -574. C'est la fin de la carte :
  la route s'arrête là.

## 4. Palette (`palette.py`)

Dosage : 45 % de blancs et gris clairs, 25 % de verre bleu-violet et de bleus, 20 % de verts, 10 % d'accents.
- **Verre** : `vitre_violette` #7468E3 (tours), `vitre_violette_claire`, `vitre_violette_fonce`, `vitre_bleue`,
  `vitre_ciel`, `vitre_claire`, `vitre_reflet` (bandes de reflet), `vitre_nuit` (intérieurs), `verre_dome`,
  `verre_canopee`, `cadre_blanc`.
- **Béton et acier** : `blanc`, `blanc_casse`, `beton_clair`, `beton`, `beton_fonce`, `acier`, `marine` (acier
  bleu nuit du portail), `marine_clair`, `noir`.
- **Ville** : `asphalte` bleu-gris, `marquage`, `marquage_jaune`, `trottoir_rose*`, `guidage`, façades
  `facade_blanche`, `facade_ciel`, `facade_creme`, `facade_rose`, `carrelage`, auvents `store_*`, voitures
  `voiture_*`, viaduc et train `viaduc*`, `rail`, `train_*`.
- **Campus** : `pave_campus*` (lavande pâle), `dalle*`, `brique*`, `toit_ardoise*`, mur `panneau_mur*`, `chaperon`.
- **Accents** : `violet` #6157F8 (accent principal), `lavande`, `lavande_pale`, `orange_couchant`, `orange`,
  `jaune`, `rouge`, `rouge_dome`, `bleu_vif`. **Néons** : `neon_cyan`, `neon_blanc`, `neon_violet`, `led`.
- **Végétation** : `feuille*`, `conifere*`, `haie*`, `herbe*`, `tronc`, fleurs. Verts francs tirant vers le
  jaune-vert, **jamais d'émeraude dominant**.
- **Entraînement et stade** : `roche*`, `robot_*`, `danger_jaune`, `lentille`, `cible_*`, `piste*`, `arene*`,
  `siege_*`, `beton_tribune`, `ecran_fond`, `ecran_lumiere`.

## 5. Budget de pièces (plafond 13 500)

| Poste | Budget |
|---|---|
| Sol (route, trottoirs, côtés, arène, mosaïque) | 1 340 (mesuré) |
| Mobilier posé (`assets/mobilier.py` : lampadaires, feux, voitures, lignes électriques, bancs, totems…) | 930 (mesuré) |
| `assets/ville.py` (10 boutiques ≤ 100, 8 bureaux ≤ 90 ou 40, viaduc 420, portail et mur avant 700, 30 tronçons de mur ≤ 12, 32 silhouettes ≤ 8) | ≈ 3 240 |
| `assets/campus.py` (5 dortoirs ≤ 160 ou 70, 2 bâtiments de cours ≤ 170, halle 160, tours jumelles 1 300) | ≈ 2 420 |
| `assets/entrainement.py` (stade 1 500, dôme 1 100, 7 immeubles factices ≤ 50, 4 décombres ≤ 16, 6 robots ≤ 40, 5 cibles ≤ 10) | ≈ 3 300 |
| `assets/vegetation.py` (23 arbres ronds ≤ 20, 13 conifères ≤ 8, 12 bosquets ≤ 30, 8 haies, 2 parterres, 2 rochers) | ≈ 1 030 |
| **Total au budget maximal** | **≈ 12 260** (marge ≈ 1 240) |

`python zone.py --stats` contrôle chaque pose (`hors_budget`), le couloir (`couloir_encombre`) et la hauteur
libre (`trop_bas_au_dessus_du_couloir`).

## 6. Propriété intellectuelle (obligatoire)

Roblox retire les contenus qui reprennent une licence sans autorisation. On n'utilise donc **qu'un campus
moderne d'« académie de héros » générique** et sa ville.
- **Aucun nom** : ni la licence, ni l'école, ni la ville, ni les personnages. Pas de « UA » ni de « U.A. », ni en
  texte ni en forme de lettres (portail, façade, sol, bannières). `ZoneMyHeroAcademia` est un nom de fichier
  interne : ne pas l'afficher en jeu.
- **Aucun personnage**, aucune statue de héros, aucune silhouette, aucun costume de héros, pas de cape.
- **Aucun emblème ni logo** : pas de blason d'école, pas d'insigne. La mosaïque est une étincelle géométrique à huit
  rayons, pas un emblème. Les bannières n'ont que des bandes.
- **Aucune réplique d'objet de la série** : les robots sont d'un **dessin original** (cubiques, un œil rond, bandes
  de danger). Pas de robots géants à points, pas de chiffres ni de « 1P / 2P / 3P », pas de robot géant de
  l'examen. Le dôme est un parc d'entraînement générique, sans le nom de l'installation de la série. Le portail
  reste une **barrière de sécurité générique**, sans lettres. Les tours restent des **tours de bureaux vitrées
  génériques**, sans la façade exacte de l'école.
- **Textes permis** sur les enseignes et totems : ACADÉMIE, CAMPUS, ENTRAÎNEMENT, STADE, GYMNASE, DORTOIRS,
  CAFÉ, FLEURS, LIVRES, MARCHÉ, RAMEN, BOULANGERIE, SPORT, PHARMACIE. Pas de marque réelle (supérette sans
  les couleurs d'une enseigne connue).

Sources consultées : [Umeda Sky Building (Wikipedia)](https://en.wikipedia.org/wiki/Umeda_Sky_Building),
[Umeda Sky Building (Japan Experience)](https://www.japan-experience.com/all-about-japan/osaka/attractions-and-excursions/umeda-sky-building),
[Tactile paving (Wikipedia)](https://en.wikipedia.org/wiki/Tactile_paving),
[Tenji blocks (JRPass)](https://www.jrpass.com/blog/tenji-blocks-the-story-behind-japan-s-tactile-paving),
[USJ, homonymies (Wikipedia)](https://en.wikipedia.org/wiki/USJ), plus les trois images de référence fournies.
