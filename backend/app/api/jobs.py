"""
Job management endpoints.
"""

from fastapi import APIRouter, HTTPException

from ..models import JobResponse
from ..jobs import job_manager

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobResponse])
async def list_jobs(limit: int = 50):
    """List recent jobs."""
    return job_manager.list_jobs(limit=min(limit, 100))


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get the status of a specific job."""
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    return job.to_response()


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a pending or running job."""
    success = job_manager.cancel(job_id)
    if not success:
        raise HTTPException(
            400, "Job could not be cancelled (not found or already finished)."
        )
    return {"status": "cancelled", "job_id": job_id}
