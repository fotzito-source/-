# Conception : zone Bleach, « la cité blanche aux toits ocre »

Sixième zone du couloir, après Naruto, One Piece, Demon Slayer, Dragon Ball et Jujutsu Kaisen. Le joueur arrive
vite. Il entre par une porte colossale dans une ville-forteresse céleste, traverse un faubourg de bois sombre, puis
une cité blanche aux murs interminables, prend son œuf dans une grande cour pavée et repart vers sa base. La
colline de la tour blanche et du monolithe ferme la perspective.

**Couloir de course vide** : `|x| < 32` (64 studs de large), trottoirs jusqu'à `|x| = 42`. Longueur : 522 studs
de la grande porte (z = 0) à la sortie (z = -522).

## 1. Ce qu'on garde des références, et ce qu'on corrige

| Source | À reprendre | À corriger ou éviter |
|---|---|---|
| Zone actuelle (`ref12.png`) | Murs blancs partout, tours carrées blanches très hautes, cerisiers roses, porte blanche au bout | Tout est blanc sur blanc et plat. Toits bleus en pyramide trop nombreux, cerisiers en boules lisses, sol blanc uni sans repère, petites maisons identiques, rien ne monte au-dessus de l'allée |
| Panorama de la cité (a) | Mer de bâtiments **blancs à toits de tuiles ocre-orangé**, longs remparts blancs à **chaperon ocre**, tours de guet blanches. Au centre, une colline porte une **grande tour blanche à bandes rouges et flèches sombres**, à côté d'un **monolithe de pierre vertical géant**, avec des masses d'arbres verts | Rien |
| Vue aérienne (b) | Grille dense d'enclos murés concentriques, toits orange, tours blanches, horizon plat | Rien |
| Rue du faubourg (c) | Chemin de **grandes dalles de pierre au milieu d'une route de sable**, maisons de bois sombre à étage, **tuiles grises**, balcons, tours de guet en bois au loin | Personnages : aucun dans la zone |

**Recherche** (éléments génériques, tous issus de l'architecture japonaise réelle) :
- **Enceintes de château** : murs d'enduit blanc (*shikkui*) posés sur une base de pierre talutée (*ishigaki*),
  coiffés d'un **chaperon de tuiles** à deux pentes (murs *dobei*). On y voit des meurtrières carrées ou
  triangulaires (*sama*) et un soubassement de planches sombres ou de tuiles à joints blancs (*namako*). Les tours
  d'angle (*yagura*) sont blanches et carrées, avec un étage en encorbellement. La **tour-porte** (*yagura-mon*)
  est un corps de garde posé sur le passage. Himeji, la « Grue blanche », tire son nom de cet enduit blanc
  jusque dans les joints des toits.
- **Villes d'Edo** : les rues de maisons de marchands à étage (bois sombre, treillis, *noren*, stores *sudare*,
  tuiles grises) avaient leurs **tours de guet à incendie** (*hinomi-yagura*). C'est une tour de bois d'environ
  9 m, sur quatre poteaux légèrement inclinés vers l'intérieur et contreventés en croix, avec une plateforme à
  garde-corps, un petit toit et une **cloche d'alarme** (*hanshō*). Au pied, des **seaux d'incendie empilés en
  pyramide** à côté d'un tonneau d'eau.
- **Pierres sacrées** (*iwakura*) : un rocher remarquable est ceint d'une corde de paille (*shimenawa*) à
  papiers blancs. On s'en sert pour le monolithe : la corde le rend générique, c'est une pierre sacrée et non
  un objet de la licence.

**En stud** : grands aplats blancs cassés en « pixels » de 3 ou 4 blancs proches, chaperons et toits en
coins (`wedge`) ocre avec studs. Bases de pierre en gradins, ouvertures sombres franches, accents rouges et
bleus rares mais nets. Les silhouettes doivent se lire de loin : remparts horizontaux, tours verticales,
toits débordants.

## 2. Séquence de la course (entrée → sortie)

