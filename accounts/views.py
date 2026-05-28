from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .ai_engine.recommendation_service import recommend_posts
from .fetchSkills import get_common_skills
from .serializers import RegisterSerializer
from django.contrib.auth.views import LoginView
from .forms import LoginForm, RecruitmentPostForm , CandidatureForm
import os
import uuid
from django.contrib import messages
from accounts.models import User, RecruiterProfile, CandidateProfile, RecruitmentPost, Candidature
from accounts.ai_engine.cv_extractor import extract_cv_text
from accounts.ai_engine.cv_prediction_service import predict_candidature_situation
from datetime import datetime
from accounts.ai_engine.clustering_service import (
    load_clusters,
    cluster_candidates
)
from django.utils import timezone
from django.contrib.auth import logout
from django.shortcuts import get_object_or_404,render,redirect
from .ai_engine.salary_predictor import predict_salary
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from accounts.ai_engine.quiz_scraper import scrape_quiz



# accounts/quiz_mapper.py

QUIZ_LINKS = {

    "sql":
        "https://www.w3schools.com/sql/sql_quiz.asp",

    "python":
        "https://www.w3schools.com/python/python_quiz.asp",

    "java":
        "https://www.w3schools.com/java/java_quiz.asp",

    "javascript":
        "https://www.w3schools.com/js/js_quiz.asp",

    "html":
        "https://www.w3schools.com/html/html_quiz.asp",

    "css":
        "https://www.w3schools.com/css/css_quiz.asp"
}



@api_view(['POST'])
def register(request):
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        return Response({
            "message": "User created successfully",
            "username": user.username,
            "role": user.role
        })

    return Response(serializer.errors, status=400)
class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm

    def get_success_url(self):
        user = self.request.user

        if user.role == 'RH':
            return '/api/auth/recruiter/dashboard/'
        else:
            return '/api/auth/candidate/dashboard/'
# def logout_view(request):
#     logout(request)
#return redirect('login')

def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("login")

    return render(request, "accounts/logout_confirm.html")
@login_required
def candidate_dashboard(request):

    candidate = CandidateProfile.objects.get(user=request.user)

    # ==========================
    # PAGE NUMBER
    # ==========================
    page_number = request.GET.get("page", 1)

    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1

    page_size = 10
    candidatures = (
        Candidature.objects
        .filter(candidate=candidate)
        .select_related("post")
        .order_by("-date_of_post")
    )
    listIdPosts = set(
        candidatures.values_list('post_id', flat=True)
    )

    # ==========================
    # FULL RECOMMENDATION LIST
    # ==========================
    countingPosts = RecruitmentPost.objects.count()
    posts_qs = recommend_posts(candidate, top_k=countingPosts)

    # filter active posts FIRST
    posts_qs = [r for r in posts_qs if r["post"].is_active and r["post"].id not in listIdPosts]

    # ==========================
    # MANUAL PAGINATION (CORRECT)
    # ==========================
    start = (page_number - 1) * page_size
    end = page_number * page_size

    recommendations = posts_qs[start:end]

    has_next = end < len(posts_qs)
    next_page = page_number + 1 if has_next else None

    # ==========================
    # ADD skills_list
    # ==========================
    for item in recommendations:
        post = item["post"]
        post.skills_list = (
            [s.strip() for s in post.required_skills.split(",")]
            if post.required_skills else []
        )

    # ==========================
    # CANDIDATURES
    # ==========================

    interviews_count = 0
    for c in candidatures :
        if c.quiz_score > 0:
            interviews_count = interviews_count + 1
    print("interviews_count:", interviews_count)

    return render(request, "accounts/candidate_dashboard.html", {
        "countingPosts" : countingPosts,
        "recommendations": recommendations,
        "candidatures": candidatures,
        "interviews_count": interviews_count,
        "has_next": has_next,
        "next_page": next_page
    })

