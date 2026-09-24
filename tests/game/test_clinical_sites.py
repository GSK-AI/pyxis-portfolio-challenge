"""
Phase 1 tests for the clinical sites capacity feature.

Covers the config (Fibonacci purchase curve, validators, mutual exclusivity)
and the per-agent site accounting on ``GameState`` (Model B): starting
endowment, derived occupancy, free-site clamping, build-timer promotion, and
copy-forward of site state through a step.
"""

import pytest
from pydantic import ValidationError

from pyxis_portfolio_challenge.config import (
    ApprovalPhaseConfig,
    CapacityConfig,
    ClinicalSitesConfig,
    Config,
    DistributionalPtrsConfig,
    DropActionConfig,
    InterimTrialObservationsConfig,
    InvestmentLevelParams,
    InvestmentLevelsConfig,
    MarketingConfig,
    PtrsReadingsConfig,
    TAExperienceConfig,
    UncertainPtrsConfig,
    fibonacci_number,
    from_yaml,
)
from pyxis_portfolio_challenge.environment.market_mechanics import resolve_site_bid
from pyxis_portfolio_challenge.game.asset import AssetState
from pyxis_portfolio_challenge.game.asset_generators import (
    DUMMY_LIST_DATA,
    FixedListAssetGenerator,
)
from pyxis_portfolio_challenge.game.clinical_sites import resolve_site_grants
from pyxis_portfolio_challenge.game.game_state import GameState
from pyxis_portfolio_challenge.game.shared_market_state import (
    AlertType,
    SharedMarketState,
)
from pyxis_portfolio_challenge.rng import get_game_rng, init_game_rng


def _shared_market(**overrides) -> SharedMarketState:
    base = dict(
        congestion_exponent=1.0,
        congestion_ramp_steps=3,
        congestion_incumbent_penalty=0.0,
    )
    base.update(overrides)
    return SharedMarketState(**base)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sites_cfg(**overrides) -> ClinicalSitesConfig:
    base = dict(
        enabled=True,
        starting_sites=3,
        purchase_base_cost=500_000_000,
        purchase_cost_rounding=1,
        site_development_steps=2,
        agent_priority=False,
        priority_entropy_weight=1.0,
        auction_enabled=True,
        auction_interval_steps=20,
        auction_min_step=10,
        site_max_bid=100_000,
    )
    base.update(overrides)
    return ClinicalSitesConfig(**base)


