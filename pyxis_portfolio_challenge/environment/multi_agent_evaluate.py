"""Evaluation functions for multi-agent competitive environment."""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Callable

from tqdm import tqdm

from pyxis_portfolio_challenge.config import config, instantiate_from_config
from pyxis_portfolio_challenge.environment.metrics import (
    EvaluationMetric,
    MetricsContext,
    collect_metrics,
    merge_all_metrics,
    report_all_metrics,
)
from pyxis_portfolio_challenge.environment.multi_agent_training_gym import (
    MultiAgentInvestmentGameEnv,
)
from pyxis_portfolio_challenge.environment.playthrough import (
    PlaythroughData,
    StepRecord,
    build_playthrough_data,
    capture_actions,
    capture_agent_states,
    capture_shared_market,
)
from pyxis_portfolio_challenge.environment.warmup_wrapper import (
    MultiAgentWarmupOnResetWrapper,
)
from app.endpoint_datamodels import bd_asset_to_response

logger = logging.getLogger(__name__)


def evaluate_multi_agent(
    agents: dict[str, Callable],
    worker_id: int,
    episodes_per_worker: int,
    env_kwargs: dict[str, Any],
    warmup_steps: int = 0,
    progress_queue=None,
    capture_playthrough: bool = False,
    agent_names: dict[str, str] | None = None,
    seed: int | None = None,
) -> tuple[
    dict[str, list[EvaluationMetric]],
    list[EvaluationMetric],
    PlaythroughData | None,
]:
    """
    Evaluate agents in the multi-agent environment (single worker).

    Args:
        agents: Dict mapping agent_id -> callable(obs) -> action
        worker_id: Worker index for seed calculation.
        episodes_per_worker: Number of episodes this worker evaluates.
        env_kwargs: Keyword arguments to construct MultiAgentInvestmentGameEnv.
        warmup_steps: Number of warmup steps after each reset.
        progress_queue: Optional queue for progress reporting.
        capture_playthrough: If True, capture a full playthrough for replay.
            Only valid with episodes_per_worker=1.
        agent_names: Optional mapping of agent_id -> display name for playthrough data.
        seed: Optional explicit seed. If provided, overrides the
            config-based seed calculation.

    Returns:
        Tuple of:
        - Per-agent metrics: {agent_id: [EvaluationMetric, ...]}
        - Global env metrics: [EvaluationMetric, ...]
        - PlaythroughData if capture_playthrough=True, else None

    """
    if capture_playthrough and episodes_per_worker > 1:
        raise ValueError(
            "Playthrough capture requires exactly 1 episode, "
            f"got episodes_per_worker={episodes_per_worker}"
        )
    cfg = config

    env = MultiAgentInvestmentGameEnv(**env_kwargs)

    if warmup_steps > 0:
        env = MultiAgentWarmupOnResetWrapper(
            env, warmup_steps=warmup_steps, verbose=False
        )

    # Create per-agent metric instances
    agent_metrics: dict[str, list[EvaluationMetric]] = {}
    for agent_id in env.possible_agents:
        agent_metrics[agent_id] = [
            instantiate_from_config(m) for m in cfg.evaluation_metrics
        ]

    # Global metrics for the whole environment
    global_metrics: list[EvaluationMetric] = [
        instantiate_from_config(m) for m in cfg.evaluation_metrics
    ]

    # Begin evaluation
    for metrics_list in agent_metrics.values():
        collect_metrics("on_evaluation_begin", metrics=metrics_list, context=None)
    collect_metrics("on_evaluation_begin", metrics=global_metrics, context=None)

    base_seed = cfg.eval_initial_seed
    for local_idx in range(episodes_per_worker):
        if seed is not None:
            episode_seed = seed
        else:
            global_episode_idx = worker_id * episodes_per_worker + local_idx
            episode_seed = base_seed + global_episode_idx

        observations, infos = env.reset(seed=episode_seed)

        # Capture initial state for playthrough
        playthrough_steps: list[StepRecord] = []
        if capture_playthrough:
            initial_agent_states = capture_agent_states(env.multi_agent_game)
            initial_shared_market = capture_shared_market(env.multi_agent_game)
            use_levels = (
                env.investment_levels_config is not None
                and env.investment_levels_config.enabled
            )

        # Attach env to agents that need it (e.g. for action masks)
        for agent_id, agent in agents.items():
            if callable(getattr(agent, "set_env", None)):
                agent.set_env(env)

        # Begin episode for per-agent metrics
        shared_market = env.multi_agent_game.shared_market
        all_states = env.agent_portfolios
        for agent_id in env.possible_agents:
            game_state = all_states[agent_id]
            ctx = MetricsContext(
                game_state=game_state,
                reward=0.0,
                shared_market_state=shared_market,
                agent_id=agent_id,
                all_agent_states=all_states,
            )
            collect_metrics(
                "on_episode_begin",
                metrics=agent_metrics[agent_id],
                context=ctx,
            )

        episode_rewards = {agent: 0.0 for agent in env.possible_agents}
        episode_steps = 0

        while env.agents:
            actions = {}
            for agent_id in env.agents:
                obs = observations[agent_id]
                actions[agent_id] = agents[agent_id](obs)

            # Capture actions before stepping (for playthrough)
            if capture_playthrough:
                pre_step_bd_assets = [
                    bd_asset_to_response(
                        a, env.multi_agent_game.shared_market.indication_name_map
                    )
                    for a in env.multi_agent_game.shared_market.current_bd_assets
                ]
                captured_actions = capture_actions(
                    actions,
                    env._asset_id_orders,
                    use_levels,
                    pre_step_bd_assets=pre_step_bd_assets,
                )

            observations, rewards, terminations, truncations, infos = env.step(actions)

            for agent_id, agent in agents.items():
                if callable(getattr(agent, "set_env", None)):
                    agent.set_env(env)

            for agent_id, reward in rewards.items():
                episode_rewards[agent_id] += reward

            episode_steps += 1

            # Capture post-step state for playthrough
            if capture_playthrough:
                playthrough_steps.append(
                    StepRecord(
                        step=episode_steps,
                        actions=captured_actions,
                        agent_states=capture_agent_states(env.multi_agent_game),
                        shared_market=capture_shared_market(env.multi_agent_game),
                        rewards={aid: float(r) for aid, r in rewards.items()},
                        cumulative_rewards={
                            aid: float(r) for aid, r in episode_rewards.items()
                        },
                    )
                )

            # Per-agent step metrics
            shared_market = env.multi_agent_game.shared_market
            all_states = env.agent_portfolios
            for agent_id in env.possible_agents:
                game_state = all_states[agent_id]
                # Extract BD bid levels from raw actions
                agent_action = actions.get(agent_id, {})
                bd_bid_levels = None
                if isinstance(agent_action, dict) and "bd_bids" in agent_action:
                    import numpy as np

                    raw = np.asarray(agent_action["bd_bids"])
                    if raw.dtype in (np.int64, np.int32, np.int8):
                        bd_bid_levels = raw.tolist()
                ctx = MetricsContext(
                    game_state=game_state,
                    reward=rewards.get(agent_id, 0.0),
                    shared_market_state=shared_market,
                    agent_id=agent_id,
                    all_agent_states=all_states,
                    bd_bid_levels=bd_bid_levels,
                )
                collect_metrics(
                    "on_step_end",
                    metrics=agent_metrics[agent_id],
                    context=ctx,
                )

            if all(terminations.values()) or all(truncations.values()):
                break

        # End episode for per-agent metrics
        shared_market = env.multi_agent_game.shared_market
        all_states = env.agent_portfolios
        for agent_id in env.possible_agents:
            game_state = all_states[agent_id]
            ctx = MetricsContext(
                game_state=game_state,
                reward=episode_rewards[agent_id],
                shared_market_state=shared_market,
                agent_id=agent_id,
                all_agent_states=all_states,
                all_agent_rewards=episode_rewards,
            )
            collect_metrics(
                "on_episode_end",
                metrics=agent_metrics[agent_id],
                context=ctx,
            )

        if progress_queue is not None:
            progress_queue.put(1)

    # End evaluation
    for metrics_list in agent_metrics.values():
        collect_metrics("on_evaluation_end", metrics=metrics_list, context=None)
    collect_metrics("on_evaluation_end", metrics=global_metrics, context=None)

    # Build playthrough data if capturing
    playthrough: PlaythroughData | None = None
    if capture_playthrough:
        playthrough = build_playthrough_data(
            env=env,
            seed=seed,
            initial_agent_states=initial_agent_states,
            initial_shared_market=initial_shared_market,
            steps=playthrough_steps,
            agent_names=agent_names,
        )

    return agent_metrics, global_metrics, playthrough


