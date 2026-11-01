# Analyse de duels LoL à partir des replays

Objectif : une review automatique des duels en lane, sort par sort.
Exemple cible : Fiora contre Mordekaiser. « Le grab de Morde t'a touché alors
que ton W (parade) était disponible, et tu as perdu le trade. »

Le principe : en replay, quand on sélectionne un champion, le HUD en bas à
gauche affiche ses sorts et leurs temps de recharge. On capture ce HUD 5 fois
par seconde et on en déduit :

- **quand chaque sort est lancé** (l'icône se grise et un chiffre de recharge apparaît) ;
- **quand le champion est contrôlé** (projection, silence… : le jeu grise tout le HUD d'un coup) ;
- **les icônes grisées sans lancer** (pas assez d'énergie ou de mana, fenêtre de relance qui expire).

En capturant les deux champions d'un fight (deux passes sur le même passage),
on peut croiser : « le Q de Cho à 6:01,4 → Yorick contrôlé à 6:02,2 ».

## Contenu

| Chemin | Rôle |
|---|---|
| `hud_detector/config.py` | Coordonnées du HUD (écran 1920×1080), réglages partagés |
| `hud_detector/calibrer.py` | Vérifie que les rectangles tombent sur les icônes → `calibration.png` |
| `hud_detector/capturer.py` | Capture le HUD pendant un replay |
| `hud_detector/analyser.py` | Détecte lancers, contrôles et icônes grisées ; compare aux annotations |
| `hud_detector/outils/planche.py` | Planche d'images d'une capture (vue d'ensemble) |
| `hud_detector/outils/autour.py` | HUD juste avant/après des moments précis (vérifier une détection) |
| `hud_detector/fight*/` | Captures de test, avec `annotations.csv` (vérité terrain vérifiée image par image) |
| `prospects_coachs_lol.csv` | Suivi des coachs/staffs contactés |
| `messages_coachs.md` | Modèles de messages de premier contact |

## Installer sur un nouveau PC

1. Installer [Python 3.11](https://www.python.org/downloads/) (cocher « Add Python to PATH ») et [Git](https://git-scm.com/download/win).
2. Récupérer le dépôt et installer les librairies :

```bash
git clone <URL_DU_DEPOT>
cd <nom_du_depot>/hud_detector
py -3.11 -m pip install -r requirements.txt
```

Si `py -3.11` n'existe pas sur ce PC, remplace-le par `python` dans toutes les commandes.

**Sans LoL installé** (PC de l'école), tu peux quand même travailler sur
`analyser.py` et les outils avec les captures déjà enregistrées.

## Utilisation

Toutes les commandes se lancent depuis le dossier `hud_detector`.

### Capturer (PC avec LoL)

Jeu en **fenêtré sans bordure**, 1920×1080. Conseillé : ajouter
`EnableReplayApi=1` dans la section `[General]` de
`C:\Riot Games\League of Legends\Config\game.cfg`, puis relancer le replay.

```bash
py -3.11 capturer.py fight4_fiora --duree 30 --attente 5
```

1. Replay ouvert, en pause, quelques secondes avant le fight.
2. Lance la commande, Alt+Tab sur le jeu pendant les bips, clique sur le champion à suivre.
3. Au bip aigu : appuie sur play (inutile si l'API de replay est activée).
4. Ne touche plus à rien jusqu'au double bip.

Pour l'autre champion : remets le replay au même moment, sélectionne-le, et
relance dans un autre dossier (`fight4_morde`). Avec l'API de replay, ajoute
`--debut 6:00` aux deux commandes pour retomber exactement au même moment.

### Analyser

```bash
py -3.11 analyser.py fight2_adversaire --annotations fight2_adversaire/annotations.csv
```

Produit dans le dossier : `courbes.png`, `evenements.csv`, `luminosite.csv`.

### Vérifier une détection

```bash
py -3.11 outils/autour.py fight3_passe1 195.2 205.6
```

## État au 1er novembre 2026

| Capture | Champion | Lancers retrouvés | Détections correctes | Contrôles |
|---|---|---|---|---|
| `fight2` | Cho'Gath (mana) | 6/6 | 6/6 | — |
| `fight2_adversaire` | Yorick (mana) | 5/5 | 5/6 | 3/3 |
| `fight3_passe1` | Zed (énergie) | 4/5 | 4/4 | 1/1 (tornade de Yasuo) |
| `fight1` | capture perturbée | — | 0 fausse alerte | — |

### Pièges déjà gérés

- HUD absent (Alt+Tab, chargement, mort) → images ignorées (comparaison du portrait).
- Buff activé avant la recharge (E de Cho, Q de Yorick) → seuil à 85 %.
- Contrôle → la majorité des sorts disponibles se grisent ensemble ; un contrôle
  ne grise que les actions interdites (pendant une projection : Flash grisé, Ignite non).
- Sort qui passe en recharge pendant un contrôle → pas un lancer (le joueur ne peut rien faire).
- Sort non appris (R avant le niveau 6) → icône immobile et sombre, ignorée.
- Manque d'énergie/mana, fenêtre de relance qui expire → un vrai lancer doit
  afficher un chiffre de recharge, ou faire baisser la barre de ressource.

### Pièges restants

- **Icône qui s'allume au lancer** : le W de Zed (échange avec l'ombre) n'est pas détecté.
- **Dernière image avant une mort** : fausse alerte possible (R de Yorick à 380,0).
- **Tout n'est testé que sur 3 champions**, une seule partie.

## Prochaines étapes

1. **Capturer un fight Fiora contre Morde** (deux passes) : vérifier que le grab
   de Morde grise bien le HUD de Fiora, et que le W de Fiora se détecte proprement.
2. Automatiser le croisement des deux passes (lancers d'un champion → contrôles subis par l'autre).
3. Écrire les fiches de matchup de Fiora (quel sort parer, dans quelle situation).
