"""Jinja2-based prompt template management."""

from pathlib import Path
from typing import Any

import jinja2


class PromptManager:
    """Loads and renders Jinja2 prompt templates from the calling module's directory."""

    def __init__(self, current_file: str):
        """Initialize with directory containing templates.

        Args:
            current_file: The __file__ of the calling module.
        """
        current_path = Path(current_file).resolve()
        if not current_path.exists():
            raise ValueError(
                f"Invalid path: {current_file}. Did you pass __name__ instead of __file__?"
            )

        base_dir = current_path.parent if current_path.is_file() else current_path

        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(base_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,
        )

    def get(self, template_name: str, **kwargs: Any) -> str:  # pyright: ignore[reportAny]
        """Load and render a template.

        Args:
            template_name: Template filename (extension optional).
            **kwargs: Variables passed to the template.

        Returns:
            Rendered template string.
        """
        for name in [template_name, f"{template_name}.jinja2", f"{template_name}.jinja"]:
            try:
                return self.env.get_template(name).render(**kwargs)
            except jinja2.TemplateNotFound:
                continue
        raise FileNotFoundError(f"Template '{template_name}' not found")
