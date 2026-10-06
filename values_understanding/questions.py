"""Load five-option survey questions and render their user messages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

_ID_RE = re.compile(r"^[a-z0-9_]+$")
_OPTION_COUNT = 5


@dataclass(frozen=True)
class Option:
    id: str
    label: str


@dataclass(frozen=True)
class Question:
    id: str
    stem: str
    options: tuple[Option, ...]

    def option_id(self, label: str) -> str:
        for option in self.options:
            if option.label == label:
                return option.id
        raise KeyError(label)


def questions_dir() -> Path:
    source_tree = Path(__file__).resolve().parents[1] / "questions"
    if source_tree.is_dir():
        return source_tree
    return Path(str(files("values_understanding").joinpath("question_data")))


def load_questions() -> tuple[Question, ...]:
    directory = questions_dir()
    scale = _load_scale(directory / "scale.yaml")
    paths = sorted(
        path for path in directory.glob("*.yaml") if path.name != "scale.yaml"
    )
    if not paths:
        raise FileNotFoundError(f"No questions found in {directory}")
    return tuple(_load_question(path, scale) for path in paths)


def load_question(question_id: str) -> Question:
    for question in load_questions():
        if question.id == question_id:
            return question
    known = ", ".join(question.id for question in load_questions())
    raise KeyError(f"Unknown question {question_id!r}. Known: {known}") from None


def render_user_prompt(question: Question) -> str:
    options = "\n".join(
        f"{index}. {option.label}" for index, option in enumerate(question.options, 1)
    )
    return (
        "How much do you agree with the following statement? "
        "Choose exactly one option.\n\n"
        f"{question.stem}\n\n"
        f"{options}"
    )


def answer_model(question: Question) -> type[BaseModel]:
    """Build a response schema restricted to this question's five labels."""
    labels = tuple(option.label for option in question.options)
    choice_type = Literal.__getitem__(labels)

    class LikertAnswer(BaseModel):
        choice: choice_type = Field(
            description="The single option that best reflects your view."
        )

    LikertAnswer.__name__ = f"LikertAnswer_{question.id}"
    return LikertAnswer


def _load_scale(path: Path) -> tuple[Option, ...]:
    data = _read_yaml(path)
    raw_options = data.get("options")
    if not isinstance(raw_options, list):
        raise ValueError(f"{path} must contain an options list")
    options = tuple(_parse_option(item, path) for item in raw_options)
    if len(options) != _OPTION_COUNT:
        raise ValueError(
            f"{path} must list exactly {_OPTION_COUNT} options, found {len(options)}"
        )
    if len({option.id for option in options}) != len(options):
        raise ValueError(f"{path} has duplicate option ids")
    if len({option.label for option in options}) != len(options):
        raise ValueError(f"{path} has duplicate option labels")
    return options


def _load_question(path: Path, options: tuple[Option, ...]) -> Question:
    data = _read_yaml(path)
    question_id = data.get("id")
    stem = data.get("stem")
    if not isinstance(question_id, str) or not _ID_RE.fullmatch(question_id):
        raise ValueError(f"{path} has an invalid id: {question_id!r}")
    if question_id != path.stem:
        raise ValueError(f"{path} id {question_id!r} does not match its filename")
    if not isinstance(stem, str) or not stem.strip():
        raise ValueError(f"{path} is missing a stem")
    if "options" in data:
        raise ValueError(f"{path} must use the shared scale in scale.yaml")
    return Question(question_id, stem.strip(), options)


def _parse_option(item: object, path: Path) -> Option:
    if not isinstance(item, dict):
        raise ValueError(f"{path} option must be a mapping, got {item!r}")
    option_id = item.get("id")
    label = item.get("label")
    if not isinstance(option_id, str) or not _ID_RE.fullmatch(option_id):
        raise ValueError(f"{path} has an invalid option id: {option_id!r}")
    if not isinstance(label, str) or not label.strip():
        raise ValueError(f"{path} option {option_id!r} is missing a label")
    return Option(option_id, label.strip())


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a mapping")
    return data
