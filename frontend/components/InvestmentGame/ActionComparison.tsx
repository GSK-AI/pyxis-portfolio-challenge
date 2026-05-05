"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useNextStep } from "nextstepjs";
import { useCustomNextStep } from "@/hooks/use-custom-next-step";
import { getGameComparison, getLevelHighScore } from "@/lib/backendCallsGame";
import ComparisonTable from "./ComparisonTable";
import ComparisonLevelLeaderboard from "./ComparisonLevelLeaderboard";
import ComparisonGraph from "./ComparisonGraph";

interface ActionComparisonProps {
  gameId: string;
  level?: number;
}

export default function ActionComparison({
  gameId,
  level,
}: ActionComparisonProps) {
  const { startNextStep } = useNextStep();
  const { startTourIfNotSkipped } = useCustomNextStep();

  const {
    data: comparisonData,
    isLoading: loading,
    error,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["gameComparison", gameId],
    queryFn: () => getGameComparison(gameId),
    enabled: !!gameId && gameId !== "",
    staleTime: 1000 * 60 * 5, // Consider data fresh for 5 minutes
    retry: 2, // Retry failed requests 2 times
  });

  const { data: highScore, isLoading: highScoreLoading } = useQuery({
    queryKey: ["levelHighScore", level],
    queryFn: () => getLevelHighScore(level || 0),
    enabled: level !== undefined,
    staleTime: 1000 * 60 * 5, // Consider data fresh for 5 minutes
    retry: 2,
  });

  // Trigger tour when data is successfully loaded
  useEffect(() => {
    if (comparisonData && !loading && !isError) {
      // Add a small delay to ensure the UI is fully rendered
      setTimeout(() => {
        startTourIfNotSkipped("finalScreen", startNextStep);
      }, 100);
    }
  }, [comparisonData, loading, isError, startTourIfNotSkipped, startNextStep]);

  if (!gameId || gameId === "") {
    return (
      <div className="flex items-center justify-center rounded-lg bg-gray-50 p-8">
        <div className="text-lg font-medium text-red-600">
          No game ID provided
        </div>
      </div>
    );
  }

  if (loading || highScoreLoading) {
    return (
      <div className="flex items-center justify-center rounded-lg bg-gray-50 p-8">
        <div className="text-lg font-medium text-gray-600">
          Loading comparison data...
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center rounded-lg bg-gray-50 p-8">
        <div className="text-lg font-medium text-red-600">
          {"Failed to load comparison data"}
        </div>
      </div>
    );
  }

  if (!comparisonData) {
    return (
      <div className="flex items-center justify-center rounded-lg bg-gray-50 p-8">
        <div className="text-lg font-medium text-gray-600">
          No comparison data available
        </div>
      </div>
    );
  }

  return (
    <div
      className="grid w-full grid-cols-2 gap-6 rounded-lg bg-gray-50"
      id="comparisonDashboard"
    >
      <div className="flex flex-col gap-6 p-6">
        <div>
          <ComparisonTable
            comparisonData={comparisonData}
            highScore={highScore}
            currentGameId={gameId}
          />
        </div>
        <div id="comparisonLeaderboard">
          <ComparisonLevelLeaderboard
            gameId={gameId}
            level={level}
            highScore={highScore}
          />
        </div>
      </div>
      <div className="flex flex-col gap-6 p-6">
        <div className="min-h-[200px] flex-1">
          <ComparisonGraph
            comparisonData={comparisonData}
            dataType="enpv_over_time"
          />
        </div>
        <div className="min-h-[200px] flex-1">
          <ComparisonGraph
            comparisonData={comparisonData}
            dataType="eroi_over_time"
          />
        </div>
      </div>
    </div>
  );
}
