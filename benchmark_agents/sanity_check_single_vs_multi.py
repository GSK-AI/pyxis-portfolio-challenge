"""
Sanity check: compare knapsack in single-agent vs multi-agent environments.

Three scenarios:
1. Single-agent knapsack (baseline)
2. Multi-agent knapsack vs knapsack, BD disabled
3. Multi-agent knapsack vs knapsack, BD enabled

Under equivalent settings (no extra features, no market competition),
scenario 2 should match scenario 1. Scenario 3 should improve on 1.
"""

import math

import numpy as np

from aiml_pyxis_investment_game.agents.knapsack import KnapsackAgent, delta_npv
from aiml_pyxis_investment_game.config import from_yaml, instantiate_from_config
from aiml_pyxis_investment_game.environment.multi_agent_training_gym import (
    MultiAgentInvestmentGameEnv,
)
from aiml_pyxis_investment_game.environment.training_gym import InvestmentGameEnv
from aiml_pyxis_investment_game.game.asset import AssetState

# Load config
cfg = from_yaml()
reward_fn = instantiate_from_config(cfg.reward_fn)

# Parameters from config
ASSETS_DIR = cfg.training_data_dir
EQUILIBRIUM_NUM_ASSETS = cfg.equilibrium_num_assets
MAX_NUM_ASSETS = cfg.max_num_assets
SENSITIVITY_BELOW = cfg.asset_arrival_sensitivity_below
SENSITIVITY_ABOVE = cfg.asset_arrival_sensitivity_above
STARTING_CASH = cfg.starting_cash
HORIZON = cfg.horizon
REINVESTMENT_PCT = cfg.reinvestment_percentage

# Benchmark parameters
NUM_EPISODES = 50
INITIAL_SEED = 42


class MultiAgentKnapsackAgent:
    """Knapsack agent adapted for multi-agent environment."""

    def __init__(self, env: MultiAgentInvestmentGameEnv, agent_id: str,
                 enable_bd: bool = False):
        self.env = env
        self.agent_id = agent_id
        self.units = 1e6
        self.enable_bd = enable_bd

    def __call__(self, obs: np.ndarray) -> dict:
        portfolio = self.env.agent_portfolios[self.agent_id]
        asset_order = self.env._asset_id_orders[self.agent_id]

        budget = portfolio.cash
        for asset in portfolio.assets.values():
            if asset.state == AssetState.InDevelopment:
                budget -= asset.cost_this_step

        investments = np.zeros(self.env.max_num_assets, dtype=np.int8)
        bd_bids = np.zeros(self.env.bd_max_slots, dtype=np.int64)

        if budget <= 0:
            return {"investments": investments, "bd_bids": bd_bids}

        # Build knapsack items from idle assets
        idle_assets = []
        for asset in portfolio.assets.values():
            if asset.state == AssetState.Idle:
                value = delta_npv(asset)
                weight = math.ceil(asset.remaining_trial_cost / self.units)
                idle_assets.append((value, weight, asset.id))

        budget_rescaled = math.floor(budget / self.units)

        if idle_assets:
            selected = self._knapsack_01(idle_assets, budget_rescaled)
            selected_ids = {item[2] for item in selected}
            for i, asset_id in enumerate(asset_order):
                if asset_id is not None and asset_id in selected_ids:
                    investments[i] = 1

        # BD bidding
        if self.enable_bd and len(portfolio.assets) < portfolio.max_num_assets:
            shared = self.env.multi_agent_game.shared_market
            if shared.current_bd_asset is not None:
                asset = shared.current_bd_asset
                value = delta_npv(asset)
                if value > 0 and portfolio.cash > 0:
                    if asset.enpv > asset.remaining_trial_cost:
                        bd_bids[0] = 3  # Bid at level 3 (~30% eNPV)

        return {"investments": investments, "bd_bids": bd_bids}

    def _knapsack_01(self, items, capacity):
        n = len(items)
        dp = [[0] * (capacity + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            value, weight, _ = items[i - 1]
            for w in range(1, capacity + 1):
                dp[i][w] = dp[i - 1][w]
                if weight <= w:
                    dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - weight] + value)
        selected = []
        w = capacity
        for i in range(n, 0, -1):
            if dp[i][w] != dp[i - 1][w]:
                selected.append(items[i - 1])
                w -= items[i - 1][1]
        return selected