# def candidate_dashboard(request):
#
#     candidate = CandidateProfile.objects.get(
#         user=request.user
#     )
#
#     # ==========================================
#     # ONLY ACTIVE POSTS
#     # ==========================================
#     recommendations = [
#         r for r in recommend_posts(candidate)
#         if r["post"].is_active
#     ]
#
#     # ==========================================
#     # ADD skills_list TO EACH RECOMMENDATION
#     # ==========================================
#     for item in recommendations:
#
#         post = item["post"]
#
#         post.skills_list = []
#
#         if post.required_skills:
#
#             post.skills_list = [
#                 s.strip()
#                 for s in post.required_skills.split(",")
#             ]
#
#     # ==========================================
#     # POSTS USER APPLIED TO
#     # ==========================================
#     candidatures = (
#         Candidature.objects
#         .filter(candidate=candidate)
#         .select_related("post")
#         .order_by("-date_of_post")
#     )
#
#     context = {
#         "recommendations": recommendations,
#         "candidatures": candidatures
#     }
#
#     return render(
#         request,
#         "accounts/candidate_dashboard.html",
#         context
#     )
# @login_required
# def candidate_dashboard(request):
#
#     candidate = CandidateProfile.objects.get(
#         user=request.user
#     )
#
#     recommendations = recommend_posts(candidate)
#
#     context = {
#         "recommendations": recommendations
#     }
#
#     return render(
#         request,
#         "accounts/candidate_dashboard.html",
#         context
#     )

@login_required
def recruiter_dashboard_page(request):
    data = recruiter_dashboard(request)
    return render(request, "accounts/recruiter_dashboard.html", {
        "total_posts": data['total_posts'],
        "active_posts": data['active_posts'],
        "posts": data['posts']
    })


def signup(request):

    if request.method == "POST":

        # COMMON DATA
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("role")
        cin = request.POST.get("cin")
        real_name = request.POST.get("real_name")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            cin=cin,
            real_name=real_name
        )

        # RH
        if role == "RH":
            RecruiterProfile.objects.create(
                user=user,
                company_name=request.POST.get("company_name"),
                sector=request.POST.get("sector"),
                phone=request.POST.get("phone"),
                address=request.POST.get("address"),
                location=request.POST.get("location"),
                number_of_employees=request.POST.get("number_of_employees"),
                domains=request.POST.get("domains"),
                expertise=request.POST.get("expertise"),
                description=request.POST.get("description"),
            )

        # CANDIDATE
        else:
            CandidateProfile.objects.create(
                user=user,
                skills=request.POST.get("skills"),
                experience=request.POST.get("experience"),
                education=request.POST.get("education"),
                phone=request.POST.get("phone"),
                birth_date=request.POST.get("birth_date"),
                cv=request.FILES.get("cv"),
                motivation_letter=request.FILES.get("motivation_letter"),
                description=request.POST.get("description"),
            )

        return redirect("login")

    return render(request, "accounts/signup.html")

def recruiter_dashboard(request):

    profile = request.user.recruiterprofile

    posts = RecruitmentPost.objects.filter(
        recruiter=profile
    )

    applications = Candidature.objects.filter(
        post__in=posts
    )

    total_posts = posts.count()
    total_applications = applications.count()

    avg_per_post = (
        total_applications / total_posts
        if total_posts > 0
        else 0
    )

    applications_by_post = {}

    for app in applications:
        post_id = app.post_id

        applications_by_post[post_id] = (
                applications_by_post.get(post_id, 0) + 1
        )

    data = {
        "total_posts": total_posts,
        "active_posts": posts.filter(is_active=True).count(),

        # 🔥 NEW METRICS
        "total_applications": total_applications,
        "avg_per_post": round(avg_per_post, 2),

        "posts": [
            {
                "id": p.id,
                "title": p.title,
                "company": p.company_name,
                "domain": p.domain,
                "description": p.description[:120] if p.description else "",
                "skills": p.required_skills,
                "created_at": p.created_at,
                "is_active": p.is_active,
                "applications_count": applications_by_post.get(p.id, 0)
            }
            for p in posts.order_by("-created_at")
        ]
    }

    return data
