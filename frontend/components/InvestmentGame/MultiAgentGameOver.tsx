"use client";

import { Button } from "../ui/button";
import {
  RotateCcw,
  ArrowLeft,
  Trophy,
  AlertTriangle,
  Clock,
} from "lucide-react";
import type {
  GameStepSchemaType,
  MultiAgentGameStep,
  AssetSchemaType,
} from "@/lib/definitionsGameZ";
import { formatDisplayNumber, formatCurrency } from "@/lib/numbers";

function getEndReasonDisplay(endedReason: string | null, cash: number) {
  if (!endedReason) {
    if (cash < 0) {
      return {
        title: "Bankrupt!",
        message: "You ran out of capital.",
        icon: AlertTriangle,
        colorClass: "text-red-600",
        bgClass: "from-red-50 to-red-100 border-red-200",
      };
    }
    return {
      title: "Game Complete!",
      message: "You've reached the end of the game.",
      icon: Trophy,
      colorClass: "text-green-600",
      bgClass: "from-green-50 to-green-100 border-green-200",
    };
  }

  if (
    endedReason.includes("ongoing investments") ||
    endedReason.includes("new investments")
  ) {
    return {
      title: "Bankrupt!",
      message: "You ran out of cash due to development costs.",
      icon: AlertTriangle,
      colorClass: "text-red-600",
      bgClass: "from-red-50 to-red-100 border-red-200",
    };
  }

  if (endedReason.includes("horizon")) {
    return {
      title: "Time's Up!",
      message: "You've reached the game horizon.",
      icon: Clock,
      colorClass: "text-blue-600",
      bgClass: "from-blue-50 to-blue-100 border-blue-200",
    };
  }

  return {
    title: "Game Over",
    message: endedReason,
    icon: Trophy,
    colorClass: "text-gray-600",
    bgClass: "from-gray-50 to-gray-100 border-gray-200",
  };
}

function calculateSummary(
  state: GameStepSchemaType,
  allAssets: AssetSchemaType[],
  gameTime?: number,
) {
  const onMarket = allAssets.filter((a) => a.state === "On Market").length;
  const failed = allAssets.filter((a) => a.state === "Failed").length;
  const inDevelopment = allAssets.filter(
    (a) => a.state === "In Development",
  ).length;

  const totalRevenue = state.realised_revenues.reduce((sum, r) => sum + r, 0);
  const totalCosts = state.realised_costs.reduce((sum, c) => sum + c, 0);
  const netCashFlow = totalRevenue - totalCosts;
  const totalEnpv = allAssets.reduce((sum, a) => sum + a.enpv, 0);

  return {
    finalCash: state.cash,
    yearsPlayed: gameTime ?? state.time,
    totalAssets: allAssets.length,
    onMarket,
    failed,
    inDevelopment,
    totalRevenue,
    totalCosts,
    netCashFlow,
    totalEnpv,
  };
}

