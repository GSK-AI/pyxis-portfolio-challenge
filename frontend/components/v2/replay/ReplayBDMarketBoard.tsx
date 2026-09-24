"use client";

import { Handshake } from "lucide-react";
import type {
  AgentActionRecord,
  BDAcquisition,
  BDAssetType,
} from "@/lib/definitionsGameZ";
import type { ViewMode } from "@/components/InvestmentGame/Replay/useReplayState";
import { formatDisplayNumber } from "@/lib/numbers";
import { EmptyState } from "@/components/v2/game/ui/EmptyState";

/**
 * v2 BD market board for the replay viewer (classic ReplayBDMarketPanel
 * logic): assets up for auction this step, each agent's bid in actions
 * view, and this step's acquisitions.
 */

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
        {label}
      </div>
      <div className="text-sm font-bold tabular-nums">{value}</div>
    </div>
  );
}

export function ReplayBDMarketBoard({
  bdAssets,
  lastAcquisitions,
  agentActions,
  agentColors,
  agentDisplayNames,
  viewMode,
}: {
  bdAssets: BDAssetType[];
  lastAcquisitions: Record<string, BDAcquisition[]>;
  agentActions?: Record<string, AgentActionRecord>;
  agentColors: Record<string, string>;
  agentDisplayNames: Record<string, string>;
  viewMode: ViewMode;
}) {
  const hasAcquisitions = Object.values(lastAcquisitions).some(
    (acqs) => acqs.length > 0,
  );

  if (bdAssets.length === 0 && !hasAcquisitions) {
    return (
      <EmptyState
        icon={Handshake}
        message="No asset available this year"
        hint="BD assets come up for auction as the game progresses"
      />
    );
  }

  return (
    <div className="space-y-2">
      {bdAssets.map((asset) => (
        <div
          key={asset.asset_id}
          className="space-y-2.5 rounded bg-secondary/40 p-3"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <span className="text-sm font-bold">{asset.name}</span>
              <span className="ml-2 text-xs capitalize text-muted-foreground">
                {asset.therapeutic_area.split(" ")[0]} —{" "}
                {asset.indication_name || "-"}
              </span>
            </div>
            <span className="shrink-0 rounded-full bg-secondary px-2.5 py-0.5 text-xs font-bold text-muted-foreground">
              {asset.trial_phase}
            </span>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <Metric
              label="Cash eNPV"
              value={formatDisplayNumber(asset.cash_enpv)}
            />
            <Metric label="Biz eNPV" value={formatDisplayNumber(asset.enpv)} />
            <Metric
              label="Max Rev"
              value={formatDisplayNumber(asset.max_revenue)}
            />
            <Metric label="PTRS" value={`${(asset.ptrs * 100).toFixed(0)}%`} />
          </div>

          {/* Actions view: each agent's bid for this asset */}
          {viewMode === "action" && agentActions && (
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(agentActions).map(([agentId, action]) => {
                // --- identical bid lookup to the classic panel ---
                const bidIndex = (action.bd_assets_at_bid ?? []).findIndex(
                  (a) => a.asset_id === asset.asset_id,
                );
                const bid =
                  bidIndex >= 0 ? (action.bd_bids?.[bidIndex] ?? 0) : 0;
                // --- end identical logic ---
                return (
                  <span
                    key={agentId}
                    className="inline-flex items-center gap-1.5 rounded-full bg-card px-2.5 py-0.5 text-[11px] font-bold"
                    style={{ color: agentColors[agentId] }}
                  >
                    <span
                      className="size-1.5 rounded-full"
                      style={{ backgroundColor: agentColors[agentId] }}
                    />
                    {agentDisplayNames[agentId] ?? agentId}:{" "}
                    {bid === 0 ? "No bid" : formatDisplayNumber(bid)}
                  </span>
                );
              })}
            </div>
          )}
        </div>
      ))}

      {/* This step's acquisitions */}
      {hasAcquisitions && (
        <div className="space-y-1.5 pt-1">
          <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">
            Acquisitions
          </div>
          {Object.entries(lastAcquisitions).map(([agentId, acqs]) =>
            acqs.map((acq, i) => (
              <div
                key={`${agentId}-${i}`}
                className="flex items-center gap-2 rounded bg-gradient-to-r from-[#dff4f8] to-[#f0fafc] px-3 py-2 text-xs"
              >
                <span
                  className="size-2 shrink-0 rounded-full"
                  style={{ backgroundColor: agentColors[agentId] }}
                />
                <span className="font-bold text-[#15717d]">
                  {agentDisplayNames[agentId] ?? agentId}
                </span>
                <span className="text-[#15717d]">
                  acquired {acq.name} for {formatDisplayNumber(acq.price)}
                </span>
              </div>
            )),
          )}
        </div>
      )}
    </div>
  );
}
