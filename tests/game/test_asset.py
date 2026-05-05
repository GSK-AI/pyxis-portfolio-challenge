import random
import uuid
from typing import Optional

import numpy as np
import pytest

from pyxis_portfolio_challenge.game.asset import AssetState, DrugAsset, revenue_formula
from pyxis_portfolio_challenge.game.constants import DISCOUNT_RATE
from pyxis_portfolio_challenge.game.trial import (
    Trial,
    TrialPhase,
    TrialState,
    trials_json_to_trials_sequence,
)


def test_revenue_formula():
    max_revenue = 1000.0
    time_until_max_revenue = 4

    assert revenue_formula(1, max_revenue, time_until_max_revenue) == 200.0
    assert revenue_formula(2, max_revenue, time_until_max_revenue) == 400.0
    assert revenue_formula(3, max_revenue, time_until_max_revenue) == 600.0
    assert revenue_formula(4, max_revenue, time_until_max_revenue) == 800.0
    assert revenue_formula(5, max_revenue, time_until_max_revenue) == 1000.0


def drug_asset_factory(
    id: Optional[uuid.UUID] = None,
    max_revenue: float = 1_000_000_000.0,
    time_until_max_revenue: int = 5,
    time_until_patent_expiry: int = 20,
    state: AssetState = AssetState.Idle,
    time_on_market: int = 0,
    seed: int = 42,
    trials_schema: Optional[dict] = None,
    trial: Optional[Trial] = None,
) -> DrugAsset:
    """
    A flexible factory for creating DrugAsset instances for testing.

    Provides sensible defaults and allows overriding any parameter. Handles
    the creation of the trial sequence and the random number generator.
    """
    asset_id = id or uuid.uuid4()

    if trial and trials_schema is not None:
        raise ValueError("Provide either 'trial' or 'trials_schema', not both.")

    # Default trial schema if none is provided
    if trials_schema is None:
        trials_schema = {
            "phase_1": {"cost_remaining": 40_000_000, "time_remaining": 2, "ptrs": 0.6},
            "phase_2": {
                "cost_remaining": 150_000_000,
                "time_remaining": 3,
                "ptrs": 0.35,
            },
            "phase_3": {
                "cost_remaining": 600_000_000,
                "time_remaining": 4,
                "ptrs": 0.5,
            },
        }

    if state == AssetState.OnMarket:
        trial = Trial(
            cost_remaining=0.0,
            time_remaining=0,
            ptrs=1.0,
            phase=TrialPhase.PHASE_3,
            state=TrialState.PHASE_SUCCESS,
            next_trial_on_success=None,
        )

    elif state == AssetState.InDevelopment and trial is None:
        trial = Trial(
            cost_remaining=1000.0,
            time_remaining=1,
            ptrs=0.8,
            phase=TrialPhase.PHASE_3,
            state=TrialState.IN_PROGRESS,
            next_trial_on_success=None,
        )
        trial._rng = random.Random(f"{seed}_{asset_id}_{trial.phase.name}")

    elif trial is None:
        trial = trials_json_to_trials_sequence(trials_schema, seed, asset_id, pending_trial_phase="Phase 1", approval_phase_config=None, trial_cost_multiplier=1.0)

    asset = DrugAsset(
        id=asset_id,
        name="Test Drug",
        therapeutic_area="oncology",
        type="internal",
        description="A test drug asset.",
        max_revenue=max_revenue,
        time_until_max_revenue=time_until_max_revenue,
        time_until_patent_expiry=time_until_patent_expiry,
        trial=trial,
        state=state,
        time_on_market=time_on_market,
    )

    # Set the private _rng attribute
    asset._rng = random.Random(f"{seed}_{asset_id}")

    return asset


@pytest.mark.parametrize(
    "max_revenue,should_raise", [(100000, False), (0, False), (-50, True)]
)
def test_validate_max_revenue(max_revenue, should_raise):
    if should_raise:
        with pytest.raises(ValueError):
            asset = drug_asset_factory(max_revenue=max_revenue)
    else:
        asset = drug_asset_factory(max_revenue=max_revenue)
        assert isinstance(asset, DrugAsset)


