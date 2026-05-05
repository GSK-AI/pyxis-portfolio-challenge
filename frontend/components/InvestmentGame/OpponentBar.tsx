"use client";

import type { OpponentSummary } from "@/lib/definitionsGameZ";
import { formatDisplayNumber } from "@/lib/numbers";
import { Check, Trophy } from "lucide-react";

function StatusBadge({
  status,
}: {
  status: "idle" | "waiting" | "thinking" | "decided";
}) {
  const base =
    "inline-flex w-[90px] items-center justify-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium";

  if (status === "idle") {
    return <span className={`${base} bg-transparent text-transparent`}>-</span>;
  }

  if (status === "waiting") {
    return (
      <span className={`${base} bg-gray-200 text-gray-500`}>Waiting...</span>
    );
  }

  if (status === "thinking") {
    return (
      <span className={`${base} bg-amber-100 text-amber-700`}>
        <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
        Analysing
      </span>
    );
  }

  return (
    <span className={`${base} bg-green-100 text-green-700`}>
      <Check className="h-3 w-3" />
      Ready
    </span>
  );
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

export default function OpponentBar({
  opponents,
  thinkingState,
  playerCumulativeReward,
}: {
  opponents: OpponentSummary[];
  thinkingState?: Record<string, "waiting" | "thinking" | "decided">;
  playerCumulativeReward: number;
}) {
  if (opponents.length === 0) return null;

  // Build ranked leaderboard: player + all opponents
  type LeaderboardEntry = {
    name: string;
    cumulativeReward: number;
    isPlayer: boolean;
  };

  const entries: LeaderboardEntry[] = [
    { name: "You", cumulativeReward: playerCumulativeReward, isPlayer: true },
    ...opponents.map((opp) => ({
      name: opp.display_name,
      cumulativeReward: opp.cumulative_reward,
      isPlayer: false,
    })),
  ];
  entries.sort((a, b) => b.cumulativeReward - a.cumulativeReward);

  // Assign ranks
  const rankMap: Record<string, number> = {};
  entries.forEach((entry, i) => {
    rankMap[entry.name] = i + 1;
  });

  const playerRank = rankMap["You"];

  return (
    <div className="flex w-full flex-col gap-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">Competitors</h3>
        <div className="flex items-center gap-2 text-xs text-gray-600">
          <span>Your rank:</span>
          <RankBadge rank={playerRank} />
          <span className="text-gray-400">|</span>
          <span>
            Net Cash Flow:{" "}
            <span
              className={`font-semibold ${playerCumulativeReward >= 0 ? "text-green-700" : "text-red-600"}`}
            >
              {formatDisplayNumber(playerCumulativeReward)}
            </span>
          </span>
        </div>
      </div>
      {opponents.map((opp) => {
        const status = thinkingState?.[opp.agent_name];
        const rank = rankMap[opp.display_name];
        return (
          <div
            key={opp.agent_name}
            className={`w-full rounded-lg border p-3 transition-colors duration-300 ${
              opp.game_ended &&
              (!opp.ended_reason || !opp.ended_reason.includes("horizon"))
                ? "border-red-300 bg-red-50"
                : status === "thinking"
                  ? "border-amber-300 bg-amber-50"
                  : status === "decided"
                    ? "border-green-300 bg-green-50"
                    : "border-gray-150 bg-gray-50"
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <RankBadge rank={rank} />
                <span className="text-xs font-semibold text-gray-800">
                  {opp.display_name}
                </span>
                <span className="text-[10px] text-gray-500">
                  ({opp.agent_type})
                </span>
              </div>
              <StatusBadge status={status || "idle"} />
            </div>
            <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-600">
              <span>
                Net Cash Flow:{" "}
                <span
                  className={`font-medium ${opp.cumulative_reward >= 0 ? "text-green-700" : "text-red-600"}`}
                >
                  {formatDisplayNumber(opp.cumulative_reward)}
                </span>
              </span>
              <span>
                Cash:{" "}
                <span className="font-medium">
                  {formatDisplayNumber(opp.cash)}
                </span>
              </span>
              <span>
                On Market:{" "}
                <span className="font-medium">{opp.num_on_market}</span>
              </span>
              <span>
                In Dev:{" "}
                <span className="font-medium">{opp.num_in_development}</span>
              </span>
              <span>
                eNPV:{" "}
                <span className="font-medium">
                  {formatDisplayNumber(opp.enpv)}
                </span>
              </span>
              {opp.game_ended &&
                (!opp.ended_reason ||
                  !opp.ended_reason.includes("horizon")) && (
                  <span className="font-semibold text-red-600">Bankrupt</span>
                )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
