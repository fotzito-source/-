"""Assets de la carte « île du futur » : chaque module expose des fonctions `f(b, variant=0, **params)`.

Conventions communes (voir OUTILS.md) :
- origine = centre de l'emprise au sol, y = 0 au niveau du sol ; 1 unité = 1 stud, Y vers le haut ;
- l'avant de l'asset regarde -Z local ; la carte le tourne avec `b.at(pos, yaw=…)` ;
- tout est construit avec `kit.Builder` (primitives et assemblages arrondis) ;
- `exemple.py` : asset de référence ; `test_primitives.py` : vitrine de toutes les formes du kit.
"""
