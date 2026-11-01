"""Mesure le HUD image par image, détecte les lancers de sorts et les
moments où le champion est contrôlé, et compare avec tes annotations
faites à la main.

Utilisation :
    py -3.11 analyser.py fiora_fight1
    py -3.11 analyser.py fiora_fight1 --annotations fiora_fight1/annotations.csv

Format de annotations.csv (séparateur ;) — un lancer par ligne, temps de jeu
lu sur l'horloge du replay :
    temps;sort
    6:31.5;W
    6:33;Q

Résultat dans le dossier :
    luminosite.csv   (luminosité de chaque sort et ressource, image par image)
    evenements.csv   (lancers, contrôles et icônes grisées sans lancer,
                      dans l'ordre du temps)
    courbes.png      (une courbe par sort, lancers détectés et annotés,
                      périodes de contrôle en orange)
"""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from config import BARRE_RESSOURCE, PORTRAIT, SORTS, temps_en_secondes

# Un sort est "en recharge" quand sa luminosité tombe sous ce pourcentage
# de sa luminosité "disponible". Sur ta capture : ~90 disponible, 35-58 en recharge.
# 0.75 ratait le E de Cho, qui passe d'abord par un état "buff actif" à ~70
# (icône à moitié grisée) avant la vraie recharge : 0.85 l'attrape.
SEUIL_RELATIF = 0.85
# En dessous de cet écart entre le plus clair et le plus sombre, on considère
# que le sort n'a pas changé d'état pendant la capture (rien à détecter).
ECART_MINIMUM = 15
# Nombre d'images consécutives "en recharge" pour valider un lancer :
# évite qu'un seul effet visuel parasite compte comme un lancer.
IMAGES_MINIMUM = 2
# Écart toléré (en secondes) entre un lancer annoté et un lancer détecté.
TOLERANCE = 0.6
# Écart maximum entre le portrait d'une image et le portrait typique.
# Mesuré sur tes captures : 0-1 quand le HUD est affiché, 43-52 sinon.
ECART_PORTRAIT_MAX = 15
# Contrôle (projection, silence, étourdissement...) : le jeu grise TOUTES les
# icônes d'un coup. Sur Yorick, les sorts disponibles perdaient ~40 % de
# luminosité. Un sort "change" s'il varie d'au moins ce pourcentage d'une image
# à la suivante...
VARIATION_CONTROLE = 0.2
# ... et on parle de contrôle quand la MAJORITÉ des sorts disponibles chute dans
# la même image, avec au moins ce nombre de sorts. Les sorts déjà en recharge
# sont déjà sombres et ne bougent presque pas : on ne peut compter que sur les
# disponibles (souvent juste Flash et l'autre sort d'invocateur). Pas "tous" :
# sur Yorick, l'icône de relance de son Q restait allumée pendant un contrôle.
# Un vrai combo (ex. : W + E de Yorick) laisse la plupart des autres allumés.
SORTS_MIN_CONTROLE = 2
# Luminosité au-dessus de laquelle une icône immobile est "prête".
# Mesuré sur les icônes immobiles : prêtes 80-120, en recharge ou non apprises 33-60.
LUMINOSITE_MIN_PRET = 70
# Un contrôle dure rarement plus longtemps. Si les sorts grisés ne se rallument
# pas ensemble avant, c'étaient de vrais lancers (ex. : Flash + Ignite).
DUREE_MAX_CONTROLE = 3.0
# Une icône peut se griser sans que le sort soit lancé : pas assez d'énergie
# ou de mana (E de Zed), fenêtre de relance qui expire (ombre de Zed). Pour
# confirmer un vrai lancer, on regarde pendant ce délai (en secondes)...
FENETRE_CONFIRMATION = 0.4
# ... si un chiffre de recharge apparaît : nombre de pixels blancs dans l'icône.
# Mesuré : 29-56 avec un chiffre, 0-2 pour une icône grisée sans chiffre.
PIXELS_CHIFFRE_MIN = 15
# ... ou si la barre de ressource baisse d'au moins cette fraction de la barre.
# La barre fait 101 pixels : 0,015 = au moins 2 pixels (1 pixel peut trembler
# au bord). Mesuré : Q de Zed -0,33, E de Cho -0,04, Q de Yorick -0,03 ;
# la régénération ne fait que monter.
BAISSE_RESSOURCE_MIN = 0.015
# En dessous de ce remplissage maximum, on considère que le champion n'a pas
# de barre de ressource (ex. : Garen) : on ne peut pas s'en servir.
RESSOURCE_PRESENTE_MIN = 0.05


