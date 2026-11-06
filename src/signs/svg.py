"""Read Inkscape SVG templates and check what they link to."""

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlsplit

from defusedxml import DefusedXmlException, ElementTree

from signs.problems import Problem, RenderError

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


def linked_image_path(href: str, svg_path: Path) -> Path | None:
    """Return the local file an image link points to, or None if it isn't a local file."""
    link = urlsplit(href)
    if link.scheme == "file":
        return Path(unquote(link.path))
    if link.scheme:
        return None
    return svg_path.parent / unquote(link.path)


def check_svg_images(svg_path: Path) -> list[Problem]:
    problems = []
    for element in parse_svg(svg_path).iter():
        href = element.get(XLINK_HREF) or element.get("href")
        if local_name(element) == "image" and href:
            image = linked_image_path(href, svg_path)
            if image is not None and not image.is_file():
                problems.append(Problem("image", f"Image not found: {href}"))
    return problems
