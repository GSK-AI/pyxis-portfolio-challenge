"use client";

import { useMemo, useState } from "react";
import type {
  AgentActionRecord,
  GameStepSchemaType,
} from "@/lib/definitionsGameZ";
import type { HighlightType } from "@/lib/replay-helpers";
import type { ViewMode } from "@/components/InvestmentGame/Replay/useReplayState";
import { cn } from "@/lib/utils";
import { formatDisplayNumber } from "@/lib/numbers";
import { extractAllAssets } from "@/lib/game";
import SiteCubes from "@/components/InvestmentGame/SiteCubes";
import { toAssetRow } from "@/components/v2/game/GameExperienceV2";
import {
  AssetTable,
  type AssetTabKey,
  type HighlightFilter,
} from "@/components/v2/game/ui/AssetTable";

/**
 * v2 per-agent portfolio panel for the replay viewer. The view-mode
 * semantics (state = current development status, action = decisions
 * taken this step) and the footer summaries (sites, marketing, PTRS
 * readings, BD bids) are IDENTICAL to the classic AgentPortfolioPanel —
 * presentation moved to the v2 AssetTable with tabs.
 */

function FooterRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded bg-secondary/40 px-3 py-2">
      <span className="shrink-0 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">
        {label}
      </span>
      <div className="flex flex-col items-end gap-0.5 text-xs">{children}</div>
    </div>
  );
}

const QUIET = "text-muted-foreground/50";

