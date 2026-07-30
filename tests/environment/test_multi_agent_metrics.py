import uuid
from unittest.mock import MagicMock

import pytest

from pyxis_portfolio_challenge.environment.metrics import MetricsContext
from pyxis_portfolio_challenge.environment.multi_agent_metrics import (
    PerEpisodeBDDealsWon,
    PerEpisodeDrugReleases,
    PerEpisodeIndicationSpread,
    PerEpisodePhaseTransitionLeaks,
    PerEpisodeWinLoss,
    PerStepAgentRank,
    PerStepAlertCount,
    PerStepBDAssetAvailable,
    PerStepBDDealAlerts,
    PerStepContestedIndications,
    PerStepDrugReleaseAlerts,
    PerStepDrugsOnMarket,
    PerStepFirstMoverExclusivities,
    PerStepIndicationConcentration,
    PerStepIndicationDiversity,
    PerStepIndicationSpread,
    PerStepIndicationsWithExclusivity,
    PerStepMeanMarketShare,
    PerStepNonBankruptAgents,
    PerStepOnMarketPerIndication,
    PerStepPipelineLeakAlerts,
    PerStepRelativeEnpv,
    PerStepTotalOnMarketPerIndication,
)
from pyxis_portfolio_challenge.game.asset import AssetState
from pyxis_portfolio_challenge.game.shared_market_state import (
    Alert,
    AlertType,
    IndicationMarketState,
)


def _make_asset(ta="oncology", indication=0, state=AssetState.Idle):
    asset = MagicMock()
    asset.therapeutic_area = ta
    asset.indication = indication
    asset.state = state
    asset.id = uuid.uuid4()
    return asset


def _make_game_state(assets=None):
    gs = MagicMock()
    gs.id = uuid.uuid4()
    gs.assets = {a.id: a for a in (assets or [])}
    gs.bankrupt = False
    return gs


def _make_shared_market(
    indication_markets=None, time=5, alerts=None, current_bd_asset=None,
):
    sm = MagicMock()
    sm.indication_markets = indication_markets or {}
    sm.time = time
    sm.ta_markets = {}
    sm.alerts = alerts or []
    sm.current_bd_assets = [current_bd_asset] if current_bd_asset is not None else []
    return sm


def _make_indication_market(
    ta, indication, name, active_drugs=None,
    first_mover=None, excl_start=None, excl_duration=4,
):
    return IndicationMarketState(
        therapeutic_area=ta,
        indication=indication,
        indication_name=name,
        active_drugs=active_drugs or {},
        first_mover_agent=first_mover,
        first_mover_drug_id=uuid.uuid4() if first_mover else None,
        exclusivity_start_time=excl_start,
        exclusivity_duration=excl_duration,
    )


def _ctx(gs, sm=None, reward=0.0, agent_id=None, all_agent_states=None,
         all_agent_rewards=None):
    return MetricsContext(
        game_state=gs, reward=reward, shared_market_state=sm,
        agent_id=agent_id, all_agent_states=all_agent_states,
        all_agent_rewards=all_agent_rewards,
    )


def _key(gs):
    return f"game_state_id_{gs.id}"


# ── PerStepIndicationDiversity ──────────────────────────────────────────


class TestPerStepIndicationDiversity:
    def test_empty_portfolio(self):
        metric = PerStepIndicationDiversity()
        gs = _make_game_state([])
        ctx = _ctx(gs)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]

    def test_single_indication(self):
        metric = PerStepIndicationDiversity()
        assets = [
            _make_asset("oncology", 0),
            _make_asset("oncology", 0),
        ]
        gs = _make_game_state(assets)
        ctx = _ctx(gs)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [1]

    def test_multiple_indications(self):
        metric = PerStepIndicationDiversity()
        assets = [
            _make_asset("oncology", 0),
            _make_asset("oncology", 1),
            _make_asset("respiratory and immunology", 0),
            _make_asset("respiratory and immunology", 0),
        ]
        gs = _make_game_state(assets)
        ctx = _ctx(gs)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [3]

    def test_step_updates(self):
        metric = PerStepIndicationDiversity()
        assets = [_make_asset("oncology", 0)]
        gs = _make_game_state(assets)
        ctx = _ctx(gs)

        metric.on_episode_begin(ctx)

        # Add a new asset in a different indication
        new_asset = _make_asset("oncology", 1)
        gs.assets[new_asset.id] = new_asset
        metric.on_step_end(ctx)

        assert metric.history[_key(gs)] == [1, 2]


# ── PerStepIndicationConcentration ──────────────────────────────────────


