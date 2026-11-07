# Conventions des assets (zone Black Clover, style stud)

Chaque asset est une fonction Python qui ajoute des **Parts Roblox** à un `kit.Builder`. La même liste de pièces
sert au rendu Blender et au modèle Roblox : on ne construit qu'avec les formes natives de Roblox (bloc, coin,
cylindre, boule). Lire aussi `CONCEPTION.md` (intention, séquence, palette, budgets, propriété intellectuelle) et
`SPECS.md` (fiche de chaque module d'assets).

## Repère et plan de la zone

- Repère **Roblox** : X à droite, **Y vers le haut**, Z vers l'arrière ; 1 unité = 1 stud. Un personnage Roblox
  mesure environ 5 studs de haut et 2 de large.
- Origine de l'asset : centre de son emprise au sol, **y = 0 = niveau du sol** (objets flottants : voir § Magie).
- **L'avant de l'asset regarde -Z local.** La mise en page tourne l'asset pour que son avant regarde le couloir
  (`yaw = -90` à gauche, `+90` à droite). La porte d'entrée, l'enceinte et le château sont posés avec `yaw = 180` :
  leur avant regarde alors +Z, vers les joueurs qui arrivent. Rotation `yaw` : `R_y(yaw) · (0, 0, -1) =
  (-sin yaw, 0, -cos yaw)` donne la direction de l'avant dans le monde (yaw 125 : vers -X et +Z).
- **Couloir de course très large : `x ∈ [-45, 45]` (90 studs)**, de `z = 0` (entrée) à `z = -548` (sortie par la
  porte du château). **Accotements jusqu'à `|x| = 55`** : alignement des façades (57 dans les champs).
  Abords de `z = 0` à `z = +40`, dans le groupe racine `Abords` (supprimable quand les zones sont mises bout à bout).
- Séquence : abords (+40 → 0), **porte d'entrée** (0 → -32 ; tours en `|x| = 63`, axe `z = -16`), **champs**
  (-32 → -80 ; côtes géantes en (118, -70)), **village abandonné** (-80 → -196 ; église en (-77, -154), colline et
  **crâne** en (132, -158)), **bourg** (-196 → -300 ; **tour aux grimoires** en (-94, -250)), **champ de bataille**
  (-300 → -404 ; **aqueduc** en `z = -352`), **place rituelle** (-404 → -498 ; **cercle magique** de rayon 34 centré
  en `z = -448`, **arbre démoniaque** en (150, -462), îlots flottants à gauche), **château démoniaque**
  (-498 → -548, posé en (0, -523)).
- Côtés : champs et blé jusqu'à `|x| = 175`, lisières de sapins sombres, falaises noires à partir de `z = -300`
  (`|x|` ≥ 180), montagne de la capitale en (-200, -112). Fin du sol et murs invisibles en `|x| = 239`.
- Le joueur arrive par +Z, court vers -Z, puis revient : **les deux sens de lecture comptent** (revers des tours
  d'entrée, façades vues en biais dans les deux sens, enseignes lisibles des deux côtés).

## Règles du couloir (vérifiées par `python zone.py --stats`)

- **Au sol** : rien de solide (`collide=True`) dans `|x| < 45` entre y = 0,05 et y = 12, sauf le sol lui-même
  (groupes `Sol/…`, dont l'estrade du cercle magique, 0,85 de haut au plus).
- **Au-dessus** : **rien du tout** (solide ou non) au-dessus de `|x| < 46` sous **y = 30**. Sinon la caméra Roblox
  saute quand le joueur passe dessous. Lucioles, bannières, branches au-dessus du couloir : au-dessus de 31.
- Ce qui **enjambe** le couloir garde **au moins 92 studs entre ses appuis** (appuis en `|x| ≥ 46`) et son
  **dessous à 34 ou plus** : aqueduc (piles en `|x| ≥ 47`, dessous de l'arche centrale ≥ 36), porte du château
  (ouverture **100** : `|x| < 50`, montants jusqu'à **40**, arc brisé au-dessus ; tout ce qui passe au-dessus du
  couloir est au-dessus de 40). La sortie en `z = -548` reste **ouverte**.
- Les assets posés sur les accotements gardent toute leur emprise en `|x| ≥ 46` (enseignes, lanternes, bâtons,
  étals, vantaux : jusqu'à `|x| = 47` au plus près).
- `zone.py --stats` affiche `couloir_encombre`, `trop_bas_au_dessus_du_couloir` et `hors_budget` : les trois doivent
  rester vides. `zone.py --chevauchements` liste les assets posés qui se recoupent.

## API du kit (`kit.py`)

```python
from palette import c, vary, pierre, moellon, roche, os_teinte   # c("ardoise") → (r, g, b) ; vary("pierre", b.rng)
from kit import shade, mix, rot_x, rot_y, rot_z                   # shade(couleur, 0.85) assombrit ; mix(a, b, t)

def mon_asset(b, variant=0, **params):
    rng = b.rng                                   # numpy Generator (aléatoire reproductible)
    b.box((x0, y0, z0), (x1, y1, z1), c("pierre"))                  # bloc par deux coins
    b.boxc((cx, cy, cz), (sx, sy, sz), couleur, yaw=30)              # bloc par centre/taille, tourné autour de Y
    b.wedge((x0, y0, z0), (x1, y1, z1), couleur, down="-z")         # coin qui remplit la boîte ; la pente descend vers `down`
    b.wedge_under(a, b_, couleur, down="-z")                         # coin retourné (console, sous-face d'encorbellement)
    b.cyl((cx, cy, cz), rayon, longueur, couleur, axis="y")          # cylindre (axis x, y ou z)
    b.ball((cx, cy, cz), rayon, couleur)
    b.part("block", taille, centre, rot_z(35), couleur)              # bloc tourné librement (cornes, branches, flèches)
    with b.at((x, y, z), yaw=90, group="Flèche"):                    # sous-repère (translation + rotation Y) et sous-groupe
        ...
    with b.group("Toit"):
        ...
    return {"emprise": (largeur_x, profondeur_z), "hauteur": h}
```

Options de toutes les primitives : `studs=` (`"top"`, `"all"`, `"sides"`, `"top+sides"`, `"none"` ou un tuple de
faces), `material=` (`SmoothPlastic` par défaut, `Wood`, `WoodPlanks`, `Slate`, `Concrete`, `Brick`, `Cobblestone`,
`Rock`, `Sand`, `Grass`, `Fabric`, `Metal`, `Neon`, `Glass`), `transparency=`, `reflectance=`, `collide=False`
(petits détails), `shadow=False`, `name=`. Chaque primitive renvoie la `Part` : `p.label = {"face": "Front",
"text": "TAVERNE", "color": (r, g, b), "bg": None, "font": "serif"}` ajoute un panneau texte (SurfaceGui dans
Roblox ; polices `serif` (capitales à empattements, Garamond dans Roblox) — la police de cette zone —, `sans`,
`brush`). Pour un texte lisible des deux côtés : deux pièces dos à dos, chacune avec son label.

Mobilier réutilisable (`assets/mobilier.py`, ≤ 40 pièces chacun ; `from assets import mobilier`, puis
`with b.at(...): mobilier.enseigne(b, "TAVERNE", variant=1)`) :
- éclairage et feux : `lanterne_fer(variant 0-3)`, `lanterne_murale(0-2)` (origine sur la face du mur),
  `brasero(0-3 : orange, violet, cramoisi, vert)`, `feu_camp(0-3)`, `chaudron(0-2)` ;
- bataille : `baton_mage(0-3 : orbe violet, vert, doré, cramoisi)`, `epee_plantee(0-3)`, `bouclier(0-3)`,
  `armes_abandonnees(0-2)` ;
- village et bourg : `caisses`, `tonneaux`, `etal(0-3)`, `puits(0-2)`, `charrette(0-2)`, `meule`,
  `enseigne(texte, variant)` (en drapeau, origine sur la face du mur, dépasse vers -Z), `panneau_pied(texte)`,
  `poteau_indicateur(textes)`, `cloture_bois(longueur)`, `muret(longueur)`, `banniere(variant, hauteur)` (toile dans
  le plan X-Y), `banniere_murale(variant, hauteur)` (origine sur la face du mur, en haut), `pierre_tombale(0-3)`,
  `pierre_runique(0-3)` ;
- magie : `grimoire_volant(0-5)` (origine au centre du livre), `nuee_grimoires(variant, rayon, hauteur, nombre)`,
  `lucioles(variant, rayon, hauteur, nombre)` ;
- petite nature : `arbre_mort(variant, hauteur)`, `sapin_sombre(variant, hauteur)`, `rocher(variant, taille)`,
  `epines_racines(variant, taille)` ;
- outil : `chaine(b, p0, p1, maillon=1.4, epaisseur=0.3, couleur=None, creux=0.0)` (maillons alternés, ≤ 40).

Formes Roblox à connaître :
- `wedge` : face pleine au fond et dessous, pente vers `down` ; une pente avec `studs="top"` reçoit les studs.
- Un cylindre Roblox est lisse ; ses studs ne vont que sur les disques des extrémités.
- Toit conique (tours) : anneaux de cylindres qui rétrécissent (6 à 10 anneaux), ou gradins octogonaux de blocs ;
  flèche gothique : 4 coins en croix sur un carré ou blocs carrés qui rétrécissent, tournés de 45° un sur deux.
- Courbe (corne, côte, racine, branche) : chaîne de 4 à 8 blocs tendus de point à point (comme `mobilier._poutre`),
  section décroissante, petites rotations successives.

## Style « stud » attendu

- Silhouettes **simples, fortes et lisibles de loin**, détails à trois échelles : masse (tour, crâne, château),
  éléments (toits coniques, flèches, cornes, contreforts, baies), petits accents (lanternes, bannières, lierre,
  fissures, glyphes). Pas de bouillie de petits blocs.
- **Sombre mais lisible en plein jour** : grandes masses foncées en « pixels » de 3-4 tons (`vary()`,
  `pierre(rng)`, `moellon(rng)`, `roche(rng)`), le noir pur (`obsidienne`) réservé aux creux et aux arêtes ; chaque
  masse sombre de plus de 20 studs porte des **lueurs** (Neon) visibles du couloir : fenêtres, veines, fissures,
  cristaux, flammes. Contrepoints clairs : os ivoire du crâne, tour aux grimoires plus claire, lucioles dorées.
- **Studs** (`studs="top"`) sur les dessus horizontaux visibles (chemins de ronde, socles, plateformes, terrasses
  de colline, gradins de falaise) et sur les pentes de toit ; **pas sur les murs des maisons**, ni sur l'os du
  crâne, ni sur les troncs.
- **Pas de vert émeraude** : verts olive, mousse, gris-vert sapin ; seul vert vif : `lueur_verte` (orbes, chaudrons).
- **Neon** pour toutes les lueurs, avec mesure (≤ ≈ 900 pièces Neon pour toute la zone ; le sol et le mobilier en
  posent déjà ≈ 330). Transparence : presque jamais.

## Magie flottante (voulue)

Grimoires, lucioles, orbes, îlots de roche peuvent flotter, **parce que c'est magique**, à condition de se lire
comme un dessin et d'être **alignés sur une source** : spirale autour de la tour aux grimoires (et livres qui
sortent de ses fenêtres), nuée au-dessus d'un pupitre gravé, nuage de lucioles autour d'une tour ou d'un îlot,
orbe tenu par un bâton, îlot relié au sol par des chaînes et des ancrages. Jamais une pièce isolée qui flotte
« par erreur » : tout le reste repose sur quelque chose ou est accroché à un support. Objet flottant posé par
`zone.py` : origine au centre de l'objet (grimoire) ou au centre du dessus (îlot), à la hauteur voulue.

## Propriété intellectuelle (obligatoire)

Roblox retire les contenus qui reprennent une licence sans autorisation. On ne fait qu'une **fantasy sombre
générique** :
- **Aucun nom** de la licence, de ses lieux, escouades, personnages, démons, sorts ou arbre, ni dans les textes, ni
  dans les noms de pièces ou de groupes, ni dans le nom affiché de la zone.
- **Aucun personnage**, statue, silhouette humanoïde, squelette humain ; **pas de statue sur le crâne** ; crâne à
  **deux orbites** seulement.
- **Aucune forme de trèfle** (3, 4 ou 5 feuilles) nulle part, **pas de quadrilobe** dans les fenêtres gothiques ;
  aucun emblème (taureau, lion, aigle, rose…), aucun blason ; bannières et boucliers **unis ou à liseré** ;
  grimoires à **couvertures unies** (bande ou coins dorés au plus) ; pas de grande épée noire à lame large.
- Cercle magique et glyphes : géométrie abstraite, **aucune étoile** (5, 6 ou 8 branches), aucune lettre d'un
  alphabet réel. **Aucun symbole religieux** (croix, croissant, étoile), ni sur l'église ni sur les tombes.
- **Textes permis** (`mobilier.TEXTES_ENSEIGNES`) : TAVERNE, AUBERGE, GRIMOIRES, MARCHÉ, FORGE, BIBLIOTHÈQUE,
  HERBORISTE, POTIONS, BOULANGERIE, PAIN, ARMURERIE ; indicateurs (`mobilier.TEXTES_INDICATEURS`) : VILLAGE,
  MARCHÉ, TAVERNE, GRIMOIRES, CHÂTEAU, TOUR. Rien d'autre (pas de chiffres, pas de dates).

## Règles techniques Roblox

- **Pas de faces coplanaires qui se chevauchent** (scintillement) : un détail posé sur un mur dépasse d'au moins
  0,1 stud ; deux blocs qui se recouvrent ne partagent pas une face au même endroit avec des couleurs différentes.
  Les segments d'enceinte se touchent bout à bout : leurs assises, chemins de ronde et merlons sont aux mêmes
  hauteurs.
- Rien ne flotte par accident (voir § Magie). Taille minimale 0,1 stud ; préférer des tailles entières ou au
  demi-stud.
- **Budget de pièces** : respecter celui de chaque fonction (`SPECS.md`, contrôlé par `zone.py --stats`). Un grand
  aplat = un seul bloc. Total de la zone ≤ 13 500 pièces.
- `collide=False` pour les petits détails décoratifs hors de portée (lierre, bannières, livres volants, fissures,
  glyphes, chaînes), `shadow=False` pour les éléments très fins.
- Ne pas poser de sol dans le couloir ni sur les accotements : `zone.py` peint tout le sol (y ≤ 0).

## Aperçu

```bash
cd roblox/zone-black-clover
PY=/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/bvenv/bin/python   # Python avec bpy 5.2
$PY apercu.py assets.mobilier:brasero --variant 1 --res 1200x675 --samples 12
$PY apercu.py assets.monuments:crane_demon --cam "-60,50,-110" --target-pt "0,40,0" --res 1200x675 --samples 12
$PY zone.py --stats                                             # couloir libre, hauteur libre, budgets, Neon
$PY zone.py --chevauchements                                    # assets posés qui se recoupent
$PY rendu.py --rapide --sans-export --vues entree,crane         # contrôle dans la zone
$PY rendu.py --rapide --sans-export --vues final --ambiance crepuscule --suffixe=-crepuscule
```

La vue A regarde l'avant (côté -Z) en 3/4, la vue B l'arrière, plus haut. Regarder les images avec l'outil Read.
Le processeur est partagé : aperçus en 1200 × 675 au plus, 12 à 16 échantillons, jamais deux rendus à la fois.
