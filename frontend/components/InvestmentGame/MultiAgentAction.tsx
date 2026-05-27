"use client";

import { useEffect, useState, useMemo } from "react";
import LayoutContainer from "@/components/LayoutContainer";
import { Button } from "../ui/button";
import { ArrowBigRight, Ban, RotateCcw } from "lucide-react";
import { stepMultiAgentGame } from "@/lib/backendCallsGame";

import type {
  AssetSchemaType,
  MultiAgentGameStep,
  ActionType,
} from "@/lib/definitionsGameZ";
import ActionStats from "./ActionStats";
import AssetsTable from "./AssetsTable";
import Timeline from "./Timeline";
import CapitalProjectionGraph from "./CapitalProjectionGraph";
import {
  calculateTrialCost,
  extractAssets,
  extractAllAssets,
} from "@/lib/game";
import {
  isFirstPhase,
  isPhaseProgression,
  TRIAL_PHASES,
} from "@/lib/game-constants";
import ActionChart from "./ActionChart";
import TAExperience from "./TAExperience";
import RDCapacity from "./RDCapacity";
import BDMarketPanel from "./BDMarketPanel";
import SalesMarketPanel from "./SalesMarketPanel";
import AlertsPanel from "./AlertsPanel";
import OpponentBar from "./OpponentBar";
import MultiAgentGameOver from "./MultiAgentGameOver";
import HighlightKey from "./HighlightKey";
import { useParentSize } from "@visx/responsive";
import { LoaderList } from "../LoaderList";
import { formatDisplayNumber } from "@/lib/numbers";

import type { TrialPhaseName } from "@/lib/definitionsGameZ";
import type { HighlightType } from "@/lib/replay-helpers";

