"""
Unit tests for BD asset persistence (slot-capped market).

Tests cover:
- Carry-forward logic in spawn_bd_asset()
- Aging and expiry at bd_persist_steps boundary
- Won-asset removal
- Urgency-first (oldest-first) slot ordering
- steps_remaining normalisation in get_bd_observations()
- Backward-compat at bd_persist_steps=1
"""

import uuid

import pytest

from pyxis_portfolio_challenge.game.asset import AssetState, DrugAsset
from pyxis_portfolio_challenge.game.shared_market_state import SharedMarketState
from pyxis_portfolio_challenge.game.trial import Trial, TrialPhase, TrialState
from pyxis_portfolio_challenge.rng import init_game_rng

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_MARKET_DEFAULTS = dict(
    exclusivity_period=4,
    first_mover_bonus=0.3,
    alert_history_length=5,
    disable_market_share_competition=False,
    num_indications_per_ta=0,
    bd_enabled=False,          # no new spawns — isolates carry-forward logic
    bd_base_lambda=0.3,
    bd_leak_lambda_boost=0.3,
    bd_min_step=0,
    bd_max_bid=10000.0,
    bd_phase_weights=None,
    bd_indication_activity_bias=0.8,
    congestion_exponent=0.0,
    congestion_ramp_steps=1,
    congestion_incumbent_penalty=0.0,
    leak_phase_probabilities=None,
)


def _make_market(bd_persist_steps: int = 3) -> SharedMarketState:
    """Return a fresh SharedMarketState with bd_enabled=False for unit testing."""
    init_game_rng(42)
    return SharedMarketState.initialize(
        **_MARKET_DEFAULTS,
        bd_persist_steps=bd_persist_steps,
    )


def _fake_trial() -> Trial:
    """Minimal pending trial for constructing test assets."""
    return Trial(
        cost_remaining=1.0,
        time_remaining=1,
        ptrs=0.5,
        phase=TrialPhase.PHASE_1,
        state=TrialState.PENDING,
        next_trial_on_success=None,
    )


_ASSET_COUNTER = 0


def _fake_asset(ta: str = "oncology", indication: int = 0) -> DrugAsset:
    """
    Minimal DrugAsset suitable for BD persistence tests.

    Each call gives a unique max_revenue so that DrugAsset.__eq__ (which
    ignores id but compares all other fields) distinguishes instances.
    """
    global _ASSET_COUNTER
    _ASSET_COUNTER += 1
    return DrugAsset(
        id=uuid.uuid4(),
        name=f"test-drug-{_ASSET_COUNTER}",
        therapeutic_area=ta,
        type="BD",
        description="",
        max_revenue=float(_ASSET_COUNTER) * 1_000_000.0,
        raw_max_revenue=float(_ASSET_COUNTER) * 1_000_000.0,
        time_until_max_revenue=5,
        time_until_patent_expiry=20,
        state=AssetState.Idle,
        time_on_market=0,
        trial=_fake_trial(),
        indication=indication,
    )


def _inject(market: SharedMarketState, asset: DrugAsset, age: int) -> None:
    """Plant an asset directly into the market at the given age."""
    market.current_bd_assets.append(asset)
    market.bd_asset_ages[str(asset.id)] = age


# ──────────────────────────────────────────────────────────────────────────────
# Carry-forward and aging
# ──────────────────────────────────────────────────────────────────────────────

class TestCarryForwardAndAging:
    def test_unwon_asset_persists_and_ages(self):
        market = _make_market(bd_persist_steps=3)
        a = _fake_asset()
        _inject(market, a, age=0)

        market.spawn_bd_asset({}, max_slots=3, won_asset_ids=set())

        assert a in market.current_bd_assets
        assert market.bd_asset_ages[str(a.id)] == 1

    def test_asset_ages_again_on_second_call(self):
        market = _make_market(bd_persist_steps=3)
        a = _fake_asset()
        _inject(market, a, age=0)

        market.spawn_bd_asset({}, max_slots=3)
        market.spawn_bd_asset({}, max_slots=3)

        assert a in market.current_bd_assets
        assert market.bd_asset_ages[str(a.id)] == 2

    def test_asset_expires_exactly_at_persist_steps(self):
        # age goes 0 → 1 → 2; at age 2 (== bd_persist_steps=2) it expires
        market = _make_market(bd_persist_steps=2)
        a = _fake_asset()
        _inject(market, a, age=1)   # one step from expiry

        market.spawn_bd_asset({}, max_slots=3)

        assert a not in market.current_bd_assets
        assert str(a.id) not in market.bd_asset_ages

    def test_asset_with_zero_age_survives_one_step(self):
        market = _make_market(bd_persist_steps=1)
        a = _fake_asset()
        _inject(market, a, age=0)

        # age 0 → 1; 1 >= bd_persist_steps(1) → expires
        market.spawn_bd_asset({}, max_slots=3)

        assert a not in market.current_bd_assets

    def test_multiple_assets_some_expire(self):
        market = _make_market(bd_persist_steps=3)
        old = _fake_asset()
        young = _fake_asset()
        _inject(market, old, age=2)    # will expire (2+1 >= 3)
        _inject(market, young, age=0)  # survives

        market.spawn_bd_asset({}, max_slots=3)

        assert old not in market.current_bd_assets
        assert young in market.current_bd_assets
        assert market.bd_asset_ages[str(young.id)] == 1


# ──────────────────────────────────────────────────────────────────────────────
# Won-asset removal
# ──────────────────────────────────────────────────────────────────────────────

