"""Command-line interface for signs."""

from importlib.metadata import version
from typing import Annotated

import typer

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
