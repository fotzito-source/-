# Conventions de la carte « île du futur » (CarteEgghead)

Chaque asset est une fonction Python qui ajoute des **Parts Roblox** à un `kit.Builder` ; la même liste de pièces
sert aux rendus Blender et au modèle Roblox. À lire avec `OUTILS.md` (API du kit), `CONCEPTION.md` (intention,
composition, budgets), `SPECS.md` (fiche de chaque module) et la bible de style
`/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/eh/style/STYLE.md` (recettes des archétypes, palette, pièges). En cas de
désaccord : **SPECS.md > CONCEPTION.md > STYLE.md > OUTILS.md** pour ce qui touche à cette carte ; OUTILS.md fait
foi pour l'API du kit.

## 1. Repère, plan, niveaux

- Repère **Roblox** : X à droite (est), **Y vers le haut**, Z vers le sud (vers la caméra de la capture refEH1) ;
  le nord est **-Z**. 1 unité = 1 stud ; un personnage mesure ≈ 5 de haut et 2 de large ; la caméra Roblox le suit
  à ≈ 12,5 studs.
- **Origine de la carte** : centre de la pelouse, dessus de la pelouse à **y = 0** (pivot du modèle Roblox).
- **Toutes les cotes du plan sont dans `plan.py`** (constantes nommées en français, listes `CEINTURE`, `TUBES`,
  `OEUF`, `NACELLES`, `PIECES_OR`, `MOBILIER`, `REPERES`, `VUES`, budgets). Aucun asset ni `carte.py` n'écrit un
  nombre du plan en dur : ils importent `plan`. Corriger le plan = modifier `plan.py`, rien d'autre.
- Niveaux (dessus des surfaces) : pelouse **0** (lignes de grille 0,15 / 0,20), route **0** (marquages 0,1),
  trottoirs **0,4** (bordures rayées 0,6), sol de la couronne **0,4** (`plan.NIVEAU_COURONNE` : y de pose des
  bâtiments de la couronne), dessus du tapis 0,6 et de ses bordures 1,0. Toutes les dalles descendent à y = -2.
- Bandes (demi-largeurs) : pelouse |x| ≤ 205, |z| ≤ 301 ; trottoir intérieur → 217 / 313 ; route → 253 / 349 ;
  trottoir extérieur → **271 / 367 = ligne des façades** ; couronne jusqu'à 351 / 447 (80 de profondeur).

## 2. Assets : signature, origine, avant, yaw

```python
from kit import Builder, rot_x, rot_y, rot_z, shade, mix, varier
from palette import P, c, schema, SCHEMAS, ZONES
import plan

def tour_galettes(b, variant=0, hauteur=200, diametre=54, quai=None, **params):
    s = schema("tour_galettes", variant)          # couleurs résolues "#RRGGBB"
    with b.group("Fut"):
        ...
    return {"emprise": (diametre, diametre), "hauteur": hauteur, "ame": rayon_du_fut}
```