class TestPerStepIndicationConcentration:
    def test_empty_portfolio(self):
        metric = PerStepIndicationConcentration()
        gs = _make_game_state([])
        ctx = _ctx(gs)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0.0]

    def test_single_indication_is_1(self):
        metric = PerStepIndicationConcentration()
        assets = [
            _make_asset("oncology", 0),
            _make_asset("oncology", 0),
            _make_asset("oncology", 0),
        ]
        gs = _make_game_state(assets)
        ctx = _ctx(gs)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [1.0]

    def test_even_split(self):
        metric = PerStepIndicationConcentration()
        assets = [
            _make_asset("oncology", 0),
            _make_asset("oncology", 1),
        ]
        gs = _make_game_state(assets)
        ctx = _ctx(gs)

        metric.on_episode_begin(ctx)
        # HHI = 0.5^2 + 0.5^2 = 0.5
        assert metric.history[_key(gs)] == [0.5]

    def test_uneven_split(self):
        metric = PerStepIndicationConcentration()
        assets = [
            _make_asset("oncology", 0),
            _make_asset("oncology", 0),
            _make_asset("oncology", 0),
            _make_asset("oncology", 1),
        ]
        gs = _make_game_state(assets)
        ctx = _ctx(gs)

        metric.on_episode_begin(ctx)
        # HHI = (3/4)^2 + (1/4)^2 = 0.5625 + 0.0625 = 0.625
        assert metric.history[_key(gs)] == [0.625]


# ── PerStepOnMarketPerIndication ────────────────────────────────────────


class TestPerStepOnMarketPerIndication:
    def test_no_on_market(self):
        metric = PerStepOnMarketPerIndication()
        assets = [
            _make_asset("oncology", 0, AssetState.Idle),
            _make_asset("oncology", 1, AssetState.InDevelopment),
        ]
        gs = _make_game_state(assets)
        ctx = _ctx(gs)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [{}]

    def test_on_market_counted(self):
        metric = PerStepOnMarketPerIndication()
        assets = [
            _make_asset("oncology", 0, AssetState.OnMarket),
            _make_asset("oncology", 0, AssetState.OnMarket),
            _make_asset("oncology", 1, AssetState.OnMarket),
            _make_asset("oncology", 1, AssetState.Idle),
        ]
        gs = _make_game_state(assets)
        ctx = _ctx(gs)

        metric.on_episode_begin(ctx)
        result = metric.history[_key(gs)][0]
        assert result == {"oncology:0": 2, "oncology:1": 1}

    def test_step_updates(self):
        metric = PerStepOnMarketPerIndication()
        assets = [_make_asset("oncology", 0, AssetState.OnMarket)]
        gs = _make_game_state(assets)
        ctx = _ctx(gs)

        metric.on_episode_begin(ctx)

        new = _make_asset("oncology", 1, AssetState.OnMarket)
        gs.assets[new.id] = new
        metric.on_step_end(ctx)

        assert len(metric.history[_key(gs)]) == 2
        assert metric.history[_key(gs)][1] == {
            "oncology:0": 1, "oncology:1": 1,
        }


# ── PerStepFirstMoverExclusivities ─────────────────────────────────────


class TestPerStepFirstMoverExclusivities:
    def test_no_shared_market(self):
        metric = PerStepFirstMoverExclusivities()
        gs = _make_game_state([])
        ctx = _ctx(gs, sm=None)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]

    def test_no_exclusivities(self):
        metric = PerStepFirstMoverExclusivities()
        ind_markets = {
            "oncology:0": _make_indication_market(
                "oncology", 0, "solid tumors",
            ),
        }
        gs = _make_game_state([])
        sm = _make_shared_market(ind_markets, time=5)
        ctx = _ctx(gs, sm=sm)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]

    def test_agent_has_exclusivity(self):
        metric = PerStepFirstMoverExclusivities()
        asset = _make_asset("oncology", 0, AssetState.OnMarket)
        gs = _make_game_state([asset])

        ind_markets = {
            "oncology:0": _make_indication_market(
                "oncology", 0, "solid tumors",
                active_drugs={"pharma_0": [asset.id]},
                first_mover="pharma_0",
                excl_start=3,
                excl_duration=4,
            ),
        }
        sm = _make_shared_market(ind_markets, time=5)
        ctx = _ctx(gs, sm=sm)

        metric.on_episode_begin(ctx)
        # excl_start=3, duration=4 → expires at 7. time=5 → active
        assert metric.history[_key(gs)] == [1]

    def test_exclusivity_expired(self):
        metric = PerStepFirstMoverExclusivities()
        asset = _make_asset("oncology", 0, AssetState.OnMarket)
        gs = _make_game_state([asset])

        ind_markets = {
            "oncology:0": _make_indication_market(
                "oncology", 0, "solid tumors",
                active_drugs={"pharma_0": [asset.id]},
                first_mover="pharma_0",
                excl_start=0,
                excl_duration=4,
            ),
        }
        sm = _make_shared_market(ind_markets, time=5)
        ctx = _ctx(gs, sm=sm)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]

    def test_other_agent_exclusivity_not_counted(self):
        metric = PerStepFirstMoverExclusivities()
        asset = _make_asset("oncology", 0, AssetState.OnMarket)
        gs = _make_game_state([asset])

        ind_markets = {
            "oncology:0": _make_indication_market(
                "oncology", 0, "solid tumors",
                active_drugs={
                    "pharma_0": [asset.id],
                    "pharma_1": [uuid.uuid4()],
                },
                first_mover="pharma_1",
                excl_start=3,
                excl_duration=4,
            ),
        }
        sm = _make_shared_market(ind_markets, time=5)
        ctx = _ctx(gs, sm=sm)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]


