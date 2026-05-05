import { useState, useMemo, useEffect, useCallback } from "react";
import type {
  PlaythroughData,
  GameStepSchemaType,
  SharedMarketSnapshot,
  AgentActionRecord,
  AssetSchemaType,
} from "@/lib/definitionsGameZ";
import {
  computeChangedAssetIds,
  computeActionHighlights,
  getAgentColorMap,
  getAgentDisplayNames,
  type HighlightType,
} from "@/lib/replay-helpers";

export type ViewMode = "state" | "action";

export interface ReplayState {
  currentStepIndex: number;
  totalSteps: number;
  viewMode: ViewMode;
  currentAgentStates: Record<string, GameStepSchemaType>;
  previousAgentStates: Record<string, GameStepSchemaType> | null;
  currentSharedMarket: SharedMarketSnapshot;
  currentActions: Record<string, AgentActionRecord> | null;
  currentRewards: Record<string, number>;
  cumulativeRewards: Record<string, number>;
  changedAssetIds: Record<string, Map<string, HighlightType>>;
  actionHighlightIds: Record<string, Set<string>>;
  agentColors: Record<string, string>;
  agentDisplayNames: Record<string, string>;
  goToStep: (index: number) => void;
  goNext: () => void;
  goPrev: () => void;
  setViewMode: (mode: ViewMode) => void;
}

/**
 * Reconstruct full expired_assets from delta-compressed playthrough data.
 *
 * The backend stores only *newly* expired/failed assets per step to reduce
 * JSON size. This function accumulates the deltas so each step has the
 * complete set of expired assets, which downstream helpers expect.
 */
function reconstructExpiredAssets(data: PlaythroughData): PlaythroughData {
  const agentIds = data.metadata.agent_ids;

  // Accumulator per agent — start from initial state
  const accumulated: Record<string, Record<string, AssetSchemaType>> = {};
  for (const agentId of agentIds) {
    accumulated[agentId] = {
      ...(data.initial_agent_states[agentId]?.expired_assets ?? {}),
    };
  }

  const reconstructedSteps = data.steps.map((step) => {
    const newAgentStates: Record<string, GameStepSchemaType> = {};
    for (const agentId of agentIds) {
      const stepExpired = step.agent_states[agentId]?.expired_assets ?? {};
      // Merge delta into accumulator
      Object.assign(accumulated[agentId], stepExpired);
      newAgentStates[agentId] = {
        ...step.agent_states[agentId],
        expired_assets: { ...accumulated[agentId] },
      };
    }
    return { ...step, agent_states: newAgentStates };
  });

  return { ...data, steps: reconstructedSteps };
}

export function useReplayState(rawData: PlaythroughData): ReplayState {
  // Reconstruct full expired_assets from deltas once on load
  const data = useMemo(() => reconstructExpiredAssets(rawData), [rawData]);

  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [viewMode, setViewMode] = useState<ViewMode>("state");

  // totalSteps = data.steps.length + 1 (initial state + one per transition)
  // Index 0 = initial state (+ action taken from it)
  // Index N = post-step-N state (+ action taken from it, if not terminal)
  // Index data.steps.length = final state (no action)
  const totalSteps = data.steps.length + 1;

  const agentColors = useMemo(
    () => getAgentColorMap(data.metadata.agent_ids),
    [data.metadata.agent_ids],
  );

  const agentDisplayNames = useMemo(
    () => getAgentDisplayNames(data.metadata),
    [data.metadata],
  );

  const goToStep = useCallback(
    (index: number) => {
      const clamped = Math.max(0, Math.min(index, totalSteps - 1));
      setCurrentStepIndex(clamped);
    },
    [totalSteps],
  );

  const goNext = useCallback(() => {
    setCurrentStepIndex((prev) => Math.min(prev + 1, totalSteps - 1));
  }, [totalSteps]);

  const goPrev = useCallback(() => {
    setCurrentStepIndex((prev) => Math.max(prev - 1, 0));
  }, []);

  // Keyboard navigation
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT"
      ) {
        return;
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goNext();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goNext, goPrev]);

  // State the agent observes at this position
  // Index 0 = initial state, Index N>0 = post-step-(N-1) state
  const currentAgentStates = useMemo(() => {
    if (currentStepIndex === 0) return data.initial_agent_states;
    return data.steps[currentStepIndex - 1].agent_states;
  }, [data, currentStepIndex]);

  const previousAgentStates = useMemo(() => {
    if (currentStepIndex === 0) return null;
    if (currentStepIndex === 1) return data.initial_agent_states;
    return data.steps[currentStepIndex - 2].agent_states;
  }, [data, currentStepIndex]);

  // Shared market matching the observed state
  const currentSharedMarket = useMemo(() => {
    if (currentStepIndex === 0) return data.initial_shared_market;
    return data.steps[currentStepIndex - 1].shared_market;
  }, [data, currentStepIndex]);

  // Action taken FROM this observed state (null at terminal)
  const currentActions = useMemo(() => {
    if (currentStepIndex >= data.steps.length) return null;
    return data.steps[currentStepIndex].actions;
  }, [data, currentStepIndex]);

  // Rewards earned from the PREVIOUS transition (arriving at this state)
  const currentRewards = useMemo(() => {
    if (currentStepIndex === 0) {
      return Object.fromEntries(data.metadata.agent_ids.map((id) => [id, 0]));
    }
    return data.steps[currentStepIndex - 1].rewards;
  }, [data, currentStepIndex]);

  const cumulativeRewards = useMemo(() => {
    if (currentStepIndex === 0) {
      return Object.fromEntries(data.metadata.agent_ids.map((id) => [id, 0]));
    }
    return data.steps[currentStepIndex - 1].cumulative_rewards;
  }, [data, currentStepIndex]);

  const changedAssetIds = useMemo(
    () => computeChangedAssetIds(currentAgentStates, previousAgentStates),
    [currentAgentStates, previousAgentStates],
  );

  const actionHighlightIds = useMemo(
    () => computeActionHighlights(currentActions),
    [currentActions],
  );

  return {
    currentStepIndex,
    totalSteps,
    viewMode,
    currentAgentStates,
    previousAgentStates,
    currentSharedMarket,
    currentActions,
    currentRewards,
    cumulativeRewards,
    changedAssetIds,
    actionHighlightIds,
    agentColors,
    agentDisplayNames,
    goToStep,
    goNext,
    goPrev,
    setViewMode,
  };
}