export default function MultiAgentAction({
  state,
  resetGame,
  goBackToStart,
}: {
  state: MultiAgentGameStep | undefined;
  resetGame: () => void;
  goBackToStart: () => void;
}) {
  const [localState, setLocalState] = useState<MultiAgentGameStep[]>([]);
  const activeState =
    localState.length > 0 ? localState[localState.length - 1] : null;
  const playerState = activeState?.player_state;
  const gameId = activeState?.game_id;
  const time = activeState?.time;
  const startingCash = playerState?.cash;

  const previousCash =
    localState.length > 1
      ? localState[localState.length - 2]?.player_state?.cash
      : undefined;
  const previousState =
    localState.length > 1
      ? localState[localState.length - 2]?.player_state
      : null;
  const previousAssets = previousState ? extractAssets(previousState) : [];

  // Selection state (same pattern as Action.tsx)
  const [selection, setSelection] = useState<
    Record<string, ActionType | boolean>
  >({});
  const [previousAssetStates, setPreviousAssetStates] = useState<
    Record<string, AssetSchemaType["state"]>
  >({});
  const [previousAssetPhases, setPreviousAssetPhases] = useState<
    Record<string, AssetSchemaType["pending_trial_phase"]>
  >({});
  const [loadingNextStep, setLoadingNextStep] = useState(false);
  const [error, setError] = useState("");
  const [gameOver, setGameOver] = useState(false);
  const [loadingResetGame, setLoadingResetGame] = useState(false);
  const [cashInPot, setCashInPot] = useState(0);
  const [previousSelection, setPreviousSelection] = useState<
    Record<string, ActionType | boolean>
  >({});
  const { parentRef, width } = useParentSize({ debounceTime: 150 });

  // BD bid state (per-asset bid levels)
  const [bdBids, setBdBids] = useState<number[]>([]);

  // Agent thinking simulation state: agent_name -> "waiting" | "thinking" | "decided"
  const [agentThinkingState, setAgentThinkingState] = useState<
    Record<string, "waiting" | "thinking" | "decided">
  >({});
  const agentsReady =
    Object.keys(agentThinkingState).length === 0 ||
    Object.values(agentThinkingState).every((s) => s === "decided");

  const investmentLevelsEnabled =
    playerState?.investment_levels_enabled ?? false;
  const distributionalPtrsEnabled =
    playerState?.distributional_ptrs_enabled ?? false;

  function handleAssetSelection(asset: AssetSchemaType) {
    const { id } = asset;
    if (!id) return;
    const currentSelection = selection[id];
    const isSelected =
      currentSelection === true ||
      (typeof currentSelection === "string" &&
        currentSelection !== "none" &&
        currentSelection !== "stop");

    if (isSelected) {
      setSelection({ ...selection, [id]: false });
      setCashInPot(cashInPot - calculateTrialCost(asset));
    } else {
      const newValue = investmentLevelsEnabled
        ? ("standard" as ActionType)
        : true;
      setSelection({ ...selection, [id]: newValue });
      setCashInPot(cashInPot + calculateTrialCost(asset));
    }
  }

  function handleInvestmentLevelChange(
    asset: AssetSchemaType,
    level: ActionType,
  ) {
    const { id } = asset;
    if (!id) return;
    const wasSelected =
      selection[id] === true ||
      (typeof selection[id] === "string" &&
        selection[id] !== "none" &&
        selection[id] !== "stop");
    const willBeSelected = level !== "none" && level !== "stop";
    setSelection({ ...selection, [id]: level });
    if (wasSelected && !willBeSelected) {
      setCashInPot(cashInPot - calculateTrialCost(asset));
    } else if (!wasSelected && willBeSelected) {
      setCashInPot(cashInPot + calculateTrialCost(asset));
    }
  }

  function handleBdBidChange(assetIndex: number, bidLevel: number) {
    setBdBids((prev) => {
      const next = [...prev];
      while (next.length <= assetIndex) next.push(0);
      next[assetIndex] = bidLevel;
      return next;
    });
  }

  // Initialize state from prop
  useEffect(() => {
    if (!state) return;
    setLocalState([state]);
    setPreviousSelection({});
    setBdBids([]);
  }, [state]);

  // Auto-select assets (same logic as Action.tsx)
  useEffect(() => {
    if (!playerState) return;
    let updatedPrevPhases = previousAssetPhases;

    if (localState.length > 1) {
      const prevPS = localState[localState.length - 2]?.player_state;
      if (prevPS) {
        const prevAllAssets = extractAllAssets(prevPS);
        const prevPhases: Record<
          string,
          AssetSchemaType["pending_trial_phase"]
        > = {};
        const prevStates: Record<string, AssetSchemaType["state"]> = {};
        prevAllAssets.forEach((asset) => {
          prevStates[asset.id] = asset.state;
          prevPhases[asset.id] = asset.pending_trial_phase;
        });
        updatedPrevPhases = prevPhases;
        setPreviousAssetStates(prevStates);
        setPreviousAssetPhases(prevPhases);
      }
    }

    const assets = extractAssets(playerState);
    const levelsEnabled = playerState.investment_levels_enabled ?? false;
    const newSelection: Record<string, ActionType | boolean> = {
      ...selection,
    };
    let totalCost = 0;

    const isSelectionActive = (
      val: ActionType | boolean | undefined,
    ): boolean => {
      if (val === true) return true;
      if (typeof val === "string" && val !== "none" && val !== "stop")
        return true;
      return false;
    };

    const phaseOrder = TRIAL_PHASES;

    assets.forEach((asset) => {
      const isIdle = asset.state === "Idle";
      const pendingPhase = asset.pending_trial_phase;
      const previousPhase = updatedPrevPhases[asset.id];
      const prevSel = previousSelection[asset.id];
      const isStartOfGame = localState.length === 1;

      const justMovedToNewPhase =
        previousPhase &&
        previousPhase !== pendingPhase &&
        isPhaseProgression(
          previousPhase as TrialPhaseName,
          pendingPhase as TrialPhaseName,
          phaseOrder,
        );

      if (isIdle && selection[asset.id] === undefined) {
        let shouldSelect: boolean;
        if (time === 0) {
          shouldSelect = false;
        } else if (isFirstPhase(pendingPhase ?? null)) {
          shouldSelect = false;
        } else if (isStartOfGame || justMovedToNewPhase) {
          shouldSelect = true;
        } else {
          shouldSelect = isSelectionActive(prevSel) || prevSel === undefined;
        }
        newSelection[asset.id] = shouldSelect
          ? levelsEnabled
            ? ("standard" as ActionType)
            : true
          : levelsEnabled
            ? ("none" as ActionType)
            : false;
      }

      if (isSelectionActive(newSelection[asset.id])) {
        totalCost += calculateTrialCost(asset);
      }
    });

    setSelection(newSelection);
    setCashInPot(totalCost);
  }, [localState, previousSelection]);

  // Compute highlighted asset IDs (new arrivals vs BD acquisitions)
  const highlightedAssetIds = useMemo(() => {
    if (!playerState || localState.length <= 1)
      return new Map<string, HighlightType>();
    const currentAssets = extractAllAssets(playerState);
    const prevAssetIds = new Set(previousAssets.map((a) => a.id));
    const highlights = new Map<string, HighlightType>();
    for (const asset of currentAssets) {
      if (!prevAssetIds.has(asset.id)) {
        highlights.set(
          asset.id,
          asset.type === "BD" ? "bd-acquisition" : "changed",
        );
      }
    }
    return highlights;
  }, [playerState, localState.length, previousAssets]);

  // Track player bankruptcy (player out but game continues)
  const playerBankrupt = activeState?.player_bankrupt ?? false;

  // Check for game over
  useEffect(() => {
    if (activeState?.game_ended) {
      setGameOver(true);
    }
  }, [activeState]);

  // Auto-advance when player is bankrupt but game is still going
  useEffect(() => {
    if (!playerBankrupt || gameOver || loadingNextStep || !gameId) return;

    const timer = setTimeout(() => {
      actionNextStep();
    }, 250);

    return () => clearTimeout(timer);
  }, [playerBankrupt, gameOver, localState.length]);

  // Simulated thinking time by agent type (central value in ms)
  const THINKING_TIMES: Record<string, number> = {
    do_nothing: 150,
    random: 250,
    knapsack_agent: 500,
    mck_agent: 600,
    pyxie: 800,
  };

  // Trigger agent thinking simulation whenever a new step loads
  useEffect(() => {
    const opponents = activeState?.opponents;
    if (!opponents || opponents.length === 0) return;

    let cancelled = false;

    // Set all to "thinking" immediately
    const initial: Record<string, "waiting" | "thinking" | "decided"> = {};
    opponents.forEach((opp) => {
      initial[opp.agent_name] = "thinking";
    });
    setAgentThinkingState(initial);

    // Run all agents in parallel, each finishes after its own delay
    opponents.forEach((opp) => {
      const base = THINKING_TIMES[opp.agent_type] ?? 800;
      const delay = Math.min(base * (0.7 + Math.random() * 0.6), 1000);
      setTimeout(() => {
        if (cancelled) return;
        setAgentThinkingState((prev) => ({
          ...prev,
          [opp.agent_name]: "decided",
        }));
      }, delay);
    });

    return () => {
      cancelled = true;
    };
  }, [localState.length]);

  // Step the game
  async function actionNextStep() {
    if (!gameId) return;
    setLoadingNextStep(true);
    setError("");

    try {
      // Build investment actions payload
      const investmentActions: Record<string, ActionType | null> = {};
      Object.keys(selection).forEach((assetId) => {
        const val = selection[assetId];
        if (val === true) {
          investmentActions[assetId] = "invest";
        } else if (typeof val === "string" && val !== "none") {
          investmentActions[assetId] = val as ActionType;
        }
      });

      const response = await stepMultiAgentGame(gameId, {
        investment_actions: investmentActions,
        bd_bids: bdBids,
      });

      if (response) {
        setLocalState((prev) => [...prev, response]);
        if (response.game_ended) {
          setGameOver(true);
        }
        setPreviousSelection(selection);
        setSelection({});
        setCashInPot(0);
        setBdBids([]);
      }
    } catch (err) {
      let message = "An unexpected error occurred";
      if (err instanceof Error) {
        try {
          const parsed = JSON.parse(err.message);
          message =
            parsed && typeof parsed.detail === "string"
              ? parsed.detail
              : err.message;
        } catch {
          message = err.message;
        }
      }
      if (
        message.toLowerCase().includes("horizon") ||
        message.toLowerCase().includes("game ended") ||
        message.toLowerCase().includes("game over") ||
        message.toLowerCase().includes("already ended")
      ) {
        setGameOver(true);
      } else {
        setError(message);
      }
    }
    setLoadingNextStep(false);
  }

  const assets = playerState ? extractAssets(playerState) : [];

  const nextStepCost = useMemo(() => {
    if (!playerState) return 0;
    const isSelectedForInvestment = (assetId: string): boolean => {
      const val = selection[assetId];
      if (val === true) return true;
      if (typeof val === "string" && val !== "none" && val !== "stop")
        return true;
      return false;
    };
    let totalSpend = 0;
    let developmentSpend = 0;
    assets.forEach((asset) => {
      if (isSelectedForInvestment(asset.id)) {
        totalSpend += calculateTrialCost(asset);
      }
      const actionVal = selection[asset.id];
      if (asset.state === "In Development" && actionVal !== "stop") {
        developmentSpend += calculateTrialCost(asset);
      }
    });
    return totalSpend + developmentSpend;
  }, [assets, selection, playerState]);

  const handleResetGame = async () => {
    setLoadingResetGame(true);
    try {
      setGameOver(false);
      await resetGame();
    } finally {
      setLoadingResetGame(false);
    }
  };

  return (
    <div className="mt-4 overflow-x-hidden">
      <LayoutContainer className="flex flex-col gap-1" maxWidth="1560px">
        {loadingResetGame ? (
          <LoaderList />
        ) : (
          <>
            {/* Game Over */}
            {gameOver ? (
              <MultiAgentGameOver
                playerState={playerState}
                activeState={activeState}
                assets={playerState ? extractAllAssets(playerState) : assets}
                onNewGame={handleResetGame}
                onBackToStart={goBackToStart}
              />
            ) : (
              <>
                {/* Main game UI */}
                <div className="flex gap-4">
                  {/* Stats and Charts */}
                  <div className="flex min-w-0 flex-1 gap-4" id="actionStat">
                    <div className="flex min-w-0 flex-col justify-between gap-4">
                      <ActionStats
                        time={time!}
                        startingCash={startingCash || 0}
                        previousCash={previousCash}
                        previousAssets={previousAssets}
                        cashInPot={cashInPot}
                        assets={assets}
                        selection={selection}
                        nextStepCost={nextStepCost}
                        eNPVDescription="eNPV stands for Expected Net Present Value and is a measure of the value of your portfolio today, taking into account all its expected future costs and revenue. In multiplayer mode the winner is determined by NCF (cumulative cash flow), not eNPV."
                      />
                      <div className="w-full overflow-hidden">
                        <CapitalProjectionGraph
                          currentTime={time || 0}
                          currentCapital={startingCash || 0}
                          totalTime={activeState?.horizon || 10}
                          gameState={playerState || undefined}
                          width={Math.min(width || 350, 350)}
                        />
                      </div>
                    </div>
                    <div className="flex min-h-[300px] min-w-0 flex-1 flex-col gap-4">
                      <div className="w-full overflow-hidden">
                        <div ref={parentRef}>
                          <ActionChart
                            assets={assets}
                            selection={selection}
                            horizon={playerState?.horizon!}
                            currentTime={time}
                            gameState={playerState!}
                            dataType="cost"
                            width={Math.min(width || 500, 700)}
                            chartTitle="Total Cost this year:"
                            hintCosts={0}
                            infoLabel="costCurve"
                          />
                        </div>
                      </div>
                      <div className="w-full overflow-hidden">
                        <ActionChart
                          assets={assets}
                          selection={selection}
                          horizon={playerState?.horizon!}
                          currentTime={time}
                          gameState={playerState!}
                          dataType="revenue"
                          width={Math.min(width || 500, 700)}
                          chartTitle="Budget next year:"
                          hintCosts={0}
                          infoLabel="revenueCurve"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Bankruptcy Banner */}
                  {playerBankrupt && (
                    <div className="w-full rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <Ban className="h-5 w-5 text-red-600" />
                        <span className="font-semibold text-red-700">
                          You went bankrupt!
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-red-600">
                        Watching remaining competitors play out the game...
                      </p>
                    </div>
                  )}

                  {/* Controls */}
                  <div className="flex flex-col items-end gap-4 rounded-lg bg-white">
                    <div className="flex items-center gap-3">
                      <Button
                        variant="outline"
                        onClick={handleResetGame}
                        size="sm"
                        disabled={loadingResetGame}
                      >
                        <RotateCcw className="h-4 w-4" />
                      </Button>
                      {!playerBankrupt && (
                        <Button
                          onClick={actionNextStep}
                          disabled={loadingNextStep || !agentsReady}
                          className="min-w-[120px]"
                        >
                          {loadingNextStep
                            ? "Processing..."
                            : !agentsReady
                              ? "Agents deciding..."
                              : "Next Year"}
                          <ArrowBigRight className="ml-2 h-4 w-4" />
                        </Button>
                      )}
                    </div>

                    <div className="flex w-full items-center gap-6 rounded-lg bg-gray-100 p-4">
                      <div className="flex flex-col items-start gap-0">
                        <span className="text-sm font-medium text-gray-600">
                          Year {time || 0} of {activeState?.horizon || 10}
                        </span>
                        <div className="w-[200px]">
                          <Timeline
                            currentTime={time || 0}
                            totalTime={activeState?.horizon || 10}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Opponent Bar */}
                    {activeState?.opponents && (
                      <OpponentBar
                        opponents={activeState.opponents}
                        thinkingState={agentThinkingState}
                        playerCumulativeReward={
                          activeState?.player_cumulative_reward ?? 0
                        }
                      />
                    )}

                    {/* TA Experience */}
                    {playerState?.ta_experience_enabled &&
                      playerState?.ta_experience &&
                      Object.keys(playerState.ta_experience).length > 0 && (
                        <div className="w-full overflow-hidden">
                          <TAExperience
                            taExperience={playerState.ta_experience}
                            maxExperience={
                              playerState.experience_to_full_knowledge
                            }
                            maxTotalExperience={
                              playerState.max_total_experience
                            }
                          />
                        </div>
                      )}

                    {/* R&D Capacity */}
                    {playerState?.investment_levels_enabled &&
                      playerState.capacity_used !== undefined &&
                      playerState.capacity_base !== undefined && (
                        <div className="w-full overflow-hidden">
                          <RDCapacity
                            capacityUsed={playerState.capacity_used}
                            capacityBase={playerState.capacity_base}
                            successModifier={playerState.success_modifier}
                            costModifier={playerState.cost_modifier}
                          />
                        </div>
                      )}
                  </div>
                </div>

                {/* Error */}
                {error && (
                  <div className="mt-2 flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
                    <Ban className="h-5 w-5 flex-shrink-0" />
                    <span className="text-sm font-medium">{error}</span>
                  </div>
                )}

                {/* Asset Table */}
                <HighlightKey
                  showBdAcquisition={activeState?.bd_enabled ?? false}
                />
                <div className="mt-2 overflow-x-auto rounded-lg bg-white shadow-sm">
                  <AssetsTable
                    assets={playerState ? extractAllAssets(playerState) : []}
                    selection={selection}
                    onAssetSelection={handleAssetSelection}
                    onInvestmentLevelChange={handleInvestmentLevelChange}
                    investmentLevelsEnabled={investmentLevelsEnabled}
                    investmentLevelsConfig={
                      playerState?.investment_levels_config ?? null
                    }
                    interimObservationsEnabled={
                      playerState?.interim_observations_enabled ?? false
                    }
                    distributionalPtrsEnabled={distributionalPtrsEnabled}
                    previousAssetStates={previousAssetStates}
                    previousAssetPhases={previousAssetPhases}
                    highlightedAssetIds={highlightedAssetIds}
                    hints={{}}
                    hintColumnVisible={false}
                    selectedAgentName=""
                    time={time}
                  />
                </div>

                {/* Multi-Agent Panels (side-by-side) */}
                <div
                  className={`mt-4 grid gap-4 ${activeState?.bd_enabled ? "grid-cols-3" : "grid-cols-2"}`}
                >
                  {activeState?.bd_enabled && (
                    <BDMarketPanel
                      bdAssets={activeState?.bd_assets ?? []}
                      playerCash={startingCash || 0}
                      bdBids={bdBids}
                      bdBidPrices={activeState?.bd_bid_prices ?? []}
                      onBidChange={handleBdBidChange}
                    />
                  )}
                  <SalesMarketPanel
                    indicationMarkets={activeState?.indication_markets || []}
                    playerAgentName={
                      activeState?.player_agent_name || "pharma_0"
                    }
                  />
                  <AlertsPanel
                    alerts={activeState?.alerts || []}
                    playerAgentName={
                      activeState?.player_agent_name || "pharma_0"
                    }
                  />
                </div>
              </>
            )}
          </>
        )}
      </LayoutContainer>
    </div>
  );
}
