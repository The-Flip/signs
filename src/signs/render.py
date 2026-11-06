"""Render sign templates to PDF."""

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from signs.fonts import font_environment
from signs.inkscape_export import export_svg
from signs.problems import RenderError
from signs.scribus_export import export_sla

EXPORTERS = {".svg": export_svg, ".sla": export_sla}


def render(source: Path, dest: Path) -> None:
    """Render a template to a PDF at `dest`, or raise without writing anything there."""
    exporter = EXPORTERS.get(source.suffix.lower())
    if exporter is None:
        raise RenderError(f"Don't know how to render {source.suffix or source.name} files")
    if not source.is_file():
        raise RenderError(f"File not found: {source}")
    if dest.is_dir():
        raise RenderError(f"Output path is a directory: {dest}")

    with font_environment() as env, TemporaryDirectory(prefix="signs-render-") as work:
        staged = Path(work) / "sign.pdf"
        exporter(source, staged, env)
        try:
            shutil.move(staged, dest)
        except OSError as error:
            raise RenderError(f"Could not write {dest}: {error}") from error
