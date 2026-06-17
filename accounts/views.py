from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import RegisterSerializer
from .forms import LoginForm, CandidatureForm, RejectionForm
from .models import (
    User, RecruiterProfile, CandidateProfile, RecruitmentPost,
    Candidature, RejectedCandidature,
)
from .ai_service import (
    compute_match_score,
    rank_candidatures,
    should_auto_reject,
)


@api_view(['POST'])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            "message": "User created successfully",
            "username": user.username,
            "role": user.role,
        })
    return Response(serializer.errors, status=400)


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm

    def get_success_url(self):
        user = self.request.user
        if user.role == 'RH':
            return '/api/auth/recruiter/dashboard/'
        return '/api/auth/candidate/dashboard/'


def logout_view(request):
    logout(request)
    return redirect('login')


def recruiter_dashboard(request):
    user = request.user
    posts = RecruitmentPost.objects.filter(recruiter=user)
    return {
        "total_posts": posts.count(),
        "active_posts": posts.filter(is_active=True).count(),
        "posts": [
            {
                "id": p.id,
                "title": p.title,
                "company": p.company_name,
                "domain": p.domain,
                "description": (p.description or "")[:120],
                "skills": p.required_skills,
                "created_at": p.created_at,
                "is_active": p.is_active,
            }
            for p in posts.order_by("-created_at")
        ],
    }


@login_required
def candidate_dashboard(request):
    posts = RecruitmentPost.objects.filter(is_active=True).order_by("-created_at")
    return render(request, 'accounts/candidate_dashboard.html', {"posts": posts})


@login_required
def recruiter_dashboard_page(request):
    data = recruiter_dashboard(request)
    return render(request, "accounts/recruiter_dashboard.html", data)


def signup(request):
    if request.method == "POST":
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
            real_name=real_name,
        )

        if role == "RH":
            RecruiterProfile.objects.create(
                user=user,
                company_name=request.POST.get("company_name", ""),
                sector=request.POST.get("sector", ""),
                phone=request.POST.get("phone", ""),
                address=request.POST.get("address", ""),
                location=request.POST.get("location", ""),
                number_of_employees=request.POST.get("number_of_employees") or 0,
                domains=request.POST.get("domains", ""),
                expertise=request.POST.get("expertise", ""),
                description=request.POST.get("description", ""),
            )
        else:
            CandidateProfile.objects.create(
                user=user,
                skills=request.POST.get("skills", ""),
                experience=request.POST.get("experience", ""),
                education=request.POST.get("education", ""),
                phone=request.POST.get("phone", ""),
                birth_date=request.POST.get("birth_date") or None,
                cv=request.FILES.get("cv"),
                motivation_letter=request.FILES.get("motivation_letter"),
                description=request.POST.get("description", ""),
            )
        return redirect("login")

    return render(request, "accounts/signup.html")


def _ensure_recruiter(view):
    from functools import wraps

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if getattr(request.user, "role", None) != "RH":
            messages.error(request, "Accès refusé.")
            return redirect("login")
        return view(request, *args, **kwargs)
    return wrapper


def _auto_reject_candidature(cand, reason="Auto-refus IA : score trop faible"):
    with transaction.atomic():
        RejectedCandidature.objects.create(
            candidate=cand.candidate,
            post=cand.post,
            cv_file=cand.cv_file,
            motivation_letter_file=cand.motivation_letter_file,
            extracted_cv_content=cand.extracted_cv_content,
            motivation_letter=cand.motivation_letter,
            full_name=cand.full_name,
            email=cand.email,
            phone=cand.phone,
            cover_message=cand.cover_message,
            years_of_experience=cand.years_of_experience,
            ai_score=cand.ai_score,
            ai_recommendation=cand.ai_recommendation,
            ai_source=cand.ai_source,
            ai_last_analysis_at=cand.ai_last_analysis_at,
            auto_rejected=True,
            rejection_reason=reason,
        )
        cand.delete()


