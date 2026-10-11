"""
Job Tracker Service -- Sprint 5.

Provides a thread-safe, in-memory status tracker for asynchronous diagram generation jobs.
Tracks pipeline progress stage, percentage, diagnostic message, and final result payload.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Ordered pipeline stages for progress calculation
PIPELINE_STAGES = [
    ("scope_guard", 10, "Validating prompt domain scope"),
    ("preprocessing", 20, "Normalizing prompt via spaCy NLP"),
    ("embedding_search", 35, "Generating Voyage AI embedding & searching cache"),
    ("cache_check", 45, "Evaluating similarity match vs fresh generation"),
    ("llm_generation", 60, "Generating graph structure via Groq LLM"),
    ("ast_validation", 75, "Validating Pydantic AST & graph topology rules"),
    ("rendering", 85, "Compiling AST to DSL & rendering SVG via Kroki"),
    ("output_validation", 95, "Validating SVG XML & semantic label reconciliation"),
    ("completed", 100, "Pipeline execution completed successfully"),
]

STAGE_LOOKUP = {stage[0]: (idx + 1, stage[1], stage[2]) for idx, stage in enumerate(PIPELINE_STAGES)}


@dataclass
class JobStatus:
    job_id: str
    stage: str = "scope_guard"
    step_index: int = 1
    total_steps: int = len(PIPELINE_STAGES)
    progress_percentage: int = 10
    message: str = "Validating prompt domain scope"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "stage": self.stage,
            "step_index": self.step_index,
            "total_steps": self.total_steps,
            "progress_percentage": self.progress_percentage,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


import hashlib

class JobTrackerService:
    """
    Thread-safe registry for asynchronous pipeline jobs.
    """

    def __init__(self, ttl_seconds: int = 3600):
        self._jobs: Dict[str, JobStatus] = {}
        self._active_prompts: Dict[str, Tuple[str, float]] = {}  # prompt_hash -> (job_id, started_at)
        self._lock = threading.Lock()
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def hash_prompt(prompt: str, user_scope: Optional[str] = None) -> str:
        """Create normalized deterministic fingerprint of user prompt."""
        normalized = " ".join(prompt.strip().lower().split())
        raw_key = f"{user_scope or 'global'}:{normalized}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def register_active_prompt(self, prompt_hash: str, job_id: str) -> None:
        """Associate in-flight generation job with prompt hash."""
        with self._lock:
            self._active_prompts[prompt_hash] = (job_id, time.time())

    def find_active_job_for_prompt(
        self,
        prompt_hash: str,
        max_age_seconds: int = 30,
    ) -> Optional[JobStatus]:
        """Check if an identical prompt is already being processed actively."""
        with self._lock:
            record = self._active_prompts.get(prompt_hash)
            if not record:
                return None

            job_id, started_at = record
            now = time.time()
            if now - started_at > max_age_seconds:
                self._active_prompts.pop(prompt_hash, None)
                return None

            job = self._jobs.get(job_id)
            if not job or job.stage in ("completed", "failed"):
                self._active_prompts.pop(prompt_hash, None)
                return None

            return job

    def clear_active_prompt(self, prompt_hash: str) -> None:
        with self._lock:
            self._active_prompts.pop(prompt_hash, None)

    def create_job(self, job_id: str) -> JobStatus:
        with self._lock:
            self._cleanup_expired()
            job = JobStatus(job_id=job_id)
            self._jobs[job_id] = job
            return job

    def update_job(
        self,
        job_id: str,
        stage: str,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> JobStatus:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                job = JobStatus(job_id=job_id)
                self._jobs[job_id] = job

            if stage in STAGE_LOOKUP:
                step_idx, pct, default_msg = STAGE_LOOKUP[stage]
                job.stage = stage
                job.step_index = step_idx
                job.progress_percentage = pct
                job.message = message or default_msg
            elif stage == "failed":
                job.stage = "failed"
                job.progress_percentage = 100
                job.message = message or "Pipeline execution failed"
                job.error = error

            if result is not None:
                job.result = result

            if error is not None:
                job.error = error

            job.updated_at = time.time()
            return job

    def get_job(self, job_id: str) -> Optional[JobStatus]:
        with self._lock:
            return self._jobs.get(job_id)

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [jid for jid, job in self._jobs.items() if now - job.updated_at > self.ttl_seconds]
        for jid in expired:
            del self._jobs[jid]


# Global singleton instance
job_tracker_service = JobTrackerService()
