# Conception : zone Black Clover, « des confins du royaume aux portes du royaume démoniaque »

Huitième zone du couloir (avant-dernière), après My Hero Academia et avant Attaque des Titans. Le joueur franchit
la porte d'un royaume de mages, traverse ses confins pauvres (champs, village abandonné dominé par un **crâne de
démon cornu**), un bourg serré autour d'une **tour aux grimoires**, un **champ de bataille de mages** sous un
aqueduc en ruine, et prend son œuf au centre d'un **cercle magique** sur une place rituelle noire. Au bout, un
**château démoniaque** gothique ferme l'horizon ; sa porte mène à la zone suivante. Plus on avance, plus tout
devient noir, violet et cramoisi. La zone doit se lire **sombre et démoniaque en plein jour** (l'éclairage Roblox
est le même pour tout le jeu), tout en restant belle et lisible : silhouettes fortes, accents lumineux, contraste
entre l'os ivoire, la pierre noire et les lueurs violettes et cramoisies.

**Couloir de course vide et très large** : `|x| < 45` (90 studs), accotements jusqu'à `|x| = 55`. Longueur : 548
studs de l'entrée (z = 0) à la sortie (z = -548), plus 40 studs d'abords (z 0 → +40, groupe `Abords`).
Modèle Roblox : `ZoneBlackClover` (nom de fichier interne, jamais affiché aux joueurs). Plan : `zone.py`.

## 1. Références de l'utilisateur : ce qu'on garde, ce qu'on évite

| Référence | À reprendre | À éviter ou corriger |
|---|---|---|
| `refBC1` : crâne de démon géant sur une colline | **Crâne cornu ivoire, fissuré**, deux grandes cornes recourbées, petites pointes sur les côtés, **mâchoire à crocs à moitié enterrée** dans une **colline boisée sombre** ; au premier plan des **labours bruns** et du **blé doré**, un village en ruine | Le **troisième orbite** au front et la **statue** posée sur le crâne (signes propres à la licence) : deux orbites seulement, front fissuré, un **étendard cramoisi uni et déchiré** au sommet |
| `refBC2` : chemin entre deux tours | **Deux tours rondes massives** de pierre à **toits coniques pointus** violet-gris, **lierre**, chemin qui passe entre elles, **lucioles dorées** partout, couchant rose-violet, le crâne au loin | Les personnages : aucun |
| `refBC3` : château noir sur la falaise | **Forteresse gothique noire** à flèches aiguës sur une **falaise** escarpée, **arches d'aqueduc brisées**, sapins sombres, lumière d'orage violette | La neige (on garde des falaises noires et des cristaux violets) |
| `refBC4` : champ de bataille de mages | **Murs et tours rondes en ruine**, arches effondrées, **bâtons de mage plantés à orbes lumineux**, **feux de camp**, prairie sombre et brumeuse | Le tapis de trèfles au sol (**aucune forme de trèfle**), l'aurore verte (pas de ciel dans le modèle) |
| `refBC5` : vallée et montagne couronnée d'un château | La **capitale du royaume** comme silhouette lointaine : montagne rocheuse coiffée d'un château clair | Tout le vert de la vallée : nos campagnes sont olive et éteintes |

**Recherche** (repères génériques de cette fantasy sombre et leur traduction en stud) :
- Dans la licence, le village des confins est connu pour le **squelette géant d'un démon** couché juste à l'extérieur,
  et une **tour** garde les grimoires qu'on remet aux jeunes de 15 ans ; un grimoire « sort du mur » de la tour.
  Le crâne y porte une **statue** et un **troisième œil** : on ne reprend ni l'un ni l'autre. Le royaume des démons y
  est relié au nôtre par un grand **arbre** sombre : on n'en garde que l'idée générique d'un arbre noir colossal.
- **Gothique** (château final) : **arc brisé**, **fenêtres lancéolées** (6 à 10 fois plus hautes que larges),
  **contreforts** et arcs-boutants, **pinacles** qui font la transition entre la masse et la **flèche**, gargouilles ;
  dans l'imaginaire, un château gothique est haut, hérissé de tourelles et d'arcs pointus.

