import json

from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import RegisterSerializer
from .models import User, RecruiterProfile, CandidateProfile, RecruitmentPost

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from .forms import LoginForm


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
            return '/api/auth//candidate/dashboard/'


def logout_view(request):
    logout(request)
    return redirect('login')


def recruiter_dashboard(request):
    user = request.user

    posts = RecruitmentPost.objects.filter(recruiter=user)

    data = {
        "total_posts": posts.count(),
        "active_posts": posts.filter(is_active=True).count(),
        "posts": [
            {
                "id": p.id,
                "title": p.title,
                "company": p.company_name,
                "domain": p.domain,
                "description": p.description[:120],
                "skills": p.required_skills,
                "created_at": p.created_at,
                "is_active": p.is_active
            }
            for p in posts.order_by("-created_at")
        ]
    }

    return data

@login_required
def candidate_dashboard(request):
    return render(request, 'accounts/candidate_dashboard.html')

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