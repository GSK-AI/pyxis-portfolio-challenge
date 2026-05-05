from __future__ import annotations

import logging
import pickle

import redis.asyncio as redis

logger = logging.getLogger(__name__)


def create_azure_redis_client(
    host: str, port: int = 6380, db: int = 0, password: str | None = None
) -> redis.Redis:
    """Creates a Redis client for Azure Redis with password-based auth."""
    logger.info(f"Attempting to connect to Redis at: {host}:{port}")

    return redis.Redis(
        host=host,
        port=port,
        db=db,
        password=password,
        ssl=True,
        decode_responses=False,
        socket_timeout=10,
        socket_connect_timeout=10,
    )


def create_local_redis_client(
    host: str = "localhost", port: int = 6379, db: int = 0
) -> redis.Redis:
    """Creates an Redis client for a local Redis instance."""
    logger.info(f"Connecting to local Redis at: {host}:{port}")
    return redis.Redis(host=host, port=port, db=db, decode_responses=False)


class RedisCache:
    """
    Interface for interacting with a Redis database/cache.

    This interface uses Pickle serialization for various set/get methods. It implements
    several custom wrappers specific to objects used in the app.
    """

    def __init__(self, client: redis.Redis) -> None:
        """
        Initialize the Redis client with the given host, port, and database index.

        Args:
            client (redis.Redis): An instance of an asynchronous Redis client.

        """
        self.client = client

    async def test_connection(self):
        """Test the Redis connection with a ping, set and get."""
        # Ping
        try:
            result = await self.client.ping()
            logger.info(f"Redis connection is alive. Ping: {result}")
        except Exception as e:
            logger.error(f"Redis connection test failed: {e}")

        # Set
        try:
            result = await self.client.set(
                "Message", "Hello, The Redis cache is working with Python!"
            )
            print("Redis SET Message succeeded: " + str(result))
        except Exception as e:
            print("Redis SET Message failed: " + str(e))

        # Get
        try:
            value = await self.client.get("Message")
            # Use decode("utf-8") to convert bytes to string when not unpickling
            value = value.decode("utf-8")
            if value is not None:
                print("Redis GET Message returned : " + str(value))
            else:
                print("Redis GET Message returned None")
        except Exception as e:
            print("Redis GET Message failed: " + str(e))

    # Generic set/get methods using Pickle for serialization
    async def set(self, key, value):
        """Set any value in Redis, serialized with Pickle."""
        await self.client.set(key, pickle.dumps(value))

    async def get(self, key):
        """Get any value from Redis, deserialized with Pickle."""
        data = await self.client.get(key)
        if data is None:
            return None
        return pickle.loads(data)

    async def delete(self, key):
        """Delete a key from Redis."""
        await self.client.delete(key)

    # --- Custom methods wrapping generic set/get ---
    async def set_game_state(self, game_id, game_state):
        """Store game state for a given game_id."""
        await self.set(f"game_state:{game_id}", game_state)

    async def get_game_state(self, game_id):
        """Retrieve game state for a given game_id."""
        return await self.get(f"game_state:{game_id}")

    async def delete_game_state(self, game_id):
        """Delete game state for a given game_id."""
        await self.delete(f"game_state:{game_id}")

    async def set_game_level(self, game_id, level_idx):
        """Store the current level index for a given game_id."""
        await self.set(f"level:{game_id}", level_idx)

    async def get_game_level(self, game_id):
        """Retrieve the current level index for a given game_id."""
        return await self.get(f"level:{game_id}")

    async def delete_game_level(self, game_id):
        """Delete the current level index for a given game_id."""
        await self.delete(f"level:{game_id}")

    async def set_user_current_game(self, user_id, game_id):
        """Store current game_id for a user."""
        await self.set(f"user:{user_id}:current_game", game_id)

    async def get_user_current_game(self, user_id):
        """Retrieve current game_id for a user."""
        return await self.get(f"user:{user_id}:current_game")

    async def close(self):
        """Close the Redis connection."""
        await self.client.close()

    # To add more custom methods, wrap the generic set/get with your desired key pattern

    # --- Multi-Agent Game Methods ---

    async def set_multi_game_state(self, game_id, multi_game):
        """Store multi-agent game state for a given game_id."""
        await self.set(f"multi_game_state:{game_id}", multi_game)

    async def get_multi_game_state(self, game_id):
        """Retrieve multi-agent game state for a given game_id."""
        return await self.get(f"multi_game_state:{game_id}")

    async def delete_multi_game_state(self, game_id):
        """Delete multi-agent game state for a given game_id."""
        await self.delete(f"multi_game_state:{game_id}")

    async def set_multi_game_opponents(self, game_id, opponent_types):
        """Store opponent agent types for a given game_id."""
        await self.set(f"multi_game_opponents:{game_id}", opponent_types)

    async def get_multi_game_opponents(self, game_id):
        """Retrieve opponent agent types for a given game_id."""
        return await self.get(f"multi_game_opponents:{game_id}")

    async def set_multi_game_display_names(self, game_id, display_names):
        """Store opponent display names for a given game_id."""
        await self.set(f"multi_game_display_names:{game_id}", display_names)

    async def get_multi_game_display_names(self, game_id):
        """Retrieve opponent display names for a given game_id."""
        return await self.get(f"multi_game_display_names:{game_id}")

    async def set_multi_game_cumulative_rewards(self, game_id, cumulative_rewards):
        """Store cumulative rewards for a given game_id."""
        await self.set(f"multi_game_cumulative_rewards:{game_id}", cumulative_rewards)

    async def get_multi_game_cumulative_rewards(self, game_id):
        """Retrieve cumulative rewards for a given game_id."""
        return await self.get(f"multi_game_cumulative_rewards:{game_id}")

    async def set_multi_game_asset_orders(self, game_id, asset_orders):
        """Store asset orderings for PPO inference in a given game_id."""
        await self.set(f"multi_game_asset_orders:{game_id}", asset_orders)

    async def get_multi_game_asset_orders(self, game_id):
        """Retrieve asset orderings for a given game_id."""
        return await self.get(f"multi_game_asset_orders:{game_id}")

    async def set_agent_hints_used(self, user_id, agent_name, hints_used):
        """Store the number of hints used by an agent."""
        await self.set(f"user:{user_id}:agent:{agent_name}:hints_used", hints_used)

    async def get_agent_hints_used(self, user_id, agent_name):
        """Retrieve the number of hints used by an agent."""
        return await self.get(f"user:{user_id}:agent:{agent_name}:hints_used")


def get_redis_cache(use_local: bool, host: str, port: int, db: int) -> RedisCache:
    """
    Factory function to get an instance of RedisCache.

    Args:
        use_local (bool): If True, returns a cache connected to a local Redis.
                          Otherwise, connects to Azure Redis.
        host (str): The Redis host.
        port (int): The Redis port.
        db (int): The Redis database index.

    Returns:
        RedisCache: An initialized RedisCache instance.

    """
    if use_local:
        client = create_local_redis_client(host=host, port=port, db=db)
    else:
        client = create_azure_redis_client(host=host, port=port, db=db)
    return RedisCache(client)