def _make_state(sites_cfg, cash=10_000_000_000, num_assets=3) -> GameState:
    init_game_rng(42)
    return GameState.initialise_new_game(
        asset_generator_cls=FixedListAssetGenerator,
        num_assets=num_assets,
        cash=cash,
        horizon=10,
        max_num_assets=10,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        seed=None,
        assets_data_list=DUMMY_LIST_DATA,
        rd_capacity_config=CapacityConfig(
            enabled=False,
            base_capacity=80.0,
            overage_max_penalty=0.5,
            overage_cost_max_penalty=0.5,
            overage_scaling="linear",
        ),
        clinical_sites_config=sites_cfg,
        investment_levels_config=InvestmentLevelsConfig(
            enabled=False,
            levels={
                "none": InvestmentLevelParams(
                    cost_modifier=0.0,
                    speed_modifier=0.0,
                    success_modifier=1.0,
                    capacity_cost=0,
                    experience_modifier=0.0,
                ),
                "standard": InvestmentLevelParams(
                    cost_modifier=1.0,
                    speed_modifier=1.0,
                    success_modifier=1.0,
                    capacity_cost=2,
                    experience_modifier=1.0,
                ),
            },
        ),
        interim_trial_observations_config=InterimTrialObservationsConfig(
            enabled=False,
            latent_quality_concentration=10.0,
            initial_noise_scale=0.3,
        ),
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
        drop_action_config=DropActionConfig(
            enabled=False,
            drop_price_fraction=0.0,
            drop_price_rounding=1_000_000,
        ),
        marketing_config=MarketingConfig(
            enabled=False,
            dc_cost_fraction=0.035,
            dc_step_boost=0.10,
            dc_decay_rate=0.206,
            be_cost_fraction=0.0175,
            be_boost=0.25,
            be_decay_rate=0.206,
            be_effectiveness=3.5,
        ),
        ptrs_readings_config=PtrsReadingsConfig(
            enabled=False,
            cost_fraction=0.05,
            cost_rounding=1_000_000,
            action_space_max_readings=10,
            sigma_logit_base=1.5,
            sigma_ep=None,
            noise_multipliers=[1.0, 1.5, 2.0],
            max_sample_obs=20,
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
        approval_phase_config=ApprovalPhaseConfig(
            enabled=False,
            duration_min=1,
            duration_max=3,
            success_rate_min=0.85,
            success_rate_max=0.95,
            cost=50_000_000,
        ),
    )


def _develop_n(game_state: GameState, n: int) -> None:
    """Transition the first n Idle assets to InDevelopment in place."""
    developed = 0
    for aid, asset in list(game_state.assets.items()):
        if developed >= n:
            break
        if asset.state == AssetState.Idle:
            game_state.assets[aid] = asset.to_develop()
            developed += 1
    assert developed == n, "not enough Idle assets to develop"


# ---------------------------------------------------------------------------
# Config: Fibonacci purchase curve
# ---------------------------------------------------------------------------


def test_fibonacci_number_sequence():
    assert [fibonacci_number(n) for n in range(1, 8)] == [1, 1, 2, 3, 5, 8, 13]


def test_fibonacci_number_rejects_non_positive():
    with pytest.raises(ValueError):
        fibonacci_number(0)


def test_purchase_cost_follows_fibonacci():
    cfg = _sites_cfg(starting_sites=3, purchase_base_cost=500_000_000)
    # total_owned starts at starting_sites; kth purchase => base * fib(k)
    # (full Fibonacci, both leading 1s: 1, 1, 2, 3, 5, 8, ...)
    multipliers = [1, 1, 2, 3, 5, 8]
    for i, mult in enumerate(multipliers):
        assert cfg.purchase_cost(3 + i) == pytest.approx(500_000_000 * mult)


def test_purchase_cost_rounding():
    cfg = _sites_cfg(purchase_base_cost=333_333_333, purchase_cost_rounding=1_000_000)
    # 1st purchase = base * 1, rounded to nearest £1M
    assert cfg.purchase_cost(3) == 333_000_000


def test_purchase_cost_floors_below_starting():
    # total_owned below starting_sites (defensive) still costs at least the 1x base
    cfg = _sites_cfg(starting_sites=3, purchase_base_cost=500_000_000)
    assert cfg.purchase_cost(0) == pytest.approx(500_000_000)


# ---------------------------------------------------------------------------
# Config: validators + mutual exclusivity
# ---------------------------------------------------------------------------


def test_negative_starting_sites_rejected():
    with pytest.raises(ValidationError):
        _sites_cfg(starting_sites=-1)


def test_zero_step_counts_rejected():
    with pytest.raises(ValidationError):
        _sites_cfg(site_development_steps=0)
    with pytest.raises(ValidationError):
        _sites_cfg(auction_interval_steps=0)


def test_clinical_sites_and_rd_capacity_mutually_exclusive():
    data = from_yaml().model_dump()
    data["clinical_sites"]["enabled"] = True
    data["rd_capacity"]["enabled"] = True
    with pytest.raises(ValidationError, match="mutually exclusive"):
        Config.model_validate(data)


def test_clinical_sites_disabled_with_rd_capacity_ok():
    data = from_yaml().model_dump()
    data["clinical_sites"]["enabled"] = False
    data["rd_capacity"]["enabled"] = True
    # Should not raise
    Config.model_validate(data)


# ---------------------------------------------------------------------------
# GameState: starting endowment + enabled gating
# ---------------------------------------------------------------------------


def test_starting_sites_seeded_when_enabled():
    gs = _make_state(_sites_cfg(starting_sites=3))
    assert gs.clinical_sites_enabled is True
    assert gs.operational_sites == 3
    assert gs.sites_in_development == []


def test_no_sites_when_feature_disabled():
    gs = _make_state(_sites_cfg(enabled=False, starting_sites=3))
    assert gs.clinical_sites_enabled is False
    assert gs.operational_sites == 0
    assert gs.free_sites == 0


def test_no_sites_when_config_disabled():
    gs = _make_state(_sites_cfg(enabled=False))
    assert gs.clinical_sites_enabled is False
    assert gs.operational_sites == 0


# ---------------------------------------------------------------------------
# GameState: derived occupancy + free-site clamping
# ---------------------------------------------------------------------------


def test_sites_occupied_derived_from_in_development():
    gs = _make_state(_sites_cfg(starting_sites=3))
    assert gs.sites_occupied == 0
    assert gs.free_sites == 3
    _develop_n(gs, 2)
    assert gs.sites_occupied == 2
    assert gs.free_sites == 1


def test_free_sites_never_negative_when_overbooked():
    gs = _make_state(_sites_cfg(starting_sites=1))
    gs.operational_sites = 1
    _develop_n(gs, 2)  # more trials than operational sites
    assert gs.sites_occupied == 2
    assert gs.free_sites == 0


def test_total_sites_owned_counts_in_development():
    gs = _make_state(_sites_cfg(starting_sites=3))
    gs.sites_in_development = [2, 1]
    assert gs.total_sites_owned == 5


# ---------------------------------------------------------------------------
# GameState: purchase cost + affordability
# ---------------------------------------------------------------------------


def test_next_site_purchase_cost_matches_config():
    cfg = _sites_cfg(starting_sites=3, purchase_base_cost=500_000_000)
    gs = _make_state(cfg)
    assert gs.next_site_purchase_cost() == cfg.purchase_cost(gs.total_sites_owned)
    gs.sites_in_development = [2]  # now owns 4
    assert gs.next_site_purchase_cost() == cfg.purchase_cost(4)


def test_can_afford_site_purchase():
    cfg = _sites_cfg(purchase_base_cost=1_000_000_000)
    gs = _make_state(cfg, cash=1_500_000_000)
    assert gs.can_afford_site_purchase() is True
    gs.cash = 500_000_000
    assert gs.can_afford_site_purchase() is False


def test_purchase_helpers_noop_when_disabled():
    gs = _make_state(_sites_cfg(enabled=False))
    assert gs.next_site_purchase_cost() == 0.0
    assert gs.can_afford_site_purchase() is False


# ---------------------------------------------------------------------------
# GameState: build-timer promotion
# ---------------------------------------------------------------------------


def test_advance_site_timers_promotes_finished():
    gs = _make_state(_sites_cfg(starting_sites=3))
    gs.sites_in_development = [1, 2]
    promoted = gs.advance_site_timers()
    assert promoted == 1
    assert gs.operational_sites == 4
    assert gs.sites_in_development == [1]


def test_start_site_build_then_two_step_delay():
    cfg = _sites_cfg(starting_sites=3, site_development_steps=2)
    gs = _make_state(cfg)
    gs.start_site_build()
    assert gs.sites_in_development == [2]
    assert gs.operational_sites == 3
    # Year 1: not yet ready
    assert gs.advance_site_timers() == 0
    assert gs.sites_in_development == [1]
    assert gs.operational_sites == 3
    # Year 2: becomes operational
    assert gs.advance_site_timers() == 1
    assert gs.sites_in_development == []
    assert gs.operational_sites == 4


def test_add_operational_site_immediate():
    gs = _make_state(_sites_cfg(starting_sites=3))
    gs.add_operational_site()
    assert gs.operational_sites == 4
    assert gs.sites_in_development == []


def test_site_mutators_noop_when_disabled():
    gs = _make_state(_sites_cfg(enabled=False))
    gs.start_site_build()
    gs.add_operational_site()
    assert gs.advance_site_timers() == 0
    assert gs.operational_sites == 0
    assert gs.sites_in_development == []


# ---------------------------------------------------------------------------
# Copy-forward: site state + config survive a step
# ---------------------------------------------------------------------------


def test_site_state_copied_forward_through_step():
    gs = _make_state(_sites_cfg(starting_sites=3))
    gs.operational_sites = 4
    gs.sites_in_development = []
    next_state = gs.step({})
    assert next_state.operational_sites == 4
    assert next_state.sites_in_development == []
    assert next_state._clinical_sites_config is gs._clinical_sites_config
    assert next_state.clinical_sites_enabled is True


# ---------------------------------------------------------------------------
# Gate resolution (pure helper)
# ---------------------------------------------------------------------------


def test_resolve_grants_all_when_enough_sites():
    assert resolve_site_grants([0, 1, 2], free_sites=3) == {0, 1, 2}
    assert resolve_site_grants([0, 1], free_sites=5) == {0, 1}


def test_resolve_grants_none_when_no_free_sites():
    assert resolve_site_grants([0, 1, 2], free_sites=0) == set()


def test_resolve_grants_index_order_when_over_requested():
    # 3 requests, 2 sites, no priorities -> lowest indices win
    assert resolve_site_grants([0, 1, 2], free_sites=2) == {0, 1}
    # request order is the fallback order, not numeric sort of the values
    assert resolve_site_grants(["a", "b", "c"], free_sites=1) == {"a"}


def test_resolve_grants_priority_order():
    # highest priority wins regardless of index order
    prios = {0: 0.1, 1: 0.9, 2: 0.5}
    assert resolve_site_grants([0, 1, 2], free_sites=1, priorities=prios) == {1}
    assert resolve_site_grants([0, 1, 2], free_sites=2, priorities=prios) == {1, 2}


def test_resolve_grants_priority_ties_break_by_request_order():
    # equal priority -> stable sort keeps request (index) order as tiebreak
    prios = {0: 0.5, 1: 0.5, 2: 0.5}
    assert resolve_site_grants([0, 1, 2], free_sites=2, priorities=prios) == {0, 1}


# ---------------------------------------------------------------------------
# Gate integration through GameState.step
# ---------------------------------------------------------------------------


def _in_dev_ids(game_state: GameState) -> set:
    return {
        aid
        for aid, a in game_state.assets.items()
        if a.state == AssetState.InDevelopment
    }


def _idle_ids(game_state: GameState) -> list:
    return [aid for aid, a in game_state.assets.items() if a.state == AssetState.Idle]


def test_step_gate_limits_new_trials_to_free_sites():
    gs = _make_state(_sites_cfg(starting_sites=1), num_assets=3)
    idle_ids = _idle_ids(gs)
    assert len(idle_ids) >= 2  # need an over-request to exercise the gate
    nxt = gs.step({aid: "invest" for aid in idle_ids})
    # Only one site free -> exactly one new trial started
    assert len(_in_dev_ids(nxt)) == 1


def test_step_gate_disabled_allows_all_new_trials():
    gs = _make_state(_sites_cfg(enabled=False), num_assets=3)
    idle_ids = _idle_ids(gs)
    nxt = gs.step({aid: "invest" for aid in idle_ids})
    # No gate -> every requested idle asset starts
    assert len(_in_dev_ids(nxt)) == len(idle_ids)


def test_step_gate_denied_request_is_costless():
    # With 1 site, requesting many costs the same as requesting 1 (denied=no-op).
    one_state = _make_state(_sites_cfg(starting_sites=1), num_assets=3)
    idle_ids = _idle_ids(one_state)
    assert len(idle_ids) >= 2
    one = one_state.step({idle_ids[0]: "invest"})

    many_state = _make_state(_sites_cfg(starting_sites=1), num_assets=3)
    many = many_state.step({aid: "invest" for aid in idle_ids})

    # Same number developed, same cash spent (denied requests charged nothing)
    assert len(_in_dev_ids(one)) == len(_in_dev_ids(many)) == 1
    assert one.cash == pytest.approx(many.cash)


def test_step_gate_priority_selects_requested_asset():
    gs = _make_state(_sites_cfg(starting_sites=1, agent_priority=True), num_assets=3)
    idle_ids = _idle_ids(gs)
    assert len(idle_ids) >= 2
    # Favour the last idle asset via priority; it should win the single site.
    priorities = {aid: 0.1 for aid in idle_ids}
    priorities[idle_ids[-1]] = 0.9
    nxt = gs.step({aid: "invest" for aid in idle_ids}, site_priorities=priorities)
    assert _in_dev_ids(nxt) == {idle_ids[-1]}


def test_step_promotes_built_site_before_gate():
    # A site finishing its build this step frees capacity for a new trial.
    gs = _make_state(_sites_cfg(starting_sites=0), num_assets=3)
    gs.operational_sites = 0
    gs.sites_in_development = [1]  # promotes to operational at this step start
    idle_ids = _idle_ids(gs)
    nxt = gs.step({aid: "invest" for aid in idle_ids})
    assert nxt.operational_sites == 1
    assert nxt.sites_in_development == []
    assert len(_in_dev_ids(nxt)) == 1


# ---------------------------------------------------------------------------
# Upgrade action: buying sites through GameState.step
# ---------------------------------------------------------------------------


def test_buy_site_charges_cost_and_starts_build():
    cfg = _sites_cfg(starting_sites=3, purchase_base_cost=500_000_000)
    gs = _make_state(cfg, cash=10_000_000_000)
    expected_cost = gs.next_site_purchase_cost()
    bought = gs.step({}, buy_site=True)
    baseline = _make_state(cfg, cash=10_000_000_000).step({})
    # Site enters the build pipeline (not immediately operational).
    assert bought.operational_sites == 3
    assert bought.sites_in_development == [cfg.site_development_steps]
    assert bought.total_sites_owned == 4
    # The only cash difference vs a no-buy step is the purchase cost.
    assert baseline.cash - bought.cash == pytest.approx(expected_cost)


def test_buy_site_becomes_operational_after_build_delay():
    cfg = _sites_cfg(starting_sites=3, site_development_steps=2)
    gs = _make_state(cfg, cash=10_000_000_000)
    s1 = gs.step({}, buy_site=True)
    assert s1.sites_in_development == [2]
    # Year 1: timer decrements at next step start, still building.
    s2 = s1.step({})
    assert s2.operational_sites == 3
    assert s2.sites_in_development == [1]
    # Year 2: promoted to operational.
    s3 = s2.step({})
    assert s3.operational_sites == 4
    assert s3.sites_in_development == []


def test_buy_site_unaffordable_is_noop():
    cfg = _sites_cfg(starting_sites=3, purchase_base_cost=1_000_000_000)
    gs = _make_state(cfg, cash=500_000_000)  # cannot afford 1x base
    bought = gs.step({}, buy_site=True)
    baseline = _make_state(cfg, cash=500_000_000).step({})
    assert bought.sites_in_development == []
    assert bought.operational_sites == 3
    assert bought.cash == pytest.approx(baseline.cash)


def test_buy_site_noop_when_disabled():
    gs = _make_state(_sites_cfg(enabled=False), cash=10_000_000_000)
    bought = gs.step({}, buy_site=True)
    baseline = _make_state(_sites_cfg(enabled=False), cash=10_000_000_000).step({})
    assert bought.operational_sites == 0
    assert bought.sites_in_development == []
    assert bought.cash == pytest.approx(baseline.cash)


def test_repeated_purchases_follow_fibonacci_cost():
    cfg = _sites_cfg(starting_sites=3, purchase_base_cost=500_000_000)
    gs = _make_state(cfg, cash=100_000_000_000)
    costs = []
    state = gs
    for _ in range(3):
        costs.append(state.next_site_purchase_cost())
        state = state.step({}, buy_site=True)
    # 1x, 1x, 2x base (total_owned grows with each purchase incl. in-dev sites)
    assert costs == pytest.approx([500_000_000, 500_000_000, 1_000_000_000])


def test_in_development_asset_does_not_consume_a_new_site():
    # An asset already InDevelopment occupies a site but is not counted as a new
    # site request; only fresh Idle->InDevelopment transitions hit the gate.
    gs = _make_state(_sites_cfg(starting_sites=1), num_assets=3)
    idle_ids = _idle_ids(gs)
    assert len(idle_ids) >= 2
    nxt = gs.step({idle_ids[0]: "invest"})
    assert len(_in_dev_ids(nxt)) == 1
    # One site, now occupied -> free_sites is 0 and a further new trial is denied.
    assert nxt.free_sites == 0
    remaining_idle = _idle_ids(nxt)
    nxt2 = nxt.step({remaining_idle[0]: "invest"})
    # The occupied in-dev asset stays in dev; the new request is denied (no-op).
    assert len(_in_dev_ids(nxt2)) == 1
    assert remaining_idle[0] not in _in_dev_ids(nxt2)


# ---------------------------------------------------------------------------
# Site auction (PvP): resolve_site_bid
# ---------------------------------------------------------------------------


def test_resolve_site_bid_highest_wins_pays_own_bid():
    init_game_rng(1)
    winner, price = resolve_site_bid(
        {"a": 1_000_000, "b": 3_000_000, "c": 2_000_000}, get_game_rng()
    )
    assert winner == "b"
    assert price == pytest.approx(3_000_000)


def test_resolve_site_bid_no_bids_returns_none():
    init_game_rng(1)
    assert resolve_site_bid({}, get_game_rng()) == (None, 0.0)
    # Zero / negative bids are passes
    assert resolve_site_bid({"a": 0.0, "b": -5.0}, get_game_rng()) == (None, 0.0)


def test_resolve_site_bid_ties_break_randomly_but_price_fixed():
    init_game_rng(7)
    winner, price = resolve_site_bid({"a": 2_000_000, "b": 2_000_000}, get_game_rng())
    assert winner in {"a", "b"}
    assert price == pytest.approx(2_000_000)


# ---------------------------------------------------------------------------
# Site auction cadence: SharedMarketState.site_auction_available
# ---------------------------------------------------------------------------


def test_site_auction_cadence():
    sm = _shared_market(
        site_auction_enabled=True,
        site_auction_interval_steps=20,
        site_auction_min_step=5,
    )
    sm.time = 4
    assert sm.site_auction_available() is False  # before warmup
    sm.time = 5
    assert sm.site_auction_available() is True  # first auction at warmup
    sm.time = 6
    assert sm.site_auction_available() is False
    sm.time = 25
    assert sm.site_auction_available() is True  # every interval thereafter


def test_site_auction_disabled_never_available():
    sm = _shared_market(site_auction_enabled=False, site_auction_min_step=0)
    for t in range(0, 40):
        sm.time = t
        assert sm.site_auction_available() is False


def test_register_site_deal_emits_priced_alert():
    sm = _shared_market(site_auction_enabled=True)
    sm.time = 3
    sm.register_site_deal("pharma_0", price=4_200_000)
    deals = [a for a in sm.alerts if a.event_type == AlertType.CLINICAL_SITE_DEAL]
    assert len(deals) == 1
    assert deals[0].agent_id == "pharma_0"
    assert deals[0].details["price"] == pytest.approx(4_200_000)
    # Opponents can see the winning price via the alert feed
    assert sm.get_alerts_for_agent("pharma_1")[0].details["price"] == pytest.approx(
        4_200_000
    )


# ---------------------------------------------------------------------------
# Site auction win: GameState.with_auction_site_win
# ---------------------------------------------------------------------------


def test_with_auction_site_win_immediate_and_charged():
    gs = _make_state(_sites_cfg(starting_sites=3), cash=10_000_000_000)
    won = gs.with_auction_site_win(price=2_000_000)
    # Won site is immediately operational (no build delay).
    assert won.operational_sites == 4
    assert won.sites_in_development == []
    assert won.cash == pytest.approx(gs.cash - 2_000_000)
    # Counts toward future Fibonacci purchase cost.
    assert won.total_sites_owned == 4
    # Original is untouched.
    assert gs.operational_sites == 3
    assert gs.cash == pytest.approx(10_000_000_000)


def test_with_auction_site_win_overbid_can_bankrupt():
    gs = _make_state(_sites_cfg(starting_sites=3), cash=1_000_000)
    won = gs.with_auction_site_win(price=5_000_000)  # overbid, no affordability mask
    assert won.cash == pytest.approx(-4_000_000)
    assert won.game_ended is True
    assert won.operational_sites == 4
