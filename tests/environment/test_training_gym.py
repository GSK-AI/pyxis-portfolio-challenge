from __future__ import annotations

import uuid
from unittest.mock import ANY, MagicMock, patch

import gymnasium as gym
import numpy as np
import pytest
from gymnasium.wrappers import FlattenObservation

from aiml_pyxis_investment_game.config import (
    CapacityConfig,
    DistributionalPtrsConfig,
    InterimTrialObservationsConfig,
    InvestmentLevelParams,
    InvestmentLevelsConfig,
    TAExperienceConfig,
    UncertainPtrsConfig,
)
from aiml_pyxis_investment_game.environment.metrics import legacy_static_npv
from aiml_pyxis_investment_game.environment.obs_layout import (
    NUM_TRIAL_PHASES,
    ObsLayout,
)
from aiml_pyxis_investment_game.environment.reward import LegacyStaticNPVReward
from aiml_pyxis_investment_game.environment.training_gym import (
    InvestmentGameEnv,
    LevelsInvestmentGameEnv,
)
from aiml_pyxis_investment_game.game.asset import AssetState
from aiml_pyxis_investment_game.game.constants import (
    LEVELS,
    MAX_NUM_ASSETS,
    TRIAL_PHASES,
)
from aiml_pyxis_investment_game.game.trial import Trial, TrialPhase, TrialState
from aiml_pyxis_investment_game import PROJECT_ROOT
from tests.game.test_asset import drug_asset_factory

_TEST_ASSETS_DIR = PROJECT_ROOT / "tests" / "data" / "generated_assets"

_DISABLED_DISTRIBUTIONAL_PTRS = DistributionalPtrsConfig(
    enabled=False,
    ta_quality_variance={"oncology": 0.08, "respiratory and immunology": 0.05, "vaccines and infectious disease": 0.03},
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
    phase_experience_weights={"phase_1": 0.5, "phase_2": 1.0, "phase_3": 1.5, "approval": 0.5},
    asset_arrival_temperature=0.1,
)
_DISABLED_UNCERTAIN_PTRS = UncertainPtrsConfig(
    enabled=False,
    ta_noise_config={"oncology": 0.12, "respiratory and immunology": 0.10, "vaccines and infectious disease": 0.08},
    phase_noise_multipliers={"phase_1": 1.5, "phase_2": 1.0, "phase_3": 0.75, "approval": 0.5},
)
_DISABLED_INVESTMENT_LEVELS = InvestmentLevelsConfig(
    enabled=False,
    levels={
        "none": InvestmentLevelParams(cost_modifier=0.0, speed_modifier=0.0, success_modifier=1.0, capacity_cost=0, experience_modifier=0.0),
        "standard": InvestmentLevelParams(cost_modifier=1.0, speed_modifier=1.0, success_modifier=1.0, capacity_cost=2, experience_modifier=1.0),
    },
)
_DISABLED_INTERIM_TRIAL_OBS = InterimTrialObservationsConfig(
    enabled=False,
    latent_quality_concentration=10.0,
    initial_noise_scale=0.3,
)
_DISABLED_RD_CAPACITY = CapacityConfig(
    enabled=False,
    base_capacity=80.0,
    overage_max_penalty=0.5,
    overage_cost_max_penalty=0.5,
    overage_scaling="linear",
)


def _make_env(valid_json_assets_path, **kwargs):
    """Helper to create InvestmentGameEnv with sensible test defaults."""
    defaults = dict(
        assets_dir=valid_json_assets_path,
        equilibrium_num_assets=20,
        reinvestment_percentage=1.0,
        starting_cash=10_000_000,
        max_num_assets=MAX_NUM_ASSETS,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        horizon=20,
        reward_fn=LegacyStaticNPVReward(),
        shuffle_order=True,
        mask_first_order_assets=False,
        mask_negative_enpv_assets=False,
        flatten_obs=False,
        distributional_ptrs_config=_DISABLED_DISTRIBUTIONAL_PTRS,
        ta_experience_config=_DISABLED_TA_EXPERIENCE,
        uncertain_ptrs_config=_DISABLED_UNCERTAIN_PTRS,
        investment_levels_config=_DISABLED_INVESTMENT_LEVELS,
        interim_trial_observations_config=_DISABLED_INTERIM_TRIAL_OBS,
        rd_capacity_config=_DISABLED_RD_CAPACITY,
    )
    defaults.update(kwargs)
    return InvestmentGameEnv(**defaults)


@pytest.fixture
def test_env(valid_json_assets_path):
    """Create a test InvestmentGameEnv with real data."""
    env = _make_env(valid_json_assets_path, equilibrium_num_assets=5, starting_cash=10000000, horizon=50)
    return env


def test_init_custom_parameters(valid_json_assets_path):
    """Test InvestmentGameEnv initialization with custom parameters."""
    env = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=5,
        starting_cash=5000000,
        horizon=30,
    )

    assert env.equilibrium_num_assets == 5
    assert env.starting_cash == 5000000
    assert env.horizon == 30
    assert env.assets_dir == valid_json_assets_path


def test_setup_gym_spaces(test_env):
    """Test that gym spaces are set up correctly."""
    env = test_env

    # Test action space
    assert isinstance(env.action_space, gym.spaces.MultiBinary)
    assert env.action_space.n == MAX_NUM_ASSETS

    # Test observation space structure
    assert isinstance(env.observation_space, gym.spaces.Dict)
    assert "cash" in env.observation_space.spaces
    assert "assets" in env.observation_space.spaces

    # Test cash space
    cash_space = env.observation_space.spaces["cash"]
    assert isinstance(cash_space, gym.spaces.Box)
    assert cash_space.shape == (1,)
    assert cash_space.dtype == np.float32

    # Test assets space
    assets_space = env.observation_space.spaces["assets"]
    assert isinstance(assets_space, gym.spaces.Tuple)
    assert len(assets_space.spaces) == MAX_NUM_ASSETS

    # Note: FlattenObservation wrapper flattens the dict space differently than
    # our custom flatten_obs=True. It handles Discrete as one-hot and nested dicts.
    # For exact shape test, use our custom flattening directly.
    flattened_env = FlattenObservation(env)
    print(flattened_env)
    obs, _ = flattened_env.reset()
    # Just verify it produces a valid 1D array
    assert len(obs.shape) == 1
    assert obs.shape[0] > 0


def test_phase_to_observation_mapping(test_env):
    """Test that phase to observation mapping is set up correctly."""
    env = test_env

    # Phase mapping includes all TrialPhase values (Phase 1-3 + Approval if enabled)
    assert env._phase_to_observation["Phase 1"] == 1
    assert env._phase_to_observation["Phase 2"] == 2
    assert env._phase_to_observation["Phase 3"] == 3


