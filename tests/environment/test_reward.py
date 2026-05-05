import uuid
from unittest.mock import MagicMock, patch

from aiml_pyxis_investment_game.environment.reward import (
    CompositeReward,
    DeltaEnpvActionBasedReward,
    DeltaENPVReward,
    ENPVExcludeOnMarketReward,
    ENPVReward,
    HorizonReachedBonus,
    LegacyStaticNPVReward,
    NegativeCashPenalty,
    NetCashFlowReward,
    PassTrialPhaseBonus,
    Reward,
    SubtractCash,
    SymLogNetCashFlowReward,
    TASpecializationBonus,
)
from aiml_pyxis_investment_game.game.asset import AssetState
from aiml_pyxis_investment_game.game.game_state import GameEndReason


def test_composite_reward():
    mock_reward_1 = MagicMock(spec=Reward)
    mock_reward_2 = MagicMock(spec=Reward)

    mock_reward_1.compute.return_value = 5.0
    mock_reward_2.compute.return_value = 10.0

    composite_reward = CompositeReward(components=[mock_reward_1, mock_reward_2])

    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    total_reward = composite_reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )

    assert total_reward == 15.0
    mock_reward_1.compute.assert_called_once_with(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
        investment_decisions=None,
    )
    mock_reward_2.compute.assert_called_once_with(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
        investment_decisions=None,
    )


def test_legacy_static_npv_reward():
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    with patch(
        "aiml_pyxis_investment_game.environment.reward.legacy_static_npv"
    ) as mock_legacy_static_npv:
        reward = LegacyStaticNPVReward()
        _ = reward.compute(
            pre_step_game_state=pre_step_game_state,
            post_step_game_state=post_step_game_state,
        )

        assert mock_legacy_static_npv.call_count == 2


def test_npv_reward():
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()
    post_step_game_state.enpv.return_value = 42.0

    reward = ENPVReward()
    npv_reward = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )

    assert npv_reward == 42.0
    post_step_game_state.enpv.assert_called_once()


def test_npv_exclude_on_market_reward():
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    def mock_asset_on_market():
        mock_asset_on_market = MagicMock()
        mock_asset_on_market.state = AssetState.OnMarket
        mock_asset_on_market.enpv = 10.0
        return mock_asset_on_market

    post_step_game_state.enpv.return_value = 42.0
    post_step_game_state.assets = {
        uuid.uuid4(): mock_asset_on_market(),
    }

    reward = ENPVExcludeOnMarketReward()
    npv_reward = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )

    assert npv_reward == 32.0


def test_horizon_reached_bonus():
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    reward = HorizonReachedBonus(bonus_amount=100.0)

    # Test when horizon is not reached
    post_step_game_state.time = 5
    post_step_game_state.horizon = 10
    bonus = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )
    assert bonus == 0.0

    # Test when horizon is reached
    post_step_game_state.game_ended = True
    post_step_game_state.ended_reason = GameEndReason.HORIZON_REACHED
    bonus = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )
    assert bonus == 100.0


def test_subtract_cash():
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()
    post_step_game_state.cash = 75.0

    reward = SubtractCash()
    cash_penalty = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )

    assert cash_penalty == -75.0


def test_negative_cash_penalty():
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    reward = NegativeCashPenalty(penalty_amount=-1000.0)

    # Test when cash is non-negative
    post_step_game_state.cash = 50.0
    penalty = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )
    assert penalty == 0.0

    # Test when cash is negative
    post_step_game_state.cash = -20.0
    penalty = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )
    assert penalty == -1000.0


def test_net_cash_flow_reward():
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()
    pre_step_game_state.cash = 1_000_000.0
    post_step_game_state.cash = 1_500_000.0

    reward = NetCashFlowReward()
    net_cash_flow = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )

    assert net_cash_flow == 500_000.0


