import secrets

import httpx
import pytest

from signs.flipfix import KEY_VARIABLE, Machine, fetch_machines
from signs.problems import MachineDataError

MACHINE = {"asset_id": "M0017", "name": "The Addams Family", "location": "Coin-op"}


@pytest.fixture
def api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = secrets.token_hex(16)
    monkeypatch.setenv(KEY_VARIABLE, key)
    return key


def respond_with(response: httpx.Response) -> httpx.MockTransport:
    return httpx.MockTransport(lambda _: response)


def test_fetches_machines_using_the_api_key(api_key: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {api_key}"
        return httpx.Response(200, json={"machines": [MACHINE]})

    machines = fetch_machines(httpx.MockTransport(handler))

    assert machines == [Machine("M0017", "The Addams Family", "Coin-op")]


def test_missing_api_key_says_what_to_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(KEY_VARIABLE, raising=False)

    with pytest.raises(MachineDataError, match=KEY_VARIABLE):
        fetch_machines()


def test_stray_whitespace_around_the_key_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    key = secrets.token_hex(16)
    monkeypatch.setenv(KEY_VARIABLE, f" {key}\n")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {key}"
        return httpx.Response(200, json={"machines": []})

    assert fetch_machines(httpx.MockTransport(handler)) == []


def test_malformed_key_is_refused_without_showing_it(monkeypatch: pytest.MonkeyPatch) -> None:
    key = f"{secrets.token_hex(16)}\n{secrets.token_hex(16)}"
    monkeypatch.setenv(KEY_VARIABLE, key)

    with pytest.raises(MachineDataError, match=KEY_VARIABLE) as caught:
        fetch_machines(httpx.MockTransport(lambda _: httpx.Response(200)))

    assert key.split()[0] not in str(caught.value)


@pytest.mark.usefixtures("api_key")
def test_rejected_key_gives_a_clear_error() -> None:
    with pytest.raises(MachineDataError, match="403"):
        fetch_machines(respond_with(httpx.Response(403, json={"success": False})))


@pytest.mark.usefixtures("api_key")
def test_unreachable_flipfix_gives_a_clear_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(MachineDataError, match="no route"):
        fetch_machines(httpx.MockTransport(handler))


@pytest.mark.usefixtures("api_key")
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="<html>Sign in</html>"),
        httpx.Response(200, json={"results": []}),
        httpx.Response(200, json={"machines": [{"asset_id": "M0017"}]}),
    ],
)
def test_unexpected_response_gives_a_clear_error(response: httpx.Response) -> None:
    with pytest.raises(MachineDataError, match="unreadable machine list"):
        fetch_machines(respond_with(response))


@pytest.mark.parametrize(
    ("location", "on_floor"),
    [("Museum", True), ("Coin-op", True), ("Storage", False), ("Workshop", False), (None, False)],
)
def test_floor_means_museum_and_coin_op(location: str | None, on_floor: bool) -> None:
    assert Machine("M0001", "Ballyhoo", location).is_on_floor is on_floor