export default function MultiAgentGameOver({
  playerState,
  activeState,
  assets,
  onNewGame,
  onBackToStart,
}: {
  playerState: GameStepSchemaType | null | undefined;
  activeState: MultiAgentGameStep | null | undefined;
  assets: AssetSchemaType[];
  onNewGame: () => void;
  onBackToStart: () => void;
}) {
  if (!playerState || !activeState) return null;

  const endDisplay = getEndReasonDisplay(
    activeState.ended_reason,
    playerState.cash,
  );
  const summary = calculateSummary(playerState, assets, activeState.time);
  const Icon = endDisplay.icon;

  // Build leaderboard ranked by cumulative reward
  type RankedEntry = {
    name: string;
    displayName: string;
    cumulativeReward: number;
    enpv: number;
    cash: number;
    bankrupt: boolean;
    isPlayer: boolean;
  };

  const entries: RankedEntry[] = [
    {
      name: "You",
      displayName: "You",
      cumulativeReward: activeState.player_cumulative_reward,
      enpv: summary.totalEnpv,
      cash: summary.finalCash,
      bankrupt: activeState.player_bankrupt,
      isPlayer: true,
    },
    ...(activeState.opponents || []).map((o) => ({
      name: o.agent_name,
      displayName: o.display_name,
      cumulativeReward: o.cumulative_reward,
      enpv: o.enpv,
      cash: o.cash,
      bankrupt:
        o.game_ended &&
        (!o.ended_reason || !o.ended_reason.includes("horizon")),
      isPlayer: false,
    })),
  ];

  // Sort: non-bankrupt first, then by cumulative reward descending
  entries.sort((a, b) => {
    if (a.bankrupt && !b.bankrupt) return 1;
    if (!a.bankrupt && b.bankrupt) return -1;
    return b.cumulativeReward - a.cumulativeReward;
  });

  const playerRank = entries.findIndex((e) => e.isPlayer) + 1;
  const playerWon = playerRank === 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div
        className={`w-full max-w-2xl rounded-2xl border bg-gradient-to-br p-8 shadow-2xl ${endDisplay.bgClass}`}
      >
        {/* Header */}
        <div className="mb-6 text-center">
          <div className="mb-4 flex justify-center">
            <div
              className={`rounded-full bg-white p-4 shadow-md ${endDisplay.colorClass}`}
            >
              <Icon className="h-12 w-12" />
            </div>
          </div>
          <h2 className={`text-3xl font-bold ${endDisplay.colorClass}`}>
            {playerWon ? "You Won!" : endDisplay.title}
          </h2>
          <p className="mt-2 text-lg text-gray-600">
            {playerWon
              ? "You finished in 1st place!"
              : `You finished in ${playerRank}${playerRank === 2 ? "nd" : playerRank === 3 ? "rd" : "th"} place. ${endDisplay.message}`}
          </p>
        </div>

        {/* Leaderboard */}
        <div className="mb-6 rounded-xl bg-white/80 p-4 shadow-inner">
          <h3 className="mb-3 text-center font-semibold text-gray-700">
            Final Standings
          </h3>
          <div className="space-y-2">
            {entries.map((entry, i) => (
              <div
                key={entry.name}
                className={`flex items-center justify-between rounded-lg border px-4 py-3 ${
                  entry.isPlayer
                    ? i === 0
                      ? "border-yellow-300 bg-yellow-50"
                      : "border-blue-200 bg-blue-50"
                    : "border-gray-100 bg-gray-50"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`text-lg font-bold ${
                      i === 0
                        ? "text-yellow-600"
                        : i === 1
                          ? "text-gray-500"
                          : "text-gray-400"
                    }`}
                  >
                    {i === 0 ? <Trophy className="h-5 w-5" /> : `#${i + 1}`}
                  </span>
                  <span
                    className={`font-medium ${entry.isPlayer ? "text-blue-800" : "text-gray-800"}`}
                  >
                    {entry.displayName}
                  </span>
                  {entry.bankrupt && (
                    <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-600">
                      Bankrupt
                    </span>
                  )}
                </div>
                <div className="flex gap-4 text-sm text-gray-600">
                  <span>
                    Net Cash Flow:{" "}
                    <span
                      className={`font-semibold ${entry.cumulativeReward >= 0 ? "text-green-700" : "text-red-600"}`}
                    >
                      {formatDisplayNumber(entry.cumulativeReward)}
                    </span>
                  </span>
                  <span>
                    eNPV:{" "}
                    <span className="font-medium">
                      {formatDisplayNumber(entry.enpv)}
                    </span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Player Summary Stats */}
        <div className="mb-6 rounded-xl bg-white/80 p-4 shadow-inner">
          <h3 className="mb-3 text-center font-semibold text-gray-700">
            Your Summary
          </h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-gray-500">Final Capital</p>
              <p
                className={`text-lg font-bold ${summary.finalCash < 0 ? "text-red-600" : "text-green-600"}`}
              >
                {formatCurrency(summary.finalCash)}
              </p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-gray-500">Years Played</p>
              <p className="text-lg font-bold text-gray-800">
                {summary.yearsPlayed} / {playerState.horizon}
              </p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-gray-500">Portfolio eNPV</p>
              <p
                className={`text-lg font-bold ${summary.totalEnpv < 0 ? "text-red-600" : "text-green-600"}`}
              >
                {formatCurrency(summary.totalEnpv)}
              </p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-gray-500">Net Cash Flow</p>
              <p
                className={`text-lg font-bold ${summary.netCashFlow < 0 ? "text-red-600" : "text-green-600"}`}
              >
                {formatCurrency(summary.netCashFlow)}
              </p>
            </div>
          </div>

          {/* Asset breakdown */}
          <div className="mt-3 flex justify-center gap-4 text-xs text-gray-500">
            <span className="rounded bg-green-100 px-2 py-1">
              {summary.onMarket} On Market
            </span>
            <span className="rounded bg-blue-100 px-2 py-1">
              {summary.inDevelopment} In Development
            </span>
            <span className="rounded bg-red-100 px-2 py-1">
              {summary.failed} Failed
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button
            onClick={onNewGame}
            variant="outline"
            size="lg"
            className="flex-1"
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            Restart with same configuration
          </Button>
          <Button onClick={onBackToStart} size="lg" className="flex-1">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Start
          </Button>
        </div>
      </div>
    </div>
  );
}
