"""Tests for multi-agent competitive investment game environment."""

from types import SimpleNamespace

import gymnasium as gym
import numpy as np
import pytest
import upath

from aiml_pyxis_investment_game.config import (
    ApprovalPhaseConfig,
    CapacityConfig,
    DistributionalPtrsConfig,
    InterimTrialObservationsConfig,
    InvestmentLevelParams,
    InvestmentLevelsConfig,
    PricingConfig,
    TAExperienceConfig,
    UncertainPtrsConfig,
)
from aiml_pyxis_investment_game.environment.market_mechanics import (
    calculate_agent_market_shares,
)
from aiml_pyxis_investment_game.environment.multi_agent_reward import (
    AbsolutePerformanceReward,
    RelativeRankReward,
    ZeroSumReward,
    create_reward_function,
)
from aiml_pyxis_investment_game.environment.multi_agent_training_gym import (
    _ALERT_FEATURES,
    _BD_OBS_FEATURES_PER_SLOT,
    _INDICATION_FEATURES,
    MultiAgentInvestmentGameEnv,
)
from aiml_pyxis_investment_game.environment.reward import NetCashFlowReward
from aiml_pyxis_investment_game.game.shared_market_state import (
    THERAPEUTIC_AREAS,
    AlertType,
    SharedMarketState,
)

TEST_ASSETS_DIR = upath.UPath("tests/data/generated_assets")


def _make_env(
    num_agents=2,
    equilibrium_num_assets=5,
    max_num_assets=15,
    horizon=10,
    **kwargs,
):
    """Helper to create a multi-agent env with sensible defaults for testing."""
    defaults = dict(
        assets_dir=TEST_ASSETS_DIR,
        num_agents=num_agents,
        starting_cash=10_000_000.0,
        max_num_assets=max_num_assets,
        horizon=horizon,
        equilibrium_num_assets=equilibrium_num_assets,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        bd_enabled=False,
        bd_assets_dir=TEST_ASSETS_DIR,
        bd_base_lambda=0.3,
        bd_leak_lambda_boost=0.3,
        bd_min_step=5,
        bd_num_bid_levels=11,
        bd_break_even_bid_level=7,
        bd_max_slots=1,
        bd_phase_weights=[0.2, 0.4, 0.4],
        bd_indication_activity_bias=0.8,
        exclusivity_period=4,
        first_mover_bonus=0.30,
        disable_market_share_competition=False,
        alert_history_length=5,
        leak_phase_probabilities=[0.2, 0.5, 0.7],
        alerts_per_agent=5,
        reward_fn=NetCashFlowReward(),
        reward_type="absolute",
        reward_scale=1.0,
        shuffle_order=False,
        mask_first_order_assets=False,
        mask_negative_enpv_assets=False,
        flatten_obs=True,
        distributional_ptrs_config=DistributionalPtrsConfig(
            enabled=False,
            ta_quality_variance={"oncology": 0.08, "respiratory and immunology": 0.05, "vaccines and infectious disease": 0.03},
            asset_noise_std=0.03,
            prior_concentration=5.0,
            observation_noise=0.1,
        ),
        ta_experience_config=TAExperienceConfig(
            enabled=False,
            experience_to_full_knowledge=30.0,
            max_expertise_boost=0.05,
            experience_to_max_boost=40.0,
            experience_decay_rate=0.98,
            max_total_experience=60.0,
            phase_experience_weights={"phase_1": 0.5, "phase_2": 1.0, "phase_3": 1.5, "approval": 0.5},
            asset_arrival_temperature=0.1,
        ),
        uncertain_ptrs_config=UncertainPtrsConfig(
            enabled=False,
            ta_noise_config={"oncology": 0.12, "respiratory and immunology": 0.10, "vaccines and infectious disease": 0.08},
            phase_noise_multipliers={"phase_1": 1.5, "phase_2": 1.0, "phase_3": 0.75, "approval": 0.5},
        ),
        investment_levels_config=InvestmentLevelsConfig(
            enabled=False,
            levels={
                "none": InvestmentLevelParams(cost_modifier=0.0, speed_modifier=0.0, success_modifier=1.0, capacity_cost=0, experience_modifier=0.0),
                "standard": InvestmentLevelParams(cost_modifier=1.0, speed_modifier=1.0, success_modifier=1.0, capacity_cost=2, experience_modifier=1.0),
            },
        ),
        interim_trial_observations_config=InterimTrialObservationsConfig(
            enabled=False,
            latent_quality_concentration=10.0,
            initial_noise_scale=0.3,
        ),
        rd_capacity_config=CapacityConfig(
            enabled=False,
            base_capacity=80.0,
            overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5,
            overage_scaling="linear",
        ),
        approval_phase_config=ApprovalPhaseConfig(
            enabled=False, duration_min=1, duration_max=3,
            success_rate_min=0.85, success_rate_max=0.95, cost=50_000_000,
        ),
        max_indications_per_ta=7,
        target_drugs_per_indication=2.0,
        on_market_fraction=0.25,
        indication_spread=1.5,
        indication_drift_speed=1.0,
        trial_cost_multiplier=1.0,
        congestion_exponent=1.0,
        congestion_ramp_steps=3,
        congestion_incumbent_penalty=0.0,
        pricing_config=PricingConfig(
            enabled=False,
            levels=[0.60, 0.75, 1.00, 1.20, 1.40, 1.60],
            default_level=2,
            elasticity=2.0,
        ),
    )
    defaults.update(kwargs)
    return MultiAgentInvestmentGameEnv(**defaults)


