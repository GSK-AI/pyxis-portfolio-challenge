"""Tests for agent utility functions."""

import uuid

from pyxis_portfolio_challenge.agents import get_agent
from pyxis_portfolio_challenge.agents.utils import (
    get_agent_investment_decisions,
    get_all_agents_investment_decisions,
)
from pyxis_portfolio_challenge.config import CapacityConfig


def test_get_agent_investment_decisions_knapsack(
    json_game_state_factory, valid_json_assets_path
):
    """Test getting investment decisions from KnapsackAgent."""
    game_state = json_game_state_factory()

    # Create a Knapsack agent
    agent = get_agent("Knapsack")

    # Get investment decisions
    decisions = get_agent_investment_decisions(
        agent=agent,
        game_state=game_state,
    )

    # Verify return type
    assert isinstance(decisions, dict)

    # All keys should be UUIDs from the game state
    for asset_id in decisions.keys():
        assert isinstance(asset_id, uuid.UUID)
        assert asset_id in game_state.assets

    # All values should be "invest" or None
    for decision in decisions.values():
        assert decision in ["invest", None]


def test_get_agent_investment_decisions_only_idle_assets(
    json_game_state_factory, valid_json_assets_path
):
    """Test that only idle assets are recommended for investment."""
    game_state = json_game_state_factory()

    # Set some assets to non-idle states
    asset_ids = list(game_state.assets.keys())
    if len(asset_ids) >= 2:
        # Put first asset in development
        game_state.assets[asset_ids[0]] = game_state.assets[
            asset_ids[0]
        ].to_develop()

    agent = get_agent("Knapsack")

    decisions = get_agent_investment_decisions(
        agent=agent,
        game_state=game_state,
    )

    # Verify in-development assets are not in decisions
    if len(asset_ids) >= 2:
        assert asset_ids[0] not in decisions


def test_get_agent_investment_decisions_respects_cash_constraint(
    json_game_state_factory, valid_json_assets_path
):
    """Test that agent respects cash constraints."""
    game_state = json_game_state_factory()

    # Set very low cash
    game_state.cash = 100.0

    agent = get_agent("Knapsack")

    decisions = get_agent_investment_decisions(
        agent=agent,
        game_state=game_state,
    )

    # Should have no or very few investments due to low cash
    assert isinstance(decisions, dict)
    # Most likely no investments with such low cash
    assert len(decisions) <= 1


def test_get_all_agents_investment_decisions(
    json_game_state_factory, valid_json_assets_path
):
    """Test getting investment decisions from multiple agents."""
    game_state = json_game_state_factory()

    # Create agents
    agents = {
        "Knapsack": get_agent("Knapsack"),
    }

    # Get all decisions
    all_decisions = get_all_agents_investment_decisions(
        agents=agents,
        game_state=game_state,
    )

    # Verify structure
    assert isinstance(all_decisions, dict)
    assert "Knapsack" in all_decisions

    # Each agent should have a decisions dict
    for agent_name, decisions in all_decisions.items():
        assert isinstance(decisions, dict)
        # All keys should be UUIDs
        for asset_id in decisions.keys():
            assert isinstance(asset_id, uuid.UUID)


def test_get_agent_investment_decisions_empty_game_state(valid_json_assets_path):
    """Test with a game state that has no investable assets."""
    from pyxis_portfolio_challenge.game.asset_generators import JSONAssetGenerator
    from pyxis_portfolio_challenge.game.game_state import GameState

    # Create a game state with all assets in non-idle state
    game_state = GameState.initialise_new_game(
        asset_generator_cls=JSONAssetGenerator,
        num_assets=3,
        max_num_assets=25,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        cash=10_000_000,
        horizon=20,
        global_seed=42,
        assets_dir=valid_json_assets_path,
        indication_spread=1.5,
        indication_drift_speed=1.0,
        trial_cost_multiplier=1.0,
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
    )

    # Put all assets in development
    for asset_id in list(game_state.assets.keys()):
        game_state.assets[asset_id] = game_state.assets[asset_id].to_develop()

    agent = get_agent("Knapsack")

    decisions = get_agent_investment_decisions(
        agent=agent,
        game_state=game_state,
    )

    # Should have no investments since all assets are in development
    assert len(decisions) == 0


def test_get_agent_investment_decisions_deterministic(
    json_game_state_factory, valid_json_assets_path
):
    """Test that decisions are deterministic for the same game state."""
    game_state = json_game_state_factory()

    agent = get_agent("Knapsack")

    # Get decisions twice
    decisions1 = get_agent_investment_decisions(
        agent=agent,
        game_state=game_state,
    )

    decisions2 = get_agent_investment_decisions(
        agent=agent,
        game_state=game_state,
    )

    # Should be identical
    assert decisions1 == decisions2


def test_get_agent_investment_decisions_environment_cleanup(
    json_game_state_factory, valid_json_assets_path
):
    """Test that the function doesn't leak environments."""
    game_state = json_game_state_factory()

    agent = get_agent("Knapsack")

    # Run multiple times to check for leaks
    for _ in range(5):
        decisions = get_agent_investment_decisions(
            agent=agent,
            game_state=game_state,
        )
        assert isinstance(decisions, dict)
