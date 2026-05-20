"use client";

import ActionGame from "@/components/InvestmentGame/Action";
import MultiAgentAction from "@/components/InvestmentGame/MultiAgentAction";
import {
  GameStepResponse,
  GameStart,
  MultiAgentGameStep,
  MultiAgentGameStart,
  OpponentAgent,
  PlaythroughData,
} from "@/lib/definitionsGameZ";
import {
  getGameConfig,
  startGame,
  getMultiAgentOpponents,
  getMultiAgentConfig,
  startMultiAgentGame,
} from "@/lib/backendCallsGame";
import { useState, useCallback, useEffect } from "react";
import { useHomeScreen } from "@/context/HomeScreenContext";
import { ArrowRight, Gamepad2, Users, User, Eye } from "lucide-react";
import PlaythroughViewer from "@/components/InvestmentGame/Replay/PlaythroughViewer";
import FileUploadArea from "@/components/InvestmentGame/Replay/FileUploadArea";
import LayoutContainer from "@/components/LayoutContainer";
import TheTitle from "@/components/TheTitle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatDisplayNumber } from "@/lib/numbers";

type GameScreen =
  | "start"
  | "action"
  | "multi-action"
  | "replay-upload"
  | "replay";
type GameMode = "single" | "multi";

const enableSinglePlayer =
  process.env.NEXT_PUBLIC_ENABLE_SINGLE_PLAYER === "true";

