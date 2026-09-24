"use client";

import { FlaskConical } from "lucide-react";
import type { BDAssetType } from "@/lib/definitionsGameZ";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatDisplayNumber } from "@/lib/numbers";
import { EmptyState } from "./EmptyState";

/**
 * BD Market board (v2 skin, classic logic): sealed-bid auction cards per
 * candidate asset — bid within cash, optional private diligence readings
 * on the asset's cost curve. Logic mirrors the classic BDMarketPanel.
 */

function Metric({
  label,
  value,
  muted = false,
  title,
}: {
  label: string;
  value: string;
  muted?: boolean;
  title?: string;
}) {
  return (
    <div title={title}>
      <div className="whitespace-nowrap text-[10px] uppercase tracking-wider text-muted-foreground/70">
        {label}
      </div>
      <div
        className={cn(
          "text-sm font-bold tabular-nums",
          muted && "font-medium text-muted-foreground",
        )}
      >
        {value}
      </div>
    </div>
  );
}

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
  readingsEnabled: boolean;
  readingCount: number;
  onReadingChange: (count: number) => void;
}) {
  // --- identical logic to the classic BDAssetCard ---
  const overCash = bid > playerCash;
  const readingCosts = asset.ptrs_reading_costs ?? [];
  const maxReadings = readingCosts.length;
  const showReadings = readingsEnabled && maxReadings > 0;
  const readingCostOf = (count: number): number =>
    count <= 0 ? 0 : (readingCosts[count - 1] ?? 0);
  let readingsAffordableUpTo = 0;
  for (let k = 1; k <= maxReadings; k++) {
    if (bid + readingCostOf(k) <= playerCash) readingsAffordableUpTo = k;
    else break;
  }
  // --- end identical logic ---

  return (
    <div
      className={cn(
        "space-y-3 rounded p-4 transition-colors",
        bid > 0
          ? "bg-gradient-to-r from-[#eef4fc] to-[#f7fafd]"
          : "bg-secondary/40",
      )}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0">
          <div className="text-sm font-bold">{asset.name}</div>
          <div className="truncate text-xs capitalize text-muted-foreground">
            {asset.therapeutic_area} — {asset.indication_name || "-"}
          </div>
        </div>
        <span className="ml-auto inline-flex whitespace-nowrap rounded-full bg-secondary px-2.5 py-0.5 text-xs font-bold text-muted-foreground">
          {asset.trial_phase}
        </span>
      </div>

      <div className="flex items-baseline justify-between gap-3">
        <Metric
          label="Cash eNPV"
          value={formatDisplayNumber(asset.cash_enpv)}
          title="eNPV with sales scaled by the reinvestment rate (35%). A fair-value guide for your bid."
        />
        <Metric
          label="Biz eNPV"
          value={formatDisplayNumber(asset.enpv)}
          muted
          title="Full eNPV with sales unscaled. Context only."
        />
        <Metric
          label="Max Rev"
          value={formatDisplayNumber(asset.max_revenue)}
        />
        <Metric label="PTRS" value={`${(asset.ptrs * 100).toFixed(0)}%`} />
        {showReadings && (
          <Metric
            label="Eff. Read"
            value={(asset.ptrs_effective_readings ?? 0).toFixed(1)}
            title="Precision-weighted number of base-quality readings behind this PTRS estimate."
          />
        )}
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Bid (£)</span>
        <Input
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
          className={cn(
            "h-8 w-32 bg-card text-sm",
            overCash && "border-destructive text-destructive",
          )}
        />
        {bid > 0 && (
          <span className="text-xs tabular-nums text-muted-foreground">
            {formatDisplayNumber(bid)}
          </span>
        )}
        {overCash && (
          <span className="text-xs font-bold text-destructive">
            exceeds cash
          </span>
        )}
      </div>

      {/* Private diligence: sharpens your PTRS estimate without revealing
          it to rival bidders. Classic ReadingSelect rules: growth beyond
          affordability is disabled, stepping DOWN is always allowed, and
          the live cost turns red if the selection no longer fits cash. */}
      {showReadings && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Diligence</span>
          <Select
            value={String(readingCount)}
            onValueChange={(value) => onReadingChange(Number(value))}
          >
            <SelectTrigger className="h-7 w-auto gap-1 whitespace-nowrap border-none bg-card px-2 text-xs shadow-none">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="0">0 readings</SelectItem>
              {readingCosts.map((cost, i) => (
                <SelectItem
                  key={i}
                  value={String(i + 1)}
                  disabled={
                    i + 1 > readingCount && i + 1 > readingsAffordableUpTo
                  }
                >
                  {i + 1} reading{i > 0 ? "s" : ""} ·{" "}
                  {formatDisplayNumber(cost)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {readingCount > 0 && (
            <span
              className={cn(
                "text-xs tabular-nums",
                readingCount > readingsAffordableUpTo
                  ? "font-bold text-destructive"
                  : "text-muted-foreground",
              )}
              title={
                readingCount > readingsAffordableUpTo
                  ? "Selected readings exceed your available cash"
                  : undefined
              }
            >
              {formatDisplayNumber(readingCosts[readingCount - 1] ?? 0)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export function BDMarketBoard({
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
  ptrsReadingsEnabled: boolean;
  ptrsResearch: Record<string, number>;
  onReadingChange: (assetId: string, count: number) => void;
}) {
  if (bdAssets.length === 0) {
    return (
      <EmptyState
        icon={FlaskConical}
        message="No assets available this year"
        hint="New assets appear at the start of each year"
      />
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        Sealed-bid auction — highest bidder wins and pays their bid. Use Cash
        eNPV as your fair-value guide.
      </p>
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
  );
}
