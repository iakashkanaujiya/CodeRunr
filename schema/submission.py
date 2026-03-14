from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SubmissionCreate(BaseModel):
    source_code: str
    language_id: int
    stdin: Optional[str] = None
    expected_output: Optional[str] = None
    cpu_time_limit: float = Field(default=1, ge=0.1, le=15)
    cpu_extra_time: float = Field(default=1, ge=0, le=5)
    wall_time_limit: float = Field(default=10, ge=0.5, le=30)
    memory_limit: int = Field(default=128000, ge=2048, le=512000, description="KB")
    stack_limit: int = Field(default=65536, ge=2048, le=131072, description="KB")
    max_file_size: int = Field(default=1024, ge=1, le=4096, description="KB")
    max_processes_and_or_threads: int = Field(default=8, ge=1, le=128)
    limit_per_process_and_thread_time_usages: bool = False
    limit_per_process_and_thread_memory_usgaes: bool = False


class SubmissionBatchCreate(BaseModel):
    submissions: list[SubmissionCreate] = Field(..., min_length=1, max_length=20)


class SubmissionResponse(BaseModel):
    token: UUID
    source_code: str
    language_id: int
    stdin: Optional[str] = None
    expected_output: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    message: Optional[str] = None
    status: str
    time: Optional[float] = None
    wall_time: Optional[float] = None
    memory: Optional[int] = None
    exit_code: Optional[int] = None
    exit_signal: Optional[int] = None
    cpu_time_limit: float
    cpu_extra_time: float
    wall_time_limit: float
    memory_limit: int
    stack_limit: int
    max_file_size: int
    max_processes_and_or_threads: int
    limit_per_process_and_thread_time_usages: bool
    limit_per_process_and_thread_memory_usgaes: bool
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SubmissionBatchResponse(BaseModel):
    token: UUID
    submissions: list[SubmissionResponse]

    model_config = {"from_attributes": True}
