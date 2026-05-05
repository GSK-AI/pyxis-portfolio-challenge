"""
Validate that the core MultiAgentKnapsackAgent and MultiAgentPyxieAgent
produce results consistent with the strategic depth analysis.

Runs:
  1. cap12 vs cap12 (expect ~10-11B mean NCF, 0% bankruptcy)
  2. PPO vs cap12 Knapsack
"""

import json
import logging
import time

import numpy as np

from aiml_pyxis_investment_game import PROJECT_ROOT, logging_utils
from aiml_pyxis_investment_game.agents.multi_agent_knapsack import (
    MultiAgentKnapsackAgent,
)
from aiml_pyxis_investment_game.agents.multi_agent_pyxie import MultiAgentPyxieAgent
from aiml_pyxis_investment_game.config import config, instantiate_from_config
from aiml_pyxis_investment_game.environment.multi_agent_evaluate import (
    evaluate_multi_agent,
    parallel_evaluate_multi_agent,
)
from aiml_pyxis_investment_game.environment.multi_agent_training_gym import (
    MultiAgentInvestmentGameEnv,
)

logging_utils.setup_logging(logging.WARNING)

NUM_EPISODES = 25
NUM_WORKERS = 14


def _build_env_kwargs():
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
        shuffle_order=cfg.shuffle_order,
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
        target_drugs_per_indication=ma.target_drugs_per_indication,
        on_market_fraction=ma.on_market_fraction,
        max_indications_per_ta=ma.max_indications_per_ta,
        indication_spread=ma.indication_spread,
        indication_drift_speed=ma.indication_drift_speed,
        trial_cost_multiplier=cfg.trial_cost_multiplier,
        congestion_exponent=ma.congestion_exponent,
        congestion_ramp_steps=ma.congestion_ramp_steps,
        congestion_incumbent_penalty=ma.congestion_incumbent_penalty,
        pricing_config=cfg.pricing,
    )


def _extract_ncf_and_bankruptcy(report):
    """Extract mean NCF and bankruptcy rate from a metrics report."""
    # report_all_metrics returns [per_eval_dict, per_episode_dict, per_step_dict]
    per_eval = report[0]
    per_episode = report[1]
    mean_ncf = None
    bankruptcy_rate = None

    for metric_dict in per_eval.get("PerEvaluationMetrics", []):
        for name, value in metric_dict.items():
            if "NCF" in name or "CumulativeNCF" in name:
                mean_ncf = value
            if "bankruptcy" in name.lower():
                bankruptcy_rate = value

    if mean_ncf is None:
        for metric_dict in per_episode.get("PerEpisodeMetrics", []):
            for name, episodes in metric_dict.items():
                if "CumulativeReward" in name and isinstance(episodes, dict):
                    values = [
                        v
                        for v in episodes.values()
                        if isinstance(v, (int, float))
                    ]
                    if values:
                        mean_ncf = np.mean(values)

    return mean_ncf, bankruptcy_rate


def run_knapsack_vs_knapsack():
    """Run cap12 vs cap12 and verify against strategic depth doc."""
    print("\n" + "=" * 60)
    print("VALIDATION 1: cap12 vs cap12 (core MultiAgentKnapsackAgent)")
    print("=" * 60)

    cfg = config
    object.__setattr__(cfg, "num_eval_episodes", NUM_EPISODES)
    env_kwargs = _build_env_kwargs()
    tmp_env = MultiAgentInvestmentGameEnv(**env_kwargs)
    agent_ids = list(tmp_env.possible_agents)

    agents = {}
    for agent_id in agent_ids:
        agents[agent_id] = MultiAgentKnapsackAgent(
            agent_name=agent_id,
            env=tmp_env,
            capacity=12,
            enable_bd_bidding=True,
        )

    t0 = time.time()
    per_agent_reports, global_report, _ = parallel_evaluate_multi_agent(
        agents=agents,
        num_workers=NUM_WORKERS,
        env_kwargs=env_kwargs,
        warmup_steps=cfg.warmup_on_reset_steps,
    )
    elapsed = time.time() - t0

    print(f"\nCompleted in {elapsed:.1f}s")
    print(f"\nExpected from strategic depth doc: ~10.6-10.7B mean NCF, 0% bankruptcy")
    print("-" * 60)
    for agent_id, report in per_agent_reports.items():
        # report is [per_eval_dict, per_episode_dict, per_step_dict]
        per_eval = report[0].get("PerEvaluationMetrics", [])
        for metric_dict in per_eval:
            for name, stats in metric_dict.items():
                if isinstance(stats, dict) and "mean" in stats:
                    print(f"  {agent_id}: {name} = {stats['mean']:,.2f}")
                elif isinstance(stats, (int, float)):
                    print(f"  {agent_id}: {name} = {stats:,.4f}")

    return per_agent_reports


