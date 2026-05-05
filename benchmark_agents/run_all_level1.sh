#!/bin/bash

# NOTE: For running the pyxie level1 agent need to select the correct input shape for the environment in config.yaml
#    {
#        "num_assets": 10,
#        "max_num_assets": 20,
#        "horizon": 15,
#        "starting_cash": 10_000_000.0,
#    },

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

echo "Running random benchmark..."
python "${SCRIPT_DIR}/benchmark.py" random --output "$OUTPUT/random.json" --flatten_obs False

echo "Running random benchmark cash wrapper..."
python "${SCRIPT_DIR}/benchmark.py" random_cash_wrapper --output "$OUTPUT/random_cash_wrapper.json" --flatten_obs False

echo "Running legacy_pyxie_level1 benchmark..."
python "${SCRIPT_DIR}/benchmark.py" legacy_pyxie_level1 --output "$OUTPUT/legacy_pyxie_level1.json"

echo "Running legacy_pyxie_level1_model_sample benchmark..."
python "${SCRIPT_DIR}/benchmark.py" legacy_pyxie_level1_model_sample --output "$OUTPUT/legacy_pyxie_level1_model_sample.json"

echo "Running knapsack benchmark..."
python "${SCRIPT_DIR}/benchmark.py" legacy_knapsack_agent --output "$OUTPUT/knapsack.json"

echo "Copying evaluation config..."
cp "${SCRIPT_DIR}/../aiml_pyxis_investment_game/config.yaml" "$OUTPUT"

echo "All benchmarks completed successfully."

echo "Plotting"

python compare_agents.py random:$OUTPUT/random.json random_cash_wrapper:$OUTPUT/random_cash_wrapper.json pyxie_level1:$OUTPUT/legacy_pyxie_level1.json pyxie_level1_model_sample:$OUTPUT/legacy_pyxie_level1_model_sample.json knapsack:$OUTPUT/knapsack.json --output-dir $OUTPUT/plots
