from typing import List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection


def create_comparison_table(
    dfs: List[pd.DataFrame],
    agent_names: List[str],
    title: str = "Agent Performance Metrics",
):
    """
    Creates a matplotlib figure with a side-by-side comparison table of agent metrics.

    This function automatically removes the 'PerEvaluation' prefix from metric
    names to improve readability.

    Args:
        dfs (List[pd.DataFrame]): A list of single-row DataFrames, one for each agent.
        agent_names (List[str]): A list of names for each agent,
        corresponding to the dfs.
        title (str, optional): The title for the table figure.

    Returns:
        (matplotlib.figure.Figure, matplotlib.axes.Axes): The Figure and
         Axes objects containing the table.

    """
    if len(dfs) != len(agent_names):
        raise ValueError("The number of DataFrames and agent names must be the same.")

    # 1. Combine the single-row dataframes into one summary dataframe
    series_list = [df.iloc[0] for df in dfs if not df.empty]
    if not series_list:
        print("Warning: All input DataFrames are empty. Cannot generate a table.")
        # Return an empty figure
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data to display.", ha="center", va="center")
        ax.axis("off")
        return fig, ax

    summary_df = pd.concat(series_list, axis=1)
    summary_df.columns = agent_names

    # 2. Prepare data for the matplotlib table
    col_labels = summary_df.columns.tolist()

    # --- MODIFICATION: Clean up row labels ---
    original_row_labels = summary_df.index.tolist()
    row_labels = [label.removeprefix("PerEvaluation") for label in original_row_labels]

    # Format the numeric data into strings for display
    cell_text = []
    for row in summary_df.itertuples(index=False):
        cell_text.append([f"{x:.3g}" for x in row])

    # 3. Create the matplotlib figure and table
    # Dynamically adjust figure height based on number of rows
    fig_height = max(4, len(row_labels) * 0.5)
    fig, ax = plt.subplots(figsize=(12, fig_height))
    ax.axis("off")  # Hide the axes
    ax.set_title(title, fontweight="bold", pad=20)

    # Create the table and add it to the axes
    table = ax.table(
        cellText=cell_text,
        rowLabels=row_labels,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
        colWidths=[0.2 for _ in col_labels],  # Adjust column widths if needed
    )

    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.2)  # Scale table to fit figure

    # Style header and row labels
    for (row, col), cell in table.get_celld().items():
        if row == 0 or col == -1:
            cell.set_text_props(weight="bold")
        if row > 0 and col > -1:  # Center align data cells
            cell.set_text_props(ha="center")

    plt.tight_layout()
    return fig, ax


def plot_distribution_hist(
    dfs: List[pd.DataFrame],
    agent_names: List[str],
    column: str,
    n_bins: int = 20,
    title: str = None,
    log_x: bool = False,
):
    """
    Plots and compares probability histograms from a list of DataFrames using ax.hist.

    Args:
        dfs (List[pd.DataFrame]): A list of DataFrames to compare.
        agent_names (List[str]): A list of names for each DataFrame/agent.
        column (str): The name of the column to plot the histogram of.
        n_bins (int): The number of bins for the histogram.
        title (str, optional): The title of the plot. Defaults to the column name.
        log_x (bool): If True, the x-axis is plotted on a logarithmic scale.

    Returns:
        (matplotlib.figure.Figure, matplotlib.axes.Axes): The Figure and Axes objects.

    """
    if len(dfs) != len(agent_names):
        raise ValueError("The number of DataFrames and agent names must be the same.")

    fig, ax = plt.subplots(figsize=(10, 6))

    # 1. Determine unified binning across ALL datasets
    all_data = pd.concat([df[column] for df in dfs if column in df], ignore_index=True)
    if all_data.empty:
        print(f"Warning: No data found for column '{column}' in any data.")
        return fig, ax

    plot_data = all_data
    if log_x:
        plot_data = plot_data[plot_data > 0]
        if plot_data.empty:
            print(
                f"Warning: No positive data for column "
                f"'{column}' to plot on a log scale."
            )
            return fig, ax
        ax.set_xscale("log")

    x_min, x_max = plot_data.min(), plot_data.max()
    bins = (
        np.logspace(np.log10(x_min), np.log10(x_max), n_bins + 1)
        if log_x
        else np.linspace(x_min, x_max, n_bins + 1)
    )

    # 2. Iterate through each DataFrame and plot its histogram
    prop_cycle = plt.rcParams["axes.prop_cycle"]
    colors = prop_cycle.by_key()["color"]

    for i, (df, agent_name) in enumerate(zip(dfs, agent_names)):
        color = colors[i % len(colors)]
        if column not in df:
            print(
                f"Warning: Column '{column}' not in data for agent "
                f"'{agent_name}'. Skipping."
            )
            continue

        subset_data = df[column]
        if log_x:
            subset_data = subset_data[subset_data > 0]
        if subset_data.empty:
            continue

        # --- Plotting using ax.hist ---
        # Create weights to plot a probability histogram (sum of bars = 1)
        n_total = len(subset_data)
        weights = np.ones(n_total) / n_total if n_total > 0 else None

        # ax.hist plots the histogram and returns the raw counts and bins
        counts, _, _ = ax.hist(
            subset_data,
            bins=bins,
            weights=weights,
            histtype="step",
            linewidth=1.5,
            label=f"{agent_name} (μ: {subset_data.mean():.2e},"
            f" σ: {subset_data.std():.2e})",
            color=color,
        )

        # --- Error Bar Calculation and Plotting ---
        # We still need to calculate and plot errors separately.
        # Use the raw counts (which we can get from np.histogram) for Poisson error.
        raw_counts, _ = np.histogram(subset_data, bins=bins)
        errors = np.sqrt(raw_counts) / n_total if n_total > 0 else np.zeros(n_bins)

        bin_centers = (bins[:-1] + bins[1:]) / 2
        if log_x:
            bin_centers = np.sqrt(bins[:-1] * bins[1:])

        ax.errorbar(
            bin_centers,
            counts,
            # 'counts' from ax.hist with weights is actually the probability
            yerr=errors,
            fmt="none",
            capsize=3,
            color=color,
            elinewidth=1,
            alpha=0.6,
        )

    # 3. Final Touches
    ax.legend()
    ax.set_title(title or f"Distribution of {column}")
    ax.set_xlabel(column)
    ax.set_ylabel("Probability")
    ax.grid(True, which="both", linestyle="--", linewidth=0.5)
    ax.set_xlim(bins[0], bins[-1])
    ax.set_ylim(bottom=0)  # Ensure y-axis starts at 0

    plt.tight_layout()
    return fig, ax


