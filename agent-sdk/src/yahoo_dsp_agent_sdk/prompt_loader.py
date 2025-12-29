from pathlib import Path
from typing import Dict, Union


def load_template_from_file(path: Union[str, Path]) -> str:
    """Loads a Markdown prompt from a file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def load_prompt(path: Union[str, Path], variables: Dict[str, str] = None) -> str:
    """
    Load a Markdown prompt and inject variables using Python's built-in string formatting.

    Args:
        path: Full path to the markdown file
        variables: Dictionary of variables to inject into the template
    """
    if variables is None:
        variables = {}

    template = load_template_from_file(path)
    return template.format(**variables)
