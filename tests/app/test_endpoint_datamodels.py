import pytest

from app.endpoint_datamodels import (
    GameStateResponse,
    asset_to_response,
    game_state_to_response,
    indication_market_to_response,
)
from pyxis_portfolio_challenge.config import MarketingConfig, PtrsReadingsConfig
from pyxis_portfolio_challenge.game.asset import AssetState
from pyxis_portfolio_challenge.game.shared_market_state import IndicationMarketState
from pyxis_portfolio_challenge.game.trial import TrialPhase, TrialState
from tests.game.test_asset import drug_asset_factory


def _marketing_cfg(**overrides):
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


def _ptrs_cfg(**overrides):
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


def test_drug_asset_to_response():
    asset = drug_asset_factory()


    # handle pending trial phase logic
    if asset.trial.phase == TrialPhase.PHASE_3 and asset.trial.state == TrialState.PHASE_SUCCESS and asset.state == AssetState.OnMarket:
        pending_trial_phase = None
    elif asset.trial.state == TrialState.PHASE_FAILED:
        pending_trial_phase = None
    else:
        pending_trial_phase = asset.trial.phase.value

    response = asset_to_response(
        asset,
        reinvestment_percentage=0.35,
        drop_action_enabled=False,
        ptrs_cfg=None,
    )

    # Check key fields match
    assert response["id"] == asset.id
    assert response["name"] == asset.name
    assert response["therapeutic_area"] == asset.therapeutic_area
    assert response["type"] == asset.type
    assert response["description"] == asset.description
    assert response["max_revenue"] == asset.max_revenue
    assert response["time_until_max_revenue"] == asset.time_until_max_revenue
    assert response["time_until_patent_expiry"] == asset.time_until_patent_expiry
    assert response["state"] == asset.state
    assert response["pending_trial_phase"] == pending_trial_phase
    assert response["time_on_market"] == asset.time_on_market
    assert response["cost_this_step"] == asset.cost_this_step
    assert response["revenue_this_step"] == asset.revenue_this_step
    assert response["enpv"] == asset.enpv
    assert response["cash_enpv"] == asset.cash_enpv(0.35)
    assert response["expected_costs"] == asset.expected_costs_and_revenues[0]
    assert response["expected_revenues"] == asset.expected_costs_and_revenues[1]
    assert response["eroi"] == asset.eroi


def test_asset_to_response_drop_available_when_enabled():
    """Idle/In-Development assets expose the 'drop' action when the feature is on."""
    idle = drug_asset_factory(state=AssetState.Idle)
    in_dev = drug_asset_factory(state=AssetState.InDevelopment)

    idle_on = asset_to_response(
        idle,
        reinvestment_percentage=1.0,
        drop_action_enabled=True,
        ptrs_cfg=None,
    )
    in_dev_on = asset_to_response(
        in_dev,
        reinvestment_percentage=1.0,
        drop_action_enabled=True,
        ptrs_cfg=None,
    )
    idle_off = asset_to_response(
        idle,
        reinvestment_percentage=1.0,
        drop_action_enabled=False,
        ptrs_cfg=None,
    )

    assert "drop" in idle_on["available_actions"]
    assert "drop" in in_dev_on["available_actions"]
    assert "drop" not in idle_off["available_actions"]


def test_ptrs_reading_costs_match_config_curve_for_live_asset():
    """A readable (live) drug carries the config's cost curve for its trial."""
    cfg = _ptrs_cfg()
    asset = drug_asset_factory(state=AssetState.InDevelopment)

    response = asset_to_response(
        asset,
        reinvestment_percentage=0.35,
        drop_action_enabled=False,
        ptrs_cfg=cfg,
    )

    assert response["ptrs_reading_costs"] == pytest.approx(
        cfg.reading_cost_curve(asset.trial.cost_remaining)
    )


def test_ptrs_reading_costs_empty_when_feature_off():
    """No cost curve is offered when the readings feature is disabled."""
    asset = drug_asset_factory(state=AssetState.InDevelopment)

    response = asset_to_response(
        asset,
        reinvestment_percentage=0.35,
        drop_action_enabled=False,
        ptrs_cfg=None,
    )

    assert response["ptrs_reading_costs"] == []