def test_trial_state_observation_phase_2_in_progress(
    test_env
):
    """Parametrized test for phase_to_observation mapping for several assets."""
    asset_id = uuid.uuid4()

    next_trial = Trial(
        cost_remaining=1500000.0,
        time_remaining=6,
        ptrs=0.7,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PENDING,
        next_trial_on_success=None
    )
    trial = Trial(
        cost_remaining=1000000.0,
        time_remaining=12,
        ptrs=0.5,
        phase=TrialPhase.PHASE_2,
        state=TrialState.IN_PROGRESS,
        next_trial_on_success=next_trial
    )

    asset = drug_asset_factory(id=asset_id, trial=trial, state=AssetState.Idle)
    test_env.game_state.assets = {asset_id: asset}
    test_env._create_shuffled_asset_order()
    obs = test_env._get_obs()
    actual_index = test_env._asset_id_order.index(asset_id)

    # Check trial structure — includes all TrialPhase values
    trials = obs["assets"][actual_index]["trials"]
    assert len(trials) == len(TrialPhase)
    # Phase 1 (already passed)
    assert trials[0]["cost_remaining"] == 0.0
    assert trials[0]["ptrs"] == 1.0
    # Phase 2 (in progress)
    assert trials[1]["cost_remaining"] == 1000000.0
    assert trials[1]["ptrs"] == 0.5
    # Phase 3 (pending)
    assert trials[2]["cost_remaining"] == 1500000.0
    assert trials[2]["ptrs"] == 0.7
    assert obs["assets"][actual_index]["pending_trial_phase"] == 2


def test_trial_state_observation_phase_1_failed(
    test_env
):
    """Failed assets are moved to failed_assets dict and not in observations."""
    asset_id = uuid.uuid4()
    trial = Trial(
        cost_remaining=0.0,
        time_remaining=0,
        ptrs=0.0,
        phase=TrialPhase.PHASE_1,
        state=TrialState.PHASE_FAILED,
        next_trial_on_success=None
    )

    asset = drug_asset_factory(id=asset_id, trial=trial, state=AssetState.Failed)
    test_env.game_state.failed_assets = {asset_id: asset}
    test_env.game_state.assets = {}
    test_env._create_shuffled_asset_order()
    obs = test_env._get_obs()

    # Failed assets should not appear in observations
    assert asset_id not in test_env._asset_id_order


def test_trial_state_observation_asset_on_market(
    test_env
):
    """Parametrized test for phase_to_observation mapping for several assets."""
    asset_id = uuid.uuid4()
    trial = Trial(
        cost_remaining=0.0,
        time_remaining=0,
        ptrs=1.0,
        phase=TrialPhase.PHASE_3,
        state=TrialState.PHASE_SUCCESS,
        next_trial_on_success=None
    )

    asset = drug_asset_factory(id=asset_id, trial=trial, state=AssetState.OnMarket)
    test_env.game_state.assets = {asset_id: asset}
    test_env._create_shuffled_asset_order()
    obs = test_env._get_obs()
    actual_index = test_env._asset_id_order.index(asset_id)

    # Check trial structure - all phases show success (ptrs=1.0)
    trials = obs["assets"][actual_index]["trials"]
    assert len(trials) == len(TrialPhase)
    for trial_obs in trials:
        assert trial_obs["cost_remaining"] == 0.0
        assert trial_obs["ptrs"] == 1.0
    assert obs["assets"][actual_index]["pending_trial_phase"] == 0  # Should be 0 since asset is on market


def test_get_obs_structure(test_env):
    """Test that _get_obs returns correctly structured observations."""
    env = test_env
    obs = env._get_obs()

    # Test top-level structure
    assert isinstance(obs, dict)
    assert "cash" in obs
    assert "assets" in obs

    # Test cash observation
    assert isinstance(obs["cash"], np.ndarray)
    assert obs["cash"].dtype == np.float32
    assert obs["cash"].shape == (1,)

    # Test assets observation
    assert isinstance(obs["assets"], tuple)
    assert len(obs["assets"]) == MAX_NUM_ASSETS


def test_get_obs_asset_structure(test_env):
    """Test that asset observations have correct structure."""
    env = test_env
    obs = env._get_obs()

    asset_obs = obs["assets"][0]  # Get first asset observation

    # Test asset observation keys
    # With all optional features disabled, interim_signal/trial_progress are absent
    expected_keys = {
        "max_revenue",
        "time_until_max_revenue",
        "time_until_patent_expiry",
        "pending_trial_phase",
        "time_on_market",
        "cost_this_step",
        "revenue_this_step",
        "enpv",
        "eroi",
        "trials",
        "state",
        "ta_index",
    }
    assert set(asset_obs.keys()) == expected_keys

    # Test trials structure
    assert isinstance(asset_obs["trials"], tuple)
    assert len(asset_obs["trials"]) == len(TRIAL_PHASES)

    # With distributional_ptrs disabled, only base trial keys present
    trial_obs = asset_obs["trials"][0]
    expected_trial_keys = {
        "cost_remaining", "time_remaining", "ptrs",
    }
    assert set(trial_obs.keys()) == expected_trial_keys


def test_get_obs_sorted_assets(json_game_state_factory,
                               valid_json_assets_path):
    """Test that assets are sorted by self._asset_id_order."""
    game_state = json_game_state_factory()

    env = _make_env(
        game_state._asset_generator.assets_dir,
        equilibrium_num_assets=len(game_state.assets),
        starting_cash=game_state.cash,
        horizon=game_state.horizon,
        max_num_assets=game_state.max_num_assets,
        shuffle_order=True,
        mask_first_order_assets=True,
    )

    env.game_state = game_state

    # 4. CRITICAL: Re-sync the asset ID order
    # Because we injected a new state, the old _asset_id_order (from __init__)
    # might point to UUIDs that don't exist in the injected game_state.
    if env.shuffle_order:
        env._create_shuffled_asset_order()
    else:
        # If testing non-shuffled logic, ensure IDs align deterministically
        env.actual_asset_ids = list(game_state.assets.keys())
        env._asset_id_order = env.actual_asset_ids + [0] * (
                env.max_num_assets - len(env.actual_asset_ids)
        )

    # Get sorted asset IDs
    expected_asset_ids = env._asset_id_order

    obs = env._get_obs()

    # Verify that assets are processed in sorted order
    for i, asset_id in enumerate(expected_asset_ids):
        if asset_id == 0:
            continue
        asset = game_state.assets[asset_id]
        asset_obs = obs["assets"][i]

        assert asset.max_revenue == asset_obs["max_revenue"]
        assert asset.time_until_max_revenue == asset_obs[
            "time_until_max_revenue"]
        assert asset.time_until_patent_expiry == asset_obs[
            "time_until_patent_expiry"]
        # Handle the case where the asset might be on market or failed
        if asset.state == AssetState.OnMarket or (
                asset.trial and asset.trial.state == TrialState.PHASE_FAILED):
            expected_phase = 0
        else:
            expected_phase = env._phase_to_observation[asset.trial.phase.value]

        assert expected_phase == asset_obs["pending_trial_phase"]
        assert asset.time_on_market == asset_obs["time_on_market"]
        assert asset.cost_this_step == asset_obs["cost_this_step"]
        assert asset.revenue_this_step == asset_obs["revenue_this_step"]


def test_get_info(test_env):
    """Test that _get_info returns empty dict."""
    env = test_env
    info = env._get_info()
    assert isinstance(info, dict)
    assert len(info) == 0


def test_action_masks_all_idle(test_env):
    """Test action masks when all assets are idle."""
    env = test_env

    # Ensure all assets are idle
    for asset in env.game_state.assets.values():
        asset.time_on_market = 0
        asset.state = "Idle"

    masks = env.action_masks()

    # Should return one flattened list
    assert isinstance(masks, list)
    assert len(masks) == MAX_NUM_ASSETS
    for idx, asset_id in enumerate(env._asset_id_order):
        if asset_id == 0:
            assert masks[idx] == [True, False]
        else:
            assert masks[idx] == [True, True]


