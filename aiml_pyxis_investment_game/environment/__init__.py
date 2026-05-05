"""Environment package public API."""

from aiml_pyxis_investment_game.environment.env_factory import (
    make_multi_agent_train_env as make_multi_agent_train_env,
)
from aiml_pyxis_investment_game.environment.self_play import (
    SelfPlayWrapper as SelfPlayWrapper,
)

# NOTE: `evaluate` cannot be re-exported here because the `evaluate.py`
# submodule shadows function-level imports. Import directly:
#   from aiml_pyxis_investment_game.environment.competition import evaluate

__all__ = [
    "SelfPlayWrapper",
    "make_multi_agent_train_env",
]
