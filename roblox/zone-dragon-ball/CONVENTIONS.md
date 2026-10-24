# Conventions des assets (zone Dragon Ball, style stud)

Chaque asset est une fonction Python qui ajoute des **Parts Roblox** à un `kit.Builder`.
La même liste de pièces sert au rendu Blender et au modèle Roblox : on ne construit donc qu'avec
les formes natives de Roblox (bloc, coin, cylindre, boule).

## Repère et plan de la zone

- Repère **Roblox** : X à droite, **Y vers le haut**, Z vers l'arrière ; 1 unité = 1 stud.
  Un personnage Roblox mesure environ 5 studs de haut et 2 de large.
- Origine de l'asset : centre de son emprise au sol, **y = 0 = niveau du sol** (sauf mention contraire dans la spec).
- **L'avant de l'asset regarde -Z local.** La mise en page tourne l'asset (yaw ±90) pour que son avant regarde le couloir :
  `largeur` = dimension le long du couloir (X local), `profondeur` = dimension vers l'extérieur (Z local).
- Couloir de course : **`x ∈ [-32, 32]`** (64 studs), de `z = 0` (porte de temple) à `z = -470` (sortie sous l'arche,
  vers la zone suivante). Trottoirs jusqu'à `|x| = 42`, premières façades à `|x| = 44`, falaises de `|x| = 124` à 200.
  Le joueur arrive par +Z et court vers -Z, puis revient : **les deux sens de lecture comptent**.
- Séquence : approche (+40 → 0), porte de temple (z = 0), campagne terrestre et village de dômes (0 → -146),
  terres de combat et mesas (-146 → -290, pont de roche en z = -222), planète extraterrestre (-290 → -358),
  arène des œufs (carré 68 × 68 centré en z = -392, dessus à y = 1), arche finale (façade z = -436, sortie z = -470).

## API du kit (`kit.py`)

```python
from palette import c, vary          # c("tuile_orange") → (r, g, b) ; vary("blanc_dome", b.rng) → petite variation
from kit import shade, mix           # shade(couleur, 0.85) assombrit ; mix(a, b, t)

def mon_asset(b, variant=0, **params):
    rng = b.rng                                   # numpy Generator (aléatoire reproductible)
    b.box((x0, y0, z0), (x1, y1, z1), c("enduit"))                  # bloc par deux coins
    b.boxc((cx, cy, cz), (sx, sy, sz), couleur, yaw=30)              # bloc par centre/taille, tourné autour de Y
    b.wedge((x0, y0, z0), (x1, y1, z1), couleur, down="-z")         # coin qui remplit la boîte ; la pente descend vers `down`
    b.wedge_under(a, b_, couleur, down="-z")                         # coin retourné (console, sous-face d'avant-toit, fanion)
    b.cyl((cx, cy, cz), rayon, longueur, couleur, axis="y")          # cylindre (axis x, y ou z)
    b.ball((cx, cy, cz), rayon, couleur)                             # boule (dôme : boule à moitié sous le sol)
    b.part("cyl", (long, d, d), centre, R, couleur)                  # cylindre d'axe quelconque (R : colonnes = axes locaux)
    with b.at((x, y, z), yaw=90, group="Lampes"):                    # sous-repère (translation + rotation Y) et sous-groupe
        ...
    with b.group("Toit"):
        ...
    return {"emprise": (largeur_x, profondeur_z), "hauteur": h}
```

Options de toutes les primitives : `studs=` (`"top"`, `"all"`, `"sides"`, `"top+sides"`, `"none"` ou un tuple de faces
`("Top", "Front", …)`), `material=` (`SmoothPlastic` par défaut, `Wood`, `WoodPlanks`, `Slate`, `Concrete`, `Brick`,
`Cobblestone`, `Rock`, `Sand`, `Grass`, `Fabric`, `Metal`, `Neon`, `Glass`), `transparency=`, `reflectance=`,
`collide=False` (petits détails), `shadow=False`, `name=`.
Chaque primitive renvoie la `Part` : `p.label = {"face": "Front", "text": "武", "color": (r, g, b), "bg": (r, g, b) ou None,
"font": "brush" | "sans", "vertical": True/False}` ajoute un panneau texte (SurfaceGui dans Roblox). Une seule face par
pièce : pour un texte lisible des deux côtés, deux plaques dos à dos (`"Front"` et `"Back"`).

Pour les grands signes en relief : `textures.glyph_mask(texte, cases, font="brush"|"sans", bold=0.5)` donne un masque
booléen et `textures.mask_rects(masque)` le découpe en rectangles → un bloc par rectangle.

Formes Roblox à connaître :
- `wedge` : face pleine au fond et dessous, pente vers `down` ; une pente avec `studs="top"` reçoit les studs.
- un cylindre Roblox est lisse ; ses studs ne vont que sur les disques. Une boule est lisse.
- **Dôme** : une boule dont le centre est à y = 0 (la moitié basse est cachée sous le sol) ; une bande colorée = un
  cylindre vertical de rayon `sqrt(r² - y²) + 0,15` à la hauteur y.

## Style « stud » attendu

