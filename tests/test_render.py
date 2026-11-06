from pathlib import Path

import pytest

from signs.problems import Problem, RenderError
from signs.render import render
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


def test_unreadable_scribus_report_gives_a_clear_error() -> None:
    with pytest.raises(RenderError, match="unreadable report"):
        parse_report('[{"kind": "fo')


def test_parses_scribus_report() -> None:
    report = '[{"kind": "font", "message": "Font not available: Arial"}]'

    assert parse_report(report) == [Problem("font", "Font not available: Arial")]
