# Developer Guide

## Setup

```bash
# Install core dependencies
uv sync

# Install with development dependencies
uv sync --extra dev

# Install with app dependencies (FastAPI server)
uv sync --extra app

# Install with experiment dependencies (Hydra, TensorBoard)
uv sync --extra experiment

# Install with asset generation dependencies
uv sync --extra asset-gen
```

## Testing

```bash
# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -s

# Run tests with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/environment/test_evaluate.py

# Run specific test function
uv run pytest tests/environment/test_evaluate.py::test_parallel_evaluate
```

## Linting & Formatting

```bash
# Check code with ruff
uv run ruff check .

# Format code with ruff
uv run ruff format .

# Auto-fix issues
uv run ruff check . --fix
```

## Architecture

### Core Game Design

**GameState** (`game/game_state.py`) is the single source of truth for all game dynamics. It is an immutable Pydantic model representing one agent's portfolio: cash, revenues, costs, time, and a collection of `DrugAsset` objects. The deterministic `step()` method implements a three-phase cycle: Cost (pay trial costs), Revenue (collect from marketed drugs), Evolution (assets progress, succeed, or fail). Game ends on bankruptcy or horizon.

**DrugAsset** (`game/asset.py`) models individual R&D assets with a state machine: `Idle` -> `InDevelopment` -> `OnMarket` -> `Expired`/`Failed`. Each asset has multi-phase trials (Phase 1/2/3) with cost, duration, and success probability (PTRS).

**MultiAgentGame** (`game/multi_agent_game.py`) is an immutable orchestrator wrapping N GameStates + a SharedMarketState. It handles cross-agent interactions: BD auctions, market share competition, and pipeline leak alerts.

### Environment Architecture

- **Single-agent**: `InvestmentGameEnv` (Gymnasium) -> `GameState.step()`
- **Multi-agent**: `MultiAgentInvestmentGameEnv` (PettingZoo) -> `MultiAgentGame` -> `[GameState, ...]`

Both are created via factory functions in `environment/env_factory.py`.

### Configuration

All environment parameters are driven by a central YAML config (`config.yaml`) validated by a Pydantic `Config` model in `config.py`. Feature flags (e.g. `ta_experience`, `distributional_ptrs`, `pricing`) use `enabled: true/false` — never null/optional. Reward functions and metrics are instantiated dynamically via the `_target_` pattern and `instantiate_from_config()`.

### Key Directories

- `aiml_pyxis_investment_game/` — core package (game logic, environment, agents, config)
- `aiml_pyxis_investment_game/game/` — immutable game state, assets, trials, market state
- `aiml_pyxis_investment_game/environment/` — Gymnasium/PettingZoo wrappers, reward, metrics, evaluation
- `aiml_pyxis_investment_game/agents/` — agent implementations (Pyxie, Knapsack, etc.)
- `train_multi_agent/` — multi-agent training scripts with Hydra configs
- `app/` — FastAPI server for the interactive frontend
- `frontend/` — Next.js frontend application
- `tests/` — test suite organised by module
- `rl-environment-assets/` — training and evaluation asset data

## Docker

### Containers

The application runs as three containers orchestrated by Docker Compose:

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `redis` | `redis:7-alpine` | 6379 | Game state cache |
| `backend` | Built from `Dockerfile.backend` | 8000 | FastAPI server |
| `frontend` | Built from `frontend/linux_dockerfile_fe` | 3000 | Next.js app |

### Docker Compose Files

- **`docker-compose.yml`** — Production-like setup. Runs all three services. Includes a PostgreSQL container for game metrics (not used in local dev).
- **`docker-compose.dev.yml`** — Development setup with hot reload. Uses profiles to run subsets:

```bash
# Run everything (frontend + backend + redis)
docker compose -f docker-compose.dev.yml --profile all up --build

# Run just backend + redis (run frontend locally with pnpm dev)
docker compose -f docker-compose.dev.yml --profile backend up --build

# Run just infrastructure (redis only)
docker compose -f docker-compose.dev.yml up
```

### Environment Variables

The backend environment variables are managed by `app/settings.py`, a Pydantic `BaseSettings` model with the `APP_` prefix. This means any field on the `Settings` class can be overridden by setting `APP_<FIELD_NAME>` as an environment variable (e.g. `APP_REDIS_HOST=redis`). The settings also include Azure configuration (Key Vault, Storage Account, managed identity) and CORS/auth middleware URLs for deployed environments.

#### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_REDIS_HOST` | `redis` | Redis hostname |
| `APP_REDIS_PORT` | `6379` | Redis port |
| `APP_REDIS_DB` | `0` | Redis database index |
| `APP_USE_LOCAL_REDIS` | `"true"` | Use local Redis (vs Azure Cache) |
| `APP_DISABLE_AUTH_MIDDLEWARE` | `"true"` | Disable Azure AD auth for local dev |
| `TESTING` | `"1"` | Use SQLite instead of PostgreSQL |
| `PORTFOLIO_DB_PATH` | `/app/data/game_metrics.db` | SQLite database path |
| `APP_GAME_ASSETS_DIR` | — | Override game assets directory |

#### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` | Backend API URL |
| `NEXT_PUBLIC_BACKEND_URL_GAME` | `http://localhost:8000` | Game-specific API URL |
| `NEXT_PUBLIC_ENABLE_SINGLE_PLAYER` | `"false"` | Show single-player mode in UI |
| `NEXT_PUBLIC_AZURE_CLIENT_ID` | — | Azure AD client ID (auth) |
| `NEXT_PUBLIC_AZURE_AUTHORITY` | — | Azure AD authority URL (auth) |

## Running the API Server

### Redis Setup

Set up Redis locally. On macOS:

```bash
# Install redis-stack
brew tap redis-stack/redis-stack
brew install --cask redis-stack

# Start redis-stack
redis-stack-server
```

For other platforms, consult the [Redis docs](https://redis.io/learn/howtos/quick-start).

### Starting the Server

1. In a terminal, start the Redis server:

```bash
redis-server
```

2. In another terminal, start the FastAPI app:

```bash
APP_DISABLE_AUTH_MIDDLEWARE=1 uvicorn app.app:app --reload --port 8000
```

### SwaggerDocs

Go to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in your browser to access the Swagger UI.

### Troubleshooting

If you get `Address already in use` when starting Redis or uvicorn, find and kill the existing process:

```bash
lsof -i :6379   # or :8000 for uvicorn
kill -9 <PID>
```

### References

- <https://stackoverflow.com/questions/65686318/sharing-python-objects-across-multiple-workers/65699375#65699375>
- <https://github.com/aio-libs/aiocache?tab=readme-ov-file#documentation>
- <https://redis.io/learn/develop/python/fastapi>

## Contributing

Install the `dev` dependencies:

```bash
uv sync --extra dev
```

If you want to contribute to the `app`, `asset_gen`, or `experiments`, you will need to install additional dependencies via their respective extras.

### Pre-commit

Install pre-commit hooks to ensure code quality:

```bash
pre-commit install
```

This will run linting and formatting checks on your code before each commit.
