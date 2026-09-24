import pytest
from pydantic import ValidationError

from pyxis_portfolio_challenge import PROJECT_ROOT, config
from pyxis_portfolio_challenge.config import (
    DropActionConfig,
    MarketingConfig,
    PtrsReadingsConfig,
)


def test_config_loading():
    cfg = config.from_yaml()
    assert cfg.equilibrium_num_assets > 0
    assert cfg.max_num_assets >= cfg.equilibrium_num_assets
    assert cfg.starting_cash > 0
    assert cfg.horizon > 0
    assert isinstance(cfg.shuffle_order, bool)
    assert "_target_" in cfg.reward_fn
    assert cfg.training_data_dir and cfg.evaluation_data_dir != ""


def test_from_yaml_default_arg_loads_correct_file():
    default_path = f"{PROJECT_ROOT}/pyxis_portfolio_challenge/config.yaml"
    cfg1 = config.from_yaml()
    cfg2 = config.from_yaml(path=default_path)
    assert cfg1 == cfg2


def test_instantiate_from_config_args():
    sample_config = {
        "_target_": "builtins.list",
        "": [1, 2, 3],
    }
    instantiated_obj = config.instantiate_from_config(sample_config)
    assert isinstance(instantiated_obj, list)
    assert instantiated_obj == [1, 2, 3]


def test_instantiate_from_config_kwargs():
    sample_config = {
        "_target_": "collections.Counter",
        "a": 2,
        "b": 3,
    }
    instantiated_obj = config.instantiate_from_config(sample_config)
    from collections import Counter

    assert isinstance(instantiated_obj, Counter)
    assert instantiated_obj == Counter(a=2, b=3)


def test_instantiate_from_config_mixed():
    sample_config = {
        "_target_": "collections.defaultdict",
        "": int,
        "a": 5,
    }
    instantiated_obj = config.instantiate_from_config(sample_config)
    from collections import defaultdict

    assert isinstance(instantiated_obj, defaultdict)
    assert instantiated_obj["a"] == 5
    assert instantiated_obj["b"] == 0  # default factory is int


class TestDropActionConfig:
    def test_defaults(self):
        cfg = DropActionConfig(
            enabled=True, drop_price_fraction=0.0, drop_price_rounding=1_000_000
        )
        assert cfg.enabled is True
        assert cfg.drop_price_fraction == 0.0
        assert cfg.drop_price_rounding == 1_000_000

    @pytest.mark.parametrize("fraction", [0.0, 0.25, 1.0])
    def test_fraction_in_range_accepted(self, fraction):
        cfg = DropActionConfig(
            enabled=True, drop_price_fraction=fraction, drop_price_rounding=1_000_000
        )
        assert cfg.drop_price_fraction == fraction

    @pytest.mark.parametrize("fraction", [-0.01, 1.01, 2.0, -1.0])
    def test_fraction_out_of_range_rejected(self, fraction):
        with pytest.raises(ValidationError, match="between 0.0 and 1.0"):
            DropActionConfig(enabled=True, drop_price_fraction=fraction)

    def test_frozen(self):
        cfg = DropActionConfig(
            enabled=True, drop_price_fraction=0.0, drop_price_rounding=1_000_000
        )
        with pytest.raises(ValidationError):
            cfg.enabled = False

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            DropActionConfig(enabled=True, not_a_real_field=1)


class TestMarketingConfigCostHelpers:
    """
    The engine step and the HTTP response layer share these helpers so the
    displayed marketing cost can never drift from what is actually charged.
    """

    @staticmethod
    def _cfg(**overrides):
        params = dict(
            enabled=True,
            dc_cost_fraction=0.05,
            dc_step_boost=0.20,
            dc_decay_rate=0.067,
            be_cost_fraction=0.03,
            be_boost=0.1,
            be_decay_rate=0.206,
            be_effectiveness=0.3,
        )
        params.update(overrides)
        return MarketingConfig(**params)

    def test_dc_cost_is_fraction_of_peak_revenue(self):
        cfg = self._cfg(dc_cost_fraction=0.05)
        assert cfg.dc_cost(2_000_000_000.0) == pytest.approx(100_000_000.0)

    def test_dc_cost_is_flat_across_peak_revenue_anchor(self):
        # DC cost is anchored to the pool-wide peak, so the same peak always
        # yields the same cost regardless of any individual asset.
        cfg = self._cfg()
        assert cfg.dc_cost(1_000_000_000.0) == cfg.dc_cost(1_000_000_000.0)

    def test_be_cost_scales_with_asset_max_revenue(self):
        cfg = self._cfg(be_cost_fraction=0.03)
        assert cfg.be_cost(1_000_000_000.0) == pytest.approx(30_000_000.0)
        # Bigger drug -> proportionally bigger push cost.
        assert cfg.be_cost(2_000_000_000.0) == pytest.approx(
            2 * cfg.be_cost(1_000_000_000.0)
        )

    def test_costs_zero_when_revenue_zero(self):
        cfg = self._cfg()
        assert cfg.dc_cost(0.0) == 0.0
        assert cfg.be_cost(0.0) == 0.0


