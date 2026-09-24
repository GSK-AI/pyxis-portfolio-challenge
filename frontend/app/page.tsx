"use client";

import {
  ActionType,
  GameStepResponse,
  GameStart,
  MultiAgentGameStep,
  MultiAgentGameStart,
  OpponentAgent,
} from "@/lib/definitionsGameZ";
import {
  getGameConfig,
  startGame,
  stepGame,
  getMultiAgentOpponents,
  getMultiAgentConfig,
  startMultiAgentGame,
  stepMultiAgentGame,
} from "@/lib/backendCallsGame";
import { useState, useCallback, useEffect } from "react";
import { ArrowRight, Gamepad2, Users, User, Eye } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Slider } from "@/components/ui/slider";
import GameExperienceV2, {
  type TurnIntents,
} from "@/components/v2/game/GameExperienceV2";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatDisplayNumber } from "@/lib/numbers";

type GameScreen = "start" | "action" | "multi-action";
type GameMode = "single" | "multi";

const enableSinglePlayer =
  process.env.NEXT_PUBLIC_ENABLE_SINGLE_PLAYER === "true";

// UI defaults shown on the start screen, applied over the backend config.
const UI_DEFAULTS = {
  num_assets: 35,
  horizon: 100,
  starting_cash: 10_000_000_000,
};

