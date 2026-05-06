from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("NVIDIA_API_KEY", "")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY env var is not set")
        _client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
        )
    return _client


_SYSTEM = (
    "You are a technical recruiter. Given a job description and a list of missing skills, "
    "rank each skill by how critical it is for the role. "
    "Respond ONLY with a valid JSON array — no markdown, no explanation."
)

_PROMPT = """Job description:
{job_text}

Missing skills to rank: {skills}

Return a JSON array with one object per skill:
[{{"skill": "<exact name from the list>", "priority": "High|Medium|Low", "reason": "<one sentence>"}}]"""


def score_importance(job_text: str, missing_skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Re-rank missing skills using Nemotron. Falls back to original order on any error."""
    if not missing_skills:
        return missing_skills

    skill_names = [s["skill"] for s in missing_skills]

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-70b-instruct",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": _PROMPT.format(
                    job_text=job_text[:4000],  # stay within context
                    skills=", ".join(skill_names),
                )},
            ],
            temperature=0.2,
            max_tokens=1024,
        )

        raw = response.choices[0].message.content or ""
        # Strip markdown code fences if the model wraps output anyway
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        llm_scores: list[dict] = json.loads(raw)

        score_map = {entry["skill"]: entry for entry in llm_scores}
        for skill in missing_skills:
            match = score_map.get(skill["skill"], {})
            if match.get("priority") in {"High", "Medium", "Low"}:
                skill["priority"] = match["priority"]
            if match.get("reason"):
                skill["reason"] = match["reason"]

    except Exception:
        logger.exception("Nemotron scoring failed — using heuristic fallback")

    return missing_skills
