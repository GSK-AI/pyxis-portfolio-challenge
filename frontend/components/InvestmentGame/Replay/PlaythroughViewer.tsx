"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import LayoutContainer from "@/components/LayoutContainer";

import type { PlaythroughData } from "@/lib/definitionsGameZ";
import { useReplayState } from "./useReplayState";
import StepNavigator from "./StepNavigator";
import ViewModeToggle from "./ViewModeToggle";
import AgentPortfolioPanel from "./AgentPortfolioPanel";
import AgentLeaderboard from "./AgentLeaderboard";
import ReplayBDMarketPanel from "./ReplayBDMarketPanel";
import ReplaySalesMarketPanel from "./ReplaySalesMarketPanel";
import ReplayAlertsPanel from "./ReplayAlertsPanel";
import RewardChart from "./RewardChart";
import GameOverSummary from "./GameOverSummary";
import HighlightKey from "../HighlightKey";

interface PlaythroughViewerProps {
  data: PlaythroughData;
  onExit: () => void;
}

export default function PlaythroughViewer({
  data,
  onExit,
}: PlaythroughViewerProps) {
  const replay = useReplayState(data);
  const numAgents = data.metadata.num_agents;
  const [showSummary, setShowSummary] = useState(false);
  const prevStepIndex = useRef(replay.currentStepIndex);

  // Detect when we reach the final step or all agents are bankrupt
  const isGameOver = useMemo(() => {
    const states = replay.currentAgentStates;
    const allEnded = data.metadata.agent_ids.every(
      (id) => states[id]?.game_ended,
    );
    const atFinalStep = replay.currentStepIndex === replay.totalSteps - 1;
    return atFinalStep || allEnded;
  }, [
    replay.currentAgentStates,
    replay.currentStepIndex,
    replay.totalSteps,
    data.metadata.agent_ids,
  ]);

  // Auto-show summary when navigating TO a game-over state
  useEffect(() => {
    if (isGameOver && prevStepIndex.current !== replay.currentStepIndex) {
      setShowSummary(true);
    }
    prevStepIndex.current = replay.currentStepIndex;
  }, [isGameOver, replay.currentStepIndex]);

  // Collect all alerts from all steps up to current observed state
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

  const agentGridCols =
    numAgents <= 2
      ? "grid-cols-2"
      : numAgents === 3
        ? "grid-cols-3"
        : "grid-cols-2";

  const sharedPanelCols = data.config.bd_enabled
    ? "grid-cols-3"
    : "grid-cols-2";

  return (
    <div className="mt-4 overflow-x-hidden">
      <LayoutContainer className="flex flex-col gap-4" maxWidth="1560px">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold">Replay</h2>
            <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
              {numAgents} agents &middot; seed {data.metadata.seed}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <ViewModeToggle
              viewMode={replay.viewMode}
              onViewModeChange={replay.setViewMode}
              disabled={replay.currentActions === null}
            />
            <StepNavigator
              currentStepIndex={replay.currentStepIndex}
              totalSteps={replay.totalSteps}
              onGoTo={replay.goToStep}
              onNext={replay.goNext}
              onPrev={replay.goPrev}
            />
            <Button variant="outline" size="sm" onClick={onExit}>
              <X className="mr-1 h-4 w-4" />
              Exit
            </Button>
          </div>
        </div>

        {/* Leaderboard */}
        <AgentLeaderboard
          agentIds={data.metadata.agent_ids}
          agentDisplayNames={replay.agentDisplayNames}
          agentStates={replay.currentAgentStates}
          cumulativeRewards={replay.cumulativeRewards}
          agentColors={replay.agentColors}
        />

        {/* Reward Chart */}
        <RewardChart
          data={data}
          currentStepIndex={replay.currentStepIndex}
          agentColors={replay.agentColors}
          agentDisplayNames={replay.agentDisplayNames}
        />

        {/* Agent Portfolio Panels */}
        <HighlightKey showBdAcquisition={data.config.bd_enabled} />
        <div className={`grid gap-4 ${agentGridCols}`}>
          {data.metadata.agent_ids.map((agentId) => (
            <AgentPortfolioPanel
              key={agentId}
              agentId={agentId}
              displayName={replay.agentDisplayNames[agentId]}
              agentState={replay.currentAgentStates[agentId]}
              previousAgentState={replay.previousAgentStates?.[agentId] ?? null}
              actions={replay.currentActions?.[agentId] ?? null}
              viewMode={replay.viewMode}
              changedAssetIds={replay.changedAssetIds[agentId] ?? new Map()}
              actionHighlightIds={
                replay.actionHighlightIds[agentId] ?? new Set()
              }
              color={replay.agentColors[agentId]}
              cumulativeReward={replay.cumulativeRewards[agentId] ?? 0}
              reward={replay.currentRewards[agentId] ?? 0}
            />
          ))}
        </div>

        {/* Shared Market Panels */}
        <div className={`grid gap-4 ${sharedPanelCols}`}>
          {data.config.bd_enabled && (
            <ReplayBDMarketPanel
              bdAssets={replay.currentSharedMarket.bd_assets}
              lastAcquisitions={replay.currentSharedMarket.last_bd_acquisitions}
              agentActions={replay.currentActions ?? undefined}
              agentColors={replay.agentColors}
              agentDisplayNames={replay.agentDisplayNames}
              viewMode={replay.viewMode}
            />
          )}
          <ReplaySalesMarketPanel
            indicationMarkets={replay.currentSharedMarket.indication_markets}
            agentColors={replay.agentColors}
            agentDisplayNames={replay.agentDisplayNames}
          />
          <ReplayAlertsPanel
            alerts={allAlerts}
            currentStep={currentStep}
            agentDisplayNames={replay.agentDisplayNames}
          />
        </div>

        {/* Game Over Summary */}
        <GameOverSummary
          open={showSummary}
          onClose={() => setShowSummary(false)}
          data={data}
          agentColors={replay.agentColors}
          agentDisplayNames={replay.agentDisplayNames}
        />
      </LayoutContainer>
    </div>
  );
}
