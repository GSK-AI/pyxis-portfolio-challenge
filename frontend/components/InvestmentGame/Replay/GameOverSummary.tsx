"use client";

import { useMemo } from "react";
import { Trophy } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { PlaythroughData } from "@/lib/definitionsGameZ";
import { extractAssets } from "@/lib/game";
import { formatDisplayNumber } from "@/lib/numbers";

interface GameOverSummaryProps {
  open: boolean;
  onClose: () => void;
  data: PlaythroughData;
  agentColors: Record<string, string>;
  agentDisplayNames: Record<string, string>;
}

interface AgentSummary {
  id: string;
  rank: number;
  ncf: number;
  finalCash: number;
  eNPV: number;
  totalAssets: number;
  onMarket: number;
  bankrupt: boolean;
  bankruptStep: number | null;
  survivalSteps: number;
}

export default function GameOverSummary({
  open,
  onClose,
  data,
  agentColors,
  agentDisplayNames,
}: GameOverSummaryProps) {
  const summaries = useMemo(() => {
    const lastStep = data.steps[data.steps.length - 1];
    if (!lastStep) return [];

    const entries: AgentSummary[] = data.metadata.agent_ids.map((id) => {
      const finalState = lastStep.agent_states[id];
      const assets = finalState ? extractAssets(finalState) : [];
      const eNPV = assets
        .filter((a) => a.state !== "Expired" && a.state !== "Failed")
        .reduce((sum, a) => sum + a.enpv, 0);
      const onMarket = assets.filter((a) => a.state === "On Market").length;

      // Find bankruptcy step
      let bankrupt = false;
      let bankruptStep: number | null = null;
      for (const step of data.steps) {
        const state = step.agent_states[id];
        if (state?.game_ended && !state?.ended_reason?.includes("horizon")) {
          bankrupt = true;
          bankruptStep = step.step;
          break;
        }
      }

      const survivalSteps = bankruptStep ?? lastStep.step;

      return {
        id,
        rank: 0,
        ncf: lastStep.cumulative_rewards[id] ?? 0,
        finalCash: finalState?.cash ?? 0,
        eNPV,
        totalAssets: assets.length,
        onMarket,
        bankrupt,
        bankruptStep,
        survivalSteps,
      };
    });

    // Rank by NCF descending
    const sorted = [...entries].sort((a, b) => b.ncf - a.ncf);
    sorted.forEach((e, i) => {
      e.rank = i + 1;
    });
    // Apply ranks back
    for (const entry of entries) {
      entry.rank = sorted.findIndex((s) => s.id === entry.id) + 1;
    }

    return entries;
  }, [data]);

  const winner = summaries.find((s) => s.rank === 1);
  const totalSteps =
    data.steps.length > 0 ? data.steps[data.steps.length - 1].step : 0;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <Trophy className="h-5 w-5 text-yellow-500" />
            Game Over
          </DialogTitle>
          <DialogDescription>
            {totalSteps} steps completed &middot; seed {data.metadata.seed}
          </DialogDescription>
        </DialogHeader>

        {/* Winner banner */}
        {winner && (
          <div
            className="flex items-center gap-3 rounded-lg border-2 p-3"
            style={{
              borderColor: agentColors[winner.id],
              backgroundColor: `${agentColors[winner.id]}10`,
            }}
          >
            <Trophy className="h-6 w-6 text-yellow-500" />
            <div>
              <div
                className="text-sm font-bold"
                style={{ color: agentColors[winner.id] }}
              >
                {agentDisplayNames[winner.id] ?? winner.id}
              </div>
              <div className="text-xs text-gray-600">
                Winner with NCF {formatDisplayNumber(winner.ncf)}
              </div>
            </div>
          </div>
        )}

        {/* Agent stats table */}
        <div className="mt-2 overflow-hidden rounded-lg border">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-gray-600">
                <th className="px-3 py-2 font-medium">Agent</th>
                <th className="px-3 py-2 text-right font-medium">NCF</th>
                <th className="px-3 py-2 text-right font-medium">Cash</th>
                <th className="px-3 py-2 text-right font-medium">eNPV</th>
                <th className="px-3 py-2 text-right font-medium">On Mkt</th>
                <th className="px-3 py-2 text-right font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {summaries
                .sort((a, b) => a.rank - b.rank)
                .map((agent) => (
                  <tr key={agent.id} className="border-b last:border-b-0">
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <div
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: agentColors[agent.id] }}
                        />
                        <span className="font-medium">
                          {agentDisplayNames[agent.id] ?? agent.id}
                        </span>
                        {agent.rank === 1 && (
                          <Trophy className="h-3 w-3 text-yellow-500" />
                        )}
                      </div>
                    </td>
                    <td
                      className={`px-3 py-2 text-right font-medium ${agent.ncf >= 0 ? "text-green-700" : "text-red-600"}`}
                    >
                      {formatDisplayNumber(agent.ncf)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {formatDisplayNumber(agent.finalCash)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {formatDisplayNumber(agent.eNPV)}
                    </td>
                    <td className="px-3 py-2 text-right">{agent.onMarket}</td>
                    <td className="px-3 py-2 text-right">
                      {agent.bankrupt ? (
                        <span className="text-red-600">
                          Bankrupt (step {agent.bankruptStep})
                        </span>
                      ) : (
                        <span className="text-green-700">Survived</span>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        <div className="flex justify-end">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