| z | Moment | Repère | Vue à hauteur de joueur |
|---|---|---|---|
| +64 → +8 | **Esplanade** | La façade extérieure de la **grande porte blanche** : mur de 64 studs à chaperon ocre, bastions, corps de garde à toit ocre à deux étages, plaque 門. Les vantaux géants sont ouverts vers l'extérieur, en éventail | On ne voit que du blanc et du ciel ; dans l'ouverture (76 × 50), la rue de sable du faubourg et, très loin, la tour blanche |
| +8 → -8 | **Passage de la porte** | Ouverture de 76 de large et 50 de haut, dalles sombres, épaisseur du mur 16 | Effet de seuil : on passe sous un linteau énorme |
| -8 → -171 | **Faubourg** | Rue de sable et chemin central de grandes dalles. Cinq maisons de bois sombre par côté, à étage et balcon, tuiles grises, noren, sudare ; ruelles avec échoppes, puits, seaux d'incendie ; **trois tours de guet en bois** au-dessus des toits ; deux guirlandes de lampions (≥ 31 studs) ; jardins potagers et cerisiers à l'arrière | Ambiance chaude et vivante, bois sombre contre sable doré ; au bout, la **porte intérieure** blanche |
| -171 → -181 | **Porte intérieure** | Tour-porte blanche (*yagura-mon*) : corps de garde au-dessus de 36 studs, balcon laqué rouge, toit ocre à deux étages, plaque 静, mur intérieur de 24 studs jusqu'aux remparts | Bascule nette : du bois sombre on passe au blanc éclatant |
| -181 → -388 | **Cité blanche** | L'allée court entre deux **longs murs blancs de 10 studs à chaperon ocre**. Trois enclos par côté, chacun avec son **portail** (静 茶 白 宿 門), une cour de gravier blanc et un bâtiment blanc à toit ocre face au couloir. Derrière : bâtiments et **tours blanches** (40-46 studs, toits ocre, deux bleus), cerisiers qui dépassent des murs, un cerisier géant par côté, un jardin à étang et pont rouge. **Passerelle laquée rouge** couverte à 38 studs au-dessus du couloir (z = -286), entre deux tours blanches | Rythme régulier de murs, portails et lanternes ; la passerelle rouge cadre la colline au loin |
| -388 → -476 | **Cour des œufs** | Cour pavée de 160 de large, fermée de murs blancs de 12 studs ; **mosaïque de fleur de cerisier** de rayon 34 (centre z = -430) ; deux pavillons à piliers rouges, lanternes, buissons, cerisiers, deux cerisiers géants derrière les murs ; deux piliers-lanternes à l'entrée | La colline remplit le fond : tour blanche à gauche, monolithe à droite, tunnel au centre |
| -476 → -522 | **Colline de la tour et du monolithe** | Mur de soutènement de pierre pâle percé d'un **tunnel** (passage de 68, hauteur libre ≥ 38) sous un corps de garde blanc à toit ocre. Sur la colline : la **grande tour blanche à bandes rouges et flèches sombres** (sommet vers 150 studs) et le **monolithe géant** de pierre gris-bleu ceint d'une corde sacrée (sommet vers 140), des masses d'arbres verts, des pins, un escalier de pierre à lanternes | Le repère final, visible dès l'entrée par l'ouverture de la grande porte |
| -522 | **Sortie** | Bouche du tunnel ouverte vers la zone suivante | — |

Les **côtés** sont fermés par des remparts blancs de 28 studs (|x| = 150), avec chaperon ocre, meurtrières et
trois tours par côté. Au-delà, la **ville lointaine** (enclos blancs à toits ocre, |x| 158-206) donne l'échelle
d'une cité immense sur les vues aériennes et de côté.

**Retour** : vu depuis la cour, l'allée blanche file vers la porte intérieure, puis le faubourg et la grande
porte. Les deux faces des portes et de la passerelle sont soignées, et les guirlandes se lisent dans les deux sens.

## 3. Repère final et sortie

`colline_tour` a pour origine le centre de l'entrée du tunnel (z = -476) et regarde +Z.
- Le **mur de soutènement** (*ishigaki*) en gradins couvre toute la largeur. Le **portail du tunnel** est
  coiffé d'un corps de garde blanc à toit ocre et balcon rouge, tout au-dessus de 38 studs.
- Le **tunnel** fait 46 studs de long, dégage `|x| < 34` jusqu'à y = 38 et débouche en z = -522.
- La **tour blanche**, posée sur la colline à gauche (x ≈ -64), monte vers 150 studs. Elle a plusieurs corps
  qui se rétrécissent, des bandes rouges en saillie, des fenêtres sombres et une couronne de **flèches sombres**.
  Des ailes basses blanches à toits ocre entourent son pied.
- Le **monolithe**, à droite (x ≈ +60), est une dalle de pierre verticale massive et légèrement irrégulière,
  qui monte vers 140 studs. Il porte une **corde sacrée** (*shimenawa*) à papiers blancs et se dresse sur une
  terrasse de pierre.
- **Masses d'arbres verts** et pins sur les gradins, plus un escalier de pierre à lanternes qui monte vers la
  tour (hors couloir).

## 4. Palette (`palette.py`)

- **Blancs** (dominants) : `blanc` #F5F2EB, `blanc_pur`, `blanc_creme`, `blanc_ombre`, `blanc_gris`
  (`blanc_pixel(rng)` tire au hasard).
- **Ocre-orangé** (signature des toits et chaperons) : `ocre` #D8924A, `ocre_clair`, `ocre_fonce`,
  `ocre_brun`, `terre_cuite`.
