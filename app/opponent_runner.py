"""
Opponent agent runner for multi-agent web games.

Adapts existing single-agent agents to produce investment actions and BD bids
for use in MultiAgentGame.step().
"""

import logging
import random
import uuid

import numpy as np

from pyxis_portfolio_challenge import config as cfg_module
from pyxis_portfolio_challenge.agents.knapsack import KnapsackAgent
from pyxis_portfolio_challenge.agents.utils import get_agent_investment_decisions
from pyxis_portfolio_challenge.game.asset import AssetState
from pyxis_portfolio_challenge.game.constants import InvestmentLevel
from pyxis_portfolio_challenge.game.multi_agent_game import MultiAgentGame

logger = logging.getLogger(__name__)

# Fun display names per agent type, sampled without replacement on game start
AGENT_DISPLAY_NAMES: dict[str, list[str]] = {
    "knapsack_cap12": [
        "Meridian Therapeutics",
        "Apex BioCapital",
        "Pinnacle Pharma",
        "Summit Health Partners",
        "Vanguard Biologics",
        "Precision Capital Rx",
        "Ledger Life Sciences",
        "Abacus BioPharma",
    ],
    "pyxie": [
        "NeuralRx",
        "Helix Dynamics",
        "AlphaPharm",
        "Tensor Therapeutics",
        "Gradient Labs",
        "Synapse Biologics",
        "Cortex Pharma",
        "Epoch Health",
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


# Maximum concurrent investments for the cap=12 knapsack agent
_KNAPSACK_CAPACITY = 12

# Map agent type strings to factory functions for knapsack-based agents.
OPPONENT_AGENT_FACTORIES = {
    "knapsack_cap12": lambda: KnapsackAgent(),
}

AVAILABLE_OPPONENTS = [
    {
        "id": "knapsack_cap12",
        "name": "Knapsack (cap=12)",
        "description": "Budget-optimizing heuristic with 12-asset capacity limit",
    },
    {
        "id": "pyxie",
        "name": "Pyxie (RL)",
        "description": "Reinforcement learning agent trained via self-play",
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


# ---------------------------------------------------------------------------
# Lazy-loaded singletons for PPO inference
# ---------------------------------------------------------------------------

# Cached inference env per num_agents
_inference_envs: dict[int, object] = {}

# Cached PPO agent per agent_name
_pyxie_agents: dict[str, object] = {}


class _NoopReward:
    """No-op reward for inference-only env (never called)."""

    def compute(self, pre_step_game_state, post_step_game_state):
        return 0.0


def _get_inference_env(num_agents: int):
    """
    Get or create a MultiAgentInvestmentGameEnv for PPO inference.

    The env is created from config but never reset() — we inject
    multi_agent_game and _asset_id_orders before each use.
    """
    if num_agents in _inference_envs:
        return _inference_envs[num_agents]

    from pyxis_portfolio_challenge.environment.multi_agent_training_gym import (
        MultiAgentInvestmentGameEnv,
    )

    game_config = cfg_module.from_yaml()
    ma = game_config.multi_agent

    env = MultiAgentInvestmentGameEnv(
        assets_dir=game_config.training_data_dir,
        num_agents=num_agents,
        starting_cash=game_config.starting_cash,
        max_num_assets=game_config.max_num_assets,
        horizon=game_config.horizon,
        equilibrium_num_assets=game_config.equilibrium_num_assets,
        asset_arrival_sensitivity_below=game_config.asset_arrival_sensitivity_below,
        asset_arrival_sensitivity_above=game_config.asset_arrival_sensitivity_above,
        reinvestment_percentage=game_config.reinvestment_percentage,
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
        reward_fn=_NoopReward(),
        shuffle_order=False,
        mask_first_order_assets=game_config.mask_first_order_assets,
        mask_negative_enpv_assets=game_config.mask_negative_enpv_assets,
        flatten_obs=game_config.flatten_obs,
        distributional_ptrs_config=game_config.distributional_ptrs,
        ta_experience_config=game_config.ta_experience,
        uncertain_ptrs_config=game_config.uncertain_ptrs,
        investment_levels_config=game_config.investment_levels,
        interim_trial_observations_config=game_config.interim_trial_observations,
        rd_capacity_config=game_config.rd_capacity,
        approval_phase_config=game_config.approval_phase,
        pricing_config=game_config.pricing,
        reward_type=ma.reward_type,
        reward_scale=ma.reward_scale,
        max_indications_per_ta=ma.max_indications_per_ta,
        target_drugs_per_indication=ma.target_drugs_per_indication,
        on_market_fraction=ma.on_market_fraction,
        indication_spread=ma.indication_spread,
        indication_drift_speed=ma.indication_drift_speed,
        trial_cost_multiplier=game_config.trial_cost_multiplier,
        congestion_exponent=ma.congestion_exponent,
        congestion_ramp_steps=ma.congestion_ramp_steps,
        congestion_incumbent_penalty=ma.congestion_incumbent_penalty,
    )

    _inference_envs[num_agents] = env
    return env


def _get_pyxie_agent(agent_name: str):
    """Get or create a MultiAgentPyxieAgent for the given agent name."""
    if agent_name in _pyxie_agents:
        return _pyxie_agents[agent_name]

    from pathlib import Path

    from pyxis_portfolio_challenge.agents.multi_agent_pyxie import (
        MultiAgentPyxieAgent,
    )

    model_dir = Path(__file__).parent.parent / (
        "pyxis_portfolio_challenge/agents/saved_multi_agent_model"
    )
    agent = MultiAgentPyxieAgent(
        agent_name=agent_name,
        model_path=model_dir / "best_model.zip",
        vecnorm_path=model_dir / "vecnormalize.pkl",
    )
    _pyxie_agents[agent_name] = agent
    return agent


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
) -> tuple[dict[uuid.UUID, InvestmentLevel | None], int]:
    """
    Get investment actions and BD bids for an opponent agent.

    Returns:
        Tuple of (investment_actions, bd_bid).
        investment_actions: dict mapping asset UUID to InvestmentLevel.
        bd_bid: integer bid level (0=pass).

    """
    game_state = multi_game.agent_states[agent_name]

    # Skip bankrupt agents
    if game_state.game_ended:
        empty_actions: dict[uuid.UUID, InvestmentLevel | None] = {}
        return empty_actions, 0

    if agent_type == "pyxie":
        return _get_pyxie_actions(agent_name, multi_game, asset_id_orders)

    if agent_type == "do_nothing":
        return {}, 0

    if agent_type == "random":
        return _get_random_actions(agent_name, multi_game)

    return _get_knapsack_actions(agent_type, agent_name, multi_game)


def _get_pyxie_actions(
    agent_name: str,
    multi_game: MultiAgentGame,
    asset_id_orders: dict[str, list] | None,
) -> tuple[dict[uuid.UUID, InvestmentLevel | None], int]:
    """Get actions from the trained PPO model."""
    if asset_id_orders is None:
        raise ValueError(
            f"asset_id_orders is required for Pyxie agent '{agent_name}' "
            "but was None — ensure Redis state is initialised before calling."
        )

    num_agents = len(multi_game.agent_states)
    env = _get_inference_env(num_agents)

    # Inject game state into the env
    env.multi_agent_game = multi_game
    env._asset_id_orders = asset_id_orders

    # Build observation
    obs = env._get_observation(agent_name)

    # Get the PPO agent and set env for mask access
    agent = _get_pyxie_agent(agent_name)
    agent.set_env(env)

    # Run inference
    action_dict = agent(obs)

    # Convert array actions to dict[UUID, InvestmentLevel | None]
    asset_order = asset_id_orders[agent_name]
    inv_array = action_dict["investments"]
    investment_actions: dict[uuid.UUID, InvestmentLevel | None] = {}

    use_levels = (
        env.investment_levels_config is not None
        and env.investment_levels_config.enabled
    )

    for i, action_val in enumerate(inv_array):
        if i >= len(asset_order) or asset_order[i] is None:
            continue
        asset_id = asset_order[i]
        if asset_id not in multi_game.agent_states[agent_name].assets:
            continue

        if use_levels:
            level = InvestmentLevel.from_int(int(action_val))
            if level != InvestmentLevel.NONE:
                investment_actions[asset_id] = level
            else:
                investment_actions[asset_id] = None
        else:
            if action_val:
                investment_actions[asset_id] = InvestmentLevel.STANDARD
            else:
                investment_actions[asset_id] = None

    # Extract BD bid (take max bid across slots, or 0 if no bids)
    bd_array = action_dict["bd_bids"]
    bd_bid = int(np.max(bd_array)) if len(bd_array) > 0 else 0

    return investment_actions, bd_bid


def _get_random_actions(
    agent_name: str,
    multi_game: MultiAgentGame,
) -> tuple[dict[uuid.UUID, InvestmentLevel | None], int]:
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
    # Random BD bid (0-2)
    bd_bid = random.randint(0, 2)
    return investment_actions, bd_bid




def _get_knapsack_actions(
    agent_type: str,
    agent_name: str,
    multi_game: MultiAgentGame,
) -> tuple[dict[uuid.UUID, InvestmentLevel | None], int]:
    """Get actions from the knapsack heuristic agent."""
    game_state = multi_game.agent_states[agent_name]

    if agent_type not in OPPONENT_AGENT_FACTORIES:
        logger.warning(f"Unknown agent type '{agent_type}', using knapsack_cap12")
        agent_type = "knapsack_cap12"

    agent = OPPONENT_AGENT_FACTORIES[agent_type]()
    decisions = get_agent_investment_decisions(agent, game_state)

    # Convert "invest" string decisions to InvestmentLevel
    investment_actions: dict[uuid.UUID, InvestmentLevel | None] = {}
    for asset_id, decision in decisions.items():
        if decision == "invest":
            investment_actions[asset_id] = InvestmentLevel.STANDARD
        else:
            investment_actions[asset_id] = None

    # Enforce capacity cap: limit total concurrent investments
    current_in_dev = sum(
        1
        for a in game_state.assets.values()
        if a.state == AssetState.InDevelopment
    )
    remaining_cap = max(0, _KNAPSACK_CAPACITY - current_in_dev)
    new_investments = [
        aid
        for aid, level in investment_actions.items()
        if level is not None
    ]
    if len(new_investments) > remaining_cap:
        # Keep only the top investments by eNPV
        scored = [
            (game_state.assets[aid].enpv, aid)
            for aid in new_investments
            if aid in game_state.assets
        ]
        scored.sort(reverse=True)
        drop = {aid for _, aid in scored[remaining_cap:]}
        for aid in drop:
            investment_actions[aid] = None

    # No BD bidding for knapsack in the app
    return investment_actions, 0