def test_symlog_net_cash_flow_reward_positive():
    """Test SymLogNetCashFlowReward compresses large positive cash flows."""
    pre = MagicMock()
    post = MagicMock()
    pre.cash = 0.0
    post.cash = 10_000_000_000.0  # 10B

    reward = SymLogNetCashFlowReward()
    result = reward.compute(pre_step_game_state=pre, post_step_game_state=post)

    import math

    expected = math.log1p(10_000_000_000.0)
    assert result == expected
    assert 23.0 < result < 24.0  # ~23.03


def test_symlog_net_cash_flow_reward_negative():
    """Test SymLogNetCashFlowReward compresses large negative cash flows."""
    pre = MagicMock()
    post = MagicMock()
    pre.cash = 10_000_000_000.0
    post.cash = 0.0  # lost 10B

    reward = SymLogNetCashFlowReward()
    result = reward.compute(pre_step_game_state=pre, post_step_game_state=post)

    import math

    expected = -math.log1p(10_000_000_000.0)
    assert result == expected
    assert result < 0


def test_symlog_net_cash_flow_reward_zero():
    """Test SymLogNetCashFlowReward returns 0 for no change."""
    pre = MagicMock()
    post = MagicMock()
    pre.cash = 5_000_000.0
    post.cash = 5_000_000.0

    reward = SymLogNetCashFlowReward()
    result = reward.compute(pre_step_game_state=pre, post_step_game_state=post)

    assert result == 0.0


def test_symlog_net_cash_flow_reward_compresses_range():
    """Test that symlog compresses a wide range into a narrow one."""
    reward = SymLogNetCashFlowReward()

    results = []
    for cash_flow in [10e9, 20e9, 30e9]:
        pre = MagicMock()
        post = MagicMock()
        pre.cash = 0.0
        post.cash = cash_flow
        results.append(
            reward.compute(pre_step_game_state=pre, post_step_game_state=post)
        )

    # 10B-30B range (20B spread) compresses to ~1.1 spread
    assert results[2] - results[0] < 2.0
    # All values in a tight band
    assert all(22.0 < r < 25.0 for r in results)


def test_symlog_net_cash_flow_reward_weight():
    """Test SymLogNetCashFlowReward respects weight parameter."""
    pre = MagicMock()
    post = MagicMock()
    pre.cash = 0.0
    post.cash = 1_000_000.0

    reward_w1 = SymLogNetCashFlowReward(weight=1.0)
    reward_w2 = SymLogNetCashFlowReward(weight=2.0)

    r1 = reward_w1.compute(pre_step_game_state=pre, post_step_game_state=post)
    r2 = reward_w2.compute(pre_step_game_state=pre, post_step_game_state=post)

    assert abs(r2 - 2.0 * r1) < 1e-10


def test_delta_enpv_reward():
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()
    pre_step_game_state.enpv.return_value = 100.0
    post_step_game_state.enpv.return_value = 150.0

    reward = DeltaENPVReward()
    delta_enpv = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )

    assert delta_enpv == 50.0


def test_pass_trial_phase_bonus():
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    reward = PassTrialPhaseBonus(bonus_amount=200.0)

    asset_id = uuid.uuid4()
    # Test when trial phase is not passed
    pre_step_game_state.assets = {
        asset_id: MagicMock(state=AssetState.InDevelopment),
    }
    post_step_game_state.assets = {
        asset_id: MagicMock(state=AssetState.InDevelopment),
    }
    bonus = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )
    assert bonus == 0.0

    # Test when trial phase is passed
    asset_id = uuid.uuid4()
    pre_step_game_state.assets = {
        asset_id: MagicMock(state=AssetState.InDevelopment),
    }
    post_step_game_state.assets = {
        asset_id: MagicMock(state=AssetState.Idle),
    }
    bonus = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )
    assert bonus == 200.0

    # Test when trial phase is passed to OnMarket
    asset_id = uuid.uuid4()
    pre_step_game_state.assets = {
        asset_id: MagicMock(state=AssetState.InDevelopment),
    }
    post_step_game_state.assets = {
        asset_id: MagicMock(state=AssetState.OnMarket),
    }
    bonus = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )
    assert bonus == 200.0


