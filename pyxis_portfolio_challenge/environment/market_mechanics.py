"""Market mechanics for multi-agent competitive environment."""

from __future__ import annotations

import logging
import random
import uuid

from pyxis_portfolio_challenge.game.asset import AssetState, DrugAsset
from pyxis_portfolio_challenge.game.game_state import GameState
from pyxis_portfolio_challenge.game.shared_market_state import (
    THERAPEUTIC_AREAS,
    SharedMarketState,
    indication_key,
)

logger = logging.getLogger(__name__)


def bd_bid_price(
    enpv: float,
    level: int,
    break_even_level: int,
    reinvestment_percentage: float,
) -> float:
    """
    Compute the cash price for a BD bid level.

    Scaled so that ``break_even_level`` pays exactly
    ``enpv * reinvestment_percentage`` (the agent's expected cash value).
    Levels above break-even overpay for strategic gain.
    """
    return (level / break_even_level) * enpv * reinvestment_percentage


def resolve_bd_bid(
    bids: dict[str, int],
    asset: DrugAsset,
    num_levels: int,
    break_even_level: int,
    reinvestment_percentage: float,
    rng: random.Random,
) -> tuple[str | None, float]:
    """
    Resolve a single BD asset auction. Highest bid wins (first-price sealed-bid).

    Args:
        bids: Dict mapping agent_id -> bid level (0=pass, 1-N = fraction of eNPV).
        asset: The BD asset being auctioned.
        num_levels: Total number of bid levels (e.g., 11 for 0-10).
        break_even_level: Level at which price = eNPV * reinvestment_percentage.
        reinvestment_percentage: Fraction of revenue captured as cash.
        rng: Random number generator for tie-breaking.

    Returns:
        Tuple of (winner_agent_id, price_paid) or (None, 0.0) if no bids.

    """
    enpv = asset.enpv
    active_bids: list[tuple[str, int, float]] = []

    for agent_id, level in bids.items():
        if level <= 0:
            continue
        price = bd_bid_price(enpv, level, break_even_level, reinvestment_percentage)
        active_bids.append((agent_id, level, price))

    if not active_bids:
        return None, 0.0

    # Sort by level (highest first)
    active_bids.sort(key=lambda x: x[1], reverse=True)
    highest_level = active_bids[0][1]
    top_bidders = [b for b in active_bids if b[1] == highest_level]

    if len(top_bidders) > 1:
        rng.shuffle(top_bidders)

    winner_agent, _, winner_price = top_bidders[0]
    logger.info(
        f"BD Auction: {winner_agent} wins {asset.name} "
        f"(level {highest_level}/{num_levels - 1}, price ${winner_price:,.0f})"
    )
    return winner_agent, winner_price


