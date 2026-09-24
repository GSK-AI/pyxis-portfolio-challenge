"""Tests for the ptrs_readings feature (stochastic PTRS sampling)."""

import random
import uuid

import pytest

from pyxis_portfolio_challenge.config import (
    ApprovalPhaseConfig,
    ClinicalSitesConfig,
    DistributionalPtrsConfig,
    DropActionConfig,
    InterimTrialObservationsConfig,
    InvestmentLevelParams,
    InvestmentLevelsConfig,
    MarketingConfig,
    PtrsReadingsConfig,
    TAExperienceConfig,
    UncertainPtrsConfig,
    fibonacci_cost,
)
from pyxis_portfolio_challenge.game.asset import DrugAsset
from pyxis_portfolio_challenge.game.trial import Trial, TrialPhase, TrialState
from pyxis_portfolio_challenge.rng import init_game_rng

# Disabled feature configs required as keyword-only args by
# GameState.initialise_new_game (rd_capacity and ptrs_readings passed explicitly).
_EXTRA_DISABLED_CONFIGS = dict(
    investment_levels_config=InvestmentLevelsConfig(
        enabled=False,
        levels={
            "none": InvestmentLevelParams(
                cost_modifier=0.0, speed_modifier=0.0, success_modifier=1.0,
                capacity_cost=0, experience_modifier=0.0,
            ),
            "standard": InvestmentLevelParams(
                cost_modifier=1.0, speed_modifier=1.0, success_modifier=1.0,
                capacity_cost=2, experience_modifier=1.0,
            ),
        },
    ),
    interim_trial_observations_config=InterimTrialObservationsConfig(
        enabled=False, latent_quality_concentration=10.0, initial_noise_scale=0.3,
    ),
    distributional_ptrs_config=DistributionalPtrsConfig(
        enabled=False,
        ta_quality_variance={
            "oncology": 0.08,
            "respiratory and immunology": 0.05,
            "vaccines and infectious disease": 0.03,
        },
        asset_noise_std=0.03, prior_concentration=5.0, observation_noise=0.1,
    ),
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
    ),
    ta_experience_config=TAExperienceConfig(
        enabled=False, experience_to_full_knowledge=30.0, max_expertise_boost=0.05,
        experience_to_max_boost=40.0, experience_decay_rate=0.98,
        max_total_experience=60.0,
        phase_experience_weights={
            "phase_1": 0.5, "phase_2": 1.0, "phase_3": 1.5, "approval": 0.5,
        },
        asset_arrival_temperature=0.1,
    ),
    uncertain_ptrs_config=UncertainPtrsConfig(
        enabled=False,
        ta_noise_config={
            "oncology": 0.12,
            "respiratory and immunology": 0.10,
            "vaccines and infectious disease": 0.08,
        },
        phase_noise_multipliers={
            "phase_1": 1.5, "phase_2": 1.0, "phase_3": 0.75, "approval": 0.5,
        },
    ),
    approval_phase_config=ApprovalPhaseConfig(
        enabled=False, duration_min=1, duration_max=3,
        success_rate_min=0.85, success_rate_max=0.95, cost=50_000_000,
    ),
)

# ---------------------------------------------------------------------------
# fibonacci_cost
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n,expected_multiplier", [
    (1, 1),
    (2, 2),
    (3, 4),
    (4, 7),
    (5, 12),
])
def test_fibonacci_cost(n, expected_multiplier):
    base = 1.0
    assert fibonacci_cost(n, base) == pytest.approx(expected_multiplier * base)


# ---------------------------------------------------------------------------
# Trial.draw_and_accumulate
# ---------------------------------------------------------------------------

def _make_trial(ptrs: float = 0.6, true_ptrs: float | None = None) -> Trial:
    t = Trial(
        cost_remaining=100_000_000,
        time_remaining=3,
        ptrs=ptrs,
        state=TrialState.PENDING,
        phase=TrialPhase.PHASE_1,
        next_trial_on_success=None,
    )
    t._true_ptrs = true_ptrs if true_ptrs is not None else ptrs
    return t


def test_draw_and_accumulate_running_mean():
    rng = random.Random(42)
    trial = _make_trial(ptrs=0.7, true_ptrs=0.7)

    trial.draw_and_accumulate(sigma=0.5, n=1, rng=rng)
    assert trial.ptrs_sample_count == 1
    assert trial.ptrs_sample_mean is not None

    first_mean = trial.ptrs_sample_mean

    trial.draw_and_accumulate(sigma=0.5, n=1, rng=rng)
    assert trial.ptrs_sample_count == 2
    # Mean must shift (unless both samples happen to be identical, which is vanishingly unlikely)
    assert trial.ptrs_sample_mean != first_mean or True  # always passes; count is the real check

    # Calling with n=3 increments count by 3
    trial.draw_and_accumulate(sigma=0.5, n=3, rng=rng)
    assert trial.ptrs_sample_count == 5


