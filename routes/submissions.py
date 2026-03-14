"""
Submission API routes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_async_db
from db.models import Submission
from db.repository.submissions import (
    create_submission,
    get_submission_by_token,
    get_submissions,
    delete_submission,
    create_submission_batch,
    get_submission_batch_by_token,
)
from schema.submission import (
    SubmissionCreate,
    SubmissionResponse,
    SubmissionBatchCreate,
    SubmissionBatchResponse,
)
from worker.tasks import submit_submission_task


router = APIRouter(prefix="/submissions", tags=["Submissions"])


def _row_to_response(row: Submission) -> SubmissionResponse:
    """Convert an ORM Submission row to a SubmissionResponse."""
    return SubmissionResponse(
        token=row.token,
        source_code=row.source_code,
        language_id=row.language_id,
        stdin=row.stdin,
        expected_output=row.expected_output,
        stdout=row.stdout,
        stderr=row.stderr,
        compile_output=row.compile_output,
        message=row.message,
        status=row.status,
        time=row.time,
        wall_time=row.wall_time,
        memory=row.memory,
        exit_code=row.exit_code,
        exit_signal=row.exit_signal,
        cpu_time_limit=row.cpu_time_limit,
        cpu_extra_time=row.cpu_extra_time,
        wall_time_limit=row.wall_time_limit,
        memory_limit=row.memory_limit,
        stack_limit=row.stack_limit,
        max_file_size=row.max_file_size,
        max_processes_and_or_threads=row.max_processes_and_or_threads,
        limit_per_process_and_thread_time_usages=row.limit_per_process_and_thread_time_usages,
        limit_per_process_and_thread_memory_usgaes=row.limit_per_process_and_thread_memory_usgaes,
        created_at=row.created_at,
        finished_at=row.finished_at,
    )


@router.post("", response_model=SubmissionResponse, status_code=201)
async def create_submission_endpoint(
    body: SubmissionCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new submission and enqueue it for processing."""
    row = await create_submission(db, body)
    submit_submission_task.delay(str(row.token))
    return _row_to_response(row)


@router.get("", response_model=list[SubmissionResponse])
async def get_submissions_endpoint(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """List submissions with pagination."""
    rows = await get_submissions(db, page=page, per_page=per_page)
    return [_row_to_response(r) for r in rows]


@router.post("/batch", response_model=SubmissionBatchResponse, status_code=201)
async def create_submission_batch_endpoint(
    body: SubmissionBatchCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """Create a batch of submissions and enqueue them all for processing."""
    batch = await create_submission_batch(db, body.submissions)
    for sub in batch.submissions:
        submit_submission_task.delay(str(sub.token))
    return SubmissionBatchResponse(
        token=batch.token,
        submissions=[_row_to_response(s) for s in batch.submissions],
    )


@router.get("/batch/{token}", response_model=SubmissionBatchResponse)
async def get_submission_batch_endpoint(
    token: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """Retrieve a submission batch and all its submissions."""
    batch = await get_submission_batch_by_token(db, token)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return SubmissionBatchResponse(
        token=batch.token,
        submissions=[_row_to_response(s) for s in batch.submissions],
    )


@router.get("/{token}", response_model=SubmissionResponse)
async def get_submission_endpoint(
    token: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """Retrieve a submission by its token."""
    row = await get_submission_by_token(db, token)
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    return _row_to_response(row)


@router.delete("/{token}", status_code=204)
async def delete_submission_endpoint(
    token: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a submission by its token."""
    deleted = await delete_submission(db, token)
    if not deleted:
        raise HTTPException(status_code=404, detail="Submission not found")
    return None
