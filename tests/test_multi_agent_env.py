"""Tests for multi-agent competitive investment game environment."""

from types import SimpleNamespace

import gymnasium as gym
import numpy as np
import pytest
import upath

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
    PricingConfig,
    PtrsReadingsConfig,
    TAExperienceConfig,
    UncertainPtrsConfig,
)
from pyxis_portfolio_challenge.environment.market_mechanics import (
    calculate_agent_market_shares,
)
from pyxis_portfolio_challenge.environment.multi_agent_reward import (
    AbsolutePerformanceReward,
    RelativeRankReward,
    ZeroSumReward,
    create_reward_function,
)
from pyxis_portfolio_challenge.environment.multi_agent_training_gym import (
    _ALERT_FEATURES,
    _BD_OBS_FEATURES_PER_SLOT,
    _INDICATION_FEATURES,
    MultiAgentInvestmentGameEnv,
)
from pyxis_portfolio_challenge.environment.reward import NetCashFlowReward
from pyxis_portfolio_challenge.environment.warmup_wrapper import (
    MultiAgentWarmupOnResetWrapper,
)
from pyxis_portfolio_challenge.game.asset import AssetState
from pyxis_portfolio_challenge.game.constants import InvestmentLevel
from pyxis_portfolio_challenge.game.shared_market_state import (
    THERAPEUTIC_AREAS,
    Alert,
    AlertType,
    SharedMarketState,
)
from pyxis_portfolio_challenge.rng import init_game_rng

TEST_ASSETS_DIR = upath.UPath("tests/data/generated_assets")

# A BD cash bid (in GBP millions) that comfortably wins an uncontested auction
# without exhausting a test agent's cash. BD bids are now raw cash amounts, so
# any positive bid beats a pass; this stays well under the per-agent cash so the
# winner never bankrupts itself acquiring the asset.
_BD_WINNING_BID = 100


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
        bd_max_bid=10000.0,
        bd_max_slots=1,
        bd_phase_weights=[0.2, 0.4, 0.4],
        bd_indication_activity_bias=0.8,
        exclusivity_period=4,
        first_mover_bonus=0.30,
        disable_market_share_competition=False,
        alert_history_length=5,
        leak_phase_probabilities=[0.2, 0.5, 0.7],
        be_leak_probability=0.8,
        dc_leak_probability=0.8,
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
            ta_quality_variance={
                "oncology": 0.08,
                "respiratory and immunology": 0.05,
                "vaccines and infectious disease": 0.03,
            },
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
            phase_experience_weights={
                "phase_1": 0.5,
                "phase_2": 1.0,
                "phase_3": 1.5,
                "approval": 0.5,
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
                "phase_1": 1.5,
                "phase_2": 1.0,
                "phase_3": 0.75,
                "approval": 0.5,
            },
        ),
        investment_levels_config=InvestmentLevelsConfig(
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
            enabled=False,
            duration_min=1,
            duration_max=3,
            success_rate_min=0.85,
            success_rate_max=0.95,
            cost=50_000_000,
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
        drop_action_config=DropActionConfig(
            enabled=False,
            drop_price_fraction=0.0,
            drop_price_rounding=1_000_000,
        ),
        ptrs_readings_config=PtrsReadingsConfig(
            enabled=False,
            cost_fraction=0.05,
            cost_rounding=1_000_000,
            action_space_max_readings=10,
            sigma_logit_base=1.5,
            sigma_ep=None,
            noise_multipliers=[1.0, 1.5, 2.0],
            max_sample_obs=20,
        ),
        marketing_config=_MARKETING_CFG_DISABLED,
        clinical_sites_config=ClinicalSitesConfig(
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
        ),
        bd_persist_steps=1,
        dc_leak_min_agents=3,
        render_mode=None,
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

    def test_bare_array_actions_rejected(self):
        """
        Bare numpy-array actions are rejected under strict parsing.

        The strict parser requires a dict containing every enabled action
        head; passing a plain array (the old backward-compat path) must now
        raise ValueError.
        """
        env = _make_env()
        env.reset(seed=42)

        actions = {
            agent: np.zeros(env.max_num_assets, dtype=np.int8) for agent in env.agents
        }

        with pytest.raises(ValueError):
            env.step(actions)

    def test_full_episode(self):
        env = _make_env(horizon=5)
        env.reset(seed=42)

        for step in range(5):
            actions = {agent: env.noop_action() for agent in env.agents}
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
        action = env.noop_action()
        idle_indices = np.where(invest_mask == 1)[0]
        if len(idle_indices) > 0:
            action["investments"][idle_indices[0]] = 1

        actions = {a: env.noop_action() for a in env.agents}
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
            # BD bids are a continuous Box and are not masked.
            assert "bd_bids" not in masks
            assert len(masks["investments"]) == env.max_num_assets

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
                    from pyxis_portfolio_challenge.game.asset import AssetState

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
    num_indications_per_ta=0,
    bd_enabled=False,
    bd_base_lambda=0.3,
    bd_leak_lambda_boost=0.3,
    bd_min_step=5,
    bd_max_bid=10000.0,
    bd_phase_weights=None,
    bd_indication_activity_bias=0.8,
    leak_phase_probabilities=None,
    congestion_exponent=0.0,
    congestion_ramp_steps=1,
    congestion_incumbent_penalty=0.0,
)


