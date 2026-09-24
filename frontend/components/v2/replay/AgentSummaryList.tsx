"use client";

import type { GameStepSchemaType } from "@/lib/definitionsGameZ";
import { cn } from "@/lib/utils";
import { formatDisplayNumber } from "@/lib/numbers";
import { extractAssets } from "@/lib/game";
import { RankBadge } from "@/components/v2/game/ui/Competitors";

/**
 * v2 agent summary for the replay viewer: one card per agent, ranked
 * by net cash flow. Entry computation (eNPV over live assets, rank by
 * cumulative reward, bankruptcy detection) is IDENTICAL to the classic
 * AgentLeaderboard — only the presentation changed.
 */

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "negative";
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
        {label}
      </div>
      <div
        className={cn(
          "text-sm font-bold tabular-nums",
          tone === "negative" && "text-destructive",
        )}
      >
        {value}
      </div>
    </div>
  );
}

export function AgentSummaryList({
  agentIds,
  agentDisplayNames,
  agentStates,
  cumulativeRewards,
  agentColors,
}: {
  agentIds: string[];
  agentDisplayNames: Record<string, string>;
  agentStates: Record<string, GameStepSchemaType>;
  cumulativeRewards: Record<string, number>;
  agentColors: Record<string, string>;
}) {
  // --- identical entry computation to the classic AgentLeaderboard ---
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

  const sorted = [...entries].sort(
    (a, b) => b.cumulativeReward - a.cumulativeReward,
  );
  const rankMap = new Map(sorted.map((e, i) => [e.id, i + 1]));
  // --- end identical logic ---

  return (
    <div className="space-y-2">
      {entries.map((entry) => {
        const rank = rankMap.get(entry.id) ?? entries.length;
        const bankrupt =
          entry.gameEnded && !entry.endedReason?.includes("horizon");
        return (
          <div
            key={entry.id}
            className={cn(
              "space-y-2.5 rounded p-3",
              rank === 1
                ? "bg-gradient-to-r from-[#dff4f8] to-[#f0fafc]"
                : bankrupt
                  ? "bg-gradient-to-r from-[#fdf1f0] to-[#fdf8f7]"
                  : "bg-secondary/40",
            )}
          >
            <div className="flex items-center gap-2">
              <RankBadge rank={rank} />
              <span
                className="size-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: agentColors[entry.id] }}
              />
              <span className="truncate text-sm font-bold">
                {agentDisplayNames[entry.id] ?? entry.id}
              </span>
              {bankrupt && (
                <span className="ml-auto text-[10px] font-bold uppercase tracking-wider text-destructive">
                  Bankrupt
                </span>
              )}
            </div>
            <div className="grid grid-cols-4 gap-2">
              <Metric
                label="NCF"
                value={formatDisplayNumber(entry.cumulativeReward)}
                tone={entry.cumulativeReward < 0 ? "negative" : undefined}
              />
              <Metric label="Cash" value={formatDisplayNumber(entry.cash)} />
              <Metric label="eNPV" value={formatDisplayNumber(entry.eNPV)} />
              <Metric label="Assets" value={String(entry.portfolioSize)} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