def run_single_agent():
    """Run knapsack on single-agent environment."""
    env = InvestmentGameEnv(
        assets_dir=ASSETS_DIR,
        equilibrium_num_assets=EQUILIBRIUM_NUM_ASSETS,
        max_num_assets=MAX_NUM_ASSETS,
        asset_arrival_sensitivity_below=SENSITIVITY_BELOW,
        asset_arrival_sensitivity_above=SENSITIVITY_ABOVE,
        starting_cash=STARTING_CASH,
        horizon=HORIZON,
        reinvestment_percentage=REINVESTMENT_PCT,
        reward_fn=reward_fn,
        shuffle_order=cfg.shuffle_order,
        mask_first_order_assets=cfg.mask_first_order_assets,
        mask_negative_enpv_assets=cfg.mask_negative_enpv_assets,
        flatten_obs=cfg.flatten_obs,
        distributional_ptrs_config=cfg.distributional_ptrs if cfg.distributional_ptrs and cfg.distributional_ptrs.enabled else None,
        ta_experience_config=cfg.ta_experience if cfg.ta_experience and cfg.ta_experience.enabled else None,
        uncertain_ptrs_config=cfg.uncertain_ptrs if cfg.uncertain_ptrs and cfg.uncertain_ptrs.enabled else None,
        investment_levels_config=cfg.investment_levels if cfg.investment_levels and cfg.investment_levels.enabled else None,
        rd_capacity_config=cfg.rd_capacity,
        interim_trial_observations_config=cfg.interim_trial_observations if cfg.interim_trial_observations and cfg.interim_trial_observations.enabled else None,
    )

    agent = KnapsackAgent(units=1e6, include_ongoing_costs=True)
    agent.set_env(env)

    all_rewards = []
    for ep in range(NUM_EPISODES):
        obs, info = env.reset(seed=INITIAL_SEED + ep)
        total_reward = 0.0
        while True:
            action = agent(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            if terminated or truncated:
                break
        all_rewards.append(total_reward)

    return np.array(all_rewards)


def run_multi_agent(num_agents: int, enable_bd: bool,
                    disable_market_share_competition: bool = True):
    """Run knapsack vs knapsack on multi-agent environment."""
    ma_cfg = cfg.multi_agent
    env = MultiAgentInvestmentGameEnv(
        assets_dir=ASSETS_DIR,
        num_agents=num_agents,
        starting_cash=STARTING_CASH,
        max_num_assets=MAX_NUM_ASSETS,
        horizon=HORIZON,
        equilibrium_num_assets=EQUILIBRIUM_NUM_ASSETS,
        asset_arrival_sensitivity_below=SENSITIVITY_BELOW,
        asset_arrival_sensitivity_above=SENSITIVITY_ABOVE,
        reinvestment_percentage=REINVESTMENT_PCT,
        bd_enabled=enable_bd,
        bd_assets_dir=ma_cfg.bd_assets_dir,
        bd_base_lambda=ma_cfg.bd_base_lambda,
        bd_leak_lambda_boost=ma_cfg.bd_leak_lambda_boost,
        bd_min_step=ma_cfg.bd_min_step,
        bd_num_bid_levels=ma_cfg.bd_num_bid_levels,
        bd_break_even_bid_level=ma_cfg.bd_break_even_bid_level,
        bd_max_slots=ma_cfg.bd_max_slots,
        bd_phase_weights=list(ma_cfg.bd_phase_weights),
        bd_indication_activity_bias=ma_cfg.bd_indication_activity_bias,
        exclusivity_period=ma_cfg.exclusivity_period,
        first_mover_bonus=ma_cfg.first_mover_bonus,
        disable_market_share_competition=disable_market_share_competition,
        alert_history_length=ma_cfg.alert_history_length,
        leak_phase_probabilities=list(ma_cfg.leak_phase_probabilities),
        alerts_per_agent=ma_cfg.alerts_per_agent,
        reward_fn=reward_fn,
        reward_type=ma_cfg.reward_type,
        reward_scale=ma_cfg.reward_scale,
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
        target_drugs_per_indication=ma_cfg.target_drugs_per_indication,
        on_market_fraction=ma_cfg.on_market_fraction,
        max_indications_per_ta=ma_cfg.max_indications_per_ta,
        indication_spread=ma_cfg.indication_spread,
        indication_drift_speed=ma_cfg.indication_drift_speed,
        trial_cost_multiplier=cfg.trial_cost_multiplier,
        congestion_exponent=ma_cfg.congestion_exponent,
        congestion_ramp_steps=ma_cfg.congestion_ramp_steps,
        congestion_incumbent_penalty=ma_cfg.congestion_incumbent_penalty,
        pricing_config=cfg.pricing,
    )

    agents = {
        aid: MultiAgentKnapsackAgent(env, aid, enable_bd=enable_bd)
        for aid in env.possible_agents
    }

    # Collect all agent rewards across all episodes into one pool
    all_rewards = []
    for ep in range(NUM_EPISODES):
        observations, _ = env.reset(seed=INITIAL_SEED + ep)
        ep_rewards = {aid: 0.0 for aid in env.possible_agents}

        while env.agents:
            actions = {
                aid: agents[aid](observations[aid]) for aid in env.agents
            }
            observations, rewards, terms, truncs, _ = env.step(actions)
            for aid in env.possible_agents:
                ep_rewards[aid] += rewards.get(aid, 0.0)
            if all(terms.values()) or all(truncs.values()):
                break

        for aid in env.possible_agents:
            all_rewards.append(ep_rewards[aid])

    return np.array(all_rewards)


def print_table(title, rows):
    """Print a formatted results table."""
    print()
    print("=" * 62)
    print(title)
    print("=" * 62)
    print(f"{'Scenario':<30} {'Mean Reward':>15} {'Std':>15}")
    print("-" * 62)
    for label, rewards in rows:
        print(f"{label:<30} {rewards.mean():>15.2f} {rewards.std():>15.2f}")
    print()


if __name__ == "__main__":
    # 0. Sanity check: 1-agent multi-agent vs single-agent (should match exactly)
    ma_sanity = run_multi_agent(num_agents=1, enable_bd=False)

    # 1. Single-agent knapsack
    sa_rewards = run_single_agent()

    # 2. Knapsack vs knapsack, no BD, no competition
    ma_no_bd = run_multi_agent(num_agents=2, enable_bd=False)

    # 3. Knapsack vs knapsack, BD enabled, no competition
    ma_with_bd = run_multi_agent(num_agents=2, enable_bd=True)

    # 4. Knapsack vs knapsack, BD enabled, market competition ON
    ma_with_competition = run_multi_agent(
        num_agents=2, enable_bd=True,
        disable_market_share_competition=False,
    )

    n = NUM_EPISODES
    print_table("RESULTS", [
        (f"Single-agent ({n} ep)", sa_rewards),
        (f"Multi-agent 1-agent ({n} ep)", ma_sanity),
        (f"Multi-agent 2-agent no BD ({n*2} s)", ma_no_bd),
        (f"Multi-agent 2-agent BD on ({n*2} s)", ma_with_bd),
        (f"Multi-agent 2-agent BD+comp ({n*2} s)", ma_with_competition),
    ])

    # Sanity check: 1-agent multi-agent vs single-agent
    print("SANITY CHECK (single-agent vs 1-agent multi-agent):")
    diff = abs(sa_rewards.mean() - ma_sanity.mean())
    pct = diff / abs(sa_rewards.mean()) * 100 if sa_rewards.mean() != 0 else 0
    print(f"  Mean reward diff: {diff:.2f} ({pct:.2f}%)")
    match = "PASS" if pct < 1 else "FAIL"
    print(f"  Status: {match}")

    print()
    print("BD IMPACT (no competition):")
    bd_uplift = ma_with_bd.mean() - ma_no_bd.mean()
    pct = bd_uplift / abs(ma_no_bd.mean()) * 100 if ma_no_bd.mean() != 0 else 0
    print(f"  Reward uplift from BD: {bd_uplift:+.2f} ({pct:+.1f}%)")

    print()
    print("COMPETITION IMPACT (BD on, competition on vs off):")
    comp_diff = ma_with_competition.mean() - ma_with_bd.mean()
    pct = comp_diff / abs(ma_with_bd.mean()) * 100 if ma_with_bd.mean() != 0 else 0
    print(f"  Reward change from competition: {comp_diff:+.2f} ({pct:+.1f}%)")
