from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import hashlib
import uuid


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
    location = models.CharField(max_length=255, blank=True, default="")
    number_of_employees = models.IntegerField(default=0)
    domains = models.TextField(blank=True, default="")
    expertise = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")


class CandidateProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    skills = models.TextField(blank=True, default="")
    experience = models.TextField(blank=True, default="")
    education = models.TextField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    birth_date = models.DateField(null=True, blank=True)
    cv = models.FileField(upload_to='cvs/', null=True, blank=True)
    motivation_letter = models.FileField(upload_to='motivation_letters/', null=True, blank=True)
    description = models.TextField(blank=True, default="")


class RecruitmentPost(models.Model):
    recruiter = models.ForeignKey(
        User, on_delete=models.CASCADE,
        null=True, blank=True, related_name="posts"
    )
    title = models.CharField(max_length=255, null=True, blank=True)
    domain = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    company_name = models.CharField(max_length=255, null=True, blank=True)
    required_skills = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)


# ============================================================
# CANDIDATURE (acceptée / en attente) — alimente le DWH
# ============================================================
class Candidature(models.Model):
    SITUATION_CHOICES = (
        ("pending",  "Pending"),
        ("accepted", "Accepted"),
    )

    candidate = models.ForeignKey(
        CandidateProfile, on_delete=models.CASCADE,
        related_name="candidatures"
    )
    post = models.ForeignKey(
        RecruitmentPost, on_delete=models.CASCADE,
        related_name="candidatures"
    )
    date_of_post = models.DateTimeField(auto_now_add=True)
    situation = models.CharField(
        max_length=20, choices=SITUATION_CHOICES, default="pending"
    )
    imported = models.BooleanField(default=False)

    # Fichiers candidature
    cv_file = models.FileField(upload_to='candidatures/cvs/')
    motivation_letter_file = models.FileField(
        upload_to='candidatures/letters/', null=True, blank=True
    )
    extracted_cv_content = models.TextField(null=True, blank=True)
    motivation_letter = models.TextField(null=True, blank=True)

    # Champs du formulaire
    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    cover_message = models.TextField(blank=True)
    years_of_experience = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("candidate", "post")
        ordering = ["-date_of_post"]

    def __str__(self):
        return f"{self.candidate.user.username} -> {self.post.title}"


# ============================================================
# CANDIDATURE REFUSEE
#   - Aucune AutoField : PK = hash SHA1 (déterministe + uuid)
#   - Donnée jamais exportée vers le Data Warehouse
# ============================================================
class RejectedCandidature(models.Model):
    """
    Pas d'id auto-incrémenté : la PK est un hash.
    Conséquence : les refus n'occupent pas de place dans la séquence d'IDs
    de Candidature et ne polluent pas le Data Warehouse.
    """
    ref = models.CharField(
        max_length=64, primary_key=True, editable=False
    )
    candidate = models.ForeignKey(
        CandidateProfile, on_delete=models.CASCADE,
        related_name="rejected_candidatures"
    )
    post = models.ForeignKey(
        RecruitmentPost, on_delete=models.CASCADE,
        related_name="rejected_candidatures"
    )
    date_of_post = models.DateTimeField(default=timezone.now, editable=False)

    # Snapshot du formulaire
    cv_file = models.FileField(upload_to='candidatures_rejected/cvs/')
    motivation_letter_file = models.FileField(
        upload_to='candidatures_rejected/letters/', null=True, blank=True
    )
    extracted_cv_content = models.TextField(null=True, blank=True)
    motivation_letter = models.TextField(null=True, blank=True)

    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    cover_message = models.TextField(blank=True)
    years_of_experience = models.PositiveIntegerField(null=True, blank=True)

    rejection_reason = models.TextField(blank=True)
    rejected_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        # Empêche les doublons; mais on autorise candidat à se représenter
        # sur d'autres offres.
        unique_together = ("candidate", "post")
        ordering = ["-rejected_at"]

    def save(self, *args, **kwargs):
        if not self.ref:
            now = self.rejected_at or timezone.now()
            self.rejected_at = now
            raw = f"{self.candidate_id}-{self.post_id}-{now.isoformat()}-{uuid.uuid4()}"
            self.ref = hashlib.sha1(raw.encode()).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[REJECTED:{self.ref[:8]}] {self.candidate.user.username} -> {self.post.title}"