- **Pierre pâle chaude** (sol, bases) : `dallage`, `pierre_claire`, `pierre`, `pierre_fonce`, `bordure`,
  `gravier`.
- **Faubourg** : `bois_fonce` à `bois_clair`, `bois_gris`, `tuile_grise`, `torchis`, `sable`, rideaux
  `noren_*`.
- **Accents** : `laque_rouge` (passerelle, balcons, bandes de la tour), `bleu` / `bleu_profond` (deux toits de
  tour, rideaux, pots), `or` (plaques, épis), `ardoise_fleche` (flèches).
- **Nature** : `sakura` (cinq roses), `tronc`, verts tendres `feuille*` et `pin` en petites masses, jamais en
  vert émeraude dominant. **Colline** : `roche*` (pâle et chaude), `monolithe*` (gris-bleu), `lichen`.

## 5. Budget de pièces (plafond 13 500)

| Poste | Budget |
|---|---|
| Sol (couloir, trottoirs, côtés, mosaïque) | 1 070 (mesuré) |
| Mobilier posé (lanternes, guirlandes, enseignes, objets) | 590 (mesuré) |
| `assets/remparts.py` (grande porte 850, porte intérieure 420, passerelle 330, 44 murs ≈ 680, 10 tours ≤ 65, 6 portails ≤ 60) | ≈ 3 290 |
| `assets/batiments.py` (14 maisons de bois, 6 maisons blanches, 4 casernes, 4 échoppes, 3 tours de guet, 2 pavillons, 10 quartiers lointains) | ≈ 3 750 |
| `assets/vegetation.py` (29 cerisiers ≤ 40, 4 géants ≤ 150, 6 pins, 5 massifs, 8 buissons, 4 rochers, 1 étang) | ≈ 2 530 |
| `assets/colline.py` (colline, tour, monolithe, tunnel) | ≤ 1 700 |
| **Total au budget maximal** | **≈ 12 940** |

`python zone.py --stats` vérifie chaque pose (`hors_budget`), le couloir (`couloir_encombre`) et la hauteur
libre (`trop_bas_au_dessus_du_couloir`).

## 6. Propriété intellectuelle (obligatoire)

Roblox retire les contenus qui reprennent une licence sans autorisation. On n'utilise donc **que des éléments
japonais génériques** : enceintes de château blanches, tours de guet, maisons d'Edo, cerisiers, pierre sacrée.
- **Aucun nom** : ni la licence, ni ses lieux, ni ses personnages, ni dans les textes, ni dans les noms de
  pièces, ni dans le nom de la zone (`ZoneBleach` reste un nom de fichier interne ; ne pas l'afficher en jeu).
- **Aucun personnage**, PNJ ou silhouette.
- **Aucun emblème** : pas de numéros de division ni de chiffres décoratifs, pas d'insigne de division ou de
  fleur-emblème de division, pas de losange d'insigne, pas de 護廷 ni de 十三隊, pas de 霊, 魂, 死神, 隊, 卍.
  Pas de noms de portes ou de lieux de la licence.
- **Aucune réplique d'objet** : pas de sabre précis, pas de masque, pas de hallebarde géante ni d'échafaud
  d'exécution sur la colline, pas de papillons noirs, pas de portail à shoji flottant.
- Le monolithe reste un **rocher sacré générique** (corde *shimenawa*). La tour reste une **tour blanche
  générique** : bandes rouges et flèches sombres, sans pont vers le monolithe.
- **Textes permis** sur les enseignes : 門, 静, 白, 茶, 宿, 米, 湯, 薬, 団子, 蕎麦, 甘味, 呉服, 豆腐, 本, 花,
  桜 (pas d'alcool : pas de 酒).
- La mosaïque de la cour est une **fleur de cerisier à cinq pétales échancrés**, motif japonais courant, qui
  n'est pas un emblème de la licence.

Sources consultées : [Kanazawa Castle, murs d'enduit et namako](https://shiro-niwa.pref.ishikawa.lg.jp/kanazawa-castle/en/explore/wall.php),
[Kanazawa Castle, caractéristiques](https://shiro-niwa.pref.ishikawa.lg.jp/kanazawa-castle/en/explore/feature.php),
[Himeji Castle (World History)](https://www.worldhistory.org/Himeji_Castle/),
[JAANUS, hi-no-mi yagura](https://projects.mcah.columbia.edu/jaanus/node/4095),
[Tour de guet à incendie traditionnelle (Muza-chan)](https://muza-chan.net/japan/index.php/amp/traditional-japanese-fire-lookout-tower),
[Namako kabe à Hagi (Muza-chan)](https://muza-chan.net/japan/index.php/blog/namako-kabe-castle-town-walls-in-hagi).
