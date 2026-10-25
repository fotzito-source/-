# Conventions des assets (zone Jujutsu Kaisen, ville de nuit, style stud)

Chaque asset est une fonction Python qui ajoute des **Parts Roblox** à un `kit.Builder`. La même liste de
pièces sert au rendu Blender et au modèle Roblox : on ne construit donc qu'avec les formes natives de
Roblox (bloc, coin, cylindre, boule). Lire aussi `CONCEPTION.md` (séquence, palette, propriété
intellectuelle).

## Repère

- Repère **Roblox** : X à droite, **Y vers le haut**, Z vers l'arrière ; 1 unité = 1 stud.
  Un personnage Roblox mesure environ 5 studs de haut et 2 de large. Un étage d'immeuble fait 8 studs
  (9 pour le rez-de-chaussée).
- Origine de l'asset : centre de son emprise au sol, **y = 0 = niveau du sol** (le train fait exception :
  y = 0 au niveau des rails).
- **L'avant de l'asset regarde -Z local.** La mise en page tourne l'asset (`yaw`) pour que son avant
  regarde le couloir. Avec `yaw = -90` (côté gauche, x < 0) : -Z local → +X monde, +X local → +Z monde.
  Avec `yaw = 90` (côté droit) : -Z local → -X monde, +X local → -Z monde.
- Zone : entrée en z = 0, sortie en z = -496 (la zone suivante, Bleach, commence là). Le joueur arrive par
  +Z et court vers -Z, puis revient : **les deux sens de lecture comptent**.
  - Viaduc d'entrée : z = 0 (tablier z ∈ [-8, 8]).
  - Rue commerçante : z -12 → -150 (petite rue transversale z ∈ [-100, -84]).
  - Passerelle 1 : z = -150. Quartier des tours : z -156 → -296. Passerelle 2 : z = -300.
  - Approche : z -300 → -354.
  - Grand carrefour = place des œufs : carré \|x\| ≤ 59, z ∈ [-446, -354], centre z = -400, rayon 34.
  - Incident : z -446 → -474. Immeuble effondré (sortie) : z -474 → -496.
- **Couloir de course** : `x ∈ [-45, 45]` (90 de large). Trottoirs jusqu'aux façades en `|x| = 55`. Seconde
  rangée à partir de `|x| = 97`, tours de fond à partir de `|x| = 151`, bord du sol en `|x| = 263`.

## Règles du couloir (vérifiées par `zone.py --stats`)

1. **Rien de solide** dans `|x| < 45` entre y = 0,05 et y = 12, sauf le sol (`couloir_libre` doit trouver 0).
2. **Rien du tout**, solide ou non, au-dessus de `|x| < 46` sous **y = 30**
   (`trop_bas_au_dessus_du_couloir` doit être vide). Un ouvrage qui enjambe le couloir a son dessous à
   **34 ou plus** (viaduc : 36) et ses appuis en `|x| ≥ 46` (92 studs libres) ; la sortie a 110 studs libres.
3. Les façades sont en `|x| = 55`. Une façade peut avoir des saillies vers le trottoir :
   - entre y = 0 et y = 7 : 0,6 stud au plus (seuils, cadres, lampions plaqués), parce que le mobilier est
     posé contre les façades ;
   - au-dessus de y = 7 : 4 studs au plus (auvents, balcons, enseignes, climatiseurs), soit `|x| ≥ 51`.
4. Les escaliers des passerelles occupent `|x| ∈ [46,5 ; 54,5]` le long du trottoir (zones réservées dans
   `zone.py`) ; les immeubles qui sont derrière reculent de 4,5 (`RECUL_ESCALIER`).
5. Le mobilier de trottoir est placé par `zone.py`, qui réserve les zones occupées (`reserver`) pour
   éviter les chevauchements. Un asset n'ajoute rien sur le trottoir hors de son emprise et de ses
   saillies autorisées.

## API du kit (`kit.py`)

