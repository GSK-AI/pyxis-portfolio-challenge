import contextvars
import random

_game_rng: contextvars.ContextVar[random.Random] = contextvars.ContextVar("game_rng")


def init_game_rng(seed: int) -> random.Random:
    """Initialize the game-wide RNG. Call once per episode."""
    rng = random.Random(seed)
    _game_rng.set(rng)
    return rng


def get_game_rng() -> random.Random:
    """Get the current game-wide RNG. Raises if not initialized."""
    try:
        return _game_rng.get()
    except LookupError:
        raise RuntimeError("Game RNG not initialized. Call init_game_rng(seed) first.")
