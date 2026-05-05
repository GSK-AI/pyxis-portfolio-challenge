"use client";

import type { IndicationMarket } from "@/lib/definitionsGameZ";

interface ReplaySalesMarketPanelProps {
  indicationMarkets: IndicationMarket[];
  agentColors: Record<string, string>;
  agentDisplayNames: Record<string, string>;
}

export default function ReplaySalesMarketPanel({
  indicationMarkets,
  agentColors,
  agentDisplayNames,
}: ReplaySalesMarketPanelProps) {
  const active = indicationMarkets.filter((m) => {
    const totalDrugs = Object.values(m.active_drugs).reduce((s, v) => s + v, 0);
    return totalDrugs > 0;
  });

  if (active.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="mb-2 text-sm font-semibold text-gray-700">
          Sales Market
        </h3>
        <p className="text-xs text-gray-400">No drugs on the market yet</p>
      </div>
    );
  }

  const sorted = [...active].sort((a, b) => {
    const taCmp = a.therapeutic_area.localeCompare(b.therapeutic_area);
    if (taCmp !== 0) return taCmp;
    return a.indication_name.localeCompare(b.indication_name);
  });

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Sales Market</h3>
      <div
        className="flex flex-col gap-3 overflow-y-auto"
        style={{ maxHeight: "400px" }}
      >
        {sorted.map((market) => {
          const hasExclusivity = market.exclusivity_remaining > 0;
          const entries = Object.entries(market.active_drugs).filter(
            ([, count]) => count > 0,
          );
          const totalDrugs = entries.reduce((s, [, v]) => s + v, 0);

          // Incumbent from game state (agent owning the first drug in entry_order)
          const incumbentId = market.incumbent_agent;

          // Use real market shares from game data, fall back to drug count ratio
          const marketShares: Record<string, number> = {};
          if (
            market.market_shares &&
            Object.keys(market.market_shares).length > 0
          ) {
            for (const [agentId] of entries) {
              marketShares[agentId] =
                (market.market_shares[agentId] ?? 0) * 100;
            }
          } else {
            for (const [agentId, count] of entries) {
              marketShares[agentId] =
                totalDrugs > 0 ? (count / totalDrugs) * 100 : 0;
            }
          }

          let cardStyle = "border-gray-150 bg-gray-50";
          if (hasExclusivity) {
            cardStyle = "border-green-300 bg-green-50";
          } else if (totalDrugs > 1) {
            cardStyle = "border-yellow-300 bg-yellow-50";
          }

          return (
            <div
              key={`${market.therapeutic_area}:${market.indication}`}
              className={`rounded-lg border p-3 ${cardStyle}`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-semibold capitalize text-gray-800">
                    {market.indication_name}
                  </span>
                  <span className="ml-2 text-[10px] capitalize text-gray-500">
                    {market.therapeutic_area.split(" ")[0]}
                  </span>
                </div>
                <span className="rounded bg-gray-200 px-1.5 py-0.5 text-[10px] font-medium text-gray-700">
                  {totalDrugs} drug{totalDrugs !== 1 ? "s" : ""} on market
                </span>
              </div>

              {/* First mover & exclusivity */}
              <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-600">
                {market.first_mover_agent && (
                  <span>
                    First Mover:{" "}
                    <span
                      className="font-medium"
                      style={{
                        color: agentColors[market.first_mover_agent] || "#333",
                      }}
                    >
                      {agentDisplayNames[market.first_mover_agent] ??
                        market.first_mover_agent}
                    </span>
                  </span>
                )}
                {incumbentId && (
                  <span>
                    Incumbent:{" "}
                    <span
                      className="font-medium"
                      style={{
                        color: agentColors[incumbentId] || "#333",
                      }}
                    >
                      {agentDisplayNames[incumbentId] ?? incumbentId}
                    </span>
                  </span>
                )}
                {hasExclusivity && (
                  <span>
                    Exclusivity:{" "}
                    <span className="font-medium">
                      {market.exclusivity_remaining}y remaining
                    </span>
                  </span>
                )}
              </div>

              {/* Per-agent drug counts + market share */}
              <div className="mt-2 flex flex-col gap-1.5">
                {entries
                  .sort(([, a], [, b]) => b - a)
                  .map(([agentId, count]) => {
                    const share = marketShares[agentId] ?? 0;
                    const isIncumbent = agentId === incumbentId;
                    const color = agentColors[agentId] || "#888";
                    return (
                      <div key={agentId} className="flex items-center gap-2">
                        <span
                          className="h-2 w-2 flex-shrink-0 rounded-full"
                          style={{ backgroundColor: color }}
                        />
                        <span
                          className="w-24 truncate text-[11px] font-medium"
                          style={{ color }}
                        >
                          {agentDisplayNames[agentId] ?? agentId}
                          {isIncumbent && entries.length > 1 && " ★"}
                        </span>
                        <span className="text-[10px] text-gray-600">
                          {count} drug{count !== 1 ? "s" : ""}
                        </span>
                        {/* Market share bar */}
                        <div className="flex flex-1 items-center gap-1">
                          <div className="h-1.5 flex-1 rounded-full bg-gray-200">
                            <div
                              className="h-1.5 rounded-full"
                              style={{
                                width: `${share}%`,
                                backgroundColor: color,
                                opacity: 0.7,
                              }}
                            />
                          </div>
                          <span className="w-8 text-right text-[10px] text-gray-500">
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
    </div>
  );
}
