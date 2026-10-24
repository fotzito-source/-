"""Assets de la zone One Piece : chaque module expose des fonctions `f(b, variant=0, **params)`.

Conventions communes (voir `CONVENTIONS.md`) :
- origine = centre de l'emprise au sol, y = 0 au niveau du sol (navires, barques et îlots : y = 0 à la flottaison) ;
- l'avant de l'asset regarde -Z local (vers le couloir une fois placé) ;
- tout est construit avec `kit.Builder` et les couleurs de `palette.py`.
"""
