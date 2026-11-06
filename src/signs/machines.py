"""Sign content for machines, and which machines on the floor are ready for a sign."""

import csv
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from signs.flipfix import Machine
from signs.problems import MachineDataError

type SignContent = Mapping[str, str]

REQUIRED_COLUMNS = ("asset_id", "MainText")
PLACEHOLDER_TEXT = re.compile(r"\[[^\]]*\]")


@dataclass(frozen=True)
class IncompleteMachine:
    machine: Machine
    reason: str


@dataclass(frozen=True)
class FloorReport:
    ready: list[Machine]
    incomplete: list[IncompleteMachine]
    unplaced: list[Machine]
    unknown_asset_ids: list[str]

    @property
    def is_clean(self) -> bool:
        return not (self.incomplete or self.unplaced or self.unknown_asset_ids)


def load_sign_content(path: Path) -> dict[str, SignContent]:
    """Read the sign content CSV, keyed by asset id."""
    content: dict[str, SignContent] = {}
    try:
        with path.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file, restval="")
            for column in REQUIRED_COLUMNS:
                if column not in (reader.fieldnames or []):
                    raise MachineDataError(f"{path} has no {column} column")
            for row in reader:
                if None in row:
                    raise MachineDataError(f"{path} line {reader.line_num} has too many cells")
                asset_id = row["asset_id"]
                if not asset_id:
                    raise MachineDataError(f"{path} line {reader.line_num} has no asset_id")
                if asset_id in content:
                    raise MachineDataError(f"{path} has two rows for {asset_id}")
                content[asset_id] = row
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise MachineDataError(f"Could not read {path}: {error}") from error
    return content


def why_incomplete(content: SignContent | None) -> str | None:
    """Say what stops a machine getting a sign, or None if nothing does."""
    if content is None:
        return "no row in the machine data"
    text = content["MainText"].strip()
    if not text:
        return "no main text"
    if PLACEHOLDER_TEXT.fullmatch(text):
        return f"placeholder main text: {text}"
    return None


def check_floor(machines: Iterable[Machine], content: Mapping[str, SignContent]) -> FloorReport:
    """Compare what's on the floor with the sign content we have."""
    by_asset_id = sorted(machines, key=lambda machine: machine.asset_id)
    ready = []
    incomplete = []
    for machine in filter(lambda machine: machine.is_on_floor, by_asset_id):
        reason = why_incomplete(content.get(machine.asset_id))
        if reason is None:
            ready.append(machine)
        else:
            incomplete.append(IncompleteMachine(machine, reason))
    if not ready and not incomplete:
        raise MachineDataError("FlipFix lists no machines on the floor")
    unplaced = [m for m in by_asset_id if not m.is_on_floor and not m.is_off_floor]
    known = {machine.asset_id for machine in by_asset_id}
    return FloorReport(ready, incomplete, unplaced, sorted(content.keys() - known))


def describe_floor(report: FloorReport) -> list[str]:
    """Return what to tell a person about the floor."""
    floor_count = len(report.ready) + len(report.incomplete)
    return [
        *(f"{i.machine.asset_id} {i.machine.name}: {i.reason}" for i in report.incomplete),
        *(f"{m.asset_id} {m.name}: unknown location {m.location}" for m in report.unplaced),
        *(
            f"{asset_id}: in the machine data, but not in FlipFix"
            for asset_id in report.unknown_asset_ids
        ),
        f"{len(report.ready)} of {floor_count} floor machines are ready for a sign",
    ]
