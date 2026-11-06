"""Export Scribus SLA templates to PDF."""

import json
from collections.abc import Mapping
from pathlib import Path
from tempfile import TemporaryDirectory

from signs.problems import Problem, RenderError, TemplateCheckError
from signs.tools import run_tool

# Kept in its own directory because Python puts a script's directory on sys.path, and
# nothing there may shadow the `scribus` module.
EXPORT_SCRIPT = Path(__file__).parent / "scribus_scripts" / "export_checked.py"
LOG_LINES_TO_SHOW = 20


def parse_report(report: str) -> list[Problem]:
    try:
        return [Problem(item["kind"], item["message"]) for item in json.loads(report)]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise RenderError(f"Scribus wrote an unreadable report: {error}") from error


def export_sla(source: Path, dest: Path, env: Mapping[str, str]) -> None:
    with TemporaryDirectory(prefix="signs-scribus-") as work:
        prefs = Path(work) / "prefs"
        prefs.mkdir()
        report = Path(work) / "report.json"
        result = run_tool(
            [
                "xvfb-run",
                "--auto-servernum",
                "scribus",
                "--no-gui",
                "--no-splash",
                "--prefs",
                str(prefs),
                "--python-script",
                str(EXPORT_SCRIPT),
                str(source.resolve()),
                str(dest),
                str(report),
            ],
            env,
        )
        if not report.exists():
            log = "\n".join(result.output.splitlines()[-LOG_LINES_TO_SHOW:])
            raise RenderError(f"Scribus could not process {source}:\n{log}")
        problems = parse_report(report.read_text())

    if problems:
        raise TemplateCheckError(problems)
    if not dest.exists():
        raise RenderError(f"Scribus reported no problems but wrote no PDF for {source}")