class TestMarketingConfigProjectionHelpers:
    """
    The engine step and the HTTP response layer share these projection helpers so
    the forward-looking preview shown before committing a spend can never drift
    from what the engine actually produces next step.
    """

    @staticmethod
    def _cfg(**overrides):
        params = dict(
            enabled=True,
            dc_cost_fraction=0.05,
            dc_step_boost=0.20,
            dc_decay_rate=0.10,
            be_cost_fraction=0.03,
            be_boost=0.25,
            be_decay_rate=0.20,
            be_effectiveness=0.3,
        )
        params.update(overrides)
        return MarketingConfig(**params)

    def test_next_brand_score_spend_adds_boost_then_decays(self):
        cfg = self._cfg(be_boost=0.25, be_decay_rate=0.20)
        # (current + boost) * (1 - decay) = (0.30 + 0.25) * 0.80 = 0.44
        assert cfg.next_brand_score(0.30, floor=0.0, spend=True) == pytest.approx(
            0.44
        )

    def test_next_brand_score_hold_decays_only(self):
        cfg = self._cfg(be_boost=0.25, be_decay_rate=0.20)
        # current * (1 - decay) = 0.30 * 0.80 = 0.24 (no boost)
        assert cfg.next_brand_score(0.30, floor=0.0, spend=False) == pytest.approx(
            0.24
        )

    def test_next_brand_score_never_below_floor(self):
        cfg = self._cfg(be_boost=0.25, be_decay_rate=0.20)
        # Decayed value (0.24) is below the floor, so the floor holds.
        assert cfg.next_brand_score(0.30, floor=0.30, spend=False) == pytest.approx(
            0.30
        )

    def test_next_demand_multiplier_spend_adds_boost_then_decays_headroom(self):
        cfg = self._cfg(dc_step_boost=0.20, dc_decay_rate=0.10)
        # 1 + ((1.50 + 0.20) - 1) * (1 - 0.10) = 1 + 0.70 * 0.90 = 1.63
        assert cfg.next_demand_multiplier(1.50, spend=True) == pytest.approx(1.63)

    def test_next_demand_multiplier_hold_decays_toward_base(self):
        cfg = self._cfg(dc_step_boost=0.20, dc_decay_rate=0.10)
        # 1 + (1.50 - 1) * (1 - 0.10) = 1 + 0.50 * 0.90 = 1.45
        assert cfg.next_demand_multiplier(1.50, spend=False) == pytest.approx(1.45)

    def test_next_demand_multiplier_base_holds_when_no_spend(self):
        cfg = self._cfg()
        # At the 1.0 base with no spend there is no headroom to decay.
        assert cfg.next_demand_multiplier(1.0, spend=False) == pytest.approx(1.0)


class TestPtrsReadingsConfigHelpers:
    """
    The engine step and the HTTP response layer share these helpers so the
    displayed reading cost and confidence signal can never drift from what the
    step actually charges / the observation actually exposes.
    """

    @staticmethod
    def _cfg(**overrides):
        params = dict(
            enabled=True,
            cost_fraction=0.05,
            cost_rounding=1_000_000,
            action_space_max_readings=5,
            sigma_logit_base=1.5,
            sigma_ep=None,
            noise_multipliers=[1.0, 1.5, 2.0],
            max_sample_obs=10,
        )
        params.update(overrides)
        return PtrsReadingsConfig(**params)

    def test_reading_base_cost_is_rounded_fraction_of_cost_remaining(self):
        cfg = self._cfg(cost_fraction=0.05, cost_rounding=1_000_000)
        # 0.05 * 101_400_000 = 5_070_000 -> rounds to nearest 1M -> 5_000_000.
        assert cfg.reading_base_cost(101_400_000.0) == pytest.approx(5_000_000.0)

    def test_reading_base_cost_no_rounding_when_rounding_is_one(self):
        cfg = self._cfg(cost_fraction=0.05, cost_rounding=1)
        assert cfg.reading_base_cost(101_400_000.0) == pytest.approx(5_070_000.0)

    def test_reading_cost_curve_is_cumulative_fibonacci_of_base(self):
        cfg = self._cfg(cost_fraction=0.05, cost_rounding=1_000_000)
        # base 5M scaled by the cumulative Fibonacci multipliers 1,2,4,7,12.
        assert cfg.reading_cost_curve(101_400_000.0) == pytest.approx(
            [5_000_000.0, 10_000_000.0, 20_000_000.0, 35_000_000.0, 60_000_000.0]
        )

    def test_reading_cost_curve_length_matches_action_space_max(self):
        cfg = self._cfg(action_space_max_readings=3)
        assert len(cfg.reading_cost_curve(100_000_000.0)) == 3

    def test_effective_readings_is_precision_times_base_sigma_squared(self):
        cfg = self._cfg(sigma_logit_base=1.5)
        # precision-weighted equivalent count at base sigma: 2.0 * 1.5**2 = 4.5.
        assert cfg.effective_readings(2.0) == pytest.approx(4.5)

    def test_effective_readings_zero_when_no_precision(self):
        cfg = self._cfg()
        assert cfg.effective_readings(0.0) == 0.0
