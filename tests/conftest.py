import copy
import uuid

import pytest

from pyxis_portfolio_challenge import PROJECT_ROOT
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
    JSONAssetGenerator,
)
from pyxis_portfolio_challenge.game.game_state import GameState
from pyxis_portfolio_challenge.game.trial import (
    Trial,
    TrialPhase,
    TrialState,
    trials_json_to_trials_sequence,
)
from pyxis_portfolio_challenge.rng import init_game_rng

_DISABLED_DISTRIBUTIONAL_PTRS = DistributionalPtrsConfig(
    enabled=False,
    ta_quality_variance={
        "oncology": 0.08,
        "respiratory and immunology": 0.05,
        "vaccines and infectious disease": 0.03,
    },
    asset_noise_std=0.03,
    prior_concentration=5.0,
    observation_noise=0.1,
)
_DISABLED_TA_EXPERIENCE = TAExperienceConfig(
    enabled=False,
    experience_to_full_knowledge=30.0,
    max_expertise_boost=0.05,
    experience_to_max_boost=40.0,
    experience_decay_rate=0.98,
    max_total_experience=60.0,
    phase_experience_weights={
        "phase_1": 0.5,
        "phase_2": 1.0,
        "phase_3": 1.5,
        "approval": 0.5,
    },
    asset_arrival_temperature=0.1,
)
_DISABLED_UNCERTAIN_PTRS = UncertainPtrsConfig(
    enabled=False,
    ta_noise_config={
        "oncology": 0.12,
        "respiratory and immunology": 0.10,
        "vaccines and infectious disease": 0.08,
    },
    phase_noise_multipliers={
        "phase_1": 1.5,
        "phase_2": 1.0,
        "phase_3": 0.75,
        "approval": 0.5,
    },
)
_DISABLED_INVESTMENT_LEVELS = InvestmentLevelsConfig(
    enabled=False,
    levels={
        "none": InvestmentLevelParams(
            cost_modifier=0.0,
            speed_modifier=0.0,
            success_modifier=1.0,
            capacity_cost=0,
            experience_modifier=0.0,
        ),
        "standard": InvestmentLevelParams(
            cost_modifier=1.0,
            speed_modifier=1.0,
            success_modifier=1.0,
            capacity_cost=2,
            experience_modifier=1.0,
        ),
    },
)
_DISABLED_INTERIM_TRIAL_OBS = InterimTrialObservationsConfig(
    enabled=False,
    latent_quality_concentration=10.0,
    initial_noise_scale=0.3,
)
_DISABLED_DROP_ACTION = DropActionConfig(
    enabled=False,
    drop_price_fraction=0.0,
    drop_price_rounding=1_000_000,
)
_DISABLED_MARKETING = MarketingConfig(
    enabled=False,
    dc_cost_fraction=0.035,
    dc_step_boost=0.10,
    dc_decay_rate=0.206,
    be_cost_fraction=0.0175,
    be_boost=0.25,
    be_decay_rate=0.206,
    be_effectiveness=3.5,
)
_DISABLED_CLINICAL_SITES = ClinicalSitesConfig(
    enabled=False,
    starting_sites=4,
    purchase_base_cost=500_000_000,
    purchase_cost_rounding=1_000_000,
    site_development_steps=2,
    agent_priority=False,
    priority_entropy_weight=1.0,
    auction_enabled=True,
    auction_interval_steps=20,
    auction_min_step=10,
    site_max_bid=100_000,
)
_DISABLED_PTRS_READINGS = PtrsReadingsConfig(
    enabled=False,
    cost_fraction=0.05,
    cost_rounding=1_000_000,
    action_space_max_readings=10,
    sigma_logit_base=1.5,
    sigma_ep=None,
    noise_multipliers=[1.0, 1.5, 2.0],
    max_sample_obs=20,
)
_DISABLED_APPROVAL_PHASE = ApprovalPhaseConfig(
    enabled=False,
    duration_min=1,
    duration_max=3,
    success_rate_min=0.85,
    success_rate_max=0.95,
    cost=50_000_000,
)


def make_asset_dict(global_seed):
    init_game_rng(global_seed)
    asset_dict = {}
    for asset_data in copy.deepcopy(DUMMY_LIST_DATA):
        asset_id = uuid.uuid4()
        asset_data["id"] = asset_id

        if AssetState(asset_data["state"]) == AssetState.OnMarket:
            trial = Trial(
                phase=TrialPhase.PHASE_3,
                state=TrialState.PHASE_SUCCESS,
                cost_remaining=0.0,
                time_remaining=0,
                ptrs=1.0,
                next_trial_on_success=None,
            )
        else:
            trial = trials_json_to_trials_sequence(
                asset_data["trials"],
                asset_id=asset_id,
                pending_trial_phase="Phase 1",
                approval_phase_config=None,
                trial_cost_multiplier=1.0,
            )
        asset = DrugAsset(
            id=asset_id,
            name=asset_data["name"],
            therapeutic_area=asset_data["therapeutic_area"],
            type=asset_data["type"],
            description=asset_data["description"],
            max_revenue=asset_data["max_revenue"],
            raw_max_revenue=asset_data["max_revenue"],
            time_until_max_revenue=asset_data["time_until_max_revenue"],
            time_until_patent_expiry=asset_data["time_until_patent_expiry"],
            state=AssetState(asset_data["state"]),
            time_on_market=asset_data["time_on_market"],
            trial=trial,
        )

        asset_dict[asset.id] = asset
    return asset_dict


