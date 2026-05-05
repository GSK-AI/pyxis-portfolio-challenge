import copy
import random

import pytest

from aiml_pyxis_investment_game.agents.knapsack import (
    KnapsackAgent,
    delta_npv,
)
from aiml_pyxis_investment_game.game.asset import AssetState
from aiml_pyxis_investment_game.game.constants import DISCOUNT_RATE
from aiml_pyxis_investment_game.game.trial import Trial, TrialPhase, TrialState
from tests.game.test_asset import drug_asset_factory


def test_delta_npv_positive():
    trial = Trial(
        phase=TrialPhase.PHASE_3,
        state=TrialState.PHASE_SUCCESS,
        cost_remaining=0.0,
        time_remaining=0,
        ptrs=1.0,
        next_trial_on_success=None
    )

    asset = drug_asset_factory(state=AssetState.OnMarket, trial=trial)
    asset_before_call = copy.deepcopy(asset)
    value = delta_npv(asset)
    assert asset == asset_before_call
    assert isinstance(value, float)
    assert value > 0
    delayed_asset = asset.evolve()
    assert value == asset.enpv - DISCOUNT_RATE * delayed_asset.enpv


def test_delta_npv_non_positive():
    asset = drug_asset_factory(
        state=AssetState.Idle, time_until_patent_expiry=3
    )
    asset._rng = random.Random(42)
    assert asset.enpv < 0
    value = delta_npv(asset)
    assert value == 0.0


def test_create_knapsack_agent():
    agent = KnapsackAgent()
    assert agent is not None
    assert isinstance(agent, KnapsackAgent)
    assert agent.units == 1e6
    assert agent.value_function == delta_npv
    assert agent.include_ongoing_costs is True


@pytest.mark.parametrize(
    "capacity,expected", [(5, set(["a", "d"])), (1, set(["a"])), (3, set(["a", "b"]))]
)
def test_knapsack_01_solver(capacity, expected):
    agent = KnapsackAgent(units=1)
    items = [
        (300, 1, "a"),
        (200, 2, "b"),
        (300, 3, "c"),
        (400, 4, "d"),
    ]
    knapsack_result = agent.knapsack_01_solver(items, capacity)
    knapsack_set = set(item[2] for item in knapsack_result)
    assert knapsack_set == expected


def test_knapsack_no_idle_assets(
    game_state_factory_fixed_list_asset_gen
):
    asset1 = drug_asset_factory(
        state=AssetState.OnMarket,
        trial=Trial(
            phase=TrialPhase.PHASE_3,
            state=TrialState.PHASE_SUCCESS,
            cost_remaining=0.0,
            time_remaining=0,
            ptrs=1.0,
            next_trial_on_success=None
        )
    )
    asset2 = drug_asset_factory(state=AssetState.InDevelopment, trial=Trial(
        phase=TrialPhase.PHASE_3,
        state=TrialState.IN_PROGRESS,
        cost_remaining=50.0,
        time_remaining=5,
        ptrs=0.5,
        next_trial_on_success=None
    ))
    asset3 = drug_asset_factory(state=AssetState.Idle, trial=Trial(
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        cost_remaining=30.0,
        time_remaining=3,
        ptrs=0.6,
        next_trial_on_success=None
    ))

    cash = 100

    game_state_no_idle = game_state_factory_fixed_list_asset_gen(
        cash=cash, assets={asset1.id: asset1, asset2.id: asset2}
    )
    game_state_idle = game_state_factory_fixed_list_asset_gen(
        cash=cash, assets={asset1.id: asset1, asset2.id: asset2, asset3.id: asset3}
    )

    agent = KnapsackAgent(units=10)
    investment_decisions_no_idle = agent.make_investment_decisions(game_state_no_idle)
    investment_decisions_idle = agent.make_investment_decisions(game_state_idle)


    assert investment_decisions_no_idle == {}  # should make no investments as none in Idle state
    assert investment_decisions_idle == {asset3.id: "invest"}  # should invest in the only Idle asset, has enough cash



