"""Errors and check results shared by the renderers."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Problem:
    """Something in a template that would make the printed sign wrong."""

    kind: str
    message: str


class RenderError(Exception):
    """Rendering could not be carried out."""


class TemplateCheckError(RenderError):
    """Rendering was refused because the template failed its checks."""

    def __init__(self, problems: Sequence[Problem]) -> None:
        super().__init__(f"{len(problems)} problem(s) found")
        self.problems = list(problems)