class TestMultiAgentEnvInit:
    def test_creates_env_with_correct_agents(self):
        env = _make_env(num_agents=3)
        assert env.possible_agents == ["pharma_0", "pharma_1", "pharma_2"]

    def test_obs_size_calculation(self):
        env = _make_env(num_agents=2, max_num_assets=15)
        layout = env._layout
        max_indications_per_ta = env.max_indications_per_ta
        expected = (
            layout.global_features
            + 15 * layout.asset_total_features
            + 1 * _BD_OBS_FEATURES_PER_SLOT
            + len(THERAPEUTIC_AREAS) * max_indications_per_ta * _INDICATION_FEATURES
            + 5 * _ALERT_FEATURES
        )
        assert env._obs_size == expected


class TestMultiAgentEnvReset:
    def test_reset_returns_observations_and_infos(self):
        env = _make_env()
        observations, infos = env.reset(seed=42)

        assert set(observations.keys()) == set(env.possible_agents)
        assert set(infos.keys()) == set(env.possible_agents)

    def test_reset_creates_agent_states(self):
        env = _make_env(num_agents=2, equilibrium_num_assets=5)
        env.reset(seed=42)

        assert len(env.agent_portfolios) == 2
        for agent_id, game_state in env.agent_portfolios.items():
            assert game_state.cash == 10_000_000.0
            assert len(game_state.assets) == 5

    def test_reset_deterministic_with_seed(self):
        env = _make_env()
        obs1, _ = env.reset(seed=42)
        obs2, _ = env.reset(seed=42)

        for agent in env.possible_agents:
            np.testing.assert_array_equal(obs1[agent], obs2[agent])

    def test_observation_shape(self):
        env = _make_env()
        observations, _ = env.reset(seed=42)

        for agent in env.possible_agents:
            obs = observations[agent]
            assert obs.shape == (env._obs_size,)
            assert obs.dtype == np.float32