def calculate_per_drug_indication_shares(
    therapeutic_area: str,
    indication: int,
    shared_market: SharedMarketState,
    agent_portfolios: dict[str, GameState],
    current_time: int,
    pricing_multipliers: dict[uuid.UUID, float] | None = None,
    pricing_elasticity: float = 1.0,
) -> dict[uuid.UUID, float]:
    """
    Compute market share for each on-market drug in an indication.

    Each drug competes individually against all other drugs (own + rival).
    First mover bonus applies to the specific first mover drug, not the agent.
    When the first mover drug expires, the bonus disappears.
    """
    if shared_market.disable_market_share_competition:
        shares: dict[uuid.UUID, float] = {}
        for portfolio in agent_portfolios.values():
            for asset in portfolio.assets.values():
                if (
                    asset.therapeutic_area == therapeutic_area
                    and asset.indication == indication
                    and asset.state == AssetState.OnMarket
                ):
                    shares[asset.id] = 1.0
        return shares

    key = indication_key(therapeutic_area, indication)
    ind_market = shared_market.indication_markets.get(key)
    if ind_market is None:
        return {}

    # Collect all on-market drugs and their qualities
    drug_qualities: dict[uuid.UUID, float] = {}
    for portfolio in agent_portfolios.values():
        for asset in portfolio.assets.values():
            if (
                asset.therapeutic_area == therapeutic_area
                and asset.indication == indication
                and asset.state == AssetState.OnMarket
            ):
                tenure_bonus = 1.0 + asset.time_on_market * 0.05
                # demand elasticity: quality = max_rev * (1/price^elast) * tenure
                price_mult = 1.0
                if pricing_multipliers is not None:
                    price_mult = pricing_multipliers.get(asset.id, 1.0)
                price_quality = 1.0 / (price_mult**pricing_elasticity)
                drug_qualities[asset.id] = (
                    asset.max_revenue * price_quality * tenure_bonus
                )

    if not drug_qualities:
        return {}

    # During exclusivity: first mover drug gets 1.0, all others 0.0
    first_mover_drug_id = ind_market.first_mover_drug_id
    if ind_market.is_in_exclusivity(current_time):
        return {
            drug_id: (1.0 if drug_id == first_mover_drug_id else 0.0)
            for drug_id in drug_qualities
        }

    # Post-exclusivity: per-drug quality-weighted shares
    total_quality = sum(drug_qualities.values())
    first_mover_bonus = shared_market.first_mover_bonus

    # First mover bonus only applies if the first mover drug is still on market
    first_mover_active = (
        first_mover_drug_id is not None and first_mover_drug_id in drug_qualities
    )

    shares = {}
    for drug_id, quality in drug_qualities.items():
        proportional = quality / total_quality
        if first_mover_active and drug_id == first_mover_drug_id:
            shares[drug_id] = first_mover_bonus + (1 - first_mover_bonus) * proportional
        elif first_mover_active:
            shares[drug_id] = (1 - first_mover_bonus) * proportional
        else:
            shares[drug_id] = proportional

    # Apply congestion penalty: reduces total revenue when many drugs compete
    # Penalty scales with position in entry_order
    congestion_exp = shared_market.congestion_exponent
    if len(drug_qualities) > 1 and congestion_exp > 0:
        n_drugs = len(drug_qualities)
        ramp_steps = shared_market.congestion_ramp_steps
        incumbent_base = shared_market.congestion_incumbent_penalty
        entry_order = ind_market.entry_order
        position_map = {drug_id: i for i, drug_id in enumerate(entry_order)}
        for drug_id in shares:
            pos = position_map.get(drug_id, len(entry_order))
            ramp = min(pos / ramp_steps, 1.0) if ramp_steps > 0 else 1.0
            penalty_fraction = incumbent_base + (1.0 - incumbent_base) * ramp
            exp = congestion_exp * penalty_fraction
            shares[drug_id] *= 1.0 / (n_drugs**exp)

    return shares