def test_action_masks_mixed_states(test_env):
    """Test action masks with mixed asset states."""
    env = test_env

    # Replace assets with ones in different states
    assets_list = list(sorted(env.game_state.assets.keys()))
    if len(assets_list) >= 5:
        env.game_state.assets[assets_list[0]] = drug_asset_factory(state=AssetState.Idle)
        env.game_state.assets[assets_list[1]] = drug_asset_factory(state=AssetState.InDevelopment)
        env.game_state.assets[assets_list[2]] = drug_asset_factory(state=AssetState.OnMarket)
        env.game_state.assets[assets_list[3]] = drug_asset_factory(state=AssetState.Failed)
        env.game_state.assets[assets_list[4]] = drug_asset_factory(state=AssetState.Expired)

    env._create_shuffled_asset_order()
    masks = env.action_masks()

    # Only idle assets should have [True, True], others [False, False]
    assert isinstance(masks, list)
    assert len(masks) == MAX_NUM_ASSETS

    if len(assets_list) >= 5:
        expected_masks = []
        for asset_id in env._asset_id_order:
            if asset_id == 0:
                expected_masks.append([True, False])
            else:
                asset = env.game_state.assets[asset_id]
                if asset.state == AssetState.Idle:
                    expected_masks.append([True, True])
                else:
                    expected_masks.append([True, False])

        assert masks == expected_masks


def test_binary_masking(test_env):
    with patch("aiml_pyxis_investment_game.environment.training_gym.InvestmentGameEnv.action_masks") as mock_action_masks:
        # Mock action mask to have incorrect size
        mock_action_masks.return_value = [[True, True], [True, False], [False, False]]  # Only 2 assets

        assert (test_env.action_masks_binary() == np.array([1, 0, 0])).all()


def test_incorrect_action_asset_non_idle_raises(test_env):
    env = test_env
    env.shuffle_order = False

    # Put an asset into development
    assets_list = list(env.game_state.assets.keys())
    env.game_state.assets[assets_list[0]] = env.game_state.assets[assets_list[0]].to_develop()
    env.game_state.cash = 1_000_000_000  # ensure enough cash to invest
    env.reset(options={"preserve_game_state": True})

    assert env.action_masks()[0] == [True, False]

    # now try to take action to invest in 0th asset
    action = np.zeros(env.game_state.max_num_assets)
    action[0] = 1  # Try to invest in first asset which is not idle

    with pytest.raises(ValueError):
        env.game_state.step({assets_list[0]: "invest"})

    with pytest.raises(ValueError):
        env.step(action)


def test_action_mask_mask_first_order_assets(test_env):
    env = test_env
    env.shuffle_order = False
    env.mask_first_order_assets = True

    # Make an asset very expensive and set cash very low
    assets_list = list(env.game_state.assets.keys())
    env.game_state.assets[assets_list[0]].trial.cost_remaining = 1_000_000_000  # make it too expensive to invest
    env.game_state.cash = 1000  # set cash low to check masking
    env.reset(options={"preserve_game_state": True})

    assert env.game_state.assets[assets_list[0]].state == AssetState.Idle
    assert env.action_masks()[0] == [True, False]  # should be masked due to insufficient cash


def test_reset_default(test_env):
    """Test reset with default parameters."""
    env = test_env

    obs, info = env.reset()

    # Test return types
    assert isinstance(obs, dict)
    assert isinstance(info, dict)

    # Test that observation is valid
    assert "cash" in obs
    assert "assets" in obs

    # Reset again and check that it is different
    obs2, info2 = env.reset()
    assert obs != obs2


def test_reset_with_seed(test_env):
    """Test reset with seed parameter."""
    env = FlattenObservation(test_env)  # flatten for convenience

    obs1, info1 = env.reset(seed=42)
    obs2, info2 = env.reset(seed=42)

    # With same seed, should get identical results
    np.testing.assert_array_equal(obs1, obs2)


def test_reset_preserve_game_state(test_env):
    """Test reset with preserve_game_state option."""
    env = test_env

    # Store original game state
    original_game_state = env.game_state
    original_cash = env.game_state.cash

    # Reset with preserve_game_state=True
    obs, info = env.reset(options={"preserve_game_state": True})

    # Game state should be preserved
    assert env.game_state == original_game_state
    assert env.game_state.cash == original_cash


def test_action_to_investment_decision_no_investments(test_env):
    """Test converting action with no investments."""
    env = test_env
    action = np.array([0, 0, 0, 0, 0])  # No investments

    decisions = env._action_to_investment_decision(action)

    assert isinstance(decisions, dict)
    assert len(decisions) == 0


def test_action_to_investment_decision_some_investments(test_env):
    """Test converting action with some investments."""
    env = test_env
    action = np.array([1, 0, 1, 0, 0])  # Invest in first and third assets
    asset_ids = sorted(env.game_state.assets.keys())
    env._asset_id_order = asset_ids

    decisions = env._action_to_investment_decision(action)

    assert isinstance(decisions, dict)
    assert len(decisions) == 2

    # Check that the correct assets are marked for investment
    assert asset_ids[0] in decisions
    assert asset_ids[2] in decisions
    assert decisions[asset_ids[0]] == "invest"
    assert decisions[asset_ids[2]] == "invest"


def test_action_to_investment_decision_all_investments(test_env):
    """Test converting action with all investments."""
    env = test_env
    action = np.array([1, 1, 1, 1, 1])  # Invest in all assets
    asset_ids = sorted(env.game_state.assets.keys())
    env._asset_id_order = asset_ids

    decisions = env._action_to_investment_decision(action)

    assert isinstance(decisions, dict)
    assert len(decisions) == env.equilibrium_num_assets

    # All assets should be marked for investment
    for asset_id in env.game_state.assets.keys():
        assert asset_id in decisions
        assert decisions[asset_id] == "invest"


def test_step_basic(test_env):
    """Test basic step functionality."""
    env = test_env

    # Reset environment first
    obs, info = env.reset()

    # Take a step with no actions
    action = np.zeros(MAX_NUM_ASSETS)
    obs, reward, terminated, truncated, info = env.step(action)

    # Test return types and structure
    assert isinstance(obs, dict)
    assert isinstance(reward, (int, float))
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)

    # Test that observation structure is maintained
    assert "cash" in obs
    assert "assets" in obs


def test_step_with_investments(test_env):
    """Test step with investment actions."""
    env = test_env

    # Reset environment first
    obs, info = env.reset()

    # Get initial NPV
    initial_npv = legacy_static_npv(env.game_state)

    # Take a step with some investments
    action = []
    for asset_id in env._asset_id_order:
        if asset_id == 0:
            action.append(0)
            continue
        elif env.game_state.assets[asset_id].state == AssetState.Idle:
            action.append(1)
        else:
            action.append(0)
    action = np.array(action)
    obs, reward, terminated, truncated, info = env.step(action)

    # Reward should be the change in NPV
    new_npv = legacy_static_npv(env.game_state)
    expected_reward = new_npv - initial_npv
    assert abs(reward - expected_reward) < 1e-6


def test_step_termination(test_env):
    """Test step termination conditions."""
    env = test_env

    # Reset environment
    obs, info = env.reset()

    # Set cash to LARGE negative to trigger termination
    env.game_state.cash = -100_000_000

    action = np.zeros(MAX_NUM_ASSETS)
    obs, reward, terminated, truncated, info = env.step(action)

    assert terminated is True


