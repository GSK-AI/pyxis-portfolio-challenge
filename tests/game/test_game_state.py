import pickle
import random
import uuid
from unittest.mock import MagicMock

import pytest

from pyxis_portfolio_challenge.config import CapacityConfig
from pyxis_portfolio_challenge.game.asset import AssetState, DrugAsset
from pyxis_portfolio_challenge.game.asset_generators import (
    DUMMY_LIST_DATA,
    FixedListAssetGenerator,
)
from pyxis_portfolio_challenge.game.game_state import GameEndReason, GameState
from pyxis_portfolio_challenge.game.trial import Trial, TrialPhase, TrialState
from tests.game.test_asset import drug_asset_factory
from tests.utils_for_tests import (
    game_states_equivalent,
)


def test_game_state_init_defaults():
    trial = Trial(
        cost_remaining=0.,
        time_remaining=0,
        ptrs=1.0,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PHASE_SUCCESS,
        next_trial_on_success=None
    )
    asset = drug_asset_factory(
        state=AssetState.OnMarket,
        time_until_patent_expiry=10,
        max_revenue=10000,
        trial=trial,
    )
    game_state = GameState(
        id=uuid.uuid4(),
        cash=10000,
        time=0,
        horizon=10,
        equilibrium_num_assets=3,
        max_num_assets=3,
        
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
initial_cash=10000,
        assets={asset.id: asset},
        failed_assets={},
        expired_assets={},
        realised_costs=[],
        realised_revenues=[],
        running_enpv=[],
        running_eroi=[],
        game_ended=False,
        ended_reason=None,
    )._post_init_update_enpv_eroi()
    assert game_state.realised_costs == []
    assert game_state.realised_revenues == []
    assert game_state.assets == {asset.id: asset}
    assert game_state.expired_assets == {}
    assert game_state.running_enpv == [60996.12071341982]
    assert game_state.running_eroi == [0.0]
    assert game_state.game_ended == False
    assert game_state.ended_reason is None
    assert game_state.enpv() == game_state.running_enpv[-1]
    assert game_state.eroi() == game_state.running_eroi[-1]


def test_initialise_new_game_without_seed():
    game_state = GameState.initialise_new_game(
        asset_generator_cls=FixedListAssetGenerator,
        num_assets=3,
        cash=100000,
        horizon=10,
        max_num_assets=10,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        assets_data_list=DUMMY_LIST_DATA,
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
    )
    assert game_state is not None
    assert game_state.cash == 100000
    assert game_state.time == 0
    assert game_state.horizon == 10
    assert len(game_state.assets) == 3
    assert game_state._asset_generator is not None
    assert game_state.realised_costs == []
    assert game_state.realised_revenues == []


def test_initialise_new_game_reproducibility():
    seed0 = 42
    seed1 = 1337

    num_assets = 3
    cash = 100000
    horizon = 10

    game_state_1 = GameState.initialise_new_game(
        asset_generator_cls=FixedListAssetGenerator,
        num_assets=num_assets,
        cash=cash,
        horizon=horizon,
        max_num_assets=10,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        global_seed=seed0,
        assets_data_list=DUMMY_LIST_DATA,
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
    )

    game_state_2 = GameState.initialise_new_game(
        asset_generator_cls=FixedListAssetGenerator,
        num_assets=num_assets,
        cash=cash,
        horizon=horizon,
        max_num_assets=10,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        global_seed=seed0,
        assets_data_list=DUMMY_LIST_DATA,
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
    )

    game_state_3 = GameState.initialise_new_game(
        asset_generator_cls=FixedListAssetGenerator,
        num_assets=num_assets,
        cash=cash,
        horizon=horizon,
        max_num_assets=10,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        global_seed=seed1,
        assets_data_list=DUMMY_LIST_DATA,
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
    )

    assert game_states_equivalent(game_state_1, game_state_2)
    assert not game_states_equivalent(game_state_1, game_state_3)


def test_game_state_assets_expire(game_state_factory_fixed_list_asset_gen):
    trial = Trial(
        cost_remaining=0.,
        time_remaining=0,
        ptrs=1.0,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PHASE_SUCCESS,
        next_trial_on_success=None
    )
    asset = drug_asset_factory(
        state=AssetState.OnMarket,
        time_until_patent_expiry=1,
        max_revenue=10000,
        trial=trial,
    )
    game_state = game_state_factory_fixed_list_asset_gen(
        assets={asset.id: asset},
    )
    game_state = game_state.step(investor_actions={})

    assert asset.id in game_state.expired_assets


