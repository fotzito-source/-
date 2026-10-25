# Conception de la zone Dragon Ball (zone 4) : style stud

Quatrième zone du couloir du jeu « Volez un œuf », après Naruto, One Piece et Demon Slayer, avant Jujutsu Kaisen.
La zone mêle **trois paysages emblématiques et génériques** de la série dans une seule course :
la campagne terrestre, les terres de combat, puis une planète extraterrestre. Elle finit sous une arche de
roche géante cadrée de nuages dorés.
Le **couloir de course reste vide** au centre (**90 studs**, élargi à la demande du client) et tout le décor l'entoure.

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
| +48 → 0 | **Approche** (groupe `Approche`, supprimable) | Lions de pierre, lanternes, palmiers devant la **porte de temple** (z = 0) : piliers rouges, double toit orange, plaque 武道, murs jusqu'aux falaises ; appuis à \|x\| ≥ 46, dessous à 34,2 | La porte cadre la rue ; au loin, le pont de roche puis l'arche |
| 0 → -146 | **Campagne terrestre** | Grandes **maisons-dômes** (r 14-16) sur tambour, ligne de toits à 25-35 studs (dôme seul, aile, deux dômes reliés, maison haute, terrasse, tourelle-dôme) ; deux **boutiques** × 1,5 (cornet, beignet) ; palmiers de 22-28 ; dojo 道場, pagodes de 3-4 étages, dômes du fond ; falaises orange à bandes claires et brunes, 4 cascades ; rosace et chevrons peints | Couleurs franches, fanions au-dessus de la rue (≥ 34) |
| -146 → -282 | **Terres de combat** | Plaine verte trouée d'ocre, piste centrale claire ; **16 mesas** violettes (bandes sombres à hauteurs fixes, éboulis clairs, chapeau d'herbe épais) dont 3 géantes (60-72) et 2 colonnes près du trottoir ; falaises lavande basses ; **pont de roche** épais (z = -214, 108 entre les piles, dessous ≥ 34,5, voûte en gradins) ; cratères, 3 traces d'impact claires | Espace ouvert, silhouettes sur le ciel |
| -282 → -344 | **Planète extraterrestre** | **Deux pitons de sable** géants (62 et 68) en quinconce à la tête des canaux ; canaux \|x\| 55-71 avec liseré d'écume et 4 passerelles ; lac et îlots à droite ; **vaisseau rond** (r 18) à gauche ; hameau de dômes reliés ; arbres boules ; **bancs de nuages dorés** sur le 2e gradin des falaises de sable | Verticales des pitons et des arbres fins |
| -344 → -434 | **Place des œufs : l'arène** | Arène 96 × 80 (dessus à 1,5, rampes de 5, deux degrés de marches jusqu'à \|x\| = 53), liseré blanc, grand **武** ; 4 poteaux à flamme sur piédestal (\|x\| = 47,8) ; temple à gauche ; tribunes de 8 rangs à grand auvent, gong et pagode à 4 étages à droite ; bannières ; fanions (≥ 34) | L'arène au premier plan, l'arche au fond |
| -434 → -470 | **Arche finale** | Arche de sable à 3 bandes violettes et 3 filets roses, cascades à écume blanche, deux pitons massifs coiffés d'arbres, deux grands bancs de nuages dorés sur ses épaules ; passage de 104 (dessous ≥ 36) | Porte naturelle qui ferme la zone |

Retour avec l'œuf (vers +Z) : l'arène, la planète, le pont de roche, puis la rue blanche et la porte de temple (plaque lisible
aussi de ce côté). Les deux sens de lecture comptent.

## 3. Plan (vue de dessus, studs)

- Couloir \|x\| < 45 (90 studs) ; trottoirs 45 → 55 (lampadaires et mâts à 50, mobilier à 52,5) ; premières façades à \|x\| = 56 ;
  falaises latérales de \|x\| = 135 à 216. Ce qui enjambe le couloir garde ses appuis à \|x\| ≥ 46 et passe à 34 studs ou plus.
- Sol : route crème (campagne), terre kaki (friche), sable clair (planète), dalles de l'arène, dalles violettes (arche).
  Les trottoirs : pavés terre cuite, gravats, sable, parvis de pierre. Dans le couloir, frontières nettes soulignées d'une bande (bordure, sable foncé) ; trames « pixel » sur ±6 studs seulement sur les trottoirs et les côtés.
- Eau : canaux \|x\| 55-71 (gauche z -340 → -300, droite -328 → -288), lac à droite (centre x = 106, z = -314), surface à y = -0,4, fond turquoise foncé.
- Repères invisibles (`Reperes`) : `ZoneOeufs` posée sur l'arène (96 × 80, y = 1,5), `Entree`, `Sortie`, `Couloir`.

## 4. Palette (voir `palette.py`)

- **Campagne** : herbe `#62BE45`, route crème `#EDE4CC`, pavés terre cuite `#D9774A`, falaises orange `#E58B3A` / `#F2A85A` / `#C06E2C`.
- **Dômes** : blanc `#F5F5F1`, bandes orange `#F28C28`, bleue `#3C7BE0`, rouge `#E0453A`, jaune `#F6C83C`, turquoise `#2DBFC2`, vitres `#5CB6E6`.
- **Temple** : tuiles orange `#F0892A`, laque rouge `#D2392D`, enduit `#F6F0E2`, or `#F2C230`, dalles d'arène `#D9D9D3` / `#BDBDB5`.
- **Friche** : kaki `#D6BE7C`, falaises lavande `#C4B2E6`, ocre `#D6A65A`, mesas violettes `#8A5CC8` / `#6B45A8` / `#A57FDC`, strate rose `#C27FCB`.
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

Compte réel (`zone.py --stats`) : **≈ 11 050 pièces** (marge ≈ 2 450), dont ≈ 650 dans le groupe `Approche`.
Principaux postes : mesas 1 100, maisons-dômes 1 000, arche 820, palmiers 790, pagodes 620, porte 580,
sol 1 490, falaises 750, temple 450, pont 270, nuages 160.