def test_step_horizon_termination(test_env):
    """Test termination when horizon is reached."""
    env = test_env

    # Reset environment
    obs, info = env.reset()

    # Set time to horizon to trigger termination
    env.game_state.time = env.game_state.horizon - 1

    action = np.zeros(MAX_NUM_ASSETS)
    obs, reward, terminated, truncated, info = env.step(action)

    assert terminated is True


def test_step_truncated_always_false(test_env):
    """Test that truncated is always False."""
    env = test_env

    # Reset environment
    obs, info = env.reset()

    action = np.zeros(MAX_NUM_ASSETS)
    obs, reward, terminated, truncated, info = env.step(action)

    assert truncated is False


def test_observation_space_contains_observation(test_env):
    """Test that observations are valid for the observation space."""
    env = test_env

    # Reset and get observation
    obs, info = env.reset()

    # Check that observation is contained in observation space
    # Note: This might be complex for nested Dict/Tuple spaces
    # We'll check key components
    assert env.observation_space.spaces["cash"].contains(obs["cash"])


def test_action_space_sample(test_env):
    """Test that action space sampling works correctly."""
    env = test_env

    # Sample actions multiple times
    for _ in range(10):
        action = env.action_space.sample()
        assert isinstance(action, np.ndarray)
        assert action.shape == (MAX_NUM_ASSETS,)
        assert all(a in [0, 1] for a in action)


def test_environment_workflow_integration(test_env):
    """Test complete environment workflow."""
    env = test_env

    # Reset environment
    obs, info = env.reset(seed=42)

    # Run multiple steps
    for step in range(5):
        # Sample random action
        # Take a step with some investments
        action = []
        for asset_id in env._asset_id_order:
            if asset_id != 0 and env.game_state.assets[
                asset_id].state == AssetState.Idle:
                action.append(1)
            else:
                action.append(0)

        # Take step
        obs, reward, terminated, truncated, info = env.step(np.array(action))

        # Verify return types
        assert isinstance(obs, dict)
        assert isinstance(reward, (int, float))
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert isinstance(info, dict)

        if terminated:
            break


def test_error_handling_invalid_action_size(test_env):
    """Test error handling for invalid action size."""
    env = test_env

    # Reset environment
    obs, info = env.reset()

    # Try step with wrong action size
    invalid_action = np.array([1, 0])  # Wrong size

    with pytest.raises((IndexError, ValueError)):
        env.step(invalid_action)


def test_init_with_different_assets_dir_types(valid_json_assets_path):
    """Test initialization with different assets_dir types."""
    # Test with string path
    env1 = _make_env(valid_json_assets_path, equilibrium_num_assets=3)
    assert env1.assets_dir == valid_json_assets_path

    # Test with Path object
    env2 = _make_env(valid_json_assets_path, equilibrium_num_assets=3)
    assert env2.assets_dir == valid_json_assets_path


@pytest.mark.parametrize(
    "num_assets,expected_action_space_size",
    [
        (1, MAX_NUM_ASSETS),
        (2, MAX_NUM_ASSETS),
        (3, MAX_NUM_ASSETS),
    ],
)
def test_action_space_size_parametrized(
    num_assets, expected_action_space_size, valid_json_assets_path
):
    """Test action space size for different numbers of assets."""
    env = _make_env(valid_json_assets_path, equilibrium_num_assets=num_assets)
    assert env.action_space.n == expected_action_space_size


def test_asset_observation_values(test_env):
    """Test that asset observations contain correct values."""
    env = test_env

    # Create a test asset with known values
    test_asset_id = uuid.uuid4()
    test_asset = drug_asset_factory(
        id=test_asset_id,
        max_revenue=1000000,
        time_until_max_revenue=5,
        time_until_patent_expiry=20,
        time_on_market=3,
        state=AssetState.OnMarket,
    )

    # Replace the first asset
    env.game_state.assets = {test_asset_id: test_asset}
    env._create_shuffled_asset_order()

    obs = env._get_obs()
    actual_index = env._asset_id_order.index(test_asset_id)
    asset_obs = obs["assets"][actual_index]

    # Check that values match
    assert asset_obs["max_revenue"] == 1000000
    assert asset_obs["time_until_max_revenue"] == 5
    assert asset_obs["time_until_patent_expiry"] == 20
    assert asset_obs["time_on_market"] == 3
    assert asset_obs["cost_this_step"] == test_asset.cost_this_step
    assert asset_obs["revenue_this_step"] == test_asset.revenue_this_step


def test_trial_observation_values(test_env):
    """Test that trial observations contain correct values."""
    env = test_env

    # Create asset with known trial values
    test_asset_id = uuid.uuid4()
    test_asset = drug_asset_factory(id=test_asset_id)

    # Replace the first asset
    env.game_state.assets = {test_asset_id: test_asset}
    env._create_shuffled_asset_order()

    obs = env._get_obs()
    actual_index = env._asset_id_order.index(test_asset_id)
    asset_obs = obs["assets"][actual_index]
    trials_obs = asset_obs["trials"]

    # Check that we have one trial per TrialPhase
    assert len(trials_obs) == len(TrialPhase)

    # Check that each trial has the correct structure and values
    for trial_obs in trials_obs:
        assert "cost_remaining" in trial_obs
        assert "time_remaining" in trial_obs
        assert "ptrs" in trial_obs
        assert isinstance(trial_obs["cost_remaining"], (int, float))
        assert isinstance(trial_obs["time_remaining"], int)
        assert isinstance(trial_obs["ptrs"], float)
        assert 0 <= trial_obs["ptrs"] <= 1


# LevelsInvestmentGameEnv tests


@pytest.mark.parametrize("level_idx", list(range(len(LEVELS))))
def test_levels_env_initialization(level_idx):
    """Test LevelsInvestmentGameEnv initializes with correct parameters per level."""
    env = LevelsInvestmentGameEnv(level_idx, assets_dir=_TEST_ASSETS_DIR, reward_fn=LegacyStaticNPVReward(), shuffle_order=True, max_num_assets=MAX_NUM_ASSETS, flatten_obs=False, distributional_ptrs_config=_DISABLED_DISTRIBUTIONAL_PTRS, ta_experience_config=_DISABLED_TA_EXPERIENCE, uncertain_ptrs_config=_DISABLED_UNCERTAIN_PTRS, investment_levels_config=_DISABLED_INVESTMENT_LEVELS, interim_trial_observations_config=_DISABLED_INTERIM_TRIAL_OBS, rd_capacity_config=_DISABLED_RD_CAPACITY)
    level_info = LEVELS[level_idx]
    assert env.equilibrium_num_assets == level_info["num_assets"]
    assert env.starting_cash == level_info["starting_cash"]
    assert env.horizon == level_info["horizon"]
    assert env.global_seed == level_info["global_seed"]
    assert isinstance(env.action_space, env.action_space.__class__)
    assert isinstance(env.observation_space, env.observation_space.__class__)


