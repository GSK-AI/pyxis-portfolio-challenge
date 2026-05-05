import json
import logging
import os

import click
from agents import AGENTS

from aiml_pyxis_investment_game import logging_utils, parallel_evaluate

logging_utils.setup_logging(logging.CRITICAL)


@click.command()
@click.argument("agent")
@click.option("--num_workers", "-n", default=10, type=int)
@click.option("--output", "-o")
@click.option("--flatten_obs", default=None, type=bool)
@click.option("--mask_first_order_assets", default=None, type=bool)
def main(agent, num_workers, output, flatten_obs, mask_first_order_assets):
    """
    Evaluate pre-defined agent with `evaluate` function in source code.

    Args:
        agent (str): Agent name.
        num_workers (int): Number of parallel workers. Defaults to 1.
        output (str): Output json file name.
        flatten_obs (bool): Whether to flatten observations. Defaults to True.
        mask_first_order_assets (bool): Whether to mask first order assets.
         Defaults to False.

    """
    agent_fn = AGENTS[agent]

    results = parallel_evaluate(
        agent_fn,
        num_workers=num_workers,
        flatten_obs=flatten_obs,
        mask_first_order_assets=mask_first_order_assets,
    )

    json_str = json.dumps(results, indent=4)

    if output:
        if len(output.split("/")) > 1:
            os.makedirs(output.split("/")[0], exist_ok=True)
        with open(output, "w") as f:
            f.write(json_str)
    else:
        print(json_str)


if __name__ == "__main__":
    main()