```python
from palette import c, vary          # c("bleu_marine") → (r, g, b) ; vary("beton", b.rng) → petite variation
from kit import shade, mix, rot_x, rot_z   # shade(couleur, 0.85) assombrit ; rot_z(angle) pour incliner
from assets.mobilier import enseigne_verticale, clim, cable, _segment   # petits éléments réutilisables

def mon_asset(b, variant=0, **params):
    rng = b.rng                                   # numpy Generator (aléatoire reproductible)
    b.box((x0, y0, z0), (x1, y1, z1), c("beton"))                   # bloc par deux coins
    b.boxc((cx, cy, cz), (sx, sy, sz), couleur, yaw=30)              # bloc par centre/taille, tourné autour de Y
    b.wedge((x0, y0, z0), (x1, y1, z1), couleur, down="-z")         # coin qui remplit la boîte ; la pente descend vers `down`
    b.wedge_under(a, b_, couleur, down="-z")                         # coin retourné (console, sous-face)
    b.cyl((cx, cy, cz), rayon, longueur, couleur, axis="y")          # cylindre (axis x, y ou z)
    b.ball((cx, cy, cz), rayon, couleur)
    b.part("block", (sx, sy, sz), (cx, cy, cz), rot_z(12), couleur)  # bloc incliné (rotation quelconque)
    with b.at((x, y, z), yaw=90, group="Enseignes"):                 # sous-repère (translation + rotation Y) et sous-groupe
        enseigne_verticale(b, "ラーメン", variant=2)
    return {"emprise": (largeur_x, profondeur_z), "hauteur": h}
```

Options de toutes les primitives : `studs=` (`"top"`, `"all"`, `"sides"`, `"top+sides"`, `"none"` ou un
tuple de faces `("Top", "Front", …)`), `material=` (`SmoothPlastic` par défaut, `Plastic`, `Concrete`,
`Brick`, `Metal`, `Neon`, `Glass`, `Slate`…), `transparency=`, `reflectance=`, `collide=False` (petits
détails), `shadow=False`, `name=`.

Chaque primitive renvoie la `Part`. Pour y mettre un panneau texte (SurfaceGui dans Roblox) :
`p.label = {"face": "Front", "text": "ラーメン", "color": (r, g, b), "bg": (r, g, b) ou None,
"font": "sans" | "brush", "vertical": True/False, "glow": 1.2}`. Avec `glow`, le texte est lumineux
(LightInfluence 0) : à utiliser pour les enseignes au néon et les écrans. Un seul label par pièce. Pour
un texte sur les deux faces, utiliser deux pièces dos à dos (voir `mobilier.enseigne_verticale`).

Pour les grands signes en relief en pixels : `textures.glyph_mask(texte, cases, font="sans", bold=0.5)`
donne un masque, que `textures.mask_rects(masque)` découpe en rectangles (un bloc par rectangle).

Formes Roblox à connaître :
- `wedge` : face pleine au fond et dessous, pente vers `down` ; une pente avec `studs="top"` reçoit les studs.
- Un cylindre Roblox est lisse ; ses studs ne vont que sur les faces planes (disques).

## Style « stud » attendu

- Silhouettes **simples et lisibles de loin**, détails à trois échelles : la masse (immeuble), les
  éléments (bandeaux de fenêtres, auvents, enseignes, citernes) et les petits accents (néons,
  climatiseurs, lampions). Pas de bouillie de petits blocs.
- **Couleurs franches** de `palette.py`. Utiliser `vary()` pour casser les grands aplats.
  - 70 % de bleus et de gris, 20 % de clairs, 10 % de néons.
  - Le violet est réservé à l'incident.
  - Jamais de noir pur sur un grand volume, jamais de vert émeraude dominant.
