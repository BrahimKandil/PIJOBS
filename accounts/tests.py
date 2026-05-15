from datetime import date
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import (
    User, RecruiterProfile, CandidateProfile,
    RecruitmentPost, Candidature, RejectedCandidature,
)
from accounts.forms import CandidatureForm


def make_pdf(name="cv.pdf", size_kb=10, content=None):
    payload = content if content is not None else (b"%PDF-1.4\n" + b"0" * (size_kb * 1024))
    return SimpleUploadedFile(name, payload, content_type="application/pdf")


class BaseSetup(TestCase):
    def setUp(self):
        self.rh = User.objects.create_user(
            username="rh1",
            password="pwd12345",
            role="RH",
            cin="111",
            real_name="RH One",
            email="rh@x.com",
        )
        RecruiterProfile.objects.create(
            user=self.rh,
            company_name="Acme",
            sector="IT",
            phone="000",
            address="addr",
        )

        self.cand_user = User.objects.create_user(
            username="cand1",
            password="pwd12345",
            role="CANDIDATE",
            cin="222",
            real_name="Cand One",
            email="cand@x.com",
        )
        self.cp = CandidateProfile.objects.create(
            user=self.cand_user,
            skills="python django sql",
            experience="2y",
            education="ing",
            phone="111",
            birth_date=date(2000, 1, 1),
        )

        self.post = RecruitmentPost.objects.create(
            recruiter=self.rh,
            title="Dev Python",
            domain="IT",
            description="Backend developer with Django and APIs",
            company_name="Acme",
            required_skills="python django sql rest api",
            is_active=True,
        )
        self.client = Client()