def parallel_evaluate_multi_agent(
    agents: dict[str, Callable],
    num_workers: int,
    env_kwargs: dict[str, Any],
    warmup_steps: int = 0,
    capture_playthrough: bool = False,
    agent_names: dict[str, str] | None = None,
    num_episodes: int | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict | None]:
    """
    Evaluate agents in parallel using multiple worker processes.

    Args:
        agents: Dict mapping agent_id -> callable(obs) -> action
        num_workers: Number of parallel workers.
        env_kwargs: Keyword arguments to construct MultiAgentInvestmentGameEnv.
        warmup_steps: Number of warmup steps after each reset.
        capture_playthrough: If True, capture a full playthrough for replay.
            Requires num_eval_episodes=1 and num_workers=1.
        agent_names: Optional mapping of agent_id -> display name for playthrough data.
        num_episodes: Total number of evaluation episodes. If None, uses
            config.num_eval_episodes.

    Returns:
        Tuple of:
        - Per-agent reported metrics: {agent_id: {metric_name: value}}
        - Global reported metrics: {metric_name: value}
        - Playthrough dict (JSON-serializable) if capture_playthrough=True, else None

    """
    cfg = config
    total_episodes = num_episodes if num_episodes is not None else cfg.num_eval_episodes
    episodes_per_worker = total_episodes // num_workers

    if capture_playthrough:
        if total_episodes > 1:
            raise ValueError(
                "Playthrough capture requires num_eval_episodes=1, "
                f"got {total_episodes}"
            )
        if num_workers > 1:
            raise ValueError(
                f"Playthrough capture requires num_workers=1, got {num_workers}"
            )

    if num_workers == 1:
        agent_metrics, global_metrics, playthrough = evaluate_multi_agent(
            agents,
            worker_id=0,
            episodes_per_worker=total_episodes,
            env_kwargs=env_kwargs,
            warmup_steps=warmup_steps,
            capture_playthrough=capture_playthrough,
            agent_names=agent_names,
        )
        per_agent_reports = {}
        for agent_id, metrics in agent_metrics.items():
            per_agent_reports[agent_id] = report_all_metrics(metrics)
        # Global metrics are not populated with episode data in
        # evaluate_multi_agent, so reporting them would fail.
        global_report: list[dict[str, Any]] = []
        playthrough_dict = playthrough.model_dump(mode="json") if playthrough else None
        return per_agent_reports, global_report, playthrough_dict

    with ProcessPoolExecutor(max_workers=num_workers) as pool:
        futures = [
            pool.submit(
                evaluate_multi_agent,
                agents,
                worker_id=i,
                episodes_per_worker=episodes_per_worker,
                env_kwargs=env_kwargs,
                warmup_steps=warmup_steps,
            )
            for i in range(num_workers)
        ]

        all_agent_metrics: dict[str, list[list[EvaluationMetric]]] = {}
        all_global_metrics: list[list[EvaluationMetric]] = []

        with tqdm(total=num_workers, desc="Workers", unit="worker") as pbar:
            for future in as_completed(futures):
                agent_metrics, global_metrics, _ = future.result()
                for agent_id, metrics in agent_metrics.items():
                    if agent_id not in all_agent_metrics:
                        all_agent_metrics[agent_id] = []
                    all_agent_metrics[agent_id].append(metrics)
                all_global_metrics.append(global_metrics)
                pbar.update(1)

    # Merge per-agent metrics across workers
    per_agent_reports = {}
    for agent_id, metrics_lists in all_agent_metrics.items():
        merged = merge_all_metrics(metrics_lists)
        per_agent_reports[agent_id] = report_all_metrics(merged)

    # Global metrics are not populated with episode data in evaluate_multi_agent,
    # so merging them would fail. Return empty global report.
    global_report: list[dict[str, Any]] = []

    return per_agent_reports, global_report, None
