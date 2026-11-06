"""Export Inkscape SVG templates to PDF."""

from collections.abc import Mapping
from pathlib import Path

from signs.fonts import check_svg_fonts
from signs.problems import RenderError, TemplateCheckError
from signs.svg import check_svg_images
from signs.tools import run_tool


def export_svg(source: Path, dest: Path, env: Mapping[str, str]) -> None:
    problems = check_svg_fonts(source, env) + check_svg_images(source)
    if problems:
        raise TemplateCheckError(problems)

    result = run_tool(
        ["inkscape", str(source), "--export-type=pdf", f"--export-filename={dest}"], env
    )
    if result.returncode != 0 or not dest.exists():
        raise RenderError(f"Inkscape could not export {source}:\n{result.output}")
