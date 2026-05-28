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
        RecruiterProfile,
        on_delete=models.CASCADE,
        related_name="posts"
    )

    title = models.CharField(max_length=255, null=True, blank=True)

    domain = models.CharField(max_length=255, null=True, blank=True)

    description = models.TextField(null=True, blank=True)

    company_name = models.CharField(max_length=255, null=True, blank=True)

    required_skills = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)
    # Maximum allowed candidatures
    max_candidatures = models.PositiveIntegerField(default=10)

    # Current number of candidatures
    current_candidatures = models.PositiveIntegerField(default=0)

    # Technical interview end date
    entretien_technique_date_fin = models.DateTimeField(
        null=True,
        blank=True
    )
class Candidature(models.Model):

    SITUATION_CHOICES = (
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    )

    candidate = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name="candidatures"
    )

    post = models.ForeignKey(
        RecruitmentPost,
        on_delete=models.CASCADE,
        related_name="candidatures"
    )

    date_of_post = models.DateTimeField(auto_now_add=True)

    situation = models.CharField(
        max_length=20,
        choices=SITUATION_CHOICES,
        default="accepted"
    )

    imported = models.BooleanField(default=False)

    cv_file = models.TextField()

    extracted_cv_content = models.TextField(
        null=True,
        blank=True
    )

    motivation_letter = models.TextField(
        null=True,
        blank=True
    )
    quiz_score = models.FloatField(
        default=0
    )
    is_hired = models.BooleanField(
        default=False
    )

    proposed_salary = models.FloatField(
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ("candidate", "post")

    def __str__(self):
        return f"{self.candidate.user.username} -> {self.post.title}"