@pytest.mark.parametrize(
    "time,horizon,should_raise",
    [
        (0, 10, False),
        (5, 10, False),
        (10, 10, True),
        (11, 10, True),
    ],
)
def test_game_state_init_raises_if_time_ge_horizon_but_game_ended_false(
    game_state_factory_fixed_list_asset_gen, time, horizon, should_raise
):
    if should_raise:
        with pytest.raises(RuntimeError):
            GameState(
                id=uuid.uuid4(),
                cash=100,
                time=time,
                horizon=horizon,
                max_num_assets=3,
                equilibrium_num_assets=3,
                asset_arrival_sensitivity_below=1.5,
                asset_arrival_sensitivity_above=3.0,
                reinvestment_percentage=1.0,
                initial_cash=10000,
                assets={},
                failed_assets={},
                expired_assets={},
                realised_costs=[],
                realised_revenues=[],
                running_enpv=[],
                running_eroi=[],
                game_ended=False,
                ended_reason=None,
            )
    else:
        GameState(
            id=uuid.uuid4(),
            cash=100,
            time=time,
            horizon=horizon,
            equilibrium_num_assets=3,
            max_num_assets=3,
            asset_arrival_sensitivity_below=1.5,
            asset_arrival_sensitivity_above=3.0,
            reinvestment_percentage=1.0,
            initial_cash=10000,
            assets={},
            failed_assets={},
            expired_assets={},
            realised_costs=[],
            realised_revenues=[],
            running_enpv=[],
            running_eroi=[],
            game_ended=False,
            ended_reason=None,
        )


def test_game_state_bankrupt_if_cash_lt_zero_and_game_ended_true():
    game_state = GameState(
        id=uuid.uuid4(),
        cash=-100,
        time=10,
        horizon=10,
        equilibrium_num_assets=3,
        max_num_assets=3,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        initial_cash=10000,
        assets={},
        failed_assets={},
        expired_assets={},
        realised_costs=[],
        realised_revenues=[],
        running_enpv=[],
        running_eroi=[],
        game_ended=True,
        ended_reason="bankrupt",
    )
    assert game_state.cash == -100
    assert game_state.game_ended is True
    assert game_state.bankrupt is True


@pytest.mark.parametrize(
    "cash,should_raise",
    [
        (0, False),
        (100, False),
        (-1, True),
        (-100, True),
    ],
)
def test_game_state_init_raises_if_cash_lt_zero_but_game_ended_false(cash, should_raise):
    if should_raise:
        with pytest.raises(RuntimeError):
            GameState(
                id=uuid.uuid4(),
                cash=cash,
                time=0,
                horizon=10,
                equilibrium_num_assets=3,
                max_num_assets=3,

        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
initial_cash=10000,
                assets={},
                failed_assets={},
                expired_assets={},
                realised_costs=[],
                realised_revenues=[],
                running_enpv=[],
                running_eroi=[],
                game_ended=False,
                ended_reason=None,
            )
    else:
        GameState(
            id=uuid.uuid4(),
            cash=cash,
            time=0,
            horizon=10,
            equilibrium_num_assets=3,
            max_num_assets=3,

        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
initial_cash=10000,
            assets={},
            failed_assets={},
            expired_assets={},
            realised_costs=[],
            realised_revenues=[],
            running_enpv=[],
            running_eroi=[],
            game_ended=False,
            ended_reason=None,
        )


def test_game_state_custom_max_num_assets_constructor():
    # Custom max_num_assets via constructor
    custom_max = 7
    assets = FixedListAssetGenerator(global_seed=123, assets_data_list=DUMMY_LIST_DATA)(
        5, "initial"
    )
    game_state = GameState(
        id=uuid.uuid4(),
        cash=5000,
        time=0,
        horizon=5,
        equilibrium_num_assets=5,
        max_num_assets=custom_max,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        initial_cash=5000,
        assets=assets,
        failed_assets={},
        expired_assets={},
        realised_costs=[],
        realised_revenues=[],
        running_enpv=[],
        running_eroi=[],
        game_ended=False,
        ended_reason=None,
    )
    assert game_state.max_num_assets == custom_max
    # Should not have more than custom_max assets
    assert len(game_state.assets) <= custom_max


