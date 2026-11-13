# Fiches des modules (carte « île du futur », CarteEgghead)

Six constructeurs en parallèle, une fiche chacun ; chaque fiche se suffit à elle-même. À lire aussi :
`CONVENTIONS.md` (repère, studs, couleurs, budgets, pièges, propriété intellectuelle), `CONCEPTION.md` (intention et
composition), `OUTILS.md` (API du kit), `plan.py` (toutes les cotes), `palette.py` (couleurs et schémas de
variantes), et la bible `/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/eh/style/STYLE.md` (recettes T01-T18, K01-K07, M01-M21,
C01-C16, G01-G07 citées ci-dessous).

**Rappels valables pour toutes les fiches**
- Signature `f(b, variant=0, **params) -> dict` avec **exactement** les paramètres nommés de la fiche (on peut en
  ajouter, facultatifs). Retour : au moins `{"emprise": (x, z), "hauteur": h}` ; les tours ajoutent `"ame"`.
- Origine : centre de l'emprise au sol (y = 0), **avant vers -Z local**, largeur le long de X local. `carte.py` pose
  avec `b.at((x, y, z), yaw)`. Ne jamais poser de sol sous un asset (carte.py le fait).
- Couleurs : `palette.schema(<archétype>, variant)` (variante k = V(k+1) de la bible) ou `palette.c(nom)` ; tons
  dérivés `shade` / `mix` seulement. Neon : petites pièces, une seule couleur par bâtiment. Verre : isolé, contenu
  opaque. Aucun texte, logo, personnage, visage (hors deux hublots-yeux), marque.
- Studs sur tous les dessus plats (jamais murs, flancs, ellipsoïdes, Neon, Glass). Aucune face confondue
  (`kit.faces_confondues(b.parts)` vide), aucune moitié basse d'ellipsoïde visible, rien qui flotte par accident,
  toutes tailles ≥ 0,1, détails fins `collide=False`.
- **Mise à l'échelle des recettes de la bible** : sauf indication contraire, échelle horizontale
  `kx = diametre / D_recette` et verticale `ky = hauteur / H_recette` ; tous les rayons × kx, toutes les hauteurs × ky.
  Si `ky / kx > 1,6`, ne pas étirer les éléments répétés (galettes, bourrelets, pneus, rangs de damier, rayures) :
  garder leur épaisseur et leur pas × kx et **en ajouter** pour remplir la hauteur. Portes, marches et cadres de
  porte restent à l'échelle du personnage (porte 5 × 8 au pied) ; hublots et fentes × min(kx, 1,6).
- Couronne : tours vues surtout de 150 à 500 studs : silhouette en trois parties nette (socle → fût → coiffe plus
  large), gros détails sur la **moitié avant** (avant ± 70°) ; l'arrière peut rester en aplats.
- Contrôles : `PY apercu.py assets.<module>:<fonction> --variant N --params '{...}' --res 1200x675 --samples 12`
  (Read sur les PNG), au moins une vue lointaine (`--cam` à 250-400 studs), `kit.controles`, budgets. Un seul rendu
  Blender à la fois. Fichiers de travail dans `/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/eh/build/<module>/`.
- Images : références `/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/refs_eh/refEH3.png`, `refEH4.png` (canon des couleurs et du
  mobilier), `refEH5.png` (canon des silhouettes), planches et agrandissements
  `/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/eh/style/planche_batiments.png`, `planche_petits_batiments.png`,
  `planche_sol_ciel.png`, `crops/*.png`. Qualité visée : au moins celle des meilleurs assets des zones finies
  (`/home/user/-/roblox/zone-demon-slayer/rendus/`, `/home/user/-/roblox/zone-black-clover/rendus/`).

> **État final (livraison, 13/11).** Ces fiches sont la commande de départ ; le code livré s'en écarte ainsi
> (cotes dans `plan.py`) : plan du juge (pelouse 410 × 637, parcelles 110 × 102, bandes d'entrée 16 × 102, tapis à
> ±48,5 sans portails de tête) ; centre : stand 28 × 24 en (-16,5 ; 244,5) et zone de vente de rayon 20 centrée en
> (-15 ; 245), machine en (25 ; 240) sans tuyaux en J, monument en (0 ; 126) avec réplique à k 0,085, panneau des
> quêtes en (14 ; 151), podium Ø 38 en (0 ; 35,5), apparition en (0 ; 205) sans potelets, `centre.portail_anneau`
> en (0 ; -105), deux kiosques à dôme en (±29,5 ; -170,5) ; nouveau module `assets/esplanade.py` (`front_labo`,
> 118 de haut, écran abstrait ; `aire_nacelle`) ; `ciel.skyline_lointaine` (36 tours pâles, sans collision) ;
> fenêtre de l'œuf ≤ 125 ; tours en baie du rang 1 à 62-94 ; `Tours/Limites` et `Tours/FondsDeBaie` posés par
> carte.py ; `groupe_palmiers(..., portee=)` pour les petits palmiers de la bande arrière (±198 ; ±88).

---

## assets/tours_rondes.py

**Rôle** : les tours rondes de la couronne (rang 2), ses quatre repères d'angle et les tambours et fusées du front de
rue (rang 1). Neuf fonctions, 45 poses (20 tours et repères d'angle, 25 tambours et fusées du front de rue). **Budget du module ≤ 4 400 pièces, ≤ 400 Neon, ≤ 40 transparentes** (plafonds
par appel ci-dessous, `plan.BUDGET_FONCTION`). Images : planche B01-B17, crops `eh5_*.png`, `r5_left.png`,
`r5_right.png`, `r3_left.png`, `r3_right.png`, `eh3_*.png`, `eh4_r1.png`, `eh4_r2.png`.