- Signature : `f(b, variant=0, **params) -> dict`, paramètres **nommés** exactement comme dans `SPECS.md` (on peut
  en ajouter d'autres, facultatifs, avec une valeur par défaut). Le dict renvoyé contient au moins
  `"emprise": (x, z)` et `"hauteur": h` ; les tours ajoutent `"ame"` (rayon du fût plein, pour les tubes).
- **Origine : centre de l'emprise au sol, y = 0** au sol de l'asset. Un objet volant (nacelle, pièce, œuf) a son
  origine en son centre (ou au point défini dans sa fiche), à l'altitude où `carte.py` le pose.
- **L'avant regarde -Z local.** `carte.py` pose avec `with b.at((x, y, z), yaw=…, group=…)` : l'avant regarde alors
  `(-sin yaw, 0, -cos yaw)` et l'axe X local devient `(cos yaw, 0, -sin yaw)`. Couronne : est **yaw 90**, ouest
  **270**, nord **180**, sud **0**, coins 135 (NE), 225 (NO), 45 (SE), 315 (SO) : l'avant regarde toujours la carte.
- Dans la couronne, la **largeur** suit X local (le long de la façade) et la **profondeur** suit Z local, de
  `-profondeur/2` (avant, sur la ligne des façades) à `+profondeur/2` (arrière). Les façades arrière ne se voient
  pas depuis la carte : elles peuvent rester simples (aplats), mais fermées (pas de vide visible d'en haut).
- Un asset ne pose **jamais de sol** sous lui (carte.py peint tout le sol) ; il pose son propre socle ou ses
  marches s'il en a.
- Aléatoire : `b.rng` uniquement (jamais `random`) ; la carte doit se reconstruire à l'identique.

## 3. Studs

- `studs="top"` sur **tous les dessus plats** : sols, socles, plateaux, rebords, toits plats, assises, marches,
  dessus des disques de chapeau et des galettes de bloc. Dans Roblox : Plastic + SurfaceType.Studs (aucune image).
- **Jamais** de studs sur un mur, un flanc de cylindre, un ellipsoïde (le kit refuse), une pièce Neon ou Glass.
  Sur un cylindre, seuls les disques des bouts en portent.
- Dalles de sol (carte.py) : tailles et coins **entiers** (studs raccordés), lignes de grille sur [8k, 8k + 1].
  Marquages de route sur des coins entiers aussi (tirets sur [235, 236], lignes de rive sur [219, 220] et [250, 251]).
- Les assets ronds n'ont pas à s'aligner sur la grille ; leurs dessus portent des studs quand même.

## 4. Groupes (Models Roblox) et repères

- Groupes racine posés par `carte.py` : `Sol` (pelouse, grille, sol de la couronne ; découpé en blocs de 64),
  `Trottoirs` (dalles, bordures rayées), `Routes` (voies, marquages, passages), `Tapis` (bande, bordures,
  chevrons, `Portail_Ouest`, `Portail_Est`), `Centre` (un sous-modèle par pièce : `Vente`, `Machine`, `Monument`,
  `Vitrine`, `Quetes`, `Apparition`), `Tours` (un sous-modèle par emplacement, nommé par son id de `CEINTURE` :
  `E-T-320`, `N-R1-05`, `Coin_NE`… ; plus `Tours/MurDeFond`, `Tours/Tubes`), `Ciel` (`Oeuf`, `Cable`, `Nacelles`,
  `PiecesOr`, `Dirigeable`, `Cumulus`), `Mobilier` (un sous-modèle par pose, nommé par son id), `Reperes`
  (dossier), `TracesParcelles` (facultatif, supprimable).
- Dans un asset, des sous-groupes parlants (`Socle`, `Fut`, `Galettes`, `Dome`, `Hublots`, `Neon`…) aident la
  relecture dans l'Explorer ; noms français génériques, **jamais un nom de la licence**.
- Repères (`plan.REPERES`, posés par carte.py avec `b.repere`) : `Spawn` (-3, 0, 206,5) regard vers le nord ;
  `Parcelle_W1…W4`, `Parcelle_E1…E4` (emprises complètes 111 × 105) ; `Entree_W1…E4` (zones d'escalier 15 × 55) ;
  `Tapis_Debut`, `Tapis_Fin`, `Tapis_01…08` (sommets de l'axe du tapis dans le sens du flux) ; `Vente`, `Machine`,
  `Monument`, `Vitrine`, `Quetes`, `ZoneVente`. Invisibles, sans collision, détectables.

## 5. Couleurs et matériaux

- **Uniquement `palette.py`** : `c("orange")`, `rgb(...)`, `schema("tour_galettes", variant)` (variante k = V(k+1) de
  la bible), `ZONES[cote]`, `RAYURES`, `ANNEAUX`. Tons dérivés permis : `shade(c, 0,6 à 1,25)`, `mix(a, b, t)` ;
  `varier(c, b.rng, 0,03)` seulement pour le végétal et les nuages.
- Accord : une dominante (60-70 %) + une secondaire (20-30 %) + un accent (≤ 10 %), plus `blanc_labo` ou `creme`
  pour piliers et socles ; chaud contre froid ; rayures à deux valeurs opposées ; l'or seulement pour anneaux,
  pièces, étoiles, flèches et bagues ; **ni gris, ni noir, ni métal** ; `sol_vert` réservé au sol.
- Matériaux : `SmoothPlastic` (défaut) ; `Plastic` automatiquement quand une pièce porte des studs ; **Neon** en
  petites pièces (fentes, pilules, liserés, hublots allumés, halos fins ; jamais plus de 4 studs de large), **une
  seule couleur de Neon par bâtiment** ; **Glass** transparence 0,45-0,6 pour bulles, coupoles et tubes, jamais
  derrière ou dans un autre verre, contenu des bulles opaque. Interdits : Wood, Brick, Concrete, Slate, Metal,
  Grass, Sand, Fabric, Foil. `Reflectance` 0 (0,1 au plus sur le verre).
- Aucun Neon au sol (grille, route, trottoirs) : avec le Bloom de Roblox il éblouit.

## 6. Budgets

- Carte entière : **≤ 24 000 pièces (cible 20 000-22 000), ≤ 1 500 Neon, ≤ 400 transparentes**.
- Plafonds par module et par appel : `plan.BUDGETS` et `plan.BUDGET_FONCTION` (`plan.budget_appel(fonction,
  params)` les résout). `carte.py` mesure chaque appel (pièces ajoutées) et liste les dépassements (`hors_budget`).
- Chaque constructeur rapporte, par fonction et par variante : pièces, Neon, transparentes, emprise, hauteur.
- Économies (STYLE.md § 3.4 et OUTILS.md) : un grand aplat = un bloc ; `anneau` avec `n` adapté au rayon (12-16
  sous 6, 24 jusqu'à 20, 32-48 au-delà) ; `disque` plein quand le trou ne se voit pas ; détails (fentes, hublots)
  sur la **moitié vue** seulement (l'avant ± 70°) pour la couronne ; le dos des bâtiments de la couronne est simple.

## 7. Pièges et règles de propreté

- **Faces confondues** (scintillement dans Roblox, taches noires dans Cycles) : tout détail posé sur une face
  dépasse de 0,05 à 0,1 au moins ; deux pièces qui se croisent n'ont jamais leur dessus au même niveau. Contrôle :
  `kit.faces_confondues(b.parts)` (liste vide exigée) et `kit.controles(b.parts)["problemes"]` vide.
- **Moitié basse des ellipsoïdes** toujours cachée (tambour ou fût au moins aussi haut que le dôme, ou cloche
  « dessous » : STYLE.md § 3.0) ; `res.info["dessous_visible"]` du kit signale un tambour trop court.
- **Octogones** : jamais deux carrés à 45° (étoile à 8 branches) ; cylindre, ou 2 blocs + 4 coins, ou
  `disque(n=8, rayon_int=…)` / `anneau(n=8)`.
- **Rien ne flotte par accident** : ce qui vole est voulu et lisible (nacelles en file avec halo, pièces en ligne,
  cubes en arc, nuage, halos autour d'un élément vertical sans le toucher, écart ≥ 4) ; tout le reste repose sur
  quelque chose. Hublots et cadres collés au mur (épaisseur 0,4 + f²/2R sur un mur courbe).
- **Tailles** : 0,1 au minimum sur chaque axe, 2 048 au maximum. Positions et tailles au 1/10 de stud de préférence.
- **Collisions** : petits détails, halos, antennes, fentes, colliers, palmes : `collide=False` (et
  `shadow=False` pour les très fins ou lumineux). Ellipsoïdes à portée de main : `collide=False`, la collision vient
  du fût ou d'un bloc invisible ajusté. Ce que le joueur touche (socles, comptoirs, marches, murs des boutiques) a
  une collision franche.
- **Hauteur libre** : rien de large (aire horizontale > 64 studs²) suspendu entre 5 et 40 au-dessus d'une zone
  praticable (pelouse, trottoirs, route) — la caméra Roblox sauterait. Permis : le toit du stand de vente, l'arche
  des portails du tapis, les têtes de lampadaires, les palmes, les panneaux. Tubes et nacelles au-dessus des voies :
  ≥ 40 (tubes ≥ 70).
- **Couronne** : rien devant la ligne des façades (d < 0) sauf enseignes plates de moins de 1,5 de saillie au-dessus
  de y = 8 ; une tour reste dans son disque au sol (`diametre`) ; ce qui la dépasse (bords de chapeau, soucoupes,
  halos) est au-dessus de y = 40.
- **Pelouse** : les 8 parcelles et leurs escaliers restent **vides** (seulement la pelouse, les repères et, si on
  les garde, les traces au sol). Rien de solide dans les allées `plan.COULOIRS_MARCHE` (|x| 56,5 → 80 sur toute la
  longueur des rangées). Le décor de pelouse ne va que dans la marge extérieure (|x| 191 → 205), les écarts entre
  rangées (sans barrer le passage), le U autour des pièces du centre et les marges nord et sud.

## 8. Propriété intellectuelle (Roblox retire les contenus sous licence)

- **Aucun texte dans la carte** (pas de `p.label`) : ni nom de la licence (« Egghead », « Punk », « Vega »,
  « Records », « Labophase », « Fabriophase », noms de personnages ou de navires), ni chiffres d'hologramme, ni
  textes du jeu de référence (« DOMAIN MACHINE », noms de joueurs, quêtes). Les mots du jeu (vendre, quêtes) sont
  affichés par l'interface du jeu, pas par le décor. Enseignes : pictogrammes abstraits, tirets Neon (« faux
  texte »), damiers, hublots, ou rien.
- **Aucun personnage**, robot, satellite, statue, silhouette humanoïde, dragon, pirate, drapeau à tête de mort,
  logo, emblème ; aucune nacelle « à visage » ; les deux hublots-yeux sur les dômes sont permis (style de l'île),
  jamais de bouche, de nez ni de sourcils.
- **Aucune marque** : pas de canette, pas de manette copiée d'une console du commerce (pas de boutons aux quatre
  couleurs d'une marque, pas de forme exacte).
- Noms de groupes et de pièces génériques et français. `CarteEgghead` reste un nom de fichier interne ; le modèle
  publié prendra un nom neutre (« IleDuFutur ») : décision de l'utilisateur.
- Composition : on recompose les archétypes génériques (tours rondes, dômes, soucoupes, cônes rayés, anneaux, tubes
  de verre, nacelles, pièces d'or, palmiers, sol quadrillé, l'œuf fêlé sur un nuage) dans notre propre plan ; on ne
  recopie ni un plan de l'anime ni le décor de EH5.

## 9. Contrôles et commandes

```bash
cd /home/user/-/roblox/carte-egghead
PY=/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/bvenv/bin/python
$PY apercu.py assets.tours_rondes:tour_galettes --variant 0 --params '{"hauteur": 200, "diametre": 54}' \
    --res 1200x675 --samples 12                       # vues A (3/4 avant) et B (3/4 arrière) ; lire les PNG avec Read
$PY apercu.py assets.tours_rondes:tour_galettes --cam="0,60,-260" --target-pt="0,90,0" --fov 40   # vue lointaine
$PY carte.py --stats                                  # build/parts.json + vérifications (sans Blender)
$PY rendu.py --rapide --sans-export --vues capture1 --res 1000x539 --echantillons 12
```

- Processeur partagé (4 cœurs, jusqu'à 6 agents) : aperçus ≤ 1200 × 675, 12 à 16 échantillons, **un seul rendu
  Blender à la fois**, pas de rendu inutile. Fichiers de travail dans
  `/tmp/claude-0/-home-user--/599f147d-b38d-564f-a2c6-ca8116a1da4e/scratchpad/eh/build/<module>/`, jamais dans le dossier de la carte.
- Avant de livrer un asset (STYLE.md § 9.2) : rendus A et B regardés ; couleurs de la palette ; aucune moitié basse
  d'ellipsoïde visible, rien qui flotte par erreur ; studs seulement sur les dessus ; Neon ≤ 10 % des pièces de
  l'asset (hors anneaux lumineux voulus) ; verre isolé ; collisions sensées ; aucun texte, logo, visage, personnage ;
  pièces dans le budget ; `faces_confondues` vide.
- Ne jamais lancer git (l'orchestrateur s'en charge). Ne modifier que ses propres fichiers.
