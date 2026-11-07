"""Run handling, with the slow Scribus render replaced by real blank PDFs."""

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from signs import machine_signs
from signs.flipfix import Machine
from signs.machine_signs import SignRun, describe_run, render_signs
from signs.machines import IncompleteMachine, PlannedSign, SignPlan
from signs.problems import Problem, ProblemKind, RenderError, TemplateCheckError

TEMPLATE = Path(__file__).parent / "fixtures" / "machine-sign.sla"
CONTENT = {"Title": "A", "Manufacturer": "B", "Address": "C", "Month": "D", "Year": "E"}
CONTENT |= {"Produced": "F", "Ownership": "G", "MainText": "H"}
GOOD = Machine("M0001", "Ballyhoo", "Museum")
BAD = Machine("M0002", "Carom", "Museum")


def plan(*machines: Machine) -> SignPlan:
    return SignPlan([PlannedSign(machine, CONTENT) for machine in machines], [])


def write_pdf(path: Path, pages: int = 1) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(100, 100)
    writer.write(path)


@pytest.fixture
def fake_render(monkeypatch: pytest.MonkeyPatch) -> None:
    """Render every sign to one blank page, except `M0002`, which fails its checks."""

    def render(source: Path, dest: Path) -> None:
        if source.stem == BAD.asset_id:
            raise TemplateCheckError([Problem(ProblemKind.OVERFLOW, "Page 1: cut off")])
        write_pdf(dest)

    monkeypatch.setattr(machine_signs, "render", render)


@pytest.mark.usefixtures("fake_render")
def test_failed_sign_is_left_out_and_the_rest_print(tmp_path: Path) -> None:
    output = tmp_path / "signs.pdf"

    run = render_signs(plan(GOOD, BAD), TEMPLATE, output)

    assert run.printed == [GOOD]
    assert run.failed[0].machine == BAD
    assert len(PdfReader(output).pages) == 1
    assert not run.is_clean


@pytest.mark.usefixtures("fake_render")
def test_no_pdf_is_written_when_every_sign_fails(tmp_path: Path) -> None:
    output = tmp_path / "signs.pdf"
    output.write_text("old")

    run = render_signs(plan(BAD), TEMPLATE, output)

    assert output.read_text() == "old"
    assert describe_run(run, output) == [
        "M0002 Carom: Page 1: cut off",
        f"No signs printed, so {output} wasn't changed",
    ]


def test_sign_with_extra_pages_is_left_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(machine_signs, "render", lambda _, dest: write_pdf(dest, pages=2))

    run = render_signs(plan(GOOD), TEMPLATE, tmp_path / "signs.pdf")

    assert run.failed[0].messages == ["Sign has 2 pages, not one"]


def test_unreadable_rendered_sign_is_left_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(machine_signs, "render", lambda _, dest: dest.write_text("not a pdf"))

    run = render_signs(plan(GOOD), TEMPLATE, tmp_path / "signs.pdf")

    assert "Can't read rendered sign" in run.failed[0].messages[0]


@pytest.mark.usefixtures("fake_render")
def test_unwritable_output_gives_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(RenderError, match="Could not write"):
        render_signs(plan(GOOD), TEMPLATE, tmp_path / "absent" / "signs.pdf")


def test_clean_run_printed_everything() -> None:
    assert SignRun([GOOD], [], []).is_clean


def test_run_with_incomplete_machines_is_not_clean() -> None:
    assert not SignRun([GOOD], [], [IncompleteMachine(BAD, "no main text")]).is_clean


def test_run_that_printed_nothing_is_not_clean() -> None:
    assert not SignRun([], [], []).is_clean
