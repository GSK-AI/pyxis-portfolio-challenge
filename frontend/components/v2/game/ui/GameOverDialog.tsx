"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { RankBadge } from "./Competitors";
import { StatGroup, type StatProps } from "./Stat";
import { formatDisplayNumber } from "@/lib/numbers";

export interface Standing {
  name: string;
  agentType?: string;
  isPlayer?: boolean;
  netCashFlow: number;
  enpv: number;
  /** Out before the horizon — ranked below solvent players (classic). */
  bankrupt?: boolean;
}

/** End-of-game results: final standings by net cash flow + player stats. */
export function GameOverDialog({
  open,
  onOpenChange,
  totalYears,
  standings,
  playerStats,
  onPlayAgain,
  onRestartSame,
  onHome,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  totalYears: number;
  /** Sorted best-first; ranks are positions in this list. */
  standings: Standing[];
  playerStats: StatProps[];
  onPlayAgain: () => void;
  /** Replay the same seed (classic single-player option). */
  onRestartSame?: () => void;
  onHome: () => void;
}) {
  const playerRank = standings.findIndex((s) => s.isPlayer) + 1;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg rounded">
        <DialogHeader>
          <DialogTitle className="font-bold">Game Over</DialogTitle>
          <DialogDescription className="pt-1 font-light">
            {playerRank > 0
              ? `You finished ${playerRank === 1 ? "1st" : playerRank === 2 ? "2nd" : playerRank === 3 ? "3rd" : `${playerRank}th`} of ${standings.length} after ${totalYears} years.`
              : `The game ended after ${totalYears} years.`}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          {standings.map((standing, i) => (
            <div
              key={standing.name}
              className={cn(
                "flex items-center gap-2.5 rounded p-3",
                standing.bankrupt
                  ? "bg-gradient-to-r from-[#fdf1f0] to-transparent"
                  : standing.isPlayer
                    ? "bg-gradient-to-r from-[#eef4fc] to-transparent"
                    : "bg-secondary/40",
              )}
            >
              <RankBadge rank={i + 1} />
              <span className="text-sm font-bold">{standing.name}</span>
              {standing.isPlayer ? (
                <span className="rounded-full bg-[var(--accent-soft)] px-2 py-0.5 text-xs font-bold text-primary">
                  You
                </span>
              ) : (
                standing.agentType && (
                  <span className="text-xs text-muted-foreground">
                    {standing.agentType}
                  </span>
                )
              )}
              {standing.bankrupt && (
                <span className="text-[10px] font-bold uppercase tracking-wider text-destructive">
                  Bankrupt
                </span>
              )}
              <span className="ml-auto flex items-baseline gap-4 text-right">
                <span>
                  <span className="block text-sm font-bold tabular-nums">
                    {formatDisplayNumber(standing.enpv)}
                  </span>
                  <span className="block text-[10px] uppercase tracking-wider text-muted-foreground/70">
                    eNPV
                  </span>
                </span>
                <span>
                  <span
                    className={cn(
                      "block text-sm font-bold tabular-nums",
                      standing.netCashFlow < 0 && "text-destructive",
                    )}
                  >
                    {formatDisplayNumber(standing.netCashFlow)}
                  </span>
                  <span className="block text-[10px] uppercase tracking-wider text-muted-foreground/70">
                    Net Cash Flow
                  </span>
                </span>
              </span>
            </div>
          ))}
        </div>

        <div className="rounded bg-secondary/25 p-4">
          <StatGroup stats={playerStats} />
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="ghost" size="sm" onClick={onHome}>
            Home
          </Button>
          {onRestartSame && (
            <Button
              variant="outline"
              size="sm"
              className="rounded"
              onClick={onRestartSame}
            >
              Replay Same Game
            </Button>
          )}
          <Button size="sm" className="rounded" onClick={onPlayAgain}>
            Play Again
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
