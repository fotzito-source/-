# Direction artistique : « Nuraq pixel »

Charte commune à toutes les vidéos TikTok. Elle reprend le style pixel art de la vidéo de référence et le fait passer dans l'identité Nuraq. Chaque vidéo a ensuite son propre brief dans `videos/`.

---

## 1. Ce que la vidéo de référence fait bien

Analyse de la vidéo fournie (TikTok sur la viande halal : 9:16, 576 × 1024, 30 i/s, 3 min 41).

| Aspect | Constat | Ce qu'on en garde |
|---|---|---|
| **Structure** | Accroche avec un personnage et une question (« Tu manges halal depuis toujours… Mais pourquoi ? »). Ensuite, des chapitres annoncés par une petite étiquette (« LA RÈGLE DE BASE », « 1. LE NOM D'ALLAH », « 2. LE SANG »…). La fin revient au personnage du début (boucle). | Accroche-question, chapitres numérotés, retour final à l'image de départ. |
| **Rythme** | ~20 illustrations en 3 min 41, soit **une image toutes les 8 à 15 s**. Pourtant, **le texte change toutes les 1,5 à 3 s** : c'est la superposition progressive des textes qui fait le rythme, pas les coupes. | Peu de décors, beaucoup d'apparitions de texte calées sur la voix. |
| **Cadrage** | Illustrations plein cadre, vignettage sombre sur les bords. Textes centrés dans la **moitié haute**. Presque rien dans le quart inférieur, couvert par l'interface TikTok. | Même répartition. Les zones de sécurité sont détaillées plus bas. |
| **Transitions** | Coupes franches, sans effet. À l'intérieur d'un plan, la caméra dérive très lentement (zoom ou glissement de quelques %). | Coupes franches ou fondu « pixel » très court. Aucune transition tape-à-l'œil. |
| **Typographie** | Trois niveaux. ① Gros titres dans une sans-serif grasse, avec contour sombre, parfois inclinés comme un tampon. ② **Étiquettes « HUD »** dans une police pixel/terminal, encadrées : vert pour les chapitres et références, rouge pour les éléments interdits. ③ Citations en phrase normale, entre « », révélées comme à la machine à écrire. | Les trois niveaux, mais en Poppins pour le texte et en police pixel seulement pour les étiquettes courtes. |
| **Mécanique « jeu vidéo »** | Des **listes qui se construisent ligne par ligne**, comme un inventaire (« – ÉTRANGLÉ », « – ASSOMMÉ »…). Une **carte-objet lumineuse** (icône de livre avec rayons) quand un verset est cité. Des références en étiquette (CORAN 5:3, BOUKHARI 5565…). | Listes progressives, références toujours visibles à l'écran, une icône sobre pour signaler une citation. |
| **Son** | **Voix off seule**, sèche et continue, montée serrée : silences de 0,1 à 0,3 s entre les phrases, respirations coupées. On ne détecte aucun fond musical (vrais silences numériques entre les phrases). | La voix porte le rythme. Pas de musique, ambiance discrète (voir § 6). |
| **Images** | Pixel art détaillé et chaleureux (proche de *Stardew Valley*) : personnages du quotidien, animaux, lieux, nourriture. Chaque image illustre l'idée au premier degré. Aucun prophète n'est représenté. | Pixel art, mais avec la palette Nuraq (sombre et violette) et des images plus sobres. |

**Ce qu'on ne reprend pas** :
- Le **vert islamique et le rouge « interdit »** comme codes dominants : le vert n'est pas l'identité Nuraq, et le code rouge-interdit peut paraître culpabilisant.
- Les **textes inclinés ou tremblants** : chez Nuraq, le texte reste droit, stable et net.
- La **machine à écrire sur un texte sacré** : on révèle plutôt les citations ligne par ligne, en fondu.
- Le **livre ouvert couvert d'écriture pixelisée** utilisé en fond : un texte sacré ne sert jamais de texture.
- Les visuels, textes, personnages et compositions de la référence : on s'inspire des principes, pas des plans.

---

## 2. Palette

| Rôle | Couleur | Usage |
|---|---|---|
| Fond principal | `#1D1D1D` | Fonds unis, écrans de schéma, fondus de fin |
| Anthracites | `#16141D` · `#211E2C` · `#2A2638` | Premier plan, façades, panneaux |
| **Violet Nuraq** | `#6157F8` | Signature : bordures d'étiquettes, nœuds actifs, accents. Une lueur, jamais un aplat géant. |
| Lavande | `#A9A3FF` | Mots-clés dans les titres, tracés, détails |
| Lavande claire | `#DAD7FF` | Texte des étiquettes, points lumineux |
| Blanc cassé | `#F3F0EA` | Texte principal (jamais de blanc pur en grande surface) |
| Touches chaudes | soleil `#FFE2A6`, fenêtres `#F4C77E`, crépuscule `#E8917C` | Ponctuelles, pour la chaleur. Le corail ne sert pas de code « interdit ». |

**Ciels pixel** : une teinte violet-bleu, même en plein jour (`#3C4694` → `#A2A9E3`). La nuit, presque noire et légèrement violacée (`#100E1D`). Les dégradés sont **tramés** (matrice de Bayer 4×4), ce qui donne l'effet rétro sans flou.

> Le vert émeraude du paywall n'est pas utilisé.

---

## 3. Typographie

| Niveau | Police | Taille indicative (1080 × 1920) | Exemple |
|---|---|---|---|
| Titre / punchline | **Poppins ExtraBold** | 76 – 96 px | « Elle suit le **soleil**. » |
| Phrase clé | Poppins SemiBold | 50 – 62 px | « Le soleil **décline** » |
| Détail | Poppins Medium, lavande | 40 – 44 px | « juste après son point le plus haut » |
| Citation | Poppins Medium, dans « » | 44 – 48 px | Verset, toujours avec sa référence |
| Sous-titres | Poppins SemiBold sur pastille sombre (80 % d'opacité) | 44 px, 2 lignes max | Synchronisés avec la voix |
| Étiquette HUD | **VT323** (police pixel, libre de droits OFL), en capitales | 34 – 46 px | `CORAN 4:103 · TRAD. HAMIDULLAH` |
| Arabe | **Amiri** (naskh lisible, libre OFL), avec diacritiques pour le Coran | 54 – 76 px | « الفجر » |

Règles :
- Un **mot-clé en lavande** par ligne au maximum.
- Une ombre portée douce sous les textes posés sur le ciel (pas de contour épais).
- La police pixel est réservée aux **étiquettes courtes** (références, chapitres, mesures). Tout ce qui se lit comme une phrase est en Poppins.
- L'arabe n'est jamais déformé, étiré ou pixelisé. On le rend avec une vraie mise en forme (ligatures), puis on le pose sur l'image.

---

## 4. Composants « jeu vidéo » sobres

1. **Étiquette HUD** : fond sombre presque opaque, bordure violette de 5 px, coins « crantés » pixel. Elle sert aux références, aux chapitres et aux nuances (« DEUX AVIS »). On peut changer la bordure pour coder une idée (lueur rouge → bordure corail), sans jugement moral.
2. **Piste de progression** : 5 losanges reliés par des pointillés, éteints puis allumés un par un, avec un petit carillon. Reprise des chemins de progression de Nuraq : c'est une métaphore, pas une interface.
3. **Carte en verre** : panneau arrondi, fond flouté avec un voile `#1D1D1D` à 58 % et un liseré lavande à 28 %. Une seule carte à l'écran, jamais empilée.
4. **Crochets de visée** : quatre coins qui clignotent deux fois autour d'un élément pour attirer l'œil (le soleil, un objet).
5. **Tracés pointillés** : trajectoires, mesures, comparaisons (arc du soleil, ombre). Ils se dessinent progressivement.
6. **Icône de citation** : petit livre fermé en pixel, sans aucune écriture, au-dessus d'un verset. C'est un repère, pas une décoration.

À éviter : les tableaux de bord, les jauges en série, les cadres empilés, la 3D, les particules décoratives, le croissant et l'étoile en cliché.

---

## 5. Grille et zones de sécurité TikTok (1080 × 1920)

```
 0 ┌──────────────────────────────┐
   │  zone onglets TikTok (≈200)  │  ← rien d'essentiel
270│  ◆ ─ ◆ ─ ◇ ─ ◇ ─ ◇  piste    │
400│  TITRE (Poppins XB)          │
495│  phrase clé                  │  ← bloc texte : 380 → 680
560│  détail lavande              │
   │                              │
   │      monde pixel / sujet     │  ← image : 700 → 1400
   │                          ┃UI│  ← colonne d'icônes TikTok à droite
1480│   ▭ sous-titres (2 lignes) ▭ │  ← sous-titres centrés vers y = 1480
1550├──────────────────────────────┤
   │ légende, pseudo, musique TT  │  ← décor uniquement
1920└──────────────────────────────┘
```

- Marges latérales : 60 px à gauche, **140 px à droite** (colonne j'aime/commentaires).
- Rien d'important au-dessus de 220 px ni au-dessous de 1550 px.
- Le monde pixel est rendu sur une grille 216 × 384, agrandie ×5 au plus proche voisin, ce qui garde des pixels nets. **Jamais de zoom fractionnaire** sur le pixel art : il scintille. Le mouvement passe par les éléments (soleil, nuages, lumières), déplacés par pixels entiers.

---

## 6. Mouvement et son

**Mouvement**
- Le texte apparaît en fondu de 0,35 s et monte de 10 px au maximum, puis il ne bouge plus. Il disparaît en fondu de 0,3 s.
- Les listes se construisent ligne par ligne, au rythme de la voix.
- Entre deux décors : coupe franche, ou « fondu pixel » de 0,5 s (trame de Bayer).
- Un seul élément animé important à la fois.

**Son**
- La **voix off** porte la vidéo : posée, chaleureuse, environ 150 à 170 mots par minute, silences courts.
- **Pas de musique par défaut.** Beaucoup de musulmans évitent la musique instrumentale (la question fait débat entre savants). Une vidéo sans musique reste regardable par tous, et on n'a aucun droit musical à vérifier. Si une musique est un jour souhaitée, elle doit être libre de droits et documentée.
- Ambiance sonore discrète : vent, oiseaux à l'aube, grillons la nuit. Des signaux d'interface courts et doux (bip d'étiquette, carillon de progression), toujours sous la voix (−18 à −24 dB sous la voix).
- Les sons d'ambiance doivent être libres (banques CC0 type Freesound CC0, ou synthétisés comme dans l'animatic).

---

## 7. Respect du sujet : check-list avant publication

- [ ] Chaque verset est cité **mot pour mot** dans une traduction publiée, nommée à l'écran (ex. « TRAD. HAMIDULLAH »), avec sa référence sourate:verset.
- [ ] Chaque hadith a sa **référence vérifiée** (recueil + numéro + système de numérotation). S'il est résumé, l'écran dit « D'APRÈS… » et ne met pas de guillemets.
- [ ] Les **divergences** importantes sont signalées (« selon la majorité… / selon Abou Hanifa… »).
- [ ] Aucun prophète représenté. Pas de texte sacré utilisé comme texture ou décor.
- [ ] Ni accroche alarmiste, ni formulation culpabilisante, ni promesse exagérée.
- [ ] Aucune démonstration de l'application et aucun appel à l'installer. Pas de signature Nuraq sauf demande explicite.
- [ ] Les sources complètes sont dans la description TikTok.
- [ ] Une personne compétente (imam, enseignant) a relu le texte de la voix off.

---

## 8. Production des visuels

Deux voies, compatibles avec cette charte :

1. **Procédural / animatic** (comme `videos/01-heures-de-priere/animatic/render.py`) : ciel, soleil, ville, schémas. Idéal pour les sujets « astronomiques » ou abstraits, 100 % libre de droits.
2. **Illustrations pixel art** (illustrateur ou génération d'images) pour les scènes avec personnages ou lieux. Prompt de base :

> *Pixel art illustration, 9:16 vertical, cozy and calm, limited palette dominated by deep charcoal (#1D1D1D) and indigo-violet tones (#6157F8 accents, lavender highlights), small warm light touches (lamps, windows), ordered dithering in gradients, crisp pixels, no text, no letters, no calligraphy, no religious figures, generous empty space in the upper third for captions.*

Vérifier à chaque image : pas de fausse écriture arabe générée, pas de symbole religieux mal reproduit, pas de visage de prophète, pas de logo.
