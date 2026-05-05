"""
Benchmark: Greedy vs Greedy (MultiAgentGreedyAgent with max_concurrent=4).

Uses parallel_evaluate_multi_agent for fast multi-process evaluation.

Usage:
    cd <repo root>
    uv run python benchmark_agents/benchmark_greedy_top4.py [--episodes 50]
"""

import argparse
import json
import logging
import os
import sys

from aiml_pyxis_investment_game import PROJECT_ROOT, logging_utils
from aiml_pyxis_investment_game.config import config, instantiate_from_config
from aiml_pyxis_investment_game.environment.multi_agent_evaluate import (
    parallel_evaluate_multi_agent,
)
from aiml_pyxis_investment_game.environment.multi_agent_training_gym import (
    MultiAgentInvestmentGameEnv,
)

logging_utils.setup_logging(logging.WARNING)

sys.path.insert(0, str(PROJECT_ROOT / "benchmark_agents"))
from agents.multi_agent_greedy import MultiAgentGreedyAgent


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=50)
    args = parser.parse_args()

    cfg = config
    num_workers = max(1, os.cpu_count() // 2)

    env_kwargs = _build_env_kwargs()
    tmp_env = MultiAgentInvestmentGameEnv(**env_kwargs)

    agents = {
        name: MultiAgentGreedyAgent(env=tmp_env, agent_name=name, max_concurrent=4)
        for name in tmp_env.possible_agents
    }

    print(
        f"Greedy vs Greedy (max_concurrent=4, "
        f"rd_capacity={'ON' if cfg.rd_capacity.enabled else 'OFF'} base={cfg.rd_capacity.base_capacity}, "
        f"congestion_exp={cfg.multi_agent.congestion_exponent}): "
        f"{args.episodes} episodes, {num_workers} workers"
    )

    original_num = cfg.num_eval_episodes
    object.__setattr__(cfg, "num_eval_episodes", args.episodes)

    all_reports, _global, _ = parallel_evaluate_multi_agent(
        agents=agents,
        num_workers=num_workers,
        env_kwargs=env_kwargs,
        warmup_steps=cfg.warmup_on_reset_steps,
    )

    object.__setattr__(cfg, "num_eval_episodes", original_num)

    out_path = "benchmark_agents/results/greedy_vs_greedy.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_reports, f, indent=2, default=str)
    print(f"\nSaved metrics to {out_path}")

    print("\n" + "=" * 60)
    print("GREEDY vs GREEDY SUMMARY")
    print("=" * 60)
    for agent_id, report in all_reports.items():
        print(f"\n  {agent_id}:")
        for item in report:
            for section, metrics in item.items():
                if not isinstance(metrics, list):
                    continue
                for m in metrics:
                    for metric_name, data in m.items():
                        if isinstance(data, dict):
                            mean = data.get("mean", data.get("bankruptcy_rate"))
                            std = data.get("stdev", data.get("std"))
                            mn, mx = data.get("min"), data.get("max")
                            if mean is not None:
                                if abs(mean) > 1e6:
                                    s = f"mean={mean/1e9:.3f}B"
                                    if std: s += f"  std={std/1e9:.2f}B"
                                    if mn is not None: s += f"  min={mn/1e9:.2f}B  max={mx/1e9:.2f}B"
                                else:
                                    s = f"{mean:.4g}"
                                print(f"    {metric_name}: {s}")
                        elif isinstance(data, (int, float)):
                            print(f"    {metric_name}: {data:.4g}")
