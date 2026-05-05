"use client";

import { useState, useEffect } from "react";
import {
  ArrowRight,
  Gamepad2,
  CheckCircle,
  Lock,
  Trophy,
  Star,
  X,
} from "lucide-react";
import LayoutContainer from "@/components/LayoutContainer";
import TheTitle from "@/components/TheTitle";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  startGame,
  getLevels,
  getGlobalLeaderboard,
  getLevelLeaderboard,
} from "@/lib/backendCallsGame";
import { formatDisplayNumber } from "@/lib/numbers";

import type {
  GameStart,
  GameStepResponse,
  GameLevel,
  LeaderboardEntry,
} from "@/lib/definitionsGameZ";
import { cn } from "@/lib/utils";
import { LoaderList } from "../LoaderList";
import { LoaderListMini } from "../LoaderListMini";
import { useNextStep } from "nextstepjs";
import { useCustomNextStep } from "@/hooks/use-custom-next-step";

export default function StartLevels({
  handleStartGameCallback,
  setCustomStart,
}: {
  handleStartGameCallback: (obj: GameStepResponse, level?: GameLevel) => void;
  setCustomStart: (value: boolean) => void;
}) {
  const { startNextStep } = useNextStep();
  const { startTourIfNotSkipped } = useCustomNextStep();

  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string>("");
  const [levels, setLevels] = useState<GameLevel[]>([]);
  const [selectedLevel, setSelectedLevel] = useState<GameLevel | null>(null);
  const [loadingLevels, setLoadingLevels] = useState(false);
  const [globalLeaderboard, setGlobalLeaderboard] = useState<
    LeaderboardEntry[]
  >([]);
  const [levelLeaderboard, setLevelLeaderboard] = useState<LeaderboardEntry[]>(
    [],
  );
  const [loadingGlobalLeaderboard, setLoadingGlobalLeaderboard] =
    useState(false);
  const [loadingLevelLeaderboard, setLoadingLevelLeaderboard] = useState(false);

  // Fetch levels and global leaderboard on component mount
  useEffect(() => {
    async function fetchData() {
      setLoadingLevels(true);
      setLoadingGlobalLeaderboard(true);

      try {
        // Fetch levels and global leaderboard in parallel
        const [levelsData, leaderboardData] = await Promise.all([
          getLevels(),
          getGlobalLeaderboard(),
        ]);
        setLevels(levelsData);
        setGlobalLeaderboard(leaderboardData);
        const nextLevel = findNextLevel(levelsData);
        setSelectedLevel(nextLevel);

        // Fetch leaderboard for the selected next level
        if (nextLevel) {
          setLoadingLevelLeaderboard(true);
          try {
            const levelLeaderboardData = await getLevelLeaderboard(
              nextLevel.level_idx,
            );
            setLevelLeaderboard(levelLeaderboardData);
          } catch (err) {
            console.error("Failed to fetch next level leaderboard:", err);
            setLevelLeaderboard([]);
          } finally {
            setLoadingLevelLeaderboard(false);
          }
        }

        startTourIfNotSkipped("startScreen", startNextStep);
      } catch (err) {
        console.error("Failed to fetch data:", err);
        setError("Failed to load data. Please try again.");
      } finally {
        setLoadingLevels(false);
        setLoadingGlobalLeaderboard(false);
      }
    }

    fetchData();
  }, []);

  async function handleLevelSelect(level: GameLevel) {
    setSelectedLevel(level);

    // Fetch level-specific leaderboard
    setLoadingLevelLeaderboard(true);
    try {
      const levelLeaderboardData = await getLevelLeaderboard(level.level_idx);
      setLevelLeaderboard(levelLeaderboardData);
    } catch (err) {
      console.error("Failed to fetch level leaderboard:", err);
      setLevelLeaderboard([]);
    } finally {
      setLoadingLevelLeaderboard(false);
    }
  }

  async function startGameCallback() {
    if (!selectedLevel) return;
    setStarting(true);
    setError(""); // Clear any previous errors
    try {
      const gameStart: GameStart = {
        num_assets: selectedLevel.num_assets,
        max_num_assets: selectedLevel.max_num_assets,
        horizon: selectedLevel.horizon,
        starting_cash: selectedLevel.starting_cash,
        level_idx: selectedLevel.level_idx,
        global_seed: selectedLevel.global_seed,
      };
      const response = await startGame(gameStart);
      setStarting(false);
      handleStartGameCallback(response, selectedLevel);
    } catch (err) {
      console.error(err);
      setStarting(false);
      setError("Failed to start the game. Please try again.");
    }
  }

  function findNextLevel(levels: GameLevel[]) {
    // Find the first level that the user has not completed
    const nextLevel = levels.find((level) => !level.user_has_completed);
    // If all levels are completed, return the last level
    return nextLevel || levels[levels.length - 1];
  }

  function getMarginLeft(levelId: number) {
    const offset = levelId % 2 === 0 ? 10 : 50;
    return offset + levelId * 5;
  }

  function isLevelLocked(levelId: number) {
    // TEMPORARY: Always show level 2 as unlocked for testing
    // if (levelId === 2) return false;

    const currentLevelIdx =
      levels.find((level) => !level.user_has_completed)?.level_idx ??
      levels.length;
    return levelId > currentLevelIdx;
  }

  return (
    <div className="mt-6 px-6">
      <LayoutContainer className="c-splash-screen flex min-h-[75vh] gap-6 rounded-2xl bg-gray-800 !p-8 text-white">
        <div className="relative z-20 flex max-w-[500px] flex-1 items-center rounded-2xl bg-white p-10 text-black">
          <div className="w-full space-y-6">
            <div>
              <div>
                <Gamepad2 />
              </div>
            </div>
            <TheTitle>
              Welcome to the
              <br />
              Investment Game
            </TheTitle>
            <p className="font-light">Choose the level to play</p>

            {/* Disclaimer */}
            <div className="min-h-[10px]">
              {selectedLevel && (
                <div className="rounded-lg bg-gray-100 p-4">
                  <div className="flex items-center justify-between">
                    <h1 className="mb-2 text-lg font-bold">
                      Level {selectedLevel?.level_idx + 1}
                    </h1>
                    <Button
                      variant="ghost"
                      onClick={() => setSelectedLevel(null)}
                    >
                      <X />
                    </Button>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="flex flex-col rounded bg-gray-200 p-4">
                      <p className="text-sm">Assets</p>
                      <p className="text-lg">{selectedLevel?.num_assets}</p>
                    </div>

                    <div className="flex flex-col rounded bg-gray-200 p-4">
                      <p className="text-sm">Horizon</p>
                      <p className="text-lg">{selectedLevel?.horizon} years</p>
                    </div>
                    <div className="flex flex-1 flex-col rounded bg-gray-200 p-4">
                      <p className="text-sm">Starting Cash</p>
                      <p className="text-lg">
                        £{formatDisplayNumber(selectedLevel?.starting_cash)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between">
                    <p className="flex items-center gap-2 text-sm">
                      Status:
                      {selectedLevel?.user_has_completed ? (
                        <>
                          <CheckCircle className="h-3 w-3 text-green-600" />{" "}
                          <span>Completed</span>
                        </>
                      ) : (
                        <span>Not Completed</span>
                      )}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Loading State */}
            {loadingLevels && <LoaderListMini />}

            {/* Levels Grid */}
            {!loadingLevels && levels.length > 0 && (
              <div className="flex flex-col gap-4 pl-20">
                {levels.map((level) => (
                  <div
                    key={level.level_idx}
                    onClick={() => handleLevelSelect(level)}
                    className={cn(
                      "flex h-[60px] w-[60px] cursor-pointer items-center justify-center rounded-full border p-4 shadow-md transition-all hover:shadow-xl",
                      {
                        "border-gray-200 bg-gray-100 hover:bg-gray-200": true,
                        "pointer-events-none opacity-50": starting,
                        "bg-blue-500 text-white hover:bg-blue-600":
                          selectedLevel?.level_idx === level.level_idx,
                        "opacity-80": isLevelLocked(level.level_idx),
                      },
                    )}
                    style={{
                      marginLeft: `${getMarginLeft(level.level_idx)}px`,
                    }}
                  >
                    {isLevelLocked(level.level_idx) ? (
                      <div
                        className="opacity-30"
                        id={`level${level.level_idx}`}
                      >
                        <Lock size={16} />
                      </div>
                    ) : (
                      <div
                        className="flex items-center justify-center"
                        id={`level${level.level_idx}`}
                      >
                        {[...Array(level.level_idx + 1)].map((_, i) => (
                          <Star
                            key={i}
                            size={16}
                            className={cn("fill-gray-600 text-gray-600", {
                              "fill-yellow-400 stroke-yellow-500 stroke-1 text-yellow-400":
                                level.user_has_completed,
                              "fill-gray-50 text-gray-50":
                                selectedLevel?.level_idx === level.level_idx &&
                                !level.user_has_completed,
                            })}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Custom Game Link */}
            <div className="flex flex-col items-end justify-end space-y-4 border-t-0 pt-6">
              {/* Controls */}
              <div className="flex items-center gap-2">
                <Button
                  disabled={
                    starting ||
                    !selectedLevel ||
                    isLevelLocked(selectedLevel?.level_idx)
                  }
                  onClick={startGameCallback}
                  id="startGame"
                >
                  {starting ? "Starting" : "Start"} <ArrowRight />
                </Button>
              </div>

              {/* Error Message */}
              {error && <p className="text-sm text-red-600">{error}</p>}

              <div
                onClick={() => setCustomStart(true)}
                className="absolute right-6 top-2 cursor-pointer text-sm font-light text-gray-600 hover:text-blue-800"
              >
                Custom Game Settings
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-1 flex-col">
          {/* Global Leaderboard */}
          <div className="mb-6 rounded-lg bg-gray-50 p-6 text-black">
            <div className="mb-4 flex items-center gap-2">
              <Trophy className="h-5 w-5" />
              <h3 className="text-lg font-semibold">Global Leaderboard</h3>
            </div>

            {loadingGlobalLeaderboard && <LoaderList />}

            {!loadingGlobalLeaderboard && globalLeaderboard.length > 0 && (
              <TooltipProvider>
                <div className="max-h-[200px] space-y-2 overflow-y-auto">
                  {globalLeaderboard.map((entry, index) => (
                    <div
                      key={entry.user_id}
                      className={`flex items-center justify-between rounded p-3 ${
                        index === 0
                          ? "bg-yellow-500/20"
                          : index === 1
                            ? "bg-gray-400/20"
                            : index === 2
                              ? "bg-orange-600/20"
                              : "bg-white/5"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-6 text-center font-bold">
                          {index + 1}
                        </div>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div className="max-w-[200px] truncate text-sm font-medium">
                              {entry.user_id}
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{entry.user_id}</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <div className="flex gap-4 text-xs">
                        <div>
                          Avg eNPV: £{formatDisplayNumber(entry.av_enpv)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </TooltipProvider>
            )}

            {!loadingGlobalLeaderboard && globalLeaderboard.length === 0 && (
              <div className="text-center">
                No global leaderboard data available
              </div>
            )}
          </div>

          {/* Level-Specific Leaderboard (shown when level is selected) */}
          {selectedLevel && (
            <div className="mb-6 flex-1 rounded-lg border border-white/20 bg-gray-200 p-6 text-black">
              <div className="mb-4 flex items-center gap-2">
                <Trophy className="h-5 w-5 text-blue-400" />
                <h3 className="text-lg font-semibold text-blue-400">
                  Level {selectedLevel.level_idx + 1} Leaderboard
                </h3>
              </div>

              {loadingLevelLeaderboard && <LoaderList />}

              {!loadingLevelLeaderboard && levelLeaderboard.length > 0 && (
                <TooltipProvider>
                  <div className="max-h-[50vh] space-y-2 overflow-y-auto">
                    {levelLeaderboard.map((entry, index) => (
                      <div
                        key={entry.user_id}
                        className={`flex items-center justify-between rounded p-3 ${
                          index === 0
                            ? "bg-blue-500/20"
                            : index === 1
                              ? "bg-blue-400/15"
                              : index === 2
                                ? "bg-blue-300/10"
                                : "bg-white/5"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-6 text-center font-bold">
                            {index + 1}
                          </div>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <div className="max-w-[180px] truncate pr-10 text-sm font-medium">
                                {entry.user_id}
                              </div>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>{entry.user_id}</p>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                        <div className="flex gap-4 text-xs">
                          <div>
                            Avg eNPV: £{formatDisplayNumber(entry.av_enpv)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </TooltipProvider>
              )}

              {!loadingLevelLeaderboard && levelLeaderboard.length === 0 && (
                <div className="text-center text-gray-400">
                  No scores for this level yet
                </div>
              )}

              <p className="pt-2 text-xs font-light">
                Only your first attempt counts towards the leaderboard
              </p>
            </div>
          )}
        </div>
      </LayoutContainer>
    </div>
  );
}
