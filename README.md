# Vidéos TikTok : découvrir l'islam, style « Nuraq pixel »

Ce dépôt réunit des scripts et des prototypes de vidéos courtes, verticales (9:16), sur des notions de l'islam. Le style visuel est en pixel art, aux couleurs de Nuraq.
Ce ne sont **pas** des publicités : aucune démonstration de l'application, aucun appel à l'installer.

| Fichier | Contenu |
|---|---|
| [`direction-artistique.md`](direction-artistique.md) | Analyse de la vidéo de référence et charte commune : palette, typographie, composants, zones de sécurité, mouvement, son, check-list de respect du sujet |
| [`videos/01-heures-de-priere/brief.md`](videos/01-heures-de-priere/brief.md) | Vidéo 01 : « Pourquoi l'heure de la prière change chaque jour ? ». Brief complet en 7 points, sources vérifiées |
| `videos/01-heures-de-priere/transcription-voix-off.txt` | Texte de la voix off : version pour générateur de voix + version horodatée |
| `videos/01-heures-de-priere/animatic/animatic.mp4` | Prototype animé de 86 s (sans voix off, sous-titres incrustés) |
| `videos/01-heures-de-priere/animatic/sous-titres.srt` | Sous-titres synchronisés, à importer dans CapCut, Premiere… |
| `videos/01-heures-de-priere/animatic/render.py` | Générateur de l'animatic (Python, numpy, Pillow, ffmpeg) |
| `videos/01-heures-de-priere/animatic/voix.py` | Génération de la voix off avec Cartesia (clé dans `CARTESIA_API_KEY`), puis `render.py --voix voix` |
| `videos/01-heures-de-priere/images/` | Images clés du storyboard |

Régénérer l'animatic :

```bash
cd videos/01-heures-de-priere/animatic
python3 render.py              # → animatic.mp4 + sous-titres.srt
python3 render.py --stills 2,24,38   # images de contrôle dans stills/
```

## Autre projet : carte Roblox

| Dossier | Contenu |
|---|---|
| [`roblox/zone-naruto/`](roblox/zone-naruto/README.md) | Zone Naruto (Konoha) en style stud pour un jeu Roblox « Volez un œuf » : plan et assets en Python, rendus Blender, modèle Roblox `.rbxm` et place de démo `.rbxl` |
| [`roblox/zone-demon-slayer/`](roblox/zone-demon-slayer/README.md) | Zone Demon Slayer (village Taishō, allée de glycines, montagne au tunnel de torii), même pipeline |
| [`roblox/prompt-zone-one-piece.md`](roblox/prompt-zone-one-piece.md) | Prompt complet pour générer la zone One Piece avec un autre Claude Code |
