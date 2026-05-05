"""Benchmark: PPO trained model vs Knapsack using multi_agent_evaluate."""

import json
import logging
import pickle
import sys
from pathlib import Path

import click
import numpy as np

from aiml_pyxis_investment_game import PROJECT_ROOT, logging_utils
from aiml_pyxis_investment_game.config import config, instantiate_from_config
from aiml_pyxis_investment_game.environment.multi_agent_evaluate import (
    evaluate_multi_agent,
)

logging_utils.setup_logging(logging.WARNING)

sys.path.insert(0, str(PROJECT_ROOT / "benchmark_agents" / "agents"))
from multi_agent_knapsack import MultiAgentKnapsackAgent


def _build_env_kwargs():
    """Build env_kwargs from central config."""
    cfg = config
    ma = cfg.multi_agent
    return dict(
        assets_dir=cfg.evaluation_data_dir,
        num_agents=ma.num_agents,
        starting_cash=cfg.starting_cash,
        max_num_assets=cfg.max_num_assets,
        horizon=cfg.horizon,
        equilibrium_num_assets=cfg.equilibrium_num_assets,
        asset_arrival_sensitivity_below=cfg.asset_arrival_sensitivity_below,
        asset_arrival_sensitivity_above=cfg.asset_arrival_sensitivity_above,
        reinvestment_percentage=cfg.reinvestment_percentage,
        bd_enabled=ma.bd_enabled,
        bd_assets_dir=ma.bd_assets_dir,
        bd_base_lambda=ma.bd_base_lambda,
        bd_leak_lambda_boost=ma.bd_leak_lambda_boost,
        bd_min_step=ma.bd_min_step,
        bd_num_bid_levels=ma.bd_num_bid_levels,
        bd_break_even_bid_level=ma.bd_break_even_bid_level,
        bd_max_slots=ma.bd_max_slots,
        bd_phase_weights=list(ma.bd_phase_weights),
        bd_indication_activity_bias=ma.bd_indication_activity_bias,
        exclusivity_period=ma.exclusivity_period,
        first_mover_bonus=ma.first_mover_bonus,
        disable_market_share_competition=ma.disable_market_share_competition,
        alert_history_length=ma.alert_history_length,
        leak_phase_probabilities=list(ma.leak_phase_probabilities),
        alerts_per_agent=ma.alerts_per_agent,
        reward_fn=instantiate_from_config(cfg.reward_fn),
        shuffle_order=False,
        mask_first_order_assets=cfg.mask_first_order_assets,
        mask_negative_enpv_assets=cfg.mask_negative_enpv_assets,
        flatten_obs=cfg.flatten_obs,
        distributional_ptrs_config=cfg.distributional_ptrs,
        ta_experience_config=cfg.ta_experience,
        uncertain_ptrs_config=cfg.uncertain_ptrs,
        investment_levels_config=cfg.investment_levels,
        rd_capacity_config=cfg.rd_capacity,
        interim_trial_observations_config=cfg.interim_trial_observations,
        approval_phase_config=cfg.approval_phase,
        reward_type=ma.reward_type,
        reward_scale=ma.reward_scale,
        max_indications_per_ta=ma.max_indications_per_ta,
        target_drugs_per_indication=ma.target_drugs_per_indication,
        on_market_fraction=ma.on_market_fraction,
        indication_spread=ma.indication_spread,
        indication_drift_speed=ma.indication_drift_speed,
        trial_cost_multiplier=cfg.trial_cost_multiplier,
        congestion_exponent=ma.congestion_exponent,
        congestion_ramp_steps=ma.congestion_ramp_steps,
        congestion_incumbent_penalty=ma.congestion_incumbent_penalty,
        pricing_config=cfg.pricing,
    )


class PPOAgent:
    """Wraps a MaskablePPO model for use in multi-agent evaluate."""

    def __init__(self, model, obs_rms_mean, obs_rms_var, env, agent_name):
        self.model = model
        self.obs_rms_mean = obs_rms_mean
        self.obs_rms_var = obs_rms_var
        self.env = env
        self.agent_name = agent_name

    def set_env(self, env):
        self.env = env

    def __call__(self, obs):
        norm_obs = (obs - self.obs_rms_mean) / np.sqrt(self.obs_rms_var + 1e-8)
        norm_obs = np.clip(norm_obs, -10.0, 10.0)

        masks = self.env.action_masks(self.agent_name)
        inv_mask = masks["investments"]
        bd_mask = masks["bd_bids"]

        parts = []
        if isinstance(inv_mask, list) and len(inv_mask) > 0 and isinstance(inv_mask[0], list):
            for slot in inv_mask:
                parts.extend(slot)
        else:
            for m in inv_mask:
                parts.extend([True, bool(m)])
        for slot in bd_mask:
            parts.extend(slot)
        flat_mask = np.array(parts, dtype=bool)

        action, _ = self.model.predict(
            norm_obs[np.newaxis],
            deterministic=True,
            action_masks=flat_mask[np.newaxis],
        )
        action = action.flatten()

        n_inv = self.env.max_num_assets
        n_bd = self.env.bd_max_slots
        return {
            "investments": action[:n_inv],
            "bd_bids": action[n_inv:n_inv + n_bd],
        }


