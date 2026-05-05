#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Get the directory where the script is located.
SCRIPT_DIR=$(dirname "$0")

# Check if the output directory argument is provided.
if [ -z "$1" ]; then
  echo "Usage: $0 <output_directory>"
  exit 1
fi

OUTPUT=$1

echo "Creating output directory: $OUTPUT"
mkdir -p "$OUTPUT"

echo "Running random benchmark cash wrapper..."
python "${SCRIPT_DIR}/benchmark.py" random_cash_wrapper --output "$OUTPUT/random_cash_wrapper.json" --flatten_obs False

echo "Running Pyxie interim trial obs benchmark..."
# Use single worker (-n 1) to avoid pickle issues with models containing closures
python "${SCRIPT_DIR}/benchmark.py" pyxie_interim_trial_obs --output "$OUTPUT/pyxie_agent.json" --mask_first_order_assets True -n 1

echo "Running knapsack benchmark..."
python "${SCRIPT_DIR}/benchmark.py" knapsack_agent --output "$OUTPUT/knapsack.json"

echo "Copying evaluation config..."
cp "${SCRIPT_DIR}/../aiml_pyxis_investment_game/config.yaml" "$OUTPUT"

echo "All benchmarks completed successfully."

echo "Plotting"

python compare_agents.py random_cash_wrapper:$OUTPUT/random_cash_wrapper.json knapsack:$OUTPUT/knapsack.json pyxie_agent:$OUTPUT/pyxie_agent.json --output-dir $OUTPUT/plots
