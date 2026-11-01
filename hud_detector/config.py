"""Réglages partagés par les scripts.

Toutes les coordonnées sont en pixels, pour un écran en 1920x1080
avec la taille de HUD par défaut. Si tu changes de résolution ou
d'échelle de HUD, il faut recalibrer avec calibrer.py.
"""

# Zone capturée : le panneau en bas à gauche du replay
# (portrait du champion sélectionné + ses sorts).
# (gauche, haut, largeur, hauteur)
ZONE_HUD = (0, 830, 310, 140)

# Position de chaque icône de sort DANS la zone capturée ci-dessus.
# (gauche, haut, largeur, hauteur)
# On ne garde que le centre de l'icône : le bord contient le cadre doré
# et les chiffres de niveau, qui ne changent pas avec la recharge.
SORTS = {
    "Q": (55, 90, 28, 24),
    "W": (93, 90, 28, 24),
    "E": (132, 90, 28, 24),
    "R": (170, 90, 28, 24),
    "D": (220, 90, 28, 24),
    "F": (255, 90, 28, 24),
}

# Portrait du champion sélectionné, dans la zone capturée.
# Sert à vérifier que le HUD est bien affiché sur chaque image.
PORTRAIT = (10, 15, 60, 60)

# Barre de ressource (mana bleue, énergie jaune...), dans la zone capturée.
# Seulement les 3 lignes du haut de la barre : le texte blanc "100 / 200"
# est au milieu et fausserait la mesure du remplissage.
BARRE_RESSOURCE = (76, 44, 101, 3)

# Nombre d'images capturées par seconde.
IMAGES_PAR_SECONDE = 5

# API de replay de LoL (activer EnableReplayApi=1 dans game.cfg).
URL_REPLAY = "https://127.0.0.1:2999/replay/playback"
# Secours quand l'API de replay n'est pas activée : donne seulement le temps de jeu.
URL_TEMPS_LIVE = "https://127.0.0.1:2999/liveclientdata/gamestats"


def temps_en_secondes(texte):
    """'6:29' -> 389.0 ; '6:29.5' -> 389.5 ; '389' -> 389.0"""
    if ":" in texte:
        minutes, secondes = texte.split(":")
        return int(minutes) * 60 + float(secondes)
    return float(texte)
