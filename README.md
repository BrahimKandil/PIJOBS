# 🚀 PIJOBS — Plateforme de recrutement IA (version finale)

Projet Django complet, intégrant la nouvelle fonctionnalité **Candidature**
(formulaire candidat + décision recruteur + refus stockés sans AutoField,
hors Data Warehouse).

---

## 📁 Structure

```
PIJOBS-final/
├── accounts/              # Authentification, profils, candidatures (FEATURE)
│   ├── models.py          # User, RecruiterProfile, CandidateProfile,
│   │                      # RecruitmentPost, Candidature, RejectedCandidature
│   ├── forms.py           # LoginForm + CandidatureForm + RejectionForm
│   ├── views.py           # Auth + apply_to_post, recruiter_accept, recruiter_reject
│   ├── urls.py            # URLs candidature
│   ├── admin.py           # Tous les modèles enregistrés
│   ├── tests.py           # 18 tests unitaires (tous verts)
│   └── migrations/
├── ai_engine/             # IA (existant)
├── documents/             # Gestion documents (existant)
├── recruitment/           # (existant)
├── myapp/                 # ETL Data Warehouse + pipelines IA (existant)
│   ├── cron.py            # ⬅ Filtre situation="accepted" → DWH
│   ├── pipline.py         # ⬅ Pipeline ML
│   └── ...
├── IAmodelsApps/          # Modèles ML (existant)
├── templates/accounts/    # base + dashboards + candidature_form +
│                          # my_applications + recruiter_applications
├── config/                # settings, urls, wsgi
├── manage.py
└── requirements.txt
```

---

## 🎯 Nouvelle fonctionnalité : Candidature

### 1. Côté Candidat
- **`/api/auth/posts/<post_id>/apply/`** — Formulaire pour postuler à une offre :
  - Validation **PDF/DOC/DOCX** + taille max **5 Mo**
  - Empêche les doublons (déjà acceptée OU déjà refusée)
- **`/api/auth/my-applications/`** — Liste de mes candidatures (acceptées + refusées)

### 2. Côté Recruteur
- **`/api/auth/recruiter/post/<post_id>/applications/`** — Liste des candidatures
- **`/api/auth/recruiter/candidature/<id>/accept/`** *(POST)* — Accepter
- **`/api/auth/recruiter/candidature/<id>/reject/`** *(POST)* — Refuser (avec motif)

### 3. Logique de stockage 🔑

- **Acceptée** → reste dans `Candidature` (table avec AutoField). Exportée
  vers le DWH par `myapp/cron.py` (filtre `situation="accepted"`).
- **Refusée** → déplacée vers `RejectedCandidature` :
  - **Pas d'AutoField** (PK = SHA1 = 40 caractères hex)
  - **Jamais exportée** vers le DWH
  - L'ID auto de `Candidature` n'est **pas consommé** par les refus
  - Les CV restent **archivés** (RGPD / IA)

```python
# accounts/views.py — recruiter_reject
@require_POST
def recruiter_reject(request, candidature_id):
    cand = get_object_or_404(Candidature, id=candidature_id,
                             post__recruiter=request.user)
    post_id = cand.post_id  # capturé AVANT delete

    with transaction.atomic():
        RejectedCandidature.objects.create(...)  # PK = SHA1, pas d'AutoField
        cand.delete()                            # libère l'ID auto
```

---

## ⚙️ Installation

```bash
# 1. Cloner / extraire le projet
cd PIJOBS-final

# 2. Environnement virtuel
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

# 3. Dépendances
pip install -r requirements.txt
# OU minimum requis :
pip install django djangorestframework

# 4. Migrations (la base est déjà supprimée pour reset propre)
python manage.py makemigrations
python manage.py migrate

# 5. Créer un super utilisateur (optionnel)
python manage.py createsuperuser

# 6. Tests unitaires
python manage.py test accounts -v 2
# → Ran 18 tests in ~10s. OK ✅

# 7. Lancer le serveur
python manage.py runserver
```

---

## 🧪 Tests unitaires (18 ✅)

```
RejectedCandidatureModelTests
  ✓ test_no_autofield_pk_is_hash               # PK = SHA1 (40 chars)
  ✓ test_two_rejects_same_candidate_post_blocked
  ✓ test_different_posts_get_different_refs

CandidatureFormTests
  ✓ test_valid_pdf
  ✓ test_bad_extension_rejected                # .exe → 400
  ✓ test_too_big_rejected                      # > 5 Mo → 400

ApplyViewTests
  ✓ test_login_required
  ✓ test_candidate_can_get_form
  ✓ test_candidate_can_submit
  ✓ test_double_apply_blocked
  ✓ test_rh_cannot_apply

RecruiterDecisionTests
  ✓ test_accept_requires_post                  # GET → 405
  ✓ test_reject_requires_post                  # GET → 405
  ✓ test_only_rh_can_decide
  ✓ test_accept_keeps_candidature
  ✓ test_reject_moves_to_rejected_table        # ⬅ feature clé
  ✓ test_reject_other_recruiters_post_forbidden

MyApplicationsTests
  ✓ test_aggregates_accepted_and_rejected
```

---

## 🛡️ Sécurité

- ✅ `@login_required` sur toutes les vues protégées
- ✅ `@require_POST` sur accept/reject (anti-CSRF)
- ✅ `post__recruiter=request.user` (un RH ne peut décider que sur ses propres offres)
- ✅ Validation extension + taille des fichiers
- ✅ Transactions atomiques (`transaction.atomic`)

---

## 🔗 Compatibilité avec le projet existant

| Composant existant | Impact | Statut |
|---|---|---|
| `myapp/cron.py` (ETL) | Filtre déjà `situation="accepted"` | ✅ Aucun changement requis |
| `myapp/pipline.py` (ML) | Lit le DWH | ✅ Aucun impact |
| `IAmodelsApps/*` | Modèles ML | ✅ Inchangés |
| `recruitment/`, `documents/`, `ai_engine/` | Apps existantes | ✅ Inchangés |
| `config/settings.py` | Ajout `DEFAULT_AUTO_FIELD` | ✅ Compatible |

---

## 📝 Notes importantes

- L'ancienne migration `0003_candidature.py` (incompatible) a été supprimée
  et remplacée par `0003_alter_candidateprofile_birth_date_and_more.py` qui
  crée à la fois `Candidature` (avec les nouveaux champs) et `RejectedCandidature`.
- La base SQLite `db.sqlite3` a été supprimée pour permettre un reset propre.
  En production, prévoir une **migration RunPython** pour préserver les
  candidatures existantes.
