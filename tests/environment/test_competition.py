"""Tests for multi-agent competition API (env.train(), Trainer, evaluate)."""

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
from aiml_pyxis_investment_game.environment.competition import (
    Trainer,
    _FlatObsAgentWrapper,
    _resolve_agent,
    _validate_flat_obs_overrides,
    train,
)
from aiml_pyxis_investment_game.environment.multi_agent_training_gym import (
    MultiAgentInvestmentGameEnv,
)
from aiml_pyxis_investment_game.environment.reward import NetCashFlowReward

TEST_ASSETS_DIR = upath.UPath("tests/data/generated_assets")


def _make_env(num_agents=2, **kwargs):
    """Helper to create a multi-agent env with test defaults."""
    defaults = dict(
        assets_dir=TEST_ASSETS_DIR,
        num_agents=num_agents,
        starting_cash=10_000_000.0,
        max_num_assets=15,
        horizon=10,
        equilibrium_num_assets=5,
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
        flatten_obs=False,
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


class TestResolveAgent:
    """Tests for named agent resolution."""

    def test_resolve_knapsack(self):
        agent = _resolve_agent("knapsack(c12)", "pharma_0")
        assert agent.agent_name == "pharma_0"
        assert hasattr(agent, "set_env")

    def test_resolve_random(self):
        agent = _resolve_agent("random", "pharma_1")
        assert agent.agent_name == "pharma_1"
        assert hasattr(agent, "set_env")

    def test_resolve_do_nothing(self):
        agent = _resolve_agent("do_nothing", "pharma_0")
        assert agent.agent_name == "pharma_0"
        assert hasattr(agent, "set_env")

    def test_resolve_callable_passthrough(self):
        fn = lambda obs: obs  # noqa: E731
        result = _resolve_agent(fn, "pharma_0")
        assert result is fn

    def test_resolve_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown agent 'bad_agent'"):
            _resolve_agent("bad_agent", "pharma_0")


class TestTrainer:
    """Tests for the Trainer gym.Env wrapper."""

    def test_trainer_is_gym_env(self):
        env = _make_env(num_agents=2)
        from aiml_pyxis_investment_game.agents.multi_agent_do_nothing import (
            MultiAgentDoNothingAgent,
        )

        opp = MultiAgentDoNothingAgent(agent_name="pharma_1")
        trainer = Trainer(env, trainee_index=0, opponents={"pharma_1": opp})
        assert isinstance(trainer, gym.Env)

    def test_trainer_spaces_match_env(self):
        env = _make_env(num_agents=2)
        from aiml_pyxis_investment_game.agents.multi_agent_do_nothing import (
            MultiAgentDoNothingAgent,
        )

        opp = MultiAgentDoNothingAgent(agent_name="pharma_1")
        trainer = Trainer(env, trainee_index=0, opponents={"pharma_1": opp})
        assert trainer.observation_space == env.observation_space("pharma_0")
        assert trainer.action_space == env.action_space("pharma_0")

    def test_trainer_reset_returns_dict_obs(self):
        env = _make_env(num_agents=2)
        from aiml_pyxis_investment_game.agents.multi_agent_do_nothing import (
            MultiAgentDoNothingAgent,
        )

        opp = MultiAgentDoNothingAgent(agent_name="pharma_1")
        trainer = Trainer(env, trainee_index=0, opponents={"pharma_1": opp})
        obs, info = trainer.reset(seed=42)
        assert isinstance(obs, dict)
        assert "cash" in obs
        assert isinstance(info, dict)

    def test_trainer_step_returns_five_tuple(self):
        env = _make_env(num_agents=2)
        from aiml_pyxis_investment_game.agents.multi_agent_do_nothing import (
            MultiAgentDoNothingAgent,
        )

        opp = MultiAgentDoNothingAgent(agent_name="pharma_1")
        trainer = Trainer(env, trainee_index=0, opponents={"pharma_1": opp})
        trainer.reset(seed=42)

        action = {
            "investments": np.zeros(env.max_num_assets, dtype=np.int64),
            "bd_bids": np.zeros(env.bd_max_slots, dtype=np.int64),
        }
        obs, reward, term, trunc, info = trainer.step(action)
        assert isinstance(obs, dict)
        assert isinstance(reward, (float, int, np.floating))
        assert isinstance(term, bool)
        assert isinstance(trunc, bool)
        assert isinstance(info, dict)

    def test_trainer_action_masks_returns_dict(self):
        env = _make_env(num_agents=2)
        from aiml_pyxis_investment_game.agents.multi_agent_do_nothing import (
            MultiAgentDoNothingAgent,
        )

        opp = MultiAgentDoNothingAgent(agent_name="pharma_1")
        trainer = Trainer(env, trainee_index=0, opponents={"pharma_1": opp})
        trainer.reset(seed=42)
        masks = trainer.action_masks()
        assert "investments" in masks
        assert "bd_bids" in masks

    def test_trainer_runs_full_episode(self):
        env = _make_env(num_agents=2, horizon=5)
        from aiml_pyxis_investment_game.agents.multi_agent_do_nothing import (
            MultiAgentDoNothingAgent,
        )

        opp = MultiAgentDoNothingAgent(agent_name="pharma_1")
        trainer = Trainer(env, trainee_index=0, opponents={"pharma_1": opp})
        trainer.reset(seed=42)

        done = False
        steps = 0
        while not done:
            action = {
                "investments": np.zeros(env.max_num_assets, dtype=np.int64),
                "bd_bids": np.zeros(env.bd_max_slots, dtype=np.int64),
            }
            _, _, term, trunc, _ = trainer.step(action)
            done = term or trunc
            steps += 1
        assert steps > 0

    def test_trainer_with_random_opponent(self):
        env = _make_env(num_agents=2)
        from aiml_pyxis_investment_game.agents.multi_agent_random import (
            MultiAgentRandomAgent,
        )

        opp = MultiAgentRandomAgent(agent_name="pharma_1")
        trainer = Trainer(env, trainee_index=0, opponents={"pharma_1": opp})
        obs, info = trainer.reset(seed=42)
        assert obs is not None

    def test_trainer_trainee_index_1(self):
        """Trainee can be any agent slot, not just index 0."""
        env = _make_env(num_agents=2)
        from aiml_pyxis_investment_game.agents.multi_agent_do_nothing import (
            MultiAgentDoNothingAgent,
        )

        opp = MultiAgentDoNothingAgent(agent_name="pharma_0")
        trainer = Trainer(env, trainee_index=1, opponents={"pharma_0": opp})
        assert trainer.trainee == "pharma_1"
        obs, info = trainer.reset(seed=42)
        assert obs is not None


class TestTrainFunction:
    """Tests for the train() function (attached to env as .train())."""

    def test_train_creates_trainer(self):
        env = _make_env(num_agents=2)
        trainer = train(env, [None, "do_nothing"])
        assert isinstance(trainer, Trainer)
        assert trainer.trainee == "pharma_0"

    def test_train_second_slot(self):
        env = _make_env(num_agents=2)
        trainer = train(env, ["do_nothing", None])
        assert isinstance(trainer, Trainer)
        assert trainer.trainee == "pharma_1"

    def test_train_wrong_length_raises(self):
        env = _make_env(num_agents=2)
        with pytest.raises(ValueError, match="Expected 2 agents"):
            train(env, [None])

    def test_train_no_none_raises(self):
        env = _make_env(num_agents=2)
        with pytest.raises(ValueError, match="Exactly one None"):
            train(env, ["do_nothing", "do_nothing"])

    def test_train_multiple_none_raises(self):
        env = _make_env(num_agents=2)
        with pytest.raises(ValueError, match="Exactly one None"):
            train(env, [None, None])

    def test_train_with_callable_opponent(self):
        env = _make_env(num_agents=2)
        from aiml_pyxis_investment_game.agents.multi_agent_do_nothing import (
            MultiAgentDoNothingAgent,
        )

        opp = MultiAgentDoNothingAgent(agent_name="pharma_1")
        trainer = train(env, [None, opp])
        assert isinstance(trainer, Trainer)

    def test_train_rejects_flat_obs_for_named(self):
        env = _make_env(num_agents=2)
        with pytest.raises(ValueError, match="Cannot override"):
            train(env, [None, "knapsack(c12)"], flat_obs={1: True})


class TestFlatObsHandling:
    """Tests for per-agent observation format handling."""

    def test_validate_rejects_override_for_named_agent(self):
        with pytest.raises(ValueError, match="Cannot override flat_obs"):
            _validate_flat_obs_overrides(
                ["knapsack(c12)", "do_nothing"],
                flat_obs={0: True},
            )

    def test_validate_allows_override_for_user_agent(self):
        my_agent = lambda obs: obs  # noqa: E731
        _validate_flat_obs_overrides([my_agent, "knapsack(c12)"], flat_obs={0: True})

    def test_validate_allows_no_overrides(self):
        _validate_flat_obs_overrides(["knapsack(c12)", "do_nothing"], flat_obs=None)

    def test_flat_obs_wrapper_flattens_dict_obs(self):
        env = _make_env(num_agents=2, flatten_obs=False)
        env.reset(seed=42)

        received_obs = []

        class FlatAgent:
            flat_obs = True

            def __init__(self):
                self.env = None

            def set_env(self, e):
                self.env = e

            def __call__(self, obs):
                received_obs.append(obs)
                return {
                    "investments": np.zeros(env.max_num_assets, dtype=np.int64),
                    "bd_bids": np.zeros(env.bd_max_slots, dtype=np.int64),
                }

        agent = FlatAgent()
        wrapper = _FlatObsAgentWrapper(agent, env)

        dict_obs, _ = env.reset(seed=42)
        wrapper(dict_obs["pharma_0"])

        assert len(received_obs) == 1
        assert isinstance(received_obs[0], np.ndarray)

    def test_trainer_flatten_trainee_obs(self):
        env = _make_env(num_agents=2, flatten_obs=False)
        from aiml_pyxis_investment_game.agents.multi_agent_do_nothing import (
            MultiAgentDoNothingAgent,
        )

        opp = MultiAgentDoNothingAgent(agent_name="pharma_1")
        trainer = Trainer(
            env, trainee_index=0, opponents={"pharma_1": opp},
            flatten_trainee_obs=True,
        )
        obs, info = trainer.reset(seed=42)
        assert isinstance(obs, np.ndarray)
        assert obs.ndim == 1

    def test_trainer_dict_trainee_obs(self):
        env = _make_env(num_agents=2, flatten_obs=False)
        from aiml_pyxis_investment_game.agents.multi_agent_do_nothing import (
            MultiAgentDoNothingAgent,
        )

        opp = MultiAgentDoNothingAgent(agent_name="pharma_1")
        trainer = Trainer(
            env, trainee_index=0, opponents={"pharma_1": opp},
            flatten_trainee_obs=False,
        )
        obs, info = trainer.reset(seed=42)
        assert isinstance(obs, dict)
        assert "cash" in obs

    def test_train_flat_obs_for_trainee(self):
        env = _make_env(num_agents=2, flatten_obs=False)
        trainer = train(env, [None, "do_nothing"], flat_obs={0: True})
        obs, info = trainer.reset(seed=42)
        assert isinstance(obs, np.ndarray)


class TestMakeMultiAgentTrainEnv:
    """Tests for make_multi_agent_train_env factory."""

    def test_creates_env_from_config(self):
        from aiml_pyxis_investment_game.environment.env_factory import (
            _build_multi_agent_env_kwargs,
        )

        kwargs = _build_multi_agent_env_kwargs(flatten_obs=True)
        assert kwargs["flatten_obs"] is True
        assert "assets_dir" in kwargs
        assert "num_agents" in kwargs
        assert "starting_cash" in kwargs
        assert "reward_fn" in kwargs
        assert "pricing_config" in kwargs

    def test_num_agents_override(self):
        from aiml_pyxis_investment_game.environment.env_factory import (
            _build_multi_agent_env_kwargs,
        )

        kwargs = _build_multi_agent_env_kwargs(flatten_obs=False, num_agents=3)
        assert kwargs["num_agents"] == 3
        assert kwargs["flatten_obs"] is False


class TestMultiAgentDoNothingAgent:
    """Tests for the core do-nothing agent."""

    def test_returns_zero_actions(self):
        from aiml_pyxis_investment_game.agents.multi_agent_do_nothing import (
            MultiAgentDoNothingAgent,
        )

        env = _make_env(num_agents=2)
        env.reset(seed=42)
        agent = MultiAgentDoNothingAgent(agent_name="pharma_0", env=env)
        action = agent(None)
        assert np.all(action["investments"] == 0)
        assert np.all(action["bd_bids"] == 0)


class TestMultiAgentRandomAgent:
    """Tests for the core random agent."""

    def test_returns_valid_actions(self):
        from aiml_pyxis_investment_game.agents.multi_agent_random import (
            MultiAgentRandomAgent,
        )

        env = _make_env(num_agents=2)
        env.reset(seed=42)
        agent = MultiAgentRandomAgent(agent_name="pharma_0", env=env)
        action = agent(None)
        assert "investments" in action
        assert "bd_bids" in action
        assert len(action["investments"]) == env.max_num_assets
        assert len(action["bd_bids"]) == env.bd_max_slots
