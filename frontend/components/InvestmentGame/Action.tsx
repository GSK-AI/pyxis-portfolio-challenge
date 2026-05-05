"use client";

import { useEffect, useState, useRef, useMemo } from "react";
import LayoutContainer from "@/components/LayoutContainer";
import { Button } from "../ui/button";
import { ArrowBigRight, Ban, RotateCcw } from "lucide-react";
import { stepGame, getLevels } from "@/lib/backendCallsGame";

import type {
  AssetSchemaType,
  GameStepResponse,
  GameStepSchemaType,
  TrialPhaseName,
  GameLevel,
  ActionType,
  GameStart,
} from "@/lib/definitionsGameZ";
import ActionStats from "./ActionStats";
import AssetsTable from "./AssetsTable";
import Timeline from "./Timeline";
import CapitalProjectionGraph from "./CapitalProjectionGraph";
import UnlockHint from "./UnlockHint";
import {
  calculateTrialCost,
  extractAssets,
  extractAllAssets,
} from "@/lib/game";
import {
  isFirstPhase,
  isPhaseProgression,
  extractPhasesFromAssets,
  TRIAL_PHASES,
} from "@/lib/game-constants";
import ActionChart from "./ActionChart";
import ActionComparison from "./ActionComparison";
import GameOverScreen from "./GameOverScreen";
import TAExperience from "./TAExperience";
import RDCapacity from "./RDCapacity";
import { useParentSize } from "@visx/responsive";
import { Badge } from "../ui/badge";
import { LoaderList } from "../LoaderList";

import { useNextStep } from "nextstepjs";
import { useCustomNextStep } from "@/hooks/use-custom-next-step";