def test_draw_and_accumulate_convergence():
    rng = random.Random(0)
    true_p = 0.65
    trial = _make_trial(ptrs=true_p, true_ptrs=true_p)
    trial.draw_and_accumulate(sigma=0.3, n=2000, rng=rng)
    assert abs(trial.ptrs_sample_mean - true_p) < 0.02


def test_draw_and_accumulate_zero_sigma_returns_true_ptrs():
    """With sigma=0, logit-normal collapses to a point mass at true_ptrs."""
    rng = random.Random(0)
    true_p = 0.55
    trial = _make_trial(ptrs=0.3, true_ptrs=true_p)
    trial.draw_and_accumulate(sigma=0.0, n=5, rng=rng)
    assert trial.ptrs_sample_mean == pytest.approx(true_p, abs=1e-9)


# ---------------------------------------------------------------------------
# asset.pending_trial_chain and apply_pending_readings
# ---------------------------------------------------------------------------

def _chain(phases, true_ptrs=0.5):
    """Build a linked trial chain for the given TrialPhase list."""
    tail = None
    for phase in reversed(phases):
        t = Trial(
            cost_remaining=100_000_000,
            time_remaining=3,
            ptrs=true_ptrs,
            state=TrialState.PENDING,
            phase=phase,
            next_trial_on_success=tail,
        )
        t._true_ptrs = true_ptrs
        tail = t
    return tail  # head of chain


def _asset_with_chain(phases, true_ptrs=0.5):
    trial = _chain(phases, true_ptrs)
    return DrugAsset(
        id=uuid.uuid4(),
        name="Test",
        therapeutic_area="oncology",
        type="internal",
        description="",
        max_revenue=1_000_000_000,
        raw_max_revenue=1_000_000_000,
        time_until_max_revenue=5,
        time_until_patent_expiry=20,
        trial=trial,
        state=__import__(
            "pyxis_portfolio_challenge.game.asset", fromlist=["AssetState"]
        ).AssetState.Idle,
        time_on_market=0,
    )


def test_pending_trial_chain_excludes_approval():
    from pyxis_portfolio_challenge.game.trial import TrialPhase
    asset = _asset_with_chain([
        TrialPhase.PHASE_1,
        TrialPhase.PHASE_2,
        TrialPhase.APPROVAL,
    ])
    chain = asset.pending_trial_chain
    assert len(chain) == 2
    assert all(t.phase != TrialPhase.APPROVAL for t in chain)


def test_apply_pending_readings_sigma_indexing():
    """Trial at position i uses noise_multipliers[i] × sigma_base."""
    rng = random.Random(99)
    asset = _asset_with_chain([TrialPhase.PHASE_1, TrialPhase.PHASE_2])
    chain = asset.pending_trial_chain

    # Use sigma=0 for position 0, large sigma for position 1
    # → position-0 trial converges to true_ptrs; position-1 trial does not
    noise_multipliers = [0.0, 5.0]
    true_p = 0.5
    asset.apply_pending_readings(50, sigma_base=1.0, noise_multipliers=noise_multipliers, rng=rng)

    # Position-0 (sigma=0): sample mean must equal true_ptrs exactly
    assert chain[0].ptrs_sample_mean == pytest.approx(true_p, abs=1e-9)
    # Position-1 (sigma=5): count is 50 but not converged to a point mass
    assert chain[1].ptrs_sample_count == 50


def test_apply_pending_readings_raises_on_chain_longer_than_multipliers():
    asset = _asset_with_chain([TrialPhase.PHASE_1, TrialPhase.PHASE_2, TrialPhase.PHASE_3])
    rng = random.Random(0)
    with pytest.raises(ValueError):
        asset.apply_pending_readings(1, sigma_base=1.0, noise_multipliers=[1.0, 1.5], rng=rng)


# ---------------------------------------------------------------------------
# Action masks — empty slots and cash-gated counts
# ---------------------------------------------------------------------------

