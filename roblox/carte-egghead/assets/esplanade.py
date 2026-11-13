"""Esplanade nord (finition) : le front du laboratoire au fond de l'axe et les aires du port de nacelles.

    python apercu.py assets.esplanade:front_labo --res 1200x675 --samples 12
    python apercu.py assets.esplanade:aire_nacelle --variant 2

Conventions de la carte : origine au centre de l'emprise au sol (y = 0), avant = -Z local (posé yaw 180 au fond
de l'esplanade : l'avant regarde le sud, vers l'apparition), studs sur les dessus, aucun texte.
"""

from __future__ import annotations

import math

from kit import mix
from palette import c

BLANC = c("blanc_labo")
NUIT = c("bleu_nuit")


def front_labo(b, variant: int = 0, largeur: float = 78, profondeur: float = 44, hauteur: float = 118, **_):
    """Front du laboratoire (version île du bâtiment à écran géant de la référence) : podium à studs, corps blanc à
    bandeaux violets, deux tambours rayés lavande / violet coiffés de dômes, grand écran abstrait tourné vers -Z
    (cadre bleu nuit, barres Neon cyan et violettes en « égaliseur », filets blancs : aucun texte), rangée de
    hublots, porte à cadre d'or ; au-dessus, galette violette à studs, tambour lavande, coupole de verre à cœur
    Neon, halo orange et antenne. Tout dans largeur × profondeur au sol (avant sur la ligne des façades, rien
    devant). ≈ 80 pièces, ≤ 12 Neon, 1 transparente."""
    W, P, H = float(largeur), float(profondeur), float(hauteur)
    i0 = len(b.parts)
    lav, vio, turq, rose = c("lavande"), c("violet"), c("turquoise"), c("rose_bonbon")
    zf = -P / 2                                        # ligne des façades (avant)
    # --- podium : toute l'emprise, 0,3 en retrait de la ligne des façades -------------------------------------------
    with b.group("Podium"):
        b.box((-W / 2 + 0.3, 0, zf + 0.3), (W / 2 - 0.3, 3.0, P / 2 - 0.3), c("dalle_labo"), studs="top",
              name="Podium")
    # --- corps central ----------------------------------------------------------------------------------------------
    xc = W / 2 - 13.0                                  # demi-largeur du corps (26 pour 78)
    zc0, zc1 = zf + 2.0, P / 2 - 2.0
    y_corps = 0.6 * H + 15.2                           # 86 pour 118
    with b.group("Corps"):
        b.box((-xc, 2.5, zc0), (xc, y_corps, zc1), BLANC, studs="top", name="Corps")
        for yb in (20.0, y_corps - 12.0):
            b.box((-xc - 0.3, yb, zc0 - 0.3), (xc + 0.3, yb + 2.2, zc1 + 0.3), vio, name="Bandeau")
    # --- deux tambours rayés aux angles avant, coiffés de dômes -----------------------------------------------------
    rt = 10.5
    xt, zt = W / 2 - rt - 0.5, zf + 14.0
    ht = y_corps + 10.0
    with b.group("Tambours"):
        for j, sx in enumerate((-1, 1)):
            b.cone_etage((sx * xt, 1.0, zt), rt, rt, ht - 1.0, [lav, vio], etages=5,
                         hauteurs=(3, 1, 3, 1, 3), name="Tambour")
            d = b.dome((sx * xt, ht, zt), rt, 7.0, rose if j == 0 else turq, rebord=0.6, collide=False)
            b.ball(d.info.get("sommet", (sx * xt, ht + 7.0, zt)), 1.2, c("or"), collide=False, name="Boule")
    # --- grand écran abstrait (sans texte) sur la face avant du corps ------------------------------------------------
    y0e, y1e = 28.0, min(66.0, y_corps - 18.0)
    xe = xc - 4.0
    with b.group("Ecran"):
        b.box((-xe - 2, y0e - 2, zc0 - 1.2), (xe + 2, y1e + 2, zc0 + 0.2), NUIT, name="Cadre")
        b.box((-xe, y0e, zc0 - 1.5), (xe, y1e, zc0 - 1.1), mix(NUIT, c("cyan"), 0.22), name="Ecran")
        n = 7
        pas = 2 * (xe - 3) / (n - 1)
        hauts = (0.30, 0.55, 0.80, 0.62, 0.42, 0.70, 0.36)
        for i in range(n):
            x = -(xe - 3) + i * pas
            h = (y1e - y0e - 8) * hauts[i]
            col = c("cyan") if i % 2 == 0 else c("neon_violet")
            b.box((x - 1.6, y0e + 3, zc0 - 1.8), (x + 1.6, y0e + 3 + h, zc0 - 1.4), col, material="Neon",
                  collide=False, shadow=False, name="Barre")
        for yl, lx in ((y1e - 4.0, xe - 3), (y1e - 6.5, (xe - 3) * 0.55)):
            b.box((-lx, yl, zc0 - 1.75), (lx, yl + 0.9, zc0 - 1.45), c("neon_blanc"), material="Neon",
                  collide=False, shadow=False, name="Filet")
    # --- hublots au-dessus de l'écran, porte à cadre d'or au pied ------------------------------------------------------
    with b.group("Hublots"):
        yh = y_corps - 6.0
        for i in range(6):
            x = -xc + 6.0 + i * (2 * xc - 12.0) / 5
            b.cyl((x, yh, zc0 - 0.1), 1.9, 0.6, c("hublot"), axis="z", name="Hublot")
    with b.group("Porte"):
        b.box((-6.0, 2.7, zc0 - 0.4), (6.0, 15.0, zc0 + 0.2), NUIT, name="Porte")
        b.box((-7.0, 2.8, zc0 - 0.7), (-6.0, 16.0, zc0 + 0.2), c("or"), name="Cadre")
        b.box((6.0, 2.8, zc0 - 0.7), (7.0, 16.0, zc0 + 0.2), c("or"), name="Cadre")
        b.box((-6.95, 15.0, zc0 - 0.75), (6.95, 16.1, zc0 + 0.15), c("or"), name="Cadre")
    # --- couronnement : galette, tambour, coupole de verre, halo orange, antenne -------------------------------------
    rg = min(xc + 4.0, P / 2 + 6.0)
    with b.group("Couronnement"):
        b.cyl((0, y_corps + 1.8, 0), rg, 4.0, vio, studs="top", name="Galette")
        b.cyl((0, y_corps + 1.0, 0), rg - 1.0, 2.6, mix(vio, NUIT, 0.35), name="Dessous")
        yt0 = y_corps + 3.8
        h_tb = 0.12 * H
        b.cyl((0, yt0 + h_tb / 2 - 0.1, 0), 17.0, h_tb, lav, name="Tambour")
        yc_ = yt0 + h_tb - 0.1
        h_cp = max(6.0, H - yc_ - 3.0)
        b.ellipsoid((0, yc_, 0), (32.0, 2 * h_cp, 32.0), c("verre"), material="Glass", transparency=0.4,
                    collide=False, name="Coupole")
        b.ball((0, yc_ + 0.35 * h_cp, 0), 5.0, c("neon_violet"), material="Neon", collide=False, shadow=False,
               name="Coeur")
        b.anneau((0, yc_ - 2.0, 0), 21.0, 0.5, c("orange"), 20, section="plat", largeur=1.6, collide=False,
                 name="Halo")
        b.cyl((0, yc_ + h_cp + 0.6, 0), 0.4, 2.6, BLANC, collide=False, name="Antenne")
        b.ball((0, yc_ + h_cp + 2.2, 0), 0.8, c("or"), collide=False, name="Boule")
    sommet = yc_ + h_cp + 3.0
    parts = b.parts[i0:]
    return {"emprise": (W, P), "hauteur": round(sommet, 1), "pieces": len(parts),
            "neon": sum(1 for p in parts if p.material == "Neon")}


