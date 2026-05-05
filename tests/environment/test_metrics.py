import uuid
from unittest.mock import MagicMock, PropertyMock

import pytest

from aiml_pyxis_investment_game.environment.metrics import (
    MergeHistoryMixin,
    MetricsContext,
    PerEpisodeCumulativeReward,
    PerEpisodeFinalEnpv,
    PerEpisodeFinalEroi,
    PerEpisodeMetric,
    PerEpisodeNumSteps,
    PerEpisodeRealisedRoi,
    PerEvaluationBankruptcyRate,
    PerEvaluationCumulativeReward,
    PerEvaluationMetric,
    PerStepCash,
    PerStepCost,
    PerStepCumulativeNetCashFlow,
    PerStepCumulativeReward,
    PerStepEnpv,
    PerStepEroi,
    PerStepFractionOfPossibleInvestments,
    PerStepFractionOfPossibleInvestmentsPosEnpv,
    PerStepMetric,
    PerStepNetCashFlow,
    PerStepNumAssetsExpiredState,
    PerStepNumAssetsFailedState,
    PerStepNumAssetsIdleState,
    PerStepNumAssetsInDevelopmentState,
    PerStepNumAssetsOnMarketState,
    PerStepRevenue,
    PerStepReward,
    collect_metrics,
    merge_all_metrics,
    report_all_metrics,
)
from aiml_pyxis_investment_game.game.asset import AssetState


@pytest.fixture
def mock_game_state():
    mock_game_state = MagicMock()
    mock_game_state.id = uuid.uuid4()
    mock_game_state.reinvestment_percentage = 1.0
    return mock_game_state


def test_per_episode_cumulative_reward(mock_game_state):
    """Test per-episode cumulative reward."""
    metric = PerEpisodeCumulativeReward()
    ctx = MetricsContext(game_state=mock_game_state, reward=1.0)

    metric.on_evaluation_begin(context=ctx)
    metric.on_step_end(context=ctx)
    metric.on_step_end(context=ctx)

    report = metric.report()
    episode_key = f"episode_id_{mock_game_state.id}"
    assert report["PerEpisodeCumulativeReward"][episode_key][
               "cumulative"] == 2.0
    assert report["PerEpisodeCumulativeReward"][episode_key]["mean"] == 1.0
    assert report["PerEpisodeCumulativeReward"][episode_key]["stdev"] == 0.0

    assert metric.report() == {
        "PerEpisodeCumulativeReward":
            {f"episode_id_{mock_game_state.id}": {
                "cumulative": 2.0,
            "mean": 1.0,
            "stdev": 0.0}}}

def test_per_step_reward(mock_game_state):
    """Test per-step reward."""
    metric = PerStepReward()
    ctx = MetricsContext(game_state=mock_game_state, reward=1.0)

    metric.on_episode_begin(context=ctx)
    metric.on_step_end(context=ctx)
    metric.on_step_end(context=ctx)

    assert metric.report() == {
        "PerStepReward": {f"episode_id_{mock_game_state.id}": [0.0, 1.0, 1.0]}
    }


def test_per_evaluation_cumulative_reward(mock_game_state):
    """Test per-evaluation cumulative reward."""
    metric = PerEvaluationCumulativeReward()
    ctx = MetricsContext(game_state=mock_game_state, reward=10.0)

    metric.on_evaluation_begin(context=ctx)
    metric.on_episode_begin(context=ctx)
    metric.on_step_end(context=ctx)
    metric.on_step_end(context=ctx)  # Episode 1 total reward = 20

    # New episode
    mock_game_state_2 = MagicMock()
    mock_game_state_2.id = uuid.uuid4()
    ctx2 = MetricsContext(game_state=mock_game_state_2, reward=30.0)
    metric.on_episode_begin(context=ctx2)
    metric.on_step_end(context=ctx2)  # Episode 2 total reward = 30

    report = metric.report()["PerEvaluationCumulativeReward"]
    assert report["mean"] == 25.0
    assert report["stdev"] == 7.0710678118654755
    assert report["min"] == 20.0
    assert report["max"] == 30.0
    assert report["median"] == 25.0


