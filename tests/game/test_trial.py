import uuid
from unittest.mock import MagicMock, patch

import pytest

from pyxis_portfolio_challenge.game.trial import (
    Trial,
    TrialPhase,
    TrialState,
    trials_json_to_trials_sequence,
)
from pyxis_portfolio_challenge.rng import init_game_rng


def test_trial_init():
    trial = Trial(cost_remaining=100, time_remaining=5, ptrs=0.5, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)
    assert trial.cost_remaining == 100
    assert trial.time_remaining == 5
    assert trial.ptrs == 0.5
    assert trial.state == TrialState.PENDING
    assert trial.phase == TrialPhase.PHASE_1
    assert trial.next_trial_on_success is None


@pytest.mark.parametrize(
    "ptrs,should_raise",
    [
        (0.5, False),
        (-0.1, True),
        (1.5, True),
        (0, False),
        (1, False),
        (None, True),
        (float("nan"), True),
    ],
)
def test_valid_invalid_ptrs(ptrs, should_raise):

    if should_raise:
        with pytest.raises(ValueError):
            Trial(cost_remaining=100, time_remaining=5, ptrs=ptrs, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)
    else:
        Trial(cost_remaining=100, time_remaining=5, ptrs=ptrs, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)


@pytest.mark.parametrize(
    "cost_remaining,should_raise", [(100, False), (0, False), (-50, True), (None, True)]
)
def test_validate_cost_remaining(cost_remaining, should_raise):
    if should_raise:
        with pytest.raises(ValueError):
            Trial(cost_remaining=cost_remaining, time_remaining=5, ptrs=0.5, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)
    else:
        trial = Trial(cost_remaining=cost_remaining, time_remaining=5, ptrs=0.5, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)
        assert trial.cost_remaining == cost_remaining


@pytest.mark.parametrize(
    "time_remaining,should_raise", [(100, False), (0, False), (-50, True), (None, True)]
)
def test_validate_time_remaining(time_remaining, should_raise):
    if should_raise:
        with pytest.raises(ValueError):
            Trial(cost_remaining=100, time_remaining=time_remaining, ptrs=0.5, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)
    else:
        trial = Trial(cost_remaining=100, time_remaining=time_remaining, ptrs=0.5, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)
        assert trial.time_remaining == time_remaining


def test_trial_ptrs_reassignment():
    trial = Trial(cost_remaining=100, time_remaining=5, ptrs=0.5, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)
    trial.ptrs = 0.8  # Reassigning to a valid value
    assert trial.ptrs == 0.8

    with pytest.raises(ValueError):
        trial.ptrs = -0.1  # Invalid value should raise ValueError


@pytest.mark.parametrize(
    "cost_remaining,time_remaining,expected_cost_this_step",
    [(100, 5, 20), (500, 10, 50), (0, 0, 0)],
)
def test_trial_cost_this_step(cost_remaining, time_remaining, expected_cost_this_step):
    trial = Trial(
        cost_remaining=cost_remaining, time_remaining=time_remaining, ptrs=0.5, state=TrialState.IN_PROGRESS, phase=TrialPhase.PHASE_1, next_trial_on_success=None
    )
    assert trial.cost_this_step == expected_cost_this_step


def test_next_trial_on_success():
    next_trial = Trial(cost_remaining=200, time_remaining=10, ptrs=0.6, state=TrialState.PENDING, phase=TrialPhase.PHASE_2, next_trial_on_success=None)
    trial = Trial(cost_remaining=100, time_remaining=5, ptrs=0.5, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=next_trial)
    assert trial.next_trial_on_success == next_trial


def test_trial_phase():
    assert TrialPhase.PHASE_1 in TrialPhase
    assert TrialPhase.PHASE_2 in TrialPhase
    assert TrialPhase.PHASE_3 in TrialPhase

def test_trial_phase_from_string():
    assert TrialPhase("Phase 1") == TrialPhase.PHASE_1
    assert TrialPhase("Phase 2") == TrialPhase.PHASE_2
    assert TrialPhase("Phase 3") == TrialPhase.PHASE_3

def test_trial_phase_from_int():
    assert TrialPhase.from_int(0) == TrialPhase.PHASE_1
    assert TrialPhase.from_int(1) == TrialPhase.PHASE_2
    assert TrialPhase.from_int(2) == TrialPhase.PHASE_3