# ── PerStepContestedIndications ─────────────────────────────────────────


class TestPerStepContestedIndications:
    def test_no_shared_market(self):
        metric = PerStepContestedIndications()
        gs = _make_game_state([])
        ctx = _ctx(gs, sm=None)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]

    def test_no_contest(self):
        metric = PerStepContestedIndications()
        ind_markets = {
            "oncology:0": _make_indication_market(
                "oncology", 0, "solid tumors",
                active_drugs={"pharma_0": [uuid.uuid4()]},
            ),
            "oncology:1": _make_indication_market(
                "oncology", 1, "lung cancer",
                active_drugs={"pharma_1": [uuid.uuid4()]},
            ),
        }
        gs = _make_game_state([])
        sm = _make_shared_market(ind_markets)
        ctx = _ctx(gs, sm=sm)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]

    def test_one_contested(self):
        metric = PerStepContestedIndications()
        ind_markets = {
            "oncology:0": _make_indication_market(
                "oncology", 0, "solid tumors",
                active_drugs={
                    "pharma_0": [uuid.uuid4()],
                    "pharma_1": [uuid.uuid4()],
                },
            ),
            "oncology:1": _make_indication_market(
                "oncology", 1, "lung cancer",
                active_drugs={"pharma_0": [uuid.uuid4()]},
            ),
        }
        gs = _make_game_state([])
        sm = _make_shared_market(ind_markets)
        ctx = _ctx(gs, sm=sm)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [1]

    def test_empty_drug_lists_not_counted(self):
        metric = PerStepContestedIndications()
        ind_markets = {
            "oncology:0": _make_indication_market(
                "oncology", 0, "solid tumors",
                active_drugs={
                    "pharma_0": [uuid.uuid4()],
                    "pharma_1": [],
                },
            ),
        }
        gs = _make_game_state([])
        sm = _make_shared_market(ind_markets)
        ctx = _ctx(gs, sm=sm)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]


# ── PerStepTotalOnMarketPerIndication ───────────────────────────────────


class TestPerStepTotalOnMarketPerIndication:
    def test_no_shared_market(self):
        metric = PerStepTotalOnMarketPerIndication()
        gs = _make_game_state([])
        ctx = _ctx(gs, sm=None)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [{}]

    def test_counts_across_agents(self):
        metric = PerStepTotalOnMarketPerIndication()
        ind_markets = {
            "oncology:0": _make_indication_market(
                "oncology", 0, "solid tumors",
                active_drugs={
                    "pharma_0": [uuid.uuid4(), uuid.uuid4()],
                    "pharma_1": [uuid.uuid4()],
                },
            ),
            "oncology:1": _make_indication_market(
                "oncology", 1, "lung cancer",
                active_drugs={},
            ),
        }
        gs = _make_game_state([])
        sm = _make_shared_market(ind_markets)
        ctx = _ctx(gs, sm=sm)

        metric.on_episode_begin(ctx)
        result = metric.history[_key(gs)][0]
        assert result == {"oncology:0": 3}

    def test_step_updates(self):
        metric = PerStepTotalOnMarketPerIndication()
        ind_markets = {
            "oncology:0": _make_indication_market(
                "oncology", 0, "solid tumors",
                active_drugs={"pharma_0": [uuid.uuid4()]},
            ),
        }
        gs = _make_game_state([])
        sm = _make_shared_market(ind_markets)
        ctx = _ctx(gs, sm=sm)

        metric.on_episode_begin(ctx)

        # Add another drug
        ind_markets["oncology:0"].active_drugs["pharma_1"] = [uuid.uuid4()]
        metric.on_step_end(ctx)

        assert metric.history[_key(gs)] == [
            {"oncology:0": 1},
            {"oncology:0": 2},
        ]


# ── PerStepIndicationSpread ─────────────────────────────────────────────