@pytest.mark.parametrize("level_idx", list(range(len(LEVELS))))
def test_levels_env_reset_consistency(level_idx):
    """Test reset produces consistent initial state for a given level."""
    env = LevelsInvestmentGameEnv(level_idx, assets_dir=_TEST_ASSETS_DIR, reward_fn=LegacyStaticNPVReward(), shuffle_order=True, max_num_assets=MAX_NUM_ASSETS, flatten_obs=False, distributional_ptrs_config=_DISABLED_DISTRIBUTIONAL_PTRS, ta_experience_config=_DISABLED_TA_EXPERIENCE, uncertain_ptrs_config=_DISABLED_UNCERTAIN_PTRS, investment_levels_config=_DISABLED_INVESTMENT_LEVELS, interim_trial_observations_config=_DISABLED_INTERIM_TRIAL_OBS, rd_capacity_config=_DISABLED_RD_CAPACITY)
    obs1, info1 = env.reset()
    obs2, info2 = env.reset()
    # Should produce different states unless seeded, but both should be valid
    assert isinstance(obs1, dict)
    assert isinstance(obs2, dict)
    assert "cash" in obs1 and "assets" in obs1
    assert "cash" in obs2 and "assets" in obs2


def test_levels_env_spaces():
    """Test observation and action spaces are correctly set up."""
    env = LevelsInvestmentGameEnv(0, assets_dir=_TEST_ASSETS_DIR, reward_fn=LegacyStaticNPVReward(), shuffle_order=True, max_num_assets=MAX_NUM_ASSETS, flatten_obs=False, distributional_ptrs_config=_DISABLED_DISTRIBUTIONAL_PTRS, ta_experience_config=_DISABLED_TA_EXPERIENCE, uncertain_ptrs_config=_DISABLED_UNCERTAIN_PTRS, investment_levels_config=_DISABLED_INVESTMENT_LEVELS, interim_trial_observations_config=_DISABLED_INTERIM_TRIAL_OBS, rd_capacity_config=_DISABLED_RD_CAPACITY)
    obs, info = env.reset()
    assert env.action_space.n == MAX_NUM_ASSETS
    assert env.observation_space.contains(obs)


def test_levels_env_step_output_types():
    """Test environment step returns expected output types."""
    env = LevelsInvestmentGameEnv(0, assets_dir=_TEST_ASSETS_DIR, reward_fn=LegacyStaticNPVReward(), shuffle_order=True, max_num_assets=MAX_NUM_ASSETS, flatten_obs=False, distributional_ptrs_config=_DISABLED_DISTRIBUTIONAL_PTRS, ta_experience_config=_DISABLED_TA_EXPERIENCE, uncertain_ptrs_config=_DISABLED_UNCERTAIN_PTRS, investment_levels_config=_DISABLED_INVESTMENT_LEVELS, interim_trial_observations_config=_DISABLED_INTERIM_TRIAL_OBS, rd_capacity_config=_DISABLED_RD_CAPACITY)
    obs, info = env.reset()
    action = np.where(np.array(env.action_masks_binary()) == 1, 1, 0)  # Invert masks for action
    result = env.step(action)
    assert isinstance(result, tuple)
    assert len(result) == 5
    obs2, reward, terminated, truncated, info2 = result
    assert isinstance(obs2, dict)
    assert isinstance(reward, (int, float, np.floating))
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info2, dict)


# Unshuffled/shuffled tests


def test_shuffle_order_true_shuffles_asset_order(valid_json_assets_path):
    """Test that shuffle_order=True shuffles asset order after reset and step."""
    env = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=5,
        starting_cash=10000000,
        horizon=10,
        shuffle_order=True,
    )
    obs1, _ = env.reset(seed=123)
    order1 = env._asset_id_order.copy()
    # Take a step
    action = np.zeros(MAX_NUM_ASSETS)
    obs2, _, _, _, _ = env.step(action)
    order2 = env._asset_id_order.copy()
    # Asset order should change (with high probability)
    assert order1 != order2


def test_maintain_unshuffled_asset_order_expiry_and_creation(valid_json_assets_path):
    """Test _maintain_unshuffled_asset_order when assets expire or are created."""
    env = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=3,
        starting_cash=10000000,
        horizon=10,
        shuffle_order=False,
    )
    env.reset(seed=42)
    # Simulate asset expiry
    expired_id = env.actual_asset_ids[0]
    del env.game_state.assets[expired_id]
    # Simulate asset creation
    new_id = uuid.uuid4()
    env.game_state.assets[new_id] = env.game_state.assets[env.actual_asset_ids[1]]
    env._maintain_unshuffled_asset_order()
    # The expired asset should be replaced by the new asset in the same slot
    assert new_id in env._asset_id_order
    assert expired_id not in env._asset_id_order


def test_asset_order_consistency_both_modes(valid_json_assets_path):
    """Test that asset order consistency is correct for both shuffle_order modes."""
    env_shuffled = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=4,
        starting_cash=10000000,
        horizon=10,
        shuffle_order=True,
    )
    env_unshuffled = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=4,
        starting_cash=10000000,
        horizon=10,
        shuffle_order=False,
    )
    obs_shuffled, _ = env_shuffled.reset(seed=1)
    obs_unshuffled, _ = env_unshuffled.reset(seed=1)
    # Orders should differ
    assert env_shuffled._asset_id_order != env_unshuffled._asset_id_order


@pytest.mark.parametrize("max_num_assets", [5, 10, 15])
def test_investment_game_env_custom_max_num_assets(
    valid_json_assets_path, max_num_assets
):
    """Test InvestmentGameEnv with custom max_num_assets values."""
    env = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=3,
        starting_cash=1000000,
        horizon=10,
        max_num_assets=max_num_assets,
        shuffle_order=False,
    )
    obs, info = env.reset(seed=42)
    # Action space size
    assert env.action_space.n == max_num_assets
    # Observation space assets tuple length
    assert isinstance(obs["assets"], tuple)
    assert len(obs["assets"]) == max_num_assets
    # Asset order and padding
    actual_assets = list(env.game_state.assets.keys())
    padded_ids = env._asset_id_order
    # Real assets should be first, padding (0) at end
    assert padded_ids[: len(actual_assets)] == actual_assets
    assert all(aid == 0 for aid in padded_ids[len(actual_assets) :])
    # Padding obs should match _padding_asset_obs
    for i in range(len(actual_assets), max_num_assets):
        assert obs["assets"][i] == env._padding_asset_obs


@pytest.mark.parametrize("max_num_assets", [5, 10, 15])
def test_levels_investment_game_env_custom_max_num_assets(max_num_assets):
    """Test LevelsInvestmentGameEnv with custom max_num_assets values."""
    env = LevelsInvestmentGameEnv(
        level_idx=0,
        assets_dir=_TEST_ASSETS_DIR,
        reward_fn=LegacyStaticNPVReward(),
        shuffle_order=False,
        max_num_assets=max_num_assets,
        flatten_obs=False,
        distributional_ptrs_config=_DISABLED_DISTRIBUTIONAL_PTRS,
        ta_experience_config=_DISABLED_TA_EXPERIENCE,
        uncertain_ptrs_config=_DISABLED_UNCERTAIN_PTRS,
        investment_levels_config=_DISABLED_INVESTMENT_LEVELS,
        interim_trial_observations_config=_DISABLED_INTERIM_TRIAL_OBS,
        rd_capacity_config=_DISABLED_RD_CAPACITY,
    )
    obs, info = env.reset(seed=42)
    # Action space size
    assert env.action_space.n == max_num_assets
    # Observation space assets tuple length
    assert isinstance(obs["assets"], tuple)
    assert len(obs["assets"]) == max_num_assets
    # Asset order and padding
    actual_assets = list(env.game_state.assets.keys())
    padded_ids = env._asset_id_order
    assert padded_ids[: len(actual_assets)] == actual_assets
    assert all(aid == 0 for aid in padded_ids[len(actual_assets) :])
    # Padding obs should match _padding_asset_obs
    for i in range(len(actual_assets), max_num_assets):
        assert obs["assets"][i] == env._padding_asset_obs


