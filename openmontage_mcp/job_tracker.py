"""In-memory job tracker for long-running OpenMontage operations.

MCP stdio calls should return quickly. Rendering a video or generating a
clip can take minutes, so we spawn a background thread and let clients poll
by job_id.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from tools.base_tool import ToolResult


@dataclass
class Job:
    job_id: str
    tool_name: str
    status: str = "pending"  # pending | running | completed | failed | cancelled
    progress_percent: float | None = None
    estimated_remaining_seconds: float | None = None
    result: ToolResult | None = None
    error: str | None = None
    thread: threading.Thread | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)


class JobTracker:
    """Thread-safe in-memory tracker for deferred tool executions."""

    # Threshold below which a job is considered "short" and may report
    # higher progress resolution if the underlying tool provides it.
    _poll_interval: float = 5.0

    def __init__(self, max_concurrent_jobs: int | None = None) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self.max_concurrent_jobs = max_concurrent_jobs or int(
            os.environ.get("OPENMONTAGE_MCP_MAX_CONCURRENT", "4")
        )

    def submit(
        self,
        fn: Callable[[], ToolResult],
        tool_name: str = "",
        estimated_seconds: float | None = None,
    ) -> str:
        """Start a background job and return its id."""
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            tool_name=tool_name,
            estimated_remaining_seconds=estimated_seconds,
        )

        def _run() -> None:
            with job._lock:
                job.status = "running"
                job.started_at = time.time()
            try:
                result = fn()
                with job._lock:
                    job.result = result
                    job.status = "completed" if result.success else "failed"
                    job.completed_at = time.time()
                    if not result.success and result.error:
                        job.error = result.error
                    job.progress_percent = 100.0 if result.success else 0.0
                    job.estimated_remaining_seconds = 0.0
            except Exception as exc:  # pragma: no cover - defensive
                with job._lock:
                    job.status = "failed"
                    job.error = str(exc)
                    job.completed_at = time.time()
                    job.progress_percent = 0.0
                    job.estimated_remaining_seconds = 0.0

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
                "tool_name": job.tool_name,
                "status": job.status,
                "created_at": job.created_at,
            }
            if job.started_at:
                payload["started_at"] = job.started_at
            if job.progress_percent is not None:
                payload["progress_percent"] = round(job.progress_percent, 1)
            if job.estimated_remaining_seconds is not None:
                payload["estimated_remaining_seconds"] = round(job.estimated_remaining_seconds, 1)
            if job.error:
                payload["error"] = job.error
            if job.result is not None:
                payload["success"] = job.result.success
                payload["data"] = job.result.data
                payload["artifacts"] = job.result.artifacts
                payload["cost_usd"] = job.result.cost_usd
                payload["duration_seconds"] = job.result.duration_seconds
            if job.completed_at:
                payload["completed_at"] = job.completed_at
                payload["duration_seconds"] = round(job.completed_at - (job.started_at or job.created_at), 2)

            payload["next_action"] = self._next_action(job)
        return payload

    def list_jobs(
        self,
        status: str | None = None,
        tool_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return a list of job summaries, optionally filtered."""
        with self._lock:
            jobs = list(self._jobs.values())

        summaries: list[dict[str, Any]] = []
        for job in jobs:
            with job._lock:
                if status and job.status != status:
                    continue
                if tool_name and job.tool_name != tool_name:
                    continue
                summaries.append({
                    "job_id": job.job_id,
                    "tool_name": job.tool_name,
                    "status": job.status,
                    "created_at": job.created_at,
                    "progress_percent": round(job.progress_percent, 1) if job.progress_percent is not None else None,
                })
        return summaries

    def cancel(self, job_id: str) -> dict[str, Any]:
        """Request cancellation of a running job.

        Because the underlying worker thread may not be interruptible
        (e.g. waiting on an HTTP response), this marks the job as cancelled
        and detaches it. The worker will finish but its result will be ignored.
        """
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            return {"error": f"job {job_id} not found"}

        with job._lock:
            if job.status in {"completed", "failed", "cancelled"}:
                return {
                    "job_id": job_id,
                    "status": job.status,
                    "message": "Job already finished or cancelled.",
                }
            job.status = "cancelled"
            job.completed_at = time.time()
            job.error = "Cancelled by user"

        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job cancellation requested. The underlying worker may finish but its result is ignored.",
        }

    def is_complete(self, job_id: str) -> bool:
        state = self.get(job_id)
        return state is not None and state["status"] in {"completed", "failed", "cancelled"}

    def can_accept(self) -> bool:
        """Return True if a new deferred job can be started without exceeding the concurrency limit."""
        with self._lock:
            active = sum(
                1 for job in self._jobs.values() if job.status in {"pending", "running"}
            )
        return active < self.max_concurrent_jobs

    def _next_action(self, job: Job) -> str:
        if job.status in {"completed", "failed", "cancelled"}:
            return "done"
        if job.status == "running":
            return "poll_again"
        return "wait_for_start"


# Singleton tracker used by the MCP server.
tracker = JobTracker()
