from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    ROLE_CHOICES = (
        ('RH', 'Recruiter'),
        ('CANDIDATE', 'Candidate'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    cin = models.CharField(max_length=20)
    real_name = models.CharField(max_length=255)
class RecruiterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    company_name = models.CharField(max_length=255)
    sector = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    location = models.CharField(max_length=255)
    number_of_employees = models.IntegerField()
    domains = models.TextField()
    expertise = models.TextField()
    description = models.TextField()


class CandidateProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    skills = models.TextField()
    experience = models.TextField()
    education = models.TextField()
    phone = models.CharField(max_length=20)
    birth_date = models.DateField()

    cv = models.FileField(upload_to='cvs/')
    motivation_letter = models.FileField(upload_to='motivation_letters/')

    description = models.TextField()



class RecruitmentPost(models.Model):
    recruiter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="posts"
    )

    title = models.CharField(max_length=255, null=True, blank=True)

    domain = models.CharField(max_length=255, null=True, blank=True)

    description = models.TextField(null=True, blank=True)

    company_name = models.CharField(max_length=255, null=True, blank=True)

    required_skills = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)