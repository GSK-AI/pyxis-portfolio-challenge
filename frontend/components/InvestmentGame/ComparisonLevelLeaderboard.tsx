"use client";

import { useQuery } from "@tanstack/react-query";
import { getLevelLeaderboard } from "@/lib/backendCallsGame";
import { formatCurrency } from "@/lib/numbers";
import { Trophy, Crown } from "lucide-react";
import type { LeaderboardEntry } from "@/lib/definitionsGameZ";

interface ComparisonLevelLeaderboardProps {
  gameId?: string;
  level?: number;
  highScore?: LeaderboardEntry;
}

export default function ComparisonLevelLeaderboard({
  gameId,
  level,
  highScore,
}: ComparisonLevelLeaderboardProps) {
  const { data: leaderboard, isLoading } = useQuery({
    queryKey: ["levelLeaderboard", level],
    queryFn: () => getLevelLeaderboard(level || 0),
    enabled: level !== undefined,
    staleTime: 1000 * 60 * 5, // Consider data fresh for 5 minutes
  });

  if (isLoading) {
    return (
      <div className="w-full">
        <h3 className="mb-4 text-lg font-semibold">Level Leaderboard</h3>
        <div className="py-4 text-center text-gray-600">
          Loading leaderboard...
        </div>
      </div>
    );
  }

  if (level === undefined) {
    return (
      <div className="w-full">
        <h3 className="mb-4 text-lg font-semibold">Level Leaderboard</h3>
        <div className="py-4 text-center text-gray-600">No level provided</div>
      </div>
    );
  }

  if (!leaderboard || leaderboard.length === 0) {
    return (
      <div className="w-full">
        <h3 className="mb-4 text-lg font-semibold">Level Leaderboard</h3>
        <div className="py-4 text-center text-gray-600">
          No leaderboard data available
        </div>
      </div>
    );
  }

  // Get top 3 records
  const top3 = leaderboard.slice(0, 3);

  return (
    <div className="w-full">
      <div className="mb-4 flex items-center gap-2">
        <Trophy className="h-5 w-5 text-yellow-500" />
        <h3 className="text-lg font-semibold">Level {level + 1} Leaderboard</h3>
        <p className="text-sm font-light">
          Only your first attempt counts towards the leaderboard
        </p>
      </div>
      <div className="space-y-2">
        {top3.map((entry: LeaderboardEntry, index: number) => {
          const position = index + 1;
          const getPositionColor = (pos: number) => {
            switch (pos) {
              case 1:
                return "bg-blue-100 text-gray-800";
              case 2:
                return "bg-blue-50 text-gray-800";
              case 3:
                return "bg-blue-25 text-gray-800";
              default:
                return "bg-blue-25 text-gray-800";
            }
          };

          // Check if this entry is the user's high score
          const isHighScoreUser =
            highScore &&
            entry.user_id === highScore.user_id &&
            entry.game_id === highScore.game_id;

          return (
            <div
              key={`${entry.user_id}-${entry.game_id}`}
              className={`flex items-center gap-4 rounded-lg p-3 ${getPositionColor(position)}`}
            >
              <div className="min-w-[20px] text-lg font-bold">{position}</div>
              <div className="flex flex-1 items-center gap-2 font-medium">
                {entry.user_id}
                {isHighScoreUser && (
                  <div title="Your High Score">
                    <Crown className="h-4 w-4 text-yellow-500" />
                  </div>
                )}
              </div>
              <div className="text-right">
                <span className="text-sm">avg. eNPV: </span>
                <span className="font-semibold">
                  {formatCurrency(entry.av_enpv)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
