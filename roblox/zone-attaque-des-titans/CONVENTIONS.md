# Conventions des assets (zone Attaque des Titans, style stud)

Chaque asset est une fonction Python qui ajoute des **Parts Roblox** à un `kit.Builder`. La même liste de pièces
sert au rendu Blender et au modèle Roblox : on ne construit qu'avec les formes natives de Roblox (bloc, coin,
cylindre, boule). Lire aussi `CONCEPTION.md`, qui donne l'intention, la séquence, les budgets et les règles de
propriété intellectuelle.

## Repère et plan de la zone

- Repère **Roblox** : X à droite, **Y vers le haut**, Z vers l'arrière ; 1 unité = 1 stud. Un personnage Roblox
  mesure environ 5 studs de haut et 2 de large.
- Origine de l'asset : centre de son emprise au sol, **y = 0 = niveau du sol**.
- **L'avant de l'asset regarde -Z local.** La mise en page tourne l'asset pour que son avant regarde le couloir
  (`yaw = -90` à gauche, `+90` à droite). Les murailles à porte (`porte_colossale`), les tours d'angle, la ferme
  et le dépôt sont posés avec `yaw = 180` : leur avant regarde alors +Z, vers les joueurs qui arrivent.
- **Couloir de course très large : `x ∈ [-45, 45]` (90 studs)**, de `z = 0` (entrée, prairie) à `z = -548` (sortie
  du tunnel de la muraille intérieure). **Trottoirs jusqu'à `|x| = 55`**, alignement des façades : la grand-rue fait
  110 studs de façade à façade.
- Séquence : prairie hors les murs (z 8 → -60), muraille extérieure et son tunnel (-60 → -84), place de la porte
  (-84 → -112), rue des colombages (-112 → -214), place de l'église (-214 → -268), quartier du canal (-268 → -404,
  canal à droite en `x ∈ [55, 75]`, rive droite en `x = 79`), grand-place des œufs (-404 → -488, cercle de rayon 34
  centré en `z = -446`, façades en `|x| = 90`), parvis (-488 → -512), muraille intérieure et tunnel (-512 → -548).
- Remparts latéraux : axe `|x| = 135`, faces en `|x| = 125` (ville) et `|x| = 145` (champs), 90 studs de haut ;
  tours d'angle de 32 × 32 et 112 de haut en `(±135, -72)` et `(±135, -530)`.
