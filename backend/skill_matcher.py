from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class SkillFound:
    skill_id: str
    found_as: List[str]
    confidence: float


ROADMAP_TEMPLATES: Dict[str, List[str]] = {
    "Cloud (AWS)": [
        "Cloud basics",
        "IAM permissions",
        "Networking basics (VPC)",
        "Deploy a small API",
        "Monitoring + cost basics",
    ],
    "Cloud (Azure)": [
        "Cloud basics",
        "Identity (Entra ID)",
        "Networking basics (VNet)",
        "Deploy a Function/App",
        "Monitoring + cost basics",
    ],
    "DevOps Fundamentals": [
        "Git workflow",
        "Containers",
        "CI pipeline",
        "CD pipeline",
        "Observability basics",
    ],
    "Auth & Security": [
        "Threat basics",
        "OAuth/JWT",
        "Secure storage",
        "OWASP checks",
        "Audit logging",
    ],
    "Databases": [
        "Schema design",
        "Indexes",
        "Transactions",
        "Query tuning",
        "Backup/restore basics",
    ],
    "APIs & Integration": [
        "REST design",
        "Validation",
        "Auth",
        "Docs (OpenAPI)",
        "Performance + caching",
    ],
    "Frontend Concepts": [
        "Core fundamentals",
        "Component patterns",
        "State management",
        "Testing",
        "Performance + a11y",
    ],
    "Architecture & Patterns": [
        "Baseline design",
        "Reliability patterns",
        "Scaling",
        "Tradeoffs",
        "Hands-on refactor",
    ],
}

_REQUIRED_WORDS = [
    "required",
    "must",
    "essential",
    "mandatory",
    "need to",
    "strongly preferred",
]


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9+\-#/\.\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def priority(imp: float) -> str:
    if imp >= 0.78:
        return "High"
    if imp >= 0.55:
        return "Medium"
    return "Low"


def suggested_path(category: str) -> List[str]:
    return ROADMAP_TEMPLATES.get(
        category,
        ["Learn fundamentals", "Build a small project using it", "Add a portfolio example"],
    )


class SkillMatcher:
    """Regex-based skill extractor and gap analyser."""

    def __init__(self, skills: List[dict]) -> None:
        self._skill_by_id: Dict[str, dict] = {s["id"]: s for s in skills}
        self._patterns: Dict[str, re.Pattern] = self._compile_patterns(skills)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compile_patterns(skills: List[dict]) -> Dict[str, re.Pattern]:
        patterns: Dict[str, re.Pattern] = {}
        for s in skills:
            escaped = [re.escape(a.lower()) for a in s["aliases"]]
            pat = r"(?<![a-z0-9])(" + "|".join(escaped) + r")(?![a-z0-9])"
            patterns[s["id"]] = re.compile(pat, re.IGNORECASE)
        return patterns

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_skills(self, text: str, role: str) -> Dict[str, SkillFound]:
        t = normalize_text(text)
        found: Dict[str, SkillFound] = {}

        for skill_id, pat in self._patterns.items():
            meta = self._skill_by_id[skill_id]
            if role not in meta.get("roles", []):
                continue
            hits = list({m.group(1) for m in pat.finditer(t)})
            if hits:
                conf = min(1.0, 0.55 + 0.08 * len(hits))
                found[skill_id] = SkillFound(
                    skill_id=skill_id, found_as=sorted(hits), confidence=conf
                )

        return found

    def importance_score(self, job_text: str, skill_id: str) -> float:
        jt = normalize_text(job_text)
        meta = self._skill_by_id[skill_id]

        count = 0
        for alias in meta["aliases"]:
            a_norm = normalize_text(alias)
            count += len(
                re.findall(rf"(?<![a-z0-9]){re.escape(a_norm)}(?![a-z0-9])", jt)
            )

        base = min(1.0, 0.25 + 0.12 * count)
        canonical = normalize_text(meta["canonical_name"])

        for rw in _REQUIRED_WORDS:
            if re.search(
                rf"{rw}.{{0,110}}{re.escape(canonical)}|{re.escape(canonical)}.{{0,110}}{rw}",
                jt,
            ):
                base = min(1.0, base + 0.25)
                break

        if meta.get("level") == "core":
            base = min(1.0, base + 0.1)

        return base

    def analyze(self, resume_text: str, job_text: str, target_role: str) -> dict:
        resume_skills = self.extract_skills(resume_text, target_role)
        job_skills = self.extract_skills(job_text, target_role)

        matched_ids = sorted(set(resume_skills) & set(job_skills))
        missing_ids = sorted(set(job_skills) - set(resume_skills))

        matched = [
            {
                "skill_id": sid,
                "skill": self._skill_by_id[sid]["canonical_name"],
                "category": self._skill_by_id[sid]["category"],
                "found_as": resume_skills[sid].found_as,
                "confidence": round(resume_skills[sid].confidence, 2),
            }
            for sid in matched_ids
        ]

        ranked: List[Tuple[str, float]] = sorted(
            ((sid, self.importance_score(job_text, sid)) for sid in missing_ids),
            key=lambda x: x[1],
            reverse=True,
        )

        missing = [
            {
                "skill_id": sid,
                "skill": self._skill_by_id[sid]["canonical_name"],
                "category": self._skill_by_id[sid]["category"],
                "importance": round(imp, 2),
                "priority": priority(imp),
                "reason": "Ranked by frequency + 'required/must' proximity in the job text (heuristic).",
                "suggested_path": suggested_path(self._skill_by_id[sid]["category"]),
            }
            for sid, imp in ranked
        ]

        return {
            "matched": matched,
            "missing": missing,
            "summary": {
                "target_role": target_role,
                "matched_count": len(matched),
                "missing_count": len(missing),
            },
        }
