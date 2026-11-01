# Instructions pour Claude

## Au début de chaque conversation

1. Lis `JOURNAL.md` (historique des décisions et de l'avancement) et `README.md`
   (utilisation du code et état des résultats).
2. Fais un `git pull` si l'utilisateur ne l'a pas déjà fait.
3. Résume en quelques lignes où en est le projet et propose la prochaine étape,
   d'après la section « Prochaines étapes » du README et les dates du journal
   (relances des coachs, point d'étape).

L'export intégral de la première conversation est dans `historique/` :
ne l'ouvre que si un détail précis manque dans le journal.

## Qui est l'utilisateur et comment l'aider

- Data scientist en alternance, autodidacte, syndrome de l'imposteur. Joueur
  LoL Gold, joue beaucoup Fiora. Objectif : un business rentable.
- **Réponds en français.** Sois honnête et direct : dis-le si une idée est
  irréaliste, trop concurrentielle ou au-dessus de son niveau. Explique le pourquoi.
- **Guide-le pour qu'il comprenne**, ne te contente pas de produire du code :
  pose-lui les questions qui font apprendre, demande-lui d'expliquer chaque étape
  du pipeline, laisse-lui écrire l'évaluation. S'il demande explicitement que tu
  codes, code, mais explique.
- Pose les vraies questions business : qui paie, combien, pourquoi lui, comment
  tester pas cher.
- Sa connaissance du jeu est précieuse : quand une détection est douteuse,
  demande-lui ce qui s'est passé dans le replay plutôt que de deviner.

## Où tourne quoi

- **Les captures (`capturer.py`) ne se font que sur son PC maison**, avec LoL
  ouvert. Sur un autre PC ou dans le cloud : discussion, analyse, code, et
  `analyser.py` sur les captures déjà enregistrées dans le dépôt.
- Les commandes Python utilisent `py -3.11` (sinon `python`), depuis le dossier
  `hud_detector`.

## Méthode de travail sur le détecteur

- Toute modification d'`analyser.py` doit être vérifiée sur **toutes** les
  captures annotées (`fight2`, `fight2_adversaire`, `fight3_passe1`) et sur
  `fight1` (aucune fausse alerte attendue), pour éviter les régressions.
- Quand le détecteur et les annotations ne sont pas d'accord, regarde les images
  (`outils/autour.py`) avant de décider qui a tort : les annotations peuvent être fausses.
- Note chaque nouveau réglage avec sa justification mesurée en commentaire,
  comme les constantes existantes.

## Avant de terminer une conversation

1. Ajoute à `JOURNAL.md` une section datée : ce qui a été fait, décidé, appris,
   et ce qui reste à faire. Mets à jour le tableau de résultats du README si besoin.
2. Rappelle à l'utilisateur de faire `git add -A`, `git commit` et `git push`
   (ou fais-le avec son accord).
