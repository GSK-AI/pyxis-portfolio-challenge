import uuid

import pytest

from app.endpoint_datamodels import GameState, StartGameRequest
from app.redis_cache import RedisCache


class MockRedisClient:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key, None)

    async def set(self, key, value):
        self.store[key] = value
        return True

    async def delete(self, key):
        if key in self.store:
            del self.store[key]
            return True
        return False

    async def close(self):
        self.store.clear()
        return True


@pytest.fixture
def redis_cache_with_mock_client(game_state_factory_json_asset_gen):
    return RedisCache(client=MockRedisClient())


@pytest.fixture
def start_game_request():
    return StartGameRequest(
        num_assets=5,
        max_num_assets=5,
        horizon=10,
        starting_cash=1000000.0,
        global_seed=100,
        level_idx=-1,
    )


@pytest.fixture
def mock_game_state():
    return GameState(
        id=uuid.uuid4(),
        cash=1000000.0,
        time=0,
        horizon=10,
        equilibrium_num_assets=5,
        max_num_assets=5,
        asset_arrival_sensitivity_below=1.5,
        asset_arrival_sensitivity_above=3.0,
        reinvestment_percentage=1.0,
        initial_cash=1000000.0,
        assets={},
        failed_assets={},
        expired_assets={},
        realised_costs=[],
        realised_revenues=[],
        running_enpv=[],
        running_eroi=[],
        game_ended=False,
        ended_reason=None,
    )
