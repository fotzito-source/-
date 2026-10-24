# Conception de la zone Dragon Ball (zone 4) : style stud

Quatrième zone du couloir du jeu « Volez un œuf », après Naruto, One Piece et Demon Slayer, avant Jujutsu Kaisen.
La zone mêle **trois paysages emblématiques et génériques** de la série dans une seule course :
la campagne terrestre, les terres de combat, puis une planète extraterrestre. Elle finit sous une arche de
roche géante cadrée de nuages dorés.
Le **couloir de course reste vide** au centre (64 studs) et tout le décor l'entoure.

## 1. Ce que dit la recherche (repères visuels génériques)

| Paysage | Repères qu'on garde (génériques) | Traduction en stud |
|---|---|---|
| Campagne terrestre (villes et villages de la série) | Maisons rétro-futuristes en **dômes blancs** à bandes de couleur, fenêtres et portes **rondes**, petites antennes ; **palmiers** ; herbe vert vif ; **falaises orange en strates** ; **cascades** ; pitons rocheux à sommet herbu | Dôme = boule blanche à moitié enterrée ; bande = cylindre un peu plus large ; hublots = disques ; falaises = gradins orange à chapeau d'herbe débordant |
| Arts martiaux | Arène d'arts martiaux **carrée en dalles de pierre claire**, un peu surélevée, avec des marches ; temple à **toits de tuiles vernissées orange**, piliers laqués rouges, murs blancs ; palmiers, statues de pierre, parasols ; bannières au caractère 武 | Arène = sol pixel en dalles 8×8, bordure sombre, grand 武 en mosaïque ; toits = coins (wedge) avec studs ; piliers rouges carrés |
| Terres de combat (« le désert rocheux ») | Plaine verte trouée de **terre kaki et ocre**, **mesas à sommet plat** aux flancs **violets** et au dessus herbu, petits rochers, **cratères d'impact** | Mesas = blocs empilés en retrait, strates rose-lavande, chapeau d'herbe ; cratères = anneau de gravats et disques brûlés |
| Planète extraterrestre | Herbe **bleu-vert** (presque sarcelle), **eau turquoise**, îlots plats aux bords de **sable ocre**, **pitons rocheux** isolés, arbres très fins à **couronne ronde** (« boules »), maisons en **dômes blancs** aux hublots ronds teintés de vert, vaisseau **rond et blanc sur pattes** | Arbre boule = tronc fin + 3 à 6 blocs ronds ; dômes = boules sous le sol ; eau = dalle turquoise translucide sous le niveau du sol |
| Ciel céleste | **Nuages dorés** en grandes masses, ciel rose-magenta, colline vert vif | Le ciel du jeu reste bleu : bancs de nuages jaune or posés sur les falaises et au pied de l'arche, strates roses dans la roche, fanions roses |

Sources consultées (fiches de fans et articles, à prendre comme repères de couleur et de forme) :
fiche « Ajisa » et « Namek » des wikis de fans (herbe sarcelle, eau vert clair, arbres fins à couronne ronde,
dômes blancs à hublots ronds teintés de vert), article de l'exposition du Barbican 2017 qui rapproche les
« Capsule houses » de l'architecture métaboliste japonaise (dômes, modules ronds), description du kit
« Tenkaichi Budokai » (toit, palmiers, statues de pierre, parasols, écran 武), et la référence `ref10` du jeu actuel.

## 2. Séquence de la course (on court vers -Z)

| z (studs) | Moment | Repère | Vue à hauteur de joueur |
|---|---|---|---|
| +40 → 0 | **Approche** | Grande **porte de temple** (z = 0) : deux énormes piliers rouges, double toit de tuiles orange à coins relevés, plaque 武道 lisible des deux côtés, murs blancs à chaperon orange jusqu'aux falaises (\|x\| = 124), deux lions de pierre gardiens | La porte cadre la rue blanche du village ; au loin, le pont de roche violet |
| 0 → -146 | **Campagne terrestre** | Rue de **maisons-dômes** blanches à bandes orange, bleues, rouges, jaunes ; deux **boutiques-dômes** à enseigne-objet ; palmiers entre les maisons ; dojo 道場 et terrain d'entraînement (mannequins, jarres) à gauche ; **pagodes** ; voitures volantes garées ; **falaises orange** en strates à chapeau d'herbe avec **4 cascades** ; pitons orange | Couleurs franches sur fond blanc, lampadaires ronds, fanions colorés au-dessus de la rue (≥ 34 studs) |
| -146 → -290 | **Terres de combat** | Sol kaki taché d'ocre, **mesas violettes** à sommet vert de toutes tailles (près : 20-30 de haut, loin : 40-55), **pont de roche naturel** au-dessus du couloir (z = -222, dessous à 34 studs, piles = mesas), **cratères**, rochers, pitons violets ; deux traces d'impact peintes au sol du couloir | Grand espace ouvert, épique ; le pont cadre la suite ; strates roses dans les falaises |
| -290 → -358 | **Planète extraterrestre** | Herbe bleu-vert, allée de **sable clair**, **canaux turquoise** des deux côtés (\|x\| 46-60), **lac** à droite avec îlots herbus aux bords de sable, **arbres boules**, **dômes blancs** aux hublots verts, **vaisseau rond sur pattes** à gauche, **pitons de sable ocre** | Ambiance étrange et douce, verticales des arbres fins |
| -358 → -426 | **Place des œufs : l'arène** | **Arène carrée 68 × 68** en dalles claires (dessus à 1 stud, rampes de 5 studs dans le couloir, marches sur les côtés), grand **武** rouge dans un cercle doré, 4 poteaux d'angle à flamme ; **temple d'arts martiaux** à gauche (toits orange, colonnade rouge), **tribunes** et **gong** à droite, bannières 武 / 気 / 修行 / 武道, deux cordons de fanions (≥ 34 studs) | L'arène au premier plan, l'arche géante au fond, des nuages dorés de chaque côté |
| -426 → -470 | **Arche finale** | **Arche de roche géante** (façade z = -436, 34 de profondeur, ~96 de haut) aux strates sable ocre et violettes, couronnée d'herbe et d'arbres boules, deux **cascades** sur ses flancs, deux **pitons géants** qui l'encadrent ; **bancs de nuages dorés** à ses pieds ; le couloir passe dessous (dessous ≥ 34 studs) vers la zone suivante | Une porte naturelle majestueuse, lumineuse, qui ferme la zone |

