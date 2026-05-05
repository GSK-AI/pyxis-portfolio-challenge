from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pyxis_portfolio_challenge.game.asset_generators import JSONAssetGenerator
from app.app import (
    get_agents,
    get_custom_seed,
    lifespan,
    start_game,
    step_game,
)

# create new FastAPI app instance without auth middleware for testing
app = FastAPI(lifespan=lifespan)


def setup_app(app: FastAPI):
    """Manually setup routes for testing without middleware."""
    app.add_api_route(
        "/game/get_agents",
        get_agents,
        methods=["GET"],
    )
    app.add_api_route(
        "/game/custom_seeds",
        get_custom_seed,
        methods=["GET"],
    )
    app.add_api_route(
        "/game/start_game",
        start_game,
        methods=["POST"],
    )
    app.add_api_route(
        "/game/{game_id}/step_game",
        step_game,
        methods=["POST"],
    )
    return app


app = setup_app(app)
client = TestClient(app)


def test_get_agents():
    response = client.get("/game/get_agents")
    assert response.status_code == 200
    data = response.json()
    assert data == [
        {"name": "Knapsack", "cost": 500000.0},
        {"name": "Pyxie", "cost": 5000000.0},
    ]


def test_get_custom_seed():
    mock_custom_seeds = MagicMock()
    d = {5: [1, 2, 3]}
    mock_custom_seeds.__getitem__.side_effect = d.__getitem__
    with patch("app.app.CUSTOM_SEEDS", new=mock_custom_seeds):
        response = client.get("/game/custom_seeds", params={"initial_num_assets": 5})
        assert response.status_code == 200
        data = response.json()
        assert data in [1, 2, 3]


async def test_start_game(
    redis_cache_with_mock_client, start_game_request, mock_game_state
):
    with (
        patch(
            "app.app.get_redis_cache_from_request",
            return_value=redis_cache_with_mock_client,
        ),
        patch("app.app.get_session_id_from_request", return_value="mudid"),
        patch(
            "app.app.GameState.initialise_new_game", return_value=mock_game_state
        ) as mock_game_state_initialise,
    ):
        response = client.post("/game/start_game", json=start_game_request.model_dump())
        assert response.status_code == 200

        mock_game_state_initialise.assert_called_once()
        call_kwargs = mock_game_state_initialise.call_args.kwargs
        assert call_kwargs["asset_generator_cls"] == JSONAssetGenerator
        assert call_kwargs["num_assets"] == start_game_request.num_assets
        assert call_kwargs["max_num_assets"] == start_game_request.max_num_assets
        assert call_kwargs["cash"] == start_game_request.starting_cash
        assert call_kwargs["horizon"] == start_game_request.horizon
        assert call_kwargs["global_seed"] == start_game_request.global_seed
        assert (
            "game_state:" + str(mock_game_state.id)
            in redis_cache_with_mock_client.client.store
        )
        assert "user:mudid:current_game" in redis_cache_with_mock_client.client.store
        assert (
            "level:" + str(mock_game_state.id)
            in redis_cache_with_mock_client.client.store
        )
        assert (
            "user:mudid:agent:Knapsack:hints_used"
            in redis_cache_with_mock_client.client.store
        )
        assert (
            "user:mudid:agent:Pyxie:hints_used"
            in redis_cache_with_mock_client.client.store
        )
        assert response.json()["id"] == str(mock_game_state.id)


# TODO: add tests for other endpoints
