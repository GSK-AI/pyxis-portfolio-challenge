"""
Benchmark: Trained PPO vs Knapsack (no BD) with full metrics pipeline.

Loads the best model from multi-agent training, plays against knapsack,
and collects all evaluation metrics including market dynamics metrics.
"""

import json
import logging
import sys

import numpy as np
import torch
from sb3_contrib import MaskablePPO

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


def make_env(cfg):
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
    return env


def load_ppo_agent(model_path, vecnorm_path):
    model = MaskablePPO.load(model_path)
    import pickle
    with open(vecnorm_path, "rb") as f:
        vecnorm = pickle.load(f)
    return model, vecnorm


def ppo_predict(model, vecnorm, obs, env, agent_name):
    """Normalize obs and predict with action masks."""
    norm_obs = (obs - vecnorm.obs_rms.mean) / np.sqrt(vecnorm.obs_rms.var + 1e-8)
    norm_obs = np.clip(norm_obs, -10.0, 10.0)
    obs_tensor = torch.tensor(norm_obs[np.newaxis], dtype=torch.float32)

    masks = env.action_masks(agent_name)
    inv_mask = masks["investments"]
    bd_mask = masks["bd_bids"]
    parts = []
    if isinstance(inv_mask, list):
        parts.extend(b for slot in inv_mask for b in slot)
    else:
        for m in inv_mask:
            parts.extend([True, bool(m)])
    for slot in bd_mask:
        parts.extend(slot)
    flat_mask = np.array(parts, dtype=bool)
    mask_tensor = torch.tensor(flat_mask[np.newaxis], dtype=torch.bool)

    with torch.no_grad():
        dist = model.policy.get_distribution(obs_tensor, action_masks=mask_tensor)
        action = dist.mode().cpu().numpy()[0]

    n_inv = env.max_num_assets
    n_bd = env.bd_max_slots
    return {
        "investments": action[:n_inv],
        "bd_bids": action[n_inv:n_inv + n_bd],
    }


def run_benchmark(model_path, vecnorm_path, num_episodes=100, seed=891024889,
                  enable_bd=False):
    cfg = config
    env = make_env(cfg)

    model, vecnorm = load_ppo_agent(model_path, vecnorm_path)

    ppo_name = env.possible_agents[0]
    knapsack_name = env.possible_agents[1]

    knapsack = MultiAgentKnapsackAgent(
        env=env, agent_name=knapsack_name, enable_bd_bidding=enable_bd,
    )

    # Create per-agent metrics
    agent_metrics = {}
    for agent_id in env.possible_agents:
        agent_metrics[agent_id] = [
            instantiate_from_config(m) for m in cfg.evaluation_metrics
        ]

    for metrics_list in agent_metrics.values():
        collect_metrics("on_evaluation_begin", metrics=metrics_list, context=None)

    ppo_total_rewards = []
    knapsack_total_rewards = []
    wins = 0

    for ep_idx in range(num_episodes):
        ep_seed = seed + ep_idx
        obs_dict, _ = env.reset(seed=ep_seed)

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
            collect_metrics("on_episode_begin", metrics=agent_metrics[agent_id], context=ctx)

        episode_rewards = {a: 0.0 for a in env.possible_agents}
        step = 0

        while env.agents:
            actions = {}
            # PPO agent
            if ppo_name in env.agents:
                actions[ppo_name] = ppo_predict(
                    model, vecnorm, obs_dict[ppo_name], env, ppo_name
                )
            # Knapsack agent
            if knapsack_name in env.agents:
                actions[knapsack_name] = knapsack(obs_dict[knapsack_name])

            obs_dict, rewards, terminations, truncations, infos = env.step(actions)
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
                collect_metrics("on_step_end", metrics=agent_metrics[agent_id], context=ctx)

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
            collect_metrics("on_episode_end", metrics=agent_metrics[agent_id], context=ctx)

        ppo_r = episode_rewards[ppo_name]
        knap_r = episode_rewards[knapsack_name]
        ppo_total_rewards.append(ppo_r)
        knapsack_total_rewards.append(knap_r)
        if ppo_r > knap_r:
            wins += 1

        if (ep_idx + 1) % 10 == 0:
            print(f"  Episode {ep_idx + 1}/{num_episodes} done ({step} steps) "
                  f"| PPO: {ppo_r:,.0f} | Knapsack: {knap_r:,.0f}")

    for metrics_list in agent_metrics.values():
        collect_metrics("on_evaluation_end", metrics=metrics_list, context=None)

    win_rate = wins / num_episodes
    print(f"\n{'=' * 70}")
    print(f"RESULTS: {num_episodes} episodes, BD={'ON' if enable_bd else 'OFF'}")
    print(f"  PPO mean reward:      {np.mean(ppo_total_rewards):>15,.0f}")
    print(f"  Knapsack mean reward: {np.mean(knapsack_total_rewards):>15,.0f}")
    print(f"  PPO win rate:         {win_rate:>15.1%}")
    print(f"{'=' * 70}")

    return agent_metrics, ppo_name, knapsack_name


