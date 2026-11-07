"""End-to-end rendering with the real Inkscape and Scribus."""

import os
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from signs.cli import app
from signs.flipfix import Machine
from signs.machine_signs import render_signs
from signs.machines import PlannedSign, SignPlan
from signs.problems import RenderError, TemplateCheckError
from signs.render import render
from signs.tools import run_tool

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parent / "fixtures"
SVG = FIXTURES / "staff-only.svg"
SLA_WITHOUT_IMAGES = FIXTURES / "donation-box.sla"
SLA_WITH_IMAGE = FIXTURES / "machine-sign.sla"
SLA_WITH_GROUP = FIXTURES / "grouped-frames.sla"
LOGO = "TheFlip_logo_large_turquoise.png"


def edited_copy(source: Path, directory: Path, old: str, new: str) -> Path:
    """Copy a fixture with its text changed, so failures start from a real template."""
    text = source.read_text()
    assert old in text
    copy = directory / source.name
    copy.write_text(text.replace(old, new))
    return copy


def pdf_fonts(pdf: Path) -> str:
    return run_tool(["pdffonts", str(pdf)], os.environ).output


def problem_kinds(error: TemplateCheckError) -> set[str]:
    return {problem.kind for problem in error.problems}


def test_svg_renders_with_its_real_font(tmp_path: Path) -> None:
    pdf = tmp_path / "sign.pdf"

    render(SVG, pdf)

    assert "BaiJamjuree" in pdf_fonts(pdf)


def test_sla_renders_with_its_real_fonts(tmp_path: Path) -> None:
    pdf = tmp_path / "sign.pdf"

    render(SLA_WITHOUT_IMAGES, pdf)

    assert "BaiJamjuree" in pdf_fonts(pdf)


def test_sla_with_linked_image_renders(tmp_path: Path) -> None:
    pdf = tmp_path / "sign.pdf"

    render(SLA_WITH_IMAGE, pdf)

    assert pdf.exists()


def test_svg_with_unavailable_font_is_refused(tmp_path: Path) -> None:
    source = edited_copy(SVG, tmp_path, "Bai Jamjuree", "No Such Font")
    pdf = tmp_path / "sign.pdf"

    with pytest.raises(TemplateCheckError) as caught:
        render(source, pdf)

    assert problem_kinds(caught.value) == {"font"}
    assert "No Such Font" in caught.value.problems[0].message
    assert not pdf.exists()


def test_sla_with_unavailable_font_is_refused(tmp_path: Path) -> None:
    source = edited_copy(SLA_WITHOUT_IMAGES, tmp_path, "Bai Jamjuree", "No Such Font")
    pdf = tmp_path / "sign.pdf"

    with pytest.raises(TemplateCheckError) as caught:
        render(source, pdf)

    assert "font" in problem_kinds(caught.value)
    assert not pdf.exists()


def test_sla_with_overflowing_text_is_refused(tmp_path: Path) -> None:
    text = SLA_WITHOUT_IMAGES.read_text()
    shrunk = re.sub(r'(<PAGEOBJECT [^>]*PTYPE="4"[^>]*? HEIGHT=")[^"]*"', r'\g<1>1"', text)
    assert shrunk != text
    source = tmp_path / SLA_WITHOUT_IMAGES.name
    source.write_text(shrunk)
    pdf = tmp_path / "sign.pdf"

    with pytest.raises(TemplateCheckError) as caught:
        render(source, pdf)

    assert problem_kinds(caught.value) == {"overflow"}
    assert not pdf.exists()


def test_blank_trailing_paragraphs_are_not_overflow(tmp_path: Path) -> None:
    text = SLA_WITHOUT_IMAGES.read_text()
    padded = text.replace("<trail", "<para/>" * 80 + "<trail", 1)
    assert padded != text
    source = tmp_path / SLA_WITHOUT_IMAGES.name
    source.write_text(padded)
    pdf = tmp_path / "sign.pdf"

    render(source, pdf)

    assert pdf.exists()


