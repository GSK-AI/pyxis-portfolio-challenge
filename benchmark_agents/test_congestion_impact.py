"""
Quick test: compare greedy-top-4 profitability with old vs new congestion params.

Old (main): congestion_exponent=2.0, congestion_incumbent_penalty=0.15
New (branch): congestion_exponent=3.0, congestion_incumbent_penalty=0.20
"""

import json
import logging
import os
from pathlib import Path

import numpy as np

from pyxis_portfolio_challenge import logging_utils
from pyxis_portfolio_challenge.config import config, instantiate_from_config
from pyxis_portfolio_challenge.environment.multi_agent_evaluate import (
    parallel_evaluate_multi_agent,
)
from pyxis_portfolio_challenge.environment.multi_agent_training_gym import (
    MultiAgentInvestmentGameEnv,
)

logging_utils.setup_logging(logging.WARNING)

NUM_EPISODES = 50
NUM_AGENTS = 4
STARTING_CASH = 500e9


class GreedyPositiveENPVAgent:
    """Invests in every idle asset with positive eNPV."""

    def __init__(self, agent_name: str):
        self.env = None
        self.agent_name = agent_name

    def set_env(self, env):
        self.env = env

    def __call__(self, observation) -> dict:
        portfolio = self.env.agent_portfolios[self.agent_name]
        masks = self.env.action_masks(self.agent_name)

        investments = np.zeros(self.env.max_num_assets, dtype=np.int64)
        bd_bids = np.zeros(self.env.bd_max_slots, dtype=np.int64)

        asset_order = self.env._asset_id_orders[self.agent_name]
        for i, asset_id in enumerate(asset_order):
            if asset_id is None or asset_id not in portfolio.assets:
                continue
            inv_mask = masks["investments"][i]
            if isinstance(inv_mask, list):
                can_invest = len(inv_mask) > 2 and inv_mask[2]
            else:
                can_invest = bool(inv_mask)
            if not can_invest:
                continue
            asset = portfolio.assets[asset_id]
            if asset.enpv > 0:
                investments[i] = 1

        if self.env.bd_enabled:
            shared = self.env.multi_agent_game.shared_market
            bd_assets = shared.current_bd_assets
            bd_masks = masks["bd_bids"]
            for slot_idx, bd_asset in enumerate(bd_assets):
                if slot_idx >= self.env.bd_max_slots:
                    break
                if bd_asset.enpv > 0:
                    slot_mask = bd_masks[slot_idx]
                    bid = 0
                    for level in [3, 2, 1]:
                        if level < len(slot_mask) and slot_mask[level]:
                            bid = level
                            break
                    bd_bids[slot_idx] = bid

        pricing = np.zeros(self.env.max_num_assets, dtype=np.int64) + 2
        return {"investments": investments, "bd_bids": bd_bids, "pricing": pricing}


def _build_env_kwargs(
    congestion_exponent: float,
    congestion_incumbent_penalty: float,
    trial_cost_multiplier: float | None = None,
) -> dict:
    cfg = config
    ma = cfg.multi_agent
    return dict(
        assets_dir=cfg.evaluation_data_dir,
        num_agents=NUM_AGENTS,
        starting_cash=STARTING_CASH,
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
        trial_cost_multiplier=trial_cost_multiplier if trial_cost_multiplier is not None else cfg.trial_cost_multiplier,
        # Override congestion params
        congestion_exponent=congestion_exponent,
        congestion_ramp_steps=ma.congestion_ramp_steps,
        congestion_incumbent_penalty=congestion_incumbent_penalty,
        pricing_config=config.pricing,
    )


def run_benchmark(label: str, tag: str, congestion_exp: float, congestion_inc: float, trial_cost_mult: float | None = None):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  congestion_exponent={congestion_exp}, incumbent_penalty={congestion_inc}, trial_cost_mult={trial_cost_mult or 'config'}")
    print(f"{'='*60}")

    cfg = config
    env_kwargs = _build_env_kwargs(congestion_exp, congestion_inc, trial_cost_mult)

    tmp_env = MultiAgentInvestmentGameEnv(**env_kwargs)
    agents = {}
    for agent_name in tmp_env.possible_agents:
        agents[agent_name] = GreedyPositiveENPVAgent(agent_name=agent_name)

    num_workers = max(1, os.cpu_count() // 2)

    original_num = cfg.num_eval_episodes
    object.__setattr__(cfg, "num_eval_episodes", NUM_EPISODES)

    all_reports, global_report, _ = parallel_evaluate_multi_agent(
        agents=agents,
        num_workers=num_workers,
        env_kwargs=env_kwargs,
        warmup_steps=cfg.warmup_on_reset_steps,
    )

    object.__setattr__(cfg, "num_eval_episodes", original_num)

    # Save full metrics JSON
    output_dir = Path("benchmark_agents/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"congestion_test_{tag}.json"
    save_data = {
        "config": {"congestion_exponent": congestion_exp, "congestion_incumbent_penalty": congestion_inc},
        "per_agent": all_reports,
        "global": global_report,
    }
    with open(out_file, "w") as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"  Saved to {out_file}")

    # Print summary for agent_0
    for agent_id, report_list in all_reports.items():
        print(f"\n  {agent_id}:")
        for category_dict in report_list:
            for category, metrics in category_dict.items():
                for metric_dict in metrics:
                    for key, val in metric_dict.items():
                        if any(kw in key for kw in ["NCF", "Cumulative", "Cash", "Bankruptcy", "ROI", "PnL"]):
                            print(f"    {key}: {val}")
        break  # Just show one agent (they're symmetric)


if __name__ == "__main__":
    # Old congestion + current trial_cost_multiplier (1.5)
    run_benchmark("OLD congestion, cost_mult=1.5", "old_cong_cost15", 2.0, 0.15)

    # New congestion + current trial_cost_multiplier (1.5)
    run_benchmark("NEW congestion, cost_mult=1.5", "new_cong_cost15", 3.0, 0.20)

    # Old congestion + trial_cost_multiplier=1.0
    run_benchmark("OLD congestion, cost_mult=1.0", "old_cong_cost10", 2.0, 0.15, trial_cost_mult=1.0)

    # New congestion + trial_cost_multiplier=1.0
    run_benchmark("NEW congestion, cost_mult=1.0", "new_cong_cost10", 3.0, 0.20, trial_cost_mult=1.0)
