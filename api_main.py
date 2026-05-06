from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from skill_matcher import SkillMatcher


def _parse_cors(origins_str: str) -> List[str]:
    s = (origins_str or "").strip()
    if not s:
        return []
    if s == "*":
        return ["*"]
    return [o.strip() for o in s.split(",") if o.strip()]


CORS_ALLOWED_ORIGINS = _parse_cors(
    os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
)
CORS_ALLOWED_ORIGIN_REGEX = os.getenv("CORS_ALLOWED_ORIGIN_REGEX")

TAXONOMY_PATH = os.getenv("SKILLS_TAXONOMY_PATH", "skills_taxonomy.json")
_taxonomy = json.loads(Path(TAXONOMY_PATH).read_text(encoding="utf-8"))
matcher = SkillMatcher(_taxonomy["skills"])


class AnalyzeRequest(BaseModel):
    resume_text: str = Field(..., min_length=30, max_length=50_000)
    job_text: str = Field(..., min_length=30, max_length=50_000)
    target_role: str = Field(..., pattern="^(backend|fullstack|cloud_devops)$")


class SkillOut(BaseModel):
    skill_id: str
    skill: str
    category: str
    found_as: Optional[List[str]] = None
    confidence: Optional[float] = None
    importance: Optional[float] = None
    priority: Optional[str] = None
    reason: Optional[str] = None
    suggested_path: Optional[List[str]] = None


class AnalyzeResponse(BaseModel):
    matched: List[SkillOut]
    missing: List[SkillOut]
    summary: dict


app = FastAPI(title="Skill Gap Analyzer", version="1.0.0")

if CORS_ALLOWED_ORIGIN_REGEX:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=CORS_ALLOWED_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/")
def root() -> dict:
    return {
        "ok": True,
        "service": "Skill Gap Analyzer API",
        "endpoints": ["/health", "/analyze", "/docs"],
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    try:
        result = matcher.analyze(req.resume_text, req.job_text, req.target_role)
        return AnalyzeResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.") from exc
