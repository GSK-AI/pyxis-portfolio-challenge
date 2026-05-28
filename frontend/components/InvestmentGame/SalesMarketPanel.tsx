"use client";

import type { IndicationMarket } from "@/lib/definitionsGameZ";
import { InformationButton } from "@/components/InformationButton";

const SALES_MARKET_INFO = `The sales market tracks competition across indications. Your drug revenue depends on your market share in each indication.

First-Mover Exclusivity:
The first company to launch a drug in an indication gets a period of exclusive sales — no competitors can earn revenue in that indication during this window. This is shown as "Exclusivity" remaining years.

• Green cards: You have exclusivity — full revenue, no competition
• Red cards: A competitor has exclusivity — your drugs earn nothing here
• Yellow cards: Shared market, no exclusivity active

Post-Exclusivity Market Shares:
Once exclusivity expires, revenue is split based on drug quality:
• Drug quality = peak revenue × tenure bonus (longer on market = higher quality)
• The first mover's drug is guaranteed a 30% share; the remaining 70% is split proportionally by quality

Strategy Tips:
• Racing to be first in a high-value indication gives you monopoly revenue
• Launching in an indication where a competitor has exclusivity wastes your drug's early years
• Multiple drugs in the same indication increase your share but face diminishing returns`;

export default function SalesMarketPanel({
  indicationMarkets,
  playerAgentName,
}: {
  indicationMarkets: IndicationMarket[];
  playerAgentName: string;
}) {
  // Only show indications with active drugs on the market
  const active = indicationMarkets.filter((m) => {
    const totalDrugs = Object.values(m.active_drugs).reduce((s, v) => s + v, 0);
    return totalDrugs > 0;
  });

  if (active.length === 0) {
    return (
      <div className="flex h-[460px] flex-col rounded-lg border border-gray-200 bg-white p-4">
        <div className="mb-2 flex items-center gap-1">
          <h3 className="text-sm font-semibold text-gray-700">Sales Market</h3>
          <InformationButton
            title="Sales Market — Indication Competition"
            description={SALES_MARKET_INFO}
          />
        </div>
        <p className="text-xs text-gray-400">No drugs on the market yet</p>
      </div>
    );
  }

  // Sort by TA then indication name
  const sorted = [...active].sort((a, b) => {
    const taCmp = a.therapeutic_area.localeCompare(b.therapeutic_area);
    if (taCmp !== 0) return taCmp;
    return a.indication_name.localeCompare(b.indication_name);
  });

  return (
    <div className="flex h-[460px] flex-col rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-1">
        <h3 className="text-sm font-semibold text-gray-700">Sales Market</h3>
        <InformationButton
          title="Sales Market — Indication Competition"
          description={SALES_MARKET_INFO}
        />
      </div>
      <div className="flex flex-1 flex-col gap-3 overflow-y-auto">
        {sorted.map((market) => {
          const playerDrugs = market.active_drugs[playerAgentName] || 0;
          const competitorDrugs = Object.entries(market.active_drugs)
            .filter(([agent]) => agent !== playerAgentName)
            .reduce((sum, [, count]) => sum + count, 0);
          const totalDrugs = playerDrugs + competitorDrugs;

          const isPlayerFirstMover =
            market.first_mover_agent === playerAgentName;
          const hasExclusivity = market.exclusivity_remaining > 0;
          const competitorHasExclusivity =
            hasExclusivity && !isPlayerFirstMover;

          let cardStyle = "border-gray-150 bg-gray-50";
          if (isPlayerFirstMover && hasExclusivity) {
            cardStyle = "border-green-300 bg-green-50";
          } else if (competitorHasExclusivity) {
            cardStyle = "border-red-300 bg-red-50";
          } else if (totalDrugs > 0) {
            cardStyle = "border-yellow-300 bg-yellow-50";
          }

          const firstMoverLabel = market.first_mover_agent
            ? market.first_mover_agent === playerAgentName
              ? "You"
              : market.first_mover_agent
            : null;

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
                {totalDrugs > 0 && (
                  <span className="text-xs font-semibold text-gray-700">
                    {(market.player_market_share * 100).toFixed(0)}% share
                  </span>
                )}
              </div>
              <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-600">
                {firstMoverLabel && (
                  <span>
                    First Mover:{" "}
                    <span className="font-medium">{firstMoverLabel}</span>
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
                <span>
                  Your Drugs: <span className="font-medium">{playerDrugs}</span>
                </span>
                <span>
                  Competitors:{" "}
                  <span className="font-medium">{competitorDrugs}</span>
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