@login_required
def recruiter_dashboard_page(request):

    if not hasattr(request.user, "recruiterprofile"):
        return JsonResponse({"error": "Not recruiter"}, status=403)

    data = recruiter_dashboard(request)

    return render(
        request,
        "accounts/recruiter_dashboard.html",
        data
    )

def create_recruitment_post(request):

    if request.method == 'POST':

        form = RecruitmentPostForm(request.POST)

        if form.is_valid():

            post = form.save(commit=False)

            # ----------------------
            # GET PROFILE (SOURCE OF TRUTH)
            # ----------------------
            profile = request.user.recruiterprofile

            post.recruiter = profile

            # company MUST come from profile only
            post.company_name = profile.company_name

            # ----------------------
            # DEFAULT VALUES
            # ----------------------
            post.is_active = True
            post.current_candidatures = 0

            # ----------------------
            # SKILLS
            # ----------------------
            selected_skills = request.POST.getlist('skills')
            post.required_skills = ",".join(selected_skills)

            post.save()

            return redirect('recruiter_dashboard_page')

    else:
        form = RecruitmentPostForm()

    COMMON_SKILLS = get_common_skills()

    return render(
        request,
        'accounts/create_post.html',
        {
            'form': form,
            'skills': COMMON_SKILLS
        }
    )



@login_required
def post_details(request, post_id):

    user = request.user

    post = get_object_or_404(
        RecruitmentPost,
        id=post_id
    )

    # ==========================================
    # USER TYPE
    # ==========================================
    is_recruiter = hasattr(user, "recruiterprofile")
    is_candidate = hasattr(user, "candidateprofile")

    # ==========================================
    # SECURITY
    # ==========================================
    if is_recruiter:

        if post.recruiter.user != user:
            return HttpResponseForbidden()

    elif not is_candidate:
        return HttpResponseForbidden()

    # ==========================================
    # SKILLS
    # ==========================================
    skills_list = []

    if post.required_skills:
        skills_list = [
            s.strip()
            for s in post.required_skills.split(",")
        ]

    # ==========================================
    # INTERVIEW STATUS
    # ==========================================
    interview_started = (
            post.entretien_technique_date_fin is not None
    )

    interview_open = False
    interview_closed = False

    if interview_started:

        if timezone.now() < post.entretien_technique_date_fin:
            interview_open = True
        else:
            interview_closed = True

    # ==========================================
    # CANDIDATURES
    # ==========================================
    candidatures = Candidature.objects.filter(
        post=post
    ).select_related(
        "candidate",
        "candidate__user"
    )

    finalRecrut = candidatures.filter(
        is_hired=True
    )
    # recruiter views
    recruiter_waiting_candidates = candidatures.order_by(
        "-date_of_post"
    )

    recruiter_ranked_candidates = candidatures.order_by(
        "-quiz_score"
    )

    # ==========================================
    # CANDIDATE STATE
    # ==========================================
    already_applied = False
    candidature = None
    situation = ""
    candidate_score = 0

    if is_candidate:

        candidature = candidatures.filter(
            candidate=user.candidateprofile
        ).first()

        already_applied = candidature is not None
        if candidature :
                situation = candidature.situation

        if candidature and candidature.quiz_score:
            candidate_score = candidature.quiz_score

    # ==========================================
    # CONDITIONS
    # ==========================================
    max_reached = (
            post.current_candidatures
            >= post.max_candidatures
    )

    can_apply = (
            is_candidate
            and not already_applied
            and not max_reached
            and not interview_started
    )

    can_take_quiz = (
            is_candidate
            and already_applied
            and interview_open
    )

    waiting_for_hiring = (
            is_candidate
            and already_applied
            and interview_closed
    )

    return render(
        request,
        "accounts/post_details.html",
        {
            "post": post,

            "skills_list": skills_list,

            "is_recruiter": is_recruiter,
            "is_candidate": is_candidate,

            "already_applied": already_applied,

            "interview_started": interview_started,
            "interview_open": interview_open,
            "interview_closed": interview_closed,
            "situation" : situation,

            "max_reached": max_reached,

            "can_apply": can_apply,
            "can_take_quiz": can_take_quiz,
            "waiting_for_hiring": waiting_for_hiring,

            "candidate_score": candidate_score,

            "recruiter_waiting_candidates": recruiter_waiting_candidates,
            "recruiter_ranked_candidates": recruiter_ranked_candidates,
            "finalRecrut": finalRecrut
        }
    )