class TestSharedMarketState:
    def test_initialize(self):
        init_game_rng(42)
        state = SharedMarketState.initialize(**_SHARED_MARKET_DEFAULTS)
        assert len(state.ta_markets) == len(THERAPEUTIC_AREAS)

    def test_alerts(self):
        init_game_rng(42)
        state = SharedMarketState.initialize(**_SHARED_MARKET_DEFAULTS)
        from pyxis_portfolio_challenge.game.shared_market_state import Alert

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

    def test_be_spend_leak_fires_when_probable(self):
        """With probability 1.0 the BE-spend leak always emits a BE_SPEND alert."""
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "be_leak_probability": 1.0}
        )
        state.generate_be_spend_leak("pharma_0", "oncology", indication=2)

        alerts = state.get_alerts_for_agent("pharma_1")
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.event_type == AlertType.BE_SPEND
        assert alert.agent_id == "pharma_0"
        assert alert.therapeutic_area == "oncology"
        assert alert.indication == 2

    def test_be_spend_leak_suppressed_when_improbable(self):
        """With probability 0.0 the BE-spend leak never emits."""
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "be_leak_probability": 0.0}
        )
        state.generate_be_spend_leak("pharma_0", "oncology", indication=2)
        assert len(state.get_alerts_for_agent("pharma_1")) == 0

    def test_be_spend_leak_count_defaults_to_one(self):
        """A single spend (default spend_count) reports be_count == 1."""
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "be_leak_probability": 1.0}
        )
        state.generate_be_spend_leak("pharma_0", "oncology", indication=2)
        assert state.get_alerts_for_agent("pharma_1")[0].details["be_count"] == 1

    def test_be_spend_leak_reports_count_when_all_leak(self):
        """At prob 1.0 every spend leaks: one alert carrying be_count == spends."""
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "be_leak_probability": 1.0}
        )
        state.generate_be_spend_leak(
            "pharma_0", "oncology", indication=2, spend_count=3
        )

        alerts = state.get_alerts_for_agent("pharma_1")
        assert len(alerts) == 1
        assert alerts[0].details["be_count"] == 3

    def test_be_spend_leak_count_is_probabilistic(self):
        """
        Each spend rolls independently, so be_count can fall below the spends.

        Two BE spends can surface as be_count 1 (one roll failed) — or, with
        enough spends at p<1, the leaked count sits strictly between 1 and the
        number of spends. Still exactly one alert per indication.
        """
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "be_leak_probability": 0.5}
        )
        state.generate_be_spend_leak(
            "pharma_0", "oncology", indication=2, spend_count=10
        )

        alerts = state.get_alerts_for_agent("pharma_1")
        assert len(alerts) == 1
        be_count = alerts[0].details["be_count"]
        assert 1 <= be_count < 10  # some but not all of the 10 rolls leaked

    def test_be_spend_leak_all_rolls_fail_no_alert(self):
        """If every per-spend roll fails, no alert is emitted at all."""
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "be_leak_probability": 0.0}
        )
        state.generate_be_spend_leak(
            "pharma_0", "oncology", indication=2, spend_count=5
        )
        assert len(state.get_alerts_for_agent("pharma_1")) == 0

    def test_dc_spend_leak_fires_when_probable(self):
        """With probability 1.0 the DC-spend leak always emits a DC_SPEND alert."""
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "dc_leak_probability": 1.0}
        )
        state.generate_dc_spend_leak("pharma_0", "oncology", indication=1)

        alerts = state.get_alerts_for_agent("pharma_1")
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.event_type == AlertType.DC_SPEND
        assert alert.agent_id == "pharma_0"
        assert alert.therapeutic_area == "oncology"
        assert alert.indication == 1

    def test_dc_spend_leak_suppressed_when_improbable(self):
        """With probability 0.0 the DC-spend leak never emits."""
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "dc_leak_probability": 0.0}
        )
        state.generate_dc_spend_leak("pharma_0", "oncology", indication=1)
        assert len(state.get_alerts_for_agent("pharma_1")) == 0

    def test_exclusivity(self):
        import uuid as _uuid

        init_game_rng(42)
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

    def test_simultaneous_market_entry_voids_exclusivity(self):
        """Two drugs entering the same indication on the same step get no exclusivity."""
        import uuid as _uuid

        from pyxis_portfolio_challenge.game.asset import AssetState, DrugAsset
        from pyxis_portfolio_challenge.game.trial import Trial, TrialPhase, TrialState

        def _on_market_drug(ta: str, ind: int) -> DrugAsset:
            return DrugAsset(
                id=_uuid.uuid4(), name="Drug", therapeutic_area=ta, type="internal",
                description="", max_revenue=1_000_000, raw_max_revenue=1_000_000,
                time_until_max_revenue=5,
                time_until_patent_expiry=19, time_on_market=0,
                trial=Trial(phase=TrialPhase.PHASE_1, state=TrialState.PHASE_SUCCESS,
                            cost_remaining=0, ptrs=1.0, time_remaining=0,
                            next_trial_on_success=None),
                state=AssetState.OnMarket, indication=ind,
            )

        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "num_indications_per_ta": 3}
        )

        state.register_drug_release("pharma_0", _on_market_drug("oncology", 0))
        state.register_drug_release("pharma_1", _on_market_drug("oncology", 0))

        ind_market = state.indication_markets["oncology:0"]
        assert ind_market.first_mover_agent is None, "exclusivity should be voided"
        assert ind_market.first_mover_drug_id is None
        assert ind_market.exclusivity_start_time is None
        assert not ind_market.is_in_exclusivity(state.time + 1)

    def test_single_market_entry_gets_exclusivity(self):
        """A drug entering alone still gets the full exclusivity window."""
        import uuid as _uuid

        from pyxis_portfolio_challenge.game.asset import AssetState, DrugAsset
        from pyxis_portfolio_challenge.game.trial import Trial, TrialPhase, TrialState

        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "num_indications_per_ta": 3}
        )
        drug = DrugAsset(
            id=_uuid.uuid4(), name="Drug-A", therapeutic_area="oncology", type="internal",
            description="", max_revenue=1_000_000, raw_max_revenue=1_000_000,
            time_until_max_revenue=5,
            time_until_patent_expiry=19, time_on_market=0,
            trial=Trial(phase=TrialPhase.PHASE_1, state=TrialState.PHASE_SUCCESS,
                        cost_remaining=0, ptrs=1.0, time_remaining=0,
                        next_trial_on_success=None),
            state=AssetState.OnMarket, indication=0,
        )
        state.register_drug_release("pharma_0", drug)

        ind_market = state.indication_markets["oncology:0"]
        assert ind_market.first_mover_agent == "pharma_0"
        assert ind_market.first_mover_drug_id == drug.id
        assert ind_market.is_in_exclusivity(state.time + 1)


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
            actions = {agent: env.noop_action() for agent in env.agents}
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
        assert "phase" in alert
        assert "bd_price" in alert

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
        # Run sequentially to avoid shared RNG interference between envs
        env_dict = _make_env(flatten_obs=False)
        dict_obs, _ = env_dict.reset(seed=42)

        env_flat = _make_env(flatten_obs=True)
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
        """
        Dict↔flat equivalence holds across multiple steps.

        Run each env independently (reset+step fully) then compare,
        because both envs share the process-wide game RNG.
        """
        num_steps = 5

        # Collect dict observations
        env_dict = _make_env(flatten_obs=False)
        dict_obs, _ = env_dict.reset(seed=42)
        dict_obs_history = [dict_obs]
        for _ in range(num_steps):
            actions = {
                agent: {
                    "investments": np.zeros(env_dict.max_num_assets, dtype=np.int8),
                    "bd_bids": np.zeros(env_dict.bd_max_slots, dtype=np.int64),
                }
                for agent in env_dict.agents
            }
            dict_obs, *_ = env_dict.step(actions)
            dict_obs_history.append(dict_obs)

        # Collect flat observations with same seed and actions
        env_flat = _make_env(flatten_obs=True)
        flat_obs, _ = env_flat.reset(seed=42)
        flat_obs_history = [flat_obs]
        for _ in range(num_steps):
            actions = {
                agent: {
                    "investments": np.zeros(env_flat.max_num_assets, dtype=np.int8),
                    "bd_bids": np.zeros(env_flat.bd_max_slots, dtype=np.int64),
                }
                for agent in env_flat.agents
            }
            flat_obs, *_ = env_flat.step(actions)
            flat_obs_history.append(flat_obs)

        # Compare
        for step in range(num_steps + 1):
            for agent in env_dict.possible_agents:
                dict_as_flat = env_dict.flatten_dict_obs(dict_obs_history[step][agent])
                np.testing.assert_allclose(
                    flat_obs_history[step][agent],
                    dict_as_flat,
                    atol=1e-6,
                    err_msg=(f"Mismatch for {agent} at step {step}"),
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
                    assert orig[key] == recon[key], f"Asset {i} key {key} mismatch"
                for key in ["max_revenue", "enpv", "eroi"]:
                    assert orig[key] == pytest.approx(recon[key], rel=1e-5), (
                        f"Asset {i} key {key} mismatch"
                    )

            # Check BD market
            for i in range(len(dict_obs["bd_market"])):
                orig = dict_obs["bd_market"][i]
                recon = reconstructed["bd_market"][i]
                assert orig["available"] == recon["available"]
                for key in ["enpv", "ptrs"]:
                    assert orig[key] == pytest.approx(recon[key], rel=1e-5), (
                        f"BD slot {i} key {key}"
                    )

    def test_flatten_then_unflatten_matches_flat(self):
        """Test flatten(unflatten(flat)) == flat."""
        env = _make_env(flatten_obs=True)
        flat_obs_all, _ = env.reset(seed=42)

        for agent in env.possible_agents:
            flat_obs = flat_obs_all[agent]
            dict_obs = env.unflatten_to_dict_obs(flat_obs)
            re_flat = env.flatten_dict_obs(dict_obs)
            np.testing.assert_allclose(
                flat_obs,
                re_flat,
                atol=1e-6,
                err_msg=f"Re-flattened mismatch for {agent}",
            )

    def test_dict_matches_flat_with_ptrs_readings(self):
        """
        Dict obs ptrs field uses ptrs_sample_mean when ptrs_readings is enabled.

        Both flat and dict obs must show the same PTRS value after a reading is
        applied. Without the fix, dict obs used trial.ptrs (raw) while flat obs
        used trial.ptrs_sample_mean — correct only because game_state also sets
        trial.ptrs = ptrs_sample_mean on flush. This test locks in the explicit
        ptrs_sample_mean path in the dict obs.
        """
        readings_cfg = PtrsReadingsConfig(
            enabled=True,
            cost_fraction=0.01,
            cost_rounding=1,
            action_space_max_readings=3,
            sigma_logit_base=1.5,
            sigma_ep=None,
            noise_multipliers=[1.0, 1.5, 2.0],
            max_sample_obs=20,
        )

        num_steps = 3

        env_dict = _make_env(
            flatten_obs=False,
            starting_cash=1_000_000_000,
            ptrs_readings_config=readings_cfg,
        )
        dict_obs, _ = env_dict.reset(seed=42)
        dict_history = [dict_obs]
        for _ in range(num_steps):
            # Only commission readings on portfolio slots (bd_enabled=False here)
            ptrs_research = np.zeros(
                env_dict.max_num_assets + env_dict.bd_max_slots, dtype=np.int64
            )
            ptrs_research[:env_dict.max_num_assets] = 1
            actions = {
                agent: {
                    "investments": np.zeros(env_dict.max_num_assets, dtype=np.int8),
                    "bd_bids": np.zeros(env_dict.bd_max_slots, dtype=np.int64),
                    "ptrs_research": ptrs_research,
                }
                for agent in env_dict.agents
            }
            dict_obs, *_ = env_dict.step(actions)
            dict_history.append(dict_obs)

        env_flat = _make_env(
            flatten_obs=True,
            starting_cash=1_000_000_000,
            ptrs_readings_config=readings_cfg,
        )
        flat_obs, _ = env_flat.reset(seed=42)
        flat_history = [flat_obs]
        for _ in range(num_steps):
            ptrs_research = np.zeros(
                env_flat.max_num_assets + env_flat.bd_max_slots, dtype=np.int64
            )
            ptrs_research[:env_flat.max_num_assets] = 1
            actions = {
                agent: {
                    "investments": np.zeros(env_flat.max_num_assets, dtype=np.int8),
                    "bd_bids": np.zeros(env_flat.bd_max_slots, dtype=np.int64),
                    "ptrs_research": ptrs_research,
                }
                for agent in env_flat.agents
            }
            flat_obs, *_ = env_flat.step(actions)
            flat_history.append(flat_obs)

        for step in range(num_steps + 1):
            for agent in env_dict.possible_agents:
                dict_as_flat = env_dict.flatten_dict_obs(dict_history[step][agent])
                np.testing.assert_allclose(
                    flat_history[step][agent],
                    dict_as_flat,
                    atol=1e-6,
                    err_msg=f"ptrs_readings dict/flat mismatch for {agent} at step {step}",
                )

    def test_observation_space_contains_dict_obs(self):
        """Observation space should contain the dict observation."""
        env = _make_env(flatten_obs=False)
        observations, _ = env.reset(seed=42)

        for agent in env.possible_agents:
            space = env.observation_space(agent)
            assert isinstance(space, gym.spaces.Dict)


class TestOwnAssetCashEnpvObservation:
    """
    Own-asset value in the observation is cash-adjusted eNPV, not full eNPV.

    The competition reward is Net Cash Flow, and cash only accrues revenue scaled
    by ``reinvestment_percentage`` (the rest is a balance sink). Exposing full
    eNPV in the observation would overstate the liquid value an asset returns to
    cash, so the per-asset value slot (flat ``offset + 7`` / dict ``"enpv"``)
    must carry ``cash_enpv`` so the policy optimises against its true objective.
    """

    _REINV = 0.35

    def _iter_owned_assets(self, env, agent, slots):
        """Yield (obs_slot, asset) pairs for populated own-asset slots."""
        game_state = env.multi_agent_game.agent_states[agent]
        asset_order = env._asset_id_orders[agent]
        for i, slot in enumerate(slots):
            if i >= len(asset_order):
                continue
            asset = game_state.assets.get(asset_order[i])
            if asset is not None:
                yield slot, asset

    def test_dict_obs_asset_enpv_is_cash_enpv(self):
        """Dict obs own-asset value slot carries cash_enpv, not full enpv."""
        env = _make_env(reinvestment_percentage=self._REINV, flatten_obs=False)
        obs, _ = env.reset(seed=42)

        differed = False
        for agent in env.possible_agents:
            for slot, asset in self._iter_owned_assets(
                env, agent, obs[agent]["assets"]
            ):
                cash = asset.cash_enpv(self._REINV)
                assert slot["enpv"] == pytest.approx(cash, rel=1e-5), (
                    f"{agent}: obs enpv {slot['enpv']:,.2f} != cash_enpv "
                    f"{cash:,.2f} (full enpv {asset.enpv:,.2f})"
                )
                if cash != pytest.approx(asset.enpv):
                    differed = True
        assert differed, (
            "Test vacuous: every owned asset had cash_enpv == full enpv, so "
            "the observation could be exposing either; use a reinvestment rate "
            "and assets where the two genuinely diverge."
        )

    def test_flat_obs_asset_enpv_is_cash_enpv(self):
        """Flat obs own-asset value slot (offset+7) carries cash_enpv."""
        env = _make_env(reinvestment_percentage=self._REINV, flatten_obs=True)
        obs, _ = env.reset(seed=42)

        for agent in env.possible_agents:
            dict_obs = env.unflatten_to_dict_obs(obs[agent])
            for slot, asset in self._iter_owned_assets(
                env, agent, dict_obs["assets"]
            ):
                cash = asset.cash_enpv(self._REINV)
                assert slot["enpv"] == pytest.approx(cash, rel=1e-4), (
                    f"{agent}: flat obs enpv {slot['enpv']:,.2f} != cash_enpv "
                    f"{cash:,.2f} (full enpv {asset.enpv:,.2f})"
                )


class TestBDAssetCashEnpvObservation:
    """
    BD-market value in the observation is cash-adjusted eNPV, not full eNPV.

    Mirrors ``TestOwnAssetCashEnpvObservation`` for the BD slots. The BD value
    slot (flat ``bd_offset + 6`` / dict ``"enpv"``) must carry ``cash_enpv`` so
    the price signal an agent bids against matches the own-asset value slot and
    the NCF reward. With ptrs readings off there is no private clone, so the
    observed asset is the shared BD asset and the slot must equal
    ``current_bd_assets[slot].cash_enpv``.
    """

    _REINV = 0.35

    def _make_bd_env(self, flatten_obs):
        return _make_env(
            reinvestment_percentage=self._REINV,
            flatten_obs=flatten_obs,
            horizon=40,
            bd_enabled=True,
            bd_min_step=0,
            bd_max_slots=3,
        )

    def _obs_with_bd(self, env, max_steps=25):
        """Reset then step blank actions until ≥1 BD asset exists; return obs."""
        obs, _ = env.reset(seed=42)
        for _ in range(max_steps):
            if env.multi_agent_game.shared_market.current_bd_assets:
                return obs
            blank = {
                a: {
                    "investments": np.zeros(env.max_num_assets, dtype=np.int8),
                    "bd_bids": np.zeros(env.bd_max_slots, dtype=np.int64),
                }
                for a in env.agents
            }
            obs, *_ = env.step(blank)
        return obs

    def _check_bd_market(self, env, bd_market, rel):
        """Assert each available BD slot's value == cash_enpv; return counts."""
        bd_assets = env.multi_agent_game.shared_market.current_bd_assets
        checked = differed = 0
        for i, entry in enumerate(bd_market):
            if not entry["available"] or i >= len(bd_assets):
                continue
            asset = bd_assets[i]
            cash = asset.cash_enpv(self._REINV)
            assert entry["enpv"] == pytest.approx(cash, rel=rel), (
                f"BD slot {i}: obs enpv {entry['enpv']:,.2f} != cash_enpv "
                f"{cash:,.2f} (full enpv {asset.enpv:,.2f})"
            )
            checked += 1
            if cash != pytest.approx(asset.enpv):
                differed += 1
        return checked, differed

    def test_dict_obs_bd_enpv_is_cash_enpv(self):
        """Dict obs BD value slot carries cash_enpv, not full enpv."""
        env = self._make_bd_env(flatten_obs=False)
        obs = self._obs_with_bd(env)

        total_checked = total_differed = 0
        for agent in env.possible_agents:
            checked, differed = self._check_bd_market(
                env, obs[agent]["bd_market"], rel=1e-5
            )
            total_checked += checked
            total_differed += differed
        assert total_checked, "Test vacuous: no BD assets appeared to check."
        assert total_differed, (
            "Test vacuous: every BD asset had cash_enpv == full enpv, so the "
            "observation could be exposing either; use a reinvestment rate and "
            "assets where the two genuinely diverge."
        )

    def test_flat_obs_bd_enpv_is_cash_enpv(self):
        """Flat obs BD value slot (bd_offset+6) carries cash_enpv."""
        env = self._make_bd_env(flatten_obs=True)
        obs = self._obs_with_bd(env)

        total_checked = 0
        for agent in env.possible_agents:
            dict_obs = env.unflatten_to_dict_obs(obs[agent])
            checked, _ = self._check_bd_market(
                env, dict_obs["bd_market"], rel=1e-4
            )
            total_checked += checked
        assert total_checked, "Test vacuous: no BD assets appeared to check."


class TestBDWinPriceObservation:
    """The price an opponent paid for a BD asset is exposed via BD_DEAL alerts."""

    @staticmethod
    def _inject_bd_deal(env, price, agent_id="pharma_0"):
        """Register a BD_DEAL alert with the given win price on the shared market."""
        from pyxis_portfolio_challenge.game.shared_market_state import Alert

        env.multi_agent_game.shared_market.add_alert(
            Alert(
                step=env.multi_agent_game.time,
                event_type=AlertType.BD_DEAL,
                agent_id=agent_id,
                therapeutic_area=THERAPEUTIC_AREAS[0],
                indication=0,
                details={"asset_name": "test_asset", "price": price},
            )
        )

    def _alert_offset(self, env):
        """Flat-obs index of the first alert slot."""
        layout = env._layout
        return (
            layout.global_features
            + env.max_num_assets * layout.asset_total_features
            + env.bd_max_slots * _BD_OBS_FEATURES_PER_SLOT
            + len(THERAPEUTIC_AREAS)
            * env.max_indications_per_ta
            * _INDICATION_FEATURES
        )

    def test_flat_obs_exposes_win_price_to_opponent(self):
        env = _make_env(flatten_obs=True)
        env.reset(seed=42)
        self._inject_bd_deal(env, price=1_234_567.0)

        offset = self._alert_offset(env)
        obs = env._get_observation_flat("pharma_1")
        assert obs[offset + 1] == 1.0  # BD_DEAL one-hot
        assert obs[offset + 11] == pytest.approx(1_234_567.0)  # bd_price

    def test_flat_obs_hides_own_win_price(self):
        """An agent never sees its own BD_DEAL alert, so no price is encoded."""
        env = _make_env(flatten_obs=True)
        env.reset(seed=42)
        self._inject_bd_deal(env, price=1_234_567.0)

        offset = self._alert_offset(env)
        obs = env._get_observation_flat("pharma_0")
        assert obs[offset + 1] == 0.0
        assert obs[offset + 11] == 0.0  # bd_price

    def test_dict_obs_exposes_win_price(self):
        env = _make_env(flatten_obs=False)
        env.reset(seed=42)
        self._inject_bd_deal(env, price=42_000_000.0)

        alert = env._get_observation_dict("pharma_1")["alerts"][0]
        assert alert["bd_price"] == pytest.approx(42_000_000.0)
        assert alert["phase"] == 0.0

    def test_non_bd_alerts_have_zero_price(self):
        from pyxis_portfolio_challenge.game.shared_market_state import Alert

        env = _make_env(flatten_obs=False)
        env.reset(seed=42)
        env.multi_agent_game.shared_market.add_alert(
            Alert(
                step=env.multi_agent_game.time,
                event_type=AlertType.DRUG_RELEASE,
                agent_id="pharma_0",
                therapeutic_area=THERAPEUTIC_AREAS[0],
            )
        )

        alert = env._get_observation_dict("pharma_1")["alerts"][0]
        assert alert["bd_price"] == 0.0

    def test_win_price_survives_flatten_round_trip(self):
        env = _make_env(flatten_obs=False)
        env.reset(seed=42)
        self._inject_bd_deal(env, price=7_500_000.0)

        dict_obs = env._get_observation_dict("pharma_1")
        flat = env.flatten_dict_obs(dict_obs)
        round_tripped = env.unflatten_to_dict_obs(flat)
        assert round_tripped["alerts"][0]["bd_price"] == pytest.approx(7_500_000.0)

    def test_padding_alerts_have_zero_price(self):
        """Empty alert slots pad bd_price to zero."""
        env = _make_env(flatten_obs=False)
        observations, _ = env.reset(seed=42)

        obs = observations["pharma_1"]
        assert len(obs["alerts"]) == env.max_alerts
        assert all(alert["bd_price"] == 0.0 for alert in obs["alerts"])


class TestMarketingSpendAlerts:
    """
    BE_SPEND / DC_SPEND alerts are exposed to opponents in the observation.

    These leaks carry no cost/amount — only *that* an agent spent brand equity
    or demand creation, and in which therapeutic area / indication.
    """

    @staticmethod
    def _inject(env, event_type, agent_id="pharma_0", ta_index=0, indication=0):
        """Register a BE/DC spend alert on the shared market."""
        from pyxis_portfolio_challenge.game.shared_market_state import Alert

        env.multi_agent_game.shared_market.add_alert(
            Alert(
                step=env.multi_agent_game.time,
                event_type=event_type,
                agent_id=agent_id,
                therapeutic_area=THERAPEUTIC_AREAS[ta_index],
                indication=indication,
            )
        )

    def _alert_offset(self, env):
        """Flat-obs index of the first alert slot."""
        layout = env._layout
        return (
            layout.global_features
            + env.max_num_assets * layout.asset_total_features
            + env.bd_max_slots * _BD_OBS_FEATURES_PER_SLOT
            + len(THERAPEUTIC_AREAS)
            * env.max_indications_per_ta
            * _INDICATION_FEATURES
        )

    def test_be_spend_alert_encoded_in_flat_obs(self):
        env = _make_env(flatten_obs=True)
        env.reset(seed=42)
        self._inject(env, AlertType.BE_SPEND, ta_index=1, indication=2)

        offset = self._alert_offset(env)
        obs = env._get_observation_flat("pharma_1")
        assert obs[offset + 4] == 1.0  # BE_SPEND one-hot
        assert obs[offset + 0] == 0.0  # not DRUG_RELEASE
        assert obs[offset + 5] == 0.0  # not DC_SPEND
        assert obs[offset + 6] == pytest.approx(0.0)  # agent_index of pharma_0
        assert obs[offset + 7] == pytest.approx(1.0)  # ta_index
        assert obs[offset + 8] == pytest.approx(2.0)  # indication
        assert obs[offset + 11] == 0.0  # no bd_price

    def test_dc_spend_alert_encoded_in_flat_obs(self):
        env = _make_env(flatten_obs=True)
        env.reset(seed=42)
        self._inject(env, AlertType.DC_SPEND, ta_index=1, indication=2)

        offset = self._alert_offset(env)
        obs = env._get_observation_flat("pharma_1")
        assert obs[offset + 5] == 1.0  # DC_SPEND one-hot
        assert obs[offset + 4] == 0.0  # not BE_SPEND
        assert obs[offset + 7] == pytest.approx(1.0)  # ta_index
        assert obs[offset + 8] == pytest.approx(2.0)  # indication
        assert obs[offset + 11] == 0.0  # no bd_price

    def test_agent_does_not_see_own_spend_alert(self):
        """An agent never sees its own BE/DC spend leak."""
        env = _make_env(flatten_obs=True)
        env.reset(seed=42)
        self._inject(env, AlertType.BE_SPEND, agent_id="pharma_0")

        offset = self._alert_offset(env)
        obs = env._get_observation_flat("pharma_0")
        assert obs[offset + 4] == 0.0

    def test_spend_alerts_have_zero_price_and_phase_in_dict(self):
        env = _make_env(flatten_obs=False)
        env.reset(seed=42)
        self._inject(env, AlertType.DC_SPEND, ta_index=0, indication=1)

        alert = env._get_observation_dict("pharma_1")["alerts"][0]
        assert alert["event_type"] == 5  # DC_SPEND
        assert alert["indication"] == 1
        assert alert["bd_price"] == 0.0
        assert alert["phase"] == 0.0

    def test_spend_alert_survives_flatten_round_trip(self):
        env = _make_env(flatten_obs=False)
        env.reset(seed=42)
        self._inject(env, AlertType.BE_SPEND, ta_index=1, indication=2)

        dict_obs = env._get_observation_dict("pharma_1")
        flat = env.flatten_dict_obs(dict_obs)
        round_tripped = env.unflatten_to_dict_obs(flat)
        alert = round_tripped["alerts"][0]
        assert alert["event_type"] == 4  # BE_SPEND
        assert alert["ta_index"] == 1
        assert alert["indication"] == 2

    @staticmethod
    def _inject_be_count(env, be_count, ta_index=0, indication=0):
        """Register a BE_SPEND alert carrying an explicit be_count."""
        from pyxis_portfolio_challenge.game.shared_market_state import Alert

        env.multi_agent_game.shared_market.add_alert(
            Alert(
                step=env.multi_agent_game.time,
                event_type=AlertType.BE_SPEND,
                agent_id="pharma_0",
                therapeutic_area=THERAPEUTIC_AREAS[ta_index],
                indication=indication,
                details={"be_count": be_count},
            )
        )

    def test_be_count_encoded_in_flat_obs(self):
        """The BE spend count surfaces at the be_count slot (+12) of the flat obs."""
        env = _make_env(flatten_obs=True)
        env.reset(seed=42)
        self._inject_be_count(env, be_count=3, ta_index=1, indication=2)

        offset = self._alert_offset(env)
        obs = env._get_observation_flat("pharma_1")
        assert obs[offset + 4] == 1.0  # BE_SPEND one-hot
        assert obs[offset + 12] == pytest.approx(3.0)  # be_count

    def test_non_be_alert_has_zero_be_count(self):
        """A DC alert carries be_count 0 (the field is BE-specific)."""
        env = _make_env(flatten_obs=False)
        env.reset(seed=42)
        self._inject(env, AlertType.DC_SPEND, ta_index=0, indication=1)

        alert = env._get_observation_dict("pharma_1")["alerts"][0]
        assert alert["event_type"] == 5  # DC_SPEND
        assert alert["be_count"] == 0

    def test_be_count_survives_flatten_round_trip(self):
        env = _make_env(flatten_obs=False)
        env.reset(seed=42)
        self._inject_be_count(env, be_count=2, ta_index=0, indication=1)

        dict_obs = env._get_observation_dict("pharma_1")
        flat = env.flatten_dict_obs(dict_obs)
        round_tripped = env.unflatten_to_dict_obs(flat)
        assert round_tripped["alerts"][0]["be_count"] == 2

    def test_two_assets_same_indication_yield_one_alert_be_count_two(self):
        """
        End-to-end: two BE spends in one indication -> one alert, be_count == 2.

        Exercises the real game aggregation rather than a hand-built alert: the
        env maps the brand_equity action onto two owned assets that share a
        (ta, indication); the game counts both and the leak (prob 1.0) reports
        be_count == 2 in a single indication-level alert, which then surfaces in
        the opponent's observation.
        """
        import uuid as _uuid

        from pyxis_portfolio_challenge.game.asset import AssetState, DrugAsset
        from pyxis_portfolio_challenge.game.trial import (
            Trial,
            TrialPhase,
            TrialState,
        )

        def _on_market_drug(ta, ind):
            return DrugAsset(
                id=_uuid.uuid4(), name="Drug", therapeutic_area=ta, type="internal",
                description="", max_revenue=1_000_000, raw_max_revenue=1_000_000,
                time_until_max_revenue=5, time_until_patent_expiry=19,
                time_on_market=0,
                trial=Trial(phase=TrialPhase.PHASE_1, state=TrialState.PHASE_SUCCESS,
                            cost_remaining=0, ptrs=1.0, time_remaining=0,
                            next_trial_on_success=None),
                state=AssetState.OnMarket, indication=ind,
            )

        env = _make_env(
            num_agents=2,
            marketing_config=_MARKETING_CFG,
            be_leak_probability=1.0,
            starting_cash=50_000_000_000.0,
        )
        env.reset(seed=7)

        # Give pharma_0 exactly two assets in the same (oncology, indication 0)
        # and point the action-slot ordering at them.
        drug_a = _on_market_drug("oncology", 0)
        drug_b = _on_market_drug("oncology", 0)
        env.multi_agent_game.agent_states["pharma_0"].assets = {
            drug_a.id: drug_a,
            drug_b.id: drug_b,
        }
        env._asset_id_orders["pharma_0"] = [drug_a.id, drug_b.id] + [None] * (
            env.max_num_assets - 2
        )

        # Spend BE on both assets (slots 0 and 1); opponent spends nothing.
        n_ind_slots = env.max_indications_per_ta * len(THERAPEUTIC_AREAS)
        be_arr = np.zeros(env.max_num_assets, dtype=np.int64)
        be_arr[0] = 1
        be_arr[1] = 1
        actions = {
            "pharma_0": {
                "investments": np.zeros(env.max_num_assets, dtype=np.int64),
                "bd_bids": np.zeros(env.bd_max_slots, dtype=np.int64),
                "demand_creation": np.zeros(n_ind_slots, dtype=np.int64),
                "brand_equity": be_arr,
            },
            "pharma_1": {
                "investments": np.zeros(env.max_num_assets, dtype=np.int64),
                "bd_bids": np.zeros(env.bd_max_slots, dtype=np.int64),
                "demand_creation": np.zeros(n_ind_slots, dtype=np.int64),
                "brand_equity": np.zeros(env.max_num_assets, dtype=np.int64),
            },
        }
        env.step(actions)

        # A single indication-level alert carrying the aggregated count.
        market = env.multi_agent_game.shared_market
        be_alerts = [
            a
            for a in market.alerts
            if a.event_type == AlertType.BE_SPEND and a.agent_id == "pharma_0"
        ]
        assert len(be_alerts) == 1
        assert be_alerts[0].therapeutic_area == "oncology"
        assert be_alerts[0].indication == 0
        assert be_alerts[0].details["be_count"] == 2

        # ...and it surfaces in the opponent's observation with be_count == 2.
        opp_alerts = env._get_observation_dict("pharma_1")["alerts"]
        be_obs = [al for al in opp_alerts if al["event_type"] == 4]  # BE_SPEND
        assert len(be_obs) == 1
        assert be_obs[0]["be_count"] == 2


class TestClinicalSiteWinPriceObservation:
    """The bid an opponent paid to win a clinical site is exposed via alerts."""

    @staticmethod
    def _inject_site_deal(env, price, agent_id="pharma_0"):
        """Register a CLINICAL_SITE_DEAL alert with the given win price."""
        env.multi_agent_game.shared_market.register_site_deal(agent_id, price)

    def _alert_offset(self, env):
        """Flat-obs index of the first alert slot."""
        layout = env._layout
        return (
            layout.global_features
            + env.max_num_assets * layout.asset_total_features
            + env.bd_max_slots * _BD_OBS_FEATURES_PER_SLOT
            + len(THERAPEUTIC_AREAS)
            * env.max_indications_per_ta
            * _INDICATION_FEATURES
        )

    def test_flat_obs_exposes_win_price_to_opponent(self):
        env = _make_env(flatten_obs=True)
        env.reset(seed=42)
        self._inject_site_deal(env, price=3_300_000.0)

        offset = self._alert_offset(env)
        obs = env._get_observation_flat("pharma_1")
        assert obs[offset + 3] == 1.0  # CLINICAL_SITE_DEAL one-hot
        assert obs[offset + 11] == pytest.approx(3_300_000.0)

    def test_flat_obs_hides_own_win_price(self):
        """An agent never sees its own site-deal alert, so no price is encoded."""
        env = _make_env(flatten_obs=True)
        env.reset(seed=42)
        self._inject_site_deal(env, price=3_300_000.0)

        offset = self._alert_offset(env)
        obs = env._get_observation_flat("pharma_0")
        assert obs[offset + 3] == 0.0
        assert obs[offset + 11] == 0.0

    def test_dict_obs_exposes_win_price(self):
        env = _make_env(flatten_obs=False)
        env.reset(seed=42)
        self._inject_site_deal(env, price=5_000_000.0)

        alert = env._get_observation_dict("pharma_1")["alerts"][0]
        assert alert["event_type"] == 3  # CLINICAL_SITE_DEAL index
        assert alert["bd_price"] == pytest.approx(5_000_000.0)
        assert alert["phase"] == 0.0

    def test_win_price_survives_flatten_round_trip(self):
        env = _make_env(flatten_obs=False)
        env.reset(seed=42)
        self._inject_site_deal(env, price=6_250_000.0)

        dict_obs = env._get_observation_dict("pharma_1")
        flat = env.flatten_dict_obs(dict_obs)
        round_tripped = env.unflatten_to_dict_obs(flat)
        assert round_tripped["alerts"][0]["event_type"] == 3
        assert round_tripped["alerts"][0]["bd_price"] == pytest.approx(6_250_000.0)


class TestBDPersistence:
    """Integration tests for BD asset persistence (slot-capped market)."""

    def test_obs_features_per_slot_is_11(self):
        assert _BD_OBS_FEATURES_PER_SLOT == 11

    def test_steps_remaining_key_in_dict_obs(self):
        env = _make_env(flatten_obs=False, bd_enabled=True, bd_max_slots=3)
        observations, _ = env.reset(seed=42)

        for agent in env.possible_agents:
            bd_market = observations[agent]["bd_market"]
            assert len(bd_market) == 3
            for slot in bd_market:
                assert "steps_remaining" in slot, "steps_remaining missing from BD slot obs"

    def test_steps_remaining_in_flat_obs_roundtrip(self):
        """steps_remaining survives flatten → unflatten without loss."""
        env = _make_env(
            flatten_obs=False,
            bd_enabled=True,
            bd_max_slots=3,
        )
        observations, _ = env.reset(seed=42)

        for agent in env.possible_agents:
            dict_obs = observations[agent]
            flat = env.flatten_dict_obs(dict_obs)
            roundtripped = env.unflatten_to_dict_obs(flat)
            for i, (orig, recon) in enumerate(
                zip(dict_obs["bd_market"], roundtripped["bd_market"])
            ):
                assert orig["steps_remaining"] == pytest.approx(
                    recon["steps_remaining"], abs=1e-6
                ), f"steps_remaining mismatch in BD slot {i}"

    def test_smoke_several_steps_bd_persist(self):
        """Full episode with bd_persist_steps=3 completes without errors."""
        env = _make_env(
            horizon=6,
            bd_enabled=True,
            bd_max_slots=3,
            bd_persist_steps=3,
            bd_min_step=0,
            bd_base_lambda=2.0,  # high λ to guarantee spawns
        )
        env.reset(seed=7)

        for _ in range(6):
            actions = {
                agent: {
                    "investments": np.zeros(env.max_num_assets, dtype=np.int8),
                    "bd_bids": np.zeros(env.bd_max_slots, dtype=np.int64),
                }
                for agent in env.agents
            }
            obs, rewards, terms, truncs, infos = env.step(actions)

        assert all(terms.values())

    def test_obs_size_includes_steps_remaining(self):
        """Observation vector size accounts for 10 features per BD slot."""
        env = _make_env(bd_max_slots=3)
        env.reset(seed=42)
        expected_bd_contribution = 3 * _BD_OBS_FEATURES_PER_SLOT
        layout = env._layout
        max_ind = env.max_indications_per_ta
        from pyxis_portfolio_challenge.environment.multi_agent_training_gym import (
            _ALERT_FEATURES,
            _INDICATION_FEATURES,
        )
        expected_total = (
            layout.global_features
            + env.max_num_assets * layout.asset_total_features
            + expected_bd_contribution
            + len(THERAPEUTIC_AREAS) * max_ind * _INDICATION_FEATURES
            + env.max_alerts * _ALERT_FEATURES
        )
        assert env._obs_size == expected_total

    def test_bd_persist_steps_default_backward_compat(self):
        """bd_persist_steps=1 env runs without error (old single-step behaviour)."""
        env = _make_env(
            horizon=4,
            bd_enabled=True,
            bd_max_slots=2,
            bd_persist_steps=1,
            bd_min_step=0,
            bd_base_lambda=1.5,
        )
        env.reset(seed=99)
        for _ in range(4):
            actions = {
                agent: {
                    "investments": np.zeros(env.max_num_assets, dtype=np.int8),
                    "bd_bids": np.zeros(env.bd_max_slots, dtype=np.int64),
                }
                for agent in env.agents
            }
            env.step(actions)


_MARKETING_CFG = MarketingConfig(
    enabled=True,
    dc_cost_fraction=0.05,
    dc_step_boost=0.20,
    dc_decay_rate=0.067,
    be_cost_fraction=0.03,
    be_boost=0.1,
    be_decay_rate=0.206,
    be_effectiveness=0.3,
)

_MARKETING_CFG_DISABLED = MarketingConfig(
    enabled=False,
    dc_cost_fraction=0.05,
    dc_step_boost=0.20,
    dc_decay_rate=0.067,
    be_cost_fraction=0.03,
    be_boost=0.1,
    be_decay_rate=0.206,
    be_effectiveness=0.3,
)


class TestMarketing:
    """Tests for demand creation and brand equity marketing mechanics."""

    def test_demand_multiplier_starts_at_one(self):
        """All indication markets initialise with demand_multiplier = 1.0."""
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "num_indications_per_ta": 2}
        )
        from pyxis_portfolio_challenge.game.shared_market_state import indication_key
        key = indication_key("oncology", 0)
        ind_market = state.indication_markets.get(key)
        assert ind_market is not None
        assert ind_market.demand_multiplier == 1.0

    def test_apply_demand_creation_increases_multiplier(self):
        """apply_demand_creation() lifts the multiplier by boost_fraction × headroom."""
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "num_indications_per_ta": 2}
        )
        from pyxis_portfolio_challenge.game.shared_market_state import indication_key
        key = indication_key("oncology", 0)
        ind_market = state.indication_markets[key]
        assert ind_market.demand_multiplier == 1.0

        expected_boost = (1.5 - 1.0) * 0.30  # headroom × boost_fraction = 0.15
        state.apply_demand_creation(key, expected_boost, _MARKETING_CFG)
        assert ind_market.demand_multiplier == pytest.approx(1.15, rel=1e-6)

    def test_demand_creation_accumulates_without_cap(self):
        """A large boost accumulates freely — no hard cap."""
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "num_indications_per_ta": 2}
        )
        from pyxis_portfolio_challenge.game.shared_market_state import indication_key
        key = indication_key("oncology", 0)
        state.apply_demand_creation(key, 5.0, _MARKETING_CFG)
        assert state.indication_markets[key].demand_multiplier == pytest.approx(6.0)

    def test_advance_time_decays_demand_multiplier(self):
        """advance_time() applies per-step headroom decay toward 1.0."""
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "num_indications_per_ta": 2}
        )
        from pyxis_portfolio_challenge.game.shared_market_state import indication_key
        key = indication_key("oncology", 0)
        ind_market = state.indication_markets[key]
        ind_market.demand_multiplier = 1.3  # set directly for test

        state.advance_time(marketing_config=_MARKETING_CFG)

        # headroom = 0.3, after one step: 1.0 + 0.3 × (1 - 0.067) ≈ 1.2799
        expected = 1.0 + 0.3 * (1.0 - 0.067)
        assert ind_market.demand_multiplier == pytest.approx(expected, rel=1e-6)

    def test_advance_time_no_decay_when_disabled(self):
        """advance_time() without marketing_config leaves demand_multiplier unchanged."""
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "num_indications_per_ta": 2}
        )
        from pyxis_portfolio_challenge.game.shared_market_state import indication_key
        key = indication_key("oncology", 0)
        state.indication_markets[key].demand_multiplier = 1.3
        state.advance_time()  # no marketing_config
        assert state.indication_markets[key].demand_multiplier == pytest.approx(1.3)

    def test_simultaneous_spend_uses_pre_step_snapshot(self):
        """Both agents' boosts computed from the pre-step multiplier, applied additively."""
        init_game_rng(42)
        state = SharedMarketState.initialize(
            **{**_SHARED_MARKET_DEFAULTS, "num_indications_per_ta": 2}
        )
        from pyxis_portfolio_challenge.game.shared_market_state import indication_key
        key = indication_key("oncology", 0)
        # Two agents both spend → fixed boosts summed and clamped
        total_boost = 2 * _MARKETING_CFG.dc_step_boost  # 2 × 0.20 = 0.40
        state.apply_demand_creation(key, total_boost, _MARKETING_CFG)
        # result = min(1.0 + 0.40, 1.5) = 1.40 (below cap)
        assert state.indication_markets[key].demand_multiplier == pytest.approx(1.40, rel=1e-6)

    def test_demand_creation_cost_is_indication_wide_and_unconditional(
        self, game_state_factory_fixed_list_asset_gen
    ):
        """
        DC cost = dc_cost_fraction × cost_base per action==1, independent of
        the agent's holdings in the indication (indication-wide, never free).

        Isolated as the cash delta vs an identical no-DC step (same seed → the
        only difference is the demand-creation cost).
        """
        PEAK = 5000.0

        def build():
            gs = game_state_factory_fixed_list_asset_gen(cash=10000)
            gs._marketing_config = _MARKETING_CFG
            return gs

        expected = _MARKETING_CFG.dc_cost_fraction * PEAK  # constant, not per-drug

        # Baseline: no demand-creation action.
        s0 = build().step(investor_actions={})

        # Size one indication → charged exactly f × PEAK, regardless of whether a
        # drug is held there (the old mechanic charged f × that drug's max_rev,
        # or nothing when no drug existed).
        s1 = build().step(
            investor_actions={},
            demand_creation_actions={"vaccines and infectious disease:3": 1},
            demand_creation_cost_base=PEAK,
        )
        assert s0.cash - s1.cash == pytest.approx(expected)

        # Two indications in one step → twice the cost (per-action charge).
        s2 = build().step(
            investor_actions={},
            demand_creation_actions={
                "vaccines and infectious disease:3": 1,
                "oncology:2": 1,
            },
            demand_creation_cost_base=PEAK,
        )
        assert s0.cash - s2.cash == pytest.approx(2 * expected)

        # Guards the default: with no cost_base passed it falls back to 0.0, so
        # callers that don't wire marketing (e.g. single-agent) are unaffected.
        s3 = build().step(
            investor_actions={},
            demand_creation_actions={"oncology:2": 1},
        )
        assert s3.cash == pytest.approx(s0.cash)

    def test_brand_scores_initialise_empty(self):
        """GameState starts with empty _brand_scores dict."""
        env = _make_env(marketing_config=_MARKETING_CFG)
        env.reset(seed=42)
        for agent in env.agents:
            gs = env.multi_agent_game.agent_states[agent]
            assert gs._brand_scores == {}

    def test_obs_size_increases_with_marketing(self):
        """obs_size grows by max_num_assets (brand_score) + n_indications (demand_mult)."""
        base_env = _make_env(max_num_assets=15, max_indications_per_ta=4)
        marketing_env = _make_env(
            max_num_assets=15, max_indications_per_ta=4, marketing_config=_MARKETING_CFG
        )
        n_ind_slots = len(THERAPEUTIC_AREAS) * 4
        expected_extra = 15 + n_ind_slots  # brand_score per asset + demand_mult per indication
        assert marketing_env._obs_size == base_env._obs_size + expected_extra

    def test_action_space_includes_marketing_keys(self):
        """action_space() includes 'demand_creation' and 'brand_equity' when enabled."""
        env = _make_env(marketing_config=_MARKETING_CFG)
        space = env.action_space("pharma_0")
        assert "demand_creation" in space.spaces
        assert "brand_equity" in space.spaces
        n_ind_slots = env.max_indications_per_ta * len(THERAPEUTIC_AREAS)
        assert space["demand_creation"].shape == (n_ind_slots,)
        assert space["brand_equity"].shape == (env.max_num_assets,)

    def test_action_space_no_marketing_keys_when_disabled(self):
        """action_space() does not include marketing keys when disabled."""
        env = _make_env(marketing_config=_MARKETING_CFG_DISABLED)
        space = env.action_space("pharma_0")
        assert "demand_creation" not in space.spaces
        assert "brand_equity" not in space.spaces

    def test_marketing_integration_run(self):
        """100-step run with marketing enabled: no exceptions, multipliers in valid range."""
        env = _make_env(
            marketing_config=_MARKETING_CFG,
            horizon=100,
            starting_cash=50_000_000_000.0,  # large cash so marketing costs can't bankrupt
        )
        env.reset(seed=99)
        n_ind_slots = env.max_indications_per_ta * len(THERAPEUTIC_AREAS)

        for _ in range(100):
            if not env.agents:
                break
            actions = {}
            for agent in env.agents:
                actions[agent] = {
                    "investments": np.zeros(env.max_num_assets, dtype=np.int64),
                    "bd_bids": np.zeros(env.bd_max_slots, dtype=np.int64),
                    "demand_creation": np.ones(n_ind_slots, dtype=np.int64),
                    "brand_equity": np.ones(env.max_num_assets, dtype=np.int64),
                }
            env.step(actions)

            # All demand multipliers must be >= 1.0 (no hard cap)
            for ind_market in env.multi_agent_game.shared_market.indication_markets.values():
                assert ind_market.demand_multiplier >= 1.0

    def test_flat_obs_size_matches_space_with_marketing(self):
        """Flat observation shape matches the declared observation space."""
        env = _make_env(marketing_config=_MARKETING_CFG)
        obs, _ = env.reset(seed=42)
        for agent in env.agents:
            assert obs[agent].shape == env.observation_space(agent).shape


