from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from defusedxml import ElementTree

from signs.problems import RenderError
from signs.sla_fill import Run, fill_template, heading_pairs, parse_markdown, styled_font

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

TEMPLATE = Path(__file__).parent / "fixtures" / "machine-sign.sla"
CONTENT = {
    "Title": "Carom",
    "Manufacturer": "Bally",
    "Address": "Chicago",
    "Month": "March",
    "Year": "1937",
    "Produced": "2,000",
    "Ownership": "The Flip Collection",
    "Heading1": "Design by",
    "Info1": "Raymond T Maloney",
    "Heading2": "Art by",
    "Info2": "",
    "Heading3": "Sound by",
    "Info3": "Nobody",
    "MainText": "One",
}


def filled(tmp_path: Path, **changes: str) -> Element:
    output = tmp_path / "filled.sla"
    fill_template(TEMPLATE, {**CONTENT, **changes}, output)
    root: Element = ElementTree.fromstring(output.read_bytes())
    return root


def lines(root: Element) -> list[str]:
    """Return the printed lines of every text frame."""
    found = []
    for story in root.iter("StoryText"):
        line = ""
        for item in story:
            if item.tag == "ITEXT":
                line += item.get("CH", "")
            elif item.tag == "tab":
                line += "|"
            elif item.tag in ("breakline", "para", "trail"):
                found.append(line)
                line = ""
    return found


def edited_template(tmp_path: Path, old: str, new: str) -> Path:
    text = TEMPLATE.read_text()
    assert old in text
    template = tmp_path / "template.sla"
    template.write_text(text.replace(old, new))
    return template


def test_fills_placeholders_across_frames(tmp_path: Path) -> None:
    text = lines(filled(tmp_path))

    assert "Carom" in text
    assert "The Flip Collection" in text
    assert "March 1937" in text


def test_heading_line_repeats_for_each_pair_with_info(tmp_path: Path) -> None:
    text = lines(filled(tmp_path))

    assert "Design by|Raymond T Maloney" in text
    assert "Sound by|Nobody" in text
    assert not any(line.startswith("Art by") for line in text)


def test_line_with_only_blank_placeholders_is_dropped(tmp_path: Path) -> None:
    text = lines(filled(tmp_path, Produced=""))

    assert not any(line.startswith("Units produced") for line in text)
    assert "" not in text[: text.index("Sound by|Nobody") + 1]


def test_blank_month_leaves_no_stray_space(tmp_path: Path) -> None:
    assert "1937" in lines(filled(tmp_path, Month=""))


def test_paragraphs_share_the_template_paragraph_style(tmp_path: Path) -> None:
    root = filled(tmp_path, MainText="One\n\nTwo")

    assert {"One", "Two"} <= set(lines(root))
    assert len([p for p in root.iter("para") if p.get("PARENT") == "Extended Text"]) == 2


def test_italics_use_the_real_italic_font(tmp_path: Path) -> None:
    root = filled(tmp_path, MainText="A *fine* game")

    fonts = {item.get("CH"): item.get("FONT") for item in root.iter("ITEXT")}

    assert fonts["fine"] == "Bai Jamjuree SemiBold Italic"
    assert fonts["A "] == "Bai Jamjuree SemiBold"


def test_image_link_still_works_from_another_directory(tmp_path: Path) -> None:
    root = filled(tmp_path)

    links = [item.get("PFILE") for item in root.iter("PAGEOBJECT") if item.get("PFILE")]

    assert links == [str(TEMPLATE.parent / "TheFlip_logo_large_turquoise.png")]


def test_placeholder_missing_from_the_data_is_refused(tmp_path: Path) -> None:
    template = edited_template(tmp_path, "%Ownership%", "%Owner%")

    with pytest.raises(RenderError, match=r"%Owner%, which isn't in the machine data"):
        fill_template(template, CONTENT, tmp_path / "filled.sla")


def test_placeholder_split_across_styles_is_refused(tmp_path: Path) -> None:
    template = edited_template(
        tmp_path, 'CH="%Ownership%"/>', 'CH="%Owner"/><ITEXT FONT="Bai Jamjuree Bold" CH="ship%"/>'
    )

    with pytest.raises(RenderError, match="splits a placeholder"):
        fill_template(template, CONTENT, tmp_path / "filled.sla")


def test_unreadable_template_gives_a_clear_error(tmp_path: Path) -> None:
    template = tmp_path / "template.sla"
    template.write_text("<SCRIBUS")

    with pytest.raises(RenderError, match="Can't read template"):
        fill_template(template, CONTENT, tmp_path / "filled.sla")


@pytest.mark.parametrize(
    ("text", "runs"),
    [
        ("plain", [Run("plain")]),
        ("a *b* c", [Run("a "), Run("b", italic=True), Run(" c")]),
        ("**b**", [Run("b", bold=True)]),
        ("***b***", [Run("b", bold=True, italic=True)]),
        (r"5 \* 5 \\ 2", [Run(r"5 * 5 \ 2")]),
    ],
)
def test_parses_inline_markdown(text: str, runs: list[Run]) -> None:
    assert parse_markdown(text) == [runs]


