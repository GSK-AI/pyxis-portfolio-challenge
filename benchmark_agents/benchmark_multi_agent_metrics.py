"""
Benchmark: Knapsack vs Knapsack in multi-agent env with full metrics pipeline.

Runs a few episodes to verify the new multi-agent metrics produce sensible data.
"""

import json
import logging
import sys

import numpy as np

from pyxis_portfolio_challenge import PROJECT_ROOT, logging_utils
from pyxis_portfolio_challenge.config import config, instantiate_from_config
from pyxis_portfolio_challenge.environment.metrics import (
    MetricsContext,
    collect_metrics,
)
from pyxis_portfolio_challenge.environment.multi_agent_training_gym import (
    MultiAgentInvestmentGameEnv,
)
from pyxis_portfolio_challenge.environment.warmup_wrapper import (
    MultiAgentWarmupOnResetWrapper,
)

logging_utils.setup_logging(logging.WARNING)

sys.path.insert(0, str(PROJECT_ROOT / "benchmark_agents" / "agents"))
from multi_agent_knapsack import MultiAgentKnapsackAgent


def run_benchmark(num_episodes=10, seed=891024889):
    cfg = config
    ma = cfg.multi_agent

    env = MultiAgentInvestmentGameEnv(
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

    warmup_steps = cfg.warmup_on_reset_steps
    if warmup_steps > 0:
        env = MultiAgentWarmupOnResetWrapper(
            env, warmup_steps=warmup_steps, verbose=False
        )

    # Create knapsack agents
    agents = {}
    for agent_name in env.possible_agents:
        agents[agent_name] = MultiAgentKnapsackAgent(
            env=env, agent_name=agent_name, enable_bd_bidding=False,
        )

    # Create per-agent metrics
    agent_metrics = {}
    for agent_id in env.possible_agents:
        agent_metrics[agent_id] = [
            instantiate_from_config(m) for m in cfg.evaluation_metrics
        ]

    for metrics_list in agent_metrics.values():
        collect_metrics("on_evaluation_begin", metrics=metrics_list, context=None)

    for ep_idx in range(num_episodes):
        ep_seed = seed + ep_idx
        observations, infos = env.reset(seed=ep_seed)

        shared_market = env.multi_agent_game.shared_market
        all_states = env.agent_portfolios
        for agent_id in env.possible_agents:
            ctx = MetricsContext(
                game_state=all_states[agent_id],
                reward=0.0,
                shared_market_state=shared_market,
                agent_id=agent_id,
                all_agent_states=all_states,
            )
            collect_metrics(
                "on_episode_begin",
                metrics=agent_metrics[agent_id],
                context=ctx,
            )

        episode_rewards = {a: 0.0 for a in env.possible_agents}
        step = 0

        while env.agents:
            actions = {}
            for agent_id in env.agents:
                actions[agent_id] = agents[agent_id](observations[agent_id])

            observations, rewards, terminations, truncations, infos = env.step(actions)
            step += 1

            for agent_id, r in rewards.items():
                episode_rewards[agent_id] += r

            shared_market = env.multi_agent_game.shared_market
            all_states = env.agent_portfolios
            for agent_id in env.possible_agents:
                ctx = MetricsContext(
                    game_state=all_states[agent_id],
                    reward=rewards.get(agent_id, 0.0),
                    shared_market_state=shared_market,
                    agent_id=agent_id,
                    all_agent_states=all_states,
                )
                collect_metrics(
                    "on_step_end",
                    metrics=agent_metrics[agent_id],
                    context=ctx,
                )

            if all(terminations.values()) or all(truncations.values()):
                break

        shared_market = env.multi_agent_game.shared_market
        all_states = env.agent_portfolios
        for agent_id in env.possible_agents:
            ctx = MetricsContext(
                game_state=all_states[agent_id],
                reward=episode_rewards[agent_id],
                shared_market_state=shared_market,
                agent_id=agent_id,
                all_agent_states=all_states,
            )
            collect_metrics(
                "on_episode_end",
                metrics=agent_metrics[agent_id],
                context=ctx,
            )

        print(f"  Episode {ep_idx + 1}/{num_episodes} done ({step} steps)")

    for metrics_list in agent_metrics.values():
        collect_metrics("on_evaluation_end", metrics=metrics_list, context=None)

    return agent_metrics


def print_multi_agent_metrics(agent_metrics):
    """Print a summary of multi-agent specific metrics."""
    multi_agent_metric_names = [
        "PerStepIndicationDiversity",
        "PerStepIndicationConcentration",
        "PerStepOnMarketPerIndication",
        "PerStepFirstMoverExclusivities",
        "PerStepContestedIndications",
        "PerStepTotalOnMarketPerIndication",
        "PerStepIndicationSpread",
        "PerEpisodeIndicationSpread",
        "PerStepNonBankruptAgents",
        "PerStepAgentRank",
        "PerStepRelativeEnpv",
        "PerStepBDAssetAvailable",
        "PerEpisodeDrugReleases",
        "PerStepDrugsOnMarket",
        "PerEpisodeBDDealsWon",
        "PerStepMeanMarketShare",
        "PerStepIndicationsWithExclusivity",
        "PerStepAlertCount",
        "PerStepDrugReleaseAlerts",
        "PerStepBDDealAlerts",
        "PerStepPipelineLeakAlerts",
    ]

    for agent_id, metrics_list in agent_metrics.items():
        print(f"\n{'=' * 70}")
        print(f"AGENT: {agent_id}")
        print(f"{'=' * 70}")

        for metric in metrics_list:
            report = metric.report()
            for name, data in report.items():
                if name not in multi_agent_metric_names:
                    continue

                print(f"\n  {name}:")

                if isinstance(data, dict):
                    for ep_key, values in sorted(data.items()):
                        if isinstance(values, list):
                            if len(values) > 0 and isinstance(values[0], dict):
                                # Dict-valued steps (e.g. OnMarketPerIndication)
                                non_empty = [v for v in values if v]
                                print(
                                    f"    {ep_key}: "
                                    f"{len(non_empty)}/{len(values)} "
                                    f"steps with data"
                                )
                                if non_empty:
                                    print(f"      last: {non_empty[-1]}")
                            else:
                                arr = np.array(values, dtype=float)
                                print(
                                    f"    {ep_key}: "
                                    f"mean={arr.mean():.3f}, "
                                    f"last={arr[-1]:.3f}, "
                                    f"min={arr.min():.3f}, "
                                    f"max={arr.max():.3f}"
                                )
                        elif isinstance(values, (int, float)):
                            print(f"    {ep_key}: {values}")


def save_results(agent_metrics, output_dir):
    """Save all metric reports to JSON files, one per agent."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    for agent_id, metrics_list in agent_metrics.items():
        report = {}
        for metric in metrics_list:
            for name, data in metric.report().items():
                report[name] = _make_serializable(data)

        path = os.path.join(output_dir, f"{agent_id}.json")
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"  Saved {path}")


def _make_serializable(obj):
    """Convert numpy types and UUIDs for JSON serialization."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serializable(v) for v in obj]
    return obj


if __name__ == "__main__":
    cfg = config
    num_episodes = cfg.num_eval_episodes
    seed = cfg.eval_initial_seed

    print("Running Knapsack vs Knapsack with full metrics pipeline...")
    print(f"Config: {cfg.multi_agent.num_agents} agents, "
          f"BD enabled={cfg.multi_agent.bd_enabled}, "
          f"competition={'ON' if not cfg.multi_agent.disable_market_share_competition else 'OFF'}, "
          f"episodes={num_episodes}, seed={seed}")
    print()

    agent_metrics = run_benchmark(num_episodes=num_episodes, seed=seed)

    output_dir = str(
        PROJECT_ROOT / "benchmark_agents" / "results" / "knapsack_vs_knapsack_multi_agent"
    )
    save_results(agent_metrics, output_dir)
    print()
    print_multi_agent_metrics(agent_metrics)
