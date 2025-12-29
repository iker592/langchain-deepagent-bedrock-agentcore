import re
from dataclasses import dataclass


@dataclass
class GEvalConfig:
    name: str
    criteria: str
    evaluation_steps: list[str]


@dataclass
class RubricConfig:
    geval: GEvalConfig | None = None
    task_completion_criteria: str | None = None


def _parse_numbered_steps(lines: list[str]) -> list[str]:
    steps = []
    current_step_lines = []

    for line in lines:
        stripped = line.strip()
        step_match = re.match(r"^\d+\.\s*(.+)$", stripped)
        if step_match:
            if current_step_lines:
                steps.append(" ".join(current_step_lines))
            current_step_lines = [step_match.group(1)]
        elif stripped and current_step_lines:
            current_step_lines.append(stripped)

    if current_step_lines:
        steps.append(" ".join(current_step_lines))

    return steps


def parse_rubric_markdown(markdown_content: str) -> RubricConfig:
    lines = markdown_content.strip().split("\n")

    geval_name = None
    geval_criteria_lines = []
    geval_steps_lines = []
    task_criteria_lines = []

    current_section = None
    current_subsection = None

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("# "):
            continue

        if stripped.startswith("## "):
            section_name = stripped[3:].strip().lower()
            if "geval" in section_name:
                current_section = "geval"
            elif "task" in section_name:
                current_section = "task"
            else:
                current_section = None
            current_subsection = None
            continue

        if stripped.startswith("### "):
            subsection_name = stripped[4:].strip().lower()
            if "name" in subsection_name:
                current_subsection = "name"
            elif "criteria" in subsection_name:
                current_subsection = "criteria"
            elif "step" in subsection_name:
                current_subsection = "steps"
            else:
                current_subsection = None
            continue

        if current_section == "geval":
            if current_subsection == "name" and stripped:
                geval_name = stripped
            elif current_subsection == "criteria" and stripped:
                geval_criteria_lines.append(stripped)
            elif current_subsection == "steps":
                geval_steps_lines.append(line)

        elif current_section == "task":
            if current_subsection == "criteria" and stripped:
                task_criteria_lines.append(stripped)

    geval_config = None
    if geval_name or geval_criteria_lines or geval_steps_lines:
        steps = _parse_numbered_steps(geval_steps_lines)
        if geval_criteria_lines and steps:
            geval_config = GEvalConfig(
                name=geval_name or "Agent Response Correctness",
                criteria=" ".join(geval_criteria_lines),
                evaluation_steps=steps,
            )

    task_criteria = " ".join(task_criteria_lines) if task_criteria_lines else None

    return RubricConfig(
        geval=geval_config,
        task_completion_criteria=task_criteria,
    )


def load_rubric_config(file_path: str) -> RubricConfig:
    with open(file_path) as f:
        return parse_rubric_markdown(f.read())