COQUES = ("orange", "turquoise", "rose_bonbon", "jaune_or")
CEINTURES = ("bleu_roi", "orange", "violet", "rouge")


def aire_nacelle(b, variant: int = 0, rayon: float = 9.0, **_):
    """Aire ronde du port de nacelles : dalle claire à studs (dessus à 0,3) sur un disque d'or qui forme le liseré,
    8 points Neon cyan, nacelle garée au centre (plot, coque, ceintures, pont, siège, console, bulle de verre).
    ≤ 20 pièces, 8 Neon, 1 transparente ; ≈ 11 de haut."""
    R = float(rayon)
    v = int(variant) % 4
    with b.group("Aire"):
        b.cyl((0, 0.1, 0), R + 0.6, 0.2, c("or"), studs="top", name="Liseré")
        b.cyl((0, 0.16, 0), R, 0.28, c("dalle_labo"), studs="top", name="Aire")
        for j in range(8):
            a = math.radians(22.5 + 45 * j)
            b.cyl(((R - 1.3) * math.cos(a), 0.33, -(R - 1.3) * math.sin(a)), 0.45, 0.12, c("cyan"),
                  material="Neon", collide=False, shadow=False, name="Point")
    k = 0.8
    with b.group("Nacelle"):
        y = 0.3
        hp = 1.6 * k
        b.cyl((0, y + hp / 2 - 0.05, 0), 1.5 * k, hp, NUIT, name="Plot")
        hb = 9 * k
        yb = y + hp - 0.4 + hb / 2
        b.ellipsoid((0, yb, 0), (14 * k, hb, 14 * k), c(COQUES[v]), name="Coque")
        b.cyl((0, yb + 0.25 * hb, 0), 6.75 * k, 0.8 * k, c(CEINTURES[v]), collide=False, name="Ceinture")
        b.cyl((0, yb + 0.37 * hb, 0), 6.5 * k, 0.5 * k, BLANC, collide=False, name="Ceinture")
        yd = yb + 0.42 * hb
        b.cyl((0, yd, 0), 6.0 * k, 0.6 * k, BLANC, studs="top", collide=False, name="Pont")
        b.boxc((0, yd + 1.5 * k, 1.2 * k), (3.2 * k, 3.0 * k, 2.0 * k), c("rouge"), collide=False, name="Siege")
        b.boxc((0, yd + 1.0 * k, -2.4 * k), (3.0 * k, 2.0 * k, 1.2 * k), NUIT, collide=False, name="Console")
        hv = 9.5 * k
        b.ellipsoid((0, yd + 0.3 * k, 0), (10.6 * k, hv, 10.6 * k), c("verre"), material="Glass",
                    transparency=0.5, collide=False, name="Bulle")
    return {"emprise": (2 * R + 1.2, 2 * R + 1.2), "hauteur": round(yd + 0.3 * k + hv / 2, 2)}