def test_game_state_custom_max_num_assets_initialise_new_game():
    # Custom max_num_assets via classmethod
    custom_max = 5
    game_state = GameState.initialise_new_game(
        asset_generator_cls=FixedListAssetGenerator,
        num_assets=3,
        cash=10000,
        horizon=4,
        max_num_assets=custom_max,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        global_seed=42,
        assets_data_list=DUMMY_LIST_DATA,
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
    )
    assert game_state.max_num_assets == custom_max
    # Should not have more than custom_max assets
    assert len(game_state.assets) <= custom_max


def test_pickle_dumps_game_state_includes_all_assets(game_state_factory_json_asset_gen):
    game_state = game_state_factory_json_asset_gen()

    dumped = pickle.dumps(game_state)
    loaded = pickle.loads(dumped)
    assert (
        loaded._asset_generator._all_assets == game_state._asset_generator._all_assets
    )


def test_game_state_enpv_one_idle_asset():
    asset = MagicMock(spec=DrugAsset)
    asset.state = AssetState.Idle
    asset.id = uuid.uuid4()
    asset.enpv = 5000
    asset.time_on_market = 0
    game_state = GameState(
        id=uuid.uuid4(),
        cash=10000,
        time=0,
        horizon=10,
        equilibrium_num_assets=1,
        max_num_assets=1,
        
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
initial_cash=10000,
        assets={asset.id: asset},
        failed_assets={},
        expired_assets={},
        realised_costs=[],
        realised_revenues=[],
        running_enpv=[],
        running_eroi=[],
        game_ended=False,
        ended_reason=None,
    )
    # ENPV should be starting cash since only asset is idle
    assert game_state.enpv() == 10000.0


def test_game_state_eroi_one_idle_asset():
    asset = MagicMock(spec=DrugAsset)
    asset.state = AssetState.Idle
    asset.id = uuid.uuid4()
    asset.enpv = 5000
    asset.time_on_market = 0
    game_state = GameState(
        id=uuid.uuid4(),
        cash=10000,
        time=0,
        horizon=10,
        equilibrium_num_assets=1,
        max_num_assets=1,
        
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
initial_cash=10000,
        assets={asset.id: asset},
        failed_assets={},
        expired_assets={},
        realised_costs=[],
        realised_revenues=[],
        running_enpv=[],
        running_eroi=[],
        game_ended=False,
        ended_reason=None,
    )
    # EROI should be 0 since only asset is idle
    assert game_state.eroi() == 0.0


def test_game_state_enpv_one_on_market_asset():
    asset = MagicMock(spec=DrugAsset)
    asset.state = AssetState.OnMarket
    asset.id = uuid.uuid4()
    asset.enpv = 5000
    asset.trial = MagicMock(state=TrialState.PHASE_SUCCESS)
    game_state = GameState(
        id=uuid.uuid4(),
        cash=10000,
        time=0,
        horizon=10,
        equilibrium_num_assets=1,
        max_num_assets=1,
        
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
initial_cash=10000,
        assets={asset.id: asset},
        failed_assets={},
        expired_assets={},
        realised_costs=[],
        realised_revenues=[],
        running_enpv=[],
        running_eroi=[],
        game_ended=False,
        ended_reason=None,
    )
    # ENPV should include asset revenue
    assert game_state.enpv() == 15000