export function ReplayPortfolioPanel({
  agentId,
  displayName,
  agentState,
  actions,
  viewMode,
  changedAssetIds,
  color,
  cumulativeReward,
  reward,
  highlightFilter = null,
}: {
  agentId: string;
  displayName?: string;
  agentState: GameStepSchemaType;
  actions: AgentActionRecord | null;
  viewMode: ViewMode;
  changedAssetIds: Map<string, HighlightType>;
  color: string;
  cumulativeReward: number;
  reward: number;
  /** Shared legend filter from the replay page. */
  highlightFilter?: HighlightFilter;
}) {
  const [tab, setTab] = useState<AssetTabKey>("development");

  const allAssets = Object.values(agentState.assets ?? {});

  // --- identical view-mode semantics to the classic panel ---
  // State view: invest reflects current development status. Action view:
  // invest/drop reflect the decision taken from this step; readings show
  // the diligence commissioned per asset.
  const investedNow = (assetId: string, state: string) => {
    if (viewMode === "action") {
      const decision = actions?.investment_decisions[assetId];
      return decision != null && decision !== "none" && decision !== "stop";
    }
    return state === "In Development";
  };
  const droppedNow = (assetId: string) =>
    viewMode === "action" && actions?.investment_decisions[assetId] === "stop";
  const readingsNow = (assetId: string) =>
    viewMode === "action" ? (actions?.ptrs_research?.[assetId] ?? 0) : 0;
  // --- end identical semantics ---

  const rowFor = (asset: (typeof allAssets)[number]) =>
    toAssetRow(
      asset,
      investedNow(asset.id, asset.state),
      readingsNow(asset.id),
      droppedNow(asset.id),
      changedAssetIds.has(asset.id),
      changedAssetIds.get(asset.id) === "bd-acquisition"
        ? "bd"
        : changedAssetIds.get(asset.id) === "changed"
          ? "changed"
          : undefined,
    );

  const devRows = allAssets
    .filter((a) => a.state === "Idle" || a.state === "In Development")
    .map(rowFor);
  const marketRows = allAssets
    .filter((a) => a.state === "On Market")
    .map(rowFor);
  const expiredRows = Object.values(agentState.expired_assets ?? {}).map(
    rowFor,
  );
  const droppedRows = Object.values(agentState.dropped_assets ?? {}).map(
    rowFor,
  );
  const tabRows =
    tab === "development"
      ? devRows
      : tab === "market"
        ? marketRows
        : tab === "expired"
          ? expiredRows
          : droppedRows;

  // --- identical footer summaries to the classic AgentPortfolioPanel ---
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

  const pendingSiteIncoming = useMemo(() => {
    if (!agentState.clinical_sites_enabled || viewMode !== "action" || !actions)
      return 0;
    const idleIds = new Set(
      allAssets.filter((a) => a.state === "Idle").map((a) => a.id),
    );
    let count = 0;
    for (const [assetId, decision] of Object.entries(
      actions.investment_decisions,
    )) {
      if (
        idleIds.has(assetId) &&
        decision !== "none" &&
        decision !== "stop" &&
        decision != null
      ) {
        count++;
      }
    }
    return count;
  }, [agentState.clinical_sites_enabled, viewMode, actions, allAssets]);

  const marketingSummary = useMemo(() => {
    if (viewMode !== "action" || !actions) return { dcNames: [], beNames: [] };
    const indName = new Map<string, string>();
    const assetName = new Map<string, string>();
    allAssets.forEach((a) => {
      indName.set(`${a.therapeutic_area}:${a.indication}`, a.indication_name);
      assetName.set(a.id, a.name);
    });
    const dcNames = Object.entries(actions.demand_creation ?? {})
      .filter(([, v]) => v === 1)
      .map(([k]) => indName.get(k) ?? k);
    const beNames = Object.entries(actions.brand_equity ?? {})
      .filter(([, v]) => v === 1)
      .map(([id]) => assetName.get(id) ?? id.slice(0, 8));
    return { dcNames, beNames };
  }, [viewMode, actions, allAssets]);

  const ptrsReadingsSummary = useMemo(() => {
    if (viewMode !== "action" || !actions) return [];
    const assetName = new Map<string, string>();
    allAssets.forEach((a) => assetName.set(a.id, a.name));
    const lines: { label: string; count: number }[] = [];
    for (const [id, n] of Object.entries(actions.ptrs_research ?? {})) {
      if (n > 0) {
        lines.push({ label: assetName.get(id) ?? id.slice(0, 8), count: n });
      }
    }
    const bdAssets = actions.bd_assets_at_bid ?? [];
    (actions.bd_ptrs_research ?? []).forEach((n, i) => {
      if (n > 0) {
        lines.push({
          label: `${bdAssets[i]?.name ?? `BD #${i + 1}`} (BD)`,
          count: n,
        });
      }
    });
    return lines;
  }, [viewMode, actions, allAssets]);

  const eNPV = useMemo(() => {
    return extractAllAssets(agentState)
      .filter((a) => a.state !== "Expired" && a.state !== "Failed")
      .reduce((sum, a) => sum + a.enpv, 0);
  }, [agentState]);
  // --- end identical footer summaries ---

  const finished = agentState.ended_reason?.includes("horizon");

  return (
    <div className="min-w-0 space-y-3 overflow-hidden rounded bg-secondary/25 p-4">
      {/* Header: identity, metrics left-aligned underneath */}
      <div className="space-y-1.5 pb-2">
        <div className="flex min-w-0 items-center gap-2">
          <span
            className="size-2.5 shrink-0 rounded-full"
            style={{ backgroundColor: color }}
          />
          <span className="truncate text-sm font-bold">
            {displayName ?? agentId}
          </span>
          {agentState.game_ended && (
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                finished
                  ? "bg-[var(--accent-soft)] text-primary"
                  : "bg-[#fdf1f0] text-destructive",
              )}
            >
              {finished ? "Finished" : "Bankrupt"}
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 pl-[18px] text-xs text-muted-foreground">
          <span>
            Cash{" "}
            <span className="font-bold tabular-nums text-foreground">
              {formatDisplayNumber(agentState.cash)}
            </span>
          </span>
          <span>
            eNPV{" "}
            <span className="font-bold tabular-nums text-foreground">
              {formatDisplayNumber(eNPV)}
            </span>
          </span>
          <span>
            NCF{" "}
            <span
              className={cn(
                "font-bold tabular-nums",
                cumulativeReward < 0 ? "text-destructive" : "text-foreground",
              )}
            >
              {formatDisplayNumber(cumulativeReward)}
            </span>
            {reward !== 0 && (
              <span className="text-muted-foreground/60">
                {" "}
                ({reward >= 0 ? "+" : ""}
                {formatDisplayNumber(reward)})
              </span>
            )}
          </span>
        </div>
      </div>

      <AssetTable
        readOnly
        variant="panel"
        highlightFilter={highlightFilter}
        tabs={[
          { key: "development", label: "Development", count: devRows.length },
          { key: "market", label: "On Market", count: marketRows.length },
          { key: "expired", label: "Expired", count: expiredRows.length },
          { key: "dropped", label: "Dropped", count: droppedRows.length },
        ]}
        activeTab={tab}
        onTabChange={setTab}
        rows={tabRows}
        ptrsReadingsEnabled={agentState.ptrs_readings_enabled}
        reinvestmentPercentage={agentState.reinvestment_percentage}
      />

      {/* This-step summaries (classic footer strips) */}
      <div className="space-y-2">
        {agentState.clinical_sites_enabled && (
          <FooterRow label="Sites">
            <div className="flex items-center gap-4">
              <SiteCubes
                sitesOccupied={agentState.sites_occupied}
                freeSites={agentState.free_sites}
                sitesInDevelopment={agentState.sites_in_development}
                incoming={pendingSiteIncoming}
                size="sm"
              />
              {viewMode === "action" && actions && (
                <span className="whitespace-nowrap">
                  {actions.upgrade ? (
                    <span className="font-bold text-[#15717d]">
                      Bought a new site
                    </span>
                  ) : actions.site_bid > 0 ? (
                    <span className="font-bold text-primary">
                      Site bid: {formatDisplayNumber(actions.site_bid)}
                    </span>
                  ) : (
                    <span className={QUIET}>No site action</span>
                  )}
                </span>
              )}
            </div>
          </FooterRow>
        )}

        {agentState.marketing_enabled && (
          <FooterRow label="Marketing">
            {viewMode === "action" && actions ? (
              <>
                {marketingSummary.dcNames.length > 0 && (
                  <span className="font-bold capitalize text-[#15717d]">
                    Grew demand: {marketingSummary.dcNames.join(", ")}
                  </span>
                )}
                {marketingSummary.beNames.length > 0 && (
                  <span className="font-bold text-[#be185d]">
                    Boosted brand: {marketingSummary.beNames.join(", ")}
                  </span>
                )}
                {marketingSummary.dcNames.length === 0 &&
                  marketingSummary.beNames.length === 0 && (
                    <span className={QUIET}>No marketing spend</span>
                  )}
              </>
            ) : (
              <span className={QUIET}>Switch to actions view to see spend</span>
            )}
          </FooterRow>
        )}

        {agentState.ptrs_readings_enabled && (
          <FooterRow label="PTRS Readings">
            {viewMode === "action" && actions ? (
              ptrsReadingsSummary.length > 0 ? (
                ptrsReadingsSummary.map((line, i) => (
                  <span key={i} className="font-bold text-primary">
                    {line.count} reading{line.count === 1 ? "" : "s"} on{" "}
                    {line.label}
                  </span>
                ))
              ) : (
                <span className={QUIET}>No readings commissioned</span>
              )
            ) : (
              <span className={QUIET}>
                Switch to actions view to see readings
              </span>
            )}
          </FooterRow>
        )}

        <FooterRow label="BD Bids">
          {viewMode === "action" ? (
            bdBidSummaries.length > 0 ? (
              bdBidSummaries.map((entry, i) => (
                <span key={i} className="font-bold text-primary">
                  {formatDisplayNumber(entry.bid)}
                  <span className="font-normal text-muted-foreground">
                    {" "}
                    for {entry.assetName}
                  </span>
                </span>
              ))
            ) : (
              <span className={QUIET}>No BD bids this step</span>
            )
          ) : (
            <span className={QUIET}>Switch to actions view to see bids</span>
          )}
        </FooterRow>
      </div>
    </div>
  );
}
