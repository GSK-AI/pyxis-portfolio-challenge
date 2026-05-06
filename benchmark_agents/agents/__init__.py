from pyxis_portfolio_challenge.agents.knapsack import (
    DistributionalMCKAgent,
    KnapsackAgent,
    KnapsackWithStopAgent,
    MultipleChoiceKnapsackAgent,
)
from pyxis_portfolio_challenge.agents.multi_step_knapsack import MultiStepKnapsackAgent

from .do_nothing_agent import do_nothing_agent
from .kelly_agent import (
    AggressiveKellyAgent,
    ConservativeKellyAgent,
    KellyAgent,
    QuarterKellyAgent,
)
from .pyxie_agent import (
    pyxie_distributional_ptrs,
    pyxie_interim_trial_obs,
    pyxie_investment_levels,
    pyxie_new_agent,
    pyxie_ta_specialization_control,
    pyxie_ta_specialization_treatment,
)
from .random_agent import (
    RandomAgent,
    RandomAgentWithCashWrapper,
    random_agent,
    random_agent_with_cash_wrapper,
)

AGENTS = {
    "do_nothing": do_nothing_agent,
    "random": RandomAgent(),  # Use new class-based agent with mask support
    "random_cash_wrapper": RandomAgentWithCashWrapper(),  # Use new class-based agent
    "random_legacy": random_agent,  # Keep legacy function for backward compatibility
    "random_cash_wrapper_legacy": random_agent_with_cash_wrapper,  # Legacy version
    "knapsack_agent": KnapsackAgent(),
    "knapsack_with_stop": KnapsackWithStopAgent(),  # Knapsack with STOP action enabled
    "mck_agent": MultipleChoiceKnapsackAgent(),  # Multiple-Choice Knapsack (all levels)
    "distributional_mck": DistributionalMCKAgent(
        stop_threshold=0.7,  # Optimal from hyperparameter sweep
        min_ev_to_continue=0.6e9,  # Optimal from sweep
        confidence_weight=0.2,  # Optimal from sweep
    ),  # MCK adapted for distributional PTRS (optimized)
    "multi_step_knapsack_agent": MultiStepKnapsackAgent(),
    "pyxie_agent": pyxie_new_agent(),
    # TA Specialization experiment agents
    "pyxie_ta_treatment": pyxie_ta_specialization_treatment(),
    "pyxie_ta_control": pyxie_ta_specialization_control(),
    # Investment levels agent
    "pyxie_investment_levels": pyxie_investment_levels(),
    # Interim trial observations agent (with STOP action)
    "pyxie_interim_trial_obs": pyxie_interim_trial_obs(),
    # Distributional PTRS agent (current training)
    "pyxie_distributional_ptrs": pyxie_distributional_ptrs(),
    # Kelly criterion agents
    "kelly_agent": KellyAgent(),  # Half-Kelly (default)
    "kelly_conservative": ConservativeKellyAgent(),  # Quarter-Kelly
    "kelly_quarter": QuarterKellyAgent(),  # Quarter-Kelly (alias)
    "kelly_aggressive": AggressiveKellyAgent(),  # Full Kelly
}
