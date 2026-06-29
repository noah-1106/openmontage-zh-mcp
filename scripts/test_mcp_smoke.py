"""Full MCP smoke test: create project, run autodl_video through MCP, poll, render."""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ID = "mcp-smoke-test"


async def main() -> None:
    params = StdioServerParameters(
        command="python3",
        args=["-m", "openmontage_mcp.server", "--project-dir", str(Path.cwd())],
        env=None,
    )

    # Clean up any prior test project
    shutil.rmtree(f"projects/{PROJECT_ID}", ignore_errors=True)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. list capabilities
            cap = await session.call_tool("list_capabilities", {"category": "video_generation"})
            data = json.loads(cap.content[0].text)
            autodl_schema = next((t for t in data["tools"] if t["name"] == "autodl_video"), None)
            assert autodl_schema, "autodl_video schema not found"
            print("1. list_capabilities OK")

            # 2. create project
            create = await session.call_tool(
                "create_project",
                {"title": "MCP Smoke Test", "pipeline": "animated-explainer", "brief": "test"},
            )
            proj = json.loads(create.content[0].text)
            assert proj["project_id"] == PROJECT_ID
            print(f"2. create_project OK: {proj['project_id']}")

            # 3. get_project_status
            status = await session.call_tool("get_project_status", {"project_id": PROJECT_ID})
            status_data = json.loads(status.content[0].text)
            assert status_data["current_stage"] == "research"
            print(f"3. get_project_status OK: current_stage={status_data['current_stage']}")

            # 4. run_tool autodl_video create task (should auto-defer)
            run = await session.call_tool(
                "run_tool",
                {
                    "name": "autodl_video",
                    "project_id": PROJECT_ID,
                    "inputs": {
                        "prompt": "A serene mountain lake at sunrise, gentle mist rising, cinematic wide shot",
                        "model": "doubao-seedance-2-0-260128",
                        "operation": "text_to_video",
                        "duration": 5,
                        "aspect_ratio": "16:9",
                        "resolution": "720p",
                        "output_path": "assets/video/clip_01.mp4",
                    },
                },
            )
            run_data = json.loads(run.content[0].text)
            assert run_data["status"] == "queued", f"expected queued, got {run_data}"
            job_id = run_data["job_id"]
            print(f"4. run_tool autodl_video queued OK: job_id={job_id}")

            # 5. poll create job until done
            while True:
                await asyncio.sleep(2)
                poll = await session.call_tool("get_job_status", {"job_id": job_id})
                state = json.loads(poll.content[0].text)
                print(f"   create job poll: status={state.get('status')}")
                if state.get("status") in ("completed", "failed"):
                    break
            assert state.get("status") == "completed", f"create job failed: {state}"
            task_id = state["data"]["task_id"]
            print(f"5. create job completed OK: task_id={task_id}")

            # 6. poll autodl get_status until video ready
            video_job_id = None
            for i in range(50):
                poll2 = await session.call_tool(
                    "run_tool",
                    {
                        "name": "autodl_video",
                        "project_id": PROJECT_ID,
                        "inputs": {
                            "operation": "get_status",
                            "task_id": task_id,
                            "output_path": "assets/video/clip_01.mp4",
                        },
                    },
                )
                status_data = json.loads(poll2.content[0].text)
                inner_status = status_data.get("data", {}).get("status")
                print(f"   get_status poll {i+1}: status={inner_status}")
                if status_data.get("status") == "error":
                    raise RuntimeError(f"get_status error: {status_data}")
                if inner_status == "succeeded":
                    video_job_id = status_data.get("data", {}).get("output")
                    break
                await asyncio.sleep(10)
            assert video_job_id, "video did not complete"
            print(f"6. autodl video succeeded: {video_job_id}")

            # 7. list_jobs
            jobs = await session.call_tool("list_jobs", {})
            jobs_data = json.loads(jobs.content[0].text)
            print(f"7. list_jobs OK: {len(jobs_data['jobs'])} jobs")

            # 8. render_video (will fail without edit_decisions/asset_manifest, but verifies path)
            render = await session.call_tool("render_video", {"project_id": PROJECT_ID})
            render_data = json.loads(render.content[0].text)
            print(f"8. render_video response: {render_data.get('status')} / {render_data.get('code', 'no code')}")

            print("\nAll MCP smoke checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
