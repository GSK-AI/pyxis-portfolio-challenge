from aiml_pyxis_investment_game.game.asset import AssetState
from aiml_pyxis_investment_game.game.trial import TrialPhase, TrialState
from app.endpoint_datamodels import (
    asset_to_response,
    game_state_to_response,
)
from tests.game.test_asset import drug_asset_factory


def test_drug_asset_to_response():
    asset = drug_asset_factory()


    # handle pending trial phase logic
    if asset.trial.phase == TrialPhase.PHASE_3 and asset.trial.state == TrialState.PHASE_SUCCESS and asset.state == AssetState.OnMarket:
        pending_trial_phase = None
    elif asset.trial.state == TrialState.PHASE_FAILED:
        pending_trial_phase = None
    else:
        pending_trial_phase = asset.trial.phase.value

    response = asset_to_response(asset)

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
    assert response["expected_costs"] == asset.expected_costs_and_revenues[0]
    assert response["expected_revenues"] == asset.expected_costs_and_revenues[1]
    assert response["eroi"] == asset.eroi


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
