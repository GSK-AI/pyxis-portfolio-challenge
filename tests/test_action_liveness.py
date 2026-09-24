"""
Smoke tests proving every action head actually affects the game.

Built end-to-end via :func:`make_multi_agent_train_env` so they cover the
``MultiAgentGame.initialise`` wiring seam (where marketing once shipped inert).
Two signals: trajectory divergence for every head, plus a stricter first-step
cash delta for spend heads (a dead ``brand_equity`` still perturbs the RNG via
its intel leak, so divergence alone would give it a false pass).
"""

import numpy as np
import pytest

from pyxis_portfolio_challenge.agents.multi_agent_knapsack import (
    MultiAgentKnapsackAgent,
)
from pyxis_portfolio_challenge.environment.env_factory import (
    make_multi_agent_train_env,
)

AGENT = "pharma_0"
OPPONENT = "pharma_1"
SEED = 7
MAX_STEPS = 60  # long enough for auction cadence / on-market preconditions


def _unwrap(env):
    """Return the underlying MultiAgentInvestmentGameEnv behind any wrappers."""
    base = env
    while hasattr(base, "env") and not hasattr(base, "multi_agent_game"):
        base = base.env
    return base


def _make_env():
    env = make_multi_agent_train_env(flatten_obs=True)
    return env, _unwrap(env)


def _present_heads(base):
    """Action heads actually offered by the current config."""
    return list(base.action_space(AGENT).spaces.keys())


def _noop_action(base):
    """A do-nothing action for every currently-enabled head."""
    m = base.max_num_assets
    nbd = base.bd_max_slots
    nind = base.max_indications_per_ta * 3
    heads = _present_heads(base)
    action = {
        "investments": np.zeros(m, dtype=np.int64),
        "bd_bids": np.zeros(nbd, dtype=np.float32),
    }
    if "ptrs_research" in heads:
        action["ptrs_research"] = np.zeros(m + nbd, dtype=np.int64)
    if "upgrade" in heads:
        action["upgrade"] = 0
    if "site_bid" in heads:
        action["site_bid"] = np.array([0.0], dtype=np.float32)
    if "site_priority" in heads:
        action["site_priority"] = np.zeros(m, dtype=np.float32)
    if "pricing" in heads:
        default_level = base.pricing_config.default_level
        action["pricing"] = np.full(m, default_level, dtype=np.int64)
    if "demand_creation" in heads:
        action["demand_creation"] = np.zeros(nind, dtype=np.int64)
    if "brand_equity" in heads:
        action["brand_equity"] = np.zeros(m, dtype=np.int64)
    return action


def _active_value(base, env, head):
    """A mask-valid "do something" value for ``head``."""
    m = base.max_num_assets
    nbd = base.bd_max_slots
    nind = base.max_indications_per_ta * 3
    masks = env.action_masks(AGENT)
    if head == "bd_bids":
        return np.full(nbd, base.bd_max_bid * 0.3, dtype=np.float32)
    if head == "ptrs_research":
        # Max valid reading count per slot (respects the action mask).
        return np.array(
            [max((n for n, ok in enumerate(slot) if ok), default=0) for slot in masks["ptrs_research"]],
            dtype=np.int64,
        )
    if head == "upgrade":
        return 1 if masks["upgrade"][1] else 0
    if head == "site_bid":
        return np.array([base.clinical_sites_config.site_max_bid * 0.1], dtype=np.float32)
    if head == "pricing":
        default_level = base.pricing_config.default_level
        alt = 0 if default_level != 0 else len(base.pricing_config.levels) - 1
        return np.full(m, alt, dtype=np.int64)
    if head == "demand_creation":
        return np.ones(nind, dtype=np.int64)
    if head == "brand_equity":
        return np.ones(m, dtype=np.int64)
    raise ValueError(f"no active value defined for head {head!r}")


def _state_signature(base):
    gs = base.multi_agent_game.agent_states[AGENT]
    sm = base.multi_agent_game.shared_market
    demand = sum(mkt.demand_multiplier for mkt in sm.indication_markets.values())
    brand = sum(gs._brand_scores.values()) if gs._brand_scores else 0.0
    return (
        round(gs.cash, 3),
        gs.operational_sites,
        tuple(gs.sites_in_development),
        len(gs.assets),
        len(gs.dropped_assets),
        round(sum(a.enpv for a in gs.assets.values()), 3),
        round(demand, 6),
        round(brand, 6),
    )


def _rollout_signatures(head, mode):
    """
    Run an episode where pharma_0 exercises ``head`` at ``mode`` each step.

    ``investments`` are driven by the knapsack policy (so market-dependent heads
    have on-market assets to act on); every other non-target head is held at its
    do-nothing value so the trajectory difference is attributable to ``head``.
    """
    env, base = _make_env()
    env.reset(seed=SEED)
    knapsack = MultiAgentKnapsackAgent(AGENT, env=base)
    signatures = []
    for _ in range(MAX_STEPS):
        action = _noop_action(base)
        if head == "investments":
            if mode == "active":
                action["investments"] = knapsack(None)["investments"]
        else:
            # Invest via knapsack to create preconditions, then vary the head.
            action["investments"] = knapsack(None)["investments"]
            if mode == "active":
                action[head] = _active_value(base, env, head)
        env.step({AGENT: action, OPPONENT: _noop_action(base)})
        if AGENT not in base.multi_agent_game.agent_states:
            break
        signatures.append(_state_signature(base))
    return signatures


def _heads_under_test():
    _, base = _make_env()
    return _present_heads(base)


@pytest.mark.parametrize("head", _heads_under_test())
def test_action_head_changes_game_state(head):
    """Exercising a head must change the game vs its do-nothing value."""
    neutral = _rollout_signatures(head, "neutral")
    active = _rollout_signatures(head, "active")
    if neutral == active:
        pytest.fail(
            f"Action head {head!r} is a NO-OP: exercising it produced an "
            f"identical trajectory to its do-nothing value over {MAX_STEPS} "
            f"steps. The head is inert in the constructed environment."
        )


@pytest.mark.parametrize("head", ["demand_creation", "brand_equity"])
def test_marketing_spend_costs_the_spender_cash(head):
    """
    Marketing spend must deduct cash on the first step (economic effect).

    This is the exact regression that shipped inert: the heads existed and could
    be "spent" but ``marketing_config`` never reached the per-agent GameState, so
    no cost was charged. First-step cash isolates the deterministic spend cost
    from downstream stochastic drift.
    """
    env, base = _make_env()
    if head not in _present_heads(base):
        pytest.skip(f"{head} not enabled in current config")

    def first_step_cash(active):
        e, b = _make_env()
        e.reset(seed=SEED)
        action = _noop_action(b)  # do-nothing investments -> no trial-cost noise
        if active:
            action[head] = _active_value(b, e, head)
        e.step({AGENT: action, OPPONENT: _noop_action(b)})
        return b.multi_agent_game.agent_states[AGENT].cash

    cash_noop = first_step_cash(active=False)
    cash_spend = first_step_cash(active=True)
    assert cash_spend < cash_noop, (
        f"Spending on {head!r} did not cost the spender any cash "
        f"(noop={cash_noop:.1f}, spend={cash_spend:.1f}). The head is "
        f"economically inert -- marketing_config is likely not wired into the "
        f"per-agent GameState."
    )
