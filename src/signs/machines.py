"""Sign content for machines, and which machines on the floor are ready for a sign."""

import csv
import re
from collections.abc import Iterable, Mapping, Sequence
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


@dataclass(frozen=True)
class PlannedSign:
    machine: Machine
    content: SignContent


@dataclass(frozen=True)
class SignPlan:
    signs: list[PlannedSign]
    incomplete: list[IncompleteMachine]


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


def sort_by_readiness(
    machines: Iterable[Machine], content: Mapping[str, SignContent]
) -> tuple[list[Machine], list[IncompleteMachine]]:
    ready = []
    incomplete = []
    for machine in machines:
        reason = why_incomplete(content.get(machine.asset_id))
        if reason is None:
            ready.append(machine)
        else:
            incomplete.append(IncompleteMachine(machine, reason))
    return ready, incomplete


def check_floor(machines: Iterable[Machine], content: Mapping[str, SignContent]) -> FloorReport:
    """Compare what's on the floor with the sign content we have."""
    by_asset_id = sorted(machines, key=lambda machine: machine.asset_id)
    ready, incomplete = sort_by_readiness((m for m in by_asset_id if m.is_on_floor), content)
    if not ready and not incomplete:
        raise MachineDataError("FlipFix lists no machines on the floor")
    unplaced = [m for m in by_asset_id if not m.is_on_floor and not m.is_off_floor]
    known = {machine.asset_id for machine in by_asset_id}
    return FloorReport(ready, incomplete, unplaced, sorted(content.keys() - known))


def plan_signs(
    machines: Sequence[Machine],
    content: Mapping[str, SignContent],
    asset_ids: Iterable[str] = (),
) -> SignPlan:
    """Choose the signs to print: the named machines, or else everything on the floor."""
    # People type asset ids in any case, so match them without it.
    named = list(dict.fromkeys(asset_id.upper() for asset_id in asset_ids))
    if named:
        by_id = {machine.asset_id.upper(): machine for machine in machines}
        unknown = [asset_id for asset_id in named if asset_id not in by_id]
        if unknown:
            raise MachineDataError(f"FlipFix has no machine {', '.join(unknown)}")
        ready, incomplete = sort_by_readiness([by_id[asset_id] for asset_id in named], content)
    else:
        report = check_floor(machines, content)
        ready, incomplete = report.ready, report.incomplete
    signs = [PlannedSign(machine, content[machine.asset_id]) for machine in ready]
    return SignPlan(signs, incomplete)


def describe_incomplete(incomplete: Iterable[IncompleteMachine]) -> list[str]:
    return [f"{i.machine.asset_id} {i.machine.name}: {i.reason}" for i in incomplete]


def describe_floor(report: FloorReport) -> list[str]:
    """Return what to tell a person about the floor."""
    floor_count = len(report.ready) + len(report.incomplete)
    return [
        *describe_incomplete(report.incomplete),
        *(f"{m.asset_id} {m.name}: unknown location {m.location}" for m in report.unplaced),
        *(
            f"{asset_id}: in the machine data, but not in FlipFix"
            for asset_id in report.unknown_asset_ids
        ),
        f"{len(report.ready)} of {floor_count} floor machines are ready for a sign",
    ]