class TestMultiAgentEnvStep:
    def test_step_with_do_nothing_actions(self):
        env = _make_env()
        env.reset(seed=42)

        # Do-nothing actions
        actions = {}
        for agent in env.agents:
            actions[agent] = {
                "investments": np.zeros(env.max_num_assets, dtype=np.int8),
                "bd_bids": np.zeros(env.bd_max_slots, dtype=np.int64),
            }

        obs, rewards, terms, truncs, infos = env.step(actions)

        assert set(obs.keys()) == set(env.possible_agents)
        assert set(rewards.keys()) == set(env.possible_agents)
        assert env.time == 1

    def test_step_with_legacy_multibinary_actions(self):
        """Test backward compat with plain array actions (investments only)."""
        env = _make_env()
        env.reset(seed=42)

        actions = {
            agent: np.zeros(env.max_num_assets, dtype=np.int8)
            for agent in env.agents
        }

        obs, rewards, terms, truncs, infos = env.step(actions)
        assert env.time == 1

    def test_full_episode(self):
        env = _make_env(horizon=5)
        env.reset(seed=42)

        for step in range(5):
            actions = {
                agent: np.zeros(env.max_num_assets, dtype=np.int8)
                for agent in env.agents
            }
            obs, rewards, terms, truncs, infos = env.step(actions)

        # After horizon steps, should be terminated
        assert all(terms.values())

    def test_investment_actions_work(self):
        env = _make_env()
        env.reset(seed=42)

        # Find an agent with idle assets and invest
        agent = env.agents[0]
        masks = env.action_masks(agent)
        invest_mask = masks["investments"]

        # Create action investing in first available idle asset
        action = np.zeros(env.max_num_assets, dtype=np.int8)
        idle_indices = np.where(invest_mask == 1)[0]
        if len(idle_indices) > 0:
            action[idle_indices[0]] = 1

        actions = {a: np.zeros(env.max_num_assets, dtype=np.int8) for a in env.agents}
        actions[agent] = action

        pre_cash = env.agent_portfolios[agent].cash
        env.step(actions)
        post_cash = env.agent_portfolios[agent].cash

        # Cash should decrease if we invested
        if len(idle_indices) > 0:
            assert post_cash <= pre_cash


class TestActionMasks:
    def test_action_masks_structure(self):
        env = _make_env()
        env.reset(seed=42)

        for agent in env.agents:
            masks = env.action_masks(agent)
            assert "investments" in masks
            assert "bd_bids" in masks
            assert len(masks["investments"]) == env.max_num_assets
            assert len(masks["bd_bids"]) == env.bd_max_slots

    def test_only_idle_assets_investable(self):
        env = _make_env()
        env.reset(seed=42)

        for agent in env.agents:
            masks = env.action_masks(agent)
            game_state = env.agent_portfolios[agent]
            asset_order = env._asset_id_orders[agent]

            for i, asset_id in enumerate(asset_order):
                if asset_id is not None and asset_id in game_state.assets:
                    asset = game_state.assets[asset_id]
                    from aiml_pyxis_investment_game.game.asset import AssetState

                    if asset.state == AssetState.Idle:
                        assert masks["investments"][i] == 1
                    else:
                        assert masks["investments"][i] == 0