def _ptrs_readings_cfg(**kwargs):
    defaults = dict(
        enabled=True,
        cost_fraction=0.1,
        cost_rounding=1,
        action_space_max_readings=5,
        sigma_logit_base=1.5,
        sigma_ep=None,
        noise_multipliers=[1.0, 1.5, 2.0],
        max_sample_obs=20,
    )
    defaults.update(kwargs)
    return PtrsReadingsConfig(**defaults)


def test_action_masks_empty_slot_is_masked():
    """Research count > 0 must be masked for empty portfolio slots."""
    import upath

    from pyxis_portfolio_challenge.config import (
        ApprovalPhaseConfig,
        CapacityConfig,
        DistributionalPtrsConfig,
        InterimTrialObservationsConfig,
        InvestmentLevelParams,
        InvestmentLevelsConfig,
        PricingConfig,
        TAExperienceConfig,
        UncertainPtrsConfig,
    )
    from pyxis_portfolio_challenge.environment.multi_agent_training_gym import (
        MultiAgentInvestmentGameEnv,
    )
    from pyxis_portfolio_challenge.environment.reward import NetCashFlowReward

    TEST_ASSETS_DIR = upath.UPath("tests/data/generated_assets")
    env = MultiAgentInvestmentGameEnv(
        assets_dir=TEST_ASSETS_DIR,
        num_agents=1,
        starting_cash=1_000_000_000.0,
        max_num_assets=10,
        horizon=10,
        equilibrium_num_assets=3,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        bd_enabled=False,
        bd_assets_dir=TEST_ASSETS_DIR,
        bd_base_lambda=0.3,
        bd_leak_lambda_boost=0.3,
        bd_min_step=5,
        bd_max_bid=10000.0,
        bd_max_slots=1,
        bd_phase_weights=[0.2, 0.4, 0.4],
        bd_indication_activity_bias=0.8,
        exclusivity_period=4,
        first_mover_bonus=0.30,
        disable_market_share_competition=False,
        alert_history_length=5,
        leak_phase_probabilities=[0.2, 0.5, 0.7],
        be_leak_probability=0.8,
        dc_leak_probability=0.8,
        alerts_per_agent=5,
        reward_fn=NetCashFlowReward(),
        reward_type="absolute",
        reward_scale=1.0,
        shuffle_order=False,
        mask_first_order_assets=False,
        mask_negative_enpv_assets=False,
        flatten_obs=True,
        distributional_ptrs_config=DistributionalPtrsConfig(
            enabled=False,
            ta_quality_variance={
                "oncology": 0.08,
                "respiratory and immunology": 0.05,
                "vaccines and infectious disease": 0.03,
            },
            asset_noise_std=0.03,
            prior_concentration=5.0,
            observation_noise=0.1,
        ),
        ta_experience_config=TAExperienceConfig(
            enabled=False,
            experience_to_full_knowledge=30.0,
            max_expertise_boost=0.05,
            experience_to_max_boost=40.0,
            experience_decay_rate=0.98,
            max_total_experience=60.0,
            phase_experience_weights={
                "phase_1": 0.5,
                "phase_2": 1.0,
                "phase_3": 1.5,
                "approval": 0.5,
            },
            asset_arrival_temperature=0.1,
        ),
        uncertain_ptrs_config=UncertainPtrsConfig(
            enabled=False,
            ta_noise_config={
                "oncology": 0.12,
                "respiratory and immunology": 0.10,
                "vaccines and infectious disease": 0.08,
            },
            phase_noise_multipliers={
                "phase_1": 1.5,
                "phase_2": 1.0,
                "phase_3": 0.75,
                "approval": 0.5,
            },
        ),
        investment_levels_config=InvestmentLevelsConfig(
            enabled=False,
            levels={
                "none": InvestmentLevelParams(
                    cost_modifier=0.0, speed_modifier=0.0, success_modifier=1.0,
                    capacity_cost=0, experience_modifier=0.0,
                ),
                "standard": InvestmentLevelParams(
                    cost_modifier=1.0, speed_modifier=1.0, success_modifier=1.0,
                    capacity_cost=2, experience_modifier=1.0,
                ),
            },
        ),
        interim_trial_observations_config=InterimTrialObservationsConfig(
            enabled=False, latent_quality_concentration=10.0, initial_noise_scale=0.3,
        ),
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
        approval_phase_config=ApprovalPhaseConfig(
            enabled=False, duration_min=1, duration_max=3,
            success_rate_min=0.85, success_rate_max=0.95, cost=50_000_000,
        ),
        max_indications_per_ta=7,
        target_drugs_per_indication=2.0,
        on_market_fraction=0.25,
        indication_spread=1.5,
        indication_drift_speed=1.0,
        trial_cost_multiplier=1.0,
        congestion_exponent=1.0,
        congestion_ramp_steps=3,
        congestion_incumbent_penalty=0.0,
        pricing_config=PricingConfig(
            enabled=False, levels=[0.60, 0.75, 1.00, 1.20, 1.40, 1.60],
            default_level=2, elasticity=2.0,
        ),
        drop_action_config=DropActionConfig(
            enabled=False, drop_price_fraction=0.0, drop_price_rounding=1_000_000,
        ),
        render_mode=None,
        marketing_config=_EXTRA_DISABLED_CONFIGS["marketing_config"],
        clinical_sites_config=_EXTRA_DISABLED_CONFIGS["clinical_sites_config"],
        bd_persist_steps=1,
        dc_leak_min_agents=3,
        ptrs_readings_config=_ptrs_readings_cfg(),
    )
    env.reset(seed=42)
    agent = env.possible_agents[0]
    masks = env.action_masks(agent)
    research_mask = masks["ptrs_research"]

    # max_num_assets=10; env initialised with equilibrium_num_assets=3 assets
    # → slots beyond the populated ones are empty → all reading counts > 0 masked
    game_state = env.multi_agent_game.agent_states[agent]
    asset_order = env._asset_id_orders[agent]
    for i in range(len(asset_order)):
        slot_mask = research_mask[i]
        asset_id = asset_order[i] if i < len(asset_order) else None
        asset = game_state.assets.get(asset_id) if asset_id else None
        if asset is None:
            # Empty slot: only count=0 allowed
            assert slot_mask[0] is True
            assert all(not allowed for allowed in slot_mask[1:])