def test_game_state_eroi_one_in_development_asset():
    trial = Trial(
        cost_remaining=10000.,
        time_remaining=1,
        ptrs=0.5,
        phase=TrialPhase.PHASE_3,
        state=TrialState.IN_PROGRESS,
        next_trial_on_success=None
    )
    asset = drug_asset_factory(
        state=AssetState.InDevelopment,
        time_until_patent_expiry=5,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
    game_state = GameState(
        id=uuid.uuid4(),
        cash=10000,
        time=0,
        horizon=10,
        equilibrium_num_assets=1,
        max_num_assets=1,
        
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
initial_cash=10000,
        assets={asset.id: asset},
        failed_assets={},
        expired_assets={},
        realised_costs=[],
        realised_revenues=[],
        running_enpv=[],
        running_eroi=[],
        game_ended=False,
        ended_reason=None,
    )
    assert game_state.eroi() == 0.75


def test_game_state_running_enpv_eroi_tracking(game_state_factory_fixed_list_asset_gen):
    game_state = game_state_factory_fixed_list_asset_gen()
    expected_enpv = []
    expected_eroi = []
    for step in range(5):
        expected_enpv.append(game_state.enpv())
        expected_eroi.append(game_state.eroi())
        game_state = game_state.step(investor_actions={})
    expected_enpv.append(game_state.enpv())
    expected_eroi.append(game_state.eroi())
    assert game_state.running_enpv == expected_enpv
    assert game_state.running_eroi == expected_eroi


def test_game_state_enpv_over_time_padded_to_horizon(game_state_factory_fixed_list_asset_gen):
    game_state = game_state_factory_fixed_list_asset_gen()
    steps = 3
    for _ in range(steps):
        game_state = game_state.step(investor_actions={})
    enpv_over_time = game_state.enpv_over_time
    assert len(enpv_over_time) == game_state.horizon
    for t in range(steps + 1, game_state.horizon):
        assert enpv_over_time[t] == 0.0
    for t in range(steps + 1):
        assert enpv_over_time[t] == game_state.running_enpv[t]


def test_game_state_eroi_over_time_padded_to_horizon(game_state_factory_fixed_list_asset_gen):
    game_state = game_state_factory_fixed_list_asset_gen()
    steps = 4
    for _ in range(steps):
        game_state = game_state.step(investor_actions={})
    eroi_over_time = game_state.eroi_over_time
    assert len(eroi_over_time) == game_state.horizon
    for t in range(steps + 1, game_state.horizon):
        assert eroi_over_time[t] == 0.0
    for t in range(steps + 1):
        assert eroi_over_time[t] == game_state.running_eroi[t]


def test_game_state_in_development_assets_returns_assets_in_development(
    game_state_factory_fixed_list_asset_gen,
):
    trial = Trial(
        cost_remaining=10000.,
        time_remaining=1,
        ptrs=0.5,
        phase=TrialPhase.PHASE_3,
        state=TrialState.IN_PROGRESS,
        next_trial_on_success=None
    )
    asset_in_dev = drug_asset_factory(
        state=AssetState.InDevelopment,
        time_until_patent_expiry=5,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
    asset_on_market = drug_asset_factory(
        state=AssetState.OnMarket,
        time_until_patent_expiry=5,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
    game_state = game_state_factory_fixed_list_asset_gen(
        assets={
            asset_in_dev.id: asset_in_dev,
            asset_on_market.id: asset_on_market,
        }
    )
    in_dev_assets = game_state.in_development_assets()
    assert len(in_dev_assets) == 1
    assert asset_in_dev.id in in_dev_assets


def test_game_state_step_game_ends_ongoing_investments(
    game_state_factory_fixed_list_asset_gen,
):
    trial = Trial(
        cost_remaining=10000.,
        time_remaining=1,
        ptrs=0.5,
        phase=TrialPhase.PHASE_3,
        state=TrialState.IN_PROGRESS,
        next_trial_on_success=None
    )
    trial._rng = random.Random()
    asset_in_dev = drug_asset_factory(
        state=AssetState.InDevelopment,
        time_until_patent_expiry=10,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
    asset_in_dev._rng = random.Random()
    game_state = game_state_factory_fixed_list_asset_gen(
        time=9,  # One step before horizo, however should end due to ongoing investments
        horizon=10,
        assets={asset_in_dev.id: asset_in_dev},
        cash=5000,
    )
    game_state_stepped = game_state.step(investor_actions={})

    # should have changed
    assert game_state_stepped.game_ended is True
    assert game_state_stepped.ended_reason == GameEndReason.ONGOING_INVESTMENTS
    assert game_state_stepped.cash < 0.
    assert game_state_stepped.bankrupt is True

    # shouldn't have changed
    assert game_state_stepped.time == game_state.time  # check time did not advance
    assert game_state_stepped.horizon == game_state.horizon
    assert game_state_stepped.equilibrium_num_assets == game_state.equilibrium_num_assets
    assert game_state_stepped.initial_cash == game_state.initial_cash
    assert game_state_stepped.assets == game_state.assets
    assert game_state_stepped.expired_assets == game_state.expired_assets
    assert game_state_stepped.realised_revenues == game_state.realised_revenues
    assert game_state_stepped.realised_costs == game_state.realised_costs
    assert game_state_stepped.running_enpv == game_state_stepped.running_enpv # check that no extra entries are added as we didn't advance time
    assert game_state_stepped.running_eroi == game_state_stepped.running_eroi


def test_game_state_step_game_ends_new_investments(
    game_state_factory_fixed_list_asset_gen,
):
    trial = Trial(
        cost_remaining=10000.,
        time_remaining=1,
        ptrs=0.5,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        next_trial_on_success=None
    )
    trial._rng = random.Random()
    asset_idle = drug_asset_factory(
        state=AssetState.Idle,
        time_until_patent_expiry=10,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
    asset_idle._rng = random.Random()
    game_state = game_state_factory_fixed_list_asset_gen(
        time=9,  # One step before horizo, however should end due to new investments
        horizon=10,
        assets={asset_idle.id: asset_idle},
        cash=5000,
    )
    game_state_stepped = game_state.step(
        investor_actions={asset_idle.id: "invest"}
    )

    # should have changed
    assert game_state_stepped.game_ended is True
    assert game_state_stepped.ended_reason == GameEndReason.NEW_INVESTMENTS
    assert game_state_stepped.cash < 0.
    assert game_state_stepped.bankrupt is True

    # shouldn't have changed
    assert game_state_stepped.time == game_state.time  # check time did not advance
    assert game_state_stepped.horizon == game_state.horizon
    assert game_state_stepped.equilibrium_num_assets == game_state.equilibrium_num_assets
    assert game_state_stepped.initial_cash == game_state.initial_cash
    assert game_state_stepped.assets.keys() == game_state.assets.keys()
    assert game_state_stepped.expired_assets == game_state.expired_assets
    assert game_state_stepped.realised_revenues == game_state.realised_revenues
    assert game_state_stepped.realised_costs == game_state.realised_costs
    assert game_state_stepped.running_enpv == game_state_stepped.running_enpv # check that no extra entries are added as we didn't advance time
    assert game_state_stepped.running_eroi == game_state_stepped.running_eroi


def test_game_state_step_game_ends_horizon_reached(
    game_state_factory_fixed_list_asset_gen,
):
    trial = Trial(
        cost_remaining=10000.,
        time_remaining=1,
        ptrs=0.5,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        next_trial_on_success=None
    )
    trial._rng = random.Random()
    asset_idle = drug_asset_factory(
        state=AssetState.Idle,
        time_until_patent_expiry=10,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
    asset_idle._rng = random.Random()
    game_state = game_state_factory_fixed_list_asset_gen(
        time=0,  # One step before horizon
        horizon=1,
        cash=5000,
        assets={asset_idle.id: asset_idle},
    )
    game_state_stepped = game_state.step(investor_actions={})  # No new investments

    # should have changed
    assert game_state_stepped.time == game_state.horizon  # time should have advanced to horizon
    assert game_state_stepped.game_ended is True
    assert game_state_stepped.ended_reason == GameEndReason.HORIZON_REACHED
    assert game_state_stepped.cash == game_state.cash  # should not be bankrupt
    assert game_state_stepped.bankrupt is False

    # shouldn't have changed
    assert game_state_stepped.horizon == game_state.horizon
    assert game_state_stepped.equilibrium_num_assets == game_state.equilibrium_num_assets
    assert game_state_stepped.initial_cash == game_state.initial_cash
    assert game_state_stepped.assets.keys() == game_state.assets.keys()
    assert game_state_stepped.expired_assets == game_state.expired_assets
    assert game_state_stepped.realised_revenues == [0.0]
    assert game_state_stepped.realised_costs == [0.0]
    assert game_state_stepped.running_enpv == [5000.0, 5000.0]  # one extra entry as time advanced
    assert game_state_stepped.running_eroi == [0.0, 0.0]  # one extra entry as time advanced


def test_game_state_step_no_game_end(
    game_state_factory_fixed_list_asset_gen,
):
    trial = Trial(
        cost_remaining=10000.,
        time_remaining=1,
        ptrs=0.5,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        next_trial_on_success=None
    )
    trial._rng = random.Random(1)  # seed=1 gives first draw < 0.5 → trial succeeds
    asset_idle = drug_asset_factory(
        state=AssetState.Idle,
        time_until_patent_expiry=10,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
    asset_idle._rng = random.Random(1)
    game_state = game_state_factory_fixed_list_asset_gen(
        time=0,
        horizon=5,
        cash=15000,
        assets={asset_idle.id: asset_idle},
    )
    game_state_stepped = game_state.step(
        investor_actions={asset_idle.id: "invest"}
    )  # New investment, but should not end game

    # should have changed
    assert game_state_stepped.time == game_state.time + 1  # time should have advanced
    assert game_state_stepped.game_ended is False
    assert game_state_stepped.ended_reason is None
    assert game_state_stepped.cash == game_state.cash - 10000.  # cash should reduce
    assert game_state_stepped.bankrupt is False

    # shouldn't have changed
    assert game_state_stepped.horizon == game_state.horizon
    assert game_state_stepped.equilibrium_num_assets == game_state.equilibrium_num_assets
    assert game_state_stepped.initial_cash == game_state.initial_cash
    assert game_state_stepped.assets.keys() == game_state.assets.keys()
    assert game_state_stepped.expired_assets == game_state.expired_assets
    assert game_state_stepped.realised_revenues == [0.0]
    assert game_state_stepped.realised_costs == [10000.0]
    assert game_state_stepped.running_enpv == [15000.0, game_state_stepped.enpv()]  # one extra entry as time advanced
    assert game_state_stepped.running_eroi == [0.0, game_state_stepped.eroi()]  # one extra entry as time advanced


def test_game_state_step_asset_expires_during_step(
    game_state_factory_fixed_list_asset_gen,
):
    trial = Trial(
        cost_remaining=0.,
        time_remaining=1,
        ptrs=1.0,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PHASE_SUCCESS,
        next_trial_on_success=None
    )
    trial._rng = random.Random()
    asset_on_market = drug_asset_factory(
        state=AssetState.OnMarket,
        time_until_patent_expiry=1,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
    asset_on_market._rng = random.Random()
    game_state = game_state_factory_fixed_list_asset_gen(
        time=0,
        horizon=5,
        cash=5000,
        assets={asset_on_market.id: asset_on_market},
    )
    game_state_stepped = game_state.step(
        investor_actions={}
    )  # No new investment

    # Asset should have expired
    assert asset_on_market.id not in game_state_stepped.assets
    assert asset_on_market.id in game_state_stepped.expired_assets


def test_game_step_new_asset_arrives(
    game_state_factory_fixed_list_asset_gen,
):
    drug_asset = drug_asset_factory()
    game_state = game_state_factory_fixed_list_asset_gen(
        time=0,
        horizon=5,
        cash=5000,
        assets={},
        equilibrium_num_assets=1,
        max_num_assets=2,
    )

    # Mock the instance's _asset_generator directly
    mock_asset_gen = MagicMock()
    mock_asset_gen.return_value = {drug_asset.id: drug_asset}
    game_state._asset_generator = mock_asset_gen

    # Mock RNG to trigger asset arrival once, then fail
    mock_rng = MagicMock(spec=random.Random)
    mock_rng.random.side_effect = [0.0, 0.99]  # First succeeds, second fails
    game_state._rng = mock_rng

    game_state_stepped = game_state.step(
        investor_actions={}
    )  # No new investment

    # New asset should have arrived
    mock_asset_gen.assert_called_once_with(
        1, "new",
        ta_experience=game_state.ta_experience,
        episode_progress=game_state.time / game_state.horizon,
    )

    assert drug_asset.id in game_state_stepped.assets


def test_game_state_invest_in_idle_asset_reduces_cash(
    game_state_factory_fixed_list_asset_gen,
):
    trial = Trial(
        cost_remaining=10000.,
        time_remaining=1,
        ptrs=0.5,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        next_trial_on_success=None
    )
    trial._rng = random.Random()
    asset_idle = drug_asset_factory(
        state=AssetState.Idle,
        time_until_patent_expiry=10,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
    asset_idle._rng = random.Random()
    initial_cash = 20000
    game_state = game_state_factory_fixed_list_asset_gen(
        time=0,
        horizon=5,
        cash=initial_cash,
        assets={asset_idle.id: asset_idle},
    )
    game_state_stepped = game_state.step(
        investor_actions={asset_idle.id: "invest"}
    )  # New investment

    # Cash should reduce by investment cost
    assert game_state_stepped.cash == initial_cash - 10000.
