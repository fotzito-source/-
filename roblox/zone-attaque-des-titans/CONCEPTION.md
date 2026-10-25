# Conception : zone Attaque des Titans, « la ville entre les murailles »

Septième zone du couloir, après Bleach. Le joueur sort d'une prairie ensoleillée, passe sous une **muraille
colossale** et traverse une ville médiévale dense et chaleureuse, coincée entre des remparts qui l'écrasent. Il
prend son œuf sur la grand-place, au pied d'un beffroi, et repart vers sa base. Au bout, la **muraille
intérieure** ferme la perspective : son tunnel mène à la zone suivante.

**Couloir de course vide et très large, à la demande du joueur** : `|x| < 45` (90 studs), trottoirs jusqu'à
`|x| = 55`. La grand-rue fait donc 110 studs de façade à façade. Longueur : 548 studs de l'entrée (z = 0) à la
sortie (z = -548).

## 1. Ce qu'on garde des références, et ce qu'on corrige

| Source | À reprendre | À corriger ou éviter |
|---|---|---|
| Zone actuelle (`refAOT1.png`, `refAOT2.png`) | Deux murailles immenses de part et d'autre, pilastres et créneaux, canons sur le mur, rangées de petites maisons européennes à toits rouges, bruns et bleus, une fontaine, un mur au fond avec une porte | Murs gris-bleu plats, sans matière ; maisons identiques et clairsemées ; sol gris uni ; le personnage rouge géant devant la porte (licence : **interdit**) ; rien entre la rue et le mur ; aucune transition à l'entrée |
| (a) Muraille vue de la colline | Mur **colossal et lisse, béton beige-gris pâle**, **nervures verticales régulières** sur toute la hauteur, tour de guet au sommet ; **colline herbeuse fleurie** (blanc, jaune, bleu), **grand arbre feuillu**, fermes et **moulins de bois** au pied | Rien |
| (b) Vue aérienne de nuit | Un **saillant rectangulaire** de la muraille enferme une ville très dense, avec un **canal** et une **église** au centre ; chemin de ronde large et éclairé | Rien |
| (c) Ville en contre-jour | **Colombages** : enduit crème, bois brun sombre ; **tuiles terre cuite** ; la muraille derrière | Rien |
| (d) Scène de rue | Maisons de pierre et d'enduit crème de 3-4 étages, **beaucoup de fenêtres et de lucarnes**, **hautes cheminées carrées de brique** | Rien |
| (e) Toits | Mer de tuiles terre cuite, plusieurs **clochers carrés de pierre à baies cintrées** | Rien |

**Recherche** (éléments génériques, tous tirés de villes réelles) :
- **Nördlingen** (Bavière), qu'on cite souvent comme modèle de la ville du manga, sans confirmation de l'auteur :
  enceinte de 1327 encore entière, d'environ 2,7 km, **chemin de ronde couvert** sur tout le tour, 5 portes et une
  douzaine de tours ; mer de **toits rouges** ; au centre, l'église Saint-Georges et sa tour de 90 m, qui domine tout.
- **Rothenburg ob der Tauber** : maisons à colombages authentiques aux couleurs franconiennes réglementées (**ocre,
  crème, rouille, terre cuite**), pignons sur rue de travers ; le **Plönlein**, petite place à fontaine encadrée de
  deux tours-portes, est la composition type d'un carrefour médiéval.
- **Colmar, Petite Venise** : **canal bordé de colombages** pastel (rose, bleu, vert pâle, « dragée »), **géraniums**
  aux fenêtres, **ponts en arc**. On le reprend pour le quartier du canal.
- **Vocabulaire** : colombages (poteaux, sablières, **croix de Saint-André**), **encorbellements** à chaque étage,
  pignons à forte pente (50-60°), tuiles plates en écaille, lucarnes rampantes, pignons à redents des maisons
  bourgeoises, **arcades** de grand-place (*Laubengang*), fontaine de marché à colonne, **mât de fête** (*Maibaum*),
  moulins sur pivot de bois (*Bockwindmühle*).