@pytest.mark.parametrize(
    "time_until_max_revenue,should_raise",
    [(10, False), (1, False), (0, True), (-5, True)],
)
def test_validate_time_until_max_revenue(
    time_until_max_revenue, should_raise
):
    if should_raise:
        with pytest.raises(ValueError):
            asset = drug_asset_factory(time_until_max_revenue=time_until_max_revenue)
    else:
        asset = drug_asset_factory(time_until_max_revenue=time_until_max_revenue)
        assert isinstance(asset, DrugAsset)


@pytest.mark.parametrize(
    "time_until_patent_expiry,should_raise",
    [(10, False), (1, False), (0, False), (-5, True)],
)
def test_validate_time_until_patent_expiry(
    time_until_patent_expiry, should_raise
):
    if should_raise:
        with pytest.raises(ValueError):
            asset = drug_asset_factory(time_until_patent_expiry=time_until_patent_expiry)
    else:
        asset = drug_asset_factory(time_until_patent_expiry=time_until_patent_expiry)
        assert isinstance(asset, DrugAsset)


@pytest.mark.parametrize(
    "time_on_market,should_raise", [(10, False), (1, False), (0, False), (-5, True)]
)
def test_validate_time_on_market(time_on_market, should_raise):
    if should_raise:
        with pytest.raises(ValueError):
            asset = drug_asset_factory(
                time_on_market=time_on_market,
                state=AssetState.OnMarket,
            )
    else:
        asset = drug_asset_factory(
            time_on_market=time_on_market, state=AssetState.OnMarket
        )
        assert isinstance(asset, DrugAsset)


def test__projected_cash_flows():
    trials_schema = {
        "phase_1": {"cost_remaining": 40, "time_remaining": 2,
                    "ptrs": 0.6},
        "phase_2": {
            "cost_remaining": 150,
            "time_remaining": 3,
            "ptrs": 0.35,
        },
        "phase_3": {
            "cost_remaining": 600,
            "time_remaining": 4,
            "ptrs": 0.5,
        },
    }
    time_until_max_revenue = 3
    max_revenue = 100

    asset = drug_asset_factory(trials_schema=trials_schema, max_revenue=max_revenue, time_until_max_revenue=time_until_max_revenue)
    projected_cash_flows = asset._projected_cash_flows

    assert projected_cash_flows == [-20.0, -20.0, -50.0, -50.0, -50.0, -150.0, -150.0, -150.0, -150.0, 25.0, 50.0, 75.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]


def test__projected_probs():
    trials_schema = {
        "phase_1": {"cost_remaining": 40, "time_remaining": 2,
                    "ptrs": 0.6},
        "phase_2": {
            "cost_remaining": 150,
            "time_remaining": 3,
            "ptrs": 0.35,
        },
        "phase_3": {
            "cost_remaining": 600,
            "time_remaining": 4,
            "ptrs": 0.5,
        },
    }
    time_until_max_revenue = 3
    max_revenue = 100

    asset = drug_asset_factory(trials_schema=trials_schema, max_revenue=max_revenue, time_until_max_revenue=time_until_max_revenue)
    projected_probs = asset._projected_probs

    assert projected_probs == [1.0, 1.0, 0.6, 0.6, 0.6, 0.21, 0.21, 0.21, 0.21, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105]


def test_expected_costs_and_revenues():
    trials_schema = {
        "phase_1": {"cost_remaining": 40, "time_remaining": 2,
                    "ptrs": 0.6},
        "phase_2": {
            "cost_remaining": 150,
            "time_remaining": 3,
            "ptrs": 0.35,
        },
        "phase_3": {
            "cost_remaining": 600,
            "time_remaining": 4,
            "ptrs": 0.5,
        },
    }
    time_until_max_revenue = 3
    max_revenue = 100

    asset = drug_asset_factory(trials_schema=trials_schema, max_revenue=max_revenue, time_until_max_revenue=time_until_max_revenue)
    expected_costs, expected_revenues = asset.expected_costs_and_revenues

    assert expected_costs == [20.0, 20.0, 30.0, 30.0, 30.0, 31.5, 31.5, 31.5, 31.5, -0.0, -0.0, -0.0, -0.0, -0.0, -0.0, -0.0, -0.0, -0.0, -0.0, -0.0]
    assert expected_revenues == [ 0., 0., 0., 0., 0., 0., 0., 0., 0., 2.625, 5.25, 7.875, 10.5, 10.5, 10.5, 10.5, 10.5, 10.5, 10.5, 10.5]