export default function InvestmentGame() {
  const [screen, setScreen] = useState<GameScreen>("start");
  const [gameMode, setGameMode] = useState<GameMode>(
    enableSinglePlayer ? "single" : "multi",
  );

  // Single-agent state
  const [gameState, setGameState] = useState<GameStepResponse | undefined>(
    undefined,
  );
  const [gameConfig, setGameConfig] = useState<GameStart | null>(null);
  const [defaultConfig, setDefaultConfig] = useState<GameStart | null>(null);

  // Multi-agent state
  const [multiAgentState, setMultiAgentState] = useState<
    MultiAgentGameStep | undefined
  >(undefined);
  const [multiAgentConfig, setMultiAgentConfig] =
    useState<MultiAgentGameStart | null>(null);
  const [availableOpponents, setAvailableOpponents] = useState<OpponentAgent[]>(
    [],
  );
  const [numOpponents, setNumOpponents] = useState(1);
  const [maxOpponents, setMaxOpponents] = useState(1);
  const [selectedOpponents, setSelectedOpponents] = useState<string[]>([
    "knapsack_cap12",
  ]);

  // Replay state
  const [playthroughData, setPlaythroughData] =
    useState<PlaythroughData | null>(null);

  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string>("");

  const { setIsHomeScreen } = useHomeScreen();
  useEffect(() => {
    setIsHomeScreen(screen === "start");
  }, [screen, setIsHomeScreen]);

  // Fetch configs on mount
  useEffect(() => {
    async function fetchConfigs() {
      try {
        const [config, opponents, maConfig] = await Promise.all([
          getGameConfig(),
          getMultiAgentOpponents(),
          getMultiAgentConfig(),
        ]);
        setGameConfig(config);
        setDefaultConfig(config);
        setAvailableOpponents(opponents);
        setMaxOpponents(maConfig.max_opponents ?? 1);
        setMultiAgentConfig({
          num_assets: maConfig.num_assets,
          max_num_assets: maConfig.max_num_assets,
          horizon: maConfig.horizon,
          starting_cash: maConfig.starting_cash,
          global_seed: Math.floor(Math.random() * 1000000),
          num_opponents: 1,
          opponent_agents: ["knapsack_cap12"],
        });
      } catch (err) {
        console.error("Failed to fetch configs:", err);
        setError("Failed to load game configuration.");
      } finally {
        setLoading(false);
      }
    }
    fetchConfigs();
  }, []);

  // Update single-agent config field
  const updateConfig = (field: keyof GameStart, value: number) => {
    if (!gameConfig) return;
    setGameConfig({ ...gameConfig, [field]: value });
  };

  // Update multi-agent config field
  const updateMultiConfig = (
    field: keyof MultiAgentGameStart,
    value: number,
  ) => {
    if (!multiAgentConfig) return;
    setMultiAgentConfig({ ...multiAgentConfig, [field]: value });
  };

  // Pyxie's PPO model requires a fixed observation space (35 starting assets)
  const PYXIE_FIXED_NUM_ASSETS = 35;

  // Handle opponent count change
  const handleNumOpponentsChange = (count: number) => {
    setNumOpponents(count);
    const newOpponents = [...selectedOpponents];
    while (newOpponents.length < count) {
      newOpponents.push("knapsack_cap12");
    }
    const sliced = newOpponents.slice(0, count);
    setSelectedOpponents(sliced);
    const hasPyxie = sliced.includes("pyxie");
    if (multiAgentConfig) {
      setMultiAgentConfig({
        ...multiAgentConfig,
        num_opponents: count,
        opponent_agents: sliced,
        num_assets: hasPyxie
          ? PYXIE_FIXED_NUM_ASSETS
          : (defaultConfig?.num_assets ?? multiAgentConfig.num_assets),
      });
    }
  };

  // Handle opponent type change
  const handleOpponentChange = (index: number, agentId: string) => {
    const newOpponents = [...selectedOpponents];
    newOpponents[index] = agentId;
    setSelectedOpponents(newOpponents);
    const hasPyxie = newOpponents.slice(0, numOpponents).includes("pyxie");
    if (multiAgentConfig) {
      setMultiAgentConfig({
        ...multiAgentConfig,
        opponent_agents: newOpponents,
        num_assets: hasPyxie
          ? PYXIE_FIXED_NUM_ASSETS
          : (defaultConfig?.num_assets ?? multiAgentConfig.num_assets),
      });
    }
  };

  // --- Single-Agent Handlers ---
  async function handleStartGame() {
    if (!gameConfig) return;
    setStarting(true);
    setError("");
    try {
      const response = await startGame(gameConfig);
      setGameState(response);
      setScreen("action");
    } catch (err) {
      console.error("Failed to start game:", err);
      setError("Failed to start the game. Please try again.");
    } finally {
      setStarting(false);
    }
  }

  function startOver() {
    setScreen("start");
    setGameState(undefined);
    setMultiAgentState(undefined);
    setPlaythroughData(null);
  }

  const restartSameGame = useCallback(async () => {
    if (!gameConfig) {
      startOver();
      return;
    }
    try {
      const response = await startGame(gameConfig);
      setGameState(response);
    } catch (err) {
      console.error("Failed to restart same game:", err);
      startOver();
    }
  }, [gameConfig]);

  const startNewGame = useCallback(async () => {
    if (!gameConfig) {
      startOver();
      return;
    }
    try {
      const newConfig = {
        ...gameConfig,
        global_seed: Math.floor(Math.random() * 1000000),
      };
      const response = await startGame(newConfig);
      setGameState(response);
      setGameConfig(newConfig);
    } catch (err) {
      console.error("Failed to start new game:", err);
      startOver();
    }
  }, [gameConfig]);

  // --- Multi-Agent Handlers ---
  async function handleStartMultiAgentGame() {
    if (!multiAgentConfig) return;
    setStarting(true);
    setError("");
    try {
      const response = await startMultiAgentGame(multiAgentConfig);
      setMultiAgentState(response);
      setScreen("multi-action");
    } catch (err) {
      console.error("Failed to start multi-agent game:", err);
      setError("Failed to start the game. Please try again.");
    } finally {
      setStarting(false);
    }
  }

  const resetMultiAgentGame = useCallback(async () => {
    if (!multiAgentConfig) {
      startOver();
      return;
    }
    try {
      const newConfig = {
        ...multiAgentConfig,
        global_seed: Math.floor(Math.random() * 1000000),
      };
      const response = await startMultiAgentGame(newConfig);
      setMultiAgentState(response);
      setMultiAgentConfig(newConfig);
    } catch (err) {
      console.error("Failed to reset multi-agent game:", err);
      startOver();
    }
  }, [multiAgentConfig]);

  // --- Render ---
  if (screen === "replay" && playthroughData) {
    return (
      <PlaythroughViewer
        data={playthroughData}
        onExit={() => {
          setPlaythroughData(null);
          setScreen("start");
        }}
      />
    );
  }

  if (screen === "replay-upload") {
    return (
      <FileUploadArea
        onPlaythroughLoaded={(data) => {
          setPlaythroughData(data);
          setScreen("replay");
        }}
        onCancel={() => setScreen("start")}
      />
    );
  }

  if (screen === "multi-action") {
    return (
      <MultiAgentAction
        state={multiAgentState}
        resetGame={resetMultiAgentGame}
        goBackToStart={startOver}
      />
    );
  }

  if (screen === "action") {
    return (
      <ActionGame
        state={gameState}
        currentLevel={null}
        resetGame={startNewGame}
        restartSameGame={restartSameGame}
        goBackToStart={startOver}
        goToNextLevel={startOver}
        gameConfig={gameConfig}
        defaultConfig={defaultConfig}
        onConfigChange={updateConfig}
      />
    );
  }

  return (
    <div className="mt-6 px-6">
      <LayoutContainer className="c-splash-screen flex min-h-[75vh] rounded-2xl bg-gray-800 !p-8 text-white">
        <div className="relative z-20 flex flex-1 items-center rounded-2xl bg-white p-20 text-black">
          <div className="space-y-10">
            <div>
              <Gamepad2 />
            </div>
            <TheTitle>
              Pyxis
              <br />
              Portfolio Challenge
            </TheTitle>
            <p className="font-light">
              A competition advancing AI decision-making under uncertainty.
              Train agents for long-horizon planning across stochastic R&D
              pipelines, competitive markets, and resource-constrained portfolio
              management.
            </p>

            {/* Game Mode Toggle */}
            <div className="flex gap-2">
              {enableSinglePlayer && (
                <Button
                  variant={gameMode === "single" ? "default" : "outline"}
                  onClick={() => setGameMode("single")}
                  size="sm"
                >
                  <User className="mr-2 h-4 w-4" />
                  Single Player
                </Button>
              )}
              <Button
                variant={gameMode === "multi" ? "default" : "outline"}
                onClick={() => setGameMode("multi")}
                size="sm"
              >
                <Users className="mr-2 h-4 w-4" />
                Multiplayer
              </Button>
              <Button
                variant="outline"
                onClick={() => setScreen("replay-upload")}
                size="sm"
              >
                <Eye className="mr-2 h-4 w-4" />
                Watch Replay
              </Button>
            </div>

            {/* Single Player Config */}
            {gameMode === "single" && gameConfig && (
              <div className="rounded-lg bg-gray-100 p-4">
                <h3 className="mb-4 font-semibold">Game Settings</h3>
                <div className="space-y-4">
                  <div className="flex items-center gap-4">
                    <label className="w-32 text-sm text-gray-600">
                      Starting Assets
                    </label>
                    <Input
                      type="number"
                      value={gameConfig.num_assets}
                      onChange={(e) =>
                        updateConfig(
                          "num_assets",
                          parseInt(e.target.value) || 1,
                        )
                      }
                      min={1}
                      max={50}
                      className="w-24"
                    />
                    <span className="text-xs text-gray-400">
                      (default: {defaultConfig?.num_assets})
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <label className="w-32 text-sm text-gray-600">
                      Horizon (years)
                    </label>
                    <Input
                      type="number"
                      value={gameConfig.horizon}
                      onChange={(e) =>
                        updateConfig("horizon", parseInt(e.target.value) || 1)
                      }
                      min={1}
                      max={200}
                      className="w-24"
                    />
                    <span className="text-xs text-gray-400">
                      (default: {defaultConfig?.horizon})
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <label className="w-32 text-sm text-gray-600">
                      Starting Cash
                    </label>
                    <Input
                      type="number"
                      value={gameConfig.starting_cash}
                      onChange={(e) =>
                        updateConfig(
                          "starting_cash",
                          parseFloat(e.target.value) || 0,
                        )
                      }
                      min={0}
                      step={100000000}
                      className="w-40"
                    />
                    <span className="text-xs text-gray-400">
                      (default:{" "}
                      {formatDisplayNumber(defaultConfig?.starting_cash || 0)})
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Multiplayer Config */}
            {gameMode === "multi" && multiAgentConfig && (
              <div className="rounded-lg bg-gray-100 p-4">
                <h3 className="mb-4 font-semibold">Multiplayer Settings</h3>
                <div className="space-y-4">
                  <div className="flex items-center gap-4">
                    <label className="w-32 text-sm text-gray-600">
                      Starting Assets
                    </label>
                    <Input
                      type="number"
                      value={multiAgentConfig.num_assets}
                      onChange={(e) =>
                        updateMultiConfig(
                          "num_assets",
                          parseInt(e.target.value) || 1,
                        )
                      }
                      min={1}
                      max={50}
                      className="w-24"
                      disabled={selectedOpponents
                        .slice(0, numOpponents)
                        .includes("pyxie")}
                    />
                    {selectedOpponents
                      .slice(0, numOpponents)
                      .includes("pyxie") && (
                      <span className="text-xs text-gray-400">
                        Fixed at {PYXIE_FIXED_NUM_ASSETS} for Pyxie
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4">
                    <label className="w-32 text-sm text-gray-600">
                      Horizon (years)
                    </label>
                    <Input
                      type="number"
                      value={multiAgentConfig.horizon}
                      onChange={(e) =>
                        updateMultiConfig(
                          "horizon",
                          parseInt(e.target.value) || 1,
                        )
                      }
                      min={1}
                      max={200}
                      className="w-24"
                    />
                  </div>
                  <div className="flex items-center gap-4">
                    <label className="w-32 text-sm text-gray-600">
                      Starting Cash
                    </label>
                    <Input
                      type="number"
                      value={multiAgentConfig.starting_cash}
                      onChange={(e) =>
                        updateMultiConfig(
                          "starting_cash",
                          parseFloat(e.target.value) || 0,
                        )
                      }
                      min={0}
                      step={100000000}
                      className="w-40"
                    />
                  </div>

                  {/* Opponent Count */}
                  {maxOpponents > 1 && (
                    <div className="flex items-center gap-4">
                      <label className="w-32 text-sm text-gray-600">
                        Opponents
                      </label>
                      <div className="flex gap-2">
                        {Array.from(
                          { length: maxOpponents },
                          (_, i) => i + 1,
                        ).map((n) => (
                          <Button
                            key={n}
                            variant={numOpponents === n ? "default" : "outline"}
                            size="sm"
                            onClick={() => handleNumOpponentsChange(n)}
                          >
                            {n}
                          </Button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Opponent Type Selection */}
                  {Array.from({ length: numOpponents }).map((_, i) => (
                    <div key={i} className="flex items-center gap-4">
                      <label className="w-32 text-sm text-gray-600">
                        Opponent
                      </label>
                      <select
                        value={selectedOpponents[i] || "knapsack_cap12"}
                        onChange={(e) =>
                          handleOpponentChange(i, e.target.value)
                        }
                        className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                      >
                        {availableOpponents.map((agent) => (
                          <option key={agent.id} value={agent.id}>
                            {agent.name} - {agent.description}
                          </option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Loading State */}
            {loading && (
              <div className="text-gray-500">Loading game configuration...</div>
            )}

            {/* Start Button */}
            <div className="flex">
              <Button
                onClick={
                  gameMode === "single"
                    ? handleStartGame
                    : handleStartMultiAgentGame
                }
                disabled={
                  loading ||
                  starting ||
                  (gameMode === "single" ? !gameConfig : !multiAgentConfig)
                }
              >
                {starting ? "Starting..." : "Start Game"} <ArrowRight />
              </Button>
            </div>

            {/* Error Message */}
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
        </div>
      </LayoutContainer>
    </div>
  );
}
