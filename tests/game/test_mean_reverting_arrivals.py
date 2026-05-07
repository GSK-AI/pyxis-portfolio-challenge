"""Tests for mean-reverting asset arrival mechanism using Gaussian CDF."""
from __future__ import annotations

import random
from unittest.mock import MagicMock, patch

import pytest
from scipy.stats import norm

from pyxis_portfolio_challenge.config import CapacityConfig
from pyxis_portfolio_challenge.game.asset_generators import JSONAssetGenerator
from pyxis_portfolio_challenge.game.game_state import GameState
from pyxis_portfolio_challenge.rng import init_game_rng

_DISABLED_RD_CAPACITY = CapacityConfig(
    enabled=False,
    base_capacity=80.0,
    overage_max_penalty=0.5,
    overage_cost_max_penalty=0.5,
    overage_scaling="linear",
)


@pytest.fixture
def mock_asset_generator():
    """Create a mock asset generator."""
    generator = MagicMock(spec=JSONAssetGenerator)
    # Mock the generator to return assets with predictable UUIDs
    def mock_generate(n, asset_type):
        from uuid import UUID
        return {UUID(int=i): MagicMock() for i in range(n)}
    generator.side_effect = mock_generate
    return generator


class TestBelowTargetProbabilities:
    """Test probability calculations when below target."""

    def test_deviation_1_sigma_1(self):
        """Test probability when 1 below target with sigma=1."""
        # deviation=1, sigma_below=1 → z=1 → p = 2*Φ(1)-1 ≈ 0.683
        z_score = 1 / 1.0
        expected_p = 2 * norm.cdf(z_score) - 1
        assert abs(expected_p - 0.683) < 0.01

    def test_deviation_2_sigma_1(self):
        """Test probability when 2 below target with sigma=1."""
        # deviation=2, sigma_below=1 → z=2 → p = 2*Φ(2)-1 ≈ 0.954
        z_score = 2 / 1.0
        expected_p = 2 * norm.cdf(z_score) - 1
        assert abs(expected_p - 0.954) < 0.01

    def test_deviation_3_sigma_1(self):
        """Test probability when 3 below target with sigma=1."""
        # deviation=3, sigma_below=1 → z=3 → p = 2*Φ(3)-1 ≈ 0.997
        z_score = 3 / 1.0
        expected_p = 2 * norm.cdf(z_score) - 1
        assert abs(expected_p - 0.997) < 0.01

    def test_deviation_2_sigma_2(self):
        """Test probability when 2 below target with sigma=2."""
        # deviation=2, sigma_below=2 → z=1 → p = 2*Φ(1)-1 ≈ 0.683
        z_score = 2 / 2.0
        expected_p = 2 * norm.cdf(z_score) - 1
        assert abs(expected_p - 0.683) < 0.01


class TestAboveTargetProbabilities:
    """Test probability calculations when at or above target."""

    def test_at_target_sigma_1(self):
        """Test probability at target with sigma=1."""
        # offset=0, sigma_above=1 → z=1 → p = 2*[1-Φ(1)] ≈ 0.317
        z_score = (0 + 1) / 1.0
        expected_p = 2 * (1 - norm.cdf(z_score))
        assert abs(expected_p - 0.317) < 0.01

    def test_one_above_sigma_1(self):
        """Test probability 1 above target with sigma=1."""
        # offset=1, sigma_above=1 → z=2 → p = 2*[1-Φ(2)] ≈ 0.046
        z_score = (1 + 1) / 1.0
        expected_p = 2 * (1 - norm.cdf(z_score))
        assert abs(expected_p - 0.046) < 0.01

    def test_at_target_sigma_3(self):
        """Test probability at target with sigma=3."""
        # offset=0, sigma_above=3 → z=1/3 → p = 2*[1-Φ(0.33)] ≈ 0.742
        z_score = (0 + 1) / 3.0
        expected_p = 2 * (1 - norm.cdf(z_score))
        assert abs(expected_p - 0.742) < 0.01

    def test_one_above_sigma_3(self):
        """Test probability 1 above target with sigma=3."""
        # offset=1, sigma_above=3 → z=2/3 → p = 2*[1-Φ(0.67)] ≈ 0.506
        z_score = (1 + 1) / 3.0
        expected_p = 2 * (1 - norm.cdf(z_score))
        assert abs(expected_p - 0.506) < 0.01