@login_required
def apply_to_post(request, post_id):

    # =====================================
    # GET DATA
    # =====================================
    post = get_object_or_404(RecruitmentPost, id=post_id)

    candidate = get_object_or_404(
        CandidateProfile,
        user=request.user
    )

    # =====================================
    # CHECK MAX CANDIDATURES
    # =====================================
    if post.current_candidatures >= post.max_candidatures:
        messages.error(request, "Maximum candidatures reached.")
        return redirect("post_details", post_id=post.id)

    # =====================================
    # CHECK DUPLICATE
    # =====================================
    already_exists = Candidature.objects.filter(
        candidate=candidate,
        post=post
    ).exists()

    if already_exists:
        messages.warning(request, "You already applied.")
        return redirect("post_details", post_id=post.id)

    # =====================================
    # FORM HANDLING
    # =====================================
    if request.method == "POST":

        form = CandidatureForm(request.POST, request.FILES)

        if form.is_valid():

            candidature = form.save(commit=False)
            candidature.candidate = candidate
            candidature.post = post

            # =====================================
            # CV HANDLING
            # =====================================
            uploaded_cv = form.cleaned_data.get("custom_cv")

            temp_dir = "media/temp"
            os.makedirs(temp_dir, exist_ok=True)

            if uploaded_cv:

                filename = f"{uuid.uuid4()}_{uploaded_cv.name}"
                temp_path = os.path.join(temp_dir, filename)

                with open(temp_path, "wb+") as destination:
                    for chunk in uploaded_cv.chunks():
                        destination.write(chunk)

                cv_text = extract_cv_text(temp_path)

                candidature.cv_file = uploaded_cv.name

            else:

                cv_text = extract_cv_text(candidate.cv.path)
                candidature.cv_file = candidate.cv.name

            # save extracted cv
            candidature.extracted_cv_content = cv_text

            # =====================================
            # BUILD ML INPUT
            # =====================================
            prediction_text = f"""
            {candidate.skills}
            {candidate.experience}
            {candidate.education}
            {candidate.description}
            {post.title}
            {post.domain}
            {post.description}
            {post.required_skills}
            {cv_text}
            """

            # =====================================
            # AI PREDICTION
            # =====================================
            prediction = predict_candidature_situation(prediction_text)

            candidature.situation = prediction
            candidature.save()

            # =====================================
            # IF ACCEPTED
            # =====================================
            if prediction == "accepted":

                post.current_candidatures += 1
                post.save()

                messages.success(
                    request,
                    "Candidature accepted successfully."
                )

            else:

                messages.error(
                    request,
                    "Candidature rejected by AI."
                )

            return redirect("candidate_dashboard")

    else:

        form = CandidatureForm(
            initial={
                "motivation_letter": candidate.description
            }
        )

    return render(
        request,
        "accounts/apply_to_post.html",
        {
            "form": form,
            "post": post,
            "candidate": candidate
        }
    )
