# Conception de la zone Jujutsu Kaisen (zone 5) — la ville de nuit pendant l'incident

Cinquième zone du couloir (après Naruto, One Piece, Demon Slayer, Dragon Ball ; avant Bleach).
Thème : une grande ville japonaise inspirée de Shibuya, « de nuit » mais lisible sous le ciel bleu du jeu,
au moment où un incident surnaturel la frappe. Le joueur traverse une rue commerçante, puis un quartier de
tours et d'écrans géants. Il arrive au grand carrefour « scramble », où se trouvent les œufs, puis s'enfonce
dans la zone sinistrée. Il sort sous un immeuble effondré en arche.

Modèle Roblox : `ZoneJujutsuKaisen`. Plan : `zone.py`. Assets : `assets/*.py`.

## 1. Ce que dit la référence actuelle (ref11) et ce qu'on garde

La zone actuelle du jeu (ref11) est une rue de ville très large, à la chaussée bleu-violet. Elle est bordée
de tours bleu foncé à bandes de fenêtres blanches, d'immeubles rouges et blancs et de néons verticaux
(magenta, jaune, cyan). Un monorail la traverse en hauteur. On y trouve aussi de petites boutiques
(ラーメン, 本), des poteaux électriques et des feux. Elle se termine sur un grand bâtiment blanc, qui est le
début de la zone Bleach (ref12).

**À garder :** la chaussée bleu-violet, les tours bleues à rubans blancs, les néons verticaux de couleur,
le train sur viaduc qui enjambe la rue et les petites boutiques à enseignes.
**À corriger :** les volumes sont trop nus et trop répétitifs, il n'y a pas d'échelle humaine (trottoirs,
mobilier), pas de grand moment (carrefour, repère final), et l'histoire de l'« incident » est absente.

Photos montrées par l'utilisateur (pas sur disque) :

- (a) Vue aérienne du carrefour de Shibuya de nuit : foule, écrans géants sur chaque immeuble, néons, gare
  à longue façade vitrée éclairée, larges passages piétons.
- (b) Rue de nuit face à une tour cylindrique à couronne lumineuse, avec de grandes affiches et des
  zébras blancs au sol.
- (c) Rue déserte avec un grand passage piéton, des rideaux métalliques tagués, un trou en cratère dans un
  mur, des enseignes verticales blanches et l'escalier d'une passerelle piétonne.
- (d) Le même carrefour en ruines sous un ciel d'orage : asphalte fissuré, tours de verre abîmées,
  flaques, et une tour cylindrique au loin.

## 2. Recherche : repères visuels génériques d'une ville japonaise (et leur traduction en stud)

| Repère réel (générique) | Traduction « stud » |
|---|---|
| Carrefour « scramble » : passages piétons sur les 4 côtés et en diagonale (X), feux pour tous les piétons à la fois | Peint dans les pixels du sol (`motif_carrefour`) : bandes blanches de 2 studs, X central, coins de trottoir à bandes podotactiles jaunes |
| Passages piétons japonais : grandes bandes blanches parallèles à la circulation, sans lignes latérales ; ligne d'arrêt blanche avant | Bandes 2/2 studs, lignes d'arrêt côté arrivée (circulation à gauche) |
| Ligne médiane jaune double, pointillés blancs, lignes de rive | Bandes de 2 studs dans le sol du couloir |
| Bandes podotactiles jaunes sur les trottoirs | Ligne jaune continue de 2 studs à 4 studs de la bordure |
| Feux horizontaux à 3 lampes (vert bleuté, jaune, rouge) sur potence ; feux piétons verticaux | `mobilier.feu_tricolore` : potence de 6,5 studs qui s'arrête au bord du couloir |
| Poteaux électriques en béton, transformateurs cylindriques, faisceaux de câbles | `mobilier.poteau_electrique` + `mobilier.cable` le long des trottoirs (jamais en travers du couloir) |
| Distributeurs de boissons éclairés, vélos de ville garés, poubelles de tri | `distributeurs`, `velos`, `poubelles_tri` |
| Passerelles piétonnes (hodōkyō) en acier, escaliers raides | `ouvrages.passerelle_pietons` (dessous à 34), escaliers le long des trottoirs |
| Viaduc ferroviaire, boutiques et bars sous les arches (gādo-shita), gare aérienne à quais couverts | `ouvrages.viaduc_ferroviaire` (dessous à 36) + `train_banlieue` |
| Immeubles « crayons » étroits à enseignes empilées, enseignes verticales en drapeau lisibles des deux sens | `batiments.immeuble_boutique` variante 5, `mobilier.enseigne_verticale` |
| Supérette 24 h (façade vitrée, bandeau rayé de couleurs) | `batiments.superette` avec des couleurs **inventées** (aucune enseigne réelle) |
| Grands magasins et tours à écrans géants, néons sur les toits | `batiments.grand_magasin`, `carrefour.immeuble_ecran`, panneaux de toit |
| Tour de mode cylindrique avec couronne lumineuse | `carrefour.tour_cylindrique` (générique : ni nom, ni chiffre, ni logo) |
| Gare à longue façade vitrée éclairée | `carrefour.gare_facade` |
| Rideaux métalliques baissés, tags | Variante 4 de `immeuble_boutique` (taches de couleur abstraites, aucun texte) |
| Ruines : asphalte fissuré, tours de verre éventrées, gravats, voitures abandonnées, barrières 立入禁止 | `incident.*`, fissures peintes au sol avec lueurs violettes (Neon) |
| « Barrière » surnaturelle en dôme sombre | `incident.voile_dome` : dôme en gradins violet nuit translucide, liserés néon (forme générique) |