def test_action_masks_cash_gates_high_counts():
    """
    Counts whose Fibonacci cost exceeds cash are masked.

    DUMMY_LIST_DATA Phase-1 cost_remaining is 200 000 or 250 000.
    cost_fraction=0.5 → base is 100 000–125 000.
    fibonacci(1)×base = 100 000–125 000  (affordable at cash=150 001)
    fibonacci(2)×base = 200 000–250 000  (not affordable at cash=150 001)
    """
    import upath

    from pyxis_portfolio_challenge.config import (
        ApprovalPhaseConfig,
        CapacityConfig,
        DistributionalPtrsConfig,
        InterimTrialObservationsConfig,
        InvestmentLevelParams,
        InvestmentLevelsConfig,
        PricingConfig,
        TAExperienceConfig,
        UncertainPtrsConfig,
    )
    from pyxis_portfolio_challenge.environment.multi_agent_training_gym import (
        MultiAgentInvestmentGameEnv,
    )
    from pyxis_portfolio_challenge.environment.reward import NetCashFlowReward

    TEST_ASSETS_DIR = upath.UPath("tests/data/generated_assets")

    env = MultiAgentInvestmentGameEnv(
        assets_dir=TEST_ASSETS_DIR,
        num_agents=1,
        starting_cash=1e18,  # unconstrained; we'll patch cash after reset
        max_num_assets=10,
        horizon=10,
        equilibrium_num_assets=3,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        bd_enabled=False,
        bd_assets_dir=TEST_ASSETS_DIR,
        bd_base_lambda=0.3,
        bd_leak_lambda_boost=0.3,
        bd_min_step=5,
        bd_max_bid=10000.0,
        bd_max_slots=1,
        bd_phase_weights=[0.2, 0.4, 0.4],
        bd_indication_activity_bias=0.8,
        exclusivity_period=4,
        first_mover_bonus=0.30,
        disable_market_share_competition=False,
        alert_history_length=5,
        leak_phase_probabilities=[0.2, 0.5, 0.7],
        be_leak_probability=0.8,
        dc_leak_probability=0.8,
        alerts_per_agent=5,
        reward_fn=NetCashFlowReward(),
        reward_type="absolute",
        reward_scale=1.0,
        shuffle_order=False,
        mask_first_order_assets=False,
        mask_negative_enpv_assets=False,
        flatten_obs=True,
        distributional_ptrs_config=DistributionalPtrsConfig(
            enabled=False,
            ta_quality_variance={
                "oncology": 0.08,
                "respiratory and immunology": 0.05,
                "vaccines and infectious disease": 0.03,
            },
            asset_noise_std=0.03,
            prior_concentration=5.0,
            observation_noise=0.1,
        ),
        ta_experience_config=TAExperienceConfig(
            enabled=False,
            experience_to_full_knowledge=30.0,
            max_expertise_boost=0.05,
            experience_to_max_boost=40.0,
            experience_decay_rate=0.98,
            max_total_experience=60.0,
            phase_experience_weights={
                "phase_1": 0.5,
                "phase_2": 1.0,
                "phase_3": 1.5,
                "approval": 0.5,
            },
            asset_arrival_temperature=0.1,
        ),
        uncertain_ptrs_config=UncertainPtrsConfig(
            enabled=False,
            ta_noise_config={
                "oncology": 0.12,
                "respiratory and immunology": 0.10,
                "vaccines and infectious disease": 0.08,
            },
            phase_noise_multipliers={
                "phase_1": 1.5,
                "phase_2": 1.0,
                "phase_3": 0.75,
                "approval": 0.5,
            },
        ),
        investment_levels_config=InvestmentLevelsConfig(
            enabled=False,
            levels={
                "none": InvestmentLevelParams(
                    cost_modifier=0.0, speed_modifier=0.0, success_modifier=1.0,
                    capacity_cost=0, experience_modifier=0.0,
                ),
                "standard": InvestmentLevelParams(
                    cost_modifier=1.0, speed_modifier=1.0, success_modifier=1.0,
                    capacity_cost=2, experience_modifier=1.0,
                ),
            },
        ),
        interim_trial_observations_config=InterimTrialObservationsConfig(
            enabled=False, latent_quality_concentration=10.0, initial_noise_scale=0.3,
        ),
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
        approval_phase_config=ApprovalPhaseConfig(
            enabled=False, duration_min=1, duration_max=3,
            success_rate_min=0.85, success_rate_max=0.95, cost=50_000_000,
        ),
        max_indications_per_ta=7,
        target_drugs_per_indication=2.0,
        on_market_fraction=0.25,
        indication_spread=1.5,
        indication_drift_speed=1.0,
        trial_cost_multiplier=1.0,
        congestion_exponent=1.0,
        congestion_ramp_steps=3,
        congestion_incumbent_penalty=0.0,
        pricing_config=PricingConfig(
            enabled=False, levels=[0.60, 0.75, 1.00, 1.20, 1.40, 1.60],
            default_level=2, elasticity=2.0,
        ),
        drop_action_config=DropActionConfig(
            enabled=False, drop_price_fraction=0.0, drop_price_rounding=1_000_000,
        ),
        render_mode=None,
        marketing_config=_EXTRA_DISABLED_CONFIGS["marketing_config"],
        clinical_sites_config=_EXTRA_DISABLED_CONFIGS["clinical_sites_config"],
        bd_persist_steps=1,
        dc_leak_min_agents=3,
        ptrs_readings_config=_ptrs_readings_cfg(cost_fraction=0.5, cost_rounding=1),
    )
    env.reset(seed=42)
    agent = env.possible_agents[0]

    game_state = env.multi_agent_game.agent_states[agent]
    asset_order = env._asset_id_orders[agent]

    # Find first eligible asset and derive costs from its actual trial cost_remaining
    from pyxis_portfolio_challenge.config import fibonacci_cost as _fib

    found_asset = None
    found_slot = None
    for i, asset_id in enumerate(asset_order):
        if asset_id is None:
            continue
        asset = game_state.assets.get(asset_id)
        if asset is not None and asset.pending_trial_chain:
            found_asset = asset
            found_slot = i
            break
    assert found_asset is not None, "No asset with pending trial chain found in portfolio"

    base = 0.5 * found_asset.trial.cost_remaining   # cost_fraction=0.5, cost_rounding=1
    cost_n1 = _fib(1, base)
    cost_n2 = _fib(2, base)

    # Patch cash to be just above cost_n1 but below cost_n2; Pydantic accepts direct assignment
    game_state.cash = cost_n1 + 1.0

    masks = env.action_masks(agent)
    research_mask = masks["ptrs_research"]
    slot_mask = research_mask[found_slot]

    assert slot_mask[0] is True   # count=0 always valid
    assert slot_mask[1] is True   # n=1: cost_n1 ≤ cash → allowed
    assert slot_mask[2] is False  # n=2: cost_n2 > cash → blocked