Retour avec l'œuf (vers +Z) : l'arène, la planète, le pont de roche, puis la rue blanche et la porte de temple (plaque lisible
aussi de ce côté). Les deux sens de lecture comptent.

## 3. Plan (vue de dessus, studs)

- Couloir \|x\| < 32 ; trottoirs 32 → 42 ; premières façades à \|x\| = 44 ; falaises latérales de \|x\| = 124 à 200.
- Sol : route crème (campagne), terre kaki (friche), sable clair (planète), dalles de l'arène, dalles violettes (arche).
  Les trottoirs : pavés terre cuite, gravats, sable, parvis de pierre. Transitions tramées « pixel » sur ±6 studs.
- Eau : canaux \|x\| 46-60 de z = -298 à -352, lac à droite (centre x = 92, z = -322), surface à y = -0,4.
- Repères invisibles (`Reperes`) : `ZoneOeufs` posée sur l'arène (y = 1), `Entree`, `Sortie`, `Couloir`.

## 4. Palette (voir `palette.py`)

- **Campagne** : herbe `#62BE45`, route crème `#EDE4CC`, pavés terre cuite `#D9774A`, falaises orange `#E58B3A` / `#F2A85A` / `#C06E2C`.
- **Dômes** : blanc `#F5F5F1`, bandes orange `#F28C28`, bleue `#3C7BE0`, rouge `#E0453A`, jaune `#F6C83C`, turquoise `#2DBFC2`, vitres `#5CB6E6`.
- **Temple** : tuiles orange `#F0892A`, laque rouge `#D2392D`, enduit `#F6F0E2`, or `#F2C230`, dalles d'arène `#D9D9D3` / `#BDBDB5`.
- **Friche** : kaki `#BCA96A`, ocre `#D6A65A`, mesas violettes `#8A5CC8` / `#6B45A8` / `#A57FDC`, strate rose `#C27FCB`.
- **Planète** : herbe sarcelle `#3DB39B`, eau turquoise `#35C3D2`, sable `#E8D096`, arbres boules `#36AE9E`, hublots verts `#86DDA8`.
- **Ciel céleste** : nuages or `#FFD24A` / `#FFE68C` / crème `#FFF5CF`, ombre `#F2B23C`, accents magenta `#F06AB8`.

Vert émeraude jamais dominant : l'herbe est vert-jaune vif, puis sarcelle. Pas de gris sale.

## 5. Propriété intellectuelle (Roblox supprime les licences non autorisées)

- **Aucun nom** de la série ni des personnages, nulle part (pas dans les noms de pièces, de groupes, ni dans le titre de la zone).
- **Aucun personnage**, aucune silhouette de personnage, aucune statue de personnage. Les statues sont des lions de pierre.
- **Interdits précis** : pas de logo ni de nom d'entreprise sur les dômes (pas de « Capsule », pas de « CC »), pas de capsules
  à lancer posées au sol ; pas de symbole ni de kanji de l'école de la tortue (亀) ; pas de maison rose sur une île avec un palmier ;
  **pas de sphères orange** (ni lampes, ni fruits, ni pommeaux), **pas d'étoiles rouges** ; pas de dragon (龍 interdit aussi) ;
  pas de petit nuage jaune isolé près du sol (le « nuage volant ») ; pas de plateforme blanche suspendue avec palmiers,
  pas de tour blanche très fine ; pas de capsule spatiale sphérique blanche dans un cratère (les cratères restent vides) ;
  pas le vaisseau exact du méchant : notre vaisseau est une lentille blanche et lavande à coupole, sur quatre pattes, avec
  trois grands hublots à l'avant seulement ; pas de texte de tournoi (天下一, 武道会…).
- **Textes autorisés** : 武, 道場, 修行, 武道, 気, 天. Aucun autre texte.

## 6. Budget de pièces (≤ 13 500)

| Bloc | Pièces visées |
|---|---|
| Sol (route, trottoirs, côtés, eau, arène) | ~1 100 |
| Falaises latérales | ~600 |
| Mobilier posé par `zone.py` (lampadaires, bannières, fanions, poteaux…) | ~550 |
| `assets/temple.py` (porte, lions, temple, tribunes, dojo, pagodes) | ≤ 2 150 |
| `assets/batiments.py` (dômes, boutiques, dômes extraterrestres, voitures) | ≤ 2 100 |
| `assets/nature.py` (palmiers, arbres, mesas, pitons, cratères, cascades, îlots…) | ≤ 3 300 |
| `assets/arche.py` (arche finale, pont de roche, nuages dorés, vaisseau) | ≤ 2 500 |
| **Total visé** | **~12 300** (marge ~1 200) |
