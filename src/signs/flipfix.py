"""Read the museum's machines from FlipFix."""

import os
import re
from dataclasses import dataclass

import httpx

from signs.problems import MachineDataError

MACHINES_URL = "https://flipfix.theflip.museum/api/v1/machines/"
KEY_VARIABLE = "FLIPFIX_API_KEY"
FLOOR_LOCATIONS = frozenset({"Museum", "Coin-op"})
OFF_FLOOR_LOCATIONS = frozenset({"Storage", "Workshop"})
VALID_API_KEY = re.compile(r"[!-~]+")
TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class Machine:
    """A physical machine. Two machines of one model are two of these."""

    asset_id: str
    name: str
    location: str | None

    @property
    def is_on_floor(self) -> bool:
        return self.location in FLOOR_LOCATIONS

    @property
    def is_off_floor(self) -> bool:
        return self.location in OFF_FLOOR_LOCATIONS


def read_api_key() -> str:
    """Return the API key, refusing one that can't go in a header.

    httpx quotes a bad header in its error, which would print the key.
    """
    api_key = os.environ.get(KEY_VARIABLE, "").strip()
    if not api_key:
        raise MachineDataError(f"Set {KEY_VARIABLE} to read machines from FlipFix")
    if not VALID_API_KEY.fullmatch(api_key):
        raise MachineDataError(f"{KEY_VARIABLE} has characters an API key can't contain")
    return api_key


def fetch_machines(transport: httpx.BaseTransport | None = None) -> list[Machine]:
    """Return every machine FlipFix knows about, wherever it is."""
    headers = {"Authorization": f"Bearer {read_api_key()}"}
    try:
        with httpx.Client(transport=transport, timeout=TIMEOUT_SECONDS) as client:
            response = client.get(MACHINES_URL, headers=headers).raise_for_status()
        return [
            Machine(item["asset_id"], item["name"], item["location"])
            for item in response.json()["machines"]
        ]
    except httpx.HTTPError as error:
        raise MachineDataError(f"Could not read machines from FlipFix: {error}") from error
    except (KeyError, TypeError, ValueError) as error:
        raise MachineDataError(f"FlipFix sent an unreadable machine list: {error!r}") from error