def test_trial_effective_readings_matches_config_for_pending_phase():
    """
    The pending trial exposes sample count and the effective-readings signal.

    effective_readings must equal the shared config helper applied to the trial's
    accumulated precision — the same quantity the observation exposes — so the
    panel's confidence figure matches what the agents see.
    """
    cfg = _ptrs_cfg(sigma_logit_base=1.5)
    asset = drug_asset_factory(state=AssetState.InDevelopment)
    # Simulate diligence already banked on this trial (2 readings, precision 2.0).
    asset.trial._ptrs_sample_count = 2
    asset.trial._ptrs_total_precision = 2.0

    response = asset_to_response(
        asset,
        reinvestment_percentage=0.35,
        drop_action_enabled=False,
        ptrs_cfg=cfg,
    )

    pending = response["trials"][asset.trial.phase.value]
    assert pending.ptrs_sample_count == 2
    assert pending.ptrs_effective_readings == pytest.approx(
        cfg.effective_readings(2.0)
    )


def test_bd_asset_readings_prefer_clone_over_shared():
    """
    A bidder's private clone drives the PTRS / readings shown, not the shared asset.

    Diligence is private: when this player has a clone with banked readings, its
    reading-adjusted PTRS and effective-readings surface, while the cost curve is
    still anchored to the shared asset's cost_remaining (what the engine charges).
    """
    from app.endpoint_datamodels import bd_asset_to_response

    cfg = _ptrs_cfg()
    shared = drug_asset_factory(state=AssetState.InDevelopment)
    clone = shared.model_copy(deep=True)
    # The clone carries this player's private diligence; the shared asset does not.
    clone.trial._ptrs_sample_count = 3
    clone.trial._ptrs_total_precision = 3.0
    clone.trial.ptrs = 0.42

    resp = bd_asset_to_response(
        shared,
        indication_name_map=None,
        reinvestment_percentage=0.10,
        ptrs_cfg=cfg,
        clone=clone,
    )

    assert resp.ptrs == pytest.approx(0.42)
    assert resp.ptrs_sample_count == 3
    assert resp.ptrs_effective_readings == pytest.approx(cfg.effective_readings(3.0))
    assert resp.ptrs_reading_costs == pytest.approx(
        cfg.reading_cost_curve(shared.trial.cost_remaining)
    )


def test_bd_asset_readings_fall_back_to_shared_without_clone():
    """With no clone (no diligence yet) the untouched shared asset is used."""
    from app.endpoint_datamodels import bd_asset_to_response

    cfg = _ptrs_cfg()
    shared = drug_asset_factory(state=AssetState.InDevelopment)

    resp = bd_asset_to_response(
        shared,
        indication_name_map=None,
        reinvestment_percentage=0.10,
        ptrs_cfg=cfg,
        clone=None,
    )

    assert resp.ptrs == pytest.approx(shared.trial.ptrs)
    assert resp.ptrs_sample_count == shared.trial.ptrs_sample_count


def test_ptrs_readings_enabled_flag_round_trips(
    game_state_factory_fixed_list_asset_gen,
):
    """The readings feature flag must survive through GameStateResponse."""
    game_state = game_state_factory_fixed_list_asset_gen()
    game_state._ptrs_readings_config = _ptrs_cfg()

    response = GameStateResponse(**game_state_to_response(game_state))

    assert response.ptrs_readings_enabled is True


def test_game_state_to_response(game_state_factory_fixed_list_asset_gen):
    game_state = game_state_factory_fixed_list_asset_gen()

    response = game_state_to_response(game_state)

    # Check key fields match
    assert response["id"] == game_state.id
    assert response["cash"] == game_state.cash
    assert response["time"] == game_state.time
    assert response["horizon"] == game_state.horizon
    assert response["equilibrium_num_assets"] == game_state.equilibrium_num_assets
    assert response["max_num_assets"] == game_state.max_num_assets
    assert response["asset_arrival_sensitivity_below"] == game_state.asset_arrival_sensitivity_below
    assert response["asset_arrival_sensitivity_above"] == game_state.asset_arrival_sensitivity_above
    assert response["reinvestment_percentage"] == game_state.reinvestment_percentage
    assert response["initial_cash"] == game_state.initial_cash
    assert len(response["assets"]) == len(game_state.assets)
    assert len(response["expired_assets"]) == len(game_state.expired_assets)
    assert response["realised_costs"] == game_state.realised_costs
    assert response["realised_revenues"] == game_state.realised_revenues
    assert response["game_ended"] == game_state.game_ended
    assert response["ended_reason"] == game_state.ended_reason
    assert response["capital_over_time"] == game_state.capital_over_time
    assert response["enpv_over_time"] == game_state.enpv_over_time
    assert response["eroi_over_time"] == game_state.eroi_over_time
    assert response["ta_experience"] == dict(game_state.ta_experience)
    # Feature flags should be present
    assert "investment_levels_enabled" in response
    assert "interim_observations_enabled" in response
    assert "distributional_ptrs_enabled" in response


