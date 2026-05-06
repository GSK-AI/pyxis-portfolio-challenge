# GSK Pyxis Portfolio Challenge

## Overview

The Pyxis Portfolio Challenge is a multi-agent reinforcement learning environment for sequential capital allocation under uncertainty. Agents manage a portfolio of R&D assets, each progressing through a multi-phase development pipeline with stochastic outcomes, compounding costs, and long time horizons. The objective is to maximise portfolio value through investment timing, resource allocation, and competitive positioning against other agents.

The environment is highly stochastic, reflecting the reality of R&D pipeline investment where the majority of assets fail and individual outcomes carry outsized financial consequences. Agents face ~80% asset attrition rates, long development timelines where investment outcomes are delayed by multiple phases, and coupled investment decisions where capital committed to one asset constrains all future options. In the multi-agent setting, agents share indication markets, compete for business development acquisitions, and receive noisy intelligence about rival pipelines. Agents must balance exploration (investing in uncertain early-stage assets) against exploitation (scaling proven late-stage assets), while adapting to opponents' strategies in a high-variance environment where robust decision-making under uncertainty is essential.

The repository provides a standardised environment with multiple baseline agents spanning different algorithmic paradigms: a budget-optimising heuristic (knapsack), a reinforcement learning agent trained via MaskablePPO self-play (Pyxie), and stochastic baselines (random, do-nothing). The environment exposes a PettingZoo `ParallelEnv` API, a gym-compatible single-agent training wrapper, and evaluation utilities for head-to-head matchups.

## Play the Game

