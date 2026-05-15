"""
Tests unitaires pour la fonctionnalité Candidature + Refus.
Couverture :
  - Modèle RejectedCandidature : pas d'AutoField, PK = hash unique
  - Form CandidatureForm : validation taille / extension
  - Vue apply_to_post : authentification, double candidature, succès
  - Vue recruiter_accept / recruiter_reject :
      * accept POST only
      * reject POST only
      * reject => crée RejectedCandidature et supprime Candidature
      * Permission RH uniquement
  - my_applications : agrège accepted + rejected
"""

import io
from datetime import date

from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import (
    User, RecruiterProfile, CandidateProfile,
    RecruitmentPost, Candidature, RejectedCandidature,
)
from accounts.forms import CandidatureForm


def make_pdf(name="cv.pdf", size_kb=10):
    return SimpleUploadedFile(name, b"%PDF-1.4\n" + b"0" * (size_kb * 1024),
                              content_type="application/pdf")


class BaseSetup(TestCase):
    def setUp(self):
        # Recruteur
        self.rh = User.objects.create_user(
            username="rh1", password="pwd12345",
            role="RH", cin="111", real_name="RH One", email="rh@x.com",
        )
        RecruiterProfile.objects.create(
            user=self.rh, company_name="Acme", sector="IT",
            phone="000", address="addr",
        )
        # Candidat
        self.cand_user = User.objects.create_user(
            username="cand1", password="pwd12345",
            role="CANDIDATE", cin="222", real_name="Cand One",
            email="cand@x.com",
        )
        self.cp = CandidateProfile.objects.create(
            user=self.cand_user, skills="python", experience="2y",
            education="ing", phone="111", birth_date=date(2000, 1, 1),
        )
        # Offre
        self.post = RecruitmentPost.objects.create(
            recruiter=self.rh, title="Dev Python", domain="IT",
            description="...", company_name="Acme",
            required_skills="python", is_active=True,
        )
        self.client = Client()


# ============================================================
# 1) Modèle RejectedCandidature
# ============================================================
class RejectedCandidatureModelTests(BaseSetup):

    def test_no_autofield_pk_is_hash(self):
        rc = RejectedCandidature.objects.create(
            candidate=self.cp, post=self.post,
            cv_file=SimpleUploadedFile("cv.pdf", b"x"),
            full_name="x", email="x@x.com", phone="0",
        )
        # PK n'est PAS un entier
        self.assertNotIsInstance(rc.pk, int)
        self.assertEqual(len(rc.pk), 40)  # SHA1 = 40 chars hex

    def test_two_rejects_same_candidate_post_blocked(self):
        RejectedCandidature.objects.create(
            candidate=self.cp, post=self.post,
            cv_file=SimpleUploadedFile("cv.pdf", b"x"),
        )
        # unique_together(candidate, post)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            RejectedCandidature.objects.create(
                candidate=self.cp, post=self.post,
                cv_file=SimpleUploadedFile("cv.pdf", b"x"),
            )

    def test_different_posts_get_different_refs(self):
        post2 = RecruitmentPost.objects.create(
            recruiter=self.rh, title="QA", domain="IT",
            company_name="Acme", required_skills="qa", is_active=True,
        )
        r1 = RejectedCandidature.objects.create(
            candidate=self.cp, post=self.post,
            cv_file=SimpleUploadedFile("a.pdf", b"x"),
        )
        r2 = RejectedCandidature.objects.create(
            candidate=self.cp, post=post2,
            cv_file=SimpleUploadedFile("b.pdf", b"x"),
        )
        self.assertNotEqual(r1.ref, r2.ref)


