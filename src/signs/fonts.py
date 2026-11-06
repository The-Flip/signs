"""Make our fonts available, and check that SVG templates can get their fonts.

Open fonts are bundled in the repo. The repo is public, so fonts we hold a license for
stay outside it, in the licensed font directory.

Inkscape and Scribus both substitute missing fonts silently and still report success,
so the checks have to happen here.
"""

import html
import os
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from signs.problems import Problem, ProblemKind, RenderError
from signs.svg import local_name, parse_svg
from signs.tools import run_tool

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

FONT_DIR = Path(__file__).parent / "fonts"
LICENSED_FONT_DIR_VARIABLE = "SIGNS_LICENSED_FONT_DIR"
GENERIC_FAMILIES = {"sans", "sans-serif", "serif", "monospace"}
TEXT_ROOT_TAGS = {"text", "flowRoot"}


def licensed_font_dir() -> Path:
    configured = os.environ.get(LICENSED_FONT_DIR_VARIABLE)
    # Absolute, because fontconfig reads a relative <dir> from its config file's directory
    return Path(configured).resolve() if configured else Path.home() / ".local/share/signs/fonts"


@contextmanager
def font_environment() -> Iterator[dict[str, str]]:
    """Yield an environment in which programs see system, bundled and licensed fonts."""
    with TemporaryDirectory(prefix="signs-fonts-") as work:
        config = Path(work) / "fonts.conf"
        config.write_text(
            '<?xml version="1.0"?>\n'
            "<fontconfig>\n"
            # The Linux location; signs targets Linux because of xvfb
            '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
            f"  <dir>{html.escape(str(FONT_DIR))}</dir>\n"
            f"  <dir>{html.escape(str(licensed_font_dir()))}</dir>\n"
            f"  <cachedir>{html.escape(work)}/cache</cachedir>\n"
            "</fontconfig>\n"
        )
        yield {**os.environ, "FONTCONFIG_FILE": str(config)}


def own_font_family(element: Element) -> str | None:
    """Return the first font family set directly on an element, if any.

    The style attribute wins over the presentation attribute, as it does in SVG.
    """
    declared = element.get("font-family")
    for declaration in element.get("style", "").split(";"):
        name, _, value = declaration.partition(":")
        if name.strip() == "font-family":
            declared = value
    if declared is None:
        return None
    return declared.split(",")[0].strip().strip("'\"")


def text_families(
    element: Element, inherited: str | None = None, in_text: bool = False
) -> Iterator[str]:
    """Yield the font family of each piece of text in an element and its children."""
    family = own_font_family(element) or inherited
    in_text = in_text or local_name(element) in TEXT_ROOT_TAGS
    if in_text and family and has_text(element.text):
        yield family
    for child in element:
        yield from text_families(child, family, in_text)
        if in_text and family and has_text(child.tail):
            yield family


def has_text(text: str | None) -> bool:
    return bool(text and text.strip())


def text_font_families(svg_path: Path) -> set[str]:
    """Return the font families used by actual text in an SVG.

    Styles on elements without text don't count, because text converted to paths often
    leaves its old font declared.
    """
    return set(text_families(parse_svg(svg_path)))


def font_pattern(family: str) -> str:
    """Escape a family name for fontconfig, where `-` would otherwise start a size."""
    return re.sub(r"([\\\-:,])", r"\\\1", family)


def is_font_available(family: str, env: Mapping[str, str]) -> bool:
    """Say whether fontconfig has this family, rather than a fallback for it."""
    if family.casefold() in GENERIC_FAMILIES:
        return True
    result = run_tool(["fc-match", "--format=%{family}", font_pattern(family)], env)
    if result.returncode != 0:
        raise RenderError(f"fc-match failed for {family}: {result.output}")
    return family.casefold() in [name.casefold() for name in result.output.split(",")]


def check_svg_fonts(svg_path: Path, env: Mapping[str, str]) -> list[Problem]:
    return [
        Problem(ProblemKind.FONT, f"Font not available: {family}")
        for family in sorted(text_font_families(svg_path))
        if not is_font_available(family, env)
    ]
