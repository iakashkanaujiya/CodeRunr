import logging
from uuid import UUID
from datetime import datetime, timezone

from db.session import SyncSessionLocal
from db.repository.sync_queries import get_submission_by_token_sync, get_language_sync
from sandbox.schema import Submission, SubmissionLanguage, Status
from sandbox.isolate import IsolateCodeSanbox
from .celery import app

logger = logging.getLogger(__name__)


@app.task
def submit_submission_task(submission_token: str) -> str:
    """
    Main task function invoked by the Celery worker.

    1. Loads the submission from PostgreSQL.
    2. Builds the internal Submission schema and IsolateJob.
    3. Runs the job inside the sandbox.
    4. Writes results back to the database.
    """
    token = UUID(submission_token)

    try:
        with SyncSessionLocal() as db:
            row = get_submission_by_token_sync(db, token)

            if row is None:
                logger.error("Submission %s not found", token)
                return

            language = get_language_sync(db, row.language_id)
            if language is None:
                row.status = Status.boxerr.value
                row.message = f"Unsupported language_id: {row.language_id}"
                db.commit()
                return

            # Mark as processing
            row.status = Status.process.value
            db.commit()

            # Build internal schema
            submission = Submission(
                id=row.id,
                language=SubmissionLanguage.model_validate(language),
                source_code=row.source_code,
                stdin=row.stdin or "",
                expected_output=row.expected_output,
                cpu_time_limit=int(row.cpu_time_limit),
                cpu_extra_time=int(row.cpu_extra_time),
                wall_time_limit=int(row.wall_time_limit),
                memory_limit=row.memory_limit,
                stack_limit=row.stack_limit,
                max_file_size=row.max_file_size,
                max_processes_and_or_threads=row.max_processes_and_or_threads,
                limit_per_process_and_thread_time_usages=row.limit_per_process_and_thread_time_usages,
                limit_per_process_and_thread_memory_usgaes=row.limit_per_process_and_thread_memory_usgaes,
            )

            # Run in sandbox
            sandbox = IsolateCodeSanbox(submission)
            # This will update the submission object
            sandbox.process_and_execute()

            # Write results back
            row.status = submission.status.value
            row.stdout = submission.stdout
            row.stderr = submission.stderr
            row.compile_output = submission.compile_output
            row.time = submission.time
            row.wall_time = submission.wall_time
            row.memory = submission.memory
            row.exit_code = submission.exit_code
            row.exit_signal = submission.exit_signal
            row.message = submission.message
            row.finished_at = datetime.now(timezone.utc)

            db.commit()
            logger.info("Submission %s processed → %s", token, row.status)

            return f"Submission successful {token}"

    except Exception:
        logger.exception("Failed to process submission %s", token)
        # Mark as internal error using a fresh session
        try:
            with SyncSessionLocal() as db:
                err_row = get_submission_by_token_sync(db, token)
                if err_row is not None:
                    err_row.status = Status.boxerr.value
                    err_row.message = "Internal worker error"
                    db.commit()
        except Exception:
            logger.exception("Failed to mark submission %s as errored", token)

        return f"Submission failed {token}"