class TestDcLeakAgentGate:
    """
    DC-spend leaks are gated on agent count; BE leaks are not.

    A DC action boosts a *public* per-indication demand multiplier that is
    already in every agent's observation, so with few agents an opponent can
    attribute a rise to the only other spender for free — the leak is
    redundant. It activates only from ``dc_leak_min_agents`` upward, so future
    multi-agent (>2) iterations get DC leaks automatically without re-adding.
    """

    @staticmethod
    def _step_all_dc(env):
        """Reset, take one all-on demand-creation step, return the shared market."""
        env.reset(seed=7)
        n_ind_slots = env.max_indications_per_ta * len(THERAPEUTIC_AREAS)
        actions = {
            agent: {
                "investments": np.zeros(env.max_num_assets, dtype=np.int64),
                "bd_bids": np.zeros(env.bd_max_slots, dtype=np.int64),
                "demand_creation": np.ones(n_ind_slots, dtype=np.int64),
                "brand_equity": np.zeros(env.max_num_assets, dtype=np.int64),
            }
            for agent in env.agents
        }
        env.step(actions)
        return env.multi_agent_game.shared_market

    @staticmethod
    def _dc_alerts(shared_market):
        return [a for a in shared_market.alerts if a.event_type == AlertType.DC_SPEND]

    @staticmethod
    def _obs_has_dc_alert(env, agent):
        """True if any alert slot in ``agent``'s flat obs is a DC_SPEND one-hot."""
        layout = env._layout
        # Use the env's live per-indication feature count: with marketing enabled
        # it is one wider (demand_multiplier) than the base _INDICATION_FEATURES.
        alert_start = (
            layout.global_features
            + env.max_num_assets * layout.asset_total_features
            + env.bd_max_slots * _BD_OBS_FEATURES_PER_SLOT
            + len(THERAPEUTIC_AREAS)
            * env.max_indications_per_ta
            * env._indication_features
        )
        obs = env._get_observation_flat(agent)
        # DC_SPEND one-hot sits at +5 within each alert slot.
        return any(
            obs[alert_start + i * _ALERT_FEATURES + 5] == 1.0
            for i in range(env.max_alerts)
        )

    def test_dc_leak_suppressed_below_threshold(self):
        """2 agents (default threshold 3): DC spend leaks nothing."""
        env = _make_env(
            num_agents=2,
            marketing_config=_MARKETING_CFG,
            dc_leak_probability=1.0,  # would always fire if not gated
            starting_cash=50_000_000_000.0,
        )
        market = self._step_all_dc(env)
        assert env.multi_agent_game.dc_leak_min_agents == 3
        assert self._dc_alerts(market) == []

    def test_dc_leak_active_at_threshold(self):
        """3 agents reach the default threshold: DC spend now leaks."""
        env = _make_env(
            num_agents=3,
            marketing_config=_MARKETING_CFG,
            dc_leak_probability=1.0,
            starting_cash=50_000_000_000.0,
        )
        assert len(self._dc_alerts(self._step_all_dc(env))) > 0

    def test_dc_leak_threshold_is_configurable(self):
        """Lowering the threshold to 2 forces DC leaks on in a 2-agent game."""
        env = _make_env(
            num_agents=2,
            marketing_config=_MARKETING_CFG,
            dc_leak_probability=1.0,
            dc_leak_min_agents=2,
            starting_cash=50_000_000_000.0,
        )
        market = self._step_all_dc(env)
        assert env.multi_agent_game.dc_leak_min_agents == 2
        assert len(self._dc_alerts(market)) > 0

    def test_threshold_survives_step_reconstruction(self):
        """The gate is carried through each step's game reconstruction."""
        env = _make_env(
            num_agents=2,
            marketing_config=_MARKETING_CFG,
            dc_leak_probability=1.0,
            dc_leak_min_agents=2,
            starting_cash=50_000_000_000.0,
        )
        self._step_all_dc(env)
        # A second step must still see the configured (non-default) threshold.
        assert env.multi_agent_game.dc_leak_min_agents == 2

    def test_dc_alert_absent_from_opponent_obs_below_threshold(self):
        """End-to-end: below threshold, no opponent's observation carries a DC alert."""
        env = _make_env(
            num_agents=2,
            marketing_config=_MARKETING_CFG,
            dc_leak_probability=1.0,
            starting_cash=50_000_000_000.0,
        )
        self._step_all_dc(env)
        assert not any(self._obs_has_dc_alert(env, a) for a in env.agents)

    def test_dc_alert_present_in_opponent_obs_at_threshold(self):
        """End-to-end: at threshold, the DC leak surfaces in an opponent's obs."""
        env = _make_env(
            num_agents=3,
            marketing_config=_MARKETING_CFG,
            dc_leak_probability=1.0,
            starting_cash=50_000_000_000.0,
        )
        self._step_all_dc(env)
        assert any(self._obs_has_dc_alert(env, a) for a in env.agents)