export default function ActionGame({
  state,
  currentLevel,
  resetGame,
  restartSameGame,
  goBackToStart,
  goToNextLevel,
  gameConfig,
  defaultConfig,
  onConfigChange,
}: {
  state: GameStepResponse | undefined;
  currentLevel: GameLevel | null;
  resetGame: () => void;
  restartSameGame?: () => void;
  goBackToStart: () => void;
  goToNextLevel: () => void;
  gameConfig?: GameStart | null;
  defaultConfig?: GameStart | null;
  onConfigChange?: (field: keyof GameStart, value: number) => void;
}) {
  const { startNextStep } = useNextStep();
  const { startTourIfNotSkipped } = useCustomNextStep();
  const [localState, setLocalState] = useState<GameStepSchemaType[]>([]);
  const gameId = state?.id;
  const activeState =
    localState.length > 0 ? localState[localState.length - 1] : null;
  const time = activeState?.time;
  const startingCash = activeState?.cash;

  // Calculate previous cash for capital change display
  const previousCash =
    localState.length > 1 ? localState[localState.length - 2]?.cash : undefined;

  // Calculate previous eNPV and eROI for change display
  const previousState =
    localState.length > 1 ? localState[localState.length - 2] : null;
  const previousAssets = previousState ? extractAssets(previousState) : [];

  // Selection tracks which assets are selected and their investment level
  // When investment_levels_enabled is false, we use boolean-like values (true -> "invest")
  // When investment_levels_enabled is true, we track the actual ActionType
  const [selection, setSelection] = useState<
    Record<string, ActionType | boolean>
  >({});
  const [previousAssetStates, setPreviousAssetStates] = useState<
    Record<string, AssetSchemaType["state"]>
  >({});
  const [previousAssetPhases, setPreviousAssetPhases] = useState<
    Record<string, AssetSchemaType["pending_trial_phase"]>
  >({});
  const [loadingNextStep, setLoadingNextStep] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [gameOver, setGameOver] = useState<boolean>(false);
  const [loadingRestart, setLoadingRestart] = useState<boolean>(false);
  const [loadingNextLevel, setLoadingNextLevel] = useState<boolean>(false);
  const [loadingResetGame, setLoadingResetGame] = useState<boolean>(false);
  const [allLevels, setAllLevels] = useState<GameLevel[]>([]);
  const [spendingWarning, setSpendingWarning] = useState<string>("");
  const warningTimeout = useRef<NodeJS.Timeout | null>(null);
  const [cashInPot, setCashInPot] = useState<number>(0);
  const [hintCosts, setHintCosts] = useState<number>(0); // Track total spent on hints
  const [hints, setHints] = useState<Record<string, boolean>>({});
  const [hintColumnVisible, setHintColumnVisible] = useState<boolean>(false);
  const [selectedAgentName, setSelectedAgentName] = useState<string>("");
  const [previousSelection, setPreviousSelection] = useState<
    Record<string, ActionType | boolean>
  >({});
  const { parentRef, width } = useParentSize({ debounceTime: 150 });

  // Fetch all levels to check if there's a next level
  useEffect(() => {
    async function fetchLevels() {
      try {
        const levels = await getLevels();
        setAllLevels(levels);
      } catch (error) {
        console.error("Failed to fetch levels:", error);
      }
    }
    fetchLevels();
    startTourIfNotSkipped("actionScreenOne", startNextStep);
  }, []);

  // Check if there's a next level available
  const hasNextLevel = useMemo(() => {
    if (!currentLevel || allLevels.length === 0) return false;
    const currentLevelIdx = currentLevel.level_idx;
    return allLevels.some((level) => level.level_idx > currentLevelIdx);
  }, [currentLevel, allLevels]);

  // Check if investment levels feature is enabled
  const investmentLevelsEnabled =
    activeState?.investment_levels_enabled ?? false;
  const investmentLevelsConfig = activeState?.investment_levels_config ?? null;

  // Check if distributional PTRS feature is enabled
  const distributionalPtrsEnabled =
    activeState?.distributional_ptrs_enabled ?? false;

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
      const newSelection = { ...selection, [id]: false };
      setSelection(newSelection);
      setCashInPot(cashInPot - calculateTrialCost(asset));
    } else {
      // When investment levels are enabled, default to "standard" for new selections
      const newValue = investmentLevelsEnabled
        ? ("standard" as ActionType)
        : true;
      const newSelection = { ...selection, [id]: newValue };
      setSelection(newSelection);
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

    const newSelection = { ...selection, [id]: level };
    setSelection(newSelection);

    // Update cash in pot based on selection change
    if (wasSelected && !willBeSelected) {
      setCashInPot(cashInPot - calculateTrialCost(asset));
    } else if (!wasSelected && willBeSelected) {
      setCashInPot(cashInPot + calculateTrialCost(asset));
    }
  }

  function pushState(state: GameStepSchemaType) {
    setLocalState((prev) => [...prev, state]);
  }

  function handleHintReceived(
    newHints: Record<string, boolean>,
    agentName: string,
  ) {
    setHints(newHints);
    setSelectedAgentName(agentName);
    setHintColumnVisible(true); // Show hint column when hints are received
  }

  function handleHintToggled(visible: boolean, agentName?: string) {
    setHintColumnVisible(visible);
    if (visible && agentName) {
      setSelectedAgentName(agentName);
    } else {
      setHints({});
      setSelectedAgentName("");
    }
  }

  function handleCashDeducted(amount: number) {
    setHintCosts((prev) => {
      const newTotal = prev + amount;
      return newTotal;
    });
  }

  useEffect(() => {
    if (!state) return;
    setLocalState([state]);
    setPreviousSelection({}); // Initialize empty previous selection at game start
  }, [state]);

  // Combined effect: Track previous asset states/phases AND handle auto-selection
  useEffect(() => {
    if (!activeState) return;

    let updatedPrevStates = previousAssetStates;
    let updatedPrevPhases = previousAssetPhases;
    let updatedPrevSelection = previousSelection;

    // Only update previous states if this is not the initial load
    // We check if localState has more than 1 item (meaning we've taken at least one step)
    if (localState.length > 1) {
      // Get the previous state's asset states and phases
      const previousState = localState[localState.length - 2];
      const previousAllAssets = extractAllAssets(previousState);
      const prevStates: Record<string, AssetSchemaType["state"]> = {};
      const prevPhases: Record<string, AssetSchemaType["pending_trial_phase"]> =
        {};

      previousAllAssets.forEach((asset) => {
        prevStates[asset.id] = asset.state;
        prevPhases[asset.id] = asset.pending_trial_phase;
      });

      updatedPrevStates = prevStates;
      updatedPrevPhases = prevPhases;

      // Update state for previous tracking
      setPreviousAssetStates(prevStates);
      setPreviousAssetPhases(prevPhases);
    }

    // Auto-select assets based on business rules (using updated previous phases)
    const assets = extractAssets(activeState);
    const levelsEnabled = activeState.investment_levels_enabled ?? false;

    const newSelection: Record<string, ActionType | boolean> = { ...selection };
    let totalCost = 0;

    // Helper to check if a selection value means "selected"
    const isSelectionActive = (
      val: ActionType | boolean | undefined,
    ): boolean => {
      if (val === true) return true;
      if (typeof val === "string" && val !== "none" && val !== "stop")
        return true;
      return false;
    };

    // Extract phase order from assets for phase progression logic
    // const availablePhases = extractPhasesFromAssets(assets);
    const phaseOrder = TRIAL_PHASES;

    assets.forEach((asset) => {
      const isIdle = asset.state === "Idle";
      const pendingPhase = asset.pending_trial_phase;
      const previousPhase = updatedPrevPhases[asset.id];
      const previousSelectionState = updatedPrevSelection[asset.id];
      const isStartOfGame = localState.length === 1; // First state after game start

      // Check if asset just moved to a new phase
      const justMovedToNewPhase =
        previousPhase &&
        previousPhase !== pendingPhase &&
        isPhaseProgression(
          previousPhase as TrialPhaseName,
          pendingPhase as TrialPhaseName,
          phaseOrder,
        );

      // Auto-select logic:
      if (isIdle && selection[asset.id] === undefined) {
        let shouldSelect: boolean;

        // Skip auto-selection on the very first step (time === 0)
        if (time === 0) {
          shouldSelect = false;
        } else if (isFirstPhase(pendingPhase ?? null)) {
          // Pre-clinical phase should default to off
          shouldSelect = false;
        } else if (isStartOfGame || justMovedToNewPhase) {
          // Start of game or just moved to new phase: default to on for post-preclinical phases
          shouldSelect = true;
        } else {
          // Otherwise, preserve the previous selection state
          shouldSelect =
            isSelectionActive(previousSelectionState) ||
            previousSelectionState === undefined;
        }

        // When investment levels are enabled, use "standard" as the default, otherwise use boolean
        newSelection[asset.id] = shouldSelect
          ? levelsEnabled
            ? ("standard" as ActionType)
            : true
          : levelsEnabled
            ? ("none" as ActionType)
            : false;
      }

      // Calculate total cost for selected assets
      if (isSelectionActive(newSelection[asset.id])) {
        totalCost += calculateTrialCost(asset);
      }
    });

    // Update selection and cash in pot
    setSelection(newSelection);
    setCashInPot(totalCost);
  }, [localState, previousSelection]); // Now depends on localState changes and previousSelection

  // Check for game over when activeState changes
  useEffect(() => {
    if (activeState?.game_ended) {
      setGameOver(true);
    }
  }, [activeState]);

  // Call Action Endpoint
  async function actionNextStep() {
    if (!gameId) return;

    const assets = activeState ? extractAssets(activeState) : [];
    let totalSpend = 0;
    let idleSpend = 0;
    let developmentSpend = 0;

    // Helper to check if a selection value means "selected for investment"
    const isSelected = (assetId: string): boolean => {
      const val = selection[assetId];
      if (val === true) return true;
      if (typeof val === "string" && val !== "none" && val !== "stop")
        return true;
      return false;
    };

    assets.forEach((asset) => {
      if (isSelected(asset.id)) {
        totalSpend += calculateTrialCost(asset);
        if (asset.state === "Idle") {
          idleSpend += calculateTrialCost(asset);
        }
      }
      // Add costs of assets already in development (these are committed costs)
      // But if "stop" action is selected, don't count it
      const actionVal = selection[asset.id];
      if (asset.state === "In Development" && actionVal !== "stop") {
        developmentSpend += calculateTrialCost(asset);
      }
    });

    // Allow overspending - the backend will end the game if capital goes negative
    setLoadingNextStep(true);
    setError("");
    try {
      // Transform selection to the format expected by the API
      // Convert { assetId: true } to { assetId: "invest" }
      // or { assetId: "standard" } to { assetId: "standard" }
      const actionPayload = Object.keys(selection).reduce(
        (acc, assetId) => {
          const selectionValue = selection[assetId];
          if (selectionValue === true) {
            // Legacy boolean selection -> invest
            acc[assetId] = "invest";
          } else if (
            typeof selectionValue === "string" &&
            selectionValue !== "none"
          ) {
            // String action type (minimal, standard, accelerated, stop)
            acc[assetId] = selectionValue;
          }
          // false or "none" -> don't include in payload
          return acc;
        },
        {} as Record<string, string>,
      );

      // TODO: Update to new API TypeSafe Pattern
      const response = (await stepGame(gameId, actionPayload)) as any;

      // The response is now the game state directly
      if (response) {
        pushState(response);
        // Check if game has ended
        if (response.game_ended) {
          setGameOver(true);
        }
        // Clear selection, reset cash in pot, clear hints, reset hint costs, and hide hint column after successful step
        setPreviousSelection(selection); // Save current selection before clearing
        setSelection({});
        setCashInPot(0);
        setHints({});
        setHintCosts(0);
        setSelectedAgentName("");
        setHintColumnVisible(false);

        // Show actionScreenTwo tour after first step (when localState will have 2 items: initial + first step)
        if (localState.length === 1) {
          startTourIfNotSkipped("actionScreenTwo", startNextStep);
        }
      }
    } catch (err) {
      // Error Handling
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

      // Game over logic
      message === "Game horizon reached"
        ? setGameOver(true)
        : setError(message);
    }
    setLoadingNextStep(false);
  }

  const assets = activeState ? extractAssets(activeState) : [];

  // Calculate next step cost for ActionStats using the same logic as spending warning
  const nextStepCost = useMemo(() => {
    if (!activeState) return 0;

    // Helper to check if a selection value means "selected for investment"
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
      // Add costs of assets already in development (these are committed costs)
      // But if "stop" action is selected, don't count it
      const actionVal = selection[asset.id];
      if (asset.state === "In Development" && actionVal !== "stop") {
        developmentSpend += calculateTrialCost(asset);
      }
    });

    // Total cost includes selected assets + assets already in development
    return totalSpend + developmentSpend;
  }, [assets, selection, activeState]);

  // Wrapper functions to handle gameOver state
  const handleGoBackToStart = async () => {
    setLoadingRestart(true);
    try {
      setGameOver(false);
      await goBackToStart();
    } finally {
      setLoadingRestart(false);
    }
  };

  const handleGoToNextLevel = async () => {
    setLoadingNextLevel(true);
    try {
      setGameOver(false);
      await goToNextLevel();
    } finally {
      setLoadingNextLevel(false);
    }
  };

  // Wrapper function for resetGame (new random game) to handle loading state
  const handleResetGame = async () => {
    setLoadingResetGame(true);
    try {
      setGameOver(false);
      await resetGame();
    } finally {
      setLoadingResetGame(false);
    }
  };

  // Wrapper function for restartSameGame (same seed) to handle loading state
  const handleRestartSameGame = async () => {
    setLoadingRestart(true);
    try {
      setGameOver(false);
      if (restartSameGame) {
        await restartSameGame();
      } else {
        await resetGame();
      }
    } finally {
      setLoadingRestart(false);
    }
  };

  return (
    <div className="mt-4">
      <LayoutContainer className="flex flex-col gap-1" maxWidth="1440px">
        {currentLevel && "level_idx" in currentLevel ? (
          <div>
            <Badge
              className="rounded-sm font-light uppercase"
              variant="secondary"
            >
              Level {currentLevel?.level_idx + 1}
            </Badge>
          </div>
        ) : null}
        {spendingWarning && (
          <div className="flex items-center gap-2 rounded-lg bg-yellow-50 px-3 py-2 text-xs font-light text-yellow-800 ring-1 ring-yellow-200">
            <Ban className="h-4 w-4 flex-shrink-0" />
            {spendingWarning}
          </div>
        )}

        {loadingRestart || loadingNextLevel || loadingResetGame ? (
          <LoaderList />
        ) : (
          <>
            {/* Main Content Row */}
            {gameOver ? (
              <>
                <ActionComparison
                  gameId={gameId || "691453fe-6afc-4fa4-b809-2275ce96263e"}
                  level={currentLevel?.level_idx}
                />
                <GameOverScreen
                  activeState={activeState}
                  onRestartSameGame={handleRestartSameGame}
                  onStartNewGame={handleResetGame}
                  loadingRestart={loadingRestart}
                  loadingNewGame={loadingResetGame}
                  gameConfig={gameConfig}
                  defaultConfig={defaultConfig}
                  onConfigChange={onConfigChange}
                />
              </>
            ) : (
              <>
                <div className="flex gap-4">
                  {/* Grouped Stats and Charts Section */}
                  <div className="flex flex-1 gap-4" id="actionStat">
                    <div className="flex flex-col justify-between gap-4">
                      {/* Stats */}
                      <ActionStats
                        time={time!}
                        startingCash={(startingCash || 0) - hintCosts}
                        previousCash={previousCash}
                        previousAssets={previousAssets}
                        cashInPot={cashInPot}
                        assets={assets}
                        selection={selection}
                        nextStepCost={nextStepCost}
                      />
                      <div className="w-full overflow-hidden">
                        <CapitalProjectionGraph
                          currentTime={time || 0}
                          currentCapital={(startingCash || 0) - hintCosts}
                          totalTime={activeState?.horizon || 10}
                          gameState={activeState || undefined}
                          width={Math.min(width || 350, 350)}
                        />
                      </div>
                    </div>

                    <div className="flex min-h-[300px] flex-1 flex-col gap-4">
                      <div className="w-full overflow-hidden">
                        <div ref={parentRef}>
                          <ActionChart
                            assets={assets}
                            selection={selection}
                            horizon={activeState?.horizon!}
                            currentTime={time}
                            gameState={activeState!}
                            dataType="cost"
                            width={Math.min(width || 500, 700)}
                            chartTitle="Total Cost this year:"
                            hintCosts={hintCosts}
                            infoLabel="costCurve"
                          />
                        </div>
                      </div>
                      <div className="w-full overflow-hidden">
                        <ActionChart
                          assets={assets}
                          selection={selection}
                          horizon={activeState?.horizon!}
                          currentTime={time}
                          gameState={activeState!}
                          dataType="revenue"
                          width={Math.min(width || 500, 700)}
                          chartTitle="Budget next year:"
                          hintCosts={0}
                          infoLabel="revenueCurve"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Controls Section - Separated */}
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
                      {!gameOver && (
                        <Button
                          onClick={actionNextStep}
                          disabled={loadingNextStep}
                          className="min-w-[120px]"
                          id="nextYearButton"
                        >
                          {loadingNextStep ? "Processing..." : "Next Year"}
                          <ArrowBigRight className="ml-2 h-4 w-4" />
                        </Button>
                      )}
                    </div>

                    <div className="flex w-full items-center gap-6 rounded-lg bg-gray-100 p-4">
                      {/* Timeline */}
                      <div className="flex flex-col items-start gap-0">
                        <span className="text-sm font-medium text-gray-600">
                          Progress:
                        </span>
                        <div className="w-[200px]">
                          <Timeline
                            currentTime={time || 0}
                            totalTime={activeState?.horizon || 10}
                          />
                        </div>
                      </div>
                    </div>

                    {/* TA Experience */}
                    {activeState?.ta_experience_enabled &&
                      activeState?.ta_experience &&
                      Object.keys(activeState.ta_experience).length > 0 && (
                        <div className="w-full overflow-hidden">
                          <TAExperience
                            taExperience={activeState.ta_experience}
                            maxExperience={
                              activeState.experience_to_full_knowledge
                            }
                            maxTotalExperience={
                              activeState.max_total_experience
                            }
                          />
                        </div>
                      )}

                    {/* R&D Capacity */}
                    {activeState?.investment_levels_enabled &&
                      activeState.capacity_used !== undefined &&
                      activeState.capacity_base !== undefined && (
                        <div className="w-full overflow-hidden">
                          <RDCapacity
                            capacityUsed={activeState.capacity_used}
                            capacityBase={activeState.capacity_base}
                            successModifier={activeState.success_modifier}
                            costModifier={activeState.cost_modifier}
                          />
                        </div>
                      )}

                    {/* Unlock Hint */}
                    {!gameOver && gameId && (
                      <UnlockHint
                        gameId={gameId}
                        onHintReceived={handleHintReceived}
                        onHintToggled={handleHintToggled}
                        onCashDeducted={handleCashDeducted}
                        currentCash={(startingCash || 0) - hintCosts}
                        resetKey={localState.length}
                        assets={activeState?.assets}
                      />
                    )}
                  </div>
                </div>
                <div className="mt-2 space-y-4">
                  {/* Error Display */}
                  {error && (
                    <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
                      <Ban className="h-5 w-5 flex-shrink-0" />
                      <span className="text-sm font-medium">{error}</span>
                    </div>
                  )}

                  {/* Asset Table */}
                  <div className="rounded-lg bg-white shadow-sm">
                    <AssetsTable
                      assets={activeState ? extractAllAssets(activeState) : []}
                      selection={selection}
                      onAssetSelection={handleAssetSelection}
                      onInvestmentLevelChange={handleInvestmentLevelChange}
                      investmentLevelsEnabled={investmentLevelsEnabled}
                      investmentLevelsConfig={investmentLevelsConfig}
                      interimObservationsEnabled={
                        activeState?.interim_observations_enabled ?? false
                      }
                      distributionalPtrsEnabled={distributionalPtrsEnabled}
                      previousAssetStates={previousAssetStates}
                      previousAssetPhases={previousAssetPhases}
                      hints={hints}
                      hintColumnVisible={hintColumnVisible}
                      selectedAgentName={selectedAgentName}
                      time={time}
                    />
                  </div>
                </div>
              </>
            )}
          </>
        )}
      </LayoutContainer>
    </div>
  );
}
