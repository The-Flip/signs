"""Read Inkscape SVG templates and check what they link to."""

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlsplit

from defusedxml import DefusedXmlException, ElementTree

from signs.problems import Problem, ProblemKind, RenderError

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


def local_name(element: Element) -> str:
    return element.tag.rpartition("}")[2]


def parse_svg(svg_path: Path) -> Element:
    try:
        return ElementTree.fromstring(svg_path.read_bytes())
    except (ElementTree.ParseError, DefusedXmlException) as error:
        raise RenderError(f"Can't read SVG file {svg_path}: {error}") from error


def is_image_available(href: str, svg_path: Path) -> bool:
    """Say whether an image link is embedded or points to a local file that exists.

    Any other scheme counts as missing. That covers web links, which would make a sign
    depend on a remote server, and Windows paths, whose drive letter reads as a scheme.
    """
    link = urlsplit(href)
    if link.scheme == "data":
        return True
    if link.scheme == "file":
        return Path(unquote(link.path)).is_file()
    return not link.scheme and (svg_path.parent / unquote(link.path)).is_file()


def check_svg_images(svg_path: Path) -> list[Problem]:
    problems = []
    for element in parse_svg(svg_path).iter():
        href = element.get(XLINK_HREF) or element.get("href")
        if local_name(element) == "image" and href and not is_image_available(href, svg_path):
            problems.append(Problem(ProblemKind.IMAGE, f"Image not found: {href}"))
    return problems