def test_knapsack_zero_budget(
    game_state_factory_fixed_list_asset_gen
):
    asset1 = drug_asset_factory(
        state=AssetState.OnMarket,
        trial=Trial(
            phase=TrialPhase.PHASE_3,
            state=TrialState.PHASE_SUCCESS,
            cost_remaining=0.0,
            time_remaining=0,
            ptrs=1.0,
            next_trial_on_success=None
        )
    )
    asset2 = drug_asset_factory(state=AssetState.InDevelopment, trial=Trial(
        phase=TrialPhase.PHASE_3,
        state=TrialState.IN_PROGRESS,
        cost_remaining=50.0,
        time_remaining=5,
        ptrs=0.5,
        next_trial_on_success=None
    ))
    asset3 = drug_asset_factory(state=AssetState.Idle, trial=Trial(
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        cost_remaining=30.0,
        time_remaining=3,
        ptrs=0.6,
        next_trial_on_success=None
    ))
    assets = {asset1.id: asset1, asset2.id: asset2, asset3.id: asset3}

    game_state = game_state_factory_fixed_list_asset_gen(
        assets=assets, cash=0
    )

    agent = KnapsackAgent(units=10)
    assert agent.make_investment_decisions(game_state) == {}  # should make no investments as no budget


def test_knapsack_sufficient_budget(
    game_state_factory_fixed_list_asset_gen
):
    asset1 = drug_asset_factory(
        state=AssetState.OnMarket,
        trial=Trial(
            phase=TrialPhase.PHASE_3,
            state=TrialState.PHASE_SUCCESS,
            cost_remaining=0.0,
            time_remaining=0,
            ptrs=1.0,
            next_trial_on_success=None
        )
    )
    asset2 = drug_asset_factory(state=AssetState.Idle,
                                trial=Trial(
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        cost_remaining=50.0,
        time_remaining=5,
        ptrs=0.5,
        next_trial_on_success=None
    ))
    asset3 = drug_asset_factory(state=AssetState.Idle,
                                trial=Trial(
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        cost_remaining=30.0,
        time_remaining=3,
        ptrs=0.6,
        next_trial_on_success=None
    ))

    assets = {asset1.id: asset1, asset2.id: asset2, asset3.id: asset3}

    # Should have enough cash to invest in all idle assets
    game_state = game_state_factory_fixed_list_asset_gen(
        assets=assets, cash=1000
    )

    agent = KnapsackAgent(units=10)
    investment_decisions = agent.make_investment_decisions(game_state)

    assert investment_decisions == {asset3.id: "invest", asset2.id: "invest"}  # should invest in the both Idle assets


def test_knapsack_include_ongoing_costs(
    game_state_factory_fixed_list_asset_gen
):
    asset1 = drug_asset_factory(
        state=AssetState.OnMarket,
        trial=Trial(
            phase=TrialPhase.PHASE_3,
            state=TrialState.PHASE_SUCCESS,
            cost_remaining=0.0,
            time_remaining=0,
            ptrs=1.0,
            next_trial_on_success=None
        )
    )
    asset2 = drug_asset_factory(state=AssetState.InDevelopment,
                                trial=Trial(
        phase=TrialPhase.PHASE_3,
        state=TrialState.IN_PROGRESS,
        cost_remaining=20.0,
        time_remaining=1,
        ptrs=0.5,
        next_trial_on_success=None
    ))
    asset3 = drug_asset_factory(
        state=AssetState.Idle,
        trial=Trial(
            phase=TrialPhase.PHASE_3,
            state=TrialState.PENDING,
            cost_remaining=30.0,
            time_remaining=1,
            ptrs=0.6,
            next_trial_on_success=None
        )
    )

    assets = {asset1.id: asset1, asset2.id: asset2, asset3.id: asset3}

    # Should have just enough cash to invest in asset 3 before paying for asset 2
    game_state = game_state_factory_fixed_list_asset_gen(
        assets=assets, cash=30.
    )

    agent_not_include_costs = KnapsackAgent(units=10, include_ongoing_costs=False)
    agent_include_costs = KnapsackAgent(units=10, include_ongoing_costs=True)

    decisions_not_include_costs = agent_not_include_costs.make_investment_decisions(
        game_state
    )
    decisions_include_costs = agent_include_costs.make_investment_decisions(game_state)

    assert decisions_not_include_costs == {asset3.id: "invest"}
    assert decisions_include_costs == {}  # should not invest as ongoing costs make budget insufficient
