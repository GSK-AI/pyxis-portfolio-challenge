"""
Analyze effective eNPV of all drugs using current config settings.

eNPV already includes trial_cost_multiplier (applied at asset construction).
Also computes effective profitability: whether lifetime revenue * reinvestment_pct
covers total trial costs, per drug.
"""

import numpy as np
from upath import UPath

from aiml_pyxis_investment_game.config import config
from aiml_pyxis_investment_game.game.asset_generators import JSONAssetGenerator
from aiml_pyxis_investment_game.game.constants import DISCOUNT_RATE

cfg = config

print(f"Config: reinvestment_pct={cfg.reinvestment_percentage}, "
      f"trial_cost_mult={cfg.trial_cost_multiplier}, "
      f"DISCOUNT_RATE={DISCOUNT_RATE:.4f}")
print(f"Assets dir: {cfg.evaluation_data_dir}\n")

generator = JSONAssetGenerator(
    global_seed=0,
    assets_dir=UPath(cfg.evaluation_data_dir),
    indication_spread=cfg.multi_agent.indication_spread,
    indication_drift_speed=cfg.multi_agent.indication_drift_speed,
    trial_cost_multiplier=cfg.trial_cost_multiplier,
    approval_phase_config=cfg.approval_phase,
)

# Load both initial and new assets
initial_assets = generator(num_assets=100, stage="initial")
new_assets = generator(num_assets=100, stage="new")

reinv = cfg.reinvestment_percentage

for label, assets in [("INITIAL", initial_assets), ("NEW", new_assets)]:
    print(f"{'='*80}")
    print(f"  {label} ASSETS (n={len(assets)})")
    print(f"{'='*80}")

    enpvs = []
    total_costs = []
    total_revs = []
    effective_profitable = 0

    rows = []
    for asset in assets.values():
        enpv = asset.enpv
        enpvs.append(enpv)

        exp_costs, exp_revs = asset.expected_costs_and_revenues
        total_cost = sum(exp_costs)
        total_rev = sum(exp_revs)
        effective_rev = total_rev * reinv
        profitable = effective_rev > total_cost
        if profitable:
            effective_profitable += 1

        total_costs.append(total_cost)
        total_revs.append(total_rev)

        rows.append((asset.name, asset.therapeutic_area, enpv, total_cost,
                      total_rev, effective_rev, profitable))

    enpvs = np.array(enpvs)
    total_costs = np.array(total_costs)
    total_revs = np.array(total_revs)

    n = len(enpvs)
    print(f"\n  eNPV (includes trial_cost_multiplier={cfg.trial_cost_multiplier}):")
    print(f"    Positive: {np.sum(enpvs > 0)}/{n} ({np.sum(enpvs > 0)/n*100:.0f}%)")
    print(f"    Negative: {np.sum(enpvs <= 0)}/{n} ({np.sum(enpvs <= 0)/n*100:.0f}%)")
    print(f"    Mean: ${np.mean(enpvs)/1e6:.0f}M  Median: ${np.median(enpvs)/1e6:.0f}M")
    print(f"    Min:  ${np.min(enpvs)/1e6:.0f}M  Max: ${np.max(enpvs)/1e6:.0f}M")

    print(f"\n  Effective profitability (revenue * reinv_pct={reinv} vs trial costs):")
    print(f"    Profitable at 100% share: {effective_profitable}/{n} ({effective_profitable/n*100:.0f}%)")

    # Check at different market shares
    for share in [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]:
        profitable_at_share = sum(
            1 for _, _, _, tc, _, _, _ in rows
            if (total_revs[rows.index((_, _, _, tc, _, _, _))] if False else True)
        )
        # Recompute properly
        count = 0
        for _, _, _, tc, tr, _, _ in rows:
            if tr * reinv * share > tc:
                count += 1
        print(f"    Profitable at {share*100:.0f}% share: {count}/{n} ({count/n*100:.0f}%)")

    # Show worst and best drugs
    rows.sort(key=lambda r: r[2])  # sort by enpv
    print("\n  Bottom 10 by eNPV:")
    print(f"    {'Name':<28} {'TA':<12} {'eNPV':>10} {'Cost':>10} {'Rev':>10} {'EffRev':>10} {'Prof'}")
    for name, ta, enpv, tc, tr, er, prof in rows[:10]:
        print(f"    {name:<28} {ta:<12} ${enpv/1e6:>8.0f}M ${tc/1e6:>8.0f}M ${tr/1e6:>8.0f}M ${er/1e6:>8.0f}M {'Y' if prof else 'N'}")

    print("\n  Top 10 by eNPV:")
    for name, ta, enpv, tc, tr, er, prof in rows[-10:]:
        print(f"    {name:<28} {ta:<12} ${enpv/1e6:>8.0f}M ${tc/1e6:>8.0f}M ${tr/1e6:>8.0f}M ${er/1e6:>8.0f}M {'Y' if prof else 'N'}")

    print()
