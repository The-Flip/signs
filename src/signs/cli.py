"""Command-line interface for signs."""

from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer

from signs.flipfix import fetch_machines
from signs.machines import check_floor, describe_floor, load_sign_content
from signs.problems import MachineDataError, RenderError, TemplateCheckError
from signs.render import describe_problems, render

app = typer.Typer(no_args_is_help=True)


def print_version(requested: bool) -> None:
    if requested:
        typer.echo(version("signs"))
        raise typer.Exit


@app.callback()
def main(
    show_version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=print_version,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """Manage and print the museum's signs."""


@app.command("render")
def render_sign(
    source: Annotated[Path, typer.Argument(help="Template to render (.svg or .sla).")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="PDF to write. Defaults to SOURCE's name, here."),
    ] = None,
) -> None:
    """Render a template to PDF, refusing if its checks fail."""
    dest = output or Path(f"{source.stem}.pdf")
    try:
        render(source, dest)
    except TemplateCheckError as error:
        for line in describe_problems(error.problems):
            typer.echo(line, err=True)
        raise typer.Exit(1) from error
    except RenderError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(f"Wrote {dest}")


@app.command("check-machines")
def check_machines(
    data: Annotated[Path, typer.Option(help="CSV of machine sign content.")] = Path(
        "data/machines.csv"
    ),
) -> None:
    """List floor machines that aren't ready for a sign."""
    try:
        content = load_sign_content(data)
        report = check_floor(fetch_machines(), content)
    except MachineDataError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    for line in describe_floor(report):
        typer.echo(line)
    if not report.is_clean:
        raise typer.Exit(1)
