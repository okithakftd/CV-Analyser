"""Unit tests for skill_matcher.py — no FastAPI, no file I/O."""
import pytest
from skill_matcher import SkillMatcher, normalize_text, priority, suggested_path

SAMPLE_SKILLS = [
    {
        "id": "python",
        "canonical_name": "Python",
        "aliases": ["python", "python3"],
        "category": "Programming Languages",
        "roles": ["backend", "fullstack"],
        "level": "core",
    },
    {
        "id": "docker",
        "canonical_name": "Docker",
        "aliases": ["docker", "docker-compose"],
        "category": "DevOps Fundamentals",
        "roles": ["backend", "fullstack", "cloud_devops"],
        "level": "core",
    },
    {
        "id": "aws_ec2",
        "canonical_name": "AWS EC2",
        "aliases": ["ec2", "aws ec2"],
        "category": "Cloud (AWS)",
        "roles": ["cloud_devops"],
        "level": "supplementary",
    },
    {
        "id": "postgres",
        "canonical_name": "PostgreSQL",
        "aliases": ["postgresql", "postgres"],
        "category": "Databases",
        "roles": ["backend", "fullstack"],
        "level": "supplementary",
    },
]


@pytest.fixture
def matcher() -> SkillMatcher:
    return SkillMatcher(SAMPLE_SKILLS)


# ---------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------


class TestNormalizeText:
    def test_lowercases_input(self):
        assert normalize_text("Python") == "python"

    def test_removes_special_chars(self):
        result = normalize_text("React & Vue!")
        assert "&" not in result
        assert "!" not in result

    def test_collapses_whitespace(self):
        assert normalize_text("  hello   world  ") == "hello world"

    def test_preserves_plus_sign(self):
        assert "+" in normalize_text("C++")

    def test_preserves_hash_sign(self):
        assert "#" in normalize_text("C#")

    def test_empty_string(self):
        assert normalize_text("") == ""


# ---------------------------------------------------------------------------
# priority
# ---------------------------------------------------------------------------


class TestPriority:
    def test_high_at_threshold(self):
        assert priority(0.78) == "High"

    def test_high_above_threshold(self):
        assert priority(1.0) == "High"

    def test_medium_at_threshold(self):
        assert priority(0.55) == "Medium"

    def test_medium_between_thresholds(self):
        assert priority(0.65) == "Medium"

    def test_low_below_medium_threshold(self):
        assert priority(0.54) == "Low"

    def test_low_at_zero(self):
        assert priority(0.0) == "Low"


# ---------------------------------------------------------------------------
# suggested_path
# ---------------------------------------------------------------------------


class TestSuggestedPath:
    def test_known_category_returns_steps(self):
        path = suggested_path("Cloud (AWS)")
        assert len(path) > 0
        assert all(isinstance(s, str) for s in path)

    def test_devops_path_contains_containers(self):
        assert "Containers" in suggested_path("DevOps Fundamentals")

    def test_databases_path_contains_indexes(self):
        assert "Indexes" in suggested_path("Databases")

    def test_unknown_category_returns_default(self):
        path = suggested_path("Something Unknown")
        assert len(path) == 3

    def test_auth_path_contains_owasp(self):
        assert "OWASP checks" in suggested_path("Auth & Security")


# ---------------------------------------------------------------------------
# SkillMatcher.extract_skills
# ---------------------------------------------------------------------------


class TestExtractSkills:
    def test_finds_skill_by_alias(self, matcher: SkillMatcher):
        found = matcher.extract_skills("I know python3 well", "backend")
        assert "python" in found

    def test_ignores_skills_not_in_role(self, matcher: SkillMatcher):
        # aws_ec2 is cloud_devops only
        found = matcher.extract_skills("We run on EC2 with aws ec2 all day", "backend")
        assert "aws_ec2" not in found

    def test_returns_found_as_list(self, matcher: SkillMatcher):
        found = matcher.extract_skills("I use python", "backend")
        assert isinstance(found["python"].found_as, list)
        assert len(found["python"].found_as) > 0

    def test_confidence_within_bounds(self, matcher: SkillMatcher):
        found = matcher.extract_skills("I use python", "backend")
        assert 0.0 <= found["python"].confidence <= 1.0

    def test_confidence_grows_with_more_hits(self, matcher: SkillMatcher):
        one_hit = matcher.extract_skills("python", "backend")
        two_hits = matcher.extract_skills("python and python3", "backend")
        assert two_hits["python"].confidence >= one_hit["python"].confidence

    def test_empty_text_returns_nothing(self, matcher: SkillMatcher):
        assert matcher.extract_skills("", "backend") == {}

    def test_cloud_devops_role_finds_ec2(self, matcher: SkillMatcher):
        found = matcher.extract_skills("We run on EC2", "cloud_devops")
        assert "aws_ec2" in found

    def test_multiple_skills_found(self, matcher: SkillMatcher):
        found = matcher.extract_skills("I use python and docker every day", "backend")
        assert "python" in found
        assert "docker" in found


