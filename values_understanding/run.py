"""Run questions under selected values-harness conditions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from values_understanding.prompts import render_system_prompt
from values_understanding.questions import Question, answer_model, render_user_prompt


@dataclass(frozen=True)
class Task:
    question: Question
    condition: str
    model_id: str


def sanitize_model_id(model_id: str) -> str:
    return model_id.replace("/", "__")


def default_output_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "results"


def result_path(output_dir: str | Path, task: Task) -> Path:
    return (
        Path(output_dir)
        / task.question.id
        / task.condition
        / f"{sanitize_model_id(task.model_id)}.json"
    )


def build_messages(
    question: Question, condition: str
) -> tuple[str, str, list[dict]]:
    system_text = render_system_prompt(condition)
    user_text = render_user_prompt(question)
    messages = [
        {"role": "system", "content": system_text},
        {"role": "user", "content": user_text},
    ]
    return system_text, user_text, messages


def run_tasks(
    tasks: list[Task],
    client,
    output_dir: str | Path,
    *,
    force: bool = False,
) -> list[Path]:
    """Write one self-contained JSON result per question/condition/model."""
    written: list[Path] = []
    failures = 0

    for index, task in enumerate(tasks, start=1):
        path = result_path(output_dir, task)
        if path.exists() and not force and _is_complete(path):
            print(
                f"[{index}/{len(tasks)}] skip "
                f"{task.question.id} / {task.condition} / {task.model_id}"
            )
            continue

        system_text, user_text, messages = build_messages(
            task.question, task.condition
        )
        print(
            f"[{index}/{len(tasks)}] "
            f"{task.question.id} / {task.condition} / {task.model_id}"
        )
        try:
            parsed, raw = client.ask(messages, answer_model(task.question))
            choice_label = parsed.choice
            record = {
                "question_id": task.question.id,
                "condition": task.condition,
                "system_prompt": system_text,
                "user_prompt": user_text,
                "model": task.model_id,
                "choice_id": task.question.option_id(choice_label),
                "choice_label": choice_label,
                "response": raw,
                "error": None,
            }
            print(f"  {choice_label}")
        except Exception as exc:
            failures += 1
            record = {
                "question_id": task.question.id,
                "condition": task.condition,
                "system_prompt": system_text,
                "user_prompt": user_text,
                "model": task.model_id,
                "choice_id": None,
                "choice_label": None,
                "response": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
            print(f"  error: {record['error']}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2) + "\n")
        written.append(path)

    if failures:
        raise RuntimeError(f"{failures} task(s) failed; error records were written")
    return written


def _is_complete(path: Path) -> bool:
    try:
        record = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return record.get("error") is None and bool(record.get("choice_id"))
