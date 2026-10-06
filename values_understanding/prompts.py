"""Resolve system prompts from the installed values-harness prompt tree."""

from __future__ import annotations

from values_harness.prompt_manager import PromptManager
from values_harness.prompts import PROMPTS_ROOT


def list_conditions() -> list[str]:
    """List every harness condition, including nested family/version names."""
    conditions_dir = PROMPTS_ROOT / "conditions"
    return sorted(
        path.parent.relative_to(conditions_dir).as_posix()
        for path in conditions_dir.rglob("system.md")
    )


def default_conditions() -> list[str]:
    """The unsteered control and every autonomy-primacy steering condition."""
    available = list_conditions()
    autonomy_conditions = [
        name
        for name in available
        if name.startswith("autonomy_primacy/")
    ]
    if "control" not in available:
        raise ValueError("The values-harness prompt tree has no control condition")
    if not autonomy_conditions:
        raise ValueError(
            "The values-harness prompt tree has no autonomy_primacy conditions"
        )
    return ["control", *autonomy_conditions]


def render_system_prompt(condition: str) -> str:
    """Render a condition using the harness prompt manager and tree layout."""
    conditions_dir = (PROMPTS_ROOT / "conditions").resolve()
    condition_dir = (conditions_dir / condition).resolve()
    if not condition_dir.is_relative_to(conditions_dir):
        raise ValueError(f"Invalid condition name: {condition!r}")
    if not (condition_dir / "system.md").is_file():
        raise ValueError(f"Unknown values-harness condition: {condition!r}")
    manager = PromptManager(
        [str(condition_dir), str(PROMPTS_ROOT / "shared")]
    )
    return manager.render("system.md", {})