_BD_READINGS_CFG = PtrsReadingsConfig(
    enabled=True,
    cost_fraction=0.01,
    cost_rounding=1,
    action_space_max_readings=3,
    sigma_logit_base=1.5,
    sigma_ep=None,
    noise_multipliers=[1.0, 1.5, 2.0],
    max_sample_obs=20,
)


def _make_bd_readings_env(bd_persist_steps=4, flatten_obs=False, **kwargs):
    return _make_env(
        bd_enabled=True,
        bd_max_slots=2,
        bd_persist_steps=bd_persist_steps,
        bd_min_step=0,
        bd_base_lambda=3.0,
        starting_cash=10_000_000_000,
        horizon=12,
        ptrs_readings_config=_BD_READINGS_CFG,
        flatten_obs=flatten_obs,
        **kwargs,
    )


def _bd_research_actions(env, n, agent):
    """Return actions for `agent` commissioning `n` readings on every occupied BD slot."""
    n_live = len(env.multi_agent_game.shared_market.current_bd_assets)
    action = env.noop_action()
    action["ptrs_research"][env.max_num_assets : env.max_num_assets + n_live] = n
    return action


def test_capture_shared_market_uses_configured_reinvestment_rate():
    """
    Replay capture serializes BD cash_enpv at the game's reinvestment rate.

    Regression: capture_shared_market called bd_asset_to_response without the
    reinvestment rate, so cash_enpv fell back to the 0.10 default instead of the
    configured value (flagged in PR #57 review). The live response path passes
    the rate; the replay-capture path must too.
    """
    from pyxis_portfolio_challenge.environment.playthrough import (
        capture_shared_market,
    )

    env = _make_bd_readings_env(num_agents=2)
    obs, _ = env.reset(seed=1)

    for _ in range(8):
        if env.multi_agent_game.shared_market.current_bd_assets:
            break
        blank = {agent: env.noop_action() for agent in env.agents}
        obs, *_ = env.step(blank)
    else:
        pytest.skip("No BD asset appeared within 8 steps")

    reinv_pct = env.reinvestment_percentage
    assert reinv_pct != pytest.approx(0.10), (
        "Test env reinvestment rate coincides with the buggy 0.10 default; "
        "the regression check would be vacuous"
    )

    snapshot = capture_shared_market(env.multi_agent_game)
    assert snapshot.bd_assets, "capture produced no BD assets to check"

    by_id = {
        str(a.id): a for a in env.multi_agent_game.shared_market.current_bd_assets
    }
    # Every serialized BD asset must price cash_enpv at the configured rate.
    for bd in snapshot.bd_assets:
        shared = by_id[str(bd["asset_id"])]
        assert bd["cash_enpv"] == pytest.approx(shared.cash_enpv(reinv_pct))

    # Guard against a vacuous test: at least one asset's value must actually
    # differ from the buggy 0.10 fallback (i.e. it has positive cash flows).
    distinguishing = any(
        by_id[str(bd["asset_id"])].cash_enpv(reinv_pct)
        != pytest.approx(by_id[str(bd["asset_id"])].cash_enpv(0.10))
        for bd in snapshot.bd_assets
    )
    if not distinguishing:
        pytest.skip("BD assets have no positive cash flows; rate indistinguishable")