class TestPerStepIndicationSpread:
    def test_no_shared_market(self):
        metric = PerStepIndicationSpread()
        gs = _make_game_state([_make_asset("oncology", 0)])
        ctx = _ctx(gs, sm=None)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0.0]

    def test_full_spread(self):
        metric = PerStepIndicationSpread()
        assets = [
            _make_asset("oncology", 0),
            _make_asset("oncology", 1),
        ]
        gs = _make_game_state(assets)

        ind_markets = {
            "oncology:0": _make_indication_market(
                "oncology", 0, "solid tumors",
            ),
            "oncology:1": _make_indication_market(
                "oncology", 1, "lung cancer",
            ),
        }
        sm = _make_shared_market(ind_markets)
        ctx = _ctx(gs, sm=sm)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [1.0]

    def test_partial_spread(self):
        metric = PerStepIndicationSpread()
        assets = [_make_asset("oncology", 0)]
        gs = _make_game_state(assets)

        ind_markets = {
            "oncology:0": _make_indication_market(
                "oncology", 0, "solid tumors",
            ),
            "oncology:1": _make_indication_market(
                "oncology", 1, "lung cancer",
            ),
            "respiratory and immunology:0": _make_indication_market(
                "respiratory and immunology", 0, "asthma",
            ),
            "respiratory and immunology:1": _make_indication_market(
                "respiratory and immunology", 1, "COPD",
            ),
        }
        sm = _make_shared_market(ind_markets)
        ctx = _ctx(gs, sm=sm)

        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0.25]


# ── PerEpisodeIndicationSpread ──────────────────────────────────────────


class TestPerEpisodeIndicationSpread:
    def test_episode_end_spread(self):
        metric = PerEpisodeIndicationSpread()
        assets = [
            _make_asset("oncology", 0),
            _make_asset("oncology", 1),
            _make_asset("respiratory and immunology", 0),
        ]
        gs = _make_game_state(assets)

        ind_markets = {
            "oncology:0": _make_indication_market(
                "oncology", 0, "solid tumors",
            ),
            "oncology:1": _make_indication_market(
                "oncology", 1, "lung cancer",
            ),
            "respiratory and immunology:0": _make_indication_market(
                "respiratory and immunology", 0, "asthma",
            ),
            "respiratory and immunology:1": _make_indication_market(
                "respiratory and immunology", 1, "COPD",
            ),
        }
        sm = _make_shared_market(ind_markets)
        ctx = _ctx(gs, sm=sm)

        metric.on_evaluation_begin(ctx)
        metric.on_episode_end(ctx)

        assert metric.history[_key(gs)] == 0.75

    def test_no_shared_market(self):
        metric = PerEpisodeIndicationSpread()
        gs = _make_game_state([_make_asset("oncology", 0)])
        ctx = _ctx(gs, sm=None)

        metric.on_evaluation_begin(ctx)
        metric.on_episode_end(ctx)

        assert metric.history[_key(gs)] == 0.0


# ── PerStepNonBankruptAgents ─────────────────────────────────────────────


class TestPerStepNonBankruptAgents:
    def test_no_all_agent_states(self):
        metric = PerStepNonBankruptAgents()
        gs = _make_game_state([])
        ctx = _ctx(gs)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]

    def test_all_alive(self):
        metric = PerStepNonBankruptAgents()
        gs0 = _make_game_state([])
        gs0.bankrupt = False
        gs1 = _make_game_state([])
        gs1.bankrupt = False
        all_states = {"pharma_0": gs0, "pharma_1": gs1}
        ctx = _ctx(gs0, agent_id="pharma_0", all_agent_states=all_states)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs0)] == [2]

    def test_one_bankrupt(self):
        metric = PerStepNonBankruptAgents()
        gs0 = _make_game_state([])
        gs0.bankrupt = False
        gs1 = _make_game_state([])
        gs1.bankrupt = True
        all_states = {"pharma_0": gs0, "pharma_1": gs1}
        ctx = _ctx(gs0, agent_id="pharma_0", all_agent_states=all_states)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs0)] == [1]


# ── PerStepAgentRank ────────────────────────────────────────────────────


class TestPerStepAgentRank:
    def test_no_context(self):
        metric = PerStepAgentRank()
        gs = _make_game_state([])
        ctx = _ctx(gs)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]

    def test_ranking(self):
        metric = PerStepAgentRank()
        gs0 = _make_game_state([])
        gs0.enpv.return_value = 100.0
        gs1 = _make_game_state([])
        gs1.enpv.return_value = 200.0
        all_states = {"pharma_0": gs0, "pharma_1": gs1}

        ctx = _ctx(gs0, agent_id="pharma_0", all_agent_states=all_states)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs0)] == [2]  # pharma_0 is rank 2

    def test_best_agent(self):
        metric = PerStepAgentRank()
        gs0 = _make_game_state([])
        gs0.enpv.return_value = 300.0
        gs1 = _make_game_state([])
        gs1.enpv.return_value = 100.0
        all_states = {"pharma_0": gs0, "pharma_1": gs1}

        ctx = _ctx(gs0, agent_id="pharma_0", all_agent_states=all_states)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs0)] == [1]


