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
