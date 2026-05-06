"""
Benchmark: Single-agent Knapsack vs Multi-agent Knapsack (BD off, competition off).

Runs 100 episodes for each configuration using parallel workers, then
compares averages and standard deviations of key metrics.
"""

import json
import logging
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

import click
import numpy as np
from tqdm import tqdm

from pyxis_portfolio_challenge import PROJECT_ROOT, logging_utils
from pyxis_portfolio_challenge.config import config, instantiate_from_config
from pyxis_portfolio_challenge.environment.multi_agent_training_gym import (
    MultiAgentInvestmentGameEnv,
)
from pyxis_portfolio_challenge.environment.warmup_wrapper import (
    MultiAgentWarmupOnResetWrapper,
)

logging_utils.setup_logging(logging.CRITICAL)


# ---------------------------------------------------------------------------
# Single-agent evaluation (reuses existing parallel_evaluate infrastructure)
# ---------------------------------------------------------------------------

def _run_single_agent_worker(
    worker_id: int,
    episodes_per_worker: int,
    base_seed: int,
) -> list[dict]:
    """Worker function for parallel single-agent evaluation."""
    from pyxis_portfolio_challenge.agents.knapsack import KnapsackAgent
    from pyxis_portfolio_challenge.environment.training_gym import InvestmentGameEnv
    from pyxis_portfolio_challenge.environment.warmup_wrapper import (
        WarmupOnResetWrapper,
    )

    cfg = config

    agent = KnapsackAgent()

    env = InvestmentGameEnv(
        equilibrium_num_assets=cfg.equilibrium_num_assets,
        max_num_assets=cfg.max_num_assets,
        asset_arrival_sensitivity_below=cfg.asset_arrival_sensitivity_below,
        asset_arrival_sensitivity_above=cfg.asset_arrival_sensitivity_above,
        starting_cash=cfg.starting_cash,
        horizon=cfg.horizon,
        reward_fn=instantiate_from_config(cfg.reward_fn),
        assets_dir=cfg.evaluation_data_dir,
        reinvestment_percentage=cfg.reinvestment_percentage,
        shuffle_order=False,
        flatten_obs=cfg.flatten_obs,
        mask_first_order_assets=cfg.mask_first_order_assets,
        mask_negative_enpv_assets=cfg.mask_negative_enpv_assets,
        uncertain_ptrs_config=cfg.uncertain_ptrs,
        investment_levels_config=cfg.investment_levels,
        rd_capacity_config=cfg.rd_capacity,
        interim_trial_observations_config=cfg.interim_trial_observations,
        distributional_ptrs_config=cfg.distributional_ptrs,
        ta_experience_config=cfg.ta_experience,
    )

    if cfg.warmup_on_reset_steps > 0:
        env = WarmupOnResetWrapper(
            env,
            warmup_steps=cfg.warmup_on_reset_steps,
            policy=cfg.warmup_on_reset_policy,
            verbose=False,
        )

    agent.set_env(env)

    episode_results = []
    for local_idx in range(episodes_per_worker):
        global_idx = worker_id * episodes_per_worker + local_idx
        seed = base_seed + global_idx

        obs, _ = env.reset(seed=seed)
        agent.set_env(env)

        episode_reward = 0.0
        episode_steps = 0
        terminated = False

        while not terminated:
            action = agent(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            agent.set_env(env)
            episode_reward += reward
            episode_steps += 1

        game_state = env.unwrapped.game_state
        episode_results.append({
            "agent_id": "single_agent",
            "cumulative_reward": episode_reward,
            "final_enpv": game_state.enpv(),
            "final_eroi": game_state.eroi(),
            "final_cash": game_state.cash,
            "realised_roi": game_state.realised_roi(),
            "bankrupt": game_state.game_ended and game_state.cash < 0,
            "num_assets": len(game_state.assets),
            "steps": episode_steps,
        })

    return episode_results


def run_single_agent_benchmark(
    num_episodes: int,
    num_workers: int,
    base_seed: int,
) -> dict:
    """Run knapsack in single-agent env with parallel workers."""
    episodes_per_worker = num_episodes // num_workers

    if num_workers == 1:
        all_results = _run_single_agent_worker(0, num_episodes, base_seed)
    else:
        all_results = []
        with ProcessPoolExecutor(max_workers=num_workers) as pool:
            futures = [
                pool.submit(
                    _run_single_agent_worker,
                    worker_id=i,
                    episodes_per_worker=episodes_per_worker,
                    base_seed=base_seed,
                )
                for i in range(num_workers)
            ]
            pbar_kwargs = dict(total=num_workers, desc="SA workers", unit="worker")
            with tqdm(**pbar_kwargs) as pbar:
                for future in as_completed(futures):
                    all_results.extend(future.result())
                    pbar.update(1)

    return {"single_agent": all_results}


# ---------------------------------------------------------------------------
# Multi-agent evaluation with parallel workers
# ---------------------------------------------------------------------------

def _run_multi_agent_worker(
    worker_id: int,
    episodes_per_worker: int,
    base_seed: int,
    enable_bd: bool = False,
    enable_market_competition: bool = False,
    exclusivity_period: int = 0,
    first_mover_bonus: float = 0.0,
    alert_history_length: int = 0,
    leak_phase_probabilities: list[float] | None = None,
    use_alert_discounting: bool = False,
    contested_ta_discount: float = 0.5,
) -> list[dict]:
    """Worker function for parallel multi-agent evaluation."""
    cfg = config
    ma = cfg.multi_agent

    env = MultiAgentInvestmentGameEnv(
        assets_dir=cfg.evaluation_data_dir,
        num_agents=2,
        starting_cash=cfg.starting_cash,
        max_num_assets=cfg.max_num_assets,
        horizon=cfg.horizon,
        equilibrium_num_assets=cfg.equilibrium_num_assets,
        asset_arrival_sensitivity_below=cfg.asset_arrival_sensitivity_below,
        asset_arrival_sensitivity_above=cfg.asset_arrival_sensitivity_above,
        reinvestment_percentage=cfg.reinvestment_percentage,
        # BD deals
        bd_enabled=enable_bd,
        bd_assets_dir=ma.bd_assets_dir,
        bd_base_lambda=ma.bd_base_lambda,
        bd_leak_lambda_boost=ma.bd_leak_lambda_boost,
        bd_min_step=ma.bd_min_step,
        bd_num_bid_levels=ma.bd_num_bid_levels,
        bd_break_even_bid_level=ma.bd_break_even_bid_level,
        bd_max_slots=ma.bd_max_slots,
        bd_phase_weights=list(ma.bd_phase_weights),
        bd_indication_activity_bias=ma.bd_indication_activity_bias,
        # Market competition
        exclusivity_period=exclusivity_period,
        first_mover_bonus=first_mover_bonus,
        disable_market_share_competition=not enable_market_competition,
        # Intelligence
        alert_history_length=alert_history_length,
        leak_phase_probabilities=leak_phase_probabilities or list(ma.leak_phase_probabilities),
        alerts_per_agent=5,
        # Reward: same as single-agent
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
        reward_type="absolute",
        reward_scale=1.0,
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

    # Apply warmup wrapper if configured
    warmup_steps = cfg.warmup_on_reset_steps
    if warmup_steps > 0:
        env = MultiAgentWarmupOnResetWrapper(
            env,
            warmup_steps=warmup_steps,
            verbose=False,
        )

    # Import here to avoid circular imports at module level
    sys.path.insert(0, str(PROJECT_ROOT / "benchmark_agents" / "agents"))
    from multi_agent_knapsack import MultiAgentKnapsackAgent

    # Create knapsack agents for both players
    agents_dict = {}
    for agent_name in env.possible_agents:
        agents_dict[agent_name] = MultiAgentKnapsackAgent(
            env=env,
            agent_name=agent_name,
            enable_bd_bidding=enable_bd,
            use_alert_discounting=use_alert_discounting,
            contested_ta_discount=contested_ta_discount,
        )

    # Run episodes
    episode_results = []
    for local_idx in range(episodes_per_worker):
        global_idx = worker_id * episodes_per_worker + local_idx
        seed = base_seed + global_idx

        observations, infos = env.reset(seed=seed)

        episode_rewards = {agent: 0.0 for agent in env.possible_agents}
        episode_steps = 0

        while env.agents:
            actions = {}
            for agent_id in env.agents:
                obs = observations[agent_id]
                actions[agent_id] = agents_dict[agent_id](obs)

            observations, rewards, terminations, truncations, infos = env.step(actions)

            for agent_id, reward in rewards.items():
                episode_rewards[agent_id] += reward

            episode_steps += 1

            if all(terminations.values()) or all(truncations.values()):
                break

        # Collect per-episode metrics for each agent
        for agent_id in env.possible_agents:
            portfolio = env.agent_portfolios[agent_id]
            episode_results.append({
                "agent_id": agent_id,
                "cumulative_reward": episode_rewards[agent_id],
                "final_enpv": portfolio.enpv(),
                "final_eroi": portfolio.eroi(),
                "final_cash": portfolio.cash,
                "realised_roi": portfolio.realised_roi(),
                "bankrupt": portfolio.bankrupt,
                "num_assets": len(portfolio.assets),
                "steps": episode_steps,
            })

    return episode_results


def run_multi_agent_benchmark(
    num_episodes: int,
    num_workers: int,
    base_seed: int,
    enable_bd: bool = False,
    enable_market_competition: bool = False,
    exclusivity_period: int = 0,
    first_mover_bonus: float = 0.0,
    alert_history_length: int = 0,
    leak_phase_probabilities: list[float] | None = None,
    use_alert_discounting: bool = False,
    contested_ta_discount: float = 0.5,
) -> dict:
    """Run knapsack vs knapsack in multi-agent env with parallel workers."""
    episodes_per_worker = num_episodes // num_workers

    worker_kwargs = dict(
        enable_bd=enable_bd,
        enable_market_competition=enable_market_competition,
        exclusivity_period=exclusivity_period,
        first_mover_bonus=first_mover_bonus,
        alert_history_length=alert_history_length,
        leak_phase_probabilities=leak_phase_probabilities,
        use_alert_discounting=use_alert_discounting,
        contested_ta_discount=contested_ta_discount,
    )

    if num_workers == 1:
        all_results = _run_multi_agent_worker(
            0, num_episodes, base_seed, **worker_kwargs
        )
    else:
        all_results = []
        with ProcessPoolExecutor(max_workers=num_workers) as pool:
            futures = [
                pool.submit(
                    _run_multi_agent_worker,
                    worker_id=i,
                    episodes_per_worker=episodes_per_worker,
                    base_seed=base_seed,
                    **worker_kwargs,
                )
                for i in range(num_workers)
            ]
            desc = "MA+BD workers" if enable_bd else "MA workers"
            pbar_kwargs = dict(
                total=num_workers, desc=desc, unit="worker"
            )
            with tqdm(**pbar_kwargs) as pbar:
                for future in as_completed(futures):
                    all_results.extend(future.result())
                    pbar.update(1)

    # Aggregate per-agent
    agent_metrics = {}
    for r in all_results:
        aid = r["agent_id"]
        if aid not in agent_metrics:
            agent_metrics[aid] = []
        agent_metrics[aid].append(r)

    return agent_metrics


# ---------------------------------------------------------------------------
# Comparison and reporting
# ---------------------------------------------------------------------------

def compute_stats(values: list[float]) -> dict:
    """Compute mean, std, min, max for a list of values."""
    arr = np.array(values, dtype=float)
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "count": len(arr),
    }


def _print_agent_stats(label: str, episodes: list[dict]):
    """Print stats for a list of per-episode dicts."""
    print(f"\n--- {label} ---")
    n = len(episodes)
    for key, display, fmt in [
        ("cumulative_reward", "Cumulative Reward", ".2f"),
        ("final_enpv", "Final eNPV", ".2f"),
        ("final_eroi", "Final eROI", ".4f"),
        ("realised_roi", "Realised ROI", ".4f"),
    ]:
        s = compute_stats([e[key] for e in episodes])
        print(f"  {display + ':':<22s} {s['mean']:>14{fmt}} +/- {s['std']:>12{fmt}}")
    br = np.mean([e["bankrupt"] for e in episodes])
    print(f"  {'Bankruptcy Rate:':<22s} {br:.4f}  (n={n})")


def print_comparison(
    multi_results: dict,
    label: str,
    multi_bd_results: dict | None = None,
):
    """Print a formatted comparison table."""
    print("\n" + "=" * 80)
    print(label)
    print("=" * 80)

    for agent_id in sorted(multi_results.keys()):
        _print_agent_stats(
            f"BASELINE ({agent_id})",
            multi_results[agent_id],
        )

    if multi_bd_results:
        for agent_id in sorted(multi_bd_results.keys()):
            _print_agent_stats(
                f"TREATMENT ({agent_id})",
                multi_bd_results[agent_id],
            )

    print("\n" + "=" * 80)


@click.command()
@click.option("--num-episodes", "-e", default=100, help="Episodes per config.")
@click.option("--num-workers", "-n", default=10, help="Parallel workers.")
@click.option("--seed", "-s", default=891024889, help="Base seed.")
@click.option(
    "--alert-history", default=5,
    help="Alert history length for pipeline leaks.",
)
@click.option(
    "--leak-prob", default=0.3,
    help="Pipeline leak probability per step.",
)
@click.option("--output", "-o", default=None, help="Output JSON file path.")
def main(
    num_episodes, num_workers, seed,
    alert_history, leak_prob, output,
):
    """Compare knapsack with alerts OFF vs ON (no discounting)."""
    print(
        f"Running {num_episodes} episodes per config, "
        f"{num_workers} workers"
    )

    # --- Baseline: alerts OFF ---
    print("\n[1/2] Running multi-agent knapsack (alerts OFF)...")
    baseline_results = run_multi_agent_benchmark(
        num_episodes, num_workers, seed,
    )

    # --- Treatment: alerts ON (knapsack doesn't use them) ---
    print(
        f"\n[2/2] Running multi-agent knapsack "
        f"(alerts ON, history={alert_history}, "
        f"leak_prob={leak_prob})..."
    )
    alerts_results = run_multi_agent_benchmark(
        num_episodes, num_workers, seed,
        alert_history_length=alert_history,
        leak_phase_probabilities=[leak_prob, leak_prob, leak_prob],
    )

    # --- Print comparison ---
    print_comparison(
        baseline_results,
        label="MULTI-AGENT KNAPSACK: ALERTS OFF vs ON",
        multi_bd_results=alerts_results,
    )

    # --- Save results ---
    if output:
        def serialise(episodes):
            return [
                {k: float(v) if isinstance(v, (np.floating, float)) else v
                 for k, v in ep.items()}
                for ep in episodes
            ]

        out = {
            "alerts_off": {
                aid: serialise(eps)
                for aid, eps in baseline_results.items()
            },
            "alerts_on": {
                aid: serialise(eps)
                for aid, eps in alerts_results.items()
            },
            "config": {
                "num_episodes": num_episodes,
                "num_workers": num_workers,
                "seed": seed,
                "alert_history_length": alert_history,
                "leak_phase_probabilities": [leak_prob, leak_prob, leak_prob],
            },
        }
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"\nResults saved to {output}")


if __name__ == "__main__":
    main()
