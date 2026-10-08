from sb3_contrib import MaskablePPO

from pyxis_portfolio_challenge.agents.knapsack import KnapsackAgent
from pyxis_portfolio_challenge.agents.multi_agent_do_nothing import (
    MultiAgentDoNothingAgent as MultiAgentDoNothingAgent,
)
from pyxis_portfolio_challenge.agents.multi_agent_knapsack import (
    MultiAgentKnapsackAgent,
)
from pyxis_portfolio_challenge.agents.multi_agent_random import (
    MultiAgentRandomAgent as MultiAgentRandomAgent,
)
from pyxis_portfolio_challenge.agents.pyxie import PyxieAgent

# Pyxie is disabled as a selectable in-game opponent. The PyxieAgent class and
# get_agent() branch remain for internal use (e.g. training eval), but Pyxie is
# no longer offered in the game.
AGENTS_LIST = [
    {"name": "Knapsack", "cost": 500_000.0},
]
AGENTS = {agent["name"]: agent for agent in AGENTS_LIST}


def get_agent(name: str, **kwargs) -> object:
    """Retrieve an investment agent instance by passing its name."""
    if name == "Knapsack":
        agent = KnapsackAgent()
    elif name == "Pyxie":
        if "model_path" not in kwargs or "vecnorm_path" not in kwargs:
            raise ValueError(
                "model_path and vecnorm_path must be provided for Pyxie agent."
            )
        agent = PyxieAgent(
            algorithm=MaskablePPO,
            model_path=kwargs["model_path"],
            vecnorm_path=kwargs["vecnorm_path"],
        )
    elif name == "MultiAgentKnapsack":
        if "agent_name" not in kwargs:
            raise ValueError("agent_name must be provided for MultiAgentKnapsack.")
        agent = MultiAgentKnapsackAgent(agent_name=kwargs["agent_name"])
    elif name == "MultiAgentRandom":
        if "agent_name" not in kwargs:
            raise ValueError("agent_name must be provided for MultiAgentRandom.")
        agent = MultiAgentRandomAgent(agent_name=kwargs["agent_name"])
    elif name == "MultiAgentDoNothing":
        if "agent_name" not in kwargs:
            raise ValueError(
                "agent_name must be provided for MultiAgentDoNothing."
            )
        agent = MultiAgentDoNothingAgent(agent_name=kwargs["agent_name"])
    else:
        raise ValueError(
            f"Unknown agent name: {name}. Available agents: {list(AGENTS.keys())}"
        )
    return agent
