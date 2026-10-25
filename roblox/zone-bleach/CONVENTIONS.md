# Conventions des assets (zone Bleach, style stud)

Chaque asset est une fonction Python qui ajoute des **Parts Roblox** à un `kit.Builder`. La même liste de pièces
sert au rendu Blender et au modèle Roblox : on ne construit qu'avec les formes natives de Roblox (bloc, coin,
cylindre, boule). Lire aussi `CONCEPTION.md`, qui donne l'intention, la séquence et les budgets.

## Repère et plan de la zone

- Repère **Roblox** : X à droite, **Y vers le haut**, Z vers l'arrière ; 1 unité = 1 stud. Un personnage Roblox
  mesure environ 5 studs de haut et 2 de large.
- Origine de l'asset : centre de son emprise au sol, **y = 0 = niveau du sol**.
- **L'avant de l'asset regarde -Z local.** La mise en page tourne l'asset pour que son avant regarde le couloir.
  Exceptions : `grande_porte`, `porte_interieure`, `passerelle_rouge` et `colline_tour` sont posées sans rotation
  (yaw = 0). Leur face principale regarde +Z, vers les joueurs qui arrivent.
- **Couloir de course (élargi) : `x ∈ [-45, 45]`**, du sol de l'esplanade (z = +64) à la sortie (z = -522).
  Trottoirs jusqu'à `|x| = 55` (façades du faubourg, murs d'allée de la cité dont la face est en `|x| = 55`).
  Ce qui enjambe le couloir laisse au moins 92 studs entre ses appuis (appuis en `|x| ≥ 46`) : grande porte
  (ouverture 100), porte intérieure (92), passerelle (portée 130), tunnel de sortie (96).
- Séquence : esplanade (+64 → +8), grande porte (mur centré sur z = 0, épaisseur 16), faubourg (-8 → -171),
  porte intérieure (z = -176, épaisseur 10), cité blanche (-181 → -388, passerelle en z = -286), cour des œufs
  (-388 → -476, place de rayon 34 centrée en z = -430), colline et tunnel (-476 → -522). Remparts latéraux en
  `|x| = 150`, ville lointaine jusqu'à `|x| = 210`.
- Le joueur arrive par +Z, court vers -Z, puis revient : **les deux sens de lecture comptent**.

## Règles du couloir (vérifiées par `python zone.py --stats`)

- **Au sol** : rien de solide (`collide=True`) dans `|x| < 45` entre y = 0,05 et y = 12, sauf le sol lui-même.
- **Au-dessus** : **rien du tout** (solide ou non) au-dessus de `|x| < 46` sous **y = 30**. Sinon la caméra
  Roblox saute quand le joueur passe dessous. Ce qui enjambe le couloir (linteaux, corps de garde, passerelle,
  voûte du tunnel, lampions) passe **au-dessus de 34** (solives de la porte intérieure à 35,1, de la grande
  porte à 55, tablier de la passerelle à 36,6, voûte du tunnel à 38, capuchons des lampions à 34).
- Les assets posés sur les trottoirs gardent toute leur emprise en `|x| ≥ 46`.
- Les poses ne s'interpénètrent pas : `python zone.py --chevauchements` (boîtes orientées des pièces, feuillages
  entre eux et jointures de murs exceptés).

## API du kit (`kit.py`)