- **Fenêtres** :
  - en rubans continus (un bloc par étage et par face) ou en grilles simples ;
  - les fenêtres éclairées sont en matériau `Neon` (`fenetre_chaude`, `fenetre_froide`), à doser : une
    sur trois ou quatre, pour que la ville paraisse « de nuit » sans éblouir en plein jour ;
  - les vitres éteintes en `vitre`, `vitre_bleue` ou `vitre_claire`.
- **Néons et écrans** :
  - enseignes verticales en drapeau (`enseigne_verticale`), bandes de néon aux angles des tours ;
  - écrans géants : cadre `ecran_fond` + aplats lumineux (Neon) en motifs abstraits (bandes, dégradés en
    3 ou 4 blocs, formes géométriques) ou un mot autorisé en `label` avec `glow`.
- **Studs** (`studs="top"`) sur les dessus horizontaux visibles : toits, acrotères, auvents, quais,
  tabliers, sol. **Pas de studs sur les murs d'immeubles.** Les dimensions des faces studdées sont de
  préférence des entiers.
- Toits vivants : citernes d'eau (cylindres), climatiseurs, locaux techniques, antennes, garde-corps,
  panneaux de toit. Feux rouges d'obstacle (`rouge_balise`, Neon) sur tout ce qui dépasse 60 studs.

## Propriété intellectuelle (obligatoire)

Rien de la licence : aucun nom de la série, de l'école ou des personnages, aucun personnage, aucun objet
maudit (doigts…), aucune marque ou aucun symbole de personnage, aucun motif d'uniforme, aucun « domaine »
recopié. Pas de 呪術, de 高専 ni de 帳. Pas de marque réelle : pas de « 109 », pas de nom de magasin, de
supérette ou de compagnie ferroviaire, pas de livrée réelle, pas de logo, pas de publicité de marque.

**Textes autorisés** : ラーメン, 本, 薬, コンビニ, カラオケ, 映画, 寿司, 喫茶, 百貨店, 駅, 東口, 西口, 出口,
止まれ, 立入禁止, 24H. 渋谷 n'apparaît qu'une fois (plaque du viaduc). Pas d'alcool (pas de 酒 ni de 居酒屋).

## Règles techniques Roblox

- **Pas de faces coplanaires qui se chevauchent** (scintillement, ou z-fighting) : un détail posé sur un
  mur dépasse d'au moins 0,1 stud ; deux blocs qui se recouvrent ne partagent pas une face au même
  endroit avec des couleurs différentes.
- Rien ne flotte : tout repose sur quelque chose (sauf les câbles et objets suspendus, accrochés à un
  support).
- Taille minimale 0,1 stud. Préférer des tailles entières ou au demi-stud.
- **Budget de pièces** : respecter celui donné pour chaque asset (toute la zone ≤ 13 500 pièces). Un grand
  aplat = un seul bloc.
- `collide=False` et `shadow=False` pour les petits détails hors de portée (enseignes, néons, câbles,
  climatiseurs, vitres de façade en saillie).
- Les grands ensembles (sol, fond, viaduc, immeuble effondré, dômes) sont découpés par `zone.py` en blocs
  de 64 × 64 studs (streaming Roblox).

## Aperçu

```bash
cd roblox/zone-jujutsu-kaisen
PY=/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/bvenv/bin/python   # Python avec bpy 5.2
$PY apercu.py assets.mobilier:planche --variant 0 --cam=-6,16,-34 --target-pt=40,5,0 --res 1200x675 --samples 12
$PY apercu.py assets.batiments:immeuble_boutique --variant 3 --params '{"etages": 6}' --res 1200x675 --samples 12
$PY zone.py --stats                                           # plan complet : pièces, couloir libre, rien de trop bas
$PY rendu.py --rapide --sans-export --vues rue,place          # rendus de contrôle de la zone
```

La vue A regarde l'avant (côté -Z) en 3/4, la vue B l'arrière, plus haut. Regarder les images avec
l'outil Read. Le processeur est partagé : rester à 1200x675 au plus et à 12-16 échantillons pour les aperçus.
