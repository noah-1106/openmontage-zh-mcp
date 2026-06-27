#!/usr/bin/env python3
"""Quick smoke test for OpenMontage MCP server over stdio."""

import json
import subprocess
import sys


def notify(stdin, msg: dict) -> None:
    payload = json.dumps(msg) + "\n"
    stdin.write(payload.encode())
    stdin.flush()


def send(stdin, stdout, msg: dict) -> dict:
    payload = json.dumps(msg) + "\n"
    stdin.write(payload.encode())
    stdin.flush()
    line = stdout.readline().decode()
    return json.loads(line)


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, "-m", "openmontage_mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        cwd="/Users/tannoah/Project/openmontage/OpenMontage-main",
    )

    init = send(proc.stdin, proc.stdout, {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "smoke-test", "version": "0.1.0"},
        },
    })
    print("INIT:", json.dumps(init, indent=2))

    notify(proc.stdin, {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
    })

    tools = send(proc.stdin, proc.stdout, {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
    })
    print("TOOLS COUNT:", len(tools.get("result", {}).get("tools", [])))
    names = [t["name"] for t in tools.get("result", {}).get("tools", [])]
    print("TOOL NAMES (first 10):", names[:10])

    caps = send(proc.stdin, proc.stdout, {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "list_capabilities", "arguments": {}},
    })
    print("CAPABILITIES:", json.dumps(caps, indent=2)[:2000])

    sub = send(proc.stdin, proc.stdout, {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "subtitle_gen",
            "arguments": {
                "segments": [
                    {"text": "Hello world", "start": 0.0, "end": 1.5,
                     "words": [{"word": "Hello", "start": 0.0, "end": 0.7},
                               {"word": "world", "start": 0.8, "end": 1.5}]}
                ],
                "format": "srt",
                "output_path": "projects/demos/renders/smoke_test.srt",
            },
        },
    })
    print("SUBTITLE:", json.dumps(sub, indent=2))

    deferred = send(proc.stdin, proc.stdout, {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "run_tool",
            "arguments": {
                "name": "subtitle_gen",
                "inputs": {
                    "segments": [
                        {"text": "Deferred job", "start": 0.0, "end": 1.0,
                         "words": [{"word": "Deferred", "start": 0.0, "end": 0.5},
                                   {"word": "job", "start": 0.5, "end": 1.0}]}
                    ],
                    "format": "srt",
                    "output_path": "projects/demos/renders/smoke_deferred.srt",
                },
                "defer": True,
            },
        },
    })
    print("DEFERRED JOB:", json.dumps(deferred, indent=2))
    job_id = json.loads(deferred["result"]["content"][0]["text"]).get("job_id")

    status = send(proc.stdin, proc.stdout, {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {"name": "get_job_status", "arguments": {"job_id": job_id}},
    })
    print("JOB STATUS:", json.dumps(status, indent=2))

    proc.stdin.close()
    proc.wait(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
