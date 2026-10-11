"""
TODO(bootcamper): write the tests for ``src/waypoint_utils.py`` in here.

The example below covers files that parse fine: with and without ``home``,
and files with comments and blank lines in them. The rest is yours:

- Bad data: a file whose top level isn't a mapping, waypoints missing
  ``lat``, ``lon``, or ``alt``, values that aren't numbers, YAML that
  doesn't parse, and a file that isn't there.
- Out of range: latitudes past +/-90 and longitudes past +/-180 get
  rejected.
- ``east_north_coordinate_offset_m``: offsets you worked out yourself,
  compared with ``pytest.approx``. Never use ``==`` on meters.
- Nothing to work with: an empty file, an empty ``waypoints`` list, and
  ``sort_clockwise_sweep`` given a list of 0 or 1 waypoints.

- Ordering: with no ``home``, ``sort_clockwise_sweep`` goes clockwise
  starting from north.
- With a ``home``: the order starts in home's direction instead, and goes
  back to starting at north if home is right on top of the centroid.
- Two waypoints in the same direction: the closer one comes first.
- Parsing gives you frozen ``Coordinate`` objects that can't be changed.

Graded by ``warg run utils grade-tests``: pass on the real code, 90% branch
coverage, and fail on every broken copy in ``grader/mutants/``.
"""

import pytest

from src.types import Coordinate
from src.waypoint_utils import (
    east_north_coordinate_offset_m,
    parse_waypoints_file,
    sort_clockwise_sweep,
)

# The helper and the test below are given to you.


def write_to_tmp_waypoints_file(tmp_path, text):
    """Write ``text`` to a YAML file and hand back its path.

    ``tmp_path`` is a pytest fixture: a fresh empty directory per test.
    """
    path = tmp_path / "waypoints.yaml"
    path.write_text(text)
    return path