# ============================================================
# 1) Modèle RejectedCandidature
# ============================================================
class RejectedCandidatureModelTests(BaseSetup):

    def test_no_autofield_pk_is_hash(self):
        rc = RejectedCandidature.objects.create(
            candidate=self.cp,
            post=self.post,
            cv_file=SimpleUploadedFile("cv.pdf", b"x"),
            full_name="x",
            email="x@x.com",
            phone="0",
        )
        self.assertNotIsInstance(rc.pk, int)
        self.assertEqual(len(rc.pk), 40)

    def test_two_rejects_same_candidate_post_blocked(self):
        RejectedCandidature.objects.create(
            candidate=self.cp,
            post=self.post,
            cv_file=SimpleUploadedFile("cv.pdf", b"x"),
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            RejectedCandidature.objects.create(
                candidate=self.cp,
                post=self.post,
                cv_file=SimpleUploadedFile("cv.pdf", b"x"),
            )

    def test_different_posts_get_different_refs(self):
        post2 = RecruitmentPost.objects.create(
            recruiter=self.rh,
            title="QA",
            domain="IT",
            company_name="Acme",
            required_skills="qa",
            is_active=True,
        )
        r1 = RejectedCandidature.objects.create(
            candidate=self.cp,
            post=self.post,
            cv_file=SimpleUploadedFile("a.pdf", b"x"),
        )
        r2 = RejectedCandidature.objects.create(
            candidate=self.cp,
            post=post2,
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
        big = SimpleUploadedFile("cv.pdf", b"0" * (6 * 1024 * 1024))
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
        self.assertEqual(r.status_code, 302)

    def test_candidate_can_get_form(self):
        self.client.login(username="cand1", password="pwd12345")
        r = self.client.get(reverse("apply_to_post", args=[self.post.id]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.post.title)

    @patch("accounts.views.compute_match_score")
    def test_candidate_can_submit(self, mock_ai):
        from accounts.ai_service import AIScoringResult
        mock_ai.return_value = AIScoringResult(
            score=72.5,
            recommendation="recommend_accept",
            source="trained_model",
            extracted_text="python django sql",
        )

        self.client.login(username="cand1", password="pwd12345")
        url = reverse("apply_to_post", args=[self.post.id])
        r = self.client.post(url, {
            "full_name": "John",
            "email": "j@j.com",
            "phone": "1",
            "years_of_experience": 1,
            "cover_message": "hi",
            "cv_file": make_pdf(),
        }, follow=True)

        self.assertEqual(r.status_code, 200)
        self.assertEqual(Candidature.objects.count(), 1)
        c = Candidature.objects.first()
        self.assertEqual(c.candidate, self.cp)
        self.assertEqual(c.post, self.post)
        self.assertEqual(c.situation, "pending")
        self.assertEqual(c.ai_score, 72.5)
        self.assertEqual(c.ai_recommendation, "recommend_accept")

    def test_double_apply_blocked(self):
        Candidature.objects.create(
            candidate=self.cp,
            post=self.post,
            cv_file=SimpleUploadedFile("a.pdf", b"x"),
        )
        self.client.login(username="cand1", password="pwd12345")
        r = self.client.get(reverse("apply_to_post", args=[self.post.id]))
        self.assertEqual(r.status_code, 302)

    def test_rh_cannot_apply(self):
        self.client.login(username="rh1", password="pwd12345")
        r = self.client.get(reverse("apply_to_post", args=[self.post.id]))
        self.assertEqual(r.status_code, 302)


# ============================================================
# 4) Décision recruteur
# ============================================================
class RecruiterDecisionTests(BaseSetup):

    def setUp(self):
        super().setUp()
        self.cand = Candidature.objects.create(
            candidate=self.cp,
            post=self.post,
            cv_file=SimpleUploadedFile("cv.pdf", b"x"),
            full_name="John",
            email="j@j.com",
            phone="1",
            years_of_experience=2,
            cover_message="hi",
            ai_score=55.0,
            ai_recommendation="borderline",
            ai_source="tfidf_fallback",
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
        self.assertEqual(r.status_code, 302)

    def test_accept_keeps_candidature(self):
        self.client.login(username="rh1", password="pwd12345")
        r = self.client.post(reverse("recruiter_accept", args=[self.cand.id]), follow=True)
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
        self.assertEqual(Candidature.objects.count(), 0)
        self.assertEqual(RejectedCandidature.objects.count(), 1)
        rc = RejectedCandidature.objects.first()
        self.assertEqual(rc.rejection_reason, "not enough exp")
        self.assertEqual(rc.ai_score, 55.0)
        self.assertEqual(rc.ai_recommendation, "borderline")
        self.assertFalse(str(rc.pk).isdigit())

    def test_reject_other_recruiters_post_forbidden(self):
        rh2 = User.objects.create_user(
            username="rh2",
            password="pwd12345",
            role="RH",
            cin="333",
            real_name="RH Two",
        )
        self.client.login(username="rh2", password="pwd12345")
        r = self.client.post(
            reverse("recruiter_reject", args=[self.cand.id]),
            {"reason": "x"},
        )
        self.assertEqual(r.status_code, 404)


# ============================================================
# 5) my_applications
# ============================================================
class MyApplicationsTests(BaseSetup):

    def test_aggregates_accepted_and_rejected(self):
        Candidature.objects.create(
            candidate=self.cp,
            post=self.post,
            cv_file=SimpleUploadedFile("cv.pdf", b"x"),
            full_name="J",
            email="j@j.com",
            phone="1",
            situation="accepted",
            ai_score=70.0,
            ai_recommendation="recommend_accept",
        )
        post2 = RecruitmentPost.objects.create(
            recruiter=self.rh,
            title="QA",
            company_name="Acme",
            domain="IT",
            required_skills="qa",
            is_active=True,
        )
        RejectedCandidature.objects.create(
            candidate=self.cp,
            post=post2,
            cv_file=SimpleUploadedFile("a.pdf", b"x"),
            rejection_reason="bof",
            ai_score=12.0,
            ai_recommendation="recommend_reject",
            auto_rejected=True,
        )
        self.client.login(username="cand1", password="pwd12345")
        r = self.client.get(reverse("my_applications"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["accepted"]), 1)
        self.assertEqual(len(r.context["rejected"]), 1)


# ============================================================
# 6) IA - score, suggestion, auto reject
# ============================================================
class AIFeatureTests(BaseSetup):

    @patch("accounts.views.compute_match_score")
    def test_candidate_submit_triggers_ai(self, mock_ai):
        from accounts.ai_service import AIScoringResult
        mock_ai.return_value = AIScoringResult(
            score=81.0,
            recommendation="recommend_accept",
            source="trained_model",
            extracted_text="python django api sql",
        )

        self.client.login(username="cand1", password="pwd12345")
        response = self.client.post(
            reverse("apply_to_post", args=[self.post.id]),
            {
                "full_name": "Cand One",
                "email": "cand@x.com",
                "phone": "111",
                "years_of_experience": 2,
                "cover_message": "I am interested",
                "cv_file": make_pdf(),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        c = Candidature.objects.get()
        self.assertEqual(c.ai_score, 81.0)
        self.assertEqual(c.ai_recommendation, "recommend_accept")
        self.assertEqual(c.ai_source, "trained_model")
        self.assertEqual(c.extracted_cv_content, "python django api sql")
        self.assertIsNotNone(c.ai_last_analysis_at)

    @patch("accounts.views.compute_match_score")
    def test_auto_reject_when_score_below_threshold(self, mock_ai):
        from accounts.ai_service import AIScoringResult
        mock_ai.return_value = AIScoringResult(
            score=10.0,
            recommendation="recommend_reject",
            source="tfidf_fallback",
            extracted_text="marketing design communication",
        )

        self.client.login(username="cand1", password="pwd12345")
        response = self.client.post(
            reverse("apply_to_post", args=[self.post.id]),
            {
                "full_name": "Cand One",
                "email": "cand@x.com",
                "phone": "111",
                "years_of_experience": 1,
                "cover_message": "hello",
                "cv_file": make_pdf(),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Candidature.objects.count(), 0)
        self.assertEqual(RejectedCandidature.objects.count(), 1)

        rc = RejectedCandidature.objects.first()
        self.assertTrue(rc.auto_rejected)
        self.assertEqual(rc.ai_score, 10.0)
        self.assertEqual(rc.ai_recommendation, "recommend_reject")
        self.assertEqual(rc.ai_source, "tfidf_fallback")

    @patch("accounts.views.compute_match_score")
    def test_no_auto_reject_when_score_above_threshold(self, mock_ai):
        from accounts.ai_service import AIScoringResult
        mock_ai.return_value = AIScoringResult(
            score=40.0,
            recommendation="borderline",
            source="tfidf_fallback",
            extracted_text="python junior",
        )

        self.client.login(username="cand1", password="pwd12345")
        response = self.client.post(
            reverse("apply_to_post", args=[self.post.id]),
            {
                "full_name": "Cand One",
                "email": "cand@x.com",
                "phone": "111",
                "years_of_experience": 1,
                "cover_message": "hello",
                "cv_file": make_pdf(),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Candidature.objects.count(), 1)
        self.assertEqual(RejectedCandidature.objects.count(), 0)

    def test_suggested_data_persist_on_manual_reject(self):
        cand = Candidature.objects.create(
            candidate=self.cp,
            post=self.post,
            cv_file=SimpleUploadedFile("cv.pdf", b"x"),
            full_name="John",
            email="john@x.com",
            phone="1",
            ai_score=23.0,
            ai_recommendation="recommend_reject",
            ai_source="trained_model",
        )
        self.client.login(username="rh1", password="pwd12345")
        response = self.client.post(
            reverse("recruiter_reject", args=[cand.id]),
            {"reason": "manual review"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        rc = RejectedCandidature.objects.get()
        self.assertEqual(rc.ai_score, 23.0)
        self.assertEqual(rc.ai_recommendation, "recommend_reject")
        self.assertFalse(rc.auto_rejected)

    @patch("accounts.views.compute_match_score")
    def test_recruiter_reanalyze_updates_ai_fields(self, mock_ai):
        from accounts.ai_service import AIScoringResult
        cand = Candidature.objects.create(
            candidate=self.cp,
            post=self.post,
            cv_file=SimpleUploadedFile("cv.pdf", b"x"),
            full_name="John",
            email="john@x.com",
            phone="1",
            ai_score=20.0,
            ai_recommendation="recommend_reject",
            ai_source="old",
        )

        mock_ai.return_value = AIScoringResult(
            score=78.0,
            recommendation="recommend_accept",
            source="trained_model",
            extracted_text="python django rest",
        )

        self.client.login(username="rh1", password="pwd12345")
        response = self.client.post(
            reverse("recruiter_reanalyze", args=[cand.id]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        cand.refresh_from_db()
        self.assertEqual(cand.ai_score, 78.0)
        self.assertEqual(cand.ai_recommendation, "recommend_accept")
        self.assertEqual(cand.ai_source, "trained_model")
        self.assertEqual(cand.extracted_cv_content, "python django rest")

    @patch("accounts.views.compute_match_score")
    def test_recruiter_reanalyze_can_auto_reject(self, mock_ai):
        from accounts.ai_service import AIScoringResult
        cand = Candidature.objects.create(
            candidate=self.cp,
            post=self.post,
            cv_file=SimpleUploadedFile("cv.pdf", b"x"),
            full_name="John",
            email="john@x.com",
            phone="1",
        )

        mock_ai.return_value = AIScoringResult(
            score=5.0,
            recommendation="recommend_reject",
            source="trained_model",
            extracted_text="unrelated profile",
        )

        self.client.login(username="rh1", password="pwd12345")
        response = self.client.post(
            reverse("recruiter_reanalyze", args=[cand.id]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Candidature.objects.count(), 0)
        self.assertEqual(RejectedCandidature.objects.count(), 1)
        rc = RejectedCandidature.objects.first()
        self.assertTrue(rc.auto_rejected)

    def test_recruiter_apps_sorted_by_ai_score(self):
        c1 = Candidature.objects.create(
            candidate=self.cp,
            post=self.post,
            cv_file=SimpleUploadedFile("1.pdf", b"x"),
            full_name="A",
            ai_score=25.0,
            ai_recommendation="recommend_reject",
        )

        cand_user2 = User.objects.create_user(
            username="cand2",
            password="pwd12345",
            role="CANDIDATE",
            cin="444",
            real_name="Cand Two",
            email="cand2@x.com",
        )
        cp2 = CandidateProfile.objects.create(user=cand_user2, phone="222")

        c2 = Candidature.objects.create(
            candidate=cp2,
            post=self.post,
            cv_file=SimpleUploadedFile("2.pdf", b"x"),
            full_name="B",
            ai_score=88.0,
            ai_recommendation="recommend_accept",
        )

        self.client.login(username="rh1", password="pwd12345")
        response = self.client.get(reverse("recruiter_applications", args=[self.post.id]))
        self.assertEqual(response.status_code, 200)

        pending = response.context["pending"]
        self.assertEqual(pending[0].id, c2.id)
        self.assertEqual(pending[1].id, c1.id)