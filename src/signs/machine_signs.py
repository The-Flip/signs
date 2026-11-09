"""Render a sign for each machine, and join them into one PDF."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError

from signs.flipfix import Machine, fetch_machines
from signs.machines import (
    IncompleteMachine,
    PlannedSign,
    SignPlan,
    describe_incomplete,
    load_sign_content,
    plan_signs,
)
from signs.problems import RenderError, TemplateCheckError
from signs.render import check_output, publish, render
from signs.sla_fill import fill_template


@dataclass(frozen=True)
class FailedSign:
    machine: Machine
    messages: list[str]


@dataclass(frozen=True)
class SignRun:
    printed: list[Machine]
    failed: list[FailedSign]
    incomplete: list[IncompleteMachine]

    @property
    def is_clean(self) -> bool:
        return bool(self.printed) and not self.failed and not self.incomplete


def check_one_page(pdf: Path) -> None:
    """Refuse a PDF that would knock the signs after it out of step."""
    try:
        pages = len(PdfReader(pdf).pages)
    except (PyPdfError, OSError) as error:
        raise RenderError(f"Can't read rendered sign: {error}") from error
    if pages != 1:
        raise RenderError(f"Sign has {pages} pages, not one")


def render_sign(sign: PlannedSign, template: Path, work: Path) -> Path:
    """Render one machine's sign, returning its PDF."""
    filled = work / f"{sign.machine.asset_id}.sla"
    pdf = filled.with_suffix(".pdf")
    fill_template(template, sign.content, filled)
    render(filled, pdf)
    check_one_page(pdf)
    return pdf


def join_pdfs(pdfs: Iterable[Path], dest: Path) -> None:
    writer = PdfWriter()
    try:
        for pdf in pdfs:
            writer.append(pdf)
        writer.write(dest)
    except (PyPdfError, OSError) as error:
        raise RenderError(f"Could not join the signs: {error}") from error


def render_signs(plan: SignPlan, template: Path, dest: Path) -> SignRun:
    """Write one PDF of every sign that passes its checks, and report the rest."""
    pdfs: dict[Machine, Path] = {}
    failed = []
    with TemporaryDirectory(prefix="signs-machines-") as work:
        for sign in plan.signs:
            try:
                pdfs[sign.machine] = render_sign(sign, template, Path(work))
            except TemplateCheckError as error:
                messages = [problem.message for problem in error.problems]
                failed.append(FailedSign(sign.machine, messages))
            except RenderError as error:
                failed.append(FailedSign(sign.machine, [str(error)]))
        if pdfs:
            joined = Path(work) / "joined.pdf"
            join_pdfs(pdfs.values(), joined)
            publish(joined, dest)
    return SignRun(list(pdfs), failed, plan.incomplete)


def print_machine_signs(
    template: Path, dest: Path, data: Path, asset_ids: Iterable[str] = ()
) -> SignRun:
    """Print the named machines' signs, or everything ready on the floor, into one PDF."""
    if template.suffix.lower() != ".sla" or not template.is_file():
        raise RenderError(f"Machine signs need a Scribus template, but found: {template}")
    check_output(template, dest)
    content = load_sign_content(data)
    return render_signs(plan_signs(fetch_machines(), content, asset_ids), template, dest)


def describe_run(run: SignRun, dest: Path) -> list[str]:
    """Return what to tell a person about a run."""
    failures = [
        f"{sign.machine.asset_id} {sign.machine.name}: {message}"
        for sign in run.failed
        for message in sign.messages
    ]
    count = len(run.printed)
    outcome = (
        f"Wrote {count} sign{'' if count == 1 else 's'} to {dest}"
        if run.printed
        else f"No signs printed, so {dest} wasn't changed"
    )
    return [*describe_incomplete(run.incomplete), *failures, outcome]