def test_order_trial_phases():
    expected_phases = [TrialPhase.PHASE_1, TrialPhase.PHASE_2, TrialPhase.PHASE_3]
    for exp_phase, phase in zip(expected_phases, TrialPhase):
        assert exp_phase == phase

def test_trial_state_enum():
    assert TrialState.PENDING in TrialState
    assert TrialState.IN_PROGRESS in TrialState
    assert TrialState.PHASE_SUCCESS in TrialState
    assert TrialState.PHASE_FAILED in TrialState

def test_trial_state_from_int():
    assert TrialState(0) == TrialState.PENDING
    assert TrialState(1) == TrialState.IN_PROGRESS
    assert TrialState(2) == TrialState.PHASE_SUCCESS
    assert TrialState(3) == TrialState.PHASE_FAILED


@pytest.fixture
def dummy_trial_json():
    return {
        "phase_1": {
            "cost_remaining": 40000000,
            "time_remaining": 2,
            "ptrs": 0.6
        },
        "phase_2": {
            "cost_remaining": 150000000,
            "time_remaining": 3,
            "ptrs": 0.35
        },
        "phase_3": {
            "cost_remaining": 600000000,
            "time_remaining": 4,
            "ptrs": 0.5
        }
    }


def test_asset_json_to_trials_sequence(dummy_trial_json):
    init_game_rng(42)
    trial = trials_json_to_trials_sequence(dummy_trial_json, asset_id="some-uuid", pending_trial_phase="Phase 1", approval_phase_config=None, trial_cost_multiplier=1.0)
    assert isinstance(trial, Trial)
    assert trial.phase == TrialPhase.PHASE_1
    assert trial.next_trial_on_success is not None
    assert trial.next_trial_on_success.phase == TrialPhase.PHASE_2
    assert trial.next_trial_on_success.next_trial_on_success is not None
    assert trial.next_trial_on_success.next_trial_on_success.phase == TrialPhase.PHASE_3
    assert trial.next_trial_on_success.next_trial_on_success.next_trial_on_success is None


def test_trial_success_ptrs_1():
    trial = Trial(cost_remaining=100, time_remaining=1, ptrs=1.0, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)
    mock_rng = MagicMock()
    mock_rng.random.return_value = 0.5
    with patch("pyxis_portfolio_challenge.game.trial.get_game_rng", return_value=mock_rng):
        assert trial.success() is True


def test_trial_success_ptrs_0():
    trial = Trial(cost_remaining=100, time_remaining=1, ptrs=0.0, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)
    mock_rng = MagicMock()
    mock_rng.random.return_value = 0.5
    with patch("pyxis_portfolio_challenge.game.trial.get_game_rng", return_value=mock_rng):
        assert trial.success() is False


def test_trial_success_rng_lt_ptrs():
    trial = Trial(cost_remaining=100, time_remaining=1, ptrs=0.5, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)
    mock_rng = MagicMock()
    mock_rng.random.return_value = 0.4
    with patch("pyxis_portfolio_challenge.game.trial.get_game_rng", return_value=mock_rng):
        assert trial.success() is True


def test_trial_cost_this_step_calculation():
    trial = Trial(cost_remaining=100, time_remaining=4, ptrs=0.5, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)
    assert trial.cost_this_step == 25.0  # 100 / 4


def test_trial_cost_this_step_zero_time():
    trial = Trial(cost_remaining=100, time_remaining=0, ptrs=0.5, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)
    assert trial.cost_this_step == 0.0


@pytest.fixture
def trial_with_sequence_always_success():
    next_next_trial = Trial(cost_remaining=50, time_remaining=1, ptrs=0.4, state=TrialState.PHASE_SUCCESS, phase=TrialPhase.PHASE_3, next_trial_on_success=None)

    next_trial = Trial(cost_remaining=50, time_remaining=2, ptrs=0.6, state=TrialState.PENDING, phase=TrialPhase.PHASE_2, next_trial_on_success=next_next_trial)

    trial = Trial(cost_remaining=100, time_remaining=5, ptrs=0.5, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=next_trial)

    return trial


