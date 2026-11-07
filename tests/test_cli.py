from importlib.metadata import version
from pathlib import Path

import pytest
from typer.testing import CliRunner

from signs import cli
from signs.cli import app
from signs.flipfix import KEY_VARIABLE, Machine
from signs.machine_signs import SignRun
from signs.machines import IncompleteMachine

runner = CliRunner()


def test_version_flag_prints_installed_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == version("signs")


def test_render_reports_a_missing_file_and_fails() -> None:
    result = runner.invoke(app, ["render", "no-such-sign.svg"])

    assert result.exit_code == 1
    assert "File not found: no-such-sign.svg" in result.stderr


def test_render_refuses_unknown_file_types() -> None:
    result = runner.invoke(app, ["render", "sign.txt"])

    assert result.exit_code == 1
    assert "Don't know how to render .txt" in result.stderr


def test_check_machines_without_a_key_says_what_to_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(KEY_VARIABLE, raising=False)

    result = runner.invoke(app, ["check-machines"])

    assert result.exit_code == 1
    assert KEY_VARIABLE in result.stderr


def write_machine_data(tmp_path: Path) -> str:
    path = tmp_path / "machines.csv"
    path.write_text("asset_id,MainText\nM0001,Written\n")
    return str(path)


def test_check_machines_passes_when_the_floor_is_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = [Machine("M0001", "Ballyhoo", "Museum")]
    monkeypatch.setattr(cli, "fetch_machines", lambda: machines)

    result = runner.invoke(app, ["check-machines", "--data", write_machine_data(tmp_path)])

    assert result.exit_code == 0
    assert "1 of 1 floor machines are ready for a sign" in result.stdout


def test_check_machines_lists_incomplete_machines_and_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = [Machine("M0001", "Ballyhoo", "Museum"), Machine("M0002", "Carom", "Museum")]
    monkeypatch.setattr(cli, "fetch_machines", lambda: machines)

    result = runner.invoke(app, ["check-machines", "--data", write_machine_data(tmp_path)])

    assert result.exit_code == 1
    assert "M0002 Carom: no row in the machine data" in result.stdout


def test_render_machines_refuses_a_bad_output_before_reading_flipfix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(KEY_VARIABLE, raising=False)
    template = tmp_path / "template.sla"
    template.touch()

    result = runner.invoke(app, ["render-machines", "--template", str(template), "-o", "x.txt"])

    assert result.exit_code == 1
    assert "Output must be a .pdf file" in result.stderr


def test_render_machines_refuses_a_template_it_cannot_fill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(KEY_VARIABLE, raising=False)

    result = runner.invoke(app, ["render-machines", "--template", "sign.svg"])

    assert result.exit_code == 1
    assert "need a Scribus template" in result.stderr


def test_render_machines_reports_the_run_and_fails_if_anything_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machine = Machine("M0001", "Ballyhoo", "Museum")
    incomplete = IncompleteMachine(Machine("M0002", "Carom", "Museum"), "no main text")
    run = SignRun([machine], [], [incomplete])
    monkeypatch.setattr(cli, "print_machine_signs", lambda *_: run)
    output = str(tmp_path / "signs.pdf")

    result = runner.invoke(app, ["render-machines", "--template", "t.sla", "-o", output])

    assert result.exit_code == 1
    assert "M0002 Carom: no main text" in result.stdout
    assert f"Wrote 1 sign to {output}" in result.stdout


def test_render_machines_passes_when_every_sign_prints(monkeypatch: pytest.MonkeyPatch) -> None:
    run = SignRun([Machine("M0001", "Ballyhoo", "Museum")], [], [])
    monkeypatch.setattr(cli, "print_machine_signs", lambda *_: run)

    result = runner.invoke(app, ["render-machines", "--template", "t.sla"])

    assert result.exit_code == 0
