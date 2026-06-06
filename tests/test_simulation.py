"""EP-003.1 — value generators (PR-F-030, requirements §11)."""

from __future__ import annotations

import pytest

from bbc_sim.models import BacnetObjectSpec, BacnetObjectType, UpdateConfig
from bbc_sim.simulation.generators import make_generator


def _analog(**update) -> BacnetObjectSpec:
    return BacnetObjectSpec(
        point_id="P1", object_type=BacnetObjectType.analogInput, object_instance=1,
        object_name="n", present_value=20.0, min_pres_value=0.0, max_pres_value=40.0,
        update=UpdateConfig(**update),
    )


def test_no_generator_when_mode_unset():
    assert make_generator(_analog()) is None


def test_random_walk_is_deterministic_and_bounded():
    g1 = make_generator(_analog(mode="random_walk", params={"step": 1.0}))
    g2 = make_generator(_analog(mode="random_walk", params={"step": 1.0}))
    seq1 = [g1.next(t) for t in range(50)]
    seq2 = [g2.next(t) for t in range(50)]
    assert seq1 == seq2  # deterministic (seeded by point_id)
    assert all(0.0 <= v <= 40.0 for v in seq1)  # clamped to [min, max]


def test_sinusoidal_oscillates_within_bounds():
    g = make_generator(_analog(mode="sinusoidal", params={"period": 10.0}))
    vals = [g.next(t) for t in range(40)]
    assert all(0.0 <= v <= 40.0 for v in vals)
    assert max(vals) > min(vals)  # actually varies


def test_replay_cycles_sequence():
    g = make_generator(_analog(mode="replay", params={"sequence": [1.0, 2.0, 3.0]}))
    assert [g.next(t) for t in range(5)] == [1.0, 2.0, 3.0, 1.0, 2.0]


def test_scenario_holds_then_steps():
    # scenario: list of (t, value) setpoints; value holds until next setpoint time.
    g = make_generator(_analog(
        mode="scenario", params={"setpoints": [[0, 10.0], [3, 25.0], [6, 5.0]]}
    ))
    assert g.next(0) == 10.0
    assert g.next(2) == 10.0
    assert g.next(3) == 25.0
    assert g.next(5) == 25.0
    assert g.next(7) == 5.0


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        make_generator(_analog(mode="teleport"))


def test_sinusoidal_rejects_nonpositive_period():
    with pytest.raises(ValueError):
        make_generator(_analog(mode="sinusoidal", params={"period": 0}))