**En stud** : la muraille se lit par ses **pilastres** (un relief tous les 12-14 studs, de la base au sommet) et
par des **assises horizontales** de 3-4 gris chauds avec quelques pierres isolées en saillie, pas par une
texture. Les maisons se lisent par le contraste **bois sombre / enduit clair** et par leurs **toits terre cuite à
studs**. Les silhouettes doivent se lire de loin : remparts horizontaux, clochers verticaux, pignons en dents de scie.

## 2. Séquence de la course (entrée → sortie)

| z | Moment | Repère | Vue à hauteur de joueur |
|---|---|---|---|
| +8 → -60 | **Prairie hors les murs** | Chemin de terre à ornières au milieu d'un **pré fleuri** (blanc, jaune, bleu, mauve) qui couvre tout le couloir ; clôtures de bois en `|x| = 57` ; à gauche un **moulin sur pivot** et une ferme au chaume, champs, meules ; à droite le **grand arbre feuillu** sur sa butte, une ferme à colombages, un second moulin au loin ; poteau indicateur | La **muraille extérieure** barre tout l'horizon à 60 studs : 90 studs de haut, 270 de large, pilastres réguliers, parapet crénelé, canons, deux tours d'angle de 112. Au centre, la gueule du **tunnel** (104 × 46), sombre, avec au fond la lumière de la ville |
| -60 → -84 | **Tunnel de la porte** | Muraille de 24 d'épaisseur ; voûte surbaissée à claveaux clairs, **herse relevée** dans la voûte (bas à 47), deux **vantaux de bois cloutés** rabattus contre les parois ; dalles sombres | Effet de seuil : on passe de la lumière à l'ombre, puis la ville s'ouvre |
| -84 → -112 | **Place de la porte** | Tapis de dalles ; puits, charrette, **boulets** et canon de campagne au pied du mur à gauche ; étals, caisses, tonneaux à droite ; arbres ; poteau indicateur | Au revers de la muraille : escaliers de bois et monte-charge ; devant, la grand-rue et ses guirlandes de fanions |
| -112 → -214 | **Rue des colombages** | Cinq maisons à colombages par côté, 2 à 4 étages en encorbellement, pignons sur rue alternant avec des toits à lucarnes, **cheminées de brique**, géraniums, enseignes en drapeau (PAIN, AUBERGE, FLEURS, BÄCKEREI, TISSUS) ; réverbères ; deux guirlandes de fanions à 38 studs ; seconde rangée et jardins derrière | Pignons en dents de scie de part et d'autre ; **au-dessus des toits, les remparts latéraux** (le haut du mur, le parapet, les canons et les tourelles dépassent de 20 studs au-dessus des faîtes) ; au bout, le **clocher de l'église** |
| -214 → -268 | **Place de l'église** | À gauche, l'**église** de pierre blonde, nef à grandes baies de vitrail, **clocher-porche de 76** à baies géminées et flèche de cuivre vert-de-gris ; à droite, une placette : **mât de fête** de 40, puits, quatre arbres, bancs ; derrière, le **clocher A** (66) | Premier grand repère vertical ; la placette ouvre la vue sur un **escalier du rempart** droit et sa tourelle de guet |
| -268 → -404 | **Quartier du canal** | À droite, le **canal** (eau bleue entre deux margelles, barques amarrées) longe le trottoir ; **trois ponts en arc** mènent à la rive droite et à ses maisons bourgeoises pastel de 3-4 étages à pignons à redents ; à gauche, le **marché** (quatre étals rayés et un panneau MARCHÉ) puis des maisons bourgeoises et à colombages (FROMAGES, LIBRAIRIE, HORLOGER) ; le **clocher B** (60) à gauche ; deux guirlandes | L'eau et les ponts donnent de la profondeur à droite ; le **beffroi** de la grand-place grandit au bout de la rue, la muraille intérieure derrière lui |
| -404 → -488 | **Grand-place des œufs** | **Cadran de pavés** de rayon 34 au centre du couloir (rose des vents à huit branches, douze marques d'heure, anneaux), anneaux carrés de pavés jusqu'aux façades en `|x| = 90` ; à droite le **beffroi** (hôtel de ville à arcades et tour d'horloge de 84, cadran sur trois faces) ; à gauche la **fontaine de marché** à colonne et des maisons à **arcades** ; arbres, parterres, réverbères à deux bras, bancs, drapeaux, deux guirlandes ; deux étals au fond | La place s'élargit à 180 studs ; l'horloge du beffroi et la fontaine encadrent l'œuf ; au fond, la **muraille intérieure** et son corps de garde |
| -488 → -512 | **Parvis du dépôt** | À gauche le **dépôt de ravitaillement** (hangar, caisses, tonneaux, grue de bois) et un canon ; à droite une **tour de guet** de bois de 40 ; charrettes, boulets, sacs | Le pied de la muraille intérieure, sa porte monumentale |
| -512 → -548 | **Muraille intérieure** (repère final) | Muraille de 90 sur 470 de large et 36 d'épaisseur ; **porte fortifiée** : corps de garde massif flanqué de **deux tours carrées de 125** à toits d'ardoise et drapeaux, grande voûte à claveaux, herse relevée ; tunnel de 104 × 46 | Visible dès la place de la porte, au bout de la grand-rue : la ville est enfermée de toutes parts |
| -548 | **Sortie** | Bouche du tunnel, ouverte vers la zone suivante | — |

Les **côtés** sont fermés par les **remparts colossaux** (faces intérieures en `|x| = 125`, 90 de haut, 20
d'épaisseur), six segments par côté entre les tours d'angle, avec chemin de ronde, parapet crénelé côté champs,
canons sur rails, deux tourelles de guet par côté, trois **monte-charges** de bois et deux **escaliers** contre les
faces intérieures. Au-delà, des **champs** en bandes (blé, prés, potagers) et des bosquets jusqu'à `|x| = 235`.

**Pourquoi les remparts à 125 et pas plus loin** : vu du milieu de la rue (œil à 5 studs), les faîtes des maisons
de la première rangée (vers 38 studs en `|x| ≈ 64`) cachent tout ce qui est sous 69 studs en `|x| = 125`. Un mur
de 90 dépasse donc de 20 studs au-dessus des toits : on voit en permanence son parapet, ses canons et ses tours.
Sur les places (porte, église, grand-place), il apparaît en entier.

**Retour** : depuis la grand-place, la rue file vers la **muraille d'entrée**, vue de dos (pilastres, escaliers,
monte-charges, tunnel lumineux sur la prairie). Les deux faces des murailles sont soignées, les enseignes et les
guirlandes se lisent dans les deux sens.

## 3. Repère final et sortie

`remparts.porte_colossale(variant=1)` est posée en `(0, 0, -530)` avec `yaw = 180` : sa façade principale regarde
la ville (+Z).
- **Muraille** : même vocabulaire que les remparts (talus, pilastres, assises, cordon, corniche, parapet crénelé),
  470 de large (elle file sous les tours d'angle et jusqu'au bord du sol), 90 de haut, 36 d'épaisseur.
- **Porte fortifiée** (`|x| < 30` environ en façade, tout ce qui passe au-dessus du couloir est au-dessus de 46) :
  corps de garde de 40 de large qui avance de 6 à 8 sur la ville entre 50 et 110 studs, flanqué de **deux tours
  carrées** (16 × 16) qui montent à 125 avec parapets crénelés, toits d'ardoise en pavillon et drapeaux.
  Grande voûte surbaissée à claveaux alternés clairs et foncés et clé lisse (aucun emblème) ; **herse** de fer
  relevée (barre basse à 47) ; lanternes et bannières unies de part et d'autre.
- **Tunnel** de 36 studs de long, `|x| < 52`, hauteur libre 46 ; il débouche en `z = -548` sur la zone suivante.
- Sur le chemin de ronde : canons sur rails pointés vers l'extérieur (côté -Z), deux grues de bois penchées sur la
  ville, deux tourelles de guet, drapeaux.
- Le revers (côté zone suivante, -Z) est plus simple : pilastres, parapet, bouche du tunnel.

## 4. Palette (`palette.py`)

- **Murailles** (dominantes) : `mur` #CFC7B6, `mur_clair`, `mur_pale` (arêtes, corniches), `mur_fonce`,
  `mur_ombre` (creux, bas), `mur_joint`, `mur_base` (talus), `mur_coulure`, `mur_mousse`, `lierre` ;
  `pierre_mur(rng)` tire une des quatre pierres principales ; `chemin_ronde` pour le dessus.
- **Ville** : enduits `enduit_creme` #F1E5C9, `enduit_blanc`, `enduit_ocre`, `enduit_saumon`, `enduit_jaune`,
  `enduit_gris`, `enduit_bleu` (rare) ; bois `colombage` #4A3226, `colombage_brun`, `colombage_rouge` ; pierre
  `pierre_maison`, `pierre_maison_claire`, `pierre_brune`, `gres`, `soubassement` ; tuiles `tuile` #C2603A,
  `tuile_claire`, `tuile_fonce`, `tuile_brune`, `tuile_rouge` ; `ardoise*` ; `brique` (cheminées) ; `cuivre_vert`
  (flèches, en accent) ; fenêtres `fenetre` sombre et `fenetre_cadre` blanc ; volets vert, bleu, rouge, brun.
- **Sol** : pavés `pave` #ABA69B, `pave_clair`, `pave_fonce`, `pave_brun`, `pave_rouge` (motifs de la place),
  dalles des trottoirs `dalle`, `dalle_fonce`, `bordure`, `quai`, `eau*`.
- **Campagne** : `herbe` #7DB547 (vert-jaune ensoleillé), `herbe_claire`, `herbe_fonce`, `herbe_seche`, `terre*`,
  fleurs blanche, jaune, bleue, mauve, rouge, rose ; `ble`, `foin`, `chaume` ; feuillages `feuille*` (jamais
  émeraude) ; troncs.
- **Accents** : drapeaux et toiles rouge, vert, bleu, jaune, crème (unis ou rayés) ; `fonte` (canons, ferronnerie),
  `fer`, `laiton`, `or` (pommeaux, aiguilles), `lampe` (verre des lanternes, Neon), `cadran`.

## 5. Budget de pièces (plafond 13 500)

| Poste | Budget |
|---|---|
| Sol (couloir 917, trottoirs 174, ville 114, prairie 171, champs 58) | 1 434 (mesuré) |
| Mobilier posé (16 réverbères, 6 guirlandes et 12 mâts, 8 étals, objets, clôtures, bornes) | ≈ 1 230 (mesuré) |
| `assets/remparts.py` : porte d'entrée ≤ 800, porte finale ≤ 1 050, 4 tours d'angle ≤ 100, 12 segments de rempart ≤ 10 + longueur + 24 par canon + 36 par tourelle (105 ou 141), 3 monte-charges ≤ 70, 2 escaliers ≤ 50 | ≤ 3 964 |
| `assets/batiments.py` : 13 maisons à colombages ≤ 100, 8 maisons bourgeoises ≤ 110, 5 maisons à arcades ≤ 110, 14 maisons du fond ≤ 30, 2 fermes ≤ 75 | ≤ 3 300 |
| `assets/monuments.py` : église ≤ 400, 2 clochers ≤ 95, beffroi ≤ 340, fontaine ≤ 70, 3 moulins ≤ 80, dépôt ≤ 150, tour de guet ≤ 60, mât de fête ≤ 40 | ≤ 1 490 |
| `assets/nature.py` : 33 arbres ≤ 26, arbre géant ≤ 200, 9 buissons ≤ 8, 10 parterres ≤ 16, 4 meules ≤ 10, 3 champs ≤ 30, colline ≤ 40, canal ≤ 160, 3 ponts ≤ 45 | ≤ 1 755 |
| **Total au budget maximal** | **≈ 13 170** |

`python zone.py --stats` vérifie chaque pose (`hors_budget`), le couloir (`couloir_encombre`) et la hauteur
libre (`trop_bas_au_dessus_du_couloir`).

## 6. Propriété intellectuelle (obligatoire)

Roblox retire les contenus qui reprennent une licence sans autorisation. La zone n'est qu'une **ville médiévale
européenne fortifiée générique** : murailles, colombages, clochers, moulins, canal, marché.
- **Aucun nom** : ni la licence, ni ses trois murs, ses districts ou ses villes, ni ses personnages, ses unités ou
  ses lieux, ni dans les textes, ni dans les noms de pièces, ni dans le nom affiché de la zone
  (`ZoneAttaqueDesTitans` reste un nom de fichier interne ; ne pas l'afficher en jeu).
- **Aucun personnage**, PNJ, statue ou silhouette humaine ; **aucun géant**, aucune tête, main, visage, crâne ou
  vapeur derrière les murs ; pas d'épouvantail.
- **Aucun emblème** ni symbole militaire : pas d'ailes, de roses, de licorne, d'épées croisées, de blason, de
  numéro d'unité ; drapeaux et bannières **unis ou à bandes**. Pas de cape verte suspendue.
- **Aucune réplique d'objet** : pas d'équipement de manœuvre (harnais, grappins, bonbonnes, lames), pas de cage
  géante, pas de cratère, pas d'arbres géants de forêt-repère, pas de rocher bouchant la porte.
- La muraille reste **générique** : pierre pâle à pilastres, comme un rempart de ville réelle agrandi. Pas de
  visage dans la maçonnerie, pas de porte en forme de bouche.
- **Textes permis** : PAIN, BOULANGERIE, AUBERGE, MARCHÉ, FROMAGES, FORGE, TISSUS, HORLOGER, FLEURS, LÉGUMES, SAVON,
  LIBRAIRIE, BÄCKEREI, GASTHAUS, MARKT, BROT, FONTAINE (pas d'alcool, pas de chiffres ni de dates).

Sources consultées : [Nördlingen, ville souvent citée comme modèle (Outlook Traveller)](https://www.outlooktraveller.com/explore/this-german-village-is-the-inspiration-behind-a-top-rated-anime),
[lien non confirmé par l'auteur (Xataka)](https://www.xataka.com.br/filmes-e-series/esta-peculiar-cidade-na-alemanha-inspirou-attack-on-titan-e-sua-origem-e-ainda-mais-intrigante),
[Nördlingen, enceinte et chemin de ronde couvert (Frommer's)](https://www.frommers.com/destinations/nordlingen/attractions/overview),
[Nördlingen, tour Daniel (Germany Footsteps)](https://germanyfootsteps.com/things-to-do-in-nordlingen/),
[Rothenburg, le Plönlein (World City Trail)](https://worldcitytrail.com/2025/02/10/plonlein-in-rothenburg/),
[Rothenburg, couleurs franconiennes (The Abroad Guide)](https://theabroadguide.com/rothenburg-romantic-road-day-trip-munich/),
[Colmar, Petite Venise (Lonely Planet)](https://www.lonelyplanet.com/france/colmar/attractions/petite-venise/a/poi-sig/1196488/1003135),
[Colmar, canaux et ponts (My Global Viewpoint)](https://www.myglobalviewpoint.com/best-things-to-do-in-colmar-france/).