class TestRewardFunctions:
    def _make_portfolios(self):
        """Create mock portfolio-like objects with bankrupt attribute."""
        p1 = SimpleNamespace(bankrupt=False)
        p2 = SimpleNamespace(bankrupt=False)
        return {"a": p1, "b": p2}

    def test_absolute_reward(self):
        reward_fn = AbsolutePerformanceReward(scale_factor=1.0)
        portfolios = self._make_portfolios()
        pre = {"a": 100.0, "b": 100.0}
        post = {"a": 150.0, "b": 80.0}
        rewards = reward_fn.compute("", pre, post, portfolios)

        assert rewards["a"] == pytest.approx(50.0)
        assert rewards["b"] == pytest.approx(-20.0)

    def test_relative_rank_reward(self):
        reward_fn = RelativeRankReward(first_place=1.0, decay_factor=0.5)
        portfolios = self._make_portfolios()
        pre = {"a": 100.0, "b": 100.0}
        post = {"a": 150.0, "b": 80.0}
        rewards = reward_fn.compute("", pre, post, portfolios)

        assert rewards["a"] == pytest.approx(1.0)  # 1st place
        assert rewards["b"] == pytest.approx(0.5)  # 2nd place

    def test_zero_sum_reward(self):
        reward_fn = ZeroSumReward(scale_factor=1.0)
        portfolios = self._make_portfolios()
        pre = {"a": 100.0, "b": 100.0}
        post = {"a": 150.0, "b": 80.0}
        rewards = reward_fn.compute("", pre, post, portfolios)

        # a gets +50, b gets -20. Mean of other: a sees -20, b sees +50
        assert rewards["a"] == pytest.approx(50.0 - (-20.0))  # 70
        assert rewards["b"] == pytest.approx(-20.0 - 50.0)  # -70

    def test_create_reward_function_factory(self):
        rf = create_reward_function("absolute", scale_factor=2.0)
        assert isinstance(rf, AbsolutePerformanceReward)
        assert rf.scale_factor == 2.0

    def test_bankrupt_agent_gets_penalty(self):
        reward_fn = AbsolutePerformanceReward()
        portfolios = self._make_portfolios()
        portfolios["a"].bankrupt = True
        pre = {"a": 100.0, "b": 100.0}
        post = {"a": 200.0, "b": 150.0}
        rewards = reward_fn.compute("", pre, post, portfolios)

        assert rewards["a"] == -1.0


_SHARED_MARKET_DEFAULTS = dict(
    exclusivity_period=4,
    first_mover_bonus=0.3,
    alert_history_length=5,
    disable_market_share_competition=False,
    seed=42,
    num_indications_per_ta=0,
    bd_enabled=False,
    bd_base_lambda=0.3,
    bd_leak_lambda_boost=0.3,
    bd_min_step=5,
    bd_num_bid_levels=11,
    bd_break_even_bid_level=7,
    bd_phase_weights=None,
    bd_indication_activity_bias=0.8,
    leak_phase_probabilities=None,
    congestion_exponent=0.0,
    congestion_ramp_steps=1,
    congestion_incumbent_penalty=0.0,
)


class TestSharedMarketState:
    def test_initialize(self):
        state = SharedMarketState.initialize(**_SHARED_MARKET_DEFAULTS)
        assert len(state.ta_markets) == len(THERAPEUTIC_AREAS)

    def test_alerts(self):
        state = SharedMarketState.initialize(**_SHARED_MARKET_DEFAULTS)
        from aiml_pyxis_investment_game.game.shared_market_state import Alert

        alert = Alert(
            step=0,
            event_type=AlertType.DRUG_RELEASE,
            agent_id="pharma_0",
            therapeutic_area="oncology",
        )
        state.add_alert(alert)

        # pharma_0 should not see their own alert
        alerts_for_1 = state.get_alerts_for_agent("pharma_1")
        assert len(alerts_for_1) == 1

        alerts_for_0 = state.get_alerts_for_agent("pharma_0")
        assert len(alerts_for_0) == 0

    def test_exclusivity(self):
        import uuid as _uuid
        state = SharedMarketState.initialize(**_SHARED_MARKET_DEFAULTS)
        ta_market = state.ta_markets["oncology"]

        assert not ta_market.is_in_exclusivity(0)

        ta_market.first_mover_agent = "pharma_0"
        ta_market.first_mover_drug_id = _uuid.uuid4()
        ta_market.exclusivity_start_time = 0

        assert ta_market.is_in_exclusivity(0)
        assert ta_market.is_in_exclusivity(3)
        assert not ta_market.is_in_exclusivity(4)
        assert ta_market.exclusivity_remaining(2) == 2


class TestMeanRevertingAssetArrival:
    def test_assets_arrive_when_below_equilibrium(self):
        """Assets should arrive more frequently when below equilibrium."""
        env = _make_env(
            equilibrium_num_assets=10,
            max_num_assets=15,
            horizon=20,
        )
        env.reset(seed=42)

        initial_counts = {
            agent: len(env.agent_portfolios[agent].assets) for agent in env.agents
        }

        # Run a few steps
        for _ in range(5):
            actions = {
                agent: np.zeros(env.max_num_assets, dtype=np.int8)
                for agent in env.agents
            }
            env.step(actions)

        # Should have more assets now
        for agent in env.agents:
            assert len(env.agent_portfolios[agent].assets) >= initial_counts[agent]