| Repère générique | Traduction « stud » |
|---|---|
| Tours rondes à toit conique d'ardoise | Corps en cylindres empilés (ou anneaux de blocs), assises en pixels de 3-4 gris-violet, cordons clairs ; toit conique en anneaux de cylindres qui rétrécissent, très élancé, épi doré ; lierre en plaques de blocs |
| Crâne de démon cornu | Volume en gradins de blocs ivoire (3 tons), noirci au ras du sol ; orbites creusées (blocs sombres en retrait, braise cramoisie au fond) ; cornes en segments de blocs tournés, de plus en plus fins ; crocs en coins ; fissures en saillie de 0,1 |
| Tour aux grimoires | La tour la plus claire du bourg ; hautes baies en arc **lumineuses** (Neon) ; **spirale de livres ouverts en V** (3 pièces par livre) qui monte autour d'elle et sort de ses fenêtres |
| Champ de bataille de mages | Bâtons plantés à **orbes Neon**, épées plantées, cratères **peints dans le sol** avec fissures incandescentes, ruines en pierre noire |
| Château gothique démoniaque | Volumes noirs verticaux, **flèches en gradins** très pointues, arcs brisés en gradins, fenêtres lancéolées **violettes** (Neon), contreforts, falaise en gradins avec **cristaux violets** |
| Arbre du royaume démoniaque | Troncs de blocs noirs **torsadés**, racines arquées qui envahissent la place, branches en griffes, **veines violettes** (Neon) |
| Cercle magique | Estrade de disques concentriques de 0,1 de haut, anneaux Neon, glyphes abstraits, **losange** inscrit (aucune étoile) |

## 2. Séquence de la course (entrée → sortie)

