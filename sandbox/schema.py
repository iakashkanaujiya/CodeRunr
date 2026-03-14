from enum import Enum
from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class Status(str, Enum):
    queue = "Queued"
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


class SubmissionLanguage(BaseModel):
    source_file: str
    compile_cmd: Optional[str] = None
    run_cmd: str

    model_config = {"from_attributes": True}


class Submission(BaseModel):
    """Internal model consumed by IsolateJob."""

    id: int
    language: SubmissionLanguage
    source_code: str
    compile_output: Optional[str] = None
    stdin: Optional[str] = None
    expected_output: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    time: Optional[float] = None
    wall_time: Optional[float] = None
    memory: Optional[int] = None
    exit_code: Optional[int] = None
    exit_signal: Optional[int] = None
    message: Optional[str] = None
    status: Status = Status.queue
    cpu_time_limit: int
    cpu_extra_time: int
    wall_time_limit: int
    stack_limit: int
    memory_limit: int
    max_file_size: int
    max_processes_and_or_threads: int
    limit_per_process_and_thread_time_usages: bool
    limit_per_process_and_thread_memory_usgaes: bool
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
