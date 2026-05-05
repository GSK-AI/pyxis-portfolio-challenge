"use client";

import { useState } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import {
  RotateCcw,
  Shuffle,
  Trophy,
  AlertTriangle,
  Clock,
  ChevronDown,
  ChevronUp,
  Settings,
} from "lucide-react";
import type { GameStepSchemaType, GameStart } from "@/lib/definitionsGameZ";
import { formatDisplayNumber, formatCurrency } from "@/lib/numbers";

interface GameOverScreenProps {
  activeState: GameStepSchemaType | null;
  onRestartSameGame: () => void;
  onStartNewGame: () => void;
  loadingRestart?: boolean;
  loadingNewGame?: boolean;
  gameConfig?: GameStart | null;
  defaultConfig?: GameStart | null;
  onConfigChange?: (field: keyof GameStart, value: number) => void;
}

// Map backend end reasons to user-friendly messages
function getEndReasonDisplay(endedReason: string | null, cash: number) {
  if (!endedReason) {
    // Fallback based on cash
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

  // Match backend GameEndReason values
  if (endedReason.includes("ongoing investments")) {
    return {
      title: "Bankrupt!",
      message: "You ran out of cash due to ongoing development costs.",
      icon: AlertTriangle,
      colorClass: "text-red-600",
      bgClass: "from-red-50 to-red-100 border-red-200",
    };
  }

  if (endedReason.includes("new investments")) {
    return {
      title: "Bankrupt!",
      message: "You ran out of cash trying to start new investments.",
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

  // Default
  return {
    title: "Game Over",
    message: endedReason,
    icon: Trophy,
    colorClass: "text-gray-600",
    bgClass: "from-gray-50 to-gray-100 border-gray-200",
  };
}

// Calculate summary stats
function calculateSummary(state: GameStepSchemaType) {
  const assets = Object.values(state.assets);
  const expiredAssets = Object.values(state.expired_assets);
  const allAssets = [...assets, ...expiredAssets];

  const onMarket = allAssets.filter((a) => a.state === "On Market").length;
  const failed = allAssets.filter((a) => a.state === "Failed").length;
  const inDevelopment = assets.filter(
    (a) => a.state === "In Development",
  ).length;

  const totalRevenue = state.realised_revenues.reduce((sum, r) => sum + r, 0);
  const totalCosts = state.realised_costs.reduce((sum, c) => sum + c, 0);
  const netCashFlow = totalRevenue - totalCosts;

  // Calculate final eNPV from assets
  const totalEnpv = assets.reduce((sum, a) => sum + a.enpv, 0);

  return {
    finalCash: state.cash,
    yearsPlayed: state.time,
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

export default function GameOverScreen({
  activeState,
  onRestartSameGame,
  onStartNewGame,
  loadingRestart = false,
  loadingNewGame = false,
  gameConfig,
  defaultConfig,
  onConfigChange,
}: GameOverScreenProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);

  if (!activeState) return null;

  const endDisplay = getEndReasonDisplay(
    activeState.ended_reason,
    activeState.cash,
  );
  const summary = calculateSummary(activeState);
  const Icon = endDisplay.icon;
  const isSuccess = activeState.cash >= 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div
        className={`w-full max-w-lg rounded-2xl border bg-gradient-to-br p-8 shadow-2xl ${endDisplay.bgClass}`}
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
            {endDisplay.title}
          </h2>
          <p className="mt-2 text-lg text-gray-600">{endDisplay.message}</p>
        </div>

        {/* Summary Stats */}
        <div className="mb-6 rounded-xl bg-white/80 p-4 shadow-inner">
          <h3 className="mb-3 text-center font-semibold text-gray-700">
            Game Summary
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
                {summary.yearsPlayed} / {activeState.horizon}
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

        {/* Collapsible Settings for New Game */}
        {gameConfig && onConfigChange && (
          <div className="mb-4">
            <button
              onClick={() => setSettingsOpen(!settingsOpen)}
              className="flex w-full items-center justify-between rounded-lg bg-white/60 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-white/80"
            >
              <span className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                New Game Settings
              </span>
              {settingsOpen ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
            {settingsOpen && (
              <div className="mt-2 space-y-3 rounded-lg bg-white/80 p-4">
                <div className="flex items-center gap-3">
                  <label className="w-28 text-sm text-gray-600">
                    Starting Assets
                  </label>
                  <Input
                    type="number"
                    value={gameConfig.num_assets}
                    onChange={(e) =>
                      onConfigChange(
                        "num_assets",
                        parseInt(e.target.value) || 1,
                      )
                    }
                    min={1}
                    max={50}
                    className="h-8 w-20 text-sm"
                  />
                  {defaultConfig && (
                    <span className="text-xs text-gray-400">
                      (default: {defaultConfig.num_assets})
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <label className="w-28 text-sm text-gray-600">
                    Horizon (years)
                  </label>
                  <Input
                    type="number"
                    value={gameConfig.horizon}
                    onChange={(e) =>
                      onConfigChange("horizon", parseInt(e.target.value) || 1)
                    }
                    min={1}
                    max={200}
                    className="h-8 w-20 text-sm"
                  />
                  {defaultConfig && (
                    <span className="text-xs text-gray-400">
                      (default: {defaultConfig.horizon})
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <label className="w-28 text-sm text-gray-600">
                    Starting Cash
                  </label>
                  <Input
                    type="number"
                    value={gameConfig.starting_cash}
                    onChange={(e) =>
                      onConfigChange(
                        "starting_cash",
                        parseFloat(e.target.value) || 0,
                      )
                    }
                    min={0}
                    step={100000000}
                    className="h-8 w-32 text-sm"
                  />
                  {defaultConfig && (
                    <span className="text-xs text-gray-400">
                      (default: £
                      {formatDisplayNumber(defaultConfig.starting_cash)})
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button
            onClick={onRestartSameGame}
            variant="outline"
            size="lg"
            className="flex-1"
            disabled={loadingRestart || loadingNewGame}
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            {loadingRestart ? "Loading..." : "Restart Same Game"}
          </Button>
          <Button
            onClick={onStartNewGame}
            size="lg"
            className="flex-1"
            disabled={loadingRestart || loadingNewGame}
          >
            <Shuffle className="mr-2 h-4 w-4" />
            {loadingNewGame ? "Loading..." : "Try New Game"}
          </Button>
        </div>
      </div>
    </div>
  );
}
