from typing import Any, List

import pandas as pd


def load_per_evaluation_metrics(metrics: list[dict[str, Any]]) -> pd.DataFrame:
    """Loads per-evaluation summary metrics into a single pandas DataFrame."""
    metric_dfs = []
    for metric_data in metrics[0]["PerEvaluationMetrics"]:
        metric_name = list(metric_data.keys())[0]
        records = metric_data[metric_name]
        if not isinstance(records, dict):
            records = {
                episode_name: {"value": value}
                for episode_name, value in records.items()
            }

        metric_df = pd.DataFrame.from_records([records], index=None).reset_index(
            drop=True
        )
        metric_df = metric_df.rename(
            columns={column: f"{metric_name}.{column}" for column in metric_df.columns}
        )
        metric_dfs.append(metric_df)

    return pd.concat(metric_dfs, axis=1)


def load_per_episode_metrics(metrics: list[dict[str, Any]]) -> pd.DataFrame:
    """Loads per-episode metrics into a single pandas DataFrame."""
    metric_dfs = []
    for metric_data in metrics[1]["PerEpisodeMetrics"]:
        metric_name = list(metric_data.keys())[0]
        records = metric_data[metric_name]

        if not isinstance(list(records.values())[0], dict):
            records = {
                episode_name: {"value": value}
                for episode_name, value in records.items()
            }

        metric_df = pd.DataFrame.from_records(records).T.reset_index(drop=True)
        metric_df = metric_df.rename(
            columns={column: f"{metric_name}.{column}" for column in metric_df.columns}
        )
        metric_dfs.append(metric_df)

    return pd.concat(metric_dfs, axis=1)


def load_per_step_metrics_multi_index(metrics: List[dict[str, Any]]) -> pd.DataFrame:
    """Loads per-step time-series metrics into a single pandas DataFrame."""
    metric_dfs = []

    # Assuming the relevant data is in the first element of the metrics list
    for metric_data in metrics[2]["PerStepMetrics"]:
        metric_name = list(metric_data.keys())[0]
        records_by_episode = metric_data[metric_name]

        # Transform the data into a "long" format list of records
        long_format_records = []
        for episode_idx, values in enumerate(records_by_episode.values()):
            for step, value in enumerate(values):
                long_format_records.append({
                    "episode_idx": episode_idx,
                    "step": step,
                    metric_name: value,
                })

        # Create a DataFrame from the long-format records
        if not long_format_records:
            continue

        metric_df = pd.DataFrame(long_format_records)
        metric_df = metric_df.set_index(["episode_idx", "step"])
        metric_dfs.append(metric_df)

    # Concatenate all metric DataFrames horizontally.
    # The shared MultiIndex ensures they align correctly.
    if not metric_dfs:
        return pd.DataFrame()

    return pd.concat(metric_dfs, axis=1)
