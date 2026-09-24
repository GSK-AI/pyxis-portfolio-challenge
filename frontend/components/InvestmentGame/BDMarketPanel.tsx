"use client";

import type { BDAssetType } from "@/lib/definitionsGameZ";
import { formatDisplayNumber } from "@/lib/numbers";
import { InformationButton } from "@/components/InformationButton";
import ReadingSelect from "./ReadingSelect";

export const BD_MARKET_INFO = `Each year, Business Development assets may become available for acquisition via sealed-bid auction. Assets appear stochastically. BD assets are more likely to arrive in active indications.

How bidding works:
- You enter a cash bid per asset — the amount you're willing to pay to acquire it
- All agents submit bids simultaneously (sealed-bid)
- The highest bidder wins the asset and pays their bid amount
- If multiple agents bid the same amount, the winner is chosen randomly
- Bidding more than your available cash will bankrupt you if you win, so bid within your means

Use the cash-adjusted eNPV as a fair-value guide: bidding much above it overpays, while bidding below it risks losing the auction.

Acquired assets are added to your portfolio and begin trials from the listed phase. If no one bids, the asset is lost.`;

function BDAssetCard({
  asset,
  bid,
  playerCash,
  maxBid,
  onBidChange,
  readingsEnabled,
  readingCount,
  onReadingChange,
}: {
  asset: BDAssetType;
  bid: number;
  playerCash: number;
  maxBid: number;
  onBidChange: (bid: number) => void;
  // PTRS readings (ptrs_readings feature): commission private diligence on this
  // candidate. Off entirely when the feature is disabled or the asset carries no
  // cost curve (no pending trial to read).
  readingsEnabled: boolean;
  readingCount: number;
  onReadingChange: (count: number) => void;
}) {
  const overCash = bid > playerCash;
  const readingCosts = asset.ptrs_reading_costs ?? [];
  const maxReadings = readingCosts.length;
  const showReadings = readingsEnabled && maxReadings > 0;
  const readingCostOf = (count: number): number =>
    count <= 0 ? 0 : (readingCosts[count - 1] ?? 0);
  // Soft affordability guard (the engine itself does not check): the diligence
  // spend competes with the bid for the same cash, so a reading may only grow
  // the selection while its cumulative cost still fits alongside the bid.
  let readingsAffordableUpTo = 0;
  for (let k = 1; k <= maxReadings; k++) {
    if (bid + readingCostOf(k) <= playerCash) readingsAffordableUpTo = k;
    else break;
  }
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
      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] text-gray-600">
        <span title="eNPV with sales scaled by the reinvestment rate (35%).">
          Cash eNPV:{" "}
          <span className="font-semibold text-gray-800">
            {formatDisplayNumber(asset.cash_enpv)}
          </span>
        </span>
        <span
          className="text-gray-400"
          title="Full eNPV with sales unscaled. Context only."
        >
          Business eNPV:{" "}
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
        {/* Effective-readings confidence signal — only meaningful once diligence
            can be bought (feature on and a pending trial exists). */}
        {showReadings && (
          <span title="Precision-weighted number of base-quality readings behind this PTRS estimate.">
            Eff. readings:{" "}
            <span className="font-medium">
              {(asset.ptrs_effective_readings ?? 0).toFixed(1)}
            </span>
          </span>
        )}
      </div>
      <div className="mt-2 flex items-center gap-2">
        <span className="text-[10px] text-gray-500">Bid (£):</span>
        <input
          type="number"
          min={0}
          max={maxBid}
          step={1_000_000}
          value={bid === 0 ? "" : bid}
          placeholder="0"
          onChange={(e) => {
            const raw = Number(e.target.value);
            const clamped = Number.isFinite(raw)
              ? Math.max(0, Math.min(raw, maxBid))
              : 0;
            onBidChange(clamped);
          }}
          className={`w-32 rounded border px-2 py-1 text-[11px] ${
            overCash
              ? "border-red-300 bg-red-50 text-red-700"
              : "border-gray-200 bg-white text-gray-700"
          }`}
        />
        {bid > 0 && (
          <span className="text-[10px] text-gray-500">
            {formatDisplayNumber(bid)}
          </span>
        )}
        {overCash && (
          <span className="text-[10px] font-medium text-red-600">
            exceeds cash
          </span>
        )}
      </div>
      {/* Diligence selector: commission 0..N private readings on this candidate.
          Diligence is private — it sharpens *your* PTRS estimate above without
          revealing it to rival bidders. */}
      {showReadings && (
        <div className="border-gray-150 mt-2 flex items-center gap-2 border-t pt-2">
          <span className="text-[10px] text-gray-500">Diligence:</span>
          <ReadingSelect
            count={readingCount}
            costs={readingCosts}
            affordableUpTo={readingsAffordableUpTo}
            onSet={onReadingChange}
            assetName={asset.name}
          />
        </div>
      )}
    </div>
  );
}

export default function BDMarketPanel({
  bdAssets,
  playerCash,
  bdBids,
  maxBid,
  onBidChange,
  ptrsReadingsEnabled,
  ptrsResearch,
  onReadingChange,
}: {
  bdAssets: BDAssetType[];
  playerCash: number;
  bdBids: number[];
  maxBid: number;
  onBidChange: (assetIndex: number, bid: number) => void;
  // PTRS readings (ptrs_readings feature): whether the diligence stepper is
  // available, the shared per-asset-id reading counts (portfolio + BD live in one
  // record, matching the request head), and its setter keyed by BD asset id.
  ptrsReadingsEnabled: boolean;
  ptrsResearch: Record<string, number>;
  onReadingChange: (assetId: string, count: number) => void;
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
            bid={bdBids[index] ?? 0}
            playerCash={playerCash}
            maxBid={maxBid}
            onBidChange={(bid) => onBidChange(index, bid)}
            readingsEnabled={ptrsReadingsEnabled}
            readingCount={ptrsResearch[asset.asset_id] ?? 0}
            onReadingChange={(count) => onReadingChange(asset.asset_id, count)}
          />
        ))}
      </div>
    </div>
  );
}
