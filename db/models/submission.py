import uuid
from enum import Enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from db.base import Base


class SubmissionStatus(str, Enum):
    queued = "Queued"
    process = "Processing"
    acc = "Accepted"
    wans = "Wrong Answer"
    tle = "Time Limit Exceeded"
    mle = "Memory Limit Exceeded"
    rf = "Stack Overflow Error"
    comerr = "Compilation Error"
    sigsegv = "Runtime Error (SIGSEGV)"
    sigxfsz = "Runtime Error (SIGXFSZ)"
    sigfpe = "Runtime Error (SIGFPE)"
    sigabrt = "Runtime Error (SIGABRT)"
    nzec = "Runtime Error (NZEC)"
    other = "Runtime Error (Other)"
    boxerr = "Internal Error (boxerr)"
    exeerr = "Exec Format Error (exeerr)"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[uuid.UUID] = mapped_column(
        unique=True, default=uuid.uuid4, index=True
    )

    # Code
    source_code: Mapped[str] = mapped_column(Text)
    language_id: Mapped[int] = mapped_column()

    # I/O
    stdin: Mapped[Optional[str]] = mapped_column(Text)
    stdout: Mapped[Optional[str]] = mapped_column(Text)
    expected_output: Mapped[Optional[str]] = mapped_column(Text)
    compile_output: Mapped[Optional[str]] = mapped_column(Text)
    stderr: Mapped[Optional[str]] = mapped_column(Text)
    message: Mapped[Optional[str]] = mapped_column(Text)
    time: Mapped[Optional[float]] = mapped_column()
    wall_time: Mapped[Optional[float]] = mapped_column()
    memory: Mapped[Optional[int]] = mapped_column()
    exit_code: Mapped[Optional[int]] = mapped_column()
    exit_signal: Mapped[Optional[int]] = mapped_column()
    status: Mapped[SubmissionStatus] = mapped_column(
        String(64), default=SubmissionStatus.queued
    )

    # Limits
    cpu_time_limit: Mapped[float] = mapped_column(default=1)
    cpu_extra_time: Mapped[float] = mapped_column(default=1)
    wall_time_limit: Mapped[float] = mapped_column(default=10)
    memory_limit: Mapped[int] = mapped_column(default=256 * 1024)
    stack_limit: Mapped[int] = mapped_column(default=64 * 1024)
    max_file_size: Mapped[int] = mapped_column(default=1 * 1024)
    max_processes_and_or_threads: Mapped[int] = mapped_column(default=64)
    limit_per_process_and_thread_cpu_time_usages: Mapped[bool] = mapped_column(
        default=False
    )
    limit_per_process_and_thread_memory_usages: Mapped[bool] = mapped_column(
        default=False
    )

    # Webhook url
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        onupdate=func.now(), server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column()

    # Batch relationship (nullable — standalone submissions have no batch)
    batch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("submission_batches.id", ondelete="CASCADE")
    )
    batch: Mapped[Optional["SubmissionBatch"]] = relationship(back_populates="submissions")


class SubmissionBatch(Base):
    __tablename__ = "submission_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[uuid.UUID] = mapped_column(
        unique=True, default=uuid.uuid4, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        onupdate=func.now(), server_default=func.now()
    )

    # Submissions
    submissions: Mapped[List["Submission"]] = relationship(
        back_populates="batch", cascade="all,delete-orphan", lazy="selectin"
    )