# ---------------------------------------------------------------------------
# SkillMatcher.importance_score
# ---------------------------------------------------------------------------


class TestImportanceScore:
    def test_score_between_zero_and_one(self, matcher: SkillMatcher):
        score = matcher.importance_score("Python developer needed.", "python")
        assert 0.0 <= score <= 1.0

    def test_required_keyword_boosts_score(self, matcher: SkillMatcher):
        with_required = matcher.importance_score(
            "Python required for this position.", "python"
        )
        without_required = matcher.importance_score(
            "Python would be nice to have.", "python"
        )
        assert with_required > without_required

    def test_must_keyword_boosts_score(self, matcher: SkillMatcher):
        score = matcher.importance_score("Must know Python for this job.", "python")
        assert score > 0.25

    def test_core_skill_gets_level_boost(self, matcher: SkillMatcher):
        # python is "core"; aws_ec2 is "supplementary" — same occurrence count, different base
        core_score = matcher.importance_score("python needed", "python")
        supp_score = matcher.importance_score("ec2 needed", "aws_ec2")
        assert core_score >= supp_score

    def test_higher_frequency_raises_score(self, matcher: SkillMatcher):
        low_freq = matcher.importance_score("We use Python.", "python")
        high_freq = matcher.importance_score(
            "Python python python is core to our stack.", "python"
        )
        assert high_freq >= low_freq


# ---------------------------------------------------------------------------
# SkillMatcher.analyze
# ---------------------------------------------------------------------------


class TestAnalyze:
    def test_matched_skills_in_both_texts(self, matcher: SkillMatcher):
        result = matcher.analyze(
            "I use python and docker daily",
            "Looking for python developer with docker experience",
            "backend",
        )
        matched_ids = {s["skill_id"] for s in result["matched"]}
        assert "python" in matched_ids
        assert "docker" in matched_ids

    def test_missing_skill_identified(self, matcher: SkillMatcher):
        result = matcher.analyze(
            "I know python",
            "Need python and docker skills",
            "backend",
        )
        missing_ids = {s["skill_id"] for s in result["missing"]}
        assert "docker" in missing_ids
        assert "python" not in missing_ids

    def test_summary_counts_match_lists(self, matcher: SkillMatcher):
        result = matcher.analyze(
            "I use python",
            "Need python and docker",
            "backend",
        )
        assert result["summary"]["matched_count"] == len(result["matched"])
        assert result["summary"]["missing_count"] == len(result["missing"])

    def test_summary_contains_target_role(self, matcher: SkillMatcher):
        result = matcher.analyze("python developer", "python expert needed", "fullstack")
        assert result["summary"]["target_role"] == "fullstack"

    def test_missing_skills_have_valid_priority(self, matcher: SkillMatcher):
        result = matcher.analyze("", "docker required python needed", "backend")
        for s in result["missing"]:
            assert s["priority"] in ("High", "Medium", "Low")

    def test_missing_sorted_descending_by_importance(self, matcher: SkillMatcher):
        result = matcher.analyze("", "docker required. python nice to have.", "backend")
        importances = [s["importance"] for s in result["missing"]]
        assert importances == sorted(importances, reverse=True)

    def test_missing_skills_have_suggested_path(self, matcher: SkillMatcher):
        result = matcher.analyze("python coder", "python and docker required", "backend")
        for s in result["missing"]:
            assert isinstance(s["suggested_path"], list)
            assert len(s["suggested_path"]) > 0

    def test_no_overlap_between_matched_and_missing(self, matcher: SkillMatcher):
        result = matcher.analyze(
            "python docker postgres",
            "python docker postgres aws",
            "backend",
        )
        matched_ids = {s["skill_id"] for s in result["matched"]}
        missing_ids = {s["skill_id"] for s in result["missing"]}
        assert matched_ids.isdisjoint(missing_ids)