@login_required
def interview_panel(request, post_id):

    print("starting the panel :>")

    post = get_object_or_404(
        RecruitmentPost,
        id=post_id
    )

    # =========================================
    # ONLY RECRUITER
    # =========================================
    if not hasattr(request.user, "recruiterprofile"):
        return HttpResponseForbidden()

    candidatures = Candidature.objects.filter(
        post=post
    )

    # =========================================
    # LOAD SAVED CLUSTERS
    # =========================================
    clusters = load_clusters(post.id)

    # =========================================
    # START INTERVIEW
    # =========================================
    if request.method == "POST":

        date_fin = request.POST.get("date_fin")

        if date_fin:

            post.entretien_technique_date_fin = (
                datetime.fromisoformat(date_fin)
            )

            post.save()

            # GENERATE CLUSTERS
            clusters = cluster_candidates(
                candidatures,
                post.id
            )

            # RELOAD SAVED FILE
            clusters = load_clusters(post.id)

    # =========================================
    # AUTO GENERATE IF EMPTY
    # =========================================
    if (
            post.entretien_technique_date_fin
            and (
            not clusters["senior"]
            and not clusters["intermediate"]
            and not clusters["junior"]
    )
    ):

        cluster_candidates(
            candidatures,
            post.id
        )

        clusters = load_clusters(post.id)

    # =========================================
    # FETCH REAL CANDIDATURE OBJECTS
    # =========================================
    senior_candidates = Candidature.objects.filter(
        id__in=clusters["senior"]
    )

    intermediate_candidates = Candidature.objects.filter(
        id__in=clusters["intermediate"]
    )

    junior_candidates = Candidature.objects.filter(
        id__in=clusters["junior"]
    )

    print("checking:", clusters)

    return render(
        request,
        "accounts/interview_panel.html",
        {
            "post": post,

            "senior_candidates":
                senior_candidates,

            "intermediate_candidates":
                intermediate_candidates,

            "junior_candidates":
                junior_candidates
        }
    )

@login_required
def take_quiz(request, post_id, skill):

    quiz_url = QUIZ_LINKS.get(skill.lower())

    return render(
        request,
        "accounts/take_quiz.html",
        {
            "quiz_url": quiz_url,
            "skill": skill
        }
    )
@login_required
def start_quiz(request, post_id):

    post = get_object_or_404(
        RecruitmentPost,
        id=post_id
    )

    if not hasattr(request.user, "candidateprofile"):
        return HttpResponseForbidden()

    candidature = get_object_or_404(
        Candidature,
        candidate=request.user.candidateprofile,
        post=post
    )

    # ==========================
    # GET SKILLS
    # ==========================
    skills = [
        s.strip().lower()
        for s in (post.required_skills or "").split(",")
        if s.strip()
    ]

    # ==========================
    # FETCH QUESTIONS
    # ==========================
    all_questions = []

    for skill in skills:
        all_questions.extend(scrape_quiz(skill))

    # limit questions
    # all_questions = all_questions[:5]

    # ==========================
    # SUBMIT QUIZ
    # ==========================
    if request.method == "POST":

        correct = 0

        for q in all_questions:

            # ==========================
            # MULTIPLE ANSWERS
            # ==========================
            if q.get("multiple"):

                selected = request.POST.getlist(str(q["id"]))

                if set(selected) == set(q["correct_answers"]):
                    correct += 1

            # ==========================
            # SINGLE ANSWER
            # ==========================
            else:

                selected = request.POST.get(str(q["id"]))

                if selected in q["correct_answers"]:
                    correct += 1

        # ==========================
        # SCORE
        # ==========================
        score = 0

        if all_questions:
            score = round(
                (correct / len(all_questions)) * 100,
                2
            )

        print("YOUR candidature.quiz_score =", candidature.quiz_score)
        print("YOUR SCORE =", score)
        if(candidature.quiz_score > 0 and score > candidature.quiz_score) :
            candidature.quiz_score = score
            candidature.save()

        return redirect(
            "post_details",
            post_id=post.id
        )

    return render(
        request,
        "accounts/start_quiz.html",
        {
            "post": post,
            "questions": all_questions
        }
    )
