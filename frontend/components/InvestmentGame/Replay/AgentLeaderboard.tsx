"use client";

import type { GameStepSchemaType } from "@/lib/definitionsGameZ";
import { formatDisplayNumber } from "@/lib/numbers";
import { extractAssets } from "@/lib/game";
import { Trophy } from "lucide-react";

interface AgentLeaderboardProps {
  agentIds: string[];
  agentDisplayNames: Record<string, string>;
  agentStates: Record<string, GameStepSchemaType>;
  cumulativeRewards: Record<string, number>;
  agentColors: Record<string, string>;
}

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) {
    return (
      <span className="inline-flex items-center gap-0.5 rounded-full bg-yellow-100 px-2 py-0.5 text-[10px] font-semibold text-yellow-800">
        <Trophy className="h-3 w-3" />
        1st
      </span>
    );
  }
  const suffix = rank === 2 ? "nd" : rank === 3 ? "rd" : "th";
  const colors =
    rank === 2 ? "bg-gray-200 text-gray-700" : "bg-gray-100 text-gray-500";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${colors}`}
    >
      {rank}
      {suffix}
    </span>
  );
}

export default function AgentLeaderboard({
  agentIds,
  agentDisplayNames,
  agentStates,
  cumulativeRewards,
  agentColors,
}: AgentLeaderboardProps) {
  const entries = agentIds.map((id) => {
    const state = agentStates[id];
    const assets = state ? extractAssets(state) : [];
    const eNPV = assets
      .filter((a) => a.state !== "Expired" && a.state !== "Failed")
      .reduce((sum, a) => sum + a.enpv, 0);
    return {
      id,
      cash: state?.cash ?? 0,
      eNPV,
      portfolioSize: assets.length,
      cumulativeReward: cumulativeRewards[id] ?? 0,
      gameEnded: state?.game_ended ?? false,
      endedReason: state?.ended_reason,
    };
  });

  // Rank by cumulative reward (descending) but keep render order fixed
  const sorted = [...entries].sort(
    (a, b) => b.cumulativeReward - a.cumulativeReward,
  );
  const rankMap = new Map(sorted.map((e, i) => [e.id, i + 1]));

  return (
    <div className="flex gap-3">
      {entries.map((entry) => {
        const color = agentColors[entry.id];
        const rank = rankMap.get(entry.id) ?? entries.length;
        const isLeader = rank === 1;
        return (
          <div
            key={entry.id}
            className={`flex-1 rounded-lg border p-3 ${
              isLeader
                ? "border-yellow-300 bg-yellow-50"
                : entry.gameEnded && !entry.endedReason?.includes("horizon")
                  ? "border-red-200 bg-red-50"
                  : "border-gray-200 bg-white"
            }`}
          >
            <div className="flex items-center gap-2">
              <RankBadge rank={rank} />
              <div
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-xs font-semibold">
                {agentDisplayNames[entry.id] ?? entry.id}
              </span>
              {entry.gameEnded && !entry.endedReason?.includes("horizon") && (
                <span className="text-[10px] font-semibold text-red-600">
                  Bankrupt
                </span>
              )}
            </div>
            <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] text-gray-600">
              <span>
                NCF:{" "}
                <span
                  className={`font-medium ${entry.cumulativeReward >= 0 ? "text-green-700" : "text-red-600"}`}
                >
                  {formatDisplayNumber(entry.cumulativeReward)}
                </span>
              </span>
              <span>
                Cash:{" "}
                <span className="font-medium">
                  {formatDisplayNumber(entry.cash)}
                </span>
              </span>
              <span>
                eNPV:{" "}
                <span className="font-medium">
                  {formatDisplayNumber(entry.eNPV)}
                </span>
              </span>
              <span>
                Assets:{" "}
                <span className="font-medium">{entry.portfolioSize}</span>
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