def _make_serializable(obj):
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


def save_results(agent_metrics, output_dir):
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


def analyze_market_dynamics(agent_metrics, ppo_name, knapsack_name):
    """Print market dynamics analysis focusing on indication metrics."""
    focus_metrics = [
        "PerStepEmptyIndications",
        "PerStepNovelIndications",
        "PerStepMeanMarketShare",
        "PerStepIndicationDiversity",
        "PerStepContestedIndications",
        "PerStepFirstMoverExclusivities",
        "PerStepIndicationsWithExclusivity",
        "PerStepDrugsOnMarket",
        "PerEpisodeDrugReleases",
        "PerStepIndicationSpread",
        "PerEpisodeIndicationSpread",
        "PerStepTotalOnMarketPerIndication",
    ]

    for agent_id in [ppo_name, knapsack_name]:
        label = "PPO" if agent_id == ppo_name else "Knapsack"
        print(f"\n{'=' * 70}")
        print(f"MARKET DYNAMICS: {label} ({agent_id})")
        print(f"{'=' * 70}")

        metrics_list = agent_metrics[agent_id]
        for metric in metrics_list:
            report = metric.report()
            for name, data in report.items():
                if name not in focus_metrics:
                    continue

                print(f"\n  {name}:")
                if isinstance(data, dict):
                    all_values = []
                    for ep_key, values in sorted(data.items()):
                        if isinstance(values, list) and len(values) > 0:
                            if isinstance(values[0], (int, float, np.integer, np.floating)):
                                all_values.extend(values)

                    if all_values:
                        arr = np.array(all_values, dtype=float)
                        n_eps = len(data)
                        steps_per_ep = len(all_values) // max(n_eps, 1)

                        print(f"    Overall: mean={arr.mean():.3f}, std={arr.std():.3f}, "
                              f"min={arr.min():.3f}, max={arr.max():.3f}")

                        # Early / mid / late breakdown
                        if steps_per_ep >= 3:
                            third = steps_per_ep // 3
                            early_vals, mid_vals, late_vals = [], [], []
                            for ep_key, values in sorted(data.items()):
                                if isinstance(values, list) and len(values) >= 3:
                                    if isinstance(values[0], (int, float, np.integer, np.floating)):
                                        early_vals.extend(values[:third])
                                        mid_vals.extend(values[third:2*third])
                                        late_vals.extend(values[2*third:])
                            if early_vals:
                                print(f"    Early:   mean={np.mean(early_vals):.3f}")
                                print(f"    Mid:     mean={np.mean(mid_vals):.3f}")
                                print(f"    Late:    mean={np.mean(late_vals):.3f}")
                    else:
                        # Non-numeric per-step data or per-episode scalar
                        for ep_key, values in sorted(data.items()):
                            if isinstance(values, (int, float)):
                                print(f"    {ep_key}: {values:.3f}")
                            elif isinstance(values, list) and len(values) > 0:
                                if isinstance(values[0], dict):
                                    non_empty = [v for v in values if v]
                                    print(f"    {ep_key}: {len(non_empty)}/{len(values)} steps with data")


if __name__ == "__main__":
    EXPERIMENT_DIR = (
        PROJECT_ROOT
        / "train_multi_agent"
        / "experiments"
        / "multi_agent_selfplay_27_Mar_2026_180348"
    )
    MODEL_PATH = EXPERIMENT_DIR / "best_model" / "best_model.zip"
    VECNORM_PATH = EXPERIMENT_DIR / "best_model" / "vecnormalize.pkl"

    cfg = config
    num_episodes = cfg.num_eval_episodes
    seed = cfg.eval_initial_seed

    print("Benchmark: PPO (best model) vs Knapsack (no BD)")
    print(f"Model: {MODEL_PATH}")
    print(f"Episodes: {num_episodes}, Seed: {seed}")
    print()

    agent_metrics, ppo_name, knapsack_name = run_benchmark(
        model_path=str(MODEL_PATH),
        vecnorm_path=str(VECNORM_PATH),
        num_episodes=num_episodes,
        seed=seed,
        enable_bd=False,
    )

    output_dir = str(
        PROJECT_ROOT / "benchmark_agents" / "results" / "ppo_vs_knapsack_per_drug_market_share"
    )
    save_results(agent_metrics, output_dir)
    print()
    analyze_market_dynamics(agent_metrics, ppo_name, knapsack_name)
