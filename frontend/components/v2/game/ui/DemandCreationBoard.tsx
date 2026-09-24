"use client";

import { TrendingUp, ArrowUp, ArrowDown } from "lucide-react";
import type { IndicationMarket } from "@/lib/definitionsGameZ";
import { cn } from "@/lib/utils";
import { formatDisplayNumber } from "@/lib/numbers";
import { EmptyState } from "./EmptyState";

/**
 * Demand Creation board (v2 skin, classic logic): toggle a flat spend per
 * indication to grow that market's shared demand multiplier. Shows the
 * classic forward projection (spend vs decay) before committing.
 */
export function DemandCreationBoard({
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
  // --- identical logic to the classic DemandCreationPanel ---
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
  // --- end identical logic ---

  if (sorted.length === 0) {
    return <EmptyState icon={TrendingUp} message="No indications available" />;
  }

  return (
    <div className="space-y-3">
      {/* Running total */}
      <div className="flex items-center justify-between border-b border-foreground/5 pb-3 text-xs">
        <span className="text-muted-foreground">
          {selectedCount} indication{selectedCount === 1 ? "" : "s"} sized
        </span>
        <span
          className={cn(
            "font-bold tabular-nums",
            overCash ? "text-destructive" : "text-foreground",
          )}
        >
          {formatDisplayNumber(totalCost)}
          {overCash && <span className="ml-1">exceeds cash</span>}
        </span>
      </div>

      <div className="space-y-2">
        {sorted.map((market) => {
          const key = `${market.therapeutic_area}:${market.indication}`;
          const selected = demandCreation[key] === 1;
          const canAfford = dcCost <= playerCash;
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
              className={cn(
                "flex w-full items-center justify-between gap-2 rounded px-3 py-2.5 text-left transition-colors",
                selected
                  ? "bg-primary text-primary-foreground"
                  : canAfford
                    ? "bg-secondary/40 hover:bg-secondary/70"
                    : "cursor-not-allowed bg-secondary/30 opacity-50",
              )}
            >
              <div className="min-w-0">
                <div className="truncate text-sm font-bold capitalize">
                  {market.indication_name}
                </div>
                <div
                  className={cn(
                    "flex items-center gap-1.5 text-xs capitalize",
                    selected
                      ? "text-primary-foreground/80"
                      : "text-muted-foreground",
                  )}
                >
                  {market.therapeutic_area.split(" ")[0]} · demand{" "}
                  {current.toFixed(2)}×
                  {deltaVisible && (
                    <span
                      className={cn(
                        "flex items-center gap-0.5 font-bold normal-case",
                        selected
                          ? "text-primary-foreground"
                          : delta > 0
                            ? "text-[#2f7d3f]"
                            : "text-muted-foreground/60",
                      )}
                    >
                      {delta > 0 ? (
                        <ArrowUp className="size-3" />
                      ) : (
                        <ArrowDown className="size-3" />
                      )}
                      {projected.toFixed(2)}× next
                    </span>
                  )}
                </div>
              </div>
              <span
                className={cn(
                  "flex items-center gap-1.5 whitespace-nowrap text-xs font-bold tabular-nums",
                  selected
                    ? "text-primary-foreground/80"
                    : "text-muted-foreground",
                )}
              >
                <TrendingUp className="size-3.5" />
                {formatDisplayNumber(dcCost)}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