# ── PerStepRelativeEnpv ─────────────────────────────────────────────────


class TestPerStepRelativeEnpv:
    def test_no_context(self):
        metric = PerStepRelativeEnpv()
        gs = _make_game_state([])
        ctx = _ctx(gs)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0.0]

    def test_equal_share(self):
        metric = PerStepRelativeEnpv()
        gs0 = _make_game_state([])
        gs0.enpv.return_value = 100.0
        gs1 = _make_game_state([])
        gs1.enpv.return_value = 100.0
        all_states = {"pharma_0": gs0, "pharma_1": gs1}

        ctx = _ctx(gs0, agent_id="pharma_0", all_agent_states=all_states)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs0)] == [0.5]

    def test_dominant_agent(self):
        metric = PerStepRelativeEnpv()
        gs0 = _make_game_state([])
        gs0.enpv.return_value = 300.0
        gs1 = _make_game_state([])
        gs1.enpv.return_value = 100.0
        all_states = {"pharma_0": gs0, "pharma_1": gs1}

        ctx = _ctx(gs0, agent_id="pharma_0", all_agent_states=all_states)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs0)] == [0.75]


# ── PerStepBDAssetAvailable ──────────────────────────────────────────────────


class TestPerStepBDAssetAvailable:
    def test_no_shared_market(self):
        metric = PerStepBDAssetAvailable()
        gs = _make_game_state([])
        ctx = _ctx(gs)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]

    def test_asset_available(self):
        metric = PerStepBDAssetAvailable()
        gs = _make_game_state([])
        sm = _make_shared_market(current_bd_asset=MagicMock())
        ctx = _ctx(gs, sm=sm)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [1]

    def test_no_asset(self):
        metric = PerStepBDAssetAvailable()
        gs = _make_game_state([])
        sm = _make_shared_market(current_bd_asset=None)
        ctx = _ctx(gs, sm=sm)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]


# ── PerEpisodeDrugReleases ──────────────────────────────────────────────


class TestPerEpisodeDrugReleases:
    def test_no_releases(self):
        metric = PerEpisodeDrugReleases()
        gs0 = _make_game_state([_make_asset(state=AssetState.Idle)])
        gs1 = _make_game_state([_make_asset(state=AssetState.InDevelopment)])
        all_states = {"pharma_0": gs0, "pharma_1": gs1}
        ctx = _ctx(gs0, agent_id="pharma_0", all_agent_states=all_states)

        metric.on_evaluation_begin(ctx)
        metric.on_episode_begin(ctx)
        metric.on_step_end(ctx)
        metric.on_episode_end(ctx)
        assert metric.history[_key(gs0)] == 0

    def test_counts_across_agents(self):
        metric = PerEpisodeDrugReleases()
        # Start: both agents have idle assets
        a0 = _make_asset(state=AssetState.Idle)
        a1 = _make_asset(state=AssetState.Idle)
        gs0_begin = _make_game_state([a0])
        gs1_begin = _make_game_state([a1])
        all_begin = {"pharma_0": gs0_begin, "pharma_1": gs1_begin}
        ctx_begin = _ctx(gs0_begin, agent_id="pharma_0", all_agent_states=all_begin)

        metric.on_evaluation_begin(ctx_begin)
        metric.on_episode_begin(ctx_begin)

        # Step: both agents' drugs reach market
        a0_market = _make_asset(state=AssetState.OnMarket)
        a0_market.id = a0.id
        a1_market = _make_asset(state=AssetState.OnMarket)
        a1_market.id = a1.id
        gs0_step = _make_game_state([a0_market])
        gs1_step = _make_game_state([a1_market])
        all_step = {"pharma_0": gs0_step, "pharma_1": gs1_step}
        ctx_step = _ctx(gs0_step, agent_id="pharma_0", all_agent_states=all_step)

        metric.on_step_end(ctx_step)
        metric.on_episode_end(ctx_step)
        assert metric.history[_key(gs0_step)] == 2

    def test_no_double_count(self):
        metric = PerEpisodeDrugReleases()
        a = _make_asset(state=AssetState.OnMarket)
        gs = _make_game_state([a])
        all_states = {"pharma_0": gs}
        ctx = _ctx(gs, agent_id="pharma_0", all_agent_states=all_states)

        metric.on_evaluation_begin(ctx)
        metric.on_episode_begin(ctx)
        # Already OnMarket at episode begin, so no transition
        metric.on_step_end(ctx)
        metric.on_step_end(ctx)
        metric.on_episode_end(ctx)
        assert metric.history[_key(gs)] == 0

    def test_no_all_agent_states(self):
        metric = PerEpisodeDrugReleases()
        gs = _make_game_state([])
        ctx = _ctx(gs, agent_id="pharma_0", all_agent_states=None)

        metric.on_evaluation_begin(ctx)
        metric.on_episode_begin(ctx)
        metric.on_step_end(ctx)
        metric.on_episode_end(ctx)
        assert metric.history[_key(gs)] == 0


