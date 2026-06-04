"use client";

import type { BDAssetType } from "@/lib/definitionsGameZ";
import { formatDisplayNumber } from "@/lib/numbers";
import { InformationButton } from "@/components/InformationButton";

const BD_MARKET_INFO = `Each year, Business Development assets may become available for acquisition via sealed-bid auction. Assets appear stochastically. BD assets are more likely to arrive in active indications.

How bidding works:
- You choose a bid level per asset — higher levels cost more but beat lower bids
- All agents submit bids simultaneously (sealed-bid)
- The highest bidder wins the asset and pays their bid amount
- If multiple agents bid the same amount, the winner is chosen randomly

Acquired assets are added to your portfolio and begin trials from the listed phase. If no one bids, the asset is lost.`;

function BDAssetCard({
  asset,
  bidPrices,
  bid,
  playerCash,
  onBidChange,
}: {
  asset: BDAssetType;
  bidPrices: number[];
  bid: number;
  playerCash: number;
  onBidChange: (bidLevel: number) => void;
}) {
  return (
    <div
      className={`rounded-lg border p-3 transition-colors ${
        bid > 0 ? "border-blue-300 bg-blue-50" : "border-gray-150 bg-gray-50"
      }`}
    >
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs font-semibold text-gray-800">
            {asset.name}
          </span>
          <span className="ml-2 text-[10px] capitalize text-gray-500">
            {asset.therapeutic_area.split(" ")[0]}
          </span>
          <span className="ml-1 text-[10px] text-gray-400">
            — {asset.indication_name || "-"}
          </span>
        </div>
        <span className="rounded bg-gray-200 px-1.5 py-0.5 text-[10px] font-medium text-gray-600">
          {asset.trial_phase}
        </span>
      </div>
      <div className="mt-1.5 flex gap-4 text-[11px] text-gray-600">
        <span>
          eNPV:{" "}
          <span className="font-medium">{formatDisplayNumber(asset.enpv)}</span>
        </span>
        <span>
          Max Rev:{" "}
          <span className="font-medium">
            {formatDisplayNumber(asset.max_revenue)}
          </span>
        </span>
        <span>
          PTRS:{" "}
          <span className="font-medium">{(asset.ptrs * 100).toFixed(0)}%</span>
        </span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1">
        <span className="mr-1 text-[10px] text-gray-500">Bid:</span>
        {bidPrices.map((price, level) => {
          const canAfford = level === 0 || price <= playerCash;
          return (
            <button
              key={level}
              onClick={() => onBidChange(level)}
              disabled={!canAfford}
              className={`rounded px-2 py-1 text-[10px] font-medium transition-colors ${
                bid === level
                  ? "bg-blue-600 text-white"
                  : canAfford
                    ? "border border-gray-200 bg-white text-gray-700 hover:bg-gray-100"
                    : "cursor-not-allowed bg-gray-100 text-gray-300"
              }`}
            >
              {level === 0 ? "No Bid" : formatDisplayNumber(price)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function BDMarketPanel({
  bdAssets,
  playerCash,
  bdBids,
  bdBidPrices,
  onBidChange,
}: {
  bdAssets: BDAssetType[];
  playerCash: number;
  bdBids: number[];
  bdBidPrices: number[][];
  onBidChange: (assetIndex: number, bidLevel: number) => void;
}) {
  if (bdAssets.length === 0) {
    return (
      <div className="flex h-[460px] flex-col rounded-lg border border-gray-200 bg-white p-4">
        <div className="mb-2 flex items-center gap-1">
          <h3 className="text-sm font-semibold text-gray-700">BD Market</h3>
          <InformationButton
            title="BD Market — Asset Auctions"
            description={BD_MARKET_INFO}
          />
        </div>
        <p className="text-xs text-gray-400">No assets available this year</p>
      </div>
    );
  }

  return (
    <div className="flex h-[460px] flex-col rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-1">
        <h3 className="text-sm font-semibold text-gray-700">BD Market</h3>
        <InformationButton
          title="BD Market — Asset Auctions"
          description={BD_MARKET_INFO}
        />
      </div>
      <div className="flex flex-1 flex-col gap-2 overflow-y-auto">
        {bdAssets.map((asset, index) => (
          <BDAssetCard
            key={asset.name}
            asset={asset}
            bidPrices={bdBidPrices[index] ?? []}
            bid={bdBids[index] ?? 0}
            playerCash={playerCash}
            onBidChange={(level) => onBidChange(index, level)}
          />
        ))}
      </div>
    </div>
  );
}
