"use client";

import { useQuery } from "@tanstack/react-query";
import { getUserName } from "@/lib/get-user-name";
import { getAgents } from "@/lib/backendCallsGame";
import { formatCurrency } from "@/lib/numbers";
import { visualisationConsts } from "@/lib/visualisations/helpers";
import { Crown } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { GameComparison, LeaderboardEntry } from "@/lib/definitionsGameZ";

interface ComparisonTableProps {
  comparisonData: GameComparison;
  highScore?: LeaderboardEntry;
  currentGameId?: string;
}

export default function ComparisonTable({
  comparisonData,
  highScore,
  currentGameId,
}: ComparisonTableProps) {
  const { colors } = visualisationConsts;

  const { data: username } = useQuery<string | undefined, Error>({
    queryKey: ["getUserName"],
    queryFn: () => getUserName(),
  });

  const { data: agents } = useQuery({
    queryKey: ["getAgents"],
    queryFn: () => getAgents(),
    staleTime: 1000 * 60 * 10, // Consider agents fresh for 10 minutes
  });

  // Get user score and filter agents that exist in comparison data
  const userScore = username ? comparisonData.av_enpv[username] : undefined;
  const availableAgents = agents
    ? agents.filter((agent) => agent.name in comparisonData.av_enpv)
    : [];

  // Check if current game is personal best
  const isPersonalBest =
    highScore && currentGameId && highScore.game_id === currentGameId;

  // Color function for agent headers (same logic as ComparisonGraph)
  const getAgentHeaderColor = (agentIndex: number) => {
    if (agentIndex === 0) {
      // First agent uses original orange color
      return colors.plotHighlightSecondary; // "#fe7800" - orange
    }

    // Other agents (index > 0) in progressively darker orange variations
    const baseOrange = 0xfe7800; // #fe7800
    const darkeningFactor = 0.6; // Reduce brightness by 20% for each subsequent agent
    const adjustedBrightness = Math.pow(darkeningFactor, agentIndex);

    const r = Math.floor(((baseOrange >> 16) & 0xff) * adjustedBrightness);
    const g = Math.floor(((baseOrange >> 8) & 0xff) * adjustedBrightness);
    const b = Math.floor((baseOrange & 0xff) * adjustedBrightness);

    return `rgb(${r}, ${g}, ${b})`;
  };

  return (
    <div className="w-full">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="text-left"></TableHead>
            <TableHead className="text-right" style={{ color: colors.plot }}>
              {isPersonalBest && (
                <div className="flex items-center justify-end">
                  <div className="mb-2 flex items-center gap-2 rounded bg-yellow-200 p-1 text-black">
                    <Crown className="h-4 w-4" /> Personal Best
                  </div>
                </div>
              )}
              <span>Your Score</span>
            </TableHead>
            {availableAgents.map((agent, agentIndex) => (
              <TableHead
                key={agent.name}
                className="text-right"
                style={{ color: getAgentHeaderColor(agentIndex) }}
              >
                <p>AI Agent</p>
                <small>{agent.name}</small>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell className="font-medium">Average eNPV</TableCell>
            <TableCell className="text-right">
              {formatCurrency(userScore || 0)}
            </TableCell>
            {availableAgents.map((agent) => (
              <TableCell key={agent.name} className="text-right">
                {formatCurrency(comparisonData.av_enpv[agent.name] || 0)}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Final eNPV</TableCell>
            <TableCell className="text-right">
              {formatCurrency(
                username ? comparisonData.final_enpv[username] || 0 : 0,
              )}
            </TableCell>
            {availableAgents.map((agent) => (
              <TableCell key={agent.name} className="text-right">
                {formatCurrency(comparisonData.final_enpv[agent.name] || 0)}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Final eROI</TableCell>
            <TableCell className="text-right">
              x
              {(username
                ? comparisonData.final_eroi[username] || 0
                : 0
              ).toFixed(2)}
            </TableCell>
            {availableAgents.map((agent) => (
              <TableCell key={agent.name} className="text-right">
                x{(comparisonData.final_eroi[agent.name] || 0).toFixed(2)}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Final Capital</TableCell>
            <TableCell className="text-right">
              {formatCurrency(
                username ? comparisonData.final_capital[username] || 0 : 0,
              )}
            </TableCell>
            {availableAgents.map((agent) => (
              <TableCell key={agent.name} className="text-right">
                {formatCurrency(comparisonData.final_capital[agent.name] || 0)}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Realised ROI</TableCell>
            <TableCell className="text-right">
              x
              {(username
                ? comparisonData.realised_eroi[username] || 0
                : 0
              ).toFixed(2)}
            </TableCell>
            {availableAgents.map((agent) => (
              <TableCell key={agent.name} className="text-right">
                x{(comparisonData.realised_eroi[agent.name] || 0).toFixed(2)}
              </TableCell>
            ))}
          </TableRow>
        </TableBody>
      </Table>
    </div>
  );
}