class TestDictObservation:
    """Test dict-based observations and flat↔dict round-trip conversion."""

    def test_dict_obs_returns_dict_with_expected_keys(self):
        env = _make_env(flatten_obs=False)
        observations, _ = env.reset(seed=42)

        for agent in env.possible_agents:
            obs = observations[agent]
            assert isinstance(obs, dict)
            assert "cash" in obs
            assert "time" in obs
            assert "assets" in obs
            assert "bd_market" in obs
            assert "indication_markets" in obs
            assert "alerts" in obs

    def test_dict_obs_asset_structure(self):
        env = _make_env(flatten_obs=False)
        observations, _ = env.reset(seed=42)

        obs = observations["pharma_0"]
        assert len(obs["assets"]) == env.max_num_assets
        asset = obs["assets"][0]
        assert "max_revenue" in asset
        assert "enpv" in asset
        assert "state" in asset
        assert "trials" in asset
        assert "ta_index" in asset
        assert "indication" in asset
        assert len(asset["trials"]) == 4  # P1, P2, P3, Approval

    def test_dict_obs_bd_market_structure(self):
        env = _make_env(flatten_obs=False)
        observations, _ = env.reset(seed=42)

        obs = observations["pharma_0"]
        assert len(obs["bd_market"]) == env.bd_max_slots
        bd = obs["bd_market"][0]
        assert "available" in bd
        assert "enpv" in bd
        assert "ptrs" in bd

    def test_dict_obs_indication_markets_structure(self):
        env = _make_env(flatten_obs=False)
        observations, _ = env.reset(seed=42)

        obs = observations["pharma_0"]
        for ta in THERAPEUTIC_AREAS:
            assert ta in obs["indication_markets"]
            inds = obs["indication_markets"][ta]
            assert len(inds) == env.max_indications_per_ta
            ind = inds[0]
            assert "exclusivity_remaining" in ind
            assert "my_avg_share" in ind
            assert "first_mover" in ind
            assert "my_drugs" in ind
            assert "competitor_drugs" in ind

    def test_dict_obs_alerts_structure(self):
        env = _make_env(flatten_obs=False)
        observations, _ = env.reset(seed=42)

        obs = observations["pharma_0"]
        assert len(obs["alerts"]) == env.max_alerts
        alert = obs["alerts"][0]
        assert "event_type" in alert
        assert "agent_index" in alert
        assert "ta_index" in alert
        assert "age" in alert

    def test_flat_obs_shape_unchanged(self):
        """Ensure flatten_obs=True still works as before."""
        env = _make_env(flatten_obs=True)
        observations, _ = env.reset(seed=42)

        for agent in env.possible_agents:
            obs = observations[agent]
            assert isinstance(obs, np.ndarray)
            assert obs.shape == (env._obs_size,)

    def test_dict_matches_flat_on_reset(self):
        """Dict obs flattened should match flat obs from same seed."""
        env_dict = _make_env(flatten_obs=False)
        env_flat = _make_env(flatten_obs=True)

        dict_obs, _ = env_dict.reset(seed=42)
        flat_obs, _ = env_flat.reset(seed=42)

        for agent in env_dict.possible_agents:
            dict_as_flat = env_dict.flatten_dict_obs(dict_obs[agent])
            np.testing.assert_allclose(
                flat_obs[agent],
                dict_as_flat,
                atol=1e-6,
                err_msg=f"Mismatch for {agent} on reset",
            )

    def test_dict_matches_flat_over_steps(self):
        """Dict↔flat equivalence holds across multiple steps."""
        env_dict = _make_env(flatten_obs=False)
        env_flat = _make_env(flatten_obs=True)

        dict_obs, _ = env_dict.reset(seed=42)
        flat_obs, _ = env_flat.reset(seed=42)

        for step in range(5):
            # Do-nothing actions
            actions = {
                agent: {
                    "investments": np.zeros(
                        env_dict.max_num_assets, dtype=np.int8
                    ),
                    "bd_bids": np.zeros(
                        env_dict.bd_max_slots, dtype=np.int64
                    ),
                }
                for agent in env_dict.agents
            }

            dict_obs, *_ = env_dict.step(actions)
            flat_obs, *_ = env_flat.step(actions)

            for agent in env_dict.possible_agents:
                dict_as_flat = env_dict.flatten_dict_obs(
                    dict_obs[agent]
                )
                np.testing.assert_allclose(
                    flat_obs[agent],
                    dict_as_flat,
                    atol=1e-6,
                    err_msg=(
                        f"Mismatch for {agent} at step {step}"
                    ),
                )

    def test_unflatten_roundtrip(self):
        """Test that unflatten(flatten(obs)) preserves values."""
        env = _make_env(flatten_obs=False)
        observations, _ = env.reset(seed=42)

        for agent in env.possible_agents:
            dict_obs = observations[agent]
            flat_obs = env.flatten_dict_obs(dict_obs)
            reconstructed = env.unflatten_to_dict_obs(flat_obs)

            # Check global features
            np.testing.assert_allclose(
                dict_obs["cash"], reconstructed["cash"], atol=1e-6
            )
            np.testing.assert_allclose(
                dict_obs["time"], reconstructed["time"], atol=1e-6
            )

            # Check per-asset scalar fields (rtol for float32 precision)
            for i in range(len(dict_obs["assets"])):
                orig = dict_obs["assets"][i]
                recon = reconstructed["assets"][i]
                for key in ["state", "ta_index", "indication"]:
                    assert orig[key] == recon[key], (
                        f"Asset {i} key {key} mismatch"
                    )
                for key in ["max_revenue", "enpv", "eroi"]:
                    assert orig[key] == pytest.approx(
                        recon[key], rel=1e-5
                    ), f"Asset {i} key {key} mismatch"

            # Check BD market
            for i in range(len(dict_obs["bd_market"])):
                orig = dict_obs["bd_market"][i]
                recon = reconstructed["bd_market"][i]
                assert orig["available"] == recon["available"]
                for key in ["enpv", "ptrs"]:
                    assert orig[key] == pytest.approx(
                        recon[key], rel=1e-5
                    ), f"BD slot {i} key {key}"

    def test_flatten_then_unflatten_matches_flat(self):
        """Test flatten(unflatten(flat)) == flat."""
        env = _make_env(flatten_obs=True)
        flat_obs_all, _ = env.reset(seed=42)

        for agent in env.possible_agents:
            flat_obs = flat_obs_all[agent]
            dict_obs = env.unflatten_to_dict_obs(flat_obs)
            re_flat = env.flatten_dict_obs(dict_obs)
            np.testing.assert_allclose(
                flat_obs, re_flat, atol=1e-6,
                err_msg=f"Re-flattened mismatch for {agent}",
            )

    def test_observation_space_contains_dict_obs(self):
        """Observation space should contain the dict observation."""
        env = _make_env(flatten_obs=False)
        observations, _ = env.reset(seed=42)

        for agent in env.possible_agents:
            space = env.observation_space(agent)
            assert isinstance(space, gym.spaces.Dict)


class TestDisableMarketShareCompetition:
    def test_disabled_returns_full_share(self):
        env = _make_env(disable_market_share_competition=True)
        env.reset(seed=42)

        shares = calculate_agent_market_shares(
            "pharma_0",
            env.multi_agent_game.shared_market,
            env.agent_portfolios, 0,
        )
        # With competition disabled, all on-market drugs get share 1.0
        for share in shares.values():
            assert share == 1.0