def charger_temps(dossier):
    """Renvoie (temps, nom_de_l_axe). Temps de jeu si dispo, sinon temps réel."""
    with open(dossier / "temps.csv") as f:
        lignes = list(csv.DictReader(f, delimiter=";"))
    if all(l["temps_jeu"] for l in lignes):
        return np.array([float(l["temps_jeu"]) for l in lignes]), "temps de jeu (s)"
    return np.array([float(l["temps_reel"]) for l in lignes]), "temps réel depuis le début (s)"


def remplissage_ressource(rgb):
    """Fraction de la barre de ressource remplie (0 à 1).

    La partie remplie est colorée (bleu, jaune...), le reste est presque noir :
    on cherche la dernière colonne colorée. Le texte blanc n'est pas coloré,
    donc il ne gêne pas même s'il déborde sur la partie vide.
    """
    x, y, w, h = BARRE_RESSOURCE
    bande = rgb[y:y + h, x:x + w].astype(int)
    saturation = bande.max(axis=2) - bande.min(axis=2)
    coloree = ((saturation > 80) & (bande.max(axis=2) > 100)).mean(axis=0) > 0.5
    colonnes = np.flatnonzero(coloree)
    return 0.0 if len(colonnes) == 0 else (colonnes[-1] + 1) / w


def pixels_blancs(rgb, zone):
    """Nombre de pixels blancs (chiffres de recharge) dans une icône."""
    x, y, w, h = zone
    icone = rgb[y:y + h, x:x + w].astype(int)
    return int(((icone.min(axis=2) > 190) & (icone.max(axis=2) - icone.min(axis=2) < 40)).sum())


def mesurer_hud(dossier):
    """Mesure, sur chaque image : la luminosité et les pixels blancs de chaque
    sort, le remplissage de la barre de ressource, et le portrait (pour
    vérifier ensuite que le HUD est bien affiché)."""
    images = sorted((dossier / "images").glob("*.png"))
    luminosite = {nom: [] for nom in SORTS}
    blancs = {nom: [] for nom in SORTS}
    ressource = []
    portraits = []
    px, py, pw, ph = PORTRAIT
    for chemin in images:
        rgb = np.asarray(Image.open(chemin).convert("RGB"))
        gris = np.asarray(Image.open(chemin).convert("L"), dtype=float)
        portraits.append(gris[py:py + ph, px:px + pw])
        ressource.append(remplissage_ressource(rgb))
        for nom, (x, y, w, h) in SORTS.items():
            luminosite[nom].append(gris[y:y + h, x:x + w].mean())
            blancs[nom].append(pixels_blancs(rgb, (x, y, w, h)))
    return ({nom: np.array(v) for nom, v in luminosite.items()},
            {nom: np.array(v) for nom, v in blancs.items()},
            np.array(ressource), np.stack(portraits))


def images_valides(portraits, temps):
    """True pour chaque image qui montre bien le HUD du champion suivi.

    Le portrait ne bouge presque pas d'une image à l'autre. On le compare au
    portrait "typique" (la médiane de toutes les images) : un grand écart veut
    dire autre chose à l'écran (Alt+Tab, chargement, autre champion sélectionné).
    On écarte aussi les images où le temps de jeu recule (barre de temps touchée).
    """
    reference = np.median(portraits, axis=0)
    ecart = np.abs(portraits - reference).mean(axis=(1, 2))
    temps_ne_recule_pas = temps >= np.maximum.accumulate(temps) - 0.05
    return (ecart < ECART_PORTRAIT_MAX) & temps_ne_recule_pas