class TestRepeatedSamplingBehavior:
    """Test that repeated sampling works correctly."""

    def test_multiple_assets_added_when_far_below(self, valid_json_assets_path):
        """Test that multiple assets can be added when far below target."""
        # Create game state with target=5 but only 2 assets
        init_game_rng(42)
        game_state = GameState.initialise_new_game(
            asset_generator_cls=JSONAssetGenerator,
            num_assets=2,
            cash=10_000_000,
            horizon=20,
            max_num_assets=15,
            asset_arrival_sensitivity_below=1.0,  # Fast recovery
            asset_arrival_sensitivity_above=3.0,
            reinvestment_percentage=1.0,
            global_seed=42,
            assets_dir=valid_json_assets_path,
            indication_spread=1.5,
            indication_drift_speed=1.0,
            trial_cost_multiplier=1.0,
            rd_capacity_config=_DISABLED_RD_CAPACITY,
        )
        # Manually set target to 5 (num_assets=2 creates 2 assets)
        game_state.equilibrium_num_assets = 5

        # Mock RNG to always return success (low values)
        mock_rng = MagicMock(spec=random.Random)
        mock_rng.random.side_effect = [0.1, 0.1, 0.1, 0.9]  # First 3 succeed, 4th fails

        initial_assets = {k: v for k, v in game_state.assets.items()}

        # Call the method
        with patch("pyxis_portfolio_challenge.game.game_state.get_game_rng", return_value=mock_rng):
            result = game_state._add_new_assets_mean_reverting(initial_assets)

        # Should have added 3 assets (stopped on 4th draw)
        assert len(result) == 5  # 2 initial + 3 new

    def test_stops_at_max_assets(self, valid_json_assets_path):
        """Test that loop stops when reaching max_num_assets."""
        init_game_rng(42)
        game_state = GameState.initialise_new_game(
            asset_generator_cls=JSONAssetGenerator,
            num_assets=3,
            cash=10_000_000,
            horizon=20,
            max_num_assets=5,
            asset_arrival_sensitivity_below=0.5,  # Very fast recovery
            asset_arrival_sensitivity_above=3.0,
            reinvestment_percentage=1.0,
            global_seed=42,
            assets_dir=valid_json_assets_path,
            indication_spread=1.5,
            indication_drift_speed=1.0,
            trial_cost_multiplier=1.0,
            rd_capacity_config=_DISABLED_RD_CAPACITY,
        )
        game_state.equilibrium_num_assets = 10  # Target above max

        # Mock RNG to always succeed
        mock_rng = MagicMock(spec=random.Random)
        mock_rng.random.return_value = 0.01  # Always succeed

        initial_assets = {k: v for k, v in game_state.assets.items()}
        with patch("pyxis_portfolio_challenge.game.game_state.get_game_rng", return_value=mock_rng):
            result = game_state._add_new_assets_mean_reverting(initial_assets)

        # Should stop at max_num_assets
        assert len(result) == 5

    def test_stops_on_first_failed_draw(self, valid_json_assets_path):
        """Test that loop stops on first failed random draw."""
        init_game_rng(42)
        game_state = GameState.initialise_new_game(
            asset_generator_cls=JSONAssetGenerator,
            num_assets=3,
            cash=10_000_000,
            horizon=20,
            max_num_assets=15,
            asset_arrival_sensitivity_below=1.5,
            asset_arrival_sensitivity_above=3.0,
            reinvestment_percentage=1.0,
            global_seed=42,
            assets_dir=valid_json_assets_path,
            indication_spread=1.5,
            indication_drift_speed=1.0,
            trial_cost_multiplier=1.0,
            rd_capacity_config=_DISABLED_RD_CAPACITY,
        )
        game_state.equilibrium_num_assets = 5

        # Mock RNG to fail immediately
        mock_rng = MagicMock(spec=random.Random)
        mock_rng.random.return_value = 0.99  # Always fail

        initial_assets = {k: v for k, v in game_state.assets.items()}
        with patch("pyxis_portfolio_challenge.game.game_state.get_game_rng", return_value=mock_rng):
            result = game_state._add_new_assets_mean_reverting(initial_assets)

        # Should not add any assets
        assert len(result) == 3


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_portfolio_rapid_recovery(self, valid_json_assets_path):
        """Test that empty portfolio recovers quickly."""
        init_game_rng(42)
        game_state = GameState.initialise_new_game(
            asset_generator_cls=JSONAssetGenerator,
            num_assets=1,
            cash=10_000_000,
            horizon=20,
            max_num_assets=15,
            asset_arrival_sensitivity_below=1.5,
            asset_arrival_sensitivity_above=3.0,
            reinvestment_percentage=1.0,
            global_seed=42,
            assets_dir=valid_json_assets_path,
            indication_spread=1.5,
            indication_drift_speed=1.0,
            trial_cost_multiplier=1.0,
            rd_capacity_config=_DISABLED_RD_CAPACITY,
        )
        game_state.equilibrium_num_assets = 5

        # Start with empty portfolio
        empty_portfolio = {}

        # Mock RNG to succeed multiple times
        mock_rng = MagicMock(spec=random.Random)
        # High probabilities when far below target should lead to many successes
        mock_rng.random.side_effect = [0.1, 0.1, 0.1, 0.1, 0.1, 0.9]

        with patch("pyxis_portfolio_challenge.game.game_state.get_game_rng", return_value=mock_rng):
            result = game_state._add_new_assets_mean_reverting(empty_portfolio)

        # Should have added multiple assets
        assert len(result) >= 3

    def test_at_max_capacity_no_overflow(self, valid_json_assets_path):
        """Test that being at max capacity prevents any additions."""
        init_game_rng(42)
        game_state = GameState.initialise_new_game(
            asset_generator_cls=JSONAssetGenerator,
            num_assets=5,
            cash=10_000_000,
            horizon=20,
            max_num_assets=5,
            asset_arrival_sensitivity_below=1.5,
            asset_arrival_sensitivity_above=3.0,
            reinvestment_percentage=1.0,
            global_seed=42,
            assets_dir=valid_json_assets_path,
            indication_spread=1.5,
            indication_drift_speed=1.0,
            trial_cost_multiplier=1.0,
            rd_capacity_config=_DISABLED_RD_CAPACITY,
        )

        # Mock RNG to always succeed (shouldn't matter)
        mock_rng = MagicMock(spec=random.Random)
        mock_rng.random.return_value = 0.01

        initial_assets = {k: v for k, v in game_state.assets.items()}
        with patch("pyxis_portfolio_challenge.game.game_state.get_game_rng", return_value=mock_rng):
            result = game_state._add_new_assets_mean_reverting(initial_assets)

        # Should not add any assets
        assert len(result) == 5


