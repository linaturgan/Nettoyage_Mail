# Nettoyage Mail

Outil macOS pour trier rapidement les expéditeurs Apple Mail, protéger certains contacts, supprimer en masse les messages inutiles et générer des rapports.

## Ce que fait le projet

- génère une liste des expéditeurs à classer pour un mois choisi
- permet de classer les expéditeurs dans une interface locale simple
- conserve une liste des expéditeurs protégés
- conserve une liste des expéditeurs bloqués
- conserve une liste des expéditeurs à supprimer sans blocage durable
- produit un aperçu avant suppression réelle

## Pré-requis

- un Mac
- l’application `Mail` configurée avec vos comptes
- `python3` disponible dans le Terminal

## Lancement rapide

Double-cliquez sur :

- `Lancer Nettoyage Mail.command`

ou lancez :

```bash
python3 lanceur_nettoyage_mail.py
```

Le navigateur s’ouvrira automatiquement.

## Flux conseillé

1. Choisir l’année et le mois
2. Cliquer sur `1. Generer la liste a traiter`
3. Cliquer sur `2. Ouvrir l'editeur`
4. Classer les expéditeurs
5. Cliquer sur `3. Apercu du nettoyage`
6. Vérifier le rapport
7. Cliquer sur `4. Supprimer vraiment` si tout est correct

## Fichiers importants

- `expediteurs_proteges.csv`
- `expediteurs_bloques.csv`
- `expediteurs_nettoyer_sans_bloquer.csv`
- `output/expediteurs_a_traiter.csv`

## Donnees locales et Git

- les vrais fichiers `expediteurs_*.csv` sont pensés pour rester locaux
- s'ils n'existent pas encore, le programme les cree automatiquement avec le bon en-tete
- le depot peut versionner seulement les fichiers `*.example.csv`
- les sorties de `output/` restent locales elles aussi

## Remarques

- `03_apply_cleanup.applescript` travaille en aperçu tant que le pilote lui demande un `dry run`
- l’historique des traitements est enregistré dans `output/historique_nettoyage.json`
- les chemins sont relatifs au dossier du projet, donc le dossier peut être déplacé

## Publication GitHub

Le dépôt est prêt à être initialisé localement et poussé vers GitHub.
