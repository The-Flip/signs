from importlib.metadata import version

from typer.testing import CliRunner

from signs.cli import app

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
