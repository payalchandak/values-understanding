"""Command-line entry point for the values-understanding survey."""

from __future__ import annotations

import argparse
import sys

from values_understanding.prompts import (
    default_conditions,
    list_conditions,
    render_system_prompt,
)
from values_understanding.questions import (
    load_question,
    load_questions,
    render_user_prompt,
)
from values_understanding.run import Task, default_output_dir, run_tasks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Ask five-option survey questions under values-harness conditions."
        )
    )
    parser.add_argument("--list-questions", action="store_true")
    parser.add_argument("--list-conditions", action="store_true")
    parser.add_argument(
        "--question",
        action="append",
        help="Question id (repeatable). Default: every question.",
    )
    parser.add_argument(
        "--condition",
        action="append",
        help=(
            "Harness condition (repeatable). Default: control and all "
            "autonomy_primacy versions."
        ),
    )
    parser.add_argument(
        "--all-conditions",
        action="store_true",
        help="Use every condition in values-harness.",
    )
    parser.add_argument(
        "--model",
        action="append",
        help="OpenRouter model id (repeatable).",
    )
    parser.add_argument(
        "--reasoning-effort",
        default="high",
        help="Provider reasoning effort; pass an empty string to omit it.",
    )
    parser.add_argument("--output-dir", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered messages without calling a model.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace already-complete results.",
    )
    args = parser.parse_args(argv)

    if args.list_questions:
        for question in load_questions():
            print(question.id)
        return 0
    if args.list_conditions:
        for condition in list_conditions():
            print(condition)
        return 0

    questions = _select_questions(args.question)
    conditions = _select_conditions(args.condition, args.all_conditions)

    if args.dry_run:
        _print_dry_run(questions, conditions)
        return 0
    if not args.model:
        parser.error("--model is required unless --dry-run is used")

    from values_understanding.llm import LLM

    output_dir = args.output_dir or default_output_dir()
    failures = 0
    for model_id in args.model:
        client = LLM(
            model_id,
            reasoning_effort=args.reasoning_effort or None,
        )
        tasks = [
            Task(question, condition, model_id)
            for question in questions
            for condition in conditions
        ]
        try:
            run_tasks(tasks, client, output_dir, force=args.force)
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            failures += 1
    return 1 if failures else 0


def _select_questions(question_ids: list[str] | None):
    if question_ids is None:
        return list(load_questions())
    return [load_question(question_id) for question_id in question_ids]


def _select_conditions(
    requested: list[str] | None, all_conditions: bool
) -> list[str]:
    if requested and all_conditions:
        raise SystemExit("Pass either --condition or --all-conditions, not both")
    available = list_conditions()
    if all_conditions:
        return available
    if requested is None:
        return default_conditions()
    unknown = [condition for condition in requested if condition not in available]
    if unknown:
        raise SystemExit(
            f"Unknown condition(s): {', '.join(unknown)}. "
            "Use --list-conditions to see valid names."
        )
    return requested


def _print_dry_run(questions, conditions) -> None:
    for question in questions:
        print(f"# question: {question.id}")
        print(render_user_prompt(question))
        print()
    for condition in conditions:
        print(f"# condition: {condition}")
        print(render_system_prompt(condition))
        print()


if __name__ == "__main__":
    raise SystemExit(main())