Before building an agent, you can play the game yourself against a provided AI opponent at [gsk.ai/pyxis-investment-game](https://gsk.ai/pyxis-investment-game). This is the best way to develop an intuition for the environment dynamics — asset pipelines, trial outcomes, cash management, and competitive market timing.

## Getting Started

### Installation

```bash
# From source
uv sync
```

### Quick Start

Run a match from the CLI and generate a replay file:

```bash
uv run pyxis 'knapsack(c12)' random --seed 42 -o replay.json
```

Upload `replay.json` to [gsk.ai/pyxis-investment-game](https://gsk.ai/pyxis-investment-game) to watch the replay in the browser.

Or use the Python API to evaluate agents over multiple episodes:

```python
from aiml_pyxis_investment_game.environment import make_multi_agent_train_env
from aiml_pyxis_investment_game.environment.competition import evaluate

env = make_multi_agent_train_env()
reports, _, _ = evaluate(agents=["knapsack(c12)", "random"], num_episodes=100)
```

### Provided Agents

The following agents are available as named opponents in `env.train()`, `env.run()`, and `evaluate()`, as well as in the interactive frontend:

| Name | API string | Description |
|------|-----------|-------------|
| **Knapsack (cap=12)** | `"knapsack(c12)"` | Budget-optimising heuristic that solves a 0/1 knapsack each step, capped at 12 concurrent investments. Strong baseline. |
| **Pyxie (RL)** | `"pyxie"` | Reinforcement learning agent trained via MaskablePPO self-play. Uses flat observations and action masking. |
| **Random** | `"random"` | Randomly invests in available idle assets each step. Useful as a lower-bound baseline. |
| **Do Nothing** | `"do_nothing"` | Never invests in anything. Useful for testing and as an absolute floor. |

### CLI

Run matches from the command line with `pyxis`. Specify two agents by name or script path:

```bash
# Named agents
uv run pyxis 'knapsack(c12)' random --seed 42

# Custom agent script vs named agent
uv run pyxis ./my_bot.py 'knapsack(c12)' -o replay.json

# Export replay with custom display names
uv run pyxis 'knapsack(c12)' random -o replay.json -n "Alpha" -n "Beta"
```

Custom agent scripts must define a `create_agent(agent_name, **kwargs)` factory function returning a callable with an optional `set_env(env)` method.

## Environment

### Overview

**Game Parameters:**
- 2 agents compete head-to-head
- 100-step horizon
- Starting cash: $10B
- Up to 40 assets in portfolio (equilibrium ~35)
- 15% reinvestment percentage (fraction of on-market revenue reinvested)
- Reward function: net cash flow per step

> **Official competition settings:** 40 asset slots (equilibrium ~35), $10B starting cash, 100-step horizon.

**Asset Pipeline:**
- Assets arrive in one of 3 therapeutic areas (TAs): oncology, respiratory & immunology, vaccines & infectious disease
- Each asset targets a specific indication within its TA (up to 4 indications per TA, 12 total)
- Assets have 3 trial phases (Phase 1, 2, 3) plus a regulatory approval phase
- Each trial phase has a cost, duration, and probability of success (PTRS)
- PTRS values are known upfront — there is no hidden information about asset quality
- Assets that pass all phases reach market and generate revenue until patent expiry
- Most assets fail during trials (~80% attrition)

**Approval Phase:**
- After Phase 3, assets enter regulatory approval (1-3 steps, 85-95% success rate, $50M filing fee)

**Shared Market & Competition:**
- Agents share indication markets — multiple drugs can compete in the same indication
- First mover in an indication gets a 4-step exclusivity period with a 30% revenue bonus
- Market congestion: revenue decreases when multiple drugs compete in the same indication (1/n^2 scaling)
- Pipeline leak alerts: when an opponent advances a trial phase, there's a probability of an intelligence leak (20%/50%/70% for Phase 1→2/2→3/3→Approval)

**Business Development (BD):**
- BD assets appear randomly each step (Poisson λ=1.3, up to 3 per step)
- BD assets are pre-progressed (already in Phase 1, 2, or 3) — buying one skips early development
- Agents bid via auction levels 0-10 (0 = pass, 7 = break-even, 8-10 = overpay for strategic advantage)
- Highest bidder wins; ties broken randomly

### Observation Space

The observation and action space dimensions scale with `max_num_assets`. The competition uses 40 asset slots (equilibrium ~35). All per-asset counts below refer to the configured `max_num_assets`.

**Flat observation** (default): a numpy array whose length depends on `max_num_assets` (1089 with 40 assets).

**Dict observation** (`flatten_obs=False`): a nested dict with these top-level keys:
- `cash` — current cash (float)
- `time` — current step (int)
- `assets` — tuple of `max_num_assets` asset dicts
- `bd_market` — tuple of 3 BD slot dicts
- `indication_markets` — dict of 3 TAs, each with 4 indication dicts
- `alerts` — tuple of 5 alert dicts

**Per-asset features** (13 fields + trials):
- `max_revenue`, `time_until_max_revenue`, `time_until_patent_expiry`
- `pending_trial_phase` (0=none, 1-4=Phase 1/2/3/Approval)
- `time_on_market`, `cost_this_step`, `revenue_this_step`
- `enpv` (expected NPV), `eroi` (expected ROI)
- `state` (0=Idle, 1=InDevelopment, 2=OnMarket, 3=Failed, 4=Expired)
- `ta_index` (0-2), `indication` (0-3)
- `trials` — tuple of 4 trial dicts, each with `cost_remaining`, `time_remaining`, `ptrs`

**Per BD slot** (9 fields): `available`, `max_revenue`, `time_until_max_revenue`, `time_until_patent_expiry`, `ta_index`, `indication`, `enpv`, `trial_phase`, `ptrs`

**Per indication market** (5 fields): `exclusivity_remaining`, `my_avg_share`, `first_mover`, `my_drugs`, `competitor_drugs`

**Per alert** (6 fields): `event_type` (0=drug release, 1=BD deal, 2=pipeline leak), `agent_index`, `ta_index`, `indication`, `age`, `phase`

Empty/padding slots: empty assets have `state=Expired`, empty BD slots have `available=0`, empty alerts have `event_type=-1`.

### Action Space

Actions are dicts with two keys:

```python
action = {
    "investments": np.array([...], dtype=np.int8),   # shape (max_num_assets,), binary 0/1
    "bd_bids": np.array([...], dtype=np.int64),       # shape (3,), values 0-10
}
```

**Investments**: Binary per asset. 1 = invest, 0 = do nothing. Only Idle assets can receive investment — investing starts the asset's next trial phase.

**BD bids**: Per BD slot. 0 = pass, 1-10 = bid level. Bid price = `(level / 7) * eNPV * reinvestment_pct`. Level 7 = break-even. Highest bidder wins.

**Action Masks**: Call `env.action_masks(agent_id)` before each step to get valid actions:

```python
masks = env.action_masks("pharma_0")
# masks["investments"]: shape (max_num_assets,), dtype int8 — 1 = can invest, 0 = cannot
# masks["bd_bids"]: shape (3, 11), dtype bool — [slot][level] = True if affordable
```

Investment mask rules:
- Only Idle assets are investable (state=0)
- Assets are masked if `cash < cost_to_invest` (when `mask_first_order_assets=True`)
- InDevelopment, OnMarket, Failed, Expired, and empty slots are always masked

BD bid mask rules:
- Level 0 (pass) is always valid
- Level k is valid if the agent can afford the bid price
- All levels masked if no BD asset in that slot, agent is bankrupt, or at max assets

Using masks with MaskablePPO or a manual agent:

```python
masks = env.action_masks(agent_id)
# For RL: pass masks to MaskablePPO predict()
# For manual agents: zero out invalid choices
action["investments"] = my_decisions * masks["investments"]
```

## Competition API

### Creating the Environment

```python
from aiml_pyxis_investment_game.environment import make_multi_agent_train_env

env = make_multi_agent_train_env()
```

This creates a PettingZoo `ParallelEnv` from the YAML configuration. Observations are flat numpy arrays by default for faster processing. Pass `flatten_obs=False` if you prefer structured dict observations:

```python
env = make_multi_agent_train_env(flatten_obs=False)
```

### PettingZoo Environment

Use the env directly for advanced training setups (self-play, population-based training, etc.):

```python
obs, infos = env.reset(seed=42)
while env.agents:
    actions = {}
    for agent_id in env.agents:
        actions[agent_id] = my_policy(obs[agent_id])
    obs, rewards, terms, truncs, infos = env.step(actions)
```

### Gym-like Trainer

Call `.train()` on the env to get a single-agent `gym.Env` wrapper. Use `None` to mark your trainee slot and name strings for opponents:

```python
trainer = env.train([None, "knapsack(c12)"])

# Standard gym loop
obs, info = trainer.reset(seed=42)
while True:
    masks = trainer.action_masks()  # for MaskablePPO
    action = my_policy(obs, masks)
    obs, reward, terminated, truncated, info = trainer.step(action)
    if terminated or truncated:
        break
```

You can also pass your own callable as an opponent:

```python
from aiml_pyxis_investment_game.agents import MultiAgentKnapsackAgent

custom_opp = MultiAgentKnapsackAgent(agent_name="pharma_1", capacity=8)
trainer = env.train([None, custom_opp])
```

### Run

Call `.run()` to pit two agents against each other for a single episode. It always captures a full playthrough and returns per-agent metrics — useful for quick head-to-head comparisons and generating replay files. Agents can be name strings or callables, just like `.train()` and `evaluate()`:

```python
per_agent_reports, playthrough = env.run(
    [my_agent, "knapsack(c12)"],
    seed=42,
    flat_obs={0: True},  # my_agent at index 0 expects flat obs
)

# per_agent_reports: {"pharma_0": [...], "pharma_1": [...]}
# playthrough is a PlaythroughData object — serialize to JSON for the replay viewer
playthrough.model_dump_json(indent=2)
```

You can also run two named agents directly:

```python
reports, playthrough = env.run(["knapsack(c12)", "random"], seed=42)

# Save replay to file
with open("replay.json", "w") as f:
    f.write(playthrough.model_dump_json(indent=2))
```

For multi-episode statistical evaluation, use `evaluate()` below instead.

### Evaluate & Metrics

Use the standalone `evaluate()` function. Agents can be strings or callables:

```python
from aiml_pyxis_investment_game.environment.competition import evaluate

per_agent_reports, global_report, playthrough = evaluate(
    agents=[my_agent, "knapsack(c12)"],
    num_episodes=100,
    num_workers=4,
    flat_obs={0: True},  # my_agent expects flat obs
)

# per_agent_reports: {"pharma_0": [...], "pharma_1": [...]}
```

The return value `per_agent_reports` is a dict mapping agent ID to a list of three report groups:

```python
[
    {"PerEvaluationMetrics": [...]},  # Aggregated across all episodes
    {"PerEpisodeMetrics": [...]},     # Per-episode breakdowns
    {"PerStepMetrics": [...]},        # Per-step time series
]
```

Each group contains dicts keyed by metric name. The metrics cover financial performance (cumulative reward, cash, revenue, cost), pipeline state (assets idle/in-development/on-market), competitive position (agent rank, relative eNPV, market share), and head-to-head outcomes (win/loss per episode).

Key metrics for competition scoring:

| Metric | Group | Description |
|--------|-------|-------------|
| `PerEvaluationCumulativeReward` | PerEvaluation | Mean, stdev, min, max of cumulative reward across episodes |
| `PerEvaluationBankruptcyRate` | PerEvaluation | Fraction of episodes ending in bankruptcy |
| `PerEpisodeWinLoss` | PerEpisode | 1.0 = win, 0.0 = loss, 0.5 = draw (based on cumulative reward). Mean across episodes gives win rate. |
| `PerEpisodeCumulativeReward` | PerEpisode | Total reward per episode |

Additional metrics cover BD deal activity (`PerEpisodeBDDealsWon`), first-mover advantage (`PerEpisodeFirstMoverRate`), revenue lost to competition (`PerEpisodeRevenueLostToCompetition`), per-drug profitability (`PerEpisodeInvestmentPnL`), pipeline efficiency (`PerEpisodeAssetLifecycle`), and market share dynamics (`PerStepMeanMarketShare`, `PerStepDrugsOnMarket`). See `config.yaml` for the full list of enabled metrics, or define your own by adding entries to the `evaluation_metrics` list.

## Training Extras

### Self-Play Training

We provide optional self-play wrappers built on Stable-Baselines3 and MaskablePPO — this is how we trained the Pyxie agent. `SelfPlayWrapper` converts the PettingZoo env into a single-agent `gym.Env` where opponents use frozen policy copies, and `OpponentSyncCallback` keeps those copies in sync during training.

```python
from aiml_pyxis_investment_game.environment import make_multi_agent_train_env, SelfPlayWrapper
from aiml_pyxis_investment_game.environment.self_play import OpponentSyncCallback

policy_kwargs = {"net_arch": [256, 256]}

env = make_multi_agent_train_env()
wrapped = SelfPlayWrapper(env, policy_kwargs=policy_kwargs)

# wrapped is a gym.Env with a MultiDiscrete action space and action_masks()
# OpponentSyncCallback keeps opponent policy copies in sync during training
```

See [`self_play.py`](aiml_pyxis_investment_game/environment/self_play.py) for full details.

### How We Trained Pyxie

The [`notebooks/train_pyxie.ipynb`](notebooks/train_pyxie.ipynb) notebook walks through the full training setup we used to produce the shipped Pyxie agent, including hyperparameters, weighted entropy across action dimensions, opponent sync callbacks, and VecNormalize persistence.

## Development

See [README_FOR_DEVS.md](README_FOR_DEVS.md) for developer setup, API server instructions, and contributing guidelines.