# ── PerStepDrugsOnMarket ────────────────────────────────────────────────


class TestPerStepDrugsOnMarket:
    def test_no_drugs_on_market(self):
        metric = PerStepDrugsOnMarket()
        gs = _make_game_state([_make_asset(state=AssetState.Idle)])
        all_states = {"pharma_0": gs}
        ctx = _ctx(gs, agent_id="pharma_0", all_agent_states=all_states)

        metric.on_evaluation_begin(ctx)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]

    def test_counts_across_agents(self):
        metric = PerStepDrugsOnMarket()
        gs0 = _make_game_state([
            _make_asset(state=AssetState.OnMarket),
            _make_asset(state=AssetState.Idle),
        ])
        gs1 = _make_game_state([
            _make_asset(state=AssetState.OnMarket),
            _make_asset(state=AssetState.OnMarket),
        ])
        all_states = {"pharma_0": gs0, "pharma_1": gs1}
        ctx = _ctx(gs0, agent_id="pharma_0", all_agent_states=all_states)

        metric.on_evaluation_begin(ctx)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs0)] == [3]

    def test_no_all_agent_states(self):
        metric = PerStepDrugsOnMarket()
        gs = _make_game_state([])
        ctx = _ctx(gs, agent_id="pharma_0", all_agent_states=None)

        metric.on_evaluation_begin(ctx)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]


# ── PerEpisodeBDDealsWon ────────────────────────────────────────────────


class TestPerEpisodeBDDealsWon:
    def test_no_deals(self):
        metric = PerEpisodeBDDealsWon()
        gs = _make_game_state([])
        sm = _make_shared_market(time=5)
        ctx = _ctx(gs, sm=sm, agent_id="pharma_0")

        metric.on_evaluation_begin(ctx)
        metric.on_episode_begin(ctx)
        metric.on_episode_end(ctx)
        assert metric.history[_key(gs)] == 0

    def test_counts_own_deals(self):
        metric = PerEpisodeBDDealsWon()
        gs = _make_game_state([])
        # Alerts created at step=5; sm.time=6 because advance_time()
        # has already run by the time on_step_end fires.
        alerts = [
            Alert(
                step=5, event_type=AlertType.BD_DEAL,
                agent_id="pharma_0", therapeutic_area="oncology",
            ),
            Alert(
                step=5, event_type=AlertType.BD_DEAL,
                agent_id="pharma_1", therapeutic_area="oncology",
            ),
        ]
        sm = _make_shared_market(time=6, alerts=alerts)
        ctx = _ctx(gs, sm=sm, agent_id="pharma_0")

        metric.on_evaluation_begin(ctx)
        metric.on_episode_begin(ctx)
        metric.on_step_end(ctx)
        metric.on_episode_end(ctx)
        assert metric.history[_key(gs)] == 1


# ── PerStepMeanMarketShare ──────────────────────────────────────────────


class TestPerStepMeanMarketShare:
    def test_no_context(self):
        metric = PerStepMeanMarketShare()
        gs = _make_game_state([])
        ctx = _ctx(gs)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0.0]

    def test_no_agent_states(self):
        metric = PerStepMeanMarketShare()
        gs = _make_game_state([])
        sm = _make_shared_market()
        ctx = _ctx(gs, sm=sm, agent_id="pharma_0")
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0.0]

    def test_delegates_to_per_drug_shares(self):
        """Verify metric uses calculate_agent_market_shares and averages."""
        metric = PerStepMeanMarketShare()
        gs = _make_game_state([])
        sm = _make_shared_market()
        drug1, drug2 = uuid.uuid4(), uuid.uuid4()
        mock_shares = {drug1: 0.6, drug2: 0.4}

        from unittest.mock import patch
        with patch(
            "pyxis_portfolio_challenge.environment.market_mechanics"
            ".calculate_agent_market_shares",
            return_value=mock_shares,
        ):
            ctx = _ctx(
                gs, sm=sm, agent_id="pharma_0",
                all_agent_states={"pharma_0": gs},
            )
            metric.on_episode_begin(ctx)
            assert abs(metric.history[_key(gs)][0] - 0.5) < 1e-9


# ── PerStepIndicationsWithExclusivity ───────────────────────────────────