@login_required
def hire_candidate_view(request, post_id):

    post = get_object_or_404(
        RecruitmentPost,
        id=post_id
    )

    # ==========================================
    # SECURITY
    # ==========================================
    if not hasattr(request.user, "recruiterprofile"):
        return HttpResponseForbidden()

    if post.recruiter.user != request.user:
        return HttpResponseForbidden()

    # ==========================================
    # CANDIDATES ORDERED BY SCORE
    # ==========================================
    candidatures = Candidature.objects.filter(
        post=post
    ).select_related(
        "candidate",
        "candidate__user"
    ).order_by("-quiz_score")

    selected_id = request.GET.get("candidate")
    clusters = load_clusters(post.id)

    selected_candidate = None

    predicted_salary = None
    salary_min = None
    salary_max = None

    # ==========================================
    # SELECTED CANDIDATE
    # ==========================================
    if selected_id:

        selected_candidate = get_object_or_404(
            Candidature,
            id=selected_id,
            post=post
        )

        predicted_salary = predict_salary(
            selected_candidate
        )

        salary_min = round(predicted_salary, 2)

        salary_max = round(predicted_salary + 200, 2)

    # ==========================================
    # FINAL HIRING
    # ==========================================
    if request.method == "POST":

        candidate_id = request.POST.get("candidate_id")

        salary = request.POST.get("salary")

        hired_candidate = get_object_or_404(
            Candidature,
            id=candidate_id,
            post=post
        )

        # reject all others
        Candidature.objects.filter(
            post=post
        ).update(
            is_hired=False,
            situation="rejected"
        )

        # hire selected
        hired_candidate.is_hired = True
        hired_candidate.proposed_salary = salary
        hired_candidate.situation = "accepted"
        hired_candidate.save()

        # close post
        post.is_active = False
        post.save()

        return redirect(
            "post_details",
            post_id=post.id
        )

    return render(
        request,
        "accounts/hire_candidate.html",
        {
            "post": post,
            "candidatures": candidatures,
            "clusterssenior" : clusters["senior"],
            "clustersintermediate" : clusters["intermediate"],
            "clustersjunior" : clusters["junior"],

            "selected_candidate": selected_candidate,

            "predicted_salary": predicted_salary,

            "salary_min": salary_min,
            "salary_max": salary_max,
        }
    )
# @login_required
# def start_quiz(request, post_id):
#     print(request)
#
#     post = get_object_or_404(RecruitmentPost, id=post_id)
#
#     if not hasattr(request.user, "candidateprofile"):
#         return HttpResponseForbidden()
#
#     candidature = get_object_or_404(
#         Candidature,
#         candidate=request.user.candidateprofile,
#         post=post
#     )
#
#     skills = [
#         s.strip().lower()
#         for s in (post.required_skills or "").split(",")
#         if s.strip()
#     ]
#
#     all_questions = []
#
#     for skill in skills:
#         all_questions.extend(scrape_quiz(skill))
#
#     # ==========================
#     # SUBMIT QUIZ
#     # ==========================
#     if request.method == "POST":
#
#         correct = 0
#
#         for q in all_questions:
#             print("checking question:", q)
#
#             selected = request.POST.get(str(q["id"]))  # IMPORTANT FIX
#
#             if selected and selected in q["correct_answers"]:
#                 correct += 1
#
#         score = 0
#         if all_questions:
#             score = (correct / len(all_questions)) * 100
#
#         print("Your Score is",score)
#         # candidature.quiz_score = score
#         # candidature.save()
#
#         return redirect("post_details", post_id=post.id)
#
#     return render(request, "accounts/start_quiz.html", {
#         "post": post,
#         "questions": all_questions[:5]
#     })