def test_trial_evolve_full_sequence(trial_with_sequence_always_success):
    trial_with_sequence = trial_with_sequence_always_success
    mock_rng = MagicMock()
    mock_rng.random.return_value = 0.3  # Always below ptrs to succeed
    with patch("pyxis_portfolio_challenge.game.trial.get_game_rng", return_value=mock_rng):
        for _ in range(8): # Total steps to complete all phases
            trial_with_sequence = trial_with_sequence.evolve()

    assert trial_with_sequence.state == TrialState.PHASE_SUCCESS
    assert trial_with_sequence.next_trial_on_success is None
    assert trial_with_sequence.phase == TrialPhase.PHASE_3
    assert trial_with_sequence.ptrs == 1.0
    assert trial_with_sequence.cost_remaining == 0.0
    assert trial_with_sequence.time_remaining == 0


def test_trial_evolve_incomplete_phase(trial_with_sequence_always_success):
    trial_with_sequence = trial_with_sequence_always_success
    mock_rng = MagicMock()
    mock_rng.random.return_value = 0.3
    with patch("pyxis_portfolio_challenge.game.trial.get_game_rng", return_value=mock_rng):
        # Evolve only 3 times, should still be in Phase 1
        for _ in range(3):
            trial_with_sequence = trial_with_sequence.evolve()

    assert trial_with_sequence.phase == TrialPhase.PHASE_1
    assert trial_with_sequence.state == TrialState.IN_PROGRESS
    assert trial_with_sequence.time_remaining == 2  # 5 - 3 steps
    assert trial_with_sequence.cost_remaining == 40.0  # 100 - (20 * 3)


def test_single_trial_evolve_success():
    next_trial = Trial(cost_remaining=0, time_remaining=0, ptrs=0.0, state=TrialState.PENDING, phase=TrialPhase.PHASE_2, next_trial_on_success=None)

    trial = Trial(cost_remaining=20, time_remaining=1, ptrs=1.0, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=next_trial)
    mock_rng = MagicMock()
    mock_rng.random.return_value = 0.0
    with patch("pyxis_portfolio_challenge.game.trial.get_game_rng", return_value=mock_rng):
        evolved_trial = trial.evolve()
    assert evolved_trial == next_trial


def test_single_trial_evolve_failure():
    trial = Trial(cost_remaining=20, time_remaining=1, ptrs=0.5, state=TrialState.PENDING, phase=TrialPhase.PHASE_1, next_trial_on_success=None)
    mock_rng = MagicMock()
    mock_rng.random.return_value = 0.5  # draw above ptrs to fail
    with patch("pyxis_portfolio_challenge.game.trial.get_game_rng", return_value=mock_rng):
        evolved_trial = trial.evolve()
    assert evolved_trial.state == TrialState.PHASE_FAILED
    assert evolved_trial.cost_remaining == 0.0
    assert evolved_trial.time_remaining == 0
    assert evolved_trial.ptrs == 0.
    assert evolved_trial.phase == TrialPhase.PHASE_1


def test_trials_json_to_trials_sequence_returns_phase_2_head():
    asset_id = uuid.uuid4()
    seed = 42

    trials_json = {
        "phase_1": {
            "cost_remaining": 0,
            "time_remaining": 0,
            "ptrs": 0.65,
        },
        "phase_2": {
            "cost_remaining": 120_000_000,
            "time_remaining": 3,
            "ptrs": 0.4,
        },
        "phase_3": {
            "cost_remaining": 450_000_000,
            "time_remaining": 3,
            "ptrs": 0.58,
        },
    }

    # Act
    init_game_rng(seed)
    head_trial = trials_json_to_trials_sequence(
        json=trials_json,
        asset_id=asset_id,
        pending_trial_phase="Phase 2",
        approval_phase_config=None,
        trial_cost_multiplier=1.0,
    )

    # Assert: head should be Phase 2
    assert head_trial.phase == TrialPhase("Phase 2")
    assert head_trial.cost_remaining == 120_000_000
    assert head_trial.time_remaining == 3
    assert head_trial.ptrs == 0.4

    # Assert: Phase 2 should link to Phase 3
    next_trial = head_trial.next_trial_on_success
    assert next_trial is not None
    assert next_trial.phase == TrialPhase("Phase 3")
    assert next_trial.cost_remaining == 450_000_000
    assert next_trial.time_remaining == 3
    assert next_trial.ptrs == 0.58

    # Assert: Phase 3 should be terminal
    assert next_trial.next_trial_on_success is None
