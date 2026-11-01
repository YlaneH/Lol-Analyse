"""Capture le HUD du champion sélectionné pendant un replay.

Utilisation (replay lancé, champion sélectionné, jeu en fenêtré sans bordure) :
    py -3.11 capturer.py fiora_fight1 --duree 30
    py -3.11 capturer.py fiora_fight1 --duree 30 --debut 6:00

Déroulé avec un seul écran :
    1. tu lances la commande depuis le terminal ;
    2. le script met le replay en pause et bipe chaque seconde pendant 5 s :
       fais Alt+Tab pour revenir sur le jeu ;
    3. bip aigu : le replay repart (au moment --debut si tu l'as donné)
       et la capture commence ;
    4. double bip : c'est fini, le replay est remis en pause.

Sans API de replay, le script marche quand même (sans pause ni saut),
mais tu n'auras que le temps réel, pas le temps de jeu.

Résultat dans le dossier donné :
    images/000001.png, 000002.png, ...  (la zone du HUD)
    temps.csv                           (numéro d'image, temps réel, temps de jeu)
"""

import argparse
import csv
import time
import winsound
from pathlib import Path

import mss
import requests
import urllib3
from PIL import Image

from config import IMAGES_PAR_SECONDE, URL_REPLAY, URL_TEMPS_LIVE, ZONE_HUD, temps_en_secondes

# L'API de replay utilise un certificat local non signé : on désactive
# l'avertissement, c'est normal pour un serveur sur 127.0.0.1.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def lire_temps_de_jeu():
    """Temps de jeu du replay en secondes, ou None si aucune API ne répond."""
    try:
        reponse = requests.get(URL_REPLAY, verify=False, timeout=0.2)
        return reponse.json()["time"]
    except (requests.RequestException, KeyError, ValueError):
        pass
    # Secours : l'API Live Client Data marche aussi en replay, même quand
    # l'API de replay n'est pas activée. Elle donne le temps, mais ne permet
    # ni pause ni saut.
    try:
        reponse = requests.get(URL_TEMPS_LIVE, verify=False, timeout=0.2)
        return reponse.json()["gameTime"]
    except (requests.RequestException, KeyError, ValueError):
        return None


def api_replay_active():
    try:
        return "time" in requests.get(URL_REPLAY, verify=False, timeout=0.5).json()
    except (requests.RequestException, ValueError):
        return False


def piloter_replay(**reglages):
    """Envoie des réglages à l'API de replay, par ex. paused=True ou time=360."""
    requests.post(URL_REPLAY, json=reglages, verify=False, timeout=2)


parser = argparse.ArgumentParser()
parser.add_argument("dossier", help="dossier de sortie, par ex. fiora_fight1")
parser.add_argument("--duree", type=float, default=30, help="durée de capture en secondes")
parser.add_argument("--debut", help="moment du replay où commencer, par ex. 6:00")
parser.add_argument("--attente", type=int, default=5, help="secondes pour revenir sur le jeu (Alt+Tab)")
args = parser.parse_args()

dossier = Path(args.dossier)
(dossier / "images").mkdir(parents=True, exist_ok=True)

api_dispo = api_replay_active()
if api_dispo:
    # Pause tout de suite : le replay n'avance pas pendant que tu fais Alt+Tab.
    piloter_replay(paused=True)
    print("Replay mis en pause.")
elif lire_temps_de_jeu() is not None:
    print("API de replay non activée : pas de pause ni de saut, mais le temps de jeu sera enregistré.")
    print("Mets le replay en lecture toi-même au bip aigu.")
else:
    print("Aucune API du jeu ne répond : seul le temps réel sera enregistré.")

# Avec un seul écran, la capture prend ce qui est affiché : le jeu doit être
# au premier plan. Un bip court marque chaque seconde, un bip aigu le départ.
print(f"Reviens sur le jeu (Alt+Tab), la capture démarre dans {args.attente} s...")
for _ in range(args.attente):
    winsound.Beep(600, 150)
    time.sleep(0.85)

if api_dispo:
    if args.debut:
        piloter_replay(time=temps_en_secondes(args.debut), paused=False)
    else:
        piloter_replay(paused=False)
    time.sleep(1.5)  # laisse le temps au replay de charger et de reprendre
winsound.Beep(1200, 300)

gauche, haut, largeur, hauteur = ZONE_HUD
zone = {"left": gauche, "top": haut, "width": largeur, "height": hauteur}
intervalle = 1 / IMAGES_PAR_SECONDE
nb_images = int(args.duree * IMAGES_PAR_SECONDE)

with mss.MSS() as sct, open(dossier / "temps.csv", "w", newline="") as f:
    ecrivain = csv.writer(f, delimiter=";")
    ecrivain.writerow(["image", "temps_reel", "temps_jeu"])

    debut = time.perf_counter()
    for i in range(1, nb_images + 1):
        # On vise un instant précis plutôt que de dormir un intervalle fixe :
        # sinon le temps de capture s'ajoute à chaque tour et on dérive.
        cible = debut + (i - 1) * intervalle
        attente = cible - time.perf_counter()
        if attente > 0:
            time.sleep(attente)

        brut = sct.grab(zone)
        temps_jeu = lire_temps_de_jeu()
        temps_reel = time.perf_counter() - debut

        Image.frombytes("RGB", brut.size, brut.rgb).save(dossier / "images" / f"{i:06d}.png")
        ecrivain.writerow([i, f"{temps_reel:.3f}", "" if temps_jeu is None else f"{temps_jeu:.3f}"])

# Pause à la fin : le replay reste sur place pour la deuxième passe
# (même --debut, mais avec l'autre champion sélectionné).
if api_dispo:
    piloter_replay(paused=True)
winsound.Beep(1200, 150)
winsound.Beep(1200, 150)
print(f"{nb_images} images enregistrées dans {dossier}")
