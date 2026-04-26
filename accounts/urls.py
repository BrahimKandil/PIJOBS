from django.urls import path
from .views import CustomLoginView, register, logout_view, candidate_dashboard, signup, \
    recruiter_dashboard_page

urlpatterns = [
    path('register/', register),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('signup/', signup, name='signup'),
    path("recruiter/dashboard/", recruiter_dashboard_page),
    path('candidate/dashboard/', candidate_dashboard, name='candidate_dashboard'),
]