def test_capture_actions_stores_decoded_gbp_bid_amount():
    """
    Replay capture stores BD bids in GBP, matching the auction's units.

    Regression: capture_actions stored the raw action (GBP millions), so a £25M
    bid was recorded as 25 and the frontend rendered it as "£25" (flagged in
    PR #57 review). Passing the env decoder stores the decoded GBP amount, which
    the frontend's GBP formatter then renders as "£25.0M".
    """
    from pyxis_portfolio_challenge.environment.playthrough import capture_actions

    env = _make_env()
    raw_actions = {
        "pharma_0": {
            "investments": np.zeros(env.max_num_assets, dtype=np.int64),
            "bd_bids": np.array([25, 0], dtype=np.int64),
        }
    }

    # With the env decoder: bids are stored in GBP (25 million -> 25_000_000).
    records = capture_actions(
        raw_actions,
        {"pharma_0": []},
        use_investment_levels=False,
        bd_bid_decoder=env._decode_bd_bids,
    )
    assert records["pharma_0"].bd_bids == [25_000_000, 0]

    # Legacy path (no decoder) leaves the raw GBP-millions value unchanged.
    legacy = capture_actions(
        raw_actions,
        {"pharma_0": []},
        use_investment_levels=False,
    )
    assert legacy["pharma_0"].bd_bids == [25, 0]


def test_bd_auction_skips_bidder_bankrupted_by_earlier_slot():
    """
    A bidder bankrupted on an earlier slot must not strand a later asset.

    Regression: ``won_asset_ids`` was updated before the winner's
    ``game_ended`` check, so a bidder who bankrupted acquiring an earlier slot
    could still be declared winner of a later slot — removing that asset from
    the market without ever adding it to a portfolio or paying for it.
    """
    import uuid

    from pyxis_portfolio_challenge.game.asset import DrugAsset
    from pyxis_portfolio_challenge.game.trial import (
        Trial,
        TrialPhase,
        TrialState,
    )

    def _bd_asset(name):
        return DrugAsset(
            id=uuid.uuid4(),
            name=name,
            therapeutic_area="oncology",
            type="BD",
            description="",
            max_revenue=1_000_000.0,
            raw_max_revenue=1_000_000.0,
            time_until_max_revenue=5,
            time_until_patent_expiry=20,
            state=AssetState.Idle,
            time_on_market=0,
            trial=Trial(
                cost_remaining=1.0,
                time_remaining=1,
                ptrs=0.5,
                phase=TrialPhase.PHASE_1,
                state=TrialState.PENDING,
                next_trial_on_success=None,
            ),
            indication=0,
        )

    env = _make_bd_readings_env(num_agents=2, bd_persist_steps=5)
    env.reset(seed=7)
    game = env.multi_agent_game

    # Replace the market with exactly two fresh BD assets, one per slot.
    market = game.shared_market
    market.current_bd_assets.clear()
    market.bd_asset_ages.clear()
    asset0 = _bd_asset("bd-slot-0")
    asset1 = _bd_asset("bd-slot-1")
    for a in (asset0, asset1):
        market.current_bd_assets.append(a)
        market.bd_asset_ages[str(a.id)] = 0

    # Give the aggressor only enough cash that winning slot 0 bankrupts them
    # before slot 1 is resolved; they nonetheless bid on both slots.
    aggressor, passive = env.agents[0], env.agents[1]
    game.agent_states[aggressor].cash = 100.0

    investor_actions = {a: {} for a in env.agents}
    bd_bids = {
        aggressor: [200.0, 50.0],  # slot 0 bankrupts (100 - 200 < 0)
        passive: [0.0, 0.0],  # passes on both slots
    }

    new_game = game.step(investor_actions, bd_bids=bd_bids)

    winner_state = new_game.agent_states[aggressor]
    assert winner_state.game_ended, "aggressor should have bankrupted on slot 0"
    assert asset0.id in winner_state.assets, "slot 0 should have been acquired"
    assert asset1.id not in winner_state.assets, "slot 1 must not be acquired"

    # asset1 had no live bidder, so it must remain in the market rather than
    # disappearing (removed as "won" but never acquired or paid for).
    live_ids = {a.id for a in new_game.shared_market.current_bd_assets}
    assert asset1.id in live_ids, "unacquired slot-1 asset must stay in the market"


