from pathlib import Path

import pytest

from signs.flipfix import Machine
from signs.machines import (
    FloorReport,
    IncompleteMachine,
    check_floor,
    describe_floor,
    load_sign_content,
    plan_signs,
)
from signs.problems import MachineDataError

MACHINE_DATA = Path(__file__).parents[1] / "data" / "machines.csv"
ON_FLOOR = Machine("M0001", "Ballyhoo", "Museum")
IN_STORAGE = Machine("M0031", "The Addams Family (Museum)", "Storage")
WRITTEN = {"MainText": "A *bagatelle* for the Depression."}


def write_csv(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "machines.csv"
    path.write_text(text)
    return path


def test_loads_rows_by_asset_id(tmp_path: Path) -> None:
    path = write_csv(tmp_path, 'asset_id,MainText\nM0001,"One\n\nTwo"\n')

    assert load_sign_content(path) == {"M0001": {"asset_id": "M0001", "MainText": "One\n\nTwo"}}


def test_checked_in_machine_data_loads() -> None:
    assert load_sign_content(MACHINE_DATA)


def test_duplicate_asset_id_is_refused(tmp_path: Path) -> None:
    path = write_csv(tmp_path, "asset_id,MainText\nM0001,One\nM0001,Two\n")

    with pytest.raises(MachineDataError, match="two rows for M0001"):
        load_sign_content(path)


def test_missing_asset_id_column_is_refused(tmp_path: Path) -> None:
    path = write_csv(tmp_path, "Title,MainText\nBallyhoo,One\n")

    with pytest.raises(MachineDataError, match="no asset_id column"):
        load_sign_content(path)


def test_missing_main_text_column_is_refused(tmp_path: Path) -> None:
    path = write_csv(tmp_path, "asset_id,Title\nM0001,Ballyhoo\n")

    with pytest.raises(MachineDataError, match="no MainText column"):
        load_sign_content(path)


def test_short_row_counts_as_blank_cells(tmp_path: Path) -> None:
    path = write_csv(tmp_path, "asset_id,MainText\nM0001\n")

    report = check_floor([ON_FLOOR], load_sign_content(path))

    assert report.incomplete == [IncompleteMachine(ON_FLOOR, "no main text")]


def test_row_with_extra_cells_is_refused(tmp_path: Path) -> None:
    path = write_csv(tmp_path, "asset_id,MainText\nM0001,One,Two\n")

    with pytest.raises(MachineDataError, match="line 2 has too many cells"):
        load_sign_content(path)


def test_row_without_an_asset_id_is_refused(tmp_path: Path) -> None:
    path = write_csv(tmp_path, "asset_id,MainText\n,One\n")

    with pytest.raises(MachineDataError, match="line 2 has no asset_id"):
        load_sign_content(path)


def test_missing_file_gives_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(MachineDataError, match="Could not read"):
        load_sign_content(tmp_path / "absent.csv")


def test_two_machines_of_one_model_are_checked_separately() -> None:
    coin_op = Machine("M0017", "The Addams Family (Coin Op)", "Coin-op")
    museum = Machine("M0031", "The Addams Family (Museum)", "Museum")

    report = check_floor([coin_op, museum], {"M0017": WRITTEN})

    assert report.ready == [coin_op]
    assert report.incomplete == [IncompleteMachine(museum, "no row in the machine data")]


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("", "no main text"),
        (" \n", "no main text"),
        ("[SEE SEPARATE DOCUMENT]", "placeholder main text: [SEE SEPARATE DOCUMENT]"),
    ],
)
def test_machine_without_real_text_is_incomplete(text: str, reason: str) -> None:
    report = check_floor([ON_FLOOR], {"M0001": {"MainText": text}})

    assert report.incomplete == [IncompleteMachine(ON_FLOOR, reason)]
    assert report.ready == []


def test_brackets_inside_real_text_are_fine() -> None:
    text = "He wanted [the] credit, and [the] fame."

    report = check_floor([ON_FLOOR], {"M0001": {"MainText": text}})

    assert report.ready == [ON_FLOOR]


def test_two_separate_bracketed_notes_are_real_text() -> None:
    text = "[Editor's note] A fine game, they said. [sic]"

    report = check_floor([ON_FLOOR], {"M0001": {"MainText": text}})

    assert report.ready == [ON_FLOOR]


def test_machines_off_the_floor_need_no_sign() -> None:
    report = check_floor([ON_FLOOR, IN_STORAGE], {"M0001": WRITTEN})

    assert report == FloorReport(ready=[ON_FLOOR], incomplete=[], unplaced=[], unknown_asset_ids=[])
    assert report.is_clean


@pytest.mark.parametrize("location", ["Main Floor", None])
def test_machine_in_an_unknown_place_is_reported(location: str | None) -> None:
    lost = Machine("M0002", "Carom", location)

    report = check_floor([ON_FLOOR, lost], {"M0001": WRITTEN})

    assert report.unplaced == [lost]
    assert not report.is_clean
    assert f"M0002 Carom: unknown location {location}" in describe_floor(report)


def test_empty_floor_is_an_error() -> None:
    with pytest.raises(MachineDataError, match="no machines on the floor"):
        check_floor([IN_STORAGE], {})


def test_row_for_a_machine_flipfix_does_not_know_is_reported() -> None:
    report = check_floor([ON_FLOOR], {"M0001": WRITTEN, "M9999": WRITTEN})

    assert report.unknown_asset_ids == ["M9999"]
    assert not report.is_clean


def test_describes_every_problem_and_the_total() -> None:
    other = Machine("M0002", "Carom", "Museum")
    report = check_floor([other, ON_FLOOR], {"M0001": WRITTEN, "M9999": WRITTEN})

    assert describe_floor(report) == [
        "M0002 Carom: no row in the machine data",
        "M9999: in the machine data, but not in FlipFix",
        "1 of 2 floor machines are ready for a sign",
    ]


def test_plan_defaults_to_ready_floor_machines() -> None:
    plan = plan_signs([ON_FLOOR, IN_STORAGE], {"M0001": WRITTEN, "M0031": WRITTEN})

    assert [sign.machine for sign in plan.signs] == [ON_FLOOR]


def test_plan_lists_incomplete_floor_machines() -> None:
    other = Machine("M0002", "Carom", "Museum")

    plan = plan_signs([ON_FLOOR, other], {"M0001": WRITTEN})

    assert plan.incomplete == [IncompleteMachine(other, "no row in the machine data")]


def test_named_machine_prints_even_off_the_floor() -> None:
    plan = plan_signs([ON_FLOOR, IN_STORAGE], {"M0031": WRITTEN}, ["m0031"])

    assert [sign.machine for sign in plan.signs] == [IN_STORAGE]
    assert plan.incomplete == []


def test_naming_an_unknown_machine_is_an_error() -> None:
    with pytest.raises(MachineDataError, match="no machine M9999"):
        plan_signs([ON_FLOOR], {"M0001": WRITTEN}, ["M9999"])


def test_naming_a_machine_twice_prints_it_once() -> None:
    plan = plan_signs([ON_FLOOR], {"M0001": WRITTEN}, ["M0001", "m0001"])

    assert [sign.machine for sign in plan.signs] == [ON_FLOOR]


def test_naming_matches_any_case_of_the_flipfix_id() -> None:
    lower_case = Machine("m0050", "Lower Case", "Museum")

    plan = plan_signs([lower_case], {"m0050": WRITTEN}, ["M0050", "m0050"])

    assert [sign.machine for sign in plan.signs] == [lower_case]