**Règles communes aux tours de ce module**
- `diametre` = Ø maximal **au sol et jusqu'à 40 de haut** (la tour ne sort pas de ce disque sous y = 40) ; ce qui le
  dépasse plus haut (bords de chapeau, soucoupes, halos) est permis. `hauteur` = sommet de la coiffe (une antenne
  ou une flèche peut ajouter jusqu'à +10).
- `quai=None | float | list[float]` (galettes, champignon) : hauteurs où un **tube de verre** entre dans la tour
  (posé par carte.py, extrémité dans l'axe). À chaque quai, le fût reste **nu** sur ±6 (aucune galette, aucun halo),
  avec deux bagues `cyl R(ame + 0,8) · ép 1,2` à quai ± 4,5 dans la couleur `cadres` (ou `bagues`) du schéma.
- Retour : `{"emprise": (d, d), "hauteur": h, "ame": rayon_du_fut_plein, "sommet": y_max}`.
- Porte en arche au pied, côté avant (STYLE § 3.0) ; deux hublots-yeux sur les dômes quand la recette les prévoit.

### `tour_galettes(b, variant=0, hauteur=200, diametre=54, quai=None)` — ≤ 140 pièces, ≤ 40 Neon (T01)
Poses : `E-T-320` v0 H 200 Ø 54 quai [100, 150] · `E-T320` v3 H 190 Ø 54 quai [80] · `O-T-160` v1 H 210 Ø 54
quai [75] · `N-T-100` v2 **H 245 Ø 58** quai [70] (tour de la fenêtre de l'œuf, côté ouest).
- Recette T01 (H 96, galettes Ø 40) en version haute : socle `disque R 0,5D · ép 3` (studs) ; pied de 5 rayures
  `cyl R 0,37D` de y 3 à 0,12 H (couleurs `pied`) ; fût `cyl R_f = 0,34 D` de 0,12 H à 0,87 H (`fut`) ; galettes
  `ell D × 0,10 D × D` au pas de 0,20 D de 0,12 H + 0,1 D jusqu'à 0,84 H (≈ 12-14 galettes, `galettes`), le fût
  visible entre elles ; 3 fentes Neon (`neon`) sur la moitié avant d'**une galette sur deux**, alignées en colonnes ;
  bande de fentes sous le dôme ; dôme `b.dome` de rayon R_f + 0,3 et de hauteur 0,9 R_f, sommet à H (`dome`), deux
  yeux (cadres `cadres`, f ≈ 0,19 R_f) ; porte au pied ; antenne facultative.
- Variantes : `schema("tour_galettes", v)` : 0 soleil, 1 lagon, 2 bonbon, 3 marine.
- Critères : silhouette « pile de disques » lisible à 400 studs, galettes nettement détachées et régulières, dôme plus
  large que rien d'autre au sommet ; cheap = galettes collées ou en assiettes, Neon tout autour.

### `tour_champignon(b, variant=0, hauteur=170, diametre=56, quai=None)` — ≤ 110 (T02)
Poses : `O-T160` v2 H 170 Ø 56 quai [75] · `N-T-170` v3 H 165 Ø 54 quai [70] · `S-T80` v1 H 170 Ø 56 quai [80].
- Recette T02 (H 93, bord Ø 40) ; `diametre` = Ø du **bord** du chapeau ; tambour de base Ø 0,75 D (c'est lui
  l'emprise au sol, le bord est en hauteur), gradin à hublots, **pilier blanc fin** (R ≈ 0,11 D) de 0,34 H à 0,835 H,
  **halo plat** autour du pilier à 0,58 H (R ≈ 3,1 × pilier, sans le toucher), cloche crème sous le bord, bord rayé
  à 3 couches débordant, dôme à côtes (3 méridiens) et 4 hublots. Technique de la cloche obligatoire (STYLE § 3.0).
- Quai : sur le pilier entre 0,36 H et 0,52 H (sous le halo) ; bagues R pilier + 0,8.
- Variantes : 0 citron, 1 bonbon (base rouge à liseré blanc, sans texte), 2 lagon, 3 menthe.
- Critères : chapeau large et bien calé, pilier et halo isolés dans le vide, la tour lisible comme un champignon.

### `tour_soucoupe(b, variant=0, hauteur=150, diametre=56)` — ≤ 100, ≤ 14 Neon, ≤ 1 verre (T08)
Poses : `E-T80` v1 H 160 Ø 56 · `O-T-320` v0 H 170 Ø 56 · `N-T240` v3 H 150 Ø 48 · **`Coin_SO` v2 H 230 Ø 70**
(repère d'angle sud-ouest, avant vers le centre).
- Recette T08 (H 119, pied Ø 56) : pied à studs, gros corps à rainures et deux fenêtres en boîte arrondie, porte,
  large corniche, plateau (avec une **coupole de verre à miniature** M16 à la place des lettres de l'anime), tige,
  gobelet (cloche) sous l'épaisse soucoupe à 10 fentes Neon, dôme, antenne à disque et boule.
- La soucoupe peut atteindre 1,3 D (au-dessus de y 40). Au coin SO (H 230), soucoupe Ø ≈ 90 à y ≈ 185 : la plus
  spectaculaire de la carte.
- Variantes : 0 EH4 (corps turquoise foncé `turquoise*0.78`), 1 coucher, 2 fraise, 3 neige.

### `tour_tete_boule(b, variant=0, hauteur=150, diametre=42)` — ≤ 100 (T03)
Poses : `E-T160` v2 H 150 Ø 42 · `S-T-240` v1 H 150 Ø 42 · **`O-T0` v0 H 215 Ø 50** (repère du milieu ouest,
posé à d = 27 : son pied touche la rue ; avant vers la pelouse).
- Recette T03 (H 100, base Ø 30) : tambour à porte et 4 hublots, balcon à studs (poteaux, bande vitrée opaque, main
  courante), **grand cône rayé** (12 à 14 rayures égales, `cone`), col, **halo octogonal** (`anneau n=8`) plus large
  que le cône, tête sphérique et menton, deux yeux à l'équateur.
- Variantes : 0 phare (bleu nuit et citron, base orange, balcon rouge), 1 sucre d'orge, 2 lagune, 3 anime.
- Critères : tête proportionnée (≈ 0,7 × le diamètre du cône), halo bien détaché du col.

### `tour_pneus(b, variant=0, hauteur=240, diametre=72)` — ≤ 220, ≤ 40 Neon (T07)
Poses : **`Coin_NO` v0 H 240 Ø 72** · **`Coin_SE` v1 H 230 Ø 70** (repères d'angle).
- Recette T07 (H 111, pneus Ø 62) en version haute : socle blanc à porte et plinthe, âme continue, **9 pneus**
  (épaisseur ≈ 10 kx, Ø décroissant de D à 0,9 D) séparés de bandes à hublots allumés / vitrées à meneaux (moitié
  avant), dôme à hublots et méridiens, flèche dorée, **halo incliné** au-dessus, 2-3 anneaux verticaux accrochés aux
  flancs (tangents aux pneus).
- Variantes : 0 EH3 (bleu roi, bandes turquoise, anneaux orange), 1 rouille (orange, crème, dôme bleu roi).

### `tour_ruban(b, variant=0, hauteur=250, diametre=72)` — ≤ 200, ≤ 12 Neon (T10)
Pose : **`Coin_NE` v0 H 250 Ø 72** (repère d'angle nord-est, le plus haut de la carte).
- Recette T10 (H 125) : `diametre` = Ø du socle (tambour à porte, bande de fenêtres, corniche) ; colonne de
  **10 cylindres** dégradés (`colonne` : `mix(a, b, t)` en marches régulières) ; **chapeau géant** `ell ≈ 1,6 D (≤ 120)
  × 36 × …` à y ≈ 0,89 H avec dessous plus sombre (`shade(chapeau, 0,75)`) et 8 fenêtres Neon sur le bord ;
  **ruban en hélice** continu (2 tours, 24 segments par tour, `ruban`) autour de la colonne ; petit épi au sommet.
- Le chapeau déborde du carré d'angle au-dessus des rues (y > 200) : voulu.
- Variantes : 0 EH3 (orange, lavande → citron, chapeau prune, ruban orange), 1, 2.

### `tour_bulbe(b, variant=0, hauteur=115, diametre=46)` — ≤ 60, ≤ 6 transparentes (T13)
Poses : `O-T-240` v3 H 115 · `N-T-240` v0 H 130 · `S-T-160` v1 H 115 (Ø 46).
- Recette T13 en version haute : tambour à porte `R 0,32 D` jusqu'à 0,3 H ; bague de col ; **bulbe en oignon**
  `ell D × 0,5 H × D` centré à 0,55 H (enfoncé de 2 dans le tambour) ; bague de taille (seul son bord dépasse) ;
  pointe `cône_étagé` de 0,8 H à 0,96 H + boule ; 4 hublots ; **cheminée** `R 0,06 D` de 0,6 H à 0,9 H à x = 0,3 D ;
  **fumée** : 6 boules qui grossissent et pâlissent (transparence 0,25 → 0,45) de 0,95 H à 1,35 H, dérivant.
- Variantes : 0 violet / lavande / or, 1 rose, 2 orange, 3 turquoise.

### `tour_fusee(b, variant=0, hauteur=55, diametre=20, type="blanche")` — ≤ 50, ≤ 1 Neon (T11)
Poses (rang 1, avant à 1 de la façade, dans une baie entre deux tours) : 16 poses, H 46-58, Ø 18-22 ; `type`
« blanche » (recette A : cône étagé blanc à bandes, pointe, 3 ailerons, hublot emblème) ou « capsule » (recette B :
corps à rainures et hublots, ogive à hublots, 4 ailerons). Ajouter un **socle rond à studs** (R D/2 + 1, ép 1) et
une petite porte au pied (le joueur passe à côté). Variantes : 0 blanc et orange, 1 vert pomme et citron, 2 rouge et
blanc, 3 bleu roi et jaune d'or.

### `tour_hublots(b, variant=0, hauteur=42, diametre=30)` — ≤ 60, ≤ 6 Neon (T16, « cylindre à hublots »)
Poses (rang 1, baies) : 9 poses, H 36-44, Ø 22-30.
- Recette T16 : tambour, toit à studs débordant, petit dôme ; variantes 0 et 2 : **3 bandes vitrées** opaques à
  meneaux (moitié avant) ; variantes 1 et 3 : **3 rangs de hublots** (5 par rang sur la moitié avant, cadres épais).
  Porte en arche à l'avant, socle à studs. Variantes : 0 orange et turquoise, 1 rose et blanc, 2 jaune d'or et bleu
  roi, 3 blanc et violet.

**Livrer** : rapport par fonction et par variante (pièces, Neon, transparentes, emprise, hauteur, `ame`) ; 3-4 aperçus
dont une vue lointaine de la ligne des tours (posées côte à côte à 80 d'écart) ; les quais rendus avec un tube d'essai.

---

## assets/tours_formes.py

**Rôle** : les tours « de formes » du rang 2 (manette, cône à étoile, bouteille à damier, tours à bourrelets, tour de
bureaux, plateau à disques, tour à anneau) et **tout le front de rue** non rond : boutiques à arche, kiosques et
connecteurs bas qui ferment la couronne. Dix fonctions, 116 poses. **Budget ≤ 5 200 pièces, ≤ 450 Neon, ≤ 30
transparentes.** Images : planche B01-B17 et P01-P08, crops `eh5_boutique_z.png`, `eh5_kiosque_z.png`,
`eh4_kiosque_z.png`, `eh4_console_z.png`, `eh5_c.png`, `eh5_d.png`, `eh4_boxes*.png`, `eh5_boxes*.png`.

Règles communes des tours (`diametre`, `hauteur`, `quai`, retour avec `"ame"`) : comme `tours_rondes.py`.
Front de rue : chaque fonction **remplit exactement** `largeur × profondeur` (avant sur la ligne des façades à
z local = -profondeur/2), sans rien devant (d < 0) sauf enseignes plates de moins de 1,5 de saillie au-dessus de
y = 8 ; toits plats à studs ; le côté ne laisse pas voir de vide (fermé jusqu'au fond de l'emprise).

### `tour_manette(b, variant=0, hauteur=195, diametre=48, largeur_manette=72)` — ≤ 160, ≤ 8 Neon (T04)
Pose : **`E-T0` v1** (repère du milieu est, d = 26, pied à la rue, avant vers la pelouse) : la **tour à
enseigne-manette violette** sur tambour turquoise.
- Version haute de T04 : socle rond à grande porte en arche (8 × 12) et colonnade (bagues + 16 poteaux) jusqu'à
  0,14 H ; **tambour** `R D/2` jusqu'à 0,72 H avec 3 bandes de grands hublots cerclés (`cadres`) sur la moitié avant ;
  rebord ; **deux pieds** visibles ; **manette** en boîte arrondie `largeur_manette × 0,45 largeur × 12` centrée à
  0,87 H, façade plus claire (`facade`) à l'avant : croix directionnelle, 4 boutons ronds en losange (une seule
  couleur `boutons`, jamais les quatre couleurs d'une marque), panneau central à 2 fentes Neon, 6 évents sur la
  tranche haute ; petite antenne ou rotor au sommet (≤ H).
- Variantes : 0 console (bleu roi / magenta), **1 menthe (turquoise / violet)**, 2 cerise (blanc / rouge).
- Critères : manette plus large que le tambour, coins arrondis, lisible de la pelouse (300 studs) ; pas de logo.

### `cone_etoile(b, variant=0, hauteur=130, diametre=40)` — ≤ 70 (T15)
Poses : `E-T-160` v0 H 130 · `O-T320` v3 H 135 · `S-T240` v2 H 140 (Ø 40).
- Recette T15 (H 60, Ø 22) : socle foncé, **cône rayé** de 14 rayures, **anneau** incliné de 8° à 0,33 H
  (`anneau`, n 32, bien détaché du cône : écart ≥ 6), tige, **étoile à 5 rayons** dorée (5 blocs + boule) face à la
  carte, au sommet. Variantes : 0 rouge / orange / or, 1 bleu nuit / citron / or, 2 violet / turquoise / citron,
  3 turquoise et blanc / rouge / or.

### `tour_damier(b, variant=0, hauteur=170, diametre=44)` — ≤ 140, ≤ 8 Neon (T06)
Poses : `E-T240` v0 H 170 Ø 44 · `N-T170` v2 H 165 Ø 44 · **`S-T0` v1 H 215 Ø 52** (repère du milieu sud,
d = 28 : la bouteille à damier rouge et blanc).
- Recette T06 : socle à studs, corps à **damier** (plaques carrées de 8 kx tangentes à un dodécagone, une facette
  sur deux, rangs décalés de 30°, 7-10 rangs), épaule bombée cannelée, col, disque, tête-soucoupe lenticulaire à
  filet et 6 feux Neon dans des cadres, antenne à disque et boule. Variantes : 0 citron-pomme, 1 fraise, 2 raisin,
  3 lagon.

### `tour_bourrelets(b, variant=0, hauteur=160, diametre=44, quai=None)` — ≤ 120, ≤ 40 Neon (T05)
Poses : `E-T-240` v3 H 150 Ø 44 quai [100] · `O-T240` v1 H 150 Ø 42 · **`N-T100` v0 H 240 Ø 52** quai [150]
(tour de la fenêtre de l'œuf, côté est).
- Variantes 0, 2, 3 : recette A (fût, pied rayé, bourrelets `ell` épais régulièrement espacés, 2-3 pilules Neon par
  bourrelet sur la moitié avant, dôme à yeux, porte). Variante 1 : recette B (fût indigo, disques violets à liseré
  Neon cyan de 0,2 qui dépasse seul, dôme lavande, un œil sombre). Bourrelets au pas et à l'épaisseur × kx, en
  nombre pour remplir la hauteur. Quai : fût nu ± 6 et deux bagues.

### `tour_bureaux(b, variant=0, hauteur=180, largeur=34, quai=None)` — ≤ 100, ≤ 6 Neon (T12, « tour à gradins »)
Poses : `E-T-80` v3 H 180 · `O-T80` v0 H 185 quai [75] · `S-T-80` v2 H 175 (largeur 34 ; emprise = cercle de Ø 34
pour la vérification : coins arrondis R ≥ 4).
- T12 en **trois gradins** : corps bas en boîte arrondie `largeur × 0,5 H`, corps haut `(largeur − 8)` jusqu'à
  0,84 H, cabine ronde vitrée, corniche, dôme à 3 fentes et un œil ; bandes vitrées opaques (`bandes`) tous les ≈ 9
  sur les faces avant et latérales, bande verticale latérale à petites fenêtres. Quai : bandeau nu ± 6, cadre en
  boîte arrondie à quai ± 4,5.

### `plateau_disques(b, variant=0, hauteur=75, diametre=56)` — ≤ 90, ≤ 12 Neon, ≤ 2 transparentes (T14)
Pose : **`N-T0` v0** H 75 Ø 56, **au centre de la fenêtre de l'œuf** (rien au-dessus de 80 : `plan.FENETRE_OEUF`).
- T14 : socle, mât blanc, 4 disques turquoise à studs de rayons nettement décroissants (0,5 / 0,41 / 0,31 / 0,22 D)
  avec sous-faces plus sombres, points Neon sur deux bords, boule au sommet ; **2 nacelles garées** posées sur les
  disques (recette C02 ou C03 simplifiée, 6-10 pièces, coque `jaune_citron` et `orange`, sans personne ; bulle en
  verre = 1 transparente chacune). Silhouette basse et large qui encadre l'axe sans cacher le nuage.

### `tour_anneau(b, variant=0, hauteur=125, diametre=40, quai=None)` — ≤ 55, ≤ 8 Neon (T17)
Poses : `O-T-80` v1 H 125 Ø 40 quai [75] · `S-T160` v3 H 125 Ø 40.
- T17 : fût lisse (deux fines bandes vitrées), **anneau épais et bombé** (`diametre` = Ø de l'anneau) à 8 fentes
  Neon, dôme dont le bas est caché par l'anneau, flèche rayée et mât à boule, porte en arche sombre. Fût étiré
  jusqu'à ≈ 0,66 H (il porte le quai).

### `boutique_arche(b, variant=0, largeur=30, profondeur=16, hauteur=28)` — ≤ 65, ≤ 4 Neon (K01)
14 poses (front de rue, devant les tours) : largeur 30, profondeur 16, H 26-28.
- K01 : façade en bloc aux arêtes avant arrondies, cadre épais, listel, **grande arche d'entrée** (porte
  `blanc_labo` à chevron rouge et rivets ; collision franche, la porte est fermée), plaque d'enseigne en gélule (M11)
  avec **pictogramme** (étoile, cœur, pièce, éclair, nuage : jamais de lettres), 2 × 3 petites fentes, panneau
  latéral et tuyau en J (M14), toit plat à studs avec petit acrotère. Remplit 30 × 16.
- Variantes : `schema("boutique_arche", v)` 0 magenta, 1 turquoise, 2 jaune d'or, 3 rose.

### `kiosque(b, variant=0, type="dome", largeur=26, profondeur=26, hauteur=24)` — ≤ 50, ≤ 6 Neon
21 poses. `type` :
- « **dome** » (K04, 6 poses, baies 34 × 28 ou 30 × 28) : socle carré arrondi `largeur × profondeur × 1` à studs,
  kiosque rond de Ø `profondeur − 2` (bord), tambour à fenêtres ovales, bord bombé, dôme à points et filets ;
  schéma `kiosque_dome`.
- « **boutons** » (K02, 3 poses, baies) : même socle, tambour rond couvert de 18 boutons ronds sur la moitié avant,
  panneau central à écran Neon, bandeau **sans texte**, chapeau ; schéma `kiosque_boutons`.
- « **arcade** » (K03, 8 poses, 30 × 14, H 22) : borne rectangulaire à toit en demi-cylindre, liserés, 6 fentes
  Neon « faux texte », panneau bas à croix ; si `largeur` > 24, ajouter à côté un petit présentoir (cubes empilés
  M17 ou parabole M15) pour remplir ; schéma `kiosque_arcade`.
- « **hublots** » (K07, 7 poses, 30 × 14, H 16) : **paire de tambours** « machine à laver » (Ø 12-13) à grand
  hublot avant et tuyaux en J, sur un socle commun, petit boîtier de commande entre les deux ; schéma
  `kiosque_hublots`.

### `connecteur(b, variant=0, largeur=8, profondeur=12, hauteur=16, couleur="lavande", accent="turquoise")` — ≤ 14 + 0,7 × largeur, ≤ 1 Neon
65 poses : 60 de 8 de large, 4 de 16 (bouts des côtés nord et sud), **la galerie de 78** sur l'axe nord
(`N-R1-13`, variante 0, blanc et violet, H 20, profondeur 14), et les 6 « ailes » (8 × 14, H 16) qui flanquent les
repères de milieu de côté. `couleur` et `accent` sont des noms de la palette (zone du côté).
- Toujours un volume fermé qui remplit `largeur × profondeur × hauteur`, toit plat à studs (légèrement débordant de
  0,3 à l'avant), collision franche.
- Variante 0 « **arcade** » : niches en arc plein cintre tous les 8 (fond `bleu_nuit` en retrait de 0,3, cadre
  `accent`), rangée de boules de haie sur le toit. Pour la galerie de 78 : 9 niches et, au centre, un **grand arc**
  (Ø 14) encadré de deux colonnes rayées qui marque l'axe vers l'œuf.
- Variante 1 « **rayé** » : mur `couleur` à deux bandeaux horizontaux `accent` / `blanc_labo`, hublots ronds tous
  les 8, jardinière de haie sur le toit.
- Variante 2 « **vitrine** » : bande vitrée opaque `hublot` à meneaux, auvent en demi-cylindre `accent` à 2/3 de la
  hauteur (saillie ≤ 1,5, dessous ≥ 8), pictogramme.
- Variante 3 « **portique** » : deux piliers carrés arrondis, linteau, petit dôme sur le dessus, fond fermé `bleu_nuit`
  avec un fin liseré Neon (`accent` si c'est une couleur Neon, sinon `cyan`).

**Liste des poses** : `plan.CEINTURE` (filtrer `module == "tours_formes"`), avec `variante` et `params`.
**Livrer** : rapport par fonction (pièces par variante, Neon, emprise, hauteur) ; un aperçu d'un tronçon de front de
rue (boutique + connecteur + kiosque + connecteur, posés jointifs) vu du trottoir et de 200 studs ; la manette vue de
la pelouse (≈ 300 studs).

---

## assets/ciel.py

**Rôle** : le repère du ciel (l'œuf-laboratoire fêlé sur son cumulus, avec cubes, anneau de données et bandes
lumineuses) et son câble, les nacelles volantes, les pièces d'or, un dirigeable-baleine générique, des cumulus
lointains. **Budget ≤ 1 300 pièces, ≤ 220 Neon, ≤ 60 transparentes.** Tout est `collide=False` (hors station
d'ancrage) et `shadow=False` pour le nuage et l'œuf. Images : `refEH5.png` (œuf en haut), crops `r5_egg.png`,
`r5_egg_zoom.png`, `eh4_sky_left.png`, `eh4_sky_mid.png`, `eh4_sky_right.png`, `r4_sky.png`, `eh4_anneaux.png`,
`eh5_pod_z.png`, planche `planche_sol_ciel.png` (C01-C07). Lire STYLE.md § 6 en entier.

### `oeuf_labo(b, variant=0, echelle=1.6)` — ≤ 320, ≤ 90 Neon, ≤ 4 transparentes (C01)
Pose (carte.py) : `plan.OEUF` → `b.at((0, 290, -900), yaw=180)` ; origine = **pied de la coquille** sur l'axe
(repère local y = 0 de la recette) ; avant (-Z local) vers la carte.
- Recette C01 de STYLE.md § 6.2 **× echelle** (k = 1,6 : coquille 240 × 320, nuage ≈ 608 × 200 × 480) : coquille en
  3 ellipsoïdes (`oeuf_violet`, `oeuf_mauve`, `oeuf_rose` : bandes violet 0-93 k, mauve 93-125 k, rose 125-168 k),
  intérieur `oeuf_interieur` au-dessus de la cassure, **grille Neon** `neon_violet` (4 méridiens, 3 parallèles),
  **14 dents** du zigzag (paires de coins, hauteurs irrégulières, penchées vers l'intérieur ; les plus hautes vers
  l'avant), **anneau de données** en 6 arcs de 50° incliné de 6° + 10 pixels, **16 cubes** en arc au-dessus (dont 2
  Neon `cyan`), **cumulus** (base ellipsoïde + 30 à 40 boules et ellipsoïdes `nuage` / `nuage_ombre`, bords nets,
  dessus vers y 40 k où la coquille est enfoncée), **2 bandes lumineuses** autour du nuage (anneaux plats en arcs
  interrompus, l'un en Neon `cyan`, l'autre `bleu_roi` à pixels Neon ; n 40 au plus).
- Retour : `{"emprise": (≈ 608, ≈ 480), "hauteur": 200 k, "nuage_bas": ≈ -55 k, "nuage_haut": ≈ 40 k, "oeuf_haut": 200 k}`
  (local).
- Critères (vues `ciel`, `oeuf`, `joueur`) : on lit d'abord un œuf rose-lavande à fond violet, cassé en zigzag sur un
  intérieur sombre quadrillé de lumière, posé sur un gros nuage blanc ; pas de pixel de nuage gris sale ; aucune
  moitié basse visible ; rien d'écrit.

### `cable(b, variant=0, depart=(-80, 216, -760), arrivee=(-80, 0, -560))` — ≤ 22, ≤ 8 Neon
Coordonnées **de la carte** (carte.py appelle avec `b.at((0, 0, 0))` et `plan.CABLE`). `cyl_entre` R 1 `blanc_labo`
du dessous du nuage à une **station d'ancrage** posée sur son propre socle au sol (dalle 24 × 24 à studs
`sol_vert_clair`, tambour R 3 × 6, bague, balise Neon), + 7 perles Neon (`neon_blanc` et `rouge`) tous les 40.

### `nacelle(b, variant=0, rayon=7, inclinaison=6, couleur=None)` — ≤ 12, ≤ 1 Neon, ≤ 1 verre
18 poses (`plan.NACELLES` : position, yaw = cap, rayon). Origine = centre de la nacelle ; avant (-Z local) = sens de
la marche ; inclinée de `inclinaison` vers l'avant. Variante 0 : bol bleu à bulle (C02) ; 1 : toupie (C03) ;
2 : blanche et orange à coupole (C16). Échelle `rayon / 7`. `couleur` (nom de palette, facultatif) remplace la
couleur de coque. Bulle de verre vide (**personne** dedans : siège et console seulement), halo Neon `cyan` sous le
plot. Jamais deux voisines identiques (carte.py alterne les variantes).

### `piece_or(b, variant=0, rayon=6)` — 2 pièces (M18)
33 poses (`plan.PIECES_OR` : position, yaw qui oriente l'axe X local le long de la ligne). Disque `or` R `rayon`
ép 1,6 d'axe **Z local** + face centrale `or_fonce` R 0,75 rayon ép 1,8 (saillie de 0,1 de chaque côté). Variante 1 :
face centrale ornée d'une petite étoile en relief (≤ 8 pièces) pour une pièce sur quatre.

### `dirigeable(b, variant=0, longueur=90)` — ≤ 60, ≤ 6 Neon
Pose : `plan.DIRIGEABLE` (au-delà de la couronne sud, y 235, cap à l'est). Ballon en forme de **baleine générique**,
opaque : corps `bleu_roi` dessus / `blanc_labo` ventre (deux ellipsoïdes décalés), tête arrondie, pédoncule,
nageoire caudale à deux lobes, deux pectorales, rangée de hublots (`hublot`) sur le flanc, nacelle en boîte arrondie
sous le ventre, deux petites hélices `orange`, 4-6 feux Neon `cyan`. **Ni œil, ni bouche, ni cicatrice**, rien qui
rappelle un personnage ou un navire de la licence. Avant (-Z local) = la tête.

### `cumulus(b, variant=0, largeur=220)` — ≤ 30
3 poses (`plan.CUMULUS`). 20 à 28 boules et ellipsoïdes, `nuage` dessus, `nuage_ombre` dessous, dessous presque
plat, `varier(c, b.rng, 0,03)` permis. Emprise ≈ largeur × 0,6 largeur, hauteur ≈ 0,35 largeur.

**Livrer** : rapport (pièces, Neon, transparentes par fonction) ; aperçus de l'œuf seul (de face et de 3/4), d'une file
de 3 nacelles, d'une ligne de pièces, du dirigeable ; les angles vus depuis l'apparition sont dans CONCEPTION.md § 3.2.

---

## assets/tapis.py + assets/centre.py

**Un constructeur, deux fichiers.** `tapis.py` : le tapis roulant **exactement sur la géométrie de `plan.py`** et les
deux portails ; `centre.py` : les pièces de jeu du U. **Budget ≤ 1 400 pièces, ≤ 160 Neon, ≤ 12 transparentes.**
Images : `refEH1.png`, `refEH2.png`, crops de l'analyste A
`/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/eh/plan/A/crops/` (`chevrons.png`, `e1_chevL_x3.png`, `e1_chevR_x3.png`,
`e1_curb_x5.png`, `e1_stallbase_x4.png`, `e1_machbase_x6.png`, `e1_shrine_x4.png`, `e1_loopend.png`), STYLE.md § 8.2
(G01, G02, G03, G06, G07).

### tapis.py — `tapis(b, variant=0)` — ≤ 480, ≤ 40 Neon
Construit en **coordonnées de la carte** (carte.py appelle `with b.at((0, 0, 0), group="Tapis")`).
- Géométrie : `plan.tapis_bandes()` donne, pour les 7 tronçons (`Voie_Ouest`, `Virage_O1`, `Virage_O2`,
  `Virage_Sud`, `Virage_E2`, `Virage_E1`, `Voie_Est`), les **quadrilatères exacts** (onglets aux joints) de la bordure
  intérieure, de la bande et de la bordure extérieure ; ils reproduisent les polygones mesurés du demi-tour au
  1/10 de stud. Chaque quadrilatère = un bloc (partie rectangulaire) + un **coin posé à plat** (triangle rectangle,
  `b.part("wedge", …)` tourné pour que ses faces triangulaires soient horizontales ; studs sur la face du dessus) à
  chaque bout biseauté. Les voies droites vont de z = -293 (sous les portails) au début du demi-tour.
- Bande : `bleu_nuit`, de y 0 à **0,6** (`plan.TAPIS_DESSUS`), studs. Bordures : `blanc_labo`, de 0 à **1,0**, studs,
  avec sur leur arête côté bande un **liseré Neon `cyan`** (0,3 × 0,15, posé sur la bordure, `collide=False`) : un
  par tronçon et par côté (14). Deux tronçons voisins n'ont jamais leurs dessus au même niveau là où ils se touchent
  (décaler de 0,02 un tronçon sur deux).
- **Chevrons** : `plan.chevrons()` (141 poses : pointe du « V » en (x, z), yaw = sens du flux) ; chaque chevron =
  2 bras `blanc_labo` de 1,2 × 0,1 × ≈ 5,7 en « V » (envergure 9, flèche 3,5, la pointe vers l'avant), dessus à 0,7,
  studs ; un bras 0,02 plus haut que l'autre (pas de face confondue à la pointe).
- Aucune arche ni rien au-dessus du tapis (caméra) ; aucun Neon au sol hors des liserés.
- Retour : `{"emprise": (112.86, ≈ 587), "hauteur": 1.0, "chevrons": 141}`.

> **Finition (13/11)** : `plan.PORTAILS` est vide (plan du juge : rien de haut sur les têtes du tapis) ; la fonction
> `tapis.portail` reste disponible mais n'est plus posée. Les repères `Parcelle_*` / `Entree_*` regardent le tapis
> (côté E yaw 90, côté W yaw 270 ; voir CONVENTIONS § 4).

### tapis.py — `portail(b, variant=0, largeur=30, profondeur=16, hauteur=36)` — ≤ 90, ≤ 12 Neon, ≤ 1 verre
Poses : `plan.PORTAILS` : `Portail_Ouest` (-48,38 ; -289) variante 0 (entrée : les objets apparaissent, Neon
`neon_violet`) et `Portail_Est` (48,38 ; -289) variante 1 (sortie, Neon `cyan`), **yaw 180** : l'avant (-Z local)
regarde le tapis (sud) ; le tapis passe dessous dans l'axe x local = 0, de z local = -8 (face avant, monde z = -281)
à +4 (monde -293).
- Deux socles en boîte arrondie à studs de part et d'autre de la bande (faces intérieures à |x| ≥ 9,25 :
  `plan.PORTAIL_OUVERTURE` = 18,5), deux **colonnes rayées** (cylindres empilés), une **grande arche** en anneau
  (`anneau`, axe z, arc 180, section carrée, `or`) de rayon ≈ 12 posée sur les colonnes (sommet ≈ 34), une fine
  arche Neon devant, un **fond fermé** arrondi `blanc_labo` avec un **cœur lumineux** rond (Neon) où naissent les
  objets, un petit dôme et une antenne au sommet, une capsule de verre facultative sur une colonne.
- Seul élément au-dessus du tapis : l'arche (segments fins) ; le dessous de l'arche ≥ 20.

### centre.py — six fonctions (poses : `plan.CENTRE`, y = 0 sur la pelouse)
Rien de plus haut que 0,3 dans les zones libres (centre du podium, zone de vente) ; collisions franches pour socles,
comptoirs, plateaux ; ellipsoïdes `collide=False` avec collision par un bloc ou cylindre invisible si on peut y buter.

`stand_vente(b, variant=0)` — ≤ 90, ≤ 6 Neon. Pose (-17, 242), yaw 0, emprise **28 × 28**, H ≈ 18 (pièce d'or
jusqu'à ≈ 25). Socle carré arrondi 28 × 28 × 1 `dalle_labo` à studs avec bord rayé rouge et blanc ; dessus, le
**kiosque G01** : comptoir en arc de 220° tourné vers l'avant (nord), colonne, **toit-dôme** sur tambour,
**lambrequin rayé rouge et blanc**, quelques points Neon sous le bord, mât et **pièce d'or géante** debout face au
nord ; **zone de vente** : demi-disque de rayon 14 au nord du socle (centre au milieu du bord nord, z local -14)
tracé en **pointillés blancs** au sol (12-16 tirets 0,6 × 0,1 × 2, dessus à 0,3, studs). Aucun texte.

`machine(b, variant=0)` — ≤ 50, ≤ 6 Neon, ≤ 1 verre. Pose (25, 240), yaw 0, emprise **12 × 10**, H ≈ 15. G02 adapté :
socle arrondi 12 × 10 à studs + bord `indigo`, 2 pylônes rayés `bleu_nuit`/`blanc_labo` (x ±4) à boules Neon
`cyan`, bulle de verre (R ≈ 3,2) à cœur Neon `neon_violet` opaque, anneau orbital d'or incliné, 2 arcs Neon fins
des boules vers la bulle, tuyaux en J à l'arrière.

`monument(b, variant=0)` — ≤ 120, ≤ 20 Neon. Pose (0, 127), **yaw 180** (avant vers le sud), emprise **34 × 34**,
H ≈ 32. G03 : plateau de 3 disques (R 17 / 14 / 11, `turquoise` / `blanc_labo` / `turquoise`, studs), halo Neon
`neon_violet` (n 16), **réplique de l'œuf** (recette C01 à k ≈ 0,15 : 3 coquilles, intérieur, 2 méridiens Neon,
10 dents), anneau de données et 5 petits cubes en arc, 4 lampadaires-soucoupes bas sur le plateau ; collision de
l'œuf par un cylindre invisible.

`vitrine(b, variant=0)` — ≤ 60, ≤ 10 Neon. Pose (0, 34), yaw 180, **podium octogonal Ø 36** (entre plats), H 2,5 :
deux gradins octogonaux (2 blocs en croix + 4 coins à plat chacun, dessus décalés de 0,05 ; jamais deux carrés à
45°), anneau octogonal Neon sur la contremarche, bord doré, **disque central de Ø 20 laissé libre** (dessus plat à
studs, rien au-dessus de 2,6 : la statue du jeu s'y pose ; repère `Vitrine`).

`panneau_quetes(b, variant=0)` — ≤ 25, ≤ 4 Neon, ≤ 2 transparentes. Pose (0, 151), yaw 180 (face au sud), emprise
12 × 4, H ≈ 16 : émetteur rond à studs, **mât fin**, cadre en boîte arrondie (10 × 6) `bleu_nuit` à bord
`blanc_labo`, écran holographique Neon `cyan` transparence 0,35 **sans texte** (3 tirets `neon_blanc` comme faux
texte), étoile dorée sur le cadre. Le panneau ne collisionne pas, le mât et le socle oui.

`apparition(b, variant=0)` — ≤ 40, ≤ 16 Neon. Pose (-3, 206,5), yaw 0, emprise 14 × 14 : plaque dorée M13 agrandie
(R 5 ; `or`, `or_fonce`, anneau `blanc_labo` à studs), halo Neon `cyan` (disque percé ou anneau, n 16) au ras du
sol, 4 potelets M06 autour (R 7,5). Dessus à ≈ 0,35 (au-dessus des lignes de grille).

**Livrer** : rapport (pièces, Neon, transparentes par fonction) ; aperçus : le tapis entier vu d'en haut (vérifier les
onglets et les chevrons) et de la caméra `capture1` ; les portails ; chaque pièce du centre de 3/4.

---

## assets/mobilier.py

**Rôle** : le mobilier urbain et les petits objets, posés par carte.py d'après `plan.MOBILIER` (≈ 200 poses).
**Budget ≤ 4 600 pièces posées, ≤ 220 Neon, ≤ 30 transparentes.** Studs sur les dessus praticables ; poteaux,
palmes, lisses, antennes `collide=False, shadow=False` quand ils sont fins ; ce que le joueur touche (bordures,
assises, bacs) a une collision franche. Origine au pied, avant (-Z local) = côté « utile » (écran, assise, feux).
Images : planche `planche_petits_batiments.png` et `planche_sol_ciel.png` (A01-A06), crops `eh4_bordure.png`,
`eh4_cloture.png`, `r4_fence.png`, `eh4_ground_l.png`, `eh4_ground_r.png`, `eh4_left.png`, `eh4_cl.png`,
`eh4_cr.png`, `r4_center.png`. Recettes STYLE.md § 4.

| Fonction | Recette | Plafond | Poses |
|---|---|---|---|
| `palmier(b, variant=0, hauteur=18, courbure=1.0)` | M01 : stipe annelé courbe (7 segments), 8 palmes en 2 ellipsoïdes, 4 noix ; variantes : courbure à gauche / à droite, 6 ou 8 palmes | 28 | via les groupes |
| `groupe_palmiers(b, variant=0, n=2, diametre=8, hauteur=None, portee=1)` | jardinière **ronde** de Ø `diametre` à bordure rayée rouge et blanc (anneau carré de 12-16 segments, studs), terre `haie` et 3-6 boules de haie, `n` palmiers de hauteurs différentes (18 → 28 ; `hauteur` = le plus grand), courbures opposées | 16 + 28 n | 22 (marges, angles, U, parvis des coins) |
| `jardiniere(b, variant=0, largeur=12, profondeur=6, palmier=True)` | M03 : bordure rayée M04 (segments de 2, carré blanc aux angles), 10-14 boules de haie sur deux rangs, un palmier au centre | 70 | 18 (trottoir extérieur, contre les façades) |
| `lampadaire(b, variant=0, hauteur=9)` | v0 : **à écran** M07 (écran Neon `cyan` vers l'avant, rien d'écrit) ; v1 : **soucoupe** M08 | 10, 1 Neon | 74 |
| `banc(b, variant=0)` | M10 arrondi ; assise et dossier `orange`, `turquoise`, `rose_bonbon` ou `jaune_citron` selon la variante | 10 | 26 |
| `poubelle(b, variant=0)` | capsule ronde (corps, bague de couleur, couvercle bombé, fente) | 6 | 7 |
| `feu_tricolore(b, variant=0, hauteur=10)` | K05 simple sur mât : boîtier arrondi, 3 feux Neon (`rouge`, `jaune_citron`, `vert_lime`) et visières vers l'avant, plateau à points | 14, 3 Neon | 8 |
| `potelet(b, variant=0)` | M06 (H 3,5) | 5 | 16 |
| `coupole_miniature(b, variant=0)` | M16 : socle blanc et bague, coupole de verre, scène **opaque** (mini-palmier, maisonnette-œuf, 2 boules) | 14, 1 verre | 6 |
| `panneau(b, variant=0, picto="etoile")` | M11 + M12 : 2 poteaux, gélule, contour Neon en retrait, pictogramme en relief (`etoile`, `coeur`, `piece`, `eclair`, `nuage`, `croix`, `boutons`, `cornet`, `planete`, `chevron`) | 14, 3 Neon | 8 |
| `champignon_lumineux(b, variant=0)` | M09 (pois Neon ≤ 5) | 11, 5 Neon | 10 |
| `rambarde(b, variant=0, longueur=16)` | M05 : poteau tous les 8 (bouts compris), pommeaux `cyan` (SmoothPlastic), bagues `indigo`, 2 lisses `dalle_labo` | 1 + 5 par travée | 8 |

Variantes de couleur : alterner les couleurs de la palette (bancs, bacs) ; les palmiers suivent STYLE (verts plus
jaunes que le sol). **Livrer** : planche d'aperçu de toutes les fonctions côte à côte (une image) + gros plans du
palmier et de la jardinière ; rapport des pièces par fonction et variante.

---

## carte.py

**Rôle : l'ingénieur du plan.** Remplacer l'ébauche de l'atelier par la carte complète **en gardant l'interface**
attendue par rendu.py : `build_carte(seed=7) -> Builder`, `meta()` (`{"nom": "CarteEgghead", "version": …}`),
`verifications(b)` (avec `"problemes"`), `VUES` (= `plan.VUES`). `python carte.py --stats` et `--export` restent.
**Budget propre (sol, routes, trottoirs, bordures, marquages, mur de fond, repères, traces, tubes) ≤ 2 600
pièces, ≤ 40 Neon, ≤ 60 transparentes** ; la carte entière ≤ 24 000 / 1 500 / 400.

### Ordre de construction
1. Sol, trottoirs, routes et marquages, sol de la couronne, mur de fond, traces des parcelles, repères.
2. `tapis.tapis` puis les deux `tapis.portail`, puis les pièces du centre.
3. La couronne : chaque emplacement de `plan.CEINTURE` avec
   `with b.at((e["x"], plan.NIVEAU_COURONNE, e["z"]), yaw=e["yaw"], group=f"Tours/{e['id']}"):`
   `res = getattr(module, e["fonction"])(b, variant=e["variante"], **e["params"])`.
4. Les tubes (`plan.TUBES`), le ciel (`plan.CIEL`), le mobilier (`plan.MOBILIER`, y donné par chaque pose).
5. `b.decouper(("Sol",), 64)`.

**Modules manquants** : importer chaque module dans un `try` ; si un module ou une fonction manque ou lève une
exception, poser un **bloc provisoire** (cylindre ou bloc de l'emprise × hauteur de l'emplacement, `lavande`, groupe
`Provisoire/<id>`) et le lister dans `verifications(b)["provisoires"]` : la carte se construit toujours. Mesurer les
pièces ajoutées par chaque appel (`len(b.parts)` avant / après, Neon, transparentes) et les comparer à
`plan.budget_appel(fonction, params)` → `"hors_budget"` (par appel, par module avec `plan.BUDGETS`, total).

### Le sol (toutes les dalles de y = -2 au niveau indiqué, `studs="top"`, coins et tailles entiers)
- **Pelouse** (`Sol`) : `sol_vert`, dessus à 0, |x| ≤ 205, |z| ≤ 301. Dalles de 64 alignées sur les multiples de 64 :
  coupes en x = -205, -192, -128, -64, 0, 64, 128, 192, 205 et en z = -301, -256, -192, …, 256, 301 (80 dalles ;
  bandes de bord de 13 et 45).
- **Grille** (`Sol`) : `sol_ligne`, studs. Lignes le long de Z : pour chaque x = 8k de -200 à 200, bloc
  (8k, 0, -301) → (8k + 1, **0,15**, 301) (51 lignes). Lignes le long de X : pour chaque z = 8k de -296 à 296, bloc
  (-205, 0, 8k) → (205, **0,20**, 8k + 1) (75 lignes). Une pièce par ligne ; elles passent sous le tapis, les pièces
  du centre et les parcelles (futures bases).
- **Trottoir intérieur** (`Trottoirs`) : `dalle_labo`, dessus à **0,4**, cadre entre |x| 205 → 216, |z| 301 → 312
  (le dernier stud côté route est la bordure). Bandes est / ouest : x 205 → 216 sur z -312 → 312 ; bandes nord / sud :
  z 301 → 312 sur x -205 → 205 ; coupées aux multiples de 64.
- **Bordure rayée** côté route des deux trottoirs (`Trottoirs`) : base continue `blanc_labo` d'1 de large, de y -2 à
  **0,6** (trottoir intérieur : x 216 → 217 et z 312 → 313 ; trottoir extérieur : x 253 → 254 et z 349 → 350), un
  tronçon par côté ; **blocs rouges** de 4 de long tous les 8 (`rouge`, 4 rouges / 4 blancs), en saillie de 0,1 sur
  le dessus (0,7) et sur la face côté route, studs dessus ; aux angles, un carré blanc (jamais un segment coupé). Le
  côté trottoir des blocs rouges ne se confond pas avec la base (bloc de 1,05 de large ou décalé de 0,05).
- **Route** (`Routes`) : `voie`, dessus à **0**, entre les trottoirs (|x| 217 → 253 sur |z| ≤ 349, |z| 313 → 349 sur
  |x| ≤ 217), dalles coupées aux multiples de 64 ; carrés d'angle de 36 × 36 compris dans les bandes est / ouest.
- **Marquages** (`Routes/Marquages`), `blanc_labo`, épaisseur 0,1 (dessus à 0,1), studs :
  - **tirets de l'axe** 1 × 6 tous les 16, sur [235, 236] (est), [-236, -235] (ouest), [331, 332] (sud),
    [-332, -331] (nord), arrêtés à 4 des carrés d'angle (≈ 128 tirets) ;
  - **lignes de rive** continues d'1 de large sur [219, 220] et [250, 251] (et symétriques), une par côté et par
    bord, raccordées aux angles ;
  - **flèches** dans chaque voie tous les 96 (décalées de 48 entre les deux voies), au milieu de la voie : hampe
    1,4 × 6 + tête en chevron (2 blocs à ±45°) ; voie intérieure (côté pelouse) **antihoraire vue du dessus** (sud :
    vers +X ; est : vers -Z ; nord : vers -X ; ouest : vers +Z), voie extérieure en sens inverse ; pas de flèche à
    moins de 12 d'un passage piéton ;
  - **passages piétons** (`plan.PASSAGES_PIETONS`, z = ±134 sur les routes est et ouest) : 9 bandes 2 × 10, de
    x = 218 à 252 au pas de 4 (bandes sur [218 + 4k, 220 + 4k]), z ∈ [s - 5, s + 5] ; la ligne de rive s'interrompt
    au passage.
- **Trottoir extérieur** (`Trottoirs`) : `dalle_labo`, dessus à 0,4, entre la bordure (254 / 350) et la ligne des
  façades (271 / 367) ; dalles coupées aux multiples de 64.
- **Sol de la couronne** (`Sol`) : `sol_vert_clair`, dessus à **0,4**, de la ligne des façades au bord extérieur
  (|x| 271 → 351 sur |z| ≤ 367, |z| 367 → 447 sur |x| ≤ 271, 4 carrés d'angle 80 × 80) ; coupes aux multiples de 64.
- **Mur de fond** (`Tours/MurDeFond`) : 4 murs continus de 2 d'épaisseur au bord extérieur (|x| 349 → 351 sur
  |z| ≤ 447 ; |z| 445 → 447 sur |x| ≤ 349), de y 0,4 à **36**, `mix(skyline, blanc_labo, 0,5)`, bandeau `lavande` de
  1,5 en haut (saillie 0,1), studs sur le dessus. Il ferme toute vue à hauteur d'œil entre deux bâtiments.
- **Traces des parcelles** (`TracesParcelles`, facultatif, supprimable) : pour chaque parcelle, 4 **équerres
  dorées** (`or`, deux barres 8 × 1 et 1 × 7 par coin, de 0 à 0,3, studs) et le bord de la zone d'escalier (3 barres
  d'1 de large `blanc_labo`, de 0 à 0,3). Rien d'autre dans les parcelles.
- **Repères** (`Reperes`) : `plan.REPERES` avec `b.repere(nom, centre, taille, yaw)`.

### Les tubes (`Tours/Tubes`, `plan.TUBES`)
Pour chaque tube : A et B = centres des deux tours (`plan.CEINTURE_PAR_ID`), à la hauteur `y` ; tube de A à B
(extrémités dans l'axe des tours : cachées dans leur âme), rayon `plan.TUBE_RAYON[type]`, `Glass` transparence 0,5 ;
anneaux seulement sur la partie visible (de `ame_A + 3` à `L - ame_B - 3`, `ame` renvoyé par la tour, sinon
0,35 × diamètre) : type « fin » : anneaux d'or **hexagonaux** `anneau(R 3,2, ép 1,2, n 6, section carrée, or)`
perpendiculaires au tube tous les 24, fil Neon `cyan` au cœur facultatif ; type « geant » : anneaux épais
`anneau(R 7,6, ép 2,4, n 12, section carrée)` alternés `jaune_or` / `orange` tous les 36, chacun tourné de 15° autour
du tube par rapport au précédent ; si `onde` > 0, tube en tronçons de 24 sur une sinusoïde d'amplitude `onde`
(anneau à chaque jonction). `collide=False`.

### Le ciel (`Ciel`)
`ciel.oeuf_labo` à `plan.OEUF` (`b.at((x, y, z), yaw)`), `ciel.cable(depart=CABLE["de"], arrivee=CABLE["a"])` à
l'origine, `ciel.nacelle` pour chaque `plan.NACELLES` (`b.at((x, y, z), yaw)`, `rayon`, variante), `ciel.piece_or`
pour chaque `plan.PIECES_OR` (`yaw` fourni), `ciel.dirigeable`, `ciel.cumulus`. Régler le modèle `Ciel` en
`ModelStreamingMode = Persistent` si l'export le permet (sinon le signaler).

### Le mobilier (`Mobilier/<id>`)
Chaque pose de `plan.MOBILIER` : `with b.at((x, y, z), yaw=yaw, group=f"Mobilier/{id}")`, fonction de
`assets/mobilier.py` avec `variant` et `params`.

### Vérifications (`verifications(b)["problemes"]` doit rester vide)
- `kit.controles` (tailles, studs interdits, repères, **faces confondues**) ; Neon ≤ 1 500, transparentes ≤ 400,
  pièces ≤ 24 000 ; `hors_budget` (par appel, par module, total) ; `provisoires` (information).
- `parcelles_occupees` : aucune pièce (hors `Sol`, `Reperes`, `TracesParcelles`) dont la boîte coupe une emprise de
  parcelle entre y 0,3 et 80 ; `escaliers_occupes` : idem pour les zones d'escalier.
- `allees_encombrees` : aucune pièce **solide** dans `plan.COULOIRS_MARCHE` entre y 0,3 et 12.
- `hauteur_libre` : aucune pièce dont le dessous est entre 5 et 40 au-dessus d'une zone praticable
  (`plan.zone_praticable`) et dont l'aire horizontale dépasse 64, hors liste blanche (`Centre/Vente`,
  `Tapis/Portail_*`, `Mobilier/*` lampadaires, palmiers et panneaux).
- `fenetre_oeuf` : rien au-dessus de `plan.FENETRE_OEUF["hauteur_max"]` (125 depuis la finition) dans |x| < 70,
  z -572 → -402 ; `visee_oeuf` : depuis l'œil d'apparition, les bâtiments de la fenêtre restent sous le dessous du
  nuage ; `reperes_parcelles` : boîtes et avant des repères `Parcelle_*` / `Entree_*` conformes au plan.
- `spawn` : un seul repère `Spawn` ; `reperes` : tous ceux de `plan.REPERES` présents.
- `sol_sans_studs` : toute dalle de `Sol`, `Trottoirs`, `Routes` porte des studs sur le dessus.

### Vues (`VUES = plan.VUES`) et rendus de contrôle
```bash
$PY carte.py --stats
$PY rendu.py --rapide --sans-export --vues capture1 --res 1000x539 --echantillons 12 --suffixe=-c1
$PY rendu.py --rapide --sans-export --vues capture2 --res 1000x525 --echantillons 12 --suffixe=-c2
$PY rendu.py --rapide --sans-export --vues aerienne,ciel,joueur,rue,coin,centre --res 1200x675 --echantillons 12
```
Comparer `capture1` / `capture2` côte à côte avec `refEH1.png` / `refEH2.png` (planche d'assemblage avec PIL dans le
dossier de travail) : tapis, stand, machine, bords de pelouse, trottoirs, route, parcelles et ligne des façades
doivent coïncider (le centre optique de refEH1 est 12,5 px sous le centre de l'image : décalage négligeable).
Rendus finaux de l'utilisateur en 1600 × 900 (16 échantillons) plus les deux captures en 2000 × 1077 et 2000 × 1050.

**Livrer** : `carte.py` complet ; `python carte.py --stats` sans problème ; les deux captures comparées aux références
(planche) ; rapport des pièces par groupe racine et par module, liste des provisoires restants.
