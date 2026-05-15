# accounts/ai_service.py

from __future__ import annotations

import os
import re
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from django.conf import settings
from django.utils import timezone

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    import joblib
except Exception:
    joblib = None

try:
    from docx import Document
except Exception:
    Document = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


# ============================================================
# CONFIG IA
# ============================================================
ACCEPT_THRESHOLD = 65.0
REJECT_THRESHOLD = 30.0
AUTO_REJECT_THRESHOLD = 15.0  # mettre à None pour désactiver


# ============================================================
# RESULTATS IA
# ============================================================
@dataclass
class AIScoringResult:
    score: float
    recommendation: str
    source: str
    extracted_text: str


# ============================================================
# OUTILS TEXTE
# ============================================================
def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_post_text(post) -> str:
    parts = [
        getattr(post, "title", "") or "",
        getattr(post, "domain", "") or "",
        getattr(post, "description", "") or "",
        getattr(post, "company_name", "") or "",
        getattr(post, "required_skills", "") or "",
    ]
    return normalize_text(" ".join(parts))


def suggest_decision(score: float) -> str:
    if score >= ACCEPT_THRESHOLD:
        return "recommend_accept"
    if score < REJECT_THRESHOLD:
        return "recommend_reject"
    return "borderline"


# ============================================================
# EXTRACTION TEXTE CV
# ============================================================
def extract_text_from_pdf(file_path: str) -> str:
    if not PdfReader:
        return ""
    try:
        reader = PdfReader(file_path)
        texts = []
        for page in reader.pages:
            texts.append(page.extract_text() or "")
        return normalize_text(" ".join(texts))
    except Exception:
        return ""


def extract_text_from_docx(file_path: str) -> str:
    if not Document:
        return ""
    try:
        doc = Document(file_path)
        return normalize_text(" ".join(p.text for p in doc.paragraphs))
    except Exception:
        return ""


def extract_text_from_file(file_field) -> str:
    """
    Extrait le texte d'un CV uploadé.
    Support principal :
      - pdf
      - docx
    Les .doc peuvent rester non extraits si aucune lib dédiée n'est installée.
    """
    if not file_field:
        return ""

    try:
        file_name = file_field.name.lower()
        file_path = file_field.path
    except Exception:
        return ""

    if file_name.endswith(".pdf"):
        return extract_text_from_pdf(file_path)

    if file_name.endswith(".docx"):
        return extract_text_from_docx(file_path)

    if file_name.endswith(".doc"):
        # Pas de support natif fiable ici sans dépendance spécifique.
        return ""

    return ""


# ============================================================
# CHARGEMENT MODELES IA EXISTANTS
# ============================================================
def get_ml_models_dir() -> str:
    return os.path.join(settings.BASE_DIR, "ml_models")


def load_cv_matching_model():
    """
    Cherche votre modèle entraîné principal :
      ml_models/cv_matching_model.pkl
    """
    if joblib is None:
        return None

    model_path = os.path.join(get_ml_models_dir(), "cv_matching_model.pkl")
    if not os.path.exists(model_path):
        return None

    try:
        return joblib.load(model_path)
    except Exception:
        return None


def load_recommender_model():
    """
    Cherche un recommender éventuel :
      ml_models/recommender.pkl
    """
    if joblib is None:
        return None

    model_path = os.path.join(get_ml_models_dir(), "recommender.pkl")
    if not os.path.exists(model_path):
        return None

    try:
        return joblib.load(model_path)
    except Exception:
        return None


# ============================================================
# SCORE FALLBACK TF-IDF
# ============================================================
def compute_tfidf_similarity(cv_text: str, post_text: str) -> float:
    cv_text = normalize_text(cv_text)
    post_text = normalize_text(post_text)

    if not cv_text or not post_text:
        return 0.0

    try:
        vectorizer = TfidfVectorizer(stop_words=None)
        matrix = vectorizer.fit_transform([cv_text, post_text])
        sim = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        return round(float(sim) * 100, 2)
    except Exception:
        return 0.0


# ============================================================
# SCORE VIA MODELE ENTRAINE
# ============================================================
def _extract_probability_from_model(model, cv_text: str, post_text: str) -> Optional[float]:
    """
    Essaie d'utiliser votre modèle entraîné.
    Cette fonction reste tolérante car la structure exacte du pickle
    peut varier selon votre projet.
    """
    if model is None:
        return None

    combined = f"{cv_text} {post_text}".strip()

    try:
        # Cas pipeline sklearn classique avec predict_proba
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba([combined])
            if proba is not None:
                if len(proba.shape) == 2 and proba.shape[1] >= 2:
                    return round(float(proba[0][1]) * 100, 2)
                if len(proba.shape) == 2 and proba.shape[1] == 1:
                    return round(float(proba[0][0]) * 100, 2)

        # Cas simple predict
        if hasattr(model, "predict"):
            pred = model.predict([combined])
            if pred is not None and len(pred) > 0:
                val = pred[0]
                if isinstance(val, (int, float)):
                    if 0 <= float(val) <= 1:
                        return round(float(val) * 100, 2)
                    if 0 <= float(val) <= 100:
                        return round(float(val), 2)
    except Exception:
        return None

    return None


# ============================================================
# ORCHESTRATEUR PRINCIPAL
# ============================================================
def compute_match_score(post, cv_file_field) -> AIScoringResult:
    """
    Pipeline IA complet :
      1) extraction texte CV
      2) modèle entraîné si disponible
      3) fallback TF-IDF sinon
      4) suggestion métier
    """
    cv_text = extract_text_from_file(cv_file_field)
    post_text = build_post_text(post)

    trained_model = load_cv_matching_model()
    trained_score = _extract_probability_from_model(trained_model, cv_text, post_text)

    if trained_score is not None:
        score = max(0.0, min(100.0, trained_score))
        source = "trained_model"
    else:
        score = compute_tfidf_similarity(cv_text, post_text)
        source = "tfidf_fallback"

    recommendation = suggest_decision(score)

    return AIScoringResult(
        score=score,
        recommendation=recommendation,
        source=source,
        extracted_text=cv_text,
    )


# ============================================================
# TRI INTELLIGENT
# ============================================================
def rank_candidatures(candidatures: List) -> List:
    """
    Trie intelligent :
      - si recommender.pkl existe : on peut brancher une logique avancée
      - sinon fallback simple sur ai_score décroissant
    """
    recommender = load_recommender_model()

    if recommender is not None:
        # Pour rester robuste, on évite de dépendre d'une structure exacte.
        # Si besoin plus tard, on branchera ici votre vrai recommendation_system.py.
        try:
            return sorted(
                candidatures,
                key=lambda c: (
                    getattr(c, "ai_score", 0.0) if getattr(c, "ai_score", None) is not None else 0.0,
                    getattr(c, "years_of_experience", 0) or 0,
                ),
                reverse=True,
            )
        except Exception:
            pass

    return sorted(
        candidatures,
        key=lambda c: (
            getattr(c, "ai_score", 0.0) if getattr(c, "ai_score", None) is not None else 0.0,
            getattr(c, "years_of_experience", 0) or 0,
        ),
        reverse=True,
    )


# ============================================================
# AIDE METIER
# ============================================================
def should_auto_reject(score: float) -> bool:
    if AUTO_REJECT_THRESHOLD is None:
        return False
    return score <= AUTO_REJECT_THRESHOLD