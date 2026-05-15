from django.contrib import admin
from .models import (
    User,
    RecruiterProfile,
    CandidateProfile,
    RecruitmentPost,
    Candidature,
    RejectedCandidature,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "cin", "real_name", "is_staff")
    search_fields = ("username", "email", "real_name", "cin")
    list_filter = ("role", "is_staff", "is_superuser")


@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "sector", "phone")
    search_fields = ("user__username", "company_name", "sector")


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "birth_date")
    search_fields = ("user__username", "user__real_name", "skills", "education")


@admin.register(RecruitmentPost)
class RecruitmentPostAdmin(admin.ModelAdmin):
    list_display = ("title", "company_name", "domain", "recruiter", "is_active", "created_at")
    search_fields = ("title", "company_name", "domain", "required_skills")
    list_filter = ("is_active", "domain", "created_at")


@admin.register(Candidature)
class CandidatureAdmin(admin.ModelAdmin):
    list_display = (
        "id", "full_name", "post", "situation",
        "ai_score", "ai_recommendation", "ai_source", "date_of_post"
    )
    search_fields = ("full_name", "email", "post__title", "candidate__user__username")
    list_filter = ("situation", "ai_recommendation", "ai_source", "date_of_post")


@admin.register(RejectedCandidature)
class RejectedCandidatureAdmin(admin.ModelAdmin):
    list_display = (
        "ref", "full_name", "post", "auto_rejected",
        "ai_score", "ai_recommendation", "rejected_at"
    )
    search_fields = ("ref", "full_name", "email", "post__title", "candidate__user__username")
    list_filter = ("auto_rejected", "ai_recommendation", "rejected_at")