from django.contrib import admin
from .models import (
    User, RecruiterProfile, CandidateProfile,
    RecruitmentPost, Candidature, RejectedCandidature,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "real_name", "cin")
    search_fields = ("username", "email", "real_name", "cin")
    list_filter = ("role",)


@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "sector", "phone")
    search_fields = ("company_name", "sector")


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "birth_date")
    search_fields = ("user__username", "user__email")


@admin.register(RecruitmentPost)
class RecruitmentPostAdmin(admin.ModelAdmin):
    list_display = ("title", "company_name", "domain", "recruiter",
                    "is_active", "created_at")
    list_filter = ("is_active", "domain")
    search_fields = ("title", "company_name", "required_skills")


@admin.register(Candidature)
class CandidatureAdmin(admin.ModelAdmin):
    list_display = ("id", "candidate", "post", "situation",
                    "imported", "date_of_post")
    list_filter = ("situation", "imported")
    search_fields = ("candidate__user__username", "post__title",
                     "full_name", "email")
    readonly_fields = ("date_of_post",)


@admin.register(RejectedCandidature)
class RejectedCandidatureAdmin(admin.ModelAdmin):
    list_display = ("ref", "candidate", "post", "rejected_at")
    search_fields = ("candidate__user__username", "post__title",
                     "full_name", "email", "ref")
    readonly_fields = ("ref", "rejected_at", "date_of_post")