def detecter_controles(luminosite, valides, temps):
    """Trouve les moments où le champion est contrôlé : tous ses sorts se
    grisent dans la même image, puis se rallument ensemble.

    Renvoie (liste de (début, fin) en temps de jeu, masque des images contrôlées).
    """
    indices = np.flatnonzero(valides)
    controle = np.zeros(len(temps), dtype=bool)
    periodes = []
    if len(indices) < 2:
        return periodes, controle

    # Une ligne par sort, une colonne par image valide.
    matrice = np.stack([luminosite[nom][indices] for nom in SORTS])
    # Rapport entre chaque image et la précédente (< 1 : le sort s'assombrit).
    rapport = matrice[:, 1:] / np.maximum(matrice[:, :-1], 1)
    chute = rapport < 1 - VARIATION_CONTROLE
    hausse = rapport > 1 / (1 - VARIATION_CONTROLE)
    # Un sort est "disponible" quand il est proche de sa luminosité la plus claire.
    disponible = matrice >= SEUIL_RELATIF * np.percentile(matrice, 90, axis=1, keepdims=True)
    # Sauf s'il n'a jamais bougé de la capture : il est alors soit toujours prêt
    # (icône claire, ex. : l'Ignite de Zed), soit jamais utilisable (icône sombre,
    # ex. : l'ultime de Zed pas encore appris au niveau 4).
    immobile = matrice.max(axis=1) - matrice.min(axis=1) < ECART_MINIMUM
    disponible[immobile] = matrice[immobile] >= LUMINOSITE_MIN_PRET

    debut = None
    for k in range(1, len(indices)):
        if debut is None:
            dispo_avant = disponible[:, k - 1]
            grises = dispo_avant & chute[:, k - 1]
            if grises.sum() >= SORTS_MIN_CONTROLE and grises.sum() > dispo_avant.sum() / 2:
                debut = k
                sorts_grises = grises  # ceux qu'on surveille pour la fin du contrôle
        elif temps[indices[k]] - temps[indices[debut]] > DUREE_MAX_CONTROLE:
            debut = None  # trop long : pas un contrôle, on laisse les lancers
        # Fin du contrôle : au moins la moitié des sorts grisés se rallument
        # ensemble (pas tous : le joueur peut relancer un sort tout de suite).
        elif hausse[sorts_grises, k - 1].sum() >= np.ceil(sorts_grises.sum() / 2):
            controle[indices[debut:k]] = True
            periodes.append((temps[indices[debut]], temps[indices[k]]))
            debut = None
    if debut is not None:  # encore contrôlé à la fin de la capture
        controle[indices[debut:]] = True
        periodes.append((temps[indices[debut]], temps[indices[-1]]))
    return periodes, controle


def detecter_lancers(valeurs, temps):
    """Renvoie (temps des lancers détectés, seuil utilisé ou None).
    valeurs et temps ne doivent contenir que des images valides."""
    if len(valeurs) == 0 or valeurs.max() - valeurs.min() < ECART_MINIMUM:
        return [], None

    # Le niveau "disponible" = les valeurs les plus claires de la série.
    # On prend le 90e percentile plutôt que le max pour ignorer un pic isolé.
    disponible = np.percentile(valeurs, 90)
    seuil = SEUIL_RELATIF * disponible
    en_recharge = valeurs < seuil

    lancers = []
    i = 1
    while i < len(valeurs):
        # Un lancer = passage de "disponible" à "en recharge"
        # qui dure au moins IMAGES_MINIMUM images.
        if en_recharge[i] and not en_recharge[i - 1] and en_recharge[i:i + IMAGES_MINIMUM].all():
            lancers.append(temps[i])
            while i < len(valeurs) and en_recharge[i]:
                i += 1
        i += 1
    return lancers, seuil


def a_change_pendant_un_controle(t, temps_utilisables, controles):
    """Vrai si le changement détecté à t a eu lieu pendant un contrôle :
    la dernière image avant t est antérieure au contrôle, et t est sa fin.

    Contrôlé, le joueur ne peut rien lancer. Un sort qui passe en recharge
    à ce moment-là, c'est autre chose : par exemple une fenêtre de relance
    qui expire (Q de Yorick à 6:17,8, pendant le silence de Cho).
    """
    avant = temps_utilisables[temps_utilisables < t]
    if len(avant) == 0:
        return False
    return any(avant[-1] < debut and fin <= t for debut, fin in controles)