@pytest.fixture
def game_state_factory_fixed_list_asset_gen():
    def _make(
        id=uuid.uuid4(), cash=10000, time=0, horizon=10, assets=None, equilibrium_num_assets=None, max_num_assets=None, asset_arrival_sensitivity_below=1.5, asset_arrival_sensitivity_above=3.0, reinvestment_percentage=1.0, expired_assets=None, global_seed=42, game_ended=False
    ):
        init_game_rng(global_seed)
        if expired_assets is None:
            expired_assets = {}

        if assets is None:
            assets = make_asset_dict(global_seed)

        game_state = GameState(
            id=id,
            cash=cash,
            time=time,
            horizon=horizon,
            equilibrium_num_assets=len(assets) if equilibrium_num_assets is None else equilibrium_num_assets,
            max_num_assets=len(assets) if max_num_assets is None else max_num_assets,
            asset_arrival_sensitivity_below=asset_arrival_sensitivity_below,
            asset_arrival_sensitivity_above=asset_arrival_sensitivity_above,
            reinvestment_percentage=reinvestment_percentage,
            initial_cash=cash,
            assets=assets,
            failed_assets={},
            expired_assets=expired_assets,
            dropped_assets={},
            realised_costs=[],
            realised_revenues=[],
            running_enpv=[],
            running_eroi=[],
            game_ended=game_ended,
            ended_reason=None,
        )
        game_state._asset_generator = FixedListAssetGenerator(
            assets_data_list=copy.deepcopy(DUMMY_LIST_DATA)
        )
        game_state._new_asset_arrival_rate = 1 / 25
        return game_state._post_init_update_enpv_eroi()

    return _make


@pytest.fixture
def game_state_factory_json_asset_gen(valid_json_assets_path):
    def _make(
        id=uuid.uuid4(), cash=10000, time=0, horizon=10, assets=None, expired_assets={}, global_seed=42
    ):
        init_game_rng(global_seed)
        if assets is None:
            assets = make_asset_dict(global_seed)

        game_state = GameState(
            id=id,
            cash=cash,
            time=time,
            horizon=horizon,
            equilibrium_num_assets=len(assets),
            asset_arrival_sensitivity_below=1.5,
            asset_arrival_sensitivity_above=3.0,
            reinvestment_percentage=1.0,
            max_num_assets=len(assets),
            initial_cash=cash,
            assets=assets,
            failed_assets={},
            expired_assets=expired_assets,
            dropped_assets={},
            realised_costs=[],
            realised_revenues=[],
            running_enpv=[],
            running_eroi=[],
            game_ended=False,
            ended_reason=None,
        )
        game_state._asset_generator = JSONAssetGenerator(
            assets_dir=valid_json_assets_path,
            indication_spread=1.5,
            indication_drift_speed=1.0,
            trial_cost_multiplier=1.0,
        )
        game_state._new_asset_arrival_rate = 1 / 25
        return game_state

    return _make


@pytest.fixture
def valid_json_assets_path():
    """Get path to valid test asset data."""
    return PROJECT_ROOT / "tests" / "data" / "generated_assets"


@pytest.fixture
def json_game_state_factory(valid_json_assets_path):
    """Create a test game state using JSONAssetGenerator."""

    def _make(num_assets=5):
        game_state = GameState.initialise_new_game(
            asset_generator_cls=JSONAssetGenerator,
            num_assets=num_assets,
            cash=10000000,
            horizon=50,
            max_num_assets=20,
            asset_arrival_sensitivity_below=1.5,
            asset_arrival_sensitivity_above=3.0,
            reinvestment_percentage=1.0,
            seed=42,
            assets_dir=valid_json_assets_path,
            indication_spread=1.5,
            indication_drift_speed=1.0,
            trial_cost_multiplier=1.0,
            rd_capacity_config=CapacityConfig(
                enabled=False,
                base_capacity=80.0,
                overage_max_penalty=0.5,
                overage_cost_max_penalty=0.5,
                overage_scaling="linear",
            ),
            investment_levels_config=_DISABLED_INVESTMENT_LEVELS,
            interim_trial_observations_config=_DISABLED_INTERIM_TRIAL_OBS,
            distributional_ptrs_config=_DISABLED_DISTRIBUTIONAL_PTRS,
            drop_action_config=_DISABLED_DROP_ACTION,
            marketing_config=_DISABLED_MARKETING,
            clinical_sites_config=_DISABLED_CLINICAL_SITES,
            ptrs_readings_config=_DISABLED_PTRS_READINGS,
            ta_experience_config=_DISABLED_TA_EXPERIENCE,
            uncertain_ptrs_config=_DISABLED_UNCERTAIN_PTRS,
            approval_phase_config=_DISABLED_APPROVAL_PHASE,
        )
        return game_state

    return _make
