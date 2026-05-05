import os

import upath

# has to be defined before any relative imports
PROJECT_ROOT = upath.UPath(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
)

from aiml_pyxis_investment_game.environment.env_factory import (  # noqa: E402
    make_train_env,
)
from aiml_pyxis_investment_game.environment.evaluate import (  # noqa: E402
    evaluate,
    parallel_evaluate,
)

__all__ = ["evaluate", "parallel_evaluate", "make_train_env", "PROJECT_ROOT"]
