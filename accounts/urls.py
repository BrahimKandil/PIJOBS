from django.urls import path
from .views import CustomLoginView, register, logout_view, candidate_dashboard, signup, \
    recruiter_dashboard_page, create_recruitment_post, post_details, apply_to_post, interview_panel,start_quiz,hire_candidate_view

urlpatterns = [
    path('register/', register),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('signup/', signup, name='signup'),
    path("recruiter/dashboard/", recruiter_dashboard_page, name='recruiter_dashboard_page' ),
    path('candidate/dashboard/', candidate_dashboard, name='candidate_dashboard'),
    path(
        "apply/<int:post_id>/",
        apply_to_post,
        name="apply_to_post"
    ),
    path(
        "post/<int:post_id>/hire/",
        hire_candidate_view,
        name="hire_candidate_view"
    ),
    path("post/<int:post_id>/interview/", interview_panel, name="interview_panel"),
    path('create-post/',create_recruitment_post,name='create_post'),
    path('post/<int:post_id>/',post_details,name='post_details'),
    path(
        "post/<int:post_id>/quiz/",
        start_quiz,
        name="start_quiz"
    ),
]