export default function InvestmentGame() {
  const [screen, setScreen] = useState<GameScreen>("start");
  // Always land on multiplayer. Single player stays reachable via the toggle
  // when NEXT_PUBLIC_ENABLE_SINGLE_PLAYER is on, but it is never the default.
  const [gameMode, setGameMode] = useState<GameMode>("multi");

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
  // BD action-space cap, converted from GBP millions (config) to GBP.
  const [bdMaxBid, setBdMaxBid] = useState(100_000 * 1e6);
  // Clinical-site auction bid cap, converted from GBP millions to GBP.
  const [siteMaxBid, setSiteMaxBid] = useState(100_000 * 1e6);
  const [selectedOpponents, setSelectedOpponents] = useState<string[]>([
    "knapsack",
  ]);

  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string>("");

  // Screens are component state, not routes — without these, browser back
  // leaves the app entirely. Entering a sub-screen pushes a history entry;
  // popping it returns to the start screen.
  useEffect(() => {
    if (screen !== "start") {
      window.history.pushState({ gameScreen: screen }, "");
    }
  }, [screen]);

  useEffect(() => {
    const onPopState = () => setScreen("start");
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  // Fetch configs on mount
  useEffect(() => {
    async function fetchConfigs() {
      try {
        const [config, opponents, maConfig] = await Promise.all([
          getGameConfig(),
          getMultiAgentOpponents(),
          getMultiAgentConfig(),
        ]);
        setGameConfig({ ...config, ...UI_DEFAULTS });
        setDefaultConfig({ ...config, ...UI_DEFAULTS });
        setAvailableOpponents(opponents);
        setMaxOpponents(maConfig.max_opponents ?? 1);
        if (typeof maConfig.bd_max_bid === "number") {
          setBdMaxBid(maConfig.bd_max_bid * 1e6);
        }
        if (typeof maConfig.site_max_bid === "number") {
          setSiteMaxBid(maConfig.site_max_bid * 1e6);
        }
        setMultiAgentConfig({
          num_assets: UI_DEFAULTS.num_assets,
          max_num_assets: maConfig.max_num_assets,
          horizon: UI_DEFAULTS.horizon,
          starting_cash: UI_DEFAULTS.starting_cash,
          global_seed: Math.floor(Math.random() * 1000000),
          num_opponents: 1,
          opponent_agents: ["knapsack"],
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

  // Handle opponent count change
  const handleNumOpponentsChange = (count: number) => {
    setNumOpponents(count);
    const newOpponents = [...selectedOpponents];
    while (newOpponents.length < count) {
      newOpponents.push("knapsack");
    }
    const sliced = newOpponents.slice(0, count);
    setSelectedOpponents(sliced);
    if (multiAgentConfig) {
      setMultiAgentConfig({
        ...multiAgentConfig,
        num_opponents: count,
        opponent_agents: sliced,
        num_assets: defaultConfig?.num_assets ?? multiAgentConfig.num_assets,
      });
    }
  };

  // Handle opponent type change
  const handleOpponentChange = (index: number, agentId: string) => {
    const newOpponents = [...selectedOpponents];
    newOpponents[index] = agentId;
    setSelectedOpponents(newOpponents);
    if (multiAgentConfig) {
      setMultiAgentConfig({
        ...multiAgentConfig,
        opponent_agents: newOpponents,
        num_assets: defaultConfig?.num_assets ?? multiAgentConfig.num_assets,
      });
    }
  };

  // --- v2 experience: advance one year with the collected intents ---
  const advanceYearSingle = useCallback(
    async (intents: TurnIntents) => {
      if (!gameState || gameState.game_ended) return;
      // Classic payload mapping: `true` → "invest"; level strings
      // ("minimal"/"standard"/"accelerated"/"stop") pass through.
      const actions: Record<string, string> = {};
      Object.entries(intents.invest).forEach(([id, val]) => {
        if (val === true) actions[id] = "invest";
        else if (typeof val === "string" && val !== "none") actions[id] = val;
      });
      Object.entries(intents.drop).forEach(([id, drop]) => {
        if (drop) actions[id] = "drop";
      });
      const response = await stepGame(gameState.id, actions);
      setGameState(response);
    },
    [gameState],
  );

  const advanceYearMulti = useCallback(
    async (intents: TurnIntents) => {
      if (!multiAgentState || multiAgentState.game_ended) return;
      // Classic payload mapping: `true` → "invest"; level strings
      // ("minimal"/"standard"/"accelerated"/"stop") pass through.
      const investmentActions: Record<string, ActionType> = {};
      Object.entries(intents.invest).forEach(([id, val]) => {
        if (val === true) investmentActions[id] = "invest";
        else if (typeof val === "string" && val !== "none")
          investmentActions[id] = val;
      });
      Object.entries(intents.drop).forEach(([id, drop]) => {
        if (drop) investmentActions[id] = "drop";
      });
      const ptrsResearch: Record<string, number> = {};
      Object.entries(intents.readings).forEach(([id, count]) => {
        if (count > 0) ptrsResearch[id] = count;
      });
      // BD bids are positional, aligned with the bd_assets on display —
      // fill unbid slots with 0 (classic parity).
      const bdBids = (multiAgentState.bd_assets ?? []).map(
        (_, index) => intents.bdBids[index] ?? 0,
      );
      const response = await stepMultiAgentGame(multiAgentState.game_id, {
        investment_actions: investmentActions,
        bd_bids: bdBids,
        upgrade: intents.buySite,
        site_bid: intents.siteBid,
        demand_creation: intents.demandCreation,
        brand_equity: intents.brandEquity,
        ptrs_research: ptrsResearch,
      });
      setMultiAgentState(response);
    },
    [multiAgentState],
  );

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
  }

  // Classic single-player option: replay the exact same game (same seed).
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
  if (screen === "multi-action") {
    return (
      <GameExperienceV2
        mode="multi"
        state={multiAgentState}
        onExit={startOver}
        onRestart={resetMultiAgentGame}
        onNextYear={advanceYearMulti}
        siteMaxBid={siteMaxBid}
        bdMaxBid={bdMaxBid}
      />
    );
  }

  if (screen === "action") {
    return (
      <GameExperienceV2
        mode="single"
        state={gameState}
        onExit={startOver}
        onRestart={startNewGame}
        onRestartSameGame={restartSameGame}
        onNextYear={advanceYearSingle}
      />
    );
  }

  return (
    <div className="-mb-4 -mt-6 font-light">
      <div className="relative mx-auto w-full max-w-[1920px] md:min-h-dvh">
        {/* Right: visual panel. Absolutely placed at a fixed half of the
            container so it never gets squeezed — below ~1400px the content
            column rides over it instead of both halves shrinking. */}
        <div className="absolute inset-y-0 right-0 hidden w-1/2 p-3 md:block">
          <div className="relative h-full min-h-[560px] overflow-hidden rounded bg-secondary">
            <div
              aria-hidden
              className="absolute inset-0 bg-[url('/images/tech-helix-color.webp')] bg-cover bg-center"
            />
            <Gamepad2
              aria-hidden
              className="absolute -bottom-10 -right-6 size-52 text-white/10"
            />
          </div>
        </div>

        {/* Left: title + settings + start. Holds a floor width and overlaps
            the image once the viewport can't fit both side by side. */}
        <div className="relative flex flex-col p-8 sm:p-12 md:min-h-dvh md:w-[max(50%,700px)] lg:px-16">
          {/* Glass: invisible over the white page, frosts the helix where
              the column overhangs it. Faded out at the overhanging edge so
              the panel has no hard seam. */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-background/85 backdrop-blur-sm"
            style={{
              maskImage: "linear-gradient(to right, black 92%, transparent)",
              WebkitMaskImage:
                "linear-gradient(to right, black 92%, transparent)",
            }}
          />
          <div className="relative">
            <Image
              src="/images/pyxis-app-icon-2.svg"
              alt="Pyxis"
              width={44}
              height={44}
            />
          </div>

          <div className="relative flex flex-1 flex-col justify-center space-y-8 py-10">
            <div className="space-y-4">
              <h1 className="text-4xl leading-[1.1] tracking-tight sm:text-5xl">
                <span className="block font-normal">Pyxis</span>
                <span className="block text-muted-foreground">
                  Portfolio Challenge
                </span>
              </h1>
              <p className="text-base leading-relaxed text-muted-foreground">
                A competition advancing AI decision-making under uncertainty.
                Train agents for long-horizon planning across stochastic R&D
                pipelines, competitive markets, and resource-constrained
                portfolio management.
              </p>
            </div>

            {/* Play section: heading + replay link + settings, tight group */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold">Play</h2>
                <Link
                  href="/replay"
                  className="flex items-center gap-1.5 text-sm text-primary hover:underline"
                >
                  <Eye className="size-4" />
                  Watch Replay
                  <ArrowRight className="size-4" />
                </Link>
              </div>

              {/* Settings skeleton — mirrors the real panel so nothing jumps */}
              {loading && (
                <div className="rounded bg-gradient-to-b from-secondary/50 to-secondary/10 p-5">
                  <Skeleton className="mb-5 h-5 w-20" />
                  <div className="space-y-5">
                    {[0, 1, 2].map((row) => (
                      <div key={row} className="flex items-center gap-4">
                        <Skeleton className="h-4 w-32" />
                        <Skeleton className="h-9 w-20 rounded" />
                        <Skeleton className="h-2 w-[240px] rounded-full" />
                      </div>
                    ))}
                    <div className="flex items-center gap-4">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-9 flex-1 rounded" />
                    </div>
                  </div>
                </div>
              )}

              {/* Game Mode Toggle — only when there is a real choice */}
              {enableSinglePlayer && (
                <div className="flex gap-2">
                  <Button
                    variant={gameMode === "single" ? "default" : "outline"}
                    onClick={() => setGameMode("single")}
                    size="sm"
                  >
                    <User className="mr-2 h-4 w-4" />
                    Single Player
                  </Button>
                  <Button
                    variant={gameMode === "multi" ? "default" : "outline"}
                    onClick={() => setGameMode("multi")}
                    size="sm"
                  >
                    <Users className="mr-2 h-4 w-4" />
                    Multiplayer
                  </Button>
                </div>
              )}

              {/* Single Player Config */}
              {gameMode === "single" && gameConfig && (
                <div className="rounded bg-gradient-to-b from-secondary/50 to-secondary/10 p-5">
                  <h3 className="mb-4 font-bold">Game Settings</h3>
                  <div className="space-y-4">
                    <div className="flex items-center gap-4">
                      <label className="w-32 text-sm text-muted-foreground">
                        Starting Assets
                      </label>
                      <div className="w-28">
                        <Input
                          type="number"
                          value={gameConfig.num_assets}
                          onChange={(e) =>
                            updateConfig(
                              "num_assets",
                              parseInt(e.target.value) || 5,
                            )
                          }
                          min={5}
                          max={50}
                          className="w-20 bg-card"
                        />
                      </div>
                      <Slider
                        value={[gameConfig.num_assets]}
                        onValueChange={([value]) =>
                          updateConfig("num_assets", value)
                        }
                        min={5}
                        max={50}
                        step={1}
                        className="max-w-[240px]"
                      />
                      <span className="text-xs text-muted-foreground/70">
                        (default: {defaultConfig?.num_assets})
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <label className="w-32 text-sm text-muted-foreground">
                        Horizon (years)
                      </label>
                      <div className="w-28">
                        <Input
                          type="number"
                          value={gameConfig.horizon}
                          onChange={(e) =>
                            updateConfig(
                              "horizon",
                              parseInt(e.target.value) || 25,
                            )
                          }
                          min={25}
                          max={1000}
                          className="w-20 bg-card"
                        />
                      </div>
                      <Slider
                        value={[gameConfig.horizon]}
                        onValueChange={([value]) =>
                          updateConfig("horizon", value)
                        }
                        min={25}
                        max={1000}
                        step={5}
                        className="max-w-[240px]"
                      />
                      <span className="text-xs text-muted-foreground/70">
                        (default: {defaultConfig?.horizon})
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <label className="w-32 text-sm text-muted-foreground">
                        Starting Cash
                      </label>
                      <div className="flex w-28 items-center gap-1.5">
                        <Input
                          type="number"
                          value={
                            Math.round(gameConfig.starting_cash / 1e8) / 10
                          }
                          onChange={(e) =>
                            updateConfig(
                              "starting_cash",
                              (parseFloat(e.target.value) || 1) * 1e9,
                            )
                          }
                          min={1}
                          max={100}
                          step={0.5}
                          className="w-20 bg-card"
                        />
                        <span className="text-sm text-muted-foreground">B</span>
                      </div>
                      <Slider
                        value={[gameConfig.starting_cash]}
                        onValueChange={([value]) =>
                          updateConfig("starting_cash", value)
                        }
                        min={1e9}
                        max={100e9}
                        step={1e9}
                        className="max-w-[240px]"
                      />
                      <span className="text-xs text-muted-foreground/70">
                        (default:{" "}
                        {formatDisplayNumber(defaultConfig?.starting_cash || 0)}
                        )
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Multiplayer Config */}
              {gameMode === "multi" && multiAgentConfig && (
                <div className="rounded bg-gradient-to-b from-secondary/50 to-secondary/10 p-5">
                  <h3 className="mb-4 font-bold">Settings</h3>
                  <div className="space-y-4">
                    <div className="flex items-center gap-4">
                      <label className="w-32 text-sm text-muted-foreground">
                        Starting Assets
                      </label>
                      <div className="w-28">
                        <Input
                          type="number"
                          value={multiAgentConfig.num_assets}
                          onChange={(e) =>
                            updateMultiConfig(
                              "num_assets",
                              parseInt(e.target.value) || 5,
                            )
                          }
                          min={5}
                          max={50}
                          className="w-20 bg-card"
                        />
                      </div>
                      <Slider
                        value={[multiAgentConfig.num_assets]}
                        onValueChange={([value]) =>
                          updateMultiConfig("num_assets", value)
                        }
                        min={5}
                        max={50}
                        step={1}
                        className="max-w-[240px]"
                      />
                    </div>
                    <div className="flex items-center gap-4">
                      <label className="w-32 text-sm text-muted-foreground">
                        Horizon (years)
                      </label>
                      <div className="w-28">
                        <Input
                          type="number"
                          value={multiAgentConfig.horizon}
                          onChange={(e) =>
                            updateMultiConfig(
                              "horizon",
                              parseInt(e.target.value) || 25,
                            )
                          }
                          min={25}
                          max={1000}
                          className="w-20 bg-card"
                        />
                      </div>
                      <Slider
                        value={[multiAgentConfig.horizon]}
                        onValueChange={([value]) =>
                          updateMultiConfig("horizon", value)
                        }
                        min={25}
                        max={1000}
                        step={5}
                        className="max-w-[240px]"
                      />
                    </div>
                    <div className="flex items-center gap-4">
                      <label className="w-32 text-sm text-muted-foreground">
                        Starting Cash
                      </label>
                      <div className="flex w-28 items-center gap-1.5">
                        <Input
                          type="number"
                          value={
                            Math.round(multiAgentConfig.starting_cash / 1e8) /
                            10
                          }
                          onChange={(e) =>
                            updateMultiConfig(
                              "starting_cash",
                              (parseFloat(e.target.value) || 1) * 1e9,
                            )
                          }
                          min={1}
                          max={100}
                          step={0.5}
                          className="w-20 bg-card"
                        />
                        <span className="text-sm text-muted-foreground">B</span>
                      </div>
                      <Slider
                        value={[multiAgentConfig.starting_cash]}
                        onValueChange={([value]) =>
                          updateMultiConfig("starting_cash", value)
                        }
                        min={1e9}
                        max={100e9}
                        step={1e9}
                        className="max-w-[240px]"
                      />
                    </div>

                    {/* Opponent Count */}
                    {maxOpponents > 1 && (
                      <div className="flex items-center gap-4">
                        <label className="w-32 text-sm text-muted-foreground">
                          Opponents
                        </label>
                        <div className="flex gap-2">
                          {Array.from(
                            { length: maxOpponents },
                            (_, i) => i + 1,
                          ).map((n) => (
                            <Button
                              key={n}
                              variant={
                                numOpponents === n ? "default" : "outline"
                              }
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
                        <label className="w-32 text-sm text-muted-foreground">
                          Opponent
                        </label>
                        <Select
                          value={selectedOpponents[i] || "knapsack"}
                          onValueChange={(value) =>
                            handleOpponentChange(i, value)
                          }
                        >
                          <SelectTrigger className="flex-1 bg-card">
                            <SelectValue placeholder="Select an opponent" />
                          </SelectTrigger>
                          <SelectContent>
                            {availableOpponents.map((agent) => (
                              <SelectItem key={agent.id} value={agent.id}>
                                {agent.name}
                                <span className="text-muted-foreground">
                                  {" "}
                                  — {agent.description}
                                </span>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Start Button */}
            <div className="max-w-sm">
              <Button
                size="lg"
                className="w-full rounded"
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
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
