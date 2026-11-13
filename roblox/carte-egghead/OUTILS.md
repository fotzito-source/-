# Outils de la carte « île du futur » (CarteEgghead)

Carte autonome d'un nouveau jeu Roblox (pas une zone de couloir) : une île scientifique futuriste, **sol entièrement
en studs**, bâtiments **arrondis, propres, façon jouet** (dômes, œufs, anneaux, cônes rayés, tubes de verre), en
**plein soleil tropical**. Même chaîne que les zones précédentes, étendue aux formes rondes :

```
carte.py + assets/*.py ──► kit.Builder ──► build/parts.json ──┬──► blender_scene.py ──► rendus PNG, .blend, .glb
                                                              └──► roblox_export.luau (Lune) ──► .rbxm, .rbxmx, -demo.rbxl
```

`CarteEgghead` est un nom de fichier interne, jamais affiché aux joueurs.

## Fichiers

| Fichier | Rôle |
|---|---|
| `kit.py` | Le kit : `Builder`, primitives (bloc, coin, cylindre, boule, **ellipsoïde**), assemblages arrondis, repères, découpage, contrôles, export Lune |
| `carte.py` | La carte complète : sol, routes, couronne, barrière invisible des façades, tapis, centre, ciel, mobilier, repères ; `--stats` (pièces, budgets, contrôles) et `--export DOSSIER` (Lune) |
| `assets/exemple.py` | Asset de référence : kiosque rond (conventions, budget, panneau) |
| `assets/test_primitives.py` | Vitrine de toutes les formes du kit (contrôle visuel et d'export) |
| `blender_scene.py` | Scène Blender : maillages des pièces, matériau stud, ciel tropical, brume, caméras, rendu Cycles, exports |
| `rendu.py` | Rendus de la carte (vues aerienne, plan, joueur…) et exports (.blend, .glb, puis Lune) |
| `apercu.py` | Aperçu d'un asset isolé sur un petit sol stud (une ou plusieurs caméras) |
| `roblox_export.luau` | Conversion en fichiers Roblox avec Lune : modèle, place de démo, relecture et contrôles |
| `textures.py` | Texture stud (calque) et images des panneaux de texte ; polices téléchargées depuis google/fonts |

Dossiers produits : `build/` (parts.json), `apercus/`, `.cache/` (polices), `textures/panneaux/` : ignorés par git ;
`rendus/` (images finales) : suivi ; les comparaisons avec les captures de l'utilisateur restent hors du dépôt (public) ; `export/` : `.rbxm` et `-demo.rbxl` suivis,
`.blend`, `.rbxmx` et `.glb` ignorés (le `.blend` reste dans le dossier, il se régénère).

## Repère et conventions

- Repère **Roblox** : X à droite, **Y vers le haut**, Z vers l'arrière ; **1 unité = 1 stud**. Un personnage mesure
  environ 5 studs de haut et 2 de large ; la caméra Roblox le suit d'environ 12 studs.
- **Origine de la carte = centre de la carte, au niveau du sol (y = 0)** : c'est le pivot du modèle Roblox
  (`workspace.CarteEgghead:PivotTo(CFrame.new(X, Y, Z))` pose ce centre en (X, Y, Z)). Le dessus du sol est à y = 0.
- **Origine d'un asset : centre de son emprise au sol, y = 0.** Un objet en lévitation se décrit par son centre,
  à la hauteur voulue, et doit être relié à une source visible (faisceau, socle, câble : voir `boule_flottante`).
- **L'avant d'un asset regarde -Z local.** La carte l'oriente avec `b.at(pos, yaw=…)` : la direction de l'avant
  dans le monde vaut `R_y(yaw) · (0, 0, -1) = (-sin yaw, 0, -cos yaw)` (yaw 90 : l'avant regarde -X ; yaw 180 : +Z).
- **Rotations libres** : matrices `rot_x(deg)`, `rot_y(deg)`, `rot_z(deg)`, composées de droite à gauche :
  `rot_y(30) @ rot_x(20)` incline d'abord de 20° autour de X, puis tourne de 30° autour de Y. Partout où un
  paramètre `rot=` existe, un nombre seul vaut un yaw en degrés. `repere_normale(n)` (axe Y local = `n`) et
  `repere_direction(d, haut)` (axe X local = `d`, axe Y au plus près de `haut`) construisent des rotations à partir
  de directions. Les matrices sont celles des `CFrame` Roblox : colonnes = axes X, Y, Z locaux dans le monde
  (`RightVector`, `UpVector`, `-LookVector`).
- **Groupes** : `b.group("Toit")` et `b.at(..., group="Labo")` deviennent des `Model` imbriqués dans Roblox et des
  collections dans Blender. Le groupe racine `Reperes` devient un `Folder`. Le groupe `Sol` est rangé en blocs
  de 64 × 64 (`b.decouper`) : avec StreamingEnabled, Roblox envoie de toute façon les pièces une à une selon leur
  position ; les blocs rangent l'Explorer par quartiers et permettent de régler un quartier d'un coup
  (`ModelStreamingMode`).
- **Précision** : tailles et positions arrondies à 4 décimales, matrices de rotation à 6. Lune range ensuite les
  flottants des propriétés sur une grille de 2^-16 (≈ 0,000015 stud) : sans effet visible.
- **Couleurs** : `"#RRGGBB"`, `"#RGB"` ou tuple `(r, g, b)` 0-255 (`hexrgb` convertit) ; `shade(c, 0.85)`
  assombrit, `shade(c, 1.2)` éclaircit, `mix(a, b, t)` mélange, `varier(c, b.rng, 0.05)` tire une nuance voisine
  (casse les grands aplats).
  La palette de la carte viendra de la bible de style (`palette.py`) ; les fichiers de l'atelier utilisent des
  constantes locales provisoires.
- **Aléatoire** : `b.rng` (numpy, graine fixe) ; jamais `random` : la carte doit se reconstruire à l'identique.

## API du kit (`kit.py`)

```python
from kit import Builder, rot_x, rot_y, rot_z, shade, mix, varier, VERRE, NEON_CYAN, BLANC_LABO

def mon_asset(b, variant=0, **params):
    with b.group("Corps"):
        ...
    return {"emprise": (largeur_x, profondeur_z), "hauteur": h}     # résumé affiché par apercu.py
```

### Builder, repères, groupes

| Appel | Effet |
|---|---|
| `b = Builder(seed=7)` | Liste de pièces vide ; `b.parts`, `b.rng` |
| `with b.at(pos, yaw=0, group=None, rot=None):` | Sous-repère : translation, rotation autour de Y puis `rot` (matrice), sous-groupe facultatif |
| `with b.group("Nom"):` | Sous-groupe (Model Roblox) |
| `b.to_world(p)` | Point du repère courant → repère de la carte |
| `b.stats()` | Pièces par groupe racine |
| `b.save_json(chemin, meta)` | Écrit parts.json (lu par Blender et par Lune) |

Toutes les positions données aux primitives et aux assemblages sont dans le **repère courant** (`b.at`).

### Primitives (1 pièce chacune)

```python
b.box((x0, y0, z0), (x1, y1, z1), couleur, studs="top")          # bloc par deux coins (aligné sur les axes)
b.boxc((cx, cy, cz), (sx, sy, sz), couleur, yaw=30)              # bloc par centre et taille, tourné autour de Y
b.wedge(a, b_, couleur, down="-z", studs="top")                  # coin qui remplit la boîte ; pente vers `down`
b.wedge_under(a, b_, couleur, down="-z")                         # coin retourné (console, sous-face d'avancée)
b.cyl((cx, cy, cz), rayon, longueur, couleur, axis="y", studs="top")   # cylindre (axis x, y ou z)
b.ball((cx, cy, cz), rayon, couleur)                             # boule (un seul diamètre)
b.ellipsoid((cx, cy, cz), (dx, dy, dz), couleur, rot=None)       # ellipsoïde de diamètres dx, dy, dz
b.part("block", taille, centre, rot_z(35), couleur)              # forme et rotation libres ("block", "wedge", "cyl", "ball", "ellipsoid")
```

Options communes : `studs=` (`"top"`, `"all"`, `"sides"`, `"top+sides"`, `"none"` ou tuple de faces `("Top",
"Front")` ; sur un cylindre, seuls les disques des bouts en reçoivent), `material=` (`SmoothPlastic` par défaut,
`Plastic`, `Wood`, `WoodPlanks`, `Slate`, `Concrete`, `Brick`, `Cobblestone`, `Rock`, `Sand`, `Grass`, `Fabric`,
`Metal`, `Neon`, `Glass`), `transparency=`, `reflectance=`, `collide=False`, `shadow=False`, `name=`, `attrs={}`
(attributs Roblox). Chaque primitive renvoie la `Part`. Panneau texte sur un **bloc** : `p.label = {"face": "Front",
"text": "INFO", "color": (r, g, b), "bg": None, "font": "rond"}` (SurfaceGui dans Roblox). Polices : `rond`
(Fredoka / FredokaOne dans Roblox, par défaut), `futur` (Michroma), `sans` (GothamBlack), `serif` (Garamond),
`brush` (GothamBold). Pour un texte lisible des deux côtés : deux pièces dos à dos.

**Studs et matériau** : une pièce à studs est exportée en `Plastic` (seul matériau où Roblox affiche les studs
intégrés), quel que soit son `material`, et le rendu Blender fait de même. Le kit **refuse les studs sur `Neon` et
`Glass`** (ils perdraient leur aspect) ; pour un sol transparent à studs : `material="Plastic", transparency=0.5`.

**L'ellipsoïde** est une `Part` de forme Block qui porte un `SpecialMesh` (MeshType `Sphere`, Scale 1, 1, 1, sans
décalage) : Roblox dessine l'ellipsoïde inscrit dans la boîte de la pièce, ses diamètres sont `Part.Size`
(redimensionner la pièce dans Studio redimensionne l'ellipsoïde). À savoir :
- **collision = la boîte entière** de la pièce, pas la forme : un joueur bute sur les coins invisibles. Le kit ne
  coupe rien tout seul : `collide=False` pour un décor, ou `dome(..., collision="gradins")` pour un dôme praticable ;
- **jamais de studs** (refusés par le kit, contrôlés à l'export) ni de panneau texte (le maillage cache les
  surfaces de la pièce) ;
- `Neon` et `Glass` + `transparency` fonctionnent comme sur les autres pièces (le verre peut paraître un peu plus
  « plastique transparent » que sur un bloc) ;
- ne pas changer `Part.Shape` dans Studio (une boule force un diamètre unique).

### Outils de placement

```python
b.cyl_entre(p0, p1, rayon, couleur)                      # barre / conduite tendue entre deux points (1 pièce)
b.bloc_entre(p0, p1, largeur, epaisseur, couleur, haut=(0, 1, 0), studs="top")   # passerelle, rampe (1 pièce)
b.repere("Spawn", (x, 0, z), taille=(6, 1, 6), yaw=0)    # repère invisible du jeu (dossier Reperes), 1 pièce
b.decouper(("Sol",), taille=64)                          # range Sol/… en Sol/Bloc_i_j/… (quartiers de 64 × 64)
```

`repere` range toujours la pièce dans le dossier racine `Reperes`, quel que soit le groupe courant ; `centre` est
le point au sol (bas de la boîte) et l'avant (-Z tourné de `yaw`) donne la direction du regard. Dans Roblox :
`Transparency` 1, `CanCollide` false, `CanTouch` et `CanQuery` true (détectable par `.Touched` et les raycasts).
Le repère **`Spawn`** place le `SpawnLocation` de la place de démo (même point, même orientation).

### Assemblages arrondis

Ce sont des méthodes du `Builder`, faites uniquement de primitives. Chacune renvoie un objet **`Pieces`** : la
liste des `Part` créées (`len(res)` = nombre de pièces) plus `res.info` (repères utiles : `sommet`, `segments`…,
dans le repère courant). `res.regler(collide=False, shadow=False)` change un attribut sur toutes ses pièces.
Les `**kw` (material, transparency, collide, shadow, name…) passent aux pièces principales.

Orientation des assemblages plans (`anneau`, `disque`, `cone_etage`, `dome`) : `axe="y"` (à plat, normale +Y),
`"z"` (debout, face à Z), `"x"` (debout, face à X) ou un vecteur normal quelconque, puis `rot=` pour incliner.

#### `anneau` — tore, arche, rail courbe
```python
b.anneau(centre, rayon, epaisseur, couleur, n=24, *, axe="y", rot=None, arc=360, depart=0,
         section="rond", largeur=None, **kw)
b.anneau((0, 9, 0), 12, 0.6, NEON_CYAN, 24, material="Neon", collide=False)        # halo lumineux horizontal
b.anneau((0, 0, 0), 6, 1.0, ["#FFFFFF", "#E8423F"], 20, axe="z", arc=180, section="carre")   # arche rayée au sol
b.anneau((0, 6, 0), 6.4, 0.6, "#FF7EB6", 24, rot=rot_x(18) @ rot_z(10), material="Neon")    # anneau incliné
```
`rayon` = ligne médiane ; `section` : `"rond"` (cylindres de diamètre `epaisseur`), `"carre"`, `"plat"` (blocs :
`epaisseur` le long de la normale, `largeur` dans le rayon). Angles (`depart`, `arc`), dans le plan de l'anneau :
`axe="y"` : 0 = +X, 90 = -Z ; `axe="z"` : 0 = +X, 90 = +Y ; `axe="x"` : 0 = -Z, 90 = +Y (pour `"z"` et `"x"`,
`arc=180` donne une arche posée au sol). Couleur unique ou liste alternée.
**Pièces : `round(n × arc / 360)`** (24 pour un anneau complet). Les segments sont allongés pour fermer les joints
extérieurs ; aux bouts d'un arc, le coin extérieur de la face extrême tombe exactement sur l'angle de départ ou
d'arrivée (une arche dont le centre est au niveau du sol a les pieds entièrement dans le sol, sans jour). En
`"carre"` et `"plat"`, deux segments qui se recouvrent ont toujours des épaisseurs différentes (paliers de +0,04)
pour qu'aucune face ne soit confondue (`res.info["paliers"]`) ; ces paliers laissent de fines lèvres de 0,02 aux
joints.

#### `disque` — plateau rond, bord de chapeau, auvent, rondelle
```python
b.disque(centre, rayon, epaisseur, couleur, *, rayon_int=0, n=24, axe="y", rot=None, **kw)
b.disque((0, 0.4, 0), 8, 0.8, "#C9D1DE", studs="top")          # socle rond stud : 1 pièce
b.disque((0, 12, 0), 9, 0.4, "#FFFFFF", rayon_int=5, n=24)     # bord plat autour d'une tour de rayon 5 : 24 pièces
```
`centre` = milieu de l'épaisseur. Plein : 1 cylindre (`studs="top"` sur le dessus). Percé : `n` blocs ; le bord
intérieur est inscrit dans le cercle `rayon_int` (caché dans une colonne de ce rayon). Si le trou est minuscule
devant la largeur, préférer un disque plein (moins de pièces, pas de paliers).

#### `cone_etage` — tour conique, flèche, cône rayé
```python
b.cone_etage(base, rayon_bas, rayon_haut, hauteur, couleurs, etages=8, *, axe="y", rot=None,
             pointe=None, profil="milieu", hauteurs=None, **kw)
b.cone_etage((0, 0.6, 0), 5, 0.4, 16, ["#E8423F", "#FFFFFF"], etages=8, pointe="#FFC93C")   # cône rayé
```
Cylindres empilés de plus en plus fins ; `profil="milieu"` (silhouette au plus près du cône) ou `"bas"` (gradins
marqués) ; `hauteurs=[…]` pour des rayures inégales ; `pointe` = couleur ou `(couleur, rayon)` ; `studs="top"` sur
les marches. **Pièces : `etages` (+1 pointe).** `res.info["sommet"]`.

#### `dome` — coupole sans couture
```python
b.dome(base, rayon, hauteur, couleur, *, rebord=None, tambour=0, couleur_tambour=None,
       materiau_tambour="SmoothPlastic", studs_tambour=(), axe="y", rot=None, collision="boite", **kw)
b.dome((0, 5, 0), 7, 6, "#FFFFFF", tambour=5, couleur_tambour="#FF7EB6", studs_tambour="top")
b.dome((0, 1, 0), 7.5, 6.5, VERRE, material="Glass", transparency=0.4)                       # dôme de verre
```
`base` = centre du plan d'appui, `rayon` = rayon du **support** (tambour créé ici ou tour existante) : le dôme
mesure `rayon - rebord` (rebord par défaut max(0,2 ; 4 % du rayon)), ce qui évite la couture dentelée et le
scintillement au raccord avec le cylindre. L'ellipsoïde est entier : **sa moitié basse descend de `hauteur` sous
`base` et doit être cachée** dans un volume plein (tambour ≥ hauteur, tour, bâtiment, sol épais) ;
`res.info["dessous_visible"]` signale un tambour trop court. `collision` : `"boite"` (la boîte de l'ellipsoïde
bloque, selon `collide`), `"aucune"`, `"gradins"` (+4 cylindres invisibles en escalier : dôme praticable).
**Pièces : 1 (+1 tambour, +4 gradins).** `res.info["sommet"]` pour poser une flèche.

#### `oeuf` — bâtiment en œuf
```python
b.oeuf(base, rayon, hauteur, couleur, *, ventre=0.4, enfonce=0, rot=None, **kw)
b.oeuf((0, 0.8, 0), 4, 11, "#FFFFFF", ventre=0.38, enfonce=0.6)
```
`base` = point le plus bas, `rayon` = rayon maximal (à mi-hauteur). Deux ellipsoïdes : un « ventre » bas et rond
et un grand ellipsoïde sur toute la hauteur ; sous la ligne du ventre, le grand reste caché dans le petit (vérifié
par le kit). `ventre` 0,5 = ellipsoïde simple ; 0,35-0,42 = œuf franc. `enfonce` pose l'œuf sur une assise plate.
**Pièces : 2 (1 si `ventre` = 0,5).** Un œuf est aussi, plus simplement, `b.ellipsoid` plus haut que large.

#### `tube` — tube de verre, couloir vitré, conduite
```python
b.tube(p0, p1, rayon, couleur=VERRE, *, materiau="Glass", transparence=None, colliers=0,
       couleur_collier=BLANC_LABO, epaisseur_collier=None, longueur_collier=None, coeur=None, creux=0, **kw)
b.tube((-9, 10.5, 0), (9, 8, 0), 1.3, colliers=3, coeur=NEON_CYAN)       # tube de verre, bagues, fil Neon
b.tube((-12, 4.2, 0), (12, 4.2, 0), 4.2, creux=12, colliers=2)          # couloir vitré où l'on peut marcher
b.tube(a, b_, 0.6, "#8A93A6", materiau="SmoothPlastic", colliers=2)     # conduite opaque
```
Plein : 1 cylindre (verre à 0,45 de transparence par défaut). `creux=n` (8-16) : n lames, une lame à plat au fond ;
**praticable si `rayon` ≥ 4** (hauteur intérieure ≈ 2 × (rayon − 0,08 × rayon), un personnage mesure ≈ 5 studs ;
le sol du couloir est à `rayon − épaisseur` sous l'axe). `colliers` : nombre (1 = milieu, 2 = bouts, k = régulier)
ou liste de fractions ; une bague posée à un bout dépasse de 0,05 (sa face ne se confond pas avec le bout du
tube) ; sur un tube creux, chaque bague est creuse (`anneau` plat de `creux` segments posés sur les lames : le
couloir reste ouvert) et une lame sur deux est plus longue de 0,04 (bouts jamais dans le même plan). `coeur` :
fil Neon dans l'axe, arrêté 0,05 avant chaque bout (tube plein seulement).
**Pièces : plein 1 + colliers (+1 cœur) ; creux `creux` × (1 + colliers)** (12 lames et 2 bagues : 36).

#### `boule_flottante` — capsule en lévitation
```python
b.boule_flottante(centre, rayon, couleur, *, aplatissement=0.8, hublot=VERRE, ceinture=None,
                  halo=NEON_CYAN, faisceau=True, socle=BLANC_LABO, sol=0.0, **kw)
b.boule_flottante((0, 9, 0), 4, "#FF8A3D", ceinture="#FFFFFF")
```
Coque ellipsoïdale, bulle de verre dessus, halo Neon dessous, faisceau lumineux jusqu'à un socle émetteur posé au
sol (`sol` = hauteur du sol dans le repère courant) : rien ne flotte « par erreur ». Chaque élément se retire avec
`None` / `False`. **Pièces : 6 par défaut (+16 avec la ceinture).**

### Contrôles et export

```python
from kit import bornes, bornes_part, controles, faces_confondues, exporter_roblox
lo, hi = bornes(b.parts)          # boîte englobante des pièces visibles
controles(b.parts)                # comptes (formes, Neon, verre, transparentes, studs, repères) + "problemes"
faces_confondues(b.parts)         # faces de deux pièces dans le même plan, du même côté, qui se recouvrent
exporter_roblox("build/parts.json", "export")   # lance roblox_export.luau, renvoie son résumé (lève si échec)
```
`controles(...)["problemes"]` doit rester vide : pièces > 2048 studs (taille maximale Roblox) ou < 0,05,
ellipsoïdes à studs, studs sur Neon ou verre, panneaux hors d'un bloc, boules non rondes, repères visibles ou
solides, **faces confondues** (scintillement : deux faces planes de pièces différentes dans le même plan, tournées
du même côté, qui se recouvrent). Les paires de même couleur, matériau et transparence, sans studs, ne sont pas
des problèmes (le scintillement ne se voit pas dans Roblox) mais font des taches noires dans les rendus Cycles :
elles sont listées à part, pour information, dans `controles(...)["faces_confondues_meme_teinte"]`. Une seule
recherche remplit les deux listes : 4 à 8 s pour 20 000 pièces.

## Interface de `carte.py`

`rendu.py` attend, et la conception doit garder :
- `build_carte(seed=7) -> Builder` : toute la carte (sol, assets posés, repères, puis `b.decouper(("Sol",), 64)`) ;
- `meta() -> dict` : au moins `{"nom": "CarteEgghead", "version": "…"}` (nom du modèle et des fichiers) ;
- `verifications(b) -> dict` : contrôles imprimés par `rendu.py` et `python carte.py` (y garder `"problemes"`) ;
- facultatif `VUES = {nom: ((x, y, z) caméra, (x, y, z) cible, champ vertical)}` : vues ajoutées ou remplacées.

La carte actuelle : pelouse 410 × 637, routes, couronne de tours, esplanade nord, repère `Spawn` en (0, 0, 205)
tourné vers le nord (-Z) ; budgets dans `plan.BUDGET_CARTE` (24 000 pièces, 1 500 Neon, 400 transparentes).

## Studs

- Sol et planchers : **`studs="top"` sur tous les dessus de sol**, comme dans les zones. Dans Roblox : studs
  intégrés (matériau `Plastic` + `SurfaceType.Studs` sur la face), aucune image, aucune instance en plus, teinte =
  `Part.Color`. Chaque pièce à studs porte aussi l'attribut `Studs` (liste des faces).
- Pour que les studs se raccordent d'une dalle à l'autre : tailles entières (de préférence paires) et coins sur des
  coordonnées entières.
- Texture HD facultative : `require(workspace.CarteEgghead.Outils.AppliquerStuds)("rbxassetid://ID")` (image
  `textures/stud.png` à téléverser) ; `{ mode = "materiau" }` crée le MaterialVariant `StudsCarte` ; `(nil)` revient
  aux studs intégrés. L'export peut aussi poser les textures directement : `--stud-id ID`.
- Studs aussi sur les dessus praticables (socles, plateaux, rebords, passerelles), jamais sur les ellipsoïdes ; sur
  un cylindre, seulement sur les disques des bouts.

## Aperçu, rendus, export

Python avec `bpy` 5.2 : `PY=/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/bvenv/bin/python`
(ou `python3.13 -m venv .venv && .venv/bin/pip install bpy==5.2.3 numpy pillow`). Lune 0.10 : variable `LUNE`, ou
`lune` dans le PATH, ou la copie de l'atelier (`kit.LUNE_SCRATCH`).

```bash
cd roblox/carte-egghead
$PY apercu.py assets.exemple:kiosque --variant 1 --res 1200x675 --samples 12
$PY apercu.py assets.test_primitives:vitrine --res 1200x675 --samples 12 --fov 42 \
    --cam="-28,36,-82;34,34,78" --target-pt="2,3,-2;-2,3,0"      # plusieurs caméras : images -a, -b…
$PY carte.py --stats                                  # build/parts.json + vérifications, sans Blender
$PY carte.py --export /tmp/essai                      # + export Roblox avec Lune, sans Blender (rapide)
$PY rendu.py --sans-export --res 1200x675 --echantillons 12 --dossier /tmp/controle     # vues de contrôle
$PY rendu.py --rapide --sans-export --vues joueur --ambiance crepuscule --suffixe=-crepuscule
$PY rendu.py --res 1600x900 --echantillons 16 --sans-export          # rendus finaux dans rendus/
$PY rendu.py --sans-rendu                             # export : .blend, .glb, puis .rbxm, .rbxmx, -demo.rbxl
```

- `apercu.py` : sans `--cam`, vue A en 3/4 avant et vue B en 3/4 arrière ; `--cam` / `--target-pt` acceptent
  plusieurs points séparés par `;` (écrire `--cam="-8,13,-44"` avec `=` quand la valeur commence par un signe
  moins) ; `--sol "#RRGGBB"`, `--fov`, `--dossier`, `--out`, `--no-ground`, `--params '{"rayon": 8}'`. Il imprime
  pièces, boîte, triangles et `controles`. Regarder les images avec l'outil Read.
- `rendu.py` : vues `aerienne` (3/4 plongeante cadrée sur l'emprise), `plan` (dessus orthographique cadré sur
  l'emprise, -Z en haut), `joueur` (12 studs derrière et 7 au-dessus du repère Spawn) et les
  `carte.VUES` (= `plan.VUES`, qui remplacent `aerienne` et `joueur`). Sans `--res`, les vues de
  `plan.RESOLUTIONS` prennent leur propre taille (captures 2000 × 1077 et 2000 × 1050, `plan_carte` 1200 × 1500) ;
  options `--vues`, `--rapide`, `--sans-rendu`, `--sans-export`, `--dossier`, `--export`, `--res`, `--echantillons`,
  `--ambiance jour|crepuscule`, `--suffixe`.
- Processeur partagé : aperçus en 1200 × 675 au plus, 12 à 16 échantillons, **un seul rendu Blender à la fois**.
- Rendu Blender fidèle à Roblox : pièces sans biseau, cylindres, boules et ellipsoïdes lissés (sphère UV avec un
  anneau de sommets sur l'équateur et aux quatre extrémités : étendue exacte = `Size`), pièces à studs rendues en
  `Plastic` comme dans l'export, **le Neon brille sans éclairer ses voisins** (comme dans Roblox ;
  `blender_scene.NEON_ECLAIRE = True` pour l'effet « ambiance »), ombres éclairées par un ciel en partie désaturé
  (proche d'`OutdoorAmbient`). Pas de Bloom dans les rendus.
- `rendu.py --sans-export` écrit son parts.json dans un dossier temporaire (rien n'est laissé dans le projet).

### Ce que l'export Roblox écrit et vérifie

`roblox_export.luau` écrit `NOM.rbxm` (binaire), `NOM.rbxmx` (XML) et `NOM-demo.rbxl` :
- modèle `CarteEgghead` : pivot à l'origine ; groupes en `Model` (sol découpé en `Sol/Bloc_i_j`) ; dossier
  `Reperes` ; dossier `Outils` avec le module `AppliquerStuds` ; attribut `Version` ;
- ellipsoïdes : `Part` Block + enfant `SpecialMesh` (`Ellipsoide`, Sphere, Scale 1, 1, 1, Offset 0 ; le type par
  défaut d'un SpecialMesh est Head, d'où le réglage explicite) ;
- pièces à studs : `Plastic` + `SurfaceType.Studs` sur les faces marquées (Neon et verre refusés) ;
- pièces sans collision : `CanQuery` false ; `CanTouch` false partout sauf les repères ;
- place de démo : `StreamingEnabled` (`ModelStreamingBehavior` Improved) ; `SpawnLocation` « Apparition » sur le
  repère `Spawn` (ou au centre) ; plein soleil tropical : `LightingStyle` Realistic, `ClockTime` 13,4,
  `GeographicLatitude` 6, `Brightness` 3,2, `ColorShift_Top` chaud, `Atmosphere` limpide et cyan,
  `ColorCorrectionEffect` (Saturation +0,22), `BloomEffect` (le Neon rayonne), `SunRaysEffect`.

Relecture automatique (l'export s'arrête sur la première erreur), dans le `.rbxm`, le `.rbxmx` et la place :
**chaque pièce relue est comparée à sa ligne de parts.json** (ordre de création conservé par `GetChildren`) :
classe et forme, nom, `Size`, `CFrame` (position à 0,001 près, matrice à 0,0001 près : une matrice transposée ou un
axe permuté est refusé), matériau, transparence, `CanCollide`, présence du `SpecialMesh` et du panneau, nombre de
pièces par groupe ; puis chaque `SpecialMesh` sous une `Part` Block, Sphere, Scale 1, Offset 0, sans studs ; pivot à
l'origine ; repères invisibles, sans collision, détectables ; repère `Spawn` cohérent ; `SpawnLocation` au bon
endroit ; `StreamingEnabled` ; éclairage ; module `AppliquerStuds` intact et compilable. Le résumé JSON donne
pièces, ellipsoïdes, Neon et verre (matériaux réellement écrits), faces stud, panneaux, repères, apparition, pivot et
emprise.

**Dans Studio** : ouvrir `export/CarteEgghead-demo.rbxl` puis Play ; ou, dans un jeu, Explorer › clic droit sur
`Workspace` › Insert from File… › `export/CarteEgghead.rbxm`, puis `workspace.CarteEgghead:PivotTo(CFrame.new(X, Y, Z))`.

## Pièces et performances

| Élément | Pièces |
|---|---|
| Primitive (bloc, coin, cylindre, boule, ellipsoïde) | 1 (l'ellipsoïde ajoute un `SpecialMesh`, sans coût notable) |
| `anneau` complet | `n` (24 par défaut) : 12-16 sous 6 studs de rayon, 24 jusqu'à 20, 32-48 au-delà (segments de 4-5 studs au plus) |
| `disque` | 1 (plein) ou `n` (percé) |
| `cone_etage` | `etages` (+1 pointe) : 6-10 suffisent |
| `dome` | 1 (+1 tambour, +4 gradins) |
| `oeuf` | 2 |
| `tube` | plein : 1 + colliers (+1 cœur) ; creux : `creux` × (1 + colliers) |
| `boule_flottante` | 6 (+16 ceinture) |
| Sol 200 × 200 en dalles de 50 | 16 |

Repères pour toute la carte : **≤ 24 000 pièces** (cible 20 000-22 000 ; la zone Black Clover, la plus riche, en
compte 13 275), dont **≤ 1 500 Neon** et **≤ 400 pièces transparentes** (verre, faisceaux : coûteuses en tri et en surimpression ;
éviter d'empiler plusieurs verres l'un derrière l'autre). Conseils :
- un grand aplat = un seul bloc ; des dalles de sol de 50 à 64 studs, découpées en blocs de 64 ;
- `collide=False` pour tout décor hors de portée ou très fin (anneaux Neon, halos, faisceaux, antennes, colliers),
  `shadow=False` pour les éléments très fins ou lumineux : moins de calcul physique et d'ombres ;
- les grands ellipsoïdes praticables : `collision="gradins"` (dôme) ou des blocs invisibles ajustés, sinon
  `collide=False` ;
- les assemblages arrondis coûtent vite : un anneau de 24 sur chaque bâtiment, c'est 24 pièces de plus par
  bâtiment ; préférer `n` adapté au rayon, et `disque` plein quand le trou ne se voit pas ;
- garder des tailles entières ou au demi-stud, 0,1 stud au minimum ; une pièce ne dépasse pas 2048 studs.

## Pièges connus

- **Faces confondues** (scintillement dans Roblox, taches noires dans Cycles) : un détail posé sur une face
  dépasse d'au moins 0,05 à 0,1 stud ; deux blocs qui se recouvrent ne partagent pas une face au même endroit.
  `anneau`, `disque` percé et `tube` le gèrent seuls ; `controles()` les détecte (`faces_confondues`).
- **Verre qui se recouvre** : là où deux pièces de verre se superposent (arêtes des lames d'un tube creux), le
  verre paraît un peu plus foncé (fines lignes le long du tube) : c'est le prix d'un couloir en lames.
- **Moitié basse des ellipsoïdes** : toujours cachée dans un volume plein (dômes, capsules, œufs posés) ; un dôme
  de verre sur une dalle mince montre sa moitié basse sous la dalle.
- **Raccord dôme / cylindre** : garder le `rebord` par défaut (un dôme de même rayon que sa tour fait une couture
  dentelée).
- **Ombrage lisse** : corrigé ici (`use_smooth`) ; les zones précédentes (`roblox/zone-*`) rendent encore leurs
  cylindres et boules à facettes dans Blender (le jeu, lui, n'est pas concerné).
- **Verre** : rendu par transparence simple dans Blender comme dans Roblox ; sur un ellipsoïde, Roblox peut
  l'afficher comme un plastique transparent un peu plus terne que sur un bloc.
- **Vue `joueur`** : celle de `plan.VUES` (caméra Roblox par défaut derrière l'apparition) remplace la vue calculée.

## Dans Studio : pose de la carte (finition)

- **Baseplate** : le dessus du sol de la carte est à y 0, exactement comme le dessus de la Baseplate par défaut
  (y -16 → 0) : tout scintillerait. Dans une place créée depuis le modèle Baseplate, **supprimer la Baseplate**, ou
  poser la carte plus haut : `workspace.CarteEgghead:PivotTo(CFrame.new(0, 2, 0))` (les dalles, de y -2 à 0,
  reposent alors sur la Baseplate) et monter d'autant le `SpawnLocation` du jeu.
- **Streaming** : le modèle `Ciel` est en `ModelStreamingMode = Persistent` (l'œuf, à 1 100-1 200 studs du sud de la
  carte, reste visible) ; la place de démo règle `StreamingTargetRadius` à 1 200. Le dossier `Reperes` est un
  Folder ordinaire : avec StreamingEnabled, un LocalScript ne reçoit que les repères proches ; lire les repères
  depuis un script serveur (ou `WaitForChild`).
- **Nom du modèle** : le Model racine s'appelle `CarteEgghead` (nom de travail, comme les fichiers). Avant de publier
  le jeu, le renommer en un nom neutre (par exemple `IleDuFutur`) : c'est le seul mot de la licence dans le .rbxm.
- **Fichier .blend** : `export/CarteEgghead.blend` (≈ 66 Mo) n'est pas suivi par git (`.gitignore`) ; il se
  régénère avec `python rendu.py --sans-rendu` (écrit aussi .glb, .rbxm, .rbxmx et la place de démo dans export/).
- **Barrière des façades** : `Tours/Limites` (8 blocs invisibles à collision, y 0,4 → 40) ferme la couronne au niveau
  de la rue ; la caméra Roblox (Popper) ignore les pièces transparentes.