def test_pass_trial_phase_bonus_multiple_assets():
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    reward = PassTrialPhaseBonus(bonus_amount=150.0)

    asset_id_1 = uuid.uuid4()
    asset_id_2 = uuid.uuid4()
    asset_id_3 = uuid.uuid4()

    pre_step_game_state.assets = {
        asset_id_1: MagicMock(state=AssetState.InDevelopment),
        asset_id_2: MagicMock(state=AssetState.InDevelopment),
        asset_id_3: MagicMock(state=AssetState.Idle),
    }
    post_step_game_state.assets = {
        asset_id_1: MagicMock(state=AssetState.Idle),  # Passed trial
        asset_id_2: MagicMock(state=AssetState.OnMarket),  # Passed trial
        asset_id_3: MagicMock(state=AssetState.OnMarket),  # Did not pass trial
    }

    bonus = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )
    assert bonus == 300.0  # 2 assets passed trial phase


def test_delta_enpv_action_based_reward_no_investment_decisions():
    """Test DeltaEnpvActionBasedReward with no investment decisions."""
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    reward = DeltaEnpvActionBasedReward()
    delta_enpv = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
        investment_decisions=None,
    )

    assert delta_enpv == 0.0


def test_delta_enpv_action_based_reward_empty_investment_decisions():
    """Test DeltaEnpvActionBasedReward with empty investment decisions."""
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    reward = DeltaEnpvActionBasedReward()
    delta_enpv = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
        investment_decisions={},
    )

    assert delta_enpv == 0.0


def test_delta_enpv_action_based_reward_single_investment():
    """Test DeltaEnpvActionBasedReward with a single investment."""
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    asset_id = uuid.uuid4()

    # Create mock assets with enpv values
    pre_asset = MagicMock()
    pre_asset.enpv = 100.0
    post_asset = MagicMock()
    post_asset.enpv = 150.0

    pre_step_game_state.assets = {asset_id: pre_asset}
    post_step_game_state.assets = {asset_id: post_asset}

    investment_decisions = {asset_id: "invest"}

    reward = DeltaEnpvActionBasedReward()
    delta_enpv = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
        investment_decisions=investment_decisions,
    )

    assert delta_enpv == 50.0  # 150.0 - 100.0


def test_delta_enpv_action_based_reward_multiple_investments():
    """Test DeltaEnpvActionBasedReward with multiple investments."""
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    asset_id_1 = uuid.uuid4()
    asset_id_2 = uuid.uuid4()
    asset_id_3 = uuid.uuid4()

    # Create mock assets with enpv values
    pre_asset_1 = MagicMock()
    pre_asset_1.enpv = 100.0
    post_asset_1 = MagicMock()
    post_asset_1.enpv = 120.0

    pre_asset_2 = MagicMock()
    pre_asset_2.enpv = 200.0
    post_asset_2 = MagicMock()
    post_asset_2.enpv = 250.0

    pre_asset_3 = MagicMock()
    pre_asset_3.enpv = 300.0
    post_asset_3 = MagicMock()
    post_asset_3.enpv = 280.0  # This one decreased

    pre_step_game_state.assets = {
        asset_id_1: pre_asset_1,
        asset_id_2: pre_asset_2,
        asset_id_3: pre_asset_3,
    }
    post_step_game_state.assets = {
        asset_id_1: post_asset_1,
        asset_id_2: post_asset_2,
        asset_id_3: post_asset_3,
    }

    # Only invest in assets 1 and 3
    investment_decisions = {
        asset_id_1: "invest",
        asset_id_3: "invest",
    }

    reward = DeltaEnpvActionBasedReward()
    delta_enpv = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
        investment_decisions=investment_decisions,
    )

    # (120 - 100) + (280 - 300) = 20 + (-20) = 0
    assert delta_enpv == 0.0


