import os
from typing import Any

import click
import matplotlib.pyplot as plt
from loading import (
    load_per_episode_metrics,
    load_per_evaluation_metrics,
    load_per_step_metrics_multi_index,
)
from plotting import (
    create_comparison_table,
    plot_distribution_hist,
    plot_per_step_timeseries,
)

from aiml_pyxis_investment_game.file_io import load_json


def compare_per_evaluation_metrics(
    names_to_results: dict[str, Any],
):
    """Compare the results of multiple agents by creating table figures."""
    per_evaluation_names_dfs = {
        name: load_per_evaluation_metrics(load_json(results_file))
        for name, results_file in names_to_results.items()
    }

    title_pre = "_v_".join(list(per_evaluation_names_dfs.keys()))
    title = f"PerEvaluationMetrics_{title_pre}"

    fig, _ = create_comparison_table(
        dfs=list(per_evaluation_names_dfs.values()),
        agent_names=list(per_evaluation_names_dfs.keys()),
        title=title,
    )
    return fig


def compare_per_episode_metrics(
    names_to_results: dict[str, Any],
):
    """Compare the results of multiple agents by creating figures."""
    per_episode_names_dfs = {
        name: load_per_episode_metrics(load_json(results_file))
        for name, results_file in names_to_results.items()
    }

    title_pre = "_v_".join(list(per_episode_names_dfs.keys()))

    # special set of kwargs to improve plotting over default params
    plotting_kwargs = {
        "PerEpisodeFinalEnpv.value": {"log_x": False},
        "PerEpisodeFinalEroi.value": {"log_x": False},
        "PerEpisodeRealisedRoi.value": {"log_x": False},
    }

    figs = []
    for column in list(per_episode_names_dfs.values())[0].columns:
        fig, _ = plot_distribution_hist(
            dfs=list(per_episode_names_dfs.values()),
            agent_names=list(per_episode_names_dfs.keys()),
            column=column,
            title=f"{column}_{title_pre}",
            **plotting_kwargs.get(column, {}),
        )
        figs.append(fig)

    return figs


def compare_per_step_metrics(
    names_to_results: dict[str, Any],
):
    """Compare the results of multiple agents by creating figures."""
    per_step_names_dfs = {
        name: load_per_step_metrics_multi_index(load_json(results_file))
        for name, results_file in names_to_results.items()
    }

    title_pre = "_v_".join(list(per_step_names_dfs.keys()))

    # special set of kwargs to improve plotting over default params
    plotting_kwargs = {
        "PerStepEnpv": {"log_y": False},
        "PerStepEroi": {"log_y": False},
    }

    figs = []
    for column in list(per_step_names_dfs.values())[0].columns:
        fig, _ = plot_per_step_timeseries(
            dfs=list(per_step_names_dfs.values()),
            agent_names=list(per_step_names_dfs.keys()),
            metric_name=column,
            title=f"{column}_{title_pre}",
            **plotting_kwargs.get(column, {}),
        )
        figs.append(fig)

    return figs


@click.command()
@click.argument("names_results", nargs=-1)
@click.option("--output-dir", default="./")
def compare_agents(names_results, output_dir):
    """
    Compare the results of multiple agents by creating tables and figures.

    Args:
        names_results: List of agent names and results separated by `:`.
        output_dir: Directory to save the comparison tables.

    """
    os.makedirs(output_dir, exist_ok=True)

    names_to_results: dict = {
        name_result.split(":")[0]: name_result.split(":")[1]
        for name_result in names_results
    }
    per_evaluation_comparison_fig = compare_per_evaluation_metrics(names_to_results)
    per_episode_comparison_figs = compare_per_episode_metrics(names_to_results)
    per_step_comparison_figs = compare_per_step_metrics(names_to_results)

    save_plots(
        [per_evaluation_comparison_fig]
        + per_episode_comparison_figs
        + per_step_comparison_figs,
        path=output_dir,
    )


def save_plots(
    figs: list[plt.Figure],
    path: str,
):
    """Save the figures to a directory by title."""
    for fig in figs:
        fig.get_figure().savefig(f"{path}/{fig.axes[0].get_title()}.png")


if __name__ == "__main__":
    compare_agents()
