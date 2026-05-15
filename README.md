# PIJOBS — Plateforme de recrutement IA

Projet Django complet de recrutement avec :

- authentification candidat / recruteur
- publication d’offres
- dépôt de candidature
- analyse IA automatique du CV
- suggestion IA
- pré-décision automatique
- tri intelligent
- archivage séparé des candidatures refusées

---

## Fonctionnalités principales

### 1. Authentification
- inscription
- connexion
- rôles : `RH` / `CANDIDATE`

### 2. Recrutement
- création et affichage d’offres
- tableau de bord recruteur
- tableau de bord candidat

### 3. Candidature
- dépôt de CV
- validation des formats : `pdf`, `doc`, `docx`
- taille maximum : `5 Mo`
- blocage des doublons

---

## Les 4 options IA intégrées

### Option 1 — Score automatique du CV
Après l’envoi d’une candidature :
- le système extrait le texte du CV
- compare le CV avec l’offre
- calcule un score de matching entre `0` et `100`
- stocke le résultat dans :
  - `ai_score`
  - `ai_recommendation`
  - `ai_source`
  - `ai_last_analysis_at`

### Option 2 — Pré-décision automatique
Si le score est très faible :
- la candidature est automatiquement refusée
- elle est déplacée vers `RejectedCandidature`
- `auto_rejected=True`

### Option 3 — Tri intelligent
Le recruteur voit les candidatures triées par pertinence :
- score IA décroissant
- fallback simple si aucun recommender n’est disponible

### Option 4 — Les 3 combinés
Le projet réunit :
- score automatique
- suggestion IA
- auto-refus
- tri intelligent
- bouton de réanalyse IA côté recruteur

---

## Architecture IA

Fichier principal :
- `accounts/ai_service.py`

Fonctions principales :
- extraction du texte CV
- calcul du score
- suggestion métier
- chargement d’un modèle entraîné si disponible :
  - `ml_models/cv_matching_model.pkl`
- fallback TF-IDF si aucun modèle n’est trouvé

---

## Stockage des candidatures

### `Candidature`
Contient les candidatures :
- en attente
- acceptées

Cette table peut alimenter le DWH.

### `RejectedCandidature`
Contient les candidatures refusées.

Caractéristiques :
- pas d’AutoField
- PK = SHA1
- refus archivés
- exclus du Data Warehouse
- conservation des champs IA

---

## Installation

```bash
python -m venv venv