class TestBDReadingsPerAgent:
    """Tests for per-agent BD PTRS readings via _bd_asset_clones."""

    def test_bd_readings_per_agent_diverge(self):
        """
        Two agents commissioning different N readings diverge in ph0_ptrs / equiv_n_norm.

        spawn_bd_asset() runs at the END of each step, so a BD asset spawned in
        step 1 only appears in step 1's obs. Its asset ID isn't in
        pre_step_game.shared_market.current_bd_assets during step 1, so research
        actions referencing BD slots are silently dropped. We must wait until a BD
        asset appears in obs, THEN commission readings in the subsequent step.
        """
        env = _make_bd_readings_env(num_agents=2)
        obs, _ = env.reset(seed=1)

        agents = env.agents
        assert len(agents) == 2
        agent_a, agent_b = agents

        # Step until a BD asset appears in obs (spawn_bd_asset runs at end of each step)
        for _ in range(8):
            bd_a = obs[agent_a]["bd_market"]
            if any(slot["available"] == 1 for slot in bd_a):
                break
            blank = {agent: env.noop_action() for agent in env.agents}
            obs, *_ = env.step(blank)
        else:
            pytest.skip("No BD asset appeared within 8 steps")

        # A BD asset is now visible in obs. Its ID IS in pre_step_game.shared_market
        # for the NEXT step — commission diverging readings now.
        actions = {
            agent: _bd_research_actions(env, 3 if agent == agent_a else 1, agent)
            for agent in env.agents
        }
        obs, *_ = env.step(actions)

        bd_a = obs[agent_a]["bd_market"]
        bd_b = obs[agent_b]["bd_market"]
        occupied_slot = next(
            (i for i in range(env.bd_max_slots) if bd_a[i]["available"] == 1),
            None,
        )
        if occupied_slot is None:
            pytest.skip("BD asset left market before second obs was built")

        slot_a = bd_a[occupied_slot]
        slot_b = bd_b[occupied_slot]

        assert slot_a["ph0_equiv_n_norm"] > slot_b["ph0_equiv_n_norm"], (
            f"Agent with 3 readings should have higher equiv_n_norm than agent with 1; "
            f"got {slot_a['ph0_equiv_n_norm']:.4f} vs {slot_b['ph0_equiv_n_norm']:.4f}"
        )
        assert (
            slot_a["ph0_ptrs"] != slot_b["ph0_ptrs"]
            or slot_a["ph0_equiv_n_norm"] != slot_b["ph0_equiv_n_norm"]
        ), "Per-agent BD obs should diverge after different reading counts"

    def test_bd_ask_cash_enpv_is_public_anchor(self):
        """
        ask_cash_enpv stays identical across agents and tracks the shared asset.

        The BD asset's cash eNPV is a public fair-value anchor for a cash bid
        (see resolve_bd_bid), frozen at the public first reading. Once an agent
        commissions readings its obs `enpv` comes from its private clone, so
        without this feature the anchor would be unobservable. Assert the anchor
        is agent-invariant, equals the shared asset's cash_enpv, and genuinely
        differs from the agent's private posterior.
        """
        env = _make_bd_readings_env(num_agents=2)
        obs, _ = env.reset(seed=1)

        agent_a, agent_b = env.agents

        for _ in range(8):
            if any(slot["available"] == 1 for slot in obs[agent_a]["bd_market"]):
                break
            blank = {agent: env.noop_action() for agent in env.agents}
            obs, *_ = env.step(blank)
        else:
            pytest.skip("No BD asset appeared within 8 steps")

        # Diverging reading counts -> diverging private posteriors
        actions = {
            agent: _bd_research_actions(env, 3 if agent == agent_a else 1, agent)
            for agent in env.agents
        }
        obs, *_ = env.step(actions)

        bd_a = obs[agent_a]["bd_market"]
        bd_b = obs[agent_b]["bd_market"]
        shared_assets = env.multi_agent_game.shared_market.current_bd_assets
        occupied_slot = next(
            (
                i
                for i in range(min(env.bd_max_slots, len(shared_assets)))
                if bd_a[i]["available"] == 1
            ),
            None,
        )
        if occupied_slot is None:
            pytest.skip("BD asset left market before second obs was built")

        slot_a = bd_a[occupied_slot]
        slot_b = bd_b[occupied_slot]
        shared = shared_assets[occupied_slot]
        reinv_pct = env.reinvestment_percentage
        expected = shared.cash_enpv(reinv_pct)

        # 1. Agent-invariant despite different reading counts
        assert slot_a["ask_cash_enpv"] == pytest.approx(slot_b["ask_cash_enpv"]), (
            f"Price anchor must be identical for all agents; got "
            f"{slot_a['ask_cash_enpv']:,.2f} vs {slot_b['ask_cash_enpv']:,.2f}"
        )

        # 2. Matches the shared asset the auction actually prices off
        assert slot_a["ask_cash_enpv"] == pytest.approx(expected), (
            f"Anchor {slot_a['ask_cash_enpv']:,.2f} != shared cash_enpv "
            f"{expected:,.2f}"
        )

        # 3. The anchor is NOT the agent's private posterior — otherwise the
        #    feature would be redundant and the price would leak private belief.
        clone = env.multi_agent_game.agent_states[agent_a]._bd_asset_clones.get(
            str(shared.id)
        )
        if clone is not None:
            private = clone.cash_enpv(reinv_pct)
            assert private != pytest.approx(expected), (
                "Agent's private clone cash_enpv coincided with the public anchor; "
                "readings did not move the posterior, so the test is vacuous"
            )

    def test_bd_ask_cash_enpv_absent_when_readings_disabled(self):
        """No anchor feature (and no obs-width change) when ptrs_readings is off."""
        env = _make_env(
            bd_enabled=True,
            bd_max_slots=2,
            bd_persist_steps=4,
            bd_min_step=0,
            bd_base_lambda=3.0,
            horizon=6,
            flatten_obs=False,
        )
        obs, _ = env.reset(seed=3)
        assert env._bd_obs_size == _BD_OBS_FEATURES_PER_SLOT
        for slot in obs[env.agents[0]]["bd_market"]:
            assert "ask_cash_enpv" not in slot

    def test_bd_clone_pruned_after_asset_leaves(self):
        """_bd_asset_clones is empty once a BD asset is no longer on the market."""
        env = _make_bd_readings_env(num_agents=2, bd_persist_steps=2)
        env.reset(seed=5)

        # Commission readings for several steps so clones are created
        for _ in range(3):
            actions = {
                agent: _bd_research_actions(env, 2, agent)
                for agent in env.agents
            }
            env.step(actions)

        # After bd_persist_steps=2, clones for expired assets should be pruned
        live_bd_ids = {
            str(a.id)
            for a in env.multi_agent_game.shared_market.current_bd_assets
        }
        for agent in env.possible_agents:
            gs = env.multi_agent_game.agent_states[agent]
            stale = set(gs._bd_asset_clones) - live_bd_ids
            assert not stale, (
                f"Agent {agent} has stale clones for IDs not on market: {stale}"
            )

    def test_dict_matches_flat_bd_with_readings(self):
        """
        flatten_dict_obs → unflatten_to_dict_obs round-trips the BD section.

        Uses a single env in dict mode so the two code paths (dict builder and
        flatten_dict_obs + unflatten_to_dict_obs) operate on the same game state.
        This avoids any cross-env RNG divergence from BD asset spawning.
        """
        env = _make_bd_readings_env()
        obs, _ = env.reset(seed=7)

        for step in range(6):
            actions = {
                agent: _bd_research_actions(env, 2, agent)
                for agent in env.agents
            }
            obs, *_ = env.step(actions)

            for agent in env.possible_agents:
                dict_obs = obs[agent]
                flat = env.flatten_dict_obs(dict_obs)
                roundtripped = env.unflatten_to_dict_obs(flat)

                for slot_i, (orig, back) in enumerate(
                    zip(dict_obs["bd_market"], roundtripped["bd_market"])
                ):
                    for key in orig:
                        assert key in back, (
                            f"Key '{key}' missing from roundtripped BD slot {slot_i} "
                            f"for {agent} at step {step + 1}"
                        )
                        # flatten_dict_obs uses float32; large-magnitude values (enpv,
                        # eroi) lose precision (~1 part in 1e5). Use rtol=1e-4 to
                        # accommodate float32 rounding while still catching wrong fields.
                        assert orig[key] == pytest.approx(
                            back[key], rel=1e-4, abs=1e-6
                        ), (
                            f"BD slot {slot_i} key '{key}' mismatch for {agent} at step {step + 1}: "
                            f"{orig[key]} vs {back[key]}"
                        )

    def test_bd_winner_no_clone(self):
        """Winner of BD auction has no clone — asset is in their portfolio instead."""
        env = _make_bd_readings_env(num_agents=2, bd_persist_steps=5)
        env.reset(seed=3)

        # Run a few steps so a BD asset appears and clones can form
        for step_i in range(5):
            bd_assets = env.multi_agent_game.shared_market.current_bd_assets
            if not bd_assets:
                actions = {agent: env.noop_action() for agent in env.agents}
                env.step(actions)
                continue

            # Commission readings then bid on slot 0
            agent = env.agents[0]

            def _winner_action(a):
                action = env.noop_action()
                if a == agent:
                    action["bd_bids"][0] = _BD_WINNING_BID
                    action["ptrs_research"][env.max_num_assets] = 2
                return action

            actions = {a: _winner_action(a) for a in env.agents}
            env.step(actions)

            # Check whether agent won the asset (it's now in their portfolio)
            gs = env.multi_agent_game.agent_states[agent]
            asset_ids_in_portfolio = {str(aid) for aid in gs.assets}
            live_bd_ids = {
                str(a.id)
                for a in env.multi_agent_game.shared_market.current_bd_assets
            }
            # Any clone for a won asset should be gone (it's not in live_bd_ids)
            stale = set(gs._bd_asset_clones) - live_bd_ids
            assert not stale, (
                f"Clone persisted for won BD asset: {stale}"
            )
            if asset_ids_in_portfolio:
                return  # agent won at least one asset; test passed

        # If we never won, just assert no stale clones — the prune logic still ran
        for agent in env.possible_agents:
            gs = env.multi_agent_game.agent_states[agent]
            live_bd_ids = {
                str(a.id)
                for a in env.multi_agent_game.shared_market.current_bd_assets
            }
            stale = set(gs._bd_asset_clones) - live_bd_ids
            assert not stale

    def test_clone_pruned_when_won_by_other_agent(self):
        """
        Agent A's clone is pruned when agent B wins the BD auction.

        Agent A commissions readings (creating a clone) but does not bid.
        Agent B bids at max level. After the step where B wins, the asset
        leaves current_bd_assets → live_bd_ids filter prunes A's clone.
        """
        env = _make_bd_readings_env(num_agents=2, bd_persist_steps=8)
        obs, _ = env.reset(seed=9)

        agents = env.agents
        assert len(agents) == 2
        agent_a, agent_b = agents[0], agents[1]

        # Wait until a BD asset appears in obs so it's in pre_step_game next step
        for _ in range(12):
            bd_a = obs[agent_a]["bd_market"]
            if any(slot["available"] == 1 for slot in bd_a):
                break
            blank = {a: env.noop_action() for a in env.agents}
            obs, *_ = env.step(blank)
        else:
            pytest.skip("No BD asset appeared within 12 steps")

        # Identify first occupied slot
        bd_assets = env.multi_agent_game.shared_market.current_bd_assets
        if not bd_assets:
            pytest.skip("No BD assets on market")
        target_id = str(bd_assets[0].id)

        # Agent A commissions readings (no bid), agent B bids max on slot 0
        action_a = env.noop_action()
        action_a["ptrs_research"][env.max_num_assets] = 2  # slot 0

        action_b = env.noop_action()
        action_b["bd_bids"][0] = _BD_WINNING_BID

        actions = {agent_a: action_a, agent_b: action_b}
        env.step(actions)

        # If agent B won, target asset is no longer in current_bd_assets
        # and agent A's clone should have been pruned
        live_bd_ids = {
            str(a.id) for a in env.multi_agent_game.shared_market.current_bd_assets
        }
        gs_a = env.multi_agent_game.agent_states[agent_a]
        gs_b = env.multi_agent_game.agent_states[agent_b]

        if target_id not in live_bd_ids:
            # Asset left market — either B won or expired; A's clone must be gone
            assert target_id not in gs_a._bd_asset_clones, (
                f"Agent A's clone for {target_id} persisted after asset left market"
            )
            assert target_id not in gs_b._bd_asset_clones, (
                f"Agent B's clone for {target_id} persisted after asset left market"
            )
        else:
            # Asset still on market (B didn't win this round); A's clone is fine
            # The test still validates no *stale* clones exist
            stale_a = set(gs_a._bd_asset_clones) - live_bd_ids
            assert not stale_a, f"Agent A has stale clones: {stale_a}"

    # ------------------------------------------------------------------
    # Precision-level BD clone lifecycle tests
    # ------------------------------------------------------------------

    # Precision added per reading for ph0 (noise_multiplier[0] = 1.0):
    # 1 / (sigma_base * 1.0)^2 = 1 / 1.5^2 = 1/2.25  (exact, deterministic)
    _PRECISION_PER_READING = 1.0 / (_BD_READINGS_CFG.sigma_logit_base ** 2)

    @staticmethod
    def _ph0_precision(asset) -> float | None:
        """ptrs_total_precision of the first (ph0) trial in the pending chain."""
        chain = asset.pending_trial_chain
        return chain[0].ptrs_total_precision if chain else None

    @staticmethod
    def _wait_for_n_bd_assets(env, n, max_steps=25):
        """Step with blank actions until ≥n BD assets appear; return True on success."""
        for _ in range(max_steps):
            if len(env.multi_agent_game.shared_market.current_bd_assets) >= n:
                return True
            blank = {a: env.noop_action() for a in env.agents}
            env.step(blank)
        return len(env.multi_agent_game.shared_market.current_bd_assets) >= n

    def test_phase0_preserves_unwon_slot_clone_existence(self):
        """
        Winning slot 0 must NOT destroy the clone for slot 1.

        Before the Phase 0 fix the GameState constructor for the winner reset
        _bd_asset_clones to {}, silently losing all other-slot clones.
        """
        env = _make_bd_readings_env(num_agents=2, bd_persist_steps=12)
        env.reset(seed=17)

        if not self._wait_for_n_bd_assets(env, 2):
            pytest.skip("Never got 2 BD assets simultaneously")

        bd_assets = env.multi_agent_game.shared_market.current_bd_assets
        win_id = str(bd_assets[0].id)
        keep_id = str(bd_assets[1].id)

        # Build clones for both slots over 2 prep steps
        for _ in range(2):
            obs, *_ = env.step({a: _bd_research_actions(env, 2, a) for a in env.agents})

        agent_a = env.agents[0]
        gs_a = env.multi_agent_game.agent_states[agent_a]

        if win_id not in gs_a._bd_asset_clones or keep_id not in gs_a._bd_asset_clones:
            pytest.skip("One of the expected clones was not built (asset may have moved)")

        # Winning step: agent A bids max on slot 0, no bid on slot 1
        bd_now = env.multi_agent_game.shared_market.current_bd_assets
        win_slot = next((i for i, a in enumerate(bd_now) if str(a.id) == win_id), None)
        if win_slot is None:
            pytest.skip("Win-target left market before winning step")

        action_a = env.noop_action()
        action_a["bd_bids"][win_slot] = _BD_WINNING_BID
        env.step({
            agent_a: action_a,
            env.agents[1]: env.noop_action(),
        })

        gs_a_new = env.multi_agent_game.agent_states[agent_a]
        won = win_id in {str(aid) for aid in gs_a_new.assets}
        if not won:
            pytest.skip("Agent A did not win (negative-enpv asset or cash issue)")

        # Won asset's clone must be gone
        assert win_id not in gs_a_new._bd_asset_clones, (
            "Clone for won asset should be dropped from _bd_asset_clones"
        )
        # Other slot's clone must survive (if still on market)
        live_ids = {str(a.id) for a in env.multi_agent_game.shared_market.current_bd_assets}
        if keep_id in live_ids:
            assert keep_id in gs_a_new._bd_asset_clones, (
                "Clone for unwon slot was lost when agent won a different slot — "
                "Phase 0 _bd_asset_clones propagation missing"
            )

    def test_phase0_preserves_unwon_slot_clone_accumulated_precision(self):
        """
        Winning slot 0 preserves the ACCUMULATED precision of the slot 1 clone.

        ptrs_total_precision accumulates exactly 1/sigma² per reading (deterministic).
        If the Phase 0 fix is absent, the slot 1 clone is discarded and recreated
        from scratch in Pt.4 — precision would equal (1 + N_win) / sigma² instead of
        the accumulated (1 + N_prep*steps + N_win) / sigma².
        """
        env = _make_bd_readings_env(num_agents=2, bd_persist_steps=12)
        env.reset(seed=17)

        if not self._wait_for_n_bd_assets(env, 2):
            pytest.skip("Never got 2 BD assets simultaneously")

        bd_assets = env.multi_agent_game.shared_market.current_bd_assets
        win_id = str(bd_assets[0].id)
        keep_id = str(bd_assets[1].id)

        N_PREP, N_STEPS, N_WIN = 2, 2, 1  # readings per prep step, prep steps, win-step readings
        p = self._PRECISION_PER_READING

        # Prep: build up clone precision on the "keep" slot only
        for _ in range(N_STEPS):
            bd_now = env.multi_agent_game.shared_market.current_bd_assets
            keep_slot = next((i for i, a in enumerate(bd_now) if str(a.id) == keep_id), None)
            if keep_slot is None:
                pytest.skip("Keep-slot asset left market during prep")
            def _prep_action(_a):
                action = env.noop_action()
                action["ptrs_research"][env.max_num_assets + keep_slot] = N_PREP
                return action

            env.step({a: _prep_action(a) for a in env.agents})

        agent_a = env.agents[0]
        gs_a = env.multi_agent_game.agent_states[agent_a]

        if keep_id not in gs_a._bd_asset_clones:
            pytest.skip("Keep-slot clone not built")
        precision_before = self._ph0_precision(gs_a._bd_asset_clones[keep_id])
        if precision_before is None:
            pytest.skip("Keep-slot clone has no pending trial chain")

        # After N_STEPS * N_PREP readings on top of the 1 initial pseudo-reading:
        expected_before = (1 + N_STEPS * N_PREP) * p
        assert precision_before == pytest.approx(expected_before, rel=1e-6), (
            f"Unexpected accumulated precision before win: {precision_before:.6f} "
            f"(expected {expected_before:.6f})"
        )

        # Winning step: bid max on slot 0 + N_WIN readings on slot 1
        bd_now = env.multi_agent_game.shared_market.current_bd_assets
        win_slot = next((i for i, a in enumerate(bd_now) if str(a.id) == win_id), None)
        keep_slot = next((i for i, a in enumerate(bd_now) if str(a.id) == keep_id), None)
        if win_slot is None or keep_slot is None:
            pytest.skip("A target asset left market before winning step")

        action_a = env.noop_action()
        action_a["bd_bids"][win_slot] = _BD_WINNING_BID
        action_a["ptrs_research"][env.max_num_assets + keep_slot] = N_WIN
        env.step({
            agent_a: action_a,
            env.agents[1]: env.noop_action(),
        })

        gs_a_new = env.multi_agent_game.agent_states[agent_a]
        if win_id not in {str(aid) for aid in gs_a_new.assets}:
            pytest.skip("Agent A did not win slot 0")

        live_ids = {str(a.id) for a in env.multi_agent_game.shared_market.current_bd_assets}
        if keep_id not in live_ids:
            pytest.skip("Keep-slot asset left market during winning step")

        assert keep_id in gs_a_new._bd_asset_clones
        precision_after = self._ph0_precision(gs_a_new._bd_asset_clones[keep_id])
        assert precision_after is not None

        expected_after = (1 + N_STEPS * N_PREP + N_WIN) * p
        stale_would_give = (1 + N_WIN) * p  # clone reset to fresh = only win-step readings
        assert precision_after == pytest.approx(expected_after, rel=1e-6), (
            f"Clone precision {precision_after:.6f} != expected {expected_after:.6f}. "
            f"If it equals {stale_would_give:.6f} the Phase 0 fix is missing."
        )

    def test_same_step_readings_on_won_asset_applied_to_portfolio(self):
        """
        Readings commissioned in the same step as winning are applied to the portfolio asset.

        Phase 0 adds the BD asset to the winner's portfolio BEFORE GameState.step()
        runs Pt.4, so the research_actions handler finds it in assets_for_step and
        treats it as a normal portfolio reading.
        """
        env = _make_bd_readings_env(num_agents=2, bd_persist_steps=10)
        env.reset(seed=7)

        if not self._wait_for_n_bd_assets(env, 1):
            pytest.skip("No BD asset appeared")

        bd_assets = env.multi_agent_game.shared_market.current_bd_assets
        target_asset = bd_assets[0]
        target_id = str(target_asset.id)

        # Initial precision on a freshly spawned BD asset = 1 * (1/sigma²)
        # from the single pseudo-reading applied by initialise_ptrs_readings()
        p = self._PRECISION_PER_READING
        initial_chain = target_asset.pending_trial_chain
        if not initial_chain:
            pytest.skip("BD asset has no pending trial chain")
        assert initial_chain[0].ptrs_total_precision == pytest.approx(p, rel=1e-6)

        # Bid max + commission N readings in the SAME step
        N = 3
        agent_a = env.agents[0]
        action_a = env.noop_action()
        action_a["bd_bids"][0] = _BD_WINNING_BID
        action_a["ptrs_research"][env.max_num_assets] = N  # slot 0
        env.step({
            agent_a: action_a,
            env.agents[1]: env.noop_action(),
        })

        gs_a = env.multi_agent_game.agent_states[agent_a]
        portfolio_asset = gs_a.assets.get(target_asset.id)
        if portfolio_asset is None:
            pytest.skip("Agent A did not win the BD asset")

        chain = portfolio_asset.pending_trial_chain
        assert chain, "Won portfolio asset should have a pending trial chain"
        precision = chain[0].ptrs_total_precision
        expected = (1 + N) * p
        assert precision == pytest.approx(expected, rel=1e-6), (
            f"Portfolio asset precision {precision:.6f} != expected {expected:.6f}. "
            f"Same-step readings should have been applied via the portfolio path."
        )
        # Also confirm no clone for this asset remains
        assert target_id not in gs_a._bd_asset_clones

    def test_bd_clone_precision_grows_across_steps(self):
        """
        Commissioning N readings per step for K steps accumulates exactly
        (1 + K*N) / sigma² precision on the BD clone's ph0 trial.

        ptrs_total_precision = initial (1 pseudo-reading) + K*N readings, all at
        1/sigma² each.  This test verifies multi-step accumulation is monotonic
        and lands at the exact expected value after each step.
        """
        env = _make_bd_readings_env(num_agents=1, bd_persist_steps=12)
        env.reset(seed=3)

        if not self._wait_for_n_bd_assets(env, 1):
            pytest.skip("No BD asset appeared")

        bd_assets = env.multi_agent_game.shared_market.current_bd_assets
        target_id = str(bd_assets[0].id)

        p = self._PRECISION_PER_READING
        N_PER_STEP = 2
        agent = env.agents[0]

        prev_precision = p  # starts at 1 * p after initialise_ptrs_readings()

        for step_k in range(1, 5):
            bd_now = env.multi_agent_game.shared_market.current_bd_assets
            slot = next((i for i, a in enumerate(bd_now) if str(a.id) == target_id), None)
            if slot is None:
                pytest.skip(f"BD asset left market at step {step_k}")

            action = env.noop_action()
            action["ptrs_research"][env.max_num_assets + slot] = N_PER_STEP
            env.step({agent: action})

            gs = env.multi_agent_game.agent_states[agent]
            if target_id not in gs._bd_asset_clones:
                pytest.skip(f"Clone for target asset missing after step {step_k}")

            precision = self._ph0_precision(gs._bd_asset_clones[target_id])
            if precision is None:
                pytest.skip("Clone has no pending trial chain")

            expected = (1 + step_k * N_PER_STEP) * p
            assert precision == pytest.approx(expected, rel=1e-6), (
                f"After step {step_k}: precision {precision:.6f} != {expected:.6f}"
            )
            assert precision > prev_precision, (
                f"Precision did not increase at step {step_k}: {precision:.6f} <= {prev_precision:.6f}"
            )
            prev_precision = precision

    def test_two_agents_different_reading_rates_see_different_clone_precision(self):
        """
        Two agents commissioning different numbers of readings on the same BD
        asset end up with clones of different ptrs_total_precision.

        Agent A reads N_A per step, agent B reads N_B per step (N_A > N_B).
        After K steps: A's precision = (1 + K*N_A) / sigma² > B's = (1 + K*N_B) / sigma².
        These are exact, deterministic values regardless of the noisy samples.
        """
        env = _make_bd_readings_env(num_agents=2, bd_persist_steps=12)
        env.reset(seed=5)

        agent_a, agent_b = env.agents[0], env.agents[1]

        if not self._wait_for_n_bd_assets(env, 1):
            pytest.skip("No BD asset appeared")

        bd_assets = env.multi_agent_game.shared_market.current_bd_assets
        target_id = str(bd_assets[0].id)

        p = self._PRECISION_PER_READING
        N_A, N_B = 3, 1   # A reads more aggressively than B
        K = 3              # steps of diverging readings

        for step_k in range(1, K + 1):
            bd_now = env.multi_agent_game.shared_market.current_bd_assets
            slot = next((i for i, a in enumerate(bd_now) if str(a.id) == target_id), None)
            if slot is None:
                pytest.skip(f"BD asset left market at step {step_k}")

            def _research_action(n):
                action = env.noop_action()
                action["ptrs_research"][env.max_num_assets + slot] = n
                return action

            env.step({
                agent_a: _research_action(N_A),
                agent_b: _research_action(N_B),
            })

            gs_a = env.multi_agent_game.agent_states[agent_a]
            gs_b = env.multi_agent_game.agent_states[agent_b]

            if target_id not in gs_a._bd_asset_clones or target_id not in gs_b._bd_asset_clones:
                pytest.skip(f"Clone missing at step {step_k}")

            prec_a = self._ph0_precision(gs_a._bd_asset_clones[target_id])
            prec_b = self._ph0_precision(gs_b._bd_asset_clones[target_id])
            if prec_a is None or prec_b is None:
                pytest.skip("Clone has no pending trial chain")

            expected_a = (1 + step_k * N_A) * p
            expected_b = (1 + step_k * N_B) * p

            assert prec_a == pytest.approx(expected_a, rel=1e-6), (
                f"Step {step_k}: agent A precision {prec_a:.6f} != {expected_a:.6f}"
            )
            assert prec_b == pytest.approx(expected_b, rel=1e-6), (
                f"Step {step_k}: agent B precision {prec_b:.6f} != {expected_b:.6f}"
            )
            assert prec_a > prec_b, (
                f"Step {step_k}: agent A ({prec_a:.6f}) should have higher precision "
                f"than B ({prec_b:.6f}) given N_A={N_A} > N_B={N_B}"
            )


