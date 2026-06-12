"""CLI to inspect captured agent transcripts from transcripts/*.jsonl."""

import argparse
import json

from backend.transcripts import read_transcripts

TRANSCRIPTS_DIR = "transcripts"


def _print_message_content(content) -> None:
    """Print one message's content, handling plain-text and content-block forms."""
    if isinstance(content, str):
        print(f"    {content}")
        return
    for block in content:
        if block["type"] == "text":
            print(f"    text: {block['text']}")
        elif block["type"] == "tool_use":
            print(f"    tool_use: {block['name']}({json.dumps(block['input'])})")
        elif block["type"] == "tool_result":
            print(f"    tool_result[{block['tool_use_id']}]: {block['content']}")
        else:
            print(f"    {block}")


def print_transcript(transcript: dict) -> None:
    """Pretty-print one Transcript record to stdout."""
    print("=" * 80)
    print(f"transcript_id: {transcript['transcript_id']}")
    print(f"created_at:    {transcript['created_at']}")
    print(f"agent_type:    {transcript['agent_type']}")
    print(f"agent_invoked: {transcript['agent_invoked']}")
    print(f"model:         {transcript['model']}")
    print(f"usage:         {transcript['usage']}")
    print(f"latency_ms:    {transcript['latency_ms']}")

    print("-" * 80)
    print("SYSTEM PROMPT:")
    print(transcript["system"])

    print("-" * 80)
    print("MESSAGES:")
    for message in transcript["messages"]:
        print(f"  [{message['role']}]")
        _print_message_content(message["content"])

    print("-" * 80)
    print("TOOL CALLS:")
    if transcript["steps"]:
        for step in transcript["steps"]:
            print(f"  {step['name']}({json.dumps(step['input'])})")
            print(f"    -> {step['result']}")
    else:
        print("  (none)")

    print("-" * 80)
    print("OUTPUT:")
    print(f"  {transcript['output']}")
    print("OUTCOME:")
    print(f"  {transcript['outcome']}")


def main():
    parser = argparse.ArgumentParser(description="View captured agent transcripts")
    parser.add_argument("--last", type=int, help="Show only the N most recent matching transcripts")
    parser.add_argument("--agent", help="Filter by agent_type (coordinator, meal_agent, exercise_agent)")
    parser.add_argument("--invoked", help="Filter by agent_invoked (meal, exercise)")
    parser.add_argument("--id", dest="transcript_id", help="Show the transcript with this transcript_id")
    parser.add_argument("--dir", default=TRANSCRIPTS_DIR, help="Directory of transcript JSONL files")
    args = parser.parse_args()

    filters = {}
    if args.agent:
        filters["agent_type"] = args.agent
    if args.invoked:
        filters["agent_invoked"] = args.invoked
    if args.transcript_id:
        filters["transcript_id"] = args.transcript_id

    transcripts = read_transcripts(args.dir, filters or None)

    if args.last:
        transcripts = transcripts[-args.last:]

    if not transcripts:
        print("No matching transcripts found.")
        return

    for transcript in transcripts:
        print_transcript(transcript)


if __name__ == "__main__":
    main()