Sources consultées : [Shibuya Scramble Crossing (Japan Travel)](https://en.japantravel.com/places/japan/shibuya-scramble-crossing/783),
[GO TOKYO – Shibuya Crossing](https://www.gotokyo.org/en/spot/366/index.html),
[Gado-shita, sous les voies (GoWithGuide)](https://gowithguide.com/blog/gado-shita-clever-use-urb-3661),
[Yurakucho, bars sous la Yamanote (kanpai)](https://www.kanpai-japan.com/tokyo/yurakucho),
[Passerelles piétonnes au Japon (structurae)](https://structurae.info/litterature/papier-de-conference/function-and-development-of-pedestrian-bridges-in-japan),
[歩道橋 (kotobank)](https://kotobank.jp/word/歩道橋),
[Néons de Tokyo (nippon.com)](https://www.nippon.com/en/images/i00060/night-in-the-city-capturing-the-fading-age-of-neon-lights-in-tokyo-and-beyond.html),
[Lieux réels de Shibuya dans l'animé (tabimania)](https://tabimaniajapan.com/culture/jujutsu-kaisen-real-life-guide-how-to-visit-shibuya-incident).
Ces liens servent seulement à comprendre la ville réelle. On n'en reprend aucune image, aucun nom de
magasin et aucun logo.

## 3. Dimensions

| Élément | Valeur | Constante de `zone.py` |
|---|---|---|
| Couloir de course (vide) | 64 de large, x ∈ [-32, 32] | `DEMI_COULOIR` |
| Rien au-dessus du couloir sous 30 studs | sur \|x\| < 33 | `X_LIBRE_HAUT` |
| Dessous des ouvrages qui l'enjambent | viaduc 36 ; passerelles et immeuble effondré 34 | `H_VIADUC`, `H_LIBRE` |
| Trottoirs | \|x\| de 32 à 42 (bordure, bande foncée, bande podotactile jaune, dalles) | `X_FACADE` |
| Seconde rangée, tours de fond, bord du sol | \|x\| = 84, 136, 242 | `X_SECOND`, `X_SKYLINE`, `X_FOND` |
| Entrée → sortie | z = 0 → z = -496 | `Z_PORTE`, `Z_SORTIE` |
| Place des œufs (carrefour) | cercle de rayon 34, centre z = -400 (81 %) | `Z_PLACE`, `R_PLACE` |
| Carré peint du carrefour | \|x\| ≤ 46, z ∈ [-446, -354] | `X_CARREFOUR` |
| Sol d'approche (côté apparition) | z de 0 à +32 (groupe `Sol/Approche`, peut être supprimé) | `Z_APPROCHE` |

## 4. Séquence, de l'entrée à la sortie

Le joueur arrive par +Z et court vers -Z, puis revient : les deux sens de lecture comptent.

### 1. Entrée : le viaduc et la gare aérienne (z +32 → -12)
- **Repère** : un viaduc ferroviaire en béton et poutres d'acier bleues traverse toute la largeur de la
  zone en z = 0 (dessous à 36 studs, rails à 42). Un train de banlieue argenté à bandes violette et cyan
  (livrée inventée) sort de la gare aérienne (quais couverts en x ∈ [-150, -50]) et passe au-dessus de la
  rue. Sur la poutre au-dessus du couloir, une grande plaque de gare porte 渋谷, sur les deux faces. C'est
  le seul emploi de ce nom de lieu.
- Sous les arches, de part et d'autre (\|x\| ≥ 44), des petites boutiques éclairées (gādo-shita) :
  ラーメン, 寿司, 喫茶. On voit aussi l'entrée de la gare avec un panneau 駅.
- **Vue joueur** : en arrivant, on voit le viaduc, le train au-dessus de soi, puis toute la rue
  commerçante en enfilade, la passerelle 1 au loin et le sommet des tours.

### 2. La rue commerçante (z -12 → -150)
- Petits immeubles de 3 à 8 étages, façades variées : carrelage blanc, bleu ardoise, brique, violet nuit.
  On y trouve un restaurant de ramen (lampions, noren), une librairie, une pharmacie, deux karaokés, un
  cinéma, des supérettes, un restaurant de sushi aux rideaux métalliques tagués et des immeubles
  « crayons » à enseignes empilées. Partout, des **enseignes verticales au néon** en drapeau.
- Poteaux électriques et câbles le long des trottoirs, distributeurs, vélos, poubelles de tri.
- **Moment** : le petit carrefour en z = -92 (rue transversale de 16 studs, deux passages piétons,
  quatre feux).
- **Moment** : on passe sous la **passerelle piétonne 1** (z = -150). Son escalier longe le trottoir
  gauche.

### 3. Le quartier des tours et des écrans (z -156 → -296)
- Grandes tours de bureaux (80 à 124 studs) à rubans de fenêtres blancs ou bleus, grilles de verre,
  bandes de néon aux angles et feux rouges d'obstacle sur les toits. Deux **grands magasins à écrans
  géants**, avec écran magenta et écran cyan. La seconde rangée et les tours de fond ferment l'horizon.
- Lampadaires, arbres d'alignement (dont un ginkgo jaune), garde-corps blancs le long de la bordure.
- **Moment** : la **passerelle 2** (z = -300) encadre la vue sur le carrefour.

### 4. L'approche du carrefour (z -300 → -354)
- **Repère** : à droite, la **tour cylindrique** (rayon 22, 76 studs) à affiches verticales, avec ses
  anneaux lumineux et sa couronne qui brille. Elle a un petit parvis planté d'arbres et de bancs. À gauche,
  l'**immeuble à écrans** du coin : écrans géants sur deux faces et bandeau défilant.

### 5. Le grand carrefour « scramble » = place des œufs (z -354 → -446, centre -400)
- Carré peint de 92 × 92 studs : quatre passages piétons sur les côtés et deux en diagonale (X). La
  grande rue transversale part à gauche et à droite et finit contre les dômes.
- Coins : la tour cylindrique (nord-est), l'immeuble à écrans (nord-ouest), la **gare** à longue façade
  vitrée éclairée (sud-ouest, 駅 / 東口) et une tour de verre déjà fissurée (sud-est). Huit feux tricolores.
- **Vue joueur** : un grand espace ouvert après la rue étroite. Au fond, l'arche de l'immeuble effondré
  et les dômes violets.

### 6. L'incident (z -446 → -474)
- L'asphalte se fissure : les lignes sont sombres et des pixels violets brillent (matériau Neon). Les
  marquages s'effacent, les trottoirs sont salis. Il y a des gravats, des voitures abandonnées, des
  barrières et des cônes 立入禁止 (toujours hors du couloir), la tour de verre éventrée et sa voisine.
- **Repère de fond** : deux **dômes de barrière** violet nuit en gradins, translucides, à liserés de
  néon. Le grand dôme (rayon 72) se dresse à gauche, derrière la gare. Le petit dôme (rayon 48) est à
  droite. La rue transversale vient buter contre eux.

### 7. La sortie : l'immeuble effondré (z -474 → -496)
- **Repère final** : deux moignons de tours (\|x\| de 42 à 100) et, coincé entre eux, le haut d'une tour
  tombé en travers, légèrement incliné. Il forme une **arche brisée** au-dessus du couloir, dont le dessous
  reste à 34 studs ou plus. On voit des planchers à nu, des fers tordus, du verre brisé, des lueurs
  violettes dans les fissures et des tas de gravats au pied des moignons.
- Le couloir passe dessous et continue vers la zone Bleach (z = -496). En revenant, la vue retour montre
  toute la rue jusqu'au viaduc, avec la passerelle 2 et les écrans.

## 5. Palette (`palette.py`)

- **Sol** : chaussée bleu-gris `asphalte` #3D4363 (comme le jeu, en plus lisible), carrefour
  `asphalte_place`, marquages blanc `marquage` et jaune `marquage_jaune`. Trottoirs gris bleuté clairs,
  bande podotactile jaune `guidage`.
- **Façades** : bleus nuit, marine, ardoise, acier et pâle ; béton clair, carrelage blanc, crème ; brique,
  bordeaux, violet nuit. Jamais de noir pur : les bâtiments doivent rester lisibles en plein jour.
- **Lumières** (matériau Neon) : fenêtres chaudes #FFD27A et froides #DCE9FF, néons magenta, cyan,
  jaune, orange, rouge, violet, bleu, et un vert vif **ponctuel seulement**. Écrans : fond #151B36 avec
  aplats bleu, violet, rose et orange.
- **Incident** : gravats gris, fissures #1B1C28, lueurs `lueur_violette` #9B4DFF, `lueur_bleue`, dômes
  `voile` #2A1748 → `voile_clair` #4E2D84, liserés `voile_bord` #8A4DFF, verre brisé translucide.
- **Règle de dosage** : 70 % de bleus et de gris, 20 % de clairs (béton, carrelage, zébras), 10 % de
  néons. Le violet est réservé à l'incident, pour qu'il « monte » vers la fin de la zone.

## 6. Propriété intellectuelle (obligatoire)

Roblox retire les contenus sous licence non autorisés. On ne garde donc que des éléments de ville
japonaise génériques.

- **Aucun nom** de la licence, de l'école ou des personnages, nulle part : ni dans les noms de pièces ou
  de groupes, ni dans les textes, le titre, la miniature ou le nom affiché de la zone. Le nom technique
  `ZoneJujutsuKaisen` reste interne. Pour le nom affiché dans le jeu, préférer « Ville de nuit » ou
  « Shibuya, la nuit ».
- **Interdits** : 呪術, 高専, 帳 et tout terme de la série ; aucun personnage, aucune silhouette ou statue
  de personnage ; aucun doigt maudit, aucun objet maudit précis ; aucun symbole, marque, tatouage ou geste
  de personnage ; aucun motif d'uniforme ; aucune copie de « domaine » (sanctuaire, ciel étoilé…).
- **Pas de marques réelles** : pas de « 109 » ni de forme de logo sur la tour cylindrique, pas de nom de
  magasin, de chaîne de supérettes, de compagnie ferroviaire ou de ligne. Pas de livrée réelle sur le
  train (pas de bande vert-jaune) et pas de publicité de marque sur les écrans, qui ne montrent que des
  aplats abstraits ou des mots génériques. Pas de statue Hachikō.
- **Textes autorisés** : ラーメン, 本, 薬, コンビニ, カラオケ, 映画, 寿司, 喫茶, 百貨店, 駅, 東口, 西口,
  出口, 止まれ, 立入禁止, 24H. 渋谷 n'apparaît **qu'une fois**, sur la plaque du viaduc. Pas d'alcool
  (pas de 居酒屋 ni de 酒).
- Le dôme de barrière est une forme générique (dôme sombre à gradins) : aucun texte, aucun motif
  reconnaissable dessus.
