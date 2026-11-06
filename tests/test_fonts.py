from pathlib import Path

import pytest

from signs import fonts
from signs.fonts import (
    LICENSED_FONT_DIR_VARIABLE,
    font_environment,
    font_pattern,
    is_font_available,
    licensed_font_dir,
    text_font_families,
)
from signs.problems import RenderError


def write_svg(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "sign.svg"
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg">{body}</svg>')
    return path


def test_finds_family_in_style_attribute(tmp_path: Path) -> None:
    svg = write_svg(
        tmp_path, """<text style="font-size:12px;font-family:'Bai Jamjuree'">Hi</text>"""
    )

    assert text_font_families(svg) == {"Bai Jamjuree"}


def test_finds_family_in_presentation_attribute(tmp_path: Path) -> None:
    svg = write_svg(tmp_path, '<text font-family="Carlito">Hi</text>')

    assert text_font_families(svg) == {"Carlito"}


def test_style_wins_over_presentation_attribute(tmp_path: Path) -> None:
    svg = write_svg(tmp_path, '<text font-family="Carlito" style="font-family:Arial">Hi</text>')

    assert text_font_families(svg) == {"Arial"}


def test_text_inherits_family_from_ancestors(tmp_path: Path) -> None:
    svg = write_svg(tmp_path, '<g style="font-family:Carlito"><text><tspan>Hi</tspan></text></g>')

    assert text_font_families(svg) == {"Carlito"}


def test_tspan_family_overrides_inherited_family(tmp_path: Path) -> None:
    svg = write_svg(
        tmp_path, '<text style="font-family:Carlito"><tspan font-family="Arial">Hi</tspan></text>'
    )

    assert text_font_families(svg) == {"Arial"}


def test_text_after_a_child_counts_for_the_parent_family(tmp_path: Path) -> None:
    svg = write_svg(
        tmp_path,
        '<text font-family="Carlito"><tspan font-family="Arial">Hi</tspan> there</text>',
    )

    assert text_font_families(svg) == {"Arial", "Carlito"}


def test_uses_first_family_in_a_list(tmp_path: Path) -> None:
    svg = write_svg(tmp_path, """<text font-family="'Noto Sans', sans-serif">Hi</text>""")

    assert text_font_families(svg) == {"Noto Sans"}


def test_ignores_fonts_on_elements_without_text(tmp_path: Path) -> None:
    svg = write_svg(
        tmp_path,
        '<path style="font-family:Arial" d="M0 0"/><text font-family="Carlito">  </text>',
    )

    assert text_font_families(svg) == set()


def test_malformed_svg_gives_a_clear_error(tmp_path: Path) -> None:
    svg = tmp_path / "sign.svg"
    svg.write_text("<svg><text>")

    with pytest.raises(RenderError, match="Can't read SVG file"):
        text_font_families(svg)


def test_svg_with_entities_gives_a_clear_error(tmp_path: Path) -> None:
    svg = tmp_path / "sign.svg"
    svg.write_text('<!DOCTYPE svg [<!ENTITY a "b">]><svg>&a;</svg>')

    with pytest.raises(RenderError, match="Can't read SVG file"):
        text_font_families(svg)


def test_font_pattern_escapes_fontconfig_syntax() -> None:
    assert font_pattern("Foo-Bold:x") == r"Foo\-Bold\:x"


def test_generic_families_are_always_available() -> None:
    with font_environment() as env:
        assert is_font_available("Sans", env)


def test_bundled_font_is_available() -> None:
    with font_environment() as env:
        assert is_font_available("Bai Jamjuree", env)


def test_carlito_is_bundled() -> None:
    with font_environment() as env:
        assert is_font_available("Carlito", env)


def test_fonts_in_the_licensed_directory_are_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(LICENSED_FONT_DIR_VARIABLE, str(fonts.FONT_DIR))
    monkeypatch.setattr(fonts, "FONT_DIR", tmp_path)

    with font_environment() as env:
        assert is_font_available("Bai Jamjuree", env)


def test_licensed_directory_defaults_to_user_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(LICENSED_FONT_DIR_VARIABLE, raising=False)

    assert licensed_font_dir() == Path.home() / ".local/share/signs/fonts"


def test_fallback_does_not_count_as_available() -> None:
    with font_environment() as env:
        assert not is_font_available("No Such Font", env)


def test_relative_licensed_font_dir_is_made_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(LICENSED_FONT_DIR_VARIABLE, "licensed")

    assert licensed_font_dir() == tmp_path / "licensed"
