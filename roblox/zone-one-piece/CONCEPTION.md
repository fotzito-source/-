# Conception de la zone One Piece (zone 2) — mer de l'Est, en style stud

Zone 2 du couloir « Volez un œuf », entre Naruto (zone 1) et Demon Slayer (zone 3). Les joueurs y arrivent
plus vite (« VITESSE CONSEILLÉE : 200 ») : la zone mesure **400 studs** (Naruto : 364), le couloir est vide et
large de 60 studs, le décor raconte une petite île de la mer de l'Est : on passe l'arche du port, on longe
la campagne aux moulins, on traverse le bourg coloré, on court sur les quais entre les navires pirates,
on attrape l'œuf sur le grand ponton à rose des vents, puis on file par la bouche du rocher du crâne.

## 1. Ce que disent les références

| Référence | Ce qu'on en garde (générique) |
|---|---|
| `refOP1` haut | moulin de bois sur tréteau, **ailes jaunes** en lattes, gouvernail rouge : silhouette forte sur le ciel |
| `refOP1` milieu | **très long ponton** de planches sur une eau bleu profond, village en front de mer : murs blancs, bleus, rouges, toits rouges et bleus, quai de pierre, colline verte derrière |
| `refOP1` bas | prairie vert pomme, **clôtures de ranch**, **vaches** pie noir, moulins de pierre blanche à **toit bleu** et grandes ailes en croix, chemin de terre qui descend vers la mer, navire au loin |
| `refOP2` | moulin à **tour rose** et ailes blanches à claire-voie, clôtures de bois au bord du chemin ; arche de bois à **enseigne suspendue** à l'entrée d'une ville ; navire-restaurant à voiles rayées jaune et blanc (on garde **les rayures**, jamais la proue en poisson) ; rue de maisons claires et palmiers |
| `refOP3` | vue de colline : **tours de pierre à dôme gris-bleu**, galerie en balcon, fermes à **toits rouges**, navire à trois mâts aux **voiles rouges** au mouillage, mouettes, grands nuages, mer bleu profond |
| `ref1`, `ref2` (jeu actuel) | allée de sable, palmiers, fanions, rivière de chaque côté, navire, phare rayé rouge et blanc, coffre, viande sur l'os ; portique bleu marine « ZONE RARE / VITESSE CONSEILLÉE : 200 » en lettres violettes et jaunes : **on garde ce panneau** (élément de jeu), habillé en arche de port |