def calculate_per_drug_ta_shares(
    therapeutic_area: str,
    shared_market: SharedMarketState,
    agent_portfolios: dict[str, GameState],
    current_time: int,
    pricing_multipliers: dict[uuid.UUID, float] | None = None,
    pricing_elasticity: float = 1.0,
) -> dict[uuid.UUID, float]:
    """Compute per-drug market shares within a TA."""
    if shared_market.disable_market_share_competition:
        shares: dict[uuid.UUID, float] = {}
        for portfolio in agent_portfolios.values():
            for asset in portfolio.assets.values():
                if (
                    asset.therapeutic_area == therapeutic_area
                    and asset.state == AssetState.OnMarket
                ):
                    shares[asset.id] = 1.0
        return shares

    ta_market = shared_market.ta_markets.get(therapeutic_area)
    if ta_market is None:
        return {}

    drug_qualities: dict[uuid.UUID, float] = {}
    for portfolio in agent_portfolios.values():
        for asset in portfolio.assets.values():
            if (
                asset.therapeutic_area == therapeutic_area
                and asset.state == AssetState.OnMarket
            ):
                tenure_bonus = 1.0 + asset.time_on_market * 0.05
                price_mult = 1.0
                if pricing_multipliers is not None:
                    price_mult = pricing_multipliers.get(asset.id, 1.0)
                price_quality = 1.0 / (price_mult**pricing_elasticity)
                drug_qualities[asset.id] = (
                    asset.max_revenue * price_quality * tenure_bonus
                )

    if not drug_qualities:
        return {}

    first_mover_drug_id = ta_market.first_mover_drug_id
    if ta_market.is_in_exclusivity(current_time):
        return {
            drug_id: (1.0 if drug_id == first_mover_drug_id else 0.0)
            for drug_id in drug_qualities
        }

    total_quality = sum(drug_qualities.values())
    first_mover_bonus = shared_market.first_mover_bonus
    first_mover_active = (
        first_mover_drug_id is not None and first_mover_drug_id in drug_qualities
    )

    shares = {}
    for drug_id, quality in drug_qualities.items():
        proportional = quality / total_quality
        if first_mover_active and drug_id == first_mover_drug_id:
            shares[drug_id] = first_mover_bonus + (1 - first_mover_bonus) * proportional
        elif first_mover_active:
            shares[drug_id] = (1 - first_mover_bonus) * proportional
        else:
            shares[drug_id] = proportional

    # Apply congestion penalty (position-based ramp using entry order)
    congestion_exp = shared_market.congestion_exponent
    if len(drug_qualities) > 1 and congestion_exp > 0:
        n_drugs = len(drug_qualities)
        ramp_steps = shared_market.congestion_ramp_steps
        incumbent_base = shared_market.congestion_incumbent_penalty
        entry_order = ta_market.entry_order
        position_map = {drug_id: i for i, drug_id in enumerate(entry_order)}
        for drug_id in shares:
            pos = position_map.get(drug_id, len(entry_order))
            ramp = min(pos / ramp_steps, 1.0) if ramp_steps > 0 else 1.0
            penalty_fraction = incumbent_base + (1.0 - incumbent_base) * ramp
            exp = congestion_exp * penalty_fraction
            shares[drug_id] *= 1.0 / (n_drugs**exp)

    return shares


def calculate_agent_market_shares(
    agent_id: str,
    shared_market: SharedMarketState,
    agent_portfolios: dict[str, GameState],
    current_time: int,
    all_pricing_multipliers: dict[uuid.UUID, float] | None = None,
    pricing_elasticity: float = 1.0,
) -> dict[uuid.UUID, float]:
    """
    Calculate per-drug market shares for a specific agent's on-market drugs.

    Returns a dict mapping asset_id -> market share for each of this agent's
    on-market drugs. Each drug competes individually against all other drugs
    in its indication (including the agent's own drugs).

    Args:
        agent_id: Identifier of the agent whose market shares are being calculated.
        shared_market: Shared market state containing indication markets and TA info.
        agent_portfolios: Dict mapping agent_id -> GameState for all agents.
        current_time: Current simulation time step.
        all_pricing_multipliers: Merged pricing multipliers from ALL agents'
            on-market drugs (asset_id -> price_mult). Used in quality formula.
        pricing_elasticity: Demand elasticity for price-share tradeoff.

    """
    agent_drug_ids = {
        asset.id
        for asset in agent_portfolios[agent_id].assets.values()
        if asset.state == AssetState.OnMarket
    }

    shares: dict[uuid.UUID, float] = {}

    if shared_market.indications_per_ta > 0:
        for ind_market in shared_market.indication_markets.values():
            all_drug_shares = calculate_per_drug_indication_shares(
                ind_market.therapeutic_area,
                ind_market.indication,
                shared_market,
                agent_portfolios,
                current_time,
                pricing_multipliers=all_pricing_multipliers,
                pricing_elasticity=pricing_elasticity,
            )
            for drug_id, share in all_drug_shares.items():
                if drug_id in agent_drug_ids:
                    shares[drug_id] = share
    else:
        for ta in THERAPEUTIC_AREAS:
            all_drug_shares = calculate_per_drug_ta_shares(
                ta,
                shared_market,
                agent_portfolios,
                current_time,
                pricing_multipliers=all_pricing_multipliers,
                pricing_elasticity=pricing_elasticity,
            )
            for drug_id, share in all_drug_shares.items():
                if drug_id in agent_drug_ids:
                    shares[drug_id] = share

    return shares
