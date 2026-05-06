"""
Hyperparameter sweep for DistributionalMCKAgent.

Scans over:
- stop_threshold: [0.3, 0.4, 0.5, 0.6, 0.7]
- min_ev_to_continue: [0.2e9, 0.3e9, 0.4e9, 0.5e9, 0.6e9]
- confidence_weight: [0.1, 0.2, 0.3, 0.4, 0.5]
"""

import itertools
import json
import logging

from pyxis_portfolio_challenge import logging_utils, parallel_evaluate
from pyxis_portfolio_challenge.agents.knapsack import DistributionalMCKAgent

logging_utils.setup_logging(logging.CRITICAL)


def evaluate_agent(agent, num_workers=5):
    """Evaluate agent and return mean reward and bankruptcy rate."""
    results = parallel_evaluate(agent, num_workers=num_workers)
    metrics = results[0]["PerEvaluationMetrics"]
    mean_reward = metrics[0]["PerEvaluationCumulativeReward"]["mean"]
    bankruptcy_rate = metrics[1]["PerEvaluationBankruptcyRate"]["bankruptcy_rate"]
    return mean_reward, bankruptcy_rate


def main():
    # Hyperparameter grid
    stop_thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
    min_evs = [0.2e9, 0.3e9, 0.4e9, 0.5e9, 0.6e9]
    confidence_weights = [0.0, 0.1, 0.2, 0.3, 0.5]

    results = []
    best_reward = float('-inf')
    best_params = None

    total = len(stop_thresholds) * len(min_evs) * len(confidence_weights)
    count = 0

    for stop_thresh, min_ev, conf_weight in itertools.product(
        stop_thresholds, min_evs, confidence_weights
    ):
        count += 1
        print(f"\n[{count}/{total}] Testing: stop={stop_thresh}, min_ev={min_ev/1e9:.1f}B, conf_weight={conf_weight}")

        agent = DistributionalMCKAgent(
            target_capacity=4,
            stop_threshold=stop_thresh,
            min_ev_to_continue=min_ev,
            confidence_weight=conf_weight,
        )

        try:
            mean_reward, bankruptcy_rate = evaluate_agent(agent)

            result = {
                "stop_threshold": stop_thresh,
                "min_ev_to_continue": min_ev,
                "confidence_weight": conf_weight,
                "mean_reward": mean_reward,
                "bankruptcy_rate": bankruptcy_rate,
            }
            results.append(result)

            print(f"  Reward: {mean_reward/1e9:.2f}B, Bankruptcy: {bankruptcy_rate*100:.0f}%")

            if mean_reward > best_reward:
                best_reward = mean_reward
                best_params = result.copy()
                print("  *** NEW BEST ***")
        except Exception as e:
            print(f"  Error: {e}")

    # Sort by reward
    results.sort(key=lambda x: x["mean_reward"], reverse=True)

    print("\n" + "="*60)
    print("TOP 10 CONFIGURATIONS:")
    print("="*60)
    for i, r in enumerate(results[:10]):
        print(f"{i+1}. Reward: {r['mean_reward']/1e9:.2f}B, Bankr: {r['bankruptcy_rate']*100:.0f}%")
        print(f"   stop={r['stop_threshold']}, min_ev={r['min_ev_to_continue']/1e9:.1f}B, conf={r['confidence_weight']}")

    print("\n" + "="*60)
    print("BEST CONFIGURATION:")
    print("="*60)
    print(f"Reward: {best_params['mean_reward']/1e9:.2f}B")
    print(f"Bankruptcy: {best_params['bankruptcy_rate']*100:.0f}%")
    print(f"stop_threshold: {best_params['stop_threshold']}")
    print(f"min_ev_to_continue: {best_params['min_ev_to_continue']/1e9:.1f}B")
    print(f"confidence_weight: {best_params['confidence_weight']}")

    # Save results
    with open("distributional_mck_sweep_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to distributional_mck_sweep_results.json")


if __name__ == "__main__":
    main()