- Le joueur arrive par +Z, court vers -Z, puis revient : **les deux sens de lecture comptent** (revers de la
  muraille d'entrée, façades vues en biais dans les deux sens, enseignes lisibles des deux côtés).

## Règles du couloir (vérifiées par `python zone.py --stats`)

- **Au sol** : rien de solide (`collide=True`) dans `|x| < 45` entre y = 0,05 et y = 12, sauf le sol lui-même.
- **Au-dessus** : **rien du tout** (solide ou non) au-dessus de `|x| < 46` sous **y = 30**. Sinon la caméra
  Roblox saute quand le joueur passe dessous. Ce qui enjambe le couloir (voûtes des tunnels, herses relevées,
  corps de garde, guirlandes de fanions) reste **au-dessus de 30**, et au-dessus de **46** pour les tunnels
  (`H_PASSAGE`), qui dégagent `|x| < 52` (`OUVERTURE = 104`).
- Les assets posés sur les trottoirs ou en façade gardent toute leur emprise en `|x| ≥ 46` (encorbellements,
  enseignes, lanternes, auvents : jusqu'à `|x| = 51` au plus près). Les ponts du canal restent dans `x ∈ [55, 79]`.
- `zone.py --stats` affiche `couloir_encombre`, `trop_bas_au_dessus_du_couloir` et `hors_budget` : les trois doivent
  rester vides.

## API du kit (`kit.py`)

```python
from palette import c, vary, pierre_mur   # c("tuile") → (r, g, b) ; vary("enduit_creme", b.rng) ; pierre_mur(b.rng)
from kit import shade, mix, rot_z         # shade(couleur, 0.85) assombrit ; mix(a, b, t) ; rot_z(30) pour les écharpes

def mon_asset(b, variant=0, **params):
    rng = b.rng                                   # numpy Generator (aléatoire reproductible)
    b.box((x0, y0, z0), (x1, y1, z1), c("enduit_creme"))            # bloc par deux coins
    b.boxc((cx, cy, cz), (sx, sy, sz), couleur, yaw=30)              # bloc par centre/taille, tourné autour de Y
    b.wedge((x0, y0, z0), (x1, y1, z1), couleur, down="-z")         # coin qui remplit la boîte ; la pente descend vers `down`
    b.wedge_under(a, b_, couleur, down="-z")                         # coin retourné (console, sous-face d'encorbellement)
    b.cyl((cx, cy, cz), rayon, longueur, couleur, axis="y")          # cylindre (axis x, y ou z)
    b.ball((cx, cy, cz), rayon, couleur)
    b.part("block", taille, centre, rot_z(35), couleur)              # bloc tourné librement (croix de Saint-André, ailes)
    with b.at((x, y, z), yaw=90, group="Lanternes"):                 # sous-repère (translation + rotation Y) et sous-groupe
        ...
    with b.group("Toit"):
        ...
    return {"emprise": (largeur_x, profondeur_z), "hauteur": h}
```

Options de toutes les primitives : `studs=` (`"top"`, `"all"`, `"sides"`, `"top+sides"`, `"none"` ou un tuple
de faces `("Top", "Front", …)`), `material=` (`SmoothPlastic` par défaut, `Wood`, `WoodPlanks`, `Slate`,
`Concrete`, `Brick`, `Cobblestone`, `Rock`, `Sand`, `Grass`, `Fabric`, `Metal`, `Neon`, `Glass`),
`transparency=`, `reflectance=`, `collide=False` (petits détails), `shadow=False`, `name=`.
Chaque primitive renvoie la `Part` : `p.label = {"face": "Front", "text": "PAIN", "color": (r, g, b), "bg": None,
"font": "serif"}` ajoute un panneau texte (SurfaceGui dans Roblox ; `serif` = capitales à empattements, Garamond
dans Roblox). Pour un texte lisible des deux côtés : deux pièces dos à dos, chacune avec son label.

Mobilier réutilisable (`assets/mobilier.py`, ≤ 40 pièces chacun) : `reverbere`, `lanterne_murale`, `enseigne(texte)`
(enseigne en drapeau sur potence, origine sur la face du mur), `panneau_pied`, `poteau_indicateur`, `cloture_bois`,
`banc`, `bac_fleurs`, `borne`, `caisses`, `tonneaux`, `sacs`, `charrette`, `brouette`, `canon_affut`, `etal`, `puits`,
`abreuvoir`, `pile_boulets`, `bottes_foin`, `tas_bois`, `drapeau`, `guirlande_fanions(p0, p1)`. Un asset peut les
appeler (`from assets import mobilier` puis `with b.at(...): mobilier.enseigne(b, "PAIN", variant=1)`).

Formes Roblox à connaître :
- `wedge` : face pleine au fond et dessous, pente vers `down` ; une pente avec `studs="top"` reçoit les studs.
- Un cylindre Roblox est lisse ; ses studs ne vont que sur les disques des extrémités.
- Un toit à deux pans = deux `wedge` dos à dos + une faîtière ; un toit en pavillon (tour) = quatre `wedge` en
  croix posés sur un carré, ou des gradins de blocs qui rétrécissent (plus « stud »).

## Style « stud » attendu

- Silhouettes **simples et lisibles de loin**, détails à trois échelles : masse (muraille, maison, tour), éléments
  (pilastres, toits, lucarnes, cheminées, encorbellements), petits accents (volets, jardinières, enseignes, lanternes).
  Pas de bouillie de petits blocs.
- **Couleurs franches** de `palette.py`. Grands aplats cassés en « pixels » de 3-4 teintes proches (`vary()`,
  `pierre_mur(rng)`) : la muraille surtout, en assises horizontales et pierres isolées. Pas de gris sale, pas de
  vert émeraude dominant (les verts de la palette tirent vers le jaune).
- **Studs** (`studs="top"`) sur les dessus horizontaux visibles (chemins de ronde, plateformes, socles, sols) et
  sur les pentes de toit ; **pas sur les murs des maisons**. Les faces des murailles colossales peuvent en avoir
  sur les gradins et le talus, pas sur leurs grandes faces verticales.
- Ville médiévale d'Europe centrale (Franconie, Alsace, Souabe) : maisons à **colombages** (bois brun sombre ou
  sang-de-bœuf sur enduit crème, ocre, blanc, saumon), **étages en encorbellement**, **pignons sur rue** à forte
  pente, **tuiles terre cuite** (5 teintes), quelques toits d'ardoise, **cheminées carrées de brique**, lucarnes,
  volets colorés et **géraniums** aux fenêtres ; maisons bourgeoises de pierre de taille à chaînages d'angle,
  pignons à redents ; clochers carrés de pierre à baies géminées, flèches d'ardoise ou de cuivre vert-de-gris.
- **Murailles colossales** : pierre beige-gris pâle, talus à la base, **pilastres verticaux réguliers** sur toute
  la hauteur, cordon et corniche, parapet crénelé, chemin de ronde large, canons sur rails, grues et
  monte-charges de bois, tourelles de guet. Elles doivent écraser la ville par leur masse.

## Propriété intellectuelle (obligatoire)

Roblox retire les contenus qui reprennent une licence sans autorisation. On ne fait qu'une **ville médiévale
européenne fortifiée générique** :
- **Aucun nom** : ni la licence, ni ses murs, districts ou villes, ni ses personnages ou unités, ni dans les textes,
  ni dans les noms de pièces ou de groupes, ni dans le nom affiché de la zone.
- **Aucun personnage, aucun géant, aucune figure humanoïde** (pas de statue humaine sur la fontaine, pas
  d'épouvantail), **aucun visage** sur les murs, pas de main, de crâne ni de silhouette qui dépasse d'une muraille.
- **Aucun emblème** : pas d'ailes, de roses, de licorne, d'épées croisées, de blason ou d'insigne militaire ; les
  drapeaux et bannières sont **unis ou à bandes** (rouge, vert, bleu, blanc, jaune). Aucune réplique d'équipement
  (pas d'harnais à grappins, de lames, de bonbonnes de gaz, de capes vertes).
- **Textes permis** sur les enseignes (`mobilier.TEXTES_ENSEIGNES`) : PAIN, BOULANGERIE, AUBERGE, MARCHÉ, FROMAGES,
  FORGE, TISSUS, HORLOGER, FLEURS, LÉGUMES, SAVON, LIBRAIRIE, BÄCKEREI, GASTHAUS, MARKT, BROT ; panneaux
  indicateurs : MARCHÉ, AUBERGE, FONTAINE. Rien d'autre (pas de chiffres, pas de dates, pas d'alcool).

## Règles techniques Roblox

- **Pas de faces coplanaires qui se chevauchent** (scintillement) : un détail posé sur un mur dépasse d'au moins
  0,1 stud ; deux blocs qui se recouvrent ne partagent pas une face au même endroit avec des couleurs différentes.
  Les segments de rempart se touchent bout à bout : leurs assises et corniches sont aux mêmes hauteurs.
- Rien ne flotte : tout repose sur quelque chose (sauf cordes, fanions, lanternes et charges suspendues, accrochés
  à un support).
- Taille minimale 0,1 stud. Préférer des tailles entières ou au demi-stud.
- **Budget de pièces** : respecter celui de chaque fonction (tableau de `CONCEPTION.md`, contrôlé par
  `zone.py --stats`). Un grand aplat = un seul bloc. Total de la zone ≤ 13 500 pièces.
- `collide=False` pour les petits détails décoratifs hors de portée (enseignes, cordes, feuillage fin, volets,
  jardinières, croisillons), `shadow=False` pour les éléments très fins.

## Aperçu

```bash
cd roblox/zone-attaque-des-titans
PY=/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/bvenv/bin/python   # Python avec bpy 5.2
$PY apercu.py assets.batiments:maison_colombages --variant 1 --params '{"etages": 4}' --res 1200x675 --samples 12
$PY apercu.py assets.remparts:porte_colossale --cam "0,30,-160" --target-pt "0,40,0" --res 1200x675 --samples 12
$PY zone.py --stats                                             # couloir libre, hauteur libre, budgets
$PY rendu.py --rapide --sans-export --vues entree,rue           # contrôle dans la zone
```

La vue A regarde l'avant (côté -Z) en 3/4, la vue B l'arrière, plus haut. Regarder les images avec l'outil Read.
Le processeur est partagé : aperçus en 1200 × 675 au plus, 12 à 16 échantillons.
