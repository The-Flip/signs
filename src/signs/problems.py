"""Errors and check results shared across the app."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class ProblemKind(StrEnum):
    """What went wrong. The Scribus script can't import this, so it repeats these values."""

    FONT = "font"
    IMAGE = "image"
    OVERFLOW = "overflow"


@dataclass(frozen=True)
class Problem:
    """Something in a template that would make the printed sign wrong."""

    kind: ProblemKind
    message: str


class MachineDataError(Exception):
    """Machine data could not be read."""


class RenderError(Exception):
    """Rendering could not be carried out."""


class TemplateCheckError(RenderError):
    """Rendering was refused because the template failed its checks."""

    def __init__(self, problems: Sequence[Problem]) -> None:
        super().__init__(f"{len(problems)} problem(s) found")
        self.problems = list(problems)
