"""Tests for agent utility functions."""

import uuid

from pyxis_portfolio_challenge.agents import get_agent
from pyxis_portfolio_challenge.agents.utils import (
    get_agent_investment_decisions,
    get_all_agents_investment_decisions,
)
from pyxis_portfolio_challenge.config import (
    ApprovalPhaseConfig,
    ClinicalSitesConfig,
    DropActionConfig,
    MarketingConfig,
    PtrsReadingsConfig,
    config,
)

# Disabled feature configs now required as keyword-only args by
# GameState.initialise_new_game.
_EXTRA_DISABLED_CONFIGS = dict(
    drop_action_config=DropActionConfig(
        enabled=False, drop_price_fraction=0.0, drop_price_rounding=1_000_000,
    ),
    marketing_config=MarketingConfig(
        enabled=False, dc_cost_fraction=0.035, dc_step_boost=0.10, dc_decay_rate=0.206,
        be_cost_fraction=0.0175, be_boost=0.25, be_decay_rate=0.206, be_effectiveness=3.5,
    ),
    clinical_sites_config=ClinicalSitesConfig(
        enabled=False, starting_sites=4, purchase_base_cost=500_000_000,
        purchase_cost_rounding=1_000_000, site_development_steps=2, agent_priority=False,
        priority_entropy_weight=1.0, auction_enabled=True, auction_interval_steps=20,
        auction_min_step=10, site_max_bid=100_000,
        auction_reserve_fraction=0.0,
    ),
    ptrs_readings_config=PtrsReadingsConfig(
        enabled=False, cost_fraction=0.05, cost_rounding=1_000_000,
        action_space_max_readings=10, sigma_logit_base=1.5, sigma_ep=1.5,
        noise_multipliers=[1.0, 1.5, 2.0], max_sample_obs=20,
    ),
    approval_phase_config=ApprovalPhaseConfig(
        enabled=False, duration_min=1, duration_max=3,
        success_rate_min=0.85, success_rate_max=0.95, cost=50_000_000,
    ),
)


def test_get_agent_investment_decisions_handles_enabled_multi_agent_features(
    json_game_state_factory,
):
    """Regression: competition game_states carry the multi-agent-only features
    (marketing, clinical sites, PTRS readings, approval phase) enabled. The
    single-agent reasoning env used here rejects those when enabled, so the helper
    must force them disabled internally rather than raise ValueError.
    """
    game_state = json_game_state_factory()
    # Mimic a competition game_state that carries these features enabled.
    game_state._marketing_config = config.marketing
    game_state._clinical_sites_config = config.clinical_sites
    game_state._ptrs_readings_config = config.ptrs_readings
    game_state._asset_generator.approval_phase_config = config.approval_phase
    assert game_state._marketing_config.enabled
    assert game_state._clinical_sites_config.enabled
    assert game_state._ptrs_readings_config.enabled
    assert game_state._asset_generator.approval_phase_config.enabled

    agent = get_agent("Knapsack")

    # Previously raised ValueError from InvestmentGameEnv's multi-only guard.
    decisions = get_agent_investment_decisions(agent=agent, game_state=game_state)

    assert isinstance(decisions, dict)
    for asset_id, decision in decisions.items():
        assert isinstance(asset_id, uuid.UUID)
        assert asset_id in game_state.assets
        assert decision in ["invest", None]


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

    from pyxis_portfolio_challenge.rng import init_game_rng
    # Create a game state with all assets in non-idle state
    init_game_rng(42)
    game_state = GameState.initialise_new_game(
        asset_generator_cls=JSONAssetGenerator,
        num_assets=3,
        max_num_assets=25,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        cash=10_000_000,
        horizon=20,
        seed=42,
        assets_dir=valid_json_assets_path,
        indication_spread=1.5,
        indication_drift_speed=1.0,
        trial_cost_multiplier=1.0,
        **_EXTRA_DISABLED_CONFIGS,
    )

    # Put every idle asset in development so none are investable. Assets that
    # already arrived on-market (or in any non-idle state) cannot be developed
    # and are not investable anyway, so leave them as-is.
    from pyxis_portfolio_challenge.game.asset import AssetState
    for asset_id in list(game_state.assets.keys()):
        asset = game_state.assets[asset_id]
        if asset.state == AssetState.Idle:
            game_state.assets[asset_id] = asset.to_develop()

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