def plot_per_step_timeseries(
    dfs: List[pd.DataFrame],
    agent_names: List[str],
    metric_name: str,
    title: str = None,
    show_confidence_interval: bool = True,
    ci_level: float = 1.0,
    show_individual_paths: bool = False,
    log_y: bool = False,
):
    """Plot per step time series with modulated alpha for confidence."""
    if len(dfs) != len(agent_names):
        raise ValueError("The number of DataFrames and agent names must be the same.")

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(12, 10), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    for i, (df, name) in enumerate(zip(dfs, agent_names)):
        color = colors[i % len(colors)]

        # --- Top Plot (Mean, CI, and optional individual paths) ---
        if metric_name not in df.columns:
            print(
                f"Warning: Metric '{metric_name}' not found for agent"
                f" '{name}'. Skipping."
            )
            continue

        # Plot individual episode paths if requested
        if show_individual_paths:
            grouped = df.groupby(level="episode_idx")
            for episode_idx, episode_df in grouped:
                steps = episode_df.index.get_level_values("step").astype(int)
                label = f"{name} (Episodes)" if episode_idx == 0 else None
                ax1.plot(
                    steps,
                    episode_df[metric_name],
                    color=color,
                    alpha=0.15,
                    label=label,
                )

        if show_confidence_interval:
            stats_by_step = df.groupby(level="step")[metric_name].agg(["mean", "std"])
            total_episodes = df.index.get_level_values("episode_idx").nunique()

            if total_episodes > 0:
                entries_per_step = df.groupby(level="step").apply(
                    lambda x: x.index.get_level_values("episode_idx").nunique()
                )
                fraction_remaining = (entries_per_step / total_episodes).reindex(
                    stats_by_step.index, fill_value=0
                )

                steps_int = stats_by_step.index.astype(int)
                mean_series = stats_by_step["mean"]
                std_series = stats_by_step["std"]

                # --- Mean Line with Fading Alpha ---
                points = np.array([steps_int, mean_series]).T.reshape(-1, 1, 2)
                segments = np.concatenate([points[:-1], points[1:]], axis=1)

                # Modulate alpha based on fraction remaining
                # Alpha goes from a max of 1.0 down to a min of 0.1
                alphas = fraction_remaining.values * 0.9 + 0.1
                lc = LineCollection(
                    segments,
                    colors=[(*plt.cm.colors.to_rgb(color), a) for a in alphas],
                    linewidth=2.5,
                    label=f"{name} (Mean)",
                )
                ax1.add_collection(lc)

                # --- Confidence Interval with Fading Alpha ---
                # We plot the CI in segments to vary its alpha
                for j in range(len(steps_int) - 1):
                    s_idx, e_idx = steps_int[j], steps_int[j + 1]
                    alpha_val = alphas[j] * 0.2  # Scale alpha for the fill
                    ax1.fill_between(
                        [s_idx, e_idx],
                        [
                            mean_series.iloc[j] - ci_level * std_series.iloc[j],
                            mean_series.iloc[j + 1] - ci_level * std_series.iloc[j + 1],
                        ],
                        [
                            mean_series.iloc[j] + ci_level * std_series.iloc[j],
                            mean_series.iloc[j + 1] + ci_level * std_series.iloc[j + 1],
                        ],
                        color=color,
                        alpha=alpha_val,
                        linewidth=0.0,
                    )
                # Add a proxy artist for the legend
                ax1.fill(
                    np.nan,
                    np.nan,
                    color=color,
                    alpha=0.2,
                    label=f"{name} (±{ci_level}σ)",
                )

        # --- Bottom Plot (Fraction of Remaining Entries) ---
        total_episodes = df.index.get_level_values("episode_idx").nunique()
        if total_episodes > 0:
            entries_per_step = df.reset_index().groupby("step")["episode_idx"].nunique()
            fraction_remaining = entries_per_step / total_episodes
            ax2.plot(
                fraction_remaining.index.astype(int),
                fraction_remaining.values,
                color=color,
                linestyle="-",
                label=name,
            )

    # --- Final Plot Adjustments ---
    ax1.set_title(title or f"{metric_name}", fontsize=16)
    ax1.set_ylabel(metric_name, fontsize=12)
    ax1.grid(True, which="both", linestyle="--", linewidth=0.5)
    handles, labels = ax1.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    if log_y:
        ax1.set_yscale("log")
    ax1.legend(by_label.values(), by_label.keys())

    ax2.set_title("Fraction of Entries Remaining", fontsize=14)
    ax2.set_xlabel("Step", fontsize=12)
    ax2.set_ylabel("Fraction", fontsize=12)
    ax2.grid(True, which="both", linestyle="--", linewidth=0.5)
    ax2.legend()
    ax2.set_ylim(0, 1.05)

    fig.tight_layout()

    return fig, (ax1, ax2)
