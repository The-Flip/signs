from pathlib import Path

import pytest

from signs.problems import Problem, ProblemKind
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

    assert check_svg_images(svg) == [Problem(ProblemKind.IMAGE, "Image not found: logo.png")]


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


@pytest.mark.parametrize("href", ["https://example.com/logo.png", "C:/Users/me/logo.png"])
def test_image_that_is_not_a_local_file_is_reported(tmp_path: Path, href: str) -> None:
    svg = write_svg(tmp_path, href)

    assert check_svg_images(svg) == [Problem(ProblemKind.IMAGE, f"Image not found: {href}")]


def write_svg_with_both_links(tmp_path: Path, href: str, xlink_href: str) -> Path:
    path = tmp_path / "sign.svg"
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" {XLINK}>'
        f'<image href="{href}" xlink:href="{xlink_href}"/></svg>'
    )
    return path


def test_href_wins_over_xlink_href(tmp_path: Path) -> None:
    (tmp_path / "old.png").touch()
    svg = write_svg_with_both_links(tmp_path, "new.png", "old.png")

    assert check_svg_images(svg) == [Problem(ProblemKind.IMAGE, "Image not found: new.png")]


def test_empty_href_is_reported_even_with_a_good_xlink_href(tmp_path: Path) -> None:
    (tmp_path / "old.png").touch()
    svg = write_svg_with_both_links(tmp_path, "", "old.png")

    assert check_svg_images(svg) == [Problem(ProblemKind.IMAGE, "Image not found: ")]
