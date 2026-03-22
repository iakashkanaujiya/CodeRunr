from datetime import datetime, timezone
from uuid import UUID

from loguru import logger

from db.repository.sync_queries import get_language_sync, get_submission_by_token_sync
from db.session import SyncSessionLocal
from exceptions.error_handler import sync_error_handler
from sandbox.isolate import IsolateCodeSandbox
from sandbox.schema import (
    SandboxSubmission,
    SandboxSubmissionLanguage,
    SandboxSubmissionStatus,
)
from utils.http_util import get_sync_http
from worker.celery import app


@sync_error_handler(name="post_data_on_callback")
def post_data_on_callback(callback_url: str, data: dict) -> None:
    response = get_sync_http().post(callback_url, json=data)
    response.raise_for_status()


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
            submission_record = get_submission_by_token_sync(db, token)

            if submission_record is None:
                logger.error("Submission {} not found", token)
                return

            language = get_language_sync(db, submission_record.language_id)
            if language is None:
                submission_record.status = SandboxSubmissionStatus.boxerr.value
                submission_record.message = (
                    f"Unsupported language_id: {submission_record.language_id}"
                )
                db.commit()
                return

            # Mark as processing
            submission_record.status = SandboxSubmissionStatus.process.value
            db.commit()

            # Build internal schema
            submission = SandboxSubmission(
                id=submission_record.id,
                language=SandboxSubmissionLanguage.model_validate(language),
                source_code=submission_record.source_code,
                stdin=submission_record.stdin or "",
                expected_output=submission_record.expected_output,
                cpu_time_limit=int(submission_record.cpu_time_limit),
                cpu_extra_time=int(submission_record.cpu_extra_time),
                wall_time_limit=int(submission_record.wall_time_limit),
                memory_limit=submission_record.memory_limit,
                stack_limit=submission_record.stack_limit,
                max_file_size=submission_record.max_file_size,
                max_processes_and_or_threads=submission_record.max_processes_and_or_threads,
                limit_per_process_and_thread_cpu_time_usages=submission_record.limit_per_process_and_thread_cpu_time_usages,
                limit_per_process_and_thread_memory_usages=submission_record.limit_per_process_and_thread_memory_usages,
            )

            # Run in sandbox
            sandbox = IsolateCodeSandbox(submission)
            # This will update the submission object
            sandbox.process_and_execute()

            # Write results back
            submission_record.status = submission.status.value
            submission_record.stdout = submission.stdout
            submission_record.stderr = submission.stderr
            submission_record.compile_output = submission.compile_output
            submission_record.time = submission.time
            submission_record.wall_time = submission.wall_time
            submission_record.memory = submission.memory
            submission_record.exit_code = submission.exit_code
            submission_record.exit_signal = submission.exit_signal
            submission_record.message = submission.message
            submission_record.finished_at = datetime.now(timezone.utc)

            # Commit the changes
            db.commit()

            if submission_record.webhook_url:
                try:
                    post_data_on_callback(
                        submission_record.webhook_url, submission.model_dump()
                    )
                except Exception:
                    logger.exception(
                        "Failed to deliver callback for submission {} to {}",
                        token,
                        submission_record.webhook_url,
                    )

            logger.info(
                "Submission {} processed -> {}", token, submission_record.status
            )
            return f"Submission successful {token}"

    except Exception as e:
        logger.exception(e.__repr__())
        # Mark as internal error using a fresh session
        try:
            with SyncSessionLocal() as db:
                err_submission_record = get_submission_by_token_sync(db, token)
                if err_submission_record is not None:
                    err_submission_record.status = SandboxSubmissionStatus.boxerr.value
                    err_submission_record.message = "Internal worker error"
                    db.commit()
        except Exception:
            logger.exception("Failed to mark submission {} as errored", token)

        return f"Submission failed {token}"
