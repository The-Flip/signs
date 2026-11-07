"""Render sign templates to PDF."""

import shutil
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

from signs.fonts import font_environment, licensed_font_dir
from signs.inkscape_export import export_svg
from signs.problems import Problem, ProblemKind, RenderError
from signs.scribus_export import export_sla

EXPORTERS = {".svg": export_svg, ".sla": export_sla}


def describe_problems(problems: Sequence[Problem]) -> list[str]:
    """Return what to tell a person about failed checks, including how to fix fonts."""
    lines = [problem.message for problem in problems]
    if any(problem.kind is ProblemKind.FONT for problem in problems):
        lines.append(f"Licensed fonts go in {licensed_font_dir()}")
    return lines


def publish(staged: Path, dest: Path) -> None:
    """Put a finished PDF in place in one step, so a failed copy can't leave half a sign."""
    try:
        with TemporaryDirectory(dir=dest.parent, prefix=f".{dest.name}.") as work:
            unfinished = Path(work) / dest.name
            shutil.copyfile(staged, unfinished)
            unfinished.replace(dest)
    except OSError as error:
        raise RenderError(f"Could not write {dest}: {error}") from error


def check_output(source: Path, dest: Path) -> None:
    """Refuse an output path before any work is done."""
    if dest.is_dir():
        raise RenderError(f"Output path is a directory: {dest}")
    if dest.suffix.lower() != ".pdf":
        raise RenderError(f"Output must be a .pdf file: {dest}")
    if dest.exists() and dest.samefile(source):
        raise RenderError(f"Output would replace the template: {dest}")


def render(source: Path, dest: Path) -> None:
    """Render a template to a PDF at `dest`, or raise without writing anything there."""
    exporter = EXPORTERS.get(source.suffix.lower())
    if exporter is None:
        raise RenderError(f"Don't know how to render {source.suffix or source.name} files")
    if not source.is_file():
        raise RenderError(f"File not found: {source}")
    check_output(source, dest)

    with font_environment() as env, TemporaryDirectory(prefix="signs-render-") as work:
        staged = Path(work) / "sign.pdf"
        exporter(source, staged, env)
        publish(staged, dest)