def trier_lancers(candidats, blancs, ressource, temps, valides):
    """Sépare les vrais lancers des icônes grisées sans lancer.

    candidats : {sort: [temps où l'icône est passée en recharge]}.
    Pour chaque candidat :
      1. un chiffre de recharge apparaît dans FENETRE_CONFIRMATION -> lancer ;
      2. sinon, la ressource baisse et aucun autre sort avec chiffre n'explique
         cette baisse -> lancer (activation de buff : Q de Yorick, E de Cho) ;
      3. sinon -> grisé sans lancer (manque de ressource, relance expirée).
    Ex. : Zed lance Q (énergie 70 -> 5), son E se grise faute d'énergie dans
    la même image. La baisse vient du Q, qui a un chiffre : le E est écarté.

    Renvoie ({sort: [temps des lancers]}, [(sort, temps) grisés sans lancer]).
    """
    a_une_ressource = ressource[valides].max(initial=0) >= RESSOURCE_PRESENTE_MIN

    def images_apres(t):
        return valides & (temps >= t) & (temps <= t + FENETRE_CONFIRMATION)

    avec_chiffre = {(nom, t) for nom, liste in candidats.items() for t in liste
                    if blancs[nom][images_apres(t)].max(initial=0) >= PIXELS_CHIFFRE_MIN}

    lancers = {nom: [] for nom in candidats}
    grises = []
    for nom, liste in candidats.items():
        for t in liste:
            if (nom, t) in avec_chiffre:
                lancers[nom].append(t)
                continue
            avant = valides & (temps < t)
            if a_une_ressource and avant.any():
                baisse = ressource[np.flatnonzero(avant)[-1]] - ressource[images_apres(t)].min(initial=1)
                ressource_ok = baisse >= BAISSE_RESSOURCE_MIN
            else:
                ressource_ok = True  # pas de barre : on ne peut pas vérifier
            autre_explication = any(n != nom and abs(t2 - t) <= FENETRE_CONFIRMATION
                                    for n, t2 in avec_chiffre)
            if ressource_ok and not autre_explication:
                lancers[nom].append(t)
            else:
                grises.append((nom, t))
    return lancers, grises


def charger_annotations(chemin):
    annotations = {nom: [] for nom in SORTS}
    with open(chemin) as f:
        for ligne in csv.DictReader(f, delimiter=";"):
            annotations[ligne["sort"].strip().upper()].append(temps_en_secondes(ligne["temps"].strip()))
    return annotations


def comparer(detectes, annotes):
    """Associe chaque lancer annoté au lancer détecté le plus proche (dans la tolérance)."""
    restants = list(detectes)
    trouves = 0
    for t in annotes:
        proches = [d for d in restants if abs(d - t) <= TOLERANCE]
        if proches:
            restants.remove(min(proches, key=lambda d: abs(d - t)))
            trouves += 1
    return trouves, len(annotes) - trouves, len(restants)  # bons, ratés, fausses alertes


parser = argparse.ArgumentParser()
parser.add_argument("dossier")
parser.add_argument("--annotations", help="chemin vers ton annotations.csv")
args = parser.parse_args()

dossier = Path(args.dossier)
temps, axe = charger_temps(dossier)
luminosite, blancs, ressource, portraits = mesurer_hud(dossier)
valides = images_valides(portraits, temps)
if not valides.all():
    print(f"{(~valides).sum()} image(s) ignorée(s) sur {len(valides)} : HUD absent ou temps qui recule.\n")
controles, controle = detecter_controles(luminosite, valides, temps)
for debut, fin in controles:
    print(f"Contrôlé de {debut:.1f} s à {fin:.1f} s ({fin - debut:.1f} s)")
if controles:
    print()
# Pendant un contrôle, les icônes grisées ne disent rien sur les lancers :
# on ne cherche les lancers que sur les images valides et non contrôlées.
utilisables = valides & ~controle
annotations = charger_annotations(args.annotations) if args.annotations else None

with open(dossier / "luminosite.csv", "w", newline="") as f:
    ecrivain = csv.writer(f, delimiter=";")
    ecrivain.writerow(["temps", "valide", "controle", "ressource", *SORTS])
    for i, t in enumerate(temps):
        ecrivain.writerow([f"{t:.3f}", int(valides[i]), int(controle[i]), f"{ressource[i]:.2f}",
                           *(f"{luminosite[nom][i]:.1f}" for nom in SORTS)])