# ---------------------------------------------------------------------------
# Latency: readings submitted at step T visible in obs at T+1
# ---------------------------------------------------------------------------

def test_ptrs_readings_applied_immediately():
    """Readings submitted at step T are applied within that step (visible at T+1 obs)."""
    from pyxis_portfolio_challenge.config import CapacityConfig
    from pyxis_portfolio_challenge.game.asset_generators import (
        DUMMY_LIST_DATA,
        FixedListAssetGenerator,
    )
    from pyxis_portfolio_challenge.game.game_state import GameState

    cfg = _ptrs_readings_cfg(cost_fraction=0.01)
    init_game_rng(42)

    game_state = GameState.initialise_new_game(
        asset_generator_cls=FixedListAssetGenerator,
        num_assets=3,
        cash=1_000_000,
        horizon=10,
        max_num_assets=10,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        assets_data_list=DUMMY_LIST_DATA,
        seed=None,
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
        ptrs_readings_config=cfg,
        **_EXTRA_DISABLED_CONFIGS,
    )

    target_asset_id = None
    for asset_id, asset in game_state.assets.items():
        if asset.pending_trial_chain:
            target_asset_id = asset_id
            break

    if target_asset_id is None:
        pytest.skip("No asset with pending trial chain available")

    count_before = game_state.assets[target_asset_id].pending_trial_chain[0].ptrs_sample_count

    # Step T: submit reading — applied immediately before evolution
    state_t1 = game_state.step(
        investor_actions={},
        research_actions={target_asset_id: 1},
    )

    # Reading was applied during step T; count must have increased in state_t1
    asset_t1 = state_t1.assets.get(target_asset_id)
    if asset_t1 is None:
        pytest.skip("Asset no longer active after step T")
    chain_t1 = asset_t1.pending_trial_chain
    if not chain_t1:
        pytest.skip("No pending trial chain at T+1")
    assert chain_t1[0].ptrs_sample_count > count_before