```python
from palette import c, vary, blanc_pixel   # c("ocre") → (r, g, b) ; vary("blanc", b.rng) → petite variation
from kit import shade, mix                 # shade(couleur, 0.85) assombrit ; mix(a, b, t)

def mon_asset(b, variant=0, **params):
    rng = b.rng                                   # numpy Generator (aléatoire reproductible)
    b.box((x0, y0, z0), (x1, y1, z1), c("blanc"))                   # bloc par deux coins
    b.boxc((cx, cy, cz), (sx, sy, sz), couleur, yaw=30)              # bloc par centre/taille, tourné autour de Y
    b.wedge((x0, y0, z0), (x1, y1, z1), couleur, down="-z")         # coin qui remplit la boîte ; la pente descend vers `down`
    b.wedge_under(a, b_, couleur, down="-z")                         # coin retourné (console, sous-face d'avant-toit)
    b.cyl((cx, cy, cz), rayon, longueur, couleur, axis="y")          # cylindre (axis x, y ou z)
    b.ball((cx, cy, cz), rayon, couleur)
    b.part("block", taille, centre, matrice_rotation_3x3, couleur)   # bloc tourné librement (pans de toit inclinés)
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
Chaque primitive renvoie la `Part` : `p.label = {"face": "Front", "text": "門", "color": (r, g, b), "bg": (r, g, b)
ou None, "font": "brush" | "sans", "vertical": True/False}` ajoute un panneau texte (SurfaceGui dans Roblox).
Les six faces sont possibles ; pour un texte lisible des deux côtés, deux pièces dos à dos avec chacune son label.

Pour un grand signe en relief : `textures.glyph_mask(texte, cases, font="brush"|"sans", bold=0.5)` donne un
masque booléen, et `textures.mask_rects(masque)` le découpe en rectangles, un bloc par rectangle.

Formes Roblox à connaître :
- `wedge` : face pleine au fond et dessous, pente vers `down`. Une pente avec `studs="top"` reçoit les studs.
  Toit à deux pans = deux coins dos à dos plus un faîtage. Croupe : coins vers ±X aux extrémités, ou toit en
  gradins de blocs.
- Un cylindre Roblox est lisse ; ses studs ne vont que sur les faces planes.
- Pas de `CornerWedge` dans le kit : une pyramide se fait en gradins de blocs ou en deux coins plus un faîtage court.

## Style « stud » attendu

- Silhouettes **simples et lisibles de loin**, détails à trois échelles : la masse (rempart, tour, maison), les
  éléments (toit, balcon, corps de garde, base de pierre) et les petits accents (meurtrières, lanternes,
  enseignes, ferrures). Pas de bouillie de petits blocs.
- **Le blanc doit vivre** : jamais un mur blanc d'un seul aplat sur plus de ~16 studs. On découpe en panneaux de
  `blanc_pixel(rng)` ou `vary("blanc", rng, 0.04)`, et on ajoute des bandeaux, des poteaux d'angle, des bases
  de pierre, des chaperons ocre, des ouvertures sombres et des ombres portées par les débords. Les toits ocre
  débordent bien (au moins 1,5 stud), avec faîtage et rives plus claires ou plus foncées.
- **Couleurs franches** de `palette.py`. Ocre-orangé pour les toits et chaperons de la cité, tuiles grises au
  faubourg, laque rouge et bleu profond en accents rares. Pas de gris sale, pas de vert émeraude dominant.
- **Studs** (`studs="top"`) sur les dessus horizontaux visibles, les pentes de toit, les chaperons, les
  plateformes et les dessus de bases de pierre. Pas sur les murs d'habitation ; les remparts peuvent en avoir
  sur leur chemin de ronde. Les faces studdées ont de préférence des dimensions entières.
- Faubourg : bois sombre, poteaux et poutres apparents, torchis beige, treillis, shoji, noren, sudare,
  balcons à garde-corps, tuiles grises. Cité : enduit blanc, base de pierre talutée, tuiles ocre, poteaux et
  linteaux de bois sombre ou de laque rouge, portails à petit toit.

## Propriété intellectuelle (obligatoire)

Rien de la licence. Pas de nom (ni la licence, ni ses lieux, ni ses personnages), pas de personnage, pas de
numéro de division ni de chiffre décoratif, pas d'insigne ni de fleur-emblème de division, pas de losange
d'insigne, pas de 護廷, 十三隊, 霊, 魂, 死神, 隊 ou 卍. Pas de sabre précis, de masque, de hallebarde géante,
d'échafaud d'exécution, de papillon noir ni de portail à shoji flottant. Le monolithe est un rocher sacré
générique (corde *shimenawa*) ; la grande tour, une tour blanche générique.
**Textes permis** : 門, 静, 白, 茶, 宿, 米, 湯, 薬, 団子, 蕎麦, 甘味, 呉服, 豆腐, 本, 花, 桜 (pas de 酒).

## Règles techniques Roblox

- **Pas de faces coplanaires qui se chevauchent** (scintillement, z-fighting). Un détail posé sur un mur dépasse
  d'au moins 0,1 stud. Deux blocs qui se recouvrent ne partagent pas une face au même endroit avec des couleurs
  différentes.
- Rien ne flotte : tout repose sur quelque chose, sauf les câbles et lampions suspendus, accrochés à un support.
- Taille minimale 0,1 stud. Préférer des tailles entières ou au demi-stud.
- **Budget de pièces** : respecter celui de l'asset (`BUDGETS` dans `zone.py`, contrôlé par `--stats`). Un grand
  aplat = un seul bloc. Mobilier : au plus 40 pièces par objet.
- `collide=False` pour les petits détails décoratifs hors de portée (lanternes, enseignes, feuillage fin, tuiles
  de rive, ferrures). Les murs, socles, corps de bâtiments et troncs restent solides.
- Tout asset garde son emprise annoncée. `place()` pose un bloc rose translucide de même emprise tant que la
  fonction n'existe pas : la mise en page est déjà vérifiable.

## Aperçu

```bash
cd roblox/zone-bleach
PY=/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/bvenv/bin/python   # Python avec bpy 5.2
$PY apercu.py assets.mobilier:lanterne_poteau --variant 1          # → apercus/mobilier-lanterne_poteau-v1-{a,b}.png
$PY apercu.py assets.remparts:tour_blanche --params '{"hauteur": 44}' --cam "40,30,-50" --target-pt "0,22,0" --res 1200x675 --samples 12
$PY zone.py --stats                                                 # couloir, hauteur libre, budgets, pièces par groupe
$PY rendu.py --rapide --sans-export --vues entree,cite              # contrôle dans la zone
```

La vue A regarde l'avant (côté -Z) en 3/4, la vue B l'arrière, plus haut. Regarder les images avec l'outil Read.
Le processeur est partagé : aperçus en 1200x675 au plus, 12 à 16 échantillons.