@click.command()
@click.option("--model-dir", "-m", required=True, help="Path to experiment dir")
@click.option("--num-episodes", "-e", default=50, help="Number of episodes")
@click.option("--knapsack-bd/--no-knapsack-bd", default=True, help="Enable BD for knapsack")
@click.option("--knapsack-cap", "-c", default=None, type=int, help="Knapsack capacity override (e.g. 12)")
def main(model_dir, num_episodes, knapsack_bd, knapsack_cap):
    model_path = Path(model_dir) / "best_model" / "best_model.zip"
    vecnorm_path = Path(model_dir) / "best_model" / "vecnormalize.pkl"

    if not model_path.exists():
        print(f"Model not found: {model_path}")
        return

    from sb3_contrib import MaskablePPO

    print(f"Loading PPO model from {model_path}")
    model = MaskablePPO.load(str(model_path))
    with open(vecnorm_path, "rb") as f:
        vecnorm = pickle.load(f)
    obs_rms_mean = vecnorm.obs_rms.mean.copy()
    obs_rms_var = vecnorm.obs_rms.var.copy()

    # Build env to create agents (they need env reference for masks)
    from aiml_pyxis_investment_game.environment.multi_agent_training_gym import (
        MultiAgentInvestmentGameEnv,
    )
    from aiml_pyxis_investment_game.environment.warmup_wrapper import (
        MultiAgentWarmupOnResetWrapper,
    )

    env_kwargs = _build_env_kwargs()
    env = MultiAgentInvestmentGameEnv(**env_kwargs)

    cfg = config
    if cfg.warmup_on_reset_steps > 0:
        env = MultiAgentWarmupOnResetWrapper(
            env,
            warmup_steps=cfg.warmup_on_reset_steps,
            policy=cfg.warmup_on_reset_policy,
            verbose=False,
        )

    ppo_name = env.possible_agents[0]
    knapsack_name = env.possible_agents[1]

    ppo_agent = PPOAgent(model, obs_rms_mean, obs_rms_var, env, ppo_name)
    knapsack_agent = MultiAgentKnapsackAgent(
        env=env, agent_name=knapsack_name, enable_bd_bidding=knapsack_bd,
    )
    if knapsack_cap is not None:
        knapsack_agent._capacity_override = knapsack_cap

    agents = {ppo_name: ppo_agent, knapsack_name: knapsack_agent}

    # Override num_eval_episodes in config for this run
    original_num = cfg.num_eval_episodes
    object.__setattr__(cfg, "num_eval_episodes", num_episodes)

    cap_label = f"cap={knapsack_cap}" if knapsack_cap is not None else "uncapped"
    print(f"Running {num_episodes} episodes: PPO vs Knapsack ({cap_label}, bd={knapsack_bd})")

    agent_metrics, global_metrics, _ = evaluate_multi_agent(
        agents=agents,
        worker_id=0,
        episodes_per_worker=num_episodes,
        env_kwargs=env_kwargs,
        warmup_steps=cfg.warmup_on_reset_steps,
    )

    # Restore
    object.__setattr__(cfg, "num_eval_episodes", original_num)

    # Report
    from aiml_pyxis_investment_game.environment.metrics import report_all_metrics

    print("\n" + "=" * 80)
    print(f"PPO vs KNAPSACK  ({num_episodes} episodes, {cap_label}, knapsack_bd={knapsack_bd})")
    print("=" * 80)

    output_path = Path(model_dir) / "benchmark_vs_knapsack.json"
    serialisable = {}

    for agent_id, metrics in agent_metrics.items():
        label = "PPO" if agent_id == ppo_name else "KNAPSACK"
        report = report_all_metrics(metrics)
        serialisable[agent_id] = _serialise(report)

        # Print summary of per-episode metrics
        print(f"\n--- {label} ({agent_id}) ---")
        per_episode = report[1].get("PerEpisodeMetrics", [])
        for metric_dict in per_episode:
            for metric_name, episodes in metric_dict.items():
                if isinstance(episodes, dict):
                    values = [v for v in episodes.values() if isinstance(v, (int, float))]
                    if values:
                        arr = np.array(values, dtype=float)
                        print(f"  {metric_name}: "
                              f"mean={np.mean(arr):>14,.2f}  "
                              f"std={np.std(arr):>12,.2f}")

        per_eval = report[0].get("PerEvaluationMetrics", [])
        for metric_dict in per_eval:
            for metric_name, value in metric_dict.items():
                if isinstance(value, (int, float)):
                    print(f"  {metric_name}: {value:,.4f}")

    with open(output_path, "w") as f:
        json.dump(serialisable, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")


def _serialise(v):
    if isinstance(v, dict):
        return {k: _serialise(val) for k, val in v.items()}
    if isinstance(v, (np.floating, np.integer)):
        return float(v)
    if isinstance(v, list):
        return [_serialise(x) for x in v]
    return v


if __name__ == "__main__":
    main()