def test_game_state_response_model_preserves_player_state_fields(
    game_state_factory_fixed_list_asset_gen,
):
    """
    Fields must survive serialization through GameStateResponse.

    game_state_to_response emits a rich dict, but the live endpoints return it
    through response_model=GameStateResponse, which silently drops any field the
    model does not declare. The frontend schema requires these, so a missing
    declaration breaks live single- and multi-agent play (parse failure).
    """
    game_state = game_state_factory_fixed_list_asset_gen()

    response = GameStateResponse(**game_state_to_response(game_state))

    # dropped_assets + reinvestment_percentage + clinical-sites block must all
    # round-trip through the response model, not just the intermediate dict.
    assert response.dropped_assets == {}
    assert response.reinvestment_percentage == game_state.reinvestment_percentage
    assert response.clinical_sites_enabled == game_state.clinical_sites_enabled
    assert response.operational_sites == game_state.operational_sites
    assert response.sites_in_development == game_state.sites_in_development
    assert response.free_sites == game_state.free_sites
    assert response.sites_occupied == game_state.sites_occupied
    assert response.next_site_purchase_cost == game_state.next_site_purchase_cost()


def test_brand_equity_fields_survive_response_model(
    game_state_factory_fixed_list_asset_gen,
):
    """
    Brand-equity fields must round-trip through DrugAssetResponse.

    game_state_to_response attaches brand_score / brand_score_floor / be_cost
    onto each asset dict, but the live endpoints validate that dict through the
    response model, which silently drops any field DrugAssetResponse does not
    declare. When the model lacked these fields, a spent brand score never
    reached the frontend and the Brand Equity panel showed 0 forever even as the
    engine accumulated the score. Assert they survive on a *live* asset through
    the model, not just the intermediate dict.
    """
    game_state = game_state_factory_fixed_list_asset_gen()
    game_state._marketing_config = _marketing_cfg()
    asset_id, asset = next(iter(game_state.assets.items()))
    # Engine has banked a brand score for this drug across prior steps.
    game_state._brand_scores[asset_id] = 0.42

    response = GameStateResponse(**game_state_to_response(game_state))

    resp_asset = response.assets[asset_id]
    assert resp_asset.brand_score == pytest.approx(0.42)
    assert resp_asset.be_cost == pytest.approx(0.03 * asset.max_revenue)


def test_brand_score_projection_survives_response_model(
    game_state_factory_fixed_list_asset_gen,
):
    """
    Forward-looking brand projections must round-trip and match the engine.

    The Brand Equity panel previews next step's score for each spend decision so
    the user can decide before committing. Those projections are computed via the
    shared MarketingConfig helper (the same maths the engine runs), so assert the
    response value equals the helper — this is what stops the preview from
    drifting from the actual outcome.
    """
    cfg = _marketing_cfg(be_boost=0.25, be_decay_rate=0.20)
    game_state = game_state_factory_fixed_list_asset_gen()
    game_state._marketing_config = cfg
    asset_id = next(iter(game_state.assets))
    game_state._brand_scores[asset_id] = 0.30
    game_state._brand_score_floors[asset_id] = 0.10

    response = GameStateResponse(**game_state_to_response(game_state))

    resp_asset = response.assets[asset_id]
    assert resp_asset.brand_score_if_spend == pytest.approx(
        cfg.next_brand_score(0.30, 0.10, spend=True)
    )
    assert resp_asset.brand_score_if_hold == pytest.approx(
        cfg.next_brand_score(0.30, 0.10, spend=False)
    )
    # Spending must project at least as high as holding (a push only helps).
    assert resp_asset.brand_score_if_spend >= resp_asset.brand_score_if_hold


