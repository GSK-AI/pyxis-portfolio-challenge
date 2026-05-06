"""Knapsack-based heuristic agent for multi-agent competitive environment."""

import math

import numpy as np

from pyxis_portfolio_challenge.game.asset import AssetState, DrugAsset
from pyxis_portfolio_challenge.game.constants import DISCOUNT_RATE
from pyxis_portfolio_challenge.game.shared_market_state import indication_key


def delta_npv(asset: DrugAsset) -> float:
    """Compute the value of investing now vs delaying one step."""
    current_npv = asset.enpv
    if current_npv <= 0:
        return 0
    delayed_asset = asset.evolve()
    return current_npv - DISCOUNT_RATE * delayed_asset.enpv


# Sentinel to distinguish BD items from regular investment items
_BD_ITEM = "bd"
_INV_ITEM = "inv"


class MultiAgentKnapsackAgent:
    """
    Knapsack-based heuristic agent for multi-agent environment.

    Uses the same knapsack optimization as single-agent KnapsackAgent
    but adapted to work with the MultiAgentInvestmentGameEnv interface.

    When BD bidding is enabled, BD assets are included in the same
    knapsack optimization as regular idle assets. The solver picks
    the optimal combination of investments and BD acquisitions
    within the available budget.
    """

    CAPACITY_PER_INVESTMENT = 1

    def __init__(
        self,
        env,
        agent_name: str,
        units: float = 1e6,
        include_ongoing_costs: bool = False,
        enable_bd_bidding: bool = False,
        use_alert_discounting: bool = False,
        contested_ta_discount: float = 0.5,
        use_reinvestment_in_valuation: bool = False,
    ):
        """Initialize multi-agent knapsack agent."""
        self.set_env(env)
        self.agent_name = agent_name
        self.units = units
        self.include_ongoing_costs = include_ongoing_costs
        self.enable_bd_bidding = enable_bd_bidding
        self.use_alert_discounting = use_alert_discounting
        self.contested_ta_discount = contested_ta_discount
        self.use_reinvestment_in_valuation = use_reinvestment_in_valuation

    def set_env(self, env):
        self.env = env

    def _expected_market_share(self, asset: DrugAsset) -> float:
        """
        Estimate per-drug market share a new drug would get in its indication.

        Uses a quality-weighted estimate consistent with the per-drug share
        formula in market_mechanics. Returns a fraction in (0, 1].
        If the indication is under rival exclusivity, returns 0.
        """
        shared = self.env.multi_agent_game.shared_market
        current_time = self.env.multi_agent_game.time
        portfolios = self.env.agent_portfolios

        if shared.indications_per_ta > 0:
            key = indication_key(asset.therapeutic_area, asset.indication)
            ind_market = shared.indication_markets.get(key)
            if ind_market is not None:
                if ind_market.is_in_exclusivity(current_time):
                    if ind_market.first_mover_agent != self.agent_name:
                        return 0.0
                    return 1.0
                # Estimate quality-weighted share for new drug
                new_quality = asset.max_revenue
                total_quality = new_quality
                for portfolio in portfolios.values():
                    for a in portfolio.assets.values():
                        if (
                            a.therapeutic_area == asset.therapeutic_area
                            and a.indication == asset.indication
                            and a.state == AssetState.OnMarket
                        ):
                            tenure_bonus = 1.0 + a.time_on_market * 0.05
                            total_quality += a.max_revenue * tenure_bonus
                if total_quality <= new_quality:
                    return 1.0
                return new_quality / total_quality
        else:
            ta_market = shared.ta_markets.get(asset.therapeutic_area)
            if ta_market is not None:
                if ta_market.is_in_exclusivity(current_time):
                    if ta_market.first_mover_agent != self.agent_name:
                        return 0.0
                    return 1.0
                new_quality = asset.max_revenue
                total_quality = new_quality
                for portfolio in portfolios.values():
                    for a in portfolio.assets.values():
                        if (
                            a.therapeutic_area == asset.therapeutic_area
                            and a.state == AssetState.OnMarket
                        ):
                            tenure_bonus = 1.0 + a.time_on_market * 0.05
                            total_quality += a.max_revenue * tenure_bonus
                if total_quality <= new_quality:
                    return 1.0
                return new_quality / total_quality
        return 1.0

    def _get_contested_tas(self) -> set[str]:
        """Return TAs where alerts indicate competitor activity."""
        shared = self.env.multi_agent_game.shared_market
        alerts = shared.get_alerts_for_agent(self.agent_name)
        contested = set()
        for alert in alerts:
            contested.add(alert.therapeutic_area)
        return contested

    def knapsack_01_solver(self, items, capacity):
        """
        Solve 0-1 knapsack problem using dynamic programming.

        Items are tuples of (value, weight, identifier).
        Returns selected items.
        """
        n = len(items)
        if capacity <= 0 or n == 0:
            return []

        dp = [[0] * (capacity + 1) for _ in range(n + 1)]

        for i in range(1, n + 1):
            value, weight, _ = items[i - 1]
            for w in range(1, capacity + 1):
                dp[i][w] = dp[i - 1][w]
                if weight <= w:
                    dp[i][w] = max(
                        dp[i - 1][w],
                        dp[i - 1][w - weight] + value,
                    )

        selected_items = []
        w = capacity
        for i in range(n, 0, -1):
            if dp[i][w] != dp[i - 1][w]:
                selected_items.append(items[i - 1])
                w -= items[i - 1][1]

        return selected_items

    def __call__(self, observation) -> dict:
        """Return action based on knapsack optimization with capacity awareness."""
        portfolio = self.env.agent_portfolios[self.agent_name]
        masks = self.env.action_masks(self.agent_name)

        budget = portfolio.cash

        investments = np.zeros(self.env.max_num_assets, dtype=np.int64)
        bd_bids = np.zeros(self.env.bd_max_slots, dtype=np.int64)

        if budget <= 0:
            pricing = np.full(self.env.max_num_assets, 2, dtype=np.int64)
            return {"investments": investments, "bd_bids": bd_bids, "pricing": pricing}

        # Capacity constraint: use override if set, otherwise check env config
        capacity_override = getattr(self, '_capacity_override', None)
        if capacity_override is not None:
            cap = capacity_override
        elif getattr(self.env.rd_capacity_config, 'enabled', False):
            cap = portfolio.capacity_base
        else:
            cap = 999
        current_in_dev = sum(
            1 for a in portfolio.assets.values()
            if a.state == AssetState.InDevelopment
        )
        remaining_capacity = max(0, cap - current_in_dev)
        if remaining_capacity <= 0:
            pricing = np.full(self.env.max_num_assets, 2, dtype=np.int64)
            return {"investments": investments, "bd_bids": bd_bids, "pricing": pricing}

        contested_tas = (
            self._get_contested_tas()
            if self.use_alert_discounting
            else set()
        )

        # Build knapsack items from regular idle assets
        items = []
        asset_order = self.env._asset_id_orders[self.agent_name]

        for i, asset_id in enumerate(asset_order):
            if asset_id is None or asset_id not in portfolio.assets:
                continue
            inv_mask = masks["investments"][i]
            # Support both binary mask (0/1) and MultiDiscrete mask (list of bools)
            if isinstance(inv_mask, list):
                # Can invest if any level > 0 is valid (e.g. STANDARD = index 2)
                can_invest = len(inv_mask) > 2 and inv_mask[2]
            else:
                can_invest = inv_mask == 1
            if not can_invest:
                continue

            asset = portfolio.assets[asset_id]
            value = delta_npv(asset)
            if value <= 0:
                continue

            # Filter out assets where reinvestment-scaled expected revenue
            # doesn't cover expected trial costs — these are unprofitable
            # at the actual cash return rate the agent receives.
            if self.use_reinvestment_in_valuation:
                reinv_pct = portfolio.reinvestment_percentage
                exp_costs, exp_revs = asset.expected_costs_and_revenues
                if sum(exp_revs) * reinv_pct < sum(exp_costs):
                    continue
                value *= reinv_pct

            # Discount value if competitor is active in this TA
            if asset.therapeutic_area in contested_tas:
                value *= self.contested_ta_discount

            weight = math.ceil(
                asset.remaining_trial_cost / self.units
            )
            if weight > 0:
                items.append((value, weight, (_INV_ITEM, i)))

        # Add BD assets as additional knapsack items (one per slot)
        if self.enable_bd_bidding and self.env.bd_enabled:
            shared = self.env.multi_agent_game.shared_market
            bd_assets = shared.current_bd_assets
            n_current = len(portfolio.assets)
            slots_free = portfolio.max_num_assets - n_current

            for slot_idx, bd_asset in enumerate(bd_assets):
                if slots_free <= 0:
                    break
                enpv = bd_asset.enpv
                if enpv > 0:
                    value = delta_npv(bd_asset)
                    if value > 0 and self.use_reinvestment_in_valuation:
                        reinv_pct = portfolio.reinvestment_percentage
                        exp_costs, exp_revs = bd_asset.expected_costs_and_revenues
                        if sum(exp_revs) * reinv_pct < sum(exp_costs):
                            continue
                        value *= reinv_pct
                    if value > 0:
                        ms = self._expected_market_share(bd_asset)
                        if ms > 0:
                            value *= ms
                            from pyxis_portfolio_challenge.environment.market_mechanics import (
                                bd_bid_price,
                            )

                            break_even = shared.bd_break_even_bid_level
                            reinv_pct = portfolio.reinvestment_percentage
                            bid_level = min(3, self.env.bd_num_bid_levels - 1)
                            bid_price = bd_bid_price(enpv, bid_level, break_even, reinv_pct)
                            total_cost = bid_price + bd_asset.remaining_trial_cost
                            weight = math.ceil(total_cost / self.units)
                            if weight > 0:
                                items.append(
                                    (value, weight, (_BD_ITEM, (slot_idx, bid_level)))
                                )

        # Solve knapsack for optimal mix (budget constraint)
        budget_rescaled = math.floor(budget / self.units)

        if items and budget_rescaled > 0:
            selected = self.knapsack_01_solver(items, budget_rescaled)
            # Sort by value descending so capacity limit keeps the best items
            selected.sort(key=lambda x: x[0], reverse=True)
            capacity_left = int(remaining_capacity)
            for _, _, (item_type, idx) in selected:
                if item_type == _INV_ITEM:
                    if capacity_left <= 0:
                        continue
                    investments[idx] = 1
                    capacity_left -= self.CAPACITY_PER_INVESTMENT
                elif item_type == _BD_ITEM:
                    if capacity_left <= 0:
                        continue
                    slot_idx, bid_level = idx
                    bd_bids[slot_idx] = bid_level
                    capacity_left -= self.CAPACITY_PER_INVESTMENT

        return {
            "investments": investments,
            "bd_bids": bd_bids,
        }
