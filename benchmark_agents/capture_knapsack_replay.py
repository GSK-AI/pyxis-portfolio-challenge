"""
Capture knapsack vs knapsack replays as JSON, one per seed.

Usage:
    cd <repo root>
    uv run python benchmark_agents/capture_knapsack_replay.py [--seeds 10]
"""

import argparse
import json
import logging

from aiml_pyxis_investment_game import PROJECT_ROOT, logging_utils
from aiml_pyxis_investment_game.config import config, instantiate_from_config
from aiml_pyxis_investment_game.environment.multi_agent_evaluate import (
    parallel_evaluate_multi_agent,
)
from aiml_pyxis_investment_game.environment.multi_agent_training_gym import (
    MultiAgentInvestmentGameEnv,
)

logging_utils.setup_logging(logging.WARNING)

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "multi_agent_knapsack",
    str(PROJECT_ROOT / "benchmark_agents" / "agents" / "multi_agent_knapsack.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
MultiAgentKnapsackAgent = _mod.MultiAgentKnapsackAgent


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
    parser.add_argument("--seeds", type=int, default=10, help="Number of seeds to run")
    parser.add_argument("--base-seed", type=int, default=42, help="Starting seed")
    parser.add_argument("--horizon", type=int, default=None, help="Override game horizon (steps)")
    parser.add_argument("--mode", type=str, default="symmetric",
                        choices=["symmetric", "uncapped_vs_capped3"],
                        help="Agent configuration mode")
    args = parser.parse_args()

    cfg = config
    object.__setattr__(cfg, "num_eval_episodes", 1)
    if args.horizon is not None:
        object.__setattr__(cfg, "horizon", args.horizon)

    env_kwargs = _build_env_kwargs()
    tmp_env = MultiAgentInvestmentGameEnv(**env_kwargs)

    agent_names = list(tmp_env.possible_agents)

    if args.mode == "symmetric":
        agents = {
            name: MultiAgentKnapsackAgent(
                env=tmp_env, agent_name=name, enable_bd_bidding=True
            )
            for name in agent_names
        }
        display_names = {name: f"Knapsack {i}" for i, name in enumerate(agent_names)}
        file_prefix = "knapsack_vs_knapsack"
    elif args.mode == "uncapped_vs_capped3":
        # pharma_0 = uncapped, pharma_1 = capped at 3
        agents = {}
        agents[agent_names[0]] = MultiAgentKnapsackAgent(
            env=tmp_env, agent_name=agent_names[0], enable_bd_bidding=True
        )
        capped = MultiAgentKnapsackAgent(
            env=tmp_env, agent_name=agent_names[1], enable_bd_bidding=True
        )
        capped._capacity_override = 3
        agents[agent_names[1]] = capped
        display_names = {
            agent_names[0]: "Knapsack (uncapped)",
            agent_names[1]: "Knapsack (cap=3)",
        }
        file_prefix = "knapsack_uncapped_vs_capped3"
    else:
        raise ValueError(f"Unknown mode: {args.mode}")

    print(f"Capturing {args.seeds} replays (seeds {args.base_seed}-{args.base_seed + args.seeds - 1}), mode={args.mode}...")

    for i in range(args.seeds):
        seed = args.base_seed + i
        object.__setattr__(cfg, "eval_initial_seed", seed)

        _, _, playthrough_dict = parallel_evaluate_multi_agent(
            agents=agents,
            num_workers=1,
            env_kwargs=env_kwargs,
            warmup_steps=cfg.warmup_on_reset_steps,
            capture_playthrough=True,
            agent_names=display_names,
        )

        if playthrough_dict is None:
            print(f"  Seed {seed}: ERROR - no playthrough captured")
            continue

        out_path = str(PROJECT_ROOT / "replays" / f"{file_prefix}_seed{seed}.json")
        with open(out_path, "w") as f:
            json.dump(playthrough_dict, f, indent=2, default=str)

        n_steps = len(playthrough_dict.get("steps", []))
        print(f"  Seed {seed}: {n_steps} steps -> {out_path}")

    print(f"\nDone. {args.seeds} replays saved to replays/{file_prefix}_seed*.json")
