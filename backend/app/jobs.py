"""
Lightweight in-memory job manager for long-running image processing tasks.
No external dependencies (no Redis, no Celery).
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional

from .config import settings
from .models import JobStatus, JobResponse, ProcessingResult

logger = logging.getLogger(__name__)


class Job:
    """Tracks the lifecycle of a single processing task."""

    __slots__ = (
        "id", "status", "progress", "result", "error",
        "created_at", "started_at", "completed_at", "_task",
    )

    def __init__(self, job_id: str) -> None:
        self.id = job_id
        self.status = JobStatus.PENDING
        self.progress: float = 0.0
        self.result: Optional[ProcessingResult] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self._task: Optional[asyncio.Task] = None

    def to_response(self) -> JobResponse:
        return JobResponse(
            job_id=self.id,
            status=self.status,
            progress=self.progress,
            result=self.result,
            error=self.error,
            created_at=self.created_at,
        )


class JobManager:
    """Manages background processing jobs with bounded concurrency."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)
        self._lock = asyncio.Lock()

    async def submit(
        self,
        coro_factory: Callable[[Job], Coroutine[Any, Any, ProcessingResult]],
    ) -> Job:
        """
        Submit a coroutine for background execution.
        ``coro_factory`` receives the Job so it can update ``job.progress``.
        Returns the Job immediately (status=PENDING).
        """
        job_id = uuid.uuid4().hex
        job = Job(job_id)

        async with self._lock:
            self._jobs[job_id] = job

        async def _run() -> None:
            async with self._semaphore:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc).isoformat()
                try:
                    result = await coro_factory(job)
                    job.result = result
                    job.status = JobStatus.COMPLETED if result.success else JobStatus.FAILED
                    if not result.success:
                        job.error = result.error
                except asyncio.CancelledError:
                    job.status = JobStatus.CANCELLED
                    job.error = "Job was cancelled"
                except Exception as exc:
                    logger.exception("Job %s failed", job_id)
                    job.status = JobStatus.FAILED
                    job.error = str(exc)
                finally:
                    job.completed_at = datetime.now(timezone.utc).isoformat()
                    job.progress = 100.0

        job._task = asyncio.create_task(_run())
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        """Attempt to cancel a running job. Returns True if cancellation was requested."""
        job = self._jobs.get(job_id)
        if job is None:
            return False
        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return False
        if job._task and not job._task.done():
            job._task.cancel()
            return True
        return False

    def list_jobs(self, limit: int = 50) -> list[JobResponse]:
        """Return the most recent jobs."""
        jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return [j.to_response() for j in jobs[:limit]]

    async def cleanup_old_jobs(self, max_age_seconds: int = 7200) -> int:
        """Remove completed/failed jobs older than max_age."""
        now = time.time()
        to_remove: list[str] = []
        async with self._lock:
            for jid, job in self._jobs.items():
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                    if job.completed_at:
                        completed = datetime.fromisoformat(job.completed_at).timestamp()
                        if now - completed > max_age_seconds:
                            to_remove.append(jid)
            for jid in to_remove:
                del self._jobs[jid]
        return len(to_remove)


# Module-level singleton
job_manager = JobManager()
