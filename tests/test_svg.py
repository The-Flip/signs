from pathlib import Path

from signs.problems import Problem
from signs.svg import check_svg_images

XLINK = 'xmlns:xlink="http://www.w3.org/1999/xlink"'


def write_svg(tmp_path: Path, href: str) -> Path:
    path = tmp_path / "sign.svg"
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" {XLINK}><image xlink:href="{href}"/></svg>'
    )
    return path


def test_missing_linked_image_is_reported(tmp_path: Path) -> None:
    svg = write_svg(tmp_path, "logo.png")

    assert check_svg_images(svg) == [Problem("image", "Image not found: logo.png")]


def test_linked_image_next_to_the_svg_passes(tmp_path: Path) -> None:
    (tmp_path / "my logo.png").touch()
    svg = write_svg(tmp_path, "my%20logo.png")

    assert check_svg_images(svg) == []


def test_file_url_is_resolved(tmp_path: Path) -> None:
    logo = tmp_path / "logo.png"
    logo.touch()
    svg = write_svg(tmp_path, f"file://{logo}")

    assert check_svg_images(svg) == []


def test_embedded_image_passes(tmp_path: Path) -> None:
    svg = write_svg(tmp_path, "data:image/png;base64,AAAA")

    assert check_svg_images(svg) == []
