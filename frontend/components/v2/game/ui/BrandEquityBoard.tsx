"use client";

import { Sparkles, ArrowUp, ArrowDown } from "lucide-react";
import type { AssetSchemaType } from "@/lib/definitionsGameZ";
import { cn } from "@/lib/utils";
import { formatDisplayNumber } from "@/lib/numbers";
import { EmptyState } from "./EmptyState";

/**
 * Brand Equity board (v2 skin, classic logic): per-drug spend toggles that
 * build a brand score. Cost scales with the drug's peak revenue; the
 * classic forward projection (push vs decay) previews next year's score.
 */

const STATE_STYLES: Record<string, string> = {
  Idle: "bg-secondary text-muted-foreground",
  "In Development": "bg-[#fff7e0] text-[#8a6d00]",
  "On Market": "bg-[#e8f6ec] text-[#2f7d3f]",
};

export function BrandEquityBoard({
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
  // --- identical logic to the classic BrandEquityPanel ---
  const ordered = assets;
  const totalCost = ordered.reduce(
    (sum, a) => sum + (brandEquity[a.id] === 1 ? (a.be_cost ?? 0) : 0),
    0,
  );
  const selectedCount = Object.values(brandEquity).filter(
    (v) => v === 1,
  ).length;
  const overCash = totalCost > playerCash;
  // --- end identical logic ---

  if (ordered.length === 0) {
    return (
      <EmptyState icon={Sparkles} message="No drugs in your portfolio yet" />
    );
  }

  return (
    <div className="space-y-3">
      {/* Running total */}
      <div className="flex items-center justify-between border-b border-foreground/5 pb-3 text-xs">
        <span className="text-muted-foreground">
          {selectedCount} drug{selectedCount === 1 ? "" : "s"} boosted
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
        {ordered.map((asset) => {
          const selected = brandEquity[asset.id] === 1;
          const beCost = asset.be_cost ?? 0;
          const canAfford = beCost <= playerCash;
          const brandScore = asset.brand_score ?? 0;
          const brandFloor = asset.brand_score_floor ?? 0;
          const projected = selected
            ? (asset.brand_score_if_spend ?? brandScore)
            : (asset.brand_score_if_hold ?? brandScore);
          const delta = projected - brandScore;
          const deltaVisible = Math.abs(delta) >= 0.005;
          return (
            <button
              key={asset.id}
              type="button"
              disabled={!canAfford && !selected}
              onClick={() => onToggle(asset.id)}
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
                <div className="flex items-center gap-1.5">
                  <span className="truncate text-sm font-bold">
                    {asset.name}
                  </span>
                  <span
                    className={cn(
                      "whitespace-nowrap rounded-full px-2 py-0.5 text-[10px] font-bold",
                      selected
                        ? "bg-primary-foreground/20 text-primary-foreground"
                        : (STATE_STYLES[asset.state] ??
                            "bg-secondary text-muted-foreground"),
                    )}
                  >
                    {asset.state}
                  </span>
                </div>
                <div
                  className={cn(
                    "mt-0.5 flex flex-wrap items-center gap-x-3 text-xs",
                    selected
                      ? "text-primary-foreground/80"
                      : "text-muted-foreground",
                  )}
                >
                  <span>Peak rev {formatDisplayNumber(asset.max_revenue)}</span>
                  <span className="flex items-center gap-1">
                    Brand {brandScore.toFixed(2)}
                    {brandFloor > 0 && (
                      <span className="opacity-70">
                        (floor {brandFloor.toFixed(2)})
                      </span>
                    )}
                    {deltaVisible && (
                      <span
                        className={cn(
                          "flex items-center gap-0.5 font-bold",
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
                        {projected.toFixed(2)} next
                      </span>
                    )}
                  </span>
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
                <Sparkles className="size-3.5" />
                {formatDisplayNumber(beCost)}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
