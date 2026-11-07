import shutil
from pathlib import Path

import pytest

from signs.fonts import LICENSED_FONT_DIR_VARIABLE
from signs.problems import Problem, ProblemKind, RenderError
from signs.render import describe_problems, publish, render
from signs.scribus_export import parse_report


def test_unknown_file_type_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RenderError, match=r"Don't know how to render \.txt"):
        render(Path("sign.txt"), tmp_path / "sign.pdf")


def test_missing_source_is_reported(tmp_path: Path) -> None:
    with pytest.raises(RenderError, match="File not found"):
        render(tmp_path / "absent.svg", tmp_path / "sign.pdf")


def test_directory_as_output_is_refused(tmp_path: Path) -> None:
    source = tmp_path / "sign.svg"
    source.write_text("<svg/>")

    with pytest.raises(RenderError, match="Output path is a directory"):
        render(source, tmp_path)


def test_output_that_is_not_a_pdf_is_refused_leaving_the_template_alone(tmp_path: Path) -> None:
    source = tmp_path / "sign.svg"
    source.write_text("<svg/>")

    with pytest.raises(RenderError, match="Output must be a .pdf file"):
        render(source, source)

    assert source.read_text() == "<svg/>"


def test_publish_replaces_the_old_pdf_and_leaves_nothing_else(tmp_path: Path) -> None:
    staged = tmp_path / "staged" / "sign.pdf"
    staged.parent.mkdir()
    staged.write_text("new")
    output = tmp_path / "out"
    output.mkdir()
    (output / "sign.pdf").write_text("old")

    publish(staged, output / "sign.pdf")

    assert [path.read_text() for path in output.iterdir()] == ["new"]


def test_output_backing_a_symlinked_template_is_refused(tmp_path: Path) -> None:
    template = tmp_path / "sign.svg.pdf"
    template.write_text("<svg/>")
    link = tmp_path / "sign.svg"
    link.symlink_to(template)

    with pytest.raises(RenderError, match="would replace the template"):
        render(link, template)

    assert template.read_text() == "<svg/>"


def test_publish_leaves_an_unrelated_temporary_file_alone(tmp_path: Path) -> None:
    staged = tmp_path / "staged.pdf"
    staged.write_text("new")
    unrelated = tmp_path / ".sign.pdf.tmp"
    unrelated.write_text("someone else's")

    publish(staged, tmp_path / "sign.pdf")

    assert unrelated.read_text() == "someone else's"


def test_interrupted_publish_leaves_nothing_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staged = tmp_path / "staged" / "sign.pdf"
    staged.parent.mkdir()
    staged.write_text("new")
    output = tmp_path / "out"
    output.mkdir()

    def interrupted_copy(_: Path, unfinished: Path) -> None:
        unfinished.write_text("ne")
        raise KeyboardInterrupt

    monkeypatch.setattr(shutil, "copyfile", interrupted_copy)

    with pytest.raises(KeyboardInterrupt):
        publish(staged, output / "sign.pdf")

    assert list(output.iterdir()) == []


def test_publish_reports_an_unwritable_output(tmp_path: Path) -> None:
    staged = tmp_path / "sign.pdf"
    staged.write_text("new")

    with pytest.raises(RenderError, match="Could not write"):
        publish(staged, tmp_path / "absent" / "sign.pdf")


def test_font_problems_say_where_licensed_fonts_go(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(LICENSED_FONT_DIR_VARIABLE, str(tmp_path))
    problem = Problem(ProblemKind.FONT, "Font not available: Arial")

    assert describe_problems([problem]) == [problem.message, f"Licensed fonts go in {tmp_path}"]


def test_other_problems_get_no_font_advice() -> None:
    problem = Problem(ProblemKind.IMAGE, "Image not found: logo.png")

    assert describe_problems([problem]) == [problem.message]


def test_unknown_problem_kind_in_scribus_report_gives_a_clear_error() -> None:
    with pytest.raises(RenderError, match="unreadable report"):
        parse_report('[{"kind": "fnot", "message": "Font not available: Arial"}]')


def test_unreadable_scribus_report_gives_a_clear_error() -> None:
    with pytest.raises(RenderError, match="unreadable report"):
        parse_report('[{"kind": "fo')


def test_parses_scribus_report() -> None:
    report = '[{"kind": "font", "message": "Font not available: Arial"}]'

    assert parse_report(report) == [Problem(ProblemKind.FONT, "Font not available: Arial")]
