# Conventions des assets (zone One Piece, style stud)

Chaque asset est une fonction Python qui ajoute des **Parts Roblox** à un `kit.Builder`.
La même liste de pièces sert au rendu Blender et au modèle Roblox : on ne construit donc qu'avec
les formes natives de Roblox (bloc, coin, cylindre, boule).

## Repère et plan de la zone

- Repère **Roblox** : X à droite, **Y vers le haut**, Z vers l'arrière ; 1 unité = 1 stud.
  Un personnage Roblox mesure environ 5 studs de haut et 2 de large.
- Origine de l'asset : centre de son emprise au sol, **y = 0 = niveau du sol** (exceptions ci-dessous).
- **L'avant de l'asset regarde -Z local.** La mise en page tourne l'asset pour que son avant regarde le couloir
  (`yaw = -90` à gauche du couloir, `+90` à droite).
- Couloir de course : `x ∈ [-30, 30]`, de `z = 0` (arche d'entrée) à `z = -400` (sortie vers la zone suivante).
  Trottoirs, accotements ou quais jusqu'à `|x| = 40` ; façades et bord des bassins en `|x| = 40`.
  Le joueur arrive par +Z et court vers -Z, puis revient : **les deux sens de lecture comptent**.
- Séquence (voir `CONCEPTION.md`) :

  | z | Section | Côtés |
  |---|---|---|
  | +40 → 0 | abords | prairie, palmiers |
  | 0 | **arche du port** « ZONE RARE / VITESSE CONSEILLÉE : 200 » | palissade jusqu'à `|x| = 130` |
  | 0 → -112 | campagne aux moulins | prairies, clôtures, moulins, granges, vaches, verger |
  | -112 → -204 | bourg du port | maisons colorées en `|x|` 40-60, terrasse haute (`y = 6`) en `|x|` 77-130 |
  | -204 → -292 | port | bassins d'eau (`y = -1,5`) de `|x| = 40` au large, navires à quai, phare, pontons |
  | -292 → -366 | place des œufs | grand ponton `|x| ≤ 56`, rose des vents (cercle de rayon 34, centre `z = -328`) |
  | -366 → -400 | rocher du crâne | le couloir traverse la bouche (passage de 64, plafond ≥ 36) |

  Collines vertes en gradins pour `|x| ≥ 130` de `z = +40` à `-196` ; plages de `-196` à `-224` ; mer au-delà.
- **Eau** : surface en `y = -1,5` (sol et quais en `y = 0`). Les navires, barques et îlots ont leur origine
  **à la surface de l'eau** (y = 0 local = flottaison) : la zone les pose en `y = -1,5`. Prolonger les coques
  d'un stud sous la flottaison pour qu'aucun jour n'apparaisse.

## API du kit (`kit.py`)

```python
from palette import c, vary          # c("rouge") → (r, g, b) ; vary("mur_blanc", b.rng) → petite variation
from kit import shade, mix, rot_x, rot_z   # shade(couleur, 0.85) assombrit ; mix(a, b, t)

def mon_asset(b, variant=0, **params):
    rng = b.rng                                   # numpy Generator (aléatoire reproductible)
    b.box((x0, y0, z0), (x1, y1, z1), c("mur_blanc"))                # bloc par deux coins
    b.boxc((cx, cy, cz), (sx, sy, sz), couleur, yaw=30)              # bloc par centre/taille, tourné autour de Y
    b.wedge((x0, y0, z0), (x1, y1, z1), couleur, down="-z")         # coin qui remplit la boîte ; la pente descend vers `down`
    b.wedge_under(a, b_, couleur, down="-z")                         # coin retourné (console, sous-face d'avant-toit)
    b.cyl((cx, cy, cz), rayon, longueur, couleur, axis="y")          # cylindre (axis x, y ou z)
    b.ball((cx, cy, cz), rayon, couleur)
    b.part("block" | "wedge" | "cyl" | "ball", taille, centre, R, couleur)  # rotation quelconque R (3×3), ex. rot_x(15)
    with b.at((x, y, z), yaw=90, group="Voiles"):                    # sous-repère (translation + rotation Y) et sous-groupe
        ...
    with b.group("Coque"):
        ...
    return {"emprise": (largeur_x, profondeur_z), "hauteur": h}
```

Options de toutes les primitives : `studs=` (`"top"`, `"all"`, `"sides"`, `"top+sides"`, `"none"` ou un tuple de faces
`("Top", "Front", …)`), `material=` (`SmoothPlastic` par défaut, `Wood`, `WoodPlanks`, `Slate`, `Concrete`, `Brick`,
`Cobblestone`, `Rock`, `Sand`, `Grass`, `Fabric`, `Metal`, `Neon`, `Glass`), `transparency=`, `reflectance=`,
`collide=False` (petits détails), `shadow=False`, `name=`.
Chaque primitive renvoie la `Part` : `p.label = {"face": "Front", "text": "TAVERNE", "color": (r, g, b), "bg": (r, g, b) ou None,
"font": "sans", "vertical": False}` ajoute un panneau texte (SurfaceGui dans Roblox). Police `"sans"` pour le
français (la police `"brush"` est japonaise). Un texte lisible **des deux côtés** = deux pièces dos à dos, l'une avec
`face: "Front"`, l'autre avec `face: "Back"`.

Pour une forme en pixels (tête de mort, lettres en relief, motif) : `textures.glyph_mask(texte, cases, font="sans", bold=1)`
donne un masque booléen et `textures.mask_rects(masque)` le découpe en rectangles → un bloc par rectangle.

Formes Roblox à connaître :
- `wedge` : face pleine au fond et dessous, pente vers `down` ; une pente avec `studs="top"` reçoit les studs.
- un cylindre Roblox est lisse ; ses studs ne vont que sur les disques des extrémités.
- une voile gonflée = 2 ou 3 blocs décalés (ventre en avant) ou un bloc + des coins, pas une boule.

## Mobilier commun (`assets/mobilier.py`, déjà écrit, à réutiliser)

`drapeau_pirate(b, variant, hauteur, largeur, mat=True)` (pavillon générique, drapeau vers +X local), `guirlande_fanions(b, p0, p1, n, creux, variant)`,
`cordage(b, p0, p1, creux)`, `bouee(b, variant)` (anneau rouge et blanc), `lanterne_quai`, `tonneaux`, `caisses`, `bitte`,
`canon`, `ancre`, `coffre_tresor`, `barre_navire`, `filet_peche`, `panneau(b, texte, variant)`, `banc`, `cloture_bois`,
`vache`, `botte_foin`, `crabe`, `mouette`, `coquillages`, `viande_geante`, `mat_guirlande`, `mat_vigie`.
Import : `from assets.mobilier import drapeau_pirate, bouee` (appel dans un `with b.at(...)` pour les placer).

## Style « stud » attendu

- Silhouettes **simples et lisibles de loin**, détails à trois échelles : masse (coque, maison, rocher), éléments
  (mâts, voiles, toits, balcons, ailes de moulin), petits accents (lanternes, bouées, fanions, volets, pots de fleurs).
  Pas de bouillie de petits blocs.
- **Couleurs franches** de `palette.py`, ambiance plein soleil. Utiliser `vary()` pour casser les grands aplats
  (murs en « pixels » de 2-4 teintes proches). Pas de gris sale : pierres et roches beige chaud ; pas de vert émeraude dominant.
- **Studs** (`studs="top"`) sur les dessus horizontaux visibles, les ponts de navires, les quais, les pentes de toit et
  les dessus de rochers ; pas sur les murs d'habitation, les voiles ni l'eau. Faces studdées de préférence aux dimensions entières.
- Mer de l'Est façon dessin animé : bois chaud, voiles crème gonflées, coques brun-rouge ou jaunes, toits rouges, bleus
  et turquoise, auvents rayés, volets colorés, palmiers courbés, moulins à ailes jaunes ou blanches, ciel bleu, eau turquoise.

## Propriété intellectuelle (obligatoire : Roblox retire les jeux sous licence non autorisée)

- **Aucun nom** de la licence ni de ses personnages, navires, villes ou lieux, nulle part (pièces, groupes, textes,
  commentaires visibles) : pas de « One Piece », pas de noms de personnages, pas de « Going Merry », « Thousand Sunny »,
  « Baratie », « Loguetown », « Foosha », « Cocoyasi », « Marine », etc. Le nom de dossier et `ZoneOnePiece` restent internes.
- **Aucun emblème exact** : pas de tête de mort au chapeau de paille, pas de pavillon d'équipage reconnaissable,
  pas de logo de la Marine (mouette + ancre), pas de figure de proue reconnaissable (pas de tête de mouton, pas de
  tête de lion à crinière en soleil, pas de proue en tête de poisson). Proues autorisées : volute simple, dragon ou
  serpent de mer stylisés génériques, ou rien.
- **Aucun personnage**, aucune silhouette de personnage, aucun chapeau de paille isolé mis en valeur.
- Autorisé : têtes de mort génériques (`drapeau_pirate`), navires pirates génériques, moulins, phare rayé,
  viande sur l'os de dessin animé, mandarines, mouettes, coffres au trésor, rose des vents.
- **Textes autorisés** (police `sans`, en français) : « ZONE RARE », « VITESSE CONSEILLÉE : 200 » (arche d'entrée),
  « PORT », « TAVERNE », « MARCHÉ », « POISSONS », « FRUITS », « VIANDE », « MOULIN », « PHARE », « AUBERGE »,
  « CHANTIER », « ÉPICES », « PLAGE », « FERME », « TRÉSOR », « BIENVENUE ». Pas de mot d'alcool (« RHUM », « GROG »,
  « BIÈRE ») : jeu tous publics.

## Règles techniques Roblox

- **Pas de faces coplanaires qui se chevauchent** (scintillement / z-fighting) : un détail posé sur un mur dépasse d'au moins
  0,1 stud ; deux blocs qui se recouvrent ne partagent pas une face au même endroit avec des couleurs différentes.
- Rien ne flotte : tout repose sur quelque chose (sauf cordages, fanions, lanternes suspendues, accrochés à un support).
  Les navires reposent sur l'eau (coque prolongée sous la flottaison).
- Taille minimale 0,1 stud. Préférer des tailles entières ou au demi-stud.
- Budget de pièces : respecter celui donné pour l'asset (Roblox mobile, **12 500 pièces au maximum pour toute la zone**).
  Un grand aplat = un seul bloc.
- `collide=False` pour les petits détails décoratifs (cordages, fanions, voiles, enseignes, feuillage fin, gréement).
- Le couloir `|x| < 30` reste **vide** au sol (de y = 0,05 à y = 12, rien de solide) ; **rien du tout au-dessus du couloir
  (|x| < 31) sous y = 30** (la caméra Roblox saute quand le joueur passe dessous). Les arches qui enjambent le couloir
  (arche d'entrée, bouche du crâne) gardent leur dessous à y ≥ 34-36. Vérifier avec `python zone.py` :
  `nb_couloir_encombre` et `trop_bas_au_dessus_du_couloir` doivent être vides.
- Les grands ensembles (sol, eau, collines, arche, rocher) sont découpés en blocs de 64 × 64 studs par `zone.decouper`.

## Aperçu

```bash
cd roblox/zone-one-piece
PY=/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/bvenv/bin/python   # Python avec bpy 5.2
$PY apercu.py assets.port:galion --variant 0 --res 1200x675 --samples 12        # → apercus/port-galion-v0-{a,b}.png
$PY apercu.py assets.monuments:porte_entree --cam "60,30,90" --target-pt "0,25,0" --res 1200x675 --samples 12
$PY zone.py --stats                                                             # plan complet, couloir, budget
$PY rendu.py --rapide --sans-export --vues entree,port                          # vues de contrôle de la zone
```

La vue A regarde l'avant (côté -Z) en 3/4, la vue B l'arrière, plus haut. Regarder les images avec l'outil Read.
Un rendu prend 20 à 60 s (Cycles CPU). Le processeur est partagé : rester à 1200×675 et 12-16 échantillons.