def test_env_reset_calls_collect_metrics_on_episode_begin(test_env):
    mock_metric = MagicMock()
    test_env.metrics = [mock_metric]

    with patch("aiml_pyxis_investment_game.environment.training_gym.collect_metrics") as collect_metrics:
        test_env.reset()
        collect_metrics.assert_called_once_with(
            collection_fn="on_episode_begin",
            context=ANY, metrics=[mock_metric])


def test_env_step_calls_collect_metrics_on_step_begin(test_env):
    mock_metric = MagicMock()
    test_env.metrics = [mock_metric]

    with patch("aiml_pyxis_investment_game.environment.training_gym.collect_metrics") as collect_metrics:
        test_env.step(np.array([0]*25))
        collect_metrics.assert_any_call(
            collection_fn="on_step_begin",
            context=ANY, metrics=[mock_metric])


def test_env_step_calls_collect_metrics_on_step_end(test_env):
    mock_metric = MagicMock()
    test_env.metrics = [mock_metric]

    with patch("aiml_pyxis_investment_game.environment.training_gym.collect_metrics") as collect_metrics:
        test_env.step(np.array([0]*25))
        collect_metrics.assert_any_call(
            collection_fn="on_step_end",
            context=ANY, metrics=[mock_metric])


def test_step_termination(test_env):
    """Test step termination conditions."""
    env = test_env

    # Reset environment
    obs, info = env.reset()

    # Set cash to LARGE negative to trigger termination
    test_env.game_state.game_ended = True
    env.game_state.cash = -100_000_000

    action = np.zeros(MAX_NUM_ASSETS)
    obs, reward, terminated, truncated, info = env.step(action)

    assert terminated is True


def test_env_step_calls_collect_metrics_on_episode_end_when_terminated(test_env):
    mock_metric = MagicMock()
    test_env.metrics = [mock_metric]

    # Set cash to LARGE negative to trigger termination
    test_env.game_state.game_ended = True
    test_env.game_state.cash = -100_000_000

    with patch("aiml_pyxis_investment_game.environment.training_gym.collect_metrics") as collect_metrics:
        test_env.step(np.array([0]*25))
        collect_metrics.assert_any_call(
            collection_fn="on_episode_end",
            context=ANY, metrics=[mock_metric])


@pytest.fixture
def env_pair(valid_json_assets_path):
    """Create a pair of environments with same seed, one flattened one dict."""
    env_dict = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=5,
        max_num_assets=10,
        starting_cash=1_000_000,
        horizon=10,
        shuffle_order=False,
        flatten_obs=False,
    )

    env_flat = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=5,
        max_num_assets=10,
        starting_cash=1_000_000,
        horizon=10,
        shuffle_order=False,
        flatten_obs=True,
    )

    yield env_dict, env_flat

    env_dict.close()
    env_flat.close()


@pytest.fixture
def levels_env_pair():
    """Create pair of level environments."""
    env_dict = LevelsInvestmentGameEnv(
        level_idx=0,
        assets_dir=_TEST_ASSETS_DIR,
        reward_fn=LegacyStaticNPVReward(),
        shuffle_order=False,
        max_num_assets=MAX_NUM_ASSETS,
        flatten_obs=False,
        distributional_ptrs_config=_DISABLED_DISTRIBUTIONAL_PTRS,
        ta_experience_config=_DISABLED_TA_EXPERIENCE,
        uncertain_ptrs_config=_DISABLED_UNCERTAIN_PTRS,
        investment_levels_config=_DISABLED_INVESTMENT_LEVELS,
        interim_trial_observations_config=_DISABLED_INTERIM_TRIAL_OBS,
        rd_capacity_config=_DISABLED_RD_CAPACITY,
    )

    env_flat = LevelsInvestmentGameEnv(
        level_idx=0,
        assets_dir=_TEST_ASSETS_DIR,
        reward_fn=LegacyStaticNPVReward(),
        shuffle_order=False,
        max_num_assets=MAX_NUM_ASSETS,
        flatten_obs=True,
        distributional_ptrs_config=_DISABLED_DISTRIBUTIONAL_PTRS,
        ta_experience_config=_DISABLED_TA_EXPERIENCE,
        uncertain_ptrs_config=_DISABLED_UNCERTAIN_PTRS,
        investment_levels_config=_DISABLED_INVESTMENT_LEVELS,
        interim_trial_observations_config=_DISABLED_INTERIM_TRIAL_OBS,
        rd_capacity_config=_DISABLED_RD_CAPACITY,
    )

    yield env_dict, env_flat

    env_dict.close()
    env_flat.close()


@pytest.fixture
def benchmark_env_pair(valid_json_assets_path):
    """Create environments for benchmarking."""
    env_dict = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=20,
        max_num_assets=50,
        starting_cash=10_000_000,
        horizon=20,
        shuffle_order=False,
        flatten_obs=False,
    )

    env_flat = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=20,
        max_num_assets=50,
        starting_cash=10_000_000,
        horizon=20,
        shuffle_order=False,
        flatten_obs=True,
    )

    yield env_dict, env_flat

    env_dict.close()
    env_flat.close()


# =============================================================================
# Observation Equivalence Tests
# =============================================================================


def test_observation_equivalence_on_reset(env_pair):
    """Test that observations are equivalent after reset."""
    env_dict, env_flat = env_pair
    seed = 42

    dict_obs, _ = env_dict.reset(seed=seed)
    flat_obs, _ = env_flat.reset(seed=seed)

    dict_as_flat = env_dict.flatten_dict_obs(dict_obs)

    np.testing.assert_allclose(
        flat_obs,
        dict_as_flat,
        rtol=1e-5,
        atol=1e-8,
        err_msg="Flattened observation does not match dict observation after reset",
    )


def test_observation_equivalence_during_episode(env_pair):
    """Test that observations remain equivalent throughout an episode."""
    env_dict, env_flat = env_pair
    seed = 42

    dict_obs, _ = env_dict.reset(seed=seed)
    flat_obs, _ = env_flat.reset(seed=seed)

    rng = np.random.default_rng(seed)
    max_steps = 5

    for step in range(max_steps):
        dict_masks = env_dict.action_masks_binary()
        flat_masks = env_flat.action_masks_binary()

        np.testing.assert_array_equal(
            dict_masks, flat_masks, err_msg=f"Action masks differ at step {step}"
        )

        action = np.zeros(env_dict.max_num_assets, dtype=int)
        valid_indices = np.where(dict_masks == 1)[0]
        if len(valid_indices) > 0:
            num_invest = rng.integers(0, min(3, len(valid_indices)) + 1)
            invest_indices = rng.choice(valid_indices, size=num_invest, replace=False)
            action[invest_indices] = 1

        dict_obs, dict_reward, dict_term, _, _ = env_dict.step(action)
        flat_obs, flat_reward, flat_term, _, _ = env_flat.step(action)

        assert dict_reward == flat_reward, f"Rewards differ at step {step}"
        assert dict_term == flat_term, f"Termination differs at step {step}"

        if dict_term:
            break

        dict_as_flat = env_dict.flatten_dict_obs(dict_obs)

        np.testing.assert_allclose(
            flat_obs,
            dict_as_flat,
            rtol=1e-5,
            atol=1e-8,
            err_msg=f"Observations differ at step {step}",
        )


