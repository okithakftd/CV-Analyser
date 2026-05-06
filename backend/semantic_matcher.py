from __future__ import annotations

import logging
import os
import re
from typing import Dict, List

from skill_matcher import SkillMatcher, SkillFound, normalize_text

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = float(os.getenv("ML_SIMILARITY_THRESHOLD", "0.35"))
MODEL_NAME = os.getenv("ML_MODEL_NAME", "all-MiniLM-L6-v2")

# Sentence splitter — split on period/newline boundaries
_SENT_RE = re.compile(r"(?<=[.!\?])\s+|\n+")


def _chunk_text(text: str, max_words: int = 40) -> List[str]:
    """Split text into overlapping sentence-level chunks."""
    sentences = [s.strip() for s in _SENT_RE.split(text) if s.strip()]
    chunks: List[str] = []
    buf: List[str] = []
    word_count = 0
    for sent in sentences:
        words = sent.split()
        if word_count + len(words) > max_words and buf:
            chunks.append(" ".join(buf))
            buf = buf[len(buf) // 2:]  # 50% overlap
            word_count = sum(len(s.split()) for s in buf)
        buf.append(sent)
        word_count += len(words)
    if buf:
        chunks.append(" ".join(buf))
    return chunks or [text]


class SemanticSkillMatcher:
    """
    Wraps SkillMatcher with a semantic fallback using sentence-transformers.
    Regex runs first; any skill not found by regex is re-checked semantically.
    """

    def __init__(self, skills: List[dict]) -> None:
        self._regex_matcher = SkillMatcher(skills)
        self._skills = skills
        self._model = None
        self._skill_embeddings: Dict[str, object] = {}
        self._load_model()

    def _load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(MODEL_NAME)
            self._skill_embeddings = self._embed_skills()
            logger.info("Semantic matcher loaded: %s", MODEL_NAME)
        except Exception:
            logger.warning("sentence-transformers not available — falling back to regex only")
            self._model = None

    def _embed_skills(self) -> Dict[str, object]:
        from sentence_transformers import SentenceTransformer
        assert isinstance(self._model, SentenceTransformer)

        embeddings: Dict[str, object] = {}
        for skill in self._skills:
            # Represent each skill as its name + top aliases joined
            text = skill["canonical_name"] + " " + " ".join(skill["aliases"][:6])
            embeddings[skill["id"]] = self._model.encode(text, convert_to_tensor=True)
        return embeddings

    def _semantic_extract(self, text: str, role: str) -> Dict[str, SkillFound]:
        from sentence_transformers import util
        import torch

        found: Dict[str, SkillFound] = {}
        chunks = _chunk_text(normalize_text(text))
        chunk_embeddings = self._model.encode(chunks, convert_to_tensor=True)  # type: ignore[union-attr]

        for skill in self._skills:
            if role not in skill.get("roles", []):
                continue
            sid = skill["id"]
            skill_emb = self._skill_embeddings[sid]
            # Max similarity across all chunks
            sims = util.cos_sim(skill_emb, chunk_embeddings)[0]
            best: float = float(torch.max(sims).item())
            if best >= SIMILARITY_THRESHOLD:
                found[sid] = SkillFound(
                    skill_id=sid,
                    found_as=[skill["canonical_name"]],
                    confidence=round(best, 2),
                )
        return found

    def extract_skills(self, text: str, role: str) -> Dict[str, SkillFound]:
        regex_found = self._regex_matcher.extract_skills(text, role)

        if self._model is None:
            return regex_found

        semantic_found = self._semantic_extract(text, role)
        # Merge: regex result wins when both find the same skill (higher precision)
        merged = {**semantic_found, **regex_found}
        return merged

    def analyze(self, resume_text: str, job_text: str, target_role: str) -> dict:
        resume_skills = self.extract_skills(resume_text, target_role)
        job_skills = self.extract_skills(job_text, target_role)

        matched_ids = sorted(set(resume_skills) & set(job_skills))
        missing_ids = sorted(set(job_skills) - set(resume_skills))

        skill_by_id = self._regex_matcher._skill_by_id

        matched = [
            {
                "skill_id": sid,
                "skill": skill_by_id[sid]["canonical_name"],
                "category": skill_by_id[sid]["category"],
                "found_as": resume_skills[sid].found_as,
                "confidence": resume_skills[sid].confidence,
            }
            for sid in matched_ids
        ]

        from skill_matcher import suggested_path, priority

        ranked = sorted(
            ((sid, self._regex_matcher.importance_score(job_text, sid)) for sid in missing_ids),
            key=lambda x: x[1],
            reverse=True,
        )

        missing = [
            {
                "skill_id": sid,
                "skill": skill_by_id[sid]["canonical_name"],
                "category": skill_by_id[sid]["category"],
                "importance": round(imp, 2),
                "priority": priority(imp),
                "reason": "Ranked by frequency + 'required/must' proximity in the job text.",
                "suggested_path": suggested_path(skill_by_id[sid]["category"]),
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
