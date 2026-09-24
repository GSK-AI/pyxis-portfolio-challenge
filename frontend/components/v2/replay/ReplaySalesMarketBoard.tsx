"use client";

import { LineChart, Star } from "lucide-react";
import type { IndicationMarket } from "@/lib/definitionsGameZ";
import { cn } from "@/lib/utils";
import { EmptyState } from "@/components/v2/game/ui/EmptyState";

/**
 * v2 sales market board for the replay viewer (classic
 * ReplaySalesMarketPanel logic): active indication markets with first
 * mover / incumbent / exclusivity and per-agent market-share bars.
 * Traffic-light gradients follow the v2 SalesMarketBoard: green =
 * exclusivity, amber = contested, grey = single player.
 */
export function ReplaySalesMarketBoard({
  indicationMarkets,
  agentColors,
  agentDisplayNames,
}: {
  indicationMarkets: IndicationMarket[];
  agentColors: Record<string, string>;
  agentDisplayNames: Record<string, string>;
}) {
  // --- identical market derivation to the classic panel ---
  const active = indicationMarkets.filter((m) => {
    const totalDrugs = Object.values(m.active_drugs).reduce((s, v) => s + v, 0);
    return totalDrugs > 0;
  });

  const sorted = [...active].sort((a, b) => {
    const taCmp = a.therapeutic_area.localeCompare(b.therapeutic_area);
    if (taCmp !== 0) return taCmp;
    return a.indication_name.localeCompare(b.indication_name);
  });
  // --- end identical logic ---

  if (active.length === 0) {
    return (
      <EmptyState
        icon={LineChart}
        message="No drugs on the market yet"
        hint="Markets appear once a drug launches"
      />
    );
  }

  return (
    <div className="space-y-2">
      {sorted.map((market) => {
        // --- identical share/incumbent logic to the classic panel ---
        const hasExclusivity = market.exclusivity_remaining > 0;
        const entries = Object.entries(market.active_drugs).filter(
          ([, count]) => count > 0,
        );
        const totalDrugs = entries.reduce((s, [, v]) => s + v, 0);
        const incumbentId = market.incumbent_agent;

        const marketShares: Record<string, number> = {};
        if (
          market.market_shares &&
          Object.keys(market.market_shares).length > 0
        ) {
          for (const [agentId] of entries) {
            marketShares[agentId] = (market.market_shares[agentId] ?? 0) * 100;
          }
        } else {
          for (const [agentId, count] of entries) {
            marketShares[agentId] =
              totalDrugs > 0 ? (count / totalDrugs) * 100 : 0;
          }
        }
        // --- end identical logic ---

        return (
          <div
            key={`${market.therapeutic_area}:${market.indication}`}
            className={cn(
              "space-y-2 rounded p-3",
              hasExclusivity
                ? "bg-gradient-to-r from-[#e0f3e6] to-[#f2faf4]"
                : totalDrugs > 1
                  ? "bg-gradient-to-r from-[#fff3cd] to-[#fffaf0]"
                  : "bg-secondary/40",
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <span className="text-sm font-bold capitalize">
                  {market.indication_name}
                </span>
                <span className="ml-2 text-xs capitalize text-muted-foreground">
                  {market.therapeutic_area.split(" ")[0]}
                </span>
              </div>
              <span className="shrink-0 rounded-full bg-card px-2.5 py-0.5 text-xs font-bold text-muted-foreground">
                {totalDrugs} drug{totalDrugs !== 1 ? "s" : ""}
              </span>
            </div>

            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
              {market.first_mover_agent && (
                <span>
                  First mover{" "}
                  <span
                    className="font-bold"
                    style={{
                      color: agentColors[market.first_mover_agent] || undefined,
                    }}
                  >
                    {agentDisplayNames[market.first_mover_agent] ??
                      market.first_mover_agent}
                  </span>
                </span>
              )}
              {incumbentId && (
                <span>
                  Incumbent{" "}
                  <span
                    className="font-bold"
                    style={{ color: agentColors[incumbentId] || undefined }}
                  >
                    {agentDisplayNames[incumbentId] ?? incumbentId}
                  </span>
                </span>
              )}
              {hasExclusivity && (
                <span>
                  Exclusivity{" "}
                  <span className="font-bold text-[#2f7d3f]">
                    {market.exclusivity_remaining}y remaining
                  </span>
                </span>
              )}
            </div>

            {/* Per-agent drug counts + market share */}
            <div className="space-y-1.5">
              {entries
                .sort(([, a], [, b]) => b - a)
                .map(([agentId, count]) => {
                  const share = marketShares[agentId] ?? 0;
                  const isIncumbent = agentId === incumbentId;
                  const color = agentColors[agentId] || "#888";
                  return (
                    <div key={agentId} className="flex items-center gap-2">
                      <span
                        className="size-2 shrink-0 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      <span
                        className="flex w-24 shrink-0 items-center gap-1 truncate text-xs font-bold"
                        style={{ color }}
                      >
                        {agentDisplayNames[agentId] ?? agentId}
                        {isIncumbent && entries.length > 1 && (
                          <Star className="size-3 shrink-0 fill-current" />
                        )}
                      </span>
                      <span className="shrink-0 text-[11px] text-muted-foreground">
                        {count} drug{count !== 1 ? "s" : ""}
                      </span>
                      <div className="flex flex-1 items-center gap-1.5">
                        <div className="h-1.5 flex-1 rounded-full bg-card">
                          <div
                            className="h-1.5 rounded-full"
                            style={{
                              width: `${share}%`,
                              backgroundColor: color,
                              opacity: 0.7,
                            }}
                          />
                        </div>
                        <span className="w-8 shrink-0 text-right text-[11px] tabular-nums text-muted-foreground">
                          {share.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
