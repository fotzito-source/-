# Conventions des assets (zone My Hero Academia, style stud)

Chaque asset est une fonction Python qui ajoute des **Parts Roblox** à un `kit.Builder`. La même liste de pièces
sert au rendu Blender et au modèle Roblox : on ne construit qu'avec les formes natives de Roblox (bloc, coin,
cylindre, boule). Lire aussi `CONCEPTION.md`, qui donne l'intention, la séquence et les budgets.

## Repère et plan de la zone

- Repère **Roblox** : X à droite, **Y vers le haut**, Z vers l'arrière ; 1 unité = 1 stud. Un personnage Roblox
  mesure environ 5 studs de haut et 2 de large.
- Origine de l'asset : centre de son emprise au sol, **y = 0 = niveau du sol**.
- **L'avant de l'asset regarde -Z local.** La mise en page tourne l'asset pour que son avant regarde le couloir
  (`face_couloir(x)` : yaw -90 à gauche, +90 à droite).
  Exceptions, posées sans rotation (yaw = 0), dont la face principale regarde **+Z** (les joueurs qui arrivent) :
  `viaduc_train`, `portail_securite`, `stade` et `tours_jumelles`. Les deux faces de ces monuments se voient
  (aller et retour).
- **Couloir de course : `x ∈ [-45, 45]` (90 studs, la route du milieu est très large à la demande)**, du sol
  d'approche (z = +24) à la sortie (z = -574). Trottoirs jusqu'à **`|x| = 55`** : façades des boutiques, haies,
  piles et pylônes commencent en `|x| = 55` (le portail dès 50).
- Séquence : approche (+24 → 0), viaduc (z = -18, tablier de z -12 à -24), rue de la ville (-26 → -122, carrefour
  et rues latérales en z = -66 ± 10), portail de sécurité et mur avant (z = -132, de -124 à -140), avenue du
  campus (-140 → -296), terrains d'entraînement (-296 → -400, dôme centré en x = 124, z = -348), stade
  (-400 → -528, place des œufs de rayon 34 centrée en z = -464), parvis (-528 → -536), tours jumelles
  (-536 → -574, sortie). Mur d'enceinte latéral en `|x| = 185`, ville lointaine en `|x| ≈ 218`, sol jusqu'à
  `|x| = 239`.
- Le joueur arrive par +Z, court vers -Z, puis revient : **les deux sens de lecture comptent**.

## Règles du couloir (vérifiées par `python zone.py --stats`)

- **Au sol** : rien de solide (`collide=True`) dans `|x| < 45` entre y = 0,05 et y = 12, sauf le sol lui-même.
- **Au-dessus** : **rien du tout** (solide ou non) au-dessus de `|x| < 46` sous **y = 30**. Sinon la caméra
  Roblox saute quand le joueur passe dessous. Ce qui enjambe le couloir (tablier du viaduc, linteau du portail,
  portiques du stade, passerelle des tours) passe **au-dessus de 36**.
- Les assets posés sur les trottoirs gardent toute leur emprise en `|x| ≥ 46` (lampadaires en `|x| = 50,5`,
  feux en 51, bancs en 52,5).
- **Les assets ne dessinent jamais de sol dans `|x| < 52`** : `zone.py` peint la chaussée, le seuil du portail,
  l'arène du stade et la mosaïque. Un sol propre à un asset (intérieur du dôme, socle d'un bâtiment) part de
  y = 0 et monte au-dessus (pas de face supérieure à y = 0, qui scintillerait avec le sol de la zone).

## API du kit (`kit.py`)

```python
from palette import c, vary, tirer   # c("vitre_violette") → (r, g, b) ; vary("blanc", b.rng) ; tirer(["brique", "brique_fonce"], b.rng)
from kit import shade, mix           # shade(couleur, 0.85) assombrit ; mix(a, b, t)

def mon_asset(b, variant=0, **params):
    rng = b.rng                                   # numpy Generator (aléatoire reproductible)
    b.box((x0, y0, z0), (x1, y1, z1), c("blanc"))                   # bloc par deux coins
    b.boxc((cx, cy, cz), (sx, sy, sz), couleur, yaw=30)              # bloc par centre/taille, tourné autour de Y
    b.wedge((x0, y0, z0), (x1, y1, z1), couleur, down="-z")         # coin qui remplit la boîte ; la pente descend vers `down`
    b.wedge_under(a, b_, couleur, down="-z")                         # coin retourné (sous-face d'avant-toit, console)
    b.cyl((cx, cy, cz), rayon, longueur, couleur, axis="y")          # cylindre (axis x, y ou z)
    b.ball((cx, cy, cz), rayon, couleur)
    b.part("block", taille, centre, matrice_rotation, couleur)       # pièce quelconque (rotation 3 × 3, colonnes = axes locaux)
    with b.at((x, y, z), yaw=90, group="Tribune"):                  # sous-repère (translation + rotation Y) et sous-groupe
        ...
    with b.group("Toit"):
        ...
    return {"emprise": (largeur_x, profondeur_z), "hauteur": h}
```

