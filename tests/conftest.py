import copy
import random
import uuid

import pytest

from aiml_pyxis_investment_game import PROJECT_ROOT
from aiml_pyxis_investment_game.config import CapacityConfig
from aiml_pyxis_investment_game.game.asset import AssetState, DrugAsset
from aiml_pyxis_investment_game.game.asset_generators import (
    DUMMY_LIST_DATA,
    FixedListAssetGenerator,
    JSONAssetGenerator,
)
from aiml_pyxis_investment_game.game.game_state import GameState
from aiml_pyxis_investment_game.game.trial import (
    Trial,
    TrialPhase,
    TrialState,
    trials_json_to_trials_sequence,
)


def make_asset_dict(global_seed):
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
                asset_data["trials"], seed=global_seed,
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
            time_until_max_revenue=asset_data["time_until_max_revenue"],
            time_until_patent_expiry=asset_data["time_until_patent_expiry"],
            state=AssetState(asset_data["state"]),
            time_on_market=asset_data["time_on_market"],
            trial=trial,
        )

        # Initialise rng after since it is private attribute
        asset._rng = random.Random(global_seed)
        asset_dict[asset.id] = asset
    return asset_dict


@pytest.fixture
def game_state_factory_fixed_list_asset_gen():
    def _make(
        id=uuid.uuid4(), cash=10000, time=0, horizon=10, assets=None, equilibrium_num_assets=None, max_num_assets=None, asset_arrival_sensitivity_below=1.5, asset_arrival_sensitivity_above=3.0, reinvestment_percentage=1.0, expired_assets=None, global_seed=42, game_ended=False
    ):
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
            realised_costs=[],
            realised_revenues=[],
            running_enpv=[],
            running_eroi=[],
            game_ended=game_ended,
            ended_reason=None,
        )
        game_state._asset_generator = FixedListAssetGenerator(
            global_seed=global_seed, assets_data_list=copy.deepcopy(DUMMY_LIST_DATA)
        )
        game_state._rng = random.Random(global_seed)
        game_state._global_seed = global_seed
        game_state._new_asset_arrival_rate = 1 / 25
        return game_state._post_init_update_enpv_eroi()

    return _make


@pytest.fixture
def game_state_factory_json_asset_gen(valid_json_assets_path):
    def _make(
        id=uuid.uuid4(), cash=10000, time=0, horizon=10, assets=None, expired_assets={}, global_seed=42
    ):
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
            realised_costs=[],
            realised_revenues=[],
            running_enpv=[],
            running_eroi=[],
            game_ended=False,
            ended_reason=None,
        )
        game_state._asset_generator = JSONAssetGenerator(
            global_seed=global_seed,
            assets_dir=valid_json_assets_path,
            indication_spread=1.5,
            indication_drift_speed=1.0,
            trial_cost_multiplier=1.0,
        )
        game_state._rng = random.Random(global_seed)
        game_state._global_seed = global_seed
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
            global_seed=42,
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
        )
        return game_state

    return _make