def test_expected_costs_and_revenues_on_market():
    trial = Trial(
        cost_remaining=0.0,
        time_remaining=0,
        ptrs=1.0,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PHASE_SUCCESS,
        next_trial_on_success=None,
    )
    asset = drug_asset_factory(state=AssetState.OnMarket, time_on_market=2, time_until_max_revenue=5, max_revenue=100, trial=trial, time_until_patent_expiry=10)
    expected_costs, expected_revenues = asset.expected_costs_and_revenues

    assert expected_costs == [0.0 for _ in range(asset.time_until_patent_expiry)]
    assert expected_revenues == [50., 66.66666666666666, 83.33333333333334, 100, 100, 100, 100, 100, 100, 100]


def test_expected_costs_and_revenues_in_development():
    """
    Computed the true cash flows and probs by hand, assuming asset has only
    Phase 3 trial left, with time remaining 2, cost remaining 100 and PTRS 0.9.
    Thus there are two steps of -50 until asset starts accruing revenue with prob 0.9.
    """
    trial = Trial(
        cost_remaining=100,
        time_remaining=2,
        ptrs=0.5,
        phase=TrialPhase.PHASE_3,
        state=TrialState.IN_PROGRESS,
        next_trial_on_success=None,
    )
    asset = drug_asset_factory(state=AssetState.InDevelopment, time_on_market=0,
                               time_until_max_revenue=5, max_revenue=100,
                               trial=trial, time_until_patent_expiry=10)
    expected_costs, expected_revenues = asset.expected_costs_and_revenues

    assert expected_costs == [50.0, 50.0, 0., 0., 0., 0., 0., 0., 0., 0.]
    assert expected_revenues == [0.0, 0.0, 8.333333333333332, 16.666666666666664, 25.0, 33.33333333333333, 41.666666666666674, 50.0, 50.0, 50.0]


def test_npv_calculation_on_market():
    trial = Trial(
        cost_remaining=0.0,
        time_remaining=0,
        ptrs=1.0,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PHASE_SUCCESS,
        next_trial_on_success=None,
    )
    asset = drug_asset_factory(state=AssetState.OnMarket, trial=trial, time_on_market=5)
    npv = asset.enpv
    assert isinstance(npv, float)
    assert npv > 0
    true_value = 0
    for t in range(asset.time_until_patent_expiry):
        true_value += (1 / ((1 + DISCOUNT_RATE) ** t)) * asset.max_revenue
    assert npv == pytest.approx(true_value)


def test_eroi_calculation_on_market():
    trial = Trial(
        cost_remaining=0.0,
        time_remaining=0,
        ptrs=1.0,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PHASE_SUCCESS,
        next_trial_on_success=None,
    )
    asset = drug_asset_factory(state=AssetState.OnMarket, trial=trial, time_on_market=5)
    eroi = asset.eroi
    assert isinstance(eroi, float)
    assert eroi == 0


def test_eroi_calculation_in_development():
    """
    Computed the true cash flows and probs by hand, assuming asset has only
    Phase 3 trial left, with time remaining 2, cost remaining 100 and PTRS 0.9.
    Thus there are two steps of -50 until asset starts accruing revenue with prob 0.9.
    """
    trial = Trial(
        cost_remaining=100,
        time_remaining=2,
        ptrs=0.9,
        phase=TrialPhase.PHASE_3,
        state=TrialState.IN_PROGRESS,
        next_trial_on_success=None,
    )
    asset = drug_asset_factory(state=AssetState.InDevelopment,
                               time_on_market=0,
                               time_until_max_revenue=5, max_revenue=10000,
                               trial=trial, time_until_patent_expiry=10)
    eroi = asset.eroi

    true_cash_flows = [
        -50,
        -50,
        10000 / 6,
        2 * 10000 / 6,
        3 * 10000 / 6,
        4 * 10000 / 6,
        5 * 10000 / 6,
        10000,
        10000,
        10000,
    ]
    true_probs = [1, 1, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9]
    assert len(true_cash_flows) == len(true_probs)
    true_expected = np.array(true_cash_flows) * np.array(true_probs)

    true_costs = list(np.where(true_expected < 0, -true_expected, 0))
    true_revenues = list(np.where(true_expected > 0, true_expected, 0))
    true_eroi = (
        (sum(true_revenues) - sum(true_costs)) / sum(true_costs)
        if sum(true_costs) != 0
        else 0
    )
    assert eroi == pytest.approx(true_eroi)