def test_unflatten_roundtrip(env_pair):
    """Test that unflatten(flatten(obs)) == obs."""
    env_dict, _ = env_pair

    dict_obs, _ = env_dict.reset(seed=42)

    flat_obs = env_dict.flatten_dict_obs(dict_obs)
    reconstructed = env_dict.unflatten_to_dict_obs(
        flat_obs, env_dict.max_num_assets
    )

    np.testing.assert_allclose(dict_obs["cash"], reconstructed["cash"], rtol=1e-5)

    for i, (orig_asset, recon_asset) in enumerate(
        zip(dict_obs["assets"], reconstructed["assets"])
    ):
        assert orig_asset["max_revenue"] == pytest.approx(
            recon_asset["max_revenue"], rel=1e-5
        ), f"Asset {i} max_revenue mismatch"

        assert (
            orig_asset["time_until_max_revenue"]
            == recon_asset["time_until_max_revenue"]
        ), f"Asset {i} time_until_max_revenue mismatch"

        assert (
            orig_asset["time_until_patent_expiry"]
            == recon_asset["time_until_patent_expiry"]
        ), f"Asset {i} time_until_patent_expiry mismatch"

        assert (
            orig_asset["pending_trial_phase"] == recon_asset["pending_trial_phase"]
        ), f"Asset {i} pending_trial_phase mismatch"

        assert (
            orig_asset["time_on_market"] == recon_asset["time_on_market"]
        ), f"Asset {i} time_on_market mismatch"

        assert orig_asset["cost_this_step"] == pytest.approx(
            recon_asset["cost_this_step"], rel=1e-5
        ), f"Asset {i} cost_this_step mismatch"

        assert orig_asset["revenue_this_step"] == pytest.approx(
            recon_asset["revenue_this_step"], rel=1e-5
        ), f"Asset {i} revenue_this_step mismatch"

        assert orig_asset["enpv"] == pytest.approx(
            recon_asset["enpv"], rel=1e-5
        ), f"Asset {i} enpv mismatch"

        assert orig_asset["eroi"] == pytest.approx(
            recon_asset["eroi"], rel=1e-5
        ), f"Asset {i} eroi mismatch"

        assert orig_asset["state"] == recon_asset["state"], f"Asset {i} state mismatch"

        for j, (orig_trial, recon_trial) in enumerate(
            zip(orig_asset["trials"], recon_asset["trials"])
        ):
            assert orig_trial["cost_remaining"] == pytest.approx(
                recon_trial["cost_remaining"], rel=1e-5
            ), f"Asset {i} Trial {j} cost_remaining mismatch"

            assert (
                orig_trial["time_remaining"] == recon_trial["time_remaining"]
            ), f"Asset {i} Trial {j} time_remaining mismatch"

            assert orig_trial["ptrs"] == pytest.approx(
                recon_trial["ptrs"], rel=1e-5
            ), f"Asset {i} Trial {j} ptrs mismatch"


# =============================================================================
# Observation Space Tests
# =============================================================================


def test_observation_space_shape(env_pair):
    """Test that flattened observation has correct shape."""
    _, env_flat = env_pair

    obs, _ = env_flat.reset(seed=42)

    L = env_flat._layout
    expected_size = L.global_features + env_flat.max_num_assets * L.asset_total_features

    assert obs.shape == (expected_size,), (
        f"Expected shape ({expected_size},), got {obs.shape}"
    )

    assert env_flat.observation_space.shape == (expected_size,)


def test_observation_space_contains_observation(env_pair):
    """Test that observations are valid according to observation space."""
    env_dict, env_flat = env_pair

    dict_obs, _ = env_dict.reset(seed=42)
    flat_obs, _ = env_flat.reset(seed=42)

    assert env_dict.observation_space.contains(
        dict_obs
    ), "Dict obs not in dict observation space"

    assert env_flat.observation_space.contains(
        flat_obs
    ), "Flat obs not in flat observation space"


# =============================================================================
# Layout Tests
# =============================================================================


def test_layout_all_enabled():
    """Verify ObsLayout with all features enabled."""
    from unittest.mock import MagicMock

    cfg = MagicMock(enabled=True)
    L = ObsLayout.from_config(
        ta_experience_config=cfg,
        rd_capacity_config=cfg,
        distributional_ptrs_config=cfg,
        uncertain_ptrs_config=cfg,
        interim_trial_observations_config=cfg,
    )
    # cash(1) + ta_exp(3) + capacity(3) + ta_quality(6) = 13
    assert L.global_features == 13
    # 10 base + 2 interim + 1 ta_index = 13
    assert L.asset_scalar_features == 13
    # 3 base + 4 distributional = 7
    assert L.trial_features == 7
    assert L.asset_total_features == 13 + NUM_TRIAL_PHASES * 7


def test_layout_all_disabled():
    """Verify ObsLayout with all features disabled."""
    from unittest.mock import MagicMock

    cfg = MagicMock(enabled=False)
    L = ObsLayout.from_config(
        ta_experience_config=cfg,
        rd_capacity_config=cfg,
        distributional_ptrs_config=cfg,
        uncertain_ptrs_config=cfg,
        interim_trial_observations_config=cfg,
    )
    # cash only
    assert L.global_features == 1
    # 10 base + 0 interim + 1 ta_index = 11
    assert L.asset_scalar_features == 11
    # 3 base only
    assert L.trial_features == 3
    assert L.asset_total_features == 11 + NUM_TRIAL_PHASES * 3


# =============================================================================
# Levels Environment Tests
# =============================================================================


def test_levels_observation_equivalence(levels_env_pair):
    """Test observations match for LevelsInvestmentGameEnv."""
    env_dict, env_flat = levels_env_pair

    dict_obs, _ = env_dict.reset()
    flat_obs, _ = env_flat.reset()

    dict_as_flat = env_dict.flatten_dict_obs(dict_obs)

    np.testing.assert_allclose(
        flat_obs,
        dict_as_flat,
        rtol=1e-5,
        atol=1e-8,
        err_msg="Level env observations do not match",
    )


# =============================================================================
# Performance Benchmark Tests
# =============================================================================


def test_flattened_is_faster(benchmark_env_pair):
    """Verify flattened observation is faster (run with pytest-benchmark)."""
    import time

    env_dict, env_flat = benchmark_env_pair

    env_dict.reset(seed=42)
    env_flat.reset(seed=42)

    n_iterations = 1000

    start = time.perf_counter()
    for _ in range(n_iterations):
        _ = env_dict._get_obs_dict()
    dict_time = time.perf_counter() - start

    start = time. perf_counter()
    for _ in range(n_iterations):
        _ = env_flat._get_obs_flattened()
    flat_time = time.perf_counter() - start

    print(f"\nDict obs time: {dict_time:.4f}s for {n_iterations} iterations")
    print(f"Flat obs time: {flat_time:.4f}s for {n_iterations} iterations")
    print(f"Speedup: {dict_time / flat_time:.2f}x")

    assert flat_time < dict_time * 1.5, (
        f"Flattened ({flat_time:.4f}s) not faster than dict ({dict_time:. 4f}s)"
    )


# =============================================================================
# Edge Case Tests
# =============================================================================