def test_blank_line_separates_paragraphs() -> None:
    assert parse_markdown("One\n\nTwo") == [[Run("One")], [Run("Two")]]


@pytest.mark.parametrize("text", ["a *b", "**b*", "b*", "trailing \\"])
def test_unmatched_markup_is_refused(text: str) -> None:
    with pytest.raises(RenderError, match="Unmatched markup"):
        parse_markdown(text)


@pytest.mark.parametrize(
    ("font", "run", "expected"),
    [
        ("Bai Jamjuree SemiBold", Run("x"), "Bai Jamjuree SemiBold"),
        ("Bai Jamjuree SemiBold", Run("x", italic=True), "Bai Jamjuree SemiBold Italic"),
        ("Bai Jamjuree SemiBold", Run("x", bold=True), "Bai Jamjuree Bold"),
        ("Bai Jamjuree Regular", Run("x", italic=True), "Bai Jamjuree Italic"),
        ("Bai Jamjuree Regular", Run("x", bold=True, italic=True), "Bai Jamjuree Bold Italic"),
    ],
)
def test_styled_font_names_the_real_face(font: str, run: Run, expected: str) -> None:
    assert styled_font(font, run) == expected


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('CH="%MainText%"/>', 'CH="Note: %MainText%"/>'),
        ('CH="%MainText%"/>', 'CH="%MainText%"/><ITEXT CH="more"/>'),
    ],
)
def test_main_text_must_be_alone_on_its_line(tmp_path: Path, old: str, new: str) -> None:
    template = edited_template(tmp_path, old, new)

    with pytest.raises(RenderError, match="alone on its line"):
        fill_template(template, CONTENT, tmp_path / "filled.sla")


def test_template_without_main_text_is_refused(tmp_path: Path) -> None:
    template = edited_template(tmp_path, 'CH="%MainText%"/>', 'CH="Fixed text"/>')

    with pytest.raises(RenderError, match="has no %MainText%"):
        fill_template(template, CONTENT, tmp_path / "filled.sla")


def test_repeated_lines_need_a_line_break_in_the_template(tmp_path: Path) -> None:
    template = edited_template(tmp_path, "<breakline/>", "")

    with pytest.raises(RenderError, match="needs a line break"):
        fill_template(template, CONTENT, tmp_path / "filled.sla")


def test_odd_placeholder_name_is_refused(tmp_path: Path) -> None:
    template = edited_template(tmp_path, "%Ownership%", "%Own_er%")

    with pytest.raises(RenderError, match="%Own_er%"):
        fill_template(template, CONTENT, tmp_path / "filled.sla")


def test_template_spacing_around_a_placeholder_is_kept(tmp_path: Path) -> None:
    template = edited_template(tmp_path, 'CH="%Ownership%"/>', 'CH="From %Ownership%, "/>')
    output = tmp_path / "filled.sla"

    fill_template(template, CONTENT, output)

    assert 'CH="From The Flip Collection, "' in output.read_text()


def test_info_without_a_heading_is_refused() -> None:
    with pytest.raises(RenderError, match="Info3 has no heading"):
        heading_pairs({"Heading3": " ", "Info3": "Nobody"})


def test_info_with_no_heading_column_is_refused() -> None:
    with pytest.raises(RenderError, match="Info3 has no heading"):
        heading_pairs({"Info3": "Nobody"})


def test_heading_pairs_follow_their_numbers() -> None:
    content = {"Heading10": "Last", "Info10": "y", "Heading2": "First", "Info2": "x"}

    assert [pair["Heading"] for pair in heading_pairs(content)] == ["First", "Last"]


@pytest.mark.parametrize("text", [r"C:\temp", r"5\x"])
def test_only_documented_escapes_are_allowed(text: str) -> None:
    with pytest.raises(RenderError, match="Unmatched markup"):
        parse_markdown(text)


@pytest.mark.parametrize("text", ["One\r\n\r\nTwo", "One\n\n\nTwo", "One\n \nTwo"])
def test_any_blank_line_separates_paragraphs(text: str) -> None:
    assert parse_markdown(text) == [[Run("One")], [Run("Two")]]


def test_single_line_break_in_main_text_is_refused() -> None:
    with pytest.raises(RenderError, match="blank line between paragraphs"):
        parse_markdown("One\nTwo")


@pytest.mark.parametrize("font", ["Arial", "Bai Jamjuree", "Bai Jamjuree Italic"])
def test_font_without_a_plain_weight_is_refused(font: str) -> None:
    with pytest.raises(RenderError, match=f"Can't work out styles for {font}"):
        styled_font(font, Run("x", italic=True))