| z | Moment | Repère | Vue à hauteur de joueur (aller vers -Z / retour vers +Z) |
|---|---|---|---|
| +40 → 0 | **Abords** (groupe `Abords`, supprimable) | Vieille route pavée gris-violet, prés sombres, sapins et arbres morts, poteau indicateur VILLAGE / CHÂTEAU, lucioles dorées | **Aller** : les deux tours rondes de la porte encadrent la vue (refBC2) ; entre elles, au loin, le **crâne cornu** sur sa colline à droite, la **tour aux grimoires** à gauche, et tout au fond la **silhouette noire du château** à flèches |
| 0 → -32 | **Porte d'entrée** | Deux **tours rondes** (Ø 26, axes en `|x| = 63`, faces intérieures en `|x| = 50`, corps de 58, mâchicoulis, **toits coniques en aiguille** d'ardoise violette jusqu'à ≈ 111, 1,65 × le diamètre comme dans refBC2), lierre, bannières unies ; **vantaux** de bois cerclés de fer ouverts contre le couloir (`|x|` 47-49) ; **enceinte crénelée** de 34 qui part vers les côtés (`|x|` 76 → 239, une brèche) ; braseros ; **lucioles dorées** accrochées aux tours : un rideau plaqué contre leur face côté couloir et le long des vantaux (`|x|` 46,5-47,7), une couronne autour du bas de chaque toit ; seuil de grandes dalles à joints sombres, chemin central usé, mousse au pied des tours | **Aller** : seuil de grandes dalles ; à travers la porte, les champs et le crâne. **Retour** : le revers des tours et de l'enceinte, piqueté de lucioles : la base est derrière |
| -32 → -80 | **Champs** | Chemin de terre à ornières et flaques, herbe entre les deux voies, bas-côtés d'herbe et de boue, clôtures au bord de la rue ; à gauche **grange** et **chaumière**, **moulin** de pierre aux ailes déchirées en retrait, labours et blé terni ; à droite une chaumière puis les **côtes géantes** du démon qui sortent des labours (36 de haut, ivoire noirci), meules, puits, charrette, clôtures, arbres morts | **Aller** : le crâne grandit à droite au-dessus des toits, l'église pointe à gauche. **Retour** : les deux tours de la porte au bout du chemin, encadrant les lucioles |
| -80 → -196 | **Village abandonné** | Le chemin de terre continue, plus boueux, avec des restes de vieux pavés ; clôtures des cours ouvertes devant chaque porte (allée de pavés), **parvis** pavé en demi-cercle devant l'église, feux follets violets sur le cimetière ; **chaumières**, **maisons de pierre** à toit d'ardoise (FORGE, AUBERGE), **ruines calcinées** ; deux tiers des fenêtres sont noires ou condamnées de planches (une bougie à l'auberge et dans deux chaumières) ; à gauche l'**église** de pierre (clocher-porche ≈ 56 à flèche d'ardoise, aucune croix) et son **cimetière** ; à droite, derrière une rangée basse, la **colline boisée** (28) et le **CRÂNE DE DÉMON** (64 + cornes, sommet ≈ 120) tourné vers l'entrée, le regard cramoisi (grandes braises Neon au fond des orbites), l'arrière enfoui sous la forêt de la colline, étendard déchiré au sommet ; trois **racines noires à veine violette** sortent du pied de la colline et crèvent les cours | **Aller** : le crâne écrase toute la droite ; au bout de la rue, la tour aux grimoires. **Retour** : le crâne de profil, ses cornes contre le ciel, les tours de la porte au loin |
| -196 → -300 | **Bourg de la tour aux grimoires** | Vieux pavés usés à rigole centrale et caniveaux, **place dallée** de la tour et du marché (z -227 → -273), **parvis en éventail** autour de la tour, deux **cordes à bannières** au-dessus de la rue (entrée et sortie du bourg, pointes des bannières à 34,45) ; **maisons hautes** à colombages noirs (3-4 étages en encorbellement, enduits sourds ; une à dernier étage de travers, une à tourelle d'angle en aiguille, deux maisons de mage aux fioles lumineuses), **taverne** (TAVERNE), **halle** du marché (MARCHÉ) et étals de fioles, BIBLIOTHÈQUE, POTIONS, HERBORISTE ; à gauche une placette et la **TOUR AUX GRIMOIRES** (Ø 32, corps et balcon à 80, **toit en aiguille** jusqu'à 138, baies en arc lumineuses, **spirale de grimoires volants**, planche GRIMOIRES sur deux potences), pupitre de pierre et sa nuée de grimoires, lucioles, bannières unies | **Aller** : la tour se dresse à gauche, l'aqueduc barre l'horizon plus loin. **Retour** : le crâne réapparaît au-dessus des toits, à gauche |
| -300 → -404 | **Champ de bataille des mages** | Terre calcinée et cendre sombres (pavés épars au sortir du bourg, dalles noires qui gagnent vers la place), **cratères** noirs : fissures éteintes dans le couloir (aucun sol lumineux rouge ou orange : on y lirait de la lave), incandescentes sur les côtés ; un **camp de tentes** à gauche ; **douze grands bâtons de mage** (≈ 20 de haut, plantés de biais vers l'extérieur, fût coudé, cage de griffes autour d'un gros orbe violet, vert, doré ou cramoisi, rubans) qui bordent les deux accotements, six petits en cercle autour de deux feux de camp ; **murs crénelés** et **tours rondes** en ruine rapprochés du couloir, une **arcade effondrée** sous l'aqueduc ; épées plantées, boucliers, armes abandonnées, **feux de camp**, bannières en lambeaux, un pupitre abandonné et sa nuée de grimoires ; l'**AQUEDUC** ruiné et sombre en z = -352 (tablier à 62, arche centrale de 94 entre piles, la seule ligne claire, dessous ≥ 36 ; grande brèche à droite entre x = 100 et 164 avec sa cascade, travée tombée à gauche entre -158 et -126, parapets édentés, deux travées affaissées) ; les **falaises noires** commencent aux bords | **Aller** : sous l'arche de l'aqueduc, la place rituelle et le château noir. **Retour** : l'aqueduc encadre la tour aux grimoires et, au loin, le crâne |
| -404 → -498 | **Place rituelle des œufs** | Dalles noires en anneaux carrés jusqu'à `|x| = 90` ; **CERCLE MAGIQUE** de rayon 34 centré en z = -448 (anneaux violets, bande de glyphes dont huit composés, anneau fin interrompu et douze graduations, losange cramoisi à nœuds runiques aux sommets, cœur cramoisi) ; six grands **obélisques** noirs de 28 à coupes de flammes, trois grandes **racines démoniaques** le long du couloir qui encadrent le cercle, épines, braseros, cristaux ; à droite l'**ARBRE DÉMONIAQUE** (≈ 150, tronc torsadé de Ø 30, longues griffes tendues vers le couloir d'où pendent des vrilles, veine violette continue côté couloir) ; haut dans le ciel (90-125), quatre **îlots flottants** de roche noire (trois à gauche, un à droite) tenus chacun par une chaîne en biais ancrée sur le dessus des falaises, lucioles violettes ; deux **fils de lumière violette** partent du cercle et filent sous la porte du château | **Aller** : le château remplit l'horizon, l'arbre et les îlots l'encadrent. **Retour** : l'aqueduc, la tour, le crâne : le chemin de la base |
| -498 → -548 | **Château démoniaque** (repère final) | Falaise noire en gradins sur toute la largeur, forteresse gothique noire, **porte en arc brisé** (voir § 3), tunnel de 50, deux fils de lumière cramoisie au sol | Visible dès l'entrée, au bout de l'axe : c'est la destination |
| -548 | **Sortie** | Bouche du tunnel, ouverte sur la zone suivante | — |

**Côtés** : parcelles de **labours** (sillons de 4) et de **blé terni** séparées de chemins de terre, puis une
**lisière de sapins sombres et d'arbres morts** (`|x|` 150-235) ; la **montagne de la capitale** au loin à gauche
(x = -200, z = -112), en bleu-violet désaturé au sommet, le pied en jupe de forêt sombre et de roche noire, trois
hautes aiguilles de roche ; derrière le bourg, un sous-bois ; à partir de z = -300 des
**falaises noires** à cristaux violets (`|x|` ≥ 180, de 34 à 62 de haut) qui se referment vers le château ; des
maisons de second rang ici et là. Des **murs invisibles** ferment le sol en `|x| = 239`.

**Pourquoi le crâne à droite et la tour à gauche** : le soleil de jour vient de -X/+Z (derrière l'entrée, à
gauche). Le crâne, tourné vers l'entrée (yaw 125), reçoit la lumière de face : l'os ivoire claque contre la colline
noire. La tour est ronde : elle se lit de tous les côtés. L'arbre (droite) et les îlots (gauche) équilibrent la fin.

## 3. Repère final et sortie

`abime.chateau_demon` est posé en `(0, 0, -523)` avec `yaw = 180` : sa façade principale regarde les joueurs (+Z).
- **Falaise** de basalte en gradins irréguliers sur toute la largeur (`|x|` ≤ 239, z -498 → -548), 20 à 46 de
  haut, cristaux violets dans les failles, racines noires qui en sortent ; aucune grande face plane : tout est en
  ressauts, éperons et pans inclinés.
- **Porte** : ouverture de **100** (`|x| < 50`), montants verticaux jusqu'à **40**, puis **arc brisé** en gradins
  jusqu'à ≈ 66 ; voussures de pierre noire à arêtes plus claires ; herse de fer relevée dans l'arc (bas ≥ 42) ;
  deux **tours de porte** octogonales ou rondes (`|x|` 50-68) à flèches jusqu'à ≈ 120 ; bannières cramoisies unies.
- **Château** : **donjon** central en retrait au-dessus de la porte, masse dominante (corps jusqu'à 140, cordon,
  oculus cramoisi) et plus haute flèche (≈ 199) ; ailes et
  tourelles à flèches qui descendent en gradins sur la falaise (≈ 100 → 60), **contreforts** et pinacles, chemin
  de ronde crénelé, **fenêtres lancéolées violettes** (Neon) à tous les étages, quelques oculi cramoisis.
- **Tunnel** : 50 de long (z -498 → -548), dalles de basalte et deux fils de lumière cramoisie peints par
  `zone.py` (ils partent du bord du cercle magique) ; rien du château en dessous de y = 40 au-dessus de `|x| < 50`.
- Le revers (côté zone suivante) est plus simple : falaise, bouche du tunnel, quelques fenêtres.

## 4. Palette et progression (`palette.py`)

La zone s'assombrit d'un bout à l'autre ; les **lueurs** (Neon) prennent le relais de la lumière.

| Séquence | Dominantes | Accents |
|---|---|---|
| Porte et champs | Pierre gris-violet (`pierre*`), ardoise violette (`ardoise*`), lierre sombre, prés olive (`herbe*`), labours (`labour*`) et blé terni (`ble*`) | **Lucioles dorées** (`lueur_doree`), braseros orange : la seule chaleur |
| Village | Moellons gris-brun (`moellon*`), chaume vieilli (`chaume*`), ardoise, ruines calcinées (`bois_brule`, `pierre_noire`), vitres noires et planches | **Os ivoire** du crâne (`os*`, noirci au pied : `os_brule`), regard cramoisi dans les orbites, rares fenêtres à la bougie |
| Bourg | Colombages noirs (`bois_noir`) sur enduits sourds (`enduit_gris`, `enduit_ocre`, `enduit_rouge`, `enduit_vert`), dalles sombres | Tour plus claire (`pierre_claire`, `pierre_pale`) à toit violet, baies dorées et violettes, bannières `toile_cramoisie` et `toile_violette`, grimoires de couleur (`cuir*`) |
| Champ de bataille | Gris-vert brumeux (`herbe_grise`), cendre sombre, brûlis, ruines noires, aqueduc sombre | Gros orbes violets, **verts maladifs**, dorés, cramoisis ; feux orange ; fissures `feu_cramoisi` seulement sur les côtés |
| Place et château | Noir : `basalte`, `obsidienne`, `chateau*`, `dalle_noire`, `racine`, `roche_violette` | **Violet profond** (`lueur_violette` #8C3BFF, `cristal`) et **cramoisi sang** (`lueur_cramoisie` #FF1430, `cramoisi`) ; plus aucune lueur chaude sauf les braseros |

**Lecture sombre en plein jour** : (1) les grandes masses sont foncées mais pas toutes noires (le noir pur
`obsidienne` reste aux arêtes, socles et creux) ; (2) toute masse sombre de plus de 20 studs porte des **lueurs
visibles du couloir** (fenêtres, veines, fissures, cristaux, flammes) ; (3) l'**os ivoire** et la **tour claire** sont
les deux contrepoints lumineux de la première moitié ; (4) Neon ≤ ≈ 900 pièces, transparence presque nulle.
Pas de vert émeraude : les verts sont olive, mousse ou gris-vert sapin ; le seul vert vif est le vert maladif des
orbes et des chaudrons.

## 5. Ce qui distingue la zone de ses voisines

- **Attaque des Titans** (zone suivante) : pas de muraille colossale plate, pas de ville pastel à colombages.
  Ici : tours rondes à toits coniques, enceinte modeste (34), village pauvre de pierre et de chaume, bourg à
  colombages **noirs** sur enduits sourds, château gothique noir hérissé de flèches sur une falaise en gradins.
- **One Piece** (arche-crâne à dents carrées, beige clair) : ici le crâne est **cornu**, posé de 3/4 sur une colline
  **à côté** du couloir, os fissuré et noirci, mâchoire à crocs brisés à demi enterrée ; il n'enjambe rien.
- **Demon Slayer** (glycines, village japonais au crépuscule) : aucune glycine, aucun élément japonais.

## 6. Magie flottante (voulue, jamais accidentelle)

Grimoires, lucioles, orbes, îlots de roche : ils flottent **parce que c'est magique**, et ils doivent se lire comme
un dessin, **alignés sur une source** :
- grimoires : en **spirale** autour de la tour aux grimoires (et sortant de ses fenêtres), ou en nuée au-dessus
  d'un **pupitre de pierre** gravé (`mobilier.nuee_grimoires`, variantes 1 et 3) ;
- lucioles : en **nuages** denses autour des tours d'entrée (rideau plaqué contre leurs faces, couronne autour des
  toits), de la placette, des îlots ; au-dessus du couloir seulement **au-dessus de 31** ;
- orbes : tenus par les griffes, fourches ou anneaux d'un **bâton** planté ;
- îlots : grands (22 à 30), haut contre le ciel (90-125), roche à dessous en plusieurs crocs, racines qui pendent,
  cristaux violets ; une **chaîne** tendue en biais vers un **ancrage** (bloc et anneau de fer, glyphe violet) posé
  sur le dessus de la falaise la plus proche.
Tout le reste repose sur quelque chose (enseignes, lanternes, bannières, herses : accrochées à un support).

## 7. Budget de pièces (plafond 13 500)

| Poste | Budget |
|---|---|
| Sol (couloir ≈ 1 030, accotements ≈ 260, côtés ≈ 790, fissures 77, cercle magique ≈ 95, abords ≈ 190) | ≈ 2 430 (mesuré) |
| Mobilier posé par `zone.py` (≈ 270 poses : clôtures, lanternes, braseros, bâtons, armes, feux, lisière de sapins, arbres morts, tombes, lucioles, grimoires…), cordes à bannières (78), tentes (21) | ≈ 2 650 (mesuré) |
| `assets/remparts.py` : porte d'entrée ≤ 620, 8 segments d'enceinte ≤ 12 + 1,1 × longueur (57), 3 tours en ruine ≤ 110, 5 murs en ruine ≤ 14 + 1,4 × longueur, 2 arches effondrées ≤ 90, aqueduc ≤ 560 | ≤ 2 455 |
| `assets/batiments.py` : 6 chaumières ≤ 60, 3 maisons de pierre ≤ 90, 3 ruines ≤ 50, grange ≤ 65, moulin ≤ 95, église ≤ 300, 7 maisons hautes ≤ 95, taverne ≤ 150, halle ≤ 110, 6 maisons de fond ≤ 28 | ≤ 2 333 |
| `assets/monuments.py` : colline ≤ 280, crâne ≤ 680, côtes géantes ≤ 170, tour aux grimoires ≤ 620, montagne de la capitale ≤ 150 | ≤ 1 900 |
| `assets/abime.py` : château ≤ 1 150, arbre ≤ 420, 4 îlots ≤ 95 (chaîne comprise), 6 obélisques ≤ 26, 9 racines ≤ 30, 6 cristaux ≤ 14, 6 falaises ≤ 14 + longueur | ≤ 2 900 |
| **Total au budget maximal** | **≈ 12 760** |
| **Total mesuré** (`python zone.py --stats`, 10 maisons de fond) | **13 275 pièces, dont 892 Neon** |

`python zone.py --stats` vérifie chaque pose (`hors_budget`), le couloir (`couloir_encombre`), la hauteur libre
(`trop_bas_au_dessus_du_couloir`, et `enjambe_sous_34` pour ce qui enjambe le couloir) et affiche le nombre de pièces
Neon et le budget maximal par module.

## 8. Propriété intellectuelle (obligatoire)

Roblox retire les contenus qui reprennent une licence sans autorisation. La zone n'est qu'une **fantasy sombre
générique** : village médiéval, tour de mages, ruines, château gothique, crâne de démon, arbre noir.
- **Aucun nom** : ni la licence, ni son royaume, ses villages, ses tours, ses escouades, ses personnages, ses
  sorts, ses démons ou son arbre ; ni dans les textes, ni dans les noms de pièces ou de groupes, ni dans le nom
  affiché de la zone (`ZoneBlackClover` reste un nom de fichier interne).
- **Aucun personnage**, PNJ, statue ou silhouette humanoïde ; **aucune statue sur le crâne** (étendard uni à la
  place) ; crâne à **deux orbites** (pas de troisième œil) ; pas d'épouvantail, pas de squelette humain.
- **Aucune forme de trèfle**, à 3, 4 ou 5 feuilles, nulle part : ni au sol, ni dans le cercle magique, ni sur les
  livres, ni dans les ferronneries, ni dans les fenêtres (**pas de quadrilobes gothiques** : baies lancéolées et
  oculi simples seulement).
- **Aucun emblème** d'escouade ou de royaume (taureau, lion, aigle, rose, etc.), aucun blason : bannières et
  boucliers **unis ou à liseré** ; grimoires à **couvertures unies** (cuir de couleur, au plus une bande ou des coins
  dorés), jamais une copie d'une couverture de la licence ; pas de grande épée noire à lame large.
- **Cercle magique générique** : anneaux, glyphes abstraits, losange ; **aucune étoile** (pentagramme,
  hexagramme, étoile à huit branches de deux carrés croisés), aucune lettre d'un alphabet réel (latin, runes,
  hébreu, arabe…).
- **Aucun symbole religieux** : pas de croix sur l'église ni sur les tombes, pas de croissant, pas d'étoile.
- **Textes permis** : enseignes TAVERNE, AUBERGE, GRIMOIRES, MARCHÉ, FORGE, BIBLIOTHÈQUE, HERBORISTE, POTIONS,
  BOULANGERIE, PAIN, ARMURERIE ; indicateurs VILLAGE, MARCHÉ, TAVERNE, GRIMOIRES, CHÂTEAU, TOUR (listes
  `mobilier.TEXTES_ENSEIGNES` et `mobilier.TEXTES_INDICATEURS`). Rien d'autre : ni chiffres, ni dates.

Sources consultées : [le village des confins et son squelette de démon (wiki, miroir)](https://breezewiki.discard.no/blackclover/wiki/Hage),
[le crâne « à trois yeux » qui sert de repère (Bubbleblabber)](https://www.bubbleblabber.com/?p=137952),
[la cérémonie de remise des grimoires (wiki)](https://blackclover.fandom.com/wiki/Grimoire_Acceptance_Ceremony),
[le mystère des tours aux grimoires (ComicBook)](https://comicbook.com/anime/news/black-clover-grimoire-towers-mystery),
[l'arbre qui relie le monde des démons (Anime Hunch)](https://animehunch.com/black-clover-what-is-the-dark-triad-ritual-advent-of-qliphoth/),
[architecture gothique : arc brisé, lancettes, contreforts, flèches (Designing Buildings)](https://www.designingbuildings.co.uk/wiki/Gothic_architecture),
[dix caractéristiques du gothique (History Lists)](https://historylists.org/architecture/10-defining-characteristics-of-gothic-architecture.html).
