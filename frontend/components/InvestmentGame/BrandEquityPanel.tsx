"use client";

import type { AssetSchemaType } from "@/lib/definitionsGameZ";
import { InformationButton } from "@/components/InformationButton";
import { formatDisplayNumber } from "@/lib/numbers";
import { Sparkles, ArrowDown, ArrowUp } from "lucide-react";

export const BRAND_EQUITY_INFO = `Brand equity is a per-drug quality boost. Spending builds a brand score for a specific drug, which lifts that drug's share of its indication's post-exclusivity market.

How it works:
- Each spend costs a fraction of the drug's peak revenue — bigger drugs cost more to push.
- Spending adds a fixed amount to the drug's brand score, which then decays each year toward a slowly-rising floor, so repeated pushes accumulate lasting brand.
- You can build brand on any live asset (Idle, In Development or On Market) — start early so the drug launches with brand already banked.

Reading a drug's impact:
- Peak revenue = the drug's size, i.e. how much revenue is at stake for the boost.
- Brand = the drug's current brand score (and its floor). The share boost is underdog-weighted: smaller drugs get proportionally more lift per point of brand.`;

// State pill styling. Brand equity applies to every live asset regardless of
// phase (the engine boosts the score for any owned asset), so all three live
// states appear here.
const STATE_STYLES: Record<string, string> = {
  Idle: "bg-gray-100 text-gray-600",
  "In Development": "bg-amber-100 text-amber-700",
  "On Market": "bg-green-100 text-green-700",
};

// One row per active asset (Idle / In Development / On Market). Brand equity is a
// per-asset action; the cost is per-drug (scales with peak revenue) and arrives
// on each asset as `be_cost`.
export default function BrandEquityPanel({
  assets,
  brandEquity,
  onToggle,
  playerCash,
}: {
  assets: AssetSchemaType[];
  brandEquity: Record<string, number>;
  onToggle: (assetId: string) => void;
  playerCash: number;
}) {
  // Preserve the incoming asset order so the rows line up with the main assets
  // table (both derive from the same portfolio ordering); no re-sort by size.
  const ordered = assets;

  const totalCost = ordered.reduce(
    (sum, a) => sum + (brandEquity[a.id] === 1 ? (a.be_cost ?? 0) : 0),
    0,
  );
  const selectedCount = Object.values(brandEquity).filter(
    (v) => v === 1,
  ).length;
  const overCash = totalCost > playerCash;

  return (
    <div className="flex h-[460px] flex-col rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-1">
        <h3 className="text-sm font-semibold text-gray-700">Brand Equity</h3>
        <InformationButton
          title="Brand Equity — Boost a Drug's Share"
          description={BRAND_EQUITY_INFO}
        />
      </div>

      {ordered.length === 0 ? (
        <p className="text-xs text-gray-400">No drugs in your portfolio yet</p>
      ) : (
        <div className="flex flex-1 flex-col gap-2 overflow-y-auto">
          {ordered.map((asset) => {
            const selected = brandEquity[asset.id] === 1;
            const beCost = asset.be_cost ?? 0;
            const canAfford = beCost <= playerCash;
            const brandScore = asset.brand_score ?? 0;
            const brandFloor = asset.brand_score_floor ?? 0;
            // Forward-looking projection: show what this drug's brand score will
            // be *next* step given the current toggle, so the user can preview
            // the impact and decide whether to commit. Selecting the drug shows
            // the push outcome (if_spend); leaving it off shows the decay toward
            // the floor (if_hold). Fall back to the current score when the
            // backend hasn't sent a projection (pre-marketing replay data).
            const projected = selected
              ? (asset.brand_score_if_spend ?? brandScore)
              : (asset.brand_score_if_hold ?? brandScore);
            const delta = projected - brandScore;
            const deltaVisible = Math.abs(delta) >= 0.005;
            const stateStyle =
              STATE_STYLES[asset.state] ?? "bg-gray-100 text-gray-600";
            return (
              <button
                key={asset.id}
                type="button"
                disabled={!canAfford && !selected}
                onClick={() => onToggle(asset.id)}
                className={`flex items-center justify-between gap-2 rounded-md border px-3 py-2 text-left transition-colors ${
                  selected
                    ? "border-rose-500 bg-rose-500 text-white"
                    : canAfford
                      ? "border-gray-200 bg-gray-50 hover:border-rose-300 hover:bg-rose-50"
                      : "border-gray-150 cursor-not-allowed bg-gray-50 opacity-60"
                }`}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`truncate text-xs font-semibold ${selected ? "text-white" : "text-gray-800"}`}
                    >
                      {asset.name}
                    </span>
                    <span
                      className={`whitespace-nowrap rounded px-1 py-0.5 text-[9px] font-medium ${
                        selected ? "bg-rose-400 text-white" : stateStyle
                      }`}
                    >
                      {asset.state}
                    </span>
                  </div>
                  <div
                    className={`mt-0.5 flex flex-wrap gap-x-3 text-[10px] ${selected ? "text-rose-50" : "text-gray-500"}`}
                  >
                    {/* Drug size = revenue at stake; the impact signal for a push. */}
                    <span>
                      Peak rev {formatDisplayNumber(asset.max_revenue)}
                    </span>
                    {/* Brand score now, its launch floor, and a forward-looking
                        preview of next step's score: selecting the drug shows the
                        push outcome, leaving it off shows the decay toward the
                        floor — so the user sees the impact before committing. The
                        floor is a launch property (0 until On Market), so only
                        surface it once it's real rather than "(floor 0.00)" on
                        every pre-launch drug. */}
                    <span className="flex items-center gap-1">
                      Brand {brandScore.toFixed(2)}
                      {brandFloor > 0 && (
                        <span
                          className={
                            selected ? "text-rose-100" : "text-gray-400"
                          }
                        >
                          (floor {brandFloor.toFixed(2)})
                        </span>
                      )}
                      {deltaVisible && (
                        <span
                          className={`flex items-center gap-0.5 font-semibold ${
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
                          {projected.toFixed(2)} next
                        </span>
                      )}
                    </span>
                  </div>
                </div>
                <span
                  className={`flex items-center gap-1 whitespace-nowrap text-[11px] font-medium ${selected ? "text-white" : "text-gray-500"}`}
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  {formatDisplayNumber(beCost)}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Running total */}
      <div className="mt-3 flex items-center justify-between border-t border-gray-100 pt-3 text-[11px]">
        <span className="text-gray-500">
          {selectedCount} drug{selectedCount === 1 ? "" : "s"} boosted
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