@login_required
def apply_to_post(request, post_id):
    post = get_object_or_404(RecruitmentPost, id=post_id, is_active=True)

    if getattr(request.user, "role", None) != "CANDIDATE":
        messages.error(request, "Seul un candidat peut postuler.")
        return redirect("login")

    try:
        candidate_profile = request.user.candidateprofile
    except CandidateProfile.DoesNotExist:
        messages.error(request, "Vous devez compléter votre profil candidat.")
        return redirect("candidate_dashboard")

    already = (
        Candidature.objects.filter(candidate=candidate_profile, post=post).exists()
        or RejectedCandidature.objects.filter(candidate=candidate_profile, post=post).exists()
    )
    if already:
        messages.warning(request, "Vous avez déjà postulé à cette offre.")
        return redirect("my_applications")

    if request.method == "POST":
        form = CandidatureForm(request.POST, request.FILES)
        if form.is_valid():
            candidature = form.save(commit=False)
            candidature.candidate = candidate_profile
            candidature.post = post
            candidature.situation = "pending"

            try:
                candidature.save()
            except IntegrityError:
                messages.error(request, "Candidature déjà existante.")
                return redirect("my_applications")

            ai_result = compute_match_score(post, candidature.cv_file)
            candidature.extracted_cv_content = ai_result.extracted_text
            candidature.ai_score = ai_result.score
            candidature.ai_recommendation = ai_result.recommendation
            candidature.ai_source = ai_result.source
            candidature.ai_last_analysis_at = timezone.now()
            candidature.save(update_fields=[
                "extracted_cv_content",
                "ai_score",
                "ai_recommendation",
                "ai_source",
                "ai_last_analysis_at",
            ])

            if should_auto_reject(ai_result.score):
                _auto_reject_candidature(candidature)
                messages.warning(request, "Candidature analysée puis refusée automatiquement par l'IA.")
                return redirect("my_applications")

            messages.success(request, "Candidature envoyée avec succès et analysée par l'IA.")
            return redirect("my_applications")
    else:
        form = CandidatureForm(initial={
            "full_name": getattr(request.user, "real_name", "") or request.user.get_full_name(),
            "email": request.user.email,
            "phone": getattr(candidate_profile, "phone", ""),
        })

    return render(request, "accounts/candidature_form.html", {
        "form": form,
        "post": post,
    })


@login_required
def my_applications(request):
    try:
        cp = request.user.candidateprofile
    except CandidateProfile.DoesNotExist:
        return redirect("candidate_dashboard")

    accepted = Candidature.objects.filter(candidate=cp).select_related("post")
    rejected = RejectedCandidature.objects.filter(candidate=cp).select_related("post")

    return render(request, "accounts/my_applications.html", {
        "accepted": accepted,
        "rejected": rejected,
    })


@_ensure_recruiter
def recruiter_applications(request, post_id):
    post = get_object_or_404(
        RecruitmentPost, id=post_id, recruiter=request.user
    )
    pending_qs = Candidature.objects.filter(post=post).select_related("candidate__user")
    pending = rank_candidatures(list(pending_qs))

    rejected = (
        RejectedCandidature.objects.filter(post=post)
        .select_related("candidate__user")
        .order_by("-rejected_at")
    )

    return render(request, "accounts/recruiter_applications.html", {
        "post": post,
        "pending": pending,
        "rejected": rejected,
        "rejection_form": RejectionForm(),
    })


@_ensure_recruiter
@require_POST
def recruiter_accept(request, candidature_id):
    cand = get_object_or_404(
        Candidature, id=candidature_id, post__recruiter=request.user
    )
    cand.situation = "accepted"
    cand.save(update_fields=["situation"])
    messages.success(request, "Candidature acceptée.")
    return redirect("recruiter_applications", post_id=cand.post_id)


@_ensure_recruiter
@require_POST
def recruiter_reject(request, candidature_id):
    cand = get_object_or_404(
        Candidature, id=candidature_id, post__recruiter=request.user
    )
    form = RejectionForm(request.POST)
    reason = form.data.get("reason", "") if form.is_valid() else ""
    post_id = cand.post_id

    with transaction.atomic():
        RejectedCandidature.objects.create(
            candidate=cand.candidate,
            post=cand.post,
            cv_file=cand.cv_file,
            motivation_letter_file=cand.motivation_letter_file,
            extracted_cv_content=cand.extracted_cv_content,
            motivation_letter=cand.motivation_letter,
            full_name=cand.full_name,
            email=cand.email,
            phone=cand.phone,
            cover_message=cand.cover_message,
            years_of_experience=cand.years_of_experience,
            ai_score=cand.ai_score,
            ai_recommendation=cand.ai_recommendation,
            ai_source=cand.ai_source,
            ai_last_analysis_at=cand.ai_last_analysis_at,
            rejection_reason=reason,
        )
        cand.delete()

    messages.info(request, "Candidature refusée et archivée.")
    return redirect("recruiter_applications", post_id=post_id)


@_ensure_recruiter
@require_POST
def recruiter_reanalyze(request, candidature_id):
    cand = get_object_or_404(
        Candidature, id=candidature_id, post__recruiter=request.user
    )

    ai_result = compute_match_score(cand.post, cand.cv_file)
    cand.extracted_cv_content = ai_result.extracted_text
    cand.ai_score = ai_result.score
    cand.ai_recommendation = ai_result.recommendation
    cand.ai_source = ai_result.source
    cand.ai_last_analysis_at = timezone.now()
    cand.save(update_fields=[
        "extracted_cv_content",
        "ai_score",
        "ai_recommendation",
        "ai_source",
        "ai_last_analysis_at",
    ])

    if should_auto_reject(ai_result.score):
        post_id = cand.post_id
        _auto_reject_candidature(cand, reason="Auto-refus IA après réanalyse")
        messages.warning(request, "La candidature a été re-analysée puis refusée automatiquement.")
        return redirect("recruiter_applications", post_id=post_id)

    messages.success(request, "Analyse IA relancée avec succès.")
    return redirect("recruiter_applications", post_id=cand.post_id)