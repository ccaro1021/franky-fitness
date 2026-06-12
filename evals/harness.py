"""Eval harness: run Tasks x k trials through run_coordinator, grade outcomes, report pass@k/pass^k.

    python -m evals.harness --trials 3
    python -m evals.harness --trials 3 --task meal_high_protein

Each trial runs run_coordinator() directly (DB-free, no prod writes) against a
fresh copy of the task's inputs and synthetic profile. Every trial's Transcript
is written to evals/results/<timestamp>/<task_id>-trial<n>.jsonl.
"""

import argparse
import copy
import time

from backend.coordinator import run_coordinator
from backend.transcripts import write_transcript
from evals.tasks import TASKS, get_task

RESULTS_DIR = "evals/results"


def run_trial(task: dict) -> tuple[dict, list[dict]]:
    """Run one trial of a task. Returns (transcript, grader_results)."""
    messages = copy.deepcopy(task["inputs"])
    profile = copy.deepcopy(task["profile"])

    result = run_coordinator(
        messages,
        profile,
        current_meal_plan=task.get("current_meal_plan"),
        current_workout_plan=task.get("current_workout_plan"),
        preference_summary=None,
    )

    transcript = result["transcript"]
    grader_results = [grader(transcript) for grader in task["graders"]]
    return transcript, grader_results


def run_task(task: dict, trials: int, results_dir: str) -> dict:
    """Run `trials` trials of a task. Returns {task_id, trial_results, pass_at_k, pass_pow_k}."""
    trial_results = []
    for i in range(trials):
        agent_runs_transcripts = []
        try:
            transcript, grader_results = run_trial(task)
            agent_runs_transcripts.append(transcript)
            passed = all(g["passed"] for g in grader_results)
        except Exception as e:
            grader_results = [{"assertion": "trial_ran", "passed": False, "reasoning": f"trial raised: {e}"}]
            passed = False

        for transcript in agent_runs_transcripts:
            write_transcript(transcript, dir=results_dir, filename=f"{task['id']}-trial{i + 1}.jsonl")

        trial_results.append({"trial": i + 1, "passed": passed, "graders": grader_results})

    pass_at_k = any(t["passed"] for t in trial_results)
    pass_pow_k = all(t["passed"] for t in trial_results)

    return {
        "task_id": task["id"],
        "trial_results": trial_results,
        "pass_at_k": pass_at_k,
        "pass_pow_k": pass_pow_k,
    }


def print_summary(task_summaries: list[dict], trials: int) -> None:
    print(f"\n{'task':<28} {'pass@' + str(trials):<10} {'pass^' + str(trials):<10}")
    print("-" * 50)
    for summary in task_summaries:
        pass_at = "PASS" if summary["pass_at_k"] else "FAIL"
        pass_pow = "PASS" if summary["pass_pow_k"] else "FAIL"
        print(f"{summary['task_id']:<28} {pass_at:<10} {pass_pow:<10}")

        for trial in summary["trial_results"]:
            status = "PASS" if trial["passed"] else "FAIL"
            print(f"  trial {trial['trial']}: {status}")
            for g in trial["graders"]:
                mark = "ok" if g["passed"] else "FAIL"
                print(f"    [{mark}] {g['assertion']}: {g['reasoning']}")

    print("-" * 50)
    overall_at = sum(1 for s in task_summaries if s["pass_at_k"]) / len(task_summaries)
    overall_pow = sum(1 for s in task_summaries if s["pass_pow_k"]) / len(task_summaries)
    print(f"{'OVERALL':<28} {overall_at:<10.0%} {overall_pow:<10.0%}")


def main():
    parser = argparse.ArgumentParser(description="Run the Franky eval harness")
    parser.add_argument("--trials", type=int, default=3, help="Number of trials (k) per task")
    parser.add_argument("--task", help="Run only this task id")
    args = parser.parse_args()

    tasks = [get_task(args.task)] if args.task else TASKS

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    results_dir = f"{RESULTS_DIR}/{timestamp}"

    task_summaries = []
    for task in tasks:
        print(f"Running {task['id']} ({args.trials} trials)...")
        task_summaries.append(run_task(task, args.trials, results_dir))

    print_summary(task_summaries, args.trials)
    print(f"\nTranscripts written to {results_dir}/")


if __name__ == "__main__":
    main()