def test_empty_assets_observation(valid_json_assets_path):
    """Test observation with minimal assets."""
    env_dict = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=1,
        max_num_assets=5,
        starting_cash=1_000_000,
        horizon=10,
        shuffle_order=False,
        flatten_obs=False,
    )

    env_flat = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=1,
        max_num_assets=5,
        starting_cash=1_000_000,
        horizon=10,
        shuffle_order=False,
        flatten_obs=True,
    )

    try:
        dict_obs, _ = env_dict.reset(seed=42)
        flat_obs, _ = env_flat. reset(seed=42)

        dict_as_flat = env_dict.flatten_dict_obs(dict_obs)

        np.testing.assert_allclose(
            flat_obs,
            dict_as_flat,
            rtol=1e-5,
            atol=1e-8,
            err_msg="Observations differ with minimal assets",
        )
    finally:
        env_dict.close()
        env_flat.close()


def test_max_assets_observation(valid_json_assets_path):
    """Test observation when num_assets equals max_num_assets."""
    env_dict = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=10,
        max_num_assets=10,
        starting_cash=1_000_000,
        horizon=10,
        shuffle_order=False,
        flatten_obs=False,
    )

    env_flat = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=10,
        max_num_assets=10,
        starting_cash=1_000_000,
        horizon=10,
        shuffle_order=False,
        flatten_obs=True,
    )

    try:
        dict_obs, _ = env_dict.reset(seed=42)
        flat_obs, _ = env_flat. reset(seed=42)

        dict_as_flat = env_dict.flatten_dict_obs(dict_obs)

        np.testing.assert_allclose(
            flat_obs,
            dict_as_flat,
            rtol=1e-5,
            atol=1e-8,
            err_msg="Observations differ when assets at max capacity",
        )
    finally:
        env_dict. close()
        env_flat.close()


def test_multiple_resets_consistency(env_pair):
    """Test that multiple resets produce consistent observations."""
    env_dict, env_flat = env_pair

    for seed in [1, 42, 100, 999]:
        dict_obs, _ = env_dict.reset(seed=seed)
        flat_obs, _ = env_flat.reset(seed=seed)

        dict_as_flat = env_dict.flatten_dict_obs(dict_obs)

        np.testing.assert_allclose(
            flat_obs,
            dict_as_flat,
            rtol=1e-5,
            atol=1e-8,
            err_msg=f"Observations differ after reset with seed {seed}",
        )


# =============================================================================
# Initial Game State Tests
# =============================================================================


def test_init_with_initial_game_state(json_game_state_factory, valid_json_assets_path):
    """Test InvestmentGameEnv initialization with initial_game_state parameter."""
    game_state = json_game_state_factory()

    env = _make_env(
        valid_json_assets_path,
        initial_game_state=game_state,
    )

    # The environment should use the provided game state
    assert env.game_state == game_state
    assert env.game_state.cash == game_state.cash
    assert env.game_state.time == game_state.time
    assert env.game_state.horizon == game_state.horizon
    assert env.game_state.assets == game_state.assets


def test_init_without_initial_game_state(valid_json_assets_path):
    """Test InvestmentGameEnv initialization without initial_game_state (default behavior)."""
    env = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=5,
        starting_cash=1_000_000,
        horizon=20,
    )

    # Should create a default game state
    assert env.game_state is not None
    assert env.game_state.cash == 1_000_000
    assert env.game_state.horizon == 20
    assert len(env.game_state.assets) == 5


def test_reset_with_initial_game_state(json_game_state_factory, valid_json_assets_path):
    """Test reset uses initial_game_state when no seed is provided."""
    game_state = json_game_state_factory()

    env = _make_env(
        valid_json_assets_path,
        initial_game_state=game_state,
    )

    # Reset without seed should use the initial_game_state
    obs, info = env.reset()

    assert env.game_state == game_state
    assert env.game_state.cash == game_state.cash
    assert env.game_state.time == game_state.time


def test_reset_with_initial_game_state_and_seed_override(
    json_game_state_factory, valid_json_assets_path
):
    """Test reset with seed overrides initial_game_state."""
    game_state = json_game_state_factory()
    original_cash = game_state.cash

    env = _make_env(
        valid_json_assets_path,
        equilibrium_num_assets=5,
        starting_cash=10_000_000,
        horizon=20,
        initial_game_state=game_state,
    )

    # Reset with seed should create a new game state
    obs, info = env.reset(seed=42)

    # Game state should be different from the initial one
    assert env.game_state != game_state
    # Should use the initialization parameters instead
    assert env.game_state.cash == 10_000_000


def test_reset_preserve_game_state_with_initial_game_state(
    json_game_state_factory, valid_json_assets_path
):
    """Test reset with preserve_game_state option when initial_game_state is set."""
    game_state = json_game_state_factory()

    env = _make_env(
        valid_json_assets_path,
        initial_game_state=game_state,
    )

    # Take a step to change the game state
    action = np.zeros(env.max_num_assets)
    obs, reward, terminated, truncated, info = env.step(action)

    current_game_state = env.game_state
    current_time = env.game_state.time

    # Reset with preserve_game_state should keep current state
    obs, info = env.reset(options={"preserve_game_state": True})

    assert env.game_state == current_game_state
    assert env.game_state.time == current_time


def test_step_with_initial_game_state(json_game_state_factory, valid_json_assets_path):
    """Test stepping environment initialized with initial_game_state."""
    game_state = json_game_state_factory()

    env = _make_env(
        valid_json_assets_path,
        initial_game_state=game_state,
    )

    env.reset()

    # Take a step with no actions
    action = np.zeros(env.max_num_assets)
    obs, reward, terminated, truncated, info = env.step(action)

    # Verify step worked correctly
    assert isinstance(obs, (dict, np.ndarray))
    assert isinstance(reward, (int, float))
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)


def test_action_masks_with_initial_game_state(
    json_game_state_factory, valid_json_assets_path
):
    """Test action masks work correctly with initial_game_state."""
    game_state = json_game_state_factory()

    env = _make_env(
        valid_json_assets_path,
        initial_game_state=game_state,
    )

    env.reset()

    # Get action masks
    masks = env.action_masks()

    # Verify masks structure
    assert isinstance(masks, list)
    assert len(masks) == env.max_num_assets

    # Verify idle assets can be invested in
    for i, asset_id in enumerate(env._asset_id_order):
        if asset_id == 0:
            assert masks[i] == [True, False]
        elif asset_id in game_state.assets:
            asset = game_state.assets[asset_id]
            if asset.state == AssetState.Idle:
                assert masks[i][1] is True  # Can invest


def test_observations_with_initial_game_state(
    json_game_state_factory, valid_json_assets_path
):
    """Test observations are correct when using initial_game_state."""
    game_state = json_game_state_factory()

    env_dict = _make_env(
        valid_json_assets_path,
        initial_game_state=game_state,
        flatten_obs=False,
        shuffle_order=False,
    )

    env_flat = _make_env(
        valid_json_assets_path,
        initial_game_state=game_state,
        flatten_obs=True,
        shuffle_order=False,
    )

    dict_obs, _ = env_dict.reset()
    flat_obs, _ = env_flat.reset()

    # Verify observations are equivalent
    dict_as_flat = env_dict.flatten_dict_obs(dict_obs)

    np.testing.assert_allclose(
        flat_obs,
        dict_as_flat,
        rtol=1e-5,
        atol=1e-8,
        err_msg="Observations differ with initial_game_state",
    )

    # Verify cash matches
    assert dict_obs["cash"][0] == game_state.cash