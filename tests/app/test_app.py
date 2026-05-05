from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aiml_pyxis_investment_game.game.asset_generators import JSONAssetGenerator
from app.app import (
    get_agents,
    get_custom_seed,
    get_global_leaderboard,
    get_highscore,
    get_level_leaderboard,
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
        "/game/leaderboard/global",
        get_global_leaderboard,
        methods=["GET"],
    )
    app.add_api_route(
        "/game/leaderboard/{level_idx}",
        get_level_leaderboard,
        methods=["GET"],
    )
    app.add_api_route(
        "/game/highscore/{level_idx}",
        get_highscore,
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


def test_get_level_leaderboard():
    with patch(
        "app.app.get_level_leaderboard_data",
    ) as mock_get_leaderboard:
        response = client.get("/game/leaderboard/1")
        assert response.status_code == 200
        mock_get_leaderboard.assert_called_once_with(level_id=1)


@pytest.fixture
def mock_leaderboard_entry():
    mock_entry = MagicMock()
    mock_entry.game_id = "game_id"
    mock_entry.user_id = "mudid"
    mock_entry.av_enpv = 500000.0
    return mock_entry


def test_get_highscore(mock_leaderboard_entry):
    with (
        patch(
            "app.app.get_user_best_level_metrics",
            return_value=mock_leaderboard_entry,
        ) as mock_get_user_best_level_metrics,
        patch(
            "app.app.get_mudid_from_request", return_value="mudid"
        ) as mock_get_mudid_from_request,
    ):
        response = client.get("/game/highscore/1")
        assert response.status_code == 200
        data = response.json()
        mock_get_mudid_from_request.assert_called_once()
        mock_get_user_best_level_metrics.assert_called_once_with(
            user_id="mudid", level_id=1
        )
        assert isinstance(data, dict)


def test_get_global_leaderboard(mock_leaderboard_entry):
    with patch(
        "app.app.get_global_leaderboard_data", return_value=mock_leaderboard_entry
    ) as mock_get_global_leaderboard:
        response = client.get("/game/leaderboard/global")
        assert response.status_code == 200
        mock_get_global_leaderboard.assert_called_once()


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
        patch("app.app.get_mudid_from_request", return_value="mudid"),
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