def test_delta_enpv_action_based_reward_negative_delta():
    """Test DeltaEnpvActionBasedReward with negative eNPV change."""
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    asset_id = uuid.uuid4()

    # Create mock assets where eNPV decreases
    pre_asset = MagicMock()
    pre_asset.enpv = 200.0
    post_asset = MagicMock()
    post_asset.enpv = 150.0

    pre_step_game_state.assets = {asset_id: pre_asset}
    post_step_game_state.assets = {asset_id: post_asset}

    investment_decisions = {asset_id: "invest"}

    reward = DeltaEnpvActionBasedReward()
    delta_enpv = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
        investment_decisions=investment_decisions,
    )

    assert delta_enpv == -50.0  # 150.0 - 200.0


def test_delta_enpv_action_based_reward_asset_not_in_post_state():
    """Test DeltaEnpvActionBasedReward when asset is not in post state."""
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    asset_id = uuid.uuid4()

    # Asset exists in pre but not in post (e.g., expired)
    pre_asset = MagicMock()
    pre_asset.enpv = 100.0

    pre_step_game_state.assets = {asset_id: pre_asset}
    post_step_game_state.assets = {}

    investment_decisions = {asset_id: "invest"}

    reward = DeltaEnpvActionBasedReward()
    delta_enpv = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
        investment_decisions=investment_decisions,
    )

    # Asset not found in post state, so it doesn't contribute
    assert delta_enpv == 0.0


def test_ta_specialization_bonus_no_experience():
    """Test TASpecializationBonus with no TA experience."""
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()
    post_step_game_state.ta_experience = {}

    reward = TASpecializationBonus(bonus_scale=1e7)
    bonus = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )

    assert bonus == 0.0


def test_ta_specialization_bonus_even_spread():
    """Test TASpecializationBonus with evenly spread experience."""
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    # Equal experience across 3 TAs
    post_step_game_state.ta_experience = {
        "oncology": 10.0,
        "respiratory and immunology": 10.0,
        "vaccines and infectious disease": 10.0,
    }

    reward = TASpecializationBonus(bonus_scale=1e7)
    bonus = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )

    # Concentration = 10/30 = 0.333, baseline = 0.333, so bonus = 0
    assert bonus == 0.0


def test_ta_specialization_bonus_full_specialization():
    """Test TASpecializationBonus with complete specialization in one TA."""
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    # All experience in one TA
    post_step_game_state.ta_experience = {
        "oncology": 30.0,
        "respiratory and immunology": 0.0,
        "vaccines and infectious disease": 0.0,
    }

    reward = TASpecializationBonus(bonus_scale=1e7)
    bonus = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )

    # Concentration = 30/30 = 1.0, baseline = 0.333, score = 0.667
    # Bonus = 0.667 * 1e7 = 6.67e6
    expected = (1.0 - 1.0 / 3.0) * 1e7
    assert abs(bonus - expected) < 1e-6


def test_ta_specialization_bonus_partial_specialization():
    """Test TASpecializationBonus with partial specialization."""
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    # More experience in oncology than others
    post_step_game_state.ta_experience = {
        "oncology": 20.0,
        "respiratory and immunology": 5.0,
        "vaccines and infectious disease": 5.0,
    }

    reward = TASpecializationBonus(bonus_scale=1e7)
    bonus = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )

    # Concentration = 20/30 = 0.667, baseline = 0.333, score = 0.333
    # Bonus = 0.333 * 1e7 = 3.33e6
    expected = (20.0 / 30.0 - 1.0 / 3.0) * 1e7
    assert abs(bonus - expected) < 1e-6


def test_ta_specialization_bonus_custom_scale():
    """Test TASpecializationBonus with custom bonus scale."""
    pre_step_game_state = MagicMock()
    post_step_game_state = MagicMock()

    post_step_game_state.ta_experience = {
        "oncology": 30.0,
        "respiratory and immunology": 0.0,
        "vaccines and infectious disease": 0.0,
    }

    # Use a different scale
    reward = TASpecializationBonus(bonus_scale=5e6)
    bonus = reward.compute(
        pre_step_game_state=pre_step_game_state,
        post_step_game_state=post_step_game_state,
    )

    expected = (1.0 - 1.0 / 3.0) * 5e6
    assert abs(bonus - expected) < 1e-6