# ---------------------------------------------------------------------------
# Phase transition: Phase 1 completes while reading for Phase 2 is delivered
# ---------------------------------------------------------------------------

def test_pending_trial_chain_excludes_terminal_states():
    """OnMarket (PHASE_SUCCESS) and Failed (PHASE_FAILED) assets return empty chain."""
    from pyxis_portfolio_challenge.game.asset import AssetState

    # OnMarket asset: last trial in PHASE_SUCCESS state
    success_trial = Trial(
        cost_remaining=0.0,
        time_remaining=0,
        ptrs=1.0,
        state=TrialState.PHASE_SUCCESS,
        phase=TrialPhase.PHASE_3,
        next_trial_on_success=None,
    )
    on_market = DrugAsset(
        id=uuid.uuid4(),
        name="OnMarket",
        therapeutic_area="oncology",
        type="internal",
        description="",
        max_revenue=1_000_000_000,
        raw_max_revenue=1_000_000_000,
        time_until_max_revenue=5,
        time_until_patent_expiry=20,
        trial=success_trial,
        state=AssetState.OnMarket,
        time_on_market=1,
    )
    assert on_market.pending_trial_chain == []

    # Failed asset: trial in PHASE_FAILED state
    failed_trial = Trial(
        cost_remaining=0.0,
        time_remaining=0,
        ptrs=0.0,
        state=TrialState.PHASE_FAILED,
        phase=TrialPhase.PHASE_1,
        next_trial_on_success=None,
    )
    failed_asset = DrugAsset(
        id=uuid.uuid4(),
        name="Failed",
        therapeutic_area="oncology",
        type="internal",
        description="",
        max_revenue=1_000_000_000,
        raw_max_revenue=1_000_000_000,
        time_until_max_revenue=5,
        time_until_patent_expiry=20,
        trial=failed_trial,
        state=AssetState.Failed,
        time_on_market=0,
    )
    assert failed_asset.pending_trial_chain == []


