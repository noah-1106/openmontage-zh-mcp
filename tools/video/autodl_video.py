"""AutoDL video generation via Volcano Ark content-generation tasks API.

Supports models hosted on the AutoDL model marketplace, such as
Doubao Seedance 2.0, through the AutoDL proxy endpoint.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


class AutoDLVideo(BaseTool):
    name = "autodl_video"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "autodl"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = (
        "Set AUTODL_API_KEY to your AutoDL token.\n"
        "  Get one at https://www.autodl.art/"
    )
    agent_skills = ["seedance-2-0", "ai-video-gen"]

    capabilities = ["text_to_video", "image_to_video", "reference_to_video"]
    supports = {
        "text_to_video": True,
        "image_to_video": True,
        "reference_to_video": True,
        "reference_image": True,
        "reference_video": True,
        "reference_audio": True,
        "generate_audio": True,
        "aspect_ratio": True,
        "duration": True,
        "resolution": True,
    }
    best_for = [
        "domestic Chinese video generation through AutoDL",
        "Doubao Seedance 2.0 cinematic clips with native audio",
        "reference-conditioned generation (image / video / audio)",
    ]
    not_good_for = ["offline generation", "non-AutoDL model endpoints"]

    input_schema = {
        "type": "object",
        "required": [],
        "properties": {
            "prompt": {"type": "string"},
            "model": {
                "type": "string",
                "default": "doubao-seedance-2-0-260128",
                "description": "AutoDL video model name",
            },
            "operation": {
                "type": "string",
                "enum": ["text_to_video", "image_to_video", "reference_to_video", "get_status"],
                "default": "text_to_video",
                "description": (
                    "Generation operations create a task and return a task_id immediately. "
                    "Use get_status with task_id to poll for completion and download the video."
                ),
            },
            "task_id": {
                "type": "string",
                "description": "Required for operation=get_status. The task ID returned by a previous generation call.",
            },
            "duration": {
                "type": "integer",
                "default": 5,
                "description": "Duration in seconds",
            },
            "aspect_ratio": {
                "type": "string",
                "enum": ["16:9", "9:16", "1:1", "4:3", "3:4"],
                "default": "16:9",
            },
            "resolution": {
                "type": "string",
                "enum": ["480p", "720p", "1080p"],
                "default": "720p",
            },
            "generate_audio": {
                "type": "boolean",
                "default": True,
            },
            "image_url": {
                "type": "string",
                "description": "Image URL for image_to_video or reference_to_video",
            },
            "image_path": {
                "type": "string",
                "description": "Local image path; uploaded to a temporary URL if needed",
            },
            "reference_image_urls": {
                "type": "array",
                "items": {"type": "string"},
            },
            "reference_video_urls": {
                "type": "array",
                "items": {"type": "string"},
            },
            "reference_audio_urls": {
                "type": "array",
                "items": {"type": "string"},
            },
            "watermark": {
                "type": "boolean",
                "default": False,
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=500, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "model", "operation", "duration", "aspect_ratio"]
    side_effects = ["writes video file to output_path", "calls AutoDL API"]
    user_visible_verification = [
        "Watch generated clip for motion coherence, audio sync, and visual quality"
    ]

    def _get_api_key(self) -> str | None:
        return os.environ.get("AUTODL_API_KEY")

    def _get_base_url(self) -> str:
        return os.environ.get("AUTODL_BASE_URL", "https://www.autodl.art/api/v1")

    def get_status(self) -> ToolStatus:
        if self._get_api_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        # AutoDL pricing is per-token based on (input+output duration) * width * height * fps / 1024.
        # Use a rough placeholder until pricing metadata is available.
        duration = inputs.get("duration", 5)
        resolution = inputs.get("resolution", "720p")
        rate_per_sec = {"480p": 0.05, "720p": 0.08, "1080p": 0.12}
        return round(rate_per_sec.get(resolution, 0.08) * duration, 2)

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        if inputs.get("operation") == "get_status":
            return 5.0
        return 120.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = self._get_api_key()
        if not api_key:
            return ToolResult(
                success=False,
                error="AUTODL_API_KEY not set. " + self.install_instructions,
            )

        import requests

        start = time.time()
        base_url = self._get_base_url().rstrip("/")
        tasks_url = f"{base_url}/ark/v3/contents/generations/tasks"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        operation = inputs.get("operation", "text_to_video")

        if operation == "get_status":
            return self._poll_task(inputs, tasks_url, headers, start)

        if "prompt" not in inputs:
            return ToolResult(
                success=False,
                error="prompt is required for generation operations",
            )

        return self._create_task(inputs, tasks_url, headers, start)

    def _create_task(
        self,
        inputs: dict[str, Any],
        tasks_url: str,
        headers: dict[str, str],
        start: float,
    ) -> ToolResult:
        import requests

        model = inputs.get("model", "doubao-seedance-2-0-260128")
        operation = inputs.get("operation", "text_to_video")

        content: list[dict[str, Any]] = [
            {"type": "text", "text": inputs["prompt"]}
        ]

        if operation == "image_to_video":
            image_url = inputs.get("image_url")
            if not image_url and inputs.get("image_path"):
                image_url = self._upload_local_file(inputs["image_path"])
            if not image_url:
                return ToolResult(
                    success=False,
                    error="image_to_video requires image_url or image_path",
                )
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url},
                "role": "reference_image",
            })

        if operation == "reference_to_video":
            for url in inputs.get("reference_image_urls") or []:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": url},
                    "role": "reference_image",
                })
            for url in inputs.get("reference_video_urls") or []:
                content.append({
                    "type": "video_url",
                    "video_url": {"url": url},
                    "role": "reference_video",
                })
            for url in inputs.get("reference_audio_urls") or []:
                content.append({
                    "type": "audio_url",
                    "audio_url": {"url": url},
                    "role": "reference_audio",
                })

        payload: dict[str, Any] = {
            "model": model,
            "content": content,
            "generate_audio": inputs.get("generate_audio", True),
            "ratio": inputs.get("aspect_ratio", "16:9"),
            "duration": inputs.get("duration", 5),
            "resolution": inputs.get("resolution", "720p"),
            "watermark": inputs.get("watermark", False),
        }

        try:
            # Create the task quickly; do not wait for completion here.
            # Long-running synchronous endpoints are killed by MCP/agent 30s timeouts.
            create_resp = requests.post(tasks_url, headers=headers, json=payload, timeout=30)
            if not create_resp.ok:
                detail = create_resp.text or "no response body"
                return ToolResult(
                    success=False,
                    error=(
                        f"AutoDL video generation failed with HTTP {create_resp.status_code}.\n"
                        f"URL: {tasks_url}\n"
                        f"Response: {detail[:800]}"
                    ),
                )
            task_id = create_resp.json()["id"]
        except Exception as e:
            return ToolResult(success=False, error=f"AutoDL video task creation failed: {e}")

        return ToolResult(
            success=True,
            data={
                "provider": "autodl",
                "model": model,
                "operation": operation,
                "task_id": task_id,
                "status": "created",
                "message": "Task created. Poll with operation='get_status' and task_id.",
            },
            cost_usd=0.0,
            duration_seconds=round(time.time() - start, 2),
            model=model,
        )

    def _poll_task(
        self,
        inputs: dict[str, Any],
        tasks_url: str,
        headers: dict[str, str],
        start: float,
    ) -> ToolResult:
        import requests

        task_id = inputs.get("task_id")
        if not task_id:
            return ToolResult(
                success=False,
                error="operation=get_status requires task_id",
            )

        try:
            status_resp = requests.get(
                f"{tasks_url}/{task_id}", headers=headers, timeout=120
            )
            if not status_resp.ok:
                detail = status_resp.text or "no response body"
                return ToolResult(
                    success=False,
                    error=(
                        f"AutoDL video task status check failed with HTTP {status_resp.status_code}.\n"
                        f"Response: {detail[:800]}"
                    ),
                )
            status_data = status_resp.json()
            status = status_data.get("status")

            if status in ("queued", "in_progress", "running"):
                return ToolResult(
                    success=True,
                    data={
                        "provider": "autodl",
                        "task_id": task_id,
                        "status": status,
                        "message": "Task is still processing. Poll again with operation='get_status'.",
                    },
                    cost_usd=0.0,
                    duration_seconds=round(time.time() - start, 2),
                )

            if status in ("failed", "cancelled"):
                error_msg = status_data.get("error") or f"task {status}"
                return ToolResult(
                    success=False,
                    error=f"AutoDL video generation {status}: {error_msg}",
                )

            if status != "succeeded":
                return ToolResult(
                    success=True,
                    data={
                        "provider": "autodl",
                        "task_id": task_id,
                        "status": status,
                        "message": "Task status unknown. Poll again with operation='get_status'.",
                    },
                    cost_usd=0.0,
                    duration_seconds=round(time.time() - start, 2),
                )

            video_url = status_data["content"]["video_url"]
            video_resp = requests.get(video_url, timeout=120)
            video_resp.raise_for_status()

            output_path = Path(inputs.get("output_path", "autodl_video.mp4"))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(video_resp.content)

        except Exception as e:
            return ToolResult(success=False, error=f"AutoDL video generation failed: {e}")

        model = status_data.get("model", inputs.get("model", "doubao-seedance-2-0-260128"))
        return ToolResult(
            success=True,
            data={
                "provider": "autodl",
                "model": model,
                "task_id": task_id,
                "status": "succeeded",
                "operation": status_data.get("operation") or inputs.get("operation"),
                "duration": status_data.get("duration"),
                "resolution": status_data.get("resolution"),
                "ratio": status_data.get("ratio"),
                "seed": status_data.get("seed"),
                "output": str(output_path),
            },
            artifacts=[str(output_path)],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            model=model,
        )

    def _upload_local_file(self, path: str) -> str | None:
        """Placeholder for local file upload.

        AutoDL / Ark generation tasks require publicly reachable URLs.
        If a local path is provided and no upload helper is configured,
        return None so the caller can surface a clear error.
        """
        return None
