"""Run the external programs that signs depends on."""

import os
import shutil
import signal
import subprocess
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass

from signs.problems import RenderError

TOOL_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class ToolResult:
    returncode: int
    output: str


def kill_process_group(process: subprocess.Popen[str]) -> None:
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)


def run_tool(
    command: Sequence[str],
    env: Mapping[str, str],
    timeout: float = TOOL_TIMEOUT_SECONDS,
) -> ToolResult:
    """Run a program and return its combined output.

    The program gets its own process group so that a timeout also kills its children.
    `xvfb-run` starts Scribus as a child, which would otherwise outlive it. That also
    keeps Ctrl-C from reaching the program, so an interrupt has to kill the group here.
    """
    program = shutil.which(command[0])
    if program is None:
        raise RenderError(f"{command[0]} is not installed; see README.md for system packages")

    with subprocess.Popen(
        [program, *command[1:]],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        start_new_session=True,
    ) as process:
        try:
            output, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            kill_process_group(process)
            process.communicate()
            raise RenderError(f"{command[0]} timed out after {timeout} seconds") from error
        except BaseException:
            kill_process_group(process)
            raise
    return ToolResult(returncode=process.returncode, output=output)
