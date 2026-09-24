"""
Opponent agent runner for multi-agent web games.

Adapts existing single-agent agents to produce investment actions and BD bids
for use in MultiAgentGame.step().
"""

import logging
import random
import uuid

from pyxis_portfolio_challenge.agents.knapsack import KnapsackAgent
from pyxis_portfolio_challenge.agents.utils import get_agent_investment_decisions
from pyxis_portfolio_challenge.game.asset import AssetState
from pyxis_portfolio_challenge.game.constants import InvestmentLevel
from pyxis_portfolio_challenge.game.multi_agent_game import MultiAgentGame

logger = logging.getLogger(__name__)

# Fun display names per agent type, sampled without replacement on game start
AGENT_DISPLAY_NAMES: dict[str, list[str]] = {
    "knapsack": [
        "Meridian Therapeutics",
        "Apex BioCapital",
        "Pinnacle Pharma",
        "Summit Health Partners",
        "Vanguard Biologics",
        "Precision Capital Rx",
        "Ledger Life Sciences",
        "Abacus BioPharma",
    ],
    "random": [
        "Chaos Pharmaceuticals",
        "Wildcard Biologics",
        "Dice Roll Therapeutics",
        "Entropy Health",
        "Scattershot Pharma",
        "Roulette BioSciences",
        "Coin Flip Labs",
        "Stochastic Rx",
    ],
    "do_nothing": [
        "Idle Pharma",
        "Inertia Therapeutics",
        "Dormant BioCapital",
        "Passive Health Partners",
        "Benchwarmer Biologics",
        "Standby Sciences",
        "Spectator Rx",
        "Sideline Labs",
    ],
}


def generate_opponent_display_names(opponent_types: list[str], seed: int) -> list[str]:
    """Pick fun display names for opponents, sampling without replacement per type."""
    rng = random.Random(seed)
    used_per_type: dict[str, list[str]] = {}
    display_names = []

    for agent_type in opponent_types:
        pool = AGENT_DISPLAY_NAMES.get(agent_type, [])
        if agent_type not in used_per_type:
            used_per_type[agent_type] = []

        available = [n for n in pool if n not in used_per_type[agent_type]]
        if not available:
            # Exhausted the pool, fall back
            available = (
                pool if pool else [f"{agent_type.replace('_', ' ').title()} Inc."]
            )

        name = rng.choice(available)
        used_per_type[agent_type].append(name)
        display_names.append(name)

    return display_names


# Map agent type strings to factory functions for knapsack-based agents.
OPPONENT_AGENT_FACTORIES = {
    "knapsack": lambda: KnapsackAgent(),
}

AVAILABLE_OPPONENTS = [
    {
        "id": "knapsack",
        "name": "Knapsack",
        "description": (
            "Budget-optimizing heuristic that solves a 0/1 knapsack each step"
        ),
    },
    {
        "id": "random",
        "name": "Random",
        "description": "Randomly invests in available assets each step",
    },
    {
        "id": "do_nothing",
        "name": "Do Nothing",
        "description": "Never invests — passive baseline opponent",
    },
]


def init_asset_id_orders(
    multi_game: MultiAgentGame,
    max_num_assets: int,
) -> dict[str, list]:
    """Initialize asset orderings for all agents (same logic as env.reset())."""
    asset_id_orders = {}
    for agent_name, game_state in multi_game.agent_states.items():
        asset_ids = list(game_state.assets.keys())
        asset_order = asset_ids + [None] * (max_num_assets - len(asset_ids))
        asset_id_orders[agent_name] = asset_order
    return asset_id_orders


def update_asset_id_orders(
    multi_game: MultiAgentGame,
    asset_id_orders: dict[str, list],
) -> None:
    """
    Update asset orderings after a game step.

    Same logic as env._update_asset_orderings().
    """
    for agent_name, game_state in multi_game.agent_states.items():
        asset_order = asset_id_orders[agent_name]

        # Remove stale entries to free up slots
        for i in range(len(asset_order)):
            if (
                asset_order[i] is not None
                and asset_order[i] not in game_state.assets
            ):
                asset_order[i] = None

        # Add new assets to available slots
        ordered_ids = {aid for aid in asset_order if aid is not None}
        for asset_id in game_state.assets:
            if asset_id not in ordered_ids:
                for i in range(len(asset_order)):
                    if asset_order[i] is None:
                        asset_order[i] = asset_id
                        break


def get_opponent_actions(
    agent_type: str,
    agent_name: str,
    multi_game: MultiAgentGame,
    asset_id_orders: dict[str, list] | None = None,
) -> tuple[dict[uuid.UUID, InvestmentLevel | None], list[float]]:
    """
    Get investment actions and BD bids for an opponent agent.

    Returns:
        Tuple of (investment_actions, bd_bids).
        investment_actions: dict mapping asset UUID to InvestmentLevel.
        bd_bids: per-BD-slot cash bids in GBP (0.0 = pass). The highest bid
            wins and pays its own bid; an overbid can bankrupt the winner.

    """
    game_state = multi_game.agent_states[agent_name]

    # Skip bankrupt agents
    if game_state.game_ended:
        empty_actions: dict[uuid.UUID, InvestmentLevel | None] = {}
        return empty_actions, []

    if agent_type == "do_nothing":
        return {}, []

    if agent_type == "random":
        return _get_random_actions(agent_name, multi_game)

    return _get_knapsack_actions(agent_type, agent_name, multi_game)


def _get_random_actions(
    agent_name: str,
    multi_game: MultiAgentGame,
) -> tuple[dict[uuid.UUID, InvestmentLevel | None], list[float]]:
    """Randomly invest in idle assets."""
    game_state = multi_game.agent_states[agent_name]
    investment_actions: dict[uuid.UUID, InvestmentLevel | None] = {}
    for asset_id, asset in game_state.assets.items():
        if asset.state == AssetState.Idle:
            investment_actions[asset_id] = (
                InvestmentLevel.STANDARD if random.random() > 0.5 else None
            )
        else:
            investment_actions[asset_id] = None
    # Random per-slot BD cash bids in GBP (0 = pass), capped at 30% of cash so
    # the random baseline does not routinely bankrupt itself via overbids.
    num_bd_slots = len(multi_game.shared_market.current_bd_assets)
    cap = max(0.0, game_state.cash * 0.3)
    bd_bids = [
        random.uniform(0.0, cap) if random.random() > 0.5 else 0.0
        for _ in range(num_bd_slots)
    ]
    return investment_actions, bd_bids




def _get_knapsack_actions(
    agent_type: str,
    agent_name: str,
    multi_game: MultiAgentGame,
) -> tuple[dict[uuid.UUID, InvestmentLevel | None], list[float]]:
    """Get actions from the knapsack heuristic agent."""
    game_state = multi_game.agent_states[agent_name]

    if agent_type not in OPPONENT_AGENT_FACTORIES:
        logger.warning(f"Unknown agent type '{agent_type}', using knapsack")
        agent_type = "knapsack"

    agent = OPPONENT_AGENT_FACTORIES[agent_type]()
    decisions = get_agent_investment_decisions(agent, game_state)

    # Convert "invest" string decisions to InvestmentLevel
    investment_actions: dict[uuid.UUID, InvestmentLevel | None] = {}
    for asset_id, decision in decisions.items():
        if decision == "invest":
            investment_actions[asset_id] = InvestmentLevel.STANDARD
        else:
            investment_actions[asset_id] = None

    # No explicit capacity cap: concurrent-trial throughput is limited
    # naturally by the clinical-sites feature at the environment level.

    # No BD bidding for knapsack in the app
    return investment_actions, []