Recherches complémentaires (vocabulaire générique, pas de visuels de la licence) :
- les cartes de jeux pirates sur Roblox et les maquettes LEGO de ports pirates combinent toujours **port + navire à quai +
  phare + palmiers + quai éclairé de lanternes** : c'est la grammaire à respecter pour être lu « pirate » en un coup d'œil
  ([carte d'île pirate](https://payhip.com/b/E9udn), [lobby tropical](https://builtbybit.com/resources/island-adventure-lobby-premium-map.105657/),
  [port LEGO en modules](https://ideas.lego.com/projects/50e4a8bd-05a0-49ae-86a1-a3cd6d240458), [conseil de port, DevForum](https://devforum.roblox.com/t/how-should-i-build-a-port/1970744)) ;
- anatomie d'un galion de dessin animé : **château avant** (gaillard) et **château arrière** surélevés, pont bas au milieu,
  **nid-de-pie** en haut du grand mât, beaupré, sabords à canons ([glossaire du Mary Rose](https://maryrose.org/glossary/)) ;
- les jeux d'animé sur Roblox sont régulièrement retirés pour atteinte au droit d'auteur (cas « Vox Seas », 2025,
  [Distractify](https://www.distractify.com/p/what-happened-to-vox-seas)) : la règle « rien de la licence » est vitale.

Traduction en style stud : grosses masses simples, couleurs franches, ailes de moulin en lattes de blocs, voiles en
2-3 blocs décalés (ventre gonflé), coques en gradins de blocs et de coins, eau en aplats turquoise sans studs, toits
studdés, tout ce qui est petit (cordages, fanions, lanternes) sans collision.

## 2. Séquence de la zone (de l'entrée à la sortie)

| z | Moment | Repère principal | Vue à hauteur de joueur (en courant vers -Z) |
|---|---|---|---|
| +40 → 0 | **Abords** | palmiers, rochers, prairie | au fond, le crâne géant domine la ligne d'horizon ; à droite le phare rayé ; devant, l'arche |
| 0 | **Arche du port** | arche de bois à cordages, bouées, filets, pavillons ; panneau bleu marine « ZONE RARE » (violet) et « VITESSE CONSEILLÉE : 200 » (jaune), lettres ≥ 4-5 studs, lisible des deux côtés ; palissade de pieux jusqu'aux collines | l'arche cadre le chemin de terre, les moulins tournent de chaque côté |
| 0 → -112 | **Campagne aux moulins** | moulin de bois à ailes jaunes (gauche, près du chemin), moulin à tour rose (droite), tour de pierre à dôme sur une butte, moulins sur les collines, granges rouges, vaches, foin, verger de mandarines | chemin de terre à ornières bordé de clôtures rustiques ; collines vertes en gradins à `|x| ≥ 130` ; au fond, les toits colorés du bourg et les mâts |
| -112 → -204 | **Bourg du port** | maisons colorées (blanc, bleu, jaune, rose, rouge ; toits rouges, bleus, turquoise ; auvents rayés), taverne à enseigne, étal de fruits, étal de viande sur l'os, viande à la broche ; seconde rangée sur une terrasse haute (`y = 6`) avec escaliers et palmiers | grandes dalles ocre ; trois guirlandes de fanions à 37 studs ; lanternes à potence ; les mâts des navires dépassent des toits |
| -204 → -292 | **Port pirate** | à gauche le grand **galion** (coque brun-rouge, voiles crème, 3 mâts) à quai avec passerelle ; à droite la **caravelle** jaune et le **phare** rouge et blanc au bout d'une jetée ; pontons, barques, îlots à palmiers, plages au pied des collines, navire aux voiles rouges au mouillage au large | quai de planches ; bassins turquoise de chaque côté, écume au pied des quais ; bittes, canons tournés vers le large, tonneaux, filets ; deux guirlandes |
| -292 → -366 | **Place des œufs** | grand ponton (`|x| ≤ 56`) à **rose des vents** (cercle de rayon 34, centre `z = -328`, nord rouge vers la sortie) ; quatre mâts de vigie à pavillons, guirlandes hautes, coffres au trésor, canons, ancre, barre de navire, pieux et cordages au bord | la mer s'ouvre des deux côtés ; devant, la face du crâne remplit le ciel |
| -366 → -400 | **Rocher du crâne** | rocher ivoire en forme de **tête de mort générique** (≈ 100 de haut) : orbites sombres, nez, rangée de dents au-dessus du passage ; le couloir traverse **la bouche** (64 de large, plafond ≥ 36) jusqu'à la zone suivante ; épave échouée sur le flanc gauche, cascade et palmiers sur le flanc droit, pavillon au sommet | on court droit dans la bouche ; la lumière de la sortie au fond |

Retour (vers +Z) : la bouche du crâne s'ouvre sur la place, puis le port et ses navires, le bourg, les moulins, l'arche
(panneau lisible côté retour). Chaque section a un repère visible dans les deux sens (navires et phare hauts de 60-70,
moulins de 22-30, crâne de 100).

## 3. Repère final et passage

- Origine du rocher : centre de l'entrée du passage, au sol, en `z = -366` ; le rocher regarde +Z (vers les joueurs)
  et s'étend jusqu'à `z = -400` ; largeur 440 (il ferme toute la largeur de la zone, mer comprise).
- Passage : `|x| < 32` libre du sol jusqu'à y = 36 au moins (les dents s'arrêtent à y ≥ 36) ; rien sous y = 30 au-dessus
  du couloir ; sol de sable ; parois de roche en gradins éclairées de lanternes.
- Tête de mort **générique** (pas d'os croisés sur le rocher, pas de chapeau, pas d'emblème) : crâne arrondi en gradins
  studdés, orbites et nez en creux sombres (`grotte`), pommettes, dents ivoire au-dessus de la bouche, herbe et palmiers
  sur le sommet, pavillon générique planté au sommet.

## 4. Palette (`palette.py`)

- Sol : sable `#F2DFA7`, chemin de terre `#D6AE70`, prairie vert pomme `#6CBF45` / `#86D05A`, terre `#9C6B3E`.
- Pierre chaude : pavés `#E6D5AE`, quais `#D9CDB4`, margelles `#B9AA8C` (jamais de gris froid).
- Eau : écume `#E6F8FC`, haut-fond `#62D6E4`, eau claire `#3FC1E0`, bassin `#2AA3D0`, large `#1E86C0`.
- Bois : `#8A5A36`, `#5E3B24`, planches `#9E6E45` / `#B07D4F`, bois flotté `#BFA88A` ; coques `#8E3B2A` (brun-rouge),
  `#E3B23C` (jaune).
- Voiles `#F8F4E8` (ombre `#E6DECA`), voiles rouges `#D63A2F`, cordages `#D8C08A`.
- Accents : rouge `#D63A2F`, jaune `#F5C842`, turquoise `#3FB8A8`, bleu `#3A6FC4`, rose `#F2A0B5`, or `#F2C230`.
- Murs : blanc `#F6F1E6`, crème, jaune `#F7D877`, bleu `#86B8E6`, rose, rouge `#D9574A`, turquoise ; toits rouge,
  bleu, turquoise, orange ; dômes de pierre bleu-gris `#8D9AAE`.
- Végétation : palmes `#4FA23A` / `#6CBF45`, troncs `#9C6B3E`, mandarines `#FF9A1F`.
- Rocher du crâne : ivoire `#EADFC4` → `#A99B7C`, creux `#3A3346`.
- Panneau de jeu : fond `#1B2150`, « ZONE RARE » `#B48CFF`, « VITESSE CONSEILLÉE : 200 » `#FFE37A`.

## 5. Propriété intellectuelle

Rien de la licence : aucun nom (série, personnages, navires, villes, restaurant, Marine), aucun emblème exact (tête
de mort au chapeau de paille, pavillons d'équipages, mouette-ancre de la Marine), aucune figure de proue reconnaissable
(mouton, lion à crinière solaire, poisson géant), aucun personnage ni chapeau de paille mis en scène. Seulement des
éléments de piraterie et de mer tropicale génériques. Textes en français courants uniquement (liste dans
`CONVENTIONS.md`), pas de mot d'alcool. Éviter aussi le nom de la licence dans le titre, les miniatures et le nom
affiché de la zone dans le jeu.

## 6. Budget de pièces (≤ 12 500)

| Ensemble | Fichier | Budget |
|---|---|---|
| Sol, eau, collines, terrasse, mobilier placé, place des œufs | `zone.py` + `assets/mobilier.py` | ≈ 3 500 |
| Arche d'entrée + rocher du crâne | `assets/monuments.py` | ≤ 1 500 |
| Navires, barques, phare, pontons | `assets/port.py` | ≤ 2 200 |
| Maisons (×13), taverne, étals, granges | `assets/batiments.py` | ≤ 2 400 |
| Moulins (×8), palmiers, arbres, rochers, îlots, butte | `assets/nature.py` | ≤ 1 950 |
| **Total visé** | | **≈ 11 550** (marge ≈ 950) |

## 7. Découpage du travail

`zone.py` (plan, sols, eau, collines, placements), `palette.py`, `assets/mobilier.py` : directeur artistique.
Quatre modules en parallèle : `assets/monuments.py`, `assets/port.py`, `assets/batiments.py`, `assets/nature.py`
(signatures exactes dans les spécifications ; `zone.py` dessine un bloc rose translucide tant qu'un asset manque).