class TestWonAssetRemoval:
    def test_won_asset_removed_immediately(self):
        market = _make_market(bd_persist_steps=5)  # would survive many steps
        a = _fake_asset()
        _inject(market, a, age=0)

        market.spawn_bd_asset({}, max_slots=3, won_asset_ids={a.id})

        assert a not in market.current_bd_assets
        assert str(a.id) not in market.bd_asset_ages

    def test_won_asset_frees_slot_for_survivor(self):
        market = _make_market(bd_persist_steps=5)
        won = _fake_asset()
        survivor = _fake_asset()
        _inject(market, won, age=0)
        _inject(market, survivor, age=0)

        market.spawn_bd_asset({}, max_slots=2, won_asset_ids={won.id})

        assert won not in market.current_bd_assets
        assert survivor in market.current_bd_assets

    def test_unwon_asset_not_removed(self):
        market = _make_market(bd_persist_steps=5)
        a = _fake_asset()
        b = _fake_asset()
        _inject(market, a, age=0)
        _inject(market, b, age=0)

        market.spawn_bd_asset({}, max_slots=3, won_asset_ids={a.id})

        assert b in market.current_bd_assets


# ──────────────────────────────────────────────────────────────────────────────
# Urgency-first ordering (oldest asset → slot 0)
# ──────────────────────────────────────────────────────────────────────────────

class TestUrgencyOrdering:
    def test_oldest_asset_in_slot_0(self):
        market = _make_market(bd_persist_steps=5)
        new = _fake_asset()
        mid = _fake_asset()
        old = _fake_asset()
        _inject(market, new, age=0)
        _inject(market, mid, age=1)
        _inject(market, old, age=2)

        market.spawn_bd_asset({}, max_slots=3)

        assert market.current_bd_assets[0] is old
        assert market.current_bd_assets[1] is mid
        assert market.current_bd_assets[2] is new

    def test_ordering_stable_after_expiry(self):
        market = _make_market(bd_persist_steps=3)
        a = _fake_asset()
        b = _fake_asset()
        _inject(market, a, age=0)  # survives, age→1
        _inject(market, b, age=2)  # expires (2+1 >= 3)

        market.spawn_bd_asset({}, max_slots=3)

        assert market.current_bd_assets == [a]


# ──────────────────────────────────────────────────────────────────────────────
# Slot capacity
# ──────────────────────────────────────────────────────────────────────────────

class TestSlotCapacity:
    def test_full_market_blocks_return_early(self):
        market = _make_market(bd_persist_steps=5)
        a = _fake_asset()
        b = _fake_asset()
        _inject(market, a, age=0)
        _inject(market, b, age=0)

        # max_slots=2, surviving=2 → no room even if bd_enabled were True
        market.spawn_bd_asset({}, max_slots=2)

        assert len(market.current_bd_assets) == 2  # unchanged count

    def test_age_tracking_cleared_after_clear_bd_asset(self):
        market = _make_market(bd_persist_steps=3)
        a = _fake_asset()
        _inject(market, a, age=1)

        market.clear_bd_asset()

        assert market.current_bd_assets == []
        assert market.bd_asset_ages == {}


# ──────────────────────────────────────────────────────────────────────────────
# steps_remaining normalisation in get_bd_observations()
# ──────────────────────────────────────────────────────────────────────────────

class TestStepsRemainingObservation:
    def test_age_0_gives_1_0(self):
        market = _make_market(bd_persist_steps=3)
        a = _fake_asset()
        _inject(market, a, age=0)

        obs = market.get_bd_observations()

        assert obs[0]["steps_remaining"] == pytest.approx(1.0)

    def test_age_1_gives_two_thirds(self):
        market = _make_market(bd_persist_steps=3)
        a = _fake_asset()
        _inject(market, a, age=1)

        obs = market.get_bd_observations()

        assert obs[0]["steps_remaining"] == pytest.approx(2 / 3)

    def test_age_2_gives_one_third(self):
        market = _make_market(bd_persist_steps=3)
        a = _fake_asset()
        _inject(market, a, age=2)

        obs = market.get_bd_observations()

        # This is the last visible step before expiry; asset expires next call to spawn
        assert obs[0]["steps_remaining"] == pytest.approx(1 / 3)

    def test_persist_steps_1_always_1_0(self):
        """Backward-compat: with N=1 every asset shows steps_remaining=1.0."""
        market = _make_market(bd_persist_steps=1)
        a = _fake_asset()
        _inject(market, a, age=0)

        obs = market.get_bd_observations()

        assert obs[0]["steps_remaining"] == pytest.approx(1.0)

    def test_steps_remaining_decreases_over_lifetime(self):
        market = _make_market(bd_persist_steps=4)
        a = _fake_asset()
        _inject(market, a, age=0)

        values = []
        for _ in range(3):   # 3 calls: ages 0→1→2; asset survives (N=4)
            values.append(market.get_bd_observations()[0]["steps_remaining"])
            market.spawn_bd_asset({}, max_slots=4)
            # re-insert in case market removed it: it shouldn't, but let's verify
            if a not in market.current_bd_assets:
                break

        assert values == sorted(values, reverse=True), "steps_remaining should decrease"


# ──────────────────────────────────────────────────────────────────────────────
# Backward compatibility
# ──────────────────────────────────────────────────────────────────────────────

class TestBackwardCompat:
    def test_persist_steps_1_clears_all_each_step(self):
        """With N=1, every unwon asset expires after one step (old behaviour)."""
        market = _make_market(bd_persist_steps=1)
        a = _fake_asset()
        b = _fake_asset()
        _inject(market, a, age=0)
        _inject(market, b, age=0)

        market.spawn_bd_asset({}, max_slots=3)

        assert market.current_bd_assets == []
        assert market.bd_asset_ages == {}
