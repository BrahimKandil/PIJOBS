import requests
import random

API_KEY = "qa_sk_07246da275492fbdb72bb40a920ccfca2276ba36"

BASE_URL = "https://quizapi.io/api/v1"

# ==========================================
# SKILL -> CATEGORY
# ==========================================
SKILL_CATEGORY = {

    "python": "Programming",
    "java": "Programming",
    "javascript": "Programming",
    "html": "Programming",
    "css": "Programming",
    "react": "Programming",
    "typescript": "Programming",
    "c++": "Programming",
    "cpp": "Programming",
    "go": "Programming",

    "sql": "Database",
    "mongodb": "Database",

    "docker": "DevOps",
    "kubernetes": "DevOps/Cloud",
    "devops": "DevOps/Cloud",
    "ansible": "Ansible",
    "jenkins": "DevOps",

    "cybersecurity": "Cybersecurity",
}

# ==========================================
# GET QUIZZES
# ==========================================
def get_quizzes_by_category(category):

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    response = requests.get(
        f"{BASE_URL}/quizzes",
        headers=headers,
        params={
            "category": category,
            "limit": 10,
            "sort": "newest"
        }
    )

    if response.status_code != 200:
        print("Quiz API Error:", response.text)
        return []

    data = response.json()

    return data.get("data", [])


# ==========================================
# GET QUESTIONS
# ==========================================
def get_questions(quiz_id):

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    response = requests.get(
        f"{BASE_URL}/questions",
        headers=headers,
        params={
            "quiz_id": quiz_id,
            "include_answers": "true"
        }
    )

    if response.status_code != 200:
        print("Question API Error:", response.text)
        return []

    data = response.json()

    return data.get("data", [])


# ==========================================
# MAIN FUNCTION
# ==========================================
def scrape_quiz(skill):

    skill = skill.lower().strip()

    category = SKILL_CATEGORY.get(skill)

    if not category:
        return []

    # ==========================================
    # FETCH QUIZZES
    # ==========================================
    quizzes = get_quizzes_by_category(category)

    if not quizzes:
        return []

    # ==========================================
    # FILTER QUIZZES BY TAG
    # ==========================================
    matching_quizzes = []

    for quiz in quizzes:

        tags = quiz.get("tags", [])

        tags_lower = [t.lower() for t in tags]

        if skill in tags_lower:
            matching_quizzes.append(quiz)

    # fallback
    if not matching_quizzes:
        matching_quizzes = quizzes

    # ==========================================
    # RANDOM QUIZ
    # ==========================================
    selected_quiz = random.choice(matching_quizzes)

    quiz_id = selected_quiz["id"]

    # ==========================================
    # FETCH QUESTIONS
    # ==========================================
    api_questions = get_questions(quiz_id)

    final_questions = []

    for q in api_questions:

        choices = []
        correct_answers = []

        answers = q.get("answers", [])

        # ==========================================
        # NEW FORMAT
        # ==========================================
        for ans in answers:

            answer_id = ans.get("id")
            answer_text = ans.get("text")
            is_correct = ans.get("isCorrect", False)

            if not answer_text:
                continue

            choices.append({
                "text": answer_text,
                "value": answer_id
            })

            if is_correct:
                correct_answers.append(answer_id)

        final_questions.append({

            "id": q.get("id"),

            "skill": skill,

            "question": q.get("text", ""),

            "description": q.get("explanation", ""),

            "image": q.get("image"),

            "multiple": (
                    len(correct_answers) > 1
            ),

            "choices": choices,

            "correct_answers": correct_answers
        })

    return final_questions