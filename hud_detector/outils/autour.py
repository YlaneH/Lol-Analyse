"""Montre le HUD juste avant et juste après des moments précis.

C'est l'outil pour vérifier une détection : "le Q à 375,0 est-il un vrai
lancer ?" -> on regarde si un chiffre de recharge apparaît, si la ressource
baisse, si tout le HUD se grise (contrôle)...

Utilisation (depuis le dossier hud_detector) :
    py -3.11 outils/autour.py fight3_passe1 195.2 205.6 210.8

Une ligne par moment : 2 images avant, l'image du moment (temps en jaune),
2 images après. Résultat : <dossier>/autour.png
"""

import argparse
import csv
from pathlib import Path

from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument("dossier")
parser.add_argument("moments", nargs="+", type=float, help="temps de jeu en secondes")
args = parser.parse_args()

dossier = Path(args.dossier)
with open(dossier / "temps.csv") as f:
    temps = [float(l["temps_jeu"] or l["temps_reel"]) for l in csv.DictReader(f, delimiter=";")]

largeur, hauteur = Image.open(dossier / "images" / "000001.png").size
planche = Image.new("RGB", (largeur * 5, hauteur * len(args.moments)))

for ligne, moment in enumerate(args.moments):
    centre = min(range(len(temps)), key=lambda k: abs(temps[k] - moment))
    for colonne, k in enumerate(range(centre - 2, centre + 3)):
        if not 0 <= k < len(temps):
            continue
        image = Image.open(dossier / "images" / f"{k + 1:06d}.png")
        dessin = ImageDraw.Draw(image)
        dessin.rectangle((0, 0, 60, 12), fill=(0, 0, 0))
        dessin.text((2, 0), f"{temps[k]:.1f}", fill=(255, 255, 0) if k == centre else (255, 255, 255))
        planche.paste(image, (colonne * largeur, ligne * hauteur))

planche.save(dossier / "autour.png")
print(f"Images enregistrées : {dossier / 'autour.png'}")