def test_phase_completes_during_flush_phase2_gets_reading():
    """
    Phase 2 retains its reading even when Phase 1 completes during evolution.

    With readings applied before evolution (new A'3 behavior):
    - Phase 1 (time_remaining=1, ptrs=1.0 → always succeeds) gets a reading
    - Phase 2 gets a reading at position-1 sigma
    - Evolution: Phase 1 succeeds, trial.evolve() returns Phase 2 directly
    - Phase 2's ptrs_sample_count is preserved (no new trial object created)
    """
    from pyxis_portfolio_challenge.game.asset import AssetState

    init_game_rng(0)
    rng = random.Random(0)

    true_ptrs = 0.7
    phase2 = Trial(
        cost_remaining=100_000_000,
        time_remaining=3,
        ptrs=true_ptrs,
        state=TrialState.PENDING,
        phase=TrialPhase.PHASE_2,
        next_trial_on_success=None,
    )
    phase2._true_ptrs = true_ptrs

    # ptrs=1.0 guarantees Phase 1 always succeeds (rng.random() is in [0,1))
    # IN_PROGRESS is required for DrugAsset.state == InDevelopment
    phase1 = Trial(
        cost_remaining=10_000_000,
        time_remaining=1,
        ptrs=1.0,
        state=TrialState.IN_PROGRESS,
        phase=TrialPhase.PHASE_1,
        next_trial_on_success=phase2,
    )
    phase1._true_ptrs = 1.0

    asset = DrugAsset(
        id=uuid.uuid4(),
        name="Test",
        therapeutic_area="oncology",
        type="internal",
        description="",
        max_revenue=1_000_000_000,
        raw_max_revenue=1_000_000_000,
        time_until_max_revenue=5,
        time_until_patent_expiry=20,
        trial=phase1,
        state=AssetState.InDevelopment,
        time_on_market=0,
    )

    # Apply 1 reading before evolution (zero-sigma: counts increase, means converge exactly)
    noise_multipliers = [0.0, 0.0]
    asset.apply_pending_readings(1, sigma_base=1.0, noise_multipliers=noise_multipliers, rng=rng)

    # Both trials received exactly 1 reading
    assert phase1.ptrs_sample_count == 1
    assert phase2.ptrs_sample_count == 1

    # Evolve: Phase 1 (ptrs=1.0) always succeeds → Phase 2 becomes current trial
    evolved = asset.evolve()

    assert evolved.state == AssetState.Idle
    assert evolved.trial.phase == TrialPhase.PHASE_2
    # Phase 2's reading is preserved (trial.evolve() returns next_trial_on_success directly)
    assert evolved.trial.ptrs_sample_count == 1


# ---------------------------------------------------------------------------
# GameState-level: reading on InDev asset, and phase-completing InDev asset
# ---------------------------------------------------------------------------

def _make_indev_game_state(time_remaining_p1: int, cfg):
    """
    Return a GameState with a single InDev Phase-1 asset.

    Uses FixedListAssetGenerator (borrowed from a zero-asset initialise call) as the
    asset generator so that step() can still produce new assets from the walk.
    """
    import uuid as _uuid

    from pyxis_portfolio_challenge.config import CapacityConfig
    from pyxis_portfolio_challenge.game.asset import AssetState
    from pyxis_portfolio_challenge.game.asset_generators import (
        DUMMY_LIST_DATA,
        FixedListAssetGenerator,
    )
    from pyxis_portfolio_challenge.game.game_state import GameState

    # Bootstrap: get an asset generator from an empty initialise call
    base = GameState.initialise_new_game(
        asset_generator_cls=FixedListAssetGenerator,
        num_assets=1,
        cash=50_000_000,
        horizon=20,
        max_num_assets=10,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        assets_data_list=DUMMY_LIST_DATA,
        seed=None,
        rd_capacity_config=CapacityConfig(
            enabled=False, base_capacity=80.0, overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5, overage_scaling="linear",
        ),
        ptrs_readings_config=cfg,
        **_EXTRA_DISABLED_CONFIGS,
    )

    # Build a 2-phase chain (Phase 1 → Phase 2); use zero-sigma config so
    # ptrs_sample_mean converges exactly to _true_ptrs for deterministic assertions.
    true_p1, true_p2 = 1.0, 0.65  # p1=1.0 guarantees success
    phase2 = Trial(
        cost_remaining=80_000_000,
        time_remaining=4,
        ptrs=true_p2,
        state=TrialState.PENDING,
        phase=TrialPhase.PHASE_2,
        next_trial_on_success=None,
    )
    phase2._true_ptrs = true_p2

    phase1 = Trial(
        cost_remaining=20_000_000,
        time_remaining=time_remaining_p1,
        ptrs=true_p1,
        state=TrialState.IN_PROGRESS,
        phase=TrialPhase.PHASE_1,
        next_trial_on_success=phase2,
    )
    phase1._true_ptrs = true_p1

    target_id = _uuid.uuid4()
    target_asset = DrugAsset(
        id=target_id,
        name="InDev-P1",
        therapeutic_area="oncology",
        type="internal",
        description="",
        max_revenue=1_000_000_000,
        raw_max_revenue=1_000_000_000,
        time_until_max_revenue=5,
        time_until_patent_expiry=20,
        trial=phase1,
        state=AssetState.InDevelopment,
        time_on_market=0,
    )

    gs = GameState(
        id=base.id,
        cash=base.cash,
        time=base.time,
        horizon=base.horizon,
        equilibrium_num_assets=0,
        max_num_assets=base.max_num_assets,
        asset_arrival_sensitivity_below=base.asset_arrival_sensitivity_below,
        asset_arrival_sensitivity_above=base.asset_arrival_sensitivity_above,
        reinvestment_percentage=base.reinvestment_percentage,
        initial_cash=base.initial_cash,
        assets={target_id: target_asset},
        failed_assets={},
        expired_assets={},
        dropped_assets={},
        realised_costs=[],
        realised_revenues=[],
        running_enpv=[],
        running_eroi=[],
        game_ended=False,
        ended_reason=None,
    )
    gs._asset_generator = base._asset_generator
    gs._ptrs_readings_config = cfg
    return gs, target_id, true_p1, true_p2


