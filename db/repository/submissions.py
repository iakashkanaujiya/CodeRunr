from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.submission import Submission, SubmissionBatch
from schema.submission import SubmissionCreate


async def create_submission(
    db: AsyncSession, submission_create: SubmissionCreate
) -> Submission:
    """
    Create a new submission record into database.
    """
    try:
        submission = Submission(
            source_code=submission_create.source_code,
            language_id=submission_create.language_id,
            stdin=submission_create.stdin,
            expected_output=submission_create.expected_output,
            cpu_time_limit=submission_create.cpu_time_limit,
            cpu_extra_time=submission_create.cpu_extra_time,
            wall_time_limit=submission_create.wall_time_limit,
            memory_limit=submission_create.memory_limit,
            stack_limit=submission_create.stack_limit,
            max_file_size=submission_create.max_file_size,
            max_processes_and_or_threads=submission_create.max_processes_and_or_threads,
            limit_per_process_and_thread_cpu_time_usages=submission_create.limit_per_process_and_thread_cpu_time_usages,
            limit_per_process_and_thread_memory_usages=submission_create.limit_per_process_and_thread_memory_usages,
            webhook_url=str(submission_create.webhook_url) if submission_create.webhook_url else None,
        )

        if submission_create.token:
            setattr(submission, "token", submission_create.token)

        db.add(submission)
        await db.commit()
        await db.refresh(submission)
        return submission
    except Exception:
        await db.rollback()
        raise


async def get_submission_by_token(db: AsyncSession, token: UUID) -> Submission | None:
    """
    Get a submission by its token.

    Args:
        db (AsyncSession): The database session.
        token (UUID): The token of the submission to retrieve.

    Returns:
        Submission | None: The submission if found, None otherwise.
    """
    result = await db.execute(select(Submission).where(Submission.token == token))
    return result.scalar_one_or_none()


async def get_submissions(
    db: AsyncSession, page: int = 1, per_page: int = 20
) -> list[Submission]:
    """
    Get all submissions.

    Args:
        db (AsyncSession): The database session.
        page (int): The page number.
        per_page (int): The number of submissions per page.

    Returns:
        list[Submission]: A list of submissions.
    """
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Submission)
        .order_by(Submission.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    return list(result.scalars().all())


async def delete_submission(db: AsyncSession, token: UUID) -> bool:
    """
    Delete a submission by its token.

    Args:
        db (AsyncSession): The database session.
        token (UUID): The token of the submission to delete.

    Returns:
        bool: True if the submission was deleted, False otherwise.
    """
    submission = await get_submission_by_token(db, token)
    if not submission:
        return False
    await db.delete(submission)
    await db.commit()
    return True


async def create_submission_batch(
    db: AsyncSession,
    submissions_data: list[SubmissionCreate],
) -> SubmissionBatch:
    """Create a batch and all its submissions in one transaction."""
    try:
        batch = SubmissionBatch()
        db.add(batch)
        await db.flush()

        submissions = []
        for data in submissions_data:
            sub = Submission(
                source_code=data.source_code,
                language_id=data.language_id,
                stdin=data.stdin,
                expected_output=data.expected_output,
                cpu_time_limit=data.cpu_time_limit,
                cpu_extra_time=data.cpu_extra_time,
                wall_time_limit=data.wall_time_limit,
                memory_limit=data.memory_limit,
                stack_limit=data.stack_limit,
                max_file_size=data.max_file_size,
                max_processes_and_or_threads=data.max_processes_and_or_threads,
                limit_per_process_and_thread_cpu_time_usages=data.limit_per_process_and_thread_cpu_time_usages,
                limit_per_process_and_thread_memory_usages=data.limit_per_process_and_thread_memory_usages,
                webhook_url=str(data.webhook_url) if data.webhook_url else None,
                batch_id=batch.id,
            )
            if data.token:
                setattr(sub, "token", data.token)

            submissions.append(sub)

        db.add_all(submissions)
        await db.commit()
        await db.refresh(batch)
        return batch
    except Exception:
        await db.rollback()
        raise


async def get_submission_batch_by_token(
    db: AsyncSession,
    token: UUID,
) -> SubmissionBatch | None:
    """
    Get a submission batch by its token.

    Args:
        db (AsyncSession): The database session.
        token (UUID): The token of the submission batch to retrieve.

    Returns:
        SubmissionBatch | None: The submission batch if found, None otherwise.
    """
    result = await db.execute(
        select(SubmissionBatch)
        .options(selectinload(SubmissionBatch.submissions))
        .where(SubmissionBatch.token == token)
    )
    return result.scalar_one_or_none()
