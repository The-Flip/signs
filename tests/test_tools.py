import os
import signal
import threading
import time

import pytest

from signs.problems import RenderError
from signs.tools import run_tool


def test_returns_exit_code_and_combined_output() -> None:
    result = run_tool(["sh", "-c", "echo out; echo err >&2; exit 3"], os.environ)

    assert result.returncode == 3
    assert result.output.split() == ["out", "err"]


def test_missing_program_gives_a_clear_error() -> None:
    with pytest.raises(RenderError, match="no-such-program is not installed"):
        run_tool(["no-such-program"], os.environ)


def test_timeout_kills_child_processes_too() -> None:
    started = time.monotonic()

    with pytest.raises(RenderError, match="timed out"):
        run_tool(["sh", "-c", "sleep 30 & wait"], os.environ, timeout=0.2)

    assert time.monotonic() - started < 5


def test_interrupt_does_not_wait_for_the_program() -> None:
    timer = threading.Timer(0.2, os.kill, [os.getpid(), signal.SIGINT])
    timer.start()
    started = time.monotonic()

    with pytest.raises(KeyboardInterrupt):
        run_tool(["sh", "-c", "sleep 30 & wait"], os.environ)

    assert time.monotonic() - started < 5