- Silhouettes **simples et lisibles de loin**, détails à trois échelles : masse (dôme, temple, mesa), éléments (toit, bande,
  hublots, chapeau d'herbe), petits accents (antennes, lampes, fanions). Pas de bouillie de petits blocs.
- **Couleurs franches** de `palette.py` (lumineuses, saturées, joyeuses). Utiliser `vary()` pour casser les grands aplats
  (falaises et mesas en strates de 2-4 teintes proches). Pas de gris sale, pas de vert émeraude dominant.
- **Studs** (`studs="top"`) sur les dessus horizontaux visibles : sols, toits, plateformes, sommets de mesas et de falaises,
  pentes de toit. Pas sur les murs d'habitation ni sur les dômes. Faces studdées de préférence en dimensions entières.
- Trois familles :
  1. **Campagne terrestre** : dômes blancs à bandes colorées, hublots et portes ronds, palmiers, herbe vert vif, falaises
     orange en strates à chapeau d'herbe, cascades ; temple d'arts martiaux à tuiles vernissées orange, piliers rouges, murs
     blancs, lions de pierre.
  2. **Terres de combat** : terre kaki et ocre, mesas violettes à sommet herbu (strate rose), cratères, rochers.
  3. **Planète extraterrestre** : herbe sarcelle, eau turquoise, îlots aux bords de sable ocre, arbres très fins à couronne
     ronde, dômes blancs aux hublots verts, vaisseau blanc et lavande, nuages dorés.

## Propriété intellectuelle (obligatoire)

Roblox supprime les contenus sous licence non autorisés : **rien de la licence**, seulement des éléments génériques.
- Aucun nom (ni de la série, ni des personnages, ni des lieux) dans les pièces, groupes, textes ou titres.
- Aucun personnage ni silhouette de personnage ; statues = lions de pierre uniquement.
- Pas de logo ni de nom d'entreprise sur les dômes, pas de « capsules » posées au sol, pas de 亀 ni de symbole d'école,
  pas de maison rose sur une île avec un palmier, **pas de sphère orange** (lampes, fruits, pommeaux compris),
  **pas d'étoile rouge**, pas de dragon (龍 interdit), pas de petit nuage jaune isolé au ras du sol, pas de plateforme blanche
  suspendue à palmiers, pas de tour blanche très fine, pas de capsule spatiale sphérique dans un cratère (cratères vides),
  pas le vaisseau exact du méchant (le nôtre : lentille blanche et lavande à coupole, quatre pattes, hublots à l'avant).
- **Textes autorisés** (et seulement ceux-là) : 武, 道場, 修行, 武道, 気, 天.

## Règles techniques Roblox

- **Pas de faces coplanaires qui se chevauchent** (scintillement / z-fighting) : un détail posé sur un mur dépasse d'au moins
  0,1 stud ; deux blocs qui se recouvrent ne partagent pas une face au même endroit avec des couleurs différentes.
- Rien ne flotte : tout repose sur quelque chose (sauf fanions, lanternes et câbles suspendus à un support ; les nuages dorés
  reposent sur le sol ou sur les falaises).
- Taille minimale 0,1 stud. Préférer des tailles entières ou au demi-stud.
- Budget de pièces : respecter celui donné pour l'asset (Roblox mobile, ≤ 13 500 pièces pour toute la zone).
  Un grand aplat = un seul bloc.
- `collide=False` pour les petits détails décoratifs (fanions, lampes, feuillage fin, hublots, câbles, enseignes).
- **Couloir** : rien de collidable dans `|x| < 32` entre `y = 0,05` et `y = 12` (hors sol), et **rien du tout au-dessus du
  couloir (`|x| < 33`) sous `y = 30`** (la caméra Roblox sauterait). Ce qui enjambe le couloir (porte, pont de roche, arche,
  fanions) passe à **34 studs ou plus** au-dessus de `|x| < 33`. `zone.py --stats` vérifie les deux règles
  (`couloir_libre`, `trop_bas_au_dessus`).
- L'arène des œufs est un **sol** en relief (dessus à 1 stud, rampes de 5 studs dans le couloir) : elle appartient au groupe `Sol`.
- L'eau (canaux, lac) est une dalle turquoise translucide dont le dessus est à y = -0,4, posée par `zone.py`.

## Aperçu

```bash
cd roblox/zone-dragon-ball
PY=/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/bvenv/bin/python   # Python avec bpy 5.2
$PY apercu.py assets.batiments:maison_dome --variant 1                    # → apercus/batiments-maison_dome-v1-{a,b}.png
$PY apercu.py assets.arche:arche_finale --cam "120,60,140" --target-pt "0,40,-17" --res 1200x675 --samples 12
$PY zone.py --stats                                                        # plan complet, pièces par groupe, contrôles
$PY rendu.py --rapide --sans-export --vues entree,place                    # rendus de contrôle de la zone
```

La vue A regarde l'avant (côté -Z) en 3/4, la vue B l'arrière, plus haut. Regarder les images avec l'outil Read.
Le processeur est partagé : aperçus ≤ 1200 × 675 et 12 à 16 échantillons. Un rendu prend 20 à 60 s.