class TestSensitivityParameters:
    """Test different sensitivity values."""

    def test_lower_sigma_faster_recovery(self):
        """Test that lower sigma gives higher probabilities (faster recovery)."""
        deviation = 2

        # sigma = 0.5
        z_low = deviation / 0.5
        p_low = 2 * norm.cdf(z_low) - 1

        # sigma = 2.0
        z_high = deviation / 2.0
        p_high = 2 * norm.cdf(z_high) - 1

        # Lower sigma should give higher probability
        assert p_low > p_high
        assert p_low > 0.95  # Very high probability
        assert p_high < 0.75  # Moderate probability

    def test_higher_sigma_above_more_fluctuation(self):
        """Test that higher sigma_above allows more upside fluctuation."""
        offset = 0  # At target

        # sigma_above = 1.0 (tight)
        z_low = (offset + 1) / 1.0
        p_low = 2 * (1 - norm.cdf(z_low))

        # sigma_above = 5.0 (wide)
        z_high = (offset + 1) / 5.0
        p_high = 2 * (1 - norm.cdf(z_high))

        # Higher sigma_above should give higher probability (MORE fluctuation)
        assert p_high > p_low
        assert p_low < 0.35  # Low probability with tight sigma
        assert p_high > 0.84  # High probability with wide sigma
