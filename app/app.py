import copy
import logging
import random
import traceback
import uuid
from contextlib import asynccontextmanager
from typing import Literal, Optional

import upath
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from aiml_pyxis_investment_game import config
from aiml_pyxis_investment_game.agents import AGENTS, AGENTS_LIST, get_agent
from aiml_pyxis_investment_game.agents.utils import get_agent_investment_decisions
from aiml_pyxis_investment_game.game.asset_generators import (
    JSONAssetGenerator,
)
from aiml_pyxis_investment_game.game.constants import (
    CUSTOM_SEEDS,
    LEVELS,
    MAX_NUM_ASSETS,
    InvestmentLevel,
)
from aiml_pyxis_investment_game.game.game_state import GameState
from aiml_pyxis_investment_game.game.metrics import prepare_game_metrics_data
from aiml_pyxis_investment_game.game.multi_agent_game import MultiAgentGame
from aiml_pyxis_investment_game.logging_utils import setup_logging
from app.endpoint_datamodels import (
    ActionType,
    AgentResponse,
    ComparisonDashboardResponse,
    GameStateResponse,
    LevelResponse,
    MultiAgentGameStateResponse,
    MultiAgentStepRequest,
    OpponentAgentInfo,
    StartGameRequest,
    StartMultiAgentGameRequest,
    game_state_to_response,
    multi_agent_game_to_response,
)
from app.game_db import (
    LeaderboardEntry,
    get_global_leaderboard_data,
    get_level_id_of_game_id,
    get_level_leaderboard_data,
    get_user_best_level_metrics,
    get_user_game_metrics,
    has_user_completed_level,
    insert_game_metrics,
)
from app.middleware import (
    SecurityHeadersMiddleware,
    UserFromJWTAuthMiddleware,
)
from app.opponent_runner import (
    AVAILABLE_OPPONENTS,
    generate_opponent_display_names,
    get_opponent_actions,
    init_asset_id_orders,
    update_asset_id_orders,
)
from app.redis_cache import get_redis_cache
from app.settings import settings

setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

