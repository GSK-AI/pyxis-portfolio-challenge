import pickle
import random
import uuid
from unittest.mock import MagicMock, patch

import pytest

from pyxis_portfolio_challenge.config import (
    ApprovalPhaseConfig,
    CapacityConfig,
    ClinicalSitesConfig,
    DistributionalPtrsConfig,
    DropActionConfig,
    InterimTrialObservationsConfig,
    InvestmentLevelParams,
    InvestmentLevelsConfig,
    MarketingConfig,
    PtrsReadingsConfig,
    TAExperienceConfig,
    UncertainPtrsConfig,
)
from pyxis_portfolio_challenge.game.asset import AssetState, DrugAsset
from pyxis_portfolio_challenge.game.asset_generators import (
    DUMMY_LIST_DATA,
    FixedListAssetGenerator,
)
from pyxis_portfolio_challenge.game.constants import InvestmentLevel
from pyxis_portfolio_challenge.game.game_state import GameEndReason, GameState
from pyxis_portfolio_challenge.game.trial import Trial, TrialPhase, TrialState
from pyxis_portfolio_challenge.rng import init_game_rng
from tests.game.test_asset import drug_asset_factory
from tests.utils_for_tests import (
    game_states_equivalent,
)

# Disabled feature configs now required as keyword-only args by
# GameState.initialise_new_game (rd_capacity passed explicitly at each call site).
_EXTRA_DISABLED_CONFIGS = dict(
    investment_levels_config=InvestmentLevelsConfig(
        enabled=False,
        levels={
            "none": InvestmentLevelParams(
                cost_modifier=0.0, speed_modifier=0.0, success_modifier=1.0,
                capacity_cost=0, experience_modifier=0.0,
            ),
            "standard": InvestmentLevelParams(
                cost_modifier=1.0, speed_modifier=1.0, success_modifier=1.0,
                capacity_cost=2, experience_modifier=1.0,
            ),
        },
    ),
    interim_trial_observations_config=InterimTrialObservationsConfig(
        enabled=False, latent_quality_concentration=10.0, initial_noise_scale=0.3,
    ),
    distributional_ptrs_config=DistributionalPtrsConfig(
        enabled=False,
        ta_quality_variance={
            "oncology": 0.08,
            "respiratory and immunology": 0.05,
            "vaccines and infectious disease": 0.03,
        },
        asset_noise_std=0.03, prior_concentration=5.0, observation_noise=0.1,
    ),
    drop_action_config=DropActionConfig(
        enabled=False, drop_price_fraction=0.0, drop_price_rounding=1_000_000,
    ),
    marketing_config=MarketingConfig(
        enabled=False, dc_cost_fraction=0.035, dc_step_boost=0.10, dc_decay_rate=0.206,
        be_cost_fraction=0.0175, be_boost=0.25, be_decay_rate=0.206, be_effectiveness=3.5,
    ),
    clinical_sites_config=ClinicalSitesConfig(
        enabled=False, starting_sites=4, purchase_base_cost=500_000_000,
        purchase_cost_rounding=1_000_000, site_development_steps=2, agent_priority=False,
        priority_entropy_weight=1.0, auction_enabled=True, auction_interval_steps=20,
        auction_min_step=10, site_max_bid=100_000,
    ),
    ptrs_readings_config=PtrsReadingsConfig(
        enabled=False, cost_fraction=0.05, cost_rounding=1_000_000,
        action_space_max_readings=10, sigma_logit_base=1.5, sigma_ep=None,
        noise_multipliers=[1.0, 1.5, 2.0], max_sample_obs=20,
    ),
    ta_experience_config=TAExperienceConfig(
        enabled=False, experience_to_full_knowledge=30.0, max_expertise_boost=0.05,
        experience_to_max_boost=40.0, experience_decay_rate=0.98,
        max_total_experience=60.0,
        phase_experience_weights={
            "phase_1": 0.5, "phase_2": 1.0, "phase_3": 1.5, "approval": 0.5,
        },
        asset_arrival_temperature=0.1,
    ),
    uncertain_ptrs_config=UncertainPtrsConfig(
        enabled=False,
        ta_noise_config={
            "oncology": 0.12,
            "respiratory and immunology": 0.10,
            "vaccines and infectious disease": 0.08,
        },
        phase_noise_multipliers={
            "phase_1": 1.5, "phase_2": 1.0, "phase_3": 0.75, "approval": 0.5,
        },
    ),
    approval_phase_config=ApprovalPhaseConfig(
        enabled=False, duration_min=1, duration_max=3,
        success_rate_min=0.85, success_rate_max=0.95, cost=50_000_000,
    ),
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
        dropped_assets={},
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
    init_game_rng(0)
    game_state = GameState.initialise_new_game(
        asset_generator_cls=FixedListAssetGenerator,
        num_assets=3,
        cash=100000,
        horizon=10,
        max_num_assets=10,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        seed=None,
        assets_data_list=DUMMY_LIST_DATA,
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
        **_EXTRA_DISABLED_CONFIGS,
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

    init_game_rng(seed0)
    game_state_1 = GameState.initialise_new_game(
        asset_generator_cls=FixedListAssetGenerator,
        num_assets=num_assets,
        cash=cash,
        horizon=horizon,
        max_num_assets=10,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        seed=seed0,
        assets_data_list=DUMMY_LIST_DATA,
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
        **_EXTRA_DISABLED_CONFIGS,
    )

    init_game_rng(seed0)
    game_state_2 = GameState.initialise_new_game(
        asset_generator_cls=FixedListAssetGenerator,
        num_assets=num_assets,
        cash=cash,
        horizon=horizon,
        max_num_assets=10,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        seed=seed0,
        assets_data_list=DUMMY_LIST_DATA,
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
        **_EXTRA_DISABLED_CONFIGS,
    )

    init_game_rng(seed1)
    game_state_3 = GameState.initialise_new_game(
        asset_generator_cls=FixedListAssetGenerator,
        num_assets=num_assets,
        cash=cash,
        horizon=horizon,
        max_num_assets=10,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        seed=seed1,
        assets_data_list=DUMMY_LIST_DATA,
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
        **_EXTRA_DISABLED_CONFIGS,
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
                dropped_assets={},
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
            dropped_assets={},
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
        dropped_assets={},
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
                dropped_assets={},
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
            dropped_assets={},
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
    assets = FixedListAssetGenerator(assets_data_list=DUMMY_LIST_DATA)(
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
        dropped_assets={},
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
    init_game_rng(42)
    game_state = GameState.initialise_new_game(
        asset_generator_cls=FixedListAssetGenerator,
        num_assets=3,
        cash=10000,
        horizon=4,
        max_num_assets=custom_max,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        seed=42,
        assets_data_list=DUMMY_LIST_DATA,
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
        **_EXTRA_DISABLED_CONFIGS,
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
        dropped_assets={},
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
        dropped_assets={},
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
        dropped_assets={},
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
        dropped_assets={},
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
    asset_in_dev = drug_asset_factory(
        state=AssetState.InDevelopment,
        time_until_patent_expiry=10,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
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
    asset_idle = drug_asset_factory(
        state=AssetState.Idle,
        time_until_patent_expiry=10,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
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
    asset_idle = drug_asset_factory(
        state=AssetState.Idle,
        time_until_patent_expiry=10,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
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
        ptrs=1.0,  # force success so asset goes on-market deterministically
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        next_trial_on_success=None
    )
    asset_idle = drug_asset_factory(
        state=AssetState.Idle,
        time_until_patent_expiry=10,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
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
    asset_on_market = drug_asset_factory(
        state=AssetState.OnMarket,
        time_until_patent_expiry=1,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
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
    with patch("pyxis_portfolio_challenge.game.game_state.get_game_rng", return_value=mock_rng):
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
    asset_idle = drug_asset_factory(
        state=AssetState.Idle,
        time_until_patent_expiry=10,
        max_revenue=10000,
        time_until_max_revenue=1,
        trial=trial,
    )
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


# --- DROP action tests ---

def test_step_drop_idle_asset(game_state_factory_fixed_list_asset_gen):
    """Dropping an Idle asset moves it to dropped_assets; no cost paid."""
    trial = Trial(
        cost_remaining=10000.0,
        time_remaining=2,
        ptrs=0.5,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        next_trial_on_success=None,
    )
    asset = drug_asset_factory(
        state=AssetState.Idle,
        time_until_patent_expiry=10,
        max_revenue=10000,
        trial=trial,
    )
    initial_cash = 100_000.0
    game_state = game_state_factory_fixed_list_asset_gen(
        cash=initial_cash,
        assets={asset.id: asset},
    )
    next_state = game_state.step(investor_actions={asset.id: InvestmentLevel.DROP})

    assert asset.id not in next_state.assets
    assert asset.id in next_state.dropped_assets
    assert next_state.dropped_assets[asset.id].state == AssetState.Dropped
    assert next_state.cash == initial_cash  # no cost deducted


def test_step_drop_in_development_asset(game_state_factory_fixed_list_asset_gen):
    """Dropping an InDevelopment asset moves it to dropped_assets; ongoing cost is waived."""
    trial = Trial(
        cost_remaining=50_000.0,
        time_remaining=3,
        ptrs=0.5,
        phase=TrialPhase.PHASE_3,
        state=TrialState.IN_PROGRESS,
        next_trial_on_success=None,
    )
    asset = drug_asset_factory(
        state=AssetState.InDevelopment,
        time_until_patent_expiry=10,
        max_revenue=10000,
        trial=trial,
    )
    initial_cash = 100_000.0
    game_state = game_state_factory_fixed_list_asset_gen(
        cash=initial_cash,
        assets={asset.id: asset},
    )
    next_state = game_state.step(investor_actions={asset.id: InvestmentLevel.DROP})

    assert asset.id not in next_state.assets
    assert asset.id in next_state.dropped_assets
    assert next_state.dropped_assets[asset.id].state == AssetState.Dropped
    # Cash is unchanged: no ongoing cost paid for a dropped in-development asset
    assert next_state.cash == initial_cash


def test_step_drop_on_market_asset(game_state_factory_fixed_list_asset_gen):
    """Dropping an OnMarket asset removes it from the portfolio; no revenue collected that step."""
    trial = Trial(
        cost_remaining=0.0,
        time_remaining=0,
        ptrs=1.0,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PHASE_SUCCESS,
        next_trial_on_success=None,
    )
    asset = drug_asset_factory(
        state=AssetState.OnMarket,
        time_until_patent_expiry=10,
        max_revenue=1_000_000,
        time_until_max_revenue=5,
        time_on_market=3,
        trial=trial,
    )
    initial_cash = 100_000.0
    game_state = game_state_factory_fixed_list_asset_gen(
        cash=initial_cash,
        assets={asset.id: asset},
    )
    next_state = game_state.step(investor_actions={asset.id: InvestmentLevel.DROP})

    assert asset.id not in next_state.assets
    assert asset.id in next_state.dropped_assets
    assert next_state.dropped_assets[asset.id].state == AssetState.Dropped


def test_step_drop_accumulates_across_steps(game_state_factory_fixed_list_asset_gen):
    """dropped_assets accumulates across multiple steps."""
    trial = Trial(
        cost_remaining=10000.0,
        time_remaining=2,
        ptrs=0.5,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        next_trial_on_success=None,
    )
    asset_a = drug_asset_factory(state=AssetState.Idle, time_until_patent_expiry=10, max_revenue=10000, trial=trial)
    asset_b = drug_asset_factory(state=AssetState.Idle, time_until_patent_expiry=10, max_revenue=10000, trial=trial)
    game_state = game_state_factory_fixed_list_asset_gen(
        cash=1_000_000.0,
        assets={asset_a.id: asset_a, asset_b.id: asset_b},
    )

    state1 = game_state.step(investor_actions={asset_a.id: InvestmentLevel.DROP})
    assert asset_a.id in state1.dropped_assets
    assert asset_b.id in state1.assets

    state2 = state1.step(investor_actions={asset_b.id: InvestmentLevel.DROP})
    assert asset_a.id in state2.dropped_assets
    assert asset_b.id in state2.dropped_assets
    assert len(state2.assets) == 0 or all(
        a.id not in (asset_a.id, asset_b.id) for a in state2.assets.values()
    )


# --- DROP fee tests ---

def _idle_asset_with_cost(cost_remaining: float) -> DrugAsset:
    """Idle asset whose current trial phase has the given cost_remaining."""
    trial = Trial(
        cost_remaining=cost_remaining,
        time_remaining=2,
        ptrs=0.5,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        next_trial_on_success=None,
    )
    return drug_asset_factory(
        state=AssetState.Idle,
        time_until_patent_expiry=10,
        max_revenue=10000,
        trial=trial,
    )


def _drop_with_config(
    game_state_factory, drop_action_config, cost_remaining=10_000_000.0,
    initial_cash=100_000_000.0,
):
    """Drop a single Idle asset under the given drop config; return (state, asset)."""
    asset = _idle_asset_with_cost(cost_remaining)
    game_state = game_state_factory(cash=initial_cash, assets={asset.id: asset})
    game_state._drop_action_config = drop_action_config
    return game_state.step(investor_actions={asset.id: InvestmentLevel.DROP}), asset


def test_drop_fee_charged_as_fraction_of_cost_remaining(
    game_state_factory_fixed_list_asset_gen,
):
    """Fee is drop_price_fraction x cost_remaining, rounded to drop_price_rounding."""
    cfg = DropActionConfig(
        enabled=True, drop_price_fraction=0.25, drop_price_rounding=1_000_000
    )
    initial_cash = 100_000_000.0
    next_state, asset = _drop_with_config(
        game_state_factory_fixed_list_asset_gen,
        cfg,
        cost_remaining=12_000_000.0,
        initial_cash=initial_cash,
    )

    # 0.25 * 12M = 3M, already an exact multiple of the £1M rounding
    assert next_state.cash == pytest.approx(initial_cash - 3_000_000.0)
    assert asset.id in next_state.dropped_assets


def test_drop_fee_rounds_half_to_even(game_state_factory_fixed_list_asset_gen):
    """Fees landing exactly on a .5 rounding boundary round half-to-even.

    This is Python's built-in round() semantics rather than a deliberate design
    choice, so it is pinned here: 0.25 x 10M = 2.5 rounding units -> 2, not 3.
    """
    cfg = DropActionConfig(
        enabled=True, drop_price_fraction=0.25, drop_price_rounding=1_000_000
    )
    initial_cash = 100_000_000.0
    next_state, _ = _drop_with_config(
        game_state_factory_fixed_list_asset_gen,
        cfg,
        cost_remaining=10_000_000.0,
        initial_cash=initial_cash,
    )

    assert next_state.cash == pytest.approx(initial_cash - 2_000_000.0)


def test_drop_fee_rounded_to_nearest_rounding_unit(
    game_state_factory_fixed_list_asset_gen,
):
    """A fee that is not a multiple of the rounding unit is rounded to nearest."""
    cfg = DropActionConfig(
        enabled=True, drop_price_fraction=0.25, drop_price_rounding=1_000_000
    )
    initial_cash = 100_000_000.0
    next_state, _ = _drop_with_config(
        game_state_factory_fixed_list_asset_gen,
        cfg,
        cost_remaining=9_400_000.0,
        initial_cash=initial_cash,
    )

    # 0.25 * 9.4M = 2.35M -> rounds to 2M
    assert next_state.cash == pytest.approx(initial_cash - 2_000_000.0)


def test_drop_fee_rounding_of_one_disables_rounding(
    game_state_factory_fixed_list_asset_gen,
):
    """drop_price_rounding=1 charges the raw unrounded fee."""
    cfg = DropActionConfig(
        enabled=True, drop_price_fraction=0.25, drop_price_rounding=1
    )
    initial_cash = 100_000_000.0
    next_state, _ = _drop_with_config(
        game_state_factory_fixed_list_asset_gen,
        cfg,
        cost_remaining=9_400_000.0,
        initial_cash=initial_cash,
    )

    assert next_state.cash == pytest.approx(initial_cash - 2_350_000.0)


def test_drop_fee_zero_fraction_charges_nothing(
    game_state_factory_fixed_list_asset_gen,
):
    """drop_price_fraction=0 drops the asset for free."""
    cfg = DropActionConfig(
        enabled=True, drop_price_fraction=0.0, drop_price_rounding=1_000_000
    )
    initial_cash = 100_000_000.0
    next_state, asset = _drop_with_config(
        game_state_factory_fixed_list_asset_gen, cfg, initial_cash=initial_cash
    )

    assert next_state.cash == pytest.approx(initial_cash)
    assert asset.id in next_state.dropped_assets


def test_drop_fee_not_charged_without_config(
    game_state_factory_fixed_list_asset_gen,
):
    """With no drop_action_config attached, dropping is free."""
    initial_cash = 100_000_000.0
    next_state, asset = _drop_with_config(
        game_state_factory_fixed_list_asset_gen, None, initial_cash=initial_cash
    )

    assert next_state.cash == pytest.approx(initial_cash)
    assert asset.id in next_state.dropped_assets


def test_drop_fee_accumulates_over_multiple_assets(
    game_state_factory_fixed_list_asset_gen,
):
    """Dropping several assets in one step charges a fee for each."""
    cfg = DropActionConfig(
        enabled=True, drop_price_fraction=0.5, drop_price_rounding=1_000_000
    )
    asset_a = _idle_asset_with_cost(10_000_000.0)
    asset_b = _idle_asset_with_cost(4_000_000.0)
    initial_cash = 100_000_000.0
    game_state = game_state_factory_fixed_list_asset_gen(
        cash=initial_cash,
        assets={asset_a.id: asset_a, asset_b.id: asset_b},
    )
    game_state._drop_action_config = cfg

    next_state = game_state.step(
        investor_actions={
            asset_a.id: InvestmentLevel.DROP,
            asset_b.id: InvestmentLevel.DROP,
        }
    )

    # 5M + 2M
    assert next_state.cash == pytest.approx(initial_cash - 7_000_000.0)
    assert asset_a.id in next_state.dropped_assets
    assert asset_b.id in next_state.dropped_assets


def test_string_drop_action_normalized_to_drop_level(
    game_state_factory_fixed_list_asset_gen,
):
    """The string action "drop" is normalized to InvestmentLevel.DROP."""
    asset = _idle_asset_with_cost(10_000_000.0)
    game_state = game_state_factory_fixed_list_asset_gen(
        cash=100_000_000.0, assets={asset.id: asset}
    )

    next_state = game_state.step(investor_actions={asset.id: "drop"})

    assert asset.id not in next_state.assets
    assert asset.id in next_state.dropped_assets
    assert next_state.dropped_assets[asset.id].state == AssetState.Dropped