class TestPerStepIndicationsWithExclusivity:
    def test_no_shared_market(self):
        metric = PerStepIndicationsWithExclusivity()
        gs = _make_game_state([])
        ctx = _ctx(gs)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]

    def test_counts_active_exclusivities(self):
        metric = PerStepIndicationsWithExclusivity()
        gs = _make_game_state([])
        ind_markets = {
            "oncology:0": _make_indication_market(
                "oncology", 0, "solid tumors",
                first_mover="pharma_0", excl_start=3, excl_duration=4,
            ),
            "oncology:1": _make_indication_market(
                "oncology", 1, "lung cancer",
                first_mover="pharma_1", excl_start=0, excl_duration=4,
            ),
        }
        sm = _make_shared_market(ind_markets, time=5)
        ctx = _ctx(gs, sm=sm)
        metric.on_episode_begin(ctx)
        # oncology:0 excl active (3+4=7 > 5), oncology:1 expired (0+4=4 < 5)
        assert metric.history[_key(gs)] == [1]


# ── Alert metrics ───────────────────────────────────────────────────────


class TestPerStepAlertCount:
    def test_no_shared_market(self):
        metric = PerStepAlertCount()
        gs = _make_game_state([])
        ctx = _ctx(gs)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [0]

    def test_counts_all(self):
        metric = PerStepAlertCount()
        gs = _make_game_state([])
        alerts = [
            Alert(
                step=1, event_type=AlertType.DRUG_RELEASE,
                agent_id="pharma_0", therapeutic_area="oncology",
            ),
            Alert(
                step=2, event_type=AlertType.BD_DEAL,
                agent_id="pharma_1", therapeutic_area="oncology",
            ),
            Alert(
                step=3, event_type=AlertType.PIPELINE_LEAK,
                agent_id="pharma_0", therapeutic_area="oncology",
            ),
        ]
        sm = _make_shared_market(alerts=alerts)
        ctx = _ctx(gs, sm=sm)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [3]


class TestPerStepDrugReleaseAlerts:
    def test_filters_type(self):
        metric = PerStepDrugReleaseAlerts()
        gs = _make_game_state([])
        alerts = [
            Alert(
                step=1, event_type=AlertType.DRUG_RELEASE,
                agent_id="pharma_0", therapeutic_area="oncology",
            ),
            Alert(
                step=2, event_type=AlertType.BD_DEAL,
                agent_id="pharma_1", therapeutic_area="oncology",
            ),
        ]
        sm = _make_shared_market(alerts=alerts)
        ctx = _ctx(gs, sm=sm)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [1]


class TestPerStepBDDealAlerts:
    def test_filters_type(self):
        metric = PerStepBDDealAlerts()
        gs = _make_game_state([])
        alerts = [
            Alert(
                step=1, event_type=AlertType.DRUG_RELEASE,
                agent_id="pharma_0", therapeutic_area="oncology",
            ),
            Alert(
                step=2, event_type=AlertType.BD_DEAL,
                agent_id="pharma_1", therapeutic_area="oncology",
            ),
            Alert(
                step=3, event_type=AlertType.BD_DEAL,
                agent_id="pharma_0", therapeutic_area="oncology",
            ),
        ]
        sm = _make_shared_market(alerts=alerts)
        ctx = _ctx(gs, sm=sm)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [2]


class TestPerStepPipelineLeakAlerts:
    def test_filters_type(self):
        metric = PerStepPipelineLeakAlerts()
        gs = _make_game_state([])
        alerts = [
            Alert(
                step=1, event_type=AlertType.PIPELINE_LEAK,
                agent_id="pharma_0", therapeutic_area="oncology",
            ),
            Alert(
                step=2, event_type=AlertType.BD_DEAL,
                agent_id="pharma_1", therapeutic_area="oncology",
            ),
        ]
        sm = _make_shared_market(alerts=alerts)
        ctx = _ctx(gs, sm=sm)
        metric.on_episode_begin(ctx)
        assert metric.history[_key(gs)] == [1]


# ── PerEpisodeWinLoss ──────────────────────────────────────────────────


