"""
Synchronous repository helpers used by the Celery worker.

Only the queries needed inside the worker task are defined here.
The async versions in submissions.py / languages.py remain the
primary API for the FastAPI routes.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models.submission import Submission
from db.models.language import Language


def get_submission_by_token_sync(db: Session, token: UUID) -> Submission | None:
    """Get submission by token."""
    result = db.execute(select(Submission).where(Submission.token == token))
    return result.scalar_one_or_none()


def get_language_sync(db: Session, language_id: int) -> Language | None:
    """Get language by ID."""
    result = db.execute(select(Language).where(Language.id == language_id))
    return result.scalar_one_or_none()
