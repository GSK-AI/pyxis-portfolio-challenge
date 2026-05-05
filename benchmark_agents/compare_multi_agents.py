"""
Compare multi-agent benchmark results using the standard plotting pipeline.

Usage:
    python compare_multi_agents.py path/to/benchmark_vs_knapsack.json --output-dir plots/
"""

import json
import os
import tempfile

import click
from compare_agents import (
    compare_per_episode_metrics,
    compare_per_evaluation_metrics,
    compare_per_step_metrics,
    save_plots,
)

from aiml_pyxis_investment_game.file_io import load_json


def _strip_non_numeric_per_step(metrics_list):
    """Remove per-step metrics that contain non-numeric values (e.g. dicts)."""
    per_step = metrics_list[2]["PerStepMetrics"]
    filtered = []
    for metric in per_step:
        name = list(metric.keys())[0]
        episodes = metric[name]
        first_values = list(episodes.values())[0] if episodes else []
        if first_values and isinstance(first_values[0], (int, float)):
            filtered.append(metric)
    metrics_list[2]["PerStepMetrics"] = filtered
    return metrics_list


@click.command()
@click.argument("results_file")
@click.option("--output-dir", "-o", default="./plots")
@click.option(
    "--agent-labels", "-l", default=None,
    help="Comma-separated labels for agents (e.g. 'PPO,Knapsack')",
)
def main(results_file, output_dir, agent_labels):
    """Plot comparison of agents from a multi-agent benchmark JSON."""
    os.makedirs(output_dir, exist_ok=True)

    data = load_json(results_file)

    agent_ids = list(data.keys())
    labels = agent_labels.split(",") if agent_labels else agent_ids

    if len(labels) != len(agent_ids):
        raise ValueError(
            f"Got {len(labels)} labels but {len(agent_ids)} agents in results"
        )

    temp_files = {}
    for agent_id, label in zip(agent_ids, labels):
        metrics = _strip_non_numeric_per_step(data[agent_id])
        tf = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(metrics, tf, default=str)
        tf.close()
        temp_files[label] = tf.name

    try:
        figs = []
        figs.append(compare_per_evaluation_metrics(temp_files))
        figs.extend(compare_per_episode_metrics(temp_files))
        figs.extend(compare_per_step_metrics(temp_files))
        save_plots(figs, path=output_dir)
        print(f"Saved {len(figs)} plots to {output_dir}/")
    finally:
        for tf_path in temp_files.values():
            os.unlink(tf_path)


if __name__ == "__main__":
    main()
