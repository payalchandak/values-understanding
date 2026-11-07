"""Run questions under selected values-harness conditions."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from values_understanding.prompts import render_system_prompt
from values_understanding.questions import (
    Question,
    answer_model,
    load_questions,
    render_user_prompt,
)


@dataclass(frozen=True)
class Task:
    question: Question
    condition: str
    model_id: str
    trial: int = 1


@dataclass(frozen=True)
class ResultSummary:
    model_id: str
    condition: str
    mean_score: float
    n: int


def sanitize_model_id(model_id: str) -> str:
    return model_id.replace("/", "__")


def default_output_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "results"


def result_path(output_dir: str | Path, task: Task) -> Path:
    model_name = sanitize_model_id(task.model_id)
    filename = (
        f"{model_name}.json"
        if task.trial == 1
        else f"{model_name}__trial_{task.trial:02d}.json"
    )
    return (
        Path(output_dir)
        / task.question.id
        / task.condition
        / filename
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
    threads: int = 250,
) -> list[Path]:
    """Write one self-contained JSON result per question/condition/model."""
    if threads < 1:
        raise ValueError("threads must be at least 1")

    written: list[Path] = []
    pending: list[tuple[int, Task, Path]] = []
    for index, task in enumerate(tasks, start=1):
        path = result_path(output_dir, task)
        if path.exists() and not force and _is_complete(path):
            print(
                f"[{index}/{len(tasks)}] skip "
                f"{task.question.id} / {task.condition} / "
                f"{task.model_id} / trial {task.trial}"
            )
            continue
        pending.append((index, task, path))

    failures = 0
    with ThreadPoolExecutor(max_workers=min(threads, len(pending) or 1)) as pool:
        futures = {
            pool.submit(_run_one, task, client, path): (index, task, path)
            for index, task, path in pending
        }
        for future in as_completed(futures):
            index, task, path = futures[future]
            succeeded, detail = future.result()
            print(
                f"[{index}/{len(tasks)}] "
                f"{task.question.id} / {task.condition} / "
                f"{task.model_id} / trial {task.trial}: {detail}"
            )
            if not succeeded:
                failures += 1
            written.append(path)

    if failures:
        raise RuntimeError(f"{failures} task(s) failed; error records were written")
    return written


def _run_one(task: Task, client, path: Path) -> tuple[bool, str]:
    system_text, user_text, messages = build_messages(
        task.question, task.condition
    )
    try:
        parsed, raw = client.ask(messages, answer_model(task.question))
        choice_label = parsed.choice
        record = {
            "question_id": task.question.id,
            "condition": task.condition,
            "trial": task.trial,
            "system_prompt": system_text,
            "user_prompt": user_text,
            "model": task.model_id,
            "choice_id": task.question.option_id(choice_label),
            "choice_label": choice_label,
            "score": task.question.option_score(choice_label),
            "response": raw,
            "error": None,
        }
        succeeded = True
        detail = choice_label
    except Exception as exc:
        record = {
            "question_id": task.question.id,
            "condition": task.condition,
            "trial": task.trial,
            "system_prompt": system_text,
            "user_prompt": user_text,
            "model": task.model_id,
            "choice_id": None,
            "choice_label": None,
            "score": None,
            "response": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
        succeeded = False
        detail = f"error: {record['error']}"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n")
    return succeeded, detail


def summarize_results(
    output_dir: str | Path,
    *,
    model_ids: list[str] | None = None,
) -> list[ResultSummary]:
    """Compute a mean Likert score for each model and condition."""
    score_by_choice_id = {
        option.id: option.score
        for option in load_questions()[0].options
    }
    selected_models = set(model_ids) if model_ids else None
    grouped: dict[tuple[str, str], list[int]] = {}

    for path in Path(output_dir).rglob("*.json"):
        try:
            record = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        model_id = record.get("model")
        condition = record.get("condition")
        if not isinstance(model_id, str) or not isinstance(condition, str):
            continue
        if selected_models is not None and model_id not in selected_models:
            continue
        if record.get("error") is not None:
            continue
        score = record.get("score")
        if not isinstance(score, int) or isinstance(score, bool):
            score = score_by_choice_id.get(record.get("choice_id"))
        if score is None:
            continue
        grouped.setdefault((model_id, condition), []).append(score)

    return [
        ResultSummary(
            model_id=model_id,
            condition=condition,
            mean_score=sum(scores) / len(scores),
            n=len(scores),
        )
        for (model_id, condition), scores in sorted(grouped.items())
    ]


def _is_complete(path: Path) -> bool:
    try:
        record = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return record.get("error") is None and bool(record.get("choice_id"))
