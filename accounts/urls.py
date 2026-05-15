from django.urls import path
from .views import (
    CustomLoginView, register, logout_view,
    candidate_dashboard, signup, recruiter_dashboard_page,
    apply_to_post, my_applications,
    recruiter_applications, recruiter_accept, recruiter_reject,
    recruiter_reanalyze,
)

urlpatterns = [
    path('register/', register),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('signup/', signup, name='signup'),

    path('recruiter/dashboard/', recruiter_dashboard_page, name='recruiter_dashboard'),
    path('candidate/dashboard/', candidate_dashboard, name='candidate_dashboard'),

    path('posts/<int:post_id>/apply/', apply_to_post, name='apply_to_post'),
    path('my-applications/', my_applications, name='my_applications'),

    path('recruiter/post/<int:post_id>/applications/',
         recruiter_applications, name='recruiter_applications'),
    path('recruiter/candidature/<int:candidature_id>/accept/',
         recruiter_accept, name='recruiter_accept'),
    path('recruiter/candidature/<int:candidature_id>/reject/',
         recruiter_reject, name='recruiter_reject'),
    path('recruiter/candidature/<int:candidature_id>/reanalyze/',
         recruiter_reanalyze, name='recruiter_reanalyze'),
]