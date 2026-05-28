import pickle

from sklearn.metrics.pairwise import cosine_similarity

from accounts.ai_engine.cv_extractor import extract_cv_text
from accounts.models import RecruitmentPost

# ==========================================
# LOAD TRAINED MODEL ONLY
# ==========================================

bundle = pickle.load(
    open("ml_models/recommender.pkl", "rb")
)

# reuse trained transformer
model = bundle["model"]


# ==========================================
# BUILD CANDIDATE TEXT
# ==========================================

def build_candidate_text(candidate, cv_text):

    return f"""
    {candidate.skills}
    {candidate.experience}
    {candidate.education}
    {candidate.description}
    {cv_text}
    """


# ==========================================
# BUILD POST TEXT
# ==========================================

def build_post_text(post):

    return f"""
    {post.title}
    {post.domain}
    {post.description}
    {post.company_name}
    {post.required_skills}
    """


# ==========================================
# MAIN RECOMMENDATION FUNCTION
# ==========================================

def recommend_posts(candidate_profile, top_k=10):

    # -----------------------------
    # Get active posts
    # -----------------------------

    posts = RecruitmentPost.objects.filter(
        is_active=True
    )

    # -----------------------------
    # No posts
    # -----------------------------

    if not posts.exists():
        return []

    # -----------------------------
    # If posts <= 10 return all
    # -----------------------------

    if posts.count() <= top_k:
        top_k = posts.count()

        # recommendations = []
        #
        # for post in posts:
        #
        #     recommendations.append({
        #         "post": post,
        #         "score": 1.0
        #     })
        #
        # return recommendations

    # -----------------------------
    # Extract CV text
    # -----------------------------

    cv_text = extract_cv_text(
        candidate_profile.cv.path
    )

    # -----------------------------
    # Build candidate text
    # -----------------------------

    candidate_text = build_candidate_text(
        candidate_profile,
        cv_text
    )

    # -----------------------------
    # Candidate embedding
    # -----------------------------

    candidate_embedding = model.encode(
        [candidate_text]
    )

    # -----------------------------
    # Create posts text list
    # -----------------------------

    post_texts = []

    for post in posts:

        post_texts.append(
            build_post_text(post)
        )

    # -----------------------------
    # Create posts embeddings
    # -----------------------------

    post_embeddings = model.encode(
        post_texts
    )

    # -----------------------------
    # Compute similarities
    # -----------------------------

    similarities = cosine_similarity(
        candidate_embedding,
        post_embeddings
    )[0]

    # -----------------------------
    # Combine posts + scores
    # -----------------------------

    recommendations = []

    for post, score in zip(posts, similarities):

        recommendations.append({
            "post": post,
            "score": round(float(score), 2)
        })

    # -----------------------------
    # Sort descending
    # -----------------------------

    recommendations.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # -----------------------------
    # Return top 10
    # -----------------------------

    return recommendations[:top_k]