def test_per_evaluation_bankruptcy_rate(mock_game_state):
    """Test per-evaluation bankruptcy rate."""
    metric = PerEvaluationBankruptcyRate()

    # Episode 1: Not bankrupt
    type(mock_game_state).game_ended = PropertyMock(return_value=True)
    type(mock_game_state).bankrupt = PropertyMock(return_value=False)
    ctx = MetricsContext(game_state=mock_game_state, reward=0)

    metric.on_evaluation_begin(context=ctx)
    metric.on_episode_begin(context=ctx)
    metric.on_episode_end(context=ctx)

    # Episode 2: Bankrupt
    mock_game_state_2 = MagicMock()
    mock_game_state_2.id = uuid.uuid4()
    type(mock_game_state_2).game_ended = PropertyMock(return_value=True)
    type(mock_game_state_2).bankrupt = PropertyMock(return_value=True)
    ctx2 = MetricsContext(game_state=mock_game_state_2, reward=0)
    metric.on_episode_begin(context=ctx2)
    metric.on_episode_end(context=ctx2)

    report = metric.report()["PerEvaluationBankruptcyRate"]
    assert report["bankruptcy_rate"] == 0.5


def test_per_episode_final_enpv(mock_game_state):
    """Test per-episode final eNPV metric."""
    metric = PerEpisodeFinalEnpv()
    mock_game_state.enpv_over_time = [100, 150, 120]
    ctx = MetricsContext(game_state=mock_game_state, reward=0)

    metric.on_episode_begin(context=ctx)
    metric.on_episode_end(context=ctx)

    report = metric.report()["PerEpisodeFinalEnpv"]
    assert report[f"episode_id_{mock_game_state.id}"] == 120


def test_per_episode_final_eroi(mock_game_state):
    """Test per-episode final eROI metric."""
    metric = PerEpisodeFinalEroi()
    mock_game_state.eroi_over_time = [1.5, 2.0, 1.8]
    ctx = MetricsContext(game_state=mock_game_state, reward=0)

    metric.on_episode_begin(context=ctx)
    metric.on_episode_end(context=ctx)

    report = metric.report()["PerEpisodeFinalEroi"]
    assert report[f"episode_id_{mock_game_state.id}"] == 1.8


def test_per_episode_num_steps(mock_game_state):
    """Test per-episode number of steps metric."""
    metric = PerEpisodeNumSteps()
    type(mock_game_state).time = PropertyMock(return_value=50)
    ctx = MetricsContext(game_state=mock_game_state, reward=0)

    metric.on_episode_begin(context=ctx)
    metric.on_episode_end(context=ctx)

    report = metric.report()["PerEpisodeNumSteps"]
    assert report[f"episode_id_{mock_game_state.id}"] == 50


def test_per_episode_realised_roi(mock_game_state):
    """Test per-episode realised ROI metric."""
    metric = PerEpisodeRealisedRoi()
    mock_game_state.realised_roi.return_value = 1.2
    ctx = MetricsContext(game_state=mock_game_state, reward=0)

    metric.on_episode_begin(context=ctx)
    metric.on_episode_end(context=ctx)

    report = metric.report()["PerEpisodeRealisedRoi"]
    assert report[f"episode_id_{mock_game_state.id}"] == 1.2


def test_per_step_cumulative_reward(mock_game_state):
    """Test per-step cumulative reward."""
    metric = PerStepCumulativeReward()

    metric.on_episode_begin(MetricsContext(mock_game_state, 0))
    metric.on_step_end(MetricsContext(mock_game_state, 10))
    metric.on_step_end(MetricsContext(mock_game_state, 5))
    metric.on_step_end(MetricsContext(mock_game_state, -3))

    report = metric.report()["PerStepCumulativeReward"]
    assert report[f"episode_id_{mock_game_state.id}"] == [0.0, 10.0, 15.0,
                                                          12.0]


def test_per_step_enpv(mock_game_state):
    """Test per-step eNPV metric."""
    metric = PerStepEnpv()
    mock_game_state.running_enpv = [100, 110, 105]
    ctx = MetricsContext(mock_game_state, 0)

    metric.on_episode_begin(ctx)
    metric.on_episode_end(ctx)

    report = metric.report()["PerStepEnpv"]
    assert report[f"episode_id_{mock_game_state.id}"] == [100, 110, 105]


def test_per_step_eroi(mock_game_state):
    """Test per-step eROI metric."""
    metric = PerStepEroi()
    mock_game_state.running_eroi = [1.2, 1.5, 1.4]
    ctx = MetricsContext(mock_game_state, 0)

    metric.on_episode_begin(ctx)
    metric.on_episode_end(ctx)

    report = metric.report()["PerStepEroi"]
    assert report[f"episode_id_{mock_game_state.id}"] == [1.2, 1.5, 1.4]


def test_per_step_cash(mock_game_state):
    """Test per-step cash metric."""
    mock_game_state.cash = 1000.
    metric = PerStepCash()

    ctx = MetricsContext(mock_game_state, 0)
    metric.on_episode_begin(ctx)
    mock_game_state.cash = 1200.
    metric.on_step_end(ctx)
    mock_game_state.cash = 1100.
    metric.on_step_end(ctx)
    mock_game_state.cash = 1300.
    metric.on_step_end(ctx)

    report = metric.report()["PerStepCash"]
    assert report[f"episode_id_{mock_game_state.id}"] == [1000.0, 1200.0, 1100.0, 1300.0]


def test_per_step_revenue(mock_game_state):
    """Test per-step revenue metric."""
    metric = PerStepRevenue()
    mock_game_state.realised_revenues = [100, 150, 200]
    ctx = MetricsContext(mock_game_state, 0)

    metric.on_episode_begin(ctx)
    metric.on_episode_end(ctx)

    report = metric.report()["PerStepRevenue"]
    assert report[f"episode_id_{mock_game_state.id}"] == [100, 150, 200]


def test_per_step_cost(mock_game_state):
    """Test per-step cost metric."""
    metric = PerStepCost()
    mock_game_state.realised_costs = [80, 130, 90]
    ctx = MetricsContext(mock_game_state, 0)

    metric.on_episode_begin(ctx)
    metric.on_episode_end(ctx)

    report = metric.report()["PerStepCost"]
    assert report[f"episode_id_{mock_game_state.id}"] == [80, 130, 90]


def test_per_step_net_cash_flow(mock_game_state):
    """Test per-step net cash flow metric."""
    metric = PerStepNetCashFlow()
    mock_game_state.realised_revenues = [100, 120, 150]
    mock_game_state.realised_costs = [80, 130, 100]
    ctx = MetricsContext(mock_game_state, 0)

    metric.on_episode_begin(ctx)
    metric.on_episode_end(ctx)

    report = metric.report()["PerStepNetCashFlow"]
    assert report[f"episode_id_{mock_game_state.id}"] == [20, -10, 50]


def test_per_step_cumulative_net_cash_flow(mock_game_state):
    """Test per-step cumulative net cash flow metric."""
    metric = PerStepCumulativeNetCashFlow()
    mock_game_state.realised_revenues = [100, 120, 150]
    mock_game_state.realised_costs = [80, 130, 100]
    ctx = MetricsContext(mock_game_state, 0)

    metric.on_episode_begin(ctx)
    metric.on_episode_end(ctx)

    report = metric.report()["PerStepCumulativeNetCashFlow"]
    assert report[f"episode_id_{mock_game_state.id}"] == [20, 10, 60]


@pytest.fixture
def mock_assets():
    assets = {
        uuid.uuid4(): MagicMock(state=AssetState.Idle),
        uuid.uuid4(): MagicMock(state=AssetState.InDevelopment),
        uuid.uuid4(): MagicMock(state=AssetState.OnMarket),
    }
    return assets


@pytest.fixture
def mock_expired_assets():
    assets = {
        uuid.uuid4(): MagicMock(state=AssetState.Expired),
        uuid.uuid4(): MagicMock(state=AssetState.Expired),
    }
    return assets


def test_per_step_num_assets_idle_state(mock_game_state, mock_assets):
    """Test per-step number of assets in idle state metric."""
    metric = PerStepNumAssetsIdleState()

    mock_game_state.assets = mock_assets
    ctx = MetricsContext(mock_game_state, 0)

    metric.on_episode_begin(ctx)
    mock_game_state.assets.update(
        {
            uuid.uuid4(): MagicMock(state=AssetState.Idle),
            uuid.uuid4(): MagicMock(state=AssetState.OnMarket),
            uuid.uuid4(): MagicMock(state=AssetState.Idle),
        }
    )
    metric.on_step_end(ctx)

    report = metric.report()["PerStepNumAssetsIdleState"]
    assert report[f"episode_id_{mock_game_state.id}"] == [1, 3]


def test_per_step_num_assets_in_development_state(
        mock_game_state, mock_assets):
    """Test per-step number of assets in development state metric."""
    metric = PerStepNumAssetsInDevelopmentState()

    mock_game_state.assets = mock_assets
    ctx = MetricsContext(mock_game_state, 0)

    metric.on_episode_begin(ctx)
    mock_game_state.assets.update(
        {
            uuid.uuid4(): MagicMock(state=AssetState.InDevelopment),
            uuid.uuid4(): MagicMock(state=AssetState.Failed),
            uuid.uuid4(): MagicMock(state=AssetState.InDevelopment),
            uuid.uuid4(): MagicMock(state=AssetState.InDevelopment),
        }
    )
    metric.on_step_end(ctx)

    report = metric.report()["PerStepNumAssetsInDevelopmentState"]
    assert report[f"episode_id_{mock_game_state.id}"] == [1, 4]


def test_per_step_num_assets_on_market_state(
        mock_game_state, mock_assets):
    """Test per-step number of assets on market state metric."""
    metric = PerStepNumAssetsOnMarketState()

    mock_game_state.assets = mock_assets
    ctx = MetricsContext(mock_game_state, 0)

    metric.on_episode_begin(ctx)
    mock_game_state.assets.update(
        {
            uuid.uuid4(): MagicMock(state=AssetState.OnMarket),
            uuid.uuid4(): MagicMock(state=AssetState.Idle),
        }
    )
    metric.on_step_end(ctx)

    report = metric.report()["PerStepNumAssetsOnMarketState"]
    assert report[f"episode_id_{mock_game_state.id}"] == [1, 2]


def test_per_step_num_assets_failed_state(
        mock_game_state, mock_assets):
    """Test per-step number of assets failed state metric."""
    metric = PerStepNumAssetsFailedState()

    mock_game_state.failed_assets = {
        uuid.uuid4(): MagicMock(state=AssetState.Failed),
    }
    ctx = MetricsContext(mock_game_state, 0)

    metric.on_episode_begin(ctx)
    mock_game_state.failed_assets.update(
        {
            uuid.uuid4(): MagicMock(state=AssetState.Failed),
            uuid.uuid4(): MagicMock(state=AssetState.Failed),
        }
    )
    metric.on_step_end(ctx)

    report = metric.report()["PerStepNumAssetsFailedState"]
    assert report[f"episode_id_{mock_game_state.id}"] == [1, 3]


def test_per_step_num_assets_expired_state(
        mock_game_state, mock_expired_assets
):
    """Test per-step number of assets expired state metric."""
    metric = PerStepNumAssetsExpiredState()

    mock_game_state.expired_assets = mock_expired_assets
    ctx = MetricsContext(mock_game_state, 0)

    metric.on_episode_begin(ctx)
    mock_game_state.expired_assets.update(
        {
            uuid.uuid4(): MagicMock(state=AssetState.Expired),
        }
    )
    metric.on_step_end(ctx)

    report = metric.report()["PerStepNumAssetsExpiredState"]
    assert report[f"episode_id_{mock_game_state.id}"] == [2, 3]


def test_per_step_fraction_of_possible_investments(mock_game_state):
    """Test per-step fraction of possible investments metric."""
    metric = PerStepFractionOfPossibleInvestments()
    asset_to_invest_id = uuid.uuid4()
    mock_game_state.assets = {
        uuid.uuid4(): MagicMock(state=AssetState.InDevelopment),
        asset_to_invest_id: MagicMock(state=AssetState.Idle),
        uuid.uuid4(): MagicMock(state=AssetState.Idle),
        uuid.uuid4(): MagicMock(state=AssetState.OnMarket),
    }
    idle_asset_ids = [
        asset_id for asset_id, asset in mock_game_state.assets.items()
        if asset.state == AssetState.Idle
    ]
    ctx = MetricsContext(mock_game_state, 0, investment_decisions={asset_to_invest_id: "invest"})

    metric.on_episode_begin(ctx)
    metric.on_step_begin(ctx)

    report = metric.report()["PerStepFractionOfPossibleInvestments"]
    assert report[f"episode_id_{mock_game_state.id}"] == [0.5]


def test_per_step_fraction_of_possible_investments_pos_enpv(
        mock_game_state):
    """Test per-step fraction of possible investments with positive eNPV metric."""
    # metric uses asset.enpv() need to create correct mocks
    metric = PerStepFractionOfPossibleInvestmentsPosEnpv()
    asset_to_invest_id = uuid.uuid4()
    asset_with_pos_enpv_id = uuid.uuid4()
    asset_with_neg_enpv_id = uuid.uuid4()

    mock_game_state.assets = {
        uuid.uuid4(): MagicMock(state=AssetState.InDevelopment),
        asset_to_invest_id: MagicMock(state=AssetState.Idle, enpv=150.0),
        asset_with_pos_enpv_id: MagicMock(state=AssetState.Idle, enpv=200.0),
        asset_with_neg_enpv_id: MagicMock(state=AssetState.Idle, enpv=-50.0),
        uuid.uuid4(): MagicMock(state=AssetState.OnMarket),
    }
    ctx = MetricsContext(
        mock_game_state, 0,
        investment_decisions={asset_to_invest_id: "invest"}
    )

    metric.on_episode_begin(ctx)
    metric.on_step_begin(ctx)

    report = metric.report()["PerStepFractionOfPossibleInvestmentsPosEnpv"]
    assert report[f"episode_id_{mock_game_state.id}"] == [0.5]


@pytest.fixture
def mock_per_evaluation_metric():
    metric = MagicMock(spec=PerEvaluationMetric)
    metric.report = MagicMock(return_value={"MockPerEvaluationMetric": 1.0})
    return metric


@pytest.fixture
def mock_per_episode_metric():
    metric = MagicMock(spec=PerEpisodeMetric)
    metric.report = MagicMock(
        return_value={"MockPerEpisodeMetric": {"ep1": 1.0, "ep2": 2.0}})
    return metric


@pytest.fixture
def mock_per_step_metric():
    metric = MagicMock(spec=PerStepMetric)
    metric.report = MagicMock(
        return_value={
            "MockPerStepMetric": {"ep1": [1.0, 1.0], "ep2": [2.0, 2.0]}}
    )
    return metric


def test_report_all_metrics_produces_correct_result(
        mock_per_evaluation_metric, mock_per_episode_metric,
        mock_per_step_metric
):
    """Test report all metrics produces correct result."""
    metrics = [
        mock_per_evaluation_metric,
        mock_per_episode_metric,
        mock_per_step_metric,
    ]
    report = report_all_metrics(metrics=metrics)
    assert report == [
        {"PerEvaluationMetrics": [{"MockPerEvaluationMetric": 1.0}]},
        {"PerEpisodeMetrics": [
            {"MockPerEpisodeMetric": {"ep1": 1.0, "ep2": 2.0}}]},
        {
            "PerStepMetrics": [
                {"MockPerStepMetric": {"ep1": [1.0, 1.0], "ep2": [2.0, 2.0]}}
            ]
        },
    ]


def test_collect_metrics_calls_all_metrics():
    """Test that collect_metrics calls the specified function on all metrics."""
    metrics_list = [MagicMock(), MagicMock(), MagicMock()]
    ctx = MagicMock()
    fn_to_call = "on_step_end"

    # Mock the method we expect to be called and set _warmup_mode to False
    for metric in metrics_list:
        setattr(metric, fn_to_call, MagicMock())
        metric._warmup_mode = False  # Ensure warmup mode is off

    collect_metrics(collection_fn=fn_to_call, metrics=metrics_list,
                    context=ctx)

    for metric in metrics_list:
        getattr(metric, fn_to_call).assert_called_once_with(context=ctx)



class DummyMetric(MergeHistoryMixin):
    def __init__(self, history):
        self.history = history


def test_merge_history_mixin_basic_merge():
    m1 = DummyMetric({"ep1": 1.0})
    m2 = DummyMetric({"ep2": 2.0})

    m1.merge(m2)

    assert m1.history == {
        "ep1": 1.0,
        "ep2": 2.0,
    }
    # source must not be mutated
    assert m2.history == {"ep2": 2.0}


def test_merge_history_mixin_duplicate_key_raises():
    m1 = DummyMetric({"ep1": 1.0})
    m2 = DummyMetric({"ep1": 2.0})

    with pytest.raises(ValueError, match="Duplicate"):
        m1.merge(m2)


def test_merge_history_mixin_type_mismatch_raises():
    class OtherMetric(DummyMetric):
        pass

    m1 = DummyMetric({"ep1": 1.0})
    m2 = OtherMetric({"ep2": 2.0})

    with pytest.raises(TypeError):
        m1.merge(m2)


class DummyMetricA(MergeHistoryMixin):
    def __init__(self, history):
        self.history = history


class DummyMetricB(MergeHistoryMixin):
    def __init__(self, history):
        self.history = history


def test_merge_all_metrics_basic():
    # Worker 1 metrics
    worker1 = [
        DummyMetricA({"ep1": 1}),
        DummyMetricB({"ep1": 10}),
    ]

    # Worker 2 metrics
    worker2 = [
        DummyMetricA({"ep2": 2}),
        DummyMetricB({"ep2": 20}),
    ]

    merged = merge_all_metrics([worker1, worker2])

    assert len(merged) == 2

    assert merged[0].history == {
        "ep1": 1,
        "ep2": 2,
    }

    assert merged[1].history == {
        "ep1": 10,
        "ep2": 20,
    }


def test_merge_all_metrics_mismatched_order_raises():
    worker1 = [
        DummyMetricA({"ep1": 1}),
        DummyMetricB({"ep1": 10}),
    ]

    worker2 = [
        DummyMetricB({"ep2": 20}),  # wrong order!
        DummyMetricA({"ep2": 2}),
    ]

    with pytest.raises(TypeError):
        merge_all_metrics([worker1, worker2])
