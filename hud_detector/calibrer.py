"""Vérifie que les rectangles de config.py tombent bien sur les icônes de sorts.

Utilisation :
    py -3.11 calibrer.py capture_plein_ecran.png
    py -3.11 calibrer.py            (sans argument : fait une capture de l'écran)

Le script enregistre calibration.png : la zone du HUD agrandie x3,
avec un rectangle par sort. Ouvre-la et vérifie que chaque rectangle
est bien au centre de son icône. Sinon, corrige SORTS dans config.py.
"""

import sys

import mss
from PIL import Image, ImageDraw

from config import SORTS, ZONE_HUD

ZOOM = 3


def charger_ecran():
    if len(sys.argv) > 1:
        return Image.open(sys.argv[1]).convert("RGB")
    with mss.MSS() as sct:
        brut = sct.grab(sct.monitors[1])
        return Image.frombytes("RGB", brut.size, brut.rgb)


ecran = charger_ecran()
print(f"Taille de l'image : {ecran.size} (attendu : (1920, 1080))")

g, h, l, ht = ZONE_HUD
hud = ecran.crop((g, h, g + l, h + ht)).resize((l * ZOOM, ht * ZOOM), Image.NEAREST)

dessin = ImageDraw.Draw(hud)
for nom, (x, y, w, hh) in SORTS.items():
    boite = (x * ZOOM, y * ZOOM, (x + w) * ZOOM, (y + hh) * ZOOM)
    dessin.rectangle(boite, outline=(255, 0, 255), width=2)
    dessin.text((x * ZOOM + 2, y * ZOOM - 14), nom, fill=(255, 0, 255))

hud.save("calibration.png")
print("Image enregistrée : calibration.png")
