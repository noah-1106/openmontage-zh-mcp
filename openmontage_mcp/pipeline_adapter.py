"""Pipeline and checkpoint adapter for the MCP server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lib.checkpoint import (
    get_completed_stages,
    get_next_stage,
    read_checkpoint,
    write_checkpoint,
)
from lib.config_model import OpenMontageConfig
from lib.pipeline_loader import list_pipelines, load_pipeline


class PipelineAdapter:
    """Wrap pipeline manifest and checkpoint operations for MCP callers."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = Path(project_dir)
        self.config = OpenMontageConfig.load(self.project_dir / "config.yaml")
        self.pipeline_dir = self.project_dir / self.config.paths.pipeline_dir

    def list_pipelines(self) -> list[str]:
        return list_pipelines()

    def get_pipeline_manifest(self, pipeline_type: str) -> dict[str, Any]:
        return load_pipeline(pipeline_type)

    def get_status(self, project_id: str, pipeline_type: str) -> dict[str, Any]:
        completed = get_completed_stages(self.pipeline_dir, project_id, pipeline_type)
        next_stage = get_next_stage(self.pipeline_dir, project_id, pipeline_type)
        latest = None
        for stage in reversed(get_completed_stages(self.pipeline_dir, project_id, pipeline_type) or []):
            cp = read_checkpoint(self.pipeline_dir, project_id, stage)
            if cp:
                latest = cp
                break

        return {
            "project_id": project_id,
            "pipeline_type": pipeline_type,
            "completed_stages": completed,
            "next_stage": next_stage,
            "latest_checkpoint": latest,
        }

    def write_stage_checkpoint(
        self,
        project_id: str,
        pipeline_type: str,
        stage: str,
        status: str,
        artifacts: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        path = write_checkpoint(
            pipeline_dir=self.pipeline_dir,
            project_id=project_id,
            stage=stage,
            status=status,
            artifacts=artifacts,
            pipeline_type=pipeline_type,
            **kwargs,
        )
        return {
            "checkpoint_path": str(path),
            "project_id": project_id,
            "pipeline_type": pipeline_type,
            "stage": stage,
            "status": status,
        }


def get_default_project_dir() -> Path:
    """Return the directory from which the MCP server was launched."""
    return Path.cwd()