def run_ppo_vs_knapsack():
    """Run PPO vs cap12 and compare against saved benchmark."""
    print("\n" + "=" * 60)
    print("VALIDATION 2: PPO vs cap12 Knapsack (core MultiAgentPyxieAgent)")
    print("=" * 60)

    model_dir = (
        PROJECT_ROOT
        / "aiml_pyxis_investment_game"
        / "agents"
        / "saved_multi_agent_model"
    )

    cfg = config
    object.__setattr__(cfg, "num_eval_episodes", NUM_EPISODES)
    env_kwargs = _build_env_kwargs()
    tmp_env = MultiAgentInvestmentGameEnv(**env_kwargs)
    agent_ids = list(tmp_env.possible_agents)

    ppo_name = agent_ids[0]
    knapsack_name = agent_ids[1]

    ppo_agent = MultiAgentPyxieAgent(
        agent_name=ppo_name,
        model_path=model_dir / "best_model.zip",
        vecnorm_path=model_dir / "vecnormalize.pkl",
        env=tmp_env,
    )
    knapsack_agent = MultiAgentKnapsackAgent(
        agent_name=knapsack_name,
        env=tmp_env,
        capacity=12,
        enable_bd_bidding=True,
    )

    agents = {ppo_name: ppo_agent, knapsack_name: knapsack_agent}

    # Use single-worker evaluate — MaskablePPO model can't be pickled
    # across processes due to lr_schedule lambda
    t0 = time.time()
    agent_metrics, global_metrics, _ = evaluate_multi_agent(
        agents=agents,
        worker_id=0,
        episodes_per_worker=NUM_EPISODES,
        env_kwargs=env_kwargs,
        warmup_steps=cfg.warmup_on_reset_steps,
    )
    elapsed = time.time() - t0

    from aiml_pyxis_investment_game.environment.metrics import report_all_metrics

    print(f"\nCompleted in {elapsed:.1f}s")

    # Load reference results if available
    ref_path = (
        PROJECT_ROOT
        / "train_multi_agent"
        / "experiments"
        / "multi_agent_selfplay_30_Apr_2026_155735"
        / "benchmark_vs_knapsack.json"
    )
    if ref_path.exists():
        with open(ref_path) as f:
            ref = json.load(f)
        print(f"Reference results loaded from {ref_path.name}")
    else:
        print("No reference results found")

    print("-" * 60)
    for agent_id, metrics in agent_metrics.items():
        label = "PPO" if agent_id == ppo_name else "KNAPSACK"
        report = report_all_metrics(metrics)
        per_eval = report[0].get("PerEvaluationMetrics", [])
        for metric_dict in per_eval:
            for name, stats in metric_dict.items():
                if isinstance(stats, dict) and "mean" in stats:
                    print(f"  {label} ({agent_id}): {name} = {stats['mean']:,.2f}")
                elif isinstance(stats, (int, float)):
                    print(f"  {label} ({agent_id}): {name} = {stats:,.4f}")

    return agent_metrics


if __name__ == "__main__":
    run_knapsack_vs_knapsack()
    run_ppo_vs_knapsack()
    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)
