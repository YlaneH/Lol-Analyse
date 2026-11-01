# Journal du projet — séance du 1er novembre 2026

Récapitulatif de la discussion avec Claude, pour retrouver les décisions,
les conseils et la suite. L'export intégral de la conversation est dans
`historique/`.

---

## 1. Point de départ

- Data scientist en alternance (SNCF), autodidacte en data/IA, à l'aise avec
  Python et Claude Code, mais pas encore d'annotation, de fine-tuning ou
  d'application livrée. Déjà un prototype YOLO de détection de joueurs de foot.
- Objectif : un **business rentable**, pas la recherche.
- Joueur LoL **Gold**, joue beaucoup **Fiora**, un ami Diamant peut aider.

## 2. Comment l'idée a évolué

1. **IA qui analyse la macro LoL** (ce que Riot ne donne pas : rotations,
   présence aux objectifs…) à partir des replays, en lisant la minimap.
   - Faisable techniquement. Pipeline : vidéo → minimap → détection d'icônes
     (YOLO) → identification limitée aux 10 champions de la draft → suivi →
     événements → métriques → rapport avec clips.
   - Piège : les erreurs se multiplient d'étape en étape (95 % × 95 % ≈ 90 %).
     Il faut un jeu d'évaluation annoté à la main et des métriques par étape.
   - Principe retenu : **l'outil mesure, le coach juge.**
2. **Autres jeux** : CS2, Dota 2, Rocket League ont des replays lisibles
   directement (pas d'avantage à la vision par ordinateur, et CS2 est saturé :
   Leetify, Skybox, Refrag…). Valorant : Augment couvre déjà les scrims.
   Overwatch 2 / Marvel Rivals : pas d'API publique, les analystes font des
   tableurs à la main → piste intéressante. MOBAs mobiles : même idée de minimap.
3. **Duels 1v1** : l'analyse sort par sort. Exemple : Fiora contre Mordekaiser.
   Avant le niveau 6, il faut parer le E (grab) de Morde ; dans certaines
   situations, il faut plutôt parer le Q.
   - Deux erreurs à mesurer : **parade manquée** (sort clé reçu, W disponible,
     pas utilisé) et **parade gâchée** (W dépensé sur un sort appât, sort clé juste après).
   - Le code ne « comprend » pas : il applique des règles écrites par des
     joueurs (fiches de matchup), puis plus tard des statistiques.

### Décision : les duels plutôt que la macro

- Tu es ton propre client (tu joues Fiora), tu as tes propres replays, tu n'attends personne.
- Personne ne fait (à notre connaissance) de review sort par sort.
- Les briques (qui lance quoi, quand, qui est contrôlé) serviront aussi pour la macro plus tard.
- Ce qu'on sacrifie : un payeur moins clair (joueurs, coachs individuels)
  et une technique plus dure.

### Réaliste ou pas (même avec Claude Code)

| | Réaliste ? |
|---|---|
| Mesurer les sorts et les fights pour tous les champions | Oui |
| Règles génériques pour tous les champions | Oui |
| Règles fines pour quelques matchups de Fiora | Oui |
| Règles fines pour tous les matchups, à jour à chaque patch | Non : c'est un problème d'expertise et de données, pas de code |

Claude Code accélère le code, pas : le savoir des matchups, les données
(replays jouables seulement sur le patch en cours), la maintenance à chaque
patch, et **ta compréhension du pipeline** (indispensable quand il se trompe).

### Chances de réussite (estimation honnête)

Réussite technique ~70-80 %, apprentissage ~90 %, business rentable ~5-10 %,
revenu d'appoint ~15-25 %. Critère d'abandon : si personne n'est prêt à payer
20 € après ~15 entretiens, ça reste un projet de portfolio.

## 3. Validation client (entretiens)

Méthode « Mom Test » : une seule question par message, pas de pitch, pas de
« tu paierais ? ». On cherche comment ils travaillent et ce qui leur prend du temps.

**Envoyés le 1er novembre 2026** (détails dans `prospects_coachs_lol.csv`) :

| Qui | Où | Langue |
|---|---|---|
| raxeris (analyste semi-pro ESLOL2) | chat Metafy | FR |
| Swonzer (ex-PCS, coach libre en Italie) | DM X @Sw0nzer | EN |
| Visdom (head coach Caldya) | DM X @VisdomLoL | EN |

