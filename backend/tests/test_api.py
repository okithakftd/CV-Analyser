"""Integration tests for the FastAPI application."""
from fastapi.testclient import TestClient

from api_main import app

client = TestClient(app)

LONG_RESUME = (
    "I am a Python developer with 5 years of experience. "
    "I have worked extensively with FastAPI, PostgreSQL, and Docker. "
    "I have deployed applications on AWS using EC2 and S3."
)
LONG_JOB = (
    "We are looking for a Python developer with strong FastAPI skills. "
    "Experience with Docker and PostgreSQL is required. "
    "Knowledge of AWS is a plus."
)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_returns_200(self):
        assert client.get("/health").status_code == 200

    def test_returns_ok_true(self):
        assert client.get("/health").json() == {"ok": True}


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------


class TestRootEndpoint:
    def test_returns_200(self):
        assert client.get("/").status_code == 200

    def test_has_ok_field(self):
        assert client.get("/").json()["ok"] is True

    def test_lists_analyze_endpoint(self):
        assert "/analyze" in client.get("/").json()["endpoints"]

    def test_lists_docs_endpoint(self):
        assert "/docs" in client.get("/").json()["endpoints"]


# ---------------------------------------------------------------------------
# POST /analyze — happy path
# ---------------------------------------------------------------------------


class TestAnalyzeEndpointSuccess:
    def test_returns_200(self):
        resp = client.post(
            "/analyze",
            json={"resume_text": LONG_RESUME, "job_text": LONG_JOB, "target_role": "backend"},
        )
        assert resp.status_code == 200

    def test_response_has_matched_field(self):
        resp = client.post(
            "/analyze",
            json={"resume_text": LONG_RESUME, "job_text": LONG_JOB, "target_role": "backend"},
        )
        assert "matched" in resp.json()

    def test_response_has_missing_field(self):
        resp = client.post(
            "/analyze",
            json={"resume_text": LONG_RESUME, "job_text": LONG_JOB, "target_role": "backend"},
        )
        assert "missing" in resp.json()

    def test_response_has_summary_field(self):
        resp = client.post(
            "/analyze",
            json={"resume_text": LONG_RESUME, "job_text": LONG_JOB, "target_role": "backend"},
        )
        assert "summary" in resp.json()

    def test_summary_target_role_echoed(self):
        resp = client.post(
            "/analyze",
            json={"resume_text": LONG_RESUME, "job_text": LONG_JOB, "target_role": "backend"},
        )
        assert resp.json()["summary"]["target_role"] == "backend"

    def test_summary_counts_are_integers(self):
        data = client.post(
            "/analyze",
            json={"resume_text": LONG_RESUME, "job_text": LONG_JOB, "target_role": "backend"},
        ).json()
        assert isinstance(data["summary"]["matched_count"], int)
        assert isinstance(data["summary"]["missing_count"], int)

    def test_fullstack_role_accepted(self):
        resp = client.post(
            "/analyze",
            json={
                "resume_text": "Full stack developer with React TypeScript Node.js and PostgreSQL experience building web applications",
                "job_text": "Seeking fullstack developer with React TypeScript Node.js REST API and database knowledge for our product team",
                "target_role": "fullstack",
            },
        )
        assert resp.status_code == 200

    def test_cloud_devops_role_accepted(self):
        resp = client.post(
            "/analyze",
            json={
                "resume_text": "Cloud engineer with AWS EC2 S3 Docker Kubernetes and Terraform working on infrastructure automation",
                "job_text": "Looking for DevOps engineer with AWS Docker Kubernetes Terraform and CI/CD pipeline automation experience",
                "target_role": "cloud_devops",
            },
        )
        assert resp.status_code == 200

    def test_missing_skills_have_priority(self):
        data = client.post(
            "/analyze",
            json={"resume_text": LONG_RESUME, "job_text": LONG_JOB, "target_role": "backend"},
        ).json()
        for skill in data["missing"]:
            assert skill["priority"] in ("High", "Medium", "Low")

    def test_matched_skills_have_confidence(self):
        data = client.post(
            "/analyze",
            json={"resume_text": LONG_RESUME, "job_text": LONG_JOB, "target_role": "backend"},
        ).json()
        for skill in data["matched"]:
            assert isinstance(skill["confidence"], float)


# ---------------------------------------------------------------------------
# POST /analyze — validation errors (422)
# ---------------------------------------------------------------------------


class TestAnalyzeEndpointValidation:
    def test_invalid_role_returns_422(self):
        resp = client.post(
            "/analyze",
            json={"resume_text": LONG_RESUME, "job_text": LONG_JOB, "target_role": "invalid_role"},
        )
        assert resp.status_code == 422

    def test_short_resume_returns_422(self):
        resp = client.post(
            "/analyze",
            json={"resume_text": "short", "job_text": LONG_JOB, "target_role": "backend"},
        )
        assert resp.status_code == 422

    def test_short_job_description_returns_422(self):
        resp = client.post(
            "/analyze",
            json={"resume_text": LONG_RESUME, "job_text": "short", "target_role": "backend"},
        )
        assert resp.status_code == 422

    def test_missing_target_role_returns_422(self):
        resp = client.post(
            "/analyze",
            json={"resume_text": LONG_RESUME, "job_text": LONG_JOB},
        )
        assert resp.status_code == 422

    def test_missing_resume_text_returns_422(self):
        resp = client.post(
            "/analyze",
            json={"job_text": LONG_JOB, "target_role": "backend"},
        )
        assert resp.status_code == 422

    def test_empty_body_returns_422(self):
        assert client.post("/analyze", json={}).status_code == 422