# 1. Candidats : chaque passage d'une icône en recharge, hors contrôle.
candidats, seuils = {}, {}
for nom in SORTS:
    candidats[nom], seuils[nom] = detecter_lancers(luminosite[nom][utilisables], temps[utilisables])
    for t in [t for t in candidats[nom] if a_change_pendant_un_controle(t, temps[utilisables], controles)]:
        print(f"{nom} : passage en recharge à {t:.1f} s ignoré (pendant un contrôle, donc pas un lancer)")
        candidats[nom].remove(t)

# 2. Tri : vrai lancer, ou icône grisée sans lancer ?
lancers_par_sort, grises = trier_lancers(candidats, blancs, ressource, temps, valides)
for nom, t in sorted(grises, key=lambda g: g[1]):
    print(f"{nom} : grisé à {t:.1f} s sans lancer (pas assez de ressource, ou relance expirée)")
if grises:
    print()

fig, axes = plt.subplots(len(SORTS), 1, figsize=(12, 2 * len(SORTS)), sharex=True)
total_bons = total_rates = total_fausses = 0
evenements = [("controle", "", debut, fin) for debut, fin in controles]
evenements += [("grise_sans_lancer", nom, t, "") for nom, t in grises]

for ax, nom in zip(axes, SORTS):
    valeurs = luminosite[nom]
    lancers, seuil = lancers_par_sort[nom], seuils[nom]
    evenements += [("lancer", nom, t, "") for t in lancers]
    for t in [t for n, t in grises if n == nom]:
        ax.axvline(t, color="gray", linestyle=":", linewidth=2)
    for debut, fin in controles:
        ax.axvspan(debut, fin, color="tab:orange", alpha=0.25)

    # Les images ignorées apparaissent comme des trous dans la courbe.
    ax.plot(temps, np.where(valides, valeurs, np.nan), color="tab:blue")
    # Même échelle pour tous les sorts : sinon un sort qui ne bouge pas
    # paraît très agité, car l'axe zoome sur le bruit.
    ax.set_ylim(0, max(150, valeurs.max() + 10))
    ax.set_ylabel(nom, rotation=0, labelpad=15, fontsize=12)
    if seuil is not None:
        ax.axhline(seuil, color="gray", linestyle=":", linewidth=1)
    for t in lancers:
        ax.axvline(t, color="tab:red", linewidth=2, alpha=0.7)

    ligne = f"{nom} : {len(lancers)} lancer(s) détecté(s)"
    if seuil is None:
        ligne += " (le sort n'a pas changé d'état)"

    if annotations is not None:
        for t in annotations[nom]:
            ax.axvline(t, color="tab:green", linestyle="--", linewidth=2)
        bons, rates, fausses = comparer(lancers, annotations[nom])
        total_bons += bons
        total_rates += rates
        total_fausses += fausses
        ligne += f" | annotés : {len(annotations[nom])}, retrouvés : {bons}, ratés : {rates}, fausses alertes : {fausses}"
    print(ligne)

with open(dossier / "evenements.csv", "w", newline="") as f:
    ecrivain = csv.writer(f, delimiter=";")
    ecrivain.writerow(["type", "sort", "debut", "fin"])
    for type_, nom, debut, fin in sorted(evenements, key=lambda e: e[2]):
        ecrivain.writerow([type_, nom, f"{debut:.1f}", fin if fin == "" else f"{fin:.1f}"])

axes[-1].set_xlabel(axe)
titre = "Rouge = lancer | gris pointillé = grisé sans lancer | orange = contrôlé"
if annotations is not None:
    titre += " | vert pointillé = lancer annoté à la main"
fig.suptitle(titre)
fig.tight_layout()
fig.savefig(dossier / "courbes.png", dpi=100)
print(f"Graphique enregistré : {dossier / 'courbes.png'}")

if annotations is not None:
    nb_annotes = total_bons + total_rates
    nb_detectes = total_bons + total_fausses
    if nb_annotes:
        print(f"\nRappel : {total_bons}/{nb_annotes} lancers annotés retrouvés ({total_bons / nb_annotes:.0%})")
    if nb_detectes:
        print(f"Précision : {total_bons}/{nb_detectes} détections correctes ({total_bons / nb_detectes:.0%})")