- Gaëtan (Instagram) : discussion déjà ouverte.
- Abandonnés : Lukas (Superprof demande adresse + téléphone), Atlas (bouton Fiverr désactivé).
- **Relance unique entre le 6 et le 8 novembre** si pas de réponse.
- Vague 2 possible : Rice, LeagueScoutHugo (PCS), Nayas (KCBS), Softorious (Galions Sharks).
- Avec le passage aux duels : viser aussi les **coachs individuels** (Ilyxou, settios…)
  et les **communautés de mains Fiora** (Reddit r/FioraMains, Discord).
- Si un staff répond : faire l'entretien quand même, et demander si savoir
  « qui a lancé quel sort et quand » leur servirait.

## 4. Plan Fiora

1. Trouver tes matchups prioritaires avec l'API Riot (Account-V1 → PUUID →
   Match-V5 → adversaire en top et résultat) : 3 à 5 matchups, dont un simple
   (Morde) et un ou deux complexes (Aatrox, Camille).
2. Écrire une **fiche par matchup** en « si… alors… » (quel sort parer, à quel
   niveau, quoi parer si le sort clé est en recharge, quoi ne pas parer).
   Les faire valider par des mains Fiora.
3. **Annoter tes trades** sur 3 à 5 parties : temps, adversaire, niveau, sorts
   adverses disponibles, W (disponible / utilisé / sur quel sort), PV avant/après,
   résultat, type d'erreur (aucune / manquée / gâchée), meilleur choix + justification.
4. **Point d'étape vers le 22 novembre** : détection fiable des sorts sur
   ~50 lancers annotés, et une review faite à la main postée chez les mains Fiora
   pour voir si des gens en demandent.

## 5. Ce qui a été construit (dossier `hud_detector/`)

Idée clé : en replay, le HUD du champion sélectionné affiche ses sorts et leurs
temps de recharge. On le capture 5 fois par seconde. Voir le `README.md` pour
l'utilisation et l'état des résultats.

Pièges découverts en analysant Cho'Gath, Yorick et Zed :
- HUD absent (Alt+Tab, chargement, mort) → images ignorées.
- Buffs (E de Cho, Q de Yorick) → l'icône ne se grise qu'à moitié.
- **Contrôles** → le jeu grise les actions interdites d'un coup. Pendant une
  projection : Flash grisé mais Ignite non (tornade de Yasuo sur Zed).
  Deux contrôles collés (Q puis W de Cho) se déduisent des timecodes.
- Un sort qui « tombe » en recharge pendant un contrôle n'a pas été lancé
  (fenêtre de relance du Q de Yorick, expirée pendant le silence).
- Sort non appris (R avant le niveau 6).
- Manque d'énergie/mana et relance expirée (ombre de Zed) → un vrai lancer
  doit afficher un chiffre de recharge ou faire baisser la barre de ressource.

Encore à faire : le W de Zed (l'icône s'allume au lancer), la dernière image
avant une mort, et surtout **tester sur Fiora contre Morde**.

## 6. Mise en place technique

- Activer l'API de replay : `EnableReplayApi=1` dans la section `[General]` de
  `C:\Riot Games\League of Legends\Config\game.cfg` (pas encore fait). Ça permet
  la pause et le saut automatiques (`--debut 6:00`).
- Jeu en fenêtré sans bordure, 1920×1080.
- Python 3.11 (`py -3.11`) ; librairies dans `hud_detector/requirements.txt`.
- Dépôt GitHub privé : `YlaneH/Lol-Analyse`. Sur le PC maison, la clé SSH est
  dans `C:\Users\PC\.ssh\id_ed25519` et le dépôt utilise le SSH de Windows
  (`core.sshCommand`). Sur un autre PC : `git clone` en HTTPS, ou créer une clé SSH là-bas.
- Routine : `git pull` en arrivant ; `git add -A`, `git commit`, `git push` en partant.

## 7. Conseils pour apprendre (pas seulement produire)

- Laisse Claude Code écrire le code, mais pour chaque étape, sache expliquer ce
  qu'elle reçoit, ce qu'elle renvoie et comment elle peut se tromper.
- Écris toi-même l'évaluation (annotations + calcul de précision).
- Quand le détecteur et tes annotations ne sont pas d'accord, **retourne voir
  les images** avant de décider qui a tort (Claude s'est trompé deux fois en annotant).
- Ta connaissance du jeu est ce qui transforme les mesures en règles justes :
  c'est elle qui a corrigé le Q de Yorick et expliqué la projection de Yasuo.
