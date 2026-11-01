"""Planche d'images d'une capture, pour voir d'un coup d'œil ce qui s'est passé.

Utilisation (depuis le dossier hud_detector) :
    py -3.11 outils/planche.py fight2_adversaire
    py -3.11 outils/planche.py fight2_adversaire --pas 3

Garde une image sur --pas (6 par défaut = une toutes les 1,2 s), écrit le
temps de jeu dessus, en rouge si analyser.py l'a ignorée (HUD absent...).
Résultat : <dossier>/planche.png
"""

import argparse
import csv
from pathlib import Path

from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument("dossier")
parser.add_argument("--pas", type=int, default=6, help="garder une image sur N")
args = parser.parse_args()

dossier = Path(args.dossier)
with open(dossier / "temps.csv") as f:
    temps = {int(l["image"]): float(l["temps_jeu"] or l["temps_reel"]) for l in csv.DictReader(f, delimiter=";")}

# Validité calculée par analyser.py, si elle a déjà tourné.
valide = {}
if (dossier / "luminosite.csv").exists():
    with open(dossier / "luminosite.csv") as f:
        for i, ligne in enumerate(csv.DictReader(f, delimiter=";"), start=1):
            valide[i] = ligne["valide"] == "1"

numeros = list(range(1, len(temps) + 1, args.pas))
colonnes = 6
largeur, hauteur = Image.open(dossier / "images" / "000001.png").size
planche = Image.new("RGB", (largeur * colonnes, hauteur * ((len(numeros) + colonnes - 1) // colonnes)))

for k, i in enumerate(numeros):
    image = Image.open(dossier / "images" / f"{i:06d}.png")
    ok = valide.get(i, True)
    dessin = ImageDraw.Draw(image)
    dessin.rectangle((0, 0, 150, 13), fill=(0, 0, 0))
    dessin.text((2, 1), f"#{i} {temps[i]:.1f}s {'OK' if ok else 'IGNOREE'}",
                fill=(0, 255, 0) if ok else (255, 60, 60))
    planche.paste(image, ((k % colonnes) * largeur, (k // colonnes) * hauteur))

planche.save(dossier / "planche.png")
print(f"Planche enregistrée : {dossier / 'planche.png'}")