# One test, three files. ``parametrize`` runs the test body once per
# ``(text, expected)`` pair, and ``ids`` names each run so a failure tells you
# which file broke.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            """
            home: {lat: 1, lon: 2, alt: 3}
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
        (
            """
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
              - {lat: 7, lon: 8, alt: 9}
            """,
            (None, [Coordinate(4, 5, 6), Coordinate(7, 8, 9)]),
        ),
        (
            """
            # a lap

            home: {lat: 1, lon: 2, alt: 3}

            waypoints:
              # first leg
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
    ],
    ids=["home-and-waypoints", "no-home", "comments-and-blank-lines"],
)
def test_parse_waypoints_file_success(tmp_path, text, expected):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    assert parse_waypoints_file(path) == expected


@pytest.mark.parametrize(
    ("text", "expected_exception"),
    [
        (
            """
          home: {lat: 91, lon: 2, alt: 3}
          waypoints:
            - {lat: 4, lon: 5, alt: 6}
          """,
            ValueError,
        ),
        (
            """
          home: {lat: 2, lon: 199, alt: 3}
          waypoints:
            - {lat: 4, lon: 5, alt: 6}
          """,
            ValueError,
        ),
        (
            """
        home: {lat: 2, lon: 185, alt: 3}
        waypoints:
          - {lat: 95, lon: 5, alt: 6}
        """,
            ValueError,
        ),
        (
            """
        home: {lat: 2, lon: 3, alt: 3}
        waypoints:
        - {lat: 4, lon: 189, alt: 6}
        """,
            ValueError,
        ),
    ],
)
def test_rejects_out_of_range_waypoints(tmp_path, text, expected_exception):
    with pytest.raises(expected_exception):
        path = write_to_tmp_waypoints_file(tmp_path, text)
        parse_waypoints_file(path)


@pytest.mark.parametrize(
    ("text", "expected_exception"),
    [
        (
            """
        home: {lata: 1, lon: 2, alt: 3}
        waypoints:
          - {lat: 4, lon: 5, alt: 6}
        """,
            ValueError,
        ),
        (
            """
        home: {lat: 1, lonb: 2, alt: 3}
        waypoints:
          - {lat: , lon: 5, alt: 6}
        """,
            ValueError,
        ),
        (
            """
        home: {lat: 1, lon: 2, alt: 3}
        waypoints:
          - {lat: , lon: 5, altc: 6}
        """,
            ValueError,
        ),
        (
            """
        waypoints:
          asjd
        """,
            ValueError,
        ),
        (
            """
        q3ji340asjd
        """,
            ValueError,
        ),
        (
            """
        waypoints:
          - {lat: "bob", lon: "jim", alt: 6}
          - {lat: 7, lon: 8, alt: "abc"}
        """,
            ValueError,
        ),
        (
            """
        waypoints:
          - {lat: 2, lon: 3}
          - {lat: 7, lon: 8}
        """,
            ValueError,
        ),
    ],
)
def test_rejects_bad_data(tmp_path, text, expected_exception):
    with pytest.raises(expected_exception):
        path = write_to_tmp_waypoints_file(tmp_path, text)
        parse_waypoints_file(path)


def test_rejects_none_yaml():
    with pytest.raises(OSError):
        parse_waypoints_file("/random.yaml")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            """
          
          """,
            (None, []),
        ),
        (
            """
          waypoints:
          """,
            (None, []),
        ),
        (
            """
          # bob
          home:
          waypoints:
          """,
            (None, []),
        ),
    ],
)
def test_empty(tmp_path, text, expected):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    assert parse_waypoints_file(path) == expected


@pytest.mark.parametrize(
    ("from_lat", "from_lon", "to_lat", "to_lon", "expected"),
    [
        (43.0, -79.0, 43.0, -79.0, (0.0, 0.0)),
        (0.0, 0.0, 0.001, 0.0, (0.0, 111.1951)),
        (0.0, 0.0, -0.001, 0.0, (0.0, -111.1951)),
        (0.0, 0.0, 0.0, 0.001, (111.1951, 0.0)),
        (0.0, 0.0, 0.0, -0.001, (-111.1951, 0.0)),
        (0.0, 0.0, 0.001, 0.001, (111.1951, 111.1951)),
        (60.0, 0.0, 60.0, 0.001, (55.5975, 0.0)),
        (-0.001, 0.0, 0.001, 0.0, (0.0, 222.3902)),
    ],
)
def test_east_north_offset_m(from_lat, from_lon, to_lat, to_lon, expected):
    e, n = east_north_coordinate_offset_m(from_lat, from_lon, to_lat, to_lon)
    assert e == pytest.approx(expected[0], abs=0.01)
    assert n == pytest.approx(expected[1], abs=0.01)


@pytest.mark.parametrize(
    ("waypoints", "home", "expected"),
    [
        ([(1, 2, 3)], None, [(1, 2, 3)]),
        ([], None, []),
    ],
)
def test_zero_or_one_coords(waypoints, home, expected):
    sorted_list = sort_clockwise_sweep(waypoints, home)
    assert sorted_list == expected


@pytest.mark.parametrize(
    ("waypoints", "home", "expected"),
    [
        (
            [
                Coordinate(0.001, 0.0, 10.0),
                Coordinate(0.0, 0.001, 20.0),
                Coordinate(-0.001, 0.0, 30.0),
                Coordinate(0.0, -0.001, 40.0),
            ],
            None,
            [
                Coordinate(0.001, 0.0, 10.0),
                Coordinate(0.0, 0.001, 20.0),
                Coordinate(-0.001, 0.0, 30.0),
                Coordinate(0.0, -0.001, 40.0),
            ],
        ),
        (
            [
                Coordinate(0.001, 0.0, 10.0),
                Coordinate(0.0, 0.001, 20.0),
                Coordinate(-0.001, 0.0, 30.0),
                Coordinate(0.0, -0.001, 40.0),
            ],
            Coordinate(0.0, 0.001, 50.0),
            [
                Coordinate(0.0, 0.001, 20.0),
                Coordinate(-0.001, 0.0, 30.0),
                Coordinate(0.0, -0.001, 40.0),
                Coordinate(0.001, 0.0, 10.0),
            ],
        ),
        (
            [
                Coordinate(0.001, 0.0, 10.0),
                Coordinate(0.0, 0.001, 20.0),
                Coordinate(-0.001, 0.0, 30.0),
                Coordinate(0.0, -0.001, 40.0),
            ],
            Coordinate(0.0, 0.0, 50.0),
            [
                Coordinate(0.001, 0.0, 10.0),
                Coordinate(0.0, 0.001, 20.0),
                Coordinate(-0.001, 0.0, 30.0),
                Coordinate(0.0, -0.001, 40.0),
            ],
        ),
        (
            [
                Coordinate(0.002, 0.0, 10.0),
                Coordinate(0.001, 0.0, 20.0),
                Coordinate(0.0, 0.001, 30.0),
                Coordinate(0.0, -0.001, 40.0),
                Coordinate(-0.003, 0.0, 50.0),
            ],
            None,
            [
                Coordinate(0.001, 0.0, 20.0),
                Coordinate(0.002, 0.0, 10.0),
                Coordinate(0.0, 0.001, 30.0),
                Coordinate(-0.003, 0.0, 50.0),
                Coordinate(0.0, -0.001, 40.0),
            ],
        ),
        (
            [
                Coordinate(0.002, 0.0, 10.0),
                Coordinate(0.001, 0.0, 20.0),
                Coordinate(0.0, 0.001, 30.0),
                Coordinate(0.0, -0.001, 40.0),
                Coordinate(-0.003, 0.0, 50.0),
            ],
            Coordinate(0.001, 0.0, 60.0),
            [
                Coordinate(0.001, 0.0, 20.0),
                Coordinate(0.002, 0.0, 10.0),
                Coordinate(0.0, 0.001, 30.0),
                Coordinate(-0.003, 0.0, 50.0),
                Coordinate(0.0, -0.001, 40.0),
            ],
        ),
        (
            [
                Coordinate(43.001, -79.0, 10.0),
                Coordinate(43.0, -78.999, 20.0),
                Coordinate(42.999, -79.0, 30.0),
                Coordinate(43.0, -79.001, 40.0),
            ],
            None,
            [
                Coordinate(43.001, -79.0, 10.0),
                Coordinate(43.0, -78.999, 20.0),
                Coordinate(42.999, -79.0, 30.0),
                Coordinate(43.0, -79.001, 40.0),
            ],
        ),
        (
            [Coordinate(43.0, -79.0, 10.0)],
            None,
            [Coordinate(43.0, -79.0, 10.0)],
        ),
        (
            [],
            None,
            [],
        ),
    ],
)
def test_ordering(waypoints, home, expected):
    assert sort_clockwise_sweep(waypoints, home) == expected


def test_placeholder():
    # TODO(bootcamper): delete this and write real tests. It's only here so
    # linter doesn't complain about unused imports before you start.
    assert callable(east_north_coordinate_offset_m)
    assert callable(parse_waypoints_file)
    assert callable(sort_clockwise_sweep)