def test_sla_with_missing_image_is_refused(tmp_path: Path) -> None:
    source = edited_copy(SLA_WITH_IMAGE, tmp_path, LOGO, "no-such-logo.png")
    pdf = tmp_path / "sign.pdf"

    with pytest.raises(TemplateCheckError) as caught:
        render(source, pdf)

    assert problem_kinds(caught.value) == {"image"}
    assert not pdf.exists()


def test_corrupt_sla_gives_an_error_rather_than_a_pdf(tmp_path: Path) -> None:
    source = tmp_path / "broken.sla"
    source.write_text("this is not a Scribus file")
    pdf = tmp_path / "sign.pdf"

    with pytest.raises(RenderError, match="Scribus could not process"):
        render(source, pdf)

    assert not pdf.exists()


def test_cli_writes_pdf_and_says_where(tmp_path: Path) -> None:
    pdf = tmp_path / "out.pdf"

    result = CliRunner().invoke(app, ["render", str(SVG), "-o", str(pdf)])

    assert result.exit_code == 0
    assert str(pdf) in result.stdout
    assert pdf.exists()


def test_cli_lists_problems_and_fails(tmp_path: Path) -> None:
    source = edited_copy(SVG, tmp_path, "Bai Jamjuree", "No Such Font")

    result = CliRunner().invoke(app, ["render", str(source), "-o", str(tmp_path / "out.pdf")])

    assert result.exit_code == 1
    assert "Font not available: No Such Font" in result.stderr
    assert "Licensed fonts go in" in result.stderr


def test_grouped_frames_are_refused(tmp_path: Path) -> None:
    output = tmp_path / "sign.pdf"

    with pytest.raises(TemplateCheckError) as caught:
        render(SLA_WITH_GROUP, output)

    assert problem_kinds(caught.value) == {"group"}
    assert not output.exists()


def sign_content(main_text: str) -> dict[str, str]:
    return {
        "Title": "Carom",
        "Manufacturer": "Bally",
        "Address": "Chicago",
        "Month": "March",
        "Year": "1937",
        "Produced": "",
        "Ownership": "The Flip Collection",
        "Heading1": "Design by",
        "Info1": "Raymond T Maloney",
        "MainText": main_text,
    }


def test_signs_join_into_one_pdf_with_real_italics(tmp_path: Path) -> None:
    output = tmp_path / "signs.pdf"
    signs = [
        PlannedSign(Machine("M0001", "One", "Museum"), sign_content("A *fine* game.")),
        PlannedSign(Machine("M0002", "Two", "Museum"), sign_content("Another game.")),
    ]

    run = render_signs(SignPlan(signs, []), SLA_WITH_IMAGE, output)

    assert len(run.printed) == 2
    assert "Pages:           2" in run_tool(["pdfinfo", str(output)], os.environ).output
    assert "BaiJamjuree-SemiBoldItalic" in pdf_fonts(output)


def test_sign_that_fails_is_left_out_and_named(tmp_path: Path) -> None:
    output = tmp_path / "signs.pdf"
    good = PlannedSign(Machine("M0001", "One", "Museum"), sign_content("A fine game."))
    too_long = Machine("M0002", "Two", "Museum")
    bad = PlannedSign(too_long, sign_content("Far too much to say. " * 400))

    run = render_signs(SignPlan([good, bad], []), SLA_WITH_IMAGE, output)

    assert run.printed == [good.machine]
    assert [sign.machine for sign in run.failed] == [too_long]
    assert "cut off" in run.failed[0].messages[0]
    assert "Pages:           1" in run_tool(["pdfinfo", str(output)], os.environ).output


def test_no_pdf_when_every_sign_fails(tmp_path: Path) -> None:
    output = tmp_path / "signs.pdf"
    bad = PlannedSign(Machine("M0002", "Two", "Museum"), sign_content("Too much. " * 900))

    run = render_signs(SignPlan([bad], []), SLA_WITH_IMAGE, output)

    assert run.printed == []
    assert not output.exists()