game_config = config.from_yaml()
reward_fn = config.instantiate_from_config(game_config.reward_fn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Creates the database and loads all data."""
    # Initialize the Redis connection
    app.state.redis_cache = get_redis_cache(
        use_local=settings.use_local_redis,
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )
    await app.state.redis_cache.test_connection()
    logger.info("Redis connection initialized")

    yield

    # Clean up Redis connection
    await app.state.redis_cache.close()
    logger.info("Redis connection closed")


origins = [
    "http://localhost:3000",
    "http://localhost:8081",
    "https://rdfn-portfolio-be-dev-001.rd-iase-devtest-us6.appserviceenvironment.net",
    "https://rdfn-portfolio-dev-001.rd-iase-devtest-us6.appserviceenvironment.net",
    "https://rdfn-portfolio-uat-001.rd-iase-uat-us6.appserviceenvironment.net",
    "https://rdfn-portfolio-be-uat-001.rd-iase-uat-us6.appserviceenvironment.net",
    "https://rdfn-portfolio-be-prod-001.rd-iase-prod-us6.appserviceenvironment.net",
    "https://rdfn-portfolio-prod-001.rd-iase-prod-us6.appserviceenvironment.net",
    "https://pyxis.gsk.com",
    "https://cdn.jsdelivr.net",
    "https://fastapi.tiangolo.com",
]

app = FastAPI(
    title="Pyxis Investment Game",
    description="Simulating investments in pharmaceutical assets",
    lifespan=lifespan,
)

if not settings.disable_auth_middleware:
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(UserFromJWTAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled exceptions."""
    error_msg = f"Unhandled exception: {str(exc)}"
    logger.error(f"{error_msg}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"message": "An internal server error occurred."},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Exception handler for HTTP exceptions."""
    logger.error(f"HTTP exception: {exc.detail}, status_code: {exc.status_code}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Exception handler for request validation errors."""
    logger.error(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=422,
        content={"message": f"Validation error: {str(exc)}"},
    )


def get_mudid_from_request(request: Request) -> str:
    """
    Helper function to extract mudid from request state.

    Useful to pull this out to enable mocking in tests.

    If auth middleware is disabled, returns a test mudid.
    """
    if settings.disable_auth_middleware:
        return "test-user-mudid"

    return request.state.mudid


def get_redis_cache_from_request(request: Request):
    """
    Helper function to extract redis cache from request app state.

    Useful to pull this out to enable mocking in tests
    """
    return request.app.state.redis_cache


@app.get("/health")
async def health_check():
    """Health check endpoint for frontend connection verification."""
    return {"status": "ok"}


@app.get("/game/config")
async def get_game_config():
    """Get default game configuration from config.yaml."""
    import random

    return {
        "num_assets": game_config.equilibrium_num_assets,
        "max_num_assets": game_config.max_num_assets,
        "horizon": game_config.horizon,
        "starting_cash": game_config.starting_cash,
        "global_seed": random.randint(1, 1000000),
    }


@app.post("/game/start", response_model=GameStateResponse)
async def start_game(request: Request, payload: StartGameRequest) -> GameStateResponse:
    """
    Start a new game with the provided parameters.

    This function creates the GameState object and returns it. It also initialises the
    variables needed throughout the game's lifetime: the investor actions and the next
    cash flow.

    Args:
        request: Request
        payload: GameState object

    Returns:
        GameState
            The initial game state.

    """
    user = get_mudid_from_request(request)

    # Get previous game id attached to user and delete corresponding key
    previous_game_id = await get_redis_cache_from_request(
        request
    ).get_user_current_game(user)
    if previous_game_id:
        logger.info(f"Previous game found for user {user} with ID: {previous_game_id}.")
        logger.info("Deleting previous game...")
        await get_redis_cache_from_request(request).delete_game_state(previous_game_id)
        await get_redis_cache_from_request(request).delete_game_level(previous_game_id)
        logger.info("Previous game deleted.")

    # Initialise game and get game id
    game_state = GameState.initialise_new_game(
        asset_generator_cls=JSONAssetGenerator,
        num_assets=payload.num_assets,
        max_num_assets=payload.max_num_assets,
        cash=payload.starting_cash,
        horizon=payload.horizon,
        global_seed=payload.global_seed,
        asset_arrival_sensitivity_below=game_config.asset_arrival_sensitivity_below,
        asset_arrival_sensitivity_above=game_config.asset_arrival_sensitivity_above,
        reinvestment_percentage=game_config.reinvestment_percentage,
        ta_experience_config=game_config.ta_experience,
        investment_levels_config=game_config.investment_levels,
        uncertain_ptrs_config=game_config.uncertain_ptrs,
        interim_trial_observations_config=game_config.interim_trial_observations,
        distributional_ptrs_config=game_config.distributional_ptrs,
        rd_capacity_config=game_config.rd_capacity,
        approval_phase_config=game_config.approval_phase,
        indication_spread=game_config.multi_agent.indication_spread,
        indication_drift_speed=game_config.multi_agent.indication_drift_speed,
        trial_cost_multiplier=game_config.trial_cost_multiplier,
        **{"assets_dir": game_config.training_data_dir},
    )
    game_id = game_state.id

    logger.debug(f"Caching new game state: {game_id}")
    # Cache the current game id, game state and level
    await get_redis_cache_from_request(request).set_user_current_game(user, game_id)
    await get_redis_cache_from_request(request).set_game_state(game_id, game_state)
    await get_redis_cache_from_request(request).set_game_level(
        game_id, payload.level_idx
    )

    logger.info("Resetting agent hints.")
    # Reset the agent hints used to zero
    for agent_name in AGENTS:
        await get_redis_cache_from_request(request).set_agent_hints_used(
            user, agent_name, 0
        )

    logger.info("Getting game state response")
    game_state_response = game_state_to_response(game_state)
    return game_state_response


def convert_action_to_investment_level(
    action: ActionType | None,
) -> InvestmentLevel | None:
    """Convert a string action type to an InvestmentLevel enum."""
    if action is None:
        return None
    action_map = {
        "invest": InvestmentLevel.STANDARD,
        "none": InvestmentLevel.NONE,
        "minimal": InvestmentLevel.MINIMAL,
        "standard": InvestmentLevel.STANDARD,
        "accelerated": InvestmentLevel.ACCELERATED,
        "stop": InvestmentLevel.STOP,
    }
    return action_map.get(action)


@app.post("/game/{game_id}/step", response_model=GameStateResponse)
async def step_game(
    request: Request,
    game_id: uuid.UUID,
    actions: dict[uuid.UUID, Optional[ActionType]],
) -> GameStateResponse:
    """
    Advance the game state by one time step.

    This function uses dictionary of investor actions in the app state to update the
    game state. Before performing the step, it checks if the game has already ended and
    whether there are enough funds for investment.

    If the game has ended successfully (i.e. non-negative cash), the metrics are saved.

    Actions can be:
    - "none": Do not invest (for idle assets)
    - "invest": Invest at standard level (backward compatible)
    - "minimal": Invest at minimal level (slower, cheaper)
    - "standard": Invest at standard level
    - "accelerated": Invest at accelerated level (faster, more expensive)
    - "stop": Stop development early (for in-development assets)

    Returns:
        GameState
            The updated game state after stepping.

    """
    current_game_state = await get_redis_cache_from_request(request).get_game_state(
        game_id
    )

    # Check if game has already ended
    if current_game_state.game_ended:
        raise HTTPException(
            status_code=400, detail="Game has already ended, not taking step."
        )

    # Convert string actions to InvestmentLevel enums
    investment_actions: dict[uuid.UUID, InvestmentLevel | None] = {
        asset_id: convert_action_to_investment_level(action)
        for asset_id, action in actions.items()
    }

    # step the game
    next_game_state = current_game_state.step(investment_actions)

    await get_redis_cache_from_request(request).set_game_state(game_id, next_game_state)

    # Save metrics if game ended
    if next_game_state.game_ended:
        logger.info(
            f"Game ended because {next_game_state.ended_reason} "
            f"Saving metrics to PostgreSQL..."
        )
        try:
            level_idx = await get_redis_cache_from_request(request).get_game_level(
                game_id
            )

            game_metrics = prepare_game_metrics_data(
                user_name=str(get_mudid_from_request(request)),
                level_idx=level_idx,
                previous_game_state=current_game_state,
                game_state=next_game_state,
                actions=actions,
            )
            insert_game_metrics(data=game_metrics)
            logger.info(f"Game metrics saved: {game_metrics}")
        except Exception as e:
            logger.warning(f"Failed to save game metrics (non-fatal): {e}")

    game_state_response = game_state_to_response(next_game_state)
    return game_state_response


@app.get("/game/levels", response_model=list[LevelResponse])
async def get_levels(request: Request) -> list[LevelResponse]:
    """
    Retrieve the configurations for the game levels.

    This returns a list of LevelResponse instances that include parameters that
    can be passed to the start_game endpoint, as well as whether the level has
    been completed or not by the given user.

    Args:
        request: Request

    Returns:
        list[LevelResponse]
            A list of objects containing a boolean indicating whether the user
            has completed the level, and the StartGameRequest values for the
            level.

    """
    user = get_mudid_from_request(request)

    response = []
    for level_idx, level in enumerate(LEVELS):
        user_completed = has_user_completed_level(user_id=user, level_id=level_idx)
        response.append(
            LevelResponse(
                level_idx=level_idx,
                user_has_completed=user_completed,
                num_assets=level["num_assets"],
                max_num_assets=level["max_num_assets"],
                horizon=level["horizon"],
                starting_cash=level["starting_cash"],
                global_seed=level["global_seed"],
            )
        )

    return response


@app.get("/game/leaderboard/global", response_model=list[LeaderboardEntry])
async def get_global_leaderboard() -> list[LeaderboardEntry]:
    """
    Retrieve the global leaderboard across all game levels.

    This returns a list of LeaderboardEntry instances, each representing a user's
    overall performance across all levels.

    Returns:
        list[LeaderboardEntry]
            A list of global leaderboard entries.

    """
    return get_global_leaderboard_data()


@app.get("/game/leaderboard/{level_idx}", response_model=list[LeaderboardEntry])
async def get_level_leaderboard(level_idx: int) -> list[LeaderboardEntry]:
    """
    Retrieve the leaderboard for a specific game level.

    This returns a list of LeaderboardEntry instances, each representing a user's
    performance in the specified level, via their best game's average eNPV.

    Args:
        level_idx : int
            The index of the game level to retrieve the leaderboard for.

    Returns:
    list[LeaderboardEntry]
        A list of leaderboard entries for the specified level.

    """
    return get_level_leaderboard_data(level_id=level_idx)


@app.get("/game/highscore/{level_idx}", response_model=Optional[LeaderboardEntry])
async def get_highscore(request: Request, level_idx: int) -> Optional[LeaderboardEntry]:
    """
    Retrieve the high score for a specific game level and user.

    This returns a LeaderboardEntry instances, with the metrics for the user's best
    playthrough, if any exist. Otherwise, it returns None.

    Args:
        request : Request
        level_idx : int
            The index of the game level to retrieve the high score for.

    Returns:
        Optional[LeaderboardEntry]
            The high score entry for the specified level and user, or None if not found.

    """
    user = get_mudid_from_request(request=request)
    return get_user_best_level_metrics(user_id=user, level_id=level_idx)


@app.get("/game/agents", response_model=list[AgentResponse])
async def get_agents() -> list[AgentResponse]:
    """
    Retrieve the list of available investment agents.

    This returns a list of AgentResponse instances, providing the name and cost of each
    available agent.

    Args:
        request : Request
            The request object.

    Returns:
        list[AgentResponse]
            A list of available investment agents.

    """
    return AGENTS_LIST


def get_agent_by_name(name: str, level_idx: int):
    """
    Retrieve an investment agent instance by its name.

    Args:
        name (str): The name of the agent.
        level_idx (int): The level index for which to retrieve the agent.

    Returns:
        InvestmentAgent: The investment agent instance.

    """
    if name == "Pyxie":
        model_path = game_config.get_pyxie_model_model_path(level_idx)
        vecnorm_path = game_config.get_pyxie_model_vecnorm_path(level_idx)
        return get_agent("Pyxie", model_path=model_path, vecnorm_path=vecnorm_path)
    if name == "Knapsack":
        return get_agent("Knapsack")

    raise ValueError(f"Unknown agent name: {name}")


@app.post(
    "/game/{game_id}/hint",
    response_model=dict[str, dict[uuid.UUID, Optional[Literal["invest"]]]],
)
async def use_agent_hint(
    request: Request, game_id: uuid.UUID, agent_name: str
) -> dict[str, dict[uuid.UUID, Optional[Literal["invest"]]]]:
    """
    Use an agent hint to get investment decisions.

    This function retrieves the investment decisions from all available agents for the
    current game state, but deducts only the cost of the agent corresponding to the
    passed `agent_name`. It first checks that the user has enough cash to purchase an
    agent hint. Notably, the agent hint is then retrieved after subtracting the cost of
    the hint from the available cash.

    Args:
        request : Request
            The request object.
        game_id : uuid.UUID
            The ID of the game.
        agent_name : str
            The name of the agent to use for hints.

    Returns:
        dict[str, dict[uuid.UUID, Optional[Literal["invest"]]]]
            A dictionary mapping agent names to their respective investment decisions.

    """
    if agent_name not in AGENTS:
        raise HTTPException(status_code=404, detail="Agent not found")

    current_game_state = await get_redis_cache_from_request(request).get_game_state(
        game_id
    )
    agent_cost = AGENTS[agent_name]["cost"]
    if agent_cost > current_game_state.cash:
        raise HTTPException(
            status_code=403, detail="Insufficient funds to use agent hint"
        )

    user = get_mudid_from_request(request)
    agent_hints_used = await get_redis_cache_from_request(request).get_agent_hints_used(
        user, agent_name
    )
    if agent_hints_used >= 3:
        raise HTTPException(status_code=403, detail="Agent hint limit reached")

    # Deduct the cost of using the agent before getting the hints
    # NOTE: Need to implement cost deduction on the FE too
    logger.info(f"Deducting cost of {agent_name} agent: {agent_cost}...")
    current_game_state.cash -= agent_cost
    current_game_state.realised_costs[-1] += agent_cost

    level_idx = await get_redis_cache_from_request(request).get_game_level(game_id)

    # Get investment decisions from all agents
    agent_investment_decisions = {}
    logger.info("Retrieving investment decisions from all agents...")
    for name in AGENTS:
        logger.info(f"Initialising {name} agent...")
        agent = get_agent_by_name(name, level_idx)
        logger.info("Agent initialised.")
        logger.info(f"Retrieving investment decisions from {name} agent...")
        investment_decisions = get_agent_investment_decisions(
            agent=agent,
            game_state=current_game_state,
        )
        agent_investment_decisions[name] = investment_decisions
        logger.info("Investment decisions retrieved.")
    logger.info("Investment decisions retrieved from all agents.")

    # Update game state stored in Redis
    await get_redis_cache_from_request(request).set_game_state(
        game_id, current_game_state
    )

    # Update agent hints used
    await get_redis_cache_from_request(request).set_agent_hints_used(
        user, agent_name, agent_hints_used + 1
    )

    return agent_investment_decisions


@app.post(
    "/game/{game_id}/comparison_dashboard", response_model=ComparisonDashboardResponse
)
async def comparison_dashboard(
    request: Request,
    game_id: uuid.UUID,
) -> ComparisonDashboardResponse:
    """
    The metrics and arrays for the table and plots in the comparison dashboard.

    Args:
        request : Request
            The request object.
        game_id : uuid.UUID
            The game id.

    Returns:
        ComparisonDashboardResponse
            An object containing the metrics and arrays needed for the
            comparison dashboard table and plots (respectively). It contains
            these values for the given game_id referring to a user's game play,
            as well as for each of the agent's optimal solution.

    """
    user_id = str(get_mudid_from_request(request))
    user_metrics = get_user_game_metrics(user_id=user_id, game_id=str(game_id))
    if not user_metrics:
        raise HTTPException(status_code=404, detail="User metrics not found")

    level_id = get_level_id_of_game_id(game_id=str(game_id))
    agents_list = copy.deepcopy(AGENTS)
    if level_id == -1:
        # Get relevant game data and recreate initial state
        user_game_state = await get_redis_cache_from_request(request).get_game_state(
            game_id
        )
        global_seed = user_game_state._global_seed
        starting_cash = user_game_state.initial_cash
        initial_num_assets = user_game_state.initial_num_assets
        horizon = user_game_state.horizon
        logger.info("Initialising game...")
        initial_game_state = GameState.initialise_new_game(
            asset_generator_cls=JSONAssetGenerator,
            num_assets=initial_num_assets,
            max_num_assets=MAX_NUM_ASSETS,
            cash=starting_cash,
            horizon=horizon,
            global_seed=global_seed,
            asset_arrival_sensitivity_below=game_config.asset_arrival_sensitivity_below,
            asset_arrival_sensitivity_above=game_config.asset_arrival_sensitivity_above,
            reinvestment_percentage=game_config.reinvestment_percentage,
            ta_experience_config=game_config.ta_experience,
            investment_levels_config=game_config.investment_levels,
            uncertain_ptrs_config=game_config.uncertain_ptrs,
            interim_trial_observations_config=game_config.interim_trial_observations,
            distributional_ptrs_config=game_config.distributional_ptrs,
            **{"assets_dir": game_config.training_data_dir},
        )
        logger.info("Game initialised.")

        # Iterate through agents and run playthroughs for each
        agent_metrics = {}
        for agent_name in agents_list:
            agent = get_agent_by_name(agent_name, level_idx=-1)
            agent_game_state = copy.deepcopy(initial_game_state)
            logger.info(f"Starting {agent_name} agent playthrough...")
            result = agent.playthrough(
                agent_game_state, level_id, agent_name, verbose=True
            )
            logger.info("Agent playthrough complete.")
            agent_metrics[agent_name] = result["game_metrics"]
    else:
        agent_metrics = {}
        for agent_name in agents_list:
            agent_best_game = get_user_best_level_metrics(
                user_id=agent_name, level_id=level_id
            )
            if not agent_best_game:
                raise HTTPException(
                    status_code=404, detail=f"Agent has not played level {level_id}"
                )
            agent_metrics[agent_name] = get_user_game_metrics(
                user_id=agent_name, game_id=str(agent_best_game.game_id)
            )

    comparison_dashboard_dict = {
        "game_id": game_id,
        "av_enpv": {
            user_id: user_metrics.av_enpv,
            **{
                agent_name: agent_metrics[agent_name].av_enpv
                for agent_name in agents_list
            },
        },
        "final_enpv": {
            user_id: user_metrics.final_enpv,
            **{
                agent_name: agent_metrics[agent_name].final_enpv
                for agent_name in agents_list
            },
        },
        "final_eroi": {
            user_id: user_metrics.final_eroi,
            **{
                agent_name: agent_metrics[agent_name].final_eroi
                for agent_name in agents_list
            },
        },
        "final_capital": {
            user_id: user_metrics.final_capital,
            **{
                agent_name: agent_metrics[agent_name].final_capital
                for agent_name in agents_list
            },
        },
        "realised_eroi": {
            user_id: user_metrics.realised_roi,
            **{
                agent_name: agent_metrics[agent_name].realised_roi
                for agent_name in agents_list
            },
        },
        "enpv_over_time": {
            user_id: user_metrics.enpv_over_time,
            **{
                agent_name: agent_metrics[agent_name].enpv_over_time
                for agent_name in agents_list
            },
        },
        "eroi_over_time": {
            user_id: user_metrics.eroi_over_time,
            **{
                agent_name: agent_metrics[agent_name].eroi_over_time
                for agent_name in agents_list
            },
        },
    }

    return ComparisonDashboardResponse(**comparison_dashboard_dict)


@app.get("/game/custom_seeds", response_model=int)
def get_custom_seed(initial_num_assets: int) -> int:
    """
    Get a custom seed for the given number of assets.

    Selects from lists of pre-explored seeds that yield at least one On Market asset.

    Args:
        initial_num_assets : int
            The initial number of assets.

    Returns:
        int
            A random custom seed for the given number of assets.

    """
    return random.choice(CUSTOM_SEEDS[initial_num_assets])


# --- Multi-Agent Endpoints ---


@app.get("/game/multi/opponents", response_model=list[OpponentAgentInfo])
async def get_multi_agent_opponents() -> list[OpponentAgentInfo]:
    """Return available opponent agent types for multi-agent games."""
    return [OpponentAgentInfo(**info) for info in AVAILABLE_OPPONENTS]


@app.get("/game/multi/config")
async def get_multi_agent_config():
    """Return multi-agent game configuration from config.yaml."""
    ma = game_config.multi_agent
    return {
        "num_assets": game_config.equilibrium_num_assets,
        "max_num_assets": game_config.max_num_assets,
        "horizon": game_config.horizon,
        "max_opponents": settings.max_opponents,
        "starting_cash": game_config.starting_cash,
        "global_seed": random.randint(1, 1000000),
        "bd_enabled": ma.bd_enabled,
        "bd_base_lambda": ma.bd_base_lambda,
        "bd_num_bid_levels": ma.bd_num_bid_levels,
        "bd_break_even_bid_level": ma.bd_break_even_bid_level,
        "exclusivity_period": ma.exclusivity_period,
        "first_mover_bonus": ma.first_mover_bonus,
        "disable_market_share_competition": ma.disable_market_share_competition,
        "alert_history_length": ma.alert_history_length,
        "leak_phase_probabilities": ma.leak_phase_probabilities,
        "alerts_per_agent": ma.alerts_per_agent,
        "target_drugs_per_indication": ma.target_drugs_per_indication,
        "on_market_fraction": ma.on_market_fraction,
        "max_indications_per_ta": ma.max_indications_per_ta,
        "indication_spread": ma.indication_spread,
        "indication_drift_speed": ma.indication_drift_speed,
        "trial_cost_multiplier": game_config.trial_cost_multiplier,
        "congestion_exponent": ma.congestion_exponent,
        "congestion_ramp_steps": ma.congestion_ramp_steps,
        "congestion_incumbent_penalty": ma.congestion_incumbent_penalty,
    }


@app.post("/game/multi/start", response_model=MultiAgentGameStateResponse)
async def start_multi_agent_game(
    request: Request, payload: StartMultiAgentGameRequest
) -> MultiAgentGameStateResponse:
    """
    Start a new multi-agent game.

    The human player is always pharma_0. Opponents are pharma_1, pharma_2, etc.
    All multi-agent config parameters come from config.yaml.
    """
    user = get_mudid_from_request(request)
    cache = get_redis_cache_from_request(request)

    if payload.num_opponents > settings.max_opponents:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_opponents} opponent(s) allowed.",
        )

    # Clean up previous game
    previous_game_id = await cache.get_user_current_game(user)
    if previous_game_id:
        logger.info(f"Deleting previous game for user {user}: {previous_game_id}")
        await cache.delete_game_state(previous_game_id)
        await cache.delete_multi_game_state(previous_game_id)
        await cache.delete_game_level(previous_game_id)

    ma = game_config.multi_agent
    num_agents = 1 + payload.num_opponents

    # Compute indications_per_ta from config
    indications_per_ta = ma.compute_indications_per_ta(payload.num_assets)

    multi_game = MultiAgentGame.initialise(
        num_agents=num_agents,
        seed=payload.global_seed,
        starting_cash=payload.starting_cash,
        horizon=payload.horizon,
        equilibrium_num_assets=payload.num_assets,
        max_num_assets=payload.max_num_assets,
        asset_arrival_sensitivity_below=game_config.asset_arrival_sensitivity_below,
        asset_arrival_sensitivity_above=game_config.asset_arrival_sensitivity_above,
        reinvestment_percentage=game_config.reinvestment_percentage,
        assets_dir=game_config.training_data_dir,
        exclusivity_period=ma.exclusivity_period,
        first_mover_bonus=ma.first_mover_bonus,
        disable_market_share_competition=ma.disable_market_share_competition,
        alert_history_length=ma.alert_history_length,
        bd_enabled=ma.bd_enabled,
        bd_assets_dir=upath.UPath(ma.bd_assets_dir),
        bd_base_lambda=ma.bd_base_lambda,
        bd_leak_lambda_boost=ma.bd_leak_lambda_boost,
        bd_min_step=ma.bd_min_step,
        bd_phase_weights=list(ma.bd_phase_weights),
        bd_indication_activity_bias=ma.bd_indication_activity_bias,
        leak_phase_probabilities=list(ma.leak_phase_probabilities),
        approval_phase_config=game_config.approval_phase,
        reward_fn_config={},
        distributional_ptrs_config=game_config.distributional_ptrs,
        ta_experience_config=game_config.ta_experience,
        uncertain_ptrs_config=game_config.uncertain_ptrs,
        investment_levels_config=game_config.investment_levels,
        interim_trial_observations_config=game_config.interim_trial_observations,
        indications_per_ta=indications_per_ta,
        indication_spread=ma.indication_spread,
        indication_drift_speed=ma.indication_drift_speed,
        trial_cost_multiplier=game_config.trial_cost_multiplier,
        congestion_exponent=ma.congestion_exponent,
        congestion_ramp_steps=ma.congestion_ramp_steps,
        congestion_incumbent_penalty=ma.congestion_incumbent_penalty,
        rd_capacity_config=game_config.rd_capacity,
        bd_num_bid_levels=ma.bd_num_bid_levels,
        bd_break_even_bid_level=ma.bd_break_even_bid_level,
        bd_max_slots=ma.bd_max_slots,
        pricing_elasticity=game_config.pricing.elasticity,
    )

    game_id = multi_game.agent_states["pharma_0"].id

    # Generate fun display names for opponents
    display_names = generate_opponent_display_names(
        payload.opponent_agents, payload.global_seed
    )

    # Initialize cumulative rewards to zero for all agents
    cumulative_rewards = {f"pharma_{i}": 0.0 for i in range(num_agents)}

    # Initialize asset orderings for PPO inference
    asset_id_orders = init_asset_id_orders(
        multi_game, payload.max_num_assets
    )

    # Store in Redis
    await cache.set_multi_game_state(game_id, multi_game)
    await cache.set_multi_game_opponents(game_id, payload.opponent_agents)
    await cache.set_multi_game_display_names(game_id, display_names)
    await cache.set_multi_game_cumulative_rewards(game_id, cumulative_rewards)
    await cache.set_multi_game_asset_orders(game_id, asset_id_orders)
    await cache.set_user_current_game(user, game_id)

    logger.info(
        f"Multi-agent game started: {game_id}, "
        f"{num_agents} agents, opponents: {payload.opponent_agents}, "
        f"display_names: {display_names}"
    )

    return multi_agent_game_to_response(
        multi_game,
        "pharma_0",
        payload.opponent_agents,
        display_names,
        cumulative_rewards,
    )


@app.post("/game/multi/{game_id}/step", response_model=MultiAgentGameStateResponse)
async def step_multi_agent_game(
    request: Request,
    game_id: uuid.UUID,
    payload: MultiAgentStepRequest,
) -> MultiAgentGameStateResponse:
    """
    Advance the multi-agent game by one step.

    The human player's actions are provided in the request.
    Opponent agents compute their actions server-side.
    """
    cache = get_redis_cache_from_request(request)
    multi_game = await cache.get_multi_game_state(game_id)
    if multi_game is None:
        raise HTTPException(status_code=404, detail="Multi-agent game not found")

    opponent_types = await cache.get_multi_game_opponents(game_id)
    if opponent_types is None:
        raise HTTPException(status_code=404, detail="Opponent config not found")
    display_names = await cache.get_multi_game_display_names(game_id)
    cumulative_rewards = await cache.get_multi_game_cumulative_rewards(game_id)
    if cumulative_rewards is None:
        cumulative_rewards = {name: 0.0 for name in multi_game.agent_states}
    asset_id_orders = await cache.get_multi_game_asset_orders(game_id)

    # Check if the entire game is over (all agents ended or horizon reached)
    all_ended = all(s.game_ended for s in multi_game.agent_states.values())
    horizon_reached = multi_game.time >= multi_game.horizon
    if all_ended or horizon_reached:
        raise HTTPException(
            status_code=400, detail="Game has already ended, not taking step."
        )

    player_state = multi_game.agent_states["pharma_0"]

    # If player is bankrupt, submit empty actions; otherwise build from payload
    num_bd_slots = len(multi_game.shared_market.current_bd_assets)
    if player_state.game_ended:
        player_inv_actions: dict[uuid.UUID, InvestmentLevel | None] = {}
        player_bd_bids = [0] * num_bd_slots
    else:
        # Build human player investment actions
        player_inv_actions = {
            asset_id: convert_action_to_investment_level(action)
            for asset_id, action in payload.investment_actions.items()
        }
        # Pad/truncate bids to match number of BD slots
        player_bd_bids = list(payload.bd_bids)
        while len(player_bd_bids) < num_bd_slots:
            player_bd_bids.append(0)
        player_bd_bids = player_bd_bids[:num_bd_slots]

    # Collect all agent actions
    all_investor_actions = {"pharma_0": player_inv_actions}
    all_bd_bids: dict[str, list[int]] = {"pharma_0": player_bd_bids}

    for i, agent_type in enumerate(opponent_types):
        agent_name = f"pharma_{i + 1}"
        if agent_name not in multi_game.agent_states:
            continue
        if multi_game.agent_states[agent_name].game_ended:
            all_investor_actions[agent_name] = {}
            all_bd_bids[agent_name] = [0] * num_bd_slots
            continue

        inv_actions, bd_bid = get_opponent_actions(
            agent_type, agent_name, multi_game, asset_id_orders
        )
        all_investor_actions[agent_name] = inv_actions
        all_bd_bids[agent_name] = [bd_bid] * num_bd_slots

    # Step the game
    new_game = multi_game.step(
        investor_actions=all_investor_actions,
        bd_bids=all_bd_bids,
    )

    # Update asset orderings for new/removed assets
    if asset_id_orders is not None:
        update_asset_id_orders(new_game, asset_id_orders)

    # Compute per-step reward for each agent using configured reward function
    for agent_name in multi_game.agent_states:
        pre_state = multi_game.agent_states[agent_name]
        post_state = new_game.agent_states[agent_name]
        if not pre_state.game_ended:
            step_reward = reward_fn.compute(pre_state, post_state)
            cumulative_rewards[agent_name] = (
                cumulative_rewards.get(agent_name, 0.0) + step_reward
            )

    # Store updated state
    await cache.set_multi_game_state(game_id, new_game)
    await cache.set_multi_game_cumulative_rewards(game_id, cumulative_rewards)
    if asset_id_orders is not None:
        await cache.set_multi_game_asset_orders(game_id, asset_id_orders)

    return multi_agent_game_to_response(
        new_game, "pharma_0", opponent_types, display_names, cumulative_rewards
    )
