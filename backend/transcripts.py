"""Transcript capture: a complete record of one agent call, shared by live turns and eval trials."""

import glob
import json
import os
import secrets
from datetime import datetime, timezone


def new_transcript_id() -> str:
    """Generate a short random identifier for a transcript."""
    return secrets.token_hex(8)


def _serialize_block(block) -> dict:
    """Convert one Anthropic content block (or plain dict) into a JSON-safe dict."""
    if isinstance(block, dict):
        return block

    if block.type == "text":
        return {"type": "text", "text": block.text}

    if block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}

    return {"type": getattr(block, "type", "unknown")}


def serialize_messages(messages: list[dict]) -> list[dict]:
    """Convert a messages list (str or Anthropic content-block content) into JSON-safe dicts."""
    serialized = []
    for message in messages:
        content = message["content"]
        if isinstance(content, str):
            serialized.append({"role": message["role"], "content": content})
        else:
            serialized.append({"role": message["role"], "content": [_serialize_block(b) for b in content]})
    return serialized


def extract_steps(serialized_messages: list[dict]) -> list[dict]:
    """Pair tool_use blocks with their tool_result by tool_use_id, in call order.

    A tool_use with no matching tool_result (e.g. the coordinator's forced
    `route` call, which is never sent back as a tool result) becomes a step
    with result=None.
    """
    tool_uses = {}
    steps = []
    resolved = set()
    for message in serialized_messages:
        content = message["content"]
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") == "tool_use":
                tool_uses[block["id"]] = {"name": block["name"], "input": block["input"]}
            elif block.get("type") == "tool_result":
                tool_use = tool_uses.get(block["tool_use_id"], {})
                steps.append({
                    "name": tool_use.get("name"),
                    "input": tool_use.get("input"),
                    "result": block.get("content"),
                })
                resolved.add(block["tool_use_id"])

    for tool_use_id, tool_use in tool_uses.items():
        if tool_use_id not in resolved:
            steps.append({"name": tool_use["name"], "input": tool_use["input"], "result": None})

    return steps


def build_transcript(
    *,
    agent_type: str,
    model: str,
    system: str,
    inputs: list[dict],
    history: list[dict],
    output: str,
    outcome: dict,
    usage: dict,
    latency_ms: int,
    agent_invoked: str | None = None,
) -> dict:
    """Assemble a Transcript dict from one agent call's inputs and final state."""
    serialized_history = serialize_messages(history)
    return {
        "transcript_id": new_transcript_id(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "agent_type": agent_type,
        "agent_invoked": agent_invoked,
        "model": model,
        "system": system,
        "inputs": serialize_messages(inputs),
        "messages": serialized_history,
        "steps": extract_steps(serialized_history),
        "output": output,
        "outcome": outcome,
        "usage": usage,
        "latency_ms": latency_ms,
    }


def write_transcript(transcript: dict, dir: str = "transcripts", filename: str | None = None) -> str:
    """Append a Transcript as one JSON line to dir/filename (default dir/<date>.jsonl). Returns the path."""
    os.makedirs(dir, exist_ok=True)
    if filename is None:
        filename = transcript["created_at"][:10] + ".jsonl"
    path = os.path.join(dir, filename)
    with open(path, "a") as f:
        f.write(json.dumps(transcript) + "\n")
    return path


def read_transcripts(path: str, filters: dict | None = None) -> list[dict]:
    """Read Transcript records from a JSONL file or a directory of them, optionally filtered by exact field match."""
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "*.jsonl")))
    else:
        files = [path]

    transcripts = []
    for file in files:
        if not os.path.exists(file):
            continue
        with open(file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                transcripts.append(json.loads(line))

    if filters:
        transcripts = [
            t for t in transcripts
            if all(t.get(key) == value for key, value in filters.items())
        ]

    transcripts.sort(key=lambda t: t.get("created_at", ""))
    return transcripts


def promote_to_task(transcript: dict) -> dict:
    """Turn a captured Transcript into a Task scaffold for the eval harness."""
    return {
        "id": f"from_{transcript['transcript_id']}",
        "description": f"Promoted from a captured {transcript['agent_type']} transcript ({transcript['transcript_id']})",
        "inputs": transcript.get("inputs", []),
        "profile": {},
        "success_criteria": "TODO: describe expected behavior based on this transcript",
        "graders": [],
        "source": f"transcript:{transcript['transcript_id']}",
    }