class TestDisableMarketShareCompetition:
    def test_disabled_returns_full_share(self):
        env = _make_env(disable_market_share_competition=True)
        env.reset(seed=42)

        shares = calculate_agent_market_shares(
            "pharma_0",
            env.multi_agent_game.shared_market,
            env.agent_portfolios,
            0,
        )
        # With competition disabled, all on-market drugs get share 1.0
        for share in shares.values():
            assert share == 1.0


_ENABLED_DROP_ACTION = DropActionConfig(
    enabled=True, drop_price_fraction=0.25, drop_price_rounding=1_000_000
)


def _make_drop_env(**kwargs):
    """Multi-agent env with the drop action enabled."""
    return _make_env(drop_action_config=_ENABLED_DROP_ACTION, **kwargs)


class TestDropAction:
    def test_action_space_is_ternary(self):
        env = _make_drop_env()
        space = env.action_space(env.possible_agents[0])
        inv_space = space["investments"]
        assert isinstance(inv_space, gym.spaces.MultiDiscrete)
        assert list(inv_space.nvec) == [3] * env.max_num_assets

    def test_action_space_binary_without_drop_action(self):
        env = _make_env()
        space = env.action_space(env.possible_agents[0])
        assert isinstance(space["investments"], gym.spaces.MultiBinary)

    def test_investment_masks_are_ternary(self):
        env = _make_drop_env()
        env.reset(seed=42)

        for agent in env.agents:
            masks = env.action_masks(agent)["investments"]
            assert len(masks) == env.max_num_assets
            assert all(len(m) == 3 for m in masks)

    def test_masks_reflect_asset_state(self):
        env = _make_drop_env()
        env.reset(seed=42)

        checked_idle = False
        for agent in env.agents:
            masks = env.action_masks(agent)["investments"]
            game_state = env.agent_portfolios[agent]
            asset_order = env._asset_id_orders[agent]

            for i, mask in enumerate(masks):
                asset_id = asset_order[i] if i < len(asset_order) else None
                if asset_id is None or asset_id not in game_state.assets:
                    assert mask == [True, False, False]
                    continue
                asset = game_state.assets[asset_id]
                assert mask[0] is True
                assert mask[2] is True  # affordable: masking is off by default
                if asset.state == AssetState.Idle:
                    checked_idle = True
                else:
                    assert mask[1] is False

        assert checked_idle, "Expected at least one Idle asset after reset"

    def test_drop_masked_when_fee_unaffordable(self):
        env = _make_drop_env(mask_first_order_assets=True)
        env.reset(seed=42)

        agent = env.agents[0]
        game_state = env.agent_portfolios[agent]
        asset_order = env._asset_id_orders[agent]

        index, asset_id = next(
            (i, aid)
            for i, aid in enumerate(asset_order)
            if aid is not None
            and aid in game_state.assets
            and env._drop_fee(game_state.assets[aid]) > 0
        )
        fee = env._drop_fee(game_state.assets[asset_id])

        env.agent_portfolios[agent] = game_state.model_copy(update={"cash": fee})
        assert env.action_masks(agent)["investments"][index][2] is True

        env.agent_portfolios[agent] = game_state.model_copy(update={"cash": fee - 1.0})
        assert env.action_masks(agent)["investments"][index][2] is False

    def test_drop_not_masked_when_masking_disabled(self):
        env = _make_drop_env(mask_first_order_assets=False)
        env.reset(seed=42)

        agent = env.agents[0]
        game_state = env.agent_portfolios[agent]
        env.agent_portfolios[agent] = game_state.model_copy(update={"cash": 0.0})
        asset_order = env._asset_id_orders[agent]

        for i, mask in enumerate(env.action_masks(agent)["investments"]):
            asset_id = asset_order[i] if i < len(asset_order) else None
            if asset_id is not None and asset_id in env.agent_portfolios[agent].assets:
                assert mask[2] is True

    def test_step_with_drop_removes_asset(self):
        env = _make_drop_env()
        env.reset(seed=42)

        agent = env.agents[0]
        asset_order = env._asset_id_orders[agent]
        index, target_id = next(
            (i, aid)
            for i, aid in enumerate(asset_order)
            if aid is not None and aid in env.agent_portfolios[agent].assets
        )

        actions = {
            a: {
                "investments": np.zeros(env.max_num_assets, dtype=np.int64),
                "bd_bids": np.zeros(env.bd_max_slots, dtype=np.int64),
            }
            for a in env.agents
        }
        actions[agent]["investments"][index] = 2

        env.step(actions)

        portfolio = env.agent_portfolios[agent]
        assert target_id in portfolio.dropped_assets
        assert target_id not in portfolio.assets

    def test_mutually_exclusive_with_investment_levels(self):
        enabled_levels = InvestmentLevelsConfig(
            enabled=True,
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
        with pytest.raises(ValueError, match="mutually exclusive"):
            _make_env(
                investment_levels_config=enabled_levels,
                drop_action_config=_ENABLED_DROP_ACTION,
            )


class TestWarmupClockRebase:
    """
    Warmup acts as a pre-roll: the agent's clock resets to 0 and it
    plays a full horizon (total sim = warmup + horizon).
    """

    WARMUP = 7
    HORIZON = 20

    def _wrapped_env(self, **kwargs):
        base = _make_env(horizon=self.HORIZON, **kwargs)
        return MultiAgentWarmupOnResetWrapper(
            base, warmup_steps=self.WARMUP, policy="do_nothing", verbose=False
        )

    def _do_nothing_actions(self, env):
        return {
            a: {
                "investments": np.zeros(env.max_num_assets, dtype=np.int8),
                "bd_bids": np.zeros(env.bd_max_slots, dtype=np.int64),
            }
            for a in env.agents
        }

    def test_reset_rebases_all_clocks_to_zero(self):
        env = self._wrapped_env(bd_enabled=True, bd_min_step=0)
        obs, _ = env.reset(seed=42)

        game = env.multi_agent_game
        assert game.time == 0
        assert game.shared_market.time == 0
        assert all(state.time == 0 for state in game.agent_states.values())
        # Global observation slot 1 is the game clock.
        assert all(obs[agent][1] == 0 for agent in env.agents)

    def test_agent_plays_full_horizon_after_warmup(self):
        env = self._wrapped_env()
        env.reset(seed=42)

        steps = 0
        done = False
        while not done and steps <= self.HORIZON + 5:
            _, _, terms, truncs, _ = env.step(self._do_nothing_actions(env))
            steps += 1
            done = not env.agents or all(terms.values()) or all(truncs.values())

        assert steps == self.HORIZON
        assert env.multi_agent_game.time == self.HORIZON

    def test_warmup_exceeding_horizon_does_not_error(self):
        """
        Warmup far larger than horizon must not raise and still gives a full
        horizon (warmup_steps and horizon are additive).
        """
        base = _make_env(horizon=10)
        env = MultiAgentWarmupOnResetWrapper(
            base, warmup_steps=25, policy="do_nothing", verbose=False
        )
        obs, _ = env.reset(seed=42)

        # Clock rebased to 0 and horizon restored to the configured value.
        game = env.multi_agent_game
        assert game.time == 0
        assert game.horizon == 10
        assert all(state.horizon == 10 for state in game.agent_states.values())
        assert all(obs[agent][1] == 0 for agent in env.agents)

        steps = 0
        done = False
        while not done and steps <= 15:
            _, _, terms, truncs, _ = env.step(self._do_nothing_actions(env))
            steps += 1
            done = not env.agents or all(terms.values()) or all(truncs.values())

        assert steps == 10
        assert env.multi_agent_game.time == 10

    def test_with_horizon_sets_game_and_state_horizons(self):
        """with_horizon sets both the game-level and every per-agent horizon."""
        env = _make_env(horizon=self.HORIZON)
        env.reset(seed=42)
        game = env.multi_agent_game.with_horizon(self.HORIZON + 5)
        assert game.horizon == self.HORIZON + 5
        assert all(
            state.horizon == self.HORIZON + 5 for state in game.agent_states.values()
        )

    def test_rebase_is_noop_at_time_zero(self):
        # A freshly initialised game (time 0) must rebase to itself unchanged.
        env = _make_env(horizon=self.HORIZON)
        env.reset(seed=42)
        game = env.multi_agent_game
        assert game.rebase_time_to_zero() is game

    def test_shared_market_rebase_shifts_alert_and_exclusivity(self):
        # Directly exercise the market rebase with synthetic stamped state so
        # the alert/exclusivity shift is covered even though do_nothing warmup
        # never produces them.
        env = _make_env(horizon=self.HORIZON)
        env.reset(seed=42)
        market = env.multi_agent_game.shared_market
        market.time = 10
        market.add_alert(
            Alert(
                step=8,
                event_type=AlertType.DRUG_RELEASE,
                agent_id="pharma_0",
                therapeutic_area=THERAPEUTIC_AREAS[0],
            )
        )
        ta_market = market.ta_markets[THERAPEUTIC_AREAS[0]]
        ta_market.exclusivity_start_time = 9

        market.rebase_time_to_zero()

        assert market.time == 0
        assert market.alerts[0].step == 8 - 10
        assert ta_market.exclusivity_start_time == 9 - 10
class TestClinicalSiteAuction:
    """Game-level PvP clinical-site auction through MultiAgentGame.step."""

    @staticmethod
    def _sites_env():
        return _make_env(
            num_agents=2,
            clinical_sites_config=ClinicalSitesConfig(
                enabled=True,
                starting_sites=3,
                auction_enabled=True,
                auction_interval_steps=1,
                auction_min_step=0,
                purchase_base_cost=500_000_000,
                purchase_cost_rounding=1_000_000,
                site_development_steps=2,
                agent_priority=False,
                priority_entropy_weight=1.0,
                site_max_bid=100_000,
            ),
        )

    def test_highest_bidder_wins_immediately_operational_site(self):
        env = self._sites_env()
        env.reset(seed=0)
        game = env.multi_agent_game
        assert game.shared_market.site_auction_available() is True
        a, b = env.agents

        new_game = game.step(
            investor_actions={a: {}, b: {}},
            site_bids={a: 5_000_000.0, b: 1_000_000.0},
        )
        # Baseline: identical step with no bids isolates the auction charge from
        # market revenue collected during the step.
        base_env = self._sites_env()
        base_env.reset(seed=0)
        base_game = base_env.multi_agent_game.step(
            investor_actions={a: {}, b: {}}, site_bids={a: 0.0, b: 0.0}
        )

        # Winner gained an immediately-operational site and paid its bid.
        assert new_game.agent_states[a].operational_sites == 4
        assert new_game.agent_states[a].sites_in_development == []
        assert new_game.agent_states[a].cash == pytest.approx(
            base_game.agent_states[a].cash - 5_000_000.0
        )
        # Loser unchanged (still 3 sites) and not charged.
        assert new_game.agent_states[b].operational_sites == 3
        assert new_game.agent_states[b].cash == pytest.approx(
            base_game.agent_states[b].cash
        )
        # Winning price is broadcast to the opponent via the alert feed.
        deals = [
            al
            for al in new_game.shared_market.get_alerts_for_agent(b)
            if al.event_type == AlertType.CLINICAL_SITE_DEAL
        ]
        assert len(deals) == 1
        assert deals[0].details["price"] == pytest.approx(5_000_000.0)

    def test_no_bids_no_deal(self):
        env = self._sites_env()
        env.reset(seed=0)
        game = env.multi_agent_game
        a, b = env.agents
        new_game = game.step(
            investor_actions={a: {}, b: {}}, site_bids={a: 0.0, b: 0.0}
        )
        assert new_game.agent_states[a].operational_sites == 3
        assert new_game.agent_states[b].operational_sites == 3

    def test_no_auction_when_not_scheduled(self):
        env = _make_env(
            num_agents=2,
            clinical_sites_config=ClinicalSitesConfig(
                enabled=True,
                starting_sites=3,
                auction_enabled=True,
                auction_interval_steps=20,
                auction_min_step=5,
                purchase_base_cost=500_000_000,
                purchase_cost_rounding=1_000_000,
                site_development_steps=2,
                agent_priority=False,
                priority_entropy_weight=1.0,
                site_max_bid=100_000,
            ),
        )
        env.reset(seed=0)
        game = env.multi_agent_game
        assert game.shared_market.site_auction_available() is False
        a, b = env.agents
        # Bids submitted off-cadence are ignored -> no site granted, no charge.
        new_game = game.step(
            investor_actions={a: {}, b: {}},
            site_bids={a: 9_000_000.0, b: 1_000_000.0},
        )
        base_env = _make_env(
            num_agents=2,
            clinical_sites_config=ClinicalSitesConfig(
                enabled=True,
                starting_sites=3,
                auction_enabled=True,
                auction_interval_steps=20,
                auction_min_step=5,
                purchase_base_cost=500_000_000,
                purchase_cost_rounding=1_000_000,
                site_development_steps=2,
                agent_priority=False,
                priority_entropy_weight=1.0,
                site_max_bid=100_000,
            ),
        )
        base_env.reset(seed=0)
        base_game = base_env.multi_agent_game.step(investor_actions={a: {}, b: {}})
        assert new_game.agent_states[a].operational_sites == 3
        assert new_game.agent_states[a].cash == pytest.approx(
            base_game.agent_states[a].cash
        )


# ---------------------------------------------------------------------------
# Phase 4: continuous clinical-site action + observation wiring at the env
# level (the game-level mechanics are covered in tests/game/test_clinical_sites)
# ---------------------------------------------------------------------------

_SITE_FEATURES = 4  # operational, free, in_development, auction_active


def _sites_env(*, flatten_obs=True, starting_cash=None, **cfg_kwargs):
    """Env with clinical sites enabled; cfg_kwargs override the site config."""
    site_defaults = dict(
        enabled=True,
        starting_sites=3,
        auction_enabled=False,
        purchase_base_cost=500_000_000,
        purchase_cost_rounding=1_000_000,
        site_development_steps=2,
        agent_priority=False,
        priority_entropy_weight=1.0,
        auction_interval_steps=20,
        auction_min_step=10,
        site_max_bid=100_000,
    )
    site_defaults.update(cfg_kwargs)
    env_kwargs = dict(num_agents=2, flatten_obs=flatten_obs)
    if starting_cash is not None:
        env_kwargs["starting_cash"] = starting_cash
    return _make_env(
        clinical_sites_config=ClinicalSitesConfig(**site_defaults),
        **env_kwargs,
    )


class TestClinicalSiteObservation:
    def test_layout_offset_and_feature_count(self):
        env = _sites_env()
        layout = env._layout
        assert layout.clinical_sites_enabled is True
        assert layout.num_site_features == _SITE_FEATURES
        assert layout.offset_clinical_sites >= 0

    def test_no_site_features_when_disabled(self):
        env = _make_env()
        layout = env._layout
        assert layout.clinical_sites_enabled is False
        assert layout.num_site_features == 0
        assert layout.offset_clinical_sites == -1

    def test_obs_size_grows_by_site_feature_count(self):
        base = _make_env(num_agents=2)
        withsites = _sites_env()
        assert withsites._obs_size - base._obs_size == _SITE_FEATURES

    def test_flat_obs_exposes_site_features(self):
        env = _sites_env(starting_sites=3)
        obs, _ = env.reset(seed=0)
        off = env._layout.offset_clinical_sites
        a = env.agents[0]
        feats = obs[a][off : off + _SITE_FEATURES]
        # operational=3, free=3 (nothing in development yet), in_dev=0,
        # auction inactive (auction disabled).
        np.testing.assert_allclose(feats, [3.0, 3.0, 0.0, 0.0])

    def test_flat_obs_auction_active_flag(self):
        env = _sites_env(
            auction_enabled=True, auction_interval_steps=1, auction_min_step=0
        )
        obs, _ = env.reset(seed=0)
        off = env._layout.offset_clinical_sites
        a = env.agents[0]
        # An auction is live on step 0 -> the auction_active feature is set.
        assert obs[a][off + 3] == pytest.approx(1.0)

    def test_dict_obs_site_structure(self):
        env = _sites_env(flatten_obs=False)
        obs, _ = env.reset(seed=0)
        a = env.agents[0]
        sites = obs[a]["clinical_sites"]
        assert float(np.ravel(sites["operational_sites"])[0]) == pytest.approx(3.0)
        assert float(np.ravel(sites["free_sites"])[0]) == pytest.approx(3.0)

    def test_dict_matches_flat_with_sites(self):
        env_dict = _sites_env(flatten_obs=False)
        dict_obs, _ = env_dict.reset(seed=42)
        env_flat = _sites_env(flatten_obs=True)
        flat_obs, _ = env_flat.reset(seed=42)
        for agent in env_dict.possible_agents:
            dict_as_flat = env_dict.flatten_dict_obs(dict_obs[agent])
            np.testing.assert_allclose(
                flat_obs[agent], dict_as_flat, atol=1e-6
            )


class TestClinicalSiteActionSpace:
    def test_action_space_has_upgrade_head(self):
        env = _sites_env()
        space = env.action_space(env.possible_agents[0])
        assert "upgrade" in space.spaces
        assert isinstance(space.spaces["upgrade"], gym.spaces.Discrete)
        assert space.spaces["upgrade"].n == 2

    def test_action_space_site_bid_is_continuous_box(self):
        env = _sites_env(auction_enabled=True, site_max_bid=100_000)
        space = env.action_space(env.possible_agents[0])
        bid = space.spaces["site_bid"]
        assert isinstance(bid, gym.spaces.Box)
        assert bid.shape == (1,)
        assert float(bid.high[0]) == pytest.approx(100_000.0)

    def test_action_space_priority_head_when_enabled(self):
        env = _sites_env(agent_priority=True)
        space = env.action_space(env.possible_agents[0])
        prio = space.spaces["site_priority"]
        assert isinstance(prio, gym.spaces.Box)
        assert prio.shape == (env.max_num_assets,)

    def test_action_space_omits_site_heads_when_disabled(self):
        env = _make_env()
        space = env.action_space(env.possible_agents[0])
        assert "upgrade" not in space.spaces
        assert "site_bid" not in space.spaces
        assert "site_priority" not in space.spaces

    def test_upgrade_mask_off_when_unaffordable(self):
        # Default base cost (£500M) dwarfs the £10M starting cash.
        env = _sites_env(starting_sites=3, purchase_base_cost=500_000_000)
        env.reset(seed=0)
        masks = env.action_masks(env.agents[0])
        assert masks["upgrade"] == [True, False]

    def test_upgrade_mask_on_when_affordable(self):
        env = _sites_env(starting_sites=3, purchase_base_cost=1_000_000)
        env.reset(seed=0)
        masks = env.action_masks(env.agents[0])
        assert masks["upgrade"] == [True, True]


class TestClinicalSiteDecodeBid:
    def test_rounds_to_nearest_million_and_scales(self):
        env = _sites_env(auction_enabled=True, site_max_bid=100_000)
        env.reset(seed=0)
        assert env._decode_site_bid(5.4) == pytest.approx(5_000_000.0)
        assert env._decode_site_bid(5.6) == pytest.approx(6_000_000.0)

    def test_negative_is_a_pass(self):
        env = _sites_env(auction_enabled=True, site_max_bid=100_000)
        env.reset(seed=0)
        assert env._decode_site_bid(-3.0) == pytest.approx(0.0)

    def test_clips_to_max_bid(self):
        env = _sites_env(auction_enabled=True, site_max_bid=100)
        env.reset(seed=0)
        assert env._decode_site_bid(500.0) == pytest.approx(100_000_000.0)

    def test_accepts_array_action(self):
        env = _sites_env(auction_enabled=True, site_max_bid=100_000)
        env.reset(seed=0)
        assert env._decode_site_bid(np.array([7.0])) == pytest.approx(7_000_000.0)


class TestClinicalSiteEnvStep:
    @staticmethod
    def _do_nothing(env):
        return env.noop_action()

    def test_upgrade_action_starts_a_site_build(self):
        env = _sites_env(starting_sites=3, purchase_base_cost=1_000_000)
        env.reset(seed=0)
        a, b = env.agents
        action = self._do_nothing(env)
        action["upgrade"] = 1
        env.step({a: action, b: self._do_nothing(env)})
        state = env.multi_agent_game.agent_states[a]
        # Purchased site enters the build pipeline, not immediately operational.
        assert state.operational_sites == 3
        assert len(state.sites_in_development) == 1
        assert state.total_sites_owned == 4
        # Opponent, which did not upgrade, is unchanged.
        other = env.multi_agent_game.agent_states[b]
        assert other.operational_sites == 3
        assert other.sites_in_development == []

    def test_upgrade_unaffordable_is_noop(self):
        env = _sites_env(starting_sites=3, purchase_base_cost=500_000_000)
        env.reset(seed=0)
        a, b = env.agents
        action = self._do_nothing(env)
        action["upgrade"] = 1  # requested but cannot afford
        env.step({a: action, b: self._do_nothing(env)})
        state = env.multi_agent_game.agent_states[a]
        assert state.operational_sites == 3
        assert state.sites_in_development == []

    def test_site_bid_via_env_step_wins_auction(self):
        env = _sites_env(
            starting_sites=3,
            auction_enabled=True,
            auction_interval_steps=1,
            auction_min_step=0,
            site_max_bid=100_000,
        )
        env.reset(seed=0)
        a, b = env.agents
        assert env.multi_agent_game.shared_market.site_auction_available() is True
        winner = self._do_nothing(env)
        winner["site_bid"] = np.array([5.0], dtype=np.float32)  # £5M
        loser = self._do_nothing(env)
        loser["site_bid"] = np.array([1.0], dtype=np.float32)  # £1M
        env.step({a: winner, b: loser})
        # Highest bidder gets an immediately-operational site.
        assert env.multi_agent_game.agent_states[a].operational_sites == 4
        assert env.multi_agent_game.agent_states[b].operational_sites == 3

    def test_priority_action_routes_scarce_site(self):
        env = _make_env(
            num_agents=2,
            starting_cash=10_000_000_000.0,
            clinical_sites_config=ClinicalSitesConfig(
                enabled=True,
                starting_sites=1,
                auction_enabled=False,
                agent_priority=True,
                purchase_base_cost=500_000_000,
                purchase_cost_rounding=1_000_000,
                site_development_steps=2,
                priority_entropy_weight=1.0,
                auction_interval_steps=20,
                auction_min_step=10,
                site_max_bid=100_000,
            ),
        )
        env.reset(seed=0)
        a, b = env.agents
        mask = np.asarray(env.action_masks(a)["investments"])
        idle = list(np.where(mask == 1)[0])
        assert len(idle) >= 2  # need an over-request to exercise the gate
        i0, i1 = idle[0], idle[1]
        order = env._asset_id_orders[a]
        favoured_id, other_id = order[i1], order[i0]

        inv = np.zeros(env.max_num_assets, dtype=np.int8)
        inv[i0] = 1
        inv[i1] = 1
        prio = np.zeros(env.max_num_assets, dtype=np.float32)
        prio[i0] = 0.1
        prio[i1] = 0.9
        action = {
            "investments": inv,
            "bd_bids": np.zeros(env.bd_max_slots, dtype=np.float32),
            "upgrade": 0,
            "site_priority": prio,
        }
        env.step({a: action, b: self._do_nothing(env)})
        assets = env.multi_agent_game.agent_states[a].assets
        # The single free site goes to the higher-priority asset; the other
        # request is a costless no-op (stays Idle).
        assert assets[favoured_id].state == AssetState.InDevelopment
        assert assets[other_id].state == AssetState.Idle


_ENABLED_PRICING = PricingConfig(
    enabled=True,
    levels=[0.60, 0.75, 1.00, 1.20, 1.40, 1.60],
    default_level=2,
    elasticity=2.0,
)
_ENABLED_INVESTMENT_LEVELS = InvestmentLevelsConfig(
    enabled=True,
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
)
_ENABLED_TA_EXPERIENCE = TAExperienceConfig(
    enabled=True,
    experience_to_full_knowledge=30.0,
    max_expertise_boost=0.05,
    experience_to_max_boost=40.0,
    experience_decay_rate=0.98,
    max_total_experience=60.0,
    phase_experience_weights={
        "phase_1": 0.5, "phase_2": 1.0, "phase_3": 1.5, "approval": 0.5,
    },
    asset_arrival_temperature=0.1,
)


class TestActionSpaceFeatureVariants:
    """
    Each feature's action head appears in action_space() exactly when its
    config is enabled, and is absent when disabled. This locks the
    action-space shape to the ``.enabled`` gate (never to config presence).
    """

    def _agent(self, env):
        return env.possible_agents[0]

    def test_ptrs_research_head_present_when_enabled(self):
        env = _make_env(ptrs_readings_config=_BD_READINGS_CFG)
        space = env.action_space(self._agent(env))
        assert "ptrs_research" in space.spaces
        assert "ptrs_research" in env.enabled_action_heads()
        n_slots = env.max_num_assets + env.bd_max_slots
        assert list(space.spaces["ptrs_research"].nvec) == (
            [_BD_READINGS_CFG.action_space_max_readings + 1] * n_slots
        )

    def test_ptrs_research_head_absent_when_disabled(self):
        env = _make_env()  # ptrs disabled by default
        space = env.action_space(self._agent(env))
        assert "ptrs_research" not in space.spaces
        assert "ptrs_research" not in env.enabled_action_heads()

    def test_pricing_head_present_when_enabled(self):
        env = _make_env(pricing_config=_ENABLED_PRICING)
        space = env.action_space(self._agent(env))
        assert "pricing" in space.spaces
        assert "pricing" in env.enabled_action_heads()
        assert list(space.spaces["pricing"].nvec) == (
            [len(_ENABLED_PRICING.levels)] * env.max_num_assets
        )

    def test_pricing_head_absent_when_disabled(self):
        env = _make_env()  # pricing disabled by default
        space = env.action_space(self._agent(env))
        assert "pricing" not in space.spaces
        assert "pricing" not in env.enabled_action_heads()

    def test_investment_levels_action_space_when_enabled(self):
        env = _make_env(investment_levels_config=_ENABLED_INVESTMENT_LEVELS)
        space = env.action_space(self._agent(env))
        inv = space.spaces["investments"]
        assert isinstance(inv, gym.spaces.MultiDiscrete)
        assert list(inv.nvec) == [len(InvestmentLevel)] * env.max_num_assets

    def test_investments_binary_when_no_levels_or_drop(self):
        env = _make_env()
        space = env.action_space(self._agent(env))
        assert isinstance(space.spaces["investments"], gym.spaces.MultiBinary)

    def test_enabled_heads_match_action_space_keys_default(self):
        env = _make_env()
        space = env.action_space(self._agent(env))
        assert set(env.enabled_action_heads()) == set(space.spaces.keys())

    def test_enabled_heads_match_action_space_keys_all_on(self):
        env = _make_env(
            ptrs_readings_config=_BD_READINGS_CFG,
            pricing_config=_ENABLED_PRICING,
            marketing_config=_MARKETING_CFG,
        )
        space = env.action_space(self._agent(env))
        assert set(env.enabled_action_heads()) == set(space.spaces.keys())


class TestObsSpaceFeatureVariants:
    """Obs-space Dict keys track each feature's ``.enabled`` gate."""

    def _agent(self, env):
        return env.possible_agents[0]

    def test_ta_experience_obs_present_when_enabled(self):
        env = _make_env(flatten_obs=False, ta_experience_config=_ENABLED_TA_EXPERIENCE)
        space = env.observation_space(self._agent(env))
        assert "ta_experience" in space.spaces

    def test_ta_experience_obs_absent_when_disabled(self):
        env = _make_env(flatten_obs=False)  # ta_experience disabled by default
        space = env.observation_space(self._agent(env))
        assert "ta_experience" not in space.spaces

    def test_clinical_sites_obs_present_when_enabled(self):
        env = _sites_env(flatten_obs=False)
        space = env.observation_space(self._agent(env))
        assert "clinical_sites" in space.spaces

    def test_clinical_sites_obs_absent_when_disabled(self):
        env = _make_env(flatten_obs=False)  # clinical_sites disabled by default
        space = env.observation_space(self._agent(env))
        assert "clinical_sites" not in space.spaces
