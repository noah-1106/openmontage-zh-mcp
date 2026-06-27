"""In-memory job tracker for long-running OpenMontage operations.

MCP stdio calls should return quickly. Rendering a video can take minutes,
so we spawn a background thread and let clients poll by job_id.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from tools.base_tool import ToolResult


@dataclass
class Job:
    job_id: str
    status: str = "pending"  # pending | running | completed | failed
    result: ToolResult | None = None
    error: str | None = None
    thread: threading.Thread | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)


class JobTracker:
    """Thread-safe in-memory tracker for deferred tool executions."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def submit(self, fn: Callable[[], ToolResult]) -> str:
        """Start a background job and return its id."""
        job_id = str(uuid.uuid4())
        job = Job(job_id=job_id)

        def _run() -> None:
            with job._lock:
                job.status = "running"
            try:
                result = fn()
                with job._lock:
                    job.result = result
                    job.status = "completed" if result.success else "failed"
                    if not result.success and result.error:
                        job.error = result.error
            except Exception as exc:  # pragma: no cover - defensive
                with job._lock:
                    job.status = "failed"
                    job.error = str(exc)

        thread = threading.Thread(target=_run, daemon=True)
        job.thread = thread

        with self._lock:
            self._jobs[job_id] = job
        thread.start()
        return job_id

    def get(self, job_id: str) -> dict[str, Any] | None:
        """Return the current public state of a job."""
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            return None

        with job._lock:
            payload: dict[str, Any] = {
                "job_id": job.job_id,
                "status": job.status,
            }
            if job.error:
                payload["error"] = job.error
            if job.result is not None:
                payload["success"] = job.result.success
                payload["data"] = job.result.data
                payload["artifacts"] = job.result.artifacts
                payload["cost_usd"] = job.result.cost_usd
                payload["duration_seconds"] = job.result.duration_seconds
        return payload

    def is_complete(self, job_id: str) -> bool:
        state = self.get(job_id)
        return state is not None and state["status"] in {"completed", "failed"}


tracker = JobTracker()
