"use client";

import type { IndicationMarket } from "@/lib/definitionsGameZ";
import { InformationButton } from "@/components/InformationButton";
import { formatDisplayNumber } from "@/lib/numbers";
import { TrendingUp, ArrowUp, ArrowDown } from "lucide-react";

export const DEMAND_CREATION_INFO = `Demand creation grows the *whole* market for an indication. Spending tops up a shared demand multiplier that scales revenue for every drug in that indication — yours and your competitors'.

How it works:
- Each spend is a fixed cost (the same for every indication) and adds a fixed boost to the indication's demand multiplier.
- The boost decays slowly each year toward the base (1.0×), so sustained spending compounds into a lasting lift.
- You can size an indication even before you hold a drug there — useful to warm up a market you're about to enter.

Strategy:
- Best where you hold (or will hold) the dominant share, since the lift is shared across all drugs in the indication.
- The multiplier shown is the current market-wide level; watch it climb as you and rivals invest.`;

// One row per indication the player can size. Demand creation is a per-indication
// action (matches the engine's per-indication demand head); the cost is flat
// across indications (anchored to the pool-wide peak revenue), so a single
// dcCost drives every row and the running total.
export default function DemandCreationPanel({
  indicationMarkets,
  demandCreation,
  onToggle,
  dcCost,
  playerCash,
}: {
  indicationMarkets: IndicationMarket[];
  demandCreation: Record<string, number>;
  onToggle: (indicationKey: string) => void;
  dcCost: number;
  playerCash: number;
}) {
  const sorted = [...indicationMarkets].sort((a, b) => {
    const taCmp = a.therapeutic_area.localeCompare(b.therapeutic_area);
    if (taCmp !== 0) return taCmp;
    return a.indication_name.localeCompare(b.indication_name);
  });

  const selectedCount = Object.values(demandCreation).filter(
    (v) => v === 1,
  ).length;
  const totalCost = selectedCount * dcCost;
  const overCash = totalCost > playerCash;

  return (
    <div className="flex h-[460px] flex-col rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-1">
        <h3 className="text-sm font-semibold text-gray-700">Demand Creation</h3>
        <InformationButton
          title="Demand Creation — Grow the Market"
          description={DEMAND_CREATION_INFO}
        />
      </div>

      {sorted.length === 0 ? (
        <p className="text-xs text-gray-400">No indications available</p>
      ) : (
        <div className="flex flex-1 flex-col gap-2 overflow-y-auto">
          {sorted.map((market) => {
            const key = `${market.therapeutic_area}:${market.indication}`;
            const selected = demandCreation[key] === 1;
            const canAfford = dcCost <= playerCash;
            // Forward-looking projection: show what this indication's demand
            // multiplier will be *next* step given the current toggle, so the
            // user can preview the impact before committing. Selecting shows the
            // spend outcome; leaving it off shows decay toward the 1.0 base. Fall
            // back to the current value when the backend sent no projection.
            const current = market.demand_multiplier;
            const projected = selected
              ? (market.demand_multiplier_if_spend ?? current)
              : (market.demand_multiplier_if_hold ?? current);
            const delta = projected - current;
            const deltaVisible = Math.abs(delta) >= 0.005;
            return (
              <button
                key={key}
                type="button"
                disabled={!canAfford && !selected}
                onClick={() => onToggle(key)}
                className={`flex items-center justify-between rounded-md border px-3 py-2 text-left transition-colors ${
                  selected
                    ? "border-cyan-500 bg-cyan-500 text-white"
                    : canAfford
                      ? "border-gray-200 bg-gray-50 hover:border-cyan-300 hover:bg-cyan-50"
                      : "border-gray-150 cursor-not-allowed bg-gray-50 opacity-60"
                }`}
              >
                <div className="min-w-0">
                  <div
                    className={`truncate text-xs font-semibold capitalize ${selected ? "text-white" : "text-gray-800"}`}
                  >
                    {market.indication_name}
                  </div>
                  <div
                    className={`flex items-center gap-1 text-[10px] capitalize ${selected ? "text-cyan-50" : "text-gray-500"}`}
                  >
                    {market.therapeutic_area.split(" ")[0]} · demand{" "}
                    {current.toFixed(2)}×
                    {deltaVisible && (
                      <span
                        className={`flex items-center gap-0.5 font-semibold normal-case ${
                          selected
                            ? "text-white"
                            : delta > 0
                              ? "text-emerald-600"
                              : "text-gray-400"
                        }`}
                      >
                        {delta > 0 ? (
                          <ArrowUp className="h-2.5 w-2.5" />
                        ) : (
                          <ArrowDown className="h-2.5 w-2.5" />
                        )}
                        {projected.toFixed(2)}× next
                      </span>
                    )}
                  </div>
                </div>
                <span
                  className={`flex items-center gap-1 whitespace-nowrap text-[11px] font-medium ${selected ? "text-white" : "text-gray-500"}`}
                >
                  <TrendingUp className="h-3.5 w-3.5" />
                  {formatDisplayNumber(dcCost)}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Running total */}
      <div className="mt-3 flex items-center justify-between border-t border-gray-100 pt-3 text-[11px]">
        <span className="text-gray-500">
          {selectedCount} indication{selectedCount === 1 ? "" : "s"} sized
        </span>
        <span
          className={`font-semibold ${overCash ? "text-red-600" : "text-gray-800"}`}
        >
          {formatDisplayNumber(totalCost)}
          {overCash && <span className="ml-1 font-medium">exceeds cash</span>}
        </span>
      </div>
    </div>
  );
}