Options de toutes les primitives : `studs=` (`"top"`, `"all"`, `"sides"`, `"top+sides"`, `"none"` ou un tuple de faces
`("Top", "Front", …)`), `material=` (`SmoothPlastic` par défaut, `Plastic`, `Wood`, `WoodPlanks`, `Slate`, `Concrete`,
`Brick`, `Cobblestone`, `Rock`, `Sand`, `Grass`, `Fabric`, `Metal`, `Neon`, `Glass`), `transparency=`, `reflectance=`,
`collide=False` (petits détails), `shadow=False`, `name=`.
Chaque primitive renvoie la `Part` : `p.label = {"face": "Front", "text": "CAFÉ", "color": (r, g, b), "bg": (r, g, b) ou None,
"font": "sans", "vertical": False}` ajoute un panneau texte (SurfaceGui dans Roblox). Police `"sans"` pour ce thème.
Les helpers `_label`, `_segment` (cylindre entre deux points) et `_chainette` de `assets/mobilier.py` sont réutilisables.

Formes Roblox à connaître :
- `wedge` : face pleine au fond et dessous, pente vers `down` ; une pente avec `studs="top"` reçoit les studs.
- un cylindre Roblox est lisse ; ses studs ne vont que sur les disques des extrémités.
- **Verre** : le rendu Blender ignore `reflectance`. Le verre se lit par la couleur : nappes `vitre_violette` en 2-3
  tons, bandes de reflet `vitre_reflet` ou `vitre_violette_claire` en diagonale ou par étage, montants blancs en
  saillie. Matériau `Glass` + `transparency` 0,3-0,5 seulement pour ce qui doit laisser voir derrière (dôme,
  verrières, garde-corps) ; les façades de tours restent opaques (SmoothPlastic ou Glass sans transparence).
- **Néons** : matériau `Neon`, bandes fines (0,2-0,4), toujours posées en saillie sur un support.

## Style « stud » attendu

- Silhouettes **simples et lisibles de loin**, détails à trois échelles : masse (tour, tribune, dôme), éléments
  (balcons, auvents, montants, verrières), petits accents (néons, enseignes, caméras, climatiseurs).
  Pas de bouillie de petits blocs.
- **Couleurs franches** de `palette.py`, utiliser `vary()` ou `tirer()` pour casser les grands aplats : béton blanc
  en 2-3 blancs, brique en 3 rouges, verre en 2-3 bleus-violets. Pas de gris sale, **pas de vert émeraude
  dominant**. Accent principal : `violet` #6157F8.
- **Studs** (`studs="top"`) sur les dessus horizontaux visibles (toits plats, dalles, terrasses, sièges des tribunes,
  sommets des haies) et sur les pentes de toit. **Pas sur les murs** de bâtiment ni sur les façades vitrées. Les faces
  studdées ont de préférence des dimensions entières.
- Ambiance : académie de héros futuriste et ville japonaise moderne, propre, héroïque, lumineuse. Verre bleu-violet
  et cadres blancs, béton blanc, acier bleu nuit, brique rouge des dortoirs, verts touffus, trottoirs roses, néons
  cyan et blancs, touches orangées du couchant.

## Propriété intellectuelle (obligatoire)

Roblox retire les contenus non licenciés. **Uniquement des éléments génériques** :
- Aucun nom de la licence, de l'école, de la ville ou des personnages, nulle part (textes, noms de pièces, groupes).
  **Jamais de « UA » ni de « U.A. »**, ni en texte ni en forme de lettres.
- Aucun personnage, aucune statue de héros, aucun costume de héros, aucune silhouette humaine.
- Aucun logo, emblème ni blason ; motifs abstraits seulement (bandes, chevrons, étincelle géométrique).
- Robots d'entraînement de **dessin original** (cubiques, un œil rond, bandes de danger). Pas de chiffres, pas de
  « 1P / 2P / 3P », pas de robot géant d'examen.
- Textes permis : ACADÉMIE, CAMPUS, ENTRAÎNEMENT, STADE, GYMNASE, DORTOIRS, CAFÉ, FLEURS, LIVRES, MARCHÉ, RAMEN,
  BOULANGERIE, SPORT, PHARMACIE, ou aucun texte. Pas de marque réelle (ni logo, ni code couleur d'une enseigne
  connue).

## Règles techniques Roblox

- **Pas de faces coplanaires qui se chevauchent** (scintillement / z-fighting) : un détail posé sur un mur dépasse
  d'au moins 0,1 stud ; deux blocs qui se recouvrent ne partagent pas une face au même endroit avec des couleurs
  différentes.
- Rien ne flotte : tout repose sur quelque chose (sauf câbles, fanions et éléments suspendus à un support).
- Taille minimale 0,1 stud. Préférer des tailles entières ou au demi-stud.
- **Budget de pièces** : respecter celui donné pour l'asset (`BUDGETS` dans `zone.py`, contrôlé par `--stats`).
  Un grand aplat = un seul bloc. Plafond de la zone : 13 500 pièces.
- `collide=False` pour les petits détails décoratifs hors de portée (néons, montants fins, enseignes, câbles,
  feuillage fin, verrières hautes).

## Aperçu

```bash
cd roblox/zone-my-hero-academia
PY=/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/bvenv/bin/python   # Python avec bpy 5.2
$PY apercu.py assets.mobilier:planche --params '{"partie": 2}'      # → apercus/mobilier-planche-v0-{a,b}.png
$PY apercu.py assets.campus:tours_jumelles --cam "0,40,120" --target-pt "0,60,-20" --res 1200x675 --samples 12
$PY zone.py --stats                                                   # couloir, hauteur libre, budgets
$PY rendu.py --rapide --sans-export --vues entree,campus              # vues de contrôle de la zone
```

La vue A regarde l'avant (côté -Z) en 3/4, la vue B l'arrière, plus haut. Regarder les images avec l'outil Read.
Le processeur est partagé : aperçus en 1200 × 675 au plus, 12 à 16 échantillons.