def test_to_develop_idle_asset():
    asset = drug_asset_factory(state=AssetState.Idle)
    asset_in_dev = asset.to_develop()
    assert asset_in_dev.state == AssetState.InDevelopment
    assert asset_in_dev.id == asset.id


@pytest.mark.parametrize("state", [AssetState.InDevelopment, AssetState.OnMarket, AssetState.Expired, AssetState.Failed])
def test_to_develop_non_idle_asset_raises(state):
    asset = drug_asset_factory(state=state)
    with pytest.raises(ValueError):
        asset.to_develop()


def test_asset_evolve_idle_state():
    asset = drug_asset_factory(state=AssetState.Idle)
    evolved_asset = asset.evolve()
    assert evolved_asset.state == AssetState.Idle
    assert evolved_asset.id == asset.id
    assert evolved_asset.time_on_market == asset.time_on_market
    assert evolved_asset.trial == asset.trial
    assert evolved_asset.revenue_this_step == 0.0
    assert evolved_asset.cost_this_step == 0.0


def test_asset_evolve_in_development_success_final_trial():
    trial = Trial(
        cost_remaining=100.0,
        time_remaining=1,
        ptrs=1.0,  # force success
        phase=TrialPhase.PHASE_3,
        state=TrialState.IN_PROGRESS,
        next_trial_on_success=None,
    )
    trial._rng = random.Random()
    asset = drug_asset_factory(state=AssetState.InDevelopment, trial=trial)
    # Force trial to succeed by setting PTRS to 1.0
    evolved_asset = asset.evolve()
    assert evolved_asset.state == AssetState.OnMarket
    assert evolved_asset.id == asset.id
    assert evolved_asset.time_on_market == 0
    assert evolved_asset.trial.state == TrialState.PHASE_SUCCESS

    # evolve again, we should start accruing revenue
    evolved_asset_2 = evolved_asset.evolve()
    assert evolved_asset_2.state == AssetState.OnMarket
    assert evolved_asset_2.time_on_market == 1
    assert evolved_asset_2.revenue_this_step > 0.0
    assert evolved_asset_2.cost_this_step == 0.0


def test_asset_evolve_in_development_failure():
    trial = Trial(
        cost_remaining=100.0,
        time_remaining=1,
        ptrs=0.0,  # force failure
        phase=TrialPhase.PHASE_1,
        state=TrialState.IN_PROGRESS,
        next_trial_on_success=None,
    )
    trial._rng = random.Random()
    asset = drug_asset_factory(state=AssetState.InDevelopment, trial=trial)
    # Force trial to fail by setting PTRS to 0.0
    evolved_asset = asset.evolve()
    assert evolved_asset.state == AssetState.Failed
    assert evolved_asset.id == asset.id
    assert evolved_asset.time_on_market == asset.time_on_market
    assert evolved_asset.trial.state == TrialState.PHASE_FAILED


def test_asset_evolve_in_development_ongoing():
    next_trial_on_success = Trial(
        cost_remaining=300.0,
        time_remaining=3,
        ptrs=0.5,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        next_trial_on_success=None,
    )
    next_trial_on_success._rng = random.Random(42)
    trial = Trial(
        cost_remaining=200.0,
        time_remaining=2,
        ptrs=1.0, # force success
        phase=TrialPhase.PHASE_2,
        state=TrialState.IN_PROGRESS,
        next_trial_on_success=next_trial_on_success,
    )
    trial._rng = random.Random(42)
    asset = drug_asset_factory(state=AssetState.InDevelopment, trial=trial)

    # first evolve
    evolved_asset = asset.evolve()
    assert evolved_asset.state == AssetState.InDevelopment
    assert evolved_asset.time_on_market == 0
    assert evolved_asset.trial.phase == TrialPhase.PHASE_2
    assert evolved_asset.trial.state == TrialState.IN_PROGRESS
    assert evolved_asset.trial.cost_remaining == 100.0  # 200 - (1 step of 100)
    assert evolved_asset.trial.time_remaining == 1

    # second evolve, should move to idle, next trial pending
    evolved_asset_2 = evolved_asset.evolve()
    assert evolved_asset_2.state == AssetState.Idle
    assert evolved_asset_2.time_on_market == 0
    assert evolved_asset_2.trial.phase == TrialPhase.PHASE_3
    assert evolved_asset_2.trial.state == TrialState.PENDING
    assert evolved_asset_2.trial.cost_remaining == 300.0
    assert evolved_asset_2.trial.time_remaining == 3

    # third evolve, first move asset to develop. Should start phase 3 trial
    # this is because we forced success in phase 2 above with ptrs=1.0
    asset_to_develop = evolved_asset_2.to_develop()
    evolved_asset_3 = asset_to_develop.evolve()
    assert evolved_asset_3.state == AssetState.InDevelopment
    assert evolved_asset_3.time_on_market == 0
    assert evolved_asset_3.trial.phase == TrialPhase.PHASE_3
    assert evolved_asset_3.trial.state == TrialState.IN_PROGRESS
    assert evolved_asset_3.trial.cost_remaining == 200.0  # 300 - (1 step of 100)
    assert evolved_asset_3.trial.time_remaining == 2