def test_brand_projection_equals_score_when_marketing_disabled(
    game_state_factory_fixed_list_asset_gen,
):
    """With marketing off there is nothing to project; both mirror the score."""
    game_state = game_state_factory_fixed_list_asset_gen()
    game_state._marketing_config = None
    asset_id = next(iter(game_state.assets))
    game_state._brand_scores[asset_id] = 0.42

    response = GameStateResponse(**game_state_to_response(game_state))

    resp_asset = response.assets[asset_id]
    assert resp_asset.brand_score_if_spend == pytest.approx(0.42)
    assert resp_asset.brand_score_if_hold == pytest.approx(0.42)


def test_brand_equity_cost_zero_when_marketing_disabled(
    game_state_factory_fixed_list_asset_gen,
):
    """be_cost gates on the feature flag; the banked score still surfaces."""
    game_state = game_state_factory_fixed_list_asset_gen()
    game_state._marketing_config = None
    asset_id = next(iter(game_state.assets))
    game_state._brand_scores[asset_id] = 0.42

    response = GameStateResponse(**game_state_to_response(game_state))

    resp_asset = response.assets[asset_id]
    assert resp_asset.be_cost == 0.0
    assert resp_asset.brand_score == pytest.approx(0.42)


def test_brand_equity_fields_present_on_expired_assets(
    game_state_factory_fixed_list_asset_gen,
):
    """
    Required brand fields must be set on every asset bucket or validation fails.

    DrugAssetResponse backs live, expired/failed and dropped assets alike, so
    the response builder has to populate the (required) brand fields for dead
    drugs too — be_cost 0 (they can't be pushed), score/floor carried over.
    """
    game_state = game_state_factory_fixed_list_asset_gen()
    game_state._marketing_config = _marketing_cfg()
    # Move a live asset into the expired bucket to exercise that path.
    asset_id, asset = next(iter(game_state.assets.items()))
    del game_state.assets[asset_id]
    game_state.expired_assets[asset_id] = asset
    game_state._brand_scores[asset_id] = 0.30

    response = GameStateResponse(**game_state_to_response(game_state))

    resp_asset = response.expired_assets[asset_id]
    assert resp_asset.brand_score == pytest.approx(0.30)
    assert resp_asset.be_cost == 0.0


def _indication_market(demand_multiplier: float) -> IndicationMarketState:
    return IndicationMarketState(
        therapeutic_area="oncology",
        indication=0,
        indication_name="Some Cancer",
        demand_multiplier=demand_multiplier,
    )


def test_demand_multiplier_projection_matches_helper():
    """
    The DC panel previews next step's demand multiplier for each spend decision.

    Those projections come from the shared MarketingConfig helper, so the
    response must equal the helper — that shared maths is what keeps the preview
    from drifting from what the engine produces next step.
    """
    cfg = _marketing_cfg(dc_step_boost=0.20, dc_decay_rate=0.10)
    market = _indication_market(1.50)

    resp = indication_market_to_response(
        market, current_time=0, player_agent="you", name_map=None, marketing_cfg=cfg
    )

    assert resp.demand_multiplier == pytest.approx(1.50)
    assert resp.demand_multiplier_if_spend == pytest.approx(
        cfg.next_demand_multiplier(1.50, spend=True)
    )
    assert resp.demand_multiplier_if_hold == pytest.approx(
        cfg.next_demand_multiplier(1.50, spend=False)
    )
    assert resp.demand_multiplier_if_spend > resp.demand_multiplier_if_hold


def test_demand_multiplier_projection_mirrors_current_when_marketing_off():
    """With no marketing config there is nothing to project; both mirror current."""
    market = _indication_market(1.30)

    resp = indication_market_to_response(
        market,
        current_time=0,
        player_agent="you",
        name_map=None,
        marketing_cfg=None,
    )

    assert resp.demand_multiplier_if_spend == pytest.approx(1.30)
    assert resp.demand_multiplier_if_hold == pytest.approx(1.30)