# ============================================================
# 2) CandidatureForm
# ============================================================
class CandidatureFormTests(TestCase):

    def _data(self):
        return {
            "full_name": "John Doe",
            "email": "john@x.com",
            "phone": "+216123",
            "years_of_experience": 3,
            "cover_message": "hello",
        }

    def test_valid_pdf(self):
        form = CandidatureForm(
            data=self._data(),
            files={"cv_file": make_pdf()},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_bad_extension_rejected(self):
        bad = SimpleUploadedFile("cv.exe", b"MZ\x90", content_type="application/x-msdownload")
        form = CandidatureForm(data=self._data(), files={"cv_file": bad})
        self.assertFalse(form.is_valid())
        self.assertIn("cv_file", form.errors)

    def test_too_big_rejected(self):
        big = SimpleUploadedFile("cv.pdf", b"0" * (6 * 1024 * 1024))  # 6 Mo
        form = CandidatureForm(data=self._data(), files={"cv_file": big})
        self.assertFalse(form.is_valid())
        self.assertIn("cv_file", form.errors)


# ============================================================
# 3) Vue apply_to_post
# ============================================================
class ApplyViewTests(BaseSetup):

    def test_login_required(self):
        url = reverse("apply_to_post", args=[self.post.id])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 302)  # redirect login

    def test_candidate_can_get_form(self):
        self.client.login(username="cand1", password="pwd12345")
        r = self.client.get(reverse("apply_to_post", args=[self.post.id]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.post.title)

    def test_candidate_can_submit(self):
        self.client.login(username="cand1", password="pwd12345")
        url = reverse("apply_to_post", args=[self.post.id])
        r = self.client.post(url, {
            "full_name": "John", "email": "j@j.com", "phone": "1",
            "years_of_experience": 1, "cover_message": "hi",
            "cv_file": make_pdf(),
        }, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Candidature.objects.count(), 1)
        c = Candidature.objects.first()
        self.assertEqual(c.candidate, self.cp)
        self.assertEqual(c.post, self.post)
        self.assertEqual(c.situation, "pending")

    def test_double_apply_blocked(self):
        Candidature.objects.create(
            candidate=self.cp, post=self.post,
            cv_file=SimpleUploadedFile("a.pdf", b"x"),
        )
        self.client.login(username="cand1", password="pwd12345")
        r = self.client.get(reverse("apply_to_post", args=[self.post.id]))
        # redirige vers my_applications avec warning
        self.assertEqual(r.status_code, 302)

    def test_rh_cannot_apply(self):
        self.client.login(username="rh1", password="pwd12345")
        r = self.client.get(reverse("apply_to_post", args=[self.post.id]))
        self.assertEqual(r.status_code, 302)


# ============================================================
# 4) Décision recruteur (accept / reject)
# ============================================================
class RecruiterDecisionTests(BaseSetup):

    def setUp(self):
        super().setUp()
        self.cand = Candidature.objects.create(
            candidate=self.cp, post=self.post,
            cv_file=SimpleUploadedFile("cv.pdf", b"x"),
            full_name="John", email="j@j.com", phone="1",
            years_of_experience=2, cover_message="hi",
        )

    def test_accept_requires_post(self):
        self.client.login(username="rh1", password="pwd12345")
        r = self.client.get(reverse("recruiter_accept", args=[self.cand.id]))
        self.assertEqual(r.status_code, 405)

    def test_reject_requires_post(self):
        self.client.login(username="rh1", password="pwd12345")
        r = self.client.get(reverse("recruiter_reject", args=[self.cand.id]))
        self.assertEqual(r.status_code, 405)

    def test_only_rh_can_decide(self):
        self.client.login(username="cand1", password="pwd12345")
        r = self.client.post(reverse("recruiter_accept", args=[self.cand.id]))
        # Pas RH -> redirect
        self.assertEqual(r.status_code, 302)

    def test_accept_keeps_candidature(self):
        self.client.login(username="rh1", password="pwd12345")
        r = self.client.post(reverse("recruiter_accept", args=[self.cand.id]),
                             follow=True)
        self.assertEqual(r.status_code, 200)
        self.cand.refresh_from_db()
        self.assertEqual(self.cand.situation, "accepted")
        self.assertEqual(Candidature.objects.count(), 1)
        self.assertEqual(RejectedCandidature.objects.count(), 0)

    def test_reject_moves_to_rejected_table(self):
        self.client.login(username="rh1", password="pwd12345")
        url = reverse("recruiter_reject", args=[self.cand.id])
        r = self.client.post(url, {"reason": "not enough exp"}, follow=True)
        self.assertEqual(r.status_code, 200)
        # La candidature est SUPPRIMÉE (donc id non consommé)
        self.assertEqual(Candidature.objects.count(), 0)
        self.assertEqual(RejectedCandidature.objects.count(), 1)
        rc = RejectedCandidature.objects.first()
        self.assertEqual(rc.rejection_reason, "not enough exp")
        # PK n'est PAS un entier
        self.assertFalse(str(rc.pk).isdigit())

    def test_reject_other_recruiters_post_forbidden(self):
        # crée un 2e RH
        rh2 = User.objects.create_user(
            username="rh2", password="pwd12345",
            role="RH", cin="333", real_name="RH Two",
        )
        self.client.login(username="rh2", password="pwd12345")
        r = self.client.post(
            reverse("recruiter_reject", args=[self.cand.id]),
            {"reason": "x"},
        )
        self.assertEqual(r.status_code, 404)


# ============================================================
# 5) my_applications agrège les deux tables
# ============================================================
class MyApplicationsTests(BaseSetup):

    def test_aggregates_accepted_and_rejected(self):
        Candidature.objects.create(
            candidate=self.cp, post=self.post,
            cv_file=SimpleUploadedFile("cv.pdf", b"x"),
            full_name="J", email="j@j.com", phone="1",
            situation="accepted",
        )
        post2 = RecruitmentPost.objects.create(
            recruiter=self.rh, title="QA", company_name="Acme",
            domain="IT", required_skills="qa", is_active=True,
        )
        RejectedCandidature.objects.create(
            candidate=self.cp, post=post2,
            cv_file=SimpleUploadedFile("a.pdf", b"x"),
            rejection_reason="bof",
        )
        self.client.login(username="cand1", password="pwd12345")
        r = self.client.get(reverse("my_applications"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["accepted"]), 1)
        self.assertEqual(len(r.context["rejected"]), 1)
