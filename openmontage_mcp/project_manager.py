"""Project workspace manager for MCP layer.

Provides a thin, stable interface over the OpenMontage project directory
conventions and checkpoint system. The MCP server uses this to resolve
project-relative paths and read/write project state without leaking
implementation details to LLM callers.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PROJECTS_DIR = Path("projects")


def sanitize_project_id(title: str) -> str:
    """Convert a human-readable title into a kebab-case project id."""
    base = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE)
    base = re.sub(r"[-\s]+", "-", base.strip()).lower()
    base = base.strip("-")
    return base or "untitled"


def get_project_dir(project_id: str) -> Path:
    """Return the workspace directory for a project id."""
    return PROJECTS_DIR / project_id


def ensure_project_dirs(project_id: str) -> Path:
    """Create the standard project subdirectories if they do not exist."""
    project_dir = get_project_dir(project_id)
    for sub in ("artifacts", "assets/images", "assets/video", "assets/audio", "assets/music", "renders"):
        (project_dir / sub).mkdir(parents=True, exist_ok=True)
    return project_dir


def create_project(title: str, pipeline: str, brief: str | None = None) -> dict[str, Any]:
    """Create a new OpenMontage project workspace.

    Returns project metadata including the canonical paths.
    """
    from lib.checkpoint import get_pipeline_stages

    project_id = sanitize_project_id(title)
    project_dir = ensure_project_dirs(project_id)

    # If id already exists, append a counter to avoid collision.
    counter = 1
    original_id = project_id
    while (project_dir / "project.json").exists():
        project_id = f"{original_id}-{counter}"
        project_dir = ensure_project_dirs(project_id)
        counter += 1

    stages = get_pipeline_stages(pipeline)
    metadata = {
        "project_id": project_id,
        "title": title,
        "pipeline": pipeline,
        "brief": brief or "",
        "stages": stages,
        "created_at": _utc_now(),
    }
    (project_dir / "project.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "project_id": project_id,
        "project_dir": str(project_dir),
        "pipeline": pipeline,
        "stages": stages,
        "next_stage": stages[0] if stages else None,
    }


def get_project_status(project_id: str) -> dict[str, Any]:
    """Read project metadata and checkpoint state."""
    from lib.checkpoint import get_completed_stages, get_next_stage

    project_dir = get_project_dir(project_id)
    if not project_dir.exists():
        return {"error": f"project {project_id} not found"}

    metadata_path = project_dir / "project.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}

    pipeline_type = metadata.get("pipeline")
    pipeline_dir = _pipeline_dir()
    completed = get_completed_stages(pipeline_dir, project_id, pipeline_type)
    next_stage = get_next_stage(pipeline_dir, project_id, pipeline_type)

    pending_human = []
    for stage in completed:
        cp_path = pipeline_dir / project_id / f"checkpoint_{stage}.json"
        if cp_path.exists():
            cp = json.loads(cp_path.read_text(encoding="utf-8"))
            if cp.get("status") == "awaiting_human":
                pending_human.append(stage)

    return {
        "project_id": project_id,
        "project_dir": str(project_dir),
        "pipeline": pipeline_type,
        "title": metadata.get("title"),
        "completed_stages": completed,
        "current_stage": next_stage,
        "pending_human_approvals": pending_human,
        "stages": metadata.get("stages", []),
    }


def resolve_project_path(project_id: str | None, path: str | None) -> str | None:
    """Resolve a path that may be relative to a project workspace.

    If project_id is given and path is relative, prepend projects/<id>/.
    """
    if path is None:
        return None
    if project_id is None:
        return path
    if Path(path).is_absolute():
        return path
    return str(get_project_dir(project_id) / path)


def read_project_artifact(project_id: str, artifact_name: str) -> dict[str, Any] | None:
    """Read a canonical artifact JSON from the project workspace."""
    project_dir = get_project_dir(project_id)
    candidates = [
        project_dir / "artifacts" / f"{artifact_name}.json",
        project_dir / f"{artifact_name}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    return None


def write_checkpoint(
    project_id: str,
    stage: str,
    status: str,
    artifacts: dict[str, Any],
    pipeline_type: str | None = None,
    human_approval_required: bool = False,
    human_approved: bool = False,
) -> dict[str, Any]:
    """Write a checkpoint for a pipeline stage."""
    from lib.checkpoint import write_checkpoint as _write_checkpoint

    project_dir = get_project_dir(project_id)
    if not project_dir.exists():
        return {"error": f"project {project_id} not found"}

    metadata_path = project_dir / "project.json"
    if pipeline_type is None and metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        pipeline_type = metadata.get("pipeline")

    try:
        _write_checkpoint(
            pipeline_dir=_pipeline_dir(),
            project_id=project_id,
            stage=stage,
            status=status,
            artifacts=artifacts,
            pipeline_type=pipeline_type,
            human_approval_required=human_approval_required,
            human_approved=human_approved,
        )
    except Exception as exc:
        return {"error": f"failed to write checkpoint: {exc}"}

    return {
        "project_id": project_id,
        "stage": stage,
        "status": status,
        "next_stage": get_project_status(project_id).get("current_stage"),
    }


def _pipeline_dir() -> Path:
    from lib.config_model import OpenMontageConfig
    cfg = OpenMontageConfig.load(Path("config.yaml"))
    return Path(cfg.paths.pipeline_dir)


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