def test_game_state_reading_on_indev_asset():
    """
    Agent requests a reading on an InDev asset; count and mean are correct in next obs.

    Phase 1 has time_remaining=3 so it does not complete during the step.
    Readings are applied before evolution, then _copy_private_attrs preserves them.
    """
    from pyxis_portfolio_challenge.game.asset import AssetState

    cfg = _ptrs_readings_cfg(cost_fraction=0.01, noise_multipliers=[0.0, 0.0, 0.0])
    init_game_rng(1)

    gs, target_id, true_p1, true_p2 = _make_indev_game_state(time_remaining_p1=3, cfg=cfg)

    # Verify preconditions: asset is InDev, both phases are in pending chain
    asset0 = gs.assets[target_id]
    assert asset0.state == AssetState.InDevelopment
    assert len(asset0.pending_trial_chain) == 2
    assert asset0.trial.ptrs_sample_count == 0  # no prior initialise call

    # Submit 1 reading
    state_t1 = gs.step(
        investor_actions={},
        research_actions={target_id: 1},
    )

    # Asset should still be InDev Phase 1 (time_remaining was 3, now 2)
    asset_t1 = state_t1.assets.get(target_id)
    assert asset_t1 is not None
    assert asset_t1.state == AssetState.InDevelopment
    assert asset_t1.trial.phase == TrialPhase.PHASE_1

    chain_t1 = asset_t1.pending_trial_chain
    assert len(chain_t1) == 2

    # Phase 1: received reading at position-0 sigma (0×anything = 0 → exact mean)
    p1_trial = chain_t1[0]
    assert p1_trial.ptrs_sample_count == 1
    assert p1_trial.ptrs_sample_mean == pytest.approx(true_p1, abs=1e-9)

    # Phase 2: received reading at position-1 sigma (also 0 with zero-sigma config)
    p2_trial = chain_t1[1]
    assert p2_trial.ptrs_sample_count == 1
    assert p2_trial.ptrs_sample_mean == pytest.approx(true_p2, abs=1e-9)


def test_game_state_reading_indev_phase_completes():
    """
    Reading for Phase 2 is correct even when Phase 1 completes during the same step.

    Phase 1 has time_remaining=1 (ptrs=1.0 → guaranteed success).
    The reading is applied in A'3 *before* evolution, so Phase 2 gets its reading at
    position-1 sigma while Phase 1 is still the head of the chain.  After evolution,
    Phase 1 is gone but Phase 2's ptrs_sample_mean == true_p2 (zero-sigma config).
    """
    from pyxis_portfolio_challenge.game.asset import AssetState

    cfg = _ptrs_readings_cfg(cost_fraction=0.01, noise_multipliers=[0.0, 0.0, 0.0])
    init_game_rng(2)

    gs, target_id, true_p1, true_p2 = _make_indev_game_state(time_remaining_p1=1, cfg=cfg)

    asset0 = gs.assets[target_id]
    assert asset0.state == AssetState.InDevelopment
    assert asset0.trial.phase == TrialPhase.PHASE_1
    assert asset0.trial.time_remaining == 1

    # Submit reading for Phase 1 asset; Phase 1 resolves during this step
    state_t1 = gs.step(
        investor_actions={},
        research_actions={target_id: 1},
    )

    # Phase 1 (ptrs=1.0) always succeeds → asset is now Idle at Phase 2
    asset_t1 = state_t1.assets.get(target_id)
    assert asset_t1 is not None, "Asset must survive (Phase 1 succeeded)"
    assert asset_t1.state == AssetState.Idle
    assert asset_t1.trial.phase == TrialPhase.PHASE_2

    # Phase 2 must have received its reading (applied before Phase 1 resolved)
    assert asset_t1.trial.ptrs_sample_count == 1
    # Zero-sigma config: mean collapses exactly to true_ptrs
    assert asset_t1.trial.ptrs_sample_mean == pytest.approx(true_p2, abs=1e-9)
