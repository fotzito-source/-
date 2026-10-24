# Conventions des assets (zone Demon Slayer, style stud)

Chaque asset est une fonction Python qui ajoute des **Parts Roblox** à un `kit.Builder`.
La même liste de pièces sert au rendu Blender et au modèle Roblox : on ne construit donc qu'avec
les formes natives de Roblox (bloc, coin, cylindre, boule).

## Repère

- Repère **Roblox** : X à droite, **Y vers le haut**, Z vers l'arrière ; 1 unité = 1 stud.
  Un personnage Roblox mesure environ 5 studs de haut et 2 de large.
- Origine de l'asset : centre de son emprise au sol, **y = 0 = niveau du sol**.
- **L'avant de l'asset regarde -Z local.** La mise en page tourne l'asset pour que son avant regarde le couloir.
- Couloir de course de la zone : `x ∈ [-30, 30]`, de `z = 0` (grand torii d'entrée) à `z = -376` (montagne aux glycines,
  traversée par une gorge et un tunnel de torii jusqu'en `z = -444`). Trottoirs jusqu'aux façades en `|x| = 40`.
  Séquence : village de l'ère Taishō (z 0 → -150), allée des glycines (-150 → -292), place des œufs et sanctuaire
  (centre z = -334), montagne (-376 → -444).
  Le joueur arrive par +Z et court vers -Z, puis revient : **les deux sens de lecture comptent**.

## API du kit (`kit.py`)

```python
from palette import c, vary          # c("vermillon") → (r, g, b) ; vary("enduit", b.rng) → petite variation
from kit import shade, mix           # shade(couleur, 0.85) assombrit ; mix(a, b, t)

def mon_asset(b, variant=0, **params):
    rng = b.rng                                   # numpy Generator (aléatoire reproductible)
    b.box((x0, y0, z0), (x1, y1, z1), c("enduit"))                  # bloc par deux coins
    b.boxc((cx, cy, cz), (sx, sy, sz), couleur, yaw=30)              # bloc par centre/taille, tourné autour de Y
    b.wedge((x0, y0, z0), (x1, y1, z1), couleur, down="-z")         # coin qui remplit la boîte ; la pente descend vers `down`
    b.wedge_under(a, b_, couleur, down="-z")                         # coin retourné (console, sous-face d'avant-toit)
    b.cyl((cx, cy, cz), rayon, longueur, couleur, axis="y")          # cylindre (axis x, y ou z)
    b.ball((cx, cy, cz), rayon, couleur)
    with b.at((x, y, z), yaw=90, group="Lampions"):                  # sous-repère (translation + rotation Y) et sous-groupe
        ...
    with b.group("Toit"):
        ...
    return {"emprise": (largeur_x, profondeur_z), "hauteur": h}
```

Options de toutes les primitives : `studs=` (`"top"`, `"all"`, `"sides"`, `"top+sides"`, `"none"` ou un tuple de faces
`("Top", "Front", …)`), `material=` (`SmoothPlastic` par défaut, `Wood`, `WoodPlanks`, `Slate`, `Concrete`, `Brick`,
`Cobblestone`, `Rock`, `Sand`, `Grass`, `Fabric`, `Metal`, `Neon`, `Glass`), `transparency=`, `reflectance=`,
`collide=False` (petits détails), `shadow=False`, `name=`.
Chaque primitive renvoie la `Part` : `p.label = {"face": "Front", "text": "茶", "color": (r, g, b), "bg": (r, g, b) ou None,
"font": "brush" | "sans", "vertical": True/False}` ajoute un panneau texte (SurfaceGui dans Roblox).

Pour les grands signes en relief (あ, ん, 忍, 火, spirale) : `textures.glyph_mask(texte, cases, font="brush"|"sans", bold=0.5)`
donne un masque booléen et `textures.mask_rects(masque)` le découpe en rectangles → un bloc par rectangle.

Formes Roblox à connaître :
- `wedge` : face pleine au fond et dessous, pente vers `down` ; une pente avec `studs="top"` reçoit les studs.
- un cylindre Roblox est lisse ; ses studs ne vont que sur les faces planes.

## Style « stud » attendu

- Silhouettes **simples et lisibles de loin**, détails à trois échelles : masse (bâtiment), éléments (toit, balcon, citerne),
  petits accents (lampions, enseignes, tuyaux). Pas de bouillie de petits blocs.
- **Couleurs franches** de `palette.py`. Utiliser `vary()` pour casser les grands aplats (murs en « pixels » de 2-4 teintes
  proches, comme les murs de la référence). Pas de gris sale, pas de vert émeraude dominant.
- **Studs** (`studs="top"`) sur les dessus horizontaux visibles et sur les pentes de toit ; pas sur les murs d'habitation
  (les murs d'enceinte et la falaise peuvent en avoir). Les dimensions des faces studdées sont de préférence des entiers.
- Ère Taishō / Japon traditionnel : bois sombre, enduit blanc, treillis de bois (koshi), shoji en papier, tuiles bleu nuit
  ou ardoise en toits à deux pans ou à croupe-pignon (irimoya) bien débordants, lanternes de papier chaudes, noren,
  sanctuaires vermillon, cordes shimenawa avec papiers shide en zigzag, lanternes de pierre, glycines mauves en cascades.
- **Propriété intellectuelle (obligatoire)** : rien de la licence. Pas de nom (Demon Slayer, Kimetsu, personnages),
  pas de kanji 滅 ni 鬼殺隊, pas de motif de haori de personnage (damier vert et noir, chanvre rose…), pas de boucles
  d'oreilles hanafuda, pas de blason de famille précis. Uniquement des éléments génériques japonais.
  Enseignes autorisées : 茶, 団子, 蕎麦, 宿, 藤, 清水, 甘味, 呉服, 薬 (pas d'alcool : pas de 酒).

## Règles techniques Roblox

- **Pas de faces coplanaires qui se chevauchent** (scintillement / z-fighting) : un détail posé sur un mur dépasse d'au moins
  0,1 stud ; deux blocs qui se recouvrent ne partagent pas une face au même endroit avec des couleurs différentes.
- Rien ne flotte : tout repose sur quelque chose (sauf câbles et lampions suspendus, accrochés à un support).
- Taille minimale 0,1 stud. Préférer des tailles entières ou au demi-stud.
- Budget de pièces : respecter celui donné pour l'asset (Roblox mobile). Un grand aplat = un seul bloc.
- `collide=False` pour les petits détails décoratifs hors de portée (lampions, câbles, enseignes, feuillage fin).
- Le couloir `|x| < 30` reste **vide** : aucun asset ne doit y empiéter au sol (sauf les arches/portes qui l'enjambent en hauteur, ≥ 30 studs).

## Aperçu

```bash
cd roblox/zone-naruto
PY=/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/bvenv/bin/python   # Python avec bpy 5.2
$PY apercu.py assets.batiments:machiya --variant 1                 # → apercus/batiments-machiya-v1-{a,b}.png
$PY apercu.py assets.glycines:arche_glycines --cam "60,20,90" --target-pt "0,20,0" --res 1200x675
```

La vue A regarde l'avant (côté -Z) en 3/4, la vue B l'arrière, plus haut. Regarder les images avec l'outil Read.
Un rendu prend 20 à 60 s (Cycles CPU, 16 échantillons).
