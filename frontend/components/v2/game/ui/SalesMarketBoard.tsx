"use client";

import { LineChart } from "lucide-react";
import type { IndicationMarket } from "@/lib/definitionsGameZ";
import { cn } from "@/lib/utils";
import { EmptyState } from "./EmptyState";

/**
 * Sales Market board (v2 skin, classic logic): one card per indication
 * with drugs on the market. Card tint mirrors the classic traffic light —
 * green: your exclusivity, red: a competitor's, amber: shared market.
 */

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="whitespace-nowrap text-[10px] uppercase tracking-wider text-muted-foreground/70">
        {label}
      </div>
      <div className="text-sm font-bold tabular-nums">{value}</div>
    </div>
  );
}

export function SalesMarketBoard({
  indicationMarkets,
  playerAgentName,
}: {
  indicationMarkets: IndicationMarket[];
  playerAgentName: string;
}) {
  // --- identical logic to the classic SalesMarketPanel ---
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

  if (sorted.length === 0) {
    return (
      <EmptyState
        icon={LineChart}
        message="No drugs on the market yet"
        hint="Markets appear once any player launches a drug"
      />
    );
  }

  return (
    <div className="space-y-3">
      {sorted.map((market) => {
        const playerDrugs = market.active_drugs[playerAgentName] || 0;
        const competitorDrugs = Object.entries(market.active_drugs)
          .filter(([agent]) => agent !== playerAgentName)
          .reduce((sum, [, count]) => sum + count, 0);
        const totalDrugs = playerDrugs + competitorDrugs;

        const isPlayerFirstMover = market.first_mover_agent === playerAgentName;
        const hasExclusivity = market.exclusivity_remaining > 0;
        const competitorHasExclusivity = hasExclusivity && !isPlayerFirstMover;

        const cardStyle =
          isPlayerFirstMover && hasExclusivity
            ? "bg-gradient-to-r from-[#e0f3e6] to-[#f2faf4]"
            : competitorHasExclusivity
              ? "bg-gradient-to-r from-[#fbe9e7] to-[#fdf6f5]"
              : totalDrugs > 0
                ? "bg-gradient-to-r from-[#fff3cd] to-[#fffaf0]"
                : "bg-secondary/40";

        const stateLabel =
          isPlayerFirstMover && hasExclusivity
            ? { text: "Your exclusivity", className: "text-[#2f7d3f]" }
            : competitorHasExclusivity
              ? {
                  text: "Competitor exclusivity",
                  className: "text-destructive",
                }
              : { text: "Shared market", className: "text-[#8a6d00]" };

        const firstMoverLabel = market.first_mover_agent
          ? market.first_mover_agent === playerAgentName
            ? "You"
            : market.first_mover_agent
          : "—";

        return (
          <div
            key={`${market.therapeutic_area}:${market.indication}`}
            className={cn("space-y-3 rounded p-4", cardStyle)}
          >
            <div className="flex items-start gap-2">
              <div className="min-w-0">
                <div className="text-sm font-bold capitalize">
                  {market.indication_name}
                </div>
                <div className="truncate text-xs capitalize text-muted-foreground">
                  {market.therapeutic_area}
                  {" · "}
                  <span className={cn("font-bold", stateLabel.className)}>
                    {stateLabel.text}
                  </span>
                </div>
              </div>
              {totalDrugs > 0 && (
                <span className="ml-auto whitespace-nowrap text-sm font-bold tabular-nums">
                  {(market.player_market_share * 100).toFixed(0)}% share
                </span>
              )}
            </div>

            <div className="flex items-baseline justify-between gap-3">
              <Metric label="First Mover" value={firstMoverLabel} />
              <Metric
                label="Exclusivity"
                value={
                  hasExclusivity ? `${market.exclusivity_remaining}y` : "—"
                }
              />
              <Metric label="Your Drugs" value={playerDrugs} />
              <Metric label="Competitors" value={competitorDrugs} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
