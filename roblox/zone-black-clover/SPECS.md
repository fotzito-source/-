# Fiches des modules d'assets (zone Black Clover)

Quatre modules, quatre constructeurs en parallèle. Chaque fiche se suffit à elle-même : signatures exactes (telles
que `zone.py` les appelle), poses, emprises, hauteurs, budgets, variantes, règles du couloir, références, aspect
de jour et au crépuscule, propriété intellectuelle. Lire aussi `CONCEPTION.md` (intention) et `CONVENTIONS.md`
(kit, palette, style). Le mobilier (`assets/mobilier.py`) et `palette.py` existent déjà : les utiliser, ne pas les
modifier ; ne pas modifier `zone.py` (le signaler au directeur artistique si une pose doit bouger).

Rappels valables pour les quatre fiches :
- Fonction `f(b, variant=0, **params)` qui ajoute des pièces au `kit.Builder` et renvoie `{"emprise": (x, z),
  "hauteur": h}`. Origine : centre de l'emprise au sol, y = 0 au sol ; **avant vers -Z local** ; `zone.py` tourne
  l'asset (`yaw = -90` à gauche, `+90` à droite, `180` pour ce qui fait face aux arrivants). `R_y(yaw)·(0,0,-1) =
  (-sin yaw, 0, -cos yaw)` donne la direction de l'avant dans le monde.
- Couloir : rien de solide dans `|x| < 45` entre y = 0,05 et 12 ; **rien du tout au-dessus de `|x| < 46` sous
  y = 30** ; ce qui enjambe le couloir garde ≥ 92 entre ses appuis (appuis en `|x| ≥ 46`) et un dessous ≥ 34.
  Ne jamais poser de sol (zone.py peint tout le sol, y ≤ 0).
- Style stud : silhouettes fortes, aplats cassés en « pixels » de 3-4 tons (`vary`, `pierre(rng)`, `moellon(rng)`,
  `roche(rng)`), studs sur les dessus et les pentes de toit (pas sur les murs), détails en saillie ≥ 0,1 (pas de
  faces coplanaires de couleurs différentes), tailles ≥ 0,1, `collide=False` pour les petits détails. **Sombre mais
  lisible en plein jour** : toute masse sombre de plus de 20 studs porte des lueurs Neon visibles du couloir ; Neon
  avec mesure (≈ 900 pour toute la zone, dont ≈ 330 déjà posées), transparence presque jamais.
- Propriété intellectuelle : aucun nom de la licence (ni texte, ni nom de pièce ou de groupe), aucun personnage ni
  statue ni silhouette humanoïde, **aucune forme de trèfle** (ni quadrilobe dans les fenêtres), aucun emblème ni
  blason (bannières et boucliers unis ou à liseré), aucune étoile (5, 6, 8 branches), aucune lettre d'un alphabet
  réel, aucun symbole religieux (croix, croissant). Textes permis seulement : TAVERNE, AUBERGE, GRIMOIRES, MARCHÉ,
  FORGE, BIBLIOTHÈQUE, HERBORISTE, POTIONS, BOULANGERIE, PAIN, ARMURERIE.
- Contrôles : `PY apercu.py assets.<module>:<fonction> --variant N [--params '{"k": v}'] --res 1200x675
  --samples 12` (lire les PNG avec Read), puis `PY zone.py --stats` (couloir, hauteur libre, `hors_budget` vides) et
  `PY zone.py --chevauchements`, puis `PY rendu.py --rapide --sans-export --vues <vues>`. Un seul rendu à la fois,
  1200 × 675 et 12-16 échantillons au plus. `PY = /tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/bvenv/bin/python`.

---

## assets/remparts.py

**Rôle** : la porte d'entrée (refBC2) et son enceinte, les ruines du champ de bataille (refBC4) et l'aqueduc
ruiné qui enjambe le couloir (refBC3). Pierre gris-violet en assises de 4 tons (`pierre`, `pierre_claire`,
`pierre_fonce`, `pierre_pale` pour cordons et arêtes, `pierre_ombre` pour les creux) ; ruines plus sombres et
calcinées (`pierre_noire`, `pierre_fonce`, `bois_brule`) ; toits `ardoise*` ; lierre `lierre`, `lierre_clair` ;
mousse `mousse`. **Budget du module ≤ 2 455 pièces.** Vues de contrôle : `entree`, `retour`, `bataille`,
`aerienne`.

### `porte_entree(b, variant=0, ouverture=100, rayon_tour=13, hauteur_tour=58, hauteur_mur=34)` — ≤ 620 pièces
Pose : `(0, 0, -16)`, `yaw = 180` (une seule, variante 0). Repère local : avant (-Z local) = côté des arrivants
(+Z monde) ; +Z local = côté village.
- **Deux tours rondes** d'axes `x = ±(ouverture/2 + rayon_tour) = ±63`, z = 0 : faces intérieures en `|x| = 50`.
  Talus à la base (rayon + 1,5, 0 → 4), corps en **assises** de cylindres empilés de 4 de haut en 3-4 tons (ou
  anneau de blocs), quelques pierres isolées en saillie, 3-4 **archères** par tour (fentes sombres, deux ou trois
  avec une lueur `lueur_bougie` Neon), **mâchicoulis** (couronne de consoles) vers `hauteur_tour - 6`, bandeau en
  saillie à `hauteur_tour`, puis **toit conique très pointu** d'ardoise violette (`ardoise_fonce`, `ardoise`,
  `ardoise_claire`) : 8-10 anneaux de cylindres qui rétrécissent du rayon 15 (débord) jusqu'à 1, sommet ≈ 96-100,
  studs sur les gradins, **épi doré** (`or`, boule et pointe). Plaques de **lierre** sur les faces avant et
  intérieures (5-6 par tour, en saillie 0,2-0,4).
- **Vantaux** : deux vantaux de bois sombre (`bois_fonce`) cerclés de fer (`fer_fonce`), ouverts à 90° vers le
  village et plaqués le long du couloir : `|x|` de 47 à 49, z local de +2 à +16, 26 de haut, gonds de fer qui les
  relient aux tours. Rien en `|x| < 47`.
- **Liaison avec l'enceinte** : un pilier de liaison par tour, `|x|` 71 → 77, z local ±5,5, de 0 à `hauteur_mur + 3`
  (le premier segment d'enceinte commence en `|x| = 76` et s'y encastre).
- **Accents** : `mobilier.banniere_murale` (cramoisie et violette, variantes 0 et 1) sur la face avant de chaque
  tour vers y = 46 et une sur le revers ; `mobilier.lanterne_murale` (variante 0) sur la face intérieure de chaque
  tour vers y = 14, au-dessus des vantaux (dépasse jusqu'à `|x| = 48`). Les braseros et les lucioles sont posés
  par `zone.py` (braseros en `(±48,6, -3)` et `(±48,6, -36)` monde, à laisser libres).
- Lecture : de l'entrée, les deux tours encadrent la vue comme dans refBC2 ; au retour, leur revers (lierre,
  lanterne, bannière) annonce la sortie. Jour : pierre gris-violet, toits violets, lueurs chaudes discrètes.
  Crépuscule : cônes en silhouette sur le ciel violet, archères allumées.
- Renvoie `{"emprise": (152, 32), "hauteur": ≈ 98}`.

### `mur_enceinte(b, variant=0, longueur=40.75, hauteur=34, epaisseur=8)` — ≤ 12 + 1,1 × longueur (57)
Poses : 8 segments en `x = ±(76 + 40,75 × (k + 0,5))`, `z = -16`, `yaw = 180`, k = 0..3 ; variantes à gauche 0,1,2,3
(du centre vers le bord), à droite 2,3,0,1. Le dernier segment finit au bord du sol (`|x| = 239`).
- Mur le long de X local, centré (`|x| ≤ longueur/2`), épaisseur ±4 en z. **Assises de 4** de haut (y = 0, 4, 8…,
  mêmes hauteurs pour tous les segments, qui se touchent bout à bout), talus de 1 à la base, **cordon** `pierre_pale`
  à 26, **chemin de ronde** à `hauteur - 4` (= 30, studs), parapet crénelé côté avant (merlons de 3 × 3 au pas de 4,
  sommet à `hauteur`), parapet bas côté village. 2 contreforts à gradins sur la face avant (jusqu'à 20).
- Variantes : 0 sobre (contreforts, une bannière murale) ; 1 rideaux de **lierre** qui pendent du parapet + 2
  archères allumées ; 2 **brèche** en V dans les 12 derniers studs du haut sur 12 de long, assises en escalier,
  éboulis au pied des deux côtés (z ±10 au plus) ; 3 **échauguette** en encorbellement au milieu de la face avant
  (cylindre r 3 de 24 à 34 sur consoles, toit conique d'ardoise jusqu'à 42, archère allumée).
- Renvoie `{"emprise": (longueur, 10), "hauteur": hauteur}`.

### `ruine_tour(b, variant=0, rayon=10, hauteur=44)` — ≤ 110
Poses : `(-84, 0, -318)` r 10 h 44 v0 yaw -90 ; `(-160, 0, -388)` r 12 h 34 v1 yaw -90 ; `(92, 0, -392)` r 11
h 52 v2 yaw 90.
- Tour ronde **brisée et creuse** : anneau de 12 « douves » de pierre (blocs de 2 d'épaisseur) par assises, chaque
  douve à une hauteur différente (couronne déchiquetée, le côté avant plus bas qui montre l'intérieur vide), une
  grande brèche, 2-3 poutres calcinées en travers à l'intérieur, une archère, éboulis au pied (4-8 blocs dans un
  rayon `rayon + 6`), lierre et mousse. Pierre `pierre_noire`, `pierre_fonce`, `pierre_ombre`.
- Variantes : 0 haute, couronne déchiquetée, brèche vers le couloir ; 1 moignon (moitié de hauteur) et un pan de
  mur couché au sol ; 2 la plus haute, un arc de parapet crénelé encore debout et une **cicatrice magique** violette
  (fente `lueur_violette` Neon dans la maçonnerie).
- Renvoie `{"emprise": (2 * rayon + 12, 2 * rayon + 12), "hauteur": hauteur}`.

### `ruine_mur(b, variant=0, longueur=36, hauteur=18, epaisseur=5)` — ≤ 14 + 1,4 × longueur
Poses (x, z, yaw, longueur, hauteur, variante) : `(-66, -380, -90, 36, 18, 0)`, `(-122, -330, 0, 40, 16, 1)`,
`(66, -318, 90, 30, 20, 2)`, `(150, -372, 20, 34, 14, 3)`, `(-112, -376, 75, 30, 12, 0)`.
- Courtine en ruine le long de X local : profil haut en escalier (3-6 ressauts), un fragment de créneaux sur la
  partie la plus haute, éboulis au pied, pierres noircies, lierre. Épaisseur ±epaisseur/2 en z ; l'emprise ne
  dépasse pas `longueur × (epaisseur + 6)`.
- Variantes : 0 déchiquetée avec deux merlons ; 1 percée d'une **porte en arc brisé** (6 × 10) ; 2 effondrée au
  milieu (deux moignons et un tas d'éboulis) ; 3 basse, avec un contrefort tombé.
- Le mur `(-66, -380, -90)` longe l'accotement gauche (face en `x = -63,5`) : rien en `|x| < 60`.
- Renvoie `{"emprise": (longueur, epaisseur + 6), "hauteur": hauteur}`.

### `arche_effondree(b, variant=0, largeur=30, hauteur=26)` — ≤ 90
Poses : `(-128, 0, -392)` yaw -60 v0 ; `(138, 0, -324)` yaw 70 v1.
- Arcade isolée de 2 ou 3 arcs (plein cintre en gradins ou arcs brisés) sur piles, le long de X local, profondeur
  4-6 ; un arc effondré (moignons de piles, claveaux tombés au sol) ; haut des arcs déchiqueté, lierre (refBC4).
  Pierre `pierre_fonce`, `pierre`, claveaux `pierre_pale` alternés.
- Variantes : 0 trois arcs dont un tombé ; 1 deux arcs, le second réduit à une pile penchée ; 2 un seul grand arc
  brisé encore debout.
- Renvoie `{"emprise": (largeur, 8), "hauteur": hauteur}`.

### `aqueduc(b, variant=0, largeur=478, ouverture=94, dessous=36, hauteur=62, rupture=(100.0, 164.0), affaisse=None)` — ≤ 560

*Finition* : pierre sombre (seuls les claveaux et l'archivolte de l'arche centrale restent clairs), `rupture` accepte
une liste de tronçons (la première brèche a la cascade ; zone.py pose (100, 164) et (-158, -126)), une travée sur
trois perd son parapet hors de |x| < 60, `affaisse` = {(x0, x1) : affaissement} abaisse tablier, parapets et canal
d'une travée. Posé en variante 3 (plus de lierre).
Pose : `(0, 0, -352)`, `yaw = 0` : l'aqueduc court le long de X (monde) de -239 à +239, en travers du couloir.
- **Piles** de 10 (x) × 10 (z) : les deux piles du couloir ont leurs faces intérieures en `|x| = ouverture/2 = 47`
  (piles de 47 à 57, socles jusqu'à `|x| = 46,5` au plus près) ; les autres piles au pas de 32 (axes en `±52,
  ±84, ±116, ±148, ±180, ±212`), l'aqueduc s'enfonce dans les falaises aux deux bouts (`|x|` > 180).
- **Arche centrale** au-dessus du couloir : naissance à `dessous = 36` contre les piles, arc surbaissé en gradins
  jusqu'à ≈ 50 au centre ; **aucune pièce sous y = 36 au-dessus de `|x| < 47`**. Arches latérales (portée 22) plus
  hautes que larges, dessous ≈ 44, claveaux alternés `pierre_pale` / `pierre`.
- **Tablier** au-dessus des arches jusqu'à `hauteur = 62` : corniche, deux parapets bas et un **canal d'eau sombre**
  (`eau`) entre eux ; mousse et lierre qui pendent des arches (pas sous 30 au-dessus du couloir).
- **Rupture** (x local de 100 à 164) : tablier et arcs disparus ; les piles 116 et 148 réduites à des moignons
  déchiquetés (18 à 30 de haut) ; bouts du tablier cassés en escalier en x = 100 et x = 164 ; **éboulis** au sol
  (blocs, claveaux) entre x = 105 et 160, z ±10 ; une **cascade** (3-4 blocs `eau_claire` décalés, sans collision)
  qui tombe du canal brisé en x = 100 dans une flaque (`eau`) au sol.
- Jour : un long trait horizontal gris-violet qui barre l'horizon du champ de bataille ; crépuscule : les arches
  cadrent la silhouette du château.
- Renvoie `{"emprise": (largeur, 12), "hauteur": hauteur}`.

**Références** : refBC2 (tours rondes, toits coniques, lierre), refBC4 (ruines, tours rondes brisées, arches
effondrées), refBC3 (arches d'aqueduc brisées). **À éviter** : muraille colossale plate (zone Attaque des Titans),
emblèmes sur les bannières, croix ou trèfles dans la maçonnerie.

---

## assets/batiments.py

**Rôle** : le village abandonné des confins (moellons, chaume, ardoise, ruines) et le bourg serré autour de la tour
aux grimoires (maisons hautes à colombages **noirs** sur enduits sourds). Tous les bâtiments sont posés par
`zone.py` avec `yaw = face_couloir(x)` (-90 à gauche, +90 à droite) : la façade avant (z local =
`-profondeur/2`) est sur l'alignement `|x| = 55` (57 dans les champs). Encorbellements, auvents, enseignes,
lanternes : rien en avant de `z local = -profondeur/2 - 3` (`|x| ≥ 52`). **Budget du module ≤ 2 333 pièces.**
Vues de contrôle : `village`, `crane`, `tour`, `retour`.

Palette : moellons `moellon`, `moellon_clair` (chaînes d'angle), `moellon_fonce` ; chaume `chaume`, `chaume_fonce`,
`chaume_clair` ; ardoise `ardoise`, `ardoise_fonce`, `ardoise_claire`, `ardoise_bleue` (pentes de 55-60°, studs) ;
bois `bois`, `bois_fonce`, `bois_noir` (colombages), `bois_gris` (granges), `bois_brule` (ruines) ; enduits
`enduit_gris`, `enduit_ocre`, `enduit_rouge`, `enduit_vert`, `enduit_creme` (jamais pastel) ; fenêtres `fenetre`
(sombres) et `lueur_bougie` (Neon, une fenêtre sur trois environ), cadres `fenetre_cadre` ; volets `bois_fonce`
ou `cramoisi_fonce`. Mobilier à appeler : `mobilier.enseigne(b, texte, variant)` (origine sur la face du mur,
dépasse vers -Z), `mobilier.lanterne_murale`, `mobilier.tonneaux`, `mobilier.caisses`, `mobilier.etal`.

### `chaumiere(b, variant=0, largeur=14, profondeur=12, lumieres="toutes")` — ≤ 60

*Finition* : `lumieres="eteintes"` (maison abandonnée : la fenêtre éclairée devient une vitre noire, condamnée de
planches une fois sur deux).
Poses : champs gauche z -70 (12 × 12, v3), champs droite z -46 (v1), village gauche z -88 (v0) et z -186 (v2),
village droite z -106 (v1) et z -143 (v4).
- Maison basse d'un niveau et combles : murs de moellons en pixels (chaînes d'angle claires), **chaume épais** en
  gradins (avant-toit bas vers 5-6, faîtage vers 13), petites fenêtres profondes (une allumée), porte de planches
  à pentures de fer, cheminée de pierre ; appentis ou tas de bois selon la variante. Hauteur ≤ 15.
- Variantes (≥ 5) : 0 faîtage parallèle à la rue ; 1 pignon sur rue et lucarne ; 2 toit d'ardoise moussu ;
  3 en L avec appentis ; 4 **toit à moitié effondré** (trou, chevrons calcinés) : village abandonné.

### `maison_pierre(b, variant=0, largeur=16, profondeur=14, etages=2, enseigne=None, lumieres="toutes")` — ≤ 90

*Finition* : `lumieres` = "toutes", "faible" (deux bougies) ou "eteintes" (vitres noires, planches, lanterne
décrochée ; le foyer d'une forge reste rougeoyant).
Poses : village gauche z -106 (v0, `enseigne="FORGE"`), village droite z -88 (v1) et z -182 (v2,
`enseigne="AUBERGE"`).
- Maison de pierre à deux niveaux, **pignon d'ardoise très pentu** sur rue, lucarne, cheminée, volets, porte sous
  un petit auvent, `mobilier.lanterne_murale` près de la porte. Si `enseigne` : `mobilier.enseigne(b, enseigne)` en
  drapeau au premier étage. FORGE : grande baie au rez-de-chaussée avec une enclume et un **foyer rougeoyant**
  (`feu` Neon) ; AUBERGE : tonneaux à la porte. Hauteur ≈ 26.
- Variantes (≥ 3) : moellons ou pierre gris-violet, pignon ou croupe, encorbellement de bois à l'étage.

### `maison_ruine(b, variant=0, largeur=12, profondeur=12)` — ≤ 50
Poses : village gauche z -123 (v0), village droite z -124 (v1) et z -161 (v2).
- **Ruine incendiée** : murs aux arêtes déchiquetées en escalier, un pignon encore debout, pas de toit (2-3 chevrons
  calcinés penchés), trou de fenêtre noir, éboulis dedans et au pied. `moellon_fonce`, `pierre_noire`,
  `bois_brule`. Hauteur ≤ 12.
- Variantes (≥ 3) : 0 pignon debout ; 1 deux murs d'angle seulement ; 2 braises encore rouges dans les décombres
  (petit `cramoisi` Neon).

### `grange(b, variant=0, largeur=20, profondeur=14)` — ≤ 65
Pose : champs gauche z -50 (v0, façade en `x = -57`).
- Grange de planches verticales `bois_gris` en deux tons sur un soubassement de pierre de 2, grand toit (chaume
  sombre ou ardoise) pignon sur rue, double porte (une entrouverte), fenil ouvert avec du foin (`foin`). Hauteur ≈ 16.
  Variantes (≥ 3) pour d'autres poses futures.

### `moulin(b, variant=0)` — ≤ 95
Pose : `(-112, 0, -62)`, `yaw = -90` (les ailes regardent le couloir).
- Moulin-tour de pierre : corps rond ou octogonal Ø ≈ 10 jusqu'à 22, toit conique (chaume sombre ou ardoise) jusqu'à
  ≈ 28, **quatre ailes** de lattes sombres sur un moyeu tourné vers -Z local (envergure ≈ 24, dans le plan X-Y à
  z local ≈ -7), deux ailes à **toile déchirée** (`toile_grise`, `toile_ecru`), une aile cassée plus courte ; porte,
  une fenêtre allumée. Emprise ≤ 14 × 14 au sol, hauteur ≤ 40. Variantes (≥ 3) : ailes entières, déchirées, arrêtées
  en croix.

### `eglise(b, variant=0, largeur=26, profondeur=44)` — ≤ 300
Pose : `(-77, 0, -154)`, `yaw = -90` : pignon et clocher tournés vers le couloir (façade en `x = -55`), nef vers
l'extérieur jusqu'à `x = -99`, z de -141 à -167.
- Petite église de village en pierre sombre (`pierre_fonce`, `moellon`) : **clocher-porche** carré de 10 × 10 au
  centre de la façade jusqu'à ≈ 38, **flèche octogonale d'ardoise** très aiguë jusqu'à ≈ 56 (gradins ou coins),
  terminée par une **simple pointe de fer et une boule dorée** (**aucune croix**) ; cloche (`laiton`) visible dans la
  chambre des cloches ; portail en **arc brisé** (bois sombre) ; **baies lancéolées** à vitraux sourds (`vitrail_violet`,
  `vitrail_ambre`, `vitrail_rouge` ; deux ou trois en Neon faible), un oculus rond simple (**pas de quadrilobe**) ;
  contreforts le long de la nef ; toit d'ardoise à studs **en partie effondré** (trou, poutres calcinées) : église
  abandonnée.
- Le cimetière (posé par `zone.py`) occupe z -132 → -140 et -170 → -176, x -60 → -92 : laisser libre.
- Variantes : 0 (posée) ; 1 sans effondrement pour une autre pose.

### `maison_haute(b, variant=0, largeur=14, profondeur=14, etages=3, enseigne=None, fioles=False)` — ≤ 95

*Finition* : `fioles=True` pose trois fioles lumineuses (Neon) à la fenêtre du premier étage tournée vers l'entrée ;
la tourelle de la v5 a une flèche en aiguille.
Poses : bourg gauche z -204 (v0, 3 étages), z -220 (v1, 4, `enseigne="BIBLIOTHÈQUE"`), z -280 (v2, 3,
`enseigne="POTIONS"`), z -294 (v3, 4, largeur 12) ; bourg droite z -231 (v4, 4), z -277 (v5, 3,
`enseigne="HERBORISTE"`), z -293 (v2, 4).
- Maison haute et étroite de bourg : rez-de-chaussée de pierre sombre avec **devanture** (grande baie à cadre de
  bois sombre, intérieur éclairé), étages en **colombages noirs** (`bois_noir` : poteaux, sablières, croix de
  Saint-André) sur enduit sourd (une teinte par variante), **chaque étage en encorbellement** de 0,8 à 1 vers la
  rue, **pignon d'ardoise très pentu** (≈ 60°) sur rue avec petite lucarne, cheminée de pierre, deux fenêtres par
  étage (sombres ou à la bougie), `mobilier.lanterne_murale`, enseigne si demandée. Hauteur ≈ 6 + 6 × étages +
  toit (≈ 30 à 40).
- Variantes (≥ 6) : enduit gris, ocre, rouge sang-de-bœuf, vert éteint, crème sali ; pignon sur rue ou toit à
  lucarnes ; dernier étage de travers ; v4 avec une **oriel** (bow-window) ; v5 avec une tourelle d'angle à toit
  conique.

### `taverne(b, variant=0, largeur=24, profondeur=16)` — ≤ 150
Pose : bourg droite z -210 (façade en `x = 55`, z -198 → -222).
- Grande auberge : rez-de-chaussée de pierre à **fenêtres en arc chaudement éclairées**, deux étages de colombages
  noirs sur enduit ocre, auvent sur poteaux devant la porte (poteaux en `|x| ≥ 52`), `mobilier.enseigne(b,
  "TAVERNE")` en drapeau, tonneaux et banc à la porte, deux cheminées. Hauteur ≈ 32.

### `halle(b, variant=0, largeur=26, profondeur=14)` — ≤ 110
Pose : bourg droite z -254 (façade en `x = 55`, z -241 → -267).
- Halle de marché couverte : poteaux de bois sombre sur dés de pierre, côtés ouverts, grand toit d'ardoise en
  croupe avec un petit lanternon au faîtage, étals intérieurs (comptoirs, caisses, sacs, fioles colorées dont
  quelques-unes en Neon), lanternes suspendues, planche « MARCHÉ » sous l'avant-toit côté couloir (label `serif`).
  Deux étals sont posés par `zone.py` sur l'accotement devant (`x ≈ 50,8`, z -246 et -260) : rien devant la façade.
  Hauteur ≈ 20.

### `maison_fond(b, variant=0, largeur=12, profondeur=10, etages=1)` — ≤ 28
Poses : six maisons de second rang (`(-104, -92)`, `(-106, -186)`, `(-100, -207)`, `(-104, -292)`, `(98, -232)`,
`(100, -284)`, 1 ou 2 étages, variantes 0-3).
- Maison simple vue de loin : bloc de pierre, toit à deux pans (ardoise ou chaume), cheminée, une ou deux fenêtres
  (une allumée). Variantes (≥ 4) : ardoise, chaume, cheminée à gauche ou à droite, une en ruine.

**Références** : refBC1 (village pauvre et ruiné au pied du crâne, champs), refBC2 (pierre et lierre). **À éviter** :
la ville pastel à colombages clairs de la zone Attaque des Titans (ici : colombages noirs, enduits sourds, ardoise
violette, chaume sombre), toute croix ou étoile, toute enseigne hors de la liste.

---

## assets/monuments.py

**Rôle** : les deux grands repères de la première moitié — le **crâne de démon cornu** sur sa colline (refBC1) et
la **tour aux grimoires** — plus les **côtes géantes** du démon dans les labours et la **montagne de la capitale**
au loin (refBC5). **Budget du module ≤ 1 900 pièces.** Vues de contrôle : `entree`, `village`, `crane`, `tour`,
`aerienne`, `cote`.

### `colline_crane(b, variant=0, largeur=110, profondeur=100, hauteur=28)` — ≤ 280 (arbres compris)
Pose : `(132, 0, -158)`, `yaw = 90` : X local (largeur 110) le long du couloir (z monde -213 → -103), Z local
(profondeur 100) vers l'extérieur (x monde 82 → 182), avant (-Z local) vers le couloir.
- **Colline boisée sombre** : 3 à 5 terrasses irrégulières de blocs à studs (`herbe_fonce`, `mousse`, `herbe`),
  affleurements de roche noire (`roche_noire`, `basalte`), contour en lobes et éperons (pas une pyramide), pente
  plus douce côté couloir, plus raide derrière. **Plateau sommital plat à y = hauteur** dans un rayon ≥ 26 autour de
  l'origine : le crâne y est posé par `zone.py` en `(132, hauteur, -158)`.
- 10 à 14 **sapins sombres et arbres morts** sur les flancs et l'arrière (`mobilier.sapin_sombre`,
  `mobilier.arbre_mort`, comptés dans ce budget), peu devant pour ne pas masquer le crâne ; 2-3 **os géants** qui
  percent les pentes (fragments `os_ombre`, `os_fonce`).
- Rien en `x monde < 80` (les maisons du village sont en x 55-69) ; renvoie `{"emprise": (largeur, profondeur),
  "hauteur": hauteur}` (la clé `hauteur` sert à poser le crâne).

### `crane_demon(b, variant=0, hauteur=64)` — ≤ 680
Pose : `(132, 28, -158)` (sur le plateau), `yaw = 125` : la face regarde (-0,82 ; 0 ; +0,57), vers le couloir et
l'entrée ; le soleil de jour l'éclaire de face.
- Origine : centre de l'emprise au niveau du plateau (y local 0) ; ne construire que ce qui est au-dessus de
  y = -2 (la **mâchoire inférieure est à moitié enterrée** dans la colline).
- **Crâne** de ≈ 56 de large (X local) × 52 de profondeur, sommet du crâne à `hauteur` (64) ; volume en **tranches
  horizontales** de blocs arrondis en gradins (10-14 tranches), pas une boule lisse. Os `os`, `os_clair` (reflets),
  `os_ombre`, `os_fonce`, noirci au ras de la colline (`os_brule`, voir `palette.os_teinte(t)`).
- **Face** (vers -Z local) : **deux orbites seulement**, grandes (≈ 14 × 12) et **profondes** (fond en retrait de 4 à
  6, `noir` / `obsidienne`) avec une **braise cramoisie** au fond de chacune (petit `lueur_cramoisie` Neon) ; cavité
  nasale en cœur renversé, en gradins ; pommettes ; mâchoire supérieure à grosses dents et **quatre longs crocs**
  (coins, `os_clair`), certains cassés ; la rangée de dents inférieures dépasse à peine de la colline, de travers.
  **Front fissuré, sans troisième orbite.**
- **Cornes** : deux énormes cornes qui partent des tempes (x local ≈ ±24, y ≈ 48), s'écartent puis montent en se
  recourbant légèrement vers l'avant (refBC1) : 6 à 9 segments de blocs tendus de point à point, section de ≈ 9 à
  ≈ 2, pointes vers y ≈ 90-95 (≈ 120 monde) et x ≈ ±50 ; dégradé `os` → `os_ombre` → `os_fonce` vers la pointe,
  anneaux de croissance en saillie de 0,2. Deux ou trois **petites pointes** latérales par côté (tempes, joues).
- **Fissures** : 8 à 12 bandes `fissure` de 0,3 à 0,6 de large en saillie de 0,1-0,2 sur le crâne et autour des
  orbites ; quelques éclats plus sombres ; terre et mousse au pied.
- Au sommet du crâne : un **étendard cramoisi uni et déchiré** sur un mât d'environ 26 (toile ≈ 6 × 12,
  `toile_cramoisie`, bas en lambeaux) — **aucune statue, aucune figure**.
- Jour : l'ivoire claque contre la colline noire, les braises rougeoient dans les orbites. Crépuscule : arêtes et
  cornes en contre-jour, braises vives. Différent de l'arche-crâne beige de la zone One Piece : ici un crâne cornu,
  fissuré, de 3/4 sur une colline, qui n'enjambe rien.
- Renvoie `{"emprise": (≈ 110, ≈ 60), "hauteur": ≈ 95}`.

### `cotes_geantes(b, variant=0, longueur=56, hauteur=36)` — ≤ 170
Pose : `(118, 0, -70)`, `yaw = 110` : l'échine (X local) court presque le long du couloir, l'avant regarde le
couloir et l'entrée.
- La **cage thoracique** du démon qui sort des labours : échine à demi enterrée le long de X local (7-9 vertèbres,
  apophyses en pointe, dessus à 3-6), 5 ou 6 **paires de côtes** énormes qui montent des deux côtés (±Z local) et se
  recourbent vers l'intérieur sans se rejoindre, les plus hautes au milieu (`hauteur`), plus courtes aux bouts
  (≈ 18) ; quelques côtes cassées ; os ivoire en haut, `os_fonce` puis `os_brule` vers le sol ; buttes de terre
  (`labour`, `terre_fonce`) au pied des côtes.
- Emprise : `longueur` × ≈ 36 ; en monde, x ≈ 100 → 136 : rien en `x < 70`. Variantes : 0 (posée) ; 1 plus petite et
  plus enterrée.
- Renvoie `{"emprise": (longueur, 36), "hauteur": hauteur}`.

### `tour_grimoires(b, variant=0, rayon=16, hauteur=118)` — ≤ 620

*Finition* : corps et balcon fixés à 80 (baies et cordons calés sur 80 / 0,68), toit en aiguille jusqu'à `hauteur`
(zone.py : 138), planche GRIMOIRES sur deux potences, grimoires sortant des baies en repère direct.
Pose : `(-94, 0, -250)`, `yaw = -90` : la porte regarde la placette et le couloir (+X monde).
- **Tour ronde** de pierre, **la plus claire du bourg** (`pierre_claire`, `pierre_pale`, `pierre`, en assises) :
  talus (rayon + 1,5), corps Ø 32 jusqu'à ≈ 92 (léger fruit, ou trois étages séparés de cordons `pierre_pale` vers
  30, 60, 90), **hautes baies en arc** (2 × 8) en quinconce, **lumineuses** (`lueur_doree` ou `lueur_bougie` Neon,
  quelques-unes `lueur_violette`), **grande porte en arc** au pied (6 × 10, bois sombre clouté) surmontée d'une
  planche « GRIMOIRES » (label `serif`, `dorure` sur `bois_fonce`), couronne de mâchicoulis et balcon à ≈ 92,
  **toit conique très élancé** d'ardoise violette (anneaux de cylindres du rayon 18 jusqu'à la pointe, à `hauteur`),
  épi doré ; une ou deux échauguettes à toit conique.
- **Spirale de grimoires** (magie voulue, alignée sur la tour) : 36 à 48 livres ouverts en V (3 pièces chacun :
  deux couvertures + bloc de pages ; `from assets.mobilier import _livre` est permis), couvertures unies `cuir_rouge`,
  `cuir_bleu`, `cuir_vert`, `cuir_violet`, `cuir_brun`, `cuir_noir`, pages `page` / `page_ombre`, **un sur quatre à
  pages lumineuses** (`lueur_doree` Neon) ; 1,5 à 2 tours d'hélice de y ≈ 12 à y ≈ 100, à `rayon + 4` à `rayon + 8`
  de l'axe (jamais au-delà de 24), orientés le long de l'hélice, légèrement penchés ; 4 à 6 livres qui **sortent des
  fenêtres** (à moitié dans l'embrasure) ; ≤ 16 lucioles dorées le long de la spirale.
- Couvertures sans aucun motif (au plus une bande ou des coins `dorure`) : jamais de trèfle, d'étoile ni de copie
  d'une couverture de la licence.
- Tout reste à moins de 24 de l'axe (x monde ≤ -70). Jour : la tour pâle se détache du bourg sombre ; crépuscule :
  baies et pages brillent. Renvoie `{"emprise": (48, 48), "hauteur": hauteur}`.

### `montagne_capitale(b, variant=0, largeur=70, hauteur=96)` — ≤ 150
Pose : `(-200, 0, -112)`, `yaw = -90` (emprise monde x -165 → -235, z -77 → -147).
- La **capitale du royaume au loin** (refBC5) : montagne rocheuse escarpée en gradins irréguliers (6-9 étages qui
  rétrécissent, une face plus raide en falaise), plateau sommital vers 78-80 coiffé d'un **petit château clair**
  (murs, 3-5 tours à toits pointus bleu-gris, un donjon : ≈ 18 de haut, sommet ≈ `hauteur`). Couleurs de
  **lointain** (`lointain`, `lointain_clair`, `lointain_fonce`) pour la roche, `chateau_royal` et `toit_royal`
  pour le château, quelques sapins `sapin_fonce` au pied. Grands plans, peu de détails, pas de Neon (2-3 fenêtres
  chaudes au plus) : une silhouette lointaine. Renvoie `{"emprise": (largeur, largeur), "hauteur": hauteur}`.

**IP propre à ce module** : crâne à deux orbites, **aucune statue ni figure** sur le crâne, étendard uni ; tour
sans nom ; grimoires unis ; aucun trèfle. **À éviter** : un crâne de pirate (zone One Piece), une tour de château
de conte (la tour reste massive, de pierre, avec sa spirale de livres).

---

## assets/abime.py

**Rôle** : le royaume démoniaque de la fin de course — le **château démoniaque** gothique noir sur sa falaise,
repère final et sortie (refBC3) —, l'**arbre démoniaque** colossal, les **îlots flottants** enchaînés, les
**falaises noires** latérales, les **obélisques** de la place rituelle, les **racines géantes** et les **cristaux**.
Palette : `chateau`, `chateau_clair`, `chateau_arete` (arêtes, merlons), `obsidienne` (creux, arêtes les plus
noires), `basalte`, `basalte_clair`, `roche_noire`, `roche_violette` (`roche(rng)`), `racine`, `racine_claire`,
`epine`, `cramoisi`, `cramoisi_fonce`, `violet_profond`, `pourpre` ; lueurs Neon `lueur_violette`,
`lueur_violette_pale`, `lueur_cramoisie`, `cristal` (et `cristal_fonce` non lumineux), `feu_violet`,
`feu_cramoisi`. **Budget du module ≤ 2 778 pièces.** Vues de contrôle : `place`, `final`, `aerienne`, `cote`,
`final --ambiance crepuscule`.

### `chateau_demon(b, variant=0, largeur=478, profondeur=50, ouverture=100, h_passage=40)` — ≤ 1 150
Pose : `(0, 0, -523)`, `yaw = 180` : -Z local regarde les arrivants (+Z monde) ; z local de -25 (façade, z monde
-498) à +25 (revers, z monde -548). Le tunnel traverse tout, `|x| < ouverture/2 = 50`.
- **Falaise** de basalte sur toute la largeur (`|x| ≤ 239`), 20 à 46 de haut : masses irrégulières en ressauts,
  éperons, pans inclinés (coins), corniches à studs ; **aucune grande face plane** ; 6 à 10 grappes de **cristaux
  violets** dans les failles, racines noires qui en sortent, un ou deux arbres morts sur les corniches. Vers les
  bords (`|x| > 150`) elle descend vers 20 et rejoint les falaises latérales (z -420 → -496).
- **Porte** : ouverture de 100, **montants verticaux jusqu'à `h_passage` = 40**, puis **arc brisé** en gradins
  jusqu'à ≈ 66 ; voussures `chateau` / `chateau_arete` alternées, clé lisse (aucun emblème) ; **herse** de fer
  (`fer_fonce`) relevée dans l'arc (bas ≥ 42) ; deux **tours de porte** octogonales ou rondes (`|x|` 50 → 68)
  jusqu'à ≈ 100, **flèches** aiguës jusqu'à ≈ 120 (gradins ou coins), archères cramoisies ; bannières `cramoisi`
  unies au-dessus de 40.
- **Château** : **donjon** central en retrait (z local 0 → +25, ≈ 40 de large) jusqu'à ≈ 110, la **plus haute flèche**
  (≈ 150) avec pinacles ; ailes et tourelles qui descendent en gradins sur la falaise (`|x|` 70 → 150, flèches de 70
  à 100) ; **contreforts** et pinacles, chemins de ronde crénelés, **fenêtres lancéolées violettes** (Neon, de 1 × 4 à
  2 × 8) à tous les niveaux, quelques **oculi cramoisis** ronds et simples (**pas de quadrilobe**), pointes en coins
  aux angles (comme des gargouilles stylisées, sans visage). Silhouette en dents de scie verticales (refBC3).
- **Tunnel** : parois de pierre noire, plafond ≥ 40 partout au-dessus de `|x| < 50` (plat ou en berceau brisé),
  `mobilier.lanterne_murale(variant=1)` (violettes) sur les parois. **Pas de sol** (zone.py peint le basalte et deux
  fils de lumière cramoisie en `|x|` 6-8). Revers (+Z local) plus simple : falaise, bouche du tunnel, quelques fenêtres.
- Règles : rien sous y = 40 au-dessus de `|x| < 50` ; montants en `|x| ≥ 50` ; sortie ouverte en z = -548 ; rien
  au-delà de z monde -548 ni en avant de -496 (la place rituelle).
- Jour : forteresse noire hérissée, fenêtres violettes, bannières cramoisies ; crépuscule (soleil bas derrière) :
  silhouette noire découpée sur le ciel cramoisi, fenêtres vives. Renvoie `{"emprise": (largeur, profondeur),
  "hauteur": ≈ 150}`.

### `arbre_demon(b, variant=0, hauteur=150)` — ≤ 420

*Finition* : tronc de Ø ≈ 30 au pied, quatre longues griffes basses vers le couloir (pointes à 55-62 de l'axe) d'où
pendent des vrilles, veine violette continue sur la face du tronc tournée vers le couloir et sous les griffes.
Pose : `(150, 0, -462)`, `yaw = 90` (l'avant regarde le couloir).
- **Arbre noir colossal** : tronc de 3 ou 4 brins **torsadés** (blocs `racine`, `racine_claire`, `obsidienne` tendus
  de point à point, rotation progressive) de Ø ≈ 20 à la base à ≈ 8 vers 80, puis 4 à 6 maîtresses branches en
  **griffes** (4-6 segments qui s'affinent, rameaux) jusqu'à `hauteur` ; 6 à 8 **racines** qui sortent du sol en arcs
  et y replongent, dans un rayon ≤ 34 de l'axe (x monde ≥ 116, z monde -428 → -496).
- **Lueurs** : 10 à 16 **veines violettes** (`lueur_violette` Neon, 0,3-0,5 de large, en saillie de 0,1) le long du
  tronc et des branches, un **cœur cramoisi** dans un creux du tronc vers 20 (`cramoisi` / `lueur_cramoisie` Neon),
  quelques **cosses cramoisies** pendues aux branches (boules Neon accrochées par une tige). Feuillage rare (touffes
  `violet_profond`, `pourpre` au bout de quelques rameaux) ou aucun.
- Houppier dans un rayon ≤ 55 de l'axe ; rien au-dessus du couloir (`x < 46`) ; sous y = 70, rester dans un rayon de
  50 (l'îlot flottant de droite est en (104, 60, -414)).
- Renvoie `{"emprise": (68, 68), "hauteur": hauteur}`.

### `ilot_flottant(b, variant=0, taille=14, ancres=())` — ≤ 95 (chaîne comprise)

*Finition* : grand cône renversé et deux ou trois cônes secondaires décalés, racines qui pendent, cristaux ; zone.py
pose quatre îlots de 22 à 30 entre 90 et 125 de haut, chacun avec une ancre sur le dessus d'une falaise (chaîne en
biais, maillons allongés au-delà de 90 de long).
Poses (`yaw = 0`, ancres = décalages alignés sur le monde, de l'origine vers un point au sol) :
`(-92, 46, -428)` t 14, ancres `((12, -46, -8), (-16, -46, -4))` v0 ; `(-136, 66, -466)` t 18,
`((6, -66, -14), (-16, -66, 4))` v1 ; `(-98, 78, -490)` t 12, `((-6, -78, 10),)` v2 ; `(104, 60, -414)` t 12,
`((-18, -60, 6),)` v3.
- **Origine au centre du dessus** de l'îlot (y local 0 = dessus). Dessus presque plat (`taille` × ≈ 0,8 `taille`,
  studs, herbe grise, cendre ou roche), **cône renversé** de roche noire en 4-6 gradins qui rétrécissent vers le bas
  (profondeur ≈ 0,8 × `taille`, pointe en bas), 2-4 **cristaux violets** (Neon) pendus sous la roche, un arbre mort,
  un fragment de colonne ou un petit obélisque sur le dessus selon la variante.
- **Chaînes** : pour chaque ancre, un anneau de fer sous le bord de l'îlot (du côté de l'ancre) et une chaîne
  (`mobilier.chaine(b, p0, p1, maillon=3.0, epaisseur=0.4)`, ≈ 15-26 maillons) jusqu'à un **ancrage au sol** au point
  d'ancre (bloc de pierre noire 2,5 × 1,5 × 2,5 avec anneau de fer et un petit glyphe violet). Les îlots flottent par
  magie : ils doivent se lire comme tenus en laisse, pas comme des pièces perdues.
- Renvoie `{"emprise": (taille, taille), "hauteur": 0.8 * taille}`.

### `falaise(b, variant=0, longueur=60, profondeur=50, hauteur=48)` — ≤ 14 + longueur
Poses `(x, z, longueur, profondeur, hauteur, yaw)` : `(-205, -330, 60, 50, 34, -90)`, `(-205, -390, 60, 50, 48, -90)`,
`(-205, -455, 70, 50, 62, -90)`, `(205, -330, 60, 50, 34, 90)`, `(205, -390, 60, 50, 46, 90)`,
`(215, -458, 76, 40, 58, 90)` ; variante = rang % 4.
- Falaise noire le long de X local (le long du couloir une fois posée), face avant (z local `-profondeur/2`, côté
  couloir) en ressauts : terrasses qui montent vers l'arrière jusqu'à `hauteur`, crête irrégulière (pics et
  encoches), basalte en pixels (`roche(rng)`), corniches à studs, 2-4 **grappes de cristaux violets** (Neon),
  racines noires, un arbre mort sur une corniche (`mobilier.arbre_mort`), éventuellement une grotte à lueur violette.
  Les segments se suivent bout à bout (hauteurs voisines aux jonctions) ; l'aqueduc (z -352) s'enfonce dans les
  premiers segments (contact voulu : on peut lui ménager une encoche).
- Renvoie `{"emprise": (longueur, profondeur), "hauteur": hauteur}`.

### `obelisque(b, variant=0, hauteur=16)` — ≤ 26

*Finition* : fût et socle épaissis avec la hauteur, coupe et flammes × 1,5 au-delà de 22 (zone.py : 28).
Poses : `(-53, -418)` v0, `(53, -418)` v1, `(-58, -448)` v2, `(58, -448)` v0, `(-53, -478)` v1, `(53, -478)` v2 ;
`yaw = face_couloir(x)`.
- Obélisque noir : socle en deux gradins (≤ 5 × 5 : rien en `|x| < 50`), fût effilé (`obsidienne`, `chateau`, de
  2,2 à 1,4), pyramidion (4 coins) ou coupe de fer à **flammes** (`feu_violet` / `lueur_violette_pale` ; v1 :
  `feu_cramoisi`), bande de 3-5 **glyphes abstraits** lumineux (`lueur_violette` ou `lueur_cramoisie` Neon) en
  saillie de 0,1, une fissure. Hauteur totale ≈ `hauteur` + 3. Renvoie `{"emprise": (5, 5), "hauteur": hauteur + 3}`.

### `racine_geante(b, variant=0, longueur=24, hauteur=10)` — ≤ 30
Poses `(x, z, yaw, variante)` : `(-78, -412, 30, 0)`, `(82, -424, -20, 1)`, `(-88, -470, 75, 2)`, `(-70, -494, 5, 3)`,
`(96, -486, -60, 0)`, `(-120, -440, 100, 1)`.
- Racine démoniaque noire qui sort du sol en un ou deux **arcs** le long de X local (segments de blocs en courbe, du
  sol jusqu'à `hauteur` puis de nouveau dans le sol, section ≈ 3 → 1,5), **épines** (`epine`), une **veine violette**
  (Neon) sur le dessus, terre retournée aux deux bouts (`brulis`, `racine`). Emprise ≤ `longueur` × 6. Renvoie
  `{"emprise": (longueur, 6), "hauteur": hauteur}`.

### `cristaux(b, variant=0, taille=6)` — ≤ 14
Poses : `(-100, -420)` v0, `(-124, -488)` v2, `(76, -452)` v1.
- Grappe de 4 à 6 prismes violets inclinés (blocs effilés par des coins), 2 ou 3 en `cristal` Neon, les autres en
  `cristal_fonce`, sur un socle de roche noire. Hauteur ≈ 1,2 × `taille`. Renvoie `{"emprise": (taille, taille),
  "hauteur": 1.2 * taille}`.

**Références** : refBC3 (château noir à flèches sur falaise, lumière violette d'orage), refBC4 (orbes et lueurs).
**IP propre à ce module** : arbre et château sans nom ; aucun emblème sur la clé de la porte ; aucun trèfle,
quadrilobe ni étoile dans les fenêtres, les glyphes ou les ferronneries ; aucune statue ni gargouille à visage
humain. **À éviter** : une muraille plate (zone Attaque des Titans) — le château se lit par ses verticales.
