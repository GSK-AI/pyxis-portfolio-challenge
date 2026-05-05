"use client";

import { useMemo } from "react";
import type {
  AssetSchemaType,
  GameStepSchemaType,
  AgentActionRecord,
  ActionType,
} from "@/lib/definitionsGameZ";
import { extractAllAssets } from "@/lib/game";
import { formatDisplayNumber } from "@/lib/numbers";
import AssetsTable from "../AssetsTable";
import type { ViewMode } from "./useReplayState";
import type { HighlightType } from "@/lib/replay-helpers";

interface AgentPortfolioPanelProps {
  agentId: string;
  displayName?: string;
  agentState: GameStepSchemaType;
  previousAgentState: GameStepSchemaType | null;
  actions: AgentActionRecord | null;
  viewMode: ViewMode;
  changedAssetIds: Map<string, HighlightType>;
  actionHighlightIds: Set<string>;
  color: string;
  cumulativeReward: number;
  reward: number;
}

export default function AgentPortfolioPanel({
  agentId,
  displayName,
  agentState,
  previousAgentState,
  actions,
  viewMode,
  changedAssetIds,
  actionHighlightIds,
  color,
  cumulativeReward,
  reward,
}: AgentPortfolioPanelProps) {
  const allAssets = useMemo(() => extractAllAssets(agentState), [agentState]);

  // Build previous asset state/phase maps for change indicators
  const { previousAssetStates, previousAssetPhases } = useMemo(() => {
    if (!previousAgentState)
      return { previousAssetStates: {}, previousAssetPhases: {} };
    const prevAll = extractAllAssets(previousAgentState);
    const states: Record<string, AssetSchemaType["state"]> = {};
    const phases: Record<string, AssetSchemaType["pending_trial_phase"]> = {};
    prevAll.forEach((asset) => {
      states[asset.id] = asset.state;
      phases[asset.id] = asset.pending_trial_phase;
    });
    return { previousAssetStates: states, previousAssetPhases: phases };
  }, [previousAgentState]);

  // Build selection record
  const selection = useMemo(() => {
    const sel: Record<string, ActionType | boolean> = {};

    if (viewMode === "action" && actions) {
      // Show actual actions taken
      for (const [assetId, decision] of Object.entries(
        actions.investment_decisions,
      )) {
        if (decision === "none" || decision === "stop") {
          sel[assetId] = decision as ActionType;
        } else if (decision === "invest") {
          sel[assetId] = true;
        } else {
          sel[assetId] = decision as ActionType;
        }
      }
    } else {
      // State view: show current development status
      allAssets.forEach((asset) => {
        if (asset.state === "In Development") {
          sel[asset.id] = asset.current_investment_level || true;
        } else {
          sel[asset.id] = false;
        }
      });
    }

    return sel;
  }, [viewMode, actions, allAssets]);

  // Row highlights: state-change highlights (amber/blue) in both views
  // Action highlights are shown via the switch halo instead
  const highlights = changedAssetIds;

  // BD bid summary for action view — one entry per asset bid on
  const bdBidSummaries = useMemo(() => {
    if (viewMode !== "action" || !actions) return [];
    const entries: { bid: number; assetName: string }[] = [];
    const assets = actions.bd_assets_at_bid ?? [];
    for (let i = 0; i < assets.length; i++) {
      const bid = actions.bd_bids[i] ?? 0;
      if (bid > 0) {
        entries.push({ bid, assetName: assets[i].name });
      }
    }
    return entries;
  }, [viewMode, actions]);

  const eNPV = useMemo(() => {
    return allAssets
      .filter((a) => a.state !== "Expired" && a.state !== "Failed")
      .reduce((sum, a) => sum + a.enpv, 0);
  }, [allAssets]);

  return (
    <div
      className="overflow-hidden rounded-lg border bg-white"
      style={{ borderTopWidth: 4, borderTopColor: color }}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b bg-gray-50 px-4 py-2">
        <div className="flex items-center gap-2">
          <div
            className="h-3 w-3 rounded-full"
            style={{ backgroundColor: color }}
          />
          <span className="text-sm font-semibold">
            {displayName ?? agentId}
          </span>
          {agentState.game_ended && (
            <span
              className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${agentState.ended_reason?.includes("horizon") ? "bg-blue-100 text-blue-700" : "bg-red-100 text-red-700"}`}
            >
              {agentState.ended_reason?.includes("horizon")
                ? "Finished"
                : "Bankrupt"}
            </span>
          )}
        </div>
        <div className="flex gap-4 text-[11px] text-gray-600">
          <span>
            Cash:{" "}
            <span className="font-medium">
              {formatDisplayNumber(agentState.cash)}
            </span>
          </span>
          <span>
            eNPV:{" "}
            <span className="font-medium">{formatDisplayNumber(eNPV)}</span>
          </span>
          <span>
            NCF:{" "}
            <span
              className={`font-medium ${cumulativeReward >= 0 ? "text-green-700" : "text-red-600"}`}
            >
              {formatDisplayNumber(cumulativeReward)}
            </span>
          </span>
          {reward !== 0 && (
            <span className="text-gray-400">
              ({reward >= 0 ? "+" : ""}
              {formatDisplayNumber(reward)})
            </span>
          )}
        </div>
      </div>

      {/* Assets Table */}
      <div className="max-h-[400px] overflow-y-auto">
        <AssetsTable
          assets={allAssets}
          selection={selection}
          onAssetSelection={() => {}}
          readOnly={true}
          highlightedAssetIds={highlights}
          actionHighlightIds={
            viewMode === "action" ? actionHighlightIds : undefined
          }
          previousAssetStates={previousAssetStates}
          previousAssetPhases={previousAssetPhases}
          investmentLevelsEnabled={agentState.investment_levels_enabled}
          investmentLevelsConfig={agentState.investment_levels_config ?? null}
          interimObservationsEnabled={agentState.interim_observations_enabled}
          distributionalPtrsEnabled={agentState.distributional_ptrs_enabled}
          hints={{}}
          hintColumnVisible={false}
          selectedAgentName=""
          time={agentState.time}
        />
      </div>

      {/* BD Bid Summary (action view only) */}
      {bdBidSummaries.length > 0 && (
        <div className="border-t bg-blue-50 px-4 py-2 text-xs text-blue-800">
          {bdBidSummaries.map((entry, i) => (
            <div key={i}>
              BD Bid: Level {entry.bid}
              <span className="text-blue-600"> for {entry.assetName}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
