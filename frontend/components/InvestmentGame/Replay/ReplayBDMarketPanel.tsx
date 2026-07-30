"use client";

import type {
  BDAssetType,
  BDAcquisition,
  AgentActionRecord,
} from "@/lib/definitionsGameZ";
import { formatDisplayNumber } from "@/lib/numbers";
import type { ViewMode } from "./useReplayState";

interface ReplayBDMarketPanelProps {
  bdAssets: BDAssetType[];
  lastAcquisitions: Record<string, BDAcquisition[]>;
  agentActions?: Record<string, AgentActionRecord>;
  agentColors: Record<string, string>;
  agentDisplayNames: Record<string, string>;
  viewMode: ViewMode;
}

export default function ReplayBDMarketPanel({
  bdAssets,
  lastAcquisitions,
  agentActions,
  agentColors,
  agentDisplayNames,
  viewMode,
}: ReplayBDMarketPanelProps) {
  const hasAcquisitions = Object.values(lastAcquisitions).some(
    (acqs) => acqs.length > 0,
  );

  return (
    <div className="flex h-[460px] flex-col rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">BD Market</h3>

      {bdAssets.length === 0 && !hasAcquisitions ? (
        <p className="text-xs text-gray-400">No asset available this year</p>
      ) : (
        <div className="flex flex-1 flex-col gap-3 overflow-y-auto">
          {/* Available BD assets */}
          {bdAssets.map((asset) => (
            <div
              key={asset.asset_id}
              className="border-gray-150 rounded-lg border bg-gray-50 p-3"
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
                  <span className="font-medium">
                    {formatDisplayNumber(asset.enpv)}
                  </span>
                </span>
                <span>
                  Max Rev:{" "}
                  <span className="font-medium">
                    {formatDisplayNumber(asset.max_revenue)}
                  </span>
                </span>
                <span>
                  PTRS:{" "}
                  <span className="font-medium">
                    {(asset.ptrs * 100).toFixed(0)}%
                  </span>
                </span>
              </div>

              {/* Action view: show each agent's bid for this specific asset */}
              {viewMode === "action" && agentActions && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {Object.entries(agentActions).map(([agentId, action]) => {
                    // Find the index of this BD asset in the agent's bid list
                    const bidIndex = (action.bd_assets_at_bid ?? []).findIndex(
                      (a) => a.asset_id === asset.asset_id,
                    );
                    const bid =
                      bidIndex >= 0 ? (action.bd_bids?.[bidIndex] ?? 0) : 0;
                    return (
                      <span
                        key={agentId}
                        className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium"
                        style={{
                          backgroundColor: `${agentColors[agentId]}20`,
                          color: agentColors[agentId],
                        }}
                      >
                        <span
                          className="h-1.5 w-1.5 rounded-full"
                          style={{ backgroundColor: agentColors[agentId] }}
                        />
                        {agentDisplayNames[agentId] ?? agentId}:{" "}
                        {bid === 0 ? "No bid" : `Level ${bid}`}
                      </span>
                    );
                  })}
                </div>
              )}
            </div>
          ))}

          {/* Acquisitions from this step */}
          {hasAcquisitions && (
            <div className="mt-1">
              <span className="text-[10px] font-medium uppercase text-gray-500">
                Acquisitions
              </span>
              {Object.entries(lastAcquisitions).map(([agentId, acqs]) =>
                acqs.map((acq, i) => (
                  <div
                    key={`${agentId}-${i}`}
                    className="mt-1 flex items-center gap-2 rounded border border-green-200 bg-green-50 px-2 py-1.5 text-xs"
                  >
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: agentColors[agentId] }}
                    />
                    <span className="font-medium text-green-800">
                      {agentDisplayNames[agentId] ?? agentId}
                    </span>
                    <span className="text-green-700">
                      acquired {acq.name} for {formatDisplayNumber(acq.price)}
                    </span>
                  </div>
                )),
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
