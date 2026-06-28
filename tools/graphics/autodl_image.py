"""AutoDL image generation via OpenAI-compatible /images/generations endpoint.

Supports models hosted on the AutoDL model marketplace, such as gpt-image-2.
"""

from __future__ import annotations

import base64
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


class AutoDLImage(BaseTool):
    name = "autodl_image"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
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
    agent_skills = ["flux-best-practices"]

    capabilities = ["generate_image", "generate_illustration", "text_to_image"]
    supports = {
        "complex_instructions": True,
        "text_in_image": True,
        "multiple_outputs": False,
    }
    best_for = [
        "domestic Chinese image generation through AutoDL",
        "OpenAI-compatible image endpoints hosted on AutoDL",
    ]
    not_good_for = ["offline generation", "non-AutoDL model endpoints"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "model": {
                "type": "string",
                "default": "gpt-image-2",
                "description": "AutoDL image model name",
            },
            "size": {
                "type": "string",
                "default": "1024x1024",
                "description": "Image size, e.g. 1024x1024",
            },
            "n": {"type": "integer", "default": 1, "minimum": 1, "maximum": 1},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=100, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "size", "model"]
    side_effects = ["writes image file to output_path", "calls AutoDL API"]
    user_visible_verification = ["Inspect generated image for relevance and quality"]

    def _get_api_key(self) -> str | None:
        return os.environ.get("AUTODL_API_KEY")

    def _get_base_url(self) -> str:
        return os.environ.get("AUTODL_BASE_URL", "https://www.autodl.art/api/v1")

    def get_status(self) -> ToolStatus:
        if self._get_api_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        # AutoDL pricing is per-call; exact cost is returned by the marketplace.
        # Use a conservative placeholder until pricing metadata is available.
        return 0.05

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = self._get_api_key()
        if not api_key:
            return ToolResult(
                success=False,
                error="AUTODL_API_KEY not set. " + self.install_instructions,
            )

        from openai import OpenAI

        start = time.time()
        base_url = self._get_base_url()
        client = OpenAI(base_url=base_url, api_key=api_key)

        model = inputs.get("model", "gpt-image-2")
        prompt = inputs["prompt"]
        size = inputs.get("size", "1024x1024")
        n = inputs.get("n", 1)

        try:
            response = client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                n=n,
                response_format="b64_json",
            )

            image_data = base64.b64decode(response.data[0].b64_json)
            output_path = Path(inputs.get("output_path", "autodl_image.png"))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(image_data)

        except Exception as e:
            return ToolResult(success=False, error=f"AutoDL image generation failed: {e}")

        return ToolResult(
            success=True,
            data={
                "provider": "autodl",
                "model": model,
                "prompt": prompt,
                "output": str(output_path),
            },
            artifacts=[str(output_path)],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            model=model,
        )
