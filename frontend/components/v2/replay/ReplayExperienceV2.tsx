"use client";

import { useMemo, useState } from "react";
import { useReplayState } from "@/components/InvestmentGame/Replay/useReplayState";
import type { PlaythroughData } from "@/lib/definitionsGameZ";
import { cn } from "@/lib/utils";
import { ReplayTopBar } from "./ReplayTopBar";
import { ReplayRewardChart } from "./ReplayRewardChart";
import { AgentSummaryList } from "./AgentSummaryList";
import { ReplayPortfolioPanel } from "./ReplayPortfolioPanel";
import { ReplayBDMarketBoard } from "./ReplayBDMarketBoard";
import { ReplaySalesMarketBoard } from "./ReplaySalesMarketBoard";
import { ReplayIntelligenceBoard } from "./ReplayIntelligenceBoard";
import {
  AssetLegend,
  type HighlightFilter,
} from "@/components/v2/game/ui/AssetTable";
import { FadeScroll } from "@/components/v2/game/ui/FadeScroll";

function MarketPanel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-w-0 rounded bg-secondary/25 p-4">
      <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">
        {title}
      </div>
      <FadeScroll className="max-h-[420px]">{children}</FadeScroll>
    </div>
  );
}

/**
 * The v2 replay viewer. All replay logic (step reconstruction, view
 * mode, keyboard navigation) comes from the classic useReplayState
 * hook — this component only owns the presentation.
 */
export function ReplayExperienceV2({
  data,
  onExit,
}: {
  data: PlaythroughData;
  onExit: () => void;
}) {
  const replay = useReplayState(data);

  // --- identical alert/step derivation to the classic PlaythroughViewer ---
  const allAlerts = useMemo(() => {
    const alerts = [...(data.initial_shared_market.alerts || [])];
    for (let i = 0; i < replay.currentStepIndex; i++) {
      if (data.steps[i]) {
        alerts.push(...(data.steps[i].shared_market.alerts || []));
      }
    }
    // Deduplicate by step+event_type+agent_id
    const seen = new Set<string>();
    return alerts.filter((a) => {
      const key = `${a.step}-${a.event_type}-${a.agent_id}-${a.indication}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [data, replay.currentStepIndex]);

  const currentStep =
    replay.currentStepIndex === 0
      ? 0
      : (data.steps[replay.currentStepIndex - 1]?.step ?? 0);
  // --- end identical derivation ---

  // Legend filter shared by both portfolio tables; counts across agents.
  const [highlightFilter, setHighlightFilter] = useState<HighlightFilter>(null);
  const highlightCounts = useMemo(() => {
    let changed = 0;
    let bd = 0;
    for (const map of Object.values(replay.changedAssetIds)) {
      for (const type of map.values()) {
        if (type === "bd-acquisition") bd += 1;
        else changed += 1;
      }
    }
    return { changed, bd };
  }, [replay.changedAssetIds]);

  return (
    <div className="-mb-4 -mt-6 flex h-dvh bg-background font-light">
      <div className="min-w-0 flex-1 overflow-y-auto">
        <ReplayTopBar
          numAgents={data.metadata.num_agents}
          seed={data.metadata.seed}
          viewMode={replay.viewMode}
          onViewModeChange={replay.setViewMode}
          stepIndex={replay.currentStepIndex}
          totalSteps={replay.totalSteps}
          onStepChange={replay.goToStep}
          onPrev={replay.goPrev}
          onNext={replay.goNext}
          onExit={onExit}
        />

        <div className="mx-auto w-full max-w-[1560px] space-y-4 p-4">
          {/* Chart + agent summary, 70/30 */}
          <div className="grid gap-4 lg:grid-cols-[7fr_3fr]">
            <div className="min-w-0 overflow-hidden rounded bg-secondary/25 p-4">
              <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">
                Net Cash Flow Over Time
              </div>
              <ReplayRewardChart
                data={data}
                currentStepIndex={replay.currentStepIndex}
                agentColors={replay.agentColors}
                agentDisplayNames={replay.agentDisplayNames}
              />
            </div>
            <div className="min-w-0 py-4">
              <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">
                Agents
              </div>
              <AgentSummaryList
                agentIds={data.metadata.agent_ids}
                agentDisplayNames={replay.agentDisplayNames}
                agentStates={replay.currentAgentStates}
                cumulativeRewards={replay.cumulativeRewards}
                agentColors={replay.agentColors}
              />
            </div>
          </div>
          {/* Shared row-tint legend for both portfolio tables */}
          <div className="flex justify-end">
            <AssetLegend
              counts={highlightCounts}
              active={highlightFilter}
              onToggle={(key) =>
                setHighlightFilter((prev) => (prev === key ? null : key))
              }
            />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {data.metadata.agent_ids.map((agentId) => {
              const agentState = replay.currentAgentStates[agentId];
              if (!agentState) return null;
              return (
                <ReplayPortfolioPanel
                  key={agentId}
                  agentId={agentId}
                  displayName={replay.agentDisplayNames[agentId]}
                  agentState={agentState}
                  actions={replay.currentActions?.[agentId] ?? null}
                  viewMode={replay.viewMode}
                  changedAssetIds={replay.changedAssetIds[agentId] ?? new Map()}
                  color={replay.agentColors[agentId]}
                  cumulativeReward={replay.cumulativeRewards[agentId] ?? 0}
                  reward={replay.currentRewards[agentId] ?? 0}
                  highlightFilter={highlightFilter}
                />
              );
            })}
          </div>

          {/* Shared market boards */}
          <div
            className={cn(
              "grid gap-4",
              data.config.bd_enabled ? "lg:grid-cols-3" : "lg:grid-cols-2",
            )}
          >
            {data.config.bd_enabled && (
              <MarketPanel title="BD Market">
                <ReplayBDMarketBoard
                  bdAssets={replay.currentSharedMarket.bd_assets}
                  lastAcquisitions={
                    replay.currentSharedMarket.last_bd_acquisitions
                  }
                  agentActions={replay.currentActions ?? undefined}
                  agentColors={replay.agentColors}
                  agentDisplayNames={replay.agentDisplayNames}
                  viewMode={replay.viewMode}
                />
              </MarketPanel>
            )}
            <MarketPanel title="Sales Market">
              <ReplaySalesMarketBoard
                indicationMarkets={
                  replay.currentSharedMarket.indication_markets
                }
                agentColors={replay.agentColors}
                agentDisplayNames={replay.agentDisplayNames}
              />
            </MarketPanel>
            <MarketPanel title="Competitive Intelligence">
              <ReplayIntelligenceBoard
                alerts={allAlerts}
                currentStep={currentStep}
                agentDisplayNames={replay.agentDisplayNames}
              />
            </MarketPanel>
          </div>
        </div>
      </div>
    </div>
  );
}