class TestPerEpisodeWinLoss:
    def test_win(self):
        metric = PerEpisodeWinLoss()
        gs = _make_game_state([])
        gs_opp = _make_game_state([])
        rewards = {"pharma_0": 150.0, "pharma_1": 100.0}
        ctx = _ctx(
            gs, agent_id="pharma_0",
            all_agent_rewards=rewards,
            all_agent_states={"pharma_0": gs, "pharma_1": gs_opp},
        )
        metric.on_evaluation_begin(ctx)
        metric.on_episode_end(ctx)
        assert metric.history[_key(gs)] == 1.0

    def test_loss(self):
        metric = PerEpisodeWinLoss()
        gs = _make_game_state([])
        gs_opp = _make_game_state([])
        rewards = {"pharma_0": 50.0, "pharma_1": 100.0}
        ctx = _ctx(
            gs, agent_id="pharma_0",
            all_agent_rewards=rewards,
            all_agent_states={"pharma_0": gs, "pharma_1": gs_opp},
        )
        metric.on_evaluation_begin(ctx)
        metric.on_episode_end(ctx)
        assert metric.history[_key(gs)] == 0.0

    def test_draw(self):
        metric = PerEpisodeWinLoss()
        gs = _make_game_state([])
        gs_opp = _make_game_state([])
        rewards = {"pharma_0": 100.0, "pharma_1": 100.0}
        ctx = _ctx(
            gs, agent_id="pharma_0",
            all_agent_rewards=rewards,
            all_agent_states={"pharma_0": gs, "pharma_1": gs_opp},
        )
        metric.on_evaluation_begin(ctx)
        metric.on_episode_end(ctx)
        assert metric.history[_key(gs)] == 0.5

    def test_no_agent_rewards(self):
        metric = PerEpisodeWinLoss()
        gs = _make_game_state([])
        ctx = _ctx(gs, agent_id="pharma_0")
        metric.on_evaluation_begin(ctx)
        metric.on_episode_end(ctx)
        assert metric.history == {}

    def test_multiple_episodes(self):
        metric = PerEpisodeWinLoss()
        gs1 = _make_game_state([])
        gs2 = _make_game_state([])
        gs3 = _make_game_state([])
        gs_opp = _make_game_state([])

        ctx_init = _ctx(gs1, agent_id="pharma_0")
        metric.on_evaluation_begin(ctx_init)

        # Episode 1: win
        ctx1 = _ctx(
            gs1, agent_id="pharma_0",
            all_agent_rewards={"pharma_0": 200.0, "pharma_1": 100.0},
            all_agent_states={"pharma_0": gs1, "pharma_1": gs_opp},
        )
        metric.on_episode_end(ctx1)

        # Episode 2: loss
        ctx2 = _ctx(
            gs2, agent_id="pharma_0",
            all_agent_rewards={"pharma_0": 50.0, "pharma_1": 100.0},
            all_agent_states={"pharma_0": gs2, "pharma_1": gs_opp},
        )
        metric.on_episode_end(ctx2)

        # Episode 3: draw
        ctx3 = _ctx(
            gs3, agent_id="pharma_0",
            all_agent_rewards={"pharma_0": 100.0, "pharma_1": 100.0},
            all_agent_states={"pharma_0": gs3, "pharma_1": gs_opp},
        )
        metric.on_episode_end(ctx3)

        assert metric.history[_key(gs1)] == 1.0
        assert metric.history[_key(gs2)] == 0.0
        assert metric.history[_key(gs3)] == 0.5

    def test_negative_rewards(self):
        metric = PerEpisodeWinLoss()
        gs = _make_game_state([])
        gs_opp = _make_game_state([])
        rewards = {"pharma_0": -50.0, "pharma_1": -100.0}
        ctx = _ctx(
            gs, agent_id="pharma_0",
            all_agent_rewards=rewards,
            all_agent_states={"pharma_0": gs, "pharma_1": gs_opp},
        )
        metric.on_evaluation_begin(ctx)
        metric.on_episode_end(ctx)
        assert metric.history[_key(gs)] == 1.0


# ── Lifecycle: evaluation_begin clears history ──────────────────────────

ALL_METRIC_CLASSES = [
    PerStepIndicationDiversity,
    PerStepIndicationConcentration,
    PerStepOnMarketPerIndication,
    PerStepFirstMoverExclusivities,
    PerStepContestedIndications,
    PerStepTotalOnMarketPerIndication,
    PerStepIndicationSpread,
    PerEpisodeIndicationSpread,
    PerStepNonBankruptAgents,
    PerStepAgentRank,
    PerStepRelativeEnpv,
    PerStepBDAssetAvailable,
    PerEpisodeDrugReleases,
    PerStepDrugsOnMarket,
    PerEpisodeBDDealsWon,
    PerEpisodeWinLoss,
    PerEpisodePhaseTransitionLeaks,
    PerStepMeanMarketShare,
    PerStepIndicationsWithExclusivity,
    PerStepAlertCount,
    PerStepDrugReleaseAlerts,
    PerStepBDDealAlerts,
    PerStepPipelineLeakAlerts,
]


@pytest.mark.parametrize("metric_cls", ALL_METRIC_CLASSES)
def test_evaluation_begin_clears_history(metric_cls):
    metric = metric_cls()
    metric.history["stale_key"] = "stale_value"
    metric.on_evaluation_begin(context=None)
    assert metric.history == {}


# ── Merge works ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("metric_cls", ALL_METRIC_CLASSES)
def test_merge_works(metric_cls):
    m1 = metric_cls()
    m2 = metric_cls()
    m1.history["ep1"] = "data1"
    m2.history["ep2"] = "data2"
    m1.merge(m2)
    assert m1.history == {"ep1": "data1", "ep2": "data2"}