def test_asset_evolve_on_market():
    asset = drug_asset_factory(state=AssetState.OnMarket, time_on_market=3, max_revenue=100, time_until_max_revenue=5)
    evolved_asset = asset.evolve()
    assert evolved_asset.state == AssetState.OnMarket
    assert evolved_asset.id == asset.id
    assert evolved_asset.time_on_market == 4
    assert evolved_asset.revenue_this_step > asset.revenue_this_step
    assert evolved_asset.cost_this_step == 0.0

    # evolve again
    evolved_asset_2 = evolved_asset.evolve()
    assert evolved_asset_2.state == AssetState.OnMarket
    assert evolved_asset_2.time_on_market == 5
    assert evolved_asset_2.revenue_this_step > evolved_asset.revenue_this_step
    assert evolved_asset_2.cost_this_step == 0.0

    # evolve again, should be at max revenue now
    evolved_asset_3 = evolved_asset_2.evolve()
    assert evolved_asset_3.state == AssetState.OnMarket
    assert evolved_asset_3.time_on_market == 6
    assert evolved_asset_3.revenue_this_step == 100
    assert evolved_asset_3.cost_this_step == 0.0


def test_asset_evolve_patent_expiry():
    asset = drug_asset_factory(state=AssetState.OnMarket, time_on_market=5, time_until_patent_expiry=1)
    evolved_asset = asset.evolve()
    assert evolved_asset.state == AssetState.Expired
    assert evolved_asset.id == asset.id
    assert evolved_asset.time_on_market == 6
    assert evolved_asset.revenue_this_step == 0.0
    assert evolved_asset.cost_this_step == 0.0


def test_asset_cost_this_step_idle():
    asset = drug_asset_factory(state=AssetState.Idle)
    assert asset.cost_this_step == 0.0


def test_asset_cost_this_step_in_development():
    trial = Trial(
        cost_remaining=150.0,
        time_remaining=3,
        ptrs=0.5,
        phase=TrialPhase.PHASE_2,
        state=TrialState.IN_PROGRESS,
        next_trial_on_success=None,
    )
    trial._rng = random.Random()
    asset = drug_asset_factory(state=AssetState.InDevelopment, trial=trial)
    assert asset.cost_this_step == 50.0  # 150 / 3 steps


def test_asset_cost_this_step_on_market():
    asset = drug_asset_factory(state=AssetState.OnMarket)
    assert asset.cost_this_step == 0.0


def test_asset_cost_to_invest_this_step():
    asset = drug_asset_factory(state=AssetState.Idle)
    assert asset.cost_to_invest_this_step == asset.trial.cost_remaining / asset.trial.time_remaining


@pytest.mark.parametrize(
    "state", [AssetState.InDevelopment, AssetState.Failed, AssetState.Expired]
)
def test_asset_revenue_this_step_idle(state):
    asset = drug_asset_factory(state=state)
    assert asset.revenue_this_step == 0.0


def test_asset_revenue_this_step_on_market():
    time_on_market = 3
    time_until_max_revenue = 5
    max_revenue = 1000.0
    asset = drug_asset_factory(state=AssetState.OnMarket, time_on_market=time_on_market, time_until_max_revenue=time_until_max_revenue, max_revenue=max_revenue)
    assert asset.revenue_this_step